"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { StatusChip } from "@/components/ui/chip";
import { OwnerChip } from "@/components/ui/owner-chip";
import { BackLink } from "@/components/layout/screen-header";
import { toChipReportStatus } from "@/lib/report-status";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { ReportDiffView } from "@/components/report/report-diff-view";
import { FinalizePreview } from "@/components/report/finalize-preview";
import { PrintableReport } from "@/components/report/printable-report";
import { PrintPortal } from "@/components/report/print-portal";
import { WorkspaceProvider, useWorkspace } from "@/components/workspace/workspace-provider";
import { WorkspaceSteps, type WorkspaceStep } from "@/components/workspace/workspace-steps";

/**
 * The workspace frame, shared by the report and evidence routes.
 *
 * THIS LAYOUT IS THE NO-REFETCH GUARANTEE. Next keeps a segment layout mounted
 * while its children change, so the report is fetched once by WorkspaceProvider
 * and both pages read the same object. Moving between them fires no request --
 * not because a cache answers it, but because nothing asks again.
 *
 * Everything that must outlive a page change lives here: the fetched report,
 * the mutation handlers, the dirty/editing sets behind both unsaved-work
 * guards, the active evidence tab, and the print document. The print portal in
 * particular has to be here rather than on the report page, or printing would
 * only work from one of the two routes.
 */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ reportId: string }>();
  return (
    <WorkspaceProvider reportId={params.reportId}>
      <WorkspaceFrame>{children}</WorkspaceFrame>
    </WorkspaceProvider>
  );
}

function WorkspaceFrame({ children }: { children: React.ReactNode }) {
  const { t } = useT();
  const pathname = usePathname();
  const {
    reportId,
    report,
    patient,
    error,
    currentDoctorId,
    reportOwnerId,
    isOwner,
    canEdit,
    otherOwnerName,
    finalizedByName,
    diffSummary,
    showDiff,
    setShowDiff,
    showPreview,
    setShowPreview,
    handleFinalizeConfirm,
    guardedNavigate,
  } = useWorkspace();

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

  const step: WorkspaceStep = pathname.endsWith("/evidence") ? "evidence" : "report";
  const contextMeta = [patient?.patient_code, report.report_date].filter(Boolean).join(" · ");

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-bg-app">
      {/* Study context bar */}
      <header className="flex h-header-bar flex-none items-center gap-14 border-b border-hairline px-24">
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

        <WorkspaceSteps
          current={step}
          generateHref={report.patient_id ? `/patients/${report.patient_id}/upload` : null}
          reportHref={`/workspace/${reportId}/report`}
          evidenceHref={`/workspace/${reportId}/evidence`}
          onNavigate={guardedNavigate}
        />

        <span className="flex-1" />

        <Link
          href={`/reports/${reportId}/explain`}
          onClick={guardedNavigate}
          className="text-sm font-medium text-text-secondary transition-colors duration-hover hover:text-cyan"
        >
          {t("workspace.askAbout")}
        </Link>
        <button
          type="button"
          onClick={() => setShowDiff(!showDiff)}
          className="text-sm font-medium text-text-secondary transition-colors duration-hover hover:text-cyan"
        >
          {showDiff ? t("workspace.hideChanges") : t("workspace.showChanges")}
        </button>
        <OwnerChip ownerId={reportOwnerId} currentDoctorId={currentDoctorId} />
        <StatusChip status={toChipReportStatus(report.status)} />
      </header>

      {showDiff && diffSummary && (
        <div className="flex-none border-b border-hairline bg-bg-raised px-24 py-20">
          <ReportDiffView summary={diffSummary} />
        </div>
      )}

      {!isOwner && reportOwnerId !== null && (
        <div className={cn("flex-none border-b border-hairline bg-bg-hover px-24 py-12 text-sm text-text-secondary")}>
          {t("workspace.belongsToPre")} {otherOwnerName ?? t("workspace.anotherDoctor")}
          {t("workspace.belongsToPost")}
        </div>
      )}

      <div className="flex min-h-0 flex-1 overflow-x-auto">{children}</div>

      {/* Paper, reachable from either page. */}
      <PrintPortal>
        <PrintableReport
          report={report}
          patientName={patient?.name ?? null}
          patientCode={patient?.patient_code ?? null}
          finalizedByName={finalizedByName ?? null}
        />
      </PrintPortal>

      {showPreview && diffSummary && canEdit && (
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
