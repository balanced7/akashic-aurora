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
// the roof) and the RIGGING GRID (the truss render.js draws across the whole floor at grid_y: a shot below it never
// lifts the lens past 1 m under its beams, a shot above it never drops past 1 m over them); the hall's structure (the
// deck, the PA hangs, the trusses, the delay towers, the FOH riser); the strand and the rings, live: never within
// CLEARANCE_M = 1.5 m of a rung or a ring (camera.js's rule). Each frame the room is walked along the shot's line from the
// shot's own position (which the director has judged clear) toward the size asked for, sphere-traced so no limit is
// stepped over and bisected to the exact boundary: the soft stop (2.5 m from the rig, 1 m inside a wall) is the goal, the
// 1.5 m rule the hard one. The same walk is made on the shot's own path half a second ahead, so a rung or a wall the
// move is about to meet holds the camera before it arrives, never after. The camera FOLLOWS the goal (never jumps to it):
// at most e^4.5 a second of size change (LOG_RATE_MAX) and LOG_ACCEL_MAX of its acceleration, braking into a limit, and it
// rides the command exactly whenever nothing limits it. If the rig still reaches the lens faster than that (a formation
// swinging into it), the camera does not slide through the rule: it CUTS to the clear size (a logged cut, pose.distCut).
//
// THE TIMING (the round-3 design, docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md
// sections 3, 5, 6): a camera command starts a continuous move from the current pose at once and never cuts at pad
// speed. A press moves v along a quintic from where it is (its speed and acceleration carried, so a second press mid-move
// bends the move instead of kinking it) to the stop, arriving ON the first beat line at least the comfort time away:
// half a beat, or the time the move needs at LOG_RATE_MAX (the subject's size changing at most e^4.5 per second at the
// move's peak: a step close -> medium about 0.36 s, close -> far about 0.73 s). At 150 BPM a step lands on the next beat
// or the one after. The move's duration is captured in seconds at the press (design 6: a clock loss never freezes it).
// SHIFT makes it a clean cut instead, ON the next beat line -- and never within 2 beats of the last cut (the director's,
// a C-key shot, or a distance cut: stage.js writes them all into director.lastCutPos; camera.js MIN_SHOT_BEATS); a cut
// that would fall in the 2 beats before the director's own next cut (his next entry, or a guard or swap he has scheduled)
// waits and lands with it (one cut, the new shot at the new size). A move already under way when Shift is pressed eases
// to rest within a quarter second (no jolt), then nothing moves until the cut. Pressing the active stop again hands distance back to the director
// (auto): a blend over two beats (design 6: "Camera handback blends from the current pose to the currently advancing
// director path over two beats"), landing on a beat line. Esc does that too (and gives the shot back to the director).
//
// THE FADER (KeyLab F8, CC 112): continuous v with SOFT TAKEOVER. The fader does nothing until it passes through the
// value the camera has now (in auto: the shot's own size, vAuto), so picking it up never jumps the camera; caught, it
// drives v through a critically damped follower at the same comfort rate. A key press or a handback lets go of it (it
// must pass through the new value again: its side of the live value is forgotten with it).

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
export const LOG_ACCEL_MAX = 25;      // the comfort of a held camera: its size's acceleration, ln a second a second
export const LOOKAHEAD_S = Object.freeze([0.15, 0.3, 0.45]);   // how far ahead on the shot's own path the room is read
export const SETTLE_S = 0.25;         // a move in flight when Shift is pressed eases to rest within this
export const GRID_MARGIN_M = 1;       // the lens stays this far from the rigging grid's beams (above or below them)
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
  // a move (or a follow) in flight eases to rest over T seconds from its current speed (no kink), then holds
  settle(t, T) {
    if (this.seg) this.tick(t, 0);
    else if (!this.follow) return;
    // from speed v and acceleration a to rest: the quintic whose fifth-order term vanishes, so its speed is
    // (1-s)^2 (v (1+2s) + a T s) -- never reversing (a braking a shortens T until that holds)
    if (this.a * this.v < 0) T = Math.min(T, (3 * Math.abs(this.v)) / Math.abs(this.a));
    if (!(T > 1e-3)) { this.set(this.x); return; }
    const x1 = this.x + (this.v * T) / 2 + (this.a * T * T) / 12;
    this.seg = { t0: t, T, x1, c: quintic(this.x, this.v, this.a, x1, T) };
    this.follow = null;
  }
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
// The rigging grid render.js draws (the bowl, "the rigging grid": beams along z at grid_y, 0.5 m deep; beams along x at
// grid_y + 0.6, 0.35 m deep) as one layer across the whole floor: its bottom and top. Keep in step with render.js.
export function gridLayer(venue) { const gy = venue.grid_y ?? 33; return { lo: gy - 0.25, hi: gy + 0.6 + 0.175 }; }
// What the walk asks of a camera position: inside the venue (the floor's x and z less a margin, above the crowd's heads,
// under the roof) on the shot's own side of the rigging grid, the segment from the last sample not through the hall's
// structure, and the live clearance to the strand and the rings. boxes: [{c, s}] from rig.js hallStructure (solid and
// truss). band(mount): the box a camera may stand in for a shot whose own camera is at mount (below the grid: its ceiling
// is GRID_MARGIN_M under the beams; above it: its floor GRID_MARGIN_M over them; widened to the shot's own camera where
// that stands outside it). inside(p, mount = p): p in that box.
export function makeRoom(venue, boxes, margin = 1) {
  const fx = (venue.floor && venue.floor.x) || [-38, 38], fz = (venue.floor && venue.floor.z) || [-24, 96];
  const lo = [fx[0] + margin, Math.max(1.8, (venue.crowd_y ?? 1.9) - 0.1), fz[0] + margin];
  const hi = [fx[1] - margin, (venue.roof_y ?? 38) - 2, fz[1] - margin];
  const grid = gridLayer(venue);
  const below = { lo, hi: [hi[0], Math.min(hi[1], grid.lo - GRID_MARGIN_M), hi[2]], gridFace: 1 };    // the grid is its ceiling
  const above = { lo: [lo[0], Math.max(lo[1], grid.hi + GRID_MARGIN_M), lo[2]], hi, gridFace: -1 };   // the grid is its floor
  // a shot whose own camera stands outside that box (the side-stand platform, a camera rising out of the crowd) has
  // the box widened to its camera on that side: the director judged that place; the walk never goes past it
  const band = (mount) => {
    const B = mount && mount[1] > (grid.lo + grid.hi) / 2 ? above : below;
    if (!mount) return B;
    let out = null;
    for (let i = 0; i < 3; i++) {
      if (mount[i] < B.lo[i]) { out = out || { lo: B.lo.slice(), hi: B.hi.slice(), gridFace: B.gridFace }; out.lo[i] = mount[i]; }
      else if (mount[i] > B.hi[i]) { out = out || { lo: B.lo.slice(), hi: B.hi.slice(), gridFace: B.gridFace }; out.hi[i] = mount[i]; }
    }
    return out || B;
  };
  // the structure, grown by half a metre (the lens is never inside a truss)
  const grown = (boxes || []).map((b) => ({ c: b.c, s: [b.s[0] + 1, b.s[1] + 1, b.s[2] + 1], what: b.what }));
  return {
    lo, hi, grid, band, boxes: grown, raw: (boxes || []).map((b) => ({ c: b.c, s: b.s, what: b.what })),
    inside: (p, mount = p) => { const B = band(mount); return p[0] >= B.lo[0] && p[0] <= B.hi[0] && p[1] >= B.lo[1] && p[1] <= B.hi[1] && p[2] >= B.lo[2] && p[2] <= B.hi[2]; },
    // a shot mounted on the structure (the truss's own view) starts inside its grown box: that box is its mount, not a wall
    blocked: (p, q, start = null) => {
      for (const b of grown) if (segmentHitsBox(p, q, b) && !(start && insideBox(start, b))) return b.what || "structure";
      return null;
    },
  };
}

// --------------------------------------------------------------------------------------------- the distance layer --
const HELD_WORDS = { clearance: "1.5 m+ from the rig", venue: "the venue's edge", grid: "the rigging grid", subject: "3 m from the subject",
                     comfort: "the shot's limit", room: "the room's edge" };
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
    this.heldWhy = null;                    // a press planned short of its stop by the room: what held it (the HUD says so)
    this.landAt = null;                     // the beat the move lands on
    this.pending = null;                    // a clean cut waiting for its beat {at, stop | null (auto)}
    this.fad = { caught: false, side: 0, value: null };   // the fader's soft takeover
    this.geo = null;                        // the last frame's shot pose and rig, for planning a press against the room
    this.frames = new Map();                // shot id -> shotFrame
    this.lamPrev = 0; this.lamShot = null;  // the scale applied last frame (ln size) and on which shot
    this.vel = 0;                           // its rate (ln size a second)
    this.onTrack = true;                    // the camera rides the command exactly (nothing has limited it)
    this.cmdPrev = 0; this.cmdShot = null;  // the command last frame (its speed, for rejoining it)
    this.hist = null;                       // the last frame's {shot, u, pos, t}: the shot's own speed along its move
    this.uRate = 0; this.bps = 2.5;         // du per beat of the shot on screen, beats a second
    this.escapes = 0;                       // cuts the rig forced (it reached the lens faster than any move could keep it clear)
    this.rigCut = null;                     // such a cut planned on the next beat line {at}
    this.last = { t: null, lam: 0, k: 1, clamp: null, fixed: null, shot: null, mount: [0, 0, 0] };
    this.cuts = [];                         // [{pos, at, stop, why}] for receipts (bounded)
    this.moves = [];                        // [{pos, landAt, stop, kind}] (bounded)
    this.changed = true;
    this._tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  }
  frameOf(shot) {
    let f = this.frames.get(shot.id);
    if (!f) { f = shotFrame(shot); this.frames.set(shot.id, f); }
    return f;
  }
  _log(list, e) { if (list.length < 256) list.push(e); }
  // ln of the size change the setting asks of this shot now
  _lamFor(f, v, w) { return f.fixed ? 0 : w * (Math.log(widthOf(v)) - Math.log(f.wRef)); }
  // the fader lets go: it must pass through the live value again, judged from scratch (no stale side of it)
  _letGo() { this.fad.caught = false; this.fad.side = 0; this.fad.value = null; }

  // A stop pressed ("close" | "medium" | "far"). ctx: {t (seconds), pos (beat position), spb (seconds a beat), shot (the
  // shot on screen, prepared), cut (Shift: a clean cut), lastCutPos, nextCutPos}. The active stop again hands back.
  press(stop, ctx) {
    if (!(stop in STOPS)) return null;
    this._letGo();
    if (this.mode === "manual" && this.stop === stop && !this.pending) return this.auto(ctx);
    const vT = STOPS[stop];
    if (ctx.cut) {
      const at = cutBeat(ctx.pos, ctx.lastCutPos, ctx.nextCutPos);
      this.pending = { at, stop, tFallback: ctx.t + (at - ctx.pos) * ctx.spb + 0.25 };
      this._settle(ctx, at);
      this.mode = "manual"; this.stop = stop; this.source = "cut"; this.heldWhy = null; this.landAt = at; this.changed = true;
      this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop, kind: "cut" });
      return { kind: "cut", at };
    }
    this.pending = null;
    const f = ctx.shot ? this.frameOf(ctx.shot) : { fixed: false, wRef: widthOf(STOPS.medium) };
    const lamNow = this._lamFor(f, this.v.x, this.w.x);
    const lamSeen = ctx.shot && this.lamShot === ctx.shot.id ? this.lamPrev : lamNow;
    // the move is planned to what the room allows this shot now (the venue's edge, the grid, the rig, the shot's range),
    // so it decelerates into a limit instead of meeting it; the stop asked for stays the stop (a director cut judges it
    // again in the new shot) and the HUD says what held it
    const R = f.fixed ? { lam: 0, why: null } : this._reach(f, ctx.shot, this._lamFor(f, vT, 1));
    const vEff = f.fixed ? vT : clampV(vOfWidth(f.wRef * Math.exp(R.lam)));
    const dl = f.fixed ? 0 : Math.max(Math.abs(R.lam - lamNow), Math.abs(R.lam - lamSeen));
    const at = landingBeat(ctx.pos, ctx.spb, dl);
    const T = (at - ctx.pos) * ctx.spb;
    if (this.w.x <= 1e-9 && !this.w.seg) this.v.set(vEff);   // from auto: the setting is the stop, the weight carries the move
    else this.v.to(vEff, ctx.t, T);
    if (this.w.x < 1 - 1e-9 || this.w.seg) this.w.to(1, ctx.t, T);
    this.heldWhy = Math.abs(vEff - vT) > 1e-6 ? R.why || "room" : null;
    this.mode = "manual"; this.stop = stop; this.source = "key"; this.landAt = at; this.changed = true;
    this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop, kind: "move", ...(vEff !== vT ? { held: +vEff.toFixed(3), why: this.heldWhy } : {}) });
    return { kind: "move", at, seconds: T, v: vEff };
  }
  // a move in flight when a clean cut is queued eases to rest (within SETTLE_S, or by the cut), then nothing moves
  _settle(ctx, at) {
    const T = Math.max(0, Math.min(SETTLE_S, (at - ctx.pos) * ctx.spb));
    this.v.settle(ctx.t, T); this.w.settle(ctx.t, T);
  }
  // The scale (ln size) the room lets this shot reach toward lamT, on the last frame's pose: the shot's comfort range,
  // then a knee inside the soft stop of the walk from the shot's own place (the rig, the walls, the grid, the structure).
  _reach(f, shot, lamT) {
    const G = this.geo;
    if (!G || G.shot !== shot.id) return { lam: lamT, why: null };
    const W = this._geom(G.pos, G.look, G.poses, G.rings);
    if (!W) return { lam: lamT, why: null };
    const { lo, hi } = this._range(f, W.d0);
    const want = Math.max(lo, Math.min(hi, lamT)), dir = Math.sign(want);
    const why0 = want !== lamT ? (lamT < 0 && W.d0 * Math.exp(lo) <= SUBJECT_MIN_M + 1e-6 ? "subject" : "comfort") : null;
    if (!dir) return { lam: want, why: why0 };
    const S = this._walk(W, 0, want + dir * 2 * KNEE);
    // planned a knee inside the soft stop, where the smooth saturation leaves the move exactly as planned
    if (Math.abs(S.soft) >= Math.abs(want) + KNEE - 1e-9) return { lam: want, why: why0 };
    const lim = dir * Math.max(0, Math.abs(S.soft) - KNEE);
    return Math.abs(lim) < Math.abs(want) ? { lam: lim, why: S.why || why0 } : { lam: want, why: why0 };
  }
  // The receipts' door: a stop (or "auto") at once, no move, no beat (a still at each size)
  setNow(stop) {
    this.pending = null; this._letGo(); this.landAt = null; this.heldWhy = null; this.changed = true;
    this.lamShot = null;      // the next frame starts there (no follow from the last one)
    if (stop === "auto") { this.w.set(0); this.mode = "auto"; this.stop = null; this.source = null; return; }
    this.v.set(STOPS[stop]); this.w.set(1); this.mode = "manual"; this.stop = stop; this.source = "key";
  }
  // Back to the director: a blend over two beats (or the comfort time, if longer), landing on a beat line. cut: at once
  // on the next beat line instead.
  auto(ctx) {
    this._letGo();
    if (this.mode === "auto" && !this.pending && !this.w.seg && this.w.x <= 1e-9) return null;
    const wasManual = this.mode === "manual";
    this.mode = "auto"; this.stop = null; this.source = null; this.heldWhy = null; this.changed = true;
    if (ctx.cut) {
      const at = cutBeat(ctx.pos, ctx.lastCutPos, ctx.nextCutPos);
      this.pending = { at, stop: null, tFallback: ctx.t + (at - ctx.pos) * ctx.spb + 0.25 };
      this._settle(ctx, at);
      this.landAt = at;
      this._log(this.moves, { pos: +ctx.pos.toFixed(4), landAt: at, stop: "auto", kind: "cut" });
      return { kind: "cut", at };
    }
    this.pending = null;
    const f = ctx.shot ? this.frameOf(ctx.shot) : { fixed: true };
    const lamSeen = ctx.shot && this.lamShot === ctx.shot.id ? Math.abs(this.lamPrev) : 0;
    const at = landingBeat(ctx.pos, ctx.spb, f.fixed ? 0 : Math.max(Math.abs(this._lamFor(f, this.v.x, this.w.x)), lamSeen), HANDBACK_BEATS);
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
    // the live value is where the camera is going: a key's stop (or the move toward it), or in auto (and while handing
    // back) the shot's own size -- so the fader must pass through what the last press asked for
    const live = this.mode === "manual" ? (this.v.seg ? this.v.seg.x1 : this.v.x) : f && !f.fixed ? f.vAuto : this.v.x;
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
    this.mode = "manual"; this.stop = null; this.source = "fader"; this.heldWhy = null; this.landAt = null; this.changed = true;
    this.v.track(x, 12, LOG_RATE_MAX / LN_RANGE);
    return { caught: true, live };
  }

  // the shot's comfort range of ln k at the subject distance d0 (k in [kMin, kMax], never nearer than 3 m)
  _range(f, d0) { return { lo: Math.log(Math.min(1, Math.max(f.kMin, SUBJECT_MIN_M / d0))), hi: Math.log(Math.max(1, f.kMax)) }; }
  // the intent eased into that range (static limits: a smooth saturation)
  _cmd(lamWant, lo, hi) { return lamWant >= 0 ? Math.max(0, softMin(lamWant, hi)) : -Math.max(0, softMin(-lamWant, -lo)); }
  // the line from the subject through the shot's own camera, and the room the camera may use on it
  _geom(pos, look, poses, rings) {
    const dx = pos[0] - look[0], dy = pos[1] - look[1], dz = pos[2] - look[2], d0 = Math.hypot(dx, dy, dz);
    if (!(d0 > 1e-3)) return null;
    return { look: look.slice(), u: [dx / d0, dy / d0, dz / d0], d0, poses, rings, mount: pos.slice(), band: this.room ? this.room.band(pos) : null };
  }
  // The goal on this line: the command, held at the soft stop of the walk from the shot's own place (a smooth saturation,
  // so a move eases into a limit), never past the hard one. from: where the camera is (the walk covers it).
  _bound(W, lamCmd, from = 0) {
    const dir = Math.sign(lamCmd);
    if (!dir) return { goal: 0, why: null, S: null };
    let end = lamCmd + dir * 2 * KNEE;
    if (Math.sign(from) === dir && Math.abs(from) > Math.abs(end)) end = from;
    const S = this._walk(W, 0, end);
    const gS = Math.abs(S.soft), gH = Math.abs(S.hard), gC = Math.abs(lamCmd);
    const g = Math.min(Math.max(0, softMin(gC, gS)), gH);
    return { goal: dir * g, why: gC - g > 0.02 ? S.why : null, S };
  }
  // where a cut puts the camera: at the command if that point keeps the soft clearance now and the rig stays clear of it
  // over the next half second, else at the soft stop of the walk from the shot's own place (now and ahead, the most
  // restrictive)
  _place(W, lamCmd, lamWant, futs) {
    if (lamCmd !== 0 && this._field(W, lamCmd).c >= SOFT_M && futs.every((F) => this._field(F.W, lamCmd).c >= CLEARANCE_M + 0.5)) return { goal: lamCmd, why: null };
    const B = this._bound(W, lamCmd);
    let goal = B.goal, why = B.why;
    for (const F of futs) {
      const bF = this._bound(F.W, this._cmd(lamWant, F.r.lo, F.r.hi));
      if (Math.sign(bF.goal) !== Math.sign(goal) || Math.abs(bF.goal) < Math.abs(goal)) { goal = Math.sign(bF.goal) === Math.sign(goal) ? bF.goal : 0; why = bF.why || why || "clearance"; }
    }
    return { goal, why };
  }
  // the shot's own line half a second ahead (LOOKAHEAD_S), where the director's own camera is clear of the rig
  // (out.blind: a future the director's own camera reaches the rig in -- his guard's, and the camera holds its size; and
  // past the shot's end, where nothing is known, when his own camera is already within the soft clearance of the rig)
  _futures(f, shot, pose, ctx, W) {
    const out = [];
    out.blind = false;
    if (!(this.uRate > 0) || !Number.isFinite(pose.u)) return out;
    for (const h of LOOKAHEAD_S) {
      const db = h * this.bps, uF = pose.u + this.uRate * db;
      if (uF > 1) { if (this._field(W, 0).c < SOFT_M) out.blind = true; break; }
      const tmp = shotPose(shot, uF, ctx.pos + db, { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 });
      const WF = this._geom(tmp.pos, tmp.look, ctx.poses, ctx.rings || this.homeRings);
      if (!WF || this._field(WF, 0).c < CLEARANCE_M) { out.blind = true; continue; }     // the director's own path: his guard's
      out.push({ h, W: WF, r: this._range(f, WF.d0) });
    }
    return out;
  }
  // whether the camera may move from a to b along this frame's line without breaking the hard rule (S: a walk from a)
  _clearTo(W, a, b, S) {
    if (b === a) return this._field(W, b).c >= CLEARANCE_M || b === 0;
    if (S && Math.sign(b - a) === Math.sign(S.end - a) && Math.abs(b - a) <= Math.abs(S.end - a) + 1e-12) return Math.abs(b - a) <= Math.abs(S.hard - a) + 1e-9;
    const V = this._walk(W, a, b);
    return Math.abs(V.hard - a) >= Math.abs(b - a) - 1e-9;
  }
  // The nearest scale on a line, from lam a in direction dir (within the shot's range), that has the soft clearance
  // (2.5 m: the hysteresis that keeps an escape from being undone the next frame), or null.
  _seek(W, a, dir, limit) {
    let lam = a, c = this._field(W, a).c;
    for (let n = 0; n < 200; n++) {
      if ((dir > 0 && lam >= limit) || (dir < 0 && lam <= limit)) return null;
      const d = W.d0 * Math.exp(lam), stepM = Math.min(2.5, Math.max(0.15, Math.abs(c - SOFT_M)));
      const ln = dir > 0 ? Math.min(limit, Math.log((d + stepM) / W.d0)) : Math.max(limit, Math.log(Math.max(1e-6, d - stepM) / W.d0));
      const fq = this._field(W, ln);
      if (fq.c >= SOFT_M) return this._bisectSoft(W, ln, lam, SOFT_M);
      lam = ln; c = fq.c;
    }
    return null;
  }
  // The span the camera may use this frame, from where it is (from): toward the command up to the soft stop of the walk
  // on this line and on the shot's own path over the next half second (the most restrictive wins, so the camera is held
  // before a limit arrives, not after); and where a rung or a wall is about to reach the camera's own spot, the nearer
  // place with the soft clearance on that future line that the camera can reach on this one without passing anything,
  // moved to ahead of it. If neither side can be reached, doom says when the spot is lost (the caller cuts, on a beat
  // line when one comes first). Returns {goal, why, S (the walk on this line), doom (seconds) | null}.
  _span(W, from, lamCmd, lamWant, futs) {
    const s = Math.sign(lamCmd - from);
    let L = -Infinity, U = Infinity, whyL = null, whyU = null, esc = 0, S = null, doom = null;
    if (s) {
      S = this._walk(W, from, lamCmd + s * 2 * KNEE);
      // a bound only where a limit stopped the walk (its end is not a wall)
      if (S.soft !== S.end) { if (s > 0) { U = S.soft; whyU = S.why; } else { L = S.soft; whyL = S.why; } }
    }
    const reach = (x) => x !== null && Math.abs(this._walk(W, from, x).hard - x) <= 1e-9;
    for (const F of futs) {
      const fF = this._field(F.W, from);
      if (from !== 0 && fF.c < CLEARANCE_M + 0.5) {
        // the camera's own spot is about to be crowded: the nearer reachable place on that line with the soft clearance
        // (never past the shot's own place: that one the director judged, so it is the way out of last resort)
        let up = from < 0 ? this._seek(F.W, from, 1, 0) ?? 0 : this._seek(F.W, from, 1, Math.max(F.r.hi, from + 1e-9));
        let dn = from > 0 ? this._seek(F.W, from, -1, 0) ?? 0 : this._seek(F.W, from, -1, Math.min(F.r.lo, from - 1e-9));
        if (!reach(up)) up = null;
        if (!reach(dn)) dn = null;
        const x = up === null ? dn : dn === null ? up : (Math.exp(up) - Math.exp(from) <= Math.exp(from) - Math.exp(dn) ? up : dn);
        if (x === null) { if (fF.c < CLEARANCE_M && doom === null) doom = F.h; continue; }
        if (x > from) { if (x > L) { L = x; whyL = fF.why; esc = 1; } } else if (x < U) { U = x; whyU = fF.why; esc = -1; }
      } else if (s) {
        const SF = this._walk(F.W, from, this._cmd(lamWant, F.r.lo, F.r.hi) + s * 2 * KNEE);
        if (SF.soft === SF.end) continue;
        if (s > 0 && SF.soft < U) { U = SF.soft; whyU = SF.why || "clearance"; }
        if (s < 0 && SF.soft > L) { L = SF.soft; whyL = SF.why || "clearance"; }
      }
    }
    // the director's own camera reaches the rig ahead (his guard will cut): the camera goes no further from his place
    if (futs.blind && s && (from === 0 || Math.sign(lamCmd) === Math.sign(from))) { if (s > 0) U = Math.min(U, from); else L = Math.max(L, from); }
    if (L > U) { if (esc > 0) U = L; else L = U; }     // the escape (the hard rule ahead) outranks a soft stop
    // the command inside [L, U] (the follower decelerates into a bound: no knee here, which could push the goal past
    // an escape's own bound and set it hunting)
    const goal = Math.max(L, Math.min(U, lamCmd));
    const why = lamCmd > goal + 0.02 ? whyU : lamCmd < goal - 0.02 ? whyL : null;
    return { goal, why, S, doom, L, U };
  }
  // the follower: toward the goal at most LOG_RATE_MAX, accelerating and braking at most LOG_ACCEL_MAX a second a second
  // (the discrete braking curve: the speed from which steps of A dt still stop on a goal that stands still), landing on
  // it exactly, at a speed a frame's braking can take away
  // L, U: the room's bounds on either side (the follower also brakes for them, so a command that runs into one at speed
  // is slowed before it, not after)
  _follow(lam, vel, goal, dt, L = -Infinity, U = Infinity) {
    const e = goal - lam, ae = Math.abs(e), dv = LOG_ACCEL_MAX * dt;
    let v = Math.sign(e) * Math.min(LOG_RATE_MAX, this._brake(ae, dt), ae / dt);
    if (v > 0) v = Math.min(v, this._brake(U - lam, dt)); else if (v < 0) v = Math.max(v, -this._brake(lam - L, dt));
    v = Math.max(-LOG_RATE_MAX, Math.min(LOG_RATE_MAX, Math.max(vel - dv, Math.min(vel + dv, v))));
    return [lam + v * dt, v];
  }

  // the fastest speed (ln a second) from which steps of LOG_ACCEL_MAX dt still stop within dist (discrete time)
  _brake(dist, dt) { if (!(dist > 0)) return 0; if (dist === Infinity) return Infinity; const dv = LOG_ACCEL_MAX * dt; return dv * (Math.sqrt(0.25 + (2 * dist) / (dv * dt)) - 0.5); }
  // Per frame, after the director: moves the pose's camera position (in place) and returns the status. ctx: {t, pos,
  // cut (the director cut this frame), poses (the live rung poses), rings (live annuli or null)}. pose.u (the director's
  // place along the shot) lets the room be read ahead on the shot's own path.
  apply(pose, shot, ctx) {
    const t = ctx.t, dt = this.last.t === null ? 0 : Math.max(0, Math.min(0.1, t - this.last.t));
    this.last.t = t;
    const M = this.last.mount; M[0] = pose.pos[0]; M[1] = pose.pos[1]; M[2] = pose.pos[2];   // the director's own camera
    let cutNow = false;
    const P = this.pending;
    if (P && (ctx.pos >= P.at - 1e-6 || t >= P.tFallback)) {
      if (P.stop) { this.v.set(STOPS[P.stop]); this.w.set(1); } else this.w.set(0);
      this.pending = null; cutNow = true; this.changed = true;
      this._log(this.cuts, { pos: +ctx.pos.toFixed(4), at: P.at, stop: P.stop || "auto", why: "shift" });
    }
    this.v.tick(t, dt); this.w.tick(t, dt);
    this.v.x = clampV(this.v.x); this.w.x = clamp01(this.w.x);
    // a director cut: a stop held by hand starts the new shot at the stop itself (a press the last shot's room planned
    // short is judged again in the new one)
    if (ctx.cut && !cutNow && this.mode === "manual" && this.stop && this.source !== "fader" && !this.pending && this.v.x !== STOPS[this.stop]) {
      this.v.set(STOPS[this.stop]); this.heldWhy = null; this.changed = true;
    }
    if (this.landAt !== null && !this.v.seg && !this.w.seg && !this.pending) this.landAt = null;
    pose.distCut = cutNow;
    // a cut, a new shot, or no time passed since the last frame (a re-evaluation): the camera starts where it should be
    const reset = !!ctx.cut || cutNow || !shot || this.lamShot !== (shot && shot.id) || !(dt > 0);
    // the shot's own pose and the rig this frame (a press plans its move against them), and its speed along its move
    if (shot) {
      this.geo = { shot: shot.id, pos: pose.pos.slice(), look: pose.look.slice(), poses: ctx.poses, rings: ctx.rings || this.homeRings };
      const H = this.hist;
      if (H && H.shot === shot.id && !reset && Number.isFinite(pose.u) && ctx.pos - H.pos > 1e-6 && pose.u >= H.u) {
        this.uRate = (pose.u - H.u) / (ctx.pos - H.pos); this.bps = (ctx.pos - H.pos) / Math.max(1e-6, t - H.t);
      } else if (reset) this.uRate = 0;
      this.hist = { shot: shot.id, u: pose.u, pos: ctx.pos, t };
    }
    // auto, and resting where the director put it: his pose exactly
    if (this.w.x <= 0 && !this.w.seg && (reset || this.lamPrev === 0)) { this._rest(shot); return this.last; }
    if (!shot) return this.last;
    const f = this.frameOf(shot);
    if (f.fixed) { this._rest(shot); this.last.fixed = f.why; return this.last; }
    const W = this._geom(pose.pos, pose.look, ctx.poses, ctx.rings || this.homeRings);
    if (!W) { this._rest(shot); return this.last; }
    // the intent, eased into the shot's comfort range and the subject floor
    const { lo, hi } = this._range(f, W.d0);
    const lamWant = this._lamFor(f, this.v.x, this.w.x);
    const lamCmd = this._cmd(lamWant, lo, hi);
    let clamp = Math.abs(lamWant - lamCmd) > 0.02 ? (lamWant < 0 && W.d0 * Math.exp(lo) <= SUBJECT_MIN_M + 1e-6 ? "subject" : "comfort") : null;
    // where the camera may be: a cut (or a new shot) starts it at the command if that point keeps the soft clearance,
    // else at the soft stop of the walk from the shot's own place; every other frame it moves on from where it was
    let lam, vel, goal, why = null;
    const futs = this._futures(f, shot, pose, ctx, W);
    const cutTo = (w0) => {
      ({ goal, why } = this._place(W, lamCmd, lamWant, futs)); lam = goal; vel = 0; this.rigCut = null;
      pose.distCut = true; this.escapes++; this.changed = true;
      this._log(this.cuts, { pos: +ctx.pos.toFixed(4), at: +ctx.pos.toFixed(4), stop: this.stop || (this.mode === "auto" ? "auto" : "fader"), why: w0 || "clearance" });
    };
    if (reset) {
      ({ goal, why } = this._place(W, lamCmd, lamWant, futs)); lam = goal; vel = 0; this.rigCut = null;
    } else if (this.lamPrev !== 0 && this._field(W, this.lamPrev).c < CLEARANCE_M) {
      cutTo(this._field(W, this.lamPrev).why);    // the rig reached the lens faster than anything could move it: a cut, never a slide
    } else if (this.rigCut && ctx.pos >= this.rigCut.at - 1e-6) {
      cutTo("rig, on the beat");                   // the spot was going to be lost and no move could keep it: cut on the beat line
    } else {
      const span = this._span(W, this.lamPrev, lamCmd, lamWant, futs);
      goal = span.goal; why = span.why;
      // a spot that will be lost with no way out: a cut on the next beat line, if one comes before the rig does
      if (span.doom !== null && !this.rigCut) {
        const nb = Math.ceil(ctx.pos + 1e-6);
        if ((nb - ctx.pos) / Math.max(1e-6, this.bps) < span.doom) this.rigCut = { at: nb };
      } else if (span.doom === null) this.rigCut = null;
      // the fader's follower is aimed at what the room allows, so pulling the fader back moves the camera at once
      const fl = this.v.follow;
      if (fl && this.w.x >= 1 - 1e-9 && !this.w.seg && goal !== lamCmd) {
        const vS = vOfWidth(f.wRef * Math.exp(goal));
        if (lamCmd > goal && fl.target > vS) fl.target = Math.max(Math.min(this.v.x, fl.target), vS);
        if (lamCmd < goal && fl.target < vS) fl.target = Math.min(Math.max(this.v.x, fl.target), vS);
      }
      // follow the goal: the command itself, exactly, while nothing limits it and it is not running into a bound faster
      // than the camera could stop for it
      const need = (lamCmd - this.lamPrev) / dt;
      const room = need > 0 ? this._brake(span.U - this.lamPrev, dt) : need < 0 ? this._brake(this.lamPrev - span.L, dt) : Infinity;
      if (this.onTrack && goal === lamCmd && Math.abs(need) <= room + 1e-12) { lam = goal; vel = need; }
      else [lam, vel] = this._follow(this.lamPrev, this.vel, goal, dt, span.L, span.U);
      // the hard rule on the frame as drawn, along the line from where the camera was: else a cut, never a slide
      if (!this._clearTo(W, this.lamPrev, lam, span.S)) cutTo(span.why || why);
    }
    if (Math.abs(lamCmd - goal) > 0.02) clamp = why || clamp;
    // back on the command once the camera is on it and moving as it moves (no step in its speed)
    const cmdVel = this.cmdShot === shot.id && dt > 0 ? (lamCmd - this.cmdPrev) / dt : 0;
    this.onTrack = goal === lamCmd && Math.abs(lam - lamCmd) < 1e-9 && (reset || pose.distCut || this.onTrack || Math.abs(vel - cmdVel) <= LOG_ACCEL_MAX * dt * (1 + 1e-9));
    if (this.onTrack) lam = lamCmd;
    this.cmdPrev = lamCmd; this.cmdShot = shot.id;
    if (Math.abs(lam) < 1e-9) lam = 0;          // the shot's own place, exactly
    // a stop held short of its own size by the room (planned so at the press, or held now): the HUD says what holds it
    if (!clamp && this.mode === "manual" && this.stop && !this.pending && !this.v.seg && !this.w.seg
        && Math.abs(lam - this._lamFor(f, STOPS[this.stop], this.w.x)) > 0.02) clamp = this.heldWhy || why || "room";
    if (lam !== 0) {
      const d = W.d0 * Math.exp(lam), p = pose.pos, u = W.u, L = pose.look;
      p[0] = L[0] + u[0] * d; p[1] = L[1] + u[1] * d; p[2] = L[2] + u[2] * d;
    }
    this.lamPrev = lam; this.vel = vel; this.lamShot = shot.id;
    this.last.shot = shot.id; this.last.fixed = null; this.last.lam = lam; this.last.k = Math.exp(lam); this.last.clamp = clamp;
    return this.last;
  }
  _rest(shot) {
    this.last.lam = 0; this.last.k = 1; this.last.clamp = null; this.last.shot = shot ? shot.id : null; this.last.fixed = null;
    this.lamPrev = 0; this.vel = 0; this.onTrack = true; this.lamShot = shot ? shot.id : null;
  }
  // The room's clearance for the camera placed at scale e^lam on the line, as one number: the rig's (the strand, the
  // rings), the walls' and the grid's plus 1.5 m (inside the shot's band), the structure's plus 1.0 m (a box the shot is
  // mounted in does not count), so the hard rule is c >= 1.5 m everywhere and the soft one c >= 2.5 m. Every term changes
  // at most 1 m a metre the camera moves (each is a distance), which is what lets the walk sphere-trace it.
  _field(W, lam, out = [0, 0, 0]) {
    const d = W.d0 * Math.exp(lam);
    out[0] = W.look[0] + W.u[0] * d; out[1] = W.look[1] + W.u[1] * d; out[2] = W.look[2] + W.u[2] * d;
    let c = Infinity, why = null;
    if (W.poses && this.z) { const r = clearanceToStrand(out, W.poses, this.z); if (r < c) { c = r; why = "clearance"; } }
    if (W.rings && W.rings.length) { const r = clearanceToRings(out, W.rings); if (r < c) { c = r; why = "clearance"; } }
    const room = this.room;
    if (room) {
      const B = W.band || room.band(W.mount);
      const yHi = B.hi[1] - out[1], yLo = out[1] - B.lo[1];
      const wall = Math.min(out[0] - B.lo[0], B.hi[0] - out[0], out[2] - B.lo[2], B.hi[2] - out[2]);
      const m = Math.min(wall, yHi, yLo) + CLEARANCE_M;
      if (m < c) {
        c = m;
        // the grid's face of the band (its ceiling below the grid, its floor above it) when that is the nearest
        const gridNear = B.gridFace > 0 ? yHi <= Math.min(wall, yLo) && B.hi[1] < room.hi[1] : yLo <= Math.min(wall, yHi) && B.lo[1] > room.lo[1];
        why = gridNear ? "grid" : "venue";
      }
      for (const b of room.raw) {
        if (insideBox(W.mount, b, 0.5)) continue;
        const s = boxDistance(out, b) + 1.0;
        if (s < c) { c = s; why = b.what || "structure"; }
      }
    }
    return { c, why, q: out };
  }
  // From lam a toward lam b, sphere-traced (each step no longer than the clearance left over the 1.5 m rule, at least
  // 0.15 m, at most 2.5 m, so no limit is stepped over), then bisected to the boundary: the furthest scale that keeps
  // the soft rule (a sample under 2.5 m that is getting nearer stops it), the furthest that keeps the hard rule, and what
  // stopped it. A start that breaks the hard rule (the shot's own camera inside a limit) looks for the first clear sample.
  _walk(W, a, b) {
    const dir = Math.sign(b - a);
    const f0 = this._field(W, a), prev = f0.q.slice(), seg = [0, 0, 0];
    let soft = a, hard = a, clear = f0.c >= CLEARANCE_M, why = null, softOk = true, cPrev = f0.c, cSoft = f0.c;
    if (!dir) return { soft, hard, why, end: b };
    let lam = a;
    for (let n = 0; n < 800; n++) {
      const d = W.d0 * Math.exp(lam);
      const stepM = Math.min(2.5, Math.max(0.15, cPrev - CLEARANCE_M));
      const ln = dir > 0 ? Math.min(b, Math.log((d + stepM) / W.d0)) : Math.max(b, Math.log(Math.max(1e-6, d - stepM) / W.d0));
      const fq = this._field(W, ln);
      const through = this.room ? this.room.blocked(prev, fq.q, W.mount) : null;
      if (!clear) { if (fq.c >= CLEARANCE_M && !through) { clear = true; soft = hard = ln; cSoft = fq.c; } }
      else if (fq.c < CLEARANCE_M || through) {
        why = why || (through ? through : fq.why);
        // the hard boundary between the last good sample and this one (the segment from the last good point clear too)
        let g = lam, x = ln;
        for (let i = 0; i < 10; i++) {
          const mid = (g + x) / 2, fm = this._field(W, mid, seg);
          if (fm.c >= CLEARANCE_M && !(this.room && this.room.blocked(prev, seg, W.mount))) g = mid; else x = mid;
        }
        hard = g;
        if (softOk) soft = this._bisectSoft(W, soft, g, Math.min(SOFT_M, cSoft));
        break;
      } else {
        hard = ln;
        if (softOk && (fq.c >= SOFT_M || fq.c >= cPrev - 1e-9)) { soft = ln; cSoft = fq.c; }
        else if (softOk) { softOk = false; why = why || fq.why; soft = this._bisectSoft(W, soft, ln, Math.min(SOFT_M, cSoft)); }
      }
      cPrev = fq.c; prev[0] = fq.q[0]; prev[1] = fq.q[1]; prev[2] = fq.q[2]; lam = ln;
      if (ln === b) break;
    }
    if (!clear) { soft = hard = a; }
    return { soft, hard, why, end: b };
  }
  // the soft stop between a sample that keeps it (g) and one that does not (x): where the clearance falls under thr
  _bisectSoft(W, g, x, thr) {
    for (let i = 0; i < 10; i++) { const mid = (g + x) / 2; if (this._field(W, mid).c >= thr - 1e-9) g = mid; else x = mid; }
    return g;
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
    const held = s.clamp ? ` · held at ${HELD_WORDS[s.clamp] || `the ${s.clamp}`}` : "";
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
