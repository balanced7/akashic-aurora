// Receipt: the KeyLab drives a shader. A fader event from the VJ engine changes a uniform on the GPU and the frame on
// the canvas, in a private headless Chrome forced onto SwiftShader (the CPU), against a FAKE engine. No keyboard, no
// real engine, no port 8793.
//
//   node arsenal/lanes/keylab_desk_verify.mjs [--port 8931] [--keep-chrome-log]
//
// What it stands up (all on 127.0.0.1, test band 89xx):
//   - a static server for THIS checkout's arsenal/web at /web/ plus GET /api/presets (the list presets.py makes, from
//     the same `//! {json}` header lines), so the page under test is the code in this tree, not Daniel's live server;
//   - a fake VJ engine: GET /api/events is an SSE stream with CORS, the contract of arsenal/keylab/vj.py
//     (hello, ctl, pad, chord, beat ...), and this script writes the events into it.
// Then it opens /web/shader-desk.html?keylab=<fake>&preset=aurora-ribbons&freeze=2 and walks the steps below, reading
// each uniform back with gl.getUniform (what the GPU holds, not what the page meant to set) and hashing the canvas.
//
// GPU lock (arsenal/GPU-LOCK.md): Chrome starts only under state/arsenal/gpu-render.lock, the burst stays under 3
// minutes, and the browser is refused unless its WebGL renderer names SwiftShader and no hardware (judgeRenderer).
// Writes state/arsenal/keylab/receipts/desk-verify-<stamp>.json and two PNGs; exits 1 when a step fails.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock } from "./gpu_lock.mjs";
import { CHROME_EXE, GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const WEB = join(REPO, "arsenal", "web");
// The GPU lock is machine-wide: from a git worktree it must be the MAIN checkout's lock, or this run and a lane in the
// main checkout would each hold "the" lock at once (gpu_lock.mjs resolves its default against its own checkout).
function mainCheckout() {
  try {
    const r = spawnSync("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"], { cwd: REPO, encoding: "utf8", windowsHide: true });
    const common = (r.stdout || "").trim();
    if (r.status === 0 && common) return resolve(common, "..");
  } catch { /* not a git checkout */ }
  return REPO;
}
const LOCK_DIR = join(mainCheckout(), "state", "arsenal", "gpu-render.lock");
const { values: opt } = parseArgs({ options: {
  port: { type: "string", default: "8931" },
  out: { type: "string", default: join(REPO, "state", "arsenal", "keylab", "receipts") },
  "gpu-wait-min": { type: "string", default: "3" },
} });
const BASE_PORT = Number(opt.port);
if (!(BASE_PORT >= 8900 && BASE_PORT <= 8998)) { console.log("ERROR --port must be in the test band 8900-8998"); process.exit(2); }
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
mkdirSync(opt.out, { recursive: true });
const receipt = { api: "arsenal.receipt/v0", title: "KeyLab fader -> shader uniform -> frame (headless, SwiftShader, fake engine)",
  started_at: new Date().toISOString(), steps: [], console: [], verdict: null,
  not_measured: ["the real KeyLab (no device is touched)", "the real VJ engine (a fake one speaks its contract)",
    "Web MIDI (headless Chrome has no MIDI devices)", "frame rate on Daniel's GPU (this is SwiftShader)"] };
let failed = 0;
const step = (name, ok, data = {}) => {
  receipt.steps.push({ name, ok, ...data });
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${Object.keys(data).length ? " " + JSON.stringify(data) : ""}`);
};

// ------------------------------------------------------------------------------------------- the servers --
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json", ".frag": "text/plain; charset=utf-8", ".glsl": "text/plain; charset=utf-8" };
function presetList() {
  const dir = join(WEB, "presets");
  return readdirSync(dir).filter((f) => f.endsWith(".frag")).sort().map((file) => {
    const text = readFileSync(join(dir, file), "utf8");
    const line = text.split(/\r?\n/)[1] || "";
    let h = {};
    try { h = JSON.parse(line.slice(3)); } catch { /* listed with a problem */ }
    const id = file.replace(/\.frag$/, "");
    return { id, file, url: `/web/presets/${file}`, name: h.name || id, author: h.author || "", tags: h.tags || [], params: h.params || [], problems: [] };
  });
}
function staticServer() {
  return createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    if (url.pathname === "/api/presets") {
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      return res.end(JSON.stringify({ presets: presetList() }));
    }
    if (!url.pathname.startsWith("/web/")) { res.writeHead(404); return res.end("not found"); }
    const file = normalize(join(WEB, decodeURIComponent(url.pathname.slice(5))));
    if (!file.startsWith(WEB + sep)) { res.writeHead(404); return res.end("not found"); }
    let body;
    try { if (!statSync(file).isFile()) throw new Error("dir"); body = readFileSync(file); } catch { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(body);
  });
}
const sse = new Set();
function fakeEngine() {
  return createServer((req, res) => {
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Private-Network": "true" };
    if (req.method === "OPTIONS") { res.writeHead(204, { ...cors, "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" }); return res.end(); }
    const url = new URL(req.url, "http://x");
    if (url.pathname === "/api/events") {
      res.writeHead(200, { ...cors, "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive" });
      res.write("retry: 1000\n\n");
      res.write(`data: ${JSON.stringify({ t: "hello", v: 1, src: "keylab-vj-fake", beat_engine: "none", pads_mode: "both" })}\n\n`);
      sse.add(res);
      req.on("close", () => sse.delete(res));
      return;
    }
    if (url.pathname === "/api/pads" && req.method === "POST") {   // the desk may ask for pad colours: count, light nothing
      receipt.pad_posts = (receipt.pad_posts || 0) + 1;
      res.writeHead(200, { ...cors, "Content-Type": "application/json" }); return res.end('{"ok":true}');
    }
    res.writeHead(404, cors); res.end();
  });
}
const send = (evt) => { for (const res of sse) res.write(`data: ${JSON.stringify(evt)}\n\n`); };
const fader = (n, value, port = "daw") => send({ t: "ctl", id: `cc${(port === "daw" ? [105, 106, 107, 108, 109, 110, 111, 112, 113] : [73, 75, 79, 72, 80, 81, 82, 83, 85])[n - 1]}`, kind: "abs", value, delta: 0, port, ch: 1 });
const knob = (n, delta) => send({ t: "ctl", id: `cc${[91, 92, 94, 95, 96, 97, 102, 103, 104][n - 1]}`, kind: "rel", value: 0.5, delta, port: "daw", ch: 1 });
const listen = (server, port) => new Promise((res, rej) => { server.once("error", rej); server.listen(port, "127.0.0.1", () => res(port)); });
async function listenInBand(server, start) {
  for (let p = start; p <= 8999; p++) { if (p === 8793) continue; try { return await listen(server, p); } catch (e) { if (e.code !== "EADDRINUSE") throw e; } }
  throw new Error("no free port in the test band");
}

// ------------------------------------------------------------------------------------------- DevTools --
function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map(), listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result); }
      else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onclose = () => { for (const { rej } of pending.values()) rej(new Error("DevTools socket closed")); pending.clear(); };
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const n = ++id; pending.set(n, { res, rej }); ws.send(JSON.stringify({ id: n, method, params })); }),
      on: (fn) => listeners.push(fn), close: () => { try { ws.close(); } catch { /* closed */ } },
    });
  });
}
const withTimeout = (p, ms, what) => Promise.race([p, delay(ms).then(() => { throw new Error(`timed out: ${what}`); })]);

// ------------------------------------------------------------------------------------------- the run --
const servers = [];
let proc = null, profile = null, page = null, gpu = null;
async function cleanup() {
  try { page?.close(); } catch { /* */ }
  if (proc && proc.exitCode === null) {
    try { spawnSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true }); } catch { /* */ }
    await delay(800);
  }
  if (profile) { try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 }); } catch { /* */ } }
  for (const s of sse) { try { s.end(); } catch { /* */ } }
  for (const s of servers) { try { s.closeAllConnections?.(); s.close(); } catch { /* */ } }
  try { gpu?.release(); } catch { /* */ }
}
process.once("SIGINT", async () => { await cleanup(); process.exit(1); });

try {
  const web = staticServer(), eng = fakeEngine();
  servers.push(web, eng);
  const webPort = await listenInBand(web, BASE_PORT);
  const engPort = await listenInBand(eng, webPort + 1);
  receipt.ports = { web: webPort, engine: engPort };

  gpu = await acquireGpuLock({ dir: LOCK_DIR, label: "keylab_desk_verify", maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, maxHoldMs: 4 * 60_000 });
  receipt.gpu_lock = { dir: LOCK_DIR, acquired_at: gpu.owner?.acquiredAt ?? null, inherited: !!gpu.inherited };
  const t0 = Date.now();
  profile = join(REPO, "state", "arsenal", "keylab", "chrome-profile", `desk-${stamp}-${process.pid}`);
  mkdirSync(profile, { recursive: true });
  proc = spawn(CHROME_EXE, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0",
    `--user-data-dir=${profile}`, "--window-size=1280,720", "about:blank"], { stdio: "ignore", windowsHide: true });
  let dport = null, dpath = null;
  while (Date.now() - t0 < 20_000 && !dport) {
    try { const [p, w] = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split(/\r?\n/); if (p && w) { dport = Number(p); dpath = w; } } catch { /* not yet */ }
    if (!dport) await delay(60);
  }
  if (!dport) throw new Error("Chrome wrote no DevToolsActivePort");
  const browser = await connect(`ws://127.0.0.1:${dport}${dpath}`);
  receipt.chrome = (await browser.send("Browser.getVersion")).product;
  const target = (await (await fetch(`http://127.0.0.1:${dport}/json/list`)).json()).find((t) => t.type === "page");
  page = await connect(target.webSocketDebuggerUrl);
  page.on((m) => {
    if (m.method === "Runtime.exceptionThrown") receipt.console.push({ type: "exception", text: String(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 400) });
    if (m.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(m.params.type)) receipt.console.push({ type: m.params.type, text: m.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
  });
  for (const d of ["Runtime", "Page", "Network"]) await page.send(`${d}.enable`);
  // Fonts come from Google: not needed for the check, and a slow network must not hold the page's stylesheet.
  await page.send("Network.setBlockedURLs", { urls: ["*fonts.googleapis.com*", "*fonts.gstatic.com*"] });
  await page.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  const evaluate = async (expr, ms = 10_000) => {
    const r = await withTimeout(page.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }), ms, expr.slice(0, 80));
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const waitFor = async (expr, ms, what) => {
    const end = Date.now() + ms;
    for (;;) { let v = null; try { v = await evaluate(expr); } catch { /* page loading */ } if (v) return v; if (Date.now() > end) throw new Error(`timed out waiting for ${what}`); await delay(100); }
  };
  const shot = async (name) => {
    const { data } = await page.send("Page.captureScreenshot", { format: "png" });
    const file = join(opt.out, `desk-verify-${stamp}-${name}.png`);
    writeFileSync(file, Buffer.from(data, "base64"));
    return file;
  };

  const url = `http://127.0.0.1:${webPort}/web/shader-desk.html?keylab=${encodeURIComponent(`http://127.0.0.1:${engPort}/api/events`)}&preset=aurora-ribbons&freeze=2&scale=0.5`;
  receipt.url = url;
  await page.send("Page.navigate", { url });
  await waitFor("window.__desk && window.__desk.ready()", 30_000, "the desk to load its presets");
  const stats = await evaluate("__desk.stats()");
  const judged = judgeRenderer(stats.renderer);
  step("the page's WebGL renderer is SwiftShader (no hardware)", judged.ok, { renderer: stats.renderer, reason: judged.reason });
  if (!judged.ok) throw new Error("refusing to go on: not SwiftShader");
  const scenes = await evaluate("__desk.scenes()");
  step("Play's presets compiled", scenes.filter((s) => s.ok).length >= 6, { ok: scenes.filter((s) => s.ok).map((s) => s.id), broken: scenes.filter((s) => !s.ok).map((s) => `${s.id}: ${s.log}`.slice(0, 160)) });
  step("the desk opened aurora-ribbons", (await evaluate("__desk.active()")) === "aurora-ribbons");
  await waitFor("__desk.keylab().source === 'engine'", 10_000, "the fake engine to be the KeyLab source");
  step("the KeyLab source is the (fake) VJ engine", true, { status: await evaluate("(({source, engine, url}) => ({source, engine, url}))(__desk.keylab())") });

  // the engine's energy bands, steady, so the picture is lit and the audio texture is the engine's (not silence)
  const ENERGY = { t: "energy", bass: 0.7, mid: 0.55, high: 0.4, level: 0.6 };
  send(ENERGY);
  const energyTimer = setInterval(() => send(ENERGY), 250);
  const u = (name) => evaluate(`__desk.uniform(${JSON.stringify(name)})`);
  const gridDiff = (a, b) => {
    const d = a.grid.map((x, i) => Math.abs(x - b.grid[i]));
    return { mean_abs_luma: Math.round((d.reduce((s, x) => s + x, 0) / d.length) * 100) / 100,
      cells_changed_over_2: Math.round((d.filter((x) => x > 2).length / d.length) * 1000) / 10 + "%", max: Math.round(Math.max(...d) * 10) / 10 };
  };
  const brief = (f) => ({ hash: f.hash, mean: f.mean, w: f.w, h: f.h });
  const still = () => evaluate("__desk.still({ time: 2, frames: 1 })");
  const settle = (ms = 400) => delay(ms);
  await settle(300);
  const k1Before = await u("u_k1");
  const before = await still();
  const pngBefore = await shot("before");
  step("before: u_k1 holds the preset's default (flow 0.5)", Math.abs(k1Before - 0.5) < 1e-6, { u_k1: k1Before, frame: brief(before), audio: (await evaluate("__desk.stats()")).audio });

  // pickup: the fader starts at the bottom, far from 0.5 -- nothing may move
  fader(1, 0.0); await settle();
  const k1Pending = await u("u_k1");
  const readPending = await evaluate("__desk.readout()");
  step("pickup: fader 1 at 0.0 does not grab flow (still 0.5)", Math.abs(k1Pending - 0.5) < 1e-6 && !!readPending?.pending,
    { u_k1: k1Pending, readout: readPending && { label: readPending.label, pending: readPending.pending } });
  const samePending = await still();
  step("pickup: the frame is unchanged", samePending.hash === before.hash, { before: before.hash, now: samePending.hash, diff: gridDiff(before, samePending) });

  // sweep the fader up through 0.5 to the top
  for (const v of [0.15, 0.3, 0.45, 0.55, 0.7, 0.85, 1.0]) { fader(1, v); await delay(40); }
  await settle(700);
  const k1After = await u("u_k1");
  step("fader 1 passed 0.5, caught it, and drove u_k1 to 1.0 (read back from the GPU)", Math.abs(k1After - 1.0) < 1e-3, { u_k1: k1After });
  const after = await still();
  const pngAfter = await shot("after");
  const diff = gridDiff(before, after);
  step("the rendered frame changed", after.hash !== before.hash && diff.mean_abs_luma > 0.5, { before: brief(before), after: brief(after), diff });
  receipt.pngs = [pngBefore, pngAfter];

  // a relative knob trims it finely: -64 ticks of 384
  knob(1, -64); await settle(700);
  const k1Knob = await u("u_k1");
  step("knob 1 (relative, fine) trims u_k1 by 64/384", Math.abs(k1Knob - (1 - 64 / 384)) < 2e-3, { u_k1: k1Knob, want: 1 - 64 / 384 });

  // fader 9 = intensity, with pickup from 0.8
  fader(9, 0.95); await settle(200);
  const i1 = await u("u_intensity");
  for (const v of [0.85, 0.75, 0.5, 0.3]) { fader(9, v); await delay(40); }
  await settle(700);
  const i2 = await u("u_intensity");
  step("fader 9 drives u_intensity after pickup (0.8 -> 0.3)", Math.abs(i1 - 0.8) < 1e-6 && Math.abs(i2 - 0.3) < 2e-3, { first: i1, after: i2 });

  // the chord root turns the hue round the circle of fifths: G = 30 degrees
  send({ t: "chord", src: "keys", name: "G", root: 7, quality: "maj", pcs: [2, 7, 11], changed: true });
  await settle(2000);
  const hue = await u("u_hue");
  step("a G chord puts u_hue at 30 degrees (one fifth round)", Math.abs(hue - 30) < 0.5, { u_hue: hue });

  // learn: k3 (spread) to fader 7, by moving it
  await evaluate("__desk.learn('k3')");
  fader(7, 0.12); await settle(200);
  const b = await evaluate("__desk.bindings().params.find((p) => p.id === 'k3').controls");
  step("learn: moving fader 7 binds it to the third parameter", b.some((c) => c.control === "fader7" && c.how === "learned"), { controls: b });
  const k3Learn = await u("u_k3");
  step("learn: the binding move does not fire (u_k3 stays 0.5)", Math.abs(k3Learn - 0.5) < 1e-6, { u_k3: k3Learn });
  for (const v of [0.3, 0.45, 0.55, 0.9]) { fader(7, v); await delay(40); }
  await settle(700);
  const k3Moved = await u("u_k3");
  step("the learned fader drives u_k3 after pickup", Math.abs(k3Moved - 0.9) < 2e-3, { u_k3: k3Moved });
  // a finding, not a failure: knobs the compiled shader never reads
  const live = await evaluate("__desk.renderer.info('aurora-ribbons').live");
  receipt.findings = receipt.findings || [];
  live.forEach((on, i) => { if (!on && i < 5) receipt.findings.push(`aurora-ribbons declares k${i + 1} but the compiled shader never reads u_k${i + 1}: that knob does nothing`); });

  // snapshot: hold pad 9 to store, move the knob, tap pad 9 to glide back
  send({ t: "pad", pad: 9, vel: 0.6, on: true, src: "daw" }); await delay(800); send({ t: "pad", pad: 9, vel: 0, on: false, src: "daw" });
  await settle(200);
  knob(1, 120); await settle(700);
  const k1Moved = await u("u_k1");
  send({ t: "pad", pad: 9, vel: 0.6, on: true, src: "daw" }); await delay(60); send({ t: "pad", pad: 9, vel: 0, on: false, src: "daw" });
  await settle(1500);
  const k1Recalled = await u("u_k1");
  step("snapshot A: hold pad 9 stores, a tap glides back", Math.abs(k1Moved - k1Knob) > 0.1 && Math.abs(k1Recalled - k1Knob) < 2e-3, { stored: k1Knob, moved: k1Moved, recalled: k1Recalled });

  // pad 2 switches the scene
  const second = scenes.filter((s) => s.ok)[1].id;
  send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "daw" }); send({ t: "pad", pad: 2, vel: 0, on: false, src: "daw" });
  await settle(900);
  step("pad 2 switches to the second scene", (await evaluate("__desk.active()")) === second, { want: second });

  clearInterval(energyTimer);
  receipt.console_errors = receipt.console.filter((c) => c.type === "exception" || c.type === "error").length;
  step("no page exceptions or console errors", receipt.console_errors === 0, { console: receipt.console.slice(0, 5) });
  receipt.elapsed_ms = Date.now() - t0;
} catch (err) {
  step("run", false, { error: String(err && err.stack || err).slice(0, 800) });
} finally {
  await cleanup();
}
receipt.verdict = failed ? "FAIL" : "PASS";
receipt.finished_at = new Date().toISOString();
const out = join(opt.out, `desk-verify-${stamp}.json`);
writeFileSync(out, JSON.stringify(receipt, null, 1));
console.log(`${receipt.verdict}: ${receipt.steps.filter((s) => s.ok).length}/${receipt.steps.length} steps -> ${out}`);
process.exit(failed ? 1 : 0);
