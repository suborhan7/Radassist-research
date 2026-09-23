// Targeted re-capture of 17-*.png.
// The first pass shot the below-floor report's REPORT page, where no retrieval
// support notice renders -- that notice lives on the Evidence page's Agreement
// tab (see 20-evidence-tab-agreement-dark.png, "RETRIEVAL SUPPORT / Met").
// Shooting the report page therefore produced a duplicate of 16, not the
// below-floor state. This captures the Agreement tab of the below-floor report,
// which is where the state is actually visible.
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "../../e2e/harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API, FE = process.env.E2E_FRONTEND, OUT = process.env.E2E_OUT;
const R_BELOWFLOOR = "30fe6afa91f744f2a6a99f63af1b1902";

mkdirSync(OUT, { recursive: true });
const edge = launchEdge({ ...cfg, cdpPort: cfg.cdpPort });
let cdp;
const clickByText = (sel, text) => `(() => {
  const el = [...document.querySelectorAll(${JSON.stringify(sel)})]
    .find(e => ((e.textContent||'')+' '+(e.getAttribute('aria-label')||'')).toLowerCase().includes(${JSON.stringify(text.toLowerCase())}));
  if (!el || el.disabled) return false; el.click(); return true; })()`;

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable"); await cdp.send("Network.enable");
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
  await sleep(1500);
  await cdp.evalJs(`(() => { document.cookie='rr_theme=dark; path=/; max-age=31536000; samesite=lax'; document.cookie='rr_lang=en; path=/; max-age=31536000; samesite=lax'; return true; })()`);

  await cdp.send("Page.navigate", { url: `${FE}/workspace/${R_BELOWFLOOR}/evidence` });
  await sleep(2500);
  if (!(await cdp.evalJs(clickByText("button", "agreement")))) throw new Error("no Agreement tab");
  await sleep(900);
  const txt = await cdp.evalJs("document.body.innerText");
  if (!/retrieval support/i.test(txt)) throw new Error("retrieval support block not rendered");
  console.log("  retrieval-support block present");
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png", clip: { x: 0, y: 0, width: 1440, height: 900, scale: 1 },
  });
  writeFileSync(join(OUT, "17-evidence-below-floor-dark.png"), Buffer.from(data, "base64"));
  console.log("  ✓ 17-evidence-below-floor-dark.png");
} catch (e) {
  console.error("FAILED:", e.message); process.exitCode = 1;
} finally { try { cdp?.close(); } catch {} killTree(edge.pid); }
