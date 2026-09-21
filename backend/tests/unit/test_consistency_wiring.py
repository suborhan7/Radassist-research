"""
Phase 22 Gate A / Step A4: ReportConsistencyService wiring, observational mode.

Frozen architecture: docs/phase22/fix_architecture_v1.2_FROZEN.md §3-§5
(frozen at docs commit 810240ea).

Same fixture conventions as test_report_generation_service.py: a real,
throwaway in-memory SQLite session with every non-DB collaborator faked.

THE KEY TEST in this module is test_generated_output_is_byte_identical_*.
Gate A's entire claim is that wiring the checker changes nothing a doctor
reads, so that claim is asserted directly rather than argued: the same fake
LLM output is generated twice, once with a real consistency service injected
and once without, and the persisted content and the formatted report are
compared byte for byte. If that test ever fails, the checker has stopped
being observational and the Phase 21 results can no longer be attributed to
the tagged system.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.consistency_status import (
    STATUS_CLEAN,
    STATUS_NOT_RUN,
    STATUS_VIOLATIONS,
    build_consistency_response,
    derive_consistency_status,
)
from app.database.base import Base
from app.domain.entities import (
    ClinicalContext,
    EvidenceSummary,
    FormattedReport,
    ReportContent,
    RetrievalStats,
    RetrievedCase,
    SemanticValidationResult,
)
from app.models.report import ReportRecord
from app.models.retrieval_session import RetrievalSession
from app.models.retrieved_evidence import RetrievedEvidence
from app.services.report_consistency_service import (
    CHECK_CONTRADICTION,
    CHECK_TEMPORAL,
    CHECK_TRANSPLANT,
    CLASS_BLANK,
    CLASS_NEGATIVE,
    CLASS_POSITIVE,
    ReportConsistencyService,
)
from app.services.report_generation_service import (
    HAS_PRIOR_STUDY_V1_2,
    ReportGenerationService,
)

TERMS = ("stable", "unchanged", "interval", "again", "redemonstrated",
         "persistent", "previously", "compared with", "new")
CONDITIONS = ("Cardiomegaly", "Lung Opacity", "No Finding")


# ----------------------------------------------------------------------
# fakes (mirroring test_report_generation_service.py)
# ----------------------------------------------------------------------

class FakeVectorStore:
    def __init__(self, cases_by_uid):
        self.cases_by_uid = cases_by_uid

    def get_by_ids(self, uids):
        return [self.cases_by_uid[uid] for uid in uids]

    def query(self, embedding, top_k):
        raise NotImplementedError

    def upsert(self, uid, embedding, metadata):
        raise NotImplementedError


class FakeLabelVoter:
    def __init__(self, voted_labels):
        self.voted_labels = voted_labels

    def vote(self, retrieved):
        return self.voted_labels


class FakeContextBuilder:
    def __init__(self, context):
        self.context = context

    def build(self, retrieved, voted_labels, questionnaire_answers=None,
              clinical_notes="", retrieval_metadata=None):
        return self.context


class FakeLLMOrchestrator:
    def __init__(self, content):
        self.content = content

    def generate_draft(self, context, language):
        return self.content


class FakeResponseValidator:
    def __init__(self, result):
        self.result = result

    def validate_semantic(self, content, evidence_summary, voted_labels):
        return self.result


class FakeReportFormatter:
    def format(self, content, language, report_date):
        return FormattedReport(
            content=content, language=language, report_date=report_date, section_headers={}
        )


class FakeLabeler:
    def __init__(self, findings_row, impression_row):
        self._rows = (tuple(findings_row), tuple(impression_row))
        self.calls = []

    @property
    def conditions(self):
        return CONDITIONS

    def label(self, texts):
        self.calls.append(list(texts))
        return self._rows


class RaisingConsistencyService:
    """Satisfies the Protocol shape, then fails. Generation must survive it."""

    def __init__(self):
        self.calls = 0

    def check(self, content, context, retrieved_cases, language, has_prior_study):
        self.calls += 1
        raise RuntimeError("labeler exploded")


class RecordingConsistencyService:
    """Wraps a real service so the call arguments can be asserted."""

    def __init__(self, inner):
        self._inner = inner
        self.calls = []

    def check(self, content, context, retrieved_cases, language, has_prior_study):
        self.calls.append(
            {"content": content, "language": language, "has_prior_study": has_prior_study,
             "n_cases": len(list(retrieved_cases))}
        )
        return self._inner.check(content, context, retrieved_cases, language, has_prior_study)


# ----------------------------------------------------------------------
# harness
# ----------------------------------------------------------------------

def _engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


def _db():
    return sessionmaker(bind=_engine())()


def _seed(db: SASession, uids):
    session_id = uuid.uuid4()
    db.add(RetrievalSession(
        id=session_id, query_image_path="q.png", top_k=len(uids),
        min_similarity=0.0, num_results=len(uids), retrieval_time_ms=10,
    ))
    db.add_all([
        RetrievedEvidence(session_id=session_id, study_uid=uid, rank=rank, similarity=0.9)
        for rank, uid in enumerate(uids, start=1)
    ])
    db.commit()
    return session_id


def _context():
    return ClinicalContext(
        retrieved_cases=(), voted_labels=(), questionnaire_answers={}, clinical_notes="",
        evidence_summary=EvidenceSummary(
            top_retrieved_case=None, findings_evidence=(), impressions_evidence=(),
            retrieval_stats=RetrievalStats(0, 0, 0, 0.0, 0.0, 0.0, 0, 0),
            retrieval_metadata=None, label_evidence=(),
        ),
    )


VALIDATION = SemanticValidationResult(
    missing_findings=False, missing_impression=False, unsupported_terms=(),
    top_label_unreflected=False, warnings=("w",), is_clean=False,
)

CLEAN_CONTENT = ReportContent(
    examination="Chest X-ray", clinical_history="None", technique="PA",
    findings="The lungs are clear. No focal consolidation.",
    impression="No acute cardiopulmonary abnormality.",
    recommendation="No follow-up required.", disclaimer="d",
)

TEMPORAL_CONTENT = ReportContent(
    examination="Chest X-ray", clinical_history="None", technique="PA",
    findings="The lungs are clear.",
    impression="Stable cardiomegaly without overt pulmonary edema.",
    recommendation="No follow-up required.", disclaimer="d",
)


def _service(db, content, consistency_service=None, cases=None):
    cases = cases if cases is not None else {
        "u1": RetrievedCase(source_uid="u1", similarity=0.9, findings="nf", impression="ni")
    }
    return ReportGenerationService(
        db=db,
        vector_store=FakeVectorStore(cases),
        label_voting_service=FakeLabelVoter([]),
        context_builder=FakeContextBuilder(_context()),
        llm_orchestrator=FakeLLMOrchestrator(content),
        response_validator=FakeResponseValidator(VALIDATION),
        report_formatter=FakeReportFormatter(),
        consistency_service=consistency_service,
    ), list(cases)


def _real_service(labeler=None):
    return ReportConsistencyService(temporal_terms=TERMS, labeler=labeler)


def _row(db, report_id) -> ReportRecord:
    return db.query(ReportRecord).filter(ReportRecord.id == report_id).one()


# ======================================================================
# THE KEY TEST: observational identity
# ======================================================================

def test_generated_output_is_byte_identical_with_and_without_the_consistency_service():
    """Gate A's whole claim in one assertion.

    The same fake LLM output is generated twice -- once with a real
    consistency service injected (which WILL find a temporal violation in
    this content) and once with none -- and the persisted content plus the
    formatted report are compared byte for byte.

    If this fails, the checker has stopped being observational: it is
    altering what the doctor reads, and Phase 21's results could no longer
    be attributed to the tagged v1.1 system.
    """
    db_with = _db()
    svc_with, uids = _service(db_with, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_with, formatted_with, validation_with, meta_with, snapshot_with = svc_with.generate(
        str(_seed(db_with, ["u1"])), "en"
    )

    db_without = _db()
    svc_without, _ = _service(db_without, TEMPORAL_CONTENT, consistency_service=None)
    id_without, formatted_without, validation_without, meta_without, snapshot_without = (
        svc_without.generate(str(_seed(db_without, ["u1"])), "en")
    )

    row_with, row_without = _row(db_with, id_with), _row(db_without, id_without)

    # the text a doctor reads
    assert row_with.final_content == row_without.final_content
    assert row_with.ai_draft_content == row_without.ai_draft_content
    assert formatted_with.content == formatted_without.content
    assert formatted_with.section_headers == formatted_without.section_headers
    assert formatted_with.language == formatted_without.language

    # every other persisted field that is not the consistency snapshot itself
    assert row_with.validation_warnings == row_without.validation_warnings
    assert row_with.status == row_without.status
    assert row_with.language == row_without.language
    assert row_with.llm_model == row_without.llm_model
    assert row_with.llm_temperature == row_without.llm_temperature
    assert validation_with == validation_without
    assert meta_with == meta_without

    # ...and the ONLY difference is the consistency snapshot
    assert snapshot_without == (None, None, None)
    assert snapshot_with[1] == [CHECK_TEMPORAL, CHECK_TRANSPLANT]
    assert len(snapshot_with[0]) >= 1, "this content should have produced a temporal violation"


def test_disclaimer_is_unchanged_by_the_consistency_service():
    """The disclaimer is rendered after the check; the check must not touch it."""
    db_with = _db()
    svc_with, _ = _service(db_with, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_with, *_ = svc_with.generate(str(_seed(db_with, ["u1"])), "en")

    db_without = _db()
    svc_without, _ = _service(db_without, TEMPORAL_CONTENT, consistency_service=None)
    id_without, *_ = svc_without.generate(str(_seed(db_without, ["u1"])), "en")

    assert _row(db_with, id_with).final_content["disclaimer"] == \
           _row(db_without, id_without).final_content["disclaimer"]


# ======================================================================
# English, real service with a fake labeler
# ======================================================================

def test_english_with_labeler_records_all_three_checks():
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler))
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    row = _row(db, report_id)
    assert row.consistency_checks_run == [CHECK_TEMPORAL, CHECK_TRANSPLANT, CHECK_CONTRADICTION]
    assert row.consistency_violations == []
    assert row.consistency_retry_count == 0
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) == STATUS_CLEAN


def test_planted_temporal_term_is_persisted_as_a_violation():
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    db = _db()
    svc, _ = _service(db, TEMPORAL_CONTENT, consistency_service=_real_service(labeler))
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    row = _row(db, report_id)
    temporal = [v for v in row.consistency_violations if v["check"] == CHECK_TEMPORAL]
    assert len(temporal) == 1
    assert temporal[0]["evidence"]["term"] == "stable"
    assert temporal[0]["field"] == "impression"
    # impression is regenerable by the Gate C retry, so this is an error
    assert temporal[0]["severity"] == "error"
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) == STATUS_VIOLATIONS


def test_findings_located_temporal_term_is_warning_only():
    """Frozen §4.1: the retry never regenerates findings."""
    content = ReportContent(
        findings="Stable granuloma in the right upper lobe.",
        impression="No acute abnormality.", recommendation="None.", disclaimer="d",
    )
    db = _db()
    svc, _ = _service(db, content, consistency_service=_real_service())
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    violations = _row(db, report_id).consistency_violations
    assert [v["severity"] for v in violations] == ["warning"]
    assert violations[0]["field"] == "findings"


def test_transplant_scores_are_computed_but_emit_no_violation_before_gate_b():
    """A perfect copy of a neighbour must be MEASURED and must NOT be flagged
    while the threshold is None -- no number is invented before Gate B."""
    copied = "Small bilateral pleural effusions with patchy bilateral airspace disease."
    content = ReportContent(findings="The lungs are clear.", impression=copied,
                            recommendation="None.", disclaimer="d")
    cases = {"u1": RetrievedCase(source_uid="u1", similarity=0.9, findings="nf", impression=copied)}

    db = _db()
    service = _real_service()
    svc, _ = _service(db, content, consistency_service=service, cases=cases)
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    row = _row(db, report_id)
    assert CHECK_TRANSPLANT in row.consistency_checks_run
    assert [v for v in row.consistency_violations if v["check"] == CHECK_TRANSPLANT] == []

    scores = service.transplant_scores(content, [cases["u1"]])
    assert scores["ratio"] == 1.0
    assert scores["neighbour_uid"] == "u1"


def test_contradiction_is_persisted_when_the_labeler_reports_one():
    labeler = FakeLabeler(
        findings_row=(CLASS_NEGATIVE, CLASS_BLANK, CLASS_BLANK),
        impression_row=(CLASS_POSITIVE, CLASS_BLANK, CLASS_BLANK),
    )
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler))
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    violations = _row(db, report_id).consistency_violations
    contradictions = [v for v in violations if v["check"] == CHECK_CONTRADICTION]
    assert len(contradictions) == 1
    assert contradictions[0]["evidence"]["label"] == "Cardiomegaly"


def test_has_prior_study_false_is_passed_from_the_one_named_constant():
    """Frozen §2(iii): v1.2 always reports no prior study, from one named
    place rather than a literal at the call site."""
    assert HAS_PRIOR_STUDY_V1_2 is False
    recorder = RecordingConsistencyService(_real_service())
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=recorder)
    svc.generate(str(_seed(db, ["u1"])), "en")
    assert recorder.calls[0]["has_prior_study"] is HAS_PRIOR_STUDY_V1_2


# ======================================================================
# labeler=None
# ======================================================================

def test_no_labeler_omits_contradiction_from_checks_run():
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler=None))
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    row = _row(db, report_id)
    assert CHECK_CONTRADICTION not in row.consistency_checks_run
    assert row.consistency_checks_run == [CHECK_TEMPORAL, CHECK_TRANSPLANT]


def test_partial_checks_with_no_violations_report_status_clean():
    """DECISION MADE IN A4, NEEDS RATIFICATION.

    With no labeler, two of three checks run. Step 4's rule is
    "checks_run non-empty and violations == [] -> clean", so this reports
    "clean" even though the contradiction check never ran.

    The information is not lost -- `checks_run` lists exactly which checks
    earned the verdict, and the API surfaces it beside the status -- but the
    single status word does not itself convey partiality. The alternative
    (a fourth status, e.g. "partial") is NOT implemented here because the
    frozen document does not define one and step 4 specifies these three.
    """
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler=None))
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")

    row = _row(db, report_id)
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) == STATUS_CLEAN
    # the partiality is recoverable from checks_run, which the API serves
    assert len(row.consistency_checks_run) == 2
    assert build_consistency_response(
        row.consistency_violations, row.consistency_checks_run, row.consistency_retry_count
    ).checks_run == [CHECK_TEMPORAL, CHECK_TRANSPLANT]


# ======================================================================
# Bengali
# ======================================================================

def test_bengali_persists_null_violations_empty_checks_run_and_reports_not_run():
    """Frozen §3.4/§8.8. checks_run == [] is a positive statement that zero
    checks were applicable; violations stays NULL because nothing was
    examined. The status must be "not_run", never "clean"."""
    db = _db()
    svc, _ = _service(db, TEMPORAL_CONTENT, consistency_service=_real_service())
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "bn")

    row = _row(db, report_id)
    assert row.consistency_violations is None
    assert row.consistency_checks_run == []
    assert row.consistency_retry_count == 0
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) == STATUS_NOT_RUN


def test_bengali_never_reports_clean_even_though_the_same_english_content_violates():
    """Guards the test above from passing because the content was clean."""
    db_en = _db()
    svc_en, _ = _service(db_en, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_en, *_ = svc_en.generate(str(_seed(db_en, ["u1"])), "en")
    assert len(_row(db_en, id_en).consistency_violations) >= 1

    db_bn = _db()
    svc_bn, _ = _service(db_bn, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_bn, *_ = svc_bn.generate(str(_seed(db_bn, ["u1"])), "bn")
    row = _row(db_bn, id_bn)
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) != STATUS_CLEAN


# ======================================================================
# checker failure
# ======================================================================

def test_check_raising_still_produces_a_report_with_all_three_columns_null():
    """Generation must never fail because of the checker."""
    raiser = RaisingConsistencyService()
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=raiser)
    report_id, formatted, _, _, snapshot = svc.generate(str(_seed(db, ["u1"])), "en")

    assert raiser.calls == 1
    row = _row(db, report_id)
    assert row.consistency_violations is None
    assert row.consistency_checks_run is None
    assert row.consistency_retry_count is None
    assert snapshot == (None, None, None)
    # the report itself is intact
    assert row.final_content["findings"] == CLEAN_CONTENT.findings
    assert formatted.content.findings == CLEAN_CONTENT.findings
    assert derive_consistency_status(row.consistency_checks_run, row.consistency_violations) == STATUS_NOT_RUN


def test_check_raising_is_logged_with_the_report_id(caplog):
    raiser = RaisingConsistencyService()
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=raiser)
    with caplog.at_level("ERROR"):
        report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")
    assert str(report_id) in caplog.text
    assert "consistency check failed" in caplog.text


def test_no_consistency_service_leaves_all_three_columns_null():
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=None)
    report_id, *_ = svc.generate(str(_seed(db, ["u1"])), "en")
    row = _row(db, report_id)
    assert (row.consistency_violations, row.consistency_checks_run,
            row.consistency_retry_count) == (None, None, None)


# ======================================================================
# status derivation -- the one shared function
# ======================================================================

@pytest.mark.parametrize("checks_run,violations,expected", [
    (None, None, STATUS_NOT_RUN),          # pre-v1.2 row
    ([], None, STATUS_NOT_RUN),            # Bengali
    ([], [], STATUS_NOT_RUN),              # zero checks, empty list
    (None, [], STATUS_NOT_RUN),            # inconsistent, read safely
    (["temporal"], None, STATUS_NOT_RUN),  # inconsistent, read safely
    (["temporal"], [], STATUS_CLEAN),
    (["temporal", "transplant"], [], STATUS_CLEAN),
    (["temporal"], [{"check": "temporal"}], STATUS_VIOLATIONS),
])
def test_status_rules(checks_run, violations, expected):
    assert derive_consistency_status(checks_run, violations) == expected


def test_status_can_never_be_clean_without_a_non_empty_checks_run():
    """The safety property of the derivation, asserted directly."""
    for violations in (None, [], [{"check": "temporal"}]):
        for checks_run in (None, []):
            assert derive_consistency_status(checks_run, violations) == STATUS_NOT_RUN


def test_pre_v1_2_row_reports_not_run_through_the_response_builder():
    block = build_consistency_response(None, None, None)
    assert block.status == STATUS_NOT_RUN
    assert block.checks_run == []
    assert block.violations == []
    assert block.retry_count is None


def test_response_builder_maps_violation_fields():
    block = build_consistency_response(
        [{"check": "temporal", "severity": "error", "field": "impression",
          "detail": "d", "evidence": {"term": "stable"}}],
        ["temporal"], 0,
    )
    assert block.status == STATUS_VIOLATIONS
    assert block.violations[0].check == "temporal"
    assert block.violations[0].evidence == {"term": "stable"}
    assert block.retry_count == 0


# ======================================================================
# schema backward compatibility
# ======================================================================

def test_existing_response_fields_are_unchanged():
    """The consistency block is additive: every pre-existing field still
    exists, and the block itself defaults so no existing construction
    breaks."""
    from app.api.schemas import GenerateReportResponse, ReportDetailResponse

    gen = GenerateReportResponse.model_fields
    for name in ("report_id", "session_id", "formatted_report", "validation",
                 "generation_metadata"):
        assert name in gen
    assert "consistency" in gen

    detail = ReportDetailResponse.model_fields
    for name in ("report_id", "session_id", "content", "ai_draft_content", "language",
                 "status", "validation", "generation_metadata", "retrieval_support",
                 "top1_similarity"):
        assert name in detail
    assert "consistency" in detail


def test_consistency_block_defaults_to_not_run_when_omitted():
    """A caller that forgets to populate it under-claims rather than
    over-claims -- a default of "clean" would let an omission read as an
    assurance."""
    from app.api.schemas import ValidationResponse, GenerationMetadataResponse
    from app.api.schemas import FormattedReportResponse, ReportContentResponse, GenerateReportResponse

    content = ReportContentResponse(
        examination="", clinical_history="", technique="", findings="",
        impression="", recommendation="", disclaimer="",
    )
    response = GenerateReportResponse(
        report_id="r", session_id="s",
        formatted_report=FormattedReportResponse(
            content=content, language="en", report_date="2026-09-21", section_headers={}
        ),
        validation=ValidationResponse(is_clean=True, warnings=[]),
        generation_metadata=GenerationMetadataResponse(
            llm_model="m", llm_temperature=0.0, embedding_model="e",
            embedding_version="v", collection_name="c",
        ),
    )
    assert response.consistency.status == STATUS_NOT_RUN
