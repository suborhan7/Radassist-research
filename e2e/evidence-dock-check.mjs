// e2e/evidence-dock-check.mjs
// ============================================================================
// Proves, against the RUNNING app, the one property the evidence panel is
// required to have: it is docked on every load, whatever the reader did last
// time. jsdom can show that a remount starts docked; only the real browser can
// show that a genuine reload, with real localStorage and a real Next.js
// navigation in between, does the same.
//
// The sequence is the one a reader actually performs:
//
//   1. open a report            -> expect DOCKED
//   2. expand the panel         -> expect OPEN
//   3. reload the same report   -> expect DOCKED   (the regression to catch)
//   4. open a DIFFERENT report  -> expect DOCKED   (no bleed between cases)
//   5. assert localStorage holds no evidence-panel key at all
//
// Step 5 is what makes the rest durable: the panel opens docked because there
// is nothing stored to consult, not because a default happens to win today.
//
// SAFETY: picks no database. Talks to whatever E2E_API names; the caller is
// responsible for pointing that backend at a disposable copy.
// ============================================================================
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "./harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API ?? cfg.apiBase;
const FE = process.env.E2E_FRONTEND ?? cfg.frontendBase;
const EMAIL = process.env.SHOT_EMAIL;
const PASSWORD = process.env.SHOT_PASSWORD;
const A = process.env.SHOT_REPORT;
const B = process.env.SHOT_REPORT_WARN;

for (const [k, v] of Object.entries({ SHOT_EMAIL: EMAIL, SHOT_PASSWORD: PASSWORD, SHOT_REPORT: A, SHOT_REPORT_WARN: B })) {
  if (!v) { console.error(`FATAL: ${k} is required`); process.exit(2); }
}

const edge = launchEdge(cfg);
let cdp;
let failures = 0;

function check(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}  (got ${actual}, expected ${expected})`);
}

async function until(expr, what, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { if (await cdp.evalJs(expr)) return; } catch {}
    await sleep(250);
  }
  throw new Error(`timed out waiting for: ${what}`);
}

async function open(reportId) {
  await cdp.send("Page.navigate", { url: `${FE}/reports/${reportId}` });
  await until("document.readyState === 'complete'", "load");
  await until(`!!document.querySelector('[aria-controls="evidence-panel"]')`, "workspace");
  await sleep(500);
}

/** "docked" | "open", read from the control's own aria-expanded. */
const dockState = `(() => {
  const btn = document.querySelector('[aria-controls="evidence-panel"]');
  return btn.getAttribute('aria-expanded') === 'true' ? 'open' : 'docked';
})()`;

const evidenceKeys = `(() => {
  try {
    return Object.keys(localStorage).filter(k => /evidence/i.test(k)).join(',') || 'none';
  } catch { return 'unavailable'; }
})()`;

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const res = await fetch(`${API}/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status}`);
  const jwt = (res.headers.getSetCookie().find((c) => c.startsWith("radassist_token=")) || "").split(";")[0].split("=")[1];
  await cdp.send("Network.setCookie", { name: "radassist_token", value: jwt, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" });

  console.log("\n1. first open of report A");
  await open(A);
  check("opens docked", await cdp.evalJs(dockState), "docked");

  console.log("\n2. expand it");
  await cdp.evalJs(`document.querySelector('[aria-controls="evidence-panel"]').click()`);
  await sleep(500);
  check("expands on click", await cdp.evalJs(dockState), "open");

  console.log("\n3. reload the SAME report (the regression this guards)");
  await open(A);
  check("still docked after reload", await cdp.evalJs(dockState), "docked");

  console.log("\n4. open a DIFFERENT report");
  await cdp.evalJs(`document.querySelector('[aria-controls="evidence-panel"]').click()`);
  await sleep(400);
  await open(B);
  check("docked on the next case", await cdp.evalJs(dockState), "docked");

  console.log("\n5. storage");
  check("no evidence key persisted", await cdp.evalJs(evidenceKeys), "none");

  console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
  process.exitCode = failures === 0 ? 0 : 1;
} catch (err) {
  console.error("FAILED:", err.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
