# Phase 22, part 2 — Gate A: v1.2 vs v1.1, pre-registered

**Never pool with any other phase.** Paired per uid against **stored Phase 21
Arm C**, on the same 477 uids, with both arms labelled by the same frozen
CheXbert instrument.

| | |
|---|---|
| **Question** | Does the v1.2 grounding fix reduce ungrounded temporal language without damaging clinical accuracy or textual fidelity? |
| **Method** | 477 cases driven through the real API path (`POST /retrieve` → `POST /generate-report`). Paired bootstrap B=2,000, seed 42, percentile. CheXbert from the **frozen evaluation path**, never the runtime adapter. |
| **n** | **477 completed / 477, 0 failed** |
| **Run date** | 2026-09-22, code `phase22-v1.2` at `52884b0e` |
| **Run plan** | committed `55e8bc08` at 2026-09-22 01:09:38 +0600 — **before any v1.2 report existed** |
| **Source** | `docs/phase22/gate_a_results.md`; `ml/outputs/evaluation/generation_v1.2_gateA_n477/gate_a_endpoints.json` |
| **Verdict** | **PASS on all three gating criteria. ADOPTION IS NOT FINAL** — a withhold trigger is open. |

## Configuration parity with Phase 21

Model `llama3:8b` digest `365c0bd3c000`, Ollama `0.34.2`, temperature 0.0 /
seed 42, retry budgets content 2 / transport 1, `num_ctx` 4096, collection
`iu_cxr_biomedclip_v1_train` (2,462 docs, sorted-ID sha256 `c6b2ab85…`),
embedding `biomedclip/v1`, evidence mode `full` verified live via
`/system/stats` **before** generation. **Everything Phase 21 recorded matches.**
Three identifiers Phase 21 did **not** record — model digest, collection count,
collection ID hash — are recorded here so a future run can make the comparison
Phase 21 could not.

**Harness deviation, recorded rather than glossed.** The run did *not* use
`run_generation_eval.py --arm full --tag n477`, because that invocation writes
into `generation_arm_full_n477` — which **is** the stored baseline being paired
against, and would have overwritten it.

## Generation

| | |
|---|---|
| structural failure rate | **0 / 477** (no HTTP 422; every response parsed within the content-retry budget) |
| consistency status | **partial 459, violations 17, clean 0, not_run 0** |
| `consistency_retry_count` | **0 for every case** — Gate A performs no retry, by construction |
| latency per report | mean **4.50 s**, median 4.47 s, max 5.97 s, n=477 |
| consistency check latency | **6.9–7.8 ms** per report (server logs) |

**No report reads `clean`**, exactly as amendment 01 predicts before Gate B.

> **Content-retry attempts are NOT OBSERVABLE.** Neither `LLMOrchestrator` nor
> `OllamaClient` logs them and the API does not expose them — gap decision
> **D5**. The structural result is therefore *"0/477 failed after retries"*,
> **not** *"0/477 needed no retry"*.

## The three gating criteria

### 1. Primary — temporal-term rate — **PASS**

| definition | v1.1 | v1.2 | diff | 95 % CI |
|---|---|---|---|---|
| **FROZEN (primary)** — 5 terms, findings+impression | 0.3501 (167/477) | **0.0273** (13/477) | **−0.3229** | **[−0.3648, −0.2830]** |
| run-plan (secondary) — 9 terms, +recommendation | 0.3899 (186/477) | 0.0503 (24/477) | −0.3396 | [−0.3836, −0.2998] |

> **A real pre-registration defect, recorded rather than resolved quietly.**
> The frozen document supports **two** readings of its own primary endpoint —
> §3.1 names three sections and a nine-term list, while its stated baseline
> (line 734) was computed over five terms and two sections. The run plan
> followed the wider one without noticing the quoted number came from the
> narrower one. **The more conservative frozen definition is reported as
> primary**, and the verdict is identical under both.

### 2. Clinical guardrail — CheXbert impression micro-F1 (δ = 0.05) — **PASS**

| | v1.1 | v1.2 | diff | 95 % CI |
|---|---|---|---|---|
| micro-F1 | 0.5250 | 0.5886 | **+0.0636** | [+0.0314, +0.0961] |

CI lower bound **+0.0314 > −0.05**. The guardrail was a *non-inferiority*
bound; the measurement is an improvement. It is reported as clearing the bound,
which is what was pre-registered.

### 3. Supplementary guardrail — impression ROUGE-L (δ = 0.03) — **PASS**

| | v1.1 | v1.2 | diff | 95 % CI |
|---|---|---|---|---|
| ROUGE-L | 0.2496 | 0.2646 | +0.0149 | **[−0.0024, +0.0317]** |

CI lower bound −0.0024 > −0.03. **The CI includes zero, so this is NOT evidence
of improvement** — only that textual drift is bounded well inside the margin,
which is all this guardrail was for.

## Secondary and descriptive endpoints (do **not** gate)

| endpoint | v1.1 | v1.2 | diff | 95 % CI | excludes 0 |
|---|---|---|---|---|---|
| harmful transplant rate (strict) | 0.0461 (22/477) | 0.0210 (10/477) | −0.0252 | [−0.0419, −0.0105] | yes |
| strict contradiction rate | 0.0461 (22/477) | 0.0084 (4/477) | −0.0377 | [−0.0566, −0.0189] | yes |
| held-out synonym rate | 0.0377 (18/477) | 0.0084 (4/477) | −0.0294 | [−0.0461, −0.0147] | yes |
| CheXbert impression **macro**-F1 | 0.1734 | 0.1958 | +0.0224 | [−0.0266, +0.0683] | **no** |

> **A denominator caveat that materially affects the transplant reading.** The
> transplant ratio is defined only for impressions with ≥5 tokens, and that
> scorable count fell **353 → 280** because v1.2 impressions are shorter.
> Against the scorable denominator: 6.23 % → 3.57 %. Part of the drop may be an
> artifact of unscorability rather than less copying — **this run cannot
> separate the two.** ([The post-hoc file removes this confound.](phase22_posthoc.md))

**The held-out tripwire did not fire.** Ten synonyms were never shown to the
model — verified over every prompt the backend can send by
`test_prompt_heldout_containment.py`. The primary rate fell **and** the held-out
rate fell with it, which per §6.4's reading rule is consistent with a real fix
rather than word-avoidance.

## Verdict, applied mechanically

| criterion | result |
|---|---|
| 1. primary temporal decreases, CI excludes zero | **PASS** (both definitions) |
| 2. micro-F1 CI lower bound > −0.05 | **PASS** (+0.0314) |
| 3. ROUGE-L CI lower bound > −0.03 | **PASS** (−0.0024) |
| **ADOPT v1.2?** | **YES on the three gating criteria** |

| withhold trigger | status |
|---|---|
| held-out rate fails to fall while primary collapses | **not triggered** — both fell |
| a single clear grounding failure in the blinded manual read | **OPEN — packet prepared, not yet read** |

> **ADOPTION IS THEREFORE NOT FINAL.** The second trigger is a stop condition
> that **overrides a clean pass on all three criteria**, and it cannot be
> evaluated until two readers complete the blinded packet (`reader_packet.md`,
> 40 reports, no version information; answer key held separately). The verdict
> above is *"passes every automated criterion"*, **not** *"cleared for
> adoption"*. Any thesis sentence that says v1.2 was adopted must carry this.

## The noise floor — supplementary, not an endpoint

v1.1 was checked out at tag `v1.1-evaluated` in a separate worktree, served
against a byte-verified copy of the same collection, and re-run on the 100
pilot uids with identical settings.

```
byte-identical to stored  : 33/100 (33.0 %)
differing                 : 67/100 (67.0 %)
temporal rate, STORED v1.1: 46/100 (46.0 %)
temporal rate, RE-RUN v1.1: 46/100 (46.0 %)
noise-floor movement      : +0.0 percentage points
```

**Two findings, and the second is what matters.** At temperature 0.0 with seed
42, **67 % of outputs are not byte-identical on re-run** — the generation is
materially non-deterministic. But **the primary endpoint's own measurement did
not move at all**. The text varies while the endpoint is stable, so the −32
percentage-point primary result cannot be attributed to re-run noise. This is
the single strongest support for the primary reading, and it is supplementary
precisely because it was **not** pre-registered.

## Limitations carried forward

- **English only.** The harness hardcodes `"language": "en"`. Every number here
  is an English result. **Bengali is unmeasured** — the prompt changes reach
  Bengali output, all three consistency checks are English-only, and **no
  Bengali defect rate has ever been measured in this project.**
- **The explanation prompt changed but is unevaluated.**
- **The transplant check emitted nothing** — its threshold is Gate B's to
  calibrate, so it was scored but not counted as run.
- **Temporal counts are lexical** (95 % measured precision), not adjudicated.
- **CheXbert's negation bug** applies; contradiction counts are labeler output.
- **The manual read has not happened.**
- **Content-retry attempts are unobservable (D5).**
