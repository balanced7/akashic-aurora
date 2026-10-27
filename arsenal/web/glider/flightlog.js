// arsenal/web/glider/flightlog.js -- the FEEL-PROXY report, pure and testable in Node.
//
// The glide-feel brief pre-registered measurable proxies so the numbers say "good" honestly.
// This module turns a recorded flight (samples of t, distance, altitude, speed, AoA, thermal
// membership) into that report. The page records; this judges; the pins hold the judging.
//
// A sample: { t, x, y, v, aoa, inThermal }. Units: seconds, meters, meters, m/s, degrees.

const REVERSAL_MIN = 0.25;   // degrees: below this, an AoA wiggle is noise, not oscillation

/** One number per flight for each pre-registered feel proxy. */
export function report(samples, { stallAoa = 12 } = {}) {
  if (!Array.isArray(samples) || samples.length === 0) {
    return {
      duration: 0, minSpeed: 0, maxSpeed: 0, pitchReversals: 0,
      diveAccel: 0, climbCost: 0, thermalGain: 0,
      stallEntered: false, stallRecovered: false, recoverable: false,
    };
  }

  const t0 = samples[0].t;
  const t1 = samples[samples.length - 1].t;

  // ---- pitch oscillation: reversals of the AoA derivative, above the noise floor
  let pitchReversals = 0;
  let lastSlope = 0;
  for (let i = 1; i < samples.length; i++) {
    const d = samples[i].aoa - samples[i - 1].aoa;
    if (Math.abs(d) < REVERSAL_MIN) continue;
    const slope = d > 0 ? 1 : -1;
    if (lastSlope !== 0 && slope !== lastSlope) pitchReversals++;
    lastSlope = slope;
  }

  // ---- energy trade: mean speed change inside descent segments vs climb segments
  // A segment is a run of samples with the same altitude direction; the speed change is
  // measured from its first sample to its last, then averaged per direction.
  let diveSum = 0, diveSegs = 0, climbSum = 0, climbSegs = 0;
  let segStart = 0;
  for (let i = 1; i <= samples.length; i++) {
    const end = i === samples.length;
    const dy = end ? 0 : samples[i].y - samples[i - 1].y;
    if (!end && Math.abs(dy) < 1e-3) continue;      // level flight is neither trade
    if (end || (segStart < i - 1 && Math.sign(samples[i - 1].y - samples[segStart].y) !== Math.sign(dy))) {
      const from = samples[segStart], to = samples[i - 1];
      const dv = to.v - from.v, dySeg = to.y - from.y;
      if (dySeg < -1e-3) { diveSum += dv; diveSegs++; }
      else if (dySeg > 1e-3) { climbSum += dv; climbSegs++; }
      segStart = i;
    }
  }

  // ---- thermal ride: altitude gained while inside the updraft column
  let thermalGain = 0;
  let thermalLow = null;
  let inside = false;
  for (const s of samples) {
    if (s.inThermal) {
      if (!inside) { inside = true; thermalLow = s.y; }
      thermalGain = Math.max(thermalGain, s.y - thermalLow);
    } else {
      inside = false;
    }
  }

  // ---- stall: entered past the stall angle, then pulled back under it
  let stallEntered = false, stallRecovered = false;
  for (const s of samples) {
    if (s.aoa > stallAoa) stallEntered = true;
    else if (stallEntered) { stallRecovered = true; break; }
  }

  // ---- the speed envelope: the observed extremes
  let minSpeed = Infinity, maxSpeed = -Infinity;
  for (const s of samples) {
    if (s.v < minSpeed) minSpeed = s.v;
    if (s.v > maxSpeed) maxSpeed = s.v;
  }
  if (!Number.isFinite(minSpeed)) minSpeed = 0;
  if (!Number.isFinite(maxSpeed)) maxSpeed = 0;

  return {
    duration: t1 - t0,
    minSpeed,
    maxSpeed,
    pitchReversals,
    diveAccel: diveSegs ? diveSum / diveSegs : 0,
    climbCost: climbSegs ? climbSum / climbSegs : 0,
    thermalGain,
    stallEntered,
    stallRecovered,
    recoverable: stallEntered && stallRecovered,
  };
}
