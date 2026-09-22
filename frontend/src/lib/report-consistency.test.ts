import { describe, expect, it } from "vitest";
import { consistencyStatusOf, isPass, missingChecks } from "./report-consistency";

const ALL = ["temporal", "transplant", "contradiction"];

describe("consistencyStatusOf — reads the verdict, never re-derives it", () => {
  for (const status of ["not_run", "partial", "clean", "violations"] as const) {
    it(`passes through "${status}"`, () => {
      expect(consistencyStatusOf({ status })).toBe(status);
    });
  }

  it("treats an absent block as not_run", () => {
    // A response from a backend older than v1.2 knows nothing about this
    // report's consistency, and nothing-known must never read as assurance.
    expect(consistencyStatusOf(undefined)).toBe("not_run");
    expect(consistencyStatusOf(null)).toBe("not_run");
    expect(consistencyStatusOf({})).toBe("not_run");
  });

  it("treats an unrecognised status as not_run, not as clean", () => {
    // If the backend ever grows a fifth status, an old client must degrade to
    // under-claiming. The dangerous direction is the other one.
    expect(consistencyStatusOf({ status: "calibrating" })).toBe("not_run");
    expect(consistencyStatusOf({ status: "" })).toBe("not_run");
  });
});

describe("isPass", () => {
  it("is true for clean and nothing else", () => {
    expect(isPass("clean")).toBe(true);
    expect(isPass("partial")).toBe(false);
    expect(isPass("not_run")).toBe(false);
    expect(isPass("violations")).toBe(false);
  });
});

describe("missingChecks — which checks a report did not get, by name", () => {
  it("names the gap between applicable and run", () => {
    expect(
      missingChecks({ checks_run: ["temporal", "contradiction"], applicable_checks: ALL }),
    ).toEqual(["transplant"]);
  });

  it("is empty when every applicable check ran", () => {
    expect(missingChecks({ checks_run: ALL, applicable_checks: ALL })).toEqual([]);
  });

  it("is empty for a Bengali report, whose applicable set is empty", () => {
    // Frozen §3.4: all three detectors are English-only, so there is no list
    // of "missing" checks -- the reason is carried by the not-run copy, not
    // by a list of things that were never owed.
    expect(missingChecks({ checks_run: [], applicable_checks: [] })).toEqual([]);
  });

  it("reports the whole applicable set when nothing ran", () => {
    expect(missingChecks({ checks_run: [], applicable_checks: ALL })).toEqual(ALL);
  });

  it("survives a payload with the fields absent", () => {
    expect(missingChecks({})).toEqual([]);
    expect(missingChecks(null)).toEqual([]);
  });
});
