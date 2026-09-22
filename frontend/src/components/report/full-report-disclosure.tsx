"use client";

import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";

/**
 * The "Full report" disclosure: everything the summary does not already show.
 *
 * WHAT IS NOT IN HERE, and why that is the whole design. Impression,
 * recommendation, the validation warnings and the consistency verdict stay
 * outside this component, permanently visible, and are not passed to it. A
 * radiologist must never have to open a control to discover that the report
 * they are reading carries a warning, or to read the conclusion. Those are the
 * two things the screen exists to deliver; the examination/history/technique/
 * findings/disclaimer block is context you consult, which is a different act.
 *
 * So this is a disclosure over CONTEXT, never over CONCLUSIONS or ALERTS. If a
 * future change moves a warning inside it, that change is wrong regardless of
 * how it looks.
 *
 * NEVER UNMOUNTS. The children render on every pass and collapsing only sets
 * `hidden` on their wrapper. Two reasons, both load-bearing:
 *
 *   - `hidden` is display:none, so the content leaves the accessibility tree
 *     and the tab order entirely. Visually clipping it (max-height:0,
 *     overflow:hidden) would leave a screen-reader user hearing five sections
 *     the sighted reader was told are closed, and would leave focusable
 *     controls inside reachable by Tab from nowhere visible.
 *   - Keeping the children mounted means toggling cannot trigger a fetch.
 *     Every section in there is already-loaded report text; unmounting and
 *     remounting would at best re-run effects for no reason, and this
 *     workspace's data effect is keyed on the report id precisely so the
 *     report is fetched once. A test asserts no request fires on toggle.
 *
 * FORCED OPEN. `forced` makes the disclosure non-collapsible rather than
 * merely open: the control stays in place, keeps `aria-expanded="true"`, and
 * is disabled with the reason shown next to it. Removing the control while a
 * section is being edited would make it disappear and come back as the state
 * changes, which reads as a bug; disabling it explains itself.
 */
export function FullReportDisclosure({
  id,
  open,
  forced,
  forcedReason,
  hint,
  onToggle,
  children,
}: {
  /** The id the toggle's aria-controls points at. */
  id: string;
  /** Resolved open state -- already the union of the stored choice and `forced`. */
  open: boolean;
  /** True while the report must stay open (editing, regenerating, printing, finalizing). */
  forced: boolean;
  /** Why it is held open, shown beside the disabled control. */
  forcedReason?: string;
  /** What is inside, e.g. "5 sections · Examination, Clinical History, …". */
  hint: string;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const { t } = useT();

  return (
    <div className="mt-16 border-t border-hairline pt-16">
      <div className="flex items-center gap-12">
        <button
          type="button"
          // A real <button>: Enter and Space both activate it natively, and it
          // is in the tab order without a tabindex. Rebuilding this on a div
          // with a keydown handler is how the two keys drift apart.
          onClick={onToggle}
          disabled={forced}
          aria-expanded={open}
          aria-controls={id}
          className={cn(
            // flex-none + nowrap: the hint beside it is long, and without this
            // the control itself is what flex shrinks, breaking "Show full
            // report" across two lines.
            "flex flex-none items-center gap-8 whitespace-nowrap rounded-control px-10 py-8",
            "text-sm font-medium",
            "text-text-secondary transition-colors duration-hover hover:text-cyan",
            "disabled:cursor-default disabled:text-text-tertiary disabled:hover:text-text-tertiary",
          )}
        >
          <span aria-hidden="true" className="font-mono text-mono-meta">
            {open ? "▾" : "▸"}
          </span>
          {open ? t("workspace.hideFullReport") : t("workspace.showFullReport")}
        </button>

        <span className="truncate font-mono text-mono-meta text-text-tertiary">
          {forced && forcedReason ? forcedReason : hint}
        </span>
      </div>

      {/* Always rendered. `hidden` (display:none) is what takes it out of the
          accessibility tree and the tab order when closed -- not a height or
          an opacity, either of which would hide it from the eye only. */}
      <div id={id} hidden={!open} className="mt-16">
        {children}
      </div>
    </div>
  );
}
