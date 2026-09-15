// G1 bench fixtures for live sheet music: arsenal/web/piano/score/bench.js (pure ES module: no DOM, no clock).
// Slice LS5, research/in-flight/live-sheet-music-2026-09-14/rendering-formats.md section 9 gate G1 and
// live-sheet-music-plan.md LR11a-c, LR11g: synthetic bars of 12, 24, 43 and 67 onsets (note-ons) with a 10-head chord
// column, triplets, sextuplets, 16ths, seconds, accidentals and rests; tape windows of 43 and 67 onsets in 3 s placed by
// the C6 placer. Shared by the lab page (timings in Chrome) and tests/score_layout.test.mjs (geometry). No session data.
//
//   denseBar({ onsets: 43, seed: 43 })      -> a transcriber-shaped bar { index, state, kind, beats, start_ms, end_ms, measure }
//   tapeWindow({ onsets: 67, spell, L })     -> { columns (placed), ticks, clamped }

import { buildMeasures } from "./measures.js";
import { createTapePlacer, tapeHeads } from "./layout.js";

export const BENCH_API = "arsenal.piano.score.bench/v0";
export const BENCH_SIZES = Object.freeze([12, 24, 43, 67]);

function rng(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const METER44 = Object.freeze({ label: "4/4", beats: 4, beatType: 4, tactus: 4, compound: false, beatTicks: 24, barTicks: 96, free: false });

// Slots after the chord: voice 1 (treble) triplet eighths on beat 2, 16ths on beat 3, a sextuplet on beat 4; voice 3
// (bass) eighths, triplet eighths and 16ths on beats 2-4. Round-robin over the six figures, one note per slot, then a
// third above per slot, then a fifth above, until the onset count is reached (at most 10 + 22 x 3 = 76).
const FIGURES = [
  { voice: 1, staff: 1, beat: 1, d: 3, base: 76 }, { voice: 3, staff: 2, beat: 1, d: 2, base: 50 },
  { voice: 1, staff: 1, beat: 2, d: 4, base: 74 }, { voice: 3, staff: 2, beat: 2, d: 3, base: 48 },
  { voice: 1, staff: 1, beat: 3, d: 6, base: 79 }, { voice: 3, staff: 2, beat: 3, d: 4, base: 45 },
];

export function denseNotes({ onsets = 43, seed = 1 } = {}) {
  const r = rng(seed * 7919 + 1);
  const notes = [];
  let id = 0;
  const add = (tick, dur, note, voice, staff) => notes.push({ id: id++, note, tick, dur, voice, staff, on_ms: tick * 31.25 });
  const alter = (n) => (r() < 0.3 ? n + (r() < 0.5 ? 1 : -1) : n);
  // the 10-head chord column on beat 1, with a second in each hand
  for (const n of [72, 76, 77, 79, 84]) add(0, 24, n, 1, 1);
  for (const n of [36, 43, 48, 52, 53]) add(0, 24, n, 4, 2);
  const slots = [];
  const per = FIGURES.map((f) => Array.from({ length: f.d }, (_, k) => ({ f, k })));
  for (let i = 0; slots.length < 22; i++) for (const list of per) if (list[i]) slots.push(list[i]);
  let left = Math.max(0, onsets - 10);
  const stack = [0, 3, 7];
  const scale = [0, 2, 4, 5, 7, 9, 11, 12, 14];
  for (let layer = 0; layer < 3 && left > 0; layer++) {
    for (const s of slots) {
      if (left <= 0) break;
      const f = s.f, step = f.base + scale[(s.k * 2 + f.beat) % scale.length] - (f.staff === 2 ? 0 : 0);
      const note = alter(step + stack[layer]);
      const dur = 24 / f.d, tick = f.beat * 24 + s.k * dur;
      add(tick, dur, note, f.voice, f.staff);
      left--;
    }
  }
  return notes;
}

export function denseBar({ onsets = 43, seed = onsets } = {}) {
  const notes = denseNotes({ onsets, seed });
  const [measure] = buildMeasures(notes, { meter: METER44, from: 0, to: 1 });
  return { index: 0, state: "settled", kind: "metric", rev: 0, beats: 4, start_ms: 0, end_ms: 3000, measure, notes, onsets: notes.length, meter: METER44 };
}

// A tape window: `onsets` note-ons in `seconds`, as groups of 1-3 notes alternating hands, placed by the C6 placer.
// spell(midis, key) -> [{ midi, letter, acc, octave }] (the injected speller).
export function tapeWindow({ onsets = 43, seconds = 3, seed = onsets, spell, L, fifths = 0 } = {}) {
  const r = rng(seed * 104729 + 3);
  const P = createTapePlacer(L, { x0: 0, t0: 0 });
  const columns = [];
  let left = onsets, t = 0, id = 0, gi = 0;
  const groupsN = Math.ceil(onsets / 1.7);
  const dt = (seconds * 1000) / groupsN;
  while (left > 0) {
    const size = Math.min(left, 1 + Math.floor(r() * 3));
    const right = gi % 2 === 0;
    const base = right ? 64 + Math.floor(r() * 20) : 36 + Math.floor(r() * 20);
    const midis = Array.from({ length: size }, (_, k) => base + [0, 1, 4][k] + (r() < 0.25 ? 1 : 0));
    const spelled = spell ? spell(midis, null) : midis.map(() => null);
    const items = midis.map((m, k) => ({ id: id++, note: m, staff: m >= 60 ? 1 : 2, spelled: spelled[k] }));
    const { heads, w, accW } = tapeHeads(items, L, { fifths });
    const c = P.place(t, w);
    for (const h of heads) h.endX = c.x + 0.3 * (dt * L.v) + 40;
    columns.push({ gid: gi, t, x: c.x, w, D: c.D, clamped: c.clamped, headX: c.x + accW + 0.11 * L.sp, heads });
    left -= size; t += dt * (0.7 + 0.6 * r()); gi++;
  }
  const ticks = [];
  for (let s = 0; s <= seconds * 1000; s += 1000) ticks.push(P.warpX(s));
  return { columns, ticks, clamped: columns.filter((c) => c.clamped).length, onsets };
}
