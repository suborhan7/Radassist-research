# User manual — outline

Written for **Chapter 7 of the final report**. Every step names the screen, what
the user does, what they see, and the screenshot that illustrates it. Every
screenshot referenced here exists in
[`../05_screenshots/`](../05_screenshots/manifest.md) and was captured from the
current page-based UI on 2026-09-23.

**Audience:** a doctor using the system for the first time.
**One role only.** There is exactly one actor — the doctor — and no admin role
exists in this build. See §0.3.

---

## 0. Before you start

### 0.1 Installation and setup

| step | what to do | what you see |
|---|---|---|
| 1 | Start **Ollama** and make sure `llama3:8b` is pulled (digest `365c0bd3c000`). | `ollama ps` lists the model, `100% GPU`. |
| 2 | Start the **backend**: `python -m uvicorn app.main:app` from `backend/`. It serves on `localhost:8000` by default. | `GET /health` returns `status: ok` for FastAPI, Ollama, ChromaDB and GPU. |
| 3 | Start the **frontend**: `npm run dev` from `frontend/`. It serves on `localhost:3000`. | The landing page loads. |
| 4 | Open `http://localhost:3000`. | — |

> **The frontend must run on port 3000 unless you also set
> `CORS_ALLOWED_ORIGINS`.** The backend's allowlist holds exactly one origin and
> defaults to `http://localhost:3000`. On any other port every action fails with
> "Failed to load report." (`08_admin/known_defects.md` A10.)

> **Everything runs locally.** The upload screen states it: *"Everything runs
> locally; nothing leaves the building."*

### 0.2 What the system is, and is not

It drafts a chest X-ray report from **five similar archived cases** and hands it
to you to review, edit and sign. Every report carries the line: *"Drafted from 5
archive cases, then reviewed and edited by the reporting radiologist. **Not an
autonomous diagnosis.**"* It is a decision-support tool. **You remain the
author.**

### 0.3 Who can use it

**One role: the doctor.** There is no admin account, no admin screen and no role
column in the schema. A doctor sees only their own reports; another doctor's
report is readable but **every write is rejected with 403**.

---

## 1. Registration and login

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 1.1 | Landing `/` | Read what the system does; choose **Sign in** or **Register**. | The public landing page. | `01-landing-dark.png` |
| 1.2 | Register `/register` | Enter full name, email, **BMDC number**, password. | The form. | `02-registration-dark.png` |
| 1.3 | — | — | ⚠️ **Your BMDC number is recorded exactly as you type it and is never checked.** The form says so: *"This system has no access to the BMDC registry and cannot verify it."* | `02-registration-dark.png` |
| 1.4 | Login `/login` | Enter email and password. | You land on the Queue. | `03-login-dark.png` |

## 2. The Queue — your worklist

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 2.1 | `/dashboard` | This is where login takes you. | Every report you own, newest first, each with its patient, date and status chip (`AI Draft`, `Doctor edited`, `Final`). | `04-queue-dark.png` |
| 2.2 | — | Click any row to reopen that report. | The result page for that report. | `14-result-partial-dark.png` |

## 3. Finding or creating a patient

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 3.1 | Find patient `/patients/search` | Search by patient code or name. | Matching patients. | `05-find-patient-dark.png` |
| 3.2 | Patients `/patients` | Or browse everyone you have examined. | The full patient list. | `06-patients-dark.png` |
| 3.3 | New patient `/patients/new` | If they are new, register them: code, name, date of birth, gender. | The empty form. | `07-register-patient-dark.png` |
| 3.4 | Patient profile `/patients/{id}` | Open the patient. | Demographics **and every prior study**, which is what makes Compare possible later. | `08-patient-profile-dark.png` |

## 4. New examination — Generate

This is the first step of the three-step workspace: **Generate → Report →
Evidence**.

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 4.1 | `/patients/{id}/upload` | Drop the chest film on the left, or click to choose a file. | The empty film drop target. | `09-new-examination-dark.png` |
| 4.2 | — | **Select the projection — PA, AP or Lateral.** | ⚠️ **Required.** *Start examination* stays disabled until you pick one. | `10-upload-selected-dark.png` |
| 4.3 | — | Optionally type clinical notes. | *"Anything the questionnaire does not cover; included in the generation context."* | `10-upload-selected-dark.png` |
| 4.4 | — | Press **Start examination**. | Four steps run with live timings: **Uploading → Retrieving similar cases → Clinical questionnaire → Generating AI report**. | `11-generate-in-progress-dark.png` |
| 4.5 | — | Answer the questionnaire, or press **Skip**. | The optional questionnaire. You can make skipping your default in Settings. | `12-questionnaire-dark.png` |
| 4.6 | — | Wait. | All four steps complete. In the captured run: upload 0.1 s, retrieval 1.0 s, generation 3.9 s. | `13-generate-complete-dark.png` |
| 4.7 | — | Press **View result** when you are ready. | ℹ️ The page **does not navigate on its own** — the per-step timings stay on screen until you choose to move on. | `13-generate-complete-dark.png` |

> **What can go wrong here.** A lateral film is **rejected at admission** — the
> system reports frontal chest X-rays only. A film whose projection does not
> match what you declared is rejected after embedding. Both produce a message on
> the *Retrieving similar cases* step.

## 5. The Report — reviewing the draft

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 5.1 | `/workspace/{id}/report` | Read the **Impression** and **Recommendation** first — the summary shows these two. | The summary-first report panel, with the masked film on the left. | `14-result-partial-dark.png` |
| 5.2 | — | Read the **Validation** box if present. | Amber warnings, e.g. *"Mentions 'Pleural Effusion' which is not supported by retrieved evidence."* | `16-result-warnings-dark.png` |
| 5.3 | — | Read the **Consistency** box. | One of three states — see §5.4. | `14`, `15`, `16` |
| 5.4 | — | — | **`Partially checked`** (every English report today): *"Ran: temporal, contradiction. Not run: transplant."* **`Violations`**: a check found a problem. **`Checks not run`**: nothing was assessed — this is **not** a pass. | `14-result-partial-dark.png`, `15-result-violations-dark.png`, `16-result-warnings-dark.png` |
| 5.5 | — | Press **Show full report**. | All seven fields: Examination, Clinical History, Technique, Findings, Impression, Recommendation, Disclaimer. | `18-full-report-expanded-dark.png` |
| 5.6 | — | Edit any field directly. | The status chip changes to **Doctor edited**; **Changes vs draft** shows what you altered. | `18-full-report-expanded-dark.png` |
| 5.7 | — | Press **Finalize** when the report is yours. | The report is signed and becomes **Final**. | — (`25-print-preview-dark.png` shows a finalized report) |

> ⚠️ **A validation warning always describes the AI draft, never your edited
> text.** Warnings are computed once, at generation, and are not recomputed when
> you edit. (`08_admin/known_defects.md` A8.)

> ⚠️ **No consistency state in this build means "checked and clean."** `clean` is
> unreachable until the transplant threshold is calibrated.
> (`08_admin/open_items.md` O3.)

## 6. Evidence — what the draft was built from

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 6.1 | `/workspace/{id}/evidence` | Press **View evidence**, or use the step bar. | The **Evidence** tab: the five retrieved neighbour cases and their similarities. | `19-evidence-tab-evidence-dark.png` |
| 6.2 | — | Open the **Agreement** tab. | Retrieval support (Met / Below threshold), top-1 and mean similarity, and *"3 of 5 retrieved cases agree on the primary finding."* | `20-evidence-tab-agreement-dark.png` |
| 6.3 | — | — | ⚠️ The panel states its own limit: *"Measures agreement among retrieved cases. **Not a probability that the report is correct.**"* | `20-evidence-tab-agreement-dark.png` |
| 6.4 | — | If support reads **Below threshold**, treat the draft with extra care. | *"No retrieved case meets the minimum retrieval-support threshold… This does not mean no similar case exists — only that none of the cases retrieved met the threshold."* | `17-evidence-below-floor-dark.png` |
| 6.5 | — | Open the **Alternatives** tab. | Labels that did not win the vote. | `21-evidence-tab-alternatives-dark.png` |

## 7. Explainability — asking about the draft

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 7.1 | `/reports/{id}/explain` | Press **Explain report**. | Suggested questions, and the *Cases in context* list with similarities. | `22-explainability-idle-dark.png` |
| 7.2 | — | Pick a suggested question or type your own. | — | `22-explainability-idle-dark.png` |
| 7.3 | — | Press **Ask**. | The impression, the evidence strength (*"Strong — 3 of 5 retrieved cases agree on Normal"*), and the findings it rests on. | `23-explainability-answered-dark.png` |
| 7.4 | — | — | ℹ️ *"Answers are grounded in the retrieved cases and this report. The assistant cannot introduce new findings, and it is not a second opinion."* Questions and answers **stay with the report as part of its audit trail**. | `23-explainability-answered-dark.png` |

## 8. Compare — this study against a prior

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 8.1 | `/reports/{id}/compare` | Press **Compare previous**. Requires a prior study for the same patient. | Both films side by side with their impressions. | `24-compare-dark.png` |
| 8.2 | — | Read the three-column split. | **Resolved / Persistent / New** — computed **deterministically** by `ComparisonService`. | `24-compare-dark.png` |
| 8.3 | — | Read the narrative. | Written by the LLM **from that split only**. The provenance line at the foot says which is which: *"the change itself is not decided by the model."* | `24-compare-dark.png` |

## 9. Printing and exporting

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 9.1 | Report page | Press **Print / Save as PDF**. | Your browser's print dialog. | `25-print-preview-dark.png` |
| 9.2 | — | Choose *Save as PDF* in the browser. | A one-page report: header, all seven fields, validation and consistency blocks. | `25-print-preview-dark.png` |

> ℹ️ **This is browser print.** There is **no server-side PDF generator** — the
> PDF is produced by your browser, so its pagination and fonts are your
> browser's.

## 10. Settings and profile

| step | screen | what to do | what you see | screenshot |
|---|---|---|---|---|
| 10.1 | `/settings` | Open **Settings** in the rail, or click your avatar. | ℹ️ **Settings *is* the profile screen.** There is no separate profile route; the avatar links here. | `26-settings-profile-dark.png` |
| 10.2 | — | Edit your name and BMDC number. | Saved to your account. | `26-settings-profile-dark.png` |
| 10.3 | — | Set workspace defaults: **k** (neighbours retrieved), default language, skip-questionnaire, evidence rail state, export format. | These become the defaults for every new examination. | `26-settings-profile-dark.png` |

## 11. Language and theme

| step | what to do | what you see | screenshot |
|---|---|---|---|
| 11.1 | Use the **EN / বাংলা** toggle, bottom right on every screen. | The whole interface switches, and **new reports are drafted in the selected language**. | `27-report-bengali-dark.png` |
| 11.2 | Use the **moon / sun** toggle beside it. | Dark (the native theme) or light. Both are fully supported. | `28`–`33` (`*-light.png`) |

> ⚠️ **A Bengali report always reads "consistency checks not run."** All three
> checks are English-only, and the system is deliberate about this: it shows
> "not run" rather than a clean tick, because *"a Bengali report showing a green
> tick — or showing nothing at all, which a clinician reads as 'nothing wrong' —
> would convert an acknowledged coverage gap into an affirmative false
> assurance, which is worse than the gap itself."*

> ⚠️ **Known gap:** validation warning text is **still English** on a Bengali
> screen. (`08_admin/known_defects.md` A9.)

---

## 12. Quick reference — the whole flow

```
Register / Login
      ↓
Queue  ──→  Find patient  ──→  Patient profile (prior studies)
                                      ↓
                          New examination  (drop film, declare projection)
                                      ↓
                    GENERATE   upload → retrieve → questionnaire → draft
                                      ↓
                    REPORT     read · validation · consistency · edit · finalize
                                      ↓
                    EVIDENCE   neighbours · agreement · alternatives
                                      ↓
              Explain  ·  Compare  ·  Print / Save as PDF
```

## 13. What the manual must not promise

These are asked about often and **do not exist in this build**:

| not available | why |
|---|---|
| BMDC verification | no registry access; the number is stored as typed |
| An admin role or admin screen | no role exists in the schema |
| Server-side PDF | printing is the browser's |
| Automatic correction of a consistency violation | Gate C not built; violations are recorded only |
| A "clean" consistency verdict | unreachable until Gate B calibrates the transplant threshold |
| Consistency warnings in the interface | stored and served, **not rendered** |
| Any Bengali quality guarantee | never measured |
| MRI or CT | frontal chest radiographs only |
