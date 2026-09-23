# Amendment 01 — Consistency Status: adding `partial`

| | |
|---|---|
| **Date** | 2026-09-21 |
| **Amends** | [`fix_architecture_v1.2_FROZEN.md`](fix_architecture_v1.2_FROZEN.md) **§3** (`ConsistencyResult` / `checks_run`) and **§5** (persistence and the status a reader sees) |
| **Frozen document commit** | `810240ea` |
| **Implemented in** | Step A4.1, commit 1 |
| **Status** | **Adopted.** The frozen document is not edited; this amendment sits alongside it and takes precedence on the points below. |

---

## 1. Why

Step A4 wired the consistency service and, where the frozen document was
silent, made nine decisions. Review ratified eight and flagged one:

> **A4 decision #5 — partial checks still report status `"clean"`.** With no
> labeler, two of three checks run; if they find nothing, the rule yields
> `"clean"`. This overstates assurance: the contradiction check never ran.

That is the exact failure mode Phase 22 exists to remove — an unchecked thing
presenting as a checked-and-satisfactory thing. It was the right call *given
the three statuses the frozen document defines*, which is why it was raised
for amendment rather than fixed silently.

This amendment adds the missing status and, in doing so, exposes a second,
larger instance of the same problem that A4 had not surfaced: **the transplant
check was being listed as having run while it was structurally incapable of
reporting anything**, because its threshold is deferred to Gate B.

---

## 2. What changes

### (a) A fourth status: `partial`

The status vocabulary becomes:

| status | meaning |
|---|---|
| `not_run` | nothing was assessed |
| `partial` | **some but not all** applicable checks ran, and those that ran found nothing |
| `clean` | every applicable check ran and found nothing |
| `violations` | at least one violation was found |

`partial` **must not be rendered as a pass.** It is closer to `not_run` than
to `clean` in what it licenses a reader to conclude.

### (b) The applicable-checks rule

> **A check is listed in `checks_run` only if it is capable of emitting a
> violation.**

Consequence, and the reason this clause exists: **the transplant check is
scored in every run but is NOT listed in `checks_run` while its threshold is
`None`** — that is, until Gate B calibrates it.

The scoring still happens on every report. `transplant_scores()` remains
public and is what Gate B will calibrate from; nothing is lost. What changes
is that the report no longer *claims* to have been checked for
transplantation when no cut-point existed against which anything could have
been found.

This is the same principle as (a), applied to a case A4 had not noticed: a
check that cannot fail is not a check that passed.

### (c) The derivation, in order

```
checks_run is NULL or empty                     -> "not_run"
any violation present                           -> "violations"
checks_run is a STRICT SUBSET of applicable     -> "partial"
otherwise                                       -> "clean"
```

Three properties of the ordering, each deliberate:

1. **`not_run` is decided first**, so no input combination can reach `clean`
   or `partial` without a non-empty `checks_run`. A report is only ever
   described as assessed when something assessed it.
2. **`violations` outranks `partial`.** A report with a real violation is
   reported as having one even when the check set is incomplete. The
   violation is the actionable fact; the incompleteness is secondary and
   remains recoverable from `checks_run`.
3. **`partial` requires a *strict* subset.** Equality means every applicable
   check ran, which is the only route to `clean`.

### (d) One definition of the applicable set

```python
# app/services/report_consistency_service.py
ALL_CHECKS = (CHECK_TEMPORAL, CHECK_TRANSPLANT, CHECK_CONTRADICTION)

def applicable_checks(language: str) -> tuple[str, ...]:
    return ALL_CHECKS if language == SUPPORTED_LANGUAGE else ()
```

**A function of language alone, never of deployment configuration.** This is
load-bearing. Were "applicable" to mean "what this process is currently
configured to run", a degraded deployment would compute
`applicable == checks_run` and report `clean` — reintroducing the very
overstatement this amendment removes, in a harder-to-notice form. Defining it
by language also means a stored row can be re-derived from its own `language`
column, without knowing anything about the process that wrote it.

A non-English report has an empty applicable set and an empty `checks_run`,
so it resolves at branch 1 to `not_run` — never `partial`, never `clean`.

The API additionally surfaces `applicable_checks` beside `checks_run`, so a
client can show **which** checks are missing by name, not merely that some
are. A status word cannot carry that, and making incompleteness visible is
the point.

### (e) Consequence, stated plainly

> **Until Gate B calibrates the transplant threshold, every English report
> reads `partial`.**

This is correct, not unfortunate. One of the three checks genuinely is not
operational. The previous behaviour — reporting `clean` — asserted a
completeness the system does not have. A dashboard that looks worse after
this amendment is a dashboard that has started telling the truth.

When Gate B supplies a threshold, transplant becomes listed, and an English
report with a labeler and no violations reaches `clean` by the ordinary
route. No code change is needed for that transition: the threshold arrives
through the constructor.

---

## 3. Existing rows are not rewritten

No migration, no backfill, no data update. Counted at the time of writing:

```sql
select count(*) from reports;                                        -- 1802
select count(*) from reports where consistency_checks_run is null;   -- 1796
select count(*) from reports where consistency_checks_run = '[]';    --    2
select count(*) from reports where consistency_checks_run is not null; -- 6
select count(*) from reports
  where consistency_checks_run like '%transplant%';                  --    4
```

How each group reads under the new derivation:

| rows | stored `checks_run` | reads as | correct? |
|---|---|---|---|
| **1796** | `NULL` (pre-v1.2) | `not_run` | Yes — unchanged, nothing was assessed |
| **2** | `[]` (Bengali, A4) | `not_run` | Yes — unchanged |
| **4** | `["temporal","transplant","contradiction"]` (English, A4) | `clean` | **No — these overstate** |

**The four English rows written by A4 will read `clean` when they should read
`partial`**, because A4 stored `transplant` in `checks_run` under the old rule
and the derivation trusts the stored list.

This is recorded rather than repaired, for three reasons. The rows are four
smoke-test reports generated by this workstream, not clinical records. A data
migration that rewrote stored history to match a later rule would make the
persisted `checks_run` a derived value rather than a record of what actually
happened — which is worse than a bounded, documented inconsistency. And
`created_at` distinguishes them precisely: any row with a non-NULL
`consistency_checks_run` written before this amendment's commit is subject to
it.

**No such row may be cited as evidence that a report was fully checked.** Any
future evaluation reading these columns must filter to rows written after this
commit, or recompute from `language` and the stored violation list.

---

## 4. Disposition of the nine A4 decisions

All nine were raised in the A4 dev log for ratification.

| # | Decision | Disposition |
|---|---|---|
| 1 | `ReportDetail` / `ReportDetailService` modified to carry the columns so `GET /reports/{id}` can serve them | **Ratified** |
| 2 | `generate()` returns a 5-tuple including the persisted snapshot | **Ratified, refactored in commit 2** (becomes `GenerationOutcome`) |
| 3 | `regenerate_section()` returns a 3-tuple | **Ratified, refactored in commit 2** (becomes `RegenerationOutcome`) |
| 4 | The regeneration check runs on the candidate **in context** (current `final_content` with the regenerated field substituted) | **Ratified** |
| 5 | Partial checks still report `"clean"` | **SUPERSEDED BY THIS AMENDMENT** — see §1, §2(a) |
| 6 | An inconsistent record (`checks_run` non-empty, `violations` NULL) reads as `not_run` | **Ratified** |
| 7 | The response block defaults to `not_run` when omitted | **Ratified** |
| 8 | The report id is generated before persistence so a failing check can be logged against it | **Ratified** |
| 9 | A per-request INFO log line records `check()` duration | **Ratified** |

Decisions 2 and 3 are ratified **as decisions** — returning the snapshot
rather than re-reading the row, and returning the candidate's verdict — and
only their *shape* changes in commit 2. Positional tuples were already at
five and three elements with more expected (D5's attempt count), which is the
point at which named fields stop being a style preference.

---

## 5. What this amendment does not change

- The three checks themselves, their logic, and their thresholds.
- The frozen §5 column schema. No migration.
- The NULL-vs-`[]` distinction, which this amendment depends on and extends.
- Gate A's observational property: no retry, nothing blocked, no generated
  text altered. The byte-identity test still passes with its assertions
  unchanged.
- The Gate B transplant threshold, still the single parameter deferred by
  design.
