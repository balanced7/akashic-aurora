// The voicing bridge for Claude's hand on the piano: arsenal/pianocue_voicing.mjs (node, no dependencies).
//
// It runs the THEORY block and spellForKey of arsenal/web/piano.js and arsenal/web/piano/nashville.js themselves, so
// every name, spelling and Nashville number it prints is the one the page would show.
//
//   echo '{"items": ["Abmaj9#11", "5^7sus4/1"], "key": "Eb major", "voicing": "spread"}' | node arsenal/pianocue_voicing.mjs
//   node arsenal/pianocue_voicing.mjs "Bb7sus4/Eb" --key "Eb major" --voicing drop2
//
// Request: { items: [text], key: "Eb major" | null, voicing: close|open|spread|drop2|shell, octave: int | null,
//            voice_lead: bool, minor: "tonic" | "relative" }  or  { check: true } (the suffix reader against every
//            Theory.TEMPLATES suffix).
// An item is a chord name ("Abmaj9#11", "Bb7sus4/Eb", "Ebm(add9)/Bb"), a Nashville number with a key ("1", "4", "b3",
// "4maj9#11", "b7maj9", "5^7sus4/1"; tonic numbering with major-scale accidentals, as nashville.js), or notes
// ("Ab3 Eb4 G4" or MIDI numbers 21..108; one token like "E4" is a note, but "G5", "C7" read as chords, as nashville.js
// parseChord does). A lone token that starts like a number (1-7, optionally after b/bb/#/##: "5", "b3", "#4m7") is
// always a number, never a note or a MIDI value; a lone number needs a key. With a key every label is the name the
// page would show (piano.js spellForKey): a number's chord ("b6" in Eb major is B, not Cb; see pageSpelledName), a
// typed chord name ("Ab7" in C# minor is G#7, beside 5^7), and notes, intervals and clusters ("Db4 F4" in A major is
// C#-E#). Without a key a typed name keeps its spelling. The result's number_typed keeps a number as typed. Dash minor
// ("C-7", "Bb-7", "Eb-") is a minor chord. A lone two-digit token with a key ("57") is a MIDI note, with a warning;
// one off the keyboard that looks like a number without its ^ ("17") says so ("did you mean 1^7?").
// A number's suffix may start with an accidental ("5b9", "7b5", "4#11", "5^b9"): its chord is built from the number's
// root, suffix and bass as parts, never by gluing the root's name to the suffix and reading that text back ("G" + "b9"
// reads as Gb9). A suffix that starts with an accidental is written in parentheses, so the name reads back as itself:
// 5b9 in C major is G(b9), which the page has no name for (a warning says so). minor: "tonic" (the page's default) or
// "relative" (the page's arsenal.piano.minor pref, so labels and numbers match a page set to it): a minor key is then
// numbered from its relative major, both ways ("6m" in A minor is Am, and Am reads back as 6m).
//
// Voicings (a slash bass is always the lowest note; without --octave it never sits below C2, and the upper voices move
// up an octave rather than crowd a low bass):
//   close   root position, root between F3 and E4 (or in --octave), chord tones in one octave, tensions stacked above
//   open    root between F2 and E3, then the 5th, the 3rd an octave up, the 7th, tensions above
//   spread  Daniel-style: bass in octave 2, a shell (3rd and 7th, or root and 7th over a foreign bass) in the middle,
//           colour tones on top, about 2.5 octaves
//   drop2   four upper voices in close position with the second from the top dropped an octave, bass below; with more
//           than four tones the 3rd, 7th and the highest named tension (13 over 11 over 9) are kept first. A triad,
//           sus or power chord doubles its root on top instead of a 7th (C: C3 | G3 C4 E4 C5, the C7 drop-2 shape with
//           the octave in place of the 7th; C5: C3 | G3 C4 C5)
//   shell   root between F2 and E3, 3rd and 7th (R-7-3 low, R-3-7 higher), tensions on top
// octave N puts the chord's root in octave N (spread: the bass); a slash bass goes below it, and drop2's dropped voice
// and its bass land in octave N-1 (drop2 "C" with octave 3 is C2 G2 C3 E3 C4, as "C7" is C2 G2 C3 E3 Bb3). A slash
// bass that would land below octave N-1 while the lowest upper voice already sounds its pitch is that voice (drop2
// "C/G" with octave 3 is G2 C3 E3 C4, not G1 G2 C3 E3 C4).
// Voice leading (voice_lead): the bass stays where the style puts it; the upper voices take the rotation or octave
// with the least movement from the previous chord (a min-cost matching of notes), never more than the plain voicing,
// never with a repeated note, within 7 semitones of the plain voicing's register and without adding low-interval
// crowding (2nds below Eb3, 3rds below C3/Bb2, 4ths below A2, 5ths below Bb1). Warnings report a named tension the
// voicing leaves out, low-interval crowding, and a voicing the page reads as another chord (a shell C7#11 reads C7b5),
// naming the styles the page does read as the chord.
// Round trip: Theory.detect(notes) must name the chord. When the first voicing reads as something else, variants of
// the same voicing (a doubled bass pitch class or a natural 5th left out) are tried; if none reads exactly, the
// voicing is kept and the reading reported (match "exact"; "enharmonic": the same chord spelled another way, which
// the page respells in the shown key (page_name); "equivalent": these notes under another chord name; "unnamed": the
// page reads a cluster). roundtrip.omits lists chord tones the voicing leaves out (usually the natural 5th).
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const src = readFileSync(here("./web/piano.js"), "utf8");
const A = src.indexOf("// ===== THEORY BEGIN"), B = src.indexOf("// ===== THEORY END");
if (A < 0 || B <= A) {
  process.stdout.write(JSON.stringify({ ok: false, error: "the THEORY markers are missing from arsenal/web/piano.js" }));
  process.exit(1);
}
const Theory = new Function(src.slice(A, B) + "\nreturn Theory;")();
const NV = await import(pathToFileURL(here("./web/piano/nashville.js")).href);

const { LETTERS, LETTER_PC, mod, pcOf, nameOf, octaveOf, spellInterval, TEMPLATES } = Theory;
const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const STYLES = ["close", "open", "spread", "drop2", "shell"];
const ODD_NAMES = new Set(["E#", "B#", "Cb", "Fb"]);
const LO = 21, HI = 108;

// ------------------------------------------------------------------ parsing --
const clean = (s) => String(s).trim().replace(/♭/g, "b").replace(/♯/g, "#").replace(/Δ/g, "maj").replace(/\s+/g, " ");
const NOTE_OCT = /^([A-Ga-g])(#{1,2}|b{1,2})?(-?\d)$/;
const CHORD_DIGITS = new Set(["5", "6", "7", "9"]);  // "G5", "C7": chords, as parseChord reads them

function noteToMidi(tok) {
  const m = NOTE_OCT.exec(tok);
  if (!m) return null;
  const letter = LETTERS.indexOf(m[1].toUpperCase());
  const acc = !m[2] ? 0 : m[2][0] === "#" ? m[2].length : -m[2].length;
  return { midi: (Number(m[3]) + 1) * 12 + LETTER_PC[letter] + acc, sp: { letter, acc } };
}

// A lone token that starts like a Nashville number: "1", "5", "b3", "#4m7", "5^7sus4/1" (not "13", not "B3").
const NUMBERISH = /^(#{1,2}|b{1,2})?[1-7](?!\d)/;

function readNotes(text, hasKey = false) {
  const toks = text.split(/[\s,]+/).filter(Boolean);
  if (!toks.length) return null;
  const out = [];
  for (const t of toks) {
    if (/^\d{1,3}$/.test(t)) { out.push({ midi: Number(t), sp: null }); continue; }
    const n = noteToMidi(t);
    if (!n) return null;
    if (toks.length === 1 && CHORD_DIGITS.has(t.replace(/^[A-Ga-g](#{1,2}|b{1,2})?/, ""))) return null;
    out.push(n);
  }
  for (const n of out) {
    if (n.midi >= LO && n.midi <= HI) continue;
    if (toks.length > 1 && toks.every((t) => NUMBERISH.test(t))) {
      throw new Error(`"${text}" looks like Nashville numbers: give one number per chord (a progression "${toks.join(" | ")}")`);
    }
    // "17" is no key, but it looks like a Nashville number written without its ^ ("1^7": the 1 chord with a 7th)
    const glued = toks.length === 1 && /^([1-7])(5|6|7|9|11|13)$/.exec(toks[0]);
    const hint = glued ? `; did you mean the Nashville number "${glued[1]}^${glued[2]}"${hasKey ? "" : " (a number needs --key)"}?` : "";
    throw new Error(`${n.midi} is off the keyboard (MIDI ${LO}..${HI})${hint}`);
  }
  return out;
}

// Low-interval limits: the lowest note an interval of 1..7 semitones sounds clear from (2nds Eb3/E3, 3rds C3/Bb2,
// 4th A2, tritone Bb2, 5th Bb1). Sixths and sevenths are left alone: Eb2 under Db3 is everyday piano.
const LIL = { 1: 52, 2: 51, 3: 48, 4: 46, 5: 45, 6: 46, 7: 34 };
function lowBreaks(notes) {
  const out = [];
  for (let i = 0; i < notes.length; i++) {
    for (let j = i + 1; j < notes.length; j++) {
      const iv = notes[j] - notes[i];
      if (iv > 7) break;  // notes are sorted
      if (iv >= 1 && notes[i] < LIL[iv]) out.push([notes[i], notes[j]]);
    }
  }
  return out;
}

function normalizeSuffix(raw) {
  let s = clean(raw).replace(/\s/g, "");
  s = s.replace(/^(°7|o7)/, "dim7").replace(/^(°|o(?=$|[#b\d(]))/, "dim").replace(/^ø7?/, "m7b5").replace(/^\+/, "aug");
  s = s.replace(/^mM(?=7|9|11|13)/, "m(maj").replace(/^mM/, "m(maj");
  if (/^m\(maj[0-9]+$/.test(s)) s += ")";
  s = s.replace(/^min(?!or)/, "m").replace(/^-/, "m").replace(/^M(?=aj|\d)/, "maj").replace(/^Maj/, "maj");
  s = s.replace(/^majaj/, "maj");
  return s;
}

// The chord tones of a suffix: Map role -> [semitones, letter steps] above the root.
function tonesOf(suffix) {
  const s = normalizeSuffix(suffix).replace(/[(),]/g, "");
  const tones = new Map([["root", [0, 0]], ["third", [4, 2]], ["fifth", [7, 4]]]);
  let i = 0, dim = false, maj = false;
  const eat = (re) => { const m = re.exec(s.slice(i)); if (m) i += m[0].length; return m; };
  if (eat(/^dim/)) { dim = true; tones.set("third", [3, 2]); tones.set("fifth", [6, 4]); }
  else if (eat(/^aug/)) tones.set("fifth", [8, 4]);
  else if (eat(/^m(?!aj)/)) tones.set("third", [3, 2]);
  if (eat(/^maj/)) maj = true;
  const seventh = () => tones.set("seventh", maj ? [11, 6] : dim ? [9, 5] : [10, 6]);
  const num = eat(/^(6\/9|69|13|11|9|7|6|5)/);
  if (num) {
    const n = num[1].replace("/", "");
    if (n === "5") tones.delete("third");
    else if (n === "6") tones.set("sixth", [9, 5]);
    else if (n === "69") { tones.set("sixth", [9, 5]); tones.set("ninth", [2, 1]); }
    else if (n === "7") seventh();
    else if (n === "9") { seventh(); tones.set("ninth", [2, 1]); }
    else if (n === "11") { seventh(); tones.set("ninth", [2, 1]); tones.set("eleventh", [5, 3]); }
    else if (n === "13") { seventh(); tones.set("ninth", [2, 1]); tones.set("thirteenth", [9, 5]); }
  } else if (maj && eat(/^$/)) { /* "Cmaj" is a major triad */ }
  const shift = (a) => (a === "#" ? 1 : a === "b" ? -1 : 0);
  const tension = (acc, deg) => {
    const d = { 2: "9", 9: "9", 4: "11", 11: "11", 6: "13", 13: "13" }[deg];
    if (d === "9") tones.set("ninth", [2 + shift(acc), 1]);
    else if (d === "11") tones.set("eleventh", [5 + shift(acc), 3]);
    else tones.set(tones.has("seventh") ? "thirteenth" : "sixth", [9 + shift(acc), 5]);
  };
  while (i < s.length) {
    let m;
    if ((m = eat(/^sus(2|4)?/))) { tones.delete("third"); tones.set("sus", m[1] === "2" ? [2, 1] : [5, 3]); continue; }
    if ((m = eat(/^add(b|#)?(2|4|6|9|11|13)/))) { tension(m[1], m[2]); continue; }
    if ((m = eat(/^(b|#)5/))) { tones.set("fifth", [7 + shift(m[1]), 4]); continue; }
    if ((m = eat(/^(b|#)(9|11|13)/))) { tension(m[1], m[2]); continue; }
    if ((m = eat(/^(9|11|13)/))) { tension("", m[1]); continue; }
    if ((m = eat(/^(no|omit)(3|5)/))) { tones.delete(m[2] === "3" ? "third" : "fifth"); continue; }
    throw new Error(`cannot read the chord suffix "${suffix}" (stuck at "${s.slice(i)}")`);
  }
  if (tones.has("sus") && tones.has("ninth") && tones.get("sus")[0] === 2 && tones.get("ninth")[0] === 2) tones.delete("sus");
  return tones;
}

const semisKey = (tones) => [...new Set([...tones.values()].map((t) => mod(t[0], 12)))].sort((a, b) => a - b).join(",");

// The suffix the page writes for these tones (Theory.TEMPLATES), or the normalized input when no template has them.
function canonicalSuffix(suffix, tones) {
  const key = semisKey(tones);
  const norm = normalizeSuffix(suffix);
  const hits = TEMPLATES.filter((t) => t.key === key);
  // detect names a bare root and 5th itself ("G3 D4" reads G5), outside TEMPLATES
  if (!hits.length) return key === "0,7" ? { suffix: "5", template: true } : { suffix: norm, template: false };
  return { suffix: (hits.find((t) => t.suffix === norm) || hits[0]).suffix, template: true };
}

// "4maj9#11", "b7maj9", "5^7sus4/1", "2-^7", "7ø7", "#4°7", "5b9" in a key -> the chord's parts { root, suffix, bass }
// (spellings, and the suffix text). Parts, not a name: "5b9" in C major is G with suffix b9; the text "Gb9" would read
// back as a G-flat 9th chord. minor "relative" numbers a minor key from its relative major ("6m" in A minor is Am).
const NUMBER = /^(#{1,2}|b{1,2})?([1-7])(.*)$/;
function numberParts(text, keyName, minor = "tonic") {
  const key = NV.parseKey(keyName);
  if (!key) throw new Error(`a Nashville number needs a readable key (--key "Eb major"), got ${JSON.stringify(keyName)}`);
  const keySp = noteToMidi(key.name.split(" ")[0] + "4").sp;
  const relative = /minor$/.test(key.name) && minor === "relative";
  const tonicSp = relative ? { letter: mod(keySp.letter + 2, 7), acc: 0 } : keySp;  // (only the letter is used)
  const tonicPc = relative ? mod(key.tonic + 3, 12) : key.tonic;
  const m = NUMBER.exec(text);
  let rest = m[3];
  let bass = null;
  const bm = /\/(#{1,2}|b{1,2})?([1-7])$/.exec(rest);
  if (bm) { bass = { acc: bm[1] ? (bm[1][0] === "#" ? bm[1].length : -bm[1].length) : 0, degree: Number(bm[2]) }; rest = rest.slice(0, bm.index); }
  rest = rest.replace(/^\^/, "").replace(/^-\^?/, "m");
  const spell = (degree, acc) => {
    const letter = mod(tonicSp.letter + degree - 1, 7);
    const pc = mod(tonicPc + MAJOR[degree - 1] + acc, 12);
    const a = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
    // "#7" in G# minor would be F###: take the plain spelling of that pitch; the page's spelling is applied after
    if (Math.abs(a) > 2) return Theory.spellAlone(pc, key.bias);
    return { letter, acc: a };
  };
  const root = spell(Number(m[2]), m[1] ? (m[1][0] === "#" ? m[1].length : -m[1].length) : 0);
  const bassSp = bass ? spell(bass.degree, bass.acc) : null;
  return { root, suffix: normalizeSuffix(rest), bass: bassSp };
}
const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
// "2-^7" and "2m7" are one number, and so are "5b9" and "5(b9)"
const bare = (t) => String(t || "").replace(/\^/g, "").replace(/-/g, "m").replace(/[()]/g, "");
// A suffix is written after a root name; one that starts with an accidental goes in parentheses, or "G" + "b9" would
// read as Gb9 (the page's own names never start a suffix with one: Theory.TEMPLATES has no such suffix)
const shownSuffix = (suffix) => (/^[#b]/.test(suffix) ? `(${suffix})` : suffix);
// Two numbers that name one chord in a key, written two ways ("2m7b5" and "2ø7", "5#5" and "5+"): the same root, bass
// and tones. A typed number that the page writes the other way is not worth a warning.
function sameChord(a, b, keyName, minor) {
  try {
    const [x, y] = [a, b].map((t) => chordFromParts(numberParts(t, keyName, minor)));
    return x.rootPc === y.rootPc && x.bassPc === y.bassPc && semisKey(x.tones) === semisKey(y.tones);
  } catch { return false; }
}

// ------------------------------------------------------------------ voicing --
const above = (pc, min) => min + mod(pc - min, 12);            // lowest midi >= min with this pitch class
const below = (pc, max) => max - mod(max - pc, 12);            // highest midi <= max with this pitch class
const rootIn = (pc, octave, lo) => (octave == null ? above(pc, lo) : (octave + 1) * 12 + pc);

// Place tones one after another, each the first instance strictly above the previous note (or >= start for the first).
function stack(pcs, start) {
  const out = [];
  for (const pc of pcs) out.push(out.length ? above(pc, out[out.length - 1] + 1) : above(pc, start));
  return out;
}

function roles(chord) {
  const t = chord.tones;
  const get = (...names) => names.map((n) => (t.has(n) ? { role: n, pc: mod(chord.rootPc + t.get(n)[0], 12), semis: t.get(n)[0] } : null)).filter(Boolean);
  const fifth = get("fifth")[0] || null;
  return {
    root: get("root")[0],
    third: get("third", "sus")[0] || null,
    seventh: get("seventh", "sixth")[0] || null,
    fifth,
    alteredFifth: fifth && fifth.semis !== 7 ? fifth : null,
    colours: get("ninth", "eleventh", "thirteenth").sort((a, b) => a.semis - b.semis),
    all: [...t.keys()].map((n) => get(n)[0]),
  };
}

const BASS_FLOOR = 36;  // C2: a slash bass below it (with a 6th or 9th right above) is mud on any piano

// Put a slash bass under the upper voices. Without --octave the bass sits at C2 or above, with at least a 4th and no
// low-interval crowding up to the lowest upper voice. lift "all" moves the whole upper structure up an octave until
// that holds (close, drop2: their shape is the point); lift "voice" moves only the crowding lowest voice up an octave
// (open, shell: already wide, so the top stays where it was instead of climbing past G6).
function withBass(chord, upper, octave = null, lift = "all") {
  let notes = [...upper].sort((a, b) => a - b);
  if (chord.bassPc === chord.rootPc && mod(notes[0], 12) === chord.rootPc) return notes;
  let bass = below(chord.bassPc, notes[0] - 5);
  // --octave N: a bass that would sit below octave N-1 while the lowest upper voice already sounds its pitch (drop2's
  // dropped 5th over a /5 bass) is that voice, not a second copy an octave under it
  if (octave != null && bass < octave * 12 && mod(notes[0], 12) === chord.bassPc) return notes;
  if (octave == null) {
    if (bass < BASS_FLOOR) bass = above(chord.bassPc, BASS_FLOOR);
    const crowded = () => notes[0] - bass < 5 || lowBreaks([bass, notes[0]]).length > 0;
    while (notes.length && crowded()) {
      if (lift === "all") notes = notes.map((n) => n + 12);
      else {
        const up = notes.shift() + 12;
        if (!notes.includes(up)) notes.push(up);  // an octave already there: the voice is simply not doubled
        notes.sort((a, b) => a - b);
      }
    }
  }
  return [bass, ...notes];
}

const VOICERS = {
  close(chord, octave) {
    const r = roles(chord);
    const root = rootIn(chord.rootPc, octave, 53);
    const core = r.all.filter((x) => !["ninth", "eleventh", "thirteenth"].includes(x.role)).sort((a, b) => a.semis - b.semis);
    const notes = core.map((x) => root + x.semis);
    let top = Math.max(...notes);
    for (const c of r.colours) { top = above(c.pc, top + 1); notes.push(top); }
    return withBass(chord, notes, octave);
  },
  open(chord, octave) {
    const r = roles(chord);
    const root = rootIn(chord.rootPc, octave, 41);
    const notes = [root];
    let top = root;
    if (r.fifth) { top = root + r.fifth.semis; notes.push(top); }
    if (r.third) { top = above(r.third.pc, Math.max(top + 1, root + 12)); notes.push(top); }
    if (r.seventh) { top = above(r.seventh.pc, top + 1); notes.push(top); }
    for (const c of r.colours) { top = above(c.pc, top + 1); notes.push(top); }
    return withBass(chord, notes, octave, "voice");
  },
  spread(chord, octave) {
    const r = roles(chord);
    const bassOct = octave == null ? 2 : octave;
    const bass = (bassOct + 1) * 12 + chord.bassPc;
    const slash = chord.bassPc !== chord.rootPc;
    const pool = slash ? [r.root, r.seventh, r.third, r.fifth] : [r.third, r.seventh, r.fifth, r.root];
    const middle = pool.filter((x) => x && x.pc !== chord.bassPc).slice(0, 2);
    const start = Math.max(bass + 7, (bassOct + 2) * 12);
    let mid = [];
    if (middle.length === 2) {
      const a = stack([middle[0].pc, middle[1].pc], start), b = stack([middle[1].pc, middle[0].pc], start);
      const cost = (v) => v[1] + (v[1] - v[0] < 3 ? 12 : 0);  // lowest top, but no 2nd crushed into the middle
      mid = cost(a) < cost(b) || (cost(a) === cost(b) && a[0] <= b[0]) ? a : b;
    } else if (middle.length === 1) mid = [above(middle[0].pc, start)];
    const used = new Set([...middle.map((x) => x.role)]);
    let topTones = [...r.colours, r.third, r.alteredFifth, r.seventh]
      .filter((x) => x && !used.has(x.role) && x.pc !== chord.bassPc);
    topTones = [...new Map(topTones.map((x) => [x.role, x])).values()];
    if (topTones.length < 2 && r.fifth && !used.has("fifth") && r.fifth.pc !== chord.bassPc && !topTones.includes(r.fifth)) topTones.push(r.fifth);
    if (!topTones.length && chord.rootPc !== chord.bassPc && !used.has("root")) topTones.push(r.root);
    if (!topTones.length) topTones.push(r.root);
    topTones.sort((x, y) => mod(x.semis, 12) - mod(y.semis, 12));
    const midTop = mid.length ? mid[mid.length - 1] : bass + 7;
    let top = stack(topTones.map((x) => x.pc), midTop + 3);
    if (top[top.length - 1] - bass > 38 && top[0] - 12 > midTop) top = top.map((n) => n - 12);
    return [bass, ...mid, ...top].sort((a, b) => a - b);
  },
  drop2(chord, octave) {
    const r = roles(chord);
    let four;
    const slash = chord.bassPc !== chord.rootPc;
    if (r.all.length <= 3) {
      // No fourth tone to drop: the root doubles an octave up as the top voice (the close stack is root, 3rd, 5th,
      // root), the second from the top drops an octave, and the root goes in the bass. Stacking by pitch class, as
      // below, would put the doubled root an octave over the first and the whole chord an octave too high.
      const root = rootIn(chord.rootPc, octave, 53);
      const close = [...new Set([...r.all.map((x) => mod(x.semis, 12)), 12])].sort((a, b) => a - b).map((s) => root + s);
      close[close.length - 2] -= 12;
      return withBass(chord, close, octave);
    }
    if (r.all.length === 4) four = r.all.map((x) => x.semis);
    else {
      // Over a foreign bass the root must stay in the upper voices (the bass cannot say which chord it is under),
      // and a tone the bass already sounds is not spent on a voice. The highest named tension goes first (13 over 11
      // over 9): the 9th is the one to lose, never the 13th of a 13 chord or the 11th of an 11 chord.
      const ORDER = ["thirteenth", "eleventh", "ninth"];
      const colours = [...r.colours].sort((a, b) => ORDER.indexOf(a.role) - ORDER.indexOf(b.role));
      // An 11 chord with a major 3rd (C11): the 3rd sits a minor 9th under the natural 11th, so it is the tone to
      // leave out (the chord sounds as C9sus4), and the 9th stays.
      const avoid3 = chord.tones.has("third") && chord.tones.get("third")[0] === 4 && chord.tones.has("eleventh") && chord.tones.get("eleventh")[0] === 5;
      const pick = slash
        ? (avoid3 ? [r.root, r.seventh, ...colours, r.third, r.fifth] : [r.root, r.third, r.seventh, ...colours, r.fifth])
        : [r.third, r.seventh, ...colours, r.fifth, r.root];
      four = [...new Map(pick.filter((x) => x && !(slash && x.pc === chord.bassPc)).map((x) => [x.role, x])).values()]
        .slice(0, 4).map((x) => x.semis);
    }
    const pcs = [...four].sort((a, b) => mod(a, 12) - mod(b, 12) || a - b).map((s) => mod(chord.rootPc + s, 12));
    const lowRoot = rootIn(chord.rootPc, octave, 53);
    const close = stack(pcs, above(pcs[0], lowRoot - (octave == null ? 0 : 0)));
    close.sort((a, b) => a - b);
    close[close.length - 2] -= 12;
    return withBass(chord, close, octave);
  },
  shell(chord, octave) {
    const r = roles(chord);
    const root = rootIn(chord.rootPc, octave, 41);
    const guide = [r.third, r.seventh || r.fifth].filter(Boolean);
    const notes = [root];
    if (guide.length === 2) {
      const order = root <= 50 ? [guide[1], guide[0]] : guide;
      notes.push(...stack(order.map((x) => x.pc), root + 1));
    } else if (guide.length === 1) notes.push(above(guide[0].pc, root + 1));
    let top = Math.max(...notes);
    const tensions = [...r.colours, r.alteredFifth].filter(Boolean).filter((x) => !guide.includes(x)).sort((a, b) => a.semis - b.semis);
    if (!tensions.length && r.fifth && !guide.includes(r.fifth)) tensions.push(r.fifth);
    for (const c of tensions) { top = above(c.pc, top + 1); notes.push(top); }
    return withBass(chord, notes, octave, "voice");
  },
};

function fit(notes) {
  let out = [...new Set(notes)].sort((a, b) => a - b);
  while (out[out.length - 1] > HI) out = out.map((n) => n - 12);
  while (out[0] < LO) out = out.map((n) => n + 12);
  return out;
}

// ---------------------------------------------------------- page spelling --
// The name the page shows for a chord in a key. The page names what Theory.detect reads (the root spelled with the
// key's bias, never with a double accidental, never an E#, B#, Cb or Fb root), then respells it in the shown key
// (piano.js spellForKey, pageName below). A Nashville number spelled straight from the key can land on names the page
// never shows ("b6" in Eb major is Cb, "b2" in Db major Ebb), so a number's chord is renamed through the same two steps.
// detect reads the chord's own tones in root position (all of them when detect names the same chord, else the triad
// or power-chord core); a bass that is no chord tone is spelled as detect spells a foreign bass.
const cost0 = (sp) => (Math.abs(sp.acc) === 2 ? 3 : Math.abs(sp.acc)) + (ODD_NAMES.has(nameOf(sp)) ? 1 : 0);  // spellCost(sp, 0)
function pageSpelledName(chord, keyName, bias) {
  const tones = [...chord.tones.values()];
  const read = (semis, suffix) => {
    const notes = [...new Set(semis.map((s) => mod(s, 12)))].map((s) => 48 + chord.rootPc + s);
    const info = Theory.detect(notes, bias);
    return info && info.kind === "chord" && pcOf(info.root) === chord.rootPc && (suffix === null || info.suffix === suffix) ? info : null;
  };
  const core = ["root", "third", "sus", "fifth"].filter((role) => chord.tones.has(role)).map((role) => chord.tones.get(role)[0]);
  const hit = read(tones.map((t) => t[0]), chord.suffix) || read(core, null);
  const root = hit ? { letter: hit.root.letter, acc: hit.root.acc } : Theory.spellAlone(chord.rootPc, bias);
  // each note with a midi in one octave: spellForKey keys its spellings by the notes' pitch classes
  const withMidi = (sp) => ({ letter: sp.letter, acc: sp.acc, midi: 48 + pcOf(sp) });
  const notes = tones.map(([semis, steps]) => withMidi(spellInterval(root, semis, steps)));
  let bass = null;
  if (chord.bassPc !== chord.rootPc) {
    const semis = mod(chord.bassPc - chord.rootPc, 12);
    const tone = tones.find(([s]) => mod(s, 12) === semis);
    bass = spellInterval(root, semis, tone ? tone[1] : IV_STEPS[semis]);
    if (cost0(bass) > 1) bass = Theory.spellAlone(chord.bassPc, bias);
    notes.push(withMidi(bass));
  }
  const info = { kind: "chord", root, suffix: chord.suffix, bass, notes,
                 name: nameOf(root) + shownSuffix(chord.suffix) + (bass ? "/" + nameOf(bass) : "") };
  return pageSpell(info, keyName);  // { name, root, bass }: the chord is rebuilt from these spellings, never from name
}
const IV_STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6];

// ------------------------------------------------------------- reading back --
// The name the page shows for a reading (chord, note, interval or cluster) in the shown key: piano.js's own
// spellForKey, run out of the file as the THEORY block is (with Theory, nashville.js's spellInKey, the page's default
// "tonic" minor numbering and ODD_NAMES), so labels follow the page even when that function changes (it did on
// 2026-09-14: an interval's top note now keeps plain letters, C#4 D4 in C major reads Db-D, not Db-Ebb). If it is
// missing or fails a probe, pageNameOwn, a copy of it, stands in and --check says which is used. PIANOCUE_OWN_SPELLING=1
// forces the copy (tests/test_arsenal_pianocue.py checks both against the page's function). Without a key: detect's name.
let PAGE_SPELL_WHY = null;
const THEORY_UI = { minor: "tonic" };  // the page's theoryUi as spellForKey reads it: minor follows each request (run)
const PAGE_SPELL = (() => {
  if (process.env.PIANOCUE_OWN_SPELLING === "1") { PAGE_SPELL_WHY = "PIANOCUE_OWN_SPELLING=1"; return null; }
  const s0 = src.indexOf("function spellForKey(info, key) {"), s1 = s0 < 0 ? -1 : src.indexOf("\n}\n", s0);
  if (s1 < 0) { PAGE_SPELL_WHY = "spellForKey was not found in arsenal/web/piano.js"; return null; }
  try {
    const fn = new Function("Theory", "spellInKey", "theoryUi", "ODD_NAMES", `${src.slice(s0, s1 + 2)}\nreturn spellForKey;`)(
      Theory, NV.spellInKey, THEORY_UI, ODD_NAMES);
    const probe = fn(Theory.detect([56, 60, 63, 67], 0), NV.parseKey("C# minor"));  // Abmaj7 in C# minor
    if (!probe || typeof probe.name !== "string") throw new Error("it returned no name");
    return fn;
  } catch (e) {
    PAGE_SPELL_WHY = `spellForKey from arsenal/web/piano.js failed: ${e.message || e}`;
    return null;
  }
})();
// pageSpell: { name, root, bass } as the page shows the reading (root and bass: spellings, for chords and notes).
const asShown = (info) => ({ name: info.name, root: info.root || null, bass: info.bass || null });
function pageSpell(info, keyName) {
  if (!info) return null;
  const key = keyName ? NV.parseKey(keyName) : null;
  if (!key) return asShown(info);
  if (PAGE_SPELL) {
    try {
      const shown = PAGE_SPELL(info, key);
      if (shown && typeof shown.name === "string") return asShown(shown);
    } catch (e) {
      if (!PAGE_SPELL_WHY) PAGE_SPELL_WHY = `spellForKey from arsenal/web/piano.js threw: ${e.message || e}`;
    }
  }
  return pageSpellOwn(info, keyName);
}
function pageName(info, keyName) {
  const shown = pageSpell(info, keyName);
  return shown ? shown.name : null;
}
function pageSpellOwn(info, keyName) {
  if (!info) return null;
  if (!keyName || !NV.parseKey(keyName)) return asShown(info);
  const inKey = (sp, suffix = null) => {
    const s = NV.spellInKey(sp, keyName, { suffix, minor: THEORY_UI.minor });
    return s && (s.inScale || (Math.abs(s.acc) <= 1 && !ODD_NAMES.has(nameOf(s)))) ? { letter: s.letter, acc: s.acc } : { letter: sp.letter, acc: sp.acc };
  };
  const moved = (sp, by) => { const letter = mod(sp.letter + by, 7); return { letter, acc: mod(pcOf(sp) - LETTER_PC[letter] + 6, 12) - 6 }; };
  const pcOfNote = (n) => (Number.isInteger(n.midi) ? mod(n.midi, 12) : pcOf(n));  // detect's notes, or bare spellings
  const map = new Map();  // pitch class -> spelling
  if (info.kind === "cluster") {
    for (const n of info.notes) if (!map.has(pcOfNote(n))) map.set(pcOfNote(n), inKey(n));
  } else {
    const root = inKey(info.root, info.kind === "chord" ? info.suffix : null);
    const by = root.letter - info.root.letter;
    for (const n of info.notes) if (!map.has(pcOfNote(n))) map.set(pcOfNote(n), moved(n, by));
    // a slash bass and an interval's top note keep plain letters where the move would need a double accidental
    for (const x of [info.bass, info.upper]) if (x && Math.abs(map.get(pcOf(x)).acc) > 1) map.set(pcOf(x), inKey(x));
  }
  if ([...map.values()].some((s) => Math.abs(s.acc) > 2)) return asShown(info);
  const at = (sp) => map.get(pcOf(sp));
  const shown = (name) => ({ name, root: info.kind === "cluster" ? null : at(info.root), bass: info.bass ? at(info.bass) : null });
  if (info.kind === "cluster") return shown([...new Set(info.notes.map(pcOfNote))].map((pc) => nameOf(map.get(pc))).join(" "));
  if (info.kind === "note") return shown(nameOf(at(info.root)) + (info.notes.length === 1 ? octaveOf(info.notes[0].midi, at(info.root)) : ""));
  if (info.kind === "interval") return shown(`${nameOf(at(info.root))}-${nameOf(at(info.upper))}`);
  return shown(nameOf(at(info.root)) + info.suffix + (info.bass ? "/" + nameOf(at(info.bass)) : ""));
}

function readBack(chord, notes, keyName, bias) {
  const info = Theory.detect(notes, bias);
  let match = "unnamed";  // the page reads a cluster, an interval or a note
  if (info && info.kind === "chord") {
    const same = pcOf(info.root) === chord.rootPc && info.suffix === chord.suffix
      && (chord.bassPc === chord.rootPc ? !info.bass : !!info.bass && pcOf(info.bass) === chord.bassPc);
    match = same ? (info.name === chord.name ? "exact" : "enharmonic") : "equivalent";
  }
  const omits = [...chord.tones].filter(([, [semis]]) => !notes.some((n) => mod(n, 12) === mod(chord.rootPc + semis, 12)))
    .map(([role]) => role);
  const number = keyName && info ? NV.nashville(info, keyName, { minor: THEORY_UI.minor }) : null;
  return { info, rt: { detected: info ? info.name : null, match, page_name: pageName(info, keyName),
                       page_number: number ? number.text : null, omits } };
}

// Variants of one voicing that keep its shape: a doubled bass pitch class or a natural 5th left out.
function variants(chord, notes) {
  const bass = notes[0];
  const upper = notes.slice(1);
  const fifthPc = chord.tones.has("fifth") && chord.tones.get("fifth")[0] === 7 ? mod(chord.rootPc + 7, 12) : null;
  const dropBassPc = [bass, ...upper.filter((n) => mod(n, 12) !== chord.bassPc)];
  const dropFifth = (ns) => [ns[0], ...ns.slice(1).filter((n) => mod(n, 12) !== fifthPc)];
  const out = [notes, dropBassPc, dropFifth(notes), dropFifth(dropBassPc)];
  return out.filter((v) => v.length >= 3 || v.length === notes.length);
}

function chordFrom(text) {
  const parsed = NV.parseChord(text);
  if (!parsed || parsed.kind !== "chord") throw new Error(`cannot read ${JSON.stringify(text)} as a chord name, a number (with --key) or notes`);
  return chordFromParts(parsed);
}
// A chord from its parts: root and bass spellings ({ letter, acc }) and the suffix text. Numbers and the page's
// respelling come here directly, so a suffix is never re-read as part of a root name.
const spOf = (x) => ({ letter: x.letter, acc: x.acc });
function chordFromParts({ root: root0, suffix, bass: bass0 = null }) {
  const root = spOf(root0);
  const tones = tonesOf(suffix);
  const rootPc = pcOf(root);
  const canon = canonicalSuffix(suffix, tones);
  const bassPc = bass0 ? pcOf(bass0) : rootPc;
  const bass = bass0 && bassPc !== rootPc ? spOf(bass0) : null;
  const spell = new Map([[rootPc, root]]);
  for (const [, [semis, steps]] of tones) if (!spell.has(mod(rootPc + semis, 12))) spell.set(mod(rootPc + semis, 12), spellInterval(root, semis, steps));
  if (bass && !spell.has(bassPc)) spell.set(bassPc, bass);
  return {
    name: nameOf(root) + shownSuffix(canon.suffix) + (bass ? "/" + nameOf(bass) : ""), suffix: canon.suffix, template: canon.template,
    root, bass, rootPc, bassPc, tones, spell,
    allPcs: [...new Set([...tones.values()].map((t) => mod(rootPc + t[0], 12)))],
  };
}

const spelledNames = (notes, spell, bias) => notes.map((m) => {
  const sp = spell.get(mod(m, 12)) || Theory.spellAlone(mod(m, 12), bias);
  return nameOf(sp) + octaveOf(m, sp);
});

// Semitones moved from one chord to the next: each note of the smaller chord is matched to its own note of the larger
// (the cheapest matching), and every note of the larger chord left over moves to its nearest note. Exact for chords of
// up to 14 notes (a bitmask DP); larger clusters fall back to nearest-note distances.
function movement(prev, next) {
  if (!prev || !next || !prev.length || !next.length) return null;
  const [s, l] = prev.length <= next.length ? [prev, next] : [next, prev];
  const nearest = l.map((n) => Math.min(...s.map((m) => Math.abs(m - n))));
  if (l.length > 14) return nearest.reduce((a, b) => a + b, 0) + s.reduce((a, m) => a + Math.min(...l.map((n) => Math.abs(m - n))), 0);
  const size = 1 << l.length;
  const dp = new Float64Array(size).fill(Infinity);
  dp[0] = 0;
  let best = Infinity;
  for (let mask = 0; mask < size; mask++) {
    const cost = dp[mask];
    if (cost === Infinity) continue;
    let i = 0;
    for (let m = mask; m; m &= m - 1) i++;
    if (i === s.length) {
      let extra = 0;
      for (let j = 0; j < l.length; j++) if (!(mask & (1 << j))) extra += nearest[j];
      best = Math.min(best, cost + extra);
      continue;
    }
    for (let j = 0; j < l.length; j++) {
      if (mask & (1 << j)) continue;
      const next = mask | (1 << j), c = cost + Math.abs(s[i] - l[j]);
      if (c < dp[next]) dp[next] = c;
    }
  }
  return best;
}

const mean = (ns) => ns.reduce((a, b) => a + b, 0) / ns.length;
const REGISTER_WINDOW = 7;  // semitones the upper voices' mean may stray from the plain voicing's

// The plain voicing itself first, then its upper voices rotated (lowest up or highest down an octave, up to three
// times) and shifted by an octave, over the same bass. A candidate must keep every note distinct, stay within
// REGISTER_WINDOW of the plain voicing's register, and add no low-interval crowding.
function voiceLeadCandidates(base) {
  const bass = base[0];
  const upper0 = base.slice(1);
  if (!upper0.length) return [base];
  const centre = mean(upper0);
  const crowding = lowBreaks(base).length;
  const out = [base];
  const seen = new Set([base.join(",")]);
  for (let rot = -3; rot <= 3; rot++) {
    const u = [...upper0];
    for (let k = 0; k < Math.abs(rot); k++) {
      u.sort((a, b) => a - b);
      if (rot > 0) u[0] += 12; else u[u.length - 1] -= 12;
    }
    for (const shift of [-12, 0, 12]) {
      const cand = [bass, ...u.map((n) => n + shift)].sort((x, y) => x - y);
      const key = cand.join(",");
      if (seen.has(key)) continue;
      seen.add(key);
      if (cand[0] !== bass || cand[1] - bass < 3 || new Set(cand).size !== cand.length) continue;
      if (cand[cand.length - 1] > HI || cand[cand.length - 1] - cand[1] > 36) continue;
      if (Math.abs(mean(cand.slice(1)) - centre) > REGISTER_WINDOW) continue;
      if (lowBreaks(cand).length > crowding) continue;
      out.push(cand);
    }
  }
  return out;
}

const NAMED = { ninth: /9/, eleventh: /11/, thirteenth: /13/, sixth: /6/ };  // a tension the suffix spells out

// Whether a style's plain voicing (or a variant of it, as voiceItem tries) reads back as the chord itself.
function readsAsItself(chord, style, octave, keyName, bias) {
  try {
    const base = fit(VOICERS[style](chord, octave));
    return variants(chord, base).some((v) => ["exact", "enharmonic"].includes(readBack(chord, fit(v), keyName, bias).rt.match));
  } catch { return false; }
}

// ------------------------------------------------------------------- items --
function voiceItem(text0, req, prev) {
  const text = clean(text0);
  const keyName = req.key || null;
  const key = keyName ? NV.parseKey(keyName) : null;
  if (keyName && !key) throw new Error(`cannot read the key ${JSON.stringify(keyName)} (try "Eb major" or "C# minor")`);
  const style = req.voicing || "close";
  if (!STYLES.includes(style)) throw new Error(`voicing must be one of ${STYLES.join(", ")}`);
  const minor = THEORY_UI.minor;
  const warnings = [];

  const numberish = !/\s/.test(text) && NUMBERISH.test(text);
  // Dash-minor ("C-7", "Bb-7", "F-9", "Eb-(maj7)"): a minor chord, never a note with a negative octave (octave -1 is
  // off the keyboard anyway). Nashville numbers ("2-7", "2-^7") are read by numberToName.
  const dashMinor = !numberish && /^[A-Ga-g](#{1,2}|b{1,2})?-(?=\d|\(|\^|$)/.test(text);
  const given = numberish || dashMinor ? null : readNotes(text, !!key);
  if (given) {
    if (key && given.length === 1 && /^\d{2}$/.test(text)) {
      warnings.push(`${text} was read as the MIDI note ${spelledNames([given[0].midi], new Map(), key.bias)[0]}, not a Nashville number; ` +
                    `write one number per chord ("5^7" for the 5 chord with a 7th, "5 7" as a progression)`);
    }
    const notes = [...new Set(given.map((n) => n.midi))].sort((a, b) => a - b);
    const bias = key ? key.bias : 0;
    const info = Theory.detect(notes, bias);
    const spell = new Map();
    for (const g of given) if (g.sp && !spell.has(mod(g.midi, 12))) spell.set(mod(g.midi, 12), g.sp);
    for (const n of info.notes) if (!spell.has(mod(n.midi, 12))) spell.set(mod(n.midi, 12), { letter: n.letter, acc: n.acc });
    const number = key ? NV.nashville(info, keyName, { minor }) : null;
    return { input: text0, kind: "notes", name: pageName(info, keyName) || info.name, key: key ? key.name : null,
             number: number ? number.text : null, voicing: "as given", notes, names: spelledNames(notes, spell, bias),
             roundtrip: { detected: info.name, match: "notes", page_name: pageName(info, keyName), page_number: number ? number.text : null },
             movement: movement(prev, notes), warnings };
  }

  let kind = "chord", name = dashMinor ? text.replace(/^([A-Ga-g](?:#{1,2}|b{1,2})?)-\^?/, "$1m") : text, numberIn = null;
  let parts = null;
  if (numberish) {
    kind = "number";
    numberIn = text;
    if (!keyName) throw new Error(`${JSON.stringify(text)} is a Nashville number: it needs --key (e.g. --key "Eb major")`);
    parts = numberParts(text, keyName, minor);
  } else if (/\s/.test(text)) {
    throw new Error(`cannot read ${JSON.stringify(text)}: notes need octaves ("Ab3 Eb4") and chords have no spaces`);
  }
  let chord = parts ? chordFromParts(parts) : chordFrom(name);
  if (key) {
    // In a key the label is the page's name for the chord, typed or numbered: Ab7 in C# minor is G#7 (beside 5^7),
    // b6 in Eb major is B. Without a key a typed name is Claude's own spelling and stays. The chord is rebuilt from
    // the page's root and bass spellings with its own suffix, never by reading the page's name back as text.
    const shown = pageSpelledName(chord, keyName, key.bias);
    const bass = chord.bass && shown ? shown.bass : null;
    const sameSp = (a, b) => (!a && !b) || (!!a && !!b && a.letter === b.letter && a.acc === b.acc);
    if (shown && shown.root && pcOf(shown.root) === chord.rootPc && (!chord.bass || (bass && pcOf(bass) === chord.bassPc))
        && !(sameSp(shown.root, chord.root) && sameSp(bass, chord.bass))) {
      try { chord = chordFromParts({ root: shown.root, suffix: chord.suffix, bass }); } catch { /* keep the typed spelling */ }
    }
  }
  if (!chord.template) warnings.push(`the page has no name for ${chord.suffix} chords; it will read these notes another way`);
  const bias = key ? key.bias : Math.sign(chord.root.acc);
  const octave = Number.isInteger(req.octave) ? req.octave : null;

  const base = fit(VOICERS[style](chord, octave));
  let best = null;
  for (const v of variants(chord, base)) {
    const notes = fit(v);
    const back = readBack(chord, notes, keyName, bias);
    if (!best) best = { notes, back };
    if (back.rt.match === "exact" || back.rt.match === "enharmonic") { best = { notes, back }; break; }
  }
  if (best.notes.length !== base.length) warnings.push(`left out ${base.length - best.notes.length} doubled or 5th note(s) so the page names it ${best.back.rt.detected}`);

  if (req.voice_lead && prev) {
    // The plain voicing is candidate 0, so the pick never moves more than it; a candidate the page reads as a
    // different chord is not taken; equal movement goes to the one nearer the plain register.
    const wanted = best.back.rt.match;
    const centre = mean(best.notes.slice(1));
    let lead = null;
    for (const cand of voiceLeadCandidates(best.notes)) {
      const back = cand === best.notes ? best.back : readBack(chord, cand, keyName, bias);
      if (back.rt.match !== wanted || back.rt.detected !== best.back.rt.detected) continue;
      const cost = movement(prev, cand) + 0.01 * Math.abs(mean(cand.slice(1)) - centre);
      if (!lead || cost < lead.cost - 1e-9) lead = { notes: cand, back, cost };
    }
    best = lead;
  }

  if (best.back.rt.match === "equivalent" || best.back.rt.match === "unnamed") {
    // (a shell C7#11 is C E Bb F#, which the page names C7b5; C9sus4's shell reads Bb/C): say which styles it names
    const named = STYLES.filter((s) => s !== style && readsAsItself(chord, s, octave, keyName, bias));
    const list = named.length > 1 ? `${named.slice(0, -1).join(", ")} and ${named[named.length - 1]}` : named[0];
    warnings.push(`the page reads this ${style} voicing as ${best.back.rt.page_name || best.back.rt.detected || "a cluster"}, not ${chord.name}` +
                  (named.length ? `; ${list} ${named.length > 1 ? "are" : "is"} read as ${chord.name}` : ""));
  }
  const lost = best.back.rt.omits.filter((role) => NAMED[role] && NAMED[role].test(chord.suffix));
  if (lost.length) warnings.push(`this ${style} voicing leaves out the ${lost.join(" and ")} that ${chord.name} names; try another voicing`);
  const t3 = chord.tones.get("third"), t11 = chord.tones.get("eleventh");
  if (best.back.rt.omits.includes("third") && t3 && t3[0] === 4 && t11 && t11[0] === 5) {
    warnings.push(`this ${style} voicing leaves out the major 3rd, which clashes with the natural 11th (it sounds as a 9sus4); try close or spread to hear the 3rd too`);
  }
  const crowded = lowBreaks(best.notes);
  if (crowded.length) {
    const pairs = crowded.map((pair) => spelledNames(pair, chord.spell, bias).join("-"));
    warnings.push(`low-interval crowding (may sound muddy): ${pairs.join(", ")}`);
  }

  let number = key ? NV.nashville({ kind: "chord", root: chord.root, suffix: chord.suffix, bass: chord.bass }, keyName, { minor }) : null;
  number = number ? number.text : null;
  if (numberIn && number && bare(number) !== bare(numberIn) && !sameChord(number, numberIn, keyName, minor)) {
    warnings.push(`${numberIn} reads back as ${number} in ${key.name}`);
  }
  return { input: text0, kind, name: chord.name, key: key ? key.name : null, number, number_typed: numberIn, voicing: style, octave,
           notes: best.notes, names: spelledNames(best.notes, chord.spell, bias),
           tones: [...chord.tones.keys()], roundtrip: best.back.rt, movement: movement(prev, best.notes), warnings };
}

function check() {
  const problems = [];
  for (const t of TEMPLATES) {
    try {
      const got = semisKey(tonesOf(t.suffix));
      const twins = TEMPLATES.filter((u) => u.suffix === t.suffix).map((u) => u.key);
      if (!twins.includes(got)) problems.push(`${t.suffix}: read ${got}, template ${t.key}`);
    } catch (e) { problems.push(`${t.suffix}: ${e.message}`); }
  }
  return { ok: true, templates: TEMPLATES.length, problems,
           page_spelling: PAGE_SPELL && !PAGE_SPELL_WHY ? "piano.js spellForKey" : `the bridge's own copy (${PAGE_SPELL_WHY})` };
}

function run(req) {
  if (req.check) return check();
  if (req.minor != null && !["tonic", "relative"].includes(req.minor)) return { ok: false, error: `minor must be tonic or relative, not ${JSON.stringify(req.minor)}` };
  THEORY_UI.minor = req.minor === "relative" ? "relative" : "tonic";
  if (!Array.isArray(req.items) || !req.items.length) return { ok: false, error: "items must be a non-empty list" };
  const results = [];
  let prev = null;
  for (const item of req.items) {
    try {
      const r = voiceItem(String(item), req, prev);
      results.push(r);
      prev = r.notes;
    } catch (e) {
      results.push({ input: String(item), error: e.message });
    }
  }
  return { ok: true, results };
}

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString("utf8");
}

let request;
const argv = process.argv.slice(2);
if (argv.length) {
  request = { items: [], key: null, voicing: "close", octave: null, voice_lead: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--key") request.key = argv[++i];
    else if (a === "--voicing") request.voicing = argv[++i];
    else if (a === "--octave") request.octave = Number(argv[++i]);
    else if (a === "--voice-lead") request.voice_lead = true;
    else if (a === "--minor") request.minor = argv[++i];
    else if (a === "--check") request.check = true;
    else request.items.push(a);
  }
} else {
  try { request = JSON.parse(await readStdin()); }
  catch (e) { process.stdout.write(JSON.stringify({ ok: false, error: `the request is not JSON: ${e.message}` })); process.exit(1); }
}
process.stdout.write(JSON.stringify(run(request), null, argv.length ? 2 : 0) + "\n");
