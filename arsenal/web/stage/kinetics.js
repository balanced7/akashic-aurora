// Virtual Stage v0, kinetics: arsenal/web/stage/kinetics.js (pure ES module). Tests: tests/stage_kinetics.test.mjs.
//
// The strand hangs from hoists, and hoists have motors. A real variable-speed chain hoist or winch (the Kinesys class,
// K1-K4 in the design's sources) moves at up to about 0.5 m/s, accelerates at about 0.4 m/s^2, and a motion controller
// shapes every move into an S-curve (jerk-limited, K13) so the load does not swing. Nothing here can ask for motion a
// motor could not make: every axis follows its target through a jerk-limited follower (vmax, amax, jmax), and a
// formation's amplitude is fitted to those limits before it runs, so the follower tracks it exactly instead of clipping.
//
//   Axis         one hoist: position (m), velocity, acceleration; step(ref, refVel, refAcc, dt) follows a reference with
//                feed-forward and a critically damped correction, then clamps jerk, acceleration and velocity in that
//                order, with the velocity bound looked ahead by the jerk limit (a can come back to 0 before v passes vmax).
//   Rung         an element hung from two pickups 8.6 m apart: height y = (hL + hR) / 2, roll = asin((hR - hL) / L).
//   formations   ceiling, wave (a sine of height and roll travelling down the strand, measure in beats, phase by rung),
//                helix (a static roll step per rung), low line, star (the front rungs dropped over the pit at roll
//                0/30/.../150, the mandala of Daniel's ref-24).
//   landing      time priority (design 2.5): a formation change computes each axis's minimum S-curve time, takes the
//                largest, rounds up to the next bar (or phrase) line, and moves every axis on a minimum-jerk curve that
//                arrives exactly then, on the ONE.
//
// Real versus dream (the design's table, Daniel's call): real = hoists 0.5 m/s, 0.4 m/s^2, roll within +-50 degrees;
// dream = x3 speed and acceleration (the S-curve and the settle stay, so the mass still reads), roll unlimited.
//
// v2 (2026-10-27, kinetics wave A; the kinetic-geometry check's corrections):
//   sCurveTime / sCurvePlan   the 7-segment jerk-limited S-curve WITH CRUISE a real motion controller runs (Kinesys
//                class): 6 m at the real limits takes 13.45 s, the quintic 22.5 s. A formation may ask for it with
//                params.curve = "scurve" (long real moves read as a machine glide); the quintic stays the default.
//   strand shapes  arch, valley, ramp (to the eye), stairs. The v0 helix (-82.5..+82.5 by 15) CLAMPS 6 of 12 rungs at
//                +-50 in real mode; the honest real helix is the travelling roll sine ("wave", size 0, roll 50, spread
//                2.67): fitted it turns +-13.7 degrees at a 32-beat measure and needs about 104 beats for +-50.
//   RingRig      the four rings as 3-point hung elements: lift (y) and tilt on the same hoists, so the tilt rate is the
//                hoist speed over the pickup radius (R0: 0.5 / 14 rad/s = 2.0 deg/s, R3: 9.5) -- ringAxisLimits is the
//                one place that number comes from. Lift before tilt (a raise moves first, a lowering last), every
//                target clamped into the ring's legal tilt window at its height (rig.js ringTiltWindow: R0 at its hang
//                only clears the deck and the back wall between about 47 and 63 degrees). DREAM formations add
//                continuous rotators (yaw about the vertical, spin about the ring's own normal, axial travel along it):
//                unwrapped angles on followers with no limits, never the two-pickup model, which aliases past 90.
const DEG = Math.PI / 180;
const TAU = Math.PI * 2;

export const MODES = Object.freeze({
  real: { vmax: 0.5, amax: 0.4, jmax: 2.0, roll: 50 },
  dream: { vmax: 1.5, amax: 1.2, jmax: 6.0, roll: 180 },
});
// Moves longer than this (metres) are the ones a formation may run on the S-curve with cruise; under it the two shapes
// differ by 10 % or less and the quintic's organic settle reads better.
export const SCURVE_MIN_M = 1.5;

// ----------------------------------------------------------------------------------------------- move times --
// The design's trapezoid minimum time (constant acceleration, no jerk limit): T = D/v + v/a when D >= v^2/a, else 2 sqrt(D/a).
export function trapezoidTime(D, vmax, amax) {
  D = Math.abs(D);
  if (D <= 0) return 0;
  return D >= (vmax * vmax) / amax ? D / vmax + vmax / amax : 2 * Math.sqrt(D / amax);
}
// The minimum-jerk (quintic) curve s(u) = 10u^3 - 15u^4 + 6u^5 over T: peak velocity 1.875 D/T, peak acceleration
// 5.7735 D/T^2, peak jerk 60 D/T^3. Its minimum time under the three limits:
export function quinticTime(D, vmax, amax, jmax) {
  D = Math.abs(D);
  if (D <= 0) return 0;
  return Math.max(1.875 * D / vmax, Math.sqrt(5.773502692 * D / amax), Math.cbrt(60 * D / jmax));
}
// The 7-segment S-curve rest to rest: jerk up, constant acceleration, jerk down, cruise, and the mirror image. Tj the
// jerk phase, Ta the constant-acceleration phase, Tv the cruise, vp the peak speed it reaches (vmax unless D is short).
export function sCurvePlan(D, vmax, amax, jmax) {
  D = Math.abs(D);
  if (!(D > 0)) return { D: 0, T: 0, Tj: 0, Ta: 0, Tv: 0, vp: 0, ap: 0, j: jmax };
  let Tj, Ta, vp = vmax;
  if ((amax * amax) / jmax >= vmax) { Tj = Math.sqrt(vmax / jmax); Ta = 0; }
  else { Tj = amax / jmax; Ta = vmax / amax - Tj; }
  const acc = 2 * Tj + Ta;                          // the time to reach vp (the distance there and back: vp * acc)
  if (D >= vp * acc) return { D, T: acc + D / vp, Tj, Ta, Tv: D / vp - acc, vp, ap: jmax * Tj, j: jmax };
  // no cruise: the peak speed vp < vmax. With amax reached: D = vp (amax / j + vp / amax)
  const r = amax / jmax;
  vp = (amax / 2) * (-r + Math.sqrt(r * r + (4 * D) / amax));
  if (vp >= (amax * amax) / jmax) { Tj = r; Ta = vp / amax - r; return { D, T: 2 * (2 * Tj + Ta), Tj, Ta, Tv: 0, vp, ap: amax, j: jmax }; }
  // amax never reached: D = 2 vp^1.5 / sqrt(j)
  vp = Math.pow((D * Math.sqrt(jmax)) / 2, 2 / 3);
  Tj = Math.sqrt(vp / jmax);
  return { D, T: 4 * Tj, Tj, Ta: 0, Tv: 0, vp, ap: jmax * Tj, j: jmax };
}
export function sCurveTime(D, vmax, amax, jmax) { return sCurvePlan(D, vmax, amax, jmax).T; }
// The same curve stretched to last exactly T seconds (time priority hands a move more time than its minimum): the cruise
// speed is lowered until the plan's time is T (the time falls as the speed rises, so a bisection finds it).
export function sCurveFit(D, T, vmax, amax, jmax) {
  const p0 = sCurvePlan(D, vmax, amax, jmax);
  if (!(T > p0.T)) return p0;
  let lo = 1e-6, hi = vmax;
  for (let i = 0; i < 48; i++) { const mid = (lo + hi) / 2; if (sCurvePlan(D, mid, amax, jmax).T > T) lo = mid; else hi = mid; }
  return sCurvePlan(D, hi, amax, jmax);
}
// Position, speed and acceleration of a plan at time t (0..T), integrated piece by piece; distances are of |D|.
export function sCurveAt(p, t, out = { s: 0, v: 0, a: 0 }) {
  if (!(p.T > 0) || t >= p.T) { out.s = p.D; out.v = 0; out.a = 0; return out; }
  if (t <= 0) { out.s = 0; out.v = 0; out.a = 0; return out; }
  const half = 2 * p.Tj + p.Ta;
  // the acceleration half, evaluated at time u from its start (and mirrored for the deceleration half)
  const accel = (u, o) => {
    const j = p.j, Tj = p.Tj, Ta = p.Ta, ap = j * Tj;
    if (u < Tj) { o.a = j * u; o.v = (j * u * u) / 2; o.s = (j * u * u * u) / 6; return o; }
    const v1 = (j * Tj * Tj) / 2, s1 = (j * Tj * Tj * Tj) / 6;
    if (u < Tj + Ta) { const w = u - Tj; o.a = ap; o.v = v1 + ap * w; o.s = s1 + v1 * w + (ap * w * w) / 2; return o; }
    const v2 = v1 + ap * Ta, s2 = s1 + v1 * Ta + (ap * Ta * Ta) / 2, w = Math.min(Tj, u - Tj - Ta);
    o.a = ap - j * w; o.v = v2 + ap * w - (j * w * w) / 2; o.s = s2 + v2 * w + (ap * w * w) / 2 - (j * w * w * w) / 6;
    return o;
  };
  if (t < half) return accel(t, out);
  const sAcc = (p.vp * half) / 2;
  if (t < half + p.Tv) { out.a = 0; out.v = p.vp; out.s = sAcc + p.vp * (t - half); return out; }
  accel(p.T - t, out);                                // the mirror: the remaining distance of the deceleration
  out.s = p.D - out.s; out.a = -out.a;
  return out;
}

export function quintic(u) { const x = u <= 0 ? 0 : u >= 1 ? 1 : u; return x * x * x * (10 + x * (-15 + 6 * x)); }
export function quinticD1(u) { const x = u <= 0 ? 0 : u >= 1 ? 1 : u; return 30 * x * x * (1 - x) * (1 - x); }
export function quinticD2(u) { const x = u <= 0 ? 0 : u >= 1 ? 1 : u; return 60 * x * (1 - x) * (1 - 2 * x); }

// ------------------------------------------------------------------------------------------------------ axis --
export class Axis {
  constructor({ x = 0, vmax = 0.5, amax = 0.4, jmax = 2, min = -Infinity, max = Infinity, omega = 5 } = {}) {
    this.x = x; this.v = 0; this.a = 0;
    this.vmax = vmax; this.amax = amax; this.jmax = jmax;
    this.min = min; this.max = max;
    this.kp = omega * omega; this.kd = 2 * omega;   // critically damped correction around the feed-forward
  }
  step(ref, refVel, refAcc, dt) {
    if (!(dt > 0)) return this.x;
    const r = Math.min(this.max, Math.max(this.min, ref));
    let aDes = refAcc + this.kp * (r - this.x) + this.kd * (refVel - this.v);
    // the velocity bound, looked ahead in discrete steps: after this step (v' = v + a dt) the acceleration must still be
    // able to come back to zero at the jerk limit (taking about a^2 / (2 j) of velocity) without passing vmax:
    // a^2 / (2 j) + a dt <= vmax - v  ->  a <= -j dt + sqrt((j dt)^2 + 2 j (vmax - v))
    const jd = this.jmax * dt;
    const up = -jd + Math.sqrt(jd * jd + 2 * this.jmax * Math.max(0, this.vmax - this.v));
    const dn = jd - Math.sqrt(jd * jd + 2 * this.jmax * Math.max(0, this.vmax + this.v));
    aDes = Math.min(this.amax, up, Math.max(-this.amax, dn, aDes));
    const j = Math.max(-this.jmax, Math.min(this.jmax, (aDes - this.a) / dt));
    this.a += j * dt;
    this.v += this.a * dt;
    // numerical guard only (the bound above keeps |v| <= vmax)
    if (this.v > this.vmax * 1.0005) this.v = this.vmax * 1.0005; else if (this.v < -this.vmax * 1.0005) this.v = -this.vmax * 1.0005;
    this.x += this.v * dt;
    if (this.x > this.max) { this.x = this.max; this.v = Math.min(0, this.v); this.a = Math.min(0, this.a); }
    else if (this.x < this.min) { this.x = this.min; this.v = Math.max(0, this.v); this.a = Math.max(0, this.a); }
    return this.x;
  }
}

// --------------------------------------------------------------------------------------------- formations --
// A formation gives each rung (index i of n) a target {y, roll} at beat position pos, and its velocity d/dpos.
// fit: the amplitude ceiling for a moving formation so that the hoists can follow it (see fitAmplitude).
export function fitAmplitude(amp, periodS, { vmax, amax, jmax }, armM = 0) {
  // a sine of amplitude A and period P needs v = 2 pi A / P, a = (2 pi / P)^2 A, j = (2 pi / P)^3 A
  if (!(periodS > 0)) return 0;
  const w = TAU / periodS;
  return Math.min(amp, vmax / w, amax / (w * w), jmax / (w * w * w)) - armM * 0;
}

// The formations the scene names. params from the scene; bpm only to fit a moving one to the hoists.
export function formationTarget(name, params, i, n, pos, out = { y: 0, roll: 0, vy: 0, vroll: 0, ay: 0, aroll: 0 }) {
  const p = params || {};
  out.vy = out.vroll = out.ay = out.aroll = 0;
  switch (name) {
    case "ceiling": out.y = p.y ?? 20; out.roll = 0; break;
    case "low": out.y = p.y ?? 9; out.roll = 0; break;
    case "helix": out.y = p.y ?? 18; out.roll = (p.roll0 ?? -82.5) + (p.step ?? 15) * i; break;
    case "zigzag": out.y = p.y ?? 18; out.roll = (i % 2 ? -1 : 1) * (p.roll ?? 35); break;
    case "star": {
      const front = p.front ?? 6;
      if (i < front) { out.y = p.y ?? 10; out.roll = (p.step ?? 30) * i; }
      else { out.y = p.rest_y ?? 21; out.roll = 0; }
      break;
    }
    // v2, the strand shapes (still shapes: they land, then hold): an ARCH crests mid-hall, a rainbow over the crowd; a
    // VALLEY dips its middle toward the crowd; the RAMP descends toward the stage and, from front of house, pours into the
    // ring's eye; STAIRS hold pairs of rungs at alternating heights. roll (default 0) tips every rung the same way.
    case "arch": out.y = (p.base ?? 9) + (p.rise ?? 12) * Math.sin((Math.PI * (i + 0.5)) / n); out.roll = p.roll ?? 0; break;
    case "valley": { const mid = (n - 1) / 2; out.y = (p.low ?? 10) + (p.depth ?? 10) * Math.abs(i - mid) / (mid || 1); out.roll = p.roll ?? 0; break; }
    case "ramp": out.y = (p.top ?? 21) - (p.step ?? 1.1) * i; out.roll = p.roll ?? 0; break;
    case "stairs": out.y = (p.y ?? 18) + (Math.floor(i / 2) % 2 ? -1 : 1) * (p.step ?? 2); out.roll = p.roll ?? 0; break;
    case "wave": {
      // y = centre + A sin(2 pi (pos / measure + i / n)), roll = R sin(2 pi (pos / measure + i / n + 1/4))
      const m = p.measure ?? 32;
      const ph = TAU * (pos / m + (p.spread ?? 1) * i / n);
      const A = p._A ?? p.size ?? 1, R = p._R ?? p.roll ?? 0, w = TAU / m;   // w: radians per beat
      out.y = (p.centre ?? 16) + A * Math.sin(ph);
      out.roll = R * Math.sin(ph + Math.PI / 2);
      out.vy = A * w * Math.cos(ph); out.vroll = R * w * Math.cos(ph + Math.PI / 2);
      out.ay = -A * w * w * Math.sin(ph); out.aroll = -R * w * w * Math.sin(ph + Math.PI / 2);
      break;
    }
    default: throw new Error(`unknown formation ${name}`);
  }
  return out;
}

// ---------------------------------------------------------------------------------------------------- strand --
// The rungs and their 2 x n hoists. pose(i) -> {y, roll}. land(name, params, grid, nowMs) starts a time-priority move;
// update(grid, tEval, dt) steps every hoist.
export class Strand {
  constructor({ rungs, pickupX = 4.3, mode = "real", home = { y: 20, roll: 0 }, limits = { y: [8, 22], roll: [-50, 50] } } = {}) {
    this.n = rungs;
    this.L = 2 * pickupX;
    this.half = pickupX;
    this.setMode(mode, false);
    this.limits = limits;
    const lo = limits.y[0] - this.half, hi = limits.y[1] + this.half;
    this.axes = [];
    for (let i = 0; i < rungs; i++) {
      for (let s = 0; s < 2; s++) this.axes.push(new Axis({ x: home.y, min: lo, max: hi, ...this.lim }));
    }
    this.formation = { name: "ceiling", params: { y: home.y } };
    this.move = null;          // {from: [h...], to: (formation), pos0, posLand}
    this.poses = Array.from({ length: rungs }, () => ({ y: home.y, roll: 0 }));
    this.tmp = { y: 0, roll: 0, vy: 0, vroll: 0, ay: 0, aroll: 0 };
    this.sc = { s: 0, v: 0, a: 0 };
    this.lands = [];           // [{name, posLand, tLand}] for receipts
  }
  setMode(mode, apply = true) {
    this.mode = MODES[mode] ? mode : "real";
    this.lim = { vmax: MODES[this.mode].vmax, amax: MODES[this.mode].amax, jmax: MODES[this.mode].jmax };
    this.rollMax = MODES[this.mode].roll;
    if (apply) for (const a of this.axes) Object.assign(a, this.lim);
  }
  // the two hoist heights for a rung at height y (rung centre) and roll (degrees)
  hoists(y, rollDeg, out = [0, 0]) {
    const r = Math.max(-this.rollMax, Math.min(this.rollMax, rollDeg));
    const lim = Math.min(this.limits.roll[1], Math.max(this.limits.roll[0], r));
    const rr = this.mode === "real" ? lim : r;
    const d = this.half * Math.sin(rr * DEG);
    out[0] = y - d; out[1] = y + d;
    return out;
  }
  // a moving formation's amplitudes fitted to the hoists at this tempo (the roll's pickup excursion and the height share
  // the same motors, so each gets half the budget when both move)
  fit(name, params, bpm) {
    if (name !== "wave") return params;
    const m = params.measure ?? 32;
    const P = (m * 60) / bpm;
    const both = (params.size ?? 0) > 0 && (params.roll ?? 0) !== 0 ? 0.5 : 1;
    const budget = { vmax: this.lim.vmax * both, amax: this.lim.amax * both, jmax: this.lim.jmax * both };
    const A = fitAmplitude(params.size ?? 1, P, budget);
    const pickupAmp = this.half * Math.sin(Math.min(this.rollMax, Math.abs(params.roll ?? 0)) * DEG);
    const pickupFit = fitAmplitude(pickupAmp, P, budget);
    const R = pickupAmp > 0 ? Math.sign(params.roll) * Math.asin(Math.min(1, pickupFit / this.half)) / DEG : 0;
    return { ...params, _A: A, _R: R, _bpm: bpm };
  }
  // Start a time-priority move to formation `name`, landing on the next bar (or phrase) line it can make. A formation
  // whose params say curve: "scurve" moves its long axes (over SCURVE_MIN_M) on the S-curve with cruise.
  land(name, params, grid, nowMs, { land = "bar" } = {}) {
    const pos = grid.posAt(nowMs);
    const fitted = this.fit(name, params || {}, grid.bpm);
    const scurve = fitted.curve === "scurve";
    const timeOf = (D, ax) => (scurve && Math.abs(D) > SCURVE_MIN_M ? sCurveTime : quinticTime)(D, ax.vmax, ax.amax, ax.jmax);
    // the slowest axis's minimum S-curve time to reach the formation as it will be at landing position p
    const tgt = [0, 0];
    const needS = (p) => {
      let T = 0;
      for (let i = 0; i < this.n; i++) {
        formationTarget(name, fitted, i, this.n, p, this.tmp);
        this.hoists(this.tmp.y, this.tmp.roll, tgt);
        for (let s = 0; s < 2; s++) {
          const ax = this.axes[i * 2 + s];
          T = Math.max(T, timeOf(tgt[s] - ax.x, ax));
        }
      }
      return T;
    };
    let T = needS(grid.nextBarPos(pos) + 4);
    let beats = (T * 1000) / grid.period;
    let posLand = land === "phrase" ? grid.nextPhrasePos(pos + beats) : grid.nextBarPos(pos + beats - 1e-9);
    // a moving formation is somewhere else at the landing than at the guess: check there, and wait a bar (or phrase)
    // more until the move fits
    for (let k = 0; k < 16; k++) {
      T = needS(posLand);
      beats = (T * 1000) / grid.period;
      if (posLand - pos >= beats) break;
      posLand = land === "phrase" ? grid.nextPhrasePos(posLand) : posLand + 4;
    }
    this.move = { name, params: fitted, pos0: pos, posLand, from: this.axes.map((a) => a.x), tMinS: T, plans: null };
    if (scurve) {
      // each long axis's S-curve stretched over the move's span (the short ones keep the quintic)
      const dS = ((posLand - pos) * grid.period) / 1000;
      this.move.plans = this.axes.map((ax, k) => {
        formationTarget(name, fitted, k >> 1, this.n, posLand, this.tmp);
        const D = this.hoists(this.tmp.y, this.tmp.roll, tgt)[k & 1] - ax.x;
        return Math.abs(D) > SCURVE_MIN_M ? sCurveFit(D, dS, ax.vmax, ax.amax, ax.jmax) : null;
      });
    }
    this.formation = { name, params: fitted };
    this.lands.push({ name, posLand, tMinS: +T.toFixed(3) });
    return { posLand, tMinS: T };
  }
  // Switch to a formation with no landing move (it must start where the rig is; used at load).
  set(name, params, bpm) {
    this.formation = { name, params: this.fit(name, params || {}, bpm) };
    this.move = null;
  }
  update(grid, tEval, dt) {
    const pos = grid.posAt(tEval);
    const bps = 1000 / grid.period;            // beats per second, to turn d/dpos into d/dt
    const f = this.formation;
    const tgt = [0, 0], tv = [0, 0], ta = [0, 0];
    for (let i = 0; i < this.n; i++) {
      formationTarget(f.name, f.params, i, this.n, pos, this.tmp);
      const t = this.tmp;
      this.hoists(t.y, t.roll, tgt);
      // feed-forward velocity and acceleration of each pickup (small-angle: d(h)/dt = vy +- half cos(roll) vroll)
      const c = this.half * Math.cos(t.roll * DEG) * DEG;
      tv[0] = (t.vy - c * t.vroll) * bps; tv[1] = (t.vy + c * t.vroll) * bps;
      ta[0] = (t.ay - c * t.aroll) * bps * bps; ta[1] = (t.ay + c * t.aroll) * bps * bps;
      for (let s = 0; s < 2; s++) {
        const k = i * 2 + s;
        let ref = tgt[s], rv = tv[s], ra = ta[s];
        if (this.move) {
          const span = this.move.posLand - this.move.pos0;
          const u = span > 0 ? (pos - this.move.pos0) / span : 1;
          if (u < 1) {
            const x0 = this.move.from[k], dS = span / bps;   // seconds of the move
            // the reference glides from where the axis was to where the formation will be at the landing
            formationTarget(f.name, f.params, i, this.n, this.move.posLand, this.tmp);
            const land = this.hoists(this.tmp.y, this.tmp.roll, [0, 0])[s];
            const plan = this.move.plans && this.move.plans[k];
            if (plan) {
              // the S-curve, mapped onto the move's fraction (a tempo change mid-move stretches it with the beat)
              const sg = land >= x0 ? 1 : -1, r = plan.T / dS, c = sCurveAt(plan, u * plan.T, this.sc);
              ref = x0 + sg * c.s; rv = sg * c.v * r; ra = sg * c.a * r * r;
            } else {
              ref = x0 + (land - x0) * quintic(u);
              rv = (land - x0) * quinticD1(u) / dS;
              ra = (land - x0) * quinticD2(u) / (dS * dS);
            }
            formationTarget(f.name, f.params, i, this.n, pos, this.tmp);
          }
        }
        this.axes[k].step(ref, rv, ra, dt);
      }
    }
    if (this.move && pos >= this.move.posLand) this.move = null;
    for (let i = 0; i < this.n; i++) {
      const hL = this.axes[i * 2].x, hR = this.axes[i * 2 + 1].x;
      this.poses[i].y = (hL + hR) / 2;
      this.poses[i].roll = Math.asin(Math.max(-1, Math.min(1, (hR - hL) / this.L))) / DEG;
    }
    return this.poses;
  }
}

// ------------------------------------------------------------------------------------------------- the ring rig --
// The scene's ring_rig is the one source of these numbers: real.hoist {vmax, amax, jmax} (the pickups on the ring's
// outer radius), dream.scale (x3) for lift and tilt, dream.rotator {vmax_deg, amax_deg, jmax_deg} for the continuous
// rotators (yaw, spin) and dream.axial {vmax, amax, jmax} for the travel along the ring's normal. A tilt of a 3-point
// hung ring moves its rim pickups by r * dtilt, so the tilt's limits are the hoist's divided by r.
export const RING_RIG_DEFAULT = Object.freeze({
  real: { hoist: { vmax: 0.5, amax: 0.4, jmax: 2.0 } },
  dream: { scale: 3, rotator: { vmax_deg: 60, amax_deg: 30, jmax_deg: 120 }, axial: { vmax: 3, amax: 2, jmax: 8 } },
});
export function ringAxisLimits(ringRig, pickupR, mode = "real") {
  const rr = ringRig || RING_RIG_DEFAULT, h = (rr.real && rr.real.hoist) || RING_RIG_DEFAULT.real.hoist;
  const dream = mode === "dream", k = dream ? ((rr.dream && rr.dream.scale) ?? 3) : 1;
  const toDeg = 1 / (DEG * Math.max(0.1, pickupR));
  const rot = (rr.dream && rr.dream.rotator) || RING_RIG_DEFAULT.dream.rotator;
  const ax = (rr.dream && rr.dream.axial) || RING_RIG_DEFAULT.dream.axial;
  return {
    y: { vmax: h.vmax * k, amax: h.amax * k, jmax: h.jmax * k },
    tilt: { vmax: h.vmax * k * toDeg, amax: h.amax * k * toDeg, jmax: h.jmax * k * toDeg },
    // the rotators and the axial travel exist in dream mode only (a 3-point hung ring cannot turn about its own axis)
    rot: dream ? { vmax: rot.vmax_deg, amax: rot.amax_deg, jmax: rot.jmax_deg } : null,
    axial: dream ? { vmax: ax.vmax, amax: ax.amax, jmax: ax.jmax } : null,
  };
}
// A cubic Hermite from (p0, m0) to (p1, m1) over u in 0..1 (m: the slope per unit u): a rotator's spin-up into a
// formation's cruise, so the ring arrives at the formation's angle AND its speed on the landing line.
export function hermite(p0, m0, p1, m1, u, out = { x: 0, v: 0, a: 0 }) {
  const x = u <= 0 ? 0 : u >= 1 ? 1 : u, x2 = x * x, x3 = x2 * x;
  out.x = (2 * x3 - 3 * x2 + 1) * p0 + (x3 - 2 * x2 + x) * m0 + (-2 * x3 + 3 * x2) * p1 + (x3 - x2) * m1;
  out.v = (6 * x2 - 6 * x) * p0 + (3 * x2 - 4 * x + 1) * m0 + (-6 * x2 + 6 * x) * p1 + (3 * x2 - 2 * x) * m1;
  out.a = (12 * x - 6) * p0 + (6 * x - 4) * m0 + (-12 * x + 6) * p1 + (6 * x - 2) * m1;
  return out;
}
// A formation's target for ring k at beat position pos: {y, tilt, yaw, spin, axial} and the rotators' rates (deg/beat).
// def.rings[k]: {tilt, lift?, yaw?, yaw_beats?, spin?, spin_beats?, axial?}; *_beats is beats per turn (a prime for the
// orrery, so each ring is beat-locked and the set never repeats; negative turns the other way).
export const RING_DOFS = Object.freeze(["y", "tilt", "yaw", "spin", "axial"]);
export function ringTarget(def, k, home, pos, out = { y: 0, tilt: 0, yaw: 0, spin: 0, axial: 0, vyaw: 0, vspin: 0 }) {
  const r = (def && def.rings && def.rings[k]) || {};
  out.y = home.y + (r.lift ?? (def && def.lift) ?? 0);
  out.tilt = r.tilt ?? home.tilt;
  out.vyaw = r.yaw_beats ? 360 / r.yaw_beats : 0;
  out.vspin = r.spin_beats ? 360 / r.spin_beats : 0;
  out.yaw = (r.yaw ?? 0) + out.vyaw * pos;
  out.spin = (r.spin ?? 0) + out.vspin * pos;
  out.axial = r.axial ?? 0;
  return out;
}
// The 360-degree turn of a continuous target nearest a wanted value (an unwrapped rotator never spins back the long way).
export function nearestTurn(target, wanted) { return target + 360 * Math.round((wanted - target) / 360); }

export class RingRig {
  // rings: [{radius (the pickup radius), home {y, tilt}, limits {y, tilt}, window(y) -> [tiltLo, tiltHi] (the legal
  // tilts at height y: rig.js ringTiltWindow)}]; ringRig: the scene's ring_rig.
  constructor({ rings, ringRig = null }) {
    this.n = rings.length;
    this.rings = rings;
    this.ringRig = ringRig || RING_RIG_DEFAULT;
    this.axes = rings.map((r) => ({
      y: new Axis({ x: r.home.y, min: r.limits.y[0], max: r.limits.y[1] }),
      tilt: new Axis({ x: r.home.tilt, min: r.limits.tilt[0], max: r.limits.tilt[1] }),
      yaw: new Axis({ x: 0 }), spin: new Axis({ x: 0 }), axial: new Axis({ x: 0, min: -12, max: 12 }),
    }));
    this.setMode("real");
    this.poses = rings.map((r) => ({ y: r.home.y, tilt: r.home.tilt, yaw: 0, spin: 0, axial: 0 }));
    this.def = null;           // the formation the rings are in (or moving to)
    this.key = "home";
    this.move = null;
    this.tmp = { y: 0, tilt: 0, yaw: 0, spin: 0, axial: 0, vyaw: 0, vspin: 0 };
    this.tl = { y: 0, tilt: 0, yaw: 0, spin: 0, axial: 0, vyaw: 0, vspin: 0 };
    this.g = { x: 0, v: 0, a: 0 };
    this.sc = { s: 0, v: 0, a: 0 };
    this.lands = [];           // [{key, pos, posLand, rings: [{k, start, land}]}] for receipts
    this.clamped = [];         // tilts a formation asked for outside the ring's legal window, clamped (for receipts)
  }
  setMode(mode) {
    this.mode = mode === "dream" ? "dream" : "real";
    for (let k = 0; k < this.n; k++) {
      const L = ringAxisLimits(this.ringRig, this.rings[k].radius, this.mode), a = this.axes[k];
      const D = ringAxisLimits(this.ringRig, this.rings[k].radius, "dream");
      Object.assign(a.y, L.y); Object.assign(a.tilt, L.tilt);
      // the rotators keep their dream limits: a real formation only takes them home (to the nearest whole turn)
      Object.assign(a.yaw, D.rot); Object.assign(a.spin, D.rot); Object.assign(a.axial, D.axial);
    }
  }
  // The legal target of ring k: the formation's, its tilt clamped into the window at its height.
  target(def, k, pos, out = this.tmp, note = false) {
    const r = this.rings[k];
    ringTarget(def, k, r.home, pos, out);
    out.y = Math.min(r.limits.y[1], Math.max(r.limits.y[0], out.y));
    const w = r.window ? r.window(out.y) : r.limits.tilt;
    if (w && (out.tilt < w[0] - 1e-9 || out.tilt > w[1] + 1e-9)) {
      const t = Math.min(w[1], Math.max(w[0], out.tilt));
      if (note && this.clamped.length < 64) this.clamped.push({ key: this.key, ring: k, asked: out.tilt, tilt: +t.toFixed(3) });
      out.tilt = t;
    }
    return out;
  }
  // Put the rings in a formation now, with no move (the load, a receipt). bpm sets the rotators already turning.
  set(key, def, pos = 0, bpm = 150) {
    this.key = key; this.def = def; this.move = null;
    this.setMode(def && def.dream ? "dream" : "real");
    for (let k = 0; k < this.n; k++) {
      const t = this.target(def, k, pos), a = this.axes[k];
      a.y.x = t.y; a.tilt.x = t.tilt; a.yaw.x = t.yaw; a.spin.x = t.spin; a.axial.x = t.axial;
      for (const ax of [a.y, a.tilt, a.yaw, a.spin, a.axial]) { ax.v = 0; ax.a = 0; }
      a.yaw.v = (t.vyaw * bpm) / 60; a.spin.v = (t.vspin * bpm) / 60;
      Object.assign(this.poses[k], { y: t.y, tilt: t.tilt, yaw: t.yaw, spin: t.spin, axial: t.axial });
    }
  }
  // A time-priority move into formation `key`. Ring k starts on the next bar line plus its rank in the reveal order times
  // stagger_beats (the reveal in depth order), lifts before it tilts (or tilts before it lowers), and lands on the first
  // bar line its slowest axis can make; the formation lands when its last ring does. A move from or to a dream formation
  // runs on dream limits. Returns {posLand, rings}.
  land(key, def, grid, nowMs) {
    const pos = grid.posAt(nowMs), bps = 1000 / grid.period;
    this.setMode((def && def.dream) || (this.def && this.def.dream) ? "dream" : "real");
    const reveal = (def && def.reveal) || {};
    const order = reveal.order || [...Array(this.n).keys()];
    const stagger = reveal.stagger_beats ?? 0;
    const start0 = grid.nextBarPos(pos - 1e-9);
    this.key = key;
    const timeOf = (ax, D) => (this.mode === "real" ? sCurveTime : quinticTime)(D, ax.vmax, ax.amax, ax.jmax);
    const rings = [];
    let posLand = start0;
    for (let k = 0; k < this.n; k++) {
      const a = this.axes[k];
      const start = start0 + Math.max(0, order.indexOf(k)) * stagger;
      let t = this.target(def, k, start + 8);
      const rise = t.y > a.y.x + 1e-6, lower = t.y < a.y.x - 1e-6;
      const phaseTimes = () => {
        const tY = timeOf(a.y, t.y - a.y.x), tT = timeOf(a.tilt, t.tilt - a.tilt.x), tX = timeOf(a.axial, t.axial - a.axial.x);
        // a rotator needs the time to change its speed (1.5 x: the Hermite's peak acceleration), or to turn to its angle
        const spinUp = (ax, w) => (Math.abs(w * bps - ax.v) / Math.max(1e-6, ax.amax)) * 1.5;
        const turnTo = (ax, to) => timeOf(ax, nearestTurn(to, ax.x) - ax.x);
        const tR = Math.max(spinUp(a.yaw, t.vyaw), spinUp(a.spin, t.vspin), t.vyaw ? 0 : turnTo(a.yaw, t.yaw), t.vspin ? 0 : turnTo(a.spin, t.spin));
        const turn = Math.max(tT, tX, tR);
        return rise ? [tY, turn] : lower ? [turn, tY] : [Math.max(tY, turn), 0];
      };
      let [tA, tB] = phaseTimes();
      let landK = tA + tB > 0 ? grid.nextBarPos(start + (tA + tB) * bps - 1e-9) : start;
      t = this.target(def, k, landK, this.tmp, true);
      [tA, tB] = phaseTimes();
      while (landK - start < (tA + tB) * bps - 1e-9) landK += 4;
      const split = tA + tB > 0 ? start + ((landK - start) * tA) / (tA + tB) : landK;
      rings.push({ k, start, split, land: landK, rise, lower, pos0: pos,
                   from: { y: a.y.x, tilt: a.tilt.x, yaw: a.yaw.x, spin: a.spin.x, axial: a.axial.x, vyaw: a.yaw.v / bps, vspin: a.spin.v / bps } });
      posLand = Math.max(posLand, landK);
    }
    this.key = key; this.def = def;
    this.move = { key, pos0: pos, posLand, rings };
    if (this.lands.length < 64) this.lands.push({ key, pos: +pos.toFixed(4), posLand, rings: rings.map((r) => ({ k: r.k, start: r.start, split: r.split, land: r.land })) });
    return { posLand, rings };
  }
  // One linear axis's reference (y, tilt, axial) in its window [p0, p1], in units per second: from -> to on the quintic
  // (dream) or on the S-curve stretched to the window (real: the machine glide).
  _glide(from, to, pos, p0, p1, bps, ax, out) {
    const span = p1 - p0;
    if (!(span > 0) || pos >= p1) { out.x = to; out.v = 0; out.a = 0; return out; }
    if (pos <= p0) { out.x = from; out.v = 0; out.a = 0; return out; }
    const u = (pos - p0) / span, dS = span / bps, D = to - from;
    if (this.mode === "real" && Math.abs(D) > 1e-9) {
      const plan = sCurveFit(D, dS, ax.vmax, ax.amax, ax.jmax), sg = D >= 0 ? 1 : -1, r = plan.T / dS;
      const c = sCurveAt(plan, u * plan.T, this.sc);
      out.x = from + sg * c.s; out.v = sg * c.v * r; out.a = sg * c.a * r * r;
    } else {
      out.x = from + D * quintic(u); out.v = (D * quinticD1(u)) / dS; out.a = (D * quinticD2(u)) / (dS * dS);
    }
    return out;
  }
  update(grid, tEval, dt) {
    const pos = grid.posAt(tEval), bps = 1000 / grid.period;
    const mv = this.move, g = this.g;
    for (let k = 0; k < this.n; k++) {
      const a = this.axes[k];
      const m = mv && mv.rings[k];
      if (m && pos < m.land) {
        const tl = this.target(this.def, k, m.land, this.tl);
        // lift before tilt: a rise moves y in [start, split] and the rest in [split, land]; a lowering the other way round
        const yWin = m.rise ? [m.start, m.split] : m.lower ? [m.split, m.land] : [m.start, m.land];
        const rWin = m.rise ? [m.split, m.land] : m.lower ? [m.start, m.split] : [m.start, m.land];
        this._glide(m.from.y, tl.y, pos, yWin[0], yWin[1], bps, a.y, g); a.y.step(g.x, g.v, g.a, dt);
        this._glide(m.from.tilt, tl.tilt, pos, rWin[0], rWin[1], bps, a.tilt, g); a.tilt.step(g.x, g.v, g.a, dt);
        this._glide(m.from.axial, tl.axial, pos, rWin[0], rWin[1], bps, a.axial, g); a.axial.step(g.x, g.v, g.a, dt);
        // the rotators: on at their own speed until the window opens, then a Hermite into the formation's angle and rate
        // (its turn chosen so the average speed over the window is the mean of the two speeds: no extra lap, no reversal)
        const p0 = rWin[0], span = m.land - p0;
        for (const [ax, f0, v0, to, w] of [[a.yaw, m.from.yaw, m.from.vyaw, tl.yaw, tl.vyaw], [a.spin, m.from.spin, m.from.vspin, tl.spin, tl.vspin]]) {
          if (pos < p0 || !(span > 0)) { ax.step(f0 + v0 * (pos - m.pos0), v0 * bps, 0, dt); continue; }
          const at0 = f0 + v0 * (p0 - m.pos0);
          const h = hermite(at0, v0 * span, nearestTurn(to, at0 + 0.5 * (v0 + w) * span), w * span, (pos - p0) / span, g);
          ax.step(h.x, (h.v / span) * bps, (h.a / (span * span)) * bps * bps, dt);
        }
      } else {
        // the formation itself (a landed rotator turns on, unwrapped: the target's turn nearest where it is)
        const t = this.target(this.def, k, pos);
        a.y.step(t.y, 0, 0, dt); a.tilt.step(t.tilt, 0, 0, dt); a.axial.step(t.axial, 0, 0, dt);
        a.yaw.step(nearestTurn(t.yaw, a.yaw.x), t.vyaw * bps, 0, dt);
        a.spin.step(nearestTurn(t.spin, a.spin.x), t.vspin * bps, 0, dt);
      }
      const p = this.poses[k];
      p.y = a.y.x; p.tilt = a.tilt.x; p.yaw = a.yaw.x; p.spin = a.spin.x; p.axial = a.axial.x;
    }
    if (mv && pos >= mv.posLand) this.move = null;
    return this.poses;
  }
}
