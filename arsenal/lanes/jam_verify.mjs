// Jam space on the real piano page (jam-spec 14: A5, A6, A7, A8, A9, A10, A12), in an isolated, muted, headless Chrome.
//
//   node arsenal/lanes/jam_verify.mjs [--port 8890] [--state DIR] [--chrome-port 9881] [--proxy-port 9884]
//                                     [--only a12,a6,a7,a8,a9,a10,a5] [--out DIR] [--framing 16:9]
//
// It starts its own `py -m arsenal serve --port <port> --root <state>/library --performance-root <state>/performance`
// (so recordings land in <state>/library and the jam files in <state>/jam), seeds the deck through the CLI with synthetic
// moments, and stops only that server. Never 8793 (Daniel's). Every note of "Daniel's" here is scripted into the page
// through __piano.midiMessage, so all practice data is synthetic. The stream-cut check of A10 puts a small HTTP proxy of
// its own on --proxy-port between the page and the server.
//
// A12  deck seed, loop start --now (the page plays and acks at L1), loop tempo +4 lands on the announced bar, loop stop,
//      practice riff latest (exit 0, L1), template save-last reaches the page's deck through the deck event within 1 s
// A6   a 60 s Loop, a Play, a remote play cue and a Hear me over 300 scripted notes: the log holds exactly his events,
//      keyRaw matches a control run, `sounding` never holds a note of Claude's or a replay's
// A7   the courtesy gate: no Claude note-on while he plays, the knock at 20 s, Enter launches, a hover waits <= 8 s, a
//      clear acts at once, --now starts the count-in, an untaken knock expires at 60 s into Tonight
// A8   deck layout and keys on the page (overlay or dock, REC, fullscreen, toast, new cards while playing, 8.7 keys,
//      KEYMAP, Space)
// A9   glass rims against the projected key tops and against the stage ghost mesh (both framings, DPR 1 and 1.5, a
//      still frame and a moving camera)
// A10  two tabs, the owner moving on input, a stream cut at a proxy, a server restart
// A5   REC in auto on a held, stepped clock: the take against a control take (drawn frames and the decoded file),
//      moonlight pixels, the recorder's sources, the recorded audio against the control, the glass during REC, jam view
//      glass outside REC, Claude back on the stage after REC
//
// GPU lock (arsenal/GPU-LOCK.md): it takes state/arsenal/gpu-render.lock through gpu_lock.mjs before it starts anything and
// holds it for the whole run, declaring a cap of 5 minutes per check (10 at least; a5 alone runs about 4.5). Render lanes
// also wait while this script runs. Started by a script that already holds the lock through gpu_lock.mjs, it inherits it.
// Writes state/arsenal/receipts/jam/<check>-<date>/<check>-<stamp>.json (and screenshots) per check plus
// jam-verify-<date>/jam-verify-<stamp>.json, and exits 1 if any check fails.
import { spawn, execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { closeSync, copyFileSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import http from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { RIM, outlineCentroid } from "../web/piano/glass.js";
import { acquireGpuLock } from "./gpu_lock.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
function pageFiles() {
  const out = {};
  for (const f of ["piano.js", "piano.html", "piano.css", "piano/deck.js", "piano/transport.js", "piano/cues.js", "piano/glass.js"]) {
    try { out[f] = createHash("sha256").update(readFileSync(join(REPO, "arsenal", "web", f))).digest("hex").slice(0, 16); } catch { out[f] = null; }
  }
  return out;
}
const { values: opt } = parseArgs({
  options: {
    port: { type: "string", default: "8890" },  // jam-rulings: 8888 is Docker Desktop's; jam lanes default to 8889 or higher
    state: { type: "string", default: "" },
    "chrome-port": { type: "string", default: "9881" },
    "proxy-port": { type: "string", default: "9884" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts", "jam") },
    only: { type: "string", default: "a12,a6,a7,a8,a9,a10,a5" },
    framing: { type: "string", default: "16:9" },
    // The piano's cinematic atmosphere (piano/spectacle.js, its own lane): "off" (default) sets its stored setting off before
    // each page loads, so these checks measure the jam space on the page's classic look; "on" leaves the page's own setting.
    spectacle: { type: "string", default: "off" },
  },
});
if (opt.port === "8793" || opt["proxy-port"] === "8793") {
  console.error("jam_verify: 8793 is Daniel's server; use a port of your own");
  process.exit(2);
}
const PORT = opt.port, CDP = opt["chrome-port"], PROXY_PORT = Number(opt["proxy-port"]);
const APP = `http://127.0.0.1:${PORT}`;
const ONLY = opt.only.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
const started = new Date();
const STAMP = started.toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const DAY = STAMP.slice(0, 8);
const STATE = opt.state || join(tmpdir(), `arsenal-jam-verify-${STAMP}`);
const LIB = join(STATE, "library"), PERF = join(STATE, "performance"), JAM = join(STATE, "jam");
const PROFILE = join(tmpdir(), `arsenal-jam-verify-chrome-${STAMP}`);
for (const d of [STATE, LIB, PERF]) mkdirSync(d, { recursive: true });
const DIRS = {
  a5: "a5-recording-clean", a6: "a6-honesty", a7: "a7-courtesy-gate", a8: "a8-deck-layout-page", a9: "a9-glass-alignment-page",
  a10: "a10-tabs-stream-restart", a12: "a12-end-to-end",
};
const dirOf = (k) => { const d = join(opt.out, `${DIRS[k]}-${DAY}`); mkdirSync(d, { recursive: true }); return d; };

const report = {
  api: "arsenal.receipt/v0", lane: "J9", title: "Jam space on the piano page (A5-A10, A12)", started_at: started.toISOString(),
  app: APP, state: STATE, chrome: null, only: ONLY, spectacle: opt.spectacle,
  // the page files the run measured (sha256, first 16 hex), at the start and the end: other lanes edit the piano page too
  page_files: { start: pageFiles() },
  flags: ["--headless=new", "--mute-audio", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
          "--disable-background-timer-throttling", "--autoplay-policy=no-user-gesture-required"],
  checks: {}, sections: {}, console: [], exceptions: [], errors: [],
};
function check(section, name, pass, detail) {
  (report.checks[section] ||= []).push({ name, pass: !!pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"} [${section}] ${name} ${JSON.stringify(detail).slice(0, 600)}`);
}
const round = (x, n = 3) => (Number.isFinite(x) ? Math.round(x * 10 ** n) / 10 ** n : x);

// ---------------------------------------------------------------------------------------------------- processes
let server = null, chrome = null, browser = null, proxy = null, gpu = null;
const killTree = (pid) => { try { execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" }); } catch { /* gone */ } };
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  let last = null;
  while (Date.now() - t0 < ms) {
    try { const v = await fn(); if (v) return v; } catch (e) { last = e; }
    await delay(100);
  }
  throw new Error(`timed out waiting for ${what}${last ? ` (${last.message})` : ""}`);
}
async function api(method, path, body) {
  const r = await fetch(`${APP}${path}`, { method, cache: "no-store", headers: body ? { "Content-Type": "application/json", Origin: APP } : undefined,
                                           body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => null);
  return { status: r.status, body: data };
}
const getJSON = async (path) => (await api("GET", path)).body;
async function startServer() {
  const fd = openSync(join(STATE, `server-${PORT}.log`), "a");
  server = spawn("py", ["-m", "arsenal", "serve", "--port", PORT, "--root", LIB, "--performance-root", PERF],
                 { cwd: REPO, stdio: ["ignore", fd, fd], windowsHide: true });
  closeSync(fd);
  await waitFor(async () => (await fetch(`${APP}/api/piano/cues/status`)).ok, 40000, `the server on ${PORT}`);
}
async function stopServer() {
  if (!server) return;
  killTree(server.pid);
  server = null;
  await waitFor(async () => { try { await fetch(`${APP}/api/piano/cues/status`); return false; } catch { return true; } }, 15000, "the server to stop");
}
function cli(args, { timeoutMs = 120000 } = {}) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    const p = spawn("py", ["-m", ...args], { cwd: REPO, windowsHide: true });
    let out = "", err = "";
    p.stdout.on("data", (d) => { out += d; });
    p.stderr.on("data", (d) => { err += d; });
    const timer = setTimeout(() => killTree(p.pid), timeoutMs);
    p.on("close", (code) => { clearTimeout(timer); resolve({ args: args.join(" "), code, out, err, t0, t1: Date.now() }); });
  });
}
const pianocue = (...a) => cli(["arsenal.pianocue", ...a, "--port", PORT]);
const brief = (r) => ({ cmd: r.args, code: r.code, out: r.out.trim().split("\n").slice(0, 4), err: r.err.trim().slice(0, 300), ms: r.t1 - r.t0 });

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map(), listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result);
      } else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const id = nextId++; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); }),
      on: (fn) => listeners.push(fn),
      close: () => { try { ws.close(); } catch { /* closed */ } },
    });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}
async function startChrome() {
  chrome = spawn(opt.chrome, [
    "--headless=new", "--mute-audio", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling", "--autoplay-policy=no-user-gesture-required", `--remote-debugging-port=${CDP}`,
    `--user-data-dir=${PROFILE}`, "--no-first-run", "--no-default-browser-check", "--window-size=1920,1080", "about:blank",
  ], { stdio: "ignore", windowsHide: true });
  const version = await waitFor(async () => (await fetch(`http://127.0.0.1:${CDP}/json/version`)).json(), 30000, "Chrome");
  report.chrome = version.Browser;
  browser = await connect(version.webSocketDebuggerUrl);
}
const pages = [];
async function openTab(label) {
  const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
  const target = await waitFor(async () => (await (await fetch(`http://127.0.0.1:${CDP}/json/list`)).json()).find((t) => t.id === targetId), 10000, "the tab");
  const ws = await connect(target.webSocketDebuggerUrl);
  const page = { label, targetId, ws };
  ws.on((m) => {
    if (m.method === "Runtime.exceptionThrown") {
      const d = m.params.exceptionDetails;
      report.exceptions.push({ page: label, text: (d.exception && d.exception.description) || d.text });
    }
    if (m.method === "Runtime.consoleAPICalled" && /error|warn/.test(m.params.type)) {
      const text = m.params.args.map((a) => a.value ?? a.description).join(" ");
      if (!/X4122/.test(text)) report.console.push({ page: label, type: m.params.type, text: text.slice(0, 300) });
    }
  });
  await ws.send("Page.enable");
  await ws.send("Runtime.enable");
  if (opt.spectacle === "off") {
    await ws.send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { try { const k = "arsenal.piano.spectacle";
      const s = JSON.parse(localStorage.getItem(k) || "{}"); s.enabled = false; localStorage.setItem(k, JSON.stringify(s)); } catch { /* storage blocked */ } })()` });
  }
  await ws.send("Emulation.setFocusEmulationEnabled", { enabled: true });
  page.ev = async (expression, { timeoutMs = 120000 } = {}) => {
    let timer;
    const r = await Promise.race([
      ws.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }),
      new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`no answer in ${timeoutMs} ms: ${expression.slice(0, 120)}`)), timeoutMs); }),
    ]).finally(() => clearTimeout(timer));
    if (r.exceptionDetails) throw new Error(`[${label}] ${(r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text}`);
    return r.result.value;
  };
  page.key = async (code, { shift = false, repeat = false } = {}) => {
    const KEYS = { KeyA: ["a", 65], KeyK: ["k", 75], ArrowUp: ["ArrowUp", 38], ArrowDown: ["ArrowDown", 40], Enter: ["Enter", 13],
                   Backslash: ["\\", 220], Quote: ["'", 222], Minus: ["-", 189], Equal: ["=", 187], BracketLeft: ["[", 219],
                   BracketRight: ["]", 221], Escape: ["Escape", 27], Backspace: ["Backspace", 8], Space: [" ", 32],
                   Comma: [",", 188], Period: [".", 190], Semicolon: [";", 186], Slash: ["/", 191] };
    let [k, vk] = KEYS[code] || [code.replace(/^Key|^Digit/, "").toLowerCase(), code.startsWith("Key") ? code.charCodeAt(3) : code.startsWith("Digit") ? code.charCodeAt(5) : 0];
    const modifiers = shift ? 8 : 0;
    await ws.send("Input.dispatchKeyEvent", { type: "keyDown", code, key: k, windowsVirtualKeyCode: vk, modifiers, autoRepeat: repeat });
    await ws.send("Input.dispatchKeyEvent", { type: "keyUp", code, key: k, windowsVirtualKeyCode: vk, modifiers });
  };
  page.shot = async (dir, name) => {
    const s = await ws.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(join(dir, name), Buffer.from(s.data, "base64"));
    return name;
  };
  page.close = async () => { try { await browser.send("Target.closeTarget", { targetId }); } catch { /* closed */ } ws.close(); };
  pages.push(page);
  return page;
}
// In-page helpers: a scheduler for Daniel's scripted MIDI (the tracking of what he sounds), and samplers.
const HELPERS = `(() => {
  if (window.__jv) return true;
  window.__jv = {
    // events: [[at_ms, [bytes]], ...] sorted; the handle tracks what his notes sound (held or under the pedal)
    run(events, { keyRaw = false } = {}) {
      const h = { t0: performance.now(), wall0: Date.now(), sent: 0, done: false, keyRaw: [], expected: new Set(), held: new Set(), pedal: false };
      h.promise = new Promise((resolve) => {
        let i = 0;
        const step = () => {
          const now = performance.now() - h.t0;
          while (i < events.length && events[i][0] <= now) {
            const b = events[i][1], type = b[0] & 0xf0;
            window.__piano.midiMessage(b);
            if (type === 0x90 && b[2] > 0) { h.held.add(b[1]); h.expected.add(b[1]); if (keyRaw) h.keyRaw.push(window.__piano.stats().keyRaw); }
            else if (type === 0x80 || (type === 0x90 && b[2] === 0)) { h.held.delete(b[1]); if (!h.pedal) h.expected.delete(b[1]); }
            else if (type === 0xb0 && b[1] === 64) { h.pedal = b[2] >= 64; if (!h.pedal) h.expected = new Set(h.held); }
            i++; h.sent++;
          }
          if (i >= events.length) { h.done = true; resolve(h.sent); return; }
          setTimeout(step, Math.max(0, Math.min(8, events[i][0] - now)));
        };
        step();
      });
      window.__jv.current = h;
      return h;
    },
    // 60 Hz: does the page's sounding hold only what his script sounds?
    sampleSounding() {
      const s = { samples: 0, bad: 0, examples: [], claudeMax: 0 };
      s.timer = setInterval(() => {
        const h = window.__jv.current;
        const st = window.__piano.stats();
        s.samples++;
        const extra = st.sounding.filter((m) => !(h && h.expected.has(m)));
        if (extra.length) { s.bad++; if (s.examples.length < 10) s.examples.push({ t: Math.round(performance.now()), extra, cue: st.cue.sounding }); }
        s.claudeMax = Math.max(s.claudeMax, st.cue.sounding.length);
      }, 16);
      window.__jv.sampler = s;
      return true;
    },
    // alpha-weighted centroid of the glass canvas's pixels (alpha >= alphaMin) inside a CSS box, in CSS px; yMin (CSS px):
    // only pixels below that line (the part of a white key's top in front of the black keys)
    glassCentroid(box, alphaMin = 64, yMin = -Infinity) {
      const c = document.getElementById("jam-glass"), g = c.getContext("2d");
      const dpr = c.width / (parseFloat(c.style.width) || c.width);
      const x0 = Math.max(0, Math.floor((box[0] - 6) * dpr)), y0 = Math.max(0, Math.floor((box[1] - 6) * dpr));
      const x1 = Math.min(c.width, Math.ceil((box[2] + 6) * dpr)), y1 = Math.min(c.height, Math.ceil((box[3] + 6) * dpr));
      if (x1 <= x0 || y1 <= y0) return null;
      const img = g.getImageData(x0, y0, x1 - x0, y1 - y0);
      let sx = 0, sy = 0, sw = 0, n = 0;
      for (let y = 0; y < img.height; y++) for (let x = 0; x < img.width; x++) {
        const a = img.data[(y * img.width + x) * 4 + 3];
        if (a < alphaMin || (y0 + y + 0.5) / dpr < yMin) continue;
        sx += (x0 + x + 0.5) * a; sy += (y0 + y + 0.5) * a; sw += a; n++;
      }
      return sw ? { c: [sx / sw / dpr, sy / sw / dpr], pixels: n, dpr } : { c: null, pixels: 0, dpr };
    },
    glassAlpha() {
      const c = document.getElementById("jam-glass");
      if (!c.width) return 0;
      const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 3; i < d.length; i += 4) if (d[i] > 16) n++;
      return n;
    },
    rect(el) { if (!el || el.hidden) return null; const b = el.getBoundingClientRect(); return b.width || b.height ? { x: +b.left.toFixed(2), y: +b.top.toFixed(2), w: +b.width.toFixed(2), h: +b.height.toFixed(2) } : null; },
    rects() {
      const d = window.__piano.jam.deck, $ = (id) => document.getElementById(id);
      const open = d.stats().open;
      return { stage: this.rect($("stage")), canvas: this.rect($("piano-canvas")), glass: this.rect($("jam-glass")),
               deck: open ? this.rect(document.querySelector("#deck .deck-panel")) : null, tab: open ? null : this.rect(document.querySelector("#deck .deck-tab")),
               pill: this.rect($("jam-pill")), toast: this.rect($("toast")), viewport: { w: innerWidth, h: innerHeight, dpr: devicePixelRatio } };
    },
  };
  return true;
})()`;
async function loadPiano(page, query, { origin = APP } = {}) {
  await page.ws.send("Page.navigate", { url: `${origin}/piano?${query}` });
  await waitFor(() => page.ev("!!(window.__piano && window.__piano.ready)"), 40000, `${page.label}: the piano page`);
  await waitFor(() => page.ev("(() => { const j = window.__piano.jam; return !!(j.deck && j.deck.stats().cards >= 17 && window.__piano.stats().cue.status === 'listening'); })()"),
                30000, `${page.label}: the deck and the stream`);
  await page.ev("window.__piano.cues.voice.unlock().then(() => window.__piano.cues.voice.status())");
  await page.ev(HELPERS);
  await page.ev("document.fonts.ready.then(() => true)");
}

// -------------------------------------------------------------------------------------------------- Daniel's notes
const EB = [70, 72, 74, 75, 77, 79, 81, 82, 84, 86];  // B♭4 up to D6 in E♭ major: his register, above Claude's G4
// count notes, one every `every` ms, each `len` ms; the pedal goes down on each bar of `bar` ms and changes 80 ms early
function melody({ count, every, len, start = 0, bar = 0, velocity = (i) => 56 + ((i * 29) % 40) }) {
  const ev = [];
  for (let i = 0; i < count; i++) {
    const t = start + i * every, n = EB[(i * 3 + (i >> 2)) % EB.length];
    ev.push([t, [0x90, n, velocity(i)]]);
    ev.push([t + len, [0x80, n, 0]]);
  }
  if (bar) {
    const end = start + count * every;
    for (let t = start; t < end; t += bar) { ev.push([t + 5, [0xb0, 64, 127]]); ev.push([Math.min(end, t + bar) - 80, [0xb0, 64, 0]]); }
  }
  return ev.sort((a, b) => a[0] - b[0] || (a[1][0] === 0x80 ? -1 : 1));
}
const at = (wall0, ms, fn) => delay(Math.max(0, wall0 + ms - Date.now())).then(fn);
const alignmentOf = (doc) => { const a = doc && doc.alignment; return Array.isArray(a) ? a[0] : a; };
function sessionsOfPage(pageId) {  // the synthetic sessions a page's log opened (the server's store under <state>/performance)
  const out = [];
  if (!existsSync(PERF)) return out;
  for (const name of readdirSync(PERF)) {
    const f = join(PERF, name, "session.json");
    if (!existsSync(f)) continue;
    try {
      const info = JSON.parse(readFileSync(f, "utf8"));
      if (info.meta && info.meta.page_id === pageId) {
        const events = readFileSync(join(PERF, name, "events.jsonl"), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
        out.push({ session: name, info, events });
      }
    } catch { /* partly written */ }
  }
  return out;
}
const kindCounts = (events) => events.reduce((acc, e) => { acc[e.kind] = (acc[e.kind] || 0) + 1; return acc; }, {});

// ---------------------------------------------------------------------------------------------------------- A12
async function a12() {
  const sec = report.sections.a12 = {};
  const moments = join(STATE, "moments-synthetic.json");
  writeFileSync(moments, JSON.stringify({ api: "arsenal.jam.seed.moments/v0", cards: {
    "lydian-four": { moments: [{ session: "20300101-000012-5e55a0f1", at: "5:22", until: "5:30", label: "synthetic" }] } } }));
  const seed = await pianocue("deck", "seed", "--moments", moments);
  sec.seed = brief(seed);
  const installed = /installed (\d+)/.exec(seed.out);
  check("a12", "1. deck seed installs 17 cards", seed.code === 0 && installed && +installed[1] === 17, sec.seed);

  const page = await openTab("a12");
  const pageId = `p-jv-a12-${STAMP.replace("-", "")}`;
  await loadPiano(page, `page=${pageId}&jam=auto`);
  await page.ev(`window.__jvA12 = window.__jv.run(${JSON.stringify(melody({ count: 110, every: 420, len: 330, bar: 2520 }))}); true`);
  await delay(2600);
  const start = await pianocue("loop", "start", "lydian-four", "--now");
  sec.start = brief(start);
  const runId = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(start.out) || [])[1] || null;
  sec.run = runId;
  let played = null;
  try {
    played = await waitFor(() => page.ev(`(() => { const s = window.__piano.jam.transport.stats(); const r = s.runs.find((x) => x.run === ${JSON.stringify(runId)});
      return r && r.handed > 0 && s.acks > 0 && s.notes > 0 ? { acks: s.acks, notes: s.notes, bars: s.bars, owner: s.owner, page: s.page_id } : null; })()`), 20000, "the page plays and acks");
  } catch (e) { sec.play_error = e.message; }
  let align = null;
  try {
    await waitFor(async () => { align = alignmentOf(await getJSON(`/api/piano/jam/runs/${runId}`)); return align && align.method === "L1"; }, 30000, "L1");
  } catch (e) { sec.align_error = e.message; }
  sec.played = played;
  sec.alignment_live = align;
  check("a12", "2. loop start lydian-four --now: the headless page plays and acks at L1",
        start.code === 0 && !!runId && !!played && align && align.method === "L1", { start: sec.start, played, alignment: align && { method: align.method, error_ms: align.error_ms, page_id: align.page_id } });

  await delay(3000);
  const tempo = await pianocue("loop", "tempo", "+4");
  sec.tempo = brief(tempo);
  const announced = +((/from bar (-?\d+)/.exec(tempo.out) || [])[1]);
  let landed = null;
  try {
    landed = await waitFor(async () => {
      const doc = await getJSON(`/api/piano/jam/runs/${runId}`);
      const seg = doc.run.segments.find((s) => s.from_bar === announced && s.bpm === 70);
      const ack = doc.events.find((e) => e.kind === "ack" && e.effective_bar === announced);
      return seg && ack ? { segment: seg, ack: { bar: ack.bar, version: ack.version, effective_bar: ack.effective_bar, page_id: ack.page_id } } : null;
    }, 30000, "the tempo change on its bar");
  } catch (e) { sec.tempo_error = e.message; }
  sec.tempo_landed = landed;
  check("a12", "3. loop tempo +4 lands on the announced bar (the run's segment starts there at 70 bpm; the page acks effective_bar there)",
        tempo.code === 0 && Number.isInteger(announced) && !!landed, { announced, landed });

  await delay(2500);
  const stop = await pianocue("loop", "stop");
  sec.stop = brief(stop);
  const stopBar = +((/from bar (-?\d+)/.exec(stop.out) || [])[1]);
  let closed = null;
  try {
    closed = await waitFor(async () => { const doc = await getJSON(`/api/piano/jam/runs/${runId}`); return doc.run.closed ? doc.run : null; }, 30000, "the run to close");
  } catch (e) { sec.stop_error = e.message; }
  check("a12", "4. loop stop: the run stops on its bar", stop.code === 0 && closed && closed.stop_bar === stopBar,
        { stop: sec.stop, stop_bar: closed && closed.stop_bar, reason: closed && closed.stop_reason });

  await page.ev("window.__jvA12.promise");
  await page.ev("Promise.resolve(window.__piano.log.flush()).then(() => true)");
  await delay(1500);
  const riff = await cli(["arsenal.practice", "riff", "latest", "--root", PERF, "--jam-root", JAM, "--json"]);
  let riffDoc = null;
  try { riffDoc = JSON.parse(riff.out); } catch { /* not JSON */ }
  const block = riffDoc && (riffDoc.runs || []).find((b) => b.run === runId);
  sec.riff = { ...brief(riff), out: riff.out.slice(0, 200), run: block && block.run, alignment: block && block.alignment,
               coverage: block && block.coverage, enough: block && block.enough };
  check("a12", "5. practice riff latest over the scripted notes: exit 0, alignment L1", riff.code === 0 && block && block.alignment.method === "L1",
        { code: riff.code, run: block && block.run, alignment: block && block.alignment, err: riff.err.slice(0, 300) });

  const before = await page.ev("window.__piano.jam.deck.stats().cards");
  await page.ev(`(() => { const d = window.__piano.jam.deck; window.__jvCard = { n0: d.stats().cards, at: null };
    window.__jvCard.timer = setInterval(() => { if (!window.__jvCard.at && d.stats().cards > window.__jvCard.n0) window.__jvCard.at = Date.now(); }, 5); return true; })()`);
  const saved = await pianocue("template", "save-last", "--root", PERF, "--json");
  let card = null;
  try { card = JSON.parse(saved.out); } catch { /* text */ }
  const appeared = await waitFor(() => page.ev("window.__jvCard.at"), 5000, "the kept card in the page's deck").catch(() => null);
  const deckFrames = await page.ev("window.__piano.jam.deck.stats().frames");
  const cardId = card && (card.id || (card.card && card.card.id));
  const seen = cardId ? await page.ev(`window.__piano.jam.deck.act('open', { cardId: ${JSON.stringify(cardId)} }).then(() => { const d = window.__piano.jam.deck.stats(); return { selected: d.selected, group: document.querySelector('.deck-card.selected') ? document.querySelector('.deck-card.selected').dataset.id : null }; })`) : null;
  sec.template = { ...brief(saved), card: cardId, group: card && (card.card || card).group, before, appeared_wall: appeared, cli_exit: saved.t1,
                   ms_after_cli_exit: appeared ? appeared - saved.t1 : null, deck_frames: deckFrames, seen };
  check("a12", "6. template save-last makes a Kept card that appears in the page's deck within 1 s through the deck event",
        saved.code === 0 && cardId && appeared && appeared - saved.t1 <= 1000 && (card.card || card).group === "kept",
        { card: cardId, ms_after_cli_exit: sec.template.ms_after_cli_exit, group: sec.template.group });
  await page.shot(dirOf("a12"), `a12-page-${STAMP}.png`);
  await page.close();
}

// ----------------------------------------------------------------------------------------------------------- A6
async function a6() {
  const sec = report.sections.a6 = {};
  const script = melody({ count: 300, every: 200, len: 140, bar: 2000 });
  const runOne = async (label, withClaude, controlSession) => {
    const page = await openTab(`a6-${label}`);
    const pageId = `p-jv-a6-${label}-${STAMP.replace("-", "")}`;
    await loadPiano(page, `page=${pageId}&jam=auto`);
    await page.ev("window.__jv.sampleSounding()");
    await page.ev("window.__piano.jam.record(true)");
    const wall0 = await page.ev(`(() => { const h = window.__jv.run(${JSON.stringify(script)}, { keyRaw: true }); window.__jvA6 = h; return h.wall0; })()`);
    const actions = [];
    if (withClaude) {
      actions.push(at(wall0, 1000, () => pianocue("loop", "start", "lydian-four", "--now")));
      actions.push(at(wall0, 20000, () => pianocue("card", "play", "held-sus-five", "--now")));
      actions.push(at(wall0, 30000, () => pianocue("play", "Ebmaj9", "--key", "Eb major")));
      actions.push(at(wall0, 40000, () => page.ev(`fetch('/api/piano/replay?session=${controlSession}&at=0:05&seconds=8&speed=1').then((r) => r.json()).then((o) => { window.__jvReplay = o.cue ? window.__piano.cues.play(o.cue) : o; return !!o.cue; })`)));
      actions.push(at(wall0, 61000, () => pianocue("loop", "stop", "--now")));
    }
    const done = await Promise.all(actions);
    await page.ev("window.__jvA6.promise");
    await delay(1500);
    await page.ev("Promise.resolve(window.__piano.log.flush()).then(() => true)");
    await delay(1500);
    const res = await page.ev(`(() => { const h = window.__jvA6, s = window.__jv.sampler; clearInterval(s.timer);
      const strikes = window.__piano.jam.strikes || [];
      return { sent: h.sent, keyRaw: h.keyRaw, samples: s.samples, bad: s.bad, examples: s.examples, claudeMax: s.claudeMax,
               claudeStrikes: strikes.filter((x) => x.source === 'claude').length, replayStrikes: strikes.filter((x) => x.source === 'replay').length,
               session: window.__piano.log.status().session, noteOns: window.__piano.stats().noteOns }; })()`);
    const sessions = sessionsOfPage(pageId);
    const events = sessions.flatMap((s) => s.events);
    res.sessions = sessions.map((s) => s.session);
    res.kinds = kindCounts(events);
    res.actions = done.map((d) => (d && d.args ? brief(d) : d));
    await page.close();
    return res;
  };
  const control = await runOne("control", false, null);
  sec.control = { ...control, keyRaw: control.keyRaw.length };
  const take = await runOne("take", true, control.session);
  sec.take = { ...take, keyRaw: take.keyRaw.length };
  const pedals = script.filter((e) => e[1][0] === 0xb0).length;
  check("a6", "the practice log holds exactly Daniel's events: 300 on, 300 off and his pedal events; 0 extra (take = control)",
        take.kinds.on === 300 && take.kinds.off === 300 && take.kinds.pedal === pedals && control.kinds.on === 300 &&
        JSON.stringify(Object.keys(take.kinds).sort()) === JSON.stringify(Object.keys(control.kinds).sort()) &&
        take.kinds.pedal === control.kinds.pedal && take.kinds.sound_end === control.kinds.sound_end,
        { take: take.kinds, control: control.kinds, pedal_events_scripted: pedals, sessions: { take: take.sessions, control: control.sessions } });
  const sameKeyRaw = JSON.stringify(take.keyRaw) === JSON.stringify(control.keyRaw);
  check("a6", "the stats().keyRaw sequence (one reading per note-on) is identical to the control run's", sameKeyRaw && take.keyRaw.length === 300,
        { n: take.keyRaw.length, first_difference: sameKeyRaw ? null : take.keyRaw.findIndex((k, i) => k !== control.keyRaw[i]) });
  check("a6", "stats().sounding never holds a note only Claude or a replay holds (60 Hz samples)",
        take.bad === 0 && take.samples > 3000 && take.claudeStrikes > 0 && take.replayStrikes > 0,
        { samples: take.samples, violations: take.bad, examples: take.examples, claude_strikes: take.claudeStrikes, replay_strikes: take.replayStrikes, claude_sounding_max: take.claudeMax });
  const pianoJs = readFileSync(join(REPO, "arsenal", "web", "piano.js"), "utf8");
  const rarity = (pianoJs.match(/rarity/gi) || []).length;
  check("a6", "rarity scorer inputs from Claude or replay notes: 0 (no scorer on the page yet; the notes a scorer would read, sounding and the log, carry none)",
        take.bad === 0 && take.kinds.on === 300, { rarity_mentions_in_piano_js: rarity });
  check("a6", "0 events of any new kind are sent (the log's kinds are the control's)",
        Object.keys(take.kinds).every((k) => ["on", "off", "pedal", "chord", "sound_end"].includes(k)), { kinds: Object.keys(take.kinds) });
}

// ----------------------------------------------------------------------------------------------------------- A7
async function a7() {
  const sec = report.sections.a7 = {};
  const page = await openTab("a7");
  const pageId = `p-jv-a7-${STAMP.replace("-", "")}`;
  await loadPiano(page, `page=${pageId}&jam=auto`);
  await page.ev("window.__piano.jam.record(true)");
  await page.ev(`(() => { const v = window.__piano.cues.view, t = window.__piano.jam.transport;
    const s = window.__jvA7s = { rows: [], last: null };
    s.timer = setInterval(() => {
      const now = document.querySelector('#deck .deck-now'), cnt = document.querySelector('#deck .now-count');
      const st = t.state();
      const row = { t: Date.now(), knock: !!(now && now.dataset.state === 'knock'), ghosts: v.ghost.size, cue: v.last ? v.last.type + ':' + v.last.id : null,
                    state: st.state, pending: st.pending.length, counting: !!(cnt && !cnt.hidden && cnt.textContent) };
      const key = JSON.stringify([row.knock, row.ghosts, row.cue, row.state, row.pending, row.counting]);
      if (key !== s.last) { s.rows.push(row); s.last = key; }
    }, 4);
    return true; })()`);
  // Daniel has used this tab (the jam's owner lease), then plays a note every 250 ms for 25 s
  sec.claim = await page.ev("window.__piano.jam.transport.claimOwner(true).then((r) => r && r.owner)");
  const wall0 = await page.ev(`(() => { const h = window.__jv.run(${JSON.stringify(melody({ count: 100, every: 250, len: 120, velocity: () => 70 }))}); window.__jvA7 = h; return h.wall0; })()`);
  const [start, hover, clear] = await Promise.all([
    at(wall0, 1800, () => pianocue("loop", "start", "lydian-four")),  // the CLI reaches the server about 0.2 s later: arrival at about 2 s
    at(wall0, 10000, () => pianocue("hover", "Ebmaj9", "--key", "Eb major", "--hold", "0")),
    at(wall0, 23000, () => pianocue("clear")),
    at(wall0, 24000, () => page.key("Enter")),
  ]);
  sec.cli = { start: brief(start), hover: brief(hover), clear: brief(clear) };
  await page.ev("window.__jvA7.promise");
  await delay(3000);
  const rows = await page.ev("window.__jvA7s.rows");
  const strikes = await page.ev("(window.__piano.jam.strikes || []).map((x) => ({ wall: performance.timeOrigin + x.t, m: x.m, cue: x.cue, sound: x.sound }))");
  const runId = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(start.out) || [])[1] || null;
  const doc = runId ? await getJSON(`/api/piano/jam/runs/${runId}`) : null;
  const rel = (w) => (w === null || w === undefined ? null : round((w - wall0) / 1000, 3));
  const arrived = rows.find((r) => r.pending > 0);
  const knockAt = rows.find((r) => r.knock);
  const hoverArrived = rows.find((r) => r.cue && r.cue.startsWith("hover:"));
  const hoverShown = hoverArrived && rows.find((r) => r.t >= hoverArrived.t && r.ghosts > 0);
  const clearRow = rows.find((r) => r.cue && r.cue.startsWith("clear:"));
  const countIn = rows.find((r) => r.counting);
  const launch = doc && doc.events.find((e) => e.kind === "launch");
  const early = strikes.filter((s) => s.wall >= wall0 + 2000 && s.wall <= wall0 + 22000);
  sec.timeline = { arrived: rel(arrived && arrived.t), knock: rel(knockAt && knockAt.t), hover_arrived: rel(hoverArrived && hoverArrived.t),
                   hover_shown: rel(hoverShown && hoverShown.t), clear: rel(clearRow && clearRow.t), count_in: rel(countIn && countIn.t),
                   launch: launch && { recorded: rel(launch.recorded_epoch_ms), start_epoch: rel(launch.start_epoch_ms), lead_ms: round(launch.start_epoch_ms - launch.recorded_epoch_ms, 1), page_id: launch.page_id },
                   courtesy: doc && doc.run.courtesy, strikes_2_22: early.length, first_strike: rel(strikes.length ? strikes[0].wall : null) };
  check("a7", "0 Claude note-ons from 2 s to 22 s while he plays", runId && early.length === 0, { run: runId, strikes_2_22: early.length, first_strike_s: sec.timeline.first_strike });
  const knockDelay = knockAt && arrived ? (knockAt.t - arrived.t) / 1000 : null;
  check("a7", "the knock is visible 20 s after the run arrives (at 22 s +/- 0.25 s for a run arriving at 2 s)",
        knockDelay !== null && Math.abs(knockDelay - 20) <= 0.25, { arrived_s: sec.timeline.arrived, knock_s: sec.timeline.knock, knock_after_arrival_s: round(knockDelay) });
  const cleared = clearRow && clearRow.ghosts === 0 && rows.filter((r) => r.t > clearRow.t && r.t < clearRow.t + 50).every((r) => r.ghosts === 0);
  const hoverWait = hoverShown && hoverArrived ? (hoverShown.t - hoverArrived.t) / 1000 : null;
  check("a7", "a hover arriving while he plays waits, then appears by 8.4 s", hoverWait !== null && hoverWait >= 7.5 && hoverWait <= 8.4,
        { hover_arrived_s: sec.timeline.hover_arrived, shown_s: sec.timeline.hover_shown, waited_s: round(hoverWait) });
  check("a7", "a clear during the knock acts within 50 ms (the ghosts go in the same task the clear arrives in)",
        !!cleared && !!knockAt && clearRow.t >= knockAt.t, { clear_s: sec.timeline.clear, ghosts_at_clear: clearRow && clearRow.ghosts, knock_showing: !!knockAt });
  check("a7", "Enter at 24 s calls launch with an epoch >= now + 150 ms, and the count-in starts on it",
        launch && launch.start_epoch_ms - launch.recorded_epoch_ms >= 150 && doc.run.courtesy && doc.run.courtesy.via === "knock" &&
        countIn && Math.abs(countIn.t - launch.start_epoch_ms) <= 150,
        { launch: sec.timeline.launch, courtesy: doc && doc.run.courtesy, count_in_s: sec.timeline.count_in });
  await pianocue("loop", "stop", "--now");
  await delay(1500);

  // --now: the count-in starts without waiting, while he plays
  await page.ev(`(() => { window.__jvA7s.rows.length = 0; const h = window.__jv.run(${JSON.stringify(melody({ count: 24, every: 250, len: 120, velocity: () => 70 }))}); window.__jvA7 = h; return h.wall0; })()`);
  await delay(800);
  const now = await pianocue("loop", "start", "lydian-four", "--now");
  const nowRun = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(now.out) || [])[1] || null;
  await delay(3500);
  const rowsNow = await page.ev("window.__jvA7s.rows");
  const countNow = rowsNow.find((r) => r.counting);
  const nowDoc = nowRun ? await getJSON(`/api/piano/jam/runs/${nowRun}`) : null;
  sec.now = { cli: brief(now), run: nowRun, count_in_after_cli_ms: countNow ? countNow.t - now.t1 : null, courtesy: nowDoc && nowDoc.run.courtesy,
              start_epoch_ms: nowDoc && nowDoc.run.start_epoch_ms };
  check("a7", "--now starts the count-in without waiting (while he plays)",
        now.code === 0 && countNow && nowDoc && nowDoc.run.courtesy.via === "now" && Math.abs(countNow.t - nowDoc.run.start_epoch_ms) <= 150,
        { count_in_after_cli_ms: sec.now.count_in_after_cli_ms, courtesy: sec.now.courtesy });
  await page.ev("window.__jvA7.promise");
  await pianocue("loop", "stop", "--now");
  await delay(1500);

  // A knock left for 60 s: the run stops with expired, and the card shows in Tonight
  const wallC = await page.ev(`(() => { window.__jvA7s.rows.length = 0; const h = window.__jv.run(${JSON.stringify(melody({ count: 90, every: 250, len: 120, velocity: () => 70 }))}); window.__jvA7 = h; return h.wall0; })()`);
  await delay(500);
  const late = await pianocue("loop", "start", "lydian-four");
  const lateRun = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(late.out) || [])[1] || null;
  let expired = null;
  try {
    expired = await waitFor(async () => { const d = await getJSON(`/api/piano/jam/runs/${lateRun}`); return d.run.closed ? d.run : null; }, 110000, "the knock to expire");
  } catch (e) { sec.expire_error = e.message; }
  const rowsC = await page.ev("window.__jvA7s.rows");
  const knockC = rowsC.find((r) => r.knock), goneC = knockC && rowsC.find((r) => r.t > knockC.t && !r.knock);
  const tonight = await page.ev(`(() => { const d = window.__piano.jam.deck; d.open(); const b = [...document.querySelectorAll('#deck .deck-tabbtn')].find((x) => x.dataset.tab === 'tonight'); b.click();
    const ids = d.visible(); d.close(); return ids; })()`);
  sec.expire = { run: lateRun, reason: expired && expired.stop_reason, knock_s: knockC ? round((knockC.t - wallC) / 1000) : null,
                 knock_gone_after_s: goneC ? round((goneC.t - knockC.t) / 1000) : null, tonight_has_card: tonight.includes("lydian-four") };
  check("a7", "a knock left 60 s stops its run with expired, and the card shows in Tonight",
        expired && expired.stop_reason === "expired" && goneC && Math.abs((goneC.t - knockC.t) / 1000 - 60) <= 1 && tonight.includes("lydian-four"), sec.expire);
  await page.shot(dirOf("a7"), `a7-page-${STAMP}.png`);
  await page.close();
}

// ----------------------------------------------------------------------------------------------------------- A8
const KEYMAP_CODES = ["KeyZ", "KeyS", "KeyX", "KeyD", "KeyC", "KeyV", "KeyG", "KeyB", "KeyN", "KeyJ", "KeyM", "Comma", "KeyL", "Period",
  "Semicolon", "Slash", "KeyQ", "Digit2", "KeyW", "Digit3", "KeyE", "KeyR", "Digit5", "KeyT", "Digit6", "KeyY", "Digit7", "KeyU", "KeyI",
  "Digit9", "KeyO", "Digit0", "KeyP"];
async function a8() {
  const sec = report.sections.a8 = { matrix: [] };
  const page = await openTab("a8");
  const pageId = `p-jv-a8-${STAMP.replace("-", "")}`;
  const viewport = (w, h, dpr = 1) => page.ws.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: dpr, mobile: false });
  const ev = page.ev;
  const recOn = async (on) => {
    const state = await ev("window.__piano.stats().rec");
    if ((state === "recording") !== on) await ev("document.getElementById('btn-rec').click(), true");
    await waitFor(() => ev(on ? "window.__piano.stats().rec === 'recording'" : "window.__piano.stats().rec === 'idle'"), 20000, `REC ${on ? "on" : "off"}`);
    await delay(350);  // the deck's ticker (250 ms) notices REC
  };
  const d = (a, b) => (a && b ? Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.w - b.w), Math.abs(a.h - b.h)) : null);
  for (const [vw, vh] of [[1280, 900], [1920, 1080], [2560, 1440]]) {
    await viewport(vw, vh);
    await loadPiano(page, `page=${pageId}-${vw}&jam=auto`);
    for (const framing of ["9:16", "16:9"]) {
      for (const fullscreen of [false, true]) {
        await ev(`document.getElementById(${JSON.stringify(framing === "9:16" ? "btn-916" : "btn-169")}).click(); window.__piano.jam.deck.close(); true`);
        if (fullscreen) await ev("document.getElementById('stage').requestFullscreen().then(() => true)");
        else await ev("document.fullscreenElement ? document.exitFullscreen().then(() => true) : true");
        await delay(300);
        const closed = await ev("window.__jv.rects()");
        const isFs = await ev("!!document.fullscreenElement");
        const f = framing === "9:16" ? { w: 1080, h: 1920 } : { w: 1920, h: 1080 };
        const pad = isFs ? 0 : 14;
        const fit = (W, H) => Math.floor(f.w * Math.max(0.05, Math.min((W - 2 * pad) / f.w, (H - 2 * pad) / f.h)));
        const margin = (closed.stage.w - fit(closed.stage.w, closed.stage.h)) / 2;
        const expect = margin >= 392 ? "overlay" : "dock";
        await ev("window.__piano.jam.deck.open(), true");
        await delay(300);
        const opened = await ev("window.__jv.rects()");
        const layout = await ev("window.__piano.jam.deck.stats().layout");
        const row = { viewport: `${vw}x${vh}`, framing, fullscreen: isFs, margin: round(margin, 1), expect, mode: layout.mode, stage: closed.stage,
                      canvas_closed: closed.canvas, canvas_open: opened.canvas, deck: opened.deck };
        if (expect === "overlay") row.canvas_delta_px = round(d(closed.canvas, opened.canvas), 2);
        else {
          row.canvas_width = opened.canvas.w;
          row.expected_width = fit(closed.stage.w - 380, closed.stage.h);
          row.width_ok = Math.abs(opened.canvas.w - row.expected_width) <= 1;
          row.literal_ok = Math.abs(opened.canvas.w - (closed.stage.w - 380 - 2 * pad)) <= 1;
          row.no_overlap = opened.canvas.x + opened.canvas.w <= opened.deck.x + 0.5;
        }
        row.glass_matches_canvas = d(opened.glass, opened.canvas) <= 0.5;
        await ev("window.__piano.jam.deck.act('capture'), true");  // "Nothing of yours is sounding to keep": a toast
        await delay(100);
        const tOpen = await ev("window.__jv.rects()");
        await ev("window.__piano.jam.deck.close(), true");
        await delay(150);
        const tClosed = await ev("window.__jv.rects()");
        const hit = (a, b) => !!(a && b && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h);
        row.toast = !!tOpen.toast;
        row.toast_hits_deck = hit(tOpen.toast, tOpen.deck);
        row.toast_hits_tab = hit(tClosed.toast, tClosed.tab);
        // REC: open and close change the canvas by 0 px (from closed, and from a docked deck)
        await recOn(true);
        const r0 = (await ev("window.__jv.rects()")).canvas;
        await ev("window.__piano.jam.deck.open(), true"); await delay(200);
        const r1 = (await ev("window.__jv.rects()")).canvas;
        await ev("window.__piano.jam.deck.close(), true"); await delay(200);
        const r2 = (await ev("window.__jv.rects()")).canvas;
        await recOn(false);
        await ev("window.__piano.jam.deck.open(), true"); await delay(200);
        const q0 = (await ev("window.__jv.rects()")).canvas;
        await recOn(true);
        await ev("window.__piano.jam.deck.close(), true"); await delay(200);
        const q1 = (await ev("window.__jv.rects()")).canvas;
        await ev("window.__piano.jam.deck.open(), true"); await delay(200);
        const q2 = (await ev("window.__jv.rects()")).canvas;
        await recOn(false);
        await ev("window.__piano.jam.deck.close(), true");
        row.rec_canvas_delta_px = round(Math.max(d(r0, r1), d(r0, r2)), 2);
        row.rec_from_dock_delta_px = round(Math.max(d(q0, q1), d(q0, q2)), 2);
        if (isFs) {
          await ev("window.__piano.jam.deck.act('show', { cardId: 'lydian-four' })");
          await delay(250);
          row.fullscreen_descendants = await ev(`(() => { const fs = document.fullscreenElement, d = window.__piano.jam.deck;
            return { fs: fs && fs.id, deck: !!fs && fs.contains(d.element), pill: !!fs && fs.contains(d.pill) && !d.pill.hidden, glass: !!fs && fs.contains(document.getElementById('jam-glass')) }; })()`);
          await ev("window.__piano.jam.deck.act('dismiss'), document.exitFullscreen().then(() => true)");
          await delay(250);
        }
        sec.matrix.push(row);
      }
    }
    if (vw === 2560) {
      await ev("window.__piano.jam.deck.open(), true");
      await delay(300);
      await page.shot(dirOf("a8"), `a8-page-2560x1440-${STAMP}.png`);
      await ev("window.__piano.jam.deck.close(), true");
    }
  }
  const M = sec.matrix, find = (vp, fr, fs) => M.find((r) => r.viewport === vp && r.framing === fr && r.fullscreen === fs);
  const a = find("2560x1440", "9:16", false), bf = find("1920x1080", "16:9", true), bw = find("1920x1080", "16:9", false);
  check("a8", "9:16 at 2560 wide: the deck overlays; the canvas rect changes by 0 px", a && a.mode === "overlay" && a.canvas_delta_px === 0, a && { mode: a.mode, delta: a.canvas_delta_px, margin: a.margin });
  check("a8", "16:9 at 1920 wide: the deck docks; canvas width = stage width - 380 +/- 1 px (fullscreen, pad 0)", bf && bf.mode === "dock" && bf.literal_ok && bf.width_ok,
        bf && { mode: bf.mode, canvas: bf.canvas_width, stage: bf.stage.w });
  check("a8", "16:9 at 1920 wide, windowed: docks; canvas width = stage width - 380 - 2 x 14 px pad +/- 1 px", bw && bw.mode === "dock" && bw.literal_ok && bw.width_ok,
        bw && { mode: bw.mode, canvas: bw.canvas_width, stage: bw.stage.w });
  check("a8", "overlay when the side margin >= 392 px, else dock, in 12 of 12 viewport x framing x window combinations; docks never overlap the canvas",
        M.length === 12 && M.every((r) => r.mode === r.expect && (r.expect === "overlay" ? r.canvas_delta_px === 0 : r.width_ok && r.no_overlap)),
        M.map((r) => [r.viewport, r.framing, r.fullscreen, r.margin, r.expect, r.mode, r.canvas_delta_px ?? r.canvas_width]));
  check("a8", "the glass keeps the canvas's exact CSS box with the deck open (12 of 12)", M.every((r) => r.glass_matches_canvas), M.map((r) => r.glass_matches_canvas));
  check("a8", "during REC the canvas rect changes by 0 px on deck open and close (12 of 12, from closed and from docked)",
        M.every((r) => r.rec_canvas_delta_px === 0 && r.rec_from_dock_delta_px === 0), M.map((r) => [r.viewport, r.framing, r.fullscreen, r.rec_canvas_delta_px, r.rec_from_dock_delta_px]));
  const fsRows = M.filter((r) => r.fullscreen);
  check("a8", "fullscreen: deck, pill and glass are descendants of the fullscreen element (6 of 6)",
        fsRows.length === 6 && fsRows.every((r) => r.fullscreen_descendants && r.fullscreen_descendants.fs === "stage" && r.fullscreen_descendants.deck && r.fullscreen_descendants.pill && r.fullscreen_descendants.glass),
        fsRows.map((r) => [r.viewport, r.framing, r.fullscreen_descendants]));
  check("a8", "the toast never intersects the open deck or the closed tab (12 of 12)", M.every((r) => r.toast && !r.toast_hits_deck && !r.toast_hits_tab),
        M.map((r) => [r.viewport, r.framing, r.fullscreen, r.toast, r.toast_hits_deck, r.toast_hits_tab]));

  // ---- a new card while he plays (a held note: not resting)
  await viewport(1920, 1080);
  await loadPiano(page, `page=${pageId}-cards&jam=auto`);
  await ev("document.getElementById('btn-916').click(); window.__piano.jam.deck.open(); [...document.querySelectorAll('#deck .deck-tabbtn')].find((x) => x.dataset.tab === 'all').click(); true");
  await delay(400);
  const probe = `(() => { const list = document.querySelector('#deck .deck-list'); const lr = list.getBoundingClientRect();
    const el = document.elementFromPoint(lr.left + lr.width / 2, lr.top + lr.height / 2); const card = el && el.closest('.deck-card');
    return { scrollTop: list.scrollTop, order: window.__piano.jam.deck.visible(), under: card && card.dataset.id, underTop: card && +card.getBoundingClientRect().top.toFixed(2),
             newPill: !document.querySelector('#deck .deck-newpill').hidden, deferred: window.__piano.jam.deck.stats().deferred }; })()`;
  await ev("(() => { const l = document.querySelector('#deck .deck-list'); l.scrollTop = 320; return l.scrollTop; })()");
  await delay(150);
  await ev("window.__piano.midiMessage([0x90, 79, 80]), true");
  const p0 = await ev(probe);
  const newCard = { api: "arsenal.jam.card/v0", id: `j9-arrives-${STAMP.slice(9)}`, title: "A card that waits for your rest", meaning: "Arrives mid-phrase; waits.",
                    group: "moves", kind: "chord", key: "Eb major", chords: [{ n: "1maj9", beats: 4 }], explanation: "A test card.", why: "The page test needs one.",
                    try: "Nothing to try.", created_by: "claude" };
  const posted = await api("POST", "/api/piano/deck/cards", { card: newCard, by: "claude" });
  await waitFor(() => ev("window.__piano.jam.deck.stats().deferred >= 1"), 5000, "the deck frame waits").catch(() => null);
  await delay(700);
  const p1 = await ev(probe);
  await ev("window.__piano.midiMessage([0x80, 79, 0]), true");
  await waitFor(() => ev("window.__piano.jam.deck.stats().pendingFrames === 0"), 4000, "flushed at his rest").catch(() => null);
  await delay(250);
  const p2 = await ev(probe);
  sec.new_card = { posted: posted.status, before: p0, while_playing: p1, after_rest: { ...p2, order: p2.order.slice(0, 5) } };
  check("a8", "a new card arriving while he plays: card order and scroll offset under the pointer unchanged (0 px) until his next rest",
        posted.status === 200 && JSON.stringify(p0.order) === JSON.stringify(p1.order) && p0.scrollTop === p1.scrollTop && p0.under === p1.under && p0.underTop === p1.underTop && p1.newPill,
        { p0: { scrollTop: p0.scrollTop, under: p0.under, top: p0.underTop }, p1: { scrollTop: p1.scrollTop, under: p1.under, top: p1.underTop, pill: p1.newPill, deferred: p1.deferred } });
  check("a8", "at his rest the waiting card goes in", p2.order.includes(newCard.id) && !p2.newPill, { included: p2.order.includes(newCard.id), pill: p2.newPill });

  // ---- the 8.7 keys on the page: each triggers its action; note-ons change by 0
  await loadPiano(page, `page=${pageId}-keys&jam=auto`);
  await ev("document.getElementById('btn-916').click(); document.activeElement && document.activeElement.blur(); window.__piano.jam.deck.open(); [...document.querySelectorAll('#deck .deck-tabbtn')].find((x) => x.dataset.tab === 'moves').click(); window.__piano.jam.deck.close(); true");
  const st = () => ev(`(() => { const p = window.__piano, d = p.jam.deck.stats(), t = p.jam.transport.stats();
    return { noteOns: p.stats().noteOns, open: d.open, selected: d.selected, show: d.show, keys: d.keys, actions: d.actions, calls: d.transport,
             tstate: p.jam.transport.state().state, ghosts: p.jam.stats().ghosts.target.length, runs: t.runs.map((r) => r.mode + ':' + r.state).join(','),
             key: (document.querySelector('#deck .deck-card.selected .card-keybpm') || {}).textContent || null, greyed: !!document.querySelector('#deck .deck-greyed') }; })()`);
  const keyRows = [];
  const press = async (label, code, o, expect) => {
    const b = await st();
    await page.key(code, o);
    await delay((o && o.wait) || 700);
    const aft = await st();
    const ok = !!expect(b, aft);
    keyRows.push({ label, code, shift: !!(o && o.shift), ok, noteOns_delta: aft.noteOns - b.noteOns, calls: aft.calls, tstate: aft.tstate });
  };
  const inc = (b, a, bag, k) => (a[bag][k] || 0) > (b[bag][k] || 0);
  await press("A opens the deck", "KeyA", {}, (b, a) => !b.open && a.open);
  await press("down selects the next card", "ArrowDown", {}, (b, a) => a.selected && a.selected !== b.selected);
  await press("down again", "ArrowDown", {}, (b, a) => a.selected !== b.selected);
  await press("up selects the previous card", "ArrowUp", {}, (b, a) => a.selected && a.selected !== b.selected);
  await press("Enter plays the selected card", "Enter", { wait: 1200 }, (b, a) => inc(b, a, "calls", "start"));
  await press("K shows its ghosts", "KeyK", {}, (b, a) => !b.show && a.show && a.ghosts > 0);
  await press("K hides them", "KeyK", {}, (b, a) => b.show && !a.show);
  await press("\\ starts a Loop", "Backslash", { wait: 1500 }, (b, a) => inc(b, a, "calls", "start") && /loop:running/.test(a.runs));
  await press("\\ stops that Loop", "Backslash", { wait: 1200 }, (b, a) => inc(b, a, "calls", "stop"));
  await press("' starts a Try", "Quote", { wait: 1500 }, (b, a) => inc(b, a, "calls", "start") && /try:running/.test(a.runs));
  await press("] raises the tempo 4 bpm on the running run", "BracketRight", { wait: 900 }, (b, a) => inc(b, a, "calls", "control:tempo"));
  await press("[ lowers it 4 bpm", "BracketLeft", { wait: 900 }, (b, a) => inc(b, a, "calls", "control:tempo"));
  await press("Esc stops Claude", "Escape", { wait: 1000 }, (b, a) => inc(b, a, "calls", "stop") && !/running/.test(a.tstate));
  await press("= transposes the selected card up a half step", "Equal", {}, (b, a) => inc(b, a, "keys", "transpose-up"));
  await press("- transposes it back down", "Minus", {}, (b, a) => inc(b, a, "keys", "transpose-down"));
  await press("Backspace stops Claude", "Backspace", {}, (b, a) => inc(b, a, "keys", "stop"));
  await ev("window.__piano.jam.deck.act('open', { cardId: 'lydian-four' }), true");
  await delay(500);
  await press("Shift+Enter: Hear me (its synthetic moment is not in this log, so the button greys)", "Enter", { shift: true, wait: 1000 }, (b, a) => inc(b, a, "actions", "hear"));
  await ev("window.__piano.jam.deck.showState({ state: 'pending', run: null, mode: null, card: null, pending: [], knock: { run: 'j9-knock', mode: 'loop', card: { id: 'lydian-four', title: 'The Lydian 4 chord' }, at_epoch_ms: Date.now() }, expired: [] }), true");
  await press("Enter takes a knock when one shows", "Enter", {}, (b, a) => inc(b, a, "actions", "knock-take"));
  await ev("window.__piano.jam.deck.showState(window.__piano.jam.transport.state()), true");
  sec.keys = keyRows;
  check("a8", "the 8.7 shortcut keys on the page (16 codes, plus Shift+Enter and Enter on a knock): each triggers its action; stats().noteOns changes by 0",
        keyRows.every((r) => r.ok && r.noteOns_delta === 0), keyRows.map((r) => [r.label, r.ok, r.noteOns_delta]));
  const rep0 = await st();
  await page.key("KeyA", { repeat: true });
  await delay(250);
  const rep1 = await st();
  check("a8", "e.repeat never re-triggers an action", rep0.open === rep1.open && rep0.noteOns === rep1.noteOns, { before: rep0.open, after: rep1.open });
  await ev("window.__piano.jam.deck.close(); document.activeElement && document.activeElement.blur(); true");
  let played = 0;
  const missed = [];
  for (const code of KEYMAP_CODES) {
    const n0 = await ev("window.__piano.stats().noteOns");
    await page.key(code);
    const n1 = await ev("window.__piano.stats().noteOns");
    if (n1 === n0 + 1) played++; else missed.push(code);
  }
  sec.keymap = { codes: KEYMAP_CODES.length, played, missed };
  check("a8", `the KEYMAP keys still play (${played} of ${KEYMAP_CODES.length}; the spec counts 32)`, played === KEYMAP_CODES.length, sec.keymap);
  await page.ws.send("Input.dispatchKeyEvent", { type: "keyDown", code: "Space", key: " ", windowsVirtualKeyCode: 32 });
  const sus1 = await ev("window.__piano.stats().pedal");
  await page.ws.send("Input.dispatchKeyEvent", { type: "keyUp", code: "Space", key: " ", windowsVirtualKeyCode: 32 });
  const sus2 = await ev("window.__piano.stats().pedal");
  check("a8", "Space still sustains (down: on, up: off)", sus1 === true && sus2 === false, { down: sus1, up: sus2 });
  await page.close();
}

// ----------------------------------------------------------------------------------------------------------- A9
// 6 white and 6 black keys each: 9:16 inside the follow camera's 16 white keys around its start, 16:9 across the keyboard
const A9_KEYS = { "9:16": [60, 62, 64, 65, 67, 69, 58, 61, 63, 66, 68, 70], "16:9": [36, 48, 57, 64, 72, 84, 37, 49, 58, 66, 75, 82] };
// summed |dRGB| a stage pixel must change by, between the frame with and without the rim frames, to count as the rim (the
// diff is the rim frames alone; this only keeps render noise out)
const A9_RIM_DIFF = 24;
function rimWorld(g) {  // the glass's rim in world units on the key top: inset 6% of the key width, corner radius 12%
  const inset = RIM.inset * g.w, r = RIM.radius * g.w;
  const x0 = g.x - g.w / 2 + inset, x1 = g.x + g.w / 2 - inset, z0 = g.back + inset, z1 = g.back + g.len - inset;
  const pts = [];
  const arc = (cx, cz, from) => { for (let k = 0; k <= 16; k++) { const a = from + (k / 16) * (Math.PI / 2); pts.push([cx + Math.cos(a) * r, g.top, cz + Math.sin(a) * r]); } };
  arc(x1 - r, z0 + r, -Math.PI / 2);
  arc(x1 - r, z1 - r, 0);
  arc(x0 + r, z1 - r, Math.PI / 2);
  arc(x0 + r, z0 + r, Math.PI);
  return pts;
}
async function a9() {
  const sec = report.sections.a9 = { rows: [] };
  const page = await openTab("a9");
  const ev = page.ev;
  for (const dpr of [1, 1.5]) {
    await page.ws.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: dpr, mobile: false });
    for (const framing of ["9:16", "16:9"]) {
      await loadPiano(page, `page=p-jv-a9-${dpr}-${framing.replace(":", "")}&jam=glass`);
      await ev(`document.getElementById(${JSON.stringify(framing === "9:16" ? "btn-916" : "btn-169")}).click(); true`);
      await delay(400);
      const cssW = await ev("window.__piano.jam.stats().glassBox.width");
      const s = cssW / (framing === "9:16" ? 1080 : 1920);  // CSS px per framing px
      // ---- still: glass rim (pixels) against the projected rim, and against the stage ghost mesh (a snapshot diff)
      await ev("window.__piano.jam.clock.hold(); true");
      for (let i = 0; i < 90; i++) await ev("window.__piano.jam.clock.frame(1 / 60), true");  // the glass view settles
      for (const m of A9_KEYS[framing]) {
        const geo = await ev(`window.__piano.jam.keyGeometry(${m})`);
        // glass view: ghost the key, draw one frame (the glass draws after the camera moves), read the rim back
        const g1 = await ev(`(() => { const J = window.__piano.jam; J.ghost({ target: [${m}] }); J.clock.frame(1 / 60);
          const q = J.keyTop(${m}); const xs = q.map((p) => p[0]), ys = q.map((p) => p[1]);
          const box = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
          return { quad: q, box, glass: window.__jv.glassCentroid(box), rim: J.project(${JSON.stringify(rimWorld(geo))}),
                   centre: J.project([[${geo.x}, ${geo.top}, ${geo.back + geo.len / 2}]])[0] }; })()`);
        const rimC = outlineCentroid(g1.rim);
        const inside = g1.box[0] >= 0 && g1.box[1] >= 0 && g1.box[2] <= cssW;
        // stage view at the same camera: the ghost mesh without and with the ghost (frames at dt 0 do not move anything)
        const fx0 = Math.max(0, Math.floor(g1.box[0] / s) - 12), fy0 = Math.max(0, Math.floor(g1.box[1] / s) - 12);
        const fw = Math.ceil((g1.box[2] - g1.box[0]) / s) + 24, fh = Math.ceil((g1.box[3] - g1.box[1]) / s) + 24;
        // The stage's ghost mesh, alone: the same ghosted frame (camera, fill and tint identical, dt 0) with its rim frames hidden
        // and shown, so the diff is the rim frames' own pixels. On the stage the black keys hide part of a white key's rim (their
        // tops stand 0.52 u higher, so from the camera they cover the white key up to 1.3-1.7 u in front of them), while the glass
        // draws its whole rim over them. So the glass's rim pixels count only where the stage's rim shows (within a band's width
        // of it): both centroids are taken over the same visible stretch of rim.
        const mesh = await ev(`(() => { const J = window.__piano.jam; J.setView('auto');
          for (let i = 0; i < 40; i++) { J.ghost({ target: [] }); J.clock.frame(1 / 60); }
          J.ghost({ target: [${m}] });
          J.ghostFrames(false); const a = J.region({ x: ${fx0}, y: ${fy0}, w: ${fw}, h: ${fh} });
          J.ghostFrames(true); const b = J.region({ x: ${fx0}, y: ${fy0}, w: ${fw}, h: ${fh} });
          J.glass.draw({ ghosts: { target: [${m}] }, alpha: 1 });
          const c = document.getElementById('jam-glass'), dpr = c.width / parseFloat(c.style.width);
          const gx0 = Math.max(0, Math.floor(${g1.box[0] - 8} * dpr)), gy0 = Math.max(0, Math.floor(${g1.box[1] - 8} * dpr));
          const gx1 = Math.min(c.width, Math.ceil(${g1.box[2] + 8} * dpr)), gy1 = Math.min(c.height, Math.ceil(${g1.box[3] + 8} * dpr));
          const img = c.getContext('2d').getImageData(gx0, gy0, gx1 - gx0, gy1 - gy0);
          const alpha = new Uint8Array(img.width * img.height);
          for (let i = 0; i < alpha.length; i++) alpha[i] = img.data[i * 4 + 3];
          let bin = ''; for (let i = 0; i < alpha.length; i += 0x8000) bin += String.fromCharCode.apply(null, alpha.subarray(i, i + 0x8000));
          const rim = J.project(${JSON.stringify(rimWorld(geo))});
          J.ghost({ target: [] }); J.setView('glass'); for (let i = 0; i < 40; i++) J.clock.frame(1 / 60);
          return { a: a.rgba, b: b.rgba, rim, glass: { x0: gx0, y0: gy0, w: img.width, h: img.height, dpr, alpha: btoa(bin) } }; })()`);
        const A = Buffer.from(mesh.a, "base64"), B = Buffer.from(mesh.b, "base64");
        const shown = new Uint8Array(fw * fh);
        let sx = 0, sy = 0, sw = 0;
        for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
          const k = (y * fw + x) * 4;
          const diff = Math.abs(A[k] - B[k]) + Math.abs(A[k + 1] - B[k + 1]) + Math.abs(A[k + 2] - B[k + 2]);
          if (diff < A9_RIM_DIFF) continue;  // the rim frame's pixels (and its soft edge), not render noise
          shown[y * fw + x] = 1;
          sx += (fx0 + x + 0.5) * diff; sy += (fy0 + y + 0.5) * diff; sw += diff;
        }
        const meshC = sw ? [sx / sw * s, sy / sw * s] : null;  // (diagnostic) the stage rim's area centroid, over what shows
        // Along the rim, point by point (every 0.5 CSS px of its projected outline): where the stage shows its rim band there,
        // the band's local centre (its pixels within half a band of the point) and the glass stroke's local centre (its pixels
        // within 3 CSS px). The two centroids are the means of those local centres over the same visible points, so neither the
        // band's width against the glass's thin stroke nor the stretch the black keys hide weighs in.
        const pxPerUnit = (g1.box[2] - g1.box[0]) / s / geo.w;
        const reach = Math.max(2, Math.ceil(0.1 * geo.w * pxPerUnit));  // framing px
        const G = Buffer.from(mesh.glass.alpha, "base64"), gd = mesh.glass.dpr;
        const samples = [];
        for (let i = 0; i < mesh.rim.length; i++) {
          const p = mesh.rim[i], q = mesh.rim[(i + 1) % mesh.rim.length];
          const n = Math.max(1, Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / 0.5));
          for (let k = 0; k < n; k++) samples.push([p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n]);
        }
        let ssx = 0, ssy = 0, gsx = 0, gsy = 0, nvis = 0;
        for (const p of samples) {
          const cfx = Math.round(p[0] / s - fx0), cfy = Math.round(p[1] / s - fy0);
          let wx = 0, wy = 0, ww = 0;
          for (let dy = -reach; dy <= reach; dy++) for (let dx = -reach; dx <= reach; dx++) {
            const x = cfx + dx, y = cfy + dy;
            if (dx * dx + dy * dy > reach * reach || x < 0 || y < 0 || x >= fw || y >= fh || !shown[y * fw + x]) continue;
            wx += fx0 + x + 0.5; wy += fy0 + y + 0.5; ww++;
          }
          if (ww < 3) continue;  // the stage shows no rim at this point (hidden behind a black key)
          let gx = 0, gy = 0, gw = 0;
          const gcx = Math.round(p[0] * gd - mesh.glass.x0), gcy = Math.round(p[1] * gd - mesh.glass.y0), gr = Math.ceil(3 * gd);
          for (let dy = -gr; dy <= gr; dy++) for (let dx = -gr; dx <= gr; dx++) {
            const x = gcx + dx, y = gcy + dy;
            if (x < 0 || y < 0 || x >= mesh.glass.w || y >= mesh.glass.h) continue;
            const al = G[y * mesh.glass.w + x];
            if (al < 64) continue;
            gx += (mesh.glass.x0 + x + 0.5) / gd * al; gy += (mesh.glass.y0 + y + 0.5) / gd * al; gw += al;
          }
          if (!gw) continue;
          nvis++;
          ssx += wx / ww * s; ssy += wy / ww * s; gsx += gx / gw; gsy += gy / gw;
        }
        const visStage = nvis ? [ssx / nvis, ssy / nvis] : null;
        mesh.glass = { c: nvis ? [gsx / nvis, gsy / nvis] : null, pixels_counted: nvis, pixels_all: samples.length };
        const rimC2 = outlineCentroid(mesh.rim);
        const dist = (p, q) => (p && q ? round(Math.hypot(p[0] - q[0], p[1] - q[1])) : null);
        // d_glass_rim3d: against the key top's rim projected from 3D (like for like); d_glass_centre3d: against the projected
        // centre point of the key top (the literal reading; a perspective outline's centroid is not its centre's projection)
        sec.rows.push({ dpr, framing, pan: false, midi: m, black: geo.black, inside, pixels: g1.glass && g1.glass.pixels,
                        d_glass_rim3d: dist(g1.glass && g1.glass.c, rimC), d_glass_centre3d: dist(g1.glass && g1.glass.c, g1.centre),
                        d_glass_mesh: dist(mesh.glass && mesh.glass.c, visStage), d_mesh_rim3d: dist(meshC, rimC2),
                        mesh_debug: { stage_px: shown.reduce((a, v) => a + v, 0), reach, visible_points: mesh.glass.pixels_counted, rim_points: mesh.glass.pixels_all,
                                      stage_visible_c: visStage && visStage.map((v) => round(v)), stage_area_c: meshC && meshC.map((v) => round(v)),
                                      glass_c: mesh.glass.c && mesh.glass.c.map((v) => round(v)),
                                      glass_view_c: g1.glass && g1.glass.c && g1.glass.c.map((v) => round(v)), box: g1.box.map((v) => round(v, 1)), s: round(s, 4) } });
      }
      // ---- a moving camera: Daniel's notes pull the follow camera (9:16); each frame's glass rim against that frame's projection
      await ev("window.__piano.jam.setView('glass'); window.__piano.jam.ghost({ target: [] }); true");
      const target = framing === "9:16" ? [67, 68] : [57, 58];  // keys that stay in view while the camera follows his notes
      await ev(`window.__piano.midiMessage([0x90, ${framing === "9:16" ? 76 : 84}, 90]); window.__piano.midiMessage([0x90, ${framing === "9:16" ? 79 : 86}, 90]); true`);
      for (let f = 0; f < 24; f++) {
        const m = target[f % 2];
        const geo = await ev(`window.__piano.jam.keyGeometry(${m})`);
        const r = await ev(`(() => { const J = window.__piano.jam; J.ghost({ target: [${m}] }); const before = window.__piano.camHints().x; J.clock.frame(1 / 30);
          const q = J.keyTop(${m}); const xs = q.map((p) => p[0]), ys = q.map((p) => p[1]);
          const box = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
          return { cam: [before, window.__piano.camHints().x], box, glass: window.__jv.glassCentroid(box), rim: J.project(${JSON.stringify(rimWorld(geo))}) }; })()`);
        const rimC = outlineCentroid(r.rim);
        sec.rows.push({ dpr, framing, pan: true, frame: f, midi: m, black: geo.black, cam_moved: round(r.cam[1] - r.cam[0], 4), inside: r.box[0] >= 0 && r.box[2] <= cssW,
                        pixels: r.glass && r.glass.pixels, d_glass_rim3d: r.glass && r.glass.c ? round(Math.hypot(r.glass.c[0] - rimC[0], r.glass.c[1] - rimC[1])) : null });
      }
      await ev(`window.__piano.midiMessage([0x80, ${framing === "9:16" ? 76 : 84}, 0]); window.__piano.midiMessage([0x80, ${framing === "9:16" ? 79 : 86}, 0]); window.__piano.jam.ghost({ target: [] }); window.__piano.jam.clock.release(); true`);
      if (dpr === 1) {
        await ev("(() => { const J = window.__piano.jam; J.ghost({ target: [60, 64, 67], incoming: [62], hold: [67] }); return true; })()");
        await delay(300);
        await page.shot(dirOf("a9"), `a9-glass-${framing.replace(":", "x")}-dpr1-${STAMP}.png`);
        await ev("window.__piano.jam.ghost({ target: [] }), true");
      }
    }
  }
  const R = sec.rows.filter((r) => r.inside);
  const still = R.filter((r) => !r.pan), pan = R.filter((r) => r.pan);
  const worst = (rows, k) => round(Math.max(...rows.map((r) => r[k] ?? Infinity)));
  check("a9", `every glass rim centroid within 1.5 CSS px of the projected 3D key-top rim (still: ${still.length} ghosts, 12 keys x 2 framings x DPR 1 and 1.5)`,
        still.length >= 44 && still.every((r) => r.d_glass_rim3d !== null && r.d_glass_rim3d <= 1.5),
        { worst: worst(still, "d_glass_rim3d"), n: still.length, literal_centre_point_worst: worst(still, "d_glass_centre3d"),
          literal_centre_point_within_1_5: still.filter((r) => r.d_glass_centre3d !== null && r.d_glass_centre3d <= 1.5).length });
  check("a9", `during a moving camera: each frame's glass rim within 1.5 CSS px of that frame's projection (${pan.length} frames)`,
        pan.length >= 40 && pan.every((r) => r.d_glass_rim3d !== null && r.d_glass_rim3d <= 1.5) && pan.some((r) => Math.abs(r.cam_moved) > 0.001),
        { worst: worst(pan, "d_glass_rim3d"), n: pan.length, camera_moved_frames: pan.filter((r) => Math.abs(r.cam_moved) > 0.001).length });
  check("a9", "every glass rim centroid within 1.5 px of the stage ghost mesh in a snapshot compare (still)",
        still.every((r) => r.d_glass_mesh !== null && r.d_glass_mesh <= 1.5), { worst: worst(still, "d_glass_mesh"), worst_mesh_vs_rim3d: worst(still, "d_mesh_rim3d"), n: still.length });
  await page.close();
}

// ---------------------------------------------------------------------------------------------------------- A10
function startProxy() {
  const sse = new Set();
  let cut = false;
  const srv = http.createServer((req, res) => {
    const isStream = req.url.startsWith("/api/piano/cues") && !req.url.startsWith("/api/piano/cues/status");
    if (cut && isStream) { res.writeHead(503, { "Content-Type": "text/plain" }); res.end("cut"); return; }
    const headers = { ...req.headers, host: `127.0.0.1:${PORT}` };
    if (headers.origin) headers.origin = APP;
    if (headers.referer) headers.referer = headers.referer.replace(`127.0.0.1:${PROXY_PORT}`, `127.0.0.1:${PORT}`);
    const up = http.request({ host: "127.0.0.1", port: Number(PORT), path: req.url, method: req.method, headers }, (ur) => {
      res.writeHead(ur.statusCode, ur.headers);
      ur.pipe(res);
      if (isStream) { sse.add(res); res.on("close", () => sse.delete(res)); }
    });
    up.on("error", () => { try { res.writeHead(502); res.end(); } catch { /* sent */ } });
    req.pipe(up);
  });
  srv.listen(PROXY_PORT, "127.0.0.1");
  return {
    srv,
    cut() { cut = true; for (const r of sse) r.destroy(); return sse.size; },
    heal() { cut = false; },
    close() { for (const r of sse) r.destroy(); srv.close(); },
  };
}
async function a10() {
  const sec = report.sections.a10 = {};
  const bar = (bpm) => 4 * 60000 / bpm;
  // ---- two tabs, one run
  const A = await openTab("a10-A"), B = await openTab("a10-B");
  await loadPiano(A, `page=p-jv-a10-A-${STAMP.replace("-", "")}&jam=auto`);
  await loadPiano(B, `page=p-jv-a10-B-${STAMP.replace("-", "")}&jam=auto`);
  for (const p of [A, B]) await p.ev("window.__piano.jam.record(true)");
  sec.claim_A = await A.ev("window.__piano.jam.transport.claimOwner(true).then((r) => r && r.owner && r.owner.page_id)");  // Daniel used tab A last
  await delay(300);
  const start = await pianocue("loop", "start", "lydian-four", "--now", "--bpm", "90");
  const runId = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(start.out) || [])[1] || null;
  await delay(bar(90) * 5);
  const inputWall = Date.now();
  await B.ev("window.__piano.midiMessage([0x90, 84, 60]); setTimeout(() => window.__piano.midiMessage([0x80, 84, 0]), 120); true");
  await delay(bar(90) * 5);
  await pianocue("loop", "stop", "--now");
  await delay(800);
  const read = (p) => p.ev(`(() => { const x = window.__piano.jam; return { page: x.pageId, strikes: (x.strikes || []).filter((s) => typeof s.cue === 'string' && s.cue.startsWith('jam:${runId}:')).map((s) => ({ wall: performance.timeOrigin + s.t, m: s.m, cue: s.cue, sound: s.sound })),
    voice: window.__piano.cues.voice.stats(), transport: { notes: x.transport.stats().notes, owner: x.transport.stats().owner } }; })()`);
  const ra = await read(A), rb = await read(B);
  const barOf = (cue) => +cue.split(":").pop();
  const soundA = ra.strikes.filter((s) => s.sound), soundB = rb.strikes.filter((s) => s.sound);
  const planned = Math.max(ra.strikes.length, rb.strikes.length);
  const stepKey = (s) => `${barOf(s.cue)}:${s.m}:${Math.round(s.wall / 5)}`;
  const aKeys = new Set(soundA.map(stepKey));
  const doubled = soundB.filter((s) => aKeys.has(stepKey(s)) || aKeys.has(`${barOf(s.cue)}:${s.m}:${Math.round(s.wall / 5) - 1}`) || aKeys.has(`${barOf(s.cue)}:${s.m}:${Math.round(s.wall / 5) + 1}`)).length;
  const firstB = soundB.find((s) => s.wall >= inputWall);
  const merged = [...soundA, ...soundB].map((s) => s.wall).sort((x, y) => x - y);
  let gap = 0;
  for (let i = 1; i < merged.length; i++) if (merged[i] > inputWall - bar(90) && merged[i - 1] < inputWall + 3 * bar(90)) gap = Math.max(gap, merged[i] - merged[i - 1]);
  sec.two_tabs = { run: runId, planned_strikes: planned, sounded_A: soundA.length, sounded_B: soundB.length, doubled, strikes_A: ra.strikes.length, strikes_B: rb.strikes.length,
                   voice_A: { strikes: ra.voice.strikes, yielded: ra.voice.yielded }, voice_B: { strikes: rb.voice.strikes, yielded: rb.voice.yielded },
                   owner_moved_after_ms: firstB ? round(firstB.wall - inputWall, 1) : null, longest_gap_ms: round(gap, 1), bar_ms: round(bar(90), 1) };
  check("a10", "two listening tabs, one run: total sounded strikes across tabs = one tab's planned strikes",
        runId && planned > 0 && soundA.length + soundB.length === planned, sec.two_tabs);
  // the move itself: tab A (which Daniel used last) sounds before B's input, B sounds from within a bar after it, A not after that
  const aBefore = soundA.filter((s) => s.wall < inputWall).length, bBefore = soundB.filter((s) => s.wall < inputWall).length;
  const aLate = soundA.filter((s) => s.wall > inputWall + bar(90)).length;
  Object.assign(sec.two_tabs, { sounded_A_before_input: aBefore, sounded_B_before_input: bBefore, sounded_A_after_1_bar: aLate });
  check("a10", "the owner moves to tab B on its input within 1 bar; 0 doubled strikes; no silent gap longer than 1 bar",
        aBefore > 0 && bBefore === 0 && aLate === 0 && firstB && firstB.wall - inputWall <= bar(90) && doubled === 0 && gap <= bar(90) + 50, sec.two_tabs);
  await A.close();
  await B.close();

  // ---- the stream cut at a proxy
  proxy = startProxy();
  const C = await openTab("a10-C");
  await loadPiano(C, `page=p-jv-a10-C-${STAMP.replace("-", "")}&jam=auto`, { origin: `http://127.0.0.1:${PROXY_PORT}` });
  await C.ev("window.__piano.jam.transport.claimOwner(true).then(() => true)");
  const s2 = await pianocue("loop", "start", "lydian-four", "--now", "--bpm", "90");
  const run2 = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(s2.out) || [])[1] || null;
  await delay(bar(90) * 3);
  const cutWall = Date.now();
  const cutStreams = proxy.cut();
  let stopped = null;
  try {
    stopped = await waitFor(() => C.ev(`(() => { const r = window.__piano.jam.transport.stats().runs.find((x) => x.run === ${JSON.stringify(run2)}); return r && r.stop && r.stop.reason === 'stream-lost' ? r.stop : null; })()`), 20000, "the page to stop");
  } catch (e) { sec.cut_error = e.message; }
  await delay(1500);
  const doc2 = run2 ? await getJSON(`/api/piano/jam/runs/${run2}`) : null;
  const ackLost = doc2 && doc2.events.find((e) => e.kind === "ack" && e.stopped === "stream-lost");
  proxy.heal();
  sec.stream_cut = { run: run2, streams_cut: cutStreams, stop: stopped, stop_after_ms: stopped ? round(stopped.epoch - cutWall, 1) : null,
                     two_bars_ms: round(2 * bar(90), 1), beat_ms: round(bar(90) / 4, 1), ack_stream_lost: !!ackLost, server_reason: doc2 && doc2.run.stop_reason };
  check("a10", "stream cut at a proxy: the page stops after 2 bars +/- 1 beat; the ack says stream-lost",
        stopped && Math.abs(stopped.epoch - cutWall - 2 * bar(90)) <= bar(90) / 4 && !!ackLost, sec.stream_cut);
  await C.close();
  proxy.close();
  proxy = null;

  // ---- a server restart
  const D = await openTab("a10-D");
  await loadPiano(D, `page=p-jv-a10-D-${STAMP.replace("-", "")}&jam=auto`);
  const s3 = await pianocue("loop", "start", "lydian-four", "--now");
  const run3 = (/run (\d{8}-\d{6}-[0-9a-f]{8})/.exec(s3.out) || [])[1] || null;
  await delay(4000);
  await stopServer();
  await startServer();
  const status = await pianocue("jam", "status", "--json");
  let st = null;
  try { st = JSON.parse(status.out); } catch { /* text */ }
  const doc3 = run3 ? await getJSON(`/api/piano/jam/runs/${run3}`) : null;
  await delay(5000);
  const pageRun = await D.ev(`(() => { const r = window.__piano.jam.transport.stats().runs.find((x) => x.run === ${JSON.stringify(run3)}); return r ? { state: r.state, stop: r.stop, live: r.live } : null; })()`).catch((e) => ({ error: e.message }));
  const stRun = st ? (st.jam && "run" in st.jam ? st.jam.run : st.run) : "unparsed";  // jam status --json answers {jam: {run, ...}, ...}
  sec.restart = { run: run3, status: brief(status), jam_status_run: stRun, closed: doc3 && doc3.run.closed, reason: doc3 && doc3.run.stop_reason,
                  approx: doc3 && doc3.run.approx, page: pageRun };
  check("a10", "server restart: the run closes with server-restart; jam status shows no run",
        doc3 && doc3.run.closed && doc3.run.stop_reason === "server-restart" && stRun === null, sec.restart);
  await D.close();
}

// ----------------------------------------------------------------------------------------------------------- A5
const A5_DECODE = `
import json, sys
import av, numpy as np
def frames(path):  # one decoded frame at a time (300 full frames of two files would not fit in memory)
    c = av.open(path)
    try:
        for f in c.decode(video=0):
            yield f.to_ndarray(format="rgb24")
    finally:
        c.close()
def audio(path):
    c = av.open(path)
    if not c.streams.audio:
        c.close(); return None, None
    chunks, sr = [], None
    for f in c.decode(audio=0):
        a = f.to_ndarray().astype(np.float64)
        a = a.mean(axis=0) if a.ndim == 2 and a.shape[0] <= 8 else a.reshape(-1)
        chunks.append(a); sr = f.sample_rate
    c.close()
    return np.concatenate(chunks), sr
def lab(rgb):
    x = rgb.astype(np.float64) / 255.0
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = x @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
MOON = lab(np.array([[[200, 220, 255]]], dtype=np.uint8))[0, 0]
def moon(fr):
    sub = fr[::2, ::2]
    return int((np.linalg.norm(lab(sub) - MOON, axis=-1) <= 6).sum()) * 4
take, control, TONE = sys.argv[1], sys.argv[2], float(sys.argv[3])
mae, maxch, moon_take, moon_ctrl = [], [], [], []
count = {"take": 0, "control": 0}
gt, gc = frames(take), frames(control)
while True:
    a, b = next(gt, None), next(gc, None)
    count["take"] += a is not None
    count["control"] += b is not None
    if a is None or b is None:
        rest = gt if a is not None else gc if b is not None else iter(())
        for _ in rest:
            count["take" if a is not None else "control"] += 1
        break
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    mae.append(float(d.mean()))
    maxch.append(float(d.reshape(-1, 3).mean(axis=0).max()))
    if (len(mae) - 1) % 10 == 0:
        moon_take.append(moon(a))
        moon_ctrl.append(moon(b))
n = len(mae)
at_, sr = audio(take)
ac, _ = audio(control)
res = None
if at_ is not None and ac is not None:
    m = min(len(at_), len(ac))
    w = min(m, sr)
    best, lag = -1e18, 0
    for L in range(-int(0.05 * sr), int(0.05 * sr) + 1, 1):
        a = at_[max(0, L):max(0, L) + w - abs(L)]
        b = ac[max(0, -L):max(0, -L) + w - abs(L)]
        v = float(np.dot(a, b))
        if v > best: best, lag = v, L
    a = at_[max(0, lag):]; b = ac[max(0, -lag):]
    k = min(len(a), len(b))
    r = a[:k] - b[:k]
    rms = lambda x: float(np.sqrt(np.mean(x * x))) if len(x) else 0.0
    def non_tone_db(x):  # the share of the energy (30 Hz-5 kHz) outside the test tone, in dB: Claude's chords would raise it
        seg = x[:min(len(x), sr * 4)]
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        freqs = np.fft.rfftfreq(len(seg), 1 / sr)
        tot = spec[(freqs >= 30) & (freqs <= 5000)].sum()
        tone = spec[(freqs >= TONE - 40) & (freqs <= TONE + 40)].sum()
        return float(10 * np.log10(max(tot - tone, 1e-30) / (tot + 1e-30)))
    res = {"sample_rate": sr, "lag_samples": lag, "take_dbfs": 20 * np.log10(rms(a[:k]) + 1e-12), "residual_dbfs": 20 * np.log10(rms(r) + 1e-12),
           "non_tone_db_take": non_tone_db(at_), "non_tone_db_control": non_tone_db(ac)}
print(json.dumps({"frames": {"take": count["take"], "control": count["control"], "compared": n}, "mae_max": max(mae) if mae else None,
                  "mae_zero_frames": sum(1 for x in mae if x == 0.0), "per_channel_mae_max": max(maxch) if maxch else None,
                  "mae_first": mae[:5], "moon_take_minus_control_max": max([t - c for t, c in zip(moon_take, moon_ctrl)] or [0]),
                  "audio": res}))
`;
async function a5() {
  const sec = report.sections.a5 = { framing: opt.framing };
  const FR = opt.framing === "9:16" ? "btn-916" : "btn-169";
  const PRE = 720, REC = 300, AFTER = 30, HASH_FROM = 240;  // frames at 60 fps of the held clock
  // In and around REC one frame is handed per RAF_MS of display frames, from inside a requestAnimationFrame callback. At 4 ms
  // apart the recorder kept as few as 124 of 300 frames, and even 40 ms apart on a timer it dropped up to 32. The encoder's
  // rate control also reads each frame's timestamp, so both takes must hand theirs the same number of display frames apart.
  const RAF_MS = 99;
  // The test input: 1500 Hz is 32 samples a period at 48 kHz, which divides the 128-sample render quantum, the 10 ms chunks
  // of a MediaStream track and the 1024-sample AAC frame. Every take's recording then starts on the same phase of the tone,
  // so a take and its control can null to the sample (a 440 Hz tone started at a random phase left about -52 dBFS).
  const A5_TONE = 1500;
  const events = melody({ count: Math.ceil((PRE + REC + AFTER) / 60 * 1000 / 420), every: 420, len: 330, bar: 2520 });
  const take = async (label, view, claude) => {
    const page = await openTab(`a5-${label}`);
    await loadPiano(page, `page=p-jv-a5-${label}-${STAMP.replace("-", "")}&jam=${view}`);
    await page.ev(`document.getElementById('${FR}').click(); document.getElementById('key-select').value; true`);
    await page.ev(`window.__piano.jam.testInput(${A5_TONE}).label`);
    await delay(6000);  // every fade and settle the page runs in real time before its clock is held (the staff's 2.4 s quiet) is done
    // the held clock starts at the same moment in every take (600 s), so time-driven drawing (the camera's slow sway, the ghost
    // breath) is the same from the first frame on
    await page.ev(`(() => { const J = window.__piano.jam; J.seedSparks(7); J.clock.hold(600);
      window.__jvA5 = { f: 0, i: 0, hashes: [], glass: [], digests: [], gaps: [], sources: null, done: false, upload: null, t0: Date.now() };
      const ev = ${JSON.stringify(events)}, s = window.__jvA5;
      const step = () => {
        const vt = s.f * 1000 / 60;
        while (s.i < ev.length && ev[s.i][0] <= vt) { window.__piano.midiMessage(ev[s.i][1]); s.i++; }
        if (s.f === ${PRE}) { document.getElementById('btn-rec').click(); s.sources = J.stats().recorderSources; }
        if (s.f === ${PRE + REC}) document.getElementById('btn-rec').click();
        const r = J.clock.frame(1 / 60, { hash: s.f >= ${HASH_FROM} });
        if (s.f >= ${HASH_FROM}) { s.hashes.push(r.hash + ':' + r.moon + ':' + r.sum.join(',')); (s.cells ||= []).push(r.cells); }
        // what the canvas draws, as state (the keys, the camera, the light budget, the chip, the pool): where a take and its
        // control part, this says why
        if (s.f >= ${PRE - 2} && s.f < ${PRE + REC}) s.digests.push(J.digest());
        if (s.f >= ${PRE} && s.f < ${PRE + REC} && (s.f - ${PRE}) % 50 === 25) {
          const js = J.stats();
          s.glass.push({ f: s.f, alpha: window.__jv.glassAlpha(), glass: js.glass.keys, onStage: js.onStage, pool: js.pool.visible, poolOpacity: js.pool.opacity });
        }
        s.f++;
        if (s.f >= ${PRE + REC + AFTER}) { s.done = true; return; }
        if (s.f >= ${PRE - 10} && s.f < ${PRE + REC + 10}) {
          const wait = (ts) => {
            if (s.last !== undefined && ts - s.last < ${RAF_MS}) { requestAnimationFrame(wait); return; }
            if (s.last !== undefined && s.f > ${PRE} && s.f <= ${PRE + REC}) s.gaps.push(Math.round(ts - s.last));
            s.last = ts;
            step();
          };
          requestAnimationFrame(wait);
        } else setTimeout(step, 4);
      };
      setTimeout(step, 0);
      return true; })()`);
    const wall0 = Date.now();
    const acts = [];
    if (claude) {
      acts.push(at(wall0, 800, () => pianocue("loop", "start", "lydian-four", "--now", "--bpm", "96")));
      acts.push(at(wall0, 6000, () => pianocue("try", "lydian-four", "--now", "--bpm", "96", "--passes", "40")));
      acts.push(at(wall0, 9000, () => pianocue("card", "play", "held-sus-five", "--now")));
      acts.push(at(wall0, 10000, () => pianocue("card", "show", "lydian-four", "--hold", "0")));
    }
    const cliOut = (await Promise.all(acts)).map(brief);
    await waitFor(() => page.ev("window.__jvA5.done"), 600000, `${label}: the stepped frames`);
    await waitFor(() => page.ev("window.__piano.stats().rec === 'idle' && !!window.__piano.lastUpload"), 60000, `${label}: the upload`);
    const out = await page.ev("(() => { const s = window.__jvA5; return { hashes: s.hashes, cells: s.cells, glass: s.glass, digests: s.digests, gaps: s.gaps, sources: s.sources, upload: window.__piano.lastUpload, recTracks: window.__piano.stats().cue.recTracks, jam: window.__piano.jam.stats().transport.runs.map((r) => r.mode + ':' + r.state) }; })()");
    if (claude) { await pianocue("loop", "stop", "--now"); await pianocue("clear"); }
    await page.ev("window.__piano.jam.clock.release(), true");
    await page.close();
    return { ...out, cli: cliOut, ms: Date.now() - wall0 };
  };
  // The platform's H.264 encoder starts cold in a fresh browser. The first recording of a session lost 13 to 32 frames about
  // a second in (receipts 2026-09-14: the control, recorded first, kept 269, 286 and 288 of 301 frames; every later take kept
  // 301). One short warm-up recording goes first, so the control and the take both meet a warm encoder.
  {
    const page = await openTab("a5-warmup");
    await loadPiano(page, `page=p-jv-a5-warmup-${STAMP.replace("-", "")}&jam=auto`);
    await page.ev(`document.getElementById('${FR}').click(); true`);
    await page.ev(`window.__piano.jam.testInput(${A5_TONE}).label`);
    await page.ev("document.getElementById('btn-rec').click(), true");
    await delay(4000);
    await page.ev("document.getElementById('btn-rec').click(), true");
    await waitFor(() => page.ev("window.__piano.stats().rec === 'idle' && !!window.__piano.lastUpload"), 60000, "the warm-up upload");
    sec.warmup = await page.ev("(() => { const u = window.__piano.lastUpload; return u && { ok: u.ok, frames_requested: u.framesRequested, seconds: u.seconds, mime: u.mime }; })()");
    await page.close();
  }
  const control = await take("control", "auto", false);
  const main = await take("take", "auto", true);
  const glass = await take("glass", "glass", true);
  // the page's own determinism floor: a second control take, with no Claude at all
  const control2 = await take("control2", "auto", false);
  const hashOf = (h) => h.split(":")[0];
  // the differing frames of two hash lists (index from `from`): the first 12, with each channel's sum difference
  // ca, cb: the frames' 16 x 9 grids of R+G+B sums (canvasHash), to say where on the canvas a frame differs
  const differing = (a, b, from, ca = null, cb = null) => {
    const out = [];
    let n = 0;
    a.forEach((h, i) => {
      if (!b[i] || hashOf(h) === hashOf(b[i])) return;
      n++;
      if (out.length < 12) {
        const sa = h.split(":")[2].split(",").map(Number), sb = b[i].split(":")[2].split(",").map(Number);
        const cells = ca && cb && ca[i] && cb[i]
          ? ca[i].map((v, k) => [k, v - cb[i][k]]).filter((x) => x[1] !== 0).map(([k, d]) => ({ col: k % 16, row_from_bottom: Math.floor(k / 16), d }))
          : null;
        out.push({ frame: from + i, d_sum: sa.map((v, k) => v - sb[k]), cells });
      }
    });
    return { n, first: out };
  };
  const recIdx = (i) => i - HASH_FROM;
  const slice = (h, from, to) => h.slice(recIdx(from), recIdx(to));
  const recT = slice(main.hashes, PRE, PRE + REC), recC = slice(control.hashes, PRE, PRE + REC);
  const recSame = recT.filter((h, i) => h === recC[i]).length;
  const moonExtra = recT.map((h, i) => +h.split(":")[1] - +recC[i].split(":")[1]).filter((x) => x > 0).length;
  const afterT = slice(main.hashes, PRE + REC, PRE + REC + AFTER), afterC = slice(control.hashes, PRE + REC, PRE + REC + AFTER);
  const backAt = afterT.findIndex((h, i) => h !== afterC[i]);
  const preG = slice(glass.hashes, HASH_FROM, PRE), preC = slice(control.hashes, HASH_FROM, PRE);
  const glassSame = preG.filter((h, i) => h === preC[i]).length;
  // The drawn state (__piano.jam.digest), frame by frame from the first REC frame (the digests start 2 frames before it):
  // how many frames of a take part from its control, and on the first few, what parts (a key, the camera, the light budget)
  const stateDiff = (a, b) => {
    const first = [];
    let n = 0;
    const same = (x, y) => JSON.stringify(x) === JSON.stringify(y);
    for (let i = 2; i < Math.min(a.length, b.length); i++) {
      const x = a[i], y = b[i], parts = [];
      for (const k of Object.keys(x)) if (k !== "keys" && !same(x[k], y[k])) parts.push({ part: k, take: x[k], control: y[k] });
      for (const m of new Set([...Object.keys(x.keys), ...Object.keys(y.keys)])) {
        if (!same(x.keys[m], y.keys[m])) parts.push({ key: +m, take: x.keys[m] ?? null, control: y.keys[m] ?? null });
      }
      if (!parts.length) continue;
      n++;
      if (first.length < 6) first.push({ frame: PRE + i - 2, parts: parts.slice(0, 8) });
    }
    return { n, of: Math.max(0, Math.min(a.length, b.length) - 2), first };
  };
  const gapsOf = (g) => (g && g.length ? { n: g.length, min: Math.min(...g), max: Math.max(...g) } : null);
  sec.state = { take: stateDiff(main.digests, control.digests), floor: stateDiff(control2.digests, control.digests),
                glass_view: stateDiff(glass.digests, control.digests) };
  sec.handed = { take: gapsOf(main.gaps), control: gapsOf(control.gaps), glass: gapsOf(glass.gaps), control2: gapsOf(control2.gaps) };
  sec.control = { upload: control.upload, sources: control.sources, ms: control.ms };
  sec.take = { upload: main.upload, sources: main.sources, glass_during_rec: main.glass, cli: main.cli, runs: main.jam, ms: main.ms };
  sec.glass_view = { upload: glass.upload, cli: glass.cli, runs: glass.jam };
  sec.drawn = { rec_frames: recT.length, identical: recSame, moonlight_frames_take_over_control: moonExtra, after_rec_first_difference_frame: backAt, glass_view_pre_rec_frames: preG.length, glass_view_identical: glassSame,
                differing_rec: differing(recT, recC, PRE, slice(main.cells, PRE, PRE + REC), slice(control.cells, PRE, PRE + REC)),
                differing_glass_pre_rec: differing(preG, preC, HASH_FROM, slice(glass.cells, HASH_FROM, PRE), slice(control.cells, HASH_FROM, PRE)) };
  const recC2 = slice(control2.hashes, PRE, PRE + REC), preC2 = slice(control2.hashes, HASH_FROM, PRE);
  sec.determinism = { rec_identical: recC2.filter((h, i) => recC[i] && hashOf(h) === hashOf(recC[i])).length, rec_of: recC2.length,
                      pre_rec_identical: preC2.filter((h, i) => preC[i] && hashOf(h) === hashOf(preC[i])).length, pre_rec_of: preC2.length,
                      differing_rec: differing(recC2, recC, PRE), differing_pre_rec: differing(preC2, preC, HASH_FROM) };
  check("a5", "(floor) two control takes with no Claude draw identical frames: the stepped page is deterministic",
        sec.determinism.rec_identical === REC && sec.determinism.pre_rec_identical === preC2.length, sec.determinism);
  let decoded = null;
  if (main.upload && main.upload.ok && control.upload && control.upload.ok) {
    const py = join(STATE, "a5_decode.py");
    writeFileSync(py, A5_DECODE);
    decoded = await new Promise((resolve) => {
      const p = spawn("py", [py, main.upload.json.path, control.upload.json.path, String(A5_TONE)], { cwd: REPO, windowsHide: true });
      let o = "", e = "";
      p.stdout.on("data", (d) => { o += d; });
      p.stderr.on("data", (d) => { e += d; });
      p.on("close", (code) => { try { resolve({ code, ...JSON.parse(o) }); } catch { resolve({ code, error: (e || o).slice(0, 600) }); } });
    });
  }
  sec.decoded = decoded;
  check("a5", `recorded frames: the take's ${REC} drawn frames are pixel-identical to the control take's (MAE 0.0; hashed as handed to the recorder)`,
        recT.length === REC && recSame === REC,
        { identical: recSame, of: recT.length, first_difference: recT.findIndex((h, i) => h !== recC[i]), state_frames_differing: sec.state.take.n,
          state_first: sec.state.take.first.slice(0, 3) });
  // 300 of 300: both files hold every recorded frame (the take's frames compared one for one with the control's)
  check("a5", `recorded video decoded from the recorder's files: per-channel MAE 0.0 against the control take on ${REC} of ${REC} frames`,
        decoded && decoded.per_channel_mae_max === 0 && decoded.frames && decoded.frames.take === decoded.frames.control && decoded.frames.compared >= REC,
        decoded && { frames: decoded.frames, requested: { take: main.upload && main.upload.framesRequested, control: control.upload && control.upload.framesRequested },
                     handed_ms: sec.handed, per_channel_mae_max: decoded.per_channel_mae_max, mae_zero_frames: decoded.mae_zero_frames, mae_first: decoded.mae_first,
                     error: decoded.error });
  check("a5", "moonlight pixels (within delta E 6 of #C8DCFF) present in the take but not in the control: 0",
        moonExtra === 0 && (!decoded || decoded.moon_take_minus_control_max <= 0), { drawn_frames_with_extra: moonExtra, decoded_max: decoded && decoded.moon_take_minus_control_max });
  check("a5", "the recorder's sources have no claude (canvas and the input only)",
        Array.isArray(main.sources) && main.sources.every((s) => s === "canvas" || s === "input") && main.sources.includes("input"), { sources: main.sources, tracks: main.recTracks });
  check("a5", "recorded audio (a test oscillator as the input) nulled against the control: residual <= -90 dBFS",
        decoded && decoded.audio && decoded.audio.residual_dbfs <= -90, decoded && decoded.audio);
  check("a5", "Claude's sound is not in the recorded audio: the take's energy outside the test tone matches the control's (within 3 dB)",
        decoded && decoded.audio && Math.abs(decoded.audio.non_tone_db_take - decoded.audio.non_tone_db_control) <= 3,
        decoded && decoded.audio && { take_db: decoded.audio.non_tone_db_take, control_db: decoded.audio.non_tone_db_control });
  const glassPx = main.glass.filter((g) => !g.onStage);
  check("a5", "the glass during REC: ghost pixels > 0 (Claude's things moved to the glass, not gone)", glassPx.length > 0 && glassPx.some((g) => g.alpha > 0), { samples: main.glass });
  check("a5", "Navi's moonlight floor pool is never drawn during REC in auto (house idea: stage only)",
        main.glass.length > 0 && main.glass.every((g) => g.pool === false && g.poolOpacity === 0), { samples: main.glass.map((g) => [g.f, g.pool, g.poolOpacity]) });
  check("a5", "?jam=glass outside REC: canvas frames equal the control (MAE 0.0)", preG.length > 0 && glassSame === preG.length, { identical: glassSame, of: preG.length, first_difference: preG.findIndex((h, i) => h !== preC[i]) });
  check("a5", "after REC stops in auto, within 300 ms Claude's keys are back on the stage (the frame differs from the control)",
        backAt >= 0 && backAt <= 18, { first_difference_after_rec_frames: backAt, ms: backAt >= 0 ? round(backAt * 1000 / 60, 1) : null });
}

// ---------------------------------------------------------------------------------------------------------- main
const SECTIONS = { a12, a6, a7, a8, a9, a10, a5 };
let exitCode = 0;
try {
  const lockWait = Date.now();
  gpu = await acquireGpuLock({ label: `jam_verify ${ONLY.join(",")}`, yieldToJam: false, maxHoldMs: Math.max(10, 5 * ONLY.length) * 60_000 });
  report.gpu_lock = { waited_s: Math.round((Date.now() - lockWait) / 1000), acquired_at: gpu.owner.acquiredAt, inherited: gpu.inherited };
  await startServer();
  await startChrome();
  if (!ONLY.includes("a12")) {  // the other checks need the seeded deck
    const seed = await pianocue("deck", "seed", "--moments", (() => { const f = join(STATE, "moments-synthetic.json"); writeFileSync(f, JSON.stringify({ api: "arsenal.jam.seed.moments/v0", cards: {} })); return f; })());
    report.seed = brief(seed);
  }
  for (const k of ["a12", "a6", "a7", "a8", "a9", "a10", "a5"]) {
    if (!ONLY.includes(k)) continue;
    const t0 = Date.now();
    try { await SECTIONS[k](); } catch (e) {
      report.errors.push({ section: k, error: String(e.stack || e) });
      check(k, `the ${k} run finished`, false, { error: String(e.message || e) });
    }
    (report.sections[k] ||= {}).seconds = round((Date.now() - t0) / 1000, 1);
    const dir = dirOf(k);
    writeFileSync(join(dir, `${DIRS[k]}-${STAMP}.json`), JSON.stringify({ ...report, sections: { [k]: report.sections[k] }, checks: { [k]: report.checks[k] } }, null, 1));
  }
} catch (e) {
  report.errors.push({ fatal: String(e.stack || e) });
  console.error("FATAL", e);
} finally {
  report.page_files.end = pageFiles();
  report.page_files.changed_during_run = JSON.stringify(report.page_files.start) !== JSON.stringify(report.page_files.end);
  if (report.page_files.changed_during_run) console.log("NOTE a piano page file changed during the run", JSON.stringify(report.page_files));
  const all = Object.values(report.checks).flat();
  report.summary = { passed: all.filter((c) => c.pass).length, failed: all.filter((c) => !c.pass).length, exceptions: report.exceptions.length, errors: report.errors.length };
  report.finished_at = new Date().toISOString();
  const dir = join(opt.out, `jam-verify-${DAY}`);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `jam-verify-${STAMP}.json`), JSON.stringify(report, null, 1));
  try { copyFileSync(fileURLToPath(import.meta.url), join(dir, "jam_verify.mjs")); } catch { /* receipts only */ }
  try { copyFileSync(join(STATE, `server-${PORT}.log`), join(dir, `server-${PORT}-${STAMP}.log`)); } catch { /* no log */ }
  for (const p of pages) { try { await p.close(); } catch { /* closed */ } }
  try { if (proxy) proxy.close(); } catch { /* closed */ }
  try { await browser?.send("Browser.close"); } catch { /* closed */ }
  await delay(800);
  if (chrome) killTree(chrome.pid);
  gpu?.release();
  await stopServer().catch(() => {});
  try { rmSync(PROFILE, { recursive: true, force: true }); } catch { /* busy */ }
  console.log(`summary ${JSON.stringify(report.summary)} -> ${join(dir, `jam-verify-${STAMP}.json`)}`);
  exitCode = report.summary.failed || report.errors.length ? 1 : 0;
  process.exit(exitCode);
}
