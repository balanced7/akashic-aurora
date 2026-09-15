// Live sheet music transcriber, skeleton: arsenal/web/piano/score/index.js (pure ES module: no DOM, no clock).
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 4, 5.2 and 6, amended by
// plan-amendments.md (C1, C2, C3 clean options, C7, section 0 rule 3) and ls1-rulings.md (a new beat tracker per pass).
// Slices LS2-LS3: onsets (onsets.js) -> beat (beat.js, or fixed beats as the jam rung's stand-in) -> hands and voices
// (hands.js, unless voiceOf is injected) -> per-beat rhythm (quantize.js) -> bars and written durations (measures.js, C1
// and C7 on hands.js voices: voice 4 is the lower staff's lowest line) -> bar states (settle.js) -> notation on the score
// (meter.js pickups, hands.js clefs, marks.js marks, the injected speller). The header carries meter.js's suggestion and
// subdivision chip and its readout model (a family press shows the dimmed request with "hold" until bpmShown confirms).
// reader and harmony are accepted and not used yet.
//
//   const tr = createTranscriber({ options: { meter: "4/4" } });
//   tr.noteOn(60, 90, perfMs); tr.noteOff(60, perfMs); tr.soundEnd(60, perfMs, "pedal"); tr.pedal(true, 100, perfMs);
//   const { header, changed, view } = tr.tick(perfMs);   // every frame or every 250 ms of event time; monotonic
//   const score = clean(events, { meter: "3/4", one: 12400, taps: [...], feel: "straight" });
//
// Segments. Bars are counted inside a segment: a run of one beat source at one tactus level. A hold, a source switch
// (taps <-> inferred), a tactus factor change, a chosen level, a meter or feel change closes the segment: its bars
// settle, bars after its last onset are dropped, and the next segment continues the bar numbers. Onsets outside every
// segment are tape (no rhythm claimed).
// Bar-line ties (C7 held bass). A written end never passes the last bar a build keeps: the last started bar while live,
// the last bar with an onset at a segment close. A tie frozen in a settled bar keeps the bar it leads into: the close
// keeps that bar, and a phase correction starts one bar later (the phase-keep convention, ratified in ls1-rulings.md: a
// frozen note's recorded duration is never re-capped). So every tie leads into the next bar of its own segment. Live, a
// continuation stops at the start of the beat the onset finality horizon is in (measures.js heardTick): the tick time, or
// the oldest note-on onsets.js has not handed out yet if earlier. So an onset the build has not seen when a pause or the
// settle beats froze the tie rarely lands inside it. The guarantee is the pin, per voice (ls1-rulings.md): a build never
// places a note inside a frozen continuation in its voice, it places that note at the continuation's end, while the notes
// of its onset group in other voices stay where they were heard (stats().pinned counts groups with a pinned note,
// pinnedNotes the notes, pinMerged pinned voices landing on another group's tick in that voice; a pinned note carries
// pinnedFrom, the tick the grid gave it). A tracker revision of the beat grid or a new division of a beat can move an
// onset the build has already seen earlier after the tie froze.
// Tactus grid. Tactus beat j of a segment sits at agent beat a0 + j / factor (beat.js factor: 1, 1/2, 1/3 or 2/3),
// linear between the chosen agent's beats (lag-2 settled times once settled), extrapolated one beat past the last.
// Bar phase. Fixed beats: the beat nearest `one` (else beat 0). Tracker: "This is 1" (beat.js barPhase) when pressed;
// otherwise an LS2 stand-in until meter.js (LS3): once a second, the phase whose tactus beats carry the most accent
// (salience, +0.7 new low bass, +1.2 pitch-class change over 0.6 s, +0.8 pedal down within 0.3 s), set once 2 bars of
// beats exist and moved only after phaseHold (4) decisions in a row with margin phaseMargin of the mean accent.
// A phase change is forward-only: it starts at the first unsettled bar (a partial bar), settled bars keep theirs.
// Live build (on any new onset, release, sound end, pedal or beat): the unsettled bars are rebuilt from the quantizer
// checkpoint at their first beat, durations use now = tick time for notes still held, and settle.js keeps settled bars
// frozen. A bar is drawn metric (kind "metric") only if every tick over its span drew bars (beat.js ladder: rung 4 only
// while steady, LR4g; plus the rung4Floor gate on periodicity strength, LR4i); otherwise its notes are tape when it
// settles. A bar settled before its end by a segment close is cut at the close (cut, fullEnd_ms).
// clean(): the same code in deferred mode on a new transcriber (a new beat tracker): no bar settles until its segment
// closes, then each segment is quantized once with the Viterbi divisions (quantize.js cleanDivisions), loose beats on
// the d = 6 grid (C2 export), and the last phase decision covers the whole segment. score.rhythm (C3): "jam" with fixed
// beats, "tapped" when a bar came from taps, "inferred" when every bar is metric from a steady rung 4 and nothing is
// tape, else "unverified". Not in LS2: the backward beat tidy (plan 8 step 2) and taps anchored with hindsight; taps
// run forward at their times.

import { createOnsets } from "./onsets.js";
import { createBeatTracker, METERS } from "./beat.js";
import { assignBeats, createLiveQuantizer, cleanDivisions, exportPositions } from "./quantize.js";
import { createGrid, writeDurations, buildMeasures, barSignature } from "./measures.js";
import { createSettle } from "./settle.js";
import { createHands, assignVoices, clefsAndOctaves } from "./hands.js";
import { createMeterModel, createHeaderModel, inferPhase as inferPhaseOf, pickupOf } from "./meter.js";
import { pedalMarks, dynamicMarks, accentMarks, keySignatureChanges, createKeySignature, freelyMarks, placeAt } from "./marks.js";

export const SCORE_API = "arsenal.piano.score/v0";
export const TPQ = 24;

export const TRANSCRIBER_OPTIONS = Object.freeze({
  meter: "4/4", feel: "straight", scoreMode: "bars", pedalled: "played", heldBass: true, tpq: TPQ, accents: "off",
  settleBeats: 4, pauseMs: 2000, takeBufferMs: 15 * 60000, viewBars: 12,
  beats: null, one: null, deferred: false, voiceOf: null,
  phaseBeats: 32, phaseHold: 4, phaseMargin: 0.1,
  // LS3: the subdivision chip rule (meter.js; "grid" is C11 as written), con Ped. (marks.js), key areas for the clean
  // copy's signatures ([{ start_ms, end_ms, key: { tonic, mode } }]), a fixed key for spelling, the meter model on/off
  chipRule: "grid", conPed: true, keyAreas: null, key: null, meterModel: true,
  // the rung-4 metric gate (plan-amendments.md LR4i, section 5): an inferred beat draws bars only while beat.js reads
  // steady and the periodicity strength is at least this floor. Raised from 4.5 in 0.5 steps until the precision of shown
  // rung-4 bars held 0.80 on the held-out tempo suite (7.5: 0.772, 8.0: 0.856). beat.js's steady word (4.5) is unchanged.
  rung4Floor: 8.0,
});

// The bench voice split (plan-amendments.md section 0 rule 3): at and above middle C voice 1 on the upper staff, below
// it voice 3 on the lower staff.
export const splitAt60 = (n) => (n.note >= 60 ? { voice: 1, staff: 1 } : { voice: 3, staff: 2 });

export function meterInfo(label) {
  const m = METERS[label] || METERS["4/4"];
  const beatTicks = m.compound ? 36 : 24;
  return { label: METERS[label] ? m.label : label, beats: m.beats, beatType: m.beatType, tactus: m.tactusPerBar, compound: m.compound, beatTicks, barTicks: beatTicks * m.tactusPerBar, free: label === "free" };
}

const EVENT_ORDER = { off: 0, sound_end: 1, pedal: 2, on: 3 };

export function createTranscriber({ spell = null, reader = null, harmony = null, params = {}, options = {} } = {}) {
  const o = { ...TRANSCRIBER_OPTIONS, ...options };
  // voices: an injected voiceOf (truth voices on fixtures, splitAt60 on request), else hands.js (LS3)
  const handsMode = !o.voiceOf;
  const voiceOf = o.voiceOf || splitAt60;
  const P = { onsets: params.onsets || {}, beat: params.beat || {}, quant: params.quant || {}, hands: params.hands || {}, meter: params.meter || {}, marks: params.marks || {} };
  const hands = handsMode ? createHands(P.hands) : null;
  const mm = createMeterModel({ meter: o.meter, feel: o.feel, params: { ...P.meter, chipRule: o.chipRule } });
  const hd = createHeaderModel(P.meter);
  const ks = createKeySignature({ params: P.marks });
  const keyLog = [];
  let vmap = null, meterSec = -Infinity, meterOut = { suggestion: null, chip: null }, maxBar = -1, lastKeyJson = null;
  let M = meterInfo(o.meter), feel = o.feel;
  const fixed = Array.isArray(o.beats) && o.beats.length >= 3 ? o.beats.slice() : null;
  const on = createOnsets(P.onsets);
  const bt = fixed ? null : createBeatTracker(P.beat, { meter: o.meter });
  const st = createSettle({ settleBeats: o.settleBeats, pauseMs: o.pauseMs });

  const events = [], notes = [], groups = [], pedalLog = [], seQueue = new Map(), voiceStats = new Map();
  const recs = new Map();
  let lastRec = -1;
  const segments = [];
  let seg = null;
  const drawLog = [];
  const bars = new Map();          // global bar index -> bar object (settled bars are final)
  let lastT = -Infinity, lastOnsetMs = null, dirty = false, nextBarBase = 0, beatBase = 0, tickBase = 0;
  let lastSample = null, floorMs = null, phaseSec = -Infinity, oneAt = o.one, finished = false;
  let changedNow = new Set();
  const counters = { builds: 0, refused: 0, groups: 0, pinned: 0, pinnedNotes: 0, pinMerged: 0 };

  // ------------------------------------------------------------------------------------------------ inputs ---
  function logEvent(e) {
    events.push(e);
    if (events.length > 8192 && events[0].t_ms < e.t_ms - o.takeBufferMs) { let k = 0; while (k < events.length && events[k].t_ms < e.t_ms - o.takeBufferMs) k++; events.splice(0, k); }
  }
  function noteOn(midi, vel, perfMs, source = null) {
    logEvent({ t_ms: perfMs, kind: "on", note: midi, vel });
    const n = on.noteOn(midi, vel, perfMs);
    notes.push(n);
    if (!seQueue.has(midi)) seQueue.set(midi, []);
    seQueue.get(midi).push(n);
    lastOnsetMs = perfMs; dirty = true;
    return n.id;
  }
  function noteOff(midi, perfMs) { logEvent({ t_ms: perfMs, kind: "off", note: midi }); on.noteOff(midi, perfMs); dirty = true; }
  function soundEnd(midi, perfMs, by = null) {
    logEvent({ t_ms: perfMs, kind: "sound_end", note: midi, by });
    const q = seQueue.get(midi);
    if (!q || !q.length) return;
    const n = q.shift();
    n.soundEnd = perfMs; n.by = by;
    if (!q.length) seQueue.delete(midi);
    dirty = true;
  }
  function pedal(down, value, perfMs) {
    logEvent({ t_ms: perfMs, kind: "pedal", down: !!down, value });
    on.pedal(down, perfMs);
    if (bt) bt.pedal(down, perfMs);
    pedalLog.push({ t_ms: perfMs, down: !!down });
    dirty = true;
  }
  const tap = (perfMs) => (bt ? bt.tap(perfMs) : null);
  function thisIsOne(perfMs) { if (bt) return bt.thisIsOne(perfMs); oneAt = perfMs; return null; }
  // a family press: the header covers the wait for bpmShown with the dimmed request (meter.js createHeaderModel)
  function chooseLevel(ratio) {
    if (!bt) return null;
    hd.press(ratio, lastT, lastSample);
    return bt.chooseLevel(ratio);
  }
  function setMeter(label) {
    if (seg) closeSegment(lastT, "meter");
    M = meterInfo(label);
    if (bt) bt.setMeter(label);
    mm.setMeter(label);
  }
  function setOptions(x = {}) {
    if (x.feel && x.feel !== feel) { if (seg) closeSegment(lastT, "feel"); feel = x.feel; mm.setFeel(x.feel); }
    Object.assign(o, x);
  }

  function voiceFor(n) {
    if (handsMode) {
      // the current build's voices; a note outside the window reads its staff from the best path, in its staff's lone voice
      const v = vmap && vmap.get(n.id);
      if (v) return v;
      const st = hands.snapshot().staffOf(n);
      return { staff: st, voice: st === 1 ? 1 : 4 };
    }
    if (!n.vinfo) {
      n.vinfo = voiceOf(n) || { voice: 1, staff: 1 };
      if (n.vinfo.staff === 2) { const s = voiceStats.get(n.vinfo.voice) || { sum: 0, n: 0 }; s.sum += n.note; s.n++; voiceStats.set(n.vinfo.voice, s); }
    }
    return n.vinfo;
  }
  function lowestVoice() {
    if (handsMode) return 4;   // hands.js: voice 4 is always the lower staff's lowest line (C7's held bass)
    let best = null, bm = Infinity;
    for (const [v, s] of voiceStats) { const m = s.sum / s.n; if (m < bm) { bm = m; best = v; } }
    return best;
  }

  // ------------------------------------------------------------------------------------------ tactus grid ---
  function recPeriod() {
    const ids = [];
    for (let i = lastRec; i >= 0 && ids.length < 5; i--) if (recs.has(i)) ids.push(i);
    if (ids.length >= 2) { const a = ids[ids.length - 1], b = ids[0]; return (recs.get(b).t_ms - recs.get(a).t_ms) / (b - a); }
    return lastSample && lastSample.period_ms ? lastSample.period_ms : 600;
  }
  function recTime(i) {
    const r = recs.get(i);
    if (r) return r.t_ms;
    if (i > lastRec) return recs.get(lastRec).t_ms + (i - lastRec) * recPeriod();
    let lo = i - 1, hi = i + 1;
    while (lo >= 0 && !recs.has(lo) && i - lo < 512) lo--;
    while (hi <= lastRec && !recs.has(hi)) hi++;
    if (recs.has(lo)) return recs.get(lo).t_ms + (recs.get(hi).t_ms - recs.get(lo).t_ms) * (i - lo) / (hi - lo);
    return recs.get(hi).t_ms - (hi - i) * recPeriod();
  }
  function tactusTime(j) {
    if (fixed) {
      const n = fixed.length;
      if (j >= 0 && j < n) return fixed[j];
      return j >= n ? fixed[n - 1] + (j - n + 1) * (fixed[n - 1] - fixed[n - 2]) : fixed[0] + j * (fixed[1] - fixed[0]);
    }
    const x = seg.a0 + j / seg.factor, lo = Math.floor(x + 1e-9), fr = x - lo;
    const tl = recTime(lo);
    return fr < 1e-9 ? tl : tl + (recTime(lo + 1) - tl) * fr;
  }
  function knownTactus(T) {
    if (fixed) { let j = -1; let lo = 0, hi = fixed.length - 1; if (fixed[0] > T) return -1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (fixed[m] <= T) lo = m; else hi = m - 1; } j = lo; return j; }
    return Math.floor((lastRec - seg.a0) * seg.factor + 1e-9);
  }
  const nearestFixed = (t) => { let best = 0; for (let j = 1; j < fixed.length; j++) if (Math.abs(fixed[j] - t) < Math.abs(fixed[best] - t)) best = j; return best; };

  // ------------------------------------------------------------------------------------ segments and bars ---
  const segKey = (s) => (fixed ? "fixed" : `${s.source}|${+s.factor.toFixed(4)}|${s.levelBpm != null ? 1 : 0}`);
  function openSegment(T, s) {
    let a0 = 0, factor = 1, source = "jam";
    if (!fixed) {
      a0 = lastRec;
      if (floorMs != null) for (let i = lastRec; i >= 0 && recs.has(i) && recs.get(i).t_ms >= floorMs - 60; i--) a0 = i;
      factor = s.factor; source = s.source;
    }
    seg = { id: segments.length, key: segKey(s), source, factor, a0, epochs: [{ from: 0, phase: 0 }], tick0: 0, phaseSet: !!fixed,
      barBase: nextBarBase, beatBase, tickBase, startMs: 0, cand: null, candN: 0, lastJK: -2, sigma: null,
      q: createLiveQuantizer({ params: P.quant, beatTicks: M.beatTicks, beatsPerBar: M.tactus, compound: M.compound, feel }) };
    seg.startMs = tactusTime(0);
    segments.push(seg);
    if (fixed && oneAt != null) setPhase(nearestFixed(oneAt));
    dirty = true;
  }
  function boundaries(jLimit) {
    const K = M.tactus, out = [];
    seg.epochs.forEach((ep, e) => {
      const end = e + 1 < seg.epochs.length ? seg.epochs[e + 1].from : jLimit + 1;
      if (ep.from < end) out.push(ep.from);
      let b = ep.from + ((((ep.phase - ep.from) % K) + K) % K);
      if (b === ep.from) b += K;
      for (; b < end; b += K) out.push(b);
    });
    return out;
  }
  function dropBars(fromGi) {
    for (const i of st.drop(fromGi)) { bars.delete(i); changedNow.add(i); }
    for (const [i, b] of bars) if (i >= fromGi && b.state !== "settled") { bars.delete(i); changedNow.add(i); }
  }
  // downTactus: a tactus index that is a downbeat
  function setPhase(downTactus) {
    const K = M.tactus, ph = ((downTactus % K) + K) % K;
    const cur = seg.epochs[seg.epochs.length - 1];
    if (seg.phaseDecided && cur.phase === ph) return false;
    const ls = st.lastSettled();
    if (o.deferred || ls == null || ls < seg.barBase) {
      seg.epochs = [{ from: 0, phase: ph }];
      seg.tick0 = downTactus;
      dropBars(seg.barBase);
    } else {
      const jK = knownTactus(lastT), bnd = boundaries(jK + K), fu = st.firstUnsettled();
      // a settled bar whose held bass ties over its bar line keeps the bar that tie leads into (at most one bar-line tie,
      // C7): the new phase starts one bar later, so the frozen continuation never spills past a partial bar
      const prev = fu == null ? null : bars.get(fu - 1);
      const tieInto = prev && prev.seg === seg.id && prev.state === "settled" && prev.measure.voices.some((v) => v.notes.some((p) => p.barTie)) ? 1 : 0;
      const iU = Math.max(0, Math.min(bnd.length - 1, (fu == null ? 0 : fu) - seg.barBase + tieInto));
      const F = bnd[iU];
      seg.epochs = seg.epochs.filter((e) => e.from < F).concat([{ from: F, phase: ph }]);
      dropBars(seg.barBase + iU);
    }
    seg.phaseSet = true; seg.phaseDecided = true; dirty = true;
    return true;
  }

  // the inferred rung's phase scorer: meter.js inferPhase (the LS2 stand-in, moved there unchanged)
  const inferPhase = (T) => inferPhaseOf({ K: M.tactus, jK: knownTactus(T), tactusTime, groups, pedals: pedalLog, phaseBeats: o.phaseBeats });
  function phaseStep(T) {
    const sec = Math.floor(T / 1000);
    if (fixed || sec <= phaseSec) return;
    phaseSec = sec;
    const bp = bt.state().barPhase;
    if (bp && bp.source === "this-is-1") { setPhase(Math.round((bp.downbeatIndex - seg.a0) * seg.factor)); return; }
    const r = inferPhase(T);
    if (!r) return;
    if (!seg.phaseDecided) { setPhase(r.phase); return; }
    const cur = seg.epochs[seg.epochs.length - 1].phase;
    if (r.phase !== cur && r.margin > o.phaseMargin * r.mean) {
      if (seg.cand === r.phase) seg.candN++; else { seg.cand = r.phase; seg.candN = 1; }
      if (seg.candN >= o.phaseHold) { setPhase(r.phase); seg.cand = null; seg.candN = 0; }
    } else { seg.cand = null; seg.candN = 0; }
  }

  // --------------------------------------------------------------------------------------------- build ---
  function build(T, { clean = false, closing = false } = {}) {
    if (!seg || !seg.phaseSet) return;
    const K = M.tactus, BT = M.beatTicks;
    const jKnown = knownTactus(T);
    if (jKnown < 0) return;
    const bnd = boundaries(jKnown + K);
    let nStarted = 0;
    while (nStarted < bnd.length && bnd[nStarted] <= jKnown) nStarted++;
    if (!nStarted || nStarted >= bnd.length) return;
    let iU = 0;
    if (!clean) { const fu = st.firstUnsettled(); iU = fu == null ? 0 : Math.max(0, fu - seg.barBase); }
    if (iU >= nStarted) return;
    counters.builds++;
    const jU = bnd[iU], jW = Math.max(0, jU - K), jTo = jKnown + 1;
    const times = [];
    for (let j = jW; j <= jTo; j++) times.push(tactusTime(j));
    const t0 = times[0] - 0.125 * (times[1] - times[0]);
    let gi = groups.length;
    while (gi > 0 && groups[gi - 1].t >= t0) gi--;
    const gw = groups.slice(gi).filter((g) => g.segId == null || g.segId === seg.id);
    if (handsMode) {
      // voices for this build (hands.js): the window's notes plus the frozen notes of the settled bar before it, whose
      // sustain decides which later notes are the moving line above a tied held bass; frozen notes keep their own voices
      const win = gw.flatMap((g) => g.notes), inWin = new Set(win);
      const fp = bars.get(seg.barBase + iU - 1);
      if (fp && fp.frozen && fp.seg === seg.id) for (const fn of fp.notes) { const m = fn.g && fn.g.notes.find((x) => x.id === fn.id); if (m && !inWin.has(m)) { win.push(m); inWin.add(m); } }
      vmap = assignVoices(win, { staffOf: hands.snapshot().staffOf, now_ms: clean ? Infinity : T, pedal: pedalLog, params: P.hands });
    }
    const asg = assignBeats(gw.map((g) => g.t), times);
    const byBeat = new Map();
    gw.forEach((g, i) => {
      const a = asg[i];
      if (!a || g.segId === seg.id) return;
      const j = jW + a.bb;
      if (j < jU) return;
      if (!byBeat.has(j)) byBeat.set(j, []);
      byBeat.get(j).push({ g, f: a.f, t: g.t, grace: !!g.grace });
    });
    const keys = [...byBeat.keys()].sort((a, b) => a - b);
    const place = new Map();
    const periodOf = (j) => times[j - jW + 1] - times[j - jW];
    if (!clean) {
      seg.q.rewind(jU);
      for (const j of keys) { const its = byBeat.get(j), r = seg.q.decide(j, its, periodOf(j)); its.forEach((it, k) => place.set(it.g, { j, off: r.pos[k], loose: r.loose })); }
    } else {
      const q = createLiveQuantizer({ params: P.quant, beatTicks: BT, beatsPerBar: K, compound: M.compound, feel });
      const list = keys.map((j) => { const its = byBeat.get(j); q.decide(j, its, periodOf(j)); return { bb: j, items: its, P: periodOf(j) }; });
      const cd = cleanDivisions(list, { params: P.quant, beatTicks: BT, beatsPerBar: K, compound: M.compound, feel, liveDiv: q.divisions(), sigma: q.sigma() });
      for (const it of list) { const d = cd.get(it.bb), pos = exportPositions(d, it.items, BT); it.items.forEach((x, k) => place.set(x.g, { j: it.bb, off: pos[k], loose: d.loose })); }
      seg.sigma = q.sigma();
    }
    // Frozen continuations are commitments the open bar respects (settled means never repainted). A bar-line tie frozen in
    // the settled bar before bar iU covers [start of bar iU, its end) in its voice; a note of that voice is never placed
    // inside it, and is pinned to the continuation's end instead. The pin is per voice (ls1-rulings.md "LS2close to LS5
    // rulings"): only the group's notes in the conflicting voice move; its notes in other voices stay where they were
    // heard. heardTick (below) keeps the claim short of onsets the build has not seen; the pin covers onsets it has seen
    // that move earlier after the tie froze: a tracker revision of the beat grid, or a beat's division changing when a new
    // onset joins it. Counted when a bar settles (freezeBar), so a pin a later build undid is not counted.
    const contEnd = new Map(), frozenPrev = bars.get(seg.barBase + iU - 1), barStartU = (jU - seg.tick0) * BT;
    if (frozenPrev && frozenPrev.frozen && frozenPrev.seg === seg.id) {
      for (const n of frozenPrev.notes) { const e = n.segTick + n.dur; if (e > barStartU && e > (contEnd.get(n.voice) ?? -Infinity)) contEnd.set(n.voice, e); }
    }
    const notePlace = new Map();   // note -> its own placement when pinned apart from its group
    if (contEnd.size) for (const g of gw) {
      const pl = place.get(g);
      if (!pl) continue;
      const tick = (pl.j - seg.tick0) * BT + pl.off;
      for (const n of g.notes) {
        const e = contEnd.get(voiceFor(n).voice);
        if (e == null || e <= tick) continue;
        const k = Math.floor(e / BT);
        notePlace.set(n, { j: k + seg.tick0, off: e - k * BT, loose: k + seg.tick0 === pl.j ? pl.loose : false, pinnedFrom: tick });
      }
    }
    const lines = [];
    for (let i = 0; i <= nStarted; i++) lines.push((bnd[i] - seg.tick0) * BT);
    const wnotes = [];
    for (const g of gw) {
      const pl = place.get(g);
      if (!pl) continue;
      for (const n of g.notes) {
        const q = notePlace.get(n) || pl, tick = (q.j - seg.tick0) * BT + q.off, v = voiceFor(n);
        wnotes.push({ id: n.id, note: n.note, vel: n.vel, tick, on_ms: n.t, off_ms: n.off, se_ms: n.soundEnd, voice: v.voice, staff: v.staff, j: q.j, off: q.off, loose: q.loose, pinnedFrom: q.pinnedFrom, g });
      }
    }
    // Frozen notes come from the settled bar itself, not from the group time window: a bar-line tie crosses one bar line,
    // so only the bar before iU can hold a continuation into the bars this build rebuilds. The window (t0, from the grid as
    // revised now) can miss a frozen onset that the next-beat rule placed on that bar's downbeat from before it (f > 0.875
    // on the grid of its own build); its continuation then vanished from bar iU (a bar tie leading nowhere, an untiled note).
    if (frozenPrev && frozenPrev.frozen && frozenPrev.seg === seg.id) {
      for (const n of frozenPrev.notes) wnotes.push({ id: n.id, note: n.note, vel: n.vel, tick: n.segTick, on_ms: n.on_ms, off_ms: n.off_ms, se_ms: n.se_ms, voice: n.voice, staff: n.staff, frozenDur: n.dur, j: n.j, off: n.off, g: n.g });
    }
    // written ends stop at the last bar this build keeps (C7 ties lead into a built bar): the last started bar, and at a
    // segment close the last bar with an onset (the bars after it are dropped). Frozen notes keep theirs: closeSegment
    // keeps a bar a frozen tie leads into, and setPhase never makes that bar partial.
    let lastBar = nStarted - 1;
    if (closing) {
      let lo = -1;
      for (const b of bars.values()) if (b.seg === seg.id && b.state === "settled" && b.notes.length) lo = Math.max(lo, b.bar);
      for (const n of wnotes) if (n.frozenDur == null && n.tick < lines[nStarted]) { let i = iU; while (i + 1 < nStarted && lines[i + 1] <= n.tick) i++; lo = Math.max(lo, i); }
      if (lo >= 0) lastBar = Math.min(lastBar, lo);
    }
    const grid = createGrid(times, { origin: seg.tick0 - jW, beatTicks: BT });
    // heardTick comes from the onset finality horizon, not the tick time: a group onsets.js still holds open (a chord,
    // near-chord or roll can still form, up to 180 ms) is not in this build, yet its note-on may lie before T. Every onset
    // this build has not seen starts at or after min(T, oldest pending note-on), so it quantizes at or after that beat.
    const pend = on.oldestPending(), horizon = pend == null ? T : Math.min(T, pend);
    const durs = writeDurations(wnotes, { grid, meter: M, barLines: lines, pedal: pedalLog, lowest: lowestVoice(), heldBass: o.heldBass, now_ms: clean ? Infinity : T, capTick: lines[lastBar + 1], heardTick: clean ? Infinity : Math.floor(grid.tickAt(horizon) / BT) * BT });
    for (const n of wnotes) {
      if (n.frozenDur != null) { n.dur = n.frozenDur; continue; }
      const d = durs.get(n.id);
      n.dur = d.dur; n.staccato = d.staccato; n.rule = d.rule;
    }
    const looseBeats = new Set(wnotes.filter((n) => n.loose && n.frozenDur == null).map((n) => n.j - seg.tick0));
    const built = buildMeasures(wnotes, { meter: M, barLines: lines, from: iU, to: nStarted, looseBeats });
    const gOff = segments[0] === seg ? 0 : seg.tickBase + seg.tick0 * BT;
    for (const b of built) {
      const i = b.index;
      if (i < iU || i >= nStarted) continue;
      const gidx = seg.barBase + i, start_ms = tactusTime(bnd[i]), end_ms = tactusTime(bnd[i + 1]);
      const sig = barSignature(b);
      const res = st.upsert(gidx, { sig, endBeat: seg.beatBase + bnd[i + 1], start_ms, end_ms });
      if (res.refused) { counters.refused++; continue; }
      const inBar = wnotes.filter((n) => n.frozenDur == null && n.tick >= lines[i] && n.tick < lines[i + 1]).map((n) => ({
        id: n.id, note: n.note, vel: n.vel, voice: n.voice, staff: n.staff, segTick: n.tick, tick: n.tick + gOff, pos: n.tick - lines[i], dur: n.dur,
        j: n.j, off: n.off, loose: n.loose, staccato: !!n.staccato, rule: n.rule, on_ms: n.on_ms, off_ms: n.off_ms, se_ms: n.se_ms, g: n.g, ...(n.pinnedFrom != null ? { pinnedFrom: n.pinnedFrom } : {}),
      }));
      const prev = bars.get(gidx);
      // beats_ms (LS4): the tactus beat times of the bar on the grid of this build, for the export tempo map (musicxml.js
      // sound tempo per bar, midi.js a tempo event per beat); not part of the bar signature
      const beats_ms = Array.from({ length: bnd[i + 1] - bnd[i] }, (_, k) => tactusTime(bnd[i] + k));
      const obj = { index: gidx, seg: seg.id, bar: i, startTactus: bnd[i], beats: bnd[i + 1] - bnd[i], startTick: lines[i] + gOff, start_ms, end_ms, beats_ms, measure: b, sig, notes: inBar, state: res.state, rev: res.rev, kind: null, source: null, modes: null };
      bars.set(gidx, obj);
      if (gidx > maxBar) maxBar = gidx;
      if (res.changed || !prev) changedNow.add(gidx);
    }
  }

  function freezeBar(gidx, T) {
    const b = bars.get(gidx);
    if (!b || b.frozen) return;
    const s = st.get(gidx);
    b.state = "settled"; b.rev = s ? s.rev : b.rev; b.reason = s ? s.reason : null; b.settledAt = T; b.frozen = true;
    // settled before its end (a segment close or the session end): the bar is cut at T, since the time after it belongs
    // to the next segment or to tape, and its kind is judged over the span it covers (LR4g)
    if (T != null && T < b.end_ms) { b.fullEnd_ms = b.end_ms; b.end_ms = Math.max(b.start_ms, T); b.cut = true; }
    let span = drawLog.filter((d) => d.T >= b.start_ms && d.T <= b.end_ms);
    if (!span.length) { const before = drawLog.filter((d) => d.T <= b.end_ms); span = before.length ? [before[before.length - 1]] : []; }
    b.kind = !M.free && span.length > 0 && span.every((d) => d.drawing === "bars") ? "metric" : "tape";
    const votes = {};
    for (const d of span) votes[d.source] = (votes[d.source] || 0) + 1;
    b.source = Object.entries(votes).sort((x, y) => y[1] - x[1])[0]?.[0] ?? null;
    b.modes = [...new Set(span.map((d) => d.mode))];
    for (const n of b.notes) {
      n.g.segId = b.seg;
      n.g.notes.forEach((m) => { if (m.id === n.id) m.placed = { segTick: n.segTick, dur: n.dur, voice: n.voice, staff: n.staff, j: n.j, off: n.off }; });
    }
    // pins as settled (the per-voice pin in build): pinned counts onset groups with a pinned note, pinnedNotes the notes,
    // pinMerged a group's pinned voice landing on the tick of another group's note in that voice (merged into its chord)
    const merged = new Set();
    for (const n of b.notes) {
      if (n.pinnedFrom == null) continue;
      counters.pinnedNotes++;
      if (!n.g.pinCounted) { n.g.pinCounted = true; counters.pinned++; }
      const k = n.g.id + "|" + n.voice;
      if (!merged.has(k) && b.notes.some((m) => m.g !== n.g && m.voice === n.voice && m.segTick === n.segTick)) { merged.add(k); counters.pinMerged++; }
    }
    changedNow.add(gidx);
  }

  function closeSegment(T, reason) {
    if (!seg) return;
    build(T, { clean: o.deferred, closing: true });
    // the last bar with an onset, or with the continuation of a tie from a settled bar
    let lastWith = -1;
    for (const b of bars.values()) if (b.seg === seg.id && (b.notes.length || b.measure.voices.some((v) => v.notes.length))) lastWith = Math.max(lastWith, b.index);
    dropBars(lastWith + 1 > seg.barBase ? lastWith + 1 : seg.barBase);
    for (const gidx of st.settleAll(reason, T)) freezeBar(gidx, T);
    const mine = [...bars.values()].filter((b) => b.seg === seg.id);
    if (mine.length) {
      const last = mine.reduce((m, b) => (b.index > m.index ? b : m));
      nextBarBase = last.index + 1;
      tickBase = last.startTick + last.beats * M.beatTicks;
      beatBase = seg.beatBase + last.startTactus + last.beats + 1;
    }
    seg.closed = true; seg.endMs = T; seg.reason = reason;
    seg = null; floorMs = null; phaseSec = -Infinity;
  }

  // ---------------------------------------------------------------------------------------------- tick ---
  function tick(T, ctx = {}) {
    if (!(T >= lastT)) throw new RangeError(`score index.js tick(${T}): the clock went back from ${lastT} ms; the clock is monotonic, build a new transcriber after a seek`);
    lastT = T;
    changedNow = new Set();
    for (const g of on.flush(T)) { groups.push(g); counters.groups++; if (bt) bt.addGroup(g); if (hands) hands.addGroup(g); if (!seg && floorMs == null) floorMs = g.t; dirty = true; }
    let s = null, drawing, mode, source;
    if (bt) {
      s = bt.tick(T);
      for (const r of s.beats) { recs.set(r.index, r); if (r.index > lastRec) lastRec = r.index; }
      if (s.beats.length || s.settled.length) dirty = true;
      drawing = M.free ? "tape" : s.drawing; mode = s.mode; source = s.source;
      if (drawing === "bars" && source === "inferred" && !(s.per >= o.rung4Floor)) drawing = "tape";
    } else { drawing = M.free ? "tape" : "bars"; mode = "steady"; source = "jam"; }
    lastSample = s;
    drawLog.push({ T, drawing, mode, source });
    if (drawLog.length > 16384) drawLog.splice(0, 8192);
    if (bt) {
      const hold = s.mode === "hold";
      if (seg && (hold || segKey(s) !== seg.key)) closeSegment(T, hold ? "hold" : "source");
      if (!seg && !hold && !M.free && s.bpm != null && s.source !== "none" && lastRec >= 0) openSegment(T, s);
    } else if (!seg && !segments.length && !M.free) openSegment(T, null);
    if (seg) {
      phaseStep(T);
      const jK = knownTactus(T);
      if (jK !== seg.lastJK) { seg.lastJK = jK; dirty = true; }
      if (!o.deferred) {
        if (dirty) build(T);
        const adv = st.advance({ T, beat: seg.beatBase + jK, lastOnsetMs });
        for (const i of adv.settling) { const b = bars.get(i); if (b) b.state = "settling"; changedNow.add(i); }
        for (const i of adv.settled) freezeBar(i, T);
      }
    }
    dirty = false;
    // meter suggestion and subdivision chip, once a second of event time (meter.js); not in the deferred clean pass
    if (bt && o.meterModel && !o.deferred && Math.floor(T / 1000) > meterSec) {
      meterSec = Math.floor(T / 1000);
      meterOut = mm.step({ T, sample: s, beats: bt.state().beats, groups, pedals: pedalLog });
    }
    // the key tracker's view: spelling's key over time, and the live key signature rule (marks.js)
    if (ctx.keyView) {
      const kv = ctx.keyView, j = JSON.stringify(kv);
      if (j !== lastKeyJson) { keyLog.push({ T, key: kv }); lastKeyJson = j; if (keyLog.length > 4096) keyLog.splice(0, 2048); }
      const tonic = Number.isInteger(kv.tonic) ? kv.tonic : kv.key && kv.key.tonic, mode = kv.mode ?? (kv.key && kv.key.mode);
      ks.step({ keyView: { tonic, mode, provisional: kv.provisional ?? (kv.locked === false) }, bar: maxBar, firstUnsettled: st.firstUnsettled() });
    }
    let header;
    if (bt) {
      const hv = hd.step(s, T);
      header = { bpm: hv.bpm, dim: hv.dim, word: hv.word, requested: hv.requested ?? null, bpmShown: s.bpmShown, source, drawing, family: s.family, meter: M.label, feel, levelBpm: s.levelBpm, suggestion: meterOut.suggestion, chip: meterOut.chip };
    } else header = { bpm: null, dim: false, word: "steady", requested: null, bpmShown: null, source, drawing, family: [], meter: M.label, feel, levelBpm: null, suggestion: null, chip: null };
    return { header, changed: [...changedNow].sort((a, b) => a - b), view: { bars: viewBars(), segment: seg ? { id: seg.id, source: seg.source, factor: seg.factor } : null } };
  }
  function viewBars() {
    const out = [];
    const top = nextBarBase + (seg ? 64 : 0);
    for (let i = top; i >= 0 && out.length < o.viewBars; i--) if (bars.has(i)) out.push(bars.get(i));
    return out.reverse();
  }

  function finish(T = lastT) {
    if (finished) return;
    if (T > lastT) tick(T);
    for (const g of on.flush(Infinity)) { groups.push(g); if (hands) hands.addGroup(g); }
    if (seg) closeSegment(Math.max(T, lastT), "end");
    for (const gidx of st.settleAll("end", T)) freezeBar(gidx, T);
    finished = true;
  }

  // LS3 notation on a score (derived from bar content and logged events only, so a settled bar's notation never moves):
  // pickups and partial bars (meter.js), clefs and octave lines (hands.js), pedal marks, dynamics, accents (off by default,
  // C8), key signatures and "freely" (marks.js), and spelling through the injected speller (plan-amendments.md section 0
  // rule 2: spell(midis, key) -> [{ midi, letter, acc, name, octave }] | null; no speller in score code)
  function keyAt(t) {
    if (o.keyAreas && o.keyAreas.length) { let k = o.keyAreas[0].key; for (const a of o.keyAreas) if (a.start_ms <= t) k = a.key; return k; }
    if (keyLog.length) { let k = null; for (const x of keyLog) { if (x.T > t) break; k = x.key; } return k ?? o.key; }
    return o.key;
  }
  function spellNotes(list) {
    const byGroup = new Map();
    for (const n of list) { const k = n.group ?? "n" + n.id; if (!byGroup.has(k)) byGroup.set(k, []); byGroup.get(k).push(n); }
    for (const g of byGroup.values()) {
      let res = null;
      try { res = spell(g.map((n) => n.note), keyAt(g[0].t_ms)); } catch { res = null; }
      const by = new Map((res || []).map((x) => [x.midi, x]));
      for (const n of g) { const x = by.get(n.note); n.spelled = x ? { letter: x.letter, acc: x.acc, name: x.name ?? null, octave: x.octave ?? null } : null; }
    }
  }
  function notate(out) {
    const ms = out.measures;
    for (const m of ms) { const b = bars.get(m.index); Object.assign(m, pickupOf({ bar: b.bar, barTicks: m.barTicks, voices: m.voices }, M)); }
    clefsAndOctaves(ms, P.hands).forEach((x, i) => { ms[i].clefs = x.clefs; ms[i].octave = x.octave; ms[i].clefChange = x.change; ms[i].ledgerBeyond = x.beyond; ms[i].ledgerOverflow = x.overflow; });
    const firstNote = new Map();
    for (const n of out.notes) if (n.group != null && !firstNote.has(n.group)) firstNote.set(n.group, n);
    const place = (at_ms, group) => { const n = group != null ? firstNote.get(group) : null; return n ? { bar: n.bar, pos: n.pos } : placeAt(ms, at_ms) || { bar: null, pos: null }; };
    const phrases = segments.map((g) => ({ start_ms: g.startMs, end_ms: g.endMs ?? lastT }));
    const ped = pedalMarks(pedalLog, { groups, phrases, params: { ...P.marks, conPed: o.conPed } });
    const accentIds = new Set(accentMarks(out.notes.map((n) => ({ id: n.id, t_ms: n.t_ms, vel: n.vel, voice: n.voice, note: n.note, group: n.group ?? "n" + n.id })), { accents: o.accents, params: P.marks }));
    const keySignatures = o.keyAreas
      ? keySignatureChanges(o.keyAreas).map((k) => { const m = k.initial ? ms[0] : ms.find((x) => x.start_ms >= k.at_ms); return { ...k, bar: m ? m.index : null }; })
      : ks.placed();
    const spans = [...ms.map((m) => ({ start_ms: m.start_ms, kind: m.kind })), ...out.tape.map((n) => ({ start_ms: n.t_ms, kind: "tape" }))].sort((a, b) => a.start_ms - b.start_ms);
    out.marks = {
      pedal: ped.marks.map((m) => ({ ...m, ...place(m.at_ms, m.group) })), conPed: ped.conPed,
      dynamics: dynamicMarks(notes.map((n) => ({ t_ms: n.t, vel: n.vel })), { params: P.marks }).map((d) => ({ ...d, ...place(d.at_ms, null) })),
      accents: out.notes.filter((n) => accentIds.has(n.id)).map((n) => ({ id: n.id, bar: n.bar, pos: n.pos })),
      keySignatures, freely: freelyMarks(spans).map((f) => ({ ...f, ...place(f.at_ms, null) })),
    };
    if (spell) spellNotes(out.notes);
    return out;
  }

  function score({ kind = "live" } = {}) {
    const measures = [...bars.values()].sort((a, b) => a.index - b.index);
    const placedIds = new Set();
    const outNotes = [];
    for (const b of measures) for (const n of b.notes) {
      placedIds.add(n.id);
      outNotes.push({ id: n.id, note: n.note, vel: n.vel, voice: n.voice, staff: n.staff, tick: n.tick, dur: n.dur, bar: b.index, pos: n.pos, loose: !!n.loose, staccato: n.staccato,
        t_ms: n.on_ms, off_ms: n.off_ms ?? null, se_ms: n.se_ms ?? null, kind: b.kind, group: n.g ? n.g.id : null, perf: { t_ms: n.on_ms, note: n.note } });
    }
    const tapeNotes = notes.filter((n) => !placedIds.has(n.id)).map((n) => ({ id: n.id, note: n.note, vel: n.vel, t_ms: n.t, off_ms: n.off, se_ms: n.soundEnd, ...voiceFor(n) }));
    const metricAll = measures.length > 0 && measures.every((b) => b.kind === "metric");
    const rhythm = fixed ? "jam" : measures.some((b) => b.source === "taps") ? "tapped" : metricAll && measures.every((b) => b.source === "inferred") && !tapeNotes.length ? "inferred" : "unverified";
    const out = {
      api: SCORE_API, kind, tpq: TPQ, meter: { ...M }, feel, rhythm,
      segments: segments.map((g) => ({ id: g.id, source: g.source, factor: g.factor, start_ms: g.startMs, end_ms: g.endMs ?? null, reason: g.reason ?? null, sigma_ms: g.sigma ?? (g.q ? g.q.sigma() : null) })),
      measures: measures.map((b) => ({ index: b.index, seg: b.seg, state: b.state, rev: b.rev, kind: b.kind, source: b.source, modes: b.modes, start_ms: b.start_ms, end_ms: b.end_ms, beats_ms: b.beats_ms, cut: !!b.cut,
        beats: b.beats, startTick: b.startTick, barTicks: b.beats * M.beatTicks, voices: b.measure.voices, beams: b.measure.beams, tuplets: b.measure.tuplets, loose: b.measure.loose })),
      notes: outNotes, tape: tapeNotes,
    };
    return notate(out);
  }

  return {
    noteOn, noteOff, soundEnd, pedal, tap, thisIsOne, setMeter, chooseLevel, setOptions, tick, finish, score,
    // the chips only suggest (meter.js): accepting one is his setting
    acceptSuggestion: (label) => setMeter(label), dismissSuggestion: (label) => mm.dismissSuggestion(label),
    acceptChip: (kind) => setOptions({ feel: kind === "triplets" ? "triplet" : "straight" }), dismissChip: (kind) => mm.dismissChip(kind),
    hands: () => hands, meterModel: () => mm,
    take: (fromMs = -Infinity, toMs = Infinity) => events.filter((e) => e.t_ms >= fromMs && e.t_ms <= toMs).map((e) => ({ ...e })),
    bars: () => [...bars.values()].sort((a, b) => a.index - b.index),
    tracker: () => bt,
    stats: () => ({ ...counters, violations: st.violations(), segments: segments.length, bars: bars.size }),
  };
}

// Feed practice-log events (t_ms, kind on/off/pedal/sound_end) into a transcriber on the tick clock, taps and "This is 1"
// at their times. Returns the transcriber (not finished).
export function replayInto(tr, events, { taps = [], one = null, tickMs = 250, endMs = null, onTick = null, fromMs = null } = {}) {
  const evs = events.filter((e) => e.kind in EVENT_ORDER).sort((a, b) => a.t_ms - b.t_ms || EVENT_ORDER[a.kind] - EVENT_ORDER[b.kind]);
  const tq = [...taps].sort((a, b) => a - b);
  const first = fromMs ?? (evs.length ? Math.min(evs[0].t_ms, tq.length ? tq[0] : Infinity) : 0);
  const last = endMs ?? ((evs.length ? evs[evs.length - 1].t_ms : 0) + 1000);
  let i = 0, k = 0, oneDone = one == null;
  for (let T = Math.floor(first / tickMs) * tickMs + tickMs; T <= last; T += tickMs) {
    for (;;) {
      const e = i < evs.length && evs[i].t_ms <= T ? evs[i] : null;
      const tp = k < tq.length && tq[k] <= T ? tq[k] : null;
      if (e == null && tp == null) break;
      if (tp != null && (e == null || tp <= e.t_ms)) { tr.tap(tp); k++; continue; }
      if (e.kind === "on") tr.noteOn(e.note, e.vel, e.t_ms);
      else if (e.kind === "off") tr.noteOff(e.note, e.t_ms);
      else if (e.kind === "pedal") tr.pedal(e.down, e.value ?? (e.down ? 127 : 0), e.t_ms);
      else tr.soundEnd(e.note, e.t_ms, e.by ?? null);
      i++;
    }
    if (!oneDone && one <= T) { tr.thisIsOne(one); oneDone = true; }
    const out = tr.tick(T);
    if (onTick) onTick(out, T, tr);
  }
  return tr;
}

// The clean copy (plan 8): the same code with hindsight, on a new transcriber and a new beat tracker.
// opts: { span: { from_ms, to_ms }, meter, feel, one, taps, beats (fixed beat times: the jam rung), voiceOf, params,
// options }.
export function clean(events, opts = {}) {
  const { span = null, meter = "4/4", feel = "straight", one = null, taps = [], beats = null, voiceOf = null, params = {}, options = {}, tickMs = 250, spell = null, keyAreas = null, key = null, accents = null } = opts;
  let evs = events;
  if (span) evs = evs.filter((e) => e.t_ms >= span.from_ms && e.t_ms <= span.to_ms);
  const extra = { ...(keyAreas ? { keyAreas } : {}), ...(key ? { key } : {}), ...(accents ? { accents } : {}) };
  const tr = createTranscriber({ spell, params, options: { ...options, ...extra, meter, feel, voiceOf, beats, one: beats ? one : null, deferred: true } });
  replayInto(tr, evs, { taps, one: beats ? null : one, tickMs });
  const end = (evs.length ? Math.max(...evs.map((e) => e.t_ms)) : 0) + 1000;
  tr.finish(end);
  return { ...tr.score({ kind: "clean" }), span };
}
