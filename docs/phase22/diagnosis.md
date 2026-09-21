# Phase 22 — Step 0: Diagnosis of the FINDINGS/IMPRESSION Grounding Failure

**Status:** READ-ONLY diagnosis. No source file, prompt, config, migration or
ChromaDB collection was modified. No fix is proposed as chosen; §4 lists
candidates only.

**Pre-flight check (required by the brief).** No Phase 21 run was active.
`Get-Process | Where-Object { $_.ProcessName -match 'python|uvicorn' }` returned
a count of `0`, and `Get-CimInstance Win32_Process -Filter "Name like '%python%'"`
returned no rows. Nothing was stopped, restarted or interfered with.

**Trigger.** A live report whose FINDINGS said the cardiomediastinal silhouette
was unremarkable while its IMPRESSION said *"Stable cardiomegaly with right
mediastinal shift…"* — near-verbatim identical to retrieved neighbour #1
(Atelectasis, similarity 0.895, a different patient); "stable" implying a prior
comparison for a patient with no prior study; and a RECOMMENDATION mislocating
the nodule. Severity S1.

**Scope note on samples.** Phase 21 Arm C (`full`, n=477) and Phase 20 (n=460)
are measured and reported **separately throughout**. They are never pooled, and
no difference between them is computed or implied — consistent with
`docs/methodology/phase21_ablation_architecture.md` §5.3, which fixes that these
two are not comparable (different sample size, different code, unmeasured
per-report defect magnitude).

---

## 1. Code path trace

Generation runs through exactly one chain, with one LLM call:

```
app/api/generation.py  ->  ReportGenerationService.generate()
   report_generation_service.py:124   reconstruct_session_evidence()
   report_generation_service.py:134   ContextBuilder.build()
   report_generation_service.py:144   LLMOrchestrator.generate_draft()
        llm_orchestrator.py:57        PromptBuilder.build_generation_prompt()
        llm_orchestrator.py:58        one LLM call -> all 7 fields at once
   report_generation_service.py:146   ResponseValidator.validate_semantic()
   report_generation_service.py:201   ReportFormatter.format()
   report_generation_service.py:257   db.add(report_record)  -- unconditional
```

### 1a. Does the IMPRESSION prompt include the FINDINGS text generated for this same report? Does the RECOMMENDATION prompt?

**No — and structurally it cannot, because there is no separate IMPRESSION or
RECOMMENDATION prompt. There is no section-wise generation.**

All seven fields are produced by a single completion.
[prompt_builder.py:348-368](../../backend/app/services/prompt_builder.py#L348-L368)
asks for all of them in one response:

> `"Output exactly these 7 fields, in this exact order, each marker on its own line…"`

and [llm_orchestrator.py:56-58](../../backend/app/services/llm_orchestrator.py#L56-L58)
issues exactly one call for the lot:

```python
def generate_draft(self, context: ClinicalContext, language: str) -> ReportContent:
    prompt = self._prompt_builder.build_generation_prompt(context, language)
    last_raw_response = self.generate_freeform(prompt)
```

So FINDINGS and IMPRESSION are **siblings drawn from the same evidence block, not
a derivation of one from the other**. Nothing in the prompt states that IMPRESSION
must summarise the FINDINGS this report just produced, and nothing sequences them.
Their only shared anchor is the retrieved-neighbour text — which is precisely the
mechanism that lets IMPRESSION track a neighbour while FINDINGS does not.

**Section regeneration is strictly worse.** `build_section_regeneration_prompt`
([prompt_builder.py:198-216](../../backend/app/services/prompt_builder.py#L198-L216))
assembles:

```python
sections = [
    self._section_regeneration_role_instruction(field_label),
    self._language_instruction(language),
    self._grounding_instruction(),
    self._confidence_instruction(context.voted_labels),
    self._evidence_section(context.evidence_summary),
]
```

The report's **own current content is not in that list at all**. Confirmed at the
call site: `ReportEditService.regenerate_section()`
([report_edit_service.py:133-193](../../backend/app/services/report_edit_service.py#L133-L193))
rebuilds a `ClinicalContext` from retrieval evidence only and passes it straight
in (line 191) — it never reads `record.final_content`. Regenerating IMPRESSION
therefore happens **without the model ever seeing the FINDINGS it must be
consistent with**. The role instruction actively reinforces this:

> `"You are not revising, reviewing, or restating any other section -- just this one."`

`_report_content_section()` — the helper that *does* serialise a report's seven
fields — exists ([prompt_builder.py:252-262](../../backend/app/services/prompt_builder.py#L252-L262))
and is used by the explanation and comparison prompts, but is **not** called by
either generation path.

### 1b. Are retrieved neighbours' findings/impressions passed to the LLM verbatim? Is any instruction present that forbids copying them?

**Verbatim: yes. Forbidding instruction: none exists.**

`ContextBuilder._build_text_evidence()`
([context_builder.py:178-192](../../backend/app/services/context_builder.py#L178-L192))
collects `case.findings` and `case.impression` with no transformation — only
de-duplication. `PromptBuilder._evidence_section()`
([prompt_builder.py:411-424](../../backend/app/services/prompt_builder.py#L411-L424))
renders them as a numbered list of raw strings:

```python
lines.append("Retrieved findings from similar cases (most similar first):")
for i, text in enumerate(evidence_summary.findings_evidence, start=1):
    lines.append(f"{i}. {text}")
...
lines.append("Retrieved impressions from similar cases (most similar first):")
for i, text in enumerate(evidence_summary.impressions_evidence, start=1):
    lines.append(f"{i}. {text}")
```

The prompt never says these sentences belong to **other patients**. It labels them
"from similar cases" and nothing more — no patient identity, no attribution
boundary, no instruction to paraphrase, and no prohibition on reuse.

The only grounding instruction in force
([prompt_builder.py:371-378](../../backend/app/services/prompt_builder.py#L371-L378))
is, read literally, an instruction *toward* copying:

> `"You must base your report ONLY on the evidence provided below. Do not invent,`
> `infer, or hallucinate any finding, measurement, or clinical detail that is not`
> `directly supported by the evidence below. If the evidence is insufficient to`
> `support a finding, do not include it."`

Every constraint here is anti-invention. None is anti-transplantation. A model
that copies a neighbour's impression verbatim has satisfied this instruction
perfectly: the text is maximally "supported by the evidence below". **The prompt's
only defence is aimed at the wrong failure mode.**

### 1c. Does the prompt say whether a prior study exists, and does it restrict temporal language?

**Neither. The generation prompt has no concept of a prior study, and places no
restriction on temporal or comparison language.**

The full inventory of `build_generation_prompt`
([prompt_builder.py:116-137](../../backend/app/services/prompt_builder.py#L116-L137))
is: role, language, schema, grounding, confidence, evidence, optional
questionnaire, optional clinical notes. No prior-study field is assembled, and
none exists on `ClinicalContext` to assemble. Priors live in an entirely separate
subsystem (`ComparisonService`, `app/models/comparison.py`) that the generation
path never touches.

The project **already knows how to write this restriction and has done so — in the
other path only.** `_comparison_grounding_instruction()`
([prompt_builder.py:282-308](../../backend/app/services/prompt_builder.py#L282-L308)):

> `'You must NOT use the words or phrases "improved", "worsened", "progression",`
> `"regression", "increasing", or "decreasing" UNLESS you are directly restating`
> `one of the deterministic facts above…'`

That rule is applied only where a genuine prior exists and the comparison has
already been computed deterministically. The generation prompt — the one path
where no prior exists and temporal language is therefore *always* unsupported —
has no equivalent clause. The safeguard is inverted relative to where it is needed.

### 1d. Where does validate_semantic() run, what does it check, and does it gate anything?

**It runs at [report_generation_service.py:146-148](../../backend/app/services/report_generation_service.py#L146-L148), and it gates nothing.**

It checks exactly four things
([response_validator.py:40-91](../../backend/app/services/response_validator.py#L40-L91)):

1. `missing_findings` — FINDINGS empty.
2. `missing_impression` — IMPRESSION empty.
3. `unsupported_terms` — a taxonomy class appears in the text but in no retrieved case's labels.
4. `top_label_unreflected` — top voted label (agreement ≥ 0.5) absent from the text.

Three structural facts make it incapable of catching this failure:

- **It concatenates the two sections before looking at them** (line 49):
  ```python
  combined_text_lower = f"{content.findings} {content.impression}".lower()
  ```
  FINDINGS and IMPRESSION are merged into one string, so *no contradiction between
  them is representable*. A report saying "silhouette unremarkable" in one and
  "cardiomegaly" in the other is, to this validator, a single blob containing both.
- **Its hallucination check would rate the reported failure clean.** `unsupported_terms`
  flags a term only when it is absent from the retrieved evidence's labels. A finding
  **transplanted from a retrieved neighbour is by construction present in that
  evidence**, so copying is the one thing check 3 can never flag.
- **It has no temporal-language check at all**, and no notion of a prior study.

Confirmed non-gating. The service is documented as non-gating by design
([response_validator.py:5-10](../../backend/app/services/response_validator.py#L5-L10)):
*"produces warnings for human review, never a pass/fail gate that triggers
automated retry (frozen Phase 8 Decision 1)"*. And the code matches: between the
`validate_semantic()` call at line 146 and the unconditional `self._db.add(...)`
at line 257, `validation_result` is read only at line 228
(`validation_warnings=list(validation_result.warnings)`) — persisted as a list,
never branched on. The report is saved with `status=ReportStatus.AI_DRAFT`
regardless. `is_clean` has exactly one consumer in the whole backend,
[app/api/generation.py:79](../../backend/app/api/generation.py#L79), where it is
serialised into the response body. No `if` anywhere tests it.

> Note: the brief's phrasing "confirm it gates nothing downstream" matches what the
> code does, but the non-gating is a deliberate frozen decision (Phase 8 Decision 1),
> not an oversight. It is a gap in *coverage*, not a broken gate.

---

## 2. Prevalence measurements

Scripts: `scratch/phase22_diagnosis/`. Raw outputs saved as
`out_2a_transplant.txt`, `out_2b_temporal.txt`, plus per-case CSVs.

### 2a. Verbatim transplant — Phase 21 Arm C, n=477

For each generated IMPRESSION, overlap was computed against **every** one of its
retrieved neighbours' impressions (`retrieved_uids` from `per_case_results.csv`,
resolved against `master_metadata.csv`'s `impression_clean`), keeping the maximum.
Tokenisation: lowercase, strip non-alphanumerics, whitespace split. 0 neighbour
UIDs failed to resolve.

Command: `.venv/Scripts/python.exe scratch/phase22_diagnosis/measure_transplant.py`

```
cases scored (status=completed): 477
neighbour uids not found in master_metadata: 0
generated impressions with <5 tokens (5-gram ratio undefined, excluded from (i)): 124

(i)  max token 5-gram overlap ratio vs any retrieved neighbour impression:
     {'n': 353, 'min': 0.0, 'q1': 0.0, 'median': 0.2857, 'q3': 0.8837, 'max': 1.0}
(ii) max longest-common-contiguous-token-substring length (tokens):
     {'n': 477, 'min': 0.0, 'q1': 4.0, 'median': 5.0, 'q3': 8.0, 'max': 42.0}

    cases with max 5-gram overlap ratio >= 0.25: 191/353 (54.1%)
    cases with max 5-gram overlap ratio >= 0.5:  145/353 (41.1%)
    cases with max 5-gram overlap ratio >= 0.75: 104/353 (29.5%)
    cases with max 5-gram overlap ratio >= 0.9:   88/353 (24.9%)
    cases with max 5-gram overlap ratio >= 1.0:   83/353 (23.5%)

    cases with max LCS >= 5 tokens:  242/477 (50.7%)
    cases with max LCS >= 10 tokens:  88/477 (18.4%)
    cases with max LCS >= 15 tokens:  43/477 (9.0%)
    cases with max LCS >= 20 tokens:  28/477 (5.9%)
    cases with max LCS >= 30 tokens:  11/477 (2.3%)
```

**83 of 353 scorable impressions (23.5%) have a 5-gram overlap ratio of exactly
1.0** — every single 5-gram in the generated impression also occurs in one
neighbour's impression. This is not stylistic similarity; it is reproduction.

Top 10 by 5-gram ratio (all 1.0), with the matched neighbour:

| uid | ratio | LCS | nb | generated impression (truncated) |
|---|---|---|---|---|
| 2434 | 1.0 | 32 | 9 | Increased size of density in the left cardiophrenic [REDACTED]. Primary differential considerations include… |
| 2255 | 1.0 | 30 | 480 | Heart size, mediastinal silhouette, pulmonary vascularity are within normal limits… |
| 3773 | 1.0 | 29 | 517 | Calcified right basilar nodule compatible with granuloma / histoplasmoma… |
| 429 | 1.0 | 27 | 3604 | The lungs are clear. No focal consolidation to suggest pneumonia or active tuberculous infection… |
| 3866 | 1.0 | 18 | 3676 | **Redemonstration of** diffuse bilateral pulmonary fibrosis with relative sparing… |
| 2323 | 1.0 | 18 | 960 | No acute findings. Please note that fractures may not be demonstrated… |
| 842 | 1.0 | 15 | 1982 | Overall, well-expanded and clear lungs. Mediastinal contour within normal limits… |
| 3740 | 1.0 | 14 | 1064 | **Stable** elevated right hemidiaphragm with questionable subtle increased right basilar airspace disease… |
| 3790 | 1.0 | 14 | 267 | Small bilateral pleural effusions with a few scattered areas of patchy bilateral airspace disease. |
| 3707 | 1.0 | 12 | 413 | Heart size is normal and lungs are clear. No evidence of tuberculosis. |

Top 10 by LCS (longest contiguous runs): uids 2932 (42 tokens), 2974 (39), 2728
(38), 2269 (37), 3512 (32), 2434 (32), 1597 (31), 3687 (30), 3073 (30), 224 (30).
Full per-case data with both neighbour texts: `transplant_armC_n477.csv`.

Note uids **3866** and **3740**: the transplanted span *carries the temporal term
with it* ("Redemonstration of…", "Stable elevated…"). §2b's temporal finding and
§2a's transplant finding are not independent — copying is one mechanism by which
unsupported temporal language enters.

**Measurement honesty notes.**
- 124 of 477 generated impressions have fewer than 5 tokens, so measure (i) is
  undefined for them; they are excluded from (i)'s denominator (n=353) and retained
  in (ii)'s (n=477). Denominators are stated on every figure above rather than
  silently switched.
- Some generated impressions carry a literal `"Impression: "` prefix. It was **not**
  stripped. That prefix contributes unmatchable 5-grams, so it can only *lower* the
  ratio — every figure here is a conservative lower bound.
- The corpus text is PHI-masked (`[REDACTED]`), identically on both sides of each
  comparison, so masking does not inflate or deflate overlap.

**Phase 20 — not computable, and not estimated.** Phase 20's
`per_case_results.csv` has no `retrieved_uids` column (header:
`study_uid,status,reason,findings_bleu,…`), and `grep -rl retrieved_uids ml/outputs/`
matches only the five Phase 21 arm files. The neighbour identities for Phase 20's
460 generations were never persisted in any artifact in this repository. Measure 2a
therefore **cannot be computed for Phase 20 from existing outputs**, and no
substitute number is offered. (Phase 20's own Fracture investigation recovered
neighbours by matching `ai_draft_content` against `backend/dev.db` — that route may
still exist, but it was not attempted here and is not assumed to work.)

### 2b. Temporal language with no prior study

**Every case in both harnesses had no prior study.** `run_generation_eval.py`
performs `POST /retrieve` then `POST /generate-report` per case
(lines 191, 212-215) and never creates a second report for a patient or calls the
comparison path. Denominator is therefore all completed cases, and the rate below
is the rate of *unsupported* temporal language, not merely its frequency.

Command: `.venv/Scripts/python.exe scratch/phase22_diagnosis/measure_temporal.py`

**Phase 21 Arm C (full), n=477** — cases with no prior study: 477/477

```
term                    FINDINGS  IMPRESSION   EITHER
stable                        96          44      122
unchanged                     27           6       32
interval                      27           5       32
again                          8           0        8
redemonstrated                 4           1        5

UNION of the five terms, either section: 167/477 (35.0%)
```

**Phase 20 (separate run — never pooled with Phase 21), n=460** — 460/460 no prior

```
term                    FINDINGS  IMPRESSION   EITHER
stable                        64          29       79
unchanged                      6           3        9
interval                      13           6       14
again                          1           0        1
redemonstrated                 2           0        2

UNION of the five terms, either section: 97/460 (21.1%)
```

Additional comparison-implying terms, counted separately and **not** pooled into
the figures above — Arm C: `previous/prior` 52, `compared` 11, `persistent` 9,
`improved/worsened` 4, `new` 0. Phase 20: `previous/prior` 27, `persistent` 9,
`compared` 8, `improved/worsened` 2, `new` 0.

Real examples from Arm C (uid/section):

```
[106/findings]  Mild [REDACTED] deformity of T12, stable.
[1178/findings] A 5 mm stable right apical nodule is noted.
[1330/findings] A well-circumscribed 11 mm right upper lobe nodule is present,
                unchanged from a previous examination 7 years ago.
[1448/findings] The heart and lungs have [REDACTED] [REDACTED] in the interval.
[1451/impression] The chest X-ray is consistent with stable interstitial fibrotic changes…
```

uid 1330 is the clearest instance: the report asserts a specific prior study
**seven years ago** that does not exist and that the system has no field to
represent.

> Caveat stated rather than buried: "stable" has a non-temporal clinical sense
> (e.g. a clinically stable patient). These counts are lexical, from word-boundary
> regex, not adjudicated readings. The examples above were read individually and
> are genuinely temporal, but the 167 and 97 totals are not individually adjudicated.

### 2c. Internal contradiction — CheXbert on FINDINGS and IMPRESSION separately

**Why the existing artifacts were insufficient.** `tier3_chexbert_*_labels.csv`
already store findings and impression labels separately, but binarised:
`to_present_binary()` ([score_chexbert.py:166-169](../../ml/evaluation/score_chexbert.py#L166-L169))
maps `{Blank, Negative} -> 0` and `{Positive, Uncertain} -> 1`. A `0` therefore
cannot distinguish *explicitly negated* from *never mentioned*, and "positive in
one section, **negative** in the other" is not expressible from those files at all.
The labeler was re-run — same frozen `score_chexbert.py` model code, same checkpoint
(`…/RRG_scorers/snapshots/6646433b3ad83a10f6e141db76d0ece44312b236/chexbert.pth`),
same tokenisation — keeping the raw 4-class index
(`{0: Blank, 1: Positive, 2: Negative, 3: Uncertain}`).

Command: `ml/evaluation/.venv-bertscore/Scripts/python.exe scratch/phase22_diagnosis/measure_contradiction.py`
Raw per-case classes: `raw_classes_phase21_armC.csv`, `raw_classes_phase20.csv`.

**"No Finding" is excluded from the strict totals** — its head has only 2 outputs
in the real architecture ([score_chexbert.py:105](../../ml/evaluation/score_chexbert.py#L105)),
so it can never emit class 2 and a contradiction is not expressible for it. It is
reported in the wider table only.

**STRICT contradiction** = Positive(1) in one section AND Negative(2) in the other.
Per label, **not pooled across labels**:

*Phase 21 Arm C (full), n=477*

| label | F+/I− | F−/I+ | total | % of n |
|---|---|---|---|---|
| Enlarged Cardiomediastinum | 0 | 0 | 0 | 0.0% |
| Cardiomegaly | 1 | 10 | 11 | 2.3% |
| Lung Opacity | 2 | 5 | 7 | 1.5% |
| Lung Lesion | 1 | 1 | 2 | 0.4% |
| Edema | 0 | 0 | 0 | 0.0% |
| Consolidation | 0 | 0 | 0 | 0.0% |
| Pneumonia | 0 | 0 | 0 | 0.0% |
| Atelectasis | 0 | 0 | 0 | 0.0% |
| Pneumothorax | 0 | 0 | 0 | 0.0% |
| Pleural Effusion | 0 | 1 | 1 | 0.2% |
| Pleural Other | 0 | 0 | 0 | 0.0% |
| Fracture | 1 | 0 | 1 | 0.2% |
| Support Devices | 0 | 0 | 0 | 0.0% |

Cases with ≥1 strict contradiction on any of the 13 four-class labels:
**22/477 (4.6%)**.

*Phase 20 (separate run — never pooled with Phase 21), n=460*

| label | F+/I− | F−/I+ | total | % of n |
|---|---|---|---|---|
| Enlarged Cardiomediastinum | 0 | 1 | 1 | 0.2% |
| Cardiomegaly | 2 | 3 | 5 | 1.1% |
| Lung Opacity | 1 | 0 | 1 | 0.2% |
| Atelectasis | 1 | 0 | 1 | 0.2% |
| Pleural Effusion | 0 | 1 | 1 | 0.2% |
| *(all 8 other labels)* | 0 | 0 | 0 | 0.0% |

Cases with ≥1 strict contradiction: **9/460 (2.0%)**.

**Cardiomegaly is the dominant contradiction label in both runs** — 11 of Arm C's
22 cases, 5 of Phase 20's 9 — and the trigger report is a Cardiomegaly case. The
asymmetry is directional: **F−/I+ 10 vs F+/I− 1** in Arm C. The IMPRESSION asserts
cardiomegaly that the FINDINGS explicitly negated, not the reverse. That is exactly
the reported live failure, and uid **2181** reproduces it almost exactly:

```
uid=2181  labels=['Cardiomegaly']
  FINDINGS  : …The cardiac and mediastinal contours are within normal limits…
  IMPRESSION: Cardiomegaly. Indistinct vascular margination which may be secondary
              to bronchovascular crowding however differential diagnosis includes
              mild pulmonary edema, atypical infection, inflammation.

uid=2322  labels=['Cardiomegaly']
  FINDINGS  : The heart is enlarged…
  IMPRESSION: Mild stable cardiomegaly without acute disease…

uid=2815  labels=['Cardiomegaly']
  FINDINGS  : …Heart size is as is within normal limits.
  IMPRESSION: …Stable cardiomegaly without overt pulmonary edema.
```

**WIDER asymmetry** (present in one section, absent-or-negated in the other) is
reported separately because it **conflates "negated" with "never mentioned" and is
therefore not a contradiction measure**. It is the ceiling of what the stored
binarised artifacts could have shown. Arm C: **300/477 (62.9%)** of cases have ≥1
asymmetry on ≥1 of 14 labels (largest contributors: No Finding 188, Lung Opacity
67, Atelectasis 49, Cardiomegaly 39). Phase 20: **243/460 (52.8%)** (No Finding
144, Lung Opacity 63, Atelectasis 40). Most of this is ordinary summarisation —
an impression legitimately omits detail — and it must **not** be read as a
contradiction rate. The defensible contradiction figures are the strict ones:
4.6% and 2.0%.

> Caveat: CheXbert has a known, separately-confirmed negation bug on this corpus
> (development_log.md §1c of the Fracture finding: *"No acute, displaced rib
> fractures"* scored Fracture=Positive). Strict counts here are labeler output,
> not adjudicated readings. The ten Arm C cases printed in the raw output were
> read individually and are genuine; the remaining twelve were not.

---

## 3. Confirmed root causes

**RC1 — No section-to-section grounding; IMPRESSION is never conditioned on this report's FINDINGS.**
One LLM call emits all 7 fields as siblings of the evidence block
([llm_orchestrator.py:56-58](../../backend/app/services/llm_orchestrator.py#L56-L58),
[prompt_builder.py:348-368](../../backend/app/services/prompt_builder.py#L348-L368)).
Section regeneration is worse: `build_section_regeneration_prompt`
([prompt_builder.py:198-216](../../backend/app/services/prompt_builder.py#L198-L216))
omits the report's own content entirely and instructs the model not to consider
other sections. **Evidence:** 22/477 strict contradictions in Arm C (§2c), 10 of
11 Cardiomegaly cases in the F−/I+ direction.

**RC2 — Neighbour text is rendered verbatim with no attribution boundary and no anti-copying instruction.**
[context_builder.py:178-192](../../backend/app/services/context_builder.py#L178-L192)
passes prose through untransformed;
[prompt_builder.py:411-424](../../backend/app/services/prompt_builder.py#L411-L424)
numbers it without stating it belongs to other patients. The only grounding rule
([prompt_builder.py:371-378](../../backend/app/services/prompt_builder.py#L371-L378))
forbids *invention* and thereby rewards *copying*. **Evidence:** 83/353 (23.5%)
of Arm C impressions have 5-gram overlap ratio 1.0 with a neighbour; max contiguous
copied run 42 tokens (§2a).

**RC3 — No prior-study state exists in the generation context, and no temporal-language restriction is applied.**
`ClinicalContext` has no prior-study field; `build_generation_prompt`
([prompt_builder.py:116-137](../../backend/app/services/prompt_builder.py#L116-L137))
assembles none. The project's temporal-language prohibition exists only in
`_comparison_grounding_instruction()`
([prompt_builder.py:282-308](../../backend/app/services/prompt_builder.py#L282-L308)),
i.e. only where a prior *does* exist. **Evidence:** 167/477 (35.0%) of Arm C
reports use ≥1 of the five terms with no prior study; Phase 20 97/460 (21.1%) (§2b).

**RC4 — The one semantic check cannot represent this failure class, and gates nothing.**
`validate_semantic()` concatenates the sections before inspection
([response_validator.py:49](../../backend/app/services/response_validator.py#L49)),
so cross-section contradiction is unrepresentable; its `unsupported_terms` check
([response_validator.py:51-55](../../backend/app/services/response_validator.py#L51-L55))
flags only terms *absent* from retrieved evidence, so a transplanted finding is
structurally exempt; it has no temporal check. Its result is persisted as warnings
(line 228) and never branched on — the report is written unconditionally at line 257.

**RC1–RC3 are independent generators of the trigger report's three defects**
(contradiction, transplantation, unsupported "stable"), and **RC4 is why none of
the three was caught.** §2a's uids 3866/3740 show RC2 and RC3 can also compound:
a copied span imports its own temporal language.

**Relationship to the Phase 20 Fracture finding.** development_log.md's Fracture
investigation established that *"the fracture finding belongs to a retrieved
neighbor case, not to the actual query patient"* in 18/18 cases, and concluded
*"nothing in the generation step currently verifies that a finding present in
retrieved evidence text actually belongs to the case being reported on."* RC2 is
that same mechanism, now measured at corpus scale on the impression field rather
than inferred from one label's F1 anomaly. This diagnosis **confirms and
generalises** that finding; it does not restate it.

---

## 4. Candidate fixes (enumerated only — none chosen, no fix code written)

**Addressing RC1 (section grounding)**
- C1. Two-stage generation: generate FINDINGS first, then pass it into a second call for IMPRESSION/RECOMMENDATION. Highest fidelity; changes latency, the frozen single-call contract, and `StructuralValidator`'s 7-field parse.
- C2. Keep one call, add an explicit prompt constraint that IMPRESSION must summarise only what FINDINGS states. Cheapest; unenforced.
- C3. Include the report's current content in `build_section_regeneration_prompt` (reusing the existing, already-tested `_report_content_section()`). Narrow, fixes only the regeneration path — but that path currently has *no* cross-section information at all.
- C4. Post-generation deterministic consistency check (CheXbert or taxonomy-based) over FINDINGS vs IMPRESSION separately, surfaced as a warning.

**Addressing RC2 (transplantation)**
- C5. Label neighbour text in-prompt as belonging to other patients, with an explicit instruction not to reuse its wording or transfer its specific findings.
- C6. Replace verbatim neighbour prose with an abstracted/structured summary in the evidence block (changes what Arm C means; interacts with the Phase 21 ablation's definition of `full`).
- C7. Post-generation n-gram overlap detector against the case's own neighbours, using §2a's measure, as a warning or a regeneration trigger.
- C8. Cap the number or length of neighbour impressions rendered.

**Addressing RC3 (temporal language)**
- C9. Add an explicit no-prior-study statement plus a temporal-term prohibition to `_grounding_instruction()`, modelled on the existing `_comparison_grounding_instruction()`.
- C10. Carry real prior-study state into `ClinicalContext` and make the instruction conditional on it (larger; touches Phase 5's frozen entity).
- C11. Deterministic post-generation temporal-term scan, gated on whether a prior exists.

**Addressing RC4 (detection)**
- C12. Extend `validate_semantic()` to inspect FINDINGS and IMPRESSION separately rather than concatenated, adding cross-section contradiction as a new warning type.
- C13. Decide explicitly whether any of these new checks should *gate* rather than warn — this would revisit frozen Phase 8 Decision 1, which deliberately chose warn-only, and must be a stated decision rather than a side effect.

**Cross-cutting constraints any fix must respect (not a fix, a boundary):** every
prompt change alters what Phase 21's arms measured, so re-running affected arms is
part of the cost; `shared/embeddings/biomedclip_embedder.py` and the retrieval path
are frozen and none of the above requires touching them; and per CLAUDE.md no
parameter or threshold may be hardcoded into a script.

---

## 5. Step 1 follow-ups

Added after review of §1–§4. Same read-only constraint; no source file was
modified. Scripts in `scratch/phase22_diagnosis/`.

### 5.1 The exact scorability rule behind n=353 of 477 (measure 2a)

A case is **scorable for measure (i)** if and only if its generated IMPRESSION
yields at least one 5-gram after tokenisation — i.e. at least 5 alphanumeric
tokens. The rule is not a quality filter or a content judgement; it is the
arithmetic precondition for the ratio's denominator to be non-zero.

From `scratch/phase22_diagnosis/measure_transplant.py`:

```python
def toks(s):
    out = []
    for w in s.lower().split():
        w = "".join(ch for ch in w if ch.isalnum())
        if w:
            out.append(w)
    return out

def ngrams(t, n=5):
    return {tuple(t[i:i+n]) for i in range(len(t)-n+1)}
```

`ngrams()` returns the empty set whenever `len(t) < 5`, because the range
`range(len(t)-n+1)` is empty. The exclusion is then applied as:

```python
g  = toks(gen)
g5 = ngrams(g)
...
if g5:
    ov = len(g5 & ngrams(b))/len(g5)     # ratio computed only when g5 is non-empty
...
rec = {..., "max_5gram_overlap_ratio": (None if not g5 else round(best_ratio,4)), ...}
if not g5:
    skipped_short.append(uid)
```

**477 completed − 124 with fewer than 5 tokens = 353 scorable.** The 124 excluded
uids are listed in full in `out_2a_transplant.txt`. Measure (ii), longest common
token substring, has no such precondition and is reported on all 477.

Two consequences worth stating plainly:

- The exclusion is **not** neutral with respect to the finding. Very short
  impressions are overwhelmingly stock strings (`"Impression: Normal"`), which
  are the *least* likely to be harmful transplants. Excluding them raises the
  ratio-1.0 rate relative to the full 477. Both denominators are therefore given
  everywhere: 83/353 (23.5%) scorable, or 83/477 (17.4%) of all completed cases.
- An alternative rule — score short impressions at n-gram order `min(5, len)` —
  was **not** adopted, because it would compare different-order n-grams across
  cases and make the distribution in §2a non-homogeneous.

### 5.2 Harmful vs benign transplant: splitting the 83 ratio-1.0 cases

A copied impression is **harmful** if the copied text itself carries at least one
CheXbert-positive finding on the 13 real conditions — a specific clinical claim
belonging to another patient. It is **benign** if it carries none — stock normal
phrasing that happens to match because the corpus is templated. `"No Finding"` is
excluded from the positive set: a `No Finding`-positive impression *is* the stock
normal phrase that defines the benign bucket.

Labels are read from the raw 4-class CheXbert output already produced in §2c
(`raw_classes_phase21_armC.csv`); no model was re-run.

Command: `.venv/Scripts/python.exe scratch/phase22_diagnosis/split_transplant_harm.py`

```
cases with max 5-gram overlap ratio == 1.0: 83
(denominator: 353 scorable of 477 total)

--- STRICT (Positive only) ---
  (a) benign  -- no positive label on the 13 real conditions: 61/83 (73.5%)
  (b) HARMFUL -- >=1 positive label                         : 22/83 (26.5%)
  harmful transplant rate vs all scorable cases: 22/353 (6.2%)
  harmful transplant rate vs all completed cases: 22/477 (4.6%)

--- INCLUSIVE (Positive or Uncertain) ---
  (a) benign  : 56/83 (67.5%)
  (b) HARMFUL : 27/83 (32.5%)
  harmful transplant rate vs all scorable cases: 27/353 (7.6%)
  harmful transplant rate vs all completed cases: 27/477 (5.7%)
```

**The harmful transplant rate is 22/353 = 6.2%** (95% CI [3.9%, 9.3%], exact
Clopper–Pearson), or 22/477 = 4.6% [2.9%, 6.9%] against all completed cases.
Under the inclusive definition (Uncertain counted as positive, matching
`to_present_binary()`) it is 27/353 = 7.6%. Both definitions are reported; neither
is merged into the other.

The 22 strict-harmful cases:

| uid | positive labels | src nb | copied impression (truncated) |
|---|---|---|---|
| 309 | Cardiomegaly | 1970 | Borderline cardiomegaly without heart failure. |
| 1706 | Cardiomegaly | 1970 | Borderline cardiomegaly without heart failure. |
| 2212 | Atelectasis | 7 | Basilar atelectasis. No confluent lobar consolidation or pleural effusion. |
| 2322 | Cardiomegaly | 3123 | Mild stable cardiomegaly without acute disease. Possible [REDACTED] right pleural effusion. |
| 2722 | Cardiomegaly | 1152 | Cardiomegaly without acute cardiopulmonary abnormality. |
| 2836 | Atelectasis | 53 | Low lung volumes with right basilar atelectasis. Otherwise, no acute cardiopulmonary disease. |
| 2859 | Atelectasis | 667 | Low lung volumes with subsequent bronchovascular crowding and bibasilar atelectasis. |
| 2865 | Cardiomegaly | 1624 | Mild cardiomegaly, no acute pulmonary findings |
| 2891 | Lung Opacity | 590 | Right middle lobe airspace disease may reflect atelectasis or pneumonia. |
| 2946 | Lung Opacity | 2293 | Mild [REDACTED] [REDACTED] opacities compatible with residual atelectasis/scarring. |
| 3165 | Cardiomegaly, Lung Opacity, Edema | 925 | Cardiomegaly with pulmonary edema superimposed on chronic interstitial lung changes. |
| 3182 | Cardiomegaly | 772 | Stable cardiomegaly, tortuous thoracic aorta and atherosclerotic calcification. |
| 3241 | Cardiomegaly, Edema | 3880 | Stable cardiomegaly with mild pulmonary interstitial edema. |
| 3442 | Lung Opacity | 494 | Atelectasis versus scar left lung base. Otherwise unremarkable. |
| 3546 | Atelectasis | 3653 | Low lung volumes with minimal bibasilar atelectasis. Overall no significant interval change. |
| 3609 | Cardiomegaly | 454 | Mild cardiomegaly. No acute cardiopulmonary findings. |
| 3740 | Lung Opacity | 1064 | Stable elevated right hemidiaphragm with questionable subtle increased right basilar airspace disease… |
| 3773 | Lung Lesion | 517 | Calcified right basilar nodule compatible with granuloma / histoplasmoma. A few calcified right hilar… |
| 3790 | Lung Opacity, Pleural Effusion | 267 | Small bilateral pleural effusions with a few scattered areas of patchy bilateral airspace disease. |
| 3846 | Atelectasis | 667 | Low lung volumes with subsequent bronchovascular crowding and bibasilar atelectasis. |
| 3866 | Pleural Other | 3676 | Redemonstration of diffuse bilateral pulmonary fibrosis with relative sparing of the bilateral lung… |
| 3949 | Cardiomegaly | 45 | Stable cardiomegaly without overt pulmonary edema. |

Per-label frequency among the 22 (not pooled): Cardiomegaly 10, Lung Opacity 6,
Atelectasis 5, Edema 2, Lung Lesion 1, Pleural Effusion 1, Pleural Other 1.

**Two neighbours were transplanted into two different patients each.** uids 309
and 1706 both received the byte-identical string *"Borderline cardiomegaly without
heart failure."* from neighbour 1970; uids 2859 and 3846 both received
*"Low lung volumes with subsequent bronchovascular crowding and bibasilar
atelectasis."* from neighbour 667. A single corpus report is therefore capable of
propagating its specific findings into multiple unrelated patients' reports.

Note also that 7 of the 22 carry temporal language *inside the copied span*
(`Stable…` ×4, `Redemonstration of…`, `no significant interval change`). RC2 and
RC3 compound, as §2a anticipated.

### 5.3 Temporal-term false-positive audit (n=20, seed stated)

20 of the 167 flagged Arm C cases were drawn with `random.Random(20260921)` —
seed fixed and recorded in the script before drawing — and every matched term was
printed with ±90 characters of context for adjudication by reading.

Command: `.venv/Scripts/python.exe scratch/phase22_diagnosis/sample_temporal_fp.py`
Full output: `out_A3_temporal_sample.txt`.

Sampled uids: 287, 951, 1491, 1563, 1648, 1776, 1799, 1812, 2364, 2474, 2506,
2614, 2746, 2892, 2956, 2974, 3086, 3156, 3660, 3694.

| uid | matched context (abbreviated) | verdict |
|---|---|---|
| 287 | "The mediastinal contours are **stable**." | true |
| 951 | "The heart and lungs have […] **in the interval**." | true |
| 1491 | "A **stable** electronic device is present on the left anterior chest wall." | true (weakest) |
| 1563 | "**Redemonstrated** syndesmophyte." / "**Stable** chest." | true |
| 1648 | "**Stable** right lower lobe calcified granulomas. Thin lingular scar, **unchanged**." | true |
| 1776 | "There is **stable** eventration of the anterior right hemidiaphragm." | true |
| 1799 | "**Stable** cardiomegaly." (findings and impression) | true |
| 1812 | "The mediastinum is **stable**." | true |
| 2364 | "**Interval** development of bandlike opacities in the left lung base." | true |
| 2474 | "Heart and mediastinum are **stable** with normal size heart." | true |
| 2506 | "Mild cardiomegaly, **stable**." | true |
| 2614 | "A **stable** right upper lobe calcified granuloma" / "appears **unchanged**." | true |
| 2746 | "**Comparison to similar cases** suggests a **stable** chest…" | **false positive** |
| 2892 | "**Stable** right lower lobe calcified granulomas… **unchanged**… **in the interval**." | true |
| 2956 | "The heart and lungs have […] **in the interval**." | true |
| 2974 | "Calcified granulomas… are **stable compared with prior study**." | true |
| 3086 | "No active cardiopulmonary disease. **Unchanged**." | true |
| 3156 | "The mediastinal contours are **stable**." | true |
| 3660 | "The mediastinum is **stable**." | true |
| 3694 | "**stable** mediastinal and hilar contours" / "dextrocurvature of the spine **again** noted." | true |

**Precision = 19/20 = 95.0%** (95% CI [75.1%, 99.9%], exact Clopper–Pearson).

Applying the point estimate to §2b's Arm C count gives roughly 159 of 167 as
genuine — but the CI is wide at n=20, so the honest statement is: **the lexical
count is a good but not perfect proxy, and the §2b figure of 167/477 (35.0%) is a
slight over-count of unknown but small magnitude.** No corrected headline figure
is substituted for the measured one.

Adjudication basis: a match is a **true** comparison term when it asserts that a
finding's state is known relative to an earlier examination — which no case in
this harness has. uid 2974 is the most flagrant (*"compared with prior study"*),
and uid 1330 from §2b (*"unchanged from a previous examination 7 years ago"*)
fabricates a dated prior outright.

**The single false positive is itself a distinct defect, not a clean miss.** uid
2746's impression reads *"Comparison to similar cases suggests a stable chest…"*.
It is not claiming a prior study, so it fails the temporal definition — but it
**narrates the retrieval mechanism to the clinician as if neighbour cases were
clinical comparanda for this patient**. That is the attribution failure of RC2
surfacing in the report's own prose. It is recorded here as a separate observation;
it is not counted in any figure in this document.

### 5.4 Output field order — correction to a premise, and a refinement of RC1

**The brief asks for the "JSON output field order". The current system does not
emit JSON.** Phase 20 replaced the JSON schema with a delimiter-marker format
after tracing all 17 content-validation failures to one cause (quoting inside the
disclaimer's JSON string). `_schema_instruction()`
([prompt_builder.py:348-368](../../backend/app/services/prompt_builder.py#L348-L368))
now instructs: *"Do NOT use JSON, a JSON wrapper, or markdown code fences."*

The order is defined once, at
[prompt_builder.py:77-85](../../backend/app/services/prompt_builder.py#L77-L85):

```python
REPORT_CONTENT_FIELDS = (
    "examination",
    "clinical_history",
    "technique",
    "findings",
    "impression",
    "recommendation",
    "disclaimer",
)
```

and rendered into the prompt at
[prompt_builder.py:357](../../backend/app/services/prompt_builder.py#L357):

```python
marker_lines = "\n".join(f"###{name.upper()}###\n<{name} text>" for name in REPORT_CONTENT_FIELDS)
```

with the instruction *"Output exactly these 7 fields, **in this exact order**"*.

**Yes — `findings` precedes `impression`** (position 4 of 7 vs position 5), and
`recommendation` follows both.

**This refines RC1 and corrects an over-strong reading in §1a.** §1a said FINDINGS
and IMPRESSION are "siblings drawn from the same evidence block, not a derivation
of one from the other." That is accurate about *instruction*, but incomplete about
*mechanism*: because generation is autoregressive and the ordering is enforced,
the model's own FINDINGS tokens **are already in context** when it emits
IMPRESSION. The failure is therefore **not** that the information is unavailable —
it is that **nothing requires the model to use it**, and the one instruction that
is present ("base your report ONLY on the evidence provided below") points at the
neighbour block instead. Section regeneration remains the genuine
information-absence case: there, FINDINGS is truly not in context at all (§1a).

The practical consequence for the fix is material: a prompt-level constraint on
the single-call path is operating on information the model already has, which
makes it a more plausible remedy than a two-stage split would be if the text were
genuinely absent. This does not establish that a prompt-only fix suffices — only
that it is not defeated by the architecture.

### 5.5 Arm C and Phase 20 side by side — not a trend

Presented adjacently for reference only. **No difference is computed, and none of
these pairs may be read as before/after, improvement, or regression.** Per
`phase21_ablation_architecture.md` §5.3 the two runs differ in sample size, code,
and an unmeasured per-report defect, and no experiment was run that would make
them comparable. The Phase 20 column is a separate system's separate result.

| measure | Phase 21 Arm C | Phase 20 |
|---|---|---|
| n (completed) | 477 | 460 |
| temporal union, 5 terms | 167/477 = 35.0% [30.7, 39.5] | 97/460 = 21.1% [17.4, 25.1] |
| strict contradiction (≥1 of 13 labels) | 22/477 = 4.6% [2.9, 6.9] | 9/460 = 2.0% [0.9, 3.7] |
| wider asymmetry (not a contradiction rate) | 300/477 = 62.9% | 243/460 = 52.8% |
| ratio-1.0 transplant | 83/353 = 23.5% [19.2, 28.3] | **not computable** (no persisted neighbour uids) |
| harmful transplant (strict) | 22/353 = 6.2% [3.9, 9.3] | **not computable** |

CIs are exact Clopper–Pearson, from `out_A_cis.txt`. The two transplant rows have
no Phase 20 value at all, so the columns are not even measuring the same set of
quantities — a further reason the table is a reference layout and not a contrast.

---

## 6. Reproduction

```bash
# 2a (main .venv)
.venv/Scripts/python.exe scratch/phase22_diagnosis/measure_transplant.py
# 2b (main .venv)
.venv/Scripts/python.exe scratch/phase22_diagnosis/measure_temporal.py
# 2c (isolated eval venv, CPU)
ml/evaluation/.venv-bertscore/Scripts/python.exe scratch/phase22_diagnosis/measure_contradiction.py

# Step 1 follow-ups (main .venv)
.venv/Scripts/python.exe scratch/phase22_diagnosis/split_transplant_harm.py   # 5.2
.venv/Scripts/python.exe scratch/phase22_diagnosis/sample_temporal_fp.py      # 5.3
.venv/Scripts/python.exe scratch/phase22_diagnosis/cis.py                     # CIs
```

Artifacts: `scratch/phase22_diagnosis/{out_2a_transplant.txt, out_2b_temporal.txt,
transplant_armC_n477.csv, raw_classes_phase21_armC.csv, raw_classes_phase20.csv,
temporal_armC_uids.txt, temporal_phase20_uids.txt}`.

**Known gap, stated not worked around:** measure 2a is unavailable for Phase 20
(no persisted neighbour UIDs — §2a). Everything else is reported for both runs,
separately.

**Step 0 ends here.** No fix is chosen and no fix code is written, per the brief.
