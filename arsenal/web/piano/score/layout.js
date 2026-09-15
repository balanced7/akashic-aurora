// Ribbon geometry for live sheet music: arsenal/web/piano/score/layout.js (pure ES module: no DOM, no clock).
// Slice LS5 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 2.1, 5.1, 7.3), amended
// by plan-amendments.md C6 (tape collision push), C15 (a settled beat widens to its content), C16 (9:16 band bounds) and
// section 0 rule 1 (constant glyph boxes in staff spaces, never measureText).
//
//   const L = createLayout({ framing: "9:16" });           // band, playhead, staff tops, tape speed, D_max
//   const P = createTapePlacer(L);  P.place(t_ms, widthPx)  // C6: x of a new tape column (placed columns never move)
//   const m = modelBar(bar, { meter, spelledOf, clefs, octave, fifths });  // a transcriber bar as a drawable model
//   const g = layoutBar(m, L, { widen: true });            // columns, beats, heads, accidentals, dots, rests, boxes
//   overlaps(g.boxes) / tapeOverlaps(columns, L)           // LR11g glyph collisions / LR11f tape head overlaps
//
// Units. s = L.sp px per staff space (15). Tiles are painted in band-local coordinates: x from the tile's left edge, y from
// the band's top (L.band.y0). Staff steps count diatonic positions above the staff's middle line (a line), so the top
// line is step 4, the first ledger line above is step 6, and y = staffTop + 2s - step * s / 2.
//
// Band (9:16, C16): x 110-940, bottom 1436 on the 1080 x 1920 canvas; the playhead at 70% of the band width (x 691). The
// band stacks, top to bottom: 4 s of ledger room, the treble staff (4 s), a 6 s gap, the bass staff (4 s), 4 s of ledger
// room, a 2 s pedal lane: 24 s = 360 px, so y 1076-1436. The header row sits above it. 16:9 is provisional (LQ4 decides
// the placement): a full-width bottom band.
//
// Tape (C6). One time axis for both staves; each onset group is one column of width 1.4 s, + 1.0 s if a head in it shows
// an accidental, + 1.18 s if it holds a second; across the staves the wider sets it. Placement with debt D (px right of
// nominal time): want = nominal(t) + D_prev, min = x_prev + w_prev; push to min when want < min, else reclaim half the
// spare space (x = want - min(D_prev, (want - min) / 2)); D is clamped to [0, D_max] and when the clamp binds x = nominal
// + D_max (an overlap, allowed and counted). D_max = min(180 px, band right - playhead - 2 columns). Ticks every 1 s at
// nominal + D interpolated between neighbouring columns; a duration line ends at the warped x of its sound end.
//
// Settled bars (C15). A bar's columns are its distinct note and rest positions over both staves. A column's width is,
// on the wider staff: accidental columns x 1.0 s + head columns x 1.18 s (2 when a second or a unison between voices
// displaces a head) + 0.6 s per augmentation dot + 0.8 s for an unbeamed flag on an up stem, + 0.4 s padding; a
// rest-only column is its rest glyph + 0.4 s. A beat's minimum width is the sum over its columns, never below 96 px
// (max(4 slots x 1.6 s, 5 s) at s = 15). The house engraver's reading of C15's "+ 1.0 if accidental": one per accidental
// column (a chord's accidentals stack into columns 3 s of pitch apart), plus the dot and flag terms, since otherwise a
// dotted or flagged column collides with the next (LR11g). Heads sit at their slot, x = beat x + pad + frac x (W - pad -
// last column width), pushed right past the previous column; widen: true moves the next beat line past the last
// column (a widened beat), widen: false keeps the beat lines fixed (the open bar). A beat whose content fits its 96 px
// places every head where the open bar placed it (LR11e: 0 shift by construction on beats that did not widen).

export const LAYOUT_API = "arsenal.piano.score.layout/v0";

export const LAYOUT_PARAMS = Object.freeze({
  sp: 15, beatMinSp: 6.4, tapePxPerSec: 120, playheadShare: 0.7,
  colSp: 1.4, accSp: 1.0, secondSp: 1.18, headWSp: 1.18, headHSp: 1.0, shrinkSp: 0.1, padSp: 0.4, dotSp: 0.6, flagSp: 0.8,
  slotPadSp: 0.2, dMaxPx: 180, tapeTickMs: 1000, accStepGap: 6, clefChangeSp: 2.6, keySigSp: 1.0,
  // band stack in staff spaces, top to bottom
  ledgerAboveSp: 4, staffGapSp: 6, ledgerBelowSp: 4, pedalLaneSp: 2,
});

export const FRAMINGS = Object.freeze({
  "9:16": Object.freeze({ width: 1080, height: 1920, x0: 110, x1: 940, bottom: 1436, provisional: false }),
  "16:9": Object.freeze({ width: 1920, height: 1080, x0: 120, x1: 1800, bottom: 1060, provisional: true }),
});

// Diatonic number of each clef's middle line (C4 = 28, as spell.js spellMidi counts): B4 in treble, D3 in bass.
export const CLEF_MID = Object.freeze({ treble: 34, bass: 22 });

// Glyph boxes in staff spaces (Bravura's bounding boxes, rounded): w, and extent above (top) and below (bot) the glyph's
// anchor line (a head's centre line; an accidental's head line; a rest's staff position).
export const GLYPH = Object.freeze({
  head: Object.freeze({ black: { w: 1.18, top: 0.5, bot: 0.5 }, half: { w: 1.18, top: 0.5, bot: 0.5 }, whole: { w: 1.69, top: 0.5, bot: 0.5 } }),
  acc: Object.freeze({ "2": { w: 1.0, top: 0.5, bot: 0.5 }, "1": { w: 1.0, top: 1.4, bot: 1.4 }, "0": { w: 0.68, top: 1.35, bot: 1.35 }, "-1": { w: 0.9, top: 1.75, bot: 0.65 }, "-2": { w: 1.64, top: 1.75, bot: 0.65 } }),
  rest: Object.freeze({ whole: { w: 1.13, top: 0, bot: 0.5 }, half: { w: 1.13, top: 0.5, bot: 0 }, quarter: { w: 1.08, top: 1.4, bot: 1.4 }, eighth: { w: 0.99, top: 1.0, bot: 1.0 }, "16th": { w: 1.27, top: 1.0, bot: 2.0 }, "32nd": { w: 1.4, top: 2.0, bot: 2.0 }, "64th": { w: 1.5, top: 2.0, bot: 3.0 } }),
  dot: Object.freeze({ w: 0.4, top: 0.2, bot: 0.2 }),
  flag: Object.freeze({ w: 1.05, h: 3.2 }),
});

const FLAGS = Object.freeze({ eighth: 1, "16th": 2, "32nd": 3, "64th": 4 });
export const flagCount = (type) => FLAGS[type] || 0;
export const headKind = (type) => (type === "whole" ? "whole" : type === "half" ? "half" : "black");

// ------------------------------------------------------------------------------------------------ framing ---
export function createLayout({ framing = "9:16", params = {} } = {}) {
  const c = { ...LAYOUT_PARAMS, ...params };
  const F = FRAMINGS[framing] || FRAMINGS["9:16"];
  const sp = c.sp;
  const bandSp = c.ledgerAboveSp + 4 + c.staffGapSp + 4 + c.ledgerBelowSp + c.pedalLaneSp;
  const y1 = F.bottom, y0 = y1 - bandSp * sp;
  const playheadX = F.x0 + c.playheadShare * (F.x1 - F.x0);
  const staffTop = { 1: c.ledgerAboveSp * sp, 2: (c.ledgerAboveSp + 4 + c.staffGapSp) * sp };
  return {
    api: LAYOUT_API, framing: F === FRAMINGS[framing] ? framing : "9:16", provisional: F.provisional,
    width: F.width, height: F.height, sp,
    band: { x0: F.x0, x1: F.x1, y0, y1, w: F.x1 - F.x0, h: y1 - y0 },
    playheadX,
    header: { x: F.x0, y: y0 - 3.2 * sp, h: 2.6 * sp },
    staffTop, staffBottom: { 1: staffTop[1] + 4 * sp, 2: staffTop[2] + 4 * sp },
    pedalY: (bandSp - c.pedalLaneSp / 2) * sp,
    tileH: y1 - y0,
    beatMinPx: c.beatMinSp * sp,
    v: c.tapePxPerSec / 1000,                                         // px per ms
    dMax: Math.min(c.dMaxPx, F.x1 - playheadX - 2 * c.colSp * sp),
    params: c,
  };
}

// ------------------------------------------------------------------------------------------ pitch geometry ---
export function staffStep(spelled, clef, octave = 0) {
  const d = spelled.octave * 7 + spelled.letter - (octave === 8 ? 7 : octave === -8 ? -7 : 0);
  return d - CLEF_MID[clef];
}
export const stepY = (L, staff, step) => L.staffTop[staff] + 2 * L.sp - (step * L.sp) / 2;
// ledger line steps a head at `step` needs (even steps beyond the staff, from the staff outwards)
export function ledgerSteps(step) {
  const out = [];
  if (step >= 6) for (let s = 6; s <= step; s += 2) out.push(s);
  if (step <= -6) for (let s = -6; s >= step; s -= 2) out.push(s);
  return out;
}

// Accidentals of a key signature by letter (C D E F G A B), from its fifths (marks.js fifthsOf).
const SHARP_LETTERS = [3, 0, 4, 1, 5, 2, 6], FLAT_LETTERS = [6, 2, 5, 1, 4, 0, 3];
export function sigFromFifths(fifths = 0) {
  const sig = [0, 0, 0, 0, 0, 0, 0];
  const n = Math.min(7, Math.abs(fifths | 0));
  for (let i = 0; i < n; i++) sig[(fifths > 0 ? SHARP_LETTERS : FLAT_LETTERS)[i]] = fifths > 0 ? 1 : -1;
  return sig;
}
// the signature's accidentals in writing order with their staff steps per clef: treble sharps F5 C5 G5 D5 A4 E5 B4, flats
// B4 E5 A4 D5 G4 C5 F4; bass the same letters two octaves and a third lower (F3 C3 G3 D3 A2 E3 B2; B2 E3 A2 D3 G2 C3 F2)
const SHARP_STEPS = { treble: [4, 1, 5, 2, -1, 3, 0], bass: [2, -1, 3, 0, -3, 1, -2] };
const FLAT_STEPS = { treble: [0, 3, -1, 2, -2, 1, -3], bass: [-2, 1, -3, 0, -4, -1, -5] };
export function keySigGlyphs(fifths, clef) {
  const n = Math.min(7, Math.abs(fifths | 0));
  const steps = (fifths > 0 ? SHARP_STEPS : FLAT_STEPS)[clef];
  return Array.from({ length: n }, (_, i) => ({ acc: fifths > 0 ? 1 : -1, step: steps[i], x: i }));
}

// ---------------------------------------------------------------------------------------------- tape (C6) ---
// heads: [{ staff, step, acc (drawn accidental value or null) }] -> px
export function tapeColumnWidth(heads, L) {
  const c = L.params;
  let w = 0;
  for (const staff of [1, 2]) {
    const hs = heads.filter((h) => h.staff === staff);
    if (!hs.length) continue;
    const steps = hs.map((h) => h.step).sort((a, b) => a - b);
    let second = false;
    for (let i = 1; i < steps.length; i++) if (steps[i] - steps[i - 1] === 1) second = true;
    const acc = hs.some((h) => h.acc != null);
    w = Math.max(w, c.colSp + (acc ? c.accSp : 0) + (second ? c.secondSp : 0));
  }
  return (w || c.colSp) * L.sp;
}

// One onset group as a tape column's heads: items [{ id, note, staff, spelled: { letter, acc, octave } | null }] ->
// { heads: [{ id, note, staff, step, acc, dx }], w (C6 column width, px), accW (px before the head column) }. A head
// shows its accidental when its spelling differs from the signature (tape has no bar to carry one); the upper head of a
// second moves right one head width (dx).
export function tapeHeads(items, L, { clefs = { 1: "treble", 2: "bass" }, fifths = 0 } = {}) {
  const sig = sigFromFifths(fifths ?? 0);
  const heads = items.map((it) => {
    const s = it.spelled, clef = clefs[it.staff] || (it.staff === 1 ? "treble" : "bass");
    return { id: it.id, note: it.note, staff: it.staff, step: s ? staffStep(s, clef, 0) : 0, acc: s && s.acc !== sig[s.letter] ? s.acc : null, dx: 0 };
  });
  for (const staff of [1, 2]) {
    const hs = heads.filter((h) => h.staff === staff).sort((a, b) => a.step - b.step);
    for (let i = 1; i < hs.length; i++) if (hs[i].step - hs[i - 1].step <= 1 && !hs[i - 1].dx) hs[i].dx = L.params.secondSp * L.sp;
  }
  return { heads, w: tapeColumnWidth(heads, L), accW: heads.some((h) => h.acc != null) ? L.params.accSp * L.sp : 0 };
}

// A causal placer (C6). The nominal x of time t is x0 + (t - t0) * v; reanchor() starts a new tape run after a bar.
export function createTapePlacer(L, { x0 = 0, t0 = 0 } = {}) {
  let ax = x0, at = t0, prev = null;
  const cols = [];
  const nominal = (t) => ax + (t - at) * L.v;
  function place(t, w) {
    const nom = nominal(t);
    const Dp = prev && prev.run === runId ? prev.D : 0;
    const min = prev && prev.run === runId ? prev.x + prev.w : ax;
    const want = nom + Dp;
    let x = want < min ? min : want - Math.min(Dp, 0.5 * (want - min));
    let D = x - nom, clamped = false;
    if (D < 0) { D = 0; x = nom; }
    if (D > L.dMax) { D = L.dMax; x = nom + L.dMax; clamped = true; }
    const col = { t, x, w, D, clamped, run: runId, nominal: nom };
    cols.push(col); prev = col;
    if (cols.length > 4096) cols.splice(0, 2048);
    return col;
  }
  let runId = 0;
  function reanchor(x, t) { ax = Math.max(x, prev ? prev.x + prev.w : x); at = t; runId++; }
  // debt at time t: linear between the neighbouring columns of the current run, the last column's debt after it
  function debtAt(t) {
    let lo = null, hi = null;
    for (let i = cols.length - 1; i >= 0; i--) { const k = cols[i]; if (k.run !== runId) break; if (k.t <= t) { lo = k; hi = cols[i + 1] && cols[i + 1].run === runId ? cols[i + 1] : null; break; } hi = k; }
    if (!lo) return 0;
    if (!hi) return lo.D;
    return lo.D + ((hi.D - lo.D) * (t - lo.t)) / Math.max(1e-9, hi.t - lo.t);
  }
  return {
    place, reanchor, nominal, debtAt,
    warpX: (t) => nominal(t) + debtAt(t),
    end: () => (prev ? Math.max(prev.x + prev.w, ax) : ax),
    anchor: () => ({ x: ax, t: at, run: runId }),
    columns: () => cols,
  };
}

// LR11f: overlapping heads on one staff in different columns. columns: [{ x, heads: [{ staff, step, dx? }] }], heads
// are 1.18 x 1.0 s boxes at x + (dx || 0), shrunk 0.1 s per side.
export function tapeOverlaps(columns, L) {
  const c = L.params, sp = L.sp, w = (c.headWSp - 2 * c.shrinkSp) * sp, h = (c.headHSp - 2 * c.shrinkSp) * sp;
  const items = [];
  columns.forEach((col, ci) => { for (const hd of col.heads) items.push({ ci, staff: hd.staff, x: col.headX ?? col.x, y: -hd.step * sp / 2 }); });
  items.sort((a, b) => a.x - b.x);
  let n = 0;
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length && items[j].x - items[i].x < w; j++) {
      const a = items[i], b = items[j];
      if (a.ci !== b.ci && a.staff === b.staff && Math.abs(a.y - b.y) < h) n++;
    }
  }
  return n;
}

// ------------------------------------------------------------------------------------------------ bar model ---
// bar: a transcriber bar (index.js bars()/view.bars: { index, state, kind, rev, start_ms, end_ms, beats, measure }) or a
// score measure ({ index, voices, beams, tuplets, ... }). spelledOf(piece) -> { letter, acc, octave } (the injected
// speller's answer for the piece's MIDI note). clefs { 1, 2 }, octave { 1, 2 }: hands.js clefsAndOctaves for the bar.
// fifths: the signature in force; keyChange: the fifths change at this bar line (or null); clefChange from hands.js.
export function modelBar(bar, { meter, spelledOf, clefs = { 1: "treble", 2: "bass" }, octave = { 1: 0, 2: 0 }, fifths = 0, keyChange = null, clefChange = null } = {}) {
  const ms = bar.measure || bar;
  const sig = sigFromFifths(fifths);
  const BT = meter.beatTicks;
  const beats = bar.beats ?? Math.ceil((ms.barTicks ?? meter.barTicks) / BT);
  const byStaffVoices = { 1: new Set(), 2: new Set() };
  for (const v of ms.voices) if (v.notes.length) byStaffVoices[v.staff].add(v.voice);
  const accState = new Map();
  const voices = [];
  // accidentals last to the end of the bar per staff, letter and octave (across the staff's voices, never across staves:
  // an F sharp in the treble does not sharpen the bass's F); a tied-to piece never reprints one (plan 6.5)
  const pieces = [];
  for (const v of ms.voices) for (const p of v.notes) pieces.push({ v, p });
  pieces.sort((a, b) => a.p.pos - b.p.pos || a.p.note - b.p.note);
  const accOf = new Map();
  for (const { v, p } of pieces) {
    const s = spelledOf(p);
    if (!s) { accOf.set(p, { s: null, acc: null }); continue; }
    const key = v.staff + "/" + s.letter + "/" + s.octave;
    const cur = accState.has(key) ? accState.get(key) : sig[s.letter];
    let acc = null;
    if (!p.tieStop && s.acc !== cur) { acc = s.acc; accState.set(key, s.acc); }
    accOf.set(p, { s, acc });
  }
  for (const v of ms.voices) {
    const clef = clefs[v.staff] || (v.staff === 1 ? "treble" : "bass"), oct = octave[v.staff] || 0;
    const two = byStaffVoices[v.staff].size > 1;
    const notes = v.notes.map((p) => {
      const { s, acc } = accOf.get(p);
      const step = s ? staffStep(s, clef, oct) : 0;
      return { id: p.id, note: p.note, pos: p.pos, dur: p.dur, type: p.type, dots: p.dots || 0, tieStart: !!p.tieStart, tieStop: !!p.tieStop, barTie: !!p.barTie, staccato: !!p.staccato, step, acc, letter: s ? s.letter : null, spelled: !!s };
    });
    let stemUp;
    if (two) stemUp = v.voice === 1 || v.voice === 3;
    else { const avg = notes.length ? notes.reduce((a, n) => a + n.step, 0) / notes.length : 0; stemUp = avg < 0; }
    voices.push({ voice: v.voice, staff: v.staff, stemUp, twoVoices: two, notes, rests: (v.rests || []).map((r) => ({ ...r, dots: r.dots || 0 })) });
  }
  return {
    index: bar.index, state: bar.state ?? null, kind: bar.kind ?? null, rev: bar.rev ?? 0,
    beats, beatTicks: BT, barTicks: ms.barTicks ?? beats * BT, compound: !!meter.compound, meter: meter.label,
    clefs: { 1: clefs[1] || "treble", 2: clefs[2] || "bass" }, octave: { 1: octave[1] || 0, 2: octave[2] || 0 }, fifths, keyChange, clefChange,
    voices, beams: ms.beams || [], tuplets: ms.tuplets || [], loose: ms.loose || [],
  };
}

// ----------------------------------------------------------------------------------------------- bar layout ---
// -> { width, lead, beats: [{ x, w, minW, widened }], columns: [{ pos, beat, x, w, headX }], heads, accidentals, dots,
//      rests, stems (per voice chord), boxes, overflowPx }
// push: false places every column at its slot with no push (C15's "widening off" report for LR11g).
export function layoutBar(model, L, { widen = true, beatPx = null, push = true } = {}) {
  const c = L.params, sp = L.sp, BT = model.beatTicks, B = beatPx ?? L.beatMinPx;
  // beams tell which pieces are unbeamed
  const beamed = new Set();
  for (const bm of model.beams) for (const id of bm.ids) beamed.add(bm.voice + ":" + id);
  // columns by position
  const cols = new Map();
  const colOf = (pos) => { if (!cols.has(pos)) cols.set(pos, { pos, beat: Math.floor(pos / BT), chords: [], rests: [] }); return cols.get(pos); };
  for (const v of model.voices) {
    const byPos = new Map();
    for (const n of v.notes) { if (!byPos.has(n.pos)) byPos.set(n.pos, []); byPos.get(n.pos).push(n); }
    for (const [pos, ns] of byPos) colOf(pos).chords.push({ voice: v.voice, staff: v.staff, stemUp: v.stemUp, twoVoices: v.twoVoices, notes: ns.sort((a, b) => a.step - b.step) });
    for (const r of v.rests) colOf(r.pos).rests.push({ ...r, voice: v.voice, staff: v.staff, stemUp: v.stemUp, twoVoices: v.twoVoices });
  }
  const order = [...cols.values()].sort((a, b) => a.pos - b.pos);
  // per column: head offsets (seconds, voice unisons), accidental columns, dots, flags -> width in s
  for (const col of order) {
    let accColsMax = 0, widthSp = 0;
    col.staff = {};
    for (const staff of [1, 2]) {
      const chords = col.chords.filter((k) => k.staff === staff);
      const rests = col.rests.filter((r) => r.staff === staff);
      let minOff = 0, maxOff = 0, dots = 0, flag = false;
      for (const ch of chords) {
        // seconds inside a chord: stem up puts the upper head of a second right of the stem, stem down the lower left
        const ns = ch.stemUp ? ch.notes : [...ch.notes].reverse();
        let last = null;
        for (const n of ns) {
          n.off = last && !last.displaced && Math.abs(n.step - last.step) <= 1 ? (ch.stemUp ? 1 : -1) : 0;
          n.displaced = n.off !== 0;
          last = n;
        }
        for (const n of ch.notes) dots = Math.max(dots, n.dots);
        if (ch.stemUp && ch.notes.some((n) => flagCount(n.type) && !beamed.has(ch.voice + ":" + n.id))) flag = true;
      }
      // two voices at one position: when their heads touch, the down-stem chord moves right past the up-stem chord's
      // rightmost head (its own left-displaced heads included) and past the up chord's flag
      if (chords.length > 1) {
        const up = chords.find((k) => k.stemUp), down = chords.find((k) => !k.stemUp);
        if (up && down && down.notes.some((d) => up.notes.some((u) => Math.abs(u.step - d.step) <= 1))) {
          const upRight = Math.max(...up.notes.map((n) => n.off));
          const downLeft = Math.min(...down.notes.map((n) => n.off));
          const upFlag = up.notes.some((n) => flagCount(n.type) && !beamed.has(up.voice + ":" + n.id));
          const shift = upRight + 1 - downLeft + (upFlag ? c.flagSp / c.headWSp : 0);
          for (const n of down.notes) n.off += shift;
        }
      }
      for (const ch of chords) for (const n of ch.notes) { minOff = Math.min(minOff, n.off); maxOff = Math.max(maxOff, n.off); }
      // accidentals: top down into the leftmost column with no accidental within accStepGap steps
      const accs = chords.flatMap((k) => k.notes.filter((n) => n.acc != null)).sort((a, b) => b.step - a.step);
      const accCols = [];
      for (const n of accs) {
        let k = 0;
        while (k < accCols.length && accCols[k].some((s) => Math.abs(s - n.step) < c.accStepGap)) k++;
        if (k === accCols.length) accCols.push([]);
        accCols[k].push(n.step); n.accCol = k;
      }
      for (const r of rests) dots = Math.max(dots, r.dots);
      const headCols = chords.length ? maxOff - minOff + 1 : 0;
      const restW = rests.length ? Math.max(...rests.map((r) => (GLYPH.rest[r.type] || GLYPH.rest.quarter).w)) : 0;
      const w = accCols.length * c.accSp + Math.max(headCols * c.headWSp, restW) + dots * c.dotSp + (flag ? c.flagSp : 0);
      col.staff[staff] = { minOff, maxOff, accCols: accCols.length, dots, flag, headCols, dotY: [] };
      accColsMax = Math.max(accColsMax, accCols.length);
      widthSp = Math.max(widthSp, w);
    }
    col.minOff = Math.min(col.staff[1].minOff, col.staff[2].minOff);
    col.accW = accColsMax * c.accSp * sp + (col.minOff < 0 ? -col.minOff * c.headWSp * sp : 0);
    col.w = (widthSp + c.padSp) * sp;
  }
  // lead-in: a clef change and a key change at the bar line
  const lead = ((model.clefChange ? c.clefChangeSp : 0) + (model.keyChange != null ? Math.abs(model.keyChange) * c.keySigSp + 1.2 : 0)) * sp;
  const beats = [];
  let x = lead, prevRight = lead, overflow = 0;
  for (let j = 0; j < model.beats; j++) {
    const inBeat = order.filter((k) => k.beat === j);
    const minW = inBeat.reduce((a, k) => a + k.w, 0);
    const W = widen ? Math.max(B, minW) : B;
    const lastW = inBeat.length ? inBeat[inBeat.length - 1].w : 0;
    const pad = c.slotPadSp * sp;
    for (const k of inBeat) {
      const frac = (k.pos - j * BT) / BT;
      const slotHead = x + pad + frac * Math.max(0, W - pad - lastW) + k.accW;
      let left = slotHead - k.accW;
      if (push && left < prevRight) left = prevRight;
      k.x = left; k.headX = left + k.accW;
      prevRight = left + k.w;
    }
    let next = x + W;
    let widened = W > B;
    if (prevRight > next) { if (widen) { next = prevRight; widened = true; } else overflow = Math.max(overflow, prevRight - next); }
    beats.push({ x, w: next - x, minW, widened, columns: inBeat.length });
    x = next;
    if (!widen) prevRight = Math.max(prevRight, lead);
  }
  const width = x;
  // glyphs and boxes
  const heads = [], accidentals = [], dots = [], rests = [], stems = [], boxes = [];
  const shrink = c.shrinkSp * sp;
  const box = (kind, staff, owner, bx, by, bw, bh, extra = {}) => boxes.push({ kind, staff, owner, x: bx, y: by, w: bw, h: bh, ...extra });
  for (const col of order) {
    for (const ch of col.chords) {
      const st = col.staff[ch.staff];
      const rightmost = st ? st.maxOff : Math.max(...ch.notes.map((n) => n.off));
      for (const n of ch.notes) {
        const g = GLYPH.head[headKind(n.type)];
        const hx = col.headX + n.off * c.headWSp * sp, hy = stepY(L, ch.staff, n.step);
        const owner = "h" + ch.staff + ":" + col.pos + ":" + n.id;
        heads.push({ id: n.id, note: n.note, staff: ch.staff, voice: ch.voice, pos: col.pos, x: hx, y: hy, step: n.step, kind: headKind(n.type), type: n.type, tieStart: n.tieStart, tieStop: n.tieStop, barTie: n.barTie, staccato: n.staccato, stemUp: ch.stemUp, dur: n.dur, off: n.off });
        box("head", ch.staff, owner, hx, hy - g.top * sp, g.w * sp, (g.top + g.bot) * sp, { id: n.id });
        if (n.acc != null) {
          const ga = GLYPH.acc[String(Math.max(-2, Math.min(2, n.acc)))];
          const ax = col.headX - (col.minOff < 0 ? -col.minOff * c.headWSp * sp : 0) - (n.accCol + 1) * c.accSp * sp + (c.accSp - ga.w) * sp;
          accidentals.push({ id: n.id, staff: ch.staff, x: ax, y: hy, acc: n.acc });
          box("accidental", ch.staff, owner, ax, hy - ga.top * sp, ga.w * sp, (ga.top + ga.bot) * sp, { id: n.id });
        }
        if (n.dots) {
          // dots after the rightmost head of the staff column; on a line a dot moves into the space above (below for a
          // lower voice), and away from a dot another voice already put at that height
          const onLine = n.step % 2 === 0;
          const lower = ch.twoVoices && !ch.stemUp;
          let dy = hy + (onLine ? (lower ? sp / 2 : -sp / 2) : 0);
          for (let k = 0; k < 4 && st && st.dotY.some((y) => Math.abs(y - dy) < 0.5 * sp); k++) dy += lower ? sp : -sp;
          if (st) st.dotY.push(dy);
          for (let d = 0; d < n.dots; d++) {
            const dx = col.headX + (rightmost + 1) * c.headWSp * sp + 0.25 * sp + d * c.dotSp * sp;
            dots.push({ id: n.id, staff: ch.staff, x: dx, y: dy });
            box("dot", ch.staff, owner, dx, dy - GLYPH.dot.top * sp, GLYPH.dot.w * sp, (GLYPH.dot.top + GLYPH.dot.bot) * sp, { id: n.id });
          }
        }
      }
      const stemmed = ch.notes.filter((n) => n.type && n.type !== "whole");
      if (stemmed.length) {
        const ys = ch.notes.map((n) => stepY(L, ch.staff, n.step));
        const top = Math.min(...ys), bottom = Math.max(...ys);
        // the stem sits on the main head column (non-displaced heads share one offset: 0, or 1 when the voice moved right)
        const main = ch.notes.find((n) => !n.displaced) || ch.notes[0];
        const baseOff = main.off - (main.displaced ? (ch.stemUp ? 1 : -1) : 0);
        const sx = col.headX + (ch.stemUp ? baseOff + 1 : baseOff) * c.headWSp * sp;
        const type = stemmed.reduce((t, n) => (flagCount(n.type) > flagCount(t) ? n.type : t), stemmed[0].type);
        const ids = ch.notes.map((n) => n.id);
        const beamedHere = ids.some((id) => beamed.has(ch.voice + ":" + id));
        // stems lengthen 0.75 s per extra flag or beam, and 1 s more when a flag hangs over heads right of an up stem
        const fl = flagCount(type), rightOfStem = ch.stemUp && st && st.maxOff > baseOff;
        const len = (3.5 + 0.75 * Math.max(0, fl - 1) + (fl && !beamedHere && rightOfStem ? 1.0 : 0)) * sp;
        const stem = { voice: ch.voice, staff: ch.staff, pos: col.pos, x: sx, up: ch.stemUp, yHead: ch.stemUp ? bottom : top, yEnd: ch.stemUp ? top - len : bottom + len, type, flags: flagCount(type), beamed: beamedHere, ids };
        stems.push(stem);
        if (stem.flags && !beamedHere) {
          const fh = (GLYPH.flag.h + 0.75 * Math.max(0, stem.flags - 1)) * sp;
          const fy = ch.stemUp ? stem.yEnd : stem.yEnd - fh;
          box("flag", ch.staff, "h" + ch.staff + ":" + col.pos + ":" + ids[0], sx, fy, GLYPH.flag.w * sp, fh, { voice: ch.voice });
        }
      }
    }
    for (const r of col.rests) {
      const g = GLYPH.rest[r.type] || GLYPH.rest.quarter;
      let step = r.type === "whole" ? 2 : 0;
      if (r.twoVoices) step += r.stemUp ? 4 : -4;
      const rx = col.headX;
      const owner = "r" + r.staff + ":" + col.pos + ":" + r.voice;
      // move away from other voices' heads in this column (2 steps at a time, 3 tries)
      const headBoxes = boxes.filter((b) => b.kind !== "rest" && b.staff === r.staff && b.x < rx + g.w * sp && rx < b.x + b.w);
      for (let k = 0; k < 3; k++) {
        const ry = stepY(L, r.staff, step);
        const bb = { x: rx + shrink, y: ry - g.top * sp + shrink, w: g.w * sp - 2 * shrink, h: (g.top + g.bot) * sp - 2 * shrink };
        if (!headBoxes.some((h) => intersects(bb, { x: h.x + shrink, y: h.y + shrink, w: h.w - 2 * shrink, h: h.h - 2 * shrink }))) break;
        step += r.stemUp || !r.twoVoices ? 2 : -2;
      }
      const ry = stepY(L, r.staff, step);
      rests.push({ staff: r.staff, voice: r.voice, pos: r.pos, x: rx, y: ry, step, type: r.type, dots: r.dots, dur: r.dur });
      box("rest", r.staff, owner, rx, ry - g.top * sp, g.w * sp, (g.top + g.bot) * sp);
      for (let d = 0; d < r.dots; d++) {
        const dx = rx + g.w * sp + 0.25 * sp + d * c.dotSp * sp, dy = ry - (step % 2 === 0 ? sp / 2 : 0);
        dots.push({ staff: r.staff, x: dx, y: dy, rest: true });
        box("dot", r.staff, owner, dx, dy - GLYPH.dot.top * sp, GLYPH.dot.w * sp, (GLYPH.dot.top + GLYPH.dot.bot) * sp);
      }
    }
  }
  return { width, lead, beats, columns: order.map((k) => ({ pos: k.pos, beat: k.beat, x: k.x, w: k.w, headX: k.headX })), heads, accidentals, dots, rests, stems, boxes, overflowPx: overflow, widen };
}

function intersects(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }

// LR11g: glyph boxes of different owners on one staff that intersect after shrinking 0.1 s per side.
export function overlaps(boxes, L, { kinds = ["head", "accidental", "dot", "rest", "flag"] } = {}) {
  const s = L.params.shrinkSp * L.sp;
  const bs = boxes.filter((b) => kinds.includes(b.kind)).map((b) => ({ ...b, x: b.x + s, y: b.y + s, w: b.w - 2 * s, h: b.h - 2 * s })).sort((a, b) => a.x - b.x);
  const pairs = [];
  for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length && bs[j].x < bs[i].x + bs[i].w; j++) {
    const a = bs[i], b = bs[j];
    if (a.staff === b.staff && a.owner !== b.owner && intersects(a, b)) pairs.push([a, b]);
  }
  return pairs;
}

// Head x shift between two layouts of one bar (LR11e): matched by note id and position; beats widened in `after` are
// reported apart. -> { unwidened: { n, meanPx, meanSp }, widened: { n, meanPx, meanSp }, moved: n (pos changed) }
export function headShift(before, after, L) {
  const at = new Map(before.heads.map((h) => [h.id + ":" + h.pos + ":" + h.staff, h]));
  const byId = new Set(before.heads.map((h) => h.id));
  const acc = { unwidened: [0, 0], widened: [0, 0], beatLocal: [0, 0] };
  let moved = 0;
  const BT = after.beatTicks || before.beatTicks || 24;
  for (const h of after.heads) {
    const b = at.get(h.id + ":" + h.pos + ":" + h.staff);
    if (!b) { if (byId.has(h.id)) moved++; continue; }
    const j = Math.floor(h.pos / BT), beat = after.beats[j], beatB = before.beats[j];
    const k = beat && beat.widened ? "widened" : "unwidened";
    acc[k][0]++; acc[k][1] += Math.abs(h.x - b.x);
    // beat-local: the head against its own beat line (a widened beat earlier in the bar moves later beat lines)
    if (k === "unwidened" && beat && beatB) { acc.beatLocal[0]++; acc.beatLocal[1] += Math.abs((h.x - beat.x) - (b.x - beatB.x)); }
  }
  const out = (k) => ({ n: acc[k][0], meanPx: acc[k][0] ? acc[k][1] / acc[k][0] : 0, meanSp: acc[k][0] ? acc[k][1] / acc[k][0] / L.sp : 0 });
  return { unwidened: out("unwidened"), widened: out("widened"), beatLocal: out("beatLocal"), moved };
}

// Time -> x inside a bar block: beat j spans [beats[j].x, + w] over equal beat durations of the bar.
export function barXAt(block, t) {
  const beatMs = (block.fullEnd_ms ?? block.end_ms) - block.start_ms;
  const per = beatMs / Math.max(1, block.beats.length);
  const f = (t - block.start_ms) / Math.max(1e-9, per);
  const j = Math.max(0, Math.min(block.beats.length - 1, Math.floor(f)));
  const b = block.beats[j];
  return block.x0 + b.x + Math.max(0, Math.min(1, f - j)) * b.w;
}
