// VJ Rig wave 2 receipt: the new sets, the beat-synced transitions, the post look and the showcase tour, checked in a
// private headless Chrome forced onto SwiftShader (the CPU: this host's AMD driver has a crash history, so no frame here
// is ever drawn on the GPU), under the house GPU lock, in bursts under three minutes with the lock released between them.
//
//   node arsenal/lanes/vj2_verify.mjs [--phase all|sets|show|sheet] [--port 8941] [--out <dir>] [--lock-dir <dir>]
//                                     [--dwell 2500] [--width 960] [--height 540] [--sets id,id]
//
// Burst 1 (sets): every set loads; each NEW set compiles, renders a non-black picture, advances frames, answers pads, and
//   stays inside the flash gate twice over -- the set alone under the demo's music makes no flash (no rise of 0.1 in mean
//   relative luminance over the darkest of the previous 300 ms), and ten white-flash requests inside one second give at
//   most three granted flashes and at most three measured flashes in any second, with the post look on. A screenshot of
//   every set, old and new, for the contact sheet.
// Burst 2 (show): each transition style (crossfade, radial wipe, glitch cut, zoom-through) is asked for with R, starts on
//   the demo's next downbeat (the demo numbers its bars), completes, and makes no flash on the way; one switch with timing
//   'beat' starts on the next beat; the look: off and on, at full amount through the flash test, learned onto a fader;
//   the showcase (?showcase=1&dwell=5) opens on its own when no engine answers, shows name cards, lands transitions and
//   plays only gentle accents.
// Burst 3 (sheet): one contact sheet of every set from burst 1's screenshots (state/arsenal/receipts/vj2-<stamp>/).
// Writes receipt.json beside the screenshots; exits 1 if any check fails.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { LOCK_DIR, acquireGpuLock } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    phase: { type: "string", default: "all" },
    port: { type: "string", default: "8941" },
    dwell: { type: "string", default: "2500" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    width: { type: "string", default: "960" },
    height: { type: "string", default: "540" },
    sets: { type: "string", default: "" },
    "gpu-wait-min": { type: "string", default: "4" },
    "lock-dir": { type: "string", default: LOCK_DIR },
    stamp: { type: "string", default: "" },
  },
});
let PORT = Number(opt.port);
if (PORT === 8793 || !(PORT >= 8900 && PORT <= 8999)) {
  console.log(`ERROR port ${PORT}: the receipt uses the test band 8900-8999 only (8793 is Daniel's server)`);
  process.exit(2);
}
const dwellMs = Number(opt.dwell);
const stamp = opt.stamp || new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const outDir = join(opt.out, `vj2-${stamp}`);
mkdirSync(outDir, { recursive: true });
const PHASES = opt.phase === "all" ? ["sets", "show", "sheet"] : opt.phase.split(",");

const NEW_SETS = ["vj-hyperspace", "vj-synthwave-grid", "vj-liquid-chrome", "vj-lissajous-chords", "vj-note-rain",
                  "vj-fractal-bloom", "vj-geometry-hall", "vj-particle-galaxy"];
const STYLES = ["crossfade", "radial", "glitch", "zoom"];
const receiptFile = join(outDir, "receipt.json");
const report = existsSync(receiptFile) ? JSON.parse(readFileSync(receiptFile, "utf8")) : {
  api: "arsenal.receipt/v0", lane: "vj2", title: "VJ rig wave 2: sets, transitions, look and showcase on SwiftShader",
  started_at: new Date().toISOString(), viewport: { width: Number(opt.width), height: Number(opt.height) },
  bursts: [], sets: [], transitions: [], look: {}, showcase: {}, sheet: null, console: [], exceptions: [], page_errors: [],
  checks: {},
  not_measured: [
    "the real GPU: every frame here is drawn by SwiftShader on the CPU, so frame rate and timing say nothing about the live rig",
    "the KeyLab and the real keylab-vj engine: the demo's scripted show and test hooks speak the event contract instead",
    "how each set looks in motion to a person: the screenshots are single frames",
    "photosensitivity beyond the three-flashes rule (red flashes, area thresholds): reasoned in the code, not measured",
  ],
};
const checks = report.checks;

// ----------------------------------------------------------------------------------------------- the server --
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".json": "application/json", ".frag": "text/plain; charset=utf-8",
                ".glsl": "text/plain; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml" };
let sheetHtml = "";
const web = createServer((req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (url.pathname === "/favicon.ico") { res.writeHead(204); res.end(); return; }
  if (url.pathname === "/sheet.html") { res.writeHead(200, { "Content-Type": TYPES[".html"] }); res.end(sheetHtml); return; }
  if (url.pathname.startsWith("/receipt/")) {            // the screenshots, for the contact sheet
    const name = basename(decodeURIComponent(url.pathname.slice(9)));
    try { res.writeHead(200, { "Content-Type": "image/png" }); res.end(readFileSync(join(outDir, name))); }
    catch { res.writeHead(404); res.end(); }
    return;
  }
  if (!url.pathname.startsWith("/web/")) { res.writeHead(404); res.end(); return; }
  const target = resolve(WEB, decodeURIComponent(url.pathname.slice(5)));
  if (!(target + sep).startsWith(WEB + sep) && target !== WEB) { res.writeHead(404); res.end(); return; }
  try {
    const body = readFileSync(target);
    res.writeHead(200, { "Content-Type": TYPES[extname(target).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
async function listenInBand(server, preferred) {
  for (let p = preferred; p <= 8999; p++) {
    if (p === 8793) continue;
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
// a test-band port nothing listens on: the showcase's engine URL, so the tour must find no engine and start the demo
async function deadPortInBand(preferred) {
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
    await delay(120);
  }
  throw new Error(`timed out waiting for ${what}`);
}

// One burst: the lock, a fresh Chrome, a page; fn(page) does the work; everything is released after.
async function burst(label, fn) {
  const t0 = Date.now();
  const entry = { label, started_at: new Date().toISOString(), seconds: null, error: null };
  report.bursts.push(entry);
  const profile = join(tmpdir(), `arsenal-vj2-${stamp}-${label}`);
  let gpu = null, chrome = null, browser = null;
  try {
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `vj2_verify ${label} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000 });
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
    const S = (method, params = {}) => withTimeout(browser.send(method, params, sessionId), 60000, method);
    browser.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled") {
        report.console.push({ burst: label, type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
      } else if (msg.method === "Runtime.exceptionThrown") {
        const d = p.exceptionDetails;
        report.exceptions.push({ burst: label, text: d.text, description: d.exception?.description, line: d.lineNumber, url: d.url });
      } else if (msg.method === "Log.entryAdded" && (p.entry.level === "error" || p.entry.level === "warning")) {
        report.console.push({ burst: label, type: `log-${p.entry.level}`, text: p.entry.text, url: p.entry.url });
      }
    });
    for (const d of ["Runtime", "Log", "Page"]) await S(`${d}.enable`);
    const evaluate = async (expression) => {
      const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const shot = async (name, params = {}) => {
      const r = await S("Page.captureScreenshot", { format: "png", ...params });
      const file = join(outDir, `${name}.png`);
      writeFileSync(file, Buffer.from(r.data, "base64"));
      return file;
    };
    const KEYS = { R: ["KeyR", "r", 82], W: ["KeyW", "w", 87], M: ["KeyM", "m", 77], L: ["KeyL", "l", 76], T: ["KeyT", "t", 84] };
    const tap = async (k) => {
      const [code, keyName, vk] = KEYS[k];
      for (const type of ["keyDown", "keyUp"]) {
        await S("Input.dispatchKeyEvent", { type, code, key: keyName, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
        if (type === "keyDown") await delay(50);
      }
    };
    const open = async (query) => {
      await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?${query}` });
      await waitFor(() => evaluate("!!(window.__vj && window.__vj.ready && window.__vjx)"), 90000, "the VJ page and its hooks");
      const gl = await evaluate(`(() => { const c = document.getElementById("gl"); const g = c.getContext("webgl2");
        if (!g) return null; const d = g.getExtension("WEBGL_debug_renderer_info");
        return { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER), version: g.getParameter(g.VERSION) }; })()`);
      report.webgl = gl;
      report.renderer_check = judgeRenderer(gl && gl.renderer);
      if (!report.renderer_check.ok) throw new Error(`refusing to judge: ${report.renderer_check.reason}`);
    };
    await fn({ S, evaluate, shot, tap, open });
    report.page_errors.push(...(await evaluate("window.__vj ? window.__vj.errors() : []").catch(() => [])).map((e) => ({ burst: label, ...e })));
    await S("Page.navigate", { url: "about:blank" }).catch(() => {});
  } catch (err) {
    entry.error = String((err && err.stack) || err);
    console.log(`ERROR in ${label}:`, entry.error);
  } finally {
    try { await browser?.send("Browser.close"); } catch { /* gone */ }
    await delay(600);
    if (chrome && chrome.exitCode === null) spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
    gpu?.release();
    await delay(300);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
    entry.seconds = Math.round((Date.now() - t0) / 100) / 10;
    console.log(`[burst] ${label}: ${entry.seconds} s${entry.error ? " (error)" : ""}`);
  }
}

// measured flashes in a luminance trace: a rise of 0.1 or more over the darkest of the previous 300 ms, re-armed when it
// falls back within 0.05 (the same rule arsenal/lanes/vj_verify.mjs applies)
function flashes(trace) {
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
  let max = 0;
  for (let i = 0; i < rises.length; i++) {
    let n = 0;
    for (let j = i; j < rises.length && rises[j] - rises[i] < 1000; j++) n++;
    max = Math.max(max, n);
  }
  return { rises, maxInAnySecond: max, samples: trace.length, peak: Math.max(0, ...trace.map((s) => s.luma)) };
}
// ten hard presses of the white-flash pad (3) 100 ms apart, fired inside the page so slow frames cannot stretch the burst
const FLASH_BURST = `new Promise((done) => {
  const times = [], t0 = performance.now();
  for (let i = 0; i < 10; i++) setTimeout(() => {
    const o = { code: "Digit3", key: "#", shiftKey: true, bubbles: true };
    window.dispatchEvent(new KeyboardEvent("keydown", o));
    window.dispatchEvent(new KeyboardEvent("keyup", o));
    times.push(Math.round(performance.now() - t0));
    if (times.length === 10) setTimeout(() => done(times), 40);
  }, i * 100);
})`;
async function flashTest(page) {
  const { evaluate } = page;
  const before = (await evaluate("window.__vj.stats()")).flash;
  await evaluate("window.__vj.probe(true)");
  const times = await evaluate(FLASH_BURST);
  await delay(1500);
  const trace = await evaluate("window.__vj.trace()");
  await evaluate("window.__vj.probe(false)");
  const after = (await evaluate("window.__vj.stats()")).flash;
  const m = flashes(trace);
  return { requests: 10, request_span_ms: times[9] - times[0], granted: after.granted - before.granted, refused: after.refused - before.refused,
           gate_max_in_any_second: after.maxInAnyWindow, measured_rises: m.rises, measured_max_in_any_second: m.maxInAnySecond,
           samples: m.samples, peak: m.peak,
           ok: after.granted - before.granted >= 1 && after.maxInAnyWindow <= 3 && m.maxInAnySecond <= 3 && m.samples > 5 };
}

// ------------------------------------------------------------------------------------------ burst 1: the sets --
async function phaseSets(page) {
  const { evaluate, shot, open, tap } = page;
  const only = opt.sets ? opt.sets.split(",").map((s) => s.trim()).filter(Boolean) : null;
  await open(`demo=1&demopads=0&hud=0&watchdog=0&look=1${only ? `&sets=${only.join(",")}` : ""}`);
  const list = await evaluate("window.__vj.sets()");
  await evaluate("window.__vjx.cardOff()");          // the boot's name card would sit in the first screenshot
  console.log(`[sets] ${list.map((s) => `${s.id}:${s.status}`).join(" ")}`);
  report.sets = report.sets.filter((r) => !list.some((s) => s.id === r.id));
  for (const s of list) {
    const isNew = NEW_SETS.includes(s.id);
    const row = { id: s.id, name: s.name, new: isNew, status: s.status, problem: s.problem };
    if (!s.broken) {
      row.selected = await evaluate(`window.__vj.select(${JSON.stringify(s.id)})`);
      const f0 = (await evaluate("window.__vj.stats()")).frames;
      // the set alone under the demo's music, its luminance traced for flashes of its own
      await evaluate("window.__vj.probe(true)");
      await delay(isNew ? dwellMs : Math.min(dwellMs, 1800));
      const own = flashes(await evaluate("window.__vj.trace()"));
      await evaluate("window.__vj.probe(false)");
      const st = await evaluate("window.__vj.stats()");
      row.active = await evaluate("window.__vj.active()");
      row.frames = st.frames - f0;
      row.fps_swiftshader = st.fps;
      row.size = `${st.width}x${st.height}`;
      row.luma = await evaluate("window.__vj.luma()");
      row.own_flashes = { max_in_any_second: own.maxInAnySecond, rises: own.rises.length, samples: own.samples, peak: +own.peak.toFixed(4) };
      row.screenshot = await shot(`set-${s.id}`);
      if (isNew) {
        // pads: a shockwave, a hard laser burst and a held particle fountain (1, 2, 6), and the set's own answer to them
        await evaluate("(window.__vj.press(1, 0.9), window.__vj.press(2, 1.0), window.__vj.press(6, 0.85), true)");
        await delay(500);
        row.luma_pads = await evaluate("window.__vj.luma()");
        row.screenshot_pads = await shot(`set-${s.id}-pads`);
        await evaluate("(window.__vj.release(1), window.__vj.release(2), window.__vj.release(6), true)");
        await tap("W");
        await delay(400);
        row.flash = await flashTest(page);
        await tap("W");
        await delay(300);
      }
      row.errors = (await evaluate("window.__vj.errors()")).filter((e) => e.id === s.id);
    }
    report.sets.push(row);
    console.log(`[set] ${s.id}: ${s.status} frames=${row.frames} luma=${row.luma?.toFixed?.(4)} own=${row.own_flashes?.max_in_any_second}` +
                `${row.flash ? ` gate=${row.flash.gate_max_in_any_second} measured=${row.flash.measured_max_in_any_second}` : ""}`);
  }
}

// ----------------------------------------------------------------- burst 2: transitions, the look, the showcase --
async function phaseShow(page) {
  const { evaluate, shot, open, tap } = page;
  await open("demo=1&demopads=0&hud=0&watchdog=0&look=1");
  await evaluate("window.__vjx.cardOff()");
  await evaluate(`window.__vj.select("vj-synthwave-grid")`);
  await delay(1500);
  report.transitions = [];
  // the transitions run three times their length here, so the mid-way screenshot lands mid-way on a slow software
  // renderer; the start (on the beat) and the completion are what the checks judge
  await evaluate("window.__vjx.setSlow(3)");
  const runOne = async (style, quantize) => {
    await evaluate(`window.__vjx.setLook({ style: ${JSON.stringify(style)}, quantize: ${JSON.stringify(quantize)} })`);
    const from = (await evaluate("window.__vj.stats()")).setA;
    const n0 = (await evaluate("window.__vjx.transitions()")).length;
    await evaluate("window.__vj.probe(true)");
    await tap("R");
    const t = await waitFor(async () => { const l = await evaluate("window.__vjx.transitions()"); return l.length > n0 ? l[l.length - 1] : null; },
                            3000, "the transition's plan");
    // a screenshot halfway through
    await waitFor(() => evaluate(`performance.now() >= ${t.start + t.ms * 0.5}`), 9000, "the transition's middle");
    const mid = await shot(`transition-${style}-${quantize}-mid`);
    const landed = await waitFor(async () => { const s = await evaluate("window.__vj.stats()"); return !s.fading && s.setA !== from ? s : null; },
                                 12000, `the ${style} transition to finish`).catch(() => null);
    const trace = await evaluate("window.__vj.trace()");
    await evaluate("window.__vj.probe(false)");
    const log = await evaluate("window.__vjx.transitions()");
    const done = log[log.length - 1];
    const m = flashes(trace);
    const row = { style, quantize, from, to: landed ? landed.setA : null, plan: done, screenshot_mid: mid,
                  started_on_beat: done.beatAtStart !== null && Math.abs(done.start - done.beatAtStart) <= 40,
                  start_beat_n: done.beatN, completed: !!landed && done.end !== null,
                  duration_ms: done.end !== null ? done.end - done.start : null, measured_rises: m.rises.length, measured_max_in_any_second: m.maxInAnySecond };
    report.transitions.push(row);
    console.log(`[transition] ${style}/${quantize}: on=${done.on} start-beat=${done.start - (done.beatAtStart ?? NaN)}ms n=${done.beatN} completed=${row.completed} rises=${row.measured_rises}`);
    await delay(800);
  };
  for (const style of STYLES) await runOne(style, "bar");
  await runOne("crossfade", "beat");
  await evaluate("window.__vjx.setSlow(1)");
  const tr = report.transitions;
  checks.every_transition_style_completes = STYLES.every((s) => tr.some((r) => r.style === s && r.completed));
  checks.transitions_start_on_the_downbeat_when_bars_are_known = tr.filter((r) => r.quantize === "bar")
    .every((r) => r.plan.on === "bar" && r.started_on_beat && r.start_beat_n % 4 === 0);
  checks.transition_timing_beat_starts_on_a_beat = tr.filter((r) => r.quantize === "beat").every((r) => r.plan.on === "beat" && r.started_on_beat);
  checks.transitions_make_no_flash = tr.every((r) => r.measured_rises === 0);

  // ---- the look: off and on, the same set and moment; at full amount through the flash test; learned onto a fader
  await evaluate(`window.__vj.select("vj-particle-galaxy")`);
  await delay(1800);
  await evaluate("window.__vjx.setLook({ on: false })");
  await delay(400);
  report.look.off = { luma: await evaluate("window.__vj.luma()"), screenshot: await shot("look-off") };
  await evaluate("window.__vjx.setLook({ on: true, amount: 1 })");
  await delay(400);
  report.look.full = { luma: await evaluate("window.__vj.luma()"), screenshot: await shot("look-full") };
  await evaluate("window.__vjx.setLook({ on: true, amount: 0.55 })");
  await delay(400);
  report.look.default = { luma: await evaluate("window.__vj.luma()"), screenshot: await shot("look-default") };
  report.look.state = await evaluate("window.__vjx.look()");
  await evaluate("window.__vjx.setLook({ on: true, amount: 1 })");
  await evaluate(`window.__vj.select("vj-chord-constellations")`);
  await delay(1200);
  report.look.flash_at_full = await flashTest(page);
  await tap("W");
  // learn on touch: open the panel, click the look's Learn, move a control; then the control moves the look
  await tap("M");
  await delay(300);
  report.look.learn_clicked = await evaluate(`(() => { const b = document.querySelector(".stage-sec .target button"); if (!b) return false; b.click(); return true; })()`);
  await evaluate(`window.__vj.event({ t: "ctl", id: "cc114", kind: "abs", value: 0.3, delta: 0 })`);
  await delay(200);
  const learned = await evaluate("window.__vjx.look()");
  await evaluate(`window.__vj.event({ t: "ctl", id: "cc114", kind: "abs", value: 0.8, delta: 0 })`);
  await delay(200);
  const moved = await evaluate("window.__vjx.look()");
  const ctlMap = (await evaluate("window.__vj.stats()")).ctlMap;
  await evaluate(`(document.querySelector(".stage-sec").scrollIntoView({ block: "center" }), true)`);
  await delay(250);
  report.look.screenshot_panel = await shot("panel-transitions-and-look");
  await tap("M");
  await tap("L");
  await delay(150);
  const toggled = await evaluate("window.__vjx.look()");
  await tap("L");
  report.look.learn = { learned_ctl: learned.ctl, learned_amount: learned.amount, moved_amount: moved.amount, l_key_on: toggled.on,
                        cc114_in_page_map: ctlMap.cc114 ?? null, sat_still_on_cc107: ctlMap.cc107 };
  checks.look_on_and_off_both_render = report.look.off.luma > 0.0008 && report.look.full.luma > 0.0008 && report.look.state.fx === true &&
    !report.look.state.fxError;
  checks.look_changes_mean_luminance_only_a_little = Math.abs(report.look.full.luma - report.look.off.luma) < 0.05;
  checks.flash_gate_holds_with_the_look_at_full = report.look.flash_at_full.ok;
  checks.look_amount_learns_a_fader = report.look.learn_clicked && learned.ctl === "cc114" && Math.abs(learned.amount - 0.3) < 1e-6 &&
    Math.abs(moved.amount - 0.8) < 1e-6 && toggled.on === false && (ctlMap.cc114 === undefined || ctlMap.cc114 === null) && ctlMap.cc107 === "sat";
  await evaluate("window.__vjx.setLook({ on: true, amount: 0.55, style: 'cycle', quantize: 'bar', ctl: null })");

  // ---- Lissajous Chords played by hand: C major (4:5:6) and then C minor (10:12:15), no demo, the same moment of drift
  await open("engine=off&hud=0&watchdog=0&look=1&sets=vj-lissajous-chords");
  await evaluate("window.__vjx.cardOff()");
  report.lissajous = {};
  const hold = async (name, keys, chord) => {
    await evaluate(`(${JSON.stringify(keys)}.forEach((k) => window.__vj.event({ t: "note", key: k, vel: 0.8, on: true })),
      window.__vj.event({ t: "chord", src: "keys", name: ${JSON.stringify(chord.name)}, root: ${chord.root}, pcs: ${JSON.stringify(chord.pcs)}, changed: true }), true)`);
    await delay(2600);
    report.lissajous[name] = { keys, chord: chord.name, luma: await evaluate("window.__vj.luma()"), screenshot: await shot(`lissajous-${name}`) };
    await evaluate(`(${JSON.stringify(keys)}.forEach((k) => window.__vj.event({ t: "note", key: k, vel: 0, on: false })), true)`);
    await delay(300);
  };
  await hold("c-major-4-5-6", [60, 64, 67], { name: "C", root: 0, pcs: [0, 4, 7] });
  await hold("c-minor-10-12-15", [60, 63, 67], { name: "Cm", root: 0, pcs: [0, 3, 7] });
  await hold("c7-4-5-6-7", [60, 64, 67, 70], { name: "C7", root: 0, pcs: [0, 4, 7, 10] });
  checks.lissajous_draws_each_chord = Object.values(report.lissajous).every((r) => r.luma > 0.002);

  // ---- the showcase: no engine answers, so the tour starts the demo itself; cards, transitions, gentle accents
  const dead = await deadPortInBand(PORT + 20);
  await open(`showcase=1&dwell=5&watchdog=0&engine=http://127.0.0.1:${dead}`);
  await delay(1200);
  const s0 = await evaluate("window.__vjx.showcase()");
  report.showcase.at_open = { ...s0, active: (await evaluate("window.__vj.stats()")).setA, hud_hidden: await evaluate(`getComputedStyle(document.getElementById("hud")).opacity === "0"`) };
  report.showcase.screenshot_card = await shot("showcase-card");
  await waitFor(async () => (await evaluate("window.__vjx.showcase()")).cards.length >= 3, 45000, "three name cards (two transitions)").catch(() => null);
  await delay(1600);
  report.showcase.screenshot_later = await shot("showcase-later");
  const s1 = await evaluate("window.__vjx.showcase()");
  const st = await evaluate("window.__vj.stats()");
  report.showcase.later = { ...s1, demo: st.demo, setA: st.setA, transitions: await evaluate("window.__vjx.transitions()") };
  const never = ["flash", "strobe", "invert", "freeze"];
  checks.showcase_starts_the_demo_when_no_engine_plays = s1.on && s1.mode === "demo" && st.demo === true;
  checks.showcase_opens_on_a_new_set_with_its_name = report.showcase.at_open.active === "vj-hyperspace" &&
    /Hyperspace/.test(s0.card ? s0.card.text : "") && report.showcase.at_open.hud_hidden;
  checks.showcase_tours_sets_with_cards_and_transitions = s1.cards.length >= 3 && new Set(s1.cards.map((c) => c.id)).size >= 3 &&
    report.showcase.later.transitions.filter((x) => x.end !== null).length >= 2;
  checks.showcase_accents_are_gentle = s1.accents.length >= 1 && s1.accents.every((a) => !never.includes(a.effect));
}

// --------------------------------------------------------------------------------------- burst 3: the sheet --
async function phaseSheet(page) {
  const { S } = page;
  const files = readdirSync(outDir).filter((f) => /^set-.+\.png$/.test(f) && !/-pads\.png$/.test(f));
  const order = (id) => { const i = NEW_SETS.indexOf(id); return i >= 0 ? 100 + i : 0; };
  const rows = report.sets.length ? report.sets.filter((r) => files.includes(`set-${r.id}.png`))
    : files.map((f) => ({ id: f.slice(4, -4), name: f.slice(4, -4), new: NEW_SETS.includes(f.slice(4, -4)) }));
  rows.sort((a, b) => order(a.id) - order(b.id));
  const cols = 4, tw = 480, th = 270;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const cells = rows.map((r) => `<figure><img src="/receipt/set-${encodeURIComponent(r.id)}.png" width="${tw}" height="${th}">` +
    `<figcaption><b>${esc(r.name || r.id)}</b>${r.new ? '<i>new</i>' : ""}<span>${esc(r.id)}</span></figcaption></figure>`).join("");
  sheetHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;background:#07080c;color:#e8ecf4;font:13px/1.3 "Segoe UI",system-ui,sans-serif}
    header{padding:18px 22px 6px;display:flex;align-items:baseline;gap:14px}
    header h1{margin:0;font-size:22px;font-weight:800;letter-spacing:.02em} header p{margin:0;color:#9aa3b5}
    main{display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:14px;padding:12px 22px 22px}
    figure{margin:0;background:#0d1017;border:1px solid rgba(160,175,210,.18);border-radius:8px;overflow:hidden}
    img{display:block;width:${tw}px;height:${th}px;object-fit:cover}
    figcaption{display:flex;gap:8px;align-items:baseline;padding:7px 10px}
    figcaption b{font-weight:700} figcaption i{font-style:normal;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#07080c;background:#4cc2ba;border-radius:3px;padding:1px 5px}
    figcaption span{margin-left:auto;color:#5d6577;font:11px ui-monospace,Consolas,monospace}
  </style></head><body><header><h1>VJ Rig: every set</h1><p>${rows.length} sets, ${rows.filter((r) => r.new).length} new tonight;
    single frames under the demo's music, drawn by SwiftShader at ${opt.width}x${opt.height} (receipt vj2-${stamp})</p></header>
    <main>${cells}</main></body></html>`;
  const W = 22 * 2 + cols * tw + (cols - 1) * 14;
  const H = 64 + Math.ceil(rows.length / cols) * (th + 34 + 14) + 22;
  await S("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/sheet.html` });
  await delay(1500);
  const r = await S("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
  const file = join(outDir, "contact-sheet.png");
  writeFileSync(file, Buffer.from(r.data, "base64"));
  report.sheet = { file, sets: rows.map((r) => r.id), size: `${W}x${H}` };
  checks.contact_sheet_written = rows.length >= 14 && existsSync(file);
}

// -------------------------------------------------------------------------------------------------- the run --
try {
  PORT = await listenInBand(web, PORT);
  if (PHASES.includes("sets")) await burst("sets", phaseSets);
  if (PHASES.includes("show")) await burst("show", phaseShow);
  if (PHASES.includes("sheet")) await burst("sheet", async (page) => phaseSheet(page));
} finally {
  if (PHASES.includes("sets")) {
    const fresh = report.sets.filter((r) => r.new);
    checks.every_new_set_present = NEW_SETS.every((id) => report.sets.some((r) => r.id === id)) || !!opt.sets;
    checks.every_new_set_compiles = fresh.length > 0 && fresh.every((r) => r.status === "ok" && r.active?.compiled && r.active?.id === r.id);
    checks.every_new_set_renders_non_black = fresh.length > 0 && fresh.every((r) => typeof r.luma === "number" && r.luma > 0.0008);
    checks.every_new_set_advances_frames = fresh.length > 0 && fresh.every((r) => r.frames > 2);
    checks.no_new_set_flashes_on_its_own = fresh.length > 0 && fresh.every((r) => r.own_flashes && r.own_flashes.max_in_any_second === 0);
    checks.flash_gate_holds_on_every_new_set = fresh.length > 0 && fresh.every((r) => r.flash && r.flash.ok);
    checks.every_old_set_still_renders = report.sets.filter((r) => !r.new).every((r) => r.status === "ok" && r.luma > 0.0008);
  }
  checks.software_renderer_only = !!report.renderer_check?.ok;
  checks.no_page_exceptions = report.exceptions.length === 0;
  const external = (c) => /fonts\.(googleapis|gstatic)\.com/.test(`${c.url || ""} ${c.text || ""}`);
  // a refused connection to the deliberately dead engine port is the showcase test working, not a page fault
  const deadEngine = (c) => /ERR_CONNECTION_REFUSED|api\/events/.test(`${c.url || ""} ${c.text || ""}`) && c.burst === "show";
  checks.no_console_errors = !report.console.some((c) => (c.type === "error" || c.type === "log-error") && !external(c) && !deadEngine(c));
  checks.no_page_recorded_errors = report.page_errors.filter((e) => e.kind !== "engine").length === 0;
  checks.no_burst_error = report.bursts.every((b) => !b.error);
  checks.bursts_under_three_minutes = report.bursts.every((b) => b.seconds === null || b.seconds < 180);
  report.verdict = { pass: Object.values(checks).every(Boolean), checks };
  report.finished_at = new Date().toISOString();
  writeFileSync(receiptFile, JSON.stringify(report, null, 2));
  web.close();
  for (const [k, v] of Object.entries(checks)) console.log(`${v ? "PASS" : "FAIL"} ${k}`);
  for (const e of report.exceptions) console.log("EXC", e.description || e.text);
  for (const c of report.console.filter((c) => c.type === "error" || c.type === "log-error")) console.log("CONSOLE", c.burst, c.text, c.url || "");
  for (const e of report.page_errors) console.log("PAGE", e.burst, e.kind, e.id, String(e.message).split("\n")[0]);
  console.log("verdict:", report.verdict.pass ? "PASS" : "FAIL");
  console.log("receipt:", receiptFile);
  if (report.sheet) console.log("contact sheet:", report.sheet.file);
  process.exit(report.verdict.pass ? 0 : 1);
}
