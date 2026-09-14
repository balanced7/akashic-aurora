// Judge control: three 4 s takes through HEAD's own (unmodified) recording path, in a fresh headless page,
// with the upload fetch intercepted in the page so nothing is POSTed to the server.
// usage: node head_rec_control.mjs <port> <url> <outdir>
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "file:///E:/AI-Setup/research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-data/scripts/cdp.mjs";

const PORT = Number(process.argv[2] || 9631);
const URL_ = process.argv[3] || "http://127.0.0.1:8793/web/piano-lab-judge-head.html";
const OUT = process.argv[4];
mkdirSync(OUT, { recursive: true });
const INTERCEPT = `(() => {
  const real = window.fetch.bind(window);
  window.__recDone = false;
  window.fetch = async (input, init) => {
    const u = typeof input === "string" ? input : input.url;
    if (u.includes("/api/recordings")) {
      const blob = init.body;
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = "";
      for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      window.__recB64 = btoa(bin);
      window.__recMime = blob.type;
      window.__recDone = true;
      return new Response(JSON.stringify({ path: "intercepted-by-judge", bytes: buf.length }), { status: 200 });
    }
    if (u.includes("/api/")) return new Response("{}", { status: 200 });  // no other API writes either
    return real(input, init);
  };
})();`;

const b = await launch({ port: PORT, width: 1600, height: 1000 });
const report = { url: URL_, takes: [] };
try {
  await b.page.send("Page.addScriptToEvaluateOnNewDocument", { source: INTERCEPT });
  await b.page.send("Page.navigate", { url: URL_ });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await delay(1500);
  await b.evaluate("(() => { const d = document.getElementById('btn-demo'); if (d.getAttribute('aria-pressed') !== 'true') d.click(); return 1; })()");
  await delay(500);
  for (let k = 0; k < 3; k++) {
    await b.evaluate("window.__recDone = false, 0");
    await b.evaluate("document.getElementById('btn-rec').click(), 0");
    await delay(200);
    const recording = await b.evaluate("document.getElementById('btn-rec').getAttribute('aria-pressed')");
    await delay(3800);
    const fps = await b.evaluate("window.__piano.stats().fps");
    await b.evaluate("document.getElementById('btn-rec').click(), 0");
    await waitFor(() => b.evaluate("window.__recDone === true"), 20000, "upload intercept");
    const len = await b.evaluate("window.__recB64.length");
    const parts = [];
    for (let i = 0; i < len; i += 1 << 20) parts.push(await b.evaluate(`window.__recB64.slice(${i}, ${i + (1 << 20)})`));
    const mime = await b.evaluate("window.__recMime");
    const file = join(OUT, `rec-${k}-head.${/mp4/.test(mime) ? "mp4" : "webm"}`);
    writeFileSync(file, Buffer.from(parts.join(""), "base64"));
    report.takes.push({ k, recording, fps, mime, file });
    console.log("take", k, recording, fps, mime, file);
    await delay(1500);
  }
} catch (e) {
  report.fatal = String(e.stack || e);
  console.log("FATAL", report.fatal);
} finally {
  report.errors = b.errors;
  writeFileSync(join(OUT, "head-control.json"), JSON.stringify(report, null, 2));
  console.log("errors", JSON.stringify(b.errors));
  await b.close();
  process.exit(0);
}
