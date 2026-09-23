# REPORT_PLAN.md

**Plan for writing the final capstone report — RadAssist (AI-Assisted Radiology Reporting Workspace)**

Place this file at `thesis final report/report/REPORT_PLAN.md`. It is the single
authoritative instruction for writing the report. If any other input conflicts with this
plan, follow the plan and record the conflict in `GAPS.md`.

---

## 0. Scope of the task

Write the complete final capstone report, chapter by chapter, into
`thesis final report/report/`.

- **No source-code changes.** Work on branch `final-prep`. `git status` for `backend/`,
  `ml/` and `frontend/src/` must stay empty throughout.
- **Output:** `chapter_1.docx` … `chapter_8.docx`, then a combined `final_report.docx`,
  then `GAPS.md`.
- **Format:** use the docx skill. Match the P2 document's fonts, heading styles,
  margins, caption style and numbering.
- **Commits:** commit each chapter as soon as it is finished
  (`docs(report): chapter N`), so nothing is lost if the run is interrupted. Do not
  pause for review between chapters.

### Inputs

| Input | Use |
|---|---|
| P2 report | Base text for Chapters 1, 2 and parts of 4 |
| P1 LaTeX project (`core/`, `chapters/`, `bibliography/references.bib`, 19 entries) | Front matter and reference list |
| Department chapter template | Section content (see §5.0 for numbering) |
| Faculty pointers | Chapter numbering and extra chapters (6, 7, 8) |
| `thesis final report/01_facts` … `08_admin` | All facts, numbers, diagrams, screenshots |
| `development_log.md` | Narrative and decision history |

---

## 1. Hard rules

1. **Every number, version, date and claim traces to the packet, the dev log, or the
   repo.** Where a fact is not recorded, write `[TO CONFIRM: ...]` inline. Never
   estimate, round up, or reconstruct a number from memory.
2. **Describe the system as built, not as planned.** Where P1/P2 described something
   different (DenseNet121 classification → BiomedCLIP retrieval; MongoDB → SQLite;
   features promised but not built), explain the change and why it was made. Correct
   P2's factual errors (image counts, validation accuracy) and record each correction.
3. **Negative and inconclusive results go in the main text, never buried.** Phase 21's
   primary endpoint did not clear; Phase 23 found no improvement; BERTScore could not
   distinguish real reports from random pairings; the omission defect remains in 27/477
   reports.
4. **Never claim clinical validation or diagnosis.** The system is decision support. No
   radiologist has validated its output.
5. **Pending work is written as pending:** blinded read, clinician feedback, Gate B
   threshold, Gate C retry, Bengali evaluation.
6. **Comparisons with published work** require a citation and the caveat that dataset,
   labeler and averaging differ, so the comparison is indicative only.
7. **References:** reuse `bibliography/references.bib`; add entries for BiomedCLIP,
   Llama 3, CheXbert, IU X-ray, RAG and any newly cited work in the same style. Mark any
   reference that cannot be verified as `[TO CONFIRM]`.

---

## 2. Editing rule — change only what must change

Where P1/P2 text is still accurate, **reuse it as written**. Do not rewrite for style.

**Chapter 3 is the exception: it is a full rewrite**, because the template's and the
pointers' sections (requirement analysis, target users, feasibility, societal,
environmental, ethical, project management, risk, economic) were not covered in P1/P2 and
the requirements have changed since.

For every other chapter, record in `GAPS.md` which paragraphs were **kept**, which were
**edited**, and which were **replaced**, each with the reason.

---

## 3. Diagram requirement

The report must explain the system **visually**, not only in prose. Each diagram is
placed in the chapter that discusses it, numbered, captioned, with a source note, and
referenced by number in the text.

**Required** (sources and PNGs are in `03_diagrams/`):

1. System architecture
2. **ML pipeline**
3. **RAG pipeline**
4. **Use case**
5. **Activity — report generation**
6. Sequence — one generation
7. ER diagram
8. Deployment
9. Page flow (Generate → Report → Evidence)

Add any further diagram or table wherever it explains something better than prose.
**The backend section (5.3) is the heaviest engineering work in this project and must be
the most thoroughly illustrated and explained section of the report.**

Never include a figure the text does not discuss.

---

## 4. Voice

Write as an engineering team arguing a case to an examiner, not as documentation.

- Each chapter opens with what it will establish and closes with what it established.
- Explain **why** a decision was made before **how** it was implemented.
- Plain declarative sentences; academic register consistent with P2; past tense for work
  done.
- No filler, no marketing language, no boilerplate repeated between chapters.

---

## 5. Chapter plan

### 5.0 Numbering — how the template and the faculty pointers were reconciled

The department template stops at Chapter 5; the faculty pointers run to Chapter 8 and
renumber the chapters. Where they conflict, **the faculty pointers decide the chapter
numbering**, and **every template section is preserved** inside the pointers' structure.
No section from either document is dropped.

Record this in `GAPS.md` with a mapping table showing where each template section ended
up.

| Template | Faculty pointers | Final location in this report |
|---|---|---|
| Ch1 Introduction | — | Chapter 1 |
| Ch2 Literature Review | — | Chapter 2 |
| Ch3 3.1 Final Specifications | Ch3 3.1–3.4 System Analysis | Chapter 3 (renumbered, §5.3 below) |
| Ch3 3.2–3.8 | — | Chapter 3, §§3.6–3.11 |
| Ch4 Design | — | Chapter 4 |
| — | Ch5 Implementation | Chapter 5 |
| Ch5 5.1–5.6 Performance Evaluation etc. | Ch6 Result and Discussion | Chapter 6 |
| — | Ch7 User Manual | Chapter 7 |
| — | Ch8 Conclusion and Future Work | Chapter 8 |

---

### Chapter 1 — Introduction (6–8 pages)

- **1.1 Background** — radiology reporting workload; the radiologist shortage in
  Bangladesh and the urban/rural gap; why chest X-ray specifically; what AI report
  generation is.
- **1.2 Rationale of the Study / Motivation** — the access problem; SDG 3 and SDG 10; why
  decision support rather than automation; why low-cost local deployment matters for
  Thana-level facilities.
- **1.3 Problem Statement** — LLM hallucination in clinical text; the grounding problem;
  the infrastructure gap (GPU clusters unavailable); no Bengali reporting support. State
  the specific gap this project addresses.
- **1.4 Objectives** — the final objective list as delivered, each phrased so it can be
  tested. Mark which were met, partially met, or re-scoped, with a forward reference to
  Chapter 6.
- **1.5 Methodology in Brief** — one page: retrieval-based (not classification) pipeline;
  BiomedCLIP + ChromaDB + Llama 3; human-in-the-loop; the pre-registered, gated
  evaluation discipline (freeze-then-build, criteria fixed before each run).
- **1.6 Scopes and Challenges** — in scope (frontal chest X-ray, English and Bengali
  drafts, single-site local deployment); out of scope (CT/MRI, DICOM/PACS, autonomous
  diagnosis); challenges actually encountered (hallucination, grounding-attribution
  failure, metric validity, non-determinism at temperature 0, limited annotated data).

### Chapter 2 — Literature Review (8–10 pages)

- **2.1 Preliminaries** — CNNs and vision transformers in medical imaging; LLMs and the
  black-box problem; RAG; vector embeddings, cosine similarity and semantic search;
  multimodal image–text models (CLIP, BiomedCLIP); clinical labelers (CheXpert,
  CheXbert) and what CE metrics measure.
- **2.2 Review of Existing Research** — report-generation models (R2Gen and successors)
  with their reported CE scores; RAG in biomedicine; retrieval noise and grounded
  hallucination; domain-specific vs larger models; explainable AI and clinical trust;
  commercial systems (PowerScribe, Rad AI, Smart Reporting, DeepTek) and what each
  contributed to this workflow design.
- **2.3 Summary of Key Findings** — what the literature establishes; where metrics are
  known to be weak; what is measured on MIMIC-CXR but not on IU X-ray, and why that
  matters here.
- **2.4 Research Gap** — lightweight, locally deployable, evidence-grounded, bilingual
  reporting with explicit human oversight, plus the evaluation discipline to show it
  works. Connect each gap to the chapter that addresses it.

### Chapter 3 — System Analysis (12–15 pages) — FULL REWRITE

Numbering merges both documents; the pointers' four sections come first, then the
template's sections in order.

- **3.1 Requirement Analysis** — functional and non-functional requirements as delivered,
  in tables, each traced to its implementation.
- **3.2 Target Users and Use Cases** — the real actors only (radiologist/doctor); the
  use-case diagram (Fig. use_case); primary use cases in a table. Do not invent an admin
  actor if no admin role exists.
- **3.3 Feasibility Study** — technical (single RTX 4070 Ti SUPER, measured VRAM and
  latency), operational (clinic workflow fit), legal/ethical (public de-identified data,
  CheXbert licence), and schedule feasibility.
- **3.4 Key Challenges Addressed** — PHI in images; hallucination; evidence attribution;
  non-determinism; bilingual output; metric validity. Each with how it was addressed.
- **3.5 Final Specifications and Requirements** — the final agreed specification;
  stakeholder feedback and its source (or `[TO CONFIRM]` if none is recorded); applicable
  standards, professional codes and regulatory requirements reviewed, and the gap where
  formal medical-device clearance would be required before clinical use.
- **3.6 Societal Impact** — access in rural Bangladesh; automation bias and how the design
  mitigates it (evidence visible, warnings never hidden, the doctor finalizes); language
  accessibility; health, safety, legal and cultural considerations; risks if misused.
- **3.7 Environmental Impact** — local inference vs cloud; measured energy per report if
  available, otherwise `[TO CONFIRM]`; hardware lifetime; the sustainability of a
  no-training design that reuses a frozen encoder.
- **3.8 Ethical Issues** — patient privacy and PHI masking; dataset licensing and the
  CheXbert non-redistribution term; professional responsibility for errors; the
  disclaimer; bias from a US-sourced dataset applied in Bangladesh; the decision not to
  ship unvalidated image explainability rather than risk misleading heatmaps.
- **3.9 Project Management Plan** — phases with real dates from `timeline.md`; roles per
  member; schedule, budget and resources; tooling and version control; the gated working
  method (freeze, build, measure) and why it was adopted; the revised plan and
  rescheduling actually applied.
- **3.10 Risk Management** — a risk register built from risks that actually materialised:
  grounding-attribution failure, threshold miscalibration, metric invalidity, a
  dependency CVE, storage incidents, non-determinism. Each with impact, likelihood,
  mitigation taken, and residual risk.
- **3.11 Economic Analysis** — development cost (hardware, electricity, zero licence cost
  for open models); marginal cost per report; a cloud-hosting alternative estimate; a
  cost–benefit estimation against current reporting costs, stated as an estimate with its
  sources. Mark anything unrecorded `[TO CONFIRM]`.

### Chapter 4 — Design and Methodology (12–15 pages)

- **4.1 Design Process / Methodology Overview** — the SDLC actually followed; the
  freeze-then-build discipline; how pre-registration shaped the design.
- **4.2 Design (Model) Specification**
  - System architecture (Fig. system_architecture), component by component.
  - **The ML pipeline** (Fig. ml_pipeline): preprocessing, PHI masking, BiomedCLIP
    encoding, embedding dimensions, the vector store, k-NN retrieval, label voting.
    State explicitly that the system does **not** classify, and why retrieval gives
    traceability.
  - **The RAG pipeline** (Fig. rag_pipeline): what is retrieved, how evidence is
    aggregated, what reaches the prompt, what is checked afterwards.
  - Workflow and decision points (Fig. activity_report_generation): admission checks,
    the projection gate, the retrieval-support threshold, validation, consistency states,
    doctor edit, finalize.
  - Sequence of one generation (Fig. sequence_generate_report).
  - Data model (Fig. er_diagram) and why SQLite plus ChromaDB rather than one store.
  - UI design: the page-based flow (Fig. page_flow) and its principles — evidence
    visible, warnings never hidden, the human decides.
- **4.3 Alternative Design Solutions Considered and Rejected** — classification
  (DenseNet121) vs retrieval, decided by the Phase 0 encoder bake-off; evidence modes,
  tested in Phase 21; model and prompt variants, tested in Phase 23; server-side PDF vs
  browser print; image explainability deferred. Each with the reason and the evidence.
  This is the template's "preliminary design of multiple alternative solutions" and their
  functional verification.
- **4.4 Dataset and Preprocessing** — IU X-ray provenance and licence; counts after every
  filtering step; the 18-class curated taxonomy; the near-duplicate audit and
  cluster-atomic, leakage-safe splitting; train/val/test sizes; what the knowledge base
  contains.

### Chapter 5 — Implementation (15–20 pages; the largest chapter)

Order follows the faculty pointers exactly.

- **5.1 Development Environment** — hardware, OS, Python/Node versions, key packages with
  versions, Ollama and model digests, GPU and CUDA, the frozen evaluation venv and why it
  exists, repository layout.
- **5.2 Frontend Development** — stack and rationale; the page-based flow; state
  management and the single-fetch layout; the report editor and section regeneration; the
  evidence panel; bilingual UI; accessibility and contrast work; design tokens.
- **5.3 Backend Development** — from `02_backend/backend_architecture.md`. The most
  detailed and most heavily illustrated section of the report:
  - Clean architecture as realised here: domain, services, infrastructure, API; the
    Protocol interfaces; dependency injection.
  - Every service, its single responsibility, inputs and outputs, and its file.
  - The full request lifecycle for upload and for generate-report, in order.
  - Every threshold and config value: current value, where defined, and how it was chosen
    — pre-registered, calibrated, or post-hoc revised. The projection threshold revision
    must be marked **post-hoc**.
  - Validation layers: structural validation; semantic validation (advisory by design,
    with the reason); the consistency service and its four states.
  - Error handling and retries; what is not recorded (D5); behaviour when the labeler,
    Ollama or ChromaDB is unavailable.
  - Caching and session reuse; what is recomputed and what is not (language switching).
  - Security: authentication, password hashing, ownership rules, upload validation; what
    is enforced and what is not.
  - API endpoint table: method, path, purpose, request and response shape.
- **5.4 Testing Strategy** — unit/integration split; backend and frontend test counts; the
  label-equivalence gate; negative controls; the design and i18n checks; what is not
  covered by tests.

### Chapter 6 — Result and Discussion (15–18 pages)

Merges the template's Chapter 5 sections with the pointers' Chapter 6.

- **6.1 Evaluation Methodology and Performance Evaluation** *(template 5.1)* —
  pre-registration; paired bootstrap; why confidence intervals rather than bare point
  estimates; the frozen labeler as a single instrument; the leakage-safe test pool; what
  each phase asked.
- **6.2 Retrieval Results (Phase 0)** — the encoder bake-off table; the three gates and
  their verdicts, including the inconclusive Recall@5; per-class results; the manual
  relevance validation (proxy precision 89%, recall 49%) and its interpretation.
- **6.3 Report Generation Results (Phase 20)** — the three tiers; the CE result against
  the random baseline; BERTScore's invalidity as a metric-validity finding; the Fracture
  attribution failure and what it revealed.
- **6.4 Ablation (Phase 21)** — the three arms; C−A clearing; the primary endpoint C−B not
  clearing at either sample size; the recall-driven decomposition and the length confound;
  the one gain that length cannot explain; the symmetric caution about what a null means.
- **6.5 Grounding Failure and Remediation (Phase 22)** — the discovered defect with the
  live example; the four root causes; measured v1.1 rates; the fix design; the
  pre-registered Gate A evaluation; the results table; the post-hoc precision/recall
  decomposition ruling out the "shorter text" explanation; the residual omission defect;
  the pre-registration inconsistency recorded honestly.
- **6.6 Accuracy Improvement Experiment (Phase 23)** — the three variants; the
  validation-set selection rule; the result that none beat the incumbent; the support
  limitation, and why the checklist hypothesis is not refuted.
- **6.7 Analysis of Design Solutions** *(template 5.2)* — which design choices the
  evidence supports, and which it does not; the optimisation actually performed on the
  selected design.
- **6.8 Final Design Adjustments** *(template 5.2 Final Design Adjustment)* — the v1.2
  remediation as the final adjustment made in response to evaluation results, and the
  Phase 23 decision to retain the incumbent design rather than change it.
- **6.9 Statistical Analysis** *(template 5.3)* — bootstrap configuration; why macro-F1's
  CI does not narrow with n and what follows; the micro vs macro trade-off, including the
  Phase 21 finding that micro-F1 is gameable on this dataset; non-determinism at
  temperature 0 and the noise-floor check.
- **6.10 Comparisons and Relationships** *(template 5.4)* — published CE scores with
  citations, and the explicit caveat that dataset, labeler and averaging differ. The fair
  statement is that this system reaches a comparable range **without any model training**.
  Also the relationships between retrieval quality, evidence mode and report quality
  across phases.
- **6.11 Discussion** *(template 5.6)* — what the evidence supports, what it does not, and
  what remains unknown.
- **6.12 Key Achievements and Limitations of the Current System** *(pointers 6.1)* —
  achievements with their evidence; limitations: low absolute clinical accuracy,
  English-only checking, Bengali unmeasured, no clinician validation, a single dataset,
  the omission defect, features not implemented.

### Chapter 7 — User Manual (10–12 pages)

- **7.1 Installation and Setup** — prerequisites, model pulls, environment variables,
  database migration, starting backend and frontend, verifying the stack is healthy.

Then one section per real screen, in the order a new user meets them, each with its
screenshot, a caption, what the user does, and what the system shows: registration and
login; queue/worklist; find patient; patients and patient profile with prior studies; new
examination and upload; generation in progress; the result page (impression,
recommendation, validation warnings, consistency state, full report); the evidence page
(evidence, agreement, alternatives); explainability; compare with previous; print / save
as PDF; language switching; settings; profile.

Use **only** the real screens in `05_screenshots/`. Do **not** use the faculty pointers'
example sections (home screen, contact page, guardian/child chat, review page); they
belong to a different project. Replace them with this project's real screens, and note
the substitution in `GAPS.md`.

### Chapter 8 — Conclusion and Future Work (4–6 pages)

- **8.1 Summary of the Work Done** — the system built, the evaluation performed, the
  defect found and remediated.
- **8.2 Key Contributions and Impact** — the retrieval-grounded bilingual reporting
  workspace; the pre-registered evaluation discipline and its negative results; the
  grounding-failure diagnosis and fix; privacy-preserving masking before embedding; a
  design that runs on a single consumer GPU.
- **8.3 Recommendations for Future Enhancements**, each with why it was not done now:
  Gate B threshold calibration and Gate C retry; warnings surfaced everywhere in the UI;
  Bengali evaluation; a clinician validation study; validated image explainability
  (attention rollout, requiring localization ground truth); larger and more diverse
  datasets; DICOM/PACS and HL7/FHIR; server-side PDF; multi-user roles; cloud or
  multi-site deployment.

---

## 6. Figures and tables

- Place every diagram from `03_diagrams/` and every chart from `04_figures/` in the
  chapter that discusses it.
- Number and caption each one, with a source note.
- Refer to each figure by number in the text.
- Every results table states **n** and the confidence interval where one exists.
- Never include a figure the text does not discuss.

---

## 7. Final deliverable

Assemble `final_report.docx`:

1. Front matter adapted from the P1 `core/` files — title page, declaration, approval,
   ethics statement, abstract, dedication, acknowledgement, table of contents, list of
   figures, list of tables, nomenclature — updated to the built system.
2. All eight chapters.
3. The reference list.

Rewrite the abstract to describe what was actually built and measured, including the
honest limitations.

---

## 8. GAPS.md

After the report is assembled, write `thesis final report/report/GAPS.md` listing:

1. Every `[TO CONFIRM]` marker with its location.
2. Every claim whose only source was the dev log rather than code or an artifact.
3. Every section that could not be completed, and why.
4. Every place P1/P2 text was **kept**, **edited** or **replaced**, with the reason
   (per §2).
5. The template-to-report mapping table (per §5.0), and any other conflict between
   inputs and how it was resolved.

**Do not fabricate anything to fill a gap.**

Final commit: `docs(report): complete final report`. Print the file tree and stop.
