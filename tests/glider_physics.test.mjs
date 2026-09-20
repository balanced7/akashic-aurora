// Node pins for arsenal/web/glider/physics.js -- the GLIDE FEEL core, RED-first.
// Zero dependencies:  node tests/glider_physics.test.mjs
//
// The whole game is the act of gliding, so the physics are pinned BEFORE the page exists. A
// point-mass glider in the vertical plane: lift = Cl*v^2 (Cl rises with angle of attack, then drops
// past the stall), drag = Cd*v^2 (Cd = parasitic + induced, Cd0 + K*Cl^2), gravity, and a thermal
// column (parabolic updraft profile). The numbers below are hand-computed from DEFAULTS; the glide
// RATIO and the stall/energy relationships are the load-bearing facts a wrong model would get wrong
// silently.

import {
  DEFAULTS, cdAt, clAt, gliderForces, simulate, step, thermalUpdraft,
} from "../arsenal/web/glider/physics.js";

let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  report.push(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (l, g, w) => check(l, JSON.stringify(g) === JSON.stringify(w), `got ${JSON.stringify(g)} want ${JSON.stringify(w)}`);
const near = (l, g, w, e = 1e-3) => check(l, Math.abs(g - w) <= e, `got ${g} want ${w} (+-${e})`);

// ------------------------------------------------------------- the lift curve is the model's spine
eq("clAt is linear below stall", [clAt(0), clAt(6), clAt(12)], [0.02, 0.116, 0.212]);
eq("...and it DROPS past the stall angle (that is what stall means)", clAt(15), 0.05);
check("stalled lift is less than peak lift", clAt(15) < clAt(12));

// ----------------------------------------------------------------- forces at a known state
// v=10, AoA=6 -> Cl=0.116, Cd=0.01+0.05*0.116^2=0.0106728 -> lift=11.6, drag=1.06728
near("lift = Cl*v^2", gliderForces(10, 6).lift, 11.6, 1e-3);
near("drag = Cd*v^2", gliderForces(10, 6).drag, 1.06728, 1e-3);
near("glide ratio = Cl/Cd at AoA 6", gliderForces(10, 6).glideRatio, 0.116 / 0.0106728, 1e-2);

// ------------------------------------------------------------- steady glide approaches Cl/Cd
// Equilibrium speed sqrt(g/Cl) ~ 9.2 m/s; glide slope Cd/Cl ~ 0.092, so distance/height ~ 10.87.
const level = simulate({ x: 0, y: 100, vx: 9.2, vy: 0 }, 6, 0.01, 6000);
const levelRatio = level.x / (100 - level.y);
check("a steady glide settles near Cl/Cd", levelRatio > 9 && levelRatio < 12.5, `ratio ${levelRatio.toFixed(2)}`);

// ----------------------------------------------------------------- stall makes the glide WORSE
const stalled = simulate({ x: 0, y: 100, vx: 9.2, vy: 0 }, 15, 0.01, 6000);
const stallRatio = stalled.x / (100 - stalled.y);
check("the stalled glide is much steeper", stallRatio > 4 && stallRatio < 6, `ratio ${stallRatio.toFixed(2)}`);
check("...and worse than the clean glide", stallRatio < levelRatio);

// ----------------------------------------------------------------- energy trade: flatter = faster
const flat = simulate({ x: 0, y: 100, vx: 9.2, vy: 0 }, 2, 0.01, 6000);
const vLevel = Math.hypot(level.vx, level.vy), vFlat = Math.hypot(flat.vx, flat.vy);
check("pitching flatter (lower AoA) trades height for speed", vFlat > vLevel,
  `flat ${vFlat.toFixed(2)} vs level ${vLevel.toFixed(2)}`);

// ------------------------------------------------------------- the SPEED envelope (Wipeout end)
// AoA 0 -> Cl=0.02 -> equilibrium speed sqrt(9.81/0.02) ~ 22 m/s. The same wing, same model, must
// span soar (~8 m/s in a thermal) to dive (~22+ m/s). "Speed feels incredible" is a lie if the model
// cannot actually go fast; this pin is the honesty check for that half of the promise.
const dive = simulate({ x: 0, y: 100, vx: 9.2, vy: 0 }, 0, 0.01, 6000);
const vDive = Math.hypot(dive.vx, dive.vy);
check("the same wing can DIVE fast (speed envelope, Wipeout end)", vDive > 20, `v ${vDive.toFixed(2)}`);

// ----------------------------------------------------------------- thermals
eq("a thermal peaks at its centre", thermalUpdraft(0, 0, { radius: 10, strength: 3 }), 3);
eq("...and is zero at the rim", thermalUpdraft(10, 0, { radius: 10, strength: 3 }), 0);
eq("...and zero outside", thermalUpdraft(11, 0, { radius: 10, strength: 3 }), 0);
const lift = simulate({ x: 0, y: 100, vx: 8.1, vy: 0 }, 8, 0.01, 4000,
  { updraft: (s) => thermalUpdraft(s.x - 16, 0, { radius: 30, strength: 6 }) });
check("riding a thermal GAINS altitude", lift.y > 100, `y_end ${lift.y.toFixed(1)}`);

// ------------------------------------------------------------- mechanical energy, no drag
// Lift is perpendicular to velocity, so it does no work; with CD0=K=0 energy is conserved, and the
// integrator must not leak it. That is the honesty test for the force model + integration.
const E = (s) => 0.5 * (s.vx * s.vx + s.vy * s.vy) + DEFAULTS.G * s.y;
const s0 = { x: 0, y: 100, vx: 9.2, vy: 0 };
const s1 = simulate(s0, 6, 0.001, 500, { p: { ...DEFAULTS, CD0: 0, K: 0 } });
const drift = Math.abs(E(s1) - E(s0)) / E(s0);
check("without drag, mechanical energy is conserved (integrator does not leak)", drift < 0.01,
  `drift ${(drift * 100).toFixed(3)}%`);

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
