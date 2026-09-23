# 05_screenshots — manifest

**33 PNGs, all 1440 × 900, captured 2026-09-23 from the CURRENT page-based UI**
(Generate → Report → Evidence), which landed at commit `a8252e09`. These
**replace** the 11 stale shots in `docs/thesis/figures/ui/`, every one of which
depicts the superseded single-screen workspace (see that folder's `STALE.md`).

Ordered as a new user meets the screens. Dark is the product's native theme
(`DEFAULT_THEME = "dark"`, `frontend/src/lib/theme/shared.ts:13`); the light
set at the end is the same screens under `rr_theme=light`.

---

## How these were captured, and why dev.db is safe

| | |
|---|---|
| **Script** | [`capture.mjs`](capture.mjs) (+ [`recapture_compare.mjs`](recapture_compare.mjs), [`recapture_belowfloor.mjs`](recapture_belowfloor.mjs)) — in this packet, not in `e2e/`, because the brief forbids source changes |
| **Driver** | Real headless Edge over CDP, reusing `e2e/harness.mjs` |
| **Backend** | `127.0.0.1:8021`, started against **`backend/test-shots.db`**, a disposable `cp` of `dev.db` |
| **Frontend** | `localhost:3021`, `NEXT_PUBLIC_API_URL=http://localhost:8021` |
| **Live services** | Ollama `llama3:8b` (digest `365c0bd3c000`) resident on GPU; ChromaDB `iu_cxr_biomedclip_v1_train`, **2,462** docs |
| **dev.db before** | `sha256 2823386768c597c9121fa07ccb9706db60741b09e198e6c313cb50a2ad7523d4`, 14,135,296 bytes, mtime `2026-09-23 12:09:20` |
| **dev.db after** | **identical on all three** — hash, size and mtime unchanged. Verified after teardown. |
| **Disposable copy** | deleted after capture |

**Two deviations from a stock dev environment, both recorded rather than hidden:**

1. **`CORS_ALLOWED_ORIGINS=http://localhost:3021`.** `DEFAULT_CORS_ALLOWED_ORIGINS`
   is `http://localhost:3000` (`backend/app/core/config.py:108`) and the
   allowlist holds exactly one origin (`main.py:254` passes
   `allow_origins=[settings.CORS_ALLOWED_ORIGINS]`, a one-element list). On a
   non-default port every `POST` preflight returns **400** and the UI renders
   "Failed to load report." This was hit for real in the first capture pass.
2. **Three fixtures were re-pointed inside the disposable copy** so one doctor
   could reach all three reachable consistency states. `retrieval_sessions.doctor_id`
   and `.patient_id` for reports `aa967481…`, `97aac3d4…` and `30fe6afa…` were
   set to `mosabber@gmail.com` / `PAT-000035`, and that doctor's
   `password_hash` was replaced with a known argon2 hash. **No report content,
   consistency column or validation warning was altered** — only ownership.

**Consistency states shown.** Three of the four exist in this build. `clean` is
**unreachable** until Gate B calibrates the transplant threshold, because that
check cannot emit a violation and so is never listed in `checks_run`, making
every English report a strict subset of `applicable` → `partial`
(`backend/app/api/consistency_status.py`, module docstring; `amendment_01_consistency_status.md` §2(e)).
`not_run`, `partial` and `violations` are all captured; **`clean` is not, because
no state of this system produces it.**

---

## The screens

| # | file | route | app state shown | caption |
|---|---|---|---|---|
| 01 | `01-landing-dark.png` | `/` | signed out | The public landing page, the first screen a new user meets. |
| 02 | `02-registration-dark.png` | `/register` | signed out, empty form | Doctor registration: full name, email, BMDC number, password. The BMDC number is **recorded as entered and never verified** — the form says so. |
| 03 | `03-login-dark.png` | `/login` | signed out, empty form | Sign in with email and password. |
| 04 | `04-queue-dark.png` | `/dashboard` | worklist, 13 reports for this doctor | The queue: every report this doctor owns. |
| 05 | `05-find-patient-dark.png` | `/patients/search` | empty search | Find patient by code or name before starting an examination. |
| 06 | `06-patients-dark.png` | `/patients` | patient list, 3 patients | All patients this doctor has examined. |
| 07 | `07-register-patient-dark.png` | `/patients/new` | empty form | Registering a new patient record. |
| 08 | `08-patient-profile-dark.png` | `/patients/{id}` | PAT-000035, 10 prior studies | Patient profile: demographics and the list of prior studies. |
| 09 | `09-new-examination-dark.png` | `/patients/{id}/upload` | empty drop target | New examination: the film drop target before an image is chosen. |
| 10 | `10-upload-selected-dark.png` | `/patients/{id}/upload` | film selected, **PA declared** | The projection is **required** — the start control stays disabled until one is picked (`disabled={!file \|\| !declaredProjection}`, `upload/page.tsx:414`). |
| 11 | `11-generate-in-progress-dark.png` | `/patients/{id}/upload` | pipeline running | Generate in progress: upload → retrieve → questionnaire → draft, with live per-step timings. |
| 12 | `12-questionnaire-dark.png` | `/patients/{id}/upload` | optional questionnaire offered | The clinical questionnaire offered after retrieval; it can be skipped, and a doctor default can skip it always. |
| 13 | `13-generate-complete-dark.png` | `/patients/{id}/upload` | all steps done, result offered | **Real measured run, this session, n=1:** upload **0.1 s**, retrieval **1.0 s**, questionnaire skipped, generation **3.9 s**. The reader chooses when to open the result — the page deliberately does not auto-navigate. |
| 14 | `14-result-partial-dark.png` | `/workspace/{id}/report` | **consistency = `partial`** | The result page. Two validation warnings, and "Partially checked — Ran: temporal, contradiction. Not run: transplant." |
| 15 | `15-result-violations-dark.png` | `/workspace/{id}/report` | **consistency = `violations`** | A temporal-check violation raised on a report with no prior study. |
| 16 | `16-result-warnings-dark.png` | `/workspace/{id}/report` | **consistency = `not_run`**, 3 validation warnings | A pre-v1.2 report: nothing was ever assessed, and the UI says so rather than showing a pass. |
| 17 | `17-evidence-below-floor-dark.png` | `/workspace/{id}/evidence` | **retrieval support = `below_floor`** | "Below threshold", top-1 similarity **88.3 %**. Captured on the Evidence page's Agreement tab, which is where this notice renders — **not** on the report page. |
| 18 | `18-full-report-expanded-dark.png` | `/workspace/{id}/report` | full-report disclosure open | All seven fields, expanded from the summary. |
| 19 | `19-evidence-tab-evidence-dark.png` | `/workspace/{id}/evidence` | Evidence tab | The k retrieved neighbour cases and their similarities. |
| 20 | `20-evidence-tab-agreement-dark.png` | `/workspace/{id}/evidence` | Agreement tab | Retrieval support "Met", top-1 97.9 %, mean 97.7 %, "3 of 5 retrieved cases agree". Carries the disclaimer **"Not a probability that the report is correct."** |
| 21 | `21-evidence-tab-alternatives-dark.png` | `/workspace/{id}/evidence` | Alternatives tab | Labels that did not win the vote. |
| 22 | `22-explainability-idle-dark.png` | `/reports/{id}/explain` | before a question is asked | The grounding questions a doctor may ask, and the "cases in context" list. |
| 23 | `23-explainability-answered-dark.png` | `/reports/{id}/explain` | question asked and answered, **live LLM** | A real answer (3.5 s): impression, evidence strength ("Strong — 3 of 5 retrieved cases agree on Normal"), and the findings it rests on. |
| 24 | `24-compare-dark.png` | `/reports/{id}/compare` | comparison complete, **live LLM** | Resolved / Persistent / New computed deterministically by `ComparisonService`; the narrative written by the LLM **from that split only**. The provenance note says which is which. |
| 25 | `25-print-preview-dark.png` | `/workspace/{id}/report` | print media emulation, English | Print / Save as PDF. This is **browser print** — there is no server-side PDF. `PrintPortal` is mounted by the workspace layout, so `.rr-print-root` exists on both workspace routes. |
| 26 | `26-settings-profile-dark.png` | `/settings` | profile + workspace defaults | **Settings *is* the profile screen.** There is no `/profile` route in this build; the rail's avatar links to `/settings` (`app-rail.tsx:219`). |
| 27 | `27-report-bengali-dark.png` | `/workspace/{id}/report` | `language=bn`, **consistency = `not_run`** | A Bengali report: UI and report body both translated, and the consistency block reads *"পরীক্ষা চালানো হয়নি"* with *"বাংলা রিপোর্টের জন্য সামঞ্জস্য পরীক্ষা উপলব্ধ নয়।"* — the frozen §3.4 contract that a non-English report must never show a pass. |
| 28 | `28-login-light.png` | `/login` | signed out | Sign in, light theme. |
| 29 | `29-queue-light.png` | `/dashboard` | worklist | The queue, light theme. |
| 30 | `30-patient-profile-light.png` | `/patients/{id}` | PAT-000035 with priors | Patient profile, light theme. |
| 31 | `31-result-partial-light.png` | `/workspace/{id}/report` | consistency = `partial` | The result page, light theme. |
| 32 | `32-evidence-light.png` | `/workspace/{id}/evidence` | Evidence tab | The evidence page, light theme. |
| 33 | `33-settings-light.png` | `/settings` | profile | Settings / profile, light theme. |

---

## What a reader should notice, and what they should not conclude

- **Shot 27's validation warning is still in English** (*"Top voted label 'Normal'
  (agreement 0.60) not reflected in report text"*) on an otherwise fully Bengali
  screen. That is a real i18n gap; it is recorded in
  [`../08_admin/known_defects.md`](../08_admin/known_defects.md).
- **Shot 24 reads "-2 DAYS APART"** — a negative interval, because the prior
  study is dated *after* the current one in the seeded data. Also recorded as a
  defect.
- **Shots 24 and 27 show a watermarked stock image**, not an IU dataset film.
  That is what was uploaded into `dev.db` during manual QA; it is seeded test
  data, not a dataset sample, and no result in `06_results/` derives from it.
- **The timings in shot 13 are one observation on one machine**, not a benchmark.
  The measured latency distributions are in
  [`../06_results/performance_and_tests.md`](../06_results/performance_and_tests.md);
  do not quote shot 13 as a performance result.
- **No screenshot here evidences an evaluation number.** Every quantitative
  claim in the thesis comes from `06_results/`, which cites result files.
