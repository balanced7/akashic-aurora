// Smoke test: the lab page boots, sizes its buffer to the canvas box, and renders without errors.
import { writeFileSync } from "node:fs";
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "./cdp.mjs";

const [W, H, DPR, PORT] = [Number(process.argv[2] || 1280), Number(process.argv[3] || 900), process.argv[4] && process.argv[4] !== "1" ? Number(process.argv[4]) : null, Number(process.argv[5] || 9601)];
const URL = process.argv[6] || "http://127.0.0.1:8793/web/piano-lab-res.html";
const OUT = new URL_("./out/", import.meta.url);
function URL_(p, base) { return new globalThis.URL(p, base); }
const b = await launch({ port: PORT, width: W, height: H, dpr: DPR });
try {
  await b.page.send("Page.navigate", { url: URL });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await delay(2500);
  const res = await b.evaluate("window.__piano.lab.res()");
  console.log("res", JSON.stringify(res));
  console.log("gpu", JSON.stringify(await b.evaluate("window.__piano.gpu()")));
  await b.evaluate("document.getElementById('btn-demo').click()");
  await delay(3000);
  console.log("stats", JSON.stringify(await b.evaluate("(() => { const s = window.__piano.stats(); return { fps: s.fps, chord: s.chord, label: s.label, trails: s.trailsLive }; })()")));
  const snap = await b.evaluate("(async () => { const u = window.__piano.snapshot(); const i = new Image(); i.src = u; await i.decode(); return [i.width, i.height, u.length]; })()");
  console.log("snapshot framing", JSON.stringify(snap));
  const nat = await b.evaluate("(async () => { const u = window.__piano.snapshot({ native: true }); const i = new Image(); i.src = u; await i.decode(); return [i.width, i.height]; })()");
  console.log("snapshot native", JSON.stringify(nat));
  console.log("res after", JSON.stringify(await b.evaluate("window.__piano.lab.res()")));
  const shot = await b.page.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/res-lab/smoke-${W}x${H}-${DPR || 1}.png`, Buffer.from(shot.data, "base64"));
  console.log("errors", JSON.stringify(b.errors));
} catch (e) {
  console.log("FATAL", e.stack || e, JSON.stringify(b.errors));
} finally {
  await b.close();
  process.exit(0);
}
