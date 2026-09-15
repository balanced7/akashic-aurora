// Standard MIDI files for live sheet music: arsenal/web/piano/score/midi.js (pure ES module: no DOM, no clock).
// Stage T10 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (section 7.4), amended by
// plan-amendments.md C5 (CC64 crossings only) and C19 (performance.mid is SMF type 0).
//
//   performanceMid(events, { t0_ms, stats })  -> Uint8Array   SMF type 0, PPQ 500, tempo 500,000 us per quarter, so 1 tick
//                                                             = 1 ms: every logged on and off at t_ms - t0_ms, CC64 127 at
//                                                             each pedal down-crossing and 0 at each up-crossing (LR9b)
//   quantizedMid(score, { stats })            -> Uint8Array   SMF type 1, PPQ 480: track 0 the tempo map (a tempo event per
//                                                             tactus beat from the bars' beat times), track 1 the upper
//                                                             staff, track 2 the lower staff; notes on the grid (LR9c)
//   measureBeatDurations(measures)            -> [[ms per tactus beat]] per measure (shared with musicxml.js)
//
// performance.mid writes the log as logged: an on for a pitch already sounding and an off with no open on are written
// unchanged (nothing is dropped or invented at their times). Only pitches still open after the last event get an off at
// the last event's tick (stats.endOffs). A pedal event that does not change the pedal state is not a crossing and is not
// written (stats.pedalNonCrossings). At one tick the order is off, pedal, on (the log's replay order). A note-on velocity
// of 0 would read as an off, so it is written as 1 (stats.velClamped). Non-integer times are rounded (stats.rounded; the
// practice log is integer ms).
// quantizedMid reads note pieces from the measures (a note's first piece gives its onset, its tied pieces its length), so
// it holds exactly the notes musicxml.js writes. Measure ticks are cumulative from the first measure (measure.startTick
// when every measure has one and they are contiguous, else the running sum of barTicks). Score ticks (24 per quarter) x 20
// = PPQ 480 ticks.

export const MIDI_API = "arsenal.piano.score.midi/v0";
export const PERFORMANCE_PPQ = 500;
export const QUANTIZED_PPQ = 480;
const US_PER_QUARTER_PERF = 500000;
const EVENT_ORDER = { off: 0, pedal: 1, on: 2 };

// -------------------------------------------------------------------------------------------- bytes ---
function vlq(n) {
  if (!(n >= 0) || !Number.isInteger(n) || n > 0x0fffffff) throw new RangeError(`midi.js: delta ${n} is not a 28-bit integer`);
  const out = [n & 0x7f];
  while ((n >>= 7)) out.unshift((n & 0x7f) | 0x80);
  return out;
}
const u32 = (n) => [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255];
const u16 = (n) => [(n >>> 8) & 255, n & 255];

// events: [{ tick, order, bytes: [...] }] -> track chunk bytes (sorted by tick, then order, then insertion)
function trackChunk(events) {
  const ev = events.map((e, i) => ({ ...e, i })).sort((a, b) => a.tick - b.tick || a.order - b.order || a.i - b.i);
  const body = [];
  let last = 0;
  for (const e of ev) { body.push(...vlq(e.tick - last), ...e.bytes); last = e.tick; }
  body.push(0, 0xff, 0x2f, 0x00);
  return [0x4d, 0x54, 0x72, 0x6b, ...u32(body.length), ...body];
}
function smf(format, ppq, tracks) {
  const head = [0x4d, 0x54, 0x68, 0x64, ...u32(6), ...u16(format), ...u16(tracks.length), ...u16(ppq)];
  const all = head.concat(...tracks.map(trackChunk));
  return Uint8Array.from(all);
}
const tempoMeta = (usPerQuarter) => [0xff, 0x51, 0x03, (usPerQuarter >> 16) & 255, (usPerQuarter >> 8) & 255, usPerQuarter & 255];

// --------------------------------------------------------------------------------------- performance ---
// events: practice-log shaped [{ t_ms, kind: on | off | pedal | sound_end | chord, note, vel, down }]
export function performanceMid(events, { t0_ms = 0, channel = 0, stats = null } = {}) {
  const st = stats || {};
  Object.assign(st, { ons: 0, offs: 0, pedalCrossings: 0, pedalNonCrossings: 0, endOffs: 0, velClamped: 0, rounded: 0, negative: 0, t0_ms });
  const evs = events.filter((e) => e.kind in EVENT_ORDER).map((e, i) => ({ e, i })).sort((a, b) => a.e.t_ms - b.e.t_ms || EVENT_ORDER[a.e.kind] - EVENT_ORDER[b.e.kind] || a.i - b.i);
  const out = [{ tick: 0, order: -1, bytes: tempoMeta(US_PER_QUARTER_PERF) }];
  const open = new Map();
  let down = false, lastTick = 0;
  for (const { e } of evs) {
    let t = e.t_ms - t0_ms;
    if (!Number.isInteger(t)) { st.rounded++; t = Math.round(t); }
    if (t < 0) { st.negative++; t = 0; }
    lastTick = Math.max(lastTick, t);
    if (e.kind === "on") {
      let v = Math.round(e.vel ?? 64);
      if (!(v >= 1)) { v = 1; st.velClamped++; } else if (v > 127) { v = 127; st.velClamped++; }
      out.push({ tick: t, order: 2, bytes: [0x90 | channel, e.note & 127, v] });
      open.set(e.note, (open.get(e.note) || 0) + 1);
      st.ons++;
    } else if (e.kind === "off") {
      out.push({ tick: t, order: 0, bytes: [0x80 | channel, e.note & 127, 0] });
      if (open.get(e.note)) open.set(e.note, open.get(e.note) - 1);
      st.offs++;
    } else {
      const d = !!e.down;
      if (d === down) { st.pedalNonCrossings++; continue; }
      down = d;
      out.push({ tick: t, order: 1, bytes: [0xb0 | channel, 64, d ? 127 : 0] });
      st.pedalCrossings++;
    }
  }
  for (const [note, n] of [...open].sort((a, b) => a[0] - b[0])) for (let k = 0; k < n; k++) { out.push({ tick: lastTick, order: 3, bytes: [0x80 | channel, note & 127, 0] }); st.endOffs++; }
  return smf(0, PERFORMANCE_PPQ, [out]);
}

// ---------------------------------------------------------------------------------------- quantized ---
const median = (a) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); if (!s.length) return NaN; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

// Tactus beat durations (ms) per measure from measure.beats_ms (index.js): the gap to the next beat; the last beat of a bar
// runs to the next bar's first beat when that bar follows in the same segment, else the median beat of the bar (or of
// the score), else (end_ms - start_ms) / beats. Clamped to 50-10,000 ms.
export function measureBeatDurations(measures, { defaultMs = 750 } = {}) {
  const inner = measures.map((m) => { const b = m.beats_ms || []; const d = []; for (let k = 0; k + 1 < b.length; k++) d.push(b[k + 1] - b[k]); return d; });
  const global = median(inner.flat().filter((x) => x > 0));
  return measures.map((m, i) => {
    const n = Math.max(1, m.beats || 1), b = m.beats_ms || [];
    const clampMs = (x) => Math.min(10000, Math.max(50, x));
    if (b.length !== n) {
      const even = m.end_ms > m.start_ms && !m.cut ? (m.end_ms - m.start_ms) / n : Number.isFinite(global) ? global : defaultMs;
      return Array.from({ length: n }, () => clampMs(even));
    }
    const d = inner[i].slice();
    const next = measures[i + 1];
    const med = median(d.filter((x) => x > 0));
    let last = null;
    if (next && next.seg === m.seg && next.beats_ms && next.beats_ms.length) { const g = next.beats_ms[0] - b[b.length - 1]; if (g > 0 && (!Number.isFinite(med) || g < 4 * med)) last = g; }
    if (last == null) last = Number.isFinite(med) ? med : m.end_ms > b[b.length - 1] && !m.cut ? m.end_ms - b[b.length - 1] : Number.isFinite(global) ? global : defaultMs;
    d.push(last);
    return d.map(clampMs);
  });
}

// Merge a score's note pieces into sounding notes in measure order: [{ id, note, vel, staff, voice, tick (score ticks from
// the first measure), dur }]. A piece that stops a tie extends the open note of its id; a piece that does not is a new
// onset.
export function soundingNotes(score) {
  const ms = [...score.measures].sort((a, b) => a.index - b.index);
  const vel = new Map((score.notes || []).map((n) => [n.id, n.vel]));
  const starts = barStarts(ms);
  const open = new Map(), out = [];
  ms.forEach((m, i) => {
    const pieces = [];
    for (const v of m.voices) for (const p of v.notes) pieces.push({ p, v });
    pieces.sort((a, b) => a.p.pos - b.p.pos || a.p.note - b.p.note);
    for (const { p, v } of pieces) {
      const at = starts[i] + p.pos;
      const o = open.get(p.id);
      if (p.tieStop && o && o.tick + o.dur === at) o.dur += p.dur;
      else { const n = { id: p.id, note: p.note, vel: vel.get(p.id) ?? 64, staff: v.staff, voice: v.voice, tick: at, dur: p.dur }; out.push(n); open.set(p.id, n); }
    }
  });
  return out;
}
export function barStarts(measures) {
  const out = [];
  let t = 0;
  for (const m of measures) { out.push(t); t += m.barTicks; }
  return out;
}

export function quantizedMid(score, { stats = null, channel = 0 } = {}) {
  const st = stats || {};
  const ms = [...score.measures].sort((a, b) => a.index - b.index);
  const starts = barStarts(ms), K = 480 / 24;
  const BT = score.meter.beatTicks;
  const conductor = [];
  const durs = measureBeatDurations(ms);
  let tempos = 0, maxUs = 0, minUs = Infinity;
  ms.forEach((m, i) => {
    durs[i].forEach((d, k) => {
      const us = Math.max(1, Math.min(0xffffff, Math.round(d * 1000 * (24 / BT))));
      conductor.push({ tick: (starts[i] + k * BT) * K, order: 0, bytes: tempoMeta(us) });
      tempos++; maxUs = Math.max(maxUs, us); minUs = Math.min(minUs, us);
    });
  });
  if (!conductor.length) conductor.push({ tick: 0, order: 0, bytes: tempoMeta(500000) });
  const meter = score.meter.free ? { beats: 4, beatType: 4 } : score.meter;
  conductor.push({ tick: 0, order: -1, bytes: [0xff, 0x58, 0x04, meter.beats, Math.round(Math.log2(meter.beatType)), 24, 8] });
  const tracks = { 1: [], 2: [] };
  const notes = soundingNotes(score);
  for (const n of notes) {
    const tr = tracks[n.staff === 2 ? 2 : 1];
    tr.push({ tick: n.tick * K, order: 1, bytes: [0x90 | channel, n.note & 127, Math.max(1, Math.min(127, Math.round(n.vel)))] });
    tr.push({ tick: (n.tick + n.dur) * K, order: 0, bytes: [0x80 | channel, n.note & 127, 0] });
  }
  Object.assign(st, { notes: notes.length, upper: notes.filter((n) => n.staff !== 2).length, lower: notes.filter((n) => n.staff === 2).length, tempos, minBpmQuarter: maxUs ? 60e6 / maxUs : null, maxBpmQuarter: Number.isFinite(minUs) ? 60e6 / minUs : null });
  return smf(1, QUANTIZED_PPQ, [conductor, tracks[1], tracks[2]]);
}

// Playback time (ms from the first measure) of a score tick under the quantized tempo map, for reports: quantized.mid
// played back against the performance.
export function tickToMs(score) {
  const ms = [...score.measures].sort((a, b) => a.index - b.index);
  const starts = barStarts(ms), durs = measureBeatDurations(ms), BT = score.meter.beatTicks;
  const beatStart = [];
  let t = 0;
  ms.forEach((m, i) => durs[i].forEach((d, k) => { beatStart.push({ tick: starts[i] + k * BT, ms: t, d }); t += d; }));
  return (tick) => {
    let lo = 0, hi = beatStart.length - 1;
    if (hi < 0) return tick * 25;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (beatStart[mid].tick <= tick) lo = mid; else hi = mid - 1; }
    const b = beatStart[lo];
    return b.ms + ((tick - b.tick) / BT) * b.d;
  };
}
