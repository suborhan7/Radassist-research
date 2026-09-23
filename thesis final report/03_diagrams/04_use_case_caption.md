# Figure 4 — Use cases, as actually implemented

**Source:** `04_use_case.mmd` · **Render:** `04_use_case.png`,
3684 × 3756 px, 300 dpi metadata. Natural size 12.28 × 12.52 in;
**recommended print size 6.5 × 6.62 in**, at which body text sets at
**6.4 pt** and effective resolution is **567 dpi**.

## What it shows

Every use case the system really supports, grouped into six areas, and the
actors that participate in them.

**There is exactly one human actor.** This is the figure's most important
claim, and it is a negative one. The `doctors` table has columns for
`id, email, password_hash, full_name, created_at, bmdc_number` and five
`default_*` workspace preferences — **and no role column**
(`backend/app/models/doctor.py:32-42`). A repository-wide search for a role
field in the doctor model and the domain entity returns nothing. There is
therefore no administrator, no radiographer, no reviewer and no institutional
actor in this system, and **none has been invented for this diagram.**

**Access control is ownership, not role.** Edit, finalize, delete and
regenerate all funnel through one four-line function
(`report_edit_service.py:101-104`), and a report whose `doctor_id` is NULL
fails closed — it is editable by nobody. Reading is deliberately *not*
ownership-gated: any authenticated doctor may read any report, which is why
"read another doctor's report, read-only" appears as a real use case rather
than being omitted.

**Ollama and ChromaDB are drawn as secondary actors** because the examination
and downstream groups cannot complete without them, and the system's behaviour
when either is unavailable is a documented, distinct outcome (502 for Ollama;
ChromaDB's absence prevents startup entirely).

The second note box lists what is **not** drawn and why, so a reader cannot
mistake absence for oversight.

## Greyscale key

Heavy-bordered white circle = the human actor. Dashed grey circle = a secondary
(system) actor. Light grey stadium = a use case. Dashed-border white box = a
note. Dotted arrows carry `includes` and `extends` relationships.

## Derived from

- `backend/app/models/doctor.py:32-42` — the absence of a role column
- `backend/app/services/report_edit_service.py:101-104` — `_check_ownership`
- `backend/app/api/` — all 26 operations, one use case per user-reachable action
- `frontend/src/app/**/page.tsx` — 15 routes, confirming each use case has a UI
- `frontend/src/components/layout/app-rail.tsx:125-156` — the navigation set
- `backend/app/domain/entities.py:60-74` — patients are institutional, not owned
- `thesis final report/01_facts/feature_catalogue.md` — the implemented /
  not-implemented determination behind every box
