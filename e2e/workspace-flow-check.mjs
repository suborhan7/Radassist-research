// e2e/workspace-flow-check.mjs
// ============================================================================
// Proves the page-based workspace flow against the RUNNING app:
//
//   1. the old /reports/{id} URL still lands on the report (permanent redirect)
//   2. /workspace/{id} redirects to /workspace/{id}/report
//   3. deep-linking /workspace/{id}/evidence loads populated, not blank
//   4. navigating report -> evidence -> report fires NO report request
//   5. the active evidence tab survives the round trip
//   6. browser back/forward land on the right pages
//
// #4 is the one jsdom cannot settle. The component test proves the provider
// does not refetch when its child swaps; only a real browser proves that Next
// actually keeps the layout mounted across a client-side navigation, which is
// the assumption the whole design rests on. Requests are counted from CDP, not
// inferred.
//
// SAFETY: picks no database. Talks to whatever E2E_API names; the caller points
// that backend at a disposable copy.
// ============================================================================
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "./harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API ?? cfg.apiBase;
const FE = process.env.E2E_FRONTEND ?? cfg.frontendBase;
const EMAIL = process.env.SHOT_EMAIL;
const PASSWORD = process.env.SHOT_PASSWORD;
const REPORT = process.env.SHOT_REPORT;

for (const [k, v] of Object.entries({ SHOT_EMAIL: EMAIL, SHOT_PASSWORD: PASSWORD, SHOT_REPORT: REPORT })) {
  if (!v) { console.error(`FATAL: ${k} is required`); process.exit(2); }
}

const edge = launchEdge(cfg);
let cdp;
let failures = 0;
let reportRequests = 0;

function check(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}  (got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)})`);
}

async function until(expr, what, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { if (await cdp.evalJs(expr)) return; } catch {}
    await sleep(200);
  }
  throw new Error(`timed out waiting for: ${what}`);
}

const path = `(() => location.pathname)()`;
/** Is the control on the page yet? A resolved URL is not a hydrated page. */
const clickTargetExists = (text) => `(() => !![...document.querySelectorAll('a,button')]
  .find(e => ((e.textContent||'') + ' ' + (e.getAttribute('aria-label')||''))
    .toLowerCase().includes(${JSON.stringify(text.toLowerCase())})))()`;

/** Click an in-app link/button by its visible text, then let the router settle. */
const clickText = (text) => `(() => {
  const el = [...document.querySelectorAll('a,button')]
    .find(e => ((e.textContent||'') + ' ' + (e.getAttribute('aria-label')||''))
      .toLowerCase().includes(${JSON.stringify(text.toLowerCase())}));
  if (!el || el.disabled) return false;
  el.click();
  return true;
})()`;

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  // Count every GET of the report itself, from the browser's own network layer.
  cdp.ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.method === "Network.requestWillBeSent") {
      const u = m.params?.request?.url ?? "";
      if (new RegExp(`/reports/${REPORT}(\\?|$)`).test(u)) reportRequests++;
    }
  });

  const res = await fetch(`${API}/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status}`);
  const jwt = (res.headers.getSetCookie().find((c) => c.startsWith("radassist_token=")) || "").split(";")[0].split("=")[1];
  await cdp.send("Network.setCookie", { name: "radassist_token", value: jwt, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" });

  console.log("\n1. the old URL still works");
  await cdp.send("Page.navigate", { url: `${FE}/reports/${REPORT}` });
  await until("document.readyState === 'complete'", "old url");
  await until(`!!document.querySelector('h3,h2,section')`, "content");
  await sleep(700);
  check("/reports/{id} lands on the report page", await cdp.evalJs(path), `/workspace/${REPORT}/report`);

  console.log("\n2. the bare workspace URL redirects");
  await cdp.send("Page.navigate", { url: `${FE}/workspace/${REPORT}` });
  await until("document.readyState === 'complete'", "bare url");
  await sleep(700);
  check("/workspace/{id} redirects to /report", await cdp.evalJs(path), `/workspace/${REPORT}/report`);

  console.log("\n3. deep link straight to evidence");
  await cdp.send("Page.navigate", { url: `${FE}/workspace/${REPORT}/evidence` });
  await until("document.readyState === 'complete'", "evidence deep link");
  await until(`document.body.innerText.toLowerCase().includes('archive cases')`, "evidence content", 30000);
  check("evidence deep link renders content", true, true);

  console.log("\n4. navigation fires no report request");
  // Land on the report first, then count only what the navigations cause.
  await cdp.evalJs(clickText("back to report"));
  await until(`location.pathname.endsWith('/report')`, "back to report");
  await sleep(600);
  const before = reportRequests;

  await cdp.evalJs(clickText("alternatives")); // change the tab later; first go to evidence
  await cdp.evalJs(clickText("view evidence"));
  await until(`location.pathname.endsWith('/evidence')`, "to evidence");
  await sleep(500);
  await cdp.evalJs(clickText("alternatives"));
  await sleep(300);
  await cdp.evalJs(clickText("back to report"));
  await until(`location.pathname.endsWith('/report')`, "to report");
  await sleep(500);
  await cdp.evalJs(clickText("view evidence"));
  await until(`location.pathname.endsWith('/evidence')`, "to evidence again");
  await sleep(600);

  check("report GETs during report<->evidence navigation", reportRequests - before, 0);

  console.log("\n5. the active tab survived");
  const activeTab = await cdp.evalJs(`(() => {
    const el = document.querySelector('main [aria-current="true"]');
    return el ? el.textContent.trim().toLowerCase() : 'none';
  })()`);
  check("tab preserved across the round trip", activeTab, "alternatives");

  console.log("\n6. browser back / forward");
  await cdp.send("Page.navigate", { url: `${FE}/workspace/${REPORT}/report` });
  await until(`location.pathname.endsWith('/report')`, "report");
  await until(clickTargetExists("view evidence"), "hydrated report page");
  await cdp.evalJs(clickText("view evidence"));
  await until(`location.pathname.endsWith('/evidence')`, "evidence");
  await cdp.evalJs("history.back()");
  await sleep(900);
  check("back returns to the report", await cdp.evalJs(path), `/workspace/${REPORT}/report`);
  await cdp.evalJs("history.forward()");
  await sleep(900);
  check("forward returns to the evidence", await cdp.evalJs(path), `/workspace/${REPORT}/evidence`);

  console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
  process.exitCode = failures === 0 ? 0 : 1;
} catch (err) {
  console.error("FAILED:", err.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
