// VJ impact receipt: how hard each pad effect hits, measured from rendered frames, in a private headless Chrome forced
// onto SwiftShader (the CPU: this host's AMD driver has a crash history, so no frame here is ever drawn on the GPU),
// under the house GPU lock, in bursts under three minutes with the lock released between them.
//
//   node arsenal/lanes/vj_impact.mjs [--label before|after] [--phase impact,variety,latency,sheet] [--sets id,id]
//                                    [--stamp S] [--port 8961] [--engine-port 8962] [--out <dir>] [--lock-dir <dir>]
//                                    [--compare <receipt.json>]
//
// Daniel, 2026-10-24: "The VJ thing is so cool!!!!! How do we make the effects feel more impactful and make the vj sets
// even more reponsive!" and "I love the feel of pad 2 the most so far, pad 1 is not bad, pad 4 could have more variety
// and be more impactful". This receipt is the ruler for that: it measures first, so a change can be judged against it.
//
// HOW (the impact phase). The receipt serves a harness page with TWO copies of /web/vj.html side by side in iframes, the
// HIT page and the CONTROL page, both on a virtual clock: an init script replaces performance.now and
// requestAnimationFrame in each, so a frame is drawn only when the receipt steps the clock, and both pages see exactly
// the same times. The pages are deterministic on SwiftShader (no engine, no demo, no music: the sets run on time alone),
// so the control page draws precisely the frame the hit page would have drawn without the pad, and hit minus control
// is the pad's own effect image -- the set's own motion cancels out. For every pad effect on several sets, the pad is
// fired at soft (0.3), medium (0.6) and hard (1.0) velocity on a fixed seed; frames are read at 60 Hz from 150 ms before
// the hit to 300 ms after, then every 50 ms to 1.5 s. Per hit:
//   impact     the mean absolute difference hit vs control (display values 0..1, the three channels averaged) over the
//              frames 0-150 ms after the hit
//   onset      the same at the first frame after the hit, as a share of the peak (1 = visible at full strength within
//              one frame)
//   peak, t_peak, decay_ms   the largest difference, when, and how long until it falls under 10 % of the peak
//   lum / con  the luminance lift (mean relative luminance, linear) and the contrast change (standard deviation of the
//              display luma) in 0-150 ms: against the control, and against the hit page's own 150 ms before the hit
//   coverage   the share of the frame the effect changes by more than 0.1; chroma = how saturated the changed pixels are
// THE VARIETY PHASE fires each effect eight times hard and compares the eight effect images (at +50 and +100 ms) with each
// other: variety = the mean pairwise difference over the mean magnitude (0 = eight identical hits; 2 = no overlap).
// THE LATENCY PHASE runs one page on the real clock with a fake engine (Server-Sent Events) and measures event arrival
// to the frame that draws it (the page's own record when it keeps one, else the next animation frame).
// THE SHEET PHASE writes a contact sheet per set (rows: the effects; columns: control, soft, medium, hard at +50 ms, hard
// at +150 and +400 ms) and a frame per effect (hard, +50 ms).
// --compare prints the before/after table against another receipt and checks pad 2 (laser burst) stays within 10 %.
// Writes state/arsenal/receipts/vj-impact-<label>-<stamp>/receipt.json and the images beside it.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { LOCK_DIR, acquireGpuLock } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const { values: opt } = parseArgs({
  options: {
    // the page files to serve (default arsenal/web); a copy lets the baseline run while the working tree changes
    web: { type: "string", default: resolve(REPO, "arsenal", "web") },
    label: { type: "string", default: "run" },
    phase: { type: "string", default: "impact,variety,latency,sheet" },
    sets: { type: "string", default: "vj-laser-cathedral,vj-reactor,vj-synthwave-grid" },
    "variety-set": { type: "string", default: "vj-reactor" },
    stamp: { type: "string", default: "" },
    port: { type: "string", default: "8961" },
    "engine-port": { type: "string", default: "8962" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    width: { type: "string", default: "640" },
    height: { type: "string", default: "360" },
    "gpu-wait-min": { type: "string", default: "4" },
    "lock-dir": { type: "string", default: LOCK_DIR },
    compare: { type: "string", default: "" },
    "burst-s": { type: "string", default: "170" },
    // only these effects (to re-measure one pad into an existing receipt: drop its rows there first)
    effects: { type: "string", default: "" },
  },
});
const WEB = resolve(opt.web);
let PORT = Number(opt.port), ENGINE_PORT = Number(opt["engine-port"]);
for (const p of [PORT, ENGINE_PORT]) {
  if (p === 8793 || p === 8794 || !(p >= 8900 && p <= 8999)) {
    console.log(`ERROR port ${p}: the receipt uses the test band 8900-8999 only (8793 and 8794 are Daniel's)`);
    process.exit(2);
  }
}
const W = Number(opt.width), H = Number(opt.height);
const stamp = opt.stamp || new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const outDir = join(opt.out, `vj-impact-${opt.label}-${stamp}`);
mkdirSync(outDir, { recursive: true });
const receiptFile = join(outDir, "receipt.json");
const PHASES = opt.phase.split(",").map((s) => s.trim()).filter(Boolean);
const SETS = opt.sets.split(",").map((s) => s.trim()).filter((s) => /^[a-z0-9][a-z0-9-]{1,40}$/.test(s));
const VELS = { soft: 0.3, medium: 0.6, hard: 1.0 };
const HOLDABLE_MS = 600, ONESHOT_MS = 100;
// the pad map both runs measure: the defaults, with pad 11 on Invert (an effect that had no pad before 2026-10-24)
const BEFORE_PADS = ["shockwave", "laser", "flash", "glitch", "strobe", "particles", "kaleido", "freeze", "dampen", "choke",
                     "invert", "next"];

const report = existsSync(receiptFile) ? JSON.parse(readFileSync(receiptFile, "utf8")) : {
  api: "arsenal.receipt/v0", lane: "vj-impact", label: opt.label, title: "VJ pad impact, onset, decay and variety on SwiftShader",
  started_at: new Date().toISOString(), viewport: { width: W, height: H }, git: null, chrome: null, webgl: null,
  method: {
    clock: "virtual: performance.now and requestAnimationFrame replaced in each page; both pages stepped together",
    control: "a second copy of the page, same set, same steps, no pad: hit minus control is the effect image",
    velocities: VELS, frames: "60 Hz from -150 ms to +300 ms, then every 50 ms to +1500 ms",
    impact: "mean |hit - control| over RGB, display values 0..1, frames in (0, 150] ms",
    variety: "8 hard hits; effect images at +50 and +100 ms; mean pairwise |Ei - Ej| over mean |Ei| (0 same, 2 disjoint)",
  },
  bursts: [], sets: {}, variety: {}, latency: null, sheets: [], frames: [], console: [], exceptions: [], page_errors: [],
  not_measured: [
    "the real GPU: SwiftShader draws every frame on the CPU, so nothing here says how fast the live rig runs",
    "how an effect feels to a person in motion; the numbers rank and compare, the contact sheets show single frames",
    "music: no engine and no demo in the impact and variety phases (a set's own beat reactions are not exercised)",
  ],
};
report.web = WEB;
try { report.git = spawnSync("git", ["rev-parse", "--short", "HEAD"], { cwd: REPO, encoding: "utf8" }).stdout.trim(); } catch { /* no git */ }
const save = () => writeFileSync(receiptFile, JSON.stringify(report, null, 2));

// --------------------------------------------------------------------------------------------------- servers --
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".json": "application/json", ".frag": "text/plain; charset=utf-8",
                ".glsl": "text/plain; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml" };
const HARNESS = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>vj impact harness</title><style>
html,body{margin:0;background:#000;overflow:hidden}#row{display:flex}
iframe{width:${W}px;height:${H}px;border:0;display:block;flex:none}</style></head>
<body><div id="row"><iframe id="H" name="hit"></iframe><iframe id="C" name="control"></iframe></div></body></html>`;
const web = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (url.pathname === "/favicon.ico") { res.writeHead(204); res.end(); return; }
  if (url.pathname === "/harness.html") { res.writeHead(200, { "Content-Type": TYPES[".html"], "Cache-Control": "no-store" }); res.end(HARNESS); return; }
  if (!url.pathname.startsWith("/web/")) { res.writeHead(404); res.end(); return; }
  const target = resolve(WEB, decodeURIComponent(url.pathname.slice(5)));
  if (!(target + sep).startsWith(WEB + sep)) { res.writeHead(404); res.end(); return; }
  try {
    const body = readFileSync(target);
    res.writeHead(200, { "Content-Type": TYPES[extname(target).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
// the fake engine for the latency phase: Server-Sent Events; POST /api/pads and /api/scene are taken (202)
const sse = new Set();
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" };
const engineServer = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (req.method === "OPTIONS") { res.writeHead(204, CORS); res.end(); return; }
  if (url.pathname === "/api/events" && req.method === "GET") {
    res.writeHead(200, { ...CORS, "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
    res.write(": vj_impact fake engine\n\n");
    sse.add(res);
    req.on("close", () => sse.delete(res));
    return;
  }
  if (req.method === "POST" && (url.pathname === "/api/pads" || url.pathname === "/api/scene")) {
    req.resume();
    req.on("end", () => { res.writeHead(202, { ...CORS, "Content-Type": "application/json", Connection: "close" }); res.end('{"ok":true}'); });
    return;
  }
  res.writeHead(404, CORS);
  res.end();
});
const send = (obj) => { for (const c of sse) c.write(`data: ${JSON.stringify(obj)}\n\n`); };
async function listenInBand(server, preferred) {
  for (let p = preferred; p <= 8999; p++) {
    if (p === 8793 || p === 8794) continue;
    try {
      await new Promise((ok, fail) => {
        const onErr = (e) => { server.off("listening", onOk); fail(e); };
        const onOk = () => { server.off("error", onErr); ok(); };
        server.once("error", onErr);
        server.once("listening", onOk);
        server.listen(p, "127.0.0.1");
      });
      return p;
    } catch (e) {
      if (e.code !== "EADDRINUSE" && e.code !== "EACCES") throw e;
    }
  }
  throw new Error(`no free port from ${preferred} to 8999`);
}

// ------------------------------------------------------------------------------------------------ Chrome, CDP --
function connect(wsUrl) {
  return new Promise((ok, fail) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result);
      } else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onopen = () => ok({
      send: (method, params = {}, sessionId) => new Promise((res, rej) => {
        const id = nextId++;
        pending.set(id, { res, rej });
        ws.send(JSON.stringify(sessionId ? { id, method, params, sessionId } : { id, method, params }));
      }),
      on: (fn) => listeners.push(fn),
      close: () => ws.close(),
    });
    ws.onerror = () => fail(new Error(`websocket error on ${wsUrl}`));
  });
}
const withTimeout = (promise, ms, what) => {
  let timer;
  return Promise.race([promise, new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`no answer within ${ms} ms: ${what}`)), ms); })])
    .finally(() => clearTimeout(timer));
};
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { const v = await fn(); if (v) return v; } catch { /* not yet */ }
    await delay(150);
  }
  throw new Error(`timed out waiting for ${what}`);
}

// The virtual clock, installed in every vj.html frame before its modules run. performance.now returns the virtual time;
// requestAnimationFrame queues; __vt.step(ms) advances the clock and runs the queued callbacks (one frame). The latency
// phase loads the page with ?realclock=1 and keeps the browser's own clock.
const VIRTUAL_CLOCK = `(() => {
  if (!/\\/web\\/vj\\.html$/.test(location.pathname) || /[?&]realclock=1/.test(location.search)) return;
  let vt = 20000;
  const q = [];
  performance.now = () => vt;
  window.requestAnimationFrame = (cb) => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__vt = { step(ms) { vt += ms; const cbs = q.splice(0, q.length); for (const cb of cbs) cb(vt); return vt; }, now: () => vt };
})();`;

// The harness's measuring code, evaluated once in the harness page (it reaches both iframes: same origin).
const MEASURE = String.raw`(() => {
  const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  const win = (id) => document.getElementById(id).contentWindow;
  const bufs = {};
  function read(id) {
    const c = win(id).document.getElementById("gl");
    const gl = c.getContext("webgl2");
    const w = c.width, h = c.height, n = w * h * 4;
    if (!bufs[id] || bufs[id].length !== n) bufs[id] = new Uint8Array(n);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, bufs[id]);
    return { w, h, buf: bufs[id], canvas: c };
  }
  function stats(b) {
    let lum = 0, y = 0, y2 = 0;
    const n = b.w * b.h;
    for (let i = 0; i < n * 4; i += 4) {
      const r = b.buf[i], g = b.buf[i + 1], bl = b.buf[i + 2];
      lum += 0.2126 * LUT[r] + 0.7152 * LUT[g] + 0.0722 * LUT[bl];
      const yy = (0.2126 * r + 0.7152 * g + 0.0722 * bl) / 255;
      y += yy; y2 += yy * yy;
    }
    const my = y / n;
    return { lum: lum / n, con: Math.sqrt(Math.max(0, y2 / n - my * my)) };
  }
  // hit vs control: mean |d| (0..1), coverage (share changed by > 0.1), chroma of the changed hit pixels; and a small
  // signed effect image (80 x 45 blocks, rgb) for the variety phase when asked
  function diff(a, b, keepImage) {
    const n = a.w * a.h;
    let sum = 0, cov = 0, chroma = 0;
    const BW = 80, BH = 45, bx = a.w / BW, by = a.h / BH;
    const img = keepImage ? new Float32Array(BW * BH * 3) : null;
    for (let p = 0, i = 0; p < n; p++, i += 4) {
      const dr = a.buf[i] - b.buf[i], dg = a.buf[i + 1] - b.buf[i + 1], db = a.buf[i + 2] - b.buf[i + 2];
      const ad = (Math.abs(dr) + Math.abs(dg) + Math.abs(db)) / 3;
      sum += ad;
      if (Math.max(Math.abs(dr), Math.abs(dg), Math.abs(db)) > 25) {
        cov++;
        const r = a.buf[i], g = a.buf[i + 1], bl = a.buf[i + 2];
        const mx = Math.max(r, g, bl), mn = Math.min(r, g, bl);
        chroma += mx > 0 ? (mx - mn) / mx : 0;
      }
      if (img) {
        const x = p % a.w, yy = (p / a.w) | 0;
        const k = ((Math.min(BH - 1, (yy / by) | 0) * BW) + Math.min(BW - 1, (x / bx) | 0)) * 3;
        img[k] += dr; img[k + 1] += dg; img[k + 2] += db;
      }
    }
    if (img) { const s = 1 / (255 * bx * by); for (let k = 0; k < img.length; k++) img[k] *= s; }
    return { mad: sum / n / 255, coverage: cov / n, chroma: cov ? chroma / cov : 0, img };
  }
  function step(ms) { win("H").__vt.step(ms); win("C").__vt.step(ms); }
  const tiles = {};
  // a copy of a frame from the pixels already read (bottom-up rows), on CPU-backed 2D canvases only: copying a WebGL
  // canvas straight into a 2D canvas tied the copy to a page that the next effect's reload destroys (the sheet hung)
  function snapFrom(b, key, scale) {
    const full = document.createElement("canvas");
    full.width = b.w; full.height = b.h;
    const g = full.getContext("2d", { willReadFrequently: true });
    const img = g.createImageData(b.w, b.h);
    const row = b.w * 4;
    for (let y = 0; y < b.h; y++) img.data.set(b.buf.subarray((b.h - 1 - y) * row, (b.h - y) * row), y * row);
    for (let i = 3; i < img.data.length; i += 4) img.data[i] = 255;
    g.putImageData(img, 0, 0);
    if (scale === 1) { tiles[key] = full; return full; }
    const c = document.createElement("canvas");
    c.width = Math.round(b.w * scale); c.height = Math.round(b.h * scale);
    c.getContext("2d", { willReadFrequently: true }).drawImage(full, 0, 0, c.width, c.height);
    tiles[key] = c;
    return c;
  }
  // One hit: pre frames, the press, post frames. Returns the time series and summary numbers. opts: { pad, vel, holdMs,
  // snaps: [{ at: ms, key, scale }], images: [ms...] (effect images kept for variety), settle: [n, ms] }
  function hit(opts) {
    const F = 1000 / 60;
    const series = [];
    for (let i = 8; i >= 0; i--) {         // 9 frames: the last is at t = 0, just before the press
      step(F);
      const h = read("H"), c = read("C");
      const s = stats(h), sc = stats(c), d = diff(h, c, false);
      series.push({ t: -i * F, mad: d.mad, lum: s.lum, con: s.con, lumC: sc.lum, conC: sc.con, cov: d.coverage, chroma: d.chroma });
    }
    win("H").__vj.press(opts.pad, opts.vel);
    let released = false, t = 0;
    const images = {};
    const post = [];
    for (let i = 0; i < 18; i++) post.push(F);
    for (let i = 0; i < 24; i++) post.push(50);
    for (const dt of post) {
      step(dt);
      t += dt;
      if (!released && t >= opts.holdMs) { win("H").__vj.release(opts.pad); released = true; }
      const h = read("H"), c = read("C");
      const keep = (opts.images || []).some((a) => Math.abs(a - t) < 1);
      const s = stats(h), sc = stats(c), d = diff(h, c, keep);
      if (keep) images[Math.round(t)] = d.img;
      for (const sn of opts.snaps || []) {
        if (Math.abs(sn.at - t) < 1) { snapFrom(h, sn.key, sn.scale); if (sn.control) snapFrom(c, sn.control, sn.scale); }
      }
      series.push({ t, mad: d.mad, lum: s.lum, con: s.con, lumC: sc.lum, conC: sc.con, cov: d.coverage, chroma: d.chroma });
      if (opts.short && t >= 101) break;
    }
    if (!released) win("H").__vj.release(opts.pad);
    const [n, ms] = opts.settle || [6, 100];
    for (let i = 0; i < n; i++) step(ms);
    return { series, images };
  }
  function variety(imgs) {                  // imgs: Float32Array[] (each: concatenated effect images)
    let mag = 0;
    for (const a of imgs) { let s = 0; for (let k = 0; k < a.length; k++) s += Math.abs(a[k]); mag += s / a.length; }
    mag /= imgs.length;
    let pair = 0, np = 0;
    for (let i = 0; i < imgs.length; i++) for (let j = i + 1; j < imgs.length; j++) {
      let s = 0; const a = imgs[i], b = imgs[j];
      for (let k = 0; k < a.length; k++) s += Math.abs(a[k] - b[k]);
      pair += s / a.length; np++;
    }
    pair /= Math.max(np, 1);
    // the part every hit shares: the magnitude of the mean image over the mean magnitude (1 = eight identical hits)
    let common = 0;
    for (let k = 0; k < imgs[0].length; k++) { let s = 0; for (const a of imgs) s += a[k]; common += Math.abs(s / imgs.length); }
    common /= imgs[0].length;
    // and the first half (+50 ms) against the second (+100 ms), apart
    const half = imgs[0].length / 2;
    const part = (from) => {
      let m = 0, p = 0, n = 0;
      for (const a of imgs) { let s = 0; for (let k = from; k < from + half; k++) s += Math.abs(a[k]); m += s / half; }
      for (let i = 0; i < imgs.length; i++) for (let j = i + 1; j < imgs.length; j++) {
        let s = 0; for (let k = from; k < from + half; k++) s += Math.abs(imgs[i][k] - imgs[j][k]); p += s / half; n++;
      }
      m /= imgs.length; p /= Math.max(n, 1);
      return m > 1e-6 ? p / m : 0;
    };
    return { mean_magnitude: mag, pairwise: pair, variety: mag > 1e-6 ? pair / mag : 0,
             shared_share: mag > 1e-6 ? common / mag : 0, variety_50ms: part(0), variety_100ms: part(half) };
  }
  function sheet(rows, cols, tileW, tileH) {   // rows: [{ label, keys: [key per col] }]
    const pad = 22, c = document.createElement("canvas");
    c.width = cols.length * tileW + 140; c.height = rows.length * tileH + pad;
    const g = c.getContext("2d", { willReadFrequently: true });
    g.fillStyle = "#000"; g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = "#ddd"; g.font = "13px monospace";
    cols.forEach((label, k) => g.fillText(label, 140 + k * tileW + 4, 15));
    rows.forEach((r, i) => {
      g.fillStyle = "#ddd"; g.fillText(r.label, 4, pad + i * tileH + tileH / 2);
      r.keys.forEach((key, k) => { if (tiles[key]) g.drawImage(tiles[key], 140 + k * tileW, pad + i * tileH, tileW, tileH); });
    });
    return c.toDataURL("image/png").slice(22);
  }
  const png = (key) => (tiles[key] ? tiles[key].toDataURL("image/png").slice(22) : null);
  const keptImages = {};
  const stash = {};
  // a long string (a PNG as base64) is handed over in slices: one multi-megabyte answer stalled the CDP connection
  function hold(key, s) { stash[key] = s || ""; return stash[key].length; }
  function slice(key, from, n) { return stash[key].slice(from, from + n); }
  window.__impact = { step, hit, variety, sheet, png, tiles, keptImages, hold, slice,
    load(id, url) { return new Promise((ok) => { const f = document.getElementById(id); f.onload = () => ok(true); f.src = url; }); },
    // both pages ready, gate v2 included (it compiles in the background; until its meter links a page refuses every pad
    // effect, its safe mode; it may decide on the CPU for a while before the GPU decision links, by the same rules)
    ready() { const lim = (w) => { const l = w.__vj.stats().limiter; return !l || l.on || !!l.error; };
      return !!(win("H").__vj && win("H").__vj.ready && win("C").__vj && win("C").__vj.ready && lim(win("H")) && lim(win("C"))); },
    padMap() { return win("H").__vj.stats().padMap; },
    choke() { for (const id of ["H", "C"]) { const o = { code: "KeyW", key: "w", bubbles: true }; win(id).dispatchEvent(new KeyboardEvent("keydown", o)); win(id).dispatchEvent(new KeyboardEvent("keyup", o)); } },
    errors() { return { hit: win("H").__vj.errors(), control: win("C").__vj.errors() }; },
    renderer() {
      const g = win("H").document.getElementById("gl").getContext("webgl2");
      const d = g.getExtension("WEBGL_debug_renderer_info");
      return { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER), version: g.getParameter(g.VERSION) };
    },
  };
  return true;
})()`;

// A long string from the harness (a PNG as base64), pulled in 256 KB slices.
async function pull(page, expr) {
  const n = await page.evaluate(`window.__impact.hold("x", ${expr})`);
  let out = "";
  for (let from = 0; from < n; from += 262144) out += await page.evaluate(`window.__impact.slice("x", ${from}, 262144)`);
  return out;
}

// ------------------------------------------------------------------------------------------- summarising a hit --
function summarise(series) {
  const pre = series.filter((s) => s.t <= 0 && s.t >= -150);
  const post = series.filter((s) => s.t > 0 && s.t <= 151);
  const all = series.filter((s) => s.t > 0);
  const mean = (a, f) => (a.length ? a.reduce((x, s) => x + f(s), 0) / a.length : 0);
  let peak = 0, tPeak = 0;
  for (const s of all) if (s.mad > peak) { peak = s.mad; tPeak = s.t; }
  let decay = null;
  for (const s of all) if (s.t > tPeak && s.mad < 0.1 * peak) { decay = s.t; break; }
  const first = all[0];
  const r4 = (x) => +x.toFixed(5);
  return {
    impact: r4(mean(post, (s) => s.mad)), pre_residual: r4(mean(pre, (s) => s.mad)),
    onset_first_frame: r4(first ? first.mad : 0), onset_share: r4(peak > 0 && first ? first.mad / peak : 0),
    peak: r4(peak), t_peak_ms: Math.round(tPeak), decay_ms: decay === null ? ">1500" : Math.round(decay),
    lum_vs_control: r4(mean(post, (s) => s.lum - s.lumC)), con_vs_control: r4(mean(post, (s) => s.con - s.conC)),
    lum_vs_before: r4(mean(post, (s) => s.lum) - mean(pre, (s) => s.lum)), con_vs_before: r4(mean(post, (s) => s.con) - mean(pre, (s) => s.con)),
    coverage: r4(mean(post, (s) => s.cov)), chroma: r4(mean(post.filter((s) => s.cov > 0), (s) => s.chroma)),
    curve: series.filter((s) => s.t > -40 && s.t <= 400).map((s) => [Math.round(s.t), r4(s.mad)]),
  };
}

// --------------------------------------------------------------------------------------------------- one burst --
async function burst(name, body) {
  const t0 = Date.now();
  const profile = join(tmpdir(), `arsenal-vj-impact-${stamp}-${name}-${process.pid}`);
  let gpu = null, chrome = null, browser = null;
  const entry = { name, started_at: new Date().toISOString(), seconds: null, error: null };
  report.bursts.push(entry);
  try {
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `vj_impact ${name} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000 });
    if (!existsSync(opt.chrome)) throw new Error(`no Chrome at ${opt.chrome}`);
    chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0",
      `--user-data-dir=${profile}`, `--window-size=${2 * W},${H}`, "--force-device-scale-factor=1", "about:blank"],
      { stdio: "ignore", windowsHide: true });
    const portFile = join(profile, "DevToolsActivePort");
    const [cdpPort, cdpPath] = await waitFor(() => {
      try { const [p, w] = readFileSync(portFile, "utf8").split(/\r?\n/); return p && w ? [p, w] : null; } catch { return null; }
    }, 30000, "Chrome's DevToolsActivePort");
    browser = await connect(`ws://127.0.0.1:${cdpPort}${cdpPath}`);
    report.chrome = (await browser.send("Browser.getVersion")).product;
    const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
    const S = (method, params = {}, ms = 90000) => withTimeout(browser.send(method, params, sessionId), ms, method);
    browser.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "warning")) {
        report.console.push({ burst: name, type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300) });
      } else if (msg.method === "Runtime.exceptionThrown") {
        const d = p.exceptionDetails;
        report.exceptions.push({ burst: name, text: d.text, description: d.exception?.description, url: d.url });
      }
    });
    for (const d of ["Runtime", "Page"]) await S(`${d}.enable`);
    await S("Emulation.setDeviceMetricsOverride", { width: 2 * W, height: H, deviceScaleFactor: 1, mobile: false });
    await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
    const evaluate = async (expression, ms = 90000) => {
      const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }, ms);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    await body({ S, evaluate, t0, deadline: t0 + Number(opt["burst-s"]) * 1000 });
  } catch (err) {
    entry.error = String((err && err.stack) || err);
    console.log(`ERROR [${name}]`, entry.error);
  } finally {
    entry.seconds = Math.round((Date.now() - t0) / 100) / 10;
    try { await browser?.send("Browser.close"); } catch { /* gone */ }
    await delay(600);
    if (chrome && chrome.exitCode === null) spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
    gpu?.release();
    await delay(300);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
    save();
  }
}

// Open the harness page (the stored pad map seeded first: same origin, so both pages read it); reloadPages() then loads
// both pages on `set` afresh (the virtual clock starts at 20 s each time), so every effect is measured from the same
// state whichever burst measures it.
async function openHarness(page) {
  await page.S("Page.navigate", { url: `http://127.0.0.1:${PORT}/harness.html` });
  await waitFor(() => page.evaluate("document.readyState === 'complete'"), 15000, "the harness page");
  await page.evaluate(MEASURE);
  // before 2026-10-24 Invert had no pad: both runs measure it on pad 11 (the new default); the after run keeps its own map
  if (opt.label === "before") await page.evaluate(`(localStorage.setItem("arsenal.vj.padMap", ${JSON.stringify(JSON.stringify(BEFORE_PADS))}), true)`);
  else await page.evaluate(`(localStorage.removeItem("arsenal.vj.padMap"), true)`);
}
async function reloadPages(page, set, extra = "") {
  const q = `engine=off&hud=0&watchdog=0&sets=${set}${extra}`;
  await page.evaluate(`Promise.all([window.__impact.load("H", "/web/vj.html?${q}"), window.__impact.load("C", "/web/vj.html?${q}")])`);
  await waitFor(() => page.evaluate("window.__impact.ready()"), 60000, `both pages ready on ${set}`);
  if (!report.webgl) {
    report.webgl = await page.evaluate("window.__impact.renderer()");
    report.renderer_check = judgeRenderer(report.webgl && report.webgl.renderer);
  }
  if (!judgeRenderer(report.webgl && report.webgl.renderer).ok) throw new Error(`refusing to judge: ${report.renderer_check.reason}`);
  // warm both pages: one second of frames so each set's feedback is under way
  await page.evaluate("(() => { for (let i = 0; i < 20; i++) window.__impact.step(50); return true; })()");
  return page.evaluate("window.__impact.padMap()");
}
const ONLY = new Set(opt.effects.split(",").map((s) => s.trim()).filter(Boolean));
const effectPads = (padMap) => padMap.map((a, i) => ({ action: a, pad: i + 1 }))
  .filter((x) => EFFECT_NAMES.has(x.action) && (!ONLY.size || ONLY.has(x.action)));
const EFFECT_NAMES = new Set(["shockwave", "laser", "flash", "glitch", "strobe", "particles", "kaleido", "freeze", "invert", "zoom"]);
const HOLDABLE = new Set(["strobe", "particles", "kaleido", "freeze", "invert"]);

// ----------------------------------------------------------------------------------------------- the phases --
async function phaseImpact(set) {
  await burst(`impact-${set}`, async (page) => {
    await openHarness(page);
    const padMap = await reloadPages(page, set);
    const row = report.sets[set] || (report.sets[set] = { pad_map: padMap, effects: {} });
    row.pad_map = padMap;
    let first = true;
    const measured = [];
    for (const { action, pad } of effectPads(padMap)) {
      if (row.effects[action] && row.effects[action].vel && Object.keys(row.effects[action].vel).length === 3) continue;
      if (!first) await reloadPages(page, set);
      first = false;
      const e = row.effects[action] = { pad, vel: {} };
      for (const [vname, vel] of Object.entries(VELS)) {
        const snaps = [{ at: 50, key: `${set}:${action}:${vname}:50`, scale: 0.4, control: vname === "soft" ? `${set}:${action}:control:50` : undefined }];
        if (vname === "hard") snaps.push({ at: 150, key: `${set}:${action}:hard:150`, scale: 0.4 }, { at: 400, key: `${set}:${action}:hard:400`, scale: 0.4 },
                                         { at: 50, key: `${set}:${action}:hard:50:full`, scale: 1 });
        const holdMs = HOLDABLE.has(action) ? HOLDABLE_MS : ONESHOT_MS;
        const r = await page.evaluate(`(() => { const r = window.__impact.hit(${JSON.stringify({ pad, vel, holdMs, snaps })}); return r.series; })()`, 120000);
        e.vel[vname] = summarise(r);
        await page.evaluate("(window.__impact.choke(), window.__impact.step(100), true)");
        console.log(`[impact] ${set} pad ${pad} ${action} ${vname}: impact ${e.vel[vname].impact} onset ${e.vel[vname].onset_share} peak ${e.vel[vname].peak} decay ${e.vel[vname].decay_ms}`);
      }
      e.velocity_ratio = e.vel.soft.impact > 0 ? +(e.vel.hard.impact / e.vel.soft.impact).toFixed(3) : null;
      measured.push({ action, pad });
      const one = await pull(page, `window.__impact.png(${JSON.stringify(`${set}:${action}:hard:50:full`)})`);
      if (one) {
        const f = join(outDir, `frame-${set}-pad${pad}-${action}-hard-50ms.png`);
        writeFileSync(f, Buffer.from(one, "base64"));
        if (!report.frames.includes(f)) report.frames.push(f);
      }
      save();
      if (Date.now() > page.deadline) { console.log(`[impact] ${set}: burst time is up; the next burst continues`); break; }
    }
    // the contact sheet of the effects this burst measured
    if (!measured.length) return;
    const rows = measured.map(({ action, pad }) => ({ label: `pad ${pad} ${action}`,
      keys: ["control", "soft", "medium", "hard"].map((v) => `${set}:${action}:${v}:50`).concat([`${set}:${action}:hard:150`, `${set}:${action}:hard:400`]) }));
    const b64 = await pull(page, `window.__impact.sheet(${JSON.stringify(rows)}, ["control +50ms", "soft +50ms", "medium +50ms", "hard +50ms", "hard +150ms", "hard +400ms"], 256, 144)`);
    const sheetFile = join(outDir, `sheet-${set}-pads-${measured.map((m) => m.pad).join("-")}.png`);
    writeFileSync(sheetFile, Buffer.from(b64, "base64"));
    if (!report.sheets.includes(sheetFile)) report.sheets.push(sheetFile);
    report.page_errors.push({ set, errors: await page.evaluate("window.__impact.errors()") });
  });
}

async function phaseVariety(set) {
  await burst(`variety-${set}`, async (page) => {
    await openHarness(page);
    const padMap = await reloadPages(page, set);
    let first = true;
    for (const { action, pad } of effectPads(padMap)) {
      if (report.variety[action]) continue;
      if (!first) await reloadPages(page, set);
      first = false;
      const imgs = [];
      for (let k = 0; k < 8; k++) {
        const holdMs = HOLDABLE.has(action) ? HOLDABLE_MS : ONESHOT_MS;
        const key = `v${k}`;
        await page.evaluate(`(() => { const r = window.__impact.hit(${JSON.stringify({ pad, vel: 1, holdMs, images: [50, 100], short: true, settle: [14, 100] })});
          const a = r.images[50], b = r.images[100]; const c = new Float32Array(a.length + b.length); c.set(a); c.set(b, a.length);
          window.__impact.keptImages[${JSON.stringify(key)}] = c; return true; })()`, 120000);
        await page.evaluate("(window.__impact.choke(), window.__impact.step(100), true)");
        imgs.push(key);
      }
      const v = await page.evaluate(`window.__impact.variety(${JSON.stringify(imgs)}.map((k) => window.__impact.keptImages[k]))`);
      report.variety[action] = { set, pad, hits: 8, ...Object.fromEntries(Object.entries(v).map(([k, x]) => [k, +x.toFixed(5)])) };
      console.log(`[variety] ${set} pad ${pad} ${action}: variety ${report.variety[action].variety} (pairwise ${report.variety[action].pairwise}, magnitude ${report.variety[action].mean_magnitude})`);
      if (Date.now() > page.deadline) { console.log(`[variety] burst time is up; the next burst continues`); break; }
    }
  });
}

// Event arrival to the frame that draws it, on the real clock: pad events from a fake engine, each one ~370 ms apart at
// a random phase of the frame. The page's own record (window.__vj.latency(), when it keeps one) gives arrival, the frame
// that drew it and the effect's level in that frame; without it, an instrumented EventSource and requestAnimationFrame
// give arrival and the next frame.
const LATENCY_PROBE = `(() => {
  if (!/\\/web\\/vj\\.html$/.test(location.pathname)) return;
  const arrivals = [], frames = [];
  window.__lat = { arrivals, frames };
  const ES = window.EventSource;
  window.EventSource = function (url, o) {
    const es = new ES(url, o);
    es.addEventListener("message", (m) => { if (m.data.includes('"t":"pad"') && m.data.includes('"on":true')) arrivals.push([performance.now(), Date.now()]); });
    return es;
  };
  window.EventSource.prototype = ES.prototype;
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => raf((ts) => { frames.push([performance.now(), Date.now()]); if (frames.length > 20000) frames.splice(0, 10000); cb(ts); });
})();`;
async function phaseLatency() {
  await burst("latency", async (page) => {
    ENGINE_PORT = await listenInBand(engineServer, ENGINE_PORT);
    await page.S("Page.addScriptToEvaluateOnNewDocument", { source: LATENCY_PROBE });
    await page.S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?realclock=1&engine=http://127.0.0.1:${ENGINE_PORT}&hud=0&watchdog=0&sets=vj-reactor` });
    await waitFor(() => page.evaluate("!!(window.__vj && window.__vj.ready)"), 60000, "the page (latency)");
    await waitFor(() => sse.size > 0, 15000, "the page's EventSource");
    send({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", pads_mode: "both", leds: false, leds_reason: "vj_impact" });
    await delay(800);
    const n = 30;
    const sentAt = [];
    for (let i = 0; i < n; i++) {
      sentAt.push(Date.now());
      send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "bank" });
      await delay(60);
      send({ t: "pad", pad: 2, vel: 0, on: false, src: "bank" });
      await delay(250 + Math.round(Math.random() * 120));
    }
    await delay(400);
    const own = await page.evaluate("typeof window.__vj.latency === 'function' ? window.__vj.latency() : null");
    const probe = await page.evaluate("({ arrivals: window.__lat.arrivals.slice(), frames: window.__lat.frames.slice() })");
    // arrival (when the page's EventSource handler ran) to the next animation frame; and, on the wall clock node and the
    // page share, the engine's SEND to that frame (a message that waited behind a slow frame waited in the page's queue,
    // which only the send time sees)
    const gaps = [], sendGaps = [];
    const sends = sentAt.slice(-probe.arrivals.length);
    probe.arrivals.forEach(([a, aw], k) => {
      const f = probe.frames.find(([t]) => t >= a);
      if (f === undefined) return;
      gaps.push(f[0] - a);
      if (sends[k] !== undefined) sendGaps.push(f[1] - sends[k]);
    });
    const q = (arr, p) => { const s = arr.slice().sort((x, y) => x - y); return s.length ? +s[Math.min(s.length - 1, Math.floor(p * s.length))].toFixed(2) : null; };
    const frameGaps = probe.frames.slice(1).map(([t], i) => t - probe.frames[i][0]).filter((g) => g < 250);
    report.latency = {
      events: n, arrivals: probe.arrivals.length,
      arrival_to_next_frame_ms: { p50: q(gaps, 0.5), p95: q(gaps, 0.95), max: q(gaps, 1) },
      send_to_next_frame_ms: { p50: q(sendGaps, 0.5), p95: q(sendGaps, 0.95), max: q(sendGaps, 1), n: sendGaps.length },
      frame_interval_ms: { p50: q(frameGaps, 0.5), p95: q(frameGaps, 0.95) },
      page_record: own,
      note: "SwiftShader frames are slow and irregular; the share of the frame interval is the number to compare, and the virtual-clock onset (impact phase) says whether the first frame shows the effect at full strength",
    };
    if (own && Array.isArray(own.records)) {
      // the engine's send (node's wall clock) to the frame that drew it (the page's wall clock: the same machine clock)
      const recs = own.records.filter((r) => r.src === "bank" && r.frameWall).slice(-sentAt.length);
      const sends = sentAt.slice(-recs.length);
      const sendToFrame = recs.map((r, k) => r.frameWall - sends[k]);
      report.latency.send_to_drawn_ms = { p50: q(sendToFrame, 0.5), p95: q(sendToFrame, 0.95), max: q(sendToFrame, 1), n: sendToFrame.length };
      const lat = own.records.filter((r) => r.frame !== null).map((r) => r.frame - r.arrive);
      report.latency.page_arrival_to_drawn_ms = { p50: q(lat, 0.5), p95: q(lat, 0.95), max: q(lat, 1), n: lat.length,
                                                  env_in_that_frame_min: own.records.reduce((m, r) => Math.min(m, r.env ?? 1), 1) };
    }
    console.log(`[latency] send -> next frame p50 ${report.latency.send_to_next_frame_ms.p50} ms, p95 ${report.latency.send_to_next_frame_ms.p95} ms; page record send -> drawn p50 ${report.latency.send_to_drawn_ms ? report.latency.send_to_drawn_ms.p50 : "-"} ms (frame interval p50 ${report.latency.frame_interval_ms.p50} ms)`);
  });
}

// ------------------------------------------------------------------------------------------- the comparison --
function compare(beforeFile) {
  const before = JSON.parse(readFileSync(beforeFile, "utf8"));
  const lines = [];
  const out = { against: beforeFile, rows: [], checks: {} };
  const sets = Object.keys(report.sets).filter((s) => before.sets[s]);
  const effects = new Set();
  for (const s of sets) for (const e of Object.keys(report.sets[s].effects)) effects.add(e);
  lines.push("effect      | set                  | impact soft/med/hard before -> after          | onset hard  | peak hard       | decay hard");
  for (const e of effects) for (const s of sets) {
    const a = report.sets[s].effects[e], b = before.sets[s].effects[e];
    if (!a || Object.keys(a.vel).length < 3) continue;
    const f = (x) => (x === undefined ? "  -   " : x.toFixed(4));
    const bi = b ? ["soft", "medium", "hard"].map((v) => f(b.vel[v]?.impact)).join("/") : "(new)";
    const ai = ["soft", "medium", "hard"].map((v) => f(a.vel[v]?.impact)).join("/");
    lines.push(`${e.padEnd(11)} | ${s.padEnd(20)} | ${bi} -> ${ai} | ${b ? f(b.vel.hard.onset_share) : "  -   "}->${f(a.vel.hard.onset_share)} | ${b ? f(b.vel.hard.peak) : "  -   "}->${f(a.vel.hard.peak)} | ${b ? b.vel.hard.decay_ms : "-"}->${a.vel.hard.decay_ms}`);
    out.rows.push({ effect: e, set: s, before: b ? b.vel : null, after: a.vel });
  }
  // laser burst (pad 2): every set's impact and peak within 10 % of before, or better
  const laser = sets.map((s) => ({ s, a: report.sets[s].effects.laser, b: before.sets[s].effects.laser })).filter((x) => x.a && x.b);
  out.checks.laser_burst_within_10pct_or_better = laser.length > 0 && laser.every(({ a, b }) => ["soft", "medium", "hard"].every((v) =>
    a.vel[v].impact >= 0.9 * b.vel[v].impact && a.vel[v].peak >= 0.9 * b.vel[v].peak));
  const glitchImpact = sets.map((s) => ({ a: report.sets[s].effects.glitch, b: before.sets[s].effects.glitch })).filter((x) => x.a && x.b);
  out.checks.glitch_beats_its_baseline_on_impact = glitchImpact.length > 0 && glitchImpact.every(({ a, b }) => a.vel.hard.impact > b.vel.hard.impact && a.vel.medium.impact > b.vel.medium.impact);
  if (report.variety.glitch && before.variety.glitch) {
    out.checks.glitch_beats_its_baseline_on_variety = report.variety.glitch.variety > before.variety.glitch.variety;
    lines.push(`glitch variety ${before.variety.glitch.variety} -> ${report.variety.glitch.variety}`);
  }
  for (const e of Object.keys(report.variety)) if (before.variety[e]) lines.push(`variety ${e.padEnd(10)} ${before.variety[e].variety} -> ${report.variety[e].variety}`);
  report.compare = out;
  console.log(lines.join("\n"));
  for (const [k, v] of Object.entries(out.checks)) console.log(`${v ? "PASS" : "FAIL"} ${k}`);
}

// ------------------------------------------------------------------------------------------------------ main --
try {
  PORT = await listenInBand(web, PORT);
  for (const set of SETS) if (PHASES.includes("impact")) {
    // a set may need two bursts: the second carries on where the first stopped (the receipt is saved after each)
    for (let k = 0; k < 4; k++) {
      await phaseImpact(set);
      const row = report.sets[set];
      const done = row && effectPads(row.pad_map || []).every((x) => row.effects[x.action] && Object.keys(row.effects[x.action].vel).length === 3);
      if (done) break;
    }
  }
  if (PHASES.includes("variety")) {
    for (let k = 0; k < 4; k++) {
      await phaseVariety(opt["variety-set"]);
      const anyRow = Object.values(report.sets)[0];
      const want = anyRow ? effectPads(anyRow.pad_map).map((x) => x.action) : [];
      if (want.length && want.every((a) => report.variety[a])) break;
      if (!want.length && Object.keys(report.variety).length >= 9) break;
    }
  }
  if (PHASES.includes("latency")) await phaseLatency();
} catch (err) {
  report.error = String((err && err.stack) || err);
  console.log("ERROR", report.error);
} finally {
  // pad 2, the reference: why it reads well, in numbers
  const ref = Object.entries(report.sets).map(([s, r]) => [s, r.effects.laser]).filter(([, e]) => e && e.vel.hard);
  if (ref.length) {
    report.laser_reference = Object.fromEntries(ref.map(([s, e]) => [s, {
      impact: [e.vel.soft.impact, e.vel.medium.impact, e.vel.hard.impact], onset_share_hard: e.vel.hard.onset_share,
      t_peak_ms: e.vel.hard.t_peak_ms, decay_ms: e.vel.hard.decay_ms, chroma_hard: e.vel.hard.chroma, coverage_hard: e.vel.hard.coverage,
      velocity_ratio: e.velocity_ratio, lum_vs_control_hard: e.vel.hard.lum_vs_control }]));
  }
  if (opt.compare) { try { compare(opt.compare); } catch (err) { console.log("compare failed:", err.message); } }
  report.finished_at = new Date().toISOString();
  save();
  web.close();
  for (const c of sse) { try { c.end(); } catch { /* closed */ } }
  engineServer.close();
  const errs = report.bursts.filter((b) => b.error).length;
  console.log(`receipt: ${receiptFile}`);
  console.log(`bursts: ${report.bursts.length} (${errs} with errors); exceptions: ${report.exceptions.length}`);
  process.exit(errs || report.exceptions.length ? 1 : 0);
}
