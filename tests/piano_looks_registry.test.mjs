// Node tests for arsenal/web/piano/looks/registry.js. Zero dependencies:  node tests/piano_looks_registry.test.mjs
// A fake page stands in for window.__piano and records every setter call, so the apply order, the one-patch rule, the
// microtask after configure(), the REC refusal and the autoWorld handling are checked without a browser.
import {
  APPLY_ORDER, LOOK_GROUPS, LOOK_IDS, LOOK_SETTINGS, REC_BLOCKED, REC_REFUSAL,
  applyLook, applySetting, cleanLook, diff, setting, snapshot, validateValue,
} from "../arsenal/web/piano/looks/registry.js";

let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
const tick = (ms = 0) => new Promise((resolve) => setTimeout(resolve, ms));

const A = { scheme: "classic", instrument: "page", enabled: true, theme: "moon", weather: "world", harmonyMode: "tonnetz",
  intensity: 0.85, motion: 1, journey: 0, harmony: true, waveform: true, autoWorld: false, labels: "harmony",
  colour: "pitch", nns: "chord", framing: "9:16", quality: "studio" };
const B = { scheme: "synth-sol", instrument: "concert-grand", enabled: true, theme: "city", weather: "snow",
  harmonyMode: "atmosphere", intensity: 1.3, motion: 1, journey: 0.6, harmony: false, waveform: false, autoWorld: true,
  labels: "full", colour: "mono", nns: "numbers", framing: "16:9", quality: "ultra" };
const ATMOSPHERE = ["enabled", "theme", "weather", "harmonyMode", "intensity", "motion", "journey", "harmony", "waveform",
  "autoWorld", "labels", "quality"];

// A page that behaves like piano.js where the registry can tell: configure() repaints the instrument's black keys a
// microtask later (piano.js:4555), module loads are async and the later pick wins, the page refuses modules, framing and
// quality while recording, and a bake-off scheme is listed only after probeSchemes().
function fakePage(start = A, opts = {}) {
  const log = [];
  const s = { ...start, rec: "idle", ready: true, blackPainted: true, loads: 0, probed: false, colourStat: true, ...opts };
  const settings = Object.fromEntries(ATMOSPHERE.map((k) => [k, s[k]]));
  const spectacle = {
    settings,
    configure(patch) {
      log.push(["configure", { ...patch }]);
      if (patch.quality && s.rec !== "idle") return false;
      Object.assign(settings, patch);
      s.blackPainted = false;
      queueMicrotask(() => { s.blackPainted = true; });
      if (s.onConfigure) s.onConfigure(settings);
      return true;
    },
  };
  const load = (kind) => async (id) => {
    const token = ++s.loads;
    log.push([`${kind}:start`, id]);
    if (s.rec !== "idle") { log.push([`${kind}:refused`, id]); return false; }
    await tick(5);
    if (s.onLoad) s.onLoad(kind, id);
    if (token !== s.loads) { log.push([`${kind}:lost`, id]); return false; }
    if (s.broken === id) { log.push([`${kind}:end`, id]); s[kind] = kind === "scheme" ? "classic" : "page"; return false; }
    s[kind] = id;
    log.push([`${kind}:end`, id]);
    return true;
  };
  const page = {
    log, s,
    looks: () => ({ ready: s.ready, scheme: s.scheme, instrument: s.instrument,
      schemes: ["classic", "upright-roll", "synth-vandor", "synth-navi", "synth-heimdall", "synth-sol", "synth-asta"]
        .map((id) => ({ id, name: id, listed: id !== "synth-asta" || s.probed })),
      instruments: ["page", "keylab88mk3", "concert-grand", "upright", "suitcase-ep", "vintage-synth", "glass-piano"]
        .map((id) => ({ id, name: id, listed: true })) }),
    stats: () => ({ framing: s.framing, nnsMode: s.nns, rec: s.rec, ...(s.colourStat ? { colour: s.colour } : {}) }),
    get spectacle() { return s.noSpectacle ? null : spectacle; },
    applyFraming(id) {
      log.push(["applyFraming", id]);
      if (s.rec !== "idle" && id !== s.framing) return false;
      s.framing = id;
      return true;
    },
    setColourMode(mode) { log.push(["setColourMode", mode, s.blackPainted]); s.colour = mode; },
    setNumbersMode(mode) { log.push(["setNumbersMode", mode, s.blackPainted]); s.nns = mode; },
    selectInstrument: load("instrument"),
    selectScheme: load("scheme"),
    async probeSchemes() { log.push(["probeSchemes"]); await tick(2); s.probed = true; return page.looks().schemes; },
  };
  return page;
}
const names = (page) => page.log.map((e) => e[0]);

// ----------------------------------------------------------- descriptors --
eq("a look holds exactly the visual settings", [...LOOK_IDS].sort(),
  ["autoWorld", "colour", "enabled", "framing", "harmony", "harmonyMode", "instrument", "intensity", "journey", "labels",
   "motion", "nns", "quality", "scheme", "theme", "waveform", "weather"]);
for (const excluded of ["key", "minor", "reader", "view", "cueView", "voice"]) check(`${excluded} is never part of a look`, !setting(excluded));
eq("groups are Scene, Atmosphere, Colour & numbers, Frame", LOOK_GROUPS.map((g) => g.label), ["Scene", "Atmosphere", "Colour & numbers", "Frame"]);
const byGroup = Object.fromEntries(LOOK_GROUPS.map((g) => [g.id, LOOK_SETTINGS.filter((s) => s.group === g.id).map((s) => s.id)]));
eq("Scene holds scheme and instrument", byGroup.scene, ["scheme", "instrument"]);
eq("Atmosphere holds its eleven controls", byGroup.atmosphere,
  ["enabled", "theme", "weather", "harmonyMode", "intensity", "motion", "journey", "harmony", "waveform", "autoWorld", "labels"]);
eq("Colour & numbers holds colour and nns", byGroup.colour, ["colour", "nns"]);
eq("Frame holds framing and quality", byGroup.frame, ["framing", "quality"]);
eq("recBlocked: what the page refuses plus what compiles mid-take", LOOK_SETTINGS.filter((s) => s.recBlocked).map((s) => s.id).sort(),
  ["autoWorld", "enabled", "framing", "harmonyMode", "instrument", "labels", "quality", "scheme", "theme"]);
eq("apply order", APPLY_ORDER, ["framing", "atmosphere", "colour", "nns", "instrument", "scheme"]);
for (const s of LOOK_SETTINGS) {
  check(`${s.id} has read and apply`, typeof s.read === "function" && typeof s.apply === "function");
  check(`${s.id} has a label and a known type`, !!s.label && ["choice", "toggle", "range"].includes(s.type));
  check(`${s.id} has values or a range`, s.type === "toggle" || (s.type === "choice" ? s.values.length > 1 : s.range.max > s.range.min));
  const stage = ATMOSPHERE.includes(s.id) ? "atmosphere" : s.id;
  eq(`${s.id} order is its stage`, s.order, APPLY_ORDER.indexOf(stage) + 2);
}
eq("nine chord visualizations", setting("harmonyMode").values.length, 9);

// ---------------------------------------------------------------- values --
check("A validates", LOOK_IDS.every((id) => validateValue(id, A[id]) === null));
check("B validates", LOOK_IDS.every((id) => validateValue(id, B[id]) === null));
for (const [id, bad] of [["theme", "sepia"], ["colour", "sepia"], ["intensity", 3], ["motion", 0.1], ["journey", "0.5"],
  ["enabled", "yes"], ["framing", "4:3"], ["scheme", "Synth Sol"], ["scheme", "not-a-scheme"], ["instrument", 7],
  ["quality", "8k"], ["nns", "roman"]]) {
  check(`${id}=${JSON.stringify(bad)} is refused`, typeof validateValue(id, bad) === "string");
}
check("a probe scheme the page lists validates against the page", validateValue("scheme", "synth-asta", fakePage()) === null);
eq("cleanLook keeps only look settings with simple values",
  cleanLook({ settings: { ...A, key: "E minor", minor: "relative", reader: "next", intensity: NaN, theme: { x: 1 } } }),
  Object.fromEntries(Object.entries(A).filter(([k]) => !["intensity", "theme"].includes(k))));

// -------------------------------------------------------------- snapshot --
{
  const page = fakePage();
  eq("snapshot reads the page", snapshot(page), Object.fromEntries(LOOK_IDS.map((id) => [id, A[id]])));
  page.s.colour = "sepia";
  eq("an unknown colour mode shows as pitch", snapshot(page).colour, "pitch");
  const bare = fakePage(A, { noSpectacle: true });
  check("no atmosphere: its fields are left out", ATMOSPHERE.every((id) => !(id in snapshot(bare))) && snapshot(bare).scheme === "classic");
  eq("no calls while reading", page.log.length + bare.log.length, 0);
}

// ------------------------------------------------------------ apply order --
{
  const page = fakePage(A);
  const r = await applyLook(page, { id: "look-b", name: "B", settings: B });
  check("A -> B applies", r.ok, JSON.stringify(r));
  eq("stages run in the verified order", r.steps, APPLY_ORDER);
  eq("setter calls in the verified order", names(page),
    ["applyFraming", "configure", "setColourMode", "setNumbersMode", "instrument:start", "instrument:end", "scheme:start", "scheme:end"]);
  const configures = page.log.filter((e) => e[0] === "configure");
  eq("one configure() with every changed atmosphere field", configures.map((e) => Object.keys(e[1]).sort()),
    [["autoWorld", "harmony", "harmonyMode", "intensity", "journey", "labels", "quality", "theme", "waveform", "weather"]]);
  check("enabled and motion were unchanged, so not sent", !("enabled" in configures[0][1]) && !("motion" in configures[0][1]));
  check("a microtask ran after configure() before colour was set", page.log.find((e) => e[0] === "setColourMode")[2] === true);
  eq("the page shows B", r.state, Object.fromEntries(LOOK_IDS.map((id) => [id, B[id]])));
  eq("applied lists every changed field", [...r.applied].sort(), LOOK_IDS.filter((id) => A[id] !== B[id]).sort());
  eq("unchanged lists the rest", r.unchanged.sort(), ["enabled", "motion"]);

  page.log.length = 0;
  const back = await applyLook(page, A);
  check("B -> A applies", back.ok && back.steps.join() === APPLY_ORDER.join());
  eq("B -> A in the same order", names(page),
    ["applyFraming", "configure", "setColourMode", "setNumbersMode", "instrument:start", "instrument:end", "scheme:start", "scheme:end"]);

  page.log.length = 0;
  const again = await applyLook(page, A);
  check("re-applying the look shown touches nothing", again.ok && page.log.length === 0 && again.applied.length === 0,
    JSON.stringify(page.log));
  eq("... and reports every field unchanged", again.unchanged.sort(), [...LOOK_IDS].sort());
}
{
  const page = fakePage(A);
  const r = await applyLook(page, { theme: "city", enabled: true, colour: "velocity" });
  check("a partial look applies", r.ok);
  eq("only its changed fields are called", page.log.map((e) => e.slice(0, 2)), [["configure", { theme: "city" }], ["setColourMode", "velocity"]]);
  eq("the rest of the page is left as it was", r.state.scheme + r.state.framing + r.state.nns, "classic9:16chord");
}
{
  const page = fakePage(A, { instrument: "concert-grand" });
  await applyLook(page, { enabled: false, colour: "mono" });
  check("with an instrument mounted, colour waits for its black keys", page.log.find((e) => e[0] === "setColourMode")[2] === true);
}

// ------------------------------------------------------------- recording --
for (const rec of ["recording", "stopping", "uploading"]) {
  const page = fakePage(A, { rec });
  const r = await applyLook(page, B);
  check(`REC ${rec}: the whole look is refused`, !r.ok && r.refused === "recording" && r.reason === REC_REFUSAL);
  eq(`REC ${rec}: nothing on the page is called`, page.log, []);
  eq(`REC ${rec}: the page still shows A`, r.state.theme + r.state.colour, "moonpitch");
  const free = await applySetting(page, "intensity", 1.1);
  check(`REC ${rec}: intensity still changes live`, free.ok && page.s.intensity !== undefined && page.spectacle.settings.intensity === 1.1);
  const blocked = await applySetting(page, "theme", "city");
  check(`REC ${rec}: theme is blocked live`, !blocked.ok && blocked.reason === REC_BLOCKED && page.spectacle.settings.theme === "moon");
}
for (const [id, value] of [["weather", "rain"], ["motion", 0.4], ["journey", 0.3], ["harmony", false], ["waveform", false],
  ["colour", "velocity"], ["nns", "off"]]) {
  const page = fakePage(A, { rec: "recording" });
  const r = await applySetting(page, id, value);
  check(`REC: ${id} is free`, r.ok && r.changed, JSON.stringify(r));
}
for (const id of ["scheme", "instrument", "framing", "quality", "theme", "enabled", "harmonyMode", "labels", "autoWorld"]) {
  const page = fakePage(A, { rec: "recording" });
  const r = await applySetting(page, id, B[id] === A[id] ? !A[id] : B[id]);
  check(`REC: ${id} is blocked`, !r.ok && r.reason === REC_BLOCKED && page.log.length === 0, JSON.stringify(r));
}
{
  const page = fakePage(A, { onLoad: (kind) => { if (kind === "instrument") page.s.rec = "recording"; } });
  const r = await applyLook(page, B);
  check("recording that starts during the instrument load stops the scheme", !r.ok && !names(page).includes("scheme:start"));
  check("... and names the scheme as not applied", r.failed.some((f) => f.id === "scheme" && /Recording/.test(f.reason)));
}

// ------------------------------------------------------------ validation --
{
  const page = fakePage(A);
  const r = await applyLook(page, { ...B, theme: "sepia" });
  check("one bad value refuses the whole look", !r.ok && r.refused === "invalid" && /Environment/.test(r.reason), r.reason);
  eq("... and nothing is called", page.log, []);
  const r2 = await applyLook(page, { intensity: 9 });
  check("an out-of-range number refuses the look", !r2.ok && r2.refused === "invalid" && page.log.length === 0);
  const r3 = await applyLook(page, null);
  check("no look at all is refused", !r3.ok && r3.refused === "invalid");
  const r4 = await applyLook(page, { key: "E minor", minor: "relative" });
  check("settings outside a look are ignored, not applied", r4.ok && page.log.length === 0);
}

// -------------------------------------------------------------- autoWorld --
{
  const page = fakePage({ ...A, autoWorld: true, theme: "nebula" });
  const look = { ...A, autoWorld: true, theme: "moon" };
  let drifted = false;
  page.s.onConfigure = (settings) => { if (!drifted) { drifted = true; queueMicrotask(() => { settings.theme = "city"; }); } };
  const r = await applyLook(page, look);
  eq("autoWorld on: theme is sent as the journey's start, in the one patch", page.log.filter((e) => e[0] === "configure").map((e) => e[1]),
    [{ theme: "moon" }]);
  check("autoWorld on: a drift before read-back is not a failure", r.ok, JSON.stringify(r.failed));
  eq("autoWorld on: diff ignores the drifted theme", diff(look, snapshot(page)), []);
  eq("autoWorld on in either look: theme ignored", diff({ theme: "moon", autoWorld: false }, { theme: "city", autoWorld: true }).map((d) => d.id),
    ["autoWorld"]);
  eq("autoWorld off: a theme change is a difference", diff({ ...A }, { ...A, theme: "city" }).map((d) => d.id), ["theme"]);
}
{
  const page = fakePage(A, { onConfigure: (settings) => { settings.theme = "rain"; } });
  const r = await applyLook(page, { theme: "city" });
  check("autoWorld off: a theme the page didn't keep is reported", !r.ok && r.failed.some((f) => f.id === "theme"));
}

// ------------------------------------------------------------------- diff --
eq("diff of a look with itself", diff(A, { ...A }), []);
eq("diff tolerates float noise", diff({ intensity: 0.85 }, { intensity: 0.8500000001 }), []);
eq("diff names each change with its label", diff({ intensity: 0.85, colour: "pitch" }, { intensity: 1.3, colour: "mono" }),
  [{ id: "intensity", label: "Light & impact", from: 0.85, to: 1.3 }, { id: "colour", label: "Note colour", from: "pitch", to: "mono" }]);
eq("diff skips settings only one look holds", diff({ scheme: "classic" }, { framing: "16:9" }), []);
eq("diff accepts presets", diff({ id: "x", name: "X", settings: { nns: "chord" } }, { settings: { nns: "off" } }).map((d) => d.id), ["nns"]);
eq("diff ignores fields that are not look settings", diff({ key: "E minor" }, { key: "C major" }), []);
eq("diff of nothing", diff(null, A), []);

// ------------------------------------------------------ modules and races --
{
  const page = fakePage(A, { broken: "synth-sol" });
  const r = await applyLook(page, { scheme: "synth-sol", colour: "mono" });
  check("a scheme that fails to load is reported, the rest stays applied", !r.ok && r.applied.includes("colour")
    && r.failed.length === 1 && r.failed[0].id === "scheme", JSON.stringify(r));
  check("... with a plain reason", /Note scheme/.test(r.reason) && r.state.scheme === "classic");
}
{
  const page = fakePage(A);
  const r = await applyLook(page, { scheme: "synth-asta" });
  check("a bake-off scheme is probed before it is selected", r.ok && names(page).join() === "probeSchemes,scheme:start,scheme:end",
    names(page).join());
}
{
  const page = fakePage(A);
  const first = applyLook(page, B), second = applyLook(page, { scheme: "synth-navi", instrument: "upright" });
  const [r1, r2] = await Promise.all([first, second]);
  check("two looks at once both apply, one after the other", r1.ok && r2.ok, JSON.stringify([r1.failed, r2.failed]));
  check("no module load is lost to a race", !names(page).some((n) => n.endsWith(":lost")));
  const endFirst = page.log.findIndex((e) => e[0] === "scheme:end" && e[1] === "synth-sol");
  const startSecond = page.log.findIndex((e) => e[0] === "instrument:start" && e[1] === "upright");
  check("the second look starts after the first finishes", endFirst >= 0 && startSecond > endFirst);
  eq("the later look wins", [page.s.scheme, page.s.instrument], ["synth-navi", "upright"]);
  const live = applySetting(page, "colour", "velocity");
  const look = applyLook(page, { colour: "pitch" });
  await Promise.all([live, look]);
  eq("a live control and a look queue in the order they came", page.s.colour, "pitch");
}
{
  const page = fakePage(A, { ready: false });
  setTimeout(() => { page.s.ready = true; }, 120);
  const r = await applyLook(page, { scheme: "synth-vandor" });
  check("a look waits until the page's stored scheme and instrument have loaded", r.ok && page.s.scheme === "synth-vandor");
  const stuck = fakePage(A, { ready: false });
  const r2 = await applyLook(stuck, { scheme: "synth-vandor" }, { readyTimeoutMs: 80 });
  check("... and gives up with a plain reason", !r2.ok && r2.refused === "loading" && stuck.log.length === 0);
}
{
  const page = fakePage(A, { noSpectacle: true });
  const r = await applyLook(page, { enabled: true, theme: "city", colour: "mono" });
  check("no atmosphere: its fields fail, the rest applies", !r.ok && r.applied.join() === "colour"
    && r.failed.map((f) => f.id).sort().join() === "enabled,theme");
}
{
  const page = fakePage(A, { colourStat: false });
  const r = await applySetting(page, "framing", "16:9");
  check("applySetting sets framing through applyFraming", r.ok && page.log[0][0] === "applyFraming" && page.s.framing === "16:9");
  const same = await applySetting(page, "framing", "16:9");
  check("applySetting skips a value already shown (no camera re-snap)", same.ok && !same.changed && page.log.length === 1);
  const bad = await applySetting(page, "framing", "4:3");
  check("applySetting refuses a bad value", !bad.ok && /Framing/.test(bad.reason) && page.log.length === 1);
  const q = await applySetting(page, "quality", "cinema");
  eq("applySetting sends one atmosphere field alone", page.log.at(-1), ["configure", { quality: "cinema" }]);
  check("... and reports it", q.ok && q.value === "cinema");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
