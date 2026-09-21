"""
app/api/schemas.py
====================================================================
Pydantic response models for the API layer only -- these are HTTP-boundary
DTOs, not domain entities (app/domain/entities.py stays framework-free by
design; see that file's own docstring). Field-for-field, RetrieveResponse
mirrors the frozen response contract (development_log.md, Phase 4
"Input/output contracts") plus the Step 11 voted_labels extension, so
FastAPI's generated OpenAPI schema actually documents the real shape
instead of an unspecified object.

GenerateReportResponse (Phase 8) mirrors that same frozen-response-contract
discipline from the start -- typed models built up front, not retrofitted
after an untyped-dict gap like Phase 4 Step 12 had to fix.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# The status vocabulary lives in ONE module (see its docstring); imported
# here so the safe default below cannot drift from the derivation. That
# module imports from this one only lazily, inside a function, so there is
# no import cycle.
from app.api.consistency_status import STATUS_NOT_RUN

# Retrieval-k bounds, mirroring frontend/src/lib/doctor-defaults.ts. The
# collection is the IU/Indiana train split and the evidence panel is laid out
# for a handful of cases; a k outside this range is a data-entry mistake.
MIN_TOP_K = 1
MAX_TOP_K = 10

# Date-of-birth bounds. 1900 is comfortably before any living patient's birth
# year, and a DOB in the future is not a date of birth. Without these,
# `<input type="date">` happily accepts a six-digit year (Chrome allows up to
# 275760) and PatientService's date.fromisoformat() raises on it -- a reported
# QA finding that surfaced as an unhandled 500 rather than a field error.
MIN_DATE_OF_BIRTH = date(1900, 1, 1)


def validate_date_of_birth(value: str) -> str:
    """Parse-and-bound a YYYY-MM-DD date of birth, or raise ValueError.

    Shared by every endpoint that accepts a DOB (patient creation and
    name+DOB search), because both hand the string to
    date.fromisoformat() deeper in PatientService and both would
    otherwise raise there, unhandled, as a 500. Validating at the edge
    turns the same bad input into a 4xx that names the field -- and
    keeps a single definition of what a plausible DOB is, rather than
    one rule at the form and a different one (or none) at the API.
    """
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        # date.fromisoformat is itself the 4-digit-year check: "20k-10-02"
        # and "200000-10-02" both land here.
        raise ValueError("date_of_birth must be a real date in YYYY-MM-DD form.") from exc

    if parsed < MIN_DATE_OF_BIRTH:
        raise ValueError(f"date_of_birth must not be earlier than {MIN_DATE_OF_BIRTH.isoformat()}.")
    if parsed > date.today():
        raise ValueError("date_of_birth must not be in the future.")
    return value


class ServiceStatusResponse(BaseModel):
    status: str  # "ok" | "degraded" | "unreachable"
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    # Priority §16.1 (design_specification.md): real backend-half of the
    # §8.2 four-service status strip. Optional/nullable so existing
    # callers reading only `status` (e.g. the Dashboard's simple ok/
    # unreachable indicator) are unaffected -- purely additive.
    fastapi: ServiceStatusResponse | None = None
    ollama: ServiceStatusResponse | None = None
    chromadb: ServiceStatusResponse | None = None
    gpu: ServiceStatusResponse | None = None


class RetrievedCaseResponse(BaseModel):
    rank: int
    similarity: float
    study_uid: str
    primary_label: str
    label_set: str
    cluster_id: int
    findings: str
    impression: str
    image_path: str


class VotedLabelResponse(BaseModel):
    label: str
    vote_weight: float
    agreement: float


class RetrieveResponse(BaseModel):
    session_id: str
    retrieval_time_ms: int
    embedding_model: str
    embedding_version: str
    collection_name: str
    retrieved_cases: list[RetrievedCaseResponse]
    voted_labels: list[VotedLabelResponse]
    # Input Admission and Modality Gate, §7.4 S8: the backend calculates
    # the retrieval support category and the frontend SHOWS it. S9 forbids
    # the frontend from deriving it from retrieved_cases[0].similarity
    # itself, which is why the category ships as its own value rather than
    # being left implicit in data the client already has.
    #
    # `retrieval_support` is RetrievalSupport's string value
    # ("at_or_above_floor" / "below_floor"). `top1_similarity` is nullable
    # for a retrieval that returned no case at all -- null means the
    # measurement was never taken, which is not the same as 0.0.
    # `modality_score` is the M4 score of the image that passed the gate;
    # an image that failed never reaches this response at all (DR-1).
    modality_score: float | None = None
    retrieval_support: str | None = None
    top1_similarity: float | None = None


class ReportContentResponse(BaseModel):
    examination: str
    clinical_history: str
    technique: str
    findings: str
    impression: str
    recommendation: str
    disclaimer: str


class FormattedReportResponse(BaseModel):
    content: ReportContentResponse
    language: str
    report_date: str
    section_headers: dict[str, str]


class ValidationResponse(BaseModel):
    is_clean: bool
    warnings: list[str]


class ConsistencyViolationResponse(BaseModel):
    """One self-consistency problem found in a generated report (Phase 22
    v1.2, frozen §3). `severity` is "error" or "warning" -- a violation
    located in FINDINGS is always "warning", because the Gate C retry
    regenerates impression/recommendation and never findings, so an error
    there could not be acted on."""

    check: str
    severity: str
    field: str
    detail: str
    evidence: dict


class ConsistencyResponse(BaseModel):
    """Phase 22 v1.2 (frozen §3/§5). ADDITIVE: every pre-existing field on
    the responses that carry this block, including `validation.is_clean`, is
    unchanged.

    `status` is the one value a UI should branch on, and it is derived in
    exactly one place (app/api/consistency_status.derive_consistency_status):
    "not_run" | "clean" | "violations".

    `checks_run` is what makes "not_run" distinguishable from "clean" and
    must be surfaced, not just used internally: a report where only some
    checks ran reports status "clean" if those checks found nothing, and
    `checks_run` is the only field that says which checks earned that
    verdict. A UI that shows the status without the check list is telling
    the reader less than the record knows.

    THE UI CONTRACT (frozen §3.4/§8.8): status "not_run" must render as
    "consistency checks not run" and must NEVER render as a clean or passed
    state, and it must be visually distinct from "clean". Every Bengali
    report is "not_run", because all three checks are English-only."""

    status: str
    checks_run: list[str] = []
    violations: list[ConsistencyViolationResponse] = []
    retry_count: int | None = None


def _not_run_consistency() -> ConsistencyResponse:
    """The default for the block below.

    Defaulted so the addition is genuinely additive -- every existing
    construction of GenerateReportResponse/ReportDetailResponse keeps
    working unchanged -- and defaulted to NOT_RUN specifically, because a
    caller that forgets to populate it then under-claims rather than
    over-claims. A default of "clean" would let an omission read as an
    assurance."""
    return ConsistencyResponse(status=STATUS_NOT_RUN, checks_run=[], violations=[], retry_count=None)


class GenerationMetadataResponse(BaseModel):
    llm_model: str
    llm_temperature: float
    embedding_model: str
    embedding_version: str
    collection_name: str


class GenerateReportResponse(BaseModel):
    report_id: str
    session_id: str
    formatted_report: FormattedReportResponse
    validation: ValidationResponse
    generation_metadata: GenerationMetadataResponse
    # Phase 22 v1.2, additive. `validation` above is unchanged and still
    # carries ResponseValidator's own advisory warnings -- the two answer
    # different questions and neither replaces the other.
    consistency: ConsistencyResponse = Field(default_factory=_not_run_consistency)


class QuestionnaireQuestionResponse(BaseModel):
    key: str
    text: str
    input_type: str


class QuestionnaireResponse(BaseModel):
    session_id: str
    based_on_label: str
    questions: list[QuestionnaireQuestionResponse]


class ExplanationResponse(BaseModel):
    id: str
    report_id: str
    question: str
    answer: str
    created_at: str
    doctor_id: str | None = None


class PatientResponse(BaseModel):
    id: str
    patient_code: str
    name: str
    date_of_birth: str
    gender: str


class PatientHistoryReportResponse(BaseModel):
    id: str
    language: str
    status: str
    ai_content: ReportContentResponse
    created_at: str
    doctor_id: str | None = None


class ComparisonFactsResponse(BaseModel):
    previous_report_id: str
    current_report_id: str
    resolved_findings: list[str]
    persistent_findings: list[str]
    new_findings: list[str]
    days_between_studies: int


class ComparisonResponse(BaseModel):
    id: str
    patient_id: str
    previous_report_id: str
    current_report_id: str
    facts: ComparisonFactsResponse
    narrative: str
    created_at: str
    doctor_id: str | None = None


class ReportAuditLogEntryResponse(BaseModel):
    """Phase 17: one row per successful PATCH /reports/{id} edit. Nested on
    ReportDetailResponse rather than a separate endpoint -- same "embed the
    related list on the detail response" convention this schema already
    uses for retrieved_cases, not a new precedent."""

    id: str
    doctor_id: str
    action: str
    at: str


class ReportDetailResponse(BaseModel):
    """Phase 12: GET /reports/{report_id} -- reuses ReportContentResponse/
    ValidationResponse/GenerationMetadataResponse/RetrievedCaseResponse
    rather than duplicating their field definitions, same discipline as
    every prior schema reuse in this project. patient_id is nullable --
    a report's underlying RetrievalSession may predate Phase 11's patient
    linkage, or may never have had a patient_id supplied.

    Phase 17 additions (additive only): `content` now sources
    final_content (what the report currently says); `ai_draft_content` is
    new, the immutable AI draft, for the frontend's "Restore AI Draft"
    action. `finalized_at`/`finalized_by` are nullable -- only set once a
    report has actually been finalized. `audit_log` is the edit history,
    oldest first."""

    report_id: str
    session_id: str
    patient_id: str | None
    content: ReportContentResponse
    ai_draft_content: ReportContentResponse
    language: str
    status: str
    validation: ValidationResponse
    generation_metadata: GenerationMetadataResponse
    report_date: str
    created_at: str
    retrieved_cases: list[RetrievedCaseResponse]
    doctor_id: str | None = None
    finalized_at: str | None = None
    finalized_by: str | None = None
    audit_log: list[ReportAuditLogEntryResponse] = []
    # Input Admission and Modality Gate §7.4 (S8/S9): served straight from
    # the stored reports.retrieval_support / reports.top1_similarity
    # columns S5 wrote at generation time -- NOT recomputed here from
    # retrieved_cases. S9 forbids the frontend from deriving the category
    # from raw similarity scores, and a backend that recomputed it on
    # every read would have the same defect one layer down: the value a
    # radiologist sees could drift away from the value stored with the
    # report the moment the collection or the floor changed.
    #
    # Both nullable: a report generated before this column existed has no
    # recorded support state, and null says so. The frontend must render
    # that as "not recorded", never as below_floor.
    retrieval_support: str | None = None
    top1_similarity: float | None = None
    # Phase 22 v1.2 (frozen §5), additive: served straight from the stored
    # reports.consistency_* columns written at generation time, never
    # recomputed on read -- the same discipline as retrieval_support above,
    # and for the same reason. A pre-v1.2 row has all three columns NULL and
    # therefore reports status "not_run", never "clean".
    consistency: ConsistencyResponse = Field(default_factory=_not_run_consistency)


class ReportListItemResponse(BaseModel):
    """GET /reports -- ownership-scoped, recency-ordered list. General
    enough to later back a full My Reports page, not a Dashboard-only
    shape: no evidence/agreement (that needs a real vector-store query
    per report, a real cost a list endpoint shouldn't impose on every
    caller -- see ReportListItem's own docstring), but content/
    ai_draft_content are both included so a caller can compute Phase 18's
    Report Edit Percentage via the existing computeReportDiff() with zero
    new logic."""

    report_id: str
    patient_id: str | None
    patient_name: str | None
    patient_code: str | None
    status: str
    report_date: str
    created_at: str
    content: ReportContentResponse
    ai_draft_content: ReportContentResponse


class RegenerateSectionResponse(BaseModel):
    """Phase 19: POST /reports/{report_id}/regenerate-section. `candidate`,
    not `content` -- this codebase already overloads "content" heavily
    (ReportContent, final_content, ai_draft_content); naming this field
    distinctly makes "not yet persisted" part of the name itself, not just
    a comment (phase19_section_regeneration_architecture.md's Endpoints
    section). Nothing about this call is written to final_content or
    logged anywhere -- accepting the candidate is a normal
    PATCH /reports/{report_id} call, made separately by the caller.

    `context_incomplete` is true only when this report predates
    questionnaire_answers/clinical_notes persistence (both NULL together,
    Phase 19 Decision 4) -- the candidate was generated from retrieval
    evidence alone, without whatever questionnaire answers or clinical
    notes the ORIGINAL generation may have used. The frontend surfaces
    this as an honest warning, not a silent gap."""

    field: str
    candidate: str
    context_incomplete: bool
    # Phase 22 v1.2 (frozen §3): the candidate is checked before it is
    # returned, so a doctor sees the consistency verdict on the text they
    # are being offered. NOT written to the report's consistency_* columns
    # -- those describe the generation-time AI draft, and this candidate is
    # not persisted anywhere until the doctor accepts it via PATCH.
    consistency: ConsistencyResponse = Field(default_factory=_not_run_consistency)


class DoctorResponse(BaseModel):
    """Phase 13. Deliberately excludes password_hash -- never serialized
    back to any client, registering or otherwise.

    Phase 16: bmdc_number/default_* are self-only fields (Settings/Profile).
    They belong ONLY here, never on DoctorPublicResponse below -- same
    reasoning that already kept email/created_at out of that one."""

    id: str
    email: str
    full_name: str
    created_at: str
    bmdc_number: str | None = None
    default_top_k: int | None = None
    default_language: str | None = None
    default_questionnaire_skip: bool | None = None
    default_rail_state: str | None = None
    default_export_format: str | None = None


class UpdateProfileRequest(BaseModel):
    """Phase 16: PATCH /auth/me. Every field optional -- a partial update,
    not a full replace; omitted fields are left untouched. email is
    deliberately not here -- no re-verification workflow exists for
    changing it.

    QA fix: default_top_k is now bounded. It was previously an unconstrained
    int, and since nothing read it back the absence of validation was
    invisible; now that the upload flow honours it, an out-of-range k would
    reach a real ChromaDB query. The client clamps to the same MIN/MAX
    (frontend/src/lib/doctor-defaults.ts), but a client-side bound is a
    convenience, not a guarantee -- this is the one that holds.
    default_language is likewise restricted to the two languages the
    dictionaries actually define; anything else would silently fall back to
    English at render time with no error, the same quiet failure the i18n
    parity gate exists to prevent."""

    full_name: str | None = None
    bmdc_number: str | None = None
    default_top_k: int | None = Field(default=None, ge=MIN_TOP_K, le=MAX_TOP_K)
    default_language: Literal["en", "bn"] | None = None
    default_questionnaire_skip: bool | None = None
    default_rail_state: str | None = None
    default_export_format: str | None = None


class DoctorPublicResponse(BaseModel):
    """Phase 15: GET /doctors/{doctor_id}, for rendering another doctor's
    name on an OwnershipChip. Deliberately narrower than DoctorResponse --
    excludes email/created_at, not just password_hash -- a doctor's own
    identity is fully visible to themselves (GET /auth/me), but the
    shared-registry read model (§2 of phase13_auth_architecture.md) only
    needs a name to attribute someone else's work, not their contact
    details. Phase 16: bmdc_number/default_* are likewise excluded here on
    purpose -- self-only data, never exposed via the public
    name-resolution endpoint."""

    id: str
    full_name: str


class RegisterResponse(BaseModel):
    doctor: DoctorResponse
    token: str


class LoginResponse(BaseModel):
    token: str


class LogoutResponse(BaseModel):
    success: bool


class DashboardStatsResponse(BaseModel):
    """Phase 15. Real counts, per frontend/CLAUDE.md's explicit
    instruction not to invent a placeholder stat."""

    my_reports: int
    total_reports: int
    my_patients: int
    total_patients: int
    examinations_today: int
    awaiting_review: int
    oldest_awaiting_review_report_id: str | None = None
    oldest_awaiting_review_report_date: str | None = None


class SystemStatsResponse(BaseModel):
    """Phase 16: GET /system/stats, design_specification.md §8.16's
    "storage & privacy" + index-stats section.

    original_images_stored is a STRUCTURAL guarantee, not a live query --
    confirmed by reading app/api/retrieval.py: POST /retrieve is the only
    file-upload endpoint in this backend, and the raw upload only ever
    exists as a tempfile.NamedTemporaryFile, synchronously deleted in
    _saved_upload's `finally` block before the request even returns.
    There is no directory this system could count originals in, so this
    is always 0 by construction, not a coincidence of current usage."""

    masked_images_stored: int
    original_images_stored: int
    index_size: int
    embedding_model: str
    embedding_version: str
    collection_name: str
    # Phase 21 §2.2. Additive, and reported so an ablation run can VERIFY which
    # arm the live backend is actually in rather than trusting the operator to
    # have restarted it correctly. Writing one arm's output into another arm's
    # directory would silently corrupt the paired comparison, and nothing else
    # in the system could detect it afterwards. Defaults to "full" in
    # production, where it is simply a statement of normal configuration.
    evidence_mode: str