// Node tests for arsenal/web/piano/score/settle.js and the index.js live transcriber's bar states (slice LS2 of the live
// sheet music plan, research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 6.7 and 10.2,
// transcription.md T9). Zero dependencies:
//   node tests/score_settle.test.mjs              settle.js contracts, then LR5 and LR6a-c on synthetic fixtures
//   node tests/score_settle.test.mjs --quick      contracts and the frozen-tie fixtures only (a pause, settle beats with
//                                                 a pending onset group, a tracker revision moving a seen onset, a frozen
//                                                 onset before a later build's window)
//   node tests/score_settle.test.mjs --sessions   also the local bench over the practice sessions (S1..Sn): LR5 on S12,
//                                                 LR6a-c on every session, and the construction audit (the five
//                                                 auditScore properties: values, tiles, bar ties lead on, one bar line,
//                                                 no overlap; live and clean copies). Reads
//                                                 state/arsenal/performance/*/events.jsonl read-only; writes aggregates
//                                                 only (S-numbers, no ids, times or notes) to
//                                                 state/arsenal/score/ls2close-bench-<date>.json. Skipped when the folder
//                                                 is missing.
// Quantizer: quantize.js defaults, d6MinGroups 5 (ls1-rulings.md LS2 rulings).
// Definitions:
//   LR5   transcriber cost excluding paint: each tick's cost (onsets, beat, quantize, measures, settle) divided by the
//         onset groups it handed out, one value per group; p95 (ticks with no new group are reported apart).
//   LR6a  a settled bar never changes: its signature when it settled equals its signature at the end, no `changed` entry
//         names a bar after it settled, and settle.js refused nothing (violations 0).
//   LR6b  relabel churn: the share of placed onsets whose settled label (segment, tactus beat, position in the beat)
//         differs between settleBeats k and settleBeats 8 (transcription.md stats4); k = 4 gated, 0, 1, 2 reported.
//   LR6c  flicker: label changes (bar, position) of notes in open and settling bars per minute of playing.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import { newAudit, auditScore } from "./fixtures/score/audit.mjs";
import { createSettle } from "../arsenal/web/piano/score/settle.js";
import { createTranscriber, replayInto, clean } from "../arsenal/web/piano/score/index.js";

const argv = process.argv.slice(2);
const quick = argv.includes("--quick"), sessions = argv.includes("--sessions");
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}

// --------------------------------------------------------------------------------------- settle.js contracts ---
{
  const st = createSettle({ settleBeats: 4, pauseMs: 2000 });
  let r = st.upsert(0, { sig: "a", endBeat: 4, start_ms: 0, end_ms: 2400 });
  check("settle: a new bar is open, rev 0, changed", r.changed && r.rev === 0 && st.state(0) === "open");
  r = st.upsert(0, { sig: "a", endBeat: 4, start_ms: 0, end_ms: 2400 });
  check("settle: the same content is no change", !r.changed && r.rev === 0);
  r = st.upsert(0, { sig: "b", endBeat: 4, start_ms: 0, end_ms: 2400 });
  check("settle: new content raises rev", r.changed && r.rev === 1);
  let a = st.advance({ T: 2000, beat: 3, lastOnsetMs: 1900 });
  check("settle: before its end beat the bar stays open", st.state(0) === "open" && !a.settling.length);
  a = st.advance({ T: 2400, beat: 4, lastOnsetMs: 2300 });
  check("settle: its end beat makes it settling", st.state(0) === "settling" && a.settling[0] === 0);
  st.upsert(1, { sig: "c", endBeat: 8, start_ms: 2400, end_ms: 4800 });
  a = st.advance({ T: 4700, beat: 7, lastOnsetMs: 4600 });
  check("settle: 3 beats past the end is still settling", st.state(0) === "settling");
  a = st.advance({ T: 4800, beat: 8, lastOnsetMs: 4700 });
  check("settle: 4 beats past the end settles", st.state(0) === "settled" && a.settled.includes(0) && st.get(0).reason === "beats");
  r = st.upsert(0, { sig: "z", endBeat: 4 });
  check("settle: a settled bar refuses new content and counts it", !r.changed && r.refused && st.violations() === 1 && st.get(0).sig === "b");
  check("settle: firstUnsettled", st.firstUnsettled() === 1);
  check("settle: drop never removes a settled bar", JSON.stringify(st.drop(0)) === "[1]" && st.state(0) === "settled" && st.state(1) === null);
  const s2 = createSettle();
  s2.upsert(0, { sig: "a", endBeat: 4, end_ms: 2400 }); s2.upsert(1, { sig: "b", endBeat: 8, end_ms: 4800 });
  s2.advance({ T: 2500, beat: 4, lastOnsetMs: 2450 });
  a = s2.advance({ T: 4460, beat: 4, lastOnsetMs: 2450 });
  check("settle: a 2 s pause settles a bar that has ended", s2.state(0) === "settled" && s2.get(0).reason === "pause" && s2.state(1) === "open");
  const all = s2.settleAll("hold", 5000);
  check("settle: settleAll settles the rest", JSON.stringify(all) === "[1]" && s2.state(1) === "settled" && s2.firstUnsettled() === 2);
}

// ------------------------------------------------------------------------------------- transcriber replays ---
// One replay with the LR6 instruments. Returns { tr, lr6a, flicker, labels, costs, minutes }.
function instrumentedRun(events, { meter = "4/4", settleBeats = 4, beats = null, one = null, voiceOf = null, timing = false, endMs = null } = {}) {
  const tr = createTranscriber({ options: { meter, settleBeats, beats, one, voiceOf } });
  const settledSig = new Map(), label = new Map();
  let lateChange = 0, flicker = 0, prevGroups = 0;
  const perGroup = [], emptyTick = [];
  const evs = events.filter((e) => e.kind === "on" || e.kind === "off" || e.kind === "pedal" || e.kind === "sound_end");
  const ons = evs.filter((e) => e.kind === "on");
  const minutes = ons.length ? (ons[ons.length - 1].t_ms - ons[0].t_ms) / 60000 : 0;
  // time each tick from outside: wrap tick
  const rawTick = tr.tick;
  tr.tick = (T) => {
    const t0 = timing ? performance.now() : 0;
    const out = rawTick(T);
    if (timing) {
      const ms = performance.now() - t0, g = tr.stats().groups, k = g - prevGroups;
      prevGroups = g;
      if (k > 0) for (let i = 0; i < k; i++) perGroup.push(ms / k); else emptyTick.push(ms);
    }
    return out;
  };
  replayInto(tr, evs, { endMs, onTick: (out) => {
    if (!out.changed.length) return;
    const byIdx = new Map(tr.bars().filter((b) => out.changed.includes(b.index)).map((b) => [b.index, b]));
    for (const i of out.changed) {
      if (settledSig.has(i)) { lateChange++; continue; }
      const b = byIdx.get(i);
      if (!b) continue;
      if (b.state === "settled") { settledSig.set(i, b.sig); continue; }
      for (const n of b.notes) {
        const lab = `${b.index}:${n.pos}`;
        if (label.has(n.id) && label.get(n.id) !== lab) flicker++;
        label.set(n.id, lab);
      }
    }
  } });
  tr.finish();
  let endMismatch = 0;
  const final = tr.bars();
  for (const b of final) {
    if (b.state !== "settled") endMismatch++;
    else if (settledSig.has(b.index) && settledSig.get(b.index) !== b.sig) endMismatch++;
  }
  const st = tr.stats();
  const placed = new Map();
  for (const b of final) for (const n of b.notes) placed.set(n.id, { lab: `${b.seg}:${n.j}:${n.off}`, metric: b.kind === "metric" });
  return { tr, lr6a: { lateChange, endMismatch, refused: st.refused, violations: st.violations, settled: final.length }, flicker, flickerPerMin: minutes > 0 ? flicker / minutes : NaN, placed, onsets: ons.length, minutes, perGroup, emptyTick };
}
// Construction audit of a score (counts only), the same five properties as score_quantize.test.mjs auditScore
// (tests/fixtures/score/audit.mjs): pieces and rests that are not one written value, notes whose pieces do not tile the
// written duration, bar-line ties that do not lead into the next bar of the same segment holding the continuation,
// notes crossing more than one bar line, and continuations overlapping a later onset in their voice. barTies is reported.
function tieAudit(sc) {
  const a = auditScore(newAudit(), sc, "session");
  let barTies = 0;
  for (const m of sc.measures) for (const v of m.voices) for (const p of v.notes) if (p.barTie) barTies++;
  return { notes: sc.notes.length, badValues: a.badNotes + a.badRests, untiled: a.tiles, dangling: a.dangling, twoBarLines: a.multiBar, overlaps: a.overlap, barTies };
}
const TIE_KEYS = ["badValues", "untiled", "dangling", "twoBarLines", "overlaps"];

// ------------------------------------------------------------------------------ frozen-tie overlap fixture ---
// The edge (ls1-rulings.md LS2 rulings): a bar settles on a 2 s pause while its held bass claims a bar-line tie, then an
// onset in the same voice arrives before the next bar's midpoint. Fixed beats 600 ms apart from 1000 ms, 4/4, bar 0 =
// 1000-3400 ms, bar 1 = 3400-5800 ms (midpoint 4600). The bass (MIDI 36, the lower-staff voice of the bench split) rings
// under the pedal from 1000 ms; the last onset of bar 0 is at 2500, a treble release at 4400 makes a build at 4500, and
// the pause settles bar 0 there. The new bass onset at 4520 quantizes to 138 ticks (bar 1 position 42, before 48).
// Before the heardTick cap (measures.js), the 4500 ms build snapped the ringing bass to 144 ticks, so the frozen
// continuation [96, 144) overlapped the new onset. Settled means never repainted: the frozen note is not re-capped, so
// the continuation must stop at the start of the beat the tick time is in (120 at 4500 ms) when it is claimed.
{
  const beats = Array.from({ length: 24 }, (_, k) => 1000 + 600 * k);
  const ev = [
    { t_ms: 900, kind: "pedal", down: true, value: 100 },
    { t_ms: 1000, kind: "on", note: 36, vel: 70 }, { t_ms: 1000, kind: "on", note: 72, vel: 70 },
    { t_ms: 1200, kind: "off", note: 36 }, { t_ms: 1250, kind: "off", note: 72 },
    { t_ms: 2500, kind: "on", note: 76, vel: 60 }, { t_ms: 4400, kind: "off", note: 76 },
    { t_ms: 4520, kind: "on", note: 38, vel: 70 }, { t_ms: 4700, kind: "off", note: 38 },
    { t_ms: 7000, kind: "pedal", down: false, value: 0 },
  ];
  const tr = createTranscriber({ options: { meter: "4/4", beats, one: 1000 } });
  let atSettle = null, late = 0;
  replayInto(tr, ev, { endMs: 9000, onTick: (out, T) => {
    const b0 = tr.bars().find((b) => b.index === 0);
    if (!b0 || b0.state !== "settled") return;
    if (!atSettle) {
      const bass = b0.measure.voices.flatMap((v) => v.notes.filter((p) => p.note === 36));
      atSettle = { T, reason: b0.reason, sig: b0.sig, barTie: bass.some((p) => p.barTie), bassDur: (b0.notes.find((n) => n.note === 36) || {}).dur };
    } else if (b0.sig !== atSettle.sig) late++;
  } });
  tr.finish();
  const sc = tr.score(), a = tieAudit(sc);
  const m1 = sc.measures.find((m) => m.index === 1), v1 = m1 && m1.voices.find((v) => v.notes.some((p) => p.note === 36));
  const cont = v1 && v1.notes.find((p) => p.note === 36 && p.tieStop && p.pos === 0), fresh = v1 && v1.notes.find((p) => p.note === 38 && !p.tieStop);
  check("frozen tie: bar 0 settles on the pause at 4500 ms with the held bass tied over its bar line", atSettle && atSettle.T === 4500 && atSettle.reason === "pause" && atSettle.barTie && atSettle.bassDur === 120, JSON.stringify(atSettle));
  check("frozen tie: the later bass onset sits in bar 1 before its midpoint, in the continuation's voice", !!(cont && fresh) && fresh.pos === 42 && fresh.pos < m1.barTicks / 2, JSON.stringify(v1 && v1.notes));
  check("frozen tie: the continuation ends at or before that onset (no overlap), bar 0 never changed, nothing refused",
    !!cont && cont.dur === 24 && cont.dur <= fresh.pos && late === 0 && sc.measures.find((m) => m.index === 0).state === "settled" && tr.stats().violations === 0 && tr.stats().refused === 0, JSON.stringify({ cont, late, stats: tr.stats() }));
  // two bar-line ties: the frozen bass 36 (bar 0 into 1) and the new bass 38, which rings under the pedal to 7000 ms (bar 1 into 2)
  check("frozen tie: the score passes the construction audit (values, tiles, ties lead on, one bar line, no overlap)", TIE_KEYS.every((k) => a[k] === 0) && a.barTies === 2, JSON.stringify(a));
}
// The same edge, settled by beats while the onset group is still pending (LS2close repair round 1, the verifier's case).
// Fixed beats 400 ms apart from 1000 ms, 4/4: bar 0 = 1000-2600 ms, bar 1 = 2600-4200 ms (midpoint 3400). The bass (MIDI
// 36) rings under the pedal from 1000 ms and a treble note holds 2010-4060 ms, so bar 0 settles by beats at 4250 ms (beat 8
// is at 4200) with its bass tied over the bar line to the end of bar 1 (no bass onset before bar 1's midpoint). The next
// bass onset, at 4140 ms, is still open in onsets.js at 4250 ms (a roll could form until 4260), so it is handed out at
// 4500 ms and quantizes to 186 ticks (bar 1 position 90). With heardTick from the tick time (beat 8, 192 ticks) the frozen
// continuation ran to 192 and overlapped it; from the onset finality horizon (the oldest pending note-on, 4140 ms, in
// beat 7) it stops at 168. Variants: the new onset at MIDI 38; the treble released at 4120 with the onset at 4150.
for (const [relMs, onMs, bass] of [[4060, 4140, 36], [4060, 4140, 38], [4120, 4150, 36]]) {
  const tag = `release ${relMs}, onset ${bass} at ${onMs}`;
  const beats = Array.from({ length: 40 }, (_, k) => 1000 + 400 * k);
  const ev = [
    { t_ms: 900, kind: "pedal", down: true, value: 100 },
    { t_ms: 1000, kind: "on", note: 36, vel: 70 }, { t_ms: 1000, kind: "on", note: 72, vel: 70 },
    { t_ms: 1200, kind: "off", note: 36 }, { t_ms: 1250, kind: "off", note: 72 },
    { t_ms: relMs - 2050, kind: "on", note: 76, vel: 60 }, { t_ms: relMs, kind: "off", note: 76 },
    { t_ms: onMs, kind: "on", note: bass, vel: 70 }, { t_ms: onMs + 150, kind: "off", note: bass },
    { t_ms: onMs + 1200, kind: "on", note: 79, vel: 60 }, { t_ms: onMs + 1400, kind: "off", note: 79 },
    { t_ms: onMs + 3200, kind: "pedal", down: false, value: 0 },
  ];
  const tr = createTranscriber({ options: { meter: "4/4", beats, one: 1000 } });
  let atSettle = null, late = 0, handedAt = null;
  replayInto(tr, ev, { endMs: onMs + 4800, onTick: (out, T) => {
    if (handedAt == null && tr.stats().groups >= 3) handedAt = T;
    const b0 = tr.bars().find((b) => b.index === 0);
    if (!b0 || b0.state !== "settled") return;
    if (!atSettle) {
      const bassP = b0.measure.voices.flatMap((v) => v.notes.filter((p) => p.note === 36));
      atSettle = { T, reason: b0.reason, sig: b0.sig, barTie: bassP.some((p) => p.barTie), bassDur: (b0.notes.find((n) => n.note === 36) || {}).dur };
    } else if (b0.sig !== atSettle.sig) late++;
  } });
  tr.finish();
  const sc = tr.score(), a = tieAudit(sc);
  const m1 = sc.measures.find((m) => m.index === 1), v1 = m1 && m1.voices.find((v) => v.notes.some((p) => p.note === 36));
  const cont = v1 && v1.notes.find((p) => p.note === 36 && p.tieStop && p.pos === 0), fresh = v1 && v1.notes.find((p) => p.note === bass && !p.tieStop);
  check(`frozen tie by beats (${tag}): bar 0 settles by beats at 4250 ms with the bass tied, before the onset group is handed out at 4500 ms`,
    atSettle && atSettle.T === 4250 && atSettle.reason === "beats" && atSettle.barTie && atSettle.bassDur === 168 && handedAt === 4500, JSON.stringify({ ...atSettle, sig: undefined, handedAt }));
  check(`frozen tie by beats (${tag}): the later bass onset sits in bar 1 at position 90, in the continuation's voice`, !!(cont && fresh) && fresh.pos === 90, JSON.stringify(v1 && v1.notes));
  check(`frozen tie by beats (${tag}): the continuation [0, 72) ends before that onset, bar 0 never changed, nothing refused`,
    !!cont && cont.dur === 72 && cont.dur <= fresh.pos && late === 0 && sc.measures.find((m) => m.index === 0).state === "settled" && tr.stats().violations === 0 && tr.stats().refused === 0, JSON.stringify({ cont, late, stats: tr.stats() }));
  check(`frozen tie by beats (${tag}): the score passes the construction audit`, TIE_KEYS.every((k) => a[k] === 0) && a.barTies === 2, JSON.stringify(a));
}
// The same edge on tracker beats, where an onset the build HAS seen moves earlier after the tie froze (LS2close repair
// round 2, the verifier's case). heardTick covers only onsets the build has not seen. Inferred beats, meter 3/4: pedal
// down at 500 ms; from 1000 ms 16 bars at a 600 ms beat, the period x1.3 (780 ms) from bar 6. Treble quarters (MIDI
// 72-74) on every beat, released after half a beat; bass 36 on beat 1 of even bars (150 ms); bass 38 at 0.95 of each odd
// bar (120 ms), about 117 ms before the next downbeat; the pedal lifted 20 ms before and pressed 30 ms after each 4th bar
// line. Bar 3 settles by beats at 14500 ms with its bass 36 (tick 228) frozen at 96 ticks: tied into bar 4, continuation
// [288, 324). The 38 at 11710 ms then sits at tick 324, touching it. At 15250 ms the tracker revises the grid and the 38
// quantizes to 318, inside the frozen continuation: pre-fix, bar 4's lower voice held 78 ticks and the audit counted 1
// overlap. Settled means never repainted, so the open bar respects the frozen claim: the group is pinned to 324
// (index.js build). The same events on exact beats need no pin.
{
  const meter = "3/4", K = 3, ev = [{ t_ms: 500, kind: "pedal", down: true, value: 100 }], beats = [];
  let t = 1000;
  for (let bar = 0; bar < 16; bar++) {
    const p = bar >= 6 ? 780 : 600;
    for (let k = 0; k < K; k++) {
      beats.push(t);
      ev.push({ t_ms: t, kind: "on", note: 72 + (k % 3), vel: k === 0 ? 90 : 60 }, { t_ms: t + p * 0.5, kind: "off", note: 72 + (k % 3) });
      if (k === 0 && bar % 2 === 0) ev.push({ t_ms: t, kind: "on", note: 36, vel: 90 }, { t_ms: t + 150, kind: "off", note: 36 });
      if (k === 0 && bar % 2 === 1) { const bt = t + p * K * 0.95; ev.push({ t_ms: bt, kind: "on", note: 38, vel: 70 }, { t_ms: bt + 120, kind: "off", note: 38 }); }
      t += p;
    }
    if (bar % 4 === 3) ev.push({ t_ms: t - 20, kind: "pedal", down: false, value: 0 }, { t_ms: t + 30, kind: "pedal", down: true, value: 100 });
  }
  ev.sort((x, y) => x.t_ms - y.t_ms);
  const tr = createTranscriber({ options: { meter } });
  let atSettle = null, late = 0, pin = null;
  replayInto(tr, ev, { onTick: (out, T) => {
    const b3 = tr.bars().find((b) => b.index === 3), b4 = tr.bars().find((b) => b.index === 4);
    const n38 = b4 && b4.notes.find((n) => n.note === 38 && Math.round(n.on_ms) === 11710);
    if (n38 && n38.pinnedFrom != null && !pin) pin = { T, from: n38.pinnedFrom, tick: n38.segTick };
    if (!b3 || b3.state !== "settled") return;
    if (!atSettle) {
      const d36 = b3.notes.find((n) => n.note === 36);
      atSettle = { T, reason: b3.reason, sig: b3.sig, bass: d36 ? [d36.segTick, d36.dur] : null, barTie: b3.measure.voices.some((v) => v.notes.some((p) => p.note === 36 && p.barTie)), n38: n38 ? n38.segTick : null };
    } else if (b3.sig !== atSettle.sig) late++;
  } });
  tr.finish();
  const sc = tr.score(), a = tieAudit(sc);
  const m4 = sc.measures.find((m) => m.index === 4), v4 = m4 && m4.voices.find((v) => v.notes.some((p) => p.note === 36 && p.tieStop));
  const cont = v4 && v4.notes.find((p) => p.note === 36 && p.tieStop && p.pos === 0), fresh = v4 && v4.notes.find((p) => p.note === 38 && !p.tieStop);
  const extent = v4 ? v4.notes.filter((p) => p.note === 36 && p.tieStop).reduce((e, p) => Math.max(e, p.pos + p.dur), 0) : null;
  check("frozen tie on tracker beats: bar 3 settles by beats at 14500 ms with bass 36 at tick 228 frozen at 96 ticks (tied), the 38 touching at 324",
    !!atSettle && atSettle.T === 14500 && atSettle.reason === "beats" && JSON.stringify(atSettle.bass) === "[228,96]" && atSettle.barTie && atSettle.n38 === 324, JSON.stringify({ ...atSettle, sig: undefined }));
  check("frozen tie on tracker beats: the 15250 ms grid revision quantizes the seen 38 to 318, and the build pins it to the continuation's end, 324",
    !!pin && pin.T === 15250 && pin.from === 318 && pin.tick === 324 && tr.stats().pinned >= 1, JSON.stringify({ pin, pinned: tr.stats().pinned }));
  check("frozen tie on tracker beats: bar 4's lower voice is the continuation [0, 36) then the 38 at 36 (72 ticks, no overlap), bar 3 never changed, nothing refused",
    !!cont && !!fresh && extent === 36 && fresh.pos === 36 && v4.notes.every((p) => p.pos + p.dur <= m4.barTicks) && late === 0 && sc.measures.find((m) => m.index === 3).state === "settled" && tr.stats().violations === 0 && tr.stats().refused === 0,
    JSON.stringify({ lower: v4 && v4.notes.map((p) => [p.note, p.pos, p.dur, p.tieStop ? "tieStop" : "", p.barTie ? "barTie" : ""]), late, stats: tr.stats() }));
  check("frozen tie on tracker beats: the score passes the construction audit", TIE_KEYS.every((k) => a[k] === 0) && a.barTies > 0, JSON.stringify(a));
  const tf = createTranscriber({ options: { meter, beats, one: 1000 } });
  replayInto(tf, ev); tf.finish();
  const af = tieAudit(tf.score());
  check("frozen tie on tracker beats: the same events on exact beats pass the audit with no pin", TIE_KEYS.every((k) => af[k] === 0) && tf.stats().pinned === 0, JSON.stringify({ af, pinned: tf.stats().pinned }));
}
// A frozen continuation must reach the bar it ties into even when a revised grid puts its onset before the build window
// (LS2close repair round 2, found by the tracker sweep: 3 audit failures in 15,840 variants, before and after the pin).
// Inferred beats, 3/4: the same pattern as above with an 800 ms beat, the period x0.9 (720 ms) from bar 5. Bar 4 settles
// by beats at 20500 ms holding the bass 38 played at 15052 ms (108 ms before bar 4's first beat, 15160) and the bass 36 at
// 15160, both at position 0 with 144 ticks: tied into bar 5. Pre-fix, a build collected frozen notes through its group
// time window: at 20750 ms the build rebuilding from bar 5 started it at 15070 ms (15160 minus 1/8 of 720), so the frozen
// 38 was left out and its continuation vanished (a bar tie leading nowhere, an untiled note). Builds before, on a 929 ms
// period, had held it. Frozen notes now come from the settled bar itself.
{
  const meter = "3/4", K = 3, ev = [{ t_ms: 500, kind: "pedal", down: true, value: 100 }];
  let t = 1000;
  for (let bar = 0; bar < 16; bar++) {
    const p = bar >= 5 ? 720 : 800;
    for (let k = 0; k < K; k++) {
      ev.push({ t_ms: t, kind: "on", note: 72 + (k % 3), vel: k === 0 ? 90 : 60 }, { t_ms: t + p * 0.5, kind: "off", note: 72 + (k % 3) });
      if (k === 0 && bar % 2 === 0) ev.push({ t_ms: t, kind: "on", note: 36, vel: 90 }, { t_ms: t + 150, kind: "off", note: 36 });
      if (k === 0 && bar % 2 === 1) { const bt = t + p * K * 0.95; ev.push({ t_ms: bt, kind: "on", note: 38, vel: 70 }, { t_ms: bt + 120, kind: "off", note: 38 }); }
      t += p;
    }
    if (bar % 4 === 3) ev.push({ t_ms: t - 20, kind: "pedal", down: false, value: 0 }, { t_ms: t + 30, kind: "pedal", down: true, value: 100 });
  }
  ev.sort((x, y) => x.t_ms - y.t_ms);
  const tr = createTranscriber({ options: { meter } });
  let atSettle = null, late = 0;
  replayInto(tr, ev, { onTick: (out, T) => {
    const b4 = tr.bars().find((b) => b.index === 4);
    if (!b4 || b4.state !== "settled") return;
    if (!atSettle) {
      const low = b4.notes.filter((n) => n.note < 60).map((n) => [n.note, Math.round(n.on_ms), n.pos, n.dur]).sort((x, y) => x[1] - y[1]);
      atSettle = { T, reason: b4.reason, start: Math.round(b4.start_ms), sig: b4.sig, low, ties: b4.measure.voices.flatMap((v) => v.notes.filter((p) => p.barTie).map((p) => p.note)).sort() };
    } else if (b4.sig !== atSettle.sig) late++;
  } });
  tr.finish();
  const sc = tr.score(), a = tieAudit(sc);
  const m5 = sc.measures.find((m) => m.index === 5);
  const conts = m5 ? m5.voices.flatMap((v) => v.notes.filter((p) => p.tieStop && p.pos === 0).map((p) => [p.note, p.dur])).sort() : null;
  check("frozen tie before the window: bar 4 settles by beats at 20500 ms with bass 38 (15052 ms) and 36 (15160 ms) at position 0, 144 ticks, both tied",
    !!atSettle && atSettle.T === 20500 && atSettle.reason === "beats" && atSettle.start === 15160 && JSON.stringify(atSettle.low) === "[[38,15052,0,144],[36,15160,0,144]]" && JSON.stringify(atSettle.ties) === "[36,38]",
    JSON.stringify({ ...atSettle, sig: undefined }));
  check("frozen tie before the window: bar 5 holds both continuations [0, 72), bar 4 never changed, nothing refused",
    JSON.stringify(conts) === "[[36,72],[38,72]]" && late === 0 && tr.stats().violations === 0 && tr.stats().refused === 0, JSON.stringify({ conts, late, stats: tr.stats() }));
  check("frozen tie before the window: the score passes the construction audit", TIE_KEYS.every((k) => a[k] === 0), JSON.stringify(a));
}
function churn(runs, onsets) {
  const ref = runs[8], out = {};
  for (const k of [0, 1, 2, 4]) {
    const a = runs[k];
    let n = 0, diff = 0, nm = 0, dm = 0;
    const ids = new Set([...a.placed.keys(), ...ref.placed.keys()]);
    for (const id of ids) {
      const x = a.placed.get(id), y = ref.placed.get(id);
      n++;
      if (!x || !y || x.lab !== y.lab) diff++;
      if ((x && x.metric) || (y && y.metric)) { nm++; if (!x || !y || x.lab !== y.lab) dm++; }
    }
    out[k] = { churn: n ? diff / n : NaN, placed: n, placedShareOfOnsets: onsets ? n / onsets : NaN, metricChurn: nm ? dm / nm : null, metricPlaced: nm };
  }
  return out;
}

if (!quick) {
  const t0 = performance.now();
  // fixtures: the LS0 pedal family (held-out seeds; full on/off/sound_end/pedal events), rung 4 with the meter set to
  // truth; the jam stand-in (fixed beats) on the same takes; the tempo-step and count-in families on rung 4 and taps
  const takes = [...G.familySuite("pedal"), ...G.familySuite("tempoStep"), ...G.familySuite("countIn")];
  const rows = [];
  for (const { family, take, spec } of takes) {
    const runs = {};
    for (const k of [0, 1, 2, 4, 8]) runs[k] = instrumentedRun(take.events, { meter: spec.meter, settleBeats: k, timing: k === 4 });
    const fixedRun = instrumentedRun(take.events, { meter: spec.meter, beats: take.truth.beats_ms, one: take.truth.downbeats_ms[0] });
    rows.push({ family, meter: spec.meter, rub: spec.rub, lr6a: runs[4].lr6a, lr6aFixed: fixedRun.lr6a, flickerPerMin: runs[4].flickerPerMin, flickerFixedPerMin: fixedRun.flickerPerMin, churn: churn(runs, runs[4].onsets), perGroup: runs[4].perGroup, emptyTick: runs[4].emptyTick });
  }
  const lr6aBad = rows.filter((r) => r.lr6a.lateChange || r.lr6a.endMismatch || r.lr6a.refused || r.lr6a.violations || r.lr6aFixed.lateChange || r.lr6aFixed.endMismatch || r.lr6aFixed.refused || r.lr6aFixed.violations);
  const settledBars = rows.reduce((s, r) => s + r.lr6a.settled + r.lr6aFixed.settled, 0);
  receipts.push({ id: "LR6a-fixtures", measured: { takes: rows.length, settledBars, takesWithAChange: lr6aBad.length }, threshold: "0 changes", pass: lr6aBad.length === 0 });
  check("LR6a fixtures: settled bars never change", lr6aBad.length === 0, JSON.stringify(lr6aBad.slice(0, 3).map((r) => [r.family, r.meter, r.rub, r.lr6a, r.lr6aFixed])));
  const ch = (k, key = "churn") => MX.mean(rows.map((r) => r.churn[k][key]).filter((v) => v != null));
  receipts.push({ id: "LR6b-fixtures", measured: Object.fromEntries([0, 1, 2, 4].map((k) => [`lag${k}vs8`, { churn: ch(k), metricChurn: ch(k, "metricChurn"), placedShare: ch(k, "placedShareOfOnsets") }])), threshold: "reported on fixtures (the receipt is S1..Sn, <= 6%)", pass: null });
  receipts.push({ id: "LR6c-fixtures", measured: { rung4PerMinMedian: MX.median(rows.map((r) => r.flickerPerMin)), rung4PerMinP90: MX.pct(rows.map((r) => r.flickerPerMin), 90), fixedBeatsPerMinMedian: MX.median(rows.map((r) => r.flickerFixedPerMin)) }, threshold: "reported", pass: null });
  const allGroups = rows.flatMap((r) => r.perGroup), empties = rows.flatMap((r) => r.emptyTick);
  receipts.push({ id: "LR5-fixtures", measured: { perGroupP95: MX.pct(allGroups, 95), perGroupMean: MX.mean(allGroups), groups: allGroups.length, emptyTickP95: MX.pct(empties, 95) }, threshold: "reported on fixtures (the receipt is S12, <= 0.5 ms p95)", pass: null, ms: Math.round(performance.now() - t0) });
}

if (sessions) {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const ROOT = path.join(here, "..", "state", "arsenal", "performance"), OUT = path.join(here, "..", "state", "arsenal", "score");
  if (!fs.existsSync(ROOT)) console.log("sessions: state/arsenal/performance is missing, skipped");
  else {
    const t1 = performance.now();
    const dirs = fs.readdirSync(ROOT).filter((d) => fs.existsSync(path.join(ROOT, d, "events.jsonl"))).sort();
    const srows = [];
    dirs.forEach((d, i) => {
      const name = "S" + (i + 1);
      const events = fs.readFileSync(path.join(ROOT, d, "events.jsonl"), "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l))
        .filter((e) => e.kind === "on" || e.kind === "off" || e.kind === "pedal" || e.kind === "sound_end");
      const ons = events.filter((e) => e.kind === "on").length;
      if (ons < 100) { srows.push({ name, skipped: true }); return; }
      const runs = {};
      for (const k of [0, 1, 2, 4, 8]) runs[k] = instrumentedRun(events, { meter: "4/4", settleBeats: k, timing: k === 4 });
      const r4 = runs[4];
      const bars = r4.tr.bars();
      srows.push({ name, minutes: +r4.minutes.toFixed(2), onsets: ons, bars: bars.length, metricBars: bars.filter((b) => b.kind === "metric").length, segments: r4.tr.stats().segments,
        lr6a: r4.lr6a, churn: churn(runs, ons), flickerPerMin: +r4.flickerPerMin.toFixed(2), ties: { live: tieAudit(r4.tr.score()), clean: tieAudit(clean(events, { meter: "4/4" })) },
        lr5: { perGroupP95: +MX.pct(r4.perGroup, 95).toFixed(4), perGroupMean: +MX.mean(r4.perGroup).toFixed(4), groups: r4.perGroup.length, emptyTickP95: +MX.pct(r4.emptyTick, 95).toFixed(4) } });
    });
    const used = srows.filter((r) => !r.skipped);
    const tot = (k, key) => { let n = 0, d = 0; for (const r of used) { const c = r.churn[k]; if (c[key === "metricChurn" ? "metricPlaced" : "placed"] && c[key] != null) { const nn = c[key === "metricChurn" ? "metricPlaced" : "placed"]; n += nn; d += c[key] * nn; } } return n ? d / n : null; };
    const s12 = used.find((r) => r.name === "S12");
    const lr6aBad = used.filter((r) => r.lr6a.lateChange || r.lr6a.endMismatch || r.lr6a.refused || r.lr6a.violations);
    const lr6b = Object.fromEntries([0, 1, 2, 4].map((k) => [`lag${k}vs8`, { churn: tot(k, "churn"), metricChurn: tot(k, "metricChurn"), range: [Math.min(...used.map((r) => r.churn[k].churn)), Math.max(...used.map((r) => r.churn[k].churn))] }]));
    const summary = {
      date: "2026-09-15", slice: "LS2close", config: "onsets.js, beat.js, quantize.js (d6MinGroups 5), measures.js, settle.js defaults; meter held at 4/4; voices split at MIDI 60",
      sessions: srows.length, skipped: srows.filter((r) => r.skipped).map((r) => r.name),
      LR5: s12 ? { S12: s12.lr5, threshold: "p95 <= 0.5 ms per onset group", pass: s12.lr5.perGroupP95 <= 0.5 } : null,
      LR6a: { settledBars: used.reduce((s, r) => s + r.lr6a.settled, 0), sessionsWithAChange: lr6aBad.map((r) => r.name), pass: lr6aBad.length === 0 },
      LR6b: { ...lr6b, threshold: "lag 4 vs 8 <= 6% (all sessions, onsets pooled)", pass: lr6b.lag4vs8.churn != null && lr6b.lag4vs8.churn <= 0.06 },
      LR6c: { perSession: Object.fromEntries(used.map((r) => [r.name, r.flickerPerMin])), median: MX.median(used.map((r) => r.flickerPerMin)), threshold: "reported" },
      ties: (() => {
        const keys = ["notes", "barTies", ...TIE_KEYS];
        const sum = (kind) => Object.fromEntries(keys.map((k) => [k, used.reduce((a, r) => a + r.ties[kind][k], 0)]));
        const live = sum("live"), cl = sum("clean");
        return { live, clean: cl, threshold: "construction, the five auditScore properties: 0 pieces or rests off the written values, 0 untiled notes, 0 bar ties leading nowhere, 0 notes over two bar lines, 0 continuations overlapping a later onset (live and clean copies, meter 4/4)", pass: TIE_KEYS.every((k) => live[k] === 0 && cl[k] === 0) };
      })(),
      rows: srows, ms: Math.round(performance.now() - t1),
    };
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, "ls2close-bench-2026-09-15.json"), JSON.stringify(summary, null, 1));
    receipts.push({ id: "LR5", measured: summary.LR5, pass: summary.LR5 ? summary.LR5.pass : null });
    receipts.push({ id: "LR6a", measured: summary.LR6a, pass: summary.LR6a.pass });
    receipts.push({ id: "LR6b", measured: summary.LR6b, pass: summary.LR6b.pass });
    receipts.push({ id: "LR6c", measured: summary.LR6c, pass: null });
    if (summary.LR5) check("LR5 S12 p95 <= 0.5 ms per onset group", summary.LR5.pass, JSON.stringify(summary.LR5));
    check("LR6a S1..Sn settled bars never change", summary.LR6a.pass, JSON.stringify(summary.LR6a));
    check("LR6b S1..Sn churn at 4 vs 8 beats <= 6%", summary.LR6b.pass, JSON.stringify(summary.LR6b.lag4vs8));
    receipts.push({ id: "LS2-ties-sessions", measured: { live: summary.ties.live, clean: summary.ties.clean }, threshold: summary.ties.threshold, pass: summary.ties.pass });
    check("S1..Sn bar-line ties lead into their continuation, pieces tile, one bar line per note", summary.ties.pass, JSON.stringify(summary.ties));
    console.log("sessions bench written to state/arsenal/score/ls2close-bench-2026-09-15.json");
  }
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v)));
console.log(`score_settle: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
