// Bars, written durations, ties and rests for live sheet music: arsenal/web/piano/score/measures.js (pure ES module:
// no DOM, no clock). Stage T4 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections
// 6.4-6.5), amended by plan-amendments.md C1 (written durations under the pedal), C7 (held bass) and section 0 rule 3
// (voices are injected: truth voices on fixtures, a split at MIDI 60 on local benches, hands.js from LS3).
//
//   const grid = createGrid(beatTimesMs, { origin, beatTicks: 24 });      // tick 0 = the beat at beats[origin]
//   const durs = writeDurations(notes, { grid, meter, pedal, barLines });  // Map id -> { dur, staccato, rule, tied }
//   const bars = buildMeasures(notesWithDur, { meter, barLines, from, to }); // per bar: voices, pieces, ties, rests, beams
//
// Bar lines: meter.barTicks apart from tick 0, or explicit barLines (ascending ticks; bar i starts at barLines[i]; past
// either end the lines continue barTicks apart). Explicit lines carry partial bars: a phrase that starts mid-bar and a
// forward-only phase correction (settle.js) both make one.
//
// Notes: { id, note, tick, on_ms, off_ms (null while held), se_ms (null = unknown), voice, staff }. Pedal: [{ t_ms, down }]
// in time order. The rules read the quantities the fixture oracle (tests/fixtures/score/gen.mjs) reads on the ideal
// performance, from the played events and the beat grid instead:
//   t_next   the earliest onset (ms) of the next distinct tick in the note's voice (chord members share it)
//   tol      one 16th at the local beat: P/4 simple, P/6 compound
//   t_se     sound end; if missing, the release when the pedal is up at release, else the next pedal up-crossing
//   slot     one slot of the beat's division: the smallest division holding every onset of that beat, all voices
// Rules (C1, C7):
//   pedal up at release and not pressed before t_next (case 1): end = the release snapped forward to the beat's
//     division, or t_next's tick when t_next − release < tol (legato fill); at least one slot; capped at the bar end.
//     Staccato when held under 40% of its slot (a mark; the value keeps its slot).
//   pedal down at release or pressed before t_next (case 2): t_se >= t_next − tol -> min(t_next, bar end); else t_se
//     snapped to the nearest slot (at least one slot after the onset), capped at the bar end, then a rest.
//   lowest voice of the lower staff (C7, option heldBass): end = min(t_se, next onset in the voice, bar end) with the
//     same fill and snap; one bar-line tie only when the next bar has no onset in that voice before its midpoint (the
//     end is then capped at the next bar's end).
// A release or sound end not known yet reads as ctx.now_ms (live: the tick time; clean: open, Infinity).
// ctx.capTick: no written end past this tick (the end of the last bar the caller builds: a live segment's last started
// bar, or at a segment close its last bar with an onset). A held-bass tie is claimed only into a bar the caller keeps, so
// every bar-line tie leads into a built bar that holds its continuation.
// ctx.heardTick (live only): a held-bass continuation past the bar line never passes this tick: the start of the beat
// the onset finality horizon falls in (index.js: min(tick time, the oldest note-on onsets.js has not handed out yet)).
// A bar can settle, and freeze its tie, before the next bar's midpoint is known; any onset the build has not seen starts
// at or after the horizon and quantizes at or after its beat (quantize.js assignBeats never picks an earlier beat), so it
// never lands inside the frozen continuation (ls1-rulings.md LS2 rulings). On its own this holds on fixed beats, and on
// tracker beats while that beat's predicted time moves by less than 1/8 of a period. It keeps the claim short; the
// no-overlap property itself is enforced by index.js build, which never places an onset inside a frozen continuation in
// its voice (the group is pinned to the continuation's end), so it also holds for onsets already seen that a grid
// revision or a division change moves earlier.

export const MEASURES_API = "arsenal.piano.score.measures/v0";

export const MEASURE_PARAMS = Object.freeze({ staccatoShare: 0.4, heldBass: true, hideRestVoices: Object.freeze([2, 4]) });

const DIVS = [1, 2, 3, 4, 6, 8, 12];
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

function normDiv(positions, beatTicks) {
  for (const d of DIVS) { if (beatTicks % d) continue; const step = beatTicks / d; if (positions.every((p) => p % step === 0)) return d; }
  return beatTicks;
}

// Tick <-> ms over beat times (ascending). Linear inside a beat; before the first and after the last beat the nearest
// beat period extends the grid.
export function createGrid(beats, { origin = 0, beatTicks = 24 } = {}) {
  const n = beats.length, BT = beatTicks;
  const periodOf = (k) => (n < 2 ? 500 : beats[clamp(k, 0, n - 2) + 1] - beats[clamp(k, 0, n - 2)]);
  function beatIndexAt(ms) {
    if (ms < beats[0]) return -1;
    if (ms >= beats[n - 1]) return n - 1;
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (beats[m] <= ms) lo = m; else hi = m; }
    return lo;
  }
  function tickAt(ms) {
    if (!n || !Number.isFinite(ms)) return ms === Infinity ? Infinity : NaN;
    const k = beatIndexAt(ms);
    if (k < 0) return (0 - origin) * BT + ((ms - beats[0]) / periodOf(0)) * BT;
    if (k >= n - 1) return (n - 1 - origin) * BT + ((ms - beats[n - 1]) / periodOf(n - 2)) * BT;
    return (k - origin) * BT + ((ms - beats[k]) / (beats[k + 1] - beats[k])) * BT;
  }
  function msAt(tick) {
    if (!n || !Number.isFinite(tick)) return tick === Infinity ? Infinity : NaN;
    const x = tick / BT + origin, k = Math.floor(x);
    if (k < 0) return beats[0] + x * periodOf(0);
    if (k >= n - 1) return beats[n - 1] + (x - (n - 1)) * periodOf(n - 2);
    return beats[k] + (x - k) * (beats[k + 1] - beats[k]);
  }
  const periodAtTick = (tick) => periodOf(Math.floor(tick / BT + origin));
  return { tickAt, msAt, periodAtTick, beatTicks: BT, origin, count: n };
}

// Bar geometry: bar index at a tick, bar start and end. Explicit lines, extended barTicks apart past both ends.
export function barGeometry(barTicks, barLines = null) {
  const L = barLines && barLines.length ? barLines : null;
  if (!L) return { indexAt: (t) => Math.floor(t / barTicks), start: (i) => i * barTicks, end: (i) => (i + 1) * barTicks };
  const n = L.length;
  const start = (i) => (i < 0 ? L[0] + i * barTicks : i < n ? L[i] : L[n - 1] + (i - n + 1) * barTicks);
  const indexAt = (t) => {
    if (t < L[0]) return -Math.ceil((L[0] - t) / barTicks);
    if (t >= L[n - 1]) return n - 1 + Math.floor((t - L[n - 1]) / barTicks);
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (L[m] <= t) lo = m; else hi = m; }
    return lo;
  };
  return { indexAt, start, end: (i) => start(i + 1) };
}

// The staff-2 voice with the lowest median pitch (C7 "lowest voice of the lower staff"), or null.
export function lowestLowerVoice(notes) {
  const by = new Map();
  for (const n of notes) if (n.staff === 2) { if (!by.has(n.voice)) by.set(n.voice, []); by.get(n.voice).push(n.note); }
  let best = null, bestMed = Infinity;
  for (const [v, ps] of by) { const s = [...ps].sort((a, b) => a - b), med = s[s.length >> 1]; if (med < bestMed || (med === bestMed && v > best)) { bestMed = med; best = v; } }
  return best;
}

function pedalOps(pedal) {
  const P = pedal || [];
  const downAt = (ms) => { let d = false; for (const p of P) { if (p.t_ms > ms) break; d = p.down; } return d; };
  const liftAfter = (ms) => { for (const p of P) if (p.t_ms > ms && !p.down) return p.t_ms; return Infinity; };
  const pressIn = (a, b) => { for (const p of P) { if (p.t_ms >= b) break; if (p.down && p.t_ms > a) return true; } return false; };
  return { downAt, liftAfter, pressIn };
}

// Written durations (C1, C7). ctx: { grid, meter: { beatTicks, barTicks, compound }, barLines, pedal, lowest (voice or
// null; default lowestLowerVoice(notes)), heldBass, now_ms }.
export function writeDurations(notes, ctx) {
  const c = { ...MEASURE_PARAMS, ...ctx };
  const { grid } = c, BT = c.meter.beatTicks, compound = !!c.meter.compound;
  const geo = barGeometry(c.meter.barTicks, c.barLines);
  const now = c.now_ms ?? Infinity, capTick = c.capTick ?? Infinity, heardTick = c.heardTick ?? Infinity;
  const { downAt, liftAfter, pressIn } = pedalOps(c.pedal);
  const lowest = c.lowest === undefined ? lowestLowerVoice(notes) : c.lowest;

  const beatPos = new Map(), byVoice = new Map(), firstOn = new Map();
  for (const n of notes) {
    if (n.tick == null) continue;
    const k = Math.floor(n.tick / BT);
    if (!beatPos.has(k)) beatPos.set(k, new Set());
    beatPos.get(k).add(n.tick - k * BT);
    if (!byVoice.has(n.voice)) byVoice.set(n.voice, new Set());
    byVoice.get(n.voice).add(n.tick);
    const key = n.voice + "|" + n.tick;
    if (!firstOn.has(key) || n.on_ms < firstOn.get(key)) firstOn.set(key, n.on_ms);
  }
  const voiceTicks = new Map([...byVoice].map(([v, s]) => [v, [...s].sort((a, b) => a - b)]));
  const divAt = (k) => (beatPos.has(k) ? normDiv([...beatPos.get(k)], BT) : 1);
  const slotAt = (tick) => BT / divAt(Math.floor(tick / BT));
  const snap = (tickF, forward) => {
    if (!Number.isFinite(tickF)) return tickF;
    const k = Math.floor(tickF / BT), step = BT / divAt(k), base = k * BT, x = (tickF - base) / step;
    return base + step * (forward ? Math.ceil(x - 1e-6) : Math.round(x));
  };
  const nextAfter = (list, tick) => { let lo = 0, hi = list.length; while (lo < hi) { const m = (lo + hi) >> 1; if (list[m] > tick) hi = m; else lo = m + 1; } return lo < list.length ? list[lo] : Infinity; };

  const out = new Map();
  for (const n of notes) {
    if (n.tick == null) continue;
    const list = voiceTicks.get(n.voice);
    const nextTick = nextAfter(list, n.tick);
    const tNext = Number.isFinite(nextTick) ? firstOn.get(n.voice + "|" + nextTick) : Infinity;
    const bi = geo.indexAt(n.tick), barEnd = geo.end(bi);
    const P = grid.periodAtTick(n.tick), tolMs = P / (compound ? 6 : 4);
    const off = n.off_ms ?? now;
    const se = n.se_ms ?? (downAt(off) ? Math.min(liftAfter(off), now) : off);
    const oneSlot = n.tick + slotAt(n.tick);
    let end, rule, staccato = false, tied = false;
    if (c.heldBass && n.staff === 2 && lowest != null && n.voice === lowest) {
      rule = "heldBass";
      end = se >= tNext - tolMs ? nextTick : Math.max(snap(grid.tickAt(se), false), oneSlot);
      let cap = barEnd;
      if (end > barEnd && barEnd < capTick) {
        const nextEnd = geo.end(bi + 1), mid = barEnd + (nextEnd - barEnd) / 2;
        const early = list.some((x) => x >= barEnd && x < mid);
        cap = early ? barEnd : nextEnd;
      }
      end = Math.min(end, cap);
      // live: the continuation stops at the beat of the onset finality horizon, so an onset in the voice this build has
      // not seen (it quantizes at or after that beat) never lands inside a tie frozen before the next bar's midpoint was known
      if (end > barEnd) end = Math.max(barEnd, Math.min(end, heardTick));
      tied = end > barEnd;
    } else if (!(downAt(off) || pressIn(off, tNext))) {
      rule = "dry";
      end = tNext - off < tolMs ? nextTick : Math.max(snap(grid.tickAt(off), true), oneSlot);
      end = Math.min(end, barEnd);
      const slotMs = (slotAt(n.tick) / BT) * P;
      staccato = Number.isFinite(off) && off - n.on_ms < c.staccatoShare * slotMs;
    } else {
      rule = "pedal";
      end = se >= tNext - tolMs ? Math.min(nextTick, barEnd) : Math.min(Math.max(snap(grid.tickAt(se), false), oneSlot), barEnd);
    }
    end = Math.min(end, nextTick);
    if (!Number.isFinite(end)) end = barEnd;
    if (n.tick < capTick && end > capTick) { end = capTick; tied = false; }
    if (end <= n.tick) end = Math.min(oneSlot, nextTick);
    out.set(n.id, { dur: end - n.tick, staccato, rule, tied });
  }
  return out;
}

// Written values at TPQ 24 (a quarter is 24 ticks): length -> [type (MusicXML names), dots]. A piece inside a tuplet
// beat is looked up at its written length, ticks × actual / normal.
export const WRITTEN_VALUES = new Map([
  [144, ["whole", 1]], [96, ["whole", 0]], [72, ["half", 1]], [48, ["half", 0]], [36, ["quarter", 1]], [24, ["quarter", 0]],
  [18, ["eighth", 1]], [12, ["eighth", 0]], [9, ["16th", 1]], [6, ["16th", 0]], [4.5, ["32nd", 1]], [3, ["32nd", 0]], [1.5, ["64th", 0]],
]);
const BEAMED = new Set(["eighth", "16th", "32nd", "64th"]);
const mod = (x, m) => ((x % m) + m) % m;

// The tuplet a voice's beat division implies: simple beats d 3, 6, 12 (3 in the time of 2 per level), compound beats
// d 2, 4 (2 in the time of 3). null for a plain division.
export function tupletOf(d, compound) {
  if (compound) return d === 2 || d === 4 ? { actual: d, normal: (d * 3) / 2 } : null;
  return d === 3 || d === 6 || d === 12 ? { actual: d, normal: (d * 2) / 3 } : null;
}

// Rhythm spelling for one voice in one bar (plan 6.5, transcription.md T4). Every note piece and rest is one written
// value; anything else is split, notes tied and rests not. points: Map beat number (tick / beatTicks) -> positions in
// that beat where a note of the voice starts or ends; the smallest division holding them is the voice's division of the
// beat, and a tuplet division makes it a tuplet beat (one bracket per beat, so no piece crosses its edges).
// A single value is allowed when:
//   notes  its written length is a value; a dotted value starts on the beat or on the beat's main subdivision (the
//          half-beat in simple beats, also the triplet eighth in simple tuplet beats, the eighth in compound beats, the
//          duplet eighth in compound tuplet beats); in a full 4/4 or 12/8 bar it crosses the half bar only from beat 1,
//          or from beat 2 when it ends by beat 4; across a beat line, simple meters: from a beat, or from the half-beat
//          over one beat line ending on the half-beat grid (the syncopated quarter, the dotted quarter after an eighth);
//          compound meters: from a beat, ending on a beat; inside a beat, a note that starts off the main subdivision
//          crosses at most one main subdivision line.
//   rests  plain values, except whole compound beats (dotted quarter, dotted half) from a beat; across a beat line only
//          the 4/4 half rests on beats 1-2 and 3-4 and whole compound beats (never across the 12/8 half bar); inside a
//          beat, a rest crosses a main subdivision line only from the beat.
// Split point: the half bar when the piece crosses it, else the beat lines, else the beat's subdivision lines (simple
// 12, 6, 3; simple triplet 8, 4, 2; sextuplet 12, 4, 2; compound 12, 6, 3; compound duplet 18, 9), then single ticks. At
// the strongest level with a line inside the piece: the first line when the piece starts off that level's grid (it
// reaches the grid), else the last one (the longest value first).
function createSpeller({ start: s, barTicks, beatTicks: BT, compound, full, points }) {
  const h = full && barTicks === 4 * BT ? s + 2 * BT : null;
  const cache = new Map();
  function ctxOf(k) {
    let c = cache.get(k);
    if (c) return c;
    const d = normDiv([0, ...(points.get(k) || [])], BT), tup = tupletOf(d, compound);
    const main = compound ? (tup ? BT / 2 : BT / 3) : tup && d === 3 ? BT / 3 : BT / 2;
    const anchors = compound || !tup ? [main] : [BT / 3, BT / 2];
    const steps = compound ? (tup ? [BT / 2, BT / 4, 1] : [BT / 3, BT / 6, BT / 12, 1]) : tup ? [main, BT / 6, BT / 12, 1] : [BT / 2, BT / 4, BT / 8, 1];
    c = { d, tup, main, anchors, steps };
    cache.set(k, c);
    return c;
  }
  function valueOf(a, e) {
    const k0 = Math.floor(a / BT), tup = Math.ceil(e / BT) - 1 === k0 ? ctxOf(k0).tup : null;
    const v = WRITTEN_VALUES.get(tup ? ((e - a) * tup.actual) / tup.normal : e - a);
    return v ? { type: v[0], dots: v[1] } : null;
  }
  function allowed(a, e, rest) {
    const len = e - a, k0 = Math.floor(a / BT), k1 = Math.ceil(e / BT) - 1, rel = a - k0 * BT;
    if (k1 > k0) for (let k = k0; k <= k1; k++) if (ctxOf(k).tup) return false;
    const cx = ctxOf(k0), v = valueOf(a, e);
    if (!v) return false;
    if (v.dots) {
      if (rest) { if (!(compound && !cx.tup && rel === 0 && len % BT === 0)) return false; }
      else if (!(k1 > k0 ? [compound ? BT / 3 : BT / 2] : cx.anchors).some((q) => rel % q === 0)) return false;
    }
    if (h != null && a < h && e > h && (rest || !(a === s || (a === s + BT && e <= s + 3 * BT)))) return false;
    if (k1 > k0) {
      if (rest) return compound ? rel === 0 && mod(e, BT) === 0 : h != null && len === 2 * BT && (a === s || a === h);
      if (compound) return rel === 0 && mod(e, BT) === 0;
      return rel === 0 || (rel % (BT / 2) === 0 && k1 === k0 + 1 && mod(e, BT / 2) === 0);
    }
    const lines = Math.ceil((e - k0 * BT) / cx.main) - 1 - Math.floor(rel / cx.main);
    return rest ? rel === 0 || lines === 0 : rel % cx.main === 0 || lines <= 1;
  }
  function lineIn(a, e, step, origin) {
    const first = origin + (Math.floor((a - origin) / step) + 1) * step;
    if (first >= e) return null;
    return mod(a - origin, step) === 0 ? origin + (Math.ceil((e - origin) / step) - 1) * step : first;
  }
  // -> [{ a, e, type, dots }] in time order; type null only for a piece no line can split further (off the tick grid)
  function split(a, e, rest, out = []) {
    if (!(e > a)) return out;
    if (allowed(a, e, rest)) { out.push({ a, e, ...valueOf(a, e) }); return out; }
    let b = h != null && a < h && e > h ? h : lineIn(a, e, BT, 0);
    if (b == null) { const k = Math.floor(a / BT); for (const step of ctxOf(k).steps) { b = lineIn(a, e, step, k * BT); if (b != null) break; } }
    if (b == null) { out.push({ a, e, ...(valueOf(a, e) || { type: null, dots: 0 }) }); return out; }
    split(a, b, rest, out);
    split(b, e, rest, out);
    return out;
  }
  return { ctxOf, split };
}

// Bars from notes with tick and dur: pieces split at bar lines (ties), then spelled into written values (ties inside the
// bar, including the 4/4 beat-3 split; see createSpeller), rests per voice spelled the same way (gaps; voices 2 and 4
// hide whole-bar rests), beams and tuplets per beat and voice. Note pieces: { id, note, pos, dur, type, dots, dotted,
// tieStart, tieStop, barTie, staccato }; rests: { pos, dur, type, dots }.
// from / to: bar indices (inclusive / exclusive), default every bar holding a note. looseBeats: Set of beat numbers
// (tick / beatTicks) flagged loose.
export function buildMeasures(notes, { meter, barLines = null, from = null, to = null, looseBeats = null, hideRestVoices = MEASURE_PARAMS.hideRestVoices } = {}) {
  const BT = meter.beatTicks, barT = meter.barTicks, compound = !!meter.compound;
  const geo = barGeometry(barT, barLines);
  const bars = new Map(), spansOf = new Map();
  const barOf = (b) => {
    if (!bars.has(b)) { const s = geo.start(b), e = geo.end(b); bars.set(b, { index: b, startTick: s, barTicks: e - s, full: e - s === barT, voices: new Map(), beams: [], tuplets: [], loose: [] }); }
    return bars.get(b);
  };
  if (from != null && to != null) for (let b = from; b < to; b++) barOf(b);
  for (const n of notes) {
    if (n.tick == null || n.dur == null) continue;
    let a = n.tick; const z = n.tick + n.dur;
    while (a < z) {
      const b = geo.indexAt(a), e = Math.min(z, geo.end(b));
      if ((from == null || b >= from) && (to == null || b < to)) {
        const bar = barOf(b);
        if (!bar.voices.has(n.voice)) { const v = { voice: n.voice, staff: n.staff, notes: [], rests: [] }; bar.voices.set(n.voice, v); spansOf.set(v, []); }
        spansOf.get(bar.voices.get(n.voice)).push({ n, a, e, z });
      }
      a = e;
    }
  }
  for (const bar of bars.values()) {
    const s = bar.startTick, end = s + bar.barTicks, k0 = Math.floor(s / BT);
    for (const v of bar.voices.values()) {
      const spans = spansOf.get(v), points = new Map();
      const addPoint = (t) => { if (t < s || t >= end) return; const k = Math.floor(t / BT); if (!points.has(k)) points.set(k, []); points.get(k).push(t - k * BT); };
      for (const sp of spans) { addPoint(sp.a); addPoint(sp.e); }
      const speller = createSpeller({ start: s, barTicks: bar.barTicks, beatTicks: BT, compound, full: bar.full, points });
      for (const { n, a, e, z } of spans) {
        const parts = speller.split(a, e, false);
        parts.forEach((p, i) => {
          const last = i === parts.length - 1;
          v.notes.push({ id: n.id, note: n.note, pos: p.a - s, dur: p.e - p.a, type: p.type, dots: p.dots, dotted: p.dots > 0, tieStop: i > 0 || a > n.tick, tieStart: !last || e < z, barTie: last && e < z, staccato: !!n.staccato && i === 0 && a === n.tick });
        });
      }
      v.notes.sort((x, y) => x.pos - y.pos || x.note - y.note);
      const rest = (g0, g1) => { for (const p of speller.split(g0, g1, true)) v.rests.push({ pos: p.a - s, dur: p.e - p.a, type: p.type, dots: p.dots }); };
      let at = s;
      for (const sp of [...spans].sort((x, y) => x.a - y.a)) { if (sp.a > at) rest(at, sp.a); at = Math.max(at, sp.e); }
      if (at < end) rest(at, end);
      const beatsN = Math.ceil(bar.barTicks / BT);
      for (let j = 0; j < beatsN; j++) {
        if (points.has(k0 + j)) { const c = speller.ctxOf(k0 + j); if (c.tup) bar.tuplets.push({ voice: v.voice, beat: j, actual: c.tup.actual, normal: c.tup.normal }); }
        const inBeat = v.notes.filter((nt) => nt.pos >= j * BT && nt.pos < (j + 1) * BT);
        const short = new Set(inBeat.filter((nt) => BEAMED.has(nt.type)).map((nt) => nt.pos));
        if (short.size >= 2) bar.beams.push({ voice: v.voice, beat: j, ids: [...new Set(inBeat.filter((nt) => short.has(nt.pos)).map((nt) => nt.id))] });
      }
    }
    for (const hv of hideRestVoices) { const v = bar.voices.get(hv); if (v && v.notes.length === 0) bar.voices.delete(hv); }
    if (looseBeats) for (const k of looseBeats) { const t = k * BT; if (t >= bar.startTick && t < bar.startTick + bar.barTicks) bar.loose.push((t - bar.startTick) / BT); }
  }
  return [...bars.values()].sort((x, y) => x.index - y.index).map((b) => ({ ...b, voices: [...b.voices.values()].sort((x, y) => x.voice - y.voice) }));
}

// Content signature of a built bar (settle.js compares it to decide rev and to prove settled bars never change).
export function barSignature(bar) {
  const parts = [bar.index, bar.startTick, bar.barTicks];
  for (const v of bar.voices) { parts.push("v" + v.voice + "s" + v.staff); for (const nt of v.notes) parts.push(`${nt.id}:${nt.note}:${nt.pos}:${nt.dur}:${+nt.tieStart}${+nt.tieStop}`); }
  if (bar.loose && bar.loose.length) parts.push("L" + bar.loose.join(","));
  return parts.join("|");
}
