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
    STATUS_PARTIAL,
    STATUS_VIOLATIONS,
    build_consistency_response,
    derive_consistency_status,
)
from app.database.base import Base
from app.domain.entities import (
    ClinicalContext,
    ConsistencySnapshot,
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
    ALL_CHECKS,
    CHECK_CONTRADICTION,
    CHECK_TEMPORAL,
    CHECK_TRANSPLANT,
    CLASS_BLANK,
    CLASS_NEGATIVE,
    CLASS_POSITIVE,
    ReportConsistencyService,
    applicable_checks,
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
    out_with = svc_with.generate(str(_seed(db_with, ["u1"])), "en")

    db_without = _db()
    svc_without, _ = _service(db_without, TEMPORAL_CONTENT, consistency_service=None)
    out_without = svc_without.generate(str(_seed(db_without, ["u1"])), "en")

    row_with = _row(db_with, out_with.report_id)
    row_without = _row(db_without, out_without.report_id)
    formatted_with, formatted_without = out_with.formatted_report, out_without.formatted_report

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
    assert out_with.validation == out_without.validation
    assert out_with.generation_metadata == out_without.generation_metadata

    # ...and the ONLY difference is the consistency snapshot
    assert out_without.consistency == ConsistencySnapshot.none()
    # amendment 01(b): transplant is scored but not listed while its
    # threshold is None, so only temporal ran here (no labeler injected).
    assert out_with.consistency.checks_run == [CHECK_TEMPORAL]
    assert len(out_with.consistency.violations) >= 1, (
        "this content should have produced a temporal violation"
    )


def test_disclaimer_is_unchanged_by_the_consistency_service():
    """The disclaimer is rendered after the check; the check must not touch it."""
    db_with = _db()
    svc_with, _ = _service(db_with, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_with = svc_with.generate(str(_seed(db_with, ["u1"])), "en").report_id

    db_without = _db()
    svc_without, _ = _service(db_without, TEMPORAL_CONTENT, consistency_service=None)
    id_without = svc_without.generate(str(_seed(db_without, ["u1"])), "en").report_id

    assert _row(db_with, id_with).final_content["disclaimer"] == \
           _row(db_without, id_without).final_content["disclaimer"]


# ======================================================================
# English, real service with a fake labeler
# ======================================================================

def test_english_with_labeler_records_the_runnable_checks():
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler))
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    # amendment 01(b): transplant is scored every run but not listed until
    # Gate B gives it a threshold, so it is absent and the status is
    # "partial" rather than "clean".
    assert row.consistency_checks_run == [CHECK_TEMPORAL, CHECK_CONTRADICTION]
    assert row.consistency_violations == []
    assert row.consistency_retry_count == 0
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_PARTIAL


def test_planted_temporal_term_is_persisted_as_a_violation():
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    db = _db()
    svc, _ = _service(db, TEMPORAL_CONTENT, consistency_service=_real_service(labeler))
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    temporal = [v for v in row.consistency_violations if v["check"] == CHECK_TEMPORAL]
    assert len(temporal) == 1
    assert temporal[0]["evidence"]["term"] == "stable"
    assert temporal[0]["field"] == "impression"
    # impression is regenerable by the Gate C retry, so this is an error
    assert temporal[0]["severity"] == "error"
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_VIOLATIONS


def test_findings_located_temporal_term_is_warning_only():
    """Frozen §4.1: the retry never regenerates findings."""
    content = ReportContent(
        findings="Stable granuloma in the right upper lobe.",
        impression="No acute abnormality.", recommendation="None.", disclaimer="d",
    )
    db = _db()
    svc, _ = _service(db, content, consistency_service=_real_service())
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

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
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    # amendment 01(b): scored, but NOT listed -- it cannot emit a violation
    # while its threshold is None, so claiming it "ran" would overstate.
    assert CHECK_TRANSPLANT not in row.consistency_checks_run
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
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

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
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    assert CHECK_CONTRADICTION not in row.consistency_checks_run
    assert row.consistency_checks_run == [CHECK_TEMPORAL]


def test_partial_checks_with_no_violations_report_status_partial():
    """AMENDMENT 01, superseding A4 decision #5.

    With no labeler and no transplant threshold, only the temporal check can
    emit a violation. Before the amendment this reported "clean", which
    overstated assurance: two of three applicable checks never ran. It now
    reports "partial", and `applicable_checks` names the gap.
    """
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=_real_service(labeler=None))
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    assert row.consistency_checks_run == [CHECK_TEMPORAL]
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_PARTIAL

    block = build_consistency_response(
        row.consistency_violations, row.consistency_checks_run,
        row.consistency_retry_count, language="en",
    )
    assert block.status == STATUS_PARTIAL
    assert block.checks_run == [CHECK_TEMPORAL]
    assert block.applicable_checks == list(ALL_CHECKS)
    # the gap is recoverable BY NAME, which a status word alone cannot carry
    assert set(block.applicable_checks) - set(block.checks_run) == {
        CHECK_TRANSPLANT, CHECK_CONTRADICTION
    }


def test_labeler_absent_yields_partial_and_a_strictly_smaller_check_set():
    """Amendment 01: the specific case A4 #5 got wrong."""
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    db_a = _db()
    svc_a, _ = _service(db_a, CLEAN_CONTENT, consistency_service=_real_service(labeler))
    id_a = svc_a.generate(str(_seed(db_a, ["u1"])), "en").report_id
    row_a = _row(db_a, id_a)

    db_b = _db()
    svc_b, _ = _service(db_b, CLEAN_CONTENT, consistency_service=_real_service(labeler=None))
    id_b = svc_b.generate(str(_seed(db_b, ["u1"])), "en").report_id
    row_b = _row(db_b, id_b)

    for row in (row_a, row_b):
        assert derive_consistency_status(
            row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
        ) == STATUS_PARTIAL
    assert set(row_b.consistency_checks_run) < set(row_a.consistency_checks_run)


def test_all_applicable_checks_run_with_no_violations_yields_clean():
    """The only route to "clean": every applicable check actually ran.

    The transplant threshold is injected through the CONSTRUCTOR here, not
    read from config -- a test-only value proving the mechanism. Inventing a
    production threshold before Gate B is exactly what the frozen document
    forbids.
    """
    labeler = FakeLabeler((CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    checker = ReportConsistencyService(
        temporal_terms=TERMS, labeler=labeler,
        transplant_ratio_threshold=0.99,   # test-only, never from config
    )
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=checker)
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    assert set(row.consistency_checks_run) == set(ALL_CHECKS)
    assert row.consistency_violations == []
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_CLEAN


def test_violation_outranks_partial():
    """Amendment 01(c): a real violation is reported even when the check set
    is incomplete. The violation is the actionable fact."""
    db = _db()
    svc, _ = _service(db, TEMPORAL_CONTENT, consistency_service=_real_service(labeler=None))
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id

    row = _row(db, report_id)
    assert set(row.consistency_checks_run) < set(ALL_CHECKS)   # incomplete
    assert len(row.consistency_violations) >= 1
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_VIOLATIONS


# ======================================================================
# Bengali
# ======================================================================

def test_bengali_persists_null_violations_empty_checks_run_and_reports_not_run():
    """Frozen §3.4/§8.8. checks_run == [] is a positive statement that zero
    checks were applicable; violations stays NULL because nothing was
    examined. The status must be "not_run", never "clean"."""
    db = _db()
    svc, _ = _service(db, TEMPORAL_CONTENT, consistency_service=_real_service())
    report_id = svc.generate(str(_seed(db, ["u1"])), "bn").report_id

    row = _row(db, report_id)
    assert row.consistency_violations is None
    assert row.consistency_checks_run == []
    assert row.consistency_retry_count == 0
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("bn")
    ) == STATUS_NOT_RUN


def test_bengali_never_reports_clean_even_though_the_same_english_content_violates():
    """Guards the test above from passing because the content was clean."""
    db_en = _db()
    svc_en, _ = _service(db_en, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_en = svc_en.generate(str(_seed(db_en, ["u1"])), "en").report_id
    assert len(_row(db_en, id_en).consistency_violations) >= 1

    db_bn = _db()
    svc_bn, _ = _service(db_bn, TEMPORAL_CONTENT, consistency_service=_real_service())
    id_bn = svc_bn.generate(str(_seed(db_bn, ["u1"])), "bn").report_id
    row = _row(db_bn, id_bn)
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("bn")
    ) not in (STATUS_CLEAN, STATUS_PARTIAL)


# ======================================================================
# checker failure
# ======================================================================

def test_check_raising_still_produces_a_report_with_all_three_columns_null():
    """Generation must never fail because of the checker."""
    raiser = RaisingConsistencyService()
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=raiser)
    outcome = svc.generate(str(_seed(db, ["u1"])), "en")
    report_id, formatted = outcome.report_id, outcome.formatted_report

    assert raiser.calls == 1
    row = _row(db, report_id)
    assert row.consistency_violations is None
    assert row.consistency_checks_run is None
    assert row.consistency_retry_count is None
    assert outcome.consistency == ConsistencySnapshot.none()
    # the report itself is intact
    assert row.final_content["findings"] == CLEAN_CONTENT.findings
    assert formatted.content.findings == CLEAN_CONTENT.findings
    assert derive_consistency_status(
        row.consistency_checks_run, row.consistency_violations, applicable_checks("en")
    ) == STATUS_NOT_RUN


def test_check_raising_is_logged_with_the_report_id(caplog):
    raiser = RaisingConsistencyService()
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=raiser)
    with caplog.at_level("ERROR"):
        report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id
    assert str(report_id) in caplog.text
    assert "consistency check failed" in caplog.text


def test_no_consistency_service_leaves_all_three_columns_null():
    db = _db()
    svc, _ = _service(db, CLEAN_CONTENT, consistency_service=None)
    report_id = svc.generate(str(_seed(db, ["u1"])), "en").report_id
    row = _row(db, report_id)
    assert (row.consistency_violations, row.consistency_checks_run,
            row.consistency_retry_count) == (None, None, None)


# ======================================================================
# status derivation -- the one shared function
# ======================================================================

@pytest.mark.parametrize("checks_run,violations,applicable,expected", [
    (None, None, ALL_CHECKS, STATUS_NOT_RUN),            # pre-v1.2 row
    ([], None, (), STATUS_NOT_RUN),                      # Bengali
    ([], [], (), STATUS_NOT_RUN),                        # zero checks, empty list
    (None, [], ALL_CHECKS, STATUS_NOT_RUN),              # inconsistent, read safely
    (["temporal"], None, ALL_CHECKS, STATUS_NOT_RUN),    # inconsistent, read safely
    (["temporal"], [], ALL_CHECKS, STATUS_PARTIAL),      # amendment 01
    (["temporal", "contradiction"], [], ALL_CHECKS, STATUS_PARTIAL),
    (list(ALL_CHECKS), [], ALL_CHECKS, STATUS_CLEAN),    # every applicable check ran
    (["temporal"], [{"check": "temporal"}], ALL_CHECKS, STATUS_VIOLATIONS),
    (list(ALL_CHECKS), [{"check": "temporal"}], ALL_CHECKS, STATUS_VIOLATIONS),
])
def test_status_rules(checks_run, violations, applicable, expected):
    assert derive_consistency_status(checks_run, violations, applicable) == expected


def test_partial_requires_a_strict_subset():
    """Equality is "clean", not "partial" -- otherwise no report could ever
    be clean."""
    assert derive_consistency_status(list(ALL_CHECKS), [], ALL_CHECKS) == STATUS_CLEAN
    assert derive_consistency_status(list(ALL_CHECKS)[:2], [], ALL_CHECKS) == STATUS_PARTIAL


def test_status_can_never_be_clean_without_a_non_empty_checks_run():
    """The safety property of the derivation, asserted directly."""
    for violations in (None, [], [{"check": "temporal"}]):
        for checks_run in (None, []):
            for applicable in (None, (), ALL_CHECKS):
                assert derive_consistency_status(
                    checks_run, violations, applicable
                ) == STATUS_NOT_RUN


def test_pre_v1_2_row_reports_not_run_through_the_response_builder():
    block = build_consistency_response(None, None, None, language="en")
    assert block.status == STATUS_NOT_RUN
    assert block.checks_run == []
    assert block.violations == []
    assert block.retry_count is None


def test_response_builder_maps_violation_fields():
    block = build_consistency_response(
        [{"check": "temporal", "severity": "error", "field": "impression",
          "detail": "d", "evidence": {"term": "stable"}}],
        ["temporal"], 0, language="en",
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
