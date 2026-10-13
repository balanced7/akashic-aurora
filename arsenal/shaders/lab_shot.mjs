// The Shader Lab's screenshot driver: pictures of the lab PAGE (the Workbench UI), taken in a private headless Chrome
// forced onto SwiftShader, under the house GPU lock, in one burst under three minutes.
//
//   node arsenal/shaders/lab_shot.mjs --out state/arsenal/shaders/labshots/<run> [--sizes 1440x900,900x1200]
//                                     [--views bench,shelf,stage,study,module,recipe,run] [--port 8797]
//                                     [--lib <module dir> --cards <card renders dir>]
//                                     [--subjects ldSfWV,lfscD7] [--raise 1] [--dpr 1] [--grow 1920x1080@2]
//
//   views: bench (as loaded), shelf (the Shelf tab), stage (a loved shader put on stage, its filmstrip playing), study
//   (a study note open), module (a built module picked in the tree), recipe (a built recipe, its generated knobs in the
//   Inspector). --lib / --cards serve a FIXTURE library and its card renders from a private server (never the house's
//   port), so the module views can be looked at before the house library has modules of its own.
//
//   VIEW ONLY. Live runs are off until their safety review clears (stage.js liveSwitch; arsenal/web/shaderlab/
//   README.md): every view above opens /lab/ as Daniel would, with the switch off, and the receipt checks each of them
//   is view only (window.__lab.live false, no Run button, the line said) and asked for no canvas and no WebGL context.
//
//   run: the one view that PRESSES RUN, here on SwiftShader (the CPU), never on a GPU. It turns the live switch on for
//   its own page only (/lab/?live=1, and the key set in this private profile by a script removed again after the run),
//   inside the headless Chrome that is forced onto SwiftShader and judged before any page loads. Each --subjects id is
//   put on stage from its Shelf card, Run is clicked, and the receipt records the pre-flight's verdict (refused, or the
//   scale it chose and the numbers it measured). A running subject is then taken to the Shelf tab (the loop must stop) and back
//   (it must not restart until Run is clicked), and --raise asks for a larger scale through the scale menu (the
//   pre-flight's guard may refuse it; the next allowed scale is tried) so that a heavy shader struggles and the
//   watchdog has to hold the last frame. Every step polls the page with a deadline, so a hung page is a receipt line,
//   not a hung driver. --dpr emulates a HiDPI display for the run view (the Stage sizes its drawing buffer by
//   devicePixelRatio, so the same shader predicts heavier). --grow WxH[@dpr] changes the window mid-run (maximised onto
//   another display): the Stage must stop drawing, run its pre-flight again at the new size before its next frame, and
//   draw only at a size it measured; the receipt records the measurement count, the measured size and the slowest frame
//   before and after. Screenshots: run-<id>[-dpr<n>]-<phase>-<w>x<h>.png.
//
// WHY A DRIVER OF ITS OWN. arsenal/shaders/headless.mjs renders shader PAGES that report window.__render; the lab is a
// different kind of page (a UI that must render nothing on load), so this driver waits for window.__lab instead and
// takes Page.captureScreenshot. Everything that keeps the machine safe is REUSED from headless.mjs, not re-derived: the
// Chrome flags (headless, ANGLE on SwiftShader, Direct3D 11 off, GPU compositing off), the renderer judgement (a WebGL2
// renderer string must name SwiftShader and no hardware, checked before the lab page loads), the state/-only rule for
// output, the burst budget, and the order on the way out (our Chrome dies first, the lock is released second). The
// lock is the house lock (arsenal/lanes/gpu_lock.mjs, arsenal/GPU-LOCK.md). Never port 8793; never the Claude app's
// browser pane; never `chrome --version`.
//
// WHAT IT PROVES BESIDES THE PICTURE. Before any page script runs, the driver wraps HTMLCanvasElement.getContext so the
// page's WebGL requests are counted; the receipt records that count and the number of <canvas> elements after load.
// Ruling 5 says the lab renders nothing live on page load, and the switch says it is view only: on every view but
// `run` both counts must be 0, the page must report the switch off, show no Run button, and say live runs are off on
// the Stage and in the Inspector's empty receipt, and the receipt says so (rule5). Those views only click UI (a tab, "Put on stage", "Play the filmstrip", "Open study note"); only `run`
// presses Run.
//
// Output: <out>/<view>-<w>x<h>.png and <out>/receipt.json. The lab server is reused when one of ours answers on --port,
// otherwise a private one is started on an ephemeral loopback port for the life of this process.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13).
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import {
  BURST_MS, CHROME_EXE, DEVTOOLS_WAIT_MS, FORBIDDEN_PORTS, PROFILE_ROOT, chromeFlags, guardHolder, judgeRenderer, underState,
} from "./headless.mjs";
import { LIVE_OFF_WORDS, LIVE_SWITCH } from "../web/lib/workbench/stage.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
export const SHOT_API = "arsenal.lab-shot/v1";
export const VIEWS = ["bench", "shelf", "stage", "study", "module", "recipe", "run"];
const PAGE_WAIT_MS = 25_000;
const IMAGES_WAIT_MS = 10_000;
const PREFLIGHT_WAIT_MS = 60_000;   // a big shader's first compile and draw on SwiftShader can take tens of seconds
const TRIP_WAIT_MS = 30_000;        // how long a raised run is watched for the watchdog's hold
const SCALES = [0.25, 0.5, 0.75, 1]; // stage.js SCALES
const say = (...a) => console.log("[lab-shot]", ...a);

function withTimeout(promise, ms, what) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(Object.assign(new Error(`no answer within ${ms} ms: ${what}`), { timeout: true })), ms);
  })]).finally(() => clearTimeout(timer));
}

// The house CDP client pattern (headless.mjs connect), small.
function connect(wsUrl) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(wsUrl);
    let next = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) p.rej(new Error(JSON.stringify(msg.error))); else p.res(msg.result);
      } else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onclose = () => { for (const p of pending.values()) p.rej(new Error("DevTools socket closed")); pending.clear(); };
    ws.onopen = () => res({
      send: (method, params = {}) => new Promise((ok, no) => {
        if (ws.readyState !== 1) return no(new Error("DevTools socket closed"));
        const id = next++;
        pending.set(id, { res: ok, rej: no });
        ws.send(JSON.stringify({ id, method, params }));
      }),
      on: (fn) => listeners.push(fn),
      close: () => { try { ws.close(); } catch { /* closed */ } },
    });
    ws.onerror = () => rej(new Error(`websocket error on ${wsUrl}`));
  });
}

// ------------------------------------------------------------------------------------------------- the server
async function probe(port) {
  try {
    const r = await withTimeout(fetch(`http://127.0.0.1:${port}/health`), 1500, "health");
    const j = await r.json();
    return j && j.api === "arsenal.shader-serve/v1" ? j : null;
  } catch { return null; }
}

// Reuse a lab server of ours on `port` (same lab root, and it serves /webl/), else start a private one on an
// ephemeral port; returns {base, stop}. With `roots` ({lib, cards}: a fixture library and its card renders) it always
// starts a private server over those roots, so a picture of a fixture can never be mistaken for the house library.
async function labServer(port, roots = {}) {
  if (FORBIDDEN_PORTS[port]) throw new Error(`port ${port} is refused: it is ${FORBIDDEN_PORTS[port]}`);
  const custom = Object.keys(roots).length > 0;
  const found = custom ? null : await probe(port);
  const lab = join(REPO, "arsenal", "web", "shaderlab");
  if (found && resolve(String(found.roots?.lab || "")).toLowerCase() === resolve(lab).toLowerCase()
      && (found.routes || []).includes("/webl/<file>")) {
    return { base: `http://127.0.0.1:${port}`, stop: () => {}, reused: true };
  }
  const kwargs = Object.entries(roots).map(([k, v]) => `${k}=Path(${JSON.stringify(resolve(v))})`).join(", ");
  const code = "import sys\nfrom pathlib import Path\nfrom arsenal.shaders import serve as S\n"
    + `s = S.start_in_thread(0${kwargs ? ", " + kwargs : ""})\nprint(s.base_url, flush=True)\n`
    + "sys.stdin.read()\ns.shutdown()\n";
  const proc = spawn("py", ["-c", code], { cwd: REPO, stdio: ["pipe", "pipe", "inherit"], windowsHide: true });
  const base = await withTimeout(new Promise((ok, no) => {
    let buf = "";
    proc.stdout.on("data", (d) => { buf += d; const m = /http:\/\/127\.0\.0\.1:\d+/.exec(buf); if (m) ok(m[0]); });
    proc.once("exit", (c) => no(new Error(`the lab server exited (${c}) before it answered`)));
  }), 20_000, "lab server start");
  const port2 = Number(new URL(base).port);
  if (FORBIDDEN_PORTS[port2]) { proc.kill(); throw new Error(`refused port ${port2}`); }
  return {
    base, reused: false,
    stop: () => { try { proc.stdin.end(); } catch { /* gone */ } setTimeout(() => { try { proc.kill(); } catch { /* gone */ } }, 1500).unref(); },
  };
}

// ------------------------------------------------------------------------------------------------- Chrome
async function launch() {
  const profile = join(PROFILE_ROOT, `labshot-${Date.now()}-${process.pid}`);
  mkdirSync(profile, { recursive: true });
  const proc = spawn(CHROME_EXE, chromeFlags(profile), { stdio: "ignore", windowsHide: true });
  const exited = new Promise((r) => proc.once("exit", r));
  const portFile = join(profile, "DevToolsActivePort");
  const t0 = Date.now();
  let port = null, path = null;
  while (Date.now() - t0 < DEVTOOLS_WAIT_MS && !port) {
    if (proc.exitCode !== null) throw new Error(`chrome exited at start (code ${proc.exitCode})`);
    try { const [p, w] = readFileSync(portFile, "utf8").split(/\r?\n/); if (p && w) { port = Number(p); path = w; } } catch { /* not yet */ }
    if (!port) await delay(50);
  }
  if (!port) throw new Error("chrome wrote no DevToolsActivePort");
  const cdp = await connect(`ws://127.0.0.1:${port}${path}`);
  const version = (await cdp.send("Browser.getVersion")).product;
  let target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
  if (!target) {
    await cdp.send("Target.createTarget", { url: "about:blank" });
    target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
  }
  const page = await connect(target.webSocketDebuggerUrl);
  const events = [];
  page.on((msg) => {
    const p = msg.params;
    if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "warning")) {
      events.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
    } else if (msg.method === "Runtime.exceptionThrown") {
      events.push({ type: "exception", text: String(p.exceptionDetails.exception?.description || p.exceptionDetails.text).slice(0, 400) });
    } else if (msg.method === "Log.entryAdded" && p.entry.level === "error") {
      events.push({ type: "log-error", text: String(p.entry.text).slice(0, 400), url: p.entry.url });
    }
  });
  for (const d of ["Runtime", "Log", "Page"]) await page.send(`${d}.enable`);
  const evaluate = async (expression, ms = 10_000) => {
    const r = await withTimeout(page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }), ms, expression.slice(0, 80));
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const close = async () => {
    if (proc.exitCode === null) {
      try { await withTimeout(cdp.send("Browser.close"), 3000, "Browser.close"); } catch { /* wedged */ }
      const gone = await Promise.race([exited.then(() => true), delay(4000).then(() => false)]);
      if (!gone) { spawnSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { windowsHide: true, timeout: 15_000 }); await Promise.race([exited, delay(3000)]); }
    }
    page.close(); cdp.close();
    // Chrome's children let go of the profile a moment after the browser exits: try a few times, briefly.
    for (let attempt = 1; attempt <= 10; attempt += 1) {
      try { rmSync(profile, { recursive: true, force: true }); break; } catch { await delay(300); }
    }
  };
  const killSync = () => { if (proc.exitCode === null) spawnSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { windowsHide: true, timeout: 15_000 }); };
  return { proc, page, cdp, version, events, evaluate, close, killSync };
}

// Counts every getContext the page asks for, from before its first script (ruling 5's receipt).
const COUNT_CONTEXTS = `(() => { const orig = HTMLCanvasElement.prototype.getContext; window.__ctxCalls = [];
  HTMLCanvasElement.prototype.getContext = function (kind, ...rest) { window.__ctxCalls.push(String(kind)); return orig.call(this, kind, ...rest); }; })();`;

const VIEW_ACTIONS = {
  bench: "true",
  shelf: `(() => { const b = document.querySelector('[data-tab="shelf"]'); if (!b) return false; b.click(); return true; })()`,
  // a loved shader on stage; view only, its filmstrip is played (an image stepped frame by frame: no GPU work)
  stage: `(() => { const b = document.querySelector('.wb-shelf-card:not(.is-study-only) .wb-stage-btn'); if (!b) return false; b.click();
    const p = document.querySelector('.wb-film-play:not([hidden])'); if (p) p.click(); return true; })()`,
  study: `(() => { document.querySelector('[data-tab="shelf"]')?.click(); const b = document.querySelector('.wb-shelf-card .wb-study-btn');
    if (!b) return false; b.click(); return true; })()`,
  // a built module inside the family tree: open its family and category, then pick it
  module: `(() => { const b = document.querySelector('.wb-family .wb-module.is-built'); if (!b) return false;
    for (let d = b.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
    b.click(); b.scrollIntoView({ block: 'center' }); return true; })()`,
  // a built recipe (its knobs are generated by params-ui)
  recipe: `(() => { const rows = [...document.querySelectorAll('.wb-module.is-built')];
    const b = rows.find((r) => /^groups\\//.test(r.dataset.path || '')) || rows[0]; if (!b) return false;
    for (let d = b.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
    b.click(); b.scrollIntoView({ block: 'center' }); return true; })()`,
};

async function shoot(browser, base, view, w, h, outDir) {
  const { page, evaluate } = browser;
  await page.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await page.send("Page.navigate", { url: `${base}/lab/` });
  const t0 = Date.now();
  let state = null;
  while (Date.now() - t0 < PAGE_WAIT_MS) {
    try { state = await evaluate("(() => { const R = window.__lab; return R ? { ready: R.ready, error: R.error, stage: R.stage } : null; })()", 3000); } catch { state = null; }
    if (state && (state.ready || state.error)) break;
    await delay(200);
  }
  const acted = await evaluate(VIEW_ACTIONS[view]).catch((e) => `error: ${e.message}`);
  // the study note is fetched; the filmstrip's contact sheet is a CSS background the image wait below cannot see
  await delay(view === "study" ? 900 : view === "stage" ? 1600 : 400);
  // Let the lazy pictures in view arrive (a still is a PNG from the same server), up to a limit.
  const t1 = Date.now();
  while (Date.now() - t1 < IMAGES_WAIT_MS) {
    const left = await evaluate("[...document.images].filter((i) => { const r = i.getBoundingClientRect(); return r.width && r.bottom > 0 && r.top < innerHeight && !i.complete && !i.closest('details:not([open])'); }).length").catch(() => 0);
    if (!left) break;
    await delay(200);
  }
  const facts = await evaluate(`(() => ({ canvases: document.querySelectorAll('canvas').length, contexts: (window.__ctxCalls || []).slice(),
    scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
    images: [...document.images].filter((i) => i.complete && i.naturalWidth).length,
    broken: [...document.images].filter((i) => i.complete && !i.naturalWidth).map((i) => i.getAttribute('src')).slice(0, 12),
    pending: [...document.images].filter((i) => { const r = i.getBoundingClientRect(); return r.width && r.bottom > 0 && r.top < innerHeight && !i.complete && !i.closest('details:not([open])'); })
      .map((i) => i.getAttribute('src')).slice(0, 12),
    live: !!(window.__lab && window.__lab.live), runButton: !!document.querySelector('.wb-run'),
    liveOffLine: document.body.innerText.includes(${JSON.stringify(LIVE_OFF_WORDS.replace(/\.$/, ""))}),
    receiptOffLine: ((document.querySelector('.wb-insp-receipt') || {}).innerText || '').includes(${JSON.stringify(LIVE_OFF_WORDS.replace(/\.$/, ""))}),
    stage: window.__wb ? window.__wb.stage.state() : null }))()`);
  const shot = await withTimeout(page.send("Page.captureScreenshot", { format: "png" }), 30_000, "screenshot");
  const file = join(outDir, `${view}-${w}x${h}.png`);
  writeFileSync(file, Buffer.from(shot.data, "base64"));
  return { view, w, h, file, state, acted, ...facts, wall_ms: Date.now() - t0 };
}

// --------------------------------------------------------------------------------------- the run view (SwiftShader)
const STAGE_STATE = "(() => window.__wb ? window.__wb.stage.state() : null)()";
const RECEIPT_TEXT = "(() => { const r = document.querySelector('.wb-receipt-sheet'); return r ? r.innerText.slice(0, 2000) : null; })()";

// Put `subject` on stage from its Shelf card, press Run, and watch what the Stage does with it on SwiftShader: the
// pre-flight's verdict, the Shelf tab stopping the loop, no restart without a click, and (with raiseTo) the watchdog
// holding the last frame once a larger scale makes frames struggle. Every page call has a deadline; the longest any
// call waited is recorded (maxEvalMs), so a page that hung would show as a number here rather than as a hung driver.
async function shootRun(browser, base, subject, raiseTo, w, h, outDir, budgetLeft, dpr = 1, grow = null) {
  const { page, evaluate } = browser;
  const t0 = Date.now();
  const log = [], files = [];
  let maxEval = 0;
  const view = { w, h, dpr };   // the window as it is now (--grow changes it mid-run)
  const ev = async (expr, ms = 15_000) => {
    const a = Date.now();
    try { return await evaluate(expr, ms); } finally { maxEval = Math.max(maxEval, Date.now() - a); }
  };
  const note = (what, extra = {}) => { log.push({ at_ms: Date.now() - t0, what, ...extra }); say(`run ${subject}: ${what}`); };
  const snap = async (phase) => {
    // at a device pixel ratio above 1 the picture is scaled back to CSS pixels, so it stays a w x h image
    const clip = view.dpr > 1 ? { clip: { x: 0, y: 0, width: view.w, height: view.h, scale: 1 / view.dpr } } : {};
    const shot = await withTimeout(page.send("Page.captureScreenshot", { format: "png", ...clip }), 30_000, "screenshot");
    const file = join(outDir, `run-${subject}${dpr > 1 ? `-dpr${dpr}` : ""}-${phase}-${view.w}x${view.h}.png`);
    writeFileSync(file, Buffer.from(shot.data, "base64"));
    files.push(file);
  };
  // What the size checks read from the Stage's state.
  const sizeFacts = (s) => (s ? { running: s.running, tripped: s.tripped, refused: s.refused, scale: s.scale, canvas: s.canvas,
    measures: s.measures, basis: s.basis, fullSize: s.preflight && s.preflight.fullSize, predictedMs: s.preflight && s.preflight.predictedMs,
    how: s.preflight && s.preflight.how, worstGapMs: s.worstGapMs, recentGapsMs: s.recentGapsMs, trip: s.trip,
    status: s.status } : null);
  const out = (extra) => ({ view: "run", subject, w, h, dpr, files, log, maxEvalMs: maxEval, wall_ms: Date.now() - t0, ...extra });
  const left = () => budgetLeft - (Date.now() - t0);
  await page.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: dpr, mobile: false });
  // The live switch's address half; withLiveSwitch (the caller) has set the key half in this private profile.
  await page.send("Page.navigate", { url: `${base}/lab/?${LIVE_SWITCH.param}=${LIVE_SWITCH.value}` });
  let boot = null;
  for (let t = Date.now(); Date.now() - t < PAGE_WAIT_MS;) {
    boot = await ev("(() => { const R = window.__lab; return R ? { ready: R.ready, error: R.error, live: !!R.live } : null; })()", 3000).catch(() => null);
    if (boot && (boot.ready || boot.error)) break;
    await delay(200);
  }
  if (!boot || !boot.live) return out({ error: `the live switch did not turn on for the run view (${JSON.stringify(boot)})` });
  const put = await ev(`(() => { document.querySelector('[data-tab="shelf"]')?.click();
    const b = document.querySelector('.wb-shelf-card[data-id="${subject}"] .wb-stage-btn'); if (!b) return false; b.click(); return true; })()`);
  if (!put) return out({ error: `no "Put on stage" for ${subject} (study only, or not on the Shelf)` });
  await delay(500);
  const before = await ev(STAGE_STATE);
  note("on stage", { label: before && before.label, cost: before && before.cost, status: before && before.status });
  await ev("(() => { document.querySelector('.wb-run').click(); return true; })()");
  let s = null;
  for (let t = Date.now(); Date.now() - t < Math.min(PREFLIGHT_WAIT_MS, left() - 20_000);) {
    s = await ev(STAGE_STATE, 20_000).catch(() => null);
    if (s && (s.refused || s.running || s.tripped || s.halted)) break;
    await delay(250);
  }
  note("pre-flight", { preflight: s && s.preflight, refused: s && s.refused, running: s && s.running, scale: s && s.scale,
    canvas: s && s.canvas, status: s && s.status });
  await delay(s && s.running ? 1500 : 300);
  await snap("preflight");
  const result = { preflight: s && s.preflight, refused: s && s.refused, receipt: await ev(RECEIPT_TEXT).catch(() => null) };
  if (!s || !s.running) return out({ ...result, final: s });

  // Running: the Shelf tab must stop it, and coming back must not restart it.
  s = await ev(STAGE_STATE);
  note("running", { frames: s.frames, scale: s.scale, canvas: s.canvas });
  await ev("(() => { document.querySelector('[data-tab=\"shelf\"]').click(); return true; })()");
  await delay(300);
  const away1 = await ev(STAGE_STATE);
  await delay(1000);
  const away2 = await ev(STAGE_STATE);
  note("Shelf tab", { running: away2.running, halted: away2.halted, framesWhileAway: away2.frames - away1.frames });
  await ev("(() => { document.querySelector('[data-tab=\"bench\"]').click(); return true; })()");
  await delay(1000);
  const back = await ev(STAGE_STATE);
  note("back on the Workbench", { running: back.running, halted: back.halted, label: back.label, status: back.status,
    framesSinceAway: back.frames - away2.frames });
  await snap("stopped");
  result.shelfTab = { stoppedOnShelf: !away2.running && away2.frames === away1.frames, restartedByItself: back.running };
  await ev("(() => { document.querySelector('.wb-run').click(); return true; })()");
  await delay(1000);
  s = await ev(STAGE_STATE);
  note("Run again", { running: s.running, frames: s.frames, scale: s.scale });

  // The window changes size mid-run: the Stage must measure again at the new size before its next frame. The drawing
  // buffer it then uses must be the one that measurement locked, and no frame may come near the one-frame limit.
  if (grow && s.running) {
    const before = sizeFacts(await ev(STAGE_STATE));
    await page.send("Emulation.setDeviceMetricsOverride", { width: grow.w, height: grow.h, deviceScaleFactor: grow.dpr, mobile: false });
    Object.assign(view, grow);
    await delay(1500);
    const after = sizeFacts(await ev(STAGE_STATE, 20_000).catch(() => null));
    const b0 = before && before.basis, b1 = after && after.basis;
    result.grow = { to: grow, before, after,
      measuredAgain: !!(before && after && after.measures > before.measures),
      // the measurement that now holds was taken over the new window: its box and pixel ratio, not the old ones
      measuredTheNewBox: !!(b0 && b1 && b1.dpr === grow.dpr && (b1.w !== b0.w || b1.h !== b0.h || b1.dpr !== b0.dpr)),
      ratioSeen: b1 ? b1.dpr : null };
    note("grown", { measuredAgain: result.grow.measuredAgain, measuredTheNewBox: result.grow.measuredTheNewBox,
      scale: after && after.scale, canvas: after && after.canvas, worstGapMs: after && after.worstGapMs });
    await snap("grown");
    s = (await ev(STAGE_STATE).catch(() => null)) || s;
  }

  // Climb toward --raise through the scale menu, as a person would: the Stage's ladder takes one step at a time, after
  // frames are measured at the current scale, and refuses a step predicted past the one-frame limit. Ask, let it draw
  // a moment, ask again, until it reaches the scale, refuses, or the watchdog holds the last frame.
  let tripped = null;
  const watchUntil = Date.now() + Math.min(TRIP_WAIT_MS, left() - 15_000);
  if (raiseTo && s.running) {
    const attempts = [];
    while (Date.now() < watchUntil) {
      await delay(1200);
      s = await ev(STAGE_STATE, 20_000).catch(() => null);
      if (!s || s.tripped || !s.running) { if (s && s.tripped) tripped = s; break; }
      if (s.scale >= raiseTo) break;
      const before = s.scale;
      const got = await ev(`(() => { const sel = document.querySelector('.wb-scale'); sel.value = '${raiseTo}';
        sel.dispatchEvent(new Event('change')); const st = window.__wb.stage.state(); return { scale: st.scale, status: st.status }; })()`);
      attempts.push({ at_ms: Date.now() - t0, from: before, asked: raiseTo, got: got.scale, status: got.status });
      if (got.scale === before && !/let it draw/i.test(got.status)) break;   // refused by a prediction: the top of the ladder
    }
    note("raise", { attempts });
    result.raise = attempts;
  }
  for (; !tripped && Date.now() < watchUntil;) {
    s = await ev(STAGE_STATE, 20_000).catch(() => null);
    if (s && s.tripped) { tripped = s; break; }
    await delay(250);
  }
  if (tripped) {
    note("watchdog held the last frame", { trip: tripped.trip, status: tripped.status });
    await delay(1000);
    const after = await ev(STAGE_STATE);
    note("after the hold", { framesSince: after.frames - tripped.frames, running: after.running, canvas: after.canvas });
    result.trip = { ...tripped.trip, framesAfterHold: after.frames - tripped.frames, status: tripped.status };
  } else {
    note("no hold within the watch", { running: s && s.running, frames: s && s.frames, scale: s && s.scale });
    await ev("(() => { window.__wb.stage.stop(); return true; })()").catch(() => null);
  }
  await snap(tripped ? "held" : "watched");
  result.receipt = await ev(RECEIPT_TEXT).catch(() => result.receipt);
  const final = await ev(STAGE_STATE).catch(() => null);
  result.worstGapMs = final ? final.worstGapMs : null;   // the slowest frame of the whole run (under the 500 ms limit, or held there)
  return out({ ...result, final });
}

// The run view's live switch, key half: set in this private headless profile (SwiftShader, judged before any page) by
// a script that runs before each document, for the run view only; removed, and the key cleared, when it is done, so
// the views shot after it open view only again (they also lack ?live=1, which alone keeps the switch off).
async function withLiveSwitch(browser, fn) {
  const KEY = JSON.stringify(LIVE_SWITCH.key), VALUE = JSON.stringify(LIVE_SWITCH.keyValue);
  const { identifier } = await browser.page.send("Page.addScriptToEvaluateOnNewDocument",
    { source: `try { localStorage.setItem(${KEY}, ${VALUE}); } catch (e) { /* off: the run view reports it */ }` });
  try {
    return await fn();
  } finally {
    await browser.page.send("Page.removeScriptToEvaluateOnNewDocument", { identifier }).catch(() => {});
    await browser.evaluate(`(() => { try { localStorage.removeItem(${KEY}); } catch (e) { /* gone */ } return true; })()`).catch(() => {});
  }
}

async function main(opt) {
  const outDir = resolve(REPO, opt.out);
  if (!underState(outDir)) throw new Error(`--out must be under ${join(REPO, "state")} (gitignored): ${outDir}`);
  mkdirSync(outDir, { recursive: true });
  const sizes = String(opt.sizes).split(",").map((s) => s.trim().split("x").map(Number)).filter(([a, b]) => a > 0 && b > 0);
  const views = String(opt.views).split(",").map((s) => s.trim()).filter((v) => VIEWS.includes(v));
  const receipt = { api: SHOT_API, started_at: new Date().toISOString(), sizes, views, shots: [], renderer: null,
    chrome: null, server: null, lock: null, error: null, rule5: null };
  const save = () => writeFileSync(join(outDir, "receipt.json"), JSON.stringify(receipt, null, 1));
  const roots = {};
  if (opt.lib) roots.lib = resolve(REPO, opt.lib);
  if (opt.cards) roots.cards = resolve(REPO, opt.cards);
  const server = await labServer(Number(opt.port), roots);
  receipt.server = { base: server.base, reused: server.reused, roots: Object.keys(roots).length ? roots : "the house roots" };
  const { acquireGpuLock } = await import("../lanes/gpu_lock.mjs");
  const lockT0 = Date.now();
  const gpu = await acquireGpuLock({ label: "lab screenshot", maxHoldMs: 4 * 60_000, maxWaitMs: 10 * 60_000, signals: false });
  const heldFrom = Date.now();
  receipt.lock = { wait_ms: heldFrom - lockT0 };
  let browser = null;
  const unguard = guardHolder({ kill: () => browser && browser.killSync(), release: () => gpu.release() });
  try {
    browser = await launch();
    receipt.chrome = browser.version;
    const renderer = await browser.evaluate(`(() => { const c = document.createElement("canvas"); const g = c.getContext("webgl2");
      if (!g) return null; const d = g.getExtension("WEBGL_debug_renderer_info");
      const r = d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER);
      const l = g.getExtension("WEBGL_lose_context"); if (l) l.loseContext(); return r; })()`, 15_000);
    receipt.renderer = renderer;
    const judged = judgeRenderer(renderer);
    if (!judged.ok) throw new Error(`refused: ${judged.reason}`);
    say(`chrome ${browser.version}; renderer ${renderer}`);
    await browser.page.send("Page.addScriptToEvaluateOnNewDocument", { source: COUNT_CONTEXTS });
    const subjects = String(opt.subjects || "").split(",").map((s) => s.trim()).filter((s) => /^[A-Za-z0-9]{6}$/.test(s));
    const raiseTo = SCALES.includes(Number(opt.raise)) ? Number(opt.raise) : null;
    const dpr = Number(opt.dpr) >= 1 && Number(opt.dpr) <= 4 ? Number(opt.dpr) : 1;   // a HiDPI display, emulated
    const gm = /^(\d{3,4})x(\d{3,4})(?:@(\d(?:\.\d+)?))?$/.exec(String(opt.grow || ""));
    const grow = gm ? { w: Number(gm[1]), h: Number(gm[2]), dpr: Math.min(4, Math.max(1, Number(gm[3] || dpr))) } : null;
    receipt.grow = grow;
    receipt.runs = [];
    for (const [w, h] of sizes) {
      for (const view of views) {
        if (Date.now() - heldFrom > BURST_MS - 30_000) { say("burst budget reached; the rest is skipped"); receipt.skipped = true; break; }
        browser.events.length = 0;
        if (view === "run") {
          for (const subject of subjects) {
            const budgetLeft = BURST_MS - 20_000 - (Date.now() - heldFrom);
            if (budgetLeft < 40_000) { say(`burst budget reached; run ${subject} is skipped`); receipt.skipped = true; break; }
            browser.events.length = 0;
            const row = await withLiveSwitch(browser, () => shootRun(browser, server.base, subject, raiseTo, w, h, outDir, budgetLeft, dpr, grow));
            row.console = browser.events.slice(0, 20);
            receipt.runs.push(row);
            save();
          }
          continue;
        }
        const row = await shoot(browser, server.base, view, w, h, outDir);
        row.console = browser.events.slice(0, 20);
        receipt.shots.push(row);
        say(`${view} ${w}x${h}: ${row.file} (canvases ${row.canvases}, contexts ${row.contexts.length}, images ${row.images}, broken ${row.broken.length})`);
        save();
      }
    }
    receipt.rule5 = !receipt.shots.length ? "not checked: no view but run"
      : receipt.shots.every((s) => s.canvases === 0 && s.contexts.length === 0 && !s.live && !s.runButton && s.liveOffLine && s.receiptOffLine)
        ? "held: view only (the switch off, no Run button, the line said on the Stage and in the Inspector's receipt) with no canvas and no WebGL context on every view but run"
        : "BROKEN: a view was not view only, created a canvas or asked for a context";
  } catch (e) {
    receipt.error = String(e && e.stack || e);
    say("error:", receipt.error.split("\n")[0]);
  } finally {
    if (browser) await browser.close();   // our Chrome first, the lock second
    gpu.release();
    unguard();
    server.stop();
    receipt.lock.held_ms = Date.now() - heldFrom;
    receipt.finished_at = new Date().toISOString();
    save();
  }
  return receipt.error ? 1 : 0;
}

if (process.argv[1] && resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()) {
  const { values: opt } = parseArgs({ options: {
    out: { type: "string" }, sizes: { type: "string", default: "1440x900,900x1200" },
    views: { type: "string", default: "bench,shelf,stage,study" }, port: { type: "string", default: "8797" },
    lib: { type: "string" }, cards: { type: "string" }, subjects: { type: "string", default: "" },
    raise: { type: "string", default: "" }, dpr: { type: "string", default: "1" }, grow: { type: "string", default: "" } } });
  if (!opt.out || isAbsolute(opt.out) && !underState(opt.out)) {
    console.log("usage: node arsenal/shaders/lab_shot.mjs --out state/arsenal/shaders/labshots/<run> [--sizes WxH,...] [--views " + VIEWS.join(",") + "] [--lib DIR --cards DIR] [--subjects ID,... --raise SCALE --dpr N --grow WxH@N]");
    process.exit(2);
  }
  if (!existsSync(CHROME_EXE)) { console.log(`no Chrome at ${CHROME_EXE}`); process.exit(1); }
  process.exit(await main(opt));
}
