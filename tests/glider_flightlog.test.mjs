// Node pins for arsenal/web/glider/flightlog.js -- the FEEL-PROXY report, RED-first.
// Zero dependencies:  node tests/glider_flightlog.test.mjs
//
// The glide-feel brief pre-registered measurable proxies so the numbers say "good" honestly:
//   1. stable and controllable  (no divergent pitch oscillation)
//   2. energy trade works       (dive -> speed, climb -> spend)
//   3. thermal ride             (altitude GAINS inside the updraft column)
//   4. stall exists but is recoverable
//   5. speed envelope           (soar <-> dive on the same wing)
// These pins hold the report() that computes them from a recorded flight, so a playable page
// can print the same numbers Daniel's thirty-second verdict is judged against.

import { report } from "../arsenal/web/glider/flightlog.js";

let pass = 0, fail = 0;
const problems = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  problems.push(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const near = (l, g, w, e = 1e-6) => check(l, Math.abs(g - w) <= e, `got ${g} want ${w} (+-${e})`);

const sample = (t, x, y, v, aoa, inThermal) => ({ t, x, y, v, aoa, inThermal: !!inThermal });
const seq = (n, fn) => Array.from({ length: n }, (_, i) => fn(i));

// ------------------------------------------------------------- a steady glide oscillates nothing
{
  const s = seq(120, (i) => sample(i * 0.1, i, 100, 10, 6, false));
  const r = report(s);
  check("a steady glide has no pitch oscillations", r.pitchReversals === 0, `got ${r.pitchReversals}`);
  check("...and no energy-trade segments to report", r.diveAccel === 0 && r.climbCost === 0,
    `dive ${r.diveAccel} climb ${r.climbCost}`);
}

// ------------------------------------------------------------- energy trade: dive buys speed
{
  const s = seq(101, (i) => sample(i * 0.1, i, 100 - i * 0.5, 8 + i * 0.14, 0, false));
  const r = report(s);
  near("a dive accelerates (height traded for speed)", r.diveAccel, 14, 1e-3);
  check("a pure dive spends nothing on climb", r.climbCost === 0, `got ${r.climbCost}`);
}

// ------------------------------------------------------------- energy trade: climb spends speed
{
  const s = seq(101, (i) => sample(i * 0.1, i, 50 + i * 0.3, 20 - i * 0.11, 8, false));
  const r = report(s);
  near("a climb costs speed", r.climbCost, -11, 1e-3);
  check("a pure climb buys nothing on dive", r.diveAccel === 0, `got ${r.diveAccel}`);
}

// ------------------------------------------------------------- thermal ride gains altitude
{
  const s = [
    ...seq(100, (i) => sample(i * 0.1, i, 100, 10, 8, false)),
    ...seq(101, (i) => sample(10 + i * 0.1, 100 + i, 100 + i * 0.3, 10, 8, true)),
  ];
  const r = report(s);
  near("riding a thermal GAINS altitude", r.thermalGain, 30, 1e-3);
}

// ------------------------------------------------------------- stall exists AND is recoverable
{
  const s = [sample(0, 0, 100, 9, 6, false), sample(1, 1, 99, 8, 13, false),
             sample(2, 2, 97, 7, 15, false), sample(3, 3, 96, 8, 8, false)];
  const r = report(s, { stallAoa: 12 });
  check("a flight that crosses the stall angle is recorded as stalled", r.stallEntered === true);
  check("...and pulling back under it is recorded as recovery", r.stallRecovered === true);
  check("stall + recovery = recoverable", r.recoverable === true);
  const clean = report(seq(60, (i) => sample(i * 0.1, i, 100, 10, 6, false)), { stallAoa: 12 });
  check("a clean flight never enters the stall book", clean.stallEntered === false &&
    clean.stallRecovered === false && clean.recoverable === false);
}

// ------------------------------------------------------------- pitch oscillation is counted
{
  // 8 -> 10 -> 8 -> 10 deg: two reversals, not noise.
  const s = [sample(0, 0, 100, 10, 8, false), sample(1, 1, 99, 10, 10, false),
             sample(2, 2, 98, 10, 8, false), sample(3, 3, 97, 10, 10, false)];
  check("pitch oscillation reversals are counted", report(s).pitchReversals >= 2,
    `got ${report(s).pitchReversals}`);
  const tiny = [sample(0, 0, 100, 10, 8, false), sample(1, 1, 99, 10, 8.1, false)];
  check("sub-threshold wiggle is not an oscillation", report(tiny).pitchReversals === 0,
    `got ${report(tiny).pitchReversals}`);
}

// ------------------------------------------------------------- the speed envelope
{
  const s = seq(200, (i) => sample(i * 0.1, i, 100 - Math.sin(i / 20) * 10, 9 + 13 * (0.5 + 0.5 * Math.sin(i / 20)), 6, false));
  const r = report(s);
  check("the envelope reports the observed extremes", r.minSpeed < 10 && r.maxSpeed > 21,
    `min ${r.minSpeed.toFixed(2)} max ${r.maxSpeed.toFixed(2)}`);
}

console.log(problems.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
