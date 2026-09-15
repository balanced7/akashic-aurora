// The jam tempo map: bar <-> epoch <-> pass <-> slot, the landing rule and the hand-off time (jam-spec 9.1, 9.3, 9.4).
//
// The page's twin of arsenal/jam/tempomap.py. Every export does the same arithmetic in the same order as its
// snake_case twin there, and both run tests/fixtures/jam/tempomap_cases.json (node tests/jam_tempomap.test.mjs;
// tests/test_arsenal_jam_schemas.py), agreeing with it to 0.001 ms. Pure: no DOM, and nothing here reads a clock.
//
// A run's segments are [{from_bar, bpm, epoch_ms, def_version, def_from_bar}] in the meter m = beats_per_bar, ordered
// by from_bar. The first segment starts the count-in at bar -count_in; bar 0 is the loop's first downbeat.
//
//   barMs(bpm, m)       = m * 60000 / bpm
//   tEpoch(bar, x)      = s.epoch_ms + (bar - s.from_bar) * barMs(s.bpm, m) + x * 60000 / s.bpm    s = segmentAt(bar)
//   new segment at B    = {from_bar: B, bpm: new, epoch_ms: tEpoch(B) under the old segment}      (never re-rounded)
//   pass(bar)           = floor((bar - s.def_from_bar) * m / cycle_beats)
//   cycleBeat(bar, x)   = ((bar - s.def_from_bar) * m + x) mod cycle_beats       (floor mod: never negative)
//   slot                = the last slot with at_beat <= cycleBeat; null while counting in (bar < def_from_bar)
//
// Epoch -> position (DATA 6.3): s = the last segment with epoch_ms <= E; beats = (E - s.epoch_ms) * s.bpm / 60000;
// bar = s.from_bar + floor((beats + EPS_BEATS) / m). Bars and epochs before the first segment extrapolate it.
//
// Tolerances: an epoch in ms near 1.9e12 is a double with a resolution of about 0.24 microseconds, so two instants
// closer than EPS_MS (1 microsecond) are the same instant, and a position within EPS_BEATS (1e-5 beat) before a bar,
// beat or slot line is on that line. Both twins and the fixture's oracle use these values.
//
// A def here is anything with {cycle_beats, slots: [{at_beat, beats}, ...]}. `defs` is one def, used for every
// def_version, or an object def_version -> def.
//
// Page time: perf = epoch - offset, offset = Date.now() - performance.now(). Session time: t_ms = perf - t0_perf_ms.

export const EPS_BEATS = 1e-5;
export const EPS_MS = 1e-3;
export const CHANGE_LEAD_MS = 250;     // a change lands at least 1 beat + 250 ms after the server has it (9.4, C3)
export const HANDOFF_MARGIN_MS = 150;  // bar n goes to the player 1 beat + 150 ms before it (9.3)
export const AT_LINES = Object.freeze(["now", "beat", "bar", "pass"]);
const MAX_STEPS = 100000;

export class TempoMapError extends Error {
  constructor(message) { super(message); this.name = "TempoMapError"; }
}

export function beatMs(bpm) { return 60000 / bpm; }

export function barMs(bpm, beatsPerBar) { return beatsPerBar * 60000 / bpm; }

function check(segments, m) {
  if (!Array.isArray(segments) || segments.length === 0) throw new TempoMapError("a tempo map needs at least one segment");
  if (!Number.isInteger(m) || m < 1) throw new TempoMapError(`beats_per_bar must be a positive integer (got ${m})`);
}

// The last segment with from_bar <= bar (the first segment for a bar before it).
export function segmentAt(segments, bar) {
  let chosen = segments[0];
  for (const s of segments) {
    if (s.from_bar <= bar) chosen = s;
    else break;
  }
  return chosen;
}

// The last segment with epoch_ms <= E (within EPS_MS; the first segment for a time before it).
export function segmentAtEpoch(segments, epochMs) {
  let chosen = segments[0];
  for (const s of segments) {
    if (s.epoch_ms <= epochMs + EPS_MS) chosen = s;
    else break;
  }
  return chosen;
}

// The epoch ms of beat position `beat` inside bar `bar`.
export function tEpoch(segments, m, bar, beat = 0) {
  check(segments, m);
  const s = segmentAt(segments, bar);
  return s.epoch_ms + (bar - s.from_bar) * barMs(s.bpm, m) + beat * 60000 / s.bpm;
}

// {bar, beat}: the bar sounding at epochMs and the beat position inside it (0 <= beat < m).
export function barAt(segments, m, epochMs) {
  check(segments, m);
  const s = segmentAtEpoch(segments, epochMs);
  const beats = (epochMs - s.epoch_ms) * s.bpm / 60000;
  const k = Math.floor((beats + EPS_BEATS) / m);
  let beat = beats - k * m;
  if (beat < 0) beat = 0;
  return { bar: s.from_bar + k, beat };
}

function defFor(defs, version) {
  if (defs && typeof defs === "object" && defs.cycle_beats !== undefined) return defs;
  if (defs && typeof defs === "object") {
    const found = defs[version];
    if (found != null) return found;
    throw new TempoMapError(`no def for def_version ${version}`);
  }
  throw new TempoMapError("defs must be a def ({cycle_beats, slots}) or an object def_version -> def");
}

function cycleOf(d) {
  const c = d.cycle_beats;
  if (typeof c !== "number" || !(c > 0)) throw new TempoMapError(`cycle_beats must be a positive number (got ${c})`);
  return c;
}

// The pass bar `bar` belongs to: 0 for the first pass of its def, negative while counting in.
export function passOf(segments, m, bar, defs) {
  check(segments, m);
  const s = segmentAt(segments, bar);
  const c = cycleOf(defFor(defs, s.def_version));
  return Math.floor((bar - s.def_from_bar) * m / c);
}

// The beat position inside the def's cycle, 0 <= cycleBeat < cycle_beats.
export function cycleBeat(segments, m, bar, beat, defs) {
  check(segments, m);
  const s = segmentAt(segments, bar);
  const c = cycleOf(defFor(defs, s.def_version));
  const v = (bar - s.def_from_bar) * m + beat;
  let r = v - Math.floor(v / c) * c;
  if (r >= c) r = 0;
  return r;
}

// The index of the last slot with at_beat <= cycleBeat (slots are ordered by at_beat), or null before the first.
export function slotAt(slots, cycleBeatValue) {
  let found = null;
  for (let i = 0; i < slots.length; i++) {
    if (slots[i].at_beat <= cycleBeatValue + EPS_BEATS) found = i;
    else break;
  }
  return found;
}

// Everything the strip and jam status show for one instant: {bar, beat, pass, cycle_beat, slot, rest, counting_in,
// def_version, bpm}. rest is true in a rest gap, before the first slot, and while counting in.
export function position(segments, m, epochMs, defs) {
  const at = barAt(segments, m, epochMs);
  const { bar, beat } = at;
  const s = segmentAt(segments, bar);
  const d = defFor(defs, s.def_version);
  const c = cycleOf(d);
  const p = Math.floor((bar - s.def_from_bar) * m / c);
  const cb = cycleBeat(segments, m, bar, beat, defs);
  const countingIn = bar < s.def_from_bar;
  const slots = d.slots || [];
  const slot = countingIn ? null : slotAt(slots, cb);
  const rest = slot === null ? true : cb + EPS_BEATS >= slots[slot].at_beat + slots[slot].beats;
  return { bar, beat, pass: p, cycle_beat: cb, slot, rest, counting_in: countingIn, def_version: s.def_version,
    bpm: s.bpm };
}

// A run's first segment: the count-in starts at startEpochMs, so bar 0 is countIn bars later (9.2).
export function firstSegment(startEpochMs, bpm, countIn = 1, defVersion = 1) {
  return { from_bar: -countIn, bpm, epoch_ms: startEpochMs, def_version: defVersion, def_from_bar: 0 };
}

// A new array with a change at bar `bar`: its epoch is tEpoch(bar) under the segment in effect there. Options left
// undefined or null keep the last segment's; a new def_version starts its cycle at `bar` unless def_from_bar says
// otherwise. A change on the last segment's own bar replaces that segment. The input is not modified.
export function addSegment(segments, m, bar, { bpm = null, def_version = null, def_from_bar = null } = {}) {
  check(segments, m);
  const last = segments[segments.length - 1];
  if (bar < last.from_bar) {
    throw new TempoMapError(`a change at bar ${bar} is before the last segment's bar ${last.from_bar}`);
  }
  const version = def_version == null ? last.def_version : def_version;
  let fromBar = def_from_bar;
  if (fromBar == null) fromBar = version === last.def_version ? last.def_from_bar : bar;
  const next = { from_bar: bar, bpm: bpm == null ? last.bpm : bpm, epoch_ms: tEpoch(segments, m, bar),
    def_version: version, def_from_bar: fromBar };
  const out = segments.map((s) => ({ ...s }));
  if (bar === last.from_bar) out[out.length - 1] = next;
  else out.push(next);
  return out;
}

function isPassTop(segments, m, bar, defs) {
  const s = segmentAt(segments, bar);
  if (bar < s.def_from_bar) return false;
  const c = cycleOf(defFor(defs, s.def_version));
  return ((bar - s.def_from_bar) * m) % c === 0;
}

// The landing rule (C3, 9.4): {bar, beat, epoch_ms} where a change received at receivedEpochMs takes effect. now: at
// once. beat, bar, pass: the first beat line, bar line or pass top (needs defs) at least one beat, at the tempo
// sounding on receipt, plus leadMs after it.
export function nextLine(segments, m, receivedEpochMs, at = "bar", defs = null, leadMs = CHANGE_LEAD_MS) {
  if (!AT_LINES.includes(at)) throw new TempoMapError(`at must be one of ${AT_LINES.join(", ")} (got ${at})`);
  const pos = barAt(segments, m, receivedEpochMs);
  if (at === "now") return { bar: pos.bar, beat: pos.beat, epoch_ms: receivedEpochMs };
  if (at === "pass" && defs == null) throw new TempoMapError("at pass needs the def (its cycle_beats)");
  const need = 60000 / segmentAtEpoch(segments, receivedEpochMs).bpm + leadMs;
  let bar = pos.bar;
  if (at === "beat") {
    let k = Math.floor(pos.beat);
    for (let step = 0; step < MAX_STEPS; step++) {
      const e = tEpoch(segments, m, bar, k);
      if (e - receivedEpochMs >= need - EPS_MS) return { bar, beat: k, epoch_ms: e };
      k += 1;
      if (k >= m) { k = 0; bar += 1; }
    }
  } else {
    for (let step = 0; step < MAX_STEPS; step++) {
      const e = tEpoch(segments, m, bar);
      if (e - receivedEpochMs >= need - EPS_MS && (at === "bar" || isPassTop(segments, m, bar, defs))) {
        return { bar, beat: 0, epoch_ms: e };
      }
      bar += 1;
    }
  }
  throw new TempoMapError(`no ${at} line within ${MAX_STEPS} steps`);
}

// H(n) (9.3): when bar n, with its pickups on bar n-1's last beat, goes to the player. One beat is measured at bar
// n-1's tempo, where the pickups sit, so a tempo change at bar n still leaves marginMs before the first pickup.
export function handoffEpoch(segments, m, bar, marginMs = HANDOFF_MARGIN_MS) {
  return tEpoch(segments, m, bar) - (60000 / segmentAt(segments, bar - 1).bpm + marginMs);
}

// Session t_ms of a bar position from one clock pair, extended by the map (11.2). At L1 the anchor is the ack:
// {bar_epoch_ms, perf_ms, t0_perf_ms: ack.log.t0_perf_ms}.
export function sessionTms(segments, m, bar, beat, anchor) {
  return anchor.perf_ms - anchor.t0_perf_ms + (tEpoch(segments, m, bar, beat) - anchor.bar_epoch_ms);
}

// Page time of an epoch, with offset = Date.now() - performance.now() (9.1).
export function perfOf(epochMs, offsetMs) { return epochMs - offsetMs; }

// The page's clock offset from paired reads [[wall_ms, perf_ms], ...]: the median of wall - perf (9.1 takes 5).
export function medianOffset(pairs) {
  if (!Array.isArray(pairs) || pairs.length === 0) {
    throw new TempoMapError("medianOffset needs at least one [wall_ms, perf_ms] pair");
  }
  const diffs = pairs.map(([w, p]) => w - p).sort((a, b) => a - b);
  const mid = Math.floor(diffs.length / 2);
  return diffs.length % 2 ? diffs[mid] : (diffs[mid - 1] + diffs[mid]) / 2;
}
