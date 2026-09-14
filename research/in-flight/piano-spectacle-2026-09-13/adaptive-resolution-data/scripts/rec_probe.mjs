// Recording at framing size: records 4 s through the lab's real REC path (no upload) at several REC render scales,
// saves each file, and measures frame cost at 1080x1920 for the candidate pipelines.
// usage: node rec_probe.mjs <port> [9:16|16:9]
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "./cdp.mjs";

const PORT = Number(process.argv[2] || 9604);
const FRAMING = process.argv[3] || "9:16";
const OUT = join("C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/res-lab/runs", `rec-${FRAMING.replace(":", "x")}`);
mkdirSync(OUT, { recursive: true });
const b = await launch({ port: PORT, width: 1600, height: 1000 });
const report = { framing: FRAMING, costs: [], recordings: [] };
try {
  await b.page.send("Page.navigate", { url: "http://127.0.0.1:8793/web/piano-lab-res.html" });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await delay(1500);
  if (FRAMING === "16:9") { await b.evaluate("document.getElementById('btn-169').click()"); await delay(600); }
  report.liveBefore = await b.evaluate("window.__piano.lab.res()");

  if (process.argv[4] !== "reconly") {
  // frame cost at the recording size, on a busy frozen frame (the demo's lush chord mid-phrase)
  await b.evaluate("document.getElementById('btn-demo').click()");
  await delay(5200);
  await b.evaluate("window.__piano.lab.freeze(performance.now() / 1000 - 0), window.__piano.lab.set({ paused: true })");
  const COST = [
    { id: "HEAD 1x MSAA4", set: { fixed: true, recScale: 1, msaa: 4 } },
    { id: "1x MSAA8", set: { fixed: true, recScale: 1, msaa: 8 } },
    { id: "1.5x box", set: { fixed: true, recScale: 1.5, msaa: 0 } },
    { id: "1.5x box + MSAA4", set: { fixed: true, recScale: 1.5, msaa: 4 } },
    { id: "2x box", set: { fixed: true, recScale: 2, msaa: 0 } },
    { id: "2x box + MSAA4", set: { fixed: true, recScale: 2, msaa: 4 } },
    { id: "TAA x4 (1x)", set: { fixed: true, recScale: 1, msaa: 0, aa: "taa", taaLevel: 2 } },
    { id: "SMAA (1x)", set: { fixed: true, recScale: 1, msaa: 0, aa: "smaa" } },
  ];
  for (const c of COST) {
    const r = await b.evaluate(`window.__piano.lab.set(${JSON.stringify({ aa: "none", ...c.set })})`);
    await b.evaluate("window.__piano.lab.bench(15), 0");
    const runs = [];
    for (let k = 0; k < 3; k++) runs.push(await b.evaluate("window.__piano.lab.bench(60)"));
    const med = runs.map((x) => x.median).sort((a, b) => a - b)[1];
    const p95 = Math.max(...runs.map((x) => x.p95));
    report.costs.push({ id: c.id, buffer: r.buffer, internal: r.internal, msaa: r.composerSamples, medianMs: med, worstP95Ms: p95, runs });
    console.log("cost", c.id.padEnd(18), JSON.stringify({ int: `${r.internal.w}x${r.internal.h}`, med, p95 }));
  }
  await b.evaluate("window.__piano.lab.set({ aa: 'none', fixed: false, msaa: 4, recScale: 1, paused: false }), window.__piano.lab.unfreeze(), 0");
  await delay(800);
  }

  // real recordings through startRecording(): the live loop runs, the demo plays
  const RECS = process.argv[4] === "reconly" ? [{ recScale: 2, msaa: 4 }, { recScale: 1, msaa: 4 }, { recScale: 2, msaa: 4 }]
                                             : [{ recScale: 1, msaa: 4 }, { recScale: 1.5, msaa: 4 }, { recScale: 2, msaa: 4 }];
  for (const [k, rc] of RECS.entries()) {
    await b.evaluate(`window.__piano.lab.set(${JSON.stringify(rc)})`);
    await b.evaluate("(() => { const d = document.getElementById('btn-demo'); if (d.getAttribute('aria-pressed') !== 'true') d.click(); return 1; })()");
    await delay(500);
    // the file stays in the page and comes back in 1 MB slices: one multi-megabyte CDP reply hung the first probe
    const r = await b.evaluate("window.__piano.lab.record(4).then((x) => { window.__recB64 = x.b64; delete x.b64; return x; })");
    const len = await b.evaluate("window.__recB64.length");
    const parts = [];
    for (let i = 0; i < len; i += 1 << 20) parts.push(await b.evaluate(`window.__recB64.slice(${i}, ${i + (1 << 20)})`));
    const ext = /mp4/.test(r.mime) ? "mp4" : "webm";
    const file = join(OUT, `rec-${k}-scale${rc.recScale}-msaa${rc.msaa}.${ext}`);
    writeFileSync(file, Buffer.from(parts.join(""), "base64"));
    const live = await b.evaluate("window.__piano.lab.res()");
    report.recordings.push({ ...rc, file, ...r, liveAfter: { output: live.output, internal: live.internal } });
    console.log("rec", JSON.stringify({ ...rc, mime: r.mime, bytes: r.bytes, frames: r.frames, seconds: r.seconds, settings: r.settings, during: r.during, after: live.output }));
    await delay(1500);
  }
} catch (e) {
  report.fatal = String(e.stack || e);
  console.log("FATAL", report.fatal);
} finally {
  report.errors = b.errors;
  writeFileSync(join(OUT, "rec-probe.json"), JSON.stringify(report, null, 2));
  console.log("errors", JSON.stringify(b.errors));
  await b.close();
  process.exit(0);
}
