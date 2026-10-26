// VJ Lasers v2 hook-up: arsenal/web/vj-hookup.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_hookup.test.mjs.
//
// Daniel, 2026-10-25: "I am really curious to see what we have so far!" -- the laser engine (vj-lasers.js), the colour
// themes (vj-themes.js) and the engine's beat clock (arsenal/keylab/beatgrid.py) on the VJ page (vj.js). This module holds
// what the page decides between them that can be tested without a browser:
//   - the clock the laser engine reads: the page's BeatClock with its continuous beat position (vj-core.js, S2)  laserClock
//   - the beam records the page uploads: all of them, or for a scene with its own heads (the `laser-heads` tag: the
//     Laser Cathedral) only the hero head's, since that scene draws the other heads itself                       packBeams
//   - the head bus for such a scene: the engine's stripBus with each pad-grid head's colour slot (L1, L2, white)
//     read from the records that head drew this frame, written into the VJ strip v3                headBus, writeHeadBus
//   - which pads tap the engine's tempo (its hello's tap list): the page fires no effect for them      tapPadsOf, isTapPad
//   - the dial as the laser gate picker: AUTO, then every gate of the engine, one detent a step          GATE_DIAL, GateDial
//   - the Custom theme (Hue A and B, turned by fader 2): the lasers' two colours and pad stand-ins      customLaserTheme,
//                                                                                                       standInLed
//   - the chord colour on a theme while the AUDIO names the chords: a hue nudge of at most 15 degrees (spec 2.2)  capHue
//
// Daniel's calls of 2026-10-25 (research/reviewed/keylab-liberation-2026-10-22/daniel-calls-2026-10-25.md): Tap is tempo
// for the visuals only, and the Tap button and pad 12 both tap (the first tap of a run is the ONE); fader 1 is the theme
// fader (Hue A and B moved into Custom); the dial picks the laser gate; on the laser pad soft = single, medium =
// one-two, hard = triple (the engine's "normal" velocity tiers).

import { GATE_IDS, GATES, HEADS, HERO_HEAD, SEG_FLOATS, MAX_SEGMENTS, GROUP_MARK, LEVEL_MAX, stripBus } from "./vj-lasers.js";
import { STRIP, stripSet } from "./vj-core.js";
import { hls, toOklch, fromOklch, ledPostedOk, isSaturatedRed, linearToHex } from "./vj-themes.js";

export const HOOKUP_API = "arsenal.vj-hookup/v1";
const clamp01 = (x) => (x > 1 ? 1 : x < 0 ? 0 : x);

// ------------------------------------------------------------------------------------------------- the clock --
// The laser engine's clock (vj-lasers.js "The clock"): the page's BeatClock, with posAt -- the page grid's continuous beat
// position (vj-core.js BeatClock.posAt, slice S2) -- so every gate is computed from one metronome that slews and
// re-anchors with the engine's grid instead of being unwrapped from a phase. Before the first beat posAt is NaN and the
// engine falls back to the phase.
export function laserClock(bc) {
  return {
    get bpm() { return bc.bpm; },
    get conf() { return bc.conf; },
    phaseAt: (t) => bc.phase(t),
    nextBeatAt: (t) => bc.nextBeatAt(t),
    posAt: (t) => { const p = typeof bc.posAt === "function" ? bc.posAt(t) : null; return p === null ? NaN : p; },
    alive: (t) => (typeof bc.alive === "function" ? bc.alive(t) : bc.bpm > 0),
  };
}

// ------------------------------------------------------------------------------------------ the beam records --
// The records to upload for the beam layer: { seg, n }. With heroOnly (a scene tagged `laser-heads` draws its own heads
// from the head bus) only the hero head's records are kept: its beams and every figure group (figures are drawn round
// the hero, by the hero head), group headers kept with their pieces. Otherwise the engine's own buffer, uncopied.
export function packBeams(out, heroOnly, dst = new Float32Array(MAX_SEGMENTS * SEG_FLOATS)) {
  if (!heroOnly) return { seg: out.seg, n: out.n };
  let w = 0, i = 0;
  const seg = out.seg, head = out.head;
  while (i < out.n) {
    const o = i * SEG_FLOATS;
    if (seg[o + 3] >= GROUP_MARK - 0.5) {                  // a group header: the next `count` rows are one figure
      const count = Math.round(seg[o + 3] - GROUP_MARK);
      const keep = count > 0 && i + 1 < out.n && head[i + 1] === HERO_HEAD;
      const rows = Math.min(count, out.n - i - 1) + 1;
      if (keep) { dst.set(seg.subarray(o, o + rows * SEG_FLOATS), w * SEG_FLOATS); w += rows; }
      i += rows;
      continue;
    }
    if (head[i] === HERO_HEAD) { dst.set(seg.subarray(o, o + SEG_FLOATS), w * SEG_FLOATS); w++; }
    i++;
  }
  return { seg: dst, n: w };
}

// ------------------------------------------------------------------------------------------------ the head bus --
// The spec's head bus (1.7) as 24 floats in stripBus's order: [1] pattern id, [2] step phase, [3] solo, [4..15] the 12
// pad-grid heads (slot + level), [16..18] L1 rgb, [19] beams per fan, [20..22] L2 rgb, [23] spread. The engine's stripBus
// gives every head slot 0 (L1); here each head's slot is the colour its brightest record drew this frame, nearest of L1,
// L2 and white, so a split or a burst reaches the Cathedral's heads in its own colours.
const levelOf = (lv) => (Math.floor(lv / 4096) / 4095) * LEVEL_MAX;
const chan = (col, shift) => { const q = Math.floor(col / shift) % 256; return (q / 255) * (q / 255); };
const cellBest = new Float32Array(12), cellSlot = new Int8Array(12);
export function headBus(engine, bus = new Float32Array(24)) {
  stripBus(engine, bus);
  const f = engine.out, c = engine.col;
  cellBest.fill(0); cellSlot.fill(0);
  const W = c.W || [1, 1, 1];
  for (let i = 0; i < f.n; i++) {
    const h = f.head[i];
    if (h < 0 || h >= HEADS.length || h === HERO_HEAD) continue;
    const o = i * SEG_FLOATS;
    if (f.seg[o + 3] >= GROUP_MARK - 0.5) continue;
    const I = levelOf(f.seg[o + 5]);
    const cell = HEADS[h].pad - 1;
    if (!(cell >= 0 && cell < 12) || I <= cellBest[cell]) continue;
    cellBest[cell] = I;
    const col = f.seg[o + 4], r = chan(col, 65536), g = chan(col, 256), b = chan(col, 1);
    let best = 0, bd = Infinity;
    const cand = [c.L1, c.L2, W];
    for (let s = 0; s < 3; s++) {
      const d = (cand[s][0] - r) ** 2 + (cand[s][1] - g) ** 2 + (cand[s][2] - b) ** 2;
      if (d < bd - 1e-9) { bd = d; best = s; }
    }
    cellSlot[cell] = best;
  }
  for (let p = 0; p < 12; p++) {
    const lv = Math.min(0.999, Math.max(0, bus[4 + p]));
    bus[4 + p] = lv > 0 ? cellSlot[p] + lv : 0;
  }
  return bus;
}
export const HEAD_BUS_IDLE = Object.freeze(Object.assign(new Array(24).fill(0), { 3: 1 }));
// Into the VJ strip (vj-core.js STRIP v3): row 2 texel 9 .yzw, row 3 texels 12-14 (the heads), row 2 texels 13-14 (L1,
// L2). `starCount` keeps texel 9's .x. A bus of null writes the idle state: no pattern, solo 1, every head 0.
export function writeHeadBus(strip, bus, starCount) {
  const b = bus || HEAD_BUS_IDLE;
  stripSet(strip, 9, STRIP.ROW_PALETTE, starCount, b[1], b[2], b[3]);
  stripSet(strip, 12, STRIP.ROW_PADCOL, b[4], b[5], b[6], b[7]);
  stripSet(strip, 13, STRIP.ROW_PADCOL, b[8], b[9], b[10], b[11]);
  stripSet(strip, 14, STRIP.ROW_PADCOL, b[12], b[13], b[14], b[15]);
  stripSet(strip, 13, STRIP.ROW_PALETTE, b[16], b[17], b[18], b[19]);
  stripSet(strip, 14, STRIP.ROW_PALETTE, b[20], b[21], b[22], b[23]);
}

// --------------------------------------------------------------------------------------------- the tap pads --
// The engine's hello names its tap controls (--tap, e.g. "daw:cc23,daw:pad12"). A pad in that list taps the beat
// clock's tempo (the first tap of a run is the ONE with --tap-one): the page fires no effect for it, so pad 12 is the
// tap and nothing else while the engine says so. port: "daw" (the DAW port's pads), "midi" (the bank's), null (either).
export function tapPadsOf(hello) {
  const spec = hello && typeof hello.tap === "string" ? hello.tap : "";
  const out = [];
  for (const part of spec.split(",")) {
    const m = /^(?:(daw|midi):)?(?:pad(\d{1,2})|(pads))$/.exec(part.trim());
    if (!m) continue;
    const port = m[1] || null;
    if (m[3]) { for (let p = 1; p <= 12; p++) out.push({ pad: p, port }); continue; }
    const pad = Number(m[2]);
    if (pad >= 1 && pad <= 12) out.push({ pad, port });
  }
  return out;
}
// Is a pad event from the engine (src "daw" or "bank") one of the engine's taps?
export function isTapPad(taps, pad, src) {
  if (src !== "daw" && src !== "bank") return false;
  const port = src === "daw" ? "daw" : "midi";
  return taps.some((t) => t.pad === pad && (t.port === null || t.port === port));
}

// ------------------------------------------------------------------------------------------- the gate dial --
// The dial picks the laser gate (Daniel, 2026-10-25): one step per message whatever its size (no acceleration), at most
// one step per stepMs (a fast spin cannot run away), wrapping round; an absolute control steps by the direction it moved.
// Index 0 is AUTO (velocity and the retrigger tiers pick the gate); the click (laserAuto) goes back to it.
export const GATE_DIAL = Object.freeze(["auto", ...GATE_IDS]);
export function gateLabel(id) { return id === "auto" ? "AUTO" : (GATES[id] ? GATES[id].label : id); }
export class GateDial {
  constructor({ stepMs = 60 } = {}) { this.stepMs = stepMs; this.index = 0; this.lastStep = -1e9; this.lastAbs = {}; this.ignored = 0; this.steps = 0; }
  get gate() { return GATE_DIAL[this.index]; }
  turn(ev, nowMs) {
    let dir = 0;
    if (ev.kind === "rel") dir = Math.sign(ev.delta);
    else {
      const prev = this.lastAbs[ev.id];
      this.lastAbs[ev.id] = ev.value;
      if (prev !== undefined) dir = Math.sign(ev.value - prev);
    }
    if (!dir) return false;
    if (nowMs - this.lastStep < this.stepMs) { this.ignored++; return false; }
    this.lastStep = nowMs;
    const n = GATE_DIAL.length;
    this.index = (((this.index + dir) % n) + n) % n;
    this.steps++;
    return true;
  }
  auto() { const was = this.index; this.index = 0; return was !== 0; }
  set(id) { const i = GATE_DIAL.indexOf(id); if (i >= 0) this.index = i; return i >= 0; }
}

// ------------------------------------------------------------------------------------------------- Custom --
// The Custom theme: today's free palette, Hue A and Hue B (the page's hueColour), turned together round the wheel by
// fader 2. The lasers take A and B (vj-lasers.js themeColours resolves a saturated red to white: a laser never emits one).
export function customLaserTheme(linA, linB) {
  return { id: "custom", L1: linearToHex(linA), L2: linearToHex(linB), W: "#ffffff" };
}
// A pad stand-in for a screen colour (linear rgb): the KeyLab's pads wash hues from orange to lime (HLS 15-100 degrees)
// and low saturation to white, so such a colour is shown as white at its lightness; any other at full saturation.
// Returns { hex, level } as vj-themes.js padLeds does (post ledHexAt(light, brightness)).
export function standInLed(lin) {
  const enc = lin.map((v) => { const x = clamp01(v); return x <= 0.0031308 ? 12.92 * x : 1.055 * Math.pow(x, 1 / 2.4) - 0.055; });
  const rgb = enc.map((v) => Math.round(v * 255));
  const { h, l, s } = hls(rgb);
  const m = Math.max(...enc);
  if (s < 0.35 || (h >= 15 && h <= 100)) return { hex: "#ffffff", level: Math.max(0.3, Math.min(1, m)) };
  // full saturation at the hue: HLS (h, 0.5, 1)
  const k = (n) => { const a = (n + h / 30) % 12; return 0.5 - 0.5 * Math.max(-1, Math.min(a - 3, 9 - a, 1)); };
  const hex = "#" + [k(0), k(8), k(4)].map((v) => Math.round(clamp01(v) * 255).toString(16).padStart(2, "0")).join("");
  return { hex: ledPostedOk(hex) ? hex : "#ffffff", level: Math.max(0.3, Math.min(1, m)) };
}

// ------------------------------------------------------------------------------------------ the chord colour --
// A theme's palette stop nudged toward a chord's colour. While the AUDIO names the chords (hardstyle), the nudge is a
// hue turn of at most maxDeg (15: spec 2.2), so the theme's two colours stay two; the keys (the piano) colour freely, up to
// the Chord colour knob, as before. amt 0..1 is how far (the knob times the chord's presence). Never returns a saturated
// red the theme did not already have.
export function capHue(stopLin, chordLin, amt, maxDeg = 15, out = [0, 0, 0]) {
  const a = toOklch(stopLin), c = toOklch(chordLin);
  if (a.C < 0.03 || c.C < 0.03 || !(amt > 0)) { out[0] = stopLin[0]; out[1] = stopLin[1]; out[2] = stopLin[2]; return out; }
  let d = c.h - a.h;
  d -= 360 * Math.round(d / 360);
  const turn = Math.max(-maxDeg, Math.min(maxDeg, d)) * clamp01(amt);
  let r = fromOklch(a.L, a.C, a.h + turn);
  if (isSaturatedRed(r) && !isSaturatedRed(stopLin)) r = stopLin;
  out[0] = r[0]; out[1] = r[1]; out[2] = r[2];
  return out;
}
