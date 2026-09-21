"""
app/services/report_consistency_service.py
====================================================================
Implements IReportConsistencyChecker, per the frozen Phase 22 v1.2
architecture (docs/phase22/fix_architecture_v1.2_FROZEN.md §3, frozen at docs
commit 810240ea). Single responsibility: **does this report contradict itself
or its own evidence boundary?**

Deliberately a separate module, not merged into anything:
  - NOT into ResponseValidator.validate_semantic(), whose subject is the
    model's claims against retrieved evidence, which concatenates findings and
    impression before inspecting them (so cross-section contradiction is not
    representable there at all), and which is frozen as advisory by Phase 8
    Decision 1.
  - NOT into LLMOrchestrator, documented as having "zero semantic judgment".
  - NOT into StructuralValidator, which owns response shape only.

Constructor takes the individual values it needs -- term list, thresholds,
optional labeler -- never a Settings object, matching ModalityGateService's
established pattern. No parameter value is written into this module: the
temporal term list and both transplant thresholds arrive by injection.

GATE A SCOPE (this step). The service is OBSERVATIONAL and UNWIRED:
  * Nothing constructs or calls it yet. ReportGenerationService,
    ReportEditService, the prompt builder, the models and the API routes are
    all untouched.
  * There is no retry logic. `retry_count` is always 0. The Gate C retry
    (frozen document §4) is a later step.
  * The transplant threshold is Gate B's to calibrate and is None here, so
    that check computes and exposes its scores but emits NO violation. A
    number is not invented to fill the gap.

WHY THE SCORING FUNCTIONS LIVE HERE. `_tokens`, `_five_grams` and
`_longest_common_token_run` below are the measurement that produced
docs/phase22/diagnosis.md §2a (83/353 impressions at 5-gram ratio 1.0). They
were moved here from scratch/phase22_diagnosis/measure_transplant.py rather
than reimplemented, so the production check and the diagnostic measurement
cannot drift into two different definitions of "copied". The scratch script
scratch/phase22_diagnosis/verify_measurement_identity.py now imports THESE
functions and reproduces the published numbers exactly; a divergence is a
stop condition, not a rounding difference.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from app.domain.entities import (
    ClinicalContext,
    ConsistencyResult,
    ConsistencyViolation,
    ReportContent,
    RetrievedCase,
)

# The three checks, named once. These strings appear in ConsistencyResult.
# checks_run and in ConsistencyViolation.check, and the evaluation plan
# (frozen document §6) reports per-check rates under these exact names.
CHECK_TEMPORAL = "temporal"
CHECK_TRANSPLANT = "transplant"
CHECK_CONTRADICTION = "contradiction"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

# The sections a check may be attributed to. FINDINGS is separated from the
# other two because the Gate C retry never regenerates it (frozen document
# §4.1) -- see _severity_for_field().
FIELD_FINDINGS = "findings"
FIELD_IMPRESSION = "impression"
FIELD_RECOMMENDATION = "recommendation"

# Structural facts, not tunable parameters, so they are named constants here
# rather than injected values:
#
# SUPPORTED_LANGUAGE -- all three checks are English-only by construction. The
# temporal terms are English word-boundary patterns, the transplant comparison
# is against an English neighbour corpus, and the labeler is an English BERT.
# This is not a setting a deployment can flip; changing it would require three
# different checks (frozen document §3.4).
SUPPORTED_LANGUAGE = "en"

# EXCLUDED_CONDITIONS -- "No Finding" cannot participate in a contradiction.
# Its head in the real CheXbert architecture has only 2 outputs, so it can
# never emit class 2 (Negative), and "Positive in one section, Negative in the
# other" is therefore not expressible for it. A property of the model, not a
# choice about clinical relevance.
EXCLUDED_CONDITIONS = ("No Finding",)

# CheXbert's own class indices (src/constants.py), reproduced here as named
# values so the contradiction rule reads as clinical logic rather than magic
# integers. {0: Blank, 1: Positive, 2: Negative, 3: Uncertain}.
CLASS_BLANK = 0
CLASS_POSITIVE = 1
CLASS_NEGATIVE = 2
CLASS_UNCERTAIN = 3

# Characters of context kept either side of a temporal match, so a violation
# can be read and adjudicated without re-opening the report.
_CONTEXT_CHARS = 90

_NGRAM_N = 5


def _tokens(text: str) -> list[str]:
    """Lowercase, strip every non-alphanumeric character, split on whitespace.

    Verbatim from scratch/phase22_diagnosis/measure_transplant.py -- see this
    module's docstring for why it was moved rather than rewritten. Any change
    here changes what diagnosis.md §2a's numbers mean and must be made in both
    places at once, with the verification script re-run.
    """
    out: list[str] = []
    for word in text.lower().split():
        word = "".join(ch for ch in word if ch.isalnum())
        if word:
            out.append(word)
    return out


def _five_grams(tokens: Sequence[str], n: int = _NGRAM_N) -> set[tuple[str, ...]]:
    """The SET of contiguous n-grams. Empty when there are fewer than n
    tokens, which is what makes a short impression unscorable for the ratio
    (diagnosis.md §5.1: 124 of 477 generated impressions) rather than scored
    as zero -- an unscorable case has no denominator, it is not a clean one.
    """
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _longest_common_token_run(a: Sequence[str], b: Sequence[str]) -> int:
    """Length, in tokens, of the longest CONTIGUOUS run common to both.

    Reported alongside the n-gram ratio and never averaged with it: the ratio
    answers "how much of this text appears somewhere in the neighbour", the
    run answers "what is the longest stretch copied verbatim". A report can
    score high on one and low on the other, and the two failures look
    different to a reader.
    """
    if not a or not b:
        return 0
    previous = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
        previous = current
    return best


def _longest_common_run_text(a: Sequence[str], b: Sequence[str]) -> str:
    """The copied span itself, as text, for ConsistencyViolation.evidence's
    `matched_span`. Separate from the length function so the hot path (which
    only needs a number) does not pay to rebuild the string."""
    if not a or not b:
        return ""
    previous = [0] * (len(b) + 1)
    best = 0
    best_end_a = 0
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
                    best_end_a = i
        previous = current
    return " ".join(a[best_end_a - best:best_end_a]) if best else ""


def _compile_term(term: str) -> re.Pattern[str]:
    """Word-boundary, case-insensitive, multi-word aware.

    Multi-word terms ("compared with") are joined on `\\s+` so a line break or
    a double space between the words still matches. The leading/trailing `\\b`
    is what stops "stable" matching inside "unstable" -- there is no word
    boundary between "un" and "stable", so the pattern correctly does not fire.
    """
    parts = [re.escape(part) for part in term.split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b", re.IGNORECASE)


class ReportConsistencyService:
    """Satisfies domain.interfaces.IReportConsistencyChecker."""

    def __init__(
        self,
        temporal_terms: Sequence[str],
        labeler=None,
        transplant_ratio_threshold: float | None = None,
        transplant_lcs_threshold: int | None = None,
    ) -> None:
        """
        temporal_terms
            The prompt-side term list (frozen document §2(iii) / §3.1),
            injected from Settings.consistency_temporal_terms. These are the
            SAME terms the generation prompt names, which is deliberate: the
            instruction is meant to be followable. The consequence is that
            this check alone cannot distinguish a real fix from
            word-avoidance, which is why the evaluation ALSO scores a
            held-out synonym list -- that list is frozen in the architecture
            document, is scoring-only, and deliberately appears NOWHERE under
            backend/, because a term the model could be trained or prompted
            against is no longer held out.

        labeler
            Optional ISectionLabeler. When None, the contradiction check does
            not run and is OMITTED from checks_run -- never reported as
            passing. A check that could not run and a check that ran clean are
            different states and this service never conflates them.

        transplant_ratio_threshold / transplant_lcs_threshold
            Gate B's calibration outputs (frozen document §3.2). Both None
            until Gate B, and with both None the transplant check computes and
            exposes its scores but emits no violation. They are constructor
            parameters, not module constants, precisely so Gate B can supply a
            measured value without editing this file.
        """
        if not temporal_terms:
            # Not a style check. An empty term list makes the temporal check
            # unconditionally silent while still reporting itself in
            # checks_run -- i.e. it would claim to have checked for fabricated
            # comparison language and always find none. Failing at
            # construction is the only safe behaviour; a check that quietly
            # stops checking is the exact failure mode this service exists to
            # prevent.
            raise ValueError("CONSISTENCY_TEMPORAL_TERMS must contain at least one term")

        self._temporal_terms = tuple(temporal_terms)
        self._temporal_patterns = tuple(
            (term, _compile_term(term)) for term in self._temporal_terms
        )
        self._labeler = labeler
        self._transplant_ratio_threshold = transplant_ratio_threshold
        self._transplant_lcs_threshold = transplant_lcs_threshold

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def check(
        self,
        content: ReportContent,
        context: ClinicalContext,
        retrieved_cases: Sequence[RetrievedCase],
        language: str,
        has_prior_study: bool,
    ) -> ConsistencyResult:
        """Run every check that CAN run, and report honestly which did.

        `context` is accepted for interface symmetry with the other
        collaborators and for the checks Gate B/C may add; the transplant
        check reads neighbour text from `retrieved_cases`, which is the
        argument that carries it.
        """
        if language != SUPPORTED_LANGUAGE:
            # Frozen document §3.4: every check is English-only. Returning an
            # empty checks_run is the whole point -- the caller and the UI
            # must be able to see that nothing was evaluated, rather than
            # inferring "clean" from an empty violations list.
            return ConsistencyResult(
                violations=(), has_violation=False, checks_run=(), retry_count=0
            )

        violations: list[ConsistencyViolation] = []
        checks_run: list[str] = []

        violations.extend(self._temporal_violations(content, has_prior_study))
        checks_run.append(CHECK_TEMPORAL)

        violations.extend(self._transplant_violations(content, retrieved_cases))
        checks_run.append(CHECK_TRANSPLANT)

        if self._labeler is not None:
            violations.extend(self._contradiction_violations(content))
            checks_run.append(CHECK_CONTRADICTION)

        return ConsistencyResult(
            violations=tuple(violations),
            has_violation=bool(violations),
            checks_run=tuple(checks_run),
            # Gate A is observational: this service performs no retry, so the
            # count is 0 by construction rather than by coincidence. Gate C
            # sets it from the caller's retry loop.
            retry_count=0,
        )

    def transplant_scores(
        self, content: ReportContent, retrieved_cases: Sequence[RetrievedCase]
    ) -> dict:
        """The transplant measurement, exposed independently of whether it
        crosses a threshold.

        Public because Gate B has to calibrate the threshold from real scores,
        and with the threshold at None `check()` emits no violation to carry
        them. Returning them here means the numbers are available to the
        calibration without the service having to invent a cut-point in order
        to record anything.

        Shape matches ConsistencyViolation.evidence for the transplant check,
        so the calibrated version needs no second format.
        """
        generated = _tokens(content.impression)
        grams = _five_grams(generated)

        best_ratio = 0.0
        best_lcs = 0
        ratio_uid: str | None = None
        lcs_uid: str | None = None
        matched_span = ""

        for case in retrieved_cases:
            neighbour = _tokens(case.impression)
            if grams:
                overlap = len(grams & _five_grams(neighbour)) / len(grams)
                if overlap > best_ratio:
                    best_ratio = overlap
                    ratio_uid = case.source_uid
            run = _longest_common_token_run(generated, neighbour)
            if run > best_lcs:
                best_lcs = run
                lcs_uid = case.source_uid
                matched_span = _longest_common_run_text(generated, neighbour)

        return {
            # None, not 0.0, when the impression is too short to have a
            # 5-gram: an unscorable case is not a case that scored zero.
            "ratio": round(best_ratio, 4) if grams else None,
            "lcs_tokens": best_lcs,
            "neighbour_uid": lcs_uid or ratio_uid,
            "ratio_neighbour_uid": ratio_uid,
            "matched_span": matched_span,
            "scorable": bool(grams),
            "n_neighbours": len(retrieved_cases),
        }

    # ------------------------------------------------------------------
    # checks
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_for_field(field: str) -> str:
        """Frozen document §4.1: a violation in FINDINGS is warning-only,
        because the Gate C retry regenerates impression/recommendation and
        never findings. Raising an error the remedy cannot address would mean
        either a retry that rewrites the wrong sections or a permanently
        failing report.

        This matters quantitatively, not just in principle: temporal terms are
        far commoner in findings than in impression in the real Arm C baseline
        (stable 96 vs 44, unchanged 27 vs 6, interval 27 vs 5 --
        diagnosis.md §2b), so MOST temporal violations are warning-only.
        """
        return SEVERITY_WARNING if field == FIELD_FINDINGS else SEVERITY_ERROR

    def _temporal_violations(
        self, content: ReportContent, has_prior_study: bool
    ) -> list[ConsistencyViolation]:
        """Frozen document §3.1. Deterministic, no model.

        With a real prior study the language is legitimate and nothing is
        emitted -- the check still RAN, and still appears in checks_run.
        """
        if has_prior_study:
            return []

        found: list[ConsistencyViolation] = []
        for field in (FIELD_FINDINGS, FIELD_IMPRESSION, FIELD_RECOMMENDATION):
            text = getattr(content, field, "") or ""
            for term, pattern in self._temporal_patterns:
                for match in pattern.finditer(text):
                    start = max(0, match.start() - _CONTEXT_CHARS)
                    end = min(len(text), match.end() + _CONTEXT_CHARS)
                    found.append(
                        ConsistencyViolation(
                            check=CHECK_TEMPORAL,
                            severity=self._severity_for_field(field),
                            field=field,
                            detail=(
                                f'"{match.group(0)}" implies comparison with an earlier '
                                f"examination, but this patient has no prior study"
                            ),
                            evidence={
                                "term": term,
                                "section": field,
                                "span": [match.start(), match.end()],
                                "context": text[start:end].strip(),
                            },
                        )
                    )
        return found

    def _transplant_violations(
        self, content: ReportContent, retrieved_cases: Sequence[RetrievedCase]
    ) -> list[ConsistencyViolation]:
        """Frozen document §3.2.

        Gate A: both thresholds are None, so the scores are computed (and are
        retrievable via transplant_scores()) and NO violation is emitted. This
        is not the check being disabled -- it ran, and it appears in
        checks_run. It has nothing to compare its scores against until Gate B
        calibrates one, and diagnosis.md §5.2 is why that calibration is not a
        formality: 73.5% of perfect-overlap copies are benign stock phrasing,
        so a cut-point on overlap alone would fire on all 83 of them.
        """
        if self._transplant_ratio_threshold is None and self._transplant_lcs_threshold is None:
            return []

        scores = self.transplant_scores(content, retrieved_cases)
        ratio = scores["ratio"]
        lcs = scores["lcs_tokens"]

        ratio_hit = (
            self._transplant_ratio_threshold is not None
            and ratio is not None
            and ratio >= self._transplant_ratio_threshold
        )
        lcs_hit = (
            self._transplant_lcs_threshold is not None
            and lcs >= self._transplant_lcs_threshold
        )
        if not (ratio_hit or lcs_hit):
            return []

        return [
            ConsistencyViolation(
                check=CHECK_TRANSPLANT,
                severity=self._severity_for_field(FIELD_IMPRESSION),
                field=FIELD_IMPRESSION,
                detail=(
                    f"impression reproduces text from retrieved case "
                    f"{scores['neighbour_uid']} (5-gram overlap {ratio}, "
                    f"longest copied run {lcs} tokens), which is another patient's report"
                ),
                evidence={
                    "neighbour_uid": scores["neighbour_uid"],
                    "ratio": ratio,
                    "lcs_tokens": lcs,
                    "matched_span": scores["matched_span"],
                },
            )
        ]

    def _contradiction_violations(self, content: ReportContent) -> list[ConsistencyViolation]:
        """Frozen document §3.3.

        The two sections are labelled SEPARATELY and never concatenated --
        which is precisely the defect that makes ResponseValidator unable to
        see this class of failure (it builds one combined string before
        inspecting anything).

        STRICT only: Positive in one section and Negative in the other. A
        label present in one section and merely ABSENT from the other is not a
        violation -- that is ordinary summarisation, and treating it as one
        would fire on 62.9% of real reports (diagnosis.md §2c). Uncertain is
        not treated as positive here for the same reason the strict reading
        exists: a hedge is not an assertion.
        """
        conditions = self._labeler.conditions
        rows = self._labeler.label([content.findings, content.impression])
        findings_classes, impression_classes = rows[0], rows[1]

        found: list[ConsistencyViolation] = []
        for index, condition in enumerate(conditions):
            if condition in EXCLUDED_CONDITIONS:
                continue
            f_class = findings_classes[index]
            i_class = impression_classes[index]
            contradicts = (
                (f_class == CLASS_POSITIVE and i_class == CLASS_NEGATIVE)
                or (f_class == CLASS_NEGATIVE and i_class == CLASS_POSITIVE)
            )
            if not contradicts:
                continue

            asserted_in = FIELD_FINDINGS if f_class == CLASS_POSITIVE else FIELD_IMPRESSION
            negated_in = FIELD_IMPRESSION if f_class == CLASS_POSITIVE else FIELD_FINDINGS
            found.append(
                ConsistencyViolation(
                    check=CHECK_CONTRADICTION,
                    # Attributed to IMPRESSION regardless of which side
                    # asserted: impression is the section the Gate C retry can
                    # actually regenerate, and a contradiction is a property of
                    # the pair, not of one member. Findings stays the grounding
                    # anchor (frozen document §4 step 2).
                    severity=self._severity_for_field(FIELD_IMPRESSION),
                    field=FIELD_IMPRESSION,
                    detail=(
                        f'"{condition}" is asserted in {asserted_in} but explicitly '
                        f"negated in {negated_in}"
                    ),
                    evidence={
                        "label": condition,
                        "findings_class": int(f_class),
                        "impression_class": int(i_class),
                    },
                )
            )
        return found
