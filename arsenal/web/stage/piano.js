// arsenal/web/stage/piano.js -- THE PIANO PLAYS THE LIGHTING: the VJ engine's KeyLab events mapped onto the rig, as pure
// functions (event -> look delta). No DOM, no WebGL, no engine, no clock of its own: every function here is a value in, a
// value out, so the mapping is pinned by tests/stage_piano.test.mjs and the page only has to APPLY what it says.
//
// Daniel, 2026-11-02: "Any ideas how we can marry what we have built with the piano visualizer and our new lightshow rig?
// ... then lets build it, we have 20m, so go crazy." His pick: the piano plays the lighting.
//
// THE EVENTS ARE THE ENGINE'S, ALREADY (arsenal/keylab/vj.py, the SSE contract; vj-core.js parseEvent):
//   note  {"t":"note","key":0..127,"vel":0..1,"on":bool}       every key on the KeyLab 88 mk3 MIDI input
//   pedal {"t":"pedal","on":bool}                              the sustain pedal (CC 64)
//   chord {"t":"chord","src":"keys"|"audio","name":"Dbmaj7","root":0..11,"quality":"maj7","pcs":[...],"conf":..}
//          src "keys" is what HE PLAYS (the engine's Voicing + theory.analyze after a 30 ms settle, so a rolled chord is
//          one event); src "audio" is the engine's ear on the speakers, and this layer never reads it (it would double
//          the reading of the same chord, and the room would follow the PA instead of the hands).
//
// THE FOUR MAPPINGS (his list, in his order):
//   1. velocity -> the intensity of that note's light hit. A note is a KICK (the rig's own vocabulary: kick.js's
//      levelOfVel / intensityOf, "kick-white" by default), so the hit is a light the stage already knows how to make, the
//      flash governor already owns, and the final-frame limiter already judges. intensityOf mirrors kick.js
//      KICK_DEFAULTS.level exactly (from_velocity [0,1], floor 0.5, gamma 0.5): a soft note still lights, at half.
//   2. sustain pedal -> haze and bloom HELD while it is down. The F5 haze fader stays the CEILING: the pedal can never
//      push the air past the operator's own value, so pedalHaze(fader, on) = fader when down and fader x haze_floor when
//      up. That is what makes the pedal audible as an effect (the room clears between legato passages, thickens inside
//      them) without ever taking the fader's authority away. Bloom adds the measured spare headroom only (bloom_add).
//   3. register (the lowest and highest HELD notes) -> camera distance, through the existing close/medium/far presets
//      (distance.js). Low on the keyboard pulls the camera out into the room, the middle holds medium, the top comes in
//      close; the hand-off reads the MIDI note of the held register's centre, so one note is its own register. Nothing
//      held -> "auto", the director's own size, i.e. the rig lets go.
//   4. chord quality -> palette FAMILY, through the existing palette library (../palettes.json, families violet / pink /
//      blue / green / warm / neutral). NEVER a colour in this file: qualityClass names a family, familyLadder is an
//      order of families, and pickFamily only ever returns a family the library actually has. A class with no palette
//      loaded returns null and the stage does not move -- fail-soft, no invented colour.
//
// THE TOGGLE: default OFF, and OFF means this module changes nothing. ?piano=1 turns it on at load and the Y key toggles
// it live (stage.js); ?pianobloom= and ?pianohaze= are the A/B overrides of the two pedal numbers. Every existing show is
// byte-for-byte the same until someone asks for the piano.
//
// THE FLASH RULES ARE NOT OURS. This layer adds no light path of its own: a note's hit is a kick (the governor's subject:
// stage.js already feeds it the limiter's remaining budget, and with the consent toggle OFF the governor sees a full
// budget and the frame reaches the canvas as drawn), and the pedal only moves the air and the bloom knob, both of which
// the final-frame limiter judges as before. A hit the governor refuses is COUNTED (state.refused), never forced.
export const PIANO_API = "arsenal.stage-piano/v1";

// ?piano=1: "1" and the usual truths. Anything else -- absent, 0, off, garbage -- is OFF.
export const PIANO_ON = Object.freeze(["1", "on", "true", "yes", "y"]);
export const PIANO_KEY = "KeyY";                 // the live toggle (the keyboard map in stage.js)
export const PIANO_CFG = Object.freeze({
  // 1. the hit (mirrors kick.js KICK_DEFAULTS.level: from_velocity [0,1], floor 0.5, gamma 0.5)
  hit_kind: "kick-white",
  level_from_velocity: Object.freeze([0, 1]),
  intensity_floor: 0.5,
  intensity_gamma: 0.5,
  hit_gap_ms: 30,                 // the same key within this is one hit (a bounced key or a doubled message)
  // 2. the pedal (the F5 haze fader is the ceiling, always)
  haze_floor: 0.55,               // pedal up: the room's air is the fader's own value x this
  bloom_add: 0.05,                // pedal down: this much on the base bloom mix ... (measured: stage.js BLOOM_MIX 0.05 is
                                  // the value with 0 limiter interventions; 0.10 the next step, 19 in the ceiling window)
  bloom_cap: 0.2,                 // ... never past this whatever the base is
  // 3. the register -> the distance presets (MIDI note numbers: under 48 far, 48..71 medium, 72 and up close)
  register_split: Object.freeze([48, 72]),
  distance_hold_ms: 150,          // a new register must hold this long before the camera is asked to move
  // 4. the quality -> the palette family
  palette_min_beats: 2,           // two family changes never land inside this many beats
  held_max: 32,                   // the held-notes map can never grow past this (a stuck key-up cannot leak)
});

const num = (v, d) => (typeof v === "number" && Number.isFinite(v) ? v : d);
export const clamp01 = (x) => (Number.isFinite(x) ? (x < 0 ? 0 : x > 1 ? 1 : x) : 0);

// ---------------------------------------------------------------------------------------------- the toggle --
// ?piano=1 -> on. Accepts a search string ("?a=1"), a URLSearchParams, or nothing.
export function parsePiano(search) {
  let asked = "";
  try {
    const qs = typeof search === "string" ? new URLSearchParams(search) : search;
    if (qs && typeof qs.get === "function") asked = String(qs.get("piano") ?? "").trim().toLowerCase();
  } catch { asked = ""; }
  return { on: PIANO_ON.includes(asked), asked };
}

// ---------------------------------------------------------------------------------------------- 1. the hit --
// velocity -> the strike's level, exactly as kick.js does it (from_velocity: the velocity range a button's press maps
// over) and the level -> the intensity the lights show (a floor, so the softest note is still a light).
export function levelOfVel(vel, cfg = PIANO_CFG) {
  const [a, b] = cfg.level_from_velocity || [0, 1];
  return clamp01(a + (b - a) * clamp01(vel));
}
export function intensityOf(level, cfg = PIANO_CFG) {
  const f = clamp01(num(cfg.intensity_floor, 0.5));
  return clamp01(f + (1 - f) * Math.pow(clamp01(level), num(cfg.intensity_gamma, 1)));
}
// one note-on -> one hit delta (or null: a note-off, or an event that is not a note)
export function hitOf(ev, cfg = PIANO_CFG) {
  if (!ev || ev.t !== "note" || ev.on === false) return null;
  const key = Math.round(num(ev.key, -1));
  if (!(key >= 0 && key <= 127)) return null;
  const vel = clamp01(num(ev.vel, 0.7));
  const level = levelOfVel(vel, cfg);
  return { type: "hit", kind: cfg.hit_kind, key, vel, level, intensity: intensityOf(level, cfg) };
}

// ---------------------------------------------------------------------------------------------- 2. the pedal --
// the air: the F5 fader is the CEILING, so this can only ever lower what the fader allows (pedal up) or hand it back
// whole (pedal down). No additive haze: a pedal is a sustain, not a second haze fader.
export function pedalHaze(fader, pedalDown, cfg = PIANO_CFG) {
  const f = clamp01(num(fader, 0));
  return pedalDown ? f : f * clamp01(num(cfg.haze_floor, 1));
}
// the bloom mix: the base (stage.js BLOOM_MIX, itself overridable by ?bloommix=) plus the pedal's add, capped. The add is
// the measured spare: 0.05 -> 0.10 put 19 limiter interventions in the six-frame window where the show already sits at
// the flash ceiling (2026-10-26 bloom receipt), so the limiter -- not the knob -- is what decides there.
export function pedalBloom(base, pedalDown, cfg = PIANO_CFG) {
  const b = clamp01(num(base, 0));
  if (!pedalDown) return b;
  return Math.min(clamp01(num(cfg.bloom_cap, 1)), b + Math.max(0, num(cfg.bloom_add, 0)));
}

// ---------------------------------------------------------------------------------------------- 3. the register --
// the notes sounding now, from a {midi: vel} map -> {low, high, mid, count}, or null when nothing is held. mid is the
// centre of the held register, which is what the camera reads: one note is its own register.
export function heldRegister(keys) {
  const ks = Object.keys(keys || {}).map(Number).filter((k) => Number.isFinite(k));
  if (!ks.length) return null;
  let low = Infinity, high = -Infinity;
  for (const k of ks) { if (k < low) low = k; if (k > high) high = k; }
  return { low, high, mid: (low + high) / 2, count: ks.length };
}
// the held register -> a distance stop ("close" | "medium" | "far"), or "auto" when nothing is held (the director's own
// size: the rig lets go of the camera when the hands do). Low pulls the camera out into the room, the top comes in.
export function registerStop(reg, split = PIANO_CFG.register_split) {
  if (!reg) return "auto";
  const [lo, hi] = split || [48, 72];
  const x = num(reg.mid, lo);
  return x >= hi ? "close" : x < lo ? "far" : "medium";
}

// ---------------------------------------------------------------------------------------------- 4. the colours --
// a chord quality (the engine's own spellings: maj, m, 7, maj7, m7, sus2, sus4, add9, madd9, dim, dim7, m7b5, aug, 5, 6,
// m6, 9, maj9, m9, 7sus4 ...) -> the class of colour it asks for. Sus and add are read FIRST -- an add9 on a minor chord
// is the sparkle, not the third -- and a diminished or augmented chord is its own class (tension) rather than a bad
// reading of a triad. 9ths and 6ths otherwise ride their third (m9 minor, maj9 major); a bare "9" is a dominant, major.
export function qualityClass(quality) {
  const q = String(quality || "").toLowerCase().trim();
  if (!q || q === "n" || q === "-" || q === "none") return "unknown";
  if (/dim|aug|°|ø|b5|#5/.test(q)) return "tension";
  if (/sus|add/.test(q)) return "shimmer";
  if (/^m(?!aj)/.test(q) || /min/.test(q)) return "minor";
  return "major";
}
// a class -> the FAMILIES it prefers, in order (palettes.json's own family names). No colour is named or invented here;
// a family the library does not have is simply skipped.
export const FAMILY_LADDER = Object.freeze({
  major: Object.freeze(["warm", "green", "violet"]),
  minor: Object.freeze(["blue", "violet", "neutral"]),
  shimmer: Object.freeze(["violet", "pink", "blue"]),
  tension: Object.freeze(["pink", "violet", "neutral"]),
});
export function familyLadder(cls) { return FAMILY_LADDER[cls] || null; }
// the first family of the class's ladder the library actually has (families: the names loaded), or null -> no change.
export function pickFamily(cls, families) {
  const l = familyLadder(cls);
  if (!l) return null;
  const have = Array.isArray(families) ? families : [];
  return l.find((f) => have.includes(f)) || null;
}
// the palette a family resolves to: the family's first id in library order, and its next one when that is already the
// one showing (so a family change is always a visible change); null when the family holds no palette.
export function resolveFamily(list, family, currentId = null) {
  const fam = (Array.isArray(list) ? list : []).filter((p) => p && p.id && p.family === family);
  if (!fam.length) return null;
  const other = fam.find((p) => p.id !== currentId);
  return (other || fam[0]).id;
}

// ---------------------------------------------------------------------------------------------- the state --
// The reducer's state: plain data, safe to freeze or copy. on is the page's toggle; keys/reg the held register; stop the
// distance last ASKED for (so the same stop is never asked twice: distance.js hands back to auto on a repeated press);
// cand the register a change is waiting on (the hold); pedal, cls, family, paletteAt the rest.
export function emptyState(over = {}) {
  return { on: false, keys: {}, reg: null, stop: "auto", cand: null,
           pedal: false, cls: null, family: null, paletteAt: null,
           lastHit: {}, hits: 0, refused: 0, ...over };
}
// The register's stop may only be asked for once the register has HELD for distance_hold_ms: a chord rolled upwards
// would otherwise walk the camera in and out on the way up. Both step() and tick() run it, so a hold that expires with
// no further event still lands (tick is the page's frame).
function settle(s, ctx, deltas, cfg) {
  const nowMs = num(ctx.nowMs, 0);
  const want = s.reg ? registerStop(s.reg, cfg.register_split) : "auto";
  if (want === s.stop) return { state: s.cand ? { ...s, cand: null } : s, deltas };
  if (!s.cand || s.cand.stop !== want) return { state: { ...s, cand: { stop: want, since: nowMs } }, deltas };
  if (nowMs - s.cand.since + 1e-9 < num(cfg.distance_hold_ms, 0)) return { state: s, deltas };
  deltas.push({ type: "distance", stop: want });
  return { state: { ...s, stop: want, cand: null }, deltas };
}
function cfgOf(ctx) { return { ...PIANO_CFG, ...(ctx && ctx.cfg ? ctx.cfg : {}) }; }

// one engine event -> {state, deltas}. Pure: the same (state, ev, ctx) always gives the same answer, so the whole mapping
// is pinned without a page. ctx: {nowMs, pos (beat), faderHaze, bloomBase, families}.
export function pianoStep(state, ev, ctx = {}) {
  let s = state || emptyState();
  const deltas = [];
  if (!s.on || !ev || typeof ev.t !== "string") return { state: s, deltas };
  const cfg = cfgOf(ctx);
  const nowMs = num(ctx.nowMs, 0);
  if (ev.t === "note") {
    const key = Math.round(num(ev.key, -1));
    if (!(key >= 0 && key <= 127)) return { state: s, deltas };
    const keys = { ...s.keys };
    // a stuck key-up cannot leak: past held_max the oldest note lets go (the register stays the sounding one)
    if (ev.on !== false && !(key in keys) && Object.keys(keys).length >= num(cfg.held_max, 32)) delete keys[Object.keys(keys)[0]];
    if (ev.on === false) delete keys[key]; else keys[key] = clamp01(num(ev.vel, 0.7));
    s = { ...s, keys, reg: heldRegister(keys) };
    if (ev.on !== false) {
      const last = s.lastHit[key];
      if (last === undefined || nowMs - last >= num(cfg.hit_gap_ms, 0)) {
        const h = hitOf(ev, cfg);
        s = { ...s, lastHit: { ...s.lastHit, [key]: nowMs }, hits: s.hits + 1 };
        if (h) deltas.push(h);
      }
    }
  } else if (ev.t === "pedal") {
    const on = ev.on === true;
    if (on !== s.pedal) {
      s = { ...s, pedal: on };
      deltas.push({ type: "pedal", on, haze: pedalHaze(ctx.faderHaze, on, cfg), bloom: pedalBloom(ctx.bloomBase, on, cfg) });
    }
  } else if (ev.t === "chord") {
    // the KEYS' chord names the colour; the audio's own ear never does (that would double the same reading)
    if (ev.src !== "audio") {
      const cls = qualityClass(ev.quality);
      if (cls !== s.cls) {
        s = { ...s, cls };
        const family = pickFamily(cls, ctx.families);
        if (family && family !== s.family) {
          const at = Math.floor(num(ctx.pos, 0) + 1e-6) + 1;        // the next beat line: a chord's colour lands on a beat
          const tooSoon = s.paletteAt !== null && at - s.paletteAt < num(cfg.palette_min_beats, 0) - 1e-9;
          if (!tooSoon) { s = { ...s, family, paletteAt: at }; deltas.push({ type: "family", cls, family, at }); }
        }
      }
    }
  }
  return settle(s, ctx, deltas, cfg);
}

// the page's frame: the same settle, for a register hold that expires between two events (no deltas of its own).
export function pianoTick(state, ctx = {}) {
  const s = state || emptyState();
  if (!s.on) return { state: s, deltas: [] };
  return settle(s, ctx, [], cfgOf(ctx));
}

// what the page says it is doing (the window event arsenal:piano, the receipts' door, the HUD)
export function pianoStatus(state, { faderHaze = 0, bloomBase = 0, cfg = PIANO_CFG } = {}) {
  const s = state || emptyState();
  return { on: !!s.on, pedal: !!s.pedal, stop: s.stop, reg: s.reg, cls: s.cls, family: s.family,
           haze: s.on ? pedalHaze(faderHaze, s.pedal, cfg) : faderHaze,
           bloom: s.on ? pedalBloom(bloomBase, s.pedal, cfg) : bloomBase,
           held: Object.keys(s.keys).length, hits: s.hits, refused: s.refused };
}
