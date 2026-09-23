# Final report packet — index

Everything the final report needs, assembled 2026-09-23 on branch `final-prep`
at `99f3eab8`. **No source file was changed to build this packet.**

## The rules this packet was built under

1. **Every fact cites a file**, and a line where it is useful.
2. **Where the repository is silent, it says `NOT RECORDED`** — never an estimate.
3. **No number was recomputed** for this packet. Every result is read from an
   artifact that already existed, except the two test-suite runs in
   `06_results/performance_and_tests.md`, which were **executed** for this packet
   and are labelled as such.
4. **Results are never pooled across phases.** Each phase ran on its own case
   set, under its own code state, with its own instrument.
5. Every diagram ships as **Mermaid source + a 300 dpi PNG + a caption file**,
   greyscale-readable by construction.

---

## 01_facts — the primary records, copied verbatim

| file | what it is |
|---|---|
| `thesis_facts.md` | the consolidated fact sheet |
| `CHANGELOG_v1.2.md` | what Phase 22 changed, and its §8 "Not done" table |
| `trigger_case_retest.md` | the case that triggered Phase 22, re-run against v1.2 |
| `decision_log.md` | D1–D5 and DR-4/DR-5, with provenance for each |
| `phase22_fix_architecture_v1.2_FROZEN.md` | the frozen fix architecture |
| `amendment_01_consistency_status.md` | the amendment that added the `partial` status |
| `gate_a_results.md` | Phase 22 Gate A, in full |
| `phase23_plan.md`, `phase23_dev_results.md` | Phase 23 pre-registration and outcome |
| **`environment.md`** | exact versions to reproduce the system |
| **`timeline.md`** | phase-by-phase dates, milestones, commit counts |
| **`feature_catalogue.md`** | every user-facing feature, with what is **not** implemented and why |

## 02_backend — the deep dive

`backend_architecture.md` (51 KB) — layering and dependency injection, the full
request lifecycle for `POST /upload` and `POST /generate-report` naming every
service in order with file and line, every behavioural threshold and how it was
chosen (**the projection threshold revision is marked post-hoc**), the data
model and its migrations, error handling and retries, concurrency and caching,
security, and a table of every API endpoint.

## 03_diagrams — source + 300 dpi PNG + caption

| # | diagram | parts |
|---|---|---|
| 1 | system architecture | — |
| 2 | ML pipeline | — |
| 3 | RAG pipeline | — |
| 4 | use case | — |
| 5 | activity, report generation | split into `05`, `05b`, `05c`; all three documented in the `05` caption |
| 6 | sequence, generate report | — |
| 7 | ER diagram | split into `07` (core) and `07b` (satellites); both in the `07` caption |
| 8 | deployment | — |
| 9 | page flow | — |

All twelve PNGs carry **300 dpi** metadata (verified `dpi=(299.9994, 299.9994)`).

## 04_figures — the five result charts

The Phase 0 / 20 / 21 / 22 charts with their CSVs, plus `architecture.mmd`.
Its `README.md` records which are stale: **none of the five result charts is**;
`architecture.mmd` is **superseded for the UI, current for the backend**.
The marker convention — **filled = CI excludes zero, hollow = it does not** —
is documented there and must not be lost.

## 05_screenshots — the current page-based UI

**33 PNGs at 1440 × 900**, captured 2026-09-23 against a **disposable copy of
`dev.db`**. `dev.db` was verified byte-identical before and after
(`sha256 2823386768…`, size and mtime unchanged). See `manifest.md` for the
per-screen table, the two recorded deviations, and the capture scripts.

**Three of the four consistency states are shown. `clean` is not — because no
state of this system produces it** until Gate B calibrates the transplant
threshold.

## 06_results — every evaluation result, one table per phase

| file | phase |
|---|---|
| `phase00_retrieval.md` | Phase 0 encoder bake-off |
| `phase20_generation.md` | Phase 20 generation quality (v1.1) |
| `phase21_ablation.md` | Phase 21 evidence ablation |
| `phase22_diagnosis.md` | Phase 22 part 1 — diagnosis |
| `phase22_gate_a.md` | Phase 22 part 2 — Gate A, pre-registered |
| `phase22_posthoc.md` | Phase 22 part 3 — **post-hoc, not pre-registered** |
| `phase23_accuracy.md` | Phase 23 — the winner was the incumbent |
| `performance_and_tests.md` | latency, VRAM, non-determinism, test counts |

**The four results a reader must not misread** are listed in that folder's
`README.md`.

## 07_manual — `user_manual_outline.md`

The steps a new user follows, each with its screen, action, what they see, and
the screenshot that illustrates it. Ends with **what the manual must not
promise**.

## 08_admin

- `known_defects.md` — defects in the system (A1–A11), in the instruments
  (B1–B7), and in the record itself (C1–C8), plus by-design scope limits.
- `open_items.md` — nine open items. **O1 (blinded read) and O5 (Bengali)
  block a claim the thesis would otherwise want to make.**

## p2 report

The previous (P2) LaTeX report, kept as the baseline the final report revises.
Its Chapter 4 describes a **DenseNet121 classification** design that the built
system does not use — the system retrieves with **BiomedCLIP**. Differences are
reconciled in the final report, not here.

---

## The five things most likely to be got wrong

1. **v1.2 is not adopted.** Gate A passed every automated criterion, but the
   blinded manual read — a withhold trigger that overrides a clean pass — has
   not been performed.
2. **The Phase 21 primary endpoint did not clear**, at n=100 or n=477:
   `+0.0256 [−0.0198, +0.0710]`.
3. **Phase 20's Tier 2 BERTScore fails its own validity bar** and must not be
   reported as a quality result.
4. **Arm B is "retrieval-as-classifier", never "no retrieval."**
5. **No clinician has evaluated anything**, and **no Bengali output has ever
   been measured.**
