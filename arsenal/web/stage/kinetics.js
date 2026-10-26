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

export const KINETICS_API = "arsenal.stage-kinetics/v1";
const DEG = Math.PI / 180;
const TAU = Math.PI * 2;

export const MODES = Object.freeze({
  real: { vmax: 0.5, amax: 0.4, jmax: 2.0, roll: 50 },
  dream: { vmax: 1.5, amax: 1.2, jmax: 6.0, roll: 180 },
});

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
  // Start a time-priority move to formation `name`, landing on the next bar (or phrase) line it can make.
  land(name, params, grid, nowMs, { land = "bar" } = {}) {
    const pos = grid.posAt(nowMs);
    const fitted = this.fit(name, params || {}, grid.bpm);
    // the slowest axis's minimum S-curve time to reach the formation as it will be at landing position p
    const tgt = [0, 0];
    const needS = (p) => {
      let T = 0;
      for (let i = 0; i < this.n; i++) {
        formationTarget(name, fitted, i, this.n, p, this.tmp);
        this.hoists(this.tmp.y, this.tmp.roll, tgt);
        for (let s = 0; s < 2; s++) {
          const ax = this.axes[i * 2 + s];
          T = Math.max(T, quinticTime(tgt[s] - ax.x, ax.vmax, ax.amax, ax.jmax));
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
    this.move = { name, params: fitted, pos0: pos, posLand, from: this.axes.map((a) => a.x), tMinS: T };
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
            ref = x0 + (land - x0) * quintic(u);
            rv = (land - x0) * quinticD1(u) / dS;
            ra = (land - x0) * quinticD2(u) / (dS * dS);
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
