// Node tests for arsenal/web/piano/score/layout.js, paint.js, engrave.js, ribbon.js and bench.js (slice LS5 of the live
// sheet music plan, research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 2.1, 7.3 and 10.4,
// amended by plan-amendments.md section 0 rule 1, C6, C15, C16 and ls1-rulings.md). Zero dependencies, synthetic
// fixtures (tests/fixtures/score/gen.mjs, score/bench.js) unless --sessions:
//   node tests/score_layout.test.mjs              contracts, then LR11e-g geometry on fixtures and the ribbon invariants
//   node tests/score_layout.test.mjs --quick      contracts only
//   node tests/score_layout.test.mjs --sessions   also LR11f and LR11e on S1..Sn ribbon replays (meter 4/4). Reads
//                                                 state/arsenal/performance/*/events.jsonl read-only; writes aggregates
//                                                 only (S-numbers, no ids, times or notes) to
//                                                 state/arsenal/score/ls5-layout-bench-2026-09-15.json.
// The timings (LR11a-c) and the page's own counters (LR11d on tile contexts) are measured in headless Chrome by
// tests/score_lab.test.mjs --browser.
// Definitions:
//   C16    9:16 band right edge <= 940 px and bottom <= 1436 px (asserted on createLayout).
//   LR11f  overlapping heads per minute of tape: two heads on one staff in different columns whose 1.18 x 1.0 s boxes,
//          shrunk 0.1 s per side, intersect. Fixture: a 1.5 s run at 10 single-note groups a second: 0 (gated); a 4 s run
//          reported. S1..Sn: pooled over the sessions <= 3.0 per tape minute (gated; plan-amendments.md section 5),
//          per session reported.
//   LR11g  glyph collisions per settled bar (heads, accidentals, dots, rests, flags of different owners on one staff,
//          boxes shrunk 0.1 s per side) on the dense bench bars of 12, 24, 43 and 67 onsets: 0 with widening (gated);
//          reported with fixed 96 px beats.
//   LR11e  mean head x shift at the settle crossfade (the open bar's layout against the first engraved layout of the
//          same bar, matched by note id, staff and position) on beats that did not widen: <= 0.5 s (gated) measured
//          against the beat's own line; the shift inside the bar and widened beats reported. Fixtures with oracle beats
//          (every LS0 family, held-out seeds) and inferred beats (the tempo suite).
//   LR11d  (model) a frozen block's x, width and layout never change after it froze; tape columns never move; every note
//          is drawn once (never in a frozen block and on tape, tie continuations included; never on tape and in a live block).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as G from "./fixtures/score/gen.mjs";
import {
  createLayout, createTapePlacer, tapeColumnWidth, tapeHeads, staffStep, stepY, sigFromFifths, keySigGlyphs, modelBar, layoutBar,
  overlaps, headShift, LAYOUT_API, FRAMINGS,
} from "../arsenal/web/piano/score/layout.js";
import { headerText, paintHeader, paintTape, paintOpenBar, paintPedalLine, paintStaves, BRAVURA_URL } from "../arsenal/web/piano/score/paint.js";
import { createHouseEngraver, ENGRAVER_API, SMUFL } from "../arsenal/web/piano/score/engrave.js";
import { createRibbon } from "../arsenal/web/piano/score/ribbon.js";
import { denseBar, tapeWindow, BENCH_SIZES } from "../arsenal/web/piano/score/bench.js";
import { createTranscriber, replayInto } from "../arsenal/web/piano/score/index.js";
import { spellMidi } from "../arsenal/web/piano/spell.js";

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
const r4 = (v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v);
const spell = (midis, key) => midis.map((m) => spellMidi(m, key));
const L = createLayout({ framing: "9:16" });
const METER44 = { label: "4/4", beats: 4, beatType: 4, tactus: 4, compound: false, beatTicks: 24, barTicks: 96 };
const spelledOf = (p) => { const s = spellMidi(p.note, null); return { letter: s.letter, acc: s.acc, octave: s.octave }; };
const ORDER = { off: 0, sound_end: 1, pedal: 2, on: 3 };

// a recording 2D context stub: counts drawing calls, keeps text
function stubCtx() {
  const calls = { draw: 0, text: [] };
  const noop = () => {};
  const ctx = new Proxy({ calls, globalAlpha: 1 }, {
    get(t, k) {
      if (k in t) return t[k];
      if (["fillText", "strokeText"].includes(k)) return (s) => { calls.draw++; calls.text.push({ s, alpha: t.globalAlpha }); };
      if (["fillRect", "stroke", "fill", "clearRect", "drawImage"].includes(k)) return () => { calls.draw++; };
      return noop;
    },
    set(t, k, v) { t[k] = v; return true; },
  });
  return ctx;
}

// Ribbon replay over practice-log shaped events on the 250 ms tick clock; onTick(ribbon, T) after each tick.
function replayRibbon(events, options, { onTick = null, spellFn = spell, endPad = 3000, taps = [], presses = [] } = {}) {
  const R = createRibbon({ spell: spellFn, layout: L, options });
  const evs = events.filter((e) => e.kind in ORDER).sort((a, b) => a.t_ms - b.t_ms || ORDER[a.kind] - ORDER[b.kind]);
  if (!evs.length) return R;
  let i = 0, k = 0, p = 0;
  const end = evs[evs.length - 1].t_ms + endPad;
  for (let T = Math.floor(evs[0].t_ms / 250) * 250 + 250; T <= end; T += 250) {
    while (k < taps.length && taps[k] <= T) R.tap(taps[k++]);
    while (i < evs.length && evs[i].t_ms <= T) {
      const e = evs[i++];
      if (e.kind === "on") R.noteOn(e.note, e.vel ?? 64, e.t_ms);
      else if (e.kind === "off") R.noteOff(e.note, e.t_ms);
      else if (e.kind === "pedal") R.pedal(!!e.down, e.value ?? 0, e.t_ms);
      else R.soundEnd(e.note, e.t_ms, e.by ?? null);
    }
    while (p < presses.length && presses[p].t <= T) { const pr = presses[p++]; pr.fn(R); }
    R.tick(T);
    if (onTick) onTick(R, T);
  }
  return R;
}

// invariants a ribbon must keep while it runs: frozen blocks and placed columns never change, scroll never goes back, and
// a note is drawn once (repair LS5 r1): no note id in a frozen block's model (any piece, tie continuations included) and in
// a tape column, none in two tape columns, no onset piece in two frozen blocks, and no live block drawing a taped note
function watcher() {
  const frozen = new Map(), colsX = new Map();
  const tapeIds = new Set(), frozenIds = new Set(), onsetBlock = new Map(), twice = new Set(), liveTwice = new Set();
  const w = { blockChanges: 0, columnMoves: 0, scrollBack: 0, lastScroll: -Infinity, checks: 0, drawnTwice: 0, liveOnTape: 0 };
  w.onTick = (R) => {
    const v = R.view();
    for (const b of v.blocks) {
      const sig = `${b.x0}|${b.x1}|${b.layout.width}|${b.layout.heads.map((h) => h.id + ":" + h.x.toFixed(3)).join(",")}`;
      if (!frozen.has(b.index)) {
        frozen.set(b.index, sig);
        for (const vo of b.model.voices) for (const n of vo.notes) {
          frozenIds.add(n.id);
          if (tapeIds.has(n.id)) twice.add(n.id);
          if (!n.tieStop) { const k = onsetBlock.get(n.id); if (k != null && k !== b.index) twice.add(n.id); else onsetBlock.set(n.id, b.index); }
        }
      } else if (frozen.get(b.index) !== sig) w.blockChanges++;
    }
    for (const c of R.columnsIn(-Infinity, Infinity)) {
      if (!colsX.has(c.gid)) { colsX.set(c.gid, c.x); for (const h of c.heads) { if (tapeIds.has(h.id) || frozenIds.has(h.id)) twice.add(h.id); tapeIds.add(h.id); } }
      else if (colsX.get(c.gid) !== c.x) w.columnMoves++;
    }
    for (const b of v.live) for (const vo of b.model.voices) for (const n of vo.notes) if (tapeIds.has(n.id)) liveTwice.add(n.id);
    w.drawnTwice = twice.size; w.liveOnTape = liveTwice.size;
    if (v.scrollX < w.lastScroll) w.scrollBack++;
    w.lastScroll = v.scrollX;
    w.checks++;
  };
  return w;
}
const shiftOut = (s) => ({
  unwidenedBeatLocalSp: s.beatLocal && s.beatLocal.n ? r4(s.beatLocal.px / s.beatLocal.n / L.sp) : 0,
  unwidenedInBarSp: s.unwidened.n ? r4(s.unwidened.px / s.unwidened.n / L.sp) : 0, unwidenedN: s.unwidened.n,
  widenedSp: s.widened.n ? r4(s.widened.px / s.widened.n / L.sp) : 0, widenedN: s.widened.n, moved: s.moved,
  blockX0Px: s.x0.n ? r4(s.x0.px / s.x0.n) : 0, transitions: s.x0.n,
});

// ======================================================================================== contracts ===
{
  // C16 and the framing
  check("layout API", LAYOUT_API === "arsenal.piano.score.layout/v0");
  check("C16: 9:16 band right edge <= 940 px", L.band.x1 <= 940, JSON.stringify(L.band));
  check("C16: 9:16 band bottom <= 1436 px", L.band.y1 <= 1436, JSON.stringify(L.band));
  check("C6: band x 110-940, playhead at 70% (x 691), D_max 180 px", L.band.x0 === 110 && Math.abs(L.playheadX - 691) < 1e-9 && L.dMax === 180, JSON.stringify({ ph: L.playheadX, dMax: L.dMax }));
  check("plan 7.3: s = 15, beat 96 px, tape 120 px per second", L.sp === 15 && L.beatMinPx === 96 && Math.abs(L.v - 0.12) < 1e-12);
  check("the band holds both staves, ledger room and the pedal lane", L.staffTop[1] >= 3 * L.sp && L.staffBottom[2] + 3 * L.sp < L.pedalY && L.pedalY < L.tileH);
  const L169 = createLayout({ framing: "16:9" });
  check("16:9 is provisional (LQ4) and inside its canvas", L169.provisional === true && L169.band.x1 <= FRAMINGS["16:9"].width && L169.band.y1 <= FRAMINGS["16:9"].height);
  receipts.push({ id: "C16", measured: { band: L.band, playheadX: L.playheadX, dMax: L.dMax, tileH: L.tileH }, threshold: "right <= 940, bottom <= 1436", pass: L.band.x1 <= 940 && L.band.y1 <= 1436 });

  // shared with piano.js (read-only source)
  const pianoSrc = fs.readFileSync(path.join(here, "..", "arsenal", "web", "piano.js"), "utf8");
  const bravura = /const BRAVURA_URL = "([^"]+)"/.exec(pianoSrc);
  check("C9: the lab loads the same pinned Bravura URL string as piano.js", bravura && bravura[1] === BRAVURA_URL, bravura && bravura[1]);
  const sm = /const SMUFL = \{([\s\S]*?)\};/.exec(pianoSrc);
  const pianoSmufl = {};
  if (sm) for (const m of sm[1].matchAll(/(\w+):\s*"\\u([0-9A-Fa-f]{4})"/g)) pianoSmufl[m[1]] = String.fromCharCode(parseInt(m[2], 16));
  const shared = ["gClef", "fClef", "brace", "whole", "flat", "natural", "sharp", "dsharp", "dflat"];
  check("SMuFL code points shared with piano.js SMUFL", shared.every((k) => pianoSmufl[k] && pianoSmufl[k] === SMUFL[k]), JSON.stringify(Object.keys(pianoSmufl)));

  // pure modules: no DOM, no clock, no speller
  const scoreDir = path.join(here, "..", "arsenal", "web", "piano", "score");
  const pure = ["layout.js", "paint.js", "engrave.js", "ribbon.js", "bench.js"];
  const impure = pure.filter((f) => /\b(document|window|performance\.now|Date\.now|requestAnimationFrame|localStorage)\b/.test(fs.readFileSync(path.join(scoreDir, f), "utf8").replace(/^\s*\/\/.*$/gm, "")));
  check("LS5 score modules read no DOM and no clock", impure.length === 0, JSON.stringify(impure));
  const twins = pure.filter((f) => /function\s+spellForKey|spellInKey\s*\(/.test(fs.readFileSync(path.join(scoreDir, f), "utf8")));
  check("no speller in LS5 score code (the speller is injected)", twins.length === 0, JSON.stringify(twins));

  // pitch geometry
  const sp = (midi) => { const s = spellMidi(midi, null); return { letter: s.letter, acc: s.acc, octave: s.octave }; };
  check("staff steps: C4 is 6 below treble's middle line and 6 above bass's", staffStep(sp(60), "treble") === -6 && staffStep(sp(60), "bass") === 6);
  check("staff steps: F5 is treble's top line (4), G2 bass's bottom (-4)", staffStep(sp(77), "treble") === 4 && staffStep(sp(43), "bass") === -4);
  check("staff steps: 8va writes C6 as C5 (step 1); 8vb writes C2 where C3 sits", staffStep(sp(84), "treble", 8) === 1 && staffStep(sp(36), "bass", -8) === staffStep(sp(48), "bass"));
  check("step y: the middle line of each staff", stepY(L, 1, 0) === L.staffTop[1] + 2 * L.sp && stepY(L, 2, 4) === L.staffTop[2]);
  check("key signatures: Eb major is B E A flat; D major F C sharp", JSON.stringify(sigFromFifths(-3)) === JSON.stringify([0, 0, -1, 0, 0, -1, -1]) && JSON.stringify(sigFromFifths(2)) === JSON.stringify([1, 0, 0, 1, 0, 0, 0]));
  check("key signature glyphs: 6 flats on treble start at B4 (step 0)", keySigGlyphs(-6, "treble").length === 6 && keySigGlyphs(-6, "treble")[0].step === 0 && keySigGlyphs(3, "bass")[0].step === 2);

  // C6 tape columns and the placer
  const h = (staff, step, acc = null) => ({ staff, step, acc });
  check("C6 column: 1.4 s", Math.abs(tapeColumnWidth([h(1, 0)], L) - 21) < 1e-9);
  check("C6 column: + 1.0 s for an accidental", Math.abs(tapeColumnWidth([h(1, 0, 1)], L) - 36) < 1e-9);
  check("C6 column: + 1.18 s for a second", Math.abs(tapeColumnWidth([h(1, 0), h(1, 1)], L) - 38.7) < 1e-9);
  check("C6 column: the wider staff sets w", Math.abs(tapeColumnWidth([h(1, 0), h(2, 0, -1), h(2, 1)], L) - 53.7) < 1e-9);
  const P = createTapePlacer(L, { x0: 0, t0: 0 });
  const a = P.place(0, 21), b = P.place(50, 21), c = P.place(1000, 21);
  check("C6 placer: the first column sits at its nominal x", a.x === 0 && a.D === 0);
  check("C6 placer: a column wanting less than min is pushed (debt 15 px)", b.x === 21 && Math.abs(b.D - 15) < 1e-9, JSON.stringify(b));
  check("C6 placer: spare space reclaims the debt, at most half the spare", Math.abs(c.x - 120) < 1e-9 && Math.abs(c.D) < 1e-9, JSON.stringify(c));
  const P2 = createTapePlacer(L, { x0: 0, t0: 0 });
  const burst = Array.from({ length: 14 }, () => P2.place(0, 21));
  check("C6 placer: the debt clamps at D_max and the clamp is flagged", burst[9].clamped && burst[9].x === 180 && !burst[8].clamped, JSON.stringify(burst.slice(7, 10).map((x) => [x.x, x.D, x.clamped])));
  const P3 = createTapePlacer(L, { x0: 0, t0: 0 });
  P3.place(0, 21); P3.place(40, 21); P3.place(80, 21);
  check("C6 ticks: debt interpolates between neighbouring columns", Math.abs(P3.debtAt(20) - (P3.columns()[0].D + P3.columns()[1].D) / 2) < 1e-9);
  const th = tapeHeads([{ id: 1, note: 64, staff: 1, spelled: sp(64) }, { id: 2, note: 65, staff: 1, spelled: sp(65) }, { id: 3, note: 61, staff: 1, spelled: sp(61) }], L, { fifths: 0 });
  // no key: spell.js writes MIDI 61 as Db (the neutral bias); Db4 and E4 sit on adjacent letters, so E4 moves right
  check("tape heads: a second displaces the upper head, an accidental shows off the signature", th.heads.find((x) => x.id === 1).dx > 0 && th.heads.find((x) => x.id === 2).dx === 0 && th.heads.find((x) => x.id === 3).acc === -1 && th.accW === 15, JSON.stringify(th));

  // bars
  const plain = { index: 0, state: "open", beats: 4, start_ms: 0, end_ms: 3000, measure: { voices: [{ voice: 1, staff: 1, notes: [0, 24, 48, 72].map((pos, i) => ({ id: i, note: 72 + i * 2, pos, dur: 24, type: "quarter", dots: 0 })), rests: [] }], beams: [], tuplets: [], loose: [] } };
  const pm = modelBar(plain, { meter: METER44, spelledOf, fifths: 0 });
  const po = layoutBar(pm, L, { widen: false }), ps = layoutBar(pm, L, { widen: true });
  check("a plain 4/4 bar is 384 px, open and settled", po.width === 384 && ps.width === 384, `${po.width} ${ps.width}`);
  const s0 = headShift(po, { ...ps, beatTicks: 24 }, L);
  check("LR11e by construction: 0 shift on a bar that did not widen", s0.unwidened.n === 4 && s0.unwidened.meanPx === 0 && s0.beatLocal.meanPx === 0, JSON.stringify(s0));
  const acc = { ...plain, measure: { ...plain.measure, voices: [{ voice: 1, staff: 1, notes: [{ id: 0, note: 73, pos: 0, dur: 12, type: "eighth", dots: 0 }, { id: 1, note: 73, pos: 12, dur: 12, type: "eighth", dots: 0 }], rests: [{ pos: 24, dur: 72, type: "half", dots: 1 }] }] } };
  const am = modelBar(acc, { meter: METER44, spelledOf, fifths: 0 });
  check("accidentals last to the end of the bar (Db5 twice: one flat)", am.voices[0].notes[0].acc === -1 && am.voices[0].notes[1].acc === null, JSON.stringify(am.voices[0].notes.map((n) => n.acc)));
  // repair LS5 r1: the running accidental is per staff. Verifier's case, C major: staff 1 voice 1 F#4 at 0, staff 2 voice 4
  // F#4 at 24 (the bass note was written F natural). Within one staff it still carries across voices.
  const inC = (p) => { const s = spellMidi(p.note, "C major"); return { letter: s.letter, acc: s.acc, octave: s.octave }; };
  const cross = { ...plain, measure: { ...plain.measure, voices: [{ voice: 1, staff: 1, notes: [{ id: 0, note: 66, pos: 0, dur: 24, type: "quarter" }], rests: [] }, { voice: 4, staff: 2, notes: [{ id: 1, note: 66, pos: 24, dur: 24, type: "quarter" }], rests: [] }] } };
  const cm = modelBar(cross, { meter: METER44, spelledOf: inC, fifths: 0 });
  const cl = layoutBar(cm, L, { widen: true });
  check("accidentals never carry across staves: F#4 treble at 0, F#4 bass at 24, both sharp and both drawn", cm.voices[0].notes[0].acc === 1 && cm.voices[1].notes[0].acc === 1 && cl.accidentals.filter((x) => x.acc === 1).map((x) => x.staff).sort().join() === "1,2", JSON.stringify({ acc: cm.voices.map((v) => v.notes.map((n) => [v.staff, n.acc])), drawn: cl.accidentals }));
  const crossBack = { ...cross, measure: { ...cross.measure, voices: [cross.measure.voices[0], { voice: 4, staff: 2, notes: [{ id: 1, note: 65, pos: 24, dur: 24, type: "quarter" }], rests: [] }, { voice: 1, staff: 1, notes: [{ id: 2, note: 65, pos: 48, dur: 24, type: "quarter" }], rests: [] }] } };
  const cb = modelBar(crossBack, { meter: METER44, spelledOf: inC, fifths: 0 });
  check("a staff's own accidental cancels on that staff only: F4 bass after a treble F#4 plain, F4 treble after it natural", cb.voices[1].notes[0].acc === null && cb.voices[2].notes[0].acc === 0, JSON.stringify(cb.voices.map((v) => v.notes.map((n) => [v.staff, n.note, n.acc]))));
  const sameStaff = { ...plain, measure: { ...plain.measure, voices: [{ voice: 3, staff: 2, notes: [{ id: 0, note: 54, pos: 0, dur: 24, type: "quarter" }], rests: [] }, { voice: 4, staff: 2, notes: [{ id: 1, note: 54, pos: 24, dur: 24, type: "quarter" }], rests: [] }] } };
  const sm2 = modelBar(sameStaff, { meter: METER44, spelledOf: inC, fifths: 0 });
  check("on one staff an accidental carries across voices (F#3 voice 3, then F#3 voice 4: one sharp)", sm2.voices[0].notes[0].acc === 1 && sm2.voices[1].notes[0].acc === null, JSON.stringify(sm2.voices.map((v) => v.notes.map((n) => n.acc))));
  const tie = { ...plain, measure: { ...plain.measure, voices: [{ voice: 1, staff: 1, notes: [{ id: 0, note: 73, pos: 0, dur: 24, type: "quarter", dots: 0, tieStop: true }, { id: 1, note: 73, pos: 24, dur: 24, type: "quarter", dots: 0 }], rests: [] }] } };
  const tm = modelBar(tie, { meter: METER44, spelledOf, fifths: 0 });
  check("a tied-to note never reprints its accidental; the next one does", tm.voices[0].notes[0].acc === null && tm.voices[0].notes[1].acc === -1, JSON.stringify(tm.voices[0].notes.map((n) => n.acc)));
  check("key signature: Eb in Eb major shows no accidental", modelBar({ ...plain, measure: { ...plain.measure, voices: [{ voice: 1, staff: 1, notes: [{ id: 0, note: 75, pos: 0, dur: 24, type: "quarter" }], rests: [] }] } }, { meter: METER44, spelledOf: (p) => { const s = spellMidi(p.note, "Eb major"); return { letter: s.letter, acc: s.acc, octave: s.octave }; }, fifths: -3 }).voices[0].notes[0].acc === null);

  // engraver interface (plan-amendments.md section 0 rule 1)
  const E = createHouseEngraver();
  check("engraver API and name", ENGRAVER_API === "arsenal.piano.score.engrave/v0" && E.name === "house" && typeof E.measureBar === "function" && typeof E.engraveBar === "function");
  const dense = denseBar({ onsets: 43 });
  const dm = modelBar(dense, { meter: METER44, spelledOf, fifths: 0 });
  const c0 = stubCtx();
  check("font gate: ready(false) and engraveBar draws nothing", E.ready({ smufl: false }) === false && E.engraveBar(c0, dm, { L }).drawn === false && c0.calls.draw === 0);
  const mb = E.measureBar(dm, { L });
  check("measureBar: minWidth and one width per beat, widened beats >= 96 px", mb.beatWidths.length === 4 && mb.beatWidths.every((w) => w >= 96) && Math.abs(mb.minWidth - mb.beatWidths.reduce((x, y) => x + y, 0) - mb.layout.lead) < 1e-6);
  const c1 = stubCtx();
  E.ready({ smufl: true });
  const eb = E.engraveBar(c1, dm, { L, ink: "full" });
  check("engraveBar draws once the font is ready and returns width and boxes", eb.drawn && c1.calls.draw > 43 && eb.width === mb.minWidth && eb.boxes.length >= 43 && eb.ms === null);

  // header: the hold display after a family press never shows a blank (ls1-rulings.md; LS3 header model)
  const pin = G.genPiece("6/8", "arp", 0, 50, 4242, { pickup: 0 });
  for (const ratio of [2, 0.5]) {
    const tr = createTranscriber({ options: { meter: "6/8" } });
    let pressed = false, blank = 0, holdTicks = 0, holdNoNumber = 0, dimOk = true, confirmed = false, afterPress = 0;
    replayInto(tr, G.eventsOf(pin.piece ?? pin), {
      onTick: (out, T, t) => {
        const tx = headerText(out.header);
        if (!pressed && T >= 20000) { t.chooseLevel(ratio); pressed = true; return; }
        if (!pressed) return;
        afterPress++;
        if (!tx.left || /≈\s*·/.test(tx.left)) blank++;
        if (out.header.word === "hold" && out.header.requested != null) { holdTicks++; if (!/≈ \d+ · hold/.test(tx.left)) holdNoNumber++; if (!tx.dim) dimOk = false; }
        else if (holdTicks) confirmed = true;
      },
    });
    const c2 = stubCtx();
    paintHeader(c2, L, { bpm: 100, dim: true, word: "hold", requested: 100, source: "inferred", meter: "6/8" });
    const painted = c2.calls.text[0];
    check(`header after a x${ratio} press: 0 blank ticks, the request dimmed with "hold" until confirmed`, afterPress > 0 && blank === 0 && holdTicks > 0 && holdNoNumber === 0 && dimOk && confirmed, JSON.stringify({ afterPress, blank, holdTicks, holdNoNumber, dimOk, confirmed }));
    check("paintHeader draws the hold header dimmed", painted && /♩ ≈ 100 · hold · heard/.test(painted.s) && painted.alpha < 1, JSON.stringify(painted));
  }
  check("header: no readout yet reads an ellipsis, never a blank", headerText({ bpm: null, word: "free", source: "free" }).left === "♩ ≈ … · free · —");

  // painters draw on a 2D context only
  const c3 = stubCtx();
  const tw = tapeWindow({ onsets: 43, spell, L });
  paintTape(c3, L, tw.columns, { endX: (x) => x.endX, ticks: tw.ticks });
  paintOpenBar(c3, L, layoutBar(dm, L, { widen: false }));
  paintPedalLine(c3, L, [{ x0: 0, x1: 300, notches: [120], open: false }]);
  paintStaves(c3, L, { fonts: { smufl: true } });
  check("paint.js painters draw on a stub 2D context", c3.calls.draw > 40);

  // the ribbon's clock is monotonic: a seek builds a new ribbon
  const R = createRibbon({ spell, layout: L });
  R.tick(1000);
  let threw = false;
  try { R.tick(750); } catch (e) { threw = e instanceof RangeError; }
  check("ribbon: tick with the clock going back throws RangeError (a seek builds a new ribbon)", threw);
}

if (!quick) {
  // ================================================================================ LR11f / LR11g fixtures ===
  const run15 = G.genTapeRun({ seconds: 1.5, rate: 10 }), run4 = G.genTapeRun({ seconds: 4, rate: 10 });
  const w15 = watcher(), w4 = watcher();
  const R15 = replayRibbon(run15.events, { meter: "4/4" }, { onTick: w15.onTick }), R4 = replayRibbon(run4.events, { meter: "4/4" }, { onTick: w4.onTick });
  const s15 = R15.stats(), s4 = R4.stats();
  check("LR11f: the 1.5 s run at 10 groups a second has 0 overlapping heads", s15.columns === 15 && s15.overlaps === 0 && s15.clamped === 0, JSON.stringify({ columns: s15.columns, overlaps: s15.overlaps, clamped: s15.clamped }));
  receipts.push({ id: "LR11f-fixture", measured: { run1_5s: { columns: s15.columns, overlaps: s15.overlaps, clamped: s15.clamped }, run4s: { columns: s4.columns, overlaps: s4.overlaps, clamped: s4.clamped, overlapsPerTapeMinute: r4(s4.overlapsPerTapeMinute) } }, threshold: "0 on the 1.5 s run; the 4 s run reported", pass: s15.overlaps === 0 });
  check("tape runs: columns never move, scroll never goes back", w15.columnMoves + w4.columnMoves === 0 && w15.scrollBack + w4.scrollBack === 0);

  const lr11g = {};
  for (const n of BENCH_SIZES) {
    const bar = denseBar({ onsets: n });
    const m = modelBar(bar, { meter: METER44, spelledOf, fifths: 0 });
    const on = overlaps(layoutBar(m, L, { widen: true }).boxes, L), off = overlaps(layoutBar(m, L, { widen: false, push: false }).boxes, L);
    const openPush = overlaps(layoutBar(m, L, { widen: false }).boxes, L);
    lr11g["bar" + n] = { onsets: bar.onsets, collisionsWidened: on.length, collisionsNoWidening: off.length, collisionsOpenBarLayout: openPush.length, kinds: [...new Set(on.map(([x, y]) => x.kind + "/" + y.kind))] };
    check(`LR11g: ${n}-onset bar, 0 glyph collisions with widening`, bar.onsets === n && on.length === 0, JSON.stringify(lr11g["bar" + n]));
  }
  // also in other signatures and with two voices per staff on every family's clean copies (oracle beats), a wider net
  let famBars = 0, famCollisions = 0;
  const famKinds = new Map();
  for (const fam of G.FAMILIES) for (const row of G.familySuite(fam)) {
    const tr = createTranscriber({ spell, options: { meter: row.take.spec.meter, beats: row.take.truth.beats_ms, one: row.take.truth.downbeats_ms[0] } });
    replayInto(tr, row.take.events);
    tr.finish();
    const sc = tr.score();
    const byId = new Map(sc.notes.map((n) => [n.id, n]));
    for (const m of sc.measures) {
      if (m.kind !== "metric") continue;
      const meter = { ...sc.meter, beatTicks: sc.meter.beatTicks };
      const model = modelBar(m, { meter, spelledOf: (p) => { const n = byId.get(p.id); return n && n.spelled ? n.spelled : spelledOf(p); }, clefs: m.clefs, octave: m.octave, fifths: 0 });
      const ov = overlaps(layoutBar(model, L, { widen: true }).boxes, L);
      famBars++; famCollisions += ov.length;
      for (const [x, y] of ov) famKinds.set(x.kind + "/" + y.kind, (famKinds.get(x.kind + "/" + y.kind) || 0) + 1);
    }
  }
  receipts.push({ id: "LR11g", measured: { bench: lr11g, familyCleanCopies: { bars: famBars, collisions: famCollisions, perBar: r4(famCollisions / Math.max(1, famBars)), kinds: Object.fromEntries(famKinds) } }, threshold: "0 per settled bar with widening on the 12/24/43/67-onset bench bars; fixed beats and the family clean copies reported", pass: BENCH_SIZES.every((n) => lr11g["bar" + n].collisionsWidened === 0) });

  // ============================================================================ LR11e and the ribbon invariants ===
  const agg = () => ({ unwidened: { n: 0, px: 0 }, widened: { n: 0, px: 0 }, beatLocal: { n: 0, px: 0 }, moved: 0, x0: { n: 0, px: 0 } });
  const add = (A, s) => { for (const k of ["unwidened", "widened"]) { A[k].n += s[k].n; A[k].px += s[k].px; } A.moved += s.moved; A.x0.n += s.x0.n; A.x0.px += s.x0.px; };
  const oracle = { OE: agg(), SS: agg() }, inferred = { OE: agg(), SS: agg() };
  const inv = { blockChanges: 0, columnMoves: 0, scrollBack: 0, drawnTwice: 0, liveOnTape: 0, conflicts: 0, demoted: 0, tiedFromTape: 0, idMismatch: 0, commits: 0, columns: 0, takes: 0 };
  // beat-local shift needs the layouts: recompute it from a second pass that records open layouts
  const beatLocal = { oracle: { n: 0, px: 0 }, inferred: { n: 0, px: 0 } };
  function lr11eRun(events, options, bucket, key) {
    const w = watcher();
    const openLayouts = new Map(), done = new Set();
    const R = replayRibbon(events, options, {
      onTick: (r) => {
        w.onTick(r);
        const v = r.view();
        for (const b of v.live) {
          if (b.state === "open") openLayouts.set(b.index, { ...b.layout, beatTicks: b.model.beatTicks });
          else if (openLayouts.has(b.index) && !done.has(b.index)) { const s = headShift(openLayouts.get(b.index), { ...b.layout, beatTicks: b.model.beatTicks }, L); beatLocal[key].n += s.beatLocal.n; beatLocal[key].px += s.beatLocal.meanPx * s.beatLocal.n; done.add(b.index); }
        }
        for (const b of v.blocks) if (openLayouts.has(b.index) && !done.has(b.index)) { const s = headShift(openLayouts.get(b.index), { ...b.layout, beatTicks: b.model.beatTicks }, L); beatLocal[key].n += s.beatLocal.n; beatLocal[key].px += s.beatLocal.meanPx * s.beatLocal.n; done.add(b.index); }
      },
    });
    const st = R.stats();
    add(bucket.OE, st.shiftOpenToEngraved); add(bucket.SS, st.shiftSettlingToSettled);
    inv.blockChanges += w.blockChanges; inv.columnMoves += w.columnMoves; inv.scrollBack += w.scrollBack; inv.drawnTwice += w.drawnTwice; inv.liveOnTape += w.liveOnTape;
    inv.conflicts += st.conflicts; inv.demoted += st.demoted; inv.tiedFromTape += st.tiedFromTape; inv.idMismatch += st.idMismatch; inv.commits += st.commits; inv.columns += st.columns; inv.takes++;
  }
  for (const fam of G.FAMILIES) for (const row of G.familySuite(fam)) lr11eRun(row.take.events, { meter: row.take.spec.meter, beats: row.take.truth.beats_ms, one: row.take.truth.downbeats_ms[0] }, oracle, "oracle");
  for (const row of G.tempoSuite()) lr11eRun(G.eventsOf(row.piece), { meter: row.meter }, inferred, "inferred");
  const bl = (k) => (beatLocal[k].n ? r4(beatLocal[k].px / beatLocal[k].n / L.sp) : 0);
  const e = { oracle: { ...shiftOut(oracle.OE), unwidenedBeatLocalSp: bl("oracle"), beatLocalN: beatLocal.oracle.n, settlingToSettled: shiftOut(oracle.SS) }, inferred: { ...shiftOut(inferred.OE), unwidenedBeatLocalSp: bl("inferred"), beatLocalN: beatLocal.inferred.n, settlingToSettled: shiftOut(inferred.SS) } };
  const lr11eOk = e.oracle.unwidenedBeatLocalSp <= 0.5 && e.inferred.unwidenedBeatLocalSp <= 0.5;
  check("LR11e: mean head x shift at the settle crossfade on beats that did not widen <= 0.5 s (beat-local), fixtures", lr11eOk && beatLocal.oracle.n > 1000, JSON.stringify(e));
  receipts.push({ id: "LR11e-fixtures", measured: e, threshold: "<= 0.5 s mean on beats that did not widen (beat-local); in-bar shift and widened beats reported", pass: lr11eOk });
  const lr11dOk = inv.blockChanges === 0 && inv.columnMoves === 0 && inv.scrollBack === 0 && inv.drawnTwice === 0 && inv.liveOnTape === 0;
  check("LR11d (model): frozen blocks never change, tape columns never move, scroll never goes back, every note drawn once", lr11dOk, JSON.stringify(inv));
  // the inferred-beat tempo suite holds notes tied into a settled bar from tape (22 before repair r1): the path is exercised
  check("drawn once: notes tied in from tape are left out of the frozen bar (the path runs on the fixtures)", inv.tiedFromTape > 0, JSON.stringify(inv));
  check("ribbon: the mirrored onset ids equal the transcriber's", inv.idMismatch === 0);
  receipts.push({ id: "LR11d-model", measured: inv, threshold: "0 frozen-block changes, 0 column moves, 0 scroll reversals, 0 notes drawn twice (frozen block and tape, two tape columns, onset in two blocks), 0 live blocks drawing a taped note", pass: lr11dOk });
}

// ================================================================================== sessions (S1..Sn) ===
if (sessions) {
  const ROOT = path.join(here, "..", "state", "arsenal", "performance"), OUT = path.join(here, "..", "state", "arsenal", "score");
  if (!fs.existsSync(ROOT)) console.log("sessions: state/arsenal/performance is missing, skipped");
  else {
    const t1 = performance.now();
    const dirs = fs.readdirSync(ROOT).filter((d) => fs.existsSync(path.join(ROOT, d, "events.jsonl"))).sort();
    const rows = [];
    dirs.forEach((d, i) => {
      const name = "S" + (i + 1);
      const events = fs.readFileSync(path.join(ROOT, d, "events.jsonl"), "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l)).filter((e) => e.kind in ORDER);
      const ons = events.filter((e) => e.kind === "on").length;
      if (ons < 100) { rows.push({ name, skipped: true }); return; }
      const w = watcher();
      const tickMs = [];
      let last = performance.now();
      const R = replayRibbon(events, { meter: "4/4" }, { onTick: (r) => { const now = performance.now(); tickMs.push(now - last); last = now; w.onTick(r); } });
      const st = R.stats();
      const sorted = [...tickMs].sort((a, b) => a - b);
      rows.push({
        name, onsets: ons, tapeMinutes: r4(st.tapeMinutes), columns: st.columns, overlaps: st.overlaps, overlapsPerTapeMinute: r4(st.overlapsPerTapeMinute), clamped: st.clamped,
        frozenBars: st.commits, tapeBars: st.tapeBars, conflicts: st.conflicts, collapses: st.collapses, waitMaxMs: st.waitMaxMs,
        shiftOpenToEngraved: shiftOut(st.shiftOpenToEngraved), invariants: { blockChanges: w.blockChanges, columnMoves: w.columnMoves, scrollBack: w.scrollBack, drawnTwice: w.drawnTwice, liveOnTape: w.liveOnTape }, tiedFromTape: st.tiedFromTape,
        tickP95Ms: r4(sorted[Math.floor(sorted.length * 0.95)] ?? 0),
      });
    });
    const used = rows.filter((r) => !r.skipped);
    const tapeMin = used.reduce((s, r) => s + r.tapeMinutes, 0), ov = used.reduce((s, r) => s + r.overlaps, 0);
    const summary = {
      date: "2026-09-15", slice: "LS5", config: "ribbon.js over index.js defaults, meter 4/4, spell.js in the lab key tracker's settled key, layout 9:16",
      sessions: rows.length, skipped: rows.filter((r) => r.skipped).map((r) => r.name),
      LR11f: { pooledOverlapsPerTapeMinute: r4(ov / Math.max(1e-9, tapeMin)), maxSession: used.reduce((m, r) => (r.overlapsPerTapeMinute > (m ? m.overlapsPerTapeMinute : -1) ? r : m), null)?.name, threshold: "pooled overlapping heads per tape minute <= 3.0 over S1..Sn (plan-amendments.md section 5); per session reported" },
      invariants: Object.fromEntries(["blockChanges", "columnMoves", "scrollBack", "drawnTwice", "liveOnTape"].map((k) => [k, used.reduce((s, r) => s + r.invariants[k], 0)])),
      rows, ms: Math.round(performance.now() - t1),
    };
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, "ls5-layout-bench-2026-09-15.json"), JSON.stringify(summary, null, 1));
    check("S1..Sn ribbon invariants: frozen blocks never change, columns never move, scroll never goes back, every note drawn once", Object.values(summary.invariants).every((n) => n === 0), JSON.stringify(summary.invariants));
    // LR11f on S1..Sn, gated since repair LS5 r1 (the limit was recorded in plan-amendments.md section 5 but never compared)
    const pooled = summary.LR11f.pooledOverlapsPerTapeMinute, lr11fOk = used.length > 0 && tapeMin > 0 && pooled <= 3.0;
    summary.LR11f.pass = lr11fOk;
    fs.writeFileSync(path.join(OUT, "ls5-layout-bench-2026-09-15.json"), JSON.stringify(summary, null, 1));
    check("LR11f S1..Sn: pooled overlapping heads per tape minute <= 3.0", lr11fOk, JSON.stringify({ pooled, tapeMinutes: r4(tapeMin), overlaps: ov, sessions: used.length }));
    receipts.push({ id: "LR11f-sessions", measured: { pooled, tapeMinutes: r4(tapeMin), overlaps: ov, perSession: Object.fromEntries(used.map((r) => [r.name, { perTapeMinute: r.overlapsPerTapeMinute, overlaps: r.overlaps, tapeMinutes: r.tapeMinutes, clamped: r.clamped }])) }, threshold: summary.LR11f.threshold, pass: lr11fOk });
    console.log("sessions bench written to state/arsenal/score/ls5-layout-bench-2026-09-15.json");
  }
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r));
console.log(`score_layout: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
