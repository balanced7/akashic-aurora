// VJ Rig receipt: load /web/vj.html in a private headless Chrome forced onto SwiftShader (the CPU: this host's AMD driver
// has a crash history, and no frame here is ever drawn on the GPU), play it through the keyboard fallback and a fake
// engine, and check what a viewer would be owed.
//
//   node arsenal/lanes/vj_verify.mjs [--port 8931] [--engine-port 8932] [--dwell 1500] [--out <dir>] [--keep-open]
//
// It serves arsenal/web itself on a test-band port (8900-8999; never 8793, Daniel's server) and runs a fake keylab-vj
// engine (Server-Sent Events at /api/events, POST /api/pads) on another, so it needs nothing else running. Chrome starts
// with the shader lab's SwiftShader flags (arsenal/shaders/headless.mjs) under the house GPU lock (arsenal/GPU-LOCK.md),
// and the receipt refuses to judge anything unless the page's WebGL2 renderer names SwiftShader and no hardware.
//
// Checks: every set compiles and renders a non-black picture; frames advance; keyboard pads trigger the mapped effects
// with Shift as hard velocity, held pads sustain and release; Q/W/E/R dampen, choke, kill (and revive) and switch sets;
// the flash gate holds (ten flash requests in one second give at most three flashes, by the gate's own log AND by the
// measured relative luminance of the rendered frames); the engine contract works end to end (hello, beats, chords, a pad,
// controls, learn-on-touch, and pad colours posted back at no more than ten a second); an engine whose hello says it has
// no LEDs is never posted to, a refused post stops posting until the engine's next hello, and a dropped connection
// clears the old engine's status (the fake engine has a no-LEDs mode for this); chordsense's key, roman numeral and
// tension (vj --chords sense) show in the HUD, the engine's tension feeds the strip in place of the page's own estimate,
// a key change accents without a flash, and an engine without them leaves the page as it was; the pedal star finds a note struck over
// and over while the bass walks under it; the showcase tour follows an engine that plays beats instead of starting
// the page's demo over it; no page exceptions or console errors.
// Writes state/arsenal/receipts/vj-<stamp>/receipt.json and the screenshots beside it; exits 1 if the verdict fails.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { LOCK_DIR, acquireGpuLock } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    port: { type: "string", default: "8931" },
    "engine-port": { type: "string", default: "8932" },
    dwell: { type: "string", default: "1500" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    width: { type: "string", default: "960" },
    height: { type: "string", default: "540" },
    "gpu-wait-min": { type: "string", default: "2" },
    // the house lock lives in the main checkout's state/; a run from a git worktree names it here
    "lock-dir": { type: "string", default: LOCK_DIR },
    "play-port": { type: "string", default: "8933" },
    "no-play": { type: "boolean", default: false },
    // the real engine (py -m arsenal.keylab vj --replay-audio demo --no-leds --no-midi) for the chordsense phase
    "real-engine-port": { type: "string", default: "8934" },
    "no-real-engine": { type: "boolean", default: false },
  },
});
let PORT = Number(opt.port), ENGINE_PORT = Number(opt["engine-port"]), PLAY_PORT = Number(opt["play-port"]);
let REAL_PORT = Number(opt["real-engine-port"]);
let playServer = null, realEngine = null;
for (const p of [PORT, ENGINE_PORT, PLAY_PORT, REAL_PORT]) {
  if (p === 8793 || !(p >= 8900 && p <= 8999)) {
    console.log(`ERROR port ${p}: the receipt uses the test band 8900-8999 only (8793 is Daniel's server)`);
    process.exit(2);
  }
}
const dwellMs = Number(opt.dwell);
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const outDir = join(opt.out, `vj-${stamp}`);
mkdirSync(outDir, { recursive: true });
const profile = join(tmpdir(), `arsenal-vj-verify-${stamp}`);

const report = {
  api: "arsenal.receipt/v0", lane: "vj", title: "VJ rig in headless Chrome on SwiftShader",
  started_at: new Date().toISOString(), page: `http://127.0.0.1:${PORT}/web/vj.html`, engine: `http://127.0.0.1:${ENGINE_PORT}`,
  viewport: { width: Number(opt.width), height: Number(opt.height) }, chrome: null, webgl: null, renderer_check: null,
  sets: [], pads: {}, controls: {}, flash: {}, engine_contract: {}, pedal: {}, frames: {}, console: [], exceptions: [],
  page_errors: [], screenshots: [],
  not_measured: [
    "the real GPU: every frame here is drawn by SwiftShader on the CPU, so frame rate and timing say nothing about the live rig",
    "the KeyLab itself and the real keylab-vj engine: a fake engine speaks the event contract instead",
    "how each set looks to a person in motion: the screenshots are single frames for that",
    "photosensitivity beyond the three-flashes rule: the red-flash rule and area thresholds are reasoned in the code, not measured",
  ],
};

// ------------------------------------------------------------------------------------------- the two servers --
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".json": "application/json", ".frag": "text/plain; charset=utf-8",
                ".glsl": "text/plain; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml" };
const web = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (url.pathname === "/favicon.ico") { res.writeHead(204); res.end(); return; }   // not a page fault worth a console error
  if (!url.pathname.startsWith("/web/")) { res.writeHead(404); res.end(); return; }
  const target = resolve(WEB, decodeURIComponent(url.pathname.slice(5)));
  if (!(target + sep).startsWith(WEB + sep) && target !== WEB) { res.writeHead(404); res.end(); return; }
  try {
    const body = readFileSync(target);
    res.writeHead(200, { "Content-Type": TYPES[extname(target).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
const sse = new Set();
const padPosts = [];
// the fake engine's pad LEDs, as the real engine answers POST /api/pads: "on" = 202 taken; "off" = 409, as `vj --no-leds`
// answers (its hello says leds false); "refuse" = 409 although its hello said leds true (the refusal path)
let ledsMode = "on";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
               "Access-Control-Allow-Headers": "Content-Type" };
const engineServer = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (req.method === "OPTIONS") { res.writeHead(204, CORS); res.end(); return; }
  if (url.pathname === "/api/events" && req.method === "GET") {
    res.writeHead(200, { ...CORS, "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
    res.write(": keylab-vj fake engine\n\n");
    sse.add(res);
    req.on("close", () => sse.delete(res));
    return;
  }
  if (url.pathname === "/api/pads" && req.method === "POST") {
    let body = "";
    req.on("data", (c) => { body += c; });
    req.on("end", () => {
      padPosts.push({ t: Date.now(), body, type: req.headers["content-type"] || "", mode: ledsMode });
      const refused = ledsMode !== "on";
      res.writeHead(refused ? 409 : 202, { ...CORS, "Content-Type": "application/json", Connection: "close" });
      res.end(refused ? '{"ok":false,"refused":"LEDs are off (--no-leds)"}' : '{"ok":true,"coalesced":false}');
    });
    return;
  }
  res.writeHead(404, CORS);
  res.end();
});
const send = (obj) => { for (const c of sse) c.write(`data: ${JSON.stringify(obj)}\n\n`); };
// Bind to the preferred test-band port, or the next free one up to 8999: another lane may hold the first (it happened:
// keylab_desk_verify ran on 8931/8932 while this was written; the GPU lock serialised us, but nothing should rely on it).
const portsTaken = new Set();
async function listenInBand(server, preferred) {
  for (let p = preferred; p <= 8999; p++) {
    if (p === 8793 || portsTaken.has(p)) continue;
    try {
      await new Promise((ok, fail) => {
        const onErr = (e) => { server.off("listening", onOk); fail(e); };
        const onOk = () => { server.off("error", onErr); ok(); };
        server.once("error", onErr);
        server.once("listening", onOk);
        server.listen(p, "127.0.0.1");
      });
      portsTaken.add(p);
      return p;
    } catch (e) {
      if (e.code !== "EADDRINUSE" && e.code !== "EACCES") throw e;
    }
  }
  throw new Error(`no free port from ${preferred} to 8999`);
}
async function freeInBand(preferred) {      // a port for a child process: bind, note, release
  const probe = createServer();
  const p = await listenInBand(probe, preferred);
  await new Promise((ok) => probe.close(ok));
  return p;
}

// --------------------------------------------------------------------------------------------- Chrome & CDP --
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

let gpu = null, chrome = null, browser = null;
const checks = {};
try {
  gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: "vj_verify (SwiftShader)", maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000 });
  report.gpu_lock = { acquired_at: gpu.owner.acquiredAt, inherited: gpu.inherited };
  PORT = await listenInBand(web, PORT);
  ENGINE_PORT = await listenInBand(engineServer, ENGINE_PORT);
  report.page = `http://127.0.0.1:${PORT}/web/vj.html`;
  report.engine = `http://127.0.0.1:${ENGINE_PORT}`;
  if (!existsSync(opt.chrome)) throw new Error(`no Chrome at ${opt.chrome}`);
  chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0",
    `--user-data-dir=${profile}`, `--window-size=${opt.width},${opt.height}`, "--force-device-scale-factor=1", "about:blank"],
    { stdio: "ignore", windowsHide: true });
  const portFile = join(profile, "DevToolsActivePort");
  const [cdpPort, cdpPath] = await waitFor(() => {
    try { const [p, w] = readFileSync(portFile, "utf8").split(/\r?\n/); return p && w ? [p, w] : null; } catch { return null; }
  }, 30000, "Chrome's DevToolsActivePort");
  browser = await connect(`ws://127.0.0.1:${cdpPort}${cdpPath}`);
  report.chrome = (await browser.send("Browser.getVersion")).product;
  const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (method, params = {}) => withTimeout(browser.send(method, params, sessionId), 45000, method);
  browser.on((msg) => {
    if (msg.sessionId !== sessionId) return;
    const p = msg.params;
    if (msg.method === "Runtime.consoleAPICalled") {
      report.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
    } else if (msg.method === "Runtime.exceptionThrown") {
      const d = p.exceptionDetails;
      report.exceptions.push({ text: d.text, description: d.exception?.description, line: d.lineNumber, url: d.url });
    } else if (msg.method === "Log.entryAdded" && (p.entry.level === "error" || p.entry.level === "warning")) {
      report.console.push({ type: `log-${p.entry.level}`, text: p.entry.text, url: p.entry.url });
    }
  });
  for (const d of ["Runtime", "Log", "Page"]) await S(`${d}.enable`);
  const evaluate = async (expression) => {
    const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const shot = async (name) => {
    const r = await S("Page.captureScreenshot", { format: "png" });
    const file = join(outDir, `${name}.png`);
    writeFileSync(file, Buffer.from(r.data, "base64"));
    report.screenshots.push(file);
    return file;
  };
  const KEYS = { 1: ["Digit1", "1", 49], 2: ["Digit2", "2", 50], 3: ["Digit3", "3", 51], 4: ["Digit4", "4", 52],
                 5: ["Digit5", "5", 53], 6: ["Digit6", "6", 54], 7: ["Digit7", "7", 55], 8: ["Digit8", "8", 56],
                 9: ["Digit9", "9", 57], 10: ["Digit0", "0", 48], 11: ["Minus", "-", 189], 12: ["Equal", "=", 187],
                 Q: ["KeyQ", "q", 81], W: ["KeyW", "w", 87], E: ["KeyE", "e", 69], R: ["KeyR", "r", 82],
                 H: ["KeyH", "h", 72], M: ["KeyM", "m", 77] };
  const key = async (k, type, shift = false) => {
    const [code, keyName, vk] = KEYS[k];
    await S("Input.dispatchKeyEvent", { type, code, key: shift ? keyName.toUpperCase() : keyName, windowsVirtualKeyCode: vk,
                                        nativeVirtualKeyCode: vk, modifiers: shift ? 8 : 0 });
  };
  const tap = async (k, shift = false, holdMs = 60) => { await key(k, "keyDown", shift); await delay(holdMs); await key(k, "keyUp", shift); };
  const stats = () => evaluate("window.__vj.stats()");
  const luma = () => evaluate("window.__vj.luma()");

  // ------------------------------------------------------------------------------------------- A: the demo --
  await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?demo=1&demopads=0&hud=0&watchdog=0` });
  await waitFor(() => evaluate("!!(window.__vj && window.__vj.ready)"), 60000, "the VJ page and its window.__vj hook");
  report.webgl = await evaluate(`(() => { const c = document.getElementById("gl"); const g = c.getContext("webgl2");
    if (!g) return null; const d = g.getExtension("WEBGL_debug_renderer_info");
    return { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER), version: g.getParameter(g.VERSION) }; })()`);
  report.renderer_check = judgeRenderer(report.webgl && report.webgl.renderer);
  if (!report.renderer_check.ok) throw new Error(`refusing to judge: ${report.renderer_check.reason}`);
  const setList = await evaluate("window.__vj.sets()");
  console.log(`[sets] ${setList.map((s) => `${s.id}:${s.status}`).join(" ")}`);

  const f0 = (await stats()).frames;
  for (const s of setList) {
    const row = { id: s.id, status: s.status, problem: s.problem };
    if (!s.broken) {
      row.selected = await evaluate(`window.__vj.select(${JSON.stringify(s.id)})`);
      const before = (await stats()).frames;
      await delay(dwellMs);
      const st = await stats();
      row.active = await evaluate("window.__vj.active()");
      row.frames = st.frames - before;
      row.luma = await luma();
      row.size = `${st.width}x${st.height}`;
      row.fps = st.fps;
      row.screenshot = await shot(`set-${s.id}`);
      // the same set answering pads: a shockwave, a hard laser burst and a held particle fountain (pads 1, 2, 6)
      await evaluate("(window.__vj.press(1, 0.9), window.__vj.press(2, 1.0), window.__vj.press(6, 0.85), true)");
      await delay(450);
      row.luma_pads = await luma();
      row.screenshot_pads = await shot(`set-${s.id}-pads`);
      await evaluate("(window.__vj.release(1), window.__vj.release(2), window.__vj.release(6), true)");
      await tap("W");                    // choke, so the next set starts clean
    }
    report.sets.push(row);
    console.log(`[set] ${s.id}: ${s.status} frames=${row.frames} luma=${row.luma?.toFixed?.(4)}`);
  }
  report.frames.advanced = (await stats()).frames - f0;

  // ------------------------------------------------------------------------------- B: pads by the keyboard --
  await evaluate(`window.__vj.select("vj-laser-cathedral")`);
  await delay(600);
  const fxOf = (st, type) => st.effects.filter((e) => e.type === type);
  await key(1, "keyDown");
  await delay(80);
  let st = await stats();
  report.pads.shockwave_soft = fxOf(st, "shockwave");
  await key(1, "keyUp");
  await key(2, "keyDown", true);
  await delay(80);
  st = await stats();
  report.pads.laser_hard = fxOf(st, "laser");
  await key(2, "keyUp", true);
  await delay(250);
  report.pads.screenshot_burst = await shot("accent-shockwave-laser");
  await key(5, "keyDown");               // strobe, held
  await key(6, "keyDown", true);         // particles, held hard
  await delay(700);
  st = await stats();
  report.pads.held = { strobe: fxOf(st, "strobe"), particles: fxOf(st, "particles") };
  report.pads.screenshot_held = await shot("accent-strobe-particles-held");
  await key(5, "keyUp");
  await key(6, "keyUp", true);
  await delay(120);
  st = await stats();
  report.pads.after_release = { strobe: fxOf(st, "strobe"), particles: fxOf(st, "particles") };
  await delay(1500);
  st = await stats();
  report.pads.released_gone = { strobe: fxOf(st, "strobe").length, particles: fxOf(st, "particles").length };
  await evaluate(`window.__vj.select("vj-reactor")`);
  await key(7, "keyDown", true);         // kaleidoscope
  await tap(4, true);                    // glitch
  await delay(500);
  report.pads.screenshot_kaleido = await shot("accent-kaleido-glitch");
  await key(7, "keyUp", true);
  await key(8, "keyDown");               // freeze
  await delay(400);
  st = await stats();
  report.pads.freeze = fxOf(st, "freeze");
  await key(8, "keyUp");
  checks.pad_soft_velocity_is_0_6 = report.pads.shockwave_soft.length === 1 && Math.abs(report.pads.shockwave_soft[0].vel - 0.6) < 1e-6;
  checks.shift_is_hard_velocity = report.pads.laser_hard.length === 1 && report.pads.laser_hard[0].vel === 1;
  checks.held_pads_sustain = report.pads.held.strobe.length === 1 && report.pads.held.strobe[0].held &&
    report.pads.held.particles.length === 1 && report.pads.held.particles[0].held && report.pads.held.particles[0].env > 0.5;
  checks.release_lets_go = report.pads.after_release.strobe.every((e) => !e.held) &&
    report.pads.released_gone.strobe === 0 && report.pads.released_gone.particles === 0;
  checks.freeze_and_kaleido_trigger = report.pads.freeze.length === 1;

  // ----------------------------------------------------------------------------------------- C: Q W E R --
  await key(6, "keyDown", true);
  await tap(1);
  await delay(200);
  await tap("Q");                        // dampen: a fast release of everything
  await delay(300);
  st = await stats();
  report.controls.after_dampen = st.effects.map((e) => `${e.type}:${e.env}`);
  checks.dampen_releases_everything_fast = st.effects.length === 0;
  await key(6, "keyUp", true);
  await tap(1); await tap(2, true); await tap(7);
  await delay(60);
  await tap("W");                        // choke: everything off now
  st = await stats();
  report.controls.after_choke = st.effects.length;
  checks.choke_cuts_now = st.effects.length === 0;
  const lumaBeforeKill = await luma();
  await tap("E");                        // kill on the next beat
  await delay(1400);
  st = await stats();
  const lumaKilled = await luma();
  report.controls.kill = { before: lumaBeforeKill, killed: lumaKilled, gain: st.kill.gain };
  report.controls.screenshot_killed = await shot("control-killed");
  await tap("E");                        // and back
  await delay(1600);
  st = await stats();
  report.controls.revive = { luma: await luma(), gain: st.kill.gain };
  checks.kill_fades_to_black_and_back = lumaKilled < 0.002 && st.kill.gain > 0.99 && report.controls.revive.luma > 0.001;
  const setBefore = st.setA;
  await tap("R");                        // next set: a transition of two beats, from the next bar (the demo counts bars)
  await delay(200);
  const fading = (await stats()).fading;
  // up to four beats' wait for the bar, then two beats of transition (112 bpm: about 3.2 s), then a margin
  await waitFor(async () => { const s = await stats(); return !s.fading && s.setA !== setBefore; }, 6000, "the switch").catch(() => null);
  st = await stats();
  report.controls.next = { from: setBefore, to: st.setA, fading_seen: fading };
  checks.next_switches_set = fading && st.setA !== setBefore;

  // ------------------------------------------------------------------------------------- D: the flash gate --
  await evaluate(`window.__vj.select("vj-chord-constellations")`);
  await delay(900);
  const gateBefore = (await stats()).flash;
  await evaluate("window.__vj.probe(true)");
  // ten presses of pad 3 (the white flash, Shift = hard) 100 ms apart, all inside one second: fired in the page through
  // the keyboard fallback's own listener, scheduled at absolute times so slow software frames cannot stretch the burst
  const requestTimes = await evaluate(`new Promise((done) => {
    const times = [], t0 = performance.now();
    for (let i = 0; i < 10; i++) setTimeout(() => {
      const o = { code: "Digit3", key: "#", shiftKey: true, bubbles: true };
      // down and up in one callback: a late timer must not deliver the next press while this key still reads as held
      window.dispatchEvent(new KeyboardEvent("keydown", o));
      window.dispatchEvent(new KeyboardEvent("keyup", o));
      times.push(Math.round(performance.now() - t0));
      if (times.length === 10) setTimeout(() => done(times), 40);
    }, i * 100);
  })`);
  const requestSpanMs = requestTimes[9] - requestTimes[0];
  await delay(1500);
  const trace = await evaluate("window.__vj.trace()");
  await evaluate("window.__vj.probe(false)");
  const gateAfter = (await stats()).flash;
  const grantedTimes = gateAfter.log.filter((t) => !gateBefore.log.includes(t));
  // measured flashes: a rise of 0.1 or more in mean relative luminance over the darkest of the previous 300 ms
  const rises = [];
  let armed = true;
  for (let i = 0; i < trace.length; i++) {
    const t = trace[i].t;
    let floor = Infinity;
    for (let j = i - 1; j >= 0 && t - trace[j].t <= 300; j--) floor = Math.min(floor, trace[j].luma);
    if (floor === Infinity) continue;
    if (armed && trace[i].luma - floor >= 0.1) { rises.push(t); armed = false; }
    if (!armed && trace[i].luma - floor < 0.05) armed = true;
  }
  let maxRises = 0;
  for (let i = 0; i < rises.length; i++) {
    let n = 0;
    for (let j = i; j < rises.length && rises[j] - rises[i] < 1000; j++) n++;
    maxRises = Math.max(maxRises, n);
  }
  report.flash = { requests: 10, request_times_ms: requestTimes, request_span_ms: requestSpanMs, granted: gateAfter.granted - gateBefore.granted,
                   refused: gateAfter.refused - gateBefore.refused, granted_times: grantedTimes,
                   gate_max_in_any_second: gateAfter.maxInAnyWindow, measured_rises: rises,
                   measured_max_in_any_second: maxRises, trace_samples: trace.length,
                   trace_peak: Math.max(0, ...trace.map((s) => s.luma)) };
  // more than three requests inside one second: the gate must refuse the excess and never grant a fourth in any second
  const firstSecond = requestTimes.filter((t) => t - requestTimes[0] < 1000).length;
  report.flash.requests_in_first_second = firstSecond;
  checks.flash_gate_grants_at_most_three_a_second = firstSecond > 3 && report.flash.granted >= 2 && gateAfter.maxInAnyWindow <= 3 &&
    report.flash.refused >= 10 - Math.ceil((requestSpanMs + 1) / 333);
  checks.measured_flashes_at_most_three_a_second = trace.length > 5 && maxRises <= 3;
  await tap("H");                        // the HUD, once, for the record
  await delay(300);
  report.hud_screenshot = await shot("hud");
  await tap("H");

  // ------------------------------------------------------------------------- E: the engine contract (fake) --
  await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=http://127.0.0.1:${ENGINE_PORT}&hud=0&watchdog=0` });
  await waitFor(() => evaluate("!!(window.__vj && window.__vj.ready)"), 60000, "the VJ page (engine run)");
  await waitFor(() => sse.size > 0, 15000, "the page's EventSource");
  const hello = (leds) => send({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", pads_mode: "both", leds,
                                 leds_reason: leds ? null : "LEDs are off (--no-leds)" });
  hello(true);
  send({ t: "status", msg: "fake engine for vj_verify" });
  const beatT0 = Date.now();
  let beatN = 0;
  const beatTimer = setInterval(() => {      // 120 bpm, each beat announced 200 ms ahead
    send({ t: "beat", due_ms: 200, bpm: 120, conf: 0.85, n: beatN++, on_beat: 0.9 });
    send({ t: "energy", bass: 0.7, mid: 0.4, high: 0.3, level: 0.5 });
  }, 500);
  await delay(1200);
  send({ t: "chord", src: "keys", name: "Dbmaj7", root: 1, quality: "maj7", pcs: [1, 5, 8, 0], changed: true });
  for (const k of [49, 65, 68, 72]) send({ t: "note", key: k, vel: 0.7, on: true });
  send({ t: "hit", strength: 0.9, band: "kick" });
  send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "bank" });
  await delay(150);
  st = await stats();
  report.engine_contract.after_events = { hello: st.engine.hello, chord: st.chord, stars: st.stars, beats: st.beats, bpm: st.bpm,
                                          effects: st.effects.map((e) => `${e.type}@${e.pad}:${e.vel}`) };
  send({ t: "pad", pad: 2, vel: 0, on: false, src: "bank" });
  // the page handles queued events between frames, so every step waits until the page has really taken the last one
  // (a learn armed over CDP would otherwise catch a control that was sent before it)
  const settle = async (pred) => { try { return await waitFor(async () => pred(await stats()), 8000, "the page"); } catch { return false; } };
  send({ t: "ctl", id: "cc105", kind: "abs", value: 0.2, delta: 0 });
  send({ t: "ctl", id: "cc91", kind: "rel", value: 0, delta: 8 });
  report.engine_contract.controls_taken = await settle((s) => s.lastCtl && s.lastCtl.id === "cc91");
  // Rewind / Fast forward (the DAW port's CC 25 / 26) step the sets, always (Daniel, 2026-10-25: "lets try always we can
  // make it an option"); the same numbers from the keys input do not, and a release does nothing
  {
    const activeId = async () => (await evaluate("window.__vj.active()"))?.id ?? null;
    const settleActive = async (pred) => { try { return await waitFor(async () => pred(await activeId()), 12000, "the set change"); } catch { return false; } };
    const press = (cc, port) => { send({ t: "ctl", id: `cc${cc}`, kind: "abs", value: 1, delta: 0, port });
                                  send({ t: "ctl", id: `cc${cc}`, kind: "abs", value: 0, delta: 0, port }); };
    const fromId = await activeId();
    press(26, "midi");
    await delay(2500);
    const keysIgnored = (await activeId()) === fromId;
    press(26, "daw");
    const stepped = await settleActive((id) => !!id && id !== fromId);
    const nextId = await activeId();
    press(25, "daw");
    const back = await settleActive((id) => id === fromId);
    report.engine_contract.transport_sets = { from: fromId, next: nextId, keys_ignored: keysIgnored, stepped, back };
    checks.rewind_and_fast_forward_step_the_sets = keysIgnored && stepped && !!back && !!nextId && nextId !== fromId;
  }
  // learn on touch, the way a person does it: open the mapping panel (M), click Learn on Saturation, move a control
  await tap("M");
  await delay(300);
  report.engine_contract.panel_open = await evaluate(`!document.getElementById("panel").hidden`);
  report.engine_contract.learn_clicked = await evaluate(`(() => {
    const row = [...document.querySelectorAll("#targets .target")].find((r) => r.querySelector("label").textContent === "Saturation");
    if (!row) return false; row.querySelector("button").click(); return true; })()`);
  send({ t: "ctl", id: "cc120", kind: "abs", value: 0.3, delta: 0 });
  report.engine_contract.learned = await settle((s) => s.ctlMap.cc120 === "sat");
  send({ t: "ctl", id: "cc120", kind: "abs", value: 0.4, delta: 0 });
  await settle((s) => s.lastCtl && s.lastCtl.value === 0.4);
  // the pad map is editable: pad 1 becomes Invert
  report.engine_contract.pad_edit = await evaluate(`(() => { const sel = document.querySelectorAll("#pad-map select")[0];
    sel.value = "invert"; sel.dispatchEvent(new Event("change")); return window.__vj.stats().padMap[0]; })()`);
  report.engine_contract.screenshot_panel = await shot("panel");
  await tap("M");
  await delay(1000);
  st = await stats();
  report.engine_contract.controls = { hueA: st.values.hueA, sat: st.values.sat, cc120: st.ctlMap.cc120, lastCtl: st.lastCtl };
  report.engine_contract.screenshot = await shot("engine-dbmaj7-pad2");
  clearInterval(beatTimer);
  const posts = padPosts.slice();
  const gaps = posts.slice(1).map((p, i) => p.t - posts[i].t);
  let bodyOk = posts.length > 0;
  for (const p of posts) {
    try { const b = JSON.parse(p.body); bodyOk = bodyOk && Array.isArray(b.colors) && b.colors.length === 12 && b.colors.every((c) => /^#[0-9a-f]{6}$/.test(c)); }
    catch { bodyOk = false; }
  }
  let maxPerSecond = 0;
  for (let i = 0; i < posts.length; i++) {
    let n = 0;
    for (let j = i; j < posts.length && posts[j].t - posts[i].t < 1000; j++) n++;
    maxPerSecond = Math.max(maxPerSecond, n);
  }
  report.engine_contract.pad_posts = { count: posts.length, min_gap_ms: gaps.length ? Math.min(...gaps) : null, max_per_second: maxPerSecond,
                                       sample: posts.slice(-1)[0]?.body, content_type: posts[0]?.type, beats_sent: beatN,
                                       seconds: (Date.now() - beatT0) / 1000 };
  checks.engine_hello_and_beats = !!(st.engine.hello && st.engine.hello.src === "keylab-vj") && st.beats >= 3 && st.bpm === 120;
  checks.engine_chord_and_stars = report.engine_contract.after_events.chord === "Dbmaj7" && report.engine_contract.after_events.stars === 4;
  checks.engine_pad_triggers_mapped_effect = report.engine_contract.after_events.effects.some((e) => e.startsWith("laser@2:0.9"));
  checks.engine_fader_sets_hue = Math.abs(st.values.hueA - 0.2) < 1e-6;
  checks.learn_on_touch_binds_any_control = report.engine_contract.panel_open && report.engine_contract.learn_clicked &&
    st.ctlMap.cc120 === "sat" && Math.abs(st.values.sat - 0.4) < 1e-6;
  checks.pad_map_is_editable = report.engine_contract.pad_edit === "invert";
  checks.pad_lights_posted_at_most_ten_a_second = bodyOk && posts.length >= 2 && maxPerSecond <= 10;

  // -------------------------------------- E1: chordsense's key, numeral and tension (vj --chords sense) --
  // The engine's hello says which chord engine runs; key {name, conf}, tension {value, pedal_pc} and the chord's roman /
  // key / bass / conf come from chordsense (arsenal/keylab/vj.py Harmony, chordsense.to_vj_events). The HUD shows the key
  // and the numeral; the engine's tension feeds the strip's tension texel (row 0, x 14, z) IN PLACE of the page's own
  // estimate, never on top of it; a key change accents through the chord-change path and never asks the flash gate; an
  // engine that sends none of it leaves the page as it was.
  const hudOf = () => evaluate(`({ key: document.getElementById("hud-key").textContent,
    chord: document.getElementById("hud-chord").textContent, engine: document.getElementById("hud-engine").textContent })`);
  const harmony = {};
  send({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", chords: "sense", pads_mode: "both", leds: true, leds_reason: null });
  send({ t: "key", name: "Db major", conf: 0.82, src: "keys" });
  send({ t: "chord", src: "keys", name: "Gbmaj7", root: 6, quality: "maj7", pcs: [1, 5, 6, 10], changed: true, bass: 6,
         roman: "IVmaj7", key: "Db major", conf: 1 });
  send({ t: "tension", value: 0.62, pedal_pc: 1, src: "keys" });
  const sensed = await settle((s) => (s.harmony.key === "Db major" && s.roman === "IVmaj7" && s.harmony.live &&
                                      s.engine.hello && s.engine.hello.chords === "sense" ? s : false));
  await delay(250);                       // the HUD redraws every 100 ms; the strip is rebuilt on the next frame
  const fed = sensed ? await stats() : null;
  harmony.sensed = fed ? { harmony: fed.harmony, roman: fed.roman, chord: fed.chord, chordKey: fed.chordKey,
                           bass: fed.bass, chordConf: fed.chordConf, pageTension: fed.tension,
                           pedalTension: fed.pedal.tension } : null;
  harmony.hud = await hudOf();
  await tap("H");
  await delay(300);
  harmony.screenshot = await shot("hud-key-roman-tension");
  await tap("H");
  console.log(`[harmony] HUD key "${harmony.hud.key}" | chord "${harmony.hud.chord}"`);
  checks.engine_key_and_roman_show_in_the_hud = !!sensed && /Db major/.test(harmony.hud.key) && /IVmaj7/.test(harmony.hud.key) &&
    /^Gbmaj7\s+IVmaj7 \(keys\)/.test(harmony.hud.chord) && /chords sense/.test(harmony.hud.engine) &&
    sensed.bass === 6 && sensed.chordConf === 1;
  // the engine's tension, not stacked on the page's: the strip carries max(engine, page pedal x 0.8) -- and when the
  // engine says the tension is gone, the strip follows it down even while the page's own estimate would say more
  checks.engine_tension_feeds_the_strip = !!fed && Math.abs(fed.harmony.tension - 0.62) < 0.05 &&
    Math.abs(fed.harmony.strip - Math.max(fed.harmony.tension, fed.pedal.tension * 0.8)) < 0.03 &&
    /tension 0\.6\d \(engine\)/.test(harmony.hud.chord);
  send({ t: "tension", value: 0, pedal_pc: null, src: "keys" });
  const relaxed = await settle((s) => (s.harmony.tension < 0.03 ? s : false));
  harmony.relaxed = relaxed ? { harmony: relaxed.harmony, pageTension: relaxed.tension, pedalTension: relaxed.pedal.tension } : null;
  // the Dbmaj7 held since phase E gives the page's own estimate a tension of its own (its major 7th): the strip must
  // follow the engine below it, which only a replacement (not a max, not a sum) does
  checks.engine_tension_replaces_the_page_estimate_never_adds = !!relaxed && relaxed.tension !== null &&
    relaxed.tension > 0.1 && relaxed.harmony.strip < relaxed.tension - 0.05 &&
    Math.abs(relaxed.harmony.strip - Math.max(relaxed.harmony.tension, relaxed.pedal.tension * 0.8)) < 0.03;
  // a key change: a small accent through the chord-change path (the chord pulse, the constellation redraw), no flash
  const gate0 = (await stats()).flash;
  const accents0 = (await stats()).harmony.keyAccents;
  send({ t: "key", name: "Ab major", conf: 0.7, src: "keys" });
  const moved = await settle((s) => (s.harmony.keyAccents === accents0 + 1 && s.harmony.key === "Ab major" ? s : false));
  harmony.key_change = moved ? { accents: moved.harmony.keyAccents, chordPulse: moved.harmony.chordPulse, gate: moved.flash } : null;
  await delay(1100);
  const gate1 = (await stats()).flash;
  harmony.gate = { before: gate0, after: gate1 };
  checks.a_key_change_accents_without_a_flash = !!moved && moved.harmony.chordPulse > 0.2 &&
    gate1.granted === gate0.granted && gate1.refused === gate0.refused && gate1.maxInAnyWindow <= 3;
  // an engine that sends no key, no tension and no numerals (--chords basic, an older engine): the page as before
  send({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", chords: "basic", pads_mode: "both", leds: true, leds_reason: null });
  send({ t: "chord", src: "audio", name: "Am", root: 9, quality: "m", pcs: [0, 4, 9], changed: true, conf: 0.9 });
  const basicSeen = await settle((s) => (s.chord === "Am" && !s.harmony.live && s.harmony.key === "" ? s : false));
  await delay(250);
  const basic = basicSeen ? await stats() : null;    // a frame later: the strip rebuilt without the engine's tension
  harmony.basic = { hud: await hudOf(), harmony: basic ? basic.harmony : null, pageTension: basic ? basic.tension : null };
  checks.an_engine_without_chordsense_leaves_the_page_estimate = !!basic && basic.roman === "" &&
    Math.abs(basic.harmony.strip - Math.max(basic.tension ?? 0, basic.pedal.tension * 0.8)) < 0.03 &&
    harmony.basic.hud.key === "—" && /^Am \(audio 0\.90\)/.test(harmony.basic.hud.chord) && !/\(engine\)/.test(harmony.basic.hud.chord);
  report.engine_contract.harmony = harmony;
  hello(true);                            // back to the plain fake engine for the phases that follow
  // the chords above set the palette travelling, and the page posts its pad colours while they change: let the posts go
  // quiet before E2 counts them (a post made before E2's no-LEDs hello arrives would be counted against it)
  for (let quiet = 0, n = padPosts.length, end = Date.now() + 8000; quiet < 700 && Date.now() < end; ) {
    await delay(100);
    if (padPosts.length === n) quiet += 100; else { quiet = 0; n = padPosts.length; }
  }

  // ----------------------------- E2: an engine without LEDs is not asked; a refusal stops posting until hello --
  // Pads 1-4 pressed five times a second, so the pad colours keep changing (the page posts only a changed frame). Each
  // window is longer than the old page's five-second retry after a refusal, which posted twice in it.
  const padActivity = (ms) => evaluate(`new Promise((done) => {
    let i = 0;
    const timer = setInterval(() => {
      const p = 1 + (i % 4);
      window.__vj.press(p, 0.5 + 0.1 * (i % 5));
      setTimeout(() => window.__vj.release(p), 120);
      if (++i * 200 >= ${ms}) { clearInterval(timer); setTimeout(() => done(true), 200); }
    }, 200);
  })`);
  // every post is stamped with the fake's mode when it arrived, so each phase counts exactly the posts made in it
  const leds = {};
  const postsIn = (mode, from) => padPosts.slice(from).filter((p) => p.mode === mode).length;
  let mark = padPosts.length;
  ledsMode = "off";
  hello(false);
  leds.off_seen = await settle((s) => s.engine.ledsOff === "LEDs are off (--no-leds)");
  await padActivity(6000);
  leds.off_posts = postsIn("off", mark);
  leds.off_state = (await stats()).engine;
  // the page's own demo playing on top of a connected engine must not speak for it: before 2026-10-23 its hello reached
  // the engine link, cleared "LEDs are off" and put "demo" in the HUD as the engine's name
  await evaluate(`window.__vj.demo(true)`);
  const withDemo = await settle((s) => (s.engine.demoEvents > 5 ? s : false));
  await evaluate(`window.__vj.demo(false)`);
  leds.demo_on_top = withDemo ? { ledsOff: withDemo.engine.ledsOff, src: withDemo.engine.hello && withDemo.engine.hello.src,
                                  demoEvents: withDemo.engine.demoEvents } : null;
  checks.the_page_demo_never_speaks_for_the_engine = !!withDemo && withDemo.engine.ledsOff === "LEDs are off (--no-leds)" &&
    !!withDemo.engine.hello && withDemo.engine.hello.src === "keylab-vj";
  mark = padPosts.length;
  ledsMode = "refuse";
  hello(true);
  await padActivity(6000);
  leds.refuse_posts = postsIn("refuse", mark);
  leds.refuse_state = (await stats()).engine;
  mark = padPosts.length;
  ledsMode = "on";
  hello(true);
  leds.on_cleared = await settle((s) => s.engine.ledsOff === "");
  await padActivity(1500);
  leds.resumed_posts = postsIn("on", mark);
  report.engine_contract.leds = leds;
  console.log(`[leds] off: ${leds.off_posts} posts in 6 s; refused: ${leds.refuse_posts} posts in 6 s; on again: ${leds.resumed_posts} in 1.5 s`);
  checks.no_pad_posts_to_an_engine_without_leds = !!leds.off_seen && leds.off_posts === 0;
  checks.a_refused_post_stops_posting_until_the_next_hello = leds.refuse_posts === 1 && leds.refuse_state.refused >= 1 &&
    /refused \(HTTP 409\)/.test(leds.refuse_state.ledsOff) && !!leds.on_cleared && leds.resumed_posts >= 2;

  // --------------------------------------------- E3: a dropped engine's status leaves the HUD with it --
  send({ t: "status", msg: "fake engine for vj_verify: about to drop" });
  await settle((s) => s.engine.status === "fake engine for vj_verify: about to drop");
  for (const c of [...sse]) { try { c.end(); } catch { /* closed */ } }
  const dropped = await settle((s) => (!s.engine.open ? s : false));
  report.engine_contract.after_drop = dropped ? dropped.engine : null;
  const hudText = () => evaluate(`document.getElementById("hud-engine").textContent`);
  // the HUD redraws a few times a second; give it a moment, then it must not show the dropped engine's last status
  let hudClean = false;
  try { hudClean = !!(await waitFor(async () => !(await hudText()).includes("about to drop"), 2000, "the HUD")); } catch { /* stale */ }
  report.engine_contract.hud_after_drop = await hudText();
  checks.a_dropped_engine_leaves_no_status = !!dropped && dropped.engine.status === "" && dropped.engine.hello === null &&
    hudClean;
  await waitFor(() => sse.size > 0, 20000, "the page reconnecting to the engine");
  hello(true);
  await settle((s) => s.engine.hello && s.engine.open);

  // ------------------------------------------------------------- F: the pedal star (Joy to the World's end) --
  // 20 strikes: the star lights at the 16th (vj-core.js PedalDetector, tuned on Daniel's whole take)
  await evaluate(`window.__vj.select("vj-chord-constellations")`);
  for (const k of [49, 65, 68, 72]) send({ t: "note", key: k, vel: 0, on: false });
  const walk = [49, 48, 46, 44, 42, 41, 39, 37, 36, 37, 39, 41, 42, 44, 46, 48, 49, 46, 44, 42];
  const names = ["Db", "C7", "Bbm", "Ab", "Gb", "Fm", "Ebm7", "Db", "C7", "Db", "Ebm7", "Fm", "Gb", "Ab", "Bbm", "C7", "Db",
                 "Bbm", "Ab", "Gb"];
  for (let i = 0; i < walk.length; i++) {
    send({ t: "chord", src: "keys", name: names[i], root: walk[i] % 12, quality: "", pcs: [walk[i] % 12, 1], changed: true });
    send({ t: "note", key: walk[i], vel: 0.7, on: true });
    await delay(15);
    send({ t: "note", key: 73, vel: 0.6 + 0.02 * i, on: true });     // D-flat 5, again and again
    await delay(200);
    send({ t: "note", key: 73, vel: 0, on: false });
    send({ t: "note", key: walk[i], vel: 0, on: false });
    if (i === walk.length - 3) report.pedal.screenshot = await shot("pedal-star-db");
    await delay(60);
  }
  st = await stats();
  report.pedal.during = st.pedal;
  await delay(2200);
  st = await stats();
  report.pedal.after = st.pedal;
  checks.pedal_star_finds_the_repeated_note = report.pedal.during.key === 73 && report.pedal.during.strikes >= 16 &&
    report.pedal.during.tension > 0.3;
  checks.pedal_resolves_when_the_repeats_stop = report.pedal.after.key === -1 && report.pedal.after.resolved >= 16;

  // ------------------------------------------ G: the showcase follows an engine that plays beats (not the demo) --
  // Merging the fixes (vj-core.js EngineLink) with the scenes (vj-stage.js) once left the stage's accessors reading
  // engine.open / engine.hello, which no longer exist: the tour then never saw the engine and started the page's demo
  // on top of it (found by the verifier's end-to-end replay, 2026-10-23).
  let showN = 0;
  const showBeats = setInterval(() => send({ t: "beat", due_ms: 200, bpm: 120, conf: 0.85, n: showN++, on_beat: 0.9 }), 500);
  await delay(1200);
  await evaluate("window.__vjx.startShowcase()");
  await delay(3600);                     // the tour listens 2.5 s for an engine's beats before it starts the demo
  report.showcase_engine = {
    show: await evaluate("(() => { const x = window.__vjx.showcase(); return { on: x.on, mode: x.mode }; })()"),
    demo: (await stats()).demo,
  };
  await evaluate("window.__vjx.stopShowcase()");
  await evaluate("window.__vj.demo(false)");
  clearInterval(showBeats);
  checks.showcase_follows_a_playing_engine = report.showcase_engine.show.on && report.showcase_engine.show.mode === "engine" &&
    report.showcase_engine.demo === false;

  report.page_errors = await evaluate("window.__vj.errors()");
  report.final_stats = await stats();

  // ------------------------------- E4: the REAL engine's chordsense, end to end (no keyboard, no LEDs, no loopback) --
  // py -m arsenal.keylab vj --replay-audio demo --no-leds --no-midi on a test-band port: its made-up groove (C Am F G under
  // a kick, a snare and hats) goes through chordsense, and the page must show the key and the numerals it hears.
  if (!opt["no-real-engine"]) {
    REAL_PORT = await freeInBand(REAL_PORT);
    const real = { port: REAL_PORT, url: `http://127.0.0.1:${REAL_PORT}` };
    realEngine = spawn("py", ["-m", "arsenal.keylab", "vj", "--port", String(REAL_PORT), "--no-leds", "--no-midi",
                              "--replay-audio", "demo", "--quiet", "--secs", "180"],   // the default chords (blend)
                       { cwd: REPO, stdio: "ignore", windowsHide: true });
    await waitFor(async () => { try { return (await fetch(`${real.url}/api/state`)).ok; } catch { return false; } },
                  30000, "the real VJ engine on its test port");
    await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=${real.url}&hud=0&watchdog=0` });
    await waitFor(() => evaluate("!!(window.__vj && window.__vj.ready)"), 60000, "the VJ page (real engine)");
    let heard = null;
    try {
      heard = await waitFor(async () => {
        const s = await stats();
        return s.engine.hello && s.engine.hello.chords === "blend" && s.harmony.key && s.roman && s.harmony.live ? s : null;
      }, 40000, "the real engine's key and numerals on the page");
    } catch { /* judged below */ }
    await delay(400);
    real.hud = await evaluate(`({ key: document.getElementById("hud-key").textContent,
      chord: document.getElementById("hud-chord").textContent, engine: document.getElementById("hud-engine").textContent })`);
    await tap("H");
    await delay(300);
    real.screenshot = await shot("real-engine-key-roman");
    await tap("H");
    const last = await stats();
    real.page = heard ? { hello: heard.engine.hello, key: heard.harmony.key, keySrc: heard.harmony.keySrc,
                          roman: heard.roman, chord: heard.chord, chordSrc: heard.chordSrc, tension: heard.harmony.tension,
                          bad: last.engine.bad, events: last.engine.events } : null;
    try { real.state = await (await fetch(`${real.url}/api/state`)).json(); } catch { real.state = null; }
    report.page_errors = report.page_errors.concat(await evaluate("window.__vj.errors()"));
    console.log(`[real engine] key "${real.hud.key}" | chord "${real.hud.chord}"`);
    const ev = real.state ? real.state.events : {};
    checks.the_real_engine_shows_key_and_roman_on_the_page = !!heard && /^(C major|A minor) /.test(real.hud.key + " ") &&
      ["C major", "A minor"].includes(heard.harmony.key) && heard.chordSrc === "audio" && /\(audio/.test(real.hud.chord) &&
      last.engine.bad === 0 && (ev.key || 0) >= 1 && (ev.tension || 0) >= 1 && (ev.chord || 0) >= 2 &&
      real.state.chords === "blend" && real.state.audio.timing.capture && real.state.audio.timing.capture.gap === false;
    report.real_engine = real;
    // the page leaves first: an engine killed under an open stream makes Chrome log a reset connection
    await S("Page.navigate", { url: "about:blank" });
    await delay(500);
    spawnSync("taskkill", ["/PID", String(realEngine.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
  }

  // the edited pad map and the learned control survive a reload (localStorage), and the reset buttons restore defaults
  await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=off&hud=0&watchdog=0` });
  await waitFor(() => evaluate("!!(window.__vj && window.__vj.ready)"), 60000, "the VJ page (reload)");
  st = await stats();
  report.persistence = { padMap0: st.padMap[0], cc120: st.ctlMap.cc120 };
  await evaluate(`(document.getElementById("btn-reset-pads").click(), document.getElementById("btn-reset-ctl").click(), true)`);
  st = await stats();
  report.persistence.after_reset = { padMap0: st.padMap[0], cc120: st.ctlMap.cc120 ?? null, cc107: st.ctlMap.cc107 };
  report.page_errors = report.page_errors.concat(await evaluate("window.__vj.errors()"));
  checks.mappings_persist_and_reset = report.persistence.padMap0 === "invert" && report.persistence.cc120 === "sat" &&
    report.persistence.after_reset.padMap0 === "shockwave" && report.persistence.after_reset.cc120 === null &&
    report.persistence.after_reset.cc107 === "sat";

  // ------------------------------------------------- G: the same preset files load in Play (their other host) --
  // Our own arsenal/serve.py on a test-band port (never 8793), an empty library, no practice log; Play's own test hook.
  if (!opt["no-play"]) {
    const consoleMark = report.console.length, excMark = report.exceptions.length;
    PLAY_PORT = await freeInBand(PLAY_PORT);
    report.play_server = `http://127.0.0.1:${PLAY_PORT}`;
    const libDir = join(profile, "empty-library");
    mkdirSync(libDir, { recursive: true });
    playServer = spawn("py", ["-m", "arsenal", "serve", "--port", String(PLAY_PORT), "--root", libDir, "--no-performance-log"],
                       { cwd: REPO, stdio: "ignore", windowsHide: true });
    await waitFor(async () => (await fetch(`http://127.0.0.1:${PLAY_PORT}/api/health`)).ok, 30000, "our serve.py on the test port");
    await S("Page.navigate", { url: `http://127.0.0.1:${PLAY_PORT}/play` });
    await waitFor(() => evaluate(`!!(window.__play && document.readyState === "complete")`), 30000, "Play and window.__play");
    await delay(2500);                   // the bank fetches and compiles
    const bank = await evaluate("window.__play.presets()");
    report.play = { presets: bank.filter((p) => p.id.startsWith("vj-")), rows: [] };
    for (const p of report.play.presets) {
      if (p.broken) { report.play.rows.push({ id: p.id, broken: true, problem: p.problem }); continue; }
      await evaluate(`window.__play.select(${JSON.stringify(p.id)})`);
      await delay(1200);
      const active = await evaluate("window.__play.active()");
      report.play.rows.push({ id: p.id, active, screenshot: await shot(`play-${p.id}`) });
    }
    report.play.errors = await evaluate("window.__play.errors()");
    await S("Page.navigate", { url: "about:blank" });   // Play's own pagehide work belongs to this phase
    await delay(800);
    // Play's console is Play's business (its audio and take plumbing); the VJ checks judge the VJ page only
    report.play.console = report.console.splice(consoleMark);
    report.play.exceptions = report.exceptions.splice(excMark);
    const vjFiles = readdirSync(join(WEB, "presets")).filter((f) => /^vj-.*\.frag$/.test(f)).length;
    report.play.vj_files = vjFiles;
    checks.vj_presets_load_and_compile_in_play = report.play.presets.length === vjFiles && vjFiles >= 5 &&
      report.play.rows.every((r) => !r.broken && r.active && r.active.id === r.id && r.active.compiled === true);
    checks.play_raised_no_exception_with_vj_presets = report.play.exceptions.length === 0;
  }
  await S("Page.navigate", { url: "about:blank" });
} catch (err) {
  report.error = String((err && err.stack) || err);
  console.log("ERROR", report.error);
} finally {
  const setsOk = report.sets.length > 0 && report.sets.every((r) => r.status === "ok" && r.active?.compiled && r.active?.id === r.id);
  checks.every_set_compiles = setsOk;
  checks.every_set_renders_non_black = report.sets.length > 0 && report.sets.every((r) => typeof r.luma === "number" && r.luma > 0.0008);
  checks.frames_advance = report.sets.length > 0 && report.sets.every((r) => r.frames > 2);
  checks.software_renderer_only = !!report.renderer_check?.ok;
  checks.no_page_exceptions = report.exceptions.length === 0;
  // the page's web fonts come from Google; a test browser that cannot reach them is not a page fault
  const external = (c) => /fonts\.(googleapis|gstatic)\.com/.test(`${c.url || ""} ${c.text || ""}`);
  report.external_errors = report.console.filter((c) => (c.type === "error" || c.type === "log-error") && external(c));
  // Chrome logs every refused fetch ("Failed to load resource ... 409"); phase E2 provokes exactly as many refusals as the
  // fake engine refused posts, so those are expected -- and counted, so a page that kept posting would still show here
  const refusal = (c) => /\/api\/pads/.test(c.url || "") && /\b409\b/.test(c.text || "");
  report.expected_refusals = report.console.filter(refusal);
  const refusedPosts = padPosts.filter((p) => p.mode !== "on").length;
  checks.refusal_console_lines_match_the_refused_posts = report.expected_refusals.length === refusedPosts;
  checks.no_console_errors = !report.console.some((c) => (c.type === "error" || c.type === "log-error") && !external(c) &&
    !refusal(c));
  checks.no_page_recorded_errors = Array.isArray(report.page_errors) && report.page_errors.length === 0;
  checks.no_script_error = !report.error;
  report.verdict = { pass: Object.values(checks).every(Boolean), checks };
  report.finished_at = new Date().toISOString();
  writeFileSync(join(outDir, "receipt.json"), JSON.stringify(report, null, 2));
  try { await browser?.send("Browser.close"); } catch { /* gone */ }
  await delay(800);
  if (chrome && chrome.exitCode === null) spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
  if (playServer && playServer.exitCode === null) {
    spawnSync("taskkill", ["/PID", String(playServer.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
  }
  if (realEngine && realEngine.exitCode === null) {
    spawnSync("taskkill", ["/PID", String(realEngine.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
  }
  for (const c of sse) { try { c.end(); } catch { /* closed */ } }
  web.close();
  engineServer.close();
  gpu?.release();
  await delay(300);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
  for (const [k, v] of Object.entries(checks)) console.log(`${v ? "PASS" : "FAIL"} ${k}`);
  for (const e of report.exceptions) console.log("EXC", e.description || e.text);
  for (const c of report.console.filter((c) => c.type === "error" || c.type === "log-error")) {
    console.log(report.expected_refusals?.includes(c) ? "CONSOLE (expected: the refusal phase E2 provokes)" : "CONSOLE", c.text);
  }
  console.log("verdict:", report.verdict.pass ? "PASS" : "FAIL");
  console.log("receipt:", join(outDir, "receipt.json"));
  process.exit(report.verdict.pass ? 0 : 1);
}
