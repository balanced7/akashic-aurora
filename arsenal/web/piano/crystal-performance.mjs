// Shared, clock-driven performance state. No rendering or browser dependencies.
export const damp = (from, to, dt, tau) => to + (from - to) * Math.exp(-Math.max(0, dt) / tau);

export function createPerformance() {
  const state = { pressed: new Map(), sounding: new Map(), pedal: false, notes: [], chord: null };
  let serial = 0;
  function noteOn(midi, vel, t) {
    if (!Number.isInteger(midi) || midi < 21 || midi > 108) return;
    if (vel <= 0) return noteOff(midi, t);
    vel = Math.min(127, vel);
    const strike = ++serial;
    state.pressed.set(midi, { vel, t0: t, strike });
    state.sounding.set(midi, { vel, t0: t, held: true, pedal: false, tRelease: null, strike });
    state.notes.push({ midi, vel, t });
    if (state.notes.length > 128) state.notes.shift();
  }
  function noteOff(midi, t) {
    state.pressed.delete(midi);
    const e = state.sounding.get(midi);
    if (!e) return;
    e.held = false; e.pedal = state.pedal; e.tRelease = t;
    if (!state.pedal) state.sounding.delete(midi);
  }
  function pedal(on) {
    state.pedal = !!on;
    if (!on) for (const [m, e] of state.sounding) if (!e.held) state.sounding.delete(m);
  }
  function clear() {
    state.pressed.clear(); state.sounding.clear(); state.notes.length = 0;
    state.pedal = false; state.chord = null;
  }
  return { state, noteOn, noteOff, pedal, clear };
}

export function frameStats(intervals) {
  const clean = intervals.filter(v => Number.isFinite(v) && v > 0);
  if (!clean.length) return null;
  const sorted = [...clean].sort((a, b) => a - b);
  const mean = clean.reduce((a, b) => a + b, 0) / clean.length;
  return { frames: clean.length, fps: +(1000 / mean).toFixed(1),
    meanMs: +mean.toFixed(2), p95Ms: +sorted[Math.ceil(sorted.length * .95) - 1].toFixed(2),
    maxMs: +sorted.at(-1).toFixed(2), over16_9Pct: +(100 * clean.filter(v => v > 16.9).length / clean.length).toFixed(1) };
}
