# Phase 20 — generation quality (v1.1, pre-fix)

**Never pool with any other phase.** This measured the **v1.1** system, before
the Phase 22 grounding fix.

| | |
|---|---|
| **Question** | How good are the generated reports, measured three ways? |
| **Method** | Three tiers on the test split: Tier 1 n-gram overlap, Tier 2 embedding similarity, Tier 3 clinical labels. Ground truth is `findings_clean` and `impression_clean` — *"the only two with real ground truth"* (`run_generation_eval.py:81`). Bootstrap CIs throughout. |
| **n** | **460 completed of 477 eligible** — 17 failed structurally |
| **Source** | `ml/outputs/evaluation/generation/` |

## Tier 1 — n-gram overlap

`tier1_bootstrap_summary.csv`

| metric | n | mean | 95% CI |
|---|---|---|---|
| findings BLEU | 460 | 6.137 | [5.615, 6.711] |
| findings ROUGE-L | 460 | 0.2311 | [0.2215, 0.2409] |
| findings METEOR | 460 | 0.2710 | [0.2583, 0.2839] |
| impression BLEU | 460 | 11.083 | [9.692, 12.493] |
| impression ROUGE-L | 460 | 0.2788 | [0.2552, 0.3030] |
| impression METEOR | 460 | 0.2826 | [0.2612, 0.3058] |

**Verdict: tight and informative.** These are the phase's usable numbers.

## Tier 2 — BERTScore: **the validity check FAILED**

`tier2_bootstrap_summary.csv`, `tier2_bertscore_random_baseline.csv`

| metric | n | F1 | 95% CI | random mismatched-pairs baseline |
|---|---|---|---|---|
| findings | 460 | 0.8420 | [0.8394, 0.8447] | **0.8403** |
| impression | 460 | 0.8455 | [0.8406, 0.8505] | **0.8432** |

**Verdict: does not clear the random-baseline validity bar**
(`generation/evaluation_config.json`). A metric that scores randomly paired
reports almost as highly as real ones is not discriminating on this corpus.
**Tier 2 must not be reported as a quality result.** Model:
`microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`, layer 9.

## Tier 3 — CheXbert clinical labels: **clears the bar Tier 2 missed**

`tier3_chexbert_summary.json`

| section | micro-F1 | macro-F1 |
|---|---|---|
| findings | 0.3015 | 0.1511 |
| impression | 0.5390 | 0.1808 |

| contrast | value | excludes 0 |
|---|---|---|
| findings, real − random baseline, macro-F1 | **+0.0767** | **yes** |

**Verdict: Tier 3 is the phase's valid clinical-accuracy instrument.**

## The 17 structural failures — one root cause

**17 of 477 cases failed structurally**, and all 17 trace to a single cause:
the LLM inconsistently quoting label names inside the disclaimer field's JSON
string value, which broke `json.loads()` at that boundary.

This is the finding that changed the system: the output format was switched
from **JSON to delimiter markers** (`###FIELDNAME###`), because there is then
no nested-string-inside-string boundary for a stray quote to break — for that
field or any other. Commit `0e83140e`, 2026-07-23. Source:
`backend/app/services/structural_validator.py:11-20`;
`development_log.md`, "Finding: All 17 Generation Failures Share One Root
Cause".

## Two other Phase 20 findings

- **The Fracture anomaly was root-caused**, not dismissed as labeler noise: it
  is a real retrieval-attribution grounding failure. Separately, CheXbert has a
  **negation bug on this corpus** — *"No acute, displaced rib fractures"* is
  labelled Fracture = Positive, in 5 of 18 cases inspected.
- **`declared_projection` is a harness constant** (`"PA"`) in the evaluation
  runs, not per-case dataset truth
  (`generation_arm_full_n477/evaluation_config.json`).

## Comparison with later phases — do not pool

Phase 22's diagnosis re-measured two of Phase 20's properties on a **separate
run**: temporal language 97/460 = 21.1%, strict contradiction 9/460 = 2.0%.
Those are reported alongside Phase 22's own 35.0% and 4.6% as *separate-run
observations*, never as a change. Transplant rate is **not computable** for
Phase 20 at all — no neighbour uids were persisted.
