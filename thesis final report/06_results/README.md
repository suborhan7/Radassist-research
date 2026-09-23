# 06_results — every evaluation result, one table per phase

> **THE RULE THAT GOVERNS THIS FOLDER: never pool across phases.** Each phase
> ran on its own case set, under its own code state, with its own instrument.
> Every table below therefore states its own **n**, and no number from one
> table may be averaged, differenced or compared row-wise with a number from
> another. Where two phases measure the same quantity, the difference between
> them is *reported as a separate-run observation*, never as an effect.
>
> Every row cites the file the number came from. Nothing here was recomputed
> for this packet.

| file | contents |
|---|---|
| [`phase00_retrieval.md`](phase00_retrieval.md) | Phase 0 — the retrieval encoder bake-off, and Gate B calibration |
| [`phase20_generation.md`](phase20_generation.md) | Phase 20 — generation quality, Tiers 1–3 (v1.1 pre-fix) |
| [`phase21_ablation.md`](phase21_ablation.md) | Phase 21 — the evidence-mode ablation, arms A/B/C |
| [`phase22_diagnosis.md`](phase22_diagnosis.md) | Phase 22 part 1 — the diagnosis of v1.1's grounding failures |
| [`phase22_gate_a.md`](phase22_gate_a.md) | Phase 22 part 2 — Gate A, v1.2 vs v1.1, pre-registered |
| [`phase22_posthoc.md`](phase22_posthoc.md) | Phase 22 part 3 — the post-hoc analyses, **not pre-registered** |
| [`phase23_accuracy.md`](phase23_accuracy.md) | Phase 23 — the accuracy experiment; the winner was the incumbent |
| [`performance_and_tests.md`](performance_and_tests.md) | latency, VRAM, non-determinism, and test counts |

## The four results a reader must not misread

1. **Phase 0 Gate 2 on Recall@5 did not clear.** `+0.0639 [−0.0065, 0.1336]`.
   BiomedCLIP was adopted on nDCG@10 and on Gate 3; Recall@5 was inconclusive
   at this sample size.
2. **The Phase 21 primary endpoint did not clear**, at n=100 or at n=477.
   `+0.0256 [−0.0198, +0.0710]`.
3. **Phase 20's Tier 2 BERTScore fails its own validity bar.** Findings F1
   0.8420 against a random mismatched-pairs baseline of 0.8403. It does not
   discriminate on this corpus and must not be reported as though it does.
4. **Phase 22 Gate A passed all three gating criteria, but adoption is not
   final.** The blinded manual read — a pre-registered withhold trigger — has
   not been performed.

## Two instruments, one of which is frozen

Every CheXbert number in Phases 20–23 comes from the **frozen evaluation
path**: `ml/evaluation/score_chexbert.py` run inside
`ml/evaluation/.venv-bertscore` (torch **2.6.0** CPU, transformers **4.46.0**).
The runtime adapter in `backend/app/infrastructure/chexbert_labeler.py` serves
the live consistency check only, and never produced an evaluation number.
Phase 22 step A2 proved their label equivalence in three layers.

Uncertain labels are collapsed to positive, following Miura et al. 2021 — a
stated deviation from CheXbert's own weighted-F1 metric, recorded in
`ml/evaluation/score_chexbert.py`'s docstring.
