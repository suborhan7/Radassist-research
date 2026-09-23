/**
 * @vitest-environment jsdom
 *
 * Per-file, so the default node environment in vitest.config.ts is untouched.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/lib/i18n";
import { EvidenceSidebar, type EvidenceTab } from "./evidence-sidebar";

let mountCount = 0;
function MountCounter() {
  useEffect(() => {
    mountCount += 1;
  }, []);
  return null;
}

/**
 * Mirrors the workspace's wiring: plain state for the dock, plain state for
 * the tab. The panel is deliberately NOT persisted -- it docks on every load
 * -- so the harness uses the same useState the page does. A source assertion
 * in full-report-rules.test.ts holds page.tsx to that.
 */
function Harness() {
  const [collapsed, setCollapsed] = useState(true);
  const [tab, setTab] = useState<EvidenceTab>("evidence");
  return (
    <LanguageProvider initial="en">
      <EvidenceSidebar
        id="evidence-panel"
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
        activeTab={tab}
        onTabChange={setTab}
      >
        <MountCounter />
        <h4>{`panel: ${tab}`}</h4>
      </EvidenceSidebar>
    </LanguageProvider>
  );
}

const collapseBtn = () => screen.getByRole("button", { name: /collapse evidence panel/i });
const expandBtn = () => screen.getByRole("button", { name: /show evidence panel/i });
const panel = (c: HTMLElement) => c.querySelector("#evidence-panel") as HTMLElement;
const aside = (c: HTMLElement) => c.querySelector("aside") as HTMLElement;

beforeEach(() => {
  window.localStorage.clear();
  mountCount = 0;
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Evidence sidebar — default and toggle", () => {
  it("starts DOCKED for a first-time reader", () => {
    // The screen opens on the report. Evidence is something a reader goes to
    // look at, so it does not occupy a third of the station uninvited -- but
    // the rail is on screen and named, so it is one click away, not hidden.
    const { container } = render(<Harness />);
    expect(expandBtn()).not.toBeNull();
    expect(expandBtn().getAttribute("aria-expanded")).toBe("false");
    expect(panel(container).hasAttribute("hidden")).toBe(true);
    expect(aside(container).className).toContain("w-evidence-rail");
  });

  it("expands on demand and docks again", () => {
    const { container } = render(<Harness />);
    fireEvent.click(expandBtn());
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
    expect(panel(container).hasAttribute("hidden")).toBe(false);
    expect(aside(container).className).toContain("w-evidence-panel");

    fireEvent.click(collapseBtn());
    expect(expandBtn().getAttribute("aria-expanded")).toBe("false");
    expect(aside(container).className).toContain("w-evidence-rail");
    expect(panel(container).hasAttribute("hidden")).toBe(true);
  });

  it("makes the docked rail itself the control, and names what it opens", () => {
    const { container } = render(<Harness />);

    // The reopen control was a 28px chevron in tertiary grey, reported as
    // invisible. Being findable by aria-label is not the same as being
    // findable by eye, so this asserts the two things that fixed it: the
    // button fills the rail rather than sitting as an icon inside it, and it
    // carries the panel's own name so the stripe says what it will open.
    const btn = expandBtn();
    expect(btn.className).toContain("flex-1");
    expect(btn.className).toContain("bg-cyan-wash");
    expect(btn.textContent).toContain("Evidence");

    // And it is the only thing in the rail -- nothing else to aim at or miss.
    const rail = aside(container);
    expect(rail.querySelectorAll("button")).toHaveLength(1);
  });

  it("uses real buttons that name what they control", () => {
    const { container } = render(<Harness />);
    expect(expandBtn().tagName).toBe("BUTTON");
    expect(expandBtn().getAttribute("aria-controls")).toBe("evidence-panel");
    // The panel it points at exists even while docked -- hidden, not
    // unmounted -- so aria-controls never dangles.
    expect(container.querySelector("#evidence-panel")).not.toBeNull();

    fireEvent.click(expandBtn());
    expect(collapseBtn().tagName).toBe("BUTTON");
    expect(collapseBtn().getAttribute("aria-controls")).toBe("evidence-panel");
  });

  it("animates width from a token and honours reduced motion through it", () => {
    const { container } = render(<Harness />);
    // --t-panel is collapsed to 1ms by the prefers-reduced-motion block in
    // tokens.css, so honouring the preference is a property of the token
    // rather than a second code path here. Asserting the class is asserting
    // that this panel opted into that mechanism.
    expect(aside(container).className).toContain("transition-[width]");
    expect(aside(container).className).toContain("duration-panel");
  });
});

describe("Evidence sidebar — collapsed content is hidden from assistive tech", () => {
  it("takes the panel out of the accessibility tree when docked", () => {
    render(<Harness />);
    // Docked from the start, so this is the state a reader actually lands in.
    expect(screen.queryByRole("heading", { name: "panel: evidence" })).toBeNull();
    // The tab buttons go with it -- a docked panel must not leave three tab
    // controls in the tab order behind a 48px rail.
    expect(screen.queryByRole("button", { name: /agreement/i })).toBeNull();

    // And all of it comes back on expand.
    fireEvent.click(expandBtn());
    expect(screen.queryByRole("heading", { name: "panel: evidence" })).not.toBeNull();
    expect(screen.queryByRole("button", { name: /agreement/i })).not.toBeNull();
  });
});

describe("Evidence sidebar — docked on every load, never remembered", () => {
  it("comes back DOCKED after a reload, even having been expanded", () => {
    // The panel used to persist, and that is exactly what was removed: a
    // reader who opened it on one report should not find the next one already
    // open. Unmount/remount is what a reload looks like to this component.
    const first = render(<Harness />);
    fireEvent.click(expandBtn());
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
    first.unmount();

    const { container } = render(<Harness />);
    expect(expandBtn().getAttribute("aria-expanded")).toBe("false");
    expect(aside(container).className).toContain("w-evidence-rail");
  });

  it("writes nothing to storage, however much it is toggled", () => {
    // The assertion that keeps the behaviour honest: not merely that it opens
    // docked, but that there is no stored value anywhere that a future change
    // could start honouring again.
    render(<Harness />);
    fireEvent.click(expandBtn());
    fireEvent.click(collapseBtn());
    fireEvent.click(expandBtn());
    expect(window.localStorage.length).toBe(0);
  });

  it("stays expanded while the reader is on this report", () => {
    // Not persisted is not the same as not sticky: within one view it holds,
    // so the panel does not snap shut between interactions.
    render(<Harness />);
    fireEvent.click(expandBtn());
    fireEvent.click(screen.getByRole("button", { name: /alternatives/i }));
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
  });
});

describe("Evidence sidebar — reopening restores the active tab", () => {
  it("comes back on the tab it was left on, not on the first one", () => {
    render(<Harness />);
    fireEvent.click(expandBtn());
    fireEvent.click(screen.getByRole("button", { name: /alternatives/i }));
    expect(screen.queryByRole("heading", { name: "panel: alternatives" })).not.toBeNull();

    fireEvent.click(collapseBtn());
    fireEvent.click(expandBtn());

    // Not re-defaulted to "evidence". The tab survives because the panel is
    // never unmounted, so there is no restore step that could pick wrong.
    expect(screen.queryByRole("heading", { name: "panel: alternatives" })).not.toBeNull();
  });
});

describe("Evidence sidebar — toggling costs nothing", () => {
  it("fires no network request and never unmounts the panel", () => {
    render(<Harness />);
    expect(mountCount).toBe(1);

    fireEvent.click(expandBtn());
    fireEvent.click(collapseBtn());
    fireEvent.click(expandBtn());

    expect(fetch).not.toHaveBeenCalled();
    expect(mountCount).toBe(1);
  });
});
