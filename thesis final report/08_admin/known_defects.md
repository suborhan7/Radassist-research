# Known defects and limitations

Every entry cites where it is recorded. Entries marked **[observed in this
packet]** were found while capturing `05_screenshots/` on 2026-09-23 and are
new to this document; everything else is carried from an existing repository
record.

Where the repository is silent about a defect's size, this file says
**NOT RECORDED** rather than estimating.

---

## A. Defects in the shipped system

| # | defect | size / evidence | source |
|---|---|---|---|
| A1 | **Consistency warnings are not shown in the UI.** The API returns them and the database stores them; no frontend work was done for them. | all **477** Gate A reports carry a `consistency` block that no interface renders | `CHANGELOG_v1.2.md` §8.1; `gate_a_results.md` §2 |
| A2 | **Transplant threshold not set.** The check scores every report and can emit nothing. | **every** English report reads `partial` for this reason — 477/477 in Gate A | `amendment_01_consistency_status.md` §2(e) |
| A3 | **No consistency retry.** Nothing is corrected; violations are recorded only. | **17/477** Gate A reports carry violations that nothing acted on | `gate_a_results.md` §2 |
| A4 | **The omission defect is uncovered.** Constraint (ii) forbids the impression asserting what findings did not state; it does **not** forbid the impression *omitting* what findings did. No check covers this and no endpoint measures it. | **27/477 (5.7 %)** v1.2 reports state an abnormality in findings and call the study normal in the impression (v1.1: 90/477) | `gate_a_results.md` §6.3 |
| A5 | **Bengali is unchecked end to end.** All three consistency checks are English-only; every evaluation harness generates English only. | **0** Bengali defect rates have ever been measured. A Bengali report stores `checks_run == []` and reads `not_run`. | `gate_a_results.md` §7; `CHANGELOG_v1.2.md` §8.5 |
| A6 | **`ChromaVectorStore` ignores `settings.CHROMA_PERSIST_PATH`.** It carries its own `DEFAULT_PERSIST_PATH` anchored at the repo root, and `main.py:110` constructs it as `ChromaVectorStore()` with **no arguments**, so the setting is never read. **No environment override can redirect the vector store.** | pre-existing at tag `v1.1-evaluated`; **not fixed** (step A6 forbade code changes). Worked around for the noise-floor run by copying the store and verifying the sorted-ID sha256. | `CHANGELOG_v1.2.md` §8.6; `gate_a_results.md` §5; verified present at `backend/app/main.py:110` |
| A7 | **4 stored rows read `clean` when they should read `partial`.** Written by an earlier commit under the pre-amendment rule and never migrated. | **4 of 1,802** rows at the time | `amendment_01_consistency_status.md` §3 |
| A8 | **Validation warnings are not recomputed after doctor edits.** `validation_warnings` is written once at generation time from `validate_semantic()` run against `ai_draft_content`. A later `PATCH /reports/{id}` can change `final_content` without the warnings changing, so **a stored warning always describes the AI draft, never the doctor's edited text.** | by design, not a regression — but a reader of a finalized report sees warnings about text that may no longer exist | `decision_log.md`, "Related audit decisions" (*source: project chat log, 2026-08-17*) |
| A9 | **Validation warnings are hardcoded English and are never translated.** `response_validator.py:70` and `:74` build the strings with f-strings; they are persisted verbatim and rendered verbatim. **[observed in this packet]** — `05_screenshots/27-report-bengali-dark.png` shows *"Top voted label 'Normal' (agreement 0.60) not reflected in report text"* on an otherwise fully Bengali screen. | affects **every** non-English report carrying a warning; count **NOT RECORDED** | verified at `backend/app/services/response_validator.py:70,74`; no translation path exists in `frontend/src/components/report/` |
| A10 | **CORS allows exactly one origin.** `allow_origins=[settings.CORS_ALLOWED_ORIGINS]` (`main.py:254`) wraps a single string in a one-element list, defaulting to `http://localhost:3000`. On any other frontend port every POST preflight returns **400** and the UI shows "Failed to load report." **[observed in this packet]** — hit for real on the first screenshot pass. | a deployment/config constraint, not a data defect; documented as out of scope ("packaging/CORS-for-production is explicitly out of scope", `config.py:105`) | verified at `backend/app/core/config.py:108`, `backend/app/main.py:254` |
| A11 | **The comparison view renders a negative interval.** Passing a report dated *later* than the current study as `?against=` produces "**-2 DAYS APART**"; the UI neither reorders nor rejects it. **[observed in this packet]** — see `05_screenshots/24-compare-dark.png`. Note the packet's own capture chose that ordering, so this is a **missing guard**, not a mis-computation. | `days_between_studies` is returned signed by `ComparisonService`; no UI guard exists | observed 2026-09-23; **not previously recorded anywhere in the repository** |

---

## B. Defects in the instruments (they bound what any result can mean)

| # | defect | size / evidence | source |
|---|---|---|---|
| B1 | **CheXbert has a negation bug on this corpus.** *"No acute, displaced rib fractures"* is labelled `Fracture = Positive`. | **5 of 18** cases inspected in the Phase 20 Fracture investigation | `diagnosis.md` §2c; `development_log.md`, Fracture finding §1c |
| B2 | **BERTScore does not discriminate on this corpus.** Findings F1 **0.8420** against a random mismatched-pairs baseline of **0.8403**. | fails its own pre-registered validity bar; **Tier 2 must not be reported as a quality result** | `phase20_generation.md`; `tier2_bertscore_random_baseline.csv` |
| B3 | **Temporal-term counts are lexical, not adjudicated.** Word-boundary regex; "stable" has a non-temporal clinical sense. | measured precision **95 %** on a 20-case audit at a stated seed | `diagnosis.md` §5.3 |
| B4 | **micro-F1 is unusable as a between-arm metric on this dataset** — it is dominated by `No Finding`. | Phase 21 arms B and A score *higher* micro-F1 than C while scoring far lower macro-F1 | `phase21_ablation_architecture.md` §6.8 |
| B5 | **Most labels have too little support to estimate anything.** | Gate A: **7 of 14** labels have support < 10. Phase 23 dev: **13 of 14** below 10, and **10 labels score 0.000 for every variant**. | `gate_a_results.md` §6.1b; `dev_results.md` §6 |
| B6 | **`declared_projection` is a harness constant (`"PA"`)** in the evaluation runs, not per-case dataset truth. | every evaluation number is conditioned on a declared projection that was not verified per case | `generation_arm_full_n477/evaluation_config.json` |
| B7 | **Generation is materially non-deterministic at temperature 0.0, seed 42.** | **67/100 (67 %)** of outputs were not byte-identical on re-run of identical code against a byte-verified identical collection | `gate_a_results.md` §5 |

---

## C. Defects in the record itself

| # | defect | source |
|---|---|---|
| C1 | **A real pre-registration defect.** The frozen v1.2 document supports **two incompatible definitions** of its own primary endpoint — §3.1 names three sections and nine terms, while its stated baseline (line 734) was computed over five terms and two sections. The run plan fixed the wider one without noticing. **Both are reported; the verdict is identical either way.** | `gate_a_results.md` §3.1.1 |
| C2 | **D2, D3 and D5 have no full text in the repository.** Their summaries come from the 2026-08-17 audit conversation. **Any thesis text relying on them must cite the project chat log with its date, not a repository document.** | `decision_log.md`, "Open items" |
| C3 | **Decision numbering is unverified.** Whether `D1`–`D5` is the complete set, or whether further unnumbered decisions exist, **has not been established**. | `decision_log.md`, "Open items" |
| C4 | **Transplant rate is NOT COMPUTABLE for Phase 20.** Its `per_case_results.csv` has no `retrieved_uids` column and the neighbour identities were never persisted. **No substitute number is offered.** | `diagnosis.md` §2a |
| C5 | **Phase 21's RQ3 per-stage latency profile was never produced.** §7 specifies `ml/outputs/evaluation/latency/latency_summary.csv`; **that directory does not exist.** | verified absent 2026-09-23; spec at `phase21_ablation_architecture.md` §7 |
| C6 | **The UI screenshot set in `docs/thesis/figures/ui/` is stale** — all 11 PNGs depict the superseded single-screen workspace. Replaced by `05_screenshots/`. | `docs/thesis/figures/ui/STALE.md` |
| C7 | **`README.md` and `CLAUDE.md` both describe a layout that no longer matches the repository.** `CLAUDE.md` states "Only `ml/`, `shared/`, and `docs/` exist in this copy" and "there is no `backend/`, `frontend/`"; **all three exist**, along with `e2e/`. `README.md` describes a flat `scripts/` + `config/` root. | verified 2026-09-23; drift noted for `README.md` in `CLAUDE.md` itself |
| C8 | **Not merged to `main`.** | `CHANGELOG_v1.2.md` §8.12 |

---

## D. Scope limitations (by design, not failures)

- **Frontal chest radiographs only** (DR-4). Lateral views are rejected at
  admission. No MRI, no CT.
- **The BMDC number is recorded as entered and never verified.** The
  registration form states this itself: *"This system has no access to the BMDC
  registry and cannot verify it."*
- **Browser print only.** There is no server-side PDF generation.
- **SQLite, single process, local deployment.** Postgres is described as "a
  deployment decision for later" (`config.py`).
- **The system is a clinical decision-support tool, not a diagnostic
  authority.** Every report carries a provenance line saying so.
