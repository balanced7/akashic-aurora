// Node tests for the Studio practice library (arsenal/web/piano/practice/library.js). Zero dependencies:
//   node tests/piano_practice_library.test.mjs
// Sections: the menu (ids unique, every family/group/exercise reference resolves, menu order = the exercise order); the
// exercise shape and wording; hands (ranges, spans an open hand reaches, hands never cross); every chord read by the page
// (piano.js's own THEORY block, the chord reader and spellForKey, sliced from the page as tests/piano_keysig.test.mjs does,
// then nashville.js): its written name and number are what the page shows for those notes in the exercise key; and every
// transposition -5..+6 through practice/player.js (numbers constant, names respelled as the page reads the moved notes, no
// triple accidentals, no double accidental on a root or bass, the bass line and right-hand shape unchanged).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as NV from "../arsenal/web/piano/nashville.js";
import * as SP from "../arsenal/web/piano/spell.js";
import { installReader, parseSuffix } from "../arsenal/web/piano/chordread.js";
import { FAMILIES, EXERCISES } from "../arsenal/web/piano/practice/library.js";
import { RANGE, viewOf, transposeChoices, transposeKey, libraryOrder } from "../arsenal/web/piano/practice/player.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const mod = (a, n) => ((a % n) + n) % n;
const SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const noteName = (m) => SHARP[mod(m, 12)] + (Math.floor(m / 12) - 1);
const notesText = (list) => list.map(noteName).join(" ");

// ======================================================================================================= the menu ==
{
  const exIds = EXERCISES.map((e) => e.id), famIds = FAMILIES.map((f) => f.id), groupIds = FAMILIES.flatMap((f) => f.groups.map((g) => g.id));
  check("exercise ids are unique", new Set(exIds).size === exIds.length, exIds.join(" "));
  check("family ids are unique", new Set(famIds).size === famIds.length, famIds.join(" "));
  check("group ids are unique across the library", new Set(groupIds).size === groupIds.length, groupIds.join(" "));
  const idRe = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  check("every id is lower-case words joined by hyphens (safe in a cue id)", [...exIds, ...famIds, ...groupIds].every((id) => idRe.test(id)),
    [...exIds, ...famIds, ...groupIds].filter((id) => !idRe.test(id)).join(" "));
  check("the library has families, groups and exercises", FAMILIES.length >= 1 && groupIds.length >= FAMILIES.length && EXERCISES.length >= groupIds.length,
    `${FAMILIES.length} families, ${groupIds.length} groups, ${EXERCISES.length} exercises`);
  const byId = new Map(EXERCISES.map((e) => [e.id, e]));
  for (const f of FAMILIES) {
    check(`family ${f.id} has a title, a blurb and groups`, typeof f.title === "string" && f.title.length > 0 && typeof f.blurb === "string" && f.blurb.length > 0
      && Array.isArray(f.groups) && f.groups.length > 0);
    for (const g of f.groups) {
      check(`group ${f.id}/${g.id} has a title, a blurb and exercises`, typeof g.title === "string" && g.title.length > 0 && typeof g.blurb === "string"
        && g.blurb.length > 0 && Array.isArray(g.exercises) && g.exercises.length > 0);
      for (const x of g.exercises) {
        const e = byId.get(x);
        check(`${f.id}/${g.id} lists ${x}, which exists`, !!e);
        if (e) check(`${x} names the family and group that list it`, e.family === f.id && e.group === g.id, `${e.family}/${e.group}`);
      }
    }
  }
  for (const e of EXERCISES) {
    const f = FAMILIES.find((x) => x.id === e.family);
    check(`${e.id}: its family ${e.family} and group ${e.group} exist`, !!f && f.groups.some((g) => g.id === e.group));
  }
  const listed = libraryOrder(FAMILIES);
  check("every exercise is listed exactly once", listed.length === EXERCISES.length && new Set(listed).size === listed.length
    && EXERCISES.every((e) => listed.includes(e.id)), `${listed.length} listed, ${EXERCISES.length} exercises`);
  check("EXERCISES are stored in menu order (the order auto-advance walks)", listed.join() === exIds.join());
  report.push(`menu: ${FAMILIES.length} families, ${groupIds.length} groups, ${EXERCISES.length} exercises, ${EXERCISES.reduce((s, e) => s + e.chords.length, 0)} chords`);
}

// ================================================================================== the exercise shape and wording ==
const EX_KEYS = ["id", "title", "family", "group", "level", "key", "minor", "bpm", "beatsPerBar", "chords", "concept", "listenFor", "leftHand", "variation", "tags"];
const CH_KEYS = ["name", "number", "bass", "upper", "beats", "pedal"];
const LEVELS = new Set(["foundation", "build", "stretch"]);
// Timeless, generic wording: nothing about a particular day, a take or a clock time.
const TIME_BOUND = /\b(tonight|today|yesterday|this morning|last night|last time|you played|recorded|recording|session|sessions)\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b/i;
const levels = { foundation: 0, build: 0, stretch: 0 };
for (const e of EXERCISES) {
  check(`${e.id}: fields ${EX_KEYS.join(", ")}`, EX_KEYS.every((k) => k in e) && Object.keys(e).every((k) => EX_KEYS.includes(k)), Object.keys(e).join(","));
  check(`${e.id}: level is foundation, build or stretch`, LEVELS.has(e.level), e.level);
  if (LEVELS.has(e.level)) levels[e.level]++;
  const K = NV.parseKey(e.key);
  check(`${e.id}: key ${e.key} is a key name nashville.js reads back unchanged`, !!K && K.name === e.key);
  check(`${e.id}: minor numbering is tonic`, e.minor === "tonic", e.minor);
  check(`${e.id}: bpm ${e.bpm} is a whole tempo 40..160; beatsPerBar ${e.beatsPerBar} a whole number 2..12`, Number.isInteger(e.bpm) && e.bpm >= 40 && e.bpm <= 160
    && Number.isInteger(e.beatsPerBar) && e.beatsPerBar >= 2 && e.beatsPerBar <= 12);
  check(`${e.id}: at least two chords`, Array.isArray(e.chords) && e.chords.length >= 2);
  const beats = e.chords.reduce((s, c) => s + c.beats, 0);
  check(`${e.id}: whole bars (${beats} beats)`, beats % e.beatsPerBar === 0);
  for (const f of ["title", "concept", "listenFor", "leftHand", "variation"]) {
    check(`${e.id}: ${f} is plain text`, typeof e[f] === "string" && e[f].trim().length >= (f === "title" ? 3 : 40), String(e[f]).slice(0, 40));
    check(`${e.id}: ${f} is timeless (no day, take or clock time)`, !TIME_BOUND.test(e[f]), (String(e[f]).match(TIME_BOUND) || [""])[0]);
  }
  check(`${e.id}: leftHand says where to change the pedal`, /pedal/i.test(e.leftHand));
  check(`${e.id}: tags are words`, Array.isArray(e.tags) && e.tags.length > 0 && e.tags.every((t) => typeof t === "string" && t.length > 0));
  e.chords.forEach((c, i) => {
    const w = `${e.id} #${i + 1} ${c.name}`;
    check(`${w}: fields ${CH_KEYS.join(", ")}`, CH_KEYS.every((k) => k in c) && Object.keys(c).every((k) => CH_KEYS.includes(k)));
    check(`${w}: beats is a whole number of beats`, Number.isInteger(c.beats) && c.beats > 0, String(c.beats));
    check(`${w}: pedal is change or hold`, c.pedal === "change" || c.pedal === "hold", c.pedal);
    if (i === 0) check(`${w}: the first chord takes a fresh pedal`, c.pedal === "change");
    const f = NV.formatNumber(c.number);
    check(`${w}: its number ${c.number} formats for display without the ^ joiner`, !!f && typeof f.display === "string" && f.display.length > 0 && !f.display.includes("^"));
  });
}
check("levels: some foundation exercises, and every level used", levels.foundation > 0 && levels.build > 0 && levels.stretch > 0, JSON.stringify(levels));
report.push(`levels: ${JSON.stringify(levels)}`);

// ========================================================================================================== hands ==
// Bass inside E1-E3, right hand inside A2-C6, each hand within an octave (an open hand reaches it with no roll), notes
// bottom-up and whole MIDI numbers the cue player accepts (21..108), no note in both hands, the hands never cross.
function handsProblems(bass, upper) {
  const out = [];
  const all = [...bass, ...upper];
  if (!bass.length || !upper.length) out.push("an empty hand");
  if (all.some((m) => !Number.isInteger(m) || m < 21 || m > 108)) out.push("a note outside MIDI 21..108");
  if (bass.some((m) => m < RANGE.bassLo || m > RANGE.bassHi)) out.push(`bass outside E1-E3 (${notesText(bass)})`);
  if (upper.some((m) => m < RANGE.upperLo || m > RANGE.upperHi)) out.push(`right hand outside A2-C6 (${notesText(upper)})`);
  if (bass.length && Math.max(...bass) - Math.min(...bass) > 12) out.push("left hand wider than an octave");
  if (upper.length && Math.max(...upper) - Math.min(...upper) > 12) out.push("right hand wider than an octave");
  const sorted = (l) => l.every((m, k) => k === 0 || m > l[k - 1]);
  if (!sorted(bass) || !sorted(upper)) out.push("notes not bottom-up (or repeated)");
  if (new Set(all).size !== all.length) out.push("a note in both hands");
  if (bass.length && upper.length && Math.max(...bass) >= Math.min(...upper)) out.push("hands cross");
  return out;
}
for (const e of EXERCISES) {
  e.chords.forEach((c, i) => {
    const p = handsProblems(c.bass, c.upper);
    check(`${e.id} #${i + 1} ${c.name}: hands in range, reachable, not crossing`, p.length === 0, p.join("; "));
  });
}

// ========================================================================================= every chord, read by the page ==
const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
const THEORY_A = pianoSrc.indexOf("// ===== THEORY BEGIN"), THEORY_B = pianoSrc.indexOf("// ===== THEORY END");
check("piano.js THEORY markers present", THEORY_A >= 0 && THEORY_B > THEORY_A);
// A top-level declaration's source, by name (braces matched outside strings, template literals and comments).
function declSource(name) {
  const m = new RegExp(`^(?:function\\s+${name}\\s*\\(|(?:const|let)\\s+${name}\\s*=)`, "m").exec(pianoSrc);
  if (!m) return null;
  const s = pianoSrc, isFn = m[0].startsWith("function");
  let depth = 0, body = false;
  for (let i = m.index; i < s.length; i++) {
    const ch = s[i];
    if (ch === "/" && s[i + 1] === "/") { i = s.indexOf("\n", i); continue; }
    if (ch === "/" && s[i + 1] === "*") { i = s.indexOf("*/", i + 2) + 1; continue; }
    if (ch === "'" || ch === '"' || ch === "`") { for (i++; i < s.length && s[i] !== ch; i++) if (s[i] === "\\") i++; continue; }
    if (ch === "{" || ch === "(" || ch === "[") { depth++; if (ch === "{") body = true; }
    else if (ch === "}" || ch === ")" || ch === "]") { depth--; if (isFn && body && depth === 0 && ch === "}") return s.slice(m.index, i + 1); }
    else if (ch === ";" && depth === 0 && !isFn) return s.slice(m.index, i + 1);
  }
  return null;
}
const spellForKeySrc = declSource("spellForKey");
check("piano.js declares spellForKey", !!spellForKeySrc);
const Theory = new Function(pianoSrc.slice(THEORY_A, THEORY_B) + "\nreturn Theory;")();
installReader(Theory, NV);  // the page's default reader (piano.js:291-303)
const theoryUi = { minor: "tonic" };
const spellForKey = new Function("Theory", "theoryUi", "keyContext", "spellChord", "spellNote", "parseSuffix",
  `${spellForKeySrc}\nreturn spellForKey;`)(Theory, theoryUi, SP.keyContext, SP.spellChord, SP.spellNote, parseSuffix);

// The page's reading of what sounds, in a trusted key, as detectSounding + readSounding + numberFor do it
// (piano.js:2691-2707, 2444). prev: the reader's previous-root prior (a pitch class) or null.
function pageRead(midis, keyName, prev = null) {
  const K = NV.parseKey(keyName);
  const info = Theory.detect([...midis], K.bias, { key: K.name, prev: prev === null ? null : { root: prev } });
  if (info && Array.isArray(info.readings)) info.spelledIn = K.name;
  const shown = spellForKey(info, K);
  const n = shown ? NV.nashville(shown, K, { minor: "tonic" }) : null;
  return { name: shown ? shown.name : null, kind: shown ? shown.kind : null, root: shown && shown.root ? Theory.pcOf(shown.root) : null,
           number: n ? n.text : null, notes: shown && Array.isArray(shown.notes) ? shown.notes : [] };
}
// The page's prior over a run of chords, as detectSounding keeps it: prev is the root before the current one, and a chord
// is read on every frame while it sounds, so the reading that stays is the one with the root before it as the prior.
// Played twice through (a loop), the second pass is the settled reading of every chord.
function settledReadings(chordNotes, keyName) {
  const rc = { root: null, prev: null };
  const out = [];
  for (let passNo = 0; passNo < 2; passNo++) {
    chordNotes.forEach((ms, i) => {
      let r = null;
      for (let frame = 0; frame < 2; frame++) {
        r = pageRead(ms, keyName, rc.prev);
        if (r.kind === "chord" && r.root !== null && r.root !== rc.root) { rc.prev = rc.root; rc.root = r.root; }
      }
      if (passNo === 1) out[i] = r;
    });
  }
  return out;
}

let readerChords = 0;
for (const e of EXERCISES) {
  const notes = e.chords.map((c) => [...c.bass, ...c.upper]);
  const settled = settledReadings(notes, e.key);
  e.chords.forEach((c, i) => {
    const w = `${e.id} #${i + 1} (${notesText(notes[i])}) in ${e.key}`;
    const cold = pageRead(notes[i], e.key, null);
    readerChords++;
    check(`${w}: the page names it ${c.name}`, cold.kind === "chord" && cold.name === c.name, `reader says ${cold.name}`);
    check(`${w}: the page numbers it ${c.number}`, cold.number === c.number, `reader says ${cold.number}`);
    check(`${w}: played in order (the reader's prior), still ${c.name} = ${c.number}`, settled[i].name === c.name && settled[i].number === c.number,
      `${settled[i].name} = ${settled[i].number}`);
    const byName = NV.nashvilleFromName(c.name, e.key, { minor: "tonic" });
    check(`${w}: nashville.js numbers the name ${c.name} as ${c.number}`, !!byName && byName.text === c.number, byName ? byName.text : "unreadable");
  });
}
report.push(`reader: ${readerChords} chords read by the page in their exercise keys`);

// ======================================================================================== transposition -5..+6 ==
const tripleName = /#{3}|b{3}/;
let shifts = 0, shiftedChords = 0, mergedNotes = 0;
const samples = [];
for (const e of EXERCISES) {
  const choices = transposeChoices(e);
  check(`${e.id}: the key picker offers 12 different keys, its own included`, choices.length === 12 && new Set(choices.map((c) => c.key)).size === 12
    && choices.some((c) => c.semis === 0 && c.key === e.key), choices.map((c) => c.key).join(", "));
  const origLine = e.chords.map((c) => c.bass[0]);
  for (let t = -5; t <= 6; t++) {
    if (t === 0) continue;
    shifts++;
    const v = viewOf(e, { transpose: t });
    const w0 = `${e.id} ${t > 0 ? "+" : ""}${t} (${v.key})`;
    check(`${w0}: the key is the exercise key moved by ${t}`, v.key === transposeKey(e.key, t) && NV.parseKey(v.key).tonic === mod(NV.parseKey(e.key).tonic + t, 12)
      && NV.parseKey(v.key).mode === NV.parseKey(e.key).mode, v.key);
    const line = v.chords.map((c) => c.bass[0]);
    check(`${w0}: the bass line moves as it was written`, line.every((m, i) => i === 0 || m - line[i - 1] === origLine[i] - origLine[i - 1]),
      `${notesText(origLine)} -> ${notesText(line)}`);
    check(`${w0}: the right hand keeps its shape (one octave move for the whole exercise)`,
      v.chords.every((c, i) => c.upper.join() === e.chords[i].upper.map((m) => m + v.upperShift).join()), `upper shift ${v.upperShift}`);
    check(`${w0}: every bass note is the written note moved by ${t}, give or take octaves`,
      v.chords.every((c, i) => c.bass.every((m) => e.chords[i].bass.some((o) => mod(m - o - t, 12) === 0))
        && e.chords[i].bass.every((o) => c.bass.some((m) => mod(m - o - t, 12) === 0))));
    mergedNotes += v.merged;
    const settled = settledReadings(v.chords.map((c) => [...c.bass, ...c.upper]), v.key);
    const bad = [];
    v.chords.forEach((c, i) => {
      shiftedChords++;
      const orig = e.chords[i];
      const where = `#${i + 1} ${orig.name} -> ${c.name}`;
      const hp = handsProblems(c.bass, c.upper);
      if (hp.length) bad.push(`${where}: ${hp.join("; ")}`);
      if (c.number !== orig.number) bad.push(`${where}: the view's number ${c.number} is not ${orig.number}`);
      const byName = NV.nashvilleFromName(c.name, v.key, { minor: "tonic" });
      if (!byName || byName.text !== orig.number) bad.push(`${where}: nashville.js numbers ${c.name} in ${v.key} as ${byName && byName.text}, not ${orig.number}`);
      const parsed = NV.parseChord(c.name);
      if (!parsed || parsed.kind !== "chord") bad.push(`${where}: unreadable name`);
      else {
        if (Math.abs(parsed.root.acc) >= 2) bad.push(`${where}: a double accidental on the root`);
        if (parsed.bass && Math.abs(parsed.bass.acc) >= 2) bad.push(`${where}: a double accidental on the bass`);
        if (SP.pcOf(parsed.root) !== mod(SP.pcOf(NV.parseChord(orig.name).root) + t, 12)) bad.push(`${where}: the root did not move by ${t}`);
      }
      if (tripleName.test(c.name)) bad.push(`${where}: a triple accidental in the name`);
      const r = pageRead([...c.bass, ...c.upper], v.key, null);
      if (r.number !== orig.number) bad.push(`${where}: the page numbers the moved notes ${r.number} (${r.name})`);
      if (r.name !== c.name) bad.push(`${where}: the page names the moved notes ${r.name}`);
      if (r.notes.some((n) => Math.abs(n.acc) >= 3)) bad.push(`${where}: a triple accidental among the spelled notes`);
      if (settled[i].name !== c.name || settled[i].number !== orig.number) bad.push(`${where}: played in order the page reads ${settled[i].name} = ${settled[i].number}`);
    });
    check(`${w0}: numbers constant, names as the page reads the moved notes, no triple or root/bass double accidental, hands in range`,
      bad.length === 0, bad.slice(0, 4).join(" | "));
    if (e.id === "stepwise-bass-g" && (t === -1 || t === 2)) samples.push(`${v.key}: ${v.chords.map((c) => c.name).join(" ")}`);
  }
}
report.push(`transposition: ${shifts} shifts, ${shiftedChords} chords checked; ${mergedNotes} octave doublings merged by folding`);
for (const s of samples) report.push(`  ${s}`);

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
