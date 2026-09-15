// The live ribbon model: arsenal/web/piano/score/ribbon.js (pure ES module: no DOM, no clock). Slice LS5 of
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 2.1, 4.1, 7.3), amended by
// plan-amendments.md C6 and C15, and ls1-rulings.md (a new tracker on every seek; the hold header). It turns the
// transcriber's ticks into what the lab page (and later piano.js) draws: settled bars as frozen blocks, the open and
// settling bars as live blocks, tape columns placed by time with the C6 push, the pedal line, the header and the key.
//
//   const R = createRibbon({ spell, layout: createLayout(), options: { meter: "4/4" } });
//   R.noteOn(60, 90, t); R.noteOff(60, t); R.soundEnd(60, t, "release"); R.pedal(true, 127, t);
//   R.tap(t); R.thisIsOne(t); R.chooseLevel(2); R.setMeter("3/4");
//   const f = R.tick(T);          // monotonic; a seek builds a new ribbon (a new transcriber and a new beat tracker)
//   R.view()                      // { scrollX, live, blocks, columnsIn(xa, xb), ticksIn(xa, xb), pedalSegments(), header, ... }
//
// What is drawn where (plan 2.1, 6.7):
// - A bar is a candidate for metric drawing while every tick inside its span drew bars (index.js freezeBar's own rule,
//   read live over the recent tape ticks); once settled, its kind decides. Candidate bars
//   that are open or settling are live blocks, re-laid out every tick (the open bar with fixed 96 px beats, a settling bar
//   widened as it will settle). A settled metric bar becomes a frozen block: its x, model and layout never change.
// - Every other onset group is a tape column (C6), placed once and never moved. Groups after the last tape tick wait
//   while the page draws bars (at most pendingMaxMs, 3 s: on the tempo suite 1.5 s left 22 settled metric bars shown as tape, 3 s left 9) for their bar to appear, groups of a bar whose kind is not
//   decided wait while bars draw, and groups after a
//   live bar wait until that bar is resolved, so time order along the ribbon holds. A settled metric bar whose own onset
//   was already placed as tape is shown as tape (stats.demoted; its taped notes count in stats.conflicts). A note placed
//   as tape and tied into a later bar (a bar-line continuation, and its splits inside that bar) is left out of that bar's
//   drawn voices, live and frozen (tapedTies "omit", stats.tiedFromTape): its tape column and duration line draw it. So
//   no note is drawn twice and nothing painted is repainted. tapedTies "demote" (measured, not the default) shows such a
//   bar as tape instead; any other value keeps the pre-repair rule, for A/B benches only.
// - Scroll: the playhead's content x is the nominal time axis in tape (the push debt sits right of the playhead, at most
//   D_max) and the bar's beat axis inside a bar; it never moves back.
// - Key (lab approximation, labelled on the page): nashville.js createKeyTracker over the page's decaying pitch-class
//   histogram (piano.js: 12 s decay, 0.5 + vel/127 per note-on), no chord cue; marks.js createKeySignature adopts a
//   signature after 2 steps of a 2 s clock (4 s, the LS6 free-time rule) of a non-provisional key. A bar takes the
//   signature in force at its start; tape takes the current one. Spelling is the injected speller in the signature's key.
// - Clefs: hands.js clefsAndOctaves over every settled bar in order plus the live bars (prefix-stable, so a frozen bar's
//   clef is final).

import { createTranscriber, meterInfo } from "./index.js";
import { createOnsets } from "./onsets.js";
import { clefsAndOctaves } from "./hands.js";
import { pedalMarks, createKeySignature } from "./marks.js";
import { createKeyTracker } from "../nashville.js";
import { createLayout, createTapePlacer, tapeHeads, modelBar, layoutBar, barXAt, headShift } from "./layout.js";

export const RIBBON_API = "arsenal.piano.score.ribbon/v0";

const MAJOR_BY_FIFTHS = Object.freeze({ "-7": "Cb", "-6": "Gb", "-5": "Db", "-4": "Ab", "-3": "Eb", "-2": "Bb", "-1": "F", "0": "C", "1": "G", "2": "D", "3": "A", "4": "E", "5": "B", "6": "F#", "7": "C#" });
export const keyNameOfFifths = (f) => (f == null ? null : `${MAJOR_BY_FIFTHS[String(f)]} major`);

export function createRibbon({ spell = null, layout = null, options = {}, params = {}, keyTracking = true, pendingMaxMs = 3000, keepPx = 6000, tapedTies = "omit" } = {}) {
  const L = layout || createLayout();
  const sp = L.sp;
  const tr = createTranscriber({ spell, params, options });
  const on = createOnsets(params.onsets || {});
  let meter = meterInfo(options.meter || "4/4");

  // ------------------------------------------------------------------------------------------------ state ---
  const notes = new Map();                 // id -> { id, note, vel, t, off, se }
  const heldBy = new Map();                // midi -> [note records without a release]
  const seQ = new Map();                   // midi -> [note records waiting for a sound end]
  let pending = [];                        // onset groups not placed, time order
  const known = new Map();                 // bar index -> the latest bar object (unresolved bars)
  const meterOf = new Map();               // bar index -> meterInfo the bar was built under
  const blocks = [];                       // frozen bar blocks, ascending
  let lastResolved = -1;
  const cols = [];                         // tape columns, ascending x (never move)
  const runs = [];                         // tape runs: { id, x, t }
  const barred = new Set(), taped = new Set(), demoted = new Set(), tapedWhy = new Map();
  let live = [];
  const prevLive = new Map();              // index -> { state, layout, x0 } of last tick's live blocks
  let lastTapeTick = -Infinity, scrollX = 0, T = null, lastHeader = null, lastDrawing = "tape", lastWasBar = true;
  const pedalLog = [], groupTimes = [], tapeTicks = [];   // tapeTicks: recent tick times that drew tape
  const settledLite = [];
  const stats = {
    ticks: 0, commits: 0, tapeBars: 0, columns: 0, overlaps: 0, clamped: 0, conflicts: 0, collapses: 0, waitMaxMs: 0,
    tapeMs: 0, idMismatch: 0, liveChanges: 0, demoted: 0, conflictWhy: {}, tiedFromTape: 0,
    shiftOpenToEngraved: { unwidened: { n: 0, px: 0 }, widened: { n: 0, px: 0 }, moved: 0, x0: { n: 0, px: 0 } },
    shiftSettlingToSettled: { unwidened: { n: 0, px: 0 }, widened: { n: 0, px: 0 }, moved: 0, x0: { n: 0, px: 0 } },
  };
  const keyTracker = keyTracking ? createKeyTracker() : null;
  const hist = new Array(12).fill(0);
  let histAt = null, keyState = null, keyView = null, curFifths = null;
  const ks = createKeySignature();
  const fifthsLog = [];
  const spellCache = new Map();
  let placer = createTapePlacer(L, { x0: 0, t0: 0 });
  let anchored = false;

  const decay = (t) => { if (histAt != null) { const f = Math.exp(-(t - histAt) / 12000); for (let i = 0; i < 12; i++) hist[i] *= f; } histAt = t; };

  // ------------------------------------------------------------------------------------------------ inputs ---
  function noteOn(midi, vel, t) {
    if (!anchored) anchor(t);
    const id = tr.noteOn(midi, vel, t);
    const n = on.noteOn(midi, vel, t);
    if (n.id !== id) stats.idMismatch++;
    const rec = { id: n.id, note: midi, vel, t, off: null, se: null };
    notes.set(n.id, rec);
    if (!heldBy.has(midi)) heldBy.set(midi, []);
    heldBy.get(midi).push(rec);
    if (!seQ.has(midi)) seQ.set(midi, []);
    seQ.get(midi).push(rec);
    decay(t); hist[((midi % 12) + 12) % 12] += 0.5 + vel / 127;
    return id;
  }
  function noteOff(midi, t) {
    tr.noteOff(midi, t); on.noteOff(midi, t);
    const q = heldBy.get(midi);
    if (q && q.length) { q.shift().off = t; if (!q.length) heldBy.delete(midi); }
  }
  function soundEnd(midi, t, by = null) {
    tr.soundEnd(midi, t, by);
    const q = seQ.get(midi);
    if (q && q.length) { q.shift().se = t; if (!q.length) seQ.delete(midi); }
  }
  function pedal(down, value, t) { tr.pedal(down, value, t); on.pedal(down, t); pedalLog.push({ t_ms: t, down: !!down }); }
  function setMeter(label) {
    for (const b of known.values()) if (!meterOf.has(b.index)) meterOf.set(b.index, meter);
    tr.setMeter(label);
    meter = meterInfo(label);
  }
  function anchor(t) { placer.reanchor(0, t); runs.push({ id: placer.anchor().run, x: placer.anchor().x, t }); anchored = true; }

  // ---------------------------------------------------------------------------------------------- helpers ---
  function spellMany(midis, fifths) {
    if (!spell) return midis.map(() => null);
    const key = keyNameOfFifths(fifths);
    const out = [];
    const miss = [];
    for (const m of midis) { const k = m + "|" + key; if (spellCache.has(k)) out.push(spellCache.get(k)); else { out.push(undefined); miss.push(m); } }
    if (miss.length) {
      let res = null;
      try { res = spell(miss, key); } catch { res = null; }
      const by = new Map((res || []).map((x) => [x.midi, x]));
      for (const m of miss) { const x = by.get(m); spellCache.set(m + "|" + key, x ? { letter: x.letter, acc: x.acc, octave: x.octave } : null); }
      if (spellCache.size > 4096) spellCache.clear();
      return midis.map((m) => spellCache.get(m + "|" + key) ?? null);
    }
    return out;
  }
  const fifthsAt = (t) => { let f = null; for (const x of fifthsLog) { if (x.at_ms > t) break; f = x.fifths; } return f; };
  const lite = (b) => ({ index: b.index, voices: (b.measure ? b.measure.voices : b.voices).map((v) => ({ staff: v.staff, notes: v.notes.map((p) => ({ note: p.note })) })) });
  function clefRows(extra) {
    const rows = clefsAndOctaves([...settledLite, ...extra.map(lite)]);
    return new Map(rows.map((r) => [r.index, r]));
  }
  function modelOf(b, clefRow, fifths, keyChange) {
    const m = meterOf.get(b.index) || meter;
    return modelBar(b, {
      meter: m,
      spelledOf: (p) => spellMany([p.note], fifths ?? null)[0],
      clefs: clefRow ? clefRow.clefs : undefined, octave: clefRow ? clefRow.octave : undefined, clefChange: clefRow ? clefRow.change : null,
      fifths: fifths ?? 0, keyChange,
    });
  }
  // A bar's voices hold its onsets and the pieces of notes tied in across its bar line (and their splits inside the bar).
  // taped ids among every piece of the bar, with whether the note's onset is the bar's own
  function tapedIn(b) {
    const own = new Set(b.notes.map((n) => n.id)), out = new Map();
    for (const v of (b.measure || b).voices) for (const p of v.notes) if (taped.has(p.id)) out.set(p.id, own.has(p.id));
    for (const n of b.notes) if (taped.has(n.id)) out.set(n.id, true);
    return out;
  }
  // the bar as drawn: with tapedTies "omit", pieces of a note already placed as tape leave the bar's voices (a note tied in
  // from tape is drawn once, as its tape column and duration line); beams and tuplets find their stems by piece, so a
  // left-out piece drops out of them too
  function drawable(b) {
    if (tapedTies !== "omit") return { bar: b, omitted: 0 };
    const ms = b.measure || b;
    const ids = new Set();
    for (const v of ms.voices) for (const p of v.notes) if (taped.has(p.id)) ids.add(p.id);
    if (!ids.size) return { bar: b, omitted: 0 };
    const voices = ms.voices.map((v) => ({ ...v, notes: v.notes.filter((p) => !ids.has(p.id)) }));
    return { bar: b.measure ? { ...b, measure: { ...ms, voices } } : { ...b, voices }, omitted: ids.size };
  }
  const lastBlock = () => (blocks.length ? blocks[blocks.length - 1] : null);
  function contentStart(t) { return Math.max(placer.end(), placer.nominal(t)); }

  function addShift(acc, before, after, x0Before, x0After) {
    if (!before) return;
    const s = headShift(before, { ...after, beatTicks: after.beatTicks }, L);
    for (const k of ["unwidened", "widened"]) { acc[k].n += s[k].n; acc[k].px += s[k].meanPx * s[k].n; }
    acc.moved += s.moved;
    acc.x0.n++; acc.x0.px += Math.abs(x0After - x0Before);
  }

  function placeTape(g, why = "noOwner") {
    const snap = tr.hands() ? tr.hands().snapshot() : null;
    const fifths = curFifths;
    const sp1 = spellMany(g.notes.map((n) => n.note), fifths);
    const lastB = lastBlock();
    const items = g.notes.map((n, i) => ({ id: n.id, note: n.note, staff: snap ? snap.staffOf(n) : n.note >= 60 ? 1 : 2, spelled: sp1[i] }));
    const { heads, w, accW } = tapeHeads(items, L, { clefs: lastB ? lastB.model.clefs : undefined, fifths: fifths ?? 0 });
    const c = placer.place(g.t, w);
    const headX = c.x + accW + 0.11 * sp;
    // LR11f: heads of this column against earlier columns within reach (same staff, boxes shrunk 0.1 s per side)
    const bw = (L.params.headWSp - 2 * L.params.shrinkSp) * sp, bh = (L.params.headHSp - 2 * L.params.shrinkSp) * sp;
    for (let k = cols.length - 1; k >= 0 && cols[k].headX + 2 * L.params.headWSp * sp > headX - bw; k--) {
      for (const a of cols[k].heads) for (const b of heads) {
        if (a.staff === b.staff && Math.abs((cols[k].headX + a.dx) - (headX + b.dx)) < bw && Math.abs(a.step - b.step) * sp / 2 < bh) stats.overlaps++;
      }
    }
    const col = { gid: g.id, t: g.t, x: c.x, w, D: c.D, clamped: c.clamped, run: c.run, headX, heads, fifths, freely: lastWasBar };
    lastWasBar = false;
    cols.push(col);
    for (const n of g.notes) { taped.add(n.id); tapedWhy.set(n.id, why); }
    groupTimes.push({ t: g.t, id: g.id });
    stats.columns++;
    if (c.clamped) stats.clamped++;
  }

  function commitBar(b0) {
    const { bar: b, omitted } = drawable(b0);
    stats.tiedFromTape += omitted;
    const rows = clefRows([b]);
    const fifths = fifthsAt(b.start_ms);
    const prevF = lastBlock() ? lastBlock().model.fifths : null;
    const keyChange = lastBlock() && fifths != null && fifths !== prevF ? fifths : null;
    const model = modelOf(b, rows.get(b.index), fifths, keyChange);
    const layout = layoutBar(model, L, { widen: true });
    const pl = prevLive.get(b.index);
    const x0 = pl && pl.x0 != null ? Math.max(pl.x0, contentStart(b.start_ms)) : contentStart(b.start_ms);
    const block = { kind: "bar", index: b.index, x0, x1: x0 + layout.width, start_ms: b.start_ms, end_ms: b.end_ms, fullEnd_ms: b.fullEnd_ms ?? null, beats: layout.beats, model, layout, state: "settled", committed: true, reason: b.reason ?? null };
    if (pl) addShift(pl.state === "open" ? stats.shiftOpenToEngraved : stats.shiftSettlingToSettled, pl.layout, { ...layout, beatTicks: model.beatTicks }, pl.x0, x0);
    blocks.push(block);
    for (const n of b.notes) { if (taped.has(n.id)) stats.conflicts++; barred.add(n.id); }
    placer.reanchor(block.x1, b.end_ms);
    runs.push({ id: placer.anchor().run, x: placer.anchor().x, t: b.end_ms });
    lastWasBar = true;
    settledLite.push(lite(b));
    lastResolved = b.index; known.delete(b.index); meterOf.delete(b.index);
    stats.commits++;
    return block;
  }

  // ------------------------------------------------------------------------------------------------ tick ---
  function tick(Tn) {
    if (!(T == null || Tn >= T)) throw new RangeError(`ribbon tick(${Tn}): the clock went back from ${T} ms; build a new ribbon after a seek`);
    const dt = T == null ? 0 : Tn - T;
    T = Tn; stats.ticks++;
    if (!anchored) anchor(T);
    if (keyTracker) {
      decay(T);
      keyState = keyTracker.update(hist.slice(), T / 1000, null);
      const k = keyState && keyState.key;
      keyView = k ? { tonic: k.tonic, mode: k.mode, provisional: keyState.confidence === "unsure" } : null;
      const step = Math.floor(T / 2000);
      const r = ks.step({ keyView, bar: step, firstUnsettled: step });
      if (r.current !== curFifths) { curFifths = r.current; fifthsLog.push({ at_ms: T, fifths: curFifths }); }
    }
    const out = tr.tick(T, keyView ? { keyView } : {});
    lastHeader = out.header;
    for (const g of on.flush(T)) pending.push(g);
    const drawing = out.header.drawing;
    if (drawing !== "bars") { lastTapeTick = T; stats.tapeMs += dt; tapeTicks.push(T); if (tapeTicks.length > 2048) tapeTicks.splice(0, 1024); }
    lastDrawing = drawing;
    const viewIdx = out.view.bars.map((b) => b.index);
    const lo = viewIdx.length ? Math.min(...viewIdx) : Infinity, hi = viewIdx.length ? Math.max(...viewIdx) : -Infinity;
    const inView = new Set(viewIdx);
    for (const [i, b] of known) if (b.state !== "settled" && i >= lo && !inView.has(i)) known.delete(i);   // dropped
    for (const [i] of known) if (i > hi && viewIdx.length && !inView.has(i)) known.delete(i);
    for (const b of out.view.bars) if (b.index > lastResolved) { known.set(b.index, b); if (!meterOf.has(b.index) && b.state === "open" && b.rev === 0) meterOf.set(b.index, meter); }
    resolve();
    const x = xAt(T, false);
    if (x > scrollX) scrollX = x;
    trim();
    return { header: out.header, changed: out.changed, drawing, live: live.map((b) => b.index), commits: stats.commits };
  }

  function resolve() {
    const bars = [...known.values()].filter((b) => b.index > lastResolved).sort((a, b) => a.index - b.index);
    const noteBar = new Map();
    for (const b of bars) for (const n of b.notes) noteBar.set(n.id, b);
    // index.js freezeBar's rule read live: no tick inside the bar's own span [start, end] drew tape (a tape tick after a
    // settling bar ended does not count against it)
    const tapeTickIn = (a, z) => { let lo = 0, hi = tapeTicks.length; while (lo < hi) { const m = (lo + hi) >> 1; if (tapeTicks[m] < a) lo = m + 1; else hi = m; } return lo < tapeTicks.length && tapeTicks[lo] <= z; };
    const candidate = (b) => !demoted.has(b.index) && (b.state === "settled" ? b.kind === "metric" : !tapeTickIn(b.start_ms, b.end_ms));
    const newLive = [], keep = [];
    let blocked = false, bi = 0, gi = 0;
    while (bi < bars.length || gi < pending.length) {
      const b = bars[bi], g = pending[gi];
      if (g && (!b || g.t < b.start_ms)) {
        gi++;
        const ids = g.notes.map((n) => n.id);
        if (ids.every((id) => barred.has(id))) continue;
        const owner = ids.map((id) => noteBar.get(id)).find(Boolean) || null;
        if (owner && candidate(owner)) { keep.push(g); continue; }
        if (blocked) { keep.push(g); continue; }
        // its bar is not decided yet while bars draw (a grid revision can move the bar's start past the last tape tick)
        if (owner && owner.state !== "settled" && lastDrawing === "bars" && !demoted.has(owner.index)) { keep.push(g); blocked = true; stats.waitMaxMs = Math.max(stats.waitMaxMs, T - g.t); continue; }
        if (!owner && lastDrawing === "bars" && g.t > lastTapeTick && T - g.t < pendingMaxMs) { keep.push(g); blocked = true; stats.waitMaxMs = Math.max(stats.waitMaxMs, T - g.t); continue; }
        placeTape(g, owner ? (owner.state === "settled" ? "ownerSettledTape" : "ownerUndecided") : lastDrawing === "bars" ? "waitExpired" : "noOwnerDrawingTape");
        continue;
      }
      bi++;
      if (b.state === "settled" && !blocked) {
        // a settled metric bar whose own onset went to tape is shown as tape; so is one holding a note tied in from tape
        // when tapedTies is "demote" (with "omit" that note's pieces leave the drawn bar instead)
        const tp = b.kind === "metric" ? tapedIn(b) : null;
        const holds = tp ? [...tp].filter(([, own]) => own || tapedTies === "demote") : [];
        if (b.kind === "metric" && !holds.length) commitBar(b);
        else if (b.kind === "metric") { const onMs = new Map(b.notes.map((n) => [n.id, n.on_ms])); for (const [id, own] of holds) { const w = tapedWhy.get(id) + (!own ? ":tiedIn" : onMs.get(id) < b.start_ms ? ":beforeStart" : ":inside"); stats.conflictWhy[w] = (stats.conflictWhy[w] || 0) + 1; } demoted.add(b.index); stats.demoted++; stats.conflicts += holds.length; settledLite.push(lite(b)); lastResolved = b.index; known.delete(b.index); meterOf.delete(b.index); }
        else { settledLite.push(lite(b)); lastResolved = b.index; known.delete(b.index); meterOf.delete(b.index); stats.tapeBars++; }
        continue;
      }
      if (candidate(b)) { newLive.push(b); blocked = true; }
    }
    pending = keep;
    // live blocks
    const drawn = newLive.map((b) => drawable(b).bar);
    const rows = drawn.length ? clefRows(drawn) : null;
    let x = null;
    const next = [];
    for (const b of drawn) {
      const fifths = fifthsAt(b.start_ms);
      const prevF = lastBlock() ? lastBlock().model.fifths : null;
      const model = modelOf(b, rows.get(b.index), fifths, lastBlock() && fifths != null && fifths !== prevF ? fifths : null);
      const open = b.state === "open";
      const layout = layoutBar(model, L, { widen: !open });
      const x0 = x ?? contentStart(b.start_ms);
      x = x0 + layout.width;
      const sig = `${b.rev}|${b.state}|${fifths}|${JSON.stringify(model.clefs)}|${JSON.stringify(model.octave)}|${layout.width}|${x0}`;
      const pl = prevLive.get(b.index);
      if (pl && pl.state === "open" && !open) addShift(stats.shiftOpenToEngraved, pl.layout, { ...layout, beatTicks: model.beatTicks }, pl.x0, x0);
      if (!pl || pl.sig !== sig) stats.liveChanges++;
      next.push({ kind: "bar", index: b.index, x0, x1: x, start_ms: b.start_ms, end_ms: b.end_ms, fullEnd_ms: b.fullEnd_ms ?? null, beats: layout.beats, model, layout, state: b.state, committed: false, sig, rev: b.rev });
    }
    for (const [i] of prevLive) if (!next.some((b) => b.index === i) && !blocks.some((b) => b.index === i)) stats.collapses++;
    prevLive.clear();
    for (const b of next) prevLive.set(b.index, { state: b.state, layout: { ...b.layout, beatTicks: b.model.beatTicks }, x0: b.x0, sig: b.sig });
    live = next;
  }

  // ----------------------------------------------------------------------------------------- time -> x ---
  function runAt(t) { let r = runs[0]; for (let i = runs.length - 1; i >= 0; i--) if (runs[i].t <= t) { r = runs[i]; break; } return r; }
  function tapeX(t, warp) {
    const r = runAt(t);
    if (!r) return placer.nominal(t);
    const nom = r.x + (t - r.t) * L.v;
    if (!warp) return nom;
    let lo = null, hi = null;
    for (let i = cols.length - 1; i >= 0; i--) {
      const k = cols[i];
      if (k.run !== r.id) { if (k.run < r.id) break; continue; }
      if (k.t <= t) { lo = k; break; }
      hi = k;
    }
    if (!lo) return nom;
    const D = hi ? lo.D + ((hi.D - lo.D) * (t - lo.t)) / Math.max(1e-9, hi.t - lo.t) : lo.D;
    return nom + D;
  }
  function xAt(t, warp = true) {
    for (const b of live) if (t >= b.start_ms && t < b.end_ms) return barXAt(b, t);
    if (live.length) {
      const lb = live[live.length - 1];
      if (t >= lb.end_ms) return lb.x1 + (t - lb.end_ms) * (lb.x1 - lb.x0) / Math.max(1, lb.end_ms - lb.start_ms);
      if (t >= live[0].start_ms) return live[0].x0;
    }
    for (let i = blocks.length - 1; i >= 0; i--) {
      const b = blocks[i];
      if (t >= b.start_ms && t < b.end_ms) return barXAt(b, t);
      if (b.end_ms <= t) break;
    }
    return tapeX(t, warp);
  }

  function trim() {
    const left = scrollX - keepPx;
    while (cols.length > 64 && cols[0].x + cols[0].w < left) cols.shift();
    while (blocks.length > 16 && blocks[0].x1 < left) blocks.shift();
    while (runs.length > 2 && runs[1].t < (cols.length ? cols[0].t : T) && (!blocks.length || runs[1].x < blocks[0].x0)) runs.shift();
    if (pedalLog.length > 4096) pedalLog.splice(0, 2048);
    if (groupTimes.length > 4096) groupTimes.splice(0, 2048);
    if (notes.size > 8192) { for (const [id, n] of notes) { if (notes.size <= 4096) break; if (n.se != null || n.off != null) notes.delete(id); } }
  }

  // ------------------------------------------------------------------------------------------------ view ---
  function columnsIn(xa, xb) {
    let lo = 0, hi = cols.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (cols[m].x + cols[m].w + 400 < xa) lo = m + 1; else hi = m; }
    const out = [];
    for (let i = lo; i < cols.length && cols[i].x <= xb; i++) out.push(cols[i]);
    return out;
  }
  function ticksIn(xa, xb) {
    const out = [];
    if (T == null) return out;
    // 1 s ticks inside tape runs only (not under bars)
    for (let i = 0; i < runs.length; i++) {
      const r = runs[i], rEnd = i + 1 < runs.length ? runs[i + 1].t : T;
      const barAfter = blocks.find((b) => b.start_ms >= r.t) || live[0];
      const stop = Math.min(rEnd, barAfter ? barAfter.start_ms : T, T);
      for (let t = Math.ceil(r.t / L.params.tapeTickMs) * L.params.tapeTickMs; t <= stop; t += L.params.tapeTickMs) {
        const x = tapeX(t, true);
        if (x >= xa && x <= xb) out.push(x);
      }
    }
    return out;
  }
  function pedalSegments(fromMs = -Infinity) {
    const log = pedalLog.filter((p) => p.t_ms >= fromMs - 60000);
    const groups = groupTimes.filter((g) => g.t >= fromMs - 60000);
    const { marks } = pedalMarks(log, { groups, params: { conPed: false } });
    const segs = [];
    let cur = null;
    for (const m of marks) {
      if (m.type === "start") { cur = { x0: xAt(m.at_ms), notches: [], open: true }; segs.push(cur); }
      else if (m.type === "change" && cur) cur.notches.push(xAt(m.at_ms));
      else if (m.type === "change") { cur = { x0: xAt(m.at_ms), notches: [], open: true }; segs.push(cur); }
      else if (m.type === "stop" && cur) { cur.x1 = xAt(m.at_ms); cur.open = false; cur = null; }
    }
    for (const s of segs) if (s.x1 == null) s.x1 = xAt(T);
    return segs;
  }
  const endX = (h) => { const n = notes.get(h.id); return xAt(n ? (n.se ?? n.off ?? T) : T); };

  return {
    api: RIBBON_API, layout: L,
    noteOn, noteOff, soundEnd, pedal, setMeter,
    tap: (t) => tr.tap(t), thisIsOne: (t) => tr.thisIsOne(t), chooseLevel: (r) => tr.chooseLevel(r), setOptions: (x) => tr.setOptions(x),
    tick,
    view: () => ({ T, scrollX, live, blocks, header: lastHeader, drawing: lastDrawing, fifths: curFifths, key: keyState, clefs: lastBlock() ? lastBlock().model.clefs : { 1: "treble", 2: "bass" } }),
    columnsIn, ticksIn, pedalSegments, endX, xAt,
    transcriber: () => tr,
    stats: () => ({ ...stats, tapeMinutes: stats.tapeMs / 60000, overlapsPerTapeMinute: stats.tapeMs > 0 ? stats.overlaps / (stats.tapeMs / 60000) : 0, pending: pending.length, live: live.length, blocks: blocks.length, tr: tr.stats() }),
  };
}
