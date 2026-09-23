# Phase 0 — retrieval encoder bake-off, and Gate B calibration

**Never pool with any other phase.**

## 1. The bake-off

| | |
|---|---|
| **Question** | Does BiomedCLIP retrieve clinically similar chest-X-ray cases well enough to make retrieval-augmented generation viable? |
| **Method** | Image→image retrieval — the fair common denominator across BiomedCLIP, generic CLIP and DenseNet121, since only BiomedCLIP has a shared image/text space. KB = train split; queries = val split; relevance = curated-label overlap, graded. Decision layer is class-stratified **paired bootstrap** CIs, because Normal ≈ 47% of the data makes micro metrics and pooled resampling deceptively favourable. |
| **n** | val split as queries against the train-split KB |
| **Source** | `ml/outputs/evaluation/encoder_comparison_macro.csv`, `gate_decision_table.csv` |

### 1.1 Point estimates — macro

| encoder | MRR | R@1 | R@5 | R@10 | nDCG@10 |
|---|---|---|---|---|---|
| **biomedclip** | **0.4238** | **0.2826** | **0.5875** | 0.7422 | **0.1745** |
| clip_generic | 0.3091 | 0.1304 | 0.5227 | 0.6831 | 0.1140 |
| densenet121 | 0.3511 | 0.1806 | 0.5127 | 0.6808 | 0.1324 |
| random | 0.3237 | 0.1627 | 0.5155 | 0.6995 | 0.1021 |

### 1.2 The pre-registered gates

| gate | comparison | metric | Δ | 95% CI | excludes 0 | verdict |
|---|---|---|---|---|---|---|
| 1 | biomedclip − random | recall@5 | +0.0716 | [0.0204, 0.1236] | **yes** | **PASS** |
| 1 | biomedclip − random | nDCG@10 | +0.0726 | [0.0510, 0.0952] | **yes** | **PASS** |
| 2 | biomedclip − clip_generic | recall@5 | +0.0639 | [−0.0065, 0.1336] | **no** | **INCONCLUSIVE** |
| 2 | biomedclip − clip_generic | nDCG@10 | +0.0604 | [0.0394, 0.0817] | **yes** | **PASS** |
| 3 | wins concentrate on real findings | — | 11 of 15 real-finding classes | — | — | **SATISFIED** |

**Verdict: BiomedCLIP adopted and frozen as the encoder.** Gate 1 passed
cleanly, Gate 2 passed on nDCG@10 but **was inconclusive on Recall@5 at this
sample size**, and Gate 3 was satisfied. The thesis must report Gate 2's
Recall@5 as inconclusive, not as a pass.

### 1.3 How good the proxy itself is

A manual relevance check against hand-read judgement put the label-overlap
proxy at **89% precise / 49% recall**. It is therefore a **conservative lower
bound**: the Phase 0 numbers likely *understate* true retrieval quality.
Source: `CLAUDE.md`, "Validated results so far".

---

## 2. Gate B calibration (architecture v1.1)

| | |
|---|---|
| **Question** | What threshold values does the admission and projection gate need? |
| **Method** | 600-study calibration set, 300 frontal and 300 lateral. Each selection rule was written down **before** the resulting value was computed. |
| **n** | 300 per projection |
| **Source** | `ml/outputs/calibration/v1_1_gate_b_selected_values.csv`, `top1_similarity_by_label.csv` |

| setting | value | rule | result | status |
|---|---|---|---|---|
| `MODALITY_THRESHOLD` | **0.60** | false-negative budget 0.02, stated before results were read | frontal FNR **0.0000** at n=300; 0.82 considered and declined | pre-registered |
| `PROJECTION_REJECT_THRESHOLD` | **0.8695459** in the CSV | midpoint of the observed separation gap (lateral max 0.8484709, frontal min 0.8906209; gap 0.0421) | 300/300 lateral rejected, 0/300 frontal rejected | pre-registered, **then superseded** |
| `PROJECTION_REJECT_THRESHOLD` | **0.8500** in `config.py:404` | *"just above the observed lateral maximum"* | re-verified on the same 600-study set: **300/300 lateral rejected, 0/300 frontal rejected** | **POST-HOC, revised 2026-08-19** |
| `RETRIEVAL_FLOOR` | **0.8906208872795105** | 0th percentile of the frontal set — the only lower-tail percentile that puts the boundary at the edge of the observed band rather than inside it | **0 of 300 fall below it — the mechanism is UNEXERCISED** | pre-registered |

### 2.1 The revision, stated as the thesis must state it

The projection threshold's *selection rule* was changed **after seeing a
failing image**: a genuine frontal chest radiograph from outside the IU dataset
scored top-1 **0.8582** and was rejected as a projection mismatch. It sits
above every lateral in the calibration set and below the old midpoint — inside
the empty gap the midpoint rule had placed the boundary in the middle of.

The repository records this openly rather than presenting it as
pre-registered: `backend/app/core/config.py:364-403` says so in capitals. The
defence offered is that the calibration population was IU-only, that no
observation of any kind lies between 0.84847 and 0.89062, and that moving the
boundary to the edge of what was observed **removes an unmeasured margin
rather than adding one**.

**It remains an observed separation point, not a validated frontal/lateral
boundary** — 300 images of each projection from one dataset.

## 3. What Phase 0 does not establish

- It does not measure generation quality. That is Phase 20.
- It does not establish that retrieval helps generation. That is Phase 21, and
  its primary endpoint **did not clear**.
- The Recall@5 comparison against generic CLIP remains open.
