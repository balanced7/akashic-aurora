// MusicXML 4.0 for live sheet music: arsenal/web/piano/score/musicxml.js (pure ES module: no DOM, no clock).
// Stage T10 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (section 7.4), amended by
// plan-amendments.md C3 ("freely" on every measure of unverified spans), C5 (pedal crossings), C19 (the pedal line) and
// ls1-rulings.md LS6 (the key signature is the key the Nashville numbers use: the score's key signature marks).
//
//   toMusicXML(score, { title, date, stats }) -> string   one Piano part, two staves, uncompressed partwise MusicXML 4.0
//
// Input: a score JSON (index.js clean() or score(), usually export.js exportScore). Written:
//   attributes  <divisions> = score.tpq (24); <key> on the first measure and at every key signature mark whose fifths
//               differ from the current signature (mode when the mark names one), with a light-light bar line before it;
//               <time> from the meter (free: 4/4); <staves>2</staves>; clefs per measure (hands.js clefs: a lower-staff
//               change writes <clef number="2">).
//   measures    number i (0 for a leading pickup); implicit="yes" on pickups (meter.js pickupOf); the last bar light-heavy.
//   voices      one stream per score voice (staff 1 voices 1-2, staff 2 voices 3-4), <backup> between. Pieces at one
//               position with one written length are a <chord/>. Where a voice holds pieces of different lengths at one
//               position (a chord member released early), or an onset while an earlier note still sounds, the longer ones stay in the
//               voice and the rest move to an extra MusicXML voice (voice x 100 + lane: 101, 301, ...) padded with <forward>;
//               a note keeps its lane inside a bar and across a bar-line tie when the lane is free (lanesOf), so a tie
//               chain stays in one voice in time order; every stream sums to the measure length.
//               Rests are written as measures.js spelled them.
//   notes       <pitch> from the note's spelling (the injected speller's letter and accidental; octave from the letter,
//               B#3 = MIDI 60), else sharps in C and sharp keys and flats in flat keys (stats.unspelledNotes); <tie> +
//               <tied> for tie pieces; <type> and <dot/> from the piece; <accidental> when the alteration differs from the
//               key signature or from an earlier note at that step and octave in the bar on that staff (never on a note
//               a tie continues); <time-modification> on every note and rest in a tuplet beat of its voice (measures.js
//               tuplets: triplets 3:2, sextuplets 6:4, compound duplets 2:3) and a bracketed <tuplet> start/stop on the
//               first and last element of that beat in the voice's own stream; <beam number="1"> begin/continue/end over
//               a beat's beamed chords (measures.js beams); <staccato/>.
//   directions  at each phrase start (a new segment): <metronome> beat unit (dotted quarter in compound meters) with
//               per-minute "c. N", N the phrase's median tactus BPM, plus <words>rubato</words> when the phrase's bar
//               tempos spread past rubatoSpread (p90 / p10 > 1.08, the plan's 4% a tempo band both ways) and its bars
//               were not forced onto a fixed grid; <sound tempo> on every measure from its beat times (quarter notes per
//               minute); <words>freely</words> on every measure that is forced or not metric; pedal marks as
//               <pedal type="start|change|stop" line="yes" sign="no"/> on staff 2 and "con Ped." as words, placed by
//               <offset> in the measure (a stop or change with no open pedal, a start while one is open and an open pedal at
//               the end are repaired: stats.pedalRepairs); dynamics; <octave-shift> (8va is type "down": note pitches stay
//               sounding) at the start and end of each run of octave-line bars per staff.

import { measureBeatDurations } from "./midi.js";

export const MUSICXML_API = "arsenal.piano.score.musicxml/v0";
export const MUSICXML_PARAMS = Object.freeze({ rubatoSpread: 1.08, partName: "Piano", title: null, date: null, software: "arsenal.piano.score/v0 musicxml.js" });

const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
const SHARP_ORDER = [3, 0, 4, 1, 5, 2, 6];
const FLAT_ORDER = [6, 2, 5, 1, 4, 0, 3];
const ACC_NAME = { "-2": "flat-flat", "-1": "flat", 0: "natural", 1: "sharp", 2: "double-sharp" };
const DYNAMICS = new Set(["ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"]);
const BEAMED = new Set(["eighth", "16th", "32nd", "64th"]);
const NAMED_FALLBACK = {
  sharp: [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0], [3, 0], [3, 1], [4, 0], [4, 1], [5, 0], [5, 1], [6, 0]],
  flat: [[0, 0], [1, -1], [1, 0], [2, -1], [2, 0], [3, 0], [4, -1], [4, 0], [5, -1], [5, 0], [6, -1], [6, 0]],
};
const mod = (a, n) => ((a % n) + n) % n;
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const sorted = (a) => a.filter(Number.isFinite).sort((x, y) => x - y);
const median = (a) => { const s = sorted(a); if (!s.length) return NaN; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const quantile = (a, q) => { const s = sorted(a); return s.length ? s[Math.round(q * (s.length - 1))] : NaN; };
const round2 = (x) => Math.round(x * 100) / 100;

function keyAlters(fifths) {
  const a = [0, 0, 0, 0, 0, 0, 0];
  if (fifths > 0) for (let i = 0; i < Math.min(7, fifths); i++) a[SHARP_ORDER[i]] = 1;
  if (fifths < 0) for (let i = 0; i < Math.min(7, -fifths); i++) a[FLAT_ORDER[i]] = -1;
  return a;
}

export function pitchOf(midi, spelled, fifths = 0) {
  if (spelled && Number.isInteger(spelled.letter) && spelled.letter >= 0 && spelled.letter < 7 && Number.isInteger(spelled.acc) && Math.abs(spelled.acc) <= 2 && mod(LETTER_PC[spelled.letter] + spelled.acc, 12) === mod(midi, 12)) {
    return { letter: spelled.letter, step: LETTERS[spelled.letter], alter: spelled.acc, octave: Math.floor((midi - spelled.acc) / 12) - 1, spelled: true };
  }
  const [letter, acc] = NAMED_FALLBACK[fifths < 0 ? "flat" : "sharp"][mod(midi, 12)];
  return { letter, step: LETTERS[letter], alter: acc, octave: Math.floor((midi - acc) / 12) - 1, spelled: false };
}

// Streams of one voice: chords (pieces with one position and one length) and rests, in lanes by position, the longest
// chord at a position first. A note keeps one lane: a later piece of it goes to the lane its earlier pieces took in this
// bar, and a piece continuing a tie from the previous bar to the lane the note had there (prevLane), when that lane is
// free at its position; otherwise the first free lane. A tie chain is then written in one MusicXML voice and in time order
// wherever the voice allows it (a stop never precedes its start in the document). stats: chordSplits (an item placed
// beside another at its position: chord members of different lengths), overlapSplits (an onset while an earlier note of the
// voice still sounds), crossVoiceTies counted by the writer.
function lanesOf(v, prevLane = new Map(), st = null) {
  const groups = new Map();
  for (const p of v.notes) { const k = p.pos + "|" + p.dur; if (!groups.has(k)) groups.set(k, { pos: p.pos, dur: p.dur, notes: [] }); groups.get(k).notes.push(p); }
  const items = [...groups.values()].map((g) => ({ ...g, notes: g.notes.sort((a, b) => a.note - b.note) })).concat(v.rests.map((r) => ({ pos: r.pos, dur: r.dur, rest: r })));
  items.sort((a, b) => a.pos - b.pos || b.dur - a.dur);
  const lanes = [], laneOfId = new Map();
  for (const it of items) {
    let j = -1;
    if (!it.rest) for (const p of it.notes) {
      const want = laneOfId.has(p.id) ? laneOfId.get(p.id) : p.tieStop ? prevLane.get(p.id) : undefined;
      if (want != null && (want >= lanes.length || lanes[want].end <= it.pos)) { j = want; break; }
    }
    if (j < 0) { j = lanes.findIndex((l) => l.end <= it.pos); if (j < 0) j = lanes.length; }
    if (st && j > 0) { if (lanes.some((l, k) => k !== j && l.items.some((x) => x.pos === it.pos))) st.chordSplits++; else if (lanes.some((l, k) => k !== j && l.end > it.pos)) st.overlapSplits++; }
    while (lanes.length <= j) lanes.push({ end: 0, items: [] });
    lanes[j].items.push(it);
    lanes[j].end = it.pos + it.dur;
    if (!it.rest) for (const p of it.notes) laneOfId.set(p.id, j);
  }
  return { lanes, laneOfId };
}

function noteXml(x) {
  let s = "<note>";
  if (x.chord) s += "<chord/>";
  s += x.rest ? (x.measureRest ? '<rest measure="yes"/>' : "<rest/>") : `<pitch><step>${x.pitch.step}</step>${x.pitch.alter ? `<alter>${x.pitch.alter}</alter>` : ""}<octave>${x.pitch.octave}</octave></pitch>`;
  s += `<duration>${x.dur}</duration>`;
  if (x.tieStop) s += '<tie type="stop"/>';
  if (x.tieStart) s += '<tie type="start"/>';
  s += `<voice>${x.voice}</voice>`;
  if (x.type) s += `<type>${x.type}</type>`;
  for (let k = 0; k < (x.dots || 0); k++) s += "<dot/>";
  if (x.acc) s += `<accidental>${x.acc}</accidental>`;
  if (x.tm) s += `<time-modification><actual-notes>${x.tm.actual}</actual-notes><normal-notes>${x.tm.normal}</normal-notes></time-modification>`;
  s += `<staff>${x.staff}</staff>`;
  if (x.beam) s += `<beam number="1">${x.beam}</beam>`;
  const nt = [];
  if (x.tieStop) nt.push('<tied type="stop"/>');
  if (x.tieStart) nt.push('<tied type="start"/>');
  if (x.tuplet) nt.push(`<tuplet type="${x.tuplet}" bracket="yes"/>`);
  if (x.staccato) nt.push("<articulations><staccato/></articulations>");
  if (nt.length) s += `<notations>${nt.join("")}</notations>`;
  return s + "</note>";
}
const direction = (placement, types, { offset = 0, staff = 1, sound = null } = {}) =>
  `<direction placement="${placement}">${types.map((t) => `<direction-type>${t}</direction-type>`).join("")}${offset ? `<offset sound="yes">${offset}</offset>` : ""}<staff>${staff}</staff>${sound || ""}</direction>`;

export function toMusicXML(score, opts = {}) {
  const c = { ...MUSICXML_PARAMS, ...opts };
  const st = opts.stats || {};
  Object.assign(st, { measures: 0, measureTicks: [], pieces: 0, chords: 0, rests: 0, emptyMeasures: 0, extraLanes: 0, chordSplits: 0, overlapSplits: 0, forwards: 0, tupletBeats: 0, bracketsSkipped: 0, tieStarts: 0, crossVoiceTies: 0,
    pedal: { start: 0, change: 0, stop: 0, conPed: 0 }, pedalRepairs: 0, pedalUnplaced: 0, unspelledNotes: 0, untypedPieces: 0, metronomes: 0, rubato: 0, freely: 0, keyChanges: 0, clefChanges: 0, octaveShifts: 0, dynamics: 0, dynamicsUnplaced: 0, pickups: 0 });
  const ms = [...(score.measures || [])].sort((a, b) => a.index - b.index);
  const meter = score.meter || { beats: 4, beatType: 4, beatTicks: 24, compound: false };
  const BT = meter.beatTicks;
  const TS = meter.free ? { beats: 4, beatType: 4 } : { beats: meter.beats, beatType: meter.beatType };
  const notesById = new Map((score.notes || []).map((n) => [n.id, n]));
  const marks = score.marks || {};
  const at = new Map(ms.map((m, i) => [m.index, i]));
  const L = [];

  // ---- key signatures per measure
  const ksAt = new Map();
  for (const k of marks.keySignatures || []) if (k.bar != null && at.has(k.bar) && Number.isInteger(k.fifths)) ksAt.set(at.get(k.bar), k);
  const keyOf = [];
  let curKey = { fifths: 0, mode: "major" };
  ms.forEach((m, i) => { const k = ksAt.get(i); if (k) curKey = { fifths: k.fifths, mode: (k.key && k.key.mode) || null }; keyOf.push(curKey); });
  const writeKey = ms.map((m, i) => i === 0 || keyOf[i].fifths !== keyOf[i - 1].fifths);

  // ---- tempo per measure and per phrase
  const durs = measureBeatDurations(ms);
  const phrases = [];
  ms.forEach((m, i) => { if (i === 0 || m.seg !== ms[i - 1].seg) phrases.push({ bars: [] }); phrases[phrases.length - 1].bars.push(i); });
  const phraseAt = new Map();
  for (const p of phrases) {
    p.tactusBpm = 60000 / median(p.bars.flatMap((i) => durs[i]));
    const barBpm = p.bars.map((i) => 60000 / (durs[i].reduce((s, d) => s + d, 0) / durs[i].length));
    p.spread = quantile(barBpm, 0.9) / quantile(barBpm, 0.1);
    p.forced = p.bars.every((i) => ms[i].forced);
    p.rubato = !p.forced && p.spread > c.rubatoSpread;
    phraseAt.set(p.bars[0], p);
  }
  const quarterBpm = (i) => (60000 / (durs[i].reduce((s, d) => s + d, 0) / durs[i].length)) * (BT / 24);

  // ---- pedal marks: placed, in order, pairing repaired
  const pedalAt = new Map(), wordsAt = new Map();
  const pm = (marks.pedal || []).map((x, k) => ({ ...x, k })).filter((x) => x.bar != null && at.has(x.bar)).map((x) => ({ ...x, i: at.get(x.bar) })).sort((a, b) => a.i - b.i || a.pos - b.pos || a.k - b.k);
  st.pedalUnplaced = (marks.pedal || []).length - pm.length;
  const pushPedal = (i, pos, type) => { if (!pedalAt.has(i)) pedalAt.set(i, []); pedalAt.get(i).push({ pos, type }); st.pedal[type]++; };
  let open = false;
  for (const x of pm) {
    if (x.type === "conPed") { if (!wordsAt.has(x.i)) wordsAt.set(x.i, []); wordsAt.get(x.i).push({ pos: x.pos, text: "con Ped." }); st.pedal.conPed++; continue; }
    let type = x.type;
    if (type === "start" && open) { type = "change"; st.pedalRepairs++; }
    else if (type === "change" && !open) { type = "start"; st.pedalRepairs++; }
    else if (type === "stop" && !open) { st.pedalRepairs++; continue; }
    open = type !== "stop";
    pushPedal(x.i, x.pos, type);
  }
  if (open && ms.length) { pushPedal(ms.length - 1, ms[ms.length - 1].barTicks, "stop"); st.pedalRepairs++; }
  const dynAt = new Map();
  for (const d of marks.dynamics || []) {
    if (d.bar == null || !at.has(d.bar) || !DYNAMICS.has(d.band)) { st.dynamicsUnplaced++; continue; }
    const i = at.get(d.bar);
    if (!dynAt.has(i)) dynAt.set(i, []);
    dynAt.get(i).push(d);
  }

  // ---- header
  L.push('<?xml version="1.0" encoding="UTF-8" standalone="no"?>');
  L.push('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">');
  L.push('<score-partwise version="4.0">');
  if (c.title) L.push(`  <work><work-title>${esc(c.title)}</work-title></work>`);
  L.push(`  <identification><encoding><software>${esc(c.software)}</software>${c.date ? `<encoding-date>${esc(c.date)}</encoding-date>` : ""}<supports element="accidental" type="yes"/><supports element="beam" type="yes"/><supports element="stem" type="no"/></encoding></identification>`);
  L.push(`  <part-list><score-part id="P1"><part-name>${esc(c.partName)}</part-name></score-part></part-list>`);
  L.push('  <part id="P1">');

  const firstIsPickup = ms.length && ms[0].pickup;
  const lastVoiceOfId = new Map(), prevLanes = new Map();
  ms.forEach((m, i) => {
    const prev = i > 0 ? ms[i - 1] : null, next = ms[i + 1] || null;
    const barTicks = m.barTicks;
    st.measures++; st.measureTicks.push(barTicks);
    if (m.pickup) st.pickups++;
    L.push(`    <measure number="${i + (firstIsPickup ? 0 : 1)}"${m.pickup ? ' implicit="yes"' : ""}>`);
    // attributes
    const attr = [];
    if (i === 0) attr.push(`<divisions>${score.tpq || 24}</divisions>`);
    if (writeKey[i]) { attr.push(`<key><fifths>${keyOf[i].fifths}</fifths>${keyOf[i].mode ? `<mode>${keyOf[i].mode}</mode>` : ""}</key>`); if (i > 0) st.keyChanges++; }
    if (i === 0) attr.push(`<time><beats>${TS.beats}</beats><beat-type>${TS.beatType}</beat-type></time>`, "<staves>2</staves>");
    const clef2 = (m.clefs && m.clefs[2]) || "bass", prevClef2 = prev ? (prev.clefs && prev.clefs[2]) || "bass" : null;
    const clefXml = (n, k) => (k === "treble" ? `<clef number="${n}"><sign>G</sign><line>2</line></clef>` : `<clef number="${n}"><sign>F</sign><line>4</line></clef>`);
    if (i === 0) attr.push(clefXml(1, "treble"), clefXml(2, clef2));
    else if (clef2 !== prevClef2) { attr.push(clefXml(2, clef2)); st.clefChanges++; }
    if (attr.length) L.push(`      <attributes>${attr.join("")}</attributes>`);
    // directions at the start
    const ph = phraseAt.get(i);
    const soundTempo = Number.isFinite(quarterBpm(i)) ? `<sound tempo="${round2(quarterBpm(i))}"/>` : "";
    if (ph && Number.isFinite(ph.tactusBpm)) {
      const types = [`<metronome parentheses="no"><beat-unit>quarter</beat-unit>${meter.compound ? "<beat-unit-dot/>" : ""}<per-minute>c. ${Math.round(ph.tactusBpm)}</per-minute></metronome>`];
      if (ph.rubato) { types.push("<words>rubato</words>"); st.rubato++; }
      L.push(`      ${direction("above", types, { staff: 1, sound: soundTempo })}`);
      st.metronomes++;
    } else if (soundTempo) L.push(`      ${soundTempo}`);
    if (m.forced || m.kind !== "metric") { L.push(`      ${direction("above", ['<words font-style="italic">freely</words>'], { staff: 1 })}`); st.freely++; }
    for (const w of wordsAt.get(i) || []) L.push(`      ${direction("below", [`<words font-style="italic">${esc(w.text)}</words>`], { staff: 2, offset: Math.min(w.pos, barTicks - 1) })}`);
    const endDirs = [];
    for (const s of [1, 2]) {
      const cur = (m.octave && m.octave[s]) || 0, was = prev ? (prev.octave && prev.octave[s]) || 0 : 0, nxt = next ? (next.octave && next.octave[s]) || 0 : 0;
      if (cur && cur !== was) { L.push(`      ${direction(s === 1 ? "above" : "below", [`<octave-shift type="${cur === 8 ? "down" : "up"}" size="8" number="${s}"/>`], { staff: s })}`); st.octaveShifts++; }
      if (cur && nxt !== cur) endDirs.push(direction(s === 1 ? "above" : "below", [`<octave-shift type="stop" size="8" number="${s}"/>`], { staff: s }));
    }
    for (const p of pedalAt.get(i) || []) {
      const d = direction("below", [`<pedal type="${p.type}" line="yes" sign="no"/>`], { staff: 2, offset: p.pos });
      if (p.pos >= barTicks) endDirs.push(direction("below", [`<pedal type="${p.type}" line="yes" sign="no"/>`], { staff: 2 })); else L.push(`      ${d}`);
    }
    for (const d of dynAt.get(i) || []) { L.push(`      ${direction("below", [`<dynamics><${d.band}/></dynamics>`], { staff: 1, offset: Math.min(d.pos, barTicks - 1) })}`); st.dynamics++; }

    // accidentals per staff (bar state per step and octave)
    const ka = keyAlters(keyOf[i].fifths), accOf = new Map(), pitchOfPiece = new Map();
    for (const s of [1, 2]) {
      const pieces = m.voices.filter((v) => v.staff === s).flatMap((v) => v.notes).sort((a, b) => a.pos - b.pos || a.note - b.note);
      const state = new Map();
      for (const p of pieces) {
        const pt = pitchOf(p.note, notesById.get(p.id) && notesById.get(p.id).spelled, keyOf[i].fifths);
        pitchOfPiece.set(p, pt);
        if (p.tieStop) continue;
        const k = pt.step + pt.octave, cur = state.has(k) ? state.get(k) : ka[pt.letter];
        if (cur !== pt.alter) { accOf.set(p, ACC_NAME[pt.alter]); state.set(k, pt.alter); }
      }
    }
    // voice streams
    let cursor = 0, wrote = false;
    const voices = [...m.voices].sort((a, b) => a.staff - b.staff || a.voice - b.voice);
    for (const v of voices) {
      const tup = new Map((m.tuplets || []).filter((t) => t.voice === v.voice).map((t) => [t.beat, t]));
      const beams = (m.beams || []).filter((b) => b.voice === v.voice).map((b) => ({ beat: b.beat, ids: new Set(b.ids) }));
      const vkey = v.staff + ":" + v.voice;
      const { lanes, laneOfId } = lanesOf(v, prevLanes.get(vkey), st);
      prevLanes.set(vkey, laneOfId);
      lanes.forEach((lane, li) => {
        if (!lane.items.length) return;
        const vno = li === 0 ? v.voice : v.voice * 100 + li;
        if (li > 0) st.extraLanes++;
        if (wrote && cursor > 0) L.push(`      <backup><duration>${cursor}</duration></backup>`);
        cursor = 0; wrote = true;
        const beamOf = new Map(), bracketOf = new Map();
        if (li === 0) {
          for (const b of beams) {
            const els = lane.items.filter((it) => !it.rest && Math.floor(it.pos / BT) === b.beat && BEAMED.has(it.notes[0].type) && it.notes.some((p) => b.ids.has(p.id)));
            if (els.length >= 2) els.forEach((it, k) => beamOf.set(it, k === 0 ? "begin" : k === els.length - 1 ? "end" : "continue"));
          }
          for (const beat of tup.keys()) {
            const els = lane.items.filter((it) => Math.floor(it.pos / BT) === beat);
            st.tupletBeats++;
            if (els.length >= 2) { bracketOf.set(els[0], "start"); bracketOf.set(els[els.length - 1], "stop"); } else st.bracketsSkipped++;
          }
        }
        for (const it of lane.items) {
          if (it.pos > cursor) { L.push(`      <forward><duration>${it.pos - cursor}</duration><voice>${vno}</voice><staff>${v.staff}</staff></forward>`); st.forwards++; }
          const t = tup.get(Math.floor(it.pos / BT));
          const tm = t ? { actual: t.actual, normal: t.normal } : null;
          if (it.rest) {
            L.push(`      ${noteXml({ rest: true, dur: it.dur, voice: vno, type: it.rest.type, dots: it.rest.dots, tm, staff: v.staff, tuplet: bracketOf.get(it) })}`);
            st.rests++;
          } else {
            st.chords++;
            it.notes.forEach((p, k) => {
              st.pieces++;
              if (!p.type) st.untypedPieces++;
              if (p.tieStart) st.tieStarts++;
              if (p.tieStop && lastVoiceOfId.has(p.id) && lastVoiceOfId.get(p.id) !== `${v.staff}:${vno}`) st.crossVoiceTies++;
              lastVoiceOfId.set(p.id, `${v.staff}:${vno}`);
              L.push(`      ${noteXml({ chord: k > 0, pitch: pitchOfPiece.get(p), dur: p.dur, tieStop: p.tieStop, tieStart: p.tieStart, voice: vno, type: p.type, dots: p.dots, acc: accOf.get(p), tm, staff: v.staff, beam: beamOf.get(it), tuplet: k === 0 ? bracketOf.get(it) : null, staccato: p.staccato })}`);
            });
          }
          cursor = it.pos + it.dur;
        }
        if (cursor < barTicks) { L.push(`      <forward><duration>${barTicks - cursor}</duration><voice>${vno}</voice><staff>${v.staff}</staff></forward>`); st.forwards++; cursor = barTicks; }
      });
    }
    if (!wrote) { L.push(`      ${noteXml({ rest: true, measureRest: true, dur: barTicks, voice: 1, staff: 1 })}`); st.emptyMeasures++; }
    for (const d of endDirs) L.push(`      ${d}`);
    if (next && writeKey[i + 1]) L.push('      <barline location="right"><bar-style>light-light</bar-style></barline>');
    if (!next) L.push('      <barline location="right"><bar-style>light-heavy</bar-style></barline>');
    L.push("    </measure>");
  });
  for (const n of score.notes || []) if (!pitchOf(n.note, n.spelled, 0).spelled) st.unspelledNotes++;
  L.push("  </part>");
  L.push("</score-partwise>");
  return L.join("\n") + "\n";
}
