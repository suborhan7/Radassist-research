# Phase 22 — Gate A Run Plan (PRE-REGISTERED, before any generation)

| | |
|---|---|
| **Written** | 2026-09-22 |
| **Status** | **Pre-registered.** Committed before a single v1.2 report was generated. |
| **Code under test** | `phase22-v1.2` at **`52884b0eba23e39a935f97e0e8111e9310c3b8c9`** (`52884b0e`, *feat(phase22): prompt grounding changes (i)-(iv)*, 2026-09-22 00:50:23 +0600) |
| **Source of every endpoint below** | [`fix_architecture_v1.2_FROZEN.md`](fix_architecture_v1.2_FROZEN.md) (frozen at docs commit `810240ea`), as amended by [`amendment_01_consistency_status.md`](amendment_01_consistency_status.md) |
| **Baselines** | [`diagnosis.md`](diagnosis.md) §2a/§2b/§2c/§5.2 |

**Purpose of committing this first.** Every endpoint, definition, sample size,
bootstrap configuration and the verdict rule are fixed here so none of them can
be chosen, dropped or redefined after seeing a result. Anything not in this
document is **post-hoc** and must be reported under that heading.

---

## 1. Run configuration

### 1.1 Recorded now

| item | value |
|---|---|
| commit under test | `52884b0eba23e39a935f97e0e8111e9310c3b8c9` |
| model name | `llama3:8b` |
| model digest (ollama ID) | `365c0bd3c000` |
| model manifest mtime | 2026-07-01 12:20 |
| ollama version | `0.34.2` |
| quantization / arch / ctx | Q4_0 / llama / 8192 (model card) |
| `num_ctx` used by the harness | **4096** (Ollama default applied; the harness sets no `num_ctx`, matching Phase 21) |
| temperature | `0.0` (`LLM_TEMPERATURE`) |
| seed | `42` (`LLM_SEED`) |
| keep_alive | `30m` |
| content / transport retry | `2` / `1` |
| evidence mode | `FULL` (Arm C) |
| retrieval collection | `iu_cxr_biomedclip_v1_train` |
| embedding model / version | `biomedclip` / `v1` |
| collection document count | **2462** |
| sha256 of sorted collection IDs | `c6b2ab850fc9b3fb9a1bfc6493cdd52b5322c1d9d47b4d5dba88afeb12ef72f6` |

### 1.2 Comparison against what Phase 21 recorded

Phase 21 Arm C's `evaluation_config.json` and its 1,814 persisted report rows
record:

```
model llama3:8b   temperature 0.0   seed 42   keep_alive 30m
content_retry_count 2   transport_retry_count 1   ollama_version 0.34.2
collection=iu_cxr_biomedclip_v1_train  emb=biomedclip/v1  llm=llama3:8b  temp=0.0
```

| item | Phase 21 | now | verdict |
|---|---|---|---|
| model name | `llama3:8b` | `llama3:8b` | **match** |
| ollama version | `0.34.2` | `0.34.2` | **match** |
| temperature / seed | 0.0 / 42 | 0.0 / 42 | **match** |
| retry budgets | 2 / 1 | 2 / 1 | **match** |
| collection name | `iu_cxr_biomedclip_v1_train` | same | **match** |
| embedding model/version | `biomedclip` / `v1` | same | **match** |
| **model digest** | **not recorded** | `365c0bd3c000` | **cannot be compared** |
| **collection doc count** | **not recorded** | 2462 | **cannot be compared** |
| **collection ID hash** | **not recorded** | `c6b2ab85…` | **cannot be compared** |

**Not a stop condition, but a real gap, stated rather than glossed.** Phase 21
recorded no model digest, no collection document count and no collection ID
hash, so there is nothing for the present values to differ *from*. Everything
Phase 21 *did* record matches exactly. The three new identifiers are recorded
here so that every future run can make the comparison Phase 21 could not.

**Supporting evidence that the retrieval store is unchanged since Phase 21.**
Phase 21 Arm C ran 2026-09-19T11:55Z. The HNSW index files
(`data_level0.bin`, `link_lists.bin`, `index_metadata.pickle`, `header.bin`,
`length.bin`) were last written **2026-07-18 21:13**, two months before that
run, and have not been written since. `chroma.sqlite3` carries today's mtime
because reading a collection opens it; no write path was invoked. The document
count 2462 equals the train-split size recorded in CLAUDE.md.

**Decision: proceed.** Nothing that Phase 21 recorded differs.

---

## 2. Endpoints, quoted verbatim from the frozen document

### 2.1 Primary

> **Primary — temporal-term rate, judged at Gate A.** Baseline 167/477 = 35.0%
> [31.0, 39.4]; also reported at n=100 (42/100). Success: post-fix rate lower, with
> the paired 95% bootstrap CI on the difference **excluding zero** in the direction
> of improvement, **at n=477**. The n=100 reading is reported alongside for
> continuity with the pilot and is not separately decisive.
>
> — `fix_architecture_v1.2_FROZEN.md` §6.3, lines 764–769

### 2.2 Secondary (do not gate adoption)

> **Secondary — harmful transplant rate, n=477.** Baseline 22/477 = 4.6% [2.7, 6.5].
> **Secondary — strict contradiction rate, n=477.** Baseline 22/477 = 4.6% [2.7, 6.5].
>
> — §6.3, lines 771–772

> **Power, stated in advance.** Moving to n=477 raises these from 4 and 2 events
> to 22 and 22, which is the reason the sample size is pre-registered at 477
> rather than left open. They remain **secondary**: a fix that halved either would
> still produce a CI that may include zero. A non-significant result on either
> **does not count as evidence the fix failed**; it is reported with its CI and
> its event count.
>
> — §6.3, lines 774–779

### 2.3 Clinical guardrail (gates)

> #### Clinical guardrail — CheXbert impression **micro**-F1. **δ = 0.05, n=477.**
>
> — §6.3, line 783

Baseline (§6.3 table, line 977): `0.5250 [0.4809, 0.5701]`.

### 2.4 Supplementary guardrail (gates)

> #### Supplementary guardrail — impression ROUGE-L. **δ = 0.03, n=477.**
>
> — §6.3, line 928

Baseline (§6.3 table, line 978): `0.2496 [0.2269, 0.2714]`.

### 2.5 Descriptive (does not gate)

> #### Descriptive (no longer a gate) — CheXbert impression macro-F1, δ = 0.06
>
> — §6.3, line 848

Baseline (§6.3 table, line 979): `0.1734 [0.1348, 0.2115]`.

> **A macro result does not gate adoption in either direction**, and specifically: a
> macro CI that fails δ = 0.06 is reported and investigated but does not by itself
> block adoption; a macro CI that clears it must not be reported as a
> non-inferiority claim, because a metric whose CI does not narrow with n cannot
> support one.
>
> — §6.3, lines 856–860

### 2.6 Held-out synonym rate (does not gate; can trigger withhold-pending-review)

Baseline 18/477 = 3.8% [2.1, 5.7] (§6.4). The ten terms are frozen in
[`heldout_temporal_terms.txt`](heldout_temporal_terms.txt), generated from §6.4's
table and diff-verified against it.

> - Primary rate falls **and** held-out rate falls → consistent with a real fix.
> - Primary rate falls **and** held-out rate holds or rises → **word-avoidance
>   signal.** Adoption is withheld pending review (§6.3), regardless of the primary
>   endpoint clearing.
> - Both hold → the prompt change did not work.
>
> — §6.4

### 2.7 Also recorded per run (not endpoints)

> **Also recorded per run (not endpoints):** structural-failure rate (parity with
> Phase 21 §6.4's check), `consistency_retry_count` distribution, count of
> warning-only FINDINGS violations (§4.1), and wall-clock latency per report.
>
> — §6.3, lines 983–985

Plus, per amendment 01, the **consistency status distribution**
(`not_run` / `partial` / `clean` / `violations`).

---

## 3. Exact definitions

Frozen before the run so no definition can be tuned to a result.

### 3.1 Temporal-term rate (primary)

A case counts if **any** of the nine prompt-side terms matches in FINDINGS,
IMPRESSION **or** RECOMMENDATION, word-boundary and case-insensitive, with
multi-word terms matched as phrases:

`stable · unchanged · interval · again · redemonstrated · persistent · previously · compared with · new`

Sourced from `settings.consistency_temporal_terms` — the same list the checker
matches on and the same list the prompt names. Every case in this harness has
**no prior study** (`run_generation_eval.py` performs `POST /retrieve` then
`POST /generate-report` and never creates a second report for a patient), so the
denominator is all completed cases and the rate is the rate of *unsupported*
temporal language.

Measured precision of this matcher on real Arm C output: **19/20 = 95.0%**
(diagnosis.md §5.3). The counts are lexical, not adjudicated.

### 3.2 Harmful transplant rate (secondary) — diagnosis.md §5.2

Two conditions, **both** required:

1. The generated IMPRESSION's **maximum token 5-gram overlap ratio against any
   retrieved neighbour's impression is exactly 1.0** — every 5-gram in the
   generated impression also occurs in one neighbour's impression.
2. That copied impression **carries at least one CheXbert-positive finding on the
   13 real conditions**. `No Finding` is excluded from the positive set: a
   `No Finding`-positive impression is exactly the stock normal phrasing that
   defines the *benign* bucket.

Positivity is **strict** (class 1, Positive) for the headline figure. The
inclusive reading (class 1 or 3, Positive or Uncertain) is reported alongside
and never merged.

Scorability: a case enters the ratio denominator only if its generated
impression yields at least one 5-gram, i.e. **≥5 alphanumeric tokens**
(diagnosis.md §5.1). Rates are reported against **both** denominators —
scorable and all-completed — never switched silently.

The scoring functions are `_tokens`, `_five_grams`,
`_longest_common_token_run` imported from
`backend/app/services/report_consistency_service.py`, the same code that
reproduces diagnosis.md §2a exactly.

### 3.3 Strict contradiction rate (secondary) — diagnosis.md §2c

A case counts if, for **any** of the 13 four-class conditions, the CheXbert raw
class is **Positive (1) in one section and Negative (2) in the other**, with
FINDINGS and IMPRESSION labelled **separately and never concatenated**.

`No Finding` is excluded: its head has only 2 outputs and can never emit
Negative, so a contradiction is not expressible for it.

Positive-vs-absent is **not** a contradiction — that is ordinary summarisation
and would fire on 62.9% of reports.

### 3.4 CheXbert micro-F1 and macro-F1 (guardrail / descriptive)

Computed on the `impression` field against the reference impression, using the
**frozen evaluation path** (`ml/evaluation/score_chexbert.py` in the frozen eval
venv), **not** the runtime adapter — so v1.1 and v1.2 are labelled by the same
instrument. Labels binarised by `to_present_binary()` ({Blank, Negative}→0,
{Positive, Uncertain}→1), as Phase 20/21 did.

- **micro**: tp/fp/fn pooled across all 14 conditions × all cases, then one F1.
- **macro**: per-condition F1 averaged over 14 conditions, `zero_division=0`.

### 3.5 ROUGE-L (supplementary guardrail)

Per-case ROUGE-L on `impression` against the reference impression, averaged —
the same `impression_rouge_l` column Phase 21's `per_case_results.csv` carries,
computed by the same harness code path.

### 3.6 Held-out synonym rate

Any of the ten terms in
[`heldout_temporal_terms.txt`](heldout_temporal_terms.txt) matching FINDINGS or
IMPRESSION, word-boundary, case-insensitive. **Scoring only — never shown to the
model**, verified by `test_prompt_heldout_containment.py` over every prompt the
backend can send.

---

## 4. Sample sizes and pairing

| endpoint | n |
|---|---|
| primary (temporal) | **477**, with n=100 pilot subset reported alongside (not separately decisive) |
| harmful transplant | **477** |
| strict contradiction | **477** |
| CheXbert micro-F1 | **477** |
| ROUGE-L | **477** |
| macro-F1 (descriptive) | **477** |
| held-out rate | **477** |

- **Cases:** the 477 completed Arm C uids in
  `ml/outputs/evaluation/generation_arm_full_n477/per_case_results.csv`.
- **Before:** the stored Phase 21 Arm C outputs for those uids.
- **After:** v1.2 at `52884b0e`, same uids, same harness path, same settings.
- **Paired per uid.** The n=100 pilot uids
  (`scratch/phase22_diagnosis/pilot100_uids.txt`) are a verified subset, so the
  n=100 reading is a strict sub-analysis, not a separate execution.

**Bootstrap:** 2,000 resamples, **seed 42**, percentile method, paired
case-level resampling — Phase 0's exact configuration, reused rather than
reinvented, and the same configuration every prior Phase 22 measurement used.

---

## 5. Verdict rule, quoted verbatim

> #### Verdict rule, fixed now
>
> v1.2 is adopted if **all** of:
>
> 1. **Primary at Gate A, n=477:** temporal rate decreases, paired 95% CI excludes zero.
> 2. **Clinical guardrail:** CheXbert impression **micro**-F1 paired CI lower bound > **−0.05**.
> 3. **Supplementary guardrail:** impression ROUGE-L paired CI lower bound > −0.03.
>
> **Not gates:** macro-F1 (descriptive, δ = 0.06 for reference only), both secondary
> endpoints, the held-out list, the manual read, and every Gate C number. These are
> reported whatever they show.
>
> **Two withhold-pending-review triggers** — not adoption criteria, but stop
> conditions that override a clean pass on 1–3:
>
> - A held-out rate that fails to fall while the primary rate collapses (§6.4) —
>   that pattern indicates word-avoidance rather than a fix.
> - A single clear grounding failure in the blinded manual read (§6.4).
>
> — `fix_architecture_v1.2_FROZEN.md` §6.3, lines 957–975

**Applied mechanically.** Endpoints are not added, dropped or redefined after
the run. Anything else goes under *"Post-hoc, not pre-registered"*.

---

## 6. Gate A is the judged run

> **The primary endpoint is judged at Gate A.**
>
> At Gate A no retry exists, so the temporal rate measures exactly one thing: did
> instruction (iii) change the model's behaviour. That is a clean causal reading.
>
> **Gate C's temporal rate is reported separately and is partly circular.** The
> same detector (§3.1) both triggers the retry and scores the outcome: a report
> whose impression is regenerated *because* it tripped the temporal check is then
> scored by that same check, so the retry mechanically suppresses the very
> measurement used to judge it.
>
> — §6.1

This run is **Gate A**: the consistency service is observational, there is **no
retry**, and no generated text is altered by it. The circularity above does not
apply to any number in this run.

---

## 7. Blinded manual read (packet prepared in this step, not read)

20 v1.1 + 20 v1.2 reports, pooled, shuffled, version hidden, **seed 20260921**
(the same fixed seed used in diagnosis.md §5.3). Readers **Borhan** and
**Sumaiyah**, independently. Raw agreement per question, no kappa. Neither
reader is a radiologist; the read assesses **temporal language and
laterality/location consistency**, not clinical correctness.

Step A6 prepares the packet and the sealed key only. Nothing is filled in.

---

## 8. Known limitations, fixed in advance

- **English only.** The harness hardcodes `"language": "en"`. No Bengali defect
  rate has ever been measured in this project, and all three checks are
  English-only. The prompt changes reach Bengali output; their effect there is
  **unmeasured**.
- **The transplant check emits nothing.** Its threshold is Gate B's to
  calibrate, so it is scored but not counted as run (amendment 01(b)). Every
  English report will therefore read `partial`.
- **The explanation prompt changed** — it reuses `_evidence_section()`, so
  change (i) propagates there — and is **not evaluated** by any endpoint here.
- **Temporal counts are lexical**, 95% precision measured, not adjudicated.
- **CheXbert has a known negation bug** on this corpus (diagnosis.md §2c
  caveat); contradiction counts are labeler output, not adjudicated readings.
