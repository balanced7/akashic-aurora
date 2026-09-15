// Piano (next) — arsenal/web/piano-next.js  (ES module)
// A three.js grand-staff piano visualizer for recording TikToks from a KeyLab 88 mk3.
// Built from piano.js per arsenal/PIANO-V2-SPEC.md: the trails and sparks moved into a scheme
// (piano/schemes/neon-trails.js) behind the scheme host, and sustain got hysteresis, polarity,
// an on-screen pedal mark, hollow pedalled note heads and a no-wash-out rule.
//
// Everything that must appear in a recording is drawn INTO the WebGL canvas (keys, the scheme,
// the chord label, the staff and the pedal mark), because MediaRecorder captures only the canvas.
// The HTML around it (topbar, HUD, hints, toasts) is never recorded.
//
// Sections: THEORY (pure; node-tested) · colour · scene · keys · scheme host · camera ·
//           overlay (chord label + staff + pedal mark) · notes engine + sustain · MIDI ·
//           computer keys · demo · recording · UI · loop.

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
const T0 = nowSec();
const clock = () => nowSec() - T0;  // page-clock seconds: every note event and scheme call uses it
const errText = (e) => (e && (e.message || e.name)) || String(e);
function safeGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function safeSet(key, value) { try { localStorage.setItem(key, value); } catch { /* storage blocked */ } }

// ----------------------------------------------------------------- colour --
// Pitch colour walks the circle of fifths: music in one key keeps a coherent arc of hues
// (C major = teal through blue and violet to pink) and a modulation visibly shifts the palette.
const COLOUR = { mode: safeGet("arsenal.piano.colour") || "pitch" };
const fifthsIndex = (pc) => (pc * 7) % 12;
function noteLch(midi, vel) {
  if (COLOUR.mode === "velocity") {
    const t = clamp(vel / 127, 0, 1);
    return [0.60 + 0.24 * t, 0.13 + 0.05 * t, lerp(255, 350, t)];
  }
  if (COLOUR.mode === "mono") return [0.80, 0.14, 68];
  return [0.76, 0.155, (200 + 30 * fifthsIndex(Theory.mod(midi, 12))) % 360];
}
function oklchToLinear(L, C, hDeg) {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [Math.max(0, 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
          Math.max(0, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
          Math.max(0, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)];
}
function noteColor(midi, vel, target = new THREE.Color()) {
  const [r, g, b] = oklchToLinear(...noteLch(midi, vel));
  return target.setRGB(r, g, b);  // linear working space
}
function noteCss(midi, vel, alpha = 1) {
  const [L, C, h] = noteLch(midi, vel);
  return `oklch(${L} ${C} ${h} / ${alpha})`;
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
for (let m = KEY.first; m <= KEY.last; m++) {
  const black = isBlack(m);
  const material = black
    ? new THREE.MeshPhysicalMaterial({ color: 0x0a0a0d, roughness: 0.3, clearcoat: 1.0, clearcoatRoughness: 0.08, envMap, envMapIntensity: 0.8 })
    : new THREE.MeshPhysicalMaterial({ color: 0xdedbd3, roughness: 0.36, clearcoat: 0.5, clearcoatRoughness: 0.2, envMap, envMapIntensity: 0.35 });
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

// ----------------------------------------------------------- scheme host --
// A scheme draws the music (trails, columns, particles...) and nothing else: keys, camera, stage and
// overlay stay here and are shared. Schemes are ES modules in ./piano/schemes/<id>.js, loaded with
// import(). Every loaded scheme receives every note event, so switching mid-passage stays coherent;
// only the active one receives update() and is visible. See PIANO-V2-SPEC.md section 1.
const SCHEMES = [
  { id: "neon-trails", name: "Neon Trails" },
];
const SCHEME_KEY = "arsenal.piano.scheme";
const SCHEME_ID = /^[a-z0-9-]+$/;
const SCHEME_METHODS = ["noteOn", "noteRelease", "noteEnd", "pedal", "update", "resize", "setActive", "dispose"];
// The camera's reach, refreshed every frame by updateCamera and handed to the active scheme as frame.view:
//   top         world y of the top of the frame on the trail plane (where rising things leave the picture)
//   pointScale  pixels per world unit at distance 1 (for gl_PointSize)
const view = { top: 30, pointScale: 1000 };
const framingInfo = () => ({ id: framing.id, width: framing.w, height: framing.h });
const schemeCtx = Object.freeze({
  THREE, scene, camera, renderer, clock, keyX, isBlack, noteColor, noteCss,
  KEY: Object.freeze({ first: KEY.first, last: KEY.last }), RAIL_Y, TRAIL_Z,
  get framing() { return framingInfo(); },
});

const schemeHost = {
  registered: [],        // [{id, name, module}] added at run time by __piano.registerScheme (tests, scheme development)
  entries: new Map(),    // id -> { id, name, instance }
  pending: new Map(),    // id -> Promise<entry | null>
  activeId: null,
  selectToken: 0,
  errors: new Map(),     // "id.method" -> count; the first of each kind is logged
  counts: { noteOn: 0, noteRelease: 0, noteEnd: 0, pedal: 0 },
  log: [],               // the last 256 note events, for the receipt: [kind, ...args]

  list() {
    const out = SCHEMES.map((s) => ({ ...s }));
    for (const r of this.registered) {
      const i = out.findIndex((s) => s.id === r.id);
      if (i >= 0) out[i] = { id: r.id, name: r.name }; else out.push({ id: r.id, name: r.name });
    }
    return out;
  },
  active() { return this.activeId ? this.entries.get(this.activeId) || null : null; },

  call(entry, method, args) {
    const fn = entry.instance[method];
    if (typeof fn !== "function") return undefined;
    try {
      return fn.apply(entry.instance, args);
    } catch (e) {
      const key = `${entry.id}.${method}`;
      const n = (this.errors.get(key) || 0) + 1;
      this.errors.set(key, n);
      if (n === 1) {
        console.error(`[piano] scheme ${key} failed:`, e);
        toast(`Scheme ${entry.name}: ${method} failed: ${errText(e)}`, true);
      }
      return undefined;
    }
  },
  emit(kind, ...args) {
    this.counts[kind]++;
    this.log.push([kind, ...args.map((a) => (typeof a === "number" ? +a.toFixed(4) : a))]);
    if (this.log.length > 256) this.log.shift();
    for (const entry of this.entries.values()) this.call(entry, kind, args);
  },
  update(dt, t, frame) {
    const entry = this.active();
    if (entry) this.call(entry, "update", [dt, t, frame]);
  },
  resize() {
    const f = framingInfo();
    for (const entry of this.entries.values()) this.call(entry, "resize", [f]);
  },

  async importModule(id) {
    const reg = this.registered.find((r) => r.id === id);
    if (reg) return reg.module;
    const mod = await import(`./piano/schemes/${id}.js`);
    return mod.default;
  },
  load(id) {
    if (this.entries.has(id)) return Promise.resolve(this.entries.get(id));
    if (this.pending.has(id)) return this.pending.get(id);
    const listed = this.list().find((s) => s.id === id);
    if (!listed) return Promise.resolve(null);
    const p = (async () => {
      const mod = await this.importModule(id);
      const problem = schemeModuleProblem(mod, id);
      if (problem) throw new Error(problem);
      const instance = mod.create(schemeCtx);
      const missing = SCHEME_METHODS.filter((k) => !instance || typeof instance[k] !== "function");
      if (missing.length) throw new Error(`create() returned an instance without ${missing.join(", ")}`);
      const entry = { id, name: mod.name || listed.name, instance };
      this.call(entry, "setActive", [false]);
      this.call(entry, "resize", [framingInfo()]);
      // A scheme that loads mid-passage starts from what is sounding now. Everything below is
      // synchronous, so no note event can slip between this replay and the registration.
      for (const [m, st] of sounding) {
        if (!st.inRange) continue;
        this.call(entry, "noteOn", [m, st.vel, st.t0]);
        if (!st.held) this.call(entry, "noteRelease", [m, st.releasedAt ?? clock()]);
      }
      if (sustain) this.call(entry, "pedal", [true, pedal.raw ?? 127, clock()]);
      this.entries.set(id, entry);
      return entry;
    })().catch((e) => {
      console.error(`[piano] scheme ${id} did not load:`, e);
      toast(`Scheme ${listed.name} did not load: ${errText(e)}`, true);
      return null;
    }).finally(() => { this.pending.delete(id); });
    this.pending.set(id, p);
    return p;
  },
  async select(id, persist = true) {
    if (typeof id !== "string" || !this.list().some((s) => s.id === id)) return false;
    const token = ++this.selectToken;
    const entry = await this.load(id);
    if (!entry || token !== this.selectToken) return false;  // failed, or a later selection won
    const prev = this.active();
    if (prev && prev !== entry) this.call(prev, "setActive", [false]);
    this.activeId = id;
    this.call(entry, "setActive", [true]);
    if (persist) safeSet(SCHEME_KEY, id);
    syncSchemeUi();
    return true;
  },
  cycle() {
    const ids = this.list().map((s) => s.id);
    if (!ids.length) return Promise.resolve(false);
    const at = ids.indexOf(this.activeId);
    return this.select(ids[(at + 1) % ids.length]);
  },
  // Load the rest in the background so they follow the music before anyone switches to them.
  async preloadOthers() {
    for (const s of this.list()) if (s.id !== this.activeId) await this.load(s.id);
  },
  register(mod) {
    const problem = schemeModuleProblem(mod, mod && mod.id);
    if (problem) throw new Error(problem);
    const old = this.entries.get(mod.id);
    if (old) {
      this.call(old, "setActive", [false]);
      this.call(old, "dispose", []);
      this.entries.delete(mod.id);
      if (this.activeId === mod.id) this.activeId = null;
    }
    this.registered = this.registered.filter((r) => r.id !== mod.id);
    this.registered.push({ id: mod.id, name: mod.name, module: mod });
    syncSchemeUi();
    return mod.id;
  },
};
function schemeModuleProblem(mod, id) {
  if (!mod || typeof mod !== "object") return "the module has no default export object";
  if (typeof mod.id !== "string" || !SCHEME_ID.test(mod.id)) return "id must be lowercase letters, digits and dashes";
  if (id !== undefined && mod.id !== id) return `the module's id "${mod.id}" does not match its file "${id}"`;
  if (typeof mod.name !== "string" || !mod.name) return "name is missing";
  if (typeof mod.create !== "function") return "create(ctx) is missing";
  return "";
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
    k.material.emissive.copy(k.color).multiplyScalar(k.glow * (k.black ? 1.7 : 0.55));
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
  view.top = RAIL_Y + dist * Math.tan(vfov / 2) * (1 + 2 * shift) * 0.98;
  view.pointScale = framing.h / (2 * Math.tan(vfov / 2));
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
                flat: "\uE260", natural: "\uE261", sharp: "\uE262", dsharp: "\uE263", dflat: "\uE264",
                pedalDown: "\uE650", pedalUp: "\uE655" };  // keyboardPedalPed, keyboardPedalUp
// staff accidentals by alteration; 0 is the natural a note shows beside an altered note on its line
const SMUFL_ACC = { 1: SMUFL.sharp, 2: SMUFL.dsharp, [-1]: SMUFL.flat, [-2]: SMUFL.dflat, 0: SMUFL.natural };
const ACC_TEXT = { 1: "\u266F", 2: "\uD834\uDD2A", [-1]: "\u266D", [-2]: "\uD834\uDD2B", 0: "\u266E" };
const PEDAL_UP_FADE = 0.6;     // seconds the release mark takes to fade
const HOLLOW_ALPHA = 0.6;      // pedalled note heads (key up, still sounding)
const LABEL_PLATE_ALPHA = 0.5; // readability plates: soft dark shapes whose edges reach zero inside their layer
const STAFF_PLATE_ALPHA = 0.5;
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
  ctx.letterSpacing = "0px";

  // readability plate: a soft dark ellipse behind both lines, so the name reads over any scheme
  const textW = Math.max(mainW, lineW);
  const plateX = spec.align === "center" ? spec.w / 2 : Math.max(x0, 30) + textW / 2;
  const plateY = baseline - S * 0.12;
  drawPlate(ctx, plateX, plateY, Math.min(textW / 2 + S * 0.7, plateX, spec.w - plateX),
            Math.min(S * 0.95, plateY, spec.h - plateY), LABEL_PLATE_ALPHA);

  drawRuns(ctx, runs, x0, baseline, glow);
  ctx.letterSpacing = `${Math.round(small * 0.06)}px`;
  drawRuns(ctx, line, spec.align === "center" ? (spec.w - lineW) / 2 : 30, baseline + S * 0.52, "rgba(0, 0, 0, 0.75)");
  ctx.letterSpacing = "0px";
}

// A radial gradient squeezed into an ellipse; it reaches zero at (rx, ry), so no edge can show.
function drawPlate(ctx, cx, cy, rx, ry, alpha) {
  if (!(rx > 1 && ry > 1)) return;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(1, ry / rx);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
  g.addColorStop(0, `rgba(1, 2, 6, ${alpha})`);
  g.addColorStop(0.55, `rgba(1, 2, 6, ${alpha * 0.72})`);
  g.addColorStop(1, "rgba(1, 2, 6, 0)");
  ctx.fillStyle = g;
  ctx.fillRect(-rx, -rx, 2 * rx, 2 * rx);
  ctx.restore();
}

// pedalled: a Set of the MIDI notes whose keys are up but still sound; their heads draw hollow.
function drawStaff(layer, info, pedalled = new Set()) {
  const { ctx, spec } = layer;
  const { w, h, s } = spec;
  ctx.clearRect(0, 0, w, h);
  layer.heads = [];
  // readability plate: a feathered dark panel over nearly the whole layer; the blur takes its edge
  // to zero before the layer's own edge
  const feather = s * 1.1;
  ctx.save();
  ctx.filter = `blur(${feather}px)`;
  ctx.fillStyle = `rgba(1, 2, 6, ${STAFF_PLATE_ALPHA})`;
  ctx.beginPath();
  ctx.roundRect(feather * 2.4, feather * 2.4, w - feather * 4.8, h - feather * 4.8, s);
  ctx.fill();
  ctx.restore();
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

  const headW = s * 1.69;
  const smufl = fontState.smufl;
  const accFont = smufl ? `${4 * s}px Bravura` : `${2.2 * s}px ${FONT.music}`;
  const staves = [
    { notes: info.notes.filter((n) => n.midi >= 60), yOf: (d) => trebleBottom - (d - 30) * s / 2, lo: 30, hi: 38 },
    { notes: info.notes.filter((n) => n.midi < 60), yOf: (d) => bassBottom - (d - 18) * s / 2, lo: 18, hi: 26 },
  ];
  // Layout first (both staves share one chord position), then draw.
  for (const staff of staves) {
    const notes = [...staff.notes].sort((a, b) => a.diatonic - b.diatonic || a.acc - b.acc);
    // Head columns. Heads a step or less apart (a second, or one line holding two spellings such as
    // B flat and B) cannot share a column: each note takes the first column whose last head sits two
    // steps or more below it. A diatonic chord keeps the usual two columns; a chromatic cluster spreads.
    const lastInCol = [];
    staff.heads = notes.map((n) => {
      let col = 0;
      while (lastInCol[col] !== undefined && n.diatonic - lastInCol[col] <= 1) col++;
      lastInCol[col] = n.diatonic;
      return { n, col, y: staff.yOf(n.diatonic) };
    });
    staff.cols = lastInCol.length;
    // Accidentals. A note on the same line or space as an altered note shows its natural. Glyphs are
    // measured, and each goes in the column nearest the heads where its ink clears every glyph already
    // there. Columns are right-aligned and never overlap.
    const altered = new Set(notes.filter((n) => n.acc).map((n) => n.diatonic));
    ctx.font = accFont;
    const accs = staff.heads.filter((hd) => hd.n.acc || altered.has(hd.n.diatonic)).map((hd) => {
      const kind = hd.n.acc;
      const glyph = smufl ? SMUFL_ACC[kind] : ACC_TEXT[kind];
      const baseline = hd.y + (smufl ? 0 : s * 0.55);
      const mt = ctx.measureText(glyph);
      let asc = mt.actualBoundingBoxAscent, desc = mt.actualBoundingBoxDescent;
      let l = mt.actualBoundingBoxLeft, r = mt.actualBoundingBoxRight;
      if (!(asc + desc > 0 && l + r > 0)) { asc = s * 1.8; desc = s * 0.8; l = 0; r = s; }  // unmeasurable: be generous
      return { hd, kind, glyph, baseline, top: baseline - asc, bottom: baseline + desc, l, r };
    }).sort((a, b) => a.top - b.top);
    const pad = s * 0.12;
    const pack = (order) => {
      const cols = [];
      for (const a of order) {
        let c = 0;
        while (cols[c] && cols[c].some((b) => a.top < b.bottom + pad && b.top < a.bottom + pad)) c++;
        (cols[c] = cols[c] || []).push(a);
      }
      return cols;
    };
    // The engraver's order (top, bottom, second from top, ...) reads best for a few accidentals. Top-down
    // packs any cluster into the fewest columns, so a big cluster takes it whenever it is narrower.
    const zigzag = [];
    for (let i = 0, j = accs.length - 1; i <= j; i++, j--) { zigzag.push(accs[i]); if (i !== j) zigzag.push(accs[j]); }
    const byEngraver = pack(zigzag), byTop = pack(accs);
    const accCols = byTop.length < byEngraver.length ? byTop : byEngraver;
    accCols.forEach((col, c) => { for (const a of col) a.col = c; });
    let edge = -s * 0.7;  // right ink edge of the column, from the first head column's left edge
    for (const col of accCols) {
      for (const a of col) a.dx = edge - a.r;  // glyph origin, so its ink ends at the column edge
      edge -= Math.max(...col.map((a) => a.l + a.r)) + s * 0.22;
    }
    staff.accs = new Map(accs.map((a) => [a.hd, a]));
    staff.accSpan = accCols.length ? -(edge + s * 0.22) : 0;
  }
  // The chord sits at 60% of the staff; a cluster with many accidental columns moves right only as far
  // as it must to clear the clefs, and never past the right barline.
  const cols = Math.max(1, ...staves.map((st) => st.cols));
  const noteX = Math.min(Math.max(left + (right - left) * 0.6, left + s * 4.2 + Math.max(...staves.map((st) => st.accSpan))),
                         right - s * 0.8 - cols * headW);
  layer.accidentals = [];

  for (const staff of staves) {
    const heads = staff.heads;
    if (!heads.length) continue;
    // ledger lines, as wide as the note columns that need them
    ctx.strokeStyle = "rgba(236, 232, 224, 0.78)";
    ctx.lineWidth = Math.max(1.5, s * 0.15);
    ctx.beginPath();
    const ledger = (d, beyond) => {
      const users = heads.filter((hd) => beyond(hd.n));
      if (!users.length) return;
      const x0 = noteX - s * 0.45 + Math.min(...users.map((hd) => hd.col)) * headW;
      const x1 = noteX + headW + s * 0.45 + Math.max(...users.map((hd) => hd.col)) * headW;
      ctx.moveTo(x0, staff.yOf(d)); ctx.lineTo(x1, staff.yOf(d));
    };
    const maxD = heads[heads.length - 1].n.diatonic, minD = heads[0].n.diatonic;
    for (let d = staff.hi + 2; d <= maxD; d += 2) ledger(d, (n) => n.diatonic >= d);
    for (let d = staff.lo - 2; d >= minD; d -= 2) ledger(d, (n) => n.diatonic <= d);
    ctx.stroke();

    for (const hd of heads) {
      const { n, col, y } = hd;
      const x = noteX + col * headW;
      const color = noteCss(n.midi, 110, 1);
      // held notes stay solid; pedalled notes (key up, still sounding) draw as outlines at 60%
      const hollow = pedalled.has(n.midi);
      layer.heads.push({ midi: n.midi, name: n.name + n.octave, x: x + headW / 2, y, w: headW, h: s * 1.1, hollow, col });
      const acc = staff.accs.get(hd);
      if (acc) {
        layer.accidentals.push({ midi: n.midi, name: n.name + n.octave, kind: acc.kind, col: acc.col,
                                 x: noteX + acc.dx - acc.l, y: acc.top, w: acc.l + acc.r, h: acc.bottom - acc.top });
      }
      ctx.globalAlpha = hollow ? HOLLOW_ALPHA : 1;
      ctx.fillStyle = color;
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(1.5, s * 0.13);
      ctx.lineJoin = "round";
      for (const pass of [0, 1]) {
        ctx.shadowColor = pass === 0 ? noteCss(n.midi, 110, 0.9) : "transparent";
        ctx.shadowBlur = pass === 0 ? s * 0.9 : 0;
        if (smufl) {
          ctx.font = `${4 * s}px Bravura`;
          if (hollow) ctx.strokeText(SMUFL.whole, x, y);
          else ctx.fillText(SMUFL.whole, x, y);
        } else {
          ctx.beginPath();
          ctx.ellipse(x + headW / 2, y, headW / 2, s * 0.52, -0.35, 0, Math.PI * 2);
          if (hollow) {
            ctx.stroke();
          } else {
            ctx.ellipse(x + headW / 2, y, headW * 0.22, s * 0.3, 0.9, 0, Math.PI * 2);
            ctx.fill("evenodd");
          }
        }
        if (acc) {
          ctx.font = accFont;
          ctx.fillText(acc.glyph, noteX + acc.dx, acc.baseline);
        }
      }
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }
  }
}

// The sheet-music pedal mark, beside the grand staff under the bass clef where "Ped." is written.
function pedalMarkSpec(staff) {
  const s = staff.s;
  const left = staff.cx - staff.w / 2 + s * 3.2;   // drawStaff's left staff edge, in canvas pixels
  const bassBottom = staff.cy + 7.5 * s;             // drawStaff's bottom bass line
  const w = Math.round(s * 7), h = Math.round(s * 4);
  return { cx: left - s * 0.4 + w / 2, cy: bassBottom + s * 2.4, w, h, s };
}
function drawPedalMark(layer, kind) {
  const { ctx, spec } = layer;
  const s = spec.s;
  ctx.clearRect(0, 0, spec.w, spec.h);
  if (!kind) return;
  const smufl = fontState.smufl;
  // Noto Music carries the Unicode pedal marks (U+1D1AE, U+1D1AF) for when Bravura did not load.
  const glyph = kind === "down" ? (smufl ? SMUFL.pedalDown : "\u{1D1AE}") : (smufl ? SMUFL.pedalUp : "\u{1D1AF}");
  ctx.font = smufl ? `${4 * s}px Bravura` : `${3 * s}px ${FONT.music}`;
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "rgba(244, 241, 234, 0.92)";
  const x = s * 0.6, y = spec.h * 0.7;
  ctx.shadowColor = "rgba(0, 0, 0, 0.9)";
  ctx.shadowBlur = s * 0.8;
  ctx.fillText(glyph, x, y);
  ctx.shadowBlur = 0;
  ctx.fillText(glyph, x, y);
}

const overlay = {
  label: null, staff: null, pedal: null,
  shown: null, pending: null, pendingSince: 0, staffKey: "", labelKey: "", pedalKey: "", pedalled: [],
  labelAlpha: 0, staffAlpha: 0, pop: 0, silentSince: 0, needsRedraw: true,
  build() {
    disposeLayer(this.label);
    disposeLayer(this.staff);
    disposeLayer(this.pedal);
    const L = LAYOUT[framing.id];
    this.label = makeLayer(L.label);
    this.staff = makeLayer(L.staff);
    this.pedal = makeLayer(pedalMarkSpec(L.staff));
    overlayCam.right = framing.w;
    overlayCam.top = framing.h;
    overlayCam.updateProjectionMatrix();
    this.invalidate();
  },
  invalidate() { this.labelKey = ""; this.staffKey = ""; this.pedalKey = ""; this.needsRedraw = true; },
  // info: the detection for what is sounding right now, or null for silence
  update(info, t, dt) {
    const sounding = !!info;
    if (sounding) this.silentSince = 0;
    else if (!this.silentSince) this.silentSince = t;

    // The staff follows every change at once. The label waits for the set to settle: 120 ms after a
    // note-on (a rolled chord does not flash its partial names), 300 ms after a release (letting go
    // of a chord note by note keeps its name), and a quick note released before settling still gets named.
    const staffInfo = info || this.shown;
    // Which sounding notes are pedalled. In silence the last set is kept, so fading heads keep their look.
    if (sounding) {
      this.pedalled = [];
      for (const [m, st] of soundingNotes) if (!st.held) this.pedalled.push(m);
      this.pedalled.sort((a, b) => a - b);
    }
    const staffKey = (staffInfo ? staffInfo.notes.map((n) => n.midi + n.name).join(",") + COLOUR.mode + fontState.smufl : "none" + fontState.smufl) +
                     "|" + (staffInfo ? this.pedalled.join(",") : "");
    if (staffKey !== this.staffKey || this.needsRedraw) {
      drawStaff(this.staff, staffInfo, new Set(this.pedalled));
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
    // Pedal mark: "Ped." while down; on release the up mark, fading over PEDAL_UP_FADE seconds.
    const sinceChange = t - pedal.changedAt;
    const mark = sustain ? "down" : sinceChange < PEDAL_UP_FADE ? "up" : "";
    const pedalKey = mark + fontState.smufl;
    if (pedalKey !== this.pedalKey || this.needsRedraw) {
      drawPedalMark(this.pedal, mark);
      this.pedal.tex.needsUpdate = true;
      this.pedalKey = pedalKey;
    }
    this.pedal.mat.opacity = mark === "down" ? 1 : mark === "up" ? clamp(1 - sinceChange / PEDAL_UP_FADE, 0, 1) : 0;
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

// ----------------------------------------------------------- notes engine --
// A note sounds while its key is held, or after release while the pedal (CC64) is down.
// Scheme events keep the spec's guarantees: every noteOn gets exactly one noteEnd, a repeat strike
// ends the previous sound first, and noteRelease comes at most once per strike, before its noteEnd.
// Only notes on the 88 keys (21..108) reach the schemes.
const sounding = new Map();  // midi -> { held, vel, t0, inRange, releasedAt }
const soundingNotes = sounding;  // an unshadowed name for code with a local "sounding" flag (overlay.update)
let sustain = false;
let detectDirty = true;
let lastInfo = null;
const pcHistory = new Array(12).fill(0);  // decaying pitch-class weights: the key guess spells lone notes
let pcHistoryAt = 0;
let keyGuess = null;
const stats = { noteOns: 0 };

function noteOn(m, vel) {
  if (vel <= 0) { noteOff(m); return; }
  const t = clock();
  const prev = sounding.get(m);
  if (prev && prev.inRange) schemeHost.emit("noteEnd", m, t);  // a repeated note ends its previous sound
  const inRange = m >= KEY.first && m <= KEY.last;
  sounding.set(m, { held: true, vel, t0: t, inRange, releasedAt: null });
  if (inRange) {
    schemeHost.emit("noteOn", m, vel, t);
    const k = keys.get(m);
    k.target = 0.17 + 0.27 * (vel / 127);  // velocity-scaled key depth (world units at the key front)
    k.glowTarget = 0.5 + 0.5 * (vel / 127);
    noteColor(m, vel, k.color);
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
  const k = keys.get(m);
  if (k) { k.target = 0; k.glowTarget = sustain ? 0.2 : 0; }
  if (!sustain) {
    if (st.inRange) schemeHost.emit("noteEnd", m, t);
    sounding.delete(m);
  } else {
    st.releasedAt = t;
    if (st.inRange) schemeHost.emit("noteRelease", m, t);
  }
  detectDirty = true;
}
// value: the raw CC64 value (0..127) when it came from MIDI; Space and the Demo pass none.
function setSustain(on, value = on ? 127 : 0) {
  if (sustain === on) return;
  sustain = on;
  const t = clock();
  pedal.changedAt = t;
  schemeHost.emit("pedal", on, value, t);
  if (!on) {
    for (const [m, st] of sounding) {
      if (st.held) continue;
      if (st.inRange) schemeHost.emit("noteEnd", m, t);
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
    if (st.inRange) schemeHost.emit("noteEnd", m, t);
    const k = keys.get(m);
    if (k) { k.target = 0; k.glowTarget = 0; }
  }
  sounding.clear();
  if (sustain) {
    sustain = false;
    pedal.changedAt = t;
    schemeHost.emit("pedal", false, pedal.raw ?? 0, t);
  }
  detectDirty = true;
}

// ---------------------------------------------------------------- sustain --
// CC64 with polarity, then hysteresis: down at >= 64, up below 40, and 40..63 keeps the last state,
// so half-pedal chatter never flips it. Inverted polarity reads the value as 127 - value.
const PEDAL_POLARITY_KEY = "arsenal.piano.pedalPolarity";
const PEDAL_DOWN_AT = 64, PEDAL_UP_BELOW = 40;
const PEDAL_HINT = "Pedal reads as held. If it isn't, flip Pedal polarity.";
const pedal = {
  polarity: safeGet(PEDAL_POLARITY_KEY) === "inverted" ? "inverted" : "normal",
  raw: null,             // the last raw CC64 value, or null before any arrives
  changedAt: -1e9,       // page-clock time of the last down/up change (the overlay fades the release mark from it)
  awaitingFirst: true,   // the next CC64 is the first since an input was bound
  hintTimer: 0,
  hints: 0,              // how many times the polarity hint was shown
};
function pedalReadsDown(raw) {
  const v = pedal.polarity === "inverted" ? 127 - raw : raw;
  if (v >= PEDAL_DOWN_AT) return true;
  if (v < PEDAL_UP_BELOW) return false;
  return sustain;
}
function onPedalCC(raw) {
  pedal.raw = raw;
  const down = pedalReadsDown(raw);
  if (pedal.awaitingFirst) {
    pedal.awaitingFirst = false;
    if (down) armPedalHint();
  }
  setSustain(down, raw);
}
// The first CC64 after binding read down. If no note follows within 3 s and it still reads down,
// the pedal is probably wired the other way round: say so once.
function armPedalHint() {
  clearTimeout(pedal.hintTimer);
  const onsAtArm = stats.noteOns;
  pedal.hintTimer = setTimeout(() => {
    if (stats.noteOns !== onsAtArm || !sustain || pedal.raw === null || !pedalReadsDown(pedal.raw)) return;
    pedal.hints++;
    toast(PEDAL_HINT);
  }, 3000);
}
function resetPedalBinding() {
  clearTimeout(pedal.hintTimer);
  pedal.awaitingFirst = true;
}
function setPedalPolarity(polarity, persist = true) {
  pedal.polarity = polarity === "inverted" ? "inverted" : "normal";
  if (persist) safeSet(PEDAL_POLARITY_KEY, pedal.polarity);
  syncPolarityButton();
  // Re-read the pedal where it is now, so flipping fixes a stuck sustain at once.
  if (pedal.raw !== null) setSustain(pedalReadsDown(pedal.raw), pedal.raw);
}
function pedalText() {
  return (sustain ? "down" : "up") + (pedal.raw !== null ? ` · CC64 ${pedal.raw}` : "") +
         (pedal.polarity === "inverted" ? " · inverted" : "");
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
  if (midi.bound.map((i) => i.id).join(",") !== before) {
    allNotesOff();  // no stuck notes across a switch
    resetPedalBinding();
  }
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
    if (d[1] === 64) onPedalCC(d[2]);
    else if (d[1] === 120 || d[1] === 123) allNotesOff();
  } else {
    return;  // clock, aftertouch, pitch bend: not drawn
  }
  midi.events++;
  midi.last = [...d].map((b) => b.toString(16).padStart(2, "0")).join(" ");
}

// --------------------------------------------------------- computer keys --
// Tracker layout by physical key (event.code), so it works on any keyboard language:
// lower rows Z-/ with D G J L ; play C3-E4; upper rows Q-P with the number row play C4-E5.
// S cycles schemes (PIANO-V2-SPEC.md), so C#3 left the lower row the way G#3 did for H.
// H is the HUD and F is fullscreen, so G#3 (the H key in this layout) lives only in the upper row.
const KEYMAP = {
  KeyZ: 0, KeyX: 2, KeyD: 3, KeyC: 4, KeyV: 5, KeyG: 6, KeyB: 7, KeyN: 9, KeyJ: 10, KeyM: 11,
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
function syncSchemeUi() {
  const select = $("scheme-select");
  const list = schemeHost.list().map((s) => ({ id: s.id, name: (schemeHost.entries.get(s.id) || s).name }));
  const signature = list.map((s) => `${s.id}:${s.name}`).join("|");
  if (select.dataset.list !== signature) {
    select.textContent = "";
    for (const s of list) {
      const o = document.createElement("option");
      o.value = s.id;
      o.textContent = s.name;
      select.append(o);
    }
    select.dataset.list = signature;
  }
  if (schemeHost.activeId) select.value = schemeHost.activeId;
}
function syncPolarityButton() {
  const b = $("btn-polarity");
  b.textContent = pedal.polarity;
  b.setAttribute("aria-pressed", String(pedal.polarity === "inverted"));
}
function schemeHudText(t) {
  const entry = schemeHost.active();
  if (!entry) return schemeHost.pending.size ? "loading…" : "none";
  const s = schemeHost.call(entry, "stats", [t]);
  return entry.name + (s && s.trailsLive !== undefined ? ` · ${s.trailsLive} live / cap ${s.trailCap}` : "") +
         (s && s.energy !== undefined ? ` · energy ${s.energy}` : "");
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
  schemeFrame.framing = framingInfo();
  schemeHost.resize();
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
  $("hud-pedal").textContent = pedalText();
  $("hud-scheme").textContent = schemeHudText(t);
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
  $("scheme-select").addEventListener("change", (e) => {
    const id = e.target.value;
    e.target.blur();  // S and the note keys must keep working after a pick
    schemeHost.select(id).then((ok) => { if (!ok) syncSchemeUi(); });
  });
  $("btn-polarity").addEventListener("click", () => setPedalPolarity(pedal.polarity === "inverted" ? "normal" : "inverted"));
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
    if (e.code === "KeyS") { e.preventDefault(); if (!e.repeat) schemeHost.cycle(); return; }
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
// The frame handed to the active scheme's update(); one object, refreshed in place every frame.
const schemeFrame = { info: null, sounding, pedalDown: false, framing: framingInfo(), view };
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
  schemeFrame.info = info;
  schemeFrame.pedalDown = sustain;
  schemeHost.update(dt, t, schemeFrame);  // only the active scheme; before the composer renders

  let count = 0;
  glowMix.setRGB(0, 0, 0);
  for (const [m, st] of sounding) { glowMix.add(noteColor(m, st.vel, tmpColor)); count++; }
  if (count) glowMix.multiplyScalar(1 / count);
  else glowMix.setRGB(0.05, 0.08, 0.2);
  tmpColor.copy(STAGE_DARK).lerp(glowMix, count ? 0.03 * Math.min(1, count / 4) : 0);
  stageTint.lerp(tmpColor, 1 - Math.exp(-dt / 0.6));
  scene.background.copy(stageTint);
  scene.fog.color.copy(stageTint);

  overlay.update(info, t, dt);
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
  snapshot(type = "image/jpeg", quality = 0.9) { renderFrame(); return canvas.toDataURL(type, quality); },
  stats() {
    const info = currentInfo();
    const active = schemeHost.active();
    const s = (active && schemeHost.call(active, "stats", [clock()])) || {};
    return { fps: Math.round(fpsValue), framing: framing.id, sounding: [...sounding.keys()].sort((a, b) => a - b),
             chord: info ? info.name : null, label: overlay.shown ? overlay.shown.name : null,
             notes: info ? info.notes.map((n) => n.name + n.octave) : [], trailsLive: s.trailsLive ?? null,
             trailCap: s.trailCap ?? null, pedal: sustain, pedalRaw: pedal.raw, pedalPolarity: pedal.polarity,
             scheme: schemeHost.activeId, key: keyGuess ? keyGuess.name : null, rec: rec.state,
             fonts: { ...fontState }, demo: demo.running, noteOns: stats.noteOns };
  },
  // schemes (PIANO-V2-SPEC.md section 1)
  schemes() {
    return schemeHost.list().map((s) => ({ id: s.id, name: (schemeHost.entries.get(s.id) || s).name,
                                            active: s.id === schemeHost.activeId }));
  },
  selectScheme(id) { return schemeHost.select(id); },
  // For tests and scheme development: register a scheme module object without a file. It joins the
  // picker for this page load only; re-registering an id disposes the old instance.
  registerScheme(module) { return schemeHost.register(module); },
  schemeEvents() {
    return { counts: { ...schemeHost.counts }, log: schemeHost.log.map((e) => [...e]),
             loaded: [...schemeHost.entries.keys()], errors: Object.fromEntries(schemeHost.errors) };
  },
  // sustain (PIANO-V2-SPEC.md section 2)
  pedalState() {
    return { down: sustain, raw: pedal.raw, polarity: pedal.polarity, hints: pedal.hints,
             awaitingFirst: pedal.awaitingFirst, text: pedalText() };
  },
  setPedalPolarity(polarity) { setPedalPolarity(polarity); return pedal.polarity; },
  // the staff layer's box, its note heads (x, y = centre) and accidentals (x, y = top-left of the
  // measured ink), in canvas pixels
  staffHeads() {
    const layer = overlay.staff;
    if (!layer) return null;
    const { cx, cy, w, h } = layer.spec;
    const x0 = cx - w / 2, y0 = cy - h / 2;
    return { box: { x: x0, y: y0, w, h }, opacity: layer.mat.opacity,
             heads: (layer.heads || []).map((hd) => ({ ...hd, x: x0 + hd.x, y: y0 + hd.y })),
             accidentals: (layer.accidentals || []).map((a) => ({ ...a, x: x0 + a.x, y: y0 + a.y })) };
  },
  pedalMark() {
    const layer = overlay.pedal;
    if (!layer) return null;
    const { cx, cy, w, h } = layer.spec;
    return { kind: overlay.pedalKey.replace(/(true|false)$/, ""), opacity: +layer.mat.opacity.toFixed(3),
             box: { x: cx - w / 2, y: cy - h / 2, w, h } };
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
};

function boot() {
  wireUi();
  applyFraming(framing.id, false);
  syncDemoButton();
  syncRecButton();
  syncPolarityButton();
  syncSchemeUi();
  loadFonts();
  (async () => {
    let state = "prompt";
    try { state = (await navigator.permissions.query({ name: "midi" })).state; } catch { /* not queryable */ }
    if (state === "denied") setMidiStatus("MIDI permission denied: allow it in site settings");
    else connectMIDI();
  })();
  listAudioInputs().catch(() => {});
  $("boot").hidden = true;
  requestAnimationFrame(loop);
  // The stage renders at once; the scheme joins when its module has loaded (a local file, so quickly).
  const stored = safeGet(SCHEME_KEY);
  const first = schemeHost.list().some((s) => s.id === stored) ? stored : SCHEMES[0].id;
  (async () => {
    let ok = await schemeHost.select(first, false);
    if (!ok && first !== SCHEMES[0].id) ok = await schemeHost.select(SCHEMES[0].id, false);
    window.__piano.ready = true;
    if (ok) await schemeHost.preloadOthers();
  })();
}
boot();
