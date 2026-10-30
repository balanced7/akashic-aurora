// Virtual Stage v0, the camera crew: arsenal/web/stage/camera.js (pure ES module). Tests: tests/stage_camera.test.mjs.
//
// Daniel: "the arial shots they get we can use as suggestions for camera flypaths". A SHOT is data, taken from the
// official Qlimax 2014 videos' camera language (the rig lane's camera-paths.json: the front-of-house lock-off, the
// crowd's view, the worm's-eye shot up the strand, the high tribune three-quarter view) plus shots nobody in the room
// could get (flying down the strand, the crane rise, the orbit round the rings).
//
// A shot: kind static | path | orbit; position and look-at as separate centripetal Catmull-Rom curves (alpha 0.5: no
// cusps or self-loops on uneven spacing), traversed at even speed (an arc-length table) and eased with the minimum-jerk
// curve 10u^3 - 15u^4 + 6u^5 (Gebhardt et al. 2018 as cited by the rig lane); hfov (or [from, to]); roll; handheld noise
// (0.3-0.5 Hz, 0.6 degrees yaw and pitch, 0.3 roll); its exposure (EV: beams seen side-on are 10-60 times dimmer than
// beams seen head-on, so each shot carries its own, never an auto-exposure that would pump on strobes).
//
// Progress is driven by the BEAT POSITION, not the clock: u = ease((pos - pos0) / (posEnd - pos0)), so a flythrough
// arrives on the ONE whatever the tempo does. The director plays a sequence of {shot, bars} and cuts only on bar lines;
// no shot is shorter than 2 beats (the rig lane's cut grammar: never faster than every 2 beats).
//
// v1 (2026-10-25): a phrase drives the camera with a PLAN, entries {shot, p0, p1} at absolute beat positions (phrases.js
// cameraPlan: one entry per step, a step's shot may split, and a step that opens with a flash is cut to one beat early so
// the cut never lands on the flash frame). An entry rebuilt with the same shot and p0 is the same entry: no second cut.
// When the plan runs out, the sequence plays on.
//
// v2 (2026-10-27, the camera lane of the VJ V2 night; research/reviewed/keylab-liberation-2026-10-22/vj-v2-research-
// 2026-10-27/camera.research.md). Daniel: "more variations of the shots with the hanging dna and the full stage with them
// at different altitudes". The strand now moves through altitude shapes, and a camera that does not know where the strand
// is flies through it (the lane's clearance matrix: the old flythrough hits the rungs in 11 of 13 candidate formations).
//   strand frame   kind "strand": a shot written in strand coordinates (s along the low-passed centre line through the
//                  rung centres, r and theta round it, or an under-ride a fixed distance below the lowest rung near the
//                  lens) re-frames itself when the formation changes: one corkscrew that stays clear at every altitude.
//   validity       the director never DEALS a shot that would come within 1.5 m of a rung: every shot is sampled against
//                  every formation of the set at load (and any new one when it first lands), plus the data's own lists
//                  (valid_for, invalid_for, held). An invalid shot is swapped for its fallback or the set's safe wide; a
//                  runtime guard watches the live clearance and cuts away (on a 2-beat line) below 1.0 m.
//   grammar        "the move shows the motion, the cut reveals the arrival": a formation that lands gets ONE long glide
//                  while the hoists move (cutting fast hides the kinetics: a real-mode shape takes a whole phrase), then a
//                  cut exactly on the landing bar line to that formation's hero view (cameras.formation_views).
//   lens and time  roll curves (roll as [from, to] or keyframes), easings arrive_fast (u^2.2: top speed on the ONE, for
//                  dives), snap (hold, then minimum jerk over the last quarter: a crash zoom on a hit) and arrive_u (the
//                  path point that lands on the bar line while the camera is still moving: crossing a plane ON the ONE),
//                  and the dolly zoom (VERTIGO_TUNNEL: hfov = 2 atan(width / (2 fill d)) holds the rings' size while the
//                  strand stretches past the lens; a linear hfov ramp would be 12 % off mid-move and the ring would breathe).

import { Axis, formationTarget } from "./kinetics.js";

export const CAMERA_API = "arsenal.stage-camera/v2";
export const MIN_SHOT_BEATS = 2;
export const CLEARANCE_M = 1.5;          // the rule: the camera stays 1.5 m from rungs, cubes and rings
export const GUARD_M = 1.0;              // the runtime guard cuts away below this (the rule's margin is the guard's time)
export const DRONE = Object.freeze({ vmax: 15, amax: 5 });   // the design's virtual drone (m/s, m/s^2): the speed lint
export const NOMINAL_BPM = 150;          // the house tempo, for anything that needs seconds out of beats at load
const DEG = Math.PI / 180;
const clamp01 = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u);
const lerp = (a, b, t) => a + (b - a) * t;

export function minJerk(u) { const x = clamp01(u); return x * x * x * (10 + x * (-15 + 6 * x)); }
export function smoothstep(u) { const x = clamp01(u); return x * x * (3 - 2 * x); }
// snap: still until `at`, then the minimum-jerk curve over the rest (a crash zoom that lands on a hit)
export function snapEase(u, at = 0.75) { const x = clamp01(u); return x <= at ? 0 : minJerk((x - at) / (1 - at)); }
export const EASES = Object.freeze({
  minjerk: minJerk,
  linear: clamp01,
  arrive_fast: (u) => Math.pow(clamp01(u), 2.2),   // still accelerating on the ONE: a dive that levels out on the drop
  snap: (u) => snapEase(u, 0.75),
});
function baseEase(shot) {
  if (shot.ease === "snap" && shot.snap_at !== undefined) return (u) => snapEase(u, shot.snap_at);
  return EASES[shot.ease || "minjerk"] || minJerk;
}
// The eased progress of a shot. arrive_u = a: the shot's curve is the base easing over the whole path, but the shot ENDS
// when the path reaches a (time t* with ease(t*) = a), so the bar line finds the camera at a and still moving.
export function easeOf(shot, u) {
  const f = shot._ease || baseEase(shot);
  const t = shot._arriveT !== undefined ? shot._arriveT : arriveTime(f, shot.arrive_u);
  return f(clamp01(u) * t);
}
function arriveTime(f, a) {
  if (!(a > 0 && a < 1)) return 1;
  let lo = 0, hi = 1;
  for (let k = 0; k < 48; k++) { const m = (lo + hi) / 2; if (f(m) < a) lo = m; else hi = m; }
  return (lo + hi) / 2;
}
// keyframes over t in [0, 1]: one value, two (a straight ramp), or more (evenly spaced, a uniform Catmull-Rom through them)
export function keyframes(v, t) {
  if (!Array.isArray(v)) return v;
  const n = v.length;
  if (n === 1) return v[0];
  if (n === 2) return lerp(v[0], v[1], clamp01(t));
  const x = clamp01(t) * (n - 1), i = Math.min(n - 2, Math.floor(x)), f = x - i;
  return crScalar(v[Math.max(0, i - 1)], v[i], v[i + 1], v[Math.min(n - 1, i + 2)], f);
}
function crScalar(p0, p1, p2, p3, t) {
  return 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t * t * t);
}
function crScalarD(p0, p1, p2, p3, t) {
  return 0.5 * ((p2 - p0) + 2 * (2 * p0 - 5 * p1 + 4 * p2 - p3) * t + 3 * (3 * p1 - p0 - 3 * p2 + p3) * t * t);
}
// The dolly zoom's lens: the field of view that keeps an object width_m wide filling `fill` of the frame from distance d.
export function dollyHfov(width_m, fill, d) { return (2 * Math.atan(width_m / (2 * fill * Math.max(1e-6, d)))) / DEG; }

// ------------------------------------------------------------------------------------- centripetal Catmull-Rom --
// One segment between p1 and p2 (p0, p3 the neighbours), at t in [0, 1], Barry-Goldman's pyramid with knots spaced by
// |p_i+1 - p_i|^alpha.
function crSegment(p0, p1, p2, p3, t, alpha, out) {
  const d = (a, b) => Math.pow(Math.max(1e-6, Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2])), alpha);
  const t0 = 0, t1 = t0 + d(p0, p1), t2 = t1 + d(p1, p2), t3 = t2 + d(p2, p3);
  const T = t1 + (t2 - t1) * t;
  for (let k = 0; k < 3; k++) {
    const A1 = ((t1 - T) * p0[k] + (T - t0) * p1[k]) / (t1 - t0);
    const A2 = ((t2 - T) * p1[k] + (T - t1) * p2[k]) / (t2 - t1);
    const A3 = ((t3 - T) * p2[k] + (T - t2) * p3[k]) / (t3 - t2);
    const B1 = ((t2 - T) * A1 + (T - t0) * A2) / (t2 - t0);
    const B2 = ((t3 - T) * A2 + (T - t1) * A3) / (t3 - t1);
    out[k] = ((t2 - T) * B1 + (T - t1) * B2) / (t2 - t1);
  }
  return out;
}
// A whole curve through points (2 or more), parameter s in [0, 1] split evenly over the segments. The end tangents come
// from mirrored phantom points.
export function catmullRom(points, s, out = [0, 0, 0], alpha = 0.5) {
  const n = points.length;
  if (n === 1) { out[0] = points[0][0]; out[1] = points[0][1]; out[2] = points[0][2]; return out; }
  const segs = n - 1;
  const x = Math.max(0, Math.min(1, s)) * segs;
  const i = Math.min(segs - 1, Math.floor(x));
  const t = x - i;
  const P = (j) => {
    if (j < 0) { const a = points[0], b = points[1]; return [2 * a[0] - b[0], 2 * a[1] - b[1], 2 * a[2] - b[2]]; }
    if (j >= n) { const a = points[n - 1], b = points[n - 2]; return [2 * a[0] - b[0], 2 * a[1] - b[1], 2 * a[2] - b[2]]; }
    return points[j];
  };
  return crSegment(P(i - 1), P(i), P(i + 1), P(i + 2), t, alpha, out);
}
// An arc-length table, so u moves along the path at even speed (then the easing shapes it).
export function arcTable(points, samples = 256) {
  const s = new Float64Array(samples + 1), p = [0, 0, 0], q = [0, 0, 0];
  catmullRom(points, 0, q);
  for (let i = 1; i <= samples; i++) {
    catmullRom(points, i / samples, p);
    s[i] = s[i - 1] + Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
    q[0] = p[0]; q[1] = p[1]; q[2] = p[2];
  }
  return { s, length: s[samples], samples };
}
export function atArc(points, table, u, out) {
  const target = Math.max(0, Math.min(1, u)) * table.length;
  const s = table.s;
  let lo = 0, hi = table.samples;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (s[m] < target) lo = m; else hi = m; }
  const f = s[hi] > s[lo] ? (target - s[lo]) / (s[hi] - s[lo]) : 0;
  return catmullRom(points, (lo + f) / table.samples, out);
}

// ----------------------------------------------------------------------------------------------- the strand frame --
// The strand's centre line runs through the rung centres (0, y_i, z_i): a uniform Catmull-Rom in rung index (the rungs
// hang evenly, 3.6 m apart), s = 0 at the first rung (by the stage) and s = 1 at the last (over the crowd); outside
// [0, 1] it runs on straight and level, so a shot can start or end past either end. line = {ys, zs}.
export const HOME_LINE = Object.freeze({ ys: Object.freeze(Array(12).fill(20)), zs: Object.freeze(Array.from({ length: 12 }, (_, i) => 4 + 3.6 * i)) });
export function strandPoint(line, s, out = [0, 0, 0], tan = null) {
  const ys = line.ys, zs = line.zs, n = zs.length;
  const z0 = zs[0], z1 = zs[n - 1];
  const x = s * (n - 1);
  out[0] = 0; out[2] = z0 + s * (z1 - z0);
  let dy = 0;
  if (x <= 0) out[1] = ys[0];
  else if (x >= n - 1) out[1] = ys[n - 1];
  else {
    const i = Math.min(n - 2, Math.floor(x)), t = x - i;
    const p0 = ys[Math.max(0, i - 1)], p1 = ys[i], p2 = ys[i + 1], p3 = ys[Math.min(n - 1, i + 2)];
    out[1] = crScalar(p0, p1, p2, p3, t);
    dy = crScalarD(p0, p1, p2, p3, t) * (n - 1);
  }
  if (tan) { const dz = z1 - z0, l = Math.hypot(dy, dz) || 1; tan[0] = 0; tan[1] = dy / l; tan[2] = dz / l; }
  return out;
}
// The lowest rung centre whose z lies in [zLo, zHi] (the nearest end rung when none does: past the strand's ends).
export function lowestRungY(line, zLo, zHi) {
  const ys = line.ys, zs = line.zs, n = zs.length;
  let m = Infinity;
  for (let i = 0; i < n; i++) if (zs[i] >= zLo && zs[i] <= zHi && ys[i] < m) m = ys[i];
  if (m < Infinity) return m;
  return Math.abs(zLo - zs[0]) < Math.abs(zLo - zs[n - 1]) ? ys[0] : ys[n - 1];
}
// Does a strand shot fly its low half-turns as a pendulum over the top? Latched once per entry (a decision mid-shot would
// jump): when the centre line over the shot's s range dips below `below`, a full turn would skim the crowd.
export function pendulumLatch(shot, line) {
  const pd = shot.strand && shot.strand.pendulum;
  if (!pd) return false;
  const [s0, s1] = shot.strand.s;
  const p = [0, 0, 0];
  for (let k = 0; k <= 16; k++) { strandPoint(line, lerp(s0, s1, k / 16), p); if (p[1] < (pd.below ?? 12)) return true; }
  return false;
}
const _C = [0, 0, 0], _T = [0, 0, 0], _L = [0, 0, 0];
function strandPose(shot, e, frame, out) {
  const st = shot.strand, line = (frame && frame.line) || HOME_LINE;
  const zs = line.zs, span = zs[zs.length - 1] - zs[0];
  const s = lerp(st.s[0], st.s[1], e);
  const dir = Math.sign(st.s[1] - st.s[0]) || 1;
  strandPoint(line, s, _C, _T);
  if (st.under !== undefined) {
    // the under-ride: a fixed distance under the lowest rung near the lens and ahead of it (the follower in the director
    // needs the warning), on the axis
    const travel = dir * Math.sign(span), win = st.window ?? 4, ahead = st.ahead ?? 8;
    const lo = _C[2] - win + Math.min(0, travel) * ahead, hi = _C[2] + win + Math.max(0, travel) * ahead;
    let y = lowestRungY(line, lo, hi) - st.under;
    if (frame && frame.under) y = frame.under(y);
    out.pos[0] = st.x ?? 0; out.pos[1] = Math.max(st.y_min ?? 4, y); out.pos[2] = _C[2];
  } else {
    // N: up, square to the tangent; B = N x T points house right (+x) when the strand runs +z. theta 0 = above, 90 = right.
    const T = _T, d = T[1];                                     // up . T (T has no x)
    let nx = 0, ny = 1 - d * T[1], nz = -d * T[2];
    const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
    const bx = ny * T[2] - nz * T[1], by = nz * T[0] - nx * T[2], bz = nx * T[1] - ny * T[0];
    let th = keyframes(st.theta ?? 0, e);
    if (frame && frame.pendulum && st.pendulum) th = (st.pendulum.deg ?? 110) * Math.sin(th * DEG);
    const r = keyframes(st.r ?? 8, e), c = Math.cos(th * DEG), sn = Math.sin(th * DEG);
    out.pos[0] = _C[0] + r * (c * nx + sn * bx);
    out.pos[1] = Math.max(st.y_min ?? 4, _C[1] + r * (c * ny + sn * by));
    out.pos[2] = _C[2] + r * (c * nz + sn * bz);
  }
  // the look: a fixed point, or the centre line ahead in the direction of travel (by s or by metres)
  if (st.look) { out.look[0] = st.look[0]; out.look[1] = st.look[1]; out.look[2] = st.look[2]; }
  else {
    const ds = st.look_ahead_m !== undefined ? st.look_ahead_m / Math.abs(span || 1) : (st.look_ahead_s ?? 0.2);
    strandPoint(line, s + dir * ds, _L);
    out.look[0] = _L[0]; out.look[1] = _L[1]; out.look[2] = _L[2];
  }
  // an arrival off the strand (rising into the ring's mouth on the ONE): a minimum-jerk blend over the last stretch
  const end = st.end;
  if (end && e > (end.from ?? 0.85)) {
    // lift > 1: the height follows late, so the lens clears the first rung before it rises (the rise is in front of it)
    const k = minJerk((e - (end.from ?? 0.85)) / (1 - (end.from ?? 0.85))), ky = Math.pow(k, end.lift ?? 1);
    for (let a = 0; a < 3; a++) {
      out.pos[a] = lerp(out.pos[a], end.pos[a], a === 1 ? ky : k);
      if (end.look) out.look[a] = lerp(out.look[a], end.look[a], k);
    }
  }
}

// --------------------------------------------------------------------------------------------------- shots --
// Prepare a shot from the scene (arc tables and the easing cached). Shot fields: kind, pos | pos_path, look | look_path,
// hfov (number or [from, to]), dolly_zoom {target, width_m, fill}, roll (number, [from, to] or keyframes), orbit {centre,
// radius, height, from_deg, to_deg, rise}, strand {s, r, theta, look_ahead_s | look_ahead_m | look, y_min, under, window,
// ahead, pendulum {below, deg}, follow "live" | "land", end {pos, look, from, lift}}, handheld, ev, ease ("minjerk" | "linear"
// | "arrive_fast" | "snap"), snap_at, arrive_u, crowd_cull (m), bars (its natural length), held, valid_for, invalid_for,
// fallback.
export function prepareShot(def) {
  const s = { ...def };
  if (s.kind === "path" || s.pos_path) {
    s.kind = "path";
    s._pos = arcTable(s.pos_path);
    if (s.look_path) s._look = arcTable(s.look_path);
  }
  s._ease = baseEase(s);
  s._arriveT = arriveTime(s._ease, s.arrive_u);
  return s;
}
// The pose at u in [0, 1] (shotPose eases), and the handheld noise at beat position pos. frame (strand shots): {line,
// pendulum, under} from the director; without one a strand shot frames the strand at its home height.
export function shotPose(shot, u, pos = 0, out = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 }, frame = null) {
  const e = easeOf(shot, u);
  if (shot.kind === "orbit") {
    const o = shot.orbit, a = (o.from_deg + (o.to_deg - o.from_deg) * e) * DEG;
    out.pos[0] = o.centre[0] + o.radius * Math.sin(a);
    out.pos[1] = o.height + (o.rise ?? 0) * e;
    out.pos[2] = o.centre[2] + o.radius * Math.cos(a);
    const lk = shot.look || o.centre;
    out.look[0] = lk[0]; out.look[1] = lk[1]; out.look[2] = lk[2];
  } else if (shot.kind === "path") {
    atArc(shot.pos_path, shot._pos, e, out.pos);
    if (shot.look_path) atArc(shot.look_path, shot._look, e, out.look);
    else { out.look[0] = shot.look[0]; out.look[1] = shot.look[1]; out.look[2] = shot.look[2]; }
  } else if (shot.kind === "strand") {
    strandPose(shot, e, frame, out);
  } else {
    out.pos[0] = shot.pos[0]; out.pos[1] = shot.pos[1]; out.pos[2] = shot.pos[2];
    out.look[0] = shot.look[0]; out.look[1] = shot.look[1]; out.look[2] = shot.look[2];
  }
  const dz = shot.dolly_zoom;
  if (dz) out.hfov = dollyHfov(dz.width_m, dz.fill, Math.hypot(out.pos[0] - dz.target[0], out.pos[1] - dz.target[1], out.pos[2] - dz.target[2]));
  else { const h = shot.hfov ?? 50; out.hfov = Array.isArray(h) ? h[0] + (h[1] - h[0]) * e : h; }
  out.roll = keyframes(shot.roll ?? 0, e);
  out.ev = shot.ev ?? 0;
  out.crowdCull = shot.crowd_cull ?? null;
  if (shot.handheld) {
    // the handheld wander: three incommensurate slow sines per axis (0.3-0.5 Hz at 150 BPM, as beats: 0.12-0.2 per beat)
    const t = pos;
    const yaw = 0.6 * (0.6 * Math.sin(t * 0.83 + 1.3) + 0.4 * Math.sin(t * 1.31 + 0.2));
    const pitch = 0.6 * (0.6 * Math.sin(t * 0.71 + 2.1) + 0.4 * Math.sin(t * 1.17 + 4.0));
    const dx = out.look[0] - out.pos[0], dy = out.look[1] - out.pos[1], dzz = out.look[2] - out.pos[2];
    const dist = Math.hypot(dx, dy, dzz);
    out.look[0] += dist * Math.tan(yaw * DEG) * (dzz / Math.max(1e-6, Math.hypot(dx, dzz)));
    out.look[2] -= dist * Math.tan(yaw * DEG) * (dx / Math.max(1e-6, Math.hypot(dx, dzz)));
    out.look[1] += dist * Math.tan(pitch * DEG);
    out.roll += 0.3 * Math.sin(t * 0.97 + 0.7);
  }
  return out;
}
export const vfovOf = (hfovDeg, aspect) => (2 * Math.atan(Math.tan((hfovDeg * DEG) / 2) / aspect)) / DEG;

// Two poses one cut apart read as a JUMP CUT when the view turns less than 30 degrees and the lens changes less than
// 1.5 x (the 30-degree rule); the same pose is no cut at all (a move that arrives where the next shot holds).
export function isJumpCut(a, b) {
  const fa = dirOf(a), fb = dirOf(b);
  const ang = Math.acos(Math.max(-1, Math.min(1, fa[0] * fb[0] + fa[1] * fb[1] + fa[2] * fb[2]))) / DEG;
  const moved = Math.hypot(a.pos[0] - b.pos[0], a.pos[1] - b.pos[1], a.pos[2] - b.pos[2]);
  if (moved < 0.25 && ang < 0.5) return false;
  const ratio = Math.max(a.hfov, b.hfov) / Math.max(1e-6, Math.min(a.hfov, b.hfov));
  return ang < 30 && ratio < 1.5;
}
function dirOf(p) {
  const dx = p.look[0] - p.pos[0], dy = p.look[1] - p.pos[1], dz = p.look[2] - p.pos[2], l = Math.hypot(dx, dy, dz) || 1;
  return [dx / l, dy / l, dz / l];
}

// ------------------------------------------------------------------------------------------------- clearance --
// The nearest distance from a point to the boxes of the rungs (each a centre, half extents and a roll about z), for the
// collision rule (the camera stays 1.5 m from rungs, cubes and rings).
export function clearanceToRungs(p, rungs) {
  let best = Infinity;
  for (const r of rungs) {
    const c = Math.cos(-r.roll * DEG), s = Math.sin(-r.roll * DEG);
    const dx = p[0] - r.centre[0], dy = p[1] - r.centre[1], dz = p[2] - r.centre[2];
    const lx = c * dx - s * dy, ly = s * dx + c * dy;
    const qx = Math.max(0, Math.abs(lx) - r.half[0]), qy = Math.max(0, Math.abs(ly) - r.half[1]), qz = Math.max(0, Math.abs(dz) - r.half[2]);
    best = Math.min(best, Math.hypot(qx, qy, qz));
  }
  return best;
}
// The rung as six boxes in its own frame, after render.js's rungGeometry: the diamond (a square turned 45 degrees,
// 1.0 m from centre to vertex, plus its struts), the beam head hung inside its lower half, the two truss arms (the pixel
// bars ride 0.18 m in front), and the two ends (the X node, the cube and the pickup plate). [x, y, half x, half y, half z,
// turn (degrees)]. Tighter than one 10 m box, which would forbid the corkscrew's honest 2.9 m.
export const RUNG_BOXES = Object.freeze([
  Object.freeze([0, 0, 0.76, 0.76, 0.2, 45]), Object.freeze([0, -0.65, 0.25, 0.3, 0.25, 0]),
  Object.freeze([-2.0, 0, 1.0, 0.2, 0.26, 0]), Object.freeze([2.0, 0, 1.0, 0.2, 0.26, 0]),
  Object.freeze([-4.05, 0, 1.0, 0.66, 0.56, 0]), Object.freeze([4.05, 0, 1.0, 0.66, 0.56, 0]),
]);
const BOX_TURN = RUNG_BOXES.map((b) => [Math.cos(b[5] * DEG), Math.sin(b[5] * DEG)]);
// The distance from p to the strand: poses [{y, roll}] (the rungs hang on x = 0), zs the rungs' z.
export function clearanceToStrand(p, poses, zs) {
  let best = Infinity;
  for (let i = 0; i < zs.length; i++) {
    const dz = p[2] - zs[i];
    if (Math.abs(dz) - 0.56 >= best) continue;
    const r = (poses[i].roll || 0) * DEG, c = Math.cos(r), s = Math.sin(r);
    const dx = p[0], dy = p[1] - poses[i].y;
    const lx = c * dx + s * dy, ly = c * dy - s * dx;              // the point in the rung's frame (rotated by -roll)
    for (let k = 0; k < RUNG_BOXES.length; k++) {
      const b = RUNG_BOXES[k], [tc, ts] = BOX_TURN[k];
      const bx = lx - b[0], by = ly - b[1];
      const qx = Math.max(0, Math.abs(tc * bx + ts * by) - b[2]), qy = Math.max(0, Math.abs(tc * by - ts * bx) - b[3]), qz = Math.max(0, Math.abs(dz) - b[4]);
      const d = Math.hypot(qx, qy, qz);
      if (d < best) best = d;
    }
  }
  return best;
}
// A ring as an annulus: centre, unit normal, inner and outer radius and half thickness. The slats span inner..outer; the
// beam heads stand 0.45 m off the outer rim. tilt leans it back about x (rig.js elementMatrix: normal (0, sin t, cos t));
// a gimbal tilted any other way passes its own normal. A ring spinning about its normal keeps its annulus.
export function ringAnnulus(centre, outer, depth, tiltDeg, normal = null) {
  const t = tiltDeg * DEG, n = normal || [0, Math.sin(t), Math.cos(t)], l = Math.hypot(n[0], n[1], n[2]) || 1;
  return { centre: centre.slice(), normal: [n[0] / l, n[1] / l, n[2] / l], inner: outer - depth - 0.1, outer: outer + 0.45, half: 0.15 };
}
export function clearanceToRings(p, rings) {
  let best = Infinity;
  for (const g of rings) {
    const dx = p[0] - g.centre[0], dy = p[1] - g.centre[1], dz = p[2] - g.centre[2];
    const n = g.normal, h = dx * n[0] + dy * n[1] + dz * n[2];
    const rho = Math.hypot(dx - h * n[0], dy - h * n[1], dz - h * n[2]);
    const dr = Math.max(0, g.inner - rho, rho - g.outer), dh = Math.max(0, Math.abs(h) - g.half);
    best = Math.min(best, Math.hypot(dr, dh));
  }
  return best;
}
// What the camera needs of the rig: the rungs' z and the rings at their home pose.
export function cameraModel(rig) {
  const rungs = rig.elements.filter((e) => e.id === "rung");
  const rings = rig.elements.filter((e) => e.id === "ring").map((e) => ringAnnulus(
    [e.origin[0], e.home && e.home.y !== undefined ? e.home.y : e.origin[1], e.origin[2]], e.params.diameter / 2, e.params.depth,
    (e.home && e.home.tilt) ?? e.params.tilt ?? 0));
  return { z: rungs.map((e) => e.origin[2]), rings, homeY: rungs.length ? rungs[0].home.y : 20 };
}

// ------------------------------------------------------------------------------------------------- validity --
// A formation's rung poses at the phases that matter: one set for a still shape, eight over its measure for a moving one
// (a travelling wave puts every rung at every height once a measure). null for a formation kinetics.js does not know (a
// ring formation): the strand-blind check cannot speak for it, the runtime guard still does.
export function formationPoseSets(def, n, phases = 8) {
  if (!def || !def.name) return null;
  const t = { y: 0, roll: 0, vy: 0, vroll: 0, ay: 0, aroll: 0 };
  let moving = false;
  try { for (let i = 0; i < n; i++) { formationTarget(def.name, def.params, i, n, 0, t); if (t.vy || t.vroll) moving = true; } }
  catch { return null; }
  const m = (def.params && def.params.measure) || 32, k = moving ? phases : 1, out = [];
  for (let j = 0; j < k; j++) {
    const pos = (j / k) * m;
    out.push(Array.from({ length: n }, (_, i) => { formationTarget(def.name, def.params, i, n, pos, t); return { y: t.y, roll: t.roll }; }));
  }
  return out;
}
// The nearest a shot comes to the strand over these pose sets (the centre line and the under-ride's follower simulated
// as the director runs them, at the house tempo over the shot's natural bars).
export function shotClearance(shot, poseSets, zs, samples = 96) {
  const s = shot._ease ? shot : prepareShot(shot);
  const tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  let best = Infinity;
  for (const poses of poseSets) {
    const line = { ys: poses.map((p) => p.y), zs };
    // the under-ride is a follower: step it at 60 Hz or finer, as the page does
    const under = s.kind === "strand" && s.strand.under !== undefined;
    const steps = under ? Math.max(samples, Math.ceil((s.bars ?? 4) * 4 * 60 / NOMINAL_BPM * 60)) : samples;
    const frame = { line, pendulum: pendulumLatch(s, line), under: under ? underFollower((s.bars ?? 4) * 4 * 60 / NOMINAL_BPM / steps) : null };
    for (let k = 0; k <= steps; k++) {
      shotPose(s, k / steps, 0, tmp, frame);
      const c = clearanceToStrand(tmp.pos, poses, zs);
      if (c < best) best = c;
    }
  }
  return best;
}
// The nearest a shot comes to a ring formation's rings (sets of annuli: the phases of a formation whose gimbals move).
export function shotRingClearance(shot, ringSets, samples = 96) {
  const s = shot._ease ? shot : prepareShot(shot);
  const tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  let best = Infinity;
  for (let k = 0; k <= samples; k++) {
    shotPose(s, k / samples, 0, tmp);
    for (const rings of ringSets) { const c = clearanceToRings(tmp.pos, rings); if (c < best) best = c; }
  }
  return best;
}
// Sight (fix round 1): the hall's structure (rig.js hallStructure boxes) between a lens and what a view is FOR. The PA
// hangs at x = +-5 stand between the front of house and the rings, so a view of the orrery's core can show a black slab
// where the core should be; a shot is judged by its worst frame.
// Does the segment p -> q pass through the axis-aligned box b {c, s}? (the slab test, end points included)
export function segmentHitsBox(p, q, b) {
  let t0 = 0, t1 = 1;
  for (let i = 0; i < 3; i++) {
    const lo = b.c[i] - b.s[i] / 2, hi = b.c[i] + b.s[i] / 2, d = q[i] - p[i];
    if (Math.abs(d) < 1e-12) { if (p[i] < lo || p[i] > hi) return false; continue; }
    let a = (lo - p[i]) / d, c = (hi - p[i]) / d;
    if (a > c) { const t = a; a = c; c = t; }
    if (a > t0) t0 = a;
    if (c < t1) t1 = c;
    if (t0 > t1) return false;
  }
  return true;
}
// The share of a target hidden from the eye: rays to its centre and to `ring` points on a disc of radius r facing the
// lens (the core and what hugs it), each blocked by any box. 0 = all of it in sight.
export function viewBlocked(eye, target, r, boxes, ring = 8) {
  let dx = target[0] - eye[0], dy = target[1] - eye[1], dz = target[2] - eye[2];
  const l = Math.hypot(dx, dy, dz) || 1; dx /= l; dy /= l; dz /= l;
  const a = Math.abs(dy) < 0.9 ? [0, 1, 0] : [1, 0, 0];
  let ux = a[1] * dz - a[2] * dy, uy = a[2] * dx - a[0] * dz, uz = a[0] * dy - a[1] * dx;
  const ul = Math.hypot(ux, uy, uz) || 1; ux /= ul; uy /= ul; uz /= ul;
  const vx = dy * uz - dz * uy, vy = dz * ux - dx * uz, vz = dx * uy - dy * ux;
  const q = [0, 0, 0];
  let hidden = 0;
  for (let k = 0; k <= ring; k++) {
    const t = (2 * Math.PI * k) / ring, rr = k === ring ? 0 : r, cu = Math.cos(t) * rr, sv = Math.sin(t) * rr;
    q[0] = target[0] + cu * ux + sv * vx; q[1] = target[1] + cu * uy + sv * vy; q[2] = target[2] + cu * uz + sv * vz;
    for (const b of boxes) if (segmentHitsBox(eye, q, b)) { hidden++; break; }
  }
  return hidden / (ring + 1);
}
// How much of a target a shot hides over its samples: {mean, worst} shares. sight: {target, r, boxes}. A moving shot
// may pass behind a hang for a moment (the parallax is the move); a static one with a slab over the core never helps.
export function shotSight(shot, sight, samples = 48) {
  const s = shot._ease ? shot : prepareShot(shot);
  const tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  let worst = 0, sum = 0;
  for (let k = 0; k <= samples; k++) {
    shotPose(s, k / samples, 0, tmp);
    const b = viewBlocked(tmp.pos, sight.target, sight.r, sight.boxes);
    sum += b; if (b > worst) worst = b;
  }
  return { mean: sum / (samples + 1), worst };
}
// The share of the frame the hall's structure fills in front of the target (the deck excepted: the floor the show stands
// on): a 32 x 18 grid of rays over the lens's view (hfov, 16:9, no roll), each as long as the distance to the target. A
// view can keep its core in sight and still have a 6 m PA hang filling its lower third: this is that number.
export function structureInFrame(pos, look, hfov, boxes, aspect = 16 / 9) {
  let fx = look[0] - pos[0], fy = look[1] - pos[1], fz = look[2] - pos[2];
  const l = Math.hypot(fx, fy, fz) || 1; fx /= l; fy /= l; fz /= l;
  const rl = Math.hypot(fx, fz) || 1, rx = -fz / rl, rz = fx / rl;             // right, level
  const ux = -rz * fy, uy = rz * fx - rx * fz, uz = rx * fy;                   // up = right x forward
  const th = Math.tan((hfov * DEG) / 2), tv = th / aspect, q = [0, 0, 0];
  let hit = 0;
  for (let i = 0; i < 32; i++) for (let j = 0; j < 18; j++) {
    const sx = (((i + 0.5) / 32) * 2 - 1) * th, sy = (((j + 0.5) / 18) * 2 - 1) * tv;
    q[0] = pos[0] + (fx + rx * sx + ux * sy) * l; q[1] = pos[1] + (fy + uy * sy) * l; q[2] = pos[2] + (fz + rz * sx + uz * sy) * l;
    for (const b of boxes) if (b.what !== "deck" && segmentHitsBox(pos, q, b)) { hit++; break; }
  }
  return hit / (32 * 18);
}
// The most of its frame a shot ever gives to the hall's structure, over its move.
export function shotStructure(shot, boxes, samples = 12) {
  const s = shot._ease ? shot : prepareShot(shot);
  const tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  let worst = 0;
  for (let k = 0; k <= samples; k++) { shotPose(s, k / samples, 0, tmp); worst = Math.max(worst, structureInFrame(tmp.pos, tmp.look, tmp.hfov, boxes)); }
  return worst;
}
// The under-ride's height follower: a jerk-limited axis (6 m/s, 4 m/s^2: an FPV drone's climb, quick enough to duck under
// a valley met at 8 m/s), so a rung entering the window eases the lens down instead of stepping it.
export const UNDER_LIMITS = Object.freeze({ vmax: 6, amax: 4, jmax: 16, omega: 5 });
export function underFollower(dt) {
  const ax = new Axis({ ...UNDER_LIMITS });
  let init = false;
  const f = (y) => {
    if (!init) { ax.x = y; ax.v = 0; ax.a = 0; init = true; return y; }
    return ax.step(y, 0, 0, f.dt);
  };
  f.dt = dt;
  f.reset = () => { init = false; };
  return f;
}
// May a shot be dealt in formation `key` (kinetics name `kin`) by its data lists? held: never (a call for Daniel).
export function listAllows(shot, key, kin) {
  if (shot.held) return false;
  if (!key) return true;
  const hit = (list) => list.includes(key) || (kin && list.includes(kin));
  if (Array.isArray(shot.valid_for) && !hit(shot.valid_for)) return false;
  if (Array.isArray(shot.invalid_for) && hit(shot.invalid_for)) return false;
  return true;
}

// ------------------------------------------------------------------------------------------------- director --
// Plays sequences of {shot, bars}. start(seqName, posStart) begins a sequence at a bar line; update(pos, scene) returns
// the pose, the shot, u, and cut = true on the frame a new shot begins. Cuts fall only on bar lines (a sequence starts on
// one and every entry lasts whole bars, or half bars >= 2 beats); the guard's emergency cut falls on a 2-beat line.
// scene (v2, optional; without it the director is v1's): {formation (the set's formation key), def ({name, params}, the
// strand's formation), posLand (the landing bar line while a formation lands), poses ([{y, roll}] live), rings (live
// annuli, else the model's home rings), dt (seconds)}. opts: {model (cameraModel), formations (the set's), views
// (cameras.formation_views), safe (a shot id), glides, posesOf ((key, def) -> rung pose sets or null: a formation the
// kinetics module cannot compute), ringsOf ((key, def) -> sets of ring annuli or null: a ring formation that moves the
// rings off their home pose, so its shots are judged against the rings it makes), sightOf ((key, def) -> {target, r,
// boxes, max} or null: what a formation's views are for, the orrery's core; a shot that hides more than max of it on
// average behind the hall's structure is not dealt there)}.
const SAFE_SHOTS = ["FOH_WIDE", "HALO_LOCK", "FOH_HOLD_ZOOM", "ROOF_ESTABLISH"];
const DEFAULT_GLIDES = ["STRAND_ORBIT_FULL", "PROFILE_GRAPH", "TRIBUNE_HIGH_R", "SPIRAL_ASCENT"];
const LINE_LIMITS = Object.freeze({ vmax: 3, amax: 2, jmax: 8, omega: 4 });   // the low-passed centre line
export class Director {
  constructor(shots, sequences, opts = {}) {
    this.shots = {};
    for (const [id, def] of Object.entries(shots)) this.shots[id] = prepareShot({ id, ...def });
    this.sequences = sequences;
    for (const [name, seq] of Object.entries(sequences)) {
      for (const e of seq) {
        if (!this.shots[e.shot]) throw new Error(`camera sequence ${name}: unknown shot ${e.shot}`);
        if (!(e.bars * 4 >= MIN_SHOT_BEATS)) throw new Error(`camera sequence ${name}: ${e.shot} is shorter than ${MIN_SHOT_BEATS} beats`);
        if (this.shots[e.shot].held) throw new Error(`camera sequence ${name}: ${e.shot} is held (${this.shots[e.shot].held})`);
      }
    }
    this.views = {};
    for (const [key, v] of Object.entries(opts.views || {})) {
      if (key.startsWith("_")) continue;
      for (const id of [...(v.glide || []), ...(v.hero || [])]) if (!this.shots[id]) throw new Error(`camera formation_views.${key}: unknown shot ${id}`);
      if (!(v.hero && v.hero.length)) throw new Error(`camera formation_views.${key}: no hero shot`);
      this.views[key] = v;
    }
    this.model = opts.model || null;
    this.formations = opts.formations || {};
    this.posesOf = opts.posesOf || ((key, def) => formationPoseSets(def, this.model.z.length));
    this.ringsOf = opts.ringsOf || (() => null);
    this.sightOf = opts.sightOf || (() => null);
    this.safe =[opts.safe, ...SAFE_SHOTS].filter((id, i, a) => id && this.shots[id] && !this.shots[id].held && a.indexOf(id) === i);
    this.glides = (opts.glides || DEFAULT_GLIDES).filter((id) => this.shots[id]);
    this.validity = new Map();   // formation key -> Set of the shots clear of the strand there (null: not knowable)
    this.seq = null; this.seqName = ""; this.pos0 = 0;
    this.index = -1;
    this.cuts = [];              // [{pos, shot}] for receipts (bounded)
    this.landings = [];          // [{formation, posLand, glide, hero}] for receipts (bounded)
    this.manual = null;          // a shot held by hand ({shot, u}) or played by hand ({shot, p0, beats})
    this.manualEntered = null;
    this.planEntries = null;     // a phrase's camera plan (v1), or a landing's (v2)
    this.planSource = null;
    this.key = null;             // the playing entry's identity (a sequence entry or a plan entry)
    this.dealt = null;           // the shot dealt for it (the entry's, or its stand-in)
    this.override = null;        // {at, shot, why, p1}: a swap or the guard, from a line inside the entry
    this.lastCutPos = -Infinity;
    this.turn = {};              // per formation and kind: the next view in its list (repeats never deal the same shot)
    this.formationKey = null; this.formationPrev = null; this.formationDef = null; this.posLand = null; this.inTransit = false;
    this.clear = { now: Infinity, min: Infinity, guards: 0 };
    this.pose = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
    this._tmp = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
    if (this.model) {
      const n = this.model.z.length;
      this.line = { ys: new Float64Array(n).fill(this.model.homeY ?? 20), zs: this.model.z };
      this.landLine = null;
      this.followers = Array.from({ length: n }, () => new Axis({ ...LINE_LIMITS, x: this.model.homeY ?? 20 }));
      this.lineInit = false;
      this.under = underFollower(1 / 60);
      this.frame = { line: this.line, pendulum: false, under: this.under };
      this.guardFrame = { line: this.line, pendulum: false, under: null };
      // every formation of the set, judged once at load (about a quarter second for two waves) so no landing stalls a frame
      if (opts.precompute !== false) for (const key of Object.keys(this.formations)) this.validFor(key);
    }
  }
  start(name, pos0) {
    if (!this.sequences[name]) throw new Error(`no camera sequence ${name}`);
    this.seq = this.sequences[name]; this.seqName = name; this.pos0 = pos0; this.index = -1;
    this.planEntries = null; this.planSource = null;
  }
  // A plan: [{shot, p0, p1, why?}]; null clears it. source "phrase" (phrases.js) or "landing" (a formation's views).
  plan(entries, source = "phrase") {
    if (!entries || !entries.length) { this.planEntries = null; this.planSource = null; return; }
    for (const e of entries) {
      if (!this.shots[e.shot]) throw new Error(`camera plan: unknown shot ${e.shot}`);
      if (!(e.p1 - e.p0 >= MIN_SHOT_BEATS - 1e-9)) throw new Error(`camera plan: ${e.shot} is shorter than ${MIN_SHOT_BEATS} beats`);
    }
    this.planEntries = entries.map((e) => ({ ...e }));
    this.planSource = source;
  }
  _planAt(pos) {
    const P = this.planEntries;
    if (!P) return null;
    if (pos >= P[P.length - 1].p1 - 1e-6) { this.planEntries = null; this.planSource = null; return null; }
    // never an entry before its own start (a plan that begins in the future leaves the sequence playing until then)
    for (const e of P) if (pos < e.p1 - 1e-6) return pos >= e.p0 - 1e-6 ? e : null;
    return null;
  }
  // the entry playing at beat position pos (sequences loop), with its start and end positions
  entryAt(pos) {
    const seq = this.seq;
    const total = seq.reduce((s, e) => s + e.bars * 4, 0);
    // the bar line itself, within float error (pos 132.9999999 for beat 133): the new shot, on its own frame
    let q = pos - this.pos0 + 1e-6;
    const loop = Math.floor(q / total);
    q -= loop * total;
    let acc = 0;
    for (let i = 0; i < seq.length; i++) {
      const len = seq[i].bars * 4;
      if (q < acc + len) return { i, e: seq[i], p0: this.pos0 + loop * total + acc, p1: this.pos0 + loop * total + acc + len, loop };
      acc += len;
    }
    const last = seq.length - 1;
    return { i: last, e: seq[last], p0: this.pos0 + loop * total + acc - seq[last].bars * 4, p1: this.pos0 + (loop + 1) * total, loop };
  }

  // ------------------------------------------------------------------------------ what may be dealt, and where --
  // The shots clear of the strand (and of a ring formation's rings) in formation `key`, computed once per formation and
  // cached; null = not knowable.
  validFor(key, def = null) {
    if (!key || !this.model) return null;
    if (this.validity.has(key)) return this.validity.get(key);
    const d = def || this.formations[key], sets = this.posesOf(key, d), rings = this.ringsOf(key, d), sight = this.sightOf(key, d);
    let ok = null;
    if (sets || rings || sight) {
      ok = new Set();
      for (const [id, s] of Object.entries(this.shots)) {
        if (s.held || (sets && shotClearance(s, sets, this.model.z) < CLEARANCE_M) || (rings && shotRingClearance(s, rings) < CLEARANCE_M)) continue;
        if (sight && shotSight(s, sight).mean > (sight.max ?? 0)) continue;
        ok.add(id);
      }
    }
    this.validity.set(key, ok);
    return ok;
  }
  _kin(key) { return key === this.formationKey && this.formationDef ? this.formationDef.name : (this.formations[key] && this.formations[key].name); }
  // the formations a shot must suit now: the one the rig is in and, while it lands, the one it is leaving
  _keys() { return this.inTransit && this.formationPrev ? [this.formationKey, this.formationPrev] : [this.formationKey]; }
  dealable(id, keys = this._keys()) {
    const s = this.shots[id];
    if (!s || s.held) return false;
    for (const key of keys) {
      if (!key) continue;
      if (!listAllows(s, key, this._kin(key))) return false;
      const v = this.validFor(key, key === this.formationKey ? this.formationDef : null);
      if (v && !v.has(id)) return false;
    }
    return true;
  }
  // the shot to deal for an entry that asks for `id`: itself, its own fallback, or the set's safe wide
  deal(id, keys = this._keys(), not = null) {
    if (id !== not && this.dealable(id, keys)) return id;
    const s = this.shots[id];
    for (const c of [s && s.fallback, ...this.safe]) if (c && c !== not && this.shots[c] && this.dealable(c, keys)) return c;
    return id;
  }

  // ------------------------------------------------------------------- formations: the glide and the hero view --
  // A formation lands at posLand (a bar line): one glide from the next bar line while the hoists move (stretched to the
  // window, between half and twice its natural length), then the cut ON posLand to the formation's hero view. Views are
  // looked up by the set's formation key, then by the kinetics name. A phrase that owns the camera keeps it.
  landing(key, pos, posLand) {
    const v = this.views[key] || (this._kin(key) && this.views[this._kin(key)]);
    if (!v || !(posLand > pos)) return null;
    if (this.planEntries && this.planSource !== "landing") return null;
    const bar0 = this.nextLine(pos, 4);
    const both = this.formationPrev ? [key, this.formationPrev] : [key];
    const glide = this._pick(v.glide && v.glide.length ? v.glide : this.glides, key, "glide", both, (id) => {
      const nat = (this.shots[id].bars ?? 4) * 4, start = Math.max(bar0, posLand - 2 * nat);
      return posLand - start >= Math.max(MIN_SHOT_BEATS, nat / 2) - 1e-9;
    });
    const hero = this._pick(v.hero, key, "hero", [key], () => true);
    if (!hero) return null;
    const heroBeats = (v.hero_bars ?? this.shots[hero].bars ?? 8) * 4;
    const entries = [];
    if (glide) entries.push({ shot: glide, p0: Math.max(bar0, posLand - 2 * (this.shots[glide].bars ?? 4) * 4), p1: posLand, why: "landing-glide" });
    entries.push({ shot: hero, p0: posLand, p1: posLand + Math.max(MIN_SHOT_BEATS, heroBeats), why: "landing-hero" });
    this.plan(entries, "landing");
    if (this.landings.length < 64) this.landings.push({ formation: key, pos: +pos.toFixed(4), posLand, glide, hero });
    return entries;
  }
  _pick(list, key, kind, keys, fits) {
    const k = `${key}:${kind}`, n = list.length, t0 = this.turn[k] ?? 0;
    for (let j = 0; j < n; j++) {
      const id = list[(t0 + j) % n];
      if (this.dealable(id, keys) && fits(id)) { this.turn[k] = t0 + j + 1; return id; }
    }
    return null;
  }
  // the first line of `every` beats (a bar: 4; the guard's half bar: 2) at or after pos, on the sequence's grid
  nextLine(pos, every) { return this.pos0 + Math.ceil((pos - this.pos0 - 1e-6) / every) * every; }

  // ---------------------------------------------------------------------------------------------- per frame --
  _sense(pos, scene) {
    const key = scene.formation || null;
    if (key !== this.formationKey) {
      this.formationPrev = this.formationKey; this.formationKey = key;
      this.formationDef = scene.def || this.formations[key] || null;
      this.posLand = scene.posLand ?? null;
      this.landLine = null;
      // the first formation (the load) has nothing to land from
      if (this.formationPrev !== null && this.posLand !== null) this.landing(key, pos, this.posLand);
    }
    this.inTransit = this.posLand !== null && pos < this.posLand - 1e-6;
    if (!this.model || !scene.poses) return;
    const dt = scene.dt ?? 0;
    for (let i = 0; i < this.followers.length; i++) {
      const f = this.followers[i], y = scene.poses[i].y;
      if (!this.lineInit) { f.x = y; f.v = 0; f.a = 0; } else f.step(y, 0, 0, dt);
      this.line.ys[i] = f.x;
    }
    this.lineInit = true;
    this.under.dt = dt > 0 ? dt : 1 / 60;
    // follow: "land" frames the shape the strand is landing into
    if (this.inTransit && !this.landLine && this.formationDef) {
      const sets = formationPoseSets(this.formationDef, this.line.zs.length, 1);
      if (sets) {
        const ys = new Float64Array(this.line.zs.length);
        const t = { y: 0, roll: 0, vy: 0, vroll: 0, ay: 0, aroll: 0 };
        for (let i = 0; i < ys.length; i++) { formationTarget(this.formationDef.name, this.formationDef.params, i, ys.length, this.posLand, t); ys[i] = t.y; }
        this.landLine = { ys, zs: this.line.zs };
      }
    }
  }
  // the entry's frame for strand shots (latched at its start)
  _frameFor(shot) {
    if (!this.model) return null;
    const land = shot.strand && shot.strand.follow === "land" && this.inTransit && this.landLine;
    this.frame.line = land ? this.landLine : this.line;
    return this.frame;
  }
  _enter(shot) {
    if (!this.model) return;
    this.frame.pendulum = pendulumLatch(shot, this.line);
    this.under.reset();
  }
  // the guard: the camera's distance from the live strand and rings now and over the next two beats
  _guard(pos, shot, u, p0, p1) {
    const sc = this.scene, poses = sc.poses, rings = sc.rings || this.model.rings;
    const tmp = this._tmp, span = p1 - p0 || 1;
    let worst = Infinity;
    this.guardFrame.line = this.frame.line; this.guardFrame.pendulum = this.frame.pendulum;
    for (const db of [0, 1, 2]) {
      const uu = u + db / span;
      if (db && uu > 1) break;
      if (db === 0) { tmp.pos[0] = this.pose.pos[0]; tmp.pos[1] = this.pose.pos[1]; tmp.pos[2] = this.pose.pos[2]; }
      else shotPose(shot, uu, pos + db, tmp, this.guardFrame);
      const c = Math.min(clearanceToStrand(tmp.pos, poses, this.model.z), clearanceToRings(tmp.pos, rings));
      if (db === 0) { this.clear.now = c; if (c < this.clear.min) this.clear.min = c; }
      if (c < worst) worst = c;
    }
    return worst;
  }
  _cut(pos, at, shot, why, forShot = null) {
    if (this.cuts.length < 512) this.cuts.push({ pos: +at.toFixed(4), at: +pos.toFixed(4), shot, why, ...(forShot ? { for: forShot } : {}) });
    this.lastCutPos = at;
  }
  update(pos, scene = null) {
    this.scene = scene;
    if (scene) this._sense(pos, scene);
    let cut = false, shot, u;
    if (this.manual) {
      shot = this.shots[this.manual.shot];
      u = this.manual.p0 !== undefined ? (((pos - this.manual.p0) % this.manual.beats) + this.manual.beats) % this.manual.beats / this.manual.beats : this.manual.u;
      if (this.manual.shot !== this.manualEntered) { this.manualEntered = this.manual.shot; this._enter(shot); }
      shotPose(shot, u, pos, this.pose, this._frameFor(shot));
    } else {
      this.manualEntered = null;
      let key, want, p0, p1, why, cutAt;
      const pe = this._planAt(pos);
      if (pe) {
        key = `plan:${pe.shot}@${pe.p0.toFixed(4)}`; want = pe.shot; p0 = pe.p0; p1 = pe.p1; why = pe.why || "plan";
        cutAt = Math.max(pe.p0, pos - 1e-6);
        this.entry = { e: { shot: pe.shot }, p0: pe.p0, p1: pe.p1, plan: true, why };
      } else {
        const en = this.entryAt(pos);
        key = `seq:${this.seqName}@${this.pos0}:${en.loop * 1000 + en.i}`; want = en.e.shot; p0 = en.p0; p1 = en.p1; why = "bar";
        cutAt = en.p0;
        this.entry = en;
      }
      if (key !== this.key) {
        const dealt = this.deal(want);
        // a new entry on the same shot is no cut (a plan or sequence restarting the shot that is already up)
        cut = (this.key !== null && dealt !== this.lastShot) || this.cuts.length === 0;
        this.key = key; this.dealt = dealt; this.override = null;
        if (!pe) this.index = this.entry.loop * 1000 + this.entry.i;
        if (cut) this._cut(pos, cutAt, dealt, why, dealt !== want ? want : null);
        this._enter(this.shots[dealt]);
      }
      shot = this.shots[this.dealt]; u = (pos - p0) / (p1 - p0);
      if (this.scene && this.model && !this.override) {
        // a formation that changed under the playing shot: off it on the next bar line, if a stand-in may be dealt
        if (!this.dealable(this.dealt)) {
          const at = Math.max(this.nextLine(pos, 4), this.nextLine(this.lastCutPos + MIN_SHOT_BEATS, 4));
          const sub = this.deal(this.dealt, this._keys(), this.dealt);
          if (sub !== this.dealt && p1 - at >= MIN_SHOT_BEATS - 1e-9) this.override = { at, shot: sub, why: "swap", p1 };
        }
      }
      if (this.override && pos >= this.override.at - 1e-6) {
        const o = this.override;
        if (!o.started) {
          o.started = true;
          if (o.shot !== this.lastShot) { cut = true; this._cut(pos, o.at, o.shot, o.why, this.dealt); }
          this._enter(this.shots[o.shot]);
        }
        shot = this.shots[o.shot]; u = (pos - o.at) / (o.p1 - o.at);
      }
      shotPose(shot, u, pos, this.pose, this._frameFor(shot));
      if (this.scene && this.model && this.scene.poses) {
        // the runtime guard: below 1.0 m now or within two beats, the safe wide from the next 2-beat line
        const worst = this._guard(pos, shot, u, this.override && this.override.started ? this.override.at : p0, p1);
        if (worst < GUARD_M && !(this.override && this.override.why === "guard")) {
          const at = Math.max(this.nextLine(pos, 2), this.nextLine(this.lastCutPos + MIN_SHOT_BEATS, 2));
          const safe = this.safe.find((id) => id !== shot.id && this.dealable(id)) || this.safe.find((id) => id !== shot.id);
          if (safe && p1 - at >= MIN_SHOT_BEATS - 1e-9) { this.override = { at, shot: safe, why: "guard", p1 }; this.clear.guards++; }
        }
      }
      this.lastShot = shot.id;
    }
    this.pose.shot = shot.id; this.pose.u = u; this.pose.cut = cut;
    this.pose.forShot = !this.manual && shot.id !== (this.entry && this.entry.e.shot) ? this.entry.e.shot : null;
    return this.pose;
  }
}
