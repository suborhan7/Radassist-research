/**
 * When the "Full report" disclosure is held open and cannot be collapsed.
 *
 * Extracted from the workspace route so it is a function with a name and a
 * test, rather than a boolean expression inline in JSX. The rule is a safety
 * rule, not a styling one -- each of the four cases is a state in which
 * collapsing would hide something the doctor is actively working on or is
 * about to put their name to -- and a safety rule that exists only as an
 * `a || b || c || d` inside a render is one nobody can point at.
 *
 * It also cannot be tested where it was. `page.tsx` is a route module that
 * pulls in next/navigation and the API client on import; a test for "does
 * editing hold the report open" should not need a router.
 */
export interface FullReportForceState {
  /** At least one section has its editor open. */
  editing: boolean;
  /** A regeneration is in flight, or a candidate is waiting on Accept/Discard. */
  regenerating: boolean;
  /** The finalize preview is open. */
  finalizing: boolean;
  /** The browser is printing (there is no separate in-app PDF view). */
  printing: boolean;
}

/**
 * True when the disclosure must be open and its control disabled.
 *
 *   editing        a live textarea must not be hidden mid-edit, and the
 *                  section being edited may be one inside the disclosure.
 *   regenerating   an un-accepted candidate that cannot be seen cannot be
 *                  judged, and Accept/Discard live next to it.
 *   finalizing     the doctor is about to sign; the document they sign is the
 *                  whole document.
 *   printing       paper must carry every section, or the printout is a
 *                  clinical document that misrepresents itself.
 */
export function shouldForceFullReport(state: FullReportForceState): boolean {
  return state.editing || state.regenerating || state.finalizing || state.printing;
}

/**
 * Which reason to show beside the disabled control.
 *
 * Ordered most-specific-first rather than by the order of the fields: printing
 * and finalizing are whole-screen modes that subsume an open editor, so when
 * several are true at once the outermost one is the true explanation. Returns
 * the edit reason when nothing is forcing, since callers only read this while
 * `shouldForceFullReport` is true.
 */
export function fullReportForcedReasonKey(state: FullReportForceState): string {
  if (state.printing) return "workspace.fullReportHeldPrint";
  if (state.finalizing) return "workspace.fullReportHeldFinalize";
  if (state.regenerating) return "workspace.fullReportHeldRegen";
  return "workspace.fullReportHeldEdit";
}
