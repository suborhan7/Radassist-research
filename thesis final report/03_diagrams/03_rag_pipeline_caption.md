# Figure 3 — The retrieval-augmented generation pipeline

**Source:** `03_rag_pipeline.mmd` · **Render:** `03_rag_pipeline.png`,
1428 × 5041 px, 300 dpi metadata. Natural size 4.76 × 16.80 in;
**recommended print size 2.55 × 9.00 in** (a tall column set beside body text),
at which body text sets at **6.4 pt** and effective resolution is **563 dpi**.

## What it shows

The RAG path specifically, and in particular the three questions a reader will
ask: **what is retrieved, what is passed to the model, and what is checked
afterwards.**

**What is retrieved.** Five neighbour studies from a ChromaDB collection of
**2,462 documents that is the train split only**. The split is
leakage-controlled twice over: at study level (one row per uid, defeating
view-pair leakage) and by near-duplicate clustering over normalised report
text, with clusters as the atomic split unit — about 28% of studies sit in
such a cluster. A query case can therefore never retrieve itself, nor its own
near-duplicate.

**What is passed to the model.** The node labelled *WHAT THE MODEL GETS* is the
one that matters most, because it is the most common misreading of a system
like this. The prompt carries the five neighbours' **findings and impression
text** plus the voted labels. **The image itself never reaches the language
model.** Generation is text-only; the image's entire contribution is the
512-dimensional vector that chose those five neighbours. The v1.2 prompt peaks
at **1,574 tokens of a 4,096 window**, so the evidence block is never
truncated.

**What is checked afterwards — and the honest answer is: nothing that blocks.**

| check | status |
|---|---|
| structural (7 markers) | the **only** one that can stop a report: 2 content retries, then 422 |
| semantic validation | **advisory** — produces warnings, gates nothing (Phase 8 Decision 1) |
| temporal | observational |
| transplant | **computes its scores and emits no violation** — no Gate B threshold has been calibrated, which is why no English report can currently read `clean` |
| contradiction (CheXbert) | observational |
| disclaimer | not a check — the server **replaces** the model's disclaimer text |

`retry_count` is drawn as **0** because there is no Gate C: a recorded
violation is acted on by nothing. Gate A recorded 17 violations in 477 reports
and every one of them changed nothing.

## Greyscale key

As Figure 2. The double-bordered box is the language model. The dashed edges
leaving the structural decision are the retry and the failure path.

## Derived from

- `backend/app/services/report_generation_service.py:160-355`
- `backend/app/services/context_builder.py:49-212`
- `backend/app/services/prompt_builder.py:168-206` — the nine sections, in order
- `backend/app/services/llm_orchestrator.py:56-110` — both retry budgets
- `backend/app/services/structural_validator.py`
- `backend/app/services/response_validator.py:6-10` — the advisory rule
- `backend/app/services/report_consistency_service.py`
- `backend/app/main.py:233-241` — why the transplant threshold is absent
- `ml/preprocessing/make_splits.py`; `CLAUDE.md`, leakage-safe splitting
- `docs/methodology/development_log.md` step A5 — the prompt-token measurement
- `docs/phase22/gate_a_results.md` — 477/477 completed, 17 violations
