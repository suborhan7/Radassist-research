# Figure 6 — Sequence: one report generation

**Source:** `06_sequence_generate_report.mmd` · **Render:**
`06_sequence_generate_report.png`, 5672 × 4084 px, 300 dpi metadata. Natural
size 18.91 × 13.61 in; **recommended print size 9.00 × 6.48 in** (full
landscape page), at which body text sets at **5.7 pt** and effective
resolution is **630 dpi**.

## What it shows

A single `POST /generate-report`, from the button press to the report page,
across seven participants: the doctor, the frontend, the API route, the
generation service, SQLite, ChromaDB and Ollama. The numbers after a call are
**the line at which control passes on**, at commit `99f3eab8`.

Three collaborators are drawn as self-calls on the generation service rather
than as their own lifelines, purely so the figure prints legibly:
`ContextBuilder.build()`, `ResponseValidator.validate_semantic()` and
`ReportConsistencyService.check()`. Each is a real, separately injected
service — see Figure 1 and §1.3 of `02_backend/backend_architecture.md`.

## The four things this figure exists to make visible

1. **The sentinel similarity.** `get_by_ids()` is an id fetch with no ranking,
   so it forces distance 0.0 and reports similarity **1.0** for every case.
   Three consumers treated that as a measurement: vote weights collapsed to the
   plain case count (3 cases → "3.00", printed into the prompt), the context
   sort degenerated from similarity order to alphabetical uid order, and the UI
   showed 100.0% on every case. The real numbers were never lost — they sit in
   `retrieved_evidence`, and are restored **keyed by uid, never zipped
   positionally**, because the fetch can return fewer rows than were asked for.

2. **The retry loop, and what it does not record.** Up to two content retries,
   each with a correction prompt carrying the rejected text and the exact
   errors. **The attempt count is never persisted** — decision D5 is open, and
   it blocks D3. Gate A can say 477/477 completed and 0 failed, but cannot say
   how many needed a retry.

3. **The consistency check cannot fail the generation.** Its exception handler
   is deliberately broad and its worst case is three NULL columns and a log
   line: a safety warning that can take down report generation is a net loss,
   because the doctor loses the report entirely instead of receiving one with
   an unchecked caveat. `retry_count` is always 0 — there is no Gate C.

4. **The response cannot disagree with the database.** The consistency block
   returned by `POST /generate-report` is derived from **the values just
   persisted**, not from the `ConsistencyResult` they were built from — so this
   response and a later `GET /reports/{id}` cannot describe the same report
   differently.

Also visible: the top-1 similarity is re-read **from `retrieved_evidence` by
rank**, not taken from the reconstructed cases, precisely because of point 1;
and the disclaimer is server-authored and **replaces** the model's text,
rendered after semantic validation so the validator is never handed a string no
model produced.

## Derived from

- `backend/app/api/generation.py:94-151` — the route and its status mapping
- `backend/app/services/report_generation_service.py:139-355` — the sequence
- `backend/app/services/session_reconstruction.py:27-95` — the sentinel restore
- `backend/app/infrastructure/chroma_store.py:57-82` — why 1.0 is reported
- `backend/app/services/llm_orchestrator.py:56-110` — the loop
- `backend/app/infrastructure/ollama_client.py:51-74` — the actual HTTP call
- `backend/app/services/report_generation_service.py:357-445` — `_run_consistency_check`
- `backend/app/api/dependencies.py:45-74` — cookie auth
- `docs/decisions/decision_log.md` — D5, and that it blocks D3
