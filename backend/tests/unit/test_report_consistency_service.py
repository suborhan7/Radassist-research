"""
Unit tests for ReportConsistencyService, per the frozen Phase 22 v1.2
architecture (docs/phase22/fix_architecture_v1.2_FROZEN.md §3, frozen at docs
commit 810240ea).

Real, hand-built ReportContent/ClinicalContext/RetrievedCase fixtures and a
fake labeler -- same convention as Phase 5/6/8's unit tests. No CheXbert here:
the labeler is Step A2, and this service is specified to work without one.

NOTE ON TEST LOCATION. The Step A1 brief named tests/services/. Every one of
the ~30 existing service test modules lives in backend/tests/unit/, and no
tests/services/ directory exists, so this follows the established layout
rather than starting a second one for a single file. Flagged in the dev log.

NOTE ON THE HELD-OUT LIST. The frozen document's held-out temporal synonyms
(§6.4) deliberately appear NOWHERE under backend/, including in these tests. A
held-out term that reaches the repository is no longer held out. Everything
below uses the prompt-side list only.
"""
from __future__ import annotations

import pytest

from app.domain.entities import (
    ClinicalContext,
    ConsistencyResult,
    EvidenceSummary,
    ReportContent,
    RetrievalStats,
    RetrievedCase,
)
from app.services.report_consistency_service import (
    CHECK_CONTRADICTION,
    CHECK_TEMPORAL,
    CHECK_TRANSPLANT,
    CLASS_BLANK,
    CLASS_NEGATIVE,
    CLASS_POSITIVE,
    CLASS_UNCERTAIN,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ReportConsistencyService,
)

TERMS = ("stable", "unchanged", "interval", "again", "redemonstrated",
         "persistent", "previously", "compared with", "new")


# ----------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------

def _stats() -> RetrievalStats:
    return RetrievalStats(
        num_cases=1, num_cases_after_dedup=1, num_near_duplicates_collapsed=0,
        mean_similarity=0.9, min_similarity=0.9, max_similarity=0.9,
        num_unique_labels=1, num_clusters_represented=0,
    )


def _context() -> ClinicalContext:
    return ClinicalContext(
        retrieved_cases=(), voted_labels=(), questionnaire_answers={}, clinical_notes="",
        evidence_summary=EvidenceSummary(
            top_retrieved_case=None, findings_evidence=(), impressions_evidence=(),
            retrieval_stats=_stats(), retrieval_metadata=None, label_evidence=(),
        ),
    )


def _case(uid: str, impression: str = "", findings: str = "") -> RetrievedCase:
    return RetrievedCase(source_uid=uid, similarity=0.9, findings=findings, impression=impression)


def _content(findings="", impression="", recommendation="") -> ReportContent:
    return ReportContent(findings=findings, impression=impression, recommendation=recommendation)


class FakeLabeler:
    """Returns canned raw 4-class rows. `rows` is (findings_row, impression_row),
    each one class index per entry of `conditions`, exactly as a real
    ISectionLabeler would."""

    def __init__(self, conditions, findings_row, impression_row):
        self._conditions = tuple(conditions)
        self._rows = (tuple(findings_row), tuple(impression_row))
        self.calls: list[list[str]] = []

    @property
    def conditions(self):
        return self._conditions

    def label(self, texts):
        self.calls.append(list(texts))
        return self._rows


def _service(labeler=None, ratio_threshold=None, lcs_threshold=None) -> ReportConsistencyService:
    return ReportConsistencyService(
        temporal_terms=TERMS,
        labeler=labeler,
        transplant_ratio_threshold=ratio_threshold,
        transplant_lcs_threshold=lcs_threshold,
    )


def _check(service, content, cases=(), language="en", has_prior_study=False) -> ConsistencyResult:
    return service.check(content, _context(), cases, language, has_prior_study)


# ----------------------------------------------------------------------
# temporal check -- matching behaviour
# ----------------------------------------------------------------------

def test_stable_matches():
    result = _check(_service(), _content(impression="Stable cardiomegaly."))
    temporal = [v for v in result.violations if v.check == CHECK_TEMPORAL]
    assert len(temporal) == 1
    assert temporal[0].evidence["term"] == "stable"


def test_unstable_does_not_match_stable():
    """The word-boundary is load-bearing: there is no boundary between "un"
    and "stable", so the pattern must not fire inside "unstable"."""
    result = _check(_service(), _content(impression="The patient is unstable."))
    assert [v for v in result.violations if v.check == CHECK_TEMPORAL] == []


def test_matching_is_case_insensitive():
    lower = _check(_service(), _content(impression="stable cardiomegaly."))
    upper = _check(_service(), _content(impression="Stable cardiomegaly."))
    shout = _check(_service(), _content(impression="STABLE cardiomegaly."))
    assert len(lower.violations) == len(upper.violations) == len(shout.violations) == 1


def test_multi_word_term_matches_as_a_phrase():
    result = _check(_service(), _content(impression="Unchanged compared with the earlier study."))
    terms = {v.evidence["term"] for v in result.violations if v.check == CHECK_TEMPORAL}
    assert "compared with" in terms


def test_multi_word_term_tolerates_intervening_whitespace():
    """A line break between the two words is still the same phrase."""
    result = _check(_service(), _content(impression="Findings compared\n   with prior imaging."))
    assert "compared with" in {v.evidence["term"] for v in result.violations}


def test_multi_word_term_does_not_match_first_word_alone():
    result = _check(_service(), _content(impression="A comparison was performed."))
    assert [v for v in result.violations if v.check == CHECK_TEMPORAL] == []


# ----------------------------------------------------------------------
# temporal check -- field attribution and severity
# ----------------------------------------------------------------------

def test_hits_are_attributed_to_the_correct_field():
    content = _content(
        findings="Stable granuloma in the right upper lobe.",
        impression="Unchanged appearance.",
        recommendation="Repeat again in six months.",
    )
    result = _check(_service(), content)
    by_field = {v.field: v.evidence["term"] for v in result.violations if v.check == CHECK_TEMPORAL}
    assert by_field == {"findings": "stable", "impression": "unchanged", "recommendation": "again"}


def test_findings_violations_are_warning_only_others_are_errors():
    """Frozen document §4.1: the Gate C retry never regenerates FINDINGS, so a
    findings-located violation must not be raised as an error the remedy
    cannot act on."""
    content = _content(
        findings="Stable granuloma.", impression="Unchanged.", recommendation="Repeat again."
    )
    result = _check(_service(), content)
    severity = {v.field: v.severity for v in result.violations}
    assert severity["findings"] == SEVERITY_WARNING
    assert severity["impression"] == SEVERITY_ERROR
    assert severity["recommendation"] == SEVERITY_ERROR


def test_violation_records_span_and_context():
    text = "The cardiomediastinal silhouette is stable in appearance."
    result = _check(_service(), _content(impression=text))
    evidence = result.violations[0].evidence
    start, end = evidence["span"]
    assert text[start:end] == "stable"
    assert "cardiomediastinal" in evidence["context"]


def test_has_prior_study_true_produces_no_temporal_violation():
    """With a real prior the language is legitimate -- but the check still ran
    and must still be reported as having run."""
    content = _content(findings="Stable granuloma.", impression="Unchanged compared with prior.")
    result = _check(_service(), content, has_prior_study=True)
    assert [v for v in result.violations if v.check == CHECK_TEMPORAL] == []
    assert CHECK_TEMPORAL in result.checks_run


def test_clean_report_produces_no_violations_but_checks_did_run():
    result = _check(_service(), _content(findings="The lungs are clear.", impression="Normal chest."))
    assert result.violations == ()
    assert result.has_violation is False
    assert CHECK_TEMPORAL in result.checks_run


# ----------------------------------------------------------------------
# transplant check -- Gate A: scores recorded, no violation
# ----------------------------------------------------------------------

def test_identical_neighbour_impression_scores_ratio_one_and_emits_no_violation():
    """The Gate B threshold does not exist yet, so a perfect copy must be
    MEASURED at 1.0 and must NOT be reported as a violation. No number is
    invented to fill the gap."""
    text = "Small bilateral pleural effusions with patchy bilateral airspace disease."
    service = _service()
    content = _content(impression=text)
    cases = (_case("267", impression=text),)

    scores = service.transplant_scores(content, cases)
    assert scores["ratio"] == 1.0
    assert scores["neighbour_uid"] == "267"
    assert scores["scorable"] is True

    result = _check(service, content, cases)
    assert [v for v in result.violations if v.check == CHECK_TRANSPLANT] == []
    assert CHECK_TRANSPLANT in result.checks_run


def test_transplant_takes_the_maximum_across_neighbours():
    text = "Small bilateral pleural effusions with patchy bilateral airspace disease."
    scores = _service().transplant_scores(
        _content(impression=text),
        (_case("1", impression="The lungs are clear."), _case("2", impression=text)),
    )
    assert scores["ratio"] == 1.0
    assert scores["neighbour_uid"] == "2"


def test_unrelated_neighbour_scores_zero():
    scores = _service().transplant_scores(
        _content(impression="Small bilateral pleural effusions with airspace disease."),
        (_case("1", impression="Osseous structures within normal limits for age."),),
    )
    assert scores["ratio"] == 0.0


def test_short_impression_is_unscorable_not_zero():
    """Fewer than 5 tokens yields no 5-gram, so the ratio has no denominator.
    This is the rule that produced n=353 of 477 in diagnosis.md §5.1 -- an
    unscorable case must not be silently recorded as a clean 0.0."""
    scores = _service().transplant_scores(
        _content(impression="Normal."), (_case("1", impression="Normal chest radiograph."),)
    )
    assert scores["scorable"] is False
    assert scores["ratio"] is None


def test_transplant_emits_a_violation_once_a_threshold_is_supplied():
    """Gate B's calibrated threshold arrives by injection, so the check needs
    no edit to start firing."""
    text = "Small bilateral pleural effusions with patchy bilateral airspace disease."
    service = _service(ratio_threshold=0.9)
    result = _check(service, _content(impression=text), (_case("267", impression=text),))
    transplant = [v for v in result.violations if v.check == CHECK_TRANSPLANT]
    assert len(transplant) == 1
    assert transplant[0].evidence["neighbour_uid"] == "267"
    assert transplant[0].evidence["ratio"] == 1.0
    assert transplant[0].severity == SEVERITY_ERROR


# ----------------------------------------------------------------------
# contradiction check
# ----------------------------------------------------------------------

CONDITIONS = ("Cardiomegaly", "Lung Opacity", "No Finding")


def test_positive_versus_negative_is_a_contradiction():
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_NEGATIVE, CLASS_BLANK, CLASS_BLANK),
        impression_row=(CLASS_POSITIVE, CLASS_BLANK, CLASS_BLANK),
    )
    result = _check(_service(labeler), _content(findings="f", impression="i"))
    contradictions = [v for v in result.violations if v.check == CHECK_CONTRADICTION]
    assert len(contradictions) == 1
    assert contradictions[0].evidence == {
        "label": "Cardiomegaly", "findings_class": CLASS_NEGATIVE,
        "impression_class": CLASS_POSITIVE,
    }


def test_positive_versus_absent_is_not_a_contradiction():
    """Present in one section and merely unmentioned in the other is ordinary
    summarisation -- treating it as a contradiction would fire on 62.9% of
    real reports (diagnosis.md §2c)."""
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_POSITIVE, CLASS_BLANK, CLASS_BLANK),
        impression_row=(CLASS_BLANK, CLASS_BLANK, CLASS_BLANK),
    )
    result = _check(_service(labeler), _content(findings="f", impression="i"))
    assert [v for v in result.violations if v.check == CHECK_CONTRADICTION] == []


def test_uncertain_versus_negative_is_not_a_strict_contradiction():
    """A hedge is not an assertion; the rule is strict Positive/Negative."""
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_UNCERTAIN, CLASS_BLANK, CLASS_BLANK),
        impression_row=(CLASS_NEGATIVE, CLASS_BLANK, CLASS_BLANK),
    )
    result = _check(_service(labeler), _content(findings="f", impression="i"))
    assert [v for v in result.violations if v.check == CHECK_CONTRADICTION] == []


def test_no_finding_never_produces_a_contradiction():
    """Its real head has only 2 outputs and can never emit Negative, so a
    contradiction is not expressible for it even if the labels say otherwise."""
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_BLANK, CLASS_BLANK, CLASS_POSITIVE),
        impression_row=(CLASS_BLANK, CLASS_BLANK, CLASS_NEGATIVE),
    )
    result = _check(_service(labeler), _content(findings="f", impression="i"))
    assert [v for v in result.violations if v.check == CHECK_CONTRADICTION] == []


def test_sections_are_labelled_separately_never_concatenated():
    """The defect that makes ResponseValidator blind to this failure class is
    that it builds one combined string first. This must not."""
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_BLANK,) * 3, impression_row=(CLASS_BLANK,) * 3,
    )
    _check(_service(labeler), _content(findings="FINDINGS TEXT", impression="IMPRESSION TEXT"))
    assert labeler.calls == [["FINDINGS TEXT", "IMPRESSION TEXT"]]


def test_no_labeler_omits_contradiction_from_checks_run():
    """Never reported as clean: a check that could not run and a check that
    ran and found nothing are different states."""
    result = _check(_service(labeler=None), _content(findings="f", impression="i"))
    assert CHECK_CONTRADICTION not in result.checks_run
    assert CHECK_TEMPORAL in result.checks_run
    assert CHECK_TRANSPLANT in result.checks_run


def test_labeler_present_adds_contradiction_to_checks_run():
    labeler = FakeLabeler(CONDITIONS, (CLASS_BLANK,) * 3, (CLASS_BLANK,) * 3)
    result = _check(_service(labeler), _content(findings="f", impression="i"))
    assert result.checks_run == (CHECK_TEMPORAL, CHECK_TRANSPLANT, CHECK_CONTRADICTION)


# ----------------------------------------------------------------------
# language
# ----------------------------------------------------------------------

def test_bengali_runs_nothing_and_reports_nothing_as_run():
    """Frozen document §3.4/§8.8: Bengali is generated directly in Bengali, so
    all three checks are English-only. The empty checks_run is the whole point
    -- the UI must show "not run", never a clean state."""
    labeler = FakeLabeler(
        CONDITIONS,
        findings_row=(CLASS_NEGATIVE, CLASS_BLANK, CLASS_BLANK),
        impression_row=(CLASS_POSITIVE, CLASS_BLANK, CLASS_BLANK),
    )
    content = _content(findings="Stable granuloma.", impression="Unchanged compared with prior.")
    result = _check(_service(labeler), content, language="bn")
    assert result.checks_run == ()
    assert result.violations == ()
    assert result.has_violation is False
    assert labeler.calls == [], "the labeler must not even be invoked for a non-English report"


def test_identical_english_content_would_have_violated():
    """Guards the test above from passing for the wrong reason: the same
    content in English must produce violations."""
    content = _content(findings="Stable granuloma.", impression="Unchanged compared with prior.")
    result = _check(_service(), content, language="en")
    assert result.has_violation is True


# ----------------------------------------------------------------------
# construction and Gate A invariants
# ----------------------------------------------------------------------

def test_empty_term_list_is_rejected_at_construction():
    """A check that reports itself as run while being unconditionally silent
    is the exact failure mode this service exists to prevent."""
    with pytest.raises(ValueError, match="CONSISTENCY_TEMPORAL_TERMS"):
        ReportConsistencyService(temporal_terms=())


def test_retry_count_is_zero_in_gate_a():
    """The service is observational at this step: it performs no retry, so the
    count is 0 by construction rather than by coincidence."""
    result = _check(_service(), _content(impression="Stable cardiomegaly."))
    assert result.retry_count == 0


def test_service_satisfies_the_protocol_structurally():
    from app.domain.interfaces import IReportConsistencyChecker
    assert isinstance(_service(), IReportConsistencyChecker)


def test_fake_labeler_satisfies_the_labeler_protocol_structurally():
    from app.domain.interfaces import ISectionLabeler
    assert isinstance(FakeLabeler(CONDITIONS, (0,) * 3, (0,) * 3), ISectionLabeler)


def test_terms_come_from_config_not_from_the_module():
    """No parameter value is written into the service: a caller supplying a
    different list gets different behaviour with no code change."""
    service = ReportConsistencyService(temporal_terms=("banana",))
    result = _check(service, _content(impression="A banana is present. Stable cardiomegaly."))
    terms = {v.evidence["term"] for v in result.violations}
    assert terms == {"banana"}


def test_config_supplies_a_usable_term_list():
    from app.core.config import settings
    service = ReportConsistencyService(temporal_terms=settings.consistency_temporal_terms)
    result = _check(service, _content(impression="Stable cardiomegaly."))
    assert result.has_violation is True
