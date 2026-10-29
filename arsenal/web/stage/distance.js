// Virtual Stage: camera DISTANCE, its own control on top of the director's shots: arsenal/web/stage/distance.js (pure ES
// module). Tests: tests/stage_distance.test.mjs. Browser receipt: arsenal/lanes/stage_verify.mjs --phases distance.
//
// Daniel, 2026-10-29: "can we think of a control scheme for camera distance so that i can trigger between closeup medium
// and far." His north star for the rig (2026-10-28): "I am trying to figure out how to make the ui be intuitive and allow
// deep expression through simplified complexity. so i can control camera, light, laser and light firing order and
// pattern ..."
//
// WHAT DISTANCE IS. Shot SIZE, the cinematographer's close-up / medium / far: how wide a slice of the room the frame holds
// at the subject (the shot's look point), not metres from it. CLOSE holds 14 m across at the subject (the inner rings
// fill the frame), MEDIUM 34 m (ring 0 with its halo), FAR 80 m (the whole 48 m deck and its towers with room round
// them); between them the value v runs 0..1 on a log scale (MEDIUM is v = 0.5, the geometric middle). The width at the
// subject is 2 d tan(hfov / 2), so the same CLOSE means the same framing on a 34-degree long lens and a 62-degree wide
// one: the long lens stands further back, as a camera operator would.
//
// HOW IT MOVES THE CAMERA. A dolly, never a zoom: the lens, the look point, the roll, the handheld wander and the shot's
// exposure are the director's, untouched. Each frame the camera slides along the line from the subject through the
// shot's own camera position, scaled by k = W(v) / W_ref (W_ref: the shot's own framing, its geometric mean over the
// move), so a moving shot keeps its angle, its motion (a crane that rises still rises, an orbit still orbits, a crash zoom
// still lands) and its subject; only its size changes. Why not mix in FOV: a zoom flattens the room and changes what the
// lens sees of the haze beams side-on, and the per-shot exposure was set for that lens; a dolly keeps both. Why the
// exposure stays: a beam in haze and a lit surface have the same radiance from 14 m as from 80 m (radiance does not fall
// with distance; only the size on screen does), so the shot's EV is right at every distance and an auto-exposure would
// only pump. The receipt measures it (stage_verify --phases distance).
//
// THE LIMITS (every frame, in this order): the shot's comfort range (k in [K_MIN, K_MAX]; the scaled move never faster
// than the house's virtual drone, camera.js DRONE.vmax, where the shot's own speed is known; never nearer the subject than
// 3 m; a shot with distance: false or a dolly zoom keeps its own size); the venue (the floor's x and z, the crowd's heads,
// the roof) and the hall's structure (the deck, the PA hangs, the trusses, the delay towers, the FOH riser); the strand
// and the rings, live: the camera never comes within CLEARANCE_M = 1.5 m of a rung or a ring (camera.js's rule). The
// walk goes from the shot's own position (which the director has already judged clear) toward the wanted distance and
// stops where the first limit bites. A soft margin (2.5 m) is what the camera aims for, eased in over ~0.15 s so a rung
// entering the line never snaps the lens; the 1.5 m rule is a hard clamp under it.
//
// THE TIMING (the round-3 design, docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md
// sections 3, 5, 6): a camera command starts a continuous move from the current pose at once and never cuts at pad
// speed. A press moves v along a quintic from where it is (its speed and acceleration carried, so a second press mid-move
// bends the move instead of kinking it) to the stop, arriving ON the first beat line at least the comfort time away:
// half a beat, or the time the move needs at LOG_RATE_MAX (the subject's size changing at most e^4.5 per second at the
// move's peak: a step close -> medium about 0.36 s, close -> far about 0.73 s). At 150 BPM a step lands on the next beat
// or the one after. The move's duration is captured in seconds at the press (design 6: a clock loss never freezes it).
// SHIFT makes it a clean cut instead, ON the next beat line -- and never within 2 beats of the director's last cut
// (camera.js MIN_SHOT_BEATS); a cut that would fall in the 2 beats before the director's own next cut waits and lands
// with it (one cut, the new shot at the new size). Pressing the active stop again hands distance back to the director
// (auto): a blend over two beats (design 6: "Camera handback blends from the current pose to the currently advancing
// director path over two beats"), landing on a beat line. Esc does that too (and gives the shot back to the director).
//
// THE FADER (KeyLab F8, CC 112): continuous v with SOFT TAKEOVER. The fader does nothing until it passes through the
// value the camera has now (in auto: the shot's own size, vAuto), so picking it up never jumps the camera; caught, it
// drives v through a critically damped follower at the same comfort rate. A key press or a handback lets go of it (it
// must pass through the new value again).

import { DRONE, NOMINAL_BPM, CLEARANCE_M, prepareShot, shotPose, segmentHitsBox, clearanceToStrand, clearanceToRings } from "./camera.js";

export const DISTANCE_API = "arsenal.stage-distance/v1";
export const STOPS = Object.freeze({ close: 0, medium: 0.5, far: 1 });
export const STOP_ORDER = Object.freeze(["close", "medium", "far"]);
export const WIDTH = Object.freeze({ close: 14, far: 80 });           // m across the frame at the subject, at v = 0 and v = 1
export const LN_RANGE = Math.log(WIDTH.far / WIDTH.close);
export const LOG_RATE_MAX = 4.5;      // the comfort: peak d(ln size)/dt of a move, per second
export const MIN_MOVE_BEATS = 0.5;    // a move never lands sooner than half a beat after the press
export const HANDBACK_BEATS = 2;      // the blend back to the director (round-3 design, section 6)
export const SOFT_M = 2.5;            // the clearance the camera aims for (the 1.5 m rule is the hard clamp)
export const SUBJECT_MIN_M = 3;       // never nearer the subject than this
export const K_MIN = 0.12, K_MAX = 4; // the scale on a shot's own size, before the other limits
export const TAKEOVER_EPS = 0.03;     // the fader catches within this of the live value (or on crossing it)
const DEG = Math.PI / 180;
const MIN_SHOT_BEATS = 2;
const clamp01 = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x);
// the setting may sit a little past the stops (a shot wider than FAR, caught by the fader without a jump)
const clampV = (x) => (x <= -0.5 ? -0.5 : x >= 1.5 ? 1.5 : x);
export const KNEE = 0.06;             // ln size: the width of the smooth saturation into a limit
// a smooth minimum (C1): min(a, b) away from the knee, a quadratic blend within it (a move eases into a limit, no kink)
export function softMin(a, b, k = KNEE) { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - (h * h * k) / 4; }

// the distance from p to an axis-aligned box {c, s} (0 inside), and whether p is inside it grown by m
export function boxDistance(p, b) {
  const qx = Math.max(0, Math.abs(p[0] - b.c[0]) - b.s[0] / 2), qy = Math.max(0, Math.abs(p[1] - b.c[1]) - b.s[1] / 2), qz = Math.max(0, Math.abs(p[2] - b.c[2]) - b.s[2] / 2);
  return Math.hypot(qx, qy, qz);
}
export const insideBox = (p, b, m = 0) => Math.abs(p[0] - b.c[0]) <= b.s[0] / 2 + m && Math.abs(p[1] - b.c[1]) <= b.s[1] / 2 + m && Math.abs(p[2] - b.c[2]) <= b.s[2] / 2 + m;
export const widthOf = (v) => WIDTH.close * Math.exp(LN_RANGE * v);
export const vOfWidth = (w) => Math.log(w / WIDTH.close) / LN_RANGE;
// the nearest named stop to v (for the HUD), and the stop a key code names
export const stopOf = (v) => (v < 0.25 ? "close" : v < 0.75 ? "medium" : "far");
export const KEY_STOPS = Object.freeze({ KeyQ: "close", KeyW: "medium", KeyE: "far" });

// The comfort time (seconds) of a move of dl in ln size: a minimum-jerk move peaks at 1.875 x its mean rate.
export function comfortSeconds(dl) { return 1.875 * Math.abs(dl) / LOG_RATE_MAX; }
// The beat line a move lands on: the first whole beat at least max(minBeats, the comfort time) after pos.
export function landingBeat(pos, spb, dl, minBeats = MIN_MOVE_BEATS) {
  const need = Math.max(minBeats, comfortSeconds(dl) / Math.max(1e-6, spb));
  return Math.ceil(pos + need - 1e-9);
}
// The beat a clean cut lands on: the next beat line after pos, never within MIN_SHOT_BEATS of the director's last cut;
// one that would fall in the 2 beats before the director's own next cut waits for it (one cut, not two).
export function cutBeat(pos, lastCutPos = -Infinity, nextCutPos = Infinity) {
  let at = Math.max(Math.floor(pos + 1e-9) + 1, Math.ceil(lastCutPos + MIN_SHOT_BEATS - 1e-9));
  if (nextCutPos > at - 1e-9 && nextCutPos - at < MIN_SHOT_BEATS - 1e-9) at = nextCutPos;
  return at;
}

// ------------------------------------------------------------------------------------------- the quintic channel --
// One scalar with its velocity and acceleration: a quintic from (x0, v0, a0) to (x1, 0, 0) over T seconds (minimum jerk
// when it starts at rest), or a critically damped follow of a moving target (the fader) at a capped speed.
export function quintic(x0, v0, a0, x1, T) {
  const D = x1 - x0, T2 = T * T, T3 = T2 * T;
  return [x0, v0, a0 / 2,
          (20 * D - 12 * v0 * T - 3 * a0 * T2) / (2 * T3),
          (-30 * D + 16 * v0 * T + 3 * a0 * T2) / (2 * T3 * T),
          (12 * D - 6 * v0 * T - a0 * T2) / (2 * T3 * T2)];
}
export class Channel {
  constructor(x = 0) { this.x = x; this.v = 0; this.a = 0; this.seg = null; this.follow = null; }
  // a move to x1 landing T seconds after t, from the current state (a move under way bends, never kinks)
  to(x1, t, T) {
    if (!(T > 1e-6)) { this.set(x1); return; }
    if (this.seg) this.tick(t, 0);            // the state now, not at the last frame (a press lands between frames)
    this.seg = { t0: t, T, x1, c: quintic(this.x, this.v, this.a, x1, T) };
    this.follow = null;
  }
  set(x) { this.x = x; this.v = 0; this.a = 0; this.seg = null; this.follow = null; }
  // follow a target that keeps moving (the fader): critically damped at omega, speed capped at vmax (units a second)
  track(target, omega, vmax) { this.seg = null; this.follow = { target, omega, vmax }; }
  get moving() { return !!this.seg || (!!this.follow && Math.abs(this.follow.target - this.x) > 1e-4); }
  tick(t, dt) {
    if (this.seg) {
      const s = this.seg, c = s.c, u = Math.min(s.T, Math.max(0, t - s.t0));
      if (t - s.t0 >= s.T - 1e-9) { this.x = s.x1; this.v = 0; this.a = 0; this.seg = null; return this.x; }
      this.x = c[0] + u * (c[1] + u * (c[2] + u * (c[3] + u * (c[4] + u * c[5]))));
      this.v = c[1] + u * (2 * c[2] + u * (3 * c[3] + u * (4 * c[4] + u * 5 * c[5])));
      this.a = 2 * c[2] + u * (6 * c[3] + u * (12 * c[4] + u * 20 * c[5]));
    } else if (this.follow && dt > 0) {
      const f = this.follow, w = f.omega, h = Math.min(dt, 0.1);
      // semi-implicit critically damped spring, its speed capped
      const acc = w * w * (f.target - this.x) - 2 * w * this.v;
      let v = this.v + acc * h;
      if (v > f.vmax) v = f.vmax; else if (v < -f.vmax) v = -f.vmax;
      this.a = (v - this.v) / h; this.v = v; this.x += v * h;
    }
    return this.x;
  }
}

// ------------------------------------------------------------------------------------------- a shot's own size --
// W_ref (the width the shot frames at its subject: 2 d tan(hfov / 2) with d and hfov their geometric means over the
// move), vAuto (where that sits on the scale), the comfort range of k, and whether the shot keeps its own size.
export function shotFrame(shot, samples = 24) {
  const s = shot._ease ? shot : prepareShot(shot);
  if (s.distance === false || s.dolly_zoom) return { fixed: true, why: s.dolly_zoom ? "dolly zoom" : "fixed by the shot", wRef: NaN, vAuto: NaN, kMin: 1, kMax: 1 };
  const tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  let ld = 0, lt = 0, vmax = 0;
  const secs = ((s.bars ?? 4) * 4 * 60) / NOMINAL_BPM, prev = [0, 0, 0];
  for (let k = 0; k <= samples; k++) {
    shotPose(s, k / samples, 0, tmp);
    const d = Math.max(0.5, Math.hypot(tmp.pos[0] - tmp.look[0], tmp.pos[1] - tmp.look[1], tmp.pos[2] - tmp.look[2]));
    ld += Math.log(d); lt += Math.log(Math.tan((Math.max(1, Math.min(170, tmp.hfov)) * DEG) / 2));
    if (k) vmax = Math.max(vmax, Math.hypot(tmp.pos[0] - prev[0], tmp.pos[1] - prev[1], tmp.pos[2] - prev[2]) / (secs / samples));
    prev[0] = tmp.pos[0]; prev[1] = tmp.pos[1]; prev[2] = tmp.pos[2];
  }
  const dRef = Math.exp(ld / (samples + 1)), wRef = 2 * dRef * Math.exp(lt / (samples + 1));
  const lim = s.distance && typeof s.distance === "object" ? s.distance : {};
  // the drone's speed: a scaled move is at most k times as fast (about a still subject), so a fast shot's FAR is capped
  // there -- never below its own size (the director dealt it at that speed)
  const kSpeed = vmax > 1e-6 ? Math.max(1, DRONE.vmax / vmax) : Infinity;
  return { fixed: false, wRef, dRef, vAuto: vOfWidth(wRef), speed: vmax,
           kMin: lim.k_min ?? K_MIN, kMax: Math.min(lim.k_max ?? K_MAX, kSpeed) };
}

// --------------------------------------------------------------------------------------------- the room's limits --
// What the walk asks of a camera position: inside the venue (the floor's x and z less a margin, above the crowd's heads,
// under the roof), the segment from the last sample not through the hall's structure, and the live clearance to the
// strand and the rings. world: {venue, boxes ([{c, s}] from rig.js hallStructure, solid and truss), z (the rungs' z)}.
export function makeRoom(venue, boxes, margin = 1) {
  const fx = (venue.floor && venue.floor.x) || [-38, 38], fz = (venue.floor && venue.floor.z) || [-24, 96];
  const lo = [fx[0] + margin, Math.max(1.8, (venue.crowd_y ?? 1.9) - 0.1), fz[0] + margin];
  const hi = [fx[1] - margin, (venue.roof_y ?? 38) - 2, fz[1] - margin];
  // the structure, grown by half a metre (the lens is never inside a truss)
  const grown = (boxes || []).map((b) => ({ c: b.c, s: [b.s[0] + 1, b.s[1] + 1, b.s[2] + 1], what: b.what }));
  return {
    lo, hi, boxes: grown, raw: (boxes || []).map((b) => ({ c: b.c, s: b.s, what: b.what })),
    inside: (p) => p[0] >= lo[0] && p[0] <= hi[0] && p[1] >= lo[1] && p[1] <= hi[1] && p[2] >= lo[2] && p[2] <= hi[2],
    // a shot mounted on the structure (the truss's own view) starts inside its grown box: that box is its mount, not a wall
    blocked: (p, q, start = null) => {
      for (const b of grown) if (segmentHitsBox(p, q, b) && !(start && insideBox(start, b))) return b.what || "structure";
      return null;
    },
  };
}

// --------------------------------------------------------------------------------------------- the distance layer --
export class CameraDistance {
  // opts: {room (makeRoom), z (the rungs' z, camera.js cameraModel), rings (the model's home annuli)}
  constructor(opts = {}) {
    this.room = opts.room || null;
    this.z = opts.z || null;
    this.homeRings = opts.rings || [];
    this.v = new Channel(STOPS.medium);     // the setting, 0 = CLOSE .. 1 = FAR
    this.w = new Channel(0);                // how much of it applies: 0 = auto (the director's own size), 1 = manual
    this.mode = "auto";                     // "auto" | "manual"
    this.stop = null;                       // the stop a key asked for (null: the fader's own value, or auto)
    this.source = null;                     // "key" | "cut" | "fader" | null
    this.landAt = null;                     // the beat the move lands on
    this.pending = null;                    // a clean cut waiting for its beat {at, stop | null (auto)}
    this.fad = { caught: false, side: 0, value: null };   // the fader's soft takeover
    this.geo = null;                        // the last frame's shot pose and rig, for planning a press against the room
    this.frames = new Map();                // shot id -> shotFrame
    this.lamPrev = 0; this.lamShot = null;  // the scale applied last frame (ln size) and on which shot
    this.escapes = 0;                       // frames the rig moved into the lens and the camera stepped back
    this.last = { t: null, lam: 0, k: 1, clamp: null, fixed: null, shot: null };
    this.cuts = [];                         // [{pos, at, stop}] for receipts (bounded)
    this.moves = [];                        // [{pos, landAt, stop, kind}] (bounded)
    this.changed = true;
  }
  frameOf(shot) {
    let f = this.frames.get(shot.id);
    if (!f) { f = shotFrame(shot); this.frames.set(shot.id, f); }
    return f;
  }
  _log(list, e) { if (list.length < 256) list.push(e); }
  // ln of the size change the setting asks of this shot now
  _lamFor(f, v, w) { return f.fixed ? 0 : w * (Math.log(widthOf(v)) - Math.log(f.wRef)); }

  // A stop pressed ("close" | "medium" | "far"). ctx: {t (seconds), pos (beat position), spb (seconds a beat), shot (the
  // shot on screen, prepared), cut (Shift: a clean cut), lastCutPos, nextCutPos}. The active stop again hands back.
  press(stop, ctx) {
    if (!(stop in STOPS)) return null;
    this.fad.caught = false;
    if (this.mode === "manual" && this.stop === stop && !this.pending) return this.auto(ctx);
    const vT = STOPS[stop];
    if (ctx.cut) {
      const at = cutBeat(ctx.pos, ctx.lastCutPos, ctx.nextCutPos);
      this.pending = { at, stop, tFallback: ctx.t + (at - ctx.pos) * ctx.spb + 0.25 };
      this.mode = "manual"; this.stop = stop; this.source = "cut"; this.landAt = at; this.changed = true;
      this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop, kind: "cut" });
      return { kind: "cut", at };
    }
    this.pending = null;
    const f = ctx.shot ? this.frameOf(ctx.shot) : { fixed: false, wRef: widthOf(STOPS.medium) };
    const lamNow = this._lamFor(f, this.v.x, this.w.x);
    // the move is planned to what the room allows this shot now (the venue's edge, the rig, the shot's range), so it
    // decelerates into a limit instead of meeting it at speed; the stop asked for stays the stop shown
    const lamR = f.fixed ? 0 : this._reach(f, ctx.shot, this._lamFor(f, vT, 1));
    const vEff = f.fixed ? vT : clampV(vOfWidth(f.wRef * Math.exp(lamR)));
    const at = landingBeat(ctx.pos, ctx.spb, f.fixed ? 0 : lamR - lamNow);
    const T = (at - ctx.pos) * ctx.spb;
    if (this.w.x <= 1e-9 && !this.w.seg) this.v.set(vEff);   // from auto: the setting is the stop, the weight carries the move
    else this.v.to(vEff, ctx.t, T);
    if (this.w.x < 1 - 1e-9 || this.w.seg) this.w.to(1, ctx.t, T);
    this.mode = "manual"; this.stop = stop; this.source = "key"; this.landAt = at; this.changed = true;
    this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop, kind: "move", ...(vEff !== vT ? { held: +vEff.toFixed(3) } : {}) });
    return { kind: "move", at, seconds: T, v: vEff };
  }
  // The scale (ln size) the room lets this shot reach toward lamT from where the camera is, on the last frame's pose:
  // the shot's comfort range, then the soft stop of the walk (the rig, the walls, the structure).
  _reach(f, shot, lamT) {
    const G = this.geo;
    if (!G || G.shot !== shot.id) return lamT;
    const d0 = Math.hypot(G.pos[0] - G.look[0], G.pos[1] - G.look[1], G.pos[2] - G.look[2]);
    if (!(d0 > 1e-3)) return lamT;
    const lo = Math.log(Math.min(1, Math.max(f.kMin, SUBJECT_MIN_M / d0))), hi = Math.log(Math.max(1, f.kMax));
    const want = Math.max(lo, Math.min(hi, lamT));
    const u = [(G.pos[0] - G.look[0]) / d0, (G.pos[1] - G.look[1]) / d0, (G.pos[2] - G.look[2]) / d0];
    const W = { look: G.look, u, d0, poses: G.poses, rings: G.rings, mount: G.pos };
    const start = this.lamPrev, dir = Math.sign(want - start);
    if (!dir) return want;
    // planned a knee inside the soft stop, where the smooth saturation leaves the move exactly as planned
    const end = this._walk(W, start, dir > 0 ? hi : lo).soft;
    if (Math.abs(end - start) > Math.abs(want - start) + KNEE) return want;
    return dir > 0 ? Math.max(start, Math.min(want, end - KNEE)) : Math.min(start, Math.max(want, end + KNEE));
  }
  // The receipts' door: a stop (or "auto") at once, no move, no beat (a still at each size)
  setNow(stop) {
    this.pending = null; this.fad.caught = false; this.landAt = null; this.changed = true;
    if (stop === "auto") { this.w.set(0); this.mode = "auto"; this.stop = null; this.source = null; return; }
    this.v.set(STOPS[stop]); this.w.set(1); this.mode = "manual"; this.stop = stop; this.source = "key";
  }
  // Back to the director: a blend over two beats (or the comfort time, if longer), landing on a beat line. cut: at once
  // on the next beat line instead.
  auto(ctx) {
    this.fad.caught = false;
    if (this.mode === "auto" && !this.pending && !this.w.seg && this.w.x <= 1e-9) return null;
    const wasManual = this.mode === "manual";
    this.mode = "auto"; this.stop = null; this.source = null; this.changed = true;
    if (ctx.cut) {
      const at = cutBeat(ctx.pos, ctx.lastCutPos, ctx.nextCutPos);
      this.pending = { at, stop: null, tFallback: ctx.t + (at - ctx.pos) * ctx.spb + 0.25 };
      this.landAt = at;
      this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop: "auto", kind: "cut" });
      return { kind: "cut", at };
    }
    this.pending = null;
    const f = ctx.shot ? this.frameOf(ctx.shot) : { fixed: true };
    const at = landingBeat(ctx.pos, ctx.spb, f.fixed ? 0 : this._lamFor(f, this.v.x, this.w.x), HANDBACK_BEATS);
    this.w.to(0, ctx.t, (at - ctx.pos) * ctx.spb);
    this.landAt = at;
    if (wasManual || this.w.seg) this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop: "auto", kind: "handback" });
    return { kind: "handback", at };
  }
  // The fader (0..1, KeyLab F8 or the HUD slider). takeover: soft (the hardware fader catches the live value first);
  // false for a control that shows the live value under the pointer (the HUD slider): it takes over at once, still
  // through the follower. ctx: {t, shot}.
  fader(value, ctx, { takeover = true } = {}) {
    const x = clamp01(Number(value));
    if (!Number.isFinite(x)) return null;
    const F = this.fad;
    const f = ctx.shot ? this.frameOf(ctx.shot) : null;
    const live = this.mode === "manual" || this.w.x > 1e-9 ? this.v.x : f && !f.fixed ? f.vAuto : this.v.x;
    if (!F.caught) {
      const side = Math.sign(x - live);
      // caught: within a hair of the live value, on crossing it, or at the end of travel when the live value lies past it
      const crossed = (F.value !== null && F.side !== 0 && side !== 0 && side !== F.side) || (live > 1 && x >= 0.99) || (live < 0 && x <= 0.01);
      F.value = x; F.side = side;
      if (takeover && !(Math.abs(x - live) <= TAKEOVER_EPS || crossed)) return { caught: false, live };
      F.caught = true;
      // caught from auto: the setting starts where the camera is (the shot's own size), so nothing jumps
      if (this.mode === "auto" && this.w.x <= 1e-9) { this.v.set(f && !f.fixed ? clampV(f.vAuto) : x); this.w.set(1); }
      else if (this.w.x < 1 - 1e-9 || this.w.seg) this.w.to(1, ctx.t, Math.max(0.2, comfortSeconds(0.5)));
      this.pending = null;
    }
    F.value = x;
    this.mode = "manual"; this.stop = null; this.source = "fader"; this.landAt = null; this.changed = true;
    this.v.track(x, 12, LOG_RATE_MAX / LN_RANGE);
    return { caught: true, live };
  }

  // Per frame, after the director: moves the pose's camera position (in place) and returns the status. ctx: {t, pos,
  // dt, cut (the director cut this frame), poses (the live rung poses), rings (live annuli or null)}.
  apply(pose, shot, ctx) {
    const t = ctx.t, dt = this.last.t === null ? 0 : Math.max(0, Math.min(0.1, t - this.last.t));
    this.last.t = t;
    let cutNow = false;
    const P = this.pending;
    if (P && (ctx.pos >= P.at - 1e-6 || t >= P.tFallback)) {
      if (P.stop) { this.v.set(STOPS[P.stop]); this.w.set(1); } else this.w.set(0);
      this.pending = null; cutNow = true; this.changed = true;
      this._log(this.cuts, { pos: +ctx.pos.toFixed(4), at: P.at, stop: P.stop || "auto", why: "shift" });
    }
    this.v.tick(t, dt); this.w.tick(t, dt);
    this.v.x = clampV(this.v.x); this.w.x = clamp01(this.w.x);
    if (this.landAt !== null && !this.v.seg && !this.w.seg && !this.pending) this.landAt = null;
    pose.distCut = cutNow;
    const reset = !!ctx.cut || cutNow || !shot || this.lamShot !== (shot && shot.id);
    // the shot's own pose and the rig this frame (a press plans its move against them)
    if (shot) this.geo = { shot: shot.id, pos: pose.pos.slice(), look: pose.look.slice(), poses: ctx.poses, rings: ctx.rings || this.homeRings };
    // auto, and resting: the director's pose exactly. A handback the rig blocked ends here with a cut on its beat line.
    if (this.w.x <= 0 && !this.w.seg) {
      if (Math.abs(this.lamPrev) > 0.02 && !reset) {
        pose.distCut = true;
        this._log(this.cuts, { pos: +ctx.pos.toFixed(4), at: +ctx.pos.toFixed(4), stop: "auto", why: "handback-blocked" });
      }
      this._rest(shot); return this.last;
    }
    if (!shot) return this.last;
    const f = this.frameOf(shot);
    if (f.fixed) { this._rest(shot); this.last.fixed = f.why; return this.last; }
    const look = pose.look, p = pose.pos;
    const dx = p[0] - look[0], dy = p[1] - look[1], dz = p[2] - look[2];
    const d0 = Math.hypot(dx, dy, dz);
    if (!(d0 > 1e-3)) { this._rest(shot); return this.last; }
    const u = [dx / d0, dy / d0, dz / d0];
    // the intent, eased into the shot's comfort range and the subject floor (static limits: a smooth saturation)
    const lo = Math.log(Math.min(1, Math.max(f.kMin, SUBJECT_MIN_M / d0))), hi = Math.log(Math.max(1, f.kMax));
    const lamWant = this._lamFor(f, this.v.x, this.w.x);
    const lamCmd = lamWant >= 0 ? Math.max(0, softMin(lamWant, hi)) : -Math.max(0, softMin(-lamWant, -lo));
    let clamp = Math.abs(lamWant - lamCmd) > 0.02 ? (lamWant < 0 && d0 * Math.exp(lo) <= SUBJECT_MIN_M + 1e-6 ? "subject" : "comfort") : null;
    const W = { look, u, d0, poses: ctx.poses, rings: ctx.rings || this.homeRings, mount: p.slice() };
    // where the camera starts this frame: where it was (the same scale on the shot's new pose); after a cut, the wanted
    // place if it is clear, else the shot's own place
    let start = reset ? 0 : this.lamPrev;
    if (reset && this._field(W, lamCmd).c >= SOFT_M) start = lamCmd;
    // escape: the rig moved into the lens (or the shot carried the lens into it): back toward the shot's own place, now
    if (start !== 0 && this._field(W, start).c < CLEARANCE_M) {
      start = this._walk(W, start, 0).firstClear;
      this.escapes++;
    }
    let lam = start;
    const dir = Math.sign(lamCmd - start);
    if (dir) {
      // the walk toward the far end of the range this way: the soft stop (nearer than 2.5 m to the rig, 1 m to a wall or the
      // structure, and getting nearer) and the hard one (1.5 m, the wall, through a truss); the move eases into the soft stop
      const W2 = this._walk(W, start, dir > 0 ? hi : lo);
      const gS = Math.abs(W2.soft - start), gH = Math.abs(W2.hard - start), gC = Math.abs(lamCmd - start);
      const g = Math.min(Math.max(0, softMin(gC, gS)), gH);
      lam = start + dir * g;
      if (gC - g > 0.02) clamp = W2.why || clamp;
      // the fader's follower is aimed at what the room allows, so it decelerates into the limit
      const fl = this.v.follow;
      if (fl && this.w.x >= 1 - 1e-9 && !this.w.seg) {
        const vS = vOfWidth(f.wRef * Math.exp(W2.soft - dir * KNEE));
        if (dir > 0 && fl.target > vS) fl.target = Math.max(this.v.x, vS);
        if (dir < 0 && fl.target < vS) fl.target = Math.min(this.v.x, vS);
      }
    }
    const k = Math.exp(lam);
    p[0] = look[0] + u[0] * d0 * k; p[1] = look[1] + u[1] * d0 * k; p[2] = look[2] + u[2] * d0 * k;
    this.lamPrev = lam; this.lamShot = shot.id;
    this.last.shot = shot.id; this.last.fixed = null; this.last.lam = lam; this.last.k = k; this.last.clamp = clamp;
    return this.last;
  }
  _rest(shot) {
    this.last.lam = 0; this.last.k = 1; this.last.clamp = null; this.last.shot = shot ? shot.id : null; this.last.fixed = null;
    this.lamPrev = 0; this.lamShot = shot ? shot.id : null;
  }
  // The room's clearance for the camera placed at scale e^lam on the ray, as one number: the rig's (the strand, the
  // rings), the walls' plus 1.5 m, the structure's plus 1.0 m (a box the shot is mounted in does not count), so the hard
  // rule is c >= 1.5 m everywhere and the soft one c >= 2.5 m.
  _field(W, lam, out = [0, 0, 0]) {
    const d = W.d0 * Math.exp(lam);
    out[0] = W.look[0] + W.u[0] * d; out[1] = W.look[1] + W.u[1] * d; out[2] = W.look[2] + W.u[2] * d;
    let c = Infinity, why = null;
    if (W.poses && this.z) { const r = clearanceToStrand(out, W.poses, this.z); if (r < c) { c = r; why = "clearance"; } }
    if (W.rings && W.rings.length) { const r = clearanceToRings(out, W.rings); if (r < c) { c = r; why = "clearance"; } }
    const room = this.room;
    if (room) {
      const wall = Math.min(out[0] - room.lo[0], room.hi[0] - out[0], out[1] - room.lo[1], room.hi[1] - out[1], out[2] - room.lo[2], room.hi[2] - out[2]) + CLEARANCE_M;
      if (wall < c) { c = wall; why = "venue"; }
      for (const b of room.raw) {
        if (insideBox(W.mount, b, 0.5)) continue;
        const s = boxDistance(out, b) + 1.0;
        if (s < c) { c = s; why = b.what || "structure"; }
      }
    }
    return { c, why, q: out };
  }
  // From lam a toward lam b in steps of 4 % of the distance (never more than 2.5 m, so no 1.5 m is stepped over): the
  // furthest scale that keeps the soft rule (a sample under 2.5 m that is getting nearer stops it), the furthest that
  // keeps the hard rule, the first hard-clear one (for an escape), and what stopped it.
  _walk(W, a, b) {
    const dir = Math.sign(b - a);
    const f0 = this._field(W, a), prev = f0.q.slice();
    let soft = a, hard = a, firstClear = f0.c >= CLEARANCE_M ? a : null, why = null, softOk = true, cPrev = f0.c;
    if (!dir) return { soft, hard, firstClear: firstClear ?? a, why };
    let lam = a;
    for (let n = 0; n < 600; n++) {
      const d = W.d0 * Math.exp(lam);
      const step = Math.min(2.5, Math.max(0.2, 0.04 * d)) / Math.max(1e-6, d);
      const ln = dir > 0 ? Math.min(b, lam + step) : Math.max(b, lam - step);
      const fq = this._field(W, ln);
      const through = this.room ? this.room.blocked(prev, fq.q, W.mount) : null;
      if (firstClear === null) { if (fq.c >= CLEARANCE_M && !through) { firstClear = ln; soft = hard = ln; } }
      else if (fq.c < CLEARANCE_M || through) { why = why || (through ? through : fq.why); break; }
      else {
        hard = ln;
        if (softOk && (fq.c >= SOFT_M || fq.c >= cPrev - 1e-9)) soft = ln;
        else if (softOk) { softOk = false; why = why || fq.why; }
      }
      cPrev = fq.c; prev[0] = fq.q[0]; prev[1] = fq.q[1]; prev[2] = fq.q[2]; lam = ln;
      if (ln === b) break;
    }
    return { soft, hard, firstClear: firstClear ?? b, why };
  }
  // what the HUD and the phone segment show
  status(shot = null) {
    const f = shot ? this.frameOf(shot) : null;
    return { mode: this.mode, stop: this.stop, source: this.source, v: +this.v.x.toFixed(3), w: +this.w.x.toFixed(3),
             moving: this.v.moving || this.w.moving || !!this.pending, landAt: this.landAt, pending: this.pending ? { ...this.pending } : null,
             k: +this.last.k.toFixed(3), clamp: this.last.clamp, fixed: this.last.fixed,
             vAuto: f && !f.fixed ? +clamp01(f.vAuto).toFixed(3) : null, fader: { caught: this.fad.caught, value: this.fad.value } };
  }
  // the HUD's words: "distance auto (as shot: far) . Q W E", "distance CLOSE (manual) -> beat 133", "distance 0.42 (F8)"
  hudText(shot = null) {
    const s = this.status(shot);
    const held = s.clamp ? ` · held at ${s.clamp === "clearance" ? "1.5 m+ from the rig" : s.clamp === "venue" ? "the venue's edge" : s.clamp === "subject" ? "3 m from the subject" : s.clamp === "comfort" ? "the shot's limit" : `the ${s.clamp}`}` : "";
    const fixed = s.fixed ? ` · this shot keeps its size (${s.fixed})` : "";
    const land = s.pending ? ` · cut on beat ${s.pending.at}` : s.landAt !== null ? ` → beat ${s.landAt}` : "";
    if (s.mode === "auto") {
      const back = s.w > 0 || s.pending ? " (handing back)" : "";
      return `distance auto${back}${s.vAuto !== null ? ` (as shot: ${stopOf(s.vAuto)})` : ""}${land}${fixed} · Q W E`;
    }
    const what = s.source === "fader" ? `${s.v.toFixed(2)} (F8)` : `${(s.stop || stopOf(s.v)).toUpperCase()}`;
    return `distance ${what} manual${land}${held}${fixed} · ${s.stop ? `${{ close: "Q", medium: "W", far: "E" }[s.stop]} again` : "Esc"} = auto`;
  }
  // a change since the last call (for the page's "arsenal:camdist" event: only when something changed, never per frame)
  takeChange() { const c = this.changed; this.changed = false; return c; }
}
