// Targeted re-capture of 24-compare-dark.png only.
// The first pass shot it mid-run: the waiting condition tested for the word
// "comparing", but the step label is "Generating comparison", so it never
// matched and the screenshot was taken while the LLM was still working.
// This waits for the Resolved/Persistent/New split, which only renders at the end.
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "../../e2e/harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API;
const FE = process.env.E2E_FRONTEND;
const OUT = process.env.E2E_OUT;
const R_FINAL = "1109f7553a294ae390fbb7b8b3f8ff29";
const R_FINAL_PREV = "efeb8016cc0c4764918779eb3545e1be";

mkdirSync(OUT, { recursive: true });
const edge = launchEdge({ ...cfg, cdpPort: cfg.cdpPort });
let cdp;
try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const res = await fetch(`${API}/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: process.env.SHOT_EMAIL, password: process.env.SHOT_PASSWORD }),
  });
  const jwt = ((res.headers.getSetCookie?.() ?? []).find((c) => c.startsWith("radassist_token=")) || "")
    .split(";")[0].split("=")[1];
  await cdp.send("Network.setCookie", {
    name: "radassist_token", value: jwt, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax",
  });

  await cdp.send("Page.navigate", { url: `${FE}/dashboard` });
  await sleep(1200);
  await cdp.evalJs(`(() => { document.cookie = 'rr_theme=dark; path=/; max-age=31536000; samesite=lax'; document.cookie = 'rr_lang=en; path=/; max-age=31536000; samesite=lax'; return true; })()`);

  await cdp.send("Page.navigate", { url: `${FE}/reports/${R_FINAL}/compare?against=${R_FINAL_PREV}` });
  const deadline = Date.now() + 300000;
  let ready = false;
  while (Date.now() < deadline && !ready) {
    try {
      ready = await cdp.evalJs(
        `/resolved/i.test(document.body.innerText) && /persistent/i.test(document.body.innerText) && /narrative/i.test(document.body.innerText)`);
    } catch {}
    if (!ready) await sleep(500);
  }
  if (!ready) throw new Error("comparison never completed");
  await sleep(1000);
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png", clip: { x: 0, y: 0, width: 1440, height: 900, scale: 1 },
  });
  writeFileSync(join(OUT, "24-compare-dark.png"), Buffer.from(data, "base64"));
  console.log("  ✓ 24-compare-dark.png (completed state)");
} catch (e) {
  console.error("FAILED:", e.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
