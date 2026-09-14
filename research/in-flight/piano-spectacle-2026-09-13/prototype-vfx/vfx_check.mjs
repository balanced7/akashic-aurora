// Headless spectacle check for the piano-lab-vfx prototype. No window is opened.
// usage: node vfx_check.mjs <mode: hook|auto> <port>
//   hook: Rare and Legendary fired from __piano.fx() over held chords, snapshots mid-effect, GPU frame-cost benches,
//         a dense pedalled wash with a Legendary on top, and a 16:9 Legendary
//   auto: plays the ~55 s pedalled F major wash score with ?fx=auto and records which tiers the scorer fires
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const MODE = process.argv[2] || "hook";
const PORT = Number(process.argv[3] || 9611);
const APP = "http://127.0.0.1:8793/web/piano-lab-vfx.html" + (MODE === "auto" ? "?fx=auto" : "");
const OUT = join("E:\\AI-Setup\\state\\arsenal\\receipts\\piano-spectacle\\vfx", process.argv[4] || MODE);
const profile = join(tmpdir(), `arsenal-vfx-check-${PORT}-${Date.now()}`);
mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, [
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
  "--mute-audio", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
  "--disable-background-timer-throttling", "--headless=new", "--window-size=1600,1000", "about:blank",
], { stdio: "ignore" });

const getJSON = async (url) => (await fetch(url)).json();
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { const v = await fn(); if (v) return v; } catch { /* not yet */ }
    await delay(200);
  }
  throw new Error(`timed out waiting for ${what}`);
}
function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      } else if (msg.method) listeners.forEach((l) => l(msg));
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const i = id++; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); }),
      on: (fn) => listeners.push(fn),
    });
    ws.onerror = () => reject(new Error("websocket error"));
  });
}

// One snapshot and its numbers, from the same rendered frame.
//   luma, white (min channel > 0.85), upper (top 55%)
//   labelBg: mean luma of the chord-name box's non-text pixels (luma < 0.7); labelText: share of pixels > 0.85 there
//   staffLuma: mean luma inside the staff box (spec acceptance: < 0.6)
//   keysSat: saturation of lit pixels in the key band; floor: mean luma of the floor band below the keys
const PROTECT = { "9:16": { label: [0.17, 0.10, 0.83, 0.235], staff: [0.13, 0.30, 0.88, 0.54], keys: [0.72, 0.80], floor: [0.83, 1.0] },
                  "16:9": { label: [0.01, 0.08, 0.47, 0.30], staff: [0.66, 0.06, 0.99, 0.46], keys: [0.62, 0.80], floor: [0.84, 1.0] } };
const SHOT = `(async () => {
  const P = ${JSON.stringify(PROTECT)};
  const url = window.__piano.snapshot();
  const s = window.__piano.stats();
  const R = P[s.framing];
  const img = new Image(); img.src = url; await img.decode();
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, img.width, img.height).data;
  const W = img.width, H = img.height;
  let luma = 0, white = 0, upper = 0, upperN = 0, lb = 0, lbN = 0, lt = 0, lN = 0, st = 0, stN = 0, kLit = 0, kSat = 0, fl = 0, flN = 0;
  const inR = (x, y, r) => x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3];
  for (let i = 0, p = 0; i < d.length; i += 4, p++) {
    const r = d[i] / 255, gg = d[i + 1] / 255, b = d[i + 2] / 255;
    const mx = Math.max(r, gg, b), mn = Math.min(r, gg, b);
    const l = 0.2126 * r + 0.7152 * gg + 0.0722 * b;
    const x = (p % W) / W, y = Math.floor(p / W) / H;
    luma += l;
    if (mn > 0.85) white++;
    if (y < 0.55) { upper += l; upperN++; }
    if (inR(x, y, R.label)) { lN++; if (l > 0.85) lt++; if (l < 0.7) { lb += l; lbN++; } }
    if (inR(x, y, R.staff)) { st += l; stN++; }
    if (y > R.keys[0] && y < R.keys[1] && mx > 0.35) { kLit++; kSat += (mx - mn) / mx; }
    if (y > R.floor[0] && y < R.floor[1]) { fl += l; flN++; }
  }
  const n = d.length / 4, f = (v) => +v.toFixed(4);
  const log = window.__piano.fxLog(), last = log[log.length - 1];
  return { url, m: { luma: f(luma / n), white: f(white / n), upper: f(upper / upperN), labelBg: f(lb / Math.max(lbN, 1)),
           labelText: f(lt / Math.max(lN, 1)), staffLuma: f(st / Math.max(stN, 1)), keysSat: f(kLit ? kSat / kLit : 0),
           floor: f(fl / Math.max(flN, 1)), fxAge: last ? +(window.__piano.clock() - last.t).toFixed(3) : null,
           fxTier: last ? last.name : null, chord: s.chord, label: s.label, framing: s.framing, fps: s.fps, trailsLive: s.trailsLive } };
})()`;

const report = { at: new Date().toISOString(), app: APP, mode: MODE, shots: [], bench: {}, errors: [] };
let browser;
try {
  const version = await waitFor(() => getJSON(`http://127.0.0.1:${PORT}/json/version`), 20000, "Chrome");
  browser = await connect(version.webSocketDebuggerUrl);
  const target = (await getJSON(`http://127.0.0.1:${PORT}/json/list`)).find((t) => t.type === "page");
  const page = await connect(target.webSocketDebuggerUrl);
  page.on((msg) => {
    if (msg.method === "Runtime.exceptionThrown") report.errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
    if (msg.method === "Runtime.consoleAPICalled" && /error|warn/.test(msg.params.type)) {
      const text = msg.params.args.map((a) => a.value ?? a.description).join(" ");
      if (!/X4122/.test(text)) report.errors.push(text);
    }
  });
  await page.send("Runtime.enable");
  await page.send("Page.enable");
  const evaluate = async (expression) => {
    const r = await page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const shot = async (name) => {
    const { url, m } = await evaluate(SHOT);
    writeFileSync(join(OUT, `${name}.jpg`), Buffer.from(url.split(",")[1], "base64"));
    report.shots.push({ name, ...m });
    console.log(name.padEnd(22), JSON.stringify(m));
  };
  const midi = (bytes) => evaluate(`window.__piano.midiMessage(${JSON.stringify(bytes)})`);
  const chordOn = async (notes, vel) => { for (const n of notes) await midi([0x90, n, vel]); };
  const allOff = async (notes) => { for (const n of notes) await midi([0x80, n, 0]); await midi([0xb0, 64, 0]); };
  const at = async (t0, sec) => { const w = t0 + sec * 1000 - Date.now(); if (w > 0) await delay(w); };

  await page.send("Page.navigate", { url: APP });
  await waitFor(() => evaluate("!!(window.__piano && window.__piano.ready)"), 30000, "piano ready");
  await delay(3000);
  report.gpu = await evaluate("window.__piano.gpu()");
  const compileErrors = report.errors.filter((e) => /shader|program|glsl|THREE/i.test(e));
  if (compileErrors.length) console.log("SHADER ERRORS", compileErrors);

  if (MODE === "hook") {
    report.bench.idle = await evaluate("window.__piano.bench(240)");

    // RARE over a pedalled Bbmaj9 (Bb2 F3 A3 C4 D4 F4), struck together at velocity 100
    const RARE = [46, 53, 57, 60, 62, 65];
    await midi([0xb0, 64, 127]);
    await chordOn(RARE, 100);
    await delay(1000);
    await shot("rare-0-before");
    report.bench.chordHeld = await evaluate("window.__piano.bench(240)");
    await delay(600);
    let t0 = Date.now();
    await evaluate("window.__piano.fx(2)");
    for (const [s, name] of [[0.25, "rare-1-+0.25s"], [0.6, "rare-2-+0.6s"], [1.0, "rare-3-+1.0s"], [1.7, "rare-4-+1.7s"], [3.0, "rare-5-+3.0s-after"]]) { await at(t0, s); await shot(name); }
    await evaluate("window.__piano.fx(2)");
    report.bench.rareLive = await evaluate("window.__piano.bench(90)");
    await allOff(RARE);
    await delay(6500);

    // LEGENDARY over a pedalled Fmaj9/A spread over three octaves (A2 F3 C4 E4 G4 A4 C5 E5), velocity 118
    const LEG = [45, 53, 60, 64, 67, 69, 72, 76];
    await midi([0xb0, 64, 127]);
    await chordOn(LEG, 118);
    await delay(1000);
    await shot("leg-0-before");
    t0 = Date.now();
    await evaluate("window.__piano.fx(4)");
    for (const [s, name] of [[0.3, "leg-1-+0.3s"], [0.8, "leg-2-+0.8s"], [1.4, "leg-3-+1.4s"], [2.2, "leg-4-+2.2s"], [3.2, "leg-5-+3.2s"], [6.0, "leg-6-+6.0s-after"]]) { await at(t0, s); await shot(name); }
    await evaluate("window.__piano.fx(4)");
    await delay(700);
    report.bench.legendaryLive = await evaluate("window.__piano.bench(90)");
    await evaluate("window.__piano.fx(4); window.__piano.fx(3); window.__piano.fx(2)");
    await delay(500);
    report.bench.stackedLive = await evaluate("window.__piano.bench(90)");
    await allOff(LEG);
    await delay(6500);

    // DENSE WASH + LEGENDARY: 40 notes in 4 s across three octaves, pedal down throughout, then a Legendary on top
    await midi([0xb0, 64, 127]);
    const dense = [];
    for (let i = 0; i < 40; i++) dense.push(48 + ((i * 7) % 36));
    t0 = Date.now();
    for (let i = 0; i < 40; i++) {
      await at(t0, i * 0.1);
      await midi([0x90, dense[i], 70 + ((i * 13) % 50)]);
      setTimeout(() => {}, 0);
      if (i % 2) await midi([0x80, dense[i - 1], 0]);
    }
    await delay(150);
    await shot("wash-0-dense");
    const t1 = Date.now();
    await evaluate("window.__piano.fx(4)");
    await at(t1, 0.8); await shot("wash-1-leg+0.8s");
    await at(t1, 1.6); await shot("wash-2-leg+1.6s");
    report.bench.denseLegendary = await evaluate("window.__piano.bench(90)");
    await allOff(dense);
    await delay(6000);

    // 16:9 LEGENDARY
    await evaluate("document.getElementById('btn-169').click()");
    await delay(800);
    await midi([0xb0, 64, 127]);
    await chordOn(LEG, 118);
    await delay(1000);
    await shot("wide-0-before");
    t0 = Date.now();
    await evaluate("window.__piano.fx(4)");
    await at(t0, 0.8); await shot("wide-1-leg+0.8s");
    await at(t0, 1.5); await shot("wide-2-leg+1.5s");
    await allOff(LEG);
    await evaluate("document.getElementById('btn-916').click()");
  } else {
    // the wash_check score: 80 bpm, bars 0-7 change the pedal each bar, bars 8-15 hold one pedal, bar 16 a loud spread F chord
    const BEAT = 0.75, BAR = 3.0;
    const PROG = [
      { bass: 45, arp: [53, 57, 60, 65, 69, 65, 60, 57], mel: [77, 76] },
      { bass: 43, arp: [52, 55, 60, 64, 67, 64, 60, 55], mel: [76, 74] },
      { bass: 38, arp: [50, 53, 57, 62, 65, 62, 57, 53], mel: [74, 72] },
      { bass: 46, arp: [50, 53, 57, 58, 62, 58, 57, 53], mel: [74, 69] },
    ];
    const events = [];
    const on = (t, n, v, len) => { events.push({ t, b: [0x90, n, v] }); events.push({ t: t + len, b: [0x80, n, 0] }); };
    const pedal = (t, down) => events.push({ t, b: [0xb0, 64, down ? 127 : 0] });
    for (let bar = 0; bar < 16; bar++) {
      const t = 0.5 + bar * BAR;
      const c = PROG[bar % 4];
      if (bar <= 8) { if (bar > 0) pedal(t - 0.05, false); pedal(t + 0.08, true); }
      on(t, c.bass, 95, BEAT * 1.5);
      c.arp.forEach((n, i) => on(t + i * BEAT / 2, n, 58 + ((i * 17 + bar * 7) % 26), 0.3));
      on(t, c.mel[0], 100, 1.4);
      on(t + 2 * BEAT, c.mel[1], 88, 1.4);
    }
    const FINAL = 0.5 + 16 * BAR;
    pedal(FINAL - 0.05, false);
    [41, 53, 57, 60, 65, 69, 72, 77].forEach((n, i) => on(FINAL + i * 0.03, n, 110, 2.0));
    pedal(FINAL + 0.1, true);
    pedal(FINAL + 2.6, false);
    // a block-chord coda so the scorer sees real strikes: Bbmaj9/D, Gm11, C9sus4, Fmaj13 (loud, wide, pedalled)
    const CODA = FINAL + 5;
    const coda = [[38, 46, 57, 60, 62, 65, 69], [43, 50, 58, 60, 65, 70, 74], [36, 48, 58, 62, 65, 67, 74], [29, 41, 57, 64, 67, 69, 72, 76, 79]];
    coda.forEach((ch, k) => {
      const t = CODA + k * 3;
      pedal(t - 0.05, false); pedal(t + 0.08, true);
      ch.forEach((n, i) => on(t + i * 0.015, n, k === 3 ? 120 : 96 + k * 6, 2.4));
    });
    pedal(CODA + 12 + 2.5, false);
    events.sort((a, b) => a.t - b.t);
    await evaluate(`(() => { const ev = ${JSON.stringify(events)};
      for (const e of ev) setTimeout(() => window.__piano.midiMessage(e.b), e.t * 1000); return ev.length; })()`);
    const t0 = Date.now();
    const SHOTS = [[12.4, "auto-bar4"], [30.4, "auto-hold"], [49.0, "auto-final"], [53.6, "auto-coda-1"], [59.4, "auto-coda-3"], [62.3, "auto-coda-4+0.3"], [63.0, "auto-coda-4+1.0"], [70.0, "auto-end"]];
    for (const [s, name] of SHOTS) { const w = t0 + s * 1000 - Date.now(); if (w > 0) await delay(w); await shot(name); }
    report.fxLog = await evaluate("window.__piano.fxLog()");
    const count = [0, 0, 0, 0, 0];
    for (const e of report.fxLog) count[e.tier]++;
    report.tierCounts = { Common: count[0], Uncommon: count[1], Rare: count[2], Epic: count[3], Legendary: count[4] };
    console.log("tiers", JSON.stringify(report.tierCounts));
    for (const e of report.fxLog) console.log(e.t.toFixed(2), e.name.padEnd(10), String(e.chord).padEnd(12), JSON.stringify(e.why));
  }
  console.log("bench", JSON.stringify(report.bench));
} catch (err) {
  report.fatal = String(err.stack || err);
  console.log("FATAL", report.fatal);
} finally {
  writeFileSync(join(OUT, "vfx-check.json"), JSON.stringify(report, null, 2));
  try { await browser?.send("Browser.close"); } catch { /* closed */ }
  await delay(800);
  try { chrome.kill(); } catch { /* gone */ }
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* busy */ }
  console.log("gpu:", JSON.stringify(report.gpu));
  console.log("errors:", JSON.stringify(report.errors));
  process.exit(0);
}
