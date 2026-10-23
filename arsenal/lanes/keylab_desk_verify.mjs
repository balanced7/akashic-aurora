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
const receipt = { api: "arsenal.receipt/v0", title: "KeyLab -> shader uniforms on the Shader Desk, Play and the VFX Bench (headless, SwiftShader, fake engine)",
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
// The /keylab/ allowlist, read from arsenal/keylab/webmount.py itself, so this check serves exactly what the snippet
// would make the Bifrost console serve.
const KEYLAB_ROUTES = Object.fromEntries([...readFileSync(join(REPO, "arsenal", "keylab", "webmount.py"), "utf8")
  .matchAll(/^\s+"([a-z0-9-]+\.js)": "([^"]+)",$/gm)].map((m) => [m[1], m[2]]));
// The two VFX Bench presets the stub serves as scenes (the bench's own preset shape).
const BENCH_PRESETS = {
  "keylab-test-a": { style: "geodesic", state: "thinking", params: { sub: 1.2 }, tint: [0.9, 0.2, 0.6], dials: { wire: 0.5, see: 0.85, rate: 0.5 } },
  "keylab-test-b": { style: "geodesic", state: "thinking", params: { sub: 4.4 }, tint: [0.2, 0.4, 1.0], dials: { wire: 0.5, see: 0.85, rate: 0.5 } },
};
const json = (res, obj, code = 200) => { res.writeHead(code, { "Content-Type": "application/json", "Cache-Control": "no-store" }); res.end(JSON.stringify(obj)); };
const file200 = (res, path, type, transform) => {
  let body = readFileSync(path);
  if (transform) body = transform(body.toString("utf8"));
  res.writeHead(200, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(body);
};
function staticServer() {
  return createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    const p = url.pathname;
    if (p === "/api/presets") return json(res, { presets: presetList() });
    // Play, as the arsenal server serves it (its other /api/ routes 404 here; Play keeps running without them)
    if (p === "/play") return file200(res, join(WEB, "play.html"), TYPES[".html"]);
    // The VFX Bench, as the Bifrost console serves it, WITH the one-line vfx.html change from webmount.py applied
    if (p === "/vfx") return file200(res, join(REPO, "scripts", "vfx.html"), TYPES[".html"],
      (t) => t + '\n<script type="module" src="/keylab/keylab-mount.js"></script>\n');   // vfx.html has no </body>: the line goes at the end
    if (p === "/agent-avatar.js") return file200(res, join(REPO, "scripts", "agent-avatar.js"), TYPES[".js"]);
    // A page of plain house-control rows (the shape params-ui renders, as on the Shader Lab's Inspector), with no
    // KeyLab code of its own: the generic mount must find its sliders and set them the way a hand does.
    if (p === "/test/ranges") {
      res.writeHead(200, { "Content-Type": TYPES[".html"], "Cache-Control": "no-store" });
      return res.end(`<!doctype html><meta charset="utf-8"><title>ranges</title><body style="background:#111;color:#ddd">
        <div class="params-row"><label class="params-label" for="a">gain</label><span class="params-ctl"><input id="a" type="range" min="0" max="2" step="0.01" value="1"></span></div>
        <div class="params-row"><label class="params-label" for="b">blur</label><span class="params-ctl"><input id="b" type="range" min="0" max="10" step="0.1" value="5"></span></div>
        <script>window.__heard = []; document.addEventListener("input", (e) => __heard.push([e.target.id, Number(e.target.value)]));</script>
        <script type="module">import("/web/lib/keylab-mount.js");</script></body>`);
    }
    const km = /^\/keylab\/([a-z0-9-]+\.js)$/.exec(p);
    if (km) { const rel = KEYLAB_ROUTES[km[1]]; if (!rel) { res.writeHead(404); return res.end(); } return file200(res, join(REPO, rel), TYPES[".js"]); }
    if (p === "/vfx/presets") return json(res, BENCH_PRESETS);
    if (p === "/vfx/bench") return json(res, null);
    if (p === "/vfx/job/next") return json(res, {});
    if (p === "/events") { res.writeHead(200, { "Content-Type": "text/event-stream" }); res.write(": stub\n\n"); return; }
    if (p.startsWith("/vfx/") || p === "/send") return json(res, req.method === "POST" ? { ok: true } : (/(chunks|sketches|graphs|compositions|groups|thumbs|clips)$/.test(p) ? [] : {}));
    if (!p.startsWith("/web/")) { res.writeHead(404); return res.end("not found"); }
    const file = normalize(join(WEB, decodeURIComponent(url.pathname.slice(5))));
    if (!file.startsWith(WEB + sep)) { res.writeHead(404); return res.end("not found"); }
    let body;
    try { if (!statSync(file).isFile()) throw new Error("dir"); body = readFileSync(file); } catch { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(body);
  });
}
const sse = new Set();
const screens = [];
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
    if (url.pathname === "/api/screen" && req.method === "POST") {   // the proposed screen route: record what the page asks to draw
      let body = "";
      req.on("data", (c) => { body += c; });
      req.on("end", () => { try { screens.push(JSON.parse(body)); } catch { screens.push({ bad: body.slice(0, 80) }); } });
      res.writeHead(200, { ...cors, "Content-Type": "application/json" }); return res.end('{"ok":true}');
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

  const url = `http://127.0.0.1:${webPort}/web/shader-desk.html?keylab=${encodeURIComponent(`http://127.0.0.1:${engPort}/api/events`)}&preset=aurora-ribbons&freeze=2&scale=0.5&watchdog=0`;
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

  // The pad panel draws the pads where they sit on the unit: 4 across x 3 down, pad 1 top left (Daniel at the device,
  // 2026-10-23: "pad 1 ... is actually the top left most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is
  // 9-12"). Read off the RENDERED boxes in the panel's shadow root: rows by their top edge, each row left to right.
  const padPanel = await evaluate(`(() => {
    const host = document.querySelector("#keylab .klh-host");
    const sr = host && host.shadowRoot;
    const grid = sr && sr.querySelector(".klh-pads");
    if (!grid) return null;
    grid.scrollIntoView({ block: "center" });
    const boxes = [...grid.querySelectorAll(".klh-pad")].map((b) => { const r = b.getBoundingClientRect(); return { pad: Number(b.dataset.pad), x: r.left, y: r.top, w: r.width, h: r.height }; });
    const tops = [...new Set(boxes.map((b) => Math.round(b.y)))].sort((a, b) => a - b);
    const lefts = [...new Set(boxes.map((b) => Math.round(b.x)))].sort((a, b) => a - b);
    const rows = tops.map((t) => boxes.filter((b) => Math.round(b.y) === t).sort((a, b) => a.x - b.x).map((b) => b.pad));
    const g = grid.getBoundingClientRect();
    return { rows, columns: lefts.length, minW: Math.min(...boxes.map((b) => b.w)),
      clip: { x: g.left + scrollX - 6, y: g.top + scrollY - 6, width: g.width + 12, height: g.height + 12 } };
  })()`);
  step("the desk's pad panel shows 1 2 3 4 across its top row, then 5-8, then 9-12 (4 across x 3 down)",
    !!padPanel && JSON.stringify(padPanel.rows) === JSON.stringify([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) && padPanel.columns === 4 && padPanel.minW > 30,
    { rows: padPanel && padPanel.rows, columns: padPanel && padPanel.columns, min_pad_width_px: padPanel && Math.round(padPanel.minW) });
  if (padPanel) {
    await delay(150);
    const { data } = await page.send("Page.captureScreenshot", { format: "png", clip: { ...padPanel.clip, scale: 2 } });
    receipt.png_pads = join(opt.out, `desk-verify-${stamp}-pads.png`);
    writeFileSync(receipt.png_pads, Buffer.from(data, "base64"));
  }

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

  // the readout on the KeyLab's screen (opt-in; the fake engine has the proposed /api/screen)
  await evaluate("__desk.option('screen', true)");
  screens.length = 0;
  for (const v of [0.9, 0.8, 0.7, 0.6]) { fader(2, v); await delay(10); }   // four moves inside 80 ms: one or two posts, the last value wins
  await settle(400);
  const lastScreen = screens.at(-1) || null;
  step("screen: a fader move asks the engine to draw the fader screen (throttled, latest wins)", screens.length >= 1 && screens.length <= 3
    && lastScreen && lastScreen.screen === "fader" && lastScreen.name.startsWith("bands") && lastScreen.value === "60%" && lastScreen.level === 76,
    { posts: screens.length, last: lastScreen });
  await evaluate("__desk.option('screen', false)");

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

  // every preset draws in the desk's runtime (Play's contract): 30 frames at a fixed clock from a cleared history
  const looks = [];
  for (const sc of scenes.filter((x) => x.ok)) {
    const f = await evaluate(`(() => { __desk.renderer.select(${JSON.stringify(sc.id)}, { fadeMs: 0 }); return __desk.renderer.still({ time: 3, frames: 30 }); })()`, 30_000);
    const luma = Math.round((0.2126 * f.mean[0] + 0.7152 * f.mean[1] + 0.0722 * f.mean[2]) * 10) / 10;
    looks.push({ id: sc.id, luma, mean: f.mean, png: await shot(`look-${sc.id}`) });
  }
  receipt.looks = looks;
  step("every preset draws a lit frame in the desk's runtime (mean luma above 3 of 255)", looks.every((l) => l.luma > 3), { looks: looks.map((l) => `${l.id} ${l.luma}`) });
  await evaluate(`__desk.select(${JSON.stringify("aurora-ribbons")})`);
  await settle(300);

  // pad 2 switches the scene
  const second = scenes.filter((s) => s.ok)[1].id;
  send({ t: "pad", pad: 2, vel: 0.9, on: true, src: "daw" }); send({ t: "pad", pad: 2, vel: 0, on: false, src: "daw" });
  await settle(900);
  step("pad 2 switches to the second scene", (await evaluate("__desk.active()")) === second, { want: second });

  clearInterval(energyTimer);
  receipt.console_errors = receipt.console.filter((c) => c.type === "exception" || c.type === "error").length;
  step("the desk: no page exceptions or console errors", receipt.console_errors === 0, { console: receipt.console.slice(0, 5) });
  receipt.console_desk = receipt.console.splice(0);

  // ======================================================================== Play, unchanged, in a frame
  await page.send("Page.navigate", { url: `http://127.0.0.1:${webPort}/web/keylab-play.html?keylab=${encodeURIComponent(`http://127.0.0.1:${engPort}/api/events`)}` });
  await waitFor("window.__keylab && __keylab.kind === 'play' && __keylab.client.source === 'engine'", 30_000, "the KeyLab to mount on Play");
  const P = "document.getElementById('play').contentWindow";
  await waitFor(`${P}.__play.presets().length > 1`, 15_000, "Play's preset list");
  const playScenes = await evaluate("__keylab.host.scenes().map((s) => s.id)");
  step("Play: its presets are the KeyLab's scenes", playScenes.length >= 6, { scenes: playScenes });
  const ribbonsAt = playScenes.indexOf("aurora-ribbons");
  send({ t: "pad", pad: ribbonsAt + 1, vel: 0.8, on: true, src: "daw" }); send({ t: "pad", pad: ribbonsAt + 1, vel: 0, on: false, src: "daw" });
  await waitFor(`(${P}.__play.active() || {}).id === 'aurora-ribbons' && ${P}.__play.active().compiled`, 15_000, "Play to switch to aurora-ribbons");
  step(`Play: pad ${ribbonsAt + 1} switches Play to aurora-ribbons through window.__play`, true);
  await settle(400);
  const macro = (t) => evaluate(`(() => { const d = ${P}.document; const r = d.querySelector('input.macro-range[aria-label="${t}"]');
    const row = r.closest('.macro'); return { value: Number(r.value), shown: row.querySelector('.macro-val').textContent, name: row.querySelector('.macro-name').textContent }; })()`);
  const pk1 = await macro("k1");
  step("Play: k1 is flow at Play's default", pk1.name === "flow" && pk1.value === 500, pk1);
  fader(1, 0.0); await settle(300);
  const pk1Hold = await macro("k1");
  step("Play: pickup holds (fader at 0, flow stays 0.50)", pk1Hold.value === 500, pk1Hold);
  for (const v of [0.2, 0.4, 0.6, 0.8, 1.0]) { fader(1, v); await delay(40); }
  await settle(700);
  const pk1After = await macro("k1");
  step("Play: fader 1 drives Play's own k1 handler to 1.00 (its readout says so)", pk1After.value === 1000 && pk1After.shown === "1.00", pk1After);
  knob(9, 30); await settle(700);
  const phue = await macro("hue");
  step("Play: knob 9 turns Play's hue (30 ticks of 128 per turn = 84 degrees)", Math.abs(phue.value - Math.round(30 / 128 * 1000)) <= 2, phue);
  receipt.pngs.push(await shot("play"));
  receipt.console_play = receipt.console.splice(0);
  const playOwn = receipt.console_play.filter((c) => /keylab/i.test(c.text) && (c.type === "exception" || c.type === "error"));
  step("Play: no KeyLab errors (Play's own 404s on this stub server are not counted)", playOwn.length === 0, { keylab_errors: playOwn, play_console: receipt.console_play.length });

  // ======================================================================== any page of sliders (the generic mount)
  await page.send("Page.navigate", { url: `http://127.0.0.1:${webPort}/test/ranges?keylab=${encodeURIComponent(`http://127.0.0.1:${engPort}/api/events`)}` });
  await waitFor("window.__keylab && __keylab.kind === 'ranges' && __keylab.client.source === 'engine'", 20_000, "the generic mount on a page of sliders");
  const rparams = await evaluate("__keylab.host.params().map((p) => p.label + ' ' + p.min + '..' + p.max)");
  step("sliders page: the generic mount lists each slider by its label and range", rparams.join("|") === "gain 0..2|blur 0..10", { params: rparams });
  for (const v of [0.2, 0.45, 0.55, 0.75]) { fader(1, v); await delay(40); }   // gain 1 of 0..2 = position 0.5
  await settle(700);
  const heard = await evaluate("({ value: Number(document.getElementById('a').value), heard: __heard.filter((h) => h[0] === 'a').length })");
  step("sliders page: fader 1 catches gain at 0.5 and sets the page's own slider to 1.5, firing its input event", Math.abs(heard.value - 1.5) < 0.011 && heard.heard > 0, heard);
  receipt.console_ranges = receipt.console.splice(0);

  // ======================================================================== the VFX Bench, with the snippet applied
  await page.send("Page.navigate", { url: `http://127.0.0.1:${webPort}/vfx?keylab=${encodeURIComponent(`http://127.0.0.1:${engPort}/api/events`)}` });
  try {
    await waitFor("window.__keylab && __keylab.kind === 'vfx-bench' && __keylab.client.source === 'engine' && window.av && av.prog", 30_000, "the KeyLab to mount on the bench");
  } catch (err) {
    const why = await evaluate("({ keylab: window.__keylab ? { kind: __keylab.kind, pending: !!__keylab.pending, source: __keylab.client && __keylab.client.source } : null, AgentAvatar: !!window.AgentAvatar, av: !!window.av, prog: !!(window.av && av.prog) })").catch((e) => String(e));
    step("VFX Bench: the mount came up", false, { why, console: receipt.console.slice(-6) });
    throw err;
  }
  step("VFX Bench: /keylab/keylab-mount.js loads through the webmount allowlist and finds the bench", true,
    { routes: Object.keys(KEYLAB_ROUTES) });
  const benchSub = () => evaluate("({ target: av.target.sub, gpu: av.gl.getUniform(av.prog, av.u.u_sub), slider: Number(document.querySelector('#params input').value), out: (document.getElementById('out').value.match(/sub: ([0-9.]+)/) || [])[1] })");
  await settle(500);
  const s0 = await benchSub();
  const pos0 = (s0.target - 0.8) / 4.2;
  for (const v of [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9]) { fader(1, v); await delay(40); }
  await settle(800);
  const s1 = await benchSub();
  const want = 0.8 + 0.9 * 4.2;
  step("VFX Bench: fader 1 catches subdivision on the way up and drives it to 4.58", Math.abs(s1.target - want) < 0.01, { before: s0, after: s1, pickup_at: Math.round(pos0 * 1000) / 1000 });
  step("VFX Bench: the avatar's u_sub on the GPU follows (gl.getUniform)", Math.abs(s1.gpu - want) < 0.05, { u_sub: s1.gpu });
  step("VFX Bench: the bench's own slider and hand-off row show it", Math.abs(s1.slider - want) < 0.03 && Math.abs(Number(s1.out) - want) < 0.01, { slider: s1.slider, handoff: s1.out });
  send({ t: "chord", src: "keys", name: "Bb", root: 10, quality: "maj", pcs: [2, 5, 10], changed: true });
  await settle(2200);
  const tintHue = await evaluate("(() => { const [r,g,b] = av.target.tint; const mx = Math.max(r,g,b), mn = Math.min(r,g,b), d = mx - mn; let h = 0; if (d > 1e-9) h = mx === r ? ((g-b)/d) % 6 : mx === g ? (b-r)/d + 2 : (r-g)/d + 4; return ((h*60)+360)%360; })()");
  step("VFX Bench: a Bb chord turns the tint to 300 degrees (root 10 -> 10 fifths round)", Math.abs(tintHue - 300) < 3, { tint_hue: tintHue });
  send({ t: "pad", pad: 2, vel: 0.8, on: true, src: "daw" }); send({ t: "pad", pad: 2, vel: 0, on: false, src: "daw" });
  await settle(900);
  const s2 = await benchSub();
  step("VFX Bench: pad 2 loads the bench's second saved preset (sub 4.4)", Math.abs(s2.target - 4.4) < 0.01, { sub: s2.target });
  receipt.pngs.push(await shot("vfx-bench"));
  receipt.console_vfx = receipt.console.splice(0);
  const vfxOwn = receipt.console_vfx.filter((c) => /keylab/i.test(c.text) && (c.type === "exception" || c.type === "error"));
  step("VFX Bench: no KeyLab errors (the stubbed bench endpoints are not counted)", vfxOwn.length === 0, { keylab_errors: vfxOwn, bench_console: receipt.console_vfx.length });
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
