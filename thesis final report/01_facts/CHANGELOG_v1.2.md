# Changelog — RadAssist-RAG v1.2 (Phase 22, Gate A)

**Range:** `810240ea` … `46d2632f` on branch `phase22-v1.2`
**Baseline tag:** `v1.1-evaluated` at `a107d4ef` (the system Phase 20/21 measured)

---

## Summary

A live report contradicted itself: the findings said the cardiomediastinal
silhouette was unremarkable, the impression said "Stable cardiomegaly with
right mediastinal shift". That impression turned out to be another patient's
impression, copied almost word for word from the top retrieved neighbour, and
"stable" referred to a prior study the patient did not have.

Diagnosis found this was not a one-off: across 477 evaluation reports, 35%
contained comparison language with no prior study, 23.5% of scorable
impressions reproduced a neighbour's impression exactly, and 4.6%
contradicted themselves between sections.

v1.2 changes the prompt in four ways — labelling retrieved text as other
patients' reports and forbidding copying, requiring the impression to follow
this report's findings, stating that no prior study exists, and giving
section regeneration the report's current findings. It adds a consistency
service that checks each report and records what it found, without altering
anything the model wrote.

Measured on all 477 cases: comparison language fell from 35.0% to 2.7%,
self-contradiction from 4.6% to 0.8%, copied impressions from 4.6% to 2.1%,
and clinical label agreement improved rather than degrading.

**Not done:** the warnings are not shown in the UI, one of the three checks
has no threshold yet, there is no automatic correction, Bengali is unchecked,
and a reader review is still pending.

---

## 1. Commits

| # | hash | title | changed |
|---|---|---|---|
| 1 | `b3271672` | feat: add ReportConsistencyService core (observational, unwired) | nothing (dead code) |
| 2 | `60603541` | feat: add CheXbert runtime labeler with verified label equivalence | nothing (dead code) |
| 3 | `06c0d68a` | feat: add nullable consistency columns to reports | **schema** |
| 4 | `f6b59eee` | feat: wire ReportConsistencyService in observational mode | **stored data, API** |
| 5 | `42bc93c3` | feat: add partial consistency status (amendment 01) | **stored data, API** |
| 6 | `05c116ff` | refactor: replace generation tuples with outcome dataclasses | nothing |
| 7 | `3015b08b` | test: make tampered-JWT test deterministic | nothing |
| 8 | `52884b0e` | feat: prompt grounding changes (i)-(iv) | **generated text** |
| 9 | `55e8bc08` | docs: gate A run plan (pre-registered, before run) | nothing |
| 10 | `c7eb0b08` | eval: gate A results | nothing (artifacts) |
| 11 | `46d2632f` | eval: gate A post-hoc analyses and pre-registration deviation record | nothing |

### 1 — `b3271672` · ReportConsistencyService core

**What.** New `app/services/report_consistency_service.py` (503 lines) with
three checks: temporal terms, neighbour transplant, findings/impression
contradiction. Domain types `ConsistencyViolation` / `ConsistencyResult` added
to `app/domain/entities.py`; `IReportConsistencyChecker` and `ISectionLabeler`
Protocols added to `app/domain/interfaces.py`; `CONSISTENCY_TEMPORAL_TERMS`
and `CONSISTENCY_RETRY_COUNT` added to `app/core/config.py`.

**Why.** The four root causes in [`diagnosis.md`](diagnosis.md) §3 needed a
component that could detect them. Kept separate from `validate_semantic()`
because that validator concatenates findings and impression before inspecting
them, so cross-section contradiction is not representable there at all
(§1d).

**Files.** `report_consistency_service.py`, `entities.py`, `interfaces.py`,
`config.py`, `test_report_consistency_service.py`, dev log.
**Tests.** +31 (module now 32 after amendment 01).
**Changed text/data/API?** **Nothing** — unwired; nothing constructed or
called it.

### 2 — `60603541` · CheXbert runtime labeler

**What.** New `app/infrastructure/chexbert_labeler.py` (353 lines)
implementing `ISectionLabeler`, returning raw 4-class indices. Config:
`CHEXBERT_CHECKPOINT_PATH`, `CHEXBERT_DEVICE`, `CHEXBERT_MAX_LENGTH`,
`CHEXBERT_BATCH_SIZE`.

**Why.** The contradiction check needs Negative distinguishable from
"not mentioned", which binarised labels destroy. `ml/evaluation/score_chexbert.py`
could not be imported (the `ml/`↔`backend/` boundary, and `transformers` 5.x
removed `encode_plus`), so the tokenisation was ported.

**Equivalence proven, not assumed.** `verify_chexbert_equivalence.py`:
954/954 token sequences identical, **0/13,356 label cells mismatched on CPU
and 0/13,356 on CUDA**. TF32 disabled inside the inference context — the
output is an argmax over 4 logits and TF32 flips near-ties.

**Files.** `chexbert_labeler.py`, `config.py`, `test_chexbert_labeler.py`,
dev log.
**Tests.** +25 (2 skip without the checkpoint).
**Changed text/data/API?** **Nothing** — unwired.

### 3 — `06c0d68a` · Consistency columns

**What.** Migration `7f2a91c4d6e8` adds three nullable columns to `reports`:
`consistency_violations` (JSON), `consistency_checks_run` (JSON),
`consistency_retry_count` (Integer). No backfill, no defaults.

**Why.** NULL and `[]` must stay distinguishable: NULL means nothing was
assessed, `[]` means the checks ran and found nothing. A default would
manufacture a recorded state for the 1,796 rows that never had one.

**Files.** `app/models/report.py`, `alembic/versions/7f2a91c4d6e8_*.py`, dev log.
**Tests.** +0 (verified directly against the live and model-built schemas).
**Changed text/data/API?** **Schema.** Requires `alembic upgrade head`.

### 4 — `f6b59eee` · Wiring (observational)

**What.** `ReportConsistencyService` and `ChexbertLabeler` constructed once in
`main.py`'s lifespan and injected into `ReportGenerationService` and
`ReportEditService`. `check()` runs after `validate_semantic()` and before
`render_disclaimer()`. Results persisted. `consistency` block added to
`GenerateReportResponse`, `ReportDetailResponse` and
`RegenerateSectionResponse`. Status derived in one place,
`app/api/consistency_status.py`.

**Why.** Frozen §3/§5. Observational so the detection could be evaluated
separately from acting on it.

**Key property, asserted by test.** The same fake LLM output generated with
and without the service injected produces **byte-identical** persisted content
and formatted report.

**Startup does not fail if the labeler is missing** — logged at warning, the
service is built with `labeler=None`, and `"contradiction"` is omitted from
`checks_run` rather than reported as passing.

**Files.** `main.py`, `report_generation_service.py`, `report_edit_service.py`,
`report_detail_service.py`, `consistency_status.py`, `schemas.py`,
`generation.py`, `reports.py`, 3 test modules, dev log.
**Tests.** +31 (28 new module + 3 in an existing one).
**Changed text/data/API?** **Stored data** (three columns now written) and
**API** (additive `consistency` block). **Generated text: unchanged** — that
is the point, and it is tested.

### 5 — `42bc93c3` · `partial` status (amendment 01)

**What.** Fourth status `partial`. A check is listed in `checks_run` only if
it *can* emit a violation, so the transplant check — threshold deferred to
Gate B — is scored but not counted as run. `applicable_checks` added to the
API. Documented in
[`amendment_01_consistency_status.md`](amendment_01_consistency_status.md).

**Why.** A4 decision #5 was flagged in review: a report where only some checks
ran and those found nothing reported `clean`, overstating assurance.
Implementing the fix exposed a larger instance — the transplant check was
being counted as run while structurally unable to report anything.

**Consequence.** Until Gate B, **every English report reads `partial`**. That
is correct: one of three checks is not operational.

**Existing rows not rewritten.** Of 1,802 reports at the time: 1,796 NULL and
2 Bengali read `not_run` correctly; **4 English rows written by commit 4 read
`clean` when they should read `partial`** (they stored `transplant` under the
old rule). Recorded, not migrated.

**Files.** `report_consistency_service.py`, `consistency_status.py`,
`schemas.py`, `generation.py`, `reports.py`, 2 test modules, amendment doc,
dev log.
**Tests.** +6, 4 existing updated.
**Changed text/data/API?** **Stored data** (`checks_run` contents) and **API**
(`status` vocabulary, new `applicable_checks` field).

### 6 — `05c116ff` · Outcome dataclasses

**What.** `ConsistencySnapshot`, `GenerationOutcome`, `RegenerationOutcome`
replace a 5-tuple and a 3-tuple. `RegenerationOutcome.language` removed a
database query commit 5 had added.

**Why.** Both returns had grown past the point where a caller can read a
position without counting commas, with D5's attempt count still expected.

**Files.** `entities.py`, `report_generation_service.py`,
`report_edit_service.py`, `generation.py`, `reports.py`, 3 test modules, dev log.
**Tests.** +0 (call sites updated).
**Changed text/data/API?** **Nothing** — no behaviour change; the byte-identity
test passes with its assertions unchanged.

### 7 — `3015b08b` · Deterministic tampered-JWT test

**What.** `test_jwt_verify_rejects_tampered_token` now decodes the signature,
flips one byte and re-encodes.

**Why.** It failed ~5% of runs, predating Phase 22. An HS256 signature is 32
bytes → 43 base64url characters; the final character carries 4 significant
bits plus 2 discarded padding bits, so flipping it to `"A"` left the decoded
bytes unchanged for characters A–D. Measured **268/5000 = 5.36%** over
distinct signatures; the fix gives **2000/2000**.

**Files.** `test_auth_infrastructure.py`, dev log.
**Tests.** +0 (one repaired).
**Changed text/data/API?** **Nothing.**

### 8 — `52884b0e` · Prompt grounding changes (i)–(iv)

**What.**
- **(i)** Evidence block now headed `EVIDENCE -- OTHER PATIENTS' REPORTS
  (reference only)`, stating the text is not this patient's history and
  prohibiting reproducing sentences or transferring findings, measurements,
  laterality or devices.
- **(ii)** New `SECTION SUPPORT INSTRUCTIONS`: findings first; impression a
  synthesis of this report's findings; recommendation preserving findings'
  location and laterality.
- **(iii)** `PRIOR STUDY` block stating no prior exists and naming the nine
  forbidden terms, sourced from `settings.consistency_temporal_terms` — the
  same list the checker matches on.
- **(iv)** Section regeneration receives `final_content["findings"]` for
  impression/recommendation; the role instruction now governs output, not
  context.

**Why.** The existing grounding instruction forbids only *invention*, which
verbatim copying satisfies ([`diagnosis.md`](diagnosis.md) §1b).

**Held-out containment.** `heldout_temporal_terms.txt` is generated from the
frozen document and diff-verified 10/10; no held-out term appears in any of
the 9 prompts the backend can send.

**Context window.** All 477 cases measured with `prompt_eval_count`: prompts
grew by exactly **+338 tokens** on every case; max 1,574 of 4,096, leaving
2,522 for output.

**Files.** `prompt_builder.py`, `report_edit_service.py`, `interfaces.py`,
`main.py`, 2 new test modules, 2 existing updated,
`heldout_temporal_terms.txt`, dev log.
**Tests.** +47 (31 + 16), 4 existing assertions updated.
**Changed text/data/API?** **Generated text.** This is the only commit that
changes what the model writes.

### 9–11 — `55e8bc08`, `c7eb0b08`, `46d2632f` · Evaluation

Run plan (pre-registered, 356 lines), Gate A results with 477 generated
reports and all artifacts (589 files), and the post-hoc analyses plus the
pre-registration deviation record. **No code changed in any of the three**
(`git diff 52884b0e..HEAD -- backend/ ml/ shared/` is empty).

---

## 2. User-visible behaviour changes

| change | detail |
|---|---|
| **Generated report text** | Impressions no longer assert findings the findings section did not state; comparison language largely gone; less text copied from retrieved neighbours. Reports are **shorter** — findings median 48 → 30 words, impression median 9 → 5 ([`gate_a_results.md`](gate_a_results.md) §6.1d). |
| **Explanation / chat assistant** | **Changed, and not evaluated.** `build_explanation_prompt()` reuses `_evidence_section()`, so change (i)'s attribution boundary and anti-copying prohibition now appear in the explainability prompt too. Intended — it shows the clinician the same other-patient text — but no endpoint measures explanation output. |
| **Section regeneration** | Regenerating impression or recommendation now sees the report's current findings. Previously the prompt told the model *not* to consider other sections. |
| **Comparison narrative** | **Unchanged**, byte-identical to `v1.1-evaluated` (asserted by test). It legitimately uses temporal language. |
| **Consistency warnings** | **Not surfaced in any UI.** Returned by the API and stored; no frontend change was made. |

## 3. API changes (all additive; no existing field changed)

| endpoint | change |
|---|---|
| `POST /generate-report` | `consistency` block added to the response |
| `GET /reports/{id}` | `consistency` block added |
| `POST /reports/{id}/regenerate-section` | `consistency` block added (the candidate's own verdict; not persisted) |

Block shape: `{status, checks_run[], applicable_checks[], violations[], retry_count}`.
`status` ∈ `not_run` \| `partial` \| `clean` \| `violations`.
**Contract:** `not_run` must render as "consistency checks not run" and never
as a clean state. `validation.is_clean` is unchanged.

## 4. Schema / migration

One migration, `7f2a91c4d6e8` (`06c0d68a`), adding three nullable columns to
`reports`. Verified against a copy of the live database with 1,794 rows: row
count unchanged, all rows NULL on all three, `alembic downgrade -1` drops
exactly those three and leaves `voted_labels`/`agreement` intact,
`alembic check` reports "No new upgrade operations detected."

**Deploy step:** `alembic upgrade head`.

## 5. New configuration

| setting | default | purpose |
|---|---|---|
| `CONSISTENCY_TEMPORAL_TERMS` | 9 pipe-separated terms | the one term list, used by both the prompt and the checker |
| `CONSISTENCY_RETRY_COUNT` | `1` | **unused in Gate A** — read first at Gate C |
| `CHEXBERT_CHECKPOINT_PATH` | local HF cache path | contradiction-check labeler |
| `CHEXBERT_DEVICE` | `auto` | cuda if available |
| `CHEXBERT_MAX_LENGTH` | `512` | BERT positional limit |
| `CHEXBERT_BATCH_SIZE` | `16` | |

## 6. Tests

| module | tests |
|---|---|
| `test_report_consistency_service.py` | 32 |
| `test_consistency_wiring.py` | 34 |
| `test_prompt_grounding_changes.py` | 31 |
| `test_chexbert_labeler.py` | 25 |
| `test_prompt_heldout_containment.py` | 16 |
| **new total** | **138** |
| suite before Phase 22 | 370 |
| **suite now** | **512**, zero failures |

(512 = 370 + 138 + 4 added to pre-existing modules.)

## 7. Tags and branches

| | |
|---|---|
| `v1.1-evaluated` | annotated tag at `a107d4ef` — the system Phase 20/21 measured |
| `phase22-v1.2` | all Phase 22 work; **not merged to `main`** |
| `main` | unchanged at `a107d4ef` |

---

## 8. Not done

Each with a measured size where one exists.

| # | gap | size / evidence |
|---|---|---|
| 1 | **Consistency warnings are not shown in the UI.** The API returns them and the database stores them; no frontend work was done. A clinician sees no difference. | all 477 Gate A reports carry a `consistency` block no interface renders — `gate_a_results.md` §2 |
| 2 | **Transplant threshold not set (Gate B).** The check scores every report and emits nothing. | **every** English report reads `partial` for this reason; 477/477 in Gate A — `amendment_01_consistency_status.md` §2(e) |
| 3 | **No retry (Gate C).** Nothing is corrected; violations are recorded only. | 17/477 Gate A reports carry violations that nothing acted on — `gate_a_results.md` §2 |
| 4 | **Omission defect uncovered.** Constraint (ii) forbids the impression asserting what findings did not state; it does not forbid the impression *omitting* what findings did. | **27/477 (5.7%)** v1.2 reports state an abnormality in findings and call the study normal in the impression (v1.1: 90/477) — `gate_a_results.md` §6.3 |
| 5 | **Bengali unchecked.** All three checks are English-only; the harness generates English only. | **0** Bengali defect rates have ever been measured; a Bengali report stores `checks_run == []` — `gate_a_results.md` §7 |
| 6 | **Chroma persist path ignores config.** `ChromaVectorStore` carries its own `DEFAULT_PERSIST_PATH` from the repo root and `main.py` constructs it with no arguments, so `settings.CHROMA_PERSIST_PATH` is never read. | pre-existing at `v1.1-evaluated`; not fixed (A6 forbade code changes). Worked around for the noise floor by copying the store and verifying the sorted-ID sha256 — `gate_a_results.md` §5 |
| 7 | **D5 open.** The structural/content retry attempt count is still unrecorded, which blocks D3. | content-retry attempts were **not observable** in Gate A; reported as such rather than as zero — `decision_log.md`, `gate_a_results.md` §2 |
| 8 | **Blinded manual read pending.** This is a withhold-pending-review trigger that overrides a clean pass on all three gating criteria. | packet built (40 reports, seed 20260921), **0 of 2 readers** have submitted — `reader_packet.md` |
| 9 | **Micro-F1 gain is substantially a `No Finding` gain.** 7 of 14 labels have support < 10; Pneumonia recall got worse. | `No Finding` support 322, recall 0.714 → 0.804; Pneumonia recall 0.150 → 0.050 on support 20 — `gate_a_results.md` §6.1b |
| 10 | **Pre-registration defect.** The frozen document supported two incompatible definitions of the primary endpoint; the run plan fixed the wider one without noticing the baseline came from the narrower. | both reported; verdict unchanged either way — `gate_a_results.md` §3.1.1 |
| 11 | **4 stored rows read `clean` when they should read `partial`.** Written by commit 4 under the pre-amendment rule; not migrated. | 4 of 1,802 rows at the time — `amendment_01_consistency_status.md` §3 |
| 12 | **Not merged to `main`.** | `main` is still `a107d4ef` |
