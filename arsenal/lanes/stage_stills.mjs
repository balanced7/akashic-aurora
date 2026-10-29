// Stage stills: render camera shots of the Virtual Stage at chosen bars of the demo show, on the GPU, so a designer SEES a
// candidate shot in seconds instead of editing the set and waiting for the director to deal it. Daniel, 2026-10-29: "also
// can we add some more full set spectacle camera positions, i think a lot of ours are close and we dont have many good
// zoom out ones so i can appreciate the crazy ring effects and full set magic".
//
//   node arsenal/lanes/stage_stills.mjs --shots FOH_WIDE,ROOF_ESTABLISH,HALO_ORBIT --bars 20,28 --look hdr --out <dir>
//        [--extra shots.json]   candidate shots {"ID": {kind, pos, look, ...}} tried without touching source-v1.json
//        [--u 0.5]              where along each shot (0..1; a list renders each); a path or orbit moves along u
//        [--section drop]       --bars count from that section's first bar (else from the demo plan's first bar)
//        [--palette <id>] [--width 1600 --height 900] [--set source-v1] [--port 8960] [--no-sheet]
//        [--facts-only]         no browser: print each shot's placement facts (clearances, landmarks in frame) and stop
//
// How: headless Chrome on the real GPU (arsenal/shaders/headless.mjs renderFlags(true); the renderer must name hardware),
// one burst at a time under the house GPU lock (arsenal/lanes/gpu_lock.mjs, the main checkout's lock even from a
// worktree), serving arsenal/web on a test-band port (8900-8999). The page runs on a VIRTUAL clock (performance.now and
// requestAnimationFrame replaced before any module loads), so the show is the same on every run: the demo plays as
// logic only (nothing drawn) up to each bar, then for every shot the camera is forced to it (the page's setShot, the
// hand-held shot C plays) and the frame is drawn at that same instant (a zero-length step: every shot of a bar sees the
// identical show), and screenshotted. The candidate shots reach the page as window.__extraShots before it boots
// (arsenal/web/stage/stills.js checks them and merges them over the set's shots; camera.js prepareShot prepares them like
// every other). Flash protection stays on (?flash=on); the look is always passed (?look=, default hdr: HDR Night).
//
// Writes <out>/<SHOT>-bar<B>[-u<U>].png, <out>/sheet.png (the contact sheet: a row per shot, a column per bar), and
// <out>/stills.json: what was rendered, each still's camera pose, section and timing, and per shot the facts a designer
// needs to place one (the nearest it comes to the strand at home and to the rings, and which of the rig's landmarks are
// in frame). Default <out>: <worktree>/state/arsenal/stills/stills-<stamp> (gitignored).
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock } from "./gpu_lock.mjs";
import { QUIET_FLAGS, judgeHardwareRenderer, renderFlags } from "../shaders/headless.mjs";
import { expandScene } from "../web/stage/rig.js";
import { cameraModel, prepareShot, shotPose, shotClearance, shotRingClearance } from "../web/stage/camera.js";
import { withExtraShots } from "../web/stage/stills.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]+$/, "");
const MAIN = REPO.split(/[\\/]\.claude[\\/]worktrees[\\/]/)[0];
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    shots: { type: "string", default: "" },
    extra: { type: "string", default: "" },
    bars: { type: "string", default: "" },
    u: { type: "string", default: "0.5" },
    section: { type: "string", default: "" },
    look: { type: "string", default: "hdr" },
    palette: { type: "string", default: "" },
    width: { type: "string", default: "1600" },
    height: { type: "string", default: "900" },
    set: { type: "string", default: "source-v1" },
    out: { type: "string", default: "" },
    port: { type: "string", default: "8960" },
    "no-sheet": { type: "boolean", default: false },
    // switch renderer layers off to find what draws a thing: "beams=0,veil=0" (render.js features: venue, crowd, strand,
    // rings, beams, lasers, emitters, bloom, veil)
    features: { type: "string", default: "" },
    "facts-only": { type: "boolean", default: false },
    "sheet-width": { type: "string", default: "640" },
    "lock-dir": { type: "string", default: join(MAIN, "state", "arsenal", "gpu-render.lock") },
    "gpu-wait-min": { type: "string", default: "10" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    help: { type: "boolean", default: false },
  },
});
const usage = () => {
  console.log("usage: node arsenal/lanes/stage_stills.mjs --shots ID1,ID2 [--extra shots.json] [--bars 20,28] [--u 0.5] [--section drop]\n" +
              "         [--look hdr|punch|velvet|classic] [--palette id] [--width 1600 --height 900] [--set source-v1] [--out dir] [--no-sheet]");
};
if (opt.help) { usage(); process.exit(0); }
const fail = (msg) => { console.log(`ERROR ${msg}`); process.exit(2); };
if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(opt.set)) fail(`--set ${opt.set}: a set name`);
if (!/^[a-z]{1,16}$/.test(opt.look)) fail(`--look ${opt.look}: hdr, punch, velvet or classic`);
if (opt.palette && !/^[a-z0-9][a-z0-9-]{0,40}$/.test(opt.palette)) fail(`--palette ${opt.palette}: a palette id`);
const W = Number(opt.width), H = Number(opt.height);
if (!(W >= 160 && W <= 3840 && H >= 90 && H <= 2160)) fail("--width 160..3840, --height 90..2160");
const PORT = Number(opt.port);
if (!(PORT >= 8900 && PORT <= 8999)) fail(`--port ${PORT}: the test band 8900-8999 only`);

// ---------------------------------------------------------------------------------------- the set and the shots --
const SCENE = JSON.parse(readFileSync(join(REPO, "arsenal", "web", "stage", "sets", `${opt.set}.json`), "utf8"));
const RIG = expandScene(SCENE);
let EXTRA = null;
if (opt.extra) {
  try { EXTRA = JSON.parse(readFileSync(resolve(opt.extra), "utf8")); } catch (e) { fail(`--extra ${opt.extra}: ${e.message}`); }
  if (!EXTRA || typeof EXTRA !== "object" || Array.isArray(EXTRA)) fail(`--extra ${opt.extra}: an object {"ID": {shot}}`);
}
const merged = withExtraShots(RIG.cameras.shots, EXTRA);
if (merged.problems.length) fail(`--extra: ${merged.problems.join("; ")}`);
const SHOT_IDS = (opt.shots ? opt.shots.split(",") : [...merged.added, ...merged.replaced]).map((s) => s.trim()).filter(Boolean);
if (!SHOT_IDS.length) { usage(); fail("no shots: --shots ID1,ID2 (or --extra with shots in it)"); }
for (const id of SHOT_IDS) if (!merged.shots[id] || id.startsWith("_")) fail(`unknown shot ${id} (not in ${opt.set}.json nor --extra)`);
const US = opt.u.split(",").map(Number);
if (!US.length || !US.every((u) => Number.isFinite(u) && u >= 0 && u <= 1)) fail(`--u ${opt.u}: numbers 0..1`);

// the bars, counted from the demo plan's first bar (or from --section's first bar in the plan)
const PLAN = (SCENE.show && SCENE.show.demo && SCENE.show.demo.plan) || [];
let sectionStart = 0;
if (opt.section) {
  let at = 0, found = false;
  for (const p of PLAN) { if (p.section === opt.section) { found = true; break; } at += p.bars; }
  if (!found) fail(`--section ${opt.section}: the demo plan has ${PLAN.map((p) => p.section).join(", ")}`);
  sectionStart = at;
}
const BARS_ASKED = (opt.bars || (opt.section ? "4" : "20,28")).split(",").map(Number);
if (!BARS_ASKED.every((b) => Number.isFinite(b) && b >= 0 && b < 400)) fail(`--bars ${opt.bars}: bar numbers`);
const BARS = [...new Set(BARS_ASKED.map((b) => sectionStart + b))].sort((a, b) => a - b);
const planSection = (bar) => {
  const total = PLAN.reduce((s, p) => s + p.bars, 0);
  let q = total ? ((Math.floor(bar) % total) + total) % total : 0;
  for (const p of PLAN) { if (q < p.bars) return { section: p.section, bar_in_section: q }; q -= p.bars; }
  return { section: null, bar_in_section: null };
};

// per shot, what a designer needs to place one: the nearest the lens comes to the strand at its home height and to the
// rings at home (the director's rule is 1.5 m), and which landmarks of the rig fall inside the frame at each u
const MODEL = cameraModel(RIG);
const HOME_POSES = [MODEL.z.map(() => ({ y: MODEL.homeY, roll: 0 }))];
const ring0 = MODEL.rings.reduce((a, b) => (b.outer > a.outer ? b : a), MODEL.rings[0]);
const ringUp = (() => { const n = ring0.normal; return [0, n[2], -n[1]]; })();      // in the halo's plane, square to x
const at = (c, d, k) => c.map((v, i) => +(v + d[i] * k).toFixed(2));
const LANDMARKS = {
  "halo top": at(ring0.centre, ringUp, ring0.outer), "halo bottom": at(ring0.centre, ringUp, -ring0.outer),
  "halo left": at(ring0.centre, [1, 0, 0], -ring0.outer), "halo right": at(ring0.centre, [1, 0, 0], ring0.outer),
  "rings centre": ring0.centre.slice(),
  "strand first rung": [0, MODEL.homeY, MODEL.z[0]], "strand last rung": [0, MODEL.homeY, MODEL.z[MODEL.z.length - 1]],
  "tower L top": [-22, 16, -2], "tower R top": [22, 16, -2], "laser truss L": [-22, 22, -2], "laser truss R": [22, 22, -2],
  "crowd front": [0, 1.9, 6], "crowd mid L": [-25, 1.9, 40], "crowd mid R": [25, 1.9, 40],
};
function inFrame(pose, p, aspect) {
  const f = [pose.look[0] - pose.pos[0], pose.look[1] - pose.pos[1], pose.look[2] - pose.pos[2]], fl = Math.hypot(...f) || 1;
  for (let i = 0; i < 3; i++) f[i] /= fl;
  let r = [-f[2], 0, f[0]]; const rl = Math.hypot(r[0], r[2]);
  r = rl < 1e-6 ? [1, 0, 0] : [r[0] / rl, 0, r[2] / rl];
  const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
  const d = [p[0] - pose.pos[0], p[1] - pose.pos[1], p[2] - pose.pos[2]];
  const z = d[0] * f[0] + d[1] * f[1] + d[2] * f[2];
  if (z < 0.5) return false;
  const tanH = Math.tan((pose.hfov * Math.PI) / 360), tanV = tanH / aspect;
  return Math.abs((d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / z) <= tanH && Math.abs((d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / z) <= tanV;
}
// Where a lens can stand (measured 2026-10-29 from render.js's hall, and seen black on the GPU): the floor is x +-38,
// z -24..96, the roof y 38, the black drape z -24. The REAR stand is a plane rising TOWARD the stage, from (z 148, y 0) to
// (z 96, y 30): a lens behind z 96 above it looks into its back. Each SIDE stand is a plane y = 0.577 (90 - |x|) that
// spans only z 32..92 (it rises toward the floor and runs on above the roof): a lens above it there looks into it. So the
// widest views stand at z <= 96 (y < 38), or at |x| up to ~90 outside z 32..92, or under the side planes.
function hallWarnings(p) {
  const [x, y, z] = p, w = [];
  if (y >= 38) w.push("above the roof (y 38)");
  if (z < -24) w.push("behind the drape (z -24)");
  if (Math.abs(x) > 90) w.push("outside the hall (|x| > 90)");
  if (z > 96 && y > (30 * (148 - z)) / 52) w.push("behind the rear stand (above its plane, z > 96): sees its back");
  if (z >= 32 && z <= 92 && Math.abs(x) > 20 && y > 0.577 * (90 - Math.abs(x))) w.push("above a side stand's plane (z 32..92): looks into it");
  return w;
}
const SHOT_FACTS = {};
for (const id of SHOT_IDS) {
  const s = prepareShot({ id, ...merged.shots[id] });
  const per_u = {};
  for (const u of US) {
    const p = shotPose(s, u, 0);
    const seen = Object.entries(LANDMARKS).filter(([, q]) => inFrame(p, q, W / H)).map(([k]) => k);
    per_u[u] = { pos: p.pos.map((v) => +v.toFixed(2)), look: p.look.map((v) => +v.toFixed(2)), hfov: +p.hfov.toFixed(1),
                 metres_to_rings_centre: +Math.hypot(p.pos[0] - ring0.centre[0], p.pos[1] - ring0.centre[1], p.pos[2] - ring0.centre[2]).toFixed(1),
                 landmarks_in_frame: `${seen.length}/${Object.keys(LANDMARKS).length}`, missing: Object.keys(LANDMARKS).filter((k) => !seen.includes(k)),
                 hall: hallWarnings(p.pos) };
  }
  SHOT_FACTS[id] = {
    source: merged.added.includes(id) ? "extra" : merged.replaced.includes(id) ? "extra (replaces the set's)" : opt.set,
    def: merged.shots[id],
    clearance_strand_home_m: +shotClearance(s, HOME_POSES, MODEL.z).toFixed(2),
    clearance_rings_home_m: +shotRingClearance(s, [MODEL.rings]).toFixed(2),
    at_u: per_u,
  };
}

if (opt["facts-only"]) {
  for (const [id, f] of Object.entries(SHOT_FACTS)) {
    console.log(`${id} (${f.source}): strand at home ${f.clearance_strand_home_m} m, rings ${f.clearance_rings_home_m} m`);
    for (const [u, a] of Object.entries(f.at_u)) console.log(`  u ${u}: pos ${a.pos} look ${a.look} hfov ${a.hfov}, ${a.metres_to_rings_centre} m from the rings, landmarks ${a.landmarks_in_frame}${a.missing.length ? ` (missing: ${a.missing.join(", ")})` : ""}${a.hall.length ? `; HALL: ${a.hall.join("; ")}` : ""}`);
  }
  process.exit(0);
}

// ------------------------------------------------------------------------------------------------ the output --
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const OUT = resolve(opt.out || join(REPO, "state", "arsenal", "stills", `stills-${stamp}`));
mkdirSync(OUT, { recursive: true });
const report = {
  api: "arsenal.stage-stills/v1", started_at: new Date().toISOString(), worktree: REPO,
  command: `node arsenal/lanes/stage_stills.mjs ${process.argv.slice(2).join(" ")}`,
  set: opt.set, look: opt.look, palette: opt.palette || null, viewport: { width: W, height: H },
  bars: BARS.map((b) => ({ plan_bar: b, ...planSection(b) })), u: US,
  extra: { file: opt.extra || null, added: merged.added, replaced: merged.replaced },
  landmarks: LANDMARKS, shots: SHOT_FACTS, stills: [], bursts: [], errors: [],
};
const writeReport = () => writeFileSync(join(OUT, "stills.json"), JSON.stringify(report, null, 1));

// ------------------------------------------------------------------------------------------------ the server --
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
async function listen(server, preferred) {
  for (let p = preferred; p <= 8999; p++) {
    try {
      await new Promise((ok, no) => { server.once("error", no); server.listen(p, "127.0.0.1", () => { server.off("error", no); ok(); }); });
      return p;
    } catch (e) { if (e.code !== "EADDRINUSE" && e.code !== "EACCES") throw e; }
  }
  throw new Error("no free port in the test band 8900-8999");
}

// ------------------------------------------------------------------------------------------------ Chrome & CDP --
function connect(wsUrl) {
  return new Promise((ok, no) => {
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
    ws.onerror = () => no(new Error(`websocket error on ${wsUrl}`));
  });
}
const withTimeout = (p, ms, what) => { let t; return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(`no answer within ${ms} ms: ${what}`)), ms); })]).finally(() => clearTimeout(t)); };
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { try { const v = await fn(); if (v) return v; } catch { /* not yet */ } await delay(200); }
  throw new Error(`timed out waiting for ${what}`);
}
// the virtual clock (as stage_verify.mjs), installed before the page's modules run
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

const BURST_MS = 170_000;    // GPU-LOCK.md: a burst stays under three minutes
async function burst(n, body) {
  const t0 = Date.now();
  const profile = join(tmpdir(), `arsenal-stage-stills-${stamp}-${n}`);
  const rec = { n, console: [], exceptions: [] };
  report.bursts.push(rec);
  let gpu = null, chrome = null, browser = null;
  try {
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `stage_stills burst ${n} (GPU)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, pollMs: 2000 });
    const tLock = Date.now();
    rec.lock_wait_s = +((tLock - t0) / 1000).toFixed(1);
    chrome = spawn(opt.chrome, [...renderFlags(true), ...QUIET_FLAGS, "--remote-debugging-port=0", `--user-data-dir=${profile}`,
      `--window-size=${W},${H}`, "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore", windowsHide: true });
    const [cdpPort, cdpPath] = await waitFor(() => { try { const [p, w] = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split(/\r?\n/); return p && w ? [p, w] : null; } catch { return null; } }, 30000, "DevToolsActivePort");
    browser = await connect(`ws://127.0.0.1:${cdpPort}${cdpPath}`);
    rec.chrome = (await browser.send("Browser.getVersion")).product;
    const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
    const S = (method, params = {}, ms = 120000) => withTimeout(browser.send(method, params, sessionId), ms, method);
    browser.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled" && /error|warn/.test(p.type)) rec.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
      else if (msg.method === "Runtime.exceptionThrown") rec.exceptions.push({ text: p.exceptionDetails.text, description: p.exceptionDetails.exception?.description?.slice(0, 600) });
    });
    for (const d of ["Runtime", "Page"]) await S(`${d}.enable`);
    await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
    if (EXTRA) await S("Page.addScriptToEvaluateOnNewDocument", { source: `window.__extraShots = ${JSON.stringify(EXTRA)};` });
    await S("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
    const ev = async (expression, ms = 150000) => {
      const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }, ms);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const query = `demo=1&vt=1&w=${W}&h=${H}&hud=0&quality=receipt&flash=on&set=${opt.set}&look=${opt.look}${opt.palette ? `&palette=${opt.palette}` : ""}`;
    rec.url = `http://127.0.0.1:${PORT}/web/stage/index.html?${query}`;
    await S("Page.navigate", { url: rec.url });
    await waitFor(() => ev("!!(window.__stage && (window.__stage.ready || window.__stage.bootError))"), 60000, "the stage to boot");
    const bootErr = await ev("window.__stage.bootError || null");
    if (bootErr) throw new Error(`boot: ${bootErr}`);
    rec.boot_s = +((Date.now() - tLock) / 1000).toFixed(1);
    await body({ ev, S, rec, deadline: tLock + BURST_MS });
  } catch (e) {
    rec.error = String(e && e.stack || e).slice(0, 1200);
    console.log(`burst ${n} failed: ${rec.error}`);
  } finally {
    try { if (browser) { await withTimeout(browser.send("Browser.close"), 3000, "Browser.close").catch(() => {}); browser.close(); } } catch { /* gone */ }
    if (chrome && chrome.exitCode === null) {
      await delay(1500);
      if (chrome.exitCode === null) spawnSync("taskkill", ["/T", "/F", "/PID", String(chrome.pid)], { stdio: "ignore" });
    }
    await delay(500);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* a handle may linger */ }
    if (gpu) gpu.release();
    rec.burst_s = +((Date.now() - t0) / 1000).toFixed(1);
    console.log(`burst ${n}: ${rec.burst_s} s`);
  }
  return rec;
}

// ----------------------------------------------------------------------------------------------- page scripts --
const F = 1000 / 60;
// logic only (nothing drawn) up to the bar: the plan's bar index is (pos - show.planStart) / 4 (show.js); stops on the last
// 60 fps frame at or before the bar's position. Returns how many frames it stepped.
const RUN_TO = String.raw`((bar, maxFrames) => {
  const s = window.__stage, F = 1000 / 60;
  const posNow = () => s.grid.posAt(performance.now() + s.grid.presentLagMs);
  s.clearShot(); s.skipRender = true;
  let n = 0;
  while (n < maxFrames && s.show.planStart === null) { window.__vt.step(F); n++; }
  const target = s.show.planStart + 4 * bar, perFrame = F / s.grid.period;
  while (n < maxFrames && posNow() + perFrame <= target + 1e-9) { window.__vt.step(F); n++; }
  return { frames: n, pos: posNow(), target, done: posNow() + perFrame > target + 1e-9 };
})`;
// one still: the shot forced by hand at u, the limiter fresh, two frames drawn at this same instant (a zero-length step:
// the show does not move, so every shot of a bar sees the same moment)
const FEAT = opt.features ? JSON.stringify(Object.fromEntries(opt.features.split(",").map((kv) => kv.split("=")).filter(([k]) => k)
  .map(([k, v]) => [k.trim(), !(v === undefined ? false : /^(0|false|off)$/i.test(v.trim()))]))) : "null";
const STILL = String.raw`((id, u, feat) => {
  const s = window.__stage;
  if (feat) s.features(feat);
  s.setShot(id, u); s.resetLimiter(); s.skipRender = false;
  window.__vt.step(0); window.__vt.step(0);
  const st = s.state(), p = s.director.pose;
  return { pos: st.pos, section: st.section, look: st.look, shot: p.shot, phrase: st.phrase && st.phrase.state === "running" ? st.phrase.stepName || st.phrase.step : null,
           pose: { pos: p.pos.map((v) => +v.toFixed(3)), look: p.look.map((v) => +v.toFixed(3)), hfov: +p.hfov.toFixed(2), roll: +p.roll.toFixed(2) },
           info: st.info ? { beams: st.info.beams, lasers: st.info.lasers, emitters: st.info.emitters } : null,
           limiter: st.limiter.interventions, errors: st.errors.length, finish: s.renderer.look };
})`;

// ------------------------------------------------------------------------------------------------------- run --
const fmtU = (u) => (US.length > 1 || u !== 0.5 ? `-u${String(u).replace(".", "")}` : "");
const pending = BARS.slice();
let PORT_USED;
try {
  PORT_USED = await listen(web, PORT);
  if (PORT_USED !== PORT) console.log(`port ${PORT} busy; serving on ${PORT_USED}`);
} catch (e) { fail(e.message); }
const tRun = Date.now();
let burstNo = 0, renderer = null, determinism = [];
while (pending.length) {
  const before = pending.length;
  burstNo++;
  await burst(burstNo, async ({ ev, S, rec, deadline }) => {
    renderer = await ev(`(() => { const gl = window.__stage.renderer.gl || window.__stage.renderer.renderer.getContext(); const x = gl.getExtension("WEBGL_debug_renderer_info"); return x ? gl.getParameter(x.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); })()`);
    rec.renderer = renderer;
    const judged = judgeHardwareRenderer(renderer);
    if (!judged.ok) throw new Error(`not on the GPU: ${judged.reason}`);
    const extra = await ev("window.__stage.extraShots || null");
    rec.extra = extra;
    if (EXTRA && extra && extra.problems.length) throw new Error(`the page refused extra shots: ${extra.problems.join("; ")}`);
    const missing = await ev(`${JSON.stringify(SHOT_IDS)}.filter((id) => !window.__stage.director.shots[id])`);
    if (missing.length) throw new Error(`the page has no shot ${missing.join(", ")}`);
    rec.bars = [];
    while (pending.length) {
      const bar = pending[0];
      const perBar = SHOT_IDS.length * US.length;
      // the estimate: a second a still plus the run to the bar; a bar that does not fit waits for the next burst
      if (rec.bars.length && Date.now() + perBar * 2500 + 20000 > deadline) break;
      const t0 = Date.now();
      let run = { done: false, frames: 0 };
      for (let k = 0; k < 40 && !run.done; k++) {
        const r = await ev(`${RUN_TO}(${bar}, 1200)`, 160000);
        run = { ...r, frames: run.frames + r.frames };
      }
      if (!run.done) throw new Error(`could not reach bar ${bar}`);
      const runMs = Date.now() - t0;
      rec.bars.push({ bar, logic_frames: run.frames, logic_s: +(runMs / 1000).toFixed(2) });
      console.log(`bar ${bar}: ${run.frames} frames of logic in ${(runMs / 1000).toFixed(1)} s (pos ${run.pos.toFixed(3)})`);
      let firstShot = null;
      for (const id of SHOT_IDS) for (const u of US) {
        const ts = Date.now();
        const st = await ev(`${STILL}(${JSON.stringify(id)}, ${u}, ${FEAT})`, 120000);
        const shot = await S("Page.captureScreenshot", { format: "png" });
        const file = join(OUT, `${id}-bar${String(bar - sectionStart).replace(".", "_")}${opt.section ? `-${opt.section}` : ""}${fmtU(u)}.png`);
        writeFileSync(file, Buffer.from(shot.data, "base64"));
        const ms = Date.now() - ts;
        if (!firstShot) firstShot = { id, u, data: shot.data };
        report.stills.push({ shot: id, bar: bar - sectionStart, plan_bar: bar, ...planSection(bar), u, file, ms, ...st });
        console.log(`  ${id} u ${u}: ${ms} ms, ${st.section}, beams ${st.info && st.info.beams}, lasers ${st.info && st.info.lasers}, limiter ${st.limiter}`);
      }
      // the same instant twice gives the same picture (the first still of the bar, drawn again after the others)
      if (firstShot) {
        await ev(`${STILL}(${JSON.stringify(firstShot.id)}, ${firstShot.u}, ${FEAT})`, 120000);
        const again = await S("Page.captureScreenshot", { format: "png" });
        determinism.push({ bar, shot: firstShot.id, identical: again.data === firstShot.data });
      }
      pending.shift();
      writeReport();
    }
    const errs = await ev("window.__stage.errors.slice()");
    if (errs.length) report.errors.push(...errs);
  });
  if (pending.length === before) { report.errors.push(`burst ${burstNo} made no progress`); break; }
}
web.close();
report.renderer = renderer;
report.determinism = determinism;
const stillMs = report.stills.map((s) => s.ms);
report.timing = {
  total_s: +((Date.now() - tRun) / 1000).toFixed(1), bursts: burstNo, stills: report.stills.length,
  still_ms_median: stillMs.length ? stillMs.slice().sort((a, b) => a - b)[Math.floor(stillMs.length / 2)] : null,
  still_ms_first: stillMs[0] ?? null,
  logic_s: report.bursts.flatMap((b) => b.bars || []).reduce((s, b) => s + b.logic_s, 0),
};

// ------------------------------------------------------------------------------------------- the contact sheet --
if (!opt["no-sheet"] && report.stills.length) {
  const cols = BARS.flatMap((b) => US.map((u) => ({ bar: b, u })));
  const plan = {
    out: join(OUT, "sheet.png"), thumb_w: Number(opt["sheet-width"]),
    title: `${opt.set} · look ${opt.look}${opt.palette ? ` · palette ${opt.palette}` : ""} · ${W}x${H} · ${renderer || ""}`.slice(0, 160),
    cols: cols.map((c) => `bar ${c.bar - sectionStart}${opt.section ? ` of ${opt.section}` : ""} (${planSection(c.bar).section})${US.length > 1 ? ` · u ${c.u}` : ""}`),
    rows: SHOT_IDS.map((id) => ({ label: id, note: `${SHOT_FACTS[id].source} · strand ${SHOT_FACTS[id].clearance_strand_home_m} m · rings ${SHOT_FACTS[id].clearance_rings_home_m} m`,
                                  cells: cols.map((c) => (report.stills.find((s) => s.shot === id && s.plan_bar === c.bar && s.u === c.u) || {}).file || null) })),
  };
  const planFile = join(OUT, "sheet-plan.json");
  writeFileSync(planFile, JSON.stringify(plan));
  const PY = String.raw`
import json, sys
from PIL import Image, ImageDraw, ImageFont
p = json.load(open(sys.argv[1], encoding="utf-8"))
tw = p["thumb_w"]; cells = [c for r in p["rows"] for c in r["cells"] if c]
w0, h0 = Image.open(cells[0]).size
th = round(tw * h0 / w0)
def font(n):
    for f in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try: return ImageFont.truetype(f, n)
        except OSError: pass
    return ImageFont.load_default()
F1, F2, F3 = font(22), font(16), font(14)
pad, head, rowhead = 12, 64, 26
W = pad + len(p["cols"]) * (tw + pad)
H = head + len(p["rows"]) * (rowhead + th + pad) + pad
sheet = Image.new("RGB", (W, H), (10, 10, 12))
d = ImageDraw.Draw(sheet)
d.text((pad, 10), p["title"], fill=(235, 235, 240), font=F1)
for j, c in enumerate(p["cols"]):
    d.text((pad + j * (tw + pad), 40), c, fill=(170, 170, 180), font=F2)
y = head
for r in p["rows"]:
    d.text((pad, y + 3), r["label"], fill=(255, 210, 120), font=F2)
    d.text((pad + 12 + d.textlength(r["label"], font=F2), y + 5), r["note"], fill=(140, 140, 150), font=F3)
    y += rowhead
    for j, c in enumerate(r["cells"]):
        x = pad + j * (tw + pad)
        if c: sheet.paste(Image.open(c).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        else: d.rectangle([x, y, x + tw, y + th], outline=(80, 30, 30))
    y += th + pad
sheet.save(p["out"])
print(p["out"])
`;
  const r = spawnSync("py", ["-c", PY, planFile], { encoding: "utf8", windowsHide: true });
  if (r.status === 0) { report.sheet = plan.out; rmSync(planFile, { force: true }); }
  else report.errors.push(`contact sheet: ${(r.stderr || r.stdout || "").slice(-600)}`);
}
report.finished_at = new Date().toISOString();
writeReport();
console.log(`\n${report.stills.length} stills in ${report.timing.total_s} s (${report.timing.bursts} burst${report.timing.bursts > 1 ? "s" : ""}; a still ${report.timing.still_ms_median} ms median, the bar runs ${report.timing.logic_s.toFixed(1)} s of logic)`);
console.log(`renderer: ${renderer}`);
console.log(`determinism: ${determinism.map((d) => `bar ${d.bar} ${d.identical ? "same" : "DIFFERENT"}`).join(", ")}`);
if (report.sheet) console.log(`sheet: ${report.sheet}`);
console.log(`report: ${join(OUT, "stills.json")}`);
if (report.errors.length) { console.log(`errors: ${report.errors.slice(0, 5).join(" | ")}`); }
const want = BARS.length * SHOT_IDS.length * US.length;
process.exit(report.stills.length === want && !report.errors.length ? 0 : 1);
