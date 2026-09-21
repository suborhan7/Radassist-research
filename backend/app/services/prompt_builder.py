"""
app/services/prompt_builder.py
====================================================================
Implements IPromptBuilder. Transforms a ClinicalContext (Phase 5's output)
into a deterministic prompt string for a specific language, per the frozen
Phase 6 architecture (development_log.md, "Phase 6 -- Prompt Builder:
Architecture (FROZEN)"). Pure text construction only -- no LLM calls, no
response parsing, no report formatting, no clinical judgment.

build_generation_prompt, build_retry_prompt, and (as of Phase 10)
build_explanation_prompt are implemented here. build_translation_prompt
(permanently unimplemented per the frozen spec -- bilingual output is
produced by the LLM generating directly in the target language via the
`language` parameter, not a separate translation pass) is intentionally
absent from this class; IPromptBuilder is a Protocol, not an ABC, so this
class is not required to implement every method on it, only the ones a
given caller actually invokes.

build_explanation_prompt reuses _evidence_section (the exact same
deterministic evidence serialization build_generation_prompt already
uses) rather than a second, divergent copy -- same "one shared
serialization" discipline as every prior phase's reuse decisions.

build_comparison_prompt (Phase 11) reuses _report_content_section (the
exact same ReportContent serialization build_explanation_prompt
established in Phase 10) for BOTH the previous and current report,
rather than a second copy -- that method now takes an explicit `label`
param (default "REPORT CONTENT", preserving build_explanation_prompt's
existing output byte-for-byte) so each call site can distinguish
"PREVIOUS REPORT CONTENT" from "CURRENT REPORT CONTENT".

build_section_regeneration_prompt (Phase 19) asks for ONE editable
section's plain replacement text, never a 7-field JSON object -- a
genuinely separate prompt from build_generation_prompt(), confirmed by
real investigation before writing any of this (not assumed a mode-switch
would do): _schema_instruction() hardcodes "exactly these 7 string
fields," and generate_draft()'s content-retry loop parses a full 7-field
JSON blob via IStructuralValidator -- neither applies to a single-field
plain-text ask. What IS reused, unchanged: _language_instruction(),
_grounding_instruction(), _confidence_instruction(), _evidence_section(),
_questionnaire_section(), _clinical_notes_section() -- same evidence,
same grounding rules, same formatting, regardless of whether the request
is for a full report or one section. Only the role instruction and the
output-format instruction are new. On the orchestrator side this pairs
with LLMOrchestrator.generate_freeform() (Phase 19 extraction from
answer_question()'s private helper), not generate_draft() -- no content-
retry/structural-validation loop, since a single section's prose has no
JSON schema to validate against, same reasoning as answer_question().

Prompt-drift risk, named rather than left implicit (per
phase19_section_regeneration_architecture.md's Risks section): if
build_generation_prompt()'s grounding/confidence instructions are ever
edited in a future phase, build_section_regeneration_prompt() reuses
those exact same helper methods, so it updates automatically -- but the
role/output instructions below are section-regeneration-specific and
will NOT automatically track any future full-report-only prompt change.
A future edit to the full-report role/schema instructions should
prompt a deliberate check of whether these need a matching update.

Determinism: every prompt is a pure function of its arguments -- no
timestamps, no wall-clock reads, no random ordering. ClinicalContext's
collections are already deterministically ordered by Phase 5; this module
only serializes in the given order, never re-sorts.
"""
from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities import (
    ClinicalContext,
    ComparisonFacts,
    EditableReportField,
    EvidenceSummary,
    Report,
    ReportContent,
    VotedLabel,
)

REPORT_CONTENT_FIELDS = (
    "examination",
    "clinical_history",
    "technique",
    "findings",
    "impression",
    "recommendation",
    "disclaimer",
)

# Phase 19: keyed by EditableReportField (app/domain/entities.py), the
# single canonical Python-side listing of the 5 regenerable fields --
# found independently duplicated against app/api/reports.py's own fresh
# Literal declaration before both were consolidated onto that one enum.
# Still mirrors the frontend's separate EDITABLE_REPORT_FIELDS constant
# (app/reports/[reportId]/page.tsx) across the Python/TypeScript language
# boundary, which is unavoidable -- but on the Python side, this dict's
# keys are tested directly against EditableReportField's members
# (test_section_field_labels_keys_match_editable_report_field) so the two
# can't silently drift apart from each other.
_SECTION_FIELD_LABELS = {
    EditableReportField.CLINICAL_HISTORY: "Clinical History",
    EditableReportField.TECHNIQUE: "Technique",
    EditableReportField.FINDINGS: "Findings",
    EditableReportField.IMPRESSION: "Impression",
    EditableReportField.RECOMMENDATION: "Recommendation",
}

# The human-readable label for each ReportContent field, in
# REPORT_CONTENT_FIELDS order. Extracted so _report_content_section() can
# render an arbitrary subset without a second hard-coded list of labels.
_CONTENT_FIELD_LABELS = {
    "examination": "Examination",
    "clinical_history": "Clinical History",
    "technique": "Technique",
    "findings": "Findings",
    "impression": "Impression",
    "recommendation": "Recommendation",
    "disclaimer": "Disclaimer",
}

NO_EVIDENCE_MESSAGE = "No retrieved evidence is available for this case."

_LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "bn": "Respond in Bengali (বাংলা).",
}


class PromptBuilder:
    """Satisfies domain.interfaces.IPromptBuilder (partially -- see module docstring)."""

    def __init__(self, temporal_terms: Sequence[str] = ()) -> None:
        """Phase 22 v1.2 frozen §2(iii).

        `temporal_terms` is THE SAME list ReportConsistencyService matches on,
        injected from `settings.consistency_temporal_terms` by the lifespan.
        There is deliberately NO second list in this module: a prompt that
        forbade a different set of words from the one the checker looks for
        would make the measured temporal rate a statement about two unrelated
        vocabularies. The single-source property is asserted by
        test_prompt_heldout_containment.py.

        Defaults to empty so every existing `PromptBuilder()` construction
        keeps working. With an empty list the no-prior instruction still
        forbids comparison language, it simply cannot enumerate the terms --
        a weaker instruction, never a wrong one.
        """
        self._temporal_terms = tuple(temporal_terms)

    def build_generation_prompt(self, context: ClinicalContext, language: str) -> str:
        sections = [
            self._role_instruction(),
            self._language_instruction(language),
            self._schema_instruction(),
            self._grounding_instruction(),
            # Phase 22 v1.2 frozen §2(ii) and §2(iii). Placed AFTER the
            # grounding instruction and BEFORE the evidence block, so the
            # rules the model must apply to the evidence are stated before it
            # reads the evidence -- the anti-copying prohibition in §2(i)
            # heads the evidence block itself, where the text it governs is.
            self._section_support_instruction(),
            self._no_prior_study_instruction(),
            self._confidence_instruction(context.voted_labels),
            self._evidence_section(context.evidence_summary),
        ]
        # Phase 9 fix: questionnaire_answers/clinical_notes existed on
        # ClinicalContext since Phase 5 but were never serialized into the
        # prompt -- silently accepted, never read. Both sections are
        # conditionally included ONLY when there's real content, so the
        # empty-fixture case every test since Phase 6 has exercised is
        # byte-identical to before this fix (see
        # test_empty_questionnaire_and_notes_produce_byte_identical_prompt).
        if context.questionnaire_answers:
            sections.append(self._questionnaire_section(context.questionnaire_answers))
        if context.clinical_notes.strip():
            sections.append(self._clinical_notes_section(context.clinical_notes))
        sections.append("Now generate the report using the field markers above.")
        return "\n\n".join(sections)

    def build_retry_prompt(
        self,
        context: ClinicalContext,
        language: str,
        previous_response: str,
        validation_errors: list[str],
    ) -> str:
        base_prompt = self.build_generation_prompt(context, language)
        errors_block = (
            "\n".join(f"- {error}" for error in validation_errors)
            if validation_errors
            else "(no specific validation errors provided)"
        )
        retry_section = (
            "---\n"
            "RETRY INSTRUCTIONS:\n"
            "Your previous response failed validation and could not be accepted. "
            "You must correct every issue listed below and output a new, complete "
            "response following all the instructions above exactly, using the "
            "field markers, not JSON. Do not repeat the same mistakes.\n\n"
            "PREVIOUS RESPONSE (rejected):\n"
            f"{previous_response}\n\n"
            "VALIDATION ERRORS (must all be fixed):\n"
            f"{errors_block}"
        )
        return f"{base_prompt}\n\n{retry_section}"

    def build_explanation_prompt(
        self, report: Report, question: str, evidence_summary: EvidenceSummary | None
    ) -> str:
        # Phase 17 (pre-Step-6 resolution): explanation chat grounds its
        # answer in final_content -- what the report currently says to the
        # doctor reading it, including any edits already made -- not the
        # immutable AI draft. Confirmed usage: this call site is Phase 10's
        # Explainability Chat (a doctor's follow-up question about a
        # specific report), never comparison narrative generation (that's
        # build_comparison_prompt(), which takes plain ReportContent args
        # already resolved by ComparisonService). Explicit user decision.
        sections = [
            self._explanation_role_instruction(),
            self._report_content_section(report.final_content),
            self._evidence_section(evidence_summary),
            self._explanation_grounding_instruction(),
            self._question_section(question),
        ]
        return "\n\n".join(sections)

    def build_comparison_prompt(
        self, facts: ComparisonFacts, previous: ReportContent, current: ReportContent
    ) -> str:
        sections = [
            self._comparison_role_instruction(),
            self._report_content_section(previous, label="PREVIOUS REPORT CONTENT"),
            self._report_content_section(current, label="CURRENT REPORT CONTENT"),
            self._comparison_facts_section(facts),
            self._comparison_grounding_instruction(),
        ]
        return "\n\n".join(sections)

    def build_section_regeneration_prompt(
        self,
        context: ClinicalContext,
        language: str,
        field: EditableReportField,
        current_findings: str = "",
    ) -> str:
        """Phase 22 v1.2 frozen §2(iv): `current_findings` is this report's
        CURRENT findings text (`final_content["findings"]`, including any
        doctor edits -- the same precedent build_explanation_prompt() set in
        Phase 17), supplied by ReportEditService.

        It is rendered only when the regenerated field is impression or
        recommendation, because those are the two that must be supported by
        findings. Regenerating findings itself needs no copy of findings, and
        including one would invite the model to echo the text it is meant to
        replace.
        """
        field_label = _SECTION_FIELD_LABELS.get(field, field)
        needs_findings = field in (
            EditableReportField.IMPRESSION,
            EditableReportField.RECOMMENDATION,
        )
        sections = [
            self._section_regeneration_role_instruction(field_label),
            self._language_instruction(language),
            self._grounding_instruction(),
        ]
        if needs_findings:
            # Reuses _report_content_section() -- the same serializer the
            # explanation and comparison prompts use -- restricted to the one
            # field, rather than a second serializer being written.
            sections.append(
                self._report_content_section(
                    ReportContent(findings=current_findings),
                    label="THIS REPORT'S CURRENT FINDINGS",
                    fields=("findings",),
                )
            )
            sections.append(self._section_support_instruction(authoring_findings=False))
        sections.append(self._no_prior_study_instruction())
        sections.extend([
            self._confidence_instruction(context.voted_labels),
            self._evidence_section(context.evidence_summary),
        ])
        # Same conditional-inclusion pattern as build_generation_prompt()
        # (Phase 9 fix) -- only included when there's real content.
        if context.questionnaire_answers:
            sections.append(self._questionnaire_section(context.questionnaire_answers))
        if context.clinical_notes.strip():
            sections.append(self._clinical_notes_section(context.clinical_notes))
        sections.append(self._section_regeneration_output_instruction(field_label))
        return "\n\n".join(sections)

    @staticmethod
    def _explanation_role_instruction() -> str:
        return (
            "You are an AI radiology assistant answering a clinician's question "
            "about a previously generated chest X-ray report."
        )

    @staticmethod
    def _section_regeneration_role_instruction(field_label: str) -> str:
        """Phase 22 v1.2 frozen §2(iv) reworded this.

        v1.1 said "You are not revising, reviewing, or restating any other
        section", which governed CONTEXT as well as output -- it told the
        model not to consider the rest of the report, which is precisely what
        it must consider to stay consistent with it. The prohibition now
        governs OUTPUT only: other sections may be shown, and must not be
        rewritten or echoed back.
        """
        return (
            f"You are an AI radiology assistant regenerating ONLY the "
            f'"{field_label}" section of a structured chest X-ray report. '
            f"Other sections of the report may be shown to you below for "
            f"context: use them to stay consistent with what the report "
            f"already says, but do not rewrite them and do not include them "
            f"in your output. Output the \"{field_label}\" section only."
        )

    @staticmethod
    def _section_regeneration_output_instruction(field_label: str) -> str:
        return (
            "OUTPUT FORMAT INSTRUCTIONS:\n"
            f'Output ONLY the replacement text for the "{field_label}" section, '
            "as plain prose. Do not include the section label, a JSON wrapper, "
            "markdown formatting, quotation marks, or any other section's "
            "content -- output the replacement text itself, and nothing else."
        )

    @staticmethod
    def _comparison_role_instruction() -> str:
        return (
            "You are an AI radiology assistant narrating a longitudinal "
            "comparison between two chest X-ray reports for the same patient."
        )

    @staticmethod
    def _report_content_section(
        content: ReportContent,
        label: str = "REPORT CONTENT",
        fields: Sequence[str] = REPORT_CONTENT_FIELDS,
    ) -> str:
        """Phase 22 v1.2 frozen §2(iv) added `fields`, defaulting to all seven
        so the explanation and comparison prompts this already serves are
        byte-identical to v1.1 (asserted by
        test_comparison_grounding_is_byte_identical_to_v1_1).

        Section regeneration passes ("findings",) to render just that one
        field, which is why this helper is reused rather than a second
        serializer being written for one field.
        """
        rendered = "\n".join(
            f"{_CONTENT_FIELD_LABELS[name]}: {getattr(content, name)}" for name in fields
        )
        return f"{label}:\n{rendered}"

    @staticmethod
    def _comparison_facts_section(facts: ComparisonFacts) -> str:
        def _list_or_none(items: tuple[str, ...]) -> str:
            return ", ".join(items) if items else "(none)"

        return (
            "DETERMINISTIC COMPARISON FACTS (already computed, not to be recomputed "
            "or second-guessed):\n"
            f"Days between studies: {facts.days_between_studies}\n"
            f"Resolved findings (present in previous report, absent from current): "
            f"{_list_or_none(facts.resolved_findings)}\n"
            f"Persistent findings (present in both reports): "
            f"{_list_or_none(facts.persistent_findings)}\n"
            f"New findings (absent from previous report, present in current): "
            f"{_list_or_none(facts.new_findings)}"
        )

    @staticmethod
    def _comparison_grounding_instruction() -> str:
        # At least as strict as _explanation_grounding_instruction() above --
        # per the frozen Phase 11 spec, this adds explicit prohibitions on
        # inventing findings/diagnoses, estimating severity, and using
        # directional/trend language ("improved"/"worsened"/"progression"/
        # "regression"/"increasing"/"decreasing") except as a direct restatement
        # of an already-computed deterministic fact -- never as independent
        # clinical inference. The LLM's only job is prose conversion of facts
        # already computed by DeterministicComparator, not clinical reasoning.
        return (
            "GROUNDING INSTRUCTIONS:\n"
            "Your ONLY job is to convert the deterministic comparison facts above "
            "into readable prose for a clinician. You are NOT performing clinical "
            "reasoning, diagnosis, or judgment of your own -- every fact about what "
            "changed between the two reports has already been computed above, and "
            "you must not recompute, contradict, or second-guess it.\n"
            "You must NOT invent any finding that is not listed above in resolved, "
            "persistent, or new findings. You must NOT invent, suggest, or imply any "
            "diagnosis that is not already present in the previous or current report "
            "content above. You must NOT estimate or characterize the severity of any "
            "finding beyond what the report content above states.\n"
            'You must NOT use the words or phrases "improved", "worsened", '
            '"progression", "regression", "increasing", or "decreasing" UNLESS you '
            "are directly restating one of the deterministic facts above (e.g. a "
            "finding moving from resolved/persistent/new) -- never as your own "
            "independent inference about clinical trajectory."
        )

    @staticmethod
    def _explanation_grounding_instruction() -> str:
        # At least as strong as _grounding_instruction() above -- interactive
        # chat is a worse hallucination surface than one-shot generation (a
        # clinician can ask leading questions), so this adds an explicit
        # "never introduce a new diagnosis" clause and a mandatory fallback
        # sentence for out-of-scope questions, both stronger than the plain
        # "do not include it" of the generation-time instruction.
        return (
            "GROUNDING INSTRUCTIONS:\n"
            "You must answer ONLY using the report content and evidence provided "
            "above. Do not invent, infer, or introduce any new diagnosis, finding, "
            "measurement, or clinical detail that is not already present in the "
            "report content or the evidence above. If the question asks about "
            "something the report content and evidence above do not address, you "
            "MUST explicitly state that the available evidence does not address "
            "this question, rather than speculating or guessing."
        )

    @staticmethod
    def _question_section(question: str) -> str:
        return f"QUESTION:\n{question}"

    @staticmethod
    def _role_instruction() -> str:
        return (
            "You are an AI radiology assistant generating a structured chest "
            "X-ray report."
        )

    @staticmethod
    def _language_instruction(language: str) -> str:
        instruction = _LANGUAGE_INSTRUCTIONS.get(
            language, f"Respond in the language identified by the code '{language}'."
        )
        return f"LANGUAGE INSTRUCTIONS:\n{instruction}"

    @staticmethod
    def _schema_instruction() -> str:
        # Delimiter-marker format, not JSON -- changed after Phase 20's real
        # generation-quality evaluation traced every one of 17 real content-
        # validation failures to the same cause: the LLM inconsistently
        # quoting label names inside the disclaimer field's JSON string
        # value, breaking the backend's json.loads() at that boundary
        # (development_log.md, "Finding: All 17 Generation Failures Share
        # One Root Cause"). A marker-delimited format has no nested-string
        # boundary for a stray quote character to ever break.
        marker_lines = "\n".join(f"###{name.upper()}###\n<{name} text>" for name in REPORT_CONTENT_FIELDS)
        return (
            "OUTPUT FORMAT INSTRUCTIONS:\n"
            "You must output ONLY plain text using the field markers below, and "
            "nothing else. Do NOT use JSON, a JSON wrapper, or markdown code "
            "fences (no ``` characters). Do not include any explanation, "
            "preamble, or trailing text outside the marked fields. Output "
            "exactly these 7 fields, in this exact order, each marker on its "
            "own line immediately followed by that field's plain text (no "
            "surrounding quotation marks needed):\n"
            f"{marker_lines}"
        )

    @staticmethod
    def _section_support_instruction(authoring_findings: bool = True) -> str:
        """Phase 22 v1.2 frozen §2(ii).

        The generation prompt already asks for the seven fields in a fixed
        order with `findings` before `impression`, and generation is
        autoregressive, so the model's own FINDINGS text is already in
        context when it writes IMPRESSION (diagnosis.md §5.4). The defect was
        never that the information was unavailable -- it is that nothing
        REQUIRED the model to use it, while the one instruction present
        ("base your report ONLY on the evidence below") pointed at the
        neighbour block instead. This states the requirement.

        The laterality/location clause is not decoration: the trigger
        report's RECOMMENDATION mislocated the nodule ("right perihilar" vs
        FINDINGS' "right upper lung"), which a rule phrased only about
        presence would not catch, and which no automated check in this phase
        measures.
        """
        opening = (
            "Author FINDINGS first, describing this patient's radiograph from the "
            "evidence below.\n"
            if authoring_findings
            # Section regeneration is NOT authoring findings -- the report's
            # findings already exist and are shown above it. Telling the model
            # to write them first would invite it to emit the wrong section.
            else "This report's FINDINGS is given above and is not being rewritten.\n"
        )
        return (
            "SECTION SUPPORT INSTRUCTIONS:\n"
            + opening +
            "IMPRESSION must be a synthesis of what THIS report's FINDINGS states. "
            "Do not assert any finding that FINDINGS did not state, and never assert "
            "a finding that FINDINGS explicitly negated or described as normal.\n"
            "RECOMMENDATION must follow from IMPRESSION, and must preserve the "
            "anatomical location and laterality used in FINDINGS. Do not move a "
            "finding to a different lobe, zone, or side than FINDINGS gave it."
        )

    def _no_prior_study_instruction(self) -> str:
        """Phase 22 v1.2 frozen §2(iii).

        v1.2 always emits the NO-PRIOR form: ClinicalContext carries no
        prior-study state and priors live in ComparisonService, which never
        generates a report. That is correct for every case in the evaluation
        harness and every first-visit report, and errs safely -- it can
        suppress comparison language that would have been legitimate for a
        patient who does have a prior, but never permits language that is
        unsupported. Recorded as a limitation in frozen §8.6.

        The enumerated terms are `self._temporal_terms`, the SAME list the
        consistency checker matches on. See __init__ for why there is no
        second list here.
        """
        lines = [
            "PRIOR STUDY:",
            "There is NO prior study for this patient. No earlier examination has "
            "been provided and none exists to compare against.",
            "You must NOT use comparison or temporal language of any kind, and must "
            "not imply that any finding has been seen before.",
        ]
        if self._temporal_terms:
            lines.append(
                "In particular, do not use these words or phrases: "
                + ", ".join(self._temporal_terms)
                + "."
            )
        lines.append(
            "Describe only the current radiograph's appearance, without reference to "
            "any earlier examination."
        )
        return "\n".join(lines)

    @staticmethod
    def _grounding_instruction() -> str:
        return (
            "GROUNDING INSTRUCTIONS:\n"
            "You must base your report ONLY on the evidence provided below. Do not "
            "invent, infer, or hallucinate any finding, measurement, or clinical "
            "detail that is not directly supported by the evidence below. If the "
            "evidence is insufficient to support a finding, do not include it."
        )

    @staticmethod
    def _confidence_instruction(voted_labels: tuple[VotedLabel, ...]) -> str:
        if not voted_labels:
            return (
                "CONFIDENCE / UNCERTAINTY INSTRUCTIONS:\n"
                "No label-voting evidence is available for this case. Do not state "
                "any diagnosis with certainty; express appropriate clinical "
                "uncertainty throughout."
            )
        top_label = voted_labels[0]
        return (
            "CONFIDENCE / UNCERTAINTY INSTRUCTIONS:\n"
            f'The top candidate label from retrieval-based voting is "{top_label.label}" '
            f"with an agreement score of {top_label.agreement:.2f} (the fraction of "
            "retrieved neighbor cases agreeing on this label). If this agreement "
            "score is low, you MUST express appropriate clinical uncertainty in your "
            "findings and impression rather than false certainty. Do not state a "
            "diagnosis as certain when the agreement score is low."
        )

    @staticmethod
    def _evidence_section(evidence_summary: EvidenceSummary | None) -> str:
        if evidence_summary is None or (
            not evidence_summary.findings_evidence
            and not evidence_summary.impressions_evidence
            and not evidence_summary.label_evidence
        ):
            return f"EVIDENCE:\n{NO_EVIDENCE_MESSAGE}"

        # Phase 22 v1.2 frozen §2(i). The block previously opened with a bare
        # "EVIDENCE:" and called these "similar cases", never stating whose
        # reports they are. The existing grounding instruction forbids only
        # INVENTION, so verbatim copying satisfied it -- 83 of 353 scorable
        # Arm C impressions reproduced a neighbour's impression exactly
        # (diagnosis.md §2a). Copying has to be named as its own prohibited
        # act, because no amount of anti-hallucination wording reaches it.
        lines = [
            "EVIDENCE -- OTHER PATIENTS' REPORTS (reference only):",
            "The findings and impressions below are taken from OTHER PATIENTS' "
            "finalised chest X-ray reports, retrieved by image similarity to this "
            "patient's image. They are NOT this patient's history, and they are NOT "
            "a description of this patient's radiograph.",
            "Use them as reference for reporting style and for differential "
            "reasoning only.",
            "You must NOT reproduce their sentences or phrasing in your report, and "
            "you must NOT transfer any specific finding, measurement, laterality, or "
            "device from them into this report unless it is independently supported "
            "for THIS patient by the evidence about this patient.",
            "",
        ]

        lines.append("Retrieved findings from other patients' reports (most similar first):")
        if evidence_summary.findings_evidence:
            for i, text in enumerate(evidence_summary.findings_evidence, start=1):
                lines.append(f"{i}. {text}")
        else:
            lines.append("(none provided)")

        lines.append("")
        lines.append("Retrieved impressions from other patients' reports (most similar first):")
        if evidence_summary.impressions_evidence:
            for i, text in enumerate(evidence_summary.impressions_evidence, start=1):
                lines.append(f"{i}. {text}")
        else:
            lines.append("(none provided)")

        lines.append("")
        lines.append("Label evidence (top voted label partition):")
        if evidence_summary.label_evidence:
            partition = evidence_summary.label_evidence[0]
            lines.append(f"- Label: {partition.label}")
            lines.append(f"- Vote weight: {partition.vote_weight:.2f}")
            lines.append(f"- Agreement: {partition.agreement:.2f}")
            lines.append(f"- Supporting cases: {len(partition.supporting_cases)}")
            lines.append(f"- Contradictory cases: {len(partition.contradictory_cases)}")
        else:
            lines.append("(none)")

        return "\n".join(lines)

    @staticmethod
    def _questionnaire_section(questionnaire_answers: dict[str, str]) -> str:
        lines = ["CLINICAL QUESTIONNAIRE:"]
        for key in sorted(questionnaire_answers):
            lines.append(f"- {key}: {questionnaire_answers[key]}")
        return "\n".join(lines)

    @staticmethod
    def _clinical_notes_section(clinical_notes: str) -> str:
        return f"ADDITIONAL CLINICAL NOTES:\n{clinical_notes}"
