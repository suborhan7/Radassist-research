/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/lib/i18n";
import { WorkspaceProvider, useWorkspace } from "./workspace-provider";

/**
 * The provider is what the workspace layout mounts, so this is where the
 * cross-route guarantees are testable. No test in this repo mounts a route
 * module -- they all avoid next/navigation -- which is exactly why the report
 * state was extracted into a plain component rather than living in layout.tsx.
 */

const REPORT = {
  report_id: "r1",
  session_id: "s1",
  patient_id: "p1",
  doctor_id: "d1",
  status: "ai_draft",
  language: "en",
  report_date: "2026-09-23",
  content: { impression: "Pneumonia", findings: "Opacities" },
  ai_draft_content: { impression: "Pneumonia", findings: "Opacities" },
  validation: { is_clean: true, warnings: [] },
  consistency: { status: "clean", checks_run: [], applicable_checks: [], violations: [] },
  retrieved_cases: [],
  audit_log: [],
};

/** Counts mounts so a remount -- and therefore a refetch -- is observable. */
let providerMounts = 0;
function MountCounter() {
  useEffect(() => {
    providerMounts += 1;
  }, []);
  return null;
}

/** Stands in for the report route. */
function ReportView() {
  const { report } = useWorkspace();
  return <h2>{`report: ${report?.report_id ?? "none"}`}</h2>;
}

/** Stands in for the evidence route, including the tab the layout owns. */
function EvidenceView() {
  const { railTab, setRailTab } = useWorkspace();
  return (
    <>
      <h2>{`evidence: ${railTab}`}</h2>
      <button onClick={() => setRailTab("alternatives")}>alternatives</button>
    </>
  );
}

function Harness({ child }: { child: "report" | "evidence" }) {
  return (
    <LanguageProvider initial="en">
      <WorkspaceProvider reportId="r1">
        <MountCounter />
        {child === "report" ? <ReportView /> : <EvidenceView />}
      </WorkspaceProvider>
    </LanguageProvider>
  );
}

let fetchSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  providerMounts = 0;
  fetchSpy = vi.fn(async (url: string) => {
    const body = url.includes("/patients/")
      ? { id: "p1", name: "Aisha Rahman", patient_code: "PAT-1" }
      : url.includes("/auth/me")
        ? { id: "d1" }
        : REPORT;
    return { ok: true, status: 200, json: async () => body } as Response;
  });
  vi.stubGlobal("fetch", fetchSpy);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const settle = () => screen.findByRole("heading", { name: /report: r1|evidence:/ });

describe("WorkspaceProvider — one fetch for the whole workspace", () => {
  it("loads the report once", async () => {
    render(<Harness child="report" />);
    await settle();
    const reportCalls = fetchSpy.mock.calls.filter(([u]) => String(u).match(/\/reports\/r1$/));
    expect(reportCalls).toHaveLength(1);
  });

  it("fires NO request when the child route changes", async () => {
    // This is the brief's hard requirement. Swapping the child is what Next
    // does when you navigate between /report and /evidence under a shared
    // layout: the layout (and this provider) stay mounted, the page swaps.
    const view = render(<Harness child="report" />);
    await settle();
    const callsAfterLoad = fetchSpy.mock.calls.length;
    expect(providerMounts).toBe(1);

    view.rerender(<Harness child="evidence" />);
    await screen.findByRole("heading", { name: /evidence:/ });

    expect(fetchSpy.mock.calls.length).toBe(callsAfterLoad);
    // And the provider itself never remounted -- a fetch count alone would
    // pass even if the subtree were being destroyed and rebuilt.
    expect(providerMounts).toBe(1);

    view.rerender(<Harness child="report" />);
    await screen.findByRole("heading", { name: /report: r1/ });
    expect(fetchSpy.mock.calls.length).toBe(callsAfterLoad);
    expect(providerMounts).toBe(1);
  });

  it("keeps the active evidence tab when the reader goes back and forth", async () => {
    const view = render(<Harness child="evidence" />);
    await screen.findByRole("heading", { name: "evidence: evidence" });

    fireEvent.click(screen.getByRole("button", { name: "alternatives" }));
    expect(screen.getByRole("heading", { name: "evidence: alternatives" })).not.toBeNull();

    view.rerender(<Harness child="report" />);
    await screen.findByRole("heading", { name: /report: r1/ });
    view.rerender(<Harness child="evidence" />);

    // Not reset to the first tab: the tab is owned by the provider, not by the
    // page that keeps unmounting.
    expect(await screen.findByRole("heading", { name: "evidence: alternatives" })).not.toBeNull();
  });
});

describe("WorkspaceProvider — the unsaved-work guard", () => {
  function GuardHarness() {
    const { handleDirtyChange, guardedNavigate, hasUnsavedChanges } = useWorkspace();
    return (
      <>
        <span>{`dirty: ${hasUnsavedChanges}`}</span>
        <button onClick={() => handleDirtyChange("findings", true)}>make dirty</button>
        <a
          href="/elsewhere"
          onClick={(e) => {
            e.preventDefault = vi.fn();
            guardedNavigate(e);
            (globalThis as { __prevented?: boolean }).__prevented =
              (e.preventDefault as ReturnType<typeof vi.fn>).mock.calls.length > 0;
          }}
        >
          leave
        </a>
      </>
    );
  }

  const render_ = () =>
    render(
      <LanguageProvider initial="en">
        <WorkspaceProvider reportId="r1">
          <GuardHarness />
        </WorkspaceProvider>
      </LanguageProvider>,
    );

  it("lets a clean reader leave without asking", () => {
    const confirmSpy = vi.fn(() => true);
    vi.stubGlobal("confirm", confirmSpy);
    render_();
    fireEvent.click(screen.getByRole("link", { name: "leave" }));
    expect(confirmSpy).not.toHaveBeenCalled();
    expect((globalThis as { __prevented?: boolean }).__prevented).toBe(false);
  });

  it("asks before abandoning an edit, and stays put when declined", () => {
    const confirmSpy = vi.fn(() => false);
    vi.stubGlobal("confirm", confirmSpy);
    render_();
    fireEvent.click(screen.getByRole("button", { name: "make dirty" }));
    expect(screen.getByText("dirty: true")).not.toBeNull();

    fireEvent.click(screen.getByRole("link", { name: "leave" }));
    expect(confirmSpy).toHaveBeenCalled();
    expect((globalThis as { __prevented?: boolean }).__prevented).toBe(true);
  });

  it("lets the reader through when they accept the loss", () => {
    vi.stubGlobal("confirm", vi.fn(() => true));
    render_();
    fireEvent.click(screen.getByRole("button", { name: "make dirty" }));
    fireEvent.click(screen.getByRole("link", { name: "leave" }));
    expect((globalThis as { __prevented?: boolean }).__prevented).toBe(false);
  });
});
