// arsenal/web/glider/physics.js -- the GLIDE FEEL core: a point-mass glider in the vertical plane.
//
// WHY THIS EXISTS. The whole game is the act of gliding, so the feel-critical physics are pinned
// in Node before a single pixel is drawn. A point-mass glider is enough for feel: it is not about
// aerobatics, it is about whether diving trades height for speed, whether a thermal lifts you, and
// whether a stall is something you recover from instead of something that kills you.
//
// THE MODEL. Lift = Cl*v^2 (Cl rises linearly with angle of attack, then drops past the stall angle
// -- a stall is a drop in lift, nothing more); drag = Cd*v^2 with Cd = CD0 + K*Cl^2 (parasitic plus
// induced); gravity; and an optional updraft (thermals are a parabolic column: full strength at the
// centre, zero at the rim, zero outside).
//
// PARAMETERIZED ON PURPOSE. Daniel wants mid-air pickups that change the wing's configuration
// mid-flight. That is only a one-line change if the aerodynamics are data, not code -- so every
// constant lives in DEFAULTS and every function takes an optional `p` override. A pickup that morphs
// the wing swaps the params object; the physics does not change. Same seam the pins exercise.
//
// It is deliberately 2D (vertical plane). Banked turns and the third axis are a later layer over the
// same core -- turning is control-feel, not physics-truth, and it must not re-pin these facts.
export const DEFAULTS = {
  CL0: 0.02,          // lift coefficient at zero angle of attack
  CL_SLOPE: 0.016,    // per degree, linear below stall
  AOA_STALL: 12,      // degrees
  CL_STALLED: 0.05,   // lift coefficient past the stall (a drop, hence a stall)
  CD0: 0.01,          // parasitic drag
  K: 0.05,            // induced drag factor (Cd = CD0 + K*Cl^2)
  G: 9.81,            // m/s^2
};

/** Lift coefficient at an angle of attack. Linear below the stall angle, then a DROP -- a stall is
 *  exactly that drop, and the game must let a player fly into it and dive back out. */
export function clAt(aoa, p = DEFAULTS) {
  return aoa <= p.AOA_STALL ? p.CL0 + p.CL_SLOPE * aoa : p.CL_STALLED;
}

/** Drag coefficient for a given lift coefficient: parasitic plus induced. */
export function cdAt(cl, p = DEFAULTS) {
  return p.CD0 + p.K * cl * cl;
}

/** Aerodynamic accelerations at a speed and angle of attack, plus the glide ratio (Cl/Cd) -- the
 *  single number that says how far you travel for how far you fall. */
export function gliderForces(v, aoa, p = DEFAULTS) {
  const Cl = clAt(aoa, p);
  const Cd = cdAt(Cl, p);
  return { lift: Cl * v * v, drag: Cd * v * v, Cl, Cd, glideRatio: Cl / Cd };
}

/** Vertical airspeed of a thermal column at (dx,dy) relative to its centre. Parabolic: strength at
 *  the core, zero at the rim, zero outside. */
export function thermalUpdraft(dx, dy, t) {
  const d2 = dx * dx + dy * dy;
  const r = t.radius;
  if (d2 >= r * r) return 0;
  return t.strength * Math.max(0, 1 - d2 / (r * r));
}

/** One physics step. state = {x, y, vx, vy} (+y up, GROUND frame), aoa in degrees, dt in seconds.
 *  opts = { p (aerodynamic params), g (gravity), updraft (number m/s, or a fn(state)->number) }.
 *
 *  A thermal is a WIND, not a force: it is a vertical airmass velocity, so it enters through the
 *  AIR-relative velocity (the aerodynamics see the glider's motion THROUGH the air), while position
 *  advances by GROUND velocity (air-relative velocity plus the wind). That distinction is the whole
 *  of "the glider climbs in an updraft": its air-relative sink stays the same, and the rising air
 *  carries it up relative to the ground. */
export function step(state, aoa, dt, opts = {}) {
  const p = opts.p || DEFAULTS;
  const g = opts.g ?? p.G;
  const W = typeof opts.updraft === "function" ? opts.updraft(state) : (opts.updraft || 0);

  const vax = state.vx;              // air-relative horizontal velocity
  const vay = state.vy - W;          // air-relative vertical velocity (air rises at W)
  const va = Math.hypot(vax, vay);
  if (va < 1e-9) {
    // no airspeed: no lift, no drag -- free fall, plus the wind carrying it
    const vy = state.vy - g * dt + W;
    return { x: state.x, y: state.y + vy * dt, vx: 0, vy };
  }
  const f = gliderForces(va, aoa, p);
  const ux = vax / va, uy = vay / va;            // velocity direction through the air
  // drag opposite air-velocity; lift perpendicular, on the "up" side of the flight path
  const ax = -f.drag * ux - f.lift * uy;
  const ay = -f.drag * uy + f.lift * ux - g;
  const vax2 = vax + ax * dt;
  const vay2 = vay + ay * dt;
  const vx = vax2;                                // ground velocity = air-relative + wind
  const vy = vay2 + W;
  return {
    x: state.x + vx * dt,
    y: state.y + vy * dt,
    vx, vy,
  };
}

/** Run `steps` frames and return the final state. For the pins and for the flight recorder. */
export function simulate(start, aoa, dt, steps, opts = {}) {
  let s = { ...start };
  for (let i = 0; i < steps; i++) s = step(s, aoa, dt, opts);
  return s;
}
