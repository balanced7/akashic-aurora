// The shader lab's headless driver. It renders shader pages in a private, headless Chrome forced onto SwiftShader (the
// CPU), under the house GPU lock, and writes what each page reported (window.__render) plus its PNG frames.
//
//   node arsenal/shaders/headless.mjs --plan <plan.json> --result <result.json>   one burst; render.py writes the plan
//   node arsenal/shaders/headless.mjs --check-renderer "<renderer string>"         the SwiftShader judgement, as JSON
//   node arsenal/shaders/headless.mjs --print-flags                                the Chrome flags, as JSON
//
// WHY THE CPU. This host has an AMD display-driver crash (TDR) history, and a shader corpus is exactly the workload that
// trips one: hundreds of strangers' raymarchers, some of which loop for seconds per pixel. So no frame here is ever drawn
// on the GPU. Chrome starts headless with ANGLE on SwiftShader, Direct3D 11 off, and hardware video decode and GPU
// compositing off (measured 2026-10-13 on Chrome 155: SystemInfo then lists SwiftShader as the only GPU device, and
// video_decode / gpu_compositing read "disabled_software"). Before any job page loads, the driver reads the browser's own
// GPU report and a WebGL2 context's WEBGL_debug_renderer_info, and refuses to render (exit 3) unless both name
// SwiftShader and neither names hardware. Each page's own renderer string is judged again before its frames are kept.
//
// WHY A FRESH PROFILE PER LAUNCH. A second chrome.exe pointed at a profile a live Chrome still holds hands its command
// line to that Chrome and exits, and the driver would be talking to a browser it did not start. Each launch gets its
// own directory under state/arsenal/shaders/chrome-profile/, removed afterwards. --remote-debugging-port=0 plus the
// DevToolsActivePort file the profile receives means the driver can only ever connect to the Chrome it launched.
//
// WHY BURSTS. arsenal/GPU-LOCK.md: one headless render at a time on this machine, bursts under three minutes, release
// between bursts. A burst is the lock's whole hold: Chrome's launch, the jobs, any relaunch after a timeout, and the
// shutdown. So every job's deadline ends SHUTDOWN_MARGIN_MS before the burst does (jobWindow), a later job starts only
// if its whole deadline still fits, and a relaunch begins only if a slow one (LAUNCH_RESERVE_MS) still leaves room for
// the shutdown (mayRelaunch). The rest come back "deferred" and render.py runs them in the next burst, after this
// process has released the lock.
//
// WHAT A PLAN MAY ASK. Before the lock is taken or Chrome launched, every job is checked (jobRefusal): it loads a lab
// page of the shader server on http://127.0.0.1:<port> (never port 8793, Daniel's server), its shader and media come
// from that same server, its frame prefix is a plain name, and it writes under <repo>/state/ (gitignored). Only a job
// that render.py marks allow_tracked, for a shader that is not from the corpus, may write elsewhere: pictures of other
// people's work never leave state/. One bad job refuses the whole plan (exit 3).
//
// KILLING ONLY OUR CHROME. Browser.close first; if the process is still alive, `taskkill /T /F` on the pid this script
// spawned, which ends that browser and its own children and nothing else (never Daniel's browser, never another lane's).
// A job that misses its deadline (a page wedged in a long SwiftShader draw) costs a full Chrome restart: a fresh GPU
// process is the only reliable way to stop a draw call that is still running. On a signal or a crash exit the order is
// the same as at the end of a burst: our Chrome dies first, the lock is released second (guardHolder).
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
export const PLAN_API = "arsenal.shader-headless-plan/v1";
export const RESULT_API = "arsenal.shader-headless/v1";
export const CHROME_EXE = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
export const STATE_ROOT = join(REPO, "state");   // gitignored: where every job writes (see WHAT A PLAN MAY ASK)
export const PROFILE_ROOT = join(STATE_ROOT, "arsenal", "shaders", "chrome-profile");
export const BURST_MS = 170_000;           // GPU-LOCK.md: under 3 minutes, launch and shutdown included
export const LOCK_HOLD_MS = 4 * 60_000;    // the cap declared in owner.json: the burst plus shutdown, with margin
export const DEFAULT_LOCK_WAIT_MS = 10 * 60_000;
export const DEVTOOLS_WAIT_MS = 20_000;
// Browser.close (3 s), the wait for its exit (4 s), taskkill (about 1 s) and the wait after it (3 s), the profile's
// removal (3 s): about 13 s when Chrome is wedged. Every job's deadline ends this long before the burst does.
export const SHUTDOWN_MARGIN_MS = 15_000;
// A launch: the DevToolsActivePort file (DEVTOOLS_WAIT_MS), then SystemInfo and the WebGL2 check (15 s each, at most).
export const LAUNCH_RESERVE_MS = DEVTOOLS_WAIT_MS + 30_000;
export const MIN_JOB_MS = 1_000;
export const POLL_MS = 200;
export const EXIT = { ok: 0, error: 1, usage: 2, refused: 3, lock: 4 };
export const FORBIDDEN_PORTS = { 8793: "Daniel's arsenal server (arsenal/serve.py)" };  // serve.py FORBIDDEN_PORTS
const PREFIX = /^[A-Za-z0-9_-]{0,64}$/;

// The three flags the contract requires, then belt and braces: nothing in this browser may open a Direct3D device on
// the AMD adapter (D3D11 off; hardware video decode and encode off; compositing in software).
export const SWIFTSHADER_FLAGS = ["--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
export const GPU_FENCE_FLAGS = ["--disable-d3d11", "--disable-accelerated-video-decode",
                                "--disable-accelerated-video-encode", "--disable-gpu-compositing"];
export const QUIET_FLAGS = ["--no-first-run", "--no-default-browser-check", "--mute-audio", "--disable-extensions",
                            "--disable-component-update", "--disable-sync", "--disable-default-apps", "--hide-scrollbars",
                            // a background tab throttles timers and rAF; the render page's watchdog must keep time
                            "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                            "--disable-backgrounding-occluded-windows"];
export const chromeFlags = (profile) => [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS,
                                         "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"];

// A renderer string names SwiftShader and no hardware. arsenal/shaders/render.py keeps the Python twin of this rule
// (judge_renderer); tests/test_shader_harness.py runs both over the same strings.
export const HARDWARE_HINT = /\b(amd|radeon|ati|nvidia|geforce|quadro|rtx|intel|iris|uhd graphics|adreno|mali|apple m\d|direct3d\d*|d3d\d+)\b/i;
export function judgeRenderer(renderer) {
  if (typeof renderer !== "string" || !renderer.trim()) {
    return { ok: false, reason: "no renderer string (no WebGL2 context, or WEBGL_debug_renderer_info is unavailable)" };
  }
  if (!/swiftshader/i.test(renderer)) return { ok: false, reason: `the renderer is not SwiftShader: ${renderer}` };
  const hw = HARDWARE_HINT.exec(renderer);
  if (hw) return { ok: false, reason: `the renderer names hardware (${hw[0]}): ${renderer}` };
  return { ok: true, reason: null };
}

// ---------------------------------------------------------------------------------------- what a plan may ask
// The real path of p's deepest existing ancestor, plus the rest: a junction under state/ cannot lead out of it.
function realish(p) {
  let head = p;
  const rest = [];
  while (!existsSync(head)) {
    const up = dirname(head);
    if (up === head) break;
    rest.unshift(basename(head));
    head = up;
  }
  try { head = realpathSync.native(head); } catch { /* keep it as written */ }
  return join(head, ...rest);
}

// True for an absolute path at or under <repo>/state/ (case-insensitive on Windows, as path.relative is there).
export function underState(dir) {
  if (typeof dir !== "string" || !isAbsolute(dir)) return false;
  const rel = relative(realish(resolve(STATE_ROOT)), realish(resolve(dir)));
  return rel === "" || (!isAbsolute(rel) && rel.split(sep)[0] !== "..");
}

// The lab server's origin a job URL names, or a reason it names none we load: http, 127.0.0.1 spelled exactly, an
// explicit port that is not Daniel's, no credentials, and a page under /lab/.
function labOrigin(url) {
  let u;
  try { u = new URL(String(url)); } catch { return { why: `not a URL: ${url}` }; }
  if (u.protocol !== "http:" || u.hostname !== "127.0.0.1" || !u.port || u.username || u.password) {
    return { why: `a job loads the shader lab server on http://127.0.0.1:<port> only, not ${url}` };
  }
  if (FORBIDDEN_PORTS[Number(u.port)]) return { why: `port ${u.port} is refused: it is ${FORBIDDEN_PORTS[u.port]}` };
  if (!u.pathname.startsWith("/lab/")) return { why: `a job loads a lab page (/lab/...), not ${u.pathname}` };
  return { u };
}

// Why the driver will not run this job, or null. render.py writes every plan, so a refusal here means a plan that was
// hand-edited or written by something else: the driver answers it before the lock is taken or Chrome launched.
export function jobRefusal(job) {
  if (!job || typeof job !== "object") return "a job is an object";
  const { u, why } = labOrigin(job.url);
  if (why) return why;
  let corpus = false;
  for (const name of ["src", "media"]) {  // the page fetches these: from the same server, or not at all
    const value = u.searchParams.get(name);
    if (value === null) continue;
    let target;
    try { target = new URL(value, u); } catch { return `${name} is not a URL: ${value}`; }
    if (target.origin !== u.origin) return `${name} must come from the lab server (${u.origin}), not ${target.origin}`;
    if (name === "src" && target.pathname.startsWith("/corpus/")) corpus = true;
  }
  if (!PREFIX.test(String(job.prefix ?? ""))) return `a frame prefix is a plain name, not ${JSON.stringify(job.prefix)}`;
  if (underState(job.out_dir)) return null;
  if (typeof job.out_dir !== "string" || !isAbsolute(job.out_dir)) return `out_dir must be an absolute path: ${job.out_dir}`;
  if (corpus) {
    return `out_dir ${job.out_dir} is outside ${STATE_ROOT}: pictures of a corpus shader (someone else's work) stay under `
      + "state/, which git ignores, whatever the plan says";
  }
  if (job.allow_tracked === true) return null;  // render.py --allow-tracked, for a shader of our own
  return `out_dir ${job.out_dir} is outside ${STATE_ROOT} (render.py's --allow-tracked lets a non-corpus shader out)`;
}

export function planRefusal(plan) {
  if (!plan || !Array.isArray(plan.jobs)) return "a plan's jobs are a list";
  for (const job of plan.jobs) {
    const why = jobRefusal(job);
    if (why) return `job ${job?.key ?? "?"}: ${why}`;
  }
  return null;
}

// ------------------------------------------------------------------------------------------- the burst's budget
// Whether job `index` may start `elapsedMs` into the burst, and its deadline. Every job, the first included, ends
// SHUTDOWN_MARGIN_MS before the burst does. A later job starts only if its whole requested timeout fits, so the budget
// never cuts one short; the first starts with whatever fits (a burst must make progress), unless that is under a second.
export function jobWindow({ index, elapsedMs, timeoutMs, burstMs = BURST_MS, marginMs = SHUTDOWN_MARGIN_MS }) {
  const roomMs = burstMs - marginMs - elapsedMs;
  if (roomMs < MIN_JOB_MS || (index > 0 && timeoutMs > roomMs)) return { start: false, deadlineMs: 0, roomMs };
  return { start: true, deadlineMs: Math.min(timeoutMs, roomMs), roomMs };
}

// A relaunch (after a timeout) begins only if even a slow one still leaves the shutdown its margin.
export const mayRelaunch = (elapsedMs, burstMs = BURST_MS) => elapsedMs + LAUNCH_RESERVE_MS + SHUTDOWN_MARGIN_MS <= burstMs;

// A job whose deadline the budget cut short tells its page so: the page's own watchdog (budget=) then fires 5 s before
// the driver's deadline, and the page reports what it has instead of being killed mid-draw.
export function clipBudget(url, deadlineMs) {
  const cap = Math.max(MIN_JOB_MS, deadlineMs - 5000);
  return String(url).replace(/([?&]budget=)(\d+)/, (_, key, value) => `${key}${Math.min(Number(value), cap)}`);
}

// ----------------------------------------------------------------------------------------------- the house lock
// How the driver asks for the lock. lock_wait_ms 0 means "do not wait" (one try, then one poll), never the default.
// signals: false, because gpu_lock.mjs's own signal handlers would release the lock before our Chrome is dead
// (they are prepended); guardHolder installs the driver's own, in the right order.
export function lockOptions(plan = {}) {
  const wait = plan.lock_wait_ms;
  return { label: plan.label || "shader render", maxHoldMs: LOCK_HOLD_MS, signals: false,
           maxWaitMs: typeof wait === "number" && Number.isFinite(wait) && wait >= 0 ? wait : DEFAULT_LOCK_WAIT_MS };
}

// On the way out our Chrome dies first and the lock goes second, so no waiter (a load-sensitive jam lane above all)
// takes the lock while our SwiftShader browser still burns CPU. The exit handler is PREPENDED, ahead of the one
// gpu_lock.mjs registered when the lock was taken. Returns the function that removes these handlers again.
export function guardHolder({ kill, release, exit = (code) => process.exit(code), proc = process }) {
  const handlers = {};
  const off = () => {
    proc.removeListener("exit", onExit);
    for (const [sig, fn] of Object.entries(handlers)) proc.removeListener(sig, fn);
  };
  const down = () => { off(); try { kill(); } finally { release(); } };
  const onExit = () => down();
  for (const [sig, code] of [["SIGINT", 130], ["SIGTERM", 143], ["SIGHUP", 129]]) {
    handlers[sig] = () => { down(); exit(code); };
    proc.on(sig, handlers[sig]);
  }
  proc.prependListener("exit", onExit);
  return off;
}

const stampNow = () => new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const say = (...a) => console.log("[headless]", ...a);

function withTimeout(promise, ms, what) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(Object.assign(new Error(`no answer within ${ms} ms: ${what}`), { timeout: true })), ms);
  })]).finally(() => clearTimeout(timer));
}

// The house CDP client (arsenal/lanes/chrome_verify.mjs), plus a close and a fail-fast when the socket drops.
function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(JSON.stringify(msg.error)));
        else res(msg.result);
      } else if (msg.method) {
        for (const listener of listeners) listener(msg);
      }
    };
    ws.onclose = () => { for (const { rej } of pending.values()) rej(new Error("DevTools socket closed")); pending.clear(); };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => {
        if (ws.readyState !== 1) return rej(new Error("DevTools socket closed"));
        const id = nextId++;
        pending.set(id, { res, rej });
        ws.send(JSON.stringify({ id, method, params }));
      }),
      on: (fn) => listeners.push(fn),
      close: () => { try { ws.close(); } catch { /* already closed */ } },
    });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}

// ------------------------------------------------------------------------------------------------------- Chrome
class Browser {
  constructor(exe) { this.exe = exe; this.proc = null; this.profile = null; this.cdp = null; this.page = null; this.events = []; }

  async launch() {
    const t0 = Date.now();
    this.profile = join(PROFILE_ROOT, `run-${stampNow()}-${process.pid}-${Math.random().toString(36).slice(2, 7)}`);
    mkdirSync(this.profile, { recursive: true });
    this.flags = chromeFlags(this.profile);
    this.proc = spawn(this.exe, this.flags, { stdio: "ignore", windowsHide: true });
    this.exited = new Promise((res) => this.proc.once("exit", res));
    this.proc.once("error", (e) => say("chrome failed to start:", e.message));
    const portFile = join(this.profile, "DevToolsActivePort");
    let port = null, path = null;
    while (Date.now() - t0 < DEVTOOLS_WAIT_MS && !port) {
      if (this.proc.exitCode !== null) throw new Error(`chrome exited at start (code ${this.proc.exitCode})`);
      try {
        const [p, w] = readFileSync(portFile, "utf8").split(/\r?\n/);
        if (p && w) { port = Number(p); path = w; }
      } catch { /* not written yet */ }
      if (!port) await delay(50);
    }
    if (!port) throw new Error(`chrome wrote no DevToolsActivePort within ${DEVTOOLS_WAIT_MS} ms`);
    this.port = port;
    this.cdp = await connect(`ws://127.0.0.1:${port}${path}`);
    this.version = (await this.cdp.send("Browser.getVersion")).product;
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    let target = targets.find((t) => t.type === "page");
    if (!target) {
      await this.cdp.send("Target.createTarget", { url: "about:blank" });
      target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
    }
    this.page = await connect(target.webSocketDebuggerUrl);
    this.page.on((msg) => {
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "warning" || p.type === "assert")) {
        this.events.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 600) });
      } else if (msg.method === "Runtime.exceptionThrown") {
        const d = p.exceptionDetails;
        this.events.push({ type: "exception", text: String(d.exception?.description || d.text).slice(0, 600), url: d.url, line: d.lineNumber });
      } else if (msg.method === "Log.entryAdded" && (p.entry.level === "error" || p.entry.level === "warning")) {
        this.events.push({ type: `log-${p.entry.level}`, text: String(p.entry.text).slice(0, 600), url: p.entry.url });
      }
    });
    for (const domain of ["Runtime", "Log", "Page"]) await this.page.send(`${domain}.enable`);
    this.startMs = Date.now() - t0;
    return this.startMs;
  }

  // The browser's own GPU report and a WebGL2 context's renderer string, judged before any job page loads.
  async assertSoftware() {
    let sys = null;
    try { sys = await withTimeout(this.cdp.send("SystemInfo.getInfo"), 15_000, "SystemInfo.getInfo"); } catch (e) { sys = { error: e.message }; }
    const gpu = sys?.gpu || {};
    const sysRenderer = gpu.auxAttributes?.glRenderer || null;
    const devices = (gpu.devices || []).map((d) => ({ vendor: d.vendorString, device: d.deviceString, driver: d.driverVendor }));
    const webgl = await this.evaluate(`(() => { const c = document.createElement("canvas"); const g = c.getContext("webgl2");
      if (!g) return null; const d = g.getExtension("WEBGL_debug_renderer_info");
      const out = { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER),
                    version: g.getParameter(g.VERSION), float_targets: !!g.getExtension("EXT_color_buffer_float") };
      const lose = g.getExtension("WEBGL_lose_context"); if (lose) lose.loseContext(); return out; })()`, 15_000);
    const judged = judgeRenderer(webgl?.renderer);
    const sysJudged = judgeRenderer(sysRenderer);
    const hwDevice = devices.find((d) => !judgeRenderer(`${d.device} ${d.vendor} ${d.driver}`).ok);
    const ok = judged.ok && sysJudged.ok && !hwDevice;
    return {
      ok, reason: ok ? null : (judged.reason || sysJudged.reason || `the GPU report lists a hardware device: ${JSON.stringify(hwDevice)}`),
      webgl, gl_renderer: sysRenderer, gl_implementation: gpu.auxAttributes?.glImplementationParts || null,
      devices, feature_status: gpu.featureStatus || null, sysinfo_error: sys?.error || null,
    };
  }

  async evaluate(expression, ms = 10_000) {
    const r = await withTimeout(this.page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }),
                                ms, expression.replace(/\s+/g, " ").slice(0, 100));
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  }

  // Browser.close, then taskkill on our own pid's tree if it is still running. Returns how it ended.
  async close() {
    if (!this.proc) return null;
    const pid = this.proc.pid;
    let how = "already-exited";
    if (this.proc.exitCode === null) {
      try { await withTimeout(this.cdp?.send("Browser.close") ?? Promise.resolve(), 3000, "Browser.close"); } catch { /* wedged */ }
      const exited = await Promise.race([this.exited.then(() => true), delay(4000).then(() => false)]);
      how = "browser-close";
      if (!exited) {
        spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { windowsHide: true, timeout: 15_000 });
        await Promise.race([this.exited, delay(3000)]);
        how = "taskkill-tree";
      }
    }
    this.page?.close(); this.cdp?.close();
    for (let i = 0; i < 10; i += 1) {  // Chrome's children let go of the profile a moment after the browser exits
      try { rmSync(this.profile, { recursive: true, force: true }); break; } catch { await delay(300); }
    }
    this.proc = null;
    return { pid, how };
  }

  killSync() {  // the exit path: no awaits allowed
    if (this.proc && this.proc.exitCode === null) spawnSync("taskkill", ["/PID", String(this.proc.pid), "/T", "/F"], { windowsHide: true, timeout: 15_000 });
  }
}

// Profiles a killed driver left behind (older than an hour; a live run's profile is minutes old at most).
function sweepProfiles() {
  try {
    for (const name of readdirSync(PROFILE_ROOT)) {
      const p = join(PROFILE_ROOT, name);
      if (name.startsWith("run-") && Date.now() - statSync(p).mtimeMs > 3_600_000) rmSync(p, { recursive: true, force: true });
    }
  } catch { /* best effort */ }
}

// ---------------------------------------------------------------------------------------------------------- jobs
const tName = (t) => `t${Number(t).toFixed(2)}`;

async function runJob(browser, job, deadlineAt) {
  const t0 = Date.now();
  const nonce = `${process.pid}-${t0}-${Math.random().toString(36).slice(2, 8)}`;
  const url = `${job.url}${job.url.includes("?") ? "&" : "?"}job=${nonce}`;
  const row = { key: job.key, url: job.url, status: "error", render: null, frames: [], screenshot: null,
                console: [], error: null, wall_ms: 0, renderer_judged: null };
  browser.events = [];
  try {
    await browser.page.send("Emulation.setDeviceMetricsOverride", { width: job.w, height: job.h, deviceScaleFactor: 1, mobile: false });
    await browser.page.send("Page.navigate", { url });
    const probe = `(() => { if (!location.search.includes(${JSON.stringify("job=" + nonce)})) return "loading";
      const r = window.__render; return r ? (r.done ? "done" : "pending") : "no-render"; })()`;
    let state = "loading";
    while (Date.now() < deadlineAt) {
      try { state = await browser.evaluate(probe, Math.max(500, Math.min(5000, deadlineAt - Date.now()))); } catch (e) {
        state = e.timeout ? "unanswered (the page's main thread is busy)" : "loading";
      }
      if (state === "done") break;
      await delay(POLL_MS);
    }
    if (state !== "done") {
      row.status = "timeout";
      row.error = `the page did not finish within ${job.timeout_ms} ms (last state: ${state})`;
      try { row.render = await browser.evaluate(`(() => { const r = window.__render; if (!r) return null;
        return JSON.parse(JSON.stringify({ ...r, frames: (r.frames || []).map((f) => ({ t: f.t, ms: f.ms })) })); })()`, 1500); } catch { /* wedged */ }
      return row;
    }
    // The report first, without the PNGs; then each frame on its own, so no single DevTools message is huge. A frame's
    // other facts (render.js adds frame, frames walked, reset) ride along; a hole in the list stays a hole, so index i
    // here is index i in the page.
    row.render = await browser.evaluate(`(() => { const r = window.__render;
      return JSON.parse(JSON.stringify({ ...r, frames: (r.frames || []).map((f) => f ? ({ ...f, png: undefined,
        has_png: typeof f.png === "string" }) : { t: null, ms: null, has_png: false }) })); })()`, 10_000);
    const judged = judgeRenderer(row.render?.renderer ?? browser.renderer);
    row.renderer_judged = judged;
    if (!judged.ok) {
      row.status = "refused";
      row.error = `frames discarded: ${judged.reason}`;
      return row;
    }
    mkdirSync(job.out_dir, { recursive: true });
    const used = new Set();  // two times that round to one name (t=1 and t=1.001) must not overwrite each other
    for (let i = 0; i < (row.render?.frames || []).length; i++) {
      const { has_png: hasPng, ...f } = row.render.frames[i];
      if (!hasPng) { row.frames.push({ ...f, file: null, bytes: 0 }); continue; }
      const dataUrl = await browser.evaluate(`window.__render.frames[${i}].png`, 20_000);
      const m = /^data:image\/png;base64,(.*)$/s.exec(String(dataUrl || ""));
      const bytes = m ? Buffer.from(m[1], "base64") : null;
      if (!bytes || bytes.length < 8 || bytes.readUInt32BE(0) !== 0x89504e47) {
        row.frames.push({ ...f, file: null, bytes: 0, error: "not a PNG data URL" });
        continue;
      }
      let stem = `${job.prefix || ""}${tName(f.t)}`;
      if (used.has(stem)) stem = `${stem}_${i}`;
      used.add(stem);
      const file = join(job.out_dir, `${stem}.png`);
      writeFileSync(file, bytes);
      row.frames.push({ ...f, file, bytes: bytes.length });
    }
    if (job.screenshot) {
      const shot = await withTimeout(browser.page.send("Page.captureScreenshot", { format: "png" }), 30_000, "screenshot");
      row.screenshot = join(job.out_dir, `${job.prefix || ""}screenshot.png`);
      writeFileSync(row.screenshot, Buffer.from(shot.data, "base64"));
    }
    row.status = "done";
    return row;
  } catch (e) {
    row.status = e.timeout ? "timeout" : "error";
    row.error = String(e && e.message || e);
    return row;
  } finally {
    row.console = browser.events.slice(0, 40);
    row.wall_ms = Date.now() - t0;
  }
}

// ---------------------------------------------------------------------------------------------------------- burst
async function burst(plan, resultPath) {
  const t0 = Date.now();
  const result = {
    api: RESULT_API, plan_label: plan.label, started_at: new Date().toISOString(), finished_at: null,
    chrome: { exe: plan.chrome || CHROME_EXE, version: null, flags: null, launches: [], closes: [] },
    software: null, refused: null, lock: null, jobs: [], timings: {}, error: null,
  };
  const save = () => { mkdirSync(dirname(resultPath), { recursive: true }); writeFileSync(resultPath, JSON.stringify(result, null, 1)); };
  const burstMs = Math.min(Number(plan.burst_ms) || BURST_MS, BURST_MS);
  const jobs = plan.jobs || [];

  const { acquireGpuLock } = await import("../lanes/gpu_lock.mjs");
  let gpu;
  const lockT0 = Date.now();
  try {
    gpu = await acquireGpuLock(lockOptions(plan));
  } catch (e) {
    result.error = e.message;
    result.jobs = jobs.map((j) => ({ key: j.key, url: j.url, status: "deferred", error: "GPU lock not taken" }));
    result.finished_at = new Date().toISOString();
    save();
    return EXIT.lock;
  }
  const heldFrom = Date.now();
  result.lock = { label: plan.label, acquired_at: gpu.owner.acquiredAt, inherited: gpu.inherited, wait_ms: heldFrom - lockT0 };
  const browser = new Browser(plan.chrome || CHROME_EXE);
  const unguard = guardHolder({ kill: () => browser.killSync(), release: () => gpu.release() });
  let code = EXIT.ok;
  try {
    sweepProfiles();
    const start = async () => {
      const ms = await browser.launch();
      result.chrome.version = browser.version;
      result.chrome.flags = browser.flags.filter((f) => !f.startsWith("--user-data-dir="));
      const sw = await browser.assertSoftware();
      result.chrome.launches.push({ pid: browser.proc.pid, start_ms: ms, software: sw.ok });
      result.software = sw;
      browser.renderer = sw.webgl?.renderer || null;
      say(`chrome ${browser.version} pid ${browser.proc.pid} up in ${ms} ms; renderer: ${browser.renderer}`);
      return sw;
    };
    const sw = await start();
    if (!sw.ok) {
      result.refused = sw.reason;
      say("REFUSED:", sw.reason);
      result.jobs = jobs.map((j) => ({ key: j.key, url: j.url, status: "refused", error: sw.reason }));
      code = EXIT.refused;
      return code;
    }
    for (let i = 0; i < jobs.length; i++) {
      const job = jobs[i];
      const timeout = Math.min(Number(job.timeout_ms) || 60_000, burstMs);
      const windowNow = () => jobWindow({ index: i, elapsedMs: Date.now() - heldFrom, timeoutMs: timeout, burstMs });
      const defer = (why) => {
        for (const rest of jobs.slice(i)) result.jobs.push({ key: rest.key, url: rest.url, status: "deferred", error: why });
        say(`${why} after ${i} job(s); ${jobs.length - i} deferred to the next burst`);
      };
      let w = windowNow();
      if (!w.start) { defer("burst budget reached"); break; }
      if (!browser.proc) {  // relaunched after a timeout; the launch spends part of the burst, so judge it again after
        if (!mayRelaunch(Date.now() - heldFrom, burstMs)) { defer("burst budget: no room to relaunch Chrome"); break; }
        const again = await start();
        if (!again.ok) {
          result.refused = again.reason;
          for (const rest of jobs.slice(i)) result.jobs.push({ key: rest.key, url: rest.url, status: "refused", error: again.reason });
          code = EXIT.refused;
          break;
        }
        w = windowNow();
        if (!w.start) { defer("burst budget reached (after a relaunch)"); break; }
      }
      const row = await runJob(browser, { ...job, url: clipBudget(job.url, w.deadlineMs), timeout_ms: w.deadlineMs },
                               Date.now() + w.deadlineMs);
      result.jobs.push(row);
      say(`${row.key}: ${row.status} in ${row.wall_ms} ms` + (row.error ? ` (${row.error.slice(0, 160)})` : ""));
      if (row.status === "timeout" || /socket closed/.test(row.error || "")) {
        result.chrome.closes.push({ reason: `${row.status} on ${row.key}`, ...(await browser.close()) });
      }
      save();
    }
  } catch (e) {
    result.error = String(e && e.stack || e);
    code = EXIT.error;
  } finally {
    const closed = await browser.close();  // our Chrome first, the lock second (as guardHolder does on a signal)
    if (closed) result.chrome.closes.push({ reason: "end of burst", ...closed });
    gpu.release();
    unguard();
    result.lock.held_ms = Date.now() - heldFrom;
    result.timings = { total_ms: Date.now() - t0, lock_wait_ms: result.lock.wait_ms, held_ms: result.lock.held_ms };
    result.finished_at = new Date().toISOString();
    save();
  }
  return code;
}

// ------------------------------------------------------------------------------------------------------------ CLI
if (process.argv[1] && resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()) {
  const { values: opt } = parseArgs({
    options: { plan: { type: "string" }, result: { type: "string" }, "check-renderer": { type: "string" },
               "print-flags": { type: "boolean", default: false } },
  });
  if (opt["check-renderer"] !== undefined) {
    console.log(JSON.stringify(judgeRenderer(opt["check-renderer"])));
    process.exit(0);
  }
  if (opt["print-flags"]) {
    console.log(JSON.stringify(chromeFlags("<profile>")));
    process.exit(0);
  }
  if (!opt.plan || !opt.result) {
    console.log("usage: node arsenal/shaders/headless.mjs --plan <plan.json> --result <result.json>\n" +
                "       node arsenal/shaders/headless.mjs --check-renderer \"<renderer string>\" | --print-flags");
    process.exit(EXIT.usage);
  }
  const plan = JSON.parse(readFileSync(opt.plan, "utf8"));
  if (plan.api !== PLAN_API) { console.log(`not a plan (${plan.api}, want ${PLAN_API})`); process.exit(EXIT.usage); }
  const refusal = planRefusal(plan);
  if (refusal) {  // before the lock and before Chrome: nothing of this plan runs
    say("REFUSED:", refusal);
    const jobs = Array.isArray(plan.jobs) ? plan.jobs : [];
    mkdirSync(dirname(opt.result), { recursive: true });
    writeFileSync(opt.result, JSON.stringify({
      api: RESULT_API, plan_label: plan.label ?? null, started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(), chrome: { exe: plan.chrome || CHROME_EXE, version: null, flags: null, launches: [], closes: [] },
      software: null, refused: refusal, lock: null, timings: {}, error: null,
      jobs: jobs.map((j) => ({ key: j?.key ?? null, url: j?.url ?? null, status: "refused",
                              error: jobRefusal(j) || "another job in this plan was refused" })),
    }, null, 1));
    process.exit(EXIT.refused);
  }
  if (!existsSync(plan.chrome || CHROME_EXE)) { console.log(`no Chrome at ${plan.chrome || CHROME_EXE}`); process.exit(EXIT.error); }
  const code = await burst(plan, opt.result);
  process.exit(code);
}
