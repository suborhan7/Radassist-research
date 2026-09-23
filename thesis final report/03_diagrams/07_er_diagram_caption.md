# Figure 7 — Entity relationships, after the latest migration (two parts)

The schema is **nine tables rendered as two figures**, because one rendering
prints at under 4 pt. Together they are the whole schema as it exists after
alembic head **`7f2a91c4d6e8`**.

| part | file | tables | render | recommended print | body pt |
|---|---|---|---|---|---|
| **7a** | `07_er_diagram.png` | the report lifecycle core: `doctors`, `patients`, `retrieval_sessions`, `retrieved_evidence`, `reports` | 3500 × 5113 px | 6.16 × 9.00 in | **6.3 pt** |
| **7b** | `07b_er_diagram_satellites.png` | the four satellites: `comparisons`, `explanations`, `report_audit_log`, `upload_rejection_log` | 5100 × 1647 px | 9.00 × 2.90 in | **6.4 pt** |

Both carry 300 dpi metadata; effective resolution at the recommended sizes is
568 and 567 dpi. In 7b the three core tables are repeated with their key
columns only, as join anchors.

## What they show

The schema as it is, not as it was designed. Three properties are worth
pointing a reader at.

**1. `doctor_id` is nullable on every work table.** Each of those columns was
added by a later migration to a table that already held rows, and **no backfill
was performed**. That is why `_check_ownership` treats a NULL owner as "owned
by nobody, editable by nobody" rather than as an error.

**2. `retrieved_evidence.similarity` is the only place the real ranked
similarity survives.** Re-fetching a case from ChromaDB by id returns a
sentinel 1.0, so this column is not a cache of something re-derivable — it is
the measurement. See Figure 6.

**3. NULL and `[]` mean different things in the three consistency columns**,
and migration `7f2a91c4d6e8` made them nullable specifically to preserve that:

| state | `consistency_violations` | `consistency_checks_run` |
|---|---|---|
| checks ran (English) | `[...]`, possibly empty | `[...]` |
| zero checks applicable (non-English) | **NULL** | `[]` |
| the checker raised | NULL | NULL |

Writing `[]` for violations on a Bengali report would assert it was examined
and found clean — the false assurance the frozen architecture forbids.

**Three column groups are collapsed in 7a for legibility**, marked as such:
`llm_model` + `llm_temperature`; `embedding_model` + `embedding_version` +
`collection_name`; `created_at` + `updated_at`. `reports` has **26 columns** in
total.

## Which migration added what

| # | revision | added |
|---|---|---|
| 1 | `e60f9520da7b` | `retrieval_sessions`, `retrieved_evidence` |
| 2 | `e8d3a5a73568` | `reports` |
| 3 | `719b6078d895` | `explanations` |
| 4 | `96e0dd80c317` | `patients`; `retrieval_sessions.patient_id` |
| 5 | `fc0fc7f35ef5` | `comparisons` |
| 6 | `8550fea2771a` | `doctors` |
| 7 | `11971c2c9396` | `retrieval_sessions.doctor_id` |
| 8 | `689ad1cf33f4` | `comparisons.doctor_id` |
| 9 | `93de8accdb66` | `explanations.doctor_id` |
| 10 | `4da4e9df3c23` | `doctors.bmdc_number` + five `default_*` columns |
| 11 | `d8ff7f78ff6a` | finalize/edit columns on `reports` |
| 12 | `528c741665ee` | `questionnaire_answers`, `clinical_notes` |
| 13 | `a1f4c72b9e30` | `retrieval_support`, `top1_similarity`; `upload_rejection_log` |
| 14 | `c3d81b6a4f27` | `voted_labels`, `agreement` (**decision D4**) |
| 15 | `7f2a91c4d6e8` | the three consistency columns (**head**) |

**One gap, recorded rather than smoothed over:** `report_audit_log` is defined
in `backend/app/models/report_audit_log.py` but appears as a `create_table` in
**none** of the 15 revisions. How the live table came to exist is
**NOT RECORDED**.

## Derived from

- `backend/app/models/*.py` — all nine table definitions and every column type
- `backend/alembic/versions/*.py` — the 15 revisions and their `down_revision`
  chain, read to establish the order above
- `backend/app/services/report_generation_service.py:369-390` — the NULL vs `[]`
  rule
- `backend/app/services/session_reconstruction.py:63-91` — why `similarity` is
  load-bearing
- `docs/decisions/decision_log.md` — D4
