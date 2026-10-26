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

export const CAMERA_API = "arsenal.stage-camera/v1";
export const MIN_SHOT_BEATS = 2;
const DEG = Math.PI / 180;

export function minJerk(u) { const x = u <= 0 ? 0 : u >= 1 ? 1 : u; return x * x * x * (10 + x * (-15 + 6 * x)); }
export function smoothstep(u) { const x = u <= 0 ? 0 : u >= 1 ? 1 : u; return x * x * (3 - 2 * x); }

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

// --------------------------------------------------------------------------------------------------- shots --
// Prepare a shot from the scene (arc tables cached). Shot fields: kind, pos | pos_path, look | look_path, hfov (number or
// [from, to]), roll, orbit {centre, radius, height, from_deg, to_deg}, handheld, ev, ease ("minjerk" | "linear").
export function prepareShot(def) {
  const s = { ...def };
  if (s.kind === "path" || s.pos_path) {
    s.kind = "path";
    s._pos = arcTable(s.pos_path);
    if (s.look_path) s._look = arcTable(s.look_path);
  }
  return s;
}
// The pose at u in [0, 1] (already eased or not: shotPose eases), and the handheld noise at beat position pos.
export function shotPose(shot, u, pos = 0, out = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 }) {
  const e = shot.ease === "linear" ? Math.max(0, Math.min(1, u)) : minJerk(u);
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
  } else {
    out.pos[0] = shot.pos[0]; out.pos[1] = shot.pos[1]; out.pos[2] = shot.pos[2];
    out.look[0] = shot.look[0]; out.look[1] = shot.look[1]; out.look[2] = shot.look[2];
  }
  const h = shot.hfov ?? 50;
  out.hfov = Array.isArray(h) ? h[0] + (h[1] - h[0]) * e : h;
  out.roll = shot.roll ?? 0;
  out.ev = shot.ev ?? 0;
  if (shot.handheld) {
    // the handheld wander: three incommensurate slow sines per axis (0.3-0.5 Hz at 150 BPM, as beats: 0.12-0.2 per beat)
    const t = pos;
    const yaw = 0.6 * (0.6 * Math.sin(t * 0.83 + 1.3) + 0.4 * Math.sin(t * 1.31 + 0.2));
    const pitch = 0.6 * (0.6 * Math.sin(t * 0.71 + 2.1) + 0.4 * Math.sin(t * 1.17 + 4.0));
    const dx = out.look[0] - out.pos[0], dy = out.look[1] - out.pos[1], dz = out.look[2] - out.pos[2];
    const dist = Math.hypot(dx, dy, dz);
    out.look[0] += dist * Math.tan(yaw * DEG) * (dz / Math.max(1e-6, Math.hypot(dx, dz)));
    out.look[2] -= dist * Math.tan(yaw * DEG) * (dx / Math.max(1e-6, Math.hypot(dx, dz)));
    out.look[1] += dist * Math.tan(pitch * DEG);
    out.roll += 0.3 * Math.sin(t * 0.97 + 0.7);
  }
  return out;
}
export const vfovOf = (hfovDeg, aspect) => (2 * Math.atan(Math.tan((hfovDeg * DEG) / 2) / aspect)) / DEG;

// ------------------------------------------------------------------------------------------------- director --
// Plays sequences of {shot, bars}. start(seqName, posStart) begins a sequence at a bar line; update(pos) returns the
// pose, the shot, u, and cut = true on the frame a new shot begins. Cuts fall only on bar lines (a sequence starts on
// one and every entry lasts whole bars, or half bars >= 2 beats).
export class Director {
  constructor(shots, sequences) {
    this.shots = {};
    for (const [id, def] of Object.entries(shots)) this.shots[id] = prepareShot({ id, ...def });
    this.sequences = sequences;
    for (const [name, seq] of Object.entries(sequences)) {
      for (const e of seq) {
        if (!this.shots[e.shot]) throw new Error(`camera sequence ${name}: unknown shot ${e.shot}`);
        if (!(e.bars * 4 >= MIN_SHOT_BEATS)) throw new Error(`camera sequence ${name}: ${e.shot} is shorter than ${MIN_SHOT_BEATS} beats`);
      }
    }
    this.seq = null; this.seqName = ""; this.pos0 = 0;
    this.index = -1;
    this.cuts = [];              // [{pos, shot}] for receipts (bounded)
    this.manual = null;          // a shot held by hand (v0: the receipts' pose override)
    this.planEntries = null;     // a phrase's camera plan (v1)
    this.key = null;             // the playing entry's identity (a sequence entry or a plan entry)
    this.pose = { pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 };
  }
  start(name, pos0) {
    if (!this.sequences[name]) throw new Error(`no camera sequence ${name}`);
    this.seq = this.sequences[name]; this.seqName = name; this.pos0 = pos0; this.index = -1;
    this.planEntries = null;
  }
  // A phrase's plan: [{shot, p0, p1, why?}]; null clears it.
  plan(entries) {
    if (!entries || !entries.length) { this.planEntries = null; return; }
    for (const e of entries) {
      if (!this.shots[e.shot]) throw new Error(`camera plan: unknown shot ${e.shot}`);
      if (!(e.p1 - e.p0 >= MIN_SHOT_BEATS - 1e-9)) throw new Error(`camera plan: ${e.shot} is shorter than ${MIN_SHOT_BEATS} beats`);
    }
    this.planEntries = entries.map((e) => ({ ...e }));
  }
  _planAt(pos) {
    const P = this.planEntries;
    if (!P) return null;
    if (pos >= P[P.length - 1].p1 - 1e-6) { this.planEntries = null; return null; }
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
  update(pos) {
    let cut = false, shot, u;
    if (this.manual) {
      shot = this.shots[this.manual.shot];
      u = this.manual.u;
    } else {
      const pe = this._planAt(pos);
      if (pe) {
        const key = `plan:${pe.shot}@${pe.p0.toFixed(4)}`;
        if (key !== this.key) {
          // a new entry on the same shot is no cut (a plan or sequence restarting the shot that is already up)
          cut = (this.key !== null && pe.shot !== this.lastShot) || this.cuts.length === 0;
          this.key = key;
          if (cut && this.cuts.length < 512) this.cuts.push({ pos: +Math.max(pe.p0, pos - 1e-6).toFixed(4), at: +pos.toFixed(4), shot: pe.shot, why: pe.why || "plan" });
        }
        shot = this.shots[pe.shot];
        u = (pos - pe.p0) / (pe.p1 - pe.p0);
        this.entry = { e: { shot: pe.shot }, p0: pe.p0, p1: pe.p1, plan: true };
      } else {
        const en = this.entryAt(pos);
        const key = `seq:${this.seqName}@${this.pos0}:${en.loop * 1000 + en.i}`;
        if (key !== this.key) {
          cut = (this.key !== null && en.e.shot !== this.lastShot) || this.cuts.length === 0;
          this.key = key;
          this.index = en.loop * 1000 + en.i;
          if (cut && this.cuts.length < 512) this.cuts.push({ pos: +en.p0.toFixed(4), at: +pos.toFixed(4), shot: en.e.shot, why: "bar" });
        }
        shot = this.shots[en.e.shot];
        u = (pos - en.p0) / (en.p1 - en.p0);
        this.entry = en;
      }
    }
    shotPose(shot, u, pos, this.pose);
    if (!this.manual) this.lastShot = shot.id;
    this.pose.shot = shot.id; this.pose.u = u; this.pose.cut = cut;
    return this.pose;
  }
}

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
