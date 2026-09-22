/**
 * One typography rule for report body text, shared by every surface that renders
 * a report: the workspace sections (EditableReportSection), the finalize preview
 * and the read-only document view (ReportDocumentView).
 *
 * It exists because those surfaces had drifted. The report body was set in
 * `text-text-secondary` -- a mid-grey used elsewhere for captions and metadata --
 * so a whole clinical document was rendered in the colour reserved for labels,
 * and read as unreadable. Worse, EditableReportSection used `text-text-primary`
 * for the SAME sentence while it was being edited and `text-text-secondary` the
 * moment it was committed, so text visibly dimmed once it became real.
 *
 * The second problem was flatness: all seven fields shared one size and colour,
 * so the impression -- the conclusion a radiologist looks for first -- was set
 * identically to the disclaimer, which is fixed boilerplate. Hierarchy now
 * follows what the field is FOR:
 *
 *   impression   the conclusion            19px/500, primary   (the `impression-report`
 *                                                              token, defined for exactly
 *                                                              this and never wired up)
 *   disclaimer   fixed legal boilerplate   14px, secondary     (quiet on purpose)
 *   everything   clinical prose            16px/1.6, primary   (the `body-read` token)
 *
 * Absent values are muted rather than set as body text, so "Not provided" does
 * not read as content the report actually contains.
 *
 * The body token is now `body-read` (16px/1.6) rather than `findings`
 * (16px/30px). Two things changed and they are separate: the leading is
 * expressed as a ratio, so it survives a size change instead of silently
 * becoming a different measure; and the SAME token now sets the evidence
 * panel's prose. The panel used to be set in `text-sm` (14px/1.5) -- a whole
 * column of clinical text one step smaller and tighter than the identical
 * kind of text beside it, for no reason a reader could see. One rule for
 * continuous prose, wherever it is rendered, is the point of this file.
 */
export type ReportFieldKey =
  | "examination"
  | "clinical_history"
  | "technique"
  | "findings"
  | "impression"
  | "recommendation"
  | "disclaimer";

const BODY_BY_FIELD: Partial<Record<ReportFieldKey, string>> = {
  impression: "text-impression-report text-text-primary",
  disclaimer: "text-sm leading-relaxed text-text-secondary",
};

const DEFAULT_BODY = "text-body-read text-text-primary";

/** Class for a field's value. `present=false` mutes it (an absent field). */
export function reportBodyClass(field: ReportFieldKey | undefined, present: boolean): string {
  if (!present) return "text-body-read text-text-muted";
  return (field && BODY_BY_FIELD[field]) ?? DEFAULT_BODY;
}

/**
 * The measure for continuous report prose, and the one place it is stated.
 *
 * It was `max-w-[68ch]`, written out by hand in ReportDocumentView and again
 * in EditableReportSection -- an arbitrary Tailwind value in a codebase whose
 * design gate exists to stop exactly that. Now a token (--report-prose, 74ch),
 * which also puts the line length inside the 70–80 character band that makes
 * a long clinical document readable, and applies to the evidence panel too so
 * the two columns are set to one rule rather than two.
 *
 * This is what keeps the report column from stretching its body text edge to
 * edge when the evidence panel docks and the column grows.
 */
export const REPORT_PROSE_MEASURE = "max-w-report-prose";

/**
 * Section heading, as a boxed and filled label rather than a bare line of small
 * caps. Three things changed together and they only work together: the label is
 * 12.5px instead of the 10.5px eyebrow floor, it sits in a bordered chip, and
 * the chip carries a fill. On a seven-section document the unboxed version gave
 * no anchor for the eye to jump between sections -- the labels were smaller and
 * quieter than the text they introduced, which is backwards for something whose
 * whole job is to say where you are.
 *
 * IMPRESSION is the one section that gets the cyan treatment. It is the
 * conclusion, and this app already uses cyan for the thing that matters; making
 * all seven cyan would mark nothing.
 */
export function reportLabelClass(field?: ReportFieldKey): string {
  const base =
    "inline-flex items-center rounded-chip border px-10 py-5 font-mono text-section-label uppercase";
  return field === "impression"
    ? `${base} border-cyan-line bg-cyan-wash text-cyan`
    : `${base} border-strong bg-bg-hover text-text-secondary`;
}
