"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  finalizeReport,
  getCurrentDoctor,
  getPatient,
  getReport,
  regenerateSection,
  retrievalSessionImageUrl,
  updateReport,
} from "@/lib/api-client";
import { StatusChip } from "@/components/ui/chip";
import { SimilarityBar } from "@/components/ui/similarity-bar";
import { AgreementBadge } from "@/components/ui/agreement-badge";
import {
  RetrievalSupportNotice,
  type RetrievalSupportCategory,
} from "@/components/ui/retrieval-support-notice";
import { OwnerChip } from "@/components/ui/owner-chip";
import { BackLink } from "@/components/layout/screen-header";
import { computeAgreement } from "@/lib/evidence-agreement";
import { toChipReportStatus } from "@/lib/report-status";
import { useDoctorName } from "@/lib/use-doctor-name";
import { BUTTON_BASE, SIZE, VARIANT } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { EditableReportSection } from "@/components/report/editable-report-section";
import type { ReportFieldKey } from "@/components/report/report-typography";
import { FinalizePreview } from "@/components/report/finalize-preview";
import { ReportDiffView } from "@/components/report/report-diff-view";
import { REPORT_CONTENT_FIELDS as CONTENT_FIELDS } from "@/components/report/report-document-view";
import { REPORT_FIELD_LABEL_KEY } from "@/components/report/report-document-view";
import { FullReportDisclosure } from "@/components/report/full-report-disclosure";
import { EvidenceSidebar, type EvidenceTab } from "@/components/report/evidence-sidebar";
import { ConsistencyState } from "@/components/report/consistency-state";
import { usePersistedToggle } from "@/lib/use-persisted-toggle";
import { shouldForceFullReport, fullReportForcedReasonKey } from "@/lib/full-report-rules";
import { computeReportDiff, editableRecordFrom } from "@/lib/report-diff";
import type { paths } from "@/lib/generated/api";

type ReportDetailResponse =
  paths["/reports/{report_id}"]["get"]["responses"][200]["content"]["application/json"];
type PatientResponse =
  paths["/patients/{patient_id}"]["get"]["responses"][200]["content"]["application/json"];
export type ReportContentKey = keyof ReportDetailResponse["content"];

// Phase 17 Step 7 / Phase 18 Decision 9: the single canonical list of the
// 5 user-editable report sections -- examination/disclaimer stay AI-set/
// read-only (exam-type metadata vs. free clinical narrative; fixed
// compliance statement) and are deliberately excluded. Exported so Phase
// 18's diff/section-counter/percentage logic imports this exact list
// rather than redeclaring it -- found duplicated (this Set plus a second,
// independent hardcoded object literal in handleRestoreAiDraft() below)
// within this same file before this consolidation, not actually
// centralized despite there being only one file involved.
export const EDITABLE_REPORT_FIELDS = [
  "clinical_history",
  "technique",
  "findings",
  "impression",
  "recommendation",
] as const satisfies readonly ReportContentKey[];

export type EditableReportField = (typeof EDITABLE_REPORT_FIELDS)[number];

const EDITABLE_KEYS = new Set<ReportContentKey>(EDITABLE_REPORT_FIELDS);

/**
 * The summary-first split of the canonical 7-field document.
 *
 * SUMMARY_FIELDS are what a radiologist opening this screen must see without
 * doing anything: the conclusion and what to do about it. They are rendered
 * outside the disclosure and there is no state in which they are hidden.
 *
 * FULL_REPORT_FIELDS are the rest -- what the examination was, what the
 * patient brought to it, how it was acquired, what was seen, and the fixed
 * legal boilerplate. Context, consulted on purpose rather than read every
 * time.
 *
 * Derived from CONTENT_FIELDS by partition rather than restated, so the
 * canonical list stays the single source of the 7 fields and their order: a
 * field added there lands in the full report automatically instead of
 * silently appearing in neither half. The summary keys are the declaration;
 * everything else follows.
 */
const SUMMARY_KEYS = ["impression", "recommendation"] as const satisfies readonly ReportContentKey[];
const SUMMARY_KEY_SET = new Set<ReportContentKey>(SUMMARY_KEYS);

const SUMMARY_FIELDS = CONTENT_FIELDS.filter((f) => SUMMARY_KEY_SET.has(f.key)).sort(
  // Impression before recommendation: the finding, then what follows from it.
  (a, b) => SUMMARY_KEYS.indexOf(a.key as (typeof SUMMARY_KEYS)[number]) -
    SUMMARY_KEYS.indexOf(b.key as (typeof SUMMARY_KEYS)[number]),
);
const FULL_REPORT_FIELDS = CONTENT_FIELDS.filter((f) => !SUMMARY_KEY_SET.has(f.key));

/** localStorage names (namespaced and scoped to the doctor by the hook). */
const FULL_REPORT_PREF = "workspace.fullReport";
const EVIDENCE_PREF = "workspace.evidenceCollapsed";

/**
 * Radiologist Workspace (Phase 12 Step 5, restyled Phase 14 per
 * design_specification.md §8.12 -- frontend/CLAUDE.md cites this as §8.10,
 * a citation slip; §8.10 is actually "Retrieval", a different screen).
 * Explainability and Comparison are actions launched FROM here, not
 * separate, disconnected features. Retrieved evidence is a rail here, not
 * a separate page.
 *
 * Three registers, per §6.1/§8.12: the image sits in `--lightbox` (the
 * only dark surface in the product), the report is paper/sans document
 * typography, the evidence rail is paper but quieter/mono-heavy.
 *
 * NOT built, flagged explicitly rather than faked:
 * - Citation markers linking specific report sentences to specific
 *   retrieved cases (§8.12's "signature interaction"). The backend
 *   returns report content as plain prose with no sentence-level
 *   grounding markup at all -- building this would mean inventing a
 *   citation-extraction feature with no backend support, not styling an
 *   existing one. The report is rendered in the correct document
 *   register; the hover-linking interaction is not implemented.
 * - Window/level, zoom, pan, invert, prior-study thumbnails (§8.12's
 *   Lightbox toolbar) -- real PACS-viewer engineering, not a styling
 *   pass; not attempted here.
 * - "Alternatives in retrieved evidence"'s (§10.3) "not present" column
 *   requires the full label taxonomy, which no endpoint here exposes to
 *   the frontend -- only the "present in the retrieved set" side is
 *   real and shown; the "not present" side is omitted rather than
 *   invented from a hardcoded label list.
 * - Evidence Agreement's Strong/Mixed/Weak classification (§10.2) is
 *   computed client-side from retrieved_cases (see lib/evidence-agreement.ts)
 *   since ReportDetailResponse carries no voted_labels field -- a
 *   documented re-derivation, not a second backend source of truth.
 * - Per-section Regenerate (§8.12) and the word-level "Changes vs AI
 *   draft" diff (§10.5) -- explicitly deferred to Phase 18, per the
 *   frozen Phase 17 scope.
 *
 * Phase 15: OwnershipChip (via OwnerChip) in the context bar, and a
 * read-only banner (§8.15, adapted copy -- no "signed" language, since
 * finalize didn't exist yet at that phase, and no "your access has been
 * recorded" clause, since no access-log table exists, per
 * frontend/CLAUDE.md's explicit instruction).
 *
 * Phase 17 Step 7: real edit/finalize. Each of the 5 editable sections
 * (EditableReportSection) commits independently via PATCH /reports/{id}
 * as soon as the doctor presses Enter or blurs the field -- there is no
 * page-level "Save" button, matching the per-section-commit design.
 * `content` (rendered here) sources final_content -- what the report
 * currently says, doctor edits included; `ai_draft_content` (fetched but
 * not directly rendered outside Restore) is the immutable original.
 * "Edited" is a per-field, client-computed signal
 * (content[key] !== ai_draft_content[key]), not a stored flag -- no
 * backend field-level tracking exists, so this is the honest thing to
 * derive. Editing/finalizing is gated on isOwner AND status !== "final";
 * a non-owner or a finalized report renders every section exactly like
 * before (EditableReportSection degrades to plain read-only text when
 * canEdit is false). Finalize opens FinalizePreview (Preview screen)
 * rather than a bare confirm, reusing ReportDocumentView for the actual
 * document -- see that component's own docstring for why extracting it
 * was necessary (nothing reusable existed before this step). The
 * unsaved-changes guard is frontend-only: beforeunload covers tab
 * close/refresh/external navigation; the in-app Explain/Compare/patient
 * links are individually guarded with a confirm() since Next.js App
 * Router has no built-in route-change-intercept event to hook globally.
 */
export default function ReportWorkspacePage() {
  const { t } = useT();
  const params = useParams<{ reportId: string }>();
  const reportId = params.reportId;

  const [report, setReport] = useState<ReportDetailResponse | null>(null);
  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [railTab, setRailTab] = useState<EvidenceTab>("evidence");
  const [currentDoctorId, setCurrentDoctorId] = useState<string | null>(null);

  const [savingField, setSavingField] = useState<ReportContentKey | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [dirtyFields, setDirtyFields] = useState<Set<ReportContentKey>>(new Set());
  // Which sections currently have their editor open. Separate from
  // dirtyFields, which only fills once text actually changes -- the full
  // report has to be held open from the moment an editor opens, otherwise a
  // section could be mid-edit inside a collapsed disclosure.
  const [editingFields, setEditingFields] = useState<Set<ReportContentKey>>(new Set());
  const [printing, setPrinting] = useState(false);

  // Phase 19: only one section can be mid-regeneration/preview at a time --
  // regeneratingField tracks the pending LLM call, regenerationResult
  // holds the candidate once it returns (cleared on Accept or Discard).
  const [regeneratingField, setRegeneratingField] = useState<EditableReportField | null>(null);
  const [regenerationResult, setRegenerationResult] = useState<{
    field: EditableReportField;
    candidate: string;
    contextIncomplete: boolean;
  } | null>(null);
  const [regenerationError, setRegenerationError] = useState<string | null>(null);
  const [regenerationErrorField, setRegenerationErrorField] = useState<EditableReportField | null>(null);

  useEffect(() => {
    getReport(reportId)
      .then(async (reportResult) => {
        setReport(reportResult);
        if (reportResult.patient_id) {
          try {
            const patientResult = await getPatient(reportResult.patient_id);
            setPatient(patientResult);
          } catch {
            setPatient(null);
          }
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : t("workspace.errLoad"));
      });
    getCurrentDoctor()
      .then((doctor) => setCurrentDoctorId(doctor?.id ?? null))
      .catch(() => setCurrentDoctorId(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  const agreement = useMemo(() => {
    if (!report) return null;
    return computeAgreement(report.retrieved_cases);
  }, [report]);

  const diffSummary = useMemo(() => {
    if (!report) return null;
    return computeReportDiff(report.ai_draft_content, report.content);
  }, [report]);

  const reportOwnerId = report?.doctor_id ?? null;
  const isOwner = reportOwnerId !== null && currentDoctorId !== null && reportOwnerId === currentDoctorId;
  const otherOwnerName = useDoctorName(isOwner ? null : reportOwnerId);
  const finalizedByName = useDoctorName(report?.finalized_by ?? null);

  const canEdit = isOwner && report?.status !== "final";
  const hasUnsavedChanges = dirtyFields.size > 0;

  const handleDirtyChange = useCallback((key: ReportContentKey, dirty: boolean) => {
    setDirtyFields((prev) => {
      const next = new Set(prev);
      if (dirty) next.add(key);
      else next.delete(key);
      return next;
    });
  }, []);

  const handleEditingChange = useCallback((key: ReportContentKey, editing: boolean) => {
    setEditingFields((prev) => {
      const next = new Set(prev);
      if (editing) next.add(key);
      else next.delete(key);
      return next;
    });
  }, []);

  /**
   * Printing counts as "the full report is open", because what the browser
   * puts on paper must be the whole document -- a printout of a report with
   * five sections silently missing is a clinical document that misrepresents
   * itself.
   *
   * There is no in-app PDF view to hook instead: the Download PDF control on
   * this screen is disabled and titled "out of scope for this thesis (frozen
   * Phase 12 spec)". So the print path IS the print/PDF path here, and
   * beforeprint/afterprint is what it exposes. matchMedia("print") is checked
   * alongside it because Safari fires the media query but not the events.
   */
  useEffect(() => {
    const before = () => setPrinting(true);
    const after = () => setPrinting(false);
    window.addEventListener("beforeprint", before);
    window.addEventListener("afterprint", after);

    const mql = window.matchMedia?.("print");
    const onChange = (e: MediaQueryListEvent) => setPrinting(e.matches);
    mql?.addEventListener?.("change", onChange);

    return () => {
      window.removeEventListener("beforeprint", before);
      window.removeEventListener("afterprint", after);
      mql?.removeEventListener?.("change", onChange);
    };
  }, []);

  // Panel preferences, remembered per doctor in this browser only. Scoped to
  // currentDoctorId so two doctors at one workstation do not inherit each
  // other's layout; until that id arrives the hook stays on the default and
  // touches no storage. Never sent to the backend -- see the hook's docstring.
  const [fullReportChoice, setFullReportChoice] = usePersistedToggle(
    currentDoctorId,
    FULL_REPORT_PREF,
    false, // default collapsed: the summary is the point of the screen
  );
  const [evidenceCollapsed, setEvidenceCollapsed] = usePersistedToggle(
    currentDoctorId,
    EVIDENCE_PREF,
    false, // default expanded for a first-time reader
  );

  // The four states that hold the full report open -- see full-report-rules.ts
  // for what each one protects. A regeneration counts as in flight both while
  // the call is out and while its candidate is waiting on Accept/Discard.
  const forceState = {
    editing: editingFields.size > 0,
    regenerating: regeneratingField !== null || regenerationResult !== null,
    finalizing: showPreview,
    printing,
  };
  const forceFullReport = shouldForceFullReport(forceState);
  const fullReportOpen = fullReportChoice || forceFullReport;
  const forcedReasonKey = fullReportForcedReasonKey(forceState);

  // beforeunload -- covers tab close/refresh/typed-URL navigation. This is
  // the one part of the guard the browser itself enforces; everything
  // else below is a best-effort in-app interception only.
  useEffect(() => {
    function handler(e: BeforeUnloadEvent) {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

  function guardedNavigate(e: React.MouseEvent) {
    if (hasUnsavedChanges && !window.confirm(t("workspace.confirmLeave"))) {
      e.preventDefault();
    }
  }

  async function handleCommit(key: ReportContentKey, nextValue: string) {
    if (!report) return;
    setSavingField(key);
    setActionError(null);
    try {
      const updated = await updateReport(reportId, { [key]: nextValue });
      setReport(updated);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : t("workspace.errSave"));
    } finally {
      setSavingField(null);
    }
  }

  async function handleRestoreAiDraft() {
    if (!report) return;
    if (!window.confirm(t("workspace.confirmRestore"))) return;
    setRestoring(true);
    setActionError(null);
    try {
      const restoreValues = EDITABLE_REPORT_FIELDS.reduce(
        (acc, field) => {
          acc[field] = report.ai_draft_content[field];
          return acc;
        },
        {} as Record<EditableReportField, string>,
      );
      const updated = await updateReport(reportId, restoreValues);
      setReport(updated);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : t("workspace.errRestore"));
    } finally {
      setRestoring(false);
    }
  }


  async function handleRegenerate(field: EditableReportField) {
    if (!report) return;
    setRegeneratingField(field);
    setRegenerationError(null);
    setRegenerationErrorField(null);
    setRegenerationResult(null);
    try {
      const result = await regenerateSection(reportId, field);
      setRegenerationResult({ field, candidate: result.candidate, contextIncomplete: result.context_incomplete });
    } catch (err) {
      setRegenerationError(err instanceof ApiError ? err.message : t("workspace.errRegen"));
      setRegenerationErrorField(field);
    } finally {
      setRegeneratingField(null);
    }
  }

  async function handleAcceptRegeneration() {
    if (!regenerationResult) return;
    await handleCommit(regenerationResult.field, regenerationResult.candidate);
    setRegenerationResult(null);
  }

  function handleDiscardRegeneration() {
    // No request fired at all -- Decision 1's entire point.
    setRegenerationResult(null);
  }

  async function handleFinalizeConfirm() {
    const updated = await finalizeReport(reportId);
    setReport(updated);
    setShowPreview(false);
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app p-30">
        <p className="rounded-field border border-amber-line bg-amber-wash px-16 py-12 text-sm text-amber">
          {error}
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app">
        <p className="text-text-tertiary">{t("workspace.loading")}</p>
      </div>
    );
  }

  const contextMeta = [patient?.patient_code, report.report_date].filter(Boolean).join(" · ");

  /**
   * One renderer for all seven sections, used by both the summary and the
   * disclosure. Written once rather than twice: the summary's impression is
   * the same editable, regeneratable section it has always been, and the only
   * difference between the two groups is where they sit. Two copies of this
   * JSX would be two places for the edit affordances to drift apart.
   */
  const renderSection = (key: ReportContentKey) => {
    const isRegeneratable = EDITABLE_KEYS.has(key);
    const activePreview =
      isRegeneratable && regenerationResult?.field === key
        ? computeReportDiff(editableRecordFrom(report.content), {
            ...editableRecordFrom(report.content),
            [key]: regenerationResult.candidate,
          }).sections.find((section) => section.field === key) ?? null
        : null;

    return (
      <EditableReportSection
        key={key}
        fieldKey={key as ReportFieldKey}
        label={t(REPORT_FIELD_LABEL_KEY[key])}
        value={report.content[key] ?? ""}
        isEdited={report.content[key] !== report.ai_draft_content[key]}
        canEdit={!!canEdit && EDITABLE_KEYS.has(key)}
        saving={savingField === key}
        onCommit={(next) => handleCommit(key, next)}
        onDirtyChange={(dirty) => handleDirtyChange(key, dirty)}
        onEditingChange={(editing) => handleEditingChange(key, editing)}
        canRegenerate={isRegeneratable}
        regenerating={regeneratingField === key}
        regenerationPreview={activePreview}
        regenerationContextIncomplete={
          regenerationResult?.field === key && regenerationResult.contextIncomplete
        }
        regenerationError={regenerationErrorField === key ? regenerationError : null}
        onRegenerate={isRegeneratable ? () => handleRegenerate(key as EditableReportField) : undefined}
        onAcceptRegeneration={handleAcceptRegeneration}
        onDiscardRegeneration={handleDiscardRegeneration}
      />
    );
  };

  const fullReportHint = t("workspace.fullReportHint", {
    count: FULL_REPORT_FIELDS.length,
    fields: FULL_REPORT_FIELDS.map(({ key }) => t(REPORT_FIELD_LABEL_KEY[key])).join(", "),
  });

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-bg-app">
      {/* Study context bar */}
      <header className="flex h-header-bar flex-none items-center gap-14 border-b border-hairline px-24">
        {/* The only way out of this screen used to be the patient's name,
            styled as a heading -- a tester reported having no way to cancel or
            go back, which is what an unlabelled exit looks like. Routed through
            guardedNavigate so the unsaved-changes prompt still fires. */}
        <BackLink
          href={patient ? `/patients/${patient.id}` : "/dashboard"}
          onClick={guardedNavigate}
        />
        {patient ? (
          <Link
            href={`/patients/${patient.id}`}
            onClick={guardedNavigate}
            className="truncate text-base font-semibold text-text-primary transition-colors duration-hover hover:text-cyan"
          >
            {patient.name}
          </Link>
        ) : (
          <span className="text-base font-semibold text-text-primary">{t("workspace.reportFallback")}</span>
        )}
        {contextMeta && (
          <span className="truncate font-mono text-mono-meta-lg text-text-tertiary">{contextMeta}</span>
        )}
        <span className="flex-1" />

        {/* Phase 18: visible to any doctor who can already read this report
            (Decision 7), owner or not, pre- or post-finalize. */}
        {/* The ask/answer feature already existed at /reports/{id}/explain, but
            nothing on this screen or Compare pointed at it, and a tester
            reported it as missing. It is a link, not a new capability. */}
        <Link
          href={`/reports/${reportId}/explain`}
          onClick={guardedNavigate}
          className="text-sm font-medium text-text-secondary transition-colors duration-hover hover:text-cyan"
        >
          {t("workspace.askAbout")}
        </Link>
        <button
          type="button"
          onClick={() => setShowDiff((prev) => !prev)}
          className="text-sm font-medium text-text-secondary transition-colors duration-hover hover:text-cyan"
        >
          {showDiff ? t("workspace.hideChanges") : t("workspace.showChanges")}
        </button>
        <OwnerChip ownerId={reportOwnerId} currentDoctorId={currentDoctorId} />
        <StatusChip status={toChipReportStatus(report.status)} />
        {canEdit && (
          <button
            type="button"
            onClick={() => setShowPreview(true)}
            className={cn(BUTTON_BASE, VARIANT.primary, SIZE.md)}
          >
            {t("workspace.finalize")}
          </button>
        )}
      </header>

      {showDiff && diffSummary && (
        <div className="flex-none border-b border-hairline bg-bg-raised px-24 py-20">
          <ReportDiffView summary={diffSummary} />
        </div>
      )}

      {!isOwner && reportOwnerId !== null && (
        <div className="flex-none border-b border-hairline bg-bg-hover px-24 py-12 text-sm text-text-secondary">
          {t("workspace.belongsToPre")} {otherOwnerName ?? t("workspace.anotherDoctor")}
          {t("workspace.belongsToPost")}
        </div>
      )}

      {/* Three-column reading station: film, report, evidence. On a monitor
          narrower than the station, scroll rather than clip a column. */}
      <div className="flex min-h-0 flex-1 overflow-x-auto">
        {/* Film -- the only pure-black surface */}
        <div className="relative flex min-w-film flex-1 items-center justify-center on-film bg-bg-film p-26">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={retrievalSessionImageUrl(report.session_id)}
            alt={`${t("workspace.altXrayPrefix")}, ${report.report_date}`}
            className="max-h-full max-w-full object-contain"
          />
          {/* PHI masking is real (Phase 1): the persisted film is masked. */}
          <span className="absolute left-26 top-26 font-mono text-mono-meta uppercase tracking-[0.12em] text-cyan">
            {t("workspace.phiMasked")}
          </span>
        </div>

        {/* Report as document. Widens into the space the evidence panel frees
            when it docks -- but only to --report-col-wide, because the prose
            inside is capped at --report-prose (74ch). Past that the extra
            width would be gutter, and body text stretched edge to edge is
            harder to read, not easier. Film (flex-1) takes the remainder. */}
        <section
          className={cn(
            "flex flex-none flex-col border-l border-hairline",
            "transition-[width] duration-panel ease-panel",
            evidenceCollapsed ? "w-report-col-wide" : "w-report-col",
          )}
        >
          <div className="flex-1 overflow-auto px-26 pb-26 pt-24">
            <div className="mb-20 flex items-baseline gap-12">
              <span className="font-mono text-eyebrow uppercase text-text-tertiary">
                {report.status === "final" ? t("workspace.finalizedReport") : t("workspace.aiReport")} · {report.report_date}
              </span>
              <span className="flex-1" />
              {canEdit && (
                <button
                  type="button"
                  onClick={handleRestoreAiDraft}
                  disabled={restoring}
                  className="font-mono text-eyebrow uppercase tracking-[0.14em] text-text-tertiary transition-colors duration-hover hover:text-cyan disabled:opacity-50"
                >
                  {restoring ? t("workspace.restoring") : t("workspace.restoreDraft")}
                </button>
              )}
            </div>

            {report.status === "final" && report.finalized_at && (
              <p className="mb-20 text-sm text-text-tertiary">
                {t("workspace.finalizedBy", {
                  name: finalizedByName ?? t("workspace.thisDoctor"),
                  date: new Date(report.finalized_at).toLocaleDateString(),
                })}
              </p>
            )}

            {/* ── SUMMARY ────────────────────────────────────────────────
                Impression and recommendation, the validation warnings and the
                consistency verdict. Nothing here is behind a control, in any
                state: a doctor must not have to open anything to find out
                that this report carries a warning, or to read its conclusion.
                ───────────────────────────────────────────────────────────── */}
            <div className="flex flex-col">{SUMMARY_FIELDS.map(({ key }) => renderSection(key))}</div>

            {actionError && (
              <div className="mt-16 rounded-field border border-amber-line bg-amber-wash px-14 py-12 text-sm text-amber">
                {actionError}
              </div>
            )}

            {/* Validation -- amber only when there is something to look at;
                a clean pass stays quiet rather than inventing a success hue.
                The clean state still renders: absence would be read as "no
                problems" by a reader who cannot tell it from "not checked",
                which is the same failure the consistency block below is
                built to avoid. */}
            <div
              className={cn(
                "mt-16 rounded-panel border p-14",
                report.validation.is_clean ? "border-hairline" : "border-amber-line bg-amber-wash",
              )}
            >
              <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">{t("workspace.validation")}</h3>
              {report.validation.is_clean ? (
                <p className="mt-8 text-body-read text-text-secondary">{t("workspace.noWarnings")}</p>
              ) : (
                // list-outside + padding, not list-inside: with the body text
                // now at 16px these warnings wrap, and list-inside returns the
                // second line to the left margin so it reads as a new item.
                <ul className="mt-8 flex list-outside list-disc flex-col gap-8 pl-18 text-body-read text-amber">
                  {report.validation.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* Phase 22 v1.2's consistency verdict -- four states, never
                collapsible. `language` decides which not-run reason is true,
                per frozen §3.4. */}
            <div className="mt-16">
              <ConsistencyState block={report.consistency} language={report.language} />
            </div>

            {/* ── FULL REPORT ────────────────────────────────────────────── */}
            <FullReportDisclosure
              id="full-report"
              open={fullReportOpen}
              forced={forceFullReport}
              forcedReason={t(forcedReasonKey)}
              hint={fullReportHint}
              onToggle={() => setFullReportChoice(!fullReportChoice)}
            >
              <div className="flex flex-col">
                {FULL_REPORT_FIELDS.map(({ key }) => renderSection(key))}
              </div>
            </FullReportDisclosure>

            {/* Actions */}
            <div className="mt-16 flex flex-wrap gap-12">
              <Link
                href={`/reports/${reportId}/explain`}
                onClick={guardedNavigate}
                className={cn(BUTTON_BASE, VARIANT.primary, SIZE.md, "flex-1")}
              >
                {t("workspace.explainReport")}
              </Link>
              <Link
                href={`/reports/${reportId}/compare`}
                onClick={guardedNavigate}
                className={cn(BUTTON_BASE, VARIANT.secondary, SIZE.md, "flex-1")}
              >
                {t("workspace.comparePrevious")}
              </Link>
              <button
                type="button"
                disabled
                title={t("workspace.downloadPdfTitle")}
                className={cn(BUTTON_BASE, VARIANT.ghost, SIZE.md, "flex-1")}
              >
                {t("workspace.downloadPdf")}
              </button>
            </div>

            <p className="mt-26 border-t border-hairline pt-16 text-caption leading-relaxed text-text-tertiary">
              {t("workspace.draftedFrom", { count: report.retrieved_cases.length })}
            </p>
          </div>
        </section>

        {/* Evidence sidebar -- quieter surface, docks to a rail rather than
            disappearing. Its prose is now set in the same body token as the
            report column (see report-typography.ts). */}
        <EvidenceSidebar
          id="evidence-panel"
          collapsed={evidenceCollapsed}
          onToggle={() => setEvidenceCollapsed(!evidenceCollapsed)}
          activeTab={railTab}
          onTabChange={setRailTab}
        >
            {railTab === "evidence" && (
              <div className="flex flex-col gap-16">
                <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">
                  {t("workspace.archiveCases", { count: report.retrieved_cases.length })}
                </h3>
                {report.retrieved_cases.map((c) => (
                  <div key={c.rank} className="rounded-panel border border-hairline p-14">
                    <div className="flex items-center gap-8">
                      <span className="font-mono text-mono-meta text-cyan">#{c.rank}</span>
                      <span className="font-medium text-text-primary">{c.primary_label}</span>
                    </div>
                    <SimilarityBar value={c.similarity * 100} className="mt-12" />
                    <p className="mt-12 max-w-report-prose text-body-read text-text-secondary">{c.findings}</p>
                    <p className="mt-8 max-w-report-prose text-body-read text-text-secondary">{c.impression}</p>
                  </div>
                ))}
              </div>
            )}

            {railTab === "agreement" && (
              <div className="flex flex-col gap-16">
                {/* §7.1's Rule: both signals, never one alone. Retrieval
                    support sits ABOVE the agreement badge because it
                    qualifies it -- high agreement among cases that are
                    all far from this image is not strong evidence, and a
                    reader who stops after the first panel must not have
                    stopped at the reassuring one. Rendered even when
                    `agreement` is null, since the support category is
                    stored on the report and does not depend on the
                    client-side agreement re-derivation. */}
                <RetrievalSupportNotice
                  category={
                    (report.retrieval_support as RetrievalSupportCategory | null | undefined) ?? null
                  }
                  topSimilarity={report.top1_similarity ?? null}
                />
                {agreement && (
                  <AgreementBadge level={agreement.level} factors={agreement.factors} />
                )}
              </div>
            )}

            {railTab === "alternatives" && agreement && (
              <div className="flex flex-col gap-16">
                <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">
                  {t("workspace.presentInSet")}
                </h3>
                <dl className="flex flex-col border-t border-hairline">
                  {agreement.presentLabels.map(({ label, count, k }) => (
                    <div
                      key={label}
                      className="flex items-center justify-between border-b border-hairline py-12"
                    >
                      <dt className="text-body-read text-text-secondary">{label}</dt>
                      <dd className="font-mono text-body-read text-text-primary">
                        {t("workspace.countOfK", { count, k })}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="max-w-report-prose text-body-read text-text-secondary">
                  {t("workspace.altNotePre")}{" "}
                  <span className="text-text-primary">{t("workspace.altNoteEmph")}</span>{" "}
                  {t("workspace.altNotePost")}
                </p>
              </div>
            )}
        </EvidenceSidebar>
      </div>

      {showPreview && diffSummary && (
        <FinalizePreview
          report={report}
          reportDate={report.report_date}
          diffSummary={diffSummary}
          onConfirm={handleFinalizeConfirm}
          onCancel={() => setShowPreview(false)}
        />
      )}
    </div>
  );
}
