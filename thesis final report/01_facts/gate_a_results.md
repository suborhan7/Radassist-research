# Phase 22 — Gate A Results

| | |
|---|---|
| **Run date** | 2026-09-22 |
| **Code under test** | `phase22-v1.2` at `52884b0eba23e39a935f97e0e8111e9310c3b8c9` |
| **Run plan** | [`gate_a_run_plan.md`](gate_a_run_plan.md), committed `55e8bc08506cb3eb6066e117d9d53bbb00c3a7f5` at 2026-09-22 01:09:38 +0600 — **before any v1.2 report existed** |
| **Baseline** | stored Phase 21 Arm C (`generation_arm_full_n477`), paired per uid |
| **Outputs** | `ml/outputs/evaluation/generation_v1.2_gateA_n477/` |
| **Verdict** | **ADOPT** on the three gating criteria (unchanged under both primary-endpoint definitions); **one withhold trigger remains open** (manual read not yet performed) |

---

## 1. Configuration

| item | value | vs Phase 21 |
|---|---|---|
| model | `llama3:8b`, digest `365c0bd3c000` | name **match**; digest not recorded by Phase 21 |
| ollama | `0.34.2` | **match** |
| temperature / seed | 0.0 / 42 | **match** |
| retry budgets | content 2 / transport 1 | **match** |
| num_ctx | 4096 | **match** |
| collection | `iu_cxr_biomedclip_v1_train`, 2462 docs | name **match**; count/hash not recorded by Phase 21 |
| sorted-ID sha256 | `c6b2ab850fc9b3fb9a1bfc6493cdd52b5322c1d9d47b4d5dba88afeb12ef72f6` | — |
| embedding | `biomedclip` / `v1` | **match** |
| evidence mode | `full`, verified live via `/system/stats` before generation | **match** |
| consistency service | **observational** — no retry, nothing blocked, no text altered | n/a (new) |

Everything Phase 21 recorded matches. The three identifiers it did not record
(model digest, collection count, collection ID hash) are recorded here so
future runs can make the comparison Phase 21 could not.

**Harness deviation, recorded rather than glossed.** This run did **not** use
`run_generation_eval.py --arm full --tag n477`: that invocation writes into
`generation_arm_full_n477`, which *is* the stored Phase 21 Arm C artifact
being paired against, and would have overwritten the baseline. The run drove
the identical API path (`POST /retrieve` → `POST /generate-report`) with
identical parameters — `top_k=5`, `min_similarity=0.0`,
`declared_projection=PA`, raw image, `language=en`,
`questionnaire_answers=None`, `clinical_notes=""` — from the explicit 477-uid
list, resumable, into a versioned directory.

---

## 2. Generation

```
completed 477/477   failed 0
```

| | |
|---|---|
| structural failure rate | **0/477** (no HTTP 422; every response parsed within the content-retry budget) |
| consistency status | **partial 459, violations 17**, clean 0, not_run 0 |
| `consistency_retry_count` | **0 for every case** — Gate A performs no retry, by construction |
| latency per report | mean **4.50 s**, median 4.47 s, max 5.97 s, n=477 |
| consistency check latency | 6.9–7.8 ms per report (server logs) |

No report reads `clean`, which is what amendment 01 predicts before Gate B:
the transplant check has no calibrated threshold, cannot emit a violation, and
is therefore not counted as having run.

**Content-retry attempts are not observable.** Neither `LLMOrchestrator` nor
`OllamaClient` logs them and the API does not expose them — the gap decision
**D5** exists to close, and why **D3** is blocked. Reported as not observable,
never as zero.

---

## 3. Pre-registered endpoints

Paired per uid, n=477. Bootstrap: 2,000 resamples, seed 42, percentile.
CheXbert labels from the **frozen evaluation path** (frozen eval venv), not the
runtime adapter, so both arms are labelled by the same instrument.

### 3.1 Primary — temporal-term rate (gates)

Reported under **both** definitions the frozen document supports; see
[§3.1.1](#311-deviations-from-pre-registration) for why there are two. The
frozen-definition figure is the primary one.

| definition | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **FROZEN (primary)** — 5 terms, findings+impression | **0.3501** (167/477) | **0.0273** (13/477) | **−0.3229** | **[−0.3648, −0.2830]** | 477 |
| run-plan (secondary) — 9 terms, +recommendation | 0.3899 (186/477) | 0.0503 (24/477) | −0.3396 | [−0.3836, −0.2998] | 477 |
| run-plan, n=100 pilot | 0.4600 (46/100) | 0.0500 (5/100) | −0.4100 | [−0.5100, −0.3200] | 100 |

**Decreases with CI excluding zero under both definitions → PASS.**

The frozen definition reproduces the frozen document's own baseline exactly:
167/477 = 0.3501.

### 3.1.1 Deviations from pre-registration

**What differs.** The run plan (§3.1) fixed the primary endpoint over **nine**
terms across **findings, impression and recommendation**. The frozen
document's stated baseline for the same endpoint — `temporal-term rate
(primary list) 0.3501 k=167/477`, `fix_architecture_v1.2_FROZEN.md` line
734 — was computed over **five** terms across **findings and impression
only** (`diagnosis.md` §2b).

**Why it happened, stated plainly: the frozen document supports both
readings, and they are not consistent with each other.**

Its §3.1, lines 241–249, defines the *check*:

> | **Input** | `content.findings`, `content.impression`, `content.recommendation`; `has_prior_study: bool` |
>
> Term list is the §2b list, config-driven, and is **the same list named in the
> prompt** (§2(iii)) — the model is told exactly what the detector looks for…
>
> — `fix_architecture_v1.2_FROZEN.md` §3.1, lines 244, 251–252

That is three sections, and §2(iii)'s prompt list is the nine terms
*stable, unchanged, interval, again, redemonstrated, persistent, previously,
compared with, new*. The run plan followed this.

Its §6.2, line 734, carries the baseline **number**, and that number came from
`diagnosis.md` §2b's headline, which is five terms over two sections. The two
cannot both describe one metric.

This was not noticed when the run plan was written: the run plan quoted §3.1's
input and §2(iii)'s list, and quoted §6.3's baseline sentence, without
checking that the quoted number had been produced by a narrower rule. That is
a real pre-registration defect and it is recorded here rather than resolved
quietly in favour of whichever figure reads better.

**Resolution.** The frozen-definition result is reported as the primary figure,
because that is the definition the frozen document's own baseline instantiates
and it is the more conservative of the two (fewer terms, fewer sections, so
fewer opportunities to count a hit). The run-plan definition is reported as
secondary.

**The verdict is unchanged.** Both definitions decrease with a 95% CI
excluding zero:

```
FROZEN   v1.1=0.3501 (167/477)  v1.2=0.0273 (13/477)  diff=-0.3229  CI [-0.3648, -0.2830]
RUN-PLAN v1.1=0.3899 (186/477)  v1.2=0.0503 (24/477)  diff=-0.3396  CI [-0.3836, -0.2998]
VERDICT UNCHANGED UNDER BOTH DEFINITIONS? True
```

Neither guardrail depends on this definition at all, so criteria 2 and 3 are
untouched.

### 3.2 Clinical guardrail — CheXbert impression micro-F1 (gates, δ = 0.05)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **micro-F1** | 0.5250 | 0.5886 | **+0.0636** | **[+0.0314, +0.0961]** | 477 |

CI lower bound **+0.0314 > −0.05 → PASS**. The guardrail was a
non-inferiority bound; the measurement is an *improvement* whose CI excludes
zero on the positive side. It is reported as clearing the bound, which is what
was pre-registered.

### 3.3 Supplementary guardrail — impression ROUGE-L (gates, δ = 0.03)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| **ROUGE-L** | 0.2496 | 0.2646 | +0.0149 | [−0.0024, +0.0317] | 477 |

CI lower bound **−0.0024 > −0.03 → PASS**. The CI includes zero, so this is
**not** evidence of improvement — only that textual drift is bounded well
inside the margin, which is all this guardrail was for.

### 3.4 Secondary (do **not** gate adoption)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| harmful transplant rate (strict) | 0.0461 (22/477) | 0.0210 (10/477) | −0.0252 | [−0.0419, −0.0105] | 477 |
| strict contradiction rate | 0.0461 (22/477) | 0.0084 (4/477) | −0.0377 | [−0.0566, −0.0189] | 477 |

Both fell with CIs excluding zero. Per the pre-registered rule they are
reported whatever they show and **do not** gate adoption.

> **A denominator caveat that materially affects the transplant reading.**
> The transplant ratio is only defined for impressions with ≥5 tokens. That
> scorable count fell from **353 (v1.1) to 280 (v1.2)**, because v1.2
> impressions are shorter (median 9 → 5 words; under-5-word impressions
> 124 → 197; see §6). Against the scorable denominator the rate is
> 22/353 = 6.23% → 10/280 = 3.57%. **Part of the harmful-transplant drop may
> be an artifact of shorter impressions being unscorable rather than of less
> copying**, and this run cannot separate the two.

### 3.5 Held-out synonym rate (does not gate; word-avoidance tripwire)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| held-out rate | 0.0377 (18/477) | 0.0084 (4/477) | −0.0294 | [−0.0461, −0.0147] | 477 |

**The primary rate fell and the held-out rate fell with it.** Per §6.4's
reading rule this is *consistent with a real fix* rather than word-avoidance,
and the word-avoidance withhold trigger is **not** fired. These ten terms were
never shown to the model — verified over every prompt the backend can send by
`test_prompt_heldout_containment.py`.

### 3.6 Descriptive — CheXbert impression macro-F1 (does **not** gate)

| | v1.1 | v1.2 | diff | 95% CI | n |
|---|---|---|---|---|---|
| macro-F1 | 0.1734 | 0.1958 | +0.0224 | [−0.0266, +0.0683] | 477 |

CI includes zero. Per the frozen rule this must **not** be reported as a
non-inferiority claim: a metric whose CI does not narrow with n cannot support
one.

---

## 4. Verdict

Applied mechanically from the pre-registered rule; no endpoint was added,
dropped or redefined.

| criterion | result |
|---|---|
| 1. primary temporal decreases, CI excludes zero (n=477) | **PASS** — frozen definition −0.3229 [−0.3648, −0.2830]; run-plan definition −0.3396 [−0.3836, −0.2998] (§3.1.1) |
| 2. micro-F1 CI lower bound > −0.05 | **PASS** (+0.0314) |
| 3. ROUGE-L CI lower bound > −0.03 | **PASS** (−0.0024) |
| **ADOPT v1.2?** | **YES on the three gating criteria** |

**Withhold-pending-review triggers:**

| trigger | status |
|---|---|
| held-out rate fails to fall while primary collapses | **not triggered** — both fell |
| a single clear grounding failure in the blinded manual read | **OPEN** — packet prepared, not yet read |

> **Adoption is therefore not final.** The second trigger is a stop condition
> that overrides a clean pass on all three criteria, and it cannot be
> evaluated until two readers have completed the blinded packet. The verdict
> above is *"passes every automated criterion"*, not *"cleared for adoption"*.

**Gate A is the judged run** (frozen §6.1). The consistency service is
observational here: no retry exists, so the temporal rate measures exactly one
thing — whether instruction (iii) changed the model's behaviour. The Gate C
circularity, where the same detector both triggers the retry and scores the
outcome, does not apply to any number in this document.

---

## 5. Supplementary — v1.1 re-run noise floor

**Not an endpoint. Does not enter the verdict.**

What could a v1.1 → v1.2 difference be worth if re-running the *same* code
produced one? v1.1 was checked out at tag `v1.1-evaluated` in a separate
worktree, served against a byte-verified copy of the same collection
(sorted-ID sha256 identical), and re-run on the 100 pilot uids with identical
settings.

```
cases compared            : 100/100  (missing 0)
byte-identical to stored  : 33/100 (33.0%)
differing                 : 67/100 (67.0%)
temporal rate, STORED v1.1: 46/100 (46.0%)
temporal rate, RE-RUN v1.1: 46/100 (46.0%)
noise-floor movement      : +0.0 percentage points
```

**Two findings, and the second is what matters.** At temperature 0.0 with
seed 42, **67% of outputs are not byte-identical on re-run** — the generation
is materially non-deterministic, which confirms and quantifies the
non-determinism this project recorded once before. But **the primary
endpoint's own measurement did not move at all**: 46/100 both times, 0.0
percentage points.

So the text varies while the endpoint is stable, and the −34 percentage point
primary result cannot be attributed to re-run noise. This is the single
strongest piece of support for the primary reading, and it is supplementary
precisely because it was not pre-registered as an endpoint.

---

## 6. Post-hoc, not pre-registered

None of the analyses below was in the run plan. **No number here is a
criterion and the verdict is not revisited.** They are reported because
several of them change how §3 should be read — in one case, decisively.

Same bootstrap configuration throughout (B=2,000, seed 42, percentile,
paired), and the same frozen CheXbert evaluation path for both arms.

### 6.1 Is the improvement just shorter text?

This is the obvious alternative explanation for §3's results, and §6(b) of the
original write-up flagged it as untested. It is now tested, and the answer is
no.

**(a) Micro precision and recall, separately — the decisive test.**

| | v1.1 | v1.2 | diff | 95% CI |
|---|---|---|---|---|
| micro **precision** | 0.5112 | 0.5863 | **+0.0750** | [+0.0400, +0.1110] |
| micro **recall** | 0.5395 | 0.5909 | **+0.0514** | [+0.0178, +0.0859] |

**Both rose, and both CIs exclude zero.** If shortening were the mechanism,
precision would rise (fewer assertions, fewer false positives) while recall
**fell** (fewer assertions, fewer true positives caught). Recall rose instead.
v1.2 writes less and catches *more* of what the reference says. That is not
what truncation looks like.

**(b) Per-label precision, recall and support — no pooling.**

Support is the number of reference-positive cases and is identical across arms
by construction (same references, same uids).

| label | support | P v1.1 | R v1.1 | P v1.2 | R v1.2 | |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 6 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Cardiomegaly | 25 | 0.250 | 0.440 | 0.364 | 0.320 | |
| Lung Opacity | 46 | 0.216 | 0.239 | 0.250 | 0.283 | |
| Lung Lesion | 15 | 0.120 | 0.200 | 0.154 | 0.133 | |
| Edema | 9 | 0.143 | 0.222 | 0.364 | 0.444 | **support < 10 — unreliable** |
| Consolidation | 4 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Pneumonia | 20 | 0.214 | 0.150 | 0.100 | 0.050 | |
| Atelectasis | 27 | 0.140 | 0.259 | 0.171 | 0.259 | |
| Pneumothorax | 1 | n/a | 0.000 | n/a | 0.000 | **support < 10 — unreliable** |
| Pleural Effusion | 17 | 0.333 | 0.294 | 0.364 | 0.235 | |
| Pleural Other | 5 | 0.111 | 0.200 | 0.333 | 0.200 | **support < 10 — unreliable** |
| Fracture | 7 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Support Devices | 2 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| No Finding | 322 | 0.777 | 0.714 | 0.766 | 0.804 | |

Seven of fourteen labels have support below 10 and their figures should not be
read as estimates of anything. Of the seven with usable support, the movements
are mixed — **Pneumonia is clearly worse** (recall 0.150 → 0.050 on support
20), Cardiomegaly trades recall for precision, and the aggregate is carried by
`No Finding` (support 322), whose recall rises 0.714 → 0.804. That is worth
stating plainly: **the micro-F1 improvement is substantially a "No Finding"
improvement**, and the per-label picture is not uniformly favourable.

**(c) Does v1.2 stay silent about findings the reference reports?**

Cases where the generated impression carries **no** positive label on the 13
real conditions while the **reference** impression carries at least one:

```
v1.1: 56/477 = 0.1174   (gen-empty 338, ref-has 116)
v1.2: 56/477 = 0.1174   (gen-empty 365, ref-has 116)
```

**Identical — 56 in both.** v1.2's impressions are empty of positive labels
more often overall (338 → 365), but the extra silence falls entirely on cases
where the reference is also negative. It does not miss a real finding more
often than v1.1 did. This is the strongest single piece of evidence against
the shortening-harms hypothesis.

**(d) Word-count distributions, reported separately.**

| field | version | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|---|
| findings | v1.1 | 10 | 33.0 | 48.0 | 61.0 | 181 |
| findings | **v1.2** | 6 | 24.0 | **30.0** | 35.0 | 109 |
| impression | v1.1 | 1 | 4.0 | 9.0 | 18.0 | 73 |
| impression | **v1.2** | 1 | 4.0 | **5.0** | 12.0 | 62 |

Both sections shortened, findings substantially (median 48 → 30, −38%), and
the long tail compressed (max 181 → 109). The shortening is real and is not
confined to impressions.

**(e) Temporal-term rate restricted to FINDINGS only** — the less confounded
test, since findings shortened proportionally less than impressions:

| terms | v1.1 | v1.2 | diff | 95% CI |
|---|---|---|---|---|
| frozen 5-term | 0.2872 (137/477) | **0.0126** (6/477) | −0.2746 | [−0.3145, −0.2348] |
| run-plan 9-term | 0.3208 (153/477) | 0.0210 (10/477) | −0.2998 | [−0.3417, −0.2600] |

**Findings length fell 38%; the findings temporal rate fell 96%** (137 → 6).
Shortening cannot produce a 96% reduction from a 38% length cut unless
temporal language were concentrated in exactly the removed text, which the
per-section numbers give no reason to believe. Instruction (iii) changed what
the model writes, not merely how much.

### 6.2 Transplant on a common denominator

§3.4 flagged that the scorable denominator fell 353 → 280 because the
transplant ratio is undefined below 5 tokens, so part of that improvement
might be unscorability rather than less copying. Restricting to uids scorable
in **both** arms removes the confound entirely:

```
scorable in v1.1 only : 92
scorable in v1.2 only : 19
scorable in BOTH      : 261

harmful transplant, common denominator, paired, n=261:
  v1.1=0.0805 (21/261)   v1.2=0.0383 (10/261)   diff=-0.0421  CI [-0.0728, -0.0153]
```

**The improvement survives, with the CI still excluding zero.** On the
identical 261 cases, harmful transplantation roughly halves. The denominator
shift inflated the headline figure in §3.4 but did not create it.

### 6.3 Residual defect: a "normal" impression over abnormal findings

Phase 22's constraint (ii) forbids the impression asserting what findings did
not state. It says nothing about the **reverse** — an impression omitting what
findings *did* state — and that failure mode survives.

Cases where the generated **findings** carry ≥1 CheXbert-positive real
condition while the generated **impression** carries none:

```
v1.2:  27/477 = 0.0566
v1.1:  90/477 = 0.1887   (context only)
```

v1.2 is roughly **three times better** here than v1.1, unprompted — but 27
cases remain, and they are a real internal inconsistency. Note this is
measured against the report's **own** findings, not the reference: §6.1(c)
shows v1.2 does not miss reference findings more often. The defect is
*self*-inconsistency, not under-detection.

Five cases sampled at **seed 20260922**:

> **uid=951** — findings-positive: Atelectasis
> *Findings:* "…**Mild right basilar atelectasis** and relative elevation of the right hemidiaphragm are noted…"
> *Impression:* "The chest X-ray is **normal**, with no evidence of active cardiopulmonary disease."

> **uid=2486** — findings-positive: Lung Opacity
> *Findings:* "…The right lung base shows **minimal opacity**, which may represent **minimal right basilar airspace disease**."
> *Impression:* "The chest X-ray is **normal**, with no acute cardiopulmonary abnormality."

> **uid=3461** — findings-positive: Lung Opacity
> *Findings:* "**The lung opacities are seen throughout the lungs**, with more focal **streaky bibasilar opacities**… prominent coarse interstitial markings throughout the lungs."
> *Impression:* "**No acute cardiopulmonary abnormality**"

> **uid=2982** — findings-positive: Support Devices
> *Findings:* "…There is an IVC [REDACTED] identified. The right upper extremity **PICC tip is in the upper SVC**. Surgical clips in the right upper abdomen."
> *Impression:* "No acute cardiopulmonary disease."

> **uid=3681** — findings-positive: Support Devices
> *Findings:* "…The **support devices** are intact."
> *Impression:* "No acute cardiopulmonary abnormalities are seen."

**Three of the five are genuine omissions** (951, 2486, 3461): the findings
section describes atelectasis or opacity and the impression calls the study
normal. uid=3461 is the worst — opacities "throughout the lungs" summarised as
"no acute cardiopulmonary abnormality".

**Two are arguably labeler artifacts** (2982, 3681): the positive label is
`Support Devices`, a device rather than a pathology, and an impression that
does not mention a PICC line is not obviously wrong. Support Devices has
reference support 2 in this corpus and is flagged unreliable in §6.1(b).

This is a residual defect of the **opposite** direction to the one Phase 22
targeted, it is not covered by any check in v1.2, and no endpoint measures it.
Recorded for Gate B/C scoping.

## 7. Limitations

- **English only.** The harness hardcodes `"language": "en"`. Every number in
  this document is an English result.
- **Bengali is unmeasured.** The prompt changes reach Bengali output; all three
  consistency checks are English-only; no Bengali defect rate has ever been
  measured in this project. Nothing here says what v1.2 does to Bengali
  reports.
- **The explanation prompt changed but is unevaluated.**
  `build_explanation_prompt()` reuses `_evidence_section()`, so change (i)
  propagates to it. That is intended — the explanation chat shows the
  clinician the same other-patient text and should carry the same attribution
  boundary — but no endpoint here measures explanation output.
- **The transplant check emitted nothing.** Its threshold is Gate B's to
  calibrate, so it was scored but not counted as run. Every report reads
  `partial` for that reason. `transplant_scores()` output is saved per case in
  `consistency_and_transplant.jsonl` as Gate B's calibration input.
- **Temporal counts are lexical**, at a measured 95% precision
  (diagnosis.md §5.3), not adjudicated readings.
- **CheXbert has a known negation bug** on this corpus (diagnosis.md §2c);
  contradiction counts are labeler output, not adjudicated readings.
- **Harmful-transplant denominators differ between arms** (353 vs 280) — see
  §3.4 and §6(b).
- **The manual read has not happened.** Its withhold trigger is open.
- **Content-retry attempts are unobservable** (D5), so the structural result
  is "0/477 failed after retries", not "0/477 needed no retry".
- **The primary endpoint had two defensible definitions** in the frozen
  document, and the run plan fixed the wider one without noticing the
  frozen baseline came from the narrower one (§3.1.1). Both are reported;
  the verdict is the same either way.
- **The micro-F1 gain is substantially a `No Finding` gain** (support 322,
  recall 0.714 → 0.804). Seven of fourteen labels have support below 10 and
  are unreliable; among those with usable support the picture is mixed, and
  **Pneumonia is clearly worse** (recall 0.150 → 0.050 on support 20). See
  §6.1(b).
- **A residual defect survives, in the opposite direction to the one fixed.**
  27/477 v1.2 reports state an abnormality in findings and call the study
  normal in the impression (§6.3). Constraint (ii) forbids the impression
  asserting what findings did not state; it does not forbid the impression
  omitting what findings did. No check in v1.2 covers this and no endpoint
  measures it.

---

## 8. Artifacts

| path | contents |
|---|---|
| `generation_v1.2_gateA_n477/generated_text/` | 477 generated reports + ground truth |
| `generation_v1.2_gateA_n477/per_case_results.csv` | status, retrieved uids, top-1 similarity, consistency status, latency |
| `generation_v1.2_gateA_n477/consistency_and_transplant.jsonl` | per-case consistency block and `transplant_scores()` — **Gate B's calibration input** |
| `generation_v1.2_gateA_n477/tier3_chexbert_*_labels.csv` | binarised CheXbert labels (frozen path) |
| `generation_v1.2_gateA_n477/tier1_rouge.csv` | per-case ROUGE-L |
| `generation_v1.2_gateA_n477/gate_a_endpoints.json` | every endpoint, CI and the verdict |
| `generation_v1.2_gateA_n477/evaluation_config.json` | full run configuration |
| `noise_floor_v1.1_rerun_n100/` | supplementary re-run and its summary |
| `reader_packet.md` | 40 blinded reports, no version information |
| `reader_packet_ANSWER_KEY.md` | held separately; do not open until both readers submit |
