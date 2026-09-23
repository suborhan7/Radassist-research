# backend_architecture.md — the deep dive

> **Every claim below cites a file, and a line where the line is what proves
> it.** Read at commit `99f3eab8` (branch `final-prep`), 2026-09-23. The API
> endpoint table in §9 was generated from the **live `/openapi.json`** of a
> running instance, not read off the source. Where the repository is silent,
> the text says **NOT RECORDED**. No number is estimated.

**Scale.** 11,477 lines of Python under `backend/app/` plus `backend/tests/`:
36 service modules, 12 API routers, 9 ORM models, 7 infrastructure adapters,
15 Alembic migrations, and **534 passing tests** (`pytest -q`, 213.99 s, run
today).

---

## 1. Layering: clean architecture as actually realised

Four layers, with dependencies pointing **inward only**.

```
app/api/            transport. FastAPI routers. Validate, call one service,
                    serialize, map exception -> HTTP status. No medical logic.
app/services/       the application layer. Every rule, every sequence, every
                    clinical decision. Depends on Protocols, never on adapters.
app/domain/         entities.py (dataclasses + enums) and interfaces.py
                    (Protocols). Depends on NOTHING in this codebase.
app/infrastructure/ adapters to the outside world: ChromaDB, Ollama, CheXbert,
                    BiomedCLIP, PyJWT, Argon2. Each satisfies one Protocol.
app/models/         SQLAlchemy ORM. Persistence shape, separate from domain
                    entities — the two are deliberately not the same objects.
```

### 1.1 Where the interfaces live

**`backend/app/domain/interfaces.py`** — 396 lines, 21 `@runtime_checkable`
`Protocol` classes and nothing else. Its own docstring (`:4-5`) states the
rule: *"Services depend on these, never on concrete"* implementations.

| Protocol | line | implemented by |
|---|---|---|
| `IEmbedder` | `:34` | `infrastructure/biomedclip_adapter.py` → `shared/embeddings/biomedclip_embedder.py` |
| `IVectorStore` | `:42` | `infrastructure/chroma_store.py` |
| `IImageValidator` | `:62` | `services/image_validator.py` |
| `ISimilaritySearchPolicy` | `:72` | `services/similarity_search.py` |
| `ILabelVoter` | `:82` | `services/label_voting_service.py` |
| `IContextBuilder` | `:89` | `services/context_builder.py` |
| `IPromptBuilder` | `:101` | `services/prompt_builder.py` |
| `ILLMClient` | `:149` | `infrastructure/ollama_client.py` |
| `IStructuralValidator` | `:156` | `services/structural_validator.py` |
| `ILLMOrchestrator` | `:166` | `services/llm_orchestrator.py` |
| `IResponseValidator` | `:191` | `services/response_validator.py` |
| `IReportFormatter` | `:205` | `services/report_formatter.py` |
| `IQuestionnaireProvider` | `:213` | `services/questionnaire_templates.py` |
| `IPatientRepository` | `:221` | `services/patient_service.py` |
| `IDeterministicComparator` | `:258` | `services/deterministic_comparator.py` |
| `IStudyRepository` / `IReportRepository` | `:284`, `:290` | declared; no concrete implementation in this repository |
| `IDoctorRepository` | `:297` | `services/doctor_service.py` |
| `IPasswordHasher` | `:320` | `infrastructure/password_hasher.py` |
| `ITokenService` | `:331` | `infrastructure/jwt_handler.py` |
| `ISectionLabeler` | `:339` | `infrastructure/chexbert_labeler.py` |
| `IReportConsistencyChecker` | `:370` | `services/report_consistency_service.py` |

**Protocols, not ABCs, and that is load-bearing twice.**
(a) `shared/embeddings/biomedclip_embedder.py` satisfies `IEmbedder`
*structurally*, without importing anything from `backend/` — which is what
keeps the frozen `ml/` ⇄ `backend/` no-import boundary intact while both sides
use one embedder implementation. (b) `PromptBuilder` implements six of
`IPromptBuilder`'s seven methods and deliberately omits
`build_translation_prompt`; a Protocol permits that, an ABC would not
(`services/prompt_builder.py:14-17`).

### 1.2 Dependency injection: one lifespan, `app.state`, no container

There is **no DI framework**. `backend/app/main.py`'s `lifespan` async context
manager (`:106-248`) constructs every shared collaborator **once per process**
and hangs it on `app.state`. Routes read them off `request.app.state`; they
construct nothing expensive themselves.

| built in lifespan | line | why once |
|---|---|---|
| `BiomedCLIPAdapter` | `:109` | loads the BiomedCLIP model |
| `ChromaVectorStore` | `:110` | opens the persistent client |
| `PHIMasker` | `:117-119` | loads EasyOCR |
| `ImageAdmissionService` | `:131-143` | every parameter read from `settings` here, once |
| `ModalityGateService` | `:149-161` | **M6: the text prompt vectors are encoded inside this constructor** — this line *is* the prompt-vector cache |
| `RetrievalService` | `:168-173` | wires validator + embedder + store + policy |
| `LabelVotingService` | `:174` | — |
| `ContextBuilder` | `:177` | evidence mode injected from config, so an ablation arm is a restart with an env override, not a code path |
| `PromptBuilder` | `:185-189` | shares the **same** temporal term list the consistency checker matches on |
| `LLMOrchestrator` | `:191-197` | holds both retry budgets |
| `ResponseValidator`, `ReportFormatter` | `:198-199` | cheap, but singletons for consistency |
| `ChexbertLabeler` | `:218-223` | **wrapped in try/except** — see §6.3 |
| `ReportConsistencyService` | `:238-241` | transplant thresholds deliberately **not** passed |
| `QuestionnaireTemplateProvider`, `DeterministicComparator`, `Argon2PasswordHasher`, `JWTHandler` | `:242-245` | stateless, singletons for uniformity (`main.py:52-58` states this explicitly) |

**The one documented exception.** `PatientService` is *not* on `app.state`: it
depends on nothing but a per-request DB session, so `api/patients.py`
constructs it per route. `main.py:21-31` records this and the mixed pattern in
`ComparisonService`, which takes a per-request `PatientService` **and** three
`app.state` singletons.

**Request-scoped:** only the DB session (`api/dependencies.py:36-41`, a FastAPI
`yield` dependency) and `ReportGenerationService` / `ReportEditService`, which
are cheap shells assembled per request from `app.state` singletons plus the
session (`api/generation.py:101-119`).

### 1.3 Every service, its single responsibility, its inputs and outputs

| service | file | single responsibility | in → out |
|---|---|---|---|
| `ImageAdmissionService` | `services/image_admission_service.py` | A1–A17: is this file admissible at all? | `bytes, ext` → `AdmittedImage` \| raises |
| `ImageValidator` | `services/image_validator.py` | the older path-based file check (Phase 4) | `path` → None \| raises |
| `ModalityGateService` | `services/modality_gate_service.py` | is this a frontal chest radiograph, and how well supported is it? | `vector` → `float`; `top1` → `RetrievalSupport` \| raises |
| `RetrievalService` | `services/retrieval_service.py` | orchestrate embed → query → select. No logic of its own | `vector, top_k, min_sim` → `list[RetrievedCase]` |
| `SimilaritySearchPolicy` | `services/similarity_search.py` | threshold, then top-K descending | `raw, top_k, min_sim` → `list[RetrievedCase]` |
| `LabelVotingService` | `services/label_voting_service.py` | similarity-weighted vote + agreement per label | `list[RetrievedCase]` → `list[VotedLabel]` |
| `ContextBuilder` | `services/context_builder.py` | deterministically organise and partition evidence. **No diagnosis, no synthesis** | cases + votes + answers + notes → `ClinicalContext` |
| `PromptBuilder` | `services/prompt_builder.py` | pure text construction. No LLM calls, no parsing | `ClinicalContext, language` → `str` |
| `LLMOrchestrator` | `services/llm_orchestrator.py` | pure sequencing + two independent retry budgets. **Zero semantic judgment** | `ClinicalContext, language` → `ReportContent` \| raises |
| `StructuralValidator` | `services/structural_validator.py` | shape only — the seven marker fields | `raw str` → `(bool, ReportContent\|None, errors)` |
| `ResponseValidator` | `services/response_validator.py` | semantic warnings. **Advisory, gates nothing** | content + evidence + votes → `SemanticValidationResult` |
| `ReportConsistencyService` | `services/report_consistency_service.py` | does this report contradict itself or its evidence boundary? | content + context + cases + language → `ConsistencyResult` |
| `evidence_disclaimer.render_disclaimer` | `services/evidence_disclaimer.py` | server-authored disclaimer from **both** signals | agreement + support + sims → `str` |
| `ReportFormatter` | `services/report_formatter.py` | attach section headers for the language. **Pure function, never renders PDF/HTML** | content + language + date → `FormattedReport` |
| `ReportGenerationService` | `services/report_generation_service.py` | sequence the whole generation chain and persist | `session_id, language, …` → `GenerationOutcome` |
| `ReportEditService` | `services/report_edit_service.py` | edit / finalize / delete / regenerate, with ownership | ids + updates → `ReportRecord` \| raises |
| `ReportDetailService` | `services/report_detail_service.py` | assemble one report's read model | `report_id` → detail |
| `QuestionnaireService` | `services/questionnaire_service.py` | pick questions for the top voted label | `session_id` → questions |
| `ExplainabilityService` | `services/explainability_service.py` | answer a question about a finished report, on the same evidence | `report_id, question` → answer |
| `ComparisonService` | `services/comparison_service.py` | deterministic facts first, then a narrative | two reports → `ComparisonRecord` |
| `DeterministicComparator` | `services/deterministic_comparator.py` | label-level deltas, no LLM | two contents → `ComparisonFacts` |
| `PatientService` | `services/patient_service.py` | `IPatientRepository` over SQLAlchemy | — |
| `DoctorService` | `services/doctor_service.py` | `IDoctorRepository` + partial self-update | — |
| `AuthService` | `services/auth_service.py` | register / login using the two Protocols | — |
| `UploadAuditService` | `services/upload_audit_service.py` | write one `upload_rejection_log` row | metadata → row |
| `DashboardService` / `SystemStatsService` / `ServiceHealthService` | `services/…` | read models for the three status surfaces | — |
| `session_reconstruction` / `report_reconstruction` | `services/…` | **one** shared reconstruction, not two drifting copies | `session_id` → `(session, cases, votes)` |
| `taxonomy_matching` | `services/taxonomy_matching.py` | word-boundary-safe term matching, shared by validator and comparator | — |

---

## 2. Request lifecycle — `POST /retrieve`

Ten steps in one endpoint. Control passes on at the exact lines named.

| # | step | service | file:line where control passes on |
|---|---|---|---|
| 0 | auth | `get_current_doctor` | `api/dependencies.py:45-74` — reads the `radassist_token` httpOnly cookie, verifies, resolves the `Doctor` |
| 1 | read multipart, **drop the filename** | — | `api/retrieval.py:336-337`. `_declared_extension()` (`:154-168`) is *"the ONLY place in the admission path that touches the uploaded file name, and it keeps nothing but the extension"* — because a filename frequently contains a patient name |
| 2 | **admission A1–A13** | `ImageAdmissionService.admit()` | `api/retrieval.py:341` → `services/image_admission_service.py:147`. Extension allow-list (`:158`), magic-byte sniff (`:167`), signature-vs-extension agreement (`:174`), size bounds (`:181`), `verify()` then a second open for `load()` (`:196`), pixel ceiling (`:203`), dimension bounds (`:213`), **PNG re-encode from the pixel array alone** (`:229`). On failure: audit row written (`:349-356`), then 415/413/422 from the table at `:131-135` |
| 3 | **declared projection A14–A17** | `check_declared_projection()` | `api/retrieval.py:367` → `image_admission_service.py:246`. Absent ⇒ `PROJECTION_NOT_DECLARED` (`:274`); LATERAL ⇒ `LateralProjectionError` (`:304`). **A17: not masked, not embedded, Chroma not queried on this path** (`api/retrieval.py:362-365`) |
| 4 | **PHI masking** | `PHIMasker.detect_and_mask()` | `api/retrieval.py:404`. Writes straight to its permanent home — *"one masked artifact, not two copies that could diverge"* (`:397-400`) |
| 5 | **embedding** | `BiomedCLIPAdapter.embed_image()` | `api/retrieval.py:409`. Embeds the **masked** file, so the vector the gate judges is the vector derived from what the system is willing to store (`:64-72`) |
| 6 | **modality gate M1–M6 — BLOCKS** | `ModalityGateService.gate()` | `api/retrieval.py:413` → `modality_gate_service.py:138`. Below 0.60 ⇒ masked image **unlinked** (`:419`), audit row, 422 |
| 7 | **retrieval** | `RetrievalService.retrieve_by_vector()` | `api/retrieval.py:432` → `retrieval_service.py:38` → `chroma_store.py:36` → `similarity_search.py:20` |
| 8 | **label voting** | `LabelVotingService.vote()` | `api/retrieval.py:433` → `label_voting_service.py:24` |
| 9 | **projection band M7–M12 — BLOCKS** | `check_projection_band()` | `api/retrieval.py:447` → `modality_gate_service.py:195`. Below 0.8500 ⇒ masked image unlinked (`:453`), audit row **carrying the modality score** (`:463`), 422 with reason `FRONTAL_MISMATCH` |
| 10 | **persistence** | — | `api/retrieval.py:471-495`. One `RetrievalSession` + one `RetrievedEvidence` per case, then commit with rollback-and-reraise |

`retrieval_time_ms` is measured from `:406` to `:434` — **the ML pipeline
only**: it excludes the upload I/O before and the DB write after
(`:310-312`).

**The mask-before-embed order is a deliberate change, not incidental.**
`api/retrieval.py:64-72` records that masking used to run *last*, so the vector
came from raw pixels. §3.3/§9 of the frozen v1.1 architecture put mask before
embed. Phase 1 measured the embedding impact of masking at mean cosine
**0.992** (0/50 flagged), which is why the reorder does not disturb retrieval
quality.

---

## 3. Request lifecycle — `POST /generate-report`

| # | step | service | file:line |
|---|---|---|---|
| 0 | auth | `get_current_doctor` | `api/dependencies.py:45` |
| 1 | assemble the service from `app.state` | — | `api/generation.py:101-119` |
| 2 | normalise inputs | — | `report_generation_service.py:139`, `:155` — both defaulted here, not only at the API boundary |
| 3 | **reconstruct the session** | `reconstruct_session_evidence()` | `report_generation_service.py:160` → `session_reconstruction.py:27`. Fetches cases by id, **then restores the real similarities from `retrieved_evidence`** (`session_reconstruction.py:84-91`) |
| 4 | **build context** | `ContextBuilder.build()` | `report_generation_service.py:170` → `context_builder.py:49`. Sort by `(-similarity, source_uid)` (`:59`), collapse near-duplicates (`:60`), partition evidence per label |
| 5 | **build prompt** | `PromptBuilder.build_generation_prompt()` | `llm_orchestrator.py:57` → `prompt_builder.py:168`. Nine sections in a fixed order (`:169-205`) |
| 6 | **LLM call** | `OllamaClient.complete()` | `llm_orchestrator.py:107` → `ollama_client.py:51`. `POST /api/generate`, non-streaming |
| 7 | **structural validation + content retry** | `StructuralValidator.validate()` | `llm_orchestrator.py:62` → `structural_validator.py:46`. Loop at `llm_orchestrator.py:61-75` |
| 8 | **semantic validation (advisory)** | `ResponseValidator.validate_semantic()` | `report_generation_service.py:182` → `response_validator.py:40` |
| 9 | **consistency check** | `ReportConsistencyService.check()` | `report_generation_service.py:200` → `_run_consistency_check()` at `:357` → `report_consistency_service.py:292` |
| 10 | **support signal** | `classify_retrieval_support()` | `report_generation_service.py:224`. Top-1 read from `retrieved_evidence` by rank (`:447-469`), **never** off the reconstructed cases |
| 11 | **server-authored disclaimer** | `render_disclaimer()` | `report_generation_service.py:242-249` → `evidence_disclaimer.py`. **Replaces the model's disclaimer text** |
| 12 | **formatting** | `ReportFormatter.format()` | `report_generation_service.py:255` → `report_formatter.py:58` |
| 13 | **persistence** | — | `report_generation_service.py:276-323`. One `ReportRecord`, commit with rollback-and-reraise |
| 14 | response | `_build_response` | `api/generation.py:142-151` |

### 3.1 Three ordering decisions that are load-bearing

**(a) The consistency check sits after `validate_semantic()` and before
`render_disclaimer()`** — `report_generation_service.py:186-193`. After the
validator so the validator's subject stays "the model's clinical claims
against retrieved evidence" and it is never handed post-processed text; before
the disclaimer so the disclaimer is rendered from the same content the check
just judged.

**(b) The disclaimer is rendered after semantic validation on purpose** —
`:237-241`: handing the validator a server-authored string *"would be
validating this system's own template output as though it were generated
content."*

**(c) `report_date` is generated in the service, not the formatter** — `:251-253`,
so `ReportFormatter` stays a pure deterministic function (Phase 8 Decision 4).

### 3.2 The disclaimer must read both signals

`report_generation_service.py:228-235` records the failure this prevents: a
model-authored disclaimer read only agreement — the real sample *"Clinical
uncertainty due to low agreement score (0.60)"* — while retrieval support is an
independent signal that can disagree with it. `modality_gate_service.py:170-178`
spells out how: *"five cases all below the floor can carry the same label,
making agreement high while support is low."*

### 3.3 `ai_draft_content` and `final_content` are two independent dicts

`report_generation_service.py:257-263`: `asdict(content)` is called **twice**,
deliberately, *"not once with the result assigned to both fields — each call
builds a genuinely independent dict, so there is no shared-reference risk."*
`PATCH /reports/{id}` is the only thing that ever touches `final_content`.

---

## 4. Every threshold and config value that affects behaviour

All in `backend/app/core/config.py` unless stated. **"How chosen" is stated for
each: pre-registered, calibrated, post-hoc revised, or a plain engineering
default.**

### 4.1 Gate thresholds

| name | value | line | how chosen |
|---|---|---|---|
| `MODALITY_THRESHOLD` | **0.60** | `:350` | **Calibrated** (Gate B, v1.1 §11.3). Frontal false-negative rate **0.0000** at n=300; 0.82 was considered and declined. Source: `ml/outputs/calibration/v1_1_gate_b_selected_values.csv` |
| `PROJECTION_REJECT_THRESHOLD` | **0.8500** | `:404` | **POST-HOC REVISED — and must be presented as such.** See §4.2 |
| `RETRIEVAL_FLOOR` | **0.8906208872795105** | `:435` | **Calibrated, rule fixed before the value was computed** (§11.5 Step R1): the 0th percentile of the frontal calibration set (n=300). Step R2, reported as a result: **0 of 300 fall below it — the low-support mechanism is unexercised** (`:428-430`) |
| `MODALITY_SOFTMAX_TEMPERATURE` | `1 / 85.2322769165039` | `:344` | Not chosen at all — it is **BiomedCLIP's own learned logit scale** |
| `DISCLAIMER_AGREEMENT_THRESHOLD` | **0.5** | `:445` | Stated, not calibrated: *"a majority of retrieved neighbour cases agree on this label."* Deliberately the same number as `ResponseValidator.TOP_LABEL_AGREEMENT_THRESHOLD` (`response_validator.py:29`) but declared separately because *"they answer different questions … and nothing requires them to move together"* (`config.py:437-444`) |

### 4.2 The projection threshold revision — post-hoc, and recorded as such

`config.py:364-403` is the primary source and says so in its own words:

> **"THIS RULE WAS CHANGED AFTER SEEING A FAILING IMAGE, AND THAT IS RECORDED
> HERE RATHER THAN PRESENTED AS A PRE-REGISTERED CHOICE."**

- **Old rule:** midpoint of the observed separation gap → **0.8695459067821503**
  (lateral max 0.84847092628479, frontal min 0.8906208872795105, gap 0.0421).
- **New rule (revised 2026-08-19):** *just above the observed lateral maximum*
  → **0.8500**.
- **What forced it:** a genuine frontal chest radiograph from outside the IU
  dataset scored top-1 **0.8582** and was rejected as a projection mismatch. It
  sits **above every lateral** in the calibration set and **below** the old
  midpoint — inside the empty gap the midpoint rule had placed the boundary in
  the middle of.
- **Why the change is defensible rather than merely convenient** (`:381-391`):
  the calibration population was IU-only, `RETRIEVAL_FLOOR`'s own §11.5 R3 note
  already said this gate's real purpose is *detecting a distribution shift at
  deployment time*, and no observation of any kind lies between 0.84847 and
  0.89062 — so moving the boundary to the edge of what was observed **removes
  an unmeasured margin rather than adding one**.
- **Re-verified on the same 600-study set** (`:393-397`): **300/300 lateral
  still rejected, 0/300 frontal rejected.**
- **The caveat that survives** (`:399-403`): this is an **observed separation
  point, not a validated frontal/lateral boundary** — 300 images of each
  projection from one dataset, not a universal cosine boundary.

The calibration CSV still records 0.8695; **the config value 0.8500
supersedes it**, and both numbers must appear in the thesis.

### 4.3 LLM settings

| name | value | line | how chosen |
|---|---|---|---|
| `OLLAMA_MODEL` | `llama3:8b` | `:51` | Engineering choice; **re-tested in Phase 23** against `qwen2.5:14b` and **retained** |
| `LLM_TEMPERATURE` | **0.0** | `:55` | Determinism attempt |
| `LLM_SEED` | **42** | `:70` | **Measured necessity.** `ollama_client.py:9-13`: a QA report of *"the same image yields different results"* was reproduced at this layer — temperature 0.0 with Ollama's default random seed produced **two different reports from five identical requests**. Both settings are needed |
| `OLLAMA_KEEP_ALIVE` | `30m` | `:94` | *"A cold model produces different (though itself reproducible) wording than a warm one"* (`ollama_client.py:59-61`) |
| `OLLAMA_TIMEOUT_SECONDS` | 120 | `:52` | default |
| `LLM_CONTENT_RETRY_COUNT` | **2** | `:53` | Phase 7 frozen architecture |
| `LLM_TRANSPORT_RETRY_COUNT` | **1** | `:54` | Phase 7 frozen architecture |
| `num_ctx` | **4096** | **not set in this codebase** | **Correction to `thesis_facts.md` §1.1**, which attributes it to `config.py`. `ollama_client.py:66` sends only `{"temperature", "seed"}`; a repo-wide grep for `num_ctx` finds no occurrence in `backend/`. 4096 is **Ollama's own default**, and `gate_a_run_plan.md:30` says so explicitly: *"the harness sets no `num_ctx`, matching Phase 21"* |

### 4.4 Upload and image bounds

| name | value | line |
|---|---|---|
| `UPLOAD_ALLOWED_EXTENSIONS` | `png,jpg,jpeg` | `:140` |
| `UPLOAD_MAX_BYTES` | 20 MB | `:141` |
| `UPLOAD_MIN_BYTES` | 20 kB | `:142` |
| `IMAGE_MIN_DIMENSION_PX` | 256 | `:143` |
| `IMAGE_MAX_DIMENSION_PX` | 8192 | `:144` |
| `IMAGE_MAX_PIXELS` | 80,000,000 | `:145` |
| `PHI_MASK_MAX_REGION_AREA_FRACTION` | **0.08** | `:325` |
| `ACCEPTED_PROJECTIONS` | `PA,AP` | `:358` |
| `DECLARED_PROJECTION_VALUES` | `PA,AP,LATERAL` | `:359` |

`LATERAL` is declarable but not accepted **on purpose** (`main.py:138-140`), so
declaring it is a distinct, separately-coded rejection rather than an
unrecognised value.

### 4.5 CheXbert and consistency

| name | value | line | note |
|---|---|---|---|
| `CHEXBERT_CHECKPOINT_PATH` | absolute path into the HF cache | `:196` | **Outside the repository by design** — Stanford Docket S20-295 forbids redistribution |
| `CHEXBERT_DEVICE` | `auto` | `:206` | Pin to `cpu` to reproduce the frozen evaluation arithmetic exactly; the adapter disables TF32 on CUDA so pinning is not required for label equivalence |
| `CHEXBERT_MAX_LENGTH` | 512 | `:213` | BERT's positional limit. **The longest of all 954 real Arm C sections is 298 tokens**, so this bound is never exercised |
| `CHEXBERT_BATCH_SIZE` | 16 | `:218` | — |
| `CONSISTENCY_TEMPORAL_TERMS` | 5 frozen terms | `:244` | **The same list the prompt forbids** (`main.py:178-182`) — a prompt banning different words from the ones the checker looks for would make the measured rate a statement about two unrelated vocabularies |
| `CONSISTENCY_RETRY_COUNT` | 1 | `:273` | **Read by no service.** The only two occurrences in `backend/` are its declaration (`:273`) and its field (`:493`). See §6.4 |
| transplant thresholds | **not passed at all** | `main.py:233-241` | Gate B's to calibrate; *"passing a number now would be inventing one"* |
| `PROMPT_LABEL_CHECKLIST_ENABLED` | **False** | `:301` | Phase 23's lever, **tested and not adopted**. With the flag off the prompt is byte-identical to v1.2's (`prompt_builder.py:186-189`) |

### 4.6 Everything else

| name | value | line |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/dev.db` | `:40` |
| `CHROMA_PERSIST_PATH` | `ml/outputs/retrieval/chroma_db` | `:29` — **and it is ignored; see §6.6** |
| `CHROMA_COLLECTION_NAME` | `iu_cxr_biomedclip_v1_train` | `:31` |
| `EVIDENCE_MODE` | `FULL` | `:102` — Arm C, the production arm |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | `:108` |
| `JWT_SECRET_KEY` | `dev-only-insecure-secret-do-not-use-in-production` | `:122` — **see §8.1** |
| `JWT_ALGORITHM` | HS256 | `:123` |
| `JWT_EXPIRATION_MINUTES` | 1440 (24 h) | `:124` |

Every path is anchored to the **file's own location**, never the process CWD
(`config.py:22-26`), after a real incident: a stray `cd backend` produced an
empty `backend/ml/outputs/retrieval/chroma_db` instead of erroring
(`chroma_store.py:20-23`).

---

## 5. The data model

SQLite. **Nine tables.** ORM under `backend/app/models/`, migrations under
`backend/alembic/versions/`.

### 5.1 Tables and key columns

| table | model | key columns | notes |
|---|---|---|---|
| `doctors` | `doctor.py:30` | `id` PK, `email` UNIQUE+indexed, `password_hash`, `full_name`, `created_at`, `bmdc_number?`, `default_top_k?`, `default_language?`, `default_questionnaire_skip?`, `default_rail_state?`, `default_export_format?` | **No role column** — there is no RBAC |
| `patients` | `patient.py:28` | `id` PK, `patient_code` UNIQUE, `name`, `date_of_birth`, `gender`, `created_at` | **No `doctor_id`** — patients are institutional, not owned (`entities.py:60-65`) |
| `retrieval_sessions` | `retrieval_session.py:38` | `id` PK, `query_image_path`, `top_k`, `min_similarity`, `num_results`, `retrieval_time_ms`, `created_at`, `patient_id?`→`patients`, `doctor_id?`→`doctors` | `query_image_path` points at the **masked** file |
| `retrieved_evidence` | `retrieved_evidence.py:22` | `id` PK, `session_id`→`retrieval_sessions`, `study_uid`, `rank`, `similarity` | **The only place the real ranked similarity survives** |
| `reports` | `report.py:56` | `id` PK, `session_id`→`retrieval_sessions`, `language`, `status`, `ai_draft_content` JSON, `final_content` JSON, `validation_warnings` JSON, `report_date`, `llm_model`, `llm_temperature`, `embedding_model`, `embedding_version`, `collection_name`, `created_at`, `updated_at`, `finalized_at?`, `finalized_by?`→`doctors`, `questionnaire_answers?` JSON, `clinical_notes?`, `retrieval_support?`, `top1_similarity?`, `voted_labels?` JSON, `agreement?`, `consistency_violations?` JSON, `consistency_checks_run?` JSON, `consistency_retry_count?` | 26 columns |
| `comparisons` | `comparison.py:43` | `id` PK, `patient_id`→`patients`, `previous_report_id`→`reports`, `current_report_id`→`reports`, `deterministic_facts` JSON, `llm_narrative`, `created_at`, `doctor_id?` | Two FKs to one table — `comparison.py:10` records the explicit disambiguation this needed |
| `explanations` | `explanation.py:38` | `id` PK, `report_id`→`reports`, `question`, `answer`, `created_at`, `doctor_id?` | |
| `report_audit_log` | `report_audit_log.py:37` | `id` PK, `report_id`→`reports`, `doctor_id`→`doctors`, `action`, `at` | **Report EDIT actions only** |
| `upload_rejection_log` | `upload_rejection.py:48` | `id` PK, `at`, `doctor_id`→`doctors`, `reason_code`, `stage`, `modality_score?`, `raw_sha256` indexed, `file_size_bytes`, `declared_extension` | **Metadata only — the filename is never stored** |

### 5.2 Relationships

```
doctors ──< retrieval_sessions ──< retrieved_evidence
   │              │
   │              └──< reports ──< explanations
   │                      │  └──< report_audit_log
   │                      └──< comparisons (previous_report_id, current_report_id)
   ├──< upload_rejection_log
patients ──< retrieval_sessions
patients ──< comparisons
```

`doctor_id` is **nullable on every work table** — every one of those columns
was added by a later migration to tables that already held rows, and no
backfill was performed.

### 5.3 Migration chain — which migration added what

Linear, 15 revisions, head `7f2a91c4d6e8`.

| # | revision | what it added |
|---|---|---|
| 1 | `e60f9520da7b` | create `retrieval_sessions` + `retrieved_evidence` |
| 2 | `e8d3a5a73568` | create `reports` |
| 3 | `719b6078d895` | create `explanations` |
| 4 | `96e0dd80c317` | create `patients`, add `retrieval_sessions.patient_id` |
| 5 | `fc0fc7f35ef5` | create `comparisons` |
| 6 | `8550fea2771a` | create `doctors` |
| 7 | `11971c2c9396` | add `retrieval_sessions.doctor_id` |
| 8 | `689ad1cf33f4` | add `comparisons.doctor_id` |
| 9 | `93de8accdb66` | add `explanations.doctor_id` |
| 10 | `4da4e9df3c23` | add `bmdc_number` + the five `default_*` workspace columns to `doctors` |
| 11 | `d8ff7f78ff6a` | add finalize/edit columns to `reports` (`finalized_at`, `finalized_by`, …) |
| 12 | `528c741665ee` | add `questionnaire_answers` + `clinical_notes` to `reports` |
| 13 | `a1f4c72b9e30` | add `retrieval_support` + `top1_similarity` to `reports`; create `upload_rejection_log` |
| 14 | `c3d81b6a4f27` | add `voted_labels` + `agreement` to `reports` (**decision D4**) |
| 15 | `7f2a91c4d6e8` | **Phase 22 v1.2** — add `consistency_violations`, `consistency_checks_run`, `consistency_retry_count`, all nullable |

**`report_audit_log` has no migration of its own.** It is defined in
`models/report_audit_log.py` but does not appear as a `create_table` in any of
the 15 revisions — how the live table came to exist is **NOT RECORDED**.

### 5.4 NULL and `[]` are different states, on purpose

Migration 15 and `report_generation_service.py:369-390` encode a three-way
distinction that a single nullable column would lose:

| state | `violations` | `checks_run` | means |
|---|---|---|---|
| checks ran (English) | `[...]` (possibly empty) | `[...]` | examined; an empty list means examined and clean |
| zero checks (non-English) | **NULL** | `[]` | *"we know zero checks were applicable"* — writing `[]` for violations here *"would assert the report was examined and found clean, which is exactly the false assurance frozen §3.4/§8.8 forbids for Bengali reports"* |
| checker raised | NULL | NULL | nothing is known and nothing is claimed |

---

## 6. Error handling, retries, and what happens when a component is down

### 6.1 Two independent retry budgets

`llm_orchestrator.py:11-25`. They do not interact.

- **Transport retry** (`LLM_TRANSPORT_RETRY_COUNT = 1`): owned by
  `generate_freeform()` (`:86-110`). Retries the **same prompt** on
  `LLMTransportError`, then raises. **Every** real LLM call goes through it —
  the initial call, every content retry's call, `answer_question()`, and
  section regeneration — so *each invocation gets its own fresh budget*.
- **Content retry** (`LLM_CONTENT_RETRY_COUNT = 2`): the loop at `:61-75`. On a
  structural failure it builds a **correction prompt** (`prompt_builder.py:208`)
  carrying the rejected response and the specific errors, and calls again. On
  exhaustion it raises `LLMGenerationValidationError` carrying the last raw
  response and the last error list — so the 422 body shows *what* went wrong,
  not a bare status (`api/generation.py:20-25`, `:132-140`).

`build_generation_prompt` is called **exactly once**, structurally guaranteed
by having exactly one call site at the top of `generate_draft()`
(`llm_orchestrator.py:27-30`).

### 6.2 **D5 — what is NOT recorded**

**The number of structural attempts is never persisted.** There is no
`structural_attempt_count` column on `reports` and no counter written anywhere;
`llm_orchestrator.py` keeps `attempt` as a loop variable and discards it.

Consequence, from `docs/decisions/decision_log.md`: **D5 is OPEN and it blocks
D3** — the marker-format failure rate cannot be reported per attempt, only as a
final success or failure. What *is* recorded is the final outcome: Gate A ran
**477/477 completed, 0 failed**, and Phase 23 ran **600/600 completed, 0
failed**, but neither can say how many of those needed a retry.

By contrast `consistency_retry_count` **is** persisted, and is always `0`
because Gate C does not exist: *"Gate A performs no retry, so 0 is a fact about
this run, not a placeholder"* (`report_generation_service.py:389-390`).

### 6.3 Component unavailable

| component | behaviour | evidence |
|---|---|---|
| **CheXbert missing** | **Startup does not fail.** `main.py:214-231` catches `ChexbertUnavailableError` and logs a **warning**, not an error, because *"running without it is a supported configuration"*. The contradiction check is dropped, the other two still run, and `checks_run` omits `"contradiction"` — *"the gap is recorded rather than hidden"*. `main.py:207-212`: *"Refusing to boot would take out report generation entirely to protect a warning."* |
| **Consistency checker raises** | **Generation never fails because of it.** `_run_consistency_check()` has **no raising path** (`report_generation_service.py:362-367`): *"A self-consistency warning is a safety improvement, and a safety improvement that can take down report generation is a net loss — the doctor loses the report entirely instead of receiving one with an unchecked caveat."* Worst case is three NULLs and a logged exception (`:408-418`). The `except Exception` is **deliberately broad** and says so |
| **Ollama down / timing out / non-2xx** | Every `httpx.HTTPError` subclass becomes `LLMTransportError` (`ollama_client.py:71-72`) → transport retry → **HTTP 502**. 502 not 503 because *"this server itself is healthy"* (`api/generation.py:14-19`) |
| **ChromaDB missing collection** | `ChromaVectorStore.__init__` calls `get_collection()` (`chroma_store.py:38`), which raises at **startup**. There is no catch — the app will not boot without the collection. No graceful-degradation path exists |
| **A uid missing from the collection** | Silently dropped from `get_by_ids()` output, deliberately, with the consequence documented: *"the returned list can be SHORTER than `uids`"* (`chroma_store.py:73-82`) |
| **DB commit failure** | Rollback then re-raise, at both write sites (`api/retrieval.py:491-495`; `report_generation_service.py:319-323`) |

### 6.4 What a recorded violation causes: **nothing**

`CONSISTENCY_RETRY_COUNT = 1` exists at `config.py:273` and is exposed as a
setting at `:493`. Those are the **only two occurrences in the entire
backend** — no service reads it. Gate A recorded **17/477 violations** and
every one of them was acted on by nothing.

### 6.5 Exception → HTTP status

| exception | status | where |
|---|---|---|
| `UnsupportedImageFormatError` | 415 | `api/retrieval.py:132` |
| `ImageTooLargeError` | 413 | `:133` |
| `InvalidImageError` | 422 | `:134` |
| `LateralProjectionError` / `ProjectionMismatchError` | 422, **i18n key + reason code, never English text** | `:138-151`, `:378`, `:469` |
| `NotAChestRadiographError` | 422 | `:429` |
| `SessionNotFoundError` | 404 | `api/generation.py:128` |
| `LLMTransportError` | 502 | `:130` |
| `LLMGenerationValidationError` | 422 + last raw response + errors | `:132-140` |
| `ForbiddenError` | 403 | `api/reports.py:307` |
| `ReportAlreadyFinalizedError` | 409 | `:309` |
| `InvalidTokenError` / no cookie | 401 | `api/dependencies.py:57`, `:62` |
| malformed `patient_id` | 400 | `api/retrieval.py:324` |

The status mapping is written as a **table** rather than a chain of `except`
clauses *"because §10 defines the exception-type → status mapping as the API
layer's single responsibility, and a table makes a missing or duplicated
mapping visible at a glance"* (`api/retrieval.py:127-130`).

### 6.6 A recorded defect in this layer

`ChromaVectorStore.__init__` takes `persist_path` with a **module-level
default** (`chroma_store.py:29-32`), and `main.py:110` constructs it as
`ChromaVectorStore()` with **no argument** — so `settings.CHROMA_PERSIST_PATH`
is declared, documented, and **never read**. Recorded as defect 6 in
`thesis_facts.md` §5. The two values happen to be identical today
(`config.py:28`: *"Matches chroma_store.py's DEFAULT_PERSIST_PATH exactly"*),
so nothing is broken — but the setting is not the thing in control.

---

## 7. Concurrency, caching and session reuse

**Concurrency model.** Routes are **synchronous `def`**, so FastAPI runs each
in its threadpool; only `lifespan` is async. There is no task queue, no
background worker, no `async` DB driver.

| thing | recomputed? | evidence |
|---|---|---|
| BiomedCLIP model | **Never** — loaded once in lifespan | `main.py:108-109`, with a log line asserting *"should log exactly once per app lifetime"* |
| EasyOCR model | **Never** | `main.py:113-119` |
| CheXbert checkpoint | **Never** | `main.py:215-223`; loading per request *"would dominate the ~9 ms the check itself costs"* (`:203-205`) |
| Modality gate prompt vectors | **Never** — encoded inside the constructor, in lifespan. **M6's cache requirement *is* that line** | `main.py:144-147` |
| Ollama model residency | Held by `keep_alive=30m` **on the Ollama side** | `ollama_client.py:62` |
| ChromaDB client | One persistent client | `main.py:110` |
| Query embedding | **Computed once per upload and reused** — the gate must not re-encode (M1), so the route embeds explicitly then calls `retrieve_by_vector()` | `api/retrieval.py:74-77`, `:409`, `:413` |
| Retrieved case **text** | **Re-fetched** at generation time by id from ChromaDB — `retrieved_evidence` stores only uid/rank/similarity | `session_reconstruction.py:83-91` |
| Retrieved case **similarity** | **Not recomputed** — restored from `retrieved_evidence`, because `get_by_ids()` reports a sentinel 1.0 | `session_reconstruction.py:63-91` |
| Label votes | **Re-voted** at generation time from the reconstructed cases… | `session_reconstruction.py:92` |
| …but then **stored, not re-voted again** | `voted_labels` and `agreement` are written from the *same* list the method built the context from, validated against and rendered the disclaimer from | `report_generation_service.py:298-310` (**decision D4**) |
| `retrieval_support` + `top1_similarity` | **Stored with the report at generation time**, not re-derived later | `report_generation_service.py:292-297` |
| Report read | **Fetched once per workspace visit**; the Next.js segment layout holds it, so Report ⇄ Evidence fires no request | `frontend/src/app/workspace/[reportId]/layout.tsx:19-30` |

**The sentinel-similarity bug, and why it matters architecturally.**
`get_by_ids()` is an id fetch with no ranking, so it forces distance 0.0 →
similarity 1.0 for every case (`chroma_store.py:57-64`). Three downstream
consumers treated that as a measurement:
vote weights collapsed to the plain case count (3 cases → "3.00", printed into
the prompt), `ContextBuilder`'s `(-similarity, source_uid)` sort degenerated to
alphabetical uid order, and the UI showed 100.0% on every case
(`session_reconstruction.py:63-79`). The real numbers were never lost — they
were in `retrieved_evidence` all along, read for their `study_uid` and then
discarded. The restore is keyed **by uid, not zipped positionally**, because
`get_by_ids()` can return fewer results than asked for.

**A named reproducibility limitation.** `RetrievalSession` does not persist
`collection_name` / `embedding_model` / `embedding_version` per session, so
`ReportGenerationService` sources them from `Settings` — *the current config,
not necessarily what was true at retrieval time*. If the config changes
between a session's retrieval and its later generation, the persisted
reproducibility metadata reflects the **later** config
(`report_generation_service.py:20-30`).

---

## 8. Security: what is enforced, and what is not

### 8.1 Authentication

- **Argon2id** via `argon2-cffi`'s high-level `PasswordHasher`
  (`infrastructure/password_hasher.py`). Salt generation and storage live
  **inside the encoded hash string**, so `doctors` needs no salt column.
- **JWT, HS256**, `sub` = doctor id, `exp` from `JWT_EXPIRATION_MINUTES`
  (`infrastructure/jwt_handler.py:26-33`). Every PyJWT failure mode — expired,
  tampered, malformed — is caught under the single base `jwt.PyJWTError` and
  re-raised as this project's own `InvalidTokenError`, so callers depend on
  this project's exception type and the token library stays swappable.
- **httpOnly cookie, not an `Authorization` header**
  (`api/dependencies.py:10-13`), *"so the token is inaccessible to frontend JS,
  mitigating XSS token theft."* Cookie name `radassist_token`.
- **Every protected route resolves the real `Doctor`**, not just a claim: a
  validly-signed token for a deleted doctor is a 401
  (`api/dependencies.py:70-72`).

**Not enforced — and it must be stated plainly:** `JWT_SECRET_KEY` defaults to
the literal string `"dev-only-insecure-secret-do-not-use-in-production"`
(`config.py:122`). It is overridable by env/`.env`, but **no deployment
configuration in this repository sets it**. Every measurement in this project
was taken under that default.

### 8.2 Authorization

**Ownership only. There are no roles.** The rule is four lines
(`report_edit_service.py:101-104`):

```python
def _check_ownership(owner_doctor_id, current_doctor_id) -> None:
    if owner_doctor_id is None or str(owner_doctor_id) != current_doctor_id:
        raise ForbiddenError("current doctor does not own this report")
```

`owner_doctor_id is None` fails closed — a pre-auth report with a NULL
`doctor_id` is owned by nobody and editable by nobody. Edit, finalize, delete
and regenerate all call the same function, so *"a non-owner is refused
[deletion] exactly as they are refused an edit"* (`api/reports.py:296-298`).
A finalized report is refused **409**, ownership or not.

**Reading is not ownership-gated** — any authenticated doctor may read any
report; the UI shows an owner chip and hides the edit controls
(Phase 15). Patients are institutional and are readable by any authenticated
doctor by design (`entities.py:60-65`).

### 8.3 Upload validation — what is actually enforced

A1–A17 in `image_admission_service.py`, all before anything expensive runs:

1. **A1** extension allow-list (`:158`) — an absent or extension-less name
   yields `""`, which is not in the list and is therefore rejected, *"the
   correct outcome, since A3 forbids inferring the format from the name
   anyway"* (`api/retrieval.py:163-166`).
2. **A2/A3** magic-byte sniff of the leading bytes (`:167`, `:312`).
3. **A4** the signature must **agree** with the extension (`:174`).
4. **A5/A6** size bounds (`:181`).
5. **A7/A8** `verify()`, then a **second open** for `load()` (`:196`, `:326`,
   `:361`) — Pillow's documented requirement, and a decompression-bomb guard.
6. **A9** pixel ceiling, checked at three separate points (`:203`, `:349`, `:378`).
7. **A10/A11** dimension bounds (`:213`).
8. **A12 re-encode from the pixel array alone** (`:229`, `:405`) — the strongest
   control here. Whatever was uploaded, what goes forward is a PNG this process
   encoded: **no EXIF, no trailing bytes, no polyglot payload**.
9. **A13** the raw bytes never reach disk (`api/retrieval.py:79-82`). Only the
   normalized PNG is written to a temp path, and only its **masked** form
   survives the request.
10. **A14–A17** declared projection, checked before masking and embedding.

**PHI protection is structural, not by convention.** The filename is read
exactly once, for its extension (`api/retrieval.py:154-168`), so nothing
downstream — not the audit row, not any error message, not the gate — can leak
a patient name that arrived in a filename like `Abdur_Rahman_CXR_2026.jpg`.
Rejection messages carry an **i18n key and a reason code, never English prose**
(`:138-151`), so the two languages cannot drift apart through a hardcoded
default. For a rejected upload **both** copies of the image are destroyed — the
masked file is explicitly unlinked before the 422 returns (`:419`, `:453`).

### 8.4 What is **not** enforced

| gap | evidence |
|---|---|
| **No roles or RBAC** | no role column exists on `doctors` |
| **No rate limiting** anywhere | no middleware beyond CORS in `main.py:252-258` |
| **Default JWT secret** unset in every recorded run | `config.py:122` |
| **CORS allows credentials from a single hardcoded-by-default origin** | `main.py:252-258`; local dev only, by explicit scope decision |
| **No HTTPS anywhere**; the auth cookie is set `secure=False` in the harness | `e2e/ui-shots.mjs` cookie install |
| **No general audit trail** — no login, read or export events | only `report_audit_log` (EDIT) and `upload_rejection_log` exist |
| **Query images are stored in the repository** under `backend/uploaded_images/`; whether that is compatible with the IU dataset's terms | **NOT RECORDED** (`thesis_facts.md` §6.3) |
| **No `LICENSE` file for this project** | **NOT RECORDED** |

---

## 9. Every API endpoint

Generated from the **live `/openapi.json`** of a running instance (port 8011),
2026-09-23. **26 operations.** Every route except `GET /health` requires the
`radassist_token` cookie.

| method | path | purpose | request | success response |
|---|---|---|---|---|
| GET | `/health` | Four-service reachability: FastAPI, Ollama, ChromaDB, GPU. **Public** | — | 200 `HealthResponse` `{status, fastapi, ollama, chromadb, gpu}` |
| POST | `/retrieve` | Admit → mask → embed → gate → retrieve → vote. Creates the session | multipart `{file*, top_k=5, min_similarity=0.0, patient_id?, declared_projection?}` | 200 `RetrieveResponse` `{session_id, retrieval_time_ms, embedding_model, embedding_version, collection_name, retrieved_cases[], voted_labels[], modality_score, retrieval_support, top1_similarity}` |
| GET | `/retrieval-sessions/{session_id}/image` | Serve the **masked** query image of a past session | — | 200 image file |
| POST | `/generate-report` | The whole generation chain; persists the report | `{session_id*, language="en", questionnaire_answers?, clinical_notes=""}` | 200 `GenerateReportResponse` `{report_id, session_id, formatted_report, validation, generation_metadata, consistency}` |
| GET | `/questionnaire/{session_id}` | Questions conditioned on the top voted label | — | 200 `QuestionnaireResponse` `{session_id, based_on_label, questions[]}` |
| GET | `/reports` | The signed-in doctor's report list | — | 200 `ReportListItemResponse[]` |
| GET | `/reports/{report_id}` | One report in full | — | 200 `ReportDetailResponse` |
| PATCH | `/reports/{report_id}` | Edit `final_content`. **Owner only**, refused once FINAL | `{clinical_history?, technique?, findings?, impression?, recommendation?}` | 200 `ReportDetailResponse` |
| DELETE | `/reports/{report_id}` | Delete. Owner only; 409 once FINAL | — | **204**, no body |
| PATCH | `/reports/{report_id}/finalize` | DOCTOR_EDITED → FINAL, stamps `finalized_at`/`finalized_by` | — | 200 `ReportDetailResponse` |
| POST | `/reports/{report_id}/regenerate-section` | Regenerate one of the five editable fields as a candidate | `{field*}` | 200 `RegenerateSectionResponse` |
| POST | `/reports/{report_id}/explain` | Answer a question grounded on the same evidence block | `{question*}` | 200 `ExplanationResponse` |
| POST | `/comparisons` | Deterministic facts + narrative against a prior report | `{patient_id*, current_report_id*, compare_against_report_id?}` | 200 `ComparisonResponse` |
| POST | `/patients` | Register a patient; the system assigns the code | `{name*, date_of_birth*, gender*}` | 200 `PatientResponse` |
| GET | `/patients` | All patients, registration order | — | 200 `PatientResponse[]` |
| GET | `/patients/search` | Search by name or patient code | query params | 200 `PatientResponse[]` |
| GET | `/patients/{patient_id}` | One patient | — | 200 `PatientResponse` |
| GET | `/patients/{patient_id}/history` | That patient's reports, chronological | — | 200 `PatientHistoryReportResponse[]` |
| POST | `/auth/register` | Create a doctor | `{email*, password*, full_name*}` | 200 `RegisterResponse` |
| POST | `/auth/login` | Issue the JWT cookie | `{email*, password*}` | 200 `LoginResponse` + `Set-Cookie` |
| POST | `/auth/logout` | Clear the cookie | — | 200 `LogoutResponse` |
| GET | `/auth/me` | The signed-in doctor, **self-scoped fields included** | — | 200 `DoctorResponse` |
| PATCH | `/auth/me` | Partial self-update; **omitted ≠ null** | `{full_name?, bmdc_number?, default_top_k?, default_language?, default_questionnaire_skip?, default_rail_state?, default_export_format?}` | 200 `DoctorResponse` |
| GET | `/doctors/{doctor_id}` | Another doctor, **public fields only** | — | 200 `DoctorPublicResponse` |
| GET | `/dashboard/stats` | Queue counts | — | 200 `DashboardStatsResponse` `{my_reports, total_reports, my_patients, total_patients, examinations_today, awaiting_review, oldest_awaiting_review_report_id?, oldest_awaiting_review_report_date?}` |
| GET | `/system/stats` | Index size read from ChromaDB itself | — | 200 `SystemStatsResponse` `{masked_images_stored, original_images_stored, index_size, embedding_model, embedding_version, collection_name, evidence_mode}` |

`* = required.`

**Two response shapes are separate on purpose.** `DoctorResponse` carries
`bmdc_number` and the five `default_*` fields; `DoctorPublicResponse` does
not — *"they must never be added to `DoctorPublicResponse`, only to the
self-scoped `DoctorResponse`"* (`entities.py:68-74`), the same reasoning that
already kept `email` and `created_at` out of the public shape.

**`ConsistencyResponse`** `{status, checks_run, applicable_checks, violations,
retry_count}` is embedded in `GenerateReportResponse` and in the report detail.
`status` is derived from the stored values, never recomputed independently, so
`POST /generate-report` and a later `GET /reports/{id}` cannot describe the same
report differently (`report_generation_service.py:342-348`).
`applicable_checks` is a function of **language alone**, never of service
configuration — otherwise *"a report checked by a degraded deployment would
compute applicable == checks_run and report 'clean'"*
(`report_consistency_service.py:79-88`).
