# Figure 2 — The machine-learning pipeline

**Source:** `02_ml_pipeline.mmd` · **Render:** `02_ml_pipeline.png`,
3659 × 4931 px, 300 dpi metadata. Natural size 12.20 × 16.44 in;
**recommended print size 6.5 × 8.76 in** (full portrait page), at which body
text sets at **6.4 pt** and effective resolution is **563 dpi**.

## What it shows

The machine-learning path end to end: an uploaded image, through admission,
PHI masking, the BiomedCLIP encoder, the vector store, k-NN retrieval and
label voting, to the three things the rest of the system consumes.

**Every number in the figure is the real configured value**, not an
illustration:

| shown | value | where it is defined |
|---|---|---|
| embedding dimension | **512** | `development_log.md:451` |
| encoder | BiomedCLIP `PubMedBERT_256-vit_base_patch16_224` | `shared/embeddings/biomedclip_embedder.py:38` |
| PHI mask area cap | **0.08** | `config.py:325` |
| modality threshold | **0.60** | `config.py:350` |
| projection reject threshold | **0.8500** | `config.py:404` |
| retrieval floor | **0.8906208872795105** | `config.py:435` |
| `top_k` | **5** | `api/retrieval.py:296` |
| collection size | **2,462** | live `collection.count()` |

**Three things the figure is careful about.**

1. **The order is `admit → mask → embed → gate → retrieve`** (decision D1). The
   embedding is computed from the **masked** pixels, so the vector the gate
   judges is derived from what the system is willing to store. Masking used to
   run last; Phase 1 measured the embedding impact of masking at mean cosine
   **0.992** (0 of 50 flagged), which is why the reorder is safe.
2. **Two thresholds, not one** (decision DR-5). The reject threshold blocks;
   the retrieval floor only sets a category and never blocks. Collapsing them
   into one value would delete the middle band that the disclaimer, the
   `retrieval_support` column and the support matrix all depend on.
3. **0.8500 is marked as a post-hoc value in the figure itself.** Its selection
   rule was changed on 2026-08-19 after a real out-of-distribution frontal
   scored 0.8582 and was wrongly rejected. It must not be presented as a
   pre-registered choice.

A fourth point the figure records by omission: **`RETRIEVAL_FLOOR`'s
low-support branch was never exercised in calibration** — 0 of 300 frontal
cases fell below it.

## Greyscale key

White diamond, heavy border = a decision. Light grey rectangle = a processing
step. Mid grey = the model. Cylinder = a store. **Mid grey with a dashed border,
reached by a dashed edge = a rejection path.** Rounded white = data passing
between stages.

## Derived from

- `backend/app/api/retrieval.py:292-505` — the whole endpoint, in order
- `backend/app/services/image_admission_service.py:147-310` — A1 to A17
- `backend/app/services/modality_gate_service.py:116-244` — M1 to M12
- `backend/app/services/retrieval_service.py`, `services/similarity_search.py`
- `backend/app/services/label_voting_service.py:24-44` — the vote formula
- `backend/app/core/config.py` — every threshold, at the lines tabled above
- `shared/phi_masking/masker.py`
- `docs/methodology/input_admission_projection_gate_architecture_v1.1_FROZEN.md`
- `ml/outputs/calibration/v1_1_gate_b_selected_values.csv` — the calibration
