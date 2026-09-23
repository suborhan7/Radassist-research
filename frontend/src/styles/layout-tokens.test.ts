import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The reading station has to FIT the frame it declares.
 *
 * It did not. `--rail` 224 + an inline `min-w-[360px]` film + `--report-col`
 * 530 + `--evidence-panel` 340 came to 1454px inside a frame tokens.css calls
 * "fixed 1440x900", so the rightmost 14px sat off screen. The thing living in
 * those 14px was the evidence panel's collapse control, which is how the one
 * affordance for putting that panel away came to be reported as missing.
 *
 * The invariant is unchanged in substance and restated in form. The evidence
 * panel is now its own full-width route rather than a fourth column, so the
 * station is three columns and the sum has slack: the assertion is that it
 * FITS 1440, not that it equals it. Asserting equality against a station that
 * no longer has a fixed fourth column would be asserting a coincidence.
 *
 * Nothing in the type system or the design gate can catch this: every value
 * involved is individually fine, and the defect is in their sum.
 */
const tokens = readFileSync(
  fileURLToPath(new URL("./tokens.css", import.meta.url)),
  "utf-8",
).replace(/\r\n/g, "\n");

function px(name: string): number {
  const m = tokens.match(new RegExp(`--${name}:\\s*(\\d+)px`));
  expect(m, `--${name} must be defined in tokens.css as a px value`).not.toBeNull();
  return Number(m![1]);
}

describe("the reading station fits the frame it declares", () => {
  it("fits the report route's three columns inside 1440", () => {
    const total = px("rail") + px("film-min") + px("report-col");
    expect(total).toBeLessThanOrEqual(1440);
  });

  it("leaves the film the largest share of what is left", () => {
    // The film is flex-1, so it takes the slack. This pins the intent that the
    // radiograph -- not the prose column -- is what grows on a wider monitor.
    const slack = 1440 - (px("rail") + px("film-min") + px("report-col"));
    expect(slack).toBeGreaterThan(0);
  });

  it("keeps the film floor as a token, not an arbitrary value in the page", () => {
    const page = readFileSync(
      fileURLToPath(new URL("../app/workspace/[reportId]/report/page.tsx", import.meta.url)),
      "utf-8",
    );
    expect(page).toContain("min-w-film");
    expect(page).not.toMatch(/min-w-\[\d+px\]/);
  });

  it("has no width token left over from the docked evidence sidebar", () => {
    // The sidebar became a route. Its widths would otherwise sit in tokens.css
    // forever, described as belonging to a panel that no longer exists.
    //
    // DECLARATIONS, not bare words: the comment above --film-min explains the
    // station's history and names the retired tokens to do it. Naming them
    // there is the documentation; declaring them is the thing to catch.
    for (const dead of ["evidence-panel", "evidence-rail", "report-col-wide"]) {
      expect(tokens, `--${dead} should no longer be declared`).not.toMatch(
        new RegExp(`--${dead}:\\s*\\S`),
      );
    }
  });
});
