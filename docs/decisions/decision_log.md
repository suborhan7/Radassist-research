# Decision Log

Index of numbered project decisions (`D*`) and frozen design rules (`DR-*`).

**Purpose.** Several decisions are referenced by identifier across the dev log,
the frozen architecture documents and project chat, but there has been no single
place listing them. This file is that index. It is a **pointer table, not the
decisions themselves** — where a decision's full text lives in the repository,
this file cites the location rather than restating it, so there is only ever one
authoritative copy.

**Provenance rule.** Every entry states where its text actually lives, and there
are two kinds:

- **In repo** — the decision's full text exists in a repository document; this
  table points at it rather than restating it.
- **Summary only — source: project chat log** — the decision was taken in
  conversation and has no full text in this repository. The summary here is a
  faithful record of what that conversation settled, **not** a reconstruction, and
  it is usable. **Any thesis text relying on such an entry must cite it as sourced
  from the project chat log, with the date, rather than implying a repository
  document backs it.**

Created during Phase 22 Step 1b (structure, from a real search of `docs/`) and
completed in Step 1c, when the D2/D3/D5 text was supplied from the 2026-08-17
audit conversation. No entry below was inferred, reconstructed or invented; where
the repo is silent, this file says so and names the real source instead.

---

## Decisions (`D*`)

| ID | One-line summary | Status | Source of record |
|---|---|---|---|
| **D1** | Pipeline invariant, corrected wording: **`admit → mask → embed → gate → retrieve`**. The admission step runs on the raw upload before masking (an unsafe file must never reach the OCR library); the gate step runs after embedding and reuses the same vector. | **Approved; wording corrected, approval status unchanged.** Intent never changed — only the words. | In repo: [`input_admission_projection_gate_architecture_v1.1_FROZEN.md` §3.3](../methodology/input_admission_projection_gate_architecture_v1.1_FROZEN.md), and dev log narrative at `development_log.md:10564`. |
| **D2** | **Phase 21 arm switching in `ReportGenerationService` via two-context construction**: the *arm* context goes to the LLM, the *reference* context goes to `validate_semantic()`. Mandatory for measurement hygiene — `validation_result` is itself a Phase 21 outcome measure, so validating an arm-suppressed context against itself would make the outcome a function of the arm rather than of the generated text. Holds **even though `validate_semantic()` is advisory** and gates nothing. | **Approved.** Freeze sequenced **after** D1/D4/D5. | **Summary only — source: project chat log, 2026-08-17 audit conversation.** No full text in repo. |
| **D3** | **No standalone baseline arm (approved).** Marker-format failure rate deferred to Phase 21 output rather than measured by a dedicated arm. | **Approved, but its deferred measurement is blocked by D5.** An attempt-1 structural failure followed by an attempt-2 success is currently invisible, so the true content-validation rate is **unmeasurable** until the attempt count is recorded. | **Summary only — source: project chat log, 2026-08-17 audit conversation.** No full text in repo. |
| **D4** | `voted_labels` and `agreement` must be **stored at generation time**, not recomputed on read — the evidence state must not change after the report exists. | **Approved and now implemented.** Originally assumed to have a migration that did not exist (correction recorded in the v1.1 frozen doc §S5/S6); migration `c3d81b6a4f27_add_voted_labels_and_agreement_to_reports.py` subsequently created both columns. | In repo: [`input_admission_projection_gate_architecture_v1.1_FROZEN.md` §S5 Note / correction](../methodology/input_admission_projection_gate_architecture_v1.1_FROZEN.md); migration `backend/alembic/versions/c3d81b6a4f27_*.py`. |
| **D5** | **Record the structural attempt count.** Preferred design: **widen `generate_draft()`'s return type** to carry the attempt count and the final structural errors, rather than inject a per-call recorder. Whether to persist it to `ReportRecord` is a **separate question**, not settled by this decision. Known confound: attempts ≥ 2 use `build_retry_prompt`, i.e. a *different prompt*, so attempt counts are not exchangeable observations. | **Open — not scoped, not scheduled.** Blocks D3. Explicitly **not** bundled into Phase 22 v1.2 (see note below). | **Summary only — source: project chat log, 2026-08-17 audit conversation.** No full text in repo. |

### Note on D5 and Phase 22

D5 concerns the **structural/content retry** loop in
`LLMOrchestrator.generate_draft()` — the existing `LLM_CONTENT_RETRY_COUNT` (2)
loop that re-prompts when `StructuralValidator` rejects a response
([`llm_orchestrator.py:61-75`](../../backend/app/services/llm_orchestrator.py#L61-L75),
[`config.py:53`](../../backend/app/core/config.py#L53)). How many of those
attempts a given report consumed is **not persisted anywhere today** — no column
on `ReportRecord` records it.

**D5 is not the consistency retry.** Phase 22's proposed
`consistency_retry_count` ([`fix_architecture_v1.2_FROZEN.md` §4-§5](../phase22/fix_architecture_v1.2_FROZEN.md))
counts a *different*, new, semantic retry with its own budget. The two are
independent mechanisms with independent budgets and must not be conflated or
stored in one column.

**D5 remains a separate, unscoped migration and is deliberately not bundled into
v1.2.** v1.2 adds `consistency_retry_count`; it does **not** add a structural
retry-attempt column. Bundling them would tie an open, unscoped decision to a
fix that is ready to evaluate, and would let D5's scope be settled implicitly by
Phase 22 rather than deliberately on its own terms.

---

## Design rules (`DR-*`)

| ID | One-line summary | Status | Source of record |
|---|---|---|---|
| **DR-4** | **The system accepts frontal chest radiographs only.** Adds a declared-projection branch at admission — architectural, not editorial. | **Frozen (v1.1).** New in v1.1. Test T2 (which asserted a lateral image passes all checks, contradicting DR-4) was removed; T15 tests the correct behaviour. | In repo: [`input_admission_projection_gate_architecture_v1.1_FROZEN.md` §DR-4](../methodology/input_admission_projection_gate_architecture_v1.1_FROZEN.md) (lines 10, 23, 41, 45); dev log at `development_log.md:10620-10624, 10730, 10824`. |
| **DR-5** | **Two thresholds on the top-1 similarity, not one.** Adds a post-retrieval projection-mismatch branch — architectural, not editorial. | **Frozen (v1.1).** New in v1.1. | In repo: [`input_admission_projection_gate_architecture_v1.1_FROZEN.md` §DR-5](../methodology/input_admission_projection_gate_architecture_v1.1_FROZEN.md) (lines 10, 24); dev log at `development_log.md:10620-10621, 10828`. |

> **DR-4 Reason 1 caveat, carried from the frozen document:** Reason 1 no longer
> attributes a clinical opinion, because that opinion is not recorded in this
> project. See DR-4 Reason 1a in the frozen document.

---

## Related audit decisions (not separately numbered)

**Validation warnings describe the AI draft only, and are not recomputed after
doctor edits.** `ReportRecord.validation_warnings` is written once, at generation
time, from `validate_semantic()` run against `ai_draft_content`. `PATCH
/reports/{id}` may subsequently change `final_content` without the warnings being
recomputed — so a stored warning describes the **AI draft**, never the doctor's
edited text.

*Source: project chat log, 2026-08-17 audit conversation.*

This is the decision Phase 22's §4.3 had to remain consistent with. Phase 22
re-runs `validate_semantic()` after a consistency retry **at generation time
only**, on the post-retry AI draft — which keeps the invariant intact (warnings
still describe the AI draft that is persisted as `ai_draft_content`) rather than
weakening it. Phase 22 does **not** propose recomputing warnings after doctor
edits. See [`fix_architecture_v1.2_FROZEN.md` §4.3](../phase22/fix_architecture_v1.2_FROZEN.md).

---

## Open items for this log

1. **D2, D3 and D5 have no full text in the repository.** The summaries above come
   from the 2026-08-17 audit conversation and are complete only to the extent that
   conversation recorded them. For D5 in particular, the acceptance criteria and
   migration shape remain unsettled (and persisting to `ReportRecord` is explicitly
   an open sub-question).
2. **D5 is open and blocks D3.** Until the structural attempt count is recorded,
   the true content-validation rate is unmeasurable.
3. **Numbering is unverified.** Whether `D1`–`D5` is the complete set, or whether
   further decisions exist unnumbered, has not been established.

**Citation rule (unchanged).** Any thesis text relying on D2, D3, D5 or the
related audit decision above **must cite it as sourced from the project chat log
(2026-08-17 audit conversation), not from a repository document.** These entries
are records of decisions taken outside the repo; treating them as repo-backed
would misrepresent their provenance.
