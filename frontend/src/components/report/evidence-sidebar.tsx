"use client";

import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";

export type EvidenceTab = "evidence" | "agreement" | "alternatives";

export const EVIDENCE_TABS: readonly EvidenceTab[] = ["evidence", "agreement", "alternatives"];

/**
 * The evidence panel, as a sidebar that docks rather than disappears.
 *
 * IT COLLAPSES TO A RAIL, NOT TO NOTHING. The collapsed state is
 * `--evidence-rail` (48px) wide and still carries a labelled reopen control.
 * A panel that collapses to zero width is a panel that a reader who collapsed
 * it by accident cannot get back, because the only thing that would reopen it
 * went away with it. The rail is the affordance; it is why this is a docked
 * sidebar and not a hide toggle.
 *
 * NOTHING UNMOUNTS AND NOTHING REFETCHES. The panel body renders on every
 * pass; collapsing sets `hidden` on it. So:
 *   - the active tab is still the active tab when it reopens, because the tab
 *     state was never destroyed -- no persistence needed for it, and no
 *     restore logic that could pick the wrong one;
 *   - no effect re-runs, so no request is fired. The evidence shown here came
 *     with the report in a single GET; collapsing a panel is a viewing
 *     preference and must not cost a round trip. A test asserts this.
 *
 * `hidden` is display:none, which takes the whole panel out of the
 * accessibility tree and the tab order when docked -- the collapsed content
 * is genuinely unreachable, not merely clipped out of sight.
 *
 * MOTION. Width animates over `--t-panel` with the shared `--ease`. Both are
 * tokens, and tokens.css already collapses every duration to 1ms under
 * `prefers-reduced-motion: reduce`, so reduced motion is honoured by the same
 * rule that honours it everywhere else rather than by a second conditional
 * here. Only width transitions; the contents do not slide or fade.
 */
export function EvidenceSidebar({
  id,
  collapsed,
  onToggle,
  activeTab,
  onTabChange,
  children,
}: {
  id: string;
  collapsed: boolean;
  onToggle: () => void;
  activeTab: EvidenceTab;
  onTabChange: (tab: EvidenceTab) => void;
  children: React.ReactNode;
}) {
  const { t } = useT();

  return (
    <aside
      className={cn(
        "flex flex-none flex-col overflow-hidden border-l border-hairline bg-bg-raised",
        "transition-[width] duration-panel ease-panel",
        collapsed ? "w-evidence-rail" : "w-evidence-panel",
      )}
    >
      {collapsed ? (
        // THE WHOLE RAIL IS THE BUTTON.
        //
        // It was a 28px icon-only control at the top of the rail, and it was
        // reported as invisible -- correctly: a bare chevron glyph in tertiary
        // grey, with no border and no fill, is indistinguishable from
        // decoration. A reader who collapsed the panel could not tell there
        // was a way back, which defeats the entire reason this docks to a rail
        // instead of closing.
        //
        // Two things fix that and they work together. The hit target is now
        // the full height of the rail, so the click is hard to miss rather
        // than needing to be aimed; and the rail carries its own name, set
        // vertically, so it says WHAT it will open rather than only that
        // something will. A docked panel that does not name itself is a
        // mystery stripe.
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={false}
          aria-controls={id}
          aria-label={t("workspace.expandEvidence")}
          title={t("workspace.expandEvidence")}
          className={cn(
            "group flex flex-1 flex-col items-center gap-14 py-14",
            "border-l-2 border-transparent bg-cyan-wash text-cyan",
            "transition-colors duration-hover hover:border-cyan hover:bg-cyan hover:text-cyan-ink",
          )}
        >
          <span aria-hidden="true" className="font-mono text-mono-meta-lg leading-none">
            ‹
          </span>
          <span
            aria-hidden="true"
            className="font-mono text-section-label uppercase tracking-[0.12em] [writing-mode:vertical-rl]"
          >
            {t("workspace.tabEvidence")}
          </span>
        </button>
      ) : (
        <div className="flex flex-none items-stretch border-b border-hairline">
          {EVIDENCE_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={cn(
                "flex-1 border-b-2 px-12 py-12 text-sm font-medium capitalize transition-colors duration-hover",
                activeTab === tab
                  ? "border-cyan text-cyan"
                  : "border-transparent text-text-tertiary hover:text-text-primary",
              )}
            >
              {t(`workspace.tab${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
            </button>
          ))}
          {/* The hide control. Given the accent wash and a left rule so it
              reads as a control rather than as a fourth, unlabelled tab -- it
              sat flush against the tabs in bare tertiary grey and was
              reported as invisible. */}
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={true}
            aria-controls={id}
            aria-label={t("workspace.collapseEvidence")}
            title={t("workspace.collapseEvidence")}
            className={cn(
              "flex w-38 flex-none items-center justify-center",
              "border-b-2 border-transparent border-l border-l-hairline bg-cyan-wash",
              "font-mono text-mono-meta-lg text-cyan",
              "transition-colors duration-hover hover:bg-cyan hover:text-cyan-ink",
            )}
          >
            <span aria-hidden="true">›</span>
          </button>
        </div>
      )}

      {/* Always rendered; `hidden` when docked. Never unmounted, so the active
          tab survives and no effect re-runs. */}
      <div id={id} hidden={collapsed} className="flex-1 overflow-auto p-20">
        {children}
      </div>
    </aside>
  );
}
