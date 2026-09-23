"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";

export type WorkspaceStep = "generate" | "report" | "evidence";

const ORDER: WorkspaceStep[] = ["generate", "report", "evidence"];

const LABEL_KEY: Record<WorkspaceStep, string> = {
  generate: "workspace.stepGenerate",
  report: "workspace.stepReport",
  evidence: "workspace.stepEvidence",
};

/**
 * Generate → Report → Evidence, and where you are in it.
 *
 * The workspace used to be one screen, so "where am I" never needed answering.
 * Splitting it into three routes makes that a real question, and a step bar is
 * the answer that also doubles as the way back -- a reader who opened the
 * evidence page should not have to find the browser's back button to return to
 * the report.
 *
 * REACHED steps are links; the current one is not, and carries
 * `aria-current="step"`. A step you have not got to yet renders as plain text
 * rather than a disabled link: there is nothing at the other end of it, and a
 * control that looks clickable and is not is worse than no control.
 *
 * Every link routes through `guardedNavigate`, because the step bar is now one
 * of the ways to walk away from an unsaved edit -- the same guard the header
 * links have always carried.
 */
export function WorkspaceSteps({
  current,
  generateHref,
  reportHref,
  evidenceHref,
  onNavigate,
}: {
  current: WorkspaceStep;
  /** null when the report carries no patient, so Generate has no destination. */
  generateHref: string | null;
  reportHref: string;
  evidenceHref: string;
  onNavigate: (e: { preventDefault: () => void }) => void;
}) {
  const { t } = useT();
  const currentIndex = ORDER.indexOf(current);

  const hrefOf = (step: WorkspaceStep): string | null =>
    step === "generate" ? generateHref : step === "report" ? reportHref : evidenceHref;

  return (
    <nav aria-label={t("workspace.stepsAria")} className="flex items-center gap-8">
      {ORDER.map((step, i) => {
        const isCurrent = step === current;
        // Evidence is always reachable from the report, so "reached" means
        // anything at or before the current step, plus the next one when we
        // already have a report to show evidence for.
        const reached = i <= currentIndex || (currentIndex >= 1 && step === "evidence");
        const href = hrefOf(step);
        const label = t(LABEL_KEY[step]);

        return (
          <span key={step} className="flex items-center gap-8">
            {i > 0 && (
              <span aria-hidden="true" className="font-mono text-mono-meta text-text-muted">
                ›
              </span>
            )}
            {isCurrent ? (
              <span
                aria-current="step"
                className="rounded-control border border-cyan-line bg-cyan-wash px-10 py-5 font-mono text-section-label uppercase tracking-[0.1em] text-cyan"
              >
                {label}
              </span>
            ) : reached && href ? (
              <Link
                href={href}
                onClick={onNavigate}
                className={cn(
                  "rounded-control px-10 py-5 font-mono text-section-label uppercase tracking-[0.1em]",
                  "text-text-secondary transition-colors duration-hover hover:bg-bg-hover hover:text-cyan",
                )}
              >
                {label}
              </Link>
            ) : (
              <span className="rounded-control px-10 py-5 font-mono text-section-label uppercase tracking-[0.1em] text-text-muted">
                {label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
