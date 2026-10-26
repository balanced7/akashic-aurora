// VJ storm receipt: pad storms on a 60 fps VIRTUAL clock, the frames as the viewer gets them, and flashes counted the way
// the adversarial verifiers counted them -- in windows the limiter does NOT use. In a private headless Chrome forced onto
// SwiftShader (the CPU: this host's AMD driver has a crash history, so no frame here is ever drawn on the GPU), under
// the house GPU lock, in bursts under three minutes with the lock released between them.
//
//   node arsenal/lanes/vj_storm.mjs [--web <dir>] [--label L] [--phases storm,safe,cpu,adv,hires,calm,parity,meter,bench]
//                                   [--sets id,id] [--scenarios a,b] [--seconds 10] [--width 640 --height 360]
//                                   [--hires 1280x720,1920x1080] [--port 8975] [--out <dir>] [--lock-dir <dir>]
//
// WHY. 2026-10-24: the impact pass threw light that never asks the FlashGate; a verifier counted up to 6.5 flashes a
// second in pad storms. Gate v2 (the final-output limiter) was built, and this receipt certified it with 28 of 28 storms
// passing. 2026-10-25, the round-2 verifier: the receipt had certified the limiter with the limiter's OWN geometry (the
// same 18 windows of a 4 x 4 grid it controls), only at 640 x 360, only with the limiter running, and only on the pads'
// own content. A quarter-screen rectangle off that grid flashed 8.5 times a second; 1-px lines flickered the whole frame
// at 10 a second at 1280 x 720 (the meter skipped every second column); without its limiter the page put 9 flashes a
// second on the screen. So now:
//   WINDOWS   flashes are counted on a 64 x 36 measuring grid of the canvas (exact pixel means), in every rectangle of a
//             quarter of the screen or more of twelve shapes (16:9, columns, strips, squares, in between) at EVERY offset of
//             that grid (4726 windows; the limiter's own grid is 8 x 8, so almost none of these is one of its windows),
//             plus the whole frame. Luminance and the WCAG red quantity, each counted two ways: transitions in any second
//             (/ 2 = flashes) and strict pairs of opposing transitions.
//   SIZES     the storms at --width x --height (640 x 360 by default) and, in the hires phase, at show sizes (1280 x 720
//             and 1920 x 1080 by default).
//   MODES     the limiter deciding on the GPU (the default), deciding on the CPU (?limiter=cpu: the JS twin on cell sums
//             read back, the page's fallback when the GPU decision cannot link), handing over from the CPU to the GPU
//             mid-storm (?limiter=late: as a slow compile on a real GPU would) and absent (?limiter=off: the page's safe
//             mode, which refuses every pad effect and cuts scenes at most once a second as crossfades).
//   CONTENT   the pads' own storms (the scenarios below), the look at full under a storm, set cuts, and adversarial
//             presets this receipt serves itself (never committed as presets): a rectangle of 25.6 % off the grid
//             flickering at 8 Hz (dim and bright), 1-px lines on odd columns at 10 Hz, a 3 x 3 checkerboard and a 3 x 6
//             checkerboard off the grid in anti-phase, a red flicker, a red / grey swap.
// THE COUNTER (the 2026-10-24 verifier's, kept verbatim below): turning points with a hysteresis of 0.02, a transition is
// a swing of 0.1 or more between turning points whose darker end is under 0.8, counted at its later turning point.
// Red: hysteresis 2, swing 20 (on the x 320 scale), no darker-end exemption (any change to or from saturated red counts).
// THE VERDICT, per run: in every window at most 6 transitions in any second (3 flashes) and at most 3 strict pairs, the
// same for red, no flashing run (every trailing second holding two flashes) longer than gate v2's rest allows (5 s, plus
// 1.2 s of counting), the limiter in the mode asked for (or, in the safe mode, absent and refusing pads), no page error.
// THE OTHER PHASES. calm: each set under the page's own demo music, no pads (should never need holding). parity: the
// page's GPU decision against its JS twin (vj-gate.js FlashLimiter) on the same synthetic cell sums, frame by frame.
// meter: the limiter's cells against the canvas's own pixels, every pixel, at every size (1-px lines on odd columns: a
// meter that skips pixels misses them). bench: the limiter's stages, fenced, at every size. frametime: whole frames
// against other builds (--compare-webs label=dir,...).
// Writes state/arsenal/receipts/vj-storm-<label>-<stamp>/receipt.json; exits 1 when the verdict fails. vj_verify runs a
// shorter set of these storms through runStormInPage.
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
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
// |delta| >= 0.1 and the darker end < 0.8; red with no darker-end exemption, as the round-1 verifier counted it)
export function transitions(L, hyst = 0.02, thr = 0.1, dark = 0.8) {
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
  for (let k = 1; k < ext.length; k++) { const a = ext[k - 1], b = ext[k]; const d = b.v - a.v; if (Math.abs(d) >= thr && Math.min(a.v, b.v) < dark) tr.push({ from: a.i, at: b.i, d: +d.toFixed(4) }); }
  return tr;
}
// the most transitions (by the frame of their end) inside any second: frames i..j with j - i < 60
export function maxIn1s(at, win = 60) { let best = 0, bi = -1; for (let i = 0, j = 0; i < at.length; i++) { while (at[i] - at[j] >= win) j++; if (i - j + 1 > best) { best = i - j + 1; bi = at[j]; } } return { n: best, at: bi }; }
// strict flashes: pairs of OPPOSING transitions, paired greedily in time order, the most inside any second
export function pairsIn1s(tr, win = 60) { let best = 0; for (let j = 0; j < tr.length; j++) { let pend = 0, n = 0; for (let i = j; i < tr.length && tr[i].at - tr[j].at < win; i++) { const sg = Math.sign(tr[i].d); if (pend === 0) pend = sg; else if (sg !== pend) { n++; pend = 0; } else pend = sg; } best = Math.max(best, n); } return best; }
// the longest run of frames whose trailing second holds at least k transitions (k = 4: two flashes a second), seconds
export function longestRun(at, frames, k = 4) { let run = 0, best = 0, j = 0, i = 0; for (let f = 0; f < frames; f++) { while (i < at.length && at[i] <= f) i++; while (j < i && f - at[j] >= 60) j++; run = i - j >= k ? run + 1 : 0; best = Math.max(best, run); } return best / 60; }

// ------------------------------------------------------------------------------------------- the windows --
// The measuring grid: 64 x 36 cells of the canvas (exact pixel means). The limiter meters 8 x 8 cells; these windows are
// built here on their own, so the receipt does not lean on the code it judges.
export const MEAS = Object.freeze({ GX: 64, GY: 36 });
export const STORM_SHAPES = Object.freeze([[32, 18], [16, 36], [64, 9], [48, 12], [24, 24], [40, 15], [20, 29], [56, 11],
                                           [28, 21], [36, 16], [18, 32], [44, 14]]);
export const STORM_WINDOWS = (() => {
  const out = [{ id: "full", x: 0, y: 0, w: MEAS.GX, h: MEAS.GY }];
  for (const [w, h] of STORM_SHAPES) {
    if (w * h * 4 < MEAS.GX * MEAS.GY) throw new Error(`window shape ${w}x${h} is under a quarter of the screen`);
    for (let y = 0; y + h <= MEAS.GY; y++) for (let x = 0; x + w <= MEAS.GX; x++) out.push({ id: `${w}x${h}@${x},${y}`, x, y, w, h });
  }
  return Object.freeze(out);
})();
const QUADRANTS = ["32x18@0,0", "32x18@32,0", "32x18@0,18", "32x18@32,18"];
export const RUN_LIMIT_S = 6.2;           // gate v2 rests after 5 s of flashing; 1.2 s of counting on top

// Judge one run: m = { frames, L: Uint16Array(frames x 2304) (mean luminance x 65535), R: Uint16Array (mean red / 320 x
// 65535), N: Float64Array(2304) (pixels per cell) }. Window series from per-frame prefix sums of (mean x pixels).
export function judgeStorm(m) {
  const { frames, N } = m, GX = MEAS.GX, GY = MEAS.GY, NC = GX * GY, W1 = GX + 1;
  const PL = new Float64Array(frames * W1 * (GY + 1)), PR = new Float64Array(frames * W1 * (GY + 1)), PN = new Float64Array(W1 * (GY + 1));
  for (let y = 0; y < GY; y++) { let row = 0; for (let x = 0; x < GX; x++) { row += N[y * GX + x]; PN[(y + 1) * W1 + x + 1] = PN[y * W1 + x + 1] + row; } }
  for (let f = 0; f < frames; f++) {
    const o = f * W1 * (GY + 1), c0 = f * NC;
    for (let y = 0; y < GY; y++) {
      let rl = 0, rr = 0;
      for (let x = 0; x < GX; x++) {
        const c = y * GX + x, n = N[c];
        rl += (m.L[c0 + c] / 65535) * n; rr += (m.R[c0 + c] / 65535) * 320 * n;
        PL[o + (y + 1) * W1 + x + 1] = PL[o + y * W1 + x + 1] + rl;
        PR[o + (y + 1) * W1 + x + 1] = PR[o + y * W1 + x + 1] + rr;
      }
    }
  }
  const rect = (P, o, w) => P[o + (w.y + w.h) * W1 + w.x + w.w] - P[o + w.y * W1 + w.x + w.w] - P[o + (w.y + w.h) * W1 + w.x] + P[o + w.y * W1 + w.x];
  const L = new Float64Array(frames), R = new Float64Array(frames);
  let worst = { n: -1 }, worstP = { n: -1 }, worstR = { n: -1 }, worstRP = { n: -1 }, run = { s: -1 };
  const keep = {};
  let full = null;
  for (const w of STORM_WINDOWS) {
    const n = rect(PN, 0, w);
    for (let f = 0; f < frames; f++) { const o = f * W1 * (GY + 1); L[f] = rect(PL, o, w) / n; R[f] = rect(PR, o, w) / n; }
    const tr = transitions(L), trR = transitions(R, 2, 20, Infinity);
    const at = tr.map((t) => t.at), atR = trR.map((t) => t.at);
    const mx = maxIn1s(at), mr = maxIn1s(atR), pp = pairsIn1s(tr), pr = pairsIn1s(trR);
    const rs = Math.max(longestRun(at, frames), longestRun(atR, frames));
    if (mx.n > worst.n) worst = { n: mx.n, at: mx.at, window: w.id, total: tr.length, densest: tr.filter((t) => t.at >= mx.at && t.at - mx.at < 60) };
    if (pp > worstP.n) worstP = { n: pp, window: w.id };
    if (mr.n > worstR.n) worstR = { n: mr.n, at: mr.at, window: w.id, total: trR.length };
    if (pr > worstRP.n) worstRP = { n: pr, window: w.id };
    if (rs > run.s) run = { s: rs, window: w.id };
    if (w.id === "full" || QUADRANTS.includes(w.id)) keep[w.id] = { max_transitions_in_1s: mx.n, transitions: tr.length, pairs: pp, red_max_transitions_in_1s: mr.n };
    if (w.id === "full") { let lo = Infinity, hi = -Infinity, sum = 0; for (let f = 0; f < frames; f++) { lo = Math.min(lo, L[f]); hi = Math.max(hi, L[f]); sum += L[f]; } full = { L_min: +lo.toFixed(4), L_max: +hi.toFixed(4), L_mean: +(sum / frames).toFixed(4) }; }
  }
  const pass = worst.n <= 6 && worstP.n <= 3 && worstR.n <= 6 && worstRP.n <= 3 && run.s <= RUN_LIMIT_S;
  return {
    frames, windows: STORM_WINDOWS.length,
    full_max_flashes_in_1s: keep.full.max_transitions_in_1s / 2, full_transitions: keep.full.transitions,
    quadrant_max_flashes_in_1s: QUADRANTS.map((q) => keep[q].max_transitions_in_1s / 2),
    max_transitions_in_1s: worst.n, max_flashes_in_1s: worst.n / 2, worst_window: worst.window, worst_at_frame: worst.at,
    densest: worst.densest, max_pairs_in_1s: worstP.n, worst_pairs_window: worstP.window,
    red_max_transitions_in_1s: worstR.n, red_max_flashes_in_1s: worstR.n / 2, red_worst_window: worstR.window,
    red_max_pairs_in_1s: worstRP.n, longest_run_s: +run.s.toFixed(3), longest_run_window: run.window,
    ...full, pass,
  };
}

// ------------------------------------------------------------------------------------------- the storms --
function lcg(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const HOLDABLE = new Set([5, 6, 7, 8, 11]);
// name: [what it is, how many sets the page needs (cuts), the adversarial preset it plays instead of the set (or null)]
export const SCENARIOS = Object.freeze({
  invert10: "pad 11 Invert held; hard hits at 10/s on pads 1,2,4,6,7,12",
  oneshots15: "pads 1,2,4,12 hard at 15/s",
  oneshots5: "pads 1,2,4,12 hard at 5/s",
  nozoom15: "pads 1,2,4 hard at 15/s",
  all12: "all 12 pads hard, a hit every 3 frames (20/s)",
  flashedge: "pad 3 white flash every 3 frames: the gate grants it at its own edge (1/3 s apart)",
  flash24: "pad 3 white flash every 24 frames (2.5/s)",
  lasglitch: "pads 2 (laser) and 4 (glitch) alternating at 15/s",
  lookstorm: "the look at full, every flash-capable pad (1-8, 11, 12) every 3 frames",
  cuts: "a cut to another set every 6 frames, pads 1,2,4,12 between them (the page holds three sets)",
  calmset: "the set alone on time, no pads (the safe mode's floor)",
  // Lasers v2 (2026-10-25): pad 2 is the laser engine's hit; the beams are drawn by the page's beam layer, before gate v2
  lasertiers: "pad 2 alone: soft / medium / hard hits (single, one-two, triple) a bar apart, presses within a bar (escalate, the hero), within a beat (one-two), held loops, Vibrate on half way",
  laserroll: "pad 2 rolls: presses at 8 and 16 a second (the grid-locked rolls), held loops under the stutter, military and push-pull gates from the dial, Vibrate on",
});
export const ADV = Object.freeze({
  // id: [GLSL body, what it is]
  "adv-offgrid12": ["float on = step(0.5, fract(u_time * 8.0)); vec2 p = v_uv; float inR = step(0.122, p.x) * step(p.x, 0.628) * step(0.108, p.y) * step(p.y, 0.614); outColor = vec4(vec3(inR * on * 0.42), 1.0);",
                    "a rectangle of 25.6 %, off the grid (u 0.122-0.628, v 0.108-0.614), 0 / 0.42 display at 8 Hz (the round-2 verifier's offgrid42)"],
  "adv-offgrid80": ["float on = step(0.5, fract(u_time * 8.0)); vec2 p = v_uv; float inR = step(0.122, p.x) * step(p.x, 0.628) * step(0.108, p.y) * step(p.y, 0.614); outColor = vec4(vec3(inR * on * 0.80), 1.0);",
                    "the same rectangle, bright (0 / 0.80 display)"],
  "adv-stripes": ["int x = int(gl_FragCoord.x); float line = (x % 4 == 1) ? 1.0 : 0.0; float on = step(0.5, fract(u_time * 10.0)); outColor = vec4(vec3(line * on), 1.0);",
                  "1-px lines on every fourth column (odd), on / off at 10 Hz"],
  "adv-checker3": ["vec2 c = floor(v_uv * 3.0); float par = mod(c.x + c.y, 2.0); float ph = step(0.5, fract(u_time * 6.0)); float b = abs(par - ph); outColor = vec4(vec3(mix(0.05, 0.85, b)), 1.0);",
                   "a 3 x 3 checkerboard in anti-phase at 6 Hz"],
  "adv-offchecker": ["vec2 c = floor(v_uv * vec2(3.0, 6.0) + vec2(0.01, 0.1)); float par = mod(c.x + c.y, 2.0); float ph = step(0.5, fract(u_time * 9.0)); float b = abs(par - ph); outColor = vec4(vec3(mix(0.03, 0.8, b)), 1.0);",
                     "a 3 x 6 checkerboard off the grid in anti-phase at 9 Hz"],
  "adv-red": ["float on = step(0.5, fract(u_time * 10.0)); outColor = vec4(on, 0.0, 0.0, 1.0);",
              "saturated red on / off over the whole frame at 10 Hz"],
  "adv-redgray": ["float on = step(0.5, fract(u_time * 8.0)); outColor = vec4(mix(vec3(0.4985), vec3(1.0, 0.0, 0.0), on), 1.0);",
                  "red / grey of equal luminance swapping at 8 Hz (a red flash with no luminance flash)"],
});
export function advPreset(id) {
  const a = ADV[id];
  if (!a) return null;
  return `#version 300 es\n//! {"id": "${id}", "name": "ADV ${id}", "author": "vj_storm", "tags": ["test"], "params": []}\n` +
    `precision highp float;\nuniform vec2 u_res;\nuniform float u_time;\nin vec2 v_uv;\nout vec4 outColor;\nvoid main() { ${a[0]} }\n`;
}
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
  } else if (name === "lasglitch") {
    let k = 0; for (let f = 0; f < frames; f += 4) out.push({ f, pad: [2, 4][k++ % 2], vel: 1, hold: 3 });
  } else if (name === "lookstorm") {
    out.push({ f: 0, act: "look", amount: 1 });
    for (let f = 2; f < frames; f += 3) { const pad = pick([1, 2, 3, 4, 5, 6, 7, 8, 11, 12]); out.push({ f, pad, vel: 1, hold: HOLDABLE.has(pad) ? 12 + Math.floor(R() * 20) : 3 }); }
  } else if (name === "cuts") {
    for (let f = 0; f < frames; f += 6) out.push({ f, act: "select", idsel: Math.floor(f / 6) });
    for (let f = 3; f < frames; f += 6) out.push({ f, pad: pick([1, 2, 4, 12]), vel: 1, hold: 3 });
  } else if (name === "lasertiers") {
    // 150 BPM with no engine (the laser engine's fallback tempo): a beat is 24 frames
    const vels = [0.3, 0.6, 0.95];
    let f = 6, k = 0;
    while (f < frames - 30) {
      const v = vels[k % 3];
      if (k === Math.floor(frames / 200)) out.push({ f: f - 2, act: "laser", vibrate: true });
      const kind = k % 5;
      if (kind === 3) { out.push({ f, pad: 2, vel: v, hold: 24 * 3 }); f += 24 * 5; }               // held: the section's loop
      else if (kind === 4) { for (let j = 0; j < 3; j++) out.push({ f: f + j * 36, pad: 2, vel: v, hold: 4 }); f += 36 * 3 + 60; }   // within a bar
      else if (kind === 2) { out.push({ f, pad: 2, vel: v, hold: 4 }); out.push({ f: f + 20, pad: 2, vel: v, hold: 4 }); f += 24 * 5; }   // within a beat
      else { out.push({ f, pad: 2, vel: v, hold: 4 }); f += 24 * 6; }                             // a burst, more than a bar apart
      k++;
    }
  } else if (name === "laserroll") {
    out.push({ f: 0, act: "laser", vibrate: true });
    const third = Math.floor(frames / 3);
    for (let f = 4; f < third; f += 8) out.push({ f, pad: 2, vel: 0.9, hold: 3 });                     // 8 a second
    for (let f = third; f < 2 * third - 40; f += 4) out.push({ f, pad: 2, vel: 1, hold: 2 });           // 15 a second
    const gates = ["stutter", "military", "pushpull"];
    for (let g = 0; g < 3; g++) {
      const f0 = 2 * third + g * Math.floor(third / 3);
      out.push({ f: f0, act: "laser", gate: gates[g] });
      out.push({ f: f0 + 2, pad: 2, vel: 0.95, hold: Math.floor(third / 3) - 8 });
    }
    out.push({ f: frames - 2, act: "laser", gate: "auto", vibrate: false });
  } else if (name === "calmset" || name.startsWith("adv-")) { /* nothing: the set (or the adversarial preset) alone */ }
  else throw new Error(`unknown storm ${name}`);
  return out;
}

// The page's own code (evaluated in the vj page, on the virtual clock): one run, the canvas read every frame into the
// 64 x 36 measuring grid (luminance and red, exact pixel means), quantized to 16 bits and kept for the receipt to pull.
export const STORM_PAGE = String.raw`(() => {
  if (window.__storm) return true;
  const GX = 64, GY = 36, NC = GX * GY;
  const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  const canvas = document.getElementById("gl");
  const gl = canvas.getContext("webgl2");
  let buf = null, map = null, N = null, mw = 0, mh = 0;
  const SL = new Float64Array(NC), SR = new Float64Array(NC);
  function maps(w, h) {
    if (mw === w && mh === h) return; mw = w; mh = h;
    map = new Int32Array(w * h); N = new Float64Array(NC);
    for (let y = 0; y < h; y++) { const cy = Math.floor((h - 1 - y) * GY / h);   // readPixels rows run bottom-up
      for (let x = 0; x < w; x++) { const c = cy * GX + Math.floor(x * GX / w); map[y * w + x] = c; N[c]++; } }
  }
  function measure() {
    const w = canvas.width, h = canvas.height, n = w * h; maps(w, h);
    if (!buf || buf.length !== n * 4) buf = new Uint8Array(n * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    SL.fill(0); SR.fill(0);
    for (let p = 0, i = 0; p < n; p++, i += 4) {
      const R8 = buf[i], G8 = buf[i + 1], B8 = buf[i + 2];
      const r = LUT[R8], g = LUT[G8], b = LUT[B8], c = map[p];
      SL[c] += 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const s = R8 + G8 + B8;
      if (s > 0 && R8 >= 0.8 * s) { const q = r - g - b; if (q > 0) SR[c] += q; }
    }
  }
  function run(schedule, frames) {
    const F = 1000 / 60, vj = window.__vj;
    const Lq = new Uint16Array(frames * NC), Rq = new Uint16Array(frames * NC);
    const byF = new Map(); for (const s of schedule) { if (!byF.has(s.f)) byF.set(s.f, []); byF.get(s.f).push(s); }
    const relByF = new Map();
    const st0 = vj.stats();
    const ids = vj.sets().filter((s) => s.status === "ok").map((s) => s.id);
    const t0 = Date.now();
    for (let f = 0; f < frames; f++) {
      const rs = relByF.get(f); if (rs) for (const pad of rs) vj.release(pad);
      const evs = byF.get(f);
      if (evs) for (const s of evs) {
        if (s.pad) { vj.press(s.pad, s.vel); const at = f + (s.hold || 3); if (!relByF.has(at)) relByF.set(at, []); relByF.get(at).push(s.pad); }
        else if (s.act === "select" && ids.length) vj.select(ids[s.idsel % ids.length]);
        else if (s.act === "next") vj.next();
        else if (s.act === "look" && window.__vjx) window.__vjx.setLook({ on: true, amount: s.amount });
        else if (s.act === "laser" && vj.laser) vj.laser({ vibrate: s.vibrate, gate: s.gate });
      }
      window.__vt.step(F);
      measure();
      for (let k = 0; k < NC; k++) { Lq[f * NC + k] = Math.min(65535, Math.round(SL[k] / N[k] * 65535)); Rq[f * NC + k] = Math.min(65535, Math.round(SR[k] / N[k] * 65535)); }
    }
    for (const [f, pads] of relByF) if (f >= frames) for (const pad of pads) vj.release(pad);
    const wall = Date.now() - t0;
    const b64 = (u16) => { const u8 = new Uint8Array(u16.buffer); let s = ""; for (let i = 0; i < u8.length; i += 32768) s += String.fromCharCode.apply(null, u8.subarray(i, i + 32768)); return btoa(s); };
    window.__storm.stash = { L: b64(Lq), R: b64(Rq) };
    const st1 = vj.stats();
    let lim = null;
    try { const l = vj.limiter ? vj.limiter() : null; lim = l ? (l.on ? { on: true, mode: l.mode, format: l.format, leaks: l.leaks, frames: l.frames, rest: l.rest, run: l.run } : { on: false, error: l.error }) : null; } catch (e) { lim = { error: String(e) }; }
    return { frames, N: Array.from(N), canvas: [canvas.width, canvas.height], wall_ms: wall, ms_per_frame: wall / frames,
             gate: { granted: st1.flash.granted - st0.flash.granted, refused: st1.flash.refused - st0.flash.refused, max_in_any_second: st1.flash.maxInAnyWindow },
             impact_hits: st1.impact ? st1.impact.hits - st0.impact.hits : null,
             lasers: st1.lasers && st0.lasers ? { hits: st1.lasers.hits - st0.lasers.hits, pulses: st1.lasers.pulses - st0.lasers.pulses,
                                                  over_frames: st1.lasers.overFrames - st0.lasers.overFrames, lit_frames: st1.lasers.litFrames - st0.lasers.litFrames,
                                                  max_window: st1.lasers.maxWindow, mode: st1.lasers.mode } : null,
             safe_refused: st1.limiter && st0.limiter ? (st1.limiter.safeRefused || 0) - (st0.limiter.safeRefused || 0) : null,
             limiter_stats: st1.limiter || null, limiter: lim, errors: vj.errors(), setA: st1.setA };
  }
  window.__storm = { run, measure, slice: (key, from, n) => window.__storm.stash[key].slice(from, from + n), len: (key) => window.__storm.stash[key].length };
  return true;
})()`;

// One run in a page already loaded on the virtual clock (ev evaluates in it). mode: what the page was asked for ("gpu"
// default, "cpu", "off"). Returns the judged result.
export async function runStormInPage(ev, scenario, frames, { seed = 7, mode = "gpu" } = {}) {
  await ev(STORM_PAGE);
  const sch = stormSchedule(scenario, frames, seed);
  const raw = await ev(`window.__storm.run(${JSON.stringify(sch)}, ${frames})`, 1800000);
  const pull = async (key) => { const n = await ev(`window.__storm.len(${JSON.stringify(key)})`); let s = ""; for (let i = 0; i < n; i += 1 << 20) s += await ev(`window.__storm.slice(${JSON.stringify(key)}, ${i}, ${1 << 20})`); return s; };
  const Lb = Buffer.from(await pull("L"), "base64"), Rb = Buffer.from(await pull("R"), "base64");
  const L = new Uint16Array(Lb.buffer, Lb.byteOffset, Lb.length / 2), R = new Uint16Array(Rb.buffer, Rb.byteOffset, Rb.length / 2);
  const judged = judgeStorm({ frames, L, R, N: Float64Array.from(raw.N) });
  // the limiter must be in the mode asked for (a shader that fails to compile drops the page to the CPU twin or the safe
  // mode: that is not what is being judged), and the safe mode must be refusing pads
  const lim = raw.limiter;
  let modeOk;
  if (mode === "off") modeOk = !!lim && lim.on === false && (sch.every((s) => !s.pad) || raw.safe_refused > 0);
  // ("late": the twin decides for the first two seconds and hands its state to the GPU mid-storm)
  else modeOk = !!lim && lim.on === true && (lim.mode === (mode === "late" ? "gpu" : mode) || (lim.mode === undefined && mode === "gpu"));
  const errs = (raw.errors || []).filter((e) => !(mode === "off" && e.id === "vj-limiter"));
  return { scenario, mode, presses: sch.filter((s) => s.pad).length, ...judged, pass: judged.pass && modeOk && errs.length === 0,
           mode_ok: modeOk, gate: raw.gate, impact_hits: raw.impact_hits, safe_refused: raw.safe_refused, limiter: lim, lasers: raw.lasers,
           canvas: raw.canvas, ms_per_frame: +raw.ms_per_frame.toFixed(1), page_errors: errs };
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

// The meter check, in the page: the limiter's cells (read back) against the canvas's own pixels with the limiter's cell
// boundaries and hats (8 x 8 cells, four corner sums each), on a frame the limiter left untouched.
export const METER_PAGE = String.raw`(() => {
  window.__vt.step(1000 / 60);           // a frame, read in the same task (the drawing buffer is not preserved)
  const l = window.__vj.limiter();
  if (!l || !l.on) return { error: "the limiter is not running" };
  const canvas = document.getElementById("gl"), gl = canvas.getContext("webgl2");
  const w = canvas.width, h = canvas.height, buf = new Uint8Array(w * h * 4);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
  const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  const GX = 8, GY = 8, bx = (c) => Math.floor(c * w / GX), by = (c) => Math.floor(c * h / GY);
  const sums = new Float64Array(GX * GY * 8);
  for (let y = 0; y < h; y++) {          // GL rows: y = 0 is the bottom row, the meter's row 0 too
    let cy = 0; for (let k = 1; k < GY; k++) if (y >= by(k)) cy = k;
    const fy0 = (y - by(cy) + 0.5) / (by(cy + 1) - by(cy)), sy = fy0 * fy0 * (3 - 2 * fy0);
    for (let x = 0; x < w; x++) {
      let cx = 0; for (let k = 1; k < GX; k++) if (x >= bx(k)) cx = k;
      const fx0 = (x - bx(cx) + 0.5) / (bx(cx + 1) - bx(cx)), sx = fx0 * fx0 * (3 - 2 * fx0);
      const i = (y * w + x) * 4, r = LUT[buf[i]], g = LUT[buf[i + 1]], b = LUT[buf[i + 2]];
      const L = 0.2126 * r + 0.7152 * g + 0.0722 * b, s = buf[i] + buf[i + 1] + buf[i + 2];
      const red = s > 0 && buf[i] >= 0.8 * s ? Math.max(0, r - g - b) : 0;
      const hw = [(1 - sx) * (1 - sy), sx * (1 - sy), (1 - sx) * sy, sx * sy], o = (cy * GX + cx) * 8;
      for (let j = 0; j < 4; j++) { sums[o + j] += hw[j] * L; sums[o + 4 + j] += hw[j] * red; }
    }
  }
  let maxErr = 0, maxRedErr = 0, cellsMean = 0;
  for (let cy = 0; cy < GY; cy++) for (let cx = 0; cx < GX; cx++) {
    const n = (bx(cx + 1) - bx(cx)) * (by(cy + 1) - by(cy)), o = (cy * GX + cx) * 8;
    for (let j = 0; j < 4; j++) {
      const gpuL = l.cells[((cy * GX + cx) * 2) * 4 + j], gpuR = l.cells[((cy * GX + cx) * 2 + 1) * 4 + j];
      maxErr = Math.max(maxErr, Math.abs(gpuL - sums[o + j] / n)); maxRedErr = Math.max(maxRedErr, Math.abs(gpuR - sums[o + 4 + j] / n));
      cellsMean += sums[o + j] / n / 64;
    }
  }
  return { width: w, height: h, grid: window.__vj.stats().limiter.grid, max_abs_err: maxErr, max_abs_red_err: maxRedErr, mean_lum: cellsMean, mode: l.mode };
})()`;

// ------------------------------------------------------------------------------------------------- the CLI --
async function main() {
  const { values: opt } = parseArgs({ options: {
    web: { type: "string", default: resolve(REPO, "arsenal", "web") },
    label: { type: "string", default: "run" },
    phases: { type: "string", default: "storm,laser,safe,cpu,adv,hires,calm,parity,meter,bench" },
    sets: { type: "string", default: "vj-reactor,vj-hyperspace,vj-led-wall" },
    scenarios: { type: "string", default: "invert10,oneshots15,oneshots5,nozoom15,all12,flashedge,flash24,lasglitch,lookstorm" },
    "safe-sets": { type: "string", default: "vj-reactor,vj-led-wall,vj-hyperspace" },
    "safe-scenarios": { type: "string", default: "oneshots15,invert10,all12,lasglitch,cuts,calmset" },
    "cpu-scenarios": { type: "string", default: "oneshots15,all12,invert10" },
    "adv-presets": { type: "string", default: Object.keys(ADV).join(",") },
    "hires-scenarios": { type: "string", default: "oneshots15,lookstorm,all12" },
    "hires-adv": { type: "string", default: "adv-stripes,adv-offgrid12,adv-offgrid80" },
    hires: { type: "string", default: "1280x720,1920x1080" },
    "hires-seconds": { type: "string", default: "5" },
    "calm-sets": { type: "string", default: "vj-reactor,vj-hyperspace,vj-led-wall,vj-synthwave-grid,vj-laser-cathedral" },
    // Lasers v2 (2026-10-25): the laser storms on the Cathedral (its heads from the head bus) and on Reactor (every head
    // from the page's beam layer)
    "laser-sets": { type: "string", default: "vj-laser-cathedral,vj-reactor" },
    "laser-scenarios": { type: "string", default: "lasertiers,laserroll" },
    seconds: { type: "string", default: "10" },
    seed: { type: "string", default: "7" },
    port: { type: "string", default: "8975" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    width: { type: "string", default: "640" },
    height: { type: "string", default: "360" },
    "lock-dir": { type: "string", default: LOCK_DIR },
    "gpu-wait-min": { type: "string", default: "30" },
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
  const list = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
  const setIds = (s) => list(s).filter((x) => /^[a-z0-9][a-z0-9-]{1,40}$/.test(x));
  const SETS = setIds(opt.sets), SAFE_SETS = setIds(opt["safe-sets"]);
  const SCN = list(opt.scenarios).filter((s) => SCENARIOS[s]);
  const SAFE_SCN = list(opt["safe-scenarios"]).filter((s) => SCENARIOS[s]);
  const CPU_SCN = list(opt["cpu-scenarios"]).filter((s) => SCENARIOS[s]);
  const ADV_IDS = list(opt["adv-presets"]).filter((s) => ADV[s]);
  const HIRES = list(opt.hires).map((s) => s.split("x").map(Number)).filter(([a, b]) => a >= 64 && b >= 36);
  const HIRES_SCN = list(opt["hires-scenarios"]).filter((s) => SCENARIOS[s]);
  const HIRES_ADV = list(opt["hires-adv"]).filter((s) => ADV[s]);
  const HIRES_FRAMES = Math.round(Number(opt["hires-seconds"]) * 60);
  const PHASES = list(opt.phases);
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
  const outDir = join(opt.out, `vj-storm-${opt.label}-${stamp}`);
  mkdirSync(outDir, { recursive: true });
  const report = {
    api: "arsenal.receipt/v0", lane: "vj-storm", label: opt.label, title: "VJ storms on a 60 fps virtual clock: flashes in the frames shown, counted in windows the limiter does not use",
    started_at: new Date().toISOString(), web: WEB, viewport: { width: W, height: H }, frames: FRAMES, seed: Number(opt.seed),
    git: null, chrome: null, webgl: null, renderer_check: null,
    method: {
      clock: "virtual: performance.now and requestAnimationFrame replaced; one frame per 1000/60 ms step",
      measure: "the canvas read every frame (after every layer and gate v2); per cell of a 64 x 36 grid: exact mean relative luminance (sRGB LUT, WCAG weights) and mean WCAG red quantity (R/(R+G+B) >= 0.8 on 8-bit values, max(0, R-G-B) x 320 linear)",
      windows: `${STORM_WINDOWS.length}: the whole frame and every rectangle of shapes ${STORM_SHAPES.map(([w, h]) => `${w}x${h}`).join(", ")} cells (each a quarter of the screen or more) at every offset of the 64 x 36 grid`,
      counter: "the 2026-10-24 verifier's, verbatim: hysteresis 0.02, |delta| >= 0.1, darker end < 0.8, counted at the later turning point; flashes = transitions / 2; strict = greedy pairs of opposing transitions; red: hysteresis 2, swing 20, no darker-end exemption",
      verdict: `every window <= 6 transitions and <= 3 strict pairs in any second, red the same, longest flashing run <= ${RUN_LIMIT_S} s, the limiter in the mode asked for, no page error`,
    },
    scenarios: SCENARIOS, adversarial: Object.fromEntries(Object.entries(ADV).map(([k, v]) => [k, v[1]])),
    runs: [], calm: null, parity: null, meter: null, bench: null, bursts: [], console: [], exceptions: [],
    not_measured: [
      "the real GPU: SwiftShader draws every frame on the CPU; the virtual clock makes the timing exact, not the speed",
      "a person: the counter is the verifier's (WCAG 2.3.1 / ITU-R BT.1702 shaped); spatial stripe patterns are not judged as patterns",
      "windows off the 64 x 36 grid (sub-cell offsets) and shapes other than the twelve; the limiter's margin is for those",
      "music in the storms: no engine and no demo (the sets run on time alone); the calm phase plays the demo's music without pads",
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
    // the adversarial presets: served by this receipt, never files in the repo
    const adv = /\/presets\/(adv-[a-z0-9-]+)\.frag$/.exec(url.pathname);
    if (adv && advPreset(adv[1])) { res.writeHead(200, { "Content-Type": TYPES[".frag"], "Cache-Control": "no-store" }); res.end(advPreset(adv[1])); return; }
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

  // One burst: our own Chrome at w x h under the house GPU lock; body({ ev, load, deadline }).
  async function burst(name, size, body) {
    const t0 = Date.now();
    const [bw, bh] = size;
    const profile = join(tmpdir(), `arsenal-vj-storm-${stamp}-${name}-${process.pid}`);
    let gpu = null, chrome = null, browser = null;
    const entry = { name, size: `${bw}x${bh}`, seconds: null, wait_s: null, error: null };
    report.bursts.push(entry);
    try {
      // a 2 s poll: lanes that render in short chunks take the lock straight back after each one, and a 10 s poll rarely
      // lands in the gap
      gpu = await acquireGpuLock({ dir: opt["lock-dir"], label: `vj_storm ${name} (SwiftShader)`, maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000, pollMs: 2000 });
      const held = Date.now();   // the burst's time runs from the lock, not from the wait for it
      entry.wait_s = Math.round((held - t0) / 100) / 10;
      chrome = spawn(opt.chrome, [...SWIFTSHADER_FLAGS, ...GPU_FENCE_FLAGS, ...QUIET_FLAGS, "--remote-debugging-port=0",
        `--user-data-dir=${profile}`, `--window-size=${bw},${bh}`, "--force-device-scale-factor=1", "about:blank"], { stdio: "ignore", windowsHide: true });
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
      await S("Emulation.setDeviceMetricsOverride", { width: bw, height: bh, deviceScaleFactor: 1, mobile: false });
      await S("Page.addScriptToEvaluateOnNewDocument", { source: VIRTUAL_CLOCK });
      const ev = async (expression) => { const r = await S("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
        if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
      const load = async (query, { root = "web", mode = "gpu", virtual = true } = {}) => {
        const q = `${query}${mode === "cpu" ? "&limiter=cpu" : mode === "off" ? "&limiter=off" : mode === "late" ? "&limiter=late" : ""}${opt.query ? `&${opt.query}` : ""}`;
        await S("Page.navigate", { url: `http://127.0.0.1:${PORT}/${root}/vj.html?${q}` });
        await waitFor(() => ev("!!(window.__vj && window.__vj.ready)"), 240000, `the vj page (${q})`);
        // every set compiled (the cut storms need them all), then gate v2: its meter and apply link first (the page decides
        // on the CPU until the GPU decision links too); the GPU mode waits for the GPU decision
        await waitFor(() => ev(`(() => { const s = window.__vj.sets(); return s.every((x) => x.status === "ok" || x.broken); })()`), 240000, "the sets").catch(() => {});
        // (an older build reports no mode: its limiter running counts as the GPU one, its error as the safe mode)
        const want = mode === "gpu" ? `(l.mode === "gpu" || (l.mode === undefined && (l.on || !!l.error)))` : mode === "cpu" || mode === "late" ? `l.mode === "cpu"` : "true";
        const step = virtual ? "window.__vt && window.__vt.step(1000 / 60);" : "";
        await waitFor(() => ev(`(() => { ${step} const l = window.__vj.stats().limiter; return !l || ${want} || l.fatal; })()`), 180000, `gate v2 (${mode})`);
        await ev("(window.__vjx && window.__vjx.cardOff(), true)");   // clean frames: no name cards
        if (!report.webgl) {
          report.webgl = await ev(`(() => { const g = document.getElementById("gl").getContext("webgl2"); const d = g.getExtension("WEBGL_debug_renderer_info"); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); })()`);
          report.renderer_check = judgeRenderer(report.webgl);
        }
        if (!judgeRenderer(report.webgl).ok) throw new Error(`refusing to judge: not SwiftShader (${report.webgl})`);
      };
      await body({ ev, load, deadline: held + Number(opt["burst-s"]) * 1000 });
    } catch (err) { entry.error = String((err && err.stack) || err); console.log(`ERROR [${name}]`, entry.error); }
    finally {
      entry.seconds = Math.round((Date.now() - t0) / 100) / 10 - (entry.wait_s || 0);
      try { await browser?.send("Browser.close"); } catch { /* gone */ }
      await delay(600);
      if (chrome && chrome.exitCode === null) spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { windowsHide: true, timeout: 15000 });
      gpu?.release();
      await delay(300);
      try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
      save();
    }
  }

  // A queue of runs: { phase, set, scenario, mode, size, frames, sets (page) }. Bursts take runs in order until the
  // burst's time is up; a run that failed to start in a burst is retried (at most twice).
  async function runQueue(phase, jobs) {
    const done = new Set();
    let tries = 0;
    const key = (j) => `${j.size.join("x")}|${j.mode}|${j.pageSets}|${j.scenario}`;
    while (jobs.some((j) => !done.has(key(j))) && tries++ < jobs.length + 3) {
      const size = jobs.find((j) => !done.has(key(j))).size;
      await burst(`${phase}-${size.join("x")}-${tries}`, size, async ({ ev, load, deadline }) => {
        for (const j of jobs) {
          if (done.has(key(j)) || j.size.join("x") !== size.join("x")) continue;
          if (Date.now() > deadline) { console.log(`[${phase}] burst time is up; the next burst continues`); return; }
          done.add(key(j));   // tried (a run that throws is recorded as an error, not retried forever)
          try {
            await load(`engine=off&hud=0&watchdog=0&sets=${j.pageSets}`, { mode: j.mode });
            await ev("(() => { for (let i = 0; i < 30; i++) window.__vt.step(1000 / 60); return true; })()");   // half a second in
            const r = await runStormInPage(ev, j.scenario, j.frames, { seed: Number(opt.seed), mode: j.mode });
            const row = { phase, set: j.set, ...r, size: j.size.join("x") };
            report.runs.push(row);
            console.log(`[${phase}] ${row.size} ${j.mode} ${j.set} ${j.scenario}: worst ${r.max_flashes_in_1s}/s pairs ${r.max_pairs_in_1s} (${r.worst_window}), full ${r.full_max_flashes_in_1s}/s, quadrants ${r.quadrant_max_flashes_in_1s.join(" ")}, red ${r.red_max_flashes_in_1s}/s p${r.red_max_pairs_in_1s}, run ${r.longest_run_s}s, L ${r.L_min}-${r.L_max}, gate ${r.gate.granted}, hits ${r.impact_hits}, refused ${r.safe_refused}, limiter ${r.limiter ? (r.limiter.on ? `${r.limiter.mode} leaks ${r.limiter.leaks}` : "off") : "-"}, ${r.ms_per_frame} ms/f${r.pass ? "" : "  << FAIL"}`);
          } catch (err) {
            report.runs.push({ phase, set: j.set, scenario: j.scenario, mode: j.mode, size: j.size.join("x"), pass: false, error: String(err && err.message || err) });
            console.log(`[${phase}] ${j.set} ${j.scenario}: ERROR ${err && err.message}`);
          }
          save();
        }
      });
    }
  }
  const SIZE = [W, H];
  const job = (phase, set, scenario, mode, size = SIZE, frames = FRAMES, pageSets = set) => ({ phase, set, scenario, mode, size, frames, pageSets });

  // ------------------------------------------------------------------------------------------- the storms --
  if (PHASES.includes("storm")) {
    const jobs = [];
    for (const set of SETS) for (const s of SCN) jobs.push(job("storm", set, s, "gpu"));
    if (SETS.length >= 2) jobs.push(job("storm", SETS.join("+"), "cuts", "gpu", SIZE, FRAMES, SETS.join(",")));
    await runQueue("storm", jobs);
  }
  // Lasers v2: the laser storms, gate v2 deciding on the GPU
  if (PHASES.includes("laser")) {
    const jobs = [];
    for (const set of list(opt["laser-sets"])) for (const s of list(opt["laser-scenarios"]).filter((x) => SCENARIOS[x])) jobs.push(job("laser", set, s, "gpu"));
    await runQueue("laser", jobs);
  }
  // the safe mode: the limiter absent (?limiter=off); every pad effect must be refused and the frame stay flash-safe
  if (PHASES.includes("safe")) {
    const jobs = [];
    for (const set of SAFE_SETS) for (const s of SAFE_SCN) {
      if (s === "cuts") { if (set === SAFE_SETS[0]) jobs.push(job("safe", SAFE_SETS.join("+"), "cuts", "off", SIZE, FRAMES, SAFE_SETS.join(","))); }
      else jobs.push(job("safe", set, s, "off"));
    }
    await runQueue("safe", jobs);
  }
  // the CPU decision (?limiter=cpu): the page's fallback when the GPU decision cannot link
  // ... and the hand-over: the twin decides for the first two seconds, then its state goes to the GPU mid-storm
  if (PHASES.includes("cpu")) await runQueue("cpu", [...CPU_SCN.map((s) => job("cpu", SETS[0], s, "cpu")), job("cpu", SETS[0], "oneshots15", "late")]);
  // adversarial content: presets this receipt serves (GPU decision; the off-grid rectangle and the lines also on the CPU)
  if (PHASES.includes("adv")) {
    const jobs = ADV_IDS.map((id) => job("adv", id, id, "gpu", SIZE, Math.min(FRAMES, 360)));
    for (const id of ["adv-offgrid12", "adv-stripes"]) if (ADV_IDS.includes(id)) jobs.push(job("adv", id, id, "cpu", SIZE, Math.min(FRAMES, 360)));
    await runQueue("adv", jobs);
  }
  // show sizes: storms, the look at full and the adversarial presets at 1280 x 720 and 1920 x 1080
  if (PHASES.includes("hires")) {
    for (const size of HIRES) {
      const jobs = [];
      for (const s of HIRES_SCN) jobs.push(job("hires", SETS[0], s, "gpu", size, HIRES_FRAMES));
      for (const id of HIRES_ADV) jobs.push(job("hires", id, id, "gpu", size, Math.min(HIRES_FRAMES, 240)));
      await runQueue("hires", jobs);
    }
  }

  // ------------------------------------------------------------------------------------------------ calm --
  // The other side of the limit: a set under the page's own demo music (beats, chords, energy; no pads) should not be held
  // at all. Every 15 frames the limiter's own state is read back (how many trackers held the frame before, the rest).
  if (PHASES.includes("calm")) {
    report.calm = {};
    for (const set of setIds(opt["calm-sets"])) {
      await burst(`calm-${set}`, SIZE, async ({ ev, load }) => {
        await load(`engine=off&hud=0&watchdog=0&demo=1&demopads=0&sets=${set}`);
        await ev(STORM_PAGE);
        const frames = FRAMES * 2;
        // the run, with the limiter sampled through a schedule-free loop of our own
        const r = await ev(`(() => { const out = { held: [], partial: [], rest: 0 };
          const orig = window.__vt.step; let f = 0;
          window.__vt.step = (ms) => { const v = orig(ms); if (++f % 15 === 0) { const l = window.__vj.limiter(); out.held.push(l.held || 0); out.partial.push(l.partial || 0); if (l.rest > 0) out.rest++; } return v; };
          const res = window.__storm.run([], ${frames});
          window.__vt.step = orig;
          return { ...res, sampled: out }; })()`);
        const pull = async (key) => { const n = await ev(`window.__storm.len(${JSON.stringify(key)})`); let s = ""; for (let i = 0; i < n; i += 1 << 20) s += await ev(`window.__storm.slice(${JSON.stringify(key)}, ${i}, ${1 << 20})`); return s; };
        const Lb = Buffer.from(await pull("L"), "base64"), Rb = Buffer.from(await pull("R"), "base64");
        const j = judgeStorm({ frames, L: new Uint16Array(Lb.buffer, Lb.byteOffset, Lb.length / 2), R: new Uint16Array(Rb.buffer, Rb.byteOffset, Rb.length / 2), N: Float64Array.from(r.N) });
        const s = r.sampled;
        report.calm[set] = { frames, max_flashes_in_1s: j.max_flashes_in_1s, max_pairs_in_1s: j.max_pairs_in_1s, worst_window: j.worst_window, red: j.red_max_flashes_in_1s,
                             limiter: r.limiter, samples: s.held.length, samples_fully_held: s.held.filter((h) => h > 0).length,
                             samples_partial: s.partial.filter((h) => h > 0).length, samples_resting: s.rest,
                             mean_held_trackers: s.held.length ? +(s.held.reduce((a, b) => a + b, 0) / s.held.length).toFixed(2) : null };
        console.log(`[calm] ${set}: ${JSON.stringify(report.calm[set])}`);
      });
    }
  }

  // ---------------------------------------------------------------------------------------------- parity --
  if (PHASES.includes("parity")) {
    await burst("parity", SIZE, async ({ ev, load }) => {
      await load("engine=off&hud=0&watchdog=0&sets=vj-reactor");
      const has = await ev("!!(window.__vj.limiterCells)");
      if (!has) { report.parity = { skipped: "this page has no gate v2 (window.__vj.limiterCells)" }; return; }
      const gate = await import(pathToFileURL(join(WEB, "vj-gate.js")).href);
      const results = [];
      const NCTRL = gate.NCTRL || 25;
      for (const [name, gen] of Object.entries(paritySequences(gate))) {
        const seq = gen();
        await ev("window.__vj.limiterReset()");
        const gpu = await ev(`(() => { const seq = ${JSON.stringify(seq.map((c) => Array.from(c)))}; const out = [];
          for (let f = 0; f < seq.length; f++) { const r = window.__vj.limiterCells(seq[f], 1 / 60); if (!r) return null; out.push({ a: r.a, k: r.k, beta: r.betaNow, held: r.trackers.map((t) => t[5]), leaks: r.leaks, trk: f % 25 === 24 ? r.trackers : null }); }
          window.__vj.limiterReset(); return out; })()`);
        if (!gpu) { results.push({ sequence: name, skipped: "the GPU decision is not running" }); continue; }
        const model = new gate.FlashLimiter();
        let maxA = 0, maxK = 0, maxB = 0, heldDiff = 0, heldFrames = 0, frames = 0, first = null;
        for (let f = 0; f < seq.length; f++) {
          const m = model.step(seq[f], 1 / 60);
          const g = gpu[f];
          for (let i = 0; i < NCTRL; i++) { maxA = Math.max(maxA, Math.abs(m.a[i] - g.a[i])); maxK = Math.max(maxK, Math.abs(m.k[i] - g.k[i])); }
          maxB = Math.max(maxB, Math.abs(m.beta - g.beta));
          let d = 0;
          if (!first && g.trk) for (let t = 0; t < g.trk.length && !first; t++) for (let q = 0; q < gate.TRACKER_FLOATS && !first; q++) {
            const mv = model.state[t * gate.TRACKER_FLOATS + q], gv = g.trk[t][q];
            if (Math.abs(mv - gv) > 1e-4 && !(Math.abs(mv) > 1e8 && Math.abs(gv) > 1e8)) first = { frame: f, tracker: t, field: q,
              model: Array.from(model.state.slice(t * gate.TRACKER_FLOATS, (t + 1) * gate.TRACKER_FLOATS)).map((x) => +x.toFixed(6)),
              gpu: g.trk[t].map((x) => +x.toFixed(6)), want: +model.want[t].toFixed(6), shown: +model.shown[t].toFixed(6) };
          }
          for (let t = 0; t < g.held.length; t++) {
            const mh = model.level[t];
            if (mh !== Math.round(g.held[t])) d++;
            heldFrames += mh > 0 ? 1 : 0;
          }
          if (d) heldDiff++;
          frames++;
        }
        const row = { sequence: name, frames, max_abs_gain: +maxA.toFixed(5), max_abs_lift: +maxK.toFixed(5), max_abs_beta: +maxB.toFixed(5),
                      frames_with_held_mismatch: heldDiff, held_tracker_frames: heldFrames, model_leaks: model.leaks, gpu_leaks: gpu[gpu.length - 1].leaks, first_divergence: first };
        results.push(row);
        console.log(`[parity] ${name}: ${JSON.stringify({ ...row, first_divergence: first ? { frame: first.frame, tracker: first.tracker, field: first.field } : null })}`);
      }
      const ran = results.filter((r) => !r.skipped);
      report.parity = { results, pass: ran.length > 0 && ran.every((r) => r.max_abs_gain < 0.02 && r.max_abs_lift < 0.02 && r.max_abs_beta < 0.02 && r.frames_with_held_mismatch <= Math.ceil(0.02 * r.frames)) };
    });
  }

  // ----------------------------------------------------------------------------------------------- meter --
  // Every pixel metered, at every size: the limiter's cells against the canvas's own pixels, on 1-px lines on odd columns
  // (a meter that strides misses them) and on a set, at the storm size and the show sizes.
  if (PHASES.includes("meter")) {
    report.meter = { rows: [] };
    for (const size of [SIZE, ...HIRES]) {
      await burst(`meter-${size.join("x")}`, size, async ({ ev, load }) => {
        for (const set of ["adv-stripes", "vj-reactor"]) {
          await load(`engine=off&hud=0&watchdog=0&sets=${set}`);
          // a frame the limiter leaves untouched: the lines' "on" half (u_time from the page's clock), checked after
          let r = null;
          for (let k = 0; k < 40; k++) {
            r = await ev(METER_PAGE);
            const l = await ev("(() => { const l = window.__vj.limiter(); return { betaNow: l.betaNow, a: Math.min(...l.a), k: Math.max(...l.k) }; })()");
            if (r && !r.error && r.mean_lum > 0.01 && l.betaNow === 0 && l.a >= 1 && l.k <= 0) { r.untouched = true; break; }
          }
          const row = { size: size.join("x"), set, ...r, pass: !!r && !r.error && !!r.untouched && r.max_abs_err < 0.004 && r.max_abs_red_err < 0.004 };
          report.meter.rows.push(row);
          console.log(`[meter] ${row.size} ${set}: ${JSON.stringify(row)}`);
        }
      });
    }
    report.meter.pass = report.meter.rows.length > 0 && report.meter.rows.every((r) => r.pass);
  }

  // ----------------------------------------------------------------------------------------------- bench --
  if (PHASES.includes("bench")) {
    report.bench = {};
    for (const size of [SIZE, ...HIRES]) {
      await burst(`bench-${size.join("x")}`, size, async ({ ev, load }) => {
        for (const mode of ["gpu", "cpu"]) {
          await load(`realclock=1&engine=off&hud=0&watchdog=0&sets=${SETS[0]}`, { mode, virtual: false });
          await delay(1500);
          const r = await ev("window.__vj.limiterBench ? window.__vj.limiterBench(20) : null");
          if (!r) { report.bench[`${size.join("x")} ${mode}`] = { skipped: "gate v2 is not running" }; continue; }
          report.bench[`${size.join("x")} ${mode}`] = r;
          console.log(`[bench] ${size.join("x")} ${mode}: limiter ${r.limiter_ms.toFixed(2)} ms vs plain copy ${r.copy_ms.toFixed(2)} ms (${JSON.stringify(r.parts_ms)})`);
        }
      });
    }
  }

  // ------------------------------------------------------------------------------------------- frametime --
  // The whole frame's cost on SwiftShader, for any build: the page's own frames run back to back (requestAnimationFrame
  // taken over after load), each fenced by a one-pixel readPixels, 40 of them; --compare-webs builds interleaved.
  if (PHASES.includes("frametime")) {
    report.frametime = {};
    const builds = [{ label: opt.label, root: "web" }, ...OTHER.map((o, i) => ({ label: o.label, root: `w${i}` }))];
    for (let rep = 0; rep < Number(opt.reps); rep++) await burst(`frametime-${rep + 1}`, SIZE, async ({ ev, load }) => {
      for (const b of builds.map((_, i) => builds[(i + rep) % builds.length])) for (const set of SETS.slice(0, 2)) {
        await load(`realclock=1&engine=off&hud=0&watchdog=0&sets=${set}`, { root: b.root, virtual: false });
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
    report.frametime_summary = Object.fromEntries(Object.entries(report.frametime).map(([label, sets]) => [label,
      Object.fromEntries(Object.entries(sets).map(([set, runs]) => { const v = runs.map((x) => x.p50).sort((a, b) => a - b); return [set, v[Math.floor(v.length / 2)]]; }))]));
    console.log(`[frametime] median p50 per build: ${JSON.stringify(report.frametime_summary)}`);
  }

  // --------------------------------------------------------------------------------------------- verdict --
  const runs = report.runs;
  const expected = (PHASES.includes("storm") ? SETS.length * SCN.length + (SETS.length >= 2 ? 1 : 0) : 0) +
    (PHASES.includes("safe") ? SAFE_SETS.length * SAFE_SCN.filter((s) => s !== "cuts").length + (SAFE_SCN.includes("cuts") ? 1 : 0) : 0) +
    (PHASES.includes("cpu") ? CPU_SCN.length + 1 : 0) +
    (PHASES.includes("adv") ? ADV_IDS.length + ["adv-offgrid12", "adv-stripes"].filter((x) => ADV_IDS.includes(x)).length : 0) +
    (PHASES.includes("hires") ? HIRES.length * (HIRES_SCN.length + HIRES_ADV.length) : 0);
  const byPhase = {};
  for (const r of runs) { const p = (byPhase[r.phase] = byPhase[r.phase] || { runs: 0, failed: 0, max_flashes_in_1s: 0, max_pairs_in_1s: 0 }); p.runs++; if (!r.pass) p.failed++; p.max_flashes_in_1s = Math.max(p.max_flashes_in_1s, r.max_flashes_in_1s || 0); p.max_pairs_in_1s = Math.max(p.max_pairs_in_1s, r.max_pairs_in_1s || 0); }
  report.verdict = {
    runs: runs.length, runs_expected: expected, by_phase: byPhase,
    failed: runs.filter((x) => !x.pass).map((x) => `${x.phase} ${x.size} ${x.mode} ${x.set} ${x.scenario}: ${x.error || `${x.max_flashes_in_1s}/s pairs ${x.max_pairs_in_1s} in ${x.worst_window}, red ${x.red_max_flashes_in_1s}, run ${x.longest_run_s}s, mode ok ${x.mode_ok}, errors ${(x.page_errors || []).length}`}`),
    max_flashes_in_1s: Math.max(0, ...runs.map((x) => x.max_flashes_in_1s || 0)),
    max_pairs_in_1s: Math.max(0, ...runs.map((x) => x.max_pairs_in_1s || 0)),
    max_full_frame_flashes_in_1s: Math.max(0, ...runs.map((x) => x.full_max_flashes_in_1s || 0)),
    page_exceptions: report.exceptions.length,
    calm: report.calm ? Object.fromEntries(Object.entries(report.calm).map(([k, v]) => [k, { max_flashes_in_1s: v.max_flashes_in_1s, fully_held_samples: v.samples_fully_held, partial_samples: v.samples_partial, rest_samples: v.samples_resting }])) : null,
    calm_failed: report.calm ? Object.entries(report.calm).filter(([, v]) => v.max_flashes_in_1s > 3 || v.max_pairs_in_1s > 3 || v.red > 3 || !v.limiter || v.limiter.on !== true).map(([k]) => k) : [],
    meter: report.meter ? report.meter.pass : null,
  };
  report.verdict.pass = report.verdict.runs === report.verdict.runs_expected && report.verdict.failed.length === 0 &&
    report.verdict.calm_failed.length === 0 && report.exceptions.length === 0 &&
    (!report.parity || report.parity.skipped || report.parity.pass) && (!report.meter || report.meter.pass);
  report.finished_at = new Date().toISOString();
  save();
  console.log(`\nVJ storm receipt (${opt.label}): ${report.verdict.runs}/${report.verdict.runs_expected} runs, worst ${report.verdict.max_flashes_in_1s} flashes/s (strict pairs ${report.verdict.max_pairs_in_1s}, full frame ${report.verdict.max_full_frame_flashes_in_1s}), failed ${report.verdict.failed.length}${report.parity ? `, parity ${report.parity.skipped ? "skipped" : report.parity.pass ? "PASS" : "FAIL"}` : ""}${report.meter ? `, meter ${report.meter.pass ? "PASS" : "FAIL"}` : ""} -> ${report.verdict.pass ? "PASS" : "FAIL"}`);
  for (const f of report.verdict.failed) console.log(`  FAIL ${f}`);
  console.log(`receipt: ${join(outDir, "receipt.json")}`);
  web.close();
  process.exit(report.verdict.pass ? 0 : 1);
}

// Synthetic cell sequences for the parity phase (the JS twin's input layout, vj-gate.js cellIndex).
function paritySequences(gate) {
  const { cellSums } = gate;
  const N = 300;
  return {
    square10: () => Array.from({ length: N }, (_, f) => cellSums(() => (Math.floor(f / 3) % 2 ? 0.5 : 0.05), () => 0, 32, 32)),
    offgrid8: () => Array.from({ length: N }, (_, f) => cellSums((u, v) => (u > 0.122 && u < 0.628 && v > 0.108 && v < 0.614 ? (Math.floor(f / 4) % 2 ? 0.3 : 0.02) : 0.02), () => 0, 64, 64)),
    redcentre: () => Array.from({ length: N }, (_, f) => cellSums((u, v) => 0.1, (u, v) => (Math.abs(u - 0.5) < 0.25 && Math.abs(v - 0.5) < 0.25 && Math.floor(f / 4) % 2 ? 0.3 : 0), 32, 32)),
    checker: () => Array.from({ length: N }, (_, f) => cellSums((u, v) => ((Math.floor(u * 3 + 0.01) + Math.floor(v * 6 + 0.1)) % 2 ^ (Math.floor(f / 3) % 2) ? 0.6 : 0.03), () => 0, 48, 48)),
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
