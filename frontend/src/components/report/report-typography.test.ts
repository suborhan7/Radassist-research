import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { reportBodyClass, REPORT_PROSE_MEASURE } from "./report-typography";

const src = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(/\r\n/g, "\n");

describe("one body rule for continuous report prose", () => {
  it("sets ordinary fields in the shared body token", () => {
    expect(reportBodyClass("findings", true)).toContain("text-body-read");
    expect(reportBodyClass(undefined, true)).toContain("text-body-read");
  });

  it("keeps absent values muted rather than set as body text", () => {
    expect(reportBodyClass("findings", false)).toContain("text-text-muted");
  });

  it("leaves the impression and the disclaimer on their own steps", () => {
    // Hierarchy by what the field is FOR is the point of this file; unifying
    // the body size must not flatten the document back out.
    expect(reportBodyClass("impression", true)).toContain("text-impression-report");
    expect(reportBodyClass("disclaimer", true)).toContain("text-sm");
  });

  it("states the measure once, as a token", () => {
    expect(REPORT_PROSE_MEASURE).toBe("max-w-report-prose");
  });
});

describe("the measure is a token, not an arbitrary value", () => {
  const files = [
    "./report-document-view.tsx",
    "./editable-report-section.tsx",
    "../../app/reports/[reportId]/page.tsx",
  ];

  for (const file of files) {
    it(`${file} carries no hand-written ch measure`, () => {
      // max-w-[68ch] was written out by hand in two components before this.
      // The design gate catches arbitrary padding, not arbitrary widths, so
      // this is the assertion that keeps the measure in tokens.css.
      expect(src(file)).not.toMatch(/max-w-\[\d+(\.\d+)?ch\]/);
    });
  }

  it("defines the measure inside the 70–80 character band", () => {
    const tokens = src("../../styles/tokens.css");
    const match = tokens.match(/--report-prose:\s*(\d+)ch/);
    expect(match, "--report-prose must be defined in tokens.css").not.toBeNull();
    const ch = Number(match![1]);
    expect(ch).toBeGreaterThanOrEqual(70);
    expect(ch).toBeLessThanOrEqual(80);
  });
});

describe("the evidence panel is set like the report column", () => {
  const page = src("../../app/reports/[reportId]/page.tsx");

  // The panel body between the sidebar's opening and closing tags.
  const panel = page.slice(
    page.indexOf("<EvidenceSidebar"),
    page.indexOf("</EvidenceSidebar>"),
  );

  it("is a section of the page that this test actually found", () => {
    expect(panel.length).toBeGreaterThan(500);
  });

  it("sets its prose in the same body token as the report", () => {
    expect(panel).toContain("text-body-read");
  });

  it("carries no panel-specific smaller body size", () => {
    // `text-sm` here was the panel-specific override: a whole column of
    // clinical text one step smaller and tighter than the same kind of text
    // beside it. Mono metric tokens are role-based and shared with the report
    // column, so they are not overrides and are not matched.
    expect(panel).not.toContain("text-sm");
  });

  it("caps its prose at the same measure", () => {
    expect(panel).toContain(REPORT_PROSE_MEASURE);
  });
});

describe("the type floor is respected", () => {
  it("defines the shared body token at 16px, well clear of the 11px floor", () => {
    const config = src("../../../tailwind.config.ts");
    const match = config.match(/"body-read":\s*\["(\d+)px"[^\]]*lineHeight:\s*"([\d.]+)"/);
    expect(match, "body-read must be defined in tailwind.config.ts").not.toBeNull();
    expect(Number(match![1])).toBeGreaterThanOrEqual(11);
    expect(Number(match![1])).toBe(16);
    // "Body text: line-height about 1.6."
    expect(Number(match![2])).toBeCloseTo(1.6, 2);
  });
});
