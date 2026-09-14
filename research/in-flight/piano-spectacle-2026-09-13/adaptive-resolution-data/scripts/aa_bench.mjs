// Anti-aliasing comparison on one frozen frame of the lab piano, at the canvas's native (adaptive) resolution.
// usage: node aa_bench.mjs <width> <height> <dpr|1> <port> <9:16|16:9> <label>
//   1. plays a fixed pedalled phrase on a scripted 60 fps clock (seeded sparks), freezes the clock
//   2. reference: the scene at 4x per axis (16 samples a pixel), tone mapped, box-averaged in linear light
//   3. every config: MAE vs the reference, MAE on edge pixels, PSNR, temporal shimmer over a slow camera pan,
//      frame cost (GPU-synchronised), and a PNG of the still
//   4. display path: page screenshots (what the compositor shows) for HEAD's fixed 1080x1920 buffer vs adaptive
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { launch, waitFor } from "./cdp.mjs";

const W = Number(process.argv[2] || 1280), H = Number(process.argv[3] || 900);
const DPR = process.argv[4] && process.argv[4] !== "1" ? Number(process.argv[4]) : null;
const PORT = Number(process.argv[5] || 9601);
const FRAMING = process.argv[6] || "9:16";
const LABEL = process.argv[7] || `${W}x${H}-dpr${DPR || 1}-${FRAMING.replace(":", "x")}`;
const APP = "http://127.0.0.1:8793/web/piano-lab-res.html";
const OUT = join("C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/res-lab/runs", LABEL);
mkdirSync(OUT, { recursive: true });
const PAN_FRAMES = 12;
const PAN_PX = 0.37;  // camera pan per frame, in output pixels at the key line

// the phrase: two pedalled bars (F/A, C/G) with arpeggios and melody, then a loud spread F chord; freeze 0.4 s in
const BEAT = 0.75, BAR = 3.0;
const PROG = [
  { bass: 45, arp: [53, 57, 60, 65, 69, 65, 60, 57], mel: [77, 76] },
  { bass: 43, arp: [52, 55, 60, 64, 67, 64, 60, 55], mel: [76, 74] },
];
const events = [];
const on = (t, n, v, len) => { events.push({ t, b: [0x90, n, v] }); events.push({ t: t + len, b: [0x80, n, 0] }); };
const pedal = (t, down) => events.push({ t, b: [0xb0, 64, down ? 127 : 0] });
for (let bar = 0; bar < 2; bar++) {
  const t = 0.2 + bar * BAR, c = PROG[bar];
  if (bar > 0) pedal(t - 0.05, false);
  pedal(t + 0.08, true);
  on(t, c.bass, 95, BEAT * 1.5);
  c.arp.forEach((n, i) => on(t + i * BEAT / 2, n, 58 + ((i * 17 + bar * 7) % 26), 0.3));
  on(t, c.mel[0], 100, 1.4);
  on(t + 2 * BEAT, c.mel[1], 88, 1.4);
}
pedal(6.15, false);
[41, 53, 57, 60, 65, 69, 72, 77].forEach((n, i) => on(6.2 + i * 0.03, n, 110, 2.0));
pedal(6.3, true);
const T_FREEZE = 6.65;

const CONFIGS = [
  { id: "none", scale: 1, msaa: 0 },
  { id: "msaa4", scale: 1, msaa: 4 },
  { id: "msaa8", scale: 1, msaa: 8 },
  { id: "fxaa", scale: 1, msaa: 0, aa: "fxaa" },
  { id: "smaa", scale: 1, msaa: 0, aa: "smaa" },
  { id: "smaa+msaa4", scale: 1, msaa: 4, aa: "smaa" },
  { id: "taa-x4", scale: 1, msaa: 0, aa: "taa", taaLevel: 2 },
  { id: "taa-x8", scale: 1, msaa: 0, aa: "taa", taaLevel: 3 },
  { id: "ss1.5-box", scale: 1.5, msaa: 0, filter: "box" },
  { id: "ss1.5-tent", scale: 1.5, msaa: 0, filter: "tent" },
  { id: "ss1.5-box+msaa4", scale: 1.5, msaa: 4, filter: "box" },
  { id: "ss2-box", scale: 2, msaa: 0, filter: "box" },
  { id: "ss2-tent", scale: 2, msaa: 0, filter: "tent" },
  { id: "ss2-box+msaa4", scale: 2, msaa: 4, filter: "box" },
];

// in-page metrics: the frames stay in the page, only numbers come back
const METRICS = `window.__M = {
  refs: [], masks: [],
  mask(img) {
    const { w, h, data } = img, L = new Float32Array(w * h), m = new Uint8Array(w * h), out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) L[i] = (0.2126 * data[i * 4] + 0.7152 * data[i * 4 + 1] + 0.0722 * data[i * 4 + 2]) / 255;
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      const gx = L[i - w + 1] + 2 * L[i + 1] + L[i + w + 1] - L[i - w - 1] - 2 * L[i - 1] - L[i + w - 1];
      const gy = L[i + w - 1] + 2 * L[i + w] + L[i + w + 1] - L[i - w - 1] - 2 * L[i - w] - L[i - w + 1];
      if (Math.hypot(gx, gy) > 0.25) m[i] = 1;
    }
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      out[i] = m[i] | m[i - 1] | m[i + 1] | m[i - w] | m[i + w];
    }
    return out;
  },
  cmp(ref, img, mask) {
    const n = ref.w * ref.h; let s = 0, e = 0, en = 0, sq = 0;
    for (let i = 0; i < n; i++) {
      const d = Math.abs(ref.data[i * 4] - img.data[i * 4]) + Math.abs(ref.data[i * 4 + 1] - img.data[i * 4 + 1]) + Math.abs(ref.data[i * 4 + 2] - img.data[i * 4 + 2]);
      s += d;
      sq += (ref.data[i * 4] - img.data[i * 4]) ** 2 + (ref.data[i * 4 + 1] - img.data[i * 4 + 1]) ** 2 + (ref.data[i * 4 + 2] - img.data[i * 4 + 2]) ** 2;
      if (mask[i]) { e += d; en++; }
    }
    const mse = sq / (n * 3);
    return { mae: s / (n * 3 * 255), edgeMae: en ? e / (en * 3 * 255) : 0, psnr: 10 * Math.log10(255 * 255 / Math.max(mse, 1e-9)), edgeShare: en / n };
  },
  // shimmer: how much the error against the reference changes from one pan frame to the next
  shimmer(frames) {
    const n = frames[0].w * frames[0].h; let s = 0, se = 0, sen = 0, motion = 0;
    let prev = null;
    for (let f = 0; f < frames.length; f++) {
      const img = frames[f], ref = this.refs[f], e = new Int16Array(n * 3);
      for (let i = 0; i < n; i++) for (let c = 0; c < 3; c++) e[i * 3 + c] = img.data[i * 4 + c] - ref.data[i * 4 + c];
      if (prev) {
        const m0 = this.masks[f], m1 = this.masks[f - 1], r0 = this.refs[f - 1];
        for (let i = 0; i < n; i++) {
          let d = 0, dm = 0;
          for (let c = 0; c < 3; c++) { d += Math.abs(e[i * 3 + c] - prev[i * 3 + c]); dm += Math.abs(ref.data[i * 4 + c] - r0.data[i * 4 + c]); }
          s += d; motion += dm;
          if (m0[i] | m1[i]) { se += d; sen++; }
        }
      }
      prev = e;
    }
    const pairs = frames.length - 1;
    return { shimmer: s / (pairs * n * 3 * 255), edgeShimmer: sen ? se / (sen * 3 * 255) : 0, refMotion: motion / (pairs * n * 3 * 255) };
  },
};`;

const b = await launch({ port: PORT, width: W, height: H, dpr: DPR });
const report = { at: new Date().toISOString(), window: [W, H], dpr: DPR || 1, framing: FRAMING, label: LABEL, configs: [], display: [] };
const f4 = (x) => +x.toFixed(5);
try {
  await b.page.send("Page.navigate", { url: APP });
  await waitFor(() => b.evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "ready");
  await waitFor(() => b.evaluate("window.__piano.stats().fonts.text && window.__piano.stats().fonts.smufl"), 15000, "fonts").catch(() => {});
  if (FRAMING === "16:9") { await b.evaluate("document.getElementById('btn-169').click()"); await delay(600); }
  await delay(1000);
  report.gpu = await b.evaluate("window.__piano.gpu()");
  await b.evaluate(METRICS);
  await b.evaluate("window.__piano.lab.seed(20260913)");
  report.sim = await b.evaluate(`window.__piano.lab.sim(${JSON.stringify(events)}, ${T_FREEZE})`);
  const base = await b.evaluate("window.__piano.lab.set({ paused: true, hideOverlay: true, scale: 1, msaa: 4, pan: 0 })");
  report.native = base;
  const pxPerWu = base.output.w / (FRAMING === "16:9" ? 57 : base.cam.span);
  const panStep = PAN_PX / pxPerWu;
  report.pan = { frames: PAN_FRAMES, pxPerFrame: PAN_PX, worldPerFrame: f4(panStep) };
  console.log(LABEL, "native", JSON.stringify(base.output), "sim", JSON.stringify(report.sim), "panStep", panStep.toFixed(5));

  // ---------------------------------------------------------------- reference --
  const refRes = await b.evaluate(`window.__piano.lab.set({ scale: 4, msaa: 0, filter: "box", aa: "none", maxInternal: 90e6 })`);
  report.reference = { internal: refRes.internal, output: refRes.output };
  await b.evaluate("window.__piano.lab.grab(), 0");
  await b.evaluate(`(async () => {
    const L = window.__piano.lab;
    for (let f = 0; f < ${PAN_FRAMES}; f++) {
      await L.set({ pan: f * ${panStep} });
      const img = L.grab();
      __M.refs.push(img);
      __M.masks.push(__M.mask(img));
    }
    await L.set({ pan: 0 });
    return __M.refs.length;
  })()`);
  const refPng = await b.evaluate("window.__piano.snapshot({ native: true, png: true })");
  writeFileSync(join(OUT, "reference.png"), Buffer.from(refPng.split(",")[1], "base64"));
  console.log("reference", JSON.stringify(refRes.internal));

  // ------------------------------------------------------------------ configs --
  for (const c of CONFIGS) {
    const set = { scale: c.scale, msaa: c.msaa, filter: c.filter || "box", aa: c.aa || "none", taaLevel: c.taaLevel || 2, maxInternal: 90e6, pan: 0 };
    const r = await b.evaluate(`window.__piano.lab.set(${JSON.stringify(set)})`);
    const m = await b.evaluate(`(async () => {
      const L = window.__piano.lab;
      L.grab(); L.grab();
      const still = __M.cmp(__M.refs[0], L.grab(), __M.masks[0]);
      const frames = [];
      for (let f = 0; f < ${PAN_FRAMES}; f++) { await L.set({ pan: f * ${panStep} }); frames.push(L.grab()); }
      const sh = __M.shimmer(frames);
      await L.set({ pan: 0 });
      L.bench(10);
      const cost = L.bench(40);
      return { still, sh, cost };
    })()`);
    const png = await b.evaluate("window.__piano.snapshot({ native: true, png: true })");
    writeFileSync(join(OUT, `${c.id}.png`), Buffer.from(png.split(",")[1], "base64"));
    const row = { id: c.id, internal: r.internal, output: r.output, msaa: r.composerSamples, aa: r.aa,
                  mae: f4(m.still.mae), edgeMae: f4(m.still.edgeMae), psnr: +m.still.psnr.toFixed(2), edgeShare: f4(m.still.edgeShare),
                  shimmer: f4(m.sh.shimmer), edgeShimmer: f4(m.sh.edgeShimmer), refMotion: f4(m.sh.refMotion), cost: m.cost };
    report.configs.push(row);
    console.log(c.id.padEnd(16), JSON.stringify({ int: `${r.internal.w}x${r.internal.h}`, mae: row.mae, edge: row.edgeMae, psnr: row.psnr, shim: row.shimmer, eshim: row.edgeShimmer, ms: m.cost.median, p95: m.cost.p95 }));
  }

  // ------------------------------------------------------------- display path --
  // What the compositor shows: HEAD's fixed framing-size buffer (browser-scaled) vs the adaptive buffer, overlay on.
  await b.evaluate(`window.__piano.lab.set({ aa: "none", hideOverlay: false, pan: 0 })`);
  // reference with the overlay, drawn at native size after the 4x scene
  await b.evaluate(`(async () => {
    const L = window.__piano.lab;
    await L.set({ scale: 4, msaa: 0, filter: "box", fixed: false });
    __M.drefs = [];
    for (let f = 0; f < ${PAN_FRAMES}; f++) { await L.set({ pan: f * ${panStep} }); const img = L.grab(); __M.drefs.push(img); }
    __M.dmasks = __M.drefs.map((i) => __M.mask(i));
    await L.set({ pan: 0 });
    return 1;
  })()`);
  const rect = await b.evaluate("(() => { const r = document.getElementById('piano-canvas').getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, dpr: devicePixelRatio }; })()");
  const DISPLAY = [
    { id: "HEAD-fixed-1080x1920-msaa4", set: { fixed: true, recScale: 1, msaa: 4, scale: 1 } },
    { id: "adaptive-msaa4", set: { fixed: false, msaa: 4, scale: 1 } },
    { id: "adaptive-ss2-box", set: { fixed: false, msaa: 0, scale: 2, filter: "box" } },
    { id: "adaptive-ss1.5-box+msaa4", set: { fixed: false, msaa: 4, scale: 1.5, filter: "box" } },
  ];
  const shoot = async () => {
    await b.evaluate("new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))");
    const s = await b.page.send("Page.captureScreenshot", { format: "png" });
    return s.data;
  };
  // crop the canvas out of a viewport screenshot, at a device-pixel offset
  const CROP = `async (b64, ox, oy, w, h) => {
    const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d"); g.drawImage(img, -ox, -oy);
    return { w, h, data: g.getImageData(0, 0, w, h).data };
  }`;
  await b.evaluate(`window.__crop = ${CROP}; 1`);
  const outW = report.native.output.w, outH = report.native.output.h;
  const ox0 = Math.round(rect.x * rect.dpr), oy0 = Math.round(rect.y * rect.dpr);
  let offset = null;
  for (const d of DISPLAY) {
    await b.evaluate(`window.__piano.lab.set(${JSON.stringify({ ...d.set, pan: 0 })})`);
    await b.evaluate("window.__piano.lab.grab(), 0");
    // align once, on the adaptive buffer, by searching +-2 device pixels for the exact match
    if (!offset && d.id === "adaptive-msaa4") {
      const shot = await shoot();
      let best = null;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        const r = await b.evaluate(`(async () => { const g = await __crop(${JSON.stringify(shot)}, ${ox0 + dx}, ${oy0 + dy}, ${outW}, ${outH}); const direct = window.__piano.lab.grab(); return __M.cmp(direct, g, __M.dmasks[0]).mae; })()`);
        if (!best || r < best.mae) best = { dx, dy, mae: r };
      }
      offset = best;
      report.displayAlign = { rect, offset: best, note: "MAE between the page screenshot and the drawing buffer read back directly; 0 means the browser shows the buffer 1:1" };
      console.log("align", JSON.stringify(report.displayAlign));
    }
  }
  for (const d of DISPLAY) {
    const r = await b.evaluate(`window.__piano.lab.set(${JSON.stringify({ ...d.set, pan: 0 })})`);
    const frames = [];
    let still = null;
    for (let f = 0; f < PAN_FRAMES; f++) {
      await b.evaluate(`window.__piano.lab.set({ pan: ${f * panStep} }).then(() => { window.__piano.lab.grab(); return 1; })`);
      const shot = await shoot();
      if (f === 0) writeFileSync(join(OUT, `display-${d.id}.png`), Buffer.from(shot, "base64"));
      await b.evaluate(`(async () => { window.__dframes = window.__dframes || []; if (${f} === 0) window.__dframes = []; __dframes.push(await __crop(${JSON.stringify(shot)}, ${ox0 + offset.dx}, ${oy0 + offset.dy}, ${outW}, ${outH})); return 1; })()`);
    }
    const m = await b.evaluate(`(() => {
      const refs = __M.refs, masks = __M.masks;
      __M.refs = __M.drefs; __M.masks = __M.dmasks;
      const still = __M.cmp(__M.drefs[0], __dframes[0], __M.dmasks[0]);
      const sh = __M.shimmer(__dframes);
      __M.refs = refs; __M.masks = masks;
      return { still, sh };
    })()`);
    const row = { id: d.id, buffer: r.buffer, internal: r.internal, mae: f4(m.still.mae), edgeMae: f4(m.still.edgeMae), psnr: +m.still.psnr.toFixed(2),
                  shimmer: f4(m.sh.shimmer), edgeShimmer: f4(m.sh.edgeShimmer) };
    report.display.push(row);
    console.log("display", d.id.padEnd(28), JSON.stringify(row));
  }
  await b.evaluate(`window.__piano.lab.set({ fixed: false, pan: 0 })`);
} catch (e) {
  report.fatal = String(e.stack || e);
  console.log("FATAL", report.fatal);
} finally {
  report.errors = b.errors;
  writeFileSync(join(OUT, "aa-bench.json"), JSON.stringify(report, null, 2));
  console.log("errors", JSON.stringify(b.errors));
  await b.close();
  process.exit(0);
}
