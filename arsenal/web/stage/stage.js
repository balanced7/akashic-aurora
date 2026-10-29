// Virtual Stage v0: arsenal/web/stage/stage.js (ES module), the page at /web/stage/index.html. Pure logic lives in the
// modules beside it (tests/stage_*.test.mjs); the browser receipt is arsenal/lanes/stage_verify.mjs.
//
// Daniel, 2026-10-24: "Also I want us to recreate that set or something similar with no fewer lasers and fog machines
// and lights. This will require research to find out how those things are wired and animated so we can build our own
// routines for this. They were able to do this in real life, surely in a 3d space we can come up with even more
// incredible and cinematic visual expirences! the arial shots they get we can use as suggestions for camera flypaths"
//
// The page wires the rig together, once per animation frame:
//   events (the VJ engine's Server-Sent Events, or the built-in demo clock)
//     -> grid (one beat position) -> show (sections, demo pads) -> programmer (looks, effects, pads, physics)
//     -> kinetics (the strand's hoists) -> lasers (the brain) -> lasers3d (3D projectors) -> camera director
//     -> atmosphere -> renderer (three.js, house GLSL) -> the final-frame flash limiter -> the canvas.
// URL: ?demo=1 (the demo show, no engine) ?engine=http://127.0.0.1:8794 (default; "off" for none) ?set=source-v1
//      (source-v0 still loads) ?quality=high|receipt|low ?hud=0 ?w=&h= (a fixed backing size, for receipts)
//      ?theme=dreaming-city (one of the set's themes) ?phrase=pillars (the phrase pad 3 starts) ?ring=orrery (a ring formation)
//      ?strand=arch (a strand shape, landed after the first section starts: arch, valley, ramp, stairs, helix-sine)
//
// v1 (2026-10-25): the phrases (phrases.js) sit between the show and the programmer: a section may name one, pads 3, 4
// and 7 (keys 3, 4, 7) are PHRASE GO, NEXT and STOP, and the HUD shows the phrase's step. Every phrase event lands on the
// beat position it belongs to.
//
// v2 (2026-10-27, kinetics wave A + the orrery): the ring formations (formations.js) between the programmer and the
// renderer. Pad 8 / key 8 MORPH steps the rings to the next formation of the deck (home, orrery, spiral, vortex, crown,
// portal) on the next bar line; pad 9 / key 9 HERO fires the energy beam's discharge up the axis through the core, once
// per eight bars, on the next ONE (through the FlashGate). ?ring=orrery (or spiral, vortex, crown, portal) starts in one.
// The camera sees a landing formation (the glide, then the cut on the landing bar line to its hero view) and the live
// rings (its guard); the phrase layer's presets re-aim on the live rings; the ring lasers ride ring 0.
//
// KICK v2 (2026-10-27, kick.js): two kick pads, pad 1 / key 1 KICK WHITE and pad 5 / key 5 KICK COLOUR (Shift: velocity
// 1). Each press deals its own AREA of the set's deck (round 2: the one the camera shows most of; its light and colour
// override the look's from the press on); a held pad keeps it lit (the kick is a gate) at a live level that padLevel()
// moves while it is held. What a kick pad does is its kind in the set's kick.kinds. The page-level pad door for touch and velocity sources: the window events
// "arsenal:pad" {pad, vel, on} and "arsenal:padlevel" {pad, vel}; window.__padDoor = 1 says the page listens.
//
// FLASH PROTECTION, THE VIEWER'S CHOICE (2026-10-28, lib/flash-consent.js). Daniel: "have it be a toggle, as it should
// be, you get a siezure warning and its up to you what you do with it, default is on". On a first visit the page shows
// the photosensitivity warning with one "Flash protection" box (checked) and Start; the show starts on Start; the choice
// is remembered in this browser; the HUD has a quiet "Flash protection" checkbox; ?flash=on|off decides from the URL
// (tests, kiosks); automation (every receipt) gets protection on and no screen. ON: the final-frame limiter (flash.js v2,
// the smooth fields) judges every frame exactly as before. OFF: the page asks no limiter, the meter does not run and the
// apply pass is the identity -- the frame reaches the canvas as drawn -- and the kick's flash governor, which exists only
// so the limiter never has to act, sees a full budget.
//
// PALETTES (2026-10-28, ../palettes.js): one active palette of thirty drives every colour (the roles, the kicks, the wheel
// plan, the splits and pins, the strand's gradient and tempo, the lasers, the air). ?palette=source-violet picks one at
// load (?theme= is read the same way; a set theme that is not a palette still loads as before); the show's own is
// show.palette. Live: key P steps to the next palette, Shift+P the previous one, and the set's pad map can name
// "palette-next" and "palette-prev" (the phone bar's PALETTE pad, a KeyLab pad); the change lands on the next 16-bar line --
// a neighbour crossfades over 4 bars, anything else cuts on the line through a one-beat dip. Every press before the
// landing steps the palette that will land. The page says what is showing and what is coming with the window event
// "arsenal:palette" {id, name, next, nextName, at} (only when it changes) and keeps the latest in window.__palette.

import { parseEvent, EngineLink } from "../vj-core.js";
import { loadLibrary } from "../glsl/modlib.js";
import { validateScene, expandScene } from "./rig.js";
import { BeatGrid, DemoBeats, beatExtras } from "./grid.js";
import { Programmer } from "./programmer.js";
import { Strand } from "./kinetics.js";
import { LaserEngine } from "./lasers.js";
import { Lasers3D } from "./lasers3d.js";
import { Atmosphere } from "./atmos.js";
import { Director, cameraModel, formationPoseSets } from "./camera.js";
import { RingFormations, validateRingFormations } from "./formations.js";
import { Show, speedFromFader } from "./show.js";
import { FrameLimiter, LIMIT } from "./flash.js";
import { hexToLinear, extraHeadsFrom } from "./lasers.js";
import { PhraseRunner, playPhraseEvents, validatePhrases } from "./phrases.js";
import { validateKick } from "./kick.js";
import { flashProtection, protectionCheckbox } from "../lib/flash-consent.js";
import { fetchPalettes, stageTheme, stepPalette, needsDip, landingPos, tableOf } from "../palettes.js";

const QS = new URLSearchParams(location.search);
const DEMO = QS.get("demo") === "1";
const ENGINE_URL = (() => {
  const asked = QS.get("engine");
  if (asked === "off") return null;
  if (asked && /^https?:\/\/[^\s"'<>]+$/i.test(asked)) return asked.replace(/\/+$/, "");
  return DEMO ? null : "http://127.0.0.1:8794";
})();
const SET = /^[a-z0-9][a-z0-9-]{0,40}$/.test(QS.get("set") || "") ? QS.get("set") : "source-v1";
// ?theme= one of the set's themes (else the show's own) and ?phrase= the phrase pad 3 starts (else the set's first): the
// looks wave-1 themes and phrases (Dreaming City, Single Thread, Pillars...) are reached by name
const asName = (v) => (/^[a-z0-9][a-z0-9-]{0,40}$/.test(v || "") ? v : null);
const THEME_ASKED = asName(QS.get("theme")), PHRASE_ASKED = asName(QS.get("phrase")), RING_ASKED = asName(QS.get("ring"));
const PALETTE_ASKED = asName(QS.get("palette")) || THEME_ASKED;
const STRAND_ASKED = asName(QS.get("strand"));
const QUALITY = ["high", "receipt", "low"].includes(QS.get("quality")) ? QS.get("quality") : "high";
const FIXED_W = Number(QS.get("w")) || 0, FIXED_H = Number(QS.get("h")) || 0;
// The bloom mix the finish pass uses. render.js reads it off the frame state as `fs.bloomMix ?? 0.05` and then divides
// by six, and no producer ever set it -- so every frame ran bloom at 0.05 / 6 = 0.83 %, present and too faint to see.
// That is what "the air does not glow" looks like in the numbers: the wing-light measure on the receipt frames came out
// at or below a plain Gaussian beam's, i.e. no spill beyond the beam's own profile. ?bloommix= overrides it, so an A/B
// is a URL and not an edit. (0.6 -> an effective mix of 0.10.)
const BLOOM_MIX = (QS.get("bloommix") !== null && Number.isFinite(Number(QS.get("bloommix")))) ? Number(QS.get("bloommix")) : 0.05;
const DPR_CAP = 2;
const $ = (id) => document.getElementById(id);

const errors = [];
function banner(msg) { const b = $("banner"); b.textContent = msg; b.hidden = false; }
function recordError(where, err) {
  const msg = `${where}: ${err && err.message ? err.message : err}`;
  if (errors.length < 50) errors.push(msg);
  console.error(msg);
}
window.addEventListener("error", (e) => recordError("page", e.error || e.message));
window.addEventListener("unhandledrejection", (e) => recordError("promise", e.reason));

const api = window.__stage = { ready: false, errors, version: "stage-v1" };
// the viewer's flash protection (the warning on a first visit: the show waits for Start)
const flash = flashProtection({ page: "stage" });

async function boot() {
  // the scene
  const res = await fetch(new URL(`./sets/${SET}.json`, import.meta.url));
  if (!res.ok) throw new Error(`the scene ${SET} did not load (HTTP ${res.status})`);
  const scene = await res.json();
  const problems = validateScene(scene);
  if (problems.length) throw new Error(`the scene ${SET} is not valid:\n${problems.join("\n")}`);
  const rig = expandScene(scene);
  const phraseProblems = validatePhrases(rig);
  if (phraseProblems.length) throw new Error(`the scene ${SET}'s phrases are not valid:\n${phraseProblems.join("\n")}`);
  const ringProblems = validateRingFormations(rig);
  if (ringProblems.length) throw new Error(`the scene ${SET}'s ring formations are not valid:\n${ringProblems.join("\n")}`);
  const kickProblems = validateKick(rig);
  if (kickProblems.length) throw new Error(`the scene ${SET}'s kick block is not valid:\n${kickProblems.join("\n")}`);
  // the palettes (checked against this rig's beam wheel; a palette that fails is refused with its reasons and the rest load;
  // without the library the set's own themes still run)
  let palettes = null;
  try {
    const beam = Object.values(scene.types || {}).find((t) => t.attrs && t.attrs.Color1 && t.attrs.Color1.colours);
    palettes = await fetchPalettes(new URL("../palettes.json", import.meta.url), fetch, { wheel: beam ? beam.attrs.Color1.colours : null });
    for (const r of palettes.refused) recordError("palette", `${r.id} refused: ${r.problems.join("; ")}`);
  } catch (e) { recordError("palettes", e); }
  // the house GLSL library and the renderer (three.js from the pinned CDN build, as the piano loads it)
  const lib = await loadLibrary(new URL("../glsl/index.json", import.meta.url).href);
  let renderMod;
  try { renderMod = await import("./render.js"); }
  catch (e) { throw new Error(`three.js r186 did not load from cdn.jsdelivr.net (${e.message}). Check the network, then reload.`); }
  const canvas = $("gl");
  const R = new renderMod.StageRenderer(canvas, rig, lib, { quality: QUALITY });
  return { scene, rig, lib, R, renderMod, palettes };
}

function start({ rig, R, renderMod, palettes }) {
  // the finish's look (render.js LOOKS): ?look=hdr|punch|velvet|classic, then this browser's last choice, then HDR Night;
  // automation (every house lane) stays on classic, the finish its numbers were measured on. L cycles it.
  const LOOKS = renderMod.LOOKS, LOOK_ORDER = renderMod.LOOK_ORDER;
  const lookStore = (v) => { try { if (v === undefined) return localStorage.getItem("arsenal.stage.look"); localStorage.setItem("arsenal.stage.look", v); } catch { return null; } return null; };
  const qLook = QS.get("look");
  R.look = LOOKS[qLook] ? qLook : navigator.webdriver ? "classic" : (LOOKS[lookStore()] ? lookStore() : "hdr");
  const show0 = rig.show;
  // the palette asked for (or a set theme by that name that is not a palette), else the show's palette, else its theme
  const palAsked = palettes && PALETTE_ASKED && palettes.byId[PALETTE_ASKED] ? PALETTE_ASKED : null;
  const legacyAsked = !palAsked && THEME_ASKED && rig.themes[THEME_ASKED] ? THEME_ASKED : null;
  const palId = palAsked || (!legacyAsked && palettes && palettes.ids.length ? (palettes.byId[show0.palette] ? show0.palette : palettes.ids[0]) : null);
  const themeName = legacyAsked || show0.theme || Object.keys(rig.themes)[0];
  let theme = palId ? stageTheme(palettes.byId[palId]) : { name: themeName, ...rig.themes[themeName] };
  const demoBpm = (show0.demo && show0.demo.bpm) || 150;
  const now0 = performance.now();
  const grid = new BeatGrid({ bpm: demoBpm, t0: now0 });
  const programmer = new Programmer(rig, { theme });
  const rungs = rig.elements.filter((e) => e.id === "rung");
  const rungEl = rungs[0];
  const strand = new Strand({ rungs: rungs.length, pickupX: Math.abs(rungEl.pickups[0][0]), mode: rig.mode,
                              home: { y: rungEl.home.y, roll: 0 }, limits: { y: rungEl.limits.y, roll: rungEl.limits.roll } });
  const lasers = new LaserEngine({ seed: rig.seed, clock: grid.clock(), colours: theme.laser, heads: extraHeadsFrom(rig.projectors) });
  const lasers3d = new Lasers3D(rig.projectors, rig.venue, { heads: lasers.heads });
  const runner = Object.keys(rig.phrases || {}).length ? new PhraseRunner(rig) : null;
  const firstPhrase = runner ? (PHRASE_ASKED && rig.phrases[PHRASE_ASKED] ? PHRASE_ASKED : Object.keys(rig.phrases)[0]) : null;
  const atmos = new Atmosphere({ hazers: rig.hazers, tau: rig.atmos.tau_s ?? 30, preHaze: rig.atmos.pre_haze ?? 0.12,
                                 wind: rig.atmos.wind || [0.25, 0, -0.1], noiseAmp: rig.atmos.noise_amp ?? 0.6 });
  // v2: the ring formations (their light is a programmer layer over the look and the phrases)
  const rings = new RingFormations(rig);
  rings.roles = programmer.roleRGB;
  programmer.setLayer(rings);
  if (RING_ASKED && rings.def(RING_ASKED)) rings.set(RING_ASKED, 0, demoBpm);
  // v2: the director knows the strand (it never deals a shot within 1.5 m of a rung) and each formation's hero views; a
  // ring formation's shots are judged against the rings it sweeps and against every strand formation of the set, and
  // a formation with a core (the orrery) against the PA hangs and trusses that would hide it (formations.js sight)
  const camModel = cameraModel(rig);
  const ringKeys = rings.formations.filter((k) => k !== "home");
  const strandSets = [].concat(...Object.values(rig.formations).map((f) => formationPoseSets(f, camModel.z.length) || []));
  const director = new Director(rig.cameras.shots, rig.cameras.sequences,
                                { model: camModel, formations: { ...rig.formations, ...Object.fromEntries(ringKeys.map((k) => [k, rings.def(k)])) },
                                  views: rig.cameras.formation_views, safe: rig.cameras.safe,
                                  posesOf: (key, def) => (ringKeys.includes(key) ? strandSets : formationPoseSets(def, camModel.z.length)),
                                  ringsOf: (key) => (ringKeys.includes(key) ? rings.annuliSets(key) : null),
                                  sightOf: (key) => (ringKeys.includes(key) ? rings.sight(key) : null) });
  director.start(Object.keys(rig.cameras.sequences)[0], 0);      // until the first section starts its own sequence
  // what the camera reads of the rig each frame: the formation key (a change with a landing gets the glide and the hero
  // view), its landing bar line, the live rung poses. A ring formation that lands elsewhere sets formation and posLand too,
  // and rings (live annuli, camera.js ringAnnulus) while the rings are off their home pose, so the guard sees them.
  const camScene = { formation: "", def: null, posLand: null, poses: strand.poses, rings: null, dt: 0 };
  const show = new Show(rig, { demo: DEMO || !ENGINE_URL });
  const limiter = new FrameLimiter();
  const link = new EngineLink();
  const demoBeats = show.demo ? new DemoBeats({ bpm: demoBpm, startMs: now0 + 300 }) : null;
  // the air: the active palette's deep colour and air tint (programmer.ambient, airTint: they crossfade with the palette)
  // PALETTES: the lasers' red fallback is the palette's white, and a fan of its first two colours is a gradient per beam
  const laserOpts = (th) => { const pl = th.palette, g = pl && pl.gradients.find((x) => x.name === "lasers");
                              return { white: hexToLinear(th.W || "#ffffff"), fanRamp: g ? tableOf(g) : null }; };
  lasers.setColours(theme.laser, laserOpts(theme));
  lasers3d.safeWhite = hexToLinear(theme.W || "#ffffff");
  // the live palette: what shows, what is queued and the 16-bar line it lands on
  const pal = { id: palId, queued: null, at: null, dip: false, landings: [] };
  function announcePalette() {
    const cur = pal.id && palettes.byId[pal.id], nxt = pal.queued && palettes.byId[pal.queued];
    const d = { id: pal.id, name: cur ? cur.name : theme.name, next: pal.queued, nextName: nxt ? nxt.name : null, at: pal.at,
                ladder: cur ? cur.kick.ladder.slice() : null, nextLadder: nxt ? nxt.kick.ladder.slice() : null };
    window.__palette = d;
    window.dispatchEvent(new CustomEvent("arsenal:palette", { detail: { ...d } }));
  }
  // step to the next (+1) or previous (-1) palette (or to id), landing on the next 16-bar line (a press before the landing
  // steps the queued one); now: true lands it on this frame, no transition (the receipts' door)
  function stepPal(delta, tEval, { id = null, now = false } = {}) {
    if (!palettes || !palettes.ids.length) return null;
    const from = pal.queued || pal.id || palettes.ids[0];
    const want = id && palettes.byId[id] ? id : stepPalette(palettes, from, delta);
    const pos = grid.posAt(tEval);
    if (now) {
      pal.id = want; pal.queued = null; pal.at = null;
      theme = stageTheme(palettes.byId[want]);
      programmer.palX = null; programmer.setTheme(theme);
      lasers.setColours(theme.laser, laserOpts(theme)); lasers3d.safeWhite = hexToLinear(theme.W || "#ffffff");
      $("hud-set").textContent = hudSetText();
      announcePalette();
      return { id: want, at: pos, dip: false };
    }
    const at = landingPos(pos, grid.barAnchor || 0, 16);
    const cur = palettes.byId[pal.id], nxt = palettes.byId[want];
    const dip = needsDip(cur, nxt, palettes.wheel);
    pal.queued = want; pal.at = at; pal.dip = dip;
    programmer.beginPalette(stageTheme(nxt), at, { beats: 16, dip });
    announcePalette();
    return { id: want, at, dip };
  }
  // the faders: F1 strand, F4 lasers, F5 haze, F6 speed, F9 grand master
  const faders = { ...{ strand: 1, lasers: 1, haze: 0.55, speed: 0.5, grand: 1 }, ...(show0.fader_defaults || {}) };
  const faderMap = show0.faders || {};
  const padMap = show0.pads || {};
  let sectionSpeed = 1, energy = 0.6, lastFrame = null, manualShot = null;
  // the room's ambient (the veil and the fill light) x the phrase step's own (a laser step darkens the room)
  const ambientNow = { scale: 1, target: 1, lastPos: null };
  const kicks = [];
  const state = { section: "", look: "", formation: "", shot: "", fps: 0, frameMs: 0, phraseSteps: [] };

  function applyFaders(tEval) {
    programmer.masters.grand = faders.grand;
    programmer.masters.strand = faders.strand;
    atmos.setTarget(faders.haze);
    programmer.setSpeed(sectionSpeed * speedFromFader(faders.speed) / speedFromFader(0.5), grid, tEval);
  }
  function enterSection(ev) {
    const sec = (show0.sections || {})[ev.name];
    if (!sec) return;
    state.section = ev.name;
    programmer.setLook(sec.look, ev.pos);
    state.look = sec.look;
    // ?strand= a shape: it replaces the sections' strand formations (the rings and the looks play on as written)
    const f = STRAND_ASKED && rig.strandShapes[STRAND_ASKED] ? null : rig.formations[sec.formation];
    if (!f && STRAND_ASKED && rig.strandShapes[STRAND_ASKED] && state.formation !== STRAND_ASKED) {
      // landed from the strand's home on the S-curve (the machine glide is the point of asking for one)
      const sh = rig.strandShapes[STRAND_ASKED];
      strand.land(sh.name, sh.params, grid, performance.now(), { land: "bar" });
      state.formation = STRAND_ASKED;
    }
    if (f) {
      const tNow = performance.now();
      if (!state.formation) strand.set(f.name, f.params, grid.bpm);
      else if (state.formation !== sec.formation) strand.land(f.name, f.params, grid, tNow, { land: "bar" });
      state.formation = sec.formation;
    }
    if (sec.lasers) lasers.setLook(sec.lasers.look, sec.lasers.level ?? 1, sec.lasers.reach ?? 1);
    lasers.setSection(ev.name);
    // a phrase started from the pad keeps the camera through a section change (the section's own phrase replans it)
    const padPhraseCamera = runner && runner.cur && runner.cur.camera && runner.cur.source !== "show";
    if (sec.camera && !manualShot && !padPhraseCamera) director.start(sec.camera, ev.pos);
    // the section's phrase starts on its ONE; a phrase the show started ends with its section (a pad's phrase plays on)
    if (runner) {
      if (sec.phrase && rig.phrases[sec.phrase.name]) {
        runner.start(sec.phrase.name, ev.pos, { repeats: sec.phrase.repeats ?? Infinity, camera: sec.phrase.camera !== false, section: ev.name });
      } else if ((runner.cur && runner.cur.source === "show") || (runner.pending && runner.pending.source === "show")) runner.stopAtPos(ev.pos);
    }
  }
  // the pre-roll: heads that are dark move in black to where a coming phrase needs them
  function prepare(name) {
    if (!runner || runner.cur || !rig.phrases[name]) return;
    programmer.setOverlay(runner.prepareLines(name), grid.posAt(performance.now() + grid.presentLagMs), { positionsOnly: true });
  }
  function phraseEnded(e) {
    const sec = (show0.sections || {})[state.section];
    if (sec && sec.camera && !manualShot) director.start(sec.camera, e.pos);
  }
  // KICK v2: the kicks are gates (held until the pad lets go) and take a live level while held (padLevel). A pad whose
  // action is one of the set's kick KINDS (kick.kinds: kick-white, kick-colour, ...) is a kick; "kick" is the first kind.
  const isKick = (action) => !!(action && programmer.kick.kindOf(action));
  // KICK round 2: the dealer only deals an area the camera sees, and prefers the one it shows most of: {share: of the area's
  // sample points (its fixtures, its LEDs, a point 10 m along each head's beam) inside the current shot's view (the roll left
  // out), cover: the share of a 16 x 8 grid over the frame those points fall in (a head's points also light the cells round
  // them: a beam in haze is wider than its lens)}
  const GX = 16, GY = 8, viewGrid = new Uint8Array(GX * GY);
  programmer.kick.view = (card) => {
    const S = card.samples;
    if (!S || !S.length) return { share: 1, cover: 1 };
    const P = director.pose, aspect = R.w > 0 && R.h > 0 ? R.w / R.h : 16 / 9;
    const f = [P.look[0] - P.pos[0], P.look[1] - P.pos[1], P.look[2] - P.pos[2]], fl = Math.hypot(f[0], f[1], f[2]) || 1;
    f[0] /= fl; f[1] /= fl; f[2] /= fl;
    let r = [-f[2], 0, f[0]], rl = Math.hypot(r[0], r[2]);                 // f x up(0, 1, 0)
    if (rl < 1e-6) { r = [1, 0, 0]; rl = 1; }
    r = [r[0] / rl, 0, r[2] / rl];
    const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
    const tanH = Math.tan(((P.hfov || 50) * Math.PI) / 360), tanV = tanH / aspect;
    let inView = 0;
    const n = S.length / 3, spread = card.heads.length ? 1 : 0;
    viewGrid.fill(0);
    for (let k = 0; k < n; k++) {
      const dx = S[k * 3] - P.pos[0], dy = S[k * 3 + 1] - P.pos[1], dz = S[k * 3 + 2] - P.pos[2];
      const z = dx * f[0] + dy * f[1] + dz * f[2];
      if (z < 0.5) continue;
      const x = (dx * r[0] + dy * r[1] + dz * r[2]) / z, y = (dx * u[0] + dy * u[1] + dz * u[2]) / z;
      if (Math.abs(x) > tanH || Math.abs(y) > tanV) continue;
      inView++;
      const gx = Math.min(GX - 1, Math.floor(((x / tanH + 1) / 2) * GX)), gy = Math.min(GY - 1, Math.floor(((y / tanV + 1) / 2) * GY));
      for (let ox = -spread; ox <= spread; ox++) for (let oy = -spread; oy <= spread; oy++) {
        const cx = gx + ox, cy = gy + oy;
        if (cx >= 0 && cx < GX && cy >= 0 && cy < GY) viewGrid[cy * GX + cx] = 1;
      }
    }
    let cells = 0;
    for (let i = 0; i < viewGrid.length; i++) cells += viewGrid[i];
    return { share: inView / n, cover: cells / viewGrid.length };
  };
  function pad(n, vel, on, tEval) {
    const action = padMap[String(n)];
    const pos = grid.posAt(tEval);
    if (!action) return;
    if (isKick(action)) {
      if (on) {
        const k = programmer.pad(action, vel, pos, { hold: true });
        if (kicks.length >= 256) kicks.shift();
        kicks.push({ pressPos: pos, onset: Math.round(pos), kind: k ? k.kind : action, row: k ? k.card.name : null, band: k ? k.band : null });
      } else programmer.padRelease(action, pos);
    }
    else if (action === "flyout" && on) programmer.pad("flyout", vel, pos);
    else if (action === "lasers") { if (on) lasers.hit(tEval, vel); else lasers.release(tEval); }
    else if (action === "drop" && on) { show.dropNow(grid, pos); const d = (show0.sections || {}).drop; if (d && d.phrase) prepare(d.phrase.name); }
    else if (runner && action === "phrase-go" && on) { prepare(firstPhrase); runner.go(firstPhrase, grid, pos, { section: state.section || "any" }); }
    else if (runner && action === "phrase-next" && on) runner.next(grid, pos);
    else if (runner && action === "phrase-stop" && on) runner.stop(grid, pos);
    else if (action === "palette-next" && on) stepPal(1, tEval);
    else if (action === "palette-prev" && on) stepPal(-1, tEval);
    else if (action === "morph" && on) rings.morph(grid, tEval);
    else if (action === "hero" && on) rings.hero(grid, tEval);
  }
  // a held pad's live level (0..1: the phone pad's finger height; later the KeyLab's aftertouch): the held kick's brightness
  function padLevel(n, vel) {
    const action = padMap[String(n)];
    if (isKick(action) && Number.isFinite(vel)) programmer.padLevel(action, Math.max(0, Math.min(1, vel)));
  }
  function handle(obj, nowMs) {
    const ev = parseEvent(obj);
    if (!ev) return;
    link.event(ev);
    const tEval = nowMs + grid.presentLagMs;
    if (ev.t === "beat") grid.beat({ ...ev, ...beatExtras(obj) }, nowMs);
    else if (ev.t === "pad") pad(ev.pad, ev.vel, ev.on, tEval);
    else if (ev.t === "energy") energy = ev.level;
    else if (ev.t === "ctl") {
      const target = faderMap[ev.id];
      if (target && ev.kind === "abs") { faders[target] = ev.value; applyFaders(tEval); syncFaderUI(); }
    }
  }
  // the engine link: Server-Sent Events, reconnecting with a backoff
  let es = null, backoff = 1000;
  function connect() {
    if (!ENGINE_URL) return;
    try { es = new EventSource(`${ENGINE_URL}/api/events`); } catch (e) { recordError("engine", e); return; }
    es.onopen = () => { link.connected(); backoff = 1000; };
    es.onerror = () => { es.close(); link.disconnected(); setTimeout(connect, backoff); backoff = Math.min(10000, backoff * 1.6); };
    es.onmessage = (m) => { let o; try { o = JSON.parse(m.data); } catch { return; } handle(o, performance.now()); };
  }
  connect();

  // ------------------------------------------------------------------------------------------------ the frame --
  const fwd = [0, 0, -1];
  let last = null;
  const timing = { list: [], n: 0 };
  function frame() {
    requestAnimationFrame(frame);
    const now = performance.now();
    const realStart = globalThis.__realNow ? globalThis.__realNow() : now;
    const dt = last === null ? 1 / 60 : Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    try {
      if (demoBeats) demoBeats.tick(now, (o) => handle(o, now));
      const tEval = now + grid.presentLagMs;
      const pos = grid.posAt(tEval);
      if (grid.locked || !show.demo) {
        for (const ev of show.update(grid, pos)) {
          if (ev.type === "section") enterSection(ev);
          else if (ev.type === "pad") pad(ev.pad, ev.vel, ev.on, tEval);
          else if (ev.type === "speed") { sectionSpeed = ev.s; applyFaders(tEval); }
          else if (ev.type === "prepare") prepare(ev.phrase);
        }
      }
      if (runner) {
        const pev = runner.update(pos);
        for (const e of pev) if (e.type === "error") recordError("phrase", e.message);
        const entered = playPhraseEvents(pev, { programmer, lasers, director, onEnd: phraseEnded, manualCamera: () => !!manualShot });
        for (const e of entered) { if (state.phraseSteps.length >= 512) state.phraseSteps.shift(); state.phraseSteps.push({ id: e.id, variant: e.variant, repeat: e.repeat, start: e.start, at: pos }); }
        for (const e of pev) { if (e.type === "step") ambientNow.target = e.step.ambient ?? 1; else if (e.type === "end" || e.type === "error") ambientNow.target = 1; }
      }
      {
        const dp = ambientNow.lastPos === null ? 0 : Math.max(0, pos - ambientNow.lastPos);
        ambientNow.lastPos = pos;
        const k = Math.min(1, dp / 0.5);                        // half a beat to the new level
        ambientNow.scale += (ambientNow.target - ambientNow.scale) * k;
      }
      // KICK round 2's flash governor: how many more counted transitions the final limiter's most loaded window can take
      // now (read from its counters, never changing them: flash.js decides on its own, as before)
      // (with flash protection off no limiter acts, so the governor holds nothing back)
      {
        let room = LIMIT.N_MAX;
        if (flash.on) for (const pair of limiter.trackers) for (const tr of pair) room = Math.min(room, LIMIT.N_MAX - tr.count(now / 1000));
        programmer.kick.headroom = room;
      }
      // the rings first (the programmer's formation layer, the camera and the lasers read their live pose)
      rings.update(grid, tEval, dt, programmer.flashGate);
      programmer.setLiveElements(rings.live ? rings.emOf : null);
      programmer.tick(grid, tEval, dt);
      // the palette's landing: the lasers and the HUD take the new palette at its swap (the dip's bottom, or a crossfade's start)
      for (const e of programmer.takePaletteEvents()) {
        if (e.type !== "swap") { if (e.type === "landed" && pal.landings.length < 64) pal.landings.push({ id: e.id, pos: e.pos }); continue; }
        theme = programmer.theme;
        lasers.setColours(theme.laser, laserOpts(theme)); lasers3d.safeWhite = hexToLinear(theme.W || "#ffffff");
        if (pal.queued === e.id) { pal.id = e.id; pal.queued = null; pal.at = null; }
        $("hud-set").textContent = hudSetText();
        announcePalette();
      }
      strand.update(grid, tEval, dt);
      // the camera follows the ring formation while one stands (its landing, its hero view, the live rings for the guard)
      const ringKey = rings.key !== "home" ? rings.key : null;
      camScene.formation = ringKey || state.formation; camScene.def = strand.formation;
      camScene.posLand = ringKey && rings.move ? rings.move.posLand : strand.move ? strand.move.posLand : null;
      camScene.rings = rings.liveAnnuli(); camScene.dt = dt;
      const pose = director.update(pos, camScene);
      const pl = Math.hypot(pose.look[0] - pose.pos[0], pose.look[1] - pose.pos[1], pose.look[2] - pose.pos[2]) || 1;
      fwd[0] = (pose.look[0] - pose.pos[0]) / pl; fwd[1] = (pose.look[1] - pose.pos[1]) / pl; fwd[2] = (pose.look[2] - pose.pos[2]) / pl;
      if (rings.live) rings.updateMounts(lasers3d, lasers.heads);
      const l2 = lasers.frame(tEval);
      rings.drawLasers(lasers, pos);
      const rf = rings.frame(pose.pos);
      lasers3d.hitOpts = rf.hitOpts;
      const l3 = lasers3d.map(l2, { reachScale: 1, master: faders.lasers, camera: { pos: pose.pos, fwd, near: 0.1 } });
      const medium = atmos.update(dt);
      const W = FIXED_W || Math.round(Math.min(window.devicePixelRatio || 1, DPR_CAP) * canvasCss().w);
      const Hh = FIXED_H || Math.round(Math.min(window.devicePixelRatio || 1, DPR_CAP) * canvasCss().h);
      R.resize(W, Hh);
      const shot = director.shots[pose.shot];
      const ambient = programmer.ambient, airTint = programmer.airTint;
      const amb = ambientNow.scale === 1 ? ambient : ambient.map((c) => c * ambientNow.scale);
      const fs = { camera: { ...pose, orbitCentre: shot && shot.orbit ? shot.orbit.centre : null }, poses: strand.poses, heads: programmer.heads,
                   pixels: programmer.pixels, lasers: l3, medium, ambient: amb, airTint, ambientScale: ambientNow.scale, beatPhase: pos - Math.floor(pos), energy,
                   bloomMix: BLOOM_MIX, rings: rf };
      // api.skipRender: the receipts fast-forward the show's logic without drawing (the limiter then judges nothing)
      // flash protection off: no limiter asked (no meter, the identity: the frame as drawn)
      const info = api.skipRender ? state.info : R.render(fs, flash.on ? (cells, t) => limiter.step(cells, t, dt) : null, now / 1000);
      state.shot = pose.shot; state.u = pose.u; state.pos = pos; state.info = info; state.l3 = l3; state.l2 = l2;
      const ft = (globalThis.__realNow ? globalThis.__realNow() - realStart : performance.now() - now);
      timing.n++; if (timing.list.length >= 240) timing.list.shift(); timing.list.push(ft);
      lastFrame = now;
    } catch (e) {
      recordError("frame", e);
      if (errors.length === 1) banner(`The stage stopped: ${e.message}`);
    }
    hud(now);
  }

  // --------------------------------------------------------------------------------------------------- the HUD --
  let hudAt = 0;
  const hudEl = $("hud");
  if (QS.get("hud") === "0") hudEl.classList.add("hidden");
  function hudSetText() {
    const q = pal.queued && palettes ? palettes.byId[pal.queued] : null;
    return `${rig.name} · ${theme.name}${q ? ` → ${q.name} (bar ${Math.round((pal.at - (grid.barAnchor || 0)) / 4)})` : ""} · ${show.demo ? "demo show" : "engine"} · ${rig.mode} motion`;
  }
  $("hud-set").textContent = hudSetText();
  function hud(now) {
    if (now - hudAt < 100 || hudEl.classList.contains("hidden")) return;
    hudAt = now;
    const tEval = now + grid.presentLagMs;
    const b = grid.barAt(tEval);
    $("hud-beatdot").classList.toggle("on", grid.phaseAt(tEval) < 0.2);
    const eng = !ENGINE_URL ? "demo clock" : link.open ? (link.hello ? `engine ${link.hello.src || "on"}` : "engine connected") : "engine offline (free-running)";
    $("hud-clock").textContent = `${grid.bpm.toFixed(1)} BPM · bar ${b.bar} beat ${b.beat} · ${eng}`;
    const kl = programmer.kick.list.filter((k) => !k.dead).map((k) => `${k.kind.replace(/^kick-/, "")} ${k.card.name} ${Math.round(k.level * 100)} %${k.strobing ? " strobe" : ""}${k.held ? "" : " (fading)"}`);
    $("hud-section").textContent = `${state.section || "-"} (look ${state.look || "-"}, speed x${programmer.speed.toFixed(2)})${kl.length ? ` · kick: ${kl.join(" · ")}` : ""}`;
    const ph = $("hud-phrase");
    if (ph) {
      const st = runner ? runner.status() : null;
      ph.textContent = !st ? "no phrases in this set" : st.state === "running"
        ? `${st.name} · ${st.step} ${st.stepName} (${st.index + 1}/${st.steps}) · ${st.variant} · repeat ${st.repeat + 1} · ${Math.max(0, st.end - grid.posAt(tEval)).toFixed(1)} beats left`
        : st.state === "armed" ? `armed: starts on the next bar line` : "idle (pad 3 / key 3: go)";
    }
    const forShot = director.pose.forShot ? ` (for ${director.pose.forShot})` : "";
    $("hud-shot").textContent = `${state.shot || "-"}${forShot} ${state.u !== undefined ? `${Math.round(Math.min(1, state.u) * 100)} %` : ""}`;
    const p0 = strand.poses[0], p11 = strand.poses[strand.poses.length - 1];
    const rk = rings.def(rings.key), rpos = grid.posAt(tEval), charge = rings.heroCharge(rpos);
    const ringTxt = `rings: ${rk ? rk.name : rings.key}${rk && rk.dream ? " (dream)" : ""}${rings.move ? ` · landing bar ${Math.round((rings.move.posLand - grid.barAnchor) / 4)}` : ""} · hero ${charge >= 1 ? "charged" : `${Math.round(charge * 100)} %`} (pads 8 / 9)`;
    $("hud-strand").textContent = `${strand.formation.name} · rung 1 ${p0.y.toFixed(2)} m ${p0.roll.toFixed(0)}° · rung ${strand.n} ${p11.y.toFixed(2)} m${strand.move ? " · landing" : ""} · ${ringTxt}`;
    $("hud-lasers").textContent = `${state.l2 ? state.l2.look : "-"} · ${state.l3 ? state.l3.n : 0} beams · ${state.l2 && state.l2.hits ? `${state.l2.hits} hits` : "no hits"}`;
    $("hud-haze").textContent = `${Math.round(atmos.H * 100)} % → ${Math.round(atmos.target * 100)} % · σ ${atmos.uniform.sigma0.toFixed(4)} /m · ${atmos.hazers.length} hazers`;
    const st = limiter.stats();
    $("hud-flash").innerHTML = !flash.on ? "protection off (frames as drawn)"
      : st.interventions ? `<span class="warn">limiter acted on ${st.interventions} frames</span>` : `<span class="ok">no limiter interventions</span> · ${st.frames} frames judged`;
    const avg = timing.list.length ? timing.list.reduce((s, x) => s + x, 0) / timing.list.length : 0;
    $("hud-render").textContent = `${(LOOKS[R.look] || LOOKS.classic).name} (L) · ${R.w}x${R.h} · ${avg.toFixed(1)} ms CPU+GPU · ${state.info ? `${state.info.beams} beams, ${state.info.emitters} emitters, ${state.info.drawCalls} draws` : ""}`;
  }
  // the fader strip (also the KeyLab's F1, F4, F5, F6, F9 through the engine)
  const FADERS = [["strand", "F1 strand"], ["lasers", "F4 lasers"], ["haze", "F5 haze"], ["speed", "F6 speed"], ["grand", "F9 master"]];
  const fwrap = $("faders");
  for (const [id, label] of FADERS) {
    const d = document.createElement("label"); d.className = "fader";
    const inp = document.createElement("input"); inp.type = "range"; inp.min = "0"; inp.max = "1"; inp.step = "0.01"; inp.value = String(faders[id]);
    inp.id = `fader-${id}`; inp.setAttribute("aria-label", label);
    inp.addEventListener("input", () => { faders[id] = Number(inp.value); applyFaders(performance.now() + grid.presentLagMs); });
    d.append(inp, document.createTextNode(label));
    fwrap.append(d);
  }
  function syncFaderUI() { for (const [id] of FADERS) { const e = $(`fader-${id}`); if (e) e.value = String(faders[id]); } }
  // the quiet flash protection setting, in the HUD's header row (on a phone the pad bar's HUD button shows it, and the
  // header sits above the kick strips, which start at 30 % of the height, and the pad bar at the bottom)
  document.querySelector("#hud .hud-head").append(protectionCheckbox(document, flash, { id: "opt-flash", className: "hud-opt" }));
  // back on: the limiter starts fresh, as at load (what played while it was off is not its history)
  flash.onChange((on) => { if (on) Object.assign(limiter, new FrameLimiter()); });
  // the keyboard: pads 1, 2, 6 and 0 (= pad 10), C next shot (played in motion, looping over its own bars), H HUD,
  // F fullscreen, Esc back to the director
  const KEYPAD = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Digit5: 5, Digit6: 6, Digit7: 7, Digit8: 8, Digit9: 9, Digit0: 10 };
  const held = new Set();
  window.addEventListener("keydown", (e) => {
    if (e.repeat) return;
    const n = KEYPAD[e.code];
    const tEval = performance.now() + grid.presentLagMs;
    if (n) { held.add(e.code); pad(n, e.shiftKey ? 1 : 0.8, true, tEval); e.preventDefault(); return; }
    if (e.code === "KeyP") stepPal(e.shiftKey ? -1 : 1, tEval);
    else if (e.code === "KeyH") hudEl.classList.toggle("hidden");
    else if (e.code === "KeyL") { R.look = LOOK_ORDER[(LOOK_ORDER.indexOf(R.look) + 1) % LOOK_ORDER.length]; lookStore(R.look); }
    else if (e.code === "KeyF") { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {}); }
    else if (e.code === "KeyC") {
      const ids = Object.keys(director.shots);
      const cur = ids.indexOf(manualShot ? manualShot : state.shot);
      manualShot = ids[(cur + 1) % ids.length];
      director.manual = { shot: manualShot, p0: grid.posAt(tEval), beats: (director.shots[manualShot].bars ?? 4) * 4 };
    } else if (e.code === "Escape") { manualShot = null; director.manual = null; }
  });
  window.addEventListener("keyup", (e) => {
    const n = KEYPAD[e.code];
    if (n && held.has(e.code)) { held.delete(e.code); pad(n, 0, false, performance.now() + grid.presentLagMs); }
  });
  // the page-level pad door, for touch and velocity sources (the phone's tall pads: a key carries no velocity):
  //   window.dispatchEvent(new CustomEvent("arsenal:pad", { detail: { pad, vel, on } }))       a press (on) or a let-go
  //   window.dispatchEvent(new CustomEvent("arsenal:padlevel", { detail: { pad, vel } }))      a held pad's live level
  // window.__padDoor = 1 once both listen, so a client can tell the page has them. Keys and MIDI are unchanged.
  const padNo = (d) => { const n = Number(d && d.pad); return Number.isInteger(n) && n >= 1 && n <= 16 ? n : null; };
  const vel01 = (v, dflt) => { const x = Number(v); return Number.isFinite(x) ? Math.max(0, Math.min(1, x)) : dflt; };
  window.addEventListener("arsenal:pad", (e) => {
    const d = e.detail || {}, n = padNo(d);
    if (n === null) return;
    pad(n, vel01(d.vel, 0.8), d.on !== false, performance.now() + grid.presentLagMs);
  });
  window.addEventListener("arsenal:padlevel", (e) => {
    const d = e.detail || {}, n = padNo(d), v = vel01(d.vel, null);
    if (n !== null && v !== null) padLevel(n, v);
  });
  window.__padDoor = 1;
  function canvasCss() { const r = canvas.getBoundingClientRect(); return { w: Math.max(1, r.width), h: Math.max(1, r.height) }; }
  const canvas = $("gl");
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); banner("The WebGL context was lost (the GPU reset). Reload the page."); });

  // ------------------------------------------------------------------------------------------- the receipts' door --
  Object.assign(api, {
    ready: true, rig, grid, programmer, strand, lasers, lasers3d, atmos, director, show, limiter, renderer: R, faders, runner, rings,
    state: () => ({ pos: state.pos, bpm: grid.bpm, bar: grid.barAt(performance.now() + grid.presentLagMs), section: state.section, look: state.look,
                    shot: state.shot, u: state.u, formation: strand.formation.name, info: state.info, counts: rig.counts,
                    limiter: limiter.stats(), grid: { ...grid.stats, ver: grid.ver, locked: grid.locked, barAnchor: grid.barAnchor },
                    haze: { H: atmos.H, target: atmos.target, sigma0: atmos.uniform.sigma0 }, engine: { open: link.open, hello: link.hello },
                    lands: strand.lands.slice(-8), cuts: director.cuts.slice(-16), kicks: kicks.slice(-64), errors: errors.slice(),
                    quality: R.qualityName, renderer: { three: renderMod.QUALITY ? "r186" : "", w: R.w, h: R.h },
                    phrase: runner ? runner.status() : null, phraseSteps: state.phraseSteps.slice(-64),
                    flashGate: { grants: programmer.flashGate.grants.slice(-32), refusals: programmer.flashGate.refusals.slice(-32) },
                    kick: programmer.kick.status(),
                    palette: { id: pal.id, name: theme.name, queued: pal.queued, at: pal.at, dip: pal.dip, landings: pal.landings.slice(-8),
                               library: palettes ? palettes.ids.length : 0, refused: palettes ? palettes.refused.map((r) => r.id) : [] },
                    rings: { key: rings.key, from: rings.from, move: rings.move ? { key: rings.move.key, start: rings.move.start, posLand: rings.move.posLand } : null,
                             poses: rings.rr.poses.map((p) => ({ ...p })), lands: rings.rr.lands.slice(-8), clamped: rings.rr.clamped.slice(-8),
                             hero: { fired: rings.heroState.fired.slice(-8), refused: rings.heroState.refused.slice(-8), armed: rings.heroState.at } } }),
    // a ring formation now (no move), or by its landing move (what MORPH does, to a named formation)
    ringSet: (key) => { rings.set(key, grid.posAt(performance.now() + grid.presentLagMs), grid.bpm); return rings.key; },
    ring: (key) => rings.go(key, grid, performance.now() + grid.presentLagMs),
    setShot: (id, u = 0.5) => { manualShot = id; director.manual = { shot: id, u }; },
    playShot: (id) => { manualShot = id; director.manual = { shot: id, p0: grid.posAt(performance.now() + grid.presentLagMs), beats: (director.shots[id].bars ?? 4) * 4 }; },
    // land one of the set's formations (or a strand shape) on the next bar line it can make; the camera sees the change
    land: (key) => {
      const f = rig.formations[key] || rig.strandShapes[key];
      if (!f) return null;
      const r = strand.land(f.name, f.params, grid, performance.now(), { land: "bar" });
      state.formation = key;
      return r;
    },
    clearShot: () => { manualShot = null; director.manual = null; },
    // PALETTES: the library's ids, and a palette by id (or a step) -- landing on the next 16-bar line, or now
    palettes: () => (palettes ? palettes.ids.slice() : []),
    palette: (id, { now = false } = {}) => stepPal(1, performance.now() + grid.presentLagMs, { id, now }),
    paletteStep: (delta = 1) => stepPal(delta, performance.now() + grid.presentLagMs),
    press: (n, vel = 0.9) => pad(n, vel, true, performance.now() + grid.presentLagMs),
    release: (n) => pad(n, 0, false, performance.now() + grid.presentLagMs),
    level: (n, v) => padLevel(n, v),
    fader: (id, v) => { faders[id] = v; applyFaders(performance.now() + grid.presentLagMs); syncFaderUI(); },
    inject: (obj) => handle(obj, performance.now()),
    features: (f) => Object.assign(R.features, f),
    profile: (on) => { R.profile = !!on; if (on) R.timings = {}; return R.timings; },
    timings: () => R.timings,
    overdraw: () => R.overdraw(),
    debugTargets: () => R.debugTargets(),
    resetLimiter: () => { const L = new FrameLimiter(); Object.assign(limiter, L); },
    // flash protection: its state, a setter for tests (not remembered), and the identity probe -- called in the same task
    // as a drawn frame, it compares the frame as drawn (the finish pass's target) with the canvas, pixel for pixel
    flashProtection: () => ({ on: flash.on, source: flash.source, shown: flash.shown }),
    setFlashProtection: (on) => flash.set(on, { remember: false }),
    identityProbe: () => {
      const w = R.w, h = R.h, a = new Uint8Array(w * h * 4), b = new Uint8Array(w * h * 4), gl = R.renderer.getContext();
      R.renderer.readRenderTargetPixels(R.ldrRT, 0, 0, w, h, a);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, b);
      let diff = 0, max = 0;
      for (let i = 0; i < a.length; i += 4) {
        const d = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
        if (d) { diff++; if (d > max) max = d; }
      }
      return { w, h, pixels: w * h, differing: diff, max_diff: max, protection: flash.on };
    },
    frameTimes: () => timing.list.slice(),
  });
  applyFaders(performance.now() + grid.presentLagMs);
  if (palettes) announcePalette();
  requestAnimationFrame(frame);
}

// the scene loads behind the warning; the show starts once the viewer has made the choice
Promise.all([boot(), flash.ready]).then(([b]) => start(b)).catch((e) => { recordError("boot", e); banner(e.message); api.bootError = e.message; });
