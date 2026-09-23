import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The three-column reading station has to ADD UP to the frame it declares.
 *
 * It did not. `--rail` 224 + an inline `min-w-[360px]` film + `--report-col`
 * 530 + `--evidence-panel` 340 came to 1454px inside a frame tokens.css calls
 * "fixed 1440x900", so the rightmost 14px sat off screen. The thing living in
 * those 14px was the evidence panel's collapse control, which is how the one
 * affordance for putting that panel away came to be reported as missing.
 *
 * Nothing in the type system or the design gate can catch that: every value
 * involved was individually fine, and the defect was in their sum. So the sum
 * is asserted here, and the film floor is a token rather than an arbitrary
 * value written into the page.
 *
 * The horizontal scroll below this width is deliberate and stays -- the
 * station may be wider than a small monitor. What must not happen is the
 * station being wider than its OWN declared width.
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
  it("sums the four columns to exactly 1440", () => {
    const total = px("rail") + px("film-min") + px("report-col") + px("evidence-panel");
    expect(total).toBe(1440);
  });

  it("still fits once the evidence panel docks to its rail", () => {
    // Collapsed, the report column grows and the panel shrinks; the station
    // must not overflow in that state either.
    const total = px("rail") + px("film-min") + px("report-col-wide") + px("evidence-rail");
    expect(total).toBeLessThanOrEqual(1440);
  });

  it("keeps the film floor as a token, not an arbitrary value in the page", () => {
    const page = readFileSync(
      fileURLToPath(new URL("../app/reports/[reportId]/page.tsx", import.meta.url)),
      "utf-8",
    );
    expect(page).toContain("min-w-film");
    expect(page).not.toMatch(/min-w-\[\d+px\]/);
  });
});
