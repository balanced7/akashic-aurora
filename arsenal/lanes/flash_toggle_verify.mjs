// The flash protection toggle's receipt (2026-10-28): arsenal/lanes/flash_toggle_verify.mjs. Headless Chrome forced onto
// SwiftShader, one browser at a time under the house GPU lock (arsenal/GPU-LOCK.md), each phase its own burst with a
// fresh profile (so a first visit is a first visit), the pages on a virtual clock.
//
//   node arsenal/lanes/flash_toggle_verify.mjs [--phases consent,identity,vjoff] [--port 8960]
//
// Phases:
//   consent    for the Stage and the VJ page, at 1280 x 720 (mouse) and at 832 x 384 with touch emulation and the pad bar
//              (touch): the page is told it is not automated (navigator.webdriver false), as a viewer's browser is. The
//              warning screen is up before the show starts (Stage: not ready; VJ: no frame drawn while the clock runs),
//              its wording, ONE checkbox "Flash protection" checked, no "recommend" on it; on the phone the screen is what
//              lies under the pad bar. Then, with real input (mouse clicks, or touch taps): uncheck, Start -> the show runs
//              with protection off and the browser remembers "off"; nothing about it appears on its own; a reload shows no
//              screen and starts with protection off; the HUD's quiet checkbox turns it back on (remembered "on").
//   identity   the Stage at 640 x 360, ?flash=off: the kick storm's segments A and B (pads 1 and 5 held at full through the
//              pad door), every drawn frame compared pixel for pixel with the frame as drawn (window.__stage.identityProbe:
//              the finish pass's target against the canvas): zero differing pixels, the limiter never runs, the kick
//              governor's headroom stays 5. Control: the same frames with ?flash=on.
//   vjoff      the VJ page, ?flash=off: a pad storm; the limiter never runs (its frame count does not move while frames
//              render) and no pad effect is refused. Control: ?flash=on, the limiter runs every frame.
// Screenshots go to --shots (scratch; default the receipt folder). Writes <worktree>/state/arsenal/receipts/
// flashtoggle-<stamp>/receipt.json (gitignored); exits 1 on a failed check.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock, LOCK_DIR } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]+$/, "");
const WEB = resolve(REPO, "arsenal", "web");
const { values: opt } = parseArgs({
  options: {
    phases: { type: "string", default: "consent,identity,vjoff" },
    pages: { type: "string", default: "stage,vj" },
    sizes: { type: "string", default: "desktop,phone" },
    port: { type: "string", default: "8960" },
    frames: { type: "string", default: "100" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    shots: { type: "string", default: "" },
    "lock-dir": { type: "string", default: LOCK_DIR },
    "gpu-wait-min": { type: "string", default: "10" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
  },
});
let PORT = Number(opt.port);
if (PORT === 8793 || PORT === 8794 || !(PORT >= 8900 && PORT <= 8999)) { console.log(`ERROR port ${PORT}: the test band 8900-8999 only`); process.exit(2); }
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const outDir = join(opt.out, `flashtoggle-${stamp}`);
mkdirSync(outDir, { recursive: true });
const shotDir = opt.shots || outDir;
mkdirSync(shotDir, { recursive: true });
const report = { api: "arsenal.receipt/v0", lane: "flash-toggle", started_at: new Date().toISOString(), worktree: REPO, phases: {}, checks: {} };
const check = (name, ok, detail) => { report.checks[name] = { ok: !!ok, detail }; console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail !== undefined ? `: ${JSON.stringify(detail).slice(0, 400)}` : ""}`); };

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
    if (p === 8793 || p === 8794) continue;
    try { await new Promise((ok, fail) => { server.once("error", fail); server.listen(p, "127.0.0.1", () => { server.off("error", fail); ok(); }); }); return p; }
    catch (e) { if (e.code !== "EADDRINUSE" && e.code !== "EACCES") throw e; }
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
// the virtual clock (the receipts' own), for both pages, on ?vt=1
const VIRTUAL_CLOCK = `(() => {
  if (!/[?&]vt=1/.test(location.search)) return;
  let vt = 20000;
  const q = [];
  const real = performance.now.bind(performance);
  window.__realNow = real;
  performance.now = () => vt;
  window.requestAnimationFrame = (cb) => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__vt = { step(ms) { vt += ms; const cbs = q.splice(0, q.length); for (const cb of cbs) cb(vt); return vt; }, now: () => vt, queued: () => q.length };
})();`;
// a viewer's browser: not driven by automation (the house's lanes are, and get protection on with no screen)
const NOT_AUTOMATED = `Object.defineProperty(Navigator.prototype, "webdriver", { get: () => false, configurable: true });`;

async function burst(name, { width, height, phone = false, viewer = false }, body) {
  const t0 = Date.now();
  const profile = join(tmpdir(), `arsenal-flashtoggle-${stamp}-${name}`);
  let gpu = null, chrome = null, browser = null;
  const phase = report.phases[name] = { console: [], exceptions: [], size: [width, height], phone };
  try {
    gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `flash_toggle_verify ${name} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, pollMs: 2000 });
    chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0", `--user-data-dir=${profile}`,
      `--window-size=${width},${height}`, "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore", windowsHide: true });
    const [cdpPort, cdpPath] = await waitFor(() => { try { const [p, w] = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split(/\r?\n/); return p && w ? [p, w] : null; } catch { return null; } }, 30000, "DevToolsActivePort");
    browser = await connect(`ws://127.0.0.1:${cdpPort}${cdpPath}`);
    const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
    const S = (method, params = {}, ms = 120000) => withTimeout(browser.send(method, params, sessionId), ms, method);
    browser.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error")) phase.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300) });
      else if (msg.method === "Runtime.exceptionThrown") phase.exceptions.push({ text: p.exceptionDetails.text, description: p.exceptionDetails.exception?.description?.slice(0, 400) });
    });
    for (const d of ["Runtime", "Page"]) await S(`${d}.enable`);
    await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
    if (viewer) await S("Page.addScriptToEvaluateOnNewDocument", { source: NOT_AUTOMATED });
    await S("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: phone, screenOrientation: phone ? { type: "landscapePrimary", angle: 90 } : undefined });
    if (phone) await S("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    const ev = async (expression, ms = 150000) => {
      const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }, ms);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const shot = async (file) => { const r = await S("Page.captureScreenshot", { format: "png" }); writeFileSync(join(shotDir, file), Buffer.from(r.data, "base64")); return file; };
    // a real press on a point: a mouse click, or on the phone a touch tap
    const press = async (x, y) => {
      if (phone) {
        await S("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
        await delay(60);
        await S("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      } else {
        await S("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
        await S("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
        await S("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
      }
      await delay(150);
    };
    await body({ S, ev, shot, press, phase });
  } catch (e) {
    phase.error = String(e && e.stack || e).slice(0, 1200);
    check(`${name}: the burst ran`, false, phase.error);
  } finally {
    try { if (browser) { await withTimeout(browser.send("Browser.close"), 3000, "Browser.close").catch(() => {}); browser.close(); } } catch { /* gone */ }
    if (chrome && chrome.exitCode === null) { await delay(1500); if (chrome.exitCode === null) spawnSync("taskkill", ["/T", "/F", "/PID", String(chrome.pid)], { stdio: "ignore" }); }
    await delay(500);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* a handle may linger */ }
    if (gpu) gpu.release();
    phase.burst_s = +((Date.now() - t0) / 1000).toFixed(1);
    console.log(`burst ${name}: ${phase.burst_s} s`);
  }
}

// ------------------------------------------------------------------------------------------------- consent --
const PAGE = {
  stage: { path: "/web/stage/index.html", query: "demo=1&vt=1&quality=low&w=320&h=180", hudBox: "#opt-flash",
           ready: "!!(window.__stage && window.__stage.ready)", state: "window.__stage.flashProtection()",
           started: "!!(window.__stage && window.__stage.ready)" },
  vj: { path: "/web/vj.html", query: "demo=1&engine=off&watchdog=0&vt=1&sets=vj-reactor", hudBox: "#hud-opt-flash",
        ready: "!!(window.__vj && window.__vj.ready)", state: "window.__vj.stats().flashProtection",
        started: "(() => { try { return window.__vj.stats().frames > 0; } catch { return false; } })()" },
};
const SIZES = { desktop: { width: 1280, height: 720, phone: false }, phone: { width: 832, height: 384, phone: true } };
const STEP = (n) => `(() => { for (let i = 0; i < ${n}; i++) window.__vt && window.__vt.step(1000 / 60); return true; })()`;
const SCREEN = String.raw`(() => {
  const veil = document.getElementById("flash-consent");
  if (!veil) return null;
  const boxes = [...veil.querySelectorAll("input[type=checkbox]")];
  const rect = (el) => { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height, top: r.top, bottom: r.bottom }; };
  const start = veil.querySelector("button");
  const label = boxes[0] ? boxes[0].closest("label") : null;
  const bar = document.querySelector("nav.tb");
  let barCovered = null, barRect = null;
  if (bar) {
    barRect = rect(bar);
    const pts = [...bar.querySelectorAll("button")].filter((b) => b.offsetParent !== null).map(rect);
    barCovered = pts.length ? pts.every((p) => { const e = document.elementFromPoint(p.x, p.y); return !!(e && e.closest("#flash-consent")); }) : null;
  }
  const vr = veil.getBoundingClientRect();
  return { text: veil.innerText, title: veil.querySelector("h1") ? veil.querySelector("h1").textContent : null,
           checkboxes: boxes.length, checked: boxes[0] ? boxes[0].checked : null, label: label ? label.textContent.trim() : null,
           button: start ? start.textContent.trim() : null, box: boxes[0] ? rect(boxes[0]) : null, labelRect: label ? rect(label) : null,
           start: start ? rect(start) : null, recommend: /recommend/i.test(veil.innerText),
           covers: vr.left <= 0 && vr.top <= 0 && vr.right >= innerWidth && vr.bottom >= innerHeight, viewport: [innerWidth, innerHeight],
           bar: !!bar, barRect, barCovered, z: getComputedStyle(veil).zIndex,
           startInView: start ? start.getBoundingClientRect().bottom <= innerHeight && start.getBoundingClientRect().top >= 0 : null };
})()`;
// is anything about protection showing outside the HUD (a badge, a toast that stays, a second screen)?
const NAG = String.raw`(() => {
  const out = [];
  for (const el of document.body.querySelectorAll("*")) {
    if (el.closest("#hud") || el.closest("#panel") || el.closest("#flash-consent") || el.closest("nav.tb") || el.closest(".tbs")) continue;
    if (el.children.length || el.tagName === "SCRIPT" || el.tagName === "STYLE") continue;
    const t = (el.textContent || "").trim();
    if (!/protection/i.test(t)) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity === 0 || r.width === 0 || r.height === 0) continue;
    out.push(t.slice(0, 80));
  }
  return { screen: !!document.getElementById("flash-consent"), visible: out };
})()`;

async function phaseConsent(pageKey, sizeKey) {
  const P = PAGE[pageKey], Z = SIZES[sizeKey], tag = `consent ${pageKey} ${sizeKey}`;
  await burst(`consent-${pageKey}-${sizeKey}`, { ...Z, viewer: true }, async ({ S, ev, shot, press, phase }) => {
    const q = `${P.query}${Z.phone ? "&pads=1" : ""}`;
    await S("Page.navigate", { url: `http://127.0.0.1:${PORT}${P.path}?${q}` });
    await waitFor(() => ev("!!document.getElementById('flash-consent')"), 60000, "the warning screen");
    // the show waits: let the page load behind the screen and run its clock
    await delay(pageKey === "vj" ? 8000 : 5000);
    await ev(STEP(20));
    const first = await ev(SCREEN);
    const startedBefore = await ev(P.started);
    phase.screen = first;
    await shot(`consent-${pageKey}-${sizeKey}.png`);
    check(`${tag}: the warning screen is up on the first visit, over the whole page`, !!first && first.covers, first && { covers: first.covers, z: first.z, viewport: first.viewport });
    check(`${tag}: the show waits behind it (${pageKey === "stage" ? "the Stage is not started" : "no VJ frame drawn"})`, startedBefore === false, { started: startedBefore });
    check(`${tag}: its wording`, first && first.title === "Photosensitivity warning" && /flashing lights and patterns that may trigger seizures in people with photosensitive epilepsy/.test(first.text) && first.button === "Start",
          first && { title: first.title, button: first.button, text: first.text });
    check(`${tag}: ONE checkbox, "Flash protection", checked; no "recommend" anywhere on it`, first && first.checkboxes === 1 && first.checked === true && first.label === "Flash protection" && !first.recommend,
          first && { checkboxes: first.checkboxes, checked: first.checked, label: first.label, recommend: first.recommend });
    check(`${tag}: Start is on screen without scrolling`, first && first.startInView === true, first && { start: first.start, viewport: first.viewport });
    if (Z.phone) check(`${tag}: the pad bar is there and does not cover the screen (the screen is what lies under every pad)`, first && first.bar && first.barCovered === true, first && { bar: first.bar, covered: first.barCovered, barRect: first.barRect });
    // uncheck, with a real press on the box's label, then Start
    await press(first.labelRect.x - first.labelRect.w / 2 + 14, first.labelRect.y);
    const afterBox = await ev(SCREEN);
    check(`${tag}: a ${Z.phone ? "tap" : "click"} unchecks the box`, afterBox && afterBox.checked === false, afterBox && { checked: afterBox.checked });
    await press(first.start.x, first.start.y);
    await waitFor(() => ev("!document.getElementById('flash-consent')"), 10000, "the screen to close");
    await waitFor(() => ev(P.ready), 120000, "the page to be ready");
    await ev(STEP(6));
    const st = await ev(P.state), stored = await ev("(() => { try { return localStorage.getItem('arsenal.flashProtection'); } catch { return 'no storage'; } })()");
    const started = await ev(P.started);
    phase.after_start = { state: st, stored, started };
    check(`${tag}: Start starts the show with protection off, and the browser remembers "off"`, st && st.on === false && stored === "off" && started === true, phase.after_start);
    await ev(STEP(12));
    const nag1 = await ev(NAG);
    await shot(`after-start-${pageKey}-${sizeKey}.png`);
    check(`${tag}: nothing about it appears on its own after the choice (no badge, no reminder, no second screen)`, !nag1.screen && nag1.visible.length === 0, nag1);
    // a reload: the choice is remembered, no screen
    await S("Page.reload");
    await waitFor(() => ev(P.ready), 120000, "the page to be ready after a reload");
    await ev(STEP(6));
    const st2 = await ev(P.state), nag2 = await ev(NAG), started2 = await ev(P.started);
    phase.after_reload = { state: st2, nag: nag2, started: started2 };
    check(`${tag}: a reload shows no screen and starts with protection off (remembered)`, !nag2.screen && st2 && st2.on === false && st2.source === "stored" && started2 === true, phase.after_reload);
    // the quiet setting in the HUD: back on, remembered
    const box = await ev(`(() => { const b = document.querySelector(${JSON.stringify(P.hudBox)}); if (!b) return null; const r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, checked: b.checked, inView: r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth }; })()`);
    phase.hud_box = box;
    check(`${tag}: the HUD has the quiet "Flash protection" checkbox, on screen, unchecked`, box && box.checked === false && box.inView, box);
    if (box) await press(box.x, box.y);
    await ev(STEP(3));
    const st3 = await ev(P.state), stored3 = await ev("(() => { try { return localStorage.getItem('arsenal.flashProtection'); } catch { return 'no storage'; } })()");
    phase.after_hud = { state: st3, stored: stored3 };
    check(`${tag}: the HUD checkbox turns protection back on, remembered "on"`, st3 && st3.on === true && stored3 === "on", phase.after_hud);
    await shot(`hud-${pageKey}-${sizeKey}.png`);
    const errs = phase.exceptions.length + phase.console.length;
    check(`${tag}: no exceptions or console errors`, errs === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.slice(0, 3) });
  });
}

// ------------------------------------------------------------------------------------------------ identity --
// the kick storm's input (stage_verify's kickstorm, segments A and B) through the page-level pad door
const KICKS = String.raw`((from, n, draw) => {
  const s = window.__stage, out = [];
  const door = (type, detail) => window.dispatchEvent(new CustomEvent(type, { detail }));
  const kp = (pad, vel, on) => door("arsenal:pad", { pad, vel, on });
  s.skipRender = !draw;
  for (let i = 0; i < n; i++) {
    const f = from + i;
    if (f === 40) kp(1, 1, true);
    if (f === 220) kp(1, 0, false);
    if (f === 240) { kp(1, 1, true); kp(5, 1, true); }
    if (f === 420) { kp(1, 0, false); kp(5, 0, false); }
    window.__vt.step(1000 / 60);
    if (!draw) continue;
    const p = s.identityProbe(), g = s.renderer.info.gains;
    out.push({ f, differing: p.differing, max: p.max_diff, headroom: s.programmer.kick.headroom, lim: g && (g.a !== 1 || g.b !== 0) ? 1 : 0, strobing: s.programmer.kick.list.filter((k) => k.strobing).length });
  }
  s.skipRender = false;
  return out;
})`;
async function phaseIdentity(flash) {
  const tag = `identity ${flash}`;
  await burst(`identity-${flash}`, { width: 1280, height: 720 }, async ({ S, ev, phase }) => {
    await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/stage/index.html?demo=1&vt=1&w=640&h=360&hud=0&quality=receipt&flash=${flash}` });
    await waitFor(() => ev("!!(window.__stage && (window.__stage.ready || window.__stage.bootError))"), 60000, "the stage");
    const renderer = await ev(`(() => { const gl = window.__stage.renderer.gl; const e = gl.getExtension("WEBGL_debug_renderer_info"); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); })()`);
    if (!judgeRenderer(renderer).ok) throw new Error(`refusing to judge: not SwiftShader (${renderer})`);
    // to bar 14 (logic only), as the kickstorm does, then frames 0..(start-1) of its input as logic, then draw
    await ev(`(() => { const s = window.__stage; s.skipRender = true; for (let i = 0; i < 96 * 14 - 30; i++) window.__vt.step(1000 / 60); s.skipRender = false; for (let i = 0; i < 30; i++) window.__vt.step(1000 / 60); return true; })()`, 170000);
    const start = 240, n = Number(opt.frames);
    await ev(`${KICKS}(0, ${start}, false)`, 170000);
    const lim0 = await ev("window.__stage.limiter.frames"), prot = await ev("window.__stage.flashProtection()");
    const rows = [];
    for (let done = 0; done < n; done += 20) rows.push(...await ev(`${KICKS}(${start + done}, ${Math.min(20, n - done)}, true)`, 170000));
    const lim1 = await ev("window.__stage.limiter.frames");
    const differ = rows.filter((r) => r.differing > 0);
    phase.protection = prot;
    phase.frames = rows.length;
    phase.limiter_frames = [lim0, lim1];
    phase.differing_frames = differ.length;
    phase.max_diff = Math.max(0, ...rows.map((r) => r.max));
    phase.limited = rows.filter((r) => r.lim).length;
    phase.headroom_min = Math.min(...rows.map((r) => r.headroom));
    phase.strobing_frames = rows.filter((r) => r.strobing > 0).length;
    console.log(`${tag}: ${JSON.stringify({ protection: prot, frames: rows.length, limiter_frames: [lim0, lim1], differing_frames: differ.length, max_diff: phase.max_diff, limited: phase.limited, headroom_min: phase.headroom_min, strobing: phase.strobing_frames })}`);
    if (flash === "off") {
      check(`${tag}: protection is off by the URL`, prot.on === false && prot.source === "url", prot);
      check(`${tag}: the canvas equals the frame as drawn on every one of ${rows.length} frames of the kick storm (segment B: both kicks held at full, strobing)`, rows.length === n && differ.length === 0 && phase.strobing_frames > 0,
            { frames: rows.length, differing_frames: differ.length, max_diff: phase.max_diff, strobing_frames: phase.strobing_frames });
      check(`${tag}: the limiter never ran (its frame count did not move)`, lim1 === lim0, { before: lim0, after: lim1 });
      check(`${tag}: the kick governor saw a full budget (headroom 5) on every frame`, phase.headroom_min === 5, { min: phase.headroom_min });
    } else {
      check(`${tag} (control): with protection on the limiter judged every frame`, lim1 - lim0 === rows.length, { before: lim0, after: lim1, frames: rows.length });
      check(`${tag} (control): the same storm, limited: the canvas differs from the frame as drawn on some frames`, differ.length > 0, { differing_frames: differ.length, limited: phase.limited });
    }
    const errs = phase.exceptions.length + phase.console.length;
    check(`${tag}: no exceptions or console errors`, errs === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.slice(0, 3) });
  });
}

// --------------------------------------------------------------------------------------------------- vj off --
async function phaseVjOff(flash) {
  const tag = `vjoff ${flash}`;
  await burst(`vjoff-${flash}`, { width: 1280, height: 720 }, async ({ S, ev, phase }) => {
    await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/vj.html?engine=off&hud=0&watchdog=0&vt=1&sets=vj-reactor&laserseed=11&flash=${flash}` });
    await waitFor(() => ev("!!(window.__vj && window.__vj.ready)"), 240000, "the vj page");
    // the limiter's programs link in the background (protection on); half a second of frames either way
    await waitFor(() => ev(`(() => { window.__vt.step(1000 / 60); const l = window.__vj.stats().limiter; return ${flash === "off" ? "true" : "l.on || l.fatal"}; })()`), 180000, "the limiter");
    await ev(STEP(30));
    const s0 = await ev("window.__vj.stats()");
    const out = await ev(String.raw`(() => {
      const vj = window.__vj; let lit = 0;
      for (let f = 0; f < 120; f++) {
        if (f % 6 === 0) vj.press(1 + (f / 6) % 4, 1);
        if (f % 6 === 3) vj.release(1 + ((f - 3) / 6) % 4);
        window.__vt.step(1000 / 60);
        if (f % 20 === 19) {
          const gl = document.getElementById("gl").getContext("webgl2"), px = new Uint8Array(4);
          gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(gl.drawingBufferWidth >> 1, gl.drawingBufferHeight >> 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
          lit += px[0] + px[1] + px[2];
        }
      }
      return { lit };
    })()`, 170000);
    const s1 = await ev("window.__vj.stats()");
    phase.before = { frames: s0.frames, limiter: s0.limiter.frames, refused: s0.limiter.safeRefused, protection: s0.flashProtection };
    phase.after = { frames: s1.frames, limiter: s1.limiter.frames, refused: s1.limiter.safeRefused, effects: (s1.effects || []).length, protection: s1.flashProtection };
    console.log(`${tag}: ${JSON.stringify({ before: phase.before, after: phase.after, lit: out.lit })}`);
    const drawn = s1.frames - s0.frames;
    if (flash === "off") {
      check(`${tag}: protection is off by the URL`, s1.flashProtection && s1.flashProtection.on === false, s1.flashProtection);
      check(`${tag}: ${drawn} frames drawn through a pad storm and the limiter never ran (its frame count did not move)`, drawn >= 100 && s1.limiter.frames === s0.limiter.frames, { drawn, limiter: [s0.limiter.frames, s1.limiter.frames] });
      check(`${tag}: no pad effect refused (the safe mode's refusals are lifted with protection off)`, s1.limiter.safeRefused === 0, { refused: s1.limiter.safeRefused });
    } else {
      check(`${tag} (control): with protection on the limiter ran on every frame`, s1.limiter.frames - s0.limiter.frames >= drawn - 1 && drawn >= 100, { drawn, limiter: [s0.limiter.frames, s1.limiter.frames] });
    }
    check(`${tag}: the picture is not black`, out.lit > 0, out);
    const errs = phase.exceptions.length + phase.console.length;
    check(`${tag}: no exceptions or console errors`, errs === 0, { exceptions: phase.exceptions.slice(0, 3), console: phase.console.slice(0, 3) });
  });
}

// ------------------------------------------------------------------------------------------------------ main --
try {
  PORT = await listen(web, PORT);
  report.port = PORT;
  const phases = opt.phases.split(",").map((s) => s.trim()).filter(Boolean);
  for (const ph of phases) {
    if (ph === "consent") { for (const p of opt.pages.split(",")) for (const z of opt.sizes.split(",")) await phaseConsent(p.trim(), z.trim()); }
    else if (ph === "identity") { await phaseIdentity("off"); await phaseIdentity("on"); }
    else if (ph === "vjoff") { await phaseVjOff("off"); await phaseVjOff("on"); }
    else console.log(`unknown phase ${ph}`);
  }
} finally { web.close(); }
report.finished_at = new Date().toISOString();
const failed = Object.entries(report.checks).filter(([, v]) => !v.ok).map(([k]) => k);
report.verdict = failed.length ? "fail" : "pass";
report.failed = failed;
writeFileSync(join(outDir, "receipt.json"), JSON.stringify(report, null, 2));
console.log(`receipt: ${join(outDir, "receipt.json")}`);
console.log(`verdict: ${report.verdict}${failed.length ? ` (${failed.join("; ")})` : ""}`);
process.exit(failed.length ? 1 : 0);
