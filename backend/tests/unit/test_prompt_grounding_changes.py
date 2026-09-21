"""
Phase 22 Step A5: frozen §2 prompt changes (i)-(iv).

Frozen architecture: docs/phase22/fix_architecture_v1.2_FROZEN.md §2
(frozen at docs commit 810240ea).

Each of the four changes is asserted on the RENDERED prompt, not on the
helper that produces it, because what matters is what the model is actually
sent. Where a change is defined against v1.1 behaviour, the v1.1 text is
read from tag `v1.1-evaluated` and compared directly rather than restated
from memory.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.domain.entities import (
    ClinicalContext,
    ComparisonFacts,
    EditableReportField,
    EvidenceSummary,
    ReportContent,
    RetrievalStats,
    RetrievedCase,
    VotedLabel,
)
from app.services.prompt_builder import PromptBuilder

REPO = Path(__file__).resolve().parents[3]

NEIGHBOUR_FINDINGS = "Bibasilar opacities are present in the left lower lobe."
NEIGHBOUR_IMPRESSION = "Bibasilar atelectasis, left greater than right."


def _context() -> ClinicalContext:
    case = RetrievedCase(
        source_uid="u1", similarity=0.9,
        findings=NEIGHBOUR_FINDINGS, impression=NEIGHBOUR_IMPRESSION,
        labels=("Atelectasis",),
    )
    return ClinicalContext(
        retrieved_cases=(case,),
        voted_labels=(VotedLabel(label="Atelectasis", vote_weight=1.0, agreement=0.8),),
        questionnaire_answers={},
        clinical_notes="",
        evidence_summary=EvidenceSummary(
            top_retrieved_case=case,
            findings_evidence=(NEIGHBOUR_FINDINGS,),
            impressions_evidence=(NEIGHBOUR_IMPRESSION,),
            retrieval_stats=RetrievalStats(1, 1, 0, 0.9, 0.9, 0.9, 1, 0),
            retrieval_metadata=None,
            label_evidence=(),
        ),
    )


def _builder() -> PromptBuilder:
    return PromptBuilder(temporal_terms=settings.consistency_temporal_terms)


def _generation() -> str:
    return _builder().build_generation_prompt(_context(), "en")


def _v1_1_builder():
    """The prompt builder exactly as it was at tag v1.1-evaluated."""
    src = subprocess.run(
        ["git", "show", "v1.1-evaluated:backend/app/services/prompt_builder.py"],
        capture_output=True, text=True, cwd=REPO,
    ).stdout
    if not src.strip():
        pytest.skip("tag v1.1-evaluated not reachable from this checkout")
    path = Path(tempfile.mkdtemp()) / "prompt_builder_v11.py"
    path.write_text(src, encoding="utf-8")
    import importlib.util
    spec = importlib.util.spec_from_file_location("prompt_builder_v11_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PromptBuilder


# ======================================================================
# (i) neighbour evidence attribution
# ======================================================================

def test_evidence_block_states_the_reports_belong_to_other_patients():
    prompt = _generation()
    assert "OTHER PATIENTS' REPORTS" in prompt
    assert "OTHER PATIENTS'" in prompt
    assert "NOT this patient's history" in prompt
    assert "NOT\na description of this patient's radiograph" in prompt.replace("\n", "\n") or \
           "NOT a description of this patient's radiograph" in prompt


def test_evidence_block_says_reference_only():
    prompt = _generation()
    assert "reference only" in prompt
    assert "reference for reporting style and for differential" in prompt


def test_evidence_block_forbids_reproducing_sentences():
    prompt = _generation()
    assert "must NOT reproduce their sentences" in prompt


def test_evidence_block_forbids_transferring_findings_measurements_laterality_devices():
    """All four nouns the frozen document names, not a paraphrase of some."""
    prompt = _generation()
    clause = prompt[prompt.index("must NOT transfer"):]
    for noun in ("finding", "measurement", "laterality", "device"):
        assert noun in clause, f"{noun!r} missing from the transfer prohibition"
    assert "unless it is independently supported for THIS patient" in prompt


def test_v1_1_evidence_block_had_no_attribution_at_all():
    """Establishes the change is real rather than a rewording."""
    old_prompt = _v1_1_builder()().build_generation_prompt(_context(), "en")
    assert "OTHER PATIENTS" not in old_prompt
    assert "must NOT reproduce" not in old_prompt
    assert "similar cases" in old_prompt   # the v1.1 wording


# ======================================================================
# (ii) impression/recommendation constrained to findings
# ======================================================================

def test_impression_must_synthesise_only_this_reports_findings():
    prompt = _generation()
    assert "SECTION SUPPORT INSTRUCTIONS:" in prompt
    assert "IMPRESSION must be a synthesis of what THIS report's FINDINGS states" in prompt


def test_impression_must_not_assert_what_findings_did_not_state_or_negated():
    prompt = _generation()
    assert "Do not assert any finding that FINDINGS did not state" in prompt
    assert "never assert a finding that FINDINGS explicitly negated" in prompt


def test_recommendation_must_follow_impression_and_preserve_location_and_laterality():
    """The laterality clause exists because the trigger report's
    RECOMMENDATION mislocated the nodule; a presence-only rule misses it."""
    prompt = _generation()
    assert "RECOMMENDATION must follow from IMPRESSION" in prompt
    assert "preserve the" in prompt and "anatomical location and laterality" in prompt
    assert "Do not move a finding to a different lobe, zone, or side" in prompt


def test_findings_is_authored_first_in_the_generation_prompt():
    prompt = _generation()
    assert "Author FINDINGS first" in prompt
    # the marker order itself is unchanged and still puts findings before impression
    assert prompt.index("###FINDINGS###") < prompt.index("###IMPRESSION###")
    assert prompt.index("###IMPRESSION###") < prompt.index("###RECOMMENDATION###")


# ======================================================================
# (iii) no-prior-study instruction
# ======================================================================

def test_prompt_states_that_no_prior_study_exists():
    prompt = _generation()
    assert "PRIOR STUDY:" in prompt
    assert "There is NO prior study for this patient" in prompt
    assert "none exists to compare against" in prompt


def test_prompt_forbids_comparison_language_and_names_the_terms():
    prompt = _generation()
    assert "must NOT use comparison or temporal language" in prompt
    for term in settings.consistency_temporal_terms:
        assert term in prompt, f"term {term!r} not named in the prompt"


def test_prompt_requires_describing_only_the_current_radiograph():
    assert "without reference to any earlier examination" in _generation()


def test_v1_1_had_no_prior_study_instruction():
    old_prompt = _v1_1_builder()().build_generation_prompt(_context(), "en")
    assert "PRIOR STUDY" not in old_prompt
    assert "no prior study" not in old_prompt.lower()


# ======================================================================
# (iv) section regeneration
# ======================================================================

DOCTOR_EDITED = "The right upper lung nodule measures 8 mm. Heart size is normal."
AI_DRAFT = "AI DRAFT FINDINGS THAT THE DOCTOR REPLACED."


@pytest.mark.parametrize("field", [EditableReportField.IMPRESSION,
                                   EditableReportField.RECOMMENDATION])
def test_regeneration_includes_current_findings_for_impression_and_recommendation(field):
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", field, current_findings=DOCTOR_EDITED
    )
    assert "THIS REPORT'S CURRENT FINDINGS:" in prompt
    assert DOCTOR_EDITED in prompt


def test_regeneration_uses_final_content_findings_not_the_ai_draft():
    """Frozen §2(iv): `final_content["findings"]`, i.e. what the report
    currently says INCLUDING doctor edits -- the Phase 17 precedent."""
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", EditableReportField.IMPRESSION, current_findings=DOCTOR_EDITED
    )
    assert DOCTOR_EDITED in prompt
    assert AI_DRAFT not in prompt


@pytest.mark.parametrize("field", [EditableReportField.FINDINGS,
                                   EditableReportField.CLINICAL_HISTORY,
                                   EditableReportField.TECHNIQUE])
def test_regeneration_omits_findings_for_fields_that_do_not_need_it(field):
    """Regenerating findings itself must not be handed a copy of the text it
    is meant to replace."""
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", field, current_findings=DOCTOR_EDITED
    )
    assert DOCTOR_EDITED not in prompt
    assert "THIS REPORT'S CURRENT FINDINGS:" not in prompt


def test_regeneration_applies_the_section_support_constraint():
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", EditableReportField.IMPRESSION, current_findings=DOCTOR_EDITED
    )
    assert "SECTION SUPPORT INSTRUCTIONS:" in prompt
    assert "IMPRESSION must be a synthesis of what THIS report's FINDINGS states" in prompt
    # and NOT the generation-time opening, which would ask it to write findings
    assert "Author FINDINGS first" not in prompt
    assert "FINDINGS is given above and is not being rewritten" in prompt


def test_regeneration_role_instruction_governs_output_not_context():
    """v1.1 said "You are not revising, reviewing, or restating any other
    section", which told the model not to CONSIDER the rest of the report --
    exactly what it must consider to stay consistent with it."""
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", EditableReportField.IMPRESSION, current_findings=DOCTOR_EDITED
    )
    assert "not revising, reviewing, or restating any other section" not in prompt
    assert "may be shown to you below for context" in prompt
    assert "do not rewrite them and do not include them in your output" in prompt


def test_v1_1_regeneration_forbade_considering_other_sections():
    old_prompt = _v1_1_builder()().build_section_regeneration_prompt(
        _context(), "en", EditableReportField.IMPRESSION
    )
    assert "not revising, reviewing, or restating any other section" in old_prompt
    assert "CURRENT FINDINGS" not in old_prompt


def test_regeneration_also_carries_the_no_prior_instruction():
    prompt = _builder().build_section_regeneration_prompt(
        _context(), "en", EditableReportField.IMPRESSION, current_findings=DOCTOR_EDITED
    )
    assert "There is NO prior study for this patient" in prompt


# ======================================================================
# unchanged paths
# ======================================================================

def test_comparison_grounding_is_byte_identical_to_v1_1():
    """The comparison path legitimately uses temporal language and is
    explicitly out of scope. Byte-identical, not merely similar."""
    assert (
        PromptBuilder._comparison_grounding_instruction()
        == _v1_1_builder()._comparison_grounding_instruction()
    )


def test_comparison_prompt_is_byte_identical_to_v1_1():
    facts = ComparisonFacts(
        previous_report_id="p1", current_report_id="c1",
        resolved_findings=("Atelectasis",), persistent_findings=(), new_findings=(),
        days_between_studies=30,
    )
    content = ReportContent(
        examination="Chest X-ray", clinical_history="h", technique="PA",
        findings="f", impression="i", recommendation="r", disclaimer="d",
    )
    assert (
        _builder().build_comparison_prompt(facts, content, content)
        == _v1_1_builder()().build_comparison_prompt(facts, content, content)
    )


def _explanation_report():
    from app.domain.entities import Language, Report, ReportStatus
    content = ReportContent(
        examination="Chest X-ray", clinical_history="h", technique="PA",
        findings="f", impression="i", recommendation="r", disclaimer="d",
    )
    return Report(
        id="r1", study_id="s1", language=Language.ENGLISH, status=ReportStatus.AI_DRAFT,
        ai_draft_content=content, final_content=content,
    )


def test_explanation_report_content_section_is_byte_identical_to_v1_1():
    """_report_content_section() gained a `fields` parameter; its DEFAULT must
    leave every existing caller byte-identical."""
    report = _explanation_report()
    new = _builder().build_explanation_prompt(report, "why?", _context().evidence_summary)
    old = _v1_1_builder()().build_explanation_prompt(report, "why?", _context().evidence_summary)

    def report_content_block(prompt: str) -> str:
        start = prompt.index("REPORT CONTENT:")
        return prompt[start:prompt.index("\n\n", start)]

    assert report_content_block(new) == report_content_block(old)


def test_explanation_prompt_inherits_the_neighbour_attribution():
    """INTENDED CONSEQUENCE, not an accident.

    build_explanation_prompt() reuses _evidence_section(), so change (i)
    propagates to it. That is correct and desirable: the explanation chat
    shows the clinician the same other-patient neighbour text, and it should
    carry the same attribution boundary and the same anti-copying
    prohibition. The frozen §2(i) rationale -- that copying must be named as
    a distinct prohibited act -- applies wherever that text is shown.

    So the explanation prompt is deliberately NOT byte-identical to v1.1; its
    evidence block changed with (i) and its report-content block did not
    (asserted above).
    """
    report = _explanation_report()
    new = _builder().build_explanation_prompt(report, "why?", _context().evidence_summary)
    old = _v1_1_builder()().build_explanation_prompt(report, "why?", _context().evidence_summary)

    assert new != old
    assert "OTHER PATIENTS' REPORTS" in new
    assert "must NOT reproduce their sentences" in new
    assert "OTHER PATIENTS" not in old


def test_marker_schema_instruction_is_byte_identical_to_v1_1():
    """The marker format is explicitly out of scope for A5."""
    assert PromptBuilder._schema_instruction() == _v1_1_builder()._schema_instruction()


def test_grounding_instruction_is_byte_identical_to_v1_1():
    """(ii) and (iii) are ADDED as separate sections; the existing grounding
    instruction is not reworded."""
    assert PromptBuilder._grounding_instruction() == _v1_1_builder()._grounding_instruction()


# ======================================================================
# language coverage
# ======================================================================

@pytest.mark.parametrize("language", ["en", "bn"])
def test_all_four_changes_apply_to_every_language(language):
    """The instructions are language-independent English instruction text.
    Their EFFECT on Bengali output is unmeasured -- see the dev log."""
    prompt = _builder().build_generation_prompt(_context(), language)
    assert "OTHER PATIENTS' REPORTS" in prompt
    assert "SECTION SUPPORT INSTRUCTIONS:" in prompt
    assert "There is NO prior study for this patient" in prompt
