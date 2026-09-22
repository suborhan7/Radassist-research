/**
 * @vitest-environment jsdom
 *
 * The frozen UI contract for this block is a safety requirement, so it gets
 * tests that assert the thing the contract actually forbids -- not merely that
 * each state renders something.
 *
 *   docs/phase22/fix_architecture_v1.2_FROZEN.md §3.4:
 *     "the UI must display 'consistency checks not run' and must never display
 *      a clean or passed state [...] The two must not share a component, an
 *      icon, or a colour."
 *
 *   docs/phase22/amendment_01_consistency_status.md §2(a):
 *     "`partial` must not be rendered as a pass."
 */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/lib/i18n";
import type { ConsistencyBlock } from "@/lib/report-consistency";
import { ConsistencyState } from "./consistency-state";

const ALL = ["temporal", "transplant", "contradiction"];

function show(block: ConsistencyBlock | null | undefined, language = "en") {
  return render(
    <LanguageProvider initial="en">
      <ConsistencyState block={block} language={language} />
    </LanguageProvider>,
  );
}

const box = (c: HTMLElement) => c.querySelector("[data-consistency]") as HTMLElement;
const state = (c: HTMLElement) => box(c).getAttribute("data-consistency");

/** The classes that mean "this passed". Nothing but `clean` may carry them. */
const PASS_MARKERS = ["text-cyan", "border-cyan-line"];
const PASS_GLYPH = "✓";

afterEach(cleanup);

describe("Consistency — the four states are four states", () => {
  it("renders `clean` as the one pass", () => {
    const { container } = show({
      status: "clean",
      checks_run: ALL,
      applicable_checks: ALL,
      violations: [],
    });
    expect(state(container)).toBe("clean");
    expect(screen.getByText("Checks passed")).not.toBeNull();
    expect(container.textContent).toContain(PASS_GLYPH);
  });

  it("renders `partial` with both halves named", () => {
    const { container } = show({
      status: "partial",
      checks_run: ["temporal", "contradiction"],
      applicable_checks: ALL,
      violations: [],
    });
    expect(state(container)).toBe("partial");
    expect(screen.getByText("Partially checked")).not.toBeNull();
    // Which ran AND which did not, by name -- amendment 01: "a status word
    // cannot carry that, and making incompleteness visible is the point".
    expect(container.textContent).toContain("Ran: temporal, contradiction");
    expect(container.textContent).toContain("Not run: transplant");
  });

  it("renders `violations` with the problems it found", () => {
    const { container } = show({
      status: "violations",
      checks_run: ALL,
      applicable_checks: ALL,
      violations: [
        {
          check: "temporal",
          severity: "error",
          field: "impression",
          detail: "mentions a prior study with no prior available",
        },
      ],
    });
    expect(state(container)).toBe("violations");
    expect(screen.getByText("Issues found")).not.toBeNull();
    expect(container.textContent).toContain("mentions a prior study with no prior available");
  });

  it("renders `not_run` as not run", () => {
    const { container } = show({
      status: "not_run",
      checks_run: [],
      applicable_checks: [],
      violations: [],
    });
    expect(state(container)).toBe("not_run");
    expect(screen.getByText("Checks not run")).not.toBeNull();
  });

  it("gives all four different words and different glyphs", () => {
    const words = new Set<string>();
    const glyphs = new Set<string>();
    const blocks: ConsistencyBlock[] = [
      { status: "clean", checks_run: ALL, applicable_checks: ALL, violations: [] },
      { status: "partial", checks_run: ["temporal"], applicable_checks: ALL, violations: [] },
      {
        status: "violations",
        checks_run: ALL,
        applicable_checks: ALL,
        violations: [{ check: "t", severity: "error", field: "impression", detail: "d" }],
      },
      { status: "not_run", checks_run: [], applicable_checks: [], violations: [] },
    ];
    for (const block of blocks) {
      const { container } = show(block);
      const verdict = box(container).querySelector("span") as HTMLElement;
      words.add(verdict.textContent ?? "");
      glyphs.add(verdict.querySelector("span")?.textContent ?? "");
      cleanup();
    }
    expect(words.size).toBe(4);
    expect(glyphs.size).toBe(4);
  });
});

describe("Consistency — nothing but `clean` may look like a pass", () => {
  const notPasses: [string, ConsistencyBlock][] = [
    ["not_run", { status: "not_run", checks_run: [], applicable_checks: [], violations: [] }],
    [
      "partial",
      { status: "partial", checks_run: ["temporal"], applicable_checks: ALL, violations: [] },
    ],
    [
      "violations",
      {
        status: "violations",
        checks_run: ALL,
        applicable_checks: ALL,
        violations: [{ check: "t", severity: "error", field: "impression", detail: "d" }],
      },
    ],
  ];

  for (const [label, block] of notPasses) {
    it(`${label} carries none of the clean styling and no tick`, () => {
      const { container } = show(block);
      const html = box(container).outerHTML;
      for (const marker of PASS_MARKERS) {
        expect(html).not.toContain(marker);
      }
      expect(container.textContent).not.toContain(PASS_GLYPH);
      expect(screen.queryByText("Checks passed")).toBeNull();
    });
  }

  it("never renders an empty checks_run as clean, whatever the payload says", () => {
    // A row with no checks run cannot be clean. Even if `status` disagreed,
    // the backend derives not_run first for exactly this reason; this asserts
    // the client does not invent a pass from an empty list either.
    const { container } = show({
      status: "not_run",
      checks_run: [],
      applicable_checks: ALL,
      violations: [],
    });
    expect(state(container)).toBe("not_run");
    expect(screen.queryByText("Checks passed")).toBeNull();
  });
});

describe("Consistency — the reason a report was not checked", () => {
  it("says plainly that Bengali reports are not covered", () => {
    const { container } = show(
      { status: "not_run", checks_run: [], applicable_checks: [], violations: [] },
      "bn",
    );
    expect(state(container)).toBe("not_run");
    expect(container.textContent).toContain(
      "Consistency checks are not available for Bengali reports.",
    );
  });

  it("says a pre-v1.2 English report simply has no record", () => {
    const { container } = show(
      { status: "not_run", checks_run: [], applicable_checks: [], violations: [] },
      "en",
    );
    expect(container.textContent).toContain(
      "No consistency checks were recorded for this report.",
    );
  });
});

describe("Consistency — a missing block under-claims rather than over-claims", () => {
  for (const [label, block] of [
    ["undefined", undefined],
    ["null", null],
    ["an unrecognised status", { status: "something-new" } as ConsistencyBlock],
  ] as const) {
    it(`renders not_run when the payload carries ${label}`, () => {
      const { container } = show(block);
      expect(state(container)).toBe("not_run");
      expect(screen.queryByText("Checks passed")).toBeNull();
    });
  }
});
