// Node test for the string light envelope and the vibration blur — arsenal/web/piano/instruments/concert-grand.js and
// glass-piano.js. Zero dependencies, no GPU:
//   node tests/piano_string_envelope.test.mjs
//
// Neither instrument module can be imported here (it wants a live THREE and a scene), so this reads their tuning
// constants out of the source and checks the PROPERTIES Daniel asked for, in bands wide enough that the look can still
// be tuned. It is a guard against a careless edit, not a freeze:
//   "the color decay doesn't fully match the sustain of the length of the note ... the decay should be slower and have a
//    higher floor" and "notes that are lower could have more of a blur and vibration similar to the wings in the
//    helicopters from the movie Dune" (2026-09-17).
// It also pins the wiring that makes the light last as long as the sound: both instruments read state.sounding, gate the
// blur on the per-note envelope and never on state.pedal, and keep the strings in the opaque list with alpha 1 at rest.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const FILES = {
  "concert-grand": readFileSync(here("../arsenal/web/piano/instruments/concert-grand.js"), "utf8"),
  "glass-piano": readFileSync(here("../arsenal/web/piano/instruments/glass-piano.js"), "utf8"),
};
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
// every `const NAME = number` at the top level of a file, as a map
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

const K = {};
for (const [id, src] of Object.entries(FILES)) {
  K[id] = constants(src);
  const need = ["PEAK_EXP", "FLASH_EXP", "FLOOR_LO", "FLOOR_HI", "AFTER_SHARE", "TAU_PROMPT_BASS", "TAU_PROMPT_TREBLE",
    "TAU_AFTER_BASS", "TAU_AFTER_TREBLE", "TAU_FLASH", "TAU_DAMP", "DAMP_FADE", "TAU_VIB_OFF", "AMP_BASS", "AMP_TREBLE",
    "AMP_EXP", "VIB_HZ_BASS", "VIB_HZ_TREBLE", "BLUR_CONSERVE", "STRING_MIN_PX"];
  const missing = need.filter((n) => !(n in K[id]));
  check(`${id}: the envelope and blur constants are all named in one block`, missing.length === 0, missing.join(", "));
}
if (fail) { console.log(`${pass} passed, ${fail} failed`); process.exit(1); }

// The envelope the two instruments integrate, written out once here so the properties can be measured.
function envelope(k, m, vel) {
  const p = (m - 21) / 87;
  const over = (lo, hi) => lo * Math.pow(hi / lo, p);
  const tauP = over(k.TAU_PROMPT_BASS, k.TAU_PROMPT_TREBLE), tauA = over(k.TAU_AFTER_BASS, k.TAU_AFTER_TREBLE);
  const v = vel / 127, peak = Math.pow(v, k.PEAK_EXP);
  const floor = peak * (k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * v), above = peak - floor;
  return {
    peak, floor, tauP, tauA,
    amp: (t) => over(k.AMP_BASS, k.AMP_TREBLE) * Math.pow(Math.max(0, envelope(k, m, vel).body(t)), k.AMP_EXP),
    body: (t) => floor + above * (1 - k.AFTER_SHARE) * Math.exp(-t / tauP) + above * k.AFTER_SHARE * Math.exp(-t / tauA),
    // the damper's fade: the body keeps falling at TAU_DAMP inside a window that closes it to exactly 0 at DAMP_FADE
    damped: (t, since) => {
      if (since >= k.DAMP_FADE) return 0;
      const u = since / k.DAMP_FADE;
      return envelope(k, m, vel).body(t) * Math.exp(-since / k.TAU_DAMP) * (1 - u * u * (3 - 2 * u));
    },
  };
}

for (const [id, k] of Object.entries(K)) {
  // --- Daniel's first ask: a higher floor, clearly readable, for as long as the note sounds ---
  const frac = (vel) => k.FLOOR_LO + (k.FLOOR_HI - k.FLOOR_LO) * (vel / 127);
  check(`${id}: the floor is 30-45 % of the strike body at mid velocity`, frac(64) >= 0.30 && frac(64) <= 0.45
    && frac(96) >= 0.30 && frac(96) <= 0.48, `vel 64 ${frac(64).toFixed(3)}, vel 96 ${frac(96).toFixed(3)}`);
  check(`${id}: the floor rises with velocity and never reaches the strike level`, k.FLOOR_HI > k.FLOOR_LO && k.FLOOR_HI < 0.7);
  for (const m of [21, 45, 60, 84, 108]) {
    const e = envelope(k, m, 96);
    // the floor is a FLOOR: the body never falls under it, however long the pedal holds the note
    const late = e.body(600);
    check(`${id}: m${m} still shows its floor ten minutes into a pedalled note`, Math.abs(late - e.floor) < 1e-9 && late > 0,
      `${late.toFixed(4)} vs floor ${e.floor.toFixed(4)}`);
    check(`${id}: m${m} at 5 s is at least 40 % of its strike body (HEAD's exponential was under 8 %)`,
      e.body(5) / e.peak >= 0.40, `${(e.body(5) / e.peak).toFixed(3)}`);
    check(`${id}: m${m} decays monotonically from the strike toward the floor`,
      [0.1, 0.5, 1, 2, 5, 10].every((t, i, a) => i === 0 || e.body(t) <= e.body(a[i - 1]) + 1e-12) && e.body(0.1) < e.peak);
  }
  // --- two stages, and the bass ringing longer than the treble ---
  const bass = envelope(k, 21, 96), treble = envelope(k, 108, 96);
  check(`${id}: the prompt decay is roughly 0.4-1.05 s across the keyboard`, bass.tauP <= 1.05 && treble.tauP >= 0.4
    && bass.tauP > treble.tauP, `${bass.tauP.toFixed(2)} at A0, ${treble.tauP.toFixed(2)} at C8`);
  check(`${id}: the aftersound lasts seconds in the bass and is much shorter at the top`, bass.tauA >= 4 && treble.tauA <= 2
    && bass.tauA / treble.tauA >= 3, `${bass.tauA.toFixed(2)} / ${treble.tauA.toFixed(2)}`);
  check(`${id}: the aftersound is slower than the prompt decay at every pitch`,
    [21, 40, 60, 80, 108].every((m) => { const e = envelope(k, m, 96); return e.tauA > e.tauP * 2; }));
  check(`${id}: the strike flash is fast and velocity-shaped, and steeper than the prompt decay`,
    k.TAU_FLASH > 0 && k.TAU_FLASH <= 0.15 && k.FLASH_EXP > k.PEAK_EXP && k.TAU_FLASH < treble.tauP);
  // --- the end of a sound is a visible fade, not a snap, and it is OVER: the light must never outlive the sound ---
  check(`${id}: the whole damping fade is 0.2-0.35 s`, k.DAMP_FADE >= 0.2 && k.DAMP_FADE <= 0.35, String(k.DAMP_FADE));
  check(`${id}: the fall inside the window is quicker than the window, so the string is nearly out before it closes`,
    k.TAU_DAMP > 0 && k.TAU_DAMP < k.DAMP_FADE * 0.7, `TAU_DAMP ${k.TAU_DAMP} vs DAMP_FADE ${k.DAMP_FADE}`);
  const e96 = envelope(k, 45, 96), rel96 = e96.body(3);      // the level at the moment the sound ends
  check(`${id}: 0.1 s after the sound ends the string is still clearly visible`, e96.damped(3, 0.1) > rel96 * 0.30,
    `${(e96.damped(3, 0.1) / rel96).toFixed(3)} of the level at the release`);
  check(`${id}: by 0.4 s the string is at rest, nothing left on screen (a bare TAU_DAMP still showed 18 % there)`,
    e96.damped(3, 0.4) === 0 && e96.damped(3, k.DAMP_FADE) === 0, `${e96.damped(3, 0.4).toFixed(5)} at +0.4 s`);
  check(`${id}: 0.4 s after a mf note stopped sounding it is darker than a quiet note that IS sounding`,
    e96.damped(3, 0.4) < envelope(k, 45, 40).floor);
  {   // a fade and not a snap: no single 60 fps step may take out a fifth of the level the note had at its release
    let worst = 0, prev = rel96;
    for (let x = 1 / 60; x <= k.DAMP_FADE + 0.2; x += 1 / 60) {
      const v = e96.damped(3, x); worst = Math.max(worst, (prev - v) / rel96); prev = v;
    }
    check(`${id}: every 60 fps step of the fade is under a fifth of the level at the release`, worst < 0.2,
      `worst step ${(worst * 100).toFixed(1)} %`);
  }
  check(`${id}: the blur stops before the light does (TAU_VIB_OFF < TAU_DAMP)`, k.TAU_VIB_OFF < k.TAU_DAMP);

  // --- Daniel's second ask: lower notes blur more, higher notes shimmer ---
  const ampAt = (m) => k.AMP_BASS * Math.pow(k.AMP_TREBLE / k.AMP_BASS, (m - 21) / 87);
  check(`${id}: the swing is widest at A0 and narrows all the way to C8`,
    [21, 33, 48, 60, 84, 108].every((m, i, a) => i === 0 || ampAt(m) < ampAt(a[i - 1])) && ampAt(21) / ampAt(108) >= 5,
    `${ampAt(21).toFixed(3)} -> ${ampAt(108).toFixed(3)} units`);
  check(`${id}: a bass swing is wide enough to read and not so wide it swallows the harp (0.15-0.7 units)`,
    ampAt(21) >= 0.15 && ampAt(21) <= 0.7, String(ampAt(21)));
  check(`${id}: the top of the keyboard is a shimmer, not a swing (under 0.08 units)`, ampAt(108) <= 0.08, String(ampAt(108)));
  check(`${id}: the blur's visual rate is slow in the bass and faster at the top, and well under half the frame rate`,
    k.VIB_HZ_BASS < k.VIB_HZ_TREBLE && k.VIB_HZ_TREBLE <= 15 && k.VIB_HZ_BASS >= 1,
    `${k.VIB_HZ_BASS} -> ${k.VIB_HZ_TREBLE} Hz`);
  check(`${id}: the amplitude follows the envelope, so it narrows as the note settles and is 0 when nothing sounds`,
    k.AMP_EXP > 0 && k.AMP_EXP <= 1);
  check(`${id}: a wider blur is fainter per pixel (bloom stays out of it), but not fully conserved`,
    k.BLUR_CONSERVE > 0 && k.BLUR_CONSERVE < 1, String(k.BLUR_CONSERVE));
  check(`${id}: a string at rest keeps a pixel-wide floor`, k.STRING_MIN_PX >= 0.4 && k.STRING_MIN_PX <= 1.5);
  report.push(`${id}: floor ${(frac(64) * 100).toFixed(0)} % at vel 64 / ${(frac(96) * 100).toFixed(0)} % at vel 96; `
    + `prompt ${bass.tauP.toFixed(2)}-${treble.tauP.toFixed(2)} s, aftersound ${bass.tauA.toFixed(1)}-${treble.tauA.toFixed(1)} s, `
    + `damping ${k.TAU_DAMP} s inside a ${k.DAMP_FADE} s window; swing ${ampAt(21).toFixed(3)} -> ${ampAt(108).toFixed(3)} units at ${k.VIB_HZ_BASS}-${k.VIB_HZ_TREBLE} Hz`);
}

// --- the two instruments answer a pedal the same way ---
const shared = ["PEAK_EXP", "FLASH_EXP", "FLOOR_LO", "FLOOR_HI", "AFTER_SHARE", "TAU_PROMPT_BASS", "TAU_PROMPT_TREBLE",
  "TAU_AFTER_BASS", "TAU_AFTER_TREBLE", "TAU_FLASH", "TAU_DAMP", "DAMP_FADE", "TAU_VIB_OFF", "AMP_BASS", "AMP_TREBLE",
  "AMP_EXP", "VIB_HZ_BASS", "VIB_HZ_TREBLE", "BLUR_CONSERVE"];
const differ = shared.filter((n) => K["concert-grand"][n] !== K["glass-piano"][n]);
check("the concert grand and the crystal grand hold the same envelope and blur tuning", differ.length === 0,
  differ.map((n) => `${n} ${K["concert-grand"][n]} vs ${K["glass-piano"][n]}`).join(", "));

// --- the wiring, in the source ---
for (const [id, src] of Object.entries(FILES)) {
  check(`${id}: the light is driven by state.sounding, the page's own sustain record`,
    /state\.sounding/.test(src) && /e\.strike !== seenStrike\[/.test(src));
  check(`${id}: a sound that ends damps instead of snapping, and only then`,
    /bFloor\[[im]\] \*= kDamp; bPrompt\[[im]\] \*= kDamp; bAfter\[[im]\] \*= kDamp;/.test(src));
  check(`${id}: that fade has an END — a window closes it to 0 by DAMP_FADE, applied on read so it cannot compound`,
    /const dampFade = \(x\) => \{ if \(x >= DAMP_FADE\) return 0;/.test(src)
    && /dampT\[[im]\] \+= dt;/.test(src)
    && /if \(dampT\[[im]\] > 0\) b \*= dampFade\(dampT\[[im]\]\);/.test(src)
    && /dampT\[[im]\] = 0;/.test(src));
  check(`${id}: a re-strike carries the level it finds (never a dip to dark first)`,
    /const carry = Math\.max\(0, body(?:Lvl)?\[[im]\] - peak\);/.test(src)
    && /bPrompt\[[im]\] = \(above \* \(1 - AFTER_SHARE\) \+ carry\)/.test(src));
  check(`${id}: the pedal never makes an unstruck string vibrate (the swing comes from the note's own envelope)`,
    /ampMax\[[im]\] \* Math\.pow\(b, AMP_EXP\)/.test(src) && !/amp\s*=\s*[^;]*pedal/.test(src));
  check(`${id}: the strings stay in the opaque list (CustomBlending, transparent false), so a transmission pass keeps them`,
    /blending: THREE\.CustomBlending, blendSrc: THREE\.SrcAlphaFactor, blendDst: THREE\.OneMinusSrcAlphaFactor/.test(src)
    && /transparent: false/.test(src));
  check(`${id}: the ribbon is nailed to the string's ends (sin(pi u)) and fades on the long-exposure density`,
    /sin\(3\.14159265 \* aParam\.x\)/.test(src) && /inversesqrt\(max\(1\.0 - d \* d/.test(src));
  check(`${id}: the header carries the tuning table Daniel's words are in`,
    /slower and have a higher floor/.test(src) && /ornithopter/.test(src) && /movie Dune/.test(src));
}

// --- the crystal grand's hammer-flight gate must never blank a string that is already lit ---
// Re-arming it on a re-strike dropped the note to full dark for the 18-33 ms before the new flash, throwing away exactly
// the level the carry had just preserved. The concert grand lights on the strike and has no such gate at all.
{
  const src = FILES["glass-piano"];
  check("glass-piano: the hammer-flight gate is armed only for a string that was dark",
    /const lit = bodyLvl\[i\] > 0;/.test(src) && /riseT\[i\] = lit \? -1e9 : t0 \+ \(0\.055 - 0\.037 \* v\);/.test(src));
  check("glass-piano: the gate is read in one place only, so nothing else can reintroduce the blank",
    (src.match(/riseT\[i\]/g) || []).length === 2 && /const on = t >= riseT\[i\] \? 1 : 0;/.test(src));
  check("concert-grand: there is no hammer-flight gate there to re-arm", !/riseT/.test(FILES["concert-grand"]));
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
