"""
app/services/report_generation_service.py
====================================================================
Orchestrates the full Phase 8 chain, per the frozen sequence diagram:
fetch session evidence -> reconstruct cases -> vote -> build context ->
generate -> semantically validate -> format -> persist. Pure sequencing
over its injected collaborators -- no business logic, no clinical
judgment, no prompt/report content decisions of its own -- same discipline
as RetrievalService (Phase 4).

Exception propagation policy (deliberate, stated explicitly): LLMTransportError
and LLMGenerationValidationError from llm_orchestrator.generate_draft() are
NOT caught here -- they propagate unchanged to the caller (Step 7's API
route). This mirrors Phase 4's precedent exactly: RetrievalService lets
ValueError propagate up to app/api/retrieval.py, the one place that knows
how to translate a domain exception into an HTTP status code. Catching and
re-wrapping here would duplicate that translation responsibility in two
places instead of one.

Reproducibility-metadata gap, flagged rather than silently worked around:
RetrievalSession (Phase 4's frozen schema) does NOT persist collection_name/
embedding_model/embedding_version per-session -- only Settings holds these
(as the current config, not necessarily what was true at the original
retrieval time if config has changed since). Sourced from Settings here,
consistent with how /retrieve's own response and Phase 7's integration test
both already source the identical values -- not a new precedent, but worth
naming as a real limitation: if the collection/model config changes between
a session's original retrieval and a later report-generation call, the
persisted reproducibility metadata reflects the LATER config, not
necessarily what actually produced that session's retrieved cases.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.entities import (
    FormattedReport,
    GenerationMetadata,
    ReportStatus,
    RetrievalMetadata,
    SemanticValidationResult,
)
from app.domain.interfaces import (
    IContextBuilder,
    ILabelVoter,
    ILLMOrchestrator,
    IReportConsistencyChecker,
    IReportFormatter,
    IResponseValidator,
    IVectorStore,
)
from app.models.report import ReportRecord
from app.models.retrieved_evidence import RetrievedEvidence
from app.services.evidence_disclaimer import render_disclaimer
from app.services.session_reconstruction import reconstruct_session_evidence

logger = logging.getLogger(__name__)

# Frozen architecture §2(iii), the v1.2 scope decision, stated ONCE here and
# imported by every caller that needs it rather than written as a bare False
# at each call site.
#
# v1.2 does NOT plumb real prior-study state into generation. ClinicalContext
# has no such field and priors live in ComparisonService, which never
# generates a report (frozen §3.5). So the generation path always reports "no
# prior study", which is correct for 100% of evaluation-harness cases and for
# every first-visit report, and which errs in the safe direction: it can
# suppress comparison language that would have been legitimate for a patient
# who DOES have a prior, but it can never permit language that is
# unsupported. Recorded as a known limitation in frozen §8.6, deferred to
# future work in frozen §9.
HAS_PRIOR_STUDY_V1_2 = False


class ReportGenerationService:
    def __init__(
        self,
        db: Session,
        vector_store: IVectorStore,
        label_voting_service: ILabelVoter,
        context_builder: IContextBuilder,
        llm_orchestrator: ILLMOrchestrator,
        response_validator: IResponseValidator,
        report_formatter: IReportFormatter,
        modality_gate_service=None,
        consistency_service: IReportConsistencyChecker | None = None,
    ) -> None:
        self._db = db
        self._vector_store = vector_store
        self._label_voting_service = label_voting_service
        self._context_builder = context_builder
        self._llm_orchestrator = llm_orchestrator
        self._response_validator = response_validator
        self._report_formatter = report_formatter
        # Input Admission and Modality Gate §7: the ONE implementation of
        # S1 ("calculate the retrieval support category from the top-1
        # similarity and the retrieval floor") lives on ModalityGateService
        # and is reused here rather than reimplemented, so /retrieve's
        # M7-M9 category and the report's stored S5 category can never be
        # computed by two rules that drift apart.
        #
        # Defaulted to None so the eight existing unit tests that construct
        # this service with seven positional collaborators keep working
        # unchanged. A None gate means the support signal is simply not
        # computed and both columns stay NULL -- which is the same honest
        # "no recorded support state" that pre-migration rows carry, not a
        # silent fallback to some assumed category.
        self._modality_gate_service = modality_gate_service
        # Phase 22 v1.2 (frozen §3). Defaulted to None for the same reason
        # modality_gate_service is: the existing unit tests construct this
        # service with seven positional collaborators and must keep working
        # unchanged. A None checker means the check simply does not run and
        # all three consistency columns stay NULL -- the same honest "no
        # recorded state" a pre-v1.2 row carries, never a silent clean
        # verdict.
        #
        # GATE A IS OBSERVATIONAL. This service calls check() and persists
        # the result. It does NOT act on it: there is no retry, nothing is
        # blocked, and no generated text is altered by it. The retry is
        # Gate C (frozen §4).
        self._consistency_service = consistency_service

    def generate(
        self,
        session_id: str,
        language: str,
        questionnaire_answers: dict[str, str] | None = None,
        clinical_notes: str = "",
    ) -> tuple[
        uuid.UUID,
        FormattedReport,
        SemanticValidationResult,
        GenerationMetadata,
        tuple[list | None, list | None, int | None],
    ]:
        # Phase 9 additive extension: questionnaire_answers/clinical_notes
        # default to None/"" (same null-handling convention as
        # PromptBuilder's own build() defaults from Phase 6 --
        # None-then-convert for the mutable dict, never a mutable literal
        # as the actual default argument value). Omitting both entirely
        # must be byte-identical to Phase 8's existing behavior -- see
        # test_no_questionnaire_data_produces_byte_identical_behavior_to_phase_8.
        questionnaire_answers = questionnaire_answers or {}
        # Phase 19: clinical_notes gets the SAME normalization, added here
        # (not just relied on via the API layer's non-Optional `str` type)
        # so the two persisted columns are structurally guaranteed non-None
        # together, regardless of caller -- not merely true for the one
        # real caller today. Closes a real gap found during Phase 19: this
        # line was missing, so the guarantee previously depended entirely
        # on GenerateReportRequest's Pydantic type, not on this service's
        # own code.
        clinical_notes = clinical_notes or ""

        # Shared with QuestionnaireService (Phase 9) -- see
        # session_reconstruction.py's own docstring for why this is
        # extracted rather than duplicated.
        retrieval_session, retrieved_cases, voted_labels = reconstruct_session_evidence(
            self._db, self._vector_store, self._label_voting_service, session_id
        )

        retrieval_metadata = RetrievalMetadata(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_model=settings.CHROMA_EMBEDDING_MODEL,
            embedding_version=settings.CHROMA_EMBEDDING_VERSION,
            retrieved_at=retrieval_session.created_at.isoformat() if retrieval_session.created_at else "",
        )
        context = self._context_builder.build(
            retrieved_cases,
            voted_labels,
            questionnaire_answers=questionnaire_answers,
            clinical_notes=clinical_notes,
            retrieval_metadata=retrieval_metadata,
        )

        # LLMTransportError / LLMGenerationValidationError intentionally
        # NOT caught here -- see module docstring's propagation policy.
        content = self._llm_orchestrator.generate_draft(context, language)

        validation_result = self._response_validator.validate_semantic(
            content, context.evidence_summary, voted_labels
        )

        # --- Phase 22 v1.2 (frozen §3): report self-consistency. ---
        #
        # Placed exactly here, AFTER validate_semantic() and BEFORE
        # render_disclaimer(), per the frozen §3 pipeline diagram. After the
        # validator so that validator's subject stays "the model's clinical
        # claims against retrieved evidence" and it is never handed
        # post-processed text; before the disclaimer so the disclaimer is
        # rendered from the same content the check just judged.
        #
        # The report id is generated up front rather than left to
        # ReportRecord's uuid4 default, purely so a check that raises can be
        # logged against the report it belongs to -- otherwise the only
        # identifier available at this point is the session.
        report_id = uuid.uuid4()
        consistency_violations, consistency_checks_run, consistency_retry_count = (
            self._run_consistency_check(
                report_id, content, context, retrieved_cases, language
            )
        )

        # --- Input Admission and Modality Gate §7: the evidence support
        # signal (S1, S2, S5). ---
        #
        # The top-1 similarity is read back out of `retrieved_evidence`,
        # NOT off the reconstructed `retrieved_cases`. That is not a
        # roundabout way of getting the same number: reconstruct_session_
        # evidence() fetches cases through IVectorStore.get_by_ids(), an
        # ID-based fetch with no ranking, which documents that it forces
        # distance 0.0 and therefore reports similarity 1.0 for every case.
        # Using that value would record every single report as being at or
        # above the floor. The real, ranked similarity from the original
        # query survives only in the retrieved_evidence rows Phase 4
        # persisted at /retrieve time -- which is also what S5 means by
        # storing the evidence state as it was, rather than as it can be
        # re-derived later.
        top1_similarity = self._top1_similarity(retrieval_session.id)
        top_agreement = voted_labels[0].agreement if voted_labels else None

        retrieval_support = None
        if self._modality_gate_service is not None:
            retrieval_support = self._modality_gate_service.classify_retrieval_support(
                top1_similarity
            )

            # S2 + S3: the disclaimer is rendered here, on the server, from
            # a parameterised template fed BOTH signals -- replacing the
            # text the LLM wrote into this field. §7.1's Rule is that the
            # disclaimer must read both signals; a model-authored
            # disclaimer reads whichever it feels like, and the Phase 7 dev
            # log's real sample ("Clinical uncertainty due to low agreement
            # score (0.60)") shows it reading only agreement -- the exact
            # single-signal failure §7.1's Warning describes.
            #
            # This runs AFTER validate_semantic() on purpose. That
            # validator's subject is the model's clinical claims in
            # findings/impression; handing it a server-authored string that
            # no model produced would be validating this system's own
            # template output as though it were generated content.
            content.disclaimer = render_disclaimer(
                agreement=top_agreement,
                support=retrieval_support,
                top1_similarity=top1_similarity,
                retrieval_floor=self._modality_gate_service.retrieval_floor,
                agreement_threshold=settings.DISCLAIMER_AGREEMENT_THRESHOLD,
                language=language,
            )

        # report_date generated HERE, not inside ReportFormatter (which must
        # stay a pure, deterministic function -- Phase 8 Decision 4).
        report_date = datetime.now(timezone.utc).date().isoformat()

        formatted_report = self._report_formatter.format(content, language, report_date)

        # Phase 17: ai_draft_content is the immutable AI draft; final_content
        # starts as a deep copy (Decision 3) that PATCH /reports/{id} is the
        # only thing that ever touches. asdict(content) is called twice
        # deliberately, not once with the result assigned to both fields --
        # each call builds a genuinely independent dict, so there is no
        # shared-reference risk if either field is later mutated in place
        # rather than reassigned wholesale.
        # Phase 19 Decision 4's resolution: persisted from here on, so an
        # existing report's original generation context can be fully
        # reconstructed for section regeneration. questionnaire_answers is
        # already normalized to a real dict (never None) by line 93 above;
        # clinical_notes is already guaranteed a real str (never None) by
        # GenerateReportRequest's own non-Optional `str` typing at the API
        # boundary (app/api/generation.py) -- so this write always
        # persists two real, non-null values, never exactly one of them.
        # Pre-migration rows stay NULL on both (no backfill, per that
        # migration's own docstring); this is the only code path that ever
        # writes either column, so the two can never independently drift
        # to one-null-one-not.
        report_record = ReportRecord(
            id=report_id,
            session_id=retrieval_session.id,
            language=language,
            status=ReportStatus.AI_DRAFT,
            ai_draft_content=asdict(content),
            final_content=asdict(content),
            validation_warnings=list(validation_result.warnings),
            report_date=report_date,
            llm_model=settings.OLLAMA_MODEL,
            llm_temperature=settings.LLM_TEMPERATURE,
            embedding_model=retrieval_metadata.embedding_model,
            embedding_version=retrieval_metadata.embedding_version,
            collection_name=retrieval_metadata.collection_name,
            questionnaire_answers=questionnaire_answers,
            clinical_notes=clinical_notes,
            # S5: stored WITH the report, at generation time. Written from
            # the same two values the disclaimer above was rendered from,
            # not re-derived, so the stored category and the sentence the
            # radiologist reads can never describe different measurements.
            retrieval_support=retrieval_support.value if retrieval_support is not None else None,
            top1_similarity=top1_similarity,
            # S7 / D4: the other two fields of the evidence snapshot,
            # written from the SAME `voted_labels` this method already
            # voted, built the context from, validated against and
            # rendered the disclaimer from -- not re-voted here, so the
            # stored snapshot and the report's own reasoning cannot
            # describe different votes.
            #
            # The whole descending-sorted list is stored, not just the
            # top entry: the disclaimer, the semantic validator and the
            # frontend each read different parts of it (see the
            # migration's docstring).
            voted_labels=[asdict(v) for v in voted_labels],
            agreement=top_agreement,
            # Phase 22 v1.2 (frozen §5). NULL and [] are different states and
            # the three values above were built to preserve that -- see
            # _run_consistency_check() for which case writes which.
            consistency_violations=consistency_violations,
            consistency_checks_run=consistency_checks_run,
            consistency_retry_count=consistency_retry_count,
        )
        self._db.add(report_record)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        # Populated from the exact same values just persisted onto
        # report_record (not re-queried from the DB) -- one computation,
        # reused, rather than a second, potentially-inconsistent read.
        generation_metadata = GenerationMetadata(
            llm_model=report_record.llm_model,
            llm_temperature=report_record.llm_temperature,
            embedding_model=report_record.embedding_model,
            embedding_version=report_record.embedding_version,
            collection_name=report_record.collection_name,
        )

        # report_id returned as uuid.UUID (its native type here, same as
        # RetrievalSession.id/ReportRecord.id throughout the service layer)
        # -- consistent with Phase 4's own boundary convention: the domain/
        # service layer works in real uuid.UUID objects, and only the API
        # layer (Step 7) converts to str for JSON serialization, same as
        # app/api/retrieval.py's _build_response() does for session_id.
        # Phase 22 v1.2: the three values EXACTLY AS PERSISTED are returned as
        # a fifth element, rather than the ConsistencyResult they were built
        # from. The route derives the response status from these, so what a
        # caller sees on POST /generate-report is derived from the same values
        # GET /reports/{id} will later read out of the row -- the two cannot
        # describe the same report differently. Returning them also avoids a
        # redundant re-read of the row that was just written.
        return (
            report_record.id,
            formatted_report,
            validation_result,
            generation_metadata,
            (consistency_violations, consistency_checks_run, consistency_retry_count),
        )

    def _run_consistency_check(self, report_id, content, context, retrieved_cases, language):
        """Returns (violations, checks_run, retry_count) ready to persist.

        GENERATION MUST NEVER FAIL BECAUSE OF THE CHECKER. Everything below
        is subordinate to that: this method has no raising path, and its
        worst case is three NULLs and a log line. A self-consistency warning
        is a safety improvement, and a safety improvement that can take down
        report generation is a net loss -- the doctor loses the report
        entirely instead of receiving one with an unchecked caveat.

        The three cases, per the frozen §5 NULL-vs-[] distinction:

          checks ran (English)   -> ([...], [...], 0)
              A real list, possibly empty. An empty list here means the
              checks ran and found nothing, and checks_run names which ones
              earned that.

          zero checks (non-English) -> (None, [], 0)
              Deliberately asymmetric, and specified this way in the step
              brief: checks_run == [] is a positive statement ("we know zero
              checks were applicable"), while violations == NULL is the
              absence of a violation record. Writing violations == [] here
              would assert the report was examined and found clean, which is
              exactly the false assurance frozen §3.4/§8.8 forbids for
              Bengali reports.

          checker raised         -> (None, None, None)
              All three NULL: nothing is known, and nothing is claimed. The
              exception is logged with the report id.

        retry_count is 0 whenever the checker ran at all. Gate A performs no
        retry, so 0 is a fact about this run, not a placeholder.
        """
        if self._consistency_service is None:
            # No checker wired: same honest "no recorded state" as a
            # pre-v1.2 row. Not logged as an error -- running without the
            # checker is a supported configuration in Gate A.
            return None, None, None

        started = time.perf_counter()
        try:
            result = self._consistency_service.check(
                content,
                context,
                retrieved_cases,
                language,
                # Frozen §2(iii): see HAS_PRIOR_STUDY_V1_2's own comment.
                HAS_PRIOR_STUDY_V1_2,
            )
        except Exception:
            # Deliberately broad. The checker calls into a neural labeler and
            # regex matching over model-authored text; enumerating every
            # failure it could have is not possible, and any one of them
            # taking down generation would be worse than not checking.
            logger.exception(
                "consistency check failed for report %s; report is still generated "
                "and persisted, and all three consistency columns stay NULL",
                report_id,
            )
            return None, None, None

        # Logged per request so the check's real cost is observable in a
        # running system, not only in a benchmark. INFO because it is one
        # short line per report, and because the whole point of Gate A is
        # that this path can be watched while it changes nothing.
        logger.info(
            "consistency check for report %s: %.1f ms, language=%s, checks_run=%s, violations=%d",
            report_id,
            (time.perf_counter() - started) * 1000.0,
            language,
            list(result.checks_run),
            len(result.violations),
        )

        if not result.checks_run:
            # Non-English: zero checks were applicable.
            return None, list(result.checks_run), result.retry_count

        return (
            [asdict(v) for v in result.violations],
            list(result.checks_run),
            result.retry_count,
        )

    def _top1_similarity(self, session_id: uuid.UUID) -> float | None:
        """The rank-1 similarity actually measured by the original
        /retrieve call (§7 M7's "top-1 similarity score from the
        RetrievalService").

        Ordered by rank rather than by max(similarity): rank 1 IS the top-1
        result by definition, SimilaritySearchPolicy having already sorted
        descending before these rows were written. Reading the rank is
        reading what was recorded; recomputing a max would be a second,
        independently-derivable opinion about the same fact.

        None when the session has no evidence rows at all -- a retrieval
        that returned nothing. ModalityGateService.classify_retrieval_
        support() maps that to BELOW_FLOOR, since no retrieved case meets
        the threshold when there is no retrieved case.
        """
        row = (
            self._db.query(RetrievedEvidence)
            .filter(RetrievedEvidence.session_id == session_id)
            .order_by(RetrievedEvidence.rank)
            .first()
        )
        return row.similarity if row is not None else None
