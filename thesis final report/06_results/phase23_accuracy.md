# Phase 23 — the accuracy experiment; the winner was the incumbent

**Never pool with any other phase.** These numbers are from a **150-case dev
set drawn from the val split**, not the 477-case test pool. They are not
comparable with any Phase 20/21/22 number.

| | |
|---|---|
| **Question** | Does a larger model, or an explicit label checklist, improve v1.2's labelled accuracy? |
| **Method** | Four variants × 150 dev cases = 600 generations. Selection rule fixed in `plan.md` §4 **before any variant ran**, applied mechanically by `apply_selection_rule.py`. Every configuration verified two independent ways before scoring: a subprocess resolved `app.core.config`, and `ollama ps` after the first real generation confirmed which model actually served it. |
| **n** | **150** per variant, all completed; shared uid set = all 150 |
| **Source** | `docs/phase23/dev_results.md`; `ml/outputs/evaluation/phase23_dev_{V0,V1,V2,V3}/`; raw verdict `scratch/phase23/dev_selection.json` |
| **Verdict** | **WINNER: V0 — the incumbent v1.2 system. No variant beat it. Step 3 was NOT run.** |

CheXbert labels come from the **frozen eval path** (`.venv-bertscore`, torch
2.6.0+cpu, transformers 4.46.0) — the same instrument as every Phase 20/21/22
number, never the runtime adapter.

## The four variants

| variant | model | label checklist | completed | failed | structural failure rate | mean s | p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|
| **V0** (incumbent) | `llama3:8b` | off | 150/150 | 0 | **0.0000** | **4.56** | 4.53 | 4.97 | 7.15 |
| V1 | `qwen2.5:14b` | off | 150/150 | 0 | 0.0000 | 7.37 | 7.33 | 8.76 | 10.76 |
| V2 | `llama3:8b` | **on** | 150/150 | 0 | 0.0000 | 4.58 | 4.55 | 4.98 | 7.76 |
| V3 | `qwen2.5:14b` | **on** | 150/150 | 0 | 0.0000 | 7.33 | 7.34 | 8.36 | 10.79 |

**600 generations, zero structural failures.**

## Results — V0 is best on 23 of 24 cells

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

The single exception in 24 cells is findings macro-precision, where V2 leads V0
by **0.0008** — far inside noise, and on the section the checklist does not target.

## Grounding endpoints

| variant | temporal (frozen 5-term) | temporal (run-plan 9-term) | strict contradiction |
|---|---|---|---|
| **V0** | **8/150 = 0.0533** | 10/150 | **0/150 = 0.0000** |
| V1 | 8/150 = 0.0533 | 11/150 | 2/150 = 0.0133 |
| V2 | 10/150 = 0.0667 | 11/150 | **0/150 = 0.0000** |
| V3 | 10/150 = 0.0667 | 14/150 | 2/150 = 0.0133 |

**Both qwen arms reintroduced self-contradiction that neither llama3 arm
produced.** The counts are small and nothing here is powered to distinguish
0.0133 from 0.0000 — but the guardrail was pre-registered as a comparison
against V0's rate, not as a significance test, and it was applied as written.

## Guardrails and verdict, exactly as printed

```
V0: (a) precision drop +0.0000 <= 0.03 -> PASS
    (b) temporal 0.0533 <= V0 0.0533 -> PASS;  contradiction 0.0000 <= V0 0.0000 -> PASS
    (c) structural failure 0.0000 <= 0.02 -> PASS        ==> QUALIFIES
V1: (a) +0.0801 -> FAIL   (b) contradiction 0.0133 -> FAIL            ==> OUT
V2: (a) +0.0031 -> PASS   (b) temporal 0.0667 > 0.0533 -> FAIL        ==> OUT
V3: (a) +0.0820 -> FAIL   (b) both FAIL                               ==> OUT

qualifying variants: ['V0']
qualifying variants that BEAT V0 (strictly): []
WINNER: V0 — STEP 3: NOT RUN
```

> **The guardrails did not decide this.** They are reported because the plan
> requires it, but they were **not load-bearing**: no variant beat V0 on the
> primary endpoint, so the verdict holds even if every guardrail is ignored.
> Stating it the other way round would overstate their role.

**Step 3 was not run.** No generation touched the 477 test uids in this phase.
`docs/phase23/test_results.md` **does not exist**. The test pool is exactly as
Phase 22 left it.

## A real limitation of this dev set — stated, not minimised

**13 of the 14 CheXbert labels have reference support below 10 on these 150
cases**, and **ten labels score 0.000 for every variant**, contributing an
identical constant to all four macro averages. The macro-F1 ranking is
effectively decided by `No Finding` (support 108), `Lung Opacity` (15) and
`Atelectasis` (9).

**This does not invalidate the verdict, for a specific reason:** the ranking is
**identical under micro-averaging** — which is not support-fragile in the same
way — and **identical on findings as well as impression**. A conclusion that
held only on macro-F1 would deserve much more scepticism.

It does mean the dev set was **underpowered to detect a small improvement on
rare findings**, which is precisely where a checklist targeting under-calling
would be expected to help. **The plan was not changed to accommodate this**,
because it was discovered after the run; it is recorded as a limitation and as
the first thing to fix if this experiment is repeated.

## Pre-registered stop conditions

| # | condition | status |
|---|---|---|
| 1 | structural failure rate > 2 % | **not triggered** — 0/600 |
| 2 | a held-out temporal term reaches a prompt | **not triggered** — asserted by test, checklist off *and* on |
| 3 | disk or VRAM exhaustion mid-run | **not triggered** — peak **11,401 of 16,376 MiB** |
| 4 | dev set intersects test pool or KB | **not triggered** — four checks, all zero |
| 5 | V0's dev numbers wildly inconsistent with its Gate A test numbers | **checked, not triggered** |

**Stop condition 5, checked explicitly.** V0's frozen temporal rate on dev is
8/150 = 0.0533; stored v1.2 on the 477 test uids is 13/477 = 0.0273. A
two-sided binomial test of 8/150 against p = 0.0273 gives **p = 0.0699**, and
the dev rate's 95 % CI **[0.0233, 0.1024] contains the test rate**. Different
case sets, and generation is non-deterministic at temperature 0, so some
difference is expected.

## What this phase establishes

1. **v1.2 with `llama3:8b` is not improved by either lever tested.** Both were
   worse, consistently, across macro and micro, precision and recall, findings
   and impression.
2. **A larger model is not automatically a better one for this task.**
   `qwen2.5:14b` is 1.85× the parameters, costs **61 % more latency** and
   **4,276 MiB more VRAM**, and is worse on every accuracy metric measured —
   while reintroducing self-contradiction that `llama3:8b` did not produce.
3. **Instructing the model to disposition every retrieved label did not improve
   labelled accuracy** on this dev set. It produced more asserted labels
   without producing more correct ones.
4. **A negative result arrived cheaply and without touching the test set** —
   which is what the dev-set design was for.

## Provenance

branch `phase23-accuracy`; plan committed `d55bd8b8` **before any run**;
implementation `a45506e7`, `2d0cdb7b`; dev uids
`scratch/phase23/dev_uids_150.csv` (seed 20260923, val split).
