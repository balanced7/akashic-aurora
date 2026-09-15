// Musical gestures drive an artistic environment; these are not emotion classifications.
export const clamp = (x, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, x));
export const approach = (a, b, tau, dt) => a + (b - a) * (1 - Math.exp(-dt / Math.max(.001, tau)));
export const VOICE_CAPACITY = 256;
export const VISUAL_TAIL = 10;
const pcOf = root => root ? (([0, 2, 4, 5, 7, 9, 11][root.letter] + root.acc) % 12 + 12) % 12 : null;

export function harmonicColour(info) {
  const suffix = info?.suffix || '';
  const pcs = [...new Set((info?.notes || []).map(n => n.midi % 12))];
  let close = 0;
  for (const pc of pcs) if (pcs.includes((pc + 1) % 12)) close++;
  return { root: pcOf(info?.root), minor: /^m(?!aj)/.test(suffix) ? 1 : 0,
    air: /sus|#11|add9|maj9/.test(suffix) ? 1 : .2,
    tension: clamp(close / 4 + (/dim|aug|b9|#9/.test(suffix) ? .4 : 0)),
    dominant: /^(7|9|11|13)/.test(suffix), name: info?.name || '' };
}

// A slow, optional art direction. Four seconds of a gesture, fourteen between worlds.
export function createWorldJourney() {
  let candidate='',since=0,lastChange=-Infinity;
  return (state,t,current) => {
    if (!state.density) {candidate='';return current;}
    const desired=state.calm>.38?'moon':state.tension>.28?'rain':state.energy>.76?'city':state.air>.6?'winter':state.minor>.55?'nebula':'ember';
    if(desired!==candidate){candidate=desired;since=t;}
    if(desired!==current && t-since>=4 && t-lastChange>=14){lastChange=t;return desired;}
    return current;
  };
}

export function createGestureModel() {
  const notes = new Map(), impacts = [], voices = Array(VOICE_CAPACITY).fill(null);
  // Per-key height, vertical speed, light and periodic emission phase continue through retriggers.
  const keyMotion = new Float32Array(88 * 4);
  const state = { energy: 0, impact: 0, calm: 0, tension: 0, air: .2, minor: 0,
    pedal: false, cadence: 0, density: 0, centroid: 60, name: '', chordChanges: 0,
    dryStaccato: 0, suspendedStaccato: 0, strikes: 0, visualOverflow: 0,
    visualDensity: 0, force: 0, presence: 0 };
  let group = null, candidate = '', candidateAt = 0, settled = null;
  function finishGroup() {
    if (!group) return;
    const mean = group.vel / group.notes.length / 127;
    const unique = new Set(group.notes.map(n => n % 12)).size;
    const strength = clamp(mean ** 2 * Math.sqrt(unique) * .62, 0, 1.8);
    impacts.push({ time: group.at, notes: group.notes, strength, chord: unique >= 3 });
    if (impacts.length > 24) impacts.shift();
    state.impact = Math.max(state.impact, strength);
    group = null;
  }
  return {
    notes, voices, keyMotion, impacts, state,
    noteOn(m, vel, t) {
      if (m < 21 || m > 108 || !Number.isFinite(t)) return;
      vel = clamp(vel, 1, 127);
      const previous = notes.get(m);
      // Close the previous strike's history without touching the persistent GPU flow.
      if (previous) { previous.held = false; if (previous.end === null) previous.end = t; }
      const n = { midi: m, velocity: vel, at: t, released: null, end: null, held: true, style: 0 };
      notes.set(m, n);
      const slot = voices.findIndex(v => !v || (v.end !== null && t - v.end > VISUAL_TAIL));
      if (slot >= 0) voices[slot] = n;
      else state.visualOverflow++; // History is bounded; water, keys and GPU flow still respond.
      keyMotion[(m - 21) * 4 + 1] += (vel / 127) ** 2 * 3;
      if (group && t - group.at > .07) finishGroup();
      if (!group) group = { at: t, notes: [], vel: 0 };
      group.notes.push(m); group.vel += vel;
      state.strikes++;
    },
    noteOff(m, t, pedal = state.pedal) {
      const n = notes.get(m);
      if (!n || !n.held) return;
      n.held = false; n.released = t;
      if (m >= 72 && t - n.at <= .24) {
        n.style = pedal ? 2 : 1;
        if (pedal) state.suspendedStaccato++; else state.dryStaccato++;
      }
      if (!pedal) n.end = t;
    },
    pedal(down, t) {
      state.pedal = down;
      if (!down) for (const n of [...notes.values(), ...voices]) if (n && !n.held && n.end === null) n.end = t;
    },
    clear(t) {
      for (const n of [...notes.values(), ...voices]) if (n) { n.held = false; if (n.end === null) n.end = t; }
      group = null; impacts.length = 0; state.pedal = false; state.impact = 0;
    },
    update(dt, t, info) {
      dt = clamp(dt, 0, .1);
      if (group && t - group.at >= .07) finishGroup();
      let sum = 0, gentle = 0, count = 0, weighted = 0;
      for (const [m, n] of notes) {
        if (n.end !== null && t - n.end > 12) { notes.delete(m); continue; }
        if (n.end !== null) continue;
        const v = n.velocity / 127;
        sum += v * v; count++; weighted += m;
        gentle += (1 - v) * clamp((t - n.at) / 3);
      }
      let visualDensity = 0;
      for (let i = 0; i < voices.length; i++) {
        const n = voices[i]; if (!n) continue;
        if (n.end !== null && t - n.end > VISUAL_TAIL) { voices[i] = null; continue; }
        visualDensity += n.end === null ? 1 : Math.exp(-(t - n.end) * .65);
      }
      state.visualDensity = visualDensity;
      // A damped spring, integrated in small steps, carries architectural momentum.
      for (let i = 0; i < 88; i++) {
        const n = notes.get(i + 21), active = n && n.end === null;
        const v = active ? n.velocity / 127 : 0, o = i * 4;
        const target = active ? 3 + v * v * 31 : 0;
        const steps = Math.max(1, Math.ceil(dt * 120)), h = dt / steps;
        for (let j = 0; j < steps; j++) {
          keyMotion[o + 1] += (25 * (target - keyMotion[o]) - 9 * keyMotion[o + 1]) * h;
          keyMotion[o] = Math.max(0, keyMotion[o] + keyMotion[o + 1] * h);
        }
        keyMotion[o + 2] = approach(keyMotion[o + 2], active ? .25 + v * .75 : 0, active ? .16 : .9, dt);
        // An integrated emission phase never restarts when velocity or articulation changes.
        keyMotion[o + 3] = (keyMotion[o + 3] + dt * (.6 + v * v * 1.8)) % 1;
      }
      const h = harmonicColour(info);
      if (h.name !== candidate) { candidate = h.name; candidateAt = t; }
      if (h.name && t - candidateAt > .3 && h.name !== state.name) {
        if (settled?.dominant && h.root !== null && (settled.root - h.root + 12) % 12 === 7) state.cadence = 1;
        settled = h; state.name = h.name; state.chordChanges++;
      }
      const target = settled || h;
      state.energy = approach(state.energy, clamp(Math.sqrt(sum) / 2.5), .3, dt);
      const force = count ? sum / count : 0;
      state.force = approach(state.force, force, force > state.force ? .16 : .9, dt);
      state.presence = approach(state.presence, count ? 1 : 0, count ? .3 : 2.2, dt);
      state.calm = approach(state.calm, count ? gentle / count : 0, 1.5, dt);
      state.density = count;
      state.centroid = approach(state.centroid, count ? weighted / count : 60, .7, dt);
      state.minor = approach(state.minor, target.minor, 3.5, dt);
      state.air = approach(state.air, target.air, 2.5, dt);
      state.tension = approach(state.tension, count ? target.tension : 0, 2.2, dt);
      state.impact *= Math.exp(-dt / .55);
      state.cadence *= Math.exp(-dt / 1.8);
      while (impacts.length && t - impacts[0].time > 6) impacts.shift();
      return state;
    },
  };
}
