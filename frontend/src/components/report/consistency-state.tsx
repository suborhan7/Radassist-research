"use client";

import { useT } from "@/lib/i18n";
import {
  consistencyStatusOf,
  missingChecks,
  type ConsistencyBlock,
} from "@/lib/report-consistency";

/**
 * The Phase 22 v1.2 consistency verdict, as four states that look nothing
 * like each other.
 *
 * WHY FOUR SEPARATE RENDERERS AND NOT ONE WITH A TONE MAP. Every other
 * status surface in this app (AgreementBadge, RetrievalSupportNotice) is one
 * component with a lookup table of tones, and that is the right shape there:
 * those are points on one scale. This is not. The frozen architecture makes
 * the separation a safety requirement rather than a style preference
 * (docs/phase22/fix_architecture_v1.2_FROZEN.md §3.4):
 *
 *   "`consistency_checks_run == []` renders as *not run*, visually distinct
 *    from `consistency_violations == []` on an English report, which renders
 *    as *ran, no violations*. The two must not share a component, an icon, or
 *    a colour. A Bengali report showing a green tick -- or showing nothing at
 *    all, which a clinician reads as *nothing wrong* -- would convert an
 *    acknowledged coverage gap into an affirmative false assurance, which is
 *    worse than the gap itself."
 *
 * A shared body parameterised by a tone map is exactly the structure in which
 * a future edit to the "default" branch silently gives `not_run` the pass
 * treatment. Four bodies cannot drift into each other by accident; changing
 * one is a decision about that one.
 *
 * THE FOUR TREATMENTS, each distinct in colour, glyph and weight:
 *
 *   violations  amber, filled wash, "!"   the actionable state
 *   partial     primary text, strong      "◐"  incomplete, NOT a pass
 *               border, hover fill
 *   clean       cyan, cyan line, "✓"      the ONLY pass
 *   not_run     muted, hairline, "–"      nothing was assessed
 *
 * No green and no tick anywhere but `clean`, per the rule above. The word
 * carries the verdict in every state -- colour is never the only signal,
 * which is this project's existing rule (AgreementBadge's docstring) and also
 * what keeps the four distinguishable to a colour-blind reader.
 *
 * `partial` sits with `not_run`, not with `clean`, per
 * docs/phase22/amendment_01_consistency_status.md §2(a):
 *
 *   "`partial` must not be rendered as a pass. It is closer to `not_run` than
 *    to `clean` in what it licenses a reader to conclude."
 *
 * Until Gate B calibrates the transplant threshold this is the state nearly
 * every English report is in (§2(e)), so it is written as a real state with
 * its own explanation, not as an edge case.
 */

/** Shared chrome only -- the panel box. Carries no status-specific styling. */
function Frame({
  status,
  border,
  children,
}: {
  status: string;
  border: string;
  children: React.ReactNode;
}) {
  return (
    <section data-consistency={status} className={`rounded-panel border p-14 ${border}`}>
      {children}
    </section>
  );
}

function Head({ glyph, word, tone }: { glyph: string; word: string; tone: string }) {
  const { t } = useT();
  return (
    <div className="flex items-baseline justify-between gap-12">
      <h3 className="font-mono text-eyebrow uppercase text-text-tertiary">
        {t("consistency.title")}
      </h3>
      <span className={`flex items-baseline gap-8 text-sm font-medium ${tone}`}>
        <span aria-hidden="true">{glyph}</span>
        {word}
      </span>
    </div>
  );
}

/** Name a check list in the reader's language, e.g. "temporal, contradiction". */
function useCheckNames() {
  const { t } = useT();
  return (checks: string[]) => checks.map((c) => t(`consistency.check.${c}`)).join(", ");
}

/**
 * VIOLATIONS -- amber, the only state that is actionable. Amber is this
 * app's "look here" accent and it is spent here rather than on `partial`,
 * because a real finding outranks an incomplete check set (amendment 01
 * §2(c) property 2: "the violation is the actionable fact; the
 * incompleteness is secondary").
 */
function ViolationsState({ block }: { block: ConsistencyBlock }) {
  const { t } = useT();
  const violations = block.violations ?? [];
  return (
    <Frame status="violations" border="border-amber-line bg-amber-wash">
      <Head glyph="!" word={t("consistency.violations")} tone="text-amber" />
      <ul className="mt-12 flex flex-col gap-8">
        {violations.map((v, i) => (
          <li key={i} className="text-body-read text-amber">
            <span className="font-mono text-mono-meta uppercase">{v.field}</span> — {v.detail}
          </li>
        ))}
      </ul>
    </Frame>
  );
}

/**
 * PARTIAL -- deliberately NOT amber and NOT cyan. It is neither an alarm nor
 * a pass, and giving it either accent would file it under one of those two.
 * Primary text on the hover surface with a strong border reads as "present
 * and unresolved", which is what it is.
 */
function PartialState({ block }: { block: ConsistencyBlock }) {
  const { t } = useT();
  const names = useCheckNames();
  const ran = block.checks_run ?? [];
  const missing = missingChecks(block);
  // Both halves, by name, in the label and in the tooltip: the amendment's
  // point is that "some checks are missing" is not enough -- WHICH ones is
  // the information a reader needs to judge what the verdict covers.
  const detail = t("consistency.partialDetail", { ran: names(ran), missing: names(missing) });
  return (
    <Frame status="partial" border="border-strong bg-bg-hover">
      <Head glyph="◐" word={t("consistency.partial")} tone="text-text-primary" />
      <p className="mt-12 text-body-read text-text-secondary" title={detail}>
        {detail}
      </p>
    </Frame>
  );
}

/** CLEAN -- cyan and the only tick in the set. The one state that is a pass. */
function CleanState({ block }: { block: ConsistencyBlock }) {
  const { t } = useT();
  const names = useCheckNames();
  const ran = block.checks_run ?? [];
  return (
    <Frame status="clean" border="border-cyan-line">
      <Head glyph="✓" word={t("consistency.clean")} tone="text-cyan" />
      <p className="mt-12 text-body-read text-text-secondary">
        {t("consistency.cleanDetail", { ran: names(ran) })}
      </p>
    </Frame>
  );
}

/**
 * NOT RUN -- muted and quiet, with an en dash rather than any mark that
 * could be read as a verdict. It still renders a box and a word: the frozen
 * text is explicit that showing NOTHING is itself a failure mode, because a
 * clinician reads absence as "nothing wrong".
 *
 * The reason is shown, not just the state, and the two reasons are different
 * facts: a Bengali report is uncheckable by construction (§3.4 -- all three
 * detectors are English-only), whereas an English report here is a pre-v1.2
 * row whose columns were never written.
 */
function NotRunState({ language }: { language: string }) {
  const { t } = useT();
  const reason =
    language === "en" ? t("consistency.notRunPreV12") : t("consistency.notRunBengali");
  return (
    <Frame status="not_run" border="border-hairline">
      {/* text-tertiary, NOT text-muted. Muted measures 3.83:1 on bg-app in
          dark and 4.29:1 in light -- tokens.css documents it as a 3:1-target
          token for de-emphasised UI text, and this is a verdict a clinician
          acts on, which is body text and owes 4.5:1. Measured 7.57:1 dark /
          8.08:1 light on tertiary. */}
      <Head glyph="–" word={t("consistency.notRun")} tone="text-text-tertiary" />
      <p className="mt-12 text-body-read text-text-secondary" title={reason}>
        {reason}
      </p>
    </Frame>
  );
}

export function ConsistencyState({
  block,
  language,
}: {
  block: ConsistencyBlock | null | undefined;
  /** The report's own language -- decides which not-run reason is true. */
  language: string;
}) {
  const status = consistencyStatusOf(block);
  const safe: ConsistencyBlock = block ?? {};

  switch (status) {
    case "violations":
      return <ViolationsState block={safe} />;
    case "partial":
      return <PartialState block={safe} />;
    case "clean":
      return <CleanState block={safe} />;
    default:
      // `consistencyStatusOf` collapses every unknown or missing value to
      // "not_run", so this branch is also what a response with no consistency
      // block at all renders as -- under-claiming rather than over-claiming.
      return <NotRunState language={language} />;
  }
}
