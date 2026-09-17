// Piano — arsenal/web/piano.js  (ES module)
// A three.js grand-staff piano visualizer for recording TikToks from a KeyLab 88 mk3.
//
// Everything that must appear in a recording is drawn INTO the WebGL canvas (keys, trails,
// the chord label and the staff), because MediaRecorder captures only the canvas. The HTML
// around it (topbar, HUD, hints, toasts) is never recorded.
//
// Sections: THEORY (pure; node-tested) · colour · scene · trails · sparks · camera ·
//           overlay (chord label, Nashville number, staff, Claude's chip) · key and numbers · practice log ·
//           notes engine · Claude's hand · Claude's band (the jam space: transport, deck, glass, floor pool) · MIDI ·
//           computer keys · demo · recording · UI · loop.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { createPerformanceLog } from "./piano/log.js";
import { createKeyTracker, nashville, parseChord, parseKey, spellInKey } from "./piano/nashville.js";
import { createCueClient, createCuePlayer, createClaudeVoice } from "./piano/cues.js";
import { createJamApi, createRestDetector, createTransport } from "./piano/transport.js";
import { createDeck } from "./piano/deck.js";
import { createGlass } from "./piano/glass.js";
import { createSpectacle } from "./piano/spectacle.js";
import * as NV from "./piano/nashville.js";
import { formatNumber } from "./piano/nashville.js";
import { installReader, parseSuffix } from "./piano/chordread.js";
import { keyContext, spellChord, spellNote } from "./piano/spell.js";
import { createKeySignatureModel, signaturePlaces, staffAccidental } from "./piano/keysig.js";

// ===== THEORY BEGIN (pure: no DOM, no three.js; the node tests extract this block) =====
const Theory = (() => {
  const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
  const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
  const mod = (a, n) => ((a % n) + n) % n;

  // A spelling is { letter: 0..6, acc: -2..2 }.
  const pcOf = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);
  const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
  const nameOf = (sp) => LETTERS[sp.letter] + accText(sp.acc);
  const octaveOf = (midi, sp) => Math.floor((midi - sp.acc) / 12) - 1;  // B#3 is MIDI 60
  const diatonicOf = (midi, sp) => octaveOf(midi, sp) * 7 + sp.letter;  // C4 = 28

  function spellInterval(rootSp, semis, steps) {
    const letter = mod(rootSp.letter + steps, 7);
    const target = mod(pcOf(rootSp) + semis, 12);
    return { letter, acc: mod(target - LETTER_PC[letter] + 6, 12) - 6 };
  }

  function spellingsOf(pc) {
    const out = [];
    for (let letter = 0; letter < 7; letter++) {
      const acc = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
      if (Math.abs(acc) <= 1) out.push({ letter, acc });
    }
    return out;
  }

  // keyBias: +1 in sharp keys, -1 in flat keys, 0 when neutral or unknown.
  const ODD = new Set(["E#", "B#", "Cb", "Fb"]);
  const NEUTRAL = { 1: -1, 3: -1, 6: 1, 8: -1, 10: -1 };  // Db Eb F# Ab Bb
  function spellCost(sp, keyBias) {
    const a = Math.abs(sp.acc);
    let c = a === 2 ? 3 : a;
    if (ODD.has(nameOf(sp))) c += 1;
    if (keyBias > 0 && sp.acc < 0) c += 0.6 * a;
    if (keyBias < 0 && sp.acc > 0) c += 0.6 * a;
    return c;
  }
  function neutralTie(pc, sp) {
    const want = NEUTRAL[pc];
    return want && Math.sign(sp.acc) !== want ? 0.01 : 0;
  }
  function spellAlone(pc, keyBias) {
    let best = null;
    for (const sp of spellingsOf(pc)) {
      const c = spellCost(sp, keyBias) + neutralTie(pc, sp);
      if (!best || c < best.c) best = { sp, c };
    }
    return best.sp;
  }

  // Chord templates. tones: [semitones above the root, letter steps above the root].
  // cost: lower is a simpler, likelier reading. omit5: the perfect fifth may be missing.
  const T = (suffix, tones, cost, omit5 = false) => ({ suffix, tones, cost, omit5 });
  const TEMPLATES = [
    T("",        [[0, 0], [4, 2], [7, 4]], 0),
    T("m",       [[0, 0], [3, 2], [7, 4]], 0.1),
    T("dim",     [[0, 0], [3, 2], [6, 4]], 1.0),
    T("aug",     [[0, 0], [4, 2], [8, 4]], 1.2),
    T("sus4",    [[0, 0], [5, 3], [7, 4]], 1.5),
    T("sus2",    [[0, 0], [2, 1], [7, 4]], 1.6),
    T("7",       [[0, 0], [4, 2], [7, 4], [10, 6]], 1.0, true),
    T("maj7",    [[0, 0], [4, 2], [7, 4], [11, 6]], 1.0, true),
    T("m7",      [[0, 0], [3, 2], [7, 4], [10, 6]], 1.0, true),
    T("m7b5",    [[0, 0], [3, 2], [6, 4], [10, 6]], 1.4),
    T("dim7",    [[0, 0], [3, 2], [6, 4], [9, 5]], 1.5),  // 7th spelled as a 6th: C Eb Gb A, as lead sheets write it
    T("6",       [[0, 0], [4, 2], [7, 4], [9, 5]], 1.3, true),
    T("m6",      [[0, 0], [3, 2], [7, 4], [9, 5]], 1.5, true),
    T("add9",    [[0, 0], [2, 1], [4, 2], [7, 4]], 1.4, true),
    T("m(add9)", [[0, 0], [2, 1], [3, 2], [7, 4]], 1.6, true),
    T("m(maj7)", [[0, 0], [3, 2], [7, 4], [11, 6]], 1.8, true),
    T("7sus4",   [[0, 0], [5, 3], [7, 4], [10, 6]], 1.8, true),
    T("add11",   [[0, 0], [4, 2], [5, 3], [7, 4]], 2.0),
    T("7#5",     [[0, 0], [4, 2], [8, 4], [10, 6]], 2.0),
    T("maj7#5",  [[0, 0], [4, 2], [8, 4], [11, 6]], 2.2),
    T("7b5",     [[0, 0], [4, 2], [6, 4], [10, 6]], 2.2),
    T("6/9",     [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5]], 2.0, true),
    T("m6/9",    [[0, 0], [2, 1], [3, 2], [7, 4], [9, 5]], 2.2, true),
    T("9",       [[0, 0], [2, 1], [4, 2], [7, 4], [10, 6]], 2.0, true),
    T("maj9",    [[0, 0], [2, 1], [4, 2], [7, 4], [11, 6]], 2.0, true),
    T("m9",      [[0, 0], [2, 1], [3, 2], [7, 4], [10, 6]], 2.0, true),
    T("9sus4",   [[0, 0], [2, 1], [5, 3], [7, 4], [10, 6]], 2.4, true),
    T("7b9",     [[0, 0], [1, 1], [4, 2], [7, 4], [10, 6]], 2.4, true),
    T("7#9",     [[0, 0], [3, 1], [4, 2], [7, 4], [10, 6]], 2.4, true),
    T("maj7#11", [[0, 0], [4, 2], [6, 3], [7, 4], [11, 6]], 2.4, true),
    T("7#11",    [[0, 0], [4, 2], [6, 3], [7, 4], [10, 6]], 2.6, true),
    T("13",      [[0, 0], [4, 2], [7, 4], [9, 5], [10, 6]], 2.3, true),
    T("13",      [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5], [10, 6]], 2.8, true),
    T("maj13",   [[0, 0], [2, 1], [4, 2], [7, 4], [9, 5], [11, 6]], 2.8, true),
    T("m11",     [[0, 0], [2, 1], [3, 2], [5, 3], [7, 4], [10, 6]], 2.5, true),
    T("m13",     [[0, 0], [2, 1], [3, 2], [7, 4], [9, 5], [10, 6]], 2.8, true),
    T("11",      [[0, 0], [2, 1], [4, 2], [5, 3], [7, 4], [10, 6]], 2.8, true),
  ];
  const keyOf = (semis) => [...semis].sort((a, b) => a - b).join(",");
  for (const t of TEMPLATES) {
    const semis = t.tones.map((x) => x[0]);
    t.key = keyOf(semis);
    t.keyNo5 = t.omit5 && semis.includes(7) ? keyOf(semis.filter((s) => s !== 7)) : null;
  }

  // Best reading of a set of distinct pitch classes (listed from the bass up).
  function matchSet(pcs, bassPc) {
    let best = null;
    for (const root of pcs) {
      const key = keyOf(pcs.map((p) => mod(p - root, 12)));
      for (const t of TEMPLATES) {
        const omitted = t.key !== key;
        if (omitted && t.keyNo5 !== key) continue;
        let cost = t.cost + (omitted ? 0.4 : 0);
        if (bassPc !== undefined && bassPc !== root) {
          const steps = t.tones.find((x) => x[0] === mod(bassPc - root, 12))[1];
          cost += steps === 2 || steps === 4 || steps === 6 ? 0.6 : 1.5;  // 3rd/5th/7th vs an extension
        }
        if (!best || cost < best.cost - 1e-9) best = { root, t, cost };
      }
    }
    return best;
  }

  const SIMPLE = ["unison", "minor 2nd", "major 2nd", "minor 3rd", "major 3rd", "perfect 4th", "tritone",
                  "perfect 5th", "minor 6th", "major 6th", "minor 7th", "major 7th", "octave"];
  const COMPOUND = { 13: "minor 9th", 14: "major 9th", 15: "minor 10th", 16: "major 10th", 17: "perfect 11th",
                     18: "augmented 11th", 19: "perfect 12th", 20: "minor 13th", 21: "major 13th" };
  const IV_STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6];

  function spelledNotes(notes, spellFor) {
    return notes.map((midi) => {
      const sp = spellFor(mod(midi, 12));
      return { midi, letter: sp.letter, acc: sp.acc, name: nameOf(sp), octave: octaveOf(midi, sp), diatonic: diatonicOf(midi, sp) };
    });
  }

  // midiNotes: every sounding MIDI note. Returns null for silence.
  function detect(midiNotes, keyBias = 0) {
    const notes = [...new Set(midiNotes)].sort((a, b) => a - b);
    if (!notes.length) return null;
    const bassPc = mod(notes[0], 12);
    const pcs = [];
    for (const n of notes) if (!pcs.includes(mod(n, 12))) pcs.push(mod(n, 12));

    if (pcs.length === 1) {
      const sp = spellAlone(pcs[0], keyBias);
      const out = spelledNotes(notes, () => sp);
      return { kind: "note", root: sp, suffix: "", bass: null, name: nameOf(sp) + (notes.length === 1 ? out[0].octave : ""),
               sub: notes.length === 1 ? "" : "octaves", octave: notes.length === 1 ? out[0].octave : null,
               pcNames: [nameOf(sp)], notes: out };
    }

    if (pcs.length === 2) {
      const lo = notes[0];
      const hi = notes.find((n) => mod(n, 12) !== bassPc);
      const semis = hi - lo;
      const ic = mod(semis, 12);
      let pick = null;
      for (const lsp of spellingsOf(bassPc)) {
        const hsp = spellInterval(lsp, ic, IV_STEPS[ic]);
        const c = spellCost(lsp, keyBias) + spellCost(hsp, keyBias) + neutralTie(bassPc, lsp);
        if (!pick || c < pick.c) pick = { lsp, hsp, c };
      }
      const map = { [bassPc]: pick.lsp, [mod(hi, 12)]: pick.hsp };
      const out = spelledNotes(notes, (pc) => map[pc]);
      const power = ic === 7;
      return { kind: power ? "chord" : "interval", root: pick.lsp, suffix: power ? "5" : "", bass: null, upper: pick.hsp,
               name: power ? nameOf(pick.lsp) + "5" : `${nameOf(pick.lsp)}-${nameOf(pick.hsp)}`,
               sub: power ? "power chord" : (semis > 12 ? (COMPOUND[semis] || SIMPLE[ic] + " (compound)") : SIMPLE[semis]),
               pcNames: [nameOf(pick.lsp), nameOf(pick.hsp)], notes: out };
    }

    let best = matchSet(pcs, bassPc);
    let slash = false;
    const lowestOther = notes.find((n) => mod(n, 12) !== bassPc);
    const bassOnlyLow = notes.every((n) => mod(n, 12) !== bassPc || n < lowestOther);
    if (bassOnlyLow && pcs.length >= 4) {
      const upper = matchSet(pcs.slice(1), undefined);
      // A foreign bass under a simple upper chord ("C/D") beats a strained full-set reading ("D9sus4"),
      // but not a plain one: B D F A stays Bm7b5, Bb C E G stays C7/Bb.
      if (upper && (!best || upper.cost + 1.7 < best.cost)) { best = { ...upper, cost: upper.cost + 1.7 }; slash = true; }
    }
    if (!best) {
      const map = {};
      for (const pc of pcs) map[pc] = spellAlone(pc, keyBias);
      return { kind: "cluster", root: null, suffix: "", bass: null, name: pcs.map((pc) => nameOf(map[pc])).join(" "),
               sub: "no chord name", pcNames: pcs.map((pc) => nameOf(map[pc])), notes: spelledNotes(notes, (pc) => map[pc]) };
    }

    // Spell the root so the chord's own tones read most simply, then spell every tone from it.
    let pick = null;
    for (const rsp of spellingsOf(best.root)) {
      const map = {};
      let c = neutralTie(best.root, rsp) + (ODD.has(nameOf(rsp)) ? 4 : 0);  // never a B# or Fb root
      for (const [semis, steps] of best.t.tones) {
        const pc = mod(best.root + semis, 12);
        if (!pcs.includes(pc)) continue;
        map[pc] = spellInterval(rsp, semis, steps);
        c += spellCost(map[pc], keyBias);
      }
      if (slash) {
        const semis = mod(bassPc - best.root, 12);
        let bsp = spellInterval(rsp, semis, IV_STEPS[semis]);
        if (spellCost(bsp, 0) > 1) bsp = spellAlone(bassPc, keyBias);
        map[bassPc] = bsp;
        c += spellCost(bsp, keyBias);
      }
      if (!pick || c < pick.c) pick = { rsp, map, c };
    }
    const bassSp = bassPc !== best.root ? pick.map[bassPc] : null;
    const name = nameOf(pick.rsp) + best.t.suffix + (bassSp ? "/" + nameOf(bassSp) : "");
    return { kind: "chord", root: pick.rsp, suffix: best.t.suffix, bass: bassSp, name, sub: "",
             pcNames: pcs.map((pc) => nameOf(pick.map[pc])), notes: spelledNotes(notes, (pc) => pick.map[pc]),
             cost: best.cost };
  }

  // Krumhansl-Kessler key finding over a pitch-class weight histogram.
  const KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
  const KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];
  const MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  const MINOR_KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];
  function pearson(xs, ys) {
    const n = xs.length;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; }
    return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : 0;
  }
  function estimateKey(hist) {
    if (hist.reduce((a, b) => a + b, 0) < 2) return null;
    let best = null;
    for (let tonic = 0; tonic < 12; tonic++) {
      const rotated = hist.map((_, i) => hist[mod(i + tonic, 12)]);
      for (const [mode, profile] of [["major", KK_MAJOR], ["minor", KK_MINOR]]) {
        const r = pearson(rotated, profile);
        if (!best || r > best.r) best = { tonic, mode, r };
      }
    }
    if (best.r < 0.5) return null;
    const relMajor = best.mode === "major" ? best.tonic : mod(best.tonic + 3, 12);
    const fifths = mod(relMajor * 7, 12);
    const bias = fifths === 0 ? 0 : fifths < 6 ? 1 : fifths > 6 ? -1 : best.mode === "major" ? 1 : -1;  // F# major, Eb minor
    const name = (best.mode === "major" ? MAJOR_KEY_NAMES : MINOR_KEY_NAMES)[best.tonic] + (best.mode === "major" ? " major" : " minor");
    return { ...best, bias, name };
  }

  return { LETTERS, LETTER_PC, mod, pcOf, nameOf, accText, octaveOf, diatonicOf, spellInterval, spellingsOf,
           spellAlone, detect, estimateKey, TEMPLATES };
})();
// ===== THEORY END =====

// ---------------------------------------------------------------- utility --
const $ = (id) => document.getElementById(id);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (current, target, tau, dt) => lerp(current, target, 1 - Math.exp(-dt / Math.max(tau, 1e-4)));
const nowSec = () => performance.now() / 1000;
const errText = (e) => (e && (e.message || e.name)) || String(e);
function safeGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function safeSet(key, value) { try { localStorage.setItem(key, value); } catch { /* storage blocked */ } }
// The chord reader (theory next-gen TN2, research/in-flight/piano-theory-nextgen-2026-09-14): "next" installs
// piano/chordread.js over Theory.detect (the same signature and info shape, with next-gen names: Gbmaj13#11 where the
// templates say Bbm11/Gb); "classic" keeps the templates. localStorage arsenal.piano.reader ("next" | "classic", default
// next). Receipts may ask with ?reader=next|classic or ?engine=templates, never stored.
const READER_MODES = ["next", "classic"];
const readerMode = (() => {
  const q = new URLSearchParams(location.search);
  if (q.get("engine") === "templates") return "classic";
  if (READER_MODES.includes(q.get("reader"))) return q.get("reader");
  return READER_MODES.includes(safeGet("arsenal.piano.reader")) ? safeGet("arsenal.piano.reader") : "next";
})();
const pianoReader = (() => {
  if (readerMode !== "next") return null;
  try { return installReader(Theory, NV); } catch (e) { console.warn("[piano] chord reader unavailable, templates kept:", errText(e)); return null; }
})();
// One id per page load (jam-spec 8.11): the practice log, Claude's band (its acks) and the cue stream all carry it, so a
// run's acks meet this page's log session (the L2 alignment). Never reused across reloads: log.js treats records carrying
// its own id as its own. ?page=<id> sets it for receipts, never stored.
const PAGE_ID = (() => {
  const asked = new URLSearchParams(location.search).get("page");
  if (asked && /^[A-Za-z0-9_.:-]{1,80}$/.test(asked)) return asked;
  return `p-${Math.random().toString(16).slice(2, 10)}${Math.random().toString(16).slice(2, 6)}`;
})();

// ----------------------------------------------------------------- colour --
// Pitch colour walks the circle of fifths: music in one key keeps a coherent arc of hues
// (C major = teal through blue and violet to pink) and a modulation visibly shifts the palette.
const COLOUR = { mode: safeGet("arsenal.piano.colour") || "pitch" };
const COLOUR_MODES = ["pitch", "velocity", "mono"];  // the Colour menu's choices (piano.html #color-select)
const fifthsIndex = (pc) => (pc * 7) % 12;
// Each hue is taken near its own most colourful lightness (blue and violet peak dark, yellow and teal
// peak light) at 95% of the sRGB edge, so no note is a pastel. A fixed lightness for every hue can only
// be as saturated as the weakest hue allows, which is what made the old palette chalky.
const vividCache = new Map();
function vivid(hDeg, baseL, pull = 0.75) {
  const key = `${Math.round(hDeg)}:${baseL}:${pull}`;
  let lc = vividCache.get(key);
  if (!lc) {
    let cuspL = 0.5, cuspC = 0;
    for (let L = 0.3; L <= 0.98; L += 0.01) { const c = maxChroma(L, hDeg); if (c > cuspC) { cuspC = c; cuspL = L; } }
    const L = lerp(baseL, cuspL, pull);
    lc = [L, maxChroma(L, hDeg) * 0.95];
    vividCache.set(key, lc);
  }
  return [lc[0], lc[1], hDeg];
}
function noteLch(midi, vel) {
  if (COLOUR.mode === "velocity") {
    const t = clamp(vel / 127, 0, 1);
    return vivid(Math.round(lerp(255, 350, t)), 0.62 + 0.2 * t);
  }
  if (COLOUR.mode === "mono") return vivid(68, 0.8, 0.5);
  return vivid((200 + 30 * fifthsIndex(Theory.mod(midi, 12))) % 360, 0.72);
}
function oklchToLinearRaw(L, C, hDeg) {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
          -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
          -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
}
function oklchToLinear(L, C, hDeg) {
  return oklchToLinearRaw(L, C, hDeg).map((v) => Math.max(0, v));
}
function maxChroma(L, hDeg) {  // the largest chroma still inside sRGB at this lightness and hue
  let lo = 0, hi = 0.4;
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2;
    if (oklchToLinearRaw(L, mid, hDeg).every((v) => v >= -1e-4 && v <= 1.0001)) lo = mid; else hi = mid;
  }
  return lo;
}
// At their most colourful, hues differ a lot in luminance (yellow-green is about 4.7x violet), which would let a
// soft yellow note outshine a hard violet one. Pitch colours are pulled most of the way toward the palette's
// geometric mean luminance, so velocity decides how bright a note is, not its name. Channels above 1 are fine in
// the linear half-float pipeline; key albedo clamps its own copy (see updateKeys).
const LUMA_PULL = 0.65;
const lumaOf = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
let pitchLumaMean = 0;
const colourCache = new Map();  // numeric keys: 0-11 pitch class, 12 mono, 100+vel velocity; built once per note
function noteColor(midi, vel, target = new THREE.Color()) {
  const pc = Theory.mod(midi, 12);
  const key = COLOUR.mode === "velocity" ? 100 + Math.round(clamp(vel, 0, 127)) : COLOUR.mode === "mono" ? 12 : pc;
  let rgb = colourCache.get(key);
  if (!rgb) {
    rgb = oklchToLinear(...noteLch(midi, vel));
    if (COLOUR.mode === "pitch") {
      if (!pitchLumaMean) {
        let sum = 0;
        for (let p = 0; p < 12; p++) sum += Math.log(lumaOf(...oklchToLinear(...noteLch(60 + p, 100))));
        pitchLumaMean = Math.exp(sum / 12);
      }
      const s = Math.pow(pitchLumaMean / Math.max(lumaOf(...rgb), 1e-4), LUMA_PULL);
      rgb = rgb.map((v) => v * s);
    }
    colourCache.set(key, rgb);
  }
  return target.setRGB(rgb[0], rgb[1], rgb[2]);  // linear working space
}
// Noteheads and chord letters sit on the dark scrim, so they keep a lightness floor (chroma refits to the sRGB edge
// there); the columns and keys keep each hue's own deeper, most colourful lightness.
const cssCache = new Map();
function noteCss(midi, vel, alpha = 1) {
  const [l, , h] = noteLch(midi, vel);
  const key = `${h}:${l.toFixed(3)}`;
  let lc = cssCache.get(key);
  if (!lc) {
    const L = Math.max(l, 0.68);
    lc = [+L.toFixed(3), +(maxChroma(L, h) * 0.95).toFixed(4)];
    cssCache.set(key, lc);
  }
  return `oklch(${lc[0]} ${lc[1]} ${h} / ${alpha})`;
}

// ---------------------------------------------------------------- framing --
const FRAMINGS = {
  "9:16": { id: "9:16", w: 1080, h: 1920, fov: 31, minSpan: 16, follow: true },
  "16:9": { id: "16:9", w: 1920, h: 1080, fov: 23, minSpan: 56, follow: false },
};
let framing = FRAMINGS[safeGet("arsenal.piano.framing")] || FRAMINGS["9:16"];
let renderScale = 1, spectacle = null;

// ------------------------------------------------------------ key geometry --
// One world unit = one white-key pitch (23.5 mm on a real piano). A0 at the left edge x=-26.
const KEY = { first: 21, last: 108, whiteW: 0.94, whiteH: 0.8, whiteL: 6.2, blackW: 0.56, blackH: 0.64,
              blackL: 3.95, blackTop: 0.52, back: -3.1, pivotBack: 6.0 };
const WHITE_OFFSET = [0, -1, 1, -1, 2, 3, -1, 4, -1, 5, -1, 6];
// Black keys sit where a real action puts them: C-E split into 5 equal slots, F-B into 7.
const BLACK_CENTER = { 1: 0.9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5.0, 10: 3 + 4 / 7 * 5.5 };
const isBlack = (m) => BLACK_CENTER[Theory.mod(m, 12)] !== undefined;
function keyX(m) {
  const oct = Math.floor(m / 12), pc = Theory.mod(m, 12);
  const x = isBlack(m) ? oct * 7 + BLACK_CENTER[pc] : oct * 7 + WHITE_OFFSET[pc] + 0.5;
  return x - 38;  // A0 is white index 12; centre the 52 whites on x=0
}
const RAIL_Y = 1.12;       // top of the back rail, where trails are emitted
const TRAIL_Z = -3.42;     // just behind the key backs

// ------------------------------------------------------------------ scene --
const canvas = $("piano-canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance" });
renderer.setPixelRatio(1);
// Khronos PBR Neutral keeps the OKLCH palette's hues and saturation; ACES would push neon toward white.
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x010206);
scene.fog = new THREE.Fog(0x010206, 95, 280);  // the floor melts into the dark instead of ending at a horizon
const pmrem = new THREE.PMREMGenerator(renderer);
// A dark studio for reflections only: black walls and a few soft strip lights, so lacquer and keys
// catch long highlights without lighting the whole stage grey. Assigned per material (not
// scene.environment, which would override each material's envMapIntensity).
const envMap = (() => {
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.BoxGeometry(80, 40, 80), new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide })));
  const strip = (w, h, intensity, tint, x, y, z, rx, ry) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(tint).multiplyScalar(intensity), side: THREE.DoubleSide }));
    m.position.set(x, y, z);
    m.rotation.set(rx, ry, 0);
    env.add(m);
  };
  strip(44, 3.2, 5.0, 0xffffff, 0, 15, 10, Math.PI / 2, 0);        // long overhead strip, in front
  strip(3.2, 18, 2.6, 0xffe1c2, -30, 6, -6, 0, Math.PI / 2);       // warm left strip
  strip(3.2, 18, 2.2, 0xc2d2ff, 30, 6, -12, 0, -Math.PI / 2);      // cool right strip
  strip(36, 1.6, 1.4, 0x9fb4ff, 0, 3, -34, 0, 0);                   // faint back strip for rims
  return pmrem.fromScene(env, 0.02).texture;
})();

const camera = new THREE.PerspectiveCamera(framing.fov, framing.w / framing.h, 0.5, 900);

const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(framing.w, framing.h,
  { type: THREE.HalfFloatType, samples: 4 }));
composer.addPass(new RenderPass(scene, camera));
// radius 0 keeps the widest bloom mips light: dense chords glow without fogging the whole frame
const bloom = new UnrealBloomPass(new THREE.Vector2(framing.w, framing.h), 0.45, 0.0, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// Sky and far floor share one colour through the fog, so the stage has no horizon line. It takes
// a faint tint of whatever is sounding (see renderFrame).
const STAGE_DARK = new THREE.Color(0x010206);
const stageTint = STAGE_DARK.clone();

const floor = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), new THREE.MeshStandardMaterial({
  color: 0x020203, roughness: 0.62, metalness: 0.0 }));
floor.rotation.x = -Math.PI / 2;
floor.position.y = -2.3;
scene.add(floor);

// Lacquered body: keybed, end cheeks, back rail with felt and a thin light line.
const lacquer = new THREE.MeshPhysicalMaterial({ color: 0x050609, roughness: 0.24, metalness: 0.0,
  clearcoat: 1.0, clearcoatRoughness: 0.04, envMap, envMapIntensity: 0.9 });
function addBox(w, h, d, r, x, y, z, material) {
  const mesh = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, r), material);
  mesh.position.set(x, y, z);
  scene.add(mesh);
  return mesh;
}
addBox(56.4, 1.5, 8.3, 0.3, 0, -1.55, -1.45, lacquer);             // keybed
addBox(1.5, 2.95, 9.5, 0.36, -27.1, -0.83, -1.0, lacquer);         // left cheek
addBox(1.5, 2.95, 9.5, 0.36, 27.1, -0.83, -1.0, lacquer);          // right cheek
addBox(52.7, 1.95, 2.35, 0.26, 0, 0.14, -4.46, lacquer);           // back rail
const felt = new THREE.Mesh(new THREE.BoxGeometry(52.2, 0.16, 0.1),
  new THREE.MeshStandardMaterial({ color: 0x5c0c1a, roughness: 0.95 }));
felt.position.set(0, 0.08, -3.2);
scene.add(felt);
const railLine = new THREE.Mesh(new THREE.BoxGeometry(52.2, 0.04, 0.04),
  new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 0.62, 0.3).multiplyScalar(0.9) }));
railLine.position.set(0, RAIL_Y - 0.06, -3.3);
scene.add(railLine);

scene.add(new THREE.HemisphereLight(0x8a9cc8, 0x040404, 0.22));
const keyLight = new THREE.DirectionalLight(0xfff0dc, 1.9);
keyLight.position.set(-16, 30, 24);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x9db6ff, 1.4);
rimLight.position.set(12, 16, -30);
scene.add(rimLight);
// Three coloured lights follow the latest notes so their colour spills onto keys and lacquer.
const noteLights = [0, 1, 2].map(() => {
  const light = new THREE.PointLight(0xffffff, 0, 9, 2);
  light.position.set(0, 2.1, -1.4);
  scene.add(light);
  return { light, level: 0, target: 0, color: new THREE.Color() };
});
let noteLightNext = 0;

// ------------------------------------------------------------------- keys --
const whiteGeo = new RoundedBoxGeometry(KEY.whiteW, KEY.whiteH, KEY.whiteL, 3, 0.07);
const blackGeo = new RoundedBoxGeometry(KEY.blackW, KEY.blackH, KEY.blackL, 3, 0.06);
const keys = new Map();  // midi -> key state
const IVORY = new THREE.Color(0xdedbd3);
const keyAlbedo = new THREE.Color();
// Claude's hand (see "Claude's hand" below). Claude's keys glow moonlight, never a pitch colour. Each key also carries
// a flat frame on its top face: the ghost rim of a hover (slate on ivory, where silver vanishes; silver on black), or a
// thin moonlight rim on a key Daniel and Claude both hold (Daniel's colour wins the key itself). The frames sit under
// the bloom threshold: a hint on the keys, not a light.
const MOON = new THREE.Color(0xc8dcff);
const GHOST = new THREE.Color(0.78, 0.84, 0.95);
const GHOST_TINT = new THREE.Color(0x8fa3c4);
// On ivory a thin, light rim disappears (receipt 2026-09-14: white-key ghosts barely showed at 0.07 wide, 0.55 opaque),
// so white keys get a wider, deeper slate rim at a higher opacity and a stronger cool fill.
const GHOST_ON_IVORY = new THREE.Color(0x3e5277);
// incomingWhite/Black: an incoming ghost's rim as a share of a target's (jam spec 8.5: 0.35 against 0.55 on ivory, 0.7 on
// black keys), with no fill
const GHOST_RIM = { white: 0.85, black: 0.7, whiteFill: 0.42, incomingWhite: 0.35 / 0.55, incomingBlack: 0.35 / 0.7 };
// Ghost fades, damp time constants in seconds: in at once, out a little slower, and a hover Claude sends in about 400 ms
// (95% at 3 tau, jam spec 8.9). Found: the rims' one pulse in size.
const GHOST_FADE = { in: 0.05, out: 0.18, remote: 0.4 / 3 };
const GHOST_FOUND = { sec: 0.2, scale: 0.15 };
// Receipts only (__piano.jam.ghostFrames): true hides the ghost rim frames while their fill stays, so a snapshot diff sees the
// rims alone (A9). Always false on the page Daniel uses.
let ghostFramesHidden = false;
// Claude's key while it is lit. Its white surface turns moonlight blue while Claude holds it (in by the first touch: fade),
// darker than Daniel's lit keys at the same velocity and lighter the harder Claude plays (low at velocity 0 to high at
// 127), with its ivory clearcoat kept and the capped moonlight glowing on top. The verifier (2026-09-14, round 3) found the
// pale #d8ecff surface lighter than Daniel's lit keys and nearly the same at every velocity. Where a colour mode's keys
// run dark (velocity: a soft note is deep violet) the surface is held at fit x the mean of Daniel's key surfaces at that
// velocity (moonSurface). Measured on the front of Claude's C4 E4 G4 beside Daniel's C3 E3 G3, 9:16 (16:9 in brackets),
// velocity 30 / 60 / 90 / 127, pitch colours: Claude 103 / 114 / 124 / 134 (99 / 110 / 120 / 130) luma, Daniel 129 / 135 /
// 141 / 153 (126 / 133 / 138 / 151), unlit ivory 160 (155); hue 220, saturation 0.35-0.45 (Daniel's 0.53-0.56). Mono:
// Claude 114-148, Daniel 155-170. Velocity colours, whose soft keys are deep violet: the cap brought Claude from 93 / 107 /
// 123 / 136 to 73 / 92 / 120 / 130, still above Daniel's 64 / 84 / 106 / 127 there (a darker surface barely lowers it: it
// is not the surface that holds it up). Black keys take a softer share of the moonlight (black), with its brightest channel
// held under the bloom threshold (blackPeak), so they read lit without a halo.
const MOON_KEY = { low: new THREE.Color(0x5f7aa8), high: new THREE.Color(0x86a0ca), fit: 0.94, fade: 8, black: 0.75,
                   blackPeak: 0.55 };
// Claude's moonlight at a velocity. The 0.75 cap (CUE_LOOK.glow) is on the glow level, but the light a key gives off is
// that level times its colour, and moonlight is brighter than most pitch colours (up to 1.9x Daniel's light at the same
// velocity: the round-1 glow probe). So the moon is scaled to the dimmest pitch colour at that velocity, by luminance and by
// its brightest channel: Claude's key light is at most 0.75 of Daniel's on every key, in every colour mode, and Claude's
// keys stay one even moonlight (a level per pitch class would carry Daniel's palette into Claude's hand).
const MOON_LUMA = lumaOf(MOON.r, MOON.g, MOON.b), MOON_PEAK = Math.max(MOON.r, MOON.g, MOON.b);
const moonScales = new Map();  // keyed like colourCache: 0 pitch (no velocity), 12 mono, 100+vel velocity
const moonProbe = new THREE.Color();
function moonColor(vel, target) {
  const key = COLOUR.mode === "velocity" ? 100 + Math.round(clamp(vel, 0, 127)) : COLOUR.mode === "mono" ? 12 : 0;
  let s = moonScales.get(key);
  if (s === undefined) {
    s = 1;
    for (let pc = 0; pc < 12; pc++) {
      noteColor(60 + pc, vel, moonProbe);
      s = Math.min(s, lumaOf(moonProbe.r, moonProbe.g, moonProbe.b) / MOON_LUMA,
                   Math.max(moonProbe.r, moonProbe.g, moonProbe.b) / MOON_PEAK);
    }
    moonScales.set(key, s);
  }
  return target.copy(MOON).multiplyScalar(s);
}
// Claude's white-key surface at a velocity: MOON_KEY low to high, held at MOON_KEY.fit x the mean luminance of Daniel's
// lit key surfaces at that velocity in this colour mode (as updateKeys builds them: his colour, peak-normalised, 0.95 of
// the way from ivory), so it stays under his keys where his colours run dark. One level for all of Claude's keys.
const moonSurfaceScales = new Map();  // "mode:velocity" -> scale
function moonSurface(vel, target) {
  const v = clamp(vel / 127, 0, 1);
  target.copy(MOON_KEY.low).lerp(MOON_KEY.high, v);
  const key = `${COLOUR.mode}:${Math.round(v * 127)}`;
  let s = moonSurfaceScales.get(key);
  if (s === undefined) {
    let sum = 0;
    for (let pc = 0; pc < 12; pc++) {
      noteColor(60 + pc, vel, moonProbe);
      const peak = Math.max(moonProbe.r, moonProbe.g, moonProbe.b, 1);
      sum += lumaOf(lerp(IVORY.r, moonProbe.r / peak, 0.95), lerp(IVORY.g, moonProbe.g / peak, 0.95), lerp(IVORY.b, moonProbe.b / peak, 0.95));
    }
    s = Math.min(1, MOON_KEY.fit * (sum / 12) / Math.max(lumaOf(target.r, target.g, target.b), 1e-4));
    moonSurfaceScales.set(key, s);
  }
  return target.multiplyScalar(s);
}
function ghostFrameGeo(w, l, edge) {  // a flat rectangle with a rectangular hole, in the XY plane
  const s = new THREE.Shape();
  s.moveTo(-w / 2, -l / 2); s.lineTo(w / 2, -l / 2); s.lineTo(w / 2, l / 2); s.lineTo(-w / 2, l / 2); s.closePath();
  const h = new THREE.Path();
  h.moveTo(-w / 2 + edge, -l / 2 + edge); h.lineTo(-w / 2 + edge, l / 2 - edge); h.lineTo(w / 2 - edge, l / 2 - edge);
  h.lineTo(w / 2 - edge, -l / 2 + edge); h.closePath();
  s.holes.push(h);
  return new THREE.ShapeGeometry(s);
}
const ghostWhiteGeo = ghostFrameGeo(KEY.whiteW - 0.06, KEY.whiteL - 0.08, 0.13);
const ghostBlackGeo = ghostFrameGeo(KEY.blackW - 0.05, KEY.blackL - 0.06, 0.05);
// The hold state's second, inner rim (jam spec 8.5: Try's shared pitch classes around a change): inset 20% of the key's
// width on every side, as the glass draws it, inside the outer frame's hole so the two never overlap.
const GHOST_HOLD_INSET = 0.2;
const ghostHoldWhiteGeo = ghostFrameGeo(KEY.whiteW * (1 - 2 * GHOST_HOLD_INSET), KEY.whiteL - 2 * GHOST_HOLD_INSET * KEY.whiteW, 0.09);
const ghostHoldBlackGeo = ghostFrameGeo(KEY.blackW * (1 - 2 * GHOST_HOLD_INSET), KEY.blackL - 2 * GHOST_HOLD_INSET * KEY.blackW, 0.04);
for (let m = KEY.first; m <= KEY.last; m++) {
  const black = isBlack(m);
  const material = black
    ? new THREE.MeshPhysicalMaterial({ color: 0x0a0a0d, roughness: 0.3, clearcoat: 1.0, clearcoatRoughness: 0.08, envMap, envMapIntensity: 0.8 })
    : new THREE.MeshPhysicalMaterial({ color: IVORY, roughness: 0.36, clearcoat: 0.5, clearcoatRoughness: 0.2, envMap, envMapIntensity: 0.35 });
  const len = black ? KEY.blackL : KEY.whiteL;
  const pivot = new THREE.Group();
  const pivotZ = KEY.back - KEY.pivotBack;
  pivot.position.set(keyX(m), 0, pivotZ);
  const mesh = new THREE.Mesh(black ? blackGeo : whiteGeo, material);
  mesh.position.set(0, black ? KEY.blackTop - KEY.blackH / 2 : -KEY.whiteH / 2, KEY.back + len / 2 - pivotZ);
  pivot.add(mesh);
  const frame = new THREE.Mesh(black ? ghostBlackGeo : ghostWhiteGeo, new THREE.MeshBasicMaterial({
    color: black ? GHOST : GHOST_ON_IVORY, transparent: true, opacity: 0, depthWrite: false }));
  frame.rotation.x = -Math.PI / 2;  // face up; the shape's length runs along the key
  frame.position.set(0, (black ? KEY.blackTop : 0) + 0.006, KEY.back + len / 2 - pivotZ);  // just above the top face
  frame.visible = false;
  pivot.add(frame);  // tilts with the key
  const holdFrame = new THREE.Mesh(black ? ghostHoldBlackGeo : ghostHoldWhiteGeo, new THREE.MeshBasicMaterial({
    color: black ? GHOST : GHOST_ON_IVORY, transparent: true, opacity: 0, depthWrite: false }));
  holdFrame.rotation.x = -Math.PI / 2;
  holdFrame.position.copy(frame.position);
  holdFrame.visible = false;
  pivot.add(holdFrame);
  scene.add(pivot);
  // The rest pose's top face in world space (x, y, z per corner), for the glass layer's projection.
  const hw = (black ? KEY.blackW : KEY.whiteW) / 2, top = black ? KEY.blackTop : 0, x = keyX(m);
  const face = new Float32Array([x - hw, top, KEY.back, x + hw, top, KEY.back, x + hw, top, KEY.back + len, x - hw, top, KEY.back + len]);
  // target/glow/glowTarget/color are Daniel's; the cue* fields are Claude's (or a replay's), so neither hand's notes
  // can lift or darken a key the other still holds.
  keys.set(m, { m, black, pivot, material, lever: len + KEY.pivotBack, depth: 0, vel: 0, target: 0,
                glow: 0, glowTarget: 0, color: new THREE.Color(),
                cueTarget: 0, cueGlow: 0, cueGlowTarget: 0, cueColor: new THREE.Color(), cueSurface: new THREE.Color(),
                cueCss: "", cueReplay: false,
                // cueDepth, cueV: Claude's press, a spring of its own beside Daniel's (depth, v), see updateKeys
                cueDepth: 0, cueV: 0,
                // ghostFull: 1 for a target ghost, 0 for an incoming one (lighter, no fill); holdLevel: the inner hold rim
                frame, holdFrame, ghostLevel: 0, ghostFull: 1, holdLevel: 0, pulse: 1, rimLevel: 0, face });
}

// ----------------------------------------------------------------- trails --
// One instanced draw for every trail. Each instance stores its note's start, release and
// sound-end times; the vertex shader places the bar from the clock, so a trail costs nothing
// per frame on the CPU. Each height is a moment in the note's life, so a column draws its loudness over
// time: a bright strike, a slow sag while it sounds, and a quick let-go when the sound stops.
const T0 = nowSec();
// Receipts only (__piano.jam.clock): a held clock that a harness steps one frame at a time, so a take and its control draw
// the same pixels (jam spec A5). null, always, on the page Daniel uses.
let heldClock = null;
const clock = () => (heldClock !== null ? heldClock : nowSec() - T0);
const FAR = 1e6;
const TRAIL_MAX = 640;          // the cap on Daniel's columns: slots are recycled, so a long session never grows
// A replay's columns (Hear me: Daniel's own playing, played back) take slots of their own above Daniel's, so a replay never
// changes which slots his columns take, nor the light budget he has once it leaves the canvas (REC in auto, A5).
const TRAIL_CUE = 128, TRAIL_SLOTS = TRAIL_MAX + TRAIL_CUE;
const TRAIL_SPEED = 6.5;        // world units per second
// A stretch of column dims as it ages, so a column's life is counted in seconds, not in how much sky the
// follow camera happens to show. Past TRAIL_LIFE it is black, and is neither drawn nor counted.
const TRAIL_LIFE = 7.0;
// Pedal history as a ring texture (60 samples a second): the shader asks whether the pedal was down at the
// moment each stretch of a held note left its key, so a pedal press lifts the column from there on. The ring
// is sized to outlast TRAIL_LIFE (512 samples, 8.5 s), so no drawn stretch ever reads a wrapped sample.
const PEDAL_HZ = 60, PEDAL_LEN = 2 ** Math.ceil(Math.log2((TRAIL_LIFE + 1) * PEDAL_HZ));
const pedalHist = new THREE.DataTexture(new Uint8Array(PEDAL_LEN), PEDAL_LEN, 1, THREE.RedFormat, THREE.UnsignedByteType);
pedalHist.magFilter = pedalHist.minFilter = THREE.NearestFilter;
pedalHist.needsUpdate = true;
let pedalHistAt = -1;
const trailUniforms = { uNow: { value: 0 }, uSpeed: { value: TRAIL_SPEED }, uBaseY: { value: RAIL_Y },
                        uZ: { value: TRAIL_Z }, uTop: { value: 30 }, uLife: { value: TRAIL_LIFE }, uPedal: { value: 0 },
                        uPedalHist: { value: pedalHist }, uDensity: { value: 1 } };

// The light model, shared by the key glow (glowLevel) and the trail shader (as #defines), so a key and its
// column always agree. Daniel, 2026-09-13: brightest with finger and pedal down together, still clearly lit
// while only the pedal holds the note, and velocity always counts.
//   loudness s seconds after the strike, like a struck string: a bright attack (strike, settling on strikeTau),
//     then a slow sag toward sagFloor on sagTau for as long as the note sounds
//   state: finger down 1.0, pedalBoost from the moment the pedal also goes down, pedalOnly once released
//   sound over: releaseFast of the light goes on releaseFastTau, the faint rest on releaseSlowTau; skipped after endCut
//   a stretch dims on afterglow as it rises; past freshAge it also shares the light budget (see renderFrame)
const LIGHT = { strike: 0.7, strikeTau: 0.22, sagFloor: 0.5, sagTau: 6.0, pedalBoost: 1.45, pedalOnly: 0.8,
                releaseFast: 0.82, releaseFastTau: 0.14, releaseSlowTau: 1.2, endCut: 5.0, afterglow: 3.2, freshAge: 0.6 };
const LIGHT_BUDGET = 1.2;  // old light allowed on screen, in screen-tall columns at full level
const lightBudget = { danDensity: 1 };  // the density Daniel's columns alone would have (renderFrame; tickCueStage takes it)
const velFactor = (vel01) => 0.35 + 0.65 * Math.pow(clamp(vel01, 0, 1), 0.8);
const envelope = (s) => (1 + LIGHT.strike * Math.exp(-s / LIGHT.strikeTau))
                      * (LIGHT.sagFloor + (1 - LIGHT.sagFloor) * Math.exp(-s / LIGHT.sagTau));
const releaseLevel = (gone) => LIGHT.releaseFast * Math.exp(-gone / LIGHT.releaseFastTau)
                             + (1 - LIGHT.releaseFast) * Math.exp(-gone / LIGHT.releaseSlowTau);
const lightLevel = (vel01, held, pedal, s) => velFactor(vel01) * envelope(s) * (held ? lerp(1, LIGHT.pedalBoost, pedal) : LIGHT.pedalOnly);
const glslF = (x) => x.toFixed(4);
const trailGeo = new THREE.InstancedBufferGeometry();
{
  const base = new THREE.PlaneGeometry(1, 1);
  base.translate(0, 0.5, 0);
  trailGeo.setIndex(base.getIndex());
  trailGeo.setAttribute("position", base.getAttribute("position"));
}
const trailAttr = {};
for (const [name, size] of [["aX", 1], ["aW", 1], ["aT0", 1], ["aT1", 1], ["aT2", 1], ["aVel", 1], ["aColor", 3]]) {
  const attr = new THREE.InstancedBufferAttribute(new Float32Array(TRAIL_SLOTS * size), size);
  attr.setUsage(THREE.DynamicDrawUsage);
  trailGeo.setAttribute(name, attr);
  trailAttr[name] = attr;
}
trailAttr.aT0.array.fill(-FAR);
trailAttr.aT1.array.fill(-FAR);
trailAttr.aT2.array.fill(-FAR);
trailGeo.instanceCount = TRAIL_SLOTS;
trailGeo.setAttribute("aCue", new THREE.InstancedBufferAttribute(Float32Array.from({length: TRAIL_SLOTS}, (_, i) => i >= TRAIL_MAX ? 1 : 0), 1));
trailUniforms.uAtmosphere = { value: 0 };
const trailMesh = new THREE.Mesh(trailGeo, new THREE.ShaderMaterial({
  uniforms: trailUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  defines: { STRIKE: glslF(LIGHT.strike), STRIKE_TAU: glslF(LIGHT.strikeTau), SAG_FLOOR: glslF(LIGHT.sagFloor),
             SAG_TAU: glslF(LIGHT.sagTau), PEDAL_BOOST: glslF(LIGHT.pedalBoost), PEDAL_ONLY: glslF(LIGHT.pedalOnly),
             RELEASE_FAST: glslF(LIGHT.releaseFast), RELEASE_FAST_TAU: glslF(LIGHT.releaseFastTau),
             RELEASE_SLOW_TAU: glslF(LIGHT.releaseSlowTau), END_CUT: glslF(LIGHT.endCut),
             AFTERGLOW: glslF(LIGHT.afterglow), FRESH_AGE: glslF(LIGHT.freshAge) },
  vertexShader: `
    uniform float uNow, uSpeed, uBaseY, uZ, uTop, uLife, uPedal, uAtmosphere;
    attribute float aCue;
    attribute float aX, aW, aT0, aT1, aT2, aVel;
    attribute vec3 aColor;
    varying vec2 vP;
    varying float vBot, vTop, vW, vT0, vT1, vEnd, vBar, vHeld, vFoot;
    varying vec3 vColor;
    float envelope(float s) { return (1.0 + STRIKE * exp(-s / STRIKE_TAU)) * (SAG_FLOOR + (1.0 - SAG_FLOOR) * exp(-s / SAG_TAU)); }
    float letGo(float t, float t1) { float x = clamp((t - t1 + 0.03) / 0.15, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); }
    void main() {
      if (uAtmosphere > .5 && aCue < .5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
      float end = min(uNow, aT2);
      float gone = uNow - end;
      float bot = uBaseY + gone * uSpeed;
      if (aT0 < -1e5 || bot > uTop || gone > END_CUT) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
      // stretches older than uLife are already black, so a long pedalled note's quad stops there
      float top = uBaseY + min(uNow - aT0, uLife) * uSpeed;
      float padX = aW * 0.6;   // halo reach to each side: neighbouring columns barely overlap
      float padY = aW * 0.8;   // room below for the foot glow and above for the rounded end
      float w = aW + padX * 2.0;
      float y = mix(bot - padY, max(top, bot + 0.001) + padY, position.y);
      vP = vec2(position.x * w, y);
      vBot = bot; vTop = top;
      vW = aW; vColor = aColor;
      vT0 = aT0; vT1 = aT1; vEnd = end;
      // the terms that are the same for the whole column are worked out here once instead of per fragment
      // once the sound stops the whole column lets go within a few tenths of a second, leaving a faint ghost
      float release = RELEASE_FAST * exp(-gone / RELEASE_FAST_TAU) + (1.0 - RELEASE_FAST) * exp(-gone / RELEASE_SLOW_TAU);
      vBar = (0.35 + 0.65 * pow(clamp(aVel, 0.0, 1.0), 0.8)) * release;
      vHeld = 1.0 - letGo(uNow, aT1);
      // the foot glows with how loud the note is right now
      vFoot = vBar * envelope(end - aT0) * mix(mix(1.0, PEDAL_BOOST, uPedal), PEDAL_ONLY, 1.0 - vHeld);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(aX + vP.x, y, uZ, 1.0);
    }`,
  fragmentShader: `
    uniform float uTop, uSpeed, uNow, uBaseY, uLife, uDensity;
    uniform sampler2D uPedalHist;
    varying vec2 vP;
    varying float vBot, vTop, vW, vT0, vT1, vEnd, vBar, vHeld, vFoot;
    varying vec3 vColor;
    float sdRoundBox(vec2 p, vec2 b, float r) {
      vec2 q = abs(p) - b + r;
      return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
    }
    float pedalAt(float t) {  // the smoothed pedal level at clock time t, from the ring written in renderFrame
      float i = mod(floor(t * ${PEDAL_HZ}.0), ${PEDAL_LEN}.0);
      return texture2D(uPedalHist, vec2((i + 0.5) / ${PEDAL_LEN}.0, 0.5)).r;
    }
    // Loudness s seconds after the strike (LIGHT above): a bright attack, then a slow sag. glowLevel() is the same curve.
    float envelope(float s) { return (1.0 + STRIKE * exp(-s / STRIKE_TAU)) * (SAG_FLOOR + (1.0 - SAG_FLOOR) * exp(-s / SAG_TAU)); }
    // 0 while the finger is down, easing to 1 over the 0.15 s around the release (no hard step in the column);
    // written without an edge difference, so FAR for a still-held note stays exact
    float letGo(float t, float t1) { float x = clamp((t - t1 + 0.03) / 0.15, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); }
    void main() {
      float h = max(vTop - vBot, 0.0);
      float r = min(vW * 0.5, h * 0.5);
      float d = sdRoundBox(vP - vec2(0.0, 0.5 * (vTop + vBot)), vec2(vW * 0.5, h * 0.5), r);
      float core = 1.0 - smoothstep(-0.025, 0.025, d);
      float halo = exp(-max(d, 0.0) * 7.0 / max(vW, 0.1)) * (1.0 - core);
      float axis = 1.0 - smoothstep(0.0, vW * 0.5, abs(vP.x));
      // te is the moment this stretch left the key: the column is the note's loudness over time, newest at the key
      float te = clamp(uNow - (vP.y - uBaseY) / uSpeed, vT0, vEnd);
      // Daniel, 2026-09-13: brightest with finger and pedal down together, and velocity always counts.
      //   finger down: 1.0, rising to PEDAL_BOOST from the moment the pedal also goes down
      //   released but the pedal still holds it: PEDAL_ONLY, with the envelope still sagging underneath
      float state = mix(mix(1.0, PEDAL_BOOST, pedalAt(te)), PEDAL_ONLY, letGo(te, vT1));
      // an old stretch dims as it rises
      float age = uNow - te;
      float after = exp(-max(age - 0.5, 0.0) / AFTERGLOW) * (1.0 - smoothstep(uLife * 0.6, uLife, age));
      // Light budget: the stretch near the key and any column still under a finger spend at full price;
      // older stretches share what renderFrame allows, so a long pedal dims its history instead of stacking it.
      float fresh = max(vHeld, 1.0 - smoothstep(FRESH_AGE * 0.5, FRESH_AGE, age));
      float energy = vBar * envelope(te - vT0) * state * after * mix(uDensity, 1.0, fresh);
      float fade = 1.0 - smoothstep(uTop * 0.6, uTop, vP.y);
      vec3 col = vColor * (core * (0.55 + 0.9 * axis * axis) + halo * 0.2) * energy;
      // a hot filament only in the attack, so each strike leaves a bright head that rises away
      float attack = exp(-(te - vT0) / STRIKE_TAU);
      col += mix(vColor, vec3(1.0), 0.35) * core * pow(axis, 3.0) * 0.6 * attack * energy;
      float fd = length((vP - vec2(0.0, vBot)) * vec2(1.4 / max(vW, 0.1), 1.4));
      col += vColor * vFoot * exp(-fd * 1.9) * 1.1;
      gl_FragColor = vec4(col * fade, 1.0);
    }`,
}));
trailMesh.frustumCulled = false;
scene.add(trailMesh);

let trailsDirty = false;
const trails = {
  next: 0, cueNext: 0,
  // gain: the column's colour scale (a replay of Daniel's own playing draws at half gain); cue: a replay's column, in its
  // own ring of slots above Daniel's (TRAIL_CUE)
  start(m, vel, t, gain = 1, cue = false) {
    const A = trailAttr, base = cue ? TRAIL_MAX : 0, count = cue ? TRAIL_CUE : TRAIL_MAX, ring = cue ? "cueNext" : "next";
    let slot = -1;
    for (let i = 0; i < count; i++) {
      const j = base + (this[ring] + i) % count;
      const gone = A.aT0.array[j] < -1e5 || t - A.aT2.array[j] > LIGHT.endCut;  // faded out: the shader skips it
      if (gone) { slot = j; break; }
    }
    if (slot < 0) slot = base + this[ring];  // every slot busy: recycle the oldest in ring order
    this[ring] = (slot - base + 1) % count;
    A.aX.array[slot] = keyX(m);
    A.aW.array[slot] = isBlack(m) ? 0.44 : 0.64;
    A.aT0.array[slot] = t;
    A.aT1.array[slot] = FAR;
    A.aT2.array[slot] = FAR;
    A.aVel.array[slot] = vel / 127;
    const c = noteColor(m, vel);
    A.aColor.array.set([c.r * gain, c.g * gain, c.b * gain], slot * 3);
    trailsDirty = true;
    // the ref keeps the float32 value actually stored: comparing against the double t would never match,
    // so release() and end() would silently drop every note and all trails would read as held forever
    return { slot, t0: A.aT0.array[slot] };
  },
  release(ref, t) {
    if (!ref || trailAttr.aT0.array[ref.slot] !== ref.t0) return;
    trailAttr.aT1.array[ref.slot] = Math.min(trailAttr.aT1.array[ref.slot], t);
    trailsDirty = true;
  },
  end(ref, t) {
    if (!ref || trailAttr.aT0.array[ref.slot] !== ref.t0) return;
    trailAttr.aT1.array[ref.slot] = Math.min(trailAttr.aT1.array[ref.slot], t);
    trailAttr.aT2.array[ref.slot] = Math.min(trailAttr.aT2.array[ref.slot], t);
    trailsDirty = true;
  },
  kill(ref) {  // gone at once, with no fade (a replay's columns leaving the canvas when REC starts)
    if (!ref || trailAttr.aT0.array[ref.slot] !== ref.t0) return;
    trailAttr.aT0.array[ref.slot] = -FAR;
    trailAttr.aT1.array[ref.slot] = -FAR;
    trailAttr.aT2.array[ref.slot] = -FAR;
    trailsDirty = true;
  },
  // Visible columns (the shader's cull test), and the light their old stretches spend: each released column's
  // level times its afterglow integrated from FRESH_AGE up to the top of the screen, as a share of the screen height.
  // Columns still under a finger are exempt in the shader, so they are not counted here either.
  scan(t) {
    const A = trailAttr, top = trailUniforms.uTop.value, G = LIGHT.afterglow;
    const screen = Math.max(1e-3, (top - RAIL_Y) / TRAIL_SPEED);  // seconds of column the screen shows
    let live = 0, oldLoad = 0, danLoad = 0;  // danLoad: Daniel's columns alone (a replay's left out)
    for (let j = 0; j < TRAIL_SLOTS; j++) {
      const t0 = A.aT0.array[j], gone = t - Math.min(t, A.aT2.array[j]);
      if (t0 < -1e5 || gone > LIGHT.endCut || RAIL_Y + gone * TRAIL_SPEED > top) continue;
      live++;
      if (A.aT1.array[j] > t) continue;
      const a0 = Math.max(gone, LIGHT.freshAge), a1 = Math.min(t - t0, TRAIL_LIFE * 0.8, screen);
      if (a1 <= a0) continue;
      const spent = G * (Math.exp(-(a0 - 0.5) / G) - Math.exp(-(a1 - 0.5) / G)) / screen;
      const load = lightLevel(A.aVel.array[j], false, 0, Math.max(0, t - t0 - 0.5 * (a0 + a1))) * releaseLevel(gone) * spent;
      oldLoad += load;
      if (j < TRAIL_MAX) danLoad += load;
    }
    return { live, oldLoad, danLoad };
  },
  liveCount(t) { return this.scan(t).live; },
  upload() {
    if (!trailsDirty) return;
    for (const attr of Object.values(trailAttr)) attr.needsUpdate = true;
    trailsDirty = false;
  },
};

// ----------------------------------------------------------------- sparks --
const SPARK_MAX = 2400;
const sparkUniforms = { uNow: { value: 0 }, uPx: { value: 1000 } };
const sparkGeo = new THREE.BufferGeometry();
const sparkAttr = {};
for (const [name, size] of [["position", 3], ["aVel", 3], ["aBirth", 1], ["aLife", 1], ["aSize", 1], ["aSeed", 1], ["aColor", 3]]) {
  const attr = new THREE.BufferAttribute(new Float32Array(SPARK_MAX * size), size);
  attr.setUsage(THREE.DynamicDrawUsage);
  sparkGeo.setAttribute(name, attr);
  sparkAttr[name] = attr;
}
sparkAttr.aBirth.array.fill(-FAR);
const sparkPoints = new THREE.Points(sparkGeo, new THREE.ShaderMaterial({
  uniforms: sparkUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `
    uniform float uNow, uPx;
    attribute vec3 aVel, aColor;
    attribute float aBirth, aLife, aSize, aSeed;
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      float age = uNow - aBirth;
      if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
      float k = age / aLife;
      vec3 p = position + aVel * age + vec3(sin(age * 2.7 + aSeed) * 0.35 * k, 0.9 * age * age, 0.0);
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_Position = projectionMatrix * mv;
      gl_PointSize = aSize * uPx * (1.0 - 0.6 * k) / max(-mv.z, 0.1);
      vAlpha = (1.0 - k) * (1.0 - k);
      vColor = aColor;
    }`,
  fragmentShader: `
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      float r = length(gl_PointCoord - 0.5);
      float a = smoothstep(0.5, 0.0, r);
      gl_FragColor = vec4(vColor * a * a * vAlpha * 3.2, 1.0);
    }`,
}));
sparkPoints.frustumCulled = false;
scene.add(sparkPoints);
let sparkNext = 0;
let sparksDirty = false;
// Math.random, unless a receipt seeds the sparks (__piano.jam.seedSparks) so a take and its control scatter the same ones
let sparkRandom = Math.random;
function burst(m, vel, t) {
  const count = Math.round(6 + 20 * (vel / 127));
  const c = noteColor(m, vel);
  const x = keyX(m);
  const rnd = sparkRandom;
  for (let i = 0; i < count; i++) {
    const j = sparkNext;
    sparkNext = (sparkNext + 1) % SPARK_MAX;
    sparkAttr.position.array.set([x + (rnd() - 0.5) * 0.5, RAIL_Y + 0.05, TRAIL_Z + 0.1], j * 3);
    sparkAttr.aVel.array.set([(rnd() - 0.5) * 1.8, 1.6 + rnd() * 4.5 * (0.5 + vel / 254),
                              (rnd() - 0.3) * 0.9], j * 3);
    sparkAttr.aBirth.array[j] = t;
    sparkAttr.aLife.array[j] = 0.7 + rnd() * 1.6;
    sparkAttr.aSize.array[j] = 0.16 + rnd() * 0.26;
    sparkAttr.aSeed.array[j] = rnd() * 6.283;
    sparkAttr.aColor.array.set([c.r * 1.3, c.g * 1.3, c.b * 1.3], j * 3);  // no white lift: sparks keep the note's hue
  }
  sparksDirty = true;
}

// ------------------------------------------------------------ key motion --
// The surface colour is already full by glow 0.4, so above a plain held note the emissive climbs faster: the
// pedal boost and hard velocities show on the key itself, capped so a strike doesn't burn to white.
const keyLift = (black, g) => (black ? g * 1.7 : Math.min(1.4, g * 0.45 + Math.max(0, g - 0.8) * 0.9));
const addScaled = (target, c, s) => { target.r += c.r * s; target.g += c.g * s; target.b += c.b * s; };  // THREE.Color has no addScaled
function updateKeys(dt, t) {
  const steps = Math.max(1, Math.ceil(dt / (1 / 240)));
  const h = dt / steps;
  // Claude's share of the canvas (jam view): cueStage.mix is 1 on the stage and 0 while Claude is off the canvas
  const onStage = cueStage.on, mix = cueStage.mix;
  const breath = 0.96 + 0.04 * Math.cos(t * Math.PI);  // the ghost fill breathes 0.92-1.00 at 0.5 Hz
  // found (8.5): every ghost rim grows once in size, 1.0 -> 1.15 -> 1.0 over 200 ms, never in brightness
  const sinceFound = t - jamGhosts.foundAt;
  const pulse = sinceFound >= 0 && sinceFound <= GHOST_FOUND.sec ? 1 + GHOST_FOUND.scale * Math.sin(Math.PI * sinceFound / GHOST_FOUND.sec) : 1;
  let cueLit = 0;
  for (const k of keys.values()) {
    // Two springs per key, drawn together: Daniel's (depth, v) moves toward his target alone, and Claude's press (cueDepth,
    // cueV) toward Claude's, only while Claude is on the stage. Claude never moves the state of Daniel's key, so on the frame
    // Claude leaves the canvas (REC in auto) every key is exactly where it would be had Claude never played (A5).
    const target = k.target, cueTarget = onStage ? k.cueTarget : 0;
    const pressing = target > k.depth + 1e-4, cuePressing = cueTarget > k.cueDepth + 1e-4;
    const stiffness = pressing ? 4200 : 820;   // fast down, springy up with a small overshoot
    const damping = pressing ? 118 : 36;
    const cueStiffness = cuePressing ? 4200 : 820, cueDamping = cuePressing ? 118 : 36;
    const cueMoves = cueTarget > 0 || k.cueDepth !== 0;
    for (let i = 0; i < steps; i++) {
      k.v = (k.v || 0) + ((target - k.depth) * stiffness - (k.v || 0) * damping) * h;
      k.depth += k.v * h;
      if (cueMoves) {
        k.cueV += ((cueTarget - k.cueDepth) * cueStiffness - k.cueV * cueDamping) * h;
        k.cueDepth += k.cueV * h;
      }
    }
    if (Math.abs(k.depth) < 1e-5 && target === 0 && Math.abs(k.v) < 1e-4) { k.depth = 0; k.v = 0; }
    if (Math.abs(k.cueDepth) < 1e-5 && cueTarget === 0 && Math.abs(k.cueV) < 1e-4) { k.cueDepth = 0; k.cueV = 0; }
    // the key shows the deeper press; a key only Claude moves shows Claude's spring whole (its springy overshoot too)
    const shown = k.cueDepth === 0 ? k.depth : target > 0 || Math.abs(k.depth) > 1e-4 ? Math.max(k.depth, k.cueDepth) : k.cueDepth;
    k.pivot.rotation.x = shown / k.lever;
    k.glow = damp(k.glow, k.glowTarget, k.glowTarget > k.glow ? 0.012 : 0.22, dt);
    k.cueGlow = damp(k.cueGlow, k.cueGlowTarget, k.cueGlowTarget > k.cueGlow ? 0.012 : 0.22, dt);
    if (k.cueGlow > 0.004 || k.ghostLevel > 0.004) cueLit++;  // what the glass would have to draw
    const danTint = Math.min(1, k.glow * 2.5);
    const cue = k.cueGlow * mix;              // Claude's light as the stage shows it
    const cueShare = 1 - danTint;             // a key Daniel lights keeps his colour
    // Ghost states (8.5): target (a hover, a Show, Try's chord now: the full rim and fill), incoming (Try's next chord on the
    // last beat: a lighter rim, no fill), hold (an inner rim on the pitch classes the two share). A hover Claude sends
    // fades in over about 400 ms (8.9); the others at once.
    const gTarget = jamGhosts.target.has(k.m), gHold = jamGhosts.hold.has(k.m);
    const gIncoming = !gTarget && jamGhosts.incoming.has(k.m);
    const ghosted = gTarget || gIncoming || gHold;
    k.ghostLevel = damp(k.ghostLevel, ghosted ? 1 : 0, ghosted ? (jamGhosts.slow.has(k.m) ? GHOST_FADE.remote : GHOST_FADE.in) : GHOST_FADE.out, dt);
    k.ghostFull = damp(k.ghostFull, gIncoming ? 0 : 1, GHOST_FADE.in, dt);
    k.holdLevel = damp(k.holdLevel, gHold ? 1 : 0, ghosted ? GHOST_FADE.in : GHOST_FADE.out, dt);
    k.rimLevel = damp(k.rimLevel, k.cueTarget > 0 && k.target > 0 ? 1 : 0, 0.05, dt);
    const ghost = k.ghostLevel * mix, rim = k.rimLevel * mix;
    const ghostFill = ghost * k.ghostFull;  // only a target ghost has the breathing fill
    // a lit white key takes the note's colour into its surface instead of laying a tint over ivory, and sheds
    // most of its white clearcoat sheen, so it reads as coloured rather than pastel (pedal-held keys too)
    if (!k.black) {
      keyAlbedo.copy(k.color);
      const peak = Math.max(keyAlbedo.r, keyAlbedo.g, keyAlbedo.b);
      if (peak > 1) keyAlbedo.multiplyScalar(1 / peak);  // a surface can't reflect more than it receives
      k.material.color.copy(IVORY).lerp(keyAlbedo, danTint * 0.95);
      let coat = danTint;
      if (cue > 0.004 && k.cueReplay) {  // a replay of Daniel's playing tints like his keys, faded; Claude's keys stay ivory
        const rt = Math.min(1, cue * 2.5) * cueShare;
        k.material.color.lerp(k.cueColor, rt * 0.95);
        coat = Math.max(coat, rt);
      } else if (cue > 0.004) {  // Claude's own key: a pale moonlight surface under the capped moonlight (MOON_KEY)
        k.material.color.lerp(k.cueSurface, Math.min(1, cue * MOON_KEY.fade) * cueShare);  // its clearcoat stays ivory's
      }
      if (ghostFill > 0.004) k.material.color.lerp(GHOST_TINT, GHOST_RIM.whiteFill * ghostFill * breath * (1 - Math.min(1, (k.glow + cue) * 2.5)));
      k.material.clearcoat = 0.5 - 0.35 * coat;  // never 0, so the material never recompiles
    }
    k.material.emissive.copy(k.color).multiplyScalar(keyLift(k.black, k.glow));
    if (cue > 0.004) {
      let lift = keyLift(k.black, cue) * cueShare;
      if (k.black && !k.cueReplay) {  // softer on lacquer, and never past the bloom threshold (MOON_KEY.blackPeak)
        lift = Math.min(lift * MOON_KEY.black, MOON_KEY.blackPeak / Math.max(k.cueColor.r, k.cueColor.g, k.cueColor.b, 1e-3));
      }
      addScaled(k.material.emissive, k.cueColor, lift);
    }
    if (ghostFill > 0.004 && k.black) addScaled(k.material.emissive, GHOST, 0.1 * ghostFill * breath);
    // the frame: a ghost's rim (an incoming one lighter), or the thin moonlight rim of a key both hands hold
    const rimBase = k.black ? GHOST_RIM.black : GHOST_RIM.white;
    const ghostRim = ghost * rimBase * lerp(k.black ? GHOST_RIM.incomingBlack : GHOST_RIM.incomingWhite, 1, k.ghostFull);
    const frameOpacity = Math.max(ghostRim, rim * 0.5);
    k.frame.visible = frameOpacity > 0.004 && !ghostFramesHidden;
    if (k.frame.visible) {
      k.frame.material.opacity = frameOpacity;
      k.frame.material.color.copy(ghostRim >= rim * 0.5 ? (k.black ? GHOST : GHOST_ON_IVORY) : MOON);
    }
    const holdRim = k.holdLevel * mix * rimBase * lerp(k.black ? GHOST_RIM.incomingBlack : GHOST_RIM.incomingWhite, 1, k.ghostFull);
    k.holdFrame.visible = holdRim > 0.004 && !ghostFramesHidden;
    if (k.holdFrame.visible) k.holdFrame.material.opacity = holdRim;
    const p = ghostRim > 0.004 ? pulse : 1;
    if (p !== k.pulse) { k.pulse = p; k.frame.scale.set(p, p, 1); k.holdFrame.scale.set(p, p, 1); }
  }
  cueStage.lit = cueLit;
  for (const nl of noteLights) {
    nl.target *= Math.exp(-dt / 0.7);
    nl.level = damp(nl.level, nl.target, 0.03, dt);
    nl.light.intensity = nl.level;
    nl.light.color.copy(nl.color);
  }
}
function lightNote(m, vel) {
  const nl = noteLights[noteLightNext];
  noteLightNext = (noteLightNext + 1) % noteLights.length;
  nl.light.position.x = keyX(m);
  noteColor(m, vel, nl.color);
  nl.target = 5 + 13 * (vel / 127);
}

// ----------------------------------------------------------------- camera --
// recent: Daniel's strikes; cueRecent: Claude's, in a list of their own (dropped when REC takes Claude off the canvas), so
// Claude's strikes never push Daniel's out of what the camera remembers
const cam = { x: 0, span: framing.minSpan, recent: [], cueRecent: [], heardAt: -Infinity, hurry: 0 };
// The view a page with no Claude would have (Daniel's notes alone), eased beside the one shown. On the frame Claude leaves
// the canvas (REC in auto) the shown view takes it over, so a take is framed exactly as it would be had Claude never played.
const camDan = { x: 0, span: framing.minSpan, hurry: 0 };
const lookTarget = new THREE.Vector3();
function hintCamera(m, t, cue = false) {  // cue: Claude's
  const list = cue ? cam.cueRecent : cam.recent;
  list.push({ x: keyX(m), t, cue });
  if (list.length > 96) list.shift();
}
// The follow camera (9:16). What frames the view:
// - Daniel's notes: every key he holds, and the notes he struck in the CAM.window s up to his latest strike while he plays
//   (so a long pedalled chord keeps its place), else in the last CAM.window s.
// - Claude's notes: every key Claude holds or hovers now (a play, a hover, a progression's step, a replay), however long
//   ago it began; the last CAM.cueLinger s of Claude's strikes, so a short cue is not lost between frames; and the steps of
//   a started sequence that land in the next CAM.lookahead s (cuePlans: the player knows the schedule), so the view is
//   already moving when a progression jumps register, without leaving the step that sounds now.
// Daniel plays while any note of his sounds (a finger down, or the pedal holding it) and for CAM.grace s after the last
// one ends. The grace is his own chord spacing (his sessions in state/arsenal/performance, 2026-09-14: chords of three or
// more notes struck p90 4.8 s apart, silences between his sound ending and his next strike p99 4.9 s). While he plays,
// Claude's notes share the frame only if they fit with his in CAM.union white keys (the next steps too, if they also fit),
// else the view stays on his: it never swings to Claude's between his chords. Once his sound has ended and the grace has
// passed, the view goes to Claude's notes.
// The camera eases (1.2 s pan, 1.6 s zoom) and hurries, down to CAM.hurry s, while keys it must frame lie outside the view
// it has, so a chord struck outside it, or Claude's next step in another register, is reached in time.
// Off the canvas (glass, or auto while REC runs) Claude never steers (cueStage.on).
const CAM = { window: 6, grace: 4.8, cueLinger: 1.5, union: 36, lookahead: 1.5, hurry: 0.3 };
const camAdd = (box, x) => { if (x < box.lo) box.lo = x; if (x > box.hi) box.hi = x; };
// Ease a view (cam, the one shown, or camDan) toward the keys lo..hi (world x; lo > hi: none to frame).
function easeCamera(c, lo, hi, dt, snap) {
  let targetX = 0, targetSpan = 57, hurry = 0;
  if (framing.follow) {
    targetSpan = lo <= hi ? clamp(hi - lo + 6, framing.minSpan, 57) : Math.max(c.span, framing.minSpan);
    targetX = lo <= hi ? (lo + hi) / 2 : c.x;
    targetX = clamp(targetX, -28.5 + targetSpan / 2, 28.5 - targetSpan / 2);
    // how far the keys to frame lie outside the view the camera has now (in white keys): hurry 0 inside it, 1 from 2 keys out
    if (lo <= hi) hurry = clamp(Math.max(c.x - c.span / 2 + 1 - lo, hi - c.x - c.span / 2 + 1) / 2, 0, 1);
  }
  c.hurry = hurry;
  c.x = snap ? targetX : damp(c.x, targetX, lerp(1.2, CAM.hurry, hurry), dt);
  c.span = snap ? targetSpan : damp(c.span, targetSpan, lerp(1.6, CAM.hurry, hurry), dt);
}
function updateCamera(dt, t, snap = false) {
  const dan = { lo: Infinity, hi: -Infinity }, cue = { lo: Infinity, hi: -Infinity }, ahead = { lo: Infinity, hi: -Infinity };
  let sounds = false, danLast = -Infinity;
  for (const [m, st] of sounding) {  // a key Daniel holds keeps his hands in the frame, however old the strike
    if (m < KEY.first || m > KEY.last) continue;
    sounds = true;
    if (st.held) camAdd(dan, keyX(m));
  }
  if (sounds) cam.heardAt = t;
  const plays = t - cam.heardAt < CAM.grace;
  for (const n of cam.recent) if (n.t > danLast) danLast = n.t;
  const danEnd = plays ? Math.min(t, danLast) : t;
  for (const n of cam.recent) if (danEnd - n.t < CAM.window && n.t <= t) camAdd(dan, n.x);
  if (cueStage.on) for (const n of cam.cueRecent) if (t - n.t < CAM.cueLinger) camAdd(cue, n.x);
  if (cueStage.on && framing.follow) {
    for (const st of cueSounding.values()) if (st.m >= KEY.first && st.m <= KEY.last) camAdd(cue, keyX(st.m));
    for (const m of cueView.ghost) if (m >= KEY.first && m <= KEY.last) camAdd(cue, keyX(m));
    cueAhead(t, ahead);
  }
  if (ahead.lo <= ahead.hi && cue.lo > cue.hi) { cue.lo = ahead.lo; cue.hi = ahead.hi; ahead.lo = Infinity; ahead.hi = -Infinity; }
  let lo = dan.lo, hi = dan.hi;
  if (cue.lo <= cue.hi) {
    const fits = (a, b) => Math.max(a.hi, b.hi) - Math.min(a.lo, b.lo) + 6 <= CAM.union;
    const both = { lo: Math.min(cue.lo, ahead.lo), hi: Math.max(cue.hi, ahead.hi) };
    if (!plays || dan.lo > dan.hi) { lo = both.lo; hi = both.hi; }  // Daniel has stopped: Claude's notes
    else if (fits(dan, both)) { lo = Math.min(lo, both.lo); hi = Math.max(hi, both.hi); }
    else if (fits(dan, cue)) { lo = Math.min(lo, cue.lo); hi = Math.max(hi, cue.hi); }
  }
  easeCamera(cam, lo, hi, dt, snap);
  easeCamera(camDan, dan.lo, dan.hi, dt, snap);  // the same view with Claude's notes left out

  const vfov = THREE.MathUtils.degToRad(framing.fov);
  const aspect = framing.w / framing.h;
  const tanH = Math.tan(vfov / 2) * aspect;
  const dist = cam.span / 2 / tanH + 7;
  const elev = THREE.MathUtils.degToRad(framing.follow ? 22 : 17) + Math.sin(t * 0.13) * 0.012;
  const yaw = Math.sin(t * 0.071) * (framing.follow ? 0.06 : 0.035);
  lookTarget.set(cam.x, 0.4, -0.5);
  camera.position.set(lookTarget.x + dist * Math.sin(yaw) * Math.cos(elev),
                      lookTarget.y + dist * Math.sin(elev),
                      lookTarget.z + dist * Math.cos(yaw) * Math.cos(elev));
  camera.lookAt(lookTarget);
  // Lens shift instead of tilting: the keyboard sits low in the frame and the trails get the sky.
  const shift = framing.follow ? 0.25 : 0.29;
  camera.setViewOffset(framing.w, framing.h, 0, -shift * framing.h, framing.w, framing.h);
  trailUniforms.uTop.value = RAIL_Y + dist * Math.tan(vfov / 2) * (1 + 2 * shift) * 0.98;
  sparkUniforms.uPx.value = framing.h * renderScale / (2 * Math.tan(vfov / 2));
}

// ------------------------------------------------------------------ looks --
// Daniel, 2026-09-15: "can we all try at a dedicated synthesia lookinf mode like the original?" and "Do you think we can make a
// 3d model of my arturia keylab in the visualizer? I think it would be really cool to see the keyboard in the visualizer!"
// Two hosts share the stage with the page's own look:
//   Scheme: what draws the music (PIANO-V2-SPEC.md section 1, the piano-next.js scheme host). "classic" is this page's own
//     columns and sparks; every other scheme is ./piano/schemes/<id>.js, { id, name, create(ctx) } -> noteOn(m, vel, t),
//     noteRelease(m, t), noteEnd(m, t), pedal(down, raw, t), update(dt, t, frame), resize(framing), setActive(on), dispose().
//   Instrument: the body around the keys (instruments-plan.md section 3). "page" is this page's own lacquer piano; every other
//     is ./piano/instruments/<id>.js, { id, name, create(ctx) } -> { group, update(dt, t, state), resize(framing),
//     setActive(on), dispose() } plus hints (keyStyle, keySpan, stage / stageHints / hints with floorY and hideHostBody).
// An instrument's `state` (looks.state, one object refreshed in place every frame, read-only to the instrument):
//   pressed   Map midi -> the live sounding entry, while the FINGER is down. Deleted on release even if the pedal holds it.
//   pedal     CC64 is down.
//   chord     { name, nns, key } while a chord reads, else null.
//   notes     a 64-entry ring of { midi, vel, t } strikes — the strike record, the only place a note shorter than one frame
//             shows at all.
//   sounding  Map midi -> { vel (1-127), t0, held, pedal, tRelease, strike } — the SUSTAIN record, added 2026-09-17 for the
//             string light: an entry exists exactly while the page considers that note sounding, which is what the ear hears.
//             It mirrors the notes engine's own map, so it is the page's answer and not a guess: `held` is the finger,
//             `pedal` (= !held) is a sound the damper pedal alone is holding, `tRelease` is when the finger lifted (null
//             while held), `t0` and `tRelease` are seconds on the same clock update() is handed, and `strike` counts that
//             key's strikes so a re-strike inside one frame is still one event (t0 cannot tell you). The entry objects are
//             pooled per key, so their identity is stable across frames and across re-strikes; the map itself is refreshed
//             in place. A pedal-held sound has NO time limit — it ends on the pedal lift, a re-strike or a panic, and its
//             entry leaves the map exactly then. Pitfall: a note struck and released between two frames never appears here
//             (it is born and dies inside the gap) — flash from `notes`, sustain from `sounding`.
// Both load with import(), one of each at a time: a switch disposes the one before (the GPU memory it held comes back), and a
// scheme starts from what is sounding now. Both are error-isolated: a module that fails to import, to create or in any call
// is disposed, says so in a toast, and the page falls back to its own look (the stored choice stays, so a fixed module comes
// back on the next load). Both persist in localStorage. Neither changes while REC runs (a module load and its shader
// compiles would hitch the take); REC takes the canvas, so both are in every take.
// Who draws what while a scheme is active (the rule):
//   - this page's classic columns (Daniel's; a replay's still show) and sparks are hidden;
//   - spectacle keeps its world: sky, lake, forest or city, weather, fog, theme light and bloom, the floor ripples and chord
//     rings, and the chord diagram of every chord view but "Atmosphere" (theory, like the overlay). The "Atmosphere" chord
//     view is itself a note scheme, so its note layers are hidden while a scheme is active (threads, motes, veils, curtains,
//     halo, note glass; on the lake, Moonwater's strands, note labels, leaders, heading and fifths inlays): spectacle draws
//     what it draws in every other chord view, and the page's own chord label shows;
//   - the overlay (chord name, Nashville number, the staff and its key signature), Claude's moonlight keys, ghosts and chip, the
//     jam glass and the floor pool stay the page's;
//   - schemes and instruments hear Daniel's notes only, so REC in auto (Claude off the canvas) draws them as with no Claude.
// An instrument replaces the page's lacquer body (keybed, cheeks, back rail, felt, rail light) unless its hints say
// hideHostBody: false, since every model was built and judged around bare keys. It hides the keys outside its keySpan, colours
// the keys from keyStyle (whiteColor, blackColor; the atmosphere's theme still tints them), and lowers the floor (and the jam's
// floor pool with it) to its floorY. All of it is restored on a switch.
const LOOK_KEYS = { scheme: "arsenal.piano.scheme", instrument: "arsenal.piano.instrument" };
const LOOK_ID = /^[a-z0-9-]+$/;
// probe: a bake-off seat whose entry may not have landed; it is listed once its file answers (probeLooks)
const SCHEMES = [
  { id: "classic", name: "Classic trails" },
  { id: "upright-roll", name: "Upright Roll" },
  { id: "synth-vandor", name: "Straight Roll" },
  { id: "synth-navi", name: "Bead & Beam" },
  { id: "synth-heimdall", name: "Glow Echo" },
  { id: "synth-sol", name: "Afterglow Roll" },
  { id: "synth-asta", name: "synth-asta", probe: true },
  { id: "synth-rill", name: "synth-rill", probe: true },
];
const INSTRUMENTS = [
  { id: "page", name: "Page keys" },
  { id: "keylab88mk3", name: "KeyLab 88 mk3" },
  { id: "concert-grand", name: "Concert grand" },
  { id: "upright", name: "Upright" },
  { id: "suitcase-ep", name: "Suitcase EP" },
  { id: "vintage-synth", name: "Vintage synth" },
  { id: "glass-piano", name: "Crystal grand" },
];
const LOOK_BUILTIN = { scheme: "classic", instrument: "page" };
const SCHEME_METHODS = ["noteOn", "noteRelease", "noteEnd", "pedal", "update", "resize", "setActive", "dispose"];
const PAGE_LOOK = { white: IVORY.clone(), black: new THREE.Color(0x0a0a0d), floorY: floor.position.y };
const pageBody = [...scene.children.filter((o) => o.isMesh && o.material === lacquer), felt, railLine];  // keybed, cheeks, rail
const looks = {
  ready: false,
  scheme: { id: "classic", active: null, loading: null, token: 0, errors: 0, lastError: null },
  instrument: { id: "page", active: null, loading: null, token: 0, errors: 0, lastError: null, hints: null },
  registered: new Map(),  // id -> scheme module, from __piano.registerScheme (scheme development)
  listed: new Map(),      // probe id -> its module's name, once its file answers
  counts: { noteOn: 0, noteRelease: 0, noteEnd: 0, pedal: 0 },
  hidden: 0,              // spectacle's Atmosphere note layers hidden in the last frame
  // what a scheme's update() and an instrument's update() get: one object each, refreshed in place every frame
  frame: { info: null, sounding: null, pedalDown: false, framing: null, view: { top: 30, pointScale: 1000 } },
  // state.sounding mirrors the page's own sound model (the notes engine's `sounding` map): an entry exists exactly while the
  // page holds the note sounding, finger or pedal. Entry objects are pooled per key, so an instrument may hold on to one.
  state: { pressed: new Map(), pedal: false, chord: null, notes: [], sounding: new Map() },
  sounds: new Map(),        // the pool behind state.sounding: midi -> the one entry object this key ever hands out
  chord: { name: "", nns: "", key: "", from: null, keyFrom: null },
};
let lookFramingInfo = null;
function lookFraming() {  // the frame in framing pixels, as schemes and instruments are told it (a new object on a change)
  if (!lookFramingInfo || lookFramingInfo.id !== framing.id) {
    lookFramingInfo = Object.freeze({ id: framing.id, width: framing.w, height: framing.h, w: framing.w, h: framing.h });
  }
  return lookFramingInfo;
}
// Schemes turn gl_FragCoord into framing pixels with renderer.getPixelRatio(). This page renders Ultra and Cinema by sizing the
// drawing buffer (renderScale) at a pixel ratio of 1, so the ratio a scheme is told includes renderScale: its bands stay put.
function lookPixelRatio() { return renderer.getPixelRatio() * renderScale; }
const lookRenderer = (() => {
  const bound = new Map();
  return new Proxy(renderer, {
    get(target, prop) {
      if (prop === "getPixelRatio") return lookPixelRatio;
      const v = Reflect.get(target, prop, target);
      if (typeof v !== "function") return v;
      let f = bound.get(prop);
      if (!f) { f = v.bind(target); bound.set(prop, f); }
      return f;
    },
  });
})();
const schemeCtx = Object.freeze({
  THREE, scene, camera, renderer: lookRenderer, clock, keyX, isBlack, noteColor, noteCss,
  KEY: Object.freeze({ first: KEY.first, last: KEY.last }), RAIL_Y, TRAIL_Z,
  get framing() { return lookFraming(); },
});
function instrumentCtx() {
  return {
    THREE, scene, keyX, isBlack, noteColor, noteCss, RoundedBoxGeometry, RAIL_Y, TRAIL_Z, KEY: { ...KEY }, framing: lookFraming(),
    span: { first: KEY.first, last: KEY.last, left: keyX(KEY.first) - 0.5, right: keyX(KEY.last) + 0.5, width: 52, keyTop: 0,
            blackTop: KEY.blackTop, keyFront: KEY.back + KEY.whiteL, keyBack: KEY.back, bedTop: -0.8, floorY: PAGE_LOOK.floorY,
            mmPerUnit: 1225.7 / 52 },
    fonts: { display: FONT.display },
    options: {},
  };
}
function lookList(kind) {
  if (kind === "instrument") return INSTRUMENTS.map((s) => ({ id: s.id, name: s.name, listed: true }));
  const out = SCHEMES.map((s) => ({ id: s.id, name: looks.registered.get(s.id)?.name || looks.listed.get(s.id) || s.name,
                                    listed: !s.probe || looks.listed.has(s.id) || looks.registered.has(s.id) }));
  for (const [id, mod] of looks.registered) if (!out.some((s) => s.id === id)) out.push({ id, name: mod.name, listed: true });
  return out;
}
function lookModuleProblem(mod, id) {
  if (!mod || typeof mod !== "object") return "the module has no default export object";
  if (typeof mod.id !== "string" || !LOOK_ID.test(mod.id)) return "id must be lowercase letters, digits and dashes";
  if (id !== undefined && mod.id !== id) return `the module's id "${mod.id}" does not match its file "${id}"`;
  if (typeof mod.name !== "string" || !mod.name) return "name is missing";
  if (typeof mod.create !== "function") return "create(ctx) is missing";
  return "";
}
async function lookModule(kind, id) {  // id is one of the listed ids (checked by the caller)
  if (kind === "scheme" && looks.registered.has(id)) return looks.registered.get(id);
  const mod = kind === "scheme" ? await import(`./piano/schemes/${id}.js`) : await import(`./piano/instruments/${id}.js`);
  return mod.default;
}
function lookFailed(kind, entry, what, e) {
  const L = looks[kind];
  L.errors++;
  L.lastError = `${entry.id} ${what}: ${errText(e)}`;
  console.error(`[piano] ${kind} ${entry.id} ${what} failed:`, e);
  toast(`${kind === "scheme" ? "Scheme" : "Instrument"} ${entry.name}: ${what} failed (${errText(e)}). Showing ${
    kind === "scheme" ? "Classic trails" : "Page keys"}.`, true);
  if (kind === "scheme") unmountScheme(); else unmountInstrument();
  L.id = LOOK_BUILTIN[kind];
  L.loading = null;
  syncLooksUi();
  return false;
}
// Note events for the active scheme and the instrument's state: Daniel's notes on the 88 keys (the notes engine calls these)
function lookEvent(method, a, b, c) {
  looks.counts[method]++;
  const s = looks.scheme.active;
  if (!s) return;
  try { s.instance[method](a, b, c); } catch (e) { lookFailed("scheme", s, method, e); }
}
function lookNoteOn(m, vel, t, st) {
  if (m < KEY.first || m > KEY.last) return;
  const S = looks.state;
  S.pressed.set(m, st);  // the sounding entry itself: { vel, t0, held, ... }
  const n = S.notes.length < 64 ? { midi: 0, vel: 0, t: 0 } : S.notes.shift();
  n.midi = m; n.vel = vel; n.t = t;
  S.notes.push(n);
  lookEvent("noteOn", m, vel, t);
}
function lookNoteOff(m, t, pedalHolds) {
  if (m < KEY.first || m > KEY.last) return;
  looks.state.pressed.delete(m);
  lookEvent(pedalHolds ? "noteRelease" : "noteEnd", m, t);
}
function lookNoteEnd(m, t) {  // a repeat strike, a pedal lift or all-notes-off ends a sound
  if (m < KEY.first || m > KEY.last) return;
  looks.state.pressed.delete(m);
  lookEvent("noteEnd", m, t);
}
let atmosphereLook = false;  // spectacle's atmosphere is on (its classic(on) callback says so)
function applyClassicLook() {  // the page's own columns and sparks show with no scheme and no atmosphere
  const classic = !atmosphereLook && !looks.scheme.active;
  trailUniforms.uAtmosphere.value = classic ? 0 : 1;
  sparkPoints.visible = classic;
}
function unmountScheme() {
  const s = looks.scheme.active;
  looks.scheme.active = null;
  if (s) {
    try { s.instance.setActive(false); } catch (e) { console.error(`[piano] scheme ${s.id} setActive(false) failed:`, e); }
    try { s.instance.dispose(); } catch (e) { console.error(`[piano] scheme ${s.id} dispose failed:`, e); }
  }
  applyClassicLook();
}
async function selectScheme(id, persist = true) {
  const L = looks.scheme;
  const listed = lookList("scheme").find((s) => s.id === id && s.listed);
  if (!listed) return false;
  if (rec.state !== "idle" || rec.arming) { toast("Stop recording before changing the scheme", true); syncLooksUi(); return false; }
  const token = ++L.token;
  if (persist) safeSet(LOOK_KEYS.scheme, id);
  if (id === LOOK_BUILTIN.scheme) { unmountScheme(); L.id = id; L.loading = null; syncLooksUi(); return true; }
  L.loading = id;
  syncLooksUi();
  let mod;
  try {
    mod = await lookModule("scheme", id);
    const problem = lookModuleProblem(mod, id);
    if (problem) throw new Error(problem);
  } catch (e) {
    return token === L.token ? lookFailed("scheme", listed, "load", e) : false;
  }
  if (token !== L.token) return false;  // a later pick won
  unmountScheme();
  const entry = { id, name: mod.name, instance: null };
  try {
    const instance = mod.create(schemeCtx);
    const missing = SCHEME_METHODS.filter((k) => !instance || typeof instance[k] !== "function");
    if (missing.length) {
      try { instance?.dispose?.(); } catch { /* half-built */ }
      throw new Error(`create() returned an instance without ${missing.join(", ")}`);
    }
    entry.instance = instance;
    instance.setActive(false);
    instance.resize(lookFraming());
    const t = clock();
    for (const [m, st] of sounding) {  // start from what is sounding now
      if (m < KEY.first || m > KEY.last) continue;
      instance.noteOn(m, st.vel, st.t0);
      if (!st.held) instance.noteRelease(m, st.tRelease || t);
    }
    if (sustain) instance.pedal(true, 127, t);
    instance.setActive(true);
  } catch (e) {
    if (entry.instance) { try { entry.instance.setActive(false); entry.instance.dispose(); } catch { /* broken */ } }
    return lookFailed("scheme", listed, "create", e);
  }
  L.active = entry;
  L.id = id;
  L.loading = null;
  applyClassicLook();
  syncLooksUi();
  return true;
}
function instrumentHints(def, handle) {
  const stage = { ...(def.hints || {}), ...(handle.hints || {}), ...(handle.stageHints || {}), ...(handle.stage || {}) };
  const style = handle.keyStyle || def.keyStyle || null;
  const span = handle.keySpan || def.keySpan || null;
  return {
    white: Number.isFinite(style?.whiteColor) ? style.whiteColor : null,
    black: Number.isFinite(style?.blackColor) ? style.blackColor : null,
    first: Number.isFinite(span?.first) ? Math.max(KEY.first, span.first) : KEY.first,
    last: Number.isFinite(span?.last) ? Math.min(KEY.last, span.last) : KEY.last,
    floorY: Number.isFinite(stage.floorY) ? Math.min(PAGE_LOOK.floorY, stage.floorY) : PAGE_LOOK.floorY,
    hideBody: stage.hideHostBody !== false && stage.hideStageBody !== false,
  };
}
const lookBlack = new THREE.Color();
function paintBlackKeys() {
  const h = looks.instrument.hints;
  lookBlack.copy(PAGE_LOOK.black);
  if (h && h.black !== null) lookBlack.set(h.black);
  for (const k of keys.values()) if (k.black) k.material.color.copy(lookBlack);
}
function applyInstrumentHints(h) {  // null: the page's own keys, body, floor and pool
  IVORY.copy(PAGE_LOOK.white);
  if (h && h.white !== null) IVORY.set(h.white);
  paintBlackKeys();
  moonSurfaceScales.clear();  // Claude's key surface is fitted to the ivory
  for (const k of keys.values()) k.pivot.visible = !h || (k.m >= h.first && k.m <= h.last);
  for (const o of pageBody) o.visible = !h || !h.hideBody;
  floor.position.y = h ? h.floorY : PAGE_LOOK.floorY;
  poolMesh.position.y = POOL.y + (floor.position.y - PAGE_LOOK.floorY);
}
function unmountInstrument() {
  const L = looks.instrument, a = L.active;
  L.active = null;
  if (a) {
    try { a.handle.setActive?.(false); } catch (e) { console.error(`[piano] instrument ${a.id} setActive(false) failed:`, e); }
    try { a.handle.dispose?.(); } catch (e) { console.error(`[piano] instrument ${a.id} dispose failed:`, e); }
    a.handle.group.removeFromParent();
  }
  if (L.hints) { L.hints = null; applyInstrumentHints(null); }
}
async function selectInstrument(id, persist = true) {
  const L = looks.instrument;
  const listed = lookList("instrument").find((s) => s.id === id);
  if (!listed) return false;
  if (rec.state !== "idle" || rec.arming) { toast("Stop recording before changing the instrument", true); syncLooksUi(); return false; }
  const token = ++L.token;
  if (persist) safeSet(LOOK_KEYS.instrument, id);
  if (id === LOOK_BUILTIN.instrument) { unmountInstrument(); L.id = id; L.loading = null; syncLooksUi(); return true; }
  L.loading = id;
  syncLooksUi();
  let def;
  try {
    def = await lookModule("instrument", id);
    const problem = lookModuleProblem(def, id);
    if (problem) throw new Error(problem);
  } catch (e) {
    return token === L.token ? lookFailed("instrument", listed, "load", e) : false;
  }
  if (token !== L.token) return false;
  unmountInstrument();
  let handle = null;
  try {
    handle = def.create(instrumentCtx());
    if (!handle || !handle.group || !handle.group.isObject3D || typeof handle.update !== "function") {
      throw new Error("create() returned no group or no update()");
    }
    if (!handle.group.parent) scene.add(handle.group);
    L.active = { id, name: def.name, handle, def };
    L.hints = instrumentHints(def, handle);
    applyInstrumentHints(L.hints);
    handle.resize?.(lookFraming());
    handle.setActive?.(true);
  } catch (e) {
    if (!L.active && handle) {
      try { handle.dispose?.(); } catch { /* half-built */ }
      handle.group?.removeFromParent?.();
    }
    return lookFailed("instrument", listed, "create", e);
  }
  L.id = id;
  L.loading = null;
  syncLooksUi();
  return true;
}
function resizeLooks() {  // applyFraming (framing and render quality)
  const f = lookFraming(), s = looks.scheme.active, i = looks.instrument.active;
  if (s) { try { s.instance.resize(f); } catch (e) { lookFailed("scheme", s, "resize", e); } }
  if (i && typeof i.handle.resize === "function") { try { i.handle.resize(f); } catch (e) { lookFailed("instrument", i, "resize", e); } }
}
// Spectacle's "Atmosphere" chord view draws the notes itself (the rule above). Spectacle hands out no handles, so its note
// layers are found by what they are: in its group, the second unnamed group (note glass), meshes with a veil layer or a note
// attribute, point clouds with per-mote uv or per-pitch colour, and the halo loop; in Moonwater, the strands, leaders, labels
// and heading (render orders 3, 14, 15, 30) and the lake's letters and connections.
let atmosphereRoot = null;
function hideAtmosphereNotes() {
  if (!atmosphereRoot || atmosphereRoot.parent !== scene) atmosphereRoot = scene.getObjectByName("Piano atmosphere") || null;
  if (!atmosphereRoot) return 0;
  let hidden = 0, groups = 0;
  for (const o of atmosphereRoot.children) {
    if (o.isGroup && !o.name) {  // the world, then the note glass
      if (groups++ === 1 && o.visible) { o.visible = false; hidden++; }
      continue;
    }
    if (o.name === "Moonwater") {
      for (const c of o.children) {
        const ro = c.renderOrder;
        if ((ro === 3 || ro === 14 || ro === 15 || ro === 30) && c.visible) { c.visible = false; hidden++; }
        const u = c.name === "Lake reflection" && c.material ? c.material.uniforms : null;
        if (u && u.uLetters && (u.uLetters.value || u.uConnections.value)) { u.uLetters.value = 0; u.uConnections.value = 0; hidden++; }
      }
      continue;
    }
    const g = o.geometry, a = g && g.attributes, u = o.material && o.material.uniforms;
    const note = (o.isMesh && ((u && u.uLayer) || (a && a.aNote))) || (o.isPoints && a && (a.aUv || a.color)) || o.isLineLoop;
    if (note && o.visible) { o.visible = false; hidden++; }
  }
  return hidden;
}
// state.sounding, refreshed in place: one pooled entry per key while the page holds that key's sound, dropped when it ends.
// It reads the notes engine's own map, so held / pedal / tRelease are the page's answer, not a guess (pedal = !held is exact:
// an entry with held false exists only while CC64 is down). The keys outside the 88 are the page's to sound and no look's to
// draw, so they never enter the mirror.
function refreshSounding(mirror) {
  const pool = looks.sounds;
  for (const [m, st] of sounding) {
    if (m < KEY.first || m > KEY.last) continue;
    let e = pool.get(m);
    if (!e) { e = { vel: 0, t0: 0, held: false, pedal: false, tRelease: null, strike: 0 }; pool.set(m, e); }
    e.vel = st.vel;
    e.t0 = st.t0;
    e.held = st.held;
    e.pedal = !st.held;
    e.tRelease = st.held ? null : st.tRelease;
    e.strike = st.strike;
    if (mirror.get(m) !== e) mirror.set(m, e);
  }
  for (const m of mirror.keys()) if (!sounding.has(m)) mirror.delete(m);  // the sounds that ended since the last frame
}
const schemeOwnsNotes = () => !!looks.scheme.active && !!spectacle && spectacle.settings.enabled && spectacle.settings.harmonyMode === "atmosphere";
function lookChord(info) {  // the instrument's state.chord: { name, nns, key } while a chord reads, else null
  if (!info || info.kind !== "chord" || !info.name) return null;
  const C = looks.chord;
  C.name = info.name;
  if (C.from !== lastNns) { C.from = lastNns; C.nns = lastNns ? formatNumber(lastNns).display : ""; }
  if (C.keyFrom !== keyView.name) { C.keyFrom = keyView.name; C.key = keyView.name ? keyText(keyView.name) : ""; }
  return C;
}
// renderFrame, after spectacle's update and before the composer renders
function updateLooks(dt, t, info) {
  const s = looks.scheme.active;
  if (s) {
    const F = looks.frame;
    F.info = info; F.sounding = sounding; F.pedalDown = sustain; F.framing = lookFraming();
    F.view.top = trailUniforms.uTop.value;        // where rising things leave the picture (updateCamera)
    F.view.pointScale = sparkUniforms.uPx.value;  // drawing-buffer pixels per world unit at distance 1
    try { s.instance.update(dt, t, F); } catch (e) { lookFailed("scheme", s, "update", e); }
  }
  looks.hidden = schemeOwnsNotes() ? hideAtmosphereNotes() : 0;
  const i = looks.instrument.active;
  if (i) {
    const S = looks.state;
    S.pedal = sustain;
    S.chord = lookChord(info);
    refreshSounding(S.sounding);
    try { i.handle.update(dt, t, S); } catch (e) { lookFailed("instrument", i, "update", e); }
  }
}
function fillLookSelect(select, list, L) {
  if (!select) return;
  const rows = list.filter((s) => s.listed);
  const signature = rows.map((s) => `${s.id}:${s.name}`).join("|");
  if (select.dataset.list !== signature) {
    select.textContent = "";
    for (const s of rows) select.append(new Option(s.name, s.id));
    select.dataset.list = signature;
  }
  select.value = L.loading || L.id;
  select.dataset.loading = String(!!L.loading);
}
function syncLooksUi() {
  fillLookSelect($("scheme-select"), lookList("scheme"), looks.scheme);
  fillLookSelect($("instrument-select"), lookList("instrument"), looks.instrument);
}
// The bake-off seats still to land are fetched only when the Scheme menu is reached for (or a stored pick names one), so a
// page load never asks for a file that is not there.
let lookProbe = null;
function probeLooks() {
  lookProbe ||= Promise.all(SCHEMES.filter((s) => s.probe).map(async (s) => {
    try {
      const r = await fetch(new URL(`./piano/schemes/${s.id}.js`, import.meta.url), { cache: "no-store" });
      if (!r.ok) return;
      const name = /\bname:\s*["']([^"'\n]{1,60})["']/.exec(await r.text());
      looks.listed.set(s.id, name ? name[1] : s.name);
    } catch { /* not there */ }
  })).then(() => { lookProbe = null; syncLooksUi(); });
  return lookProbe;
}
function startLooks() {  // boot, after spectacle: the stored scheme and instrument
  syncLooksUi();
  const scheme = safeGet(LOOK_KEYS.scheme), instrument = safeGet(LOOK_KEYS.instrument);
  (async () => {
    try {
      if (SCHEMES.some((s) => s.id === scheme && s.probe)) await probeLooks();
      if (scheme && scheme !== LOOK_BUILTIN.scheme) await selectScheme(scheme, false);
      if (instrument && instrument !== LOOK_BUILTIN.instrument) await selectInstrument(instrument, false);
    } catch (e) {
      console.error("[piano] looks did not start:", e);
    } finally {
      looks.ready = true;
    }
  })();
}
function registerScheme(mod) {  // __piano.registerScheme: a scheme module object without a file, for this page load
  const problem = lookModuleProblem(mod);
  if (problem) throw new Error(problem);
  looks.registered.set(mod.id, mod);
  syncLooksUi();
  if (looks.scheme.id === mod.id) selectScheme(mod.id, false);  // re-registering the active one rebuilds it
  return mod.id;
}
function looksHudText(t) {
  const S = looks.scheme, I = looks.instrument;
  let live = "";
  if (S.active && typeof S.active.instance.stats === "function") {
    try { const s = S.active.instance.stats(t); if (s && s.trailsLive !== undefined) live = ` · ${s.trailsLive} live`; } catch { /* optional */ }
  }
  const name = (L, kind) => (L.active ? L.active.name : (lookList(kind).find((s) => s.id === L.id) || {}).name || L.id);
  return `${name(S, "scheme")}${S.loading ? ` (loading ${S.loading})` : ""}${live} · ${name(I, "instrument")}` +
         `${I.loading ? ` (loading ${I.loading})` : ""}${S.errors + I.errors ? ` · ${S.errors + I.errors} errors` : ""}` +
         `${looks.hidden ? " · atmosphere notes hidden" : ""}`;
}
// __piano.looks(): what shows, what loads, errors, the renderer's GPU memory; geometry: the instrument's box against its keys;
// render: one frame drawn with the renderer's counters kept across passes (calls, triangles)
function lookStats(opts = {}) {
  const S = looks.scheme, I = looks.instrument, info = renderer.info;
  const safe = (fn) => { try { return fn(); } catch (e) { return { error: errText(e) }; } };
  let shown = 0;
  for (const k of keys.values()) if (k.pivot.visible) shown++;
  const out = {
    ready: looks.ready,
    scheme: S.id, schemeName: (lookList("scheme").find((s) => s.id === S.id) || {}).name || null, schemeLoading: S.loading,
    schemeErrors: S.errors, schemeLastError: S.lastError,
    instrument: I.id, instrumentName: I.active ? I.active.name : "Page keys", instrumentLoading: I.loading,
    instrumentErrors: I.errors, instrumentLastError: I.lastError,
    schemes: lookList("scheme").map((s) => ({ ...s, active: s.id === S.id })),
    instruments: lookList("instrument").map((s) => ({ ...s, active: s.id === I.id })),
    counts: { ...looks.counts },
    classicTrails: trailUniforms.uAtmosphere.value === 0, sparks: sparkPoints.visible,
    atmosphereNotesHidden: looks.hidden, labelOnCanvas: overlay.label ? overlay.label.mesh.visible : null,
    keysShown: shown, bodyShown: pageBody.every((o) => o.visible), floorY: +floor.position.y.toFixed(3),
    keyStyle: I.hints ? { ...I.hints } : null,
    chordForInstrument: looks.state.chord ? { name: looks.state.chord.name, nns: looks.state.chord.nns, key: looks.state.chord.key } : null,
    memory: { geometries: info.memory.geometries, textures: info.memory.textures }, programs: info.programs ? info.programs.length : null,
    schemeStats: S.active && typeof S.active.instance.stats === "function" ? safe(() => S.active.instance.stats(clock())) : null,
    instrumentStats: I.active ? safe(() => (typeof I.active.handle.stats === "function" ? I.active.handle.stats() : I.active.handle.info ?? null)) : null,
  };
  if (opts.render) {
    info.autoReset = false;
    info.reset();
    try { renderFrame(); } finally { info.autoReset = true; }
    out.render = { calls: info.render.calls, triangles: info.render.triangles };
  }
  if (opts.geometry) {
    const h = I.hints, first = h ? h.first : KEY.first, last = h ? h.last : KEY.last;
    const g = { span: { first, last, left: keyX(first) - 0.5, right: keyX(last) + 0.5 }, keyFront: KEY.back + KEY.whiteL, keyBack: KEY.back,
                box: null, screenPx: null };
    if (I.active) {
      I.active.handle.group.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(I.active.handle.group);
      g.box = { min: box.min.toArray().map((v) => +v.toFixed(3)), max: box.max.toArray().map((v) => +v.toFixed(3)) };
      const lay = I.active.handle.layout;
      if (lay && lay.screen && Number.isFinite(lay.yPlate)) {
        camera.updateMatrixWorld();
        const v = new THREE.Vector3(lay.screen.x, lay.yPlate, lay.screen.z).project(camera);
        g.screenPx = [+((v.x + 1) * 0.5 * framing.w).toFixed(1), +((1 - v.y) * 0.5 * framing.h).toFixed(1)];
      }
    }
    out.geometry = g;
  }
  return out;
}

// ---------------------------------------------------------------- overlay --
// The chord label and the grand staff are Canvas2D layers drawn at output resolution and
// composited after bloom (so they stay crisp), inside the WebGL canvas (so REC records them).
// A layer is redrawn and re-uploaded only when its content changes; fades are uniforms.
const FONT = {
  display: '"Archivo", "Arial Narrow", "Segoe UI", sans-serif',
  music: '"Noto Music", "Segoe UI Symbol", serif',
};
const SMUFL = { gClef: "\uE050", fClef: "\uE062", brace: "\uE000", whole: "\uE0A2",
                flat: "\uE260", natural: "\uE261", sharp: "\uE262", dsharp: "\uE263", dflat: "\uE264" };
const BRAVURA_URL = "https://cdn.jsdelivr.net/npm/@vexflow-fonts/bravura@1.0.2/bravura.woff2";
const fontState = { smufl: false, text: false, error: null };

async function loadFonts() {
  const within = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error("timed out")), ms))]);
  const bravura = new FontFace("Bravura", `url(${BRAVURA_URL}) format("woff2")`);
  document.fonts.add(bravura);
  await Promise.all([
    within(bravura.load(), 9000).then(() => { fontState.smufl = true; })
      .catch((e) => { fontState.error = "Bravura: " + errText(e); console.warn("[piano] staff font fallback:", errText(e)); }),
    within(Promise.all([document.fonts.load('800 120px "Archivo"'), document.fonts.load('600 40px "Archivo"'),
                        document.fonts.load('100px "Noto Music"', "♭♯")]), 9000)
      .then(() => { fontState.text = true; }).catch(() => {}),
  ]);
  overlay.invalidate();
}

// nns: the Nashville number line, under the note chips and above the staff's clefs.
// cue: Claude's chip, clear of all the others (see drawCueChip): 9:16 the top band above the label (y 28-144), 16:9
// under the numbers (x 50-950, y 464-568).
const LAYOUT = {
  "9:16": { label: { cx: 540, cy: 318, w: 1060, h: 340, align: "center", size: 170 },
            nns: { cx: 540, cy: 536, w: 1060, h: 130, align: "center", size: 76 },
            staff: { cx: 540, cy: 800, w: 860, h: 600, s: 24 },
            cue: { cx: 540, cy: 86, w: 980, h: 116, align: "center", size: 46 } },
  "16:9": { label: { cx: 500, cy: 196, w: 900, h: 310, align: "left", size: 140 },
            nns: { cx: 500, cy: 392, w: 900, h: 120, align: "left", size: 64 },
            staff: { cx: 1560, cy: 272, w: 640, h: 520, s: 20 },
            cue: { cx: 500, cy: 516, w: 900, h: 104, align: "left", size: 42 } },
};

const overlayScene = new THREE.Scene();
const overlayCam = new THREE.OrthographicCamera(0, framing.w, framing.h, 0, -10, 10);

function makeLayer(spec) {
  const c = document.createElement("canvas");
  c.width = Math.round(spec.w * renderScale);
  c.height = Math.round(spec.h * renderScale);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(spec.w, spec.h), mat);
  mesh.position.set(spec.cx, framing.h - spec.cy, 0);
  overlayScene.add(mesh);
  // Drawn in software (willReadFrequently): Chrome's GPU-accelerated 2D canvases rasterize text through state the GPU process
  // shares with every other canvas, so Claude's chip or the glass drawing elsewhere moved one pixel of the staff's brace by a
  // level (jam spec A5, receipts 2026-09-14). The software path draws the same pixels every time, and a layer is redrawn
  // and uploaded only when its content changes.
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.scale(renderScale, renderScale);
  return { canvas: c, ctx, tex, mat, mesh, spec };
}
function disposeLayer(layer) {
  if (!layer) return;
  overlayScene.remove(layer.mesh);
  layer.mesh.geometry.dispose();
  layer.mat.dispose();
  layer.tex.dispose();
}

const INK = "rgba(244, 241, 234, 1)";
const accGlyph = (acc) => ({ 1: "♯", 2: "𝄪", [-1]: "♭", [-2]: "𝄫" })[acc] || "";
function nameRuns(letter, acc, size, weight, color, raise = 0) {
  const runs = [{ text: letter, font: `${weight} ${size}px ${FONT.display}`, color, dy: -raise }];
  if (acc) runs.push({ text: accGlyph(acc), font: `${Math.round(size * 0.62)}px ${FONT.music}`, color, dy: -raise - size * 0.3, kern: size * 0.02 });
  return runs;
}
function suffixRuns(suffix, size, color) {
  const runs = [];
  for (const part of suffix.split(/([b#])/).filter(Boolean)) {
    if (part === "b" || part === "#") {
      runs.push({ text: part === "b" ? "♭" : "♯", font: `${Math.round(size * 0.5)}px ${FONT.music}`, color, dy: -size * 0.34 });
    } else {
      runs.push({ text: part, font: `600 ${Math.round(size * 0.54)}px ${FONT.display}`, color, dy: -size * 0.3 });
    }
  }
  return runs;
}
// A run may carry its own letter spacing (r.spacing); the others keep the caller's.
function drawRuns(ctx, runs, x, baseline, glow) {
  const spacing = ctx.letterSpacing;
  let cursor = x;
  for (const r of runs) {
    ctx.font = r.font;
    ctx.letterSpacing = r.spacing || spacing;
    r.x = cursor;
    r.w = ctx.measureText(r.text).width;
    cursor += r.w + (r.kern || 0);
  }
  const width = cursor - x;
  for (const pass of glow ? [0, 1] : [1]) {
    for (const r of runs) {
      ctx.font = r.font;
      ctx.letterSpacing = r.spacing || spacing;
      ctx.fillStyle = r.color;
      ctx.shadowColor = pass === 0 ? glow : "transparent";
      ctx.shadowBlur = pass === 0 ? 38 : 0;
      ctx.fillText(r.text, r.x, baseline + (r.dy || 0));
    }
  }
  ctx.shadowBlur = 0;
  ctx.letterSpacing = spacing;
  return width;
}
function measureRuns(ctx, runs) {
  const spacing = ctx.letterSpacing;
  let w = 0;
  for (const r of runs) {
    ctx.font = r.font;
    ctx.letterSpacing = r.spacing || spacing;
    w += ctx.measureText(r.text).width + (r.kern || 0);
  }
  ctx.letterSpacing = spacing;
  return w;
}

// A Nashville degree ("b3", "#4", "5"): the accidental before the numeral, raised, as charts write it.
function degreeRuns(text, size, weight, color) {
  const m = /^(b{1,2}|#{1,2})?(\d+)$/.exec(text || "");
  if (!m) return [{ text: String(text), font: `${weight} ${size}px ${FONT.display}`, color }];
  const runs = [];
  if (m[1]) {
    const acc = m[1][0] === "#" ? m[1].length : -m[1].length;
    runs.push({ text: accGlyph(acc), font: `${Math.round(size * 0.6)}px ${FONT.music}`, color, dy: -size * 0.32, kern: size * 0.02 });
  }
  runs.push({ text: m[2], font: `${weight} ${size}px ${FONT.display}`, color });
  return runs;
}
// A nashville() result drawn like a chord name, by the shared formatter (nashville.js formatNumber, which the other views
// use too): the numeral, the quality and extensions raised ("maj7", "°7", "m", "6/9": a 4 with 6/9 raised, never "46/9"),
// then "/" and the bass degree a size smaller.
function numberRuns(n, size, color) {
  const slash = (s) => ({ text: s, font: `300 ${Math.round(size * 0.78)}px ${FONT.display}`, color, dy: 0, kern: size * 0.02 });
  const f = formatNumber(n);
  const runs = [];
  for (const p of f ? f.parts : []) {
    if (p.role === "degree") runs.push(...degreeRuns(p.text, size, 800, color));
    else if (p.role === "sup") runs.push(...suffixRuns(p.text, size, color));
    else if (p.role === "dash") runs.push({ text: " – ", font: `300 ${size}px ${FONT.display}`, color });
    else if (p.role === "slash") runs.push(slash("/"));
    else if (p.role === "bass") runs.push(...degreeRuns(p.text, Math.round(size * 0.78), 700, color));
    else runs.push({ text: p.text, font: `800 ${size}px ${FONT.display}`, color });
  }
  return runs;
}
// "Bb major" as small capitals with a real flat: B♭ MAJOR.
function keyCaptionRuns(prefix, keyName, size, color) {
  const m = /^([A-G])(bb?|##?)?\s+(major|minor)$/.exec(keyName || "");
  const font = `600 ${size}px ${FONT.display}`, spacing = `${Math.round(size * 0.12)}px`;
  if (!m) return [{ text: `${prefix}${keyName || ""}`.toUpperCase(), font, color, spacing }];
  const runs = [{ text: `${prefix}${m[1]}`.toUpperCase(), font, color, spacing }];
  if (m[2]) runs.push({ text: accGlyph(m[2][0] === "#" ? m[2].length : -m[2].length), font: `${Math.round(size * 1.05)}px ${FONT.music}`, color, dy: -size * 0.2 });
  runs.push({ text: ` ${m[3]}`.toUpperCase(), font, color, spacing });
  return runs;
}

function drawLabel(layer, info) {
  const { ctx, spec } = layer;
  ctx.clearRect(0, 0, spec.w, spec.h);
  if (!info) return;
  ctx.fontStretch = "semi-condensed";
  ctx.textBaseline = "alphabetic";
  const S = spec.size;
  const first = info.notes[0];
  const glow = noteCss(first.midi, 100, 0.55);
  // "Numbers only": the Nashville number takes the name's place (a cluster, or no key yet, keeps the name)
  const number = theoryUi.nns === "numbers" ? numberFor(info) : null;
  let runs;
  if (number) {
    runs = numberRuns(number, S, keyView.dim ? INK_UNSURE : INK);
  } else if (info.kind === "chord") {
    runs = [...nameRuns(Theory.LETTERS[info.root.letter], info.root.acc, S, 800, INK), ...suffixRuns(info.suffix, S, INK)];
    if (info.bass) {
      runs.push({ text: "/", font: `300 ${Math.round(S * 0.78)}px ${FONT.display}`, color: "rgba(244,241,234,0.62)", dy: 0, kern: S * 0.02 });
      runs.push(...nameRuns(Theory.LETTERS[info.bass.letter], info.bass.acc, Math.round(S * 0.78), 700, INK));
    }
  } else if (info.kind === "interval") {
    runs = [...nameRuns(Theory.LETTERS[info.root.letter], info.root.acc, S, 800, INK),
            { text: " – ", font: `300 ${S}px ${FONT.display}`, color: "rgba(244,241,234,0.5)" },
            ...nameRuns(Theory.LETTERS[info.upper.letter], info.upper.acc, S, 800, INK)];
  } else if (info.kind === "note") {
    runs = nameRuns(Theory.LETTERS[info.root.letter], info.root.acc, S, 800, INK);
    if (info.octave !== null) runs.push({ text: String(info.octave), font: `500 ${Math.round(S * 0.42)}px ${FONT.display}`, color: "rgba(244,241,234,0.6)", dy: 0, kern: 0 });
  } else {
    runs = [{ text: info.pcNames.join(" ").replace(/b/g, "♭").replace(/#/g, "♯"), font: `700 ${Math.round(S * 0.5)}px ${FONT.display}`, color: INK }];
  }
  const mainW = measureRuns(ctx, runs);
  const baseline = spec.h * 0.56;
  const x0 = spec.align === "center" ? (spec.w - mainW) / 2 : 24;
  drawRuns(ctx, runs, x0, baseline, glow);

  // second line: the pitch classes in voicing order, each in its trail colour, plus a caption
  const small = Math.round(S * 0.24);
  const line = [];
  const seen = new Set();
  for (const n of info.notes) {
    if (seen.has(n.name)) continue;
    seen.add(n.name);
    if (line.length) line.push({ text: " ", font: `500 ${small}px ${FONT.display}`, color: INK });
    line.push(...nameRuns(Theory.LETTERS[n.letter], n.acc, small, 700, noteCss(n.midi, 110, 1)));
  }
  const caption = info.sub;
  if (caption) {
    line.push({ text: " " + caption.toUpperCase(), font: `600 ${Math.round(small * 0.72)}px ${FONT.display}`, color: "rgba(244,241,234,0.55)" });
  }
  ctx.letterSpacing = `${Math.round(small * 0.06)}px`;
  const lineW = measureRuns(ctx, line);
  drawRuns(ctx, line, spec.align === "center" ? (spec.w - lineW) / 2 : 30, baseline + S * 0.52, "rgba(0, 0, 0, 0.75)");
  ctx.letterSpacing = "0px";
}

// The Nashville line under the chips: "With chord" draws the number and "in F major"; "Numbers only" draws just the
// caption (the number is the label). A chord outside the key reads "outside F major": a fact, not a verdict.
// While the tracker is unsure of the key the whole line reads dimmer.
const INK_UNSURE = "rgba(244, 241, 234, 0.5)";
let nnsDrawn = null;  // the runs the Nashville row last drew: [{ text, raised }] (window.__piano.theory.nns())
const drawnRuns = (runs) => runs.map((r) => ({ text: r.text, raised: (r.dy || 0) < 0 }));
function drawNumbers(layer, info) {
  const { ctx, spec } = layer;
  ctx.clearRect(0, 0, spec.w, spec.h);
  nnsDrawn = null;
  if (!info || theoryUi.nns === "off") return;
  ctx.fontStretch = "semi-condensed";
  ctx.textBaseline = "alphabetic";
  ctx.letterSpacing = "0px";
  const S = spec.size;
  if (!keyView.key) {  // the tracker hears a few bars before it names a key; say so, faintly, where the number will be
    const wait = keyCaptionRuns("listening for the key", "", Math.round(S * 0.34), "rgba(244, 241, 234, 0.34)");
    drawRuns(ctx, wait, spec.align === "center" ? (spec.w - measureRuns(ctx, wait)) / 2 : 30, spec.h * 0.62, "rgba(0, 0, 0, 0.8)");
    nnsDrawn = drawnRuns(wait);
    return;
  }
  const number = numberFor(info);
  const ink = keyView.dim ? INK_UNSURE : "rgba(244, 241, 234, 0.94)";
  const runs = theoryUi.nns === "chord" && number ? numberRuns(number, S, ink) : [];
  const words = (runs.length ? "   " : "") + (number && !number.diatonic ? "outside " : "in ");
  runs.push(...keyCaptionRuns(words, keyView.key.name, Math.round(S * 0.34), keyView.dim ? "rgba(244, 241, 234, 0.34)" : "rgba(244, 241, 234, 0.58)"));
  nnsDrawn = drawnRuns(runs);
  const width = measureRuns(ctx, runs);
  drawRuns(ctx, runs, spec.align === "center" ? (spec.w - width) / 2 : 30, spec.h * 0.62, "rgba(0, 0, 0, 0.8)");
}

let staffDrawn = null;  // what drawStaff last drew: the signature and each note's accidental (window.__piano.theory.staff())
// sig: the key signature model's view (piano/keysig.js), or null for none.
function drawStaff(layer, info, sig = null) {
  const { ctx, spec } = layer;
  const { w, h, s } = spec;
  ctx.clearRect(0, 0, w, h);
  // an elliptical scrim that reaches zero inside the layer, so no rectangle edge can show
  ctx.save();
  ctx.translate(w / 2, h / 2);
  ctx.scale(1, h / w);
  const scrim = ctx.createRadialGradient(0, 0, 0, 0, 0, w / 2);
  scrim.addColorStop(0, "rgba(1, 2, 6, 0.62)");
  scrim.addColorStop(0.6, "rgba(1, 2, 6, 0.42)");
  scrim.addColorStop(1, "rgba(1, 2, 6, 0)");
  ctx.fillStyle = scrim;
  ctx.fillRect(-w / 2, -w / 2, w, w);
  ctx.restore();

  const left = s * 3.2, right = w - s * 1.6;
  const trebleTop = h / 2 - s * 7.5, trebleBottom = trebleTop + 4 * s;
  const bassTop = trebleBottom + 7 * s, bassBottom = bassTop + 4 * s;
  const LINE = "rgba(236, 232, 224, 0.52)";
  ctx.strokeStyle = LINE;
  ctx.lineWidth = Math.max(1, s * 0.1);
  ctx.beginPath();
  for (const top of [trebleTop, bassTop]) {
    for (let i = 0; i < 5; i++) { ctx.moveTo(left, top + i * s); ctx.lineTo(right, top + i * s); }
  }
  ctx.stroke();
  ctx.lineWidth = Math.max(1.5, s * 0.16);
  ctx.beginPath();
  ctx.moveTo(left, trebleTop); ctx.lineTo(left, bassBottom);
  ctx.moveTo(right, trebleTop); ctx.lineTo(right, bassBottom);
  ctx.stroke();

  const CLEF = "rgba(244, 241, 234, 0.9)";
  ctx.fillStyle = CLEF;
  ctx.textBaseline = "alphabetic";
  if (fontState.smufl) {
    ctx.font = `${4 * s}px Bravura`;
    ctx.fillText(SMUFL.gClef, left + s * 0.7, trebleTop + 3 * s);
    ctx.fillText(SMUFL.fClef, left + s * 0.7, bassTop + s);
    ctx.save();
    const braceH = bassBottom - trebleTop;
    ctx.translate(left - s * 1.3, bassBottom);
    ctx.scale(0.55, 1);
    ctx.font = `${braceH}px Bravura`;
    ctx.fillText(SMUFL.brace, 0, 0);
    ctx.restore();
  } else {
    ctx.font = `${4.4 * s}px ${FONT.music}`;
    ctx.fillText("𝄞", left + s * 0.5, trebleTop + 3.1 * s);
    ctx.font = `${3.6 * s}px ${FONT.music}`;
    ctx.fillText("𝄢", left + s * 0.5, bassTop + 2.1 * s);
  }
  // The key signature (live sheet music LS6): the key the numbers use, once it settles (piano/keysig.js). For 2 s after a
  // change, a double bar after the clefs, then the new signature, and a small "→ key" tag under the staff.
  const signature = sig ? sig.signature : null;
  const showing = !!(sig && sig.showing && sig.change);
  if (showing) {
    ctx.strokeStyle = LINE;
    ctx.lineWidth = Math.max(1.5, s * 0.14);
    ctx.beginPath();
    for (const x of [left + s * 3.75, left + s * 4.15]) { ctx.moveTo(x, trebleTop); ctx.lineTo(x, bassBottom); }
    ctx.stroke();
  }
  if (signature && signature.count) {
    const sigX = left + s * (showing ? 4.75 : 3.9);
    ctx.fillStyle = CLEF;
    for (const [clef, yOf] of [["treble", (d) => trebleBottom - (d - 30) * s / 2], ["bass", (d) => bassBottom - (d - 18) * s / 2]]) {
      signaturePlaces(signature, clef).forEach((p, i) => {
        const x = sigX + i * s * (p.acc > 0 ? 1.2 : 1.0);  // a sharp is wider than a flat: neighbours never touch
        if (fontState.smufl) {
          ctx.font = `${4 * s}px Bravura`;
          ctx.fillText(p.acc > 0 ? SMUFL.sharp : SMUFL.flat, x, yOf(p.diatonic));
        } else {
          ctx.font = `${2.2 * s}px ${FONT.music}`;
          ctx.fillText(accGlyph(p.acc), x, yOf(p.diatonic) + s * 0.55);
        }
      });
    }
  }
  if (showing) {
    const tag = keyCaptionRuns("→ ", sig.change.to, Math.round(s * 0.8), "rgba(244, 241, 234, 0.78)");
    drawRuns(ctx, tag, left + s * 3.75, bassBottom + s * 2.6, "rgba(0, 0, 0, 0.8)");
  }
  staffDrawn = { key: sig ? sig.key : null, type: signature ? signature.type : "none", count: signature ? signature.count : 0,
                 doubleBar: showing, tag: showing ? sig.change.to : null, notes: [] };
  if (!info) return;

  const noteX = left + (right - left) * 0.6;
  const headW = s * 1.69;
  const staves = [
    { notes: info.notes.filter((n) => n.midi >= 60), yOf: (d) => trebleBottom - (d - 30) * s / 2, lo: 30, hi: 38 },
    { notes: info.notes.filter((n) => n.midi < 60), yOf: (d) => bassBottom - (d - 18) * s / 2, lo: 18, hi: 26 },
  ];
  for (const staff of staves) {
    const notes = [...staff.notes].sort((a, b) => a.diatonic - b.diatonic || a.acc - b.acc);
    if (!notes.length) continue;
    notes.forEach((n, i) => {
      n.col = i > 0 && notes[i - 1].diatonic >= n.diatonic - 1 && notes[i - 1].col === 0 ? 1 : 0;
    });
    // ledger lines, as wide as the note columns that need them
    ctx.strokeStyle = "rgba(236, 232, 224, 0.78)";
    ctx.lineWidth = Math.max(1.5, s * 0.15);
    ctx.beginPath();
    const ledger = (d, beyond) => {
      const users = notes.filter(beyond);
      if (!users.length) return;
      const x0 = noteX - s * 0.45 + Math.min(...users.map((n) => n.col)) * headW;
      const x1 = noteX + headW + s * 0.45 + Math.max(...users.map((n) => n.col)) * headW;
      ctx.moveTo(x0, staff.yOf(d)); ctx.lineTo(x1, staff.yOf(d));
    };
    const maxD = notes[notes.length - 1].diatonic, minD = notes[0].diatonic;
    for (let d = staff.hi + 2; d <= maxD; d += 2) ledger(d, (n) => n.diatonic >= d);
    for (let d = staff.lo - 2; d >= minD; d -= 2) ledger(d, (n) => n.diatonic <= d);
    ctx.stroke();

    // accidentals against the key signature (a note the signature already gives needs none, a natural cancels the
    // signature), stacked into columns from the top so they never collide
    for (const n of notes) n.shown = staffAccidental(n, signature);
    staffDrawn.notes.push(...notes.map((n) => ({ name: n.name + n.octave, midi: n.midi, shown: n.shown })));
    const accCols = [];
    const withAcc = notes.filter((n) => n.shown !== null).sort((a, b) => b.diatonic - a.diatonic);
    for (const n of withAcc) {
      let c = 0;
      while (accCols[c] && accCols[c].some((d) => Math.abs(d - n.diatonic) < 6)) c++;
      (accCols[c] = accCols[c] || []).push(n.diatonic);
      n.accCol = c;
    }
    for (const n of notes) {
      const y = staff.yOf(n.diatonic);
      const x = noteX + n.col * headW;
      const color = noteCss(n.midi, 110, 1);
      ctx.fillStyle = color;
      for (const pass of [0, 1]) {
        ctx.shadowColor = pass === 0 ? noteCss(n.midi, 110, 0.9) : "transparent";
        ctx.shadowBlur = pass === 0 ? s * 0.9 : 0;
        if (fontState.smufl) {
          ctx.font = `${4 * s}px Bravura`;
          ctx.fillText(SMUFL.whole, x, y);
          if (n.shown !== null) {
            const glyph = { 0: SMUFL.natural, 1: SMUFL.sharp, 2: SMUFL.dsharp, [-1]: SMUFL.flat, [-2]: SMUFL.dflat }[n.shown];
            ctx.fillText(glyph, noteX - s * 0.35 - (n.accCol + 1) * s * 1.3, y);
          }
        } else {
          ctx.beginPath();
          ctx.ellipse(x + headW / 2, y, headW / 2, s * 0.52, -0.35, 0, Math.PI * 2);
          ctx.ellipse(x + headW / 2, y, headW * 0.22, s * 0.3, 0.9, 0, Math.PI * 2);
          ctx.fill("evenodd");
          if (n.shown !== null) {
            ctx.font = `${2.2 * s}px ${FONT.music}`;
            ctx.fillText(n.shown === 0 ? "♮" : accGlyph(n.shown), noteX - s * 0.2 - (n.accCol + 1) * s * 1.3, y + s * 0.55);
          }
        }
      }
      ctx.shadowBlur = 0;
    }
  }
}

// "CLAUDE · Abmaj9#11" over "4maj9#11 in Eb major · the Lydian 4": what Claude is playing or showing, in Claude's own
// words, never the page's reading of the cue notes (the two can differ, and the big label, the chips, the numbers and
// the staff are Daniel's alone). A replay of Daniel's own playing leads with YOU and puts the step playing now on a line
// under its caption. The boxes (LAYOUT.cue) keep clear of the label, note chips, Nashville row and staff: in 9:16 the
// top band, whose ink the label only reaches near y 215; in 16:9 under the numbers, left of the staff. The hairline
// says what it is: moonlight for a play (the colour of Claude's keys), dashed silver for a hover, amber for a replay.
const CHIP = { scrim: "rgba(6, 8, 12, 0.58)", lead: "rgba(200, 220, 255, 0.92)", leadYou: "rgba(242, 181, 74, 0.92)",
               detail: "rgba(244, 241, 234, 0.74)", under: "rgba(242, 181, 74, 0.95)", play: "rgba(200, 220, 255, 0.72)",
               hover: "rgba(211, 219, 232, 0.6)", replay: "rgba(242, 181, 74, 0.7)" };
const CUE_NOTE = /^([A-G])(##|#|bb|b|♯|♭)?(-?\d{1,2})?$/;
const CUE_ACC = { "#": 1, "##": 2, "♯": 1, b: -1, bb: -2, "♭": -1 };
function cueLabelRuns(label, S) {
  const c = label ? parseChord(label) : null;
  const known = (sp) => sp && sp.letter >= 0;
  if (c && c.kind === "chord" && known(c.root)) {  // set like the big label: real flats and sharps, a raised suffix
    const runs = [...nameRuns(Theory.LETTERS[c.root.letter], c.root.acc, S, 800, INK), ...suffixRuns(c.suffix, S, INK)];
    if (known(c.bass)) {
      runs.push({ text: "/", font: `300 ${Math.round(S * 0.78)}px ${FONT.display}`, color: "rgba(244,241,234,0.62)", kern: S * 0.02 },
                ...nameRuns(Theory.LETTERS[c.bass.letter], c.bass.acc, Math.round(S * 0.78), 700, INK));
    }
    return runs;
  }
  if (c && c.kind === "interval" && known(c.root) && known(c.upper)) {
    return [...nameRuns(Theory.LETTERS[c.root.letter], c.root.acc, S, 800, INK),
            { text: " – ", font: `300 ${S}px ${FONT.display}`, color: "rgba(244,241,234,0.5)" },
            ...nameRuns(Theory.LETTERS[c.upper.letter], c.upper.acc, S, 800, INK)];
  }
  // A list of notes ("Db4 F#4", "E4 G#4 B4"): each name with a real flat or sharp, its octave smaller
  const names = label ? label.trim().split(/\s+/) : [];
  if (names.length && names.length <= 40 && names.every((n) => CUE_NOTE.test(n))) {
    const runs = [];
    for (let i = 0; i < names.length; i++) {
      const [, letter, acc, octave] = names[i].match(CUE_NOTE);
      if (i) runs.push({ text: " ", font: `700 ${S}px ${FONT.display}`, color: INK });
      runs.push(...nameRuns(letter, CUE_ACC[acc || ""] || 0, S, 800, INK));
      if (octave) runs.push({ text: octave, font: `600 ${Math.round(S * 0.6)}px ${FONT.display}`, color: "rgba(244,241,234,0.72)", kern: S * 0.02 });
    }
    return runs;
  }
  return [{ text: label || "", font: `700 ${S}px ${FONT.display}`, color: INK }];  // "you, at 5:22", anything else
}
function fitRun(ctx, run, maxW) {  // one run trimmed with an ellipsis to maxW (only when the chip is redrawn)
  if (measureRuns(ctx, [run]) <= maxW) return run;
  let text = run.text;
  while (text.length > 1 && measureRuns(ctx, [{ ...run, text: `${text}…` }]) > maxW) text = text.slice(0, -1);
  return { ...run, text: `${text.trimEnd()}…` };
}
// The chip's small lines are Claude's own text ("5^7sus4/1 in Eb major", "Cm9/Ab · 4maj9#11 in Eb major"). The numbers,
// chord names and note names in it are set as the label and the Nashville row set them: real flats and sharps, and a
// number's suffix raised with no "^" joiner (5^7sus4/1 reads 5 with 7sus4 raised, then /1). The rest is set as typed. A
// word counts as a chord only if its suffix is chord vocabulary, so "Claude" or "Bass" stay words.
const CUE_DEGREE = /^((?:bb?|##?)?[1-7])(\^\d[^\s/]*|[A-Za-z#°ø+(-][^\s/]*)?(?:\/((?:bb?|##?)?[1-7]))?$/;
const CUE_SUFFIX = /^(?:maj|min|dim|aug|sus|add|alt|no|m|M|°|ø|\+|-|\d|b|#|\(|\))*$/;
function cueTextRuns(text, size, weight, color) {
  const plain = (t) => ({ text: t, font: `${weight} ${size}px ${FONT.display}`, color });
  const raised = (suffix) => suffixRuns(suffix, Math.round(size * 1.3), color);  // the row's superscript, at this line's size
  const slash = () => ({ text: "/", font: `300 ${size}px ${FONT.display}`, color, kern: size * 0.02 });
  const runs = [];
  for (const part of String(text || "").split(/(\s+)/)) {
    if (!part) continue;
    const [, lead, core, trail] = /^(\(*)(.*?)([,;:.)]*)$/.exec(part);
    let set = null;
    const n = CUE_DEGREE.exec(core);
    if (n && (!n[2] || CUE_SUFFIX.test(n[2].replace(/^\^/, "")))) {
      set = degreeRuns(n[1], size, weight, color);
      if (n[2]) set.push(...raised(n[2].replace(/^\^/, "")));
      if (n[3]) set.push(slash(), ...degreeRuns(n[3], size, weight, color));
    } else if (/^[A-G]/.test(core)) {
      const c = parseChord(core);
      if (c && c.kind === "chord" && c.root.letter >= 0 && CUE_SUFFIX.test(c.suffix) && (c.bass || !core.includes("/"))) {
        set = nameRuns(Theory.LETTERS[c.root.letter], c.root.acc, size, weight, color);
        if (c.suffix) set.push(...raised(c.suffix));
        if (c.bass) set.push(slash(), ...nameRuns(Theory.LETTERS[c.bass.letter], c.bass.acc, size, weight, color));
      }
    }
    if (!set) { runs.push(plain(part)); continue; }
    if (lead) runs.push(plain(lead));
    runs.push(...set);
    if (trail) runs.push(plain(trail));
  }
  return runs;
}
function fitTextRuns(ctx, text, size, weight, color, maxW) {  // set as above, or (too wide) plain text with an ellipsis
  const runs = cueTextRuns(text, size, weight, color);
  return measureRuns(ctx, runs) <= maxW ? runs : [fitRun(ctx, { text, font: `${weight} ${size}px ${FONT.display}`, color }, maxW)];
}
// The chip's first word: YOU for a replay of Daniel's own playing; EXERCISE for the Studio's practice player, whose chords
// are local cues with ids starting "exercise:" (practice/player.js ID_PREFIX; the caption carries the id, cues.js meta);
// CLAUDE for everything else. Stream cues carry the server's integer ids, so none of them can read EXERCISE.
const EXERCISE_CUE_PREFIX = "exercise:";
function cueChipLead(info) {
  if (!info) return null;
  if (info.source === "replay") return "YOU";
  return typeof info.cue_id === "string" && info.cue_id.startsWith(EXERCISE_CUE_PREFIX) ? "EXERCISE" : "CLAUDE";
}
function drawCueChip(layer, info) {
  const { ctx, spec } = layer;
  ctx.clearRect(0, 0, spec.w, spec.h);
  if (!info) return;
  ctx.fontStretch = "semi-condensed";
  ctx.textBaseline = "alphabetic";
  ctx.letterSpacing = "0px";
  const replay = info.source === "replay";
  const u = info.under;
  const underText = u && (u.label || u.detail) ? [u.label, u.detail].filter(Boolean).join("  ·  ") : "";
  const S = Math.round(spec.size * (underText ? 0.78 : 1)), pad = Math.round(spec.size * 0.45);
  const small = Math.round(spec.size * (underText ? 0.34 : 0.4));
  const maxText = spec.w - 4 - pad * 2;
  const lead = [{ text: `${cueChipLead(info)}  ·  `, font: `700 ${Math.round(S * 0.42)}px ${FONT.display}`,
                  color: replay ? CHIP.leadYou : CHIP.lead, spacing: `${Math.round(S * 0.06)}px`, dy: -S * 0.1 }];
  const leadW = measureRuns(ctx, lead), room = maxText - leadW;
  let main = info.label ? cueLabelRuns(info.label, S) : fitTextRuns(ctx, info.detail || "", Math.round(S * 0.62), 600, INK, room);
  const detail = info.label && info.detail ? fitTextRuns(ctx, info.detail, small, 500, CHIP.detail, maxText) : null;
  const under = underText ? fitTextRuns(ctx, underText, small, 600, CHIP.under, maxText) : null;
  // A main line wider than the chip: a chord or a list of note names is set smaller (not below 60%), and anything still
  // too wide becomes plain text ending in an ellipsis, never cut mid-letter at the layer's edge.
  const mainW = measureRuns(ctx, main);
  if (info.label && mainW > room && main.length > 1) {
    const smaller = Math.floor(S * Math.max(0.6, room / mainW));
    main = cueLabelRuns(info.label, smaller);
    if (measureRuns(ctx, main) > room) main = [{ text: info.label, font: `700 ${smaller}px ${FONT.display}`, color: INK }];
  }
  if (main.length === 1 && measureRuns(ctx, main) > room) main = [fitRun(ctx, main[0], room)];
  const top = leadW + measureRuns(ctx, main);
  const w = Math.min(spec.w - 4, Math.max(top, detail ? measureRuns(ctx, detail) : 0, under ? measureRuns(ctx, under) : 0) + pad * 2);
  // the scrim covers only what the lines need (a label alone gets a shorter chip), so less of Daniel's trails is hidden
  const lineCount = (detail ? 1 : 0) + (under ? 1 : 0);
  const h = Math.round((spec.h - 4) * (lineCount ? 1 : 0.74)), x = spec.align === "center" ? (spec.w - w) / 2 : 2;
  ctx.beginPath();
  ctx.roundRect(x, 2, w, h, spec.size * 0.3);
  ctx.fillStyle = CHIP.scrim;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.setLineDash(info.kind === "hover" && !replay ? [10, 7] : []);
  ctx.strokeStyle = replay ? CHIP.replay : info.kind === "hover" ? CHIP.hover : CHIP.play;
  ctx.stroke();
  ctx.setLineDash([]);
  const lines = lineCount;
  const base = 2 + h * (lines === 2 ? 0.42 : lines === 1 ? 0.54 : 0.7);
  const x0 = x + pad;
  drawRuns(ctx, main, x0 + drawRuns(ctx, lead, x0, base, null), base, null);
  if (detail) drawRuns(ctx, detail, x0, 2 + h * (lines === 2 ? 0.69 : 0.86), null);
  if (under) drawRuns(ctx, under, x0, 2 + h * (lines === 2 ? 0.92 : 0.86), null);
}

const overlay = {
  label: null, staff: null, nns: null, cue: null,
  shown: null, pending: null, pendingSince: 0, staffKey: "", labelKey: "", nnsKey: "",
  labelAlpha: 0, staffAlpha: 0, pop: 0, silentSince: 0, needsRedraw: true,
  cueShown: null, cueDrawn: undefined, cueFont: null, cueAlpha: 0,
  // The label's settle on Daniel's own reading (ownInfo), run beside the shown one: the two are the same until the jam key
  // (8.10) reads his chords. On the frame the jam key leaves (REC in auto arms on it) the shown label takes this state, so a
  // take's label, number and staff are a no-band page's from its first frame, pop and fade included (A5).
  // jamRead: the jam key was shown on the last update.
  own: { shown: null, pending: null, pendingSince: 0, pendingGrew: undefined, lastOnCount: undefined, labelAlpha: 0, pop: 0 },
  jamRead: false,
  build() {
    disposeLayer(this.label);
    disposeLayer(this.staff);
    disposeLayer(this.nns);
    disposeLayer(this.cue);
    const L = LAYOUT[framing.id];
    this.label = makeLayer(L.label);
    this.staff = makeLayer(L.staff);
    this.nns = makeLayer(L.nns);  // added after the staff, so it draws over the staff's scrim
    this.cue = makeLayer(L.cue);  // Claude's chip, last: over everything (it overlaps nothing in either framing)
    overlayCam.right = framing.w;
    overlayCam.top = framing.h;
    overlayCam.updateProjectionMatrix();
    this.invalidate();
  },
  invalidate() { this.labelKey = ""; this.staffKey = ""; this.nnsKey = ""; this.cueDrawn = undefined; this.needsRedraw = true; },
  // The label's settle (see update), on a state: this, the label shown, or this.own, Daniel's own beside it
  settle(st, info, t) {
    if (info) {
      const grew = info.onCount !== st.lastOnCount;
      st.lastOnCount = info.onCount;
      if (!st.pending || st.pending.name !== info.name) { st.pending = info; st.pendingSince = t; st.pendingGrew = grew; }
      else st.pending = info;
      if (st.shown && st.shown.name === info.name) {
        st.shown = info;  // same name, new voicing: follow at once
      } else if (t - st.pendingSince >= (st.pendingGrew ? 0.12 : 0.3)) {
        if (st.shown) st.pop = 1;
        st.shown = st.pending;
      }
    } else if (st.pending && st.pendingGrew && (!st.shown || st.shown.name !== st.pending.name)) {
      st.shown = st.pending;
      st.pop = 1;
    }
  },
  // info: the detection for what is sounding right now, or null for silence; own: Daniel's own reading of it (ownInfo)
  update(info, t, dt, own = info) {
    const sounding = !!info;
    if (sounding) this.silentSince = 0;
    else if (!this.silentSince) this.silentSince = t;
    if (this.jamRead && !keyView.jam) Object.assign(this, this.own);  // the jam key left: the label is Daniel's own from this frame
    this.jamRead = !!keyView.jam;

    // The staff follows every change at once. The label waits for the set to settle: 120 ms after a
    // note-on (a rolled chord does not flash its partial names), 300 ms after a release (letting go
    // of a chord note by note keeps its name), and a quick note released before settling still gets named.
    const staffInfo = info || this.shown;
    const sig = keySig.view(t);  // the settled key signature (LS6); its id changes only when the drawing does
    const staffKey = (staffInfo ? staffInfo.notes.map((n) => n.midi + n.name).join(",") + COLOUR.mode + fontState.smufl : "none" + fontState.smufl)
                     + "|" + sig.id + "|" + theoryUi.minor;
    if (staffKey !== this.staffKey || this.needsRedraw) {
      // the notes are spelled in the signature's key: the shown key's spelling when the two agree, else the one speller's
      drawStaff(this.staff, sig.key && staffInfo ? spellForKey(staffInfo, { name: sig.key }) : staffInfo, sig);
      this.staff.tex.needsUpdate = true;
      this.staffKey = staffKey;
    }
    this.settle(this.own, own, t);
    this.settle(this, info, t);
    // the number depends on the key, the minor numbering and how sure the tracker is; "Numbers only" puts it in the label
    const theory = `${theoryUi.nns}|${theoryUi.minor}|${keyView.name}|${keyView.dim}`;
    const labelKey = this.shown ? this.shown.name + "|" + this.shown.notes.map((n) => n.name).join(",") + COLOUR.mode + fontState.text
                                  + (theoryUi.nns === "numbers" ? theory : "") : "";
    if (labelKey !== this.labelKey || this.needsRedraw) {
      drawLabel(this.label, this.shown);
      this.label.tex.needsUpdate = true;
      this.labelKey = labelKey;
    }
    const nnsKey = this.shown ? this.shown.name + "|" + theory + fontState.text : "";
    if (nnsKey !== this.nnsKey || this.needsRedraw) {
      drawNumbers(this.nns, this.shown);
      this.nns.tex.needsUpdate = true;
      this.nnsKey = nnsKey;
    }
    // Claude's chip: the newest caption, else the hover's; the last one stays drawn while it fades out. The player hands
    // over a new info object on every change, so identity says when to redraw (no key string per frame).
    // (a hover Claude sends while Daniel plays waits at the courtesy gate with its ghosts: captionGated)
    let cueInfo = cueView.caption || (cueView.hover && cueView.hover.info) || null;
    if (captionGated(cueInfo)) cueInfo = null;
    cueInfo = jamChipCaption(cueInfo);  // Claude's band: the chord sounding now, not the next bar's from its pickup
    // A progression's steps hold a little short of the next (pianocue: each chord's length minus 40 ms), so between two
    // chords the sequence's own caption is on top for a frame or two. Keep the step's chip through such a hand-over.
    const prev = this.cueShown;
    if (cueInfo && prev && cueInfo !== prev && cueInfo.kind === "sequence" && cueInfo.source !== "replay"
        && prev.kind !== "sequence" && prev.cue_id === cueInfo.cue_id) {
      if (!this.cueSeqSince) this.cueSeqSince = t;
      if (t - this.cueSeqSince < 0.15) cueInfo = prev;
    } else {
      this.cueSeqSince = 0;
    }
    if (cueInfo) this.cueShown = cueInfo;
    if (this.cueShown !== this.cueDrawn || this.cueFont !== fontState.text || this.needsRedraw) {
      drawCueChip(this.cue, this.cueShown);
      this.cue.tex.needsUpdate = true;
      this.cueDrawn = this.cueShown;
      this.cueFont = fontState.text;
    }
    this.needsRedraw = false;

    const quiet = sounding ? 0 : t - this.silentSince;
    const target = sounding ? 1 : quiet < 2.4 ? 0.62 : 0;
    for (const st of [this.own, this]) {  // the label shown and Daniel's own beside it fade alike
      st.labelAlpha = damp(st.labelAlpha, st.shown ? target : 0, target > st.labelAlpha ? 0.05 : (quiet < 2.4 ? 0.2 : 0.55), dt);
      st.pop = damp(st.pop, 0, 0.09, dt);
    }
    this.staffAlpha = damp(this.staffAlpha, sounding ? 1 : quiet < 2.4 ? 0.7 : 0.4, 0.25, dt);
    this.label.mat.opacity = this.labelAlpha * (1 - 0.35 * this.pop);
    this.label.mesh.scale.setScalar(1 + 0.045 * this.pop);
    this.nns.mat.opacity = this.label.mat.opacity;
    this.nns.mesh.scale.setScalar(1 + 0.045 * this.pop);
    this.staff.mat.opacity = this.staffAlpha;
    this.cueAlpha = damp(this.cueAlpha, cueInfo ? 1 : 0, cueInfo ? 0.08 : 0.35, dt);
    if (!cueInfo && this.cueAlpha < 0.01) { this.cueAlpha = 0; this.cueShown = null; }  // under 1%: gone
    this.cue.mat.opacity = this.cueAlpha * cueStage.mix;  // off the canvas (jam view) the glass draws it instead
    this.cue.mesh.visible = this.cue.mat.opacity > 0.002;
    for (const st of [this.own, this]) if (!sounding && quiet > 4.5 && st.shown) { st.shown = null; st.pending = null; }
  },
};

// -------------------------------------------------------- key and numbers --
// Daniel, 2026-09-13: "see the nashville numbers based on what key the algo thinks you are playing in".
// The key shown (HUD, overlay, numbers, spelling) is the tracker's from piano/nashville.js: the same
// Krumhansl-Kessler reading as Theory.estimateKey over pcHistory, but a new key must lead for a few seconds
// before it replaces the old one, so one borrowed bar doesn't flip it. It ticks at 10 Hz, the cadence its tests
// run. Theory.estimateKey's raw reading stays as keyRaw: the HUD shows it, and it spells notes until the tracker
// has named a key. The Key menu can lock one of the 24 keys instead.
const NNS_MODES = ["chord", "numbers", "off"];
const KEY_NAMES = [
  ...["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"].map((k) => `${k} major`),
  ...["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"].map((k) => `${k} minor`),
];
const theoryUi = {
  nns: NNS_MODES.includes(safeGet("arsenal.piano.nns")) ? safeGet("arsenal.piano.nns") : "chord",
  minor: safeGet("arsenal.piano.minor") === "relative" ? "relative" : "tonic",  // A minor's Am: 1m, or 6m
  key: KEY_NAMES.includes(safeGet("arsenal.piano.key")) ? safeGet("arsenal.piano.key") : "auto",
};
const KEY_TICK = 0.1;
const DIM_HOLD = 0.8;  // "unsure" must hold this long before the numbers dim, and "fair" as long before they brighten
const keyTracker = createKeyTracker();
// jam: the running section's key while Claude's band plays (jamKey, jam spec 8.10), else null. trackDim: the tracker's own
// unsure state with its hold (dim is that, unless the jam key is shown). trackName: the tracker's own key's name, shown or not
const keyView = { key: null, name: "", confidence: "unsure", locked: false, candidate: null, dim: false, trackDim: false, dimSince: 0,
                  at: -Infinity, jam: null, trackName: "" };
let keyRaw = null;
// The staff's key signature (live sheet music LS6, piano/keysig.js): the tracker's key, the one the numbers use with no band,
// adopted once the tracker has held it with lock confidence for 4 s (free time), never inside an open chord, at most once per
// 16 s; a key locked in the Key menu wins at once. tickKey feeds it at the tracker's 10 Hz, from Daniel's playing only.
const keySig = createKeySignatureModel();
const keyText = (name) => String(name).replace(/^([A-G])b/, "$1♭").replace(/^([A-G])#/, "$1♯");
// The jam key (8.10): while a run plays, and for 2 s after it ends, the key shown (numbers, spelling, the Key menu's auto
// line) is the running section's, so Daniel's chords are numbered in the key the band is in. A key he locked by hand
// always wins. The tracker keeps listening underneath, so its own key comes straight back afterwards.
// Only while Claude is on the stage (cueStage.on): the canvas's label and numbers are Daniel's alone whenever Claude is off
// it (8.6), so a take in auto (and the glass view) numbers his chords exactly as it would with no band playing (A5).
const JAM_KEY_HOLD = 2;
const jamKeyState = { name: null, parsed: null, until: -Infinity };
function jamKey(t) {
  if (theoryUi.key !== "auto" || !cueOnStage()) return null;  // live, so REC's arming frame already has it off
  const p = jam.position;  // tickKey first runs from boot(), after the module (and `jam`, below) is set up
  const name = p && p.state !== "waiting" && typeof p.key === "string" ? p.key : null;
  if (name) {
    if (name !== jamKeyState.name) { jamKeyState.name = name; jamKeyState.parsed = parseKey(name); }
    if (jamKeyState.parsed) jamKeyState.until = t + JAM_KEY_HOLD;
  }
  return t <= jamKeyState.until ? jamKeyState.parsed : null;
}
let keyTrack = null;  // the tracker's last reading
function tickKey(t, force = false) {
  if (!force && t - keyView.at < KEY_TICK) return;
  keyView.at = t;
  // copies the histogram; the sounding chord gives the V7 -> I cue. It hears Daniel's chords as his own reading names them
  // (ownInfo, in the tracker's key), never as the jam key reads them, so its key is the one a page with no band reaches (A5)
  keyTrack = keyTracker.update(pcHistory, t, ownInfo);
  // the dim hold runs on the tracker's own confidence, band or no band, so it is where a page with no band would be the
  // moment the jam key goes (REC in auto); the jam key only lifts the dim while it is shown
  const unsure = !keyTrack.locked && keyTrack.confidence === "unsure";
  if (unsure === keyView.trackDim) keyView.dimSince = t;
  else if (t - keyView.dimSince >= DIM_HOLD) { keyView.trackDim = unsure; keyView.dimSince = t; }
  showKey(t);
  // The signature hears Daniel alone (LS6: the page's key tracker; a manual key lock wins): the tracker's own key, with lock
  // confidence when it holds it fair or sure, and the key he locked. Never the jam key (8.10): it numbers his chords while
  // the band plays, but it must never change what a take shows (A5). Nor the band's bar clock, the only one the page has:
  // it would move the moment a signature lands, so the staff settles in free time (4 s). A chord is open while the notes of
  // its last onset sound.
  keySig.update({ t, key: keyTrack.key, sure: keyTrack.confidence === "sure" || keyTrack.confidence === "fair",
                  manual: theoryUi.key !== "auto" ? theoryUi.key : null, bar: null, chord: sounding.size ? stats.noteOns : null });
}
// The key shown: the tracker's last reading, or the jam key over it. REC in auto calls it as it arms (startRecording), before
// any recorded frame, so a take numbers Daniel's chords in his own key from its first frame, exactly as with no band.
function showKey(t) {
  const s = keyTrack;
  if (!s) return;
  const jk = jamKey(t);
  keyView.key = jk || s.key;
  keyView.confidence = jk ? "sure" : s.confidence;
  keyView.locked = s.locked;
  keyView.candidate = jk ? null : s.candidate;
  const name = keyView.key ? keyView.key.name : "";
  const jamName = jk ? jk.name : null;
  // Daniel's own reading is read again when the tracker's key changes, band or no band, exactly as on a page with no band;
  // the reading shown is read again when the jam key comes, goes or changes (jamDirty; REC in auto arms on such a frame)
  const trackName = s.key ? s.key.name : "";
  if (trackName !== keyView.trackName) { keyView.trackName = trackName; detectDirty = true; }
  if (name !== keyView.name || jamName !== keyView.jam) {
    jamDirty = true;  // respell and renumber what is sounding
    keyView.name = name;
    keyView.jam = jamName;
    syncKeySelect();
  }
  keyView.dim = keyView.trackDim && !jk;
}
function setKeyChoice(choice, persist = true) {
  theoryUi.key = KEY_NAMES.includes(choice) ? choice : "auto";
  if (persist) safeSet("arsenal.piano.key", theoryUi.key);
  keyTracker.lock(theoryUi.key === "auto" ? null : theoryUi.key);  // unlocking resumes tracking from the pinned key
  keyView.dim = false;
  keyView.trackDim = false;
  tickKey(clock(), true);
  syncKeySelect();
}
const numberFor = (info) => (info && keyView.key ? nashville(info, keyView.key, { minor: theoryUi.minor }) : null);
// The chord name, the note chips and the staff are spelled in a key by the one shared speller, piano/spell.js (the TN2
// spelling ruling, tn1-rulings.md): the root whose chord needs the fewest accidentals against the key wins (ties: the key's
// spelling, then the bias); every tone the name names goes by its letter steps from that root (the reader's own inputs, so a
// #9 stays a #9: G#7 beside 5^7 in C# minor); a bass or passing note that is no chord tone is spelled in the key. Letters
// follow the key, not the minor numbering pref (the reader spells as the tonic numbering reads). An info the reader already
// spelled in this key (info.spelledIn) comes back as it is, and one it spelled otherwise gets the same letters it would
// have had, so the page never respells the reader's name (F+(add9) stays F+(add9) in F# major, never E#+(add9)). An
// interval keeps its letter distance; a note and a cluster are spelled note by note. key: a tracker key or { name }.
function spellForKey(info, key) {
  if (!info || !key || !Array.isArray(info.notes)) return info;
  const K = keyContext(key);
  if (!K || info.spelledIn === K.name) return info;
  const pcOfMidi = (m) => Theory.mod(m, 12);
  const pcs = [...new Set(info.notes.map((n) => pcOfMidi(n.midi)))];
  let chord = null;  // spellChord's result: the chord's tones and bass, spelled together
  if (info.kind === "chord" && info.root) {
    // The tones the name names, as the reader passes them (chordread.js namedTones and spellReading): for the reading the
    // name came from, its base's tones (an omitted 5th or 3rd left out) and the tensions that sound; for a template name,
    // every tone of its suffix. Letter steps from the suffix (a dim7's 7th: spell.js DIM7_SEVENTH, a diminished 7th or a 6th,
    // whichever the key needs fewer accidentals for: B D F Ab in C minor), and the suffix the key's spelling of the root reads
    // (the reading's base, or the template's own suffix).
    const rootPc = Theory.pcOf(info.root), bassPc = info.bass ? Theory.pcOf(info.bass) : null;
    const r = Array.isArray(info.readings) ? info.readings.find((x) => x && x.root === rootPc && (x.bass ?? null) === bassPc
      && !!(x.omit && x.omit.no3) === !!info.no3 && String(x.suffix).replace("(no3)", "") === info.suffix) : null;
    const parsed = parseSuffix(r ? r.suffix : info.suffix), steps = { ...parsed.tones };
    if (parsed.base === "dim7" && 9 in steps) steps[9] = [6, 5];  // spell.js DIM7_SEVENTH
    const grammar = !!r && r.path !== "template" && !!r.base && Array.isArray(r.tensions);
    const ivs = grammar
      ? [...Object.keys(parseSuffix(r.base.id).tones).map(Number).filter((t) => !(r.omit.no5 && t === 7) && !(r.omit.no3 && (t === 3 || t === 4))), ...r.tensions]
      : Object.keys(steps).map(Number);
    chord = spellChord({ rootPc, tonesPc: ivs.map((iv) => rootPc + iv), steps, bassPc, key: K,
                         suffix: r ? (r.path === "template" ? r.suffix : r.base.id) : info.suffix });
  } else if (info.kind === "interval" && info.root && info.upper) {
    const rootPc = Theory.pcOf(info.root), iv = Theory.mod(Theory.pcOf(info.upper) - rootPc, 12);
    chord = spellChord({ rootPc, tonesPc: [rootPc + iv], steps: { [iv]: Theory.mod(info.upper.letter - info.root.letter, 7) }, key: K });
  }
  const map = new Map();  // pitch class -> spelling
  for (const pc of pcs) { const s = spellNote(pc, K, { chord }); map.set(pc, { letter: s.letter, acc: s.acc }); }
  if ([...map.values()].some((s) => Math.abs(s.acc) > 2)) return info;
  const at = (sp) => map.get(Theory.pcOf(sp));
  const notes = info.notes.map((n) => {
    const s = map.get(pcOfMidi(n.midi));
    return { ...n, letter: s.letter, acc: s.acc, name: Theory.nameOf(s), octave: Theory.octaveOf(n.midi, s), diatonic: Theory.diatonicOf(n.midi, s) };
  });
  const pcNames = pcs.map((pc) => Theory.nameOf(map.get(pc)));
  const out = { ...info, notes, pcNames, spelledIn: K.name };
  if (info.kind === "cluster") { out.name = pcNames.join(" "); return out; }
  out.root = at(info.root);
  if (info.upper) out.upper = at(info.upper);
  if (info.bass) out.bass = at(info.bass);
  if (info.kind === "note") {
    if (notes.length === 1) out.octave = notes[0].octave;
    out.name = Theory.nameOf(out.root) + (notes.length === 1 ? notes[0].octave : "");
  } else if (info.kind === "interval") {
    out.name = `${Theory.nameOf(out.root)}-${Theory.nameOf(out.upper)}`;
  } else {
    out.name = Theory.nameOf(out.root) + info.suffix + (out.bass ? "/" + Theory.nameOf(out.bass) : "");
  }
  return out;
}

// ----------------------------------------------------------- practice log --
// Daniel, 2026-09-13: "keep a temp log of the notes so you can see how I play music theory wise". piano/log.js
// records every note, pedal change, sound ending and chord change with its key and number, and the server
// summarises each session for the agents (arsenal/PIANO-V2-SPEC.md sections 4 and 6.5). Nothing is sent per note:
// log.js batches into IndexedDB and uploads in the background, and keeps buffering while the server has no
// practice-log routes. Log calls sit behind logged(), so nothing in the log can reach the note path. The demo is
// not Daniel's playing, so it is not logged.
//
// A GET (no body) asks first whether this server has the routes. A server started before the practice log existed,
// or run with --no-performance-log, answers log.js's POSTs 404 without reading their bodies, and on its keep-alive
// connection the unread body corrupts the next request (seen 2026-09-13: the next POST came back 501). A REC upload
// could be that next request. So without the routes log.js is pointed at port 9, which the browser refuses to
// connect to: it buffers exactly as when the server is down, and nothing reaches the server. The GET repeats each
// minute only to tell Daniel when a reload would upload what is kept.
const LOG_PREF = "arsenal.piano.log";
const LOG_ENDPOINT = "/api/performance";
const LOG_NOWHERE = "http://127.0.0.1:9/api/performance";
let perfLog = null;
let logRoutes = null;  // null: still asking; true: this server takes the log; false: buffering here; "reload": it does now
const hasLogRoutes = () => fetch(LOG_ENDPOINT, { cache: "no-store" }).then((r) => r.ok, () => false);
async function startLog() {
  const ok = await hasLogRoutes();
  try {
    perfLog = createPerformanceLog({ endpoint: ok ? LOG_ENDPOINT : LOG_NOWHERE, meta: { page: "piano" },
                                     enabled: safeGet(LOG_PREF) !== "off", pageId: PAGE_ID });
  } catch (e) {
    console.warn("[piano] practice log unavailable:", errText(e));
  }
  logRoutes = ok;
  syncLogButton();
  syncLogReadout();
  if (ok) return;
  const timer = setInterval(async () => {
    if (await hasLogRoutes()) { logRoutes = "reload"; clearInterval(timer); syncLogReadout(); }
  }, 60000);
}
let logMuted = false;  // set around the demo's own note calls
let logFailed = false;
function logged(fn) {
  if (!perfLog || logMuted || demo.running) return;
  try {
    fn(perfLog);
  } catch (e) {
    if (!logFailed) { logFailed = true; console.warn("[piano] practice log call failed (ignored):", errText(e)); }
  }
}
const pageSec = (t) => T0 + t;  // log.js takes page-clock seconds (performance.now() / 1000)
// One chord event per change of the detected name, key, number or lock; log.js drops exact repeats as well.
let loggedChord = "";
function logChord(t) {
  const info = lastInfo, key = keyView.key;
  const sig = info ? `${info.name}|${keyView.name}|${lastNns ? lastNns.text : ""}|${keyView.locked}` : "";
  if (sig === loggedChord) return;
  loggedChord = sig;
  logged((log) => log.chord(info && {
    name: info.name, kind: info.kind, notes: info.notes, bass: info.bass, key: key && key.name,
    nns: lastNns ? lastNns.text : null, nns_key: key && key.name, key_conf: key ? keyView.confidence : null, locked: keyView.locked,
  }, pageSec(t)));
}

// ----------------------------------------------------------- notes engine --
// A note sounds while its key is held, or after release while the pedal (CC64) is down.
const sounding = new Map();  // midi -> { held, vel, t0, tRelease, strike, trail }
const strikeCount = new Uint32Array(128);  // per key, ++ on every note on: two strikes inside one frame share a t0, not this
let sustain = false;
let detectDirty = true;
let jamDirty = false;  // the jam key came, went or changed: the reading shown is read again, Daniel's own is not (currentInfo)
let lastInfo = null;
let ownInfo = null;    // Daniel's own reading, in the tracker's key (lastInfo itself whenever the jam key is not shown)
let lastNns = null;  // nashville() of lastInfo in the shown key
const pcHistory = new Array(12).fill(0);  // decaying pitch-class weights: the key tracker and estimateKey read it
let pcHistoryAt = 0;
const stats = { noteOns: 0 };

// How lit a sounding key is: the shared light model (LIGHT, also the trail shader's), taken at this moment.
// Daniel, 2026-09-13: brightest with finger and pedal down together, still clearly lit while only the
// pedal holds the note, velocity always counts.
function glowLevel(st, t) {
  return lightLevel(st.vel / 127, st.held, sustain ? 1 : 0, t - st.t0);
}

function noteOn(m, vel) {
  if (vel <= 0) { noteOff(m); return; }
  const t = clock();
  spectacle?.noteOn(m, vel, t);
  beforeChange(t);
  const prev = sounding.get(m);
  if (prev) {
    trails.end(prev.trail, t);  // a repeated note closes its previous trail
    lookNoteEnd(m, t);          // and the scheme's previous sound
    logged((log) => log.soundEnd(m, "repeat", pageSec(t)));
  }
  logged((log) => log.noteOn(m, vel, pageSec(t)));
  const inRange = m >= KEY.first && m <= KEY.last;
  sounding.set(m, { held: true, vel, t0: t, tRelease: 0, strike: ++strikeCount[m], trail: inRange ? trails.start(m, vel, t) : null });
  if (inRange) {
    const k = keys.get(m);
    k.target = 0.17 + 0.27 * (vel / 127);  // velocity-scaled key depth (world units at the key front)
    k.glowTarget = glowLevel(sounding.get(m), t);
    noteColor(m, vel, k.color);
    burst(m, vel, t);
    lightNote(m, vel);
    hintCamera(m, t);
    lookNoteOn(m, vel, t, sounding.get(m));
  }
  const f = Math.exp(-(t - pcHistoryAt) / 12);
  for (let i = 0; i < 12; i++) pcHistory[i] *= f;
  pcHistoryAt = t;
  pcHistory[Theory.mod(m, 12)] += 0.5 + vel / 127;
  stats.noteOns++;
  detectDirty = true;
  afterChange(t);
  hideIdleHint();
  if (!demo.running) jamHeard(m, vel);  // Claude's band hears him: his rest (8.9), the duck, the owner lease, the floor pool
}
function noteOff(m) {
  const st = sounding.get(m);
  if (!st || !st.held) return;
  const t = clock();
  spectacle?.noteOff(m, t, sustain);
  beforeChange(t);
  st.held = false;
  st.tRelease = t;
  jamRest.noteOff(m);
  trails.release(st.trail, t);
  lookNoteOff(m, t, sustain);  // the scheme: a release while the pedal holds the sound, else the sound's end
  const k = keys.get(m);
  // Daniel's fields only: a key Claude still holds stays down and moonlit (cueTarget, cueGlowTarget: Claude's hand)
  if (k) { k.target = 0; k.glowTarget = sustain ? glowLevel(st, t) : 0; }
  logged((log) => { log.noteOff(m, pageSec(t)); if (!sustain) log.soundEnd(m, "release", pageSec(t)); });
  if (!sustain) { trails.end(st.trail, t); sounding.delete(m); }
  detectDirty = true;
  afterChange(t);
}
// value: the raw CC64 value, for the log (a half-pedalling controller sends many; only the crossing is logged)
function setSustain(on, value = on ? 127 : 0) {
  if (sustain === on) return;
  const t = clock();
  spectacle?.pedal(on, t);
  beforeChange(t);
  sustain = on;
  lookEvent("pedal", on, value, t);
  if (!demo.running) jamRest.sustain(on);
  logged((log) => log.pedal(on, value, pageSec(t)));
  if (!on) {
    // The pedal is Daniel's: cue notes ignore it, and this loop touches only his notes and his glow fields.
    for (const [m, st] of sounding) {
      if (st.held) continue;
      trails.end(st.trail, t);
      lookNoteEnd(m, t);
      logged((log) => log.soundEnd(m, "pedal", pageSec(t)));
      sounding.delete(m);
      const k = keys.get(m);
      if (k) k.glowTarget = 0;
    }
  }
  detectDirty = true;
  afterChange(t);
}
function allNotesOff() {  // CC120 (all sound off), CC123 (all notes off), input switches, Demo stop
  const t = clock();
  spectacle?.clear(t);
  beforeChange(t);
  for (const [m, st] of sounding) {
    trails.end(st.trail, t);
    lookNoteEnd(m, t);
    logged((log) => log.soundEnd(m, "all-off", pageSec(t)));
    const k = keys.get(m);
    if (k) { k.target = 0; k.glowTarget = 0; }
  }
  for (const m of sounding.keys()) jamRest.noteOff(m);
  sounding.clear();
  if (sustain) { logged((log) => log.pedal(false, 0, pageSec(t))); lookEvent("pedal", false, 0, t); }
  sustain = false;
  jamRest.sustain(false);
  detectDirty = true;
  afterChange(t);
  // Claude's hand is untouched here: a Demo or a MIDI input switch is about Daniel's notes. The MIDI panic itself
  // (CC120/123, onMidiMessage) and Esc/Backspace hush Claude as well.
}
// The chord reader names what sounds (TN2) with the key it may trust (trust): a key the tracker holds fair or sure, a key
// locked in the Key menu, or the jam key. An unsure key is no key to it (spec 2.1 A1: a no-3rd chord's family stays open,
// and names are spelled by the bias), and spellForKey then spells its name in the key read in. prev: the root of the chord
// before, the reader's previous-root prior. own: Daniel's own reading (in the tracker's key), the only one that moves that
// prior; the jam key's reading borrows it as it stands, so his own reading is never steered by the band's key.
const readerChord = { root: null, prev: null };
function detectSounding(bias, trust = null, own = true) {
  const midis = [...sounding.keys()];
  if (!pianoReader) return Theory.detect(midis, bias);
  const k = trust ? keyContext(trust) : null;
  const info = Theory.detect(midis, bias, { key: k ? k.name : null, prev: readerChord.prev === null ? null : { root: readerChord.prev } });
  if (info && k && Array.isArray(info.readings)) info.spelledIn = k.name;  // the reader spelled it in this key already
  if (own && info && info.kind === "chord" && info.root) {
    const root = Theory.pcOf(info.root);
    if (root !== readerChord.root) { readerChord.prev = readerChord.root; readerChord.root = root; }
  }
  return info;
}
// What sounds, read in key (trusted: the reader may use it) and spelled in it
function readSounding(key, trusted, own) {
  const bias = key ? key.bias : keyRaw ? keyRaw.bias : 0;
  return spellForKey(detectSounding(bias, key && trusted ? key : null, own), key);
}
// t: the moment it is read at (a frame's clock, or a catch-up's; see "theory without frames")
// Two readings (A5). ownInfo is Daniel's own, in the tracker's key, read again only when a page with no band would read
// again (detectDirty: a note, the pedal, the minor numbering, the tracker's key): the key tracker hears it, and the label
// settles on it beside the shown one (overlay.own). lastInfo is what the page shows: while the jam key (8.10) is shown, what
// sounds read in that key (read again on jamDirty too), else ownInfo itself. So the frame the jam key leaves (REC in auto)
// reads and draws exactly what a page with no band would.
function currentInfo(t = clock()) {
  if (!detectDirty && !jamDirty) return lastInfo;
  // the jam key's reading first, so it borrows the reader's prior as Daniel's own reading finds it
  const jamRead = keyView.jam && sounding.size ? readSounding(keyView.key, true, false) : null;
  if (detectDirty) {
    keyRaw = Theory.estimateKey(pcHistory);
    const track = keyTrack && keyTrack.key ? keyTrack : null;
    ownInfo = sounding.size ? readSounding(track ? track.key : null, !!track && (track.locked || track.confidence !== "unsure"), true) : null;
    if (ownInfo) ownInfo.onCount = stats.noteOns;  // lets the label tell a new note from a release
  }
  if (jamRead) jamRead.onCount = stats.noteOns;
  detectDirty = false;
  jamDirty = false;
  lastInfo = keyView.jam ? jamRead : ownInfo;
  lastNns = numberFor(lastInfo);
  logChord(t);
  return lastInfo;
}

// ----------------------------------------------------------- Claude's hand --
// Daniel, 2026-09-14: "can we make a verb for you to be able to play a chord you are curious about or hovering it in the
// viewer?" ... "so I can click and hear concepts you are describing and have a visual for them". Claude sends cues with
// `py -m arsenal.pianocue`; piano/cues.js listens (createCueClient), schedules them (createCuePlayer) and sounds them in
// Claude's own voice (createClaudeVoice). This section is the page's half.
//
// Cue notes never enter `sounding`. They live in cueSounding, so they are never in detect(), the chord label, the note
// chips, the Nashville row, the staff, the key tracker, stats.noteOns, logged() (the practice log, and every summary,
// count and rarity built from it), the stage tint or the light budget. Each key keeps Claude's depth and light in its
// own fields (cueTarget, cueGlow), so a key both hands hold stays down until both let go. The pedal is Daniel's.
//
// How they look (jam spec 8.5): Claude's keys press to 60% of the depth Daniel's would, glow moonlight (#C8DCFF) at 0.75
// of the light his would have at that velocity, and are never pitch-tinted; no trails, sparks or note lights. A key
// both hold keeps Daniel's colour, with a thin moonlight rim. A replay of Daniel's own playing ("YOU · you, at 5:22")
// shows his pitch colours at 55% saturation and 70% glow, trails at half gain, no sparks. A hover draws ghost rims with a
// faint breathing fill. The chip (drawCueChip) names what Claude meant.
//
// Jam view (arsenal.piano.jam.view): "auto" (default) keeps Claude on the stage while Daniel practises, and the moment REC
// starts takes Claude's keys, ghosts, chip and replay trails off the recorded canvas onto the glass (an unrecorded 2D
// layer over it); "stage" keeps them on the canvas, in recordings too; "glass" keeps them off it always. Claude's voice
// is never connected to the recorder in any view: it plays through its own AudioContext, and the recording takes only
// the canvas and the chosen audio input (if that input is a Loopback of the speakers, the speakers are in it).
const CUE_PREF = { listen: "arsenal.piano.cueListen", voice: "arsenal.piano.cueVoice", volume: "arsenal.piano.cueVolume",
                   midiOut: "arsenal.piano.cueMidiOut", synth: "arsenal.piano.cueSynth", lowLift: "arsenal.piano.cueLowLift",
                   bassDouble: "arsenal.piano.cueBassDouble", view: "arsenal.piano.jam.view" };
// The jam view's pref has the name jam spec 8.8 gives it (arsenal.piano.jam.view). Pages before that stored it as
// arsenal.piano.cueView: a stored choice moves over once, unless the new name already holds one.
{
  const old = safeGet("arsenal.piano.cueView");
  if (old !== null) {
    if (safeGet(CUE_PREF.view) === null) safeSet(CUE_PREF.view, old);
    try { localStorage.removeItem("arsenal.piano.cueView"); } catch { /* storage blocked */ }
  }
}
const CUE_VIEWS = ["auto", "stage", "glass"];
const CUE_LOOK = { depth: 0.6, glow: 0.75, replayGlow: 0.7, replaySat: 0.55, replayTrail: 0.5 };
const cueSounding = new Map();  // midi -> { m, vel, t0, source, trail } (m again, so frame loops need no [key, value] pairs)
const cueTrails = [];           // a replay's recent trail refs, so REC can take them off the canvas at once
const NO_GHOSTS = new Set();
const cueView = { status: "off", hover: null, caption: null, ghost: NO_GHOSTS, last: null, lastLabel: null, want: false };
const cueQueryView = new URLSearchParams(location.search).get("jam");  // receipts: ?jam=auto|stage|glass, never stored
const cueStage = {
  view: CUE_VIEWS.includes(cueQueryView) ? cueQueryView : CUE_VIEWS.includes(safeGet(CUE_PREF.view)) ? safeGet(CUE_PREF.view) : "auto",
  on: true, mix: 1, glass: 0, lit: 0,  // on: Claude is drawn on the canvas; mix: its fade there; glass: the glass layer's
};
let cueUiDirty = true, cueUiAt = 0, cueLocalSeq = 0;
// The echo guard (midiRank) knows the port before it opens. Never the KeyLab: a stored KeyLab name (cues-test.html shares
// this pref, and older pages allowed it) must not make /piano stop listening to Daniel's keyboard.
let cueMidiOutName = isKeyLabKeys(safeGet(CUE_PREF.midiOut)) ? "" : safeGet(CUE_PREF.midiOut) || "";
const cueDepth = (vel) => CUE_LOOK.depth * (0.17 + 0.27 * (vel / 127));  // 60% of noteOn's velocity-scaled depth
const cueGlowLevel = (st, t) => (st.source === "replay" ? CUE_LOOK.replayGlow : CUE_LOOK.glow) * lightLevel(st.vel / 127, true, 0, t - st.t0);
// Claude is off the canvas in "glass", and in "auto" while REC runs or is about to start (rec.arming: startRecording).
const cueOnStage = () => cueStage.view === "stage" || (cueStage.view === "auto" && rec.state !== "recording" && !rec.arming);
function replayColor(m, vel, target) {  // Daniel's pitch colour at 55% saturation
  noteColor(m, vel, target);
  const l = lumaOf(target.r, target.g, target.b), s = CUE_LOOK.replaySat;
  return target.setRGB(lerp(l, target.r, s), lerp(l, target.g, s), lerp(l, target.b, s));
}

function cueNoteOn(m, vel, meta) {
  const t = clock();
  if (jam.record && jam.record.length < 400000) {  // receipts only (__piano.jam.record): every strike of Claude's, heard or not
    jam.record.push({ t: performance.now(), m, vel, cue: meta ? meta.cue_id ?? null : null, at: meta && Number.isFinite(meta.at) ? meta.at : null,
                      sound: !meta || meta.sound !== false, source: meta && meta.source === "replay" ? "replay" : "claude" });
  }
  if (meta && Number.isFinite(meta.at)) cueStepStarted(meta, meta.at / 1000 - T0);  // meta.at: the strike's performance.now()
  const replay = !!meta && meta.source === "replay";
  const prev = cueSounding.get(m);
  if (prev && prev.trail) trails.end(prev.trail, t);  // a restrike closes the old column
  const inRange = m >= KEY.first && m <= KEY.last;
  const trail = inRange && replay && cueStage.on ? trails.start(m, vel, t, CUE_LOOK.replayTrail, true) : null;
  if (trail) { cueTrails.push(trail); if (cueTrails.length > 128) cueTrails.shift(); }
  const st = { m, vel, t0: t, source: replay ? "replay" : "claude", trail };
  cueSounding.set(m, st);
  if (!inRange) return;
  const k = keys.get(m);
  k.cueTarget = cueDepth(vel);
  k.cueReplay = replay;
  // a replay's glass quad takes the key's own faded colour; Claude's key the moonlight capped under Daniel's light (moonColor)
  if (replay) { replayColor(m, vel, k.cueColor); k.cueCss = k.cueColor.getStyle(); }
  else { moonColor(vel, k.cueColor); moonSurface(vel, k.cueSurface); }
  k.cueGlowTarget = cueGlowLevel(st, t);
  if (cueOnStage()) hintCamera(m, t, true);  // off the canvas (glass, or auto while REC runs) Claude never moves the view
  hideIdleHint();
  // deliberately absent: burst, lightNote, logged(...), pcHistory, stats.noteOns++, detectDirty, before/afterChange
}
function cueNoteOff(m, meta) {
  cueCancelled(meta);
  const st = cueSounding.get(m);
  if (!st) return;
  const t = clock();
  if (st.trail) { trails.release(st.trail, t); trails.end(st.trail, t); }
  cueSounding.delete(m);
  const k = keys.get(m);
  if (k) { k.cueTarget = 0; k.cueGlowTarget = 0; }  // Claude's fields only: a key Daniel holds stays down and lit
}

// The schedule of Claude's sequences, for the camera's look-ahead (updateCamera, cueAhead): cue id -> { base, steps,
// created }. steps: [{ at, notes }], seconds from the sequence's 0 ms, at the index the player reports (meta.step: a cue's
// own step order). base: the clock time that 0 ms fell on, known once one of its steps has started (the player may start
// a cue later than it arrived, behind a backlog); until then the plan looks ahead to nothing. A clear or a page hide drops
// every plan, a backlog cue the player dropped its own; a plan with no step still to land drops itself, and one that
// never started goes after CUE_PLAN_STALE s.
const cuePlans = new Map();
const CUE_PLAN_STALE = 60;
function planCue(cue, id, t = clock()) {
  if (!cue || typeof cue !== "object") return;
  if (cue.type === "clear") { cuePlans.clear(); return; }
  if (cue.type !== "sequence" || !Array.isArray(cue.steps)) return;
  for (const [key, p] of cuePlans) if (p.base === null && t - p.created > CUE_PLAN_STALE) cuePlans.delete(key);
  const steps = cue.steps.map((s) => ({
    at: (s && Number.isFinite(s.at_ms) ? s.at_ms : 0) / 1000,
    notes: (s && Array.isArray(s.notes) ? s.notes : []).filter((m) => Number.isInteger(m) && m >= KEY.first && m <= KEY.last),
  }));
  cuePlans.set(id, { base: null, steps, created: t });
}
// A step began at clock time `at` (a strike's own time, or now for a hover). An arpeggio's later notes start after the
// step does, so the earliest report is the step's start.
function cueStepStarted(meta, at) {
  const p = meta ? cuePlans.get(meta.cue_id) : null;
  const s = p && Number.isInteger(meta.step) ? p.steps[meta.step] : null;
  if (s) p.base = Math.min(p.base ?? Infinity, at - s.at);
}
function cueCancelled(meta) {  // the player ended cues early (meta.reason other than "hold")
  const reason = meta && meta.reason;
  if (!reason || reason === "hold") return;
  if (reason === "backlog") cuePlans.delete(meta.cue_id); else cuePlans.clear();
}
// The keys of every step of a started sequence that lands after now and within CAM.lookahead s, into box.
function cueAhead(t, box) {
  for (const [id, p] of cuePlans) {
    if (p.base === null) continue;
    const now = t - p.base;
    let later = false;
    for (const s of p.steps) {
      if (s.at <= now) continue;
      later = true;
      if (s.at - now <= CAM.lookahead) for (const m of s.notes) camAdd(box, keyX(m));
    }
    if (!later) cuePlans.delete(id);
  }
}

// Once per frame, before updateKeys. Leaving the canvas has no fade (the first recorded frame must already be clean):
// Claude's keys jump back up, a replay's trails go, and the glass fades in instead. Coming back fades in over 250 ms.
function tickCueStage(dt) {
  const on = cueOnStage();
  if (!on && cueStage.on) {
    for (const k of keys.values()) { k.cueDepth = 0; k.cueV = 0; }  // Claude's presses (Daniel's springs are his own)
    for (const ref of cueTrails) trails.kill(ref);
    cueTrails.length = 0;
    for (const st of cueSounding.values()) st.trail = null;
    trailUniforms.uDensity.value = lightBudget.danDensity;  // the light budget of Daniel's columns alone
    // and Claude stops steering the view: from this frame on, the view a page with no Claude would have (a new array only
    // at this moment)
    cam.cueRecent = [];
    cam.x = camDan.x;
    cam.span = camDan.span;
    cam.hurry = camDan.hurry;
    pool.level = 0;  // the moonlight floor pool goes with Claude's keys, at once
    poolMesh.material.opacity = 0;
    poolMesh.visible = false;
  }
  if (on) {
    cueStage.mix = damp(cueStage.mix, 1, 0.08, dt);
    cueStage.glass = 1 - cueStage.mix;
  } else {
    cueStage.mix = 0;
    cueStage.glass = damp(cueStage.glass, 1, 0.08, dt);
  }
  cueStage.on = on;
}

// The glass (#jam-glass, piano/glass.js): an unrecorded 2D canvas over the WebGL one, on the canvas's CSS box. While Claude
// is off the canvas (jam view glass, or auto while REC runs) it draws what the stage would: Claude's lit keys as moonlight
// quads at 38% fill with an 80% rim (a replay in its faded pitch colour), the ghost rims in their states (target, dashed
// incoming, the inner hold rim, the found pulse) through each key top's own perspective, and the chip. glassKeyTop hands it
// a key's rest-pose top face through this frame's camera, in CSS pixels of the glass box (back-left, back-right,
// front-right, front-left, as the face is built).
const glassEl = $("jam-glass");
const glassBox = { width: 0, height: 0, had: false };  // had: the last draw put something on the glass
const glassPt = new THREE.Vector3();
function glassKeyTop(m) {
  const k = keys.get(m);
  if (!k || !glassBox.width) return null;
  const s = glassBox.width / framing.w, f = k.face, quad = [];
  for (let i = 0; i < 4; i++) {
    glassPt.set(f[i * 3], f[i * 3 + 1], f[i * 3 + 2]).project(camera);
    quad.push([(glassPt.x + 1) * 0.5 * framing.w * s, (1 - glassPt.y) * 0.5 * framing.h * s]);
  }
  return quad;
}
const jamGlass = glassEl ? createGlass({ canvas: glassEl, projectKeyTop: glassKeyTop, isBlack }) : null;
const glassClaude = [];
// After the frame is drawn (the camera has moved); only while the glass has something on it, or has to be cleared.
function drawGlass() {
  if (!jamGlass) return;
  const a = cueStage.glass;
  if (a < 0.004 && !glassBox.had) return;
  glassClaude.length = 0;
  let ghosts = null, chip = null;
  if (a >= 0.004) {
    for (const k of keys.values()) {
      if (k.cueGlow > 0.004) glassClaude.push({ midi: k.m, level: Math.min(1, k.cueGlow * 1.6), css: k.cueReplay ? k.cueCss : null });
    }
    if (cueView.ghost.size) {
      ghosts = { target: [...jamGhosts.target], incoming: [...jamGhosts.incoming], hold: [...jamGhosts.hold], found: jamGhosts.foundPerf };
    }
    if (overlay.cue && overlay.cueAlpha > 0.004) {
      const sp = overlay.cue.spec, s = glassBox.width / framing.w;
      chip = { image: overlay.cue.canvas, x: (sp.cx - sp.w / 2) * s, y: (sp.cy - sp.h / 2) * s, w: sp.w * s, h: sp.h * s,
               alpha: overlay.cueAlpha };
    }
  }
  const has = glassClaude.length > 0 || !!ghosts || !!chip;
  if (!has && !glassBox.had) return;
  jamGlass.draw({ ghosts, claude: glassClaude, chip, alpha: a });
  glassBox.had = has;
}

// Navi's moonlight floor pool (house ideas, 2026-09-14): while Claude's band plays a Loop or a Try on the stage, a soft
// moonlight radial lies on the floor under Claude's hand, swells a little on each beat (most on the downbeat), and dims
// while Daniel plays strongly (velocity over POOL.strongFrom). One normal-blended quad whose brightest point stays far under
// the bloom threshold, outside the light budget. It is drawn only while Claude is on the canvas (cueStage.on): REC in auto
// never records it, and it goes at once, with no fade, when Claude leaves the canvas (tickCueStage).
const POOL = { opacity: 0.1, width: 26, depth: 13, y: -2.28, z: 3.4, dim: 0.65, strongFrom: 50, strongSpan: 60, strongTau: 1.2,
               inTau: 0.5, outTau: 0.8, beatTau: 0.3, swell: 0.3, offbeat: 0.6, followTau: 0.8 };
const poolMesh = (() => {
  // The falloff is drawn opaque, grey on black: an alphaMap reads the green channel, and a gradient of white at falling alpha
  // keeps its green at full, which drew the pool as a hard-edged disc.
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = "#000";
  g.fillRect(0, 0, 128, 128);
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, "rgb(255,255,255)");
  grad.addColorStop(0.3, "rgb(150,150,150)");
  grad.addColorStop(0.65, "rgb(48,48,48)");
  grad.addColorStop(1, "rgb(0,0,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({
    color: MOON, alphaMap: new THREE.CanvasTexture(c), transparent: true, opacity: 0, depthWrite: false, blending: THREE.NormalBlending }));
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(0, POOL.y, POOL.z);
  mesh.scale.set(POOL.width, POOL.depth, 1);
  mesh.visible = false;
  scene.add(mesh);
  return mesh;
})();
const pool = { level: 0, strong: 0, x: 0, beatAt: -Infinity, downbeat: false };
function updatePool(dt, t) {
  pool.strong *= Math.exp(-dt / POOL.strongTau);
  const p = jam.position;
  const live = cueStage.on && !!p && p.mode !== "play" && p.state !== "waiting" && Number.isFinite(p.bar);
  let target = 0;
  if (live) {
    const swell = Math.exp(-Math.max(0, t - pool.beatAt) / POOL.beatTau) * (pool.downbeat ? 1 : POOL.offbeat);
    target = (1 - POOL.swell + POOL.swell * swell) * (1 - POOL.dim * Math.min(1, pool.strong));
  }
  pool.level = damp(pool.level, target, target > pool.level ? POOL.inTau : POOL.outTau, dt);
  let sx = 0, n = 0;
  for (const st of cueSounding.values()) if (st.source !== "replay") { sx += keyX(st.m); n++; }
  if (n) pool.x = damp(pool.x, sx / n, POOL.followTau, dt);
  poolMesh.position.x = pool.x;
  poolMesh.material.opacity = POOL.opacity * pool.level;
  poolMesh.visible = cueStage.on && poolMesh.material.opacity > 0.002;
}

// The voice and player. The voice calls onStatus once from inside createClaudeVoice, before the page is wired, so it
// only raises a flag; renderFrame syncs the controls. Its unlock listeners (the first click or key) are registered in
// createClaudeVoice, so the status a press found is noted first, here (the Voice button must not read an unlock that
// press itself started as "turn the voice off").
let cuePressStatus = null;
for (const type of ["pointerdown", "keydown"]) {
  window.addEventListener(type, () => { try { cuePressStatus = cueVoice.status(); } catch { cuePressStatus = null; } }, true);
}
const cueVoice = createClaudeVoice({
  volume: (() => { const v = Number.parseFloat(safeGet(CUE_PREF.volume) ?? "0.7"); return Number.isFinite(v) ? clamp(v, 0, 1) : 0.7; })(),
  enabled: safeGet(CUE_PREF.voice) !== "off",
  internal: safeGet(CUE_PREF.synth) !== "off",
  lowLift: safeGet(CUE_PREF.lowLift) === "off" ? 0 : 1,
  polyphony: 24,  // jam spec 8.11 item 2: Claude's band (transport.js) raises it to 40 while a run sounds
  onStatus: () => { cueUiDirty = true; },
});
const cuePlayer = createCuePlayer({
  voice: cueVoice,
  bassDouble: safeGet(CUE_PREF.bassDouble) === "on",
  noteOn: cueNoteOn,
  noteOff: cueNoteOff,
  // a hover's ghosts go through the courtesy gate (8.9, gateHover) and join the band's and the deck's (syncGhosts)
  hover: (notes, info) => { cueView.hover = { notes, info }; gateHover(info); syncGhosts(); cueStepStarted(info, clock()); },
  clearHover: (info) => { cueView.hover = null; hoverGate.open = true; syncGhosts(); cueCancelled(info); },
  caption: (info) => { cueView.caption = info; },
  onError: (e) => console.warn("[piano] cue player:", errText(e)),
});
let cueClient = null, cueClickToastAt = -1e9;
// shown while the voice waits for a click; syncCueUi takes it down the moment the voice is unlocked or turned off
const CUE_CLICK_TOAST = "Claude is playing: click the page once (or Enable voice) to hear it";
async function startCues() {
  if (safeGet(CUE_PREF.listen) === "off") { cueView.status = "off"; cueUiDirty = true; return; }
  // Like the practice log, ask first: a server from before the cue routes answers 404 and gets no retry loop.
  // A server that is down (fetch throws) still gets a client: it keeps retrying until the server is up.
  const routes = await fetch("/api/piano/cues/status", { cache: "no-store" }).then((r) => r.status !== 404, () => true);
  if (!routes) { cueView.status = "no routes"; cueUiDirty = true; return; }
  cueClient = createCueClient({  // the only stream: the client closes it on pagehide and freeze, so no unload handler
    // jam1, deck1: this page plays Claude's band and shows the deck (jam spec 6); page: the id its log and acks carry
    url: `/api/piano/cues?caps=jam1,deck1&page=${encodeURIComponent(PAGE_ID)}`,
    events: {
      jam: (payload, info) => { try { transport.apply(payload, info); } catch (e) { jamWarn("jam frame", e); } },
      deck: (payload) => { if (jam.deck) jam.deck.applyDeckFrame(payload); },
    },
    onCue: (cue, info) => {
      noteCue(cue, info.id);
      planCue(cue, info.id);  // before the player, which may start a step at once
      cuePlayer.handle(cue, info);  // info (sent_at, age_ms) keeps a backlog spaced and the voice in one tab
      const sounds = (cue.type === "play" || cue.type === "sequence") && cue.sound;
      if (sounds && cueVoice.enabled && cueVoice.status() === "needs a click") {
        cueView.want = true;
        if (clock() - cueClickToastAt > 20) {
          cueClickToastAt = clock();
          toast(CUE_CLICK_TOAST);  // KeyLab MIDI is not a gesture
        }
      }
      cueUiDirty = true;
    },
    onStatus: (s) => {
      cueView.status = s;
      cueUiDirty = true;
      // a lost stream stops a run after 2 bars; every open reads the jam and the deck again (state is truth, jam spec 6)
      try { transport.streamStatus(s); } catch (e) { jamWarn("stream status", e); }
      if (s === "listening" && jam.deck) jam.deck.refresh();
    },
  });
}
// "Stop Claude" (8.7): Esc / Backspace, the deck's Stop, and the MIDI panic (CC120/123). Pending cues, Claude's keys and
// sound, a running Loop, Try or Play (stopped now, with an 80 ms fade), the ghosts and the chip; Daniel's notes untouched.
function hushClaude() {
  cuePlans.clear();
  cuePlayer.clear();
  hoverGate.open = true;
  try { Promise.resolve(transport.stop("now")).catch((e) => jamWarn("stop", e)); } catch (e) { jamWarn("stop", e); }
  if (jam.deck) jam.deck.act("dismiss");
}

// ------------------------------------------------------------- Claude's band --
// Daniel, 2026-09-14: "I want us to be able to play in this space, can you make verbs so you can play chord progressions or
// show loops of chords for me to try, I can then riff on that and play with it and we can discuss it". The jam space
// (research/in-flight/piano-jam-2026-09-14/jam-spec.md) is wired here, per its section 8.11:
// - piano/transport.js keeps a run's time (Play, Loop, Try) and hands Claude's player one bar at a time. Only the page that
//   owns the jam sounds a run (Daniel's input claims it); a run Claude sends waits for his rest, then knocks (8.9).
// - piano/deck.js is the drawer of cards at the stage's right (A, the arrow keys, Enter, K, \, ', - =, [ ]).
// - piano/glass.js draws Claude's keys and ghosts on the glass while the jam view keeps Claude off the recorded canvas.
// - Ghosts come from three places and are drawn together (syncGhosts): a hover cue, the deck (a chip's hover, Show) and a
//   Try (the chord now, the next one on the last beat, the pitch classes they share).
// None of it reaches `sounding`, the practice log, the key tracker or anything that counts Daniel's playing: Claude's notes
// still arrive through cueNoteOn, and Daniel's own notes only feed his rest, the duck and the owner lease (jamHeard).
const jamRest = createRestDetector();  // 8.9: 1.2 s with none of his notes sounding, or 3 s with no note-on under the pedal
const jam = { position: null, state: null, deck: null, deckGhosts: null, tryGhosts: null, tryFound: false, errors: 0,
              lastError: null, record: null };
const jamGhosts = { target: new Set(), incoming: new Set(), hold: new Set(), slow: new Set(), foundAt: -Infinity, foundPerf: null };
function jamWarn(what, e) {
  jam.errors++;
  jam.lastError = `${what}: ${errText(e)}`;
  console.warn("[piano] Claude's band:", jam.lastError);
}
// The chip names the chord sounding now (jam-spec 8.4). A bar's cue carries its chord names from its first strike, and
// that strike can be a pickup a beat before the bar, which showed the next chord's name for a beat while the old one
// rang (round-2 verify: 833 ms per change at 72 bpm). For a cue of the run the transport positions, the name comes from
// the position's slot instead, so the old chord keeps its name up to its bar line. One info object per name (the
// overlay redraws on identity); the count-in or a rest names nothing.
const jamChip = { key: "", info: null };
function jamChipCaption(info) {
  if (!info || typeof info.cue_id !== "string" || !info.cue_id.startsWith("jam:")) return info;
  const p = jam.position;
  const run = info.cue_id.split(":")[1];
  if (!p || p.run !== run) return info;
  const c = p.chord;
  if (!c || (!c.name && !c.n)) return null;
  const label = c.name || c.n;
  const detail = c.n ? `${c.n} in ${c.key || p.key}` : null;
  const key = `${run}|${label}|${detail}`;
  if (jamChip.key !== key) { jamChip.key = key; jamChip.info = { ...info, label, detail, under: null }; }
  return jamChip.info;
}
const transport = createTransport({
  player: cuePlayer, voice: cueVoice, api: createJamApi(), pageId: PAGE_ID,
  log: { timebase: () => (perfLog ? perfLog.timebase() : null) },  // the ack's clock pair meets the log (L1)
  isResting: () => jamRest.resting(),
  sounding: () => [...sounding.keys()],  // Daniel's notes, for Try's "found"
  duck: safeGet("arsenal.piano.jam.duck") !== "off",
  knock: safeGet("arsenal.piano.jam.knock") !== "off",
  onPosition: (p) => {
    const prev = jam.position;
    jam.position = p;
    if (p && Number.isInteger(p.beat_index) && (!prev || prev.beat_index !== p.beat_index || prev.bar !== p.bar)) {
      pool.beatAt = clock();
      pool.downbeat = p.beat_index === 0;
    }
    if (jam.deck) jam.deck.showPosition(p);
  },
  onGhosts: (g) => {
    const any = g && (g.target.length || g.incoming.length || g.hold.length);
    if (g && g.found && !jam.tryFound) {
      jamGhosts.foundAt = clock();
      jamGhosts.foundPerf = performance.now();
      if (jam.deck) jam.deck.flashFound();
    }
    jam.tryFound = !!(g && g.found);
    jam.tryGhosts = any ? g : null;
    syncGhosts();
  },
  onState: (s) => { jam.state = s; if (jam.deck) jam.deck.showState(s); cueUiDirty = true; },
  onError: (msg) => jamWarn("transport", msg),
});

// Daniel played a note (not the Demo): his rest, the duck and the owner lease; a strong note dims the floor pool.
function jamHeard(m, vel) {
  jamRest.noteOn(m);
  pool.strong = Math.max(pool.strong, clamp((vel - POOL.strongFrom) / POOL.strongSpan, 0, 1));
  try { transport.noteOn(); } catch (e) { jamWarn("noteOn", e); }
}

// The courtesy gate for a hover Claude sends (8.9): while Daniel plays it waits up to 8 s for his rest, then fades in
// anyway (over about 400 ms, GHOST_FADE.remote). A clear acts at once. Hovers made on this page (a Show, a chip, a receipt's
// local cue) are not Claude knocking, so they show at once; direct play cues keep their behaviour (no gate).
const HOVER_WAIT_SEC = 8;
const hoverGate = { cue: null, since: 0, remote: false, open: true };
function gateHover(info) {
  const cue = info ? info.cue_id : null;
  if (cue !== null && cue === hoverGate.cue) return;  // a hover progression's next step: already decided
  hoverGate.cue = cue;
  hoverGate.remote = Number.isInteger(cue);  // stream cues carry the server's integer id
  hoverGate.since = clock();
  hoverGate.open = !hoverGate.remote || jamRest.resting();
}
function tickHoverGate(t) {
  if (hoverGate.open || !cueView.hover) return;
  if (jamRest.resting() || t - hoverGate.since >= HOVER_WAIT_SEC) { hoverGate.open = true; syncGhosts(); }
}
// Is this caption the one of a hover still waiting at the gate (the chip waits with its ghosts)?
const captionGated = (info) => !!info && !hoverGate.open && info.cue_id === hoverGate.cue;

// Every ghost on the keys: the hover (past its gate), the deck's (a chip's hover or a Show) and Try's (the band's).
function syncGhosts() {
  const target = new Set(), incoming = new Set(), hold = new Set(), slow = new Set();
  if (cueView.hover && hoverGate.open) {
    for (const m of cueView.hover.notes) { target.add(m); if (hoverGate.remote) slow.add(m); }
  }
  for (const g of [jam.deckGhosts, jam.tryGhosts]) {
    if (!g) continue;
    for (const m of g.target || []) target.add(m);
    for (const m of g.incoming || []) incoming.add(m);
    for (const m of g.hold || []) hold.add(m);
  }
  jamGhosts.target = target;
  jamGhosts.incoming = incoming;
  jamGhosts.hold = hold;
  jamGhosts.slow = slow;
  const all = new Set([...target, ...incoming, ...hold]);
  cueView.ghost = all.size ? all : NO_GHOSTS;
}

// "Keep what I just played" (8.4, DATA 2.10): Daniel's sounding notes with the page's own reading of them.
function captureChord() {
  const info = currentInfo();
  const notes = [...sounding.keys()].filter((m) => m >= KEY.first && m <= KEY.last).sort((a, b) => a - b);
  if (!info || !notes.length) return null;
  return { notes, name: info.name, number: lastNns ? lastNns.text : null, key: keyView.key ? keyView.key.name : null,
           key_conf: keyView.key ? keyView.confidence : null, locked: keyView.locked, title: null, page_id: PAGE_ID,
           perf_ms: performance.now(), log: perfLog ? perfLog.timebase() : null };
}

// The deck's settings (8.8) that the page and the band carry out; the deck keeps its own (groove, backing, count-in).
function applyDeckSettings(s, name) {
  if (name === "view") {
    cueStage.view = CUE_VIEWS.includes(s.view) ? s.view : "auto";
    const sel = $("cue-view-select");
    if (sel) sel.value = cueStage.view;
  } else if (name === "volume") {
    cueVoice.setVolume(s.volume);
    const vol = $("cue-volume");
    if (vol) vol.value = String(cueVoice.volume);
  } else if (name === "duck") {
    transport.setDuck(!!s.duck);
  } else if (name === "knock") {
    transport.setKnock(!!s.knock);
  }
}

// boot(), after startCues(): the drawer inside the stage, outside the recorded canvas (8.1).
function startDeck() {
  try {
    jam.deck = createDeck({
      stage: $("stage"), api: "", transport, glass: jamGlass, cueClient: { status: () => cueView.status },
      keyView: () => ({ name: keyView.name }), isRecording: () => rec.state === "recording" || rec.arming,
      onOpenChange: () => fitCanvas(), onLayout: () => fitCanvas(),
      canvas, framing: () => framing, pad: () => (document.fullscreenElement ? 0 : 14), pageId: PAGE_ID,
      isResting: () => jamRest.resting(), minor: () => theoryUi.minor,
      onGhosts: (g) => { jam.deckGhosts = g && ((g.target && g.target.length) || (g.incoming && g.incoming.length)) ? g : null; syncGhosts(); },
      onSettings: applyDeckSettings, toast, unlock: () => cueVoice.unlock(),
      stopDemo: () => { if (!demo.running) return false; stopDemo(); return true; },
      capture: captureChord,
      // Hear me: Daniel's own logged notes, played here only (never broadcast), in his faded pitch colours
      playReplay: (cue) => { const id = `replay-${++cueLocalSeq}`; noteCue(cue, id); planCue(cue, id); return cuePlayer.handle(cue, { id }); },
      hush: hushClaude, voiceReady: () => cueVoice.status() === "ready",
    });
    const s = jam.deck.settings();
    transport.setDuck(!!s.duck);
    transport.setKnock(!!s.knock);
    if (!new URLSearchParams(location.search).get("jam") && CUE_VIEWS.includes(s.view) && safeGet(CUE_PREF.view) !== "stage") cueStage.view = s.view;
  } catch (e) {
    jamWarn("deck", e);
    toast(`The cards could not start: ${errText(e)}`, true);
  }
  fitCanvas();
}

// The Studio (piano/studio/studio.js): a second right-edge drawer inside the stage, outside the recorded canvas, with two
// tabs. Practice plays the exercise library (piano/practice) through Claude's voice as local cues ("exercise:" ids), so its
// notes reach the keys, the ghosts and the chip but never `sounding`, the practice log, the key tracker, the chord reader,
// the Nashville row, the staff, the schemes or a recording (cueNoteOn). Looks saves and applies the page's visual settings
// through piano/looks/registry.js and the server's /api/piano/looks. The Studio and the deck close each other (the Studio
// closes the deck when it opens and watches #deck's data-open, as conversation-dock.js does); fitCanvas subtracts whichever
// is docked. Its modules load with import() after the deck, so a Studio that fails to load never stops the page: the page
// plays on without it and says so.
let studio = null;
async function startStudio() {
  try {
    const [studioMod, library, playerMod, registry, storeMod] = await Promise.all([
      import("./piano/studio/studio.js"), import("./piano/practice/library.js"), import("./piano/practice/player.js"),
      import("./piano/looks/registry.js"), import("./piano/looks/store.js"),
    ]);
    // What the Studio reads and sets is window.__piano (the registry's page: looks(), stats(), spectacle, the select and set
    // functions); the few hooks below are the Studio's own and stay off window.__piano.
    const page = Object.assign(Object.create(window.__piano), {
      canvas, toast,
      framing: () => framing,
      pad: () => (document.fullscreenElement ? 0 : 14),
      minor: () => theoryUi.minor,
      // REC, as the page's own guards read it (applyFraming, selectScheme): recording, stopping or saving, or about to start.
      // The Studio holds its dock width through all of it and keeps the settings a take can't change locked.
      isRecording: () => rec.state !== "idle" || rec.arming,
      // An exercise starting while Claude's band sounds a run: the band stops first, as Esc or the deck's Stop stop it, so
      // the two never play through one player at once. A run that isn't sounding (a knock waiting for his rest) is left.
      beforeExerciseStart: () => {
        try {
          if (!transport.stats().runs.some((r) => r.live || r.handed > 0)) return;
          Promise.resolve(transport.stop("now")).catch((e) => jamWarn("stop", e));
        } catch (e) { jamWarn("stop", e); }
      },
    });
    studio = studioMod.mountStudio({
      stage: $("stage"), page, keys: false,  // the page's keydown handler calls studio.handleKey (wireUi)
      practice: { library: { FAMILIES: library.FAMILIES, EXERCISES: library.EXERCISES }, createPlayer: (o) => playerMod.createExercisePlayer(o) },
      looks: { registry, store: storeMod.createLooksStore() },
      onLayout: () => fitCanvas(),
    });
  } catch (e) {
    studio = null;
    console.error("[piano] Studio unavailable:", e);
    toast(`The Studio could not start: ${errText(e)}`, true);
  }
  fitCanvas();
}
// The last cue, for the status readout, the HUD, stats and the REC toast. lastLabel keeps the last cue that had a label, so
// a clear does not blank it.
function noteCue(cue, id) {
  cueView.last = { type: cue.type, label: cue.label || null, id, at: clock() };
  if (cue.label) cueView.lastLabel = cue.label;
  cueUiDirty = true;
}

// ---------------------------------------------------- theory without frames --
// The key tracker and the chord log used to run only inside renderFrame. A hidden, minimized or covered tab gets no
// requestAnimationFrame at all, while Web MIDI still delivers every note, so whatever Daniel played with the page out
// of sight reached the practice log as notes, pedal and sound endings with no chord events, and the key tracker never
// heard it (seen 2026-09-14: whole stretches of a real session, before and after long pauses, with no chord events;
// replayed headless on a virtual clock the same notes log chords throughout with frames and leave exactly that gap
// without them). So while no frame is being drawn, each change to what sounds first brings the theory up to its own
// moment, as frames would have: the changes within one frame's span (FRAME_SEC) are read together at the time that
// frame would have come, and the time since the last read is ticked through the key tracker every KEY_TICK. A short
// timer reads the last change of a phrase; in a background tab it may wake late, but every read carries its own time.
// The first frame after such a stretch catches up the same way before it draws.
const FRAME_SEC = 1 / 60;
const FRAMES_STALL = 0.25;     // no frame drawn for this long (or the tab is hidden): the page is not drawing
const CATCH_UP_TICKS = 3000;   // key ticks one catch-up runs at most (5 min); the tracker counts only ACTIVE_SEC past a note
let frameAt = -Infinity;       // clock() of the last drawn frame
let pendingAt = null;          // clock() of the first change nothing has read yet, while no frame is drawn
let settleTimer = 0;
const drawing = (t) => document.visibilityState === "visible" && t - frameAt < FRAMES_STALL;
function catchUp(until) {
  if (pendingAt !== null) {
    const at = Math.min(until, pendingAt + FRAME_SEC);
    pendingAt = null;
    tickKey(at);
    currentInfo(at);
  }
  if (!Number.isFinite(keyView.at)) return;  // nothing has been heard yet
  for (let s = Math.max(keyView.at, until - CATCH_UP_TICKS * KEY_TICK) + KEY_TICK; s < until; s += KEY_TICK) {
    tickKey(s, true);
    currentInfo(s);  // a key change respells and renumbers what sounds, as the next frame would
  }
}
// Every change to what sounds calls beforeChange(t) before it changes anything and afterChange(t) once it has.
function beforeChange(t) {
  if (drawing(t) || (pendingAt !== null && t < pendingAt + FRAME_SEC)) return;
  catchUp(t);
}
function afterChange(t) {
  if (drawing(t)) return;
  if (pendingAt === null) pendingAt = t;
  if (!settleTimer) settleTimer = setTimeout(settle, 50);
}
function settle() {
  settleTimer = 0;
  const t = clock();
  if (pendingAt !== null && !drawing(t)) catchUp(t);
}
// A change made while frames were still drawing waits for the next frame. If the tab hides before that frame comes
// (a last chord, then straight to another window), nothing would read it until the next MIDI event, perhaps after
// log.js's idle close, so hiding hands it to the settle timer.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" || !detectDirty) return;
  if (pendingAt === null) pendingAt = clock();
  if (!settleTimer) settleTimer = setTimeout(settle, 50);
});

// ------------------------------------------------------------------- MIDI --
const ALL_INPUTS = "__all__";
const midi = { access: null, inputs: [], bound: [], status: "not connected", last: "", events: 0, echoes: 0 };
const midiPrefKey = "arsenal.piano.midiInput";  // stored by port name: ids can change between sessions
// "KeyLab 88 mk3 MIDI" carries keys, pedal and controls; its "DAW" port carries DAW-control traffic.
// Daniel's KeyLab: its keys-and-pedal port, not the DAW port. A hardware keyboard cannot bring Claude's notes back, so it
// never takes the echo guard, whatever a stored MIDI out says.
function isKeyLabKeys(name) { return /keylab/i.test(name || "") && !/daw/i.test(name || ""); }
// A port Claude may not play into: the KeyLab, the MIDI in Daniel chose by name, or (with no choice stored) the one input
// the page picked for him. As Claude's out, the echo guard would stop the page listening to it. A loopMIDI port that is
// not his input stays allowed: that loop is what the guard is for.
function isDanielsKeyboard(name) {
  if (!name) return false;
  if (isKeyLabKeys(name)) return true;
  const chosen = safeGet(midiPrefKey);
  if (chosen && chosen !== ALL_INPUTS) return chosen === name;
  return !chosen && midi.bound.length === 1 && midi.bound[0].name === name;
}
// Claude's MIDI out ranks -2: a loopMIDI port has the same name on its input side, and bound as an input it would bring
// Claude's notes back as Daniel's playing, into the log. It is never bound, and its messages are ignored (onMidiMessage).
function midiRank(input) {
  const name = input.name || "";
  if (cueMidiOutName && name === cueMidiOutName) return -2;  // never the KeyLab (see cueMidiOutName and the Out menu)
  if (/daw/i.test(name)) return -1;
  if (/keylab/i.test(name) && /midi/i.test(name)) return 3;
  if (/keylab/i.test(name)) return 2;
  return 1;
}
async function connectMIDI() {
  if (!navigator.requestMIDIAccess) { setMidiStatus("Web MIDI is unavailable in this browser"); return; }
  try {
    midi.access = await navigator.requestMIDIAccess({ sysex: false });
    midi.access.onstatechange = () => refreshMidiInputs();
    refreshMidiInputs();
    $("btn-midi").textContent = "Rescan";
  } catch (e) {
    setMidiStatus("MIDI blocked: " + errText(e));
  }
}
function refreshMidiInputs() {
  if (!midi.access) return;
  const inputs = [...midi.access.inputs.values()];
  midi.inputs = inputs;
  const select = $("midi-select");
  select.textContent = "";
  const add = (value, text) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = text;
    select.append(opt);
  };
  if (!inputs.length) add("", "no MIDI inputs found");
  for (const input of inputs) {
    const rank = midiRank(input);
    add(input.id, (input.name || input.id) + (rank === -2 ? "  (Claude's MIDI out)" : rank < 0 ? "  (DAW control)" : "") +
                  (input.state === "disconnected" ? "  (disconnected)" : ""));
  }
  if (inputs.length > 1) add(ALL_INPUTS, "all inputs except DAW ports");

  const saved = safeGet(midiPrefKey);
  let choice = "";
  if (saved === ALL_INPUTS && inputs.length > 1) choice = ALL_INPUTS;
  else if (saved && inputs.some((i) => i.name === saved)) choice = inputs.find((i) => i.name === saved).id;
  else {
    const best = [...inputs].filter((i) => midiRank(i) > 0).sort((a, b) => midiRank(b) - midiRank(a))[0];
    choice = best ? best.id : "";
  }
  select.value = choice;
  bindMidi(choice, false);
}
function bindMidi(choice, remember) {
  const before = midi.bound.map((i) => i.id).join(",");
  for (const input of midi.inputs) input.onmidimessage = null;
  const picked = choice === ALL_INPUTS ? midi.inputs.filter((i) => midiRank(i) > 0)
                                       : midi.inputs.filter((i) => i.id === choice);
  midi.bound = picked.filter((i) => midiRank(i) !== -2);
  if (midi.bound.length < picked.length) {
    toast(`Not listening to "${cueMidiOutName}": it is Claude's MIDI out, so Claude's notes would come back as yours. ` +
          "Pick another MIDI in, or another MIDI out for Claude.", true);
  }
  for (const input of midi.bound) input.onmidimessage = onMidiMessage;
  if (midi.bound.map((i) => i.id).join(",") !== before) allNotesOff();  // no stuck notes across a switch
  if (remember) safeSet(midiPrefKey, choice === ALL_INPUTS ? ALL_INPUTS : (picked[0] && picked[0].name) || "");
  setMidiStatus(midi.bound.length ? midi.bound.map((i) => i.name).join(" + ") : midi.inputs.length ? "no input selected" : "no inputs");
}
function setMidiStatus(text) { midi.status = text; }
function onMidiMessage(ev) {
  const d = ev.data;
  if (!d || d.length < 2) return;
  const port = ev.currentTarget || ev.target;
  if (port && cueMidiOutName && port.name === cueMidiOutName) { midi.echoes++; return; }  // Claude's own notes, back
  const type = d[0] & 0xf0;
  if (type === 0x90 && d.length >= 3) {
    if (d[2] > 0) noteOn(d[1], d[2]); else noteOff(d[1]);
  } else if (type === 0x80 && d.length >= 3) {
    noteOff(d[1]);
  } else if (type === 0xb0 && d.length >= 3) {
    if (d[1] === 64) setSustain(d[2] >= 64, d[2]);
    else if (d[1] === 120 || d[1] === 123) { allNotesOff(); hushClaude(); }  // a panic silences both hands
  } else {
    return;  // clock, aftertouch, pitch bend: not drawn
  }
  midi.events++;
  midi.last = [...d].map((b) => b.toString(16).padStart(2, "0")).join(" ");
}

// --------------------------------------------------------- computer keys --
// Tracker layout by physical key (event.code), so it works on any keyboard language:
// lower rows Z-/ with S D G J L ; play C3-E4; upper rows Q-P with the number row play C4-E5.
// H is the HUD and F is fullscreen, so G#3 (the H key in this layout) lives only in the upper row.
const KEYMAP = {
  KeyZ: 0, KeyS: 1, KeyX: 2, KeyD: 3, KeyC: 4, KeyV: 5, KeyG: 6, KeyB: 7, KeyN: 9, KeyJ: 10, KeyM: 11,
  Comma: 12, KeyL: 13, Period: 14, Semicolon: 15, Slash: 16,
  KeyQ: 12, Digit2: 13, KeyW: 14, Digit3: 15, KeyE: 16, KeyR: 17, Digit5: 18, KeyT: 19, Digit6: 20, KeyY: 21,
  Digit7: 22, KeyU: 23, KeyI: 24, Digit9: 25, KeyO: 26, Digit0: 27, KeyP: 28,
};
let kbOctave = 0;
const kbDown = new Map();  // event.code -> midi
function releaseComputerKeys() {
  for (const m of kbDown.values()) noteOff(m);
  kbDown.clear();
}

// ------------------------------------------------------------------- demo --
// Royal-road colours in C: Fmaj9 G9 Em7 Am9 Dm9 G13 Cmaj9 Cmaj7/E, rolled, with pedal changes.
function buildDemo() {
  const beat = 60 / 84;
  const bars = [
    { bass: [41, 48], rh: [57, 60, 64, 67], top: [72, 76] },
    { bass: [43, 50], rh: [59, 62, 65, 69], top: [74, 77] },
    { bass: [40, 47], rh: [55, 59, 62, 67], top: [71, 74] },
    { bass: [45, 52], rh: [55, 60, 64, 71], top: [72, 76] },
    { bass: [38, 45], rh: [53, 57, 60, 64], top: [69, 72] },
    { bass: [43, 50], rh: [53, 59, 64], top: [71, 76] },
    { bass: [48, 55], rh: [64, 67, 71, 74], top: [76, 79] },
    { bass: [40], rh: [59, 60, 64, 67], top: [72, 76, 79], beats: 4 },
  ];
  const ev = [];
  let at = 0;
  for (const bar of bars) {
    const len = (bar.beats || 2) * beat;
    ev.push([at - 0.04, "pedal", false]);
    bar.bass.forEach((m, i) => { ev.push([at + i * 0.012, "on", m, 74 - i * 8]); ev.push([at + beat * 1.2, "off", m]); });
    ev.push([at + 0.09, "pedal", true]);
    bar.rh.forEach((m, i) => { ev.push([at + 0.06 + i * 0.05, "on", m, 56 + i * 7]); ev.push([at + beat * 1.1, "off", m]); });
    bar.top.forEach((m, i) => {
      const on = at + beat * (1 + i * 0.5);
      ev.push([on, "on", m, 88 - i * 9]);
      ev.push([Math.min(on + beat * 0.5, at + len) - 0.07, "off", m]);
    });
    at += len;
  }
  ev.push([at + 0.4, "pedal", false]);
  ev.push([at + 0.5, "end"]);
  return ev.sort((a, b) => a[0] - b[0]);
}
const demo = { events: [], i: 0, t0: 0, running: false };
function startDemo() {
  allNotesOff();
  demo.events = buildDemo();
  demo.i = 0;
  demo.t0 = clock() + 0.2;
  demo.running = true;
  syncDemoButton();
}
function stopDemo() {
  demo.running = false;
  logMuted = true;  // the notes it ends were the demo's
  try { allNotesOff(); } finally { logMuted = false; }
  syncDemoButton();
}
function tickDemo(t) {
  if (!demo.running) return;
  while (demo.i < demo.events.length && demo.t0 + demo.events[demo.i][0] <= t) {
    const [, type, a, b] = demo.events[demo.i++];
    if (type === "on") noteOn(a, b);
    else if (type === "off") noteOff(a);
    else if (type === "pedal") setSustain(a);
  }
  if (demo.i >= demo.events.length) { demo.running = false; syncDemoButton(); }
}

// ------------------------------------------------------------ audio input --
// The chosen input is analysed for the meter and mixed into recordings. It is never connected to
// an AudioContext destination or any element: the Focusrite Loopback already carries the speaker
// mix, so playing it back would feed back.
const audioIn = { stream: null, ctx: null, analyser: null, source: null, data: null, level: 0, label: "", unlocked: false };
const audioPrefKey = "arsenal.piano.audioInput";
async function listAudioInputs() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
  const inputs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
  audioIn.unlocked = inputs.some((d) => d.label);
  const select = $("audio-select");
  const current = select.value;
  select.textContent = "";
  const add = (value, text) => { const o = document.createElement("option"); o.value = value; o.textContent = text; select.append(o); };
  add("", "none");
  inputs.forEach((d, i) => {
    if (d.deviceId === "default" || d.deviceId === "communications") return;
    add(d.deviceId, (d.label || `input ${i + 1} (click to allow names)`) + (/loopback/i.test(d.label) ? "  (computer audio)" : ""));
  });
  const remembered = safeGet(audioPrefKey);
  const byLabel = remembered ? inputs.find((d) => d.label === remembered) : null;
  const keep = [...select.options].some((o) => o.value === current) ? current : (byLabel ? byLabel.deviceId : "");
  select.value = keep;
  if (keep && keep !== current && !audioIn.stream) useAudioInput(keep);
}
async function unlockAudioLabels() {
  if (audioIn.unlocked || !navigator.mediaDevices) return;
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    for (const t of s.getTracks()) t.stop();
  } catch (e) {
    toast("Audio input permission: " + errText(e), true);
  }
  await listAudioInputs();
}
async function useAudioInput(deviceId) {
  if (audioIn.source) { audioIn.source.disconnect(); audioIn.source = null; }
  if (audioIn.stream) { for (const t of audioIn.stream.getTracks()) t.stop(); audioIn.stream = null; }
  audioIn.label = "";
  if (!deviceId) return;
  try {
    audioIn.stream = await navigator.mediaDevices.getUserMedia({ video: false, audio: {
      deviceId: { exact: deviceId }, echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: { ideal: 2 } } });
    audioIn.label = (audioIn.stream.getAudioTracks()[0] || {}).label || "input";
    audioIn.ctx = audioIn.ctx || new AudioContext();
    if (!audioIn.analyser) {
      audioIn.analyser = audioIn.ctx.createAnalyser();
      audioIn.analyser.fftSize = 1024;
      audioIn.data = new Float32Array(audioIn.analyser.fftSize);
    }
    audioIn.source = audioIn.ctx.createMediaStreamSource(audioIn.stream);
    audioIn.source.connect(audioIn.analyser);  // analysis only; the analyser has no outgoing connection
    audioIn.ctx.resume().catch(() => {});
  } catch (e) {
    audioIn.stream = null;
    $("audio-select").value = "";
    toast("Audio input failed: " + errText(e), true);
  }
}
function tickMeter(dt) {
  let rms = 0;
  if (audioIn.stream && audioIn.analyser) {
    audioIn.analyser.getFloatTimeDomainData(audioIn.data);
    let sum = 0;
    for (let i = 0; i < audioIn.data.length; i++) sum += audioIn.data[i] * audioIn.data[i];
    rms = Math.sqrt(sum / audioIn.data.length);
  }
  const db = 20 * Math.log10(rms + 1e-9);
  const target = clamp((db + 60) / 60, 0, 1);
  audioIn.level = target > audioIn.level ? target : damp(audioIn.level, target, 0.25, dt);
  $("audio-meter").style.width = `${(audioIn.level * 100).toFixed(1)}%`;
}

// -------------------------------------------------------------- recording --
const rec = { recorder: null, chunks: [], mime: "", startedAt: 0, state: "idle", withAudio: false, error: "",
              arming: false, tracks: null };
let lastUpload = null;
function pickMime(withAudio) {
  const a = withAudio ? ",mp4a.40.2" : "";
  // Level 4.2 can encode 1080p60, but Chrome can silently omit the video track at 4K.
  // Select the level for the canvas's actual macroblocks per second, including portrait.
  const blocksPerSecond = Math.ceil(canvas.width / 16) * Math.ceil(canvas.height / 16) * 60;
  const profiles = blocksPerSecond > 983040 ? ["avc1.640034"]
    : blocksPerSecond > 522240 ? ["avc1.640033", "avc1.640034"]
    : ["avc1.64002a", "avc1.640033", "avc1.4d002a", "avc1"];
  const mp4 = profiles.map((c) => `video/mp4;codecs=${c}${a}`);
  const webm = withAudio ? ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"]
                         : ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
  // This Chromium/AMD path downgrades requested H.264 5.2 to 5.1 and stalls at 4K60.
  // VP9 avoids that negotiation; lower resolutions retain the existing MP4 preference.
  const choices = blocksPerSecond > 983040 ? [...webm, ...mp4] : [...mp4, ...webm];
  return choices.find((m) => MediaRecorder.isTypeSupported(m)) || "";
}
async function startRecording() {
  if (rec.state !== "idle") return;
  if (typeof MediaRecorder === "undefined") { toast("MediaRecorder is unavailable in this browser", true); return; }
  rec.error = "";
  // Jam view: in "auto" Claude's keys, ghosts and chip leave the canvas before the recorder can see a frame (one clean
  // frame is drawn now; see cueOnStage and tickCueStage), and Claude stops steering the camera. Claude's voice is never
  // added to this stream in any view: it has its own AudioContext, and the stream below is the canvas plus the chosen input.
  // (tickCueStage, in that frame, also drops Claude's camera hints.)
  rec.arming = true;
  try {
    showKey(clock());  // the jam key (8.10) is off the canvas from this frame on: the take numbers Daniel's chords in his own key
    try { renderFrame(); } catch { /* the render loop reports frame errors */ }
    // Frames are requested by the render loop at a paced 60 fps: captureStream(60) on a 144/240 Hz
    // display gave uneven, roughly 30 fps files.
    const stream = canvas.captureStream(0);
    rec.videoTrack = stream.getVideoTracks()[0];
    rec.frameAcc = 1 / 60;
    rec.frames = 0;
    const track = audioIn.stream && audioIn.stream.getAudioTracks()[0];
    if (track && track.readyState === "live") stream.addTrack(track.clone());  // the clone stops with the recording
    // 8.11 item 8: the take is the canvas and the chosen input, never Claude. Claude's voice plays through its own
    // AudioContext and makes no MediaStream, so every track here must be the canvas's or a clone of the input's; anything
    // else refuses the take. rec.sources is what __piano.jam.stats().recorderSources reports.
    const inputLabels = new Set(audioIn.stream ? audioIn.stream.getAudioTracks().map((tr) => tr.label) : []);
    rec.sources = stream.getTracks().map((tr) => (tr.kind === "video" ? "canvas" : inputLabels.has(tr.label) ? "input" : "unknown"));
    if (rec.sources.includes("unknown")) {
      for (const tr of stream.getTracks()) tr.stop();
      toast("REC refused: the recording would have taken a sound that is not your input", true);
      return;
    }
    rec.withAudio = stream.getAudioTracks().length > 0;
    rec.mime = pickMime(rec.withAudio);
    try {
      rec.recorder = new MediaRecorder(stream, { mimeType: rec.mime,
        videoBitsPerSecond: Math.round(16_000_000 * canvas.width * canvas.height / (1920 * 1080)),
                                                 ...(rec.withAudio ? { audioBitsPerSecond: 256_000 } : {}) });
    } catch (e) {
      for (const t of stream.getTracks()) t.stop();
      toast("Recorder failed to start: " + errText(e), true);
      return;
    }
    rec.chunks = [];
    rec.recorder.ondataavailable = (e) => { if (e.data && e.data.size) rec.chunks.push(e.data); };
    rec.recorder.onerror = (e) => { rec.error = errText(e.error || e); };
    rec.recorder.onstop = () => finishRecording(stream);
    rec.recorder.start(1000);
    rec.startedAt = performance.now();
    rec.state = "recording";
    rec.tracks = stream.getTracks().map((tr) => ({ kind: tr.kind, label: tr.label }));
    lastUpload = null;
    syncRecButton();
  } finally {
    rec.arming = false;  // however it ends (captureStream or the recorder can throw), Claude is not kept off the canvas
  }
  // Say so only when Claude is doing something on the page or sent a cue in the last minute, not on every take.
  const claudeBusy = cueSounding.size > 0 || cueView.ghost.size > 0 || overlay.cueAlpha > 0.004 || (cueView.last && clock() - cueView.last.at < 60);
  if (rec.state === "recording" && cueStage.view === "auto" && claudeBusy) toast("Recording you only. Claude's keys stay on the glass.");
}
function stopRecording() {
  if (rec.state !== "recording") return;
  rec.state = "stopping";
  syncRecButton();
  rec.recorder.stop();
}
async function finishRecording(stream) {
  for (const t of stream.getTracks()) t.stop();
  const seconds = (performance.now() - rec.startedAt) / 1000;
  const type = rec.recorder.mimeType || rec.mime || "video/webm";
  const blob = new Blob(rec.chunks, { type });
  rec.chunks = [];
  rec.state = "uploading";
  syncRecButton();
  try {
    const res = await fetch("/api/recordings?name=piano", { method: "POST", headers: { "Content-Type": blob.type }, body: blob });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* not JSON */ }
    if (!res.ok || !json || !json.path) throw new Error(`HTTP ${res.status} ${(json && json.error) || text.slice(0, 160)}`);
    lastUpload = { ok: true, status: res.status, json, mime: blob.type, blobBytes: blob.size, seconds: +seconds.toFixed(2),
                   withAudio: rec.withAudio, framesRequested: rec.frames };
    toast(`Saved ${(json.bytes / 1048576).toFixed(1)} MB: ${json.path}`);
  } catch (e) {
    const ext = /mp4/.test(blob.type) ? "mp4" : "webm";
    const name = `piano-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.${ext}`;
    lastUpload = { ok: false, error: errText(e), mime: blob.type, blobBytes: blob.size, seconds: +seconds.toFixed(2) };
    toast(`Upload failed (${errText(e)}).`, true, { href: URL.createObjectURL(blob), name, text: `Download ${name}` });
  }
  rec.state = "idle";
  syncRecButton();
}

// --------------------------------------------------------------------- UI --
function syncDemoButton() {
  const b = $("btn-demo");
  b.setAttribute("aria-pressed", String(demo.running));
  b.textContent = demo.running ? "Stop demo" : "Demo";
}
function syncRecButton() {
  const b = $("btn-rec");
  b.setAttribute("aria-pressed", String(rec.state === "recording"));
  b.dataset.busy = String(rec.state === "stopping" || rec.state === "uploading");
  if (rec.state !== "recording") $("rec-label").textContent = rec.state === "idle" ? "REC" : rec.state === "stopping" ? "…" : "Saving";
}
function hideIdleHint() { $("idle-hint").classList.add("gone"); }
let toastTimer = 0;
function toast(message, isError = false, link = null) {
  const el = $("toast");
  el.textContent = message;
  el.classList.toggle("error", !!isError);
  if (link) {
    const a = document.createElement("a");
    a.href = link.href;
    a.download = link.name;
    a.textContent = link.text;
    el.append(" ", a);
  }
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, link ? 120000 : 8000);
}
function hideToast(message) {  // only while that message is the one showing
  const el = $("toast");
  if (el.hidden || el.textContent !== message) return;
  clearTimeout(toastTimer);
  el.hidden = true;
}
// The canvas fits the stage, less the right drawer that is docked: the deck or the Studio, each 380 px (8.11 item 7; each
// keeps its dock width frozen while REC runs, so a take never reflows). The two close each other, so at most one is open;
// while REC runs one that was just closed may still hold its frozen width, so the wider of the two is taken, never the sum
// (deck.css and studio.css pad the stage by one drawer's width either way). layout() and dockWidth() may themselves call
// back here (onLayout): the guard makes that a no-op, since this call already reads the new width.
let fitting = false;
function fitCanvas() {
  if (fitting) return;
  fitting = true;
  try {
    const dock = Math.max(jam.deck ? jam.deck.layout().dockWidth : 0, studio ? studio.dockWidth() : 0);
    const r = $("stage").getBoundingClientRect();
    const pad = document.fullscreenElement ? 0 : 14;
    const scale = Math.max(0.05, Math.min((r.width - dock - 2 * pad) / framing.w, (r.height - 2 * pad) / framing.h));
    const cssW = Math.floor(framing.w * scale), cssH = Math.floor(framing.h * scale);
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    if (jamGlass) {  // the glass takes the canvas's exact CSS box, at the screen's pixel density
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      // sub-pixel placement: offsetLeft/offsetTop are whole pixels, and a centred canvas often sits at x.5
      const cr = canvas.getBoundingClientRect(), stage = $("stage");
      jamGlass.resize({ left: cr.left - r.left - stage.clientLeft, top: cr.top - r.top - stage.clientTop, width: cssW, height: cssH }, dpr);
      glassBox.width = cssW;
      glassBox.height = cssH;
      glassBox.had = true;  // the next frame draws the glass again (or clears it: a resize to the same size keeps its pixels)
    }
  } finally {
    fitting = false;
  }
}
// true once the framing is applied; false when REC refuses it (the buttons ignore the answer, the Studio's Looks read it)
function applyFraming(id, persist = true) {
  if (rec.state !== "idle" && FRAMINGS[id] !== framing) { toast("Stop recording before changing the framing", true); return false; }
  const was = framing;
  framing = FRAMINGS[id] || FRAMINGS["9:16"];
  // a new framing starts from its own closest view: with nothing sounding the camera keeps the span it has
  // (easeCamera), so 16:9's whole keyboard would otherwise stay on a 9:16 page until notes are played
  if (framing !== was) cam.span = camDan.span = framing.minSpan;
  if (persist) safeSet("arsenal.piano.framing", framing.id);
  renderer.setSize(Math.round(framing.w * renderScale), Math.round(framing.h * renderScale), false);
  composer.setSize(Math.round(framing.w * renderScale), Math.round(framing.h * renderScale));
  camera.fov = framing.fov;
  camera.aspect = framing.w / framing.h;
  overlay.build();
  resizeLooks();  // schemes and instruments (the KeyLab's phone profile follows 9:16)
  $("btn-916").setAttribute("aria-pressed", String(framing.id === "9:16"));
  $("btn-169").setAttribute("aria-pressed", String(framing.id === "16:9"));
  updateCamera(0, clock(), true);
  fitCanvas();
  return true;
}
function toggleHud() { $("hud").hidden = !$("hud").hidden; }
function setRenderQuality(scale) {
  if (rec.state !== "idle" || rec.arming) return;
  renderScale = scale;
  applyFraming(framing.id, false);
}
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else $("stage").requestFullscreen().catch((e) => toast("Fullscreen refused: " + errText(e), true));
}
const fmtNotes = (info) => (info ? info.notes.map((n) => n.name + n.octave).join(" ") : "none");
const fmtCount = (n) => Number(n || 0).toLocaleString("en-US");
function keySummary() {
  const raw = keyRaw && keyRaw.name !== keyView.name ? ` · raw ${keyRaw.name}` : "";
  const next = keyView.candidate ? ` · next ${keyView.candidate.name} ${keyView.candidate.heldSec.toFixed(1)} s` : "";
  if (!keyView.key) return `listening${raw}`;
  return `${keyView.key.name} · ${keyView.confidence} · ${keyView.locked ? "locked" : "auto"}${next}${raw}`;
}
// The top bar's log readout: short text, with the full story in its tooltip.
function logReadout() {
  if (!perfLog) {
    return logRoutes === null ? { state: "idle", text: "starting", title: "Asking the server for the practice-log routes." }
                              : { state: "off", text: "unavailable", title: "The practice log did not start (see the console)." };
  }
  const s = perfLog.status();
  const sent = s.sent ? ` · ${fmtCount(s.sent)} sent` : "";
  const why = s.lastError ? ` Last answer: ${s.lastError}.` : "";
  const kept = "so notes are kept in this browser and nothing is sent to it. Restart `py -m arsenal serve`, then reload " +
               "this page at the same address, and they upload.";
  const noRoutes = logRoutes === "reload"
    ? "The server has the practice-log routes now: reload this page (same address) to upload the notes kept in this browser."
    : `This server was started before the practice log existed (or with --no-performance-log), ${kept}`;
  switch (s.state) {
    case "live":
      return { state: s.state, text: `live${sent}`, title: `Recording to session ${s.session || "(opening)"}.` };
    case "buffering":
      if (logRoutes !== true) {
        return { state: s.state, text: `buffering ${fmtCount(s.buffered)} · ${logRoutes === "reload" ? "reload to upload" : "until the server restarts"}`,
                 title: noRoutes };
      }
      return { state: s.state, text: `buffering ${fmtCount(s.buffered)} · server unreachable, retrying`,
               title: "The server didn't take the last upload, so notes are kept in this browser and sent when it answers." + why };
    case "uploading":
      return { state: s.state, text: `uploading ${fmtCount(s.buffered)}${sent}`, title: "Sending notes kept in this browser." + why };
    case "off":
      return { state: s.state, text: s.buffered ? `off · ${fmtCount(s.buffered)} to upload` : "off",
               title: "Not recording. Notes already kept still upload." + why };
    default:
      if (logRoutes !== true) return { state: s.state, text: "idle · buffers until the server restarts", title: noRoutes };
      return { state: s.state, text: `idle${sent}`, title: "A session starts with the next note." + why };
  }
}
function syncLogButton() {
  const b = $("btn-log");
  const onNow = safeGet(LOG_PREF) !== "off";
  b.setAttribute("aria-pressed", String(onNow && !!perfLog));
  b.textContent = onNow ? "On" : "Off";
  b.disabled = !perfLog;
}
let logReadoutText = "";
function syncLogReadout() {
  const r = logReadout();
  if (r.text + r.title === logReadoutText) return;
  logReadoutText = r.text + r.title;
  const el = $("log-status");
  el.textContent = r.text;
  el.title = r.title;
  el.dataset.state = r.state;
}
// Claude's controls in the top bar. Voice: "Enable voice" (Chrome keeps sound off until the page is clicked; KeyLab MIDI
// is not a click), "Voice on", "Voice off", or "Other tab" (the one Daniel used last sounds, this one still draws).
const CUE_STATUS_TITLE = {
  off: "Not listening for Claude (arsenal.piano.cueListen is off).",
  connecting: "Opening the cue stream.",
  listening: "Listening for Claude's cues (py -m arsenal.pianocue play | hover | progression | replay | clear). Esc or Backspace hushes Claude.",
  reconnecting: "The server went away; reconnecting (cues from the last 10 s are replayed once).",
  paused: "Paused while the page is hidden in the back/forward cache or frozen.",
  closed: "The cue stream is closed.",
  "no routes": "This server predates Claude's cue routes: restart py -m arsenal serve, then reload.",
};
function syncCueUi() {
  cueUiDirty = false;
  const b = $("btn-cue-voice");
  if (!b) return;
  const s = cueVoice.status();
  if (s !== "needs a click") cueView.want = false;
  if (s !== "needs a click" || !cueVoice.enabled) hideToast(CUE_CLICK_TOAST);  // unlocked, or turned off: nothing to click for
  const text = s === "needs a click" && cueVoice.enabled ? "Enable voice" : !cueVoice.enabled ? "Voice off"
             : s === "another tab" ? "Other tab" : "Voice on";
  if (b.textContent !== text) b.textContent = text;
  b.setAttribute("aria-pressed", String(cueVoice.enabled && s !== "needs a click"));
  b.dataset.want = String(cueView.want);
  b.title = s === "needs a click" ? "Chrome keeps sound off until the page is clicked: click here, or anywhere on the page, to hear Claude."
          : s === "another tab" ? "Claude's voice is playing in another tab (the one you used last). Click to play it here; this tab still shows Claude's keys."
          : s === "unsupported" ? "Web Audio is unavailable in this browser."
          : `Claude's voice is ${cueVoice.enabled ? "on" : "off"}: click to turn it ${cueVoice.enabled ? "off" : "on"}.`;
  $("btn-cue-lift").setAttribute("aria-pressed", String(cueVoice.lowLift > 0));
  const st = $("cue-status");
  // Only the state word, in a fixed width (piano.css #cue-status), so nothing Claude sends can change the top bar's
  // layout; the last cue's label is in the tooltip and the HUD.
  if (st.textContent !== cueView.status) st.textContent = cueView.status;
  st.dataset.state = cueView.status === "no routes" ? "error" : cueView.status;
  const title = (CUE_STATUS_TITLE[cueView.status] || cueView.status) + (cueView.lastLabel ? `\nLast cue: ${cueView.lastLabel}` : "");
  if (st.title !== title) st.title = title;
}
function wireCueUi() {
  const voiceBtn = $("btn-cue-voice");
  if (!voiceBtn) return;
  voiceBtn.addEventListener("click", async () => {
    const was = cuePressStatus || cueVoice.status();  // the press itself may already have started the unlock
    cuePressStatus = null;
    if (was === "needs a click" && cueVoice.enabled) {
      await cueVoice.unlock();
    } else if (was === "another tab" && cueVoice.enabled) {
      // The press already made this the tab Daniel used last, which is the tab that sounds: take the voice, don't mute it.
      toast("Claude's voice plays in this tab from Claude's next cue");
    } else {
      const on = !cueVoice.enabled;
      cueVoice.setEnabled(on);
      safeSet(CUE_PREF.voice, on ? "on" : "off");
      if (on) await cueVoice.unlock();  // still inside the click, so the context may start
    }
    syncCueUi();
  });
  const vol = $("cue-volume");
  vol.value = String(cueVoice.volume);
  vol.addEventListener("input", () => { cueVoice.setVolume(Number(vol.value)); safeSet(CUE_PREF.volume, vol.value); });
  vol.addEventListener("change", () => vol.blur());  // hand the arrow keys back to the octave shift
  $("btn-cue-lift").addEventListener("click", () => {
    const on = !(cueVoice.lowLift > 0);
    cueVoice.setLowLift(on ? 1 : 0);
    safeSet(CUE_PREF.lowLift, on ? "on" : "off");
    syncCueUi();
  });
  // MIDI out: outputs are listed only when Daniel reaches for the menu, or at boot when MIDI is already granted and a
  // port is remembered, so the page never prompts for it on load. The port is remembered by name (ids change).
  const out = $("cue-midi-select");
  let listed = false, outPortId = "";
  const outNames = new Map();  // port id -> name
  async function listOutputs() {
    try {
      const outs = await cueVoice.listMidiOutputs();
      const keep = out.value;
      out.textContent = "";
      out.append(new Option("none", ""));
      outNames.clear();
      for (const o of outs) {
        outNames.set(o.id, o.name);
        const mine = isDanielsKeyboard(o.name);  // listed so Daniel sees why, but not pickable
        const opt = new Option(`${o.name}${mine ? " (your keyboard)" : ""}${o.state === "disconnected" ? " (disconnected)" : ""}`, o.id);
        opt.disabled = mine;
        out.append(opt);
      }
      const saved = safeGet(CUE_PREF.midiOut);
      const match = outs.find((o) => o.id === keep && !isDanielsKeyboard(o.name))
        || (!listed && saved && !isDanielsKeyboard(saved) && outs.find((o) => o.name === saved));
      out.value = match ? match.id : "";
      if (!listed && match) await cueVoice.setMidiOutput(match.id);
      outPortId = out.value;
      listed = true;
    } catch (e) {
      toast("Claude's MIDI outputs are unavailable: " + errText(e), true);
    }
    cueUiDirty = true;
  }
  out.addEventListener("pointerdown", () => { if (!listed) listOutputs(); });
  out.addEventListener("focus", () => { if (!listed) listOutputs(); });
  out.addEventListener("change", async () => {
    const name = outNames.get(out.value) || "";
    if (name && isDanielsKeyboard(name)) {  // a disabled option can still be set by script: refuse it, keep the last pick
      out.value = outPortId;
      toast(`"${name}" is your keyboard, so Claude can't play into it: the page would have to stop listening to it. ` +
            "Pick a loopMIDI port, or none.", true);
      out.blur();
      return;
    }
    try {
      const port = await cueVoice.setMidiOutput(out.value || null);
      cueMidiOutName = port ? port.name : "";
      outPortId = out.value;
      safeSet(CUE_PREF.midiOut, cueMidiOutName);
      refreshMidiInputs();  // re-rank: Claude's out is never bound as an input
    } catch (e) {
      toast("Claude's MIDI out failed: " + errText(e), true);
    }
    out.blur();
    cueUiDirty = true;
  });
  (async () => {
    try { if ((await navigator.permissions.query({ name: "midi" })).state === "granted" && safeGet(CUE_PREF.midiOut)) listOutputs(); }
    catch { /* not queryable */ }
  })();
  const view = $("cue-view-select");
  view.value = cueStage.view;
  view.addEventListener("change", () => {
    cueStage.view = CUE_VIEWS.includes(view.value) ? view.value : "auto";
    safeSet(CUE_PREF.view, cueStage.view);
    view.blur();
  });
  syncCueUi();
}
function syncKeySelect() {
  const select = $("key-select");
  if (!select) return;
  const auto = select.querySelector('option[value="auto"]');
  // while Claude's band plays: "jam: E♭" (a minor key "jam: Cm"), the section's key (8.10)
  const jamText = keyView.jam ? `jam: ${keyText(keyView.jam.replace(/ major$/, "").replace(/ minor$/, "m"))}` : null;
  const text = jamText || (!keyView.locked && keyView.key ? `auto · ${keyText(keyView.key.name)}` : "auto");
  if (auto && auto.textContent !== text) auto.textContent = text;
  if (select.value !== theoryUi.key) select.value = theoryUi.key;
}
function updateHud(t) {
  if ($("hud").hidden) return;
  const info = lastInfo;
  $("hud-fps").textContent = `${fpsValue.toFixed(0)} fps · ${frameMsP95.toFixed(1)} ms p95`;
  $("hud-render").textContent = `${canvas.width}x${canvas.height} (${framing.id}) · three r${THREE.REVISION}`;
  $("hud-midi").textContent = midi.status + (midi.last ? ` · ${midi.last}` : "");
  $("hud-notes").textContent = fmtNotes(info);
  $("hud-chord").textContent = (info ? info.name : "none") + (lastNns ? ` · ${formatNumber(lastNns).display}` : "")
    + (info && info.band ? ` · ${info.band}` : "") + (pianoReader ? "" : " · classic names");
  const staffSig = keySig.state(), settling = staffSig.waiting || staffSig.candidate;
  $("hud-key").textContent = keySummary() + ` · staff ${staffSig.key ? keyText(staffSig.key) : "no signature"}`
    + (settling ? ` (settling ${keyText(settling.key)})` : "");
  const routes = logRoutes === true ? "" : logRoutes === null ? " · asking" : logRoutes === "reload" ? " · routes now: reload" : " · no routes";
  if (perfLog) {
    const s = perfLog.status();
    $("hud-log").textContent = `${s.state}${routes} · ${s.session || "no session"} · sent ${fmtCount(s.sent)} · buffered ${fmtCount(s.buffered)}` +
                               (s.lastError && logRoutes === true ? ` · ${s.lastError}` : "");
  } else {
    $("hud-log").textContent = `unavailable${routes}`;
  }
  $("hud-pedal").textContent = sustain ? "down (CC64)" : "up";
  $("hud-trails").textContent = `${trails.liveCount(t)} live / cap ${TRAIL_MAX}`;
  $("hud-look").textContent = looksHudText(t);
  $("hud-octave").textContent = `computer keys C${3 + kbOctave}-E${5 + kbOctave}`;
  const recText = rec.state === "recording"
    ? `recording ${((performance.now() - rec.startedAt) / 1000).toFixed(1)} s · ${rec.recorder.mimeType || rec.mime}`
    : rec.state !== "idle" ? rec.state
    : lastUpload ? (lastUpload.ok ? `saved ${lastUpload.json.path}` : `upload failed: ${lastUpload.error}`) : "idle";
  $("hud-rec").textContent = recText + (audioIn.label ? ` · audio: ${audioIn.label}` : " · no audio");
  const cs = cueClient ? cueClient.stats() : null, ps = cuePlayer.state();
  const last = cueView.last ? ` · last ${cueView.last.type}${cueView.last.label ? ` ${cueView.last.label}` : ""} ${Math.round(t - cueView.last.at)} s ago` : "";
  $("hud-cue").textContent = `${cueView.status}${cs && cs.server ? ` · ${cs.server.listeners} listening` : ""} · voice ${cueVoice.status()}` +
    ` · view ${cueStage.view}${cueStage.on ? "" : " (off canvas)"} · ${ps.sounding.length} sounding` +
    (ps.hovering ? ` · hover ${ps.hovering.label || `${ps.hovering.notes.length} notes`}` : "") + last +
    (ps.lateness.n ? ` · ${ps.lateness.mean_ms} ms late avg` : "") + (cs && cs.stale ? ` · ${cs.stale} stale dropped` : "") +
    (midi.echoes ? ` · ${midi.echoes} echoes ignored` : "") + jamHudText();
}

// The Colour menu and the Studio's Looks set the colour mode here (window.__piano.setColourMode): stored, the keys that
// sound now recoloured, the menu kept in step. false for a mode the menu doesn't offer (nothing changes).
function setColourMode(mode) {
  if (!COLOUR_MODES.includes(mode)) return false;
  COLOUR.mode = mode;
  safeSet("arsenal.piano.colour", COLOUR.mode);
  for (const [m, st] of sounding) { const k = keys.get(m); if (k) noteColor(m, st.vel, k.color); }
  for (const st of cueSounding.values()) {  // Claude's moonlight level is set per colour mode too (moonColor)
    const k = keys.get(st.m);
    if (!k) continue;
    if (st.source === "replay") { replayColor(st.m, st.vel, k.cueColor); k.cueCss = k.cueColor.getStyle(); }
    else moonColor(st.vel, k.cueColor);
  }
  overlay.invalidate();
  const select = $("color-select");
  if (select && select.value !== COLOUR.mode) select.value = COLOUR.mode;
  return true;
}
// The Numbers menu and the Studio's Looks set the Nashville numbers mode here (window.__piano.setNumbersMode): stored, the
// menu kept in step. false for a mode the menu doesn't offer (nothing changes).
function setNumbersMode(mode) {
  if (!NNS_MODES.includes(mode)) return false;
  theoryUi.nns = mode;
  safeSet("arsenal.piano.nns", theoryUi.nns);
  const select = $("nns-select");
  if (select && select.value !== theoryUi.nns) select.value = theoryUi.nns;
  return true;
}

function wireUi() {
  for (const b of document.querySelectorAll(".btn")) b.addEventListener("click", () => b.blur());
  $("btn-midi").addEventListener("click", () => (midi.access ? refreshMidiInputs() : connectMIDI()));
  $("midi-select").addEventListener("change", (e) => bindMidi(e.target.value, true));
  $("btn-demo").addEventListener("click", () => (demo.running ? stopDemo() : startDemo()));
  $("btn-916").addEventListener("click", () => applyFraming("9:16"));
  $("btn-169").addEventListener("click", () => applyFraming("16:9"));
  $("color-select").value = COLOUR.mode;
  $("color-select").addEventListener("change", (e) => { setColourMode(e.target.value); });
  // Scheme and Instrument: stored, loaded with import(), error-isolated (the "looks" section); blur so the note keys keep working
  const schemeSelect = $("scheme-select"), instrumentSelect = $("instrument-select");
  schemeSelect.addEventListener("pointerdown", () => { probeLooks(); });
  schemeSelect.addEventListener("focus", () => { probeLooks(); });
  schemeSelect.addEventListener("change", () => { const id = schemeSelect.value; schemeSelect.blur(); selectScheme(id); });
  instrumentSelect.addEventListener("change", () => { const id = instrumentSelect.value; instrumentSelect.blur(); selectInstrument(id); });
  const audioSelect = $("audio-select");
  audioSelect.addEventListener("pointerdown", () => { unlockAudioLabels(); });
  audioSelect.addEventListener("change", () => {
    const opt = audioSelect.selectedOptions[0];
    safeSet(audioPrefKey, audioSelect.value && opt ? opt.textContent.replace(/\s+\(computer audio\)$/, "") : "");
    useAudioInput(audioSelect.value);
  });
  if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
    navigator.mediaDevices.addEventListener("devicechange", () => { listAudioInputs(); });
  }
  // Nashville numbers, minor numbering, key lock and the practice log; each choice is remembered
  const nnsSelect = $("nns-select"), minorSelect = $("minor-select"), keySelect = $("key-select");
  nnsSelect.value = theoryUi.nns;
  nnsSelect.addEventListener("change", () => {
    setNumbersMode(NNS_MODES.includes(nnsSelect.value) ? nnsSelect.value : "chord");
    nnsSelect.blur();  // hand the keyboard back to the computer-key piano
  });
  minorSelect.value = theoryUi.minor;
  minorSelect.addEventListener("change", () => {
    theoryUi.minor = minorSelect.value === "relative" ? "relative" : "tonic";
    safeSet("arsenal.piano.minor", theoryUi.minor);
    detectDirty = true;
    minorSelect.blur();
  });
  for (const mode of ["major", "minor"]) {
    const group = document.createElement("optgroup");
    group.label = mode;
    for (const name of KEY_NAMES.filter((k) => k.endsWith(mode))) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = `${keyText(name)} (lock)`;
      group.append(opt);
    }
    keySelect.append(group);
  }
  keySelect.addEventListener("change", () => { setKeyChoice(keySelect.value); keySelect.blur(); });
  setKeyChoice(theoryUi.key, false);
  $("btn-log").addEventListener("click", () => {
    const onNow = safeGet(LOG_PREF) === "off";
    safeSet(LOG_PREF, onNow ? "on" : "off");
    if (perfLog) perfLog.setEnabled(onNow);
    syncLogButton();
    syncLogReadout();
  });
  syncLogButton();
  syncLogReadout();

  $("btn-rec").addEventListener("click", () => (rec.state === "recording" ? stopRecording() : startRecording()));
  $("btn-full").addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", fitCanvas);
  new ResizeObserver(fitCanvas).observe($("stage"));

  const resumeAudio = () => { if (audioIn.ctx && audioIn.ctx.state === "suspended") audioIn.ctx.resume().catch(() => {}); };
  window.addEventListener("pointerdown", resumeAudio);
  // Daniel's hand on the page claims the jam's owner lease (the tab he uses sounds Claude's band; jam spec 5.2)
  window.addEventListener("pointerdown", () => { try { transport.input(); } catch (e) { jamWarn("input", e); } }, true);
  window.addEventListener("keydown", (e) => {
    resumeAudio();
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    try { transport.input(); } catch (err) { jamWarn("input", err); }
    const tag = e.target && e.target.tagName;
    // "hush, Claude" works from a focused top-bar menu or slider too: neither has a use for Esc or Backspace, and the key
    // is not taken from it (no preventDefault), so Esc still closes what it closes and leaves fullscreen
    if ((e.code === "Escape" || e.code === "Backspace") && (tag === "SELECT" || (tag === "INPUT" && e.target.type === "range"))) {
      if (!e.repeat) hushClaude();
      return;
    }
    // The deck's keys (8.7: A, the up and down arrows, Enter, K, \, ', - =, [ ], Esc and Backspace) come before the page's
    // own and KEYMAP. The deck skips form fields itself, except its own search box's Esc.
    if (jam.deck && jam.deck.handleKey(e)) return;
    // The Studio's keys (none is a letter; every letter is taken): ` toggles it, Page Up / Page Down the previous / next
    // exercise, Home play or pause, End stop, Insert / Delete the previous / next saved look. Like the deck's, they skip form
    // fields (the Studio's own search box keeps its Esc) and never run with Ctrl, Meta or Alt (the return above).
    if (studio && studio.handleKey(e)) return;
    if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;
    if (e.code === "KeyH") { e.preventDefault(); if (!e.repeat) toggleHud(); return; }
    if (e.code === "KeyF") { e.preventDefault(); if (!e.repeat) toggleFullscreen(); return; }
    if (e.code === "Space") { e.preventDefault(); if (!e.repeat) setSustain(true); return; }
    // "hush, Claude": pending cues, Claude's keys and sound, ghosts and chip; Daniel's notes are untouched
    if (e.code === "Escape" || e.code === "Backspace") { e.preventDefault(); if (!e.repeat) hushClaude(); return; }
    if (e.code === "ArrowLeft" || e.code === "ArrowRight") {
      e.preventDefault();
      releaseComputerKeys();
      kbOctave = clamp(kbOctave + (e.code === "ArrowLeft" ? -1 : 1), -3, 3);
      return;
    }
    const offset = KEYMAP[e.code];
    if (offset === undefined) return;
    e.preventDefault();
    if (e.repeat || kbDown.has(e.code)) return;
    const m = 48 + 12 * kbOctave + offset;
    kbDown.set(e.code, m);
    noteOn(m, 92);
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space") { setSustain(false); return; }
    const m = kbDown.get(e.code);
    if (m === undefined) return;
    kbDown.delete(e.code);
    if (![...kbDown.values()].includes(m)) noteOff(m);
  });
  window.addEventListener("blur", () => { releaseComputerKeys(); });
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); toast("The WebGL context was lost. Reload the page.", true); });
}

// ------------------------------------------------------------------- loop --
let lastT = clock();
let fpsValue = 0, fpsFrames = 0, fpsAt = clock(), hudAt = 0, frameMsP95 = 0, logUiAt = 0;
const frameTimes = [];
const glowMix = new THREE.Color();
const tmpColor = new THREE.Color();
function renderFrame() {
  const t = clock();
  const dt = clamp(t - lastT, 0, 0.1);
  lastT = t;
  if (pendingAt !== null || t - keyView.at > FRAMES_STALL) catchUp(t);  // the first frame after a stretch without frames
  frameAt = t;
  tickDemo(t);
  cuePlayer.pump();  // frame-aligned; the player's worker timer covers hidden windows
  transport.tick(t);  // Claude's band: bars handed on time (its worker timer covers hidden windows), the strip, the gate
  tickHoverGate(t);
  tickKey(t);
  const info = currentInfo(t);
  tickCueStage(dt);
  updateKeys(dt, t);
  updatePool(dt, t);
  updateCamera(dt, t);
  trailUniforms.uNow.value = t;
  sparkUniforms.uNow.value = t;
  trails.upload();
  if (sparksDirty) { for (const attr of Object.values(sparkAttr)) attr.needsUpdate = true; sparksDirty = false; }

  let count = 0;
  glowMix.setRGB(0, 0, 0);
  for (const [m, st] of sounding) {
    glowMix.add(noteColor(m, st.vel, tmpColor));
    count++;
    const k = keys.get(m);
    if (k) k.glowTarget = glowLevel(st, t);  // pedalled notes ring down slowly instead of switching off
  }
  for (const st of cueSounding.values()) {  // Claude's keys follow the strike envelope like held notes, with no pedal
    const k = keys.get(st.m);
    if (k) k.cueGlowTarget = cueGlowLevel(st, t);
  }
  trailUniforms.uPedal.value = damp(trailUniforms.uPedal.value, sustain ? 1 : 0, 0.06, dt);
  // record the pedal for the trail shader's pedalAt(): every sample slot since the last frame gets this level
  const pedalIdx = Math.floor(t * PEDAL_HZ);
  if (pedalIdx !== pedalHistAt) {
    const level = Math.round(clamp(trailUniforms.uPedal.value, 0, 1) * 255);
    for (let i = Math.max(pedalHistAt + 1, pedalIdx - PEDAL_LEN + 1); i <= pedalIdx; i++) {
      pedalHist.image.data[((i % PEDAL_LEN) + PEDAL_LEN) % PEDAL_LEN] = level;
    }
    pedalHistAt = pedalIdx;
    pedalHist.needsUpdate = true;
  }
  // Light budget: old light (released columns, past their first FRESH_AGE above the key) may add up to
  // LIGHT_BUDGET screen-tall full-level columns; past that it is scaled down to fit, while fresh strikes, feet and
  // held notes keep full price. It dims fast but recovers slowly, so a lift doesn't flare the fading columns back up.
  const lightLoad = trails.scan(t);
  const densityTarget = Math.min(1, LIGHT_BUDGET / Math.max(lightLoad.oldLoad, 1e-3));
  const density = trailUniforms.uDensity;
  density.value = damp(density.value, densityTarget, densityTarget < density.value ? 0.05 : 1.5, dt);
  // and the density of Daniel's columns alone, which the canvas takes on the frame a replay leaves it (tickCueStage)
  const danTarget = Math.min(1, LIGHT_BUDGET / Math.max(lightLoad.danLoad, 1e-3));
  lightBudget.danDensity = damp(lightBudget.danDensity, danTarget, danTarget < lightBudget.danDensity ? 0.05 : 1.5, dt);
  if (count) glowMix.multiplyScalar(1 / count);
  else glowMix.setRGB(0.05, 0.08, 0.2);
  tmpColor.copy(STAGE_DARK).lerp(glowMix, count ? 0.03 * Math.min(1, count / 4) : 0);
  stageTint.lerp(tmpColor, 1 - Math.exp(-dt / 0.6));
  scene.background.copy(stageTint);
  scene.fog.color.copy(stageTint);

  overlay.update(info, t, dt, ownInfo);
  tickMeter(dt);
  spectacle?.update(dt, t, info, audioIn.stream ? audioIn.level : 0);
  updateLooks(dt, t, info);  // the scheme and the instrument, after spectacle (its camera drift) and before the composer
  const theoryDisplay = spectacle?.settings.enabled ? spectacle.settings.labels : "full";
  // with a scheme over spectacle's Atmosphere chord view its note labels are hidden, so the page's own chord label shows
  const ownsTheory = spectacle?.settings.enabled && spectacle?.ownsTheory?.() && !schemeOwnsNotes();
  overlay.label.mesh.visible = !ownsTheory && theoryDisplay !== "off";
  overlay.staff.mesh.visible = overlay.nns.mesh.visible = theoryDisplay === "full";
  composer.render(dt);
  renderer.autoClear = false;
  renderer.render(overlayScene, overlayCam);
  renderer.autoClear = true;
  drawGlass(t);  // after the camera has moved for this frame; the glass is never recorded
  if (rec.state === "recording" && rec.videoTrack) {
    rec.frameAcc += dt;
    if (rec.frameAcc >= 1 / 60 - 0.004) {  // at most one frame per render; averages 60 fps at any refresh rate
      rec.frameAcc = clamp(rec.frameAcc - 1 / 60, -0.004, 1 / 60);
      rec.videoTrack.requestFrame();
      rec.frames++;
    }
  }

  frameTimes.push(dt * 1000);
  if (frameTimes.length > 120) frameTimes.shift();
  fpsFrames++;
  if (t - fpsAt >= 0.5) {
    fpsValue = fpsFrames / (t - fpsAt);
    fpsFrames = 0;
    fpsAt = t;
    const sorted = [...frameTimes].sort((a, b) => a - b);
    frameMsP95 = sorted[Math.floor(sorted.length * 0.95)] || 0;
  }
  if (rec.state === "recording") {
    const s = Math.floor((performance.now() - rec.startedAt) / 1000);
    $("rec-label").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }
  if (t - hudAt > 0.2) { hudAt = t; updateHud(t); }
  if (t - logUiAt > 0.5) { logUiAt = t; syncLogReadout(); }
  if (cueUiDirty && t - cueUiAt > 0.1) { cueUiAt = t; syncCueUi(); }
}
let loopError = null;
function loop() {
  requestAnimationFrame(loop);
  // Leave GPU time for canvas capture/encoding on high-refresh monitors.
  // MIDI and cue scheduling retain their independent event/worker clocks.
  if (spectacle?.settings.enabled && clock() - lastT < 1 / 60 - .001) return;
  try {
    renderFrame();
  } catch (e) {
    if (!loopError) { loopError = e; console.error("[piano] frame failed:", e); toast("Render error: " + errText(e), true); }
  }
}

// --------------------------------------------------------------- debug/boot --
// window.__piano is for the CDP receipt and for poking at the page from DevTools.
window.__piano = {
  ready: false,
  get spectacle() { return spectacle; },
  // Scheme and Instrument (the "looks" section): looks({ geometry, render }) reports; select*() resolve true once shown;
  // registerScheme(module) joins a module object without a file for this page load (scheme development)
  looks: (opts) => lookStats(opts),
  selectScheme: (id, persist = true) => selectScheme(id, persist),
  selectInstrument: (id, persist = true) => selectInstrument(id, persist),
  registerScheme: (mod) => registerScheme(mod),
  probeSchemes: () => probeLooks().then(() => lookList("scheme")),
  // The top bar's visual settings as the Studio's Looks set them (looks/registry.js): each is what its own control does, and
  // each answers false when it keeps the setting as it was (a mode the menu doesn't offer; a framing change while REC runs).
  setColourMode: (mode) => setColourMode(mode),
  setNumbersMode: (mode) => setNumbersMode(mode),
  applyFraming: (id) => (FRAMINGS[id] ? applyFraming(id) : false),
  get studio() { return studio; },  // the Studio drawer (piano/studio/studio.js), once it has mounted
  get scheme() { return looks.scheme.active ? looks.scheme.active.instance : null; },
  get instrument() { return looks.instrument.active ? looks.instrument.active.handle : null; },
  conversation: {
    async mark() {
      if (!perfLog) throw new Error("The practice log is not available yet.");
      if (demo.running) throw new Error("Stop Demo before playing an answer.");
      const perf_ms = pageSec(clock()) * 1000;  // same origin as the note events and log.timebase()
      await perfLog.flush();
      const status = perfLog.status();
      if (status.state === "off") throw new Error("Enable the practice log before playing an answer.");
      return { page_id: PAGE_ID, perf_ms, timebase: perfLog.timebase(), buffered: status.buffered };
    },
  },
  snapshot() { renderFrame(); return canvas.toDataURL("image/jpeg", 0.9); },
  stats() {
    const info = currentInfo();
    return { fps: Math.round(fpsValue), framing: framing.id, sounding: [...sounding.keys()].sort((a, b) => a - b),
             chord: info ? info.name : null, label: overlay.shown ? overlay.shown.name : null,
             notes: info ? info.notes.map((n) => n.name + n.octave) : [], trailsLive: trails.liveCount(clock()),
             trailCap: TRAIL_MAX, pedal: sustain, rec: rec.state,
             nns: lastNns ? lastNns.text : null,
             key: { name: keyView.key ? keyView.key.name : null, confidence: keyView.confidence, locked: keyView.locked, dim: keyView.dim },
             keyRaw: keyRaw ? keyRaw.name : null, nnsMode: theoryUi.nns, minor: theoryUi.minor, colour: COLOUR.mode,
             log: perfLog ? perfLog.status() : null, logRoutes,
             fonts: { ...fontState }, demo: demo.running, noteOns: stats.noteOns,
             glow: Object.fromEntries([...sounding.keys()].map((m) => [m, +(keys.get(m)?.glow ?? 0).toFixed(3)])),
             cue: cueStats() };
  },
  // Claude's hand, for receipts: play(cue) hands a cue straight to the player, as the stream would (no server).
  // play(cue, { id, at, grace }) makes it a local at-cue (cues.js handle): the Studio's practice player hands each chord so,
  // with an "exercise:" id, and takes chords back with cancel(id) / extend(id, step, offAt); clears() is the player's clear
  // counter, which only a real clear moves (hush, an SSE clear, pagehide), so the practice player notices one and stops.
  cues: { get client() { return cueClient; }, player: cuePlayer, voice: cueVoice, view: cueView, stage: cueStage,
          play: (cue, opts) => {
            const o = opts || {};
            const id = o.id ?? `local-${++cueLocalSeq}`;
            noteCue(cue, id);
            planCue(cue, id);
            return cuePlayer.handle(cue, o.at === undefined ? { id } : { id, at: o.at, grace: o.grace });
          },
          cancel: (id, o) => cuePlayer.cancel(id, o),
          extend: (id, step, offAt) => cuePlayer.extend(id, step, offAt),
          clears: () => cuePlayer.state().clears,
          clear: () => hushClaude(),
          get chipLabel() { return overlay.cueShown ? overlay.cueShown.label : null; },  // what the chip draws now
          get chipLead() { return cueChipLead(overlay.cueShown); },  // its first word: CLAUDE, EXERCISE or YOU
          setView: (v) => { cueStage.view = CUE_VIEWS.includes(v) ? v : "auto"; return cueStage.view; } },
  // The jam space, for receipts (arsenal/lanes/jam_verify.mjs; jam spec 8.11 item 12): the deck, Claude's band (transport),
  // the glass and the jam view, stats(), and hooks a harness needs to measure them.
  jam: {
    get deck() { return jam.deck; },
    transport,
    glass: jamGlass,
    pageId: PAGE_ID,
    get view() { return cueStage.view; },
    setView: (v) => { cueStage.view = CUE_VIEWS.includes(v) ? v : "auto"; const sel = $("cue-view-select"); if (sel) sel.value = cueStage.view; return cueStage.view; },
    stats: () => jamStats(),
    // A5: what the canvas draws, as state: each key away from its rest (tilt, surface, light, clearcoat, rims), the camera,
    // the light budget, the stage tint, the chip's and the floor pool's opacity. Where a take and its control part, this
    // says what parts.
    digest() {
      const out = {};
      for (const k of keys.values()) {
        const c = k.material.color, e = k.material.emissive;
        const surface = !k.black && (c.r !== IVORY.r || c.g !== IVORY.g || c.b !== IVORY.b);
        if (k.pivot.rotation.x !== 0 || e.r || e.g || e.b || surface || k.frame.visible || k.holdFrame.visible) {
          out[k.m] = [k.pivot.rotation.x, c.r, c.g, c.b, e.r, e.g, e.b, k.material.clearcoat ?? null,
                      k.frame.visible ? k.frame.material.opacity : 0, k.holdFrame.visible ? k.holdFrame.material.opacity : 0];
        }
      }
      return { camera: [cam.x, cam.span, camera.position.x, camera.position.y, camera.position.z], density: trailUniforms.uDensity.value,
               tint: [stageTint.r, stageTint.g, stageTint.b], chip: overlay.cue ? overlay.cue.mat.opacity : 0,
               pool: poolMesh.visible ? poolMesh.material.opacity : 0, keys: out };
    },
    // A5: a held clock the harness steps. hold() freezes it; frame(dt, {hash}) moves it on by dt and draws one frame (and
    // hashes what was drawn); release() gives the page its own clock back.
    clock: {
      // at: the clock value to hold at (a take and its control hold at the same one), else wherever the clock is now
      hold(at = null) { heldClock = Number.isFinite(at) ? at : clock(); return heldClock; },
      frame(dt = 1 / 60, { hash = false } = {}) {
        if (heldClock === null) heldClock = clock();
        heldClock += dt;
        renderFrame();
        return hash ? { t: heldClock, ...canvasHash() } : { t: heldClock };
      },
      release() { heldClock = null; return true; },
      get held() { return heldClock; },
    },
    seedSparks(seed = 1) {  // a seeded spark scatter (mulberry32), so a take and its control draw the same sparks
      let s = seed >>> 0;
      sparkRandom = () => { s = (s + 0x6d2b79f5) >>> 0; let x = Math.imul(s ^ (s >>> 15), 1 | s); x ^= x + Math.imul(x ^ (x >>> 7), 61 | x); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
      return seed;
    },
    record(on = true) { jam.record = on ? [] : null; return !!jam.record; },  // Claude's strikes (cueNoteOn), heard or not
    get strikes() { return jam.record ? jam.record.slice() : null; },
    // Ghosts put on the keys directly (A9): as Try's would be; instant sets the keys' levels at once (no fade)
    ghost({ target = [], incoming = [], hold = [], instant = true } = {}) {
      jam.tryGhosts = target.length || incoming.length || hold.length ? { target, incoming, hold } : null;
      syncGhosts();
      if (instant) {
        for (const k of keys.values()) {
          const g = jamGhosts.target.has(k.m) || jamGhosts.incoming.has(k.m) || jamGhosts.hold.has(k.m);
          k.ghostLevel = g ? 1 : 0;
          k.ghostFull = !jamGhosts.target.has(k.m) && jamGhosts.incoming.has(k.m) ? 0 : 1;
          k.holdLevel = jamGhosts.hold.has(k.m) ? 1 : 0;
        }
      }
      return [...cueView.ghost].sort((a, b) => a - b);
    },
    keyTop(m) { camera.updateMatrixWorld(); return glassKeyTop(m); },  // the glass's projection of a key's top face (CSS px)
    // world points [x, y, z] through this frame's camera, in CSS px of the glass box
    project(points) {
      camera.updateMatrixWorld();
      const s = glassBox.width / framing.w, v = new THREE.Vector3();
      return points.map(([x, y, z]) => { v.set(x, y, z).project(camera); return [(v.x + 1) * 0.5 * framing.w * s, (1 - v.y) * 0.5 * framing.h * s]; });
    },
    // A9: false hides the ghost rim frames (their fill stays), true shows them again; returns whether they show
    ghostFrames(show = true) { ghostFramesHidden = !show; return !ghostFramesHidden; },
    keyGeometry(m) {  // the rest-pose top face in world units, as the key and the glass use it
      const k = keys.get(m);
      if (!k) return null;
      return { midi: m, black: k.black, x: keyX(m), top: k.black ? KEY.blackTop : 0, back: KEY.back, len: k.black ? KEY.blackL : KEY.whiteL,
               w: k.black ? KEY.blackW : KEY.whiteW, blackL: KEY.blackL };
    },
    // Draw a frame and read a region of it back (framing px, top-left origin): base64 RGBA, row 0 at the top (A9's snapshot)
    region({ x = 0, y = 0, w = 64, h = 64, draw = true } = {}) {
      if (draw) renderFrame();
      const gl = renderer.getContext(), H = gl.drawingBufferHeight;
      const sw = Math.round(w * renderScale), sh = Math.round(h * renderScale);
      const buf = new Uint8Array(sw * sh * 4);
      gl.readPixels(Math.round(x * renderScale), H - Math.round(y * renderScale) - sh, sw, sh, gl.RGBA, gl.UNSIGNED_BYTE, buf);
      const flipped = new Uint8Array(w * h * 4);
      // Keep the existing framing-pixel contract when Cinema renders more physical pixels.
      for (let row = 0; row < h; row++) for (let col = 0; col < w; col++) {
        const source = ((sh - 1 - Math.min(sh - 1, Math.floor((row + .5) * sh / h))) * sw + Math.min(sw - 1, Math.floor((col + .5) * sw / w))) * 4;
        flipped.set(buf.subarray(source, source + 4), (row * w + col) * 4);
      }
      let bin = "";
      for (let i = 0; i < flipped.length; i += 0x8000) bin += String.fromCharCode.apply(null, flipped.subarray(i, i + 0x8000));
      return { x, y, w, h, rgba: btoa(bin) };
    },
    // A5: a test oscillator as the recorded audio input (the recorder takes it like a chosen device)
    testInput(freq = 440, gain = 0.25) {
      audioIn.ctx = audioIn.ctx || new AudioContext();
      const osc = audioIn.ctx.createOscillator(), g = audioIn.ctx.createGain(), dest = audioIn.ctx.createMediaStreamDestination();
      osc.frequency.value = freq;
      g.gain.value = gain;
      osc.connect(g).connect(dest);
      osc.start();
      audioIn.ctx.resume().catch(() => {});
      audioIn.stream = dest.stream;
      audioIn.label = `test oscillator ${freq} Hz`;
      return { label: audioIn.label, tracks: dest.stream.getAudioTracks().map((tr) => tr.label) };
    },
  },
  get log() { return perfLog; },  // the practice log itself, for receipts: flush(), stop(), stats()
  midiInputs() { return midi.inputs.map((i) => ({ name: i.name, state: i.state, bound: midi.bound.includes(i) })); },
  // port: a port name to arrive from (the echo guard); midiRankOf(name): how that port ranks for binding
  midiMessage(bytes, port = null) {
    onMidiMessage({ data: Uint8Array.from(bytes), timeStamp: performance.now(), currentTarget: port ? { name: port } : null });
  },
  midiRankOf: (name) => midiRank({ name }),
  cueOutIsKeyboard: (name) => isDanielsKeyboard(name),  // would Claude's Out menu refuse this port
  camHints() {  // the camera's recent note hints: Daniel's and Claude's
    const cue = cam.cueRecent.length, daniel = cam.recent.length;
    return { cue, daniel, x: +cam.x.toFixed(3), span: +cam.span.toFixed(3), hurry: +cam.hurry.toFixed(3),
             danielPlays: clock() - cam.heardAt < CAM.grace, plans: cuePlans.size };
  },
  // Where a key's top face lands on the canvas (framing pixels), at its current tilt through this frame's camera: the
  // whole face, or (front) the middle of the part a finger sees, in front of the black keys. For framing and colour receipts.
  keyQuad(m, front = false) {
    const k = keys.get(m);
    if (!k) return null;
    camera.updateMatrixWorld();
    k.pivot.updateMatrixWorld();
    const hw = (k.black ? KEY.blackW : KEY.whiteW) / 2, top = k.black ? KEY.blackTop : 0;
    const len = k.black ? KEY.blackL : KEY.whiteL, pivotZ = KEY.back - KEY.pivotBack;
    const x1 = front ? hw * 0.55 : hw;
    const z0 = KEY.back - pivotZ + (front ? (k.black ? len * 0.35 : KEY.blackL + 0.5) : 0);
    const z1 = KEY.back - pivotZ + (front ? len * 0.9 : len);
    const v = new THREE.Vector3();
    return [[-x1, z0], [x1, z0], [x1, z1], [-x1, z1]].map(([x, z]) => {
      v.set(x, top, z).applyMatrix4(k.pivot.matrixWorld).project(camera);
      return [+((v.x + 1) * 0.5 * framing.w).toFixed(1), +((1 - v.y) * 0.5 * framing.h).toFixed(1)];
    });
  },
  gpu() {
    const gl = renderer.getContext();
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    return { renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
             version: gl.getParameter(gl.VERSION), three: THREE.REVISION };
  },
  get lastUpload() { return lastUpload; },
};
// Theory next-gen (TN2) and the staff's key signature (LS6), for receipts: the reader mode and the reader, what the staff and
// the Nashville row last drew, the signature model with its changes, and the shared number formatter.
window.__piano.theory = {
  get mode() { return pianoReader ? "next" : "classic"; },
  get reader() { return pianoReader; },
  staff: () => staffDrawn && { ...staffDrawn, notes: staffDrawn.notes.map((n) => ({ ...n })) },
  nns: () => nnsDrawn && nnsDrawn.map((r) => ({ ...r })),
  signature: () => ({ ...keySig.state(), history: keySig.history() }),
  formatNumber,
};

function cueStats() {
  const c = cueView.caption;
  const frames = [], lit = {};
  for (const k of keys.values()) {
    if (k.frame.visible) frames.push(k.m);
    if (k.cueGlow > 0.004) lit[k.m] = +k.cueGlow.toFixed(3);  // Claude's light still on a key, released ones included
  }
  return {
    status: cueView.status, view: cueStage.view, onStage: cueStage.on, mix: +cueStage.mix.toFixed(3), glass: +cueStage.glass.toFixed(3),
    sounding: [...cueSounding.keys()].sort((a, b) => a - b), ghosts: [...cueView.ghost].sort((a, b) => a - b), frames, lit,
    lastLabel: cueView.lastLabel, last: cueView.last,
    caption: c ? { label: c.label, detail: c.detail, kind: c.kind, source: c.source,
                   under: c.under ? { label: c.under.label, detail: c.under.detail, step: c.under.step } : null } : null,
    chip: +overlay.cueAlpha.toFixed(3), chipOnCanvas: overlay.cue ? overlay.cue.mesh.visible : false,
    glow: Object.fromEntries([...cueSounding.keys()].map((m) => [m, +(keys.get(m)?.cueGlow ?? 0).toFixed(3)])),
    depth: Object.fromEntries([...cueSounding.keys()].map((m) => [m, +(keys.get(m)?.depth ?? 0).toFixed(3)])),
    voice: cueVoice.status(), voiceStats: cueVoice.stats(), player: cuePlayer.state(), client: cueClient ? cueClient.stats() : null,
    midiOut: cueMidiOutName || null, echoes: midi.echoes, recTracks: rec.tracks,
  };
}

// The HUD's claude row, continued: Claude's band (the run, bar and pass, the owner, late notes) and the jam key
function jamHudText() {
  const p = jam.position, s = jam.state;
  let text = "";
  if (p && p.state !== "waiting") {
    text += ` · ${p.mode} bar ${p.bar} pass ${Number.isFinite(p.pass) ? p.pass + 1 : "-"}${p.sounding_here ? "" : " (silent here)"}`;
  } else if (s && s.knock) {
    text += " · knocking";
  } else if (s && s.pending && s.pending.length) {
    text += " · waiting for your rest";
  }
  if (s && s.owner) text += ` · owner ${s.owner_here ? "this tab" : "another tab"}`;
  const runs = transport.stats().runs;
  const late = runs.reduce((n, r) => n + (r.late_dropped || 0), 0);
  if (late) text += ` · ${late} late notes skipped`;
  if (keyView.jam) text += ` · jam key ${keyView.jam}`;
  return text;
}

// __piano.jam.stats(): what the jam space is doing, for receipts
function jamStats() {
  const frames = [], holds = [];
  for (const k of keys.values()) {
    if (k.frame.visible) frames.push(k.m);
    if (k.holdFrame.visible) holds.push(k.m);
  }
  const sorted = (set) => [...set].sort((a, b) => a - b);
  return {
    page_id: PAGE_ID, view: cueStage.view, onStage: cueStage.on, glassMix: +cueStage.glass.toFixed(3), rest: jamRest.resting(),
    key: keyView.name, jamKey: keyView.jam, keyLocked: keyView.locked,
    recording: rec.state, recorderSources: rec.sources || null,
    position: jam.position, state: jam.state,
    ghosts: { target: sorted(jamGhosts.target), incoming: sorted(jamGhosts.incoming), hold: sorted(jamGhosts.hold),
              foundAt: Number.isFinite(jamGhosts.foundAt) ? +jamGhosts.foundAt.toFixed(3) : null, frames, holds },
    hoverGate: { ...hoverGate },
    pool: { level: +pool.level.toFixed(4), opacity: +poolMesh.material.opacity.toFixed(4), visible: poolMesh.visible,
            x: +pool.x.toFixed(3), strong: +pool.strong.toFixed(3) },
    deck: jam.deck ? jam.deck.stats() : null, transport: transport.stats(),
    glass: jamGlass ? jamGlass.stats() : null, glassBox: { width: glassBox.width, height: glassBox.height },
    errors: jam.errors, lastError: jam.lastError,
  };
}
// The pixels just drawn: an FNV-1a hash of the whole drawing buffer, per-channel sums, and the pixels within a small
// distance of moonlight (#C8DCFF, every channel within 12). Read in the same task as the render.
let hashBuf = null;
function canvasHash() {
  const gl = renderer.getContext();
  const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
  if (!hashBuf || hashBuf.length !== w * h * 4) hashBuf = new Uint8Array(w * h * 4);
  gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, hashBuf);
  let hsh = 0x811c9dc5, r = 0, g = 0, b = 0, moon = 0;
  const cells = new Array(16 * 9).fill(0);  // R+G+B per cell of a 16 x 9 grid, row 0 at the bottom of the buffer
  for (let i = 0; i < hashBuf.length; i += 4) {
    const R = hashBuf[i], G = hashBuf[i + 1], B = hashBuf[i + 2];
    hsh = Math.imul(hsh ^ R, 16777619); hsh = Math.imul(hsh ^ G, 16777619); hsh = Math.imul(hsh ^ B, 16777619);
    r += R; g += G; b += B;
    if (Math.abs(R - 200) <= 12 && Math.abs(G - 220) <= 12 && Math.abs(B - 255) <= 12) moon++;
    const p = i >> 2;
    cells[Math.floor(Math.floor(p / w) * 9 / h) * 16 + Math.floor((p % w) * 16 / w)] += R + G + B;
  }
  return { hash: (hsh >>> 0).toString(16).padStart(8, "0"), sum: [r, g, b], moon, w, h, cells };
}

function boot() {
  wireUi();
  wireCueUi();
  applyFraming(framing.id, false);
  try {
    spectacle = createSpectacle({ THREE, scene, renderer, camera, keys, lacquer, floor, railLine, bloom, keyX, toast,
      recording: () => rec.state !== "idle" || rec.arming, quality: setRenderQuality,
      audio: () => audioIn.stream ? audioIn.data : null,
      lookTarget,
      // classic(on): the page's own look, with the atmosphere off; a scheme hides the classic columns too (applyClassicLook).
      // Turning the atmosphere off restores the keys' colours, so an instrument's black keys are painted again after it.
      classic: (on) => { atmosphereLook = !on; applyClassicLook(); if (looks.instrument.hints) queueMicrotask(paintBlackKeys); } });
  } catch (e) { console.error("[piano] atmosphere unavailable:", e); toast("Atmosphere unavailable: " + errText(e), true); }
  startLooks();  // the stored Scheme and Instrument, after spectacle has taken the page's own materials
  syncDemoButton();
  syncRecButton();
  loadFonts();
  startLog();
  startCues();
  startDeck();  // the cards, after the stream (8.11 item 13): deck frames arriving before it are read by its first refresh
  startStudio();  // the Studio after the deck, which it shares the right edge with (it loads its modules on its own)
  (async () => {
    let state = "prompt";
    try { state = (await navigator.permissions.query({ name: "midi" })).state; } catch { /* not queryable */ }
    if (state === "denied") setMidiStatus("MIDI permission denied: allow it in site settings");
    else connectMIDI();
  })();
  listAudioInputs().catch(() => {});
  $("boot").hidden = true;
  window.__piano.ready = true;
  requestAnimationFrame(loop);
}
boot();
