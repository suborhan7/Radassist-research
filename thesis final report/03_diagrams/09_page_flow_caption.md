# Figure 9 — The page-based UI flow

**Source:** `09_page_flow.mmd` · **Render:** `09_page_flow.png`,
4022 × 3331 px, 300 dpi metadata. Natural size 13.41 × 11.10 in;
**recommended print size 7.85 × 6.50 in** (landscape), at which body text sets
at **7.0 pt** and effective resolution is **512 dpi**.

## What it shows

All 15 frontend routes and how a user moves between them, with the new
**Generate → Report → Evidence** flow at the centre.

**This is a new shape, landed on 2026-09-23 in commit `a8252e09`.** The
workspace used to be a single screen at `/reports/{id}` with a 340 px evidence
sidebar that docked to a 48 px rail. It is now three routes:

| step | route | what it is |
|---|---|---|
| 1 — Generate | `/patients/{id}/upload` | upload → retrieval → questionnaire → generate, one guided flow with a four-step progress display |
| 2 — Report | `/workspace/{reportId}/report` | summary first: impression, recommendation, validation warnings and the consistency verdict all visible without opening anything |
| 3 — Evidence | `/workspace/{reportId}/evidence` | full width, three tabs: Evidence, Agreement, Alternatives |

**Two properties of this flow are asserted by test, not by hope.**

*The no-refetch guarantee.* Next keeps a segment layout mounted while its
children change, so the workspace layout fetches the report **once** and both
pages read the same object. Moving between Report and Evidence fires no
request — not because a cache answers it, but because nothing asks again. The
evidence page fetches nothing at all; every value on it, including the
agreement re-derivation and the stored retrieval-support category, comes off
the report the layout already holds.

*The step bar's honesty.* A step you have reached is a link; the current one
carries `aria-current="step"`; a step you have **not** reached renders as plain
text rather than a disabled link, because there is nothing at the other end of
it and a control that looks clickable and is not is worse than no control.
Every step-bar link routes through `guardedNavigate`, the same unsaved-work
guard the header links carry.

**`/workspace/{reportId}` is a server-side redirect**, not a page, so a deep
link never paints an empty frame before redirecting.

**The print portal lives in the layout, not on the report page** — otherwise
printing would work from only one of the two routes.

**There is no `/profile` route.** Profile and workspace defaults are both on
`/settings`.

The dashed "superseded" box records that all 11 screenshots in
`docs/thesis/figures/ui/` depict the **old** single-screen workspace and are
stale. They are retained deliberately — see `04_figures/` and
`docs/thesis/figures/ui/STALE.md`.

## Derived from

- `frontend/src/app/**/page.tsx` — all 15 routes (enumerated)
- `frontend/src/app/workspace/[reportId]/layout.tsx:19-30` — the no-refetch
  guarantee, in its own words
- `frontend/src/app/workspace/[reportId]/page.tsx` — the server redirect
- `frontend/src/app/workspace/[reportId]/evidence/page.tsx:15-31` — "it fetches
  nothing"
- `frontend/src/components/workspace/workspace-steps.tsx:17-33` — the step-bar
  rule
- `frontend/src/components/layout/app-rail.tsx:125-156` — the global rail
- `frontend/src/components/report/print-portal.tsx`
- `docs/thesis/figures/ui/STALE.md` — the staleness record
- `git log`: commits `a8252e09`, `99f3eab8`
