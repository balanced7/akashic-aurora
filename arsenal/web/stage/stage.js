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
//
// v1 (2026-10-25): the phrases (phrases.js) sit between the show and the programmer: a section may name one, pads 3, 4
// and 7 (keys 3, 4, 7) are PHRASE GO, NEXT and STOP, and the HUD shows the phrase's step. Every phrase event lands on the
// beat position it belongs to.

import { parseEvent, EngineLink } from "../vj-core.js";
import { loadLibrary } from "../glsl/modlib.js";
import { validateScene, expandScene } from "./rig.js";
import { BeatGrid, DemoBeats, beatExtras } from "./grid.js";
import { Programmer } from "./programmer.js";
import { Strand } from "./kinetics.js";
import { LaserEngine } from "./lasers.js";
import { Lasers3D } from "./lasers3d.js";
import { Atmosphere } from "./atmos.js";
import { Director } from "./camera.js";
import { Show, speedFromFader } from "./show.js";
import { FrameLimiter } from "./flash.js";
import { hexToLinear, extraHeadsFrom } from "./lasers.js";
import { PhraseRunner, playPhraseEvents, validatePhrases } from "./phrases.js";

const QS = new URLSearchParams(location.search);
const DEMO = QS.get("demo") === "1";
const ENGINE_URL = (() => {
  const asked = QS.get("engine");
  if (asked === "off") return null;
  if (asked && /^https?:\/\/[^\s"'<>]+$/i.test(asked)) return asked.replace(/\/+$/, "");
  return DEMO ? null : "http://127.0.0.1:8794";
})();
const SET = /^[a-z0-9][a-z0-9-]{0,40}$/.test(QS.get("set") || "") ? QS.get("set") : "source-v1";
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
  // the house GLSL library and the renderer (three.js from the pinned CDN build, as the piano loads it)
  const lib = await loadLibrary(new URL("../glsl/index.json", import.meta.url).href);
  let renderMod;
  try { renderMod = await import("./render.js"); }
  catch (e) { throw new Error(`three.js r186 did not load from cdn.jsdelivr.net (${e.message}). Check the network, then reload.`); }
  const canvas = $("gl");
  const R = new renderMod.StageRenderer(canvas, rig, lib, { quality: QUALITY });
  return { scene, rig, lib, R, renderMod };
}

function start({ rig, R, renderMod }) {
  const show0 = rig.show;
  const themeName = show0.theme || Object.keys(rig.themes)[0];
  const theme = { name: themeName, ...rig.themes[themeName] };
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
  const firstPhrase = runner ? Object.keys(rig.phrases)[0] : null;
  const atmos = new Atmosphere({ hazers: rig.hazers, tau: rig.atmos.tau_s ?? 30, preHaze: rig.atmos.pre_haze ?? 0.12,
                                 wind: rig.atmos.wind || [0.25, 0, -0.1], noiseAmp: rig.atmos.noise_amp ?? 0.6 });
  const director = new Director(rig.cameras.shots, rig.cameras.sequences);
  director.start(Object.keys(rig.cameras.sequences)[0], 0);      // until the first section starts its own sequence
  const show = new Show(rig, { demo: DEMO || !ENGINE_URL });
  const limiter = new FrameLimiter();
  const link = new EngineLink();
  const demoBeats = show.demo ? new DemoBeats({ bpm: demoBpm, startMs: now0 + 300 }) : null;
  const ambient = hexToLinear(theme.ambient || "#3a1a8a");
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
    const f = rig.formations[sec.formation];
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
  function pad(n, vel, on, tEval) {
    const action = padMap[String(n)];
    const pos = grid.posAt(tEval);
    if (!action) return;
    if (action === "kick" && on) { programmer.pad("kick", vel, pos); kicks.push({ pressPos: pos, onset: Math.round(pos) }); }
    else if (action === "flyout" && on) programmer.pad("flyout", vel, pos);
    else if (action === "lasers") { if (on) lasers.hit(tEval, vel); else lasers.release(tEval); }
    else if (action === "drop" && on) { show.dropNow(grid, pos); const d = (show0.sections || {}).drop; if (d && d.phrase) prepare(d.phrase.name); }
    else if (runner && action === "phrase-go" && on) { prepare(firstPhrase); runner.go(firstPhrase, grid, pos, { section: state.section || "any" }); }
    else if (runner && action === "phrase-next" && on) runner.next(grid, pos);
    else if (runner && action === "phrase-stop" && on) runner.stop(grid, pos);
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
      programmer.tick(grid, tEval, dt);
      strand.update(grid, tEval, dt);
      const pose = director.update(pos);
      const pl = Math.hypot(pose.look[0] - pose.pos[0], pose.look[1] - pose.pos[1], pose.look[2] - pose.pos[2]) || 1;
      fwd[0] = (pose.look[0] - pose.pos[0]) / pl; fwd[1] = (pose.look[1] - pose.pos[1]) / pl; fwd[2] = (pose.look[2] - pose.pos[2]) / pl;
      const l2 = lasers.frame(tEval);
      const l3 = lasers3d.map(l2, { reachScale: 1, master: faders.lasers, camera: { pos: pose.pos, fwd, near: 0.1 } });
      const medium = atmos.update(dt);
      const W = FIXED_W || Math.round(Math.min(window.devicePixelRatio || 1, DPR_CAP) * canvasCss().w);
      const Hh = FIXED_H || Math.round(Math.min(window.devicePixelRatio || 1, DPR_CAP) * canvasCss().h);
      R.resize(W, Hh);
      const shot = director.shots[pose.shot];
      const amb = ambientNow.scale === 1 ? ambient : ambient.map((c) => c * ambientNow.scale);
      const fs = { camera: { ...pose, orbitCentre: shot && shot.orbit ? shot.orbit.centre : null }, poses: strand.poses, heads: programmer.heads,
                   pixels: programmer.pixels, lasers: l3, medium, ambient: amb, ambientScale: ambientNow.scale, beatPhase: pos - Math.floor(pos), energy,
                   bloomMix: BLOOM_MIX };
      // api.skipRender: the receipts fast-forward the show's logic without drawing (the limiter then judges nothing)
      const info = api.skipRender ? state.info : R.render(fs, (cells, t) => limiter.step(cells, t, dt), now / 1000);
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
  $("hud-set").textContent = `${rig.name} · ${theme.name} · ${show.demo ? "demo show" : "engine"} · ${rig.mode} motion`;
  function hud(now) {
    if (now - hudAt < 100 || hudEl.classList.contains("hidden")) return;
    hudAt = now;
    const tEval = now + grid.presentLagMs;
    const b = grid.barAt(tEval);
    $("hud-beatdot").classList.toggle("on", grid.phaseAt(tEval) < 0.2);
    const eng = !ENGINE_URL ? "demo clock" : link.open ? (link.hello ? `engine ${link.hello.src || "on"}` : "engine connected") : "engine offline (free-running)";
    $("hud-clock").textContent = `${grid.bpm.toFixed(1)} BPM · bar ${b.bar} beat ${b.beat} · ${eng}`;
    $("hud-section").textContent = `${state.section || "-"} (look ${state.look || "-"}, speed x${programmer.speed.toFixed(2)})`;
    const ph = $("hud-phrase");
    if (ph) {
      const st = runner ? runner.status() : null;
      ph.textContent = !st ? "no phrases in this set" : st.state === "running"
        ? `${st.name} · ${st.step} ${st.stepName} (${st.index + 1}/${st.steps}) · ${st.variant} · repeat ${st.repeat + 1} · ${Math.max(0, st.end - grid.posAt(tEval)).toFixed(1)} beats left`
        : st.state === "armed" ? `armed: starts on the next bar line` : "idle (pad 3 / key 3: go)";
    }
    $("hud-shot").textContent = `${state.shot || "-"} ${state.u !== undefined ? `${Math.round(Math.min(1, state.u) * 100)} %` : ""}`;
    const p0 = strand.poses[0], p11 = strand.poses[strand.poses.length - 1];
    $("hud-strand").textContent = `${strand.formation.name} · rung 1 ${p0.y.toFixed(2)} m ${p0.roll.toFixed(0)}° · rung ${strand.n} ${p11.y.toFixed(2)} m${strand.move ? " · landing" : ""}`;
    $("hud-lasers").textContent = `${state.l2 ? state.l2.look : "-"} · ${state.l3 ? state.l3.n : 0} beams · ${state.l2 && state.l2.hits ? `${state.l2.hits} hits` : "no hits"}`;
    $("hud-haze").textContent = `${Math.round(atmos.H * 100)} % → ${Math.round(atmos.target * 100)} % · σ ${atmos.uniform.sigma0.toFixed(4)} /m · ${atmos.hazers.length} hazers`;
    const st = limiter.stats();
    $("hud-flash").innerHTML = st.interventions ? `<span class="warn">limiter acted on ${st.interventions} frames</span>` : `<span class="ok">no limiter interventions</span> · ${st.frames} frames judged`;
    const avg = timing.list.length ? timing.list.reduce((s, x) => s + x, 0) / timing.list.length : 0;
    $("hud-render").textContent = `${R.w}x${R.h} · ${avg.toFixed(1)} ms CPU+GPU · ${state.info ? `${state.info.beams} beams, ${state.info.emitters} emitters, ${state.info.drawCalls} draws` : ""}`;
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
  // the keyboard: pads 1, 2, 6 and 0 (= pad 10), C next shot, H HUD, F fullscreen
  const KEYPAD = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Digit6: 6, Digit7: 7, Digit0: 10 };
  const held = new Set();
  window.addEventListener("keydown", (e) => {
    if (e.repeat) return;
    const n = KEYPAD[e.code];
    const tEval = performance.now() + grid.presentLagMs;
    if (n) { held.add(e.code); pad(n, e.shiftKey ? 1 : 0.8, true, tEval); e.preventDefault(); return; }
    if (e.code === "KeyH") hudEl.classList.toggle("hidden");
    else if (e.code === "KeyF") { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {}); }
    else if (e.code === "KeyC") {
      const ids = Object.keys(director.shots);
      const cur = ids.indexOf(manualShot ? manualShot : state.shot);
      manualShot = ids[(cur + 1) % ids.length];
      director.manual = { shot: manualShot, u: 0.5 };
    } else if (e.code === "Escape") { manualShot = null; director.manual = null; }
  });
  window.addEventListener("keyup", (e) => {
    const n = KEYPAD[e.code];
    if (n && held.has(e.code)) { held.delete(e.code); pad(n, 0, false, performance.now() + grid.presentLagMs); }
  });
  function canvasCss() { const r = canvas.getBoundingClientRect(); return { w: Math.max(1, r.width), h: Math.max(1, r.height) }; }
  const canvas = $("gl");
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); banner("The WebGL context was lost (the GPU reset). Reload the page."); });

  // ------------------------------------------------------------------------------------------- the receipts' door --
  Object.assign(api, {
    ready: true, rig, grid, programmer, strand, lasers, lasers3d, atmos, director, show, limiter, renderer: R, faders, runner,
    state: () => ({ pos: state.pos, bpm: grid.bpm, bar: grid.barAt(performance.now() + grid.presentLagMs), section: state.section, look: state.look,
                    shot: state.shot, u: state.u, formation: strand.formation.name, info: state.info, counts: rig.counts,
                    limiter: limiter.stats(), grid: { ...grid.stats, ver: grid.ver, locked: grid.locked, barAnchor: grid.barAnchor },
                    haze: { H: atmos.H, target: atmos.target, sigma0: atmos.uniform.sigma0 }, engine: { open: link.open, hello: link.hello },
                    lands: strand.lands.slice(-8), cuts: director.cuts.slice(-16), kicks: kicks.slice(-64), errors: errors.slice(),
                    quality: R.qualityName, renderer: { three: renderMod.QUALITY ? "r186" : "", w: R.w, h: R.h },
                    phrase: runner ? runner.status() : null, phraseSteps: state.phraseSteps.slice(-64),
                    flashGate: { grants: programmer.flashGate.grants.slice(-32), refusals: programmer.flashGate.refusals.slice(-32) } }),
    setShot: (id, u = 0.5) => { manualShot = id; director.manual = { shot: id, u }; },
    clearShot: () => { manualShot = null; director.manual = null; },
    press: (n, vel = 0.9) => pad(n, vel, true, performance.now() + grid.presentLagMs),
    release: (n) => pad(n, 0, false, performance.now() + grid.presentLagMs),
    fader: (id, v) => { faders[id] = v; applyFaders(performance.now() + grid.presentLagMs); syncFaderUI(); },
    inject: (obj) => handle(obj, performance.now()),
    features: (f) => Object.assign(R.features, f),
    profile: (on) => { R.profile = !!on; if (on) R.timings = {}; return R.timings; },
    timings: () => R.timings,
    overdraw: () => R.overdraw(),
    debugTargets: () => R.debugTargets(),
    resetLimiter: () => { const L = new FrameLimiter(); Object.assign(limiter, L); },
    frameTimes: () => timing.list.slice(),
  });
  applyFaders(performance.now() + grid.presentLagMs);
  requestAnimationFrame(frame);
}

boot().then(start).catch((e) => { recordError("boot", e); banner(e.message); api.bootError = e.message; });
