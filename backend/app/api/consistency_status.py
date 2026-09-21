"""
app/api/consistency_status.py
====================================================================
The ONE place the consistency status is derived. Phase 22 v1.2, frozen
architecture §3/§5 (docs/phase22/fix_architecture_v1.2_FROZEN.md, frozen at
docs commit 810240ea), AS AMENDED by
docs/phase22/amendment_01_consistency_status.md (2026-09-21), which adds the
fourth status "partial".

Why a shared function rather than a computed property on each response
builder: the status collapses the persisted columns into one word a clinician
reads, and the whole point of the frozen §5 schema is that NULL and [] mean
different things. Two copies of that collapse would eventually disagree, and
the direction they would disagree in is the dangerous one -- some caller
rendering "not assessed" as a clean tick. One function, used by every
endpoint, so there is a single place to audit and a single place to change.

THE RULES, in this order (amendment 01(c)):

    checks_run NULL or []                      -> "not_run"
    any violation                              -> "violations"
    checks_run a STRICT SUBSET of applicable   -> "partial"
    otherwise                                  -> "clean"

`applicable` is `report_consistency_service.applicable_checks(language)` --
the single definition of what a report in that language is entitled to. It is
a function of language alone, never of how the running deployment happens to
be configured, so a stored row can be re-derived from its own `language`
column without knowing anything about the process that wrote it.

WHY "partial" EXISTS. Before this amendment, a report where only some checks
ran and those found nothing reported "clean" -- A4 decision #5, which
overstated assurance: a missing contradiction check disappeared into a clean
verdict. "partial" says what actually happened.

CONSEQUENCE, stated plainly: until Gate B calibrates the transplant
threshold, that check cannot emit a violation and is therefore not listed in
checks_run (amendment 01(b)), so **every English report reads "partial"**.
That is correct rather than unfortunate -- one of the three checks genuinely
is not yet operational, and the status now says so instead of implying a
completeness the system does not have.

A pre-v1.2 row has all three columns NULL and reports "not_run": nothing was
ever assessed about it.

A Bengali report stores checks_run == [] because all three checks are
English-only (frozen §3.4), so it also reports "not_run" -- never "clean" and
never "partial". Both its checks_run and its applicable set are empty, and
"not_run" is decided before the subset comparison is reached.
"""
from __future__ import annotations

from collections.abc import Sequence

STATUS_NOT_RUN = "not_run"
STATUS_CLEAN = "clean"
STATUS_PARTIAL = "partial"
STATUS_VIOLATIONS = "violations"


def derive_consistency_status(
    checks_run: Sequence[str] | None,
    violations: Sequence[object] | None,
    applicable: Sequence[str] | None = None,
) -> str:
    """Collapse the persisted columns into one status word.

    Branch order is the safety property of this function and is not
    incidental:

      1. "not_run" is decided FIRST, so no combination of inputs can reach
         "clean" or "partial" without a non-empty `checks_run`. A report is
         only ever described as assessed when something actually assessed it.
      2. "violations" outranks "partial" (amendment 01(c)): a report with a
         real violation is reported as having one even if other checks did
         not run. The violation is the actionable fact; the incompleteness is
         secondary and is still recoverable from `checks_run`.
      3. "partial" requires a STRICT subset. Equality means every applicable
         check ran, which is the only route to "clean".

    `applicable` defaults to None for callers that cannot supply it; with
    None the subset test is skipped and the result is the pre-amendment
    behaviour. Every production call site passes it -- the default exists so
    a caller that genuinely does not know the language is not forced to
    invent one.
    """
    if not checks_run:
        # Covers NULL (pre-v1.2 rows, or a check that raised) and []
        # (non-English, where zero checks are applicable). Both mean the same
        # thing to a reader: nothing was assessed.
        return STATUS_NOT_RUN

    if violations is None:
        # Not reachable through ReportGenerationService, which writes a real
        # list whenever any check ran. Handled anyway, and handled as
        # "not_run" rather than "clean": a non-empty checks_run with no
        # violations list is an inconsistent record, and the safe reading of
        # an inconsistent record is that nothing can be claimed from it.
        return STATUS_NOT_RUN

    if len(violations) > 0:
        return STATUS_VIOLATIONS

    if applicable is not None and set(checks_run) < set(applicable):
        return STATUS_PARTIAL

    return STATUS_CLEAN


def build_consistency_response(
    violations: Sequence[dict] | None,
    checks_run: Sequence[str] | None,
    retry_count: int | None,
    language: str | None = None,
):
    """Build the API block from the persisted column values plus the report's
    language, which is what determines the applicable set.

    Imported lazily inside the function to avoid a circular import with
    app.api.schemas, which imports STATUS_NOT_RUN from here at module level.

    Every endpoint that serves a consistency block goes through this one
    function, so the status word and the payload beside it are always built
    together from the same inputs.
    """
    from app.api.schemas import ConsistencyResponse, ConsistencyViolationResponse
    from app.services.report_consistency_service import applicable_checks

    applicable = applicable_checks(language) if language is not None else None

    return ConsistencyResponse(
        status=derive_consistency_status(checks_run, violations, applicable),
        checks_run=list(checks_run or []),
        # Surfaced beside checks_run so a client can show WHICH checks are
        # missing, not merely that some are. A status word alone cannot carry
        # that, and the amendment's whole purpose is to stop incompleteness
        # being invisible.
        applicable_checks=list(applicable or []),
        violations=[
            ConsistencyViolationResponse(
                check=v.get("check", ""),
                severity=v.get("severity", ""),
                field=v.get("field", ""),
                detail=v.get("detail", ""),
                evidence=v.get("evidence", {}) or {},
            )
            for v in (violations or [])
        ],
        retry_count=retry_count,
    )
