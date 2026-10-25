// Node tests for the VJ rig's pure logic (arsenal/web/vj-core.js). Zero dependencies:
//   node tests/vj_core.test.mjs
// Sections: the event contract; the engine link (when the page may post pad colours); the flash gate (three flashes in any second, and the shader twin of envFlashSafe); ADSR and
// the effect bank (velocity, hold and release, dampen, choke, the fixed pool); the beat clock (scheduling, refreshed
// predictions, the flywheel); the pedal detector (Joy to the World's repeated D-flat over a walking bass, and Daniel's
// whole real take through it: tests/fixtures/vj/joy_take_events.json); the star layout;
// the pad and control maps; the strip layout every VJ preset reads; the demo script; and the pitch colours baked into the
// presets (they must equal the piano's palette as ported here).
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as C from "../arsenal/web/vj-core.js";

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
  check("pads 9-12 dampen choke kill next", C.DEFAULT_PAD_MAP.slice(8).join() === "dampen,choke,kill,next");
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
  const learned = C.learnBinding(C.DEFAULT_CTL_MAP, "cc7", "hueA");
  check("learn moves a target to the new control", learned.cc7 === "hueA" && !("cc105" in learned));
  check("faders 1-9 are CC105-113", ["cc105", "cc106", "cc107", "cc108", "cc109", "cc110", "cc111", "cc112", "cc113"]
        .map((c) => C.DEFAULT_CTL_MAP[c]).join() === "hueA,hueB,sat,bright,trails,strobeRate,accent,xfade,bassReact");
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

console.log(`vj_core: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
