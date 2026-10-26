// Node tests for the VJ rig's pure logic (arsenal/web/vj-core.js). Zero dependencies:
//   node tests/vj_core.test.mjs
// Sections: gate v2 (vj-gate.js: the final-output flash limiter and the verifier's flash counter); the event contract; the engine link (when the page may post pad colours); the flash gate (three flashes in any second, and the shader twin of envFlashSafe); ADSR and
// the effect bank (velocity, hold and release, dampen, choke, the fixed pool); the beat clock (scheduling, refreshed
// predictions, the flywheel); the pedal detector (Joy to the World's repeated D-flat over a walking bass, and Daniel's
// whole real take through it: tests/fixtures/vj/joy_take_events.json); the star layout;
// the pad and control maps; the strip layout every VJ preset reads; the demo script; and the pitch colours baked into the
// presets (they must equal the piano's palette as ported here).
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as C from "../arsenal/web/vj-core.js";
import * as G from "../arsenal/web/vj-gate.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
function check(name, cond, detail = "") {
  if (cond) pass++;
  else { fail++; console.log(`FAIL ${name}${detail ? `: ${detail}` : ""}`); }
}
const near = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps;

// ------------------------------------------------------------------------------------------------ the contract --
{
  const P = C.parseEvent;
  check("hello", P({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", pads_mode: "both" }).pads_mode === "both");
  check("hello with an unknown pads_mode keeps none", P({ t: "hello", pads_mode: "weird" }).pads_mode === "");
  const b = P({ t: "beat", due_ms: 220, bpm: 121.5, conf: 2, n: 7, on_beat: null });
  check("beat clamps conf", b.conf === 1 && b.n === 7 && b.on_beat === null && b.bpm === 121.5);
  check("beat without bpm is refused", P({ t: "beat", due_ms: 100 }) === null);
  check("energy clamps", P({ t: "energy", bass: 3, mid: -1, high: 0.5, level: NaN }).bass === 1);
  check("hit band defaults to full", P({ t: "hit", strength: 0.4, band: "cowbell" }).band === "full");
  const ch = P({ t: "chord", src: "audio", name: "Dbmaj7", root: 13, pcs: [1, 5, 8, 12, 1, 0.5] });
  check("chord root and pcs fold into 0..11 and dedupe", ch.root === 1 && ch.pcs.join() === "1,5,8,0" && ch.src === "audio");
  check("note off", P({ t: "note", key: 61, vel: 0, on: false }).on === false);
  check("note out of range refused", P({ t: "note", key: 128, vel: 1, on: true }) === null);
  check("pad out of range refused", P({ t: "pad", pad: 13, vel: 1, on: true }) === null);
  const pad = P({ t: "pad", pad: 3, vel: 0.5, on: true, src: "bank" });
  check("pad", pad.pad === 3 && pad.src === "bank" && pad.on);
  const ctl = P({ t: "ctl", id: "cc105", kind: "rel", value: 0.5, delta: -3 });
  check("ctl rel", ctl.kind === "rel" && ctl.delta === -3);
  check("ctl keeps the engine's port, and only a known one",
        P({ t: "ctl", id: "cc25", kind: "abs", value: 1, port: "daw" }).port === "daw" &&
        P({ t: "ctl", id: "cc25", kind: "abs", value: 1, port: "evil" }).port === undefined && ctl.port === undefined);
  check("ctl with a hostile id refused", P({ t: "ctl", id: "<script>", kind: "abs", value: 1 }) === null);
  check("unknown type refused", P({ t: "nope" }) === null && P(null) === null && P("x") === null);
  const hNo = P({ t: "hello", v: 1, src: "keylab-vj", leds: false, leds_reason: "LEDs are off (--no-leds)" });
  check("hello says whether the engine has LEDs", hNo.leds === false && hNo.leds_reason === "LEDs are off (--no-leds)" &&
        P({ t: "hello", leds: true }).leds === true);
  check("an older engine's hello (no leds field) leaves it unknown", P({ t: "hello", v: 1 }).leds === null &&
        P({ t: "hello", leds: "yes" }).leds === null);
}

// ------------------------------------------------- the contract: chordsense's key, tension and chord fields --
// vj --chords sense (arsenal/keylab/vj.py, chordsense.to_vj_events): key {name, conf}, tension {value, pedal_pc}, and the
// chord's roman / key / bass / conf. Clamped like every other number; malformed -> null; an engine that sends none of it
// (--chords basic, an older engine, the page's demo) still parses exactly as before.
{
  const P = C.parseEvent;
  const k = P({ t: "key", name: "Db major", conf: 0.82, src: "keys" });
  check("key", k.t === "key" && k.name === "Db major" && near(k.conf, 0.82) && k.src === "keys");
  check("key conf clamps", P({ t: "key", name: "F# minor", conf: 7 }).conf === 1 && P({ t: "key", name: "A minor", conf: -2 }).conf === 0);
  check("key without a src keeps none", P({ t: "key", name: "C major", conf: 0.5 }).src === "" &&
        P({ t: "key", name: "C major", conf: 0.5, src: "<b>" }).src === "");
  check("key with no name is refused", P({ t: "key", conf: 0.5 }) === null && P({ t: "key", name: null, conf: 0.5 }) === null);
  check("key with a name chordsense could not write is refused", P({ t: "key", name: "H major", conf: 0.5 }) === null &&
        P({ t: "key", name: "Db dorian", conf: 0.5 }) === null && P({ t: "key", name: "<script>", conf: 0.5 }) === null &&
        P({ t: "key", name: "Db major ".repeat(9), conf: 0.5 }) === null);
  check("key without a confidence is refused", P({ t: "key", name: "C major" }) === null &&
        P({ t: "key", name: "C major", conf: "high" }) === null && P({ t: "key", name: "C major", conf: NaN }) === null);

  const tn = P({ t: "tension", value: 0.42, pedal_pc: 1, src: "audio" });
  check("tension", tn.value === 0.42 && tn.pedal_pc === 1 && tn.src === "audio");
  check("tension clamps", P({ t: "tension", value: 3 }).value === 1 && P({ t: "tension", value: -1 }).value === 0);
  check("tension with no pedal says -1", P({ t: "tension", value: 0.2, pedal_pc: null }).pedal_pc === -1 &&
        P({ t: "tension", value: 0.2 }).pedal_pc === -1);
  // -1 is the page's own "none", so it never wraps to 11 (B); a number past 11 is no pitch class, not a folded one
  check("tension pedal out of 0..11 is none, never wrapped", P({ t: "tension", value: 0.2, pedal_pc: 13 }).pedal_pc === -1 &&
        P({ t: "tension", value: 0.2, pedal_pc: -1 }).pedal_pc === -1 && P({ t: "tension", value: 0.2, pedal_pc: 99 }).pedal_pc === -1);
  check("chord bass out of 0..11 is none", P({ t: "chord", name: "C", root: 0, pcs: [0, 4, 7], bass: -1 }).bass === -1 &&
        P({ t: "chord", name: "C", root: 0, pcs: [0, 4, 7], bass: 16 }).bass === -1 &&
        P({ t: "chord", name: "C/E", root: 0, pcs: [0, 4, 7], bass: 4 }).bass === 4);
  check("a no-chord carries no numeral", P({ t: "chord", name: "N", root: null, pcs: [], roman: "IV" }).roman === "");
  check("tension without a value is refused", P({ t: "tension" }) === null && P({ t: "tension", value: "0.4" }) === null &&
        P({ t: "tension", value: Infinity }) === null);
  check("tension with a pedal that is no pitch class is refused", P({ t: "tension", value: 0.3, pedal_pc: 1.5 }) === null &&
        P({ t: "tension", value: 0.3, pedal_pc: "Db" }) === null);

  const ch = P({ t: "chord", src: "keys", name: "Gb", root: 6, quality: "maj", pcs: [6, 10, 1], changed: true,
                 bass: 6, roman: "IV", key: "Db major", conf: 1 });
  check("chord carries roman, key, bass and conf", ch.roman === "IV" && ch.key === "Db major" && ch.bass === 6 && ch.conf === 1);
  const inv = P({ t: "chord", src: "audio", name: "Ab7/C", root: 8, quality: "7", pcs: [0, 3, 6, 8], bass: 12,
                  roman: "V65", key: "Db major", conf: 1.7 });
  check("chord bass outside 0..11 is none (the contract sends 0..11), conf clamps", inv.bass === -1 && inv.conf === 1 && inv.roman === "V65");
  for (const r of ["bVII", "vii°", "V7/V", "V43/IV", "IVmaj42", "i64", "Vsus4", "#IV", "bII", "I5", "bVIadd9", "III+"]) {
    check(`roman ${r} is taken`, P({ t: "chord", name: "x", root: 0, roman: r }).roman === r);
  }
  const bad = P({ t: "chord", src: "audio", name: "C", root: 0, quality: "maj", pcs: [0, 4, 7], bass: "C", roman: "<img>",
                  key: "C lydian", conf: "sure" });
  check("malformed new chord fields empty out, the chord stays", bad !== null && bad.name === "C" && bad.bass === -1 &&
        bad.roman === "" && bad.key === "" && bad.conf === null);
  check("a long roman is refused", P({ t: "chord", name: "C", root: 0, roman: "IIIIIIIIIIIIIIIIII" }).roman === "");
  const old = P({ t: "chord", src: "keys", name: "Dbmaj7", root: 1, quality: "maj7", pcs: [1, 5, 8, 0], changed: true });
  check("an older engine's chord parses as before, the new fields empty", old.name === "Dbmaj7" && old.root === 1 &&
        old.pcs.join() === "1,5,8,0" && old.roman === "" && old.key === "" && old.bass === -1 && old.conf === null);
  const none = P({ t: "chord", src: "audio", name: "N", root: null, quality: null, pcs: [], bass: null, roman: null,
                   key: "A minor", conf: 1, changed: true });
  check("the audio's no-chord (N)", none.name === "N" && none.root === -1 && none.pcs.length === 0 && none.bass === -1 &&
        none.roman === "" && none.key === "A minor");
  check("hello says which chord engine runs", P({ t: "hello", chords: "sense" }).chords === "sense" &&
        P({ t: "hello", chords: "basic" }).chords === "basic" && P({ t: "hello" }).chords === "" &&
        P({ t: "hello", chords: "magic" }).chords === "");
}

// ------------------------------------------------------------------------------------- the engine's harmony --
{
  const P = C.parseEvent;
  const H = new C.EngineHarmony();
  check("no engine tension: the page's own estimate is the harmonic term", !H.live && H.harmonic(0.37) === 0.37 &&
        near(H.stripTension(0.37, 0.9), 0.72));
  check("a key landing is a change (the page accents it)", H.event(P({ t: "key", name: "Db major", conf: 0.6 })) === true &&
        H.key === "Db major" && H.keyChanges === 1);
  check("the same key again is not", H.event(P({ t: "key", name: "Db major", conf: 0.9 })) === false && H.keyChanges === 1 &&
        near(H.keyConf, 0.9));
  check("a modulation is", H.event(P({ t: "key", name: "Eb major", conf: 0.7 })) === true && H.keyChanges === 2);
  H.event(P({ t: "tension", value: 0.6, pedal_pc: 1, src: "keys" }));
  check("the first engine tension is taken as it is", H.live && near(H.value, 0.6) && H.pedalPc === 1);
  check("... and REPLACES the page's harmonic estimate: never both", near(H.harmonic(0.95), 0.6) &&
        near(H.harmonic(0.1), 0.6));
  check("the page's pedal star still counts, through the same max", near(H.stripTension(0.95, 0.5), 0.6) &&
        near(H.stripTension(0.1, 1), 0.8));
  H.event(P({ t: "tension", value: 0.1, pedal_pc: null }));
  H.update(0.1);
  check("a step down eases (~0.8 s)", H.value < 0.6 && H.value > 0.5 && H.pedalPc === -1, `${H.value}`);
  for (let i = 0; i < 300; i++) H.update(1 / 60);
  check("and arrives", near(H.value, 0.1, 1e-3));
  H.event(P({ t: "tension", value: 0.9 }));
  H.update(0.1);
  check("a step up eases faster (~0.35 s)", H.value > 0.1 + 0.2 * 0.8 && H.value < 0.9);
  H.reset();
  check("reset (a new hello, a dropped engine) gives the page its own estimate back", !H.live && H.key === "" &&
        H.harmonic(0.2) === 0.2 && H.keyChanges === 2);
}

// ------------------------------------------------------------------------------------------- the engine link --
{
  const P = C.parseEvent;
  const L = new C.EngineLink();
  check("nothing is posted before the engine is connected", !L.mayPostLeds());
  L.connected();
  L.event(P({ t: "hello", v: 1, src: "keylab-vj", leds: false, leds_reason: "LEDs are off (--no-leds)" }));
  check("an engine whose hello says leds false is not posted to", !L.mayPostLeds() && L.ledsOff === "LEDs are off (--no-leds)");
  L.event(P({ t: "hello", v: 1, src: "keylab-vj", leds: true }));
  check("a hello with leds true allows posting", L.mayPostLeds());
  const gen = L.gen;
  check("a 202 is not a refusal", L.postResult(202, gen) === false && L.mayPostLeds());
  check("a 409 stops posting", L.postResult(409, gen) === true && !L.mayPostLeds() && L.refused === 1);
  check("... and keeps it stopped (no retry timer)", !L.mayPostLeds());
  L.event(P({ t: "status", msg: "pads repainted" }));
  check("a status does not lift it", !L.mayPostLeds());
  L.event(P({ t: "hello", v: 1, src: "keylab-vj", leds: true }));
  check("the next hello lifts it", L.mayPostLeds());
  check("a late refusal of a post made before that hello is ignored", L.postResult(409, gen) === false && L.mayPostLeds());
  check("a 503 (no DAW output, or stopping) stops posting too", L.postResult(503) === true && !L.mayPostLeds());
  L.event(P({ t: "hello", v: 1, src: "keylab-vj" }));
  check("an older engine's hello allows posting", L.mayPostLeds());
  L.event(P({ t: "status", msg: "audio: 0.30 s behind" }));
  L.disconnected();
  check("a dropped connection forgets the engine's status and hello", L.status === "" && L.hello === null && !L.open &&
        !L.mayPostLeds());
}

// --------------------------------------------------------------------------------------------------- the gate --
{
  const g = new C.FlashGate();
  let granted = 0;
  for (let i = 0; i < 10; i++) if (g.request(i * 0.1)) granted++;      // ten requests in 0.9 s
  check("ten requests in a second give three flashes", granted === 3, `granted ${granted}`);
  check("the gate's log agrees", g.maxInAnyWindow() <= 3 && g.refused === 7);
  check("granted onsets are a third of a second apart", g.log().every((t, i, a) => i === 0 || t - a[i - 1] >= 1 / 3 - 1e-9));
  const g2 = new C.FlashGate();
  let n = 0;
  for (let t = 0; t < 10; t += 0.01) if (g2.request(t)) n++;              // a strobe asking 100 times a second for 10 s
  check("a fast strobe never beats three a second", g2.maxInAnyWindow() <= 3 && n <= 30, `${n} in 10 s, max ${g2.maxInAnyWindow()}`);
  check("envFlashSafe twin", C.envFlashSafe(0.2) === 0 && C.envFlashSafe(0.5) === 1 && C.envFlashSafe(0.6) === 1 &&
        C.envFlashSafe(0.4) > 0 && C.envFlashSafe(0.4) < 1);
  check("the first flash is unattenuated", C.envFlashSafe(new C.FlashGate().prevGap) === 1);
}

// --------------------------------------------------------------------------------------------- ADSR and bank --
{
  const def = { a: 0.1, d: 0.2, s: 0.5, r: 0.4 };
  check("adsr attack", near(C.adsr(def, 0.05, 0, null), 0.5));
  check("adsr peak", near(C.adsr(def, 0.1, 0, null), 1));
  check("adsr sustain", near(C.adsr(def, 2, 0, null), 0.5));
  check("adsr release starts at the sustain", near(C.adsr(def, 2, 0, 2), 0.5));
  check("adsr release ends at zero", C.adsr(def, 2.401, 0, 2) === 0);
  check("adsr release is monotone", C.adsr(def, 2.1, 0, 2) > C.adsr(def, 2.3, 0, 2));
  check("adsr dampened release is faster", C.adsr(def, 2.1, 0, 2, 1, 0.15) === 0 && C.adsr(def, 2.03, 0, 2, 1, 0.15) > 0);
  check("a dampened release is never shorter than 60 ms", near(C.releaseTime({ r: 0.18 }, 0.15), 0.06) &&
        near(C.releaseTime({ r: 0.04 }, 0.15), 0.04) && near(C.releaseTime({ r: 0.9 }, 0.15), 0.135));

  const bank = new C.EffectBank();
  const one = bank.trigger("shockwave", 1, 0, { pad: 1 });
  bank.update(0.01);
  check("a one-shot starts", one.active && one.env > 0.9);
  bank.release(1, 0.05);                                 // the pad lets go: a one-shot plays on
  bank.update(0.3);
  check("a one-shot ignores the pad's release", one.active && one.env > 0);
  check("velocity lengthens a one-shot", C.adsr(C.EFFECTS.shockwave, 0.8, 0, null, 0.6 + 0.8 * 1) >
        C.adsr(C.EFFECTS.shockwave, 0.8, 0, null, 0.6 + 0.8 * 0.1));
  bank.update(3);
  check("a one-shot ends", !one.active);

  const held = bank.trigger("particles", 0.8, 10, { pad: 6 });
  bank.update(12);
  check("a holdable sustains while held", held.active && near(held.env, C.EFFECTS.particles.s));
  bank.release(6, 12);
  bank.update(12 + C.EFFECTS.particles.r * 0.5);
  check("a holdable releases on note-off", held.active && held.env < C.EFFECTS.particles.s);
  bank.update(12 + C.EFFECTS.particles.r + 0.01);
  check("and is gone after its release", !held.active);

  const h2 = bank.trigger("strobe", 1, 20, { pad: 5 });
  const o2 = bank.trigger("laser", 1, 20, { pad: 2 });
  bank.update(20.05);
  const before = h2.env;
  bank.dampen(20.05);
  bank.update(20.052);
  check("dampen releases from where it is (no cut)", h2.active && h2.env > 0.85 * before, `${before} -> ${h2.env}`);
  bank.update(20.05 + 0.07);
  check("dampen ends everything fast", !h2.active && !o2.active, `${h2.active} ${o2.active}`);

  bank.trigger("glitch", 1, 30, { pad: 4 });
  bank.trigger("kaleido", 1, 30, { pad: 7 });
  bank.choke();
  check("choke silences everything now", bank.activeCount() === 0);

  for (let i = 0; i < 40; i++) bank.trigger("shockwave", 0.5, 40 + i * 0.001, { pad: 1 });
  check("the pool never grows", bank.fx.length === C.MAX_FX && bank.activeCount() === C.MAX_FX);
  check("every pad action is known", C.DEFAULT_PAD_MAP.every((a) => C.PAD_ACTIONS.includes(a)));
  check("pads 1-4 one-shots, 5-8 holdable", C.DEFAULT_PAD_MAP.slice(0, 4).every((a) => !C.EFFECTS[a].hold) &&
        C.DEFAULT_PAD_MAP.slice(4, 8).every((a) => C.EFFECTS[a].hold));
  check("pads 9-12 dampen choke invert zoom (2026-10-24)", C.DEFAULT_PAD_MAP.slice(8).join() === "dampen,choke,invert,zoom");
  check("kill and next left the pads (still pad actions)", !C.DEFAULT_PAD_MAP.includes("kill") && !C.DEFAULT_PAD_MAP.includes("next") &&
        C.PAD_ACTIONS.includes("kill") && C.PAD_ACTIONS.includes("next"));
  check("pad 11 holds (invert), pad 12 is a one-shot (zoom)", C.EFFECTS.invert.hold && !C.EFFECTS.zoom.hold);
  check("every one-shot shows in the first frame (attack 0)", ["shockwave", "laser", "flash", "glitch", "zoom"].every((t) => C.EFFECTS[t].a === 0));
  check("the full-frame effects are marked flash", C.EFFECTS.flash.flash && C.EFFECTS.strobe.flash && C.EFFECTS.invert.flash);
}

// ---------------------------------------------------------------------------------------------- the beat clock --
{
  const clock = new C.BeatClock();
  clock.schedule(1000, { due_ms: 200, bpm: 120, conf: 0.9, n: 1, on_beat: 0.8 });
  clock.schedule(1050, { due_ms: 160, bpm: 120, conf: 0.9, n: 1, on_beat: 0.8 });   // the same beat, refined
  check("a refreshed prediction replaces the old one", clock.qlen === 1 && clock.q[0] === 1210);
  check("not fired early", clock.update(1205, 0.016) === 0);
  check("fired when due", clock.update(1211, 0.016) === 1 && clock.pulse === 1 && clock.count === 1);
  check("phase mid-beat (the beat lands at its scheduled time, not the frame's)", near(clock.phase(1460), 0.5, 1e-9));
  check("next beat from the flywheel", near(clock.nextBeatAt(1300), 1710));
  clock.update(1711, 0.016);
  check("the flywheel keeps time when predictions stop", clock.count === 2);
  clock.update(1711 + 5000, 0.016);
  check("but not forever", clock.count === 2 && !clock.alive(6800));
  clock.schedule(9000, { due_ms: -500, bpm: 120, conf: 0.9, n: 9, on_beat: null });
  check("a stale beat is dropped", clock.qlen === 0);
}

// -------------------------------------------------------------------------------------------- the pedal star --
{
  // Joy to the World's ending: D-flat 5 struck on every beat while the bass walks down under it
  const det = new C.PedalDetector();
  const walk = [49, 48, 46, 44, 42, 41, 39, 37, 36, 37, 39, 41, 42, 44, 46, 48, 49, 46, 44, 42];
  let firstLit = -1;
  for (let i = 0; i < walk.length; i++) {
    const t = i * 0.5;
    det.strike(walk[i], t, -1);
    det.strike(73, t + 0.01, (walk[i] + 1) * 4096);
    det.update(t + 0.02, 0.02);
    if (firstLit < 0 && det.key === 73) firstLit = i + 1;
  }
  check("the repeated note is the pedal", det.key === 73 && det.strikes() === 20, `key ${det.key} strikes ${det.strikes()}`);
  check("it lights at the 16th strike", firstLit === 16, `lit at strike ${firstLit}`);
  check("its tension grows with the strikes", near(det.tension(), 1 - Math.exp(-20 / 24)));
  det.update(9.5 + 1.7, 1.7);
  check("the run ends when the repeats stop", det.key === -1 && det.resolvePulse > 0.1 && det.resolvedCount === 20);
  check("the page's strike signature", C.pedalSignature(-1, "") === -1 && C.pedalSignature(36, "Db") ===
        37 * 4096 + C.hashString("Db") && C.pedalSignature(-1, "Db") === C.hashString("Db"));

  const still = new C.PedalDetector();
  for (let i = 0; i < 8; i++) still.strike(73, i * 0.4, 5 * 4096);    // repeated over an unmoving harmony
  check("a repeat over a still harmony is not a pedal", still.key === -1);
  const slow = new C.PedalDetector();
  for (let i = 0; i < 20; i++) slow.strike(73, i * 2.5, (40 + i) * 4096);
  check("strikes too far apart are not a run", slow.key === -1);
}

// ------------------------------------------------------------------- the pedal star on Daniel's whole Joy take --
// tests/fixtures/vj/joy_take_events.json: the take as the page receives it from `vj --replay-midi` (made by
// tests/fixtures/vj/make_joy_take.py; test_keylab_vj.py checks it is still what the engine produces). It runs through the
// detector the way the page runs it: notes and chord names update what sounds, each note-on strikes with the page's
// signature, and update() runs on a steady 60 Hz frame clock (a clock reset to each event's time loses up to a frame per
// event -- ~6 % of the time on this take, which the first end-to-end sweep did). The ending is the longest run of
// D-flat 4 strikes (no more than 1.6 s apart). keep = the share of it the star spends on D-flat 4; false alarms = the
// seconds the star is lit anywhere else (the ending's own release, up to 1.6 s after its last strike, is not one).
// Daniel's real take is his own playing and the repo is public: it lives in the gitignored state/ folder (or wherever
// KEYLAB_JOY_TAKE points) and this section skips when it is absent.
const JOY_TAKE = process.env.KEYLAB_JOY_TAKE || here("../state/arsenal/keylab/joy_take_events.json");
function joyPedal(opts) {
  const ev = JSON.parse(readFileSync(JOY_TAKE, "utf8")).events;
  const db = ev.filter((r) => r[1] === "n" && r[2] === 61).map((r) => r[0]);
  const runs = [[db[0]]];
  for (let i = 1; i < db.length; i++) { if (db[i] - db[i - 1] > 1.6) runs.push([]); runs[runs.length - 1].push(db[i]); }
  const end = runs.reduce((a, b) => (b.length > a.length ? b : a));
  const T0 = end[0], T1 = end[end.length - 1];
  const det = new C.PedalDetector(opts);
  const held = new Uint8Array(128);
  let chordName = "", tf = null, keep = 0, lit = 0, onEnding = 0;
  const lowestOther = (key) => { for (let k = 0; k < 128; k++) if (k !== key && held[k]) return k; return -1; };
  const frames = (t) => {
    if (tf === null) { tf = t; return; }
    while (tf + 1 / 60 <= t) {
      det.update(tf + 1 / 60, 1 / 60);
      const mid = tf + 1 / 120;
      if (det.key >= 0) {
        lit += 1 / 60;
        if (det.key === 61 && mid >= T0 && mid <= T1 + 1.6) onEnding += 1 / 60;
        if (det.key === 61 && mid >= T0 && mid <= T1) keep += 1 / 60;
      }
      tf += 1 / 60;
    }
  };
  for (const r of ev) {
    frames(r[0]);
    if (r[1] === "c") chordName = r[2];
    else if (r[1] === "n") { held[r[2]] = 1; det.strike(r[2], r[0], C.pedalSignature(lowestOther(r[2]), chordName)); }
    else held[r[2]] = 0;
  }
  frames(tf + 4);
  return { strikes: end.length, start: T0, seconds: T1 - T0, keep: keep / (T1 - T0), falseS: lit - onEnding };
}
if (!existsSync(JOY_TAKE)) {
  console.log("joy pedal: skipped -- Daniel's Joy take is kept out of the public repo (state/arsenal/keylab/, gitignored)");
} else {
  const joy = joyPedal();
  const old = joyPedal({ minCount: 4, minMoves: 1 });
  console.log(`joy pedal: the D-flat ending is ${joy.strikes} strikes over ${joy.seconds.toFixed(1)} s from ${joy.start.toFixed(1)} s; ` +
              `defaults keep ${(100 * joy.keep).toFixed(1)} % with ${joy.falseS.toFixed(1)} s of false alarms ` +
              `(4 strikes / 1 move: ${(100 * old.keep).toFixed(1)} %, ${old.falseS.toFixed(1)} s)`);
  check("the Joy take's ending is the 89-strike D-flat run", joy.strikes === 89 && joy.seconds > 55 && joy.seconds < 57);
  check("the pedal star keeps at least 75 % of the D-flat ending", joy.keep >= 0.75, `${(100 * joy.keep).toFixed(1)} %`);
  check("and lights for at most 8 s anywhere else in the take", joy.falseS <= 8, `${joy.falseS.toFixed(1)} s`);
  check("the old setting lit the star for over a minute elsewhere", old.falseS > 60, `${old.falseS.toFixed(1)} s`);
}

// ------------------------------------------------------------------------------------------ stars and colours --
{
  const p = [0, 0];
  C.starPosition(60, p);
  check("C sits at twelve o'clock", near(p[0], 0, 1e-9) && p[1] > 0);
  C.starPosition(67, p);
  check("G is one step clockwise", p[0] > 0 && p[1] > 0);
  const lo = [0, 0], hi = [0, 0];
  C.starPosition(24, lo); C.starPosition(96, hi);
  check("the register is the radius", Math.hypot(...lo) < Math.hypot(...hi) && Math.hypot(...hi) < 0.45);
  const pcs = C.pitchColours();
  check("twelve pitch colours", pcs.length === 36 && pcs.every((v) => Number.isFinite(v) && v >= 0));
  // the piano's C (#27c5cd as sRGB) and G-flat (#ff4760)
  check("C is the piano's teal", C.rgbToHex(pcs[0], pcs[1], pcs[2]) === "#27c5cd");
  check("G-flat is the piano's red", C.rgbToHex(pcs[18], pcs[19], pcs[20]) === "#ff4760");
  // the constants baked into the presets must equal the port (to the 4 decimals written there)
  for (const file of ["vj-chord-constellations.frag", "vj-led-wall.frag"]) {
    const src = readFileSync(here(`../arsenal/web/presets/${file}`), "utf8");
    const block = src.match(/const vec3 PC_COL\[12\] = vec3\[12\]\(([\s\S]*?)\);/);
    check(`${file} carries PC_COL`, !!block);
    if (!block) continue;
    const nums = [...block[1].matchAll(/-?\d+\.\d+/g)].map((m) => +m[0]);
    check(`${file} PC_COL has 36 numbers`, nums.length === 36);
    check(`${file} PC_COL equals the piano's palette`, nums.every((v, i) => Math.abs(v - pcs[i]) < 6e-5),
          nums.map((v, i) => (v - pcs[i]).toFixed(5)).filter((d) => Math.abs(+d) >= 6e-5).join(" "));
  }
  check("hex encodes linear light", C.rgbToHex(1, 0.5, 0) === "#ffbc00" && C.rgbToHex(-1, 2, 0) === "#00ff00");
  const lab = new Float64Array(3), back = new Float64Array(3);
  C.linearToOklab(0.2, 0.5, 0.9, lab);
  C.oklabToLinear(lab[0], lab[1], lab[2], back);
  check("oklab round trip", near(back[0], 0.2, 1e-6) && near(back[1], 0.5, 1e-6) && near(back[2], 0.9, 1e-6));
}

// -------------------------------------------------------------------------------------------- maps and strip --
{
  check("pad map: junk falls back", C.normalizePadMap(["flash", "nope", 7]).join() ===
        ["flash", ...C.DEFAULT_PAD_MAP.slice(1)].join());
  const m = C.normalizeCtlMap({ cc120: "sat", cc105: null, "bad id!": "hueA", cc1: "nothing" });
  check("ctl map: learned, removed, refused", m.cc120 === "sat" && !("cc105" in m) && !("bad id!" in m) && !("cc1" in m));
  // Lasers v2 (Daniel, 2026-10-25: "3. yes i like that"): fader 1 is the theme fader, fader 2 the hue drift (Hue A and B
  // moved into Custom), the dial the laser gate picker (tests/vj_hookup.test.mjs pins the rest)
  const learned = C.learnBinding(C.DEFAULT_CTL_MAP, "cc7", "theme");
  check("learn moves a target to the new control", learned.cc7 === "theme" && !("cc105" in learned));
  check("faders 1-9 are CC105-113", ["cc105", "cc106", "cc107", "cc108", "cc109", "cc110", "cc111", "cc112", "cc113"]
        .map((c) => C.DEFAULT_CTL_MAP[c]).join() === "theme,hueDrift,sat,bright,trails,strobeRate,accent,xfade,bassReact");
  check("rel nudges, abs sets", near(C.applyCtl(0.5, { kind: "rel", delta: 8 }), 0.625) &&
        near(C.applyCtl(0.5, { kind: "abs", value: 0.2 }), 0.2) && C.applyCtl(0.99, { kind: "rel", delta: 64 }) === 1);
  const s = C.createStrip();
  check("the strip is 16 x 6 RGBA", s.length === 16 * 6 * 4 && C.STRIP.W === 16 && C.STRIP.H === 6);
  C.stripSet(s, 15, 2, 1, 2, 3, 4);
  check("stripSet writes texel (x, y)", s[(2 * 16 + 15) * 4] === 1 && s[(2 * 16 + 15) * 4 + 3] === 4);
  // every VJ preset recognises the strip by exactly that size
  for (const file of ["vj-laser-cathedral.frag", "vj-reactor.frag", "vj-aurora-curtains.frag", "vj-led-wall.frag", "vj-chord-constellations.frag"]) {
    const src = readFileSync(here(`../arsenal/web/presets/${file}`), "utf8");
    check(`${file} recognises the 16x6 strip`, src.includes("textureSize(u_video, 0) == ivec2(16, 6)"));
    check(`${file} line 1`, src.split(/\r?\n/)[0] === "#version 300 es");
  }
}

// ------------------------------------------------------------------------------- the impact pass (2026-10-24) --
{
  // the velocity curve: soft is a nudge, hard is huge
  check("velCurve ends", C.velCurve(0) === 0 && C.velCurve(1) === 1 && C.velCurve(-1) === 0 && C.velCurve(2) === 1);
  check("velCurve is steep", C.velCurve(0.3) < 0.08 && near(C.velCurve(0.6), Math.pow(0.6, 2.2)) && C.velCurve(1) / C.velCurve(0.3) > 10);
  let mono = true;
  for (let v = 0.01; v <= 1; v += 0.01) if (C.velCurve(v) < C.velCurve(v - 0.01)) mono = false;
  check("velCurve is monotone", mono);
  check("hardness: nothing at medium, all at full", C.hardness(0.5) === 0 && C.hardness(0.3) === 0 && C.hardness(1) === 1);

  // the impact layer: punch (fast out, eased back), shake (hard hits only), dip (~40-50 ms), afterglow
  const L = new C.ImpactLayer();
  L.hit("laser", 1, 10, { seed: 0.3, x: 0.2, y: -0.5 });
  let o = L.sample(10);
  check("a hard hit punches at once", near(o.punch, C.IMPACT.laser.punch) && near(o.dip, C.IMPACT.laser.dip) && o.glow > 0.9);
  check("a hard hit shakes, within the cap", Math.hypot(o.shakeX, o.shakeY) > 0 && Math.abs(o.shakeX) <= 0.045 && Math.abs(o.shakeY) <= 0.045);
  check("the strip hears it", o.code === C.EFFECT_CODES.laser && near(o.vel, 1) && near(o.x, 0.2) && near(o.y, -0.5) && o.pulse > 0.99);
  o = L.sample(10.029);
  check("the dip holds 30 ms", near(o.dip, C.IMPACT.laser.dip));
  o = L.sample(10.051);
  check("the dip is gone by 50 ms", o.dip === 0);
  const p1 = L.sample(10.05).punch, p2 = L.sample(10.12).punch, p3 = L.sample(10.25).punch;
  check("the punch eases back", p1 > p2 && p2 > p3 && L.sample(10.29).punch === 0, `${p1} ${p2} ${p3}`);
  check("the shake dies within ~0.35 s", Math.hypot(L.sample(10.4).shakeX, L.sample(10.4).shakeY) === 0);
  check("the pulse decays", L.sample(10.25).pulse < 0.4 && L.sample(10.25).pulse > 0.3);
  const soft = new C.ImpactLayer();
  soft.hit("laser", 0.3, 0, { seed: 0.5 });
  o = soft.sample(0);
  check("a soft hit barely moves the frame: no shake, no dip", o.punch < 0.1 * C.IMPACT.laser.punch && o.shakeX === 0 && o.shakeY === 0 && o.dip === 0);
  check("but the strip still hears it", o.pulse > 0.25);
  const off = new C.ImpactLayer();
  off.hit("glitch", 1, 0, { seed: 0.1, punch: false });
  o = off.sample(0);
  check("the impact switch off: no punch, shake, dip or glow; the hit texel still lit", o.punch === 0 && o.shakeX === 0 && o.dip === 0 &&
        o.glow === 0 && o.pulse > 0.99);
  const two = new C.ImpactLayer();
  const sw = two.hit("shockwave", 1, 0, { seed: 0.2 });
  const swPunch = sw.punch;
  const gl = two.hit("glitch", 1, 0.01, { seed: 0.7 });
  check("two hits: the larger punch wins", near(two.sample(0.01).punch, Math.max(gl.punch, swPunch * (1 - 0.01 / 0.28) ** 2)));
  // the glitch varies its punch, shake and dip by its seed (the same on average); the others do not
  const pg = [];
  for (let k = 0; k < 40; k++) { const g = new C.ImpactLayer().hit("glitch", 1, 0, { seed: (k * 0.618034) % 1 }); pg.push(g.punch); }
  const meanP = pg.reduce((x, y) => x + y, 0) / pg.length;
  check("the glitch's punch varies hit to hit around its profile", Math.max(...pg) / Math.min(...pg) > 2 && Math.abs(meanP / C.IMPACT.glitch.punch - 1) < 0.2,
        `${Math.min(...pg)} .. ${Math.max(...pg)} mean ${meanP}`);
  check("the laser's punch does not", new C.ImpactLayer().hit("laser", 1, 0, { seed: 0.1 }).punch === new C.ImpactLayer().hit("laser", 1, 0, { seed: 0.9 }).punch);
  check("strobe and freeze carry no impact", C.IMPACT.strobe.punch === 0 && C.IMPACT.freeze.punch === 0 && C.IMPACT.strobe.dip === 0);
  check("every effect has an impact profile", C.EFFECT_TYPES.every((t) => C.IMPACT[t]));
  check("zoom depth: 8 % soft .. 30 % hard", near(C.zoomDepth(0), 0.08) && near(C.zoomDepth(1), 0.30) && C.zoomDepth(0.3) < 0.1);

  // the dip's safety limit: never a luminance drop of DIP_SAFE_DELTA or more unless it rides a granted flash
  let worst = 0;
  for (let L2 = 0; L2 <= 1; L2 += 0.01) for (let d = 0; d <= 0.9; d += 0.05) worst = Math.max(worst, C.dipSafeDepth(d, L2) * L2);
  check("a dip alone stays under the flash line (drop < 0.1, and <= the safe delta)", worst <= C.DIP_SAFE_DELTA + 1e-12 && C.DIP_SAFE_DELTA < 0.1, `${worst}`);
  check("a dark scene dips deep", near(C.dipSafeDepth(0.5, 0.04), 0.5));
  check("a bright scene dips shallow", near(C.dipSafeDepth(0.5, 0.45), 0.1));
  check("a dip riding a granted flash keeps its depth", near(C.dipSafeDepth(0.7, 0.8, true), 0.7));

  // the gate still holds with dips: a storm of hard hits (every pad, 20 a second, 5 s) through the page's own rules
  {
    const gate = new C.FlashGate(), bank = new C.EffectBank(), lay = new C.ImpactLayer();
    let dipsAsked = 0, worstDrop = 0;
    for (let k = 0; k < 100; k++) {
      const t = k * 0.05, type = C.DEFAULT_PAD_MAP[k % 12];
      if (!C.EFFECTS[type]) continue;
      let granted = false;
      if (type === "flash" || type === "invert") granted = gate.request(t);
      const f = bank.trigger(type, 1, t, { granted });
      lay.hit(type, 1, t, { seed: f.seed, granted: type === "flash" && granted });
      for (let s = 0; s < 3; s++) {          // three frames per hit, on a scene whose brightness wanders 0.02 .. 0.62
        const o2 = lay.sample(t + s * 0.0167);
        const meanLum = 0.32 + 0.3 * Math.sin(k * 0.7 + s);
        if (o2.dip > 0) dipsAsked++;
        const d = C.dipSafeDepth(o2.dip, meanLum, o2.dipGranted);
        if (!o2.dipGranted) worstDrop = Math.max(worstDrop, d * meanLum);
      }
    }
    check("the storm asked for dips", dipsAsked > 50);
    check("no ungranted dip dropped 0.045 or more", worstDrop <= C.DIP_SAFE_DELTA + 1e-12, `${worstDrop}`);
    check("the gate never granted more than three flashes in a second", gate.maxInAnyWindow() <= 3, `${gate.maxInAnyWindow()}`);
  }

  // the glitch: a mode or a pair per hit, from the hit's seed; deterministic; every mode turns up
  const bank = new C.EffectBank();
  const plans = [];
  for (let k = 0; k < 60; k++) { const f = bank.trigger("glitch", 1, k); plans.push(C.glitchPlan(f.seed, 1)); }
  const prim = new Set(plans.map((p) => p.primary));
  check("all six glitch modes come up as primaries in 60 hits", prim.size === 6 && C.GLITCH_MODES.length === 6, [...prim].join());
  check("consecutive hits never repeat the primary mode", plans.every((p, i) => i === 0 || p.primary !== plans[i - 1].primary));
  check("a hard hit stacks a second, different mode", plans.every((p) => p.secondary >= 0 && p.secondary !== p.primary));
  const pairs = new Set(plans.map((p) => `${p.primary}+${p.secondary}`));
  check("hard hits draw at least 12 different combinations in 60", pairs.size >= 12, `${pairs.size}`);
  check("the same seed gives the same plan", JSON.stringify(C.glitchPlan(0.4321, 0.8)) === JSON.stringify(C.glitchPlan(0.4321, 0.8)));
  check("a soft hit is one mode", C.glitchPlan(0.4321, 0.3).secondary === -1 && C.glitchPlan(0.4321, 0.3).names.length === 1);
  check("velocity sets intensity and size", C.glitchPlan(0.2, 1).amount > C.glitchPlan(0.2, 0.6).amount &&
        C.glitchPlan(0.2, 0.6).amount > C.glitchPlan(0.2, 0.3).amount && C.glitchPlan(0.2, 1).size > C.glitchPlan(0.2, 0.3).size);

  // the band envelopes: fast attack, slower release; a sustained level stops pumping
  const B = new C.BandEnvelopes();
  for (let t = 0; t < 500; t += 16) B.update(t, 0.016);
  B.energy({ bass: 0.8, mid: 0.1, high: 0.1, level: 0.5 }, 500);
  B.update(516, 0.016);
  check("a bass rise lands within one frame (level)", B.level.bass > 0.85 * 0.8, `${B.level.bass}`);
  check("and pumps the kick within one frame", B.env.kick > 0.5, `${B.env.kick}`);
  let t2 = 516;
  for (; t2 < 1600; t2 += 16) { B.energy({ bass: 0.8, mid: 0.1, high: 0.1, level: 0.5 }, t2); B.update(t2, 0.016); }
  check("a sustained bass stops pumping", B.env.kick < 0.15, `${B.env.kick}`);
  const B2 = new C.BandEnvelopes();
  B2.hit("snare", 0.9);
  B2.update(0, 0.016);
  const s0 = B2.env.snare;
  for (let t = 16; t <= 200; t += 16) B2.update(t, 0.016);
  check("a snare hit kicks its envelope at once, then lets go", s0 > 0.8 && B2.env.snare < 0.25, `${s0} -> ${B2.env.snare}`);
  B2.hit("hat", 1);
  B2.update(216, 0.016);
  const h0 = B2.env.hat;
  for (let t = 232; t <= 360; t += 16) B2.update(t, 0.016);
  check("the hat is the shortest", h0 > 0.8 && B2.env.hat < 0.1);
  B2.hit("full", 1);
  B2.update(400, 0.016);
  check("a full hit kicks kick and snare", B2.env.kick > 0.8 && B2.env.snare > 0.8);

  // the beat snap
  const clock = new C.BeatClock();
  clock.schedule(800, { due_ms: 200, bpm: 120, conf: 0.9, n: 0, on_beat: null });
  clock.update(1000, 0.016);
  check("snap: just after a 16th fires now", C.snapDelayMs(1010, clock) === 0);
  check("snap: mid-16th waits for the next", near(C.snapDelayMs(1050, clock), 75));
  check("snap: the next 16th after a beat", near(C.snapDelayMs(1130 + 50, clock), 70));
  check("snap: no live beat, no wait", C.snapDelayMs(9000, clock) === 0 && C.snapDelayMs(100, new C.BeatClock()) === 0);
  check("snap never waits a whole 16th", (() => { for (let t = 1000; t < 2000; t += 3) { const w = C.snapDelayMs(t, clock); if (w < 0 || w > 125 * 0.75 + 1e-9) return false; } return true; })());

  // scenes from the transport and the dial
  const sc = new C.SceneControl();
  const btn = (id, v) => ({ t: "ctl", id, kind: "abs", value: v, delta: 0 });
  const dial = (d) => ({ t: "ctl", id: "cc116", kind: "rel", value: 0.5, delta: d });
  let r = sc.ctl(btn("cc26", 1), "sceneNext", 1000, 14, 3);
  check("fast-forward's press: next scene", r && r.do === "next" && r.index === 4);
  check("its release does nothing", sc.ctl(btn("cc26", 0), "sceneNext", 1080, 14, 4) === null);
  r = sc.ctl(btn("cc26", 1), "sceneNext", 1100, 14, 4);
  check("a press inside 160 ms of the last is a bounce", r === null);
  r = sc.ctl(btn("cc26", 0), "sceneNext", 1150, 14, 4);
  r = sc.ctl(btn("cc26", 1), "sceneNext", 1300, 14, 4);
  check("a later press moves again", r && r.index === 5);
  check("a repeat while held does nothing", sc.ctl(btn("cc26", 1), "sceneNext", 1600, 14, 5) === null);
  sc.ctl(btn("cc26", 0), "sceneNext", 1700, 14, 5);
  r = sc.ctl(btn("cc25", 1), "scenePrev", 1800, 14, 0);
  check("rewind wraps from the first scene to the last", r && r.do === "prev" && r.index === 13);
  sc.ctl(btn("cc25", 0), "scenePrev", 1850, 14, 13);
  r = sc.ctl(dial(3), "sceneDial", 2000, 14, 6);
  check("the dial browses one scene per message (no acceleration)", r && r.do === "browse" && r.index === 7 && sc.browsing());
  check("a second message inside 60 ms is dropped", sc.ctl(dial(5), "sceneDial", 2030, 14, 6) === null && sc.cursor === 7);
  r = sc.ctl(dial(-2), "sceneDial", 2100, 14, 6);
  check("turning back browses back", r && r.index === 6);
  r = sc.ctl(dial(1), "sceneDial", 2200, 14, 6);
  r = sc.ctl(btn("cc117", 1), "sceneGo", 2300, 14, 6);
  check("the dial's click goes to the scene shown", r && r.do === "go" && r.index === 7 && !sc.browsing());
  sc.ctl(btn("cc117", 0), "sceneGo", 2350, 14, 7);
  check("a click with nothing shown does nothing", sc.ctl(btn("cc117", 1), "sceneGo", 2600, 14, 7) === null);
  sc.ctl(btn("cc117", 0), "sceneGo", 2650, 14, 7);
  sc.ctl(dial(1), "sceneDial", 3000, 14, 7);
  check("a browse without a click ends after 4 s", sc.tick(5000) === null && sc.tick(7100)?.do === "browse-end" && !sc.browsing());
  let flood = 0;
  const sc2 = new C.SceneControl();
  for (let t = 0; t < 1000; t += 5) if (sc2.ctl(dial(4), "sceneDial", t, 14, 0)) flood++;
  check("a fast spin cannot flood: at most one step per 60 ms", flood <= 17, `${flood}`);
  let fires = 0;
  const sc3 = new C.SceneControl();
  for (let t = 0; t < 1000; t += 10) if (sc3.ctl(btn("cc26", 1), "sceneNext", t, 14, 0)) fires++;
  check("a held button fires once", fires === 1);

  // the maps: pads 11-12 reclaimed, old stored maps still normalise, the transport and dial on scenes
  check("an old stored map of the old defaults takes the new pads 11-12", C.normalizePadMap(C.PAD_MAP_V1_DEFAULT.slice()).join() === C.DEFAULT_PAD_MAP.join());
  const mine = C.PAD_MAP_V1_DEFAULT.slice(); mine[0] = "glitch"; mine[10] = "flash";
  const kept = C.normalizePadMap(mine);
  check("an old stored map keeps every pad Daniel set", kept[0] === "glitch" && kept[10] === "flash" && kept[11] === "zoom");
  check("a v2 map keeps kill on pad 11 when chosen", C.normalizePadMap({ v: 2, pads: [...C.DEFAULT_PAD_MAP.slice(0, 10), "kill", "next"] }).slice(10).join() === "kill,next");
  check("serialise writes v2", C.serializePadMap(C.DEFAULT_PAD_MAP).v === 2 && C.serializePadMap(C.DEFAULT_PAD_MAP).pads.join() === C.DEFAULT_PAD_MAP.join());
  check("junk in a v2 map falls back", C.normalizePadMap({ v: 2, pads: ["nope"] }).join() === C.DEFAULT_PAD_MAP.join() &&
        C.normalizePadMap("nonsense").join() === C.DEFAULT_PAD_MAP.join());
  // since Lasers v2: Rewind / Fast forward step the sets through the page's transport path (not the map), the dial is
  // the laser gate picker and its click AUTO; the scene actions stay learnable
  check("rewind and fast-forward are the transport's, the dial the laser gate's", !("cc25" in C.DEFAULT_CTL_MAP) &&
        !("cc26" in C.DEFAULT_CTL_MAP) && C.DEFAULT_CTL_MAP.cc116 === "laserGate" && C.DEFAULT_CTL_MAP.cc117 === "laserAuto");
  const n2 = C.normalizeCtlMap({ cc60: "sceneNext", cc26: null });
  check("a scene action can be learned and unbound", n2.cc60 === "sceneNext" && !("cc26" in n2));
  check("learn moves a scene action", (() => { const m = C.learnBinding({ ...C.DEFAULT_CTL_MAP, cc25: "scenePrev" }, "cc61", "scenePrev"); return m.cc61 === "scenePrev" && !("cc25" in m); })());

  // the scene event and the scene route's refusals
  const se = C.parseEvent({ t: "scene", name: "  Laser Cathedral ", index: 0, count: 14, color: "#FF00AA", browsing: true });
  check("scene event", se && se.name === "Laser Cathedral" && se.color === "#ff00aa" && se.browsing && se.count === 14);
  check("scene event refuses a bad name", C.parseEvent({ t: "scene", name: "x".repeat(41) }) === null && C.parseEvent({ t: "scene", name: "" }) === null &&
        C.parseEvent({ t: "scene" }) === null);
  check("sceneName strips control characters", C.sceneName("A\u0007B") === "AB");
  const link = new C.EngineLink();
  link.connected();
  link.event({ t: "hello", leds: true });
  check("a fresh engine may be told the scene", link.mayPostScene());
  check("202 is ok", link.sceneResult(202) === "ok" && link.mayPostScene());
  check("429 is busy, not a refusal", link.sceneResult(429) === "busy" && link.mayPostScene());
  const g0 = link.gen;
  check("an older engine's 404 stops the reports", link.sceneResult(404, g0) === "absent" && !link.mayPostScene() && /older/.test(link.sceneOff));
  link.event({ t: "hello", leds: true });
  check("its next hello lifts it", link.mayPostScene());
  check("a late answer to a post from before that hello is ignored", link.sceneResult(404, g0) === "stale" && link.mayPostScene());
  check("a refusal stops it too", link.sceneResult(409) === "refused" && !link.mayPostScene());
  link.disconnected();
  check("a dropped connection forgets it", link.sceneOff === "" && !link.mayPostScene());

  // the strip's v2 hit texels, and the sets that react to them
  check("strip version 3 (v2's hit texels kept; v3 adds the lasers' head bus)", C.STRIP.VERSION === 3);
  const reacting = ["vj-reactor", "vj-laser-cathedral", "vj-hyperspace", "vj-particle-galaxy", "vj-synthwave-grid", "vj-led-wall"];
  for (const id of reacting) {
    const src = readFileSync(here(`../arsenal/web/presets/${id}.frag`), "utf8");
    check(`${id} reads the shared hit input`, src.includes("vjAt(10, 2)") && /hitLoad\(\);/.test(src) && /gHit/.test(src.split("void main()")[1] || ""));
  }
}

// ------------------------------------------------------------------------------------------------- the demo --
{
  const demo = new C.DemoScript({ bpm: 120, pads: true });
  const got = [];
  for (let t = 0; t <= 64000; t += 16) { demo.tick(t, (e) => got.push(e)); demo.flush(t, (e) => got.push(e)); }
  const parsed = got.map((e) => C.parseEvent(e));
  check("every demo event passes the contract", parsed.every(Boolean), JSON.stringify(got[parsed.findIndex((p) => !p)]));
  check("the demo says hello first", got[0].t === "hello");
  const beats = got.filter((e) => e.t === "beat");
  check("beats are announced ahead", beats.length > 100 && beats.every((b) => b.due_ms > 0 && b.due_ms <= 260));
  check("the demo plays chords, notes, hits and pads", ["chord", "note", "hit", "pad", "energy"].every((t) => got.some((e) => e.t === t)));
  const db5 = got.filter((e) => e.t === "note" && e.key === 73 && e.on);
  check("the demo ends on the D-flat pedal", db5.length >= 20, `${db5.length} strikes`);
  const ons = got.filter((e) => e.t === "note" && e.on).length, offs = got.filter((e) => e.t === "note" && !e.on).length;
  check("every demo note is released", ons - offs <= 6, `${ons} on, ${offs} off`);
}

// ------------------------------------------------------------------------- gate v2: the final-output limiter --
// arsenal/web/vj-gate.js: the rules the GPU limiter (vj-limiter.js) runs on the frame actually shown, and their JS twin.
// The counter is the 2026-10-24 verifier's (pairs of swings of 0.1 relative luminance, counted where they end). Since
// 2026-10-25 (the round-2 verifier) the twin is also judged the way the receipt judges the page: on the picture it would
// show, rebuilt point by point, in quarter-screen rectangles at every offset of a grid finer than its own.
{
  const N = G.NW;
  const lumOf = (L) => () => L;
  // run a picture sequence through the twin; returns per-window shown and wanted series and the limiter
  const drive = (frames, pic, red = () => () => 0, dt = 1 / 60) => {
    const lim = new G.FlashLimiter();
    const shown = Array.from({ length: N }, () => []), want = Array.from({ length: N }, () => []);
    const redShown = Array.from({ length: N }, () => []);
    const trace = [];
    for (let f = 0; f < frames; f++) {
      const g = lim.step(G.cellSums(pic(f), red(f), 32, 32), dt);
      for (let w = 0; w < N; w++) { shown[w].push(lim.shown[w * 2]); want[w].push(lim.want[w * 2]); redShown[w].push(lim.shown[w * 2 + 1] * 320); }
      trace.push({ held: lim.held(), rest: lim.glob[1], beta: g.beta, gainsOne: g.a.every((x) => x === 1) && g.k.every((x) => x === 0), commits: lim.commits,
                   lift: g.k.some((x) => x > 0.02) });
    }
    return { lim, shown, want, redShown, trace };
  };
  // the quarter windows only (the cells are windows too, with thresholds of their own; the standard is about quarters)
  const worst = (series, opts) => Math.max(...series.slice(0, G.NWQ).map((s) => G.flashReport(s, opts).max_flashes_in_1s));
  // The receipt's view: the picture the twin would show, rebuilt on a 64 x 48 point grid (the gains through the hats,
  // the blend toward the previous shown picture), counted in quarter-screen rectangles of several shapes at EVERY point
  // offset (1/64 x 1/48 of the screen, eight times finer than the twin's own grid): the most transitions and strict pairs
  // in any second, over all of them.
  const NX = 64, NY = 48, NP = NX * NY;
  const SHAPES = [[32, 24], [16, 48], [64, 12], [48, 16], [24, 32], [40, 20], [20, 40], [56, 14], [28, 28]];
  const RW = [{ x: 0, y: 0, w: NX, h: NY }];
  for (const [w, h] of SHAPES) for (let y = 0; y + h <= NY; y++) for (let x = 0; x + w <= NX; x++) RW.push({ x, y, w, h });
  const maxIn1s = (at) => { let best = 0; for (let i = 0, j = 0; i < at.length; i++) { while (at[i] - at[j] >= 60) j++; best = Math.max(best, i - j + 1); } return best; };
  const offGrid = (seconds, lumAt) => {
    const lim = new G.FlashLimiter(), frames = Math.round(seconds * 60), h = new Float64Array(6);
    const P = new Float64Array((NX + 1) * (NY + 1)), series = RW.map(() => new Float64Array(frames)), drawnFull = new Float64Array(frames);
    let prev = new Float64Array(NP);
    const L = new Float64Array(NP);
    for (let f = 0; f < frames; f++) {
      const t = f / 60;
      for (let iy = 0; iy < NY; iy++) for (let ix = 0; ix < NX; ix++) L[iy * NX + ix] = lumAt((ix + 0.5) / NX, (iy + 0.5) / NY, t);
      const { a, k, beta } = lim.step(G.cellSums((u, v) => L[Math.min(NY - 1, Math.floor(v * NY)) * NX + Math.min(NX - 1, Math.floor(u * NX))], () => 0, NX, NY), 1 / 60);
      const cur = new Float64Array(NP);
      let dsum = 0;
      for (let iy = 0; iy < NY; iy++) for (let ix = 0; ix < NX; ix++) {
        G.hats((ix + 0.5) / NX, (iy + 0.5) / NY, h);
        let ga = 0, gk = 0;
        for (let j = 0; j < 4; j++) { const ci = G.ctrlIndex(h[0], h[1], j); ga += h[2 + j] * a[ci]; gk += h[2 + j] * k[ci]; }
        const p = iy * NX + ix, Y = L[p];
        let o = Y * ga + (1 - Y) * gk; o += beta * (prev[p] - o);
        cur[p] = o; dsum += Y;
      }
      drawnFull[f] = dsum / NP;
      prev = cur;
      P.fill(0);
      for (let y = 0; y < NY; y++) { let row = 0; for (let x = 0; x < NX; x++) { row += cur[y * NX + x]; P[(y + 1) * (NX + 1) + x + 1] = P[y * (NX + 1) + x + 1] + row; } }
      for (let q = 0; q < RW.length; q++) { const { x, y, w, h: hh } = RW[q]; series[q][f] = (P[(y + hh) * (NX + 1) + x + w] - P[y * (NX + 1) + x + w] - P[(y + hh) * (NX + 1) + x] + P[y * (NX + 1) + x]) / (w * hh); }
    }
    let tr = 0, pairs = 0;
    for (const s of series) { const t = G.transitions(Array.from(s)); tr = Math.max(tr, maxIn1s(t.map((x) => x.at))); pairs = Math.max(pairs, G.maxPairsInWindow(t)); }
    return { transitions: tr, pairs, leaks: lim.leaks, drawnFull: G.flashReport(Array.from(drawnFull)).max_flashes_in_1s };
  };
  const sq = (t, hz) => (Math.floor(t * hz * 2) % 2 ? 1 : 0);

  // the counter itself: a known series
  const sqw = Array.from({ length: 120 }, (_, f) => (Math.floor(f / 6) % 2 ? 0.5 : 0.05));
  const rep = G.flashReport(sqw);
  check("gate v2 counter: a 5 Hz square wave is 5 flashes a second (a window may hold one edge more)", rep.max_flashes_in_1s >= 5 && rep.max_flashes_in_1s <= 5.5, JSON.stringify(rep.max_flashes_in_1s));
  check("gate v2 counter: ... and 5 strict pairs of opposing transitions", rep.max_pairs_in_1s === 5, String(rep.max_pairs_in_1s));
  check("gate v2 counter: swings under 0.1 are not flashes", G.flashReport(sqw.map((v) => 0.3 + (v - 0.3) * 0.15)).transitions === 0);
  check("gate v2 counter: a bright pair (darker end at 0.8 or more) is not a flash", G.flashReport(sqw.map((v) => (v > 0.1 ? 1 : 0.85))).transitions === 0);
  check("gate v2 counter: a staircase (rise, small dip, rise) is two transitions but no strict pair", (() => { const r = G.flashReport([0, 0, 0.12, 0.12, 0.09, 0.09, 0.21, 0.21]); return r.transitions === 2 && r.max_pairs_in_1s === 0; })());

  // the windows: every rectangle of a quarter of the cells or more, then the 64 cells; and the overlap the thresholds
  // are built on: any quarter-screen rectangle, wherever it sits, has a window at least P_MIN inside it
  check("gate v2: 311 quarter windows (every rectangle of 16 cells or more, at every offset), the whole frame first",
        G.NWQ === 311 && G.WINDOWS.slice(0, G.NWQ).every(([x0, y0, x1, y1]) => (x1 - x0 + 1) * (y1 - y0 + 1) >= G.LIMIT.MIN_CELLS) &&
        G.WINDOWS[0].join() === "0,0,7,7" && new Set(G.WINDOWS.map((w) => w.join())).size === G.NW);
  check("gate v2: then every cell, a window of its own", G.NW - G.NWQ === 64 && G.WINDOWS.slice(G.NWQ).every(([x0, y0, x1, y1]) => x0 === x1 && y0 === y1));
  {
    const o = G.worstOverlap(20000, 5);
    check("gate v2: every quarter-screen rectangle has a window at least P_MIN (0.72) inside it", o.worst >= G.LIMIT.P_MIN, o.worst.toFixed(4));
    check("gate v2: the luminance threshold leaves the standard's 0.1 times P_MIN a margin", G.LIMIT.TH[0] < 0.1 * G.LIMIT.P_MIN && G.LIMIT.TH_REST[0] <= 0.1 * G.LIMIT.P_MIN);
  }

  // the hat model is exact: the window value from the cell sums equals the window mean of the picture as the apply pass
  // transforms it (a Y + k (1 - Y), corners interpolated by the hats)
  {
    let s = 3; const R = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
    const a = Float32Array.from({ length: G.NCTRL }, () => 0.3 + 0.7 * R()), k = Float32Array.from({ length: G.NCTRL }, () => 0.4 * R());
    const pic = (u, v) => 0.5 + 0.4 * Math.sin(u * 9.1) * Math.cos(v * 7.3);
    const h = new Float64Array(6);
    const gainAt = (u, v, arr) => { G.hats(u, v, h); let g = 0; for (let j = 0; j < 4; j++) g += h[2 + j] * arr[G.ctrlIndex(h[0], h[1], j)]; return g; };
    const out = (u, v) => { const l = pic(u, v); return gainAt(u, v, a) * l + gainAt(u, v, k) * (1 - l); };
    const cellsIn = G.cellSums(pic, () => 0, 64, 64), cellsOut = G.cellSums(out, () => 0, 64, 64);
    let err = 0;
    for (let w = 0; w < N; w++) err = Math.max(err, Math.abs(G.windowValue(cellsIn, a, k, w, 0) - G.windowValue(cellsOut, new Float32Array(G.NCTRL).fill(1), new Float32Array(G.NCTRL), w, 0)));
    check("gate v2: the window value is an exact linear function of the 81 corner gains and lifts", err < 1e-5, err.toExponential(2));
  }

  // nothing to hold: every gain exactly 1, no lift, no blend (the apply pass copies the frame untouched)
  {
    const d = drive(240, (f) => lumOf(0.2 + 0.05 * Math.sin(f / 20)));
    check("gate v2: a calm picture is never touched", d.trace.every((t) => t.gainsOne && t.beta === 0 && t.held === 0));
  }
  // a 10 Hz full-frame square wave: at most 2.5 flashes a second in every window (N_MAX 5), the first ones untouched
  {
    const d = drive(600, (f) => lumOf(Math.floor(f / 3) % 2 ? 0.5 : 0.05));
    check("gate v2: a 10 Hz full-frame flicker is held to 2.5 flashes a second in every window", worst(d.shown) <= 2.5, String(worst(d.shown)));
    check("gate v2: ... the drawn picture was 10 flashes a second", worst(d.want) >= 10);
    check("gate v2: ... and the first flashes pass untouched", d.shown[0].slice(0, 12).every((v, i) => Math.abs(v - d.want[0][i]) < 1e-6));
    check("gate v2: ... no transition ever starts while held", d.lim.leaks === 0);
    const restAt = d.trace.findIndex((t) => t.rest > 0);
    check("gate v2: ... flashing for 5 s forces a rest", restAt > 280 && restAt < 380, String(restAt));
    const during = d.trace.filter((t) => t.rest > 0);
    check("gate v2: ... and no transition starts during the rest", during.length > 100 && during[during.length - 1].commits === during[0].commits);
  }
  // white flashes at two a second (the gate allows three): never touched
  {
    const d = drive(240, (f) => lumOf(0.05 + 0.5 * Math.exp(-((f % 30) / 60) / 0.15)));
    // (a window may sit in the PARTIAL watch, one transition kept for a fall, without any gain moving)
    check("gate v2: two decaying flashes a second pass untouched", d.trace.every((t) => t.gainsOne && t.beta === 0), String(d.trace.filter((t) => !t.gainsOne).length));
  }
  // a storm of bright hits (a punch of the whole frame 15 times a second): held by taking light away, not by lifting the
  // gaps toward white (a flash's last slot is kept for its fall, so a window runs out of budget dark)
  {
    const d = drive(600, (f) => { let v = 0.15; for (let h = 0; h <= f; h += 4) v += 0.2 * Math.exp(-((f - h) / 60) / 0.05); return lumOf(Math.min(1, v)); }, undefined);
    const lifted = d.trace.filter((t) => t.lift).length;
    check("gate v2: a storm of bright hits is held by darkening, the gaps never lifted toward white", worst(d.shown) <= 2.5 && lifted <= 6, `${worst(d.shown)}/s, ${lifted} lifted frames`);
  }
  // a quarter of the screen flickering: held there, the far corner left alone
  {
    const d = drive(300, (f) => (u, v) => (u < 0.5 && v < 0.5 ? (Math.floor(f / 3) % 2 ? 0.6 : 0.05) : 0.1));
    check("gate v2: a flickering quadrant is held to 2.5 flashes a second", worst(d.shown) <= 2.5, String(worst(d.shown)));
    const g = d.lim.a, k = d.lim.k, far = [70, 71, 79, 80];   // the corners around the bottom-right cell
    // (the whole frame and the wide windows hold too, and take a little of their share there: at most a tenth)
    check("gate v2: ... and the opposite corner keeps at least 90 % of its light, no lift", far.every((i) => g[i] > 0.9 && k[i] < 0.03), far.map((i) => g[i].toFixed(3)).join(" "));
  }
  // red: a saturated red centre switching on and off at 7.5 Hz
  {
    const d = drive(300, () => lumOf(0.1), (f) => (u, v) => (Math.abs(u - 0.5) < 0.25 && Math.abs(v - 0.5) < 0.25 && Math.floor(f / 4) % 2 ? 0.3 : 0));
    const wr = Math.max(...d.redShown.slice(0, G.NWQ).map((s) => G.flashReport(s, { hyst: 2, thr: 20, dark: Infinity }).max_flashes_in_1s));
    check("gate v2: a red flicker over a quarter of the screen is held to 2.5 red flashes a second", wr <= 2.5, String(wr));
  }
  // random storms of bright and dark hits anywhere: every window, also with a second counter's noise of +-0.003
  {
    let worstSeen = 0, worstNoisy = 0, leaks = 0;
    for (let seed = 1; seed <= 4; seed++) {
      let s = seed * 7919; const R = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
      const hits = [];
      for (let f = 0; f < 360; f += 2 + Math.floor(R() * 8)) hits.push([f, 0.1 + 0.4 * R(), R() < 0.3 ? -1 : 1, R(), R()]);
      const d = drive(360, (f) => (u, v) => {
        let val = 0.2;
        for (const [hf, amp, sg, cx, cy] of hits) if (hf <= f && f - hf < 30) { const r = Math.hypot(u - cx, v - cy); val += sg * amp * Math.exp(-((f - hf) / 60) / 0.06) * Math.exp(-r * r * 6); }
        return Math.max(0, Math.min(1, val));
      });
      worstSeen = Math.max(worstSeen, worst(d.shown));
      let n = seed;
      const noise = () => { n = (n * 1664525 + 1013904223) >>> 0; return (n / 4294967296 - 0.5) * 0.006; };
      worstNoisy = Math.max(worstNoisy, worst(d.shown.map((sr) => sr.map((v) => v + noise()))));
      leaks += d.lim.leaks;
    }
    check("gate v2: random storms stay at 2.5 flashes a second in every window", worstSeen <= 2.5, String(worstSeen));
    check("gate v2: ... also counted through +-0.003 of another meter's noise", worstNoisy <= 3, String(worstNoisy));
    check("gate v2: ... without a single transition started while held", leaks === 0, String(leaks));
  }
  // OFF THE GRID (the round-2 verifier's findings): what the receipt would count in rectangles the limiter does not use
  {
    const rect = (x0, x1, y0, y1) => (u, v) => u >= x0 && u <= x1 && v >= y0 && v <= y1;
    const R0 = rect(0.122, 0.628, 0.108, 0.614);
    for (const sw of [0.117, 0.4]) {
      const r = offGrid(3, (u, v, t) => 0.02 + (R0(u, v) ? sw * sq(t, 8) : 0));
      check(`gate v2: a rectangle of 25.6 % off the grid flickering at 8 Hz by ${sw}: at most 3 flashes and 3 strict pairs a second in every quarter-screen rectangle`,
            r.transitions <= 6 && r.pairs <= 3 && r.leaks === 0, JSON.stringify(r));
    }
    const ck = offGrid(3, (u, v, t) => { const p = (Math.floor(u * 3) + Math.floor(v * 3)) % 2; return 0.01 + 0.55 * (p ^ sq(t, 6)); });
    check("gate v2: a 3 x 3 checkerboard in anti-phase at 6 Hz: at most 3 a second in every quarter-screen rectangle", ck.transitions <= 6 && ck.pairs <= 3, JSON.stringify(ck));
    const oc = offGrid(3, (u, v, t) => { const p = (Math.floor(u * 3 + 0.01) + Math.floor(v * 6 + 0.1)) % 2; return 0.01 + 0.6 * (p ^ sq(t, 9)); });
    check("gate v2: a 3 x 6 checkerboard off the grid at 9 Hz (each quarter of the twin's grid level): at most 3 a second", oc.transitions <= 6 && oc.pairs <= 3, JSON.stringify(oc));
    const hv = offGrid(3, (u, v, t) => 0.02 + 0.5 * ((u < 0.43 ? 1 : 0) ^ sq(t, 6)));
    check("gate v2: halves in anti-phase split off the grid (u = 0.43): at most 3 a second", hv.transitions <= 6 && hv.pairs <= 3, JSON.stringify(hv));
  }
  // the GPU twin's shaders: no word GLSL ES 3.00 reserves for future use as a name (2026-10-24: a `bool active` kept the
  // limiter from compiling, and the page fell back to its safe mode), and every constant the twin uses is in them
  {
    const L = await import("../arsenal/web/vj-limiter.js");
    const src = L.limiterShaderSources();
    const RESERVED = ["attribute", "varying", "coherent", "volatile", "restrict", "readonly", "writeonly", "resource", "atomic_uint",
      "noperspective", "patch", "sample", "subroutine", "common", "partition", "active", "asm", "class", "union", "enum", "typedef",
      "template", "this", "goto", "inline", "noinline", "public", "static", "extern", "external", "interface", "long", "short",
      "double", "half", "fixed", "unsigned", "superp", "input", "output", "hvec2", "hvec3", "hvec4", "dvec2", "dvec3", "dvec4",
      "fvec2", "fvec3", "fvec4", "sampler3DRect", "filter", "sizeof", "cast", "namespace", "using"];
    const bad = [];
    for (const [name, s] of Object.entries(src)) {
      const code = s.replace(/\/\/[^\n]*/g, "");
      for (const w of RESERVED) if (new RegExp(`\\b${w}\\b`).test(code)) bad.push(`${name}: ${w}`);
    }
    check("gate v2: the limiter's shaders use no reserved word", bad.length === 0, bad.join(", "));
    check("gate v2: the shaders carry the twin's constants", src.solve.includes(`const float NMAX = ${G.LIMIT.N_MAX}.0;`) &&
          src.state.includes(`const int RING = ${G.LIMIT.RING};`) && src.band.includes(`const int NWQ = ${G.NWQ};`) &&
          src.band.includes(`const vec4 TH4 = vec4(${G.LIMIT.TH.join(", ")})`));
    // every pixel metered: the meter's blocks never exceed 16 x 16 pixels and tile every cell, at any canvas size
    const sizes = [[640, 360], [1280, 720], [1920, 1080], [2560, 1440], [3840, 2160], [1366, 768], [801, 451]];
    const ok = sizes.every(([w, h]) => { const g = L.meterGrid(w, h); return Math.ceil(g.cellW / g.sx) <= 16 && Math.ceil(g.cellH / g.sy) <= 16 && g.width === 8 * g.sx && g.height === 8 * g.sy; });
    check("gate v2: the meter reads every pixel at any size (blocks of at most 16 x 16 tile each cell)", ok, JSON.stringify(sizes.map(([w, h]) => L.meterGrid(w, h))));
  }
}

console.log(`vj_core: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
