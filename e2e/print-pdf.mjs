// e2e/print-pdf.mjs
// ============================================================================
// Saves the printed report to PDF, in English and in Bengali, from the RUNNING
// app -- the same path a radiologist takes when they press "Print / Save as
// PDF" and choose Save as PDF in the browser dialog.
//
// It drives Chromium's own print pipeline (Page.printToPDF), NOT a PDF library.
// That matters for what the output is evidence OF: a PDF produced by a
// server-side renderer would prove nothing about what a doctor's browser
// actually puts on paper, and this feature is browser print by construction.
//
// The Bengali run is the one with something to prove. Noto Sans Bengali is
// self-hosted through next/font with the `bengali` subset, but "the font is
// configured" and "the conjuncts render on paper" are different claims -- a
// missing subset shows up as tofu boxes only once something rasterises it.
//
// SAFETY: picks no database. Talks to whatever E2E_API names; the caller is
// responsible for pointing that backend at a disposable copy.
//
//   E2E_API=... E2E_FRONTEND=... SHOT_EMAIL=... SHOT_PASSWORD=... \
//   PDF_REPORT_EN=<id> PDF_REPORT_BN=<id> E2E_OUT=docs/thesis/figures \
//   node e2e/print-pdf.mjs
// ============================================================================
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { cdpConnect, killTree, launchEdge, loadConfig, sleep } from "./harness.mjs";

const cfg = loadConfig();
const API = process.env.E2E_API ?? cfg.apiBase;
const FE = process.env.E2E_FRONTEND ?? cfg.frontendBase;
const OUT = process.env.E2E_OUT ?? "scratch/print-pdf";
const EMAIL = process.env.SHOT_EMAIL;
const PASSWORD = process.env.SHOT_PASSWORD;
const EN = process.env.PDF_REPORT_EN;
const BN = process.env.PDF_REPORT_BN;

for (const [k, v] of Object.entries({ SHOT_EMAIL: EMAIL, SHOT_PASSWORD: PASSWORD, PDF_REPORT_EN: EN, PDF_REPORT_BN: BN })) {
  if (!v) { console.error(`FATAL: ${k} is required`); process.exit(2); }
}

mkdirSync(OUT, { recursive: true });
const edge = launchEdge(cfg);
let cdp;

async function until(expr, what, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { if (await cdp.evalJs(expr)) return; } catch {}
    await sleep(250);
  }
  throw new Error(`timed out waiting for: ${what}`);
}

const setLang = (lang) =>
  `(() => { document.cookie = 'rr_lang=${lang}; path=/; max-age=31536000; samesite=lax'; return true; })()`;

async function savePdf(reportId, lang, name) {
  // Language is a cookie the SERVER layout reads, so it has to be set before
  // the navigation that renders the page, not after.
  await cdp.send("Page.navigate", { url: `${FE}/dashboard` });
  await until("document.readyState === 'complete'", "dashboard");
  await cdp.evalJs(setLang(lang));

  await cdp.send("Page.navigate", { url: `${FE}/reports/${reportId}` });
  await until("document.readyState === 'complete'", "report load");
  await until(`!!document.querySelector('.rr-print-root')`, "print document present");
  await until(`document.fonts.status === 'loaded'`, "webfonts settled");
  await sleep(800);

  // What the printed page will actually contain, read back before printing so
  // a blank or truncated PDF is caught here rather than by eye later.
  const probe = await cdp.evalJs(`(() => {
    const r = document.querySelector('.rr-print-root');
    const text = r.innerText || r.textContent || '';
    return JSON.stringify({
      lang: r.getAttribute('lang'),
      sections: [...r.querySelectorAll('[data-print-section]')].map(e => e.getAttribute('data-print-section')),
      chars: text.length,
      bengali: (text.match(/[\\u0980-\\u09FF]/g) || []).length,
    });
  })()`);
  const info = JSON.parse(probe);
  console.log(`  ${name}: lang=${info.lang} sections=${info.sections.length} chars=${info.chars} bengaliGlyphs=${info.bengali}`);
  console.log(`    sections: ${info.sections.join(", ")}`);

  const { data } = await cdp.send("Page.printToPDF", {
    printBackground: true,
    paperWidth: 8.27,   // A4
    paperHeight: 11.69,
    marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0, // @page owns margins
    preferCSSPageSize: true,
  });
  const path = join(OUT, name);
  writeFileSync(path, Buffer.from(data, "base64"));
  console.log(`    saved ${path}`);

  // A PNG of the same page under print media emulation. The PDF is the
  // deliverable, but a PDF cannot be eyeballed from here, and "the codepoints
  // are in the DOM" is not the same claim as "the conjuncts rasterised" -- a
  // missing font subset produces tofu with the text layer fully intact. This
  // is the same engine and the same stylesheet, rendered to something that can
  // actually be looked at.
  // The viewport has to be the PAPER's content box, not the window: print
  // emulation still lays out at the viewport width, so screenshotting a
  // 1440px-wide window and cropping to A4 shows lines running off the crop
  // that would have wrapped correctly on the real page. A4 is 210mm wide and
  // @page takes 14mm each side, leaving 182mm ~= 688px at 96dpi.
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 688, height: 1200, deviceScaleFactor: 2, mobile: false,
  });
  await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
  await sleep(500);
  const shot = await cdp.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: 688, height: 1200, scale: 1 },
  });
  const shotPath = join(OUT, name.replace(/\.pdf$/, "_preview.png"));
  writeFileSync(shotPath, Buffer.from(shot.data, "base64"));
  console.log(`    saved ${shotPath}`);
  await cdp.send("Emulation.setEmulatedMedia", { media: "" });
  await cdp.send("Emulation.clearDeviceMetricsOverride");

  return info;
}

try {
  cdp = await cdpConnect(cfg.cdpPort);
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");

  const res = await fetch(`${API}/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status}`);
  const jwt = (res.headers.getSetCookie().find((c) => c.startsWith("radassist_token=")) || "").split(";")[0].split("=")[1];
  await cdp.send("Network.setCookie", { name: "radassist_token", value: jwt, domain: "localhost", path: "/", httpOnly: true, secure: false, sameSite: "Lax" });

  console.log("\nprinting:");
  const en = await savePdf(EN, "en", "report_print_en.pdf");
  const bn = await savePdf(BN, "bn", "report_print_bn.pdf");

  let bad = 0;
  if (en.sections.length < 9) { console.error("FAIL: English PDF is missing sections"); bad++; }
  if (bn.sections.length < 9) { console.error("FAIL: Bengali PDF is missing sections"); bad++; }
  if (bn.bengali < 100) { console.error(`FAIL: Bengali page carries only ${bn.bengali} Bengali codepoints`); bad++; }
  console.log(bad === 0 ? "\nboth PDFs written and non-empty." : `\n${bad} problem(s).`);
  process.exitCode = bad === 0 ? 0 : 1;
} catch (err) {
  console.error("FAILED:", err.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close(); } catch {}
  killTree(edge.pid);
}
