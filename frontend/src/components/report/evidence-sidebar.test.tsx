/**
 * @vitest-environment jsdom
 *
 * Per-file, so the default node environment in vitest.config.ts is untouched.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/lib/i18n";
import { usePersistedToggle } from "@/lib/use-persisted-toggle";
import { EvidenceSidebar, type EvidenceTab } from "./evidence-sidebar";

const STORAGE_KEY = "rr:v1:doctor-1:workspace.evidenceCollapsed";

let mountCount = 0;
function MountCounter() {
  useEffect(() => {
    mountCount += 1;
  }, []);
  return null;
}

/** Mirrors the workspace's wiring: persisted collapse + in-React tab state. */
function Harness({ scope = "doctor-1" }: { scope?: string | null }) {
  const [collapsed, setCollapsed] = usePersistedToggle(scope, "workspace.evidenceCollapsed", false);
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
  it("is expanded for a first-time reader", () => {
    const { container } = render(<Harness />);
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
    expect(panel(container).hasAttribute("hidden")).toBe(false);
    expect(aside(container).className).toContain("w-evidence-panel");
  });

  it("collapses to a rail that still carries a reopen control", () => {
    const { container } = render(<Harness />);
    fireEvent.click(collapseBtn());

    // The whole point of a docked rail: the control that brings it back is
    // still on screen. A panel that collapses to nothing is unreachable.
    expect(expandBtn()).not.toBeNull();
    expect(expandBtn().getAttribute("aria-expanded")).toBe("false");
    expect(aside(container).className).toContain("w-evidence-rail");
    expect(panel(container).hasAttribute("hidden")).toBe(true);
  });

  it("makes the docked rail itself the control, and names what it opens", () => {
    const { container } = render(<Harness />);
    fireEvent.click(collapseBtn());

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

  it("reopens from the rail", () => {
    const { container } = render(<Harness />);
    fireEvent.click(collapseBtn());
    fireEvent.click(expandBtn());
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
    expect(panel(container).hasAttribute("hidden")).toBe(false);
  });

  it("uses real buttons that name what they control", () => {
    const { container } = render(<Harness />);
    expect(collapseBtn().tagName).toBe("BUTTON");
    expect(collapseBtn().getAttribute("aria-controls")).toBe("evidence-panel");
    expect(container.querySelector("#evidence-panel")).not.toBeNull();

    fireEvent.click(collapseBtn());
    expect(expandBtn().tagName).toBe("BUTTON");
    expect(expandBtn().getAttribute("aria-controls")).toBe("evidence-panel");
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
    expect(screen.queryByRole("heading", { name: "panel: evidence" })).not.toBeNull();

    fireEvent.click(collapseBtn());
    expect(screen.queryByRole("heading", { name: "panel: evidence" })).toBeNull();
    // The tab buttons go with it -- a docked panel must not leave three tab
    // controls in the tab order behind a 48px rail.
    expect(screen.queryByRole("button", { name: /agreement/i })).toBeNull();
  });
});

describe("Evidence sidebar — persistence", () => {
  it("writes the collapse choice to a namespaced, per-doctor key", () => {
    render(<Harness />);
    fireEvent.click(collapseBtn());
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("true");
  });

  it("survives a reload", () => {
    const first = render(<Harness />);
    fireEvent.click(collapseBtn());
    first.unmount();

    const { container } = render(<Harness />);
    expect(expandBtn().getAttribute("aria-expanded")).toBe("false");
    expect(aside(container).className).toContain("w-evidence-rail");
  });

  it("does not leak one doctor's layout to another", () => {
    const first = render(<Harness scope="doctor-1" />);
    fireEvent.click(collapseBtn());
    first.unmount();

    render(<Harness scope="doctor-2" />);
    expect(collapseBtn().getAttribute("aria-expanded")).toBe("true");
  });
});

describe("Evidence sidebar — reopening restores the active tab", () => {
  it("comes back on the tab it was left on, not on the first one", () => {
    render(<Harness />);
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

    fireEvent.click(collapseBtn());
    fireEvent.click(expandBtn());
    fireEvent.click(collapseBtn());

    expect(fetch).not.toHaveBeenCalled();
    expect(mountCount).toBe(1);
  });
});
