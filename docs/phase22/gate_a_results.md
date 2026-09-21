# Phase 22 — Gate A Results

| | |
|---|---|
| **Run date** | 2026-09-22 |
| **Code under test** | `phase22-v1.2` at `52884b0eba23e39a935f97e0e8111e9310c3b8c9` |
| **Run plan** | [`gate_a_run_plan.md`](gate_a_run_plan.md), committed `55e8bc08506cb3eb6066e117d9d53bbb00c3a7f5` at 2026-09-22 01:09:38 +0600 — **before any v1.2 report existed** |
| **Baseline** | stored Phase 21 Arm C (`generation_arm_full_n477`), paired per uid |
| **Outputs** | `ml/outputs/evaluation/generation_v1.2_gateA_n477/` |
| **Verdict** | **ADOPT** on the three gating criteria; **one withhold trigger remains open** (manual read not yet performed) |

---

## 1. Configuration

| item | value | vs Phase 21 |
|---|---|---|
| model | `llama3:8b`, digest `365c0bd3c000` | name **match**; digest not recorded by Phase 21 |
| ollama | `0.34.2` | **match** |
| temperature / seed | 0.0 / 42 | **match** |
| retry budgets | content 2 / transport 1 | **match** |
| num_ctx | 4096 | **match** |
| collection | `iu_cxr_biomedclip_v1_train`, 2462 docs | name **match**; count/hash not recorded by Phase 21 |
| sorted-ID sha256 | `c6b2ab850fc9b3fb9a1bfc6493cdd52b5322c1d9d47b4d5dba88afeb12ef72f6` | — |
| embedding | `biomedclip` / `v1` | **match** |
| evidence mode | `full`, verified live via `/system/stats` before generation | **match** |
| consistency service | **observational** — no retry, nothing blocked, no text altered | n/a (new) |

Everything Phase 21 recorded matches. The three identifiers it did not record
(model digest, collection count, collection ID hash) are recorded here so
future runs can make the comparison Phase 21 could not.

**Harness deviation, recorded rather than glossed.** This run did **not** use
`run_generation_eval.py --arm full --tag n477`: that invocation writes into
`generation_arm_full_n477`, which *is* the stored Phase 21 Arm C artifact
being paired against, and would have overwritten the baseline. The run drove
the identical API path (`POST /retrieve` → `POST /generate-report`) with
identical parameters — `top_k=5`, `min_similarity=0.0`,
`declared_projection=PA`, raw image, `language=en`,
`questionnaire_answers=None`, `clinical_notes=""` — from the explicit 477-uid
list, resumable, into a versioned directory.

---

## 2. Generation

```
completed 477/477   failed 0
```

| | |
|---|---|
| structural failure rate | **0/477** (no HTTP 422; every response parsed within the content-retry budget) |
| consistency status | **partial 459, violations 17**, clean 0, not_run 0 |
| `consistency_retry_count` | **0 for every case** — Gate A performs no retry, by construction |
| latency per report | mean **4.50 s**, median 4.47 s, max 5.97 s, n=477 |
| consistency check latency | 6.9–7.8 ms per report (server logs) |

No report reads `clean`, which is what amendment 01 predicts before Gate B:
the transplant check has no calibrated threshold, cannot emit a violation, and
is therefore not counted as having run.

**Content-retry attempts are not observable.** Neither `LLMOrchestrator` nor
`OllamaClient` logs them and the API does not expose them — the gap decision
**D5** exists to close, and why **D3** is blocked. Reported as not observable,
never as zero.

---

## 3. Pre-registered endpoints

Paired per uid, n=477. Bootstrap: 2,000 resamples, seed 42, percentile.
CheXbert labels from the **frozen evaluation path** (frozen eval venv), not the
runtime adapter, so both arms are labelled by the same instrument.

### 3.1 Primary — temporal-term rate (gates)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **temporal-term rate** | **0.3899** (186/477) | **0.0503** (24/477) | **−0.3396** | **[−0.3836, −0.2998]** | 477 |
| same, n=100 pilot | 0.4600 (46/100) | 0.0500 (5/100) | −0.4100 | [−0.5100, −0.3200] | 100 |

**Decreases, CI excludes zero → PASS.**

> **Why 186/477 and not the frozen document's 167/477.** The run plan (§3.1,
> pre-registered) defines this endpoint over **nine** prompt-side terms across
> **findings, impression and recommendation**. `diagnosis.md` §2b's headline
> 167/477 used **five** terms across **findings and impression only**. The
> paired comparison is unaffected — both arms are measured identically — and
> under §2b's own definition this run reproduces its baseline **exactly**
> (see §6, post-hoc: v1.1 = 167/477 = 0.3501). The drop holds under both
> definitions.

### 3.2 Clinical guardrail — CheXbert impression micro-F1 (gates, δ = 0.05)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **micro-F1** | 0.5250 | 0.5886 | **+0.0636** | **[+0.0314, +0.0961]** | 477 |

CI lower bound **+0.0314 > −0.05 → PASS**. The guardrail was a
non-inferiority bound; the measurement is an *improvement* whose CI excludes
zero on the positive side. It is reported as clearing the bound, which is what
was pre-registered.

### 3.3 Supplementary guardrail — impression ROUGE-L (gates, δ = 0.03)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **ROUGE-L** | 0.2496 | 0.2646 | +0.0149 | [−0.0024, +0.0317] | 477 |

CI lower bound **−0.0024 > −0.03 → PASS**. The CI includes zero, so this is
**not** evidence of improvement — only that textual drift is bounded well
inside the margin, which is all this guardrail was for.

### 3.4 Secondary (do **not** gate adoption)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| harmful transplant rate (strict) | 0.0461 (22/477) | 0.0210 (10/477) | −0.0252 | [−0.0419, −0.0105] | 477 |
| strict contradiction rate | 0.0461 (22/477) | 0.0084 (4/477) | −0.0377 | [−0.0566, −0.0189] | 477 |

Both fell with CIs excluding zero. Per the pre-registered rule they are
reported whatever they show and **do not** gate adoption.

> **A denominator caveat that materially affects the transplant reading.**
> The transplant ratio is only defined for impressions with ≥5 tokens. That
> scorable count fell from **353 (v1.1) to 280 (v1.2)**, because v1.2
> impressions are shorter (median 9 → 5 words; under-5-word impressions
> 124 → 197; see §6). Against the scorable denominator the rate is
> 22/353 = 6.23% → 10/280 = 3.57%. **Part of the harmful-transplant drop may
> be an artifact of shorter impressions being unscorable rather than of less
> copying**, and this run cannot separate the two.

### 3.5 Held-out synonym rate (does not gate; word-avoidance tripwire)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| held-out rate | 0.0377 (18/477) | 0.0084 (4/477) | −0.0294 | [−0.0461, −0.0147] | 477 |

**The primary rate fell and the held-out rate fell with it.** Per §6.4's
reading rule this is *consistent with a real fix* rather than word-avoidance,
and the word-avoidance withhold trigger is **not** fired. These ten terms were
never shown to the model — verified over every prompt the backend can send by
`test_prompt_heldout_containment.py`.

### 3.6 Descriptive — CheXbert impression macro-F1 (does **not** gate)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| macro-F1 | 0.1734 | 0.1958 | +0.0224 | [−0.0266, +0.0683] | 477 |

CI includes zero. Per the frozen rule this must **not** be reported as a
non-inferiority claim: a metric whose CI does not narrow with n cannot support
one.

---

## 4. Verdict

Applied mechanically from the pre-registered rule; no endpoint was added,
dropped or redefined.

| criterion | result |
|---|---|
| 1. primary temporal decreases, CI excludes zero (n=477) | **PASS** |
| 2. micro-F1 CI lower bound > −0.05 | **PASS** (+0.0314) |
| 3. ROUGE-L CI lower bound > −0.03 | **PASS** (−0.0024) |
| **ADOPT v1.2?** | **YES on the three gating criteria** |

**Withhold-pending-review triggers:**

| trigger | status |
|---|---|
| held-out rate fails to fall while primary collapses | **not triggered** — both fell |
| a single clear grounding failure in the blinded manual read | **OPEN** — packet prepared, not yet read |

> **Adoption is therefore not final.** The second trigger is a stop condition
> that overrides a clean pass on all three criteria, and it cannot be
> evaluated until two readers have completed the blinded packet. The verdict
> above is *"passes every automated criterion"*, not *"cleared for adoption"*.

**Gate A is the judged run** (frozen §6.1). The consistency service is
observational here: no retry exists, so the temporal rate measures exactly one
thing — whether instruction (iii) changed the model's behaviour. The Gate C
circularity, where the same detector both triggers the retry and scores the
outcome, does not apply to any number in this document.

---

## 5. Supplementary — v1.1 re-run noise floor

**Not an endpoint. Does not enter the verdict.**

What could a v1.1 → v1.2 difference be worth if re-running the *same* code
produced one? v1.1 was checked out at tag `v1.1-evaluated` in a separate
worktree, served against a byte-verified copy of the same collection
(sorted-ID sha256 identical), and re-run on the 100 pilot uids with identical
settings.

```
cases compared            : 100/100  (missing 0)
byte-identical to stored  : 33/100 (33.0%)
differing                 : 67/100 (67.0%)
temporal rate, STORED v1.1: 46/100 (46.0%)
temporal rate, RE-RUN v1.1: 46/100 (46.0%)
noise-floor movement      : +0.0 percentage points
```

**Two findings, and the second is what matters.** At temperature 0.0 with
seed 42, **67% of outputs are not byte-identical on re-run** — the generation
is materially non-deterministic, which confirms and quantifies the
non-determinism this project recorded once before. But **the primary
endpoint's own measurement did not move at all**: 46/100 both times, 0.0
percentage points.

So the text varies while the endpoint is stable, and the −34 percentage point
primary result cannot be attributed to re-run noise. This is the single
strongest piece of support for the primary reading, and it is supplementary
precisely because it was not pre-registered as an endpoint.

---

## 6. Post-hoc, not pre-registered

Neither analysis below was in the run plan. Both are reported because they
change how §3 should be read.

**(a) The primary endpoint under `diagnosis.md` §2b's own definition** (five
terms, findings and impression only):

```
v1.1 167/477 = 0.3501   (diagnosis 2b reported 167/477 = 0.3501 -- exact match)
v1.2  13/477 = 0.0273   diff = -0.3229
```

The frozen baseline is reproduced **exactly**, and the drop is
−0.3229 against the pre-registered definition's −0.3396. The primary result is
robust to which of the two definitions is used.

**(b) Impression length**, because it bears directly on §3.4's denominator:

```
v1.1 mean=13.4  median=9  min=1  max=73   under 5 words: 124
v1.2 mean= 9.3  median=5  min=1  max=62   under 5 words: 197
```

**v1.2 impressions are substantially shorter.** This is not a pre-registered
endpoint and no claim is made about whether it is good or bad, but it is the
mechanism behind the transplant scorable denominator falling 353 → 280, and
it means part of the harmful-transplant improvement in §3.4 may be shorter
text rather than less copying. It also plausibly relates to the micro-F1
improvement, since a shorter impression asserts fewer labels and can reduce
false positives. **Neither possibility is tested here.**

---

## 7. Limitations

- **English only.** The harness hardcodes `"language": "en"`. Every number in
  this document is an English result.
- **Bengali is unmeasured.** The prompt changes reach Bengali output; all three
  consistency checks are English-only; no Bengali defect rate has ever been
  measured in this project. Nothing here says what v1.2 does to Bengali
  reports.
- **The explanation prompt changed but is unevaluated.**
  `build_explanation_prompt()` reuses `_evidence_section()`, so change (i)
  propagates to it. That is intended — the explanation chat shows the
  clinician the same other-patient text and should carry the same attribution
  boundary — but no endpoint here measures explanation output.
- **The transplant check emitted nothing.** Its threshold is Gate B's to
  calibrate, so it was scored but not counted as run. Every report reads
  `partial` for that reason. `transplant_scores()` output is saved per case in
  `consistency_and_transplant.jsonl` as Gate B's calibration input.
- **Temporal counts are lexical**, at a measured 95% precision
  (diagnosis.md §5.3), not adjudicated readings.
- **CheXbert has a known negation bug** on this corpus (diagnosis.md §2c);
  contradiction counts are labeler output, not adjudicated readings.
- **Harmful-transplant denominators differ between arms** (353 vs 280) — see
  §3.4 and §6(b).
- **The manual read has not happened.** Its withhold trigger is open.
- **Content-retry attempts are unobservable** (D5), so the structural result
  is "0/477 failed after retries", not "0/477 needed no retry".

---

## 8. Artifacts

| path | contents |
|---|---|
| `generation_v1.2_gateA_n477/generated_text/` | 477 generated reports + ground truth |
| `generation_v1.2_gateA_n477/per_case_results.csv` | status, retrieved uids, top-1 similarity, consistency status, latency |
| `generation_v1.2_gateA_n477/consistency_and_transplant.jsonl` | per-case consistency block and `transplant_scores()` — **Gate B's calibration input** |
| `generation_v1.2_gateA_n477/tier3_chexbert_*_labels.csv` | binarised CheXbert labels (frozen path) |
| `generation_v1.2_gateA_n477/tier1_rouge.csv` | per-case ROUGE-L |
| `generation_v1.2_gateA_n477/gate_a_endpoints.json` | every endpoint, CI and the verdict |
| `generation_v1.2_gateA_n477/evaluation_config.json` | full run configuration |
| `noise_floor_v1.1_rerun_n100/` | supplementary re-run and its summary |
| `reader_packet.md` | 40 blinded reports, no version information |
| `reader_packet_ANSWER_KEY.md` | held separately; do not open until both readers submit |
