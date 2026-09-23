# Phase 22, part 1 — the diagnosis of v1.1's grounding failures

**Never pool with any other phase.** This is a measurement of the **v1.1**
system, on Phase 21's stored Arm C outputs. It is the evidence that motivated
the v1.2 fix; it is not an evaluation of the fix.

| | |
|---|---|
| **Question** | Why does v1.1 produce impressions that contradict their own findings, copy neighbours verbatim, and assert prior studies that do not exist? |
| **Method** | Code-path trace plus three prevalence measurements over stored Phase 21 Arm C outputs. Scripts in `scratch/phase22_diagnosis/`. |
| **n** | **477** (Arm C); Phase 20 n=460 quoted only as a separate-run observation |
| **Source** | `docs/phase22/diagnosis.md`; raw outputs `out_2a_transplant.txt`, `out_2b_temporal.txt`, `out_A*.txt` |

## The three prevalence measurements

| # | measure | Arm C (v1.1), n=477 | Phase 20, n=460 | notes |
|---|---|---|---|---|
| 2a | impressions with 5-gram overlap ratio **1.0** against a retrieved neighbour | **83 / 353 = 23.5 %** | **not computable** | denominator is impressions with ≥5 tokens; 124 were shorter. Max contiguous copied run **42 tokens**. 0 neighbour uids failed to resolve. |
| 2b | reports using ≥1 of five temporal terms **with no prior study** | **167 / 477 = 35.0 %** | 97 / 460 = 21.1 % | every case in both harnesses had no prior study |
| 2c | **strict** internal contradiction (CheXbert on findings vs impression) | **22 / 477 = 4.6 %** | 9 / 460 = 2.0 % | the *loose* asymmetry rate is 300/477 = 62.9 %, and is **not** a contradiction rate |

> **Transplant is NOT COMPUTABLE for Phase 20.** Its `per_case_results.csv` has
> no `retrieved_uids` column, and the neighbour identities for its 460
> generations were never persisted in any artifact in this repository. **No
> substitute number is offered.**

> **The Phase 20 column is a separate-run observation, not a change.** Different
> n, different code state. It must never be differenced against the Arm C column.

## Two caveats that bound how hard these numbers can be pushed

- **Temporal counts are lexical**, from word-boundary regex, not adjudicated
  readings. "Stable" has a non-temporal clinical sense. A 20-case audit at a
  stated seed put precision at **95 %** (§5.3). The 167 and 97 totals are not
  individually adjudicated.
- **CheXbert has a confirmed negation bug on this corpus**: *"No acute,
  displaced rib fractures"* is labelled `Fracture = Positive`. Strict
  contradiction counts are **labeler output, not adjudicated readings**. Ten of
  the 22 Arm C cases were read individually and are genuine; twelve were not.

The clearest single instance found: **uid 1330**, whose findings assert a
nodule *"unchanged from a previous examination 7 years ago"* — a specific prior
study that does not exist and that the system has **no field to represent**.

## The four confirmed root causes

| # | root cause | where | evidence |
|---|---|---|---|
| **RC1** | **No section-to-section grounding.** One LLM call emits all 7 fields as siblings of the evidence block; the impression is never conditioned on *this report's* findings. Section regeneration is worse — it omits the report's own content and instructs the model not to consider other sections. | `llm_orchestrator.py:56-58`, `prompt_builder.py:348-368`, `:198-216` | 22/477 strict contradictions; 10 of 11 Cardiomegaly cases in the F−/I+ direction |
| **RC2** | **Neighbour text is rendered verbatim with no attribution boundary and no anti-copying instruction.** The only grounding rule forbids *invention*, and thereby **rewards copying**. | `context_builder.py:178-192`, `prompt_builder.py:411-424`, `:371-378` | 83/353 = 23.5 % at overlap ratio 1.0; max run 42 tokens |
| **RC3** | **No prior-study state exists in the generation context**, and no temporal restriction is applied. The prohibition exists only in `_comparison_grounding_instruction()` — i.e. only where a prior *does* exist. | `prompt_builder.py:116-137`, `:282-308` | 167/477 = 35.0 % |
| **RC4** | **The one semantic check cannot represent this failure class, and gates nothing.** `validate_semantic()` concatenates sections before inspection, so cross-section contradiction is *unrepresentable*; its `unsupported_terms` check flags only terms **absent** from evidence, so a transplanted finding is **structurally exempt**; it has no temporal check. Its result is persisted as warnings and **never branched on** — the report is written unconditionally. | `response_validator.py:49`, `:51-55`, `:228`, `:257` | — |

**RC1–RC3 are independent generators** of the three observed defects; **RC4 is
why none of the three was caught.** RC2 and RC3 can compound: a copied span
imports its own temporal language.

## Relationship to the Phase 20 Fracture finding

Phase 20's Fracture investigation established that *"the fracture finding
belongs to a retrieved neighbor case, not to the actual query patient"* in
18/18 cases. **RC2 is that same mechanism, now measured at corpus scale** on
the impression field rather than inferred from one label's F1 anomaly. This
diagnosis confirms and generalises that finding; it does not restate it.

## Verdict

Four root causes confirmed, three of them independently sufficient to produce
the observed defects, and the fourth explaining the absence of detection. **No
fix was chosen and no fix code was written in this step** — candidates were
enumerated only (§4), so the fix could not be selected on knowledge of which
would score best.
