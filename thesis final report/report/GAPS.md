# GAPS.md — what the final report could not confirm, and how it was assembled

Written alongside `final_report.docx` on 2026-09-29, on branch `final-prep`.
This file records every gap, every unverified claim, every editorial decision
about reused text, and every conflict between the inputs and how it was
resolved. It exists so that nothing in the report has to be taken on trust.

**Nothing was fabricated to fill a gap.** Where the repository, the packet and
the P1/P2 documents were all silent, the report says so inline and this file
records it.

---

## 0. What was produced

| File | Pages | Contents |
|---|---|---|
| `chapter_1.docx` | 7 | Introduction |
| `chapter_2.docx` | 8 | Literature Review |
| `chapter_3.docx` | 20 | System Analysis (full rewrite) |
| `chapter_4.docx` | 20 | Design and Methodology |
| `chapter_5.docx` | 25 | Implementation |
| `chapter_6.docx` | 27 | Result and Discussion |
| `chapter_7.docx` | 17 | User Manual |
| `chapter_8.docx` | 7 | Conclusion and Future Work |
| **`final_report.docx`** | **157** | Front matter + all 8 chapters + references |
| `feature_catalogue.docx` | 41 | Standalone: all 68 features with 34 screenshots |

The assembled report contains **45 figures** and **62 tables**, both lists
generated from the captions themselves rather than maintained by hand.

---

## 1. Every `[TO CONFIRM]` marker, with its location

**30 markers across 6 chapters and the reference list.** None is a placeholder
for something that could have been looked up in the available material; each
marks something the project genuinely never recorded.

### 1.1 Chapter 1 — Introduction

| # | §  | What is unconfirmed |
|---|---|---|
| 1 | 1.1 | **The "more than 170 million" population figure.** Carried from the P2 report, which cited no source. No source exists in P1, P2 or the repository. Kept because §2 of the plan requires reusing accurate P2 text, but marked because rule 1 requires traceability. |

### 1.2 Chapter 2 — Literature Review

| # | §  | What is unconfirmed |
|---|---|---|
| 2 | 2.2.1 | **The CE scores reported by R2Gen and its successors**, with each one's dataset and labeller configuration. Must be read from the primary publications. No value was supplied from memory. |
| 3 | 2.2.6 | **The commercial-system review** (PowerScribe, Rad AI, Smart Reporting, DeepTek). Conducted at the proposal stage; the repository records no product-by-product notes, versions or evaluation dates. |

### 1.3 Chapter 3 — System Analysis (16 markers)

| # | §  | What is unconfirmed |
|---|---|---|
| 4 | 3.1.2 (NFR-10) | **Energy consumed per report.** No power measurement of any kind was ever taken. |
| 5 | 3.1.2 (NFR-11) | **Concurrent multi-user throughput.** No load test was ever run. |
| 6 | 3.3.3 | **The IU X-ray dataset licence, DOI and formal citation.** Never transcribed into the repository. |
| 7 | 3.3.3 | **Whether storing query images inside the repository is compatible with the dataset's terms.** Not recorded. |
| 8 | 3.3.3 | **BiomedCLIP's licence and citation.** Not recorded anywhere in the repository. |
| 9 | 3.3.3 | **No `LICENSE` file exists for this project itself.** |
| 10 | 3.7 | **Energy per report** (restated in the environmental analysis) — no wall-power reading, no GPU power sample, no derived figure. |
| 11 | 3.7 | **Embodied carbon / hardware lifecycle.** No assessment performed. |
| 12 | 3.9.3 | **What happened during the 40-day commit gap** (2026-08-10 → 2026-09-19). The repository is silent; no account is offered. |
| 13 | 3.9.4 | **Halimaya Sadia's role, task allocation and contribution.** The repository records no role for this member and no formal division of responsibilities for any member. Must be supplied from outside the repository. |
| 14 | 3.11.1 | **Hardware purchase price.** Not recorded. |
| 15 | 3.11.1 | **Electricity cost.** Not recorded. |
| 16 | 3.11.1 | **Labour hours and rate.** No hours logged. Commit counts are not a measure of effort. |
| 17 | 3.11.3 | **Cloud-hosting cost estimate.** No pricing was ever gathered. |
| 18 | 3.11.4 | **Baseline reporting cost and clinician time saving.** Neither measured; no clinician has used the system. **No cost–benefit figure is offered as a result.** |
| 19 | 3.3.1 | (Non-marker, recorded here) **Phase 21's per-stage latency profile was never produced** — the specified file and its directory do not exist. |

### 1.4 Chapters 4–6

| # | §  | What is unconfirmed |
|---|---|---|
| 20 | 4.4.1 | **The dataset's licence, DOI and citation** (cross-reference to marker 6). |
| 21 | 5.1.5 | **`README.md` and `CLAUDE.md` both describe repository layouts that no longer match the repository.** `CLAUDE.md` states `backend/` and `frontend/` do not exist in this copy; all three exist, along with `e2e/`. The layout in the report was verified directly. |
| 22 | 6.10.1 | **Published CE figures for comparison** (cross-reference to marker 2). The report makes only the weak, defensible claim — a comparable *range* without any training — and quotes no published number. |

### 1.5 Reference list (7 markers)

| # | Entry | What is unconfirmed |
|---|---|---|
| 23 | [20]–[25] blanket | **The repository contains no bibliography file and no transcribed citation for any component or dataset.** A repository-wide search for `*.bib`, `references*` and `citation*` returns nothing outside virtual environments. |
| 24 | [20] CheXbert | Venue and page numbers. **Citation is required by the licence**, so the entry must be completed, not dropped. |
| 25 | [21] IU X-ray | Authors, volume, issue, pages; plus the licence text and DOI. |
| 26 | [22] BiomedCLIP | Full author list, year, current publication status. |
| 27 | [23] Llama 3 | Authorship attribution and citation form. |
| 28 | [24] CheXpert | Venue, volume, pages. |
| 29 | [25] R2Gen | Venue and pages. Its reported scores are **deliberately not quoted** anywhere in the report. |
| 30 | — | Entries [1]–[19] are reproduced **as recorded in the P1/P2 `references.bib`**. They were not re-verified against primary sources; they are accurate as a record of what P1/P2 cited. |

---

## 2. Claims whose only source is the development log or project chat

Per §8.2 of the plan. These are claims with no code artefact or result file
behind them. They are usable, but their provenance is weaker than the rest of
the report and any examiner question about them should be answered with that
provenance stated.

### 2.1 Sourced from the project chat log, not the repository

The decision log is explicit that these have **no full text in any repository
document** and that any thesis text relying on them must cite the project chat
log of **2026-08-17** rather than implying a repository document backs it.

| ID | Claim | Where used in the report |
|---|---|---|
| **D2** | Phase 21 arm switching via two-context construction, for measurement hygiene. | §4.1.2, §6.4 (method description) |
| **D3** | No standalone baseline arm; marker-format failure rate deferred to Phase 21 output. Approved but blocked by D5. | §5.3.7 |
| **D5** | Record the structural retry attempt count; preferred design is to widen the return type. **Open, unscoped, blocks D3.** | §4.2.5, §5.3.7, §6.3.4, §6.9.5, §8.3.2 — cited in the report as chat-sourced |
| — | Validation warnings describe the AI draft only and are not recomputed after doctor edits. | §5.2.4, §7.6.2 |

Additionally recorded: **the decision numbering itself is unverified** — whether
D1–D5 is the complete set, or whether further unnumbered decisions exist, has
never been established.

### 2.2 Sourced from the development log rather than a result artefact

| Claim | Where used |
|---|---|
| Near-duplicate rate of 28.2% (1,064/3,767) and the 51-report largest cluster | §2.1.4, §4.4.4 |
| Embedding validation: within-cluster similarity 0.9131 vs random-pair 0.8831; image→text top-1 4.8% / top-5 15.6% | §2.1.4, §2.1.5 |
| PHI masking run totals: 2,875/3,689, 4,278 regions, 0.426 s/image | §3.8.1, §4.4.2 |
| Masking embedding-impact validation: mean cosine 0.992, min 0.9215, 0/50 flagged | §3.8.1, §4.2.2, §6.7 |
| Indexing: 2,462 records in 1.03 s, six pre-insertion validation checks | §4.4.5 |
| The Fracture investigation (18/18 disjoint, 5/18 negation mislabels) | §6.3.5 |
| Non-determinism diagnosis (five requests → two reports; cold vs warm) | §5.3.5, §6.9.4 |
| The QA report's 13 findings and the write-only preferences | §3.5.2, §5.2, feature catalogue F-13 |
| Contrast ratio tables and the Orthoc-derived light palette | §5.2.7 |
| Print/Bengali rasterisation verification (9 sections, 781 codepoints) | §4.2.7, §5.2.6, §7.11 |

### 2.3 Claims resting on a single observation

| Claim | Status in the report |
|---|---|
| Trigger-case re-test (n=1, 3 runs) | Reported as **qualitative, proving nothing about rates**, with Gate A's n=477 named as the rate evidence (§6.5.9) |
| Screenshot 13's timings (upload 0.1 s, retrieval 1.0 s, generation 3.9 s) | Explicitly marked **not a benchmark** wherever it appears (§7.5, feature catalogue F-23) |

---

## 3. Sections that could not be completed, and why

| Section | What is missing | Why |
|---|---|---|
| §3.7 Environmental Impact | Energy per report; embodied carbon | Never measured. The section makes only the structural argument (no training energy; inference bounded at 4.5 s on one GPU) and explicitly declines to derive watt-hours from VRAM and wall-clock, which would require a power figure the project never took. |
| §3.11 Economic Analysis | Development cost, marginal cost in currency, cloud comparison, cost–benefit | No financial record of any kind was kept. The section gives the **shape** of the argument and the conditions under which it would hold, and states that a cost–benefit claim cannot be made from this project's evidence. |
| §3.9.4 Roles | Per-member task allocation | Only three role facts exist in the repository (reader 1, reader 2, git author). One member has no recorded role. |
| §6.10.1 Comparison with published work | The published numbers themselves | No transcribed figure exists in the project. The section states the four-way incomparability and makes only the feasibility claim. |
| §3.3.1 Technical feasibility | Per-stage latency breakdown | Specified for Phase 21 and **never produced**; the file and directory do not exist. |

---

## 4. P1/P2 text: kept, edited, replaced

Per §2 of the plan. Chapter 3 was a **full rewrite** by instruction and is
excluded from this table. Chapters 5, 7 and 8 have no P1/P2 antecedent — P2
contained no implementation chapter, no user manual, and only a six-line
conclusion — so they are new throughout.

### 4.1 Chapter 1

| P2 passage | Action | Reason |
|---|---|---|
| §Background ¶1 (Bangladesh disparity, travel, cost) | **Kept**, verbatim apart from British spelling and one clause | Still accurate; §2 of the plan requires reuse where accurate. Population figure marked `[TO CONFIRM]`. |
| §Background ¶2 (LLMs, hallucination, RAG) | **Kept**, lightly edited | Accurate. Removed "automatically generating medical images", which misdescribes what the cited work does. |
| §Motivation, whole section | **Kept** as §1.2 ¶1, edited | Accurate and still the project's rationale. "pre-built RAG engine" → "retrieval-augmented pipeline", because the delivered system assembles its own pipeline rather than adopting a packaged engine. |
| §Problem Statement ¶1–2 | **Kept**, edited | Accurate. |
| §Problem Statement, remainder | **Replaced** | P2 described the problem generically. Replaced with the three specific gaps this project addressed, including the measured attribution failure — which P2 could not have known about. |
| §Project Objectives (5 bullets) | **Replaced** | P2's objectives describe a system that was not built (pre-built RAG framework, CNN classification). Replaced with the delivered objective list, each testable and status-marked. |
| §Methodology in brief | **Replaced** | P2 describes a DenseNet121/CNN feature-extraction pipeline. The delivered system trains no classifier. |
| §Work Plan SDLC table (12 months) | **Replaced** | The real schedule is 90 commits over 75 days on 15 active days (§3.9.2). The P2 table is a plan, not a record. |
| §Project Features (17 numbered items) | **Replaced** | Contains features never built (BMDC verification, admin login, chat assistant, PDF download, report filtering, feedback/error reporting). Replaced by §3.1 requirements and §3.1.3's not-delivered table. |
| §Scopes and Challenges | **Edited substantially** | In/out-of-scope statements kept where still true. "Challenges" replaced: P2 listed anticipated risks; §1.6.3 lists what was actually encountered. |
| Nomenclature list | **Kept and extended** | All P2 entries retained; ~30 added for terms the built system introduced. |

### 4.2 Chapter 2

| P2 passage | Action | Reason |
|---|---|---|
| §Preliminaries — Deep Learning in Medical Vision | **Kept**, edited | Accurate. Added the paragraph distinguishing frozen feature extractor from trained classifier, which is the distinction the delivered system turns on. |
| §Preliminaries — LLMs and the "Black Box" Problem | **Kept**, edited for register | Accurate. |
| §Preliminaries — RAG (Lewis et al.) | **Kept**, edited | Accurate. |
| §Preliminaries — Semantic Search and Vector Embeddings | **Kept**, edited | Accurate. Added the measured 0.88 baseline similarity, which bounds how the thresholds in Ch. 5 should be read. |
| §Introduction and Overview | **Merged** into §2.1.2 and §2.2 | Substantially duplicated the Preliminaries. Merging removed the repetition. |
| §Existing Solutions and Technical Limitations | **Kept**, reorganised into §2.2.1–2.2.3 | Accurate. |
| §Bridging the Infrastructure Gap (all subsections) | **Kept**, edited | Accurate and load-bearing for the research gap. Gu et al.'s domain-specificity claim now carries this project's own Phase 23 test of it. |
| §Social Trust and Explainable AI | **Kept**, rewritten as prose | Accurate; P2's bullet-inside-itemize structure did not survive into a report register. Added the applied conclusion (why no saliency map ships). |
| §Summary of Key Findings (3 items) | **Kept and extended to 5** | The three original findings stand. Added the attribution-vs-retrieval-noise refinement and the metric-weakness finding, both from this project's own results. |
| §Research Gap | **Kept**, edited and extended | The infrastructure-gap argument is unchanged. Added the four further gap elements and the table mapping each to the chapter addressing it. |
| §Conclusion (duplicated as Ch. 5 in P2) | **Dropped** | It was the same paragraph in two places, and its content is carried by §2.4 and Ch. 8. |
| — | **New: §2.1.6** (clinical labellers, CE metrics) | P2 had no account of the metric family every result in Ch. 6 depends on. |
| — | **New: §2.2.4** (how the field evaluates) | Needed to motivate the pre-registration discipline. |
| — | **New: §2.3.1** (MIMIC-CXR vs IU X-ray) | Needed to bound every comparison in §6.10. |

### 4.3 Chapter 4 — and the P2 corrections it makes

P2's Chapter 4 describes a **DenseNet121 classification** design that the built
system does not use. It is therefore **replaced**, not edited, with four
exceptions where its text described something that survived:

| P2 passage | Action | Reason |
|---|---|---|
| §Dataset — IU X-ray chosen for having both images and reports | **Kept** | Still the reason. |
| §ChromaDB — lightweight, similarity search, Python integration | **Kept**, edited | Still the rationale for the vector store. |
| §RAG — the risk of hallucination and the intent to ground output | **Kept**, edited | Still the design intent. |
| §Future Improvements & Limitations — modality limits, KB-quality dependence, decision-support framing | **Kept** | All three still true; now evidenced. |
| Everything describing DenseNet121 as the pipeline core, its training, its feature layer as the retrieval embedding, MongoDB, and the proposed workflow diagram | **Replaced** | The system retrieves with BiomedCLIP and trains nothing. |

**Factual corrections to P2, recorded as the plan requires:**

| # | P2 stated | Correct value | Where corrected |
|---|---|---|---|
| C1 | "7,265 images and radiology reports" | **3,851 studies** and **7,466 image rows** — P2 conflated studies with images | §4.4.2, Table 4.4 |
| C2 | "7,625 unique images" (in the same chapter as C1) | As C1. **P2 is internally inconsistent**, giving both 7,265 and 7,625 | §4.4.2 |
| C3 | "validation accuracy remained stable within a maximum of 51.91%" | **55.91%** — contradicts P2's own results table, where 55.91 is the epoch-1 value. The narrative figure appears to be a transposition | §4.3.1 |
| C4 | MongoDB as the database | **SQLite + ChromaDB** | §4.2.6 |
| C5 | Grad-CAM explainability listed as a feature | **Not built**, deliberately, on ethical grounds | §3.8.5, §4.3.5, §8.3.4 |
| C6 | Knowledge base built from four source categories (reports, disease descriptions, templates, guidelines) | **Only IU X-ray reports** are indexed | §4.4.5 |
| C7 | "The embeddings and metadata will be stored in ChromaDB" from DenseNet121 | Embeddings are **BiomedCLIP**, 512-dim | §4.2.2 |

---

## 5. Template-to-report mapping, and conflicts between inputs

### 5.1 The mapping (per §5.0 of the plan)

The department template stops at Chapter 5; the faculty pointers run to Chapter 8
and renumber. **The pointers decide the numbering; every template section is
preserved inside the pointers' structure.** No section from either document was
dropped.

| Template section | Faculty pointers | Final location |
|---|---|---|
| Ch1 Introduction | — | **Chapter 1** |
| Ch2 Literature Review | — | **Chapter 2** |
| Ch3 §3.1 Final Specifications | Ch3 §3.1–3.4 System Analysis | **Chapter 3 §3.5** (pointers' four sections first, at §3.1–3.4) |
| Ch3 §3.2–3.8 | — | **Chapter 3 §§3.6–3.11** (societal, environmental, ethical, project management, risk, economic) |
| Ch4 Design | — | **Chapter 4** |
| — | Ch5 Implementation | **Chapter 5** |
| Ch5 §5.1 Performance Evaluation | Ch6 Result and Discussion | **§6.1** |
| Ch5 §5.2 Analysis of Design Solutions | — | **§6.7** |
| Ch5 §5.2 Final Design Adjustment | — | **§6.8** |
| Ch5 §5.3 Statistical Analysis | — | **§6.9** |
| Ch5 §5.4 Comparisons and Relationships | — | **§6.10** |
| Ch5 §5.6 Discussion | — | **§6.11** |
| — | Ch6 §6.1 Key Achievements and Limitations | **§6.12** |
| — | Ch7 User Manual | **Chapter 7** |
| — | Ch8 Conclusion and Future Work | **Chapter 8** |

### 5.2 Conflicts between inputs, and how each was resolved

| # | Conflict | Resolution |
|---|---|---|
| 1 | **The department template and the faculty pointers number chapters differently** and the template stops at 5. | Plan §5.0 applied: pointers decide numbering, every template section preserved. Mapping above. |
| 2 | **The faculty pointers' Chapter 7 examples** (home screen, contact page, guardian/child chat, review page) belong to a different project. | Plan §5 Ch7 applied: **substituted** with this project's real screens from `05_screenshots/`. Recorded here as the plan requires. |
| 3 | **P2 Chapter 4 describes a system that was not built.** | Plan rule 2 applied: describe as built, explain the change, record the corrections. See §4.3 above. |
| 4 | **`thesis_facts.md` §1.1 attributes `num_ctx` 4096 to the backend config.** | The backend deep dive corrects this: the parameter is set **nowhere in the codebase**; 4096 is Ollama's own default. The correction is carried into §5.1.2. |
| 5 | **`thesis_facts.md` §5 defect 1 says the consistency verdict is rendered by no UI.** | Superseded: `feature_catalogue.md` records that all four states render as of 2026-09-23. The report uses the corrected state, and §8.3.2 lists the *remaining* gap (not surfaced in list views). |
| 6 | **Ollama version differs between records** — 0.34.2 at the Gate A run, 0.34.3 in `environment.md`. | Both stated in §5.1.2; neither harmonised away, because a reproduction needs to know which produced the results. (A third value, **0.34.4**, was observed on the machine on 2026-09-29 — see §7.) |
| 7 | **Backend test wall-time differs between two records** (207.51 s and 213.99 s). | Both stated in §5.4.1 as two runs on the same day. |
| 8 | **The projection threshold differs between the calibration CSV (0.8695) and the config (0.8500).** | Both appear in the report, with the config value marked as superseding and the revision marked **post-hoc** (§5.3.5, §6.2.3). |
| 9 | **The split counts differ between records** — 2,563/609/595 study-level vs 2,462/576/571 embedded. | Both given in §4.4.2 with the distinction stated: study-level assignment vs the embedded, non-flagged, frontal subset. |
| 10 | **`CLAUDE.md` states `backend/` and `frontend/` do not exist in this copy.** | Verified false on 2026-09-23 and again on 2026-09-29; all three exist, plus `e2e/`. Marked `[TO CONFIRM]` in §5.1.5 as drift in the record. |
| 11 | **Plan page targets vs delivered length.** Ch3 targeted 12–15 pages, delivered **20**; Ch5 targeted 15–20, delivered **25**; Ch6 targeted 15–18, delivered **27**; Ch7 targeted 10–12, delivered **17**. | **The plan's content requirements were treated as binding over its page guidance.** Ch3 carries 11 mandated sections and 11 tables; Ch5 §5.3 is required by plan §3 to be "the most thoroughly illustrated and explained section of the report"; Ch6 carries 12 sections and 5 figures; Ch7 carries 28 screenshots. Table typography was tightened to 9 pt to recover space rather than cutting required content. Recorded here as a deliberate deviation. |

### 5.3 A note on two inputs

The department chapter template and the faculty pointers were **not supplied as
separate files**. The user confirmed mid-task that both are merged into
`REPORT_PLAN.md`, so §5 of the plan was treated as the authoritative statement
of both, and the mapping in §5.1 above reconstructs the reconciliation the plan
describes. The P1 LaTeX project and the "p2 report" folder were verified to be
**byte-identical file sets** (23 files, same sizes), so they are one input, not two.

---

## 6. Figures and tables: what was used, and what was not

- **All 9 required diagrams** from `03_diagrams/` appear, each in the chapter that
  discusses it and referenced by number: system architecture (Fig. 4.1), ML
  pipeline (4.2), RAG pipeline (4.3), activity in three parts (4.4–4.6), sequence
  (4.7), ER in two parts (4.8–4.9), page flow (4.10), use case (3.1), deployment (5.1).
- **All 5 result charts** from `04_figures/` appear in Chapter 6 (Figs. 6.1–6.5).
- **All 33 screenshots** appear: 28 in Chapter 7, and all 33 in the standalone
  feature catalogue.
- **The marker convention is preserved** wherever a chart is discussed: filled =
  CI excludes zero, hollow = it does not. The three hollow results are named in
  the text as not having cleared.
- **No figure appears that the text does not discuss.**
- `architecture.mmd` was **not** included: it is superseded for the UI by the page
  flow diagram, and current for the backend only, which Fig. 4.1 already covers
  at higher fidelity.
- The 11 stale UI screenshots in `docs/thesis/figures/ui/` were **not** used;
  they depict the superseded single-screen workspace.

---

## 7. Changes to the environment during this work

The report describes the recorded environment. On **2026-09-29** the servers were
started from this archive copy, which revealed environment facts that differ from
the recorded ones. **No report text was changed to match them**, because the
recorded environment is what produced every measurement.

| Item | Recorded in the report | Observed 2026-09-29 |
|---|---|---|
| torch | 2.5.1+cu121 | **2.14.0+cpu** — GPU unavailable |
| fastapi | 0.139.0 | 0.141.1 |
| transformers | 5.13.0 | 5.17.0 |
| SQLAlchemy | 2.0.51 | 2.1.1 |
| Ollama | 0.34.2 (Gate A) / 0.34.3 | **0.34.4** |
| chromadb | 1.5.9 | 1.5.9 (matches) |
| Collection count | 2,462 | **2,462 (matches)** |

This is a direct demonstration of the caveat already in §5.1.4: the requirements
file **does not pin the backend stack**, so a reinstall from it does not reproduce
the recorded versions. The archive copy shipped without a virtual environment or
`node_modules`, both of which were created to start the servers. `backend/dev.db`
was backed up before anything ran, Alembic was already at head `7f2a91c4d6e8`
(no migration executed), and the backup was moved out of the repository so that
`git status` on `backend/`, `ml/`, `frontend/src/` and `shared/` stayed empty.

---

## 8. Source-tree integrity

Plan §0 requires that `git status` for `backend/`, `ml/` and `frontend/src/`
stays empty throughout. **It did.** Verified at the start of the work, before
each chapter commit, after starting the servers, and at completion.

Every commit in this series touches only `thesis final report/report/`:

```
00196da7  docs(report): chapter 1
a202ccf9  docs(report): chapter 2
297ba73c  docs(report): chapter 3
49eabc98  docs(report): chapter 4
96fddc1f  docs(report): chapter 5
da2b56ea  docs(report): chapter 6
5c8c457f  docs(report): chapter 7
54df8f0   docs(report): complete feature catalogue with screenshots
d771199   docs(report): chapter 8
d3c8d10   docs(report): assemble final_report.docx
```

---

## 9. The five things a reader of this report must not get wrong

Carried from the packet's own warning list, and honoured throughout the report:

1. **v1.2 is not adopted.** Gate A passed every automated criterion, but the
   blinded manual read — a withhold trigger that overrides a clean pass — has
   not been performed. Every mention of v1.2 in the report carries this.
2. **The Phase 21 primary endpoint did not clear**, at n=100 or n=477:
   `+0.0256 [−0.0198, +0.0710]`. Reported as the phase's headline.
3. **Phase 20's Tier 2 BERTScore fails its own validity bar** and is never
   reported as a quality result.
4. **Arm B is "retrieval-as-classifier", never "no retrieval."** Stated
   explicitly wherever the ablation appears.
5. **No clinician has evaluated anything, and no Bengali output has ever been
   measured.** Stated in the abstract, §1.3, §3.5.2, §6.12 and §8.2.2.
