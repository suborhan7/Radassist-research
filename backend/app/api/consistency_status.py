"""
app/api/consistency_status.py
====================================================================
The ONE place the consistency status is derived. Phase 22 v1.2, frozen
architecture §3/§5 (docs/phase22/fix_architecture_v1.2_FROZEN.md, frozen at
docs commit 810240ea).

Why a shared function rather than a computed property on each response
builder: the status collapses two nullable columns into one word a clinician
reads, and the whole point of the frozen §5 schema is that NULL and [] mean
different things. Two copies of that collapse would eventually disagree, and
the direction they would disagree in is the dangerous one -- some caller
rendering "not assessed" as a clean tick. One function, used by every
endpoint, so there is a single place to audit and a single place to change.

THE RULES (frozen §5's NULL-vs-[] distinction, applied):

    checks_run NULL or []        -> "not_run"
    checks_run non-empty, violations == []   -> "clean"
    violations non-empty         -> "violations"

A pre-v1.2 row has all three columns NULL and therefore reports "not_run",
which is the honest answer: nothing was ever assessed about it.

A Bengali report stores checks_run == [] because all three checks are
English-only (frozen §3.4), so it also reports "not_run" -- never "clean".
That is the case this whole mechanism exists for: a report nobody checked
must not look like a report that passed.
"""
from __future__ import annotations

from collections.abc import Sequence

STATUS_NOT_RUN = "not_run"
STATUS_CLEAN = "clean"
STATUS_VIOLATIONS = "violations"


def derive_consistency_status(
    checks_run: Sequence[str] | None,
    violations: Sequence[object] | None,
) -> str:
    """Collapse the two persisted columns into one status word.

    Order of the branches is deliberate and is the safety property of this
    function: "not_run" is decided FIRST, so no combination of inputs can
    reach "clean" without a non-empty `checks_run`. A report is only ever
    described as clean when something actually checked it.
    """
    if not checks_run:
        # Covers NULL (pre-v1.2 rows, or a check that raised) and []
        # (non-English, where zero checks are applicable). Both mean the
        # same thing to a reader: nothing was assessed.
        return STATUS_NOT_RUN

    if violations is None:
        # Not reachable through ReportGenerationService, which writes a real
        # list whenever any check ran. Handled anyway, and handled as
        # "not_run" rather than "clean": a non-empty checks_run with no
        # violations list is an inconsistent record, and the safe reading of
        # an inconsistent record is that nothing can be claimed from it.
        return STATUS_NOT_RUN

    return STATUS_VIOLATIONS if len(violations) > 0 else STATUS_CLEAN


def build_consistency_response(
    violations: Sequence[dict] | None,
    checks_run: Sequence[str] | None,
    retry_count: int | None,
):
    """Build the API block from the three PERSISTED column values.

    Imported lazily inside the function to keep this module free of a
    circular import with app.api.schemas, which imports nothing from here.

    Every endpoint that serves a consistency block goes through this one
    function, so the status word and the payload beside it are always built
    together from the same three inputs.
    """
    from app.api.schemas import ConsistencyResponse, ConsistencyViolationResponse

    return ConsistencyResponse(
        status=derive_consistency_status(checks_run, violations),
        checks_run=list(checks_run or []),
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
