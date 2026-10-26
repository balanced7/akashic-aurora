// VJ core: arsenal/web/vj-core.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_core.test.mjs.
//
// Daniel, 2026-10-23: "this makes me want to vj so bad with the pads triggering effects, I think that would be super cool
// ^___^ can you build something to play with? what kind of vfx sets or laser shows can you think of with cool elements for
// me to accent hits and chord changes with, perhaps faders for colors too, go wild" and "there could be a pad to play an
// effect with velocity changing something about the element, then we could have sort of crash close buttons to dampen or
// stop the effect".
//
// This module holds everything the VJ page decides that can be tested without a browser:
//   - the event contract (keylab-vj engine -> page, Server-Sent Events, v1) and its validation   parseEvent
//   - what the page knows of its engine, and whether it may post pad colours                     EngineLink
//   - the engine's key and tension (chordsense), and how its tension meets the page's own        EngineHarmony
//   - the accent effects, their ADSR envelopes and how velocity shapes them                      EFFECTS, EffectBank
//   - the flash gate: at most three full-field flashes in any second (WCAG 2.3.1)                 FlashGate
//   - the predicted-beat clock the engine's 'beat' events feed                                    BeatClock
//   - the pedal detector: one note re-struck while the harmony moves under it                     PedalDetector, pedalSignature
//   - the circle-of-fifths star layout and the house pitch colours                                starPosition, pitchColours
//   - the default pad and control maps, and their validation for localStorage                     DEFAULT_PAD_MAP, ...
//   - the VJ strip: the 16x6 float texture a VJ-aware preset reads through u_video                STRIP
//   - the demo: a scripted show in D-flat that ends on a repeated pedal note                      DemoScript
//   - the impact pass (2026-10-24): the velocity curve, the hit's punch / shake / dip / afterglow  velCurve, ImpactLayer
//     the dip's safe depth against the flash line, the glitch's modes per hit, the band envelopes  dipSafeDepth,
//     (kick / snare / hat), the beat snap, and the scene controls (rewind, fast-forward, dial)     glitchPlan, BandEnvelopes,
//                                                                                                 BeatSnap, SceneControl
//
// Daniel, 2026-10-24: "The VJ thing is so cool!!!!! How do we make the effects feel more impactful and make the vj sets
// even more reponsive! ... perhaps for vj mode the skip forward and backwards buttons can be repurposed to switch presets
// so we can reclaim pad 12, pad 11 also did not seem super useful" and "I love the feel of pad 2 the most so far, pad 1 is
// not bad, pad 4 could have more variety and be more impactful".
//
// Nothing here allocates per frame once constructed (fixed pools, preallocated typed arrays), so the page can call it from
// requestAnimationFrame.

export const VJ_API = "arsenal.vj/v1";

// ------------------------------------------------------------------------------------------------------- the strip --
// The VJ strip is a 16 x 6 RGBA32F texture. The VJ page binds it to u_video and keeps u_has_video at 0, so a VJ-aware
// preset can tell the VJ host from Play (where u_video is a 1x1 black texture or a real video): textureSize == 16 x 6.
// Every preset stays inside Play's uniform list (arsenal/presets.py) and still loads in Play, where it falls back to audio.
export const STRIP = Object.freeze({
  W: 16, H: 6, VERSION: 3,
  // row 0: pads 0..11 = (level, velocity, seconds since press, held); 12 beat = (phase, pulse, bar phase, count mod 64);
  //        13 colour = (hue A turns, hue B turns, saturation, brightness); 14 = (trails, bass reactivity, tension, lushness);
  //        15 chord = (change pulse, root pc or -1, seconds since change, harmonic brightness)
  ROW_PADS: 0,
  // row 1: pitch classes 0..11 = (level, strike pulse, register 0..1, held voices); 12 hit = (pulse, kick, snare, hat);
  //        13 energy = (bass, mid, high, level); 14 pedal = (x, y, strike pulse, tension);
  //        15 = (pedal pc or -1, pedal active, resolve pulse, constellation draw-on progress 0..1)
  ROW_PCS: 1,
  // row 2: 0..3 palette now (linear rgb, 1); 4..7 palette before the last chord change (rgb, 1);
  //        8 = (palette travel progress 0..1, accent gain, metronome amount, kill gain);
  //        9 = (star count, v3: the lasers' pattern id 0-17 (0 = none), their step phase 0..1, solo 0.3..1 (1 = idle beams
  //            at full; 0.3 while a laser gate runs: the scene's own beams dip, as a laser desk's Flash-Solo))
  //        v2 (2026-10-24), the shared HIT input every set may react to in its own way:
  //        10 = (hit pulse 0..1: the latest pad hit through the velocity curve, decaying in ~0.25 s; its velocity 0..1;
  //              its effect code (EFFECT_CODES: 1 shockwave .. 10 zoom); seconds since it, capped at 30)
  //        11 = (kick envelope, snare envelope, hat envelope, the frame's punch: zoom kick 0..~0.3)
  //        12 = (the hit's seed 0..1, its x, its y in the preset's centred space, 0)
  //        v3 (Lasers v2, 2026-10-25), the HEAD BUS for scenes tagged `laser-heads` (spec 1.7; its texels 10-12 moved to
  //        row 3, since v2 had taken them for the hit): 13 = (the lasers' first colour L1, linear rgb; beams per fan);
  //        14 = (their second colour L2, linear rgb; fan spread in radians)
  //        15 = (VERSION, 0, 0, 1)
  ROW_PALETTE: 2,
  // row 3: pad colours 0..11 (linear rgb, 1), the same colours the pads' LEDs get;
  //        v3: 12..14 = the 12 laser heads on the pad grid (head i at texel 12 + i / 4, channel i % 4), each a colour slot
  //        plus a level: slot 0 = L1, 1 = L2, 2 = white, level in [0, 0.999] (vj-lasers.js stripBus, padGrid order:
  //        row 1 = Bank A, row 2 = towers and hero, row 3 = Bank B); 0 everywhere while no laser runs
  ROW_PADCOL: 3,
  // row 4: star slots 0..15 = (x, y, brightness, pc or -1), in the preset's centred space: p = (uv - 0.5) * (aspect, 1);
  //        slots are sorted by angle so consecutive stars make the constellation's polygon
  ROW_STARS: 4,
  // row 5: star slots 0..15 = (velocity, seconds since strike, is root, is pedal)
  ROW_STARS2: 5,
  STAR_SLOTS: 16,
});

export function createStrip() {
  return new Float32Array(STRIP.W * STRIP.H * 4);
}

// Write one texel (x, y) of the strip.
export function stripSet(strip, x, y, r, g, b, a) {
  const i = (y * STRIP.W + x) * 4;
  strip[i] = r; strip[i + 1] = g; strip[i + 2] = b; strip[i + 3] = a;
}

// ---------------------------------------------------------------------------------------------- the event contract --
// The keylab-vj engine (GET http://127.0.0.1:8794/api/events) sends one JSON object per 'data:' line. parseEvent
// normalises one decoded object, clamping every number into its documented range, or returns null for anything it does
// not recognise (an unknown type, a missing field): the page never acts on a malformed event.
const clamp01 = (x) => (x > 1 ? 1 : x < 0 ? 0 : x);
const num = (v, fallback = null) => (typeof v === "number" && Number.isFinite(v) ? v : fallback);
const BANDS = new Set(["kick", "snare", "hat", "full"]);
const BEAT_SRC = new Set(["db", "track", "tap", "fly"]);
const BAR_SRC = new Set(["tap", "drop", "guess"]);
const TAP_MODES = new Set(["resync", "run", "lock", "release", "return"]);
const pc12 = (p) => ((p % 12) + 12) % 12;
// a pitch class that must already be one (a pedal, a bass): 0..11, else -1 = none. Never wrapped: -1 is not B, 99 not Eb
const pcOrNone = (p) => (Number.isInteger(p) && p >= 0 && p < 12 ? p : -1);
// a key as chordsense names it ("Db major", "F# minor"); a roman numeral as it spells one ("IV", "V65/V", "bVII", "vii°")
const KEY_NAME = /^[A-G][#b]? (major|minor)$/;
const ROMAN = /^[#b]?[IViv]{1,4}(?:[°+]|sus[24]|add9|maj|[0-9]{1,2})*(?:\/[#b]?[IViv]{1,4}[°+]?)?$/;
export const keyName = (v) => (typeof v === "string" && KEY_NAME.test(v) ? v : "");
export const romanNumeral = (v) => (typeof v === "string" && v.length <= 16 && ROMAN.test(v) ? v : "");

export function parseEvent(obj) {
  if (!obj || typeof obj !== "object" || typeof obj.t !== "string") return null;
  switch (obj.t) {
    case "hello":
      // leds: true / false from an engine that says; null from one that does not (an older engine: post, and stop on refusal)
      // chords: which chord engine runs ("blend": the templates name the audio chords, chordsense sends the key and the
      // tension; "sense": chordsense names them too; "basic": no key or tension events; "" = an older engine)
      return { t: "hello", v: num(obj.v, 0), src: String(obj.src || ""), beat_engine: String(obj.beat_engine || ""),
               chords: ["blend", "sense", "basic"].includes(obj.chords) ? obj.chords : "",
               pads_mode: ["daw", "bank", "both"].includes(obj.pads_mode) ? obj.pads_mode : "",
               leds: obj.leds === true ? true : obj.leds === false ? false : null,
               leds_reason: typeof obj.leds_reason === "string" ? obj.leds_reason.slice(0, 200) : "",
               // since Lasers v2 (2026-10-25): the controls that tap the engine's beat clock (its --tap list, e.g.
               // "daw:cc23,daw:pad12"; "" = an older engine, or none) and whether the first tap of a run is the ONE. A pad in
               // the list taps the tempo, so the page fires no effect for it (vj-hookup.js tapPadsOf)
               tap: typeof obj.tap === "string" && /^[a-z0-9:,]{0,120}$/i.test(obj.tap) ? obj.tap.toLowerCase() : "",
               tap_one: obj.tap_one === true };
    case "key": {
      // the key the engine hears (chordsense): a name it could not have written, or no confidence number, is malformed
      const name = keyName(obj.name), conf = num(obj.conf);
      if (!name || conf === null) return null;
      return { t: "key", name, conf: clamp01(conf), src: obj.src === "audio" ? "audio" : obj.src === "keys" ? "keys" : "" };
    }
    case "tension": {
      // the harmony's tension 0..1, and the pitch class held as a pedal under it (-1 = none)
      const value = num(obj.value), ped = obj.pedal_pc;
      if (value === null) return null;
      if (ped !== null && ped !== undefined && !Number.isInteger(ped)) return null;
      return { t: "tension", value: clamp01(value), pedal_pc: pcOrNone(ped),
               src: obj.src === "audio" ? "audio" : obj.src === "keys" ? "keys" : "" };
    }
    case "beat": {
      const due = num(obj.due_ms), bpm = num(obj.bpm);
      if (due === null || bpm === null || bpm <= 0) return null;
      // since 2026-10-24 (the engine's beat clock, arsenal/keylab/beatgrid.py): on_beat -1..1 (negative = the beats sit on
      // the off-beat), src (db = the song database's tempo, track = the tracker's, tap = the hand's), bar 1..4 (0 =
      // unknown) and bar_src, ver (bumped on every hard re-anchor: re-anchor, do not slew), the referee's offset_ms and
      // the send time wall_ms. An older engine sends none of them: the defaults below.
      const ob = num(obj.on_beat), bar = num(obj.bar), ver = num(obj.ver), off = num(obj.offset_ms);
      return { t: "beat", due_ms: Math.max(-1000, Math.min(due, 4000)), bpm: Math.max(20, Math.min(bpm, 300)),
               conf: clamp01(num(obj.conf, 0.5)), n: Math.round(num(obj.n, -1)),
               on_beat: ob === null ? null : Math.max(-1, Math.min(ob, 1)),
               src: BEAT_SRC.has(obj.src) ? obj.src : "", bar: Number.isInteger(bar) && bar >= 1 && bar <= 4 ? bar : 0,
               bar_src: BAR_SRC.has(obj.bar_src) ? obj.bar_src : "", ver: ver === null ? -1 : Math.round(ver),
               offset_ms: off === null ? null : Math.max(-1000, Math.min(off, 1000)), wall_ms: num(obj.wall_ms) };
    }
    case "tap": {
      // the KeyLab's Tap button reaching the engine's beat clock: resync (one isolated tap; shift = how far the beat
      // moved, in beats), run (taps 2-3), lock (4 or more: the lights follow the taps at bpm), release (the taps stopped:
      // the hand keeps the beat), return (the beat went back to the tracker)
      if (!TAP_MODES.has(obj.mode)) return null;
      const tb = num(obj.bpm), sh = num(obj.shift);
      return { t: "tap", count: Math.max(0, Math.round(num(obj.count, 0))), mode: obj.mode,
               bpm: tb === null || tb <= 0 ? null : Math.max(20, Math.min(tb, 300)),
               shift: sh === null ? null : Math.max(-0.5, Math.min(sh, 0.5)) };
    }
    case "track": {
      // a new track, and the song database's tempo for it (null: none found); key_db is reserved (none is read yet)
      const db = num(obj.bpm_db);
      return { t: "track", bpm_db: db === null || db <= 0 ? null : Math.max(20, Math.min(db, 300)), key_db: keyName(obj.key_db) };
    }
    case "energy":
      return { t: "energy", bass: clamp01(num(obj.bass, 0)), mid: clamp01(num(obj.mid, 0)), high: clamp01(num(obj.high, 0)),
               level: clamp01(num(obj.level, 0)) };
    case "hit":
      return { t: "hit", strength: clamp01(num(obj.strength, 0.5)), band: BANDS.has(obj.band) ? obj.band : "full" };
    case "chord": {
      const root = num(obj.root);
      const pcs = Array.isArray(obj.pcs) ? obj.pcs.filter((p) => Number.isInteger(p)).map(pc12) : [];
      const conf = num(obj.conf);
      // chordsense's fields (--chords sense): an older engine, or a malformed field, leaves them empty -- never the chord
      return { t: "chord", src: obj.src === "audio" ? "audio" : "keys", name: typeof obj.name === "string" ? obj.name.slice(0, 24) : "",
               root: root === null ? -1 : pc12(Math.round(root)), quality: String(obj.quality || ""),
               pcs: [...new Set(pcs)].slice(0, 12), changed: obj.changed !== false,
               bass: pcOrNone(obj.bass), roman: root === null ? "" : romanNumeral(obj.roman), key: keyName(obj.key),
               conf: conf === null ? null : clamp01(conf) };
    }
    case "note": {
      const key = num(obj.key);
      if (key === null || key < 0 || key > 127) return null;
      return { t: "note", key: Math.round(key), vel: clamp01(num(obj.vel, 0.7)), on: obj.on !== false };
    }
    case "pedal":
      return { t: "pedal", on: obj.on === true };
    case "pad": {
      const pad = num(obj.pad);
      if (pad === null || pad < 1 || pad > 12) return null;
      return { t: "pad", pad: Math.round(pad), vel: clamp01(num(obj.vel, 0.8)), on: obj.on !== false,
               src: obj.src === "bank" ? "bank" : obj.src === "key" ? "key" : obj.src === "demo" ? "demo" : "daw" };
    }
    case "ctl": {
      if (typeof obj.id !== "string" || !/^[A-Za-z0-9_.:-]{1,32}$/.test(obj.id)) return null;
      const kind = obj.kind === "rel" ? "rel" : "abs";
      const ev = { t: "ctl", id: obj.id, kind, value: clamp01(num(obj.value, 0)), delta: Math.round(num(obj.delta, 0)) };
      if (obj.port === "daw" || obj.port === "midi") ev.port = obj.port;   // which KeyLab input, when the engine says
      return ev;
    }
    case "status":
      return { t: "status", msg: String(obj.msg || "").slice(0, 200) };
    case "scene": {
      // the engine's echo of the scene a page reported (POST /api/scene); the KeyLab's screen shows it on line 2
      const name = sceneName(obj.name);
      if (!name) return null;
      const index = num(obj.index), count = num(obj.count);
      return { t: "scene", name, index: index === null ? -1 : Math.round(index), count: count === null ? 0 : Math.round(count),
               color: typeof obj.color === "string" && /^#[0-9a-fA-F]{6}$/.test(obj.color) ? obj.color.toLowerCase() : "",
               browsing: obj.browsing === true };
    }
    default:
      return null;
  }
}

// A scene name as the page sends it and the screen shows it: printable, at most 40 characters, trimmed ("" = invalid).
export function sceneName(v) {
  if (typeof v !== "string") return "";
  const s = v.replace(/[\u0000-\u001f\u007f]/g, "").trim();
  return s.length >= 1 && s.length <= 40 ? s : "";
}

// ------------------------------------------------------------------------------------------------ the engine link --
// What the page knows of the engine it is connected to, and whether it may post pad colours (POST /api/pads). The engine's
// hello says whether its LEDs can light at all (leds false: --no-leds, or no KeyLab DAW output); a refused post (409 =
// turned off, 503 = no device or the engine is stopping; 403 and 423 too) also stops posting -- until the next hello,
// which is the engine saying what changed. Until 2026-10-23 a refusal only paused posting for five seconds, so an engine
// without LEDs was asked again and again for as long as the page ran. A dropped connection forgets the old engine's
// hello and status (the next engine may be another one), so the HUD never shows a dead engine's last word as current.
const REFUSALS = new Set([403, 409, 423, 503]);
// POST /api/scene (2026-10-24): an engine older than the scene route answers 404 (or 405 / 501): the page stops
// reporting its scene to that engine until its next hello, politely, without a retry loop. A refusal (403 / 409 / 423 /
// 503) stops it the same way. 429 is the engine's rate limit: transient, the page waits `retryMs` and sends its newest.
const SCENE_ABSENT = new Set([404, 405, 501]);
export class EngineLink {
  constructor() {
    this.open = false;
    this.hello = null;        // the parsed hello of the engine now connected, or null
    this.status = "";         // its last status message
    this.ledsOff = "";        // why pad colours are not posted now ("" = they may be)
    this.refused = 0;         // posts the engine refused
    this.sceneOff = "";       // why the scene is not reported now ("" = it may be)
    this.sceneRefused = 0;
    this.gen = 0;             // bumps on every hello and every disconnect: a late answer to an older post is ignored
  }
  connected() { this.open = true; }
  disconnected() {
    this.open = false;
    this.hello = null;
    this.status = "";
    this.ledsOff = "";
    this.sceneOff = "";
    this.gen++;
  }
  event(ev) {                 // a parsed event (parseEvent); only hello and status matter here
    if (ev.t === "hello") {
      this.hello = ev;
      this.gen++;
      this.ledsOff = ev.leds === false ? (ev.leds_reason || "the engine has no pad LEDs") : "";
      this.sceneOff = "";
    } else if (ev.t === "status") this.status = ev.msg;
  }
  mayPostLeds() { return this.open && !this.ledsOff; }
  // The HTTP status of a POST /api/pads made under generation `gen`. Returns true when it was a refusal now in force.
  postResult(status, gen = this.gen) {
    if (!REFUSALS.has(status) || gen !== this.gen) return false;
    this.refused++;
    this.ledsOff = `refused (HTTP ${status}); waiting for the engine's next hello`;
    return true;
  }
  mayPostScene() { return this.open && !this.sceneOff; }
  // The HTTP status of a POST /api/scene made under `gen`: "ok", "absent" (an older engine), "refused", "busy" (429),
  // "stale" (an answer from before the latest hello: ignored) or "error".
  sceneResult(status, gen = this.gen) {
    if (gen !== this.gen) return "stale";
    if (status >= 200 && status < 300) return "ok";
    if (status === 429) return "busy";
    if (SCENE_ABSENT.has(status)) {
      this.sceneRefused++;
      this.sceneOff = `this engine has no scene route (HTTP ${status}: older than 2026-10-24); not asked again until its next hello`;
      return "absent";
    }
    if (REFUSALS.has(status)) {
      this.sceneRefused++;
      this.sceneOff = `refused (HTTP ${status}); waiting for the engine's next hello`;
      return "refused";
    }
    return "error";
  }
}

// ------------------------------------------------------------------------------------------- the engine's harmony --
// What the engine's chordsense says (vj --chords sense): the key (key events) and the tension (tension events). The page
// has its own harmonic tension (harmony-feel's, from the notes it sees) and its own pedal star. While the engine sends
// tension, the engine's value REPLACES the page's harmonic estimate -- it is the same quantity, heard with the key, and it
// already carries the engine's pedal pull -- so the strip's tension stays max(harmonic, page pedal x 0.8) with ONE
// harmonic term, never the two of them stacked. An engine that sends no tension (--chords basic, an older engine, no
// engine) leaves the page's own estimate in charge. The engine's value moves in steps (one per chord it decides), so it is
// eased: up in ~0.35 s, down in ~0.8 s, as chordsense eases its own. reset() on every engine hello and disconnect.
export class EngineHarmony {
  constructor({ rise = 0.35, fall = 0.8, pedalWeight = 0.8 } = {}) {
    this.rise = rise; this.fall = fall; this.pedalWeight = pedalWeight;
    this.keyChanges = 0;
    this.reset();
  }
  reset() {
    this.key = ""; this.keyConf = 0; this.keySrc = "";
    this.live = false;           // the engine has sent a tension since its hello
    this.target = 0; this.value = 0; this.pedalPc = -1; this.src = "";
  }
  // a parsed key or tension event (parseEvent). Returns true when the key moved (or first landed): the page accents it.
  event(ev) {
    if (ev.t === "key") {
      const moved = ev.name !== this.key;
      this.key = ev.name; this.keyConf = ev.conf; this.keySrc = ev.src;
      if (moved) this.keyChanges++;
      return moved;
    }
    if (ev.t === "tension") {
      if (!this.live) this.value = ev.value;       // the first value is taken as it is (no ease up from 0)
      this.live = true; this.target = ev.value; this.pedalPc = ev.pedal_pc; this.src = ev.src;
    }
    return false;
  }
  update(dt) {
    if (!this.live) return;
    const tau = this.target > this.value ? this.rise : this.fall;
    this.value += (this.target - this.value) * (1 - Math.exp(-Math.max(0, dt) / tau));
  }
  harmonic(pageTension) { return this.live ? this.value : pageTension; }
  stripTension(pageTension, pedalTension) { return Math.max(this.harmonic(pageTension), pedalTension * this.pedalWeight); }
}

// ------------------------------------------------------------------------------------------------- pitch colours --
// The house pitch palette, ported from arsenal/web/piano.js (colour section, "pitch" mode) and pinned there by
// arsenal/web/glsl/colour/palette.glsl palPitchFifths: the circle of fifths from 200 degrees, each hue near its own most
// colourful OKLCH lightness at 95 % of the sRGB edge, then pulled 65 % toward the twelve colours' geometric-mean
// luminance, so velocity, not the note's name, decides brightness. Linear light. C is the same colour on every surface.
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
export function oklchToLinear(L, C, hDeg) {
  return oklchToLinearRaw(L, C, hDeg).map((v) => Math.max(0, v));
}
export function maxChroma(L, hDeg) {  // the largest chroma still inside sRGB at this lightness and hue
  let lo = 0, hi = 0.4;
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2;
    if (oklchToLinearRaw(L, mid, hDeg).every((v) => v >= -1e-4 && v <= 1.0001)) lo = mid; else hi = mid;
  }
  return lo;
}
function vivid(hDeg, baseL, pull = 0.75) {
  let cuspL = 0.5, cuspC = 0;
  for (let L = 0.3; L <= 0.98; L += 0.01) { const c = maxChroma(L, hDeg); if (c > cuspC) { cuspC = c; cuspL = L; } }
  const L = baseL + (cuspL - baseL) * pull;
  return [L, maxChroma(L, hDeg) * 0.95, hDeg];
}
const lumaOf = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
let pitchCache = null;
// Twelve linear rgb triples, pitch class 0 (C) to 11 (B), as one Float32Array(36). Computed once.
export function pitchColours() {
  if (pitchCache) return pitchCache;
  const raw = [];
  for (let pc = 0; pc < 12; pc++) raw.push(oklchToLinear(...vivid((200 + 30 * ((pc * 7) % 12)) % 360, 0.72)));
  let sum = 0;
  for (const c of raw) sum += Math.log(lumaOf(...c));
  const mean = Math.exp(sum / 12);
  pitchCache = new Float32Array(36);
  raw.forEach((c, pc) => {
    const s = Math.pow(mean / Math.max(lumaOf(...c), 1e-4), 0.65);
    for (let k = 0; k < 3; k++) pitchCache[pc * 3 + k] = c[k] * s;
  });
  return pitchCache;
}

// OKLab <-> linear sRGB, for palette mixing that keeps lightness (a mix through linear rgb goes muddy between hues).
export function linearToOklab(r, g, b, out) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  out[0] = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  out[1] = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  out[2] = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return out;
}
export function oklabToLinear(L, a, b, out) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  out[0] = Math.max(0, 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s);
  out[1] = Math.max(0, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s);
  out[2] = Math.max(0, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s);
  return out;
}

// A fader hue (turns) as a vivid linear colour at lightness L, chroma at `edge` of the sRGB wall. Cached per 1/360 turn.
const hueCache = new Map();
export function hueColour(turns, L = 0.72, edge = 0.9) {
  const deg = Math.round((((turns % 1) + 1) % 1) * 360) % 360;
  const key = deg * 1000 + Math.round(L * 100) * 10 + Math.round(edge * 10);
  let c = hueCache.get(key);
  if (!c) {
    c = oklchToLinear(L, maxChroma(L, deg) * edge, deg);
    hueCache.set(key, c);
  }
  return c;
}

export function rgbToHex(r, g, b) {
  // linear light in, sRGB-encoded #rrggbb out (each channel clamped)
  const enc = (v) => {
    const x = v <= 0 ? 0 : v >= 1 ? 1 : v;
    const s = x <= 0.0031308 ? 12.92 * x : 1.055 * Math.pow(x, 1 / 2.4) - 0.055;
    return Math.round(s * 255).toString(16).padStart(2, "0");
  };
  return `#${enc(r)}${enc(g)}${enc(b)}`;
}

// ---------------------------------------------------------------------------------------------- circle of fifths --
// A note's star: its angle walks the circle of fifths (C at twelve o'clock, then G, D, A ... clockwise), its radius is its
// register (the lowest A near the middle, the top C at the rim). out = [x, y] in the preset's centred space (y up, height 1).
export function fifthsIndex(pc) { return (((pc * 7) % 12) + 12) % 12; }
export function starAngle(pc) { return Math.PI / 2 - fifthsIndex(pc) * (Math.PI / 6); }
export function starPosition(midi, out) {
  const pc = ((midi % 12) + 12) % 12;
  const reg = Math.min(1, Math.max(0, (midi - 21) / 87));
  const r = 0.11 + 0.31 * reg;
  const a = starAngle(pc);
  out[0] = r * Math.cos(a);
  out[1] = r * Math.sin(a);
  return out;
}

// -------------------------------------------------------------------------------------------------------- effects --
// Each accent effect has an ADSR envelope (seconds; sustain is a level) and says how velocity shapes it. A one-shot ignores
// the pad's hold (sustain 0: it plays attack and decay and is gone); a holdable sustains while the pad is held and releases
// on note-off. `flash` marks an effect that can change the whole frame's brightness: it must pass the FlashGate first.
// 2026-10-24 (the impact pass): every one-shot starts at full strength in the frame after the hit (attack 0; the
// shockwave and the laser had 4 and 12 ms ramps), the particles too; the kaleidoscope folds in over 0.12 s instead of
// 0.25 s; Zoom punch is new (pad 12). Every hit also gets the shared impact layer (ImpactLayer: punch, shake, dip,
// afterglow) through the velocity curve (velCurve): a soft tap barely moves the frame, a hard hit throws it.
export const EFFECTS = Object.freeze({
  shockwave: { label: "Shockwave", hold: false, a: 0.0, d: 1.1, s: 0, r: 0.25, colour: "#7fd8ff",
               velocity: "ring speed, width, brightness and how hard the ring refracts the picture behind it" },
  laser:     { label: "Laser burst", hold: false, a: 0.0, d: 0.9, s: 0, r: 0.3, colour: "#ff4fd8",
               velocity: "beam count (3-12), fan spread and brightness" },
  flash:     { label: "White flash", hold: false, a: 0.0, d: 0.22, s: 0, r: 0.12, colour: "#ffffff", flash: true,
               velocity: "flash brightness and length (gated: 3 per second at most)" },
  glitch:    { label: "Glitch", hold: false, a: 0.0, d: 0.5, s: 0, r: 0.2, colour: "#7dff9a",
               velocity: "intensity and size; each hit picks its own mode or pair (split, tear, datamosh, sort, stutter, VHS)" },
  strobe:    { label: "Strobe", hold: true, a: 0.0, d: 0.08, s: 1, r: 0.18, colour: "#f2f2ff", flash: true,
               velocity: "scanner-bar brightness; full-frame pulses go through the flash gate" },
  particles: { label: "Particles", hold: true, a: 0.0, d: 0.35, s: 0.75, r: 0.9, colour: "#ffb347",
               velocity: "particle count and speed" },
  kaleido:   { label: "Kaleidoscope", hold: true, a: 0.12, d: 0.2, s: 1, r: 0.6, colour: "#b78cff",
               velocity: "mirror segments (4-12) and spin" },
  freeze:    { label: "Freeze", hold: true, a: 0.06, d: 0.1, s: 1, r: 0.4, colour: "#9ad7ff",
               velocity: "how much of the frozen frame shows, and its drift" },
  invert:    { label: "Invert", hold: true, a: 0.4, d: 0.0, s: 1, r: 0.5, colour: "#ffe066", flash: true,
               velocity: "how far the colours invert (eased in over 0.4 s, gated)" },
  zoom:      { label: "Zoom punch", hold: false, a: 0.0, d: 0.42, s: 0, r: 0.2, colour: "#5ef0ff",
               velocity: "zoom depth (8-30 % of the frame) and a radial blur while it springs back" },
});
export const EFFECT_TYPES = Object.freeze(Object.keys(EFFECTS));
// The effect codes the strip carries (row 2, texel 10 z): a set can tell which pad effect hit it.
export const EFFECT_CODES = Object.freeze({ shockwave: 1, laser: 2, flash: 3, glitch: 4, strobe: 5, particles: 6, kaleido: 7,
                                            freeze: 8, invert: 9, zoom: 10 });

// The control actions a pad (or Q/W/E/R) can carry instead of an effect.
export const CONTROLS = Object.freeze({
  dampen: { label: "Dampen", colour: "#3d7bff", help: "fast release of every active effect" },
  choke:  { label: "Choke", colour: "#ff9a1f", help: "cut every accent effect now; the set keeps playing" },
  kill:   { label: "Kill", colour: "#ff2a2a", help: "fade everything to black on the next beat; again to bring it back" },
  next:   { label: "Next set", colour: "#e8e8ff", help: "crossfade to the next set" },
  none:   { label: "(nothing)", colour: "#000000", help: "" },
});

export const PAD_ACTIONS = Object.freeze([...EFFECT_TYPES, "dampen", "choke", "kill", "next", "none"]);

// Pads 1-4 one-shots, 5-8 holdable, 9 dampen, 10 choke, 11 invert (holdable), 12 zoom punch (one-shot). The scenes
// moved to the transport (rewind / fast-forward) and the main dial (DEFAULT_CTL_MAP); kill stays on the E key.
export const DEFAULT_PAD_MAP = Object.freeze(["shockwave", "laser", "flash", "glitch", "strobe", "particles", "kaleido",
                                              "freeze", "dampen", "choke", "invert", "zoom"]);
// The map before 2026-10-24 (stored as a bare array): pads 11 and 12 were kill and next set.
export const PAD_MAP_V1_DEFAULT = Object.freeze(["shockwave", "laser", "flash", "glitch", "strobe", "particles", "kaleido",
                                                 "freeze", "dampen", "choke", "kill", "next"]);
export const PAD_MAP_VERSION = 2;

// A stored pad map, as it comes back from localStorage, made safe: an unknown action keeps that pad's default. Two shapes
// are read: { v: 2, pads: [...] } (written since 2026-10-24) and a bare array (written before). In a bare array, a pad
// that still holds the OLD default (pad 11 kill, pad 12 next) takes the new one -- it was the default saved along, not a
// choice -- while every pad Daniel set himself keeps what he set.
export function normalizePadMap(stored) {
  const out = DEFAULT_PAD_MAP.slice();
  let pads = null, legacy = false;
  if (Array.isArray(stored)) { pads = stored; legacy = true; }
  else if (stored && typeof stored === "object" && Array.isArray(stored.pads)) pads = stored.pads;
  if (pads) {
    for (let i = 0; i < 12; i++) {
      if (!PAD_ACTIONS.includes(pads[i])) continue;
      if (legacy && pads[i] === PAD_MAP_V1_DEFAULT[i] && PAD_MAP_V1_DEFAULT[i] !== DEFAULT_PAD_MAP[i]) continue;
      out[i] = pads[i];
    }
  }
  return out;
}
export function serializePadMap(map) { return { v: PAD_MAP_VERSION, pads: normalizePadMap({ pads: map }) }; }

export function actionLabel(action) {
  return EFFECTS[action] ? EFFECTS[action].label : CONTROLS[action] ? CONTROLS[action].label : action;
}

// ------------------------------------------------------------------------------------------------ control targets --
// Faders and knobs. Every target holds 0..1. `kind` says how a control moves it by default: abs (a fader's position) or
// rel (a knob's nudge, delta / 64 per detent). Learn-on-touch rebinds any control id to any target.
// Since Lasers v2 (Daniel, 2026-10-25: "3. yes i like that"): fader 1 is the THEME fader (21 colour themes in colour-wheel
// order, Custom at the top: vj-themes.js) and fader 2 the hue drift (inside a theme +-15 degrees, its centre "as
// designed"; in Custom it turns Hue A and B round the wheel together). Hue A and B moved into Custom: they are the
// Custom theme's own two hues, set from the panel (or any control by learn).
export const TARGETS = Object.freeze([
  { id: "theme", label: "Theme", def: 0.62, group: "colour", help: "fader 1: the colour theme (21 in colour-wheel order, Custom at the top); lands on the next bar" },
  { id: "hueDrift", label: "Hue drift / Custom turn", def: 0.5, group: "colour", help: "fader 2: inside a theme a hue drift of up to 15 degrees (centre = as designed); in Custom it turns Hue A and B round the wheel" },
  { id: "hueA", label: "Hue A (Custom)", def: 0.53, group: "colour", help: "the Custom theme's first hue" },
  { id: "hueB", label: "Hue B (Custom)", def: 0.80, group: "colour", help: "the Custom theme's second hue" },
  { id: "sat", label: "Saturation", def: 0.9, group: "colour", help: "0 is grey, 1 full colour" },
  { id: "bright", label: "Master brightness", def: 0.9, group: "colour", help: "everything, set and accents" },
  { id: "trails", label: "Trails / feedback", def: 0.5, group: "motion", help: "how long light lingers" },
  { id: "strobeRate", label: "Strobe rate", def: 0.45, group: "accents", help: "scanner bars 2-12 Hz; full-frame pulses stay gated" },
  { id: "accent", label: "Accent intensity", def: 0.85, group: "accents", help: "how strong every pad effect is" },
  { id: "xfade", label: "Set crossfade", def: 0.0, group: "sets", help: "manual mix toward the cued set (picks up at 0 after a switch)" },
  { id: "bassReact", label: "Bass reactivity", def: 0.5, group: "music", help: "how hard bass drives glow and size" },
  { id: "chordAmt", label: "Chord colour", def: 0.7, group: "music", help: "how far chords recolour the palette" },
  { id: "metro", label: "Metronome pulse", def: 0.25, group: "music", help: "the beat pulse layer, subtle by default" },
  { id: "k1", label: "Set k1", def: null, group: "set", help: "the active set's first parameter" },
  { id: "k2", label: "Set k2", def: null, group: "set", help: "" },
  { id: "k3", label: "Set k3", def: null, group: "set", help: "" },
  { id: "k4", label: "Set k4", def: null, group: "set", help: "" },
  { id: "k5", label: "Set k5", def: null, group: "set", help: "" },
  { id: "k6", label: "Set k6", def: null, group: "set", help: "" },
  { id: "k7", label: "Set k7", def: null, group: "set", help: "" },
  { id: "k8", label: "Set k8", def: null, group: "set", help: "" },
]);
export const TARGET_IDS = Object.freeze(TARGETS.map((t) => t.id));

// Scene ACTIONS a control can carry instead of a value (2026-10-24): buttons fire on the press (value rising through
// 0.5), never on the release; the dial moves a cursor through the scenes (shown on the page and on the KeyLab's screen)
// and its click jumps to the scene shown. SceneControl decides; learn-on-touch binds them like any target.
export const SCENE_ACTIONS = Object.freeze([
  { id: "scenePrev", label: "Previous scene", help: "a press switches to the previous scene (rewind by default)" },
  { id: "sceneNext", label: "Next scene", help: "a press switches to the next scene (fast-forward by default)" },
  { id: "sceneDial", label: "Scene dial", help: "turning moves through the scenes; the screen shows the one under the dial" },
  { id: "sceneGo", label: "Go to the scene shown", help: "a press jumps to the scene the dial shows (the dial's click)" },
]);
export const SCENE_ACTION_IDS = Object.freeze(SCENE_ACTIONS.map((a) => a.id));

// Laser and theme ACTIONS (Lasers v2, 2026-10-25). The dial picks the laser gate (Daniel: "the dial becomes the laser gate
// picker"): each detent one step through AUTO and the engine's fixed gates (vj-lasers.js GATES), its click back to AUTO.
// Vibrate and the classic burst are toggles (a press); the family tabs pick a colour family (spec 2.3: the buttons under
// the screen, learned on first touch -- their numbers are inferred, so none is bound by default; F1-F8 on the keyboard).
export const LASER_ACTIONS = Object.freeze([
  { id: "laserGate", label: "Laser gate", help: "turning steps the laser gate: AUTO (velocity picks), then each fixed gate (the dial by default)" },
  { id: "laserAuto", label: "Laser gate: AUTO", help: "a press puts the gate back on AUTO (the dial's click by default)" },
  { id: "laserVibrate", label: "Laser vibrate", help: "a press turns Vibrate on or off: the beams ring like plucked strings (V)" },
  { id: "laserClassic", label: "Lasers: classic", help: "a press switches pad 2 between Lasers v2 and the classic burst (C)" },
  { id: "themeLock", label: "Theme lock", help: "a press holds the theme; a change then waits for the next phrase line" },
]);
export const THEME_FAMILIES = Object.freeze(["ritual", "fire", "celestial", "night", "green", "pyro", "worship", "line"]);
export const FAMILY_ACTIONS = Object.freeze(THEME_FAMILIES.map((f, i) => ({
  id: `fam_${f}`, family: f, label: `Family: ${f}`, help: `a press picks the ${f} family's theme for the section; again inside a bar, its next theme (F${i + 1})`,
})));
export const LASER_ACTION_IDS = Object.freeze(LASER_ACTIONS.map((a) => a.id));
export const FAMILY_ACTION_IDS = Object.freeze(FAMILY_ACTIONS.map((a) => a.id));
const CTL_BINDABLE = new Set([...TARGET_IDS, ...SCENE_ACTION_IDS, ...LASER_ACTION_IDS, ...FAMILY_ACTION_IDS]);

// Faders 1-9 are CC105-113 (absolute) and the knobs CC91, 92, 94-97, 102-104 (relative around 64), as Arturia's FL script
// reads them; unconfirmed on the hardware, which is why every binding can be learned. The transport and the dial, from
// the same script's map (research/reviewed/keylab-liberation-2026-10-22/evidence-control-map-2026-10-22.md and
// keylab-full-surface-map-2026-10-23.md, T6 / T7 / D1 / D2; INFERRED, not yet confirmed at the device): DAW mode sends
// Rewind as CC25 and Fast forward as CC26 (127 on press, 0 on release), the main dial's turn as CC116 (relative around
// 64) and its click as CC117. The engine forwards every CC as a ctl event (cc25, cc26, cc116, cc117).
// v2 (Lasers v2, 2026-10-25): fader 1 is the theme, fader 2 the hue drift, the dial the laser gate and its click AUTO.
// Rewind and Fast forward are not in the map: the page's transport path steps the sets with them on the DAW port
// (vj.js onCtl: Daniel's "lets try always we can make it an option"); with ?transport=off they are unbound, free to learn.
export const CTL_MAP_VERSION = 2;
export const DEFAULT_CTL_MAP = Object.freeze({
  cc105: "theme", cc106: "hueDrift", cc107: "sat", cc108: "bright", cc109: "trails", cc110: "strobeRate", cc111: "accent",
  cc112: "xfade", cc113: "bassReact",
  cc91: "k1", cc92: "k2", cc94: "k3", cc95: "k4", cc96: "k5", cc97: "k6", cc102: "k7", cc103: "k8", cc104: "chordAmt",
  cc116: "laserGate", cc117: "laserAuto",
});
// the bindings the defaults used to hold: a map stored before v2 (a bare object, written whole) that still holds one of
// these held the default saved along, not a choice, so it takes the new default (as normalizePadMap does for the pads)
export const CTL_MAP_V1_DEFAULTS = Object.freeze({ cc105: "hueA", cc106: "hueB", cc25: "scenePrev", cc26: "sceneNext",
                                                   cc116: "sceneDial", cc117: "sceneGo" });

// A stored control map made safe. Two shapes: { v: 2, map: {...} } (written since Lasers v2) and a bare object (before).
export function normalizeCtlMap(stored) {
  const out = { ...DEFAULT_CTL_MAP };
  let map = null, legacy = false;
  if (stored && typeof stored === "object" && !Array.isArray(stored)) {
    if (stored.v === CTL_MAP_VERSION && stored.map && typeof stored.map === "object" && !Array.isArray(stored.map)) map = stored.map;
    else { map = stored; legacy = true; }
  }
  if (map) {
    for (const [id, target] of Object.entries(map)) {
      if (!/^[A-Za-z0-9_.:-]{1,32}$/.test(id)) continue;
      if (legacy && target !== null && CTL_MAP_V1_DEFAULTS[id] === target) continue;   // an old default: the new one stands
      if (target === null) delete out[id];
      else if (CTL_BINDABLE.has(target)) out[id] = target;
    }
  }
  return out;
}
// What the page stores: the whole map, tagged with its version (a control the defaults bind that was unbound is null).
export function serializeCtlMap(map) {
  const m = normalizeCtlMap({ v: CTL_MAP_VERSION, map: map || {} });
  const out = { ...m };
  for (const id of Object.keys(DEFAULT_CTL_MAP)) if (!(id in m)) out[id] = null;
  return { v: CTL_MAP_VERSION, map: out };
}

// A press of a button-like control: the value rising through 0.5 (a relative control: a positive nudge). The release, a
// repeat while held (some controllers resend 127) and a second press inside minGapMs (a bounce) are not presses.
export class PressGate {
  constructor({ minGapMs = 160 } = {}) { this.minGapMs = minGapMs; this.down = {}; this.last = {}; this.ignored = 0; }
  press(ev, key, nowMs) {
    const pressed = ev.kind === "rel" ? ev.delta > 0 : ev.value >= 0.5;
    const was = !!this.down[ev.id];
    this.down[ev.id] = ev.kind === "rel" ? false : pressed;
    if (!pressed || was) { this.ignored++; return false; }
    if (nowMs - (this.last[key] ?? -1e9) < this.minGapMs) { this.ignored++; return false; }
    this.last[key] = nowMs;
    return true;
  }
}

// Bind `id` to `target`, dropping any other control bound to that target (one control per target, as learn implies).
export function learnBinding(map, id, target) {
  const out = {};
  for (const [k, v] of Object.entries(map)) if (v !== target && k !== id) out[k] = v;
  out[id] = target;
  return out;
}

// A control's new value: an absolute control sets it, a relative one nudges it by delta / 64 per detent.
export function applyCtl(current, ev) {
  if (ev.kind === "rel") return clamp01(current + ev.delta / 64);
  return clamp01(ev.value);
}

// ------------------------------------------------------------------------------------------------------- ADSR ----
// A release `rScale` times the effect's own, but never shorter than 60 ms (or the effect's own, if that is shorter):
// a dampened effect falls fast without the hard edge of a cut.
export function releaseTime(def, rScale = 1) {
  const r = def.r * rScale;
  return Math.max(1e-3, rScale < 1 ? Math.max(r, Math.min(def.r, 0.06)) : r);
}
// The envelope of one instance at time `now` (seconds): attack to 1, decay to sustain, hold the sustain while held, then
// release to 0. `dScale` stretches the decay (velocity can lengthen a one-shot), `rScale` the release (dampen shortens it).
export function adsr(def, now, t0, tRelease, dScale = 1, rScale = 1) {
  const age = now - t0;
  if (age < 0) return 0;
  const a = def.a, d = def.d * dScale, s = def.s;
  const level = (t) => {
    if (t < a) return a > 0 ? t / a : 1;
    const x = t - a;
    if (x < d) {
      const k = x / d;
      return s + (1 - s) * (1 - k) * (1 - k);   // a fast fall that eases into the sustain
    }
    return s;
  };
  if (tRelease === null || tRelease === undefined || tRelease > now) return level(age);
  const atRelease = level(Math.max(0, tRelease - t0));
  const r = releaseTime(def, rScale);
  const k = (now - tRelease) / r;
  if (k >= 1) return 0;
  return atRelease * (1 - k) * (1 - k);
}

// ------------------------------------------------------------------------------------------------------ FlashGate --
// The photosensitivity line (WCAG 2.3.1 "Three Flashes or Below Threshold"): no more than three full-field flashes in any
// one-second window. A request is granted only when at least minGap seconds have passed since the last granted flash AND
// fewer than maxPerSecond were granted in the trailing second. The shader repeats the guard: it multiplies a flash by
// envFlashSafe(gap) (arsenal/web/glsl/motion/envelope.glsl), 0 for a gap under 1/3 s and 1 from 1/2 s on.
export class FlashGate {
  constructor({ maxPerSecond = 3, minGap = 1 / 3, windowS = 1 } = {}) {
    this.maxPerSecond = maxPerSecond;
    this.minGap = minGap;
    this.windowS = windowS;
    this.times = new Float64Array(64);   // ring of granted onsets (seconds)
    this.head = 0;
    this.size = 0;
    this.last = -1e9;
    this.prevGap = 1e9;                  // the gap before the most recent granted flash
    this.granted = 0;
    this.refused = 0;
  }
  countSince(t) {
    let n = 0;
    for (let i = 0; i < this.size; i++) {
      const v = this.times[(this.head - 1 - i + 64) % 64];
      if (v > t) n++; else break;
    }
    return n;
  }
  request(now) {
    const gap = now - this.last;
    if (gap < this.minGap || this.countSince(now - this.windowS) >= this.maxPerSecond) {
      this.refused++;
      return false;
    }
    this.prevGap = gap;
    this.last = now;
    this.times[this.head] = now;
    this.head = (this.head + 1) % 64;
    this.size = Math.min(64, this.size + 1);
    this.granted++;
    return true;
  }
  // The most flashes granted in any `windowS` window among the recorded onsets (for receipts).
  maxInAnyWindow() {
    const list = [];
    for (let i = 0; i < this.size; i++) list.push(this.times[(this.head - this.size + i + 64) % 64]);
    let best = 0;
    for (let i = 0; i < list.length; i++) {
      let n = 0;
      for (let j = i; j < list.length && list[j] - list[i] < this.windowS; j++) n++;
      best = Math.max(best, n);
    }
    return best;
  }
  log() {
    const list = [];
    for (let i = 0; i < this.size; i++) list.push(this.times[(this.head - this.size + i + 64) % 64]);
    return list;
  }
}

// The shader twin of envFlashSafe, for tests and for the page's own luminance budget.
export function envFlashSafe(sinceLastFlash) {
  const x = Math.min(1, Math.max(0, (sinceLastFlash - 1 / 3) / (0.5 - 1 / 3)));
  return x * x * (3 - 2 * x);
}

// ----------------------------------------------------------------------------------------------------- EffectBank --
// A fixed pool of effect instances. trigger() starts one (stealing the quietest when the pool is full), release() lets the
// holdables tied to a pad go, dampen() hurries every release, choke() silences everything now. update(now) refreshes each
// instance's envelope and frees the finished ones. No allocation after construction.
export const MAX_FX = 16;

export class EffectBank {
  constructor() {
    this.fx = [];
    for (let i = 0; i < MAX_FX; i++) {
      this.fx.push({ active: false, type: "", pad: 0, vel: 0, t0: 0, tr: null, rScale: 1, dScale: 1, env: 0, seed: 0,
                     x: 0, y: 0, granted: true, serial: 0 });
    }
    this.serial = 0;
    this.seedCounter = 0;
  }
  // Start an effect. opts: { pad, x, y, granted } -- `granted` false marks a flash effect the gate refused (it then plays
  // without its full-frame component). Returns the instance.
  trigger(type, vel, now, opts = {}) {
    const def = EFFECTS[type];
    if (!def) return null;
    let slot = null;
    for (const f of this.fx) if (!f.active) { slot = f; break; }
    if (!slot) {
      slot = this.fx[0];
      for (const f of this.fx) if (f.env < slot.env) slot = f;
    }
    slot.active = true;
    slot.type = type;
    slot.pad = opts.pad || 0;
    slot.vel = clamp01(vel);
    slot.t0 = now;
    slot.tr = null;
    slot.rScale = 1;
    // velocity lengthens a one-shot: a soft tap is short, a hard hit rings (x0.6 .. x1.4)
    slot.dScale = def.hold ? 1 : 0.6 + 0.8 * slot.vel;
    slot.env = def.a > 0 ? 0 : 1;
    this.seedCounter = (this.seedCounter + 1) % 997;
    slot.seed = ((this.seedCounter * 0.618033988749895) % 1);
    slot.x = opts.x || 0;
    slot.y = opts.y || 0;
    slot.granted = opts.granted !== false;
    slot.serial = ++this.serial;
    return slot;
  }
  release(pad, now) {
    for (const f of this.fx) if (f.active && f.pad === pad && f.tr === null) f.tr = now;
  }
  dampen(now, scale = 0.15) {
    for (const f of this.fx) {
      if (!f.active) continue;
      // release from wherever the envelope is now, `scale` times the usual release: fast, but never a cut
      if (f.tr === null || f.tr > now) f.tr = now;
      f.rScale = Math.min(f.rScale, scale);
    }
  }
  choke() {
    for (const f of this.fx) { f.active = false; f.env = 0; }
  }
  update(now) {
    for (const f of this.fx) {
      if (!f.active) continue;
      const def = EFFECTS[f.type];
      // a one-shot is fire and forget: the pad's release does not cut it short
      const tr = def.hold ? f.tr : (f.rScale < 1 ? f.tr : null);
      f.env = adsr(def, now, f.t0, tr, f.dScale, f.rScale);
      const age = now - f.t0;
      const oneShotDone = !def.hold && f.tr === null && def.s === 0 && age > def.a + def.d * f.dScale;
      const released = tr !== null && now - tr >= releaseTime(def, f.rScale);
      if (oneShotDone || released || (f.env <= 0 && age > def.a + 0.05 && (tr !== null || def.s === 0))) {
        f.active = false;
        f.env = 0;
      }
    }
  }
  // The largest envelope among active instances of `type` (times velocity when withVel).
  level(type, withVel = false) {
    let m = 0;
    for (const f of this.fx) {
      if (!f.active || f.type !== type) continue;
      const v = withVel ? f.env * (0.35 + 0.65 * f.vel) : f.env;
      if (v > m) m = v;
    }
    return m;
  }
  // The strongest instance of `type`, or null.
  strongest(type) {
    let best = null;
    for (const f of this.fx) if (f.active && f.type === type && (!best || f.env > best.env)) best = f;
    return best;
  }
  activeCount() {
    let n = 0;
    for (const f of this.fx) if (f.active) n++;
    return n;
  }
}

// ------------------------------------------------------------------------------------------------- the impact pass --
// The velocity curve every new impact parameter goes through: v^2.2. soft 0.3 -> 0.071, medium 0.6 -> 0.325, hard 1.0
// -> 1.0: a soft tap is a nudge, a hard hit is fourteen times that. (The laser burst keeps its own linear velocity map --
// beams 3 + 9 v -- because it is the reference that reads well; it gains the impact layer on top.)
export const VEL_GAMMA = 2.2;
export function velCurve(v) { const x = clamp01(v); return x <= 0 ? 0 : Math.pow(x, VEL_GAMMA); }
// How far above "medium" a hit is, 0 below `from`, 1 at full velocity, eased: shake and dip only come with hard hits.
export function hardness(v, from = 0.5) { const x = clamp01((clamp01(v) - from) / (1 - from)); return x * x * (3 - 2 * x); }

// Per effect: the most the impact layer may do at full velocity. punch = the frame's zoom kick (a fraction: 0.03 = the
// frame grows 3 %), shake = its jolt (fraction of the frame height), dip = how far the scene darkens for ~40 ms right at
// the hit (before the dip's safety limit, dipSafeDepth), glow = the afterglow (how much longer the effect's light trails
// for ~0.35 s). Strobe and freeze carry none (a strobe that punched would shake the frame at its own rate). react = how
// strongly the SET answers the hit (the strip's hit pulse, and u_pulse for a plain Play preset): an effect with a look of
// its own (the kaleidoscope's mirrors, the frozen frame, Invert, the strobe's bars, the particles) leads, and the set's
// own flare stays small, so on Reactor every pad no longer opens on the same core flare (2026-10-24 safety pass).
export const IMPACT = Object.freeze({
  shockwave: { punch: 0.030, shake: 0.010, dip: 0.55, glow: 0.8, react: 1.0 },
  laser:     { punch: 0.024, shake: 0.007, dip: 0.50, glow: 1.0, react: 1.0 },
  flash:     { punch: 0.020, shake: 0.000, dip: 0.70, glow: 0.3, react: 0.6 },
  glitch:    { punch: 0.020, shake: 0.016, dip: 0.50, glow: 0.6, vary: true, slip: 0.035, react: 1.0 },
  strobe:    { punch: 0.000, shake: 0.000, dip: 0.00, glow: 0.0, react: 0.3 },
  particles: { punch: 0.018, shake: 0.004, dip: 0.30, glow: 0.8, react: 0.7 },
  kaleido:   { punch: 0.030, shake: 0.000, dip: 0.30, glow: 0.4, react: 0.25 },
  freeze:    { punch: 0.000, shake: 0.000, dip: 0.00, glow: 0.0, react: 0.15 },
  invert:    { punch: 0.020, shake: 0.000, dip: 0.00, glow: 0.0, react: 0.2 },
  zoom:      { punch: 0.000, shake: 0.008, dip: 0.40, glow: 0.7, react: 0.8 },   // its punch is the effect itself (zoomDepth)
});
export const PUNCH_BACK_S = 0.16;      // the punch eases back over this (+0.12 s at full velocity)
export const SHAKE_HZ = 23, SHAKE_TAU_S = 0.06;
export const DIP_HOLD_S = 0.03, DIP_RAMP_S = 0.02;   // the dip: held 30 ms, back in 20 ms (50 ms in all)
export const GLOW_S = 0.35;
// The Zoom punch effect: depth 8 % at the softest, 30 % at full velocity, through the curve; its EffectBank envelope
// (attack 0, a quadratic fall over 0.42 s x velocity's stretch) is the spring back.
export function zoomDepth(vel) { return 0.08 + 0.22 * velCurve(vel); }

// The dip's safety limit. A dip darkens the SCENE (not the accents) by `depth` for ~40 ms; with the scene's mean relative
// luminance L (linear, as displayed: the page measures it every frame, vj.js meter), that is a drop of depth x L, and the
// recovery is the same rise back. A change of 0.1 in relative luminance is where WCAG 2.3.1 starts counting a flash, so a
// dip that rides no flash of its own is held to DIP_SAFE_DELTA (0.045: under half the line, leaving the effect's own light
// room above it): it never asks the FlashGate, because it can never be a flash. A dip that comes with a flash the gate
// GRANTED (the white flash, a strobe pulse) rides that flash's slot at full depth: the pair is one flash, counted once.
export const DIP_SAFE_DELTA = 0.045;
export function dipSafeDepth(depth, meanLum, granted = false) {
  const d = Math.max(0, Math.min(0.9, depth));
  if (granted) return d;
  return Math.min(d, DIP_SAFE_DELTA / Math.max(meanLum, 1e-4));
}

// The impact layer: a small pool of recent hits, each with its punch, shake, dip and afterglow; sample(now) mixes them into
// one frame's values (punch: the largest; shake: the sum, capped; dip: the largest; glow: the largest; pulse: the strip's
// hit pulse). No allocation after construction.
export class ImpactLayer {
  constructor(size = 8) {
    this.hits = [];
    for (let i = 0; i < size; i++) this.hits.push({ on: false, t0: 0, vel: 0, k: 0, punch: 0, back: 0.2, shake: 0, sx: 1, sy: 0,
                                                    ph: 0, dip: 0, granted: false, glow: 0, type: "", code: 0, seed: 0, x: 0, y: 0,
                                                    slip: 0, slx: 1, sly: 0, react: 1 });
    this.out = { punch: 0, shakeX: 0, shakeY: 0, dip: 0, dipGranted: false, glow: 0, pulse: 0, vel: 0, code: 0, since: 30,
                 seed: 0, x: 0, y: 0 };
    this.last = null;
    this.count = 0;
  }
  // type: an EFFECTS key; opts: { seed 0..1, granted (the hit's flash was granted), x, y (centred space), punch (false:
  // the panel's impact switch is off -- no punch, shake, dip or afterglow; the strip's hit texel still hears the hit) }
  hit(type, vel, now, opts = {}) {
    const prof = IMPACT[type];
    if (!prof) return null;
    let slot = this.hits.find((h) => !h.on);
    if (!slot) { slot = this.hits[0]; for (const h of this.hits) if (h.t0 < slot.t0) slot = h; }
    const k = velCurve(vel), hard = hardness(vel);
    const on = opts.punch === false ? 0 : 1;
    const seed = clamp01(opts.seed ?? 0.5);
    slot.on = true; slot.t0 = now; slot.vel = clamp01(vel); slot.k = k; slot.type = type; slot.code = EFFECT_CODES[type] || 0;
    slot.react = prof.react ?? 1;
    // an effect whose profile says `vary` (the glitch) throws a different punch, shake and dip every hit, from its seed
    // (the same on average): no two glitches land alike
    const v1 = prof.vary ? 0.3 + 1.4 * hash01(seed * 5.1 + 0.3) : 1;
    const v2 = prof.vary ? 0.4 + 1.2 * hash01(seed * 9.7 + 1.1) : 1;
    const v3 = prof.vary ? 0.3 + 1.4 * hash01(seed * 2.3 + 2.9) : 1;
    slot.punch = prof.punch * k * on * v1;
    slot.back = PUNCH_BACK_S + 0.12 * k;
    slot.shake = prof.shake * hard * on * v2;
    const a = seed * 6.283185307179586;
    slot.sx = Math.cos(a); slot.sy = Math.sin(a); slot.ph = seed * 3.1;
    slot.dip = Math.min(0.9, prof.dip * hardness(vel, 0.55) * on * v3);
    // a slip (the glitch): the whole frame jumps sideways in the hit's own direction and eases back with the punch
    slot.slip = (prof.slip || 0) * k * on;
    const sa = hash01(seed * 13.7 + 0.1) * 6.283185307179586;
    slot.slx = Math.cos(sa); slot.sly = Math.sin(sa);
    slot.granted = opts.granted === true;
    slot.glow = prof.glow * k * on;
    slot.seed = seed; slot.x = opts.x || 0; slot.y = opts.y || 0;
    this.last = slot;
    this.count++;
    return slot;
  }
  clear() { for (const h of this.hits) h.on = false; this.last = null; }
  sample(now) {
    const o = this.out;
    o.punch = 0; o.shakeX = 0; o.shakeY = 0; o.dip = 0; o.dipGranted = false; o.glow = 0;
    for (const h of this.hits) {
      if (!h.on) continue;
      const t = now - h.t0;
      if (t < 0) continue;
      const done = t > Math.max(h.back, 6 * SHAKE_TAU_S, DIP_HOLD_S + DIP_RAMP_S, GLOW_S);
      if (done) { h.on = false; continue; }
      if (t < h.back) {                                  // fast out, eased back
        const e = 1 - t / h.back;
        o.punch = Math.max(o.punch, h.punch * e * e);
        if (h.slip > 0) { o.shakeX += h.slip * h.slx * e * e; o.shakeY += h.slip * h.sly * e * e; }
      }
      if (h.shake > 0) {
        const amp = h.shake * Math.exp(-t / SHAKE_TAU_S);
        const w = 6.283185307179586 * SHAKE_HZ * t + h.ph;
        o.shakeX += amp * (h.sx * Math.cos(w) - h.sy * 0.5 * Math.sin(1.37 * w));
        o.shakeY += amp * (h.sy * Math.cos(w) + h.sx * 0.5 * Math.sin(1.37 * w));
      }
      const dipE = t < DIP_HOLD_S ? 1 : Math.max(0, 1 - (t - DIP_HOLD_S) / DIP_RAMP_S);
      if (h.dip * dipE > o.dip) { o.dip = h.dip * dipE; o.dipGranted = h.granted; }
      if (t < GLOW_S) o.glow = Math.max(o.glow, h.glow * (1 - t / GLOW_S));
    }
    const cap = 0.045;
    o.shakeX = Math.max(-cap, Math.min(cap, o.shakeX));
    o.shakeY = Math.max(-cap, Math.min(cap, o.shakeY));
    const L = this.last;
    if (L) {
      const since = Math.max(0, now - L.t0);
      o.pulse = (0.25 + 0.75 * L.k) * Math.exp(-since / 0.25) * L.react;
      o.vel = L.vel; o.code = L.code; o.since = Math.min(30, since); o.seed = L.seed; o.x = L.x; o.y = L.y;
    } else { o.pulse = 0; o.vel = 0; o.code = 0; o.since = 30; o.seed = 0; o.x = 0; o.y = 0; }
    return o;
  }
}

// ----------------------------------------------------------------------------------------------- the glitch's modes --
// Pad 4, rebuilt (2026-10-24: "pad 4 could have more variety and be more impactful"). Six modes, drawn by the composite
// shader (vj.js COMPOSITE_FS): 0 RGB split with slice offsets, 1 block displacement with scanline tearing, 2 a datamosh
// smear through the previous frame (the composite's own feedback), 3 pixel-sort streaks, 4 a stutter that repeats slices
// of the frame held at the hit, 5 a VHS wobble. Each hit picks a primary mode from its seed (the EffectBank's golden-ratio
// seeds: consecutive hits always land on different modes) and, from medium velocity up, a second mode on top; velocity
// (through the curve) sets the intensity and the size of slices and blocks. Whatever the modes, the first ~120 ms are a
// strike shaped by the seed too (its block grid, the shove's direction, the channels' split angle, some blocks with their
// channels turned round), so every glitch lands hard in the next frame; the datamosh and the stutter take over after it.
// Its impact profile varies by seed as well (IMPACT.glitch vary: punch, shake and dip; and a slip of the whole frame in the
// hit's own direction). Deterministic: the same seed and velocity give the same plan, so the receipts can count the
// variety (8 hard hits on Reactor, 2026-10-24: pairwise difference 0.011 -> 0.065, over the mean 0.84 -> 0.89).
export const GLITCH_MODES = Object.freeze(["split", "tear", "datamosh", "sort", "stutter", "vhs"]);
function hash01(x) { const s = Math.sin(x * 127.1 + 311.7) * 43758.5453123; return s - Math.floor(s); }
export function glitchPlan(seed, vel) {
  const sd = clamp01(seed);
  const primary = Math.min(5, Math.floor(sd * 6));
  let secondary = -1;
  if (vel >= 0.5) secondary = (primary + 1 + Math.floor(hash01(sd * 7.7 + 1.3) * 5)) % 6;   // never the primary
  const k = velCurve(vel);
  return { primary, secondary, amount: 0.35 + 0.65 * k, size: 0.25 + 0.75 * clamp01(vel), seed: hash01(sd * 3.3 + 0.7),
           names: secondary >= 0 ? [GLITCH_MODES[primary], GLITCH_MODES[secondary]] : [GLITCH_MODES[primary]] };
}

// ---------------------------------------------------------------------------------------------- the band envelopes --
// Per band, a fast-attack / slower-release envelope instead of plain smoothing: the level follows a rise within one
// frame (attack tau ~5 ms) and falls on its own time (kick 0.16 s, snare 0.12 s, hat 0.05 s). Each band has two parts:
// its LEVEL (the engine's energy band, 100 events a second since 2026-10-24: bass, mid, high) and its ONSET (the rise of
// that band above its own recent floor, and every hit event of that band as an impulse), which drives the punchy uses:
// kick -> the frame's scale pump, snare -> a colour and contrast kick, hat -> sparkle.
export const BAND_ENV = Object.freeze({
  kick:  { band: "bass", attack: 0.005, release: 0.16, floorTau: 0.25 },
  snare: { band: "mid",  attack: 0.005, release: 0.12, floorTau: 0.2 },
  hat:   { band: "high", attack: 0.004, release: 0.05, floorTau: 0.12 },
});
export function arStep(cur, target, dt, attack, release) {
  const tau = target > cur ? attack : release;
  return cur + (target - cur) * (1 - Math.exp(-Math.max(0, dt) / Math.max(tau, 1e-4)));
}
export class BandEnvelopes {
  constructor() {
    this.level = { bass: 0, mid: 0, high: 0, all: 0 };
    this.target = { bass: 0, mid: 0, high: 0, all: 0 };
    this.floor = { kick: 0, snare: 0, hat: 0 };
    this.impulse = { kick: 0, snare: 0, hat: 0 };
    this.env = { kick: 0, snare: 0, hat: 0 };
    this.last = -1e9;
  }
  energy(ev, nowMs) {        // a parsed energy event
    this.target.bass = ev.bass; this.target.mid = ev.mid; this.target.high = ev.high; this.target.all = ev.level;
    this.last = nowMs;
  }
  hit(band, strength) {      // a parsed hit's band and strength
    const s = clamp01(strength);
    if (band === "kick" || band === "full") this.impulse.kick = Math.max(this.impulse.kick, s);
    if (band === "snare" || band === "full") this.impulse.snare = Math.max(this.impulse.snare, s);
    if (band === "hat") this.impulse.hat = Math.max(this.impulse.hat, s);
  }
  update(nowMs, dt) {
    if (nowMs - this.last > 1500) { this.target.bass = this.target.mid = this.target.high = this.target.all = 0; }
    // levels: fast up, a 0.12 s fall (the engine's own release is 0.10 s; this only smooths the steps between events)
    for (const k of ["bass", "mid", "high", "all"]) this.level[k] = arStep(this.level[k], this.target[k], dt, 0.006, 0.12);
    for (const [name, def] of Object.entries(BAND_ENV)) {
      const lv = this.level[def.band];
      // the band's recent floor rises slowly and drops at once: a sustained level stops pumping, a new rise pumps
      this.floor[name] = lv < this.floor[name] ? lv : arStep(this.floor[name], lv, dt, def.floorTau, def.floorTau);
      const onset = Math.min(1, Math.max(0, lv - this.floor[name]) * 2.2);
      const target = Math.max(onset, this.impulse[name]);
      this.impulse[name] = 0;
      this.env[name] = arStep(this.env[name], target, dt, def.attack, def.release);
    }
    return this.env;
  }
}

// --------------------------------------------------------------------------------------------------- the beat snap --
// Off by default (the panel's checkbox and the B key): a pad hit waits for the next 16th of the engine's beat while one is
// live. A hit up to `lateShare` of a 16th after a grid line counts as on it (it fires now: being a hair late is still on
// the beat); otherwise it waits for the next line. Without a live beat it never waits. Returns the ms to wait (0 = now).
export function snapDelayMs(nowMs, beatClock, { division = 4, lateShare = 0.25 } = {}) {
  if (!beatClock || !beatClock.alive(nowMs)) return 0;
  const p = beatClock.period();
  if (!(p > 0)) return 0;
  const grid = p / division;
  const since = nowMs - beatClock.lastBeat;
  if (since < 0) return Math.max(0, -since);        // the beat itself is just ahead
  const into = since % grid;
  if (into <= lateShare * grid) return 0;
  return grid - into;
}

// --------------------------------------------------------------------------------------------------- scene controls --
// The transport and the dial, turned into scene moves. Buttons (scenePrev, sceneNext, sceneGo) act on the PRESS: a value
// rising through 0.5; the release (value 0) and any repeat while held (some controllers resend 127) do nothing, and a
// second press inside `minGapMs` is a bounce. The dial (sceneDial) moves a cursor one scene per message whatever the
// message's size (no acceleration), at most one step per `stepMs` (a fast spin cannot run away); the cursor is what the
// page and the KeyLab's screen show while browsing, and sceneGo jumps to it. Without a click the browse ends after
// `browseMs` and the cursor returns to the live scene. Pure: the page passes its scene count and the live index.
export class SceneControl {
  constructor({ minGapMs = 160, stepMs = 60, browseMs = 4000 } = {}) {
    this.minGapMs = minGapMs; this.stepMs = stepMs; this.browseMs = browseMs;
    this.down = {};             // control id -> held (value >= 0.5)
    this.lastFire = {};         // action -> ms
    this.cursor = -1;           // -1 = not browsing
    this.lastStep = -1e9;
    this.lastTouch = -1e9;
    this.lastAbs = {};          // an absolute dial's last value
    this.ignored = 0;           // releases, repeats, bounces and over-fast dial messages dropped
  }
  browsing() { return this.cursor >= 0; }
  // ev: a parsed ctl event; action: one of SCENE_ACTION_IDS; n: how many scenes; live: the live scene's index.
  // -> null, or { do: "prev" | "next" | "browse" | "go" | "browse-end", index }
  ctl(ev, action, nowMs, n, live) {
    if (!(n > 0)) return null;
    if (action === "sceneDial") {
      let dir = 0;
      if (ev.kind === "rel") dir = Math.sign(ev.delta);
      else {
        const prev = this.lastAbs[ev.id];
        this.lastAbs[ev.id] = ev.value;
        if (prev !== undefined) dir = Math.sign(ev.value - prev);
      }
      if (!dir) return null;
      if (nowMs - this.lastStep < this.stepMs) { this.ignored++; this.lastTouch = nowMs; return null; }
      this.lastStep = nowMs; this.lastTouch = nowMs;
      const from = this.cursor >= 0 ? this.cursor : live;
      this.cursor = (((from + dir) % n) + n) % n;
      return { do: "browse", index: this.cursor };
    }
    const pressed = ev.kind === "rel" ? ev.delta > 0 : ev.value >= 0.5;
    const was = !!this.down[ev.id];
    this.down[ev.id] = ev.kind === "rel" ? false : pressed;
    if (!pressed || was) { this.ignored++; return null; }     // a release, or a repeat while held
    if (nowMs - (this.lastFire[action] ?? -1e9) < this.minGapMs) { this.ignored++; return null; }
    this.lastFire[action] = nowMs;
    if (action === "sceneGo") {
      if (this.cursor < 0) return null;                        // nothing shown under the dial: a click does nothing
      const index = this.cursor;
      this.cursor = -1;
      return { do: "go", index };
    }
    this.cursor = -1;                                          // a transport press ends any browse
    if (action === "scenePrev") return { do: "prev", index: (((live - 1) % n) + n) % n };
    if (action === "sceneNext") return { do: "next", index: (live + 1) % n };
    return null;
  }
  // Call every frame: ends a browse that waited too long for its click.
  tick(nowMs) {
    if (this.cursor >= 0 && nowMs - this.lastTouch > this.browseMs) { this.cursor = -1; return { do: "browse-end", index: -1 }; }
    return null;
  }
}

// ------------------------------------------------------------------------------------------------------ BeatClock --
// The engine predicts beats 150-300 ms ahead ('beat' events with due_ms). schedule() turns each into an absolute time on
// performance.now(); update() fires the ones that are due. A refreshed prediction for the same beat number replaces the
// old one. When predictions stop, the clock flywheels on its last tempo for up to `flywheelMs`, with confidence fading,
// so a dropout of a second or two never stops the show.
//
// THE PAGE GRID (Lasers v2 slice S2, spec 3.2): a continuous beat position, posAt(t) = anchorBeat + (t - anchorMs) /
// period, that every sub-beat gate is computed from (vj-lasers.js reads it through the clock adapter, vj-hookup.js). When
// beat n fires at t_n:
//   - the engine's grid version (`ver`, bumped on every hard re-anchor of its beat clock) changed: hard re-anchor at that
//     beat (anchor = t_n, the nearest whole beat), never mid-pulse;
//   - otherwise the error e = n - pos(t_n), n the nearest whole beat: |e| <= 1/4 beat SLEWS (the next beat is stretched
//     by up to 10 % so the position meets the grid there; it never jumps, never runs backward); |e| > 1/4 re-anchors.
// A beat of a new ver flushes the queued beats of the old one. The engine's bar (1-4, --tap-one) puts the ONE on a
// position that is a multiple of 4 (a forward step of whole beats at most), so bar lines downstream are the engine's.
// The 4 s flywheel is unchanged: its beats go through the same grid.
export const GRID_SLEW_MAX = 0.25;      // beats: a beat this close to the grid slews; further off re-anchors
export const GRID_STRETCH_MAX = 0.10;   // the most one beat may be stretched or squeezed while slewing
export class BeatClock {
  constructor({ flywheelMs = 4000, decayS = 0.18 } = {}) {
    this.q = new Float64Array(8);        // due times (ms)
    this.qn = new Int32Array(8);         // beat numbers
    this.qv = new Int32Array(8);         // the engine's grid version of each (-1: an engine that sends none)
    this.qb = new Int8Array(8);          // its bar (1-4, 0 unknown)
    this.qlen = 0;
    this.bpm = 0;
    this.conf = 0;
    this.lastBeat = -1e9;                // ms
    this.count = 0;                      // beats fired
    this.n = -1;
    this.pulse = 0;
    this.lastRecv = -1e9;
    this.flywheelMs = flywheelMs;
    this.decayS = decayS;
    this.onBeat = null;                  // the engine's on-beat referee score, or null
    this.fired = 0;                      // beats fired by the last update()
    // the page grid (S2)
    this.ver = -1;                       // the grid version of the beats fired
    this.qver = -1;                      // the newest version announced (queued beats of older ones are flushed)
    this.src = "";                       // where the engine's beat comes from (db, track, tap, fly)
    this.bar = 0;                        // the engine's bar of the beat fired last (1-4, 0 unknown)
    this.barBeat = 0;                    // the grid's whole beat that bar was
    this.anchorMs = null;                // the grid: pos(t) = anchorBeat + rate * (t - anchorMs) / anchorP within one beat
    this.anchorBeat = 0;
    this.anchorP = 0;
    this.rate = 1;                       // the slew's stretch of the beat after the anchor (1 = none)
    this.beat = 0;                       // the whole beat the grid gave the beat fired last
    this.reanchors = 0;                  // hard re-anchors (a new ver, or a beat more than 1/4 off)
    this.slews = 0;                      // beats met by slewing
    this.flushed = 0;                    // queued beats of an old ver dropped
    this.lastError = 0;                  // the last fired beat's error against the grid (beats)
  }
  schedule(nowMs, ev) {
    this.lastRecv = nowMs;
    this.bpm = ev.bpm;
    this.conf = ev.conf;
    if (ev.on_beat !== null && ev.on_beat !== undefined) this.onBeat = ev.on_beat;
    if (typeof ev.src === "string" && ev.src) this.src = ev.src;
    const ver = Number.isInteger(ev.ver) ? ev.ver : -1;
    if (ver >= 0 && ver !== this.qver) {
      // a new grid version: the beats still queued from the old one are not the engine's beats any more
      for (let i = 0; i < this.qlen;) {
        if (this.qv[i] >= 0 && this.qv[i] !== ver) { this.dropAt(i); this.flushed++; } else i++;
      }
      this.qver = ver;
    }
    const t = nowMs + ev.due_ms;
    if (t < nowMs - 60) return;          // stale
    const bar = Number.isInteger(ev.bar) && ev.bar >= 1 && ev.bar <= 4 ? ev.bar : 0;
    for (let i = 0; i < this.qlen; i++) {
      if (ev.n >= 0 && this.qn[i] === ev.n && this.qv[i] === ver) { this.q[i] = t; this.qb[i] = bar; return; }
    }
    // a beat this close to one already queued (or just fired) is the same beat said twice
    for (let i = 0; i < this.qlen; i++) if (Math.abs(this.q[i] - t) < 60) return;
    if (Math.abs(t - this.lastBeat) < 60) return;
    if (this.qlen < 8) {
      this.q[this.qlen] = t;
      this.qn[this.qlen] = ev.n;
      this.qv[this.qlen] = ver;
      this.qb[this.qlen] = bar;
      this.qlen++;
    }
  }
  dropAt(i) {
    const j = this.qlen - 1;
    this.q[i] = this.q[j]; this.qn[i] = this.qn[j]; this.qv[i] = this.qv[j]; this.qb[i] = this.qb[j];
    this.qlen--;
  }
  period() { return this.bpm > 0 ? 60000 / this.bpm : 0; }
  update(nowMs, dt) {
    this.fired = 0;
    this.pulse *= Math.exp(-dt / this.decayS);
    for (;;) {                           // due beats in time order (a late frame may find two)
      let k = -1;
      for (let i = 0; i < this.qlen; i++) if (this.q[i] <= nowMs && (k < 0 || this.q[i] < this.q[k])) k = i;
      if (k < 0) break;
      const t = this.q[k], n = this.qn[k], v = this.qv[k], b = this.qb[k];
      this.dropAt(k);
      this.fire(t, n, v, b);
    }
    // flywheel: no prediction queued, the tempo known, the engine heard from recently
    const p = this.period();
    if (this.qlen === 0 && p > 0 && nowMs - this.lastRecv < this.flywheelMs && nowMs - this.lastBeat >= p) {
      this.fire(this.lastBeat + p * Math.max(1, Math.floor((nowMs - this.lastBeat) / p)), -1, this.ver, 0);
      this.conf *= 0.85;
    }
    return this.fired;
  }
  fire(t, n, ver = -1, bar = 0) {
    this.grid(t, ver, bar);
    this.lastBeat = t;
    this.count++;
    if (n >= 0) this.n = n;
    this.pulse = 1;
    this.fired++;
  }
  // the page grid at a fired beat (see above)
  grid(t, ver, bar) {
    const p = this.period();
    if (!(p > 0)) return;
    const newVer = ver >= 0 && this.ver >= 0 && ver !== this.ver;
    let whole;
    if (this.anchorMs === null) {
      whole = 0;
      this.anchorMs = t; this.anchorBeat = 0; this.rate = 1;
    } else {
      const pred = this.posAt(t);
      whole = Math.round(pred);
      const e = whole - pred;
      this.lastError = e;
      if (newVer || Math.abs(e) > GRID_SLEW_MAX) {
        this.anchorBeat = whole; this.anchorMs = t; this.rate = 1;
        this.reanchors++;
      } else {
        this.anchorBeat = pred; this.anchorMs = t;
        this.rate = Math.min(1 + GRID_STRETCH_MAX, Math.max(1 - GRID_STRETCH_MAX, 1 + e));
        if (Math.abs(e) > 1e-9) this.slews++;
      }
    }
    this.anchorP = p;
    if (ver >= 0) this.ver = ver;
    if (bar >= 1) {
      // the ONE on a multiple of 4: step the grid forward by whole beats when the engine's bar says otherwise
      const want = bar - 1, have = ((whole % 4) + 4) % 4;
      const step = (want - have + 4) % 4;
      if (step) { this.anchorBeat += step; whole += step; }
      this.bar = bar; this.barBeat = whole;
    }
    this.beat = whole;
  }
  // The continuous beat position at time t (ms), or null before the first beat. Within the beat after the anchor it runs
  // at the slew's rate, then at one beat a period: continuous and never backward.
  posAt(t) {
    if (this.anchorMs === null || !(this.anchorP > 0)) return null;
    const x = (t - this.anchorMs) / this.anchorP;
    if (x <= 0) return this.anchorBeat + x;
    return x <= 1 ? this.anchorBeat + this.rate * x : this.anchorBeat + this.rate + (x - 1);
  }
  // the beat of the bar (1-4) at time t, from the engine's bar; 0 while the bar is unknown
  barAt(t) {
    if (!this.bar) return 0;
    const pos = this.posAt(t);
    if (pos === null) return 0;
    return ((((Math.floor(pos + 1e-6) - this.barBeat) + this.bar - 1) % 4) + 4) % 4 + 1;
  }
  // 0..1 through the current beat (0 just after a beat); 0 when no tempo is known.
  phase(nowMs) {
    const p = this.period();
    if (!(p > 0) || nowMs - this.lastBeat > 4 * p) return 0;
    const x = (nowMs - this.lastBeat) / p;
    return x >= 1 ? 0.999 : Math.max(0, x);
  }
  // When the next beat lands (ms), or null.
  nextBeatAt(nowMs) {
    let best = Infinity;
    for (let i = 0; i < this.qlen; i++) if (this.q[i] >= nowMs && this.q[i] < best) best = this.q[i];
    if (best < Infinity) return best;
    const p = this.period();
    if (p > 0 && nowMs - this.lastRecv < this.flywheelMs) {
      return this.lastBeat + p * Math.max(1, Math.ceil((nowMs - this.lastBeat) / p));
    }
    return null;
  }
  alive(nowMs) { return this.period() > 0 && nowMs - this.lastRecv < this.flywheelMs; }
}

// --------------------------------------------------------------------------------------------------- PedalDetector --
// A pedal point: one note struck again and again while the harmony moves under it. Daniel's Joy to the World ends with
// D-flat 4 struck 89 times over a walking bass (56 s at the replay's 100 BPM): the repeats build tension that only the end
// releases. Each key keeps its own run (strikes no more than maxGap apart); a strike counts a harmony move when what
// sounds under it (pedalSignature: the lowest other note and the chord name) differs from its previous strike. A run with
// at least minCount strikes and minMoves moves is a pedal; the longest such run is THE pedal. tension =
// 1 - exp(-count / tensionScale). When the pedal run ends, end() reports it once (the page blooms).
//
// minCount 16 and minMoves 3, measured on the whole Joy take as the page receives it (tests/fixtures/vj/
// joy_take_events.json, replayed in tests/vj_core.test.mjs on a steady 60 Hz frame clock): the old 4 / 1 lit the star for
// 109 s away from the D-flat ending (any repeated melody or inner note: F4, A-flat 4, C4); 12 / 3 for 12.4 s; 16 / 3 for
// 7.0 s (the repeated F4 - G-flat 4 - A-flat 4 figure over a moving bass at 114-132 s, a pedal-like passage in its own
// right), while keeping 83.8 % of the ending lit (88.6 % before: it now lights at the 16th strike, ~9 s in). The rule
// from the end-to-end review: keep at least 75 % of the ending, fewest false alarms. Going further (20 strikes: 4.3 s,
// 79.7 %) would only be fitting the one F4 run of this take, and a pedal shorter than 20 strikes would never show.
export function pedalSignature(lowestOther, chordName) {
  return lowestOther < 0 && !chordName ? -1 : (lowestOther + 1) * 4096 + hashString(chordName || "");
}
export class PedalDetector {
  constructor({ maxGap = 1.6, minCount = 16, minMoves = 3, tensionScale = 24 } = {}) {
    this.maxGap = maxGap;
    this.minCount = minCount;
    this.minMoves = minMoves;
    this.tensionScale = tensionScale;
    this.count = new Int32Array(128);
    this.moves = new Int32Array(128);
    this.last = new Float64Array(128).fill(-1e9);
    this.sig = new Int32Array(128).fill(-1);
    this.key = -1;               // the current pedal key, or -1
    this.pulse = 0;              // strike pulse of the pedal (decays)
    this.resolvePulse = 0;       // set to 1 when a pedal run ends
    this.resolvedKey = -1;
    this.resolvedCount = 0;
  }
  // `under` is a whole-number signature of the harmony under the strike (the page passes the lowest other sounding note
  // times 4096 plus a hash of the chord name), or -1 when nothing else sounds.
  strike(key, t, under) {
    if (key < 0 || key > 127) return;
    if (t - this.last[key] > this.maxGap) {
      this.count[key] = 0;
      this.moves[key] = 0;
      this.sig[key] = under;
    }
    this.count[key]++;
    if (under !== this.sig[key] && this.count[key] > 1) this.moves[key]++;
    this.sig[key] = under;
    this.last[key] = t;
    this.pick(t);
    if (key === this.key) this.pulse = 1;
  }
  pick(t) {
    let best = -1, bestCount = 0;
    for (let k = 0; k < 128; k++) {
      if (t - this.last[k] > this.maxGap) continue;
      if (this.count[k] >= this.minCount && this.moves[k] >= this.minMoves && this.count[k] > bestCount) {
        best = k; bestCount = this.count[k];
      }
    }
    if (best !== this.key && this.key >= 0 && best < 0) this.end();
    this.key = best;
  }
  end() {
    this.resolvePulse = 1;
    this.resolvedKey = this.key;
    this.resolvedCount = this.count[this.key];
  }
  update(t, dt) {
    this.pulse *= Math.exp(-dt / 0.22);
    this.resolvePulse *= Math.exp(-dt / 0.9);
    if (this.key >= 0 && t - this.last[this.key] > this.maxGap) {
      this.end();
      this.key = -1;
    }
  }
  tension() {
    return this.key >= 0 ? 1 - Math.exp(-this.count[this.key] / this.tensionScale) : 0;
  }
  strikes() { return this.key >= 0 ? this.count[this.key] : 0; }
}

// A small stable string hash (for the harmony signature).
export function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) % 4096;
}

// ------------------------------------------------------------------------------------------------------- the demo --
// ?demo=1 plays a scripted show through the same event path the engine uses: predicted beats, energy, kicks and snares,
// a chord progression in D-flat with the chord tones as key presses, and -- the last eight bars -- a walking bass under a
// D-flat struck on every beat, so the pedal star has something to do. With pads on, it also taps and holds pads.
const DB = 1;  // pitch class of D-flat
const PROGRESSION = [
  // [name, root pc, chord tones as midi notes, bass midi] -- one bar each
  ["Db", 1, [61, 65, 68], 37], ["Gb/Db", 6, [61, 66, 70], 37], ["Ab7", 8, [60, 63, 66, 68], 44], ["Db", 1, [61, 65, 68], 37],
  ["Bbm7", 10, [61, 65, 68, 70], 46], ["Ebm7", 3, [61, 63, 66, 70], 39], ["Ab7sus4", 8, [61, 63, 66, 68], 44], ["Ab7", 8, [60, 63, 66, 68], 44],
];
// the pedal ending: one bass note per beat, D-flat 5 struck on every beat above it
const WALK = [49, 48, 46, 44, 42, 41, 39, 37, 36, 37, 39, 41, 42, 44, 46, 48, 49, 46, 44, 42, 41, 39, 37, 44,
              49, 48, 46, 44, 42, 41, 44, 37];
const WALK_NAMES = { 49: "Db", 48: "C7", 46: "Bbm", 44: "Ab", 42: "Gb", 41: "Fm", 39: "Ebm7", 37: "Db", 36: "C7" };

export class DemoScript {
  constructor({ bpm = 112, pads = true } = {}) {
    this.bpm = bpm;
    this.pads = pads;
    this.beatMs = 60000 / bpm;
    this.t0 = null;
    this.nextBeat = 0;          // index of the next beat to announce
    this.nextEnergyAt = 0;
    this.held = [];             // notes to release: [key, offAt]
    this.padOff = [];           // pads to release: [pad, offAt]
    this.pending = [];          // stamped events waiting for their time: [at, obj]
    this.bars = PROGRESSION.length + WALK.length / 4;   // the loop, in bars
  }
  // Emit every event due by nowMs through emit(obj). Beats are announced `lead` ms ahead, the way the engine does.
  tick(nowMs, emit) {
    if (this.t0 === null) {
      this.t0 = nowMs + 400;
      emit({ t: "hello", v: 1, src: "demo", beat_engine: "demo", pads_mode: "both" });
      emit({ t: "status", msg: "demo: a scripted show in D-flat; the last 8 bars are a pedal point" });
    }
    const lead = 220;
    while (this.t0 + this.nextBeat * this.beatMs - lead <= nowMs) {
      const i = this.nextBeat++;
      const due = this.t0 + i * this.beatMs;
      emit({ t: "beat", due_ms: due - nowMs, bpm: this.bpm, conf: 0.9, n: i, on_beat: 0.92 });
      this.beatEvents(i, due, nowMs, emit);
    }
    // energy at ~100 Hz (as the engine sends it since 2026-10-24): a kick envelope on every beat, the mids breathing with
    // the bar, a hat shimmer on the off-beats
    if (nowMs >= this.nextEnergyAt) {
      this.nextEnergyAt = nowMs + 10;
      const b = (nowMs - this.t0) / this.beatMs;
      const inBeat = b - Math.floor(b);
      const kick = Math.exp(-inBeat * 5.5);
      const bar = (b / 4) % 1;
      const hat = Math.exp(-(((b + 0.5) % 1)) * 9);
      emit({ t: "energy", bass: 0.25 + 0.6 * kick, mid: 0.35 + 0.2 * Math.sin(bar * Math.PI * 2) ** 2,
             high: 0.2 + 0.45 * hat, level: 0.35 + 0.35 * kick });
    }
    for (let i = this.held.length - 1; i >= 0; i--) {
      if (this.held[i][1] <= nowMs) {
        emit({ t: "note", key: this.held[i][0], vel: 0, on: false });
        this.held.splice(i, 1);
      }
    }
    for (let i = this.padOff.length - 1; i >= 0; i--) {
      if (this.padOff[i][1] <= nowMs) {
        emit({ t: "pad", pad: this.padOff[i][0], vel: 0, on: false, src: "demo" });
        this.padOff.splice(i, 1);
      }
    }
  }
  // Note and chord events are emitted when their beat is announced, stamped for that beat: the page holds them back until
  // due (a key press cannot be predicted, so a real engine sends them as they happen; the demo only fakes the timing).
  beatEvents(i, due, nowMs, emit) {
    const later = (ms, obj) => this.pending.push([due + ms, obj]);
    const loopBeats = this.bars * 4;
    const beat = i % loopBeats;
    const bar = Math.floor(beat / 4);
    const inBar = beat % 4;
    later(0, { t: "hit", strength: inBar === 0 ? 0.95 : 0.7, band: "kick" });
    if (inBar === 1 || inBar === 3) later(0, { t: "hit", strength: 0.6, band: "snare" });
    const hold = this.beatMs * 0.92;
    if (bar < PROGRESSION.length) {
      if (inBar === 0) {
        const [name, root, tones, bass] = PROGRESSION[bar];
        later(0, { t: "chord", src: "keys", name, root, quality: "", pcs: [...new Set(tones.map((k) => k % 12))], changed: true });
        for (const k of [bass, ...tones]) later(2, { t: "note", key: k, vel: 0.62, on: true, hold: this.beatMs * 3.85 });
      }
    } else {
      const w = beat - PROGRESSION.length * 4;
      const bass = WALK[w % WALK.length];
      const name = WALK_NAMES[bass] || "Db";
      later(0, { t: "chord", src: "keys", name, root: bass % 12, quality: "", pcs: [bass % 12, DB], changed: true });
      later(1, { t: "note", key: bass, vel: 0.7, on: true, hold });
      later(3, { t: "note", key: 73, vel: 0.55 + 0.35 * (w / WALK.length), on: true, hold: this.beatMs * 0.5 });  // Db5
    }
    if (this.pads) {
      // a one-shot on the bar's downbeat every other bar, a held pad across beats 2-3 every fourth bar
      if (inBar === 0 && bar % 2 === 0) later(0, { t: "pad", pad: 1 + ((bar / 2) % 4), vel: 0.55 + 0.4 * ((bar * 7) % 5) / 4, on: true, src: "demo", hold: 120 });
      if (inBar === 1 && bar % 4 === 1) later(0, { t: "pad", pad: 5 + (Math.floor(bar / 4) % 4), vel: 0.8, on: true, src: "demo", hold: this.beatMs * 2 });
      // the loop's last beat: a zoom punch (pad 12), then the fast-forward button (cc26: next scene) half a beat later
      if (beat === loopBeats - 1) {
        later(0, { t: "pad", pad: 12, vel: 0.9, on: true, src: "demo", hold: 80 });
        later(this.beatMs * 0.5, { t: "ctl", id: "cc26", kind: "abs", value: 1, delta: 0 });
        later(this.beatMs * 0.5 + 90, { t: "ctl", id: "cc26", kind: "abs", value: 0, delta: 0 });
      }
    }
  }
  // Release the stamped events that are due. Returns nothing; calls emit for each.
  flush(nowMs, emit) {
    for (let i = 0; i < this.pending.length;) {
      const [at, obj] = this.pending[i];
      if (at > nowMs) { i++; continue; }
      this.pending.splice(i, 1);
      const { hold, ...ev } = obj;
      emit(ev);
      if (ev.t === "note" && ev.on && hold) this.held.push([ev.key, nowMs + hold]);
      if (ev.t === "pad" && ev.on && hold) this.padOff.push([ev.pad, nowMs + hold]);
    }
  }
}
