import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { hasReportContent, NARRATIVE_FIELDS } from "./report-content";

const src = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(/\r\n/g, "\n");

const FULL = {
  examination: "Chest X-ray",
  clinical_history: "Cough",
  technique: "PA",
  findings: "Opacities",
  impression: "Pneumonia",
  recommendation: "Follow up",
  disclaimer: "AI generated, requires review.",
};

describe("hasReportContent", () => {
  it("is true for a report with narrative", () => {
    expect(hasReportContent(FULL)).toBe(true);
  });

  it("is true when only one narrative field is filled", () => {
    expect(hasReportContent({ findings: "Opacities" })).toBe(true);
  });

  it("is FALSE for boilerplate alone", () => {
    // The case the print control exists to block: examination is exam-type
    // metadata the system sets and disclaimer is on every report ever
    // generated, so a page built from those two is a letterhead that says
    // nothing. If either counted, this predicate would gate nothing.
    expect(hasReportContent({ examination: "Chest X-ray", disclaimer: "AI generated." })).toBe(false);
  });

  it("treats whitespace as empty", () => {
    expect(hasReportContent({ findings: "   \n  " })).toBe(false);
  });

  it("survives a missing or partial content object", () => {
    expect(hasReportContent(null)).toBe(false);
    expect(hasReportContent(undefined)).toBe(false);
    expect(hasReportContent({})).toBe(false);
    expect(hasReportContent({ findings: null })).toBe(false);
  });
});

describe("the narrative field list does not drift from the canonical one", () => {
  it("matches EDITABLE_REPORT_FIELDS in the workspace route", () => {
    // The canonical copy lives in a route module that pulls next/navigation on
    // import and cannot be loaded here, so it is read as text -- the same
    // approach report-document-view.test.ts already uses for the 7-field list.
    const page = src("../app/reports/[reportId]/page.tsx");
    const block = page.slice(
      page.indexOf("export const EDITABLE_REPORT_FIELDS = ["),
      page.indexOf("] as const satisfies readonly ReportContentKey[]"),
    );
    expect(block.length, "EDITABLE_REPORT_FIELDS not found in page.tsx").toBeGreaterThan(0);

    const canonical = [...block.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
    expect(canonical).toEqual([...NARRATIVE_FIELDS]);
  });
});

describe("the print control is honest about what it is", () => {
  const page = src("../app/reports/[reportId]/page.tsx");
  const en = src("./i18n/dictionaries/en.ts");

  it("is gated on there being something to print", () => {
    expect(page).toContain("disabled={!hasReportContent(report.content)}");
  });

  it("calls the browser's own print, not a server endpoint", () => {
    expect(page).toContain("onClick={() => window.print()}");
    // No fetch, no download URL, nothing that would imply a generated file.
    expect(page).not.toMatch(/\/reports\/[^"'`]*\/pdf/);
  });

  it("says browser in the tooltip and never claims to generate a PDF", () => {
    expect(en).toContain('"workspace.downloadPdfTitle": "Print / Save as PDF (browser)"');
    expect(en).toContain('"workspace.downloadPdf": "Print / Save as PDF"');
    // The old copy promised a download and called the feature out of scope.
    expect(en).not.toContain('"workspace.downloadPdf": "Download PDF"');
  });
});

describe("the print stylesheet hides the application and shows the document", () => {
  const css = src("../app/globals.css");
  const printBlock = css.slice(css.indexOf("@media print"));

  it("has a print block at all", () => {
    expect(printBlock.length).toBeGreaterThan(500);
  });

  it("hides every sibling of the print document -- rail, panels, buttons, toggles", () => {
    // One rule covers all UI chrome because the document is a body-level
    // sibling of the app, so nothing has to opt out of printing individually.
    expect(printBlock).toContain("body > *:not(.rr-print-root)");
    expect(printBlock).toContain("display: none !important");
  });

  it("prints on paper colours regardless of the active theme", () => {
    expect(printBlock).toContain("var(--print-paper)");
    expect(printBlock).toContain("var(--print-ink)");
    // The screen palette must not leak onto the page.
    expect(printBlock).not.toContain("var(--bg-app)");
    expect(printBlock).not.toContain("var(--text-primary)");
  });

  it("undoes the reading station's fixed height so pages two and beyond exist", () => {
    expect(printBlock).toMatch(/height:\s*auto\s*!important/);
    expect(printBlock).toMatch(/overflow:\s*visible\s*!important/);
  });

  it("sets A4 and keeps a heading from stranding at the foot of a page", () => {
    expect(printBlock).toMatch(/@page\s*\{[^}]*size:\s*A4/);
    expect(printBlock).toContain("break-after: avoid");
    expect(printBlock).toContain("page-break-after: avoid");
  });

  it("keeps the print document hidden on screen", () => {
    // Defined outside the media query, so it never shows in the workspace.
    const beforePrint = css.slice(0, css.indexOf("@media print"));
    expect(beforePrint).toMatch(/\.rr-print-root\s*\{\s*display:\s*none;/);
  });
});
