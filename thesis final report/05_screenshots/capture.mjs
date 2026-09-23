// thesis final report/05_screenshots/capture.mjs
// ============================================================================
// Captures the CURRENT page-based UI (Generate -> Report -> Evidence) for the
// final report packet, at 1440x900, in dark and light.
//
// This file lives in the PACKET, not in e2e/, because the packet brief forbids
// source changes. It reuses e2e/harness.mjs's Edge + CDP client rather than
// adding a second browser mechanism.
//
// SAFETY -- the property that matters:
//   This script NEVER selects a database. It talks to whatever E2E_API points
//   at. The caller starts that backend against a DISPOSABLE COPY of dev.db,
//   and the copy's sha256 is checked before and after. dev.db is never opened
//   by the backend this script drives.
//
// Usage:
//   E2E_API=http://localhost:8021 E2E_FRONTEND=http://localhost:3021 \
//   SHOT_EMAIL=... SHOT_PASSWORD=... \
//   node "thesis final report/05_screenshots/capture.mjs"
// ============================================================================
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "../../e2e/harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API ?? cfg.apiBase;
const FE = process.env.E2E_FRONTEND ?? cfg.frontendBase;
const OUT = process.env.E2E_OUT ?? "thesis final report/05_screenshots";
const EMAIL = process.env.SHOT_EMAIL;
const PASSWORD = process.env.SHOT_PASSWORD;

// Fixtures staged in the disposable copy (see 05_screenshots/README.md).
const PATIENT = process.env.SHOT_PATIENT ?? "9b977adac2a5479cb3bd9716cf0ce44b"; // PAT-000035, 10 priors
const PATIENT_FRESH = process.env.SHOT_PATIENT_FRESH ?? "1744d1dede864de596c1e1b1063b8e8c"; // PAT-000036
const R_PARTIAL = process.env.SHOT_R_PARTIAL ?? "97aac3d4b0d34eea84be84d58b3ae18f";
const R_VIOLATIONS = process.env.SHOT_R_VIOLATIONS ?? "aa967481b34042c1a9df36dfd22956ac";
const R_WARNINGS = process.env.SHOT_R_WARNINGS ?? "4452830e88584ae3a785473588f61dfc";
const R_BELOWFLOOR = process.env.SHOT_R_BELOWFLOOR ?? "30fe6afa91f744f2a6a99f63af1b1902";
const R_BENGALI = process.env.SHOT_R_BENGALI ?? "9928bef771c14078aee450f39e44a8aa";
const R_FINAL = process.env.SHOT_R_FINAL ?? "1109f7553a294ae390fbb7b8b3f8ff29";
const R_FINAL_PREV = process.env.SHOT_R_FINAL_PREV ?? "efeb8016cc0c4764918779eb3545e1be";
const IMAGE = process.env.SHOT_IMAGE ?? cfg.image;

for (const [k, v] of Object.entries({ SHOT_EMAIL: EMAIL, SHOT_PASSWORD: PASSWORD })) {
  if (!v) { console.error(`FATAL: ${k} is required`); process.exit(2); }
}

mkdirSync(OUT, { recursive: true });
const log = (...a) => console.log(...a);
/** Every capture, recorded as it happens; written out as the manifest seed. */
const captured = [];

const edge = launchEdge({ ...cfg, cdpPort: cfg.cdpPort });
let cdp;

async function until(expr, what, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try { if (await cdp.evalJs(expr)) return true; } catch (e) { last = e.message; }
    await sleep(200);
  }
  throw new Error(`timed out waiting for: ${what}${last ? ` (last: ${last})` : ""}`);
}

async function goto(url) {
  await cdp.send("Page.navigate", { url });
  await until("document.readyState === 'complete'", `load ${url}`);
  await sleep(450); // let client data land and paint
}

async function shot(name, route, state, caption) {
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 0, y: 0, width: 1440, height: 900, scale: 1 },
  });
  const file = `${name}.png`;
  writeFileSync(join(OUT, file), Buffer.from(data, "base64"));
  captured.push({ file, route, state, caption });
  log(`  ✓ ${file}`);
}

const clickByText = (selector, text) => `(() => {
  const el = [...document.querySelectorAll(${JSON.stringify(selector)})]
    .find(e => ((e.textContent || '') + ' ' + (e.getAttribute('aria-label') || ''))
      .toLowerCase().includes(${JSON.stringify(text.toLowerCase())}));
  if (!el || el.disabled) return false;
  el.click(); return true;
})()`;

const setCookieJs = (name, value) =>
  `(() => { document.cookie = ${JSON.stringify(name)} + '=' + ${JSON.stringify(value)} + '; path=/; max-age=31536000; samesite=lax'; return true; })()`;

const clearPrefs = `(() => { try { Object.keys(localStorage)
  .filter(k => k.startsWith('rr:v1:')).forEach(k => localStorage.removeItem(k)); } catch {} return true; })()`;

/** Set theme + language by cookie, then hard-reload so the server layout picks them up. */
async function setChrome({ theme, lang }) {
  await goto(`${FE}/dashboard`);
  if (theme) await cdp.evalJs(setCookieJs("rr_theme", theme));
  if (lang) await cdp.evalJs(setCookieJs("rr_lang", lang));
}

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");
  await cdp.send("DOM.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  // ---------------------------------------------------------------- unauthed
  // Captured BEFORE the session cookie is installed, so they are the real
  // signed-out screens rather than authenticated ones that happen to render.
  log("\n=== signed-out screens (dark) ===");
  await goto(`${FE}/`);
  await cdp.evalJs(setCookieJs("rr_theme", "dark"));
  await goto(`${FE}/`);
  await shot("01-landing-dark", "/", "signed out", "The public landing page, the first screen a new user meets.");

  await goto(`${FE}/register`);
  await shot("02-registration-dark", "/register", "signed out, empty form", "Doctor registration: name, email, BMDC number, password.");

  await goto(`${FE}/login`);
  await shot("03-login-dark", "/login", "signed out, empty form", "Sign in with email and password.");

  // ------------------------------------------------------------------- auth
  log("\nauthenticating…");
  const res = await fetch(`${API}/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status} ${await res.text()}`);
  const jwt = ((res.headers.getSetCookie?.() ?? []).find((c) => c.startsWith("radassist_token=")) || "")
    .split(";")[0].split("=")[1];
  if (!jwt) throw new Error("login did not return a radassist_token cookie");
  await cdp.send("Network.setCookie", {
    name: "radassist_token", value: jwt, domain: "localhost", path: "/",
    httpOnly: true, secure: false, sameSite: "Lax",
  });
  log("  session cookie installed");

  // ------------------------------------------------------- authed, dark pass
  log("\n=== signed-in screens (dark) ===");
  await setChrome({ theme: "dark", lang: "en" });

  await goto(`${FE}/dashboard`);
  await shot("04-queue-dark", "/dashboard", "worklist with this doctor's reports", "The queue: every report this doctor owns, newest first.");

  await goto(`${FE}/patients/search`);
  await shot("05-find-patient-dark", "/patients/search", "empty search", "Find patient by code or name before starting an examination.");

  await goto(`${FE}/patients`);
  await shot("06-patients-dark", "/patients", "patient list", "All patients this doctor has examined.");

  await goto(`${FE}/patients/new`);
  await shot("07-register-patient-dark", "/patients/new", "empty form", "Registering a new patient record.");

  await goto(`${FE}/patients/${PATIENT}`);
  await shot("08-patient-profile-dark", `/patients/${PATIENT}`, "PAT-000035, with prior studies", "Patient profile: demographics and the list of prior studies.");

  // ----------------------------------------------- live generate (real LLM)
  log("\n=== live generation on a disposable DB ===");
  await goto(`${FE}/patients/${PATIENT_FRESH}/upload`);
  await shot("09-new-examination-dark", `/patients/${PATIENT_FRESH}/upload`, "empty drop target", "New examination: the film drop target before an image is chosen.");

  const { root } = await cdp.send("DOM.getDocument", { depth: -1 });
  const { nodeId } = await cdp.send("DOM.querySelector", { nodeId: root.nodeId, selector: "input[type=file]" });
  if (!nodeId) throw new Error("no file input on the upload page");
  await cdp.send("DOM.setFileInputFiles", { nodeId, files: [IMAGE] });
  await sleep(900);
  // Projection is REQUIRED: the start control stays disabled until one is
  // picked (`disabled={!file || !declaredProjection}`), so this is part of the
  // flow, not a convenience.
  if (!(await cdp.evalJs(clickByText("button", "PA")))) throw new Error("could not select the PA projection");
  await sleep(350);
  await shot("10-upload-selected-dark", `/patients/${PATIENT_FRESH}/upload`, "chest X-ray selected, PA projection declared", "The selected film with the declared projection, before the pipeline runs.");

  if (!(await cdp.evalJs(clickByText("button", "start examination")))) {
    throw new Error("could not find the start control");
  }
  // The pipeline paints upload -> retrieve -> questionnaire -> generate. Shoot
  // while retrieval/questionnaire is on screen, which is the "in progress" state.
  await sleep(1400);
  await shot("11-generate-in-progress-dark", `/patients/${PATIENT_FRESH}/upload`, "pipeline running, per-step timings live", "Generate in progress: the four pipeline steps with elapsed times.");

  // Questionnaire step, if the doctor has not defaulted it to skip.
  const hasQ = await cdp.evalJs(`!!document.querySelector('form input, form textarea, form select')`).catch(() => false);
  if (hasQ) {
    await shot("12-questionnaire-dark", `/patients/${PATIENT_FRESH}/upload`, "optional clinical questionnaire", "The optional questionnaire offered after retrieval; it can be skipped.");
    await cdp.evalJs(clickByText("button", "skip"));
  }
  // Wait for the generation to finish and the "view result" link to appear.
  let newReportId = null;
  try {
    await until(`!!document.querySelector('a[href*="/workspace/"]')`, "generation complete", 180000);
    newReportId = await cdp.evalJs(`(() => {
      const a = [...document.querySelectorAll('a[href*="/workspace/"]')].pop();
      const m = a && a.getAttribute('href').match(/\\/workspace\\/([^/]+)/);
      return m ? m[1] : null; })()`);
    await shot("13-generate-complete-dark", `/patients/${PATIENT_FRESH}/upload`, "all four steps done, result offered", "Generation complete; the reader chooses when to open the result.");
    log(`  live report: ${newReportId}`);
  } catch (e) {
    log(`  ! live generation did not complete: ${e.message}`);
  }

  // ------------------------------------------------------- result / evidence
  log("\n=== report + evidence states (dark) ===");
  const reportShots = [
    ["14-result-partial-dark", R_PARTIAL, "consistency = partial (English, pre-Gate-B)", "Result page. Consistency reads 'partial': the transplant check is not yet calibrated."],
    ["15-result-violations-dark", R_VIOLATIONS, "consistency = violations", "Result page with a consistency violation raised by the temporal check."],
    ["16-result-warnings-dark", R_WARNINGS, "validation warnings, consistency = not_run", "Result page carrying semantic validation warnings on a pre-v1.2 report."],
    ["17-result-below-floor-dark", R_BELOWFLOOR, "retrieval support = below_floor", "Result page where retrieval support fell below the floor."],
  ];
  for (const [name, rid, state, caption] of reportShots) {
    await goto(`${FE}/workspace/${rid}/report`);
    await cdp.evalJs(clearPrefs);
    await goto(`${FE}/workspace/${rid}/report`);
    await sleep(600);
    await shot(name, `/workspace/{id}/report`, state, caption);
  }

  // Full report expanded
  await goto(`${FE}/workspace/${R_PARTIAL}/report`);
  await sleep(500);
  if (await cdp.evalJs(clickByText("button", "full report"))) {
    await sleep(500);
    await shot("18-full-report-expanded-dark", `/workspace/{id}/report`, "full report disclosure expanded", "The full seven-field report, expanded from the summary.");
  }

  // Evidence, all three tabs
  await goto(`${FE}/workspace/${R_PARTIAL}/evidence`);
  await sleep(700);
  await shot("19-evidence-tab-evidence-dark", `/workspace/{id}/evidence`, "Evidence tab: retrieved neighbours", "Evidence page, Evidence tab: the k retrieved neighbour cases and their similarity.");
  if (await cdp.evalJs(clickByText("button", "agreement"))) {
    await sleep(450);
    await shot("20-evidence-tab-agreement-dark", `/workspace/{id}/evidence`, "Agreement tab: label voting", "Evidence page, Agreement tab: voted labels and the agreement score.");
  }
  if (await cdp.evalJs(clickByText("button", "alternative"))) {
    await sleep(450);
    await shot("21-evidence-tab-alternatives-dark", `/workspace/{id}/evidence`, "Alternatives tab", "Evidence page, Alternatives tab: labels that did not win the vote.");
  }

  // Explainability -- asks a real question of the LLM.
  log("\n=== explainability (live LLM) ===");
  await goto(`${FE}/reports/${R_PARTIAL}/explain`);
  await sleep(500);
  await shot("22-explainability-idle-dark", `/reports/{id}/explain`, "before a question is asked", "Explainability: the grounding questions a doctor may ask about a draft.");
  try {
    const Q = "Which retrieved case supports the impression?";
    await cdp.evalJs(`(() => {
      const el = document.querySelector('form input[type=text], form input:not([type]), form textarea');
      if (!el) return false;
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, ${JSON.stringify(Q)});
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return true; })()`);
    await sleep(300);
    if (!(await cdp.evalJs(clickByText("form button", "ask")))) await cdp.evalJs(clickByText("button", "ask"));
    // The step label "Asking AI assistant" is always in the DOM, so waiting on
    // it never settles. Wait for the ANSWER exchange instead: the asked
    // question is echoed back only once status === "done".
    await until(`document.body.innerText.includes(${JSON.stringify(Q)})`, "explanation returned", 240000);
    await sleep(900);
    await shot("23-explainability-answered-dark", `/reports/{id}/explain`, "question asked and answered", "Explainability after an answer: the question and the model's grounded reply.");
  } catch (e) { log(`  ! explain: ${e.message}`); }

  // Compare -- two reports for the same patient.
  log("\n=== compare (live LLM) ===");
  try {
    await goto(`${FE}/reports/${R_FINAL}/compare?against=${R_FINAL_PREV}`);
    // Wait for the DONE state, not for a spinner word to disappear: the step
    // label is "Generating comparison", so any /comparing/ test passes while it
    // is still running. The Resolved/Persistent/New split only renders at the end.
    await until(
      `/resolved/i.test(document.body.innerText) && /persistent/i.test(document.body.innerText) && /narrative/i.test(document.body.innerText)`,
      "comparison complete", 300000);
    await sleep(900);
    await shot("24-compare-dark", `/reports/{id}/compare`, "current vs prior study", "Compare: deterministic Resolved/Persistent/New split plus an LLM narrative.");
  } catch (e) { log(`  ! compare: ${e.message}`); }

  // Print preview -- the browser's own print media, which is what the feature is.
  log("\n=== print preview ===");
  // PrintPortal is mounted by the workspace layout itself, so `.rr-print-root`
  // exists as soon as the report loads -- no control has to be pressed. What
  // makes this a *preview* is print media emulation, which is what the browser
  // would show; this feature IS browser print (there is no server-side PDF).
  await goto(`${FE}/workspace/${R_FINAL}/report`);
  await sleep(800);
  try {
    await until(`!!document.querySelector('.rr-print-root')`, "print document present", 20000);
    await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
    await sleep(500);
    await shot("25-print-preview-dark", `/workspace/{id}/report`, "print media emulation, English", "Print / Save as PDF: the printed report under print media.");
    await cdp.send("Emulation.setEmulatedMedia", { media: "" });
  } catch (e) { log(`  ! print: ${e.message}`); }

  // Settings == Profile. There is no separate /profile route in this build.
  await goto(`${FE}/settings`);
  await sleep(600);
  await shot("26-settings-profile-dark", "/settings", "profile and workspace defaults", "Settings: this build's Settings screen IS the profile screen; there is no separate /profile route.");

  // Bengali report
  log("\n=== Bengali ===");
  await setChrome({ theme: "dark", lang: "bn" });
  await goto(`${FE}/workspace/${R_BENGALI}/report`);
  await sleep(800);
  await shot("27-report-bengali-dark", `/workspace/{id}/report`, "language = bn, consistency = not_run", "A Bengali report. The consistency block reads 'not run' — the checks are English-only.");
  await setChrome({ theme: "dark", lang: "en" });

  // ------------------------------------------------------ light theme pass
  log("\n=== light theme ===");
  await setChrome({ theme: "light", lang: "en" });
  const lightPass = [
    ["28-login-light", `${FE}/login`, "/login", "signed out", "Sign in, light theme."],
    ["29-queue-light", `${FE}/dashboard`, "/dashboard", "worklist", "The queue, light theme."],
    ["30-patient-profile-light", `${FE}/patients/${PATIENT}`, `/patients/{id}`, "with prior studies", "Patient profile, light theme."],
    ["31-result-partial-light", `${FE}/workspace/${R_PARTIAL}/report`, "/workspace/{id}/report", "consistency = partial", "Result page, light theme."],
    ["32-evidence-light", `${FE}/workspace/${R_PARTIAL}/evidence`, "/workspace/{id}/evidence", "Evidence tab", "Evidence page, light theme."],
    ["33-settings-light", `${FE}/settings`, "/settings", "profile", "Settings / profile, light theme."],
  ];
  for (const [name, url, route, state, caption] of lightPass) {
    await goto(url);
    await sleep(600);
    await shot(name, route, state, caption);
  }

  writeFileSync(join(OUT, "_captured.json"), JSON.stringify(captured, null, 2));
  log(`\n${captured.length} screenshots captured into ${OUT}`);
} catch (err) {
  console.error("FAILED:", err.message);
  process.exitCode = 1;
} finally {
  try { writeFileSync(join(OUT, "_captured.json"), JSON.stringify(captured, null, 2)); } catch {}
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
