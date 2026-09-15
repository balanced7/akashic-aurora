// Headless page check for the score lab, arsenal/web/piano-lab-score.html (slice LS5 of the live sheet music plan,
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md section 10.4, receipt LR11; plan-amendments.md
// section 0 rule 4: replay first, no receipt depends on Web MIDI). A small lab server on 127.0.0.1:8981 serves
// arsenal/web, synthetic fixtures (tests/fixtures/score/gen.mjs) and, with --sessions, S1..Sn events.jsonl by S-number
// (read-only; ids never leave this machine). A headless Chrome on DevTools port 9981 opens the page and drives it.
//   node tests/score_lab.test.mjs                     Node only: the server answers (page, modules, fixtures); no browser
//   node tests/score_lab.test.mjs --browser           also the headless Chrome check (G1 bench, fixture replays, seeks)
//   node tests/score_lab.test.mjs --browser --sessions  also replays 180 s of S12 in the page (aggregates only)
//   node tests/score_lab.test.mjs --serve             the lab server alone on 8981 (open /web/piano-lab-score.html)
// Browser rules (this machine): headless only, with the three anti-throttling flags; before launch, wait while a node
// process running jam_timing.mjs or jam_verify.mjs exists (timing receipts are load-sensitive); take the GPU lock
// (mkdir state/arsenal/gpu-render.lock, which fails while held) and remove it the moment the browser work ends; keep the
// burst under 3 minutes. Never `chrome --version`. Writes state/arsenal/score/ls5-lab-2026-09-15.json (and a fixture
// screenshot) with S-numbers and aggregates only.
// Receipts measured in the page: LR11a paintOpenBar / paintTape p95 on 43- and 67-onset windows; LR11b engraveBar
// (layout plus draw) p95 at 12/24/43/67 onsets; LR11c one ~400 x 280 tile upload p95 with the three.js scene running;
// LR11d drawing calls on a settled tile's context after it settled and re-uploads of settled tiles (0); LR11e the head
// shift at the settle crossfade the page's ribbon measured; LR11g glyph collisions on the bench bars.
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import * as G from "./fixtures/score/gen.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.join(here, "..");
const WEB = path.join(REPO, "arsenal", "web");
const PERF = path.join(REPO, "state", "arsenal", "performance");
const OUT = path.join(REPO, "state", "arsenal", "score");
const LOCK = path.join(REPO, "state", "arsenal", "gpu-render.lock");
// this build's ports on this machine: the lab server 8981, Chrome DevTools 9981 (8981-8983 / 9981-9983 are reserved for it)
const PORT = 8981, DEVTOOLS = 9981;
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const argv = process.argv.slice(2);
const browser = argv.includes("--browser"), sessions = argv.includes("--sessions"), serveOnly = argv.includes("--serve");
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") { if (ok) { pass++; return; } fail++; console.log(`FAIL ${label}${detail ? ": " + detail : ""}`); }

// ------------------------------------------------------------------------------------------ fixtures ---
function fixture(name) {
  if (name === "tape15") return { events: G.genTapeRun({ seconds: 1.5, rate: 10 }).events, meter: "4/4" };
  if (name === "tape4") return { events: G.genTapeRun({ seconds: 4, rate: 10 }).events, meter: "4/4" };
  let m = /^tempo(\d+)$/.exec(name);
  if (m) { const row = G.tempoSuite()[Number(m[1])]; return row ? { events: G.eventsOf(row.piece), meter: row.meter } : null; }
  m = /^(\w+)-(\d+)$/.exec(name);
  if (m && G.FAMILIES.includes(m[1])) {
    const row = G.familySuite(m[1])[Number(m[2])];
    return row ? { events: row.take.events, beats_ms: row.take.truth.beats_ms, one_ms: row.take.truth.downbeats_ms[0], meter: row.take.spec.meter } : null;
  }
  return null;
}
function sessionDirs() { return fs.existsSync(PERF) ? fs.readdirSync(PERF).filter((d) => fs.existsSync(path.join(PERF, d, "events.jsonl"))).sort() : []; }

// ------------------------------------------------------------------------------------------- server ---
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".jsonl": "application/x-ndjson", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png" };
function startServer(port, { allowSessions = false } = {}) {
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const send = (code, body, type = "text/plain; charset=utf-8") => { res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
    try {
      if (u.pathname === "/") { res.writeHead(302, { Location: "/web/piano-lab-score.html" }); return res.end(); }
      if (u.pathname.startsWith("/web/")) {
        const target = path.resolve(WEB, decodeURIComponent(u.pathname.slice(5)));
        if (!target.startsWith(WEB + path.sep)) return send(403, "outside arsenal/web");
        if (!fs.existsSync(target) || !fs.statSync(target).isFile()) return send(404, "not found");
        res.writeHead(200, { "Content-Type": TYPES[path.extname(target)] || "application/octet-stream", "Cache-Control": "no-store" });
        return fs.createReadStream(target).pipe(res);
      }
      let m = /^\/fixture\/([\w-]+)\.json$/.exec(u.pathname);
      if (m) { const f = fixture(m[1]); return f ? send(200, JSON.stringify(f), TYPES[".json"]) : send(404, "no such fixture"); }
      m = /^\/session\/S(\d+)\/events\.jsonl$/.exec(u.pathname);
      if (m && allowSessions) {
        const d = sessionDirs()[Number(m[1]) - 1];
        if (!d) return send(404, "no such session");
        res.writeHead(200, { "Content-Type": TYPES[".jsonl"], "Cache-Control": "no-store" });
        return fs.createReadStream(path.join(PERF, d, "events.jsonl")).pipe(res);
      }
      return send(404, "not found");
    } catch (e) { return send(500, String(e && e.message)); }
  });
  return new Promise((resolve, reject) => { server.once("error", reject); server.listen(port, "127.0.0.1", () => resolve(server)); });
}

if (serveOnly) {
  await startServer(PORT, { allowSessions: true });
  console.log(`score lab: http://127.0.0.1:${PORT}/web/piano-lab-score.html  (fixtures: /fixture/tempo2.json, /fixture/pedal-0.json; sessions: /session/S12/events.jsonl)`);
  await new Promise(() => {});
}

// ---------------------------------------------------------------------------------------- Node checks ---
const server = await startServer(PORT, { allowSessions: sessions });
const get = async (p) => { const r = await fetch(`http://127.0.0.1:${PORT}${p}`); return { status: r.status, type: r.headers.get("content-type"), text: await r.text() }; };
{
  const page = await get("/web/piano-lab-score.html");
  check("lab server: the page", page.status === 200 && /piano-lab-score\.js/.test(page.text), String(page.status));
  for (const mod of ["piano-lab-score.js", "piano/score/ribbon.js", "piano/score/layout.js", "piano/score/paint.js", "piano/score/engrave.js", "piano/score/bench.js", "piano/score/index.js", "piano/spell.js", "piano/nashville.js"]) {
    const r = await get("/web/" + mod);
    check(`lab server: /web/${mod} as JavaScript`, r.status === 200 && /javascript/.test(r.type), `${r.status} ${r.type}`);
  }
  const fx = await get("/fixture/pedal-0.json");
  const fj = fx.status === 200 ? JSON.parse(fx.text) : null;
  check("lab server: a fixed-beat fixture take", fj && fj.events.length > 100 && fj.beats_ms.length > 10);
  check("lab server: nothing outside arsenal/web", (await get("/web/..%2F..%2Fstate%2Farsenal")).status >= 403);
  check("lab server: sessions only with --sessions", sessions || (await get("/session/S1/events.jsonl")).status === 404);
}

// ------------------------------------------------------------------------------------------ browser ---
function jamProcesses() {
  const r = spawnSync("powershell.exe", ["-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | ForEach-Object { $_.CommandLine }"], { encoding: "utf8" });
  return (r.stdout || "").split(/\r?\n/).filter((l) => /jam_timing\.mjs|jam_verify\.mjs/.test(l)).length;
}
function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map(), listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result); }
      else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onopen = () => resolve({ send: (method, params = {}) => new Promise((res, rej) => { const id = nextId++; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); }), on: (fn) => listeners.push(fn), close: () => ws.close() });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}
async function waitFor(fn, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { try { const v = await fn(); if (v) return v; } catch { /* not yet */ } await delay(200); } throw new Error(`timed out waiting for ${what}`); }

if (browser) {
  const report = { api: "arsenal.receipt/v0", slice: "LS5", receipt: "LR11", date: "2026-09-15", port: PORT, devtools: DEVTOOLS, steps: [], console: [], exceptions: [] };
  const step = (name, data) => { report.steps.push({ name, ...data }); console.log(`[${name}]`, JSON.stringify(data).slice(0, 600)); };
  let chrome = null, profile = null, locked = false, cdp = null, burstStart = null;
  try {
    for (let n = jamProcesses(); n > 0; n = jamProcesses()) { step("wait-jam-timing", { processes: n }); spawnSync(process.execPath, ["-e", "setTimeout(()=>{},60000)"]); }
    for (let tries = 0; ; tries++) {
      try { fs.mkdirSync(LOCK); locked = true; break; } catch (e) { if (e.code !== "EEXIST" || tries > 30) throw e; step("wait-gpu-lock", { tries }); await delay(20000); }
    }
    burstStart = Date.now();
    if (!fs.existsSync(CHROME)) throw new Error("Chrome not found at " + CHROME);
    profile = fs.mkdtempSync(path.join(os.tmpdir(), "score-lab-chrome-"));
    chrome = spawn(CHROME, [
      "--headless=new", `--remote-debugging-port=${DEVTOOLS}`, `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check", "--mute-audio",
      "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding", "--disable-background-timer-throttling",
      "--window-size=1500,1400", "about:blank",
    ], { stdio: "ignore" });
    const version = await waitFor(async () => (await fetch(`http://127.0.0.1:${DEVTOOLS}/json/version`)).json(), 20000, "Chrome DevTools");
    report.chrome = version.Browser;
    const target = (await (await fetch(`http://127.0.0.1:${DEVTOOLS}/json/list`)).json()).find((t) => t.type === "page");
    cdp = await connect(target.webSocketDebuggerUrl);
    cdp.on((msg) => {
      const p = msg.params;
      if (msg.method === "Runtime.consoleAPICalled") report.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300) });
      else if (msg.method === "Runtime.exceptionThrown") report.exceptions.push({ text: p.exceptionDetails.text, description: (p.exceptionDetails.exception?.description || "").slice(0, 400) });
      else if (msg.method === "Log.entryAdded" && (p.entry.level === "error" || p.entry.level === "warning")) report.console.push({ type: "log-" + p.entry.level, text: p.entry.text.slice(0, 300), url: p.entry.url });
    });
    for (const d of ["Runtime", "Log", "Page"]) await cdp.send(`${d}.enable`);
    const evaluate = async (expression, timeout = 90000) => {
      const r = await Promise.race([cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }), delay(timeout).then(() => { throw new Error("evaluate timed out: " + expression.slice(0, 80)); })]);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    await cdp.send("Page.navigate", { url: `http://127.0.0.1:${PORT}/web/piano-lab-score.html` });
    await waitFor(() => evaluate("!!window.scoreLab"), 20000, "window.scoreLab");
    const fonts = await evaluate("scoreLab.fonts()", 15000);
    step("loaded", { fonts });

    // G1 bench
    const bench = await evaluate("scoreLab.bench()", 90000);
    step("bench", { gl: bench.gl, checks: bench.checks });
    report.bench = bench;

    // a fixed-beat fixture (the jam rung stand-in): bars settle and freeze
    const run1 = await evaluate(`(async () => { await scoreLab.loadUrl('/fixture/pedal-1.json'); return scoreLab.run({ frameMs: 1000 / 60 }); })()`, 60000);
    step("fixture-fixed-beats", { counters: run1.counters, ribbon: run1.ribbon, ms: run1.ms });
    const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, "ls5-lab-fixture-2026-09-15.png"), Buffer.from(shot.data, "base64"));

    // inferred beats: the tempo suite's steady rub0 pieces, then seeks (a new ribbon each) and a x2 press with the hold header
    const run2 = await evaluate(`(async () => { await scoreLab.loadUrl('/fixture/tempo2.json'); return scoreLab.run({ frameMs: 1000 / 60 }); })()`, 60000);
    step("fixture-inferred", { counters: run2.counters, ribbon: run2.ribbon, ms: run2.ms });
    const seekRes = await evaluate(`(() => {
      const before = scoreLab.stats().counters.ribbons;
      scoreLab.seek(30000); const a = scoreLab.run({ seconds: 10 });
      scoreLab.seek(12000); const b = scoreLab.run({ seconds: 6 });
      scoreLab.press('level', 2);
      const heads = [];
      for (let i = 0; i < 40; i++) { scoreLab.run({ seconds: 0.25 }); const h = scoreLab.stats().header; heads.push({ bpm: h.bpm, word: h.word, dim: h.dim, requested: h.requested }); }
      return { ribbonsAdded: scoreLab.stats().counters.ribbons - before, rangeErrors: scoreLab.stats().counters.rangeErrors, afterSeekT: [a.t, b.t], heads };
    })()`, 60000);
    step("seeks-and-press", { ribbonsAdded: seekRes.ribbonsAdded, rangeErrors: seekRes.rangeErrors, heads: seekRes.heads.slice(0, 12) });
    const blankAfterPress = seekRes.heads.filter((h) => h.bpm == null).length;
    const holdTicks = seekRes.heads.filter((h) => h.word === "hold" && h.requested != null).length;
    const holdDimmed = seekRes.heads.filter((h) => h.word === "hold" && h.requested != null).every((h) => h.dim);

    let run3 = null;
    if (sessions && sessionDirs().length >= 12) {
      run3 = await evaluate(`(async () => { await scoreLab.loadUrl('/session/S12/events.jsonl'); return scoreLab.run({ seconds: 180, frameMs: 1000 / 60, budgetMs: 70000 }); })()`, 80000);
      step("S12-180s", { counters: run3.counters, ribbon: run3.ribbon, ms: run3.ms, t: run3.t });
    }
    const all = [run1, run2, ...(run3 ? [run3] : [])];
    report.burstSeconds = (Date.now() - burstStart) / 1000;

    // ------------------------------------------------------------------------------------- receipts ---
    const b = bench;
    receipts.push({ id: "LR11a", measured: b.lr11a, threshold: b.checks.LR11a.threshold, pass: b.checks.LR11a.pass });
    receipts.push({ id: "LR11b", measured: b.lr11b, threshold: b.checks.LR11b.threshold, pass: b.checks.LR11b.pass });
    receipts.push({ id: "LR11c", measured: b.lr11c, threshold: b.checks.LR11c.threshold, pass: b.checks.LR11c.pass, gl: b.gl });
    const settled = all.reduce((s, r) => s + r.counters.settledEngraves, 0);
    const after = all.reduce((s, r) => s + r.counters.drawCallsAfterSettle, 0), reup = all.reduce((s, r) => s + r.counters.settledReuploads, 0), repaints = all.reduce((s, r) => s + r.counters.settledRepaints, 0);
    receipts.push({ id: "LR11d", measured: { settledTiles: settled, drawCallsAfterSettle: after, settledRepaints: repaints, settledReuploads: reup, tileUploads: all.map((r) => r.counters.tileUploads), inSituUploadMs: all.map((r) => r.ms.tileUpload) }, threshold: "0", pass: settled > 0 && after === 0 && reup === 0 && repaints === 0 });
    const e1 = run1.ribbon.shiftOpenToEngraved, e2 = run2.ribbon.shiftOpenToEngraved;
    receipts.push({ id: "LR11e-page", measured: { fixedBeats: e1, inferred: e2, settlingToSettled: [run1.ribbon.shiftSettlingToSettled, run2.ribbon.shiftSettlingToSettled] }, threshold: "<= 0.5 s mean on beats that did not widen (in-bar shift measured here; the beat-local gate is tests/score_layout.test.mjs)", pass: (e1.unwidenedMeanSp ?? 0) <= 0.5 && (e2.unwidenedMeanSp ?? 0) <= 0.5 });
    receipts.push({ id: "LR11g", measured: b.lr11g, threshold: b.checks.LR11g.threshold, pass: b.checks.LR11g.pass });
    receipts.push({ id: "LR11-page", measured: { frameMs: all.map((r) => r.ms.frame), tickMs: all.map((r) => r.ms.tick), openPaintMs: all.map((r) => r.ms.openPaint), lightEngraveMs: all.map((r) => r.ms.lightEngrave), settledEngraveMs: all.map((r) => r.ms.settledEngrave), S12: run3 ? { overlapsPerTapeMinute: run3.ribbon.overlapsPerTapeMinute, columns: run3.ribbon.columns, tapeMinutes: run3.ribbon.tapeMinutes, frozenBars: run3.ribbon.commits } : null, exceptions: report.exceptions.length, burstSeconds: report.burstSeconds }, threshold: "reported", pass: null });
    receipts.push({ id: "LR11-seek-hold", measured: { ribbonsAdded: seekRes.ribbonsAdded, rangeErrors: seekRes.rangeErrors, blankAfterPress, holdTicks, holdDimmed }, threshold: "a new ribbon on every seek, 0 RangeErrors, 0 blank headers after a press", pass: seekRes.ribbonsAdded === 2 && seekRes.rangeErrors === 0 && blankAfterPress === 0 && holdDimmed });

    check("page: fonts loaded (the house engraver draws)", fonts.smufl === true, JSON.stringify(fonts));
    check("page: WebGL scene for the upload bench", !!b.gl && !!b.gl.kind && b.gl.kind !== "none", JSON.stringify(b.gl));
    check("LR11a paintOpenBar / paintTape p95", b.checks.LR11a.pass, JSON.stringify(b.lr11a));
    check("LR11b engraveBar p95 at 43 and 67 onsets", b.checks.LR11b.pass, JSON.stringify(b.lr11b));
    check("LR11c tile upload p95 <= 2 ms", b.checks.LR11c.pass, JSON.stringify(b.lr11c));
    check("LR11d settled tiles: 0 drawing calls after settling, 0 re-engraves, 0 re-uploads", settled > 0 && after === 0 && reup === 0 && repaints === 0, JSON.stringify({ settled, after, repaints, reup }));
    check("LR11g bench bars: 0 collisions with widening (page)", b.checks.LR11g.pass, JSON.stringify(b.lr11g));
    check("seek builds a new ribbon each time, no RangeError", seekRes.ribbonsAdded === 2 && seekRes.rangeErrors === 0, JSON.stringify({ ribbonsAdded: seekRes.ribbonsAdded, rangeErrors: seekRes.rangeErrors }));
    check("header after a x2 press in the page: never blank, the request dimmed with hold", blankAfterPress === 0 && holdDimmed, JSON.stringify({ blankAfterPress, holdTicks, holdDimmed }));
    check("page: no exceptions", report.exceptions.length === 0, JSON.stringify(report.exceptions.slice(0, 3)));
    check("browser burst under 3 minutes", report.burstSeconds < 180, String(report.burstSeconds));
  } catch (e) {
    step("error", { message: String((e && e.stack) || e).slice(0, 1200) });
    check("browser run completed", false, String(e && e.message));
  } finally {
    try { await cdp?.send("Browser.close"); } catch { /* gone */ }
    await delay(800);
    try { chrome?.kill(); } catch { /* gone */ }
    if (locked) { try { fs.rmdirSync(LOCK); } catch (e) { console.log("could not remove the GPU lock:", e.message); } }
    report.lockReleasedAt = new Date().toISOString();
    try { if (profile) fs.rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may hold a file */ }
    report.receipts = receipts;
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, "ls5-lab-2026-09-15.json"), JSON.stringify(report, null, 1));
    console.log("receipt written to state/arsenal/score/ls5-lab-2026-09-15.json");
  }
}

server.close();
for (const r of receipts) console.log("RECEIPT", JSON.stringify(r).slice(0, 2000));
console.log(`score_lab: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
