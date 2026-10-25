// VJ storm receipt: pad storms on a 60 fps VIRTUAL clock, the frames as the viewer gets them, and flashes counted the way
// the 2026-10-24 adversarial verifier counted them. In a private headless Chrome forced onto SwiftShader (the CPU: this
// host's AMD driver has a crash history, so no frame here is ever drawn on the GPU), under the house GPU lock, in bursts
// under three minutes with the lock released between them.
//
//   node arsenal/lanes/vj_storm.mjs [--web <dir>] [--label L] [--sets id,id] [--scenarios a,b] [--seconds 10]
//                                   [--phases storm,calm,parity,bench] [--port 8975] [--out <dir>] [--lock-dir <dir>]
//
// WHY. The impact pass (2026-10-24) made every hit throw light that never asks the FlashGate (the punch, the set's own
// reaction, the overlay, the glitch). The verifier measured pad storms on a virtual clock and found up to about 6.5
// flashes a second (8.5 in one-shot storms), where the gate alone keeps about 3. The real-clock storm in vj_verify had
// missed it: SwiftShader's slow frames stretch a storm and it counted rises only. This receipt is the replacement: every
// frame is one 60 Hz step, so a storm of 15 hits a second is exactly that, and pairs of swings are counted, not rises.
//
// HOW. The vj page loads with an init script that replaces performance.now and requestAnimationFrame (vj_impact's
// virtual clock): a frame is drawn only when the receipt steps the clock by 1000/60 ms. Each frame the receipt reads the
// canvas (the frame the viewer gets: after every layer and after gate v2) and keeps, per cell of a 4 x 4 grid, the mean
// relative luminance (sRGB-decoded, WCAG weights) and the mean WCAG red quantity (max(0, R - G - B) x 320 over pixels
// with R / (R + G + B) >= 0.8). From those it builds 18 windows of a quarter of the screen or more (the whole frame, the
// nine 2 x 2 blocks -- the four quadrants among them -- the four rows, the four columns) and counts flashes in each with
// the verifier's counter, kept verbatim below: turning points with a hysteresis of 0.02, a transition is a swing of 0.1 or
// more between turning points whose darker end is under 0.8, counted at its later turning point; flashes in a second =
// transitions in that second / 2. Red: hysteresis 2, swing 20 (on the x320 scale), darker end under 0.8.
// THE SCENARIOS (presses hard, a seeded pick; one-shots held 4 frames, holdables 18-48):
//   invert10   pad 11 (Invert) held throughout, hard hits at 10 a second on pads 1, 2, 4, 6, 7, 12
//   oneshots15 pads 1, 2, 4, 12 at 15 a second          oneshots5   the same at 5 a second
//   nozoom15   pads 1, 2, 4 at 15 a second             all12       all 12 pads, a hit every 3 frames (20 a second)
//   flashedge  pad 3 (the white flash) every 3 frames: the gate grants it at exactly its own limit, a third of a second
//              apart, the edge where the shader blanks the flash (envFlashSafe) and the dip used to ride without it
//   flash24    pad 3 every 24 frames (2.5 a second): granted flashes the shader shows at half strength
// THE VERDICT: on every set and scenario, at most 3 flashes in any second in every window, at most 3 red flashes, and no
// flashing run (every trailing second holding a flash) longer than gate v2's rest allows (5 s, plus 1.2 s of counting).
// THE PARITY PHASE feeds the page's GPU limiter and its JS twin (vj-gate.js FlashLimiter) the same synthetic cell sums
// frame by frame and compares the gains, the fallback blend and the trackers' held flags.
// THE CALM PHASE plays each set under the page's own demo music (beats, chords, energy; no pads) for twice --seconds and
// reads the limiter's state back every 15 frames: under music alone a set should flash at most 3 times a second in every
// window (the verdict) and gate v2 should not need to hold it at all (reported: samples held, samples resting).
// THE BENCH PHASE times the limiter's passes on the real clock (each stage fenced by a one-pixel readPixels: meter,
// decide, apply, blit) against the plain copy to the canvas they replace.
// Writes state/arsenal/receipts/vj-storm-<label>-<stamp>/receipt.json; exits 1 when the verdict fails. vj_verify runs the
// same storms (fewer frames) through runStormInPage.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { LOCK_DIR, acquireGpuLock } from "./gpu_lock.mjs";
import { GPU_FENCE_FLAGS, QUIET_FLAGS, SWIFTSHADER_FLAGS, judgeRenderer } from "../shaders/headless.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));

// ------------------------------------------------------------------------- the verifier's counter, verbatim --
// (arsenal/lanes/vj_adv.mjs of the 2026-10-24 verifier: transitions between successive local extremes, hysteresis 0.02,
// |delta| >= 0.1 and the darker end < 0.8; maxInWindow over the transitions' frame times)
export function transitions(L, hyst = 0.02, thr = 0.1) {
  const ext = []; let dir = 0; let hi = { i: 0, v: L[0] }, lo = { i: 0, v: L[0] }, cand = null;
  for (let i = 1; i < L.length; i++) {
    const v = L[i];
    if (dir === 0) {
      if (v > hi.v) hi = { i, v };
      if (v < lo.v) lo = { i, v };
      if (hi.v - lo.v >= hyst) { if (hi.i > lo.i) { ext.push(lo); dir = 1; cand = hi; } else { ext.push(hi); dir = -1; cand = lo; } }
    } else if (dir === 1) {
      if (v > cand.v) cand = { i, v }; else if (cand.v - v >= hyst) { ext.push(cand); dir = -1; cand = { i, v }; }
    } else {
      if (v < cand.v) cand = { i, v }; else if (v - cand.v >= hyst) { ext.push(cand); dir = 1; cand = { i, v }; }
    }
  }
  if (cand) ext.push(cand);
  const tr = [];
  for (let k = 1; k < ext.length; k++) { const a = ext[k - 1], b = ext[k]; const d = b.v - a.v; if (Math.abs(d) >= thr && Math.min(a.v, b.v) < 0.8) tr.push({ from: a.i, at: b.i, d: +d.toFixed(4) }); }
  return tr;
}
export function maxInWindow(times, win) { let best = 0; for (let i = 0; i < times.length; i++) { let n = 0; for (let j = i; j < times.length && times[j] - times[i] < win; j++) n++; best = Math.max(best, n); } return best; }

// The windows (cell rectangles [x0, y0, x1, y1] of the 4 x 4 grid, inclusive): the same family gate v2 limits, built
// here on their own so the receipt does not lean on the code it judges.
export const STORM_WINDOWS = (() => {
  const w = [{ id: "full", r: [0, 0, 3, 3] }];
  for (let by = 0; by < 3; by++) for (let bx = 0; bx < 3; bx++) w.push({ id: `block${bx}${by}`, r: [bx, by, bx + 1, by + 1] });
  for (let r = 0; r < 4; r++) w.push({ id: `row${r}`, r: [0, r, 3, r] });
  for (let c = 0; c < 4; c++) w.push({ id: `col${c}`, r: [c, 0, c, 3] });
  return w;
})();
const QUADRANTS = ["block00", "block20", "block02", "block22"];

// Flashes in one window's series (per frame, 60 fps).
function countSeries(L, hyst, thr) {
  const tr = transitions(L, hyst, thr);
  const t = tr.map((x) => x.at / 60);
  const maxTr = maxInWindow(t, 1);
  // the longest flashing run: consecutive frames whose trailing second holds at least two flashes (four transitions),
  // the flashing that ITU-R BT.1702 warns about past ~5 s and gate v2 rests after
  let run = 0, best = 0, j = 0;
  for (let f = 0; f < L.length; f++) {
    while (j < t.length && t[j] <= f / 60) j++;
    let n = 0;
    for (let q = j - 1; q >= 0 && f / 60 - t[q] < 1; q--) n++;
    run = n >= 4 ? run + 1 / 60 : 0;
    best = Math.max(best, run);
  }
  let bi = 0, bn = 0;
  for (let i = 0; i < t.length; i++) { let n = 0; for (let k = i; k < t.length && t[k] - t[i] < 1; k++) n++; if (n > bn) { bn = n; bi = i; } }
  return { transitions: tr.length, max_transitions_in_1s: maxTr, max_flashes_in_1s: maxTr / 2, longest_run_s: +best.toFixed(3),
           densest: tr.slice(bi, bi + bn) };
}
// Judge one storm: cells = { L: [frame][16], R: [frame][16], N: [16] (pixels per cell) }.
export const RUN_LIMIT_S = 6.2;           // gate v2 rests after 5 s of flashing; 1.2 s of counting on top
export function judgeStorm(cells) {
  const frames = cells.L.length;
  const series = (key, r) => {
    const out = new Float64Array(frames);
    let n = 0;
    for (let cy = r[1]; cy <= r[3]; cy++) for (let cx = r[0]; cx <= r[2]; cx++) n += cells.N[cy * 4 + cx];
    for (let f = 0; f < frames; f++) {
      let s = 0;
      for (let cy = r[1]; cy <= r[3]; cy++) for (let cx = r[0]; cx <= r[2]; cx++) s += cells[key][f][cy * 4 + cx] * cells.N[cy * 4 + cx];
      out[f] = s / n;
    }
    return Array.from(out);
  };
  const windows = {};
  let worst = null, worstRed = null, longest = 0;
  for (const w of STORM_WINDOWS) {
    const L = series("L", w.r), R = series("R", w.r);
    const lum = countSeries(L, 0.02, 0.1), red = countSeries(R, 2, 20);
    windows[w.id] = { lum: { ...lum, densest: undefined }, red: { transitions: red.transitions, max_flashes_in_1s: red.max_flashes_in_1s },
                      L_min: +Math.min(...L).toFixed(4), L_max: +Math.max(...L).toFixed(4), red_max: +Math.max(...R).toFixed(3) };
    if (!worst || lum.max_flashes_in_1s > worst.max_flashes_in_1s) worst = { window: w.id, ...lum };
    if (!worstRed || red.max_flashes_in_1s > worstRed.max_flashes_in_1s) worstRed = { window: w.id, max_flashes_in_1s: red.max_flashes_in_1s, transitions: red.transitions };
    longest = Math.max(longest, lum.longest_run_s, red.longest_run_s);
  }
  const full = windows.full;
  return {
    frames, full_max_flashes_in_1s: full.lum.max_flashes_in_1s, full_transitions: full.lum.transitions,
    quadrant_max_flashes_in_1s: QUADRANTS.map((q) => windows[q].lum.max_flashes_in_1s),
    worst_window: worst.window, max_flashes_in_1s: worst.max_flashes_in_1s, densest: worst.densest,
    red_worst_window: worstRed.window, red_max_flashes_in_1s: worstRed.max_flashes_in_1s, longest_run_s: +longest.toFixed(3),
    L_full_min: full.L_min, L_full_max: full.L_max, windows,
    pass: worst.max_flashes_in_1s <= 3 && worstRed.max_flashes_in_1s <= 3 && longest <= RUN_LIMIT_S,
  };
}

// ------------------------------------------------------------------------------------------------ the storms --
function lcg(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const HOLDABLE = new Set([5, 6, 7, 8, 11]);
export const SCENARIOS = Object.freeze({
  invert10: "pad 11 Invert held; hard hits at 10/s on pads 1,2,4,6,7,12",
  oneshots15: "pads 1,2,4,12 hard at 15/s",
  oneshots5: "pads 1,2,4,12 hard at 5/s",
  nozoom15: "pads 1,2,4 hard at 15/s",
  all12: "all 12 pads hard, a hit every 3 frames (20/s)",
  flashedge: "pad 3 white flash every 3 frames: the gate grants it at its own edge (1/3 s apart)",
  flash24: "pad 3 white flash every 24 frames (2.5/s)",
});
export function stormSchedule(name, frames, seed = 7) {
  const R = lcg(seed), out = [];
  const pick = (pads) => pads[Math.floor(R() * pads.length)];
  if (name === "invert10") {
    out.push({ f: 0, pad: 11, vel: 1, hold: frames + 5 });
    for (let f = 30; f < frames; f += 6) out.push({ f, pad: pick([1, 2, 4, 6, 7, 12]), vel: 0.9 + 0.1 * R(), hold: 4 });
  } else if (name === "oneshots15" || name === "oneshots5" || name === "nozoom15") {
    const pads = name === "nozoom15" ? [1, 2, 4] : [1, 2, 4, 12];
    const step = name === "oneshots5" ? 12 : 4;
    for (let f = 0; f < frames; f += step) out.push({ f, pad: pick(pads), vel: 1, hold: 4 });
  } else if (name === "all12") {
    const pads = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    for (let f = 0; f < frames; f += 3) { const pad = pick(pads); out.push({ f, pad, vel: 0.85 + 0.15 * R(), hold: HOLDABLE.has(pad) ? 18 + Math.floor(R() * 30) : 4 }); }
  } else if (name === "flashedge" || name === "flash24") {
    const step = name === "flashedge" ? 3 : 24;
    for (let f = 0; f < frames; f += step) out.push({ f, pad: 3, vel: 1, hold: 2 });
  } else throw new Error(`unknown storm ${name}`);
  return out;
}

// The page's own code (evaluated in the vj page, on the virtual clock): one storm, the canvas read every frame.
export const STORM_PAGE = String.raw`(() => {
  if (window.__storm) return true;
  const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  const canvas = document.getElementById("gl");
  const gl = canvas.getContext("webgl2");
  let buf = null;
  function cells() {
    const w = canvas.width, h = canvas.height, n = w * h * 4;
    if (!buf || buf.length !== n) buf = new Uint8Array(n);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    const bx = [0, 1, 2, 3, 4].map((c) => Math.floor(c * w / 4)), by = [0, 1, 2, 3, 4].map((c) => Math.floor(c * h / 4));
    const L = new Float64Array(16), R = new Float64Array(16), N = new Float64Array(16);
    for (let y = 0; y < h; y++) {
      const cy = y >= by[3] ? 3 : y >= by[2] ? 2 : y >= by[1] ? 1 : 0;
      for (let cx = 0; cx < 4; cx++) {
        let l = 0, r = 0;
        for (let x = bx[cx], i = (y * w + bx[cx]) * 4; x < bx[cx + 1]; x++, i += 4) {
          const R8 = buf[i], G8 = buf[i + 1], B8 = buf[i + 2];
          const lr = LUT[R8], lg = LUT[G8], lb = LUT[B8];
          l += 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
          const s = R8 + G8 + B8;
          if (s > 0 && R8 / s >= 0.8) r += Math.max(0, (lr - lg - lb) * 320);
        }
        const c = cy * 4 + cx;
        L[c] += l; R[c] += r; N[c] += bx[cx + 1] - bx[cx];
      }
    }
    return { L: Array.from(L, (v, c) => +(v / N[c]).toFixed(5)), R: Array.from(R, (v, c) => +(v / N[c]).toFixed(3)), N: Array.from(N) };
  }
  function run(schedule, frames) {
    const F = 1000 / 60, rel = [], out = { L: [], R: [], N: null };
    const st0 = window.__vj.stats();
    for (let f = 0; f < frames; f++) {
      for (const r of rel) if (r.f === f) window.__vj.release(r.pad);
      for (const s of schedule) if (s.f === f) { window.__vj.press(s.pad, s.vel); rel.push({ f: f + s.hold, pad: s.pad }); }
      window.__vt.step(F);
      const c = cells();
      out.L.push(c.L); out.R.push(c.R); out.N = c.N;
    }
    for (const r of rel) if (r.f >= frames) window.__vj.release(r.pad);
    const st1 = window.__vj.stats();
    out.gate = { granted: st1.flash.granted - st0.flash.granted, refused: st1.flash.refused - st0.flash.refused, max_in_any_second: st1.flash.maxInAnyWindow };
    out.impact_hits = st1.impact ? st1.impact.hits - st0.impact.hits : null;
    out.errors = window.__vj.errors();
    if (window.__vj.limiter) { const l = window.__vj.limiter(); out.limiter = l.on ? { on: true, format: l.format, leaks: l.leaks, frames: l.frames, rest: l.rest, run: l.run } : { on: false, error: l.error }; }
    else out.limiter = null;
    return out;
  }
  window.__storm = { run, cells };
  return true;
})()`;

// One storm in a page already loaded on the virtual clock (ev evaluates in it). Returns the judged result.
export async function runStormInPage(ev, scenario, frames, seed = 7) {
  await ev(STORM_PAGE);
  const sch = stormSchedule(scenario, frames, seed);
  const raw = await ev(`window.__storm.run(${JSON.stringify(sch)}, ${frames})`, 600000);
  const judged = judgeStorm(raw);
  // a page that has gate v2 must be running it (a shader that fails to compile leaves the page in its safe mode: that is
  // not what is being judged)
  const limiterDown = !!(raw.limiter && raw.limiter.on === false);
  return { scenario, presses: sch.length, ...judged, pass: judged.pass && !limiterDown, limiter_down: limiterDown,
           gate: raw.gate, impact_hits: raw.impact_hits, limiter: raw.limiter, page_errors: raw.errors };
}

// The virtual clock (vj_impact's), installed in the vj page before its modules run; ?realclock=1 keeps the real one.
export const VIRTUAL_CLOCK = `(() => {
  if (!/\\/web\\/vj\\.html$/.test(location.pathname) || /[?&]realclock=1/.test(location.search)) return;
  let vt = 20000;
  const q = [];
  performance.now = () => vt;
  window.requestAnimationFrame = (cb) => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__vt = { step(ms) { vt += ms; const cbs = q.splice(0, q.length); for (const cb of cbs) cb(vt); return vt; }, now: () => vt };
})();`;

// ------------------------------------------------------------------------------------------------- the CLI --
async function main() {
  const { values: opt } = parseArgs({ options: {
    web: { type: "string", default: resolve(REPO, "arsenal", "web") },
    label: { type: "string", default: "run" },
    sets: { type: "string", default: "vj-reactor,vj-hyperspace,vj-aurora-curtains,vj-led-wall" },
    scenarios: { type: "string", default: Object.keys(SCENARIOS).join(",") },
    seconds: { type: "string", default: "10" },
    seed: { type: "string", default: "7" },
    phases: { type: "string", default: "storm,calm,parity,bench" },
    port: { type: "string", default: "8975" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    width: { type: "string", default: "640" },
    height: { type: "string", default: "360" },
    "lock-dir": { type: "string", default: LOCK_DIR },
    "gpu-wait-min": { type: "string", default: "6" },
    "burst-s": { type: "string", default: "150" },
    // the frametime phase: other copies of the page to time against this one, interleaved in one browser (label=dir,...)
    "compare-webs": { type: "string", default: "" },
    reps: { type: "string", default: "3" },
    query: { type: "string", default: "" },   // appended to every page load (experiments)
  } });
  const WEB = resolve(opt.web);
  const OTHER = opt["compare-webs"].split(",").filter(Boolean).map((x) => { const [label, ...dir] = x.split("="); return { label, dir: resolve(dir.join("=")) }; });
  const PORT0 = Number(opt.port);
  if (PORT0 === 8793 || PORT0 === 8794 || !(PORT0 >= 8900 && PORT0 <= 8999)) { console.log(`ERROR port ${PORT0}: test band 8900-8999 only (8793 and 8794 are Daniel's)`); process.exit(2); }
  const W = Number(opt.width), H = Number(opt.height);
  const FRAMES = Math.round(Number(opt.seconds) * 60);
  const SETS = opt.sets.split(",").map((s) => s.trim()).filter((s) => /^[a-z0-9][a-z0-9-]{1,40}$/.test(s));
  const SCN = opt.scenarios.split(",").map((s) => s.trim()).filter((s) => SCENARIOS[s]);
  const PHASES = opt.phases.split(",").map((s) => s.trim());
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
  const outDir = join(opt.out, `vj-storm-${opt.label}-${stamp}`);
  mkdirSync(outDir, { recursive: true });
  const report = {
    api: "arsenal.receipt/v0", lane: "vj-storm", label: opt.label, title: "VJ pad storms on a 60 fps virtual clock: flashes in the frames shown",
    started_at: new Date().toISOString(), web: WEB, viewport: { width: W, height: H }, frames: FRAMES, seed: Number(opt.seed),
    git: null, chrome: null, webgl: null, renderer_check: null,
    method: {
      clock: "virtual: performance.now and requestAnimationFrame replaced; one frame per 1000/60 ms step",
      measure: "the canvas read every frame (after every layer and gate v2); per 4 x 4 cell: mean relative luminance (sRGB LUT, WCAG weights) and mean WCAG red quantity (R/(R+G+B) >= 0.8 on 8-bit values, max(0, R-G-B) x 320 linear)",
      windows: STORM_WINDOWS.map((w) => w.id),
      counter: "the 2026-10-24 verifier's, verbatim: hysteresis 0.02, |delta| >= 0.1, darker end < 0.8, counted at the later turning point; flashes = transitions / 2; red: hysteresis 2, swing 20",
      verdict: `every window <= 3 flashes in any second, red <= 3, longest flashing run <= ${RUN_LIMIT_S} s`,
    },
    scenarios: Object.fromEntries(SCN.map((s) => [s, SCENARIOS[s]])), sets: {}, parity: null, bench: null, bursts: [],
    console: [], exceptions: [],
    not_measured: [
      "the real GPU: SwiftShader draws every frame on the CPU; the virtual clock makes the timing exact, not the speed",
      "a person: the counter is the verifier's (WCAG 2.3.1 / ITU-R BT.1702 shaped); stripes and patterns are not counted",
      "music: no engine and no demo (the sets run on time alone), so beat-driven light is not in these storms",
    ],
  };
  try { report.git = spawnSync("git", ["rev-parse", "--short", "HEAD"], { cwd: WEB, encoding: "utf8" }).stdout.trim(); } catch { /* no git */ }
  const save = () => writeFileSync(join(outDir, "receipt.json"), JSON.stringify(report, null, 2));

  const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                  ".css": "text/css; charset=utf-8", ".json": "application/json", ".frag": "text/plain; charset=utf-8",
                  ".glsl": "text/plain; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml" };
  const web = createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    if (url.pathname === "/favicon.ico") { res.writeHead(204); res.end(); return; }
    const m = /^\/(web|w\d+)\//.exec(url.pathname);
    const root = m ? (m[1] === "web" ? WEB : (OTHER[Number(m[1].slice(1))] || {}).dir) : null;
    if (!root) { res.writeHead(404); res.end(); return; }
    const target = resolve(root, decodeURIComponent(url.pathname.slice(m[0].length)));
    if (!(target + sep).startsWith(root + sep)) { res.writeHead(404); res.end(); return; }
    try { const body = readFileSync(target); res.writeHead(200, { "Content-Type": TYPES[extname(target).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" }); res.end(body); }
    catch { res.writeHead(404); res.end(); }
  });
  let PORT = PORT0;
  for (; PORT <= 8999; PORT++) {
    if (PORT === 8793 || PORT === 8794) continue;
    try { await new Promise((ok, fail) => { web.once("error", fail); web.listen(PORT, "127.0.0.1", () => { web.off("error", fail); ok(); }); }); break; }
    catch (e) { if (e.code !== "EADDRINUSE") throw e; }
  }

  function connect(wsUrl) {
    return new Promise((ok, fail) => {
      const ws = new WebSocket(wsUrl); let nextId = 1; const pending = new Map(); const listeners = [];
      ws.onmessage = (ev) => { const msg = JSON.parse(ev.data);
        if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result); }
        else if (msg.method) for (const l of listeners) l(msg); };
      ws.onopen = () => ok({ send: (method, params = {}, sessionId) => new Promise((res, rej) => { const id = nextId++; pending.set(id, { res, rej });
        ws.send(JSON.stringify(sessionId ? { id, method, params, sessionId } : { id, method, params })); }), on: (fn) => listeners.push(fn), close: () => ws.close() });
      ws.onerror = () => fail(new Error("websocket error"));
    });
  }
  async function waitFor(fn, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { try { const v = await fn(); if (v) return v; } catch { /* not yet */ } await delay(150); } throw new Error(`timed out: ${what}`); }

  async function burst(name, body) {
    const t0 = Date.now();
    const profile = join(tmpdir(), `arsenal-vj-storm-${stamp}-${name}-${process.pid}`);
    let gpu = null, chrome = null, browser = null;
    const entry = { name, seconds: null, error: null };
    report.bursts.push(entry);
    try {
      gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `vj_storm ${name} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000 });
      const held = Date.now();   // the burst's time runs from the lock, not from the wait for it
      chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0",
        `--user-data-dir=${profile}`, `--window-size=${W},${H}`, "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore", windowsHide: true });
      const [p, w] = await waitFor(() => { try { const [a, b] = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split(/\r?\n/); return a && b ? [a, b] : null; } catch { return null; } }, 30000, "DevToolsActivePort");
      browser = await connect(`ws://127.0.0.1:${p}${w}`);
      report.chrome = (await browser.send("Browser.getVersion")).product;
      const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
      const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });
      const S = (m, params = {}) => browser.send(m, params, sessionId);
      browser.on((msg) => {
        if (msg.sessionId !== sessionId) return;
        const q = msg.params;
        if (msg.method === "Runtime.exceptionThrown") report.exceptions.push({ burst: name, text: q.exceptionDetails.exception?.description || q.exceptionDetails.text });
        if (msg.method === "Runtime.consoleAPICalled" && (q.type === "error" || q.type === "warning")) report.console.push({ burst: name, text: q.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300) });
      });
      await S("Runtime.enable"); await S("Page.enable");
      await S("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
      await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
      const ev = async (expression) => { const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
        if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
      const load = async (query, root = "web") => {
        await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/${root}/vj.html?${query}${opt.query ? `&${opt.query}` : ""}` });
        await waitFor(() => ev("!!(window.__vj && window.__vj.ready)"), 240000, `the vj page (${query})`);
        // gate v2 compiles in the background (the page is in its safe mode until it links): wait for it, or its error
        await waitFor(() => ev("(() => { const l = window.__vj.stats().limiter; return !l || l.on || !!l.error; })()"), 120000, "gate v2's programs");
        if (!report.webgl) {
          report.webgl = await ev(`(() => { const g = document.getElementById("gl").getContext("webgl2"); const d = g.getExtension("WEBGL_debug_renderer_info"); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); })()`);
          report.renderer_check = judgeRenderer(report.webgl);
        }
        if (!judgeRenderer(report.webgl).ok) throw new Error(`refusing to judge: not SwiftShader (${report.webgl})`);
      };
      await body({ ev, load, deadline: held + Number(opt["burst-s"]) * 1000 });
    } catch (err) { entry.error = String((err && err.stack) || err); console.log(`ERROR [${name}]`, entry.error); }
    finally {
      entry.seconds = Math.round((Date.now() - t0) / 100) / 10;
      try { await browser?.send("Browser.close"); } catch { /* gone */ }
      await delay(600);
      if (chrome && chrome.exitCode === null) spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
      gpu?.release();
      await delay(300);
      try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
      save();
    }
  }

  // ---------------------------------------------------------------------------------------------- storms --
  if (PHASES.includes("storm")) {
    for (const set of SETS) {
      report.sets[set] = report.sets[set] || {};
      let tries = 0;
      while (SCN.some((s) => !report.sets[set][s]) && tries++ < SCN.length + 2) {
        await burst(`storm-${set}-${tries}`, async ({ ev, load, deadline }) => {
          for (const scenario of SCN) {
            if (report.sets[set][scenario]) continue;
            if (Date.now() > deadline) { console.log(`[storm] ${set}: burst time is up; the next burst continues`); return; }
            await load(`engine=off&hud=0&watchdog=0&sets=${set}`);
            await ev("(() => { for (let i = 0; i < 30; i++) window.__vt.step(1000 / 60); return true; })()");   // half a second in
            const r = await runStormInPage(ev, scenario, FRAMES, Number(opt.seed));
            report.sets[set][scenario] = { ...r, windows: undefined, window_detail: r.windows };
            const lim = r.limiter ? (r.limiter.on ? `limiter leaks ${r.limiter.leaks}` : `limiter OFF (${r.limiter.error})`) : "no limiter";
            console.log(`[storm] ${set} ${scenario}: full ${r.full_max_flashes_in_1s}/s, worst ${r.max_flashes_in_1s}/s (${r.worst_window}), quadrants ${r.quadrant_max_flashes_in_1s.join(" ")}, red ${r.red_max_flashes_in_1s}, run ${r.longest_run_s}s, L ${r.L_full_min}-${r.L_full_max}, gate ${r.gate.granted}/${r.gate.max_in_any_second}, ${lim}${r.pass ? "" : "  << FAIL"}`);
            save();
          }
        });
      }
    }
  }

  // ------------------------------------------------------------------------------------------------ calm --
  // The other side of the limit: a set under the page's own demo music (beats, chords, energy; no pads) should not be held
  // at all. Every 15 frames the limiter's own state is read back (how many of its 36 trackers held the frame before, the
  // forced rest), and every frame is counted as in the storms.
  if (PHASES.includes("calm")) {
    report.calm = report.calm || {};
    for (const set of SETS) {
      await burst(`calm-${set}`, async ({ ev, load }) => {
        await load(`engine=off&hud=0&watchdog=0&demo=1&demopads=0&sets=${set}`);
        await ev(STORM_PAGE);
        const has = await ev("!!(window.__vj.limiter)");
        const on = has ? await ev("window.__vj.limiter().on === true") : null;
        const r = await ev(`(() => { const out = { L: [], R: [], N: null, held: [], rest: 0 };
          for (let f = 0; f < ${FRAMES * 2}; f++) {
            window.__vt.step(1000 / 60);
            const c = window.__storm.cells(); out.L.push(c.L); out.R.push(c.R); out.N = c.N;
            if (${has} && f % 15 === 14) { const l = window.__vj.limiter(); out.held.push(l.held); if (l.rest > 0) out.rest++; }
          }
          return out; })()`);
        const j = judgeStorm(r);
        const heldSamples = r.held.filter((h) => h > 0).length;
        report.calm[set] = { frames: r.L.length, max_flashes_in_1s: j.max_flashes_in_1s, worst_window: j.worst_window, red: j.red_max_flashes_in_1s,
                             limiter_on: on, samples: r.held.length, samples_with_a_window_held: heldSamples, samples_resting: r.rest,
                             mean_held_trackers: r.held.length ? +(r.held.reduce((a, b) => a + b, 0) / r.held.length).toFixed(2) : null };
        console.log(`[calm] ${set}: ${JSON.stringify(report.calm[set])}`);
      });
    }
  }

  // ---------------------------------------------------------------------------------------------- parity --
  if (PHASES.includes("parity")) {
    await burst("parity", async ({ ev, load }) => {
      await load("engine=off&hud=0&watchdog=0&sets=vj-reactor");
      const has = await ev("!!(window.__vj.limiterCells)");
      if (!has) { report.parity = { skipped: "this page has no gate v2 (window.__vj.limiterCells)" }; return; }
      const gate = await import(pathToFileURL(join(WEB, "vj-gate.js")).href);
      const results = [];
      for (const [name, gen] of Object.entries(paritySequences(gate))) {
        const seq = gen();
        await ev("window.__vj.limiterReset()");
        const gpu = await ev(`(() => { const seq = ${JSON.stringify(seq.map((c) => Array.from(c)))}; const out = [];
          for (const c of seq) { const r = window.__vj.limiterCells(c, 1 / 60); out.push({ a: r.a, k: r.k, beta: r.betaNow, held: r.trackers.map((t) => t[5]), leaks: r.leaks, trk: r.trackers }); }
          window.__vj.limiterReset(); return out; })()`);
        const model = new gate.FlashLimiter();
        let maxA = 0, maxK = 0, maxB = 0, heldDiff = 0, heldFrames = 0, frames = 0, first = null;
        for (let f = 0; f < seq.length; f++) {
          const m = model.step(seq[f], 1 / 60);
          const g = gpu[f];
          for (let i = 0; i < 25; i++) { maxA = Math.max(maxA, Math.abs(m.a[i] - g.a[i])); maxK = Math.max(maxK, Math.abs(m.k[i] - g.k[i])); }
          maxB = Math.max(maxB, Math.abs(m.beta - g.beta));
          let d = 0;
          // the first frame where any tracker's state differs by more than 1e-4 (an earlier, quieter divergence)
          if (!first && g.trk) for (let t = 0; t < g.trk.length && !first; t++) for (let q = 0; q < gate.TRACKER_FLOATS && !first; q++) {
            if (Math.abs(model.state[t * gate.TRACKER_FLOATS + q] - g.trk[t][q]) > 1e-4) first = { frame: f, tracker: t, field: q, kind: "state",
              model: Array.from(model.state.slice(t * gate.TRACKER_FLOATS, (t + 1) * gate.TRACKER_FLOATS)).map((x) => +x.toFixed(6)),
              gpu: g.trk[t].map((x) => +x.toFixed(6)), want: +model.want[t].toFixed(6), shown: +model.shown[t].toFixed(6),
              lo: model.lo[t], hi: model.hi[t], level: model.level ? model.level[t] : null, a: Array.from(m.a).map((x) => +x.toFixed(5)), ga: g.a.map((x) => +x.toFixed(5)) };
          }
          for (let t = 0; t < g.held.length; t++) {
            const mh = model.level ? model.level[t] : (model.mode[t] === gate.MODE.HELD ? 1 : 0);
            if (mh !== Math.round(g.held[t])) {
              d++;
              // the first divergence, for the record: both twins' tracker state after that frame
              if (!first) first = { frame: f, tracker: t, model: Array.from(model.state.slice(t * gate.TRACKER_FLOATS, (t + 1) * gate.TRACKER_FLOATS)).map((x) => +x.toFixed(5)),
                                    gpu: g.trk[t].map((x) => +x.toFixed(5)), want: +model.want[t].toFixed(5), shown: +model.shown[t].toFixed(5) };
            }
            heldFrames += mh > 0 ? 1 : 0;
          }
          if (d) heldDiff++;
          frames++;
        }
        const row = { sequence: name, frames, max_abs_gain: +maxA.toFixed(5), max_abs_lift: +maxK.toFixed(5), max_abs_beta: +maxB.toFixed(5),
                      frames_with_held_mismatch: heldDiff, held_tracker_frames: heldFrames, model_leaks: model.leaks, first_divergence: first };
        results.push(row);
        console.log(`[parity] ${name}: ${JSON.stringify(row)}`);
      }
      report.parity = { results, pass: results.every((r) => r.max_abs_gain < 0.02 && r.max_abs_lift < 0.02 && r.max_abs_beta < 0.02 && r.frames_with_held_mismatch <= Math.ceil(0.02 * r.frames)) };
    });
  }

  // ----------------------------------------------------------------------------------------------- bench --
  if (PHASES.includes("bench")) {
    await burst("bench", async ({ ev, load }) => {
      report.bench = {};
      for (const set of SETS.slice(0, 2)) {
        await load(`realclock=1&engine=off&hud=0&watchdog=0&sets=${set}`);
        await delay(2500);
        const has = await ev("!!(window.__vj.limiterBench)");
        if (!has) { report.bench[set] = { skipped: "no gate v2" }; continue; }
        const r = await ev("window.__vj.limiterBench(30)");
        if (!r) { report.bench[set] = { skipped: "gate v2 is not running" }; report.exceptions.push({ burst: "bench", text: `gate v2 not running on ${set}` }); continue; }
        // the real-clock frame interval with the page running (rAF), for context
        const ft = await ev(`new Promise((done) => { const ts = []; const tick = (t) => { ts.push(t); if (ts.length < 61) requestAnimationFrame(tick); else { const g = ts.slice(1).map((v, i) => v - ts[i]).sort((a, b) => a - b); done({ p50: g[30], mean: g.reduce((a, b) => a + b, 0) / g.length }); } }; requestAnimationFrame(tick); })`);
        report.bench[set] = { ...r, frame_interval_ms: ft };
        console.log(`[bench] ${set}: limiter ${r.limiter_ms.toFixed(2)} ms vs plain copy ${r.copy_ms.toFixed(2)} ms at ${r.width}x${r.height}; frame interval p50 ${ft.p50.toFixed(1)} ms`);
      }
    });
  }

  // ------------------------------------------------------------------------------------------- frametime --
  // The whole frame's cost on SwiftShader, for any build (master, the impact pass, this one): the page's own frames run
  // back to back (requestAnimationFrame taken over after load), each fenced by a one-pixel readPixels, 40 of them.
  if (PHASES.includes("frametime")) {   // (with --compare-webs the other builds are timed in the same browser, interleaved)
    report.frametime = {};
    const builds = [{ label: opt.label, root: "web" }, ...OTHER.map((o, i) => ({ label: o.label, root: `w${i}` }))];
    for (let rep = 0; rep < Number(opt.reps); rep++) await burst(`frametime-${rep + 1}`, async ({ ev, load }) => {
      // the order rotates rep to rep, so no build always runs first (or right after a launch)
      for (const b of builds.map((_, i) => builds[(i + rep) % builds.length])) for (const set of SETS.slice(0, 2)) {
        await load(`realclock=1&engine=off&hud=0&watchdog=0&sets=${set}`, b.root);
        await delay(2000);
        const r = await ev(`new Promise((done) => {
          const gl = document.getElementById("gl").getContext("webgl2"), px = new Uint8Array(4);
          let cbs = [];
          window.requestAnimationFrame = (cb) => { cbs.push(cb); return 1; };
          setTimeout(() => {
            const run = (n) => { const ts = []; for (let i = 0; i < n; i++) { const t = performance.now(); const q = cbs; cbs = []; for (const cb of q) cb(performance.now());
              gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); ts.push(performance.now() - t); } return ts; };
            run(10);
            const ts = run(40).sort((a, b) => a - b);
            done({ n: ts.length, p50: +ts[20].toFixed(2), mean: +(ts.reduce((a, b) => a + b, 0) / ts.length).toFixed(2), p90: +ts[36].toFixed(2) });
          }, 300);
        })`);
        ((report.frametime[b.label] = report.frametime[b.label] || {})[set] = report.frametime[b.label][set] || []).push(r);
        console.log(`[frametime] ${b.label} ${set} rep ${rep + 1}: p50 ${r.p50} ms, mean ${r.mean} ms, p90 ${r.p90} ms (back to back, fenced)`);
      }
    });
    // per build and set: the median of the reps' p50s
    report.frametime_summary = Object.fromEntries(Object.entries(report.frametime).map(([label, sets]) => [label,
      Object.fromEntries(Object.entries(sets).map(([set, runs]) => { const v = runs.map((x) => x.p50).sort((a, b) => a - b); return [set, v[Math.floor(v.length / 2)]]; }))]));
    console.log(`[frametime] median p50 per build: ${JSON.stringify(report.frametime_summary)}`);
  }

  // --------------------------------------------------------------------------------------------- verdict --
  const rows = [];
  for (const [set, scn] of Object.entries(report.sets)) for (const [name, r] of Object.entries(scn)) rows.push({ set, name, r });
  report.verdict = {
    storms: rows.length, storms_expected: PHASES.includes("storm") ? SETS.length * SCN.length : 0,
    failed: rows.filter((x) => !x.r.pass).map((x) => `${x.set} ${x.name}: ${x.r.max_flashes_in_1s}/s in ${x.r.worst_window}, red ${x.r.red_max_flashes_in_1s}, run ${x.r.longest_run_s}s`),
    max_flashes_in_1s: Math.max(0, ...rows.map((x) => x.r.max_flashes_in_1s)),
    max_full_frame_flashes_in_1s: Math.max(0, ...rows.map((x) => x.r.full_max_flashes_in_1s)),
    page_exceptions: report.exceptions.length,
    calm: report.calm ? Object.fromEntries(Object.entries(report.calm).map(([k, v]) => [k, { max_flashes_in_1s: v.max_flashes_in_1s, held_samples: v.samples_with_a_window_held, rest_samples: v.samples_resting }])) : null,
    calm_failed: report.calm ? Object.entries(report.calm).filter(([, v]) => v.max_flashes_in_1s > 3 || v.red > 3 || v.limiter_on === false).map(([k]) => k) : [],
  };
  report.verdict.pass = report.verdict.storms === report.verdict.storms_expected && report.verdict.failed.length === 0 &&
    report.verdict.calm_failed.length === 0 &&
    report.exceptions.length === 0 && (!report.parity || report.parity.skipped || report.parity.pass);
  report.finished_at = new Date().toISOString();
  save();
  console.log(`\nVJ storm receipt (${opt.label}): ${report.verdict.storms}/${report.verdict.storms_expected} storms, worst ${report.verdict.max_flashes_in_1s} flashes/s (full frame ${report.verdict.max_full_frame_flashes_in_1s}), failed ${report.verdict.failed.length}${report.parity ? `, parity ${report.parity.skipped ? "skipped" : report.parity.pass ? "PASS" : "FAIL"}` : ""} -> ${report.verdict.pass ? "PASS" : "FAIL"}`);
  for (const f of report.verdict.failed) console.log(`  FAIL ${f}`);
  console.log(`receipt: ${join(outDir, "receipt.json")}`);
  web.close();
  process.exit(report.verdict.pass ? 0 : 1);
}

// Synthetic cell sequences for the parity phase (the JS twin's input layout, vj-gate.js cellIndex).
function paritySequences(gate) {
  const { cellSums } = gate;
  const N = 360;
  return {
    square10: () => Array.from({ length: N }, (_, f) => cellSums(() => (Math.floor(f / 3) % 2 ? 0.5 : 0.05), () => 0, 32, 32)),
    quadrant10: () => Array.from({ length: N }, (_, f) => cellSums((u, v) => (u < 0.5 && v < 0.5 ? (Math.floor(f / 3) % 2 ? 0.6 : 0.05) : 0.1), () => 0, 32, 32)),
    redcentre: () => Array.from({ length: N }, (_, f) => cellSums((u, v) => 0.1, (u, v) => (Math.abs(u - 0.5) < 0.25 && Math.abs(v - 0.5) < 0.25 && Math.floor(f / 4) % 2 ? 0.3 : 0), 32, 32)),
    random: () => {
      const R = lcg(11), hits = [];
      for (let f = 0; f < N; f += 2 + Math.floor(R() * 8)) hits.push([f, 0.1 + 0.4 * R(), R() < 0.3 ? -1 : 1, R(), R()]);
      return Array.from({ length: N }, (_, f) => cellSums((u, v) => {
        let val = 0.2;
        for (const [h, amp, sg, cx, cy] of hits) if (h <= f && f - h < 30) { const d = Math.hypot(u - cx, v - cy); val += sg * amp * Math.exp(-((f - h) / 60) / 0.06) * Math.exp(-d * d * 6); }
        return Math.max(0, Math.min(1, val));
      }, () => 0, 32, 32));
    },
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((err) => { console.log("ERROR", err && err.stack || err); process.exit(1); });
}
