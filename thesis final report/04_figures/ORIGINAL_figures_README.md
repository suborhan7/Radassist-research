# Thesis figures

Generated 2026-09-22 from existing result files only. **Nothing here was
recomputed** — every number is read from a file already in the repository, and
each CSV's first line names its source.

Regenerate with:

```bash
python scratch/phase22_diagnosis/build_thesis_figures.py
```

All PNGs are 300 dpi and grayscale-readable by construction: greys plus hatch
patterns, no colour carries information.

| file | what it shows | source |
|---|---|---|
| `fig01_phase0_encoder_bakeoff.png/.csv` | Phase 0 macro Recall@5 and nDCG@10 for 4 encoders; the two pre-registered gates with class-stratified paired bootstrap CIs | `ml/outputs/evaluation/encoder_comparison_macro.csv`, `gate_decision_table.csv` |
| `fig02_phase20_generation_quality.png/.csv` | Phase 20 (n=460) Tiers 1–3 with 95% bootstrap CIs, including the BERTScore random-baseline line it fails to clear | `ml/outputs/evaluation/generation/tier1_bootstrap_summary.csv`, `tier2_bootstrap_summary.csv`, `tier2_bertscore_random_baseline.csv`, `tier3_chexbert_summary.json` |
| `fig03_phase21_arms_primary.png/.csv` | Phase 21 arms A/B/C on the primary endpoint, and the three contrasts — the pre-registered C−B did not clear at n=100 or n=477 | `ml/outputs/evaluation/phase21_arm_contrasts.json`, `phase21_arm_contrasts_n477.json` |
| `fig04_phase22_gateA_endpoints.png/.csv` | Phase 22 Gate A, every endpoint, v1.1 vs v1.2 level and paired difference (n=477) | `ml/outputs/evaluation/generation_v1.2_gateA_n477/gate_a_endpoints.json`, `docs/phase22/gate_a_results.md` §3.1.1 |
| `fig05_phase22_posthoc_micro_pr.png/.csv` | Phase 22 **post-hoc** micro precision/recall, and per-label precision/recall with supports | `scratch/phase22_diagnosis/out_posthoc_gate_a.txt` §2a–2b, reproduced in `gate_a_results.md` §6 |
| `architecture.mmd` | Mermaid flowchart of the pipeline as implemented, in execution order | code: `backend/app/api/retrieval.py`, `generation.py`, `services/report_generation_service.py`, `core/config.py`; counts from `thesis_facts.md` §2 |
| `ui_screenshot_list.md` | Ordered list of UI screens to screenshot, with route + state | `frontend/src/app/**/page.tsx` |

## Reading the marker convention

In every CI panel: **filled marker = CI excludes zero; hollow marker = it does
not.** This is deliberate — three of the results in these figures are hollow
(Phase 0 Gate 2 Recall@5, the Phase 21 primary endpoint, and the Phase 22
impression ROUGE-L guardrail), and the thesis must not read as though they
cleared.

## Caveats that belong in the captions

- **Fig 3**: Arm B is `labels_only`, i.e. retrieval-as-classifier. It must never
  be described as "no retrieval" (`phase21_ablation_architecture.md` §41). The
  n=100 and n=477 bars are different case sets and are not comparable row-wise.
- **Fig 4(a)**: rates and scores share one axis. Read each row on its own; the
  bars are not comparable across rows.
- **Fig 5**: everything in this figure is **post-hoc**, not pre-registered
  (`gate_a_results.md` §6). Seven of the fourteen CheXbert labels have support
  below 10 and are omitted from panel (b) as unreliable.
- **Fig 2**: BERTScore fails its own random mismatched-pairs validity bar
  (0.8420 vs 0.8403 findings; 0.8455 vs 0.8432 impression), so it does not
  discriminate on this corpus.

## Validation performed

- `architecture.mmd` parses: `mermaid.parse()` v11 under jsdom →
  `PARSE OK  diagramType = flowchart-v2`.
- All five PNGs were rendered and visually inspected at full size.
- The CSVs are written by the same script pass that draws each figure, from the
  same in-memory values, so figure and CSV cannot disagree.
