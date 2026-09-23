# Open items — what is unfinished, and what each one blocks

Nine open items. Two of them (O1, O5) **block a claim the thesis would
otherwise want to make**, and are marked accordingly.

---

## O1 — The blinded manual read has not been performed 🔴 **BLOCKS A CLAIM**

| | |
|---|---|
| **What** | Two readers score 40 blinded reports (no version information) from `docs/phase22/reader_packet.md`, seed 20260921. The answer key is held separately in `reader_packet_ANSWER_KEY.md` and must not be opened until both readers submit. |
| **Status** | Packet built. **0 of 2 readers have submitted.** |
| **Why it matters** | *"A single clear grounding failure in the blinded manual read"* is a **withhold-pending-review trigger** — a stop condition that **overrides a clean pass on all three Gate A criteria.** |
| **Consequence** | **v1.2's adoption is not final.** Gate A's verdict is *"passes every automated criterion"*, **not** *"cleared for adoption"*. Any thesis sentence stating that v1.2 was adopted must carry this qualification. |
| **Source** | `gate_a_results.md` §4; `CHANGELOG_v1.2.md` §8.8 |

## O2 — Clinician feedback has not been collected

| | |
|---|---|
| **What** | No radiologist or clinician has evaluated the system's output or its interface. |
| **Status** | **NOT RECORDED** — no clinician-feedback instrument, protocol, sample size or result exists anywhere in this repository. |
| **Consequence** | Every usability and clinical-utility claim in the thesis is **unevidenced**. The label taxonomy in `ml/config/label_mapping.yaml` also still *"needs clinically-informed review before being frozen"* and has not had it. |
| **Source** | absence verified across `docs/` 2026-09-23; taxonomy caveat from `CLAUDE.md` |

## O3 — Gate B has not been run

| | |
|---|---|
| **What** | Calibrate the transplant-check threshold from `generation_v1.2_gateA_n477/consistency_and_transplant.jsonl`, which exists precisely as Gate B's calibration input. |
| **Status** | Not started. |
| **Consequence** | The transplant check **scores every report and can emit nothing**, so it is never listed in `checks_run` — which is why **every English report reads `partial`** and why the `clean` status is **unreachable in the shipped build**. |
| **Source** | `amendment_01_consistency_status.md` §2(e); `CHANGELOG_v1.2.md` §8.2 |

## O4 — Gate C has not been run

| | |
|---|---|
| **What** | The consistency **retry**: re-prompt when a consistency violation is detected. |
| **Status** | Not started. The service is **observational** — it records violations and alters nothing. |
| **Consequence** | **17/477** Gate A reports carry violations that nothing acted on. Note that Gate A being retry-free is what makes its primary endpoint clean: the Gate C circularity, where the same detector both triggers the retry and scores the outcome, **does not apply to any number in Gate A**. |
| **Source** | `gate_a_results.md` §2, §4; `CHANGELOG_v1.2.md` §8.3 |

## O5 — Bengali is entirely unmeasured 🔴 **BLOCKS A CLAIM**

| | |
|---|---|
| **What** | A defect rate — temporal, transplant, contradiction, or any accuracy metric — for Bengali output. |
| **Status** | **Zero Bengali defect rates have ever been measured in this project.** Every harness hardcodes `"language": "en"`. All three consistency checks are English-only by design, so a Bengali report stores `checks_run == []` and reads `not_run`. |
| **Consequence** | The v1.2 prompt changes **do** reach Bengali output, but nothing is known about their effect there. The bilingual feature is **shipped and unevaluated**, and the thesis must present it as a feature, never as a validated one. |
| **Source** | `gate_a_results.md` §7; `CHANGELOG_v1.2.md` §8.5 |

## O6 — D5 is open, and it blocks D3

| | |
|---|---|
| **What** | Record the structural/content retry attempt count. Preferred design: widen `generate_draft()`'s return type to carry the attempt count and final structural errors. Whether to persist it to `ReportRecord` is **a separate, unsettled sub-question**. |
| **Status** | **Open — not scoped, not scheduled.** Deliberately **not** bundled into Phase 22 v1.2, so its scope would not be settled implicitly by a fix that was ready to evaluate. |
| **Consequence** | An attempt-1 structural failure followed by an attempt-2 success is **invisible**, so the true content-validation rate is **unmeasurable** (this is what blocks **D3**). Every "0 structural failures" in `06_results/` therefore means *"0 failed after retries"*, **never** *"0 needed a retry"*. |
| **Known confound already recorded** | attempts ≥ 2 use `build_retry_prompt`, i.e. a **different prompt**, so attempt counts would not be exchangeable observations even once recorded. |
| **Source** | `decision_log.md` D5 and its Phase 22 note (*summary only — source: project chat log, 2026-08-17*) |

## O7 — The Chroma persist-path config bug is unfixed

| | |
|---|---|
| **What** | `main.py:110` constructs `ChromaVectorStore()` with no arguments, so `settings.CHROMA_PERSIST_PATH` is never read and **no environment override can redirect the vector store.** |
| **Status** | Pre-existing at tag `v1.1-evaluated`; **not fixed**, because Phase 22 step A6 forbade code changes at that point. |
| **Workaround used** | For the noise-floor run the store was **copied** and the sorted-ID sha256 verified identical, rather than redirected by config. |
| **Consequence** | Any future evaluation that needs a second collection must copy the store rather than configure a path. |
| **Source** | `CHANGELOG_v1.2.md` §8.6; `gate_a_results.md` §5; verified present 2026-09-23 |

## O8 — Phase 23 Step 3 was not run, by rule

| | |
|---|---|
| **What** | The test-set measurement for a winning variant. |
| **Status** | **Correctly not run.** `plan.md` §4 specifies that if no variant beats V0, the winner is V0 and Step 3 does not run. None did. |
| **Consequence** | `docs/phase23/test_results.md` **does not exist** and no new numbers exist for the 477 test uids. **The test pool is exactly as Phase 22 left it.** This is a clean outcome, not an omission. |
| **Source** | `dev_results.md` §8 |

## O9 — Four stale `clean` rows are unmigrated

| | |
|---|---|
| **What** | 4 of 1,802 report rows store `clean` under the pre-amendment rule and should read `partial`. |
| **Status** | Not migrated. |
| **Consequence** | Four reports in `dev.db` display a pass that the current rule would not grant. |
| **Source** | `amendment_01_consistency_status.md` §3 |

---

## Summary table

| item | blocks a thesis claim? | blocks another item? |
|---|---|---|
| **O1** blinded read | **yes — v1.2 adoption** | — |
| O2 clinician feedback | yes — all usability/utility claims | taxonomy freeze |
| O3 Gate B | no | makes `clean` unreachable |
| O4 Gate C | no | — |
| **O5** Bengali | **yes — any Bengali quality claim** | — |
| O6 D5 | no, if worded as "failed after retries" | **D3** |
| O7 Chroma path | no | future multi-collection evaluation |
| O8 Step 3 | no — correct by rule | — |
| O9 stale rows | no | — |
