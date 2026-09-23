"use client";

import Link from "next/link";
import { SimilarityBar } from "@/components/ui/similarity-bar";
import { AgreementBadge } from "@/components/ui/agreement-badge";
import {
  RetrievalSupportNotice,
  type RetrievalSupportCategory,
} from "@/components/ui/retrieval-support-notice";
import { BUTTON_BASE, SIZE, VARIANT } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { useWorkspace, type EvidenceTab } from "@/components/workspace/workspace-provider";

const EVIDENCE_TABS: readonly EvidenceTab[] = ["evidence", "agreement", "alternatives"];

/**
 * The retrieved evidence, full width.
 *
 * This was a 340px sidebar that docked to a 48px rail, because on a
 * single-screen workspace it was competing with the report for the same 1440px
 * and losing. Given its own route it has the whole width, and the cases can be
 * read as cases rather than as a column of truncated cards.
 *
 * IT FETCHES NOTHING. Every value here -- the retrieved cases, the agreement
 * re-derivation, the stored retrieval-support category -- comes off the report
 * that the workspace layout already holds. That is what makes arriving here
 * and going back free, and it is asserted by test rather than assumed.
 *
 * `railTab` lives in the layout for the same reason: a tab owned by this page
 * would reset every time the page unmounted, and "the active tab is preserved
 * when returning" would quietly be false.
 */
export default function WorkspaceEvidencePage() {
  const { t } = useT();
  const { reportId, report, agreement, railTab, setRailTab, guardedNavigate } = useWorkspace();

  if (!report) return null;

  return (
    <section className="flex min-w-0 flex-1 flex-col">
      <div className="flex flex-none items-stretch gap-14 border-b border-hairline px-24">
        {EVIDENCE_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setRailTab(tab)}
            // "true", not "page": the app rail already marks the current
            // PAGE with aria-current="page", and a tab within this page is a
            // current item in a set, not a second current page. Two
            // aria-current="page" nodes on one document is a claim no reader
            // can resolve.
            aria-current={railTab === tab ? "true" : undefined}
            className={cn(
              "border-b-2 px-12 py-14 text-sm font-medium capitalize transition-colors duration-hover",
              railTab === tab
                ? "border-cyan text-cyan"
                : "border-transparent text-text-tertiary hover:text-text-primary",
            )}
          >
            {t(`workspace.tab${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
          </button>
        ))}
        <span className="flex-1" />
        <Link
          href={`/workspace/${reportId}/report`}
          onClick={guardedNavigate}
          className={cn(BUTTON_BASE, VARIANT.secondary, SIZE.sm, "my-12")}
        >
          {t("workspace.backToReport")}
        </Link>
      </div>

      <div className="flex-1 overflow-auto p-24">
        {railTab === "evidence" && (
          <div className="flex flex-col gap-16">
            <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">
              {t("workspace.archiveCases", { count: report.retrieved_cases.length })}
            </h3>
            <div className="grid grid-cols-2 gap-16">
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
          </div>
        )}

        {railTab === "agreement" && (
          <div className="flex max-w-report-prose flex-col gap-16">
            {/* §7.1's Rule: both signals, never one alone. Retrieval support
                sits ABOVE the agreement badge because it qualifies it -- high
                agreement among cases that are all far from this image is not
                strong evidence, and a reader who stops after the first panel
                must not have stopped at the reassuring one. */}
            <RetrievalSupportNotice
              category={(report.retrieval_support as RetrievalSupportCategory | null | undefined) ?? null}
              topSimilarity={report.top1_similarity ?? null}
            />
            {agreement && <AgreementBadge level={agreement.level} factors={agreement.factors} />}
          </div>
        )}

        {railTab === "alternatives" && agreement && (
          <div className="flex max-w-report-prose flex-col gap-16">
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
      </div>
    </section>
  );
}
