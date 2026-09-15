// Node tests for arsenal/web/piano/groove.js and arsenal/groove_bridge.mjs (jam-spec 10.2-10.6; A2, groove half).
// Zero dependencies:  node tests/jam_groove.test.mjs
//
// A2 rows covered here: determinism over 1000 random (def, settings, seed, pass, bar) inputs, in-process and across a
// node process; humanize 0 puts every event on its table position and velocity (hand-derived bars, plus a table
// check over random bar-aligned defs); transposing the def to all 12 keys leaves every event's beat, len and vel (and
// ms) unchanged; ties and pickups belong to the bar that owns them; the bridge gives the module's events for 200 bars.
// Also: dropout, the ballad early step, Try backings, Play, count-in, meters, the lament's ties, errors.
// All data is synthetic or from tests/fixtures/jam (J0): nothing reads Daniel's practice log.
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import * as G from "../arsenal/web/piano/groove.js";
import * as TM from "../arsenal/web/piano/tempomap.js";
import { answer } from "../arsenal/groove_bridge.mjs";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let passed = 0, failed = 0;
function check(label, ok, detail = "") {
  if (ok) {
    passed++;
    if (label.startsWith("A2")) console.log(`ok ${label}`);  // the acceptance rows print their counts as a receipt
    return;
  }
  failed++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const fx = (name) => JSON.parse(readFileSync(here(`./fixtures/jam/${name}`), "utf8"));
const clone = (x) => JSON.parse(JSON.stringify(x));
const LYD = fx("def_lydian_four.json");
const LAMENT = fx("def_lament_bass.json");
const DROP = fx("def_minor_third_drop_a.json");
const DORIAN = fx("def_dorian_vamp.json");
const WALTZ = fx("def_waltz_rest.json");

const S = (o = {}) => ({ from_bar: 0, groove: "hold", backing: "full", level: 44, humanize: 0, seed: 1, walk: 1,
  try_backing: null, passes: 0, ending: "cut", ...o });
const fmt = (e) => `${e.beat} ${e.voice[0]} ${e.midi} v${e.vel} l${e.len} ${e.row}${e.tie ? " tie" : ""}${e.carry ? " carry" : ""}`;
function expectBar(label, events, lines) {
  const got = events.map(fmt);
  const n = Math.max(got.length, lines.length);
  for (let i = 0; i < n; i++) {
    if (got[i] !== lines[i]) {
      check(label, false, `line ${i}: got ${JSON.stringify(got[i])} want ${JSON.stringify(lines[i])}\n  got all:\n    ${got.join("\n    ")}`);
      return;
    }
  }
  check(label, true);
}
const cycleBars = (def) => def.cycle_beats / def.beats_per_bar;
const barAt = (def, settings, n, opts = {}) =>
  G.bar(def, settings, Math.floor((n - (opts.def_from_bar ?? 0)) / cycleBars(def)), n, opts);

// A def from compact slots: {beats, bass, upper, tones, roles?, section?, key?, play?, hold?, vel?, arp?}.
const KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
function fixedDef({ key, m = 4, slots, backing = "comp", cycle = null }) {
  let at = 0;
  const out = slots.map((s, i) => {
    const a = s.at ?? at;
    at = a + s.beats;
    const upperRoles = s.roles ?? s.upper.map((_, j) => ["third", "seventh", "ninth", "fifth", "eleventh"][j % 5]);
    const v = [s.bass, ...s.upper];
    const roles = ["bass", ...upperRoles];
    const slot = { i, section: s.section ?? 0, at_beat: a, beats: s.beats, n: `x${i}`, name: `x${i}`, key: s.key ?? key,
      tones_pc: s.tones, bass_pc: s.bass % 12, chord_pcs: [], scale: G.keyScale(s.key ?? key), scale_name: "x",
      class: "diatonic", voicings: { play: s.play ?? v, full: v, comp: v, bass: [s.bass] },
      roles: { full: roles, comp: roles, bass: ["bass"] }, exact: true, upper_same: false, vel: s.vel ?? 48,
      arp_ms: s.arp ?? 0, say: null, page_reads: null, warnings: [] };
    if (s.hold != null) slot.hold = s.hold;
    return slot;
  });
  const sections = [];
  for (const s of out) if (!sections.length || sections[sections.length - 1].i !== s.section) sections.push({ i: s.section, key: s.key, from_beat: s.at_beat });
  return { api: "arsenal.jam.def/v0", card: { id: "t", rev: 1, title: "t", variant: null }, key, beats_per_bar: m,
    cycle_beats: cycle ?? at, backing, sections, slots: out, warnings: [] };
}
// Abmaj7 | Bb11/Ab | Eb/G | Ebmaj9 in Eb, comp: the gospel 5 over 4 shape, for ballad.
const GOSPEL = fixedDef({ key: "Eb major", slots: [
  { beats: 4, bass: 44, upper: [55, 60, 63], tones: { root: 8, third: 0, fifth: 3, seventh: 7 } },
  { beats: 4, bass: 44, upper: [53, 56, 62], tones: { root: 10, third: 2, fifth: 5, seventh: 8, eleventh: 3 } },
  { beats: 4, bass: 43, upper: [51, 55, 58], tones: { root: 3, third: 7, fifth: 10 } },
  { beats: 4, bass: 39, upper: [50, 55, 58], tones: { root: 3, third: 7, fifth: 10, seventh: 2, ninth: 5 } },
] });

// ======================================================================================= random source and helpers
{
  check("fnv1a32 empty", G.fnv1a32("") === 0x811c9dc5);
  check("fnv1a32 a", G.fnv1a32("a") === 0xe40c292c);
  check("fnv1a32 foobar", G.fnv1a32("foobar") === 0xbf9cf968);
  // The classic mulberry32, written independently.
  function classic(a) {
    return function () {
      let t = (a += 0x6d2b79f5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  for (const seed of [0, 1, 90210, 0xdeadbeef]) {
    const a = G.mulberry32(seed), b = classic(seed >>> 0);
    let same = true;
    for (let i = 0; i < 1000; i++) if (a() !== b()) same = false;
    check(`mulberry32 matches the classic generator (seed ${seed})`, same);
  }
  const r1 = G.laneRandom(90210, 0, 3, 1), r2 = G.laneRandom(90210, 0, 3, 1);
  check("laneRandom is keyed by (seed, pass, bar, lane)", r1.next() === r2.next()
    && r1.next() === mulberryOf("90210:0:3:1", 2));
  check("laneRandom differs by bar", G.laneRandom(90210, 0, 3, 1).next() !== G.laneRandom(90210, 0, 4, 1).next());
  check("laneRandom differs by lane", G.laneRandom(90210, 0, 3, 1).next() !== G.laneRandom(90210, 0, 3, "roll").next());
  function mulberryOf(key, nth) { const g = G.mulberry32(G.fnv1a32(key)); let v; for (let i = 0; i < nth; i++) v = g(); return v; }

  check("keyScale Eb major", JSON.stringify(G.keyScale("Eb major")) === "[3,5,7,8,10,0,2]");
  check("keyScale D minor", JSON.stringify(G.keyScale("D minor")) === "[2,4,5,7,9,10,0]");
  check("keyScale F# minor", JSON.stringify(G.keyScale("F# minor")) === "[6,8,9,11,1,2,4]");
  check("keyScale junk", G.keyScale("not a key") === null);

  const eb = G.keyScale("Eb major");
  check("approach |d| <= 2: none", G.approachNote(44, 43, eb) === null && G.approachNote(46, 44, eb) === null);
  check("approach |d| 5 up: a half step below", G.approachNote(39, 44, eb) === 43);
  check("approach |d| 5 down: a half step below", G.approachNote(44, 39, eb) === 38);
  check("approach |d| 4: the key note in the middle", G.approachNote(43, 39, eb) === 41 && G.approachNote(39, 43, eb) === 41);
  check("approach |d| 3: the key note nearest the middle", G.approachNote(40, 43, G.keyScale("C major")) === 41);
  check("approach |d| 3, two key notes equally near the middle: the lower", G.approachNote(40, 43, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) === 41);
  check("approach |d| 3 with no key note between: the lower chromatic middle", G.approachNote(40, 43, [0]) === 41);
  check("approach below E1 goes above", G.approachNote(33, 28, eb) === 29);
  check("secondBass: root position with a natural 5th, 5th below", G.secondBass(GOSPEL.slots[0], 44) === 39);
  check("secondBass: slash chord repeats the bass", G.secondBass(GOSPEL.slots[1], 44) === 44);
  check("secondBass: 5th above when below is out of range", G.secondBass({ tones_pc: { root: 4, fifth: 11 }, bass_pc: 4 }, 28) === 35);

  const lydUpper = [51, 55, 60, 62].map((midi, i) => ({ midi, role: ["fifth", "seventh", "third", "eleventh"][i], lane: i + 1 }));
  check("pulseVoices full: 3rd, 7th, top colour", JSON.stringify(G.pulseVoices(lydUpper, "full").map((v) => v.midi)) === "[55,60,62]");
  check("pulseVoices comp: the voices it has", G.pulseVoices(lydUpper, "comp").length === 4);
}

// ======================================================================================= settings, meters, errors
{
  const w = G.effectiveSettings(fixedDef({ key: "C major", m: 5, slots: [{ beats: 5, bass: 36, upper: [52, 55], tones: { root: 0 } }] }), S({ groove: "pulse" }));
  check("meter 5 pulse plays hold, with a warning", w.groove === "hold" && w.warnings.some((x) => x.includes("meter 5")));
  const g = G.effectiveSettings(LYD, S({ groove: "gospel", backing: "pad" }));
  check("a v2 groove plays ballad, pad plays comp", g.groove === "ballad" && g.backing === "comp" && g.warnings.length === 2);
  check("meter 3 keeps pulse", G.effectiveSettings(WALTZ, S({ groove: "pulse" })).groove === "pulse");
  check("L = level + groove offset", G.effectiveSettings(LYD, S({ groove: "pulse", level: 50 })).L === 46
    && G.effectiveSettings(LYD, S({ groove: "hold" })).L === 42 && G.effectiveSettings(LYD, S({ try_backing: "bass" })).L === 44);
  check("groove default by bpm", G.effectiveSettings(LYD, { backing: "full" }, { bpm: 66 }).groove === "ballad"
    && G.effectiveSettings(LYD, { backing: "full" }, { bpm: 80 }).groove === "pulse");
  check("dropout is off by default", G.effectiveSettings(LYD, S()).dropout === 0);
  const throws = (label, fn, field) => {
    try { fn(); check(label, false, "no error"); } catch (e) { check(label, e instanceof G.GrooveError && (!field || e.field === field), `${e.name} ${e.field} ${e.message}`); }
  };
  throws("a pass that disagrees with the bar", () => G.bar(LYD, S(), 1, 0), "pass");
  throws("an unknown groove", () => G.bar(LYD, S({ groove: "polka" }), 0, 0), "settings.groove");
  throws("humanize out of range", () => G.bar(LYD, S({ humanize: 2 }), 0, 0), "settings.humanize");
  throws("dropout out of range", () => G.bar(LYD, S({ dropout: -1 }), 0, 0), "settings.dropout");
  throws("a def with a bad cycle", () => G.bar({ ...LYD, cycle_beats: 6 }, S(), 0, 0), "def.cycle_beats");
  throws("overlapping slots", () => G.bar({ ...LYD, slots: [LYD.slots[0], { ...LYD.slots[1], at_beat: 2 }] }, S(), 0, 0), "def.slots[1].at_beat");
  check("muted gives no events", G.bar(LYD, S({ muted: true }), 0, 0).length === 0);
}

// ======================================================================================= humanize 0: the tables, by hand
{
  const opts = { bpm: 66 };
  // hold, full (10.3): L = 42. G (55) and D (62) tie into Abmaj7#11; the rest breathe on beat 2.
  expectBar("hold lydian bar 0", barAt(LYD, S(), 0, opts), [
    "-1 b 38 v36 l0.9 approach",
    "0 b 39 v44 l2.95 bass",
    "0 u 55 v38 l7.97 upper tie",
    "0 u 58 v38 l1.97 upper",
    "0 u 62 v38 l7.97 upper tie",
    "0 u 65 v42 l1.97 upper",
    "2 u 58 v30 l1.97 breath",
    "2 u 65 v30 l1.97 breath",
  ]);
  expectBar("hold lydian bar 1", barAt(LYD, S(), 1, opts), [
    "-1 b 43 v36 l0.9 approach",
    "0 b 44 v44 l2.95 bass",
    "0 u 51 v38 l1.97 upper",
    "0 u 55 v38 l3.97 upper carry",
    "0 u 60 v38 l1.97 upper",
    "0 u 62 v38 l3.97 upper carry",
    "2 u 51 v30 l1.97 breath",
    "2 u 60 v30 l1.97 breath",
  ]);
  expectBar("hold lydian bar 2 (pass 1 strikes again: no tie over the wrap)", barAt(LYD, S(), 2, opts), barAt(LYD, S(), 0, opts).map(fmt));
  expectBar("hold at 120 bpm: no breath row (a beat under 0.6 s)", barAt(LYD, S(), 0, { bpm: 120 }), [
    "-1 b 38 v36 l0.9 approach",
    "0 b 39 v44 l2.95 bass",
    "0 u 55 v38 l7.97 upper tie",
    "0 u 58 v38 l3.97 upper",
    "0 u 62 v38 l7.97 upper tie",
    "0 u 65 v42 l3.97 upper",
  ]);
  expectBar("hold walk 0: no approach", barAt(LYD, S({ walk: 0 }), 0, opts).filter((e) => e.voice === "bass"), ["0 b 39 v44 l3.97 bass"]);

  // ballad, comp (10.4): L = 44.
  const B = S({ groove: "ballad", backing: "comp" });
  expectBar("ballad bar 0", barAt(GOSPEL, B, 0, opts), [
    "-1 b 43 v38 l0.9 approach",
    "0 b 44 v48 l1.9 bass",
    "0 u 55 v42 l1.95 upper",
    "0 u 60 v42 l1.95 upper",
    "0 u 63 v46 l1.95 upper",
    "2 b 39 v42 l1.9 second",
    "2 u 55 v34 l1.95 inner",
    "2 u 60 v34 l1.95 inner",
  ]);
  expectBar("ballad bar 1 (slash chord: the second bass repeats Ab; Ab to G steps, so no approach)", barAt(GOSPEL, B, 1, opts), [
    "0 b 44 v48 l1.9 bass",
    "0 u 53 v42 l1.95 upper",
    "0 u 56 v42 l1.95 upper",
    "0 u 62 v46 l1.95 upper",
    "2 b 44 v42 l1.9 second",
    "2 u 53 v34 l1.95 inner",
    "2 u 56 v34 l1.95 inner",
  ]);
  expectBar("ballad bar 2 (0.95 before the beat-4 approach)", barAt(GOSPEL, B, 2, opts), [
    "0 b 43 v48 l1.9 bass",
    "0 u 51 v42 l1.95 upper",
    "0 u 55 v42 l1.95 upper",
    "0 u 58 v46 l1.95 upper",
    "2 b 43 v42 l0.95 second",
    "2 u 51 v34 l1.95 inner",
    "2 u 55 v34 l1.95 inner",
  ]);
  expectBar("ballad bar 3 (the approach F leads in; the second bass makes room for the early step)", barAt(GOSPEL, B, 3, opts), [
    "-1 b 41 v38 l0.9 approach",
    "0 b 39 v48 l1.9 bass",
    "0 u 50 v42 l1.95 upper",
    "0 u 55 v42 l1.95 upper",
    "0 u 58 v46 l1.95 upper",
    "2 b 34 v42 l1.45 second",
    "2 u 50 v34 l1.95 inner",
    "2 u 55 v34 l1.95 inner",
  ]);
  expectBar("ballad bar 4: the early step into the pass top, tied over the bar line", barAt(GOSPEL, B, 4, opts), [
    "-0.5 b 44 v48 l2.4 early",
    "0 u 55 v42 l1.95 upper",
    "0 u 60 v42 l1.95 upper",
    "0 u 63 v46 l1.95 upper",
    "2 b 39 v42 l1.9 second",
    "2 u 55 v34 l1.95 inner",
    "2 u 60 v34 l1.95 inner",
  ]);
  const early3 = barAt(DROP, B, 3, opts);
  check("ballad early step before a key item (F major to D major, slot 4)", early3.some((e) => e.row === "early" && e.beat === -0.5 && e.midi === 38)
    && !early3.some((e) => e.voice === "bass" && e.beat === 0 && !e.carry) && !early3.some((e) => e.row === "approach"),
    early3.map(fmt).join(" | "));
  const approach4 = barAt(DROP, B, 4, opts);
  check("inside a section the approach stays", approach4.some((e) => e.row === "approach" && e.beat === -1 && e.midi === 42), approach4.map(fmt).join(" | "));
  check("no early step with walk 0", !barAt(GOSPEL, { ...B, walk: 0 }, 4, opts).some((e) => e.row === "early"));
  check("no early step in hold or pulse", !barAt(GOSPEL, { ...B, groove: "hold" }, 4, opts).some((e) => e.row === "early")
    && !barAt(GOSPEL, { ...B, groove: "pulse" }, 4, opts).some((e) => e.row === "early"));

  // pulse, comp (10.5): L = 40.
  const P = S({ groove: "pulse", backing: "comp" });
  const eighths = (lo, hi) => {
    const vels = [42, 30, 34, 30, 39, 30, 34, 32];
    const out = [];
    for (let e = 0; e < 8; e++) { out.push(`${e / 2} u ${lo} v${vels[e]} l0.28 eighth`, `${e / 2} u ${hi} v${vels[e]} l0.28 eighth`); }
    return out;
  };
  const pulse0 = eighths(48, 53);
  pulse0.splice(0, 0, "-1 b 37 v34 l0.9 approach", "0 b 38 v42 l1.9 bass");
  pulse0.splice(pulse0.indexOf("2 u 48 v39 l0.28 eighth"), 0, "2 b 38 v40 l0.95 second");
  expectBar("pulse bar 0", barAt(DORIAN, P, 0, { bpm: 88 }), pulse0);
  const pulse1 = eighths(53, 59);
  pulse1.splice(0, 0, "-1 b 42 v34 l0.9 approach", "0 b 43 v42 l1.9 bass");
  pulse1.splice(pulse1.indexOf("2 u 53 v39 l0.28 eighth"), 0, "2 b 43 v40 l0.95 second");
  expectBar("pulse bar 1", barAt(DORIAN, P, 1, { bpm: 88 }), pulse1);

  // meter 3: ballad is the waltz; a rest bar is silent.
  const W = S({ groove: "ballad", backing: "full" });
  expectBar("waltz bar 0", barAt(WALTZ, W, 0, opts), [
    "-1 b 35 v38 l0.9 approach",
    "0 b 36 v48 l2.9 bass",
    "0 u 52 v42 l0.95 upper",
    "0 u 55 v42 l0.95 upper",
    "0 u 59 v46 l0.95 upper",
    "1 u 52 v34 l0.8 inner",
    "1 u 55 v34 l0.8 inner",
    "2 u 52 v34 l0.8 inner",
    "2 u 55 v34 l0.8 inner",
  ]);
  expectBar("waltz bar 1 is the rest", barAt(WALTZ, W, 1, opts), []);
  expectBar("waltz bar 3 (early step on the and of 3 into the pass top)", barAt(WALTZ, W, 3, opts), [
    "0 b 43 v48 l2.45 bass",
    "0 u 53 v42 l0.95 upper",
    "0 u 59 v42 l0.95 upper",
    "0 u 62 v46 l0.95 upper",
    "1 u 53 v34 l0.8 inner",
    "1 u 59 v34 l0.8 inner",
    "2 u 53 v34 l0.8 inner",
    "2 u 59 v34 l0.8 inner",
  ]);
  expectBar("waltz bar 4", barAt(WALTZ, W, 4, opts).filter((e) => e.voice === "bass"), ["-0.5 b 36 v48 l3.4 early"]);
  const p3 = barAt(WALTZ, S({ groove: "pulse", backing: "comp" }), 0, opts);
  check("meter 3 pulse: 6 eighths with the waltz accents", JSON.stringify(p3.filter((e) => e.row === "eighth" && e.midi === 52).map((e) => e.vel))
    === JSON.stringify([6, -6, -2, -6, 2, -6].map((a) => 40 - 4 + a)), p3.map(fmt).join(" | "));
  check("meter 3 pulse: bass for 2.9, no second bass", p3.some((e) => e.row === "bass" && e.len === 2.9) && !p3.some((e) => e.row === "second"));

  // The lament (upper: "same"): the hands hold the whole pass; only the bass walks.
  const lament = [0, 1, 2, 3, 4].map((n) => barAt(LAMENT, S(), n, { bpm: 60 }));
  const uppers = (evs) => evs.filter((e) => e.voice === "upper").map(fmt);
  check("lament bar 0: the upper shape struck once, tied", JSON.stringify(uppers(lament[0])) === JSON.stringify(
    ["0 u 56 v38 l15.97 upper tie", "0 u 60 v38 l15.97 upper tie", "0 u 61 v38 l15.97 upper tie", "0 u 63 v38 l15.97 upper tie", "0 u 65 v42 l15.97 upper tie"]),
    uppers(lament[0]).join(" | "));
  check("lament bars 1-3 carry the hands, no breath", lament.slice(1, 4).every((evs) => evs.filter((e) => e.voice === "upper").every((e) => e.carry)));
  check("lament bar 3 carries to the pass end without a tie", lament[3].filter((e) => e.voice === "upper").every((e) => e.len === 3.97 && !e.tie));
  check("lament bass walks Bb Ab Gb F", JSON.stringify(lament.slice(0, 4).map((evs) => evs.find((e) => e.row === "bass").midi)) === "[46,44,42,41]");
  check("lament pass 2 strikes the hands again", lament[4].filter((e) => e.voice === "upper").every((e) => !e.carry) && uppers(lament[4]).length === 5);

  // Try backings (10.6).
  expectBar("try bass", barAt(LYD, S({ try_backing: "bass" }), 0, opts), ["-1 b 38 v38 l0.9 approach", "0 b 39 v46 l2.95 bass"]);
  const ghosts = barAt(LYD, S({ try_backing: "ghosts" }), 0, opts);
  check("try ghosts: a soft tick on every beat", ghosts.length === 4 && ghosts.every((e, i) => e.voice === "tick" && e.beat === i && e.vel === 40 && e.freq === 1500 && e.midi === null));
  check("try loop plays the groove", JSON.stringify(barAt(GOSPEL, { ...B, try_backing: "loop" }, 0, opts)) === JSON.stringify(barAt(GOSPEL, B, 0, opts)));
  const count = G.bar(LYD, S(), -1, -1);
  check("count-in: 4 ticks at velocity 60, 2 kHz on beat 1", count.length === 4 && count.every((e, i) => e.row === "count" && e.vel === 60 && e.beat === i && e.freq === (i ? 1500 : 2000)));
  check("count-in in waltz: 3 ticks", G.bar(WALTZ, S(), -1, -1).length === 3);
  check("no count-in for play", G.bar(LYD, S(), -1, -1, { mode: "play" }).length === 0);

  // Play (10.6): exact voicings, legato to the next chord + 80 ms, no humanising.
  const play = [0, 1, 2, 3].map((n) => barAt(LYD, S({ humanize: 0.6 }), n, { mode: "play", bpm: 66 }));
  expectBar("play bar 0", play[0], [
    "0 b 39 v48 l4.088 play tie", "0 u 50 v48 l4.088 play tie", "0 u 55 v48 l4 play", "0 u 65 v48 l4.088 play tie", "0 u 70 v48 l4.088 play tie",
  ]);
  expectBar("play bar 1", play[1], [
    "0 b 39 v48 l0.088 play carry", "0 b 44 v48 l4.088 play tie", "0 u 50 v48 l0.088 play carry", "0 u 55 v48 l4.088 play tie",
    "0 u 60 v48 l4.088 play tie", "0 u 65 v48 l0.088 play carry", "0 u 70 v48 l0.088 play carry", "0 u 74 v48 l4.088 play tie", "0 u 75 v48 l4.088 play tie",
  ]);
  check("play bar 2 carries only the tail", play[2].length === 5 && play[2].every((e) => e.carry && e.len === 0.088 && !e.tie));
  check("play bar 3 is empty", play[3].length === 0);
  const arp = fixedDef({ key: "C major", slots: [
    { beats: 4, bass: 36, upper: [52, 55, 59], tones: { root: 0 }, arp: 45, vel: 60, hold: "detached" },
    { beats: 4, bass: 41, upper: [57, 60, 64], tones: { root: 5 }, hold: 2 },
  ] });
  const ap = barAt(arp, S(), 0, { mode: "play", bpm: 60 });
  check("play arp_ms rolls bottom-up", JSON.stringify(ap.map((e) => e.ms)) === "[0,45,90,135]" && ap.every((e) => e.vel === 60));
  check("play detached = length - 40 ms", ap.every((e) => e.len === 3.96));
  check("play hold as beats", barAt(arp, S(), 1, { mode: "play", bpm: 60 }).every((e) => e.len === 2));
}

// ======================================================================================= random defs
function rngOf(seed) {
  const next = G.mulberry32(seed);
  return { next, int: (a, b) => a + Math.floor(next() * (b - a + 1)), pick: (xs) => xs[Math.floor(next() * xs.length)], chance: (p) => next() < p };
}
const ROLE_POOL = ["third", "fifth", "seventh", "ninth", "eleventh", "thirteenth", "sixth", "sus", "root"];
const KEYS = ["C major", "Eb major", "Db major", "D minor", "F# minor", "Gb major", "A major", "Bb minor"];
function randomDef(r, { m = null, barAligned = false } = {}) {
  m = m ?? r.pick([4, 4, 4, 3, 3, 2, 5, 6, 7]);
  const C = r.int(1, 4) * m;
  const slots = [];
  const sections = [];
  let at = 0, section = -1, key = null;
  while (at < C - 1e-9) {
    if (at > 0 && r.chance(0.1)) { at = Math.min(C, at + (barAligned ? m : 0.5 * r.int(1, 4))); continue; }
    if (section < 0 || r.chance(0.15)) { section++; key = r.pick(KEYS); sections.push({ i: section, key, from_beat: at }); }
    const want = barAligned ? m * r.int(1, 2) : 0.5 * r.int(1, 16);
    const beats = Math.min(C - at, want);
    const bass = r.int(28, 50);
    const nUp = r.int(1, 5);
    const up = new Set();
    while (up.size < nUp) up.add(r.int(50, 69));
    const upper = [...up].sort((a, b) => a - b);
    const roles = upper.map(() => r.pick(ROLE_POOL));
    const comp = [r.chance(0.8) ? bass : r.int(28, 50), ...upper.slice(0, r.int(1, Math.min(3, upper.length)))];
    const rootPc = r.chance(0.7) ? bass % 12 : r.int(0, 11);
    const tones = { root: rootPc, third: (rootPc + r.pick([3, 4])) % 12 };
    if (r.chance(0.7)) tones.fifth = (rootPc + r.pick([7, 7, 6, 8])) % 12;
    if (r.chance(0.6)) tones.seventh = (rootPc + r.pick([10, 11])) % 12;
    const slot = { i: slots.length, section, at_beat: at, beats, n: "x", name: "x", key, tones_pc: tones, bass_pc: bass % 12,
      chord_pcs: [], scale: G.keyScale(key), scale_name: "x", class: "diatonic",
      voicings: { play: [bass, ...upper.map((u) => u + r.pick([0, 12]))].sort((a, b) => a - b), full: [bass, ...upper], comp, bass: [bass] },
      roles: { full: ["bass", ...roles], comp: ["bass", ...roles.slice(0, comp.length - 1)], bass: ["bass"] },
      exact: true, upper_same: r.chance(0.2), vel: r.int(30, 90), arp_ms: r.pick([0, 0, 30]), say: null, page_reads: null, warnings: [] };
    if (r.chance(0.5)) slot.hold = r.pick(["legato", "detached", 1.5, 3]);
    slots.push(slot);
    at += beats;
  }
  if (!slots.length) return randomDef(r, { m, barAligned });
  return { api: "arsenal.jam.def/v0", card: { id: "r", rev: 1, title: "r", variant: null }, key: sections[0].key, beats_per_bar: m,
    cycle_beats: C, backing: r.pick(["full", "comp", "bass"]), sections, slots, warnings: [] };
}
function randomSettings(r) {
  const s = S({ groove: r.pick(["hold", "ballad", "pulse", "gospel", "hold"]), backing: r.pick(["full", "comp", "bass", "pad"]),
    level: r.int(30, 80), humanize: r.pick([0, 0.3, 0.6, 1]), seed: r.int(0, 2 ** 31 - 1), walk: r.pick([0, 1, 1]),
    try_backing: r.pick([null, null, null, "ghosts", "bass", "loop"]) });
  if (r.chance(0.4)) s.dropout = r.pick([0.2, 0.5, 1]);
  return s;
}

// ======================================================================================= A2: determinism
const cases = [];
{
  const r = rngOf(20300101);
  let allSame = true, untouched = true;
  for (let i = 0; i < 1000; i++) {
    const def = randomDef(r);
    const settings = randomSettings(r);
    const mode = settings.try_backing ? null : r.pick(["loop", "loop", "play"]);
    const dfb = r.int(0, 6);
    const n = dfb + r.int(-1, 3 * cycleBars(def));
    const opts = { def_from_bar: dfb, bpm: r.int(40, 180), mode };
    const pass = Math.floor((n - dfb) / cycleBars(def));
    const before = JSON.stringify(def);
    const a = JSON.stringify(G.bar(def, settings, pass, n, opts));
    const b = JSON.stringify(G.bar(clone(def), clone(settings), pass, n, { ...opts }));
    if (a !== b) { allSame = false; check(`determinism case ${i}`, false, a.slice(0, 200)); }
    if (JSON.stringify(def) !== before) untouched = false;
    if (i < 150) cases.push({ req: { def, settings, bars: [n], def_from_bar: dfb, bpm: opts.bpm, mode }, events: a });
  }
  check("A2 determinism: 1000 random (def, settings, seed, pass, bar) inputs, byte-identical on repeat", allSame);
  check("bar() never changes its def", untouched);
  const res = spawnSync(process.execPath, [here("../arsenal/groove_bridge.mjs")], {
    input: JSON.stringify({ batch: cases.map((c) => c.req) }), encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
  let ok = res.status === 0;
  let out = null;
  try { out = JSON.parse(res.stdout); } catch (e) { ok = false; }
  check("bridge batch exits 0", ok, res.stderr || res.stdout.slice(0, 300));
  if (out) {
    const same = cases.every((c, i) => out.results[i].ok && JSON.stringify(out.results[i].bars[0].events) === c.events);
    check("A2 determinism across processes: 150 random inputs through the bridge match the module", same);
  }
}

// ======================================================================================= A2: humanize 0 on the tables
{
  const r = rngOf(7);
  const TABLE = {
    hold: { bass: [2], upper: [-4, 0], breath: [-12], approach: [-6] },
    trybass: { bass: [2], approach: [-6] },
    ballad: { bass: [4], upper: [-2, 2], second: [-2], inner: [-10], approach: [-6], early: [4] },
    pulse: { bass: [2], second: [0], approach: [-6] },
  };
  const LENS = {
    ballad4: { bass: [1.9, 0.95], upper: [1.95], second: [1.9, 0.95, 1.45], inner: [1.95], approach: [0.9] },
    ballad3: { bass: [2.9, 1.95, 2.45], upper: [0.95], inner: [0.8], approach: [0.9] },
    pulse4: { bass: [1.9, 0.95], second: [1.9, 0.95], eighth: [0.28], approach: [0.9] },
    pulse3: { bass: [2.9, 1.95], eighth: [0.28], approach: [0.9] },
  };
  let bad = 0, total = 0;
  for (let i = 0; i < 400; i++) {
    const def = randomDef(r, { m: r.pick([3, 4]), barAligned: true });
    const settings = { ...randomSettings(r), humanize: 0, level: 60, dropout: 0 };
    const E = G.effectiveSettings(def, settings, { bpm: 66 });
    const grooveKey = E.mode === "try" && E.try_backing === "bass" ? "trybass" : E.groove;
    const m = def.beats_per_bar;
    for (let n = 0; n < 2 * cycleBars(def); n++) {
      const evs = barAt(def, settings, n, { bpm: 66 });
      for (const e of evs) {
        if (e.carry || e.voice === "tick") continue;
        total++;
        const off = e.vel - E.L;
        let why = null;
        if (e.ms !== 0) why = "ms";
        else if (e.row === "eighth") {
          const acc = G.PULSE_ACCENTS[m][Math.round(e.beat * 2)];
          if (off !== -4 + acc) why = "eighth velocity";
          if (!Number.isInteger(e.beat * 2)) why = "eighth position";
        } else if (!(TABLE[grooveKey][e.row] || []).includes(off)) why = `velocity offset ${off}`;
        const pos = { bass: [0], upper: [0], second: [2], inner: m === 3 ? [1, 2] : [2], breath: [2], approach: [-1], early: [-0.5] }[e.row];
        if (pos && !pos.includes(e.beat)) why = `position ${e.beat}`;
        const lens = LENS[`${grooveKey}${m}`];
        if (lens && lens[e.row] && !lens[e.row].includes(e.len)) why = `length ${e.len}`;
        if (why) { bad++; if (bad < 5) check(`table position (${grooveKey} m${m} bar ${n})`, false, `${why}: ${fmt(e)}`); }
      }
    }
  }
  check(`A2 humanize 0: ${total} events on their table position, velocity and length`, bad === 0 && total > 5000, `${bad} off`);
}

// ======================================================================================= A2: transposition
function transposeDef(def, t) {
  const d = clone(def);
  const pc = (x) => ((x + t) % 12 + 12) % 12;
  const keyName = (k) => {
    const m = /^([A-G][#b]*)\s+(major|minor)$/.exec(k);
    const tonic = G.keyScale(k)[0];
    return `${KEY_NAMES[pc(tonic)]} ${m ? m[2] : "major"}`;
  };
  d.key = keyName(d.key);
  for (const s of d.sections) s.key = keyName(s.key);
  for (const s of d.slots) {
    s.key = keyName(s.key);
    for (const v of Object.keys(s.voicings)) s.voicings[v] = s.voicings[v].map((x) => x + t);
    for (const r of Object.keys(s.tones_pc)) s.tones_pc[r] = pc(s.tones_pc[r]);
    s.bass_pc = pc(s.bass_pc);
    s.chord_pcs = (s.chord_pcs || []).map(pc);
    s.scale = (s.scale || []).map(pc);
  }
  return d;
}
{
  const proj = (evs) => JSON.stringify(evs.map((e) => [e.beat, e.len, e.vel, e.ms, e.row, e.voice, e.tie, e.carry, e.slot]));
  const r = rngOf(12);
  const defs = [LYD, LAMENT, DROP, DORIAN, WALTZ, GOSPEL];
  for (let i = 0; i < 60; i++) defs.push(randomDef(r));
  let bad = 0, compared = 0;
  for (const def of defs) {
    const settingsList = [S(), S({ groove: "ballad", backing: "comp", humanize: 0.6, seed: 5 }), S({ groove: "pulse", humanize: 1, seed: 9, dropout: 0.5 }),
      S({ try_backing: "bass", humanize: 0.6 }), randomSettings(r)];
    for (const settings of settingsList) {
      for (const mode of ["loop", "play"]) {
        if (settings.try_backing && mode === "play") continue;
        const base = [];
        for (let n = 0; n < 2 * cycleBars(def); n++) base.push(proj(barAt(def, settings, n, { bpm: 66, mode })));
        for (let t = -6; t <= 5; t++) {
          if (t === 0) continue;
          const td = transposeDef(def, t);
          for (let n = 0; n < base.length; n++) {
            compared++;
            if (proj(barAt(td, settings, n, { bpm: 66, mode })) !== base[n]) {
              bad++;
              if (bad < 4) check(`transpose ${t} (${def.card.id} ${settings.groove} ${mode} bar ${n})`, false, `${proj(barAt(td, settings, n, { bpm: 66, mode })).slice(0, 200)} vs ${base[n].slice(0, 200)}`);
            }
          }
        }
      }
    }
  }
  check(`A2 transposition: ${compared} bars in 11 other keys keep every beat, len, vel and ms`, bad === 0 && compared > 1000, `${bad} differ`);
}

// ======================================================================================= A2: ties and pickups
{
  const r = rngOf(99);
  const jobs = [];
  for (const def of [LYD, LAMENT, DROP, DORIAN, WALTZ, GOSPEL]) {
    for (const settings of [S(), S({ groove: "ballad", backing: "comp", humanize: 0.6, seed: 3 }), S({ groove: "pulse", backing: "full", humanize: 0.6 }),
      S({ humanize: 0.6, dropout: 0.5, seed: 11 }), S({ try_backing: "bass", humanize: 0.6 })]) {
      jobs.push({ def, settings, mode: "loop" });
    }
    jobs.push({ def, settings: S(), mode: "play" });
  }
  for (let i = 0; i < 150; i++) {
    const settings = randomSettings(r);
    jobs.push({ def: randomDef(r), settings, mode: settings.try_backing ? null : r.pick(["loop", "play"]) });
  }
  let ties = 0, carries = 0, pickups = 0, problems = 0;
  const problem = (label, detail) => { problems++; if (problems < 6) check(label, false, detail); };
  for (const { def, settings, mode } of jobs) {
    const m = def.beats_per_bar;
    const dfb = 3;
    const bars = [];
    const N = 3 * cycleBars(def) + 1;
    for (let k = 0; k < N; k++) bars.push(barAt(def, settings, dfb + k, { def_from_bar: dfb, bpm: 70, mode }));
    const strikes = new Set();
    for (let k = 0; k < N; k++) {
      const evs = bars[k];
      for (const e of evs) {
        if (e.beat < -1 - 1e-9 || e.beat >= m - 1e-9) problem("event inside its bar or one beat before", `${k} ${fmt(e)}`);
        if (e.beat < 0) {
          pickups++;
          const at0 = G.chordsInBar(def, dfb + k, { def_from_bar: dfb }).find((c) => c.beat === 0 && c.onset);
          if (!["approach", "early"].includes(e.row) || !at0 || at0.slot !== e.slot) problem("a pickup leads into the chord on its bar's downbeat", `${k} ${fmt(e)} ${JSON.stringify(at0)}`);
        }
        if (e.carry) {
          carries++;
          if (e.beat !== 0) problem("a carry starts on the downbeat", fmt(e));
          const prev = k > 0 ? bars[k - 1].find((p) => p.tie === "next" && p.midi === e.midi && p.voice === e.voice && p.vel === e.vel && p.row === e.row) : null;
          if (!prev) problem("every carry continues a tie of the bar before", `${k} ${fmt(e)}`);
        }
        if (e.tie === "next") {
          ties++;
          const nxt = k + 1 < N ? bars[k + 1].find((c) => c.carry && c.midi === e.midi && c.voice === e.voice && c.vel === e.vel) : true;
          if (!nxt) problem("every tie is carried by the next bar", `${k} ${fmt(e)}`);
        }
        if (!e.carry && e.voice !== "tick") {
          const key = `${(k * m + e.beat).toFixed(6)}|${e.midi}|${e.voice}`;
          if (strikes.has(key)) problem("no note is struck twice", `${k} ${fmt(e)}`);
          strikes.add(key);
        }
      }
    }
  }
  check(`A2 ties and pickups: ${ties} ties, ${carries} carries and ${pickups} pickups all belong to the bar that owns them`, problems === 0 && ties > 100 && pickups > 100, `${problems} problems`);
}

// ======================================================================================= humanising
{
  const settings = S({ groove: "ballad", backing: "full", humanize: 0.6, seed: 90210 });
  let within = true, downbeat = true, topCap = true;
  const E = G.effectiveSettings(GOSPEL, settings);
  for (let n = 0; n < 64; n++) {
    for (const e of barAt(GOSPEL, settings, n, { bpm: 66 })) {
      if (e.carry) continue;
      const rollMax = e.row === "upper" ? 3 * 14 * 0.6 : 0;
      if (e.ms < -12 * 0.6 - 1e-9 || e.ms > 12 * 0.6 + rollMax + 1e-9) within = false;
      if (e.voice === "bass" && e.beat === 0 && e.ms < -4) downbeat = false;
      if (e.row === "upper" && e.midi === Math.max(...barAt(GOSPEL, S({ groove: "ballad" }), n, { bpm: 66 }).filter((x) => x.row === "upper").map((x) => x.midi)) && e.vel > E.L + 2) topCap = false;
    }
  }
  check("humanize timing within +-12h ms (plus the roll)", within);
  check("a downbeat bass is never earlier than -4 ms", downbeat);
  check("the top voice stays at or under L + 2", topCap);
  const a = JSON.stringify(barAt(GOSPEL, settings, 0, { bpm: 66 }).map((e) => [e.ms, e.vel, e.len]));
  const b = JSON.stringify(barAt(GOSPEL, settings, 4, { bpm: 66 }).map((e) => [e.ms, e.vel, e.len]));
  const c = JSON.stringify(barAt(GOSPEL, { ...settings, seed: 90211 }, 0, { bpm: 66 }).map((e) => [e.ms, e.vel, e.len]));
  check("the same loop bar in another pass wobbles differently", a !== b);
  check("another seed wobbles differently", a !== c);
  const late = JSON.stringify(barAt(GOSPEL, settings, 9, { bpm: 66 }));
  for (let n = 0; n < 9; n++) barAt(GOSPEL, settings, n, { bpm: 66 });
  check("a bar's wobble does not depend on which bars were asked for before", late === JSON.stringify(barAt(GOSPEL, settings, 9, { bpm: 66 })));
  const shifted = JSON.stringify(barAt(GOSPEL, settings, 9, { bpm: 66, def_from_bar: 0 }).map((e) => [e.ms, e.vel]));
  const moved = JSON.stringify(G.bar(GOSPEL, settings, 2, 12, { bpm: 66, def_from_bar: 3 }).map((e) => [e.ms, e.vel]));
  check("the seed key is the run bar (the same def bar at another run bar wobbles differently)", shifted !== moved);
}

// ======================================================================================= dropout
{
  const counts = [0, 0, 0, 0];
  let first = false, twoInARow = false;
  for (let seed = 1; seed <= 400; seed++) {
    const settings = S({ groove: "ballad", backing: "comp", dropout: 0.3, seed });
    let prev = false;
    for (let n = 0; n < 32; n++) {
      const d = G.dropoutBar(GOSPEL, settings, n);
      if (d && n === 0) first = true;
      if (d && prev) twoInARow = true;
      if (d) counts[n % 4]++;
      prev = d;
    }
  }
  check("dropout: never the first bar", !first);
  check("dropout: never two bars in a row", !twoInARow);
  check("dropout leans on phrase ends (bar 4 of each 4 rests most)", counts[3] > counts[0] && counts[3] > counts[1] && counts[3] > counts[2] && counts[1] > 0, JSON.stringify(counts));
  check("dropout off: no hole", Array.from({ length: 64 }, (_, n) => G.dropoutBar(GOSPEL, S({ seed: 4 }), n)).every((d) => !d));
  check("dropout after a card swap: never the new def's first bar", !Array.from({ length: 200 }, (_, s) => G.dropoutBar(GOSPEL, S({ dropout: 1, seed: s }), 7, { def_from_bar: 7 })).some(Boolean));

  let holes = 0, ok = true, restruck = true;
  for (const [def, groove] of [[GOSPEL, "ballad"], [LYD, "hold"], [DORIAN, "pulse"], [LAMENT, "hold"]]) {
    for (let seed = 1; seed <= 40; seed++) {
      const on = S({ groove, backing: "full", dropout: 0.5, seed, humanize: 0 });
      const off = { ...on, dropout: 0 };
      for (let n = 0; n < 24; n++) {
        if (!G.dropoutBar(def, on, n)) continue;
        holes++;
        const evs = barAt(def, on, n, { bpm: 60 });
        if (evs.some((e) => e.voice === "upper")) ok = false;
        if (JSON.stringify(evs.filter((e) => e.voice === "bass")) !== JSON.stringify(barAt(def, off, n, { bpm: 60 }).filter((e) => e.voice === "bass"))) ok = false;
        if (n > 0 && barAt(def, on, n - 1, { bpm: 60 }).some((e) => e.voice === "upper" && e.tie)) ok = false;
        const after = n + 1;
        if (after % cycleBars(def) !== 0 && !G.dropoutBar(def, on, after)) {
          const sounding = (evs2) => JSON.stringify([...new Set(evs2.filter((e) => e.voice === "upper" && e.beat === 0).map((e) => e.midi))].sort());
          if (sounding(barAt(def, on, after, { bpm: 60 })) !== sounding(barAt(def, off, after, { bpm: 60 }))) restruck = false;
        }
      }
    }
  }
  check(`dropout bars (${holes}): the bass plays as it would, every other voice rests, nothing rings in`, ok && holes > 20);
  check("after a hole, held voices strike again on the downbeat", restruck);
}

// ======================================================================================= chordsInBar, times, bridge
{
  check("chordsInBar: the slot starting in a bar", JSON.stringify(G.chordsInBar(DROP, 5)) === JSON.stringify([{ slot: 5, beat: 0, beats: 4, onset: true, n: "1maj9", name: "Dmaj9" }]));
  check("chordsInBar: a chord held from the bar before", G.chordsInBar(DROP, 6)[0].onset === false);
  check("chordsInBar: two chords in a bar", G.chordsInBar(fixedDef({ key: "C major", slots: [{ beats: 2, bass: 36, upper: [52], tones: { root: 0 } }, { beats: 2, bass: 41, upper: [57], tones: { root: 5 } }] }), 0).length === 2);
  check("chordsInBar: counting in", G.chordsInBar(LYD, -1).length === 0);

  const segs = TM.addSegment([TM.firstSegment(1893456020000, 66, 1, 1)], 4, 8, { bpm: 72 });
  const timed = G.eventTimes(segs, 4, 8, barAt(LYD, S(), 8, { bpm: 72 }));
  const ap = timed.find((e) => e.row === "approach");
  check("a pickup is timed at the tempo of the bar before", Math.abs(ap.epoch_ms - (TM.tEpoch(segs, 4, 8) - 60000 / 66)) < 1e-6);
  const bs = timed.find((e) => e.row === "bass");
  check("a downbeat is timed on its bar line", Math.abs(bs.epoch_ms - TM.tEpoch(segs, 4, 8)) < 1e-6
    && Math.abs(bs.end_epoch_ms - TM.tEpoch(segs, 4, 8, 2.95)) < 1e-6);

  // run_loop_l1 (J0): the def comes from the run's start line.
  const run = fx("run_loop_l1/run.json");
  const start = readFileSync(here("./fixtures/jam/run_loop_l1/events.jsonl"), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)).find((e) => e.kind === "start");
  const got = answer({ run, defs: { [start.version]: start.def }, flat: true });
  check("bridge run form on run_loop_l1: bars -1..15", got.ok && got.from_bar === -1 && got.to_bar === 16 && got.bars.length === 17, JSON.stringify(got).slice(0, 300));
  if (got.ok) {
    const ticks = got.bars[0].events;
    check("count-in ticks at the start epoch plus k beats", ticks.length === 4 && ticks.every((t, k) => Math.abs(t.epoch_ms - (run.start_epoch_ms + k * 60000 / 66)) < 1e-6));
    const down = got.bars[1].events.find((e) => e.row === "bass");
    check("bar 0's downbeat bass sits on bar0_epoch_ms (plus its humanising)", Math.abs(down.epoch_ms - down.ms - run.bar0_epoch_ms) < 1e-3 && down.ms >= -4);
    check("bars 8+ at 72 bpm", got.bars[9].bpm === 72 && got.bars[8].bpm === 66);
    check("flat notes are the struck notes", got.notes.length === got.bars.reduce((a, b) => a + b.events.filter((e) => !e.carry && e.voice !== "tick").length, 0));
    const mod = G.barOfRun(run, start.def, 5);
    check("barOfRun matches the bridge", JSON.stringify(G.eventTimes(run.segments, 4, 5, mod.events)) === JSON.stringify(got.bars[6].events));
  }

  // A2: the bridge in its own process against the module, 200 bars, with tempo, card and settings changes.
  let segments = [TM.firstSegment(1893456020000, 66, 1, 1)];
  segments = TM.addSegment(segments, 4, 40, { bpm: 80 });
  segments = TM.addSegment(segments, 4, 90, { def_version: 2 });
  segments = TM.addSegment(segments, 4, 150, { bpm: 120 });
  const run200 = { run: "synthetic-200", mode: "loop", beats_per_bar: 4, count_in_bars: 1, segments, stop_bar: null,
    settings: [S({ humanize: 0.6, seed: 90210, dropout: 0.3 }), S({ from_bar: 50, groove: "ballad", backing: "comp", humanize: 0.6, seed: 90210 }),
      S({ from_bar: 120, groove: "pulse", backing: "full", humanize: 1, seed: 7, walk: 0 })] };
  const defs = { 1: LYD, 2: DORIAN };
  const res = spawnSync(process.execPath, [here("../arsenal/groove_bridge.mjs")], {
    input: JSON.stringify({ run: run200, defs, to_bar: 200 }), encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
  let out = null;
  try { out = JSON.parse(res.stdout); } catch (e) { /* reported below */ }
  check("bridge 200 bars exits 0", res.status === 0 && out && out.ok, res.stderr || (res.stdout || "").slice(0, 300));
  if (out && out.ok) {
    let same = out.bars.length === 201;
    for (let n = -1; n < 200 && same; n++) {
      const mine = G.barOfRun(run200, defs, n);
      const want = G.eventTimes(segments, 4, n, mine.events);
      if (JSON.stringify(want) !== JSON.stringify(out.bars[n + 1].events)) { same = false; check(`bridge bar ${n}`, false, JSON.stringify(out.bars[n + 1].events).slice(0, 200)); }
    }
    check("A2 groove_bridge.mjs against the browser module: identical events for 200 bars", same);
    check("the bridge follows the card change at bar 90", out.bars[91].def_version === 2 && out.bars[91].events.some((e) => e.midi === 38 && e.row === "bass"));
  }

  check("bridge: a run without stop_bar needs to_bar", answer({ run: { ...run200 }, defs }).ok === false);
  check("bridge: a bad request names the field", answer({ def: LYD, settings: S({ groove: "polka" }), bars: [0] }).field === "settings.groove");
  check("bridge: plain form", answer({ def: LYD, settings: S(), from_bar: -1, to_bar: 2 }).bars.length === 3);
  const playRun = answer({ run: { mode: "play", beats_per_bar: 4, count_in_bars: 0, segments: [TM.firstSegment(0, 66, 0, 1)], settings: [S()], stop_bar: null }, defs: LYD });
  check("bridge: a play run defaults to one bar past its cycle", playRun.ok && playRun.bars.length === 3 && playRun.bars[2].events.every((e) => e.carry));
  const cli = spawnSync(process.execPath, [here("../arsenal/groove_bridge.mjs")], { input: "not json", encoding: "utf8" });
  check("bridge: unreadable JSON exits 1 with an error", cli.status === 1 && JSON.parse(cli.stdout).ok === false);
}

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
