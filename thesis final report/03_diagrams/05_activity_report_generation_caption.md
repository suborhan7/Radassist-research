# Figure 5 — Activity flow, end to end (three parts)

The end-to-end activity flow is **one flow rendered as three figures**, because
a single rendering would print at under 3 pt. The parts join at explicit
connector nodes and must be read in order.

| part | file | what it covers | render | recommended print | body pt |
|---|---|---|---|---|---|
| **5a** | `05_activity_report_generation.png` | upload → admission → masking → embedding → modality gate → retrieval → support band → persistence | 2359 × 4250 px | 4.99 × 9.00 in | **7.6 pt** |
| **5b** | `05b_activity_generation_review.png` | questionnaire → prompt → LLM → structural retry → semantic → consistency → persist as AI_DRAFT | 2391 × 5713 px | 3.77 × 9.00 in | **5.7 pt** |
| **5c** | `05c_activity_doctor_review.png` | the doctor's loop: read → edit → regenerate → finalize → print | 1316 × 4066 px | 2.91 × 9.00 in | **8.0 pt** |

All three carry 300 dpi metadata; at the recommended print sizes the effective
resolution is 472, 634 and 452 dpi respectively.

## What they show

**Every decision node in these figures is a branch that really exists in the
code.** The task of the figure is as much to show what does *not* branch as
what does.

### The decisions that really exist

| decision | blocks? | where |
|---|---|---|
| admission A1–A13 | **yes** — 415 / 413 / 422 | `image_admission_service.py:147` |
| declared projection A14–A17 | **yes** — 422 | `image_admission_service.py:246` |
| modality gate, score ≥ 0.60 | **yes** — 422 | `modality_gate_service.py:138` |
| projection band, top-1 < 0.8500 | **yes** — 422 | `modality_gate_service.py:195` |
| retrieval support (below / at-or-above floor) | **no** — sets a category only (DR-3) | `modality_gate_service.py:164` |
| structural validation, 7 markers | **yes** — retry ×2, then 422 | `llm_orchestrator.py:61-75` |
| semantic warnings | **no** — advisory, gates nothing | `response_validator.py:6-10` |
| consistency state (4 states) | **no** — observational | `report_consistency_service.py:292` |
| doctor edit / regenerate / finalize | the human decisions | `api/reports.py:249, 343, 315` |

### The decision that does not exist, drawn as an absence

In 5b, the dashed box hanging off the `violations` state records that **a
recorded violation triggers no retry**. `CONSISTENCY_RETRY_COUNT = 1` exists in
config and is read by no service; Gate A recorded **17 violations in 477
reports** and each was acted on by nothing. Drawing it as a dashed note rather
than a live branch is the point: the figure must not imply a loop that the
code does not contain.

### Two states worth reading carefully in 5b

- **`partial` is not a pass.** Because the transplant check has no calibrated
  threshold, it never runs to completion, so `checks_run` is always a strict
  subset of `applicable_checks` — and **every English report lands in
  `partial`**. `clean` is reachable in principle and, in the current database,
  reached by nothing.
- **A non-English report shows `not_run`, never a green tick.** All three
  checks are English-only by construction. Showing nothing at all, which a
  clinician reads as "nothing wrong", would convert an acknowledged coverage
  gap into an affirmative false assurance.

### One state change in 5c

`FINAL` is a one-way door: after finalize, `PATCH /reports/{id}` returns
**409**, ownership or not.

## Greyscale key

Black filled circle = start or end. White rounded box = a connector to the next
part. White diamond, heavy border = a decision. Light grey rectangle = an
action. Mid grey, dashed border = a rejection. White box with a fine dashed
border = an absence, drawn deliberately.

## Derived from

- `backend/app/api/retrieval.py:292-505` (part 5a)
- `backend/app/services/report_generation_service.py:139-355` (part 5b)
- `backend/app/services/llm_orchestrator.py:56-110` (the retry loop)
- `backend/app/services/report_consistency_service.py:79-110, 292-345`
- `docs/phase22/amendment_01_consistency_status.md` §2(a), §2(e) — `partial`
- `docs/phase22/fix_architecture_v1.2_FROZEN.md` §3.4 — the four states
- `backend/app/services/report_edit_service.py`, `backend/app/api/reports.py`
- `frontend/src/components/report/consistency-state.tsx` — the four renderings
- `docs/phase22/gate_a_results.md` §2 — 17/477 violations
