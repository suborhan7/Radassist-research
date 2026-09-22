"""Phase 23 Step 1: the label checklist prompt block (variants V2 and V3).

Pre-registered in docs/phase23/plan.md §3.2.

The property that matters most here is the FIRST one: with the flag off, the
generation prompt must be BYTE-IDENTICAL to v1.2's. Phase 23 compares V2/V3
against V0/V1, and V0 is only a real baseline if turning the feature off
leaves nothing behind -- not "nearly nothing", not "an extra blank line".
Every other test in this module is about what the block says when it is on.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.config import settings
from app.domain.entities import (
    ClinicalContext,
    EditableReportField,
    EvidenceSummary,
    RetrievalStats,
    RetrievedCase,
    VotedLabel,
)
from app.services.prompt_builder import PromptBuilder

REPO = Path(__file__).resolve().parents[3]

NEIGHBOUR_FINDINGS = "Bibasilar opacities are present in the left lower lobe."
NEIGHBOUR_IMPRESSION = "Bibasilar atelectasis, left greater than right."


def _context(voted: tuple[VotedLabel, ...] | None = None) -> ClinicalContext:
    case = RetrievedCase(
        source_uid="u1", similarity=0.9,
        findings=NEIGHBOUR_FINDINGS, impression=NEIGHBOUR_IMPRESSION,
        labels=("Atelectasis",),
    )
    if voted is None:
        voted = (
            VotedLabel(label="Atelectasis", vote_weight=1.0, agreement=0.8),
            VotedLabel(label="Cardiomegaly", vote_weight=0.6, agreement=0.6),
            VotedLabel(label="Pneumothorax", vote_weight=0.2, agreement=0.2),
        )
    return ClinicalContext(
        retrieved_cases=(case,),
        voted_labels=voted,
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


def _builder(checklist: bool, threshold: float = 0.5) -> PromptBuilder:
    return PromptBuilder(
        temporal_terms=settings.consistency_temporal_terms,
        label_checklist=checklist,
        checklist_agreement_threshold=threshold,
    )


def _gen(checklist: bool, threshold: float = 0.5, voted=None) -> str:
    return _builder(checklist, threshold).build_generation_prompt(_context(voted), "en")


# --------------------------------------------------------------- flag OFF

def test_flag_off_is_byte_identical_to_v1_2():
    """The load-bearing test. A v1.2 PromptBuilder is constructed the way
    v1.2's lifespan constructed it -- temporal_terms only, no Phase 23
    arguments at all -- and must produce the same bytes as an explicitly
    disabled Phase 23 builder."""
    v1_2 = PromptBuilder(temporal_terms=settings.consistency_temporal_terms)
    assert v1_2.build_generation_prompt(_context(), "en") == _gen(checklist=False)


def test_flag_off_emits_no_checklist_text():
    out = _gen(checklist=False)
    assert "LABEL CHECKLIST" not in out
    assert "IMPRESSION COVERAGE" not in out
    assert "Candidate labels" not in out


def test_flag_off_default_construction():
    """PromptBuilder() with no arguments must not enable the checklist --
    every test written before Phase 23 constructs it that way."""
    out = PromptBuilder().build_generation_prompt(_context(), "en")
    assert "LABEL CHECKLIST" not in out


def test_flag_off_introduces_no_extra_separator():
    """Guards the specific regression of appending "" to the section list,
    which would add a blank line and break byte-identity invisibly."""
    off = _gen(checklist=False)
    assert "\n\n\n" not in off


# ---------------------------------------------------------------- flag ON

def test_flag_on_emits_checklist():
    out = _gen(checklist=True)
    assert "LABEL CHECKLIST:" in out
    assert "Candidate labels:" in out


def test_flag_on_lists_only_labels_at_or_above_threshold():
    out = _gen(checklist=True, threshold=0.5)
    assert "- Atelectasis (agreement 0.80)" in out
    assert "- Cardiomegaly (agreement 0.60)" in out
    # 0.2 < 0.5 -- must not be listed as a candidate
    assert "- Pneumothorax" not in out


def test_threshold_boundary_is_inclusive():
    """agreement == threshold is IN. The plan says "at or above"."""
    voted = (VotedLabel(label="Edema", vote_weight=1.0, agreement=0.5),)
    assert "- Edema (agreement 0.50)" in _gen(checklist=True, threshold=0.5, voted=voted)


def test_threshold_is_respected_when_changed():
    voted = (
        VotedLabel(label="Atelectasis", vote_weight=1.0, agreement=0.8),
        VotedLabel(label="Cardiomegaly", vote_weight=0.6, agreement=0.6),
    )
    out = _gen(checklist=True, threshold=0.7, voted=voted)
    assert "- Atelectasis" in out
    assert "- Cardiomegaly" not in out


def test_no_label_clears_threshold_emits_nothing():
    voted = (VotedLabel(label="Fracture", vote_weight=0.1, agreement=0.1),)
    out = _gen(checklist=True, threshold=0.5, voted=voted)
    assert "LABEL CHECKLIST" not in out


def test_empty_voted_labels_emits_nothing():
    out = _gen(checklist=True, voted=())
    assert "LABEL CHECKLIST" not in out


def test_forces_a_disposition_both_ways():
    """The block must offer present AND absent, and forbid doing neither.
    A checklist that only said "state it if present" would be a licence to
    over-call, which is the opposite of the intended effect."""
    out = _gen(checklist=True)
    assert "state the finding as present" in out
    assert "absent or not demonstrated" in out
    assert "must not do neither" in out


def test_does_not_instruct_blind_acceptance():
    out = _gen(checklist=True)
    assert "ONLY where this patient's image evidence supports it" in out
    assert "Do not state a label as present merely because it appears below" in out


def test_labels_are_named_as_hypotheses_not_observations():
    out = _gen(checklist=True)
    assert "HYPOTHESIS" in out
    assert "not an observation of this patient's radiograph" in out


def test_impression_coverage_clause_present():
    """The findings->impression direction v1.2 left unconstrained:
    27/477 v1.2 reports stated an abnormality in findings and called the
    study normal in the impression (gate_a_results.md §6.3)."""
    out = _gen(checklist=True)
    assert "IMPRESSION COVERAGE:" in out
    assert "every abnormality your FINDINGS states must also appear in your IMPRESSION" in out
    assert "must not describe the study as normal" in out


# ------------------------------------------------------------- placement

def test_checklist_sits_after_confidence_and_before_evidence():
    """v1.2's ordering rule: rules to apply to the evidence are stated
    before the evidence is read."""
    out = _gen(checklist=True)
    conf = out.index("CONFIDENCE / UNCERTAINTY INSTRUCTIONS:")
    chk = out.index("LABEL CHECKLIST:")
    ev = out.index("EVIDENCE -- OTHER PATIENTS' REPORTS")
    assert conf < chk < ev


def test_flag_on_preserves_every_v1_2_section():
    """Turning the checklist on must ADD a block, never replace one."""
    off = _gen(checklist=False)
    on = _gen(checklist=True)
    for marker in (
        "GROUNDING INSTRUCTIONS:",
        "SECTION SUPPORT INSTRUCTIONS:",
        "PRIOR STUDY:",
        "CONFIDENCE / UNCERTAINTY INSTRUCTIONS:",
        "EVIDENCE -- OTHER PATIENTS' REPORTS",
    ):
        assert marker in off
        assert marker in on
    assert len(on) > len(off)


# ------------------------------------------------- other prompts untouched

def test_checklist_does_not_leak_into_section_regeneration_prompt():
    """Section regeneration rewrites ONE field of an existing report. A
    checklist telling the model to disposition every candidate label would
    invite it to rewrite the whole report inside one field."""
    b = _builder(checklist=True)
    out = b.build_section_regeneration_prompt(
        context=_context(),
        language="en",
        field=EditableReportField.IMPRESSION,
        current_findings="Bibasilar atelectasis is present.",
    )
    assert "LABEL CHECKLIST" not in out


def test_checklist_reaches_the_retry_prompt():
    """build_retry_prompt wraps build_generation_prompt, so the checklist
    DOES propagate there. That is intended -- a retry must be given the same
    instructions as the attempt it replaces -- and is asserted rather than
    left as an accident."""
    b = _builder(checklist=True)
    out = b.build_retry_prompt(
        context=_context(),
        language="en",
        previous_response="bad",
        validation_errors=["missing marker"],
    )
    assert "LABEL CHECKLIST:" in out
    assert "RETRY INSTRUCTIONS:" in out


# --------------------------------------------------- held-out containment

def _heldout_patterns() -> list[tuple[str, str]]:
    path = REPO / "docs/phase22/heldout_temporal_terms.txt"
    assert path.exists(), (
        "held-out list missing -- a containment test that silently passes "
        "because it had nothing to check is worse than no test"
    )
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, rx = line.split("\t", 1)
            rows.append((name.strip(), rx.strip()))
    assert rows, "held-out list parsed to zero terms"
    return rows


@pytest.mark.parametrize("checklist_on", [False, True])
def test_no_heldout_term_reaches_the_generation_prompt(checklist_on):
    """A held-out term in ANY prompt burns the list and invalidates the
    temporal endpoint. Checked with the checklist off AND on, because
    Phase 23 adds prompt text and the list must survive that."""
    out = _gen(checklist=checklist_on)
    for name, rx in _heldout_patterns():
        assert not re.search(rx, out, re.IGNORECASE), (
            f"held-out term {name!r} (/{rx}/) reached the generation prompt "
            f"with checklist={'on' if checklist_on else 'off'} -- the list is "
            f"burned and must be replaced before the next evaluation"
        )


def test_no_heldout_term_in_the_checklist_block_alone():
    """Narrower than the test above: isolates the new text, so a failure
    points at the checklist rather than anywhere in the prompt."""
    block = _builder(checklist=True)._label_checklist_instruction(
        _context().voted_labels
    )
    assert block
    for name, rx in _heldout_patterns():
        assert not re.search(rx, block, re.IGNORECASE), (
            f"held-out term {name!r} is in the Phase 23 checklist block"
        )
