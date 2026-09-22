# Phase 23 Step 1 — measurements and drop decisions

Pre-registered in [`plan.md`](plan.md). Nothing here changes the plan; it
records the measurements the plan said to take before running anything.

## 1. VRAM — V1/V3 drop condition

`scratch/phase23/vram_qwen.py`, real output. llama3:8b is explicitly unloaded
(`keep_alive=0`) first, because production runs one LLM at a time and
measuring both resident would overstate the footprint.

| stage | used | marginal |
|---|---|---|
| baseline (llama3 unloaded) | 558 MiB | — |
| + **qwen2.5:14b** | 9,834 MiB | **9,276 MiB** |
| + BiomedCLIP | 10,875 MiB | 1,041 MiB |
| + CheXbert | 11,327 MiB | 452 MiB |
| **peak, all three + inference** | **11,401 MiB** | — |

| | |
|---|---|
| card total | 16,376 MiB |
| **headroom** | **4,975 MiB = 4.86 GiB** |
| drop threshold (plan §5) | 1,024 MiB |
| **VERDICT** | **PASS — V1 and V3 proceed** |

For comparison, Phase 22's llama3:8b stack peaked at 7,125 MiB (headroom
9.03 GiB). qwen costs **4,276 MiB more** and still clears the threshold by
3.86 GiB.

BiomedCLIP (1,041 vs 1,043 MiB) and CheXbert (452 vs 452 MiB) reproduce their
Phase 22 marginals almost exactly, which is the check that the measurement is
of the same stack.

**Latency note, recorded not concluded.** qwen's first-token load was 24.1 s
cold; a call under full load returned in 2.9 s. CheXbert under the qwen stack:
mean 10.8 ms, p50 10.0, p95 43.5, max 43.5 (n=20) versus Phase 22's mean 8.2 /
p50 8.0 / p95 11.1. The p95 is 4x higher. n=20 is too small to call this a
regression; per-case latency is measured properly during the dev runs.

## 2. Does ollama apply qwen's default system prompt?

Flagged in plan §3.1.1 item 3. `scratch/phase23/system_prompt_probe.py`,
temperature 0, seed 42, prompt `Who created you? Answer in one short sentence.`

| case | response |
|---|---|
| **A** no system field (what `OllamaClient` sends) | I was created by Alibaba Cloud. |
| **B** explicit contradictory system field | I was created by **Acme Corp**. |
| **C** explicit **empty** system field | I was created by Alibaba Cloud. |
| **D** `raw=true` (template bypassed) | ...created by a team of developers and researchers at Anthropic. |

**What this establishes:** an explicit `system` field **is** honoured under
`/api/generate` — B adopted the injected persona outright.

**What this does NOT establish, stated plainly:** whether the *Modelfile's*
default SYSTEM is injected when no system field is sent. A == C is consistent
with two different explanations — either neither carries the default, or
ollama treats an empty string as "no override" so both do. The naive
who-created-you answer is not evidence either way, because a qwen model
answers Alibaba Cloud from training alone. **This probe cannot separate those
two cases and is not claimed to.**

**What is established, and is what actually matters:** the two models ship
different Modelfiles.

| model | SYSTEM directive in its Modelfile |
|---|---|
| llama3:8b | **none** — `ollama show llama3:8b` prints no System section |
| qwen2.5:14b | **present** — "You are Qwen, created by Alibaba Cloud. You are a helpful assistant." |

Both templates gate on `.System` in the `/api/generate` branch, so whatever
ollama puts there is what reaches the model.

**Consequence for the experiment, recorded before any run:** V1 and V3 may
carry a generic assistant persona that V0 and V2 definitionally cannot. This
is an **uncontrolled prompt difference between the model arms**, it is not
removable without diverging from "qwen2.5:14b as ollama ships it", and it must
be restated in the dev and test results rather than left here. It does not
affect V0-vs-V2 (both llama3) or V1-vs-V3 (both qwen), so the **prompt** lever
is cleanly measured; only the **model** lever carries it.

## 3. Label checklist — implementation

| | |
|---|---|
| flag | `Settings.PROMPT_LABEL_CHECKLIST_ENABLED`, `config.py:301` / `:494` |
| default | **False** |
| threshold | `settings.DISCLAIMER_AGREEMENT_THRESHOLD` = 0.5, injected, not read in-module |
| builder | `PromptBuilder._label_checklist_instruction` |
| wiring | `main.py:183-189` |
| tests | `backend/tests/unit/test_prompt_label_checklist.py`, **21 tests** |

Rendered block, flag on, threshold 0.5, votes Atelectasis 0.80 /
Cardiomegaly 0.60 / Pneumothorax 0.20:

```
LABEL CHECKLIST:
Retrieval-based voting proposed the candidate labels below. Each one is a HYPOTHESIS drawn from other patients' cases, not an observation of this patient's radiograph.
For EVERY label listed, your report must do one of two things, and must not do neither:
  (1) state the finding as present, ONLY where this patient's image evidence supports it; or
  (2) state explicitly that it is absent or not demonstrated.
Do not omit a listed label without dispositioning it. Do not state a label as present merely because it appears below.
Candidate labels:
  - Atelectasis (agreement 0.80)
  - Cardiomegaly (agreement 0.60)
IMPRESSION COVERAGE: every abnormality your FINDINGS states must also appear in your IMPRESSION. If FINDINGS describes an abnormality, IMPRESSION must not describe the study as normal or free of acute abnormality.
```

Pneumothorax at 0.20 is correctly absent.

### 3.1 Properties asserted by test

- **Flag off ⇒ byte-identical to v1.2.** A `PromptBuilder` constructed exactly
  as v1.2's lifespan constructed it produces the same bytes as an explicitly
  disabled Phase 23 builder. This is the test V0 depends on: V0 is only a real
  baseline if the feature leaves nothing behind when off — not a stray blank
  line. Also asserted: no triple newline appears, which is how an empty
  appended section would show up.
- **Threshold is inclusive** at `agreement == threshold`, per the plan's
  "at or above".
- **No candidate clears the threshold ⇒ no block at all**, rather than a
  checklist instructing the model to adjudicate an empty list.
- **Disposition is forced both ways** — present *or* explicitly negated, and
  "must not do neither". A checklist that only offered "state it if present"
  would be a licence to over-call, the opposite of the intent.
- **Not a leak into other prompts**: section regeneration is unaffected
  (rewriting one field must not invite rewriting the report). The **retry**
  prompt *does* carry it, because `build_retry_prompt` wraps
  `build_generation_prompt` — intended, and asserted rather than left to
  accident.
- **Held-out containment, checklist OFF and ON.** Parametrised over both
  states, plus a narrower test over the new block in isolation so a failure
  points at the checklist rather than anywhere in the prompt.

### 3.2 Test suite

| | |
|---|---|
| before Step 1 | **512 passed** |
| after Step 1 | **533 passed**, 0 failed |

## 4. Nothing was run

No variant has been generated. The dev set has not been touched beyond the
Step 0 disjointness proof, which reads uids only. Step 2 is next.
