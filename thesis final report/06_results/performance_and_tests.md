# Latency, VRAM, non-determinism, and test counts

**Never pool across phases.** Every block below states its own instrument, its
own n, and the run it came from. Two latency figures measured on different
phases are two observations, never a trend.

---

## 1. Generation latency

| source | config | n | mean | p50 | p95 | max |
|---|---|---|---|---|---|---|
| **Phase 22 Gate A** (`gate_a_results.md` §2) | v1.2, `llama3:8b` | **477** | **4.50 s** | 4.47 s | — | 5.97 s |
| **Phase 23 dev, V0** | v1.2, `llama3:8b` | 150 | 4.56 s | 4.53 s | 4.97 s | 7.15 s |
| Phase 23 dev, V2 | + label checklist | 150 | 4.58 s | 4.55 s | 4.98 s | 7.76 s |
| Phase 23 dev, V1 | `qwen2.5:14b` | 150 | 7.37 s | 7.33 s | 8.76 s | 10.76 s |
| Phase 23 dev, V3 | qwen + checklist | 150 | 7.33 s | 7.34 s | 8.36 s | 10.79 s |

**`qwen2.5:14b` costs ~61 % more latency than `llama3:8b`** and was worse on
every accuracy metric (see [`phase23_accuracy.md`](phase23_accuracy.md)).

**A single end-to-end observation, this packet's own capture session (n=1, not
a benchmark):** upload **0.1 s**, retrieval **1.0 s**, questionnaire skipped,
generation **3.9 s** — read off the UI's own per-step timings in
`../05_screenshots/13-generate-complete-dark.png`. **Do not quote this as a
performance result.**

> ### Phase 21's RQ3 per-stage latency profile is **NOT RECORDED**
> `phase21_ablation_architecture.md` §7 specifies P50/P95 **per pipeline
> stage**, written to `ml/outputs/evaluation/latency/latency_summary.csv`.
> **That directory does not exist, and no such file exists anywhere in this
> repository.** The figures above are whole-request generation latency from
> other phases. **The stage-by-stage breakdown the resource-constrained
> deployment argument was supposed to rest on was never produced.**

## 2. Consistency-check latency

| source | n | figure |
|---|---|---|
| Phase 22 §7 harness | 50 | mean **8.6 ms**, min 5.0, p50 9.0, p95 12.0, max 12.0 |
| Phase 22 A2, **real runtime adapter** | — | mean **8.2 ms**, p50 8.0, p95 11.1 |
| Phase 22 Gate A, server logs | 477 | **6.9–7.8 ms** per report |
| v1.2 smoke, server logs | **2** | 13.7 ms (en, 3 checks), 0.0 ms (bn, 0 checks) — **a smoke observation only** |
| Phase 23, under the **qwen** stack | 20 | mean 10.8 ms, p50 10.0, **p95 43.5**, max 43.5 |

Against a ~4.5 s generation, the check is **~0.2 % of request latency**. The
qwen p95 is 4× higher, but **n=20 is too small to call that a regression** and
it is recorded, not concluded.

## 3. VRAM — card total 16,376 MiB throughout

**The `llama3:8b` production stack (Phase 22):**

| component | marginal | note |
|---|---|---|
| `llama3:8b` | **5,025 MiB** | measured from a genuinely cold 537 MiB baseline |
| BiomedCLIP | 1,043 MiB | |
| CheXbert | **452 MiB** | identical to the byte between the §7 harness and the A2 adapter |
| **peak, all three** | **7,095–7,125 MiB** | 30 MiB spread across two runs |
| **headroom** | **9,251–9,281 MiB (≈9.0 GiB)** | threshold: flag if < 1,024 MiB → **PASS** |

**The `qwen2.5:14b` stack (Phase 23 step 1),** `llama3` explicitly unloaded
first because production runs one LLM at a time:

| stage | used | marginal |
|---|---|---|
| baseline | 558 MiB | — |
| + `qwen2.5:14b` | 9,834 MiB | **9,276 MiB** |
| + BiomedCLIP | 10,875 MiB | 1,041 MiB |
| + CheXbert | 11,327 MiB | 452 MiB |
| **peak + inference** | **11,401 MiB** | headroom **4,975 MiB (4.86 GiB)** → **PASS** |

**qwen costs 4,276 MiB more** and still clears the 1 GiB threshold by 3.86 GiB.
BiomedCLIP and CheXbert reproduce their Phase 22 marginals almost exactly,
which is the check that both measurements are of the same stack.

> **One measurement artifact, recorded.** One VRAM script's "baseline" row read
> 5,542–5,556 MiB because `llama3:8b` was still resident under its
> `keep_alive`, so **that run's llama delta (0 MiB) is not meaningful.** The
> clean llama-only figure is **5,025 MiB**, from a cold 537 MiB baseline.

## 4. Non-determinism — measured, not assumed

**At temperature 0.0 with seed 42, generation is materially non-deterministic.**

```
v1.1 re-run against a byte-verified copy of the same collection, n=100:
  byte-identical to stored  : 33/100 (33.0 %)
  differing                 : 67/100 (67.0 %)
  temporal rate, STORED     : 46/100 (46.0 %)
  temporal rate, RE-RUN     : 46/100 (46.0 %)
  noise-floor movement      : +0.0 percentage points
```

**67 % of outputs are not byte-identical on re-run, while the measured endpoint
did not move at all.** Both halves matter: the text varies, so no claim may rest
on exact output reproduction; the endpoint is stable, so Gate A's primary result
cannot be attributed to re-run noise.

## 5. Test counts — **executed for this packet, not counted from source**

Both suites were run on 2026-09-23 for this packet; these are pass counts from
a real execution, not `grep` over `def test_`.

| suite | command | files | tests | result | wall time |
|---|---|---|---|---|---|
| **backend** | `.venv/Scripts/python.exe -m pytest -q` (from `backend/`) | — | **534 collected** | **534 passed, 0 failed** | **207.51 s** |
| **frontend** | `npx vitest run` (from `frontend/`) | **12** | **138** | **138 passed, 0 failed** | 1.08 s |

**672 automated tests pass in total.** 14 warnings on the backend run, all
deprecation notices (`starlette.testclient` httpx, `WordPiece.__init__`); none
is a failure.

> **Two integration tests skip without a real CheXbert checkpoint**, by design —
> the loader fails loudly on a partial match rather than leaving
> randomly-initialised heads emitting plausible garbage.

**There is no ML-pipeline test suite.** `ml/` has no tests; its stages are
verified by running them and reading their printed reports.

## 6. Structural failure rates, across every phase that measured one

| phase | system | n | structural failures |
|---|---|---|---|
| Phase 20 | v1.1 (JSON output) | 477 | **17 (3.6 %)** — all one root cause: a stray quote inside the disclaimer's JSON string value |
| Phase 21, all arms | v1.1 (delimiters) | 100 × 3 | **0** |
| Phase 22 Gate A | v1.2 | 477 | **0** |
| Phase 23, all variants | v1.2 | 150 × 4 | **0** |

The switch from **JSON to delimiter markers** (`###FIELDNAME###`, commit
`0e83140e`) removed the nested-string boundary a stray quote could break.
**1,777 generations since, zero structural failures.**

> **But every "0" above means "0 failed *after* retries", not "0 needed a
> retry".** Content-retry attempts are not logged by `LLMOrchestrator` or
> `OllamaClient` and are not exposed by the API — gap decision **D5**, still
> open.
