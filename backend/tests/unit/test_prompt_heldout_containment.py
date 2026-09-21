"""
Phase 22 Step A5: held-out containment and single-source checks.

Frozen architecture §2 and §6.4
(docs/phase22/fix_architecture_v1.2_FROZEN.md, frozen at docs commit
810240ea), as amended by amendment_01_consistency_status.md.

TWO PROPERTIES ARE ASSERTED HERE, and both are about what the model is
allowed to be told:

1. CONTAINMENT. No held-out temporal synonym may appear in ANY prompt the
   backend can send. The held-out list exists to detect word-avoidance: if a
   fix drives the prompt-side terms to zero while the held-out terms hold
   steady, the model learned to dodge the words it was shown rather than to
   stop making unsupported claims. A held-out term that reaches a prompt
   burns the list, and the measurement it supports becomes meaningless.

2. SINGLE SOURCE. The prompt's temporal term list must BE
   Settings.CONSISTENCY_TEMPORAL_TERMS -- the same list
   ReportConsistencyService matches on. A prompt forbidding one vocabulary
   while the checker measures another would make the reported temporal rate
   a statement about two unrelated things.

The held-out list is read from docs/phase22/heldout_temporal_terms.txt,
which is generated from the frozen document (never retyped) and diffed
against it by scratch/phase22_diagnosis/check_heldout.py. This module FAILS
if that file is missing -- a containment test that silently passes because
it had nothing to check is worse than no test.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.config import settings
from app.domain.entities import (
    ClinicalContext,
    ComparisonFacts,
    EditableReportField,
    EvidenceSummary,
    Language,
    Report,
    ReportContent,
    ReportStatus,
    RetrievalStats,
    RetrievedCase,
    VotedLabel,
)
from app.services.prompt_builder import PromptBuilder

HELDOUT_FILE = (
    Path(__file__).resolve().parents[3] / "docs" / "phase22" / "heldout_temporal_terms.txt"
)

# Deliberately free of every temporal word, prompt-side and held-out alike,
# so any hit the containment test finds comes from the INSTRUCTION text the
# builder wrote, never from the fixture data fed into it.
NEUTRAL_FINDINGS = "The lungs are clear. No focal consolidation is seen."
NEUTRAL_IMPRESSION = "No acute cardiopulmonary abnormality."
NEUTRAL_TEXT = "Placeholder clinical text for prompt rendering."


def _load_heldout() -> list[tuple[str, str]]:
    if not HELDOUT_FILE.is_file():
        pytest.fail(
            f"held-out term file missing: {HELDOUT_FILE}. Containment cannot be "
            f"checked, and a containment test that passes with nothing to check "
            f"is worse than no test. Regenerate it with "
            f"scratch/phase22_diagnosis/extract_heldout.py."
        )
    rows = []
    for line in HELDOUT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        term, regex = line.split("\t", 1)
        rows.append((term.strip(), regex.strip()))
    return rows


def _context(findings=NEUTRAL_FINDINGS, impression=NEUTRAL_IMPRESSION) -> ClinicalContext:
    case = RetrievedCase(
        source_uid="u1", similarity=0.9, findings=findings, impression=impression,
        labels=("Normal",),
    )
    return ClinicalContext(
        retrieved_cases=(case,),
        voted_labels=(VotedLabel(label="Normal", vote_weight=1.0, agreement=1.0),),
        questionnaire_answers={"duration": NEUTRAL_TEXT},
        clinical_notes=NEUTRAL_TEXT,
        evidence_summary=EvidenceSummary(
            top_retrieved_case=case,
            findings_evidence=(findings,),
            impressions_evidence=(impression,),
            retrieval_stats=RetrievalStats(1, 1, 0, 0.9, 0.9, 0.9, 1, 0),
            retrieval_metadata=None,
            label_evidence=(),
        ),
    )


def _content() -> ReportContent:
    return ReportContent(
        examination="Chest X-ray", clinical_history=NEUTRAL_TEXT, technique="PA",
        findings=NEUTRAL_FINDINGS, impression=NEUTRAL_IMPRESSION,
        recommendation="No follow-up imaging is indicated.", disclaimer=NEUTRAL_TEXT,
    )


def _report() -> Report:
    return Report(
        id="r1", study_id="s1", language=Language.ENGLISH, status=ReportStatus.AI_DRAFT,
        ai_draft_content=_content(), final_content=_content(),
    )


def _builder() -> PromptBuilder:
    return PromptBuilder(temporal_terms=settings.consistency_temporal_terms)


def all_rendered_prompts() -> dict[str, str]:
    """Every prompt the backend can actually send.

    Enumerated explicitly rather than by introspection so that a new builder
    method added later fails test_every_builder_method_is_covered() and has
    to be added here deliberately -- an un-enumerated prompt is an
    unchecked prompt.
    """
    pb = _builder()
    context = _context()
    prompts = {
        "generation": pb.build_generation_prompt(context, "en"),
        "generation_bn": pb.build_generation_prompt(context, "bn"),
        "retry": pb.build_retry_prompt(
            context, "en", previous_response=NEUTRAL_TEXT,
            validation_errors=["missing field: findings"],
        ),
        "explanation": pb.build_explanation_prompt(
            _report(), question="Why was this impression reached?",
            evidence_summary=context.evidence_summary,
        ),
        "comparison": pb.build_comparison_prompt(
            ComparisonFacts(
                previous_report_id="p1", current_report_id="c1",
                resolved_findings=(), persistent_findings=(), new_findings=(),
                days_between_studies=30,
            ),
            _content(), _content(),
        ),
    }
    for field in EditableReportField:
        prompts[f"regeneration_{field.value}"] = pb.build_section_regeneration_prompt(
            context, "en", field, current_findings=NEUTRAL_FINDINGS
        )
    return prompts


# ----------------------------------------------------------------------
# containment
# ----------------------------------------------------------------------

def test_heldout_file_exists_and_has_the_expected_terms():
    rows = _load_heldout()
    assert len(rows) == 10, f"expected 10 held-out terms, found {len(rows)}"
    assert all(term and regex for term, regex in rows)


@pytest.mark.parametrize("prompt_name", sorted(all_rendered_prompts()))
def test_no_heldout_term_appears_in_any_rendered_prompt(prompt_name):
    """Word-boundary, case-insensitive, over every prompt the backend sends."""
    prompt = all_rendered_prompts()[prompt_name]
    hits = []
    for term, regex in _load_heldout():
        match = re.search(regex, prompt, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 60)
            hits.append(f"{term!r} matched {match.group(0)!r} near: ...{prompt[start:match.end() + 60]}...")
    assert not hits, (
        f"HELD-OUT TERM LEAKED INTO THE {prompt_name} PROMPT. The held-out list is "
        f"burned and must be replaced before the next evaluation:\n  " + "\n  ".join(hits)
    )


def test_the_containment_check_can_actually_fail():
    """Guards the test above from passing vacuously: the same matcher must
    fire on text that genuinely contains a held-out term."""
    poisoned = "The nodule remains unchanged and there is no interval change."
    hits = [t for t, rx in _load_heldout() if re.search(rx, poisoned, flags=re.IGNORECASE)]
    assert len(hits) >= 2, f"matcher failed to detect planted held-out terms, found {hits}"


def test_every_builder_method_is_covered_by_containment():
    """A new prompt-building method must be added to all_rendered_prompts()
    deliberately. An un-enumerated prompt is an unchecked prompt."""
    public = {
        name for name in dir(PromptBuilder)
        if name.startswith("build_") and callable(getattr(PromptBuilder, name))
    }
    # build_translation_prompt is permanently unimplemented per the frozen
    # spec (bilingual output is generated directly in the target language),
    # and is absent from this class.
    covered = {
        "build_generation_prompt", "build_retry_prompt", "build_explanation_prompt",
        "build_comparison_prompt", "build_section_regeneration_prompt",
    }
    assert public == covered, (
        f"prompt builder methods not covered by containment: {public - covered}"
    )


# ----------------------------------------------------------------------
# single source
# ----------------------------------------------------------------------

def test_prompt_temporal_terms_equal_the_settings_value():
    prompt = _builder().build_generation_prompt(_context(), "en")
    for term in settings.consistency_temporal_terms:
        assert term in prompt, f"settings term {term!r} missing from the prompt"


def test_prompt_builder_holds_no_second_term_list():
    """The strong single-source check.

    Built with a sentinel vocabulary, the prompt must name the sentinels and
    NONE of the real terms. If prompt_builder.py carried its own hard-coded
    list, the real terms would appear regardless of what was injected.
    """
    sentinels = ("zzalpha", "zzbeta", "zzgamma")
    prompt = PromptBuilder(temporal_terms=sentinels).build_generation_prompt(_context(), "en")

    for sentinel in sentinels:
        assert sentinel in prompt

    for term in settings.consistency_temporal_terms:
        assert not re.search(rf"\b{re.escape(term)}\b", prompt, flags=re.IGNORECASE), (
            f"real term {term!r} appears in a prompt built from sentinels only -- "
            f"prompt_builder.py holds a second, hard-coded term list"
        )


def test_empty_term_list_still_forbids_comparison_language():
    """Degrades to a weaker instruction, never to a wrong or absent one."""
    prompt = PromptBuilder().build_generation_prompt(_context(), "en")
    assert "PRIOR STUDY:" in prompt
    assert "NO prior study" in prompt
    assert "must NOT use comparison" in prompt
    assert "In particular, do not use" not in prompt
