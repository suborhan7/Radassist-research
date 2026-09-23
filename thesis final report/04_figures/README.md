# 04_figures — the five result charts, their CSVs, and the architecture Mermaid

Copied verbatim from `docs/thesis/figures/` at commit `99f3eab8`. **Nothing was
recomputed for this packet.** Every number in these figures is read from a
result file already in the repository, and each CSV's first line names its own
source. They were built by
`scratch/phase22_diagnosis/build_thesis_figures.py`.

`ORIGINAL_figures_README.md` is the original README, kept unedited because it
carries the caveats that belong in the published captions.

## Contents

| file | shows | n | source of the numbers |
|---|---|---|---|
| `fig01_phase0_encoder_bakeoff.png` / `.csv` | Phase 0 macro Recall@5 and nDCG@10 for four encoders, plus both pre-registered gates with class-stratified paired bootstrap CIs | val split | `ml/outputs/evaluation/encoder_comparison_macro.csv`, `gate_decision_table.csv` |
| `fig02_phase20_generation_quality.png` / `.csv` | Phase 20 Tiers 1–3 with 95% bootstrap CIs, including the BERTScore random-baseline line it **fails** to clear | 460 | `ml/outputs/evaluation/generation/tier1_bootstrap_summary.csv`, `tier2_bootstrap_summary.csv`, `tier2_bertscore_random_baseline.csv`, `tier3_chexbert_summary.json` |
| `fig03_phase21_arms_primary.png` / `.csv` | Phase 21 arms A/B/C on the primary endpoint and the three contrasts — the pre-registered C−B **did not clear** at either n | 100 and 477 | `phase21_arm_contrasts.json`, `phase21_arm_contrasts_n477.json` |
| `fig04_phase22_gateA_endpoints.png` / `.csv` | Phase 22 Gate A: every endpoint, v1.1 vs v1.2 level and paired difference | 477 | `generation_v1.2_gateA_n477/gate_a_endpoints.json`, `gate_a_results.md` §3.1.1 |
| `fig05_phase22_posthoc_micro_pr.png` / `.csv` | Phase 22 **post-hoc** micro precision/recall and per-label detail with supports | 477 | `scratch/phase22_diagnosis/out_posthoc_gate_a.txt` §2a–2b, reproduced in `gate_a_results.md` §6 |
| `architecture.mmd` | Mermaid flowchart of the pipeline in execution order | — | `backend/app/api/retrieval.py`, `generation.py`, `services/report_generation_service.py`, `core/config.py` |

All five PNGs carry **300 dpi** metadata (verified: `dpi=(299.9994, 299.9994)`)
and are greyscale-readable by construction — greys plus hatch patterns, with no
colour carrying information.

| file | pixels | size at 300 dpi |
|---|---|---|
| fig01 | 2411 × 1167 | 8.04 × 3.89 in |
| fig02 | 2460 × 1117 | 8.20 × 3.72 in |
| fig03 | 2523 × 1213 | 8.41 × 4.04 in |
| fig04 | 2627 × 1351 | 8.76 × 4.50 in |
| fig05 | 2607 × 1259 | 8.69 × 4.20 in |

## The marker convention, which the thesis must not lose

**Filled marker = the CI excludes zero. Hollow marker = it does not.** Three
results across these figures are hollow:

1. Phase 0 Gate 2, Recall@5 — `+0.0639 [−0.0065, 0.1336]`
2. The Phase 21 primary endpoint, C−B — `+0.0256 [−0.0198, +0.0710]` at n=477
3. The Phase 22 impression ROUGE-L guardrail — `+0.0149 [−0.0024, +0.0317]`

The thesis must not read as though any of these cleared.

---

## Which figures are now STALE

**None of the five result charts is stale.** Their underlying result files have
not changed since 2026-09-22 — Phase 23 produced new numbers but **on a
different (dev) set**, and Step 3 was never run, so no figure here is
contradicted. Two qualifications apply:

| figure | status | qualification |
|---|---|---|
| fig01 | **current** | — |
| fig02 | **current** | — |
| fig03 | **current** | — |
| fig04 | **current** | Gate A's verdict stands, but **adoption is not final**: the blinded manual read, a withhold trigger, has not been performed. |
| fig05 | **current** | Everything in it is post-hoc, not pre-registered. |
| `architecture.mmd` | **superseded for the UI, current for the backend** | It diagrams the backend pipeline, which has not changed. It says nothing about the page flow, which **has** — see `03_diagrams/09_page_flow.*`. |

**What IS stale is the UI screenshot set, and it is not in this folder.** All
11 PNGs in `docs/thesis/figures/ui/` depict the **superseded single-screen
workspace** — a 340 px evidence sidebar docking to a 48 px rail, with no step
bar. The page-based Generate → Report → Evidence flow landed on 2026-09-23
(commit `a8252e09`) and replaced it. `docs/thesis/figures/ui/STALE.md` marks
all 11 files stale and records that they were deliberately retained, being the
only record of what the old workspace looked like.

**The replacement set is `05_screenshots/` in this packet**, captured from the
current UI. Use those; cite the old ones only when discussing the redesign.

## A note added by this packet

`ORIGINAL_figures_README.md` also lists `ui_screenshot_list.md`, which is not
copied here because it is a work list rather than a figure. It has been
superseded by `05_screenshots/manifest.md`.
