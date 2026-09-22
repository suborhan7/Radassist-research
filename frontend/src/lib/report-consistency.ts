/**
 * Presentation logic for the Phase 22 v1.2 consistency block.
 *
 * THE CONTRACT THIS IMPLEMENTS, quoted from
 * docs/phase22/fix_architecture_v1.2_FROZEN.md §3.4 (binding UI requirement):
 *
 *   "For any report with `language != "en"`, the UI must display
 *    'consistency checks not run' and must never display a clean or passed
 *    state for the consistency block. [...] The two must not share a
 *    component, an icon, or a colour. A Bengali report showing a green tick --
 *    or showing nothing at all, which a clinician reads as 'nothing wrong' --
 *    would convert an acknowledged coverage gap into an affirmative false
 *    assurance, which is worse than the gap itself."
 *
 * and from docs/phase22/amendment_01_consistency_status.md §2(a)/§2(e):
 *
 *   "`partial` must not be rendered as a pass. It is closer to `not_run` than
 *    to `clean` in what it licenses a reader to conclude."
 *   "Until Gate B calibrates the transplant threshold, every English report
 *    reads `partial`."
 *
 * THIS MODULE DERIVES NOTHING. `status` is read straight off the response.
 * The backend derives it in exactly one place
 * (app/api/consistency_status.derive_consistency_status) precisely so two
 * copies cannot disagree, and the direction they would disagree in is the
 * dangerous one -- a client rendering "not assessed" as a pass. The same
 * discipline RetrievalSupportNotice follows for retrieval support (S9), for
 * the same reason.
 *
 * What it DOES compute is the missing-check list, which the amendment
 * explicitly asks clients to show:
 *
 *   "The API additionally surfaces `applicable_checks` beside `checks_run`, so
 *    a client can show WHICH checks are missing by name, not merely that some
 *    are. A status word cannot carry that, and making incompleteness visible
 *    is the point."
 *
 * That is a set difference over two lists the backend sent, not a second
 * opinion about the verdict.
 */

/** The four states, exactly as `derive_consistency_status` emits them. */
export type ConsistencyStatus = "not_run" | "partial" | "clean" | "violations";

const STATUSES: readonly string[] = ["not_run", "partial", "clean", "violations"];

/** The structural shape this module needs. Matches ConsistencyResponse. */
export interface ConsistencyBlock {
  status?: string | null;
  checks_run?: string[] | null;
  applicable_checks?: string[] | null;
  violations?: { check: string; severity: string; field: string; detail: string }[] | null;
  retry_count?: number | null;
}

/**
 * Read the status, defaulting to "not_run".
 *
 * Every unknown input resolves to "not_run", never to "clean": a missing
 * block (a response from a backend older than v1.2, or a field the generated
 * types have not caught up with) means nothing is known about this report's
 * consistency, and the frozen rule is that nothing-known never renders as
 * assurance. This mirrors the backend's own `_not_run_consistency()` default,
 * which exists so "a caller that forgets to populate it then under-claims
 * rather than over-claims".
 */
export function consistencyStatusOf(block: ConsistencyBlock | null | undefined): ConsistencyStatus {
  const raw = block?.status;
  return typeof raw === "string" && STATUSES.includes(raw) ? (raw as ConsistencyStatus) : "not_run";
}

/**
 * The applicable checks this report did NOT get, by name.
 *
 * Empty for a Bengali report -- its applicable set is empty (§3.4: the checks
 * are English-only), so there is no list of "missing" checks to show. The
 * reason a Bengali report has no checks is carried by the status copy itself,
 * not by this list.
 */
export function missingChecks(block: ConsistencyBlock | null | undefined): string[] {
  const applicable = block?.applicable_checks ?? [];
  const run = new Set(block?.checks_run ?? []);
  return applicable.filter((check) => !run.has(check));
}

/**
 * Whether this status licenses a reader to conclude the report was checked
 * and found sound. True for exactly one of the four.
 *
 * Exported so the "not_run never renders as a pass" rule is a named,
 * testable predicate rather than a condition spelled out at each call site
 * and liable to drift at one of them.
 */
export function isPass(status: ConsistencyStatus): boolean {
  return status === "clean";
}
