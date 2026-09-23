"use client";

import Link from "next/link";
import { retrievalSessionImageUrl } from "@/lib/api-client";
import { BUTTON_BASE, SIZE, VARIANT } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { EditableReportSection } from "@/components/report/editable-report-section";
import type { ReportFieldKey } from "@/components/report/report-typography";
import { REPORT_FIELD_LABEL_KEY } from "@/components/report/report-document-view";
import { FullReportDisclosure } from "@/components/report/full-report-disclosure";
import { ConsistencyState } from "@/components/report/consistency-state";
import { usePersistedToggle } from "@/lib/use-persisted-toggle";
import { shouldForceFullReport, fullReportForcedReasonKey } from "@/lib/full-report-rules";
import { computeReportDiff, editableRecordFrom } from "@/lib/report-diff";
import { hasReportContent } from "@/lib/report-content";
import {
  EDITABLE_KEYS,
  FULL_REPORT_FIELDS,
  FULL_REPORT_PREF,
  SUMMARY_FIELDS,
  type EditableReportField,
  type ReportContentKey,
} from "@/lib/report-fields";
import { useWorkspace } from "@/components/workspace/workspace-provider";

/**
 * The Result page: the film and the report, and nothing that belongs to the
 * evidence.
 *
 * SUMMARY FIRST, AND NEVER COLLAPSIBLE. Impression, recommendation, the
 * validation warnings and the consistency verdict render outside the
 * disclosure in every state. A doctor must not have to open a control to find
 * out that this report carries a warning, or to read its conclusion. The other
 * five sections sit behind "Show full report", which auto-expands and locks
 * open while editing, regenerating, finalizing or printing.
 *
 * The evidence tabs used to sit in a sidebar here. They now have their own
 * full-width route, reached by "View evidence" -- and because the report lives
 * in the shared layout, going there and coming back fetches nothing.
 */
export default function WorkspaceReportPage() {
  const { t } = useT();
  const {
    reportId,
    report,
    canEdit,
    currentDoctorId,
    finalizedByName,
    savingField,
    restoring,
    actionError,
    editingFields,
    regeneratingField,
    regenerationResult,
    regenerationError,
    regenerationErrorField,
    printing,
    setShowPreview,
    handleCommit,
    handleRestoreAiDraft,
    handleRegenerate,
    handleAcceptRegeneration,
    handleDiscardRegeneration,
    handleDirtyChange,
    handleEditingChange,
    guardedNavigate,
  } = useWorkspace();

  const [fullReportChoice, setFullReportChoice] = usePersistedToggle(
    currentDoctorId,
    FULL_REPORT_PREF,
    false, // default collapsed: the summary is the point of the screen
  );

  if (!report) return null;

  const forceState = {
    editing: editingFields.size > 0,
    regenerating: regeneratingField !== null || regenerationResult !== null,
    finalizing: false,
    printing,
  };
  const forceFullReport = shouldForceFullReport(forceState);
  const fullReportOpen = fullReportChoice || forceFullReport;
  const forcedReasonKey = fullReportForcedReasonKey(forceState);

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
    <>
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

      {/* Report as document */}
      <section className="flex w-report-col flex-none flex-col border-l border-hairline">
        <div className="flex-1 overflow-auto px-26 pb-26 pt-24">
          <div className="mb-20 flex items-baseline gap-12">
            <span className="font-mono text-eyebrow uppercase text-text-tertiary">
              {report.status === "final" ? t("workspace.finalizedReport") : t("workspace.aiReport")} ·{" "}
              {report.report_date}
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

          {/* ── SUMMARY ──────────────────────────────────────────────────── */}
          <div className="flex flex-col">{SUMMARY_FIELDS.map(({ key }) => renderSection(key))}</div>

          {actionError && (
            <div className="mt-16 rounded-field border border-amber-line bg-amber-wash px-14 py-12 text-sm text-amber">
              {actionError}
            </div>
          )}

          {/* Validation -- amber only when there is something to look at; the
              clean state still renders, because absence would be read as "no
              problems" by a reader who cannot tell it from "not checked". */}
          <div
            className={cn(
              "mt-16 rounded-panel border p-14",
              report.validation.is_clean ? "border-hairline" : "border-amber-line bg-amber-wash",
            )}
          >
            <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">
              {t("workspace.validation")}
            </h3>
            {report.validation.is_clean ? (
              <p className="mt-8 text-body-read text-text-secondary">{t("workspace.noWarnings")}</p>
            ) : (
              <ul className="mt-8 flex list-outside list-disc flex-col gap-8 pl-18 text-body-read text-amber">
                {report.validation.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Phase 22 v1.2's consistency verdict -- four states, never
              collapsible. `language` decides which not-run reason is true. */}
          <div className="mt-16">
            <ConsistencyState block={report.consistency} language={report.language} />
          </div>

          {/* ── FULL REPORT ──────────────────────────────────────────────── */}
          <FullReportDisclosure
            id="full-report"
            open={fullReportOpen}
            forced={forceFullReport}
            forcedReason={t(forcedReasonKey)}
            hint={fullReportHint}
            onToggle={() => setFullReportChoice(!fullReportChoice)}
          >
            <div className="flex flex-col">{FULL_REPORT_FIELDS.map(({ key }) => renderSection(key))}</div>
          </FullReportDisclosure>

          {/* Actions */}
          <div className="mt-16 flex flex-wrap gap-12">
            <Link
              href={`/workspace/${reportId}/evidence`}
              className={cn(BUTTON_BASE, VARIANT.primary, SIZE.md, "flex-1")}
            >
              {t("workspace.viewEvidence")}
            </Link>
            <Link
              href={`/reports/${reportId}/explain`}
              onClick={guardedNavigate}
              className={cn(BUTTON_BASE, VARIANT.secondary, SIZE.md, "flex-1")}
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
          </div>

          <div className="mt-12 flex flex-wrap gap-12">
            <button
              type="button"
              onClick={() => window.print()}
              disabled={!hasReportContent(report.content)}
              title={t("workspace.downloadPdfTitle")}
              className={cn(BUTTON_BASE, VARIANT.ghost, SIZE.md, "flex-1")}
            >
              {t("workspace.downloadPdf")}
            </button>
            {canEdit && (
              <button
                type="button"
                onClick={() => setShowPreview(true)}
                className={cn(BUTTON_BASE, VARIANT.primary, SIZE.md, "flex-1")}
              >
                {t("workspace.finalize")}
              </button>
            )}
          </div>

          <p className="mt-26 border-t border-hairline pt-16 text-caption leading-relaxed text-text-tertiary">
            {t("workspace.draftedFrom", { count: report.retrieved_cases.length })}
          </p>
        </div>
      </section>
    </>
  );
}
