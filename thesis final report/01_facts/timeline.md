# timeline.md — phase-by-phase dates, milestones and commit counts

> **Source of every date and count:** `git log` on branch `final-prep` at
> commit `99f3eab8`, plus the dated headings in
> `docs/methodology/development_log.md`. Phases are assigned to commits by the
> commit subject line, which names its phase explicitly in every case.
>
> **Total: 90 commits, 2026-07-11 → 2026-09-23 (75 calendar days).**
> Work happened on **15 distinct days**; the repository is silent on effort
> between them, so no duration is claimed for any phase beyond its
> first-to-last commit date.

---

## 1. Commits per active day

| date | commits |
|---|---|
| 2026-07-11 | 2 |
| 2026-07-12 | 9 |
| 2026-07-13 | 3 |
| 2026-07-14 | 2 |
| 2026-07-17 | 5 |
| 2026-07-18 | 4 |
| 2026-07-22 | 5 |
| 2026-07-23 | 2 |
| 2026-08-08 | 5 |
| 2026-08-09 | 1 |
| 2026-08-10 | 1 |
| 2026-09-19 | 17 |
| 2026-09-21 | 9 |
| 2026-09-22 | 10 |
| 2026-09-23 | 15 |
| **total** | **90** |

There is a **40-day gap** with no commits at all between 2026-08-10 and
2026-09-19. The repository does not record what happened in it — **NOT
RECORDED**.

---

## 2. Phase table

`first` and `last` are the dates of that phase's first and last commit.
Single-commit phases show one date.

| phase | milestone | first | last | commits | first / last commit |
|---|---|---|---|---|---|
| **0–2** | Data foundation, encoder validation gate, embedding pipeline | 2026-07-11 | 2026-07-11 | **1** | `58553fd4` |
| **3** | ChromaDB retrieval indexing | 2026-07-11 | 2026-07-11 | **1** | `213f4ba4` |
| **4** | Backend assembly: RetrievalService, LabelVotingService, DB layer, Alembic, FastAPI skeleton, Swagger (12 steps) | 2026-07-12 | 2026-07-12 | **6** | `d094461c` → `3da205c6` |
| **5** | Context Builder | 2026-07-12 | 2026-07-12 | **1** | `07371ed8` |
| **6** | Prompt Builder | 2026-07-12 | 2026-07-12 | **1** | `165aea17` |
| **7** | LLM Orchestrator, StructuralValidator, OllamaClient | 2026-07-12 | 2026-07-12 | **1** | `e0fa2242` |
| **8** | Response Validator + Hospital Report Formatter — first full generation chain | 2026-07-13 | 2026-07-13 | **1** | `e52595b5` |
| **9** | Clinical Questionnaire | 2026-07-13 | 2026-07-13 | **1** | `1b151420` |
| **10** | Explainability Chat | 2026-07-13 | 2026-07-13 | **1** | `c21bd5b1` |
| **11** | Longitudinal patient history and comparison | 2026-07-14 | 2026-07-14 | **1** | `7711fdb6` |
| **12** | Radiologist workflow UI — the whole frontend, 8 steps | 2026-07-14 | 2026-07-14 | **1** | `9bacaede` |
| **13a/13b** | Auth + doctor ownership (backend, then login/register frontend) | 2026-07-17 | 2026-07-17 | **2** | `34760a29`, `7f4413b5` |
| **14** | Visual system pass | 2026-07-17 | 2026-07-17 | **1** | `886dba6c` |
| **15** | Ownership UI | 2026-07-17 | 2026-07-17 | **1** | `d357912b` |
| **16** | Settings / Profile, BMDC number field, system stats | 2026-07-17 | 2026-07-17 | **1** | `54243cd0` |
| **17** | Finalize / edit workflow | 2026-07-18 | 2026-07-18 | **1** | `486da609` |
| **18** | Word-level diff view | 2026-07-18 | 2026-07-18 | **2** | `c1de6a7f`, `3c445245` |
| **19** | Section-level regeneration | 2026-07-18 | 2026-07-18 | **1** | `cdf4a417` |
| *post-19* | Route protection, nan-bug fix, dashboard rebuild, landing page, architecture docs tracked | 2026-07-22 | 2026-07-22 | **2** | `5ea45f8e`, `b8fffb4f` |
| **20** | Generation-quality evaluation (Tiers 1–3); **JSON → delimiter-marker format change** | 2026-07-22 | 2026-07-23 | **5** | `e7d939c0` → `d2485f8d` |
| *redesign* | Reading Room dark-theme redesign, E2E owner-flow harness, release audit | 2026-08-08 | 2026-08-10 | **7** | `fcaf9c7c` → `2849405f` |
| *gate v1.1* | Input admission + projection gate v1.1, Gate B recalibration, QA fixes | 2026-09-19 | 2026-09-19 | **4** | `c39654a6` → `bd0ce97a` |
| **21** | Evidence-mode ablation, Arms A/B/C, n=100 then n=477, closing verification | 2026-09-19 | 2026-09-19 | **12** | `34ea5599` → `149b3fb6` |
| *freeze* | **CODE FREEZE** — backend, ml and thresholds frozen | 2026-09-19 | 2026-09-19 | **1** | `a107d4ef` |
| **22** | Decision log, v1.2 fix architecture, consistency service, CheXbert runtime labeler, amendment 01, prompt grounding, **Gate A**, post-hoc, trigger re-test, thesis facts | 2026-09-21 | 2026-09-22 | **14** | `ae271d68` → `7d3a8bc8` |
| **23** | Pre-registered accuracy experiment, 4 variants × 150 dev cases; **verdict V0, Step 3 not run** | 2026-09-22 | 2026-09-22 | **5** | `d55bd8b8` → `3c0b3a00` |
| *UI final* | Summary-first report, evidence sidebar, Orthoc light mode, print/PDF, **page-based Generate → Report → Evidence flow** | 2026-09-23 | 2026-09-23 | **15** | `b526e122` → `99f3eab8` |

---

## 3. Dated milestones from the development log

These are the entries whose headings carry an explicit date. Earlier phases'
entries carry no date in the log, so their dates above come from git alone.

| date | milestone | dev log |
|---|---|---|
| 2026-08-20 | Phase 20 / Phase 21 boundary: code state, tag, and what Phase 21 runs on | `development_log.md:11265` |
| 2026-08-19 | `PROJECTION_REJECT_THRESHOLD` selection rule **revised post-hoc** after a real out-of-distribution frontal was wrongly rejected | `backend/app/core/config.py:364-403`; `development_log.md:10865` |
| 2026-09-19 | CI width does not extrapolate as 1/√n for macro-averaged metrics | `development_log.md:11351` |
| 2026-09-19 | Phase 21 final verdicts — phase CLOSED | `development_log.md:11467` |
| 2026-09-19 | Phase 21 closing verification — four items, two defects found | `development_log.md:11586` |
| 2026-09-19 | **Code freeze** — backend, ml and thresholds | commit `a107d4ef` |
| 2026-09-21 | Phase 22 A1 — ReportConsistencyService core, observational and unwired | `development_log.md:11755` |
| 2026-09-21 | Phase 22 A2 — CheXbert runtime labeler, equivalence proven in three layers | `development_log.md:11970` |
| 2026-09-21 | Phase 22 A3 — consistency columns migration (`7f2a91c4d6e8`) | `development_log.md:12188` |
| 2026-09-21 | Phase 22 A4 — wiring the service in observational mode | `development_log.md:12427` |
| 2026-09-21 | Phase 22 A4.1 — amendment 01: the `partial` consistency status | `development_log.md:12689` |
| 2026-09-22 | Phase 22 A5 — prompt grounding changes (i)–(iv) | `development_log.md:13004` |
| 2026-09-22 | Phase 22 A6 — **pre-registered Gate A evaluation run**, all three gating criteria PASS | `development_log.md:13303` |
| 2026-09-22 | Phase 23 — accuracy improvement experiment, pre-registered and validation-selected | `development_log.md:13468` |
| 2026-09-23 | Workspace UI — summary-first report panel, evidence sidebar, consistency verdict's first rendering | `development_log.md:13639` |
| 2026-09-23 | Light mode re-derived from the Orthoc template — hue adopted, luminance rejected | `development_log.md:13906` |
| 2026-09-23 | Report print / Save as PDF, including a Bengali page that rasterises | `development_log.md:14045` |
| 2026-09-23 | Page-based Generate / Report / Evidence flow; six tests retargeted under negative control | `development_log.md:14214` |

---

## 4. Ordering facts that matter for the thesis

1. **The code freeze (2026-09-19, `a107d4ef`) precedes Phase 22.** Every
   Phase 22 change is therefore a deliberate post-freeze amendment recorded
   in `docs/phase22/fix_architecture_v1.2_FROZEN.md`, not drift.
2. **The Gate A run plan (`55e8bc08`) was committed before any Gate A output
   existed**, and the Phase 23 plan (`d55bd8b8`) before any variant ran. Both
   pre-registrations are verifiable from commit order.
3. **The projection-threshold revision (2026-08-19) came after seeing a
   failing image** and is marked post-hoc in the config source itself.
4. **Branch `phase22-v1.2` was never merged to `main`**; `main` remains at
   `a107d4ef`, the code-freeze commit
   ([`thesis_facts.md`](thesis_facts.md) §5 defect 24). The current branch is
   `final-prep`.
5. All Phase 20 / 21 / 22 / 23 evaluation numbers were produced **after** the
   relevant code state was fixed, and each phase states its own n. They are
   never pooled — see [`../06_results/`](../06_results/).
