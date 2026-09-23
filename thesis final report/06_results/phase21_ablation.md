# Phase 21 — the evidence-mode ablation (arms A / B / C)

**Never pool with any other phase.** This measured the **v1.1** system, before
the Phase 22 grounding fix. Arm C *is* the v1.1 production configuration.

| | |
|---|---|
| **Question** | Does full retrieved evidence produce better reports than voted labels alone, or than no retrieval-derived evidence at all? |
| **Method** | Three arms differing **only** in what `ContextBuilder` assembles, switched by a new `EVIDENCE_MODE` enum in `backend/app/core/config.py`. Paired per uid. Bootstrap B=2,000, seed 42, percentile. |
| **n** | **100** (all three arms) and **477** (arms C and B only) |
| **Source** | `ml/outputs/evaluation/phase21_arm_contrasts.json`, `phase21_arm_contrasts_n477.json`, `phase21_results_manifest.json`, `phase21_arm_integrity.json`; design in `docs/methodology/phase21_ablation_architecture.md` |

## The arms — and the naming rule that must not be broken

| arm | evidence text | voted labels | disclaimer | `EVIDENCE_MODE` |
|---|---|---|---|---|
| **A** | ✗ | ✗ | ✓ | `empty` |
| **B** | ✗ | ✓ | ✓ | `labels_only` |
| **C** | ✓ | ✓ | ✓ | `full` |

> **Arm B must never be described as "no retrieval."** Retrieval still executes
> in Arm B; only its output is reduced to voted labels. The accurate phrase is
> **"retrieval-as-classifier"**. Arm A is the only arm with no retrieval-derived
> evidence, and even there retrieval still runs to create the session — only its
> output is discarded before context assembly. *"Any wording that implies Arm B
> bypasses BiomedCLIP or ChromaDB is a misstatement of the experiment and will
> not survive examiner questioning"* (`phase21_ablation_architecture.md` §2.1).

**Why B matters:** Arm B is the modern equivalent of the classify-then-template
approach this project abandoned after Phase 0. C−B is therefore the direct
empirical test of the retrieval-augmented design over a classification-based one.

## Run integrity

`phase21_arm_integrity.json`: 100 attempted / 100 completed in **every** arm,
100 shared by all three, **zero** retrieval mismatches, **zero** problems. At
n=477, arms C and B both completed 477/477.

## Arm levels (descriptive — the contrasts below are the result)

| n | arm | findings macro-F1 | findings micro-F1 | impression macro-F1 | impression micro-F1 |
|---|---|---|---|---|---|
| 100 | C `full` | 0.1539 | 0.2679 | 0.1389 | 0.5581 |
| 100 | B `labels_only` | 0.1272 | 0.3830 | 0.1586 | 0.6735 |
| 100 | A `empty` | 0.0386 | 0.3874 | 0.0578 | 0.6733 |
| 477 | C `full` | 0.1689 | 0.2863 | 0.1734 | 0.5250 |
| 477 | B `labels_only` | 0.1102 | 0.3850 | 0.1478 | 0.6002 |

## The pre-registered primary endpoint — **IT DID NOT CLEAR**

> **Primary:** CheXbert macro-F1 on `impression`, **Arm C minus Arm B**, paired
> bootstrap 95 % CI excludes zero in the positive direction.
> Pre-registered `phase21_ablation_architecture.md` §6.3, **before any run**.

| n | estimate | 95 % CI | excludes 0 | verdict |
|---|---|---|---|---|
| 100 | **−0.0197** | [−0.0621, +0.0334] | no | **did not clear** |
| **477** | **+0.0256** | **[−0.0198, +0.0710]** | **no** | **DID NOT CLEAR** |

The n=100 interval was 0.0955 wide and contained zero, values favouring B *and*
values favouring C — it could not distinguish "no effect" from "an effect this
design could not resolve." The endpoint was therefore extended to the full 477
eligible cases, **by a rule fixed in advance** (§6.3.1) and by the same
precedent as Phase 20's extension. It still did not clear.

**This is reported as a negative result, in full.** No alternative metric,
field or contrast was promoted to primary afterwards — §6.3 forbade it in
advance, and the ban was honoured.

## Secondary contrasts (exploratory; a family, not independent confirmations)

**C − B, n=477:**

| metric | estimate | 95 % CI | excludes 0 |
|---|---|---|---|
| findings ROUGE-L | +0.0919 | [+0.0832, +0.1012] | yes |
| findings METEOR | +0.2265 | [+0.2151, +0.2376] | yes |
| findings CheXbert macro-F1 | +0.0587 | [+0.0165, +0.0978] | yes |
| impression ROUGE-L | +0.2145 | [+0.1906, +0.2403] | yes |
| impression METEOR | +0.2097 | [+0.1858, +0.2348] | yes |
| **impression CheXbert macro-F1 (PRIMARY)** | **+0.0256** | **[−0.0198, +0.0710]** | **no** |

**C − A, n=100** (a floor, not a controlled contrast — see below). All six
intervals exclude zero, including impression macro-F1 at **+0.0811
[+0.0299, +0.1213]**.

> **C − A must not be reported on the same case set as the extended C − B.**
> Arm A stayed at n=100 by a decision recorded in advance (§6.3.1). The two
> contrasts are not comparable and are not presented as though they were.

> **C − A is not a clean evidence contrast.** `PromptBuilder` calls
> `_confidence_instruction(voted_labels)`; with no labels it emits a different
> fallback sentence, so **Arm A's prompt differs from C's outside the evidence
> block as well as inside it** (§2.4, named before any run). The fallback was
> deliberately *not* changed, because special-casing it would mean the ablation
> no longer measured the shipped system. C − B is the pure contrast, and it is
> the primary.

## Why BLEU and BERTScore are absent from the contrasts

Both were excluded on documented, pre-existing negative findings about the
**metrics**, established before these arms existed: BERTScore fails the
mismatched-pairs validity bar on this corpus (Phase 20), and that conclusion
was re-checked on Arm C and **stood**. This is not result-shopping; the
exclusions predate the outcome.

## Two methodological findings this phase produced

1. **micro-F1 is unusable as a between-arm metric on this dataset** (§6.8).
   Note the direction in the table above: B and A score *higher* micro-F1 than
   C while scoring far lower macro-F1 — the micro figure is dominated by
   `No Finding`.
2. **CI width does not extrapolate as 1/√n for macro-averaged metrics** (§6.10),
   and **n=100 and n=477 macro-F1 are not the same estimand** (§6.11). The two
   sample sizes are reported side by side above and must not be read as a
   convergence.

## RQ3 — the latency characterisation was **NOT RECORDED**

§7 of the architecture specifies a per-stage P50/P95 latency profile written to
`ml/outputs/evaluation/latency/latency_summary.csv`. **That directory does not
exist and no such file exists anywhere in this repository.** The latency
numbers that *do* exist come from other phases and other instruments; they are
in [`performance_and_tests.md`](performance_and_tests.md) and are **not** the
Phase 21 RQ3 deliverable.

## What this phase establishes, stated at the strength the evidence supports

Full retrieved evidence beats retrieval-as-classifier on **every n-gram metric
and on findings-level clinical labels**, with intervals excluding zero. On the
**one endpoint that was pre-registered as primary** — clinical labels on the
impression — the difference is positive but **not distinguishable from zero at
n=477**. The design is supported on secondary evidence and unproven on its own
primary endpoint, and the thesis must say exactly that.
