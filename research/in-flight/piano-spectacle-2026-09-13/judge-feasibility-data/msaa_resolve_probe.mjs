// Judge experiment: at REC size (1080x1920 output, 2160x3840 scene, MSAA 4) does dropping MSAA from the composer's
// second target (only OutputPass writes it when the downsample runs) cut frame cost without changing a pixel?
import { writeFileSync } from "node:fs";
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "file:///E:/AI-Setup/research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-data/scripts/cdp.mjs";
const BEAT = 0.75, BAR = 3.0;
const PROG = [ { bass: 45, arp: [53, 57, 60, 65, 69, 65, 60, 57], mel: [77, 76] }, { bass: 43, arp: [52, 55, 60, 64, 67, 64, 60, 55], mel: [76, 74] } ];
const events = [];
const on = (t, n, v, len) => { events.push({ t, b: [0x90, n, v] }); events.push({ t: t + len, b: [0x80, n, 0] }); };
const pedal = (t, down) => events.push({ t, b: [0xb0, 64, down ? 127 : 0] });
for (let bar = 0; bar < 2; bar++) { const t = 0.2 + bar * BAR, c = PROG[bar]; if (bar > 0) pedal(t - 0.05, false); pedal(t + 0.08, true);
  on(t, c.bass, 95, BEAT * 1.5); c.arp.forEach((n, i) => on(t + i * BEAT / 2, n, 58 + ((i * 17 + bar * 7) % 26), 0.3));
  on(t, c.mel[0], 100, 1.4); on(t + 2 * BEAT, c.mel[1], 88, 1.4); }
pedal(6.15, false); [41, 53, 57, 60, 65, 69, 72, 77].forEach((n, i) => on(6.2 + i * 0.03, n, 110, 2.0)); pedal(6.3, true);
const b = await launch({ port: 9633, width: 1600, height: 1000 });
const out = { runs: [] };
try {
  await b.page.send("Page.navigate", { url: "http://127.0.0.1:8793/web/piano-lab-judge-res.html" });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await delay(1500);
  await b.evaluate("window.__piano.lab.seed(20260913)");
  out.sim = await b.evaluate(`window.__piano.lab.sim(${JSON.stringify(events)}, 6.65)`);
  const order = [["2x MSAA4, rt1 MSAA4 (lab as shipped)", 4, 4], ["2x MSAA4, rt1 no MSAA", 4, 0], ["2x MSAA4, rt1 MSAA4 (lab as shipped)", 4, 4], ["2x MSAA4, rt1 no MSAA", 4, 0], ["2x no MSAA", 0, 0], ["1x MSAA4 fixed (HEAD-equivalent)", 4, 4]];
  for (const [id, msaa, rt1] of order) {
    const scale = id.startsWith("1x") ? 1 : 2;
    const res = await b.evaluate(`(window.__judgeRt1 = ${rt1}, window.__piano.lab.set({ paused: true, fixed: true, recScale: ${scale}, msaa: ${msaa} }))`);
    await b.evaluate("window.__piano.lab.bench(15), 0");
    const runs = []; for (let k = 0; k < 3; k++) runs.push(await b.evaluate("window.__piano.lab.bench(60)"));
    let pix = null;
    if (scale === 2 && msaa === 4) pix = await b.evaluate(`(() => { const g = window.__piano.lab.grab(); if (!window.__gA) { window.__gA = g; return { ref: true, w: g.w, h: g.h }; }
      const a = window.__gA.data, d = g.data; let s = 0, mx = 0, n = 0; for (let i = 0; i < d.length; i += 4) for (let c = 0; c < 3; c++) { const e = Math.abs(a[i+c] - d[i+c]); s += e; if (e > mx) mx = e; n++; }
      return { mae: s / n / 255, maxAbs: mx, w: g.w, h: g.h }; })()`);
    const row = { id, internal: res.internal, output: res.output, samples: res.composerSamples, medians: runs.map((r) => r.median), p95s: runs.map((r) => r.p95), pix };
    out.runs.push(row); console.log(JSON.stringify(row));
  }
} catch (e) { out.fatal = String(e.stack || e); console.log("FATAL", out.fatal); }
finally { out.errors = b.errors; writeFileSync("msaa-resolve-probe.json", JSON.stringify(out, null, 2)); console.log("errors", JSON.stringify(b.errors)); await b.close(); process.exit(0); }
