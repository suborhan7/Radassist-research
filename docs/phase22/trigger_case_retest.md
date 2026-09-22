# Phase 22 — Re-test of the original trigger case

> **n = 1 case, 3 runs, qualitative. This proves nothing about rates.**
> Generation is non-deterministic at temperature 0 — the Gate A noise floor
> measured 67/100 v1.1 outputs differing on re-run
> ([`gate_a_results.md`](gate_a_results.md) §5) — which is why this was run
> three times rather than once. For rates, see Gate A (n=477).

| | |
|---|---|
| **Date** | 2026-09-22 |
| **v1.1 report** | `4e0a63d0bdb146518895f684611bb420`, status FINAL, created 2026-09-19 17:26:16, language `en` |
| **v1.2 code** | `phase22-v1.2` at `52884b0e` |
| **Query image** | `backend/uploaded_images/b3b2575a-998b-4c2b-8f78-dab3c72ac2ea.png` |
| **Image sha256** | `eda335d146c5215da954af976a5f0ae6247c4b50954e7076fd1d4ae553544ac6` |
| **dev.db backup** | `…/scratchpad/phase22_closing_backup/dev.db.20260922T024810.bak`, sha256 `5099d765312f5e61efd4cc72be34d37ae6eaa68994650aa665e40fc3233d4f9a` (matches source) |

**New report ids, for screenshotting in the UI:**

| run | report id |
|---|---|
| 1 | `3513df7a-f8bc-4d58-9a57-36b1c947e417` |
| 2 | `f5a220fd-8322-4bf1-8b49-1386acf9c260` |
| 3 | `59963299-17e8-4231-96dd-88761e79746e` |

---

## 1. Retrieval reproduced exactly

The same image was uploaded to the current backend. All five neighbours and
all five similarities are **identical** to those stored with the v1.1 report,
in the same rank order, on every one of the three runs:

| rank | uid | similarity | labels | same as v1.1? |
|---|---|---|---|---|
| **1** | **2477** | **0.8953** | **Atelectasis**; Calcinosis/Atherosclerosis; Cardiomegaly; Granuloma; Lung Opacity | ✓ |
| 2 | 3666 | 0.8582 | Atelectasis; Cardiomegaly; Lung Opacity; Pleural Effusion | ✓ |
| 3 | 1047 | 0.8509 | Normal | ✓ |
| 4 | 1752 | 0.8483 | Lung Opacity; Nodule/Mass | ✓ |
| 5 | 1102 | 0.8470 | Cardiomegaly; Edema/Congestion; Lung Opacity; Pleural Effusion | ✓ |

Neighbour #1 is an Atelectasis case at 0.895, exactly as expected. **Retrieval
is unchanged by v1.2** — only the prompt changed — so any difference in the
generated text is attributable to the prompt and not to different evidence.

**No ground truth exists for this case.** The uploaded file is not
byte-identical to any raw dataset image (checked against all 3,851 by sha256),
so it cannot be matched to a study uid and there is no reference report. Every
judgement below is about **internal consistency and provenance**, never about
whether a finding is clinically correct.

---

## 2. Before and after, side by side

### v1.1 (the stored report, what the screenshot showed)

> **FINDINGS:** The lungs are clear bilaterally, with no evidence of focal
> consolidation, pneumothorax, or pleural effusion. **Cardio mediastinal
> silhouette is unremarkable.** Visualized osseous structures of the thorax are
> without acute abnormality. There is a vague opacity in the right infrahilar
> region. There is also a **5 mm well-circumscribed nodule in the right upper
> lung**.
>
> **IMPRESSION:** **Stable cardiomegaly with right mediastinal shift. Stable
> interstitial markings and prominent bibasilar airspace opacities which
> likely represent atelectasis.**
>
> **RECOMMENDATION:** Consider CT thorax with contrast to further assess the
> **right perihilar** lung nodule.

### v1.2, all three runs

Runs 1–3 produced **identical findings and impression**; only the
recommendation differed (run 1 vs runs 2–3).

> **FINDINGS:** The lungs show bilateral interstitial markings with patchy
> bibasilar atelectasis. There is no evidence of focal consolidation,
> pneumothorax, or large pleural effusion. The cardiac silhouette is
> unremarkable.
>
> **IMPRESSION:** The chest X-ray shows bilateral interstitial markings with
> patchy bibasilar atelectasis, consistent with mild interstitial edema.
>
> **RECOMMENDATION (run 1):** No specific recommendation is made based on this
> report.
> **RECOMMENDATION (runs 2, 3):** Further evaluation with CT thorax with
> contrast is recommended to assess the bibasilar airspace opacities.

**Consistency block, all three runs, identical:**

```json
{"status": "partial", "checks_run": ["temporal", "contradiction"],
 "applicable_checks": ["temporal", "transplant", "contradiction"],
 "violations": [], "retry_count": 0}
```

`partial` because the transplant check has no Gate B threshold and so is not
counted as having run — not because anything failed.

---

## 3. Verdict per defect

### 3.1 Self-contradiction — **resolved in 3/3 runs**

Frozen-path CheXbert (same instrument as every Phase 22 number), findings and
impression labelled separately:

| | findings | impression | strict contradiction |
|---|---|---|---|
| **v1.1** | Cardiomegaly **Negative** | Cardiomegaly **Positive** | **YES — Cardiomegaly** |
| v1.2 run 1 | Cardiomegaly Negative | Cardiomegaly *(blank)* | none |
| v1.2 run 2 | Cardiomegaly Negative | Cardiomegaly *(blank)* | none |
| v1.2 run 3 | Cardiomegaly Negative | Cardiomegaly *(blank)* | none |

v1.1 stated the cardiomediastinal silhouette was unremarkable and then
asserted cardiomegaly. In all three v1.2 runs the findings still record the
cardiac silhouette as unremarkable and the impression no longer asserts
cardiomegaly.

### 3.2 Transplant from neighbour #1 — **resolved in 3/3 runs**

Max token 5-gram overlap ratio of the generated impression against each
neighbour's impression (production scoring functions):

| neighbour | v1.1 | run 1 | run 2 | run 3 |
|---|---|---|---|---|
| **2477 (#1)** | **0.50** (LCS 9) | **0.00** (LCS 2) | **0.00** (LCS 2) | **0.00** (LCS 2) |
| 3666 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1047 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1752 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1102 | 0.00 | 0.00 | 0.00 | 0.00 |

The provenance is unambiguous. Neighbour #1's stored impression reads:

> "1. **Stable cardiomegaly with right mediastinal shift.** 2. **Stable
> interstitial markings and prominent bibasilar airspace opacities** which
> [REDACTED] represent atelectasis."

v1.1's impression was that sentence pair with the numbering removed and
`[REDACTED]` replaced by "likely". **This was another patient's impression,
copied.** In v1.2 the overlap ratio is 0.00 and the longest common run is 2
tokens.

### 3.3 "Stable" with no prior study — **resolved in 3/3 runs**

| | prompt-list terms found | held-out terms found |
|---|---|---|
| **v1.1** | **`Stable`, `Stable`** | none |
| v1.2 run 1 | **none** | none |
| v1.2 run 2 | **none** | none |
| v1.2 run 3 | **none** | none |

Searched across findings, impression and recommendation. The held-out list —
never shown to the model — is also empty in all three runs, so this is not the
model substituting an unlisted synonym.

### 3.4 Nodule location mismatch — **no longer arises, but for a reason worth stating**

v1.1 placed a nodule in the **right upper lung** in findings and asked for CT
of the **right perihilar** nodule in the recommendation. That mismatch also
has a traceable origin: neighbour **1752** (rank 4, labels Lung Opacity;
Nodule/Mass) has the stored impression

> "1. **Right perihilar lung nodule. Recommend CT thorax with contrast to
> further assess.**"

so "right perihilar" was transplanted from a *different* neighbour than the
impression was. The v1.1 report drew from at least two other patients'
reports.

**In v1.2 the mismatch cannot arise, because no nodule is mentioned at all.**
All three runs omit the nodule from findings entirely. That is **not the same
as fixing the mislocation**, and it is recorded as such: without ground truth
for this image (§1) there is no way to say whether omitting the nodule is
correct or is a loss of a real finding. This is the same omission-direction
behaviour measured at 27/477 in
[`gate_a_results.md`](gate_a_results.md) §6.3, which no v1.2 check covers.

---

## 4. Summary

| defect | v1.1 | v1.2 (3 runs) |
|---|---|---|
| self-contradiction (Cardiomegaly) | present | **absent 3/3** |
| transplant from neighbour #1 | ratio 0.50, LCS 9 | **ratio 0.00 3/3** |
| "stable" with no prior study | 2 occurrences | **0 occurrences 3/3** |
| nodule location mismatch | present | **does not arise 3/3** — nodule omitted, not relocated |

All four defects from the original screenshot are absent from all three v1.2
runs, with retrieval held identical. **n = 1 case, 3 runs, qualitative.** The
rate evidence is Gate A's n=477.
