"use client";

import { useT } from "@/lib/i18n";
import { REPORT_CONTENT_FIELDS, REPORT_FIELD_LABEL_KEY } from "./report-document-view";
import { consistencyStatusOf, missingChecks, type ConsistencyBlock } from "@/lib/report-consistency";
import { toChipReportStatus } from "@/lib/report-status";

/**
 * The report as it goes on paper.
 *
 * THIS IS A SECOND RENDER, NOT THE SCREEN RE-STYLED, and that is the whole
 * design. The workspace shows a summary first and hides five sections behind a
 * disclosure; a printed clinical document must carry all seven, in the order a
 * radiologist expects to read them, whatever the reader happened to have open
 * when they hit print. Trying to reach that by un-hiding the screen's DOM in a
 * print stylesheet would mean the printout's completeness depended on UI state
 * -- one stale CSS selector and a report silently prints five sections short.
 * Rendering the document independently makes "all seven, always" a property of
 * the markup rather than of a media query.
 *
 * It is driven by REPORT_CONTENT_FIELDS, the same canonical 7-field list the
 * screen uses, so a field added there appears here without anyone remembering
 * to add it.
 *
 * NOTHING HERE IS CONDITIONAL ON THE SCREEN'S STATE. There is no `collapsed`
 * prop and no way to pass one. The validation warnings and the consistency
 * verdict print whether or not they were on screen, for the same reason they
 * are never collapsible there: they are what a reader must not miss.
 *
 * This is browser print. It is labelled as such everywhere it is named -- the
 * control reads "Print / Save as PDF" and its tooltip says "(browser)". No PDF
 * is generated on the server and none is claimed to be.
 */
export function PrintableReport({
  report,
  patientName,
  patientCode,
  finalizedByName,
}: {
  report: {
    report_id: string;
    report_date: string;
    status: string;
    language: string;
    content: Record<string, string | null | undefined>;
    validation: { is_clean: boolean; warnings: string[] };
    consistency?: ConsistencyBlock | null;
    finalized_at?: string | null;
  };
  patientName: string | null;
  patientCode: string | null;
  /** Resolved display name for finalized_by, or null if unknown/not final. */
  finalizedByName: string | null;
}) {
  const { t } = useT();

  const statusLabel = t(
    {
      draft: "chip.statusDraft",
      review: "chip.statusReview",
      edited: "chip.statusEdited",
      final: "chip.statusFinal",
    }[toChipReportStatus(report.status)],
  );

  const consistency = report.consistency;
  const status = consistencyStatusOf(consistency);
  const ran = (consistency?.checks_run ?? []).map((c) => t(`consistency.check.${c}`)).join(", ");
  const missing = missingChecks(consistency).map((c) => t(`consistency.check.${c}`)).join(", ");

  const consistencyLine =
    status === "violations"
      ? t("consistency.violations")
      : status === "partial"
        ? `${t("consistency.partial")} — ${t("consistency.partialDetail", { ran, missing })}`
        : status === "clean"
          ? `${t("consistency.clean")} — ${t("consistency.cleanDetail", { ran })}`
          : `${t("consistency.notRun")} — ${
              report.language === "en" ? t("consistency.notRunPreV12") : t("consistency.notRunBengali")
            }`;

  return (
    <article className="rr-print-root" lang={report.language}>
      {/* Repeats at the top of every printed page (position:fixed in print). */}
      <header className="rr-print-running" aria-hidden="true">
        <span>{t("print.systemName")}</span>
        <span>
          {[patientName, patientCode].filter(Boolean).join(" · ")} · {report.report_date}
        </span>
      </header>

      <div className="rr-print-body">
        <h1 className="rr-print-title">{t("print.title")}</h1>

        <dl className="rr-print-meta">
          <div>
            <dt>{t("print.patient")}</dt>
            <dd>{patientName ?? t("print.notRecorded")}</dd>
          </div>
          <div>
            <dt>{t("print.patientCode")}</dt>
            <dd>{patientCode ?? t("print.notRecorded")}</dd>
          </div>
          <div>
            <dt>{t("print.studyDate")}</dt>
            <dd>{report.report_date}</dd>
          </div>
          <div>
            <dt>{t("print.status")}</dt>
            <dd>{statusLabel}</dd>
          </div>
        </dl>

        {/* All seven, in canonical order, unconditionally. */}
        {REPORT_CONTENT_FIELDS.map(({ key }) => (
          <section key={key} className="rr-print-section" data-print-section={key}>
            <h2>{t(REPORT_FIELD_LABEL_KEY[key])}</h2>
            <p>{report.content[key]?.trim() || t("compare.none")}</p>
          </section>
        ))}

        <section className="rr-print-section rr-print-validation" data-print-section="validation">
          <h2>{t("workspace.validation")}</h2>
          {report.validation.is_clean ? (
            <p>{t("workspace.noWarnings")}</p>
          ) : (
            <ul>
              {report.validation.warnings.map((warning, i) => (
                <li key={i}>{warning}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="rr-print-section" data-print-section="consistency">
          <h2>{t("consistency.title")}</h2>
          <p>{consistencyLine}</p>
        </section>

        {/* The signature block. Only a finalized report has one -- an AI draft
            is explicitly not a signed document, and printing a name under one
            would say otherwise. */}
        {report.status === "final" && report.finalized_at && (
          <section className="rr-print-section rr-print-signature" data-print-section="finalized">
            <h2>{t("print.finalized")}</h2>
            <p>
              {t("workspace.finalizedBy", {
                name: finalizedByName ?? t("workspace.thisDoctor"),
                date: new Date(report.finalized_at).toLocaleDateString(),
              })}
            </p>
          </section>
        )}

        <footer className="rr-print-footer">
          {t("print.footer", { id: report.report_id })}
        </footer>
      </div>
    </article>
  );
}
