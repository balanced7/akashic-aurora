// Node tests for arsenal/web/piano/chordread.js, the next-gen chord reader (research/in-flight/piano-theory-nextgen-2026-09-14/
// theory-nextgen-spec.md, TN1), scored against the TN0 corpus in tests/fixtures/theory/. Zero dependencies:
//   node tests/theory_chordread.test.mjs                  the corpus contracts, then the reader's receipts (NG1, NG3 lab table)
//   node tests/theory_chordread.test.mjs --contracts      the TN0 corpus alone (TN0 exit): every fixture against its schema,
//                                                          internal consistency, the lexicon guard on its own strings
//   node tests/theory_chordread.test.mjs --reader <file>  score another module with chordread.js's exports (a scratch lab)
// The corpus is frozen after TN0; changes go through the conductor. Names match by identity (root pitch class, suffix
// exactly, bass pitch class, read by nashville.js parseChord), so enharmonic spellings of one chord match. The reader's
// results are checked against tests/fixtures/theory/contracts.schema.json ($defs ReadResult, Reading, AlsoResult,
// DetectInfo, ParsedSuffix). After the corpus receipts come the TN1 reader invariants: parseSuffix against nashville.js's
// TONE_STEPS, FAMILY and DOMINANT; every reading's name parsing back to its notes; A1, A2, A4 and A7 over every fixture
// result; A2 and the augmented duplicate over every chord shape; spellings the page keeps (E#, Cb); inputs a live window
// hands in (a bass outside the notes, weights that are not numbers); detect()'s info shape and D12. The band ceiling and
// canvas ALSO spec 2.6 gives every case are checked on the cases that are not strict too. Real-window receipts (NG2,
// the rest of NG3) replay S1-S6 read only, in a scratch lane (theory-nextgen/tn1/static_lane.mjs), counts only.
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";
import * as NV from "../arsenal/web/piano/nashville.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const FX = here("./fixtures/theory/");
const argv = process.argv.slice(2);
const contractsOnly = argv.includes("--contracts");
const readerArg = argv.indexOf("--reader") >= 0 ? argv[argv.indexOf("--reader") + 1] : null;
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const load = (name) => JSON.parse(readFileSync(FX + name, "utf8"));
const mod = (a, n) => ((a % n) + n) % n;
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
const pcOfSp = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);
const pcOfNote = (text) => { const c = NV.parseChord(text, "note"); return c ? pcOfSp(c.root) : null; };
function midiOf(tok) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(tok);
  if (!m) return null;
  return (Number(m[3]) + 1) * 12 + LETTER_PC["CDEFGAB".indexOf(m[1])] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0);
}
const midis = (text) => text.trim().split(/\s+/).map(midiOf);
function ident(name) {
  const c = name == null ? null : NV.parseChord(String(name));
  if (!c || c.kind !== "chord") return null;
  return `${pcOfSp(c.root)}|${c.suffix}|${c.bass ? pcOfSp(c.bass) : ""}`;
}
const identOf = (r) => `${r.root}|${r.suffix}|${r.bass ?? ""}`;
const plainText = (s) => String(s).replace(/♭/g, "b").replace(/♯/g, "#");
function numberOf(name, key, kind = null) {
  if (!name || !key) return null;
  const r = NV.nashvilleFromName(plainText(name).replace("(no3)", ""), key, kind ? { kind } : {});
  return r ? r.text : null;
}
const sameSet = (a, b) => a.length === b.length && [...a].sort().join() === [...b].sort().join();

// ------------------------------------------------------------- a small JSON Schema reader (the keywords used) --
const schemaDocs = new Map();
const schemaDoc = (file) => { if (!schemaDocs.has(file)) schemaDocs.set(file, load(file)); return schemaDocs.get(file); };
const typeOk = (t, v) => t === "null" ? v === null : t === "array" ? Array.isArray(v) : t === "object" ? v !== null && typeof v === "object" && !Array.isArray(v)
  : t === "integer" ? Number.isInteger(v) : t === "number" ? typeof v === "number" && Number.isFinite(v) : typeof v === t;
function validate(schema, value, file, path = "$", errors = []) {
  if (schema === true || schema == null) return errors;
  if (schema.$ref) {
    const [f, frag] = schema.$ref.split("#");
    const target = f || file;
    let node = schemaDoc(target);
    for (const part of (frag || "").split("/").filter(Boolean)) node = node[part];
    if (!node) { errors.push(`${path}: unresolved ${schema.$ref}`); return errors; }
    validate(node, value, target, path, errors);
  }
  if (schema.allOf) for (const s of schema.allOf) validate(s, value, file, path, errors);
  if (schema.anyOf && !schema.anyOf.some((s) => validate(s, value, file, path, []).length === 0)) {
    const near = schema.anyOf.map((s) => validate(s, value, file, path, [])).sort((a, b) => a.length - b.length)[0];
    errors.push(`${path}: matches none of anyOf (${near[0]})`);
  }
  if (schema.type && ![].concat(schema.type).some((t) => typeOk(t, value))) {
    errors.push(`${path}: want ${[].concat(schema.type).join("|")}, got ${JSON.stringify(value)?.slice(0, 60)}`);
    return errors;
  }
  if ("const" in schema && JSON.stringify(schema.const) !== JSON.stringify(value)) errors.push(`${path}: want ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.some((e) => JSON.stringify(e) === JSON.stringify(value))) errors.push(`${path}: ${JSON.stringify(value)} not in ${JSON.stringify(schema.enum)}`);
  if (typeof value === "string") {
    if (schema.minLength != null && value.length < schema.minLength) errors.push(`${path}: shorter than ${schema.minLength}`);
    if (schema.pattern && !new RegExp(schema.pattern, "u").test(value)) errors.push(`${path}: ${JSON.stringify(value)} does not match ${schema.pattern}`);
  }
  if (typeof value === "number") {
    if (schema.minimum != null && value < schema.minimum) errors.push(`${path}: below ${schema.minimum}`);
    if (schema.maximum != null && value > schema.maximum) errors.push(`${path}: above ${schema.maximum}`);
    if (schema.exclusiveMinimum != null && value <= schema.exclusiveMinimum) errors.push(`${path}: not above ${schema.exclusiveMinimum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems != null && value.length < schema.minItems) errors.push(`${path}: ${value.length} items, want at least ${schema.minItems}`);
    if (schema.maxItems != null && value.length > schema.maxItems) errors.push(`${path}: ${value.length} items, want at most ${schema.maxItems}`);
    if (schema.items) value.forEach((v, i) => validate(schema.items, v, file, `${path}[${i}]`, errors));
  }
  if (typeOk("object", value)) {
    for (const k of schema.required || []) if (!(k in value)) errors.push(`${path}: missing ${k}`);
    for (const [k, v] of Object.entries(value)) {
      if (schema.properties && k in schema.properties) validate(schema.properties[k], v, file, `${path}.${k}`, errors);
      else if (schema.additionalProperties === false) errors.push(`${path}: unexpected ${k}`);
      else if (typeof schema.additionalProperties === "object") validate(schema.additionalProperties, v, file, `${path}.${k}`, errors);
    }
  }
  return errors;
}
const schemaCheck = (label, value, schemaFile, def = null) => {
  const errs = validate(def ? { $ref: `${schemaFile}#/$defs/${def}` } : schemaDoc(schemaFile), value, schemaFile);
  check(label, errs.length === 0, errs.slice(0, 5).join("; ") + (errs.length > 5 ? ` (+${errs.length - 5})` : ""));
  return errs.length === 0;
};

// ====================================================================================== the TN0 corpus contracts ==
const chordFx = load("chord_readings_cases.json");
const scaleFx = load("scale_cases.json");
const fnFx = load("function_cases.json");
const lex = load("lexicon.json");
const sessions = readdirSync(FX + "window_sessions").filter((f) => f.endsWith(".json")).sort().map((f) => ({ f, doc: load(`window_sessions/${f}`) }));
schemaCheck("chord_readings_cases.json against its schema", chordFx, "chord_readings_cases.schema.json");
schemaCheck("scale_cases.json against its schema", scaleFx, "scale_cases.schema.json");
schemaCheck("function_cases.json against its schema", fnFx, "function_cases.schema.json");
schemaCheck("lexicon.json against its schema", lex, "lexicon.schema.json");
for (const { f, doc } of sessions) schemaCheck(`window_sessions/${f} against its schema`, doc, "window_session.schema.json");
check("contracts.schema.json defines the frozen shapes", ["Reading", "ReadResult", "AlsoResult", "DetectInfo", "ParsedSuffix", "ScaleResult", "CentreResult",
  "FunctionResult", "HarmonyTick", "NoteEvent", "TheoryFrame"].every((d) => d in schemaDoc("contracts.schema.json").$defs));

// ---------------------------------------------------------------------------------------------- chord cases --
const cases = chordFx.cases;
const byId = new Map(cases.map((c) => [c.id, c]));
check("chord case ids are unique", byId.size === cases.length);
check("at least 180 chord cases", cases.length >= 180, String(cases.length));
for (const c of cases) {
  const ms = midis(c.notes);
  check(`${c.id} notes are keys of the piano`, ms.every((m) => m != null && m >= 21 && m <= 108), c.notes);
  check(`${c.id} key reads`, c.key === null || !!NV.parseKey(c.key), c.key);
  check(`${c.id} prev reads`, c.prev === null || ident(c.prev) !== null, c.prev);
  const e = c.expect;
  for (const n of [e.name, ...(e.accept || []), e.also, e.close, ...(e.include || []).map((x) => x.name), ...(e.exclude || []).map((x) => x.name)]) {
    if (n != null) check(`${c.id} names read as chords`, ident(n) !== null, n);
  }
  if (e.number !== undefined && e.name) check(`${c.id} number is the name's in the key`, numberOf(e.name, c.key) === e.number, `${numberOf(e.name, c.key)} want ${e.number}`);
}
const group = (g) => cases.filter((c) => c.group === g);
const proto = group("prototype");
const protoSet = (s) => proto.filter((c) => c.set === s);
check("prototype: the 73 voicings of design-engine 5", proto.length === 73, String(proto.length));
check("prototype: 71 with a name", proto.filter((c) => c.expect.name).length === 71);
for (const [s, n] of [["plain", 32], ["daniel", 24], ["dominant", 10]]) check(`prototype ${s}: ${n} named`, protoSet(s).filter((c) => c.expect.name).length === n);
check("prototype voicing: 5 named, 2 tag-only", protoSet("voicing").filter((c) => c.expect.name).length === 5 && protoSet("voicing").length === 7);
check("prototype: 6 wanted voicing tags", proto.reduce((a, c) => a + (c.expect.tags || []).length, 0) === 6);
check("D6: no accept list names a no-3rd shape 11", !cases.some((c) => ["C/D", "F/G"].includes(c.expect.name) && (c.expect.accept || []).some((a) => /11$/.test(a))));
// spec 2.6: each case carries an expected band ceiling and an expected canvas ALSO (written by hand)
const HAND = ["prototype", "transposed", "defect", "chip"];
const handMiss = cases.filter((c) => HAND.includes(c.group) && c.expect.name && (!(c.expect.band_max || c.expect.band) || c.expect.also === undefined));
check("spec 2.6: every named prototype, transposed, defect and chip case writes a band ceiling and a canvas ALSO", handMiss.length === 0, handMiss.slice(0, 6).map((c) => c.id).join(", "));
check("spec 2.6: the tag-only quartal voicing writes a band ceiling", proto.some((c) => c.expect.name === null && (c.expect.tags || []).includes("quartal") && c.expect.band_max === "leaning"));
for (const c of cases.filter((x) => x.expect.also && x.expect.name)) {
  const [r1, , b1] = ident(c.expect.also).split("|"), [r2, , b2] = ident(c.expect.name).split("|");
  check(`${c.id} ALSO ${c.expect.also} is on another root or bass than ${c.expect.name}`, r1 !== r2 || b1 !== b2);
}
// transpositions: Daniel's 24 in every major key
const transposed = group("transposed");
check("transposed: Daniel's 24 in 11 more keys", transposed.length === 24 * 11, String(transposed.length));
for (const orig of protoSet("daniel")) {
  const mine = transposed.filter((c) => c.of === orig.id);
  const keys = new Set(mine.map((c) => NV.parseKey(c.key).tonic).concat([NV.parseKey(orig.key).tonic]));
  check(`${orig.id} is in all 12 keys`, mine.length === 11 && keys.size === 12);
  const o = midis(orig.notes);
  const moveId = (id, s) => { const [r, sfx, b] = id.split("|"); return `${mod(Number(r) + s, 12)}|${sfx}|${b === "" ? "" : mod(Number(b) + s, 12)}`; };
  for (const c of mine) {
    const m = midis(c.notes);
    check(`${c.id} notes are ${orig.id}'s moved ${c.shift}`, m.length === o.length && m.every((x, i) => x === o[i] + c.shift));
    check(`${c.id} key moved ${c.shift}`, NV.parseKey(c.key).tonic === mod(NV.parseKey(orig.key).tonic + c.shift, 12));
    check(`${c.id} names, band ceiling and ALSO moved ${c.shift}`, ident(c.expect.name) === moveId(ident(orig.expect.name), c.shift)
      && sameSet(c.expect.accept.map(ident), orig.expect.accept.map((a) => moveId(ident(a), c.shift)))
      && (orig.prev === null ? c.prev === null : ident(c.prev) === moveId(ident(orig.prev), c.shift))
      && c.expect.band_max === orig.expect.band_max
      && (orig.expect.also === null ? c.expect.also === null : ident(c.expect.also) === moveId(ident(orig.expect.also), c.shift)));
    check(`${c.id} number equals ${orig.id}'s`, c.expect.number === orig.expect.number, `${c.expect.number} want ${orig.expect.number}`);
  }
}
check("also-lab: spec 2.1's eight voicings, each with a band and a canvas ALSO", group("also-lab").length === 8
  && group("also-lab").every((c) => c.expect.band && c.expect.also !== undefined && c.expect.strict));
const DEFECTS = ["d-a1-no3-eb", "d-a1-no3-f", "d-a1-no3-nokey", "d-a1-no3-9-eb", "d-a3-cluster", "d-a3-cadd9", "d-a2-gospel", "d-a4-no-g11"];
check("defect: A1-A4 voicings present and strict", DEFECTS.every((id) => byId.get(id)?.group === "defect" && byId.get(id).expect.strict));
check("chip: Dbmaj9/F, Ab9/Gb and Gdim7 present and strict", ["Dbmaj9/F", "Ab9/Gb", "Gdim7"].every((n) => group("chip").some((c) => c.expect.name === n && c.expect.strict)));
const CARDS = ["lydian-four", "gospel-five-over-four", "one-note-apart", "blooming-chord", "half-step-slide", "lament-bass", "minor-third-drop", "borrowed-four-minor",
  "borrowed-b6-b7-home", "float-or-pull", "lush-two-five-one", "sunrise-ending", "db-opening", "held-sus-five", "open-ending-b7", "white-keys", "dorian-vamp"];
check("seed: every one of the 17 cards has its slots", CARDS.every((id) => group("seed").some((c) => c.card === id)));

// ---------------------------------------------------------------------------------------------- scale cases --
const scaleSets = new Map();
for (const s of scaleFx.scales) {
  check(`scale ${s.name} (${s.family}) intervals rise from 0`, s.intervals[0] === 0 && s.intervals.every((x, i) => i === 0 || x > s.intervals[i - 1]));
  if (!scaleSets.has(s.name)) scaleSets.set(s.name, []);
  scaleSets.get(s.name).push(s.intervals);
}
for (const name of Object.keys(scaleFx.gate)) check(`gate ${name} names a scale`, scaleSets.has(name));
const gateOpen = (name, rootPc, heard) => {
  const g = scaleFx.gate[name];
  return !!g && g.character.every((x) => heard.has(mod(rootPc + x, 12)));
};
const scaleIds = new Set(scaleFx.cases.map((c) => c.id));
check("scale case ids are unique", scaleIds.size === scaleFx.cases.length);
check("at least 20 scale cases", scaleFx.cases.length >= 20);
for (const c of scaleFx.cases.filter((x) => x.kind === "rank")) {
  const root = pcOfNote(c.root), chord = c.chord_notes.map(pcOfNote);
  const heard = new Set([...chord, ...Object.entries(c.melody).filter(([, w]) => w > 0.02).map(([n]) => pcOfNote(n)), ...c.recent.map(pcOfNote)]);
  const fits = (scaleSets.get(c.expect.top) || []).find((iv) => chord.every((p) => iv.includes(mod(p - root, 12))));
  check(`${c.id} the chord's notes are on ${c.expect.top}`, !!fits, c.label);
  if (!fits) continue;
  const implied = fits.map((x) => mod(root + x, 12)).filter((p) => !heard.has(p));
  check(`${c.id} implied tones`, sameSet(implied, c.expect.implied.map(pcOfNote)), `${implied} want ${c.expect.implied}`);
  check(`${c.id} sounded is the naming gate`, gateOpen(c.expect.top, root, heard) === c.expect.sounded);
  check(`${c.id} root spelled in the key`, pcOfNote(c.expect.root_name) === root && (c.key === null || (() => {
    const sp = NV.parseChord(c.expect.root_name, "note").root, s = NV.spellInKey(sp, c.key);
    return s.letter === sp.letter && s.acc === sp.acc;
  })()), c.expect.root_name);
  if (c.expect.canvas) check(`${c.id} a canvas caption needs a key and an open gate`, c.key !== null && c.expect.sounded);
}
check("scale: the 11 prototype cases", scaleFx.cases.filter((c) => c.group === "prototype-11").length === 11);
check("scale: an implied-only case with the gate closed", scaleFx.cases.some((c) => c.kind === "rank" && c.chord === "Abmaj9" && c.key === "Eb major" && !c.expect.sounded && c.expect.canvas === false));
for (const c of scaleFx.cases.filter((x) => x.kind === "gate")) {
  const heard = new Set([...c.heard, ...c.recent].map(pcOfNote));
  check(`${c.id} gate ${c.scale} on ${c.root}`, gateOpen(c.scale, pcOfNote(c.root), heard) === c.expect.gate);
}
const centres = scaleFx.cases.filter((x) => x.kind === "centre");
for (const c of centres) {
  check(`${c.id} chord roots and families read`, c.chords.every((x) => ident(x.chord)?.split("|")[0] === String(pcOfNote(x.root))));
  if (c.expect.centre) check(`${c.id} centre is a mode name`, scaleSets.has(c.expect.centre.mode));
}
for (const [label, root, mode] of [["Dm7 G7", "D", "Dorian"], ["Am7 D", "A", "Dorian"], ["Am F C G", "A", "Aeolian"]]) {
  check(`scale: the vamp ${label} gives ${root} ${mode}`, centres.some((c) => c.label.startsWith(label) && c.expect.centre?.root === root && c.expect.centre?.mode === mode));
}
check("scale: his Db loop gives no centre", centres.some((c) => c.group === "daniel" && c.expect.centre === null));
for (const c of scaleFx.cases.filter((x) => x.kind === "view")) check(`${c.id} steps in time order`, c.steps.every((s, i) => i === 0 || s.t > c.steps[i - 1].t));

// ------------------------------------------------------------------------------------------- function cases --
check("function case ids are unique", new Set(fnFx.cases.map((c) => c.id)).size === fnFx.cases.length);
check("at least 40 function cases", fnFx.cases.length >= 40);
for (const c of fnFx.cases) {
  check(`${c.id} areas start at window 0 and rise`, (c.areas[0].from === 0) && c.areas.every((a, i) => i === 0 || a.from > c.areas[i - 1].from));
  check(`${c.id} one expectation per window, in order`, c.expect.length === c.windows.length && c.expect.every((e, i) => e.at === i));
  c.windows.forEach((w, i) => {
    const area = [...c.areas].reverse().find((a) => a.from <= i);
    check(`${c.id} window ${i} ${w.chord} numbers ${w.number} in ${area.key}`, numberOf(w.chord, area.key, w.kind || null) === w.number, String(numberOf(w.chord, area.key, w.kind || null)));
    if (w.notes) check(`${c.id} window ${i} notes read`, midis(w.notes).every((m) => m != null));
    const e = c.expect[i];
    if (e.label === null) { check(`${c.id} window ${i}: only a note has no label`, w.kind === "note"); return; }
    check(`${c.id} window ${i} lexId`, e.lexId === fnFx.labels[e.label] && lex.entries.some((x) => x.id === e.lexId), e.lexId);
    if (e.label === "from the old key") {
      const ai = c.areas.indexOf(area), old = ai > 0 ? c.areas[ai - 1].key : c.before;
      check(`${c.id} window ${i} old key and its number`, e.detail.old_key === old && numberOf(w.chord, old, w.kind || null) === e.detail.old_number, `${old} ${numberOf(w.chord, old, w.kind || null)}`);
    }
    if (e.label === "borrowed") {
      const k = NV.parseKey(area.key);
      check(`${c.id} window ${i} borrowed from the parallel key`, e.detail.from === `${area.key.split(" ")[0]} ${k.mode === "major" ? "minor" : "major"}`);
    }
  });
}
const fnGroups = new Set(fnFx.cases.map((c) => c.group));
check("function: every required shape is present", ["cadence", "secondary-dominant", "backdoor", "tritone", "passing", "borrowed", "modal", "chromatic", "gospel", "key-change"].every((g) => fnGroups.has(g)));
check("function: the 9 no-pause key changes of S1-S6", ["k-01", "k-02a", "k-03", "k-04", "k-05", "k-06", "k-07", "k-08", "k-09"].every((id) => fnFx.cases.some((c) => c.id === id)));
check("function: a secondary dominant that lands and one that does not", fnFx.cases.some((c) => c.expect.some((e) => e.detail?.lands === true)) && fnFx.cases.some((c) => c.expect.some((e) => e.detail?.lands === false)));
check("function: the gospel 5 over 4 resolving and not", ["Bb11/Ab", "Ab6/9#11"].every((n) => fnFx.cases.some((c) => c.expect.some((e) => e.confirmed === n))));

// ------------------------------------------------------------------------------------------ window sessions --
const DANIEL = new Set(["midi", "keys", "demo"]);
check("at least 12 window sessions", sessions.length >= 12);
const sessionById = new Map(sessions.map(({ doc }) => [doc.id, doc]));
for (const { f, doc } of sessions) {
  const ev = doc.events;
  check(`${doc.id} file name follows the id`, f === `${doc.id.slice(0, 4)}_${doc.id.slice(5).replace(/-/g, "_")}.json`);
  check(`${doc.id} events in time order, inside the session`, ev.every((e, i) => (i === 0 || e.t_ms >= ev[i - 1].t_ms) && e.t_ms <= doc.expect.end_ms));
  const open = new Map();
  let paired = true, pedalDown = null, pedalMs = 0;
  for (const e of ev) {
    if (e.kind === "pedal") { if (e.down && pedalDown === null) pedalDown = e.t_ms; else if (!e.down && pedalDown !== null) { pedalMs += e.t_ms - pedalDown; pedalDown = null; } continue; }
    const k = `${e.source}|${e.note}`, st = open.get(k);
    if (e.kind === "on") { if (st) paired = false; open.set(k, { on: e.t_ms, off: null }); }
    else if (e.kind === "off") { if (!st || st.off !== null) paired = false; else st.off = e.t_ms; }
    else if (e.kind === "sound_end") { if (!st || st.off === null || e.t_ms < st.off) paired = false; open.delete(k); }
  }
  check(`${doc.id} every note is struck, released and ends`, paired && open.size === 0 && pedalDown === null);
  check(`${doc.id} pedal share`, Math.abs(pedalMs / doc.expect.end_ms - doc.profile.pedal_down_share) <= 0.01, (pedalMs / doc.expect.end_ms).toFixed(2));
  const onsets = ev.filter((e) => e.kind === "on" && DANIEL.has(e.source)).map((e) => e.t_ms);
  const w = doc.expect.windows.map((x) => x.start_ms);
  check(`${doc.id} windows start at Daniel's onsets, the first at his first`, w[0] === onsets[0] && w.every((t, i) => onsets.includes(t) && (i === 0 || t > w[i - 1])));
  if (doc.same_as) {
    const twin = sessionById.get(doc.same_as);
    const mine = (d) => JSON.stringify(d.events.filter((e) => e.kind === "pedal" || DANIEL.has(e.source)));
    check(`${doc.id} has the same Daniel notes and windows as ${doc.same_as}`, !!twin && mine(twin) === mine(doc) && JSON.stringify(twin.expect.windows) === JSON.stringify(doc.expect.windows));
    check(`${doc.id} carries notes from other sources`, ev.some((e) => !DANIEL.has(e.source)));
  }
}
const allSources = new Set(sessions.flatMap(({ doc }) => doc.events.map((e) => e.source)));
check("window sessions use midi, keys, demo, claude and replay notes", ["midi", "keys", "demo", "claude", "replay"].every((s) => allSources.has(s)));
check("window sessions include pedalled arpeggios, a walking bass and a pedal held through a change", ["ws03", "ws04", "ws06", "ws14"].every((p) => sessions.some(({ doc }) => doc.id.startsWith(p))));

// ---------------------------------------------------------------------------------------------------- lexicon --
const lexIds = new Set(lex.entries.map((e) => e.id));
check("lexicon ids are unique", lexIds.size === lex.entries.length);
const guardRe = new RegExp(`\\b(${lex.guard.never.filter((w) => /^\w+$/.test(w)).join("|")})\\b`, "i");
const guardHits = (s) => guardRe.test(s) || (lex.guard.never.includes("%") && s.includes("%")) || lex.guard.never_symbols.some((x) => s.includes(x));
check("lexicon guard names the spec's words", ["wrong", "mistake", "error", "should", "correct", "best", "score", "%"].every((w) => lex.guard.never.includes(w)));
const own = [...lex.entries.flatMap((e) => [e.plain, e.theory, e.meaning]), ...lex.captions.map((c) => c.example), ...lex.captions.map((c) => c.situation)];
const hits = own.filter(guardHits);
check("lexicon guard passes on its own strings", hits.length === 0, hits.slice(0, 5).join(" | "));
check("lexicon guard catches what it names", ["that was wrong", "a 90% fit", "the best name", "Cm7(no3)", "5^7"].every(guardHits) && !guardHits("borrowed colour"));
for (const e of lex.entries) {
  const slots = `${e.plain} ${e.theory}`.match(/<[^>]+>/g) || [];
  check(`lexicon ${e.id} placeholders are declared`, slots.every((s) => lex.placeholders.includes(s)), slots.join());
}
for (const [label, id] of Object.entries(lex.labels)) check(`lexicon label ${label} has entry ${id}`, lexIds.has(id) && fnFx.labels[label] === id);
for (const c of lex.captions) {
  check(`caption priority ${c.priority} (${c.label ?? c.situation}) runs resolve`, c.runs.every((r) => (r.lex ? lexIds.has(r.lex) : lex.placeholders.includes(r.slot))));
}
check("captions: priorities 0 to 4 are all written", [0, 1, 2, 3, 4].every((p) => lex.captions.some((c) => c.priority === p)));
check("lexicon holds the row, chip, HUD, reason and practice words", ["row.new_key", "row.listening", "chip.no3", "chip.also", "hud.implied", "reason.bass_root", "verb.another_name", "word.bright_four"].every((id) => lexIds.has(id)));
check("lexicon holds design-pedagogy 6.2's words", ["home", "lift", "pull", "float", "shade", "soft landing", "arrival", "surprise", "colour", "the bright 4", "floor", "held floor",
  "walking floor", "roof and floor", "rub", "release", "question", "answer", "borrowed colour", "half-step slide", "door chord", "same notes, other home", "same home, other mood",
  "another name for the same notes"].every((w) => lex.entries.some((e) => e.plain === w)));

// ==================================================================================== the reader (TN1) receipts ==
check("the schema reader rejects a broken case", validate(schemaDoc("chord_readings_cases.schema.json").$defs.case, { id: "x", group: "nope" }, "chord_readings_cases.schema.json").length >= 3);

const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
const THEORY_A = pianoSrc.indexOf("// ===== THEORY BEGIN"), THEORY_B = pianoSrc.indexOf("// ===== THEORY END");
const sliceTheory = () => new Function(pianoSrc.slice(THEORY_A, THEORY_B) + "\nreturn Theory;")();
const RANK = { clear: 0, leaning: 1, ambiguous: 2, none: 3 };
const noNo3 = (id) => id && id.replace("(no3)", "");

async function scoreReader(file) {
  check("THEORY markers present in arsenal/web/piano.js", THEORY_A >= 0 && THEORY_B > THEORY_A);
  const M = await import(pathToFileURL(file).href);
  check("READER_API is arsenal.piano.chordread/v1", M.READER_API === "arsenal.piano.chordread/v1", String(M.READER_API));
  for (const fn of ["createReader", "installReader", "parseSuffix"]) check(`chordread exports ${fn}`, typeof M[fn] === "function");
  if (typeof M.createReader !== "function") return;
  const Templates = sliceTheory();  // the pre-build Theory.detect, whose name the canvas ALSO keeps
  const reader = M.createReader({ Theory: sliceTheory(), NV });
  for (const fn of ["read", "alsoOf", "closeOf", "detect"]) check(`reader.${fn} is a function`, typeof reader[fn] === "function");
  const reasonRes = lex.entries.filter((e) => e.id.startsWith("reason.")).map((e) => new RegExp("^" + e.plain.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/<[^>]+>/g, ".+") + "$"));
  const results = new Map(), unmatched = new Set(), suffixes = new Set(), shapeErr = [];
  for (const c of cases) {
    const ms = midis(c.notes), k = c.key ? NV.parseKey(c.key) : null;
    const prev = c.prev ? { root: Number(ident(c.prev).split("|")[0]) } : null;
    let res;
    try { res = reader.read(ms, { key: c.key, prev }); } catch (e) { check(`${c.id} read does not throw`, false, String(e.stack).split("\n").slice(0, 2).join(" ")); continue; }
    const errs = validate({ $ref: "contracts.schema.json#/$defs/ReadResult" }, res, "contracts.schema.json");
    if (errs.length) shapeErr.push(`${c.id}: ${errs[0]}`);
    const top = res && res.kind === "chord" && Array.isArray(res.readings) && res.readings[0] || null;
    const tInfo = Templates.detect(ms, k ? k.bias : 0);
    let also = null, close = null;
    try { also = reader.alsoOf(res, tInfo, 1000); close = reader.closeOf(res, 1000); } catch (e) { check(`${c.id} alsoOf and closeOf do not throw`, false, e.message); }
    if (validate({ $ref: "contracts.schema.json#/$defs/AlsoResult" }, also, "contracts.schema.json").length) shapeErr.push(`${c.id}: alsoOf shape`);
    results.set(c.id, { res, top, also, close, tInfo });
    for (const r of (res?.readings || []).slice(0, 3)) {
      for (const s of r.reasons || []) if (!reasonRes.some((re) => re.test(plainText(s)))) unmatched.add(s);
      suffixes.add(r.suffix);
    }
  }
  check("every read() result has the ReadResult shape", shapeErr.length === 0, `${shapeErr.length}: ${shapeErr.slice(0, 3).join("; ")}`);
  check("every reason of the top 3 readings is a lexicon reason (the HUD's plain half)", unmatched.size === 0, [...unmatched].slice(0, 8).join(" | "));

  const R = (c) => results.get(c.id) || { res: { readings: [] }, top: null };
  const okIds = (c) => [c.expect.name, ...(c.expect.accept || [])].map((n) => noNo3(ident(n)));
  const right = (c) => { const r = R(c); return !!r.top && !!c.expect.name && okIds(c).includes(noNo3(identOf(r.top))) && (!/\(no3\)/.test(c.expect.name) || noNo3(identOf(r.top)) !== noNo3(ident(c.expect.name)) || !!r.top.omit?.no3); };
  const exact = (c) => { const r = R(c); return !!r.top && !!c.expect.name && noNo3(identOf(r.top)) === noNo3(ident(c.expect.name)); };
  const shown = (c) => { const r = R(c); return r.top ? r.top.name : `(${r.res?.kind ?? "no result"})`; };
  const missLine = (c) => `${c.id.padEnd(30)} ${c.notes.padEnd(30)} ${String(c.key).padEnd(9)} want ${String(c.expect.name).padEnd(12)} read ${shown(c).padEnd(14)} ${R(c).res?.band ?? ""}`;

  // NG1: the original 71
  const named = proto.filter((c) => c.expect.name);
  const nRight = named.filter(right), nExact = named.filter(exact);
  report.push(`NG1 prototype: ${nRight.length}/${named.length} right, ${nExact.length} exact`);
  check("NG1: the original 71 at least 71 right", nRight.length >= 71, named.filter((c) => !right(c)).map(missLine).join("\n  "));
  check("NG1: the original 71 at least 67 exact", nExact.length >= 67, String(nExact.length));
  for (const [s, n] of [["plain", 32], ["daniel", 24], ["dominant", 10], ["voicing", 5]]) {
    const g = protoSet(s).filter((c) => c.expect.name), ok = g.filter(right);
    report.push(`NG1 ${s}: ${ok.length}/${n}`);
    check(`NG1: ${s} ${n}/${n}`, ok.length === n, g.filter((c) => !right(c)).map(missLine).join("\n  "));
  }
  const wanted = proto.flatMap((c) => (c.expect.tags || []).map((t) => [c, t]));
  const found = wanted.filter(([c, t]) => (R(c).res?.tags || []).some((x) => x.tag === t));
  report.push(`NG1 tags: ${found.length}/${wanted.length}`);
  check("NG1: voicing tags 6/6", found.length === 6 && wanted.length === 6, wanted.filter((w) => !found.includes(w)).map(([c, t]) => `${c.id} ${t}`).join(", "));
  const clusterFp = protoSet("daniel").filter((c) => (R(c).res?.tags || []).some((x) => x.tag === "cluster"));
  report.push(`NG1 cluster tag on Daniel's 24: ${clusterFp.length} (at most 4, goal 2)`);
  check("NG1: cluster tag on at most 4 of Daniel's 24", clusterFp.length <= 4, clusterFp.map((c) => c.id).join(", "));

  // strict cases: defects and chips (NG1), the ALSO lab table (NG3)
  for (const c of cases.filter((x) => x.expect.strict)) {
    const r = R(c), e = c.expect, res = r.res || { readings: [] }, out = [];
    const first = (res.readings || [])[0];
    if (e.name && !right(c)) out.push(`name ${shown(c)}, want ${e.name}${e.accept?.length ? " or " + e.accept.join(" or ") : ""}`);
    if (e.kind && res.kind !== e.kind) out.push(`kind ${res.kind}, want ${e.kind}`);
    if (e.band && res.band !== e.band) out.push(`band ${res.band}, want ${e.band}`);
    if (e.band_max && !(RANK[res.band] >= RANK[e.band_max])) out.push(`band ${res.band}, want ${e.band_max} or less sure`);
    const tags = (res.tags || []).map((t) => t.tag);
    for (const t of e.tags || []) if (!tags.includes(t)) out.push(`no ${t} tag`);
    for (const t of e.tags_absent || []) if (tags.includes(t)) out.push(`a ${t} tag`);
    if (e.base_family && first?.base?.family !== e.base_family) out.push(`family ${first?.base?.family}, want ${e.base_family}`);
    if (e.no3 !== undefined && !!first?.omit?.no3 !== e.no3) out.push(`no3 ${!!first?.omit?.no3}, want ${e.no3}`);
    for (const x of e.include || []) if (!(res.readings || []).slice(0, x.within).some((y) => noNo3(identOf(y)) === noNo3(ident(x.name)))) out.push(`${x.name} not in the first ${x.within} readings`);
    for (const x of e.exclude || []) {
      const want = ident(x.name), cut = (id) => (x.any_bass ? id.split("|").slice(0, 2).join("|") : id);
      const hit = (res.readings || []).find((y) => cut(identOf(y)) === cut(want));
      if (hit) out.push(`${hit.name} is among the readings`);
    }
    if (e.also !== undefined && exact(c)) { const got = r.also ? plainText(r.also.name) : null; if (got !== e.also) out.push(`ALSO ${got}, want ${e.also}`); }
    if (e.close !== undefined) { const got = r.close ? plainText(r.close.name) : null; if (got !== e.close) out.push(`HUD close ${got}, want ${e.close}`); }
    if (e.number !== undefined && (e.name === null || exact(c))) { const got = first ? numberOf(first.name, c.key) : null; if (got !== e.number) out.push(`number ${got}, want ${e.number}`); }
    if (e.name && exact(c) && plainText(first.name).replace("(no3)", "") !== e.name.replace("(no3)", "")) out.push(`spelled ${first.name}, want ${e.name}`);
    check(`${c.group === "also-lab" ? "NG3" : "NG1"} ${c.group} ${c.id} (${c.notes} in ${c.key})`, out.length === 0, out.join("; "));
  }

  // spec 2.6's band ceiling and canvas ALSO on the cases that are not strict (prototype, transposed). ALSO is asserted
  // when the top reading is the expected name, and matched by identity (the strict cases above match its spelling).
  const loose = cases.filter((x) => !x.expect.strict);
  const ceil = loose.filter((x) => x.expect.band_max), ceilBad = ceil.filter((x) => !(RANK[R(x).res?.band] >= RANK[x.expect.band_max]));
  report.push(`band ceilings (cases not strict): ${ceil.length - ceilBad.length}/${ceil.length} held`);
  check("spec 2.6: every band ceiling holds", ceilBad.length === 0, ceilBad.slice(0, 8).map((x) => `${x.id} ${R(x).top?.name} ${R(x).res?.band} over ${x.expect.band_max}`).join(" | "));
  const was = loose.filter((x) => x.expect.also !== undefined && exact(x));
  const wasBad = was.filter((x) => (R(x).also ? ident(R(x).also.name) : null) !== (x.expect.also ? ident(x.expect.also) : null));
  report.push(`canvas ALSO as written (cases not strict, top reading the expected name): ${was.length - wasBad.length}/${was.length}`);
  check("spec 2.6: every canvas ALSO is as written", wasBad.length === 0, wasBad.slice(0, 8).map((x) => `${x.id} ALSO ${R(x).also?.name ?? null}, want ${x.expect.also}`).join(" | "));

  // NG1: Daniel's 24 give identical numbers in every key
  let sameNumbers = 0;
  for (const orig of protoSet("daniel")) {
    const mine = [orig, ...transposed.filter((c) => c.of === orig.id)];
    const nums = mine.map((c) => (R(c).top ? numberOf(R(c).top.name, c.key) : null));
    const same = nums.every((n) => n !== null && n === nums[0]);
    sameNumbers += same;
    check(`NG1: ${orig.id} (${orig.expect.name}) numbers identically in all 12 keys`, same, [...new Set(nums.map((n, i) => `${n} in ${mine[i].key}`))].slice(0, 4).join(", "));
  }
  report.push(`NG1 Daniel's 24 x 12 keys: ${sameNumbers}/24 identical numbers; transposed right ${transposed.filter(right).length}/${transposed.length}`);
  const seeds = group("seed"), seedMiss = seeds.filter((c) => !right(c));
  // reported, not a spec gate: the page reads every seed slot today ("the same page, but right"), so misses are listed
  report.push(`seed slots right: ${seeds.length - seedMiss.length}/${seeds.length}${seedMiss.length ? "\n  " + seedMiss.map(missLine).join("\n  ") : ""}`);

  // detect() keeps today's info shape; installReader; parseSuffix; alsoOf's guards
  for (const c of protoSet("plain")) {
    const ms = midis(c.notes), info = reader.detect(ms, NV.parseKey(c.key).bias);
    const errs = validate({ $ref: "contracts.schema.json#/$defs/DetectInfo" }, info, "contracts.schema.json");
    check(`detect ${c.id} has today's info shape plus readings`, errs.length === 0 && Array.isArray(info.readings), errs[0] || "no readings");
  }
  const T2 = sliceTheory(), original = T2.detect;
  M.installReader(T2, NV);
  check("installReader keeps the templates as Theory.detectTemplates", T2.detectTemplates === original);
  check("installReader sets Theory.read and replaces Theory.detect", typeof T2.read === "function" && T2.detect !== original && T2.detect(midis("C3 E3 G3"), 0)?.name === "C");
  for (const s of suffixes) {
    let p = null;
    try { p = M.parseSuffix(s); } catch (e) { /* reported below */ }
    const errs = p ? validate({ $ref: "contracts.schema.json#/$defs/ParsedSuffix" }, p, "contracts.schema.json") : ["threw or returned nothing"];
    check(`parseSuffix(${JSON.stringify(s)}) shape`, errs.length === 0 && p.tones && ("0" in p.tones), errs[0]);
  }
  const lab = R(byId.get("also-lab-1"));
  check("alsoOf waits 1 s", reader.alsoOf(lab.res, lab.tInfo, 999) === null);
  check("alsoOf needs a template chord", reader.alsoOf(lab.res, { ...lab.tInfo, kind: "cluster" }, 1000) === null);
  check("closeOf waits 1 s", reader.closeOf(R(byId.get("also-lab-8")).res, 999) === null);

  // ---------------------------------------------------------------- TN1 reader invariants over every fixture result --
  // parseSuffix twins nashville.js's hand tables (NG4's twin lands in TN5): TONE_STEPS exactly, FAMILY and DOMINANT read
  // from nashville.js's own source.
  const nvSrc = readFileSync(here("../arsenal/web/piano/nashville.js"), "utf8");
  const FAMILY = new Function(`return ${/const FAMILY = (\{[\s\S]*?\});/.exec(nvSrc)[1]}`)();
  const DOMINANT = new Set(new Function(`return ${/const DOMINANT = new Set\((\[[^\]]*\])\)/.exec(nvSrc)[1]}`)());
  for (const [s, steps] of Object.entries(NV.TONE_STEPS)) {
    const p = M.parseSuffix(s);
    const got = JSON.stringify(Object.entries(p.tones).map(([k, v]) => [Number(k), v]).sort((a, b) => a[0] - b[0]));
    const want = JSON.stringify(Object.entries(steps).map(([k, v]) => [Number(k), v]).sort((a, b) => a[0] - b[0]));
    check(`parseSuffix(${JSON.stringify(s)}) tones equal nashville.js TONE_STEPS`, got === want, `${got} want ${want}`);
    check(`parseSuffix(${JSON.stringify(s)}) family equals nashville.js FAMILY`, p.family === FAMILY[s], `${p.family} want ${FAMILY[s]}`);
    check(`parseSuffix(${JSON.stringify(s)}) dominant equals nashville.js DOMINANT`, p.dominant === DOMINANT.has(s));
  }
  const emitted = new Map();
  let nRead = 0, a1 = 0, a2 = 0, a4 = 0, a7 = 0, back = 0, fam = 0;
  const badA1 = [], badBack = [], badA7 = [];
  const keyScaleOf = (k) => new Set((k.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11]).map((x) => mod(x + k.tonic, 12)));
  const overOwnTop = (r) => r.path === "slash" && r.bass != null && [9, 10, 11].includes(mod(r.bass - r.root, 12));
  let augT = 0;
  for (const c of cases) {
    const res = R(c).res;
    if (!res || !Array.isArray(res.readings)) continue;
    const ms = midis(c.notes), k = c.key ? NV.parseKey(c.key) : null;
    // every candidate of the same read (reach: Infinity), so A2's condition can be judged from outside
    const wide = reader.read(ms, { key: c.key, prev: c.prev ? { root: Number(ident(c.prev).split("|")[0]) } : null, reach: Infinity }).readings;
    const pcs = new Set(ms.map((m) => mod(m, 12))), bass = mod(Math.min(...ms), 12);
    for (const r of res.readings) {
      nRead++;
      emitted.set(r.suffix, (emitted.get(r.suffix) || 0) + 1);
      const p = M.parseSuffix(r.suffix);
      // the name parses back to the notes: every sounding pitch class is a tone of the suffix on its root (a slash
      // reading's bass excepted), and no tone of the suffix is missing but an omitted 5th, 3rd or root
      const toneSet = new Set(Object.keys(p.tones).map((x) => mod(Number(x) + r.root, 12)));
      const heard = [...pcs].filter((x) => !(r.path === "slash" && x === bass));
      const missing = [...toneSet].filter((x) => !pcs.has(x) && !(r.omit.no5 && mod(x - r.root, 12) === 7) && !(r.omit.rootless && x === r.root)
        && !(r.path === "template") && !(mod(x - r.root, 12) === 2 && /13/.test(r.suffix)) && !(mod(x - r.root, 12) === 2 && /^m?(11|13)/.test(r.suffix)));
      if (r.path !== "drop" && p.known && heard.every((x) => toneSet.has(x)) && missing.length === 0) back++;
      else badBack.push(`${c.id} ${r.name} (${r.path})`);
      if (r.path === "template" || p.quality === r.base.family || (r.base.family === "open" && r.omit.no3)) fam++;
      // A1: a no-3rd reading's family follows the key's diatonic 3rd; open with no key
      if (r.omit.no3) {
        let want;
        if (!k) want = "open";
        else {
          const sc = keyScaleOf(k), m3 = sc.has(mod(r.root + 3, 12)), M3 = sc.has(mod(r.root + 4, 12));
          want = m3 && !M3 ? "min" : null;
        }
        if (want === "open" ? r.base.family === "open" : want === "min" ? r.base.family === "min" : r.base.family !== "min" && r.base.family !== "open") a1++;
        else badA1.push(`${c.id} ${r.name} ${r.base.family}`);
      } else a1++;
      // A2: no slash reading over its own 6th, b7 or 7th survives beside a full reading on that root and bass (a duplicate)
      if (!(overOwnTop(r) && wide.some((f) => f.path === "full" && f.root === r.root && f.bass === r.bass))) a2++;
      if (r.base.id === "aug" && r.tensions.length) augT++;
      // A4 and D6: no 11 without a 3rd
      if (!(r.omit.no3 && r.tensions.includes(5))) a4++;
      // A7: the root is spelled as spellInKey spells it whenever the page's spellForKey takes that spelling: on the key's
      // scale (E# and Cb included), or one accidental at most and not E#, B#, Cb or Fb
      if (k) {
        const root = NV.parseChord(r.name).root, w = NV.spellInKey(root, c.key, { suffix: r.base.id });
        const wName = "CDEFGAB"[w.letter] + (w.acc > 0 ? "#".repeat(w.acc) : "b".repeat(-w.acc));
        if (!(w.inScale || (Math.abs(w.acc) <= 1 && !["E#", "B#", "Cb", "Fb"].includes(wName))) || (w.letter === root.letter && w.acc === root.acc)) a7++;
        else badA7.push(`${c.id} ${r.name} (${c.key}: ${wName})`);
      } else a7++;
    }
  }
  report.push(`TN1 readings over the fixtures: ${nRead}, ${emitted.size} distinct suffixes`);
  check("every reading's name parses back to its notes (parseSuffix)", back === nRead - badBack.filter((x) => /\(drop\)/.test(x)).length, badBack.filter((x) => !/\(drop\)/.test(x)).slice(0, 6).join(" | "));
  check("every reading's family is its suffix's quality (open only for no-3rd without a key)", fam === nRead, String(nRead - fam));
  check("A1: every no-3rd reading takes the key's diatonic 3rd (open with no key)", a1 === nRead, badA1.slice(0, 6).join(" | "));
  check("A2: no slash duplicate (a slash reading over its own 6th, b7 or 7th beside a full reading on that root and bass) in any result", a2 === nRead, String(nRead - a2));
  check("no augmented triad with a tension in any result (it is a 7#5 chord on another root)", augT === 0, String(augT));
  check("A4: no 11 over a missing 3rd in any result", a4 === nRead, String(nRead - a4));
  check("A7: every root spelled in the key", a7 === nRead, badA7.slice(0, 6).join(" | "));
  for (const [s] of emitted) check(`parseSuffix(${JSON.stringify(s)}) reads the whole suffix`, M.parseSuffix(s).known === true);
  const allReasons = new Set(cases.flatMap((c) => (R(c).res?.readings || []).flatMap((r) => r.reasons)));
  const offLex = [...allReasons].filter((s) => !reasonRes.some((re) => re.test(plainText(s))));
  check("every reason of every reading is a lexicon reason", offLex.length === 0, offLex.slice(0, 6).join(" | "));

  // A1 words and D12 on detect(): the flag stays, "(no3)" never reaches info.name or info.suffix
  const eb = reader.read(midis("C3 G3 Bb3"), { key: "Eb major" });
  check("A1: the key's 3rd is a reason", eb.readings[0].reasons.includes("no 3rd: the key gives it a minor 3rd"), eb.readings[0].reasons.join("; "));
  for (const [key, want] of [["Eb major", "Cm7"], ["F major", "C7"]]) {
    const info = reader.detect(midis("C3 G3 Bb3"), NV.parseKey(key).bias, { key });
    check(`D12: detect in ${key} names ${want} with info.no3 and no (no3)`, info.name === want && info.suffix === want.slice(1) && info.no3 === true
      && NV.nashville(info, key)?.text === (key === "Eb major" ? "6m7" : "5^7"), `${info.name} ${info.suffix} ${info.no3}`);
  }
  const cl = reader.detect(midis("C4 D4 E4 F4"), 0);
  check("A3: detect draws a cluster as letters", cl.kind === "cluster" && cl.name === "C D E F" && cl.root === null && cl.notes.length === 4, `${cl.kind} ${cl.name}`);
  const iv = reader.detect(midis("C4 G4"), 0), note = reader.detect(midis("E4"), 0);
  check("detect keeps today's info for a power chord and a note", iv.name === "C5" && iv.sub === "power chord" && note.kind === "note" && note.name === "E4");
  const gb = reader.detect(midis("Gb2 Db3 F3 Ab3 Bb3 C4 Eb4"), -1, { key: "Db major" });
  check("detect spells every note of the chord from its root", gb.name === "Gbmaj13#11" && gb.pcNames.join(" ") === "Gb Db F Ab Bb C Eb"
    && gb.notes.every((n) => n.octave >= 2) && NV.nashville(gb, "Db major")?.text === "4maj13#11", `${gb.name} ${gb.pcNames}`);
  // install twice, determinism, the faint-note path, the bass option, empty and small inputs
  const T3 = sliceTheory(), first = T3.detect;
  const r1 = M.installReader(T3, NV);
  M.installReader(T3, NV);
  check("installReader twice keeps the first templates and returns the reader", T3.detectTemplates === first && typeof r1?.read === "function");
  const v = midis("Ab2 Eb3 G3 C4 D4 F4 Bb4");
  check("read is deterministic (bit-identical results)", JSON.stringify(reader.read(v, { key: "Eb major" })) === JSON.stringify(reader.read(v, { key: "Eb major" })));
  const faint = reader.read([{ midi: 48, w: 1 }, { midi: 52, w: 1 }, { midi: 55, w: 1 }, { midi: 59, w: 1 }, { midi: 62, w: 0.2 }], { key: "C major" });
  check("a faint note may be passing, nRead in the key", faint.readings.some((r) => r.path === "drop" && r.reasons.includes("D treated as passing (faint)"))
    || faint.readings[0].name === "Cmaj9", faint.readings.map((r) => `${r.name} ${r.path}`).join(", "));
  const onBass = reader.read(midis("E3 G3 C4"), { key: "C major", bassMidi: 48 });
  check("bassMidi names the chord from the given bass", onBass.readings[0].name === "C", onBass.readings[0]?.name);
  const none = reader.read([], {}), two = reader.read(midis("C4 E4"), {});
  check("an empty or two-note input is small", none.kind === "small" && two.kind === "small" && none.band === "none" && reader.alsoOf(two, { kind: "chord", name: "C" }, 5000) === null && reader.closeOf(two, 5000) === null);
  // A2 over every chord shape: each set of 4-8 pitch classes over a bass that sounds only lowest, with no key and in C
  // major and C minor, every candidate listed. No slash reading over its own 6th, b7 or 7th sits beside a full reading on
  // that root and bass; one with no full reading is a name of its own and stays. No augmented triad keeps a tension.
  let shapes = 0, dupes = 0, keptSlash = 0, augShapes = 0;
  for (let mask = 0; mask < 1 << 11; mask++) {
    const upper = [];
    for (let b = 0; b < 11; b++) if (mask & (1 << b)) upper.push(b + 1);
    if (upper.length < 3 || upper.length > 7) continue;
    for (const key of [null, "C major", "C minor"]) {
      shapes++;
      const all = reader.read([36, ...upper.map((x) => 48 + x)], { key, reach: Infinity }).readings;
      const over = all.filter(overOwnTop), full = (x) => all.some((f) => f.path === "full" && f.root === x.root && f.bass === x.bass);
      if (over.some(full)) dupes++;
      if (over.some((x) => !full(x))) keptSlash++;
      if (all.some((x) => x.base.id === "aug" && x.tensions.length)) augShapes++;
    }
  }
  report.push(`A2 over ${shapes} chord shapes: ${dupes} with a slash duplicate; ${keptSlash} keep a slash name over its 6th, b7 or 7th with no full reading`);
  check(`A2: no slash duplicate in ${shapes} chord shapes`, dupes === 0, String(dupes));
  check(`no augmented triad with a tension in ${shapes} chord shapes`, augShapes === 0, String(augShapes));
  const noFull = reader.read([36, 49, 50, 52, 53, 57], {});
  check("A2 keeps a slash name with no full reading on its root: C2 C#3 D3 E3 F3 A3 reads Dm(maj9)/C", noFull.kind === "chord" && ident(noFull.readings[0]?.name) === ident("Dm(maj9)/C"), `${noFull.kind} ${noFull.readings[0]?.name}`);
  const augRead = reader.read(midis("G#2 C3 E3 D4"), { key: "A minor", reach: Infinity });
  check("an augmented triad with a tension reads as its 7#5 chord: G#2 C3 E3 D4 in A minor is E7#5/G#", augRead.readings[0]?.name === "E7#5/G#"
    && !augRead.readings.some((r) => r.base.id === "aug" && r.tensions.length), augRead.readings.slice(0, 3).map((r) => r.name).join(", "));
  const q3 = reader.read(midis("D3 G3 C4"), { key: "C major" });
  check("three pitch classes stacked in 4ths up from the bass are never clear: D3 G3 C4", q3.kind === "chord" && q3.band !== "clear", `${q3.readings[0]?.name} ${q3.band}`);
  const rootless = reader.read(midis("C2 E3 Bb3 D4 F#4 A4"), { key: "F major", allowRootless: false });
  check("allowRootless false leaves out rootless readings", rootless.readings.every((r) => !r.omit.rootless));

  // A7 spellings the page keeps (piano.js spellForKey): E#, B#, Cb and Fb when the key's scale or the chord's letters call
  // for them, in read() names and in detect()'s label
  for (const [notes, key, want] of [["E#2 G#3 C#4", "F# major", "C#/E#"], ["E#2 A#2 C#3 F#3", "F# major", "F#maj7/E#"], ["Cb2 Ab2 Eb3", "Ab major", "Abm/Cb"],
    ["Cb3 Eb3 Gb3 Bb3 Db4", "Gb major", "Cbmaj9"]]) {
    const got = reader.read(midis(notes), { key }).readings[0]?.name, info = reader.detect(midis(notes), NV.parseKey(key).bias, { key });
    check(`A7: ${notes} in ${key} is spelled ${want}`, got === want && info.name === want, `read ${got}, detect ${info.name}`);
  }

  // inputs a live window hands in (H5): a bass outside the notes joins them, so every reason is a lexicon reason and every
  // name's bass sounds; weights that are missing, not a number or out of range never reach a cost. A reader that throws
  // on them fails the check instead of stopping the run.
  const tryRead = (label, ms, opts) => {
    try { return reader.read(ms, opts); } catch (e) {
      check(`${label}: read does not throw`, false, String(e.message));
      return { kind: "small", readings: [], band: "none", margin: 0, confidence: 0, tags: [], key: null };
    }
  };
  for (const [ms, bassMidi, key] of [[[48, 51, 55], 44, "C minor"], [[48, 52, 55], 58, "F major"], [[50, 53, 57], 43, null], [[48, 51, 55], 52, "C minor"]]) {
    const res = tryRead(`bassMidi ${bassMidi} outside ${ms.join(" ")}`, ms, { key, bassMidi });
    const errs = validate({ $ref: "contracts.schema.json#/$defs/ReadResult" }, res, "contracts.schema.json");
    const sounding = new Set([...ms, bassMidi].map((m) => mod(m, 12)));
    const offWords = res.readings.flatMap((r) => r.reasons).filter((s) => !reasonRes.some((re) => re.test(plainText(s))));
    check(`bassMidi ${bassMidi} outside ${ms.join(" ")} (${key}): the ReadResult shape, lexicon reasons, a bass that sounds`,
      errs.length === 0 && offWords.length === 0 && res.readings.length > 0 && res.readings.every((r) => sounding.has(r.bass ?? r.root)),
      `${errs[0] || ""} ${offWords.join(" | ")} ${res.readings.map((r) => r.name).join(", ")}`);
  }
  const under = tryRead("bassMidi Ab2 under C3 Eb3 G3", midis("C3 Eb3 G3"), { key: "C minor", bassMidi: 44 });
  check("bassMidi Ab2 under C3 Eb3 G3 names Abmaj7", under.readings[0]?.name === "Abmaj7", under.readings[0]?.name);
  const odd = tryRead("weights that are not numbers", [{ midi: 48, w: 1 }, { midi: 52, w: undefined }, { midi: 55, w: 1 }, { midi: 59, w: NaN }, { midi: 62, w: 7 }, { midi: "x" }, null], { key: "C major" });
  const oddErrs = validate({ $ref: "contracts.schema.json#/$defs/ReadResult" }, odd, "contracts.schema.json");
  check("weights that are missing, not a number or out of range count as 1 or clamp, and notes that are not numbers are skipped",
    oddErrs.length === 0 && odd.readings[0]?.name === "Cmaj9" && odd.readings.every((r) => Number.isFinite(r.cost) && Number.isFinite(r.p)), `${oddErrs[0] || ""} ${odd.readings[0]?.name} ${odd.readings[0]?.cost}`);
  check("p sums to 1 over the readings returned", odd.readings.length > 0 && Math.abs(odd.readings.reduce((s, r) => s + r.p, 0) - 1) < 1e-9);
}

if (!contractsOnly) {
  const readerFile = readerArg ? resolve(readerArg) : here("../arsenal/web/piano/chordread.js");
  if (existsSync(readerFile)) await scoreReader(readerFile);
  else check(`reader module ${readerArg ? readerFile : "arsenal/web/piano/chordread.js"} exists (TN1 builds it; --contracts scores the corpus alone)`, false);
}

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
