# Workspace UI — summary-first report panel and collapsible evidence sidebar

Captured 2026-09-23 from the **running app** (real backend, real reports from a
disposable copy of `dev.db`), not from mockups. Viewport is exactly 1440×900,
pinned with `Emulation.setDeviceMetricsOverride` rather than a window size, so
the whole reading station is in frame with no dead band.

**The two themes are different palettes, not one inverted.** Dark is the
original "Reading Room" cyan-on-near-black, which the product was designed for.
Light is derived from the Orthoc medical template and reads green — its hue,
its white-card-on-tinted-page surfaces and its button pattern (solid fill
inverting to an outline on hover). Orthoc's own colour values fail WCAG AA in
six of eight text pairs, so the hue is Orthoc's and the luminance is this
project's; the derivation and all 27 measured pairs are recorded in
`frontend/src/styles/tokens.css`.

Regenerate with:

```bash
# 1. backend against a DISPOSABLE copy -- never dev.db
cp backend/dev.db "$TMP/shots.db"
DATABASE_URL="sqlite:///$TMP/shots.db" .venv/Scripts/python -m uvicorn app.main:app --port 8011

# 2. frontend on :3000 (the backend's only CORS origin -- see
#    core/config.py DEFAULT_CORS_ALLOWED_ORIGINS)
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8011 npx next dev -p 3000

# 3. capture
E2E_API=http://localhost:8011 E2E_FRONTEND=http://localhost:3000 \
SHOT_EMAIL=... SHOT_PASSWORD=... \
SHOT_REPORT=<clean report id> SHOT_REPORT_WARN=<report with validation warnings> \
E2E_OUT=docs/thesis/figures/ui node e2e/ui-shots.mjs
```

`e2e/ui-shots.mjs` picks no database. It drives whatever backend `E2E_API`
names, and the caller is responsible for having pointed that backend at a
disposable copy — the same fail-closed discipline as the rest of `e2e/`.

## What each frame shows

| file | state | what it is evidence of |
|---|---|---|
| `{dark,light}-1-summary.png` | default, collapsed | The impression, the recommendation, the validation block and the consistency verdict are all visible without opening anything. The full report sits behind one control, labelled with what is inside it. |
| `{dark,light}-2-full-report-expanded.png` | disclosure open | Examination, Clinical History, Technique, Findings and Disclaimer, with the control now reading "Hide full report". |
| `{dark,light}-3-sidebar-expanded.png` | evidence panel open | Reached by clicking the docked rail. Evidence prose is set in the same 16px/1.6 body token as the report column. |
| `{dark,light}-4-sidebar-collapsed.png` | evidence panel docked — **the default** | The panel collapses to a 48px rail that still carries its reopen control, and the report column widens from 530px to 700px. Body text does **not** stretch edge to edge — it stays capped at the 74ch measure. |
| `{dark,light}-5-warnings-full-report-collapsed.png` | warnings present, report collapsed | **The frame that matters most.** Three validation warnings and a `partial` consistency verdict are both fully visible while the full report is still collapsed. Nothing a doctor must act on is behind a disclosure. |

## The two reports used

Both are real rows, chosen rather than constructed, and between them they cover
two of the four consistency states:

- **clean report** — `consistency_checks_run` is NULL, a pre-v1.2 row, so the
  block reads **not run** with the reason "No consistency checks were recorded
  for this report."
- **warning report** — `checks_run = ["temporal", "contradiction"]`, a strict
  subset of the applicable set, so the block reads **partial**: "Ran: temporal,
  contradiction. Not run: transplant." This is the state
  [`amendment_01_consistency_status.md`](../../../phase22/amendment_01_consistency_status.md)
  §2(e) says every English report is in until Gate B calibrates the transplant
  threshold.

The other two states (`clean`, `violations`) have no such row in this database
and are proven by component test instead
(`frontend/src/components/report/consistency-state.test.tsx`), rather than
staged by writing rows that no run produced.
