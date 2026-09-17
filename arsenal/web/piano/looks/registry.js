// Looks registry: every visual setting a saved look holds, how to read it from the page and set it, and the one order a
// whole look is applied in. Plain functions over a page object (window.__piano in the browser, a fake in
// tests/piano_looks_registry.test.mjs), so nothing here touches the DOM.
//
// A look covers visual settings only: scheme, instrument, framing, colour, numbers (nns), and the atmosphere's enabled,
// theme, weather, quality, intensity, motion, journey, harmony, waveform, autoWorld, harmonyMode and labels. Key lock,
// minor numbering, the chord reader, the jam view and Claude's cue and voice preferences are never part of one.
//
// The apply order was measured on the page (Studio looks spike, A -> B -> A with canvas hashes):
//   0. recording   stats().rec !== "idle" refuses the whole look (recording, stopping and uploading alike)
//   1. validate    every value against its choices or range; one bad value refuses the whole look
//   2. framing     applyFraming(id)                  only if different (the same id re-snaps the follow camera)
//   3. atmosphere  spectacle.configure(ONE patch)    only the changed fields, all in one call (split calls leave the
//                                                    particle pool at the wrong size); then one microtask, so an
//                                                    instrument's black keys are painted again before anything reads
//   4. colour      setColourMode(mode)               only if different
//   5. numbers     setNumbersMode(mode)              only if different
//   6. instrument  await selectInstrument(id)        only if different (the same id rebuilds it)
//   7. scheme      await selectScheme(id)            only if different; a bake-off seat is probed first
//   8. read back   from looks(), stats() and spectacle.settings, never from storage (a scheme that fails to load
//                  shows Classic while storage keeps its id)
// Modules load one at a time: when two picks race, the later one wins and the earlier resolves false.
// With autoWorld on the atmosphere drifts its own theme, so a look's theme is where the journey starts: it is sent with
// the patch, but diff() and the read-back ignore it.
import { MODES } from "../harmony-model.js";

export const LOOKS_API = "arsenal.piano.looks/v1";
export const REC_REFUSAL = "Stop recording first. A look can't change while you're recording.";
export const REC_BLOCKED = "Stop recording to change this.";

export const LOOK_GROUPS = Object.freeze([
  { id: "scene", label: "Scene" },
  { id: "atmosphere", label: "Atmosphere" },
  { id: "colour", label: "Colour & numbers" },
  { id: "frame", label: "Frame" },
]);

// The apply stages in the verified order; a setting's `order` is its stage's index here.
export const APPLY_ORDER = Object.freeze(["framing", "atmosphere", "colour", "nns", "instrument", "scheme"]);
const STAGE = Object.fromEntries(APPLY_ORDER.map((id, i) => [id, i + 2]));  // 0 and 1 are the REC gate and validation

const LOOK_ID = /^[a-z0-9-]+$/;
const EPSILON = 1e-6;
const opt = (value, label) => Object.freeze({ value, label });

// Choices as the page lists them: schemes and instruments piano.js:1205-1223, colour piano.html:50-52, numbers
// piano.html:79-81 and piano.js:2350, framing piano.js:406-409, themes, quality, weather and labels spectacle.js:11-19,
// 316-317, 340-347, chord visualizations harmony-model.js (MODES).
const SCHEMES = [opt("classic", "Classic trails"), opt("upright-roll", "Upright Roll"), opt("synth-vandor", "Straight Roll"),
  opt("synth-navi", "Bead & Beam"), opt("synth-heimdall", "Glow Echo"), opt("synth-sol", "Afterglow Roll")];
const INSTRUMENTS = [opt("page", "Page keys"), opt("keylab88mk3", "KeyLab 88 mk3"), opt("concert-grand", "Concert grand"),
  opt("upright", "Upright"), opt("suitcase-ep", "Suitcase EP"), opt("vintage-synth", "Vintage synth"),
  opt("glass-piano", "Crystal grand")];
const COLOURS = [opt("pitch", "Pitch (circle of fifths)"), opt("velocity", "How hard you play"), opt("mono", "Amber")];

const call = (fn) => { try { return fn(); } catch { return null; } };

// Everything a snapshot needs, read once: looks(), stats() and the atmosphere's settings.
export function readContext(page) {
  return { looks: call(() => page.looks()), stats: call(() => page.stats()), settings: call(() => page.spectacle?.settings) };
}

const microtask = () => new Promise((resolve) => queueMicrotask(resolve));

// Atmosphere fields go through one configure() patch when a whole look applies; alone (a live control) they send
// just their own field.
function atmosphere(id, group, label, type, extra) {
  return {
    id, group, label, type, ...extra, order: STAGE.atmosphere, batch: "atmosphere",
    read: (page, ctx = readContext(page)) => ctx.settings ? ctx.settings[id] : undefined,
    async apply(page, value) {
      const spectacle = call(() => page.spectacle);
      if (!spectacle) return false;
      const ok = spectacle.configure({ [id]: value }) !== false;
      await microtask();
      return ok;
    },
  };
}

function knownIds(kind, ctx) {
  const listed = kind === "scheme" ? ctx?.looks?.schemes : ctx?.looks?.instruments;
  const ids = new Set((kind === "scheme" ? SCHEMES : INSTRUMENTS).map((o) => o.value));
  if (Array.isArray(listed)) for (const s of listed) if (s && typeof s.id === "string") ids.add(s.id);
  return ids;
}

function moduleOptions(kind, page) {
  const listed = call(() => page.looks())?.[kind === "scheme" ? "schemes" : "instruments"];
  if (!Array.isArray(listed)) return kind === "scheme" ? SCHEMES : INSTRUMENTS;
  return listed.filter((s) => s && typeof s.id === "string" && s.listed !== false).map((s) => opt(s.id, s.name || s.id));
}

async function selectModule(kind, page, id) {
  if (kind === "scheme") {
    const entry = call(() => page.looks())?.schemes?.find((s) => s.id === id);
    if (entry && entry.listed === false && typeof page.probeSchemes === "function") await page.probeSchemes();
    return (await page.selectScheme(id)) === true;
  }
  return (await page.selectInstrument(id)) === true;
}

export const LOOK_SETTINGS = Object.freeze([
  // ------------------------------------------------------------------ Scene
  {
    id: "scheme", group: "scene", label: "Note scheme", type: "choice", values: SCHEMES, recBlocked: true,
    order: STAGE.scheme, options: (page) => moduleOptions("scheme", page),
    read: (page, ctx = readContext(page)) => ctx.looks?.scheme,
    apply: (page, value) => selectModule("scheme", page, value),
  },
  {
    id: "instrument", group: "scene", label: "Instrument", type: "choice", values: INSTRUMENTS, recBlocked: true,
    order: STAGE.instrument, options: (page) => moduleOptions("instrument", page),
    read: (page, ctx = readContext(page)) => ctx.looks?.instrument,
    apply: (page, value) => selectModule("instrument", page, value),
  },
  // ------------------------------------------------------------- Atmosphere
  atmosphere("enabled", "atmosphere", "Cinematic atmosphere", "toggle", { recBlocked: true }),
  atmosphere("theme", "atmosphere", "Environment", "choice", {
    recBlocked: true,
    values: [opt("moon", "Moonlit lake"), opt("ember", "Ember sanctuary"), opt("nebula", "Velvet nebula"),
      opt("winter", "Winter mountains"), opt("rain", "Rainforest at midnight"), opt("city", "City of light")],
  }),
  atmosphere("weather", "atmosphere", "Weather", "choice", {
    recBlocked: false,
    values: [opt("world", "Environment default"), opt("none", "Clear air"), opt("rain", "Rain"), opt("snow", "Snow"),
      opt("embers", "Embers")],
  }),
  atmosphere("harmonyMode", "atmosphere", "Chord visualization", "choice", {
    recBlocked: true, values: Object.entries(MODES).map(([id, m]) => opt(id, m.name)),
  }),
  atmosphere("intensity", "atmosphere", "Light & impact", "range", { recBlocked: false, range: { min: 0.25, max: 1.4, step: 0.05 } }),
  atmosphere("motion", "atmosphere", "Motion", "range", { recBlocked: false, range: { min: 0.15, max: 1, step: 0.05 } }),
  atmosphere("journey", "atmosphere", "Camera drift", "range", { recBlocked: false, range: { min: 0, max: 1, step: 0.05 } }),
  atmosphere("harmony", "atmosphere", "Let harmony colour the world", "toggle", { recBlocked: false }),
  atmosphere("waveform", "atmosphere", "Waveform from connected audio", "toggle", { recBlocked: false }),
  atmosphere("autoWorld", "atmosphere", "Travel with the music", "toggle", { recBlocked: true }),
  atmosphere("labels", "atmosphere", "Theory display", "choice", {
    recBlocked: true,
    values: [opt("harmony", "Chord + Nashville + note glass"), opt("full", "Harmony + staff"),
      opt("chord", "Chord + note glass"), opt("off", "Pure performance")],
  }),
  // ------------------------------------------------------- Colour & numbers
  {
    id: "colour", group: "colour", label: "Note colour", type: "choice", recBlocked: false, order: STAGE.colour,
    values: COLOURS,
    // stats().colour is COLOUR.mode; until the page reports it, the stored choice holds the same value (piano.js:316,
    // 4016-4017). The page never checks the stored mode, and notes fall back to pitch colour for an unknown one.
    read(page, ctx = readContext(page)) {
      let mode = ctx.stats?.colour;
      if (mode === undefined) { try { mode = globalThis.localStorage?.getItem("arsenal.piano.colour") || "pitch"; } catch { mode = "pitch"; } }
      return COLOURS.some((o) => o.value === mode) ? mode : "pitch";
    },
    apply: async (page, value) => page.setColourMode(value) !== false,
  },
  {
    id: "nns", group: "colour", label: "Nashville numbers", type: "choice", recBlocked: false, order: STAGE.nns,
    values: [opt("chord", "With the chord name"), opt("numbers", "Numbers only"), opt("off", "Off")],
    read: (page, ctx = readContext(page)) => ctx.stats?.nnsMode,
    apply: async (page, value) => page.setNumbersMode(value) !== false,
  },
  // ------------------------------------------------------------------ Frame
  {
    id: "framing", group: "frame", label: "Framing", type: "choice", recBlocked: true, order: STAGE.framing,
    values: [opt("9:16", "Tall 9:16 (phone)"), opt("16:9", "Wide 16:9")],
    read: (page, ctx = readContext(page)) => ctx.stats?.framing,
    apply: async (page, value) => page.applyFraming(value) !== false,
  },
  atmosphere("quality", "frame", "Render quality", "choice", {
    recBlocked: true,
    values: [opt("studio", "Studio · 1080p"), opt("ultra", "Ultra · 1440p"), opt("cinema", "Cinema · 4K")],
  }),
].map((s) => Object.freeze(s)));

export const LOOK_IDS = Object.freeze(LOOK_SETTINGS.map((s) => s.id));
const BY_ID = new Map(LOOK_SETTINGS.map((s) => [s.id, s]));
export const setting = (id) => BY_ID.get(id) || null;

// ------------------------------------------------------------------ values --
export function validateValue(id, value, page = null, ctx = null) {
  const s = BY_ID.get(id);
  if (!s) return `${id} is not a look setting`;
  if (s.type === "toggle") return typeof value === "boolean" ? null : `${s.label} must be on or off`;
  if (s.type === "range") {
    const { min, max } = s.range;
    return Number.isFinite(value) && value >= min - EPSILON && value <= max + EPSILON ? null
      : `${s.label} must be a number from ${min} to ${max}`;
  }
  if (typeof value !== "string") return `${s.label} must be one of its choices`;
  if (id === "scheme" || id === "instrument") {
    if (!LOOK_ID.test(value)) return `${s.label} "${value.slice(0, 40)}" is not a name the page uses`;
    const known = knownIds(id, ctx || (page ? readContext(page) : null));
    return known.has(value) ? null : `the page has no ${s.label.toLowerCase()} called "${value.slice(0, 40)}"`;
  }
  return s.values.some((o) => o.value === value) ? null : `${s.label} "${String(value).slice(0, 40)}" is not one of its choices`;
}

const sameValue = (s, a, b) => s.type === "range" ? Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= EPSILON : a === b;

// The settings part of a look: a preset ({ id, name, settings }) or a plain settings object.
export function lookSettings(look) {
  if (!look || typeof look !== "object") return null;
  return look.settings && typeof look.settings === "object" && !Array.isArray(look.settings) ? look.settings : look;
}

// Only the look settings, with simple values: what a preset stores.
export function cleanLook(look) {
  const src = lookSettings(look) || {};
  const out = {};
  for (const id of LOOK_IDS) {
    const v = src[id];
    if (typeof v === "boolean" || typeof v === "string" || Number.isFinite(v)) out[id] = v;
  }
  return out;
}

// What the page shows now, as a look (fields the page cannot report, such as the atmosphere when it failed to start,
// are left out).
export function snapshot(page) {
  const ctx = readContext(page);
  const out = {};
  for (const s of LOOK_SETTINGS) {
    const v = call(() => s.read(page, ctx));
    if (v !== undefined && v !== null) out[s.id] = v;
  }
  return out;
}

// [{ id, label, from, to }] for every setting both looks hold with different values. theme is left out while either
// look travels with the music (autoWorld), because the atmosphere moves it by itself.
export function diff(a, b) {
  const A = lookSettings(a), B = lookSettings(b);
  if (!A || !B) return [];
  const travelling = A.autoWorld === true || B.autoWorld === true;
  const out = [];
  for (const s of LOOK_SETTINGS) {
    const from = A[s.id], to = B[s.id];
    if (from === undefined || to === undefined) continue;
    if (s.id === "theme" && travelling) continue;
    if (!sameValue(s, from, to)) out.push({ id: s.id, label: s.label, from, to });
  }
  return out;
}

export function recording(page) {
  const stats = call(() => page.stats());
  return !!stats && stats.rec !== undefined && stats.rec !== "idle";
}

// One look or setting change at a time per page, so two module loads never race.
const queues = new WeakMap();
function serial(page, job) {
  const key = page && typeof page === "object" ? page : serial;
  const prev = queues.get(key) || Promise.resolve();
  const run = prev.then(job, job);
  queues.set(key, run.catch(() => {}));
  return run;
}

async function lookModulesSettled(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const L = call(() => page.looks());
    if (!L || L.ready !== false) return true;
    if (Date.now() >= deadline) return false;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

// applyLook(page, look) -> { ok, reason, refused, applied, unchanged, failed, steps, state }
//   refused: "recording" | "invalid" | "loading" | null; the page is untouched when a look is refused.
//   applied: ids the page took; unchanged: ids already showing; failed: [{ id, reason }]; steps: the stages run, in order;
//   state: snapshot(page) afterwards.
export function applyLook(page, look, opts = {}) {
  return serial(page, () => applyLookNow(page, look, opts));
}

async function applyLookNow(page, look, { readyTimeoutMs = 10000 } = {}) {
  const result = { ok: false, reason: null, refused: null, applied: [], unchanged: [], failed: [], steps: [], state: null };
  const settings = lookSettings(look);
  const done = () => { result.state = snapshot(page); return result; };
  if (!settings) { result.refused = "invalid"; result.reason = "That isn't a look."; return done(); }
  if (!(await lookModulesSettled(page, readyTimeoutMs))) {
    result.refused = "loading"; result.reason = "The page is still loading its scheme and instrument. Try again in a moment.";
    return done();
  }
  if (recording(page)) { result.refused = "recording"; result.reason = REC_REFUSAL; return done(); }

  const ctx = readContext(page);
  const wanted = LOOK_SETTINGS.filter((s) => settings[s.id] !== undefined);
  const problems = wanted.map((s) => validateValue(s.id, settings[s.id], page, ctx)).filter(Boolean);
  if (problems.length) {
    result.refused = "invalid"; result.reason = `This look can't be used: ${problems.join("; ")}.`;
    return done();
  }
  const travelling = settings.autoWorld === true;
  const changed = new Map();
  for (const s of wanted) {
    const now = call(() => s.read(page, ctx));
    if (now !== undefined && sameValue(s, now, settings[s.id])) result.unchanged.push(s.id);
    else changed.set(s.id, settings[s.id]);
  }
  const fail = (ids, reason) => { for (const id of ids) result.failed.push({ id, reason }); };
  const took = (ids) => { result.applied.push(...ids); };
  const stillIdle = (ids) => {
    if (!recording(page)) return true;
    fail(ids, "Recording started before this could change.");
    return false;
  };

  // 2. framing
  if (changed.has("framing")) {
    result.steps.push("framing");
    const ok = call(() => page.applyFraming(changed.get("framing"))) !== false;
    (ok ? took : (ids) => fail(ids, "The page kept its framing."))(["framing"]);
  }
  // 3. atmosphere, one patch
  const patchIds = LOOK_SETTINGS.filter((s) => s.batch === "atmosphere" && changed.has(s.id)).map((s) => s.id);
  if (patchIds.length) {
    result.steps.push("atmosphere");
    const spectacle = call(() => page.spectacle);
    if (!spectacle) fail(patchIds, "The atmosphere isn't available on this page.");
    else {
      const patch = Object.fromEntries(patchIds.map((id) => [id, changed.get(id)]));
      let ok;
      try { ok = spectacle.configure(patch) !== false; } catch { ok = false; }
      await microtask();
      (ok ? took : (ids) => fail(ids, "The atmosphere refused the change."))(patchIds);
    }
  }
  // 4, 5. colour and numbers
  for (const [id, setter] of [["colour", "setColourMode"], ["nns", "setNumbersMode"]]) {
    if (!changed.has(id)) continue;
    result.steps.push(id);
    let ok;
    try { ok = page[setter](changed.get(id)) !== false; } catch { ok = false; }
    (ok ? took : (ids) => fail(ids, "The page kept its setting."))([id]);
  }
  // 6, 7. instrument, then scheme: awaited one at a time
  for (const id of ["instrument", "scheme"]) {
    if (!changed.has(id)) continue;
    if (!stillIdle([id])) continue;
    result.steps.push(id);
    let ok;
    try { ok = await selectModule(id, page, changed.get(id)); } catch { ok = false; }
    (ok ? took : (ids) => fail(ids, `The ${id} didn't load.`))([id]);
  }
  // 8. read back from the page
  done();
  for (const id of [...result.applied]) {
    if (id === "theme" && travelling) continue;
    const s = BY_ID.get(id), now = result.state[id];
    if (now === undefined || sameValue(s, now, changed.get(id))) continue;
    result.applied.splice(result.applied.indexOf(id), 1);
    fail([id], `The page shows ${String(now)} instead.`);
  }
  result.ok = result.failed.length === 0;
  if (!result.ok) result.reason = `Some of this look didn't apply: ${result.failed.map((f) => BY_ID.get(f.id).label).join(", ")}.`;
  return result;
}

// applySetting(page, id, value) -> { ok, changed, reason, value }: one live control. A recBlocked setting is refused
// while recording; the rest go through as the page allows. Queued behind any look being applied.
export function applySetting(page, id, value) {
  return serial(page, async () => {
    const s = BY_ID.get(id);
    const ctx = readContext(page);
    const problem = validateValue(id, value, page, ctx);
    if (problem) return { ok: false, changed: false, reason: `${problem}.`, value: s ? call(() => s.read(page, ctx)) : undefined };
    if (s.recBlocked && recording(page)) return { ok: false, changed: false, reason: REC_BLOCKED, value: call(() => s.read(page, ctx)) };
    const before = call(() => s.read(page, ctx));
    if (before !== undefined && sameValue(s, before, value)) return { ok: true, changed: false, reason: null, value: before };
    let ok;
    try { ok = await s.apply(page, value); } catch { ok = false; }
    const after = call(() => s.read(page));
    const landed = ok && after !== undefined && sameValue(s, after, value);
    return { ok: landed, changed: landed, reason: landed ? null : `The page kept ${s.label.toLowerCase()} as it was.`, value: after };
  });
}
