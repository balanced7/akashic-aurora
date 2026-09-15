// Node tests for the live sheet music export writers and CLI (slice LS4): arsenal/web/piano/score/musicxml.js, midi.js,
// export.js and arsenal/score_cli.mjs. research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections
// 7.4, 8 and 10.3, amended by plan-amendments.md C3, C5 and section 6 LS4, and ls1-rulings.md. Zero dependencies:
//   node tests/score_export.test.mjs              contracts, then LR9a-c on synthetic fixtures (every LS0 family on held-out
//                                                 seeds, with oracle beats and with inferred beats; free pieces; tape runs).
//                                                 Fixture exports go to state/arsenal/score/ls4-fixtures/<case>/ with an
//                                                 events.jsonl copy and export.json, for tests/test_score_export.py
//   node tests/score_export.test.mjs --quick      contracts only
//   node tests/score_export.test.mjs --sessions   also score_cli bench over S1..Sn (every session with a note-on): exports to
//                                                 state/arsenal/score/<session>/full/, aggregates (S-numbers, counts) to
//                                                 state/arsenal/score/ls4-bench-<date>.json, and the construction audit on
//                                                 every export view
// Definitions: LR9a, LR9b and LR9c as verifyExport in arsenal/score_cli.mjs (the header there). LS4-audit: the five
// construction properties of tests/fixtures/score/audit.mjs on the export view (forced bars included).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import { newAudit, auditScore, auditOk, auditLine } from "./fixtures/score/audit.mjs";
import { toMusicXML, pitchOf, timeSignatureOf } from "../arsenal/web/piano/score/musicxml.js";
import { performanceMid, quantizedMid, soundingNotes } from "../arsenal/web/piano/score/midi.js";
import { parseKey } from "../arsenal/web/piano/nashville.js";
import { parseArgs, parseTime, takeOptions, takeName, pageSpeller, buildTake, writeTake, verifyExport, readSmf, bench, SCORE_ROOT, readMusicXML as readMusicXMLFor } from "../arsenal/score_cli.mjs";

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
const count = (s, re) => (s.match(re) || []).length;

const spell = pageSpeller();
check("the page speller builds read-only from the page sources", typeof spell === "function", String(spell));
const oracle = (take, spec, extra = {}) => ({ ...takeOptions({ meter: spec.meter }), beats: take.truth.beats_ms, one: take.truth.downbeats_ms[0], ...extra });
const build = (events, options, more = {}) => buildTake({ events, options, spell, ...more });
const verifyOk = (label, b) => {
  const v = verifyExport(b), a = auditScore(newAudit(), b.view, label);
  check(`${label}: LR9a-c on the export`, v.pass, JSON.stringify({ lr9a: v.lr9a, lr9b: v.lr9b, lr9c: v.lr9c }));
  check(`${label}: the export view passes the construction audit`, auditOk(a), JSON.stringify({ ...auditLine(a), ex: a.examples }));
  return v;
};

// ============================================================================================ contracts ===
{
  // ---- CLI arguments
  check("parseTime: m:ss and seconds", parseTime("3:43") === 223000 && parseTime("12.40") === 12400 && parseTime("1:02.5") === 62500 && parseTime("0:05") === 5000);
  let threw = false; try { parseTime("3m"); } catch { threw = true; }
  check("parseTime: a bad time throws", threw);
  check("parseArgs: flags with values, = and bare", same(parseArgs(["export", "S3", "--at", "3:43", "--seconds=30", "--quick"]), { _: ["export", "S3"], at: "3:43", seconds: "30", quick: true }));
  const o = takeOptions({ at: "3:43", seconds: "30", meter: "3/4" });
  check("takeOptions: span, meter", same(o.span, { from_ms: 223000, to_ms: 253000 }) && o.meter === "3/4" && o.feel === "straight");
  check("takeName: from the span and flags", takeName(o) === "at-223s-30s-3-4" && takeName(takeOptions({})) === "full" && takeName(takeOptions({ bpm: "70" })) === "full-bpm70");
  threw = false; try { takeName(takeOptions({}), { take: "../escape" }); } catch { threw = true; }
  check("takeName: a take name cannot leave the score folder", threw);
  threw = false; try { writeTake(path.join(SCORE_ROOT, "..", "escape-test"), null); } catch (e) { threw = /refusing to write outside/.test(e.message); }
  check("writeTake: refuses a folder outside state/arsenal/score", threw);
  for (const bad of [{ meter: "5/4" }, { feel: "swing" }, { bpm: "5" }, { seconds: "-1" }]) { threw = false; try { takeOptions(bad); } catch { threw = true; } check(`takeOptions rejects ${JSON.stringify(bad)}`, threw); }

  // ---- performance.mid (C5): every logged on, off and crossing at its time; end offs only for pitches left open
  const ev = [
    { t_ms: 0, kind: "on", note: 60, vel: 80 }, { t_ms: 0, kind: "pedal", down: true, value: 100 }, { t_ms: 50, kind: "pedal", down: true, value: 90 },
    { t_ms: 127, kind: "on", note: 64, vel: 0 }, { t_ms: 128, kind: "off", note: 60 }, { t_ms: 128, kind: "sound_end", note: 60, by: "pedal" },
    { t_ms: 16383, kind: "on", note: 67, vel: 90 }, { t_ms: 16384, kind: "on", note: 67, vel: 91 }, { t_ms: 30, kind: "off", note: 72 },
    { t_ms: 2097152, kind: "pedal", down: false, value: 0 }, { t_ms: 2097152, kind: "off", note: 67 }, { t_ms: 2097153, kind: "on", note: 71, vel: 200 },
    { t_ms: 60, kind: "chord", chord: "C" },
  ];
  const st = {}, smf = readSmf(performanceMid(ev, { stats: st }));
  const tr = smf.tracks[0];
  const ons = tr.filter((e) => e.status === 0x90 && e.b > 0).map((e) => [e.tick, e.a, e.b]);
  const offs = tr.filter((e) => e.status === 0x80).map((e) => [e.tick, e.a]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cc = tr.filter((e) => e.status === 0xb0).map((e) => [e.tick, e.a, e.b]);
  const tempo = tr.find((e) => e.meta === 0x51);
  check("performance.mid: SMF type 0, one track, PPQ 500, tempo 500,000 us (1 tick = 1 ms)", smf.format === 0 && smf.ntracks === 1 && smf.ppq === 500 && tempo && same(tempo.data, [0x07, 0xa1, 0x20]) && tempo.tick === 0);
  check("performance.mid: ons at their ms across VLQ widths (0, 127, 16383, 16384, 2097153), velocity 0 and 200 clamped", same(ons, [[0, 60, 80], [127, 64, 1], [16383, 67, 90], [16384, 67, 91], [2097153, 71, 127]]), JSON.stringify(ons));
  check("performance.mid: logged offs as logged (an orphan off too), end offs at the last tick for pitches left open", same(offs, [[30, 72], [128, 60], [2097152, 67], [2097153, 64], [2097153, 67], [2097153, 71]]), JSON.stringify(offs));
  check("performance.mid: CC64 127 / 0 at crossings only (a repeated down is not written)", same(cc, [[0, 64, 127], [2097152, 64, 0]]), JSON.stringify(cc));
  check("performance.mid: stats", st.ons === 5 && st.offs === 3 && st.pedalCrossings === 2 && st.pedalNonCrossings === 1 && st.endOffs === 3 && st.velClamped === 2 && st.rounded === 0, JSON.stringify(st));
  const order0 = tr.filter((e) => e.tick === 0).map((e) => (e.meta != null ? "meta" : e.status === 0xb0 ? "cc" : "on"));
  const orderEnd = tr.filter((e) => e.tick === 2097152).map((e) => (e.status === 0xb0 ? "cc" : "off"));
  check("performance.mid: at one tick off, pedal, on (the replay order)", same(order0, ["meta", "cc", "on"]) && same(orderEnd, ["off", "cc"]), JSON.stringify({ order0, orderEnd }));
  const s2 = readSmf(performanceMid([{ t_ms: 1500, kind: "on", note: 60, vel: 70 }, { t_ms: 1700, kind: "off", note: 60 }], { t0_ms: 1000 }));
  check("performance.mid: t0 shifts every time by the span start", same(s2.tracks[0].filter((e) => e.status).map((e) => e.tick), [500, 700]));
}
{
  // ---- MusicXML and quantized.mid on fixtures with oracle beats
  const [{ take: pk, spec: pks }] = G.familySuite("pickup", [71]);
  const b = build(pk.events, oracle(pk, pks));
  verifyOk("pickup oracle", b);
  check("musicxml: a leading anacrusis is measure 0, implicit", /<measure number="0" implicit="yes">/.test(b.xml) && b.stats.musicxml.pickups >= 1);
  check("musicxml: MusicXML 4.0 partwise, divisions 24, two staves, treble and bass clefs", /<score-partwise version="4.0">/.test(b.xml) && /<divisions>24<\/divisions>/.test(b.xml) && /<staves>2<\/staves>/.test(b.xml) && /<clef number="1"><sign>G<\/sign><line>2<\/line><\/clef><clef number="2"><sign>F<\/sign><line>4<\/line><\/clef>/.test(b.xml));
  check("musicxml: spelled by the injected page speller (no fallback names)", b.stats.musicxml.unspelledNotes === 0, JSON.stringify(b.stats.musicxml.unspelledNotes));
  const q = readSmf(b.quant), sn = soundingNotes(b.view);
  const tempos = q.tracks[0].filter((e) => e.meta === 0x51).length, beats = b.view.measures.reduce((s, m) => s + m.beats, 0);
  check("quantized.mid: SMF type 1, 3 tracks, PPQ 480, a tempo event per tactus beat", q.format === 1 && q.ntracks === 3 && q.ppq === 480 && tempos === beats, JSON.stringify({ tempos, beats }));
  const perTrack = [1, 2].map((t) => q.tracks[t].filter((e) => e.status === 0x90).length);
  check("quantized.mid: the upper staff on track 1, the lower on track 2", same(perTrack, [sn.filter((n) => n.staff !== 2).length, sn.filter((n) => n.staff === 2).length]), JSON.stringify(perTrack));
  const firstOn = [1, 2].flatMap((t) => q.tracks[t].filter((e) => e.status === 0x90)).sort((x, y) => x.tick - y.tick)[0];
  check("quantized.mid: 20 ticks per score tick", firstOn.tick === Math.min(...sn.map((n) => n.tick)) * 20);

  // metronome "c. N" and rubato
  const rows = G.familySuite("pedal").filter((r) => r.spec.meter === "4/4");
  const rub0 = rows.filter((r) => r.spec.rub === 0), rub2 = rows.filter((r) => r.spec.rub === 2);
  let markOk = 0, rub0Rubato = 0, rub2Rubato = 0;
  for (const r of rub0) {
    const x = build(r.take.events, oracle(r.take, r.spec)).xml, m = /<per-minute>c\. (\d+)<\/per-minute>/.exec(x);
    if (m && Math.abs(Number(m[1]) - r.spec.bpm) <= 2) markOk++;
    if (/<words>rubato<\/words>/.test(x)) rub0Rubato++;
  }
  for (const r of rub2) if (/<words>rubato<\/words>/.test(build(r.take.events, oracle(r.take, r.spec)).xml)) rub2Rubato++;
  check("musicxml: metronome per-minute \"c. N\" within 2 bpm of a steady take's tempo; no rubato on steady takes", markOk === rub0.length && rub0Rubato === 0, JSON.stringify({ markOk, rub0: rub0.length, rub0Rubato }));
  check("musicxml: rubato beside the mark on strong-rubato takes", rub2Rubato === rub2.length, JSON.stringify({ rub2Rubato, rub2: rub2.length }));

  // tuplets: sextuplets 6:4, triplets 3:2, compound duplets 2:3; brackets
  const [{ take: sx, spec: sxs }] = G.familySuite("sextuplet", [71]);
  const bs = build(sx.events, oracle(sx, sxs));
  verifyOk("sextuplet oracle", bs);
  check("musicxml: sextuplets as 6:4 time-modification with a bracketed tuplet", /<time-modification><actual-notes>6<\/actual-notes><normal-notes>4<\/normal-notes><\/time-modification>/.test(bs.xml) && /<tuplet type="start" bracket="yes"\/>/.test(bs.xml) && count(bs.xml, /<tuplet type="start"/g) === count(bs.xml, /<tuplet type="stop"/g));
  let trip = 0, dup = 0, dot = 0, pedChange = 0, pedAttrsBad = 0;
  for (const r of G.familySuite("pedal", [71])) {
    const x = build(r.take.events, oracle(r.take, r.spec)).xml;
    if (/<actual-notes>3<\/actual-notes><normal-notes>2<\/normal-notes>/.test(x)) trip++;
    if (/<actual-notes>2<\/actual-notes><normal-notes>3<\/normal-notes>/.test(x)) dup++;
    if (r.spec.meter === "12/8" && /<beat-unit>quarter<\/beat-unit><beat-unit-dot\/>/.test(x) && /<beats>12<\/beats><beat-type>8<\/beat-type>/.test(x)) dot++;
    if (/<pedal type="change" line="yes" sign="no"\/>/.test(x)) pedChange++;
    pedAttrsBad += count(x, /<pedal (?![^>]*line="yes" sign="no")/g);
  }
  check("musicxml: triplets 3:2 on simple-meter fixtures", trip > 0, String(trip));
  check("musicxml: compound meter: 12/8 time, a dotted-quarter metronome unit, duplets 2:3", dot === 9 && dup > 0, JSON.stringify({ dot, dup }));
  check("musicxml: pedal change notches as line pedals with no sign", pedChange > 0 && pedAttrsBad === 0, JSON.stringify({ pedChange, pedAttrsBad }));

  // key signatures from key areas, with a double bar before a change
  const ka = build(pk.events, oracle(pk, pks), { keyAreas: [{ start_ms: 0, end_ms: 20000, key: parseKey("C major") }, { start_ms: 20000, end_ms: 1e9, key: parseKey("D major") }] });
  verifyOk("key areas", ka);
  const keys = [...ka.xml.matchAll(/<key><fifths>(-?\d+)<\/fifths>(?:<mode>(\w+)<\/mode>)?<\/key>/g)].map((m) => [Number(m[1]), m[2]]);
  check("musicxml: the opening signature and one change at the area's first bar line, after a light-light bar line", same(keys, [[0, "major"], [2, "major"]]) && /light-light<\/bar-style><\/barline>\s*<\/measure>\s*<measure number="\d+"[^>]*>\s*<attributes><key><fifths>2/.test(ka.xml), JSON.stringify(keys));

  // spelling in D-flat major: diatonic notes carry flats from the signature, no sharps, no accidentals
  const beatsDb = Array.from({ length: 24 }, (_, k) => 1000 + 500 * k);
  const evDb = [{ t_ms: 1000, kind: "on", note: 49, vel: 70 }, { t_ms: 4900, kind: "off", note: 49 }];
  [61, 63, 65, 66, 68, 70, 72, 73].forEach((n, k) => evDb.push({ t_ms: 1000 + 500 * k, kind: "on", note: n, vel: 64 }, { t_ms: 1000 + 500 * k + 450, kind: "off", note: n }));
  evDb.sort((a, b) => a.t_ms - b.t_ms);
  const db = build(evDb, { ...takeOptions({}), beats: beatsDb, one: 1000 }, { keyAreas: [{ start_ms: 0, end_ms: 1e9, key: parseKey("Db major") }] });
  verifyOk("D-flat major", db);
  check("musicxml: D-flat major: five flats, Db written D flat, no sharps, no accidentals on diatonic notes", /<fifths>-5<\/fifths>/.test(db.xml) && /<step>D<\/step><alter>-1<\/alter><octave>4<\/octave>/.test(db.xml) && !/<alter>1<\/alter>/.test(db.xml) && count(db.xml, /<accidental>/g) === 0 && db.stats.musicxml.unspelledNotes === 0,
    JSON.stringify({ accidentals: count(db.xml, /<accidental>/g), unspelled: db.stats.musicxml.unspelledNotes }));
  check("musicxml: pitchOf takes the octave from the letter (B#3 = MIDI 60, Cb4 = 59)", same(pitchOf(60, { letter: 6, acc: 1 }), { letter: 6, step: "B", alter: 1, octave: 3, spelled: true }) && pitchOf(59, { letter: 0, acc: -1 }).octave === 4 && !pitchOf(61, { letter: 0, acc: 0 }).spelled);

  // chord members of different written lengths at one position in a voice (a member released early under C1): an extra
  // MusicXML voice, every stream full (the pedal family's first held-out take holds such positions)
  const [{ take: pl, spec: pls }] = G.familySuite("pedal", [71]);
  const bl = build(pl.events, oracle(pl, pls));
  verifyOk("unequal chord lengths", bl);
  const unequal = bl.view.measures.reduce((s, m) => s + m.voices.reduce((t, v) => { const by = new Map(); for (const p of v.notes) { if (!by.has(p.pos)) by.set(p.pos, new Set()); by.get(p.pos).add(p.dur); } return t + [...by.values()].filter((x) => x.size > 1).length; }, 0), 0);
  check("musicxml: pieces of different lengths at one position in a voice go to an extra voice, every stream still full", unequal > 0 && bl.stats.musicxml.extraLanes > 0 && bl.stats.musicxml.forwards > 0, JSON.stringify({ unequal, extraLanes: bl.stats.musicxml.extraLanes, forwards: bl.stats.musicxml.forwards }));

  // an octave line: a right-hand passage above the treble range
  const beatsL = Array.from({ length: 16 }, (_, k) => 1000 + 500 * k);
  const evO = [];
  [96, 98, 100, 96, 98, 100, 98, 96].forEach((n, k) => evO.push({ t_ms: 1000 + 500 * k, kind: "on", note: n, vel: 64 }, { t_ms: 1000 + 500 * k + 450, kind: "off", note: n }));
  evO.push({ t_ms: 1000, kind: "on", note: 48, vel: 60 }, { t_ms: 4900, kind: "off", note: 48 });
  evO.sort((a, b) => a.t_ms - b.t_ms);
  const bo = build(evO, { ...takeOptions({}), beats: beatsL, one: 1000 });
  verifyOk("octave line", bo);
  check("musicxml: an 8va run is octave-shift down then stop, pitches kept sounding", /<octave-shift type="down" size="8" number="1"\/>/.test(bo.xml) && /<octave-shift type="stop" size="8" number="1"\/>/.test(bo.xml) && /<step>C<\/step><octave>7<\/octave>/.test(bo.xml));
  // 15ma (ls1-rulings.md LS3 rulings): a passage of notes beyond 3 ledger lines even under 8va (G7-B7) takes 15ma, written
  // as octave-shift size 15 above staff 1, pitches kept sounding
  const evQ = [];
  [103, 105, 107, 105, 103, 105, 107, 103].forEach((n, k) => evQ.push({ t_ms: 1000 + 500 * k, kind: "on", note: n, vel: 64 }, { t_ms: 1000 + 500 * k + 450, kind: "off", note: n }));
  evQ.push({ t_ms: 1000, kind: "on", note: 48, vel: 60 }, { t_ms: 4900, kind: "off", note: 48 });
  evQ.sort((a, b) => a.t_ms - b.t_ms);
  const bq = build(evQ, { ...takeOptions({}), beats: beatsL, one: 1000 });
  verifyOk("15ma line", bq);
  check("musicxml: a 15ma run is octave-shift down size 15 then stop, placed above, pitches kept sounding", /<direction placement="above">(?:(?!<\/direction>)[^])*<octave-shift type="down" size="15" number="1"\/>/.test(bq.xml) && /<octave-shift type="stop" size="15" number="1"\/>/.test(bq.xml) && /<step>G<\/step><octave>7<\/octave>/.test(bq.xml) && bq.view.measures.every((m) => m.octave[1] === 15 && m.ledgerBeyond[1] === 0), JSON.stringify(bq.view.measures.map((m) => [m.octave, m.ledgerBeyond])));

  // freely (ls1-rulings.md LS4, replacing C3's mark on every measure): once at the start of each free-time passage, "a tempo"
  // once where a tracked beat resumes; a copy with no taps and no jam beat is one passage with one "freely" at the top
  check("musicxml: no freely on a copy with fixed beats", b.stats.musicxml.freely === 0 && b.stats.musicxml.aTempo === 0 && !/freely|a tempo/.test(b.xml));
  const inf = build(pk.events, takeOptions({ meter: "4/4" }));
  verifyOk("pickup inferred", inf);
  const freeMeasures = inf.view.measures.filter((m) => m.forced || m.kind !== "metric").length;
  check("musicxml: an inferred copy (no taps, no jam) is one free-time passage: one freely at the top, no a tempo, no per-measure marks", inf.view.rhythm !== "jam" && freeMeasures > 1 && inf.stats.musicxml.freely === 1 && inf.stats.musicxml.aTempo === 0 && count(inf.xml, /<words font-style="italic">freely<\/words>/g) === 1 && /<measure number="[01]"[^>]*>(?:(?!<\/measure>)[^])*freely/.test(inf.xml) && inf.view.marks.freely.length === 1 && inf.view.marks.aTempo.length === 0, JSON.stringify({ freely: inf.stats.musicxml.freely, aTempo: inf.stats.musicxml.aTempo, freeMeasures, rhythm: inf.view.rhythm }));
  {
    // a jam-beat copy with a free-time passage inside it: measures 2-4 forced -> "freely" on measure 2, "a tempo" on 5
    const v = JSON.parse(JSON.stringify(b.view));
    v.measures.forEach((m, i) => { if (i >= 2 && i <= 4) m.forced = true; });
    const x = toMusicXML(v, { stats: {} }), st2 = {};
    toMusicXML(v, { stats: st2 });
    const words = [...x.matchAll(/<measure number="(\d+)"[^>]*>((?:(?!<\/measure>)[^])*)<\/measure>/g)].flatMap((mm) => [...mm[2].matchAll(/<words[^>]*>(freely|a tempo)<\/words>/g)].map((w) => [Number(mm[1]), w[1]]));
    const first = b.view.measures[0].pickup ? 0 : 1;
    check("musicxml: a free-time passage inside a jam copy: one freely where it starts, one a tempo where the beat resumes", st2.freely === 1 && st2.aTempo === 1 && JSON.stringify(words) === JSON.stringify([[2 + first, "freely"], [5 + first, "a tempo"]]), JSON.stringify({ words, freely: st2.freely, aTempo: st2.aTempo }));
  }
  const run4 = G.genTapeRun({ seconds: 4, rate: 10, seed: 3 });
  const bt = build(run4.events, takeOptions({}));
  verifyOk("tape run 4 s", bt);
  check("export.js: tape notes become forced bars; nothing stays tape", bt.view.tape.length === 0 && bt.view.forced.notes + bt.base.notes.length === run4.truth.groups && bt.view.forced.tapeLeft === 0, JSON.stringify(bt.view.forced));
  const fr = G.genFree(701), evF = G.eventsOf(fr).map((e) => ({ ...e, t_ms: Math.round(e.t_ms) }));
  const bf = build(evF, takeOptions({}));
  verifyOk("free piece", bf);
  const [{ take: pd, spec: pds }] = G.familySuite("pedal", [72]);
  const bp = build(pd.events, { ...takeOptions({ meter: pds.meter, bpm: String(Math.round(pds.bpm)) }) });
  verifyOk("pinned bpm", bp);
  check("export.js: --bpm pins a grid: rhythm unverified, every measure forced, one freely at the top (one free-time passage)", bp.view.rhythm === "unverified" && bp.view.measures.every((m) => m.forced) && bp.view.measures.length > 1 && bp.stats.musicxml.freely === 1 && bp.stats.musicxml.aTempo === 0 && bp.view.pinned && bp.view.pinned.bpm === Math.round(pds.bpm), JSON.stringify({ rhythm: bp.view.rhythm, freely: bp.stats.musicxml.freely, measures: bp.view.measures.length }));

  // ---- ls1-rulings.md "LS2close to LS5 rulings", LS4 export conventions, on hand-built measures
  const M44 = { label: "4/4", beats: 4, beatType: 4, tactus: 4, compound: false, beatTicks: 24, barTicks: 96 };
  let tAt = 1000;
  const mk = (index, barTicks, voices, extra = {}) => { const m = { index, seg: 0, kind: "metric", source: "jam", forced: false, barTicks, beats: barTicks / 24, start_ms: tAt, end_ms: tAt + barTicks * 25, beats_ms: [], voices, beams: [], tuplets: [], ...extra }; tAt += barTicks * 25; return m; };
  const notesOf = (xml, n) => { const mm = [...xml.matchAll(/<measure number="(\d+)"([^>]*)>((?:(?!<\/measure>)[^])*)<\/measure>/g)][n]; return [...mm[3].matchAll(/<note>((?:(?!<\/note>)[^])*)<\/note>/g)].map((x) => ({ step: (/<step>(\w)/.exec(x[1]) || [])[1], alter: Number((/<alter>(-?\d+)/.exec(x[1]) || [0, 0])[1]), octave: Number((/<octave>(-?\d+)/.exec(x[1]) || [0, NaN])[1]), type: (/<type>(\w+)/.exec(x[1]) || [])[1], acc: (/<accidental[^>]*>(\w[\w-]*)</.exec(x[1]) || [])[1] || null, courtesy: /<accidental cautionary="yes" parentheses="yes">/.test(x[1]), beam: (/<beam number="1">(\w+)/.exec(x[1]) || [])[1] || null, voice: (/<voice>(\d+)/.exec(x[1]) || [])[1], rest: /<rest/.test(x[1]) })); };

  // beams (must-fix): the verifier's S4 shape, staff 2 voice 4 beat 4 as a sextuplet 16th, a sextuplet quarter and a 16th.
  // measures.js no longer groups across the quarter, and the writer never beams across it even when handed the old group.
  const { buildMeasures } = await import("../arsenal/web/piano/score/measures.js");
  const [sb] = buildMeasures([{ id: 0, note: 48, tick: 0, dur: 72, voice: 4, staff: 2 }, { id: 1, note: 50, tick: 72, dur: 4, voice: 4, staff: 2 }, { id: 2, note: 52, tick: 76, dur: 16, voice: 4, staff: 2 }, { id: 3, note: 53, tick: 92, dur: 4, voice: 4, staff: 2 }], { meter: M44 });
  check("measures.js beams: no group spans the sextuplet quarter between two sextuplet 16ths (S4 shape)", sb.voices[0].notes.find((p) => p.id === 2).type === "quarter" && sb.tuplets.some((t) => t.beat === 3 && t.actual === 6) && sb.beams.every((g) => !(g.ids.includes(1) && g.ids.includes(3))), JSON.stringify({ beams: sb.beams, notes: sb.voices[0].notes.map((p) => [p.id, p.pos, p.type]) }));
  const oldGroup = { tpq: 24, meter: M44, notes: [], marks: {}, measures: [mk(0, 96, sb.voices, { beams: [{ voice: 4, beat: 3, ids: [1, 3] }], tuplets: sb.tuplets })] };
  const xb = toMusicXML(oldGroup, { stats: {} });
  const nb = notesOf(xb, 0).filter((x) => !x.rest);
  check("musicxml beam writer: handed a group across an unbeamable quarter, it writes no beam over it", nb.every((x) => x.beam === null) && pitchOf && readMusicXMLFor(xb).beamBad === 0, JSON.stringify(nb.map((x) => [x.type, x.beam])));
  const bad = xb.replace(/(<step>D<\/step><octave>3<\/octave>(?:(?!<\/note>)[^])*<staff>2<\/staff>)/, '$1<beam number="1">begin</beam>').replace(/(<step>F<\/step><octave>3<\/octave>(?:(?!<\/note>)[^])*<staff>2<\/staff>)/, '$1<beam number="1">end</beam>');
  // two violations: the unbeamed quarter inside the open beam (which closes it), then an end with no open beam
  check("LR9a beam structure check catches the failing case (begin, an unbeamed sextuplet quarter, end)", bad !== xb && readMusicXMLFor(bad).beamBad === 2, String(readMusicXMLFor(bad).beamBad));
  // 6/8 end to end: an eighth, an eighth rest and an eighth in one beat are not beamed across the rest; the run of 16ths and
  // a dotted eighth in the beat before stays one beam
  const ev68 = [], P68 = 900;
  const on68 = (t, n, d) => ev68.push({ t_ms: t, kind: "on", note: n, vel: 70 }, { t_ms: t + d, kind: "off", note: n });
  for (let k = 0; k < 4; k++) { const t = 1000 + k * 2 * P68; on68(t, 72, 140); on68(t + 150, 76, 590); on68(t + 750, 79, 140); on68(t + P68, 74, 280); on68(t + P68 + 600, 77, 280); }
  ev68.sort((a, b) => a.t_ms - b.t_ms);
  const b68 = build(ev68, { ...takeOptions({ meter: "6/8" }), beats: Array.from({ length: 12 }, (_, k) => 1000 + k * P68), one: 1000 });
  verifyOk("6/8 beams", b68);
  const n68 = notesOf(b68.xml, 0);
  check("musicxml beams (6/8): no beam across the eighth rest; the 16th run is one begin..end", JSON.stringify(n68.map((x) => x.beam)) === JSON.stringify(["begin", "continue", "continue", "end", null, null, null]) && readMusicXMLFor(b68.xml).beamBad === 0 && b68.view.measures.every((m) => m.beams.every((g) => g.pos.length >= 2)), JSON.stringify(n68.map((x) => [x.type, x.rest, x.beam])));

  // short measures: implicit only for the opening pickup; a short measure mid-score writes its time signature and the
  // next measure restores the meter
  const whole = (id, note) => [{ voice: 1, staff: 1, notes: [{ id, note, pos: 0, dur: 96, type: "whole", dots: 0 }], rests: [] }];
  tAt = 1000;
  const shortScore = { tpq: 24, meter: M44, notes: [], marks: {}, measures: [
    mk(0, 24, [{ voice: 1, staff: 1, notes: [{ id: 0, note: 67, pos: 0, dur: 24, type: "quarter", dots: 0 }], rests: [] }], { pickup: { implicit: true, ticks: 24, subBeats: 2, offset: 0 } }),
    mk(1, 96, whole(1, 72)),
    mk(2, 48, [{ voice: 1, staff: 1, notes: [{ id: 2, note: 74, pos: 0, dur: 48, type: "half", dots: 0 }], rests: [] }], { seg: 1, pickup: { implicit: true, ticks: 48, subBeats: 4, offset: 0 } }),
    mk(3, 96, whole(3, 76), { seg: 1 }),
    mk(4, 36, [{ voice: 1, staff: 1, notes: [{ id: 4, note: 77, pos: 0, dur: 36, type: "quarter", dots: 1 }], rests: [] }], { seg: 2, cut: true }),
  ] };
  const sst = {}, xs = toMusicXML(shortScore, { stats: sst });
  const heads = [...xs.matchAll(/<measure number="(\d+)"([^>]*)>(?:\s*<attributes>((?:(?!<\/attributes>)[^])*)<\/attributes>)?/g)].map((mm) => [Number(mm[1]), /implicit="yes"/.test(mm[2]), (/<time><beats>(\d+)<\/beats><beat-type>(\d+)<\/beat-type><\/time>/.exec(mm[3] || "") || []).slice(1).join("/") || null]);
  check("musicxml: implicit only on the opening pickup; mid-score 2/4 and 3/8 measures carry their time signature and the next measure restores 4/4",
    JSON.stringify(heads) === JSON.stringify([[0, true, "4/4"], [1, false, null], [2, false, "2/4"], [3, false, "4/4"], [4, false, "3/8"]]) && sst.implicitMeasures === 1 && sst.timeChanges === 3 && sst.timeUnwritable === 0, JSON.stringify({ heads, sst: [sst.implicitMeasures, sst.timeChanges, sst.timeUnwritable] }));
  const rs = readMusicXMLFor(xs), MTs = shortScore.measures.map((m) => m.barTicks);
  check("LR9a short-measure check: every measure's length equals its time signature (implicit opening pickup excepted)", rs.measures.every((m, i) => (m.implicit && i === 0) || (m.time.beats * 96) / m.time.beatType === MTs[i]) && rs.measures.filter((m) => m.implicit).length === 1);
  const unmarked = xs.replace(/<measure number="2">/, '<measure number="2" implicit="yes">').replace("<time><beats>2</beats><beat-type>4</beat-type></time>", "");
  const ru = readMusicXMLFor(unmarked);
  check("LR9a short-measure check catches an implicit short measure mid-score", ru.measures[2].implicit && (ru.measures[2].time.beats * 96) / ru.measures[2].time.beatType !== 48);
  check("timeSignatureOf: 48 in 4/4 is 2/4, 36 is 3/8, 72 in 12/8 is 6/8, a full bar is the meter, 4 ticks has none", same(timeSignatureOf(48, { beats: 4, beatType: 4 }), { beats: 2, beatType: 4 }) && same(timeSignatureOf(36, { beats: 4, beatType: 4 }), { beats: 3, beatType: 8 }) && same(timeSignatureOf(72, { beats: 12, beatType: 8 }), { beats: 6, beatType: 8 }) && same(timeSignatureOf(96, { beats: 4, beatType: 4 }), { beats: 4, beatType: 4 }) && timeSignatureOf(4, { beats: 4, beatType: 4 }) === null);

  // accidentals: F4 + F#4 at one position; a courtesy natural after a tied-in F#4; duplicate A-flats in two lanes both print
  tAt = 1000;
  const accScore = { tpq: 24, meter: M44, marks: {}, notes: [{ id: 10, note: 80, spelled: { letter: 5, acc: -1 } }, { id: 11, note: 80, spelled: { letter: 5, acc: -1 } }], measures: [
    mk(0, 96, [{ voice: 1, staff: 1, notes: [{ id: 0, note: 65, pos: 0, dur: 24, type: "quarter" }, { id: 1, note: 66, pos: 0, dur: 24, type: "quarter" }, { id: 5, note: 66, pos: 72, dur: 24, type: "quarter", tieStart: true }], rests: [{ pos: 24, dur: 48, type: "half" }] }]),
    mk(1, 96, [{ voice: 1, staff: 1, notes: [{ id: 5, note: 66, pos: 0, dur: 24, type: "quarter", tieStop: true }, { id: 6, note: 65, pos: 48, dur: 24, type: "quarter" }, { id: 7, note: 66, pos: 72, dur: 24, type: "quarter" }], rests: [{ pos: 24, dur: 24, type: "quarter" }] }]),
    mk(2, 96, [{ voice: 1, staff: 1, notes: [{ id: 10, note: 80, pos: 24, dur: 24, type: "quarter" }, { id: 11, note: 80, pos: 24, dur: 48, type: "half" }], rests: [{ pos: 0, dur: 24, type: "quarter" }, { pos: 72, dur: 24, type: "quarter" }] }]),
  ] };
  const ast = {}, xa = toMusicXML(accScore, { stats: ast });
  const a0 = notesOf(xa, 0).filter((x) => !x.rest), a1 = notesOf(xa, 1).filter((x) => !x.rest), a2 = notesOf(xa, 2).filter((x) => !x.rest);
  check("musicxml accidentals: F4 and F#4 at one position print a natural and a sharp", JSON.stringify(a0.slice(0, 2).map((x) => [x.step, x.alter, x.acc])) === JSON.stringify([["F", 0, "natural"], ["F", 1, "sharp"]]) && ast.accClashes === 1, JSON.stringify(a0));
  check("musicxml accidentals: after a tied-in F#4, a later F4 prints a courtesy natural in parentheses, the next F#4 a sharp", JSON.stringify(a1.map((x) => [x.alter, x.acc, x.courtesy])) === JSON.stringify([[1, null, false], [0, "natural", true], [1, "sharp", false]]) && ast.courtesy === 1, JSON.stringify(a1));
  check("musicxml accidentals: duplicate A-flats at one position in two lanes both print the flat", a2.length === 2 && new Set(a2.map((x) => x.voice)).size === 2 && a2.every((x) => x.step === "A" && x.alter === -1 && x.acc === "flat"), JSON.stringify(a2));

  // the modules stay pure and hold no speller
  const scoreDir = path.join(here, "..", "arsenal", "web", "piano", "score");
  const impure = ["musicxml.js", "midi.js", "export.js"].filter((f) => /\bdocument\.|\bwindow\.|performance\.now|Date\.now|new Date\b|\bfetch\(|require\(|from "node:/.test(fs.readFileSync(path.join(scoreDir, f), "utf8")));
  check("musicxml.js, midi.js, export.js: no DOM, clock, fetch or Node imports", impure.length === 0, JSON.stringify(impure));
  const twins = fs.readdirSync(scoreDir).filter((f) => f.endsWith(".js") && /function\s+spellForKey|spellInKey\s*\(|spellNote\s*\(/.test(fs.readFileSync(path.join(scoreDir, f), "utf8")));
  check("no speller in score code", twins.length === 0, JSON.stringify(twins));
}

// ============================================================================================= receipts ===
const FIX_ROOT = path.join(SCORE_ROOT, "ls4-fixtures");
function fixtureRow(name, events, options) {
  const t = performance.now();
  const b = build(events, options, { title: name });
  const ms = performance.now() - t;
  const dir = path.join(FIX_ROOT, name);
  writeTake(dir, b, { label: name, group: "fixtures", take: name, eventsRef: { base: "dir", path: "events.jsonl" }, writeJson: false });
  fs.writeFileSync(path.join(dir, "events.jsonl"), b.spanEvents.map((e) => JSON.stringify(e)).join("\n") + "\n");
  const v = verifyExport(b), a = auditScore(newAudit(), b.view, name);
  return { name, v, audit: auditLine(a), auditOk: auditOk(a), forced: b.view.forced, X: b.stats.musicxml, P: b.stats.performance, ms };
}
if (!quick) {
  const t9 = performance.now();
  const rows = [];
  for (const fam of G.FAMILIES) for (const { take, spec } of G.familySuite(fam)) {
    const base = `${fam}-${spec.meter.replace("/", "-")}-${spec.texture}-r${spec.rub}-s${spec.seed}`;
    rows.push({ fam, mode: "oracle", ...fixtureRow(`${base}-oracle`, take.events, oracle(take, spec)) });
    rows.push({ fam, mode: "inferred", ...fixtureRow(`${base}-inferred`, take.events, takeOptions({ meter: spec.meter })) });
  }
  for (const pc of G.freeSuite()) rows.push({ fam: "free", mode: "inferred", ...fixtureRow(`free-s${pc.truth ? pc.truth.seed ?? rows.length : rows.length}`, G.eventsOf(pc).map((e) => ({ ...e, t_ms: Math.round(e.t_ms) })), takeOptions({})) });
  for (const [seconds, seed] of [[1.5, 1], [4, 2]]) rows.push({ fam: "tapeRun", mode: "inferred", ...fixtureRow(`taperun-${seconds}s-s${seed}`, G.genTapeRun({ seconds, rate: 10, seed }).events, takeOptions({})) });
  const agg = (pick) => ({
    exports: pick.length,
    LR9a: { pass: pick.filter((r) => r.v.lr9a.pass).length, sounding: pick.reduce((s, r) => s + r.v.lr9a.sounding, 0), logOns: pick.reduce((s, r) => s + r.v.lr9a.logOns, 0), voicesChecked: pick.reduce((s, r) => s + r.v.lr9a.voicesChecked, 0), voiceSumBad: pick.reduce((s, r) => s + r.v.lr9a.voiceSumBad, 0), tieUnmatched: pick.reduce((s, r) => s + r.v.lr9a.tieUnmatchedStart + r.v.lr9a.tieUnmatchedStop, 0), scoreDiff: pick.reduce((s, r) => s + r.v.lr9a.scoreDiff, 0) },
    LR9b: { pass: pick.filter((r) => r.v.lr9b.pass).length, ons: pick.reduce((s, r) => s + r.v.lr9b.midiOns, 0), offs: pick.reduce((s, r) => s + r.v.lr9b.midiOffs, 0), cc64: pick.reduce((s, r) => s + r.v.lr9b.midiCc64, 0), endOffs: pick.reduce((s, r) => s + r.v.lr9b.endOffs, 0), onsDiff: pick.reduce((s, r) => s + r.v.lr9b.onsDiff, 0), ccDiff: pick.reduce((s, r) => s + r.v.lr9b.ccDiff, 0) },
    LR9c: { pass: pick.filter((r) => r.v.lr9c.pass).length, notes: pick.reduce((s, r) => s + r.v.lr9c.notes, 0), tickPitchDiff: pick.reduce((s, r) => s + r.v.lr9c.tickPitchDiff, 0) },
    audit: { ok: pick.filter((r) => r.auditOk).length, ...Object.fromEntries(["notePieces", "badNotes", "badRests", "untiled", "danglingBarTies", "twoBarLines", "overlaps"].map((k) => [k, pick.reduce((s, r) => s + r.audit[k], 0)])) },
    forced: { runs: pick.reduce((s, r) => s + r.forced.runs, 0), notes: pick.reduce((s, r) => s + r.forced.notes, 0), measures: pick.reduce((s, r) => s + r.forced.measures, 0), tapeLeft: pick.reduce((s, r) => s + r.forced.tapeLeft, 0) },
    writer: { extraLanes: pick.reduce((s, r) => s + r.X.extraLanes, 0), crossVoiceTies: pick.reduce((s, r) => s + r.X.crossVoiceTies, 0), pedalRepairs: pick.reduce((s, r) => s + r.X.pedalRepairs, 0), bracketsSkipped: pick.reduce((s, r) => s + r.X.bracketsSkipped, 0), unspelledNotes: pick.reduce((s, r) => s + r.X.unspelledNotes, 0), untypedPieces: pick.reduce((s, r) => s + r.X.untypedPieces, 0), rubato: pick.reduce((s, r) => s + r.X.rubato, 0), metronomes: pick.reduce((s, r) => s + r.X.metronomes, 0) },
    playback: { medianOfMediansMs: MX.median(pick.map((r) => r.v.playback.medianMs)), worstP95Ms: Math.max(0, ...pick.map((r) => r.v.playback.p95Ms ?? 0)) },
    msPerExport: { median: MX.median(pick.map((r) => r.ms)), max: Math.max(...pick.map((r) => r.ms)) },
  });
  const all = agg(rows);
  const byMode = { oracle: agg(rows.filter((r) => r.mode === "oracle")), inferred: agg(rows.filter((r) => r.mode === "inferred")) };
  const failed = rows.filter((r) => !r.v.pass).map((r) => r.name);
  receipts.push({ id: "LR9a", scope: "fixtures", measured: { ...all.LR9a, exports: all.exports }, threshold: "100% of exports", pass: all.LR9a.pass === all.exports });
  receipts.push({ id: "LR9b", scope: "fixtures", measured: { ...all.LR9b, exports: all.exports }, threshold: "every on, off and CC64 crossing at the log's t_ms, 0 ms error; CC64 in {0, 127}", pass: all.LR9b.pass === all.exports });
  receipts.push({ id: "LR9c", scope: "fixtures", measured: { ...all.LR9c, exports: all.exports }, threshold: "quantized.mid notes = MusicXML sounding notes, 100%", pass: all.LR9c.pass === all.exports });
  receipts.push({ id: "LS4-audit", scope: "fixtures", measured: all.audit, threshold: "0 on the five construction properties on every export view", pass: all.audit.ok === all.exports });
  receipts.push({ id: "LS4-fixtures-report", measured: { byMode, forced: all.forced, writer: all.writer, playback: all.playback, msPerExport: all.msPerExport, failed: failed.slice(0, 10), ms: Math.round(performance.now() - t9) } });
  check("LR9a fixtures: 100% of exports", all.LR9a.pass === all.exports, JSON.stringify({ failed: rows.filter((r) => !r.v.lr9a.pass).slice(0, 3).map((r) => [r.name, r.v.lr9a]) }));
  check("LR9b fixtures: 100% of exports", all.LR9b.pass === all.exports, JSON.stringify({ failed: rows.filter((r) => !r.v.lr9b.pass).slice(0, 3).map((r) => [r.name, r.v.lr9b]) }));
  check("LR9c fixtures: 100% of exports", all.LR9c.pass === all.exports, JSON.stringify({ failed: rows.filter((r) => !r.v.lr9c.pass).slice(0, 3).map((r) => [r.name, r.v.lr9c]) }));
  check("LS4-audit fixtures: every export view passes the construction audit", all.audit.ok === all.exports, JSON.stringify(rows.filter((r) => !r.auditOk).slice(0, 3).map((r) => [r.name, r.audit])));
  check("fixtures: no forced pass leaves tape", all.forced.tapeLeft === 0);
  console.log(`fixture exports written to ${path.relative(path.join(here, ".."), FIX_ROOT)} (${rows.length})`);
}

if (sessions) {
  const auditRows = [];
  const summary = bench({ onBuilt: (b, s) => { const a = auditScore(newAudit(), b.view, s.name); auditRows.push({ name: s.name, ok: auditOk(a), line: auditLine(a) }); }, log: null });
  const aud = { sessions: auditRows.length, ok: auditRows.filter((r) => r.ok).length, ...Object.fromEntries(["notePieces", "badNotes", "badRests", "untiled", "danglingBarTies", "twoBarLines", "overlaps"].map((k) => [k, auditRows.reduce((s, r) => s + r.line[k], 0)])) };
  receipts.push({ id: "LR9a", scope: "S1..Sn", measured: { ...summary.LR9a, used: summary.used, skipped: summary.skipped }, threshold: "100% of sessions", pass: summary.LR9a.pass && summary.used > 0 });
  receipts.push({ id: "LR9b", scope: "S1..Sn", measured: summary.LR9b, threshold: "every on, off and CC64 crossing at the log's t_ms, 0 ms error; CC64 in {0, 127}", pass: summary.LR9b.pass && summary.used > 0 });
  receipts.push({ id: "LR9c", scope: "S1..Sn", measured: summary.LR9c, threshold: "quantized.mid notes = MusicXML sounding notes, 100%", pass: summary.LR9c.pass && summary.used > 0 });
  receipts.push({ id: "LS4-audit", scope: "S1..Sn", measured: aud, threshold: "0 on the five construction properties on every export view", pass: aud.ok === aud.sessions });
  receipts.push({ id: "LS4-sessions-report", measured: { totals: summary.totals, playback: summary.playback, ms: summary.ms } });
  check("LR9a S1..Sn", summary.LR9a.pass && summary.used > 0, JSON.stringify(summary.LR9a));
  check("LR9b S1..Sn", summary.LR9b.pass && summary.used > 0, JSON.stringify(summary.LR9b));
  check("LR9c S1..Sn", summary.LR9c.pass && summary.used > 0, JSON.stringify(summary.LR9c));
  check("LS4-audit S1..Sn", aud.ok === aud.sessions, JSON.stringify(auditRows.filter((r) => !r.ok).map((r) => [r.name, r.line])));
  console.log(`sessions bench written to state/arsenal/score/ls4-bench-${summary.date}.json`);
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => r4(v)));
console.log(`score_export: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
