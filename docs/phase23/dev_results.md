# Phase 23 Step 2 — dev results and the selection verdict

Pre-registered in [`plan.md`](plan.md). The selection rule in §4 of that
document was fixed before any variant ran and is applied here mechanically by
`scratch/phase23/apply_selection_rule.py`.

> **Verdict: the winner is V0 — the incumbent v1.2 system. No variant beat it.
> Step 3 is NOT run.**
>
> This is one of the outcomes the plan explicitly provided for
> (§4: *"If no variant beats V0 on macro-F1, the winner is V0 and Step 3 is not
> run"*). It is reported as a result, not as a failed experiment.

---

## 1. Runs

All four variants completed the full dev set. Every configuration was verified
two independent ways before any case was scored, per `run_dev.py`: a subprocess
resolved `app.core.config` under the same environment, and `ollama ps` after
the first real generation confirmed which model actually served the request.

| variant | model | checklist | completed | failed | structural failure rate | mean s | p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|
| **V0** | llama3:8b | off | **150/150** | 0 | **0.0000** | 4.56 | 4.53 | 4.97 | 7.15 |
| **V1** | qwen2.5:14b | off | **150/150** | 0 | **0.0000** | 7.37 | 7.33 | 8.76 | 10.76 |
| **V2** | llama3:8b | **on** | **150/150** | 0 | **0.0000** | 4.58 | 4.55 | 4.98 | 7.76 |
| **V3** | qwen2.5:14b | **on** | **150/150** | 0 | **0.0000** | 7.33 | 7.34 | 8.36 | 10.79 |

600 generations, **zero** structural failures. All metrics below are computed
on the shared uid set, which is all 150 cases since every variant completed
every case.

CheXbert labels come from the **frozen eval path**
(`ml/evaluation/score_chexbert.py` in `.venv-bertscore`, torch 2.6.0+cpu,
transformers 4.46.0) — the same instrument as every Phase 20/21/22 number,
never the runtime adapter.

## 2. Results table, exactly as printed

```
completed per variant: {'V0': 150, 'V1': 150, 'V2': 150, 'V3': 150}
SHARED uid set used for every metric: 150

==============================================================================================
      imp macroF1  imp macroP  imp macroR  temporal  contra   fail  mean s
==============================================================================================
V0         0.1227      0.1654      0.1201    0.0533  0.0000 0.0000    4.56
V1         0.0826      0.0853      0.0811    0.0533  0.0133 0.0000    7.37
V2         0.1160      0.1623      0.1089    0.0667  0.0000 0.0000    4.58
V3         0.0788      0.0834      0.0765    0.0667  0.0133 0.0000    7.33
==============================================================================================
```

### 2.1 Every metric, both sections

**V0 is the best variant on all twelve cells.** Not the best on the primary
endpoint and mixed elsewhere — the best on macro and micro, precision, recall
and F1, impression and findings.

**Impression**

| | macro-F1 | macro-P | macro-R | micro-F1 | micro-P | micro-R |
|---|---|---|---|---|---|---|
| **V0** | **0.1227** | **0.1654** | **0.1201** | **0.6120** | **0.6299** | **0.5951** |
| V1 | 0.0826 | 0.0853 | 0.0811 | 0.5325 | 0.5655 | 0.5031 |
| V2 | 0.1160 | 0.1623 | 0.1089 | 0.5833 | 0.6107 | 0.5583 |
| V3 | 0.0788 | 0.0834 | 0.0765 | 0.5017 | 0.5515 | 0.4601 |

**Findings**

| | macro-F1 | macro-P | macro-R | micro-F1 | micro-P | micro-R |
|---|---|---|---|---|---|---|
| **V0** | **0.1032** | 0.1081 | **0.1118** | **0.3513** | **0.3475** | **0.3551** |
| V1 | 0.0928 | 0.0961 | 0.0969 | 0.3271 | 0.3359 | 0.3188 |
| V2 | 0.0980 | **0.1089** | 0.1047 | 0.3404 | 0.3333 | 0.3478 |
| V3 | 0.0902 | 0.0920 | 0.0944 | 0.3123 | 0.3206 | 0.3043 |

The single exception in 24 cells is findings macro-precision, where V2 leads
V0 by 0.0008 — far inside noise and on the section the checklist does not
target.

### 2.2 Grounding endpoints

| variant | temporal (frozen 5-term) | temporal (run-plan 9-term) | strict contradiction |
|---|---|---|---|
| **V0** | **8/150 = 0.0533** | 10/150 | **0/150 = 0.0000** |
| V1 | 8/150 = 0.0533 | 11/150 | 2/150 = 0.0133 |
| V2 | 10/150 = 0.0667 | 11/150 | **0/150 = 0.0000** |
| V3 | 10/150 = 0.0667 | 14/150 | 2/150 = 0.0133 |

Both qwen arms reintroduced self-contradiction that neither llama3 arm
produced. The counts are small (2/150) and nothing here is powered to
distinguish 0.0133 from 0.0000 — but the guardrail is pre-registered as a
comparison against V0's rate, not as a significance test, and it is applied
as written.

## 3. Guardrails, exactly as printed

```
--- guardrails, per plan §4 (V0 is the reference) ---
  V0: (a) precision drop +0.0000 <= 0.03 -> PASS
      (b) temporal 0.0533 <= V0 0.0533 -> PASS;  contradiction 0.0000 <= V0 0.0000 -> PASS
      (c) structural failure 0.0000 <= 0.02 -> PASS
      ==> QUALIFIES
  V1: (a) precision drop +0.0801 <= 0.03 -> FAIL
      (b) temporal 0.0533 <= V0 0.0533 -> PASS;  contradiction 0.0133 <= V0 0.0000 -> FAIL
      (c) structural failure 0.0000 <= 0.02 -> PASS
      ==> OUT
  V2: (a) precision drop +0.0031 <= 0.03 -> PASS
      (b) temporal 0.0667 <= V0 0.0533 -> FAIL;  contradiction 0.0000 <= V0 0.0000 -> PASS
      (c) structural failure 0.0000 <= 0.02 -> PASS
      ==> OUT
  V3: (a) precision drop +0.0820 <= 0.03 -> FAIL
      (b) temporal 0.0667 <= V0 0.0533 -> FAIL;  contradiction 0.0133 <= V0 0.0000 -> FAIL
      (c) structural failure 0.0000 <= 0.02 -> PASS
      ==> OUT
```

**The guardrails did not decide this.** They are reported because the plan
requires it, but they were not load-bearing: no variant beat V0 on the primary
endpoint, so the verdict holds even if every guardrail is ignored. Stating it
the other way round would overstate their role.

## 4. Verdict, exactly as printed

```
qualifying variants: ['V0']
V0 impression macro-F1 = 0.1227
qualifying variants that BEAT V0 (strictly): []

==============================================================================================
WINNER: V0
REASON: no qualifying variant beat V0 on impression macro-F1; plan §4 makes V0 the winner
        and Step 3 is NOT run
STEP 3: NOT RUN
==============================================================================================
```

**Step 3 was not run.** No generation has touched the 477 test uids in this
phase. The test pool is exactly as Phase 22 left it.

---

## 5. Why each lever failed

Stated as description, not as a mechanism proven by this experiment. n=150,
single dev set, no confirmatory run.

### 5.1 qwen2.5:14b (V1, V3) — over-calls findings

qwen's macro-precision on impression is **0.0853 against V0's 0.1654**, close
to half. Its recall is also lower (0.0811 vs 0.1201), so this is not a
precision/recall trade — it is worse on both.

Two observations consistent with over-calling:

| | median findings words | impressions carrying ≥1 positive real label |
|---|---|---|
| reference | — | 30 / 150 |
| **V0** | 28 | **30** |
| V1 | **38** | **35** |
| V2 | 27 | 33 |
| V3 | **39** | 34 |

qwen writes materially longer findings and asserts a positive finding in more
impressions than the reference contains. More assertions against a fixed
reference lowers precision directly, and the two qwen arms are also the only
ones producing self-contradiction.

**qwen also costs 61% more latency** (7.37 s vs 4.56 s) and **4,276 MiB more
VRAM** ([`step1_measurements.md`](step1_measurements.md) §1). It is worse,
slower and larger on this task.

### 5.2 The label checklist (V2, V3) — no benefit, small cost

V2 is below V0 on impression macro-F1 (0.1160 vs 0.1227) and micro-F1
(0.5833 vs 0.6120), and raised the temporal rate from 8/150 to 10/150.

The checklist did do something measurable in the intended direction: V2
asserts a positive finding in 33 impressions against V0's 30, closer to the
reference's 30 in count but evidently not in placement, since precision barely
moved (0.1623 vs 0.1654) while recall fell (0.1089 vs 0.1201). Forcing a
disposition on every above-threshold label appears to have produced more
*stated* labels without producing more *correct* ones.

**The hypothesis the checklist was built on is not refuted by this result, and
should not be reported as refuted.** The plan targeted a specific defect —
27/477 v1.2 reports describing an abnormality in findings and calling the study
normal in the impression (`gate_a_results.md` §6.3). This dev set contains too
few abnormal cases to measure that defect: only 30 of 150 references carry any
positive real label. What V2 shows is that the checklist did not improve
aggregate labelled accuracy here, which is what the pre-registered rule asked.

## 6. A real limitation of this dev set

**13 of the 14 CheXbert labels have reference support below 10 on these 150
cases.** Per-label impression F1, with support:

| label | support | V0 | V1 | V2 | V3 |
|---|---|---|---|---|---|
| **No Finding** | **108** | **0.811** | 0.766 | 0.787 | 0.722 |
| **Lung Opacity** | **15** | 0.312 | 0.200 | **0.323** | 0.200 |
| Atelectasis | 9 | **0.261** | 0.190 | 0.182 | 0.182 |
| Enlarged Cardiomediastinum | 5 | 0.333 | 0.000 | 0.333 | 0.000 |
| Cardiomegaly | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| Fracture | 4 | 0.000 | 0.000 | 0.000 | 0.000 |
| Lung Lesion | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| Pneumonia | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| Pleural Effusion | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| Edema | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| Consolidation | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| Support Devices | 2 | 0.000 | 0.000 | 0.000 | 0.000 |
| Pneumothorax | 1 | 0.000 | 0.000 | 0.000 | 0.000 |
| Pleural Other | 1 | 0.000 | 0.000 | 0.000 | 0.000 |

**Ten labels score 0.000 for every variant**, so they contribute an identical
constant to all four macro averages. The macro-F1 ranking is effectively
decided by `No Finding`, `Lung Opacity` and `Atelectasis`.

**This does not invalidate the verdict, for a specific reason:** the ranking is
identical under **micro**-averaging, which is not support-fragile in the same
way, and identical on **findings** as well as impression. A conclusion that
held only on macro-F1 would deserve much more scepticism than this one does.

It does mean the dev set was **underpowered to detect a small improvement on
rare findings**, which is precisely where a checklist targeting under-calling
would be expected to help. Had the plan been written with these support counts
in hand, a larger or abnormality-enriched dev set would have been the better
choice. **The plan was not changed to accommodate this**, because it was
discovered after the run; it is recorded as a limitation and as the first thing
to fix if this experiment is repeated.

## 7. Pre-registered stop conditions

| # | condition | status |
|---|---|---|
| 1 | structural failure rate > 2% | **not triggered** — 0/600 across all variants |
| 2 | a held-out temporal term reaches a prompt | **not triggered** — asserted by test, checklist off and on |
| 3 | disk or VRAM exhaustion mid-run | **not triggered** — peak 11,401 of 16,376 MiB |
| 4 | dev set intersects test pool or KB | **not triggered** — four checks, all zero (plan §2.3) |
| 5 | V0's dev numbers wildly inconsistent with its Gate A test numbers | **checked, not triggered** — see below |

**Stop condition 5, checked explicitly.** V0's frozen temporal rate on dev is
**8/150 = 0.0533**; stored v1.2 on the 477 test uids is **13/477 = 0.0273**.
Two-sided binomial test of 8/150 against p = 0.0273 gives **p = 0.0699**, and
the dev rate's 95% CI **[0.0233, 0.1024] contains the test rate**. These are
different case sets and generation is non-deterministic at temperature 0, so
some difference is expected. The harness is producing v1.2-like output and the
condition is not met.

## 8. What was produced, and what was not

**Produced:** 600 generations across four verified configurations, CheXbert
labels for all of them via the frozen path, and a mechanically applied verdict.

**Not produced:** any Step 3 test-set measurement. Per plan §4, Step 3 runs
only if a variant beat V0. None did, so `docs/phase23/test_results.md` does not
exist and no new numbers exist for the 477 test uids.

## 9. What this phase establishes

1. **v1.2 with llama3:8b is not improved by either lever tested.** Both were
   worse, consistently, across macro and micro, precision and recall, findings
   and impression.
2. **A larger model is not automatically a better one for this task.**
   qwen2.5:14b is 1.85x the parameters, costs 61% more latency and 4,276 MiB
   more VRAM, and is worse on every accuracy metric measured — while also
   reintroducing self-contradiction that llama3:8b did not produce.
3. **Instructing the model to disposition every retrieved label did not
   improve labelled accuracy** on this dev set. It produced more asserted
   labels without producing more correct ones.
4. **A negative result arrived cheaply and without touching the test set** —
   which is what the dev-set design was for.

## 10. Provenance

| | |
|---|---|
| branch | `phase23-accuracy` |
| plan | committed `d55bd8b8`, before any run |
| implementation | `a45506e7`, `2d0cdb7b` |
| dev uids | `scratch/phase23/dev_uids_150.csv` (seed 20260923, val split) |
| runner | `scratch/phase23/run_dev.py` |
| scorer | `scratch/phase23/score_dev.py`, frozen eval venv |
| selection | `scratch/phase23/apply_selection_rule.py` |
| raw verdict | `scratch/phase23/dev_selection.json` |
| outputs | `ml/outputs/evaluation/phase23_dev_{V0,V1,V2,V3}/` |
