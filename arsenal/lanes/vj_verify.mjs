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
// the page's demo over it; no page exceptions or console errors. Since the impact pass (2026-10-24): pad storms on a
// 60 fps virtual clock (vj_storm.mjs: Invert held, one-shots at 15 and 5 a second, all 12 pads, the white flash at the
// gate's edge) stay at three flashes a second or fewer in every quarter-screen window, gate v2 running; the transport and the
// dial switch scenes (a press, never a release; a held button once; the dial browses and its click goes; a fast spin
// cannot flood); the page tells the engine its scene (POST /api/scene) and stops asking an older engine that answers 404;
// ~100 energy events a second reach the page; a pad event is drawn in the next frame at full strength; the beat snap
// holds a hit to the next 16th; the real engine keeps the page's scene for the KeyLab's screen. Since Lasers v2
// (2026-10-25), phase L on a 60 fps virtual clock with the engine's beats: pad 2 draws the laser engine's beams (the beam
// layer, read back) on the beat grid with the three velocity tiers (soft single, medium one-two, hard triple); the dial
// (cc116) changes the gate and its click (cc117) puts it back on AUTO; fader 1 (cc105) changes the colour theme on the
// next bar and the lasers take its colours; a hello naming the tap controls makes pad 12 the tap (no effect fires for
// it, the press is counted); the Laser Cathedral draws its own heads from the head bus while the beam layer draws only
// the hero's; the pad lights posted are LED stand-ins the pads can show. D2 adds the laser storms (lasertiers, laserroll).
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
import { SCENARIOS as STORM_SCENARIOS, VIRTUAL_CLOCK as STORM_VIRTUAL_CLOCK, runStormInPage } from "./vj_storm.mjs";

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
    "photosensitivity beyond flashes: stripes and patterns are not counted (flashes, red flashes and quarter-screen areas are, in phase D2)",
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
// the fake engine's scene route (POST /api/scene, 2026-10-24): "on" = 202 as the real engine answers; "absent" = 404, as
// an engine older than the route answers (the page must stop asking it until its next hello)
let sceneMode = "on";
const scenePosts = [];
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
  if (url.pathname === "/api/scene" && req.method === "POST") {
    let body = "";
    req.on("data", (c) => { body += c; });
    req.on("end", () => {
      let parsed = null;
      try { parsed = JSON.parse(body); } catch { /* counted as unparsed */ }
      scenePosts.push({ t: Date.now(), body: parsed, raw: body.slice(0, 300), mode: sceneMode });
      const absent = sceneMode !== "on";
      res.writeHead(absent ? 404 : 202, { ...CORS, "Content-Type": "application/json", Connection: "close" });
      res.end(absent ? '{"error":"no route /api/scene"}' : '{"ok":true,"changed":true}');
      if (!absent && parsed && parsed.name) send({ t: "scene", name: parsed.name, index: parsed.index, count: parsed.count,
                                                    color: parsed.color || null, browsing: parsed.browsing === true });
    });
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
  // one run holds the lock throughout (about 9 min before Lasers v2, 12-14 with its phase and storms): a 25-minute cap so a
  // waiter never reaps a run still going, and a 0.5 s poll so a run waiting behind lanes that render in short chunks gets
  // its turn (at 2 s it waited more than 30 minutes on 2026-10-25)
  gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: "vj_verify (SwiftShader)", maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000,
                              maxHoldMs: 25 * 60_000, pollMs: 500 });
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
  // gate v2 compiles in the background; the page is in its safe mode (every pad effect refused) until the meter and the
  // apply pass link, decides on the CPU until the GPU decision links too, then on the GPU
  await waitFor(() => evaluate("(() => { const l = window.__vj.stats().limiter; return l.mode === 'gpu' || l.fatal; })()"), 120000, "gate v2's programs");
  report.limiter = await evaluate("window.__vj.stats().limiter");
  checks.gate_v2_compiled = !!(report.limiter && report.limiter.on && report.limiter.mode === "gpu");
  report.webgl =await evaluate(`(() => { const c = document.getElementById("gl"); const g = c.getContext("webgl2");
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
  report.pads.laser_hard = st.lasers && st.lasers.last ? [st.lasers.last] : [];   // pad 2: the laser engine's hit (Lasers v2)
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
  checks.shift_is_hard_velocity = report.pads.laser_hard.length === 1 && report.pads.laser_hard[0].vel === 1 &&
    report.pads.laser_hard[0].src === "key";
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

  // ------------------------------- D2: pad storms on a 60 fps virtual clock (the 2026-10-24/25 safety passes) --
  // The real-clock storm this phase used to run missed what the adversarial verifier found (SwiftShader's slow frames
  // stretched the storm, and it counted rises only). Now: a second tab with vj_storm's virtual clock, the storms of
  // arsenal/lanes/vj_storm.mjs on Reactor for 4 s (the receipt itself runs them 10 s on three sets, at show sizes, with
  // adversarial content): Invert held under hard hits at 10 a second, one-shots (pads 1, 2, 4, 12) at 15 and at 5 a
  // second, pads 1, 2, 4 at 15, all 12 pads, the white flash at the gate's own edge and at 2.5 a second, laser and glitch
  // alternating, the look at full under every flash-capable pad; then the one-shots again with the limiter deciding on the
  // CPU (its fallback) and with no limiter at all (the safe mode, which must refuse the pads). Flashes are counted the
  // verifier's way (pairs of swings of 0.1 relative luminance), transitions and strict pairs, in 4726 quarter-screen
  // windows at every offset of a 64 x 36 grid (not the limiter's own), and red flashes too: at most 3 a second.
  {
    const { targetId: t2 } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId: s2 } = await browser.send("Target.attachToTarget", { targetId: t2, flatten: true });
    const S2 = (method, params = {}) => withTimeout(browser.send(method, params, s2), 600000, method);
    browser.on((msg) => {
      if (msg.sessionId !== s2 || msg.method !== "Runtime.exceptionThrown") return;
      const d = msg.params.exceptionDetails;
      report.exceptions.push({ text: d.text, description: d.exception?.description, line: d.lineNumber, url: d.url, tab: "storm" });
    });
    await S2("Runtime.enable"); await S2("Page.enable");
    await S2("Emulation.setDeviceMetricsOverride", { width: 640, height: 360, deviceScaleFactor: 1, mobile: false });
    await S2("Page.addScriptToEvaluateOnNewDocument", { source: STORM_VIRTUAL_CLOCK });
    const ev2 = async (expression) => {
      const r = await S2("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const storms = [];
    const D2 = [...["invert10", "oneshots15", "oneshots5", "nozoom15", "all12", "flashedge", "flash24", "lasglitch", "lookstorm"].map((s) => [s, "gpu"]),
                ["oneshots15", "cpu"], ["oneshots15", "off"], ["invert10", "off"],
                // Lasers v2 (2026-10-25): pad 2's beams through the beam layer, on Reactor and on the Cathedral (head bus)
                ["lasertiers", "gpu"], ["laserroll", "gpu"], ["lasertiers", "gpu", "vj-laser-cathedral"], ["laserroll", "gpu", "vj-laser-cathedral"]];
    for (const [scenario, mode, stormSet = "vj-reactor"] of D2) {
      const q = mode === "cpu" ? "&limiter=cpu" : mode === "off" ? "&limiter=off" : "";
      await S2("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=off&hud=0&watchdog=0&sets=${stormSet}&laserseed=11${q}` });
      const want = mode === "off" ? "true" : `l.mode === "${mode}"`;
      await waitFor(() => ev2(`!!(window.__vj && window.__vj.ready) && (() => { window.__vt.step(1000 / 60); const l = window.__vj.stats().limiter; return !l || ${want} || l.fatal; })()`), 120000, "the storm tab's VJ page and gate v2");
      await ev2("(() => { for (let i = 0; i < 30; i++) window.__vt.step(1000 / 60); return true; })()");
      const r = await runStormInPage(ev2, scenario, /^laser/.test(scenario) ? 480 : 240, { mode });
      storms.push({ ...r, set: stormSet, densest: r.densest.slice(0, 8) });
      console.log(`[storm] ${mode} ${scenario}: worst ${r.max_flashes_in_1s}/s pairs ${r.max_pairs_in_1s} (${r.worst_window}), full ${r.full_max_flashes_in_1s}/s, red ${r.red_max_flashes_in_1s}, gate ${r.gate.granted}, hits ${r.impact_hits}, refused ${r.safe_refused}, limiter ${r.limiter && r.limiter.on ? `${r.limiter.mode} leaks ${r.limiter.leaks}` : "off"}`);
    }
    await browser.send("Target.closeTarget", { targetId: t2 });
    report.flash.storms = storms;
    checks.pad_storms_at_most_three_flashes_a_second_in_every_window = storms.length === D2.length &&
      storms.every((r) => r.max_transitions_in_1s <= 6 && r.max_pairs_in_1s <= 3 && r.red_max_transitions_in_1s <= 6 && r.red_max_pairs_in_1s <= 3 && r.longest_run_s <= 6.2);
    checks.gate_v2_limiter_running_without_leaks = storms.filter((r) => r.mode !== "off").every((r) => r.limiter && r.limiter.on && r.limiter.mode === r.mode && r.limiter.leaks === 0);
    checks.storms_keep_their_hits = storms.filter((r) => r.mode !== "off" && /oneshots|nozoom|all12|invert/.test(r.scenario)).every((r) => r.impact_hits >= 20);
    checks.the_safe_mode_refuses_every_pad_effect = storms.filter((r) => r.mode === "off").every((r) => r.mode_ok && r.impact_hits === 0 && r.safe_refused > 20);
    // the laser storms really played the lasers (their hits and pulses), and the laser engine never sent a frame over its
    // own flash budget (its change estimate); gate v2 then judged the final frame like every other storm above
    const laserStorms = storms.filter((r) => /^laser/.test(r.scenario));
    report.flash.laser_storms = laserStorms.map((r) => ({ scenario: r.scenario, set: r.set, worst: r.max_flashes_in_1s, pairs: r.max_pairs_in_1s,
      red: r.red_max_flashes_in_1s, lasers: r.lasers, limiter: r.limiter }));
    checks.laser_storms_play_the_lasers_within_their_budget = laserStorms.length === 4 && laserStorms.every((r) => r.lasers &&
      r.lasers.mode === "v2" && r.lasers.hits >= 4 && r.lasers.pulses >= 6 && r.lasers.lit_frames >= 30 && r.lasers.over_frames === 0);
  }
  await tap("H");                        // the HUD, once, for the record
  await delay(300);
  report.hud_screenshot = await shot("hud");
  await tap("H");

  // ------------------------------------------------- L: Lasers v2 and the colour themes (a 60 fps virtual clock) --
  // A tab on the storm receipt's virtual clock, fed the engine's beats (120 BPM, 220 ms ahead, bar 1-4 as the engine
  // sends with --tap-one) through the test hook, so every pulse's frame is exact. Pad 2 at soft / medium / hard (each
  // pressed 40 ms before a beat, a hand a little early, more than a bar apart): the gate the velocity tier picks, the
  // pulses it fires, each pulse's picture against the beat grid (the engine lights a pulse in the frame whose picture,
  // one frame on, lands at or just before its grid point), and the beam layer's own pixels read back. The dial (cc116)
  // and its click (cc117); fader 1 (cc105); a hello naming the tap controls with pad 12 pressed on the DAW port; the
  // Laser Cathedral's head bus; the pad lights posted.
  {
    const { targetId: t3 } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId: s3 } = await browser.send("Target.attachToTarget", { targetId: t3, flatten: true });
    const S3 = (method, params = {}) => withTimeout(browser.send(method, params, s3), 600000, method);
    browser.on((msg) => {
      if (msg.sessionId !== s3 || msg.method !== "Runtime.exceptionThrown") return;
      const d = msg.params.exceptionDetails;
      report.exceptions.push({ text: d.text, description: d.exception?.description, line: d.lineNumber, url: d.url, tab: "lasers" });
    });
    await S3("Runtime.enable"); await S3("Page.enable");
    await S3("Emulation.setDeviceMetricsOverride", { width: 640, height: 360, deviceScaleFactor: 1, mobile: false });
    await S3("Page.addScriptToEvaluateOnNewDocument", { source: STORM_VIRTUAL_CLOCK });
    const ev3 = async (expression) => {
      const r = await S3("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    await S3("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=off&hud=0&watchdog=0&sets=vj-reactor,vj-laser-cathedral&laserseed=7&theme=night-sea` });
    await waitFor(() => ev3(`!!(window.__vj && window.__vj.ready) && (() => { window.__vt.step(1000 / 60); const l = window.__vj.stats().limiter; return l.mode === "gpu" || l.fatal; })()`), 180000, "the lasers tab's VJ page and gate v2");
    report.lasers = await ev3(String.raw`(() => {
      const vj = window.__vj, F = 1000 / 60, per = 500;
      let n = 0, next = performance.now() + 150;
      const feed = () => { while (performance.now() + 220 >= next) { vj.event({ t: "beat", due_ms: next - performance.now(), bpm: 120, conf: 0.9, n, on_beat: 0.9, src: "track", bar: (n % 4) + 1, ver: 1, wall_ms: 0 }); n++; next += per; } };
      const step = (k, each) => { for (let i = 0; i < k; i++) { feed(); window.__vt.step(F); if (each) each(i); } };
      const st = () => vj.stats();
      const ctl = (id, value, kind = "abs", delta = 0) => vj.event({ t: "ctl", id, kind, value, delta, port: "daw" });
      const out = { tiers: [], dial: {}, theme: {}, tap: {}, cathedral: {}, leds: {} };
      step(150);                                       // the grid settles: the engine's beats for 2.5 s
      // one bank for the tier presses: in "call" mode bank B answers every pulse half a beat later (more pulses, off the
      // gate's own grid by design), which the engine's own tests cover; here each hit's gate is counted and timed alone
      vj.laser({ bank: "A" });
      // to just before a beat: the next whole beat of the page grid 40 ms (a hand a little early) after the press
      const toBeat = () => { for (let g = 0; g < 60; g++) { const p = st().clock.pos; if (p !== null) { const left = (Math.ceil(p) - p) * per; if (left >= 40 && left < 40 + F) return left; } step(1); } return null; };
      // pad 2 at the three velocity tiers, each a burst (more than a bar after the last press)
      for (const vel of [0.3, 0.6, 0.95]) {
        step(240);
        const lead = toBeat();
        const p0 = st().lasers.pulses;
        vj.press(2, vel);
        const pulses = [], lit = [];
        let maxLit = 0, maxBeamRecords = 0;
        step(36, (i) => {
          if (i === 2) vj.release(2);                  // a tap (held for half a beat it would run the section's loop)
          const s = st();
          if (s.lasers.pulses > p0 + pulses.length) {
            // this frame lit a pulse: its picture lands one frame on (judged against the gate's grid below)
            pulses.push({ pos: +s.clock.pos.toFixed(5), present: +(s.clock.pos + F / per).toFixed(5), n: s.lasers.pulses - p0 });
          }
          const b = vj.beams();
          if (b && b.lit > maxLit) { maxLit = b.lit; maxBeamRecords = b.records; }
        });
        const last = st().lasers.last;
        out.tiers.push({ vel, lead_ms: lead, gate: last.gate, tier: last.tier, pattern: last.pattern, pulses: st().lasers.pulses - p0,
                         pulse_frames: pulses, beam_pixels_lit: maxLit, beam_records: maxBeamRecords });
      }
      vj.laser({ bank: "auto" });
      // the dial: one detent to Single, two more to Triple; a hard press then fires the dial's gate; the click is AUTO
      step(240);
      ctl("cc116", 0.5, "rel", 1); step(6);
      out.dial.after_one = st().lasers.gate;
      ctl("cc116", 0.5, "rel", 1); step(6); ctl("cc116", 0.5, "rel", 1); step(6);
      out.dial.after_three = st().lasers.gate;
      vj.press(2, 0.3); step(4); vj.release(2);
      out.dial.soft_hit_gate = st().lasers.last.gate;
      step(240);
      ctl("cc117", 1); step(2); ctl("cc117", 0); step(4);
      out.dial.after_click = st().lasers.gate;
      vj.press(2, 0.3); step(4); vj.release(2);
      out.dial.soft_hit_after_click = st().lasers.last.gate;
      // fader 1: a theme from the other side of the wheel; it lands on the next bar, the lasers take its colours
      step(120);
      const t0 = st().themes;
      vj.event({ t: "ctl", id: "cc105", kind: "abs", value: 0.81, delta: 0, port: "daw" });
      let pend = null, pendFrames = 0;
      step(200, () => { const p = st().themes.pending; if (p) { pend = pend || p; pendFrames++; } });
      const t1 = st().themes, l1 = st().lasers;
      out.theme = { from: t0.current, fader: t1.fader, fader_theme: t1.faderTheme, pending_seen: pend, pending_frames: pendFrames, to: t1.current, changes: t1.changes - t0.changes,
                    landed_on: t1.last ? t1.last.on : null, lasers_theme: l1.theme, palette_moved: t1.palette.some((v, i) => Math.abs(v - t0.palette[i]) > 0.02) };
      // the tap: the engine's hello names the Tap button and pad 12; pad 12 pressed on the DAW port fires nothing
      vj.event({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", chords: "blend", pads_mode: "both", leds: false, leds_reason: "receipt",
                 tap: "daw:cc23,daw:pad12", tap_one: true });
      step(2);
      const before = st();
      vj.event({ t: "pad", pad: 12, vel: 0.9, on: true, src: "daw" }); step(3);
      const during = st();
      vj.event({ t: "pad", pad: 12, vel: 0, on: false, src: "daw" }); step(2);
      vj.event({ t: "tap", count: 1, mode: "resync", bpm: null, shift: 0.0 }); step(2);
      const after = st();
      out.tap = { pads: after.tap.pads, presses: after.tap.presses - before.tap.presses, zoom: during.effects.filter((e) => e.type === "zoom").length,
                  impact_hits: during.impact.hits - before.impact.hits, last: after.tap.last };
      vj.event({ t: "pad", pad: 12, vel: 0.9, on: true, src: "bank" }); step(3);
      out.tap.bank_pad_12_zoom = st().effects.filter((e) => e.type === "zoom").length;
      vj.event({ t: "pad", pad: 12, vel: 0, on: false, src: "bank" }); step(30);
      // the Laser Cathedral: its heads from the head bus, the hero's beams from the beam layer
      vj.select("vj-laser-cathedral"); step(60);
      vj.laser({ gate: "triple" });
      vj.press(2, 0.95);
      let busPeak = 0, heroOnly = false, busOn = false, rec = 0, upl = 0;
      step(24, () => { const s = st().lasers; heroOnly = heroOnly || s.heroOnly; busOn = busOn || s.busOn;
        if (s.bus) busPeak = Math.max(busPeak, ...s.bus.slice(4, 16).map((v) => v - Math.floor(v))); rec = Math.max(rec, s.records); upl = Math.max(upl, s.uploaded); });
      vj.release(2); vj.laser({ gate: "auto" });
      out.cathedral = { heroOnly, busOn, bus_peak_level: +busPeak.toFixed(3), records_max: rec, uploaded_max: upl };
      const s9 = st();
      out.leds = { last: s9.leds.last, washed: s9.ledsWashed };
      out.errors = vj.errors();
      out.limiter = s9.limiter.mode;
      return out;
    })()`);
    await S3("Page.captureScreenshot", { format: "png" }).then((r) => { const f = join(outDir, "lasers-cathedral.png"); writeFileSync(f, Buffer.from(r.data, "base64")); report.screenshots.push(f); });
    await browser.send("Target.closeTarget", { targetId: t3 });
    const Lr = report.lasers;
    const pulsesOf = { single: 1, onetwo: 2, triple: 3, triplet: 3 };
    // Each pulse's PICTURE against its gate's grid (a quarter beat; a third for the Triplet Triple): the engine lights a
    // pulse in the last frame whose picture lands at or before its grid point, so 0 to one frame early.
    const gridOf = { single: 1 / 4, onetwo: 1 / 4, triple: 1 / 4, triplet: 1 / 3 };
    // Snap to the NEAREST grid point and keep the sign, and record which grid point it was. The first version snapped
    // with Math.ceil(present / g - 1e-6), which can only answer "on the grid" or "a whole grid step early": a pulse that
    // lands a rounding error PAST its grid point was charged a full step, so the Triplet's third shot -- reading
    // present 33.66667 against a grid point of 101/3 = 33.666666..., 1.7 microseconds of error -- came back as 166.66 ms
    // early and failed the round. Nearest-point snapping measures the real error with its sign; the grid INDEX is then
    // checked separately for consecutiveness, which is what actually catches a skipped or repeated grid step.
    const snapPulses = (pulses, g, per = 500) => pulses.map((p) => {
      const k = Math.round(p.present / g);
      return { ...p, grid_k: k, early_ms: +((k * g - p.present) * per).toFixed(2) };  // > 0 early, < 0 late
    });
    // Calibrate the snapper on synthetic pulse sets whose answer is known, so the tolerance below cannot quietly widen
    // into "anything passes". Runs every time; a throw here means the ruler, not the engine, needs looking at.
    const snapSelftest = () => {
      const g = 1 / 3, k0 = 99;
      const onGrid = [0, 1, 2].map((i) => ({ present: +(k0 + i) / 3 + (i === 2 ? 3.3e-6 : 0) }));  // incl. the rounding case
      const skipped = [0, 1, 3].map((i) => ({ present: +(k0 + i) / 3 }));
      const a = snapPulses(onGrid, g), b = snapPulses(skipped, g);
      const okA = a.every((p) => Math.abs(p.early_ms) < 1) && a.every((p, i) => i === 0 || p.grid_k === a[i - 1].grid_k + 1);
      const okB = b.every((p) => Math.abs(p.early_ms) < 1) && !b.every((p, i) => i === 0 || p.grid_k === b[i - 1].grid_k + 1);
      if (!okA || !okB) throw new Error(`grid snap selftest failed: on-grid ${JSON.stringify(a)} skipped ${JSON.stringify(b)}`);
      return true;
    };
    snapSelftest();
    for (const t of Lr.tiers) {
      const g = gridOf[t.gate] || 1 / 4;
      t.pulse_frames = snapPulses(t.pulse_frames, g);
      t.consecutive = t.pulse_frames.every((p, i) => i === 0 || p.grid_k === t.pulse_frames[i - 1].grid_k + 1);
    }
    console.log(`[lasers] tiers ${Lr.tiers.map((t) => `${t.vel}:${t.gate}x${t.pulses} lit ${t.beam_pixels_lit}px early ${t.pulse_frames.map((p) => p.early_ms).join("/")}${t.consecutive ? "" : " NONCONSECUTIVE"}`).join(" | ")}; dial ${Lr.dial.after_one}/${Lr.dial.after_three}/${Lr.dial.after_click}; theme ${Lr.theme.from} -> ${Lr.theme.to} (${Lr.theme.landed_on}); tap ${Lr.tap.presses} press, zoom ${Lr.tap.zoom}; cathedral bus ${Lr.cathedral.bus_peak_level}`);
    // Half a frame late is allowed by spec 3.3; more than one frame early is not on the grid at all.
    const onGrid = (t) => t.pulse_frames.length === t.pulses && t.consecutive &&
      t.pulse_frames.every((p) => p.early_ms >= -1000 / 120 && p.early_ms <= 1000 / 60 + 0.5);
    checks.pad_2_draws_lasers_v2_beams_on_the_grid_with_the_three_tiers = Lr.tiers.length === 3 &&
      Lr.tiers[0].gate === "single" && Lr.tiers[1].gate === "onetwo" && ["triple", "triplet"].includes(Lr.tiers[2].gate) &&
      Lr.tiers.every((t) => t.tier === "burst" && t.pulses === pulsesOf[t.gate] && t.beam_pixels_lit > 50 && onGrid(t));
    checks.the_dial_changes_the_laser_gate = Lr.dial.after_one === "single" && Lr.dial.after_three === "triple" &&
      Lr.dial.soft_hit_gate === "triple" && Lr.dial.after_click === "auto" && Lr.dial.soft_hit_after_click === "single";
    checks.fader_1_changes_the_theme_on_the_bar = Lr.theme.fader_theme === Lr.theme.to && Lr.theme.to !== Lr.theme.from &&
      Lr.theme.changes === 1 && !!Lr.theme.pending_seen && Lr.theme.landed_on === "bar" && Lr.theme.lasers_theme === Lr.theme.to && Lr.theme.palette_moved;
    checks.pad_12_is_the_tap_and_fires_no_effect = Lr.tap.pads.length === 1 && Lr.tap.pads[0].pad === 12 && Lr.tap.presses === 1 &&
      Lr.tap.zoom === 0 && Lr.tap.impact_hits === 0 && Lr.tap.last && Lr.tap.last.mode === "resync" && Lr.tap.bank_pad_12_zoom === 1;
    checks.the_cathedral_draws_its_heads_from_the_head_bus = Lr.cathedral.heroOnly && Lr.cathedral.busOn && Lr.cathedral.bus_peak_level > 0.05 &&
      Lr.cathedral.uploaded_max < Lr.cathedral.records_max;
    report.page_errors = (report.page_errors || []).concat(Lr.errors || []);
  }

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
  const framesAtSend = (await stats()).frames;
  send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "bank" });
  await delay(150);
  // the stars are counted when the page draws a frame: at SwiftShader's 5-10 frames a second, wait for two after the send
  try { await waitFor(async () => (await stats()).frames >= framesAtSend + 2, 5000, "two frames after the events"); } catch { /* judged below */ }
  st = await stats();
  report.engine_contract.after_events = { hello: st.engine.hello, chord: st.chord, stars: st.stars, beats: st.beats, bpm: st.bpm,
                                          effects: st.effects.map((e) => `${e.type}@${e.pad}:${e.vel}`), laser: st.lasers.last };
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
  report.engine_contract.controls = { hueA: st.values.hueA, theme: st.values.theme, sat: st.values.sat, cc120: st.ctlMap.cc120, lastCtl: st.lastCtl };
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
  // pad 2 from the engine plays the laser engine (Lasers v2); fader 1 (cc105) is the theme fader, Hue A untouched
  // (Daniel, 2026-10-25: "3. yes i like that")
  checks.engine_pad_triggers_mapped_effect = !!report.engine_contract.after_events.laser &&
    report.engine_contract.after_events.laser.vel === 0.9 && report.engine_contract.after_events.laser.src === "bank";
  checks.engine_fader_1_is_the_theme_fader = Math.abs(st.values.theme - 0.2) < 1e-6 && Math.abs(st.values.hueA - 0.53) < 1e-6;
  checks.learn_on_touch_binds_any_control = report.engine_contract.panel_open && report.engine_contract.learn_clicked &&
    st.ctlMap.cc120 === "sat" && Math.abs(st.values.sat - 0.4) < 1e-6;
  checks.pad_map_is_editable = report.engine_contract.pad_edit === "invert";
  checks.pad_lights_posted_at_most_ten_a_second = bodyOk && posts.length >= 2 && maxPerSecond <= 10;
  // spec A8: the pads get LED stand-ins (vj-themes.js ledPostedOk: white, or saturated and outside the 15-100 degree wash)
  const { ledPostedOk } = await import("../web/vj-themes.js");
  const posted = posts.flatMap((p) => { try { return JSON.parse(p.body).colors; } catch { return []; } });
  report.engine_contract.pad_colours_checked = posted.length;
  checks.every_pad_light_posted_is_a_stand_in_the_pads_show = posted.length >= 24 && posted.every((c) => ledPostedOk(c));

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

  // ------------------------- E5: scenes from the transport and the dial; the scene told to the engine (2026-10-24) --
  // The KeyLab's rewind (cc25) and fast-forward (cc26) press 127 and release 0; the dial turns cc116 (relative) and clicks
  // cc117. The page maps them to scenes (vj-core.js DEFAULT_CTL_MAP, SceneControl): a press moves one scene, a release
  // or a held button does nothing more, the dial browses (the page tells the engine the scene under it, browsing) and its
  // click goes there, a fast spin cannot run away. The page reports the scene it shows (POST /api/scene); an engine that
  // answers 404 (older than the route) is not asked again until its next hello. Energy at ~100 events a second reaches
  // the page's band envelopes. And pad events from the engine: arrival to the frame that draws them (the latency record).
  {
    const sc = {};
    const ctl = (id, value, kind = "abs", delta = 0) => send({ t: "ctl", id, kind, value, delta });
    const setOf = async () => (await stats()).setA;
    const nextAfter = (list, id, k) => { const i = list.indexOf(id); return list[(((i + k) % list.length) + list.length) % list.length]; };
    const valid = (await evaluate("window.__vj.sets()")).filter((s) => !s.broken).map((s) => s.id);
    sceneMode = "on";
    hello(true);
    sc.reported_on_hello = await settle((s) => s.scenes.sentKey !== "" && scenePosts.some((p) => p.body && p.body.name));
    const waitSet = async (want) => { try { return await waitFor(async () => { const s = await stats(); return !s.fading && s.setA === want ? s : null; }, 7000, want); } catch { return null; } };
    const s0 = await setOf();
    ctl("cc26", 1); await delay(60); ctl("cc26", 0);
    sc.ff = { from: s0, to: (await waitSet(nextAfter(valid, s0, 1)))?.setA ?? (await setOf()) };
    await delay(300);
    sc.release_did_not_move = (await setOf()) === sc.ff.to;
    ctl("cc25", 1); await delay(60); ctl("cc25", 0);
    sc.rew = { to: (await waitSet(s0))?.setA ?? (await setOf()) };
    // a held button (repeating 127) moves once
    const s1 = await setOf();
    for (let i = 0; i < 5; i++) { ctl("cc26", 1); await delay(40); }
    ctl("cc26", 0);
    sc.held = { from: s1, to: (await waitSet(nextAfter(valid, s1, 1)))?.setA ?? (await setOf()) };
    await delay(400);
    sc.held.after = await setOf();
    // the scene dial (learned: since Lasers v2 the main dial picks the laser gate, Daniel 2026-10-25): three detents
    // browse three scenes, the screen is told (browsing), the live set stays until the click
    await evaluate(`window.__vj.learn("sceneDial")`);
    ctl("cc118", 0.5, "rel", 0);
    sc.dial_learned = await settle((s) => s.ctlMap.cc118 === "sceneDial");
    await evaluate(`window.__vj.learn("sceneGo")`);
    ctl("cc119", 0);
    sc.click_learned = await settle((s) => s.ctlMap.cc119 === "sceneGo");
    await delay(200);
    const s2 = await setOf();
    const browsePosts0 = scenePosts.length;
    for (let i = 0; i < 3; i++) { ctl("cc118", 0.5, "rel", 1); await delay(150); }
    const br = await settle((s) => (s.scenes.browsing && s.scenes.cursor >= 0 ? s : false));
    sc.browse = { cursor: br ? br.scenes.cursor : null, live: await setOf(), want: nextAfter(valid, s2, 3) };
    await delay(400);
    const browsePosts = scenePosts.slice(browsePosts0).filter((p) => p.body && p.body.browsing === true);
    sc.browse.posts = browsePosts.map((p) => p.body.name);
    ctl("cc119", 1); await delay(60); ctl("cc119", 0);
    sc.go = { to: (await waitSet(sc.browse.want))?.setA ?? (await setOf()) };
    // a fast spin: 30 messages in ~300 ms move the cursor at most one step per 60 ms
    const spin0 = (await stats()).scenes.ignored;
    for (let i = 0; i < 30; i++) { ctl("cc118", 0.5, "rel", 4); await delay(10); }
    const sp = await settle((s) => (s.scenes.ignored > spin0 ? s : false));
    sc.spin = { ignored: sp ? sp.scenes.ignored - spin0 : 0 };
    await delay(4500);                    // the browse lets go without a click
    sc.spin.browse_ended = !(await stats()).scenes.browsing;
    sc.spin.live_unchanged = (await setOf()) === sc.go.to;
    // an older engine: 404 on the route, asked once, then not again until its next hello
    const old0 = scenePosts.length;
    sceneMode = "absent";
    hello(true);
    await settle((s) => s.scenes.off !== "" || scenePosts.length > old0);
    await delay(300);
    ctl("cc26", 1); await delay(60); ctl("cc26", 0);
    await delay(1500);
    ctl("cc25", 1); await delay(60); ctl("cc25", 0);
    await delay(1500);
    const st5 = await stats();
    sc.older = { posts: scenePosts.slice(old0).filter((p) => p.mode === "absent").length, off: st5.scenes.off };
    sceneMode = "on";
    const res0 = scenePosts.length;
    hello(true);
    sc.older.resumed = await settle((s) => (s.scenes.off === "" && scenePosts.length > res0 ? true : false));
    // energy at ~100 a second
    const e0 = (await stats()).energyEvents;
    // one every 10 ms on the clock (a Windows timer may wake late: every event due by then goes out, as the engine's
    // audio blocks would)
    const eStart = Date.now();
    await new Promise((done) => {
      let k = 0;
      const timer = setInterval(() => {
        while (k < 100 && eStart + k * 10 <= Date.now()) {
          send({ t: "energy", bass: 0.3 + 0.5 * ((k % 50) < 5 ? 1 : 0), mid: 0.3, high: 0.2, level: 0.4 });
          k++;
        }
        if (k >= 100) { clearInterval(timer); done(); }
      }, 4);
    });
    const eSpanMs = Date.now() - eStart;
    await delay(60);
    const se = await stats();                 // at once: the page's count of the last second is the rate
    sc.energy = { sent: 100, over_ms: eSpanMs, received: se.energyEvents - e0, page_rate_last_second: se.energyRate, kick: se.bands.kick };
    // latency: pad events from the engine, each drawn in the next frame at full strength -- measured on the classic burst
    // (Lasers: classic, kept exactly; Lasers v2's first pulse waits for the beat grid when a press is a little early)
    await evaluate("window.__vj.laser({ classic: true })");
    const latT0 = await evaluate("performance.now()");
    const latSent = [];
    for (let i = 0; i < 12; i++) {
      latSent.push(Date.now());
      send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "bank" });
      await delay(50);
      send({ t: "pad", pad: 2, vel: 0, on: false, src: "bank" });
      await delay(180 + (i % 4) * 37);
    }
    await delay(400);
    await evaluate("window.__vj.laser({ classic: false })");
    const lat = (await evaluate("window.__vj.latency()")).records.filter((r) => r.src === "bank" && r.arrive >= latT0);
    // a laser burst at 0.9 starts at full strength (attack 0) and falls (1 - age / D)^2, D = 0.9 s x (0.6 + 0.8 x 0.9):
    // the frame that draws it must show at least that, so nothing between the event and the frame held it back
    const D = 0.9 * (0.6 + 0.8 * 0.9);
    for (const r of lat) r.expected = r.frame === null ? null : +Math.pow(Math.max(0, 1 - (r.frame - r.fired) / 1000 / D), 2).toFixed(3);
    // the engine's send (this process's wall clock) to the end of the frame that drew it (the page's: the same clock)
    const sends = latSent.slice(-lat.length);
    const gaps = lat.map((r, k) => (r.frameWall ? r.frameWall - sends[k] : null)).filter((g) => g !== null).sort((a, b) => a - b);
    const fps = (await stats()).fps;
    sc.latency = { records: lat.length, send_to_drawn_ms: { p50: gaps[Math.floor(gaps.length / 2)] ?? null, max: gaps[gaps.length - 1] ?? null },
                   frame_ms_at_this_rate: fps > 0 ? +(1000 / fps).toFixed(1) : null, env_in_that_frame_min: Math.min(...lat.map((r) => r.env ?? 0)),
                   env_short_of_full_max: Math.max(...lat.map((r) => (r.expected ?? 1) - (r.env ?? 0))) };
    // the beat snap (off by default; B or the panel): with the engine's beat live, a pad hit waits for the next 16th
    let snapN = 0;
    const snapBeats = setInterval(() => send({ t: "beat", due_ms: 200, bpm: 120, conf: 0.9, n: 1000 + snapN++, on_beat: 0.9 }), 500);
    await delay(1300);
    const snapOn = await evaluate("window.__vj.snap(true)");
    const snapT0 = await evaluate("performance.now()");
    for (let i = 0; i < 8; i++) {
      send({ t: "pad", pad: 1, vel: 0.8, on: true, src: "bank" });
      await delay(40);
      send({ t: "pad", pad: 1, vel: 0, on: false, src: "bank" });
      await delay(170 + i * 23);
    }
    await delay(500);
    const snapRecs = (await evaluate("window.__vj.latency()")).records.filter((r) => r.arrive >= snapT0 && r.pad === 1);
    await evaluate("window.__vj.snap(false)");
    clearInterval(snapBeats);
    const onGrid = (r) => { const k = (r.snapAt - r.snapBeat) / r.snapGrid; return Math.abs(k - Math.round(k)) < 0.01; };
    sc.snap = { on: snapOn, hits: snapRecs.length, waited: snapRecs.filter((r) => r.snapAt !== null).length,
                waits_ms: snapRecs.filter((r) => r.snapAt !== null).map((r) => +(r.snapAt - r.arrive).toFixed(1)),
                on_grid: snapRecs.filter((r) => r.snapAt !== null).every(onGrid),
                drawn_after_its_16th: snapRecs.filter((r) => r.snapAt !== null).every((r) => r.frame !== null && r.frame >= r.snapAt) };
    report.engine_contract.scenes = { ...sc, posts: scenePosts.length, sample: scenePosts.slice(-3) };
    console.log(`[scenes] ff ${sc.ff.from} -> ${sc.ff.to}; browse ${sc.browse.posts.join(", ")}; older engine: ${sc.older.posts} post(s); energy ${sc.energy.received} in 1 s; send to drawn p50 ${sc.latency.send_to_drawn_ms.p50} ms at ${sc.latency.frame_ms_at_this_rate} ms a frame`);
    checks.scene_is_reported_to_the_engine = !!sc.reported_on_hello && scenePosts.filter((p) => p.mode === "on").every((p) => p.body && typeof p.body.name === "string" && p.body.name.length >= 1);
    checks.fast_forward_and_rewind_switch_scenes = sc.ff.to === nextAfter(valid, s0, 1) && sc.rew.to === s0 && sc.release_did_not_move;
    checks.a_held_button_switches_once = sc.held.to === nextAfter(valid, s1, 1) && sc.held.after === sc.held.to;
    checks.the_dial_browses_and_its_click_goes = !!sc.dial_learned && !!sc.click_learned && sc.browse.live === s2 &&
      sc.browse.posts.length >= 1 && sc.go.to === sc.browse.want;
    checks.a_fast_spin_cannot_flood = sc.spin.ignored >= 10 && sc.spin.browse_ended && sc.spin.live_unchanged;
    checks.an_older_engine_is_asked_once_until_its_next_hello = sc.older.posts === 1 && /older/.test(sc.older.off) && sc.older.resumed === true;
    checks.energy_at_100_a_second_reaches_the_page = sc.energy.received === 100 && sc.energy.over_ms <= 1150;
    checks.beat_snap_holds_a_hit_to_the_next_16th = sc.snap.on === true && sc.snap.hits === 8 && sc.snap.waited >= 3 &&
      sc.snap.on_grid && sc.snap.drawn_after_its_16th && sc.snap.waits_ms.every((w) => w > 0 && w <= 125 * 0.75 + 1);
    checks.pad_events_drawn_in_the_next_frame_at_full_strength = sc.latency.records >= 10 && lat.every((r) => r.frame !== null) &&
      sc.latency.env_short_of_full_max <= 0.02;
  }

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
    // the page told the real engine which scene shows (POST /api/scene), and the engine keeps it for `screen --live`
    const liveName = await evaluate("(() => { const s = window.__vj.stats(); const x = window.__vj.sets().find((q) => q.id === s.setA); return x ? x.name : null; })()");
    real.scene = { page: liveName, engine: real.state ? real.state.scene : null, counts: real.state ? real.state.scene_counts : null };
    checks.the_real_engine_hears_the_page_scene = !!liveName && !!real.scene.engine && real.scene.engine.name === liveName &&
      real.scene.counts.taken >= 1;
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
  // ... and phase E5's older engine answers 404 to the scene route: exactly one report, then the page stops asking it
  const sceneAbsent = (c) => /\/api\/scene/.test(c.url || "") && /\b404\b/.test(c.text || "");
  report.expected_scene_404 = report.console.filter(sceneAbsent);
  checks.scene_404_console_lines_match_the_older_engine_posts = report.expected_scene_404.length === scenePosts.filter((p) => p.mode !== "on").length;
  checks.no_console_errors = !report.console.some((c) => (c.type === "error" || c.type === "log-error") && !external(c) &&
    !refusal(c) && !sceneAbsent(c));
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
    console.log(report.expected_refusals?.includes(c) ? "CONSOLE (expected: the refusal phase E2 provokes)" :
      report.expected_scene_404?.includes(c) ? "CONSOLE (expected: E5's older engine has no scene route)" : "CONSOLE", c.text);
  }
  console.log("verdict:", report.verdict.pass ? "PASS" : "FAIL");
  console.log("receipt:", join(outDir, "receipt.json"));
  process.exit(report.verdict.pass ? 0 : 1);
}
