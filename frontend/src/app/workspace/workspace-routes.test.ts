import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The route shape of the workspace.
 *
 * These are source assertions rather than mounted routes, for the reason the
 * rest of this suite already gives: a route module pulls in next/navigation and
 * the API client on import, and nothing here mounts one. What can be asserted
 * without a router is the structure the guarantees rest on -- that all three
 * pages exist, that each reads the shared state instead of fetching its own,
 * and that the old URL still resolves.
 */
const src = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(/\r\n/g, "\n");
const has = (rel: string) => existsSync(fileURLToPath(new URL(rel, import.meta.url)));

describe("the three pages exist", () => {
  for (const [name, rel] of [
    ["layout", "./[reportId]/layout.tsx"],
    ["index (redirects to report)", "./[reportId]/page.tsx"],
    ["report", "./[reportId]/report/page.tsx"],
    ["evidence", "./[reportId]/evidence/page.tsx"],
  ] as const) {
    it(`has a ${name} route`, () => {
      expect(has(rel), `${rel} should exist`).toBe(true);
    });
  }

  it("sends the bare workspace URL to the report", () => {
    const index = src("./[reportId]/page.tsx");
    expect(index).toContain("redirect(");
    expect(index).toContain("/report");
  });
});

describe("deep links load real state, not a blank page", () => {
  const layout = src("./[reportId]/layout.tsx");

  it("wraps every child route in the provider that owns the report", () => {
    // Whichever of the three URLs is opened cold, the layout mounts first and
    // fetches, so no page can render against nothing.
    expect(layout).toContain("<WorkspaceProvider");
    expect(layout).toContain("params.reportId");
  });

  it("renders loading and error states rather than an empty frame", () => {
    expect(layout).toContain("workspace.loading");
    expect(layout).toMatch(/if\s*\(\s*error\s*\)/);
    expect(layout).toMatch(/if\s*\(\s*!report\s*\)/);
  });

  for (const [name, rel] of [
    ["report", "./[reportId]/report/page.tsx"],
    ["evidence", "./[reportId]/evidence/page.tsx"],
  ] as const) {
    it(`the ${name} page reads shared state and fetches nothing itself`, () => {
      const page = src(rel);
      expect(page).toContain("useWorkspace()");
      // The whole no-refetch guarantee is that these never call the loaders.
      for (const loader of ["getReport(", "getPatient(", "getCurrentDoctor(", "useEffect("]) {
        expect(page, `${rel} should not call ${loader}`).not.toContain(loader);
      }
    });
  }
});

describe("the old workspace URL still resolves", () => {
  // /reports/{id} appears in screenshots taken against dev.db, in working
  // notes and possibly in the thesis draft. A 404 on a URL printed in a thesis
  // is not a broken link, it is a broken citation.
  const config = readFileSync(
    fileURLToPath(new URL("../../../next.config.ts", import.meta.url)),
    "utf-8",
  ).replace(/\r\n/g, "\n");

  it("redirects /reports/:id to the report page, permanently", () => {
    expect(config).toContain("async redirects()");
    expect(config).toContain('source: "/reports/:reportId"');
    expect(config).toContain('destination: "/workspace/:reportId/report"');
    expect(config).toContain("permanent: true");
  });

  it("does not swallow the explain and compare routes", () => {
    // Those are still /reports/{id}/... and must keep matching, so the source
    // has to be the bare segment with nothing after it.
    expect(config).not.toContain('source: "/reports/:reportId/:path*"');
    expect(has("../reports/[reportId]/explain/page.tsx")).toBe(true);
    expect(has("../reports/[reportId]/compare/page.tsx")).toBe(true);
  });
});

describe("the report page keeps alerts out of any disclosure", () => {
  const page = src("./[reportId]/report/page.tsx");

  it("renders the validation and consistency blocks outside FullReportDisclosure", () => {
    // Ordering is asserted in full-report-rules.test.ts; this asserts the
    // stronger structural fact that neither block is among the disclosure's
    // children, in ANY consistency state -- there is no branch that could put
    // them there, because they are not inside those tags at all.
    const open = page.indexOf("<FullReportDisclosure");
    const close = page.indexOf("</FullReportDisclosure>");
    expect(open).toBeGreaterThan(-1);
    const inside = page.slice(open, close);
    expect(inside).not.toContain("<ConsistencyState");
    expect(inside).not.toContain("report.validation");
  });

  it("passes the report's own consistency block through unmodified", () => {
    // All four states are covered by consistency-state.test.tsx; what matters
    // here is that the page hands it the real value rather than deciding
    // anything about it.
    expect(page).toContain("block={report.consistency}");
    expect(page).toContain("language={report.language}");
  });

  it("still offers every action the single screen had", () => {
    for (const key of [
      "workspace.viewEvidence",
      "workspace.explainReport",
      "workspace.comparePrevious",
      "workspace.downloadPdf",
      "workspace.finalize",
      "workspace.restoreDraft",
      "workspace.draftedFrom",
      "workspace.phiMasked",
    ]) {
      expect(page, `report page should still offer ${key}`).toContain(key);
    }
  });
});
