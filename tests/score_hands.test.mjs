// Node tests for arsenal/web/piano/score/hands.js, marks.js, meter.js and their wiring in index.js (slice LS3 of the live
// sheet music plan, research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 6.3, 6.5 and 10.3,
// amended by plan-amendments.md C1, C7, C8, C11 and section 0 rule 2, and ls1-rulings.md "Readout after ×0.5").
// Zero dependencies, synthetic fixtures (tests/fixtures/score/gen.mjs) unless --sessions:
//   node tests/score_hands.test.mjs              contracts, then LR7, LR3d and the header hold receipt on fixtures
//   node tests/score_hands.test.mjs --quick      contracts only
//   node tests/score_hands.test.mjs --sessions   also LR8 with LR8b-d on S1..Sn clean copies. Reads
//                                                state/arsenal/performance/*/events.jsonl and summary.json (key areas)
//                                                read-only; writes aggregates only (S-numbers, no ids, times or notes) to
//                                                state/arsenal/score/ls3-bench-2026-09-15.json. Skipped when missing.
// Definitions:
//   LR7   staff accuracy: share of notes whose staff equals truth. Voice F1: links between notes of one voice (every pair
//         at one onset, every pair across successive onsets of that voice), estimated links against truth links, F1.
//         Gated on the clean copy (clean(), oracle beats, hands.js voices, estimated ticks) over every LS0 family on
//         held-out seeds; the module alone (hands.js on onset groups with hindsight, truth tick order) and the MIDI 60
//         split are reported beside it.
//   Clefs (repair LS3 r1, plan 6.5): note pieces beyond 3 ledger lines under their bar's clef and octave line on the clean
//         copies (fixtures, and S1..Sn with --sessions): 0 on every bar some clef and octave line hold (gated); pieces on
//         bars no option holds, clef changes by reason ("bars" hysteresis, "range") and octave-line bars reported, with
//         outOfRange "octave" (octave line before a clef change) beside them.
//   LR3d  the "triplets?" chip (index.js header.chip, meter.js chipRule "grid" = C11 as written): appears within 32 true
//         beats of the first beat on 12/8 fixtures under meter 4/4 (inferred beats); false on straight 4/4 and 3/4
//         fixtures (every LS0 family in simple meters and the tempo suite's 4/4 and 3/4 pieces), within 32 beats (gated)
//         and anywhere (reported). chipRule "tatum" (a proposal) reported.
//   Header hold (ls1-rulings.md): after a family press, every tick until bpmShown confirms shows the request dimmed with
//         "hold"; 0 blank ticks after a press; the request within 3% of the number shown before the press × ratio.
//   LR8   (sessions, clean copies, meter 4/4, hands.js voices) medians per bar: tuplet brackets <= 1, ties <= 2, voices
//         per staff <= 2; pedal marks per beat <= 1; dynamics <= 3 per minute; key signature changes <= 1 per 30 s of
//         key area (summary.json key areas); LR8b median rests per voice per pedalled bar (pedal down >= 50%) <= 1; LR8c
//         bar-line ties per held-bass note (voice 4) <= 1 on every note; LR8d accents per minute 0 with defaults, "voice"
//         reported.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import { newAudit, auditScore, auditOk, auditLine } from "./fixtures/score/audit.mjs";
import { createHands, assignVoices, clefsAndOctaves, ledgerExcess, HANDS_PARAMS } from "../arsenal/web/piano/score/hands.js";
import { createHeaderModel, createMeterModel, createMeterState, scoreMeters, pickupOf } from "../arsenal/web/piano/score/meter.js";
import { pedalMarks, dynamicMarks, accentMarks, keySignatureChanges, createKeySignature, fifthsOf, freelyMarks, placeAt } from "../arsenal/web/piano/score/marks.js";
import { createTranscriber, replayInto, clean, splitAt60 } from "../arsenal/web/piano/score/index.js";
import { groupNotes } from "../arsenal/web/piano/score/onsets.js";
import { FAMILY_RATIOS } from "../arsenal/web/piano/score/beat.js";
import { parseKey, spellInKey } from "../arsenal/web/piano/nashville.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const quick = argv.includes("--quick"), sessions = argv.includes("--sessions");
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const r4 = (v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v);
const near = (a, b, tol) => a != null && b != null && Math.abs(a - b) <= tol;

// voice links (LR7): every pair at one onset and every pair across successive onsets of one voice (staff, voice)
function links(items) {
  const by = new Map(), L = new Set();
  for (const x of items) { const k = x.staff + "|" + x.voice; if (!by.has(k)) by.set(k, []); by.get(k).push(x); }
  for (const list of by.values()) {
    const ons = new Map();
    for (const x of list) { if (!ons.has(x.on)) ons.set(x.on, []); ons.get(x.on).push(x.id); }
    const keys = [...ons.keys()].sort((a, b) => a - b);
    keys.forEach((k, i) => {
      const cur = ons.get(k);
      for (let a = 0; a < cur.length; a++) for (let b = a + 1; b < cur.length; b++) L.add(Math.min(cur[a], cur[b]) + "|" + Math.max(cur[a], cur[b]));
      if (i + 1 < keys.length) for (const a of cur) for (const b of ons.get(keys[i + 1])) L.add(Math.min(a, b) + "|" + Math.max(a, b));
    });
  }
  return L;
}
// clefs and octave lines on a score's measures (repair LS3 r1): note pieces beyond 3 ledger lines under the bar's clef and
// octave line, split by whether some clef and octave line holds the bar (ledgerBeyond 0); clef changes by reason; bars with
// an octave line per staff
function clefStats(measures) {
  const s = { bars: measures.length, notePieces: 0, beyondHoldable: 0, beyondUnholdable: 0, unholdableBars: 0, changesBars: 0, changesRange: 0, octaveBars1: 0, octaveBars2: 0 };
  for (const m of measures) {
    const unholdable = !!m.ledgerBeyond && (m.ledgerBeyond[1] > 0 || m.ledgerBeyond[2] > 0);
    if (unholdable) s.unholdableBars++;
    for (const v of m.voices) for (const p of v.notes) { s.notePieces++; if (ledgerExcess(p.note, m.clefs[v.staff], m.octave[v.staff]) > 0) s[unholdable ? "beyondUnholdable" : "beyondHoldable"]++; }
    if (m.clefChange === "bars") s.changesBars++; else if (m.clefChange === "range") s.changesRange++;
    if (m.octave[1]) s.octaveBars1++; if (m.octave[2]) s.octaveBars2++;
  }
  return s;
}
const withClefs = (ms, params) => { const co = clefsAndOctaves(ms, params); return ms.map((m, i) => ({ ...m, clefs: co[i].clefs, octave: co[i].octave, clefChange: co[i].change, ledgerBeyond: co[i].beyond })); };
const sumStats = (list) => list.reduce((a, s) => { for (const k in s) a[k] = (a[k] || 0) + s[k]; return a; }, {});
const linkF1 = (T, E) => { let tp = 0; for (const x of E) if (T.has(x)) tp++; return T.size + E.size ? (2 * tp) / (T.size + E.size) : 1; };

// the page's speller, read-only from piano.js (plan-amendments.md section 0 rule 2), the way tests/nashville_js.test.mjs
// builds it: never copied into score code
const pianoSrc = fs.readFileSync(path.join(here, "..", "arsenal", "web", "piano.js"), "utf8");
const ta = pianoSrc.indexOf("// ===== THEORY BEGIN"), tb = pianoSrc.indexOf("// ===== THEORY END");
const Theory = new Function(pianoSrc.slice(ta, tb) + "\nreturn Theory;")();
// TN2: spellForKey spells with the one shared speller (piano/spell.js) and chordread.js's parseSuffix, injected as the page
// imports them
const sa = pianoSrc.indexOf("function spellForKey(info, key) {"), sb = pianoSrc.indexOf("\n}\n", sa);
const theoryUi = { minor: "tonic" };
const SPELL = await import("../arsenal/web/piano/spell.js");
const { parseSuffix } = await import("../arsenal/web/piano/chordread.js");
const spellForKey = new Function("Theory", "spellInKey", "theoryUi", "keyContext", "spellChord", "spellNote", "parseSuffix", pianoSrc.slice(sa, sb + 2) + "\nreturn spellForKey;")(
  Theory, spellInKey, theoryUi, SPELL.keyContext, SPELL.spellChord, SPELL.spellNote, parseSuffix);
const pageSpell = (midis, key) => {
  const info = spellForKey(Theory.detect(midis, key ? key.bias : 0), key);
  return info && Array.isArray(info.notes) ? info.notes.map((n) => ({ midi: n.midi, letter: n.letter, acc: n.acc, name: n.name, octave: n.octave })) : null;
};

// ============================================================================================ contracts ===
{
  // ---- hands.js: split, staves, voices
  const mk = (id, note, t, off, gid) => ({ id, note, vel: 80, t, off, group: { id: gid } });
  const groupOf = (gid, t, notes) => ({ id: gid, t, notes });
  {
    const h = createHands();
    const n0 = mk(0, 36, 1000, 1400, 0), n1 = mk(1, 76, 1000, 1400, 0), n2 = mk(2, 43, 1500, 1900, 1), n3 = mk(3, 79, 1500, 1900, 1);
    h.addGroup(groupOf(0, 1000, [n0, n1])); h.addGroup(groupOf(1, 1500, [n2, n3]));
    const s = h.snapshot();
    check("hands: bass to staff 2, melody to staff 1", s.staffOf(n0) === 2 && s.staffOf(n1) === 1 && s.staffOf(n2) === 2 && s.staffOf(n3) === 1, JSON.stringify([n0, n1, n2, n3].map((n) => s.staffOf(n))));
  }
  {
    // a right-hand line walking down to F3 stays on the treble staff; an E3 in it moves to the lower staff (3 ledger lines)
    const h = createHands();
    const line = [72, 69, 65, 62, 57, 55, 53, 52].map((p, i) => mk(10 + i, p, 1000 + 250 * i, 1200 + 250 * i, 10 + i));
    const bass = [mk(30, 36, 1000, 2900, 30)];
    h.addGroup(groupOf(30, 1000, [bass[0], line[0]]));
    line.slice(1).forEach((n, i) => h.addGroup(groupOf(11 + i, n.t, [n])));
    const s = h.snapshot();
    check("hands: a right-hand line down to F3 stays on staff 1, E3 moves to staff 2", line.slice(0, 7).every((n) => s.handOf(n.id) === "R" && s.staffOf(n) === 1) && s.staffOf(line[7]) === 2 && s.staffOf(bass[0]) === 2,
      JSON.stringify(line.map((n) => [n.note, s.handOf(n.id), s.staffOf(n)])));
  }
  {
    // voices: a held bass under a moving line in staff 2 (4 below, 3 above); a triad held under a melody in staff 1 (2, 1)
    const notes = [mk(0, 36, 1000, 3000, 0), mk(1, 48, 1500, 1900, 1), mk(2, 50, 2000, 2400, 2), mk(3, 43, 3000, 3400, 3),
      mk(10, 60, 1000, 3000, 10), mk(11, 64, 1000, 3000, 10), mk(12, 72, 1000, 1450, 10), mk(13, 74, 1500, 1950, 13), mk(14, 76, 2000, 2450, 14)];
    const v = assignVoices(notes, { staffOf: (n) => (n.note < 60 ? 2 : 1) });
    const got = notes.map((n) => [n.note, v.get(n.id).voice]);
    check("hands: held bass voice 4 under a moving line voice 3; a held triad voice 2 under a melody voice 1; a lone bass voice 4", same(got, [[36, 4], [48, 3], [50, 3], [43, 4], [60, 2], [64, 2], [72, 1], [74, 1], [76, 1]]), JSON.stringify(got));
    const v2 = assignVoices(notes, { staffOf: (n) => (n.note < 60 ? 2 : 1), now_ms: 1600 });
    check("hands: live, a note still held reads now as its release", v2.get(0).voice === 4 && v2.get(1).voice === 3);
    const voicesPerStaff = new Map(); for (const n of notes) { const x = v.get(n.id); if (!voicesPerStaff.has(x.staff)) voicesPerStaff.set(x.staff, new Set()); voicesPerStaff.get(x.staff).add(x.voice); }
    check("hands: at most 2 voices per staff", [...voicesPerStaff.values()].every((s) => s.size <= 2));
  }
  {
    const bar = (i, p2, p1 = [72]) => ({ index: i, voices: [{ staff: 1, notes: p1.map((note) => ({ note })) }, { staff: 2, notes: p2.map((note) => ({ note })) }] });
    const beyondOf = (bars, co) => bars.map((b, i) => b.voices.map((v) => v.notes.filter((n) => ledgerExcess(n.note, co[i].clefs[v.staff], co[i].octave[v.staff]) > 0).length).reduce((a, x) => a + x, 0));
    const view = (co) => co.map((x) => [x.clefs[2], x.octave[2]]);
    // hysteresis inside the 3-ledger range: A3 and G3 (57, 55) in treble clef keep it for 2 bars, then bass
    const hb = [bar(0, [48]), bar(1, [62, 64]), bar(2, [60, 67]), bar(3, [65]), bar(4, [57]), bar(5, [55]), bar(6, [40]), bar(7, [30], [91])];
    const co = clefsAndOctaves(hb);
    check("clefs: the lower staff turns treble at the bar line after 2 bars at or above C4, back after 2 bars below",
      same(co.map((x) => x.clefs[2]), ["bass", "bass", "bass", "treble", "treble", "treble", "bass", "bass"]) && same(co.map((x) => x.change), [null, null, null, "bars", null, null, "bars", null]), JSON.stringify(co.map((x) => [x.clefs[2], x.change])));
    check("octave lines: 8va above E6 on the treble staff, 8vb below A1 on a bass clef", co[7].octave[1] === 8 && co[7].octave[2] === -8 && co[0].octave[1] === 0);
    check("clefs: no note beyond 3 ledger lines (hysteresis bars)", beyondOf(hb, co).every((x) => x === 0), JSON.stringify(beyondOf(hb, co)));
    // repair LS3 r1, the verifier's probe: 2 bars around middle C, then C2 (treble clef held C2 at 11 ledger lines), then
    // C3 with E5 (bass clef held E5 at 5 ledger lines)
    const pb = [bar(0, [60, 64]), bar(1, [62]), bar(2, [36]), bar(3, [36]), bar(4, [48, 76]), bar(5, [48])];
    const pc = clefsAndOctaves(pb);
    check("clefs (probe): C2 after 2 bars at C4 changes the clef back to bass at that bar; C3 with E5 takes 8va on the bass clef",
      same(view(pc), [["bass", 0], ["bass", 0], ["bass", 0], ["bass", 0], ["bass", 8], ["bass", 0]]) && beyondOf(pb, pc).every((x) => x === 0) && pc.every((x) => x.beyond[2] === 0), JSON.stringify(pc));
    // the state the hysteresis left is treble at bar 2 (the old output), so bar 2's bass is a change for range
    const pc2 = clefsAndOctaves([bar(0, [60, 64]), bar(1, [62]), bar(2, [60]), bar(3, [36])]);
    check("clefs: a lower-staff note below F3 in treble clef changes the clef at that bar (change \"range\")",
      same(view(pc2), [["bass", 0], ["bass", 0], ["treble", 0], ["bass", 0]]) && same(pc2.map((x) => x.change), [null, null, "bars", "range"]), JSON.stringify(pc2));
    // the old contract's bar 4: D3 (50) in treble clef (4 ledger lines) is now a clef change at bar 4
    const ob = [bar(0, [48]), bar(1, [62, 64]), bar(2, [60, 67]), bar(3, [65]), bar(4, [50]), bar(5, [55]), bar(6, [40])];
    const oc = clefsAndOctaves(ob);
    check("clefs: D3 after the switch to treble writes bass clef at that bar, 0 ledger excess", same(oc.map((x) => x.clefs[2]), ["bass", "bass", "bass", "treble", "bass", "bass", "bass"]) && beyondOf(ob, oc).every((x) => x === 0), JSON.stringify(view(oc)));
    // bass clef above bassMax (67): the clef changes at that bar rather than E5 on 5 ledger lines, and back for C3
    const ab = [bar(0, [48]), bar(1, [76]), bar(2, [48]), bar(3, [68])];
    const ac = clefsAndOctaves(ab);
    check("clefs: a lower-staff note above G4 in bass clef changes the clef at that bar (bassMax is read)", same(view(ac), [["bass", 0], ["treble", 0], ["bass", 0], ["treble", 0]]) && beyondOf(ab, ac).every((x) => x === 0), JSON.stringify(view(ac)));
    const aoc = clefsAndOctaves(ab, { outOfRange: "octave" });
    check("clefs outOfRange \"octave\": the same bars take 8va on the bass clef", same(view(aoc), [["bass", 0], ["bass", 8], ["bass", 0], ["bass", 8]]) && beyondOf(ab, aoc).every((x) => x === 0), JSON.stringify(view(aoc)));
    // lower staff in treble clef above E6: 8va; below A1 while treble: bass clef with 8vb; a span no option holds
    const tb = [bar(0, [62]), bar(1, [64]), bar(2, [72, 91]), bar(3, [60, 64]), bar(4, [28])];
    const tc = clefsAndOctaves(tb);
    check("octave lines: 8va on a treble-clef lower staff above E6; A1-below in treble takes bass clef and 8vb", same(view(tc), [["bass", 0], ["bass", 0], ["treble", 8], ["treble", 0], ["bass", -8]]) && beyondOf(tb, tc).every((x) => x === 0), JSON.stringify(view(tc)));
    const wc = clefsAndOctaves([bar(0, [24, 72])]);
    // C1 with C5: bass 0 leaves both out (9 and 5 semitones); one note out at best, the fewest semitones is bass 8vb (C5
    // written C6, 17 over), first in order before treble 8vb (C1 written C2, 17 under)
    check("clefs: a bar no option holds keeps the fewest notes beyond, then semitones (bass 8vb) and reports it", same(view(wc), [["bass", -8]]) && wc[0].beyond[2] === 1 && ledgerExcess(72, "bass", -8) === 17, JSON.stringify(wc));
    check("octave lines: staff 1 takes 8vb when its notes lie below F3 (injected voices)", clefsAndOctaves([bar(0, [36], [48, 60])])[0].octave[1] === -8);
    // property sweep: every bar some option holds has 0 notes beyond 3 ledger lines, beyond is exact, and a bar's clef and
    // octave depend only on it and earlier bars (a prefix gives the same output)
    let seed = 12345;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
    let sweepBars = 0, fittable = 0, fitBad = 0, beyondBad = 0, prefixBad = 0, changes = 0;
    for (let s = 0; s < 400; s++) {
      const bars = [];
      for (let i = 0; i < 16; i++) {
        const centre = 30 + Math.floor(rnd() * 50), k = Math.floor(rnd() * 4);
        bars.push(bar(i, Array.from({ length: k }, () => Math.max(21, Math.min(108, centre + Math.floor(rnd() * 25) - 12))), Array.from({ length: 1 + Math.floor(rnd() * 3) }, () => 60 + Math.floor(rnd() * 49))));
      }
      const out = clefsAndOctaves(bars), cut = 1 + Math.floor(rnd() * 15);
      if (!same(clefsAndOctaves(bars.slice(0, cut)), out.slice(0, cut))) prefixBad++;
      bars.forEach((b, i) => {
        sweepBars++; if (out[i].change) changes++;
        const p2 = b.voices[1].notes.map((n) => n.note);
        const holds = ["bass", "treble"].some((cl) => [0, 8, -8].some((oc) => p2.every((x) => ledgerExcess(x, cl, oc) === 0)));
        const beyond = p2.filter((x) => ledgerExcess(x, out[i].clefs[2], out[i].octave[2]) > 0).length;
        if (holds) { fittable++; if (beyond) fitBad++; }
        if (beyond !== out[i].beyond[2]) beyondBad++;
      });
    }
    check("clefs sweep (400 x 16 random bars): 0 notes beyond 3 ledger lines on every bar some option holds; beyond exact; prefix-stable",
      fitBad === 0 && beyondBad === 0 && prefixBad === 0 && fittable > 5000, JSON.stringify({ sweepBars, fittable, fitBad, beyondBad, prefixBad, changes }));
  }

  // ---- meter.js
  {
    const hd = createHeaderModel();
    let h = hd.step({ bpm: 70, bpmShown: 70, mode: "steady", levelBpm: null }, 19750);
    check("header: no press shows bpmShown in full ink", h.bpm === 70 && !h.dim && h.word === "steady");
    hd.press(0.5, 19750, { bpm: 70, bpmShown: 70 });
    h = hd.step({ bpm: 35.2, bpmShown: 70, mode: "steady", levelBpm: 35.2 }, 20000);
    check("header: after a press the dimmed request with hold until bpmShown confirms", h.bpm === 35 && h.dim && h.word === "hold" && near(h.requested, 35.2, 1e-9), JSON.stringify(h));
    h = hd.step({ bpm: null, bpmShown: 70, mode: "steady", levelBpm: null }, 19750 + 1);
    check("header: a level that lets go ends the request (bpmShown again)", h.bpm === 70 && !h.dim, JSON.stringify(h));
    hd.press(2, 30000, { bpm: 70, bpmShown: 70 });
    h = hd.step({ bpm: null, bpmShown: null, mode: "free", levelBpm: null }, 30000);
    check("header: never blank after a press (the request from the value before it)", h.bpm === 140 && h.dim && h.word === "hold", JSON.stringify(h));
    h = hd.step({ bpm: 139, bpmShown: 138, mode: "steady", levelBpm: 139 }, 31000);
    check("header: bpmShown within 3% of the request confirms it", h.bpm === 138 && !h.dim && h.confirmed, JSON.stringify(h));
    h = hd.step({ bpm: 139, bpmShown: 138, mode: "hold", levelBpm: 139 }, 40000);
    check("header: a pause holds the last tempo dimmed", h.bpm === 138 && h.dim && h.word === "hold");
  }
  {
    const meter = { tactus: 4, beatTicks: 24, compound: false };
    const p = pickupOf({ bar: 0, barTicks: 24, voices: [{ notes: [{ pos: 12, tieStop: false }] }] }, meter);
    check("pickup: a partial first bar of a segment is an anacrusis in whole sub-beats", same(p, { pickup: { implicit: true, ticks: 12, subBeats: 1, offset: 12 } }), JSON.stringify(p));
    check("pickup: a partial bar later in a segment is a partial bar of rests", same(pickupOf({ bar: 3, barTicks: 48, voices: [] }, meter), { partial: true }));
    check("pickup: a full bar is neither", same(pickupOf({ bar: 0, barTicks: 96, voices: [] }, meter), {}));
    const ms = createMeterState();
    ms.setMeter("3/4"); ms.setFeel("triplet"); ms.dismiss("6/8");
    check("meter state: his settings, remembered", same(JSON.parse(ms.serialize()), { meter: "3/4", feel: "triplet", dismissed: ["6/8"] }));
  }
  {
    // the scorer on a steady 3/4 (bass and harmony change every 3 beats) prefers 3/4 over 4/4 by more than the margin
    const beats = [], groups = [];
    for (let i = 0; i < 32; i++) { beats.push({ t_ms: 1000 + 600 * i, index: i }); const down = i % 3 === 0; groups.push({ t: 1000 + 600 * i, s: down ? 2.2 : 1.2, low: down ? 40 + ((i / 3) % 4) : 64, pcs: new Set(down ? [(i / 3) % 12, ((i / 3) + 4) % 12] : [7]) }); }
    const sc = scoreMeters({ beats, groups });
    check("meter scorer: a 3/4 accent pattern scores 3/4 above 4/4 by >= 0.15", sc && sc.sub === 1 && sc.scores["3/4"] - (sc.scores["4/4"] ?? 0) >= 0.15, JSON.stringify(sc && { sub: sc.sub, scores: sc.scores }));
    const mm = createMeterModel({ meter: "4/4" });
    let first = null;
    for (let k = 0; k < 12; k++) { const r = mm.step({ T: 20000 + 1000 * k, sample: { mode: "steady", subdivision: 1 }, beats, groups }); if (r.suggestion && first == null) first = k; }
    check("meter suggestion: 3/4 offered after 8 consecutive steady decisions", first === 7 && mm.state().suggestion.label === "3/4", JSON.stringify([first, mm.state().suggestion]));
    const mm2 = createMeterModel({ meter: "4/4" });
    for (let k = 0; k < 12; k++) mm2.step({ T: 20000 + 1000 * k, sample: { mode: "loose", subdivision: 1 }, beats, groups });
    check("meter suggestion: not while loose (steady gate)", mm2.state().suggestion === null);
    mm.dismissSuggestion("3/4");
    mm.step({ T: 40000, sample: { mode: "steady", subdivision: 1 }, beats, groups });
    check("meter suggestion: a dismissed label is not offered again", mm.state().suggestion === null);
  }
  {
    const run = (samples, feel = "straight") => { const mm = createMeterModel({ meter: "4/4", feel }); let first = null; samples.forEach((s, k) => { const r = mm.step({ T: 1000 * (k + 1), sample: s }); if (r.chip && first == null) first = k; }); return { first, mm }; };
    const g3 = Array.from({ length: 12 }, () => ({ mode: "loose", subdivision: 3 }));
    check("chip (C11 grid rule): triplets? after 8 decisions of subdivision 3, loose is enough", run(g3).first === 7 && run(g3).mm.state().chip.kind === "triplets");
    check("chip: not while free", run(g3.map((s) => ({ ...s, mode: "free" }))).first === null);
    check("chip: not in a compound meter", (() => { const mm = createMeterModel({ meter: "12/8" }); return g3.every((s, k) => !mm.step({ T: 1000 * (k + 1), sample: s }).chip); })());
    check("chip: sounds straight? is the mirror under feel triplet", (() => { const r = run(g3.map((s) => ({ ...s, subdivision: 2 })), "triplet"); return r.first === 7 && r.mm.state().chip.kind === "straight"; })());
    check("chip: a break resets the run", run([...g3.slice(0, 7), { mode: "loose", subdivision: 2 }, ...g3.slice(0, 7)]).first === null);
  }

  // ---- marks.js
  {
    const groups = [{ id: 0, t: 1000 }, { id: 1, t: 2000 }, { id: 2, t: 3000 }, { id: 3, t: 5000 }];
    const P = [{ t_ms: 1150, down: true }, { t_ms: 2020, down: false }, { t_ms: 2160, down: true }, { t_ms: 3500, down: false }, { t_ms: 4400, down: true }, { t_ms: 6000, down: false }];
    const { marks } = pedalMarks(P, { groups });
    check("pedal: a down 150 ms after a group sits at the group; up-down within 300 ms is one change notch; a longer up is a stop and a start",
      same(marks.map((m) => [m.type, m.at_ms]), [["start", 1000], ["change", 2000], ["stop", 3500], ["start", 4400], ["stop", 6000]]), JSON.stringify(marks.map((m) => [m.type, m.at_ms])));
    const cp = pedalMarks(P, { groups, phrases: [{ start_ms: 1000, end_ms: 3400 }] });
    check("pedal: con Ped. replaces the notches of a phrase pedalled >= 80% of its time", same(cp.marks.map((m) => [m.type, m.at_ms]), [["conPed", 1000], ["stop", 3500], ["start", 4400], ["stop", 6000]]) && near(cp.conPed[0].share, 2110 / 2400, 1e-9), JSON.stringify(cp));
    check("pedal: con Ped. off keeps the notches", pedalMarks(P, { groups, phrases: [{ start_ms: 1000, end_ms: 3400 }], params: { conPed: false } }).marks.length === 5);
  }
  {
    const notes = [];
    const at = (t0, n, vel) => { for (let i = 0; i < n; i++) notes.push({ t_ms: t0 + i * 400, vel }); };
    at(0, 10, 70); at(4000, 10, 72); at(8000, 10, 90); at(12000, 2, 60); at(16000, 10, 92); at(20000, 10, 91);
    const d = dynamicMarks(notes);
    check("dynamics: a band prints once it holds 2 windows, at the first onset of the run", same(d.map((x) => [x.band, x.at_ms]), [["mf", 0], ["f", 16000]]), JSON.stringify(d));
  }
  {
    const N = [];
    for (let i = 0; i < 12; i++) N.push({ id: i, t_ms: 1000 + 500 * i, vel: 60, voice: 1, note: 72, group: i });
    N[8].vel = 90; N[9].vel = 92; N[10].vel = 95;
    N.push({ id: 100, t_ms: 1000 + 500 * 10, vel: 50, voice: 2, note: 64, group: 10 });
    check("accents (C8): off by default, no marks", accentMarks(N).length === 0);
    check("accents voice: +25 over the voice median, at least 2 notes between accents", same(accentMarks(N, { accents: "voice" }), [8]), JSON.stringify(accentMarks(N, { accents: "voice" })));
    const M2 = N.map((n) => ({ ...n }));
    M2[8].vel = 60; M2[9].vel = 60; M2[10].vel = 95;
    const M3 = M2.map((n) => (n.id === 100 ? { ...n, vel: 52 } : n));
    check("accents voice: never the top note of a chord unless the whole group clears +25", accentMarks(M3, { accents: "voice" }).length === 0 && same(accentMarks(M3.map((n) => (n.id === 100 ? { ...n, voice: 1 } : n)).filter((n) => n.id !== 100), { accents: "voice" }), [10]),
      JSON.stringify(accentMarks(M3, { accents: "voice" })));
  }
  {
    check("key signatures: fifths as performance.py MAJOR_KEY_NAMES spells the tonic (Db -5, F# +6), minor from its relative major", fifthsOf(1, "major") === -5 && fifthsOf(6, "major") === 6 && fifthsOf(9, "minor") === 0 && fifthsOf(0, "minor") === -3);
    const ch = keySignatureChanges([{ start_ms: 0, end_ms: 40000, key: { tonic: 0, mode: "major" } }, { start_ms: 40000, end_ms: 80000, key: { tonic: 9, mode: "minor" } }, { start_ms: 80000, end_ms: 120000, key: { tonic: 3, mode: "major" } }]);
    check("key signatures: A minor after C major is no change; Eb major is one", same(ch.map((c) => [c.at_ms, c.fifths, c.initial]), [[0, 0, true], [80000, -3, false]]), JSON.stringify(ch));
    const shortCh = keySignatureChanges([{ start_ms: 0, end_ms: 40000, key: { tonic: 0, mode: "major" } }, { start_ms: 40000, end_ms: 59000, key: { tonic: 2, mode: "major" } }, { start_ms: 59000, end_ms: 120000, key: { tonic: 7, mode: "major" } }]);
    check("key signatures: a 19 s area stays accidentals (30 s minimum, plan 6.6)", same(shortCh.map((c) => [c.at_ms, c.fifths]), [[0, 0], [59000, 1]]), JSON.stringify(shortCh));
    const ks = createKeySignature();
    const seq = [[0, { tonic: 7, mode: "major", provisional: true }], [1, { tonic: 7, mode: "major", provisional: false }], [2, { tonic: 7, mode: "major" }], [3, { tonic: 7, mode: "major" }], [4, { tonic: 2, mode: "major" }], [5, { tonic: 2, mode: "major" }], [6, { tonic: 2, mode: "major" }]];
    for (const [bar, kv] of seq) ks.step({ keyView: kv, bar, firstUnsettled: bar - 1 });
    check("key signature live: a non-provisional key held 2 bars is placed at the first unsettled bar line", same(ks.placed().map((p) => [p.bar, p.fifths]), [[2, 1], [5, 2]]), JSON.stringify(ks.placed()));
    check("freely: at each entry into tape", same(freelyMarks([{ start_ms: 0, kind: "tape" }, { start_ms: 1, kind: "tape" }, { start_ms: 2, kind: "metric" }, { start_ms: 3, kind: "tape" }]).map((f) => f.at_ms), [0, 3]));
    check("placeAt: linear inside a bar, null outside", same(placeAt([{ index: 4, start_ms: 1000, end_ms: 3000, barTicks: 96 }], 2000), { bar: 4, pos: 48 }) && placeAt([{ index: 4, start_ms: 1000, end_ms: 3000, barTicks: 96 }], 3000) === null);
  }

  // ---- index.js wiring: hands voices by default, pickups, marks, C8, C1/C7 on hands voices, spelling injected
  {
    const [{ take }] = G.familySuite("pickup", [71]);
    const T = take.truth;
    const sc = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: "4/4" });
    const m0 = sc.measures[0];
    check("clean: a pickup family take opens with an implicit anacrusis of 1 beat (2 sub-beats)", !!m0.pickup && m0.pickup.implicit && m0.barTicks === 24 && m0.pickup.ticks === 24 && m0.pickup.subBeats === 2, JSON.stringify({ barTicks: m0.barTicks, pickup: m0.pickup }));
    check("clean: marks on the score, accents 0 by default (C8), clefs per bar", sc.marks && sc.marks.accents.length === 0 && sc.marks.pedal.length > 0 && sc.marks.dynamics.length > 0 && sc.measures.every((m) => m.clefs && m.clefs[1] === "treble"), JSON.stringify(sc.marks && { pedal: sc.marks.pedal.length, dyn: sc.marks.dynamics.length }));
    const voices = new Set(sc.notes.map((n) => n.staff + ":" + n.voice));
    check("clean: hands.js voices by default (staff 1 voices 1-2, staff 2 voices 3-4)", [...voices].every((v) => ["1:1", "1:2", "2:3", "2:4"].includes(v)) && voices.has("2:4"), JSON.stringify([...voices]));
    const a = auditScore(newAudit(), sc, "pickup");
    check("clean: the hands-voiced copy passes the construction audit", auditOk(a), JSON.stringify(auditLine(a)));
    const withVoice = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: "4/4", accents: "voice" });
    check("clean: accents \"voice\" is an option", Array.isArray(withVoice.marks.accents));
    const key = parseKey("C major");
    const sp = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: "4/4", spell: pageSpell, key });
    const byGroup = new Map();
    for (const n of sp.notes) { if (!byGroup.has(n.group)) byGroup.set(n.group, []); byGroup.get(n.group).push(n); }
    let chordTones = 0, agree = 0, spelled = 0;
    for (const list of byGroup.values()) {
      const midis = list.map((n) => n.note), ref = pageSpell(midis, key);
      if (!ref) continue;
      for (const n of list) { const r = ref.find((x) => x.midi === n.note); if (!r) continue; chordTones++; if (n.spelled && n.spelled.letter === r.letter && n.spelled.acc === r.acc) agree++; }
    }
    for (const n of sp.notes) if (n.spelled) spelled++;
    check("spelling injected: every chord tone the score spells equals the page's spellForKey spelling", chordTones > 100 && agree === chordTones, JSON.stringify({ chordTones, agree, spelled, notes: sp.notes.length }));
    const scoreDir = path.join(here, "..", "arsenal", "web", "piano", "score");
    const twins = fs.readdirSync(scoreDir).filter((f) => f.endsWith(".js") && /function\s+spellForKey|spellInKey\s*\(/.test(fs.readFileSync(path.join(scoreDir, f), "utf8")));
    check("spelling injected: no speller in score code (no spellForKey or spellInKey call under score/)", twins.length === 0, JSON.stringify(twins));
    receipts.push({ id: "LS3-spelling-injected", measured: { chordTones, agree, notesSpelled: spelled, notes: sp.notes.length }, threshold: "100% of chord tones equal spellForKey", pass: chordTones > 100 && agree === chordTones });
    const ka = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: "4/4", keyAreas: [{ start_ms: 0, end_ms: 20000, key: { tonic: 0, mode: "major" } }, { start_ms: 20000, end_ms: 1e9, key: { tonic: 7, mode: "major" } }] });
    const kch = ka.marks.keySignatures;
    check("key areas: the opening signature on the first bar and a change at the first bar line at or after the area start", kch.length === 2 && kch[0].bar === ka.measures[0].index && kch[1].fifths === 1 && ka.measures.find((m) => m.index === kch[1].bar).start_ms >= 20000, JSON.stringify(kch));
  }
  {
    // C7 on hands.js voices: a held bass (voice 4) under a moving staff-2 line (voice 3) keeps its heldBass rule: one
    // bar-line tie (no voice-4 onset before bar 1's midpoint) that stops at the next onset in its voice, the line note
    // played as the bass key lifts (5200 ms, tick 168), which is no longer over a held note and so is voice 4; the moving
    // line takes the pedal rule
    const beats = Array.from({ length: 24 }, (_, k) => 1000 + 600 * k);
    const ev = [{ t_ms: 900, kind: "pedal", down: true, value: 100 }, { t_ms: 1000, kind: "on", note: 36, vel: 80 }, { t_ms: 1000, kind: "on", note: 76, vel: 70 }, { t_ms: 1500, kind: "off", note: 76 }];
    for (let k = 1; k < 8; k++) ev.push({ t_ms: 1000 + 600 * k, kind: "on", note: 48 + (k % 3), vel: 60 }, { t_ms: 1000 + 600 * k + 250, kind: "off", note: 48 + (k % 3) });
    ev.push({ t_ms: 5200, kind: "off", note: 36 }, { t_ms: 7400, kind: "pedal", down: false, value: 0 });
    ev.sort((x, y) => x.t_ms - y.t_ms);
    const sc = clean(ev, { beats, one: 1000, meter: "4/4" });
    const bass = sc.notes.find((n) => n.note === 36), mov = sc.notes.filter((n) => n.note >= 48 && n.note < 60);
    const pieces = sc.measures.flatMap((m) => m.voices.flatMap((v) => v.notes.filter((p) => p.id === bass.id).map((p) => [m.index, p.pos, p.dur, p.barTie])));
    const during = mov.filter((n) => n.t_ms < 5200), atLift = mov.filter((n) => n.t_ms >= 5200);
    check("C7 on hands voices: the held bass is voice 4 with one bar-line tie ending at the next voice-4 onset (168), the line above it voice 3",
      bass.voice === 4 && bass.staff === 2 && during.length === 6 && during.every((n) => n.voice === 3) && atLift.length === 1 && atLift[0].voice === 4 && atLift[0].tick === 168 &&
      bass.dur === 168 && same(pieces, [[0, 0, 96, true], [1, 0, 72, false]]), JSON.stringify({ bass, pieces, mov: mov.map((n) => [n.note, n.voice, n.tick, n.dur]) }));
    check("C1 on hands voices: the pedalled moving line fills to its next onset (no rests between)", mov.slice(0, 2).every((n) => n.dur === 24), JSON.stringify(mov.map((n) => [n.tick, n.dur])));
  }
}

// ============================================================================================= receipts ===
if (!quick) {
  // ---- LR7: hands on fixtures
  const t7 = performance.now();
  const rows = [];
  for (const fam of G.FAMILIES) for (const { take, spec } of G.familySuite(fam)) {
    const T = take.truth, byKey = new Map(T.notes.map((n) => [n.note + "|" + Math.round(n.on_ms), n]));
    const truthItems = T.notes.map((n) => ({ id: n.id, staff: n.staff, voice: n.voice, on: n.tick }));
    const TL = links(truthItems);
    // the clean copy (product path)
    const sc = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: spec.meter });
    const est = [];
    for (const n of sc.notes) { const tn = byKey.get(n.note + "|" + Math.round(n.t_ms)); if (tn) est.push({ id: tn.id, staff: n.staff, voice: n.voice, on: n.tick, truthStaff: tn.staff, tick: n.tick, dur: n.dur }); }
    // C1 / C7 written durations on hands.js voices (LR4h reads truth voices; reported here, not gated)
    const durHands = fam === "pedal" || fam === "heldBass" ? MX.durationsExact(est, T.notes).durationsExact : null;
    // the live copy (settled bars)
    const trL = createTranscriber({ options: { meter: spec.meter, beats: T.beats_ms, one: T.downbeats_ms[0] } });
    replayInto(trL, take.events); trL.finish();
    const live = [];
    for (const n of trL.score().notes) { const tn = byKey.get(n.note + "|" + Math.round(n.t_ms)); if (tn) live.push({ id: tn.id, staff: n.staff, voice: n.voice, on: n.tick, truthStaff: tn.staff }); }
    // the module alone and the MIDI 60 split, in truth tick order
    const groups = groupNotes(take.events), hands = createHands();
    for (const g of groups) hands.addGroup(g);
    const snap = hands.snapshot(), all = groups.flatMap((g) => g.notes);
    const pedal = take.events.filter((e) => e.kind === "pedal").map((e) => ({ t_ms: e.t_ms, down: e.down }));
    const vm = assignVoices(all, { staffOf: snap.staffOf, pedal });
    const mod = [], s60 = [];
    for (const x of all) { const tn = byKey.get(x.note + "|" + x.t); if (!tn) continue; const v = vm.get(x.id); mod.push({ id: tn.id, staff: v.staff, voice: v.voice, on: tn.tick, truthStaff: tn.staff }); const sp = splitAt60({ note: x.note }); s60.push({ id: tn.id, staff: sp.staff, voice: sp.voice, on: tn.tick, truthStaff: tn.staff }); }
    const acc = (list) => MX.mean(list.map((e) => +(e.staff === e.truthStaff)));
    rows.push({ fam, meter: spec.meter, tex: spec.texture, rub: spec.rub, durHands, clefs: clefStats(sc.measures), clefsOctaveFirst: clefStats(withClefs(sc.measures, { outOfRange: "octave" })), clean: { staff: acc(est), f1: linkF1(TL, links(est)), n: est.length / T.notes.length }, live: { staff: acc(live), f1: linkF1(TL, links(live)) }, module: { staff: acc(mod), f1: linkF1(TL, links(mod)) }, split60: { staff: acc(s60), f1: linkF1(TL, links(s60)) } });
  }
  const agg = (key, pick = rows) => ({ staff: MX.mean(pick.map((r) => r[key].staff)), voiceF1: MX.mean(pick.map((r) => r[key].f1)) });
  const byTex = Object.fromEntries(["ballad", "arp", "mixed"].map((t) => [t, agg("clean", rows.filter((r) => r.tex === t))]));
  const LR7 = { clean: agg("clean"), live: agg("live"), module: agg("module"), split60: agg("split60"), cleanByTexture: byTex, cleanPlacedShare: MX.mean(rows.map((r) => r.clean.n)), takes: rows.length,
    durationsExactOnHandsVoices: { pedal: MX.mean(rows.filter((r) => r.fam === "pedal").map((r) => r.durHands)), heldBass: MX.mean(rows.filter((r) => r.fam === "heldBass").map((r) => r.durHands)) } };
  receipts.push({ id: "LR7", measured: LR7, threshold: "clean copy on fixtures: staff accuracy >= 0.95 / voice F1 >= 0.90", pass: LR7.clean.staff >= 0.95 && LR7.clean.voiceF1 >= 0.9, ms: Math.round(performance.now() - t7) });
  check("LR7 staff accuracy >= 0.95 (clean copy, fixtures)", LR7.clean.staff >= 0.95, JSON.stringify(LR7.clean));
  check("LR7 voice F1 >= 0.90 (clean copy, fixtures)", LR7.clean.voiceF1 >= 0.9, JSON.stringify(LR7.clean));
  // ---- clefs and octave lines on the fixture clean copies (repair LS3 r1)
  const CF = { clef: sumStats(rows.map((r) => r.clefs)), octaveFirst: sumStats(rows.map((r) => r.clefsOctaveFirst)), takes: rows.length };
  receipts.push({ id: "LS3-clefs-fixtures", measured: CF, threshold: "0 note pieces beyond 3 ledger lines on bars some clef and octave line hold (clean copies, every LS0 family, held-out seeds); outOfRange octave reported", pass: CF.clef.beyondHoldable === 0 });
  check("clefs on fixture clean copies: 0 note pieces beyond 3 ledger lines on holdable bars", CF.clef.beyondHoldable === 0, JSON.stringify(CF));

  // ---- LR3d: the subdivision chip
  const t3 = performance.now();
  const chipRun = (events, meter, beatsMs, chipRule) => {
    const tr = createTranscriber({ options: { meter, chipRule } });
    let first = null;
    replayInto(tr, events, { onTick: (out, T) => { if (first == null && out.header.chip && out.header.chip.kind === "triplets") first = T; } });
    const lim = beatsMs[Math.min(beatsMs.length - 1, 32)];
    return { within: first != null && first <= lim, any: first != null };
  };
  const c44 = G.familySuite("compound44").map(({ take }) => ({ events: take.events, beats: take.truth.beats_ms.slice(take.truth.lead) }));
  const straight = [];
  for (const fam of G.FAMILIES) for (const { take, spec } of G.familySuite(fam)) if (spec.meter === "4/4" || spec.meter === "3/4") straight.push({ events: take.events, meter: spec.meter, beats: take.truth.beats_ms.slice(take.truth.lead) });
  for (const r of G.tempoSuite()) if (r.meter !== "6/8") straight.push({ events: G.eventsOf(r.piece), meter: r.meter, beats: r.piece.truth.beats_ms.slice(r.piece.truth.pickup) });
  const lr3d = {};
  for (const rule of ["grid", "tatum"]) {
    const h = c44.map((x) => chipRun(x.events, "4/4", x.beats, rule)), f = straight.map((x) => chipRun(x.events, x.meter, x.beats, rule));
    lr3d[rule] = { hit: h.filter((x) => x.within).length / h.length, hitAny: h.filter((x) => x.any).length / h.length, falseWithin32: f.filter((x) => x.within).length / f.length, falseAny: f.filter((x) => x.any).length / f.length, compoundTakes: h.length, straightTakes: f.length };
  }
  receipts.push({ id: "LR3d", measured: lr3d, threshold: "chipRule grid (C11 as written): hit within 32 beats >= 0.90 on 12/8 under 4/4; false within 32 beats <= 0.05 on straight 4/4 and 3/4 (start values); tatum reported", pass: lr3d.grid.hit >= 0.9 && lr3d.grid.falseWithin32 <= 0.05, ms: Math.round(performance.now() - t3) });
  check("LR3d chip hit >= 90% within 32 beats (12/8 under 4/4)", lr3d.grid.hit >= 0.9, JSON.stringify(lr3d.grid));
  check("LR3d chip false <= 5% within 32 beats (straight 4/4, 3/4)", lr3d.grid.falseWithin32 <= 0.05, JSON.stringify(lr3d.grid));

  // ---- header hold after a family press (ls1-rulings.md), on the LS1 button pins
  const th = performance.now();
  const pins = [
    { name: "6/8 arp 50", meter: "6/8", ev: G.eventsOf(G.genPiece("6/8", "arp", 0, 50, 4242, { pickup: 0 })) },
    { name: "12/8 arp 50", meter: "12/8", ev: G.eventsOf(G.genScore("12/8", "arp", 0, 50, 4242)) },
    { name: "4/4 arp 63", meter: "4/4", ev: G.eventsOf(G.genPiece("4/4", "arp", 0, 63, 4242, { pickup: 0 })) },
  ];
  const AT = 20000, hrows = [];
  for (const pin of pins) for (const ratio of FAMILY_RATIOS) {
    const tr = createTranscriber({ options: { meter: pin.meter } });
    let pre = null, pressT = null, confirmT = null, blank = 0, pending = 0, pendingOk = 0, pendingNear = 0, postConfirmHold = 0;
    replayInto(tr, pin.ev, { endMs: AT + 45000, onTick: (out, T, t) => {
      const h = out.header;
      if (pressT == null) { if (T >= AT && h.bpmShown != null) { pre = h; pressT = T; t.chooseLevel(ratio); } return; }
      if (h.bpm == null) blank++;
      if (confirmT == null) {
        if (h.dim && h.word === "hold" && h.requested != null) { pending++; if (Math.abs(h.bpm / h.requested - 1) <= 0.03) pendingOk++; if (Math.abs(h.requested / (pre.bpmShown * ratio) - 1) <= 0.03) pendingNear++; }
        else confirmT = T;
      } else if (h.word === "hold" && h.dim && out.header.bpmShown != null && h.requested != null) postConfirmHold++;
    } });
    hrows.push({ pin: pin.name, ratio: +ratio.toFixed(3), waitS: confirmT == null ? null : (confirmT - pressT) / 1000, blank, pending, pendingOk, pendingNear, postConfirmHold });
  }
  const confirmed = hrows.filter((r) => r.waitS != null);
  const waits = Object.fromEntries(FAMILY_RATIOS.map((q) => [+q.toFixed(3), hrows.filter((r) => r.ratio === +q.toFixed(3)).map((r) => r.waitS)]));
  const H = { presses: hrows.length, confirmed: confirmed.length, blankTicks: hrows.reduce((s, r) => s + r.blank, 0), pendingTicks: hrows.reduce((s, r) => s + r.pending, 0),
    pendingShowsRequest: hrows.reduce((s, r) => s + r.pendingOk, 0) / Math.max(1, hrows.reduce((s, r) => s + r.pending, 0)),
    requestWithin3OfShownTimesRatio: hrows.reduce((s, r) => s + r.pendingNear, 0) / Math.max(1, hrows.reduce((s, r) => s + r.pending, 0)), waitsS: waits };
  receipts.push({ id: "LS3-header-hold", measured: H, threshold: "0 blank ticks after a press; every pending tick shows the request dimmed with hold; every press confirmed; request within 3% of shown x ratio reported", pass: H.blankTicks === 0 && H.pendingShowsRequest === 1 && H.confirmed === H.presses, ms: Math.round(performance.now() - th) });
  check("header hold: 0 blank ticks after a press, the dimmed request on every pending tick, every press confirmed", H.blankTicks === 0 && H.pendingShowsRequest === 1 && H.confirmed === H.presses, JSON.stringify(hrows));
  // no press: the header is bpmShown in full ink except during a hold
  let ctrlBad = 0, ctrlTicks = 0;
  for (const r of G.tempoSuite().slice(0, 9)) {
    const tr = createTranscriber({ options: { meter: r.meter } });
    replayInto(tr, G.eventsOf(r.piece), { onTick: (out) => { ctrlTicks++; const h = out.header; if (h.word !== "hold" && (h.bpm !== h.bpmShown || h.dim)) ctrlBad++; } });
  }
  check("header with no press: bpmShown in full ink on every tick outside a hold", ctrlTicks > 1000 && ctrlBad === 0, JSON.stringify({ ctrlTicks, ctrlBad }));
}

// ============================================================================================ sessions ===
if (sessions) {
  const ROOT = path.join(here, "..", "state", "arsenal", "performance"), OUT = path.join(here, "..", "state", "arsenal", "score");
  if (!fs.existsSync(ROOT)) console.log("sessions: state/arsenal/performance is missing, skipped");
  else {
    const t8 = performance.now();
    const dirs = fs.readdirSync(ROOT).filter((d) => fs.existsSync(path.join(ROOT, d, "events.jsonl"))).sort();
    const srows = [];
    const ALL = { bars: [], metricBars: [] };
    dirs.forEach((d, i) => {
      const name = "S" + (i + 1);
      const events = fs.readFileSync(path.join(ROOT, d, "events.jsonl"), "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l))
        .filter((e) => e.kind === "on" || e.kind === "off" || e.kind === "pedal" || e.kind === "sound_end");
      const ons = events.filter((e) => e.kind === "on");
      if (ons.length < 100) { srows.push({ name, skipped: true }); return; }
      let keyAreas = null;
      const sumPath = path.join(ROOT, d, "summary.json");
      if (fs.existsSync(sumPath)) {
        const nv = JSON.parse(fs.readFileSync(sumPath, "utf8")).nashville;
        const areas = ((nv && nv.areas) || []).filter((a) => a.key && Number.isInteger(a.key.tonic));
        if (areas.length) keyAreas = areas.map((a) => ({ start_ms: a.start_s * 1000, end_ms: a.end_s * 1000, key: { tonic: a.key.tonic, mode: a.key.mode } }));
      }
      const minutes = (ons[ons.length - 1].t_ms - ons[0].t_ms) / 60000;
      const sc = clean(events, { meter: "4/4", keyAreas });
      const scV = clean(events, { meter: "4/4", keyAreas, accents: "voice" });
      const pedal = events.filter((e) => e.kind === "pedal").map((e) => ({ t_ms: e.t_ms, down: !!e.down })).sort((a, b) => a.t_ms - b.t_ms);
      const downShare = (a, z) => { let st = false, t = a, dn = 0; for (const p of pedal) { if (p.t_ms <= a) { st = p.down; continue; } if (p.t_ms >= z) break; if (st) dn += p.t_ms - t; st = p.down; t = p.t_ms; } if (st) dn += z - t; return z > a ? dn / (z - a) : 0; };
      const perBar = sc.measures.map((m) => {
        const staves = new Map();
        let ties = 0, rests = [], voicesWithNotes = 0;
        for (const v of m.voices) {
          if (!staves.has(v.staff)) staves.set(v.staff, new Set());
          if (v.notes.length) { staves.get(v.staff).add(v.voice); voicesWithNotes++; rests.push(v.rests.length); }
          ties += v.notes.filter((p) => p.tieStart).length;
        }
        const pedalMarksHere = sc.marks.pedal.filter((pm) => pm.bar === m.index).length;
        return { index: m.index, kind: m.kind, tuplets: new Set(m.tuplets.map((x) => x.voice + ":" + x.beat)).size, ties, voicesPerStaff: Math.max(0, ...[...staves.values()].map((s) => s.size)), beats: m.beats, pedalMarks: pedalMarksHere, pedalled: downShare(m.start_ms, m.end_ms) >= 0.5, rests };
      });
      ALL.bars.push(...perBar); ALL.metricBars.push(...perBar.filter((b) => b.kind === "metric"));
      // LR8c: bar-line ties per held-bass note (voice 4 of the lower staff)
      const barTiesOf = new Map();
      for (const m of sc.measures) for (const v of m.voices) for (const p of v.notes) if (p.barTie) barTiesOf.set(p.id, (barTiesOf.get(p.id) || 0) + 1);
      const held = sc.notes.filter((n) => n.staff === 2 && n.voice === 4);
      const heldOver1 = held.filter((n) => (barTiesOf.get(n.id) || 0) > 1).length;
      // key signature changes per 30 s of key area
      const changes = sc.marks.keySignatures.filter((k) => !k.initial).length, areaS = keyAreas ? keyAreas.reduce((s, a) => s + (a.end_ms - a.start_ms) / 1000, 0) : null;
      const perArea = keyAreas ? keyAreas.map((a, j) => ({ s: (a.end_ms - a.start_ms) / 1000, changes: sc.marks.keySignatures.filter((k) => !k.initial && k.at_ms === a.start_ms).length })) : [];
      const audit = auditScore(newAudit(), sc, "session");
      srows.push({ name, minutes: +minutes.toFixed(2), onsets: ons.length, bars: perBar.length, metricBars: perBar.filter((b) => b.kind === "metric").length,
        medians: { tuplets: MX.median(perBar.map((b) => b.tuplets)), ties: MX.median(perBar.map((b) => b.ties)), voicesPerStaff: MX.median(perBar.map((b) => b.voicesPerStaff)) },
        pedalMarksPerBeat: perBar.reduce((s, b) => s + b.pedalMarks, 0) / Math.max(1, perBar.reduce((s, b) => s + b.beats, 0)),
        pedalMarks: sc.marks.pedal.length, conPedPhrases: sc.marks.conPed.length, pedalMarksNoConPed: clean(events, { meter: "4/4", options: { conPed: false } }).marks.pedal.length,
        dynamicsPerMin: sc.marks.dynamics.length / minutes,
        keyAreas: keyAreas ? keyAreas.length : 0, keyChanges: changes, keyChangesPer30s: areaS ? changes / (areaS / 30) : null, keyAreaMaxChangesPer30s: perArea.length ? Math.max(...perArea.map((a) => a.changes / Math.max(1e-9, a.s / 30))) : null, shortestAreaS: perArea.length ? Math.min(...perArea.map((a) => a.s)) : null,
        lr8b: { pedalledBars: perBar.filter((b) => b.pedalled).length, medianRestsPerVoice: MX.median(perBar.filter((b) => b.pedalled).flatMap((b) => b.rests)) },
        lr8c: { heldBassNotes: held.length, over1: heldOver1 },
        lr8d: { defaultPerMin: sc.marks.accents.length / minutes, voicePerMin: scV.marks.accents.length / minutes },
        clefs: clefStats(sc.measures), clefsOctaveFirst: clefStats(withClefs(sc.measures, { outOfRange: "octave" })),
        audit: auditLine(audit) });
    });
    const used = srows.filter((r) => !r.skipped);
    const medianOver = (bars, k) => MX.median(bars.map((b) => b[k]));
    const LR8 = {
      pooled: { bars: ALL.bars.length, tuplets: medianOver(ALL.bars, "tuplets"), ties: medianOver(ALL.bars, "ties"), voicesPerStaff: medianOver(ALL.bars, "voicesPerStaff"), pedalMarksPerBeat: ALL.bars.reduce((s, b) => s + b.pedalMarks, 0) / Math.max(1, ALL.bars.reduce((s, b) => s + b.beats, 0)), beatsWithOver1PedalMark: null },
      metricPooled: { bars: ALL.metricBars.length, tuplets: medianOver(ALL.metricBars, "tuplets"), ties: medianOver(ALL.metricBars, "ties"), voicesPerStaff: medianOver(ALL.metricBars, "voicesPerStaff") },
      worstSession: { tuplets: Math.max(...used.map((r) => r.medians.tuplets)), ties: Math.max(...used.map((r) => r.medians.ties)), voicesPerStaff: Math.max(...used.map((r) => r.medians.voicesPerStaff)), pedalMarksPerBeat: Math.max(...used.map((r) => r.pedalMarksPerBeat)), dynamicsPerMin: Math.max(...used.map((r) => r.dynamicsPerMin)), keyChangesPer30s: Math.max(...used.map((r) => r.keyChangesPer30s ?? 0)), keyAreaMaxChangesPer30s: Math.max(...used.map((r) => r.keyAreaMaxChangesPer30s ?? 0)) },
    };
    const lr8Pass = used.every((r) => r.medians.tuplets <= 1 && r.medians.ties <= 2 && r.medians.voicesPerStaff <= 2 && r.pedalMarksPerBeat <= 1 && r.dynamicsPerMin <= 3 && (r.keyAreaMaxChangesPer30s == null || r.keyAreaMaxChangesPer30s <= 1));
    const lr8b = { perSession: Object.fromEntries(used.map((r) => [r.name, r.lr8b.medianRestsPerVoice])), pooledMedian: MX.median(ALL.bars.filter((b) => b.pedalled).flatMap((b) => b.rests)), pedalledBars: ALL.bars.filter((b) => b.pedalled).length };
    const lr8c = { heldBassNotes: used.reduce((s, r) => s + r.lr8c.heldBassNotes, 0), over1: used.reduce((s, r) => s + r.lr8c.over1, 0) };
    const lr8d = { defaultPerMinMax: Math.max(...used.map((r) => r.lr8d.defaultPerMin)), voicePerMin: Object.fromEntries(used.map((r) => [r.name, +r.lr8d.voicePerMin.toFixed(2)])) };
    const auditSum = Object.fromEntries(["notePieces", "rests", "badNotes", "badRests", "untiled", "danglingBarTies", "twoBarLines", "overlaps"].map((k) => [k, used.reduce((s, r) => s + r.audit[k], 0)]));
    const CS = { clef: sumStats(used.map((r) => r.clefs)), octaveFirst: sumStats(used.map((r) => r.clefsOctaveFirst)), minutes: +used.reduce((s, r) => s + r.minutes, 0).toFixed(2),
      worstSession: { changesPer100Bars: Math.max(...used.map((r) => (100 * (r.clefs.changesBars + r.clefs.changesRange)) / Math.max(1, r.clefs.bars))), changesPer100BarsOctaveFirst: Math.max(...used.map((r) => (100 * (r.clefsOctaveFirst.changesBars + r.clefsOctaveFirst.changesRange)) / Math.max(1, r.clefsOctaveFirst.bars))) } };
    const summary = { date: "2026-09-15", slice: "LS3", config: "clean(), meter 4/4, inferred beats, hands.js voices, marks.js defaults (conPed on, accents off), key areas from summary.json", sessions: srows.length, skipped: srows.filter((r) => r.skipped).map((r) => r.name), LR8, LR8pass: lr8Pass, LR8b: lr8b, LR8c: lr8c, LR8d: lr8d, audit: auditSum, clefs: CS, rows: srows, ms: Math.round(performance.now() - t8) };
    receipts.push({ id: "LS3-clefs-sessions", measured: CS, threshold: "0 note pieces beyond 3 ledger lines on bars some clef and octave line hold (S1..Sn clean copies); outOfRange octave reported", pass: CS.clef.beyondHoldable === 0 });
    check("clefs on S1..Sn clean copies: 0 note pieces beyond 3 ledger lines on holdable bars", CS.clef.beyondHoldable === 0, JSON.stringify(CS));
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, "ls3-bench-2026-09-15.json"), JSON.stringify(summary, null, 1));
    receipts.push({ id: "LR8", measured: { ...LR8, perSession: Object.fromEntries(used.map((r) => [r.name, { ...r.medians, pedalMarksPerBeat: +r.pedalMarksPerBeat.toFixed(3), dynamicsPerMin: +r.dynamicsPerMin.toFixed(2), keyChangesPer30s: r.keyChangesPer30s == null ? null : +r.keyChangesPer30s.toFixed(3), keyAreaMaxChangesPer30s: r.keyAreaMaxChangesPer30s == null ? null : +r.keyAreaMaxChangesPer30s.toFixed(3) }])) }, threshold: "every session: median per bar tuplet brackets <= 1, ties <= 2, voices per staff <= 2; pedal marks <= 1 per beat; dynamics <= 3 per min; key signature changes <= 1 per 30 s of key area", pass: lr8Pass });
    receipts.push({ id: "LR8b", measured: lr8b, threshold: "median rests per voice per pedalled bar <= 1 (every session)", pass: used.every((r) => !(r.lr8b.medianRestsPerVoice > 1)) });
    receipts.push({ id: "LR8c", measured: lr8c, threshold: "bar-line ties per held-bass note <= 1 on every note", pass: lr8c.over1 === 0 });
    receipts.push({ id: "LR8d", measured: lr8d, threshold: "0 accents per minute with defaults; voice reported", pass: lr8d.defaultPerMinMax === 0 });
    receipts.push({ id: "LS3-audit-sessions", measured: auditSum, threshold: "0 on the five construction properties (hands voices, clean copies)", pass: auditSum.badNotes + auditSum.badRests + auditSum.untiled + auditSum.danglingBarTies + auditSum.twoBarLines + auditSum.overlaps === 0 });
    check("LR8 S1..Sn readability proxies", lr8Pass, JSON.stringify(LR8.worstSession));
    check("LR8b S1..Sn median rests per voice per pedalled bar <= 1", used.every((r) => !(r.lr8b.medianRestsPerVoice > 1)), JSON.stringify(lr8b));
    check("LR8c S1..Sn bar-line ties per held-bass note <= 1", lr8c.over1 === 0, JSON.stringify(lr8c));
    check("LR8d S1..Sn 0 accents per minute by default", lr8d.defaultPerMinMax === 0);
    check("S1..Sn clean copies with hands voices pass the construction audit", receipts[receipts.length - 1].pass, JSON.stringify(auditSum));
    console.log("sessions bench written to state/arsenal/score/ls3-bench-2026-09-15.json");
  }
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => r4(v)));
console.log(`score_hands: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
