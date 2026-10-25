// Virtual Stage v0, the programmer: arsenal/web/stage/programmer.js (pure ES module). Tests: tests/stage_programmer.test.mjs.
//
// What a lighting console does every frame, in the design's order (section 3.2), for the v0 rig:
//   1. the LOOK (the running section's cue): base values per group (Dimmer, Pan, Tilt, Zoom, Color, Color2) and the
//      effects it runs; a new look crossfades its dimmers over its fade (beats) and starts / stops effects with their own
//      fade-in and fade-out, so nothing snaps;
//   2. the EFFECTS (effects.js), in the look's line order, on the group's members;
//   3. the PLAYBACKS on top (pads): KICK is a flash playback, merged HTP (highest takes precedence) on Dimmer; FLY-OUT is a
//      one-shot that adds an outward tilt and a dimmer pop, its delay spread by distance from the centre;
//   4. the MASTERS: the strand (F1), the beams (everything else with a lens), the pixels, the grand master (F9);
//   5. COLOUR: theme roles (A, B, W, beamA, beamB) resolve to linear RGB; a wheel fixture snaps to the nearest of its 14
//      slots, and its wheel turns at its real speed (0.12 s per slot), so a far colour change runs past the colours between;
//      saturated red (R / (R + G + B) >= 0.8) is never the result of an effect that pulses (the theme refuses red roles);
//   6. PHYSICS: every attribute follows its target no faster than its motor (velocity = range / real_fade, acceleration =
//      velocity / real_accel, from the type's attribute table); snap attributes (wheel slots) jump.
// The output is the design's FrameState: heads (16 floats each: pan, tilt, dimmer, r, g, b, zoomDeg, frost, iris, gobo,
// goboRot, prism, prismRot, shutter, focus, flags) and pixels (4 floats each: r, g, b, a, linear, before each cell kind's
// luminance scale, which the renderer owns). Gobo, prism and frost are modelled at their home values and drawn in v1.

import { EffectInstance, hashSeed } from "./effects.js";
import { hexToLinear, isSaturatedRed } from "./lasers.js";

export const PROGRAMMER_API = "arsenal.stage-programmer/v1";
export const HEAD_FLOATS = 16;
export const H = Object.freeze({ PAN: 0, TILT: 1, DIM: 2, R: 3, G: 4, B: 5, ZOOM: 6, FROST: 7, IRIS: 8, GOBO: 9, GOBOROT: 10,
  PRISM: 11, PRISMROT: 12, SHUTTER: 13, FOCUS: 14, FLAGS: 15 });
const ROLES = ["A", "B", "W", "beamA", "beamB", "warm"];

// ------------------------------------------------------------------------------------------------- physics --
// A slew-limited follower: velocity at most vmax, acceleration at most amax, braking in whole frames so it stops ON the
// target (no overshoot, no snap): each step takes the fastest speed toward the target from which a frame-by-frame
// deceleration of amax dt still lands exactly there.
export class Slew {
  constructor(x = 0, vmax = 1, amax = 10) { this.x = x; this.v = 0; this.vmax = vmax; this.amax = amax; }
  step(target, dt) {
    if (!(dt > 0)) return this.x;
    const d = target - this.x, sg = d < 0 ? -1 : 1, D = Math.abs(d), ad = this.amax * dt;
    if (D < 1e-9 && Math.abs(this.v) <= ad) { this.x = target; this.v = 0; return this.x; }
    // the distance a speed v still covers while braking by ad each frame: dt (v - ad) + dt (v - 2 ad) + ...
    const brake = (v) => { if (v <= ad) return 0; const m = Math.floor(v / ad); return dt * (m * v - (ad * m * (m + 1)) / 2); };
    const ok = (v) => v * dt + brake(v) <= D + 1e-12;
    const vc = this.v * sg;
    let lo = Math.max(-this.vmax, vc - ad), hi = Math.min(this.vmax, vc + ad), v;
    if (ok(hi)) v = hi;
    else if (!ok(lo)) v = lo;                       // the target jumped closer than we can stop: brake as hard as allowed
    else { for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; } v = lo; }
    this.v = v * sg;
    this.x += this.v * dt;
    return this.x;
  }
}
export function slewFor(attr, x0 = 0) {
  const range = (attr.max ?? 1) - (attr.min ?? 0);
  const vmax = range / (attr.real_fade ?? 0.1);
  const amax = vmax / (attr.real_accel ?? 0.05);
  return new Slew(x0, vmax, amax);
}

// ----------------------------------------------------------------------------------------- the theme's colours --
export function resolveTheme(theme) {
  const out = {};
  for (const r of ROLES) out[r] = theme && theme[r] ? hexToLinear(theme[r]) : [1, 1, 1];
  for (const r of ROLES) if (isSaturatedRed(out[r])) throw new Error(`theme ${theme && theme.name}: role ${r} is saturated red (held, never pulsed)`);
  out.laser = (theme && theme.laser) || ["#19ff4a", "#4a3cff", "#e6ffe9"];
  return out;
}
// the wheel slot nearest a colour (squared distance on chromaticity, then brightness)
export function nearestSlot(wheel, rgb) {
  const n = (c) => { const s = c[0] + c[1] + c[2] || 1; return [c[0] / s, c[1] / s, c[2] / s]; };
  const q = n(rgb);
  let best = 0, bd = Infinity;
  for (let i = 0; i < wheel.length; i++) {
    const p = n(wheel[i]);
    const d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2;
    if (d < bd - 1e-12) { bd = d; best = i; }
  }
  return best;
}

// --------------------------------------------------------------------------------------------- the programmer --
export class Programmer {
  constructor(rig, { theme = null, seed = null } = {}) {
    this.rig = rig;
    this.seed = seed ?? rig.seed;
    this.nH = rig.heads.length;
    this.nC = rig.cells.n;
    this.heads = new Float32Array(this.nH * HEAD_FLOATS);
    this.pixels = new Float32Array(this.nC * 4);
    // targets before physics: per head pan, tilt, dimmer, zoom, mix, role, role2; per cell dimmer, mix, role, role2
    this.tH = new Float64Array(this.nH * 7);
    this.tC = new Float64Array(this.nC * 4);
    this.baseH = new Float64Array(this.nH * 7); this.fromH = new Float64Array(this.nH * 7);
    this.baseC = new Float64Array(this.nC * 4); this.fromC = new Float64Array(this.nC * 4);
    this.fade = { p0: 0, len: 0 };
    this.masters = { grand: 1, strand: 1, beams: 1, pixels: 1 };
    this.speed = 1;
    this.effects = new Map();      // "group:effect" -> EffectInstance
    this.lines = [];
    this.pads = [];                // running playbacks {kind, onset, vel}
    this.lookName = "";
    this.setTheme(theme || Object.values(rig.themes)[0] || null);
    // the head's type data: attributes, wheel colours
    this.headType = rig.heads.map((fi) => rig.types[rig.fixtures[fi].type]);
    this.strandHead = rig.heads.map((fi) => rig.elements[rig.fixtures[fi].element].id === "rung");
    this.strandCell = new Uint8Array(this.nC);
    for (let c = 0; c < this.nC; c++) this.strandCell[c] = rig.elements[rig.cells.element[c]].id === "rung" ? 1 : 0;
    this.slews = this.headType.map((t) => ({
      pan: slewFor(t.attrs.Pan || { min: -270, max: 270, real_fade: 2.2, real_accel: 0.2 }),
      tilt: slewFor(t.attrs.Tilt || { min: -135, max: 135, real_fade: 1.4, real_accel: 0.2 }),
      dim: slewFor(t.attrs.Dimmer || { min: 0, max: 1, real_fade: 0.08, real_accel: 0.02 }),
      zoom: slewFor(t.attrs.Zoom || { min: 0.5, max: 4, real_fade: 0.6, real_accel: 0.1 }, (t.attrs.Zoom && t.attrs.Zoom.home) ?? 2),
      wheel: new Slew(0, 1 / ((t.attrs.Color1 && t.attrs.Color1.slot_time) || 0.12), 1e6),
    }));
    this.wheels = this.headType.map((t) => (t.attrs.Color1 && t.attrs.Color1.colours ? t.attrs.Color1.colours.map(hexToLinear) : null));
    this.stats = { kicks: [], flyouts: 0, lookChanges: 0 };
  }
  setTheme(theme) {
    this.theme = theme;
    this.colours = resolveTheme(theme);
    this.roleRGB = ROLES.map((r) => this.colours[r]);
  }
  setSpeed(s, grid, tEval) {
    this.speed = s;
    const pos = grid.posAt(tEval);
    for (const inst of this.effects.values()) inst.phasor.setScale((inst.def.scale ?? 1) * s, pos, grid.barAnchor);
  }
  // Start a look (the scene's looks[name]): lines of {group, values, effects}; fade in beats.
  setLook(name, pos, { fade = null } = {}) {
    const look = this.rig.looks[name];
    if (!look) throw new Error(`no look ${name}`);
    this.lookName = name;
    this.stats.lookChanges++;
    this.fromH.set(this.baseH); this.fromC.set(this.baseC);
    // a look is a full state: every head and cell it does not name goes to black
    for (let i = 0; i < this.nH; i++) this.baseH[i * 7 + 2] = 0;
    for (let c = 0; c < this.nC; c++) this.baseC[c * 4] = 0;
    const wanted = new Set();
    this.lines = [];
    for (const line of look.lines || look) {
      if (!line.group) continue;
      const g = this.rig.groups[line.group];
      if (!g) throw new Error(`look ${name}: no group ${line.group}`);
      const v = line.values || {};
      for (let m = 0; m < g.n; m++) {
        const k = g.members[m];
        if (g.kind === "heads") {
          const b = k * 7;
          if (v.Pan !== undefined) this.baseH[b] = v.Pan;
          if (v.Tilt !== undefined) this.baseH[b + 1] = v.Tilt;
          this.baseH[b + 2] = v.Dimmer ?? 0;
          if (v.Zoom !== undefined) this.baseH[b + 3] = v.Zoom;
          this.baseH[b + 4] = v.ColorMix ?? 0;
          this.baseH[b + 5] = Math.max(0, ROLES.indexOf(v.Color || "W"));
          this.baseH[b + 6] = Math.max(0, ROLES.indexOf(v.Color2 || "B"));
        } else if (g.kind === "cells") {
          const b = k * 4;
          this.baseC[b] = v.Dimmer ?? 0;
          this.baseC[b + 1] = v.ColorMix ?? 0;
          this.baseC[b + 2] = Math.max(0, ROLES.indexOf(v.Color || "A"));
          this.baseC[b + 3] = Math.max(0, ROLES.indexOf(v.Color2 || "B"));
        }
      }
      const effs = [];
      for (const e of line.effects || []) {
        const ref = typeof e === "string" ? { name: e } : e;
        const def = { ...(this.rig.effects[ref.name] || {}), ...(ref.with || {}) };
        if (!this.rig.effects[ref.name]) throw new Error(`look ${name}: no effect ${ref.name}`);
        const id = `${line.group}:${ref.name}`;
        wanted.add(id);
        let inst = this.effects.get(id);
        if (!inst) {
          inst = new EffectInstance(id, def, g, { seed: hashSeed(this.seed, id), speed: this.speed, pos });
          this.effects.set(id, inst);
        } else inst.start();
        effs.push(inst);
      }
      this.lines.push({ group: g, effects: effs });
    }
    for (const [id, inst] of this.effects) if (!wanted.has(id)) inst.stop();
    this.fade = { p0: pos, len: fade ?? look.fade ?? 2 };
  }
  // A pad playback at beat position pos. kick: onset on the nearest beat (a press within half a beat of a line lands on
  // it). flyout: onset now.
  pad(kind, vel, pos) {
    if (kind === "kick") {
      const onset = Math.round(pos);
      this.pads.push({ kind, onset, vel });
      this.stats.kicks.push(onset);
      if (this.stats.kicks.length > 256) this.stats.kicks.shift();
    } else if (kind === "flyout") {
      this.pads.push({ kind, onset: pos, vel });
      this.stats.flyouts++;
    }
    while (this.pads.length > 16) this.pads.shift();
  }
  kickLevel(pos) {
    let lv = 0;
    for (const p of this.pads) {
      if (p.kind !== "kick") continue;
      const age = pos - p.onset;
      if (age < -1e-6 || age > 2) continue;                      // within float error of its line it is on it
      lv = Math.max(lv, (0.6 + 0.4 * p.vel) * Math.exp(-Math.max(0, age) / 0.3));
    }
    return lv;
  }
  tick(grid, tEval, dt) {
    const pos = grid.posAt(tEval);
    const ver = grid.ver;
    const nH = this.nH, nC = this.nC;
    // 1. the look's base, crossfading dimmers from the previous look
    const f = this.fade.len > 0 ? Math.min(1, Math.max(0, (pos - this.fade.p0) / this.fade.len)) : 1;
    for (let i = 0; i < nH * 7; i++) {
      const isDim = i % 7 === 2;
      this.tH[i] = isDim ? this.fromH[i] + (this.baseH[i] - this.fromH[i]) * f : this.baseH[i];
    }
    for (let i = 0; i < nC * 4; i++) this.tC[i] = i % 4 === 0 ? this.fromC[i] + (this.baseC[i] - this.fromC[i]) * f : this.baseC[i];
    // 2. effects, in line order
    for (const inst of this.effects.values()) inst.tick(pos, ver);
    for (const line of this.lines) {
      const g = line.group;
      for (const inst of line.effects) {
        if (inst.level <= 0) continue;
        const attrs = inst.def.attrs || [];
        for (let m = 0; m < g.n; m++) {
          const k = g.members[m];
          for (const a of attrs) {
            if (g.kind === "heads") {
              const off = a === "Pan" ? 0 : a === "Tilt" ? 1 : a === "Dimmer" ? 2 : a === "Zoom" ? 3 : a === "ColorMix" ? 4 : -1;
              if (off >= 0) this.tH[k * 7 + off] = inst.apply(a, this.tH[k * 7 + off], m);
            } else if (g.kind === "cells") {
              const off = a === "Dimmer" ? 0 : a === "ColorMix" ? 1 : -1;
              if (off >= 0) this.tC[k * 4 + off] = inst.apply(a, this.tC[k * 4 + off], m);
            }
          }
        }
      }
    }
    for (const [id, inst] of this.effects) if (inst.dead) this.effects.delete(id);
    // 3. playbacks: KICK (HTP lift on the strand) and FLY-OUT (outward tilt and a pop on the beams)
    const kick = this.kickLevel(pos);
    if (kick > 0) {
      for (let i = 0; i < nH; i++) if (this.strandHead[i]) this.tH[i * 7 + 2] = Math.max(this.tH[i * 7 + 2], kick);
      for (let c = 0; c < nC; c++) if (this.strandCell[c] && this.rig.cells.kind[c] === 2) this.tC[c * 4] = Math.max(this.tC[c * 4], kick);
    }
    for (const p of this.pads) {
      if (p.kind !== "flyout") continue;
      for (let i = 0; i < nH; i++) {
        if (this.strandHead[i]) continue;
        const fx = this.rig.fixtures[this.rig.heads[i]];
        const x = this.rig.elements[fx.element].origin[0] + fx.local[0];
        const delay = Math.min(0.5, Math.abs(x) / 40);           // the burst runs outward from the centre over half a beat
        const age = pos - p.onset - delay;
        if (age < 0 || age > 2) continue;
        const env = Math.sin(Math.min(1, age / 2) * Math.PI);
        this.tH[i * 7 + 1] += Math.sign(x || 1) * 28 * env * p.vel;
        this.tH[i * 7 + 2] = Math.max(this.tH[i * 7 + 2], Math.min(1, 0.85 * (1 - age / 2) + 0.15));
      }
    }
    this.pads = this.pads.filter((p) => pos - p.onset < 3);
    // 4-6. masters, colour, physics -> FrameState
    const M = this.masters;
    for (let i = 0; i < nH; i++) {
      const b = i * 7, o = i * HEAD_FLOATS, s = this.slews[i];
      const master = M.grand * (this.strandHead[i] ? M.strand : M.beams);
      const dim = Math.max(0, Math.min(1, s.dim.step(Math.max(0, Math.min(1, this.tH[b + 2])) * master, dt)));
      const pan = s.pan.step(this.tH[b], dt), tilt = s.tilt.step(this.tH[b + 1], dt);
      const zoom = s.zoom.step(this.tH[b + 3] || (this.headType[i].attrs.Zoom && this.headType[i].attrs.Zoom.home) || 2, dt);
      const mix = Math.max(0, Math.min(1, this.tH[b + 4]));
      const c1 = this.roleRGB[this.tH[b + 5] | 0], c2 = this.roleRGB[this.tH[b + 6] | 0];
      let r = c1[0] + (c2[0] - c1[0]) * mix, g = c1[1] + (c2[1] - c1[1]) * mix, bl = c1[2] + (c2[2] - c1[2]) * mix;
      const wheel = this.wheels[i];
      if (wheel) {
        const slot = nearestSlot(wheel, [r, g, bl]);
        const wpos = s.wheel.step(slot, dt);
        const c = wheel[Math.round(wpos)];
        r = c[0]; g = c[1]; bl = c[2];
      }
      const h = this.heads;
      h[o + H.PAN] = pan; h[o + H.TILT] = tilt; h[o + H.DIM] = dim; h[o + H.R] = r; h[o + H.G] = g; h[o + H.B] = bl;
      h[o + H.ZOOM] = zoom; h[o + H.FROST] = 0; h[o + H.IRIS] = 1; h[o + H.GOBO] = 0; h[o + H.GOBOROT] = 0;
      h[o + H.PRISM] = 0; h[o + H.PRISMROT] = 0; h[o + H.SHUTTER] = 1; h[o + H.FOCUS] = 0.5; h[o + H.FLAGS] = 0;
    }
    for (let c = 0; c < nC; c++) {
      const b = c * 4;
      const master = M.grand * M.pixels * (this.strandCell[c] ? M.strand : 1);
      const dim = Math.max(0, Math.min(1, this.tC[b])) * master;
      const mix = Math.max(0, Math.min(1, this.tC[b + 1]));
      const c1 = this.roleRGB[this.tC[b + 2] | 0], c2 = this.roleRGB[this.tC[b + 3] | 0];
      this.pixels[b] = (c1[0] + (c2[0] - c1[0]) * mix) * dim;
      this.pixels[b + 1] = (c1[1] + (c2[1] - c1[1]) * mix) * dim;
      this.pixels[b + 2] = (c1[2] + (c2[2] - c1[2]) * mix) * dim;
      this.pixels[b + 3] = dim;
    }
    return { heads: this.heads, pixels: this.pixels };
  }
}
