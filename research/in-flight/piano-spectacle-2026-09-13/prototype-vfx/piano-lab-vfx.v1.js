// Piano — arsenal/web/piano.js  (ES module)
// A three.js grand-staff piano visualizer for recording TikToks from a KeyLab 88 mk3.
//
// Everything that must appear in a recording is drawn INTO the WebGL canvas (keys, trails,
// the chord label and the staff), because MediaRecorder captures only the canvas. The HTML
// around it (topbar, HUD, hints, toasts) is never recorded.
//
// Sections: THEORY (pure; node-tested) · colour · scene · trails · sparks · camera ·
//           overlay (chord label + staff) · notes engine · MIDI · computer keys · demo ·
//           recording · UI · loop.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

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
    const bias = fifths === 0 ? 0 : fifths <= 6 ? 1 : -1;
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

// ----------------------------------------------------------------- colour --
// Pitch colour walks the circle of fifths: music in one key keeps a coherent arc of hues
// (C major = teal through blue and violet to pink) and a modulation visibly shifts the palette.
const COLOUR = { mode: safeGet("arsenal.piano.colour") || "pitch" };
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
  scene.add(pivot);
  keys.set(m, { m, black, pivot, material, lever: len + KEY.pivotBack, depth: 0, vel: 0, target: 0,
                glow: 0, glowTarget: 0, color: new THREE.Color() });
}

// ----------------------------------------------------------------- trails --
// One instanced draw for every trail. Each instance stores its note's start, release and
// sound-end times; the vertex shader places the bar from the clock, so a trail costs nothing
// per frame on the CPU. Each height is a moment in the note's life, so a column draws its loudness over
// time: a bright strike, a slow sag while it sounds, and a quick let-go when the sound stops.
const T0 = nowSec();
const clock = () => nowSec() - T0;
const FAR = 1e6;
const TRAIL_MAX = 640;          // the cap: slots are recycled, so a long session never grows
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
                        uPedalHist: { value: pedalHist }, uDensity: { value: 1 },
                        // LAB spectacle: the shimmer band (fxTrigger sets these)
                        uShimT0: { value: -1e6 }, uShimX0: { value: 0 }, uShimX1: { value: 0 }, uShimGain: { value: 0 }, uShimGold: { value: 0 } };

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
  const attr = new THREE.InstancedBufferAttribute(new Float32Array(TRAIL_MAX * size), size);
  attr.setUsage(THREE.DynamicDrawUsage);
  trailGeo.setAttribute(name, attr);
  trailAttr[name] = attr;
}
trailAttr.aT0.array.fill(-FAR);
trailAttr.aT1.array.fill(-FAR);
trailAttr.aT2.array.fill(-FAR);
trailGeo.instanceCount = TRAIL_MAX;
const trailMesh = new THREE.Mesh(trailGeo, new THREE.ShaderMaterial({
  uniforms: trailUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  defines: { STRIKE: glslF(LIGHT.strike), STRIKE_TAU: glslF(LIGHT.strikeTau), SAG_FLOOR: glslF(LIGHT.sagFloor),
             SAG_TAU: glslF(LIGHT.sagTau), PEDAL_BOOST: glslF(LIGHT.pedalBoost), PEDAL_ONLY: glslF(LIGHT.pedalOnly),
             RELEASE_FAST: glslF(LIGHT.releaseFast), RELEASE_FAST_TAU: glslF(LIGHT.releaseFastTau),
             RELEASE_SLOW_TAU: glslF(LIGHT.releaseSlowTau), END_CUT: glslF(LIGHT.endCut),
             AFTERGLOW: glslF(LIGHT.afterglow), FRESH_AGE: glslF(LIGHT.freshAge) },
  vertexShader: `
    uniform float uNow, uSpeed, uBaseY, uZ, uTop, uLife, uPedal;
    attribute float aX, aW, aT0, aT1, aT2, aVel;
    attribute vec3 aColor;
    varying vec2 vP;
    varying float vX;
    varying float vBot, vTop, vW, vT0, vT1, vEnd, vBar, vHeld, vFoot;
    varying vec3 vColor;
    float envelope(float s) { return (1.0 + STRIKE * exp(-s / STRIKE_TAU)) * (SAG_FLOOR + (1.0 - SAG_FLOOR) * exp(-s / SAG_TAU)); }
    float letGo(float t, float t1) { float x = clamp((t - t1 + 0.03) / 0.15, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); }
    void main() {
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
      vW = aW; vColor = aColor; vX = aX;
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
    uniform float uShimT0, uShimX0, uShimX1, uShimGain, uShimGold;
    varying float vX;
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
      // LAB spectacle: a shimmer band that rides up the chord's columns 3.2x faster than they rise; gold adds a second
      // band and a dispersion fringe (red leading, blue trailing)
      float sAge = uNow - uShimT0;
      if (uShimGain > 0.0 && sAge > 0.0 && sAge < 2.6) {
        float inX = smoothstep(uShimX0 - 0.8, uShimX0, vX) * (1.0 - smoothstep(uShimX1, uShimX1 + 0.8, vX));
        float bw = 0.8 + 0.5 * sAge;
        float lit = smoothstep(0.0, 0.04, energy) * (1.0 - smoothstep(1.4, 2.6, sAge)) * inX * uShimGain;
        vec3 shim = vec3(0.0);
        for (int b = 0; b < 2; b++) {
          float dy = vP.y - (uBaseY + (sAge - 0.45 * float(b)) * uSpeed * 3.2);
          float g = exp(-dy * dy / (bw * bw)) * (b == 0 ? 1.0 : 0.55 * uShimGold);
          float s2 = 0.3 * bw * bw;
          vec3 fringe = vec3(exp(-(dy - 0.5 * bw) * (dy - 0.5 * bw) / s2), exp(-dy * dy / s2), exp(-(dy + 0.5 * bw) * (dy + 0.5 * bw) / s2));
          shim += mix(mix(vColor, vec3(1.0), 0.3) * g, vec3(1.0, 0.62, 0.22) * g * 1.2 + fringe * g * 0.5, uShimGold);
        }
        col += shim * (core * (0.45 + 0.8 * axis * axis) + halo * 0.3) * lit;
      }
      gl_FragColor = vec4(col * fade, 1.0);
    }`,
}));
trailMesh.frustumCulled = false;
scene.add(trailMesh);

let trailsDirty = false;
const trails = {
  next: 0,
  start(m, vel, t) {
    const A = trailAttr;
    let slot = -1;
    for (let i = 0; i < TRAIL_MAX; i++) {
      const j = (this.next + i) % TRAIL_MAX;
      const gone = A.aT0.array[j] < -1e5 || t - A.aT2.array[j] > LIGHT.endCut;  // faded out: the shader skips it
      if (gone) { slot = j; break; }
    }
    if (slot < 0) slot = this.next;  // every slot busy: recycle the oldest in ring order
    this.next = (slot + 1) % TRAIL_MAX;
    A.aX.array[slot] = keyX(m);
    A.aW.array[slot] = isBlack(m) ? 0.44 : 0.64;
    A.aT0.array[slot] = t;
    A.aT1.array[slot] = FAR;
    A.aT2.array[slot] = FAR;
    A.aVel.array[slot] = vel / 127;
    const c = noteColor(m, vel);
    A.aColor.array.set([c.r, c.g, c.b], slot * 3);
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
  // Visible columns (the shader's cull test), and the light their old stretches spend: each released column's
  // level times its afterglow integrated from FRESH_AGE up to the top of the screen, as a share of the screen height.
  // Columns still under a finger are exempt in the shader, so they are not counted here either.
  scan(t) {
    const A = trailAttr, top = trailUniforms.uTop.value, G = LIGHT.afterglow;
    const screen = Math.max(1e-3, (top - RAIL_Y) / TRAIL_SPEED);  // seconds of column the screen shows
    let live = 0, oldLoad = 0;
    for (let j = 0; j < TRAIL_MAX; j++) {
      const t0 = A.aT0.array[j], gone = t - Math.min(t, A.aT2.array[j]);
      if (t0 < -1e5 || gone > LIGHT.endCut || RAIL_Y + gone * TRAIL_SPEED > top) continue;
      live++;
      if (A.aT1.array[j] > t) continue;
      const a0 = Math.max(gone, LIGHT.freshAge), a1 = Math.min(t - t0, TRAIL_LIFE * 0.8, screen);
      if (a1 <= a0) continue;
      const spent = G * (Math.exp(-(a0 - 0.5) / G) - Math.exp(-(a1 - 0.5) / G)) / screen;
      oldLoad += lightLevel(A.aVel.array[j], false, 0, Math.max(0, t - t0 - 0.5 * (a0 + a1))) * releaseLevel(gone) * spent;
    }
    return { live, oldLoad };
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
function burst(m, vel, t) {
  const count = Math.round(6 + 20 * (vel / 127));
  const c = noteColor(m, vel);
  const x = keyX(m);
  for (let i = 0; i < count; i++) {
    const j = sparkNext;
    sparkNext = (sparkNext + 1) % SPARK_MAX;
    sparkAttr.position.array.set([x + (Math.random() - 0.5) * 0.5, RAIL_Y + 0.05, TRAIL_Z + 0.1], j * 3);
    sparkAttr.aVel.array.set([(Math.random() - 0.5) * 1.8, 1.6 + Math.random() * 4.5 * (0.5 + vel / 254),
                              (Math.random() - 0.3) * 0.9], j * 3);
    sparkAttr.aBirth.array[j] = t;
    sparkAttr.aLife.array[j] = 0.7 + Math.random() * 1.6;
    sparkAttr.aSize.array[j] = 0.16 + Math.random() * 0.26;
    sparkAttr.aSeed.array[j] = Math.random() * 6.283;
    sparkAttr.aColor.array.set([c.r * 1.3, c.g * 1.3, c.b * 1.3], j * 3);  // no white lift: sparks keep the note's hue
  }
  sparksDirty = true;
}

// ------------------------------------------------------------ key motion --
function updateKeys(dt) {
  const steps = Math.max(1, Math.ceil(dt / (1 / 240)));
  const h = dt / steps;
  for (const k of keys.values()) {
    const pressing = k.target > k.depth + 1e-4;
    const stiffness = pressing ? 4200 : 820;   // fast down, springy up with a small overshoot
    const damping = pressing ? 118 : 36;
    for (let i = 0; i < steps; i++) {
      k.v = (k.v || 0) + ((k.target - k.depth) * stiffness - (k.v || 0) * damping) * h;
      k.depth += k.v * h;
    }
    if (Math.abs(k.depth) < 1e-5 && k.target === 0 && Math.abs(k.v) < 1e-4) { k.depth = 0; k.v = 0; }
    k.pivot.rotation.x = k.depth / k.lever;
    k.glow = damp(k.glow, k.glowTarget, k.glowTarget > k.glow ? 0.012 : 0.22, dt);
    // a lit white key takes the note's colour into its surface instead of laying a tint over ivory, and sheds
    // most of its white clearcoat sheen, so it reads as coloured rather than pastel (pedal-held keys too)
    if (!k.black) {
      const tint = Math.min(1, k.glow * 2.5);
      keyAlbedo.copy(k.color);
      const peak = Math.max(keyAlbedo.r, keyAlbedo.g, keyAlbedo.b);
      if (peak > 1) keyAlbedo.multiplyScalar(1 / peak);  // a surface can't reflect more than it receives
      k.material.color.copy(IVORY).lerp(keyAlbedo, tint * 0.95);
      k.material.clearcoat = 0.5 - 0.35 * tint;  // never 0, so the material never recompiles
    }
    // The surface colour is already full by glow 0.4, so above a plain held note the emissive climbs faster: the
    // pedal boost and hard velocities show on the key itself, capped so a strike doesn't burn to white.
    const lift = k.black ? k.glow * 1.7 : Math.min(1.4, k.glow * 0.45 + Math.max(0, k.glow - 0.8) * 0.9);
    k.material.emissive.copy(k.color).multiplyScalar(lift);
  }
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
const cam = { x: 0, span: framing.minSpan, recent: [] };
const lookTarget = new THREE.Vector3();
function hintCamera(m, t) {
  cam.recent.push({ x: keyX(m), t });
  if (cam.recent.length > 96) cam.recent.shift();
}
function updateCamera(dt, t, snap = false) {
  let lo = Infinity, hi = -Infinity;
  for (const n of cam.recent) if (t - n.t < 6) { lo = Math.min(lo, n.x); hi = Math.max(hi, n.x); }
  let targetX = 0, targetSpan = 57;
  if (framing.follow) {
    targetSpan = lo <= hi ? clamp(hi - lo + 6, framing.minSpan, 57) : Math.max(cam.span, framing.minSpan);
    targetX = lo <= hi ? (lo + hi) / 2 : cam.x;
    targetX = clamp(targetX, -28.5 + targetSpan / 2, 28.5 - targetSpan / 2);
  }
  cam.x = snap ? targetX : damp(cam.x, targetX, 1.2, dt);
  cam.span = snap ? targetSpan : damp(cam.span, targetSpan, 1.6, dt);

  const vfov = THREE.MathUtils.degToRad(framing.fov);
  const aspect = framing.w / framing.h;
  const tanH = Math.tan(vfov / 2) * aspect;
  const dist = (cam.span / 2 / tanH + 7) * (1 - fxCam.push);  // LAB spectacle: a push-in on Epic and Legendary
  const elev = THREE.MathUtils.degToRad(framing.follow ? 22 : 17) + Math.sin(t * 0.13) * 0.012 + fxCam.elev;
  const yaw = Math.sin(t * 0.071) * (framing.follow ? 0.06 : 0.035) + fxCam.yaw;
  lookTarget.set(cam.x, 0.4, -0.5);
  camera.position.set(lookTarget.x + dist * Math.sin(yaw) * Math.cos(elev),
                      lookTarget.y + dist * Math.sin(elev),
                      lookTarget.z + dist * Math.cos(yaw) * Math.cos(elev));
  camera.lookAt(lookTarget);
  // Lens shift instead of tilting: the keyboard sits low in the frame and the trails get the sky.
  const shift = framing.follow ? 0.25 : 0.29;
  camera.setViewOffset(framing.w, framing.h, 0, -shift * framing.h, framing.w, framing.h);
  trailUniforms.uTop.value = RAIL_Y + dist * Math.tan(vfov / 2) * (1 + 2 * shift) * 0.98;
  sparkUniforms.uPx.value = framing.h / (2 * Math.tan(vfov / 2));
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

const LAYOUT = {
  "9:16": { label: { cx: 540, cy: 318, w: 1060, h: 340, align: "center", size: 170 },
            staff: { cx: 540, cy: 800, w: 860, h: 600, s: 24 } },
  "16:9": { label: { cx: 500, cy: 196, w: 900, h: 310, align: "left", size: 140 },
            staff: { cx: 1560, cy: 272, w: 640, h: 520, s: 20 } },
};

const overlayScene = new THREE.Scene();
const overlayCam = new THREE.OrthographicCamera(0, framing.w, framing.h, 0, -10, 10);

function makeLayer(spec) {
  const c = document.createElement("canvas");
  c.width = spec.w;
  c.height = spec.h;
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(spec.w, spec.h), mat);
  mesh.position.set(spec.cx, framing.h - spec.cy, 0);
  overlayScene.add(mesh);
  return { canvas: c, ctx: c.getContext("2d"), tex, mat, mesh, spec };
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
function drawRuns(ctx, runs, x, baseline, glow) {
  let cursor = x;
  for (const r of runs) {
    ctx.font = r.font;
    r.x = cursor;
    r.w = ctx.measureText(r.text).width;
    cursor += r.w + (r.kern || 0);
  }
  const width = cursor - x;
  for (const pass of glow ? [0, 1] : [1]) {
    for (const r of runs) {
      ctx.font = r.font;
      ctx.fillStyle = r.color;
      ctx.shadowColor = pass === 0 ? glow : "transparent";
      ctx.shadowBlur = pass === 0 ? 38 : 0;
      ctx.fillText(r.text, r.x, baseline + (r.dy || 0));
    }
  }
  ctx.shadowBlur = 0;
  return width;
}
function measureRuns(ctx, runs) {
  let w = 0;
  for (const r of runs) { ctx.font = r.font; w += ctx.measureText(r.text).width + (r.kern || 0); }
  return w;
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
  let runs;
  if (info.kind === "chord") {
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

function drawStaff(layer, info) {
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

    // accidentals, stacked into columns from the top so they never collide
    const accCols = [];
    const withAcc = notes.filter((n) => n.acc).sort((a, b) => b.diatonic - a.diatonic);
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
          if (n.acc) {
            const glyph = { 1: SMUFL.sharp, 2: SMUFL.dsharp, [-1]: SMUFL.flat, [-2]: SMUFL.dflat }[n.acc];
            ctx.fillText(glyph, noteX - s * 0.35 - (n.accCol + 1) * s * 1.3, y);
          }
        } else {
          ctx.beginPath();
          ctx.ellipse(x + headW / 2, y, headW / 2, s * 0.52, -0.35, 0, Math.PI * 2);
          ctx.ellipse(x + headW / 2, y, headW * 0.22, s * 0.3, 0.9, 0, Math.PI * 2);
          ctx.fill("evenodd");
          if (n.acc) {
            ctx.font = `${2.2 * s}px ${FONT.music}`;
            ctx.fillText(accGlyph(n.acc), noteX - s * 0.2 - (n.accCol + 1) * s * 1.3, y + s * 0.55);
          }
        }
      }
      ctx.shadowBlur = 0;
    }
  }
}

const overlay = {
  label: null, staff: null,
  shown: null, pending: null, pendingSince: 0, staffKey: "", labelKey: "",
  labelAlpha: 0, staffAlpha: 0, pop: 0, silentSince: 0, needsRedraw: true,
  build() {
    disposeLayer(this.label);
    disposeLayer(this.staff);
    const L = LAYOUT[framing.id];
    this.label = makeLayer(L.label);
    this.staff = makeLayer(L.staff);
    overlayCam.right = framing.w;
    overlayCam.top = framing.h;
    overlayCam.updateProjectionMatrix();
    this.invalidate();
    fxBuildOverlay();
  },
  invalidate() { this.labelKey = ""; this.staffKey = ""; this.needsRedraw = true; },
  // info: the detection for what is sounding right now, or null for silence
  update(info, t, dt) {
    const sounding = !!info;
    if (sounding) this.silentSince = 0;
    else if (!this.silentSince) this.silentSince = t;

    // The staff follows every change at once. The label waits for the set to settle: 120 ms after a
    // note-on (a rolled chord does not flash its partial names), 300 ms after a release (letting go
    // of a chord note by note keeps its name), and a quick note released before settling still gets named.
    const staffInfo = info || this.shown;
    const staffKey = staffInfo ? staffInfo.notes.map((n) => n.midi + n.name).join(",") + COLOUR.mode + fontState.smufl : "none" + fontState.smufl;
    if (staffKey !== this.staffKey || this.needsRedraw) {
      drawStaff(this.staff, staffInfo);
      this.staff.tex.needsUpdate = true;
      this.staffKey = staffKey;
    }
    if (sounding) {
      const grew = info.onCount !== this.lastOnCount;
      this.lastOnCount = info.onCount;
      if (!this.pending || this.pending.name !== info.name) { this.pending = info; this.pendingSince = t; this.pendingGrew = grew; }
      else this.pending = info;
      if (this.shown && this.shown.name === info.name) {
        this.shown = info;  // same name, new voicing: follow at once
      } else if (t - this.pendingSince >= (this.pendingGrew ? 0.12 : 0.3)) {
        if (this.shown) this.pop = 1;
        this.shown = this.pending;
      }
    } else if (this.pending && this.pendingGrew && (!this.shown || this.shown.name !== this.pending.name)) {
      this.shown = this.pending;
      this.pop = 1;
    }
    const labelKey = this.shown ? this.shown.name + "|" + this.shown.notes.map((n) => n.name).join(",") + COLOUR.mode + fontState.text : "";
    if (labelKey !== this.labelKey || this.needsRedraw) {
      drawLabel(this.label, this.shown);
      this.label.tex.needsUpdate = true;
      this.labelKey = labelKey;
    }
    this.needsRedraw = false;

    const quiet = sounding ? 0 : t - this.silentSince;
    const target = sounding ? 1 : quiet < 2.4 ? 0.62 : 0;
    this.labelAlpha = damp(this.labelAlpha, this.shown ? target : 0, target > this.labelAlpha ? 0.05 : (quiet < 2.4 ? 0.2 : 0.55), dt);
    this.staffAlpha = damp(this.staffAlpha, sounding ? 1 : quiet < 2.4 ? 0.7 : 0.4, 0.25, dt);
    this.pop = damp(this.pop, 0, 0.09, dt);
    this.label.mat.opacity = this.labelAlpha * (1 - 0.35 * this.pop);
    this.label.mesh.scale.setScalar(1 + 0.045 * this.pop);
    this.staff.mat.opacity = this.staffAlpha;
    if (!sounding && quiet > 4.5 && this.shown) { this.shown = null; this.pending = null; }
  },
};

// -------------------------------------------------------------- spectacle --
// LAB ONLY (piano-lab-vfx). Rarity tiers for musical moments; each tier is a stack of stage effects that escalates:
//   0 Common     a colour pulse along the rail
//   1 Uncommon   two rail pulses and a small ember lift
//   2 Rare       + a floor shockwave, a spark fountain, a shimmer band up the chord's columns, the banner
//   3 Epic       + light shafts, a second ring, a small camera push, old columns dimmed a little
//   4 Legendary  gold: three rings, a gold fountain, gold shafts, an aurora curtain, a dispersion shimmer, the chord
//                name in gold foil, a camera push, and the house lights dimmed on old columns so net light holds
// Design: research/in-flight/piano-spectacle-2026-09-13/design-vfx-director.md
// Rules: every effect is a pure function of the clock; nothing flashes the whole frame; effect light fades out of the
// chord name and staff rectangles (PROTECT); bodies stay under the bloom threshold (0.9), only thin crests cross it.
const TIER_NAMES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"];
const TIER_INK = [null, "#8fe8a8", "#79b8ff", "#c79bff", "#ffc766"];
// fractions of the frame, origin top-left: [x0, y0, x1, y1]
const PROTECT = {
  "9:16": { label: [0.17, 0.10, 0.83, 0.235], staff: [0.13, 0.30, 0.88, 0.54] },
  "16:9": { label: [0.01, 0.08, 0.47, 0.30], staff: [0.66, 0.06, 0.99, 0.46] },
};
const PAL_N = 8;
const fxShared = {
  uNow: { value: 0 }, uRes: { value: new THREE.Vector2(1080, 1920) },
  uProtA: { value: new THREE.Vector4() }, uProtB: { value: new THREE.Vector4() },
  uPal: { value: Array.from({ length: PAL_N }, () => new THREE.Color()) }, uPalN: { value: 1 },
  uSpan: { value: new THREE.Vector2() }, uGoldC: { value: new THREE.Color(1.0, 0.62, 0.22) },
};
const FX_GLSL = `
  uniform float uNow, uPalN;
  uniform vec2 uRes, uSpan;
  uniform vec4 uProtA, uProtB;
  uniform vec3 uPal[${PAL_N}];
  uniform vec3 uGoldC;
  float sq(float x) { return x * x; }
  float fxRect(vec2 p, vec4 r, float soft) {
    vec2 a = smoothstep(r.xy - soft, r.xy, p) * (1.0 - smoothstep(r.zw, r.zw + soft, p));
    return a.x * a.y;
  }
  // effect light allowed here: 0 inside the chord name, 0.35 inside the staff, 1 elsewhere
  float fxProtect() {
    vec2 p = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
    return (1.0 - fxRect(p, uProtA, 0.035)) * (1.0 - 0.65 * fxRect(p, uProtB, 0.035));
  }
  // the chord's colours, low note to high; f counts palette steps and wraps, with a short blend between neighbours
  vec3 fxPal(float f) {
    float n = max(uPalN, 1.0);
    float i = floor(mod(f, n));
    float j = mod(i + 1.0, n);
    float fr = smoothstep(0.35, 0.65, fract(f));
    return mix(uPal[int(i)], uPal[int(j)], fr);
  }
`;
const FX_WORLD_VS = `
  varying vec3 vWorld;
  void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const fxEase = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
function fxBump(age, rise, hold, fall) {
  if (age < 0) return 0;
  if (age < rise) return fxEase(age / rise);
  if (age < rise + hold) return 1;
  return 1 - fxEase((age - rise - hold) / fall);
}
function fxMaterial(uniforms, fragmentShader, vertexShader = FX_WORLD_VS) {
  return new THREE.ShaderMaterial({ uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
                                    vertexShader, fragmentShader: FX_GLSL + fragmentShader });
}

// Floor shockwave: rings on the stage floor, so the front arc crosses the empty floor below the keys and the back arc
// rises out from behind the rail. The piano body occludes it (depth test), which is what sells it as 3D.
const RING_N = 4;
const ringU = { ...fxShared,
  uRing: { value: Array.from({ length: RING_N }, () => new THREE.Vector4(0, 0, -1e6, 0)) },     // x, z, t0, gold
  uRingP: { value: Array.from({ length: RING_N }, () => new THREE.Vector4(0, 24, 1.6, 0.5)) } }; // gain, radius, duration, width
const ringMesh = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), fxMaterial(ringU, `
  uniform vec4 uRing[${RING_N}];
  uniform vec4 uRingP[${RING_N}];
  varying vec3 vWorld;
  void main() {
    vec3 col = vec3(0.0);
    for (int k = 0; k < ${RING_N}; k++) {
      float age = uNow - uRing[k].z;
      float dur = uRingP[k].z;
      if (age < 0.0 || age > dur) continue;
      vec2 q = vWorld.xz - uRing[k].xy;
      float r = uRingP[k].y * (1.0 - exp(-age / 0.5));        // fast out, slowing: a shockwave, not a ripple
      float d = length(q) - r;
      float w = uRingP[k].w * (0.35 + 1.2 * age / dur);       // the wave widens as it spends itself
      float aa = fwidth(d);                                    // a ring thinner than a pixel is widened, energy kept
      float we = max(w, aa * 2.0);
      float body = (d > 0.0 ? exp(-sq(d / (we * 0.3 + aa))) : exp(d / we)) * (w / we);
      float crest = exp(-sq(d / (aa * 1.5 + 0.06))) * min(1.0, 2.0 * w / we);
      float life = sq(1.0 - age / dur);
      float ang = atan(q.y, q.x) / 6.2831853 + 0.5;
      vec3 c = mix(fxPal(ang * uPalN * 2.0 + age * 1.5), uGoldC, uRing[k].w);
      col += (c * body * 0.32 + mix(c, vec3(1.0), 0.45) * crest * 1.1) * life * uRingP[k].x;
    }
    float fogK = 1.0 - smoothstep(55.0, 130.0, distance(vWorld, cameraPosition));
    gl_FragColor = vec4(col * fogK * fxProtect(), 1.0);
  }`));
ringMesh.rotation.x = -Math.PI / 2;
ringMesh.position.y = -2.27;
ringMesh.frustumCulled = false;
ringMesh.visible = false;
scene.add(ringMesh);

// Rail pulse: fronts of the chord's colours running outward along the gold rail line from under the chord.
const PULSE_N = 6;
const railU = { ...fxShared, uRailGold: { value: 0 }, uRailY: { value: RAIL_Y - 0.06 },
  uPulse: { value: Array.from({ length: PULSE_N }, () => new THREE.Vector4(0, -1e6, 40, 0)) } };  // cx, t0, speed, gain
const railFx = new THREE.Mesh(new THREE.PlaneGeometry(58, 1.4), fxMaterial(railU, `
  uniform vec4 uPulse[${PULSE_N}];
  uniform float uRailGold, uRailY;
  varying vec3 vWorld;
  void main() {
    float e = 0.0;
    for (int k = 0; k < ${PULSE_N}; k++) {
      float age = uNow - uPulse[k].y;
      if (age < 0.0 || age > 1.8) continue;
      float d = abs(vWorld.x - uPulse[k].x) - uPulse[k].z * age;
      float head = exp(-d * d / 0.35);
      float wake = d < 0.0 ? exp(d * 0.35) * 0.18 : 0.0;
      e += (head + wake) * exp(-age / 0.55) * uPulse[k].w;
    }
    float dy = vWorld.y - uRailY;
    float prof = exp(-dy * dy / 0.0035) + 0.22 * exp(-abs(dy) * 6.0);
    float ends = 1.0 - smoothstep(25.6, 26.6, abs(vWorld.x));
    float span = max(uSpan.y - uSpan.x, 0.001);
    vec3 c = mix(fxPal(clamp((vWorld.x - uSpan.x) / span, 0.0, 1.0) * (uPalN - 1.0)), uGoldC, uRailGold);
    vec3 col = c * e * prof * 1.4 + uGoldC * uRailGold * prof * 0.3;
    gl_FragColor = vec4(col * ends, 1.0);
  }`));
railFx.position.set(0, RAIL_Y - 0.06, -3.26);
railFx.frustumCulled = false;
railFx.visible = false;
scene.add(railFx);

// Fountain: ballistic sparks from the chord's keys (up, then falling back), separate from the rising embers.
const FXS_MAX = 2000;
const fxsU = { ...fxShared, uPx: sparkUniforms.uPx };
const fxsGeo = new THREE.BufferGeometry();
const fxsAttr = {};
for (const [name, size] of [["position", 3], ["aVel", 3], ["aBirth", 1], ["aLife", 1], ["aSize", 1], ["aSeed", 1], ["aColor", 3]]) {
  const attr = new THREE.BufferAttribute(new Float32Array(FXS_MAX * size), size);
  attr.setUsage(THREE.DynamicDrawUsage);
  fxsGeo.setAttribute(name, attr);
  fxsAttr[name] = attr;
}
fxsAttr.aBirth.array.fill(-FAR);
const fxsPoints = new THREE.Points(fxsGeo, fxMaterial(fxsU, `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float r = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, r);
    vec3 c = mix(vColor, vec3(1.0), 0.35 * a * a);  // a white-hot centre
    gl_FragColor = vec4(c * a * a * vAlpha * 2.6 * fxProtect(), 1.0);
  }`, `
  uniform float uNow, uPx;
  attribute vec3 aVel, aColor;
  attribute float aBirth, aLife, aSize, aSeed;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float age = uNow - aBirth;
    if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
    float k = age / aLife;
    float drag = (1.0 - exp(-age * 0.9)) / 0.9;
    vec3 p = position + aVel * drag + vec3(sin(age * 3.1 + aSeed) * 0.2 * k, -4.2 * age * age, 0.0);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float px = aSize * uPx * (1.0 - 0.45 * k) / max(-mv.z, 0.1);
    gl_PointSize = max(px, 2.5);
    float cover = min(1.0, (px * px) / 6.25);  // a point clamped up to 2.5 px keeps its energy: no sub-pixel flicker
    vAlpha = pow(1.0 - k, 1.6) * cover * (0.78 + 0.22 * sin(age * 11.0 + aSeed * 7.0));
    vColor = aColor;
  }`));
fxsPoints.frustumCulled = false;
fxsPoints.visible = false;
scene.add(fxsPoints);
let fxsNext = 0, fxsDirty = false;
function fxFountain(notes, t, tier) {
  const gold = tier >= 4;
  const total = [0, 90, 300, 520, 900][tier];
  const per = Math.max(6, Math.floor(total / notes.length));
  const spread = gold ? 0.55 : 0.35;
  const A = fxsAttr, G = fxShared.uGoldC.value;
  for (const m of notes) {
    const x = keyX(m), c = noteColor(m, 110);
    for (let i = 0; i < per; i++) {
      const j = fxsNext;
      fxsNext = (fxsNext + 1) % FXS_MAX;
      const up = [0, 3.2, 6.0, 7.2, 8.5][tier] * (0.45 + 0.55 * Math.random());
      A.position.array.set([x + (Math.random() - 0.5) * 0.5, RAIL_Y + 0.1, TRAIL_Z + 0.2], j * 3);
      A.aVel.array.set([(Math.random() - 0.5) * 2.4, up, (Math.random() - 0.3) * 1.2], j * 3);
      A.aBirth.array[j] = t + Math.random() * spread;
      A.aLife.array[j] = 1.0 + Math.random() * (gold ? 1.3 : 0.9);
      A.aSize.array[j] = 0.1 + Math.random() * 0.22;
      A.aSeed.array[j] = Math.random() * 6.283;
      const src = gold && Math.random() < 0.55 ? [G.r * 1.5, G.g * 1.5, G.b * 1.5] : [c.r * 1.2, c.g * 1.2, c.b * 1.2];
      A.aColor.array.set(src, j * 3);
    }
  }
  fxsDirty = true;
}

// Light shafts: a fan of seven beams from the rail under the chord, behind the columns, shooting up at 42 u/s.
const shaftU = { ...fxShared, uShaftT0: { value: -1e6 }, uShaftGain: { value: 0 }, uShaftGold: { value: 0 },
                 uShaftCx: { value: 0 }, uBaseY: { value: RAIL_Y } };
const shaftGeo = new THREE.PlaneGeometry(1, 1);
shaftGeo.translate(0, 0.5, 0);
const shaftMesh = new THREE.Mesh(shaftGeo, fxMaterial(shaftU, `
  uniform float uShaftT0, uShaftGain, uShaftGold, uShaftCx, uBaseY;
  varying vec3 vWorld;
  void main() {
    float age = uNow - uShaftT0;
    vec2 q = vec2(vWorld.x - uShaftCx, vWorld.y - uBaseY);
    float r = length(q);
    float a = atan(q.x, max(q.y, 1e-3));
    float env = smoothstep(0.0, 0.3, age) * (1.0 - smoothstep(1.7, 3.3, age));
    float reach = smoothstep(-4.0, 0.0, age * 42.0 - r);
    vec3 col = vec3(0.0);
    for (int k = 0; k < 7; k++) {
      float fk = float(k) - 3.0;
      float th = fk * 0.17 + 0.035 * sin(uNow * 0.6 + fk * 1.9);
      float wdt = 0.03 + 0.01 * abs(fk) + fwidth(a) * 0.7;
      float g = exp(-sq((a - th) / wdt));
      vec3 c = mix(uPal[int(mod(float(k), max(uPalN, 1.0)))], uGoldC, uShaftGold * (k == 3 ? 1.0 : 0.55));
      col += c * g * (1.0 - 0.12 * abs(fk));
    }
    float fall = exp(-r / 15.0) * smoothstep(0.4, 2.2, r);
    float motes = 0.8 + 0.2 * sin(r * 1.1 - uNow * 4.0);
    gl_FragColor = vec4(col * fall * reach * motes * env * uShaftGain * 0.55 * fxProtect(), 1.0);
  }`));
shaftMesh.scale.set(70, 40, 1);
shaftMesh.position.set(0, RAIL_Y, TRAIL_Z - 0.7);
shaftMesh.frustumCulled = false;
shaftMesh.visible = false;
scene.add(shaftMesh);

// Aurora curtain: far behind the piano, a folded curtain with a gold hem, rays fading upward.
const auroraU = { ...fxShared, uAurT0: { value: -1e6 }, uAurGain: { value: 0 }, uAurCx: { value: 0 }, uBaseY: { value: RAIL_Y } };
const auroraGeo = new THREE.PlaneGeometry(1, 1);
auroraGeo.translate(0, 0.5, 0);
const auroraMesh = new THREE.Mesh(auroraGeo, fxMaterial(auroraU, `
  uniform float uAurT0, uAurGain, uAurCx, uBaseY;
  varying vec3 vWorld;
  void main() {
    float age = uNow - uAurT0;
    float env = smoothstep(0.0, 0.9, age) * (1.0 - smoothstep(3.2, 5.2, age));
    float x = vWorld.x - uAurCx;
    float hem = uBaseY + 1.0 + 2.4 * sin(x * 0.09 + uNow * 0.31) + 1.3 * sin(x * 0.23 - uNow * 0.53) + 0.5 * sin(x * 0.57 + uNow * 0.97);
    float h = vWorld.y - hem;
    float curtain = smoothstep(-0.8, 0.6, h) * exp(-max(h, 0.0) / 10.0);
    float fold = 0.5 + 0.5 * sin(x * 0.8 + 1.6 * sin(x * 0.17 + uNow * 0.45) + uNow * 0.7);
    float rays = 0.45 + 0.55 * fold * fold * fold;
    float hemLine = exp(-sq(h / 0.9));
    vec3 low = mix(fxPal(x * 0.05 + uNow * 0.1), uGoldC, 0.65);
    vec3 high = fxPal(x * 0.04 + 2.0 + uNow * 0.07);
    vec3 col = mix(low, high, smoothstep(0.0, 14.0, h)) * curtain * rays * 0.34 + uGoldC * hemLine * 0.22;
    float side = 1.0 - smoothstep(40.0, 70.0, abs(x));
    gl_FragColor = vec4(col * env * side * uAurGain * fxProtect(), 1.0);
  }`));
auroraMesh.scale.set(150, 60, 1);
auroraMesh.position.set(0, RAIL_Y - 6, -30);
auroraMesh.frustumCulled = false;
auroraMesh.visible = false;
scene.add(auroraMesh);

// Overlay: the tier banner (between the chord name and the staff) and the gold foil on the chord name.
const BANNER = { "9:16": { cx: 540, cy: 540, w: 760, h: 100 }, "16:9": { cx: 500, cy: 400, w: 760, h: 96 } };
const fxOverlay = { banner: null, foil: null };
function fxBuildOverlay() {
  disposeLayer(fxOverlay.banner);
  if (fxOverlay.foil) { overlayScene.remove(fxOverlay.foil); fxOverlay.foil.geometry.dispose(); fxOverlay.foil.material.dispose(); }
  fxOverlay.banner = makeLayer({ ...BANNER[framing.id], align: "center" });
  fxOverlay.banner.mat.opacity = 0;
  fxOverlay.banner.mesh.renderOrder = 3;
  const L = overlay.label;
  fxOverlay.foil = new THREE.Mesh(new THREE.PlaneGeometry(L.spec.w, L.spec.h), new THREE.ShaderMaterial({
    uniforms: { map: { value: L.tex }, uAmt: { value: 0 }, uSweep: { value: -1 }, uOpacity: { value: 1 } },
    transparent: true, depthTest: false, depthWrite: false,
    vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      uniform sampler2D map;
      uniform float uAmt, uSweep, uOpacity;
      varying vec2 vUv;
      void main() {
        float a = texture2D(map, vUv).a;
        float yy = 1.0 - vUv.y;
        // glyph cores of the main name only: the glow halo is under 0.6 alpha, the note chips sit below yy 0.64
        float core = smoothstep(0.78, 0.98, a) * (1.0 - smoothstep(0.62, 0.68, yy));
        vec3 foil = mix(vec3(1.0, 0.93, 0.70), vec3(0.93, 0.60, 0.20), smoothstep(0.18, 0.56, yy));
        float band = exp(-pow((vUv.x - uSweep + (yy - 0.4) * 0.35) / 0.045, 2.0));
        vec3 col = min(foil + vec3(1.0, 0.98, 0.9) * band * 0.9, vec3(1.0));
        gl_FragColor = vec4(col, core * uAmt * uOpacity);
      }`,
  }));
  fxOverlay.foil.renderOrder = 2;
  overlayScene.add(fxOverlay.foil);
  const P = PROTECT[framing.id];
  fxShared.uProtA.value.set(...P.label);
  fxShared.uProtB.value.set(...P.staff);
  fxState.banner.t0 = -1e6;
}
function fxDrawBanner(tier) {
  const { ctx, spec, tex } = fxOverlay.banner;
  ctx.clearRect(0, 0, spec.w, spec.h);
  tex.needsUpdate = true;
  if (tier < 2) return;
  const text = TIER_NAMES[tier].toUpperCase();
  const size = Math.round(spec.h * 0.36);
  const cx = spec.w / 2, cy = spec.h * 0.42;
  const ink = TIER_INK[tier];
  ctx.font = `700 ${size}px ${FONT.display}`;
  ctx.letterSpacing = `${Math.round(size * 0.42)}px`;
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  const tw = ctx.measureText(text).width;
  for (const dir of [-1, 1]) {  // hairline rules that fade outward
    const x0 = cx + dir * (tw / 2 + size * 0.6), x1 = cx + dir * (tw / 2 + size * 4.0);
    const g = ctx.createLinearGradient(x0, 0, x1, 0);
    g.addColorStop(0, ink);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(Math.min(x0, x1), cy - 1.5, Math.abs(x1 - x0), 3);
  }
  ctx.shadowColor = "rgba(0,0,0,0.85)";
  ctx.shadowBlur = 14;
  if (tier === 4) {
    const g = ctx.createLinearGradient(0, cy - size / 2, 0, cy + size / 2);
    g.addColorStop(0, "#fff1c4");
    g.addColorStop(1, "#e59a2e");
    ctx.fillStyle = g;
  } else ctx.fillStyle = "rgba(244,241,234,0.95)";
  ctx.fillText(text, cx + size * 0.21, cy);
  ctx.shadowBlur = 0;
  ctx.letterSpacing = "0px";
  ctx.fillStyle = ink;  // one gem per tier step
  for (let i = 0; i < tier; i++) {
    const gx = cx + (i - (tier - 1) / 2) * size * 0.62, gy = cy + size * 1.0, r = size * 0.13;
    ctx.beginPath();
    ctx.moveTo(gx, gy - r); ctx.lineTo(gx + r, gy); ctx.lineTo(gx, gy + r); ctx.lineTo(gx - r, gy);
    ctx.closePath();
    ctx.fill();
  }
}

const fxCam = { push: 0, elev: 0, yaw: 0 };
const fxState = { dim: 1, fired: [-1e6, -1e6, -1e6, -1e6, -1e6], lastName: null, log: [], seen: new Map(),
                  auto: /[?&]fx=auto/.test(location.search), until: { ring: -1, rail: -1, fxs: -1, shaft: -1, aurora: -1 },
                  banner: { t0: -1e6, hold: 1, tier: 0 }, shimGain: 0 };
const fxSlot = (arr, key) => arr.reduce((best, v, i) => (v[key] < arr[best][key] ? i : best), 0);
function fxRing(cx, t0, gold, gain, radius, dur, width) {
  const i = fxSlot(ringU.uRing.value, "z");
  ringU.uRing.value[i].set(cx, -0.5, t0, gold);
  ringU.uRingP.value[i].set(gain, radius, dur, width);
  fxState.until.ring = Math.max(fxState.until.ring, t0 + dur);
}
function fxPulse(cx, t0, speed, gain) {
  const i = fxSlot(railU.uPulse.value, "y");
  railU.uPulse.value[i].set(cx, t0, speed, gain);
  fxState.until.rail = Math.max(fxState.until.rail, t0 + 1.8);
}
function fxTrigger(tier, t = clock(), notesIn = null, why = null) {
  const notes = [...new Set(notesIn || [...sounding.keys()])].filter((m) => m >= KEY.first && m <= KEY.last).sort((a, b) => a - b);
  if (!notes.length) return false;
  const xs = notes.map(keyX);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), cx = (x0 + x1) / 2;
  const seen = new Set();
  let n = 0;
  for (const m of notes) {
    const pc = Theory.mod(m, 12);
    if (seen.has(pc) || n >= PAL_N) continue;
    seen.add(pc);
    noteColor(m, 110, fxShared.uPal.value[n++]);
  }
  fxShared.uPalN.value = n;
  fxShared.uSpan.value.set(x0, x1);
  const gold = tier >= 4 ? 1 : 0;
  fxState.fired[tier] = t;
  fxState.log.push({ tier, name: TIER_NAMES[tier], t: +t.toFixed(3), chord: overlay.shown ? overlay.shown.name : null, notes, why });
  fxPulse(cx, t, tier >= 2 ? 44 : 36, [0.45, 0.8, 1.0, 1.1, 1.25][tier]);
  if (tier >= 1) { fxPulse(cx, t + 0.12, 36, 0.5); fxFountain(notes, t, tier); fxState.until.fxs = t + 3.2; }
  if (tier >= 4) fxPulse(cx, t + 0.26, 30, 0.8);
  if (tier >= 2) {
    fxRing(cx, t, gold, tier >= 4 ? 1.35 : 1.0, 26, 1.7, 0.55);
    trailUniforms.uShimT0.value = t + 0.03;
    trailUniforms.uShimX0.value = x0 - 0.6;
    trailUniforms.uShimX1.value = x1 + 0.6;
    trailUniforms.uShimGold.value = gold;
    fxState.shimGain = tier >= 4 ? 1.3 : 1.0;
    fxState.banner = { t0: t + 0.05, hold: [0, 0, 1.2, 1.8, 2.8][tier], tier };
    fxDrawBanner(tier);
  }
  if (tier >= 3) {
    fxRing(cx, t + 0.18, 0, 0.7, 32, 1.9, 0.8);
    shaftU.uShaftT0.value = t + 0.05;
    shaftU.uShaftCx.value = cx;
    shaftU.uShaftGold.value = gold;
    shaftU.uShaftGain.value = tier >= 4 ? 1.2 : 0.9;
    shaftMesh.position.x = cx;
    fxState.until.shaft = t + 3.4;
  }
  if (tier >= 4) {
    fxRing(cx, t + 0.36, 1, 0.6, 38, 2.2, 0.35);
    auroraU.uAurT0.value = t + 0.1;
    auroraU.uAurCx.value = cx;
    auroraU.uAurGain.value = 1;
    auroraMesh.position.x = cx;
    fxState.until.aurora = t + 5.4;
  }
  return true;
}
// Fanciness score for a newly named chord (LAB heuristic; the design doc gives the production scorer).
function fxScore(info, t) {
  const parts = {};
  const entries = [...sounding.entries()];
  if (!info || !entries.length) return { score: 0, tier: 0, parts };
  const newest = Math.max(...entries.map(([, s]) => s.t0));
  const strike = entries.filter(([, s]) => newest - s.t0 < 0.25);
  const vel = strike.reduce((a, [, s]) => a + s.vel, 0) / strike.length;
  const suf = info.suffix || "";
  if (info.kind === "chord") {
    parts.colour = /13|11/.test(suf) ? 4 : /9/.test(suf) ? 3 : /7|6/.test(suf) ? 2 : /sus|dim|aug/.test(suf) ? 1 : 0;
    if (info.bass) parts.slash = 1;
  }
  const pcs = new Set(info.notes.map((x) => Theory.mod(x.midi, 12))).size;
  if (pcs > 3) parts.density = 0.5 * (pcs - 3);
  const ms = info.notes.map((x) => x.midi);
  const span = Math.max(...ms) - Math.min(...ms);
  if (span >= 24) parts.span = span >= 36 ? 2 : 1;
  if (vel >= 96) parts.dynamics = vel >= 112 ? 2 : 1;
  if (sustain) parts.pedal = 0.5;
  if (keyGuess && info.kind === "chord") {
    const scale = keyGuess.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11];
    if (info.notes.some((x) => !scale.includes(Theory.mod(x.midi - keyGuess.tonic, 12)))) parts.borrowed = 1.5;
  }
  const hist = (fxState.seen.get(info.name) || []).filter((x) => t - x < 60);
  if (!fxState.seen.has(info.name)) parts.novelty = 1;
  else if (hist.length >= 3) parts.fatigue = -1;
  fxState.seen.set(info.name, [...hist, t]);
  const score = Object.values(parts).reduce((a, b) => a + b, 0);
  let tier = score >= 7 ? 4 : score >= 5.5 ? 3 : score >= 4 ? 2 : score >= 2 ? 1 : 0;
  let capped = null;
  if (strike.length < 3 && tier > 1) { tier = 1; capped = "fewer than 3 notes struck together"; }
  const COOL = [0, 1.5, 8, 30, 120];
  const want = tier;
  while (tier > 0 && t - fxState.fired[tier] < COOL[tier]) tier--;
  return { score: +score.toFixed(2), want, tier, capped, parts, strike: strike.length, vel: Math.round(vel) };
}
function fxUpdate(dt, t) {
  fxShared.uNow.value = t;
  fxShared.uRes.value.set(composer.readBuffer.width, composer.readBuffer.height);
  const shown = overlay.shown;
  if (!shown) fxState.lastName = null;
  else if (shown.name !== fxState.lastName) {
    fxState.lastName = shown.name;
    if (fxState.auto) { const s = fxScore(shown, t); fxTrigger(s.tier, t, null, s); }
  }
  const legend = t - fxState.fired[4], epic = t - fxState.fired[3];
  const L = fxBump(legend, 1.0, 0.8, 2.4), E = fxBump(epic, 0.8, 0.4, 1.8);
  fxCam.push = 0.055 * L + 0.025 * E * (1 - L);
  fxCam.elev = 0.02 * L + 0.008 * E * (1 - L);
  fxCam.yaw = 0.022 * L;
  fxState.dim = 1 - 0.35 * fxBump(legend, 0.25, 2.2, 1.2) - 0.15 * fxBump(epic, 0.2, 0.8, 1.0);
  railU.uRailGold.value = 0.9 * fxBump(legend, 0.1, 1.6, 1.4);
  ringMesh.visible = t < fxState.until.ring;
  railFx.visible = t < Math.max(fxState.until.rail, fxState.fired[4] + 3.2);
  fxsPoints.visible = t < fxState.until.fxs;
  shaftMesh.visible = t < fxState.until.shaft;
  auroraMesh.visible = t < fxState.until.aurora;
  trailUniforms.uShimGain.value = t - trailUniforms.uShimT0.value < 2.6 ? fxState.shimGain : 0;
  if (fxsDirty) { for (const attr of Object.values(fxsAttr)) attr.needsUpdate = true; fxsDirty = false; }
  const b = fxState.banner, bm = fxOverlay.banner;
  const bo = fxBump(t - b.t0, 0.14, b.hold, 0.6);
  bm.mat.opacity = bo;
  bm.mesh.scale.set(0.94 + 0.06 * fxEase((t - b.t0) / 0.35), 1, 1);
  const foil = fxOverlay.foil, lab = overlay.label;
  foil.material.uniforms.uAmt.value = fxBump(legend - 0.1, 0.18, 2.9, 0.8);
  foil.material.uniforms.uSweep.value = legend > 0.2 && legend < 1.3 ? lerp(0.12, 0.98, fxEase((legend - 0.2) / 1.0)) : -1;
  foil.material.uniforms.uOpacity.value = lab.mat.opacity;
  foil.position.copy(lab.mesh.position);
  foil.scale.copy(lab.mesh.scale);
  foil.visible = foil.material.uniforms.uAmt.value > 0;
}

// ----------------------------------------------------------- notes engine --
// A note sounds while its key is held, or after release while the pedal (CC64) is down.
const sounding = new Map();  // midi -> { held, vel, t0, trail }
let sustain = false;
let detectDirty = true;
let lastInfo = null;
const pcHistory = new Array(12).fill(0);  // decaying pitch-class weights: the key guess spells lone notes
let pcHistoryAt = 0;
let keyGuess = null;
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
  const prev = sounding.get(m);
  if (prev) trails.end(prev.trail, t);  // a repeated note closes its previous trail
  const inRange = m >= KEY.first && m <= KEY.last;
  sounding.set(m, { held: true, vel, t0: t, tRelease: 0, trail: inRange ? trails.start(m, vel, t) : null });
  if (inRange) {
    const k = keys.get(m);
    k.target = 0.17 + 0.27 * (vel / 127);  // velocity-scaled key depth (world units at the key front)
    k.glowTarget = glowLevel(sounding.get(m), t);
    noteColor(m, vel, k.color);
    burst(m, vel, t);
    lightNote(m, vel);
    hintCamera(m, t);
  }
  const f = Math.exp(-(t - pcHistoryAt) / 12);
  for (let i = 0; i < 12; i++) pcHistory[i] *= f;
  pcHistoryAt = t;
  pcHistory[Theory.mod(m, 12)] += 0.5 + vel / 127;
  stats.noteOns++;
  detectDirty = true;
  hideIdleHint();
}
function noteOff(m) {
  const st = sounding.get(m);
  if (!st || !st.held) return;
  const t = clock();
  st.held = false;
  st.tRelease = t;
  trails.release(st.trail, t);
  const k = keys.get(m);
  if (k) { k.target = 0; k.glowTarget = sustain ? glowLevel(st, t) : 0; }
  if (!sustain) { trails.end(st.trail, t); sounding.delete(m); }
  detectDirty = true;
}
function setSustain(on) {
  if (sustain === on) return;
  sustain = on;
  if (!on) {
    const t = clock();
    for (const [m, st] of sounding) {
      if (st.held) continue;
      trails.end(st.trail, t);
      sounding.delete(m);
      const k = keys.get(m);
      if (k) k.glowTarget = 0;
    }
  }
  detectDirty = true;
}
function allNotesOff() {  // CC120 (all sound off), CC123 (all notes off), input switches, Demo stop
  const t = clock();
  for (const [m, st] of sounding) {
    trails.end(st.trail, t);
    const k = keys.get(m);
    if (k) { k.target = 0; k.glowTarget = 0; }
  }
  sounding.clear();
  sustain = false;
  detectDirty = true;
}
function currentInfo() {
  if (!detectDirty) return lastInfo;
  detectDirty = false;
  keyGuess = Theory.estimateKey(pcHistory);
  lastInfo = sounding.size ? Theory.detect([...sounding.keys()], keyGuess ? keyGuess.bias : 0) : null;
  if (lastInfo) lastInfo.onCount = stats.noteOns;  // lets the label tell a new note from a release
  return lastInfo;
}

// ------------------------------------------------------------------- MIDI --
const ALL_INPUTS = "__all__";
const midi = { access: null, inputs: [], bound: [], status: "not connected", last: "", events: 0 };
const midiPrefKey = "arsenal.piano.midiInput";  // stored by port name: ids can change between sessions
// "KeyLab 88 mk3 MIDI" carries keys, pedal and controls; its "DAW" port carries DAW-control traffic.
function midiRank(input) {
  const name = input.name || "";
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
    add(input.id, (input.name || input.id) + (midiRank(input) < 0 ? "  (DAW control)" : "") +
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
  midi.bound = choice === ALL_INPUTS ? midi.inputs.filter((i) => midiRank(i) > 0)
                                     : midi.inputs.filter((i) => i.id === choice);
  for (const input of midi.bound) input.onmidimessage = onMidiMessage;
  if (midi.bound.map((i) => i.id).join(",") !== before) allNotesOff();  // no stuck notes across a switch
  if (remember) safeSet(midiPrefKey, choice === ALL_INPUTS ? ALL_INPUTS : (midi.bound[0] && midi.bound[0].name) || "");
  setMidiStatus(midi.bound.length ? midi.bound.map((i) => i.name).join(" + ") : midi.inputs.length ? "no input selected" : "no inputs");
}
function setMidiStatus(text) { midi.status = text; }
function onMidiMessage(ev) {
  const d = ev.data;
  if (!d || d.length < 2) return;
  const type = d[0] & 0xf0;
  if (type === 0x90 && d.length >= 3) {
    if (d[2] > 0) noteOn(d[1], d[2]); else noteOff(d[1]);
  } else if (type === 0x80 && d.length >= 3) {
    noteOff(d[1]);
  } else if (type === 0xb0 && d.length >= 3) {
    if (d[1] === 64) setSustain(d[2] >= 64);
    else if (d[1] === 120 || d[1] === 123) allNotesOff();
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
  allNotesOff();
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
const rec = { recorder: null, chunks: [], mime: "", startedAt: 0, state: "idle", withAudio: false, error: "" };
let lastUpload = null;
function pickMime(withAudio) {
  const a = withAudio ? ",mp4a.40.2" : "";
  const mp4 = ["avc1.64002a", "avc1.640033", "avc1.4d002a", "avc1"].map((c) => `video/mp4;codecs=${c}${a}`);
  const webm = withAudio ? ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"]
                         : ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
  return [...mp4, ...webm].find((m) => MediaRecorder.isTypeSupported(m)) || "";
}
async function startRecording() {
  if (rec.state !== "idle") return;
  if (typeof MediaRecorder === "undefined") { toast("MediaRecorder is unavailable in this browser", true); return; }
  rec.error = "";
  // Frames are requested by the render loop at a paced 60 fps: captureStream(60) on a 144/240 Hz
  // display gave uneven, roughly 30 fps files.
  const stream = canvas.captureStream(0);
  rec.videoTrack = stream.getVideoTracks()[0];
  rec.frameAcc = 1 / 60;
  rec.frames = 0;
  const track = audioIn.stream && audioIn.stream.getAudioTracks()[0];
  if (track && track.readyState === "live") stream.addTrack(track.clone());  // the clone stops with the recording
  rec.withAudio = stream.getAudioTracks().length > 0;
  rec.mime = pickMime(rec.withAudio);
  try {
    rec.recorder = new MediaRecorder(stream, { mimeType: rec.mime, videoBitsPerSecond: 16_000_000,
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
  lastUpload = null;
  syncRecButton();
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
function fitCanvas() {
  const r = $("stage").getBoundingClientRect();
  const pad = document.fullscreenElement ? 0 : 14;
  const scale = Math.max(0.05, Math.min((r.width - 2 * pad) / framing.w, (r.height - 2 * pad) / framing.h));
  canvas.style.width = `${Math.floor(framing.w * scale)}px`;
  canvas.style.height = `${Math.floor(framing.h * scale)}px`;
}
function applyFraming(id, persist = true) {
  if (rec.state !== "idle" && FRAMINGS[id] !== framing) { toast("Stop recording before changing the framing", true); return; }
  framing = FRAMINGS[id] || FRAMINGS["9:16"];
  if (persist) safeSet("arsenal.piano.framing", framing.id);
  renderer.setSize(framing.w, framing.h, false);
  composer.setSize(framing.w, framing.h);
  camera.fov = framing.fov;
  camera.aspect = framing.w / framing.h;
  overlay.build();
  $("btn-916").setAttribute("aria-pressed", String(framing.id === "9:16"));
  $("btn-169").setAttribute("aria-pressed", String(framing.id === "16:9"));
  updateCamera(0, clock(), true);
  fitCanvas();
}
function toggleHud() { $("hud").hidden = !$("hud").hidden; }
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else $("stage").requestFullscreen().catch((e) => toast("Fullscreen refused: " + errText(e), true));
}
const fmtNotes = (info) => (info ? info.notes.map((n) => n.name + n.octave).join(" ") : "none");
function updateHud(t) {
  if ($("hud").hidden) return;
  const info = lastInfo;
  $("hud-fps").textContent = `${fpsValue.toFixed(0)} fps · ${frameMsP95.toFixed(1)} ms p95`;
  $("hud-render").textContent = `${framing.w}x${framing.h} (${framing.id}) · three r${THREE.REVISION}`;
  $("hud-midi").textContent = midi.status + (midi.last ? ` · ${midi.last}` : "");
  $("hud-notes").textContent = fmtNotes(info);
  $("hud-chord").textContent = (info ? info.name : "none") + (keyGuess ? ` · key ${keyGuess.name}` : "");
  $("hud-pedal").textContent = sustain ? "down (CC64)" : "up";
  $("hud-trails").textContent = `${trails.liveCount(t)} live / cap ${TRAIL_MAX}`;
  $("hud-octave").textContent = `computer keys C${3 + kbOctave}-E${5 + kbOctave}`;
  const recText = rec.state === "recording"
    ? `recording ${((performance.now() - rec.startedAt) / 1000).toFixed(1)} s · ${rec.recorder.mimeType || rec.mime}`
    : rec.state !== "idle" ? rec.state
    : lastUpload ? (lastUpload.ok ? `saved ${lastUpload.json.path}` : `upload failed: ${lastUpload.error}`) : "idle";
  $("hud-rec").textContent = recText + (audioIn.label ? ` · audio: ${audioIn.label}` : " · no audio");
}

function wireUi() {
  for (const b of document.querySelectorAll(".btn")) b.addEventListener("click", () => b.blur());
  $("btn-midi").addEventListener("click", () => (midi.access ? refreshMidiInputs() : connectMIDI()));
  $("midi-select").addEventListener("change", (e) => bindMidi(e.target.value, true));
  $("btn-demo").addEventListener("click", () => (demo.running ? stopDemo() : startDemo()));
  $("btn-916").addEventListener("click", () => applyFraming("9:16"));
  $("btn-169").addEventListener("click", () => applyFraming("16:9"));
  $("color-select").value = COLOUR.mode;
  $("color-select").addEventListener("change", (e) => {
    COLOUR.mode = e.target.value;
    safeSet("arsenal.piano.colour", COLOUR.mode);
    for (const [m, st] of sounding) { const k = keys.get(m); if (k) noteColor(m, st.vel, k.color); }
    overlay.invalidate();
  });
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
  $("btn-rec").addEventListener("click", () => (rec.state === "recording" ? stopRecording() : startRecording()));
  $("btn-full").addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", fitCanvas);
  new ResizeObserver(fitCanvas).observe($("stage"));

  const resumeAudio = () => { if (audioIn.ctx && audioIn.ctx.state === "suspended") audioIn.ctx.resume().catch(() => {}); };
  window.addEventListener("pointerdown", resumeAudio);
  window.addEventListener("keydown", (e) => {
    resumeAudio();
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = e.target && e.target.tagName;
    if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;
    if (e.code === "KeyH") { e.preventDefault(); if (!e.repeat) toggleHud(); return; }
    if (e.code === "KeyF") { e.preventDefault(); if (!e.repeat) toggleFullscreen(); return; }
    if (e.code === "Space") { e.preventDefault(); if (!e.repeat) setSustain(true); return; }
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
let fpsValue = 0, fpsFrames = 0, fpsAt = clock(), hudAt = 0, frameMsP95 = 0;
const frameTimes = [];
const glowMix = new THREE.Color();
const tmpColor = new THREE.Color();
function renderFrame() {
  const t = clock();
  const dt = clamp(t - lastT, 0, 0.1);
  lastT = t;
  tickDemo(t);
  const info = currentInfo();
  updateKeys(dt);
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
  const densityTarget = Math.min(1, LIGHT_BUDGET / Math.max(trails.scan(t).oldLoad, 1e-3)) * fxState.dim;  // LAB: house lights
  const density = trailUniforms.uDensity;
  density.value = damp(density.value, densityTarget, densityTarget < density.value ? 0.05 : 1.5, dt);
  if (count) glowMix.multiplyScalar(1 / count);
  else glowMix.setRGB(0.05, 0.08, 0.2);
  tmpColor.copy(STAGE_DARK).lerp(glowMix, count ? 0.03 * Math.min(1, count / 4) : 0);
  stageTint.lerp(tmpColor, 1 - Math.exp(-dt / 0.6));
  scene.background.copy(stageTint);
  scene.fog.color.copy(stageTint);

  overlay.update(info, t, dt);
  fxUpdate(dt, t);
  composer.render(dt);
  renderer.autoClear = false;
  renderer.render(overlayScene, overlayCam);
  renderer.autoClear = true;
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
  tickMeter(dt);
  if (t - hudAt > 0.2) { hudAt = t; updateHud(t); }
}
let loopError = null;
function loop() {
  requestAnimationFrame(loop);
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
  snapshot() { renderFrame(); return canvas.toDataURL("image/jpeg", 0.9); },
  stats() {
    const info = currentInfo();
    return { fps: Math.round(fpsValue), framing: framing.id, sounding: [...sounding.keys()].sort((a, b) => a - b),
             chord: info ? info.name : null, label: overlay.shown ? overlay.shown.name : null,
             notes: info ? info.notes.map((n) => n.name + n.octave) : [], trailsLive: trails.liveCount(clock()),
             trailCap: TRAIL_MAX, pedal: sustain, key: keyGuess ? keyGuess.name : null, rec: rec.state,
             fonts: { ...fontState }, demo: demo.running, noteOns: stats.noteOns,
             glow: Object.fromEntries([...sounding.keys()].map((m) => [m, +(keys.get(m)?.glow ?? 0).toFixed(3)])) };
  },
  midiInputs() { return midi.inputs.map((i) => ({ name: i.name, state: i.state, bound: midi.bound.includes(i) })); },
  midiMessage(bytes) { onMidiMessage({ data: Uint8Array.from(bytes), timeStamp: performance.now() }); },
  gpu() {
    const gl = renderer.getContext();
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    return { renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
             version: gl.getParameter(gl.VERSION), three: THREE.REVISION };
  },
  get lastUpload() { return lastUpload; },
  // LAB spectacle hooks
  clock: () => clock(),
  fx(tier, notes = null) { return fxTrigger(tier, clock(), notes, "hook"); },
  fxLog() { return fxState.log; },
  // mean ms per frame over n synchronous frames, each forced to finish on the GPU with a 1-pixel read
  bench(n = 120) {
    const gl = renderer.getContext(), px = new Uint8Array(4);
    renderFrame(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const t0 = performance.now();
    for (let i = 0; i < n; i++) { renderFrame(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); }
    return +((performance.now() - t0) / n).toFixed(3);
  },
};

function boot() {
  wireUi();
  applyFraming(framing.id, false);
  syncDemoButton();
  syncRecButton();
  loadFonts();
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
