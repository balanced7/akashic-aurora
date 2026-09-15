// Hands, staves, voices, clefs and octave lines for live sheet music: arsenal/web/piano/score/hands.js (pure ES module:
// no DOM, no clock). Stage T5 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 5.1,
// 6.5 "Hands", "Clefs and octave lines") and transcription.md T5; plan-amendments.md section 0 rule 3 (from LS3,
// measures.js takes this module's voices).
//
//   const hands = createHands();
//   hands.addGroup(group)                    // onset groups from onsets.js flush(), in time order ({ id, t, notes })
//   const snap = hands.snapshot();           // the current best path: snap.handOf(noteId) -> "L" | "R", snap.staffOf(note)
//   assignVoices(notes, { staffOf, now_ms }) // Map id -> { staff, voice } for a window of notes
//   clefsAndOctaves(measures)                // per bar (hindsight): clef per staff, octave line (8va / 15ma, 8vb / 15mb),
//                                            // change reason, notes left beyond 3 ledger lines and why
//   createClefTracker().commit(bar, next)    // live: decide a bar once with the next bar as known then; preview(bars)
//   ledgerExcess(note, clef, octave)         // semitones beyond the 3-ledger range (0 inside)
//
// Split per onset group (T5): the candidate splits are every gap between adjacent pitches plus all-left and all-right
// (k = 0..m: the left hand takes the k lowest notes). A Viterbi over the groups in time order; each state carries its
// path's hand histories (key-held notes, the last contMs of notes each hand held), so the costs read that path:
//   span        a hand's new notes plus the keys it still holds span more than spanSoft (12) semitones: 1; more than
//               spanHard (16): 4
//   continuity  contPerSemitone (1/6, 2 per octave) × the distance of the hand's new notes' mean from the mean pitch of
//               the notes that hand held in the last contMs (2 s; pedal-held notes do not count, since only key-held ones
//               are in the history). A hand with no history reads a prior centre (left 48, right 72) at priorWeight (0.5).
//               Single-hand stretch: while the other hand has held nothing for contMs, notes whose mean lies between the
//               two prior centres cost nothing.
//   crossing    the left hand's top (new or held, else its centre) above the right hand's bottom: crossCost (3)
//   gap         a split at a gap that is not the group's largest: gapCost (0.5)
// Live, the best path is read back at every build, so a recent group's hand may change as later groups arrive (fixed-lag
// smoothing); a group older than `horizon` (48) groups keeps the hand the best path gave it when it left the trellis.
// Settled bars carry their notes' staves and voices, so a change never reaches a settled bar (index.js).
// Staff from hand: left hand -> staff 2, right hand -> staff 1; a right-hand note below trebleMin (F3, 53: three ledger
// lines) moves to staff 2 as its upper voice.
// Voices, at most 2 per staff (T5): a note whose key is still held (release, or now_ms while held, minus sustainTolMs
// 100) at the onset of a later group in its staff, and that lies at or below every note of every such later group, is a
// sustained lower note; the notes of those later groups are the moving line above it. Staff 1: moving and lone notes
// voice 1, sustained lower notes voice 2. Staff 2: sustained lower notes and lone notes voice 4, the moving line above a
// sustained lower note voice 3. So voice 4 is always the lower staff's lowest line: C7's held bass (measures.js) applies
// to it, the way the fixture oracle's "voice 4 if present, else 3" does.
// Clefs and octave lines (T5, plan 6.5, ls1-rulings.md LS3 rulings; the rules are written out above clefStep below): 3
// ledger lines are allowed, so a clef holds written pitches treble F3-E6 (53-88) and bass A1-G4 (33-67) (the note on the
// third ledger line is the limit). 8va and 15ma only above a treble clef, 8vb and 15mb only below a bass clef; the lower
// staff changes clef only after 2 bars that want it and holds a clef at least 2 bars; a note the rules leave beyond 3
// ledger lines is counted (overflow).

export const HANDS_API = "arsenal.piano.score.hands/v0";

export const HANDS_PARAMS = Object.freeze({
  spanSoft: 12, spanSoftCost: 1, spanHard: 16, spanHardCost: 4, crossCost: 3, gapCost: 0.5,
  contPerSemitone: 1 / 6, contMs: 2000, priorLeft: 48, priorRight: 72, priorWeight: 0.5,
  // switchCost, switchMs, clusterMs: tuned on the LS0 tuning seeds (5, 6) only. clusterMs 80: voice F1 0.8646 at 60,
  // 0.8691 at 80, 0.8681 at 120 (where a bass played 90 ms before the next downbeat bass merged with it as a chord)
  switchCost: 3, switchMs: 600, chordPedalSustain: true, clusterMs: 80,
  horizon: 48, histMax: 32, sustainTolMs: 100,
  // clefs and octave lines (ls1-rulings.md LS3 rulings): written-pitch ranges within 3 ledger lines, the hysteresis note,
  // the 2-bar rule, the lookahead reading of it, and the least passage for a double octave line
  trebleMin: 53, trebleMax: 88, bassMin: 33, bassMax: 67, clefUp: 60, clefBars: 2, clefLookahead: true, doubleMinNotes: 2,
});

const heldAt = (n, t) => n.t < t && (n.off == null || n.off > t);

// the path-dependent summary one state needs for the next group's costs
function summarize(hist, t, c) {
  const s = { held: [null, null], recent: [0, 0], recentN: [0, 0] };
  for (let h = 0; h < 2; h++) {
    let lo = Infinity, hi = -Infinity, sum = 0, n = 0;
    for (const x of hist[h]) {
      if (heldAt(x, t)) { if (x.note < lo) lo = x.note; if (x.note > hi) hi = x.note; }
      if (x.t >= t - c.contMs || x.off == null || x.off > t - c.contMs) { sum += x.note; n++; }
    }
    s.held[h] = lo === Infinity ? null : { lo, hi };
    s.recent[h] = n ? sum / n : null; s.recentN[h] = n;
  }
  return s;
}

export function createHands(params = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  const layers = [];              // { g, notes (by pitch), states: [{ k, cost, prev, hist: [L[], R[]] }] }
  const fixed = new Map();        // note id -> "L" | "R" for groups that left the trellis
  let rev = 0, snap = null;

  function localCost(k, notes, pre, sum, s) {
    const m = notes.length;
    let cost = 0;
    const hands = [[0, k], [k, m]];
    const ref = [null, null];
    for (let h = 0; h < 2; h++) {
      const [a, b] = hands[h];
      if (b <= a) {
        ref[h] = s.held[h] ? (h === 0 ? s.held[h].hi : s.held[h].lo) : s.recent[h];
        continue;
      }
      const lo = notes[a].note, hi = notes[b - 1].note, mean = (pre[b] - pre[a]) / (b - a);
      const hlo = s.held[h] ? Math.min(lo, s.held[h].lo) : lo, hhi = s.held[h] ? Math.max(hi, s.held[h].hi) : hi;
      const span = hhi - hlo;
      if (span > c.spanHard) cost += c.spanHardCost; else if (span > c.spanSoft) cost += c.spanSoftCost;
      const other = 1 - h;
      let cont = s.recent[h] != null ? c.contPerSemitone * Math.abs(mean - s.recent[h]) : c.priorWeight * c.contPerSemitone * Math.abs(mean - (h === 0 ? c.priorLeft : c.priorRight));
      // single-hand stretch: the other hand idle for contMs, notes between the prior centres are free for this hand
      if (s.recentN[h] > 0 && s.recentN[other] === 0 && mean >= c.priorLeft && mean <= c.priorRight) cont = 0;
      cost += cont;
      ref[h] = h === 0 ? hhi : hlo;
    }
    if (ref[0] != null && ref[1] != null && (k > 0 || k < m) && ref[0] > ref[1]) cost += c.crossCost;
    if (k > 0 && k < m && notes[k].note - notes[k - 1].note < sum.maxGap) cost += c.gapCost;
    // figure continuity: a single note that changes hand from the single note just before it (within switchMs)
    if (m === 1 && sum.prevSingle && sum.prevK != null && (sum.prevK === 1) !== (k === 1)) cost += c.switchCost;
    return cost;
  }

  function addGroup(g) {
    const notes = [...g.notes].sort((a, b) => a.note - b.note || a.id - b.id);
    const m = notes.length, t = g.t;
    const pre = [0]; for (const n of notes) pre.push(pre[pre.length - 1] + n.note);
    let maxGap = 0; for (let i = 1; i < m; i++) maxGap = Math.max(maxGap, notes[i].note - notes[i - 1].note);
    const last = layers.length ? layers[layers.length - 1] : null;
    const prev = last ? last.states : [{ k: null, cost: 0, prev: null, hist: [[], []] }];
    const prevSingle = !!last && m === 1 && last.notes.length === 1 && t - last.g.t <= c.switchMs;
    const sums = prev.map((p) => summarize(p.hist, t, c));
    const states = [];
    for (let k = 0; k <= m; k++) {
      let best = null, bj = -1;
      for (let j = 0; j < prev.length; j++) {
        const v = prev[j].cost + localCost(k, notes, pre, { maxGap, prevSingle, prevK: prev[j].k }, sums[j]);
        if (best == null || v < best) { best = v; bj = j; }
      }
      const ph = prev[bj].hist, keep = (x) => x.off == null || x.off > t - c.contMs || x.t >= t - c.contMs;
      const hist = [ph[0].filter(keep).concat(notes.slice(0, k)), ph[1].filter(keep).concat(notes.slice(k))];
      for (let h = 0; h < 2; h++) if (hist[h].length > c.histMax) hist[h] = hist[h].slice(-c.histMax);
      states.push({ k, cost: best, prev: layers.length ? bj : null, hist });
    }
    // keep costs bounded: subtract the layer minimum
    const lo = Math.min(...states.map((s) => s.cost));
    for (const s of states) s.cost -= lo;
    layers.push({ g, notes, states });
    if (layers.length > c.horizon) {
      const path = backtrack();
      const L0 = layers.shift();
      for (const n of L0.notes) fixed.set(n.id, path.get(n.id));
      for (const s of layers[0].states) s.prev = null;
    }
    rev++;
    return rev;
  }

  function backtrack() {
    const out = new Map();
    if (!layers.length) return out;
    let si = 0, lastStates = layers[layers.length - 1].states;
    for (let i = 1; i < lastStates.length; i++) if (lastStates[i].cost < lastStates[si].cost) si = i;
    for (let li = layers.length - 1; li >= 0 && si != null; li--) {
      const L = layers[li], s = L.states[si];
      L.notes.forEach((n, i) => out.set(n.id, i < s.k ? "L" : "R"));
      si = s.prev;
    }
    return out;
  }

  function snapshot() {
    if (snap && snap.rev === rev) return snap;
    const path = backtrack();
    const handOf = (id) => path.get(id) ?? fixed.get(id) ?? null;
    const staffOf = (n) => { const h = handOf(n.id); if (h == null) return n.note >= 60 ? 1 : 2; return h === "L" ? 2 : n.note < c.trebleMin ? 2 : 1; };
    snap = { rev, handOf, staffOf };
    return snap;
  }

  return { addGroup, snapshot, params: () => ({ ...c }), size: () => layers.length };
}

// Voices for a window of notes (see header). notes: [{ id, note, t, off (null while held), group: { id } | groupId }];
// staffOf(note) -> 1 | 2; now_ms: the release time of notes still held (live: the tick time; offline: Infinity).
export function assignVoices(notes, { staffOf, now_ms = Infinity, pedal = null, params = {} } = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  const out = new Map();
  const P = pedal || [];
  const downAt = (ms) => { let d = false; for (const p of P) { if (p.t_ms > ms) break; d = p.down; } return d; };
  const liftAfter = (ms) => { for (const p of P) if (p.t_ms > ms && !p.down) return p.t_ms; return now_ms; };
  // a chord's inner and lower notes sound to their sound end under the pedal (an early finger release under the pedal
  // keeps the chord sustained); a single note and a chord's top note read their key release only, so a pedalled melody
  // never splits into voices
  const endOf = (n, chordInner) => {
    const key = n.off ?? now_ms;
    if (!chordInner || !c.chordPedalSustain || n.off == null) return key;
    const se = n.soundEnd ?? (downAt(n.off) ? liftAfter(n.off) : n.off);
    return Math.max(key, Math.min(se, now_ms));
  };
  for (const staff of [1, 2]) {
    // clusters: notes of the staff starting within clusterMs (the roll span) of a cluster's first note, so a rolled or
    // jittered chord and the melody note played with it are one onset for the voice test
    const mine = notes.filter((n) => staffOf(n) === staff).sort((a, b) => a.t - b.t || a.note - b.note);
    const groups = [];
    for (const n of mine) {
      const G = groups[groups.length - 1];
      if (G && n.t - G.t <= c.clusterMs) G.notes.push(n); else groups.push({ t: n.t, notes: [n] });
    }
    const lows = groups.map((G) => Math.min(...G.notes.map((n) => n.note)));
    const lower = new Set(), moving = new Set();   // note ids
    for (let i = 0; i < groups.length; i++) {
      const G = groups[i];
      const topNote = G.notes.length > 1 ? G.notes.reduce((a, b) => (b.note > a.note ? b : a)) : null;
      for (const n of G.notes) {
        const inner = !!topNote && n.note < topNote.note;
        const end = endOf(n, inner) - c.sustainTolMs;
        let over = 0, below = true;
        const cover = [];
        for (let j = i + 1; j < groups.length && groups[j].t < end; j++) {
          over++; cover.push(j);
          if (n.note > lows[j]) { below = false; break; }
        }
        // (a chord's lower notes outlasting its top note at one onset were tried as a second rule for the lower voice: on
        // the tuning seeds voice F1 with truth staves fell 0.9365 -> 0.9268, so the rule stays "sustained over a later onset")
        if (below && over) {
          lower.add(n.id);
          for (const j of cover) for (const x of groups[j].notes) moving.add(x.id);
        }
      }
    }
    // at most 2 voices per staff: a note both sustained below a later line and moving above an earlier sustained note
    // joins the moving line
    for (const n of mine) {
      const low = lower.has(n.id) && !moving.has(n.id);
      const voice = staff === 1 ? (low ? 2 : 1) : low ? 4 : moving.has(n.id) ? 3 : 4;
      out.set(n.id, { staff, voice });
    }
  }
  return out;
}

// Written = sounding minus this under an octave line: 8va +12, 15ma +24 (treble clef only); 8vb -12, 15mb -24 (bass clef
// only). The octave value per staff per bar is 0 | 8 | 15 | -8 | -15.
export const OCTAVE_SHIFT = Object.freeze({ 0: 0, 8: 12, 15: 24, "-8": -12, "-15": -24 });

// Semitones a sounding pitch lies beyond the 3-ledger range of a clef under an octave line (0 inside).
export function ledgerExcess(note, clef, octave = 0, params = {}) {
  // a full parameter set (every internal caller passes one) is read as is; anything else is merged over the defaults
  const c = "trebleMin" in params && "trebleMax" in params && "bassMin" in params && "bassMax" in params ? params : { ...HANDS_PARAMS, ...params };
  const w = note - (OCTAVE_SHIFT[octave] ?? 0);
  const lo = clef === "bass" ? c.bassMin : c.trebleMin, hi = clef === "bass" ? c.bassMax : c.trebleMax;
  return w < lo ? lo - w : w > hi ? w - hi : 0;
}

// Clefs and octave lines (ls1-rulings.md "LS2close to LS5 rulings", LS3; plan 6.5; transcription.md T5):
// - Octave lines by clef: 8va and 15ma only above a treble clef, 8vb and 15mb only below a bass clef. Staff 1 is always
//   treble. A lower staff that climbs changes to treble clef under the 2-bar rule; it never takes a bass-clef 8va.
// - The octave line on a bar: none if the clef holds every note within 3 ledger lines, else the single line (8va / 8vb)
//   if it holds them all; else the double line (15ma / 15mb) only for a passage of at least doubleMinNotes (2) distinct
//   notes still beyond under the better of the two, when it leaves fewer beyond. A single note beyond is accepted on its
//   ledger lines and counted (overflow "single"). The clef never changes mid-bar.
// - The lower staff's clef (initial bass). A bar wants the clef whose lines (0 and its single octave line) hold its notes
//   when only one clef does; when both do, treble if every note is at or above clefUp (C4, 60), else bass (the plan 6.5
//   hysteresis); when neither does, nothing. A change needs clefBars (2) consecutive bars that want the other clef (with
//   clefLookahead, the default, the bar itself and the next bar, so the change sits at the first of them; without it, the
//   previous bar and this one), and a clef holds for at least clefBars bars before it may change again (no one-bar round
//   trips). A shorter excursion keeps the clef: an octave line where the clef allows one, else ledger lines, counted as
//   overflow "excursion".
// - Every bar reports its notes still beyond 3 ledger lines per staff (beyond: note pieces; beyondNotes: distinct notes)
//   and why (overflow: "excursion" when the other clef would hold the bar, "single" for one note, "span" otherwise).
// The decision for a bar reads its own notes, the state earlier bars left and (with lookahead) the next bar's notes.
// createClefTracker commits bars one at a time with the next bar as then known (live: a settled bar's row is final);
// clefsAndOctaves runs it over a finished sequence with hindsight.
const OTHER_CLEF = (k) => (k === "bass" ? "treble" : "bass");
const LINES = { treble: [8, 15], bass: [-8, -15] };

function piecesOf(m) {
  const p1 = [], p2 = [];
  for (const v of (m && m.voices) || []) for (const n of v.notes) (v.staff === 2 ? p2 : p1).push(n);
  return { p1, p2 };
}
// beyond under one clef and octave line: note pieces, distinct notes (by id, else by piece), semitones
function excessOn(pieces, clef, oct, c) {
  let beyond = 0, semis = 0;
  const ids = new Set();
  for (const x of pieces) { const e = ledgerExcess(x.note, clef, oct, c); if (e) { beyond++; semis += e; ids.add(x.id ?? x); } }
  return { clef, oct, beyond, notes: ids.size, semis };
}
const fewer = (a, b) => (a.notes !== b.notes ? a.notes < b.notes : a.semis !== b.semis ? a.semis < b.semis : Math.abs(a.oct) <= Math.abs(b.oct));
// the octave line a clef takes for a bar's pieces (see header)
export function octaveOn(pieces, clef, params = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  const [single, dbl] = LINES[clef];
  const o0 = excessOn(pieces, clef, 0, c);
  if (!o0.beyond) return o0;
  const o1 = excessOn(pieces, clef, single, c);
  if (!o1.beyond) return o1;
  const best = fewer(o1, o0) ? o1 : o0;
  if (best.notes >= c.doubleMinNotes) { const o2 = excessOn(pieces, clef, dbl, c); if (o2.notes < best.notes || (o2.notes === best.notes && o2.semis < best.semis)) return o2; }
  return best;
}
const holdsWith = (pieces, clef, c) => excessOn(pieces, clef, 0, c).beyond === 0 || excessOn(pieces, clef, LINES[clef][0], c).beyond === 0;
// the clef a bar's lower-staff pieces want (see header): "bass" | "treble" | null (empty, or neither clef holds them)
export function clefWant(p2, params = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  if (!p2.length) return null;
  const fb = holdsWith(p2, "bass", c), ft = holdsWith(p2, "treble", c);
  if (fb && !ft) return "bass";
  if (ft && !fb) return "treble";
  if (fb && ft) return p2.every((x) => x.note >= c.clefUp) ? "treble" : "bass";
  return null;
}

export function initialClefState() { return { clef2: "bass", held: Infinity, prevClef2: null, prevWant: null }; }

// one bar: -> { row, state }. next: the next bar ({ voices }) or null (unknown or none)
export function clefStep(state, m, next, params = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  const { p1, p2 } = piecesOf(m);
  const want = clefWant(p2, c);
  const S = state.clef2, O = OTHER_CLEF(S);
  const confirm = c.clefLookahead ? (next ? clefWant(piecesOf(next).p2, c) : null) : state.prevWant;
  let clef2 = S, held = state.held;
  if (want === O && confirm === O && held >= c.clefBars) { clef2 = O; held = 0; }
  held++;
  const s1 = octaveOn(p1, "treble", c), s2 = octaveOn(p2, clef2, c);
  const change = state.prevClef2 == null || clef2 === state.prevClef2 ? null : holdsWith(p2, S, c) ? "bars" : "range";
  const reason = (s, staff) => {
    if (!s.beyond) return null;
    if (staff === 2 && octaveOn(p2, OTHER_CLEF(clef2), c).beyond === 0) return "excursion";
    return s.notes === 1 ? "single" : "span";
  };
  const row = {
    index: m.index, clefs: { 1: "treble", 2: clef2 }, octave: { 1: s1.oct, 2: s2.oct }, change, want,
    beyond: { 1: s1.beyond, 2: s2.beyond }, beyondNotes: { 1: s1.notes, 2: s2.notes }, overflow: { 1: reason(s1, 1), 2: reason(s2, 2) },
  };
  return { row, state: { clef2, held, prevClef2: clef2, prevWant: want } };
}

// Live: commit(bar, next) decides a bar once, with the next bar as known then, and keeps the state; preview(bars) decides
// later bars from the committed state without committing.
export function createClefTracker(params = {}) {
  const c = { ...HANDS_PARAMS, ...params };
  let st = initialClefState();
  return {
    commit(m, next = null) { const r = clefStep(st, m, next, c); st = r.state; return r.row; },
    preview(ms) { let s = st; return ms.map((m, i) => { const r = clefStep(s, m, ms[i + 1] ?? null, c); s = r.state; return r.row; }); },
    state: () => ({ ...st }),
  };
}

// Clefs and octave lines per bar over a finished sequence (hindsight: each bar sees the next).
// measures: [{ index, voices: [{ staff, notes: [{ note, id? }] }] }] ascending.
// -> [{ index, clefs: { 1: "treble", 2: "bass" | "treble" }, octave: { 1: 0 | 8 | 15, 2: 0 | 8 | 15 | -8 | -15 },
//       change: null | "bars" (the old clef still held the bar) | "range" (it did not), want, beyond: { 1, 2 },
//       beyondNotes: { 1, 2 }, overflow: { 1, 2 }: null | "excursion" | "single" | "span" }]
export function clefsAndOctaves(measures, params = {}) {
  const t = createClefTracker(params);
  return measures.map((m, i) => t.commit(m, measures[i + 1] ?? null));
}
