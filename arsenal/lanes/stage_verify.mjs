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
    phases: { type: "string", default: "load,clock,engine,cost,flash,storm,sheet" },
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
      const st = { t, pos, section: s.state().section, shot: s.director.pose.shot, cut: s.director.pose.cut, u: s.director.pose.u,
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
  // the demo: intro 8 bars, build 8, drop 16 (150 BPM: 96 frames a bar). Run to bar 22: the build, its landing, the drop.
  const total = 96 * 22 + 120;
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
  for (let i = 1; i < drop.length - 1; i++) if (drop[i].headDim > drop[i - 1].headDim + 0.02 && drop[i].headDim >= drop[i + 1].headDim) peaks.push(drop[i].pos);
  const off = peaks.map((p) => { const d = p - Math.round(p); return Math.abs(d) * 24; });     // in frames
  phase.off_peaks = peaks.map((p, k) => ({ pos: +p.toFixed(3), frames_off: +off[k].toFixed(2) })).filter((x) => x.frames_off > 1).slice(0, 6);
  phase.drop_dimmer = drop.slice(0, 120).map((s) => [+s.pos.toFixed(3), +s.headDim.toFixed(4)]);
  check("clock: the strand heads' pulse peaks on beat frames (+-1 frame)", peaks.length >= 8 && off.every((x) => x <= 1.01), { peaks: peaks.length, worst_frames: +Math.max(0, ...off).toFixed(2) });
  // KICK lifts (the demo presses pad 1 on every drop downbeat): onset on its beat
  const kicks = st.kicks;
  check("clock: the KICK lift lands on its beat (onset = the beat the press fell on)", kicks.length >= 4 && kicks.every((k) => k.onset === Math.round(k.pressPos) && Math.abs(k.pressPos - k.onset) <= 1 / 24 + 1e-9), kicks.slice(0, 6));
  // 4. sections and cuts on bar lines; no cut faster than 2 beats
  const cuts = [];
  for (let i = 1; i < series.length; i++) if (series[i].cut) cuts.push(series[i].pos);
  const cutOff = cuts.map((p) => { const q = ((p - g.barAnchor) % 4 + 4) % 4; return Math.min(q, 4 - q) * 24; });
  const cutGaps = cuts.slice(1).map((c, k) => c - cuts[k]);
  check("clock: camera cuts fall on bar lines (+-1 frame) and never closer than 2 beats", cuts.length >= 3 && cutOff.every((x) => x <= 1.01) && cutGaps.every((x) => x >= 2 - 0.05), { cuts: cuts.length, worst_frames: +Math.max(0, ...cutOff).toFixed(2), min_gap_beats: cutGaps.length ? +Math.min(...cutGaps).toFixed(3) : null });
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

// ------------------------------------------------------------------------------------------------------ main --
try {
  PORT = await listen(web, PORT);
  ENGINE_PORT = await listen(engine, ENGINE_PORT);
  report.ports = { web: PORT, engine: ENGINE_PORT };
  const table = { load: phaseLoad, clock: phaseClock, engine: phaseEngine, cost: phaseCost, flash: phaseFlash, storm: phaseStorm, sheet: phaseSheet, probe: phaseProbe, diag: phaseDiag };
  for (const p of PHASES) {
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
