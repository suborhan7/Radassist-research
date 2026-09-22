"""
app/main.py
====================================================================
FastAPI app assembly. Expensive singletons -- most importantly
BiomedCLIPAdapter, which loads the BiomedCLIP model -- are constructed
exactly ONCE at startup via the lifespan context manager and stored on
app.state, never per-request. RetrievalService/LabelVotingService/
ContextBuilder/LLMOrchestrator/ResponseValidator/ReportFormatter are wired
from those singletons once and also stored on app.state; routes
(app/api/retrieval.py, app/api/generation.py) read them off
request.app.state rather than constructing anything themselves.
`vector_store` itself is also stored directly on app.state (not just
buried inside retrieval_service) since Phase 8's ReportGenerationService
needs the same ChromaVectorStore instance independently, for get_by_ids().
`prompt_builder` is likewise stored directly on app.state (Phase 10) --
previously constructed inline as an LLMOrchestrator constructor arg only,
with no standalone reference route code could reach; ExplainabilityService
needs the same PromptBuilder instance independently, for
build_explanation_prompt().

PatientService (Phase 11) is NOT stored on app.state -- unlike every
service above, it depends on nothing but a per-request db session (no
shared collaborator singleton to wire), so app/api/patients.py constructs
it directly in each route, same as it would even if a singleton existed
to read here. `deterministic_comparator` IS stored on app.state (Phase
11) -- same reasoning as `response_validator`: it takes no db session,
only an optional taxonomy_classes override, so it is constructed once and
reused, not rebuilt per request. app/api/comparisons.py's ComparisonService
mixes both patterns: patient_repository is a per-request PatientService
(db-dependent), while deterministic_comparator/prompt_builder/
llm_orchestrator are read off app.state (shared singletons).

CORS (Phase 12 Step 1): a real, necessary backend change, not silent
scope creep into frontend/'s territory -- every route above was built and
tested Phases 4-11 with no browser origin involved at all (TestClient/
pytest bypass CORS entirely), so this is genuinely new backend surface
area, flagged as such rather than folded in unannounced. Local dev only,
per the frozen Phase 12 spec's explicit "deployment packaging out of
scope" decision; `settings.CORS_ALLOWED_ORIGINS` defaults to the Next.js
dev server's origin (http://localhost:3000), not hardcoded here.

`phi_masker` (Phase 12 Step 7): a real prerequisite fix for the
Comparison page -- POST /retrieve previously deleted every uploaded query
image immediately after embedding, so there was no way to redisplay a
past visit's X-ray at all. Persisting the raw upload would have broken
this system's own PHI-masking invariant (every image this system stores/
serves has been masked first, since Phase 1); PHIMasker is loaded once
here, same "expensive singleton, constructed exactly once" rule as
BiomedCLIPAdapter, and POST /retrieve now masks the upload before
persisting it -- see app/api/retrieval.py.

`password_hasher`/`token_service` (Phase 13): both stateless/cheap to
construct (no model load, unlike BiomedCLIPAdapter/PHIMasker), but wired
as app.state singletons anyway for the same reason `response_validator`/
`deterministic_comparator` are -- consistency: every cross-cutting
collaborator that isn't inherently per-request (like a db session) lives
on app.state, not "singleton for expensive ones, ad-hoc construction for
cheap ones."
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.comparisons import router as comparisons_router
from app.api.dashboard import router as dashboard_router
from app.api.doctors import router as doctors_router
from app.api.explainability import router as explainability_router
from app.api.generation import router as generation_router
from app.api.patients import router as patients_router
from app.api.questionnaire import router as questionnaire_router
from app.api.reports import router as reports_router
from app.api.retrieval import router as retrieval_router
from app.api.system import router as system_router
from app.core.config import settings
from app.infrastructure.biomedclip_adapter import BiomedCLIPAdapter
from app.infrastructure.chroma_store import ChromaVectorStore
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.ollama_client import OllamaClient
from app.infrastructure.password_hasher import Argon2PasswordHasher
from app.services.context_builder import ContextBuilder
from app.services.deterministic_comparator import DeterministicComparator
from app.services.image_admission_service import ImageAdmissionService
from app.services.image_validator import ImageValidator
from app.services.modality_gate_service import ModalityGateService
from app.services.label_voting_service import LabelVotingService
from app.services.llm_orchestrator import LLMOrchestrator
from app.services.prompt_builder import PromptBuilder
from app.services.questionnaire_templates import QuestionnaireTemplateProvider
from app.services.report_formatter import ReportFormatter
from app.infrastructure.chexbert_labeler import ChexbertLabeler, ChexbertUnavailableError
from app.services.report_consistency_service import ReportConsistencyService
from app.services.response_validator import ResponseValidator
from app.services.retrieval_service import RetrievalService
from app.services.similarity_search import SimilaritySearchPolicy
from app.services.structural_validator import StructuralValidator
from shared.phi_masking.masker import PHIMasker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("lifespan startup: loading BiomedCLIPAdapter (should log exactly once per app lifetime)")
    embedder = BiomedCLIPAdapter()
    vector_store = ChromaVectorStore()
    validator = ImageValidator()
    search_policy = SimilaritySearchPolicy()
    logger.info("lifespan startup: loading PHIMasker (EasyOCR model load, should log exactly once)")
    # max_region_area_fraction comes from settings, not the masker's own
    # default, so the live pipeline's cap is configurable per deployment
    # like every other Gate B value.
    app.state.phi_masker = PHIMasker(
        max_region_area_fraction=settings.PHI_MASK_MAX_REGION_AREA_FRACTION
    )

    # Input Admission and Modality Gate (input_admission_modality_gate_
    # architecture_v1.0_FROZEN.md). Two separate singletons for two
    # separate services -- §1's closing line and §10 forbid merging them,
    # and they sit at different points of §9's pipeline (admission before
    # the PHI mask, the gate after the embed).
    #
    # Every parameter comes off `settings` (§11.1's Rule: no parameter
    # value in the source code). The constructor arguments are read here,
    # once, rather than inside either service, so a running process cannot
    # end up with one control on a stale value and another on a fresh one.
    app.state.image_admission_service = ImageAdmissionService(
        allowed_extensions=settings.upload_allowed_extensions,
        max_bytes=settings.UPLOAD_MAX_BYTES,
        min_bytes=settings.UPLOAD_MIN_BYTES,
        min_dimension_px=settings.IMAGE_MIN_DIMENSION_PX,
        max_dimension_px=settings.IMAGE_MAX_DIMENSION_PX,
        max_pixels=settings.IMAGE_MAX_PIXELS,
        # §5.5 (A14-A17). DR-4: the accepted set is PA/AP; the declarable
        # set additionally holds LATERAL, so declaring it is a distinct,
        # separately-coded rejection rather than an unrecognised value.
        accepted_projections=settings.accepted_projections,
        declared_projection_values=settings.declared_projection_values,
    )
    # M6: the prompt text vectors are encoded inside this constructor, so
    # this line IS the "cache the text vectors at start-up" requirement --
    # it runs in lifespan, exactly once per process, and shares the one
    # already-loaded BiomedCLIP embedder rather than loading a second copy.
    logger.info("lifespan startup: caching ModalityGateService prompt vectors (M6, once per app lifetime)")
    app.state.modality_gate_service = ModalityGateService(
        embedder=embedder,
        positive_prompts=settings.modality_prompts_positive,
        negative_prompts=settings.modality_prompts_negative,
        softmax_temperature=settings.MODALITY_SOFTMAX_TEMPERATURE,
        modality_threshold=settings.MODALITY_THRESHOLD,
        retrieval_floor=settings.RETRIEVAL_FLOOR,
        # DR-5 / §6.1: the second, independent threshold on the top-1
        # similarity. Read here alongside the floor so one process cannot
        # hold a stale value of one and a fresh value of the other -- the
        # three bands are defined by the pair, not by either alone.
        projection_reject_threshold=settings.PROJECTION_REJECT_THRESHOLD,
    )
    # Shared with app/api/retrieval.py's gate step: the SAME embedder
    # instance the retrieval path uses, so the vector the gate judges and
    # the vector ChromaDB is queried with are guaranteed identical (M1).
    app.state.embedder = embedder

    app.state.vector_store = vector_store
    app.state.retrieval_service = RetrievalService(
        validator=validator,
        embedder=embedder,
        vector_store=vector_store,
        search_policy=search_policy,
    )
    app.state.label_voting_service = LabelVotingService()
    # Phase 21 §2.2: the arm comes from configuration, so an evaluation run is
    # a backend restart with an env override, not a different code path.
    app.state.context_builder = ContextBuilder(evidence_mode=settings.EVIDENCE_MODE)
    # Phase 22 v1.2 frozen §2(iii): the prompt's temporal term list is THE
    # SAME settings value ReportConsistencyService matches on, read here
    # once. A prompt that forbade a different set of words from the one
    # the checker looks for would make the measured temporal rate a
    # statement about two unrelated vocabularies.
    # Phase 23 (docs/phase23/plan.md §3.2): the checklist flag defaults False,
    # so with no env override this construction is exactly v1.2's.
    prompt_builder = PromptBuilder(
        temporal_terms=settings.consistency_temporal_terms,
        label_checklist=settings.PROMPT_LABEL_CHECKLIST_ENABLED,
        checklist_agreement_threshold=settings.DISCLAIMER_AGREEMENT_THRESHOLD,
    )
    app.state.prompt_builder = prompt_builder
    app.state.llm_orchestrator = LLMOrchestrator(
        prompt_builder=prompt_builder,
        llm_client=OllamaClient(),
        structural_validator=StructuralValidator(),
        transport_retry_count=settings.LLM_TRANSPORT_RETRY_COUNT,
        content_retry_count=settings.LLM_CONTENT_RETRY_COUNT,
    )
    app.state.response_validator = ResponseValidator()
    app.state.report_formatter = ReportFormatter()

    # --- Phase 22 v1.2 (frozen §3, §7): report self-consistency. ---
    #
    # The labeler is constructed ONCE here, like every other model in this
    # lifespan, because loading a BERT checkpoint per request would dominate
    # the ~9 ms the check itself costs.
    #
    # STARTUP MUST NOT FAIL BECAUSE OF THE LABELER. A missing or unreadable
    # checkpoint is a degraded-capability condition, not a broken server: the
    # contradiction check is dropped, the other two still run, and
    # ReportConsistencyService omits "contradiction" from checks_run so the
    # gap is recorded rather than hidden. Refusing to boot would take out
    # report generation entirely to protect a warning.
    section_labeler = None
    try:
        logger.info(
            "lifespan startup: loading ChexbertLabeler (should log exactly once per app lifetime)"
        )
        section_labeler = ChexbertLabeler(
            checkpoint_path=settings.CHEXBERT_CHECKPOINT_PATH,
            device=settings.CHEXBERT_DEVICE,
            max_length=settings.CHEXBERT_MAX_LENGTH,
            batch_size=settings.CHEXBERT_BATCH_SIZE,
        )
    except ChexbertUnavailableError as exc:
        # warning, not error: this is a supported configuration.
        logger.warning(
            "CheXbert labeler unavailable, continuing without it -- the "
            "findings/impression contradiction check will not run and will be "
            "omitted from checks_run (never reported as clean): %s",
            exc,
        )

    # Every constructor value comes off `settings` here, once, rather than
    # inside the service -- same rule as ModalityGateService above. The
    # transplant thresholds are deliberately NOT passed: they are Gate B's to
    # calibrate, and until then that check records its scores and emits no
    # violation (frozen §3.2). Passing a number now would be inventing one.
    app.state.consistency_service = ReportConsistencyService(
        temporal_terms=settings.consistency_temporal_terms,
        labeler=section_labeler,
    )
    app.state.questionnaire_provider = QuestionnaireTemplateProvider()
    app.state.deterministic_comparator = DeterministicComparator()
    app.state.password_hasher = Argon2PasswordHasher()
    app.state.token_service = JWTHandler()
    logger.info("lifespan startup complete")

    yield


app = FastAPI(title="RadAssist-RAG Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(retrieval_router)
app.include_router(generation_router)
app.include_router(questionnaire_router)
app.include_router(explainability_router)
app.include_router(patients_router)
app.include_router(comparisons_router)
app.include_router(reports_router)
app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(dashboard_router)
app.include_router(system_router)