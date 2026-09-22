# UI screenshots to capture, in thesis order

> Every route below exists as a page file in `frontend/src/app/`. Nothing here
> is speculative; the "evidence" column names the file. Capture at a single
> viewport (1440×900 suggested) so the figures are consistent, and capture both
> EN and বাংলা only where the caption says so.
>
> **Two report ids are needed throughout:** the **v1.1 trigger report**
> `4e0a63d0bdb146518895f684611bb420` (the original screenshot case, showing the
> defects) and any **v1.2 re-test report**, e.g.
> `3513df7a-f8bc-4d58-9a57-36b1c947e417` (see
> [`trigger_case_retest.md`](../../phase22/trigger_case_retest.md)).

| # | route | state to capture | why it is in the thesis | page file |
|---|---|---|---|---|
| 1 | `/login` | empty form | entry point; shows JWT + Argon2 auth exists | `login/page.tsx` |
| 2 | `/register` | empty form | account creation | `register/page.tsx` |
| 3 | `/dashboard` | populated — several patients and reports present | system overview; backs `GET /dashboard/stats` | `dashboard/page.tsx` |
| 4 | `/patients` | list with ≥5 patients | patient management is implemented | `patients/page.tsx` |
| 5 | `/patients/new` | filled form, before submit | patient creation | `patients/new/page.tsx` |
| 6 | `/patients/search` | a query typed, results shown | search endpoint `GET /patients/search` | `patients/search/page.tsx` |
| 7 | `/patients/[patientId]` | a patient with ≥2 prior reports | longitudinal history; feeds the comparison path | `patients/[patientId]/page.tsx` |
| 8 | `/patients/[patientId]/upload` | **(a)** empty drop zone | the upload entry point | `patients/[patientId]/upload/page.tsx` |
| 9 | same | **(b)** frontal CXR selected, before submit | the admission gate's input | same |
| 10 | same | **(c)** retrieval result — 5 neighbours with similarities and labels | **the core RAG evidence panel**; pair with the neighbour table in `trigger_case_retest.md` §1 | same |
| 11 | same | **(d)** questionnaire shown for the session | `GET /questionnaire/{session_id}` | same |
| 12 | same | **(e)** clinical-notes field filled | free-text clinician input reaches the prompt | same |
| 13 | same | **(f)** a **rejected** upload — lateral view or non-CXR image, showing the rejection message | **DR-4 / DR-5 gates are real and user-visible**; backs `upload_rejection_log` | same |
| 14 | `/reports/[reportId]` | **v1.1 trigger report** `4e0a63d0…`, AI draft as generated | **the failure case the whole of Phase 22 is about** — cardiomegaly contradiction, transplanted impression, "stable" with no prior | `reports/[reportId]/page.tsx` |
| 15 | `/reports/[reportId]` | **v1.2 report** `3513df7a…`, same image, same 5 neighbours | **the after picture**; all four defects absent | same |
| 16 | `/reports/[reportId]` | evidence / retrieved-cases section expanded | shows the report is attributed to specific neighbour uids | same |
| 17 | `/reports/[reportId]` | server-authored disclaimer visible | the disclaimer is written by the server, not the model | same |
| 18 | `/reports/[reportId]` | a section in **edit** mode, before save | `PATCH /reports/{id}`, `ai_draft_content` vs `final_content` | same |
| 19 | `/reports/[reportId]` | after an edit — the draft-vs-final diff view | the `diff` dependency is used here; provenance of every clinician change | same |
| 20 | `/reports/[reportId]` | **section regeneration** in progress or its result | `POST /reports/{id}/regenerate-section` | same |
| 21 | `/reports/[reportId]` | status transition control — AI_DRAFT → DOCTOR_EDITED → FINAL | the human-in-the-loop workflow; `PATCH /reports/{id}/finalize` | same |
| 22 | `/reports/[reportId]/explain` | a question asked and answered | `POST /reports/{id}/explain`, the explainability assistant | `reports/[reportId]/explain/page.tsx` |
| 23 | `/reports/[reportId]/compare` | two studies for one patient, differences highlighted | `POST /comparisons`, `DeterministicComparator` | `reports/[reportId]/compare/page.tsx` |
| 24 | `/settings` | profile + workspace defaults | `PATCH /auth/me` | `settings/page.tsx` |
| 25 | `/reports/[reportId]` | **the same report rendered in বাংলা** (toggle switched) | the bilingual layer; caption **must** say Bengali output has never been evaluated (see `gate_a_results.md` §7) | same |
| 26 | `/dashboard` | **বাংলা** | shows the toggle is global, not report-only | `dashboard/page.tsx` |
| 27 | `/` | landing / root | completeness | `page.tsx` |

## Deliberately NOT in the list

| thing | why not |
|---|---|
| a consistency-warning banner | **no UI renders it.** The v1.2 consistency result is returned by the API and stored in the database, but nothing displays it — this is defect #1 in `thesis_facts.md` §5. Do not stage a mock-up of one. |
| an export / download dialog | export is not implemented (`thesis_facts.md` §3) |
| a role or permissions screen | no RBAC exists (`thesis_facts.md` §3) |
| an audit-trail screen | only report EDIT actions and upload rejections are logged, and neither has a page |

## Capture notes

- Shots 14 and 15 are the **paired before/after** and should be laid out side by
  side in the thesis. They share the same query image
  (`b3b2575a-998b-4c2b-8f78-dab3c72ac2ea.png`) and the same five neighbours, so
  the only difference visible is the generated text.
- Shot 13 needs a deliberately bad upload. A lateral chest film is the cleanest
  demonstration, since Gate B calibration rejected **300/300** laterals
  (`v1_1_gate_b_selected_values.csv`).
- Any patient names, MRNs or dates of birth visible in shots 3–7 must be
  synthetic before the thesis is submitted.
