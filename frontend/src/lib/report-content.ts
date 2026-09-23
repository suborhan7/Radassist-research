/**
 * Whether a report has enough in it to be worth putting on paper.
 *
 * The print control is gated on this rather than being always-on, because a
 * report whose narrative fields are all empty prints as a letterhead, a
 * disclaimer and nothing else -- a document that looks official and says
 * nothing, which is worse than no document.
 *
 * WHAT COUNTS. Only the five narrative fields. `examination` is exam-type
 * metadata the system sets, and `disclaimer` is fixed boilerplate present on
 * every report ever generated -- if either counted, the predicate would be
 * true for every row and would gate nothing at all.
 *
 * The list is restated here rather than imported because the canonical copy
 * (EDITABLE_REPORT_FIELDS) lives in the workspace route module, which pulls in
 * next/navigation and the API client on import and cannot be loaded by a plain
 * node test. `report-content.test.ts` reads that module as TEXT and asserts
 * the two lists agree, which is the same drift-guard this codebase already
 * uses for the 7-field label list.
 */
export const NARRATIVE_FIELDS = [
  "clinical_history",
  "technique",
  "findings",
  "impression",
  "recommendation",
] as const;

export type NarrativeField = (typeof NARRATIVE_FIELDS)[number];

/** True when at least one narrative field carries non-whitespace text. */
export function hasReportContent(
  content: Partial<Record<string, string | null | undefined>> | null | undefined,
): boolean {
  if (!content) return false;
  return NARRATIVE_FIELDS.some((field) => (content[field] ?? "").trim().length > 0);
}
