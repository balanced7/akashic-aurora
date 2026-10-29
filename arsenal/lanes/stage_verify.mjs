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
//   camera  (v2) a formation landed through the page's door: one glide, the cut ON the landing bar line to its hero view
//           with the strand already there, the lens 1.5 m from the live strand and rings on every frame; the
//           strand-frame corkscrew played by hand round the low strand.
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
// KICK v2 phases (2026-10-27, arsenal/web/stage/kick.js):
//   kick         the real page's logic: the page-level pad door (arsenal:pad, arsenal:padlevel, window.__padDoor), the two
//                kick buttons held at once on two different rows, the live level, the strobe only in the level's top band,
//                key 5 and Shift; contact frames of the kicks on FOH_WIDE to the receipt folder (for the eye).
//   kickstorm    the pre-registered flash case K1 (research/in-flight/kick-v2-report-2026-10-27.md): held top-level kicks,
//                both buttons together, a level wobbling across the strobe band, a 10-a-second tap storm, all through the
//                pad door over the demo's build into its drop, every frame read back (--kick-scale, --kick-seconds).
//   kickpix      round 2's acceptance: the share of an 832 x 384 frame a kick changes by dE76 > --pix-de (10), the same
//                frames drawn with and without it, every look on its main shots (--pix-looks), plus the latency (the first
//                frames after the press) and presses_unlit; the frames are fetched from the page in slices.
//   kickrepeat   round 2's repeat hits at --repeat-rate taps a second (4, 6, 8): each tap's own change of the screen, and
//                how often the limiter has to act, every frame drawn.
//   --flash-from-bar N   where the flash phase starts (default 14; 30 covers the demo's KICK on every drop downbeat).
//   --flash-debug        the flash phase keeps every frame's cells and the kick's state (headroom, live areas) in the receipt.
//   --flash-shots a,b    the flash phase saves a screenshot after each of these frames (diagnosis).
//   --kick-from-frame A --kick-to-frame B   kickstorm in chunks (SwiftShader draws about 4 frames a second here, so 720
//                frames do not fit one burst): frames before A are replayed as logic only, with their input (the virtual
//                clock makes the replay exact), and A..B are drawn and stored in the receipt.
//   --stitch dirA,dirB,...   no browser: judge kickstorm's chunks, each on its own with the same verifier code (chunks
//                overlapping by a second or more, so every one-second window lies inside one chunk), and report case K1's
//                and K3's checks and predictions from them.
// PALETTES phases (2026-10-28, arsenal/web/palettes.js):
//   palettes     the contact sheet: each palette (--pal-ids a,b; all thirty by default) landed through the page's door, the
//                --pal-look (drop) from --pal-shot (FOH_WIDE), settled, drawn; --pal-kick adds the same view with a colour
//                kick on the rings and on the strand. PNGs to --sheet-dir (else the receipt folder).
//   phonebar     the headless phone check (915 x 412, touch): the PALETTE pad's label, the colour strip's wash of the lift
//                colours, a touch that queues the next palette, the page's palette event only on a change, the frame time
//                with the bar against without it, a finger on the colour strip, and the landing on the 16-bar line.
// CAMERA DISTANCE phase (2026-10-29, arsenal/web/stage/distance.js; not in the default list: run it attended, --gpu):
//   distance     the same shot (HALO_LOCK, FOH_WIDE) at CLOSE, MEDIUM and FAR: the rings' on-screen box through the renderer's
//                own camera (close >= 3x far, medium between), a dolly not a zoom, the picture's luminance and true-black
//                share, stills distance-<shot>-<stop>.png; the keys Q / Q again / Shift+E / Esc and the F8 fader on the
//                60 fps virtual clock; the phone segment at 667 x 375 to 915 x 412; the high shots at FAR; a held stop
//                through two moving shots; the cut spacing after a C-key shot.
// THE CHORD PHRASING phase (2026-10-29, arsenal/web/stage/grammar.js + ensemble.js):
//   chords       real keystrokes (CDP Input.dispatchKeyEvent: trusted, so the page's "key" source with its number row),
//                every frame drawn and read back on FOH_WIDE in the demo's break, flash protection on: a chord (1 then 5
//                33 ms later) and a fast strum (6 5 4, 33 ms apart) played twice -- ?grammar=0 (today's singles) and the
//                grammar -- comparing the attack identities (distinct kick punches), the limiter's interventions and the
//                verifier's flash count; then (grammar only) Daniel's slow sweep (6 5 4 3 2 1 then back 2 3 4 5 6, 183 ms
//                apart: the fade out and in) and the explicit B (held, 9 down to 1 and back), with the level's path
//                per frame and stills to the receipt folder for the eye.
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
import { QUIET_FLAGS, judgeFor, renderFlags, rendererName } from "../shaders/headless.mjs";
import { expandScene } from "../web/stage/rig.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]+$/, "");
const MAIN = REPO.split(/[\\/]\.claude[\\/]worktrees[\\/]/)[0];
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    phases: { type: "string", default: "load,clock,camera,phrase,engine,flash,storm,kick,kickstorm,pic-levels,pic-rush,pic-ring,pic-handoff,orrery,spiral" },
    "flash-from-bar": { type: "string", default: "14" },
    "kick-scale": { type: "string", default: "0.5" },
    "kick-seconds": { type: "string", default: "16" },
    "pix-looks": { type: "string", default: "intro,build,drop,break,groove" },
    "pix-de": { type: "string", default: "10" },
    "pix-max-cases": { type: "string", default: "0" },
    "repeat-rate": { type: "string", default: "6" },
    "repeat-kind": { type: "string", default: "colour" },
    "pix-debug": { type: "boolean", default: false },
    "flash-debug": { type: "boolean", default: false },
    "flash-shots": { type: "string", default: "" },
    "kick-from-frame": { type: "string", default: "0" },
    "kick-to-frame": { type: "string", default: "0" },
    stitch: { type: "string", default: "" },
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
    // render on the real GPU instead of SwiftShader: attended runs only (see headless.mjs GPU_FLAGS)
    gpu: { type: "boolean", default: false },
    "flash-seconds": { type: "string", default: "8" },
    "flash-scale": { type: "string", default: "1" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    query: { type: "string", default: "" },
    set: { type: "string", default: "source-v1" },
    "pal-ids": { type: "string", default: "" },
    "pal-look": { type: "string", default: "drop" },
    "pal-shot": { type: "string", default: "FOH_WIDE" },
    "pal-kick": { type: "boolean", default: false },
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
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `stage_verify ${name} (${rendererName(opt.gpu)})`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, pollMs: 2000 });
    phase.lock = { dir: opt["lock-dir"], acquired_at: gpu.owner.acquiredAt };
    const tLock = Date.now();          // the burst (under three minutes) starts when the lock is ours, not while waiting
    chrome = spawn(opt.chrome, [...renderFlags(opt.gpu), ...QUIET_FLAGS, "--remote-debugging-port=0", `--user-data-dir=${profile}`,
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
  const judged = judgeFor(opt.gpu)(renderer);
  phase.renderer = renderer;
  check(opt.gpu ? "load: the renderer is the GPU (--gpu)" : "load: the renderer is SwiftShader (no hardware)", judged.ok, renderer);
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

// v2 (2026-10-27): the camera knows the strand. The receipt holds the show's sections still, plays the groove, and lands
// a low formation through the page's own door (what a MORPH does): one glide from the next bar line while the hoists
// move, the cut ON the landing bar line to the formation's hero view with the strand already there, and on no frame the
// lens within 1.5 m of the live strand or rings (the guard idle). Then the strand-frame corkscrew, played by hand (C),
// round the landed low strand: over the top as a pendulum, clear on every frame. Logic only, every 60 fps frame.
async function phaseCamera({ ev, open, phase, deadline }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev("window.__stage.skipRender = true");
  await ev(`(() => { for (let i = 0; i < 120; i++) window.__vt.step(${F}); return true; })()`);
  const LOW_Y = 11;
  const setup = await ev(`(async () => { const s = window.__stage;
    s.show.update = () => [];
    s.rig.formations["receipt-low"] = { name: "low", params: { y: ${LOW_Y} } };
    s.director.views["receipt-low"] = { glide: ["PROFILE_GRAPH"], hero: ["REAR_TELE_ZIGGURAT"], hero_bars: 4 };
    const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
    s.director.start("groove", s.grid.nextBarPos(pos) - 8);
    for (let i = 0; i < 30; i++) window.__vt.step(${F});
    const r = s.land("receipt-low");
    const C = await import("/web/stage/camera.js");
    window.__cam = { C, model: C.cameraModel(s.rig) };
    return { pos: s.grid.posAt(performance.now() + s.grid.presentLagMs), posLand: r.posLand, barAnchor: s.grid.barAnchor }; })()`);
  phase.setup = setup;
  const RUN = String.raw`((frames) => { const s = window.__stage, out = [], C = window.__cam.C, m = window.__cam.model;
    for (let i = 0; i < frames; i++) {
      window.__vt.step(1000 / 60);
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs), p = s.director.pose;
      out.push({ pos, shot: p.shot, cut: p.cut, why: p.cut ? s.director.cuts.at(-1).why : null, manual: !!s.director.manual,
                 clear: Math.min(C.clearanceToStrand(p.pos, s.strand.poses, m.z), C.clearanceToRings(p.pos, m.rings)),
                 y: p.pos[1], ys: s.strand.poses.map((q) => q.y) });
    }
    return out; })`;
  const series = [];
  const until = setup.posLand + 4 * 4 + 2;
  while (Date.now() < deadline - 30000) {
    const chunk = await ev(`${RUN}(240)`, 160000);
    series.push(...chunk);
    if (chunk.at(-1).pos > until) break;
  }
  const landing = await ev("window.__stage.director.landings.at(-1) || null");
  const guards = await ev("window.__stage.director.clear.guards");
  // the corkscrew by hand, eight bars round the landed strand
  await ev(`(() => { window.__stage.playShot("HELIX_CORKSCREW"); return true; })()`);
  const hand = [];
  for (let k = 0; k < 4 && Date.now() < deadline - 20000; k++) hand.push(...await ev(`${RUN}(192)`, 160000));
  phase.frames = series.length + hand.length;
  const inLanding = series.filter((r) => r.pos >= setup.pos && r.pos < setup.posLand + 16);
  const cuts = inLanding.filter((r) => r.cut).map((r) => ({ pos: +r.pos.toFixed(4), shot: r.shot, why: r.why }));
  const glide = cuts.find((c) => c.why === "landing-glide"), hero = cuts.find((c) => c.why === "landing-hero");
  const offBar = (p) => { const q = ((p - setup.barAnchor) % 4 + 4) % 4; return Math.min(q, 4 - q) * 24; };
  phase.landing = { landing, cuts, guards };
  check("camera: a formation landing gets ONE glide from a bar line while the hoists move, then the cut ON the landing bar line to its hero view (+-1 frame)",
        landing && landing.formation === "receipt-low" && glide && hero && offBar(glide.pos) <= 1.01 && hero.shot === "REAR_TELE_ZIGGURAT"
        && Math.abs(hero.pos - setup.posLand) * 24 <= 1.01 && cuts.filter((c) => c.pos > glide.pos && c.pos < hero.pos).length === 0,
        { posLand: setup.posLand, glide, hero, cuts_between: cuts.filter((c) => glide && hero && c.pos > glide.pos && c.pos < hero.pos).length });
  const heroFrame = hero && series.find((r) => r.pos >= hero.pos - 1e-6);
  const err = heroFrame ? Math.max(...heroFrame.ys.map((y) => Math.abs(y - LOW_Y))) : null;
  check("camera: the cut reveals the arrival -- every rung is at its new height on the hero view's first frame (within 5 cm)",
        err !== null && err <= 0.05, { worst_m: err && +err.toFixed(4), strand_moved_m: series.length ? +(Math.max(...series[0].ys) - LOW_Y).toFixed(2) : null });
  const worst = Math.min(...series.map((r) => r.clear));
  check("camera: on no frame was the lens within 1.5 m of the live strand or the rings, and the guard never had to act",
        series.length > 500 && worst >= 1.5 && guards === 0, { frames: series.length, closest_m: +worst.toFixed(3), guards, shots: [...new Set(series.map((r) => r.shot))] });
  const handWorst = hand.length ? Math.min(...hand.map((r) => r.clear)) : null;
  const span = hand.length ? Math.max(...hand.map((r) => r.y)) - Math.min(...hand.map((r) => r.y)) : 0;
  check("camera: the strand-frame corkscrew by hand (C) round the low strand swings over it as a pendulum and keeps 1.5 m on every frame",
        hand.length >= 700 && hand.every((r) => r.shot === "HELIX_CORKSCREW" && r.manual) && handWorst >= 1.5 && span > 3 && Math.min(...hand.map((r) => r.y)) > LOW_Y - 8 * Math.cos(70 * Math.PI / 180) - 0.3,
        { frames: hand.length, closest_m: handWorst && +handWorst.toFixed(3), height_span_m: +span.toFixed(2), lowest_m: hand.length ? +Math.min(...hand.map((r) => r.y)).toFixed(2) : null });
  const errs = phase.exceptions.length + (await ev("window.__stage.errors.length"));
  check("camera: no exceptions", errs === 0, { exceptions: phase.exceptions.slice(0, 3), page: await ev("window.__stage.errors.slice(0, 3)") });
}

// v2 (2026-10-27, kinetics wave A + the orrery): the ring formations on the page. Each phase holds the show's sections (the
// formation is judged alone, in the Dreaming City theme it was drawn for), measures the rings' motion on the 60 fps
// virtual clock, shoots a frame from each hero view for the contact sheet, and reads every frame through the near view
// (the holographic shimmer awake) and the HERO's discharge on its ONE, judged by the verifier's own flash counter.
const RING_RUN = String.raw`((frames, pressAt) => { const s = window.__stage, out = [];
  for (let i = 0; i < frames; i++) {
    if (i === pressAt) s.press(9, 1);
    window.__vt.step(1000 / 60);
    const c = window.__probe.cells(), g = s.renderer.info.gains;
    out.push({ L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, pos: s.grid.posAt(performance.now() + s.grid.presentLagMs),
               hl: s.rings.hl || 0, lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0 });
  }
  return out; })`;
async function ringHeroSeries({ ev, phase, tag, shotId, frames, deadline }) {
  await ev(`window.__stage.setShot(${JSON.stringify(shotId)}, 0.95)`);
  const series = [];
  // the discharge is pressed after a second; it lands on the next bar line
  for (let done = 0; done < frames && Date.now() < deadline - 15000; done += 60) series.push(...await ev(`${RING_RUN}(${Math.min(60, frames - done)}, ${done === 60 ? 0 : -1})`, 160000));
  const j = judgeFlashes(series);
  const fired = await ev("window.__stage.state().rings.hero.fired.slice(-1)[0] || null");
  const first = series.find((x) => x.hl > 0);
  phase[`${tag}_judged`] = { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red, frames: series.length, limited: series.filter((x) => x.lim).length };
  check(`${tag}: HERO's discharge lands on its ONE (+-1 frame) through the FlashGate`, fired && fired.granted && first && Math.abs(first.pos - fired.at) * 24 <= 1.01,
        { fired, first_lit_pos: first && +first.pos.toFixed(4) });
  check(`${tag}: at most 3 flashes a second in every window, red at most 3, through the discharge (${series.length} frames on ${shotId})`,
        series.length >= 180 && j.worst <= 3 && j.worst_red <= 3, phase[`${tag}_judged`]);
}

async function phaseOrrery({ ev, open, shot, phase, deadline }) {
  await open(`demo=1&vt=1&ring=orrery&theme=dreaming-city&${BASE}`);
  await ev(PAGE_PROBE);
  await ev(`(() => { const s = window.__stage; s.show.update = () => []; for (let i = 0; i < 20; i++) window.__vt.step(${F}); return true; })()`);
  // the gimbals turn at their own prime rates: ten beats, logic only
  const m = await ev(`(() => { const s = window.__stage; s.skipRender = true;
    const a = s.rings.rr.poses.map((p) => ({ ...p })), p0 = s.grid.posAt(performance.now() + s.grid.presentLagMs);
    for (let i = 0; i < 240; i++) window.__vt.step(${F});
    const b = s.rings.rr.poses.map((p) => ({ ...p })), p1 = s.grid.posAt(performance.now() + s.grid.presentLagMs);
    s.skipRender = false; return { a, b, beats: p1 - p0 }; })()`);
  const rate = (k, d) => (m.b[k][d] - m.a[k][d]) / m.beats;
  const want = [["spin", 0, 360 / 113], ["yaw", 1, 360 / 89], ["yaw", 2, -360 / 67], ["yaw", 3, 360 / 37]];
  phase.rates = want.map(([d, k, w]) => ({ ring: k, dof: d, measured: +rate(k, d).toFixed(4), want: +w.toFixed(4) }));
  check("orrery: the gimbals stand at 55 / 80 / 60 / 30 and turn at their own prime rates (R0 spins 360/113, R1 360/89, R2 -360/67, R3 360/37 degrees a beat)",
        m.b.map((p) => Math.round(p.tilt)).join() === "55,80,60,30" && want.every(([d, k, w]) => Math.abs(rate(k, d) - w) <= Math.abs(w) * 0.03), phase.rates);
  // the scenery: the core mesh and the formation's emitters, from each hero view (the contact sheet)
  for (const id of ["ORRERY_UNDER", "ORRERY_HERO", "ORRERY_HIGH", "ORRERY_NEAR"]) {
    await ev(`(() => { window.__stage.setShot(${JSON.stringify(id)}, 0.6); for (let i = 0; i < 3; i++) window.__vt.step(${F}); return true; })()`);
    await shot(join(outDir, `orrery-${id.toLowerCase()}.png`));
  }
  const sc = await ev("({ core: window.__stage.renderer.orbMesh.visible, emit: window.__stage.rings.emit.n, info: window.__stage.state().info })");
  phase.scenery = sc;
  check("orrery: the core is drawn, with its bands, planets and star motes (the formation's emitters)", sc.core && sc.emit > 1500 && sc.info.emitters > 4000, sc);
  await ringHeroSeries({ ev, phase, tag: "orrery", shotId: "ORRERY_NEAR", frames: 240, deadline });
  const errs = phase.exceptions.length + (await ev("window.__stage.errors.length"));
  check("orrery: no exceptions", errs === 0, { exceptions: phase.exceptions.slice(0, 3), page: await ev("window.__stage.errors.slice(0, 3)") });
}

async function phaseSpiral({ ev, open, shot, phase, deadline }) {
  await open(`demo=1&vt=1&theme=dreaming-city&${BASE}`);
  await ev(PAGE_PROBE);
  // MORPH from home: pad 8 deals the orrery, the deck's next; then the spiral lands through the same door, logic only,
  // with the camera's landing grammar watched every frame (the glide, the cut ON the landing bar line to the hero view)
  // (the show's first section sets the strand's formation first: a ring formation lands from it, as on the page)
  const setup = await ev(`(async () => { const s = window.__stage; s.skipRender = true;
    for (let i = 0; i < 120; i++) window.__vt.step(${F});
    s.show.update = () => [];
    s.press(8, 1); const morphed = s.rings.key;
    s.ringSet("home");
    const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs);
    s.director.start("groove", s.grid.nextBarPos(pos) - 8);
    for (let i = 0; i < 6; i++) window.__vt.step(${F});
    const r = s.ring("spiral");
    const C = await import("/web/stage/camera.js");
    window.__cam = { C, model: C.cameraModel(s.rig) };
    return { morphed, start: r.start, posLand: r.posLand, barAnchor: s.grid.barAnchor }; })()`);
  phase.setup = setup;
  check("spiral: MORPH (pad 8) steps home to the deck's next formation, the orrery", setup.morphed === "orrery", setup);
  const RUN = String.raw`((frames) => { const s = window.__stage, out = [], C = window.__cam.C, m = window.__cam.model;
    for (let i = 0; i < frames; i++) {
      window.__vt.step(1000 / 60);
      const pos = s.grid.posAt(performance.now() + s.grid.presentLagMs), p = s.director.pose, rings = s.rings.liveAnnuli() || m.rings;
      out.push({ pos, shot: p.shot, cut: p.cut, why: p.cut ? s.director.cuts.at(-1).why : null,
                 clear: Math.min(C.clearanceToStrand(p.pos, s.strand.poses, m.z), C.clearanceToRings(p.pos, rings)) });
    }
    return out; })`;
  const series = [];
  while (Date.now() < deadline - 90000) {
    const chunk = await ev(`${RUN}(240)`, 160000);
    series.push(...chunk);
    if (chunk.at(-1).pos > setup.posLand + 6) break;
  }
  const cuts = series.filter((r) => r.cut).map((r) => ({ pos: +r.pos.toFixed(4), shot: r.shot, why: r.why }));
  const hero = cuts.find((c) => c.why === "landing-hero"), glide = cuts.find((c) => c.why === "landing-glide");
  const guards = await ev("window.__stage.director.clear.guards");
  const poses = await ev("window.__stage.state().rings.poses");
  phase.landing = { cuts, guards, poses };
  check("spiral: the rings land on the bar line their last ring makes, coplanar at 55 and stepped 3 m up their axis",
        Math.abs((((setup.posLand - setup.barAnchor) % 4) + 4) % 4) < 1e-6 && poses.every((p, k) => Math.abs(p.tilt - 55) < 0.05 && Math.abs(p.axial - 3 * k) < 0.02),
        { posLand: setup.posLand, poses });
  check("spiral: the camera glides from a bar line while the rings move, then cuts ON the landing bar line (+-1 frame) to the spiral's hero view",
        glide && hero && hero.shot === "SPIRAL_HERO" && Math.abs(hero.pos - setup.posLand) * 24 <= 1.01, { glide, hero, posLand: setup.posLand });
  const worst = series.length ? Math.min(...series.map((r) => r.clear)) : null;
  check("spiral: on no frame was the lens within 1.5 m of the live rings or the strand, and the guard never acted",
        series.length > 300 && worst >= 1.5 && guards === 0, { frames: series.length, closest_m: worst && +worst.toFixed(3), guards });
  // drawn: the well from below and from above, the energy column among the beams
  await ev("window.__stage.skipRender = false");
  for (const id of ["SPIRAL_HERO", "HALO_LOCK"]) {
    await ev(`(() => { window.__stage.setShot(${JSON.stringify(id)}, 0.5); for (let i = 0; i < 3; i++) window.__vt.step(${F}); return true; })()`);
    await shot(join(outDir, `spiral-${id.toLowerCase()}.png`));
  }
  const info = await ev("window.__stage.state().info");
  phase.info = info;
  check("spiral: the energy column draws as a beam beside the halo's", info.beams >= 1 && (await ev("window.__stage.rings.beams.length")) === 1, info);
  await ringHeroSeries({ ev, phase, tag: "spiral", shotId: "SPIRAL_HERO", frames: 240, deadline });
  const errs = phase.exceptions.length + (await ev("window.__stage.errors.length"));
  check("spiral: no exceptions", errs === 0, { exceptions: phase.exceptions.slice(0, 3), page: await ev("window.__stage.errors.slice(0, 3)") });
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
async function phaseKickStorm(ctx) { return phaseFlash(ctx, "kicks"); }
// KICK v2's pre-registered case K1 (kickstorm), frame by frame through the page-level pad door; segments A-D as written in
// research/in-flight/kick-v2-report-2026-10-27.md before the first run
const KICK_SEGMENTS = { A: [40, 220], B: [240, 420], C: [440, 620], D: [640, 700], E: [720, 900] };
// case K1 over frames frame0.. (cells: per frame {lim, ks, kn, rows}); j: the verifier's judgement of those frames
function kickCase(cells, frame0, j, errs) {
  const seg = {};
  const end = frame0 + cells.length;
  for (const [k, [a, b]] of Object.entries(KICK_SEGMENTS)) {
    const xs = cells.slice(Math.max(0, a - frame0), Math.max(0, Math.min(b, end) - frame0));
    seg[k] = { frames: xs.length, whole: a >= frame0 && b <= end, limited: xs.filter((x) => x.lim).length, strobing_frames: xs.filter((x) => x.ks > 0).length,
               hold90: xs.filter((x) => x.hd >= 0.9).length, edge10: xs.filter((x) => x.sm >= 0.1).length, hard_hold: xs.filter((x) => x.he).length,
               max_hold: +Math.max(0, ...xs.map((x) => x.hd || 0)).toFixed(4), max_seam: +Math.max(0, ...xs.map((x) => x.sm || 0)).toFixed(4),
               both_strobing: xs.filter((x) => x.ks >= 2).length, two_live: xs.filter((x) => x.kn >= 2).length, rows: [...new Set(xs.map((x) => x.rows).filter(Boolean))].slice(0, 12) };
  }
  const held = ["A", "B", "C"].filter((k) => seg[k].frames);
  const heldFrames = held.reduce((s, k) => s + seg[k].frames, 0), heldLimited = held.reduce((s, k) => s + seg[k].limited, 0);
  const input = {
    A: seg.A.whole ? seg.A.strobing_frames > 60 : null,
    B: seg.B.whole ? seg.B.both_strobing > 60 : null,
    C: seg.C.whole ? seg.C.strobing_frames > 20 && seg.C.strobing_frames < seg.C.frames - 20 : null,
    // D (round 2): the taps re-strike the two buttons' areas (a press while its area is lit), so the storm shows as both
    // buttons live, not as round 1's run of different rows
    D: seg.D.whole ? seg.D.two_live >= 30 : null,
    E: seg.E.whole ? seg.E.rows.length >= 1 && seg.E.frames > 0 : null,
  };
  return {
    segments: seg, input, input_ok: Object.values(input).every((v) => v !== false) && Object.values(input).some((v) => v === true),
    prereg: {
      P1_gate: { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red, held: j.worst <= 3 && j.worst_red <= 3 },
      P2_held_strobe_limited_share: { frames: heldFrames, limited: heldLimited, share: +(heldLimited / Math.max(1, heldFrames)).toFixed(4), held: heldLimited / Math.max(1, heldFrames) < 0.1 },
      P3_tap_storm_limited: seg.D.whole ? { frames: seg.D.frames, limited: seg.D.limited, held: seg.D.limited > 0 } : { frames: seg.D.frames, note: "segment D not wholly in these frames" },
      P4_red_zero: { worst_red: j.worst_red, held: j.worst_red === 0 },
      P5_no_errors: { errors: errs, held: errs === 0 },
      P8_rapid_full_taps_limited_share: seg.E.whole ? { frames: seg.E.frames, limited: seg.E.limited, share: +(seg.E.limited / Math.max(1, seg.E.frames)).toFixed(4), held: seg.E.limited / Math.max(1, seg.E.frames) < 0.05 } : { frames: seg.E.frames, note: "segment E not wholly in these frames" },
    },
  };
}
// --stitch dirA,dirB,...: the kickstorm chunks of one case. Since round 2 the kick's flash governor reads the final
// limiter's history, which a chunk's logic-only replay does not have, so chunks need not agree where they overlap: each
// chunk is judged on its own (the verifier's count, every window inside it), the chunks overlapping by a second or more so
// every one-second window of the case lies wholly inside one chunk, and each segment is read from the chunk that holds it.
function stitchKickstorm(dirs) {
  const parts = dirs.map((d) => {
    const r = JSON.parse(readFileSync(join(d, "receipt.json"), "utf8"));
    const k = r.phases.kickstorm;
    if (!k || !k.cells) throw new Error(`${d}: no kickstorm cells (run it with this version of the receipt)`);
    return { dir: d, frame0: k.frame0, cells: k.cells.map((c) => ({ ...c, N: k.N })), size: k.size, errs: k.prereg && k.prereg.P5_no_errors ? k.prereg.P5_no_errors.errors : 0 };
  }).sort((a, b) => a.frame0 - b.frame0);
  const total = Math.round(Number(opt["kick-seconds"]) * 60);
  const ends = parts.map((p) => p.frame0 + p.cells.length);
  let covered = parts[0].frame0 === 0 && ends[ends.length - 1] >= total - 10;
  const overlaps = [];
  for (let i = 1; i < parts.length; i++) { const o = ends[i - 1] - parts[i].frame0; overlaps.push(o); if (o < 60) covered = false; }
  // the overlap, for the record: how far the chunks' frames differ where both drew them
  const diffs = [];
  for (let i = 1; i < parts.length; i++) {
    const A = parts[i - 1], B = parts[i];
    for (let f = B.frame0; f < ends[i - 1]; f++) { const x = A.cells[f - A.frame0], y = B.cells[f - B.frame0]; if (x && y) diffs.push(Math.max(...x.L.map((v, q) => Math.abs(v - y.L[q])))); }
  }
  const judged = parts.map((p) => ({ dir: p.dir, from: p.frame0, frames: p.cells.length, ...(() => { const j = judgeFlashes(p.cells); return { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red }; })() }));
  const worst = Math.max(...judged.map((j) => j.worst)), worstRed = Math.max(...judged.map((j) => j.worst_red));
  const errs = parts.reduce((s, p) => s + p.errs, 0);
  // each segment from the first chunk that holds it whole
  const seg = {}, input = {};
  for (const [name, [a, b]] of Object.entries(KICK_SEGMENTS)) {
    const p = parts.find((q) => q.frame0 <= a && q.frame0 + q.cells.length >= b);
    if (!p) { seg[name] = { frames: 0, whole: false }; continue; }
    const c = kickCase(p.cells, p.frame0, { worst, worst_window: "", worst_red: worstRed }, errs);
    seg[name] = { ...c.segments[name], chunk: p.dir }; input[name] = c.input[name];
  }
  const held = ["A", "B", "C"].filter((k) => seg[k].frames);
  const heldFrames = held.reduce((s, k) => s + seg[k].frames, 0), heldLimited = held.reduce((s, k) => s + seg[k].limited, 0);
  const segs = Object.keys(KICK_SEGMENTS).filter((k) => seg[k].frames);
  const sum = (f) => segs.reduce((a, k) => a + (seg[k][f] || 0), 0);
  report.phases.stitch_holds = { segments: segs.join(""), frames: sum("frames"), limited: sum("limited"), hold90: sum("hold90"), edge10: sum("edge10"),
                                 hard_hold: sum("hard_hold"), max_hold: Math.max(0, ...segs.map((k) => seg[k].max_hold || 0)), max_seam: Math.max(0, ...segs.map((k) => seg[k].max_seam || 0)) };
  console.log(`kickstorm chunked holds (the frozen-tile measure, segments ${segs.join("")}): ${JSON.stringify(report.phases.stitch_holds)}`);
  const prereg = {
    P1_gate: { worst, worst_red: worstRed, held: worst <= 3 && worstRed <= 3, chunks: judged },
    P2_held_strobe_limited_share: { frames: heldFrames, limited: heldLimited, share: +(heldLimited / Math.max(1, heldFrames)).toFixed(4), held: heldLimited / Math.max(1, heldFrames) < 0.1 },
    P3_tap_storm_limited: { frames: seg.D.frames, limited: seg.D.limited, held: seg.D.limited > 0 },
    P4_red_zero: { worst_red: worstRed, held: worstRed === 0 },
    P5_no_errors: { errors: errs, held: errs === 0 },
    P8_rapid_full_taps_limited_share: seg.E && seg.E.frames ? { frames: seg.E.frames, limited: seg.E.limited, share: +(seg.E.limited / Math.max(1, seg.E.frames)).toFixed(4), held: seg.E.limited / Math.max(1, seg.E.frames) < 0.05 } : null,
  };
  report.title = "KICK v2 case K1 (+ K3), judged chunk by chunk";
  report.phases.stitch = { parts: judged, overlaps, overlap_max_diff: diffs.length ? +Math.max(...diffs).toFixed(4) : null, segments: seg, prereg };
  check(`stitch: the chunks cover the case (frames 0..${total - 1}) and overlap by a second or more, so every one-second window is inside one chunk`, covered, { from: parts.map((p) => p.frame0), ends, overlaps });
  check(`kickstorm (chunked): at most 3 flashes a second in every window of every chunk, red at most 3 (case K1 + K3, ${total} frames)`, covered && worst <= 3 && worstRed <= 3, { worst, worst_red: worstRed, chunks: judged.map((j) => [j.from, j.worst, j.worst_window]) });
  check("kickstorm (chunked): the input happened in every segment", Object.keys(KICK_SEGMENTS).every((k) => input[k] === true), input);
  check("kickstorm (chunked): no exceptions or console errors in any chunk", errs === 0, { errors: errs });
  console.log(`kickstorm chunked pre-registered: ${JSON.stringify(prereg)}`);
  console.log(`kickstorm chunked segments: ${JSON.stringify(seg)}`);
  console.log(`kickstorm chunked overlap max difference (for the record): ${report.phases.stitch.overlap_max_diff}`);
}
async function phaseFlash({ ev, open, shot, phase, deadline }, storm = false) {
  const kicks = storm === "kicks";
  const scale = kicks ? (Number(opt["kick-scale"]) || 0.5) : (Number(opt["flash-scale"]) || 1);
  const fromBar = kicks ? 14 : (Number(opt["flash-from-bar"]) || 14);
  const fw = Math.round(W * scale), fh = Math.round(H * scale);
  await open(`demo=1&vt=1&w=${fw}&h=${fh}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`);
  await ev(PAGE_PROBE);
  // fast-forward to two bars before the drop (bar 14; --flash-from-bar), logic only, then 30 frames drawn
  phase.from_bar = fromBar;
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * ${fromBar} - 30; i++) window.__vt.step(${F}); s.skipRender = false; for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`, 170000);
  const lim0 = await ev("window.__stage.limiter.stats()");
  const laser0 = await ev("({ onsets: window.__stage.lasers.count, presses: window.__stage.lasers.presses || 0 })");
  // then every frame: the drop's KICKs and FLY-OUT come from the demo; on top, a laser pad storm (pad 2 every 4 frames
  // for a second, then a held gate) and the director's cuts; or (kicks) case K1 through the pad door
  const RUN = String.raw`((frames, storm0, mode, draw = true, debug = false) => {
    const s = window.__stage, out = [];
    s.skipRender = !draw;
    const door = (type, detail) => window.dispatchEvent(new CustomEvent(type, { detail }));
    const kp = (pad, vel, on) => door("arsenal:pad", { pad, vel, on }), kl = (pad, vel) => door("arsenal:padlevel", { pad, vel });
    for (let i = 0; i < frames; i++) {
      const f = storm0 + i;
      if (mode === "storm") {
        if (f >= 140 && f < 200 && f % 4 === 0) s.press(2, 1);
        if (f >= 140 && f < 200 && f % 4 === 2) s.release(2);
        if (f === 230) s.press(2, 1);
        if (f === 290) s.release(2);
      } else if (mode === "kicks") {
        if (f === 40) kp(1, 1, true);
        if (f === 220) kp(1, 0, false);
        if (f === 240) { kp(1, 1, true); kp(5, 1, true); }
        if (f === 420) { kp(1, 0, false); kp(5, 0, false); }
        if (f === 440) kp(5, 0.9, true);
        if (f === 470) kl(5, 1); if (f === 500) kl(5, 0.9); if (f === 530) kl(5, 1); if (f === 560) kl(5, 0.92); if (f === 590) kl(5, 1);
        if (f === 620) kp(5, 0, false);
        if (f >= 640 && f < 700) { const q = f - 640, pad = Math.floor(q / 6) % 2 ? 5 : 1; if (q % 6 === 0) kp(pad, 1, true); if (q % 6 === 3) kp(pad, 0, false); }
        // round 2, case K3: rapid alternating taps of both kicks at full level, every 8 frames for 3 s
        if (f >= 720 && f < 904) { const q = f - 720, pad = Math.floor(q / 8) % 2 ? 5 : 1; if (q % 8 === 0 && f < 900) kp(pad, 1, true); if (q % 8 === 4) kp(pad, 0, false); }
      }
      window.__vt.step(1000 / 60);
      if (!draw) continue;
      const c = window.__probe.cells();
      const g = s.renderer.info.gains;
      const row = { L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, section: s.state().section, shot: s.director.pose.shot,
                    lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0 };
      // the frozen-tile measure (flash toggle, 2026-10-28): hd, the largest share of any point of the shown frame that is
      // the previous shown frame (a hold); sm, the largest step of the limiter's controls across a cell border (a seam);
      // he, a hold of 0.9 or more at a cell with such a step of 0.1 or more beside it (a hard-edged hold). From the
      // limiter's own gains, the ones the apply pass used this frame (a limiter with holdMetrics() measures itself; the v1
      // limiter's per-cell gains are measured here)
      if (s.limiter && s.limiter.gains) {
        const hm = typeof s.limiter.holdMetrics === "function" ? s.limiter.holdMetrics() : ((A, B) => {
          let hd = 0, sm = 0, he = 0;
          for (let q = 0; q < 16; q++) {
            hd = Math.max(hd, B[q]);
            const nb = [];
            if (q % 4 < 3) nb.push(q + 1);
            if (q % 4 > 0) nb.push(q - 1);
            if (q < 12) nb.push(q + 4);
            if (q >= 4) nb.push(q - 4);
            for (const o of nb) {
              const st = Math.max(Math.abs(A[q] - A[o]), Math.abs(B[q] - B[o]));
              sm = Math.max(sm, st);
              if (B[q] >= 0.9 && st >= 0.1) he = 1;
            }
          }
          return { hd, sm, he };
        })(s.limiter.gains.cellA, s.limiter.gains.cellB);
        row.hd = +hm.hd.toFixed(4); row.sm = +hm.sm.toFixed(4); row.he = hm.he ? 1 : 0;
        if (!row.lim) { row.hd = 0; row.sm = 0; row.he = 0; }
      }
      if (mode === "kicks") { const ks = s.programmer.kick.list; row.kn = ks.length; row.ks = ks.filter((k) => k.strobing).length; row.rows = ks.map((k) => k.card.name).join("+"); }
      else if (debug) { const K = s.programmer.kick; row.kd = { room: K.headroom, live: K.list.map((k) => [k.kind, k.card.name, +K._env(k, s.state().pos ?? 0).toFixed(3), k.motion ? k.motion.id : null, k.held ? 1 : 0]), gov: { ...K.gov }, beams: s.renderer.info.beams, lm: s.renderer.info.beamPowerLm, ib: s.renderer.inBeamFaded || 0 }; }
      out.push(row);
    }
    s.skipRender = false;
    return out;
  })`;
  const series = [];
  const total = Math.round(Number(kicks ? opt["kick-seconds"] : opt["flash-seconds"]) * 60);
  const mode = kicks ? "kicks" : storm ? "storm" : "flash";
  // kickstorm in chunks: frames before `from` replayed as logic only (with their input), from..want drawn
  const from = kicks ? Math.max(0, Number(opt["kick-from-frame"]) || 0) : 0;
  const want = kicks && Number(opt["kick-to-frame"]) > 0 ? Math.min(total, Number(opt["kick-to-frame"])) : total;
  for (let done = 0; done < from; done += 240) await ev(`${RUN}(${Math.min(240, from - done)}, ${done}, ${JSON.stringify(mode)}, false)`, 160000);
  phase.frame0 = from;
  const t0 = Date.now();
  // --flash-shots: a screenshot after each of these frames (diagnosis; scratch only)
  const shots = String(opt["flash-shots"] || "").split(",").filter((x) => x.trim() !== "").map(Number).filter((x) => Number.isInteger(x) && x >= from && x < want).sort((a, b) => a - b);
  for (let done = from; done < want && Date.now() < deadline - 20000;) {
    const next = shots.find((x) => x >= done);
    const n = Math.min(60, want - done, next !== undefined ? next - done + 1 : Infinity);
    series.push(...await ev(`${RUN}(${n}, ${done}, ${JSON.stringify(mode)}, true, ${opt["flash-debug"] ? "true" : "false"})`, 160000));
    done += n;
    if (next !== undefined && done === next + 1) await shot(join(outDir, `flash-f${next}.png`));
  }
  phase.frames = series.length;
  phase.ms_per_frame = +((Date.now() - t0) / Math.max(1, series.length)).toFixed(0);
  phase.size = [fw, fh];
  const j = judgeFlashes(series);
  phase.judged = { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red, full: j.windows.full, windows: j.windows };
  phase.limited_frames = series.map((x, i) => (x.lim ? i : -1)).filter((i) => i >= 0).slice(0, 80);
  phase.holds = { frames: series.length, limited: series.filter((x) => x.lim).length, hold90: series.filter((x) => x.hd >= 0.9).length,
                  edge10: series.filter((x) => x.sm >= 0.1).length, hard_hold: series.filter((x) => x.he).length,
                  max_hold: +Math.max(0, ...series.map((x) => x.hd || 0)).toFixed(4), max_seam: +Math.max(0, ...series.map((x) => x.sm || 0)).toFixed(4) };
  console.log(`${kicks ? "kickstorm" : storm ? "storm" : "flash"} holds (the frozen-tile measure): ${JSON.stringify(phase.holds)}`);
  if (opt["flash-debug"] && !kicks) phase.debug_frames = series.map((x) => ({ L: x.L, R: x.R, N: x.N, lim: x.lim, kd: x.kd, shot: x.shot }));
  phase.full_series = series.slice(0, 160).map((x) => +(x.L.reduce((a, v, i) => a + v * x.N[i], 0) / x.N.reduce((a, v) => a + v, 0)).toFixed(4));
  phase.timeline = series.map((x, i) => [i, x.section, x.shot]).filter((r, i, a) => i === 0 || r[1] !== a[i - 1][1] || r[2] !== a[i - 1][2]);
  phase.sections = [...new Set(series.map((s) => s.section))];
  phase.shots = [...new Set(series.map((s) => s.shot))];
  const lim1 = await ev("window.__stage.limiter.stats()");
  const laser1 = await ev("({ onsets: window.__stage.lasers.count, presses: window.__stage.lasers.presses || 0 })");
  phase.lasers = { presses: laser1.presses - laser0.presses, onsets: laser1.onsets - laser0.onsets };
  phase.limiter = { interventions: lim1.interventions - lim0.interventions, frames: lim1.frames - lim0.frames, beta_frames: lim1.beta_frames - lim0.beta_frames, log: lim1.log };
  const what = kicks ? "case K1: held top-level kicks (A), both buttons held (B), a level wobbling across the strobe band (C), a 10-a-second tap storm (D), through the pad door, over the build's laser gate, the cut and the drop's phrase"
             : storm ? "the build's held laser gate into the drop, KICKs, FLY-OUT, the cut, plus a laser pad storm (15 presses a second for a second, then a held gate)"
             : fromBar === 14 ? "the demo as programmed: the build's held laser gate, the flythrough, the cut into the drop, KICKs and FLY-OUT"
             : `the demo as programmed from bar ${fromBar}: the drop's KICK on every downbeat, its laser hits, FLY-OUT and cuts`;
  const tag = kicks ? "kickstorm" : storm ? "storm" : "flash";
  check(`${tag}: at most 3 flashes a second in every window, red at most 3 (${series.length} frames${kicks ? ` (frames ${from}..${from + series.length - 1})` : ""}, ${fw}x${fh}: ${what})`,
        (kicks ? series.length === want - from : series.length >= 240) && j.worst <= 3 && j.worst_red <= 3, { worst: j.worst, window: j.worst_window, worst_red: j.worst_red, frames: series.length });
  if (kicks) {
    // every frame's cells, for --stitch (the chunks of one run judged as one)
    phase.N = series.length ? series[0].N : null;
    phase.cells = series.map((x) => ({ L: x.L, R: x.R, lim: x.lim, ks: x.ks, kn: x.kn, rows: x.rows, hd: x.hd, sm: x.sm, he: x.he }));
    const pageErrors = await ev("window.__stage.errors.slice(0, 5)");
    const errs = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length + pageErrors.length;
    Object.assign(phase, kickCase(phase.cells, from, j, errs));
    const ks = await ev("window.__stage.programmer.kick.status()");
    phase.kick_status = { presses: ks.presses, presses_unlit: ks.presses_unlit, restrikes: ks.restrikes, areas_passed_over: ks.areas_passed_over, governor_held_back: ks.governor_held_back };
    console.log(`kickstorm kick (cumulative from frame 0): ${JSON.stringify(phase.kick_status)}`);
    console.log(`kickstorm pre-registered (frames ${from}..${from + series.length - 1}): ${JSON.stringify(phase.prereg)}`);
    console.log(`kickstorm segments: ${JSON.stringify(phase.segments)}`);
    const inside = Object.entries(phase.segments).filter(([, s]) => s.whole).map(([k]) => k);
    check(`kickstorm: the input happened in the segments this run drew (${inside.join(", ") || "none whole"})`, phase.input_ok, phase.input);
    check("kickstorm: no exceptions or console errors", errs === 0, { exceptions: phase.exceptions.slice(0, 3), page: pageErrors });
    phase.note = "case K1: the gate (P1) is a check; P2 and P3 are predictions reported in phase.prereg, the limiter being the backstop for a tap storm";
  } else if (storm) phase.note = "a pad storm on the lasers is the final limiter's job in v0 (the predictive governor is v1): interventions are reported, not failed";
  else check(`flash: the stage's limiter recorded zero interventions (the programmed show stays inside the budget${fromBar !== 14 ? `, from bar ${fromBar}` : ""})`, phase.limiter.interventions === 0, phase.limiter);
}

// KICK round 2's acceptance: what the SCREEN shows. The page in engine mode on the fake engine (no beats: the grid
// free-runs at 150 BPM on the virtual clock, the show sits in its groove section, no demo pads, no phrases), at the
// phone-like 832 x 384. Each look is set on the programmer; on each of its main shots (pinned) a white and a colour case.
// The same frames are drawn twice -- page A without the kick, page B with it pressed through the pad door (0.8, held) --
// and every pixel compared in CIELAB: a pixel CHANGES when it moves by more than dE76 --pix-de (10). A case's coverage is
// the larger of its two frames' changed share (a quarter beat and a beat after the press); its control frame, just before
// the press, must be identical in A and B.
const PIX_SHOTS = {
  intro: ["FOH_HOLD_ZOOM", "CRANE_RISE_REVEAL", "FOH_WIDE", "TRIBUNE_34"],
  build: ["STRAND_FLYTHROUGH", "FOH_WIDE", "HEAD_ORBIT", "TUNNEL_UP"],
  drop: ["TUNNEL_UP", "TOPDOWN_GODVIEW", "TRIBUNE_34", "HEAD_ORBIT", "FOH_WIDE", "CROWD_POV", "WORM_RING"],
  break: ["HEAD_ORBIT_SLOW", "DJ_OTS", "FOH_WIDE", "CROWD_POV"],
  groove: ["FOH_HOLD_ZOOM", "TRIBUNE_34", "PROFILE_GRAPH", "HEAD_ORBIT"],
};
const PIX_W = 832, PIX_H = 384;
// sRGB 8-bit -> CIELAB (D65), and the share of pixels whose colour moved by more than each threshold
const LIN8 = new Float64Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
const labF = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
function labBuf(px) {
  const n = px.length >> 2, out = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const r = LIN8[px[i * 4]], g = LIN8[px[i * 4 + 1]], b = LIN8[px[i * 4 + 2]];
    const fx = labF((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047), fy = labF(0.2126 * r + 0.7152 * g + 0.0722 * b), fz = labF((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
    out[i * 3] = 116 * fy - 16; out[i * 3 + 1] = 500 * (fx - fy); out[i * 3 + 2] = 200 * (fy - fz);
  }
  return out;
}
function pixDiff(labA, labB, ths = [5, 10, 20]) {
  const n = labA.length / 3, cnt = ths.map(() => 0);
  let sum = 0;
  for (let i = 0; i < n; i++) {
    const d = Math.hypot(labA[i * 3] - labB[i * 3], labA[i * 3 + 1] - labB[i * 3 + 1], labA[i * 3 + 2] - labB[i * 3 + 2]);
    sum += d;
    for (let k = 0; k < ths.length; k++) if (d > ths[k]) cnt[k]++;
  }
  return { share: Object.fromEntries(ths.map((t, k) => [`de${t}`, +(cnt[k] / n).toFixed(4)])), mean_de: +(sum / n).toFixed(3) };
}
function pixPlan(looks) {
  // each look: set at a block start, two bars to settle, then each case two bars (the press half a beat in)
  const cases = [];
  let pos = 16;
  for (const look of looks) {
    const setAt = pos;
    pos += 8;
    let first = true;
    for (const shot of PIX_SHOTS[look] || []) for (const [kind, pad] of [["kick-white", 1], ["kick-colour", 5]]) {
      // the press falls at a different place in its beat every case (0.37 apart), half of them in the beat's second half
      cases.push({ look, shot, kind, pad, start: pos, phase: +((0.1 + 0.37 * cases.length) % 1).toFixed(3), setLook: first ? setAt : null });
      first = false;
      pos += 8;
    }
  }
  return cases;
}
async function phaseKickPix({ ev, open, phase, deadline }) {
  const looks = opt["pix-looks"].split(",").map((s) => s.trim()).filter((l) => PIX_SHOTS[l]);
  const de = Number(opt["pix-de"]) || 10;
  const cases = pixPlan(looks).slice(0, Number(opt["pix-max-cases"]) || Infinity);
  phase.size = [PIX_W, PIX_H]; phase.de = de; phase.cases_planned = cases.length;
  // one case in the page: logic to its start (setting the look first if it opens a block), the shot pinned, the limiter
  // fresh, three frames drawn, the control frame read, the press (page B), frames read a quarter beat and a beat later,
  // the release; returns the frames as base64 RGBA (rows bottom-up, the same in A and B)
  const CASE = String.raw`((c, withKick, debug) => {
    const s = window.__stage, F = 1000 / 60;
    const t0 = window.__realNow ? window.__realNow() : 0;
    const log = (m) => { if (debug) console.log("kickpix " + m + " pos " + posNow().toFixed(3) + " real " + ((window.__realNow ? window.__realNow() : 0) - t0).toFixed(0) + " ms"); };
    const posNow = () => s.grid.posAt(performance.now() + s.grid.presentLagMs);
    const stepTo = (p, draw) => { s.skipRender = !draw; while (posNow() < p - 1e-9) window.__vt.step(F); s.skipRender = false; };
    const gl = s.renderer.gl, canvas = document.getElementById("gl");
    const read = () => {
      const w = canvas.width, h = canvas.height, buf = new Uint8Array(w * h * 4);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
      let bin = ""; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      const g = s.renderer.info.gains;
      return { w, h, b64: btoa(bin), lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0 };
    };
    const drawRead = () => { window.__vt.step(F); return read(); };
    log("start");
    if (c.setLook !== null) { stepTo(c.setLook, false); s.programmer.setLook(c.look, posNow(), { fade: 0 }); }
    log("look");
    stepTo(c.start + c.phase - 4 / 24, false);
    log("at case");
    s.setShot(c.shot, 0.5); s.resetLimiter();
    for (let i = 0; i < 3; i++) { window.__vt.step(F); log("warm " + i); }
    const control = drawRead();
    log("control");
    const pressAt = posNow();
    log("press");
    let dealt = null;
    if (withKick) {
      window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: c.pad, vel: 0.8, on: true } }));
      const live = s.programmer.kick.list.filter((k) => k.held).map((k) => k.card.name);
      dealt = live;
    }
    // the first three frames after the press (the latency), then a quarter beat and a beat after it
    const f1 = drawRead(), f2 = drawRead(), f3 = drawRead();
    stepTo(pressAt + 0.25, false);
    log("stepped");
    const q = drawRead();
    log("q");
    stepTo(pressAt + 1, false);
    const b = drawRead();
    log("b");
    const skipped = withKick ? s.programmer.kick.status() : null;
    if (withKick) window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: c.pad, vel: 0, on: false } }));
    // the frames stay in the page; the receipt fetches them in slices (a 5 MB answer never arrives through one CDP message)
    window.__pix = { control: control.b64, f1: f1.b64, f2: f2.b64, f3: f3.b64, q: q.b64, b: b.b64 };
    return { sizes: [control.b64.length, f1.b64.length, f2.b64.length, f3.b64.length, q.b64.length, b.b64.length],
             lim: control.lim + f1.lim + f2.lim + f3.lim + q.lim + b.lim, pressAt, dealt, presses: skipped ? skipped.presses : null,
             unlit: skipped ? skipped.presses_unlit ?? null : null, passed: skipped ? skipped.areas_passed_over ?? null : null };
  })`;
  const fetchPix = async (name, len) => {
    const parts = [];
    for (let i = 0; i < len; i += 262144) parts.push(await ev(`window.__pix.${name}.slice(${i}, ${i + 262144})`, 60000));
    return Buffer.from(parts.join(""), "base64");
  };
  const query = `engine=http://127.0.0.1:${ENGINE_PORT}&vt=1&w=${PIX_W}&h=${PIX_H}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`;
  // page A: the frames without the kick, kept as CIELAB
  await open(query);
  await waitFor(() => ev("window.__stage.state().engine.open"), 15000, "the engine link");
  const A = [];
  for (const c of cases) {
    if (Date.now() > deadline - 60000) break;
    const r = await ev(`${CASE}(${JSON.stringify(c)}, false, ${opt["pix-debug"] ? "true" : "false"})`, 160000);
    const fr = {};
    for (const [k, name] of ["control", "f1", "f2", "f3", "q", "b"].entries()) fr[name] = labBuf(await fetchPix(name, r.sizes[k]));
    A.push({ ...fr, lim: r.lim });
  }
  // page B: the same frames with the kick
  await open(query);
  await waitFor(() => ev("window.__stage.state().engine.open"), 15000, "the engine link");
  const rows = [];
  for (let i = 0; i < A.length; i++) {
    if (Date.now() > deadline - 15000) break;
    const c = cases[i];
    const r = await ev(`${CASE}(${JSON.stringify(c)}, true, ${opt["pix-debug"] ? "true" : "false"})`, 160000);
    const dd = {};
    for (const [k, name] of ["control", "f1", "f2", "f3", "q", "b"].entries()) dd[name] = pixDiff(A[i][name], labBuf(await fetchPix(name, r.sizes[k])));
    const ctl = dd.control, dq = dd.q, db = dd.b;
    const key = `de${de}`;
    // latency: the first frame after the press whose changed share (dE > de) reaches 1 % of the screen
    const lat = ["f1", "f2", "f3"].findIndex((n) => dd[n].share[key] >= 0.01);
    const best = dq.share[key] >= db.share[key] ? dq : db;
    rows.push({ look: c.look, shot: c.shot, kind: c.kind, dealt: r.dealt, coverage: best.share[key], at: best === dq ? "quarter beat" : "one beat",
                latency_frames: lat >= 0 ? lat + 1 : null, first_frames: ["f1", "f2", "f3"].map((n) => dd[n].share[key]), unlit: r.unlit, areas_passed_over: r.passed,
                shares: { q: dq.share, b: db.share }, control: ctl.share[key], limiter: A[i].lim + r.lim });
  }
  phase.cases = rows;
  const cov = rows.map((r) => r.coverage).sort((a, b) => a - b);
  const q = (p) => (cov.length ? cov[Math.min(cov.length - 1, Math.floor(p * (cov.length - 1)))] : null);
  phase.distribution = { cases: cov.length, min: cov[0], p10: q(0.1), median: q(0.5), max: cov[cov.length - 1] };
  const byLookKind = {};
  for (const r of rows) { const k = `${r.look} ${r.kind}`; (byLookKind[k] = byLookKind[k] || []).push(r.coverage); }
  phase.by_look_kind = Object.fromEntries(Object.entries(byLookKind).map(([k, v]) => [k, { min: Math.min(...v), median: v.slice().sort((a, b) => a - b)[v.length >> 1], max: Math.max(...v) }]));
  phase.worst = rows.slice().sort((a, b) => a.coverage - b.coverage).slice(0, 8).map((r) => ({ look: r.look, shot: r.shot, kind: r.kind, dealt: r.dealt, coverage: r.coverage }));
  const lats = rows.map((r) => r.latency_frames);
  phase.latency = { worst_frames: lats.some((x) => x === null) ? "over 3" : Math.max(...lats), by_frames: { 1: lats.filter((x) => x === 1).length, 2: lats.filter((x) => x === 2).length, 3: lats.filter((x) => x === 3).length, over3: lats.filter((x) => x === null).length } };
  console.log(`kickpix latency: ${JSON.stringify(phase.latency)}`);
  console.log(`kickpix: ${JSON.stringify(phase.distribution)}`);
  console.log(`kickpix by look and kind: ${JSON.stringify(phase.by_look_kind)}`);
  for (const r of rows) console.log(`kickpix case ${r.look.padEnd(6)} ${r.shot.padEnd(18)} ${r.kind.padEnd(11)} ${(100 * r.coverage).toFixed(1).padStart(5)} % (${r.at}; dE5 ${(100 * Math.max(r.shares.q.de5, r.shares.b.de5)).toFixed(1)} %, dE20 ${(100 * Math.max(r.shares.q.de20, r.shares.b.de20)).toFixed(1)} %) control ${(100 * r.control).toFixed(2)} % latency ${r.latency_frames ?? "> 3"} frames limiter ${r.limiter} dealt ${JSON.stringify(r.dealt)}`);
  check(`kickpix: every case was measured (${rows.length} of ${cases.length})`, rows.length === cases.length, { measured: rows.length, planned: cases.length });
  check("kickpix: every control frame is identical with and without the kick (the comparison is sound)", rows.every((r) => r.control === 0), rows.filter((r) => r.control !== 0).slice(0, 4));
  check(`kickpix: every kick changes at least 10 % of the screen by dE76 > ${de} (R1)`, rows.length && rows.every((r) => r.coverage >= 0.1), phase.distribution);
  check("kickpix: every kick shows on the first frame after its press (R4: 1 % of the screen by dE76 > 10)", rows.length && rows.every((r) => r.latency_frames === 1), phase.latency);
  phase.unlit = rows.length ? Math.max(...rows.map((r) => r.unlit ?? 0)) : null;
  // the AREAS the dealer judged and passed by (an area it would not show on), for the record: a press never goes unlit
  phase.areas_passed_over = rows.reduce((n, r) => n + (r.areas_passed_over ?? 0), 0);
  console.log(`kickpix: presses unlit ${phase.unlit}, areas the dealer passed over ${phase.areas_passed_over}`);
  check("kickpix: no press was left unlit (R5: presses_unlit stays 0)", rows.length && rows.every((r) => (r.unlit ?? 0) === 0), { presses_unlit: phase.unlit });
}

// KICK round 2, REPEAT HITS (R6, R7 in the report): the drop look on FOH_WIDE at 832 x 384, every frame drawn in page A
// (no taps) and page B (--repeat-kind's kick tapped at --repeat-rate a second for 1.25 s, frames 30 to 105, each tap held
// 3 frames, velocity 0.8; one kind a run so both pages fit one burst). A tap's change: pixels moving by dE76 > --pix-de between the frame before it and 6 frames after it in B
// but not in A. Every tap must change 3 % of the screen; the limiter may act on at most 2 % of B's frames.
async function phaseKickRepeat({ ev, open, phase, deadline }) {
  const rate = Number(opt["repeat-rate"]) || 6, de = Number(opt["pix-de"]) || 10;
  // one kind a run (both pages of 120 frames fit one burst): --repeat-kind colour or white
  const kindArg = opt["repeat-kind"] === "white" ? "white" : "colour";
  const segs = [kindArg === "white" ? { pad: 1, kind: "kick-white", from: 30, to: 105 } : { pad: 5, kind: "kick-colour", from: 30, to: 105 }];
  phase.kind = kindArg;
  const taps = [];
  for (const sg of segs) for (let k = 0; ; k++) { const f = sg.from + Math.round((k * 60) / rate); if (f >= sg.to) break; taps.push({ f, pad: sg.pad, kind: sg.kind }); }
  const total = 120;
  phase.rate = rate; phase.taps_planned = taps.length; phase.size = [PIX_W, PIX_H];
  const keep = new Set(taps.flatMap((t) => [t.f - 1, t.f + 6]));
  const RUN = String.raw`((from, n, withTaps, taps, keep) => {
    const s = window.__stage, F = 1000 / 60, out = [];
    const gl = s.renderer.gl, canvas = document.getElementById("gl");
    window.__rep = window.__rep || {};
    for (let i = 0; i < n; i++) {
      const f = from + i;
      if (withTaps) for (const t of taps) {
        if (t.f === f) window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: t.pad, vel: 0.8, on: true } }));
        if (t.f + 3 === f) window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: t.pad, vel: 0, on: false } }));
      }
      window.__vt.step(F);
      const c = window.__probe.cells();
      const g = s.renderer.info.gains;
      if (keep.includes(f)) {
        const w = canvas.width, h = canvas.height, buf = new Uint8Array(w * h * 4);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
        let bin = ""; for (let k = 0; k < buf.length; k += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(k, k + 0x8000));
        window.__rep[f] = btoa(bin);
      }
      const ks = s.programmer.kick.list;
      out.push({ L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0,
                 rows: ks.map((k) => k.card.name + ":" + (s.programmer.kick._hexOf ? s.programmer.kick._hexOf(k) : "")).join(" ") });
    }
    return out;
  })`;
  const SETUP = String.raw`(() => {
    const s = window.__stage, F = 1000 / 60;
    const posNow = () => s.grid.posAt(performance.now() + s.grid.presentLagMs);
    s.skipRender = true;
    while (posNow() < 16) window.__vt.step(F);
    s.programmer.setLook("drop", posNow(), { fade: 0 });
    while (posNow() < 24) window.__vt.step(F);
    s.skipRender = false;
    s.setShot("FOH_WIDE", 0.5); s.resetLimiter();
    return true;
  })()`;
  const query = `engine=http://127.0.0.1:${ENGINE_PORT}&vt=1&w=${PIX_W}&h=${PIX_H}&hud=0&quality=receipt&set=${opt.set}${opt.query ? `&${opt.query}` : ""}`;
  const fetchFrame = async (f) => {
    const len = await ev(`window.__rep[${f}].length`);
    const parts = [];
    for (let i = 0; i < len; i += 262144) parts.push(await ev(`window.__rep[${f}].slice(${i}, ${i + 262144})`, 60000));
    return labBuf(Buffer.from(parts.join(""), "base64"));
  };
  const runPage = async (withTaps) => {
    await open(query);
    await waitFor(() => ev("window.__stage.state().engine.open"), 15000, "the engine link");
    await ev(PAGE_PROBE);
    await ev(SETUP, 160000);
    const series = [];
    for (let done = 0; done < total && Date.now() < deadline - 25000; done += 30) {
      series.push(...await ev(`${RUN}(${done}, ${Math.min(30, total - done)}, ${withTaps}, ${JSON.stringify(taps)}, ${JSON.stringify([...keep])})`, 160000));
    }
    const frames = {};
    for (const f of keep) if (f < series.length) frames[f] = await fetchFrame(f);
    const status = withTaps ? await ev("window.__stage.programmer.kick.status()") : null;
    return { series, frames, status };
  };
  const A = await runPage(false);
  const B = await runPage(true);
  const share = (a0, a1, b0, b1) => {
    let n = 0, hit = 0;
    for (let i = 0; i < a0.length; i += 3) {
      const dB = Math.hypot(b1[i] - b0[i], b1[i + 1] - b0[i + 1], b1[i + 2] - b0[i + 2]);
      const dA = Math.hypot(a1[i] - a0[i], a1[i + 1] - a0[i + 1], a1[i + 2] - a0[i + 2]);
      if (dB > de && dA <= de) hit++;
      n++;
    }
    return hit / n;
  };
  const rows = [];
  for (const t of taps) {
    if (!(A.frames[t.f - 1] && A.frames[t.f + 6] && B.frames[t.f - 1] && B.frames[t.f + 6])) continue;
    rows.push({ f: t.f, kind: t.kind, change: +share(A.frames[t.f - 1], A.frames[t.f + 6], B.frames[t.f - 1], B.frames[t.f + 6]).toFixed(4), shows: B.series[t.f + 6] && B.series[t.f + 6].rows });
  }
  const j = judgeFlashes(B.series);
  const limB = B.series.filter((x) => x.lim).length, limA = A.series.filter((x) => x.lim).length;
  phase.taps = rows; phase.frames = { A: A.series.length, B: B.series.length };
  phase.limiter = { B: limB, A: limA, share_B: +(limB / Math.max(1, B.series.length)).toFixed(4), frames_B: B.series.map((x, i) => (x.lim ? i : -1)).filter((i) => i >= 0).slice(0, 40) };
  phase.judged = { worst: j.worst, worst_window: j.worst_window, worst_red: j.worst_red };
  phase.kick_status = B.status && { presses: B.status.presses, presses_unlit: B.status.presses_unlit, restrikes: B.status.restrikes,
                                     areas_passed_over: B.status.areas_passed_over, governor_held_back: B.status.governor_held_back };
  const ch = rows.map((r) => r.change);
  phase.change = { taps: rows.length, min: ch.length ? Math.min(...ch) : null, median: ch.length ? ch.slice().sort((a, b) => a - b)[ch.length >> 1] : null, max: ch.length ? Math.max(...ch) : null };
  console.log(`kickrepeat ${kindArg} ${rate} taps/s: ${JSON.stringify(phase.change)} limiter ${JSON.stringify(phase.limiter)} flashes ${JSON.stringify(phase.judged)} kick ${JSON.stringify(phase.kick_status)}`);
  for (const r of rows) console.log(`kickrepeat ${rate}/s tap at frame ${r.f} ${r.kind.padEnd(11)} ${(100 * r.change).toFixed(1).padStart(5)} %  ${r.shows || ""}`);
  check(`kickrepeat ${kindArg} ${rate}/s: every tap was measured (${rows.length} of ${taps.length}) over ${total} frames drawn in both pages`, rows.length === taps.length && A.series.length === total && B.series.length === total, { taps: rows.length, frames: phase.frames });
  check(`kickrepeat ${kindArg} ${rate}/s: every tap reads as a new hit (R6: at least 3 % of the screen changes by dE76 > ${de} that the scene alone did not change)`, rows.length && rows.every((r) => r.change >= 0.03), phase.change);
  check(`kickrepeat ${kindArg} ${rate}/s: the limiter acts on at most 2 % of the frames (R7)`, limB / Math.max(1, B.series.length) <= 0.02, phase.limiter);
  check(`kickrepeat ${kindArg} ${rate}/s: at most 3 flashes a second in every window, red at most 3`, j.worst <= 3 && j.worst_red <= 3, phase.judged);
  check(`kickrepeat ${kindArg} ${rate}/s: no press left unlit`, B.status && B.status.presses_unlit === 0, phase.kick_status);
}

// KICK v2 in the real page: the page-level pad door, the two buttons at once, the live level, the strobe band, key 5 and
// Shift; then four contact frames of the kicks on FOH_WIDE (the receipt folder, for the eye). Logic every 60 fps frame.
async function phaseKick({ ev, open, shot, phase }) {
  await open(`demo=1&vt=1&${BASE}`);
  // into the break (bar 41), where the demo presses no pads of its own (in the drop it presses pad 1 on every downbeat,
  // and a new press of a kick button lets go of that button's held kick), logic only
  await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 41 + 6; i++) window.__vt.step(${F}); return true; })()`, 170000);
  const step = (n) => ev(`(() => { for (let i = 0; i < ${n}; i++) window.__vt.step(${F}); return true; })()`, 170000);
  const door = (type, detail) => ev(`window.dispatchEvent(new CustomEvent(${JSON.stringify(type)}, { detail: ${JSON.stringify(detail)} }))`);
  const key = (type, code, shift = false) => ev(`window.dispatchEvent(new KeyboardEvent(${JSON.stringify(type)}, { code: ${JSON.stringify(code)}, shiftKey: ${shift} }))`);
  const live = () => ev("window.__stage.state().kick.live");
  check("kick: the page-level pad door is there (window.__padDoor = 1)", (await ev("window.__padDoor")) === 1, await ev("window.__padDoor"));
  const kicks0 = (await ev("window.__stage.state().kicks")).length;
  // the two buttons through the door, held together
  await door("arsenal:pad", { pad: 1, vel: 0.8, on: true }); await step(4);
  await door("arsenal:pad", { pad: 5, vel: 0.8, on: true }); await step(12);
  const both = await live();
  phase.both = both;
  const heldNow = both.filter((k) => k.held);
  check("kick: pads 1 and 5 through the door hold KICK WHITE and KICK COLOUR at once, on two different rows",
        heldNow.length === 2 && heldNow.some((k) => k.kind === "kick-white") && heldNow.some((k) => k.kind === "kick-colour") && heldNow[0].row !== heldNow[1].row, heldNow);
  // the live level, then the strobe band
  await door("arsenal:padlevel", { pad: 1, vel: 0.3 }); await step(20);
  const lv = (await live()).find((k) => k.kind === "kick-white" && k.held);
  check("kick: arsenal:padlevel moves the held row's level (0.8 -> 0.3 within 20 frames)", lv && Math.abs(lv.level - 0.3) < 0.02, lv);
  await door("arsenal:padlevel", { pad: 1, vel: 1 }); await step(40);
  const st1 = (await live()).find((k) => k.kind === "kick-white" && k.held);
  await door("arsenal:padlevel", { pad: 1, vel: 0.9 }); await step(60);
  const st2 = (await live()).find((k) => k.kind === "kick-white" && k.held);
  const colourNotStrobing = (await live()).find((k) => k.kind === "kick-colour" && k.held);
  check("kick: the strobe runs only while the live level is in the top band (on at 1.0, off back at 0.9; the colour kick at 0.8 never)",
        st1 && st1.strobing && st2 && !st2.strobing && colourNotStrobing && !colourNotStrobing.strobing, { at_1: st1, at_0_9: st2, colour: colourNotStrobing });
  // let go through the door: both fade and are gone two beats later
  await door("arsenal:pad", { pad: 1, vel: 0, on: false }); await door("arsenal:pad", { pad: 5, vel: 0, on: false });
  await step(3);
  const fading = await live();
  await step(60);
  const gone = await live();
  check("kick: let go, both rows fade and are gone within two beats", fading.length === 2 && fading.every((k) => !k.held) && gone.length === 0, { fading, gone });
  // the keyboard: key 5 holds KICK COLOUR at 0.8; Shift+1 holds KICK WHITE at 1.0 (the strobe band)
  await key("keydown", "Digit5"); await step(6);
  const k5 = (await live()).find((k) => k.held);
  await key("keyup", "Digit5"); await step(2);
  const k5up = (await live()).find((k) => k.kind === "kick-colour");
  await key("keydown", "Digit1", true); await step(30);
  const k1 = (await live()).find((k) => k.held);
  await key("keyup", "Digit1"); await step(60);
  check("kick: key 5 holds KICK COLOUR at 0.8 until key-up; Shift+1 holds KICK WHITE at 1.0, strobing",
        k5 && k5.kind === "kick-colour" && Math.abs(k5.target - 0.8) < 1e-9 && k5up && !k5up.held && k1 && k1.kind === "kick-white" && k1.target === 1 && k1.strobing, { k5, k5up, k1 });
  const st = await ev("window.__stage.state()");
  phase.kick_status = st.kick;
  const added = st.kicks.slice(kicks0);
  check("kick: every press is booked on the beat it fell on (onset = the nearest beat)", added.length >= 4 && added.every((k) => k.onset === Math.round(k.pressPos)), added.slice(0, 6));
  // contact frames on FOH_WIDE: nothing, white, white + colour, colour alone (logic as above, drawn)
  await ev(`(() => { const s = window.__stage; s.setShot("FOH_WIDE", 0.5); s.skipRender = false; for (let i = 0; i < 4; i++) window.__vt.step(${F}); return true; })()`);
  const frames = {};
  frames.none = await shot(join(outDir, "kick-0-none.png"));
  await door("arsenal:pad", { pad: 1, vel: 0.8, on: true }); await step(10);
  frames.white = await shot(join(outDir, "kick-1-white.png"));
  await door("arsenal:pad", { pad: 5, vel: 0.8, on: true }); await step(10);
  frames.both = await shot(join(outDir, "kick-2-both.png"));
  phase.frame_rows = (await live()).map((k) => `${k.kind} ${k.row}`);
  await door("arsenal:pad", { pad: 1, vel: 0, on: false }); await step(30);
  frames.colour = await shot(join(outDir, "kick-3-colour.png"));
  await door("arsenal:pad", { pad: 5, vel: 0, on: false }); await step(2);
  phase.frames = frames;
  const pageErrors = await ev("window.__stage.errors.slice(0, 5)");
  const errs = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length + pageErrors.length;
  check("kick: no exceptions or console errors", errs === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.filter((c) => /error/.test(c.type)).slice(0, 3), page: pageErrors });
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
  // every shot the demo programs (its sections' sequences, its phrases' steps, alternates and variants): since v2 the
  // set's library holds shots the demo never plays (formation hero views, the groove's, the new sequences')
  const programmed = new Set();
  for (const p of (RIG.show.demo && RIG.show.demo.plan) || []) for (const e of RIG.cameras.sequences[RIG.show.sections[p.section].camera] || []) programmed.add(e.shot);
  for (const m of JSON.stringify(RIG.phrases || {}).matchAll(/"(?:shot|alt)":"([A-Z0-9_]+)"/g)) programmed.add(m[1]);
  const allShots = [...programmed];
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
  check(`flash3m: ${summary.seconds} s of the programmed demo, crowd on, every shot the demo programs, every frame read back (${fw}x${fh}): zero final-limiter interventions, <= 3 flashes a second in all 18 windows, no red flash, no rest`,
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

// ===================================================================================================== PALETTES --
// 2026-10-28 (arsenal/web/palettes.js; research/in-flight/palettes-2026-10-28/DESIGN.md). Daniel: "I want us to have 30
// color palates that are high quality and what is used for driving the colors so it always looks careful and deliberate".
//   palettes   the contact sheet: every palette (or --pal-ids) on the Stage from one hero view (--pal-look, drop; --pal-shot,
//              FOH_WIDE), the palette landed at once through the page's door, two seconds of logic to settle (the wheels move
//              in black), then the frame; with --pal-kick also the same view with a colour kick lit on the rings and one on
//              the strand. PNGs to --sheet-dir (or the receipt folder), for the eye.
//   phonebar   the headless phone check: a phone's viewport (915 x 412, touch), ?pads=1 -- the PALETTE pad shows the palette
//              and, pressed by touch, the one queued; the colour strip wears the palette's lift colours; the page says so
//              only when the palette changes (never per frame), and the frames keep coming as fast with the bar as without.
async function phasePalettes({ ev, open, shot, phase, deadline }) {
  const dir = sheetDir || join(outDir, "palettes");
  mkdirSync(dir, { recursive: true });
  await open(`engine=http://127.0.0.1:${ENGINE_PORT}&vt=1&${BASE}`);
  await waitFor(() => ev("window.__stage.state().engine.open"), 15000, "the engine link");
  const ids = await ev("window.__stage.palettes()");
  const want = (opt["pal-ids"] ? opt["pal-ids"].split(",").map((s) => s.trim()) : ids).filter((x) => ids.includes(x));
  phase.dir = dir; phase.planned = want.length; phase.shots = [];
  const look = opt["pal-look"], camShot = opt["pal-shot"], kick = opt["pal-kick"];
  const STEP = String.raw`((id, look, camShot, u) => {
    const s = window.__stage, F = 1000 / 60;
    const posNow = () => s.grid.posAt(performance.now() + s.grid.presentLagMs);
    s.palette(id, { now: true });
    s.programmer.setLook(look, posNow(), { fade: 0 });
    s.setShot(camShot, u); s.resetLimiter();
    s.skipRender = true; for (let i = 0; i < 120; i++) window.__vt.step(F); s.skipRender = false;
    for (let i = 0; i < 2; i++) window.__vt.step(F);
    const st = s.state();
    return { palette: st.palette.id, name: st.palette.name, errors: st.errors.slice(), limiter: st.limiter.interventions };
  })`;
  const KICK = String.raw`((area) => {
    const s = window.__stage, F = 1000 / 60, P = s.programmer;
    const i = P.kick.cards.findIndex((c) => c.name === area);
    P.kick.deck.forceNext = i;
    window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: 5, vel: 0.8, on: true } }));
    s.skipRender = true; for (let k = 0; k < 20; k++) window.__vt.step(F); s.skipRender = false;
    for (let k = 0; k < 2; k++) window.__vt.step(F);
    const live = P.kick.list.filter((k) => k.held).map((k) => ({ area: k.card.name, colour: P.kick._hexOf(k) }));
    return live;
  })`;
  const RELEASE = String.raw`(() => { const s = window.__stage, F = 1000 / 60; window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad: 5, vel: 0, on: false } })); s.skipRender = true; for (let k = 0; k < 120; k++) window.__vt.step(F); s.skipRender = false; return true; })()`;
  for (const [n, id] of want.entries()) {
    if (Date.now() > deadline - 12000) break;
    const r = await ev(`${STEP}(${JSON.stringify(id)}, ${JSON.stringify(look)}, ${JSON.stringify(camShot)}, 0.5)`, 120000);
    const tag = `${String(ids.indexOf(id) + 1).padStart(2, "0")}-${id}`;
    const row = { id, name: r.name, landed: r.palette, errors: r.errors, file: await shot(join(dir, `${tag}.png`)) };
    if (kick) {
      for (const area of ["rings", "strand"]) {
        row[`kick_${area}`] = await ev(`${KICK}(${JSON.stringify(area)})`, 120000);
        row[`file_kick_${area}`] = await shot(join(dir, `${tag}-kick-${area}.png`));
        await ev(RELEASE, 120000);
      }
    }
    phase.shots.push(row);
    console.log(`palettes ${tag}: ${r.name}${kick ? ` (kicks: ${JSON.stringify(row.kick_rings)} ${JSON.stringify(row.kick_strand)})` : ""}`);
  }
  check(`palettes: every palette asked for landed and was drawn (${phase.shots.length} of ${want.length})`, phase.shots.length === want.length && phase.shots.every((x) => x.landed === x.id), phase.shots.map((x) => `${x.id}:${x.landed}`));
  check("palettes: no errors on the page while switching", phase.shots.every((x) => !x.errors.length) && !phase.exceptions.length, phase.shots.flatMap((x) => x.errors).slice(0, 4));
}

async function phasePhoneBar({ S, ev, open, phase, deadline }) {
  const PW = 915, PH = 412;
  await S("Emulation.setDeviceMetricsOverride", { width: PW, height: PH, deviceScaleFactor: 1, mobile: true });
  await S("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  const frames = async (n, render = true) => ev(`(() => { const s = window.__stage, F = 1000 / 60, t0 = window.__realNow(); s.skipRender = ${!render}; for (let i = 0; i < ${n}; i++) window.__vt.step(F); s.skipRender = false; return (window.__realNow() - t0) / ${n}; })()`, 170000);
  // the same page without the bar first: the frame time to beat
  await open(`demo=1&vt=1&pads=0&w=${PW}&h=${PH}&hud=0&quality=low&set=${opt.set}`);
  await frames(30);
  const msBare = await frames(90);
  await open(`demo=1&vt=1&pads=1&w=${PW}&h=${PH}&hud=0&quality=low&set=${opt.set}`);
  await waitFor(() => ev("!!document.querySelector('.tbs.right')"), 15000, "the kick strips");
  await ev(`(() => { window.__palEvents = 0; window.addEventListener("arsenal:palette", () => { window.__palEvents++; }); return true; })()`);
  const read = () => ev(`(() => { const b = [...document.querySelectorAll(".tb button")].find((x) => x.dataset.code === "KeyP");
    const st = document.querySelector(".tbs.right"), r = b.getBoundingClientRect(), rs = st.getBoundingClientRect(), s = window.__stage.state();
    return { label: b.textContent, small: b.querySelector("small").textContent, tinted: st.classList.contains("tinted"), k0: st.style.getPropertyValue("--k0"), k1: st.style.getPropertyValue("--k1"),
             rect: [r.left + r.width / 2, r.top + r.height / 2], strip: [rs.left + rs.width / 2, rs.top + rs.height / 2],
             palette: s.palette, events: window.__palEvents, pos: s.pos, bar: s.grid.barAnchor, errors: s.errors.slice(), ladder: window.__palette && window.__palette.ladder }; })()`);
  const touch = async (type, x, y, id = 1) => S("Input.dispatchTouchEvent", { type, touchPoints: type === "touchEnd" ? [] : [{ x, y, id }] });
  await frames(30);
  const msBar = await frames(90);
  const a = await read();
  phase.before = a; phase.ms = { bare: +msBare.toFixed(1), bar: +msBar.toFixed(1) };
  check("phonebar: the PALETTE pad shows the palette playing", a.small === a.palette.name, { small: a.small, palette: a.palette.name });
  check("phonebar: the colour strip wears the palette's two lift colours", a.tinted && a.k0.startsWith(a.ladder[0]) && a.k1.startsWith(a.ladder[1]), { k0: a.k0, k1: a.k1, ladder: a.ladder });
  // press the PALETTE pad with a finger: the next palette is queued for the next 16-bar line, and the pad says so
  await touch("touchStart", a.rect[0], a.rect[1]); await frames(2); await touch("touchEnd", a.rect[0], a.rect[1]);
  await frames(2);
  const b = await read();
  phase.queued = b;
  check("phonebar: a touch on the PALETTE pad queues the next palette for the next 16-bar line", !!b.palette.queued && b.palette.at > b.pos && Math.abs(((b.palette.at - b.bar) / 64) - Math.round((b.palette.at - b.bar) / 64)) < 1e-6 && b.small === `-> ${(await ev(`window.__palette.nextName`))}`, { small: b.small, palette: b.palette, pos: b.pos });
  // rendered frames with the bar: no event per frame, no slower than without the bar (a hang would show here)
  const msQueued = await frames(120);
  const c = await read();
  phase.ms.queued = +msQueued.toFixed(1);
  check("phonebar: the page announces the palette only when it changes (never per frame)", c.events === b.events && b.events - a.events === 1, { before: a.events, after_press: b.events, after_120_frames: c.events });
  check("phonebar: the frames keep coming as fast with the bar (no hang)", msQueued < Math.max(2 * msBare, msBare + 40) && msBar < Math.max(2 * msBare, msBare + 40), phase.ms);
  // a colour kick held on the right strip by a finger, slid, let go: the page keeps drawing
  await touch("touchStart", a.strip[0], a.strip[1], 2); await frames(10);
  await touch("touchMove", a.strip[0], a.strip[1] - 40, 2); await frames(10);
  const k = await ev("window.__stage.state().kick.live.map((x) => [x.kind, x.colour])");
  await touch("touchEnd", a.strip[0], a.strip[1] - 40, 2); await frames(10);
  phase.kick = k;
  check("phonebar: a finger on the colour strip kicks in the palette's lift colours", k.some(([kind, col]) => kind === "kick-colour" && a.ladder.includes(col)), k);
  // to the landing: the new palette shows, the pad and the strip follow it
  const toLand = Math.ceil(((b.palette.at - c.pos) + 1) * 24) + 4;
  if (Date.now() < deadline - 30000) {
    await frames(toLand, false); await frames(2);
    const d = await read();
    phase.landed = d;
    check("phonebar: on the 16-bar line the queued palette lands, and the pad and the strip follow it", d.palette.id === b.palette.queued && !d.palette.queued && d.small === d.palette.name && d.k0.startsWith(d.ladder[0]) && d.events === c.events + 1,
          { id: d.palette.id, small: d.small, k0: d.k0, ladder: d.ladder, events: d.events });
  } else check("phonebar: the landing was reached inside the burst", false, { deadline: "short" });
  check("phonebar: no exceptions or console errors", !phase.exceptions.length && !phase.console.some((x) => x.type === "error" || x.type === "log-error") && !(await ev("window.__stage.state().errors.length")), { exceptions: phase.exceptions.slice(0, 3), console: phase.console.filter((x) => x.type === "error" || x.type === "log-error").slice(0, 3) });
}

// CAMERA DISTANCE (2026-10-29, arsenal/web/stage/distance.js). Daniel: "can we think of a control scheme for camera distance
// so that i can trigger between closeup medium and far." Pre-registered bars, before the first run:
//   size     the rings (the subject of both shots) as the renderer's own camera projects them: the on-screen bounding box's
//            area (clipped to the frame) at CLOSE is at least 3x its area at FAR, and MEDIUM lies strictly between, on
//            HALO_LOCK (the long lens) and FOH_WIDE (the hero wide). The first two runs (receipts stage-20261029-130859 and
//            -131056) FAILED it, and the failure was the receipt's: it projected the ring cells' positions as if they were
//            world positions, but rig.cells.pos is in each element's own frame (a ring's cells sit round (0, 0, 0)). The
//            first run's numbers (2.87x and 3.84x) measure nothing; the second also tried the inner ring alone (a subject
//            chosen after the first run). Fixed: the cells are placed by the element's live matrix; the bar is the one
//            registered first, on all four rings; the inner ring's box rides along as detail;
//   dolly    the lens (hfov), the look point and the shot's exposure (EV) identical at the three sizes, the view's direction
//            within 0.5 degrees: a dolly, not a zoom;
//   picture  every still neither black nor blown (the load phase's bar: mean relative luminance 0.004..0.6), the camera
//            inside the venue and 1.5 m or more from the strand and the rings;
//   keys     (logic, every 60 fps frame) Q moves on the next frame and arrives on its planned beat line (+-1 frame); Q again
//            hands back to the director's pose exactly on a beat line two or more beats on; Shift+E cuts on a beat line
//            (+-1 frame) with nothing moving before it; Esc hands back; the F8 fader (CC 112 through the engine's ctl event)
//            does nothing until it crosses the live value, then drives the distance with no jump;
//   high     (the review's F1, 2026-10-29) the high shots at FAR, where the lens used to rise into the rigging grid and
//            render black: TOPDOWN_DESCEND u 0.2, HIGH_REAR_CRANE u 0.83, ORRERY_HIGH u 0.39, HALO_ORBIT u 0.73,
//            TOPDOWN_GODVIEW, ROOF_ESTABLISH, DIVE_FROM_ROOF u 0.1 -- each still neither black nor blown and the lens inside
//            the shot's own band of the room (1 m or more under the grid's beams);
//   ride     (F2) a moving shot played by hand through its move at a held stop (CRANE_RISE_REVEAL at FAR, STRAND_FLYTHROUGH
//            at CLOSE), every 60 fps frame on the live rig: the size never changes faster than e^4.5 a second nor
//            accelerates past LOG_ACCEL_MAX (outside a cut), the 1.5 m rule every frame (the frames where the director's
//            own camera is inside 1.5 m -- the flythrough's end -- are judged as: never nearer than his own camera);
//   spacing  (F6) a C-key shot then Shift+E at once: the distance cut lands 2 beats or more after the C cut, and is in the
//            director's own cut log (why "distance") on the frame it is drawn;
//   phone    at 667 x 375, 740 x 360, 780 x 360 (narrow phones: the bar wraps to two rows there, the review's F5), 832 x 384
//            and 915 x 412 (touch): no pad of the bar over either kick strip, the CLOSE . MID . FAR pads each at least 44 x 44
//            CSS px; a tap on MID lights it and the camera's distance goes manual MEDIUM;
//   no exceptions or console errors.
async function phaseDistance({ S, ev, open, shot, phase, deadline }) {
  await open(`demo=1&vt=1&${BASE}`);
  await ev(PAGE_PROBE);
  const renderer = await ev("window.__probe.renderer()");
  phase.renderer = renderer;
  check(opt.gpu ? "distance: the renderer is the GPU (--gpu)" : "distance: the renderer is SwiftShader (no hardware)", judgeFor(opt.gpu)(renderer).ok, renderer);
  await ev(`(() => { for (let i = 0; i < 120; i++) window.__vt.step(${F}); window.__stage.show.update = () => []; return true; })()`);
  // what the renderer's camera makes of the rings, the pose, the clearance, and the picture: read in the frame's own task
  const READ = String.raw`(() => {
    const s = window.__stage, R = s.renderer, cam = R.camera, rig = s.rig, C = rig.cells, gl = R.gl;
    const v = cam.position.clone();
    const ringEls = rig.elements.filter((e) => e.id === "ring");
    const inner = ringEls.reduce((a, e) => (e.params.diameter < a.params.diameter ? e : a), ringEls[0]);
    // the on-screen box of the cells passing keep(element): clipped to the frame, as a share of it
    // cells.pos are in each element's own frame: placed in the world by the element's live matrix (the rings' formation
    // layer when it moves them, else the home pose)
    const Rg = window.__distModel.R, mats = new Map(), wpt = [0, 0, 0], lpt = [0, 0, 0];
    const matOf = (ei) => { if (!mats.has(ei)) mats.set(ei, s.rings.live && s.rings.emOf ? s.rings.emOf(ei) : Rg.elementMatrix(rig.elements[ei])); return mats.get(ei); };
    const box = (keep) => {
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, n = 0, on = 0;
      for (let i = 0; i < C.n; i++) {
        const e = rig.elements[C.element[i]];
        if (!e || !keep(e)) continue;
        lpt[0] = C.pos[i * 3]; lpt[1] = C.pos[i * 3 + 1]; lpt[2] = C.pos[i * 3 + 2];
        Rg.transformPoint(matOf(C.element[i]), lpt, wpt);
        v.set(wpt[0], wpt[1], wpt[2]).project(cam);
        if (v.z < -1 || v.z > 1) continue;
        n++; if (Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1) on++;
        if (v.x < x0) x0 = v.x; if (v.x > x1) x1 = v.x; if (v.y < y0) y0 = v.y; if (v.y > y1) y1 = v.y;
      }
      const cx0 = Math.max(-1, x0), cx1 = Math.min(1, x1), cy0 = Math.max(-1, y0), cy1 = Math.min(1, y1);
      const area = cx1 > cx0 && cy1 > cy0 ? ((cx1 - cx0) * (cy1 - cy0)) / 4 : 0;
      return { cells: n, on_screen: on, bbox_ndc: [x0, y0, x1, y1].map((x) => +x.toFixed(3)), area: +area.toFixed(4) };
    };
    const w = R.w, h = R.h, buf = new Uint8Array(w * h * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    const lin = (c) => { const x = c / 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    const LUT = Array.from({ length: 256 }, (_, i) => lin(i));
    let sum = 0, black = 0;
    const hist = new Uint32Array(256);
    for (let i = 0; i < buf.length; i += 4) {
      const L = 0.2126 * LUT[buf[i]] + 0.7152 * LUT[buf[i + 1]] + 0.0722 * LUT[buf[i + 2]];
      sum += L; if (Math.max(buf[i], buf[i + 1], buf[i + 2]) <= 2) black++;
      hist[Math.min(255, Math.round(Math.sqrt(L) * 255))]++;
    }
    const N = w * h; let acc = 0, p50 = 0, p95 = 0;
    for (let k = 0; k < 256; k++) { acc += hist[k]; if (!p50 && acc >= N * 0.5) p50 = (k / 255) ** 2; if (!p95 && acc >= N * 0.95) { p95 = (k / 255) ** 2; break; } }
    const P = s.director.pose, M = window.__distModel;
    const clear = Math.min(M.C.clearanceToStrand(P.pos, s.strand.poses, M.m.z), M.C.clearanceToRings(P.pos, M.m.rings));
    const st = s.camDist.status(s.director.shots[P.shot]);
    return { shot: P.shot, pos: P.pos.slice(), look: P.look.slice(), hfov: P.hfov, ev: P.ev, clear, inside: s.camDist.room.inside(P.pos, s.camDist.last.mount),
             inner: box((e) => e === inner), rings: box((e) => e.id === "ring"),
             luminance: { mean: +(sum / N).toFixed(4), p50: +p50.toFixed(5), p95: +p95.toFixed(4), true_black_share: +(black / N).toFixed(4) },
             distance: { mode: st.mode, stop: st.stop, k: st.k, clamp: st.clamp } };
  })()`;
  await ev(`(async () => { const C = await import("/web/stage/camera.js"), R = await import("/web/stage/rig.js"); window.__distModel = { C, R, m: C.cameraModel(window.__stage.rig) }; return true; })()`);
  const stills = {};
  for (const id of ["HALO_LOCK", "FOH_WIDE"]) {
    stills[id] = {};
    for (const stop of ["close", "medium", "far"]) {
      // 24 frames = one beat at 150 BPM between stills: the three sizes are drawn at the same beat phase
      await ev(`(() => { const s = window.__stage; s.setShot("${id}", 0.5); s.distance("${stop}", { now: true }); for (let i = 0; i < 23; i++) window.__vt.step(${F}); return true; })()`);
      const r = await ev(`(() => { window.__vt.step(${F}); return ${READ}; })()`);
      r.png = await shot(join(outDir, `distance-${id.toLowerCase()}-${stop}.png`));
      stills[id][stop] = r;
    }
  }
  phase.stills = stills;
  const DEG = 180 / Math.PI;
  const dirOf = (r) => { const d = r.look.map((x, i) => x - r.pos[i]), l = Math.hypot(...d); return d.map((x) => x / l); };
  for (const id of Object.keys(stills)) {
    const { close: c, medium: m, far: f } = stills[id];
    check(`distance: ${id} -- the rings' on-screen box at CLOSE is at least 3x its area at FAR, MEDIUM between`,
          c.rings.area >= 3 * f.rings.area && f.rings.area < m.rings.area && m.rings.area < c.rings.area && f.rings.area > 0,
          { close: c.rings.area, medium: m.rings.area, far: f.rings.area, ratio: +(c.rings.area / Math.max(1e-9, f.rings.area)).toFixed(2),
            inner_ring: { close: c.inner.area, medium: m.inner.area, far: f.inner.area, ratio: +(c.inner.area / Math.max(1e-9, f.inner.area)).toFixed(2) },
            k: [c.distance.k, m.distance.k, f.distance.k], clamps: [c.distance.clamp, m.distance.clamp, f.distance.clamp] });
    const ang = Math.max(...[m, f].map((r) => Math.acos(Math.min(1, dirOf(r).reduce((s, x, i) => s + x * dirOf(c)[i], 0))) * DEG));
    check(`distance: ${id} -- a dolly, not a zoom (the same lens, look point and EV; the view's direction within 0.5 degrees)`,
          c.hfov === m.hfov && m.hfov === f.hfov && c.ev === m.ev && m.ev === f.ev && [m, f].every((r) => r.look.every((x, i) => Math.abs(x - c.look[i]) < 0.05)) && ang <= 0.5,
          { hfov: [c.hfov, m.hfov, f.hfov], ev: [c.ev, m.ev, f.ev], degrees: +ang.toFixed(3), metres_to_look: [c, m, f].map((r) => +Math.hypot(...r.pos.map((x, i) => x - r.look[i])).toFixed(1)) });
    check(`distance: ${id} -- every still neither black nor blown, the lens inside the venue and 1.5 m from the strand and rings`,
          [c, m, f].every((r) => r.luminance.mean > 0.004 && r.luminance.mean < 0.6 && r.inside && r.clear >= 1.5),
          [c, m, f].map((r) => ({ mean: r.luminance.mean, p50: r.luminance.p50, true_black: r.luminance.true_black_share, clear_m: +r.clear.toFixed(2), inside: r.inside })));
  }
  // F1: the high shots at FAR (the lens used to rise into the rigging grid there and render black)
  const high = {};
  for (const [id, u] of [["TOPDOWN_DESCEND", 0.2], ["HIGH_REAR_CRANE", 0.83], ["ORRERY_HIGH", 0.39], ["HALO_ORBIT", 0.73], ["TOPDOWN_GODVIEW", 0.5], ["ROOF_ESTABLISH", 0.5], ["DIVE_FROM_ROOF", 0.1]]) {
    const has = await ev(`!!window.__stage.director.shots["${id}"]`);
    if (!has) continue;
    await ev(`(() => { const s = window.__stage; s.setShot("${id}", ${u}); s.distance("far", { now: true }); for (let i = 0; i < 23; i++) window.__vt.step(${F}); return true; })()`);
    const r = await ev(`(() => { window.__vt.step(${F}); return ${READ}; })()`);
    r.png = await shot(join(outDir, `distance-high-${id.toLowerCase()}-far.png`));
    r.mount = await ev("window.__stage.camDist.last.mount.slice()");
    high[id] = r;
  }
  phase.high = high;
  check("distance: the high shots at FAR -- neither black nor blown, the lens in the shot's own band of the room (1 m or more under the rigging grid)",
        Object.keys(high).length >= 5 && Object.values(high).every((r) => r.luminance.mean > 0.004 && r.luminance.mean < 0.6 && r.inside && r.clear >= 1.5),
        Object.fromEntries(Object.entries(high).map(([id, r]) => [id, { mean: r.luminance.mean, p95: r.luminance.p95, true_black: r.luminance.true_black_share, y: +r.pos[1].toFixed(2), director_y: +r.mount[1].toFixed(2), inside: r.inside, k: r.distance.k, clamp: r.distance.clamp }])));
  // the controls, logic only (every 60 fps frame): the keys as the keyboard sends them, the fader as the engine does
  await ev("window.__stage.skipRender = true");
  // F2: a moving shot played by hand through its move at a held stop, every frame on the live rig
  const RIDE = String.raw`((id, stop) => {
    const s = window.__stage, D = s.camDist, M = window.__distModel, out = [];
    s.playShot(id); s.distance(stop, { now: true });
    const beats = (s.director.shots[id].bars ?? 4) * 4, n = Math.round(beats * 60 / s.grid.bpm * 60) - 3;   // (not into its loop)
    for (let i = 0; i < n; i++) {
      window.__vt.step(1000 / 60);
      const P = s.director.pose, cl = (q) => Math.min(M.C.clearanceToStrand(q, s.strand.poses, M.m.z), M.C.clearanceToRings(q, M.m.rings));
      // own: the director's own camera this frame (where it is in the rig, the rule is his guard's, never the layer's)
      out.push({ lam: D.last.lam, cut: !!P.distCut || !!P.cut, c: cl(P.pos), own: cl(D.last.mount), u: P.u });
    }
    let d1 = 0, d2 = 0, cuts = 0, clear = Infinity, own_in_rig = 0, worse = 0, vsOwn = Infinity, where = null, a = null, b = null;
    for (const r of out) {
      // (1 cm: a camera within a hair of his pose -- k 1.001 -- is his pose for this rule)
      if (r.own < 1.5) { own_in_rig++; if (r.c - r.own < vsOwn) { vsOwn = r.c - r.own; where = r; } if (r.c < r.own - 0.01) worse++; a = b = null; continue; }
      if (r.lam !== 0 && r.c < clear) clear = r.c;
      if (r.cut) { cuts++; a = b = null; continue; }
      if (a !== null) d1 = Math.max(d1, Math.abs(r.lam - a));
      if (b !== null) d2 = Math.max(d2, Math.abs(r.lam - 2 * a + b));
      b = a; a = r.lam;
    }
    return { id, stop, frames: out.length, d1, d2, cuts, clear, own_in_rig, worse_than_own: worse, min_vs_own_m: vsOwn, vs_own_frame: where && { ...where, i: out.indexOf(where), prev: out[out.indexOf(where) - 1], next: out[out.indexOf(where) + 1] }, escapes: D.escapes, lam_range: [Math.min(...out.map((r) => r.lam)), Math.max(...out.map((r) => r.lam))] };
  })`;
  const rides = [];
  for (const [id, stop] of [["CRANE_RISE_REVEAL", "far"], ["STRAND_FLYTHROUGH", "close"]]) rides.push(await ev(`${RIDE}("${id}", "${stop}")`));
  await ev(`(() => { const s = window.__stage; s.distance("auto", { now: true }); s.clearShot(); return true; })()`);
  phase.rides = rides;
  check("distance: a held stop through a moving shot (60 fps, the live rig) -- no step past e^4.5 a second, no jolt, the 1.5 m rule every frame (never nearer the rig than the director's own camera where his own path enters it)",
        rides.every((r) => r.d1 <= 4.5 / 60 + 1e-6 && r.d2 <= 25 / 3600 + 1e-6 && r.clear >= 1.5 && r.worse_than_own === 0), rides);
  const KEYS = String.raw`((code, shift, frames) => {
    const s = window.__stage, D = s.camDist, out = [];
    const pos = () => s.grid.posAt(performance.now() + s.grid.presentLagMs);
    const dist = () => { const p = s.director.pose; return Math.hypot(p.pos[0] - p.look[0], p.pos[1] - p.look[1], p.pos[2] - p.look[2]); };
    const before = { pos: pos(), d: dist(), k: D.last.k };
    if (code) { window.dispatchEvent(new KeyboardEvent("keydown", { code, key: code.slice(-1).toLowerCase(), shiftKey: shift })); window.dispatchEvent(new KeyboardEvent("keyup", { code, key: code.slice(-1).toLowerCase(), shiftKey: shift })); }
    const move = D.moves.at(-1) || null;
    for (let i = 0; i < frames; i++) { window.__vt.step(1000 / 60); out.push({ pos: pos(), d: dist(), k: D.last.k, w: D.w.x, cut: !!s.director.pose.distCut }); }
    return { before, move: move && { ...move }, frames: out, status: D.status(s.director.shots[s.director.pose.shot]) };
  })`;
  await ev(`(() => { const s = window.__stage; s.setShot("HALO_LOCK", 0.5); s.distance("auto", { now: true }); for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`);
  const onFrame = (p, at) => Math.abs(p - at) * 24 <= 1.01;
  const q = await ev(`${KEYS}("KeyQ", false, 90)`);
  const qLand = q.frames.find((r) => r.pos >= q.move.landAt - 1e-6);
  const settled = q.frames.at(-1).d;
  const firstAt = q.frames.findIndex((r) => Math.abs(r.d - settled) < 1e-6);
  phase.q = { move: q.move, before: q.before, land_frame: qLand, first_settled: q.frames[firstAt] };
  check("distance: Q moves the camera on the next frame and arrives on its planned beat line (+-1 frame)",
        q.move && q.move.stop === "close" && q.frames[0].d < q.before.d - 1e-6 && q.move.landAt === Math.round(q.move.landAt) && firstAt >= 0 && onFrame(q.frames[firstAt].pos, q.move.landAt),
        { press_pos: +q.before.pos.toFixed(3), land_at: q.move && q.move.landAt, settled_at: firstAt >= 0 ? +q.frames[firstAt].pos.toFixed(3) : null, d: [+q.before.d.toFixed(1), +settled.toFixed(1)] });
  const qq = await ev(`${KEYS}("KeyQ", false, 110)`);
  const back = qq.frames.find((r) => r.pos >= qq.move.landAt - 1e-6);
  const backFirst = qq.frames.findIndex((r) => r.k === 1 && r.w === 0);
  check("distance: Q again hands back to the director: his pose exactly, on a beat line two or more beats on (+-1 frame)",
        qq.move.kind === "handback" && qq.move.landAt - qq.before.pos >= 2 - 1e-6 && back && back.k === 1 && backFirst >= 0 && onFrame(qq.frames[backFirst].pos, qq.move.landAt) && qq.status.mode === "auto",
        { press_pos: +qq.before.pos.toFixed(3), land_at: qq.move.landAt, back_at: backFirst >= 0 ? +qq.frames[backFirst].pos.toFixed(3) : null, mode: qq.status.mode });
  const e = await ev(`${KEYS}("KeyE", true, 72)`);
  const cutI = e.frames.findIndex((r) => r.cut);
  check("distance: Shift+E is a clean cut on a beat line (+-1 frame), nothing moving before it",
        e.move.kind === "cut" && cutI >= 0 && onFrame(e.frames[cutI].pos, Math.round(e.frames[cutI].pos)) && e.frames.slice(0, cutI).every((r) => r.k === 1) && e.frames[cutI].k > 1,
        { press_pos: +e.before.pos.toFixed(3), cut_at: cutI >= 0 ? +e.frames[cutI].pos.toFixed(3) : null, planned: e.move.landAt, k_after: cutI >= 0 ? e.frames[cutI].k : null, clamp: e.status.clamp });
  const esc = await ev(`${KEYS}("Escape", false, 110)`);
  check("distance: Esc hands distance back to the director (auto, his pose exactly at the end)",
        esc.status.mode === "auto" && esc.frames.at(-1).k === 1 && esc.frames.at(-1).w === 0, { mode: esc.status.mode, k: esc.frames.at(-1).k });
  // F6: a C-key shot is a cut: Shift+E pressed right after it lands 2 beats or more later, and the distance cut is in the
  // director's own log on the frame it is drawn
  const cPos = await ev(`(() => { const s = window.__stage; window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyC", key: "c" })); window.dispatchEvent(new KeyboardEvent("keyup", { code: "KeyC", key: "c" })); window.__vt.step(1000 / 60); return s.director.lastCutPos; })()`);
  const ce = await ev(`${KEYS}("KeyE", true, 150)`);
  const ceI = ce.frames.findIndex((r) => r.cut);
  const ceLog = await ev(`window.__stage.director.cuts.slice(-3)`);
  phase.c_then_shift = { c_cut_at: cPos, planned: ce.move && ce.move.landAt, cut_at: ceI >= 0 ? ce.frames[ceI].pos : null, director_log: ceLog };
  check("distance: Shift+E right after a C-key shot lands 2 beats or more after it, on a beat line, and is in the director's cut log",
        ce.move && ce.move.kind === "cut" && ce.move.landAt - cPos >= 2 - 1e-6 && ceI >= 0 && onFrame(ce.frames[ceI].pos, ce.move.landAt) && ceLog.some((c) => c.why === "distance" && Math.abs(c.pos - ce.move.landAt) < 0.05),
        phase.c_then_shift);
  await ev(`(() => { const s = window.__stage; window.dispatchEvent(new KeyboardEvent("keydown", { code: "Escape", key: "Escape" })); window.dispatchEvent(new KeyboardEvent("keyup", { code: "Escape", key: "Escape" })); s.distance("auto", { now: true }); for (let i = 0; i < 30; i++) window.__vt.step(1000 / 60); return true; })()`);
  // the fader through the engine's ctl event: soft takeover
  const FAD = String.raw`((value, frames) => { const s = window.__stage, D = s.camDist, out = [];
    s.inject({ t: "ctl", id: "cc112", kind: "abs", value });
    for (let i = 0; i < frames; i++) { window.__vt.step(1000 / 60); out.push({ k: D.last.k, v: D.v.x }); }
    return { status: D.status(s.director.shots[s.director.pose.shot]), frames: out }; })`;
  await ev(`(() => { const s = window.__stage; s.setShot("HALO_LOCK", 0.5); for (let i = 0; i < 12; i++) window.__vt.step(${F}); return true; })()`);
  const f0 = await ev(`${FAD}(0.02, 6)`);
  const f1 = await ev(`${FAD}(${Math.min(0.99, (f0.status.vAuto ?? 0.6) + 0.05)}, 6)`);
  const f2 = await ev(`${FAD}(0.0, 60)`);
  const steps = f2.frames.map((r, i) => (i ? Math.abs(Math.log(r.k / f2.frames[i - 1].k)) : 0));
  phase.fader = { before: f0.status, caught: f1.status, end: f2.status, max_step_ln: +Math.max(...steps).toFixed(4) };
  check("distance: F8 (CC 112) does nothing until it crosses the live distance, then drives it toward CLOSE with no jump",
        f0.status.mode === "auto" && f0.frames.every((r) => r.k === 1) && f1.status.fader.caught && f1.status.source === "fader" && Math.abs(Math.log(f1.frames[0].k)) < 0.05
        && f2.frames.at(-1).k < 0.6 && Math.max(...steps) <= 4.5 / 60 + 1e-3, phase.fader);
  await ev(`(() => { const s = window.__stage; s.distance("auto", { now: true }); s.clearShot(); s.skipRender = false; return true; })()`);
  const errs = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length + (await ev("window.__stage.errors.length"));
  // the phone: the segment in the pad bar
  const phone = [];
  for (const [PW, PH] of [[667, 375], [740, 360], [780, 360], [832, 384], [915, 412]]) {
    await S("Emulation.setDeviceMetricsOverride", { width: PW, height: PH, deviceScaleFactor: 1, mobile: true });
    await S("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    await open(`demo=1&vt=1&pads=1&w=${PW}&h=${PH}&hud=0&quality=low&set=${opt.set}`);
    await waitFor(() => ev("!!document.querySelector('.tbs.right') && !!document.querySelector('.tb .seg')"), 15000, "the strips and the segment");
    await ev(`(() => { for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`);
    const g = await ev(`(() => { const r = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      const bar = document.querySelector(".tb"), seg = [...document.querySelectorAll(".tb .seg button")];
      const vis = [...bar.querySelectorAll("button")].filter((b) => b.offsetParent !== null);
      const tops = [...new Set(vis.map((b) => Math.round(b.getBoundingClientRect().top)))];
      return { bar: r(bar), rows: tops.length, seg: seg.map((b) => ({ label: b.textContent, rect: r(b) })), strips: [...document.querySelectorAll(".tbs")].map(r),
               pads: vis.map((b) => ({ label: b.textContent, rect: r(b) })) }; })()`);
    const ov = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
    const mid = g.seg.find((x) => x.label === "mid");
    const cx = (mid.rect[0] + mid.rect[2]) / 2, cy = (mid.rect[1] + mid.rect[3]) / 2;
    const under = await ev(`(() => { const el = document.elementFromPoint(${cx}, ${cy}); return el ? el.textContent : null; })()`);
    await S("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: cx, y: cy, id: 1 }] });
    await ev(`(() => { for (let i = 0; i < 2; i++) window.__vt.step(${F}); return true; })()`);
    await S("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await ev(`(() => { for (let i = 0; i < 4; i++) window.__vt.step(${F}); return true; })()`);
    const after = await ev(`(() => ({ status: window.__stage.camDist.status(), lit: [...document.querySelectorAll(".tb .seg button.lit")].map((b) => b.textContent) }))()`);
    await shot(join(outDir, `distance-phone-${PW}x${PH}.png`));
    phone.push({ viewport: [PW, PH], ...g, under, after });
    const over = g.pads.filter((x) => g.strips.some((st) => ov(x.rect, st))).map((x) => x.label);
    check(`distance: phone ${PW} x ${PH} -- no pad of the bar over a kick strip (${g.rows} row${g.rows > 1 ? "s" : ""}), CLOSE . MID . FAR 44 x 44 px or more; a tap on MID lights it and goes manual MEDIUM`,
          over.length === 0 && g.seg.length === 3 && g.seg.every((x) => x.rect[2] - x.rect[0] >= 44 - 0.5 && x.rect[3] - x.rect[1] >= 44 - 0.5)
          && under === "mid" && after.status.mode === "manual" && after.status.stop === "medium" && after.lit.length === 1 && after.lit[0] === "mid",
          { rows: g.rows, over, seg: g.seg.map((x) => [x.label, Math.round(x.rect[2] - x.rect[0]), Math.round(x.rect[3] - x.rect[1])]), strips: g.strips.map((x) => x.map(Math.round)), under, status: { mode: after.status.mode, stop: after.status.stop }, lit: after.lit });
  }
  phase.phone = phone;
  const errs2 = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length + (await ev("window.__stage.errors.length"));
  check("distance: no exceptions or console errors", errs === 0 && errs2 === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.filter((c) => /error/.test(c.type)).slice(0, 3) });
}

// ------------------------------------------------------------------------------------------- the chord phrasing --
// Daniel, 2026-10-29: "lets also land the chord phrasing."; 2026-10-28: "i mean like 8 7 6 5 4 then 456789".
async function phaseChords({ S, ev, open, shot, phase }) {
  const VK = (k) => (/^[0-9]$/.test(k) ? 48 + Number(k) : k.charCodeAt(0));
  const key = (k, down) => S("Input.dispatchKeyEvent", { type: down ? "rawKeyDown" : "keyUp", code: /^[0-9]$/.test(k) ? `Digit${k}` : `Key${k}`,
                                                         key: k.toLowerCase(), windowsVirtualKeyCode: VK(k), nativeVirtualKeyCode: VK(k) });
  // n frames drawn; per frame the cells (the verifier's 4 x 4), whether the limiter acted, the fade's level
  const rec = (n) => ev(`(() => { const s = window.__stage, out = [];
    for (let i = 0; i < ${n}; i++) { window.__vt.step(${F}); const c = window.__probe.cells(), g = s.renderer.info.gains, b = s.breath ? s.breath() : null;
      let l = 0, nn = 0; for (let q = 0; q < 16; q++) { l += c.L[q] * c.N[q]; nn += c.N[q]; }
      out.push({ L: c.L.map((v) => +v.toFixed(5)), R: c.R.map((v) => +v.toFixed(3)), N: c.N, mean: +(l / nn).toFixed(5), lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0,
                 level: b ? +b.level.toFixed(4) : 1 }); }
    return out; })()`, 170000);
  const punches = () => ev("window.__stage.programmer.kick.list.map((k) => k.punchFrom).filter((x) => Number.isFinite(x)).map((x) => +x.toFixed(4))");
  const kickPresses = () => ev("window.__stage.programmer.kick.presses");
  const segment = async (name, script) => {
    const lim0 = await ev("window.__stage.limiter.stats().interventions"), p0 = await punches();
    const frames = [], seen = new Set();
    for (const step of script) {
      if (typeof step === "number") frames.push(...(await rec(step)));
      else if (step.shot) await shot(join(outDir, `chords-${step.shot}.png`));
      else { await key(step.k, step.down); for (const x of await punches()) seen.add(x); }   // (a faded kick leaves the list)
    }
    const lim1 = await ev("window.__stage.limiter.stats().interventions");
    const fresh = [...seen].filter((x) => !p0.includes(x));
    const j = judgeFlashes(frames);
    return { name, frames: frames.length, limiter_interventions: lim1 - lim0, limited_frames: frames.reduce((s, f) => s + f.lim, 0),
             flashes_per_s: j.worst, red_flashes_per_s: j.worst_red, attacks: fresh.length, punch_from: fresh,
             mean: frames.map((f) => f.mean), level: frames.map((f) => f.level) };
  };
  const down = (k) => ({ k, down: true }), up = (k) => ({ k, down: false });
  // the chord: 1, then 5 two frames (33 ms) later, held half a second; the strum: 6 5 4 two frames apart
  const CHORD = [down("1"), 2, down("5"), 28, { shot: null }, up("1"), up("5"), 90];
  const STRUM = [down("6"), 2, down("5"), 2, down("4"), 26, { shot: null }, up("6"), up("5"), up("4"), 90];
  const runs = {};
  for (const g of ["0", "1"]) {
    await open(`demo=1&vt=1&${BASE}&grammar=${g}`);
    await ev(PAGE_PROBE);
    await S("Page.bringToFront");
    // into the break (bar 41: the demo presses no pads of its own there), logic only; then FOH_WIDE held still, drawn
    await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 41 + 6; i++) window.__vt.step(${F}); s.setShot("FOH_WIDE", 0.5); s.skipRender = false; for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`, 170000);
    const tag = g === "1" ? "grammar" : "singles";
    if (g === "0") await shot(join(outDir, "chords-0-before.png"));
    // a single is instant: key 1's kick exists on the key's own call, before any frame
    const k0 = await kickPresses();
    await key("1", true);
    const k1 = await kickPresses();
    await key("1", false);
    await rec(90);
    const chord = await segment("chord", CHORD.map((x) => (x && x.shot === null ? { shot: `1-chord-${tag}` } : x)));
    const strum = await segment("strum", STRUM.map((x) => (x && x.shot === null ? { shot: `2-strum-${tag}` } : x)));
    const st = await ev("window.__stage.state()");
    runs[tag] = { instant: k1 - k0, chord, strum, grammar: st.grammar };
    if (g === "1") {
      // Daniel's sweep: 6 5 4 3 2 1 (the third key takes over: a fade out), then back 2 3 4 5 6 inside its gap (a fade in)
      const SW = [];
      // (the bottom's still is taken inside the gap: a pause over 450 ms would end the sweep, and 2 would fire LASER)
      for (const k of ["6", "5", "4", "3", "2", "1"]) SW.push(down(k), 3, up(k), 8);
      SW.push({ shot: "3-sweep-bottom" });
      for (const k of ["2", "3", "4", "5", "6"]) SW.push(down(k), 3, up(k), 8);
      SW.push(60, { shot: "4-sweep-back" });
      // the explicit B: held, 9 down to 1 (no single fires), then 1 up to 9, let go
      const BB = [down("B"), 4];
      for (const k of ["9", "8", "7", "6", "5", "4", "3", "2", "1"]) BB.push(down(k), 3, up(k), 5);
      BB.push(40, { shot: "5-breath-bottom" });
      for (const k of ["2", "3", "4", "5", "6", "7", "8", "9"]) BB.push(down(k), 3, up(k), 5);
      BB.push(up("B"), 60, { shot: "6-breath-back" });
      const kp0 = await kickPresses(), hero0 = await ev("window.__stage.state().rings.hero.armed");
      runs.grammar.sweep = await segment("sweep", SW);
      const kp1 = await kickPresses();
      runs.grammar.breath = await segment("breath", BB);
      const kp2 = await kickPresses(), st2 = await ev("window.__stage.state()");
      runs.grammar.sweep_kicks = kp1 - kp0; runs.grammar.breath_kicks = kp2 - kp1;
      runs.grammar.hero_armed = { before: hero0, after: st2.rings.hero.armed, fired: st2.rings.hero.fired, morph: st2.rings.move, key: st2.rings.key };
      runs.grammar.final = st2.grammar;
      runs.grammar.errors = st2.errors;
    }
  }
  // the receipt keeps the paths short: the level per frame, the mean luminance per frame for the fades
  const A = runs.singles, B = runs.grammar;
  phase.runs = { singles: { instant: A.instant, chord: { ...A.chord, mean: undefined, level: undefined }, strum: { ...A.strum, mean: undefined, level: undefined } },
                 grammar: { instant: B.instant, chord: { ...B.chord, mean: undefined, level: undefined }, strum: { ...B.strum, mean: undefined, level: undefined },
                            sweep: B.sweep, breath: B.breath, sweep_kicks: B.sweep_kicks, breath_kicks: B.breath_kicks, hero: B.hero_armed,
                            counts: B.final.counts, ensemble: B.final.ensemble, gestures: B.final.gestures } };
  check("chords: a single is instant (key 1's kick is pressed on the key's own call, before any frame), with and without the grammar",
        A.instant === 1 && B.instant === 1, { singles: A.instant, grammar: B.instant });
  check("chords: the page heard real keystrokes as the keyboard source (key), and recognised a chord and a strum",
        !!(B.final.sources && B.final.sources.key) && B.final.gestures.some((x) => x.type === "reclassify" && x.kind === "chord") && B.final.gestures.some((x) => x.type === "reclassify" && x.kind === "strum"),
        { sources: Object.keys(B.final.sources || {}), reclassified: B.final.gestures.filter((x) => x.type === "reclassify").map((x) => x.kind) });
  check("chords: one attack per chord with the grammar (1 + 5: one punch shared), two as singles", B.chord.attacks === 1 && A.chord.attacks === 2,
        { grammar: B.chord.punch_from, singles: A.chord.punch_from });
  for (const seg of ["chord", "strum"]) {
    check(`chords: the ${seg} adds no flash -- the limiter's interventions and the verifier's flash count with protection on are no more than the same keys as singles`,
          B[seg].limiter_interventions <= A[seg].limiter_interventions && B[seg].flashes_per_s <= A[seg].flashes_per_s && B[seg].red_flashes_per_s <= A[seg].red_flashes_per_s,
          { grammar: { lim: B[seg].limiter_interventions, limited_frames: B[seg].limited_frames, flashes: B[seg].flashes_per_s, red: B[seg].red_flashes_per_s },
            singles: { lim: A[seg].limiter_interventions, limited_frames: A[seg].limited_frames, flashes: A[seg].flashes_per_s, red: A[seg].red_flashes_per_s } });
  }
  const lv = B.sweep.level, lo = Math.min(...lv);
  check("chords: the sweep fades out to 4/9 (6 and 5 fire their singles, 4 takes over; 3, 2, 1 step) and back to 1 (2 up to 6)",
        Math.abs(lo - 4 / 9) < 0.01 && lv[lv.length - 1] === 1 && B.sweep_kicks === 1, { min: lo, end: lv[lv.length - 1], kick_presses: B.sweep_kicks });
  const bl = B.breath.level, blo = Math.min(...bl);
  check("chords: B held is a fader from the first key: 9 to 1 is 1/9 (no single fires: no kick, no HERO), 1 to 9 is back to 1",
        Math.abs(blo - 1 / 9) < 0.01 && bl[bl.length - 1] === 1 && B.breath_kicks === 0 && B.hero_armed.after === B.hero_armed.before,
        { min: blo, end: bl[bl.length - 1], kick_presses: B.breath_kicks, hero: B.hero_armed });
  // the level ramps (never faster than a 1/9 step per 120 ms) and the frame follows it down
  let fastest = 0;
  for (const p of [lv, bl]) for (let i = 1; i < p.length; i++) fastest = Math.max(fastest, Math.abs(p[i] - p[i - 1]));
  check("chords: the fade is a ramp (at most a 1/9 step per 120 ms: 0.0154 a frame)", fastest <= (1 / 9) * (F / 120) + 1e-3, { fastest_per_frame: +fastest.toFixed(4) });
  const meanAt = (seg, i) => seg.mean[Math.max(0, Math.min(seg.mean.length - 1, i))];
  const iLo = bl.indexOf(blo);
  phase.fade_frame_mean = { breath_top: meanAt(B.breath, 0), breath_bottom: meanAt(B.breath, iLo + 20), breath_back: meanAt(B.breath, B.breath.mean.length - 1),
                            sweep_top: meanAt(B.sweep, 0), sweep_bottom: meanAt(B.sweep, lv.indexOf(lo) + 1) };
  check("chords: the picture follows the fade (B: the frame's mean luminance at the bottom under half of the top; the sweep, whose first two keys fired their singles: under 0.8 of the top once their kicks are let go)",
        phase.fade_frame_mean.breath_bottom < 0.5 * phase.fade_frame_mean.breath_top && phase.fade_frame_mean.sweep_bottom < 0.8 * phase.fade_frame_mean.sweep_top, phase.fade_frame_mean);
  phase.sweep_cancels = B.final.gestures.filter((x) => x.did.some((d) => /^\d: /.test(d))).map((x) => x.did.filter((d) => /^\d: /.test(d)));
  for (const seg of ["sweep", "breath"]) check(`chords: the ${seg} adds no flash (the verifier's count stays under 3 a second; red 0)`,
                                               B[seg].flashes_per_s < 3 && B[seg].red_flashes_per_s === 0, { flashes: B[seg].flashes_per_s, red: B[seg].red_flashes_per_s, lim: B[seg].limiter_interventions });
  // ---- the review's cases (2026-10-29): a chord never ADDS a punch (a refused one, a re-strike), a mash and a key inside
  // W is one attack, a lost key-up does not eat the next press. Each on a fresh page in the break, both modes, every kick
  // record read straight from kick.js (punchFrom: the beat position its punch counts from; -Infinity: none)
  const kickRecs = () => ev("window.__stage.programmer.kick.list.filter((k) => !k.dead).map((k) => ({ kind: k.kind, from: k.from, pf: Number.isFinite(k.punchFrom) ? k.punchFrom : null, presses: k.presses }))");
  const colourPf = async () => { const r = (await kickRecs()).filter((k) => k.kind === "kick-colour"); return r.length ? r[r.length - 1].pf : undefined; };
  const settleKicks = () => ev(`(() => { const s = window.__stage; s.skipRender = true; let i = 0;
    for (; i < 900 && s.programmer.kick.list.some((k) => !k.dead); i++) window.__vt.step(${F}); s.skipRender = false; window.__vt.step(${F}); return i; })()`, 170000);
  const review = {};
  for (const g of ["0", "1"]) {
    await open(`demo=1&vt=1&${BASE}&grammar=${g}`);
    await ev(PAGE_PROBE);
    await S("Page.bringToFront");
    await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 41 + 6; i++) window.__vt.step(${F}); s.setShot("FOH_WIDE", 0.5); s.skipRender = false; for (let i = 0; i < 30; i++) window.__vt.step(${F}); return true; })()`, 170000);
    const R = {}, newer = [];
    const watch = async () => { for (const k of await kickRecs()) if (k.pf !== null && k.pf > k.from + 1e-6) newer.push(k); };
    // 1. refused: 1 (granted), the governor's budget spent, 5 on the same call (a chord): 5's punch must stay refused
    await settleKicks();
    await key("1", true); await watch();
    await ev("(window.__stage.programmer.kick.headroom = 0, true)");
    const pfBefore = await colourPf();
    await key("5", true); await watch();
    R.refused = { colour_before: pfBefore ?? "none", colour_after: await colourPf() };
    await rec(20); await key("1", false); await key("5", false); await rec(10);
    // 2. re-strike: tap 5, then a third of a second later the chord 1 + 5 (5 still lit): 5 keeps its tap's punch
    await settleKicks();
    await key("5", true); await rec(3); await key("5", false); await rec(20);
    const pfTap = await colourPf();
    await key("1", true); await watch(); await rec(2); await key("5", true); await watch();
    R.restrike = { colour_tap: pfTap, colour_after_chord: await colourPf() };
    await rec(20); await key("1", false); await key("5", false); await rec(10);
    // 3. the mash 4 5 6 (one call each: a strum) and 1 a frame later: one attack with the grammar
    await settleKicks();
    const m0 = await ev("window.__stage.programmer.kick.list.filter((k) => !k.dead).length");
    const seen = new Set();
    for (const k of ["4", "5", "6"]) await key(k, true);
    await rec(1); await key("1", true); await watch();
    for (const k of await kickRecs()) if (k.pf !== null) seen.add(+k.pf.toFixed(4));
    R.mash = { kicks_alive_before: m0, attacks: seen.size, punch_from: [...seen] };
    await rec(20); for (const k of ["4", "5", "6", "1"]) await key(k, false); await rec(10);
    // 4. a lost key-up: 1 down, and down again with no up between (not the OS's auto-repeat): two presses, not one
    await settleKicks();
    const p0 = await kickPresses();
    await key("1", true); await rec(3); await key("1", true);
    R.lost_keyup = { presses: (await kickPresses()) - p0 };
    await rec(5); await key("1", false); await rec(10);
    // 5. eighths up the row at full level (1 2 3 4 5, 12 frames = 200 ms apart): nothing to fade in, so every key fires
    await settleKicks();
    const e0 = await kickPresses();
    for (const k of ["1", "2", "3", "4", "5"]) { await key(k, true); await rec(3); await key(k, false); await rec(9); }
    R.eighths_up = { kick_presses: (await kickPresses()) - e0, breath: g === "1" ? await ev("window.__stage.breath().target") : 1 };
    await rec(10);
    // 6. the fade's chip: B held, 9 down to 5 -- with the HUD hidden the corner says so; Esc hands it back and it goes
    if (g === "1") {
      const chip = () => ev("(() => { const c = document.getElementById('breath-chip'); return c ? { shown: !c.hidden, text: c.textContent } : null; })()");
      await key("B", true); await rec(2);
      for (const k of ["9", "8", "7", "6", "5"]) { await key(k, true); await rec(2); await key(k, false); await rec(4); }
      await key("B", false); await rec(60);
      R.chip_low = await chip();
      await S("Input.dispatchKeyEvent", { type: "rawKeyDown", code: "Escape", key: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await S("Input.dispatchKeyEvent", { type: "keyUp", code: "Escape", key: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await ev(`(() => { for (let i = 0; i < 120; i++) window.__vt.step(${F}); return true; })()`, 170000);
      R.chip_back = await chip();
      R.hud_hidden = await ev("document.getElementById('hud').classList.contains('hidden') || getComputedStyle(document.getElementById('hud')).display === 'none'");
    }
    R.newer_than_press = newer.slice(0, 4); R.newer_count = newer.length;
    review[g === "1" ? "grammar" : "singles"] = R;
  }
  phase.review = review;
  const Ag = review.singles, Bg = review.grammar;
  const expectRefused = (r) => r.colour_after === (r.colour_before === "none" ? null : r.colour_before);
  check("chords (review F1): a punch the flash governor refused stays refused inside a chord (5 after 1, budget spent)",
        expectRefused(Bg.refused) && expectRefused(Ag.refused), { grammar: Bg.refused, singles: Ag.refused });
  check("chords (review F1): a re-strike inside a chord keeps its tap's punch (never a fresh one)",
        Bg.restrike.colour_after_chord === Bg.restrike.colour_tap && Ag.restrike.colour_after_chord === Ag.restrike.colour_tap, { grammar: Bg.restrike, singles: Ag.restrike });
  check("chords (review F1/F5): no kick's punch is ever newer than its own first press (kick.js grants it only at the press)",
        Bg.newer_count === 0 && Ag.newer_count === 0, { grammar: Bg.newer_than_press, singles: Ag.newer_than_press });
  check("chords (review F2): the mash 4 5 6 and 1 a frame later is one attack with the grammar (two as singles)",
        Bg.mash.attacks === 1 && Ag.mash.attacks === 2, { grammar: Bg.mash, singles: Ag.mash });
  check("chords (review F7): a key-down whose key-up was lost is a new press (two presses), with and without the grammar",
        Bg.lost_keyup.presses === 2 && Ag.lost_keyup.presses === 2, { grammar: Bg.lost_keyup, singles: Ag.lost_keyup });
  check("chords (review F4): eighths up the row at full level fire every key (kicks 1 and 5 both press; nothing to fade in)",
        Bg.eighths_up.kick_presses === 2 && Ag.eighths_up.kick_presses === 2 && Bg.eighths_up.breath === 1, { grammar: Bg.eighths_up, singles: Ag.eighths_up });
  check("chords (review F3): a latched fade shows in the corner with the HUD hidden, and the chip goes when Esc hands it back",
        !!(Bg.chip_low && Bg.chip_low.shown && /breath \d+ %/.test(Bg.chip_low.text)) && !!(Bg.chip_back && !Bg.chip_back.shown), { low: Bg.chip_low, back: Bg.chip_back, hud_hidden: Bg.hud_hidden });
  const errs = phase.exceptions.length + phase.console.filter((c) => c.type === "error" || c.type === "log-error").length + (B.errors || []).length;
  check("chords: no exceptions or console errors", errs === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.filter((c) => /error/.test(c.type)).slice(0, 3), page: (B.errors || []).slice(0, 3) });
}

// ------------------------------------------------------------------------------------------------------ main --
if (opt.stitch) {
  // no browser, no lock: judge stored chunks
  try { stitchKickstorm(opt.stitch.split(",").map((s) => s.trim()).filter(Boolean)); }
  catch (e) { check("stitch: the chunks load", false, String(e && e.message || e)); }
  const failedS = Object.entries(report.checks).filter(([, v]) => !v.ok).map(([k]) => k);
  report.verdict = failedS.length ? "fail" : "pass"; report.failed = failedS; report.finished_at = new Date().toISOString();
  writeFileSync(join(outDir, "receipt.json"), JSON.stringify(report, null, 2));
  console.log(`receipt: ${join(outDir, "receipt.json")}`);
  console.log(`verdict: ${report.verdict}${failedS.length ? ` (${failedS.join("; ")})` : ""}`);
  process.exit(failedS.length ? 1 : 0);
}
try {
  PORT = await listen(web, PORT);
  ENGINE_PORT = await listen(engine, ENGINE_PORT);
  report.ports = { web: PORT, engine: ENGINE_PORT };
  const table = { load: phaseLoad, clock: phaseClock, camera: phaseCamera, engine: phaseEngine, cost: phaseCost, flash: phaseFlash, storm: phaseStorm, sheet: phaseSheet, probe: phaseProbe, diag: phaseDiag,
                  phrase: phasePhrase, "pic-debug": phasePicDebug, "pic-levels": phasePicLevels, "pic-rush": phasePicRush, "pic-ring": phasePicRing, "pic-handoff": phasePicHandoff, "sheet-phrase": phaseSheetPhrase,
                  orrery: phaseOrrery, spiral: phaseSpiral, kick: phaseKick, kickstorm: phaseKickStorm, kickpix: phaseKickPix, kickrepeat: phaseKickRepeat,
                  palettes: phasePalettes, phonebar: phasePhoneBar, distance: phaseDistance, chords: phaseChords };
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
