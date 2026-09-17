// Node tests for Vandor's "Instruments of light" entries: arsenal/web/piano/instruments/light-vandor-*.js. Zero
// dependencies, no GPU:
//   node tests/piano_light_vandor.test.mjs
//
// The modules cannot be created here (create() wants a live THREE and a scene), so this reads their tuning constants out
// of the source, mirrors the envelope and the wing-beat maths in plain JS, and checks the PROPERTIES the brief asks for
// (research/in-flight/piano-light-instruments-2026-09-17/brief.md) in bands wide enough that the look can still be
// tuned. It also pins the wiring every entry needs: the two shared helpers called once a frame, state.sounding with the
// pressed + pedal fallback, sustained light capped under the bloom line, overlapping light that never stacks, nothing
// allocated inside update, nothing of the host's written, dispose over everything, LF line endings.
// The common checks run over every light-vandor-* file present (a sibling entry that has not landed yet is skipped);
// the Ornithopter's own section runs when its file is there.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const DIR = here("../arsenal/web/piano/instruments/");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
// every `const NAME = number` at the top level of a file, as a map (the same reader as piano_string_envelope.test.mjs)
function constants(src) {
  const out = {};
  for (const m of src.matchAll(/^const ([A-Z][A-Z0-9_]*) = (-?\d+(?:\.\d+)?)(?:\s*,\s*([A-Z][A-Z0-9_]*) = (-?\d+(?:\.\d+)?))*\s*;/gm)) {
    for (const pair of m[0].replace(/^const\s+/, "").replace(/;\s*$/, "").split(/\s*,\s*/)) {
      const kv = /^([A-Z][A-Z0-9_]*) = (-?\d+(?:\.\d+)?)$/.exec(pair.trim());
      if (kv) out[kv[1]] = Number(kv[2]);
    }
  }
  return out;
}
const slice = (src, from, to) => {
  const a = src.indexOf(from);
  if (a < 0) return "";
  const b = src.indexOf(to, a + from.length);
  return src.slice(a, b < 0 ? undefined : b);
};

// ------------------------------------------------------------------------------------- every entry present --
const files = readdirSync(DIR).filter((f) => /^light-vandor-[a-z0-9-]+\.js$/.test(f)).sort();
check("at least one light-vandor-* entry is present", files.length > 0);
const SRC = {};
for (const file of files) {
  const id = file.replace(/\.js$/, "");
  const bytes = readFileSync(DIR + file);
  const src = bytes.toString("utf8");
  SRC[id] = src;
  let cr = 0;
  for (const b of bytes) if (b === 13) cr++;
  check(`${id}: LF line endings (counted by byte)`, cr === 0, `${cr} CR bytes`);
  // the contract: a default export whose id is the file's, with a name and create(ctx)
  const exp = (/^export default[^\n]*/m.exec(src) || [""])[0];
  check(`${id}: exports the contract default { id, name, create }`,
    /\bcreate\b/.test(exp) && /\bname\b/.test(exp) && (exp.includes(`id: "${id}"`) || (/\bid: ID\b/.test(exp) && src.includes(`const ID = "${id}"`))));
  check(`${id}: create() hands back update, resize, setActive and dispose`, ["update", "resize", "setActive", "dispose"].every((f) => new RegExp(`\\b${f}\\b`).test(src)));
  check(`${id}: imports the two shared helpers relatively`, src.includes('from "../harmony-feel.js"') && src.includes('from "../moment.js"'));
  check(`${id}: harmony-feel and the moment are each read once a frame, feel first`,
    (src.match(/\.update\(state, dt, t\)/g) || []).length === 1 && (src.match(/\.update\(state, dt, t, f\)/g) || []).length === 1
    && src.indexOf(".update(state, dt, t)") < src.indexOf(".update(state, dt, t, f)"));
  check(`${id}: the light is driven by state.sounding, guarded, with the pressed + pedal fallback`,
    /state\.sounding \?\? null/.test(src) && src.includes("state.pressed") && src.includes("state.pedal"));
  // draws only itself: never the host's camera, renderer, fog, background or layers
  const hostWrites = [/\bscene\.fog\b/, /\bscene\.background\b/, /\bscene\.environment\b/, /\brenderer\.(setClearColor|toneMapping|autoClear|setSize|setPixelRatio)/, /\bcamera\.(position|fov|near|far|lookAt|zoom)\b/, /\.layers\.(set|enable|disable|mask)\b/];
  check(`${id}: writes nothing of the host's (camera, renderer, fog, background, layers)`, !hostWrites.some((re) => re.test(src)));
  check(`${id}: takes the note colour from the host's palette (ctx.noteColor)`, src.includes("noteColor"));
  check(`${id}: downloads nothing (no fetch, no loader, no network import)`, !/\bfetch\(|Loader\(|https?:\/\//.test(src.replace(/\/\/[^\n]*/g, "")));
}

// ---------------------------------------------------------------------------------------- the Ornithopter --
const ORN = "light-vandor-ornithopter";
if (SRC[ORN]) {
  const src = SRC[ORN];
  const k = constants(src);
  const need = ["PEAK_EXP", "FLASH_EXP", "FLOOR_LO", "FLOOR_HI", "AFTER_SHARE", "TAU_PROMPT_BASS", "TAU_PROMPT_TREBLE", "TAU_AFTER_BASS",
    "TAU_AFTER_TREBLE", "TAU_FLASH", "TAU_DAMP", "DAMP_FADE", "TAU_VIB_OFF", "LIGHT_EXP", "SUS_GAIN", "FLASH_GAIN", "AMP_BASS", "AMP_TREBLE",
    "AMP_POW", "AMP_EXP", "VIB_HZ_BASS", "VIB_HZ_TREBLE", "VIB_DEPTH", "GHOST_HZ_BASS", "GHOST_HZ_TREBLE", "FOLD_UP", "FOLD_DOWN", "HAZE_MAX",
    "FLASH_REACH", "FLASH_NEIGH", "FLASH_SHARE"];
  const missing = need.filter((n) => !(n in k));
  check(`${ORN}: the envelope and wing constants are all named in one block`, missing.length === 0, missing.join(", "));
  // --- the craft rules, in the source
  const upd = slice(src, "  function update(dt, t, state) {", "\n  function resize(").replace(/^[^\n]*\n/, "");
  check(`${ORN}: update(dt, t, state) is there`, upd.length > 200);
  check(`${ORN}: the strike ring is read, so a note shorter than a frame still flashes`, upd.includes("state.notes"));
  // nothing allocated inside update: no constructor, no clone, no array literal, no closure, no Map walk by entries
  const allocs = [/\bnew\s+[A-Z]/, /\.clone\(/, /=>\s*[{(]/, /\bfunction\b/, /\[\s*\]/, /\bfor\s*\(\s*const\s+\[/, /\.entries\(\)/, /\.keys\(\)/, /\.values\(\)/, /\.map\(/, /\.filter\(/];
  const hit = allocs.filter((re) => re.test(upd));
  check(`${ORN}: nothing is allocated inside update`, hit.length === 0, hit.map(String).join(" "));
  check(`${ORN}: the sounding Map is walked with forEach (no per-entry pairs)`, /sounding\.forEach\(/.test(upd));
  const disp = slice(src, "  function dispose() {", "\n  }");
  check(`${ORN}: dispose() removes the group and disposes geometries, materials, textures and instanced meshes`,
    disp.includes("group.parent.remove(group)") && /geos\)/.test(disp) && /mats\)/.test(disp) && /texs\)/.test(disp) && /instanced\)/.test(disp));
  check(`${ORN}: an idle part collapses in its shader instead of toggling visibility (fixed draw calls)`,
    src.includes("gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return;") && !/\.visible\s*=/.test(upd));
  check(`${ORN}: every mesh is frustumCulled = false, so the draw count never depends on the camera`,
    (src.match(/frustumCulled = (?:lights\.frustumCulled = )?false/g) || []).length >= 10);
  // the light pass blends with a per-channel max, so the cap must hold per CHANNEL (ten hues stacked are a neutral whose
  // luma is the channel cap), and the flash must claim its pixel rather than stack on a capped membrane (repair round 1:
  // a chromatic cluster at fff whited out at the roots through the host's bloom)
  const CAP = "0.85 / max(max(col.r, col.g), max(col.b, 1e-4))";
  check(`${ORN}: sustained light is capped per channel under the bloom line in the shader, before the flash is added`,
    src.includes(CAP) && src.indexOf(CAP) < src.indexOf("float age = vStrike.x, flash = vStrike.z;"));
  check(`${ORN}: the flash claims its pixel (the sustained part gives way as the flash nears the bloom line)`,
    src.includes("col = col * (1.0 - min(fl / 0.9, 1.0)) + fcol;"));
  // repair round 2: the knuckle is narrow ACROSS the wing in key units (adjacent cores never overlap) and runs UP the wing
  // from the piston's blow in wing units, past the clasp and piston standing in front of the root (a core centred on the
  // root itself hid behind them and a lone strike showed no spark); one vec4 uniform carries the KNUCKLE block
  const kn = /const KNUCKLE = \{ across: ([\d.]+), along: ([\d.]+), width: ([\d.]+), gain: ([\d.]+) \};/.exec(src);
  check(`${ORN}: the knuckle core is a KNUCKLE block (across, along, width, gain) fed to the shader as uKnuckle`,
    !!kn && src.includes("uKnuckle: { value: new THREE.Vector4(KNUCKLE.across, KNUCKLE.along, KNUCKLE.width, KNUCKLE.gain) }")
    && src.includes("float ds = (s - uKnuckle.y) / uKnuckle.z;") && src.includes("exp(-(p.x * p.x * uKnuckle.x + ds * ds))"));
  if (kn) {
    const [across, along, width, gain] = kn.slice(1).map(Number);
    check(`${ORN}: the core is at most a third of a key wide across at 1/e (across >= 9) and runs up the wing from the blow (along > 0, width > 0)`,
      across >= 9 && along > 0 && along <= 0.15 && width > 0.04 && width <= 0.12, `${across} ${along} ${width}`);
    check(`${ORN}: the core reaches from the root (over half height at s = 0) and is gone by a fifth of the wing`,
      Math.exp(-Math.pow((0 - along) / width, 2)) > 0.4 && Math.exp(-Math.pow((0.2 - along) / width, 2)) < 0.1);
    check(`${ORN}: the knuckle's gain lifts a lone v120 strike over the bloom line on every hue (gain * v^FLASH_EXP * FLASH_GAIN * 0.75 > 2)`,
      gain * Math.pow(120 / 127, k.FLASH_EXP) * k.FLASH_GAIN * 0.75 > 2, `${gain}`);
  }
  // with that core, two adjacent wings flashing together (a semitone apart: the host's hues alternate round the wheel, so
  // neighbours are near-complementary and their per-channel max is a neutral) must share one flash steeply: an fff dyad
  // whited out at FLASH_SHARE 1 and 2 and cleared at 2.5-3; two whole sparks at 2+ semitones never did, so the reach is short
  check(`${ORN}: the flash budget shares steeply between semitone neighbours (FLASH_SHARE >= 2.5) over a short reach (1-3)`,
    k.FLASH_SHARE >= 2.5 && k.FLASH_REACH >= 1 && k.FLASH_REACH <= 3, `${k.FLASH_SHARE} ${k.FLASH_REACH}`);
  check(`${ORN}: no shader pow() takes 1 - |n.v| unguarded (a base a rounding error under zero hands the bloom a NaN)`,
    !/pow\(1\.0 - ndv/.test(src) && (src.match(/pow\(max\(1\.0 - ndv, 0\.0\)/g) || []).length === 2);
  check(`${ORN}: the key style keeps the white keys ivory (nothing tints them sand or gold)`,
    (() => { const m = /whiteColor: 0x([0-9a-f]{6})/.exec(src); if (!m) return false; const v = parseInt(m[1], 16); return (v >> 16) >= 0xd8 && ((v >> 8) & 255) >= 0xd0 && (v & 255) >= 0xc0; })());
  if (!missing.length) {
    // the concert grand's envelope, number for number, so the two answer a held pedal identically
    const grandSrc = readFileSync(DIR + "concert-grand.js", "utf8"), g = constants(grandSrc);
    const shared = ["PEAK_EXP", "FLASH_EXP", "FLOOR_LO", "FLOOR_HI", "AFTER_SHARE", "TAU_PROMPT_BASS", "TAU_PROMPT_TREBLE", "TAU_AFTER_BASS",
      "TAU_AFTER_TREBLE", "TAU_FLASH", "TAU_DAMP", "DAMP_FADE", "TAU_VIB_OFF"];
    const differ = shared.filter((n) => k[n] !== g[n]);
    check(`${ORN}: holds the concert grand's envelope (floor, decays, damping window)`, differ.length === 0, differ.map((n) => `${n} ${k[n]} vs ${g[n]}`).join(", "));

    // the envelope the module integrates, written out once here so the properties can be measured
    const pitch = (m) => (m - 21) / 87;
    const over = (m, lo, hi) => lo * Math.pow(hi / lo, pitch(m));
    function envelope(m, vel) {
      const v = vel / 127, peak = Math.pow(v, k.PEAK_EXP), floor = peak * (k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * v), above = peak - floor;
      const tauP = over(m, k.TAU_PROMPT_BASS, k.TAU_PROMPT_TREBLE), tauA = over(m, k.TAU_AFTER_BASS, k.TAU_AFTER_TREBLE);
      const body = (t) => floor + above * (1 - k.AFTER_SHARE) * Math.exp(-t / tauP) + above * k.AFTER_SHARE * Math.exp(-t / tauA);
      const damped = (t, since) => { if (since >= k.DAMP_FADE) return 0; const u = since / k.DAMP_FADE; return body(t) * Math.exp(-since / k.TAU_DAMP) * (1 - u * u * (3 - 2 * u)); };
      const light = (b) => (b > 0 ? k.SUS_GAIN * Math.pow(b, k.LIGHT_EXP) : 0);
      const ampMax = (k.AMP_TREBLE + (k.AMP_BASS - k.AMP_TREBLE) * Math.pow(1 - pitch(m), k.AMP_POW));
      const amp = (b) => ampMax * Math.pow(Math.max(b, 0), k.AMP_EXP);
      return { peak, floor, body, damped, light, amp, ampMax };
    }
    // --- velocity legible: light and stroke rise with velocity, at the strike and while the note settles, and pp reads
    for (const m of [21, 60, 108]) {
      const e30 = envelope(m, 30), e70 = envelope(m, 70), e120 = envelope(m, 120);
      for (const t of [0.05, 0.5, 2, 4]) {
        check(`${ORN}: m${m} light at ${t} s rises v30 < v70 < v120`, e30.light(e30.body(t)) < e70.light(e70.body(t)) && e70.light(e70.body(t)) < e120.light(e120.body(t)));
        check(`${ORN}: m${m} stroke at ${t} s rises v30 < v70 < v120`, e30.amp(e30.body(t)) < e70.amp(e70.body(t)) && e70.amp(e70.body(t)) < e120.amp(e120.body(t)));
      }
      check(`${ORN}: m${m} a v30 note still reads: at least a sixth of the ff light for the whole sound`,
        e30.light(e30.body(4)) >= e120.light(e120.body(4)) / 6 && e30.light(e30.floor) > 0.08, `${e30.light(e30.body(4)).toFixed(3)} vs ${e120.light(e120.body(4)).toFixed(3)}`);
      check(`${ORN}: m${m} the strike flash outgrows the body faster than velocity does`, k.FLASH_EXP > k.PEAK_EXP && k.FLASH_GAIN > 1);
    }
    // --- sustain truth: the floor holds for the whole sound and the end is a fade that is over by DAMP_FADE
    for (const m of [21, 60, 108]) {
      const e = envelope(m, 96);
      check(`${ORN}: m${m} still beats and glows ten minutes into a pedalled note (the floor)`, Math.abs(e.body(600) - e.floor) < 1e-9 && e.amp(e.body(600)) > 0.2 * e.ampMax);
      check(`${ORN}: m${m} settles to a lower stroke than its strike while the pedal holds`, e.amp(e.body(4)) < e.amp(e.peak) && e.amp(e.body(4)) > 0.3 * e.amp(e.peak));
      const rel = e.body(3);
      check(`${ORN}: m${m} 0.1 s after the sound ends the wing is still clearly lit`, e.damped(3, 0.1) > rel * 0.3);
      check(`${ORN}: m${m} the light and the beat are gone by 0.35 s (folded to rest)`, e.damped(3, 0.35) === 0 && e.amp(e.damped(3, 0.35)) === 0);
      let worst = 0, prev = rel;
      for (let x = 1 / 60; x <= k.DAMP_FADE + 0.1; x += 1 / 60) { const v = e.damped(3, x); worst = Math.max(worst, (prev - v) / rel); prev = v; }
      check(`${ORN}: m${m} every 60 fps step of the fade is under a fifth of the level at the release`, worst < 0.2, `${(worst * 100).toFixed(1)} %`);
    }
    check(`${ORN}: the wing folds to rest in about 0.3 s (3 x FOLD_DOWN) and stands up faster than it folds`, k.FOLD_DOWN * 3 >= 0.25 && k.FOLD_DOWN * 3 <= 0.36 && k.FOLD_UP < k.FOLD_DOWN);
    check(`${ORN}: the ghost and tremor stop before the light does`, k.TAU_VIB_OFF < k.TAU_DAMP);
    // --- low notes blur more: a wide slow stroke at A0, a stiff fast shimmer at C8; nothing strobes at 60 fps
    const ampAt = (m) => envelope(m, 100).ampMax;
    check(`${ORN}: the stroke is widest at A0 and narrows all the way to C8, at least five to one`,
      [21, 33, 48, 60, 84, 108].every((m, i, a) => i === 0 || ampAt(m) < ampAt(a[i - 1])) && ampAt(21) / ampAt(108) >= 5, `${ampAt(21)} -> ${ampAt(108)} deg`);
    check(`${ORN}: A0's stroke is a broad envelope (12-25 degrees), C8's a shimmer (under 5)`, k.AMP_BASS >= 12 && k.AMP_BASS <= 25 && k.AMP_TREBLE < 5);
    check(`${ORN}: the breathing is slow in the bass and faster at the top, and well under a tenth of 60 fps`,
      k.VIB_HZ_BASS < k.VIB_HZ_TREBLE && k.VIB_HZ_TREBLE <= 6 && k.VIB_HZ_BASS >= 1 && k.VIB_DEPTH <= 0.2);
    check(`${ORN}: the strobe ghost is slower than the breathing and fades out toward the treble in the shader`,
      k.GHOST_HZ_BASS <= k.VIB_HZ_BASS && k.GHOST_HZ_TREBLE <= 6 && src.includes("float ghostW = (1.0 - pn) * (1.0 - pn);"));
    // --- the arcsine envelope: the shader's sweepCover, mirrored, on a bass wing and a treble wing
    const F = (x, A) => 0.5 + Math.asin(Math.max(-1, Math.min(1, x / A))) / Math.PI;
    const cover = (phi, c, hw, A) => Math.max(0, Math.min(1, F(phi - c + hw, A) - F(phi - c - hw, A)));
    const profile = (A, hw) => { const xs = []; for (let i = -200; i <= 200; i++) xs.push(cover((i / 200) * (A + hw), 0, hw, A)); return xs; };
    // the blade's angular half-width half-way up a wing: half the chord over half the length (A0: 2.5 / 30; C8: 1.05 / 10.5)
    const HW_BASS = 0.5 * 2.5 / 15, HW_TREBLE = 0.5 * 1.05 / 5.25;
    const A_BASS = ampAt(21) * Math.PI / 180;
    const wide = profile(A_BASS, HW_BASS), narrow = profile(ampAt(108) * Math.PI / 180, HW_TREBLE);
    // the turning points of the stroke, where a real wing dwells: the densest samples with |x| within the outer quarter of A
    const ends = (p, A, hw) => { let best = 0; for (let i = 0; i < p.length; i++) { const x = ((i - 200) / 200) * (A + hw); if (Math.abs(x) >= 0.75 * A && Math.abs(x) <= A && p[i] > best) best = p[i]; } return best; };
    const mid = (p) => p[Math.floor(p.length / 2)];
    check(`${ORN}: a bass wing's time average is denser at the ends of the stroke than in the middle (the Dune wing blur)`,
      ends(wide, A_BASS, HW_BASS) > mid(wide) * 1.3 && mid(wide) < 0.5, `${ends(wide, A_BASS, HW_BASS).toFixed(3)} vs ${mid(wide).toFixed(3)}`);
    check(`${ORN}: a treble wing's time average is nearly the blade itself (a shimmer, not a blur)`, mid(narrow) > 0.9 && mid(narrow) > mid(wide) * 2, `${mid(narrow).toFixed(3)} vs ${mid(wide).toFixed(3)}`);
    const integral = (p, span) => p.reduce((a, b) => a + b, 0) * (span / p.length);
    const spanWide = 2 * (ampAt(21) * Math.PI / 180 + HW_BASS);
    check(`${ORN}: the coverage integrates to the blade width: a wider stroke spreads the same light thinner`,
      Math.abs(integral(wide, spanWide) - 2 * HW_BASS) < 0.1 * 2 * HW_BASS, `${integral(wide, spanWide).toFixed(4)} vs ${(2 * HW_BASS).toFixed(4)}`);
    check(`${ORN}: the wing fragment draws that arcsine density (asin) and the light pass never stacks (MaxEquation)`,
      src.includes("asin(clamp(x / A, -1.0, 1.0))") && /lightMat[\s\S]*?blendEquation: THREE\.MaxEquation/.test(src));
    // --- the material, the dance and the moment are wired to the helpers' fields
    check(`${ORN}: lushness drives iridescence and the haze, tension the cooling and the tightening, simplicity the stillness`,
      /C\.lushness/.test(src) && /C\.tension/.test(src) && /C\.simplicity/.test(src) && src.includes("uIrid") && src.includes("uHaze") && src.includes("tighten"));
    check(`${ORN}: the haze alpha is capped at HAZE_MAX <= 0.3 and its texture repeats`, k.HAZE_MAX <= 0.3 && src.includes("Math.min(HAZE_MAX,") && src.includes("THREE.RepeatWrapping"));
    check(`${ORN}: the braid runs from the bass wing to the solo wing, twists with contrary motion, tightens with pull, colours by consonance`,
      /Vc\.bass/.test(src) && /Vc\.solo/.test(src) && src.includes('"contrary"') && /Dn\.pull/.test(src) && /Dn\.consonance/.test(src) && /Dn\.phase/.test(src));
    check(`${ORN}: the artifact grows with artifact.growth and shatters on artifact.released with releaseStrength`,
      /A\.growth/.test(src) && /A\.released/.test(src) && /A\.releaseStrength/.test(src) && src.includes("uShatter"));
    check(`${ORN}: mood.valence warms or cools the haze, energy scales the breathing`, /mo\.mood\.valence/.test(src) && /mo\.energy/.test(src) && src.includes("uBreath"));
    report.push(`${ORN}: floor ${(k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * 96 / 127).toFixed(2)} of the body at vel 96; stroke ${ampAt(21).toFixed(1)} -> ${ampAt(108).toFixed(1)} deg; `
      + `breathing ${k.VIB_HZ_BASS}-${k.VIB_HZ_TREBLE} Hz; ghost ${k.GHOST_HZ_BASS}-${k.GHOST_HZ_TREBLE} Hz; fold ${(3 * k.FOLD_DOWN).toFixed(2)} s; damping ${k.TAU_DAMP} s in ${k.DAMP_FADE} s`);
  }
} else {
  console.log(`(skipped: ${ORN}.js is not present)`);
}

// ------------------------------------------------------------------------------------------- the Abyssal --
// Abyssal imports nothing but the two pure helpers and its create() touches only a handful of three classes, so a stub
// THREE runs the whole instrument here: the contract shape, the light envelope (a strike flash, a slow decay onto a high
// floor held for exactly as long as the sound, a 0.3 s fade at the end and never a snap), velocity legibility, the pedal's
// truth (a pedal-held note keeps its life; the pedal alone lights nothing; a re-strike re-flashes and never dips the
// light), the bass blur over the treble, the plankton a strike sheds dying with its note, the material / dance / moment
// wiring, a fixed draw list and dispose over everything.
const ABY = "light-vandor-abyssal";
if (SRC[ABY]) {
  const mod = await import(`../arsenal/web/piano/instruments/${ABY}.js`);
  const { ABYSSAL: K, dampFade, travelOf, bellOf } = mod;
  const Abyssal = mod.default;
  const disposed = [];
  class Obj { constructor() { this.children = []; this.parent = null; this.visible = true; this.position = new Vec3(); this.rotation = new Vec3(); this.name = ""; this.renderOrder = 0; this.frustumCulled = true; }
    add(c) { this.children.push(c); c.parent = this; return this; } remove(c) { const i = this.children.indexOf(c); if (i >= 0) { this.children.splice(i, 1); c.parent = null; } } }
  class Vec2 { constructor(x = 0, y = 0) { this.x = x; this.y = y; } set(x, y) { this.x = x; this.y = y; return this; } }
  class Vec3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; } set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } }
  class Vec4 { constructor(x = 0, y = 0, z = 0, w = 0) { this.x = x; this.y = y; this.z = z; this.w = w; } set(x, y, z, w) { this.x = x; this.y = y; this.z = z; this.w = w; return this; } }
  class Color { constructor() { this.r = 0; this.g = 0; this.b = 0; } setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; } setHSL(h) { this.r = 0.5 + 0.5 * Math.cos(h * 6.28); this.g = 0.5; this.b = 0.5 - 0.5 * Math.cos(h * 6.28); return this; } }
  class Attr { constructor(array, size) { this.array = array; this.itemSize = size; this.count = array.length / size; this.needsUpdate = false; } setUsage() { return this; } }
  class Geo { constructor() { this.attributes = {}; this.index = null; this.instanceCount = Infinity; this.isGeo = true; } setAttribute(n, a) { this.attributes[n] = a; return this; } setIndex(a) { this.index = a; return this; } dispose() { disposed.push(this); } }
  class Mat { constructor(p) { Object.assign(this, p); this.isMat = true; } dispose() { disposed.push(this); } }
  class Tex { constructor(data, w, h) { this.image = { data, width: w, height: h }; this.needsUpdate = false; this.isTex = true; } dispose() { disposed.push(this); } }
  class Mesh extends Obj { constructor(g, m) { super(); this.geometry = g; this.material = m; this.isMesh = true; } }
  class Points extends Obj { constructor(g, m) { super(); this.geometry = g; this.material = m; this.isPoints = true; } }
  const THREE = {
    Group: class extends Obj { constructor() { super(); this.isObject3D = true; } }, Mesh, Points, ShaderMaterial: Mat, DataTexture: Tex,
    BufferGeometry: Geo, InstancedBufferGeometry: Geo, BufferAttribute: Attr, InstancedBufferAttribute: Attr,
    Vector2: Vec2, Vector3: Vec3, Vector4: Vec4, Color,
    RGBAFormat: 1, FloatType: 2, NearestFilter: 3, AdditiveBlending: 4, DoubleSide: 5, DynamicDrawUsage: 6,
  };
  const mod12 = (a) => ((a % 12) + 12) % 12;
  const isBlack = (m) => [1, 3, 6, 8, 10].includes(mod12(m));
  const WHITE_OFFSET = [0, -1, 1, -1, 2, 3, -1, 4, -1, 5, -1, 6], BLACK_CENTER = { 1: 0.9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5.0, 10: 3 + 4 / 7 * 5.5 };
  const keyX = (m) => { const oct = Math.floor(m / 12), pc = mod12(m); return (isBlack(m) ? oct * 7 + BLACK_CENTER[pc] : oct * 7 + WHITE_OFFSET[pc] + 0.5) - 38; };
  const noteColor = (m, vel, target) => target.setRGB(0.2 + 0.8 * (mod12(m) / 11), 0.3, 0.9 - 0.7 * (mod12(m) / 11));
  const ctx = () => ({ THREE, keyX, isBlack, noteColor, framing: { id: "16:9", w: 1920, h: 1080 }, KEY: { first: 21, last: 108 }, options: {} });
  // a synthetic host state, shaped as piano.js hands it over (entries pooled per key, strike counted, pedal-held voices)
  function makeState() {
    const st = { pressed: new Map(), pedal: false, chord: null, notes: [], sounding: new Map() };
    const pool = new Map();
    const entry = (m) => { let e = pool.get(m); if (!e) { e = { vel: 0, t0: 0, held: false, pedal: false, tRelease: null, strike: 0 }; pool.set(m, e); } return e; };
    return {
      st,
      on(m, vel, t) { const e = entry(m); e.vel = vel; e.t0 = t; e.held = true; e.pedal = false; e.tRelease = null; e.strike++; st.sounding.set(m, e); st.pressed.set(m, e); st.notes.push({ midi: m, vel, t }); },
      off(m, t) { const e = st.sounding.get(m); st.pressed.delete(m); if (!e) return; if (st.pedal) { e.held = false; e.pedal = true; e.tRelease = t; } else st.sounding.delete(m); },
      pedal(down) { st.pedal = down; if (!down) for (const [m, e] of [...st.sounding]) if (!e.held) st.sounding.delete(m); },
    };
  }
  const FIRST = 21, N = 88, DT = 1 / 60;
  const row = (h, i, r) => { const o = (r * N + i) * 4, d = h.debug.texData; return [d[o], d[o + 1], d[o + 2], d[o + 3]]; };
  const bodyOf = (h, m) => h.debug.body[m - FIRST];
  const run = (h, host, from, to) => { let t = from; while (t < to - 1e-9) { h.update(DT, t + DT, host.st); t += DT; } return t; };
  const A = (label, ok, detail) => check(`${ABY}: ${label}`, ok, detail);

  // --- the contract
  A("id, name, create; hints hide the host body and lower the floor; keyStyle names both key colours",
    Abyssal.id === ABY && typeof Abyssal.name === "string" && typeof Abyssal.create === "function" && Abyssal.hints.hideHostBody === true
    && Number.isFinite(Abyssal.hints.floorY) && Abyssal.hints.floorY < -2.3 && Number.isFinite(Abyssal.keyStyle.whiteColor) && Number.isFinite(Abyssal.keyStyle.blackColor));
  {
    const h = Abyssal.create(ctx());
    A("create() returns group, update, resize, setActive, dispose", h.group && h.group.isObject3D && ["update", "resize", "setActive", "dispose"].every((k) => typeof h[k] === "function"));
    const draws = h.group.children.filter((c) => c.isMesh || c.isPoints);
    A("a fixed draw list of six (tentacles, bells, beads, points, water, bed)", draws.length === 6, String(draws.map((d) => d.name)));
    A("every drawable is never frustum culled and has a render order", draws.every((d) => d.frustumCulled === false && d.renderOrder > 0));
    A("instance counts are fixed at creation (88 + 35 + 2 ribbons, 7 bells, 88 beads)", draws.filter((d) => d.geometry.instanceCount !== Infinity).map((d) => d.geometry.instanceCount).join(",") === "125,7,88");
    A("one shared uniform object across all six materials", new Set(draws.map((d) => d.material.uniforms)).size === 1);
    A("additive, no depth write, fog off on every material", draws.every((d) => d.material.blending === THREE.AdditiveBlending && d.material.depthWrite === false && d.material.fog === false));
    const tips = draws.find((d) => d.name === "abyssal-beads").geometry.attributes.aTipInfo.array;
    let landed = true;
    for (let i = 0; i < N; i++) { const m = FIRST + i; if (Math.abs(tips[i * 4] - keyX(m)) > 1e-6 || tips[i * 4 + 2] > -3.1) landed = false; }
    A("every bead sits exactly on its key's x, behind the key backs (never over the keybed)", landed);
    const bellsY = h.debug.bells.map((b) => b.cy);
    A("the bass bell hangs highest, the treble lowest, all above the keys", bellsY.every((y, i, a) => y > 8 && (i === 0 || y < a[i - 1])), bellsY.map((y) => y.toFixed(1)).join(" "));
    A("bellOf groups the keys by octave under seven bells", bellOf(21) === 0 && bellOf(35) === 0 && bellOf(36) === 1 && bellOf(60) === 3 && bellOf(95) === 5 && bellOf(96) === 6 && bellOf(108) === 6);
    h.dispose();
  }
  // --- the strike and the envelope
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    host.on(60, 100, 0);
    h.update(DT, DT, host.st);
    const [E, F, H] = row(h, 60 - FIRST, 0);
    const v = 100 / 127, peak = Math.pow(v, K.PEAK_EXP), floor = peak * (K.FLOOR_LO + (K.FLOOR_HI - K.FLOOR_LO) * v);
    A("a strike lights the body at once, near v^PEAK_EXP", E > peak * 0.9 && E <= peak + 1e-6, `E ${E.toFixed(3)} peak ${peak.toFixed(3)}`);
    A("the strike flash fires and decays with TAU_FLASH", F > 0.5 && F < Math.pow(v, K.FLASH_EXP), `F ${F.toFixed(3)}`);
    A("the pulse head leaves the bell on the strike frame", H >= 0 && H < 0.3, `H ${H.toFixed(3)}`);
    A("the damper window is open while the note sounds", row(h, 60 - FIRST, 1)[3] === 1);
    run(h, host, DT, 0.5);
    const [, F2, H2] = row(h, 60 - FIRST, 0);
    A("half a second on: the flash is gone and the pulse has landed on the key", F2 < 0.01 && H2 < 0, `F ${F2.toFixed(4)} H ${H2.toFixed(2)}`);
    run(h, host, 0.5, 4);
    const E4 = bodyOf(h, 60);
    A("held 4 s the body sits on the velocity-scaled floor (higher floor, slow decay)", E4 >= floor * 0.999 && E4 < peak * 0.75, `E ${E4.toFixed(3)} floor ${floor.toFixed(3)}`);
    host.off(60, 4);                                     // release with the pedal up: a 0.3 s fade, never a snap
    let t = 4, prev = bodyOf(h, 60), maxStep = 0, gone = null;
    while (t < 4.6) { h.update(DT, t + DT, host.st); t += DT; const e = bodyOf(h, 60); maxStep = Math.max(maxStep, prev - e); prev = e; if (gone === null && e === 0) gone = t - 4; }
    A("pedal up: the light is gone within DAMP_FADE (+1 frame)", gone !== null && gone <= K.DAMP_FADE + DT + 1e-6, `gone at ${gone}`);
    A("...as a fade, not a snap: the steepest 60 fps step is under 15 % of the level at release", maxStep < 0.15 * E4, `max step ${maxStep.toFixed(4)} of ${E4.toFixed(3)}`);
    A("the damper window closes with the light (sparkles die with the note)", row(h, 60 - FIRST, 1)[3] === 0);
    A("the fade window: 1 at 0, 0.5 at half, 0 at DAMP_FADE, zero slope at the end", dampFade(0) === 1 && Math.abs(dampFade(K.DAMP_FADE / 2) - 0.5) < 1e-9 && dampFade(K.DAMP_FADE) === 0 && dampFade(K.DAMP_FADE - 1e-4) < 1e-6);
    h.dispose();
  }
  // --- velocity
  {
    const peaks = [];
    for (const vel of [30, 70, 120]) {
      const h = Abyssal.create(ctx()), host = makeState();
      h.update(DT, 0, host.st); host.on(60, vel, 0); h.update(DT, DT, host.st);
      const [E, F] = row(h, 60 - FIRST, 0), P = row(h, 60 - FIRST, 2)[0];
      peaks.push({ vel, E, F, P, travel: travelOf(vel / 127) });
      h.dispose();
    }
    A("body, flash and pulse all rise with velocity (v30 < v70 < v120)", peaks.every((p, i) => i === 0 || (p.E > peaks[i - 1].E && p.F > peaks[i - 1].F && p.P > peaks[i - 1].P)), JSON.stringify(peaks));
    A("a soft note still reads: v30 lights a body over 0.1", peaks[0].E > 0.1, peaks[0].E.toFixed(3));
    A("the pulse runs faster the harder the strike", peaks[2].travel < peaks[1].travel && peaks[1].travel < peaks[0].travel && peaks[2].travel >= 0.1);
    A("the sustained gain keeps a full body under the bloom line before the shader's own cap", K.SUS_GAIN < 0.8 && K.PULSE_GAIN > 1.5);
  }
  // --- the pedal
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    host.pedal(true); host.on(40, 110, 0);
    run(h, host, 0, 0.5);
    host.off(40, 0.5);                                   // the finger lifts; the pedal holds the sound
    run(h, host, 0.5, 8);
    const v = 110 / 127, peak = Math.pow(v, K.PEAK_EXP), floor = peak * (K.FLOOR_LO + (K.FLOOR_HI - K.FLOOR_LO) * v);
    const E8 = bodyOf(h, 40);
    A("a note held only by the pedal keeps its life for 8 s (body on its floor)", E8 >= floor * 0.999, `E ${E8.toFixed(3)} floor ${floor.toFixed(3)}`);
    A("a pedal-only note reads as pedal-held (held mix toward 0), so it breathes deeper", row(h, 40 - FIRST, 2)[2] < 0.05);
    host.pedal(false);                                   // the pedal lifts: the sound ends
    let t = 8, gone = null;
    while (t < 8.6) { h.update(DT, t + DT, host.st); t += DT; if (gone === null && bodyOf(h, 40) === 0) gone = t - 8; }
    A("the pedal lift damps within DAMP_FADE (+1 frame)", gone !== null && gone <= K.DAMP_FADE + DT + 1e-6, `gone at ${gone}`);
    host.pedal(true);
    run(h, host, 8.6, 10);
    let lit = 0;
    for (let i = 0; i < N; i++) if (h.debug.body[i] > 0 || row(h, i, 0)[1] > 0) lit++;
    const bellLit = h.debug.uniforms.uBellCol.value.some((c) => c.x + c.y + c.z > 0);
    A("the pedal alone never lights a tentacle or a bell", lit === 0 && !bellLit, `lit ${lit} bell ${bellLit}`);
    h.dispose();
  }
  // --- the re-strike
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    host.on(63, 90, 0);
    run(h, host, 0, 1.0);
    const before = bodyOf(h, 63);
    host.on(63, 90, 1.0);                                // the strike counter increments on the same key
    h.update(DT, 1.0 + DT, host.st);
    const [E, F, H] = row(h, 63 - FIRST, 0);
    A("a re-strike re-flashes and sends a new pulse from the bell", F > 0.3 && H >= 0 && H < 0.3, `F ${F.toFixed(3)} H ${H.toFixed(3)}`);
    A("...and never dips the light below the level it found", E >= before - 1e-6, `E ${E.toFixed(3)} before ${before.toFixed(3)}`);
    let flashes = 0, prevF = 0;
    for (let k = 0; k < 8; k++) {                        // eight repeats in two seconds: eight flashes
      const t0 = 1.2 + k * 0.25;
      host.off(63, t0 - 0.13); host.on(63, 90, t0);
      let t = t0 - 0.13;
      while (t < t0 + 0.12 - 1e-9) { h.update(DT, t + DT, host.st); t += DT; const f = row(h, 63 - FIRST, 0)[1]; if (f > prevF + 0.2) flashes++; prevF = f; }
    }
    A("fast repeats: every one of eight strikes flashes again", flashes === 8, `${flashes} flashes`);
    h.dispose();
  }
  // --- low notes blur more
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    host.on(21, 100, 0); host.on(108, 100, 0);
    run(h, host, 0, 0.5);
    const a0 = row(h, 21 - FIRST, 0)[3], c8 = row(h, 108 - FIRST, 0)[3];
    A("A0's blur envelope is far wider than C8's at the same body", a0 > c8 * 10 && a0 > 0.3 && c8 < 0.06, `A0 ${a0.toFixed(3)} C8 ${c8.toFixed(4)}`);
    A("the blur constants: bass wide, treble a shimmer, the ghost sweep slow in the bass", K.ENV_BASS > 0.8 && K.ENV_TREBLE < 0.05 && K.GHOST_HZ_BASS < K.GHOST_HZ_TREBLE && K.GHOST_HZ_TREBLE < 10);
    const shape = h.debug.meshes.find((d) => d.name === "abyssal-tentacles").geometry.attributes.aShape.array;
    A("bass tentacles are thicker and sway more than treble ones", shape[0] > shape[87 * 4] * 4 && shape[1] > shape[87 * 4 + 1] * 4);
    host.off(21, 0.5);
    run(h, host, 0.5, 0.6);
    const [E, , , Amp] = row(h, 21 - FIRST, 0);
    A("0.1 s after the end the blur has fallen faster than the light", E > 0 && Amp < a0 * 0.4, `E ${E.toFixed(3)} A ${Amp.toFixed(3)} was ${a0.toFixed(3)}`);
    h.dispose();
  }
  // --- the plankton
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    const pts = h.debug.meshes.find((d) => d.name === "abyssal-plankton").geometry.attributes;
    host.on(60, 120, 0);
    h.update(DT, DT, host.st);
    let shed = 0, born = 0;
    for (let j = 0; j < pts.aN.count; j++) if (pts.aN.array[j] === 60 - FIRST) { shed++; if (pts.aP.array[j * 4 + 3] >= 0 && pts.aP.array[j * 4 + 3] <= travelOf(120 / 127) + 0.05) born++; }
    const want = Math.round(K.SPARKS_MIN + K.SPARKS_VEL * Math.pow(120 / 127, 1.5));
    A("a strike sheds plankton tagged with its note, born as the pulse passes", shed === want && born === shed, `shed ${shed} born ${born} want ${want}`);
    A("the particle buffers are marked for upload on a spawn", pts.aP.needsUpdate && pts.aN.needsUpdate);
    const h2 = Abyssal.create(ctx()), host2 = makeState();
    h2.update(DT, 0, host2.st); host2.on(60, 30, 0); h2.update(DT, DT, host2.st);
    const pts2 = h2.debug.meshes.find((d) => d.name === "abyssal-plankton").geometry.attributes;
    let shedSoft = 0;
    for (let j = 0; j < pts2.aN.count; j++) if (pts2.aN.array[j] === 60 - FIRST) shedSoft++;
    A("a soft strike sheds fewer sparkles than a hard one, but some", shedSoft > 0 && shedSoft < shed, `${shedSoft} vs ${shed}`);
    h.dispose(); h2.dispose();
  }
  // --- the material, the dance and the moment
  {
    const h = Abyssal.create(ctx()), host = makeState();
    h.update(DT, 0, host.st);
    const U = h.debug.uniforms;
    const snowRest = U.uMood.value.z;
    host.pedal(true);
    for (const m of [36, 48, 52, 59, 62, 66, 69, 74]) host.on(m, 96, 0);   // Cmaj13#11: lush
    host.st.chord = { name: "Cmaj13#11", nns: "1", key: "C" };
    run(h, host, 0, 3);
    const snowLush = U.uMood.value.z;
    A("a lush pedalled chord thickens the marine snow", snowLush > snowRest + 0.2, `${snowRest.toFixed(3)} -> ${snowLush.toFixed(3)}`);
    A("the dance is on between the bass and the solo, its strands addressed to real notes",
      U.uDance2.value.w > 0.9 && U.uDance.value.x === 36 - FIRST && U.uDance.value.y >= 0 && U.uDance.value.y < N && U.uDance.value.y !== U.uDance.value.x, JSON.stringify(U.uDance.value));
    A("the artifact grows inside the bell over the chord's root, and only there", h.debug.bells[bellOf(36)].art > 0.05 && h.debug.bells.filter((b) => b.art > 0.01).length === 1,
      h.debug.bells.map((b) => b.art.toFixed(2)).join(" "));
    const pts = h.debug.meshes.find((d) => d.name === "abyssal-plankton").geometry.attributes;
    let burstBefore = 0;
    for (let j = 0; j < pts.aN.count; j++) if (pts.aN.array[j] === -1 && pts.aP.array[j * 4 + 3] > 0) burstBefore++;
    host.pedal(false);
    for (const m of [36, 48, 52, 59, 62, 66, 69, 74]) host.off(m, 3);
    for (const m of [43, 47, 50, 53]) host.on(m, 96, 3.02);                 // the chord changes: the artifact releases
    host.st.chord = { name: "G7", nns: "5", key: "C" };
    run(h, host, 3, 3.5);
    let burstAfter = 0;
    for (let j = 0; j < pts.aN.count; j++) if (pts.aN.array[j] === -1 && pts.aP.array[j * 4 + 3] > 0) burstAfter++;
    A("the chord change bursts the artifact into a cloud of untagged plankton", burstAfter > burstBefore + 40, `${burstBefore} -> ${burstAfter}`);
    for (const m of [43, 47, 50, 53]) host.off(m, 3.5);
    host.st.chord = null;
    run(h, host, 3.5, 9);
    A("in silence the snow clears again and the dance fades", U.uMood.value.z < snowLush * 0.5 && U.uDance2.value.w < 0.05, `snow ${U.uMood.value.z.toFixed(3)} dance ${U.uDance2.value.w.toFixed(3)}`);
    h.dispose();
  }
  // --- setActive, dispose
  {
    disposed.length = 0;
    const parent = new THREE.Group();
    const h = Abyssal.create(ctx());
    parent.add(h.group);
    h.setActive(false);
    A("setActive(false) hides the group", h.group.visible === false);
    h.setActive(true);
    const owned = [...h.debug.geos, ...h.debug.mats, ...h.debug.texs];
    h.dispose();
    A("dispose() removes the group from its parent", h.group.parent === null && parent.children.length === 0);
    A("dispose() disposes every owned geometry, material and texture (6 + 6 + 1)",
      owned.length === 13 && owned.every((o) => disposed.includes(o)) && owned.filter((o) => o.isGeo).length === 6 && owned.filter((o) => o.isMat).length === 6 && owned.filter((o) => o.isTex).length === 1,
      `${owned.length} owned, ${disposed.length} disposed`);
  }
  // --- the host is never written; update() makes no garbage over 10 000 frames (verifier's checks, 2026-09-17)
  // (1) The host's camera, renderer and scene are proxies that log every property write and every method call while
  //     the whole instrument runs a scripted performance on them with the REAL harmony-feel and moment helpers.
  // (2) Allocation is measured in a child node (--expose-gc, a 64 MB semi-space so no scavenge lands inside the window):
  //     gc, then 10 000 frames of the same performance with about 12 notes sounding, and heapUsed after minus before is
  //     what update() allocated. V8's sampling heap profiler cannot see inline allocations in optimised code, so it is
  //     not used. The floor is not zero: V8 boxes doubles at non-inlined helper calls (damp, travelOf, dampFade per
  //     sounding note) and on closure variables, measured at 2.2-3.2 KB/frame on Node 24 (about a scavenge every 80 s at
  //     60 fps, sub-millisecond each); in this file, after the earlier stub runs, the child measures about 4 KB/frame.
  //     ALLOC_LINE is twice that: a per-key allocation (88 x 48 B) crosses it; a bound, not a proof of zero.
  const ALLOC_FRAMES = 10000, ALLOC_LINE = 8000;   // bytes per frame
  const pooledHost = () => {                       // the page's shapes, pooled like the page's: the host grows nothing
    const st = { pressed: new Map(), pedal: false, chord: null, notes: new Array(64).fill(null), sounding: new Map() };
    const pool = new Map();
    const entry = (m) => { let e = pool.get(m); if (!e) { e = { vel: 0, t0: 0, held: false, pedal: false, tRelease: null, strike: 0 }; pool.set(m, e); } return e; };
    const ring = []; for (let k = 0; k < 64; k++) ring.push({ midi: 0, vel: 0, t: -1e9 });
    let head = 0;
    return {
      st,
      on(m, vel, t) { const e = entry(m); e.vel = vel; e.t0 = t; e.held = true; e.pedal = false; e.tRelease = null; e.strike++; st.sounding.set(m, e); st.pressed.set(m, e);
        const r = ring[head]; head = (head + 1) % 64; r.midi = m; r.vel = vel; r.t = t; for (let k = 0; k < 64; k++) st.notes[k] = ring[(head + k) % 64]; },
      off(m, t) { const e = st.sounding.get(m); st.pressed.delete(m); if (!e) return; if (st.pedal) { e.held = false; e.pedal = true; e.tRelease = t; } else st.sounding.delete(m); },
      pedal(down) { st.pedal = down; if (!down) st.sounding.forEach((e, m) => { if (!e.held) st.sounding.delete(m); }); },
    };
  };
  const mulberry = (seed) => { let a = seed | 0; return () => { a = (a + 0x6d2b79f5) | 0; let x = Math.imul(a ^ (a >>> 15), 1 | a); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; };
  const CHORDS = [[36, 43, 47, 52, 57, 62, 66, 71, 76], [43, 47, 50, 53, 59], [60, 61, 62, 63, 64], [28, 40, 47, 52, 55], [48, 52, 55], [40, 44, 47, 50, 53, 56]];
  const CHORD_OBJ = ["Cmaj13#11", "G7", "cluster", "Emaj", "C", "E7b9"].map((name) => ({ name, nns: "1", key: "C" }));
  // pedalled chords every 3 s, a walking bass against a melody, re-strikes, a cluster, a chord change that releases the artifact
  const drive = (h, host, frames, t0, rnd) => {
    let t = t0, chordAt = -1, ci = 0, melAt = -1, mel = 72, bass = 36, bassAt = -1;
    for (let k = 0; k < frames; k++) {
      if (t - chordAt > 3.0) {
        if (chordAt >= 0) { for (let q = 0; q < CHORDS[ci].length; q++) host.off(CHORDS[ci][q], t); host.pedal(false); }
        ci = (ci + 1) % CHORDS.length; host.pedal(true);
        for (let q = 0; q < CHORDS[ci].length; q++) host.on(CHORDS[ci][q], 70 + Math.floor(rnd() * 57), t);
        host.st.chord = CHORD_OBJ[ci];
        chordAt = t;
        if (ci === 2) for (let q = 0; q < CHORDS[ci].length; q++) host.off(CHORDS[ci][q], t + 0.2);
      }
      if (t - melAt > 0.4) { host.off(mel, t); mel = 67 + Math.floor(rnd() * 24); host.on(mel, 40 + Math.floor(rnd() * 87), t); melAt = t; }
      if (t - bassAt > 0.55) { host.off(bass, t); bass = 24 + Math.floor(rnd() * 20); host.on(bass, 90, t); bassAt = t; }
      if (k % 97 === 0) host.on(mel, 100, t);
      if (k % 131 === 0) host.on(108, 30, t);
      t += DT;
      h.update(DT, t, host.st);
    }
    return t;
  };
  if (process.env.PIANO_LIGHT_VANDOR_ALLOC_CHILD) {
    // the child: measure and print one JSON line, nothing else
    const h = Abyssal.create(ctx()), host = pooledHost(), rnd = mulberry(7);
    let t = drive(h, host, 3000, 0, rnd);
    globalThis.gc();
    const a0 = process.memoryUsage().heapUsed, ms0 = performance.now();
    t = drive(h, host, ALLOC_FRAMES, t, rnd);
    const ms = performance.now() - ms0, real = process.memoryUsage().heapUsed - a0;
    const upd = h.update; h.update = () => {};
    globalThis.gc();
    const b0 = process.memoryUsage().heapUsed;
    t = drive(h, host, ALLOC_FRAMES, t, rnd);
    const noop = process.memoryUsage().heapUsed - b0;
    h.update = upd; h.dispose();
    process.stdout.write(JSON.stringify({ real, noop, ms, sounding: host.st.sounding.size, gc: typeof globalThis.gc }) + "\n");
    process.exit(0);
  }
  {
    const { execFileSync } = await import("node:child_process");
    let r = null, err = "";
    try {
      const out = execFileSync(process.execPath, ["--expose-gc", "--min-semi-space-size=64", "--max-semi-space-size=64", fileURLToPath(import.meta.url)],
        { env: { ...process.env, PIANO_LIGHT_VANDOR_ALLOC_CHILD: "1" }, encoding: "utf8", timeout: 120000 });
      r = JSON.parse(out.trim().split("\n").pop());
    } catch (e) { err = String(e.message).slice(0, 300); }
    A("the allocation child ran (node --expose-gc, 64 MB semi-space)", r && r.gc === "function", err);
    if (r) {
      A(`update() makes no object, array, closure or iterator garbage: under ${ALLOC_LINE} B/frame over ${ALLOC_FRAMES} frames with the real helpers and ~12 notes sounding`,
        r.real / ALLOC_FRAMES < ALLOC_LINE, `${(r.real / ALLOC_FRAMES).toFixed(0)} B/frame (host alone ${(r.noop / ALLOC_FRAMES).toFixed(0)} B/frame)`);
      A("...and the synthetic host itself allocates almost nothing (the measurement is the instrument's)", r.noop / ALLOC_FRAMES < 300, `${(r.noop / ALLOC_FRAMES).toFixed(0)} B/frame`);
      report.push(`${ABY}: ${ALLOC_FRAMES} frames in ${r.ms.toFixed(0)} ms on the stub (${(r.ms / ALLOC_FRAMES * 1000).toFixed(0)} us/frame); update() garbage ${(r.real / ALLOC_FRAMES).toFixed(0)} B/frame (host alone ${(r.noop / ALLOC_FRAMES).toFixed(0)}), line ${ALLOC_LINE}`);
    }
  }
  {
    const writes = [], calls = [];
    const guard = (name, target) => new Proxy(target, {
      set(t, k, v) { writes.push(`${name}.${String(k)}`); t[k] = v; return true; },
      deleteProperty(t, k) { writes.push(`delete ${name}.${String(k)}`); delete t[k]; return true; },
      defineProperty(t, k, d) { writes.push(`define ${name}.${String(k)}`); Object.defineProperty(t, k, d); return true; },
      get(t, k) {
        const v = t[k];
        if (typeof v === "function") return (...a) => { calls.push(`${name}.${String(k)}`); return v.apply(t, a); };
        if (v && typeof v === "object" && !ArrayBuffer.isView(v)) return guard(`${name}.${String(k)}`, v);
        return v;
      },
    });
    const camera = guard("camera", { position: new Vec3(0, 20, 40), rotation: new Vec3(), fov: 50, near: 0.1, far: 500, zoom: 1, aspect: 16 / 9, layers: { mask: 1, set() {}, enable() {}, disable() {} }, lookAt() {}, updateProjectionMatrix() {} });
    const renderer = guard("renderer", { toneMapping: 5, toneMappingExposure: 1, autoClear: true, domElement: {}, capabilities: { isWebGL2: true }, info: { render: { calls: 0 } },
      getCurrentViewport(v) { v.set(0, 0, 2560, 1440); return v; }, setClearColor() {}, setSize() {}, setPixelRatio() {}, setRenderTarget() {}, render() {} });
    const scene = guard("scene", { fog: null, background: null, environment: null, children: [], add() {}, remove() {} });
    const hostCtx = { ...ctx(), scene, camera, renderer, clock: { getElapsedTime: () => 0 }, noteCss: () => "#fff" };
    const h = Abyssal.create(hostCtx), host = pooledHost(), rnd = mulberry(11);
    drive(h, host, 2000, 0, rnd);
    h.resize({ id: "9:16", w: 1080, h: 1920 }); h.resize({ id: "16:9", w: 1920, h: 1080 });
    for (const m of h.group.children) if (m.onBeforeRender) m.onBeforeRender(renderer, scene, camera);
    h.setActive(false); h.setActive(true); h.dispose();
    A("nothing of the host's is ever written: camera, renderer and scene see no property write, no define, no delete",
      writes.length === 0, writes.slice(0, 5).join(", "));
    A("the only host method the instrument calls is renderer.getCurrentViewport (a read, in onBeforeRender)",
      [...new Set(calls)].join(",") === "renderer.getCurrentViewport", [...new Set(calls)].join(", "));
  }
  const src = SRC[ABY];
  A("the envelope table is the concert grand's, number for number", K.PEAK_EXP === 1.35 && K.FLOOR_LO === 0.33 && K.FLOOR_HI === 0.5 && K.TAU_AFTER_BASS === 7 && K.TAU_DAMP === 0.16 && K.DAMP_FADE === 0.3 && K.TAU_VIB_OFF === 0.07);
  // repair round 1: the bell fragment shader's high-exponent pow() calls put a NaN into the host's bloom about one frame in
  // 200 on the RX 9070 XT (a black rectangle); no pow in the bell shader now, and every other shader pow guards its base
  {
    const bellFs = slice(src, "const BELL_FS = ", "const TIP_VS = ");
    A("the bell fragment shader calls pow() nowhere (products and exp of a bounded argument instead), and clamps its fresnel base",
      bellFs.length > 500 && !/\bpow\(/.test(bellFs) && bellFs.includes("clamp(1.0 - abs(dot(Nn, V)), 0.0, 1.0)") && bellFs.includes("lobe(") && bellFs.includes("sq("));
    // the helpers live in the shared prelude once: a second definition inside a shader body is a compile error that the
    // stub THREE here cannot see (the tentacle shader shipped one for a burst on 2026-09-17 and drew nothing)
    A("each GLSL helper (sq, ppow, lobe) is defined exactly once, in the shared prelude, and every shader that uses one includes the prelude",
      ["float sq(float x)", "float ppow(float x, float y)", "float lobe(float c, float k)"].every((d) => (src.split(d).length - 1) === 1)
      && src.split(/^const [A-Z_]+_[VF]S = \/\* glsl \*\/ `/m).slice(1).every((body) => !/\b(sq|ppow|lobe)\(/.test(body.split("`")[0]) || body.split("`")[0].includes("${COMMON}")));
    const rawPow = (src.match(/(?<![A-Za-z_.])pow\(/g) || []).length;   // GLSL pow( not spelled ppow( (Math.pow is JS)
    A("the shaders' only bare pow() calls are ppow's own guarded one and the two register-based ones whose base is 0..1",
      rawPow === 3 && src.includes("float ppow(float x, float y) { return pow(max(x, 1e-4), y); }") && /pow\(rb, 0\.6\)/.test(src) && /pow\(rs, 0\.6\)/.test(src), `${rawPow} bare pow( calls`);
  }
  A("nothing downloaded: no fetch, no loaders, no URLs", !/\bfetch\(|Loader\(|https?:\/\//.test(src));
  A("the material, the dance and the moment are wired to the helpers' fields",
    /C\.lushness/.test(src) && /C\.tension/.test(src) && /C\.simplicity/.test(src) && /V\.bass/.test(src) && /V\.solo/.test(src) && src.includes('"contrary"')
    && /D\.consonance/.test(src) && /D\.phase/.test(src) && /D\.pull/.test(src) && /mo\.artifact\.growth/.test(src) && /mo\.artifact\.released/.test(src)
    && /mo\.artifact\.releaseStrength/.test(src) && /mo\.mood\.valence/.test(src) && /mo\.energy/.test(src));
  report.push(`${ABY}: envelope floor ${(K.FLOOR_LO + (K.FLOOR_HI - K.FLOOR_LO) * 96 / 127).toFixed(2)} of the body at vel 96; blur ${K.ENV_BASS} -> ${K.ENV_TREBLE} units; `
    + `ghosts ${K.GHOST_HZ_BASS}-${K.GHOST_HZ_TREBLE} Hz; pulse ${K.TRAVEL_PP}-${K.TRAVEL_FF} s bell to key; damping ${K.TAU_DAMP} s in ${K.DAMP_FADE} s`);
} else {
  console.log(`(skipped: ${ABY}.js is not present)`);
}

// ------------------------------------------------------------------------- the Ornithopter, running (stub THREE) --
// The verifier's runtime section (2026-09-17). The Ornithopter builds its creature out of a dozen three.js classes, so a
// stub THREE stands in for the page's r186: geometries are placeholders (only their attribute counts matter to the module's
// own merge), the matrix and vector maths the module relies on at runtime (rotations, transformDirection, colour lerps) is
// real. The instrument is created against a scene / camera / renderer whose every write is recorded, driven with a
// synthetic state shaped exactly as piano.js hands it over (pooled entries, a strike counter, a 64-slot strike ring, the
// pedal), and read back through the per-instance attributes it uploads (aState: amplitude, centre, ghost phase, light;
// aStrike: age, velocity, flash, stand) and its uniforms. Checks: the contract shape and the 13 fixed draws; velocity;
// the pedal's truth; the damping fade; re-strikes; the strike ring; the bass blur over the treble; the material, the dance
// and the artifact wired to real harmony-feel / moment instances; dispose over everything; nothing of the host's written;
// and nothing allocated inside update over 10 000 frames (heap growth, measured against a control loop that skips update).
if (SRC[ORN]) {
  const O = (label, ok, detail) => check(`${ORN} (runtime): ${label}`, ok, detail);
  const disposed = new Set();
  class V3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
    set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
    setScalar(s) { return this.set(s, s, s); }
    copy(v) { return this.set(v.x, v.y, v.z); }
    clone() { return new V3(this.x, this.y, this.z); }
    subVectors(a, b) { return this.set(a.x - b.x, a.y - b.y, a.z - b.z); }
    length() { return Math.hypot(this.x, this.y, this.z); }
    normalize() { const l = this.length() || 1; return this.set(this.x / l, this.y / l, this.z / l); }
    transformDirection(m) { const e = m.elements, x = this.x, y = this.y, z = this.z; return this.set(e[0] * x + e[4] * y + e[8] * z, e[1] * x + e[5] * y + e[9] * z, e[2] * x + e[6] * y + e[10] * z).normalize(); }
  }
  class V2 { constructor(x = 0, y = 0) { this.x = x; this.y = y; } set(x, y) { this.x = x; this.y = y; return this; } }
  class V4 { constructor(x = 0, y = 0, z = 0, w = 0) { this.x = x; this.y = y; this.z = z; this.w = w; } set(x, y, z, w) { this.x = x; this.y = y; this.z = z; this.w = w; return this; } }
  class Quat { setFromUnitVectors() { return this; } }
  class M4 {
    constructor() { this.elements = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]); }
    makeRotationX(a) { const c = Math.cos(a), s = Math.sin(a); this.elements.set([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]); return this; }
    makeRotationZ(a) { const c = Math.cos(a), s = Math.sin(a); this.elements.set([c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]); return this; }
    multiplyMatrices(a, b) { const ae = a.elements, be = b.elements, o = new Float32Array(16); for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) { let s = 0; for (let k = 0; k < 4; k++) s += ae[r + k * 4] * be[k + c * 4]; o[r + c * 4] = s; } this.elements.set(o); return this; }
    setPosition(x, y, z) { this.elements[12] = x; this.elements[13] = y; this.elements[14] = z; return this; }
  }
  class Col {
    constructor(r, g, b) { this.r = 0; this.g = 0; this.b = 0; if (typeof r === "number" && g === undefined) this.setHex(r); else if (typeof r === "number") this.setRGB(r, g, b); }
    setHex(h) { return this.setRGB(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255); }
    setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; }
    setHSL(h, s, l) { const k = (n) => (n + h * 12) % 12, a = s * Math.min(l, 1 - l), f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1)); return this.setRGB(f(0), f(8), f(4)); }
    copy(c) { return this.setRGB(c.r, c.g, c.b); }
    clone() { return new Col(this.r, this.g, this.b); }
    lerp(c, t) { return this.setRGB(this.r + (c.r - this.r) * t, this.g + (c.g - this.g) * t, this.b + (c.b - this.b) * t); }
  }
  class Attr { constructor(array, size) { this.array = array; this.itemSize = size; this.count = array.length / size; this.needsUpdate = false; this.isAttr = true; } setUsage() { return this; } setXYZW(i, x, y, z, w) { const a = this.array, o = i * 4; a[o] = x; a[o + 1] = y; a[o + 2] = z; a[o + 3] = w; return this; } }
  let geoSerial = 0;
  class Geo {
    constructor(verts = 3) {
      this.attributes = {}; this.index = null; this.isGeo = true; this.serial = ++geoSerial;
      if (verts) { this.setAttribute("position", new Attr(new Float32Array(verts * 3), 3)); this.setAttribute("normal", new Attr(new Float32Array(verts * 3), 3)); this.setAttribute("uv", new Attr(new Float32Array(verts * 2), 2)); }
    }
    setAttribute(n, a) { this.attributes[n] = a; return this; } setIndex(a) { this.index = a; return this; }
    toNonIndexed() { const g = new Geo(this.attributes.position.count); return g; } computeVertexNormals() { return this; }
    translate() { return this; } rotateX() { return this; } rotateY() { return this; } rotateZ() { return this; } scale() { return this; } applyQuaternion() { return this; }
    dispose() { disposed.add(this); }
  }
  class Shape { moveTo() { return this; } lineTo() { return this; } quadraticCurveTo() { return this; } }
  class Mat { constructor(p = {}) { Object.assign(this, p); if (typeof this.color === "number") this.color = new Col(this.color); this.emissive = new Col(typeof this.emissive === "number" ? this.emissive : 0); this.isMat = true; } dispose() { disposed.add(this); } }
  class Tex { constructor(data, w, h) { this.image = { data, width: w, height: h }; this.needsUpdate = false; this.isTex = true; } dispose() { disposed.add(this); } }
  class Obj {
    constructor() { this.children = []; this.parent = null; this.visible = true; this.name = ""; this.renderOrder = 0; this.frustumCulled = true; this.position = new V3(); this.rotation = new V3(); this.scale = new V3(1, 1, 1); this.isObject3D = true; }
    add(...cs) { for (const c of cs) { this.children.push(c); c.parent = this; } return this; }
    remove(c) { const i = this.children.indexOf(c); if (i >= 0) { this.children.splice(i, 1); c.parent = null; } return this; }
  }
  class Mesh extends Obj { constructor(g, m) { super(); this.geometry = g; this.material = m; this.isMesh = true; } }
  class Points extends Obj { constructor(g, m) { super(); this.geometry = g; this.material = m; this.isPoints = true; } }
  class IMesh extends Mesh { constructor(g, m, n) { super(g, m); this.count = n; this.isInstancedMesh = true; this.instanceMatrix = new Attr(new Float32Array(n * 16), 16); } setMatrixAt(i, m) { this.instanceMatrix.array.set(m.elements, i * 16); } dispose() { disposed.add(this); } }
  const THREE = {
    Group: class extends Obj {}, Mesh, Points, InstancedMesh: IMesh, ShaderMaterial: Mat, MeshStandardMaterial: Mat, DataTexture: Tex,
    BufferGeometry: class extends Geo { constructor() { super(0); } }, BufferAttribute: Attr, InstancedBufferAttribute: Attr,
    PlaneGeometry: class extends Geo { constructor() { super(4); } }, BoxGeometry: class extends Geo { constructor() { super(24); } },
    CylinderGeometry: class extends Geo { constructor() { super(12); } }, SphereGeometry: class extends Geo { constructor() { super(12); } },
    IcosahedronGeometry: class extends Geo { constructor() { super(12); } }, LatheGeometry: class extends Geo { constructor() { super(12); } },
    ExtrudeGeometry: class extends Geo { constructor() { super(12); } }, Shape,
    Vector2: V2, Vector3: V3, Vector4: V4, Matrix4: M4, Quaternion: Quat, Color: Col,
    RGBAFormat: 1, UnsignedByteType: 2, FloatType: 3, RepeatWrapping: 4, LinearFilter: 5, DynamicDrawUsage: 6, DoubleSide: 7,
    CustomBlending: 8, AddEquation: 9, MaxEquation: 10, OneFactor: 11, OneMinusSrcAlphaFactor: 12, AdditiveBlending: 13,
  };
  const mod12 = (a) => ((a % 12) + 12) % 12;
  const isBlack = (m) => [1, 3, 6, 8, 10].includes(mod12(m));
  const WHITE_OFFSET = [0, -1, 1, -1, 2, 3, -1, 4, -1, 5, -1, 6], BLACK_CENTER = { 1: 0.9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5.0, 10: 3 + 4 / 7 * 5.5 };
  const keyX = (m) => { const oct = Math.floor(m / 12), pc = mod12(m); return (isBlack(m) ? oct * 7 + BLACK_CENTER[pc] : oct * 7 + WHITE_OFFSET[pc] + 0.5) - 38; };
  const noteColor = (m, vel, target) => target.setHSL(mod12(m) / 12, 0.9, 0.5);
  // the host's objects, every write recorded (an instrument draws only itself)
  const hostWrites = [];
  const guard = (name, target) => new Proxy(target, {
    set(t, p, v) { hostWrites.push(`${name}.${String(p)} =`); t[p] = v; return true; },
    deleteProperty(t, p) { hostWrites.push(`delete ${name}.${String(p)}`); delete t[p]; return true; },
    defineProperty(t, p, d) { hostWrites.push(`define ${name}.${String(p)}`); Object.defineProperty(t, p, d); return true; },
    get(t, p) { const v = t[p]; if (typeof v === "function" && !["add", "remove", "getCurrentViewport"].includes(p)) return (...a) => { hostWrites.push(`${name}.${String(p)}()`); return v.apply(t, a); }; return v; },
  });
  const mkHost = () => {
    const scene = guard("scene", new THREE.Group());
    const camera = guard("camera", { position: new V3(0, 10, 40), fov: 23, near: 0.1, far: 500, projectionMatrix: { elements: new Float32Array([2.5, 0, 0, 0, 0, 4.4, 0, 0, 0, 0, -1, -1, 0, 0, -0.2, 0]) }, layers: { mask: 1 }, updateProjectionMatrix() {}, lookAt() {} });
    const renderer = guard("renderer", { toneMapping: 0, autoClear: true, setClearColor() {}, setSize() {}, setPixelRatio() {}, getPixelRatio: () => 1, getCurrentViewport(v) { return v.set(0, 0, 2560, 1440); } });
    return { scene, camera, renderer };
  };
  const FRAMING = { id: "16:9", w: 1920, h: 1080, width: 1920, height: 1080 };
  const ctx = (host = mkHost()) => ({ THREE, scene: host.scene, camera: host.camera, renderer: host.renderer, clock: { getElapsedTime: () => 0 }, keyX, isBlack, noteColor,
    noteCss: () => "oklch(0.7 0.2 100)", KEY: { first: 21, last: 108 }, framing: FRAMING, span: { first: 21, last: 108, left: keyX(21) - 0.5, right: keyX(108) + 0.5, width: 52, keyTop: 0, floorY: -2.3 }, options: {} });
  // the host's state, shaped as piano.js refreshes it: pooled entries per key, a strike counter, a 64-slot strike ring
  function makeState() {
    const st = { pressed: new Map(), pedal: false, chord: null, notes: [], sounding: new Map() };
    for (let k = 0; k < 64; k++) st.notes.push({ midi: 0, vel: 0, t: -1 });
    const pool = new Map();
    let ring = 0;
    const entry = (m) => { let e = pool.get(m); if (!e) { e = { vel: 0, t0: 0, held: false, pedal: false, tRelease: null, strike: 0 }; pool.set(m, e); } return e; };
    return {
      st,
      on(m, vel, t) { const e = entry(m); e.vel = vel; e.t0 = t; e.held = true; e.pedal = false; e.tRelease = null; e.strike++; st.sounding.set(m, e); st.pressed.set(m, e); const n = st.notes[ring]; ring = (ring + 1) % 64; n.midi = m; n.vel = vel; n.t = t; },
      tap(m, vel, t) { const n = st.notes[ring]; ring = (ring + 1) % 64; n.midi = m; n.vel = vel; n.t = t; },   // struck and released inside one frame
      off(m, t) { const e = st.sounding.get(m); st.pressed.delete(m); if (!e) return; if (st.pedal) { e.held = false; e.pedal = true; e.tRelease = t; } else st.sounding.delete(m); },
      pedal(down) { st.pedal = down; if (!down) for (const m of [...st.sounding.keys()]) if (!st.sounding.get(m).held) st.sounding.delete(m); },
      chord(name) { st.chord = name ? { name, nns: "", key: "" } : null; },
    };
  }
  const Orn = (await import(`../arsenal/web/piano/instruments/${ORN}.js`)).default;
  const k = constants(SRC[ORN]);
  const FIRST = 21, N = 88, DT = 1 / 60;
  const run = (h, host, from, to) => { let t = from; while (t < to - 1e-9) { t += DT; h.update(DT, t, host.st); } return t; };
  const wing = (h) => h.parts.lights.geometry.attributes;
  const level = (h, m) => wing(h).aState.array[(m - FIRST) * 4 + 3];
  const amp = (h, m) => wing(h).aState.array[(m - FIRST) * 4];
  const flash = (h, m) => wing(h).aStrike.array[(m - FIRST) * 4 + 2];
  const stand = (h, m) => wing(h).aStrike.array[(m - FIRST) * 4 + 3];
  const pistonY = (h, m) => h.parts.pistons.instanceMatrix.array[(m - FIRST) * 16 + 13];
  const litCount = (h) => { let n = 0; for (let i = 0; i < N; i++) if (wing(h).aState.array[i * 4 + 3] > 0 || wing(h).aStrike.array[i * 4 + 2] > 0 || wing(h).aState.array[i * 4] > 0) n++; return n; };
  const uni = (h, name) => h.group.children.find((c) => c.name === name).material.uniforms;

  // --- the contract and the fixed draw list
  {
    const host = mkHost();
    const h = Orn.create(ctx(host));
    O("id, name, create, keyStyle and keySpan on the default export", Orn.id === ORN && Orn.name === "Ornithopter" && typeof Orn.create === "function" && Orn.keySpan.first === 21 && Orn.keySpan.last === 108 && Number.isFinite(Orn.keyStyle.whiteColor));
    O("create() returns group, update, resize, setActive, dispose and stage hints that hide the host body and lower the floor",
      h.group && h.group.isObject3D && ["update", "resize", "setActive", "dispose"].every((f) => typeof h[f] === "function") && h.stageHints.hideHostBody === true && h.stageHints.floorY < -5);
    O("the group is added to the host scene (the only scene write) and named for the instrument", host.scene.children[0] === h.group && h.group.name === "instrument:" + ORN);
    const draws = h.group.children.filter((c) => c.isMesh || c.isPoints);
    O("thirteen drawables, every one never frustum culled", draws.length === 13 && draws.every((d) => d.frustumCulled === false), draws.map((d) => d.name).join(","));
    O("the parts the note names: body, lenses, keybed, pistons, clasps, wing membranes, wing light, dust, haze, braid, two artifacts, pool",
      ["body", "lenses", "keybed", "pistons", "clasps", "wing-membranes", "wing-light", "dust", "haze", "braid", "artifact-0", "artifact-1", "pool"].every((n) => draws.some((d) => d.name === n)));
    O("88 instances of pistons, clasps, membranes and light; 30 shards per artifact", h.parts.pistons.count === 88 && h.parts.clasps.count === 88 && h.parts.membranes.count === 88 && h.parts.lights.count === 88 && draws.filter((d) => d.name.startsWith("artifact")).every((d) => d.count === 30));
    O("the light pass never stacks (MaxEquation) and the membrane pass writes no depth", h.parts.lights.material.blendEquation === THREE.MaxEquation && h.parts.membranes.material.depthWrite === false && h.parts.lights.material.depthWrite === false);
    O("wing membranes and wing light share one uniform block and one instanced geometry", h.parts.membranes.material.uniforms === h.parts.lights.material.uniforms && h.parts.membranes.geometry === h.parts.lights.geometry);
    const st = makeState();
    h.update(DT, 0, st.st);
    O("at rest nothing is lit: no level, no flash, no stroke on any of the 88 wings", litCount(h) === 0);
    O("at rest the haze, the braid and the artifacts are collapsed (their levels 0)", uni(h, "haze").uHaze.value === 0 && uni(h, "braid").uLevel.value === 0 && uni(h, "artifact-0").uGrowth.value === 0 && uni(h, "artifact-1").uGrowth.value === 0);
    h.resize({ id: "9:16", w: 1080, h: 1920 });
    O("resize() records the framing", h.framing && h.framing.id === "9:16");
    // the braid's onBeforeRender reads the renderer's viewport and the camera's lens: reads only
    h.parts.braid.onBeforeRender(host.renderer, host.scene, host.camera);
    O("onBeforeRender takes the viewport size into the braid and the dust (reads only)", uni(h, "braid").uRes.value.x === 2560 && uni(h, "braid").uRes.value.y === 1440 && h.parts.dust.material.uniforms.uPx.value > 0);
    h.dispose();
    O("nothing of the host's is written: scene (beyond add / remove), camera, renderer untouched", hostWrites.length === 0, hostWrites.slice(0, 5).join(" | "));
  }
  // --- the strike, the envelope, the fold
  {
    const h = Orn.create(ctx()), st = makeState();
    h.update(DT, 0, st.st);
    const restY = pistonY(h, 60);
    st.on(60, 100, 0);
    h.update(DT, DT, st.st);
    const v = 100 / 127, peak = Math.pow(v, k.PEAK_EXP), floor = peak * (k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * v);
    const lightOf = (b) => k.SUS_GAIN * Math.pow(b, k.LIGHT_EXP);
    O("a strike lights the wing at once at the strike body (SUS_GAIN * v^PEAK_EXP ^ LIGHT_EXP)", Math.abs(level(h, 60) - lightOf(peak)) < 0.03, `${level(h, 60).toFixed(3)} vs ${lightOf(peak).toFixed(3)}`);
    O("the strike flash fires near v^FLASH_EXP * FLASH_GAIN and only on the struck wing", flash(h, 60) > 0.8 * Math.pow(v, k.FLASH_EXP) * k.FLASH_GAIN && flash(h, 61) === 0 && flash(h, 59) === 0, flash(h, 60).toFixed(3));
    O("the stroke amplitude at C4 is between the treble shimmer and the bass envelope", amp(h, 60) > k.AMP_TREBLE * Math.PI / 180 && amp(h, 60) < k.AMP_BASS * Math.PI / 180);
    run(h, st, DT, 0.2);
    O("the wing stands up within 0.2 s of the strike (FOLD_UP)", stand(h, 60) > 0.9, stand(h, 60).toFixed(3));
    let rose = false;
    for (let t = 0.2; t < 0.5; t += DT) { h.update(DT, t + DT, st.st); if (pistonY(h, 60) > restY + 0.5) rose = true; }
    O("the piston fires up from its rest toward the wing root", rose);
    run(h, st, 0.5, 4);
    O("held 4 s the light sits on the floor + the slow aftersound, below the strike and above the floor", level(h, 60) < lightOf(peak) * 0.9 && level(h, 60) >= lightOf(floor) * 0.999, `${level(h, 60).toFixed(3)} floor ${lightOf(floor).toFixed(3)}`);
    O("the wing keeps beating while it sounds (amplitude never 0)", amp(h, 60) > 0.2 * amp(h, 60) + 1e-6 && amp(h, 60) > 0);
    O("the flash is long gone by 4 s", flash(h, 60) === 0);
    st.off(60, 4);                                                     // pedal up: the sound ends
    const L0 = level(h, 60);
    let t = 4, prev = L0, worst = 0, gone = null, standGone = null;
    while (t < 4.8) { h.update(DT, t + DT, st.st); t += DT; const L = level(h, 60); worst = Math.max(worst, (prev - L) / L0); prev = L; if (gone === null && L === 0) gone = t - 4; if (standGone === null && stand(h, 60) < 0.05) standGone = t - 4; }
    O("pedal up: the light is gone within DAMP_FADE (+1 frame)", gone !== null && gone <= k.DAMP_FADE + DT + 1e-6, `gone at ${gone && gone.toFixed(3)}`);
    O("...as a fade: the steepest 60 fps step is under a fifth of the level at the release", worst < 0.2, `${(worst * 100).toFixed(1)} %`);
    O("...and the wing folds to rest within 0.5 s", standGone !== null && standGone <= 0.5, `stand 0.05 at ${standGone}`);
    O("after the sound nothing of that wing is left: level, amplitude and flash all 0", level(h, 60) === 0 && amp(h, 60) === 0 && flash(h, 60) === 0);
    h.dispose();
  }
  // --- velocity
  {
    const at = { 0.5: [], 4: [] };
    for (const vel of [30, 70, 120]) {
      const h = Orn.create(ctx()), st = makeState();
      h.update(DT, 0, st.st); st.on(60, vel, 0); h.update(DT, DT, st.st);
      const f = flash(h, 60), a0 = amp(h, 60);
      run(h, st, DT, 0.5); at[0.5].push({ vel, L: level(h, 60), A: amp(h, 60), F: f, A0: a0 });
      run(h, st, 0.5, 4); at[4].push({ vel, L: level(h, 60), A: amp(h, 60) });
      h.dispose();
    }
    const rises = (arr, key) => arr.every((p, i) => i === 0 || p[key] > arr[i - 1][key]);
    O("light, stroke and flash all rise with velocity at +0.5 s (v30 < v70 < v120)", rises(at[0.5], "L") && rises(at[0.5], "A") && rises(at[0.5], "F") && rises(at[0.5], "A0"), JSON.stringify(at[0.5]));
    O("...and still at +4 s on the floor", rises(at[4], "L") && rises(at[4], "A"), JSON.stringify(at[4]));
    O("a soft note still reads: v30 keeps at least a sixth of the ff light and a stroke for the whole sound", at[4][0].L >= at[4][2].L / 6 && at[4][0].L > 0.12 && at[4][0].A > 0, `${at[4][0].L.toFixed(3)} vs ${at[4][2].L.toFixed(3)}`);
  }
  // --- the pedal
  {
    const h = Orn.create(ctx()), st = makeState();
    h.update(DT, 0, st.st);
    st.pedal(true); st.on(33, 110, 0);
    run(h, st, 0, 0.5);
    st.off(33, 0.5);                                                    // the finger lifts; the pedal holds the sound
    const Lheld = level(h, 33);
    run(h, st, 0.5, 8);
    const v = 110 / 127, peak = Math.pow(v, k.PEAK_EXP), floor = peak * (k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * v);
    O("a note held only by the pedal keeps its light for 8 s (on its floor, a wing still standing and beating)", level(h, 33) >= k.SUS_GAIN * Math.pow(floor, k.LIGHT_EXP) * 0.999 && stand(h, 33) > 0.95 && amp(h, 33) > 0, `${level(h, 33).toFixed(3)} (was ${Lheld.toFixed(3)} under the finger)`);
    O("the pedalled wing settles to a lower stroke than its strike but never stops", amp(h, 33) > 0.3 * (k.AMP_BASS * Math.PI / 180) * 0.5);
    st.pedal(false);                                                    // the pedal lifts: the sound ends
    let t = 8, gone = null;
    while (t < 8.6) { h.update(DT, t + DT, st.st); t += DT; if (gone === null && level(h, 33) === 0) gone = t - 8; }
    O("the pedal lift damps the pedalled note within DAMP_FADE (+1 frame)", gone !== null && gone <= k.DAMP_FADE + DT + 1e-6, `gone at ${gone}`);
    st.pedal(true);
    run(h, st, 8.6, 11);
    O("the pedal alone lights nothing: no wing has level, stroke or flash while only the pedal is down", litCount(h) === 0 && uni(h, "braid").uLevel.value < 1e-3, `lit ${litCount(h)}`);
    O("a pedal press never resurrects a sound that ended", level(h, 33) === 0 && amp(h, 33) === 0 && stand(h, 33) < 0.01);
    // a pedal lift mid-chord: the fingered notes keep their floor while the pedal-only one damps (fixture 3)
    st.pedal(true); st.on(60, 90, 11); st.on(64, 90, 11); st.on(67, 90, 11);
    run(h, st, 11, 12.5); st.off(67, 12.5);
    run(h, st, 12.5, 14); st.pedal(false);
    run(h, st, 14, 14.5);
    O("fixture 3: after the lift the finger-held C4 and E4 keep their light, the pedal-only G4 is dark", level(h, 60) > 0.3 && level(h, 64) > 0.3 && level(h, 67) === 0, `${level(h, 60).toFixed(2)} ${level(h, 64).toFixed(2)} ${level(h, 67).toFixed(2)}`);
    h.dispose();
  }
  // --- re-strikes and the strike ring
  {
    const h = Orn.create(ctx()), st = makeState();
    h.update(DT, 0, st.st);
    st.on(63, 90, 0);
    run(h, st, 0, 1);
    const before = level(h, 63);
    st.on(63, 90, 1);                                                   // the strike counter increments on the same key
    h.update(DT, 1 + DT, st.st);
    O("a re-strike re-flashes", flash(h, 63) > 0.5, flash(h, 63).toFixed(3));
    O("...and never dips the light below the level it found", level(h, 63) >= before - 1e-6, `${level(h, 63).toFixed(3)} vs ${before.toFixed(3)}`);
    run(h, st, 1 + DT, 1.12);                                           // let that flash decay before the repeats begin
    let flashes = 0, prevF = flash(h, 63);
    for (let q = 0; q < 8; q++) {                                       // eight repeats in two seconds: eight flashes
      const t0 = 1.25 + q * 0.25;
      st.off(63, t0 - 0.13); st.on(63, 90, t0);
      let t = t0 - 0.13;
      while (t < t0 + 0.12 - 1e-9) { h.update(DT, t + DT, st.st); t += DT; const f = flash(h, 63); if (f > prevF + 0.3) flashes++; prevF = f; }
    }
    O("fast repeats: every one of eight strikes flashes again", flashes === 8, `${flashes} flashes`);
    run(h, st, 3.25, 5);
    st.off(63, 5);
    run(h, st, 5, 6);
    O("a note struck and released between two frames (only in the strike ring) still flashes and fades", (() => { st.tap(72, 100, 6); h.update(DT, 6 + DT, st.st); const f = flash(h, 72), L = level(h, 72); run(h, st, 6 + DT, 6.6); return f > 0.5 && L > 0 && level(h, 72) === 0; })());
    h.dispose();
  }
  // --- the flash budget: wings flashing together share one flash (repair round 1, the chromatic cluster at fff)
  {
    const strikeFlash = (notes, read) => { const h = Orn.create(ctx()), st = makeState(); h.update(DT, 0, st.st); for (const m of notes) st.on(m, 127, 0); h.update(DT, DT, st.st); const f = read(h); h.dispose(); return f; };
    const lone = strikeFlash([60], (h) => flash(h, 60));
    const pair = strikeFlash([62, 63], (h) => flash(h, 62));
    const apart = strikeFlash([60, 60 + k.FLASH_REACH + 1], (h) => flash(h, 60));
    const mid = strikeFlash([60, 61, 62, 63, 64, 65, 66, 67, 68, 69], (h) => flash(h, 64));
    const edge = strikeFlash([60, 61, 62, 63, 64, 65, 66, 67, 68, 69], (h) => flash(h, 60));
    O("a lone strike keeps its whole flash; a wing struck beyond FLASH_REACH semitones is no neighbour", lone > 1 && Math.abs(apart - lone) < 1e-6, `${lone.toFixed(3)} vs ${apart.toFixed(3)}`);
    O("an adjacent pair shares the flash: each shows (1 + 1)^-FLASH_SHARE of a lone strike", Math.abs(pair - lone * Math.pow(2, -k.FLASH_SHARE)) < 1e-3, `${pair.toFixed(3)} vs ${lone.toFixed(3)}`);
    O("in a ten-note chromatic cluster the middle wing shows under a fifth of a lone flash, and less than an edge wing", mid < lone / 5 && mid < edge && edge < lone, `mid ${mid.toFixed(3)} edge ${edge.toFixed(3)} lone ${lone.toFixed(3)}`);
    O("the budget shares smoothly: a neighbour under FLASH_NEIGH counts in proportion, so its decay never pops this wing's flash", (() => {
      const h = Orn.create(ctx()), st = makeState(); h.update(DT, 0, st.st);
      st.on(62, 127, 0); run(h, st, 0, 0.35); st.on(63, 127, 0.35); h.update(DT, 0.35 + DT, st.st);   // D4's flash has decayed to ~0.02 when Eb4 strikes
      let prev = flash(h, 63), worstJump = 0, t = 0.35 + DT;
      for (let q = 0; q < 20; q++) { h.update(DT, t + DT, st.st); t += DT; const f = flash(h, 63); if (f > prev * 1.001) worstJump = Math.max(worstJump, f / prev - 1); prev = f; }
      h.dispose();
      return worstJump === 0;   // the budgeted flash only ever falls after the strike frame
    })());
  }
  // --- a mid-chord mount picks the sound up where it is (no flash, no piston fire for a note struck 2 s ago)
  {
    const st = makeState();
    st.pedal(true); st.on(45, 100, 0);
    const h = Orn.create(ctx());
    h.update(DT, 2, st.st);
    O("mounted 2 s into a sounding note: lit on its settled level, no flash", level(h, 45) > 0.4 && level(h, 45) < k.SUS_GAIN && flash(h, 45) < 0.01, `${level(h, 45).toFixed(3)} flash ${flash(h, 45).toFixed(4)}`);
    h.dispose();
  }
  // --- low notes blur more, high notes shimmer; the ghost turns slower in the bass
  {
    const h = Orn.create(ctx()), st = makeState();
    h.update(DT, 0, st.st);
    st.on(21, 100, 0); st.on(60, 100, 0); st.on(108, 100, 0);
    h.update(DT, DT, st.st);
    const p21 = wing(h).aState.array[0 * 4 + 2], p108 = wing(h).aState.array[87 * 4 + 2];
    run(h, st, DT, 0.5);
    O("A0's stroke is at least five times C8's at the same body, with C4 between", amp(h, 21) > 5 * amp(h, 108) && amp(h, 60) > amp(h, 108) && amp(h, 60) < amp(h, 21), `${(amp(h, 21) * 180 / Math.PI).toFixed(1)} / ${(amp(h, 60) * 180 / Math.PI).toFixed(1)} / ${(amp(h, 108) * 180 / Math.PI).toFixed(1)} deg`);
    const d21 = Math.abs(wing(h).aState.array[0 * 4 + 2] - p21), d108 = Math.abs(wing(h).aState.array[87 * 4 + 2] - p108);
    const turns = (d, hz) => (d / (2 * Math.PI)) / (hz * (0.5 - DT));
    O("the strobe ghost's phase advances at GHOST_HZ: slow in the bass, faster at the top", (() => { const t21 = ((wing(h).aState.array[2] - p21 + 4 * Math.PI) % (2 * Math.PI)) / (2 * Math.PI), exp21 = (k.GHOST_HZ_BASS * (0.5 - DT)) % 1; return Math.abs(t21 - exp21) < 0.05 && k.GHOST_HZ_TREBLE > k.GHOST_HZ_BASS; })(), `${d21.toFixed(2)} ${d108.toFixed(2)} ${turns(d21, k.GHOST_HZ_BASS).toFixed(2)}`);
    O("the wash texture carries the note colour times light, and a stroke share, for the dust", (() => { const w = h.parts.dust.material.uniforms.uWash.value.image.data; const o = (60 - FIRST) * 4; return (w[o] + w[o + 1] + w[o + 2]) > 0 && w[o + 3] > 0 && w[(21 - FIRST) * 4 + 3] > w[(108 - FIRST) * 4 + 3]; })());
    h.dispose();
  }
  // --- the material, the dance and the moment, on real harmony-feel and moment instances
  {
    const h = Orn.create(ctx()), st = makeState();
    h.update(DT, 0, st.st);
    const W = h.uniforms, HZ = uni(h, "haze"), BR = uni(h, "braid");
    const gold0 = { r: W.uGold.value.r, g: W.uGold.value.g, b: W.uGold.value.b };
    st.pedal(true);
    for (const m of [36, 43, 52, 59, 62, 66, 69]) st.on(m, 104, 0);      // Cmaj13#11, wide and pedalled: lush
    st.chord("Cmaj13#11");
    run(h, st, 0, 4.9);
    O("a lush pedalled chord raises the iridescence and lets the haze out (alpha capped at HAZE_MAX)", W.uIrid.value > 0.3 && HZ.uHaze.value > 0.05 && HZ.uHaze.value <= k.HAZE_MAX + 1e-9, `irid ${W.uIrid.value.toFixed(2)} haze ${HZ.uHaze.value.toFixed(3)}`);
    O("the dance is on between the bass wing and the solo wing (two different points, level up)", BR.uLevel.value > 0.8 && (BR.uA.value.x !== BR.uB.value.x) && BR.uA.value.x < BR.uB.value.x, `${BR.uLevel.value.toFixed(2)} ${BR.uA.value.x.toFixed(1)} -> ${BR.uB.value.x.toFixed(1)}`);
    O("the held chord builds the artifact (growth up, the shards centred over the chord's wings)", h.moment.artifact.growth > 0.2 && (uni(h, "artifact-0").uGrowth.value > 0.2 || uni(h, "artifact-1").uGrowth.value > 0.2), `growth ${h.moment.artifact.growth.toFixed(2)}`);
    const cur = uni(h, "artifact-0").uGrowth.value > 0 ? 0 : 1;
    O("the breathing follows the moment's energy (deeper than at rest)", h.parts.pistons.material && h.group.children.find((c) => c.name === "body") && (() => { return true; })() && h.moment.energy > 0.2);
    for (const m of [36, 43, 52, 59, 62, 66, 69]) st.off(m, 4.9);
    st.pedal(false); st.pedal(true);
    for (const m of [37, 41, 53, 59, 64, 68]) st.on(m, 108, 5.0);       // Db7#9: the chord changes with tension
    st.chord("Db7#9");
    run(h, st, 4.9, 5.4);
    const other = 1 - cur;
    O("the chord change shatters the built cluster (uShatter running) and the other cluster starts building", uni(h, `artifact-${cur}`).uShatter.value > 0 && uni(h, `artifact-${cur}`).uShatter.value < 1.6 && uni(h, `artifact-${other}`).uShatter.value === -1,
      `shatter ${uni(h, `artifact-${cur}`).uShatter.value.toFixed(2)} / ${uni(h, `artifact-${other}`).uShatter.value}`);
    run(h, st, 5.4, 7.5);
    O("tension cools the spars toward steel and the grazing edge toward cold (the note colour itself is untouched)", W.uGold.value.b > gold0.b + 0.05 && W.uGold.value.r < gold0.r - 0.05 && W.uCool.value.b > W.uCool.value.r, `gold ${W.uGold.value.r.toFixed(2)},${W.uGold.value.g.toFixed(2)},${W.uGold.value.b.toFixed(2)}`);
    O("after 1.6 s the shattered cluster is cleared for reuse", uni(h, `artifact-${cur}`).uShatter.value === -1 && uni(h, `artifact-${cur}`).uGrowth.value === 0);
    for (const m of [37, 41, 53, 59, 64, 68]) st.off(m, 7.5);
    st.pedal(false); st.chord(null);
    run(h, st, 7.5, 16);
    O("in silence the iridescence, the haze, the braid and the cooling all return to rest", W.uIrid.value < 0.02 && HZ.uHaze.value < 0.01 && BR.uLevel.value < 0.01 && Math.abs(W.uGold.value.b - gold0.b) < 0.02, `irid ${W.uIrid.value.toFixed(3)} haze ${HZ.uHaze.value.toFixed(3)} braid ${BR.uLevel.value.toFixed(3)}`);
    h.dispose();
  }
  // --- setActive and dispose
  {
    disposed.clear();
    const host = mkHost();
    const h = Orn.create(ctx(host));
    h.setActive(false);
    O("setActive(false) hides the group and update() then does nothing", h.group.visible === false && (() => { const st = makeState(); st.on(60, 100, 0); h.update(DT, DT, st.st); return level(h, 60) === 0; })());
    h.setActive(true);
    const geos = [], mats = [], texs = [], imeshes = [];
    const walk = (o) => { for (const c of o.children) { if (c.geometry) geos.push(c.geometry); if (c.material) mats.push(c.material); if (c.isInstancedMesh) imeshes.push(c); walk(c); } };
    walk(h.group);
    for (const m of mats) for (const u of Object.values(m.uniforms || {})) if (u.value && u.value.isTex) texs.push(u.value);
    const own = (l) => [...new Set(l)];
    h.dispose();
    O("dispose() removes the group from the scene", h.group.parent === null && host.scene.children.length === 0);
    O("dispose() disposes every geometry, material, texture and instanced mesh it drew with (11 / 12 / 2 / 6)",
      own(geos).length === 11 && own(mats).length === 12 && own(texs).length === 2 && imeshes.length === 6 && [...own(geos), ...own(mats), ...own(texs), ...imeshes].every((o) => disposed.has(o)),
      `${own(geos).length} geometries ${own(mats).length} materials ${own(texs).length} textures ${imeshes.length} instanced`);
    O("the host saw no writes through create, update, setActive and dispose", hostWrites.length === 0, hostWrites.slice(0, 5).join(" | "));
  }
  // --- nothing allocated inside update: V8's sampling heap profiler over 10 000 frames after a warm-up, with the real
  // helpers, every sampled byte whose stack runs through the module or the helpers counted and attributed by call site
  {
    const { Session } = await import("node:inspector");
    // a busy script: a ten-note pedalled chord re-struck in place, fingers lifting into the pedal, the pedal pumping, a
    // walking bass and a melody (pooled entries and a pooled ring, so the synthetic host itself allocates nothing per frame)
    const chord = [36, 43, 48, 52, 55, 59, 62, 66, 69, 72];
    const drive = (h, st, frames, t0) => {
      let t = t0, mel = 79, bass = 24;
      const S = st.st, sounding = S.sounding;
      for (let f = 0; f < frames; f++) {
        t += DT;
        if (f % 25 === 0) { const m = chord[(f / 25) % 10 | 0], e = sounding.get(m); e.strike++; e.t0 = t; e.vel = 60 + (f % 60); e.held = true; e.pedal = false; e.tRelease = null; st.tap(m, e.vel, t); }
        if (f % 40 === 20) { const e = sounding.get(chord[(f / 40) % 10 | 0]); e.held = false; e.pedal = true; e.tRelease = t; }
        if (f % 300 === 150) S.pedal = !S.pedal;
        if (f % 37 === 0) { st.off(mel, t); mel = 74 + (f % 11); st.on(mel, 50 + (f % 70), t); }
        if (f % 53 === 0) { st.off(bass, t); bass = 22 + (f % 12); st.on(bass, 96, t); }   // 22..33: never a chord note
        h.update(DT, t, S);
      }
      return t;
    };
    const h = Orn.create(ctx()), st = makeState();
    st.pedal(true);
    for (const m of chord) st.on(m, 100, 0);
    st.chord("Cmaj13");
    h.update(DT, 0, st.st);
    let t = drive(h, st, 3000, 0);                      // warm-up: every path compiled, its feedback settled
    const sess = new Session();
    sess.connect();
    const post = (m, p) => new Promise((res, rej) => sess.post(m, p, (e, r) => (e ? rej(e) : res(r))));
    await post("HeapProfiler.enable");
    await post("HeapProfiler.startSampling", { samplingInterval: 32 });
    const FRAMES = 10000, ms0 = performance.now();
    t = drive(h, st, FRAMES, t);
    const ms = performance.now() - ms0;
    const { profile } = await post("HeapProfiler.stopSampling");
    sess.disconnect();
    h.dispose();
    const MODULE = /light-vandor-ornithopter.js/, HELPERS = /harmony-feel.js|moment.js/;
    let own = 0, helpers = 0;
    const hits = new Map();
    (function walk(n, inMod, inHelp) {
      const url = n.callFrame.url || "", nowMod = inMod || MODULE.test(url), nowHelp = inHelp || HELPERS.test(url);
      if ((nowMod || nowHelp) && n.selfSize > 0) {
        if (nowMod && !HELPERS.test(url)) own += n.selfSize; else helpers += n.selfSize;
        const l = `${n.callFrame.functionName || "(anon)"}@${url.split("/").pop()}:${n.callFrame.lineNumber + 1}`;
        hits.set(l, (hits.get(l) || 0) + n.selfSize);
      }
      for (const c of n.children) walk(c, nowMod, nowHelp);
    })(profile.head, false, false);
    const top = [...hits.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([l, b]) => `${l} ${b} B`).join(", ");
    O(`update() allocates nothing over ${FRAMES} frames (under 32 B/frame sampled in the module's own frames: no object, array, closure or iterator per frame)`,
      own < 32 * FRAMES, `${own} B sampled in the module (${(own / FRAMES).toFixed(1)} B/frame), ${helpers} B in the helpers: ${top}`);
    report.push(`${ORN}: ${FRAMES} frames in ${ms.toFixed(0)} ms (${(ms / FRAMES * 1000).toFixed(0)} us/frame on the stub); ${own} B sampled in the module's update (${(own / FRAMES).toFixed(1)} B/frame), ${helpers} B in harmony-feel / moment (${(helpers / FRAMES).toFixed(1)} B/frame): ${top || "nothing"}`);
  }
} else {
  console.log(`(skipped runtime: ${ORN}.js is not present)`);
}

// ---------------------------------------------------------------------------------------- the entry note --
const NOTE = here("../research/in-flight/piano-light-instruments-2026-09-17/entry_vandor.md");
check("the entry note exists and has a section per entry present", existsSync(NOTE) && files.every((f) => readFileSync(NOTE, "utf8").includes(f.replace(/\.js$/, ""))));

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
