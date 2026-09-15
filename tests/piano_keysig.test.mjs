// Node tests for theory TN2's page wiring and live sheet music LS6's key signature on the "now" staff. Zero dependencies,
// synthetic voicings only:
//   node tests/piano_keysig.test.mjs           everything, the 24-key page sweeps included
//   node tests/piano_keysig.test.mjs --quick   without the sweeps
// Rulings: research/in-flight/live-sheet-music-2026-09-14/ls1-rulings.md ("LS6 rulings": key signatures follow the settled
// Nashville key) and research/in-flight/piano-theory-nextgen-2026-09-14/tn1-rulings.md (the TN2 spelling ruling: one speller
// for the reader and the page).
// Sections: the settle model (arsenal/web/piano/keysig.js: free time, unsure, the change mark, spacing, open chords, the bar
// clock, a manual lock); signatures on the staff (24 keys, accidentals against the signature); the shared Nashville
// formatter (nashville.js formatNumber: 4 with 6/9 raised, never "46/9"); piano.js's own spellForKey and numberRuns, sliced
// from the page: one speller for the reader and the page (no rename, never worse, no double accidental on a root or bass).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as NV from "../arsenal/web/piano/nashville.js";
import * as SP from "../arsenal/web/piano/spell.js";
import * as KS from "../arsenal/web/piano/keysig.js";
import { installReader, parseSuffix } from "../arsenal/web/piano/chordread.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const quick = process.argv.includes("--quick");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const mod = (a, n) => ((a % n) + n) % n;
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
function midiOf(tok) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(tok);
  return m ? (Number(m[3]) + 1) * 12 + LETTER_PC["CDEFGAB".indexOf(m[1])] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) : null;
}
const midis = (text) => text.trim().split(/\s+/).map(midiOf);
const MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"].map((t) => `${t} major`);
const MINOR_KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"].map((t) => `${t} minor`);
const KEYS = [...MAJOR_KEYS, ...MINOR_KEYS];

// ================================================================================================ the settle model ==
check("KEYSIG_API", KS.KEYSIG_API === "arsenal.piano.keysig/v1");
// Steps a model from t0 to t1 (exclusive) every 0.1 s with the inputs input(t) gives; returns the times the signature changed.
function run(model, t0, t1, input) {
  const at = [];
  let key = model.view(t0).key;
  for (let i = 0; t0 + i * 0.1 < t1 - 1e-9; i++) {
    const t = +(t0 + i * 0.1).toFixed(3);
    model.update({ t, ...input(t) });
    const v = model.view(t);
    if (v.key !== key) { at.push({ t, from: key, to: v.key }); key = v.key; }
  }
  return at;
}
const sure = (key, more = {}) => () => ({ key, sure: true, ...more });

{  // free time: the first key after 4 s of lock confidence, with no change mark
  const m = KS.createKeySignatureModel();
  check("a new model has no signature", m.view(0).key === null && m.view(0).signature.count === 0 && m.view(0).signature.type === "none");
  const ch = run(m, 0, 10, sure("Eb major"));
  check("free time: the first key is adopted after 4 s held", ch.length === 1 && ch[0].to === "Eb major" && Math.abs(ch[0].t - 4) < 0.051, JSON.stringify(ch));
  check("the first key draws no double bar", m.view(ch[0].t).showing === false && m.view(ch[0].t).change === null);
  check("Eb major's signature is three flats", m.view(10).signature.type === "flats" && m.view(10).signature.count === 3);
  report.push(`settle model, free time: first key at ${ch[0] && ch[0].t} s`);

  // unsure keeps the signature and restarts the hold; the tracker's own key objects are read by name
  const ch2 = run(m, 30, 33, sure({ name: "Gb major", tonic: 6, mode: "major" }));
  const ch3 = run(m, 33, 33.5, () => ({ key: "Gb major", sure: false }));
  const ch4 = run(m, 33.5, 37, sure("Gb major"));
  check("unsure for 0.5 s restarts the 4 s hold (3 s + 3.5 s is no change)", ch2.length + ch3.length + ch4.length === 0 && m.view(37).key === "Eb major",
    JSON.stringify([ch2, ch3, ch4]));
  const idBefore = m.view(37).id;
  const ch5 = run(m, 37, 45, sure("Gb major"));
  check("after 4 s held without a break, the signature changes once", ch5.length === 1 && ch5[0].from === "Eb major" && ch5[0].to === "Gb major"
    && Math.abs(ch5[0].t - 37.5) < 0.051, JSON.stringify(ch5));
  const tc = ch5[0] ? ch5[0].t : 0;
  const v0 = m.view(tc), v1 = m.view(tc + 1.9), v2 = m.view(tc + 2.0);
  check("a change shows the double bar for 2 s", v0.showing && v0.change.from === "Eb major" && v0.change.to === "Gb major" && v1.showing && !v2.showing,
    JSON.stringify([v0.showing, v1.showing, v2.showing]));
  const ids = [idBefore, v0.id, v1.id, m.view(tc + 0.5).id, v2.id, m.view(tc + 9).id];
  check("the view's id changes only at the change and when the mark goes (2 redraws)", new Set(ids).size === 3 && ids[0] !== ids[1] && ids[1] === ids[3] && ids[4] === ids[5],
    ids.join(" "));
  check("Gb major's signature is six flats, Cb last", v2.signature.count === 6 && v2.signature.accidentals.map((a) => a.name).join(" ") === "Bb Eb Ab Db Gb Cb");

  // spacing: at most one change per 8 bars (16 s in free time); the change above was at 37.5 s
  const ch6 = run(m, 45, 53.4, sure("Eb major"));
  check("spacing: a key held after a change waits for 16 s since it", ch6.length === 0 && m.view(53.3).key === "Gb major", JSON.stringify(ch6));
  const ch7 = run(m, 53.4, 56, sure("Eb major"));
  check("spacing: then it is adopted", ch7.length === 1 && ch7[0].to === "Eb major" && ch7[0].t >= tc + 16 - 1e-9 && ch7[0].t < tc + 16.15, JSON.stringify(ch7));
}
{  // a change the spacing holds back is dropped when the tracker moves back
  const m = KS.createKeySignatureModel();
  run(m, 0, 5, sure("C major"));
  const back = [...run(m, 5, 12, sure("A minor")), ...run(m, 12, 40, sure("C major"))];
  check("spacing: a held-back key the tracker leaves is dropped (no change)", back.length === 0 && m.view(40).key === "C major" && m.state().candidate === null, JSON.stringify(back));
  const none = run(m, 40, 80, () => ({ key: null, sure: false }));
  check("no key for 40 s keeps the last settled signature", none.length === 0 && m.view(80).key === "C major");
  const unsure = run(m, 80, 120, () => ({ key: "D major", sure: false }));
  check("an unsure key for 40 s never changes it", unsure.length === 0 && m.view(120).key === "C major");
}
{  // never inside an open chord
  const m = KS.createKeySignatureModel();
  const open = run(m, 0, 8, sure("A major", { chord: 7 }));
  check("an open chord holds the change past its 4 s", open.length === 0 && m.state().waiting && m.state().waiting.key === "A major", JSON.stringify(m.state()));
  const next = run(m, 8, 8.2, sure("A major", { chord: 8 }));
  check("a new onset closes it: the change lands on that tick", next.length === 1 && next[0].t === 8 && next[0].to === "A major", JSON.stringify(next));
  const m2 = KS.createKeySignatureModel();
  run(m2, 0, 6, sure("F major", { chord: 3 }));
  const silent = run(m2, 6, 6.2, sure("F major", { chord: null }));
  check("silence closes it too", silent.length === 1 && silent[0].t === 6, JSON.stringify(silent));
}
{  // the bar clock: 2 bars held, at the next bar line, at most one change per 8 bars (a bar every 2 s here)
  const m = KS.createKeySignatureModel();
  const bars = (key) => (t) => ({ key, sure: true, bar: { index: Math.floor((t - 0.6) / 2), pos: (t - 0.6) / 2 }, chord: null });
  const first = run(m, 1.2, 12, bars("D major"));  // held from pos 0.3; 2 bars at pos 2.3 (t 5.2); bar line 3 at t 6.6
  check("bars: adopted at the first bar line after 2 bars held", first.length === 1 && Math.abs(first[0].t - 6.6) < 0.051, JSON.stringify(first));
  const second = run(m, 12, 30, bars("B minor"));  // spaced 8 bars from pos 3 (pos 11, t 22.6), then the bar line after
  check("bars: a second key waits 8 bars since the change, then the next bar line", second.length === 1 && Math.abs(second[0].t - 24.6) < 0.051, JSON.stringify(second));
  check("B minor takes D major's signature (two sharps)", m.view(30).signature.type === "sharps" && m.view(30).signature.count === 2);
}
{  // a key locked by hand wins at once
  const m = KS.createKeySignatureModel();
  run(m, 0, 4.5, sure("Eb major"));  // Eb major settles at 4 s; a chord is struck at 4.5 s and still sounds
  run(m, 4.5, 5, sure("Eb major", { chord: 1 }));
  const locked = run(m, 5, 5.1, () => ({ key: "Eb major", sure: true, manual: "Gb major", chord: 1 }));
  check("a manual lock is adopted on its tick, inside an open chord and the spacing", locked.length === 1 && locked[0].to === "Gb major" && locked[0].t === 5
    && m.view(5).showing && m.view(5).change.manual === true, JSON.stringify(locked));
  const again = run(m, 5.1, 6, () => ({ key: "Eb major", sure: true, manual: "C major", chord: 1 }));
  check("another lock wins again at once", again.length === 1 && again[0].to === "C major");
  const unlocked = run(m, 6, 12, sure("C major"));
  check("unlocked, the tracker's key (the pinned key) changes nothing", unlocked.length === 0 && m.view(12).key === "C major");
  const hist = m.history();
  check("history lists every change with its source", hist.length === 3 && hist.map((h) => `${h.from}>${h.to}:${h.manual}`).join(",")
    === "null>Eb major:false,Eb major>Gb major:true,Gb major>C major:true", JSON.stringify(hist));
}

// ===================================================================================== signatures on the staff ==
const EXPECT = { C: 0, G: 1, D: 2, A: 3, E: 4, B: 5, "F#": 6, F: -1, Bb: -2, Eb: -3, Ab: -4, Db: -5 };
const REL = { A: "C", E: "G", B: "D", "F#": "A", "C#": "E", "G#": "B", D: "F", G: "Bb", C: "Eb", F: "Ab", Bb: "Db", Eb: "Gb" };
for (const key of KEYS) {
  const [tonic, mode] = key.split(" ");
  const major = mode === "major" ? tonic : REL[tonic];
  const want = major === "Gb" ? -6 : EXPECT[major];
  const s = SP.keySignature(key);
  const got = s.type === "sharps" ? s.count : s.type === "flats" ? -s.count : 0;
  check(`${key}: signature ${want}`, got === want, `${s.type} ${s.count}`);
  for (const clef of ["treble", "bass"]) {
    const places = KS.signaturePlaces(s, clef);
    const lo = clef === "treble" ? 31 : 17, hi = clef === "treble" ? 39 : 25;  // F4..G5 and F2..G3: on the staff or a step off it
    check(`${key}: ${clef} signature places lie on the staff`, places.length === s.count && places.every((p) => p.diatonic >= lo && p.diatonic <= hi
      && mod(p.diatonic, 7) === s.accidentals[places.indexOf(p)].letter), JSON.stringify(places));
  }
  // the key's own notes (natural minor for a minor key) need no accidental; every other pitch class shows one
  const K = SP.keyContext(key);
  const natural = K.natural || K;
  for (let pc = 0; pc < 12; pc++) {
    const sp = SP.spellNote(pc, key);
    const shown = KS.staffAccidental(sp, s);
    const own = natural.scalePcs.has(pc);
    check(`${key}: pitch class ${pc} (${sp.name}) ${own ? "needs no accidental" : "shows an accidental"}`, own ? shown === null : shown !== null, String(shown));
    if (s.type === "flats" && own) check(`${key}: flat key, no sharp on its own note ${sp.name}`, sp.acc <= 0);
  }
}
check("Eb major places: B4 E5 A4 over B2 E3 A2", JSON.stringify(KS.signaturePlaces(SP.keySignature("Eb major"), "treble").map((p) => p.diatonic)) === "[34,37,33]"
  && JSON.stringify(KS.signaturePlaces(SP.keySignature("Eb major"), "bass").map((p) => p.diatonic)) === "[20,23,19]");
check("A major places: F5 C5 G5", JSON.stringify(KS.signaturePlaces(SP.keySignature("A major"), "treble").map((p) => p.diatonic)) === "[38,35,39]");
const sigEb = SP.keySignature("Eb major"), sigF = SP.keySignature("F major"), sigGb = SP.keySignature("Gb major");
check("Ab C Eb Ab in Eb major: no accidental on any note", midis("Ab3 C4 Eb4 Ab4").every((m) => KS.staffAccidental(SP.spellMidi(m, "Eb major"), sigEb) === null));
check("A natural in Eb major draws a natural", KS.staffAccidental({ letter: 5, acc: 0 }, sigEb) === 0);
check("F# in Eb major draws a sharp", KS.staffAccidental({ letter: 3, acc: 1 }, sigEb) === 1);
check("B natural in F major draws a natural", KS.staffAccidental({ letter: 6, acc: 0 }, sigF) === 0);
check("Cb in Gb major needs none; C natural draws a natural", KS.staffAccidental({ letter: 0, acc: -1 }, sigGb) === null && KS.staffAccidental({ letter: 0, acc: 0 }, sigGb) === 0);
check("no signature: a natural needs none, a flat shows its flat", KS.staffAccidental({ letter: 2, acc: 0 }, SP.keySignature(null)) === null
  && KS.staffAccidental({ letter: 2, acc: -1 }, null) === -1);
check("a G♭ passage: its seven notes show no accidental under six flats", [6, 8, 10, 11, 1, 3, 5].every((pc) => KS.staffAccidental(SP.spellNote(pc, "Gb major"), sigGb) === null));

// ============================================================================ the shared Nashville formatter ==
check("nashville.js exports formatNumber", typeof NV.formatNumber === "function");
const f69 = NV.formatNumber("4^6/9");
check("4^6/9: the 4, then 6/9 raised; display 4⁶ᐟ⁹", JSON.stringify(f69.parts) === JSON.stringify([{ role: "degree", acc: 0, num: "4", text: "4" }, { role: "sup", text: "6/9" }])
  && f69.display === "4⁶ᐟ⁹", JSON.stringify(f69));
const db69 = NV.nashvilleFromName("Db6/9", "Ab major");
check("Db6/9 in Ab major is 4 with 6/9 raised (structured and text agree)", db69.text === "4^6/9" && JSON.stringify(NV.formatNumber(db69).parts) === JSON.stringify(f69.parts));
check("no part ever reads 46/9", !NV.formatNumber(db69).parts.some((p) => p.text === "46/9") && !NV.formatNumber(db69).display.includes("46"));
for (const [text, display] of [["b3^6/9/5", "♭3⁶ᐟ⁹/5"], ["5^7/7", "5⁷/7"], ["2m7", "2ᵐ⁷"], ["2-^7", "2⁻⁷"], ["1-3", "1–3"], ["3", "3"], ["#1°7", "♯1°⁷"],
  ["b7^7b9/2", "♭7⁷♭⁹/2"], ["4maj13#11", "4ᵐᵃʲ¹³♯¹¹"], ["4^6/7", "4⁶/7"]]) {
  check(`formatNumber(${text}).display is ${display}`, NV.formatNumber(text).display === display, NV.formatNumber(text).display);
}
check("formatNumber(null) is null; unreadable text is one plain part", NV.formatNumber(null) === null && NV.formatNumber("hello").parts[0].role === "plain");
{  // every template suffix and the reader's colour suffixes, 12 roots, with and without a bass, in major and minor keys
  const suffixes = [...new Set([...Object.keys(NV.TONE_STEPS), "6/9#11", "maj13#11", "maj9#11", "m7(11)", "13sus4", "7b9b13", "+(add9)", "m(add11)", "7#9#5"])];
  const roots = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  let n = 0, bad = [];
  for (const key of ["C major", "Ab major", "A minor", "F# major"]) {
    for (const r of roots) for (const sfx of suffixes) for (const bass of ["", "/E", "/Bb"]) {
      const x = NV.nashvilleFromName(r + sfx + bass, key);
      if (!x || x.kind !== "chord") continue;
      n++;
      const fs = NV.formatNumber(x), ft = NV.formatNumber(x.text);
      const want = [{ role: "degree", text: x.root }, ...(x.suffix ? [{ role: "sup", text: x.suffix }] : []), ...(x.bass ? [{ role: "slash", text: "/" }, { role: "bass", text: x.bass.text }] : [])];
      const shape = (f) => JSON.stringify(f.parts.map((p) => ({ role: p.role, text: p.text })));
      if (shape(fs) !== JSON.stringify(want) || shape(ft) !== shape(fs) || fs.display !== ft.display) bad.push(`${r + sfx + bass} in ${key}: ${x.text} ${shape(fs)} / ${shape(ft)}`);
    }
  }
  report.push(`formatNumber parity: ${n} numbers, structured and text forms agree on ${n - bad.length}`);
  check("formatNumber: the structured and text forms give the same parts for every suffix (the ^ joiner never drawn)", bad.length === 0 && n > 1500, `${bad.length}: ${bad.slice(0, 4).join(" | ")}`);
}

// ======================================================================== piano.js's own spellForKey and numberRuns ==
const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
const THEORY_A = pianoSrc.indexOf("// ===== THEORY BEGIN"), THEORY_B = pianoSrc.indexOf("// ===== THEORY END");
const sliceTheory = () => new Function(pianoSrc.slice(THEORY_A, THEORY_B) + "\nreturn Theory;")();
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
const DECLS = ["spellForKey", "accGlyph", "FONT", "degreeRuns", "suffixRuns", "numberRuns"];
const decls = DECLS.map((n) => [n, declSource(n)]);
check("piano.js declares spellForKey, numberRuns and their helpers", decls.every(([, x]) => x), decls.filter(([, x]) => !x).map(([n]) => n).join(", "));
check("piano.js keeps no speller of its own (spellForKey calls spell.js; no ODD_NAMES rule)", !/const ODD_NAMES/.test(pianoSrc)
  && /spellChord\(/.test(decls[0][1] || "") && /spellNote\(/.test(decls[0][1] || ""));
check("piano.js installs the reader behind arsenal.piano.reader (next | classic, default next)", /installReader\(Theory, NV\)/.test(pianoSrc)
  && /arsenal\.piano\.reader/.test(pianoSrc) && /: "next";/.test(pianoSrc));
if (decls.every(([, x]) => x)) {
  const TP = sliceTheory();
  const reader = installReader(TP, NV);
  const theoryUi = { minor: "tonic" };
  const page = new Function("Theory", "theoryUi", "keyContext", "spellChord", "spellNote", "parseSuffix", "formatNumber",
    `${decls.map(([, x]) => x).join("\n")}\nreturn { spellForKey, numberRuns };`)(TP, theoryUi, SP.keyContext, SP.spellChord, SP.spellNote, parseSuffix, NV.formatNumber);
  const plainInfo = (info) => { const x = { ...info }; delete x.spelledIn; return x; };
  const spPc = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);

  // the Nashville row's runs: a 4, then 6/9 raised
  const runs = page.numberRuns(db69, 76, "#fff");
  check("numberRuns (Db6/9 in Ab major): the 4 on the line, 6/9 raised, no 46/9", runs.length === 2 && runs[0].text === "4" && !(runs[0].dy < 0)
    && runs[1].text === "6/9" && runs[1].dy < 0, JSON.stringify(runs.map((r) => [r.text, r.dy])));
  const slashRuns = page.numberRuns(NV.nashvilleFromName("Eb7b9/G", "Ab major"), 76, "#fff").map((r) => r.text);
  check("numberRuns (Eb7b9/G in Ab major): 5, 7 ♭ 9 raised, /, 7", JSON.stringify(slashRuns) === JSON.stringify(["5", "7", "♭", "9", "/", "7"]), JSON.stringify(slashRuns));

  // the ruling's page case: F A C# G in F# major stays F+(add9), whichever way it reaches spellForKey
  const faug = midis("F3 A3 C#4 G4"), Fs = NV.parseKey("F# major");
  const inKey = reader.detect(faug, Fs.bias, { key: "F# major" }), noKey = reader.detect(faug, Fs.bias, { key: null });
  const a = page.spellForKey(inKey, Fs), b = page.spellForKey(plainInfo(inKey), Fs), c = page.spellForKey(noKey, Fs);
  check("F A C# G in F# major: F+(add9) from the reader, kept by the page (marked, unmarked and from a key-less read)",
    inKey.name === "F+(add9)" && a.name === "F+(add9)" && b.name === "F+(add9)" && c.name === "F+(add9)", [inKey.name, a.name, b.name, c.name].join(" "));
  // the favourite chord and the Db6/9 through the page
  const fav = page.spellForKey(reader.detect(midis("Gb2 Db3 F3 Ab3 Bb3 C4 Eb4"), -1, { key: null }), NV.parseKey("Db major"));
  check("Gb2 Db3 F3 Ab3 Bb3 C4 Eb4 in Db major: Gbmaj13#11 through spellForKey", fav.name === "Gbmaj13#11", fav.name);
  const d69 = page.spellForKey(reader.detect(midis("Db3 F3 Ab3 Bb3 Eb4"), -1, { key: "Ab major" }), NV.parseKey("Ab major"));
  check("Db3 F3 Ab3 Bb3 Eb4 in Ab major: Db6/9", d69.name === "Db6/9", d69.name);
  const eb = page.spellForKey(TP.detectTemplates(midis("Ab3 C4 Eb4 Ab4"), -1), NV.parseKey("Eb major"));
  check("Ab C Eb Ab (templates) in Eb major: Ab, chips Ab C Eb", eb.name === "Ab" && eb.pcNames.join(" ") === "Ab C Eb", `${eb.name} ${eb.pcNames}`);

  // TN2 repair round 1, findings 1 and 3: the viio7 of every minor key, through the page (what the staff draws), needs no
  // accidental on its 3rd, 5th or 7th under the key's signature: the reader's info marked, unmarked, read with no key, and the
  // classic templates' info. G# minor's leading-tone dim7 keeps the key's A#, C# and E (its root F## is written G).
  {
    const bad = [];
    let n = 0;
    for (const keyName of MINOR_KEYS) {
      const K = NV.parseKey(keyName), sig = SP.keySignature(keyName), lt = mod(K.tonic + 11, 12);
      for (const ms of [[48 + lt, 51 + lt, 54 + lt, 57 + lt], [36 + lt, 51 + lt, 57 + lt, 66 + lt]]) {
        const own = reader.detect(ms, K.bias, { key: keyName });
        for (const info of [page.spellForKey(own, K), page.spellForKey(plainInfo(own), K), page.spellForKey(reader.detect(ms, K.bias, { key: null }), K),
          page.spellForKey(TP.detectTemplates(ms, K.bias), K)]) {
          n++;
          const accs = [3, 6, 9].map((iv) => KS.staffAccidental(info.notes.find((x) => mod(x.midi - lt, 12) === iv), sig));
          if (accs.some((a) => a !== null) || !/dim7$/.test(info.name)) bad.push(`${keyName}: ${info.name} (${info.pcNames.join(" ")}) ${accs}`);
        }
      }
    }
    check(`repair round 1: the viio7 of each minor key through the page (${n} infos: marked, unmarked, key-less, classic templates) draws no accidental on its 3rd, 5th or 7th`,
      bad.length === 0 && n === 96, bad.slice(0, 6).join(" | "));
    const gs = page.spellForKey(plainInfo(reader.detect(midis("G2 A#2 C#3 E3"), 1, { key: "G# minor" })), NV.parseKey("G# minor"));
    const gsSig = SP.keySignature("G# minor");
    check("repair round 1 finding 3: G A# C# E in G# minor through the page: Gdim7, chips G A# C# E, no accidental on A#, C# or E",
      gs.name === "Gdim7" && gs.pcNames.join(" ") === "G A# C# E" && gs.notes.filter((x) => x.letter !== 4).every((x) => KS.staffAccidental(x, gsSig) === null), `${gs.name} ${gs.pcNames}`);
  }

  // TN2 repair round 1, finding 2 (LS6: "a G♭ passage shows six flats once in the signature"): the key tracker names pitch
  // class 6 major and 3 minor from the key shown before them. Synthetic passages (each chord struck for 2 s, the page's
  // decaying histogram) through the tracker, the signature model at the tracker's 10 Hz tick, and the page's spellForKey.
  {
    const hold = (tracker, sig, hist, clock, chords, rounds) => {
      let st = null;
      for (let r = 0; r < rounds; r++) chords.forEach((text, ci) => {
        const ms = midis(text);
        for (let s = 0; s < 20; s++) {
          for (let i = 0; i < 12; i++) hist[i] *= Math.exp(-0.1 / 12);
          if (s === 0) for (const m of ms) hist[mod(m, 12)] += 1;
          clock.t = +(clock.t + 0.1).toFixed(3);
          st = tracker.update(hist, clock.t, TP.detect(ms, st && st.key ? st.key.bias : 0));
          sig.update({ t: clock.t, key: st.key, sure: st.confidence === "sure" || st.confidence === "fair", manual: null, bar: null, chord: `${r}.${ci}` });
        }
      });
      return st;
    };
    const scenario = (before, after) => {
      const tracker = NV.createKeyTracker(), sig = KS.createKeySignatureModel(), hist = new Array(12).fill(0), clock = { t: 0 };
      const firstState = before ? hold(tracker, sig, hist, clock, before, 4) : null;
      const first = firstState && firstState.key ? firstState.key.name : null;  // read now: the tracker reuses its state object
      const st = hold(tracker, sig, hist, clock, after, 8);
      const view = sig.view(clock.t);
      return { first, key: st.key ? st.key.name : null, bias: st.key ? st.key.bias : null, sig: view.signature, sigKey: view.key,
               names: after.map((text) => page.spellForKey(reader.detect(midis(text), st.key.bias, { key: st.key.name }), st.key).name) };
    };
    const gb = scenario(["Eb3 G3 Bb3", "Ab2 C3 Eb3", "Bb2 D3 F3 Ab3", "Eb3 G3 Bb3"], ["Gb3 Bb3 Db4", "Cb3 Eb3 Gb3", "Db3 F3 Ab3 Cb4", "Gb3 Bb3 Db4"]);
    check("finding 2: Eb major, then Gb Cb Db7: the tracker names Gb major, the staff settles on six flats, the chords read Gb Cb Db7",
      gb.first === "Eb major" && gb.key === "Gb major" && gb.bias === -1 && gb.sigKey === "Gb major" && gb.sig.type === "flats" && gb.sig.count === 6
      && gb.names.join(" ") === "Gb Cb Db7 Gb", JSON.stringify(gb));
    const fs = scenario(["B2 D#3 F#3", "E3 G#3 B3", "F#2 A#2 C#3 E3", "B2 D#3 F#3"], ["F#3 A#3 C#4", "B2 D#3 F#3", "C#3 E#3 G#3 B3", "F#3 A#3 C#4"]);
    check("finding 2: B major, then F# B C#7: the tracker names F# major, six sharps, the chords read F# B C#7",
      fs.first === "B major" && fs.key === "F# major" && fs.bias === 1 && fs.sigKey === "F# major" && fs.sig.type === "sharps" && fs.sig.count === 6
      && fs.names.join(" ") === "F# B C#7 F#", JSON.stringify(fs));
    const fresh = scenario(null, ["F#3 A#3 C#4", "B2 D#3 F#3", "C#3 E#3 G#3 B3", "F#3 A#3 C#4"]);
    check("finding 2: with no key before, pitch class 6 major keeps its default name (F# major)", fresh.key === "F# major" && fresh.sigKey === "F# major", JSON.stringify(fresh));
    const ds = scenario(["G#2 B2 D#3", "C#3 E3 G#3", "D#3 G3 A#3 C#4", "G#2 B2 D#3"], ["D#3 F#3 A#3", "G#2 B2 D#3", "A#2 D3 E#3 G#3", "D#3 F#3 A#3"]);
    check("finding 2: a sharp key, then a D#-minor passage: pitch class 3 minor (or its relative) is spelled with sharps, never Eb minor's six flats",
      ds.bias === 1 && ds.sig.type === "sharps" && ["D# minor", "F# major"].includes(ds.key), JSON.stringify(ds));
  }

  if (!quick) {
    // every set of 3-6 pitch classes, close and spread, in the 24 keys
    let infos = 0, renamed = 0, notesMoved = 0, doubles = 0, triples = 0, compared = 0, differ = 0, tmplDoubles = 0, tmplTriples = 0, tmplInfos = 0, thrown = 0;
    const samples = { renamed: [], differ: [], doubles: [], tmpl: [] };
    const dbl = (sp) => !!sp && Math.abs(sp.acc) > 1;
    const t0 = Date.now();
    for (let mask = 1; mask < 4096; mask++) {
      const pcs = [];
      for (let bit = 0; bit < 12; bit++) if (mask & (1 << bit)) pcs.push(bit);
      if (pcs.length < 3 || pcs.length > 6) continue;
      const close = pcs.map((p) => 48 + p), spread = [36 + pcs[0], ...pcs.slice(1).map((p, i) => 60 + p + (i % 2 ? 12 : 0))];
      for (const ms of [close, spread]) {
        for (const keyName of KEYS) {
          const K = NV.parseKey(keyName);
          try {
            // 1. idempotent: the reader's info in this key, unmarked, comes back with the same letters
            const own = reader.detect(ms, K.bias, { key: keyName });
            const back = page.spellForKey(plainInfo(own), K);
            infos++;
            if (back.name !== own.name) { renamed++; if (samples.renamed.length < 6) samples.renamed.push(`${ms} ${keyName}: ${own.name} -> ${back.name}`); }
            if (back.notes.some((n, i) => n.name !== own.notes[i].name)) notesMoved++;
            if (back.kind === "chord" && (dbl(back.root) || dbl(back.bass))) { doubles++; if (samples.doubles.length < 6) samples.doubles.push(`${ms} ${keyName}: ${back.name}`); }
            if (back.notes.some((n) => Math.abs(n.acc) > 2)) triples++;
            // 2. one speller: a key-less read of the same chord, respelled by the page in the key, reads the same name
            const loose = page.spellForKey(reader.detect(ms, K.bias, { key: null }), K);
            if (loose.kind === "chord" && own.kind === "chord" && loose.suffix === own.suffix && spPc(loose.root) === spPc(own.root)
                && (loose.bass ? spPc(loose.bass) : null) === (own.bass ? spPc(own.bass) : null)) {
              compared++;
              if (loose.name !== own.name) { differ++; if (samples.differ.length < 6) samples.differ.push(`${ms} ${keyName}: reader ${own.name}, page ${loose.name}`); }
            }
            if (loose.kind === "chord" && (dbl(loose.root) || dbl(loose.bass))) doubles++;
            // 3. classic: the templates' info respelled in the key
            const tmpl = page.spellForKey(TP.detectTemplates(ms, K.bias), K);
            tmplInfos++;
            if (tmpl.kind === "chord" && (dbl(tmpl.root) || dbl(tmpl.bass))) { tmplDoubles++; if (samples.tmpl.length < 6) samples.tmpl.push(`${ms} ${keyName}: ${tmpl.name}`); }
            if (tmpl.notes.some((n) => Math.abs(n.acc) > 2)) tmplTriples++;
          } catch (e) {
            thrown++;
            if (thrown < 3) console.log(`threw on ${ms} ${keyName}: ${e.stack}`);
          }
        }
      }
    }
    report.push(`page spellForKey sweep (${((Date.now() - t0) / 1000).toFixed(1)} s): ${infos} reader infos in the 24 keys, ${renamed} renamed and ${notesMoved} with a note respelled when fed back unmarked; `
      + `${compared} key-less reads of the same chord respelled by the page, ${differ} named otherwise; ${doubles} double-accidental roots or basses; ${triples} triple accidentals; `
      + `classic templates: ${tmplInfos} infos, ${tmplDoubles} double-accidental roots or basses, ${tmplTriples} triples; ${thrown} threw`);
    check("rule 4, one speller: the page never renames the reader's info in its own key (fed back unmarked)", renamed === 0 && notesMoved === 0, `${renamed} renamed, ${notesMoved} notes: ${samples.renamed.join(" | ")}`);
    check("rule 4, one speller: a key-less read respelled by the page names the same chord as the reader in that key", differ === 0 && compared > 50000, `${differ} of ${compared}: ${samples.differ.join(" | ")}`);
    check("rule 5 on the page: 0 double accidentals on a root or bass, 0 triples (reader infos)", doubles === 0 && triples === 0, `${doubles} doubles, ${triples} triples: ${samples.doubles.join(" | ")}`);
    check("rule 5 on the page: 0 double accidentals on a root or bass, 0 triples (classic templates)", tmplDoubles === 0 && tmplTriples === 0, `${tmplDoubles} doubles, ${tmplTriples} triples: ${samples.tmpl.join(" | ")}`);
    check("spellForKey never throws", thrown === 0, String(thrown));
  }
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
