# Phase 23 — Accuracy improvement experiment: pre-registration

> **This document is written and committed BEFORE any variant has been run.**
> Nothing below was chosen after seeing a result. The selection rule in §4 is
> mechanical: applied to the dev numbers it returns exactly one winner with no
> further judgement, and it can return V0 (do nothing), in which case Step 3 is
> not run at all.
>
> Branch `phase23-accuracy`, cut from `phase22-v1.2` at `7d3a8bc8`.

---

## 1. What this phase asks

Phase 22 v1.2 fixed a **grounding** failure: temporal language with no prior
study, transplanted impressions, self-contradiction. It did not set out to make
the reports more **clinically accurate**, and the Gate A numbers show that
plainly — impression CheXbert macro-F1 moved +0.0224 with a CI of
[−0.0266, +0.0683] that includes zero
([`gate_a_results.md`](../phase22/gate_a_results.md) §3). The post-hoc analysis
showed the micro-F1 gain that *did* clear was largely `No Finding`, while
Pneumonia recall fell from 0.150 to 0.050 (§6.2).

Phase 23 asks a different question: **can the labelled accuracy of the
impression be improved, and if so by what?** Two candidate levers are tested,
separately and together.

## 2. Dev set — 150 validation cases

**The test pool is not touched until Step 3.** All variant selection happens on
a dev set drawn from the **validation split only**.

### 2.1 Eligibility rule

Identical to the rule that produced the 477 test cases, with `split == "val"`
substituted for `split == "test"` and nothing else changed. The rule is
`build_eligible_pool` in
[`ml/evaluation/run_generation_eval.py:131-154`](../../ml/evaluation/run_generation_eval.py#L131-L154):

```
split match  AND  has_frontal == True  AND  real findings_clean  AND  real impression_clean
```

where *real* means not-null, not empty after strip, and not the literal string
`"nan"`.

### 2.2 Sample

| | |
|---|---|
| eligible **val** pool | **490** |
| eligible **test** pool (re-derived, for comparison) | **477** — matches Phase 21/22 exactly |
| dev sample | **150**, `pandas.DataFrame.sample(n=150, random_state=20260923)` |
| unique uids | 150 |
| uid list | [`scratch/phase23/dev_uids_150.csv`](../../scratch/phase23/dev_uids_150.csv) |

The eligible test pool re-deriving to exactly 477 is the check that the rule
was transplanted correctly rather than merely producing *a* number.

### 2.3 Zero-overlap proof

Produced by [`scratch/phase23/build_dev_set.py`](../../scratch/phase23/build_dev_set.py),
real output:

```
eligible TEST pool  : 477   (Phase 21/22 used 477)
eligible VAL  pool  : 490

dev set sampled     : 150 (seed 20260923)
unique uids         : 150

OVERLAP vs test pool (477 uids): 0
OVERLAP vs the 477 GENERATED uids (477): 0
OVERLAP vs Gate A v1.2 uids (477): 0

KB collection       : 2462 documents
OVERLAP vs KB ids   : 0
dev uids not in val split: 0  []
```

Four separate disjointness checks, all zero:

| check | against | result |
|---|---|---|
| eligible test pool | 477 uids | **0** |
| the uids actually generated in Phase 21 Arm C | `generation_arm_full_n477/per_case_results.csv` | **0** |
| the uids actually generated in Phase 22 Gate A v1.2 | `generation_v1.2_gateA_n477/per_case_results.csv` | **0** |
| the retrieval knowledge base | ChromaDB `iu_cxr_biomedclip_v1_train`, 2462 docs | **0** |

Plus a positive control: **0** of the 150 dev uids fall outside the `val`
split.

The KB check matters most. The knowledge base is the **train** split only, so a
dev case is never retrieved as its own neighbour — the same leakage property
the test pool has. Splits are leakage-controlled at study level and by
near-duplicate clustering with clusters as the atomic unit
(`ml/preprocessing/make_splits.py`), so a dev case's near-duplicates are also
not in the KB.

### 2.4 What the dev set is and is not

It **is** the surface on which all four variants are compared and the winner
chosen. It **is not** a second test set: whatever wins, its dev numbers are
selection numbers, quoted as such, and are expected to be optimistic. The
Step 3 test numbers are the ones that get reported as results.

---

## 3. Variants

All four run through the same harness, the same retrieval, the same KB, the
same scoring path. Only the stated thing changes.

| id | model | prompt | change vs V0 |
|---|---|---|---|
| **V0** | llama3:8b | v1.2 as-is | none — the incumbent, re-run on dev for a same-conditions baseline |
| **V1** | **qwen2.5:14b** | v1.2 as-is | model only |
| **V2** | llama3:8b | v1.2 + label checklist | prompt only |
| **V3** | **qwen2.5:14b** | v1.2 + label checklist | both |

V0 is re-run rather than reusing Gate A numbers, because Gate A ran on test
uids and these are dev uids. Comparing a dev variant against a test baseline
would be the exact confound this phase exists to avoid.

### 3.1 V1 / V3 — the model swap

`OLLAMA_MODEL` is **already a Settings field**, so this needs no code change:

- `backend/app/core/config.py:51` — `DEFAULT_OLLAMA_MODEL = "llama3:8b"`
- `backend/app/core/config.py:429` — `OLLAMA_MODEL: str = DEFAULT_OLLAMA_MODEL`
- `backend/app/infrastructure/ollama_client.py:38` — `model: str = settings.OLLAMA_MODEL`

The config file already frames the model as tunable: *"a documented config-value
swap to what's actually available locally, not an architecture change, per the
frozen spec's own framing of the model choice as tunable config"*
(`config.py:45-49`).

**One caveat recorded now, not after it bites.** `OllamaClient.__init__` takes
`settings.OLLAMA_MODEL` as a *default argument value*, which Python binds once
at import time, and `main.py:187` constructs `OllamaClient()` with no arguments.
So the env var must be set **before the server process starts**, and cannot be
changed on a running server. The harness therefore launches a **fresh backend
per variant**. This is the same shape of latent defect as
`ChromaVectorStore` ignoring `settings.CHROMA_PERSIST_PATH`
(`thesis_facts.md` §5 defect 6); it is recorded here but **not fixed in this
phase**, because changing DI wiring mid-experiment would make V0 not-v1.2.

**Exact tag and digest** — pulled at Step 0 specifically so this document can
name it rather than promise it:

#### 3.1.1 qwen2.5:14b, as pulled

`ollama pull qwen2.5:14b`, completed 2026-09-22 before this document was
committed, so the tag and digest below are read off the machine rather than
promised.

| | |
|---|---|
| tag | `qwen2.5:14b` |
| digest (short) | `7cdf5a0187d5` |
| digest (full) | `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6` |
| parameters | 14.8B |
| quantization | **Q4_K_M** (llama3:8b is Q4_0 — not the same quantisation scheme) |
| format | gguf |
| on-disk size | 9.0 GB |
| model context length | 32768 (llama3:8b: 8192) |
| embedding length | 5120 (llama3:8b: 4096) |
| licence | **Apache License 2.0** — materially more permissive than llama3's META LLAMA 3 COMMUNITY LICENSE |
| ollama | 0.34.2 |

Source: `ollama list`, `ollama show qwen2.5:14b`, and
`GET http://localhost:11434/api/tags`.

**Three differences recorded now so they are not mistaken for findings later:**

1. **`num_ctx` stays 4096** for both models (`config.py`), so qwen's larger
   native context window is not used. Prompt tokens max at 1,574 of 4,096
   (`development_log.md` A5), well inside both. The window is not the variable
   under test.
2. **Quantisation differs** (Q4_K_M vs Q4_0). V1 and V3 therefore test
   "qwen2.5:14b as ollama ships it", not a controlled parameter-count
   comparison. Any V1 win is attributable to the model *as deployed*, which is
   the practical question, but it is **not** evidence that 14B beats 8B at
   equal quantisation.
3. **qwen ships a default system prompt** (*"You are Qwen, created by Alibaba
   Cloud. You are a helpful assistant."*). Whether ollama applies it under
   `/api/generate` with an explicit prompt must be checked at Step 1 and
   reported; if it is applied, it is an uncontrolled prompt difference between
   V0/V2 and V1/V3 and must be stated as such in the results.

### 3.2 V2 / V3 — the label checklist

A new prompt block, built in `prompt_builder.py`, behind a Settings flag
defaulting **OFF** so V0 and V1 are byte-identical to v1.2.

For each voted label whose `agreement` is at or above the existing agreement
threshold, the block instructs the model to **either** state that label as
present *only if it is consistent with this image's evidence*, **or** explicitly
negate it. It additionally requires that **every abnormality stated in FINDINGS
appears in the IMPRESSION**.

The second half targets a defect Phase 22 measured and fixed nothing about:
**27 of 477 v1.2 reports state an abnormality in findings and call the study
normal in the impression** (`gate_a_results.md` §6.3, defect 4 in
`thesis_facts.md` §5). That is an accuracy defect, and it is in scope here.

**Agreement threshold — source, and a coupling flagged before it is used.**
There are two 0.5 thresholds in the codebase and the code says explicitly that
they are not the same knob:

- `backend/app/services/response_validator.py:29` — `TOP_LABEL_AGREEMENT_THRESHOLD = 0.5`, gates a validation warning.
- `backend/app/core/config.py:417` — `DEFAULT_DISCLAIMER_AGREEMENT_THRESHOLD = 0.5`, selects a disclaimer cell. Its comment: *"the two are deliberately the same number today, but they answer different questions ... and nothing requires them to move together."*

This phase uses **`settings.DISCLAIMER_AGREEMENT_THRESHOLD`**, because §11.1's
rule puts parameter values in the settings object. **This introduces a third
consumer of a threshold whose own comment warns against exactly that coupling.**
It is used here anyway, deliberately, because (a) the value is 0.5 either way so
the experiment is unaffected, and (b) inventing a fourth threshold before
knowing whether the checklist helps at all would be premature. **If V2 or V3
wins, a dedicated `CHECKLIST_AGREEMENT_THRESHOLD` must be split out before the
winner is treated as production config.** This is a pre-registered follow-up,
not a discovered one.

### 3.3 Held-out tripwire still applies

The held-out temporal synonym list
([`heldout_temporal_terms.txt`](../phase22/heldout_temporal_terms.txt)) is
scoring-only and must never reach the model. The existing containment test must
still pass for every variant, checklist on or off. A held-out term appearing in
the checklist block burns the list and invalidates the temporal endpoint.

---

## 4. Selection rule — fixed now, applied mechanically

The winner is the variant with the **highest impression CheXbert macro-F1 on
the 150 dev cases**, among those that satisfy **all three** guardrails:

| | guardrail | threshold |
|---|---|---|
| **(a)** | impression macro-**precision** drop vs V0 | **not more than 0.03** |
| **(b)** | temporal-term rate **and** strict contradiction rate | **must not exceed V0's** |
| **(c)** | structural failure rate | **≤ 2%** (≤ 3 of 150) |

**If no variant beats V0 on impression macro-F1, the winner is V0 and Step 3 is
not run.** A variant that ties V0 does not beat it.

Definitions, all inherited unchanged from Phase 22 so the numbers are
commensurable:

- **CheXbert labelling**: the frozen eval path (`ml/evaluation/score_chexbert.py`)
  in the isolated venv, **not** the runtime adapter — same instrument as every
  Phase 20/21/22 number. Binarised `to_present_binary()`: {Blank, Negative} → 0,
  {Positive, Uncertain} → 1. The uncertain→positive collapse follows Miura et
  al. 2021 and is a stated deviation from CheXbert's own weighted-F1 metric.
- **macro-F1 / macro-precision / macro-recall**: unweighted mean over the 14
  CheXbert labels.
- **temporal-term rate**: the **frozen** 5-term definition over findings +
  impression — the same primary-endpoint definition Phase 22 settled on after
  the pre-registration defect in `gate_a_results.md` §3.1.1. The 9-term run-plan
  variant is reported alongside as secondary but does **not** gate.
- **strict contradiction rate**: `ReportConsistencyService`'s contradiction
  check, CheXbert-labelled findings vs impression, any of the 13 real labels
  Positive in one and Negative in the other.
- **structural failure**: the harness records the case as failed — the LLM's
  output did not satisfy `StructuralValidator`'s 7 marker fields after the
  configured content retries.

### 4.1 Ties and degenerate outcomes, decided now

- **Exact tie on macro-F1** among qualifying variants → the **simpler** variant
  wins, ordered V0 > V2 > V1 > V3 (prefer no change, then prompt-only, then
  model-only, then both). Rationale: a tie is no evidence of benefit, and the
  cheaper, more auditable configuration should not lose to a 14B model on a
  coin-flip.
- **A variant wins on macro-F1 but fails a guardrail** → it is **out**, and the
  best *qualifying* variant wins. The failure is reported in full, not omitted.
- **All variants fail guardrails** → winner is V0, Step 3 not run.
- **V1 or V3 cannot run at all** (VRAM, see §5) → they are dropped and the rule
  is applied to whatever remains. Dropping is reported, not silently skipped.

---

## 5. VRAM and the drop condition for V1 / V3

qwen2.5:14b must fit **with BiomedCLIP and CheXbert resident**, since all three
are live during a real generation.

Measured Phase 22 footprints
([`fix_architecture_v1.2_FROZEN.md`](../phase22/fix_architecture_v1.2_FROZEN.md) §7):

| component | VRAM |
|---|---|
| llama3:8b | 5,025 MiB |
| BiomedCLIP marginal | 1,043 MiB |
| CheXbert marginal | 452 MiB |
| **peak, all three + inference** | **7,125 MiB of 16,376** (headroom 9.03 GiB) |

**Drop condition, fixed now:** if the peak with qwen2.5:14b resident alongside
BiomedCLIP and CheXbert leaves **less than 1 GB headroom** on the 16,376 MiB
card, V1 and V3 are dropped, that is reported, and the rule in §4 is applied to
V0 and V2 only.

**Disk, flagged now:** the machine has **25 GB free on C: (98% used)** at the
time of writing. A ~9 GB model pull fits, but this is tight and is recorded so
that a mid-run disk exhaustion is recognised as a known risk rather than
diagnosed from scratch.

---

## 6. Final test endpoint — Step 3

Run **only if a variant beat V0** under §4. The winner is then run on **all 477
test uids** and compared against the **stored v1.2 Gate A outputs**, which
already exist and are not regenerated.

Measured, all of it reported whatever the outcome:

| quantity | detail |
|---|---|
| impression macro-F1, macro-precision, macro-recall | winner vs v1.2, paired |
| findings macro-F1, macro-precision, macro-recall | winner vs v1.2, paired |
| **paired bootstrap 95% CI** | **B=2000, seed=42, percentile, case-level** — identical to Phase 0/20/21/22 |
| per-label table | precision, recall, F1, support, both arms, **no pooling**; labels with support < 10 marked unreliable |
| temporal-term rate | frozen 5-term definition, and run-plan 9-term as secondary |
| strict contradiction rate | as §4 |
| harmful transplant rate | strict, and on the common scorable denominator |
| latency | mean, median, p95, max, n |
| VRAM | peak with all three models resident |

### 6.1 What would make this a negative result, stated now

The pre-registered comparison is **winner − v1.2 on impression macro-F1 with a
paired 95% CI excluding zero**. If that CI includes zero, the honest reading is
that **the dev-set win did not replicate on test**, and the report says so in
those words. A macro-F1 CI that includes zero is the *expected* outcome given
Phase 21's finding that this metric's CI width barely moves with n — extending
n from 100 to 477 narrowed it by 5% against a predicted 2.2× narrowing
(`development_log.md:11351`). **This is not a reason to substitute a different
endpoint after the fact.** It is the reason the per-label table and the
precision/recall split are pre-registered as mandatory reporting rather than
optional follow-up.

### 6.2 What is explicitly out of scope

- **Bengali.** All checks and all scoring are English-only. No Bengali output
  has ever been evaluated (`thesis_facts.md` §5 defect 5) and this phase does
  not change that.
- **Adopting the winner into production config.** Step 3 ends at a measured
  verdict. Promotion is a separate decision.
- **The blinded manual read.** Still pending from Phase 22 and not revived here.

---

## 7. Stop conditions

Per the brief: no mid-run fixes. If any of the following occurs, the run stops
and is reported rather than repaired in flight.

1. A variant's structural failure rate exceeds 2% — it is recorded as failing
   guardrail (c); the run completes so the number is real, but the variant is
   out.
2. A held-out temporal term appears in any prompt — the list is burned, the
   temporal endpoint is invalidated, and the phase stops.
3. Disk or VRAM exhaustion mid-run.
4. The dev set turns out to intersect the test pool or KB by any amount — §2.3
   says zero on all four checks, so any non-zero here means the harness is not
   reading what this document says it reads.
5. V0's dev numbers are wildly inconsistent with its Gate A test numbers in a
   way that suggests the harness is misconfigured rather than that dev and test
   differ. Judgement is required here, so the raw numbers for both are reported
   side by side and the call is made explicitly rather than silently.

---

## 8. Provenance

| | |
|---|---|
| branch | `phase23-accuracy` from `phase22-v1.2` @ `7d3a8bc8` |
| dev set builder | `scratch/phase23/build_dev_set.py` |
| dev uids | `scratch/phase23/dev_uids_150.csv` (150 rows) |
| provenance json | `scratch/phase23/dev_set_provenance.json` |
| KB | ChromaDB `iu_cxr_biomedclip_v1_train`, 2462 docs, at `ml/outputs/retrieval/chroma_db` |
| scoring | `ml/evaluation/score_chexbert.py` in `ml/evaluation/.venv-bertscore` |
| bootstrap | B=2000, seed=42, percentile, case-level |
