// Final sizing check on the final lab code: framings, the live pixel cap, a runtime DPR change and a resize.
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "./cdp.mjs";
const b = await launch({ port: 9601, width: 2560, height: 1440 });
const pick = (r) => ({ display: `${r.display.w}x${r.display.h}`, buffer: r.buffer.join("x"), scene: `${r.internal.w}x${r.internal.h}`, msaa: r.composerSamples, downsample: r.downsample, dpr: r.dpr, css: r.css.join(" x "), framing: r.framing });
const step = async (name) => {
  const r = await b.evaluate("window.__piano.lab.res()");
  await b.evaluate("document.getElementById('hud').hidden = false, 0"); await delay(300);
  const hud = await b.evaluate("document.getElementById('hud-render').textContent");
  await b.evaluate("document.getElementById('hud').hidden = true, 0");
  // is the buffer shown 1:1? compare a screenshot crop with the buffer read back directly
  const exact = await b.evaluate(`(async () => {
    const L = window.__piano.lab; await L.set({ paused: true });
    const direct = L.grab();
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    window.__direct = direct; return 1; })()`);
  const rect = await b.evaluate("(() => { const r = document.getElementById('piano-canvas').getBoundingClientRect(); return { x: r.x, y: r.y, dpr: devicePixelRatio }; })()");
  const shot = (await b.page.send("Page.captureScreenshot", { format: "png" })).data;
  const mae = await b.evaluate(`(async () => {
    const d = window.__direct, img = new Image(); img.src = "data:image/png;base64,${shot}"; await img.decode();
    let best = 1;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const c = document.createElement("canvas"); c.width = d.w; c.height = d.h;
      const g = c.getContext("2d"); g.drawImage(img, -(Math.round(${rect.x} * ${rect.dpr}) + dx), -(Math.round(${rect.y} * ${rect.dpr}) + dy));
      const s = g.getImageData(0, 0, d.w, d.h).data; let sum = 0;
      for (let i = 0; i < s.length; i += 4) sum += Math.abs(s[i] - d.data[i]) + Math.abs(s[i + 1] - d.data[i + 1]) + Math.abs(s[i + 2] - d.data[i + 2]);
      best = Math.min(best, sum / (d.w * d.h * 3 * 255));
    }
    await window.__piano.lab.set({ paused: false }); return best; })()`);
  console.log(name.padEnd(34), JSON.stringify({ ...pick(r), screenshotVsBufferMAE: +mae.toFixed(6), hud }));
};
try {
  await b.page.send("Page.navigate", { url: "http://127.0.0.1:8793/web/piano-lab-res.html" });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await b.evaluate("document.getElementById('btn-demo').click(), 0");
  await delay(2500);
  await step("2560x1440 dpr1 9:16");
  await b.evaluate("document.getElementById('btn-169').click(), 0"); await delay(1200);
  await step("2560x1440 dpr1 16:9 (over live cap)");
  await b.evaluate("document.getElementById('btn-916').click(), 0"); await delay(1200);
  await b.page.send("Emulation.setDeviceMetricsOverride", { width: 2560, height: 1440, deviceScaleFactor: 1.5, mobile: false });
  await delay(1500);
  await step("runtime DPR 1 -> 1.5, 9:16");
  await b.page.send("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
  await delay(1500);
  await step("resize to 1600x1000 dpr1, 9:16");
  const snap = await b.evaluate("(async () => { const u = window.__piano.snapshot(); const i = new Image(); i.src = u; await i.decode(); return [i.width, i.height]; })()");
  console.log("snapshot() size", JSON.stringify(snap), "res after", JSON.stringify(pick(await b.evaluate("window.__piano.lab.res()"))));
  console.log("stats", JSON.stringify(await b.evaluate("(() => { const s = window.__piano.stats(); return { fps: s.fps, chord: s.chord, rec: s.rec }; })()")));
} catch (e) { console.log("FATAL", e.stack || e); }
finally { console.log("errors", JSON.stringify(b.errors)); await b.close(); process.exit(0); }
