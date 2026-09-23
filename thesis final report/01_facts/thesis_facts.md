# Thesis facts sheet — RadAssist-RAG

> **Source material, not thesis prose.** Every item is backed by a file in
> this repository and cites it. Where the repository does not record
> something, this sheet says **NOT RECORDED** rather than guessing. Nothing
> here is pooled across phases.
>
> Generated 2026-09-22 at `phase22-v1.2` / `46d2632f`.

---

## 1. System as implemented

### 1.1 Components and versions

Versions read from the installed environment (`importlib.metadata`) unless
noted.

| role | component | version | source |
|---|---|---|---|
| Embedding model | BiomedCLIP `hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224` | — | `shared/embeddings/biomedclip_embedder.py` |
| Embedding runtime | `open_clip_torch` | 3.3.0 | installed |
| Embedding dim | 512 | — | `development_log.md:451` |
| Vector DB | ChromaDB `PersistentClient` | 1.5.9 | `backend/app/infrastructure/chroma_store.py` |
| Collection | `iu_cxr_biomedclip_v1_train`, **2462** documents | — | `gate_a_run_plan.md` §1.1 |
| Collection ID hash | `c6b2ab850fc9b3fb9a1bfc6493cdd52b5322c1d9d47b4d5dba88afeb12ef72f6` | — | `gate_a_run_plan.md` §1.1 |
| LLM | `llama3:8b`, digest `365c0bd3c000`, Q4_0, 8B params | via ollama 0.34.2 | `gate_a_run_plan.md` §1.1 |
| LLM settings | temperature 0.0, seed 42, num_ctx 4096, keep_alive 30m | — | `backend/app/core/config.py` |
| LLM retries | content 2, transport 1 | — | `config.py:53-54` |
| Clinical labeler | CheXbert (`StanfordAIMI/RRG_scorers/chexbert.pth`), 14 heads | — | `backend/app/infrastructure/chexbert_labeler.py` |
| DL runtime | `torch` | 2.5.1+cu121 | installed |
| Tokeniser/NLP | `transformers` | 5.13.0 | installed |
| OCR (PHI masking) | `easyocr` | 1.7.2 | installed |
| Backend framework | FastAPI | 0.139.0 | installed |
| ASGI server | uvicorn | 0.51.0 | installed |
| Validation | pydantic 2.13.4 / pydantic-settings 2.14.2 | | installed |
| Database | SQLite (`backend/dev.db`) | — | `config.py:40` |
| ORM | SQLAlchemy | 2.0.51 | installed |
| Migrations | Alembic | 1.18.5 | installed |
| Frontend | Next.js 16.2.10, React 19.2.4 | | `frontend/package.json` |
| Frontend libs | clsx 2.1.1, tailwind-merge 3.6.0, diff 9.0.0 | | `frontend/package.json` |
| Auth | JWT (`pyjwt` 2.13.0) + Argon2 (`argon2-cffi` 25.1.0) | | `backend/app/infrastructure/` |
| Eval metrics | rouge-score 0.1.2, sacrebleu 2.6.0, nltk 3.10.0 | | installed |

**GPU:** NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB
(`fix_architecture_v1.2_FROZEN.md` §7).

### 1.2 Pipeline order as implemented

Decision **D1**'s corrected invariant is `admit → mask → embed → gate →
retrieve` (`input_admission_projection_gate_architecture_v1.1_FROZEN.md` §3.3).
The full implemented order, from `backend/app/main.py`, `app/api/retrieval.py`
and `app/services/report_generation_service.py`:

```
1  upload                     POST /retrieve (multipart image)
2  admission                  ImageAdmissionService  -- extension, size, dimensions,
                              pixel count, declared projection (DR-4: frontal only)
3  PHI masking                PHIMasker (EasyOCR, solid black boxes, never blur/inpaint)
                              cap: PHI_MASK_MAX_REGION_AREA_FRACTION = 0.08
4  embedding                  BiomedCLIPAdapter -> shared/embeddings (512-dim)
5  modality gate              ModalityGateService, softmax over prompt set
                              MODALITY_THRESHOLD = 0.60
6  projection band (DR-5)     PROJECTION_REJECT_THRESHOLD = 0.8500
                              RETRIEVAL_FLOOR = 0.8906208872795105
7  retrieval                  ChromaVectorStore + SimilaritySearchPolicy (top_k=5)
8  label voting               LabelVotingService -> VotedLabel(label, weight, agreement)
9  context builder            ContextBuilder (near-dup collapse, evidence partition)
                              EVIDENCE_MODE = FULL
--- POST /generate-report ---
10 prompt builder             PromptBuilder.build_generation_prompt
11 LLM                        LLMOrchestrator -> OllamaClient (llama3:8b)
12 structural validator       StructuralValidator (7 marker fields; content retry x2)
13 semantic validator         ResponseValidator.validate_semantic  (ADVISORY, gates nothing)
14 consistency service        ReportConsistencyService  (v1.2, OBSERVATIONAL)
15 disclaimer                 render_disclaimer (server-authored, replaces model text)
16 formatter                  ReportFormatter
17 persistence                ReportRecord (ai_draft_content + final_content)
```

**Thresholds** (`backend/app/core/config.py`, values selected in
`ml/outputs/calibration/v1_1_gate_b_selected_values.csv`):

| threshold | value | selection rule / evidence |
|---|---|---|
| `MODALITY_THRESHOLD` | 0.60 | §11.3; frontal FNR 0.0000 (n=300) |
| `PROJECTION_REJECT_THRESHOLD` | **0.8500** (config; supersedes the 0.8695 in the calibration CSV) | Selection rule **revised 2026-08-19**, from "midpoint of the separation gap" (which gave 0.8695459, lateral max 0.8484709 → frontal min 0.8906209) to "just above the observed lateral maximum". `config.py:333-375` records that **the rule was changed after seeing a failing image** — a genuine out-of-distribution frontal scored 0.8582 and was wrongly rejected — and explicitly states this is *not* presented as a pre-registered choice. Re-verified on the same 600-study set: **300/300 lateral still rejected, 0/300 frontal rejected**. Still an observed separation point, not a validated boundary. |
| `RETRIEVAL_FLOOR` | 0.8906208872795105 | §11.5 R1: 0th percentile of the frontal set (n=300); R2: 0/300 below; **mechanism unexercised** |
| `DISCLAIMER_AGREEMENT_THRESHOLD` | 0.5 | `config.py:417` |
| `MODALITY_SOFTMAX_TEMPERATURE` | 1/85.2322769165039 | BiomedCLIP's own learned logit scale |
| false-negative budget (selection input) | 0.02 | stated in source before results were read |

### 1.3 Decisions D1–D5, DR-4, DR-5

Full index: `docs/decisions/decision_log.md`.

| id | summary | status |
|---|---|---|
| **D1** | Invariant `admit → mask → embed → gate → retrieve` | approved; wording corrected |
| **D2** | Phase 21 arm switching via two-context construction (arm context → LLM, reference context → `validate_semantic()`) | approved — **summary only, source: project chat log 2026-08-17** |
| **D3** | No standalone baseline arm; marker-format failure rate deferred to Phase 21 output | approved but **blocked by D5** — chat-sourced |
| **D4** | `voted_labels` and `agreement` stored at generation time | approved; migration `c3d81b6a4f27` |
| **D5** | Record the structural attempt count | **OPEN**, blocks D3 — chat-sourced |
| **DR-4** | Frontal chest radiographs only; declared-projection branch at admission | frozen (v1.1) |
| **DR-5** | Two thresholds on top-1 similarity, not one | frozen (v1.1) |

---

## 2. Dataset

**Source:** IU / Indiana chest X-ray dataset (`development_log.md:43-44`).

| stage | count | source |
|---|---|---|
| `indiana_reports.csv` — unique studies | **3,851** | `development_log.md:43` |
| `indiana_projections.csv` — image rows | **7,466** | `development_log.md:44` |
| `study_index.csv` rows (study-level, one per uid) | **3,851** | counted |
| `master_metadata.csv` rows | **3,851** | counted |
| studies with ≥1 frontal view (`has_frontal`) | **3,689** | counted |
| studies excluded (`exclude_flag`) | **84** | counted |
| PHI masking applied (≥1 region masked) | **2,875** of 3,689 frontal = 77.9% | counted; `CLAUDE.md` |
| embeddings cached | **3,609** | counted |
| ChromaDB collection (train split, indexed) | **2,462** | `gate_a_run_plan.md` §1.1 |

**Splits** (`master_metadata.csv`, `split` column):

| split | studies |
|---|---|
| train | 2,563 |
| val | 609 |
| test | 595 |
| (blank — excluded rows) | 84 |

> Note: the split column counts (2,563 / 609 / 595) are the **study-level**
> assignment. `CLAUDE.md` records the *embedded, non-flagged, frontal* subset
> as train 2,462 / val 576 / test 571 = 3,609, which matches
> `embedding_cached`. The ChromaDB collection holds the 2,462 train figure.

**Ground truth definition.** `findings_clean` and `impression_clean` from the
IU reports, after cleaning and PHI text masking — the only two fields with
real ground truth (`run_generation_eval.py:81`,
*"the only two with real ground truth"*). Evaluation cases are the **477 real
eligible test-split cases (frontal + real findings + real impression)**
(`generation_arm_full_n477/evaluation_config.json`).

**Train/eval separation.** The retrieval knowledge base is the **train** split
only (collection `iu_cxr_biomedclip_v1_train`, 2,462 docs); generation is
evaluated on **test**-split uids. Splits are leakage-controlled at study level
and by near-duplicate clustering (TF-IDF cosine, connected components), with
clusters as the atomic split unit — ~28% of studies sit in a near-dup cluster
(`CLAUDE.md`, `ml/preprocessing/make_splits.py`).

**Licence / citation.** **NOT RECORDED.** No `.bib`, `references.md`, or
dataset licence statement exists anywhere in the repository (searched: `*.bib`,
`references*`, `citation*`, and the dev log). The dataset is named and its
counts recorded, but no licence text, DOI or formal citation is present.

---

## 3. Implemented vs not implemented

Evidence is an API route (`backend/app/api/`), a page
(`frontend/src/app/**/page.tsx`), or a service.

| feature | status | evidence |
|---|---|---|
| Patient management | **implemented** | `POST/GET /patients`, `/patients/search`, `/patients/{id}`, `/patients/{id}/history`; pages `patients/`, `patients/new/`, `patients/search/`, `patients/[patientId]/` |
| Prior studies / longitudinal comparison | **implemented** | `POST /comparisons`, `ComparisonService`, `DeterministicComparator`; page `reports/[reportId]/compare/` |
| Image upload | **implemented** | `POST /retrieve` (multipart); page `patients/[patientId]/upload/` |
| Admission gate (DR-4) | **implemented** | `ImageAdmissionService`; `upload_rejection_log` table |
| PHI masking | **implemented** | `PHIMasker` (EasyOCR); 2,875/3,689 frontal images masked |
| Modality + projection gate (DR-5) | **implemented** | `ModalityGateService`, two thresholds |
| Retrieval panel / evidence display | **implemented** | `POST /retrieve` returns cases; `GET /retrieval-sessions/{id}/image` |
| Questionnaire | **implemented** | `GET /questionnaire/{session_id}`, `QuestionnaireTemplateProvider` |
| Clinical notes | **implemented** | `clinical_notes` on `POST /generate-report`, persisted column |
| Report generation | **implemented** | `POST /generate-report` |
| Bilingual (EN / বাংলা) | **implemented, partially verified** | `_LANGUAGE_INSTRUCTIONS` en/bn; full i18n layer (324 keys) per memory. **Generated directly in Bengali, no translation pass.** No Bengali output has ever been evaluated. |
| Explainability assistant | **implemented** | `POST /reports/{id}/explain`, `ExplainabilityService`; page `reports/[reportId]/explain/` |
| Report editing | **implemented** | `PATCH /reports/{id}`, `ReportEditService`, `final_content` vs `ai_draft_content` |
| Section regeneration | **implemented** | `POST /reports/{id}/regenerate-section` (5 editable fields) |
| Status workflow | **implemented** | `ReportStatus` AI_DRAFT → DOCTOR_EDITED → FINAL; `PATCH /reports/{id}/finalize` |
| Semantic validation | **implemented, advisory** | `ResponseValidator.validate_semantic()` — **gates nothing** (Phase 8 Decision 1) |
| Consistency checking (v1.2) | **implemented, observational, not surfaced** | `ReportConsistencyService`; returned by API, stored, **rendered by no UI** |
| Auth | **implemented** | `POST /auth/register`, `/auth/login`, `/auth/logout`, `GET/PATCH /auth/me`; JWT + Argon2 |
| Roles / RBAC | **NOT implemented** | Only a `doctors` table; ownership checks exist (`_check_ownership`) but no role field or role-based authorisation |
| Audit logging | **partial** | `report_audit_log` table records report EDIT actions and `upload_rejection_log` records rejections. No general-purpose audit trail (no login/read/export events) |
| Report deletion | **implemented** | `DELETE /reports/{report_id}` |
| Dashboard | **implemented** | `GET /dashboard/stats`; page `dashboard/` |
| Settings | **implemented** | `PATCH /auth/me` (profile + workspace defaults); page `settings/` |
| Export (PDF / DOCX / other) | **NOT implemented** | No export route in `backend/app/api/`; no export library in `frontend/package.json`. `ReportFormatter` returns a structured object and is documented as *"never rendered PDF/HTML"* |

---

## 4. Evaluation results, Phase 0 → Phase 22

**Never pooled across phases.** Each row states its own n.

### 4.1 Phase 0 — retrieval encoder bake-off (the gate)

Image→image retrieval; KB = train split, queries = val split; relevance =
curated-label overlap (graded). Source: `ml/outputs/evaluation/`.

Macro metrics (`encoder_comparison_macro.csv`):

| encoder | MRR | R@1 | R@5 | R@10 | nDCG@10 |
|---|---|---|---|---|---|
| **biomedclip** | **0.4238** | **0.2826** | **0.5875** | 0.7422 | **0.1745** |
| clip_generic | 0.3091 | 0.1304 | 0.5227 | 0.6831 | 0.1140 |
| densenet121 | 0.3511 | 0.1806 | 0.5127 | 0.6808 | 0.1324 |
| random | 0.3237 | 0.1627 | 0.5155 | 0.6995 | 0.1021 |

Pre-registered gates (`gate_decision_table.csv`), class-stratified paired
bootstrap:

| gate | comparison | metric | Δ | 95% CI | excludes 0 |
|---|---|---|---|---|---|
| 1 | biomedclip − random | recall@5 | +0.0716 | [0.0204, 0.1236] | **yes** |
| 1 | biomedclip − random | nDCG@10 | +0.0726 | [0.0510, 0.0952] | **yes** |
| 2 | biomedclip − clip_generic | recall@5 | +0.0639 | [−0.0065, 0.1336] | **no** |
| 2 | biomedclip − clip_generic | nDCG@10 | +0.0604 | [0.0394, 0.0817] | **yes** |

**Verdict:** BiomedCLIP adopted. Gate 1 passed cleanly; Gate 2 passed on
nDCG@10 but was inconclusive on Recall@5; Gate 3 satisfied (wins on 11/15
real-finding classes). Manual relevance check: the label-overlap proxy is
**89% precise / 49% recall** vs hand-read judgement — a conservative lower
bound (`CLAUDE.md`).

### 4.2 Gate B calibration (v1.1)

Source: `ml/outputs/calibration/v1_1_gate_b_selected_values.csv`.

| setting | value | evidence |
|---|---|---|
| `MODALITY_THRESHOLD` | 0.60 | frontal FNR **0.0000** (n=300); 0.82 declined |
| `PROJECTION_REJECT_THRESHOLD` | 0.8695 | midpoint of separation gap (0.8485, 0.8906); **300/300** lateral rejected, **0/300** frontal |
| `RETRIEVAL_FLOOR` | 0.8906 | 0th percentile of frontal set (n=300); **0/300** below — mechanism unexercised |

### 4.3 Phase 20 — generation quality (v1.1 pre-fix), n=460 completed of 477

Tier 1 (`generation/tier1_bootstrap_summary.csv`):

| metric | n | mean | 95% CI |
|---|---|---|---|
| findings BLEU | 460 | 6.137 | [5.615, 6.711] |
| findings ROUGE-L | 460 | 0.2311 | [0.2215, 0.2409] |
| findings METEOR | 460 | 0.2710 | [0.2583, 0.2839] |
| impression BLEU | 460 | 11.083 | [9.692, 12.493] |
| impression ROUGE-L | 460 | 0.2788 | [0.2552, 0.3030] |
| impression METEOR | 460 | 0.2826 | [0.2612, 0.3058] |

Tier 2 BERTScore (`tier2_bootstrap_summary.csv`): findings F1 0.8420
[0.8394, 0.8447]; impression F1 0.8455 [0.8406, 0.8505].
**Validity check failed:** random mismatched-pairs baseline 0.8403 / 0.8432 —
"does not clear random-baseline validity bar"
(`generation/evaluation_config.json`). BERTScore does not discriminate here.

Tier 3 CheXbert (`tier3_chexbert_summary.json`): findings micro-F1 0.3015,
macro-F1 0.1511; impression micro-F1 0.5390, macro-F1 0.1808. Findings
real−baseline macro-F1 diff +0.0767, **excludes zero**.

**17 of 477 cases failed structurally**, all traced to one cause: the LLM
inconsistently quoting label names inside the disclaimer field's JSON string
(`CLAUDE.md`, prompt_builder.py:348-356). This motivated the marker format.

### 4.4 Phase 21 — evidence-mode ablation (Arms A/B/C)

Arms: A `empty` (no retrieval-derived evidence), B `labels_only`
(retrieval-as-classifier), C `full` (production).
**Arm B must never be described as "no retrieval"**
(`phase21_ablation_architecture.md` §41).

**Primary endpoint — CheXbert impression macro-F1, C − B, paired bootstrap:**

| n | diff | 95% CI | excludes 0 |
|---|---|---|---|
| 100 | −0.0197 | [−0.0621, +0.0334] | no |
| **477** | **+0.0256** | **[−0.0198, +0.0710]** | **no** |

**The primary endpoint did not clear at either sample size.**

Other C − B contrasts at n=477 (`phase21_arm_contrasts_n477.json`): findings
ROUGE-L +0.0919 [0.0832, 0.1012] **excludes 0**; findings METEOR +0.2265
[0.2151, 0.2376] **excludes 0**; findings CheXbert macro-F1 +0.0587
[0.0165, 0.0978] **excludes 0**; impression ROUGE-L +0.2145 [0.1906, 0.2403]
**excludes 0**; impression METEOR +0.2097 [0.1858, 0.2348] **excludes 0**.

**Arm A finding:** emitted one byte-identical string across all 100 cases —
a degeneracy observation (`phase21_ablation_architecture.md` §435).

**CI-width finding:** extending n from 100 to 477 reduced the macro-F1 CI
width by **5%**, against a predicted 2.2× narrowing — macro-averaged metrics
do not extrapolate as 1/√n (`development_log.md:11351`).

### 4.5 Phase 22 — diagnosis (v1.1, Arm C, n=477)

Source: `docs/phase22/diagnosis.md`.

| finding | value | CI |
|---|---|---|
| temporal language, no prior study | 167/477 = **35.0%** | [30.7, 39.5] |
| impressions with 5-gram overlap ratio 1.0 vs a neighbour | 83/353 scorable = **23.5%** | [19.2, 28.3] |
| of those, **harmful** (carry a positive finding) | 22/83 = **26.5%** | [17.4, 37.3] |
| harmful transplant rate | 22/353 = **6.2%** | [3.9, 9.3] |
| strict self-contradiction (≥1 of 13 labels) | 22/477 = **4.6%** | [2.9, 6.9] |
| held-out synonym rate | 18/477 = **3.8%** | [2.1, 5.7] |
| temporal-matcher precision (adjudicated) | 19/20 = **95.0%** | [75.1, 99.9] |

Phase 20 comparison (**separate run, never pooled**): temporal 97/460 = 21.1%;
strict contradiction 9/460 = 2.0%. Transplant **not computable** for Phase 20 —
no neighbour uids were persisted.

### 4.6 Phase 22 — Gate A (v1.2 vs v1.1, paired, n=477)

Source: `docs/phase22/gate_a_results.md`. Pre-registered in
`gate_a_run_plan.md` (commit `55e8bc08`) **before any output existed**.

| endpoint | v1.1 | v1.2 | diff | 95% CI | role |
|---|---|---|---|---|---|
| temporal (frozen def.) | 0.3501 | 0.0273 | **−0.3229** | [−0.3648, −0.2830] | **primary, PASS** |
| temporal (run-plan def.) | 0.3899 | 0.0503 | −0.3396 | [−0.3836, −0.2998] | secondary |
| CheXbert impression micro-F1 | 0.5250 | 0.5886 | +0.0636 | [+0.0314, +0.0961] | **guardrail, PASS** |
| impression ROUGE-L | 0.2496 | 0.2646 | +0.0149 | [−0.0024, +0.0317] | **guardrail, PASS** |
| harmful transplant | 0.0461 | 0.0210 | −0.0252 | [−0.0419, −0.0105] | secondary |
| strict contradiction | 0.0461 | 0.0084 | −0.0377 | [−0.0566, −0.0189] | secondary |
| held-out synonyms | 0.0377 | 0.0084 | −0.0294 | [−0.0461, −0.0147] | tripwire (not fired) |
| CheXbert impression macro-F1 | 0.1734 | 0.1958 | +0.0224 | [−0.0266, +0.0683] | descriptive |

**Verdict: all three gating criteria PASS. Adoption not final** — the blinded
manual read (a withhold trigger) has not been performed.

Generation: 477/477 completed, 0 failed. Consistency status: partial 459,
violations 17, clean 0.

### 4.7 Phase 22 — post-hoc (not pre-registered)

| analysis | result |
|---|---|
| micro **precision** | 0.5112 → 0.5863, +0.0750 [+0.0400, +0.1110] |
| micro **recall** | 0.5395 → 0.5909, +0.0514 [+0.0178, +0.0859] |
| impressions empty of positives while reference has one | **56/477 for both arms** — identical |
| findings word count (median) | 48 → 30 |
| impression word count (median) | 9 → 5 |
| temporal rate, FINDINGS only (frozen terms) | 137/477 → 6/477, −0.2746 [−0.3145, −0.2348] |
| harmful transplant, common denominator | n=261: 21/261 → 10/261, −0.0421 [−0.0728, −0.0153] |
| "normal" impression over abnormal findings | v1.1 90/477 → v1.2 **27/477** |
| micro-F1 gain concentration | largely `No Finding` (support 322, recall 0.714 → 0.804); **Pneumonia worse** (recall 0.150 → 0.050, support 20); 7/14 labels support < 10 |

### 4.8 Non-determinism

| measurement | result | source |
|---|---|---|
| v1.1 re-run, 100 pilot uids, temp 0.0 seed 42 | **33/100 byte-identical; 67/100 differ** | `gate_a_results.md` §5 |
| primary endpoint under re-run | 46/100 → 46/100, **0.0 pp movement** | same |
| earlier non-determinism finding | recorded in the QA report phase | `development_log.md` |

### 4.9 Latency and VRAM

| measurement | value | source |
|---|---|---|
| llama3:8b VRAM | 5,025 MiB | `fix_architecture_v1.2_FROZEN.md` §7 |
| BiomedCLIP marginal VRAM | 1,043 MiB | same |
| CheXbert marginal VRAM | **452 MiB** | same |
| peak, all three + inference | **7,125 MiB of 16,376** (headroom 9.03 GiB) | same |
| CheXbert latency per report | mean 8.2 ms, p50 8.0, p95 11.1 (n=50) | `development_log.md` A2 |
| consistency check latency (live) | 6.9–7.8 ms per report | `gate_a_results.md` §2 |
| end-to-end generation (Gate A) | mean **4.50 s**, median 4.47, max 5.97 (n=477) | `gate_a_results.md` §2 |
| prompt tokens v1.1 → v1.2 | max 1,236 → 1,574 of 4,096 (**+338 on every case**) | `development_log.md` A5 |

### 4.10 Trigger-case re-test (n=1, 3 runs, qualitative)

Source: `docs/phase22/trigger_case_retest.md`. Retrieval identical to the
stored v1.1 report (same 5 neighbours, same similarities). All four defects
absent in 3/3 runs: Cardiomegaly contradiction, transplant from neighbour #1
(ratio 0.50 → 0.00), "stable" ×2 → 0, nodule mislocation (no longer arises —
nodule omitted, not relocated).

---

## 5. Known defects and limitations

| # | defect | source |
|---|---|---|
| 1 | Consistency warnings stored and returned but **rendered by no UI** | `CHANGELOG_v1.2.md` §8.1 |
| 2 | Transplant check has **no threshold** (Gate B) — every English report reads `partial` | `amendment_01_consistency_status.md` §2(e) |
| 3 | **No retry** (Gate C) — 17/477 violations acted on by nothing. `CONSISTENCY_RETRY_COUNT = 1` exists in `config.py:273` but **is read by no service**; `report_generation_service.py:389` states "Gate A performs no [retry]" | `gate_a_results.md` §2; `config.py:273` |
| 4 | **Omission defect**: 27/477 v1.2 reports state an abnormality in findings and call the study normal in the impression; no check covers it | `gate_a_results.md` §6.3 |
| 5 | **Bengali entirely unmeasured**; all three checks English-only | `gate_a_results.md` §7 |
| 6 | `ChromaVectorStore` **ignores `settings.CHROMA_PERSIST_PATH`** (own repo-root default; `main.py` passes no argument) | `gate_a_results.md` §5 |
| 7 | **D5 open**: structural retry attempt count unrecorded; blocks D3 | `decision_log.md` |
| 8 | Blinded manual read **pending** (withhold trigger) | `reader_packet.md` |
| 9 | Pre-registration defect: frozen doc supported two primary-endpoint definitions | `gate_a_results.md` §3.1.1 |
| 10 | 4 stored rows read `clean` that should read `partial` | `amendment_01_consistency_status.md` §3 |
| 11 | `validate_semantic()` concatenates findings+impression, so cross-section contradiction is unrepresentable; gates nothing | `diagnosis.md` §1d |
| 12 | Phase 21 primary endpoint **did not clear** at n=100 or n=477 | §4.4 above |
| 13 | Phase 20 Tier 2 BERTScore **fails its random-baseline validity bar** | `generation/evaluation_config.json` |
| 14 | Macro-F1 CI does not narrow with n (ratio 1.014 from n=100→477) | `fix_architecture_v1.2_FROZEN.md` §6.3 |
| 15 | CheXbert **negation bug** on this corpus: "No acute, displaced rib fractures" labelled Fracture=Positive (5 of 18 cases) | `development_log.md` §1c Fracture finding |
| 16 | PHI masking is a deployment-readiness feature, **not a validated PHI-recall measurement** — no burned-in-PHI ground truth exists | `CLAUDE.md` |
| 17 | `declared_projection` is a **harness constant** ("PA"), not per-case dataset truth | `generation_arm_full_n477/evaluation_config.json` |
| 18 | `RETRIEVAL_FLOOR` mechanism **unexercised**: 0/300 frontal fell below it | `v1_1_gate_b_selected_values.csv` |
| 19 | `PROJECTION_REJECT_THRESHOLD`'s selection rule was **changed after observing a failure** (a real frontal scoring 0.8582 rejected). The repo records this openly as a post-hoc revision rather than a pre-registered choice, and re-verifies 300/300 lateral, 0/300 frontal — but the thesis must present it as post-hoc | `config.py:333-375` |
| 20 | Explanation prompt changed by v1.2 (shares `_evidence_section()`) and is **not evaluated** | `gate_a_results.md` §7 |
| 21 | Phase 21 recorded **no model digest, collection count or ID hash**, so v1.2 could not verify identity against it | `gate_a_run_plan.md` §1.2 |
| 22 | No export functionality (PDF/DOCX) | §3 above |
| 23 | No roles/RBAC | §3 above |
| 24 | Branch `phase22-v1.2` **not merged**; `main` still at `a107d4ef` | `git log` |

---

## 6. External sources, licences and citations

### 6.1 Bibliography in the repository

**NOT RECORDED.** There is no `.bib` file, no `references.md`, and no
citations file anywhere in the repository (searched `*.bib`, `references*`,
`citation*` outside virtualenvs). The items below are the external sources
actually used, assembled from code and the development log. **Formal
citations must be written for the thesis; this repository does not contain
them.**

| source | version / identifier | licence recorded in repo? |
|---|---|---|
| **IU / Indiana chest X-ray dataset** | `indiana_reports.csv` (3,851 studies), `indiana_projections.csv` (7,466 rows) | **NOT RECORDED** — no licence, DOI or citation anywhere |
| **BiomedCLIP** | `hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224` | **NOT RECORDED** |
| **llama3:8b** | ollama digest `365c0bd3c000`, Q4_0, 8B | licence text is shipped inside the model (`ollama show` prints "META LLAMA 3 COMMUNITY LICENSE AGREEMENT", release date 2024-04-18). **Not stored in the repo.** |
| **CheXbert** | `StanfordAIMI/RRG_scorers/chexbert.pth` | **RECORDED IN DETAIL** — see §6.2 |
| ChromaDB | 1.5.9 | NOT RECORDED |
| PyTorch | 2.5.1+cu121 | NOT RECORDED |
| transformers | 5.13.0 | NOT RECORDED |
| open_clip_torch | 3.3.0 | NOT RECORDED |
| FastAPI / uvicorn / SQLAlchemy / Alembic / pydantic | see §1.1 | NOT RECORDED |
| Next.js / React | 16.2.10 / 19.2.4 | NOT RECORDED |
| EasyOCR | 1.7.2 | NOT RECORDED |
| rouge-score / sacrebleu / nltk | 0.1.2 / 2.6.0 / 3.10.0 | NOT RECORDED |
| bert-score (Phase 20 Tier 2) | in `ml/evaluation/.venv-bertscore` | NOT RECORDED |
| PubMedBERT (BERTScore model) | `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`, layer 9 | NOT RECORDED |

### 6.2 CheXbert licensing — recorded in full

Source: `development_log.md:9417-9450`, "Phase 20 Tier 3 (CheXbert) — Steps
1-2: Availability, Licensing, Environment".

- **Distribution.** The official Stanford Box link in
  `stanfordmlgroup/CheXbert`'s README **returns a genuine 404** — the official
  channel is dead, not gated. The only working source found was the
  third-party HuggingFace mirror `StanfordAIMI/RRG_scorers/chexbert.pth`
  (1.31 GB, no login).
- **The mirror's "MIT" tag is very likely a mislabel** by the third-party
  uploader and is **not authoritative**.
- **Governing terms**: the upstream repo's `LICENSE.pdf` — **Stanford Docket
  S20-295, "Academic Software License Agreement", dated 2020-10-15**, read in
  full. Royalty-free but binding by use; restricted to **internal academic
  non-commercial purposes** (this thesis qualifies); **requires citing Smit et
  al. 2020 in any publication**; and **"RECIPIENT may not further distribute
  Software without express written permission of STANFORD."**
- **Operational consequence, recorded so it is never silently violated:**
  `chexbert.pth` **must never be committed to this repository, pushed to the
  public remote, or included in any public thesis submission bundle.** It
  lives in the HuggingFace cache
  (`~/.cache/huggingface/hub/models--StanfordAIMI--RRG_scorers/`), outside the
  repository entirely, so it never needs to be gitignored-and-trusted.
- **Required citation:** Smit et al. 2020 (CheXbert). Full bibliographic
  details **NOT RECORDED** in the repo.
- **Metric deviation recorded:** uncertain → positive collapse follows
  Miura et al. 2021 (NAACL, `github.com/ysmiura/ifcc`, `eval_prf.py`), a
  stated deviation from CheXbert's own weighted-F1 metric
  (`ml/evaluation/score_chexbert.py` docstring).

### 6.3 Other licensing notes

- **Query images are stored in the repository** under
  `backend/uploaded_images/`. Whether that is compatible with the IU dataset's
  terms is **NOT RECORDED**.
- No `LICENSE` file exists for this project itself. **NOT RECORDED.**

---

## 7. Team members and roles

| name | role | source |
|---|---|---|
| **Borhan** | reader 1 for the blinded manual read; named owner of the Bengali limitation | `fix_architecture_v1.2_FROZEN.md` §6.4, §9 |
| **Sumaiyah** | reader 2 for the blinded manual read; author of the QA report (13 findings) | `fix_architecture_v1.2_FROZEN.md` §6.4; `development_log.md` QA report entry |
| git author | `suborhan7` | `git log` |

Neither reader is a radiologist (`fix_architecture_v1.2_FROZEN.md` §6.4).
Formal role titles, supervisor, institution and degree programme are
**NOT RECORDED** anywhere in the repository.

---

## 8. Figures and data

Built by `scratch/phase22_diagnosis/build_thesis_figures.py` from existing
result files only; nothing was recomputed. Each PNG has a CSV beside it whose
first line names its source. See
[`figures/README.md`](figures/README.md) for the caveats that belong in the
captions.

| figure | shows | section above |
|---|---|---|
| [`figures/fig01_phase0_encoder_bakeoff.png`](figures/fig01_phase0_encoder_bakeoff.png) | Phase 0 encoder bake-off + both pre-registered gates with CIs | §4.1 |
| [`figures/fig02_phase20_generation_quality.png`](figures/fig02_phase20_generation_quality.png) | Phase 20 Tiers 1–3 with CIs, incl. the BERTScore validity bar | §4.3 |
| [`figures/fig03_phase21_arms_primary.png`](figures/fig03_phase21_arms_primary.png) | Phase 21 arms A/B/C, primary endpoint and contrasts | §4.4 |
| [`figures/fig04_phase22_gateA_endpoints.png`](figures/fig04_phase22_gateA_endpoints.png) | Phase 22 Gate A, every endpoint, v1.1 vs v1.2, paired CIs | §4.6 |
| [`figures/fig05_phase22_posthoc_micro_pr.png`](figures/fig05_phase22_posthoc_micro_pr.png) | Phase 22 post-hoc micro precision/recall and per-label detail | §4.7 |
| [`figures/architecture.mmd`](figures/architecture.mmd) | Mermaid flowchart of the pipeline as implemented, in execution order | §1.2 |
| [`figures/ui_screenshot_list.md`](figures/ui_screenshot_list.md) | Ordered list of UI screens to capture, with route and state | §3 |

**Marker convention in every CI panel: filled = CI excludes zero, hollow = it
does not.** Three results in these figures are hollow — Phase 0 Gate 2
Recall@5, the Phase 21 primary endpoint, and the Phase 22 impression ROUGE-L
guardrail. The thesis must not read as though they cleared.
