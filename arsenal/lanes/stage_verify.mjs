// Virtual Stage v0 receipt: load /web/stage/index.html in a private headless Chrome forced onto SwiftShader (the CPU:
// this host's AMD driver has a crash history, and no frame here is ever drawn on the GPU), one browser at a time under
// the house GPU lock (arsenal/GPU-LOCK.md, the main checkout's lock even when run from a worktree), in bursts under three
// minutes, and check what Daniel would be owed.
//
//   node arsenal/lanes/stage_verify.mjs [--phases load,clock,engine,cost,flash,sheet] [--width 1280] [--height 720]
//                                       [--port 8980] [--engine-port 8981] [--flash-seconds 8] [--sheet-dir <dir>]
//
// It serves arsenal/web itself on a test-band port (8900-8999; never 8793, Daniel's server, never 8794, his engine) and
// runs a fake keylab-vj engine (Server-Sent Events at /api/events) on another. The page runs on a VIRTUAL clock
// (performance.now and requestAnimationFrame replaced before any module loads; one frame per 1000/60 ms step) except in
// the engine phase, which needs real time for the event stream.
//
// Phases (each its own burst: lock, Chrome, work, Chrome closed, lock released):
//   load    the page boots with no exceptions or console errors; the renderer string names SwiftShader and no hardware;
//           the rig's counts; one frame renders a picture with beams (the beam pass has fragments) and haze (the
//           medium's density is above zero where the beams are).
//   clock   60 fps virtual clock through the demo show's build into its drop: the beat grid's beats sit on whole numbers;
//           the strand moves (every rung's height changes, and follows the wave formation within 2 cm); the effects follow
//           the clock (the strand heads' unison pulse peaks on beat frames +-1; the KICK lift lands on its beat frame +-1);
//           sections change on bar lines and the camera cuts only on bar lines; the flythrough arrives on the downbeat.
//   engine  real clock, the fake engine: hello, beats at 140 BPM with bar and ver, a tap (ver bump), pads 1 and 2 -> the
//           page's grid follows the engine's tempo, re-anchors on the ver, and the pads reach the programmer and lasers.
//   cost    per-pass SwiftShader timings (gl.finish fences) on three shots, the frame time with each feature switched off,
//           and the fragment counts behind the op-count estimate for an RX 6600 (the numbers are the CPU rasteriser's,
//           not the live GPU's: the real-GPU bench is Daniel's, after a fresh boot, design slice S10).
//   flash   the canvas read EVERY frame on the 60 fps virtual clock through the drop (KICK on every downbeat, FLY-OUT, a
//           laser pad storm, camera cuts): flashes counted with the 2026-10-24 verifier's rule (written here on its own,
//           not imported from the page) in 18 windows of a quarter of the screen or more, luminance and red; the stage's
//           own limiter must record zero interventions.
//   sheet   screenshots of the signature shots for the contact sheets (private, scratch only: Daniel's frames are other
//           people's footage and never leave the scratchpad).
// v1 phases (2026-10-25, the phrase; --set source-v1 is the default):
//   phrase       the real page's logic every frame through the first drop's two repeats: steps on their lines (0-1 frame),
//                the thirds and the verticals in order, one FlashGate grant per horizontal step, the ring effects, the
//                laser groups answering each step, the cuts (bar lines; the pre-cut one beat before a flash).
//   pic-levels   HALO_LOCK, rendered: the rows of the three thirds' emitters: the top row's period (3 beats), the middle
//   pic-rush     and bottom rows' lags (+1 and +2 steps), the dark step's share; pic-rush the same at the footage's speed.
//   pic-ring     the chopper on the rendered rings (harmonic, rate, direction) and the colour bump (period, brightness).
//   pic-handoff  step D's frames (lit and true-black shares) and the same phrase position in two repeats (never static).
//   flash3m      three minutes of the programmed demo, crowd on, every frame read back, in chunks of --chunk-seconds,
//                each its own burst; the verifier's counter judges the stitched run (--flash3m-dir resumes a run).
//   sheet-phrase the phrase's contact sheet: every step from its own camera and from the tribune (scratch only).
// Writes <worktree>/state/arsenal/receipts/stage-<stamp>/receipt.json (gitignored) and the PNGs; exits 1 on a failed check.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";
import { expandScene } from "../web/stage/rig.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]+$/, "");
const MAIN = REPO.split(/[\\/]\.claude[\\/]worktrees[\\/]/)[0];
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    phases: { type: "string", default: "load,clock,phrase,engine,flash,storm,pic-levels,pic-rush,pic-ring,pic-handoff" },
    "flash3m-seconds": { type: "string", default: "180" },
    "chunk-seconds": { type: "string", default: "10" },
    "chunk-from": { type: "string", default: "0" },
    "chunk-to": { type: "string", default: "0" },
    "flash3m-dir": { type: "string", default: "" },
    port: { type: "string", default: "8980" },
    "engine-port": { type: "string", default: "8981" },
    width: { type: "string", default: "1280" },
    height: { type: "string", default: "720" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    "sheet-dir": { type: "string", default: "" },
    "lock-dir": { type: "string", default: join(MAIN, "state", "arsenal", "gpu-render.lock") },
    "gpu-wait-min": { type: "string", default: "6" },
    "flash-seconds": { type: "string", default: "8" },
    "flash-scale": { type: "string", default: "1" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    query: { type: "string", default: "" },
    set: { type: "string", default: "source-v1" },
  },
});
if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(opt.set)) { console.log(`ERROR --set ${opt.set}: a set name`); process.exit(2); }
// the set the page will load, expanded here too: the receipt compares the page's counts with the file's
const SCENE = JSON.parse(readFileSync(join(REPO, "arsenal", "web", "stage", "sets", `${opt.set}.json`), "utf8"));
const RIG = expandScene(SCENE);
const PHASES = opt.phases.split(",").map((s) => s.trim()).filter(Boolean);
const W = Number(opt.width), H = Number(opt.height);
let PORT = Number(opt.port), ENGINE_PORT = Number(opt["engine-port"]);
for (const p of [PORT, ENGINE_PORT]) {
  if (p === 8793 || p === 8794 || !(p >= 8900 && p <= 8999)) { console.log(`ERROR port ${p}: the test band 8900-8999 only`); process.exit(2); }
}
const BURST_MS = 170_000;
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const outDir = join(opt.out, `stage-${stamp}`);
mkdirSync(outDir, { recursive: true });
const sheetDir = opt["sheet-dir"] || null;
if (sheetDir) mkdirSync(sheetDir, { recursive: true });

const report = {
  api: "arsenal.receipt/v0", lane: "stage", title: "Virtual Stage v0 in headless Chrome on SwiftShader",
  started_at: new Date().toISOString(), worktree: REPO, viewport: { width: W, height: H }, phases: {}, checks: {},
  not_measured: [
    "the real GPU: SwiftShader draws every frame on the CPU, so its milliseconds rank the passes but say nothing absolute about the RX 6600 (the op-count estimate is a model; the real-GPU bench is design slice S10, with Daniel present)",
    "the KeyLab and the real keylab-vj engine: a fake engine speaks the event contract",
    "beauty: the contact sheets are for Daniel's eye; no metric certifies a composition",
  ],
};
const check = (name, ok, detail) => { report.checks[name] = { ok: !!ok, detail }; console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail !== undefined ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail).slice(0, 300)}` : ""}`); };

// ------------------------------------------------------------------------------------------------ the servers --
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".json": "application/json", ".glsl": "text/plain; charset=utf-8", ".frag": "text/plain; charset=utf-8" };
const web = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (url.pathname === "/favicon.ico") { res.writeHead(204); res.end(); return; }
  if (!url.pathname.startsWith("/web/")) { res.writeHead(404); res.end(); return; }
  const target = resolve(WEB, decodeURIComponent(url.pathname.slice(5)));
  if (!(target + sep).startsWith(WEB + sep)) { res.writeHead(404); res.end(); return; }
  try { const body = readFileSync(target); res.writeHead(200, { "Content-Type": TYPES[extname(target).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" }); res.end(body); }
  catch { res.writeHead(404); res.end(); }
});
const sse = new Set();
const CORS = { "Access-Control-Allow-Origin": "*" };
const engine = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (url.pathname === "/api/events") {
    res.writeHead(200, { ...CORS, "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
    res.write(": stage fake engine\n\n");
    sse.add(res);
    req.on("close", () => sse.delete(res));
    return;
  }
  res.writeHead(404, CORS); res.end();
});
const send = (o) => { for (const c of sse) c.write(`data: ${JSON.stringify(o)}\n\n`); };
async function listen(server, preferred) {
  for (let p = preferred; p <= 8999; p++) {
    if (p === 8793 || p === 8794) continue;
    try {
      await new Promise((ok, fail) => { server.once("error", fail); server.listen(p, "127.0.0.1", () => { server.off("error", fail); ok(); }); });
      return p;
    } catch (e) { if (e.code !== "EADDRINUSE" && e.code !== "EACCES") throw e; }
  }
  throw new Error("no free test-band port");
}

// ------------------------------------------------------------------------------------------------ Chrome & CDP --
function connect(wsUrl) {
  return new Promise((ok, fail) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map(), listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result); }
      else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onopen = () => ok({
      send: (method, params = {}, sessionId) => new Promise((res, rej) => { const id = nextId++; pending.set(id, { res, rej }); ws.send(JSON.stringify(sessionId ? { id, method, params, sessionId } : { id, method, params })); }),
      on: (fn) => listeners.push(fn), close: () => ws.close(),
    });
    ws.onerror = () => fail(new Error(`websocket error on ${wsUrl}`));
  });
}
const withTimeout = (p, ms, what) => { let t; return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(`no answer within ${ms} ms: ${what}`)), ms); })]).finally(() => clearTimeout(t)); };
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { try { const v = await fn(); if (v) return v; } catch { /* not yet */ } await delay(200); }
  throw new Error(`timed out waiting for ${what}`);
}

// The virtual clock, installed before the page's modules run (only on pages that ask for it with vt=1).
const VIRTUAL_CLOCK = `(() => {
  if (!/[?&]vt=1/.test(location.search)) return;
  let vt = 20000;
  const q = [];
  const real = performance.now.bind(performance);
  window.__realNow = real;
  performance.now = () => vt;
  window.requestAnimationFrame = (cb) => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__vt = { step(ms) { vt += ms; const cbs = q.splice(0, q.length); for (const cb of cbs) cb(vt); return vt; }, now: () => vt };
})();`;

// One burst: the lock, a fresh Chrome, the work, Chrome closed, the lock released.
async function burst(name, body) {
  const t0 = Date.now();
  const profile = join(tmpdir(), `arsenal-stage-verify-${stamp}-${name}`);
  let gpu = null, chrome = null, browser = null;
  const phase = report.phases[name] = { console: [], exceptions: [] };
  try {
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `stage_verify ${name} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, pollMs: 2000 });
    phase.lock = { dir: opt["lock-dir"], acquired_at: gpu.owner.acquiredAt };
    const tLock = Date.now();          // the burst (under three minutes) starts when the lock is ours, not while waiting
    chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0", `--user-data-dir=${profile}`,
      `--window-size=${W},${H}`, "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore", windowsHide: true });
    const [cdpPort, cdpPath] = await waitFor(() => { try { const [p, w] = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split(/\r?\n/); return p && w ? [p, w] : null; } catch { return null; } }, 30000, "DevToolsActivePort");
    browser = await connect(`ws://127.0.0.1:${cdpPort}${cdpPath}`);
    phase.chrome = (await browser.send("Browser.getVersion")).product;
    const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
    const S = (method, params = {}, ms = 120000) => withTimeout(browser.send(method, params, sessionId), ms, method);
    browser.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled") phase.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
      else if (msg.method === "Runtime.exceptionThrown") phase.exceptions.push({ text: p.exceptionDetails.text, description: p.exceptionDetails.exception?.description?.slice(0, 600) });
      else if (msg.method === "Log.entryAdded" && (p.entry.level === "error")) phase.console.push({ type: "log-error", text: p.entry.text, url: p.entry.url });
    });
    for (const d of ["Runtime", "Log", "Page"]) await S(`${d}.enable`);
    await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
    await S("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
    const ev = async (expression, ms = 150000) => {
      const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }, ms);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const open = async (query) => {
      const url = `http://127.0.0.1:${PORT}/web/stage/index.html?${query}`;
      await S("Page.navigate", { url });
      await waitFor(() => ev("!!(window.__stage && (window.__stage.ready || window.__stage.bootError))"), 60000, "the stage to boot");
      const err = await ev("window.__stage.bootError || null");
      if (err) throw new Error(`boot: ${err}`);
      return url;
    };
    const shot = async (file) => { const r = await S("Page.captureScreenshot", { format: "png" }); writeFileSync(file, Buffer.from(r.data, "base64")); return file; };
    const deadline = tLock + BURST_MS;
    await body({ S, ev, open, shot, phase, deadline });
  } catch (e) {
    phase.error = String(e && e.stack || e).slice(0, 1200);
    check(`${name}: the burst ran`, false, phase.error);
  } finally {
    try { if (browser) { await withTimeout(browser.send("Browser.close"), 3000, "Browser.close").catch(() => {}); browser.close(); } } catch { /* gone */ }
    if (chrome && chrome.exitCode === null) {
      await delay(1500);
      if (chrome.exitCode === null) spawnSync("taskkill", ["/T", "/F", "/PID", String(chrome.pid)], { stdio: "ignore" });
    }
    await delay(500);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* a handle may linger */ }
    if (gpu) gpu.release();
    phase.burst_s = +((Date.now() - t0) / 1000).toFixed(1);
    console.log(`burst ${name}: ${phase.burst_s} s`);
  }
}

// ----------------------------------------------------------------------------------------- the page-side probe --
// Evaluated in the page: the renderer string, and a canvas reader (4 x 4 cells of relative luminance and the WCAG red
// quantity, written here on its own: sRGB-decoded, WCAG weights; red = max(0, R - G - B) x 320 over R / (R + G + B) >= 0.8).
const PAGE_PROBE = String.raw`(() => {
  if (window.__probe) return true;
  const canvas = document.getElementById("gl");
  const gl = window.__stage.renderer.gl;
  const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  let buf = null;
  function cells() {
    const w = canvas.width, h = canvas.height, n = w * h * 4;
    if (!buf || buf.length !== n) buf = new Uint8Array(n);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    const L = new Float64Array(16), R = new Float64Array(16), N = new Float64Array(16);
    const bx = [0, 1, 2, 3, 4].map((c) => Math.floor(c * w / 4)), by = [0, 1, 2, 3, 4].map((c) => Math.floor(c * h / 4));
    let mean = 0;
    for (let y = 0; y < h; y++) {
      const cy = y >= by[3] ? 3 : y >= by[2] ? 2 : y >= by[1] ? 1 : 0;
      for (let cx = 0; cx < 4; cx++) {
        let l = 0, r = 0;
        for (let x = bx[cx], i = (y * w + bx[cx]) * 4; x < bx[cx + 1]; x++, i += 4) {
          const R8 = buf[i], G8 = buf[i + 1], B8 = buf[i + 2];
          const lr = LUT[R8], lg = LUT[G8], lb = LUT[B8];
          l += 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
          const s = R8 + G8 + B8;
          if (s > 0 && R8 / s >= 0.8) r += Math.max(0, (lr - lg - lb) * 320);
        }
        const c = cy * 4 + cx;
        L[c] += l; R[c] += r; N[c] += bx[cx + 1] - bx[cx];
      }
    }
    for (let c = 0; c < 16; c++) mean += L[c];
    return { L: Array.from(L, (v, c) => v / N[c]), R: Array.from(R, (v, c) => v / N[c]), N: Array.from(N) };
  }
  function renderer() {
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  }
  window.__probe = { cells, renderer };
  return true;
})()`;

// ---------------------------------------------------------------------------- the verifier's counter, written here --
// Turning points with a hysteresis; a transition is a swing of thr or more between turning points whose darker end is
// under 0.8, counted at its later turning point; flashes in a second = transitions in that second / 2.
function transitions(L, hyst = 0.02, thr = 0.1) {
  const ext = []; let dir = 0, hi = { i: 0, v: L[0] }, lo = { i: 0, v: L[0] }, cand = null;
  for (let i = 1; i < L.length; i++) {
    const v = L[i];
    if (dir === 0) {
      if (v > hi.v) hi = { i, v }; if (v < lo.v) lo = { i, v };
      if (hi.v - lo.v >= hyst) { if (hi.i > lo.i) { ext.push(lo); dir = 1; cand = hi; } else { ext.push(hi); dir = -1; cand = lo; } }
    } else if (dir === 1) { if (v > cand.v) cand = { i, v }; else if (cand.v - v >= hyst) { ext.push(cand); dir = -1; cand = { i, v }; } }
    else { if (v < cand.v) cand = { i, v }; else if (v - cand.v >= hyst) { ext.push(cand); dir = 1; cand = { i, v }; } }
  }
  if (cand) ext.push(cand);
  const tr = [];
  for (let k = 1; k < ext.length; k++) { const a = ext[k - 1], b = ext[k]; if (Math.abs(b.v - a.v) >= thr && Math.min(a.v, b.v) < 0.8) tr.push(b.i); }
  return tr;
}
function maxPerSecond(frames, fps = 60) {
  let best = 0;
  for (let i = 0; i < frames.length; i++) { let n = 0; for (let j = i; j < frames.length && (frames[j] - frames[i]) / fps < 1; j++) n++; best = Math.max(best, n); }
  return best;
}
const WINDOWS = (() => {
  const w = [{ id: "full", r: [0, 0, 3, 3] }];
  for (let by = 0; by < 3; by++) for (let bx = 0; bx < 3; bx++) w.push({ id: `block${bx}${by}`, r: [bx, by, bx + 1, by + 1] });
  for (let r = 0; r < 4; r++) w.push({ id: `row${r}`, r: [0, r, 3, r] });
  for (let c = 0; c < 4; c++) w.push({ id: `col${c}`, r: [c, 0, c, 3] });
  return w;
})();
function judgeFlashes(series) {
  const out = { windows: {}, worst: 0, worst_red: 0, worst_window: "" };
  for (const w of WINDOWS) {
    const [x0, y0, x1, y1] = w.r;
    const L = [], R = [];
    for (const f of series) {
      let l = 0, r = 0, n = 0;
      for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) { const c = cy * 4 + cx; l += f.L[c] * f.N[c]; r += f.R[c] * f.N[c]; n += f.N[c]; }
      L.push(l / n); R.push(r / n);
    }
    const fl = maxPerSecond(transitions(L, 0.02, 0.1)) / 2, fr = maxPerSecond(transitions(R, 2, 20)) / 2;
    out.windows[w.id] = { flashes_per_s: fl, red_flashes_per_s: fr, L_min: +Math.min(...L).toFixed(4), L_max: +Math.max(...L).toFixed(4) };
    if (fl > out.worst) { out.worst = fl; out.worst_window = w.id; }
    out.worst_red = Math.max(out.worst_red, fr);
  }
  return out;
}

// ---------------------------------------------------------------------------------------------------- phases --
const BASE = `w=${W}&h=${H}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`;
const F = 1000 / 60;

async function phaseLoad({ ev, open, shot, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PAGE_PROBE);
  const renderer = await ev("window.__probe.renderer()");
  const judged = judgeRenderer(renderer);
  phase.renderer = renderer;
  check("load: the renderer is SwiftShader (no hardware)", judged.ok, renderer);
  // a few seconds of the show, so the grid locks and the first section starts (timed: SwiftShader's frame cost)
  const tRun = Date.now();
  await ev(`(() => { for (let i = 0; i < 90; i++) window.__vt.step(${F}); window.__stage.renderer.gl.finish(); return true; })()`);
  phase.swiftshader_ms_per_frame = +((Date.now() - tRun) / 90).toFixed(1);
  const st = await ev("window.__stage.state()");
  phase.state = st;
  const want = RIG.counts;
  check(`load: the rig's counts match ${opt.set}.json`, ["heads", "rungs", "projectors", "hazers", "cubes", "cells", "fixtures"].every((k) => st.counts[k] === want[k]),
        { heads: st.counts.heads, rungs: st.counts.rungs, cubes: st.counts.cubes, ring_cells: st.counts.ring_cells, projectors: st.counts.projectors, hazers: st.counts.hazers, cells: st.counts.cells });
  check("load: the beat grid locked and the first section started", st.grid.locked && st.section === "intro", { locked: st.grid.locked, section: st.section });
  // a drop moment on the hero shot: the beams have fragments, the haze is there, the picture is not black
  await ev(`(() => { window.__stage.setShot("FOH_WIDE", 0.5); for (let i = 0; i < 6; i++) window.__vt.step(${F}); return true; })()`);
  // the canvas must be read in the same task as the frame that drew it (preserveDrawingBuffer is off)
  const cells = await ev(`(() => { window.__vt.step(${F}); return window.__probe.cells(); })()`);
  const od = await ev("window.__stage.overdraw()");
  const info = await ev("window.__stage.state().info");
  const mean = cells.L.reduce((s, v, i) => s + v * cells.N[i], 0) / cells.N.reduce((s, v) => s + v, 0);
  phase.frame = { overdraw: od, info, mean_luminance: mean };
  check("load: beams render (beam-pass fragments > 0, lit heads > 0)", od.beams_frags > 0 && info.beams > 0, { beams: info.beams, beam_fragments: od.beams_frags });
  check("load: lasers and LED emitters render", info.lasers > 0 && info.emitters > 1000, { lasers: info.lasers, emitters: info.emitters });
  const haze = await ev("window.__stage.state().haze");
  check("load: haze is in the room (sigma above zero, below the whiteout cap)", haze.sigma0 > 0.003 && haze.sigma0 <= 0.26, haze);
  check("load: the picture is neither black nor blown", mean > 0.004 && mean < 0.6, { mean_relative_luminance: +mean.toFixed(4) });
  await shot(join(outDir, "load-foh.png"));
  const errs = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length;
  const pageErrors = await ev("window.__stage.errors.slice()");
  check("load: no exceptions or console errors", errs === 0 && pageErrors.length === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.filter((c) => /error/.test(c.type)).slice(0, 3), page: pageErrors.slice(0, 3) });
}

async function phaseClock({ ev, open, phase, deadline }) {
  await open(`demo=1&vt=1&${BASE}`);
  // the receipt reads state every frame from inside the page (one evaluate per chunk of frames)
  const RUN = String.raw`((frames) => {
    const s = window.__stage, out = [];
    for (let i = 0; i < frames; i++) {
      window.__vt.step(1000 / 60);
      const t = performance.now(), tEval = t + s.grid.presentLagMs;
      const pos = s.grid.posAt(tEval);
      const st = { t, pos, section: s.state().section, shot: s.director.pose.shot, cut: s.director.pose.cut, why: s.director.pose.cut ? s.director.cuts.at(-1).why : null, u: s.director.pose.u,
                   cam: s.director.pose.pos.slice(), ys: s.strand.poses.map((p) => +p.y.toFixed(4)), rolls: s.strand.poses.map((p) => +p.roll.toFixed(3)),
                   form: s.strand.formation.name, move: !!s.strand.move,
                   headDim: s.programmer.heads[2], cube: s.programmer.pixels[s.rig.cells.kind.indexOf(2) * 4 + 3] };
      out.push(st);
    }
    return out;
  })`;
  const series = [];
  await ev("window.__stage.skipRender = true");      // the clock phase judges the logic, frame by frame; drawing is the other phases'
  phase.drawing = "off (logic only, every 60 fps frame)";
  // the demo: intro 8 bars, build 8, drop 24 (150 BPM: 96 frames a bar). v1: the phrase plays the drop's first 16 bars, so
  // the run goes on into the classic drop (KICK on every downbeat, the strand's unison pulse) after it.
  const total = 18 + 24 * (61 + 64 + 24);
  for (let done = 0; done < total && Date.now() < deadline - 25000; done += 240) {
    series.push(...await ev(`${RUN}(${Math.min(240, total - done)})`, 160000));
  }
  phase.frames = series.length;
  const st = await ev("window.__stage.state()");
  phase.final_state = { grid: st.grid, lands: st.lands, cuts: st.cuts, kicks: st.kicks.slice(0, 8), limiter: st.limiter };
  const g = await ev("({ barAnchor: window.__stage.grid.barAnchor, period: window.__stage.grid.period })");
  // 1. the beats sit on whole numbers: the frames where pos crosses an integer are spaced by the period
  const crossings = [];
  for (let i = 1; i < series.length; i++) if (Math.floor(series[i].pos) > Math.floor(series[i - 1].pos)) crossings.push(i);
  const gaps = crossings.slice(1).map((c, k) => c - crossings[k]);
  check("clock: one beat every 24 frames at 150 BPM (60 fps)", gaps.length > 50 && gaps.every((x) => x === 24 || x === 23 || x === 25), { beats: crossings.length, gap_set: [...new Set(gaps)] });
  // 2. the strand moves: every rung's height changes, and the build lands the lower wave on a bar line
  const span = series[0].ys.map((_, k) => Math.max(...series.map((s) => s.ys[k])) - Math.min(...series.map((s) => s.ys[k])));
  check("clock: the strand moves (every rung travels at least 0.5 m over the run)", span.every((x) => x > 0.5), { travel_m: span.map((x) => +x.toFixed(2)) });
  const lands = st.lands;
  const landOnBar = lands.filter((l) => Math.abs(((l.posLand - g.barAnchor) % 4 + 4) % 4) < 1e-6);
  check("clock: formation changes land on bar lines (time priority)", lands.length >= 1 && landOnBar.length === lands.length, lands);
  // the strand follows its wave: the rung heights move in a travelling wave, phase-shifted by rung (rung 0 leads rung 6)
  const corr = (a, b) => { const ma = a.reduce((s, x) => s + x, 0) / a.length, mb = b.reduce((s, x) => s + x, 0) / b.length; let n = 0, da = 0, db = 0; for (let i = 0; i < a.length; i++) { n += (a[i] - ma) * (b[i] - mb); da += (a[i] - ma) ** 2; db += (b[i] - mb) ** 2; } return n / Math.sqrt(da * db || 1); };
  const tail = series.slice(-600);
  phase.wave_corr_0_6 = +corr(tail.map((s) => s.ys[0]), tail.map((s) => s.ys[6])).toFixed(3);
  // 3. the effects follow the clock: in the drop, the strand heads' unison pulse peaks on beat frames
  const drop = series.filter((s) => s.section === "drop");
  const peaks = [];
  // a peak: a rise of more than 0.02 then a fall (the crossfade between looks makes ripples smaller than that)
  // (a lift: six frames before the peak the light was already at 0.4 or more. In v1 a phrase step blacks the heads, and
  // an entry from black takes the dimmer motor 2.4 frames: that is the motor, not the clock)
  for (let i = 6; i < drop.length - 1; i++) if (drop[i].headDim > drop[i - 1].headDim + 0.02 && drop[i].headDim >= drop[i + 1].headDim && drop[i - 6].headDim >= 0.4) peaks.push(drop[i].pos);
  const off = peaks.map((p) => { const d = p - Math.round(p); return Math.abs(d) * 24; });     // in frames
  phase.off_peaks = peaks.map((p, k) => ({ pos: +p.toFixed(3), frames_off: +off[k].toFixed(2) })).filter((x) => x.frames_off > 1).slice(0, 6);
  phase.drop_dimmer = drop.slice(0, 120).map((s) => [+s.pos.toFixed(3), +s.headDim.toFixed(4)]);
  check("clock: the strand heads' pulse peaks on beat frames (+-1 frame)", peaks.length >= 8 && off.every((x) => x <= 1.01), { peaks: peaks.length, worst_frames: +Math.max(0, ...off).toFixed(2) });
  // KICK lifts (the demo presses pad 1 on every drop downbeat): onset on its beat
  const kicks = st.kicks;
  check("clock: the KICK lift lands on its beat (onset = the beat the press fell on)", kicks.length >= 4 && kicks.every((k) => k.onset === Math.round(k.pressPos) && Math.abs(k.pressPos - k.onset) <= 1 / 24 + 1e-9), kicks.slice(0, 6));
  // 4. sections and cuts on bar lines; no cut faster than 2 beats
  const cuts = [], why = [];
  for (let i = 1; i < series.length; i++) if (series[i].cut) { cuts.push(series[i].pos); why.push(series[i].why); }
  // a phrase's pre-cut lands one beat before the bar line of the step that opens with a flash (v1); every other cut on a bar line
  const cutOff = cuts.map((p, k) => { const q = ((p + (why[k] === "precut" ? 1 : 0) - g.barAnchor) % 4 + 4) % 4; return Math.min(q, 4 - q) * 24; });
  const cutGaps = cuts.slice(1).map((c, k) => c - cuts[k]);
  check("clock: camera cuts fall on bar lines (+-1 frame; a phrase's pre-cut one beat before its flash step's) and never closer than 2 beats", cuts.length >= 3 && cutOff.every((x) => x <= 1.01) && cutGaps.every((x) => x >= 2 - 0.05), { cuts: cuts.length, precuts: why.filter((w) => w === "precut").length, worst_frames: +Math.max(0, ...cutOff).toFixed(2), min_gap_beats: cutGaps.length ? +Math.min(...cutGaps).toFixed(3) : null });
  // 5. the flythrough arrives inside the inner ring on the drop's downbeat
  const lastFly = [...series].reverse().find((s) => s.shot === "STRAND_FLYTHROUGH");
  const firstDrop = series.find((s) => s.section === "drop");
  const ring = [0, 14, -10.5];
  const dist = lastFly ? Math.hypot(lastFly.cam[0] - ring[0], lastFly.cam[1] - ring[1], lastFly.cam[2] - ring[2]) : null;
  check("clock: the strand flythrough arrives inside the inner ring on the downbeat", lastFly && firstDrop && dist < 0.15 && Math.abs(firstDrop.pos - Math.round(firstDrop.pos)) * 24 <= 1.01,
        { last_fly_u: lastFly && +lastFly.u.toFixed(4), metres_from_ring_centre: dist && +dist.toFixed(3), drop_starts_at_pos: firstDrop && +firstDrop.pos.toFixed(4) });
  phase.section_log = [...new Set(series.map((s) => s.section))];
  phase.limiter = st.limiter;
}

async function phaseEngine({ ev, open, phase }) {
  // real time: the fake engine's stream
  await open(`engine=http://127.0.0.1:${ENGINE_PORT}&${BASE}`);
  await waitFor(() => ev("window.__stage.state().engine.open"), 15000, "the engine link");
  send({ t: "hello", v: 1, src: "stage-fake", beat_engine: "fake", pads_mode: "both", leds: false });
  const bpm = 140, period = 60000 / bpm;
  const t0 = Date.now();
  let n = 0, ver = 0;
  const posLog = [];
  while (Date.now() - t0 < 9000) {
    const now = Date.now() - t0;
    const due = n * period + 400 - now;
    if (due < 260) {
      if (n === 12) ver = 1;                 // a tap: the engine re-anchors (and shifts the beat by 120 ms from here)
      send({ t: "beat", due_ms: due + (ver ? 120 : 0), bpm, conf: 0.9, n, on_beat: 0.9, bar: (n % 4) + 1, bar_src: "tap", ver });
      n++;
    }
    if (n === 6 && !phase.padSent) { send({ t: "pad", pad: 1, vel: 0.9, on: true, src: "daw" }); send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "daw" }); phase.padSent = true; }
    if (n === 7 && !phase.padOff) { send({ t: "pad", pad: 2, vel: 0, on: false, src: "daw" }); phase.padOff = true; }
    if (n % 2 === 0) posLog.push(await ev("({ pos: window.__stage.state().pos, bpm: window.__stage.grid.bpm })"));
    await delay(30);
  }
  const st = await ev("window.__stage.state()");
  phase.state = { bpm: st.bpm, grid: st.grid, engine: st.engine, kicks: st.kicks, laserHits: await ev("window.__stage.lasers.count") };
  check("engine: the hello arrived and the link is open", st.engine.open && st.engine.hello && st.engine.hello.src === "stage-fake", st.engine);
  check("engine: the grid follows the engine's tempo (140 BPM) and its ver re-anchor", Math.abs(st.bpm - 140) < 0.01 && st.grid.vers >= 1 && st.grid.locked, st.grid);
  check("engine: pads reach the rig (pad 1 KICK, pad 2 lasers)", st.kicks.length >= 1 && phase.state.laserHits >= 1, { kicks: st.kicks.length, laser_hits: phase.state.laserHits });
  let mono = true; for (let i = 1; i < posLog.length; i++) if (posLog[i].pos < posLog[i - 1].pos - 1e-9) mono = false;
  check("engine: the beat position never runs backward through the tap", mono, { samples: posLog.length });
}

// The op-count estimate for an RX 6600 (8.9 TFLOPS FP32, 224 GB/s, 32 MB Infinity Cache), per pass, at this frame's
// size: fragments x ALU ops per fragment / (peak x 35 % utilisation) + bytes moved / (bandwidth x 70 %). The ops per
// fragment are counted by hand from shaders.js (a texture fetch counted as 8 ALU-equivalent ops; transcendentals
// as 4-8): beams 120 setup + 6 samples x ~260 (the haze density with its 8 plumes ~140, the HG lobe ~25, the profile
// ~25, tan/sqrt/exp ~40, the rest ~30); lasers ~230; emitters ~25; lit surfaces ~40 per spot light x the lit heads plus
// ~40 (the opaque pass's fragments are not counted here: the estimate takes 1.6 x the frame, the hall and the crowd
// fill the frame about once and a half); composite ~45; bloom 13 taps down + 9 up per level; finish ~110 (display-out);
// meter 16 fetches per texel over two levels; present ~20. Bytes: RGBA16F = 8 B, 4x MSAA colour + depth = 48 B per
// pixel written plus the resolve. An estimate until the real-GPU bench replaces it (design slice S10).
function rx6600Estimate(od, info) {
  const px = W * H, peak = 8.9e12 * 0.35, bw = 224e9 * 0.7;
  const ms = (frags, ops, bytes) => +(((frags * ops) / peak + bytes / bw) * 1000).toFixed(3);
  const bloomPx = [1, 2, 3, 4, 5, 6].reduce((s, i) => s + px / 4 ** i, 0);
  const beamPx = od.beam_target[0] * od.beam_target[1];
  const spots = Math.min(32, info.beams || 0);
  const out = {
    opaque: ms(px * 1.6, 40 + 40 * spots, px * (48 + 8 + 4)),
    emitters: ms(od.emit_frags, 25, od.emit_frags * 16),
    lasers: ms(od.laser_frags, 230, od.laser_frags * 16),
    beams: ms(od.beams_frags, 120 + 6 * 260, beamPx * 8 + od.beams_frags * 16),
    composite: ms(px, 45, px * (8 + 8 + 4 + 8)),
    bloom: ms(bloomPx * 2, 22 * 8, bloomPx * 8 * 14),
    finish: ms(px, 110, px * (8 + 2 + 4)),
    meter_and_present: ms(px / 16 + px, 16 * 8 / 16 + 20, px * (4 + 4 + 4 + 4)),
  };
  out.total = +Object.values(out).reduce((s, v) => s + v, 0).toFixed(2);
  out.model = "frags x ops / (8.9 TFLOPS x 0.35) + bytes / (224 GB/s x 0.7); hand-counted ops from shaders.js";
  return out;
}

async function phaseCost({ ev, open, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  // into the drop (bar 16), then profile three shots
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 16 + 60; i++) window.__vt.step(${F}); s.skipRender = false; return true; })()`, 170000);
  const shots = ["FOH_WIDE", "TUNNEL_UP", "STRAND_FLYTHROUGH"];
  phase.shots = {};
  for (const id of shots) {
    await ev(`(() => { const s = window.__stage; s.setShot(${JSON.stringify(id)}, ${id === "STRAND_FLYTHROUGH" ? 0.55 : 0.5}); for (let i = 0; i < 3; i++) window.__vt.step(${F}); s.profile(true); for (let i = 0; i < 8; i++) window.__vt.step(${F}); s.profile(false); return true; })()`, 170000);
    const t = await ev("window.__stage.timings()");
    const od = await ev("window.__stage.overdraw()");
    const info = await ev("window.__stage.state().info");
    const per = {}; let total = 0;
    for (const [k, v] of Object.entries(t)) { per[k] = +(v.sum / v.n).toFixed(2); total += v.sum / v.n; }
    phase.shots[id] = { pass_ms: per, total_ms: +total.toFixed(1), overdraw: od, info, rx6600: rx6600Estimate(od, info) };
  }
  // the frame time with each feature off (FOH_WIDE)
  phase.features = {};
  await ev(`window.__stage.setShot("FOH_WIDE", 0.5)`);
  const frameMs = async () => ev(`(() => { const t = []; for (let i = 0; i < 6; i++) { const t0 = Date.now(); window.__vt.step(${F}); window.__stage.renderer.gl.finish(); t.push(Date.now() - t0); } t.sort((a, b) => a - b); return t[2]; })()`, 170000);
  phase.features.all = await frameMs();
  for (const f of ["beams", "lasers", "emitters", "crowd", "bloom"]) {
    await ev(`window.__stage.features({ ${f}: false })`);
    phase.features[`without_${f}`] = await frameMs();
    await ev(`window.__stage.features({ ${f}: true })`);
  }
  check("cost: profiled three shots and five features", Object.keys(phase.shots).length === 3, { foh_total_ms: phase.shots.FOH_WIDE.total_ms });
}

async function phaseStorm(ctx) { return phaseFlash(ctx, true); }
async function phaseFlash({ ev, open, phase, deadline }, storm = false) {
  const scale = Number(opt["flash-scale"]) || 1;
  const fw = Math.round(W * scale), fh = Math.round(H * scale);
  await open(`demo=1&vt=1&w=${fw}&h=${fh}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`);
  await ev(PAGE_PROBE);
  // fast-forward to two bars before the drop (bar 14), at 6 frames a step (the show's own logic runs every step)
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 14 - 30; i++) window.__vt.step(${F}); s.skipRender = false; for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`, 170000);
  const lim0 = await ev("window.__stage.limiter.stats()");
  const laser0 = await ev("({ onsets: window.__stage.lasers.count, presses: window.__stage.lasers.presses || 0 })");
  // then every frame: the drop's KICKs and FLY-OUT come from the demo; on top, a laser pad storm (pad 2 every 4 frames
  // for a second, then a held gate) and the director's cuts
  const RUN = String.raw`((frames, storm0, storm) => {
    const s = window.__stage, out = [];
    for (let i = 0; i < frames; i++) {
      const f = storm0 + i;
      if (storm && f >= 140 && f < 200 && f % 4 === 0) s.press(2, 1);
      if (storm && f >= 140 && f < 200 && f % 4 === 2) s.release(2);
      if (storm && f === 230) s.press(2, 1);
      if (storm && f === 290) s.release(2);
      window.__vt.step(1000 / 60);
      const c = window.__probe.cells();
      const g = s.renderer.info.gains;
      out.push({ L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, section: s.state().section, shot: s.director.pose.shot,
                 lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0 });
    }
    return out;
  })`;
  const series = [];
  const want = Math.round(Number(opt["flash-seconds"]) * 60);
  const t0 = Date.now();
  for (let done = 0; done < want && Date.now() < deadline - 20000; done += 60) {
    series.push(...await ev(`${RUN}(${Math.min(60, want - done)}, ${done}, ${storm ? "true" : "false"})`, 160000));
  }
  phase.frames = series.length;
  phase.ms_per_frame = +((Date.now() - t0) / Math.max(1, series.length)).toFixed(0);
  phase.size = [fw, fh];
  const j = judgeFlashes(series);
  phase.judged = { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red, full: j.windows.full, windows: j.windows };
  phase.limited_frames = series.map((x, i) => (x.lim ? i : -1)).filter((i) => i >= 0).slice(0, 80);
  phase.full_series = series.slice(0, 160).map((x) => +(x.L.reduce((a, v, i) => a + v * x.N[i], 0) / x.N.reduce((a, v) => a + v, 0)).toFixed(4));
  phase.timeline = series.map((x, i) => [i, x.section, x.shot]).filter((r, i, a) => i === 0 || r[1] !== a[i - 1][1] || r[2] !== a[i - 1][2]);
  phase.sections = [...new Set(series.map((s) => s.section))];
  phase.shots = [...new Set(series.map((s) => s.shot))];
  const lim1 = await ev("window.__stage.limiter.stats()");
  const laser1 = await ev("({ onsets: window.__stage.lasers.count, presses: window.__stage.lasers.presses || 0 })");
  phase.lasers = { presses: laser1.presses - laser0.presses, onsets: laser1.onsets - laser0.onsets };
  phase.limiter = { interventions: lim1.interventions - lim0.interventions, frames: lim1.frames - lim0.frames, beta_frames: lim1.beta_frames - lim0.beta_frames, log: lim1.log };
  const what = storm ? "the build's held laser gate into the drop, KICKs, FLY-OUT, the cut, plus a laser pad storm (15 presses a second for a second, then a held gate)"
                     : "the demo as programmed: the build's held laser gate, the flythrough, the cut into the drop, KICKs and FLY-OUT";
  const tag = storm ? "storm" : "flash";
  check(`${tag}: at most 3 flashes a second in every window, red at most 3 (${series.length} frames, ${fw}x${fh}: ${what})`,
        series.length >= 240 && j.worst <= 3 && j.worst_red <= 3, { worst: j.worst, window: j.worst_window, worst_red: j.worst_red, frames: series.length });
  if (storm) phase.note = "a pad storm on the lasers is the final limiter's job in v0 (the predictive governor is v1): interventions are reported, not failed";
  else check("flash: the stage's limiter recorded zero interventions (the programmed show stays inside the budget)", phase.limiter.interventions === 0, phase.limiter);
}

// A diagnostic burst (not part of the default run): which layer swings the frame during the build's flythrough. Four
// segments of 48 frames (two beats at 150 BPM), each with one layer off, and each window's range and swing count.
async function phaseDiag({ ev, open, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PAGE_PROBE);
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 14 - 10; i++) window.__vt.step(${F}); s.skipRender = false; for (let i = 0; i < 10; i++) window.__vt.step(${F}); return true; })()`, 170000);
  phase.segments = {};
  for (const off of ["none", "beams", "lasers", "emitters", "crowd"]) {
    const r = await ev(`(() => { const s = window.__stage; s.features({ beams: true, lasers: true, emitters: true, crowd: true }); ${off !== "none" ? `s.features({ ${off}: false });` : ""}
      s.resetLimiter(); const out = [];
      for (let i = 0; i < 48; i++) { window.__vt.step(${F}); const c = window.__probe.cells(); out.push(c.L.reduce((a, v) => a + v, 0) / 16); }
      return out; })()`, 120000);
    let swings = 0; for (let i = 1; i < r.length; i++) if (Math.abs(r[i] - r[i - 1]) > 0.03) swings++;
    phase.segments[off] = { min: +Math.min(...r).toFixed(3), max: +Math.max(...r).toFixed(3), mean: +(r.reduce((a, v) => a + v, 0) / r.length).toFixed(3),
                            frame_jumps_over_0_03: swings, series: r.map((v) => +v.toFixed(3)) };
  }
  check("diag: ran", true, Object.fromEntries(Object.entries(phase.segments).map(([k, v]) => [k, { min: v.min, max: v.max, mean: v.mean, jumps: v.frame_jumps_over_0_03 }])));
}

// A diagnostic burst (not part of the default run): what each target holds on a few shots.
async function phaseProbe({ ev, open, shot, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PAGE_PROBE);
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 17; i++) window.__vt.step(${F}); s.skipRender = false; return true; })()`, 170000);
  phase.shots = {};
  for (const id of ["FOH_WIDE", "TUNNEL_UP", "TOPDOWN_GODVIEW"]) {
    const r = await ev(`(() => { const s = window.__stage; s.setShot(${JSON.stringify(id)}, 0.5); for (let i = 0; i < 3; i++) window.__vt.step(${F});
      const c = window.__probe.cells(); const mean = c.L.reduce((a, v) => a + v, 0) / 16;
      return { mean: +mean.toFixed(4), targets: s.debugTargets(), gains: s.renderer.info.gains, limiter: s.limiter.stats().interventions }; })()`, 120000);
    phase.shots[id] = r;
    await shot(join(outDir, `probe-${id}.png`));
  }
  check("probe: ran", true, Object.fromEntries(Object.entries(phase.shots).map(([k, v]) => [k, { mean: v.mean, hdr: v.targets.hdr, gains: v.gains }])));
}

async function phaseSheet({ ev, open, shot, phase }) {
  if (!sheetDir) { phase.skipped = "no --sheet-dir"; return; }
  await open(`demo=1&vt=1&${BASE}`);
  const plan = [
    // [label, bar to run to, shot, u]
    ["intro-foh", 3, "FOH_HOLD_ZOOM", 0.6],
    ["intro-tribune", 6, "TRIBUNE_34", 0.6],
    ["build-flythrough", 12, "STRAND_FLYTHROUGH", 0.45],
    ["build-crane", 13, "CRANE_RISE_REVEAL", 0.9],
    ["drop-foh-wide", 16.06, "FOH_WIDE", 0.5],
    ["drop-tunnel-up", 17, "TUNNEL_UP", 0.5],
    ["drop-orbit", 19, "HEAD_ORBIT", 0.35],
    ["drop-rings", 21, "WORM_RING", 0.5],
    ["drop-topdown", 23, "TOPDOWN_GODVIEW", 0.5],
    ["drop-crowd", 25, "CROWD_POV", 0.5],
  ];
  phase.shots = [];
  let bar = 0;
  for (const [label, toBar, id, u] of plan) {
    const frames = Math.max(0, Math.round((toBar - bar) * 96));
    await ev(`(() => { const s = window.__stage; s.clearShot(); s.skipRender = true; for (let i = 0; i < ${frames}; i++) window.__vt.step(${F}); s.skipRender = false; s.setShot(${JSON.stringify(id)}, ${u}); for (let i = 0; i < 2; i++) window.__vt.step(${F}); return true; })()`, 170000);
    bar = toBar;
    const file = await shot(join(sheetDir, `${label}.png`));
    const st = await ev("window.__stage.state()");
    phase.shots.push({ label, file, section: st.section, formation: st.formation, beams: st.info.beams, lasers: st.info.lasers });
  }
  check("sheet: ten signature shots captured", phase.shots.length === plan.length, phase.shots.map((s) => `${s.label}:${s.section}`));
}

// ============================================================================================== v1: the phrase --
// Daniel, 2026-10-25: "3 levels of light all shooting over the crowd ... top, midle then bottom pan up and down
// sequentially. or horizontal flash and pan, then vertical 1, 2, 3 then back to lasers, then a cool pattern of lights from
// the circular halo." The v1 phases prove the phrase in the real page: its steps land on their lines, the thirds and the
// columns fire in order, the ring effects and the laser groups answer it, and three minutes of the programmed demo with
// the crowd on, through every camera shot, never make the final limiter act.
const DROP_BEAT = 61;                                  // the demo's first drop (intro and build: 16 bars from beat -3)
const frameOfBeat = (b) => Math.round(18 + b * 24);    // virtual clock: the demo's beat b falls on this frame from load

// A page-side recorder: the phrase's state and the FrameState measures, one entry per 60 fps frame.
const PHRASE_PROBE = String.raw`(() => {
  if (window.__ph) return true;
  const s = window.__stage, R = s.rig, P = s.programmer, HF = 16;
  const G = (n) => R.groups[n];
  const thirds = ["halo.top", "halo.mid", "halo.bot"].map(G);
  const vert = G("vert"), depth = G("vert.depth"), hrow = G("hrow"), r0 = G("rings.r0.slats"), slats = G("rings.slats");
  const idx = (g, key, v) => Array.from({ length: g.n }, (_, m) => m).filter((m) => g.keys[key][m] === v);
  const cols = [0, 1, 2].map((c) => idx(vert, "column", c)), deps = [0, 1, 2].map((c) => idx(depth, "depth", c));
  const md = (g, list) => { let a = 0; const L = list || Array.from({ length: g.n }, (_, m) => m); for (const m of L) a += P.heads[g.members[m] * HF + 2]; return a / L.length; };
  const ang = Array.from(r0.keys.angle);
  window.__ph = { rec(frames) {
    const out = [];
    for (let i = 0; i < frames; i++) {
      window.__vt.step(1000 / 60);
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
      const st = s.runner.status(), pose = s.director.pose, o = s.lasers.out;
      const lh = new Set();
      for (let k = o.groupStart; k < o.groupStart + o.groups; k++) lh.add(o.seg[k * 16 + 13]);
      let lo = Infinity; for (let m = 0; m < r0.n; m++) lo = Math.min(lo, P.pixels[r0.members[m] * 4 + 3]);
      let re = 0, im = 0, w = 0;
      for (let m = 0; m < r0.n; m++) { const d = P.pixels[r0.members[m] * 4 + 3] - lo; re += d * Math.cos(2 * ang[m]); im += d * Math.sin(2 * ang[m]); w += d; }
      let rs = 0, n = 0;
      for (let m = 0; m < slats.n; m += 16) { const c = slats.members[m] * 4, t = P.pixels[c] + P.pixels[c + 1] + P.pixels[c + 2]; if (t > 1e-6) { rs += P.pixels[c] / t; n++; } }
      out.push({ pos: +pos.toFixed(5), st: st.state === "running" ? [st.step, +st.start.toFixed(4), st.variant, st.repeat] : null,
                 th: thirds.map((g) => +md(g).toFixed(4)), col: cols.map((L) => +md(vert, L).toFixed(4)), dep: deps.map((L) => +md(depth, L).toFixed(4)),
                 pan: +P.heads[hrow.members[0] * HF].toFixed(2), hd: +md(hrow).toFixed(4), lh: [...lh],
                 h2: w > 1e-6 ? [+(Math.hypot(re, im) / w).toFixed(4), +Math.atan2(im, re).toFixed(4)] : [0, 0],
                 bump: n ? +(rs / n).toFixed(4) : 0, cut: pose.cut ? [pose.shot, s.director.cuts.at(-1).why] : null, shot: pose.shot,
                 section: s.show.section && s.show.section.name });
    }
    return out;
  } };
  return true;
})()`;

async function phasePhrase({ ev, open, phase, deadline }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PHRASE_PROBE);
  await ev("window.__stage.skipRender = true");
  phase.drawing = "off (logic only, every 60 fps frame of the real page)";
  const start = frameOfBeat(DROP_BEAT - 2), total = 24 * (64 + 4);
  await ev(`(() => { for (let i = 0; i < ${start}; i++) window.__vt.step(${F}); return true; })()`, 160000);
  const rec = [];
  for (let done = 0; done < total && Date.now() < deadline - 20000; done += 400) rec.push(...await ev(`window.__ph.rec(${Math.min(400, total - done)})`, 160000));
  phase.frames = rec.length;
  const st = await ev(`({ log: window.__stage.runner.log.slice(0, 40), grants: window.__stage.programmer.flashGate.grants.slice(), refusals: window.__stage.programmer.flashGate.refusals.slice(),
                         barAnchor: window.__stage.grid.barAnchor, groups: window.__stage.lasers.groupStats, laserGroups: Object.fromEntries(Object.entries(window.__stage.rig.laserGroups).map(([k, v]) => [k, v.heads])) })`);
  phase.runner_log = st.log;
  const FB = 1 / 24;
  const onBar = (p) => { const q = ((p - st.barAnchor) % 4 + 4) % 4; return Math.min(q, 4 - q) < 1e-6; };
  // 1. the steps land on their lines (0-1 frame): the first frame of each step
  const firsts = [];
  for (let i = 0; i < rec.length; i++) {
    const a = rec[i].st, b = i ? rec[i - 1].st : null;
    if (a && (!b || a[0] !== b[0] || a[1] !== b[1])) firsts.push({ step: a[0], start: a[1], variant: a[2], repeat: a[3], pos: rec[i].pos });
  }
  phase.steps = firsts;
  const late = firsts.map((f) => (f.pos - f.start) / FB);
  check("phrase: every step starts on its bar line, on its first frame (0-1 frame)", firsts.length >= 10 && firsts.every((f) => onBar(f.start)) && late.every((x) => x >= -1e-6 && x <= 1.01),
        { steps: firsts.length, worst_frames_late: +Math.max(...late).toFixed(3), sequence: firsts.map((f) => `${f.step}@${f.start}`).join(" ") });
  // 2. the thirds fire in order, one per beat (bottom first when the repeat ascends; top+bottom / middle for pinch)
  const want = (variant, b) => variant === "ascend" ? [[0, 0, 1], [0, 1, 0], [1, 0, 0]][b % 3] : variant === "pinch" ? (b % 2 ? [0, 1, 0] : [1, 0, 1]) : [[1, 0, 0], [0, 1, 0], [0, 0, 1]][b % 3];
  const bad = [];
  let judged = 0;
  for (const r of rec) {
    if (!r.st || r.st[0] !== "A") continue;
    const age = r.pos - r.st[1], b = Math.floor(age + 1e-9), frac = age - b;
    if (frac < 0.25 || frac > 0.75) continue;                       // mid-beat: away from the edges
    const lit = r.th.map((v) => (v > 0.5 ? 1 : 0)), w = want(r.st[2], b);
    judged++;
    if (lit.join("") !== w.join("")) bad.push({ pos: r.pos, variant: r.st[2], beat: b, lit: lit.join(""), want: w.join("") });
  }
  check("phrase: the thirds fire in order one per beat (top, middle, bottom; ascend reverses; pinch: top+bottom, middle)", judged > 100 && bad.length === 0, { judged_frames: judged, wrong: bad.slice(0, 4) });
  // 3. the verticals fire 1, 2, 3 on beats 1-3, dark on beat 4 (depth: stage, z 30, z 55)
  const vbad = [];
  let vj = 0;
  for (const r of rec) {
    if (!r.st || r.st[0] !== "C") continue;
    const age = r.pos - r.st[1], b = Math.floor(age + 1e-9), frac = age - b;
    if (frac < 0.25 || frac > 0.75) continue;
    const v = r.st[2] === "depth" ? r.dep : r.col;
    const lit = v.map((x) => (x > 0.5 ? 1 : 0)).join("");
    const k = r.st[2] === "ascend" ? 2 - b : b;
    const w = b === 3 ? "000" : [0, 1, 2].map((c) => (c === k ? 1 : 0)).join("");
    vj++;
    if (lit !== w) vbad.push({ pos: r.pos, variant: r.st[2], beat: b, lit, want: w });
  }
  check("phrase: verticals 1-2-3 in order on beats 1-3, dark on beat 4 (depth variant: stage, z 30, z 55)", vj > 40 && vbad.length === 0, { judged_frames: vj, wrong: vbad.slice(0, 4) });
  // 4. the horizontal: one FlashGate grant per B on its ONE; the row holds 0.6 or more after the flash
  const Bs = firsts.filter((f) => f.step === "B").map((f) => f.start);
  const hold = rec.filter((r) => r.st && r.st[0] === "B" && r.pos - r.st[1] > 0.75).map((r) => r.hd);
  check("phrase: exactly one FlashGate grant per horizontal step, on its ONE; the row holds >= 0.6 after it", JSON.stringify(st.grants) === JSON.stringify(Bs) && st.refusals.length === 0 && Math.min(...hold) >= 0.6 - 1e-6,
        { grants: st.grants, b_steps: Bs, refusals: st.refusals, min_hold: +Math.min(...hold).toFixed(3) });
  // 5. the ring effects run: the bump swaps once a beat in A; the chopper is two blades at a turn a beat in E, its
  //    direction alternating repeat to repeat
  const bumpA = rec.filter((r) => r.st && r.st[0] === "A");
  let bestP = 0, best = 0;
  for (let P = 0.5; P <= 3.0001; P += 0.01) { let re = 0, im = 0; for (const r of bumpA) { re += r.bump * Math.cos(2 * Math.PI * r.pos / P); im += r.bump * Math.sin(2 * Math.PI * r.pos / P); } const a = Math.hypot(re, im); if (a > best) { best = a; bestP = P; } }
  const Es = firsts.filter((f) => f.step === "E");
  const chop = Es.slice(0, 2).map((e0) => {
    const E = rec.filter((r) => r.st && r.st[0] === "E" && r.st[1] === e0.start && r.pos - r.st[1] > 0.05 && r.pos - r.st[1] < 2.9);
    if (E.length < 20) return null;
    const amp = E.reduce((a, r) => a + r.h2[0], 0) / E.length;
    const a2 = [E[0].h2[1] / 2];
    for (let i = 1; i < E.length; i++) { let d = E[i].h2[1] / 2 - E[i - 1].h2[1] / 2; while (d > Math.PI / 2) d -= Math.PI; while (d < -Math.PI / 2) d += Math.PI; a2.push(a2.at(-1) + d); }
    const xs = E.map((r) => r.pos), n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = a2.reduce((a, b) => a + b) / n;
    let sxy = 0, sxx = 0; for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (a2[i] - my); sxx += (xs[i] - mx) ** 2; }
    const turns = sxy / sxx / (2 * Math.PI);
    const within = a2.filter((a, i) => Math.abs(a - (my + (sxy / sxx) * (xs[i] - mx))) <= Math.PI / 6).length / n;
    return { amp: +amp.toFixed(3), turns_per_beat: +turns.toFixed(3), within_30deg: +within.toFixed(3) };
  });
  phase.ring = { bump_period_beats: +bestP.toFixed(2), chopper: chop };
  check("phrase: the ring effects run (the colour bump swaps once a beat in A; the chopper: two blades, 1 turn a beat +-5 %, the direction alternating, 90 %+ of frames on the fit)",
        Math.abs(bestP - 1) <= 0.05 && chop.length === 2 && chop.every((c) => c && c.amp >= 0.6 && Math.abs(Math.abs(c.turns_per_beat) - 1) <= 0.05 && c.within_30deg >= 0.9) && Math.sign(chop[0].turns_per_beat) !== Math.sign(chop[1].turns_per_beat),
        phase.ring);
  // 6. the laser groups answer the phrase: A = the lit third's halo lasers; D = the lasers enter on its ONE from the banks
  //    it names; E = the rim corona on the halo lasers plus the core
  const halo = (lv) => st.laserGroups[["halo.lasers.top", "halo.lasers.mid", "halo.lasers.bot"][lv]];
  let aOk = 0, aN = 0;
  for (const r of rec) {
    if (!r.st || r.st[0] !== "A" || !r.lh.length) continue;
    const age = r.pos - r.st[1], b = Math.floor(age + 1e-9), frac = age - b;
    if (frac < 0.25 || frac > 0.75 || r.st[2] === "pinch") continue;
    const k = r.st[2] === "ascend" ? 2 - (b % 3) : b % 3;
    aN++;
    if (r.lh.every((h) => halo(k).includes(h)) && r.lh.length === halo(k).length) aOk++;
  }
  const dFirst = firsts.filter((f) => f.step === "D").map((f) => { const r = rec.find((x) => x.pos >= f.start - 1e-6 && x.lh.length); return r ? +((r.pos - f.start) / FB).toFixed(2) : null; });
  const banks = new Set(st.laserGroups.lasers);
  const dOk = rec.filter((r) => r.st && r.st[0] === "D" && r.lh.length).every((r) => r.lh.every((h) => banks.has(h)));
  const eHeads = new Set(rec.filter((r) => r.st && r.st[0] === "E").flatMap((r) => r.lh));
  const eHalo = st.laserGroups["halo.lasers"].filter((h) => eHeads.has(h)).length;
  phase.lasers = { a_frames: aN, a_matching: aOk, d_first_laser_frames: dFirst, d_from_named_banks: dOk, e_halo_spokes_seen: eHalo, group_stats: st.groups };
  check("phrase: the laser groups answer the phrase (A: the lit third's halo lasers; D: in on its ONE +-1 frame, from the named banks; E: the halo spokes)",
        aN > 50 && aOk / aN >= 0.98 && dFirst.length >= 2 && dFirst.every((x) => x !== null && x <= 1.01) && dOk && eHalo === 12, phase.lasers);
  // 7. the phrase's cuts: on bar lines, except the pre-cut one beat before each horizontal flash
  const cuts = rec.filter((r) => r.cut && r.st).map((r) => ({ pos: r.pos, shot: r.cut[0], why: r.cut[1] }));
  const cutBad = cuts.filter((c) => {
    if (c.why === "precut") return !Bs.some((b) => Math.abs(c.pos - (b - 1)) <= FB * 1.01);
    const q = ((c.pos - st.barAnchor) % 4 + 4) % 4; return Math.min(q, 4 - q) > FB * 1.01;
  });
  phase.cuts = cuts;
  check("phrase: camera cuts on bar lines (+-1 frame), and the cut into the horizontal step one beat before its flash, never on the flash frame",
        cuts.length >= 8 && cutBad.length === 0 && !cuts.some((c) => Bs.some((b) => Math.abs(c.pos - b) <= FB * 1.01)), { cuts: cuts.length, wrong: cutBad.slice(0, 4) });
}

// The picture measures (rendered, read back): a test phrase is injected into the page's runner (the set file is not
// touched) and played with the demo's pads off and the camera held; frames are read from the canvas.
const PICTURE_PROBE = String.raw`(() => {
  if (window.__pic) return true;
  const s = window.__stage, canvas = document.getElementById("gl"), gl = s.renderer.gl;
  const LUT = new Float32Array(256).map((_, i) => { const v = i / 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  let buf = null;
  const read = () => { const w = canvas.width, h = canvas.height; if (!buf || buf.length !== w * h * 4) buf = new Uint8Array(w * h * 4); gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf); return { w, h }; };
  const lumAt = (x, y, w) => { const i = (y * w + x) * 4; return 0.2126 * LUT[buf[i]] + 0.7152 * LUT[buf[i + 1]] + 0.0722 * LUT[buf[i + 2]]; };
  // a world point to canvas pixels (readPixels rows run bottom-up)
  const project = (p) => { const cam = s.renderer.camera; const v = { x: p[0], y: p[1], z: p[2] };
    const e = cam.matrixWorldInverse.elements, q = cam.projectionMatrix.elements;
    const vx = e[0] * v.x + e[4] * v.y + e[8] * v.z + e[12], vy = e[1] * v.x + e[5] * v.y + e[9] * v.z + e[13], vz = e[2] * v.x + e[6] * v.y + e[10] * v.z + e[14];
    const cx = q[0] * vx + q[4] * vy + q[8] * vz + q[12], cy = q[1] * vx + q[5] * vy + q[9] * vz + q[13], cw = q[3] * vx + q[7] * vy + q[11] * vz + q[15];
    return [(cx / cw * 0.5 + 0.5) * canvas.width, (cy / cw * 0.5 + 0.5) * canvas.height, cw > 0]; };
  window.__pic = {
    // the mean relative luminance of horizontal strips centred on canvas rows (bottom-up), each +-half rows
    strips(rows, half) { const { w, h } = read(); return rows.map((r) => { let a = 0, n = 0; for (let y = Math.max(0, Math.round(r - half)); y <= Math.min(h - 1, Math.round(r + half)); y++) for (let x = 0; x < w; x += 2) { a += lumAt(x, y, w); n++; } return n ? a / n : 0; }); },
    // the luminance and redness at projected points (3 x 3 px around each)
    points(pts) { const { w, h } = read(); return pts.map(([x, y]) => { let a = 0, r = 0, b = 0, n = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const X = Math.round(x) + dx, Y = Math.round(y) + dy; if (X < 0 || Y < 0 || X >= w || Y >= h) continue; const i = (Y * w + X) * 4; a += lumAt(X, Y, w); r += LUT[buf[i]]; b += LUT[buf[i + 2]]; n++; } return n ? [a / n, r / n, b / n] : [0, 0, 0]; }); },
    // the whole frame: mean luminance, lit share (luminance >= 0.05) and true-black share (every channel <= 8 of 255)
    frame() { const { w, h } = read(); let a = 0, lit = 0, black = 0; const n = w * h, hist = new Uint32Array(256); for (let i = 0; i < n; i++) { const L = 0.2126 * LUT[buf[i * 4]] + 0.7152 * LUT[buf[i * 4 + 1]] + 0.0722 * LUT[buf[i * 4 + 2]]; a += L; if (L >= 0.05) lit++; const mx = Math.max(buf[i * 4], buf[i * 4 + 1], buf[i * 4 + 2]); hist[mx]++; if (mx <= 8) black++; }
      let acc = 0, med = 0; for (let v = 0; v < 256; v++) { acc += hist[v]; if (acc >= n / 2) { med = v; break; } } return { mean: a / n, lit: lit / n, black: black / n, median_max_channel: med }; },
    // a frame kept for a later comparison, and the mean absolute luminance difference against it
    keep(name) { const { w, h } = read(); const L = new Float32Array(w * h); for (let i = 0; i < w * h; i++) L[i] = 0.2126 * LUT[buf[i * 4]] + 0.7152 * LUT[buf[i * 4 + 1]] + 0.0722 * LUT[buf[i * 4 + 2]]; (window.__kept ||= {})[name] = L; return true; },
    size() { return [canvas.width, canvas.height]; },
    // the luminance at the exact pixel of each point (no neighbours); reads the frame
    centres(pts) { const { w, h } = read(); return pts.map(([x, y]) => { const X = Math.round(x), Y = Math.round(y); return X < 0 || Y < 0 || X >= w || Y >= h ? 0 : lumAt(X, Y, w); }); },
    diff(a, b) { const A = window.__kept[a], B = window.__kept[b]; let d = 0, m = 0; for (let i = 0; i < A.length; i++) { d += Math.abs(A[i] - B[i]); m += (A[i] + B[i]) / 2; } return { mean_abs: d / A.length, mean: m / A.length, relative: m > 0 ? d / m : 0 }; },
    project,
  };
  return true;
})()`;
// A test phrase (one step) for the picture measures: everything dark but what the measure needs.
const darkLines = [{ group: "heads.all", values: { Dimmer: 0 } }, { group: "leds.all", values: { Dimmer: 0 } }];
function testPhrase(id, lines, beats, shot) {
  return { name: id, bars: beats / 4 + 1, steps: [{ id: "Z", name: "dark lead-in", beats: 4, trigger: "follow", lines: darkLines, camera: { shot } },
                                                  { id: "T", name: id, beats, trigger: "follow", lines: [...darkLines, ...lines] }] };
}
const LEVELS_LINE = (eff) => ({ group: "halo", preset: "layers", values: { Dimmer: 0, Zoom: 1.2, Color: "beamA" }, effects: [eff] });
// Returns the beat the measured step starts on (after the dark lead-in when the phrase has one).
async function startTestPhrase(ev, id, def, shot) {
  return ev(`(() => { const s = window.__stage; s.show.padRules = []; s.rig.phrases[${JSON.stringify(id)}] = ${JSON.stringify(def)};
    const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs); const at = s.grid.nextBarPos(pos);
    s.runner.start(${JSON.stringify(id)}, at, { repeats: 1, camera: false, section: "groove", source: "pad" }); s.setShot(${JSON.stringify(shot)}, 0.5);
    return at + (${JSON.stringify(def)}.steps[0].id === "Z" ? 4 : 0); })()`);
}
// the strongest period (beats) of a series over [lo, hi], scanned finely
function peakPeriod(xs, ys, lo, hi, step = 0.002) {
  const m = ys.reduce((a, b) => a + b, 0) / ys.length;
  let best = 0, bestP = lo;
  for (let P = lo; P <= hi + 1e-9; P += step) { let re = 0, im = 0; for (let i = 0; i < xs.length; i++) { re += (ys[i] - m) * Math.cos(2 * Math.PI * xs[i] / P); im += (ys[i] - m) * Math.sin(2 * Math.PI * xs[i] / P); } const a = Math.hypot(re, im); if (a > best) { best = a; bestP = P; } }
  return bestP;
}
// the lag (in samples) that best aligns b to a (b later = positive)
function bestLag(a, b, maxLag, minLag = -maxLag) { const ma = a.reduce((s, v) => s + v, 0) / a.length, mb = b.reduce((s, v) => s + v, 0) / b.length; let best = -Infinity, bl = 0; for (let L = minLag; L <= maxLag; L++) { let c = 0; for (let i = Math.max(0, -L); i < a.length && i + L < b.length; i++) c += (a[i] - ma) * (b[i + L] - mb); if (c > best) { best = c; bl = L; } } return bl; }

// The thirds in the picture, in the show (the limiter's interventions recorded): samples along each third's 16 beams (3, 6
// and 10 m out from the lens: the lens glare itself clips, the beam's light does not), at HALO_LOCK. The footage's rows at
// the ring centre +-R/3 do not transfer: our ring leans back 55 degrees and from this lens every lit beam fans out across
// the picture, so a row across the frame catches all three thirds. daniel: the demo's own step A (repeat 0, 12 beats);
// rush: the phrase forced to a rush repeat in the build (its home), lengthened to 8 beats of rush for the measure.
const BEAM_SAMPLES = (ts) => String.raw`(() => { const s = window.__stage, R = s.renderer; return ["halo.top", "halo.mid", "halo.bot"].map((n) => { const out = [];
  for (const k of s.rig.groups[n].members) { const o = R.headOut[k]; for (const t of ${JSON.stringify(ts)}) { const q = window.__pic.project([o.lens[0] + o.dir[0] * t, o.lens[1] + o.dir[1] * t, o.lens[2] + o.dir[2] * t]);
    if (q[2] && q[0] >= 2 && q[1] >= 2 && q[0] < window.__pic.size()[0] - 2 && q[1] < window.__pic.size()[1] - 2) out.push([q[0], q[1]]); } } return out; }); })()`;
async function levelsInShow({ ev, open, phase, deadline }, variant) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PICTURE_PROBE);
  const rush = variant === "rush";
  let at, until, every;
  if (!rush) {
    at = DROP_BEAT; until = DROP_BEAT + 10.95; every = 2;          // (the cut to the horizontal step comes on A's beat 12)
  } else {
    // the rush repeat at the build's ONE: A1 4 beats at Daniel's speed, then A2 8 beats at the footage's
    await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < ${frameOfBeat(26)}; i++) window.__vt.step(${F}); return true; })()`, 160000);
    at = await ev(`(() => { const s = window.__stage; s.show.padRules = [];
      s.rig.phrases["halo-levels"].vary.variants["rx-rush"] = { steps: { A: { split: [{ beats: 4 }, { beats: 8, swap: { "levels-step": "levels-rush" }, laser_schedule: "levels-rush" }] } } };
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs), at = s.grid.nextBarPos(pos);
      s.programmer.setOverlay(s.runner.prepareLines("halo-levels"), pos, { positionsOnly: true });
      s.runner.start("halo-levels", at, { repeats: 1, camera: true, section: "build", source: "pad", variant: "rx-rush" }); return at + 4; })()`);
    until = at + 6.95; every = 1;                                // (the cut to the horizontal step comes a beat before A2 ends)
  }
  await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${at} + 0.02) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return true; })()`, 160000);
  // (the rush is a lift: near the lens its beams clip, so it is read further out, where a beam has spread into the
  // display's linear range)
  const along = rush ? [20, 30, 40] : [3, 6, 10];
  const heads = await ev(BEAM_SAMPLES(along));                   // projected once the step's own camera is up
  const lim0 = await ev("window.__stage.limiter.stats().interventions");
  const series = [];
  while (Date.now() < deadline - 15000) {
    const chunk = await ev(`(() => { const s = window.__stage, out = [], H3 = ${JSON.stringify(heads)}; for (let i = 0; i < 24; i++) { s.skipRender = ${every > 1 ? "true" : "false"}; for (let k = 1; k < ${every}; k++) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F});
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs); out.push([pos, ...H3.map((pts) => { const L = window.__pic.points(pts); return L.reduce((a, q) => a + q[0], 0) / L.length; }), s.director.pose.shot, s.runner.status().step]); if (pos > ${until}) break; } return out; })()`, 160000);
    series.push(...chunk);
    if (chunk.at(-1)[0] > until) break;
  }
  const lim1 = await ev("window.__stage.limiter.stats().interventions");
  const run = series.filter((r) => r[0] >= at + 0.05 && r[0] < until - 0.02);
  const xs = run.map((r) => r[0] - at);
  const strip = [1, 2, 3].map((k) => run.map((r) => r[k]));
  const want = rush ? 0.75 : 3;
  const P = peakPeriod(xs, strip[0], rush ? 0.4 : 1.5, rush ? 1.5 : 6);
  const stepBeats = rush ? 0.25 : 1, spb = stepBeats / ((every * 150) / 60 / 60);
  const cyc = Math.round(spb * 3) - 1;                    // lags searched over one cycle forward: 0 .. 3 steps
  const lagMid = bestLag(strip[0], strip[1], cyc, 0) / spb, lagBot = bestLag(strip[0], strip[2], cyc, 0) / spb;
  const byStep = [0, 1, 2].map((k) => { const v = run.filter((r, i) => Math.floor(((xs[i] / stepBeats) % 3 + 3) % 3) === k && ((xs[i] / stepBeats) % 1) > 0.2 && ((xs[i] / stepBeats) % 1) < 0.8).map((r) => r[1]); return v.reduce((a, b) => a + b, 0) / Math.max(1, v.length); });
  const darkRaw = Math.min(...byStep) / Math.max(1e-9, Math.max(...byStep));
  // in the show other light sits under every sample (the strand, the slats, the lasers): the dark step is measured above
  // the strip's own floor (its 5th percentile over the step), the raw ratio reported beside it
  const floorTop = [...strip[0]].sort((a, b) => a - b)[Math.floor(0.05 * (strip[0].length - 1))];
  const darkShare = Math.max(0, Math.min(...byStep) - floorTop) / Math.max(1e-9, Math.max(...byStep) - floorTop);
  const res = { variant, in_show: rush ? "the build, the phrase forced to a rush repeat (8 beats of rush)" : "the demo's drop, repeat 0, step A",
                shots: [...new Set(run.map((r) => r[4]))], samples: run.length, measure: `3 x 3 px patches along each third's 16 beams (${along.join(", ")} m from the lens)`, patches: heads.map((h) => h.length),
                top_peak_period_beats: +P.toFixed(3), lag_middle_steps: +lagMid.toFixed(2), lag_bottom_steps: +lagBot.toFixed(2), top_by_step: byStep.map((v) => +v.toFixed(5)),
                dark_over_lit: +darkShare.toFixed(3), dark_over_lit_raw: +darkRaw.toFixed(3), top_floor: +floorTop.toFixed(5), limiter_interventions: lim1 - lim0 };
  phase[`levels_${variant}`] = res;
  writeFileSync(join(outDir, `levels-${variant}-series.json`), JSON.stringify({ at, xs, strip }));
  const tol = rush ? 0.03 : 0.09;
  // rush is a lift (the unlit thirds hold 0.72): its dark step is most of its lit one by design, so its targets are the
  // period and the order
  check(`picture: HALO_LOCK in the show, ${variant} levels along the thirds' beams: the top third's period ${want} +- ${tol} beats, middle +1 step, bottom +2 steps (+-0.25)${rush ? "" : ", dark step <= 15 % of the lit step"}, no limiter intervention`,
        Math.abs(P - want) <= tol && Math.abs(lagMid - 1) <= 0.25 && Math.abs(lagBot - 2) <= 0.25 && (rush || darkShare <= 0.15) && res.limiter_interventions === 0, res);
}
async function phasePicLevels(ctx) { return levelsInShow(ctx, "daniel"); }
async function phasePicRush(ctx) { return levelsInShow(ctx, "rush"); }

// The chopper's blade angle from the luminance at a ring's cells: the 2nd circular harmonic (amplitude over a robust
// baseline, the 20th percentile of the cells), its phase unwrapped and fitted.
function chopperFit(frames, ang) {
  const pct = (arr, q) => { const v = [...arr].sort((a, b) => a - b); return v[Math.floor(q * (v.length - 1))]; };
  // each cell by its own range over the frames: a cell's static gain (the strand or the halo's hardware in front of it,
  // perspective on the tilted ring, its size on the canvas) is not the blade pattern; cells that never change are left out
  const nC = frames[0].L.length, lo = new Float64Array(nC).fill(Infinity), hi = new Float64Array(nC).fill(-Infinity);
  for (const r of frames) for (let k = 0; k < nC; k++) { lo[k] = Math.min(lo[k], r.L[k]); hi[k] = Math.max(hi[k], r.L[k]); }
  const ranges = Array.from(hi, (v, k) => v - lo[k]), medR = pct(ranges, 0.5);
  const use = ranges.map((r) => r > 0.1 * medR && r > 1e-4);
  const h = frames.map((r) => { let re = 0, im = 0, w = 0, re1 = 0, im1 = 0;
    r.L.forEach((v, k) => { if (!use[k]) return; const d = (v - lo[k]) / ranges[k]; re += d * Math.cos(2 * ang[k]); im += d * Math.sin(2 * ang[k]); re1 += d * Math.cos(ang[k]); im1 += d * Math.sin(ang[k]); w += d; });
    return { a2: w ? Math.hypot(re, im) / w : 0, a1: w ? Math.hypot(re1, im1) / w : 0, ph: Math.atan2(im, re) }; });
  const a2 = [h[0].ph / 2];
  for (let i = 1; i < h.length; i++) { let d = h[i].ph / 2 - h[i - 1].ph / 2; while (d > Math.PI / 2) d -= Math.PI; while (d < -Math.PI / 2) d += Math.PI; a2.push(a2.at(-1) + d); }
  const xs = frames.map((r) => r.pos), n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = a2.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0; for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (a2[i] - my); sxx += (xs[i] - mx) ** 2; }
  const turns = sxy / sxx / (2 * Math.PI);
  const within = a2.filter((a, i) => Math.abs(a - (my + (sxy / sxx) * (xs[i] - mx))) <= Math.PI / 6).length / n;
  const contrast = frames.map((r) => { const L = r.L; return pct(L, 0.9) / Math.max(1e-6, pct(L, 0.1)); });
  return { frames: n, cells_used: use.filter(Boolean).length, second_harmonic: +(h.reduce((s, x) => s + x.a2, 0) / n).toFixed(3), first_harmonic: +(h.reduce((s, x) => s + x.a1, 0) / n).toFixed(3),
           turns_per_beat: +turns.toFixed(3), counter_clockwise: turns > 0, within_30deg: +within.toFixed(3), cell_contrast_p90_p10: +(contrast.reduce((a, b) => a + b, 0) / contrast.length).toFixed(2) };
}
// the luminance at the exact pixel of each projected point (no neighbours)
const CELL_READ = (pts) => `(() => { const P = ${JSON.stringify(pts)}; const L = window.__pic.points(P); const C = window.__pic.centres(P); return { L: L.map((q) => q[0]), C, R: L.map((q) => q[1]), B: L.map((q) => q[2]) }; })()`;

async function phasePicRing({ ev, open, phase, deadline, shot }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PICTURE_PROBE);
  // 1. the demo's own step E (repeat 0, HALO_ORBIT): the chopper on ring 0's slats
  const E0 = DROP_BEAT + 28;
  await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${E0} + 0.05) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return true; })()`, 160000);
  const ringPts = async () => ev(`(() => { const s = window.__stage, g = s.rig.groups["rings.r0.slats"], out = []; for (let m = 0; m < g.n; m += 2) { const p = window.__pic.project(g.world[m]); out.push([p[0], p[1], g.keys.angle[m]]); } return out; })()`);
  // HALO_ORBIT moves (a 30 degree arc): the cells are projected again on every frame
  const E = [];
  while (Date.now() < deadline - 100000) {
    const chunk = await ev(`(() => { const s = window.__stage, out = []; for (let i = 0; i < 24; i++) { window.__vt.step(${F}); const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
      const g = s.rig.groups["rings.r0.slats"], g3 = s.rig.groups["rings.r3.slats"], pts = [], p3 = []; for (let m = 0; m < g.n; m += 2) { const p = window.__pic.project(g.world[m]); pts.push([p[0], p[1]]); }
      for (let m = 0; m < g3.n; m += 2) { const p = window.__pic.project(g3.world[m]); p3.push([p[0], p[1]]); }
      out.push({ pos, shot: s.director.pose.shot, step: s.runner.status().step, C: window.__pic.centres(pts), L: window.__pic.points(pts).map((q) => q[0]), L3: window.__pic.points(p3).map((q) => q[0]) }); if (pos > ${E0} + 2.9) break; } return out; })()`, 160000);
    E.push(...chunk);
    if (chunk.at(-1).pos > E0 + 2.9) break;
  }
  const ang = (await ringPts()).map((p) => p[2]);
  const ang3 = await ev(`(() => { const g = window.__stage.rig.groups["rings.r3.slats"], out = []; for (let m = 0; m < g.n; m += 2) out.push(g.keys.angle[m]); return out; })()`);
  const inE = E.filter((r) => r.step === "E");
  const ownCam = { shot: [...new Set(inE.map((r) => r.shot))], patch: chopperFit(inE, ang), centre: chopperFit(inE.map((r) => ({ pos: r.pos, L: r.C })), ang),
                   inner_ring: chopperFit(inE.map((r) => ({ pos: r.pos, L: r.L3 })), ang3) };
  phase.chopper_in_show = ownCam;
  // 2. the isolated front-of-house test: the chopper on every slat (5 beats), then the colour bump (6 beats) at 5 %
  await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${E0 + 6}) window.__vt.step(${F}); s.skipRender = false; return true; })()`, 160000);
  const def = { name: "rx-ring", bars: 3, steps: [
    { id: "C", name: "chopper", beats: 6, trigger: "follow", lines: [...darkLines, { group: "rings.slats", values: { Dimmer: 0.9, Color: "W", Color2: "A" }, effects: ["ring-chopper"] }] },
    { id: "B", name: "bump", beats: 6, trigger: "follow", lines: [...darkLines, { group: "rings.slats", values: { Dimmer: 0.05, Color: "bumpA", Color2: "bumpB" }, effects: ["ring-colour-bump"] }] }] };
  const at = await startTestPhrase(ev, "rx-ring", def, "HALO_LOCK");
  await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${at}) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return true; })()`, 160000);
  const pts = await ringPts();
  const PTS = JSON.stringify(pts.map((p) => [p[0], p[1]]));
  const rec = [];
  while (Date.now() < deadline - 15000) {
    const chunk = await ev(`(() => { const s = window.__stage, out = []; for (let i = 0; i < 24; i++) {
      let pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
      if (pos > ${at + 3.1} && pos < ${at + 6}) { s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${at + 6}) window.__vt.step(${F}); s.skipRender = false; }
      if (pos >= ${at + 6}) { s.skipRender = true; window.__vt.step(${F}); s.skipRender = false; }
      window.__vt.step(${F}); pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
      const L = window.__pic.points(${PTS}); out.push({ pos, L: L.map((q) => q[0]), R: L.map((q) => q[1]), B: L.map((q) => q[2]), C: window.__pic.centres(${PTS}), mean: window.__pic.frame().mean }); if (pos > ${at + 12}) break; } return out; })()`, 160000);
    rec.push(...chunk);
    if (chunk.at(-1).pos > at + 12) break;
  }
  const Cf = rec.filter((r) => r.pos >= at + 0.1 && r.pos < at + 3.0);
  phase.chopper_foh = { patch: chopperFit(Cf, ang), centre: chopperFit(Cf.map((r) => ({ pos: r.pos, L: r.C })), ang) };
  const best = (x) => [x.centre, x.patch, x.inner_ring].filter(Boolean).sort((a, b) => b.second_harmonic - a.second_harmonic)[0];
  const o = best(ownCam), f = best(phase.chopper_foh);
  check("picture: the chopper on the rendered rings at front of house (HALO_LOCK): second harmonic >= 0.6, 1 turn a beat +-5 %, counter-clockwise, 90 %+ of frames within 30 degrees of the fit",
        f.second_harmonic >= 0.6 && Math.abs(f.turns_per_beat - 1) <= 0.05 && f.turns_per_beat > 0 && f.within_30deg >= 0.9, phase.chopper_foh);
  check("picture: the chopper at its own camera in the show (step E, HALO_ORBIT, repeat 0): 1 turn a beat +-5 %, counter-clockwise, 90 %+ of frames on the fit (its harmonic reported: the corona's heads and beams sit over part of the ring from that angle)",
        Math.abs(o.turns_per_beat - 1) <= 0.05 && o.turns_per_beat > 0 && o.within_30deg >= 0.9, { own_camera: ownCam, best: o });
  const B = rec.filter((r) => r.pos >= at + 6.1 && r.pos < at + 11.9);
  const red = B.map((r) => { let a = 0, b = 0; for (let k = 0; k < r.R.length; k++) { a += r.R[k]; b += r.B[k]; } return a / Math.max(1e-9, a + b); });
  const P = peakPeriod(B.map((r) => r.pos), red, 0.5, 3);
  const half = (lo, hi, fn) => { const v = B.filter((r) => { const fr = ((r.pos - at) % 1 + 1) % 1; return fr >= lo && fr < hi; }).map(fn); return v.reduce((a, b) => a + b, 0) / Math.max(1, v.length); };
  const cells = (r) => r.L.reduce((a, b) => a + b, 0) / r.L.length;
  const rb = half(0.1, 0.4, cells), rp = half(0.6, 0.9, cells), fb = half(0.1, 0.4, (r) => r.mean), fp = half(0.6, 0.9, (r) => r.mean);
  const bump = { frames: B.length, period_beats: +P.toFixed(3), dimmer: 0.05, ring_cells_blue: +rb.toFixed(5), ring_cells_pink: +rp.toFixed(5), ring_cells_change: +(Math.abs(rp - rb) / ((rp + rb) / 2)).toFixed(4),
                 frame_blue: +fb.toFixed(5), frame_pink: +fp.toFixed(5), frame_change: +(Math.abs(fp - fb) / ((fp + fb) / 2)).toFixed(4) };
  phase.bump = bump;
  writeFileSync(join(outDir, "ring-series.json"), JSON.stringify({ at, ang, inE: inE.slice(0, 4), foh: Cf.slice(0, 4), bump: B.slice(0, 24).map((r) => [r.pos, cells(r), r.mean]) }));
  check("picture: the colour bump on the rendered rings: its period 1.00 +- 0.05 beat; blue or pink, the rings' brightness and the frame's change 3 % or less (a hue bump, not a flash)",
        Math.abs(P - 1) <= 0.05 && bump.ring_cells_change <= 0.03 && bump.frame_change <= 0.03, bump);
}

// A diagnostic burst (not in the default run): the ring test at HALO_LOCK, a screenshot, the projected points of ring 0's
// slats and of each third's heads, and the luminance read at them, to check the picture probes against the picture.
async function phasePicDebug({ ev, open, shot, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PICTURE_PROBE);
  // 1. step D (repeat 0) at beat 5: which heads are lit, and what the renderer drew
  const D5 = DROP_BEAT + 25;
  const r = await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${D5}) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F});
    const P = s.programmer, lit = {};
    for (const [n, g] of Object.entries(s.rig.groups)) { if (g.kind !== "heads") continue; let mx = 0; for (const k of g.members) mx = Math.max(mx, P.heads[k * 16 + 2]); if (mx > 0.01) lit[n] = +mx.toFixed(3); }
    const tl = []; for (let i = 0; i < P.nH; i++) if (P.tH[i * 7 + 2] > 0.01) tl.push(i);
    return { pos: s.grid.posAt(performance.now() + s.grid.presentLagMs), step: s.runner.status(), shot: s.director.pose.shot, lit, targetsLit: tl.length, info: s.renderer.info,
             ov: { active: P.ov.active, preroll: P.ov.preroll, lines: P.ov.lines.length } }; })()`);
  phase.debug_d = r;
  if (sheetDir) await shot(join(sheetDir, "debug-D5.png"));
  // 2. the bump at 5 %: the rendered ring cells' luminance, blue against pink at four pink gains (the theme's bumpB scaled
  // in linear light)
  await ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${DROP_BEAT + 36}) window.__vt.step(${F}); s.skipRender = false; return true; })()`, 160000);
  const def = { name: "rx-bump", bars: 6, steps: [{ id: "B", name: "bump", beats: 24, trigger: "follow", lines: [...darkLines, { group: "rings.slats", values: { Dimmer: 0.05, Color: "bumpA", Color2: "bumpB" }, effects: ["ring-colour-bump"] }] }] };
  const at = await startTestPhrase(ev, "rx-bump", def, "HALO_LOCK");
  const gains = [1.0, 1.12, 1.24, 1.36];
  const out = [];
  for (const [k, gain] of gains.entries()) {
    const res = await ev(`(() => { const s = window.__stage, P = s.programmer;
      const lin = (h) => { const v = parseInt(h.slice(1), 16), f = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return [f((v >> 16) & 255), f((v >> 8) & 255), f(v & 255)]; };
      const pink = lin(s.rig.themes["source-violet"].bumpB).map((c) => c * ${gain}); P.roleRGB[7] = pink;
      while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${at} + ${4 * k} + 1) { s.skipRender = true; window.__vt.step(${F}); }
      s.skipRender = false;
      const g = s.rig.groups["rings.r0.slats"], pts = []; for (let m = 0; m < g.n; m += 2) { const q = window.__pic.project(g.world[m]); pts.push([q[0], q[1]]); }
      const acc = { blue: [], pink: [] };
      for (let i = 0; i < 48; i++) { window.__vt.step(${F}); const f = ((s.grid.posAt(performance.now() + s.grid.presentLagMs) - ${at}) % 1 + 1) % 1; const L = window.__pic.points(pts); const m = L.reduce((a, q) => a + q[0], 0) / L.length;
        if (f > 0.1 && f < 0.4) acc.blue.push(m); else if (f > 0.6 && f < 0.9) acc.pink.push(m); }
      const mean = (v) => v.reduce((a, b) => a + b, 0) / Math.max(1, v.length);
      return { gain: ${gain}, blue: mean(acc.blue), pink: mean(acc.pink) }; })()`, 160000);
    out.push(res);
  }
  phase.bump_gains = out;
  check("pic-debug: ran", true, { d5: r, bump: out.map((o) => ({ gain: o.gain, blue: +o.blue.toFixed(4), pink: +o.pink.toFixed(4), ratio: +(o.pink / o.blue).toFixed(3) })) });
}

// The hand-off and never-static, in the demo as programmed (its own cameras): D's frames (lit share, true black) and the
// same phrase position in two repeats.
async function phasePicHandoff({ ev, open, phase, deadline, shot }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PICTURE_PROBE);
  const goTo = async (beat) => ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${beat}) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return s.grid.posAt(performance.now() + s.grid.presentLagMs); })()`, 160000);
  const positions = [["A", 1.5], ["B", 2.5], ["C", 1.5], ["E", 1.5]];
  const stepAt = { A: 0, B: 12, C: 16, D: 20, E: 28 };
  // repeat 0: the same-position frames, then D sampled every 4th frame; repeat 1: the same positions again
  const D = [];
  const rep0 = DROP_BEAT, rep1 = DROP_BEAT + 32;
  const keepAt = async (beat, name) => ev(`(() => { const s = window.__stage; s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${beat}) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return window.__pic.keep(${JSON.stringify(name)}); })()`, 160000);
  for (const [st, b] of positions.slice(0, 3)) await keepAt(rep0 + stepAt[st] + b, `r0-${st}`);
  await goTo(rep0 + stepAt.D + 0.05);
  let shotTaken = false;
  while (Date.now() < deadline - 60000) {
    const chunk = await ev(`(() => { const s = window.__stage, out = []; for (let i = 0; i < 12; i++) { s.skipRender = true; for (let k = 0; k < 3; k++) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F});
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs); out.push({ pos, shot: s.director.pose.shot, ...window.__pic.frame() }); if (pos > ${rep0 + stepAt.E - 0.1}) break; } return out; })()`, 160000);
    D.push(...chunk.filter((r) => r.pos < rep0 + stepAt.E));
    if (!shotTaken && sheetDir && chunk.at(-1).pos >= rep0 + stepAt.D + 5) { await shot(join(sheetDir, "handoff-D-beat5.png")); shotTaken = true; }
    if (chunk.at(-1).pos > rep0 + stepAt.E - 0.1) break;
  }
  await keepAt(rep0 + stepAt.E + 1.5, "r0-E");
  for (const [st, b] of positions) await keepAt(rep1 + stepAt[st] + b, `r1-${st}`);
  const lit = D.reduce((a, r) => a + r.lit, 0) / D.length, black = D.reduce((a, r) => a + r.black, 0) / D.length;
  phase.handoff = { frames: D.length, shots: [...new Set(D.map((r) => r.shot))], lit_share: +lit.toFixed(4), true_black_share: +black.toFixed(4),
                    median_max_channel: D.map((r) => r.median_max_channel).sort((a, b) => a - b)[Math.floor(D.length / 2)],
                    definition: "lit: relative luminance >= 0.05; true black: every channel <= 8 of 255" };
  check("picture: the hand-off to the lasers (step D, the demo's own cameras): 15 % or less of the frame lit, 30 % or more true black", D.length >= 20 && lit <= 0.15 && black >= 0.30, phase.handoff);
  const diffs = {};
  for (const [st] of positions) diffs[st] = await ev(`window.__pic.diff("r0-${st}", "r1-${st}")`);
  phase.never_static = Object.fromEntries(Object.entries(diffs).map(([k, v]) => [k, { relative: +v.relative.toFixed(3), mean_abs: +v.mean_abs.toFixed(5) }]));
  check("picture: never static: the same phrase position in two repeats differs by a mean of 4 % or more (A, B, C, E)", Object.values(diffs).every((d) => d.relative >= 0.04), phase.never_static);
}

// The three-minute run: the programmed demo (with its phrase in the drop) from one second after load, every frame read
// back with the crowd on, in chunks: each chunk is its own burst (the lock, a fresh Chrome, under three minutes), fast-
// forwards the show's logic to its start, renders a warm-up of 64 frames the limiter judges (so its 1.01 s windows are
// full), then the chunk. The verifier's own counter judges the stitched series of all chunks.
const RUN_START = 60;
async function flashChunk({ ev, open, phase, deadline }, k, framesPer, warm, runFrames, fw, fh) {
  await open(`demo=1&vt=1&w=${fw}&h=${fh}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`);
  await ev(PAGE_PROBE);
  const f0 = RUN_START + k * framesPer, f1 = Math.min(RUN_START + runFrames, f0 + framesPer);
  const ff = Math.max(0, f0 - warm);
  const t0 = Date.now();
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < ${ff}; i++) window.__vt.step(${F}); s.skipRender = false; return true; })()`, 170000);
  phase.fast_forward_s = +((Date.now() - t0) / 1000).toFixed(1);
  const RUN = String.raw`((n) => { const s = window.__stage, out = []; for (let i = 0; i < n; i++) { window.__vt.step(1000 / 60); const c = window.__probe.cells(); const g = s.renderer.info.gains; const st = s.runner ? s.runner.status() : null;
    out.push({ L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0, shot: s.director.pose.shot, section: s.state().section, step: st && st.state === "running" ? st.step + ":" + st.variant : "" }); } return out; })`;
  const series = [];
  let frame = ff;
  const t1 = Date.now();
  while (frame < f1 && Date.now() < deadline - 12000) {
    const n = Math.min(30, f1 - frame);
    const chunk = await ev(`${RUN}(${n})`, 160000);
    chunk.forEach((c, i) => { c.frame = frame + i + 1; });
    series.push(...chunk);
    frame += n;
  }
  phase.ms_per_frame = +((Date.now() - t1) / Math.max(1, series.length)).toFixed(0);
  const lim = await ev("window.__stage.limiter.stats()");
  const body = series.filter((c) => c.frame > f0);
  const out = { k, f0, f1, warm, rendered: series.length, frames: body.length, complete: frame >= f1, interventions_in_chunk: body.filter((c) => c.lim).length,
                interventions_in_warmup: series.filter((c) => c.frame <= f0 && c.lim).length, limiter_rest_frames: lim.rest_frames, size: [fw, fh],
                ms_per_frame: phase.ms_per_frame, series };
  writeFileSync(join(outDir, `flash3m-chunk-${String(k).padStart(3, "0")}.json`), JSON.stringify(out));
  phase.chunk = { k, f0, f1, frames: body.length, complete: out.complete, interventions: out.interventions_in_chunk, ms_per_frame: phase.ms_per_frame,
                  shots: [...new Set(body.map((c) => c.shot))], sections: [...new Set(body.map((c) => c.section))] };
  console.log(`flash3m chunk ${k}: frames ${f0}-${f1}, ${body.length} judged, interventions ${out.interventions_in_chunk}, ${phase.ms_per_frame} ms/frame, shots ${phase.chunk.shots.join(",")}`);
}
async function runFlash3m() {
  const seconds = Number(opt["flash3m-seconds"]) || 180, per = Number(opt["chunk-seconds"]) || 10;
  const runFrames = Math.round(seconds * 60), framesPer = Math.round(per * 60), warm = 64;
  const scale = Number(opt["flash-scale"]) || 1;
  const fw = Math.round(W * scale), fh = Math.round(H * scale);
  const nChunks = Math.ceil(runFrames / framesPer);
  const from = Number(opt["chunk-from"]) || 0, to = Math.min(nChunks, Number(opt["chunk-to"]) || nChunks);
  const dir = opt["flash3m-dir"] || outDir;
  mkdirSync(dir, { recursive: true });
  for (let k = from; k < to; k++) {
    const file = join(dir, `flash3m-chunk-${String(k).padStart(3, "0")}.json`);
    if (existsSync(file)) { try { if (JSON.parse(readFileSync(file, "utf8")).complete) { console.log(`flash3m chunk ${k}: already done`); continue; } } catch { /* redo */ } }
    await burst(`flash3m-${k}`, (ctx) => flashChunk(ctx, k, framesPer, warm, runFrames, fw, fh));
    if (dir !== outDir && existsSync(join(outDir, `flash3m-chunk-${String(k).padStart(3, "0")}.json`))) writeFileSync(file, readFileSync(join(outDir, `flash3m-chunk-${String(k).padStart(3, "0")}.json`)));
  }
  // stitch every chunk present and judge the whole run
  const chunks = [];
  for (let k = 0; k < nChunks; k++) {
    const file = join(dir, `flash3m-chunk-${String(k).padStart(3, "0")}.json`);
    if (existsSync(file)) chunks.push(JSON.parse(readFileSync(file, "utf8")));
  }
  const series = chunks.flatMap((c) => c.series.filter((s) => s.frame > c.f0 && s.frame <= c.f1));
  const covered = chunks.filter((c) => c.complete).length === nChunks;
  const j = judgeFlashes(series);
  const allShots = Object.keys(RIG.cameras.shots);
  const seen = [...new Set(series.map((s) => s.shot))];
  const steps = [...new Set(series.map((s) => s.step).filter(Boolean))];
  const interventions = chunks.reduce((a, c) => a + c.interventions_in_chunk, 0);
  const summary = { seconds: +(series.length / 60).toFixed(1), frames: series.length, chunks: chunks.length, all_chunks_complete: covered, size: [fw, fh],
                    interventions, interventions_in_warmups: chunks.reduce((a, c) => a + c.interventions_in_warmup, 0), rest_frames: Math.max(0, ...chunks.map((c) => c.limiter_rest_frames)),
                    worst_flashes_per_s: j.worst, worst_window: j.worst_window, worst_red: j.worst_red,
                    max_transitions_per_window_1s: Object.fromEntries(Object.entries(j.windows).map(([k, v]) => [k, v.flashes_per_s * 2])),
                    shots_seen: seen, shots_missing: allShots.filter((s) => !seen.includes(s)), phrase_steps_seen: steps,
                    sections: [...new Set(series.map((s) => s.section))], ms_per_frame: chunks.map((c) => c.ms_per_frame) };
  report.phases.flash3m = summary;
  check(`flash3m: ${summary.seconds} s of the programmed demo, crowd on, every camera shot, every frame read back (${fw}x${fh}): zero final-limiter interventions, <= 3 flashes a second in all 18 windows, no red flash, no rest`,
        covered && series.length >= runFrames - 1 && interventions === 0 && j.worst <= 3 && j.worst_red === 0 && summary.rest_frames === 0 && summary.shots_missing.length === 0,
        { frames: series.length, interventions, worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red, shots_missing: summary.shots_missing, chunks_complete: covered });
}

// The phrase's contact sheet: each step at its telling moment, from the phrase's own camera (front of house) and from the
// tribune. Scratch only (the sheets sit beside Daniel's frames, which are other people's footage).
async function phaseSheetPhrase({ ev, open, shot, phase }) {
  if (!sheetDir) { phase.skipped = "no --sheet-dir"; return; }
  await open(`demo=1&vt=1&${BASE}`);
  const plan = [
    ["A1-top", "A", 0.5], ["A2-middle", "A", 1.5], ["A3-bottom", "A", 2.5], ["B1-flash", "B", 0.06], ["B2-pan", "B", 2.0],
    ["C1-v1", "C", 0.5], ["C2-v2", "C", 1.5], ["C3-v3", "C", 2.5], ["D1-bloom", "D", 0.6], ["D2-lasers", "D", 5.0], ["E1-halo", "E", 1.4], ["E2-halo", "E", 2.6],
  ];
  const stepAt = { A: 0, B: 12, C: 16, D: 20, E: 28 };
  phase.shots = [];
  for (const rep of [0, 1]) {
    for (const [label, st, b] of plan) {
      const beat = DROP_BEAT + 32 * rep + stepAt[st] + b;
      await ev(`(() => { const s = window.__stage; s.clearShot(); s.skipRender = true; while (s.grid.posAt(performance.now() + s.grid.presentLagMs) < ${beat}) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return true; })()`, 170000);
      const info = await ev("(() => { const s = window.__stage; const st = s.runner.status(); return { shot: s.director.pose.shot, step: st.step, variant: st.variant }; })()");
      const f1 = await shot(join(sheetDir, `r${rep}-${label}-foh.png`));
      await ev(`(() => { const s = window.__stage; s.setShot("TRIBUNE_34", 0.6); window.__vt.step(${F}); return true; })()`);
      const f2 = await shot(join(sheetDir, `r${rep}-${label}-tribune.png`));
      phase.shots.push({ rep, label, ...info, files: [f1, f2] });
    }
  }
  check("sheet-phrase: every step of two repeats from the phrase's camera and the tribune", phase.shots.length === plan.length * 2, phase.shots.map((s) => `${s.rep}:${s.label}:${s.step}:${s.variant}:${s.shot}`));
  // the HUD names the running step (Daniel's view of where the phrase is)
  const hud = await ev(`(() => { const s = window.__stage; s.clearShot(); document.getElementById("hud").classList.remove("hidden");
    for (let i = 0; i < 8; i++) window.__vt.step(${F}); const st = s.runner.status(); return { text: document.getElementById("hud-phrase").textContent, step: st.step, stepName: st.stepName, variant: st.variant }; })()`);
  phase.hud = hud;
  check("sheet-phrase: the HUD's phrase row names the running step, its variant and its repeat", hud.step && hud.text.includes(`${hud.step} ${hud.stepName}`) && hud.text.includes(hud.variant), hud);
}

// ------------------------------------------------------------------------------------------------------ main --
try {
  PORT = await listen(web, PORT);
  ENGINE_PORT = await listen(engine, ENGINE_PORT);
  report.ports = { web: PORT, engine: ENGINE_PORT };
  const table = { load: phaseLoad, clock: phaseClock, engine: phaseEngine, cost: phaseCost, flash: phaseFlash, storm: phaseStorm, sheet: phaseSheet, probe: phaseProbe, diag: phaseDiag,
                  phrase: phasePhrase, "pic-debug": phasePicDebug, "pic-levels": phasePicLevels, "pic-rush": phasePicRush, "pic-ring": phasePicRing, "pic-handoff": phasePicHandoff, "sheet-phrase": phaseSheetPhrase };
  for (const p of PHASES) {
    if (p === "flash3m") { await runFlash3m(); continue; }
    if (!table[p]) { console.log(`unknown phase ${p}`); continue; }
    await burst(p, table[p]);
  }
} finally {
  web.close(); engine.close();
  for (const c of sse) c.end();
}
report.finished_at = new Date().toISOString();
const failed = Object.entries(report.checks).filter(([, v]) => !v.ok).map(([k]) => k);
report.verdict = failed.length ? "fail" : "pass";
report.failed = failed;
writeFileSync(join(outDir, "receipt.json"), JSON.stringify(report, null, 2));
console.log(`receipt: ${join(outDir, "receipt.json")}`);
console.log(`verdict: ${report.verdict}${failed.length ? ` (${failed.join("; ")})` : ""}`);
process.exit(failed.length ? 1 : 0);
