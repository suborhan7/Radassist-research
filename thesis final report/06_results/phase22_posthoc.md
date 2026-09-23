# Phase 22, part 3 — the post-hoc analyses

> ## **NOTHING IN THIS FILE WAS PRE-REGISTERED.**
> None of these analyses was in the run plan. **No number here is a criterion
> and the Gate A verdict is not revisited.** They are reported because several
> of them change how [`phase22_gate_a.md`](phase22_gate_a.md) should be read —
> in one case decisively, and in two cases *against* the fix.

Same bootstrap configuration throughout (B=2,000, seed 42, percentile, paired),
same frozen CheXbert evaluation path for both arms, same 477 uids.
Source: `docs/phase22/gate_a_results.md` §6; raw
`scratch/phase22_diagnosis/out_posthoc_gate_a.txt`.

---

## 1. Is the improvement just shorter text? — **No**

This is the obvious alternative explanation for every Gate A result, and it was
flagged as untested in the original write-up.

### (a) Micro precision and recall, separately — the decisive test

| | v1.1 | v1.2 | diff | 95 % CI |
|---|---|---|---|---|
| micro **precision** | 0.5112 | 0.5863 | **+0.0750** | [+0.0400, +0.1110] |
| micro **recall** | 0.5395 | 0.5909 | **+0.0514** | [+0.0178, +0.0859] |

**Both rose, and both CIs exclude zero.** If shortening were the mechanism,
precision would rise (fewer assertions → fewer false positives) while recall
**fell** (fewer assertions → fewer true positives caught). **Recall rose
instead.** v1.2 writes less and catches *more* of what the reference says. That
is not what truncation looks like.

### (b) Per-label precision, recall and support — **no pooling**

Support is reference-positive cases, identical across arms by construction.

| label | support | P v1.1 | R v1.1 | P v1.2 | R v1.2 | |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 6 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Cardiomegaly | 25 | 0.250 | 0.440 | 0.364 | 0.320 | |
| Lung Opacity | 46 | 0.216 | 0.239 | 0.250 | 0.283 | |
| Lung Lesion | 15 | 0.120 | 0.200 | 0.154 | 0.133 | |
| Edema | 9 | 0.143 | 0.222 | 0.364 | 0.444 | **support < 10 — unreliable** |
| Consolidation | 4 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| **Pneumonia** | 20 | 0.214 | **0.150** | 0.100 | **0.050** | **clearly WORSE** |
| Atelectasis | 27 | 0.140 | 0.259 | 0.171 | 0.259 | |
| Pleural Effusion | 17 | 0.333 | 0.294 | 0.364 | 0.235 | |
| Pleural Other | 5 | 0.111 | 0.200 | 0.333 | 0.200 | **support < 10 — unreliable** |
| Fracture | 7 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Support Devices | 2 | 0.000 | 0.000 | 0.000 | 0.000 | **support < 10 — unreliable** |
| Pneumothorax | 1 | n/a | 0.000 | n/a | 0.000 | **support < 10 — unreliable** |
| **No Finding** | **322** | 0.777 | 0.714 | 0.766 | **0.804** | carries the aggregate |

**Seven of fourteen labels have support below 10** and their figures should not
be read as estimates of anything. Among the seven with usable support the
movements are **mixed**: Pneumonia is clearly worse, Cardiomegaly trades recall
for precision, and **the micro-F1 improvement is substantially a `No Finding`
improvement** (support 322, recall 0.714 → 0.804). The per-label picture is
**not uniformly favourable**, and the thesis must not present it as one.

### (c) Does v1.2 stay silent about findings the reference reports? — **No**

Cases where the generated impression carries **no** positive label on the 13
real conditions while the **reference** impression carries at least one:

```
v1.1: 56/477 = 0.1174   (gen-empty 338, ref-has 116)
v1.2: 56/477 = 0.1174   (gen-empty 365, ref-has 116)
```

**Identical — 56 in both.** v1.2's impressions are empty of positive labels
more often overall (338 → 365), but **the extra silence falls entirely on cases
where the reference is also negative.** It does not miss a real finding more
often than v1.1 did. This is the strongest single piece of evidence against the
shortening-harms hypothesis.

### (d) Word-count distributions — the shortening is real

| field | version | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|---|
| findings | v1.1 | 10 | 33.0 | 48.0 | 61.0 | 181 |
| findings | **v1.2** | 6 | 24.0 | **30.0** | 35.0 | 109 |
| impression | v1.1 | 1 | 4.0 | 9.0 | 18.0 | 73 |
| impression | **v1.2** | 1 | 4.0 | **5.0** | 12.0 | 62 |

Both sections shortened, findings substantially (median 48 → 30, **−38 %**),
and the long tail compressed (max 181 → 109).

### (e) Temporal rate restricted to FINDINGS only — the less confounded test

| terms | v1.1 | v1.2 | diff | 95 % CI |
|---|---|---|---|---|
| frozen 5-term | 0.2872 (137/477) | **0.0126** (6/477) | −0.2746 | [−0.3145, −0.2348] |
| run-plan 9-term | 0.3208 (153/477) | 0.0210 (10/477) | −0.2998 | [−0.3417, −0.2600] |

**Findings length fell 38 %; the findings temporal rate fell 96 %** (137 → 6).
A 38 % length cut cannot produce a 96 % reduction unless temporal language were
concentrated in exactly the removed text, which the per-section numbers give no
reason to believe. **Instruction (iii) changed what the model writes, not
merely how much.**

---

## 2. Transplant on a common denominator — the confound removed

Gate A §3.4 flagged that the scorable denominator fell 353 → 280, so part of
the transplant improvement might be unscorability. Restricting to uids scorable
in **both** arms removes the confound entirely:

```
scorable in v1.1 only : 92
scorable in v1.2 only : 19
scorable in BOTH      : 261

harmful transplant, common denominator, paired, n=261:
  v1.1 = 0.0805 (21/261)   v1.2 = 0.0383 (10/261)
  diff = −0.0421   CI [−0.0728, −0.0153]
```

**The improvement survives, with the CI still excluding zero.** On the
identical 261 cases, harmful transplantation roughly halves. The denominator
shift inflated the headline figure but **did not create it**.

---

## 3. A residual defect, in the **opposite** direction to the one fixed

Phase 22's constraint (ii) forbids the impression asserting what findings did
not state. **It says nothing about the reverse** — an impression *omitting* what
findings *did* state — and that failure mode survives.

Cases where generated **findings** carry ≥1 CheXbert-positive real condition
while the generated **impression** carries none:

```
v1.2:  27/477 = 0.0566
v1.1:  90/477 = 0.1887   (context only)
```

v1.2 is roughly **three times better** here than v1.1, unprompted — but **27
cases remain**, and they are a real internal inconsistency. This is measured
against the report's **own** findings, not the reference: §1(c) shows v1.2 does
not miss *reference* findings more often. The defect is **self-inconsistency,
not under-detection.**

Five cases sampled at seed 20260922; **three of five are genuine omissions**:

> **uid 951** — *Findings:* "…Mild right basilar **atelectasis** and relative
> elevation of the right hemidiaphragm are noted…"
> *Impression:* "The chest X-ray is **normal**, with no evidence of active
> cardiopulmonary disease."

> **uid 2486** — *Findings:* "…The right lung base shows **minimal opacity**,
> which may represent minimal right basilar airspace disease."
> *Impression:* "The chest X-ray is **normal**, with no acute cardiopulmonary
> abnormality."

> **uid 3461** — *Findings:* "**The lung opacities are seen throughout the
> lungs**, with more focal streaky bibasilar opacities…"
> *Impression:* "**No acute cardiopulmonary abnormality**"  ← **the worst case**

Two others (2982, 3681) are arguably **labeler artifacts**: the positive label
is `Support Devices` — a device, not a pathology, with reference support 2 and
already flagged unreliable in §1(b).

**This defect is not covered by any check in v1.2 and no endpoint measures it.**
Recorded for Gate B/C scoping.

---

## What the post-hoc work settles, and what it does not

**Settles:** the shortening explanation is refuted on four independent tests,
and the transplant improvement survives the denominator confound.

**Does not settle, and argues the other way:** the micro-F1 gain is
substantially a `No Finding` gain; Pneumonia got clearly worse; and a
27/477 self-inconsistency defect survives in a direction the fix never
addressed. **A thesis that reports only §1(a)–(c) and §2 would be reporting
half of this file.**
