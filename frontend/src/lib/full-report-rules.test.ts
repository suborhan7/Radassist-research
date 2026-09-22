import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { shouldForceFullReport, fullReportForcedReasonKey } from "./full-report-rules";

const NONE = { editing: false, regenerating: false, finalizing: false, printing: false };

describe("shouldForceFullReport", () => {
  it("leaves the disclosure under the doctor's control when nothing is happening", () => {
    expect(shouldForceFullReport(NONE)).toBe(false);
  });

  for (const key of ["editing", "regenerating", "finalizing", "printing"] as const) {
    it(`holds the full report open while ${key}`, () => {
      expect(shouldForceFullReport({ ...NONE, [key]: true })).toBe(true);
    });
  }
});

describe("fullReportForcedReasonKey", () => {
  it("names the outermost mode when several are true at once", () => {
    // Printing and finalizing are whole-screen modes that subsume an open
    // editor, so they are the true explanation when they coincide with one.
    expect(fullReportForcedReasonKey({ ...NONE, editing: true, printing: true })).toBe(
      "workspace.fullReportHeldPrint",
    );
    expect(fullReportForcedReasonKey({ ...NONE, editing: true, finalizing: true })).toBe(
      "workspace.fullReportHeldFinalize",
    );
    expect(fullReportForcedReasonKey({ ...NONE, editing: true, regenerating: true })).toBe(
      "workspace.fullReportHeldRegen",
    );
    expect(fullReportForcedReasonKey({ ...NONE, editing: true })).toBe(
      "workspace.fullReportHeldEdit",
    );
  });

  it("returns a key the dictionaries actually define", () => {
    const src = fileURLToPath(new URL("../..", import.meta.url));
    const en = readFileSync(`${src}/src/lib/i18n/dictionaries/en.ts`, "utf-8");
    for (const flag of ["printing", "finalizing", "regenerating", "editing"] as const) {
      const key = fullReportForcedReasonKey({ ...NONE, [flag]: true });
      expect(en).toContain(`"${key}"`);
    }
  });
});

/**
 * The summary-first rule is a layout invariant, and layout invariants rot
 * quietly. Mounting the route to assert it would need a router, an API client
 * and a session; this reads the source instead, which is the same approach
 * report-document-view.test.ts already uses in this codebase for the same
 * reason.
 *
 * What it locks in is the one thing a doctor's safety depends on here: the
 * impression, the recommendation, the validation warnings and the consistency
 * verdict are rendered OUTSIDE the disclosure, so no state of the UI can hide
 * them behind a control.
 */
describe("the workspace keeps conclusions and alerts out of the disclosure", () => {
  // Normalised to LF: the working tree is CRLF on Windows, and an assertion
  // that silently depends on the checkout's line endings is not an assertion.
  const page = readFileSync(
    fileURLToPath(new URL("../app/reports/[reportId]/page.tsx", import.meta.url)),
    "utf-8",
  ).replace(/\r\n/g, "\n");

  const at = (needle: string) => {
    const i = page.indexOf(needle);
    expect(i, `expected to find ${needle} in page.tsx`).toBeGreaterThan(-1);
    return i;
  };

  it("splits the canonical 7 fields rather than restating them", () => {
    // A field added to REPORT_CONTENT_FIELDS must land somewhere by itself.
    expect(page).toContain("CONTENT_FIELDS.filter((f) => SUMMARY_KEY_SET.has(f.key))");
    expect(page).toContain("CONTENT_FIELDS.filter((f) => !SUMMARY_KEY_SET.has(f.key))");
  });

  it("puts only impression and recommendation in the summary", () => {
    expect(page).toContain('const SUMMARY_KEYS = ["impression", "recommendation"]');
  });

  it("renders the summary, the warnings and the consistency verdict before the disclosure", () => {
    const disclosure = at("<FullReportDisclosure");
    expect(at("SUMMARY_FIELDS.map")).toBeLessThan(disclosure);
    expect(at("report.validation.is_clean")).toBeLessThan(disclosure);
    expect(at("<ConsistencyState")).toBeLessThan(disclosure);
  });

  it("renders the remaining sections inside the disclosure", () => {
    // The exact render call, not just the name: FULL_REPORT_FIELDS is also
    // mapped earlier to build the "what is inside" hint, and matching that
    // occurrence would make this assertion pass while proving nothing.
    const render = at("{FULL_REPORT_FIELDS.map(({ key }) => renderSection(key))}");
    expect(render).toBeGreaterThan(at("<FullReportDisclosure"));
    expect(render).toBeLessThan(at("</FullReportDisclosure>"));
  });

  it("wires the force rule rather than rebuilding it inline", () => {
    expect(page).toContain("shouldForceFullReport(forceState)");
    expect(page).toContain("fullReportForcedReasonKey(forceState)");
    // The stored choice must never be able to close a forced-open report.
    expect(page).toContain("fullReportChoice || forceFullReport");
  });

  it("scopes the panel preference to the signed-in doctor", () => {
    // Scoped, so two doctors at one workstation do not inherit each other's
    // layout -- the whole reason the hook takes a scope at all.
    expect(page).toContain("usePersistedToggle(\n    currentDoctorId,\n    FULL_REPORT_PREF,");
  });
});
