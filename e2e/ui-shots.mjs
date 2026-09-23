// e2e/ui-shots.mjs
// ============================================================================
// Captures the workspace UI states for the summary-first report panel and the
// collapsible evidence sidebar, at 1440x900, in BOTH themes.
//
// Reuses e2e/harness.mjs's Edge + CDP client rather than adding a browser
// dependency -- the repo already drives a real headless browser this way, and
// a second mechanism would be a second thing to keep working.
//
// SAFETY: this script never picks a database. It talks to whatever backend
// E2E_API points at, and the caller is responsible for having started that
// backend against a disposable copy. It performs no writes of its own beyond
// logging in as a doctor it is given.
//
//   E2E_API=http://localhost:8011 E2E_FRONTEND=http://localhost:3011 \
//   SHOT_EMAIL=... SHOT_PASSWORD=... SHOT_REPORT=... SHOT_REPORT_WARN=... \
//   E2E_OUT=docs/thesis/figures/ui node e2e/ui-shots.mjs
// ============================================================================
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "./harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API ?? cfg.apiBase;
const FE = process.env.E2E_FRONTEND ?? cfg.frontendBase;
const OUT = process.env.E2E_OUT ?? "scratch/ui-shots";
const EMAIL = process.env.SHOT_EMAIL;
const PASSWORD = process.env.SHOT_PASSWORD;
const REPORT = process.env.SHOT_REPORT;
const REPORT_WARN = process.env.SHOT_REPORT_WARN;

for (const [k, v] of Object.entries({ SHOT_EMAIL: EMAIL, SHOT_PASSWORD: PASSWORD, SHOT_REPORT: REPORT, SHOT_REPORT_WARN: REPORT_WARN })) {
  if (!v) { console.error(`FATAL: ${k} is required`); process.exit(2); }
}

mkdirSync(OUT, { recursive: true });
const log = (...a) => console.log(...a);

const edge = launchEdge({ ...cfg, cdpPort: cfg.cdpPort });
let cdp;

/** Wait until an expression is truthy, or throw. */
async function until(expr, what, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { if (await cdp.evalJs(expr)) return; } catch {}
    await sleep(250);
  }
  throw new Error(`timed out waiting for: ${what}`);
}

async function goto(url) {
  await cdp.send("Page.navigate", { url });
  await until("document.readyState === 'complete'", `load ${url}`);
}

async function shot(name) {
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 0, y: 0, width: 1440, height: 900, scale: 1 },
  });
  const path = join(OUT, `${name}.png`);
  writeFileSync(path, Buffer.from(data, "base64"));
  log(`  captured ${path}`);
}

/** Click the first element matching a text predicate; returns whether it hit. */
// Both the visible text AND the aria-label are searched, concatenated rather
// than ||'d: the sidebar's controls are icon-only, so their textContent is a
// chevron glyph -- truthy, and it would shadow the label that actually names
// them.
const clickByText = (selector, text) => `(() => {
  const el = [...document.querySelectorAll(${JSON.stringify(selector)})]
    .find(e => ((e.textContent || '') + ' ' + (e.getAttribute('aria-label') || ''))
      .toLowerCase().includes(${JSON.stringify(text.toLowerCase())}));
  if (!el || el.disabled) return false;
  el.click();
  return true;
})()`;

const setTheme = (theme) => `(() => {
  document.cookie = 'rr_theme=' + ${JSON.stringify("")} + ${JSON.stringify(theme)} + '; path=/; max-age=31536000; samesite=lax';
  return true;
})()`;

/** Reset the two remembered panel choices so each run starts from the default. */
const clearPrefs = `(() => { try { Object.keys(localStorage)
  .filter(k => k.startsWith('rr:v1:')).forEach(k => localStorage.removeItem(k)); } catch {} return true; })()`;

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");

  // Pin the VIEWPORT to 1440x900, not just the window. --window-size sizes the
  // outer window, so the page's own viewport comes out ~90px shorter and a
  // 100dvh layout leaves a dead band at the bottom of every capture. These
  // shots are of a fixed 1440x900 reading station, so the viewport is the
  // thing that has to be exact.
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  // Authenticate exactly the way owner-flow.mjs does: take the httpOnly cookie
  // the API itself issues and inject it. Driving the login form instead would
  // be testing the login form, which is not what these shots are of, and it is
  // the step most likely to fail for reasons unrelated to the panels.
  log("authenticating…");
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status} ${await res.text()}`);
  const setCookies = res.headers.getSetCookie?.() ?? [];
  const jwt = (setCookies.find((c) => c.startsWith("radassist_token=")) || "").split(";")[0].split("=")[1];
  if (!jwt) throw new Error("login did not return a radassist_token cookie");
  await cdp.send("Network.setCookie", {
    name: "radassist_token", value: jwt, domain: "localhost", path: "/",
    httpOnly: true, secure: false, sameSite: "Lax",
  });
  log("  session cookie installed");

  for (const theme of ["dark", "light"]) {
    log(`\n=== ${theme} ===`);
    await goto(`${FE}/dashboard`);
    await cdp.evalJs(setTheme(theme));

    // ---- clean report: summary, full report, sidebar states ----
    await goto(`${FE}/reports/${REPORT}`);
    await cdp.evalJs(clearPrefs);
    await goto(`${FE}/reports/${REPORT}`);
    await until("!!document.querySelector('[aria-controls=\"full-report\"]')", "workspace loaded", 30000);
    await sleep(600); // let the film image paint

    await shot(`${theme}-1-summary`);

    if (!(await cdp.evalJs(clickByText("button", "show full report")))) {
      throw new Error("could not find the 'Show full report' control");
    }
    await sleep(350);
    await shot(`${theme}-2-full-report-expanded`);

    // Back to summary, then exercise the sidebar. Docked is the DEFAULT now,
    // so the collapsed frame is simply the state the screen opens in and the
    // expanded one has to be asked for -- the reverse of the original order.
    await cdp.evalJs(clickByText("button", "hide full report"));
    await sleep(350);
    await shot(`${theme}-4-sidebar-collapsed`);

    if (!(await cdp.evalJs(clickByText("button", "show evidence panel")))) {
      throw new Error("could not find the expand control on the docked rail");
    }
    await sleep(500); // width transition
    await shot(`${theme}-3-sidebar-expanded`);

    // ---- report WITH validation warnings, full report collapsed ----
    await goto(`${FE}/reports/${REPORT_WARN}`);
    await cdp.evalJs(clearPrefs);
    await goto(`${FE}/reports/${REPORT_WARN}`);
    await until("!!document.querySelector('[aria-controls=\"full-report\"]')", "warning workspace loaded", 30000);
    await sleep(600);
    await shot(`${theme}-5-warnings-full-report-collapsed`);
  }

  log("\nall shots captured.");
} catch (err) {
  console.error("FAILED:", err.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
