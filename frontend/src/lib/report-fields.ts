import {
  REPORT_CONTENT_FIELDS as CONTENT_FIELDS,
} from "@/components/report/report-document-view";
import type { paths } from "@/lib/generated/api";

/**
 * The report's field vocabulary: which of the canonical seven are editable,
 * which lead the summary, and which sit behind the full-report disclosure.
 *
 * WHY THIS IS A LIBRARY MODULE AND NOT PART OF THE ROUTE. These constants used
 * to live in `app/reports/[reportId]/page.tsx`, and `lib/report-diff.ts` --
 * production code, not a test -- imported them from there. A library reaching
 * up into a route module is backwards, and it had a visible cost: two test
 * files could not import what they wanted to assert on, because loading that
 * module pulls in next/navigation and the API client, so they read the route
 * file as TEXT and matched substrings instead. Moving the constants here means
 * those tests import the real values and compare them directly.
 *
 * Nothing in this file imports from `next/*`, which is the property that makes
 * it loadable from a plain node-environment test.
 */

type ReportDetailResponse =
  paths["/reports/{report_id}"]["get"]["responses"][200]["content"]["application/json"];

export type ReportContentKey = keyof ReportDetailResponse["content"];

/**
 * Phase 17 Step 7 / Phase 18 Decision 9: the single canonical list of the
 * 5 user-editable report sections -- examination/disclaimer stay AI-set/
 * read-only (exam-type metadata vs. free clinical narrative; fixed
 * compliance statement) and are deliberately excluded. Exported so Phase
 * 18's diff/section-counter/percentage logic imports this exact list
 * rather than redeclaring it -- found duplicated (this Set plus a second,
 * independent hardcoded object literal in handleRestoreAiDraft()) before
 * that consolidation, not actually centralized despite there being only
 * one file involved.
 */
export const EDITABLE_REPORT_FIELDS = [
  "clinical_history",
  "technique",
  "findings",
  "impression",
  "recommendation",
] as const satisfies readonly ReportContentKey[];

export type EditableReportField = (typeof EDITABLE_REPORT_FIELDS)[number];

export const EDITABLE_KEYS = new Set<ReportContentKey>(EDITABLE_REPORT_FIELDS);

/**
 * The summary-first split of the canonical 7-field document.
 *
 * SUMMARY_FIELDS are what a radiologist opening the report must see without
 * doing anything: the conclusion and what to do about it. They are rendered
 * outside the disclosure and there is no state in which they are hidden.
 *
 * FULL_REPORT_FIELDS are the rest -- what the examination was, what the
 * patient brought to it, how it was acquired, what was seen, and the fixed
 * legal boilerplate. Context, consulted on purpose rather than read every
 * time.
 *
 * Derived from CONTENT_FIELDS by partition rather than restated, so the
 * canonical list stays the single source of the 7 fields and their order: a
 * field added there lands in the full report automatically instead of
 * silently appearing in neither half. The summary keys are the declaration;
 * everything else follows.
 */
export const SUMMARY_KEYS = [
  "impression",
  "recommendation",
] as const satisfies readonly ReportContentKey[];

const SUMMARY_KEY_SET = new Set<ReportContentKey>(SUMMARY_KEYS);

export const SUMMARY_FIELDS = CONTENT_FIELDS.filter((f) => SUMMARY_KEY_SET.has(f.key)).sort(
  // Impression before recommendation: the finding, then what follows from it.
  (a, b) =>
    SUMMARY_KEYS.indexOf(a.key as (typeof SUMMARY_KEYS)[number]) -
    SUMMARY_KEYS.indexOf(b.key as (typeof SUMMARY_KEYS)[number]),
);

export const FULL_REPORT_FIELDS = CONTENT_FIELDS.filter((f) => !SUMMARY_KEY_SET.has(f.key));

/** localStorage name (namespaced and scoped to the doctor by the hook). */
export const FULL_REPORT_PREF = "workspace.fullReport";
