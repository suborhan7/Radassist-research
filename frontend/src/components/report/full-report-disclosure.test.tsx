/**
 * @vitest-environment jsdom
 *
 * The DOM environment is requested per-file, not globally: vitest.config.ts
 * keeps `environment: "node"` as the default so the pre-existing node tests
 * (report-document-view, report-diff) run exactly as they did, with no jsdom
 * cost and no behaviour change.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/lib/i18n";
import { usePersistedToggle } from "@/lib/use-persisted-toggle";
import { shouldForceFullReport, type FullReportForceState } from "@/lib/full-report-rules";
import { FullReportDisclosure } from "./full-report-disclosure";

const STORAGE_KEY = "rr:v1:doctor-1:workspace.fullReport";

const NOTHING_FORCING: FullReportForceState = {
  editing: false,
  regenerating: false,
  finalizing: false,
  printing: false,
};

/** Counts mounts, so a remount (and therefore a refetch) is observable. */
let mountCount = 0;
function MountCounter() {
  useEffect(() => {
    mountCount += 1;
  }, []);
  return null;
}

/**
 * Mirrors exactly how the workspace wires these three pieces together --
 * usePersistedToggle for the remembered choice, shouldForceFullReport for the
 * override, and their OR for the resolved state. Testing the disclosure with
 * hand-set props would prove the component renders; this proves the wiring
 * the page actually uses behaves.
 */
function Harness({
  force = NOTHING_FORCING,
  scope = "doctor-1",
}: {
  force?: FullReportForceState;
  scope?: string | null;
}) {
  const [choice, setChoice] = usePersistedToggle(scope, "workspace.fullReport", false);
  const forced = shouldForceFullReport(force);
  return (
    <LanguageProvider initial="en">
      <FullReportDisclosure
        id="full-report"
        open={choice || forced}
        forced={forced}
        forcedReason="held open"
        hint="5 more sections"
        onToggle={() => setChoice(!choice)}
      >
        <MountCounter />
        <h4>Findings</h4>
      </FullReportDisclosure>
    </LanguageProvider>
  );
}

const toggle = () => screen.getByRole("button", { name: /full report/i });
const panel = (c: HTMLElement) => c.querySelector("#full-report") as HTMLElement;

beforeEach(() => {
  window.localStorage.clear();
  mountCount = 0;
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Full report disclosure — default and toggle", () => {
  it("is collapsed by default and offers to show the full report", () => {
    const { container } = render(<Harness />);
    expect(toggle()).toHaveProperty("textContent", expect.stringContaining("Show full report"));
    expect(toggle().getAttribute("aria-expanded")).toBe("false");
    expect(panel(container).hasAttribute("hidden")).toBe(true);
  });

  it("expands on click and collapses again", () => {
    const { container } = render(<Harness />);
    fireEvent.click(toggle());
    expect(toggle().getAttribute("aria-expanded")).toBe("true");
    expect(toggle().textContent).toContain("Hide full report");
    expect(panel(container).hasAttribute("hidden")).toBe(false);

    fireEvent.click(toggle());
    expect(toggle().getAttribute("aria-expanded")).toBe("false");
    expect(panel(container).hasAttribute("hidden")).toBe(true);
  });

  it("names the element it controls, and that element exists", () => {
    const { container } = render(<Harness />);
    const controls = toggle().getAttribute("aria-controls");
    expect(controls).toBe("full-report");
    // aria-controls pointing at an id nothing renders is the usual way this
    // attribute rots, so the target is asserted to exist rather than assumed.
    expect(container.querySelector(`#${controls}`)).not.toBeNull();
  });

  it("is reachable and operable as a real button", () => {
    render(<Harness />);
    // A <button> gets Enter and Space from the platform. Asserting the tag is
    // what proves both keys work; a div with a click handler would pass a
    // fireEvent.click test while failing a keyboard user.
    expect(toggle().tagName).toBe("BUTTON");
    expect(toggle().getAttribute("disabled")).toBeNull();
  });
});

describe("Full report disclosure — collapsed content is hidden from assistive tech", () => {
  it("removes the collapsed sections from the accessibility tree, not just from view", () => {
    render(<Harness />);
    // getByRole consults the accessibility tree and ignores anything inside a
    // [hidden] subtree. A max-height/overflow "collapse" would still expose
    // this heading, which is the bug this asserts against.
    expect(screen.queryByRole("heading", { name: "Findings" })).toBeNull();

    fireEvent.click(toggle());
    expect(screen.queryByRole("heading", { name: "Findings" })).not.toBeNull();
  });
});

describe("Full report disclosure — persistence", () => {
  it("writes the choice to a namespaced, per-doctor localStorage key", () => {
    render(<Harness />);
    fireEvent.click(toggle());
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("true");
  });

  it("survives a reload", () => {
    const first = render(<Harness />);
    fireEvent.click(toggle());
    first.unmount();

    // A fresh mount with nothing carried over in React state is what a reload
    // looks like to this component.
    const { container } = render(<Harness />);
    expect(toggle().getAttribute("aria-expanded")).toBe("true");
    expect(panel(container).hasAttribute("hidden")).toBe(false);
  });

  it("does not leak one doctor's choice to another at the same workstation", () => {
    const first = render(<Harness scope="doctor-1" />);
    fireEvent.click(toggle());
    first.unmount();

    render(<Harness scope="doctor-2" />);
    expect(toggle().getAttribute("aria-expanded")).toBe("false");
  });

  it("falls back to the default, collapsed, when no doctor is known", () => {
    render(<Harness scope={null} />);
    expect(toggle().getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle());
    // Still works for the session, but nothing was written under a shared key.
    expect(toggle().getAttribute("aria-expanded")).toBe("true");
    expect(window.localStorage.length).toBe(0);
  });
});

describe("Full report disclosure — toggling costs nothing", () => {
  it("fires no network request and never unmounts its content", () => {
    render(<Harness />);
    expect(mountCount).toBe(1);

    fireEvent.click(toggle());
    fireEvent.click(toggle());
    fireEvent.click(toggle());

    // No request: collapsing a panel is a viewing preference.
    expect(fetch).not.toHaveBeenCalled();
    // And no remount, which is what would cause a refetch in any child that
    // loads on mount. Both halves matter -- a fetch spy alone would pass even
    // if the subtree were being destroyed and rebuilt.
    expect(mountCount).toBe(1);
  });
});

describe("Full report disclosure — the four states that hold it open", () => {
  const cases: [string, FullReportForceState][] = [
    ["a section is being edited", { ...NOTHING_FORCING, editing: true }],
    ["a section is being regenerated", { ...NOTHING_FORCING, regenerating: true }],
    ["the finalize preview is open", { ...NOTHING_FORCING, finalizing: true }],
    ["the print view is open", { ...NOTHING_FORCING, printing: true }],
  ];

  for (const [label, force] of cases) {
    it(`auto-expands and cannot be collapsed while ${label}`, () => {
      const { container } = render(<Harness force={force} />);

      expect(toggle().getAttribute("aria-expanded")).toBe("true");
      expect(panel(container).hasAttribute("hidden")).toBe(false);
      expect((toggle() as HTMLButtonElement).disabled).toBe(true);

      // Clicking a disabled control does nothing, which is the point: the
      // reader cannot collapse away a live editor, a pending candidate, the
      // document they are signing, or a page being printed.
      fireEvent.click(toggle());
      expect(toggle().getAttribute("aria-expanded")).toBe("true");
      expect(panel(container).hasAttribute("hidden")).toBe(false);
    });
  }

  it("holds open even when the doctor's stored choice is collapsed", () => {
    // The stored preference says collapsed; editing must still win.
    window.localStorage.setItem(STORAGE_KEY, "false");
    render(<Harness force={{ ...NOTHING_FORCING, editing: true }} />);
    expect(toggle().getAttribute("aria-expanded")).toBe("true");
  });

  it("returns control to the doctor once nothing is forcing it", () => {
    function Swapper() {
      const [editing, setEditing] = useState(true);
      return (
        <>
          <button onClick={() => setEditing(false)}>stop editing</button>
          <Harness force={{ ...NOTHING_FORCING, editing }} />
        </>
      );
    }
    render(<Swapper />);
    expect((toggle() as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "stop editing" }));
    expect((toggle() as HTMLButtonElement).disabled).toBe(false);
    // Falls back to the stored choice (collapsed), not stuck open.
    expect(toggle().getAttribute("aria-expanded")).toBe("false");
  });
});
