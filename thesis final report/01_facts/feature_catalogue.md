# feature_catalogue.md — every user-facing feature, with evidence

> **Status vocabulary.** *implemented* = a real route and a real page exist and
> the feature works end to end. *partial* = it exists but a stated part of it
> does not. *not implemented* = it does not exist in this repository, with the
> reason given.
>
> Evidence is a file, and a line number where the line is what proves the
> claim. Read at commit `99f3eab8`, 2026-09-23.

**One correction to [`thesis_facts.md`](thesis_facts.md), which is dated
2026-09-22.** Its §5 defect 1 says the consistency verdict is "stored and
returned but **rendered by no UI**". That was true when it was written and is
**no longer true**: `frontend/src/components/report/consistency-state.tsx`
renders all four states, and it is exercised by
`consistency-state.test.tsx`. The change landed on 2026-09-23 in commits
`b526e122` / `f2cdfd67`. Every other defect in that list still stands.

---

## 1. Authentication and account

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| Registration | Create a doctor account with email, password, full name, and an optional BMDC number. | `/register` → `POST /auth/register` | implemented | `frontend/src/app/register/page.tsx`; `backend/app/api/auth.py:90` |
| Login | Email + password, returns a JWT in an httpOnly cookie. | `/login` → `POST /auth/login` | implemented | `backend/app/api/auth.py:108`; `backend/app/api/dependencies.py:33` |
| Logout | Clears the auth cookie. | `POST /auth/logout` | implemented | `backend/app/api/auth.py:126` |
| Session identity | Reads the current doctor from the cookie on every protected route. | `GET /auth/me` | implemented | `backend/app/api/auth.py:140` |
| Password storage | Argon2id via `argon2-cffi`; salt lives inside the encoded hash, so no salt column. | — | implemented | `backend/app/infrastructure/password_hasher.py` |
| **BMDC verification** | The number is stored and printed on the report, but is **never checked against any registry**. | `/register`, `/settings` | **not implemented** | `backend/app/domain/entities.py:73-74`: *"this system has no access to any real BMDC registry to verify it against, and the UI must say so, not imply verification"* |
| **Roles / RBAC / admin** | There is **no role field on `doctors`** and no role-based authorisation anywhere. Access control is ownership only. | — | **not implemented** | `backend/app/models/doctor.py:32-42` — the table has `id, email, password_hash, full_name, created_at, bmdc_number` and five `default_*` columns, and no role. A `grep` for `role` in that file and in `domain/entities.py` returns nothing. |

---

## 2. Patients

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| Queue / dashboard | Landing screen after login; counts and recent work for the signed-in doctor. | `/dashboard` → `GET /dashboard/stats` | implemented | `frontend/src/app/dashboard/page.tsx`; `backend/app/api/dashboard.py:23` |
| Patients directory | All patients in registration order. | `/patients` → `GET /patients` | implemented | `backend/app/api/patients.py:148` |
| Find patient | Search by name or patient code. | `/patients/search` → `GET /patients/search` | implemented | `backend/app/api/patients.py:162` |
| Register patient | Name, date of birth, gender; the system assigns the patient code. | `/patients/new` → `POST /patients` | implemented | `backend/app/api/patients.py:137` |
| Patient profile with prior studies | One patient, with their report history in chronological order. | `/patients/[patientId]` → `GET /patients/{id}`, `GET /patients/{id}/history` | implemented | `backend/app/api/patients.py:195`, `:211` |
| Patient ownership | Patients are **institutional, not owned** — there is no `doctor_id` on `patients`. Ownership attaches to the work (sessions, reports, comparisons, explanations). | — | implemented, by design | `backend/app/domain/entities.py:60-65`; `backend/app/models/patient.py` |

---

## 3. Examination → report generation

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| New examination / upload | One guided flow: upload → retrieval → questionnaire → generate, with a live four-step progress display. | `/patients/[patientId]/upload` | implemented | `frontend/src/app/patients/[patientId]/upload/page.tsx:39-55` |
| Declared projection | The doctor must declare PA, AP or LATERAL; absence is a coded rejection, not a default. | `POST /retrieve` form field | implemented | `backend/app/api/retrieval.py:299-306`; `backend/app/services/image_admission_service.py:267-296` |
| Admission gate | Extension allow-list, magic-byte sniff, size bounds, `verify()` + `load()`, pixel ceiling, dimension bounds, PNG re-encode. Thirteen checks A1–A13. | `POST /retrieve` | implemented | `backend/app/services/image_admission_service.py:147-244` |
| PHI masking | EasyOCR detection, **solid black boxes, never blur or inpaint**. Runs before embedding. Only the masked copy is ever stored. | `POST /retrieve` | implemented | `backend/app/api/retrieval.py:396-404`; `shared/phi_masking/masker.py` |
| PHI reveal slider | Shows the uploaded original beside the masked copy, from a local object URL — the original is never uploaded or stored. | upload page | implemented | `frontend/src/app/patients/[patientId]/upload/page.tsx:30-36` |
| Modality gate | Softmax over BiomedCLIP text prompts; below `MODALITY_THRESHOLD` = 0.60, the upload is refused. **Blocks.** | `POST /retrieve` | implemented | `backend/app/services/modality_gate_service.py:138-158` |
| Projection band gate | Top-1 similarity below `PROJECTION_REJECT_THRESHOLD` = 0.8500 is refused as a projection mismatch. **Blocks.** | `POST /retrieve` | implemented | `backend/app/services/modality_gate_service.py:195-244` |
| Retrieval | k-NN over the 2,462-document train collection, top_k default 5. | `POST /retrieve` | implemented | `backend/app/api/retrieval.py:292-296`, `:432` |
| Label voting | Similarity-weighted vote over the retrieved cases; every label gets a weight and an agreement fraction. | — | implemented | `backend/app/services/label_voting_service.py` |
| Retrieval support signal | `at_or_above_floor` / `below_floor`, computed by the backend and sent as a value the frontend must not re-derive. | `POST /retrieve` response | implemented | `backend/app/api/retrieval.py:257-269` |
| Clinical questionnaire | Label-conditioned free-text questions between retrieval and generation; skippable via a workspace default. | `GET /questionnaire/{session_id}` | implemented | `backend/app/api/questionnaire.py:40`; `backend/app/services/questionnaire_templates.py` |
| Clinical notes | Free text the questionnaire does not cover; persisted with the report. | `POST /generate-report` | implemented | `backend/app/api/generation.py:54`; `backend/app/models/report.py:84` |
| Report generation | Seven-field structured report from `llama3:8b`, grounded on the retrieved evidence. | `POST /generate-report` | implemented | `backend/app/api/generation.py:94` |
| Structural validation + content retry | Delimiter-marker parsing; up to **2** content retries with a correction prompt. | — | implemented | `backend/app/services/structural_validator.py`; `backend/app/services/llm_orchestrator.py:61-75` |
| Semantic validation | Warnings for empty sections, unsupported terms and an unreflected top label. **Advisory — gates nothing.** | shown on the report page | implemented, advisory | `backend/app/services/response_validator.py:6-10` |
| Server-authored disclaimer | The model's disclaimer text is **replaced** by a server template fed both signals (agreement and retrieval support). | — | implemented | `backend/app/services/report_generation_service.py:228-249` |
| Consistency checking | Three checks — temporal, transplant, contradiction — run after generation and stored. Renders as four visually distinct states. | report page | **partial** | Service `backend/app/services/report_consistency_service.py`; UI `frontend/src/components/report/consistency-state.tsx`. Partial because of the two rows below. |
| **Consistency: transplant threshold (Gate B)** | The transplant check computes its scores but **emits no violation**, because no threshold has been calibrated. Consequence: **every English report reads `partial`, never `clean`.** | — | **not implemented** | `backend/app/main.py:233-241` — the thresholds are deliberately not passed; `amendment_01_consistency_status.md` §2(e) |
| **Consistency retry (Gate C)** | `CONSISTENCY_RETRY_COUNT = 1` exists in config and **is read by no service**. A violation is recorded and acted on by nothing. | — | **not implemented** | `grep -rn CONSISTENCY_RETRY_COUNT backend/` returns exactly two hits, both declarations: `config.py:273` and `config.py:493`. `report_generation_service.py:389`: *"Gate A performs no retry"* |

---

## 4. The report workspace

The workspace is now **three routes**, not one screen (2026-09-23, commit
`a8252e09`): Generate → Report → Evidence, with a step bar that doubles as the
way back.

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| Report page | Summary first — impression, recommendation, validation warnings and consistency verdict all visible without opening anything; the rest behind one disclosure. | `/workspace/[reportId]/report` | implemented | `frontend/src/components/report/full-report-disclosure.tsx` |
| Workspace index redirect | `/workspace/{id}` server-redirects to `/report`, so a deep link never paints an empty frame. | `/workspace/[reportId]` | implemented | `frontend/src/app/workspace/[reportId]/page.tsx` |
| Evidence page, three tabs | Evidence / Agreement / Alternatives, full width. **Fetches nothing** — every value comes off the report the layout already holds. | `/workspace/[reportId]/evidence` | implemented | `frontend/src/app/workspace/[reportId]/evidence/page.tsx:15`, `:24-31` |
| No-refetch guarantee | The segment layout holds the fetched report, so moving between Report and Evidence fires no request. | — | implemented | `frontend/src/app/workspace/[reportId]/layout.tsx:19-30` |
| Step bar | Generate → Report → Evidence, `aria-current="step"`; unreached steps are plain text, not disabled links. | workspace layout | implemented | `frontend/src/components/workspace/workspace-steps.tsx` |
| Section editing | Five of the seven fields are editable; `examination` and `disclaimer` are AI-set-once. | report page → `PATCH /reports/{id}` | implemented | `backend/app/domain/entities.py:308-320`; `backend/app/api/reports.py:249` |
| Section regeneration | Regenerate one section as a candidate the doctor accepts or rejects. | `POST /reports/{id}/regenerate-section` | implemented | `backend/app/api/reports.py:343` |
| Word-level diff | Shows what the doctor changed against the AI draft. | report page | implemented | `frontend/src/components/report/report-diff-view.tsx` |
| Finalize | AI_DRAFT → DOCTOR_EDITED → FINAL, with a preview and an audit row. | `PATCH /reports/{id}/finalize` | implemented | `backend/app/api/reports.py:315`; `backend/app/models/report_audit_log.py` |
| Delete report | Owner only; refused once finalized (409). | `DELETE /reports/{id}` | implemented | `backend/app/api/reports.py:284-312` |
| Read-only for non-owners | A non-owner sees the report with an owner chip and no edit controls. | — | implemented | `backend/app/services/report_edit_service.py:101-104`; `frontend/src/components/ui/owner-chip.tsx` |
| **Print / Save as PDF** | A second render for paper via the browser's own print dialog, including a Bengali page that rasterises. | print portal, any workspace route | implemented, **client-side only** | `frontend/src/components/report/print-portal.tsx`; `printable-report.tsx` |
| **Server-side PDF export** | **No export route exists** in `backend/app/api/`, and **no PDF or DOCX library** is in `frontend/package.json`. Printing is `window.print()`; the file is produced by the browser, not by this system. | — | **not implemented** | `grep` for an export route across `backend/app/api/` returns nothing; `frontend/package.json` dependency list contains no export library |

---

## 5. Downstream tools

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| Explainability chat | Ask a question about a finished report; the answer is grounded on the same evidence block the report used. | `/reports/[reportId]/explain` → `POST /reports/{id}/explain` | implemented | `backend/app/api/explainability.py:60`; `backend/app/services/explainability_service.py` |
| Longitudinal comparison | Compare a report with a prior report for the same patient — deterministic facts first, then a narrative. | `/reports/[reportId]/compare` → `POST /comparisons` | implemented | `backend/app/api/comparisons.py:69`; `backend/app/services/deterministic_comparator.py` |
| Query image replay | The masked query image of any past session can be redisplayed. | `GET /retrieval-sessions/{id}/image` | implemented | `backend/app/api/retrieval.py:508` |

---

## 6. Cross-cutting

| feature | description | page / route | status | evidence |
|---|---|---|---|---|
| Bilingual EN ⇄ বাংলা | Global toggle; **412 keys in both dictionaries, parity checked by a script**. Reports are **generated directly in Bengali**, not translated. | everywhere | implemented, **unevaluated** | `frontend/src/lib/i18n/dictionaries/{en,bn}.ts`; `node scripts/check-i18n.mjs` → *"i18n parity OK — 412 keys in both en.ts and bn.ts"*; `backend/app/services/prompt_builder.py:122-125`. **No Bengali output has ever been evaluated** and all three consistency checks are English-only (`report_consistency_service.py:63-70`) |
| Light / dark theme | Two different palettes, not one inverted; light is derived from the Orthoc template, hue adopted and luminance rejected. | everywhere | implemented | `frontend/src/styles/tokens.css`; `docs/thesis/figures/ui/README.md`; `node scripts/check-design-tokens.mjs` → *"palette parity OK — 21 themed tokens in both palettes; 0 violations"* |
| Settings / profile | Full name, BMDC number, and five workspace defaults (top-k, language, questionnaire skip, rail state, export format). | `/settings` → `PATCH /auth/me` | implemented | `backend/app/api/auth.py:145`; `backend/app/models/doctor.py:37-42` |
| Service health strip | Real FastAPI / Ollama / ChromaDB / GPU reachability checks. | `GET /health` | implemented | `backend/app/api/retrieval.py:273`; `backend/app/services/service_health_service.py` |
| System stats | Index size read from ChromaDB itself. | `GET /system/stats` | implemented | `backend/app/api/system.py:25`; `backend/app/services/system_stats_service.py` |
| Upload rejection audit | Every refused upload is recorded with reason code, stage, SHA-256, size and extension — **never the filename**. | — | implemented | `backend/app/models/upload_rejection.py`; `backend/app/api/retrieval.py:154-168` |
| Report edit audit | `report_audit_log` records EDIT actions against a report and doctor. | — | **partial** | The table exists and is written. There is **no general audit trail** — no login, read or export events are recorded anywhere |

---

## 7. Summary of what is NOT implemented, and why

| # | feature | why not | evidence |
|---|---|---|---|
| 1 | **BMDC verification** | There is no BMDC registry this system can reach. The number is recorded as entered and the UI is required to say so rather than imply verification. | `backend/app/domain/entities.py:73-74` |
| 2 | **Admin role / RBAC** | No role column was ever added to `doctors`. Access control is ownership-only: a doctor may edit what they created, and nothing else. Nothing in the system needs an actor above that, so no admin actor appears in the use-case diagram either. | `backend/app/models/doctor.py:32-42` |
| 3 | **Server-side PDF** | No export endpoint and no PDF library. The print path was deliberately built as a second browser render (`print-portal.tsx`), which reaches paper without a server renderer — and without a font stack for Bengali on the server, which would have been the hard part. | `frontend/src/components/report/print-portal.tsx`; absence of any export route under `backend/app/api/` |
| 4 | **Consistency retry (Gate C)** | Gate A's scope was explicitly *observational*: measure the check's effect while it changes nothing. The retry is the next gate, not this one. The config value exists and is read by no code, which is the honest state — **17/477 recorded violations were acted on by nothing.** | `config.py:273` and `:493` are the only two occurrences in the backend; `report_generation_service.py:389` |
| 5 | **Gate B transplant threshold** | Calibrating it needs a labelled set this project does not have. Rather than invent a number, `main.py` passes none, and the check records its scores and emits no violation. The visible consequence is that **no English report can currently read `clean`.** | `backend/app/main.py:233-241`; `amendment_01_consistency_status.md` §2(e) |
| 6 | Near-duplicate dedup at retrieval | `SimilaritySearchPolicy` documents cluster-based dedup as a future extension point and does not implement it. The `ContextBuilder` collapses near-duplicates afterwards instead. | `backend/app/services/similarity_search.py:6-9` |
| 7 | `build_translation_prompt` | Permanently unimplemented by design — Bengali is generated directly, so there is no translation pass to prompt for. | `backend/app/services/prompt_builder.py:10-17`; `backend/app/domain/interfaces.py:114` |
| 8 | Multi-label `label_set` in the retrieve response | `chroma_result_mapper.py`'s multi-label parsing is an open TODO, so `label_set` is today a degenerate single value. | `backend/app/api/retrieval.py:228-232` |
