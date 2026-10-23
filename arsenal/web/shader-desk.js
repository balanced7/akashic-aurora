// Shader Desk -- arsenal/web/shader-desk.js. Play's preset bank under the KeyLab's hands.
//
// The page renders Play's presets (arsenal/web/presets/*.frag, listed by GET /api/presets on the arsenal server) with
// lib/preset-gl.js, shows each preset's parameters as house controls (lib/params-ui.js over lib/params.js), and lets
// the KeyLab drive them through lib/keylab-client.js:
//
//   faders 1-8   the active preset's parameters in order (k1, k2, ...), each catching its value only when it passes
//                it (pickup: nothing jumps when you switch presets)
//   knobs 1-8    the same parameters, finely (relative in DAW mode: no jumps, ever)
//   fader 9      intensity       knob 9   hue (0-360)
//   pads 1-8     the first eight presets (velocity flashes the picture); the dial, Fast forward and Rewind step scenes
//   pads 9-12    snapshots A-D of the active preset (tap recalls with a glide, hold stores)
//   chord root   turns the hue round the circle of fifths (switchable)
//   beat, energy, hits from the VJ engine   u_beat, u_bass/mid/high/level, u_pulse, u_flux and the audio texture
//
// Any parameter can be learned to any control instead ("learn", then move or touch it); learned bindings, options and
// snapshots stay in this browser (localStorage, namespace "shader-desk").
//
// URL: ?preset=<id> start there; ?keylab=<events url> or ?keylab=midi; ?scale=0.5 render scale; ?ui=0 perform mode;
// ?freeze=<seconds> hold the shader clock (for checks); ?watchdog=0 never lowers the scale. Test hook: window.__desk.
import { createBinder, createKeyLabClient } from "./lib/keylab-client.js";
import { mountKeyLabHud, wirePadLights, wireScreen } from "./lib/keylab-desk.js";
import { renderParams } from "./lib/params-ui.js";
import { createPresetRenderer, listPresets, parseHeader } from "./lib/preset-gl.js";

const q = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const deskEl = $("desk"), canvas = $("gl"), stage = $("stage");
// Colours a KeyLab pad renders clearly (saturated blue, purple, magenta, pink, red: surface map L4); scene n gets one.
const SCENE_COLOURS = ["#2f6bff", "#8a3cff", "#ff2fd0", "#ff4f8b", "#ff2a2a", "#00a6ff", "#5b2bff", "#c02cff"];
const FADE_MS = 600;

const desk = { scenes: [], hue: 0, intensity: 0.8, panel: null, ready: false, errors: [] };
let r;
try {
  r = createPresetRenderer(canvas, { scale: Number(q.get("scale")) || 1, watchdog: q.get("watchdog") !== "0" });
} catch (err) {
  showError(`The desk needs WebGL2: ${err.message}`);
  throw err;
}
if (q.has("freeze")) r.freeze(Number(q.get("freeze")) || 0);

function showError(text) {
  const e = $("stage-error");
  e.textContent = text;
  e.hidden = !text;
}

// ------------------------------------------------------------------------------------------- the host --
// What the binder drives: the active preset's named knobs, then intensity (master) and hue.
function activeParams() {
  const info = r.active ? r.info(r.active) : null;
  const out = [];
  if (info) {
    for (const p of [...info.params].filter((x) => x && x.k >= 1 && x.k <= 8 && x.name).sort((a, b) => a.k - b.k)) {
      // A knob the compiled shader never reads is still listed (fader n stays k n, as in Play), and says so.
      const inert = info.live && info.live[p.k - 1] === false;
      out.push({ id: `k${p.k}`, label: inert ? `${p.name} (unused)` : p.name, min: 0, max: 1, step: 0.01, unit: "ratio",
        default: typeof p.default === "number" ? p.default : 0, inert });
    }
  }
  out.push({ id: "intensity", label: "intensity", min: 0, max: 1, step: 0.01, unit: "ratio", role: "master", default: 0.8 });
  out.push({ id: "hue", label: "hue", min: 0, max: 360, step: 1, unit: "deg", role: "hue", default: 0 });
  return out;
}
function getValue(id) {
  if (id === "hue") return desk.hue;
  if (id === "intensity") return desk.intensity;
  const m = /^k([1-8])$/.exec(id);
  return m && r.active ? r.knob(r.active, Number(m[1])) : 0;
}
function applyValue(id, v) {
  if (id === "hue") { desk.hue = v; r.setGlobal("u_hue", v); }
  else if (id === "intensity") { desk.intensity = v; r.setGlobal("u_intensity", v); }
  else { const m = /^k([1-8])$/.exec(id); if (m && r.active) r.setKnob(r.active, Number(m[1]), v); }
}
let panelDirty = new Set(), panelFrame = 0;
const host = {
  params: activeParams,
  get: getValue,
  set(id, v) {
    applyValue(id, v);
    panelDirty.add(id);
    if (!panelFrame) panelFrame = requestAnimationFrame(syncPanel);
  },
  scenes: () => desk.scenes.filter((s) => s.ok),
  scene: () => r.active,
  selectScene: (id) => selectScene(id),
  pulse: (vel) => { r.hit(0.35 + 0.65 * (vel || 0)); r.beat(vel || 0.6); },
};

// ------------------------------------------------------------------------------------------- the KeyLab --
const client = createKeyLabClient();
const binder = createBinder(client, host, { namespace: "shader-desk" });
const hud = mountKeyLabHud({ client, binder, parent: $("keylab"), floating: false, overlay: stage, title: "KeyLab",
  map: false, scenes: host.scenes, scene: host.scene });
wirePadLights(client, binder);
wireScreen(client, binder);
client.onBeat(() => r.beat(1));
client.on("energy", (e) => r.setBands(e));
client.on("hit", (e) => r.hit(e.strength));
client.on("pressure", (e) => { if (e.pad >= 1 && e.pad <= 8) r.hit(e.value * 0.8); });
client.on("source", () => paintFoot());
binder.on("readout", (rd) => markHot(rd.param));
binder.on("learn", () => decorateRows());
binder.on("bindings", () => decorateRows());
client.start();

// ------------------------------------------------------------------------------------------- the panel --
function buildPanel() {
  const box = $("params");
  box.textContent = "";
  const list = activeParams();
  const descs = list.map((p, i) => ({ id: p.id, group: p.role ? "master" : "shader", label: p.label, type: "range", unit: p.unit,
    range: { min: p.min, max: p.max, step: p.step }, default: p.default, order: i }));
  const values = Object.fromEntries(list.map((p) => [p.id, getValue(p.id)]));
  desk.panel = renderParams(document, descs, {
    values, idPrefix: "desk",
    groups: [{ id: "shader", label: r.active ? (r.info(r.active).name || r.active) : "shader" }, { id: "master", label: "master" }],
    onChange: (id, v) => { applyValue(id, v); binder.notifyExternal(id); },
  });
  box.append(desk.panel.root);
  for (const p of list) if (p.inert) {
    const rec = desk.panel.rows.get(p.id);
    if (rec) { rec.row.classList.add("inert"); rec.row.title = "This shader declares the knob but never reads it: moving it changes nothing."; }
  }
  $("param-note").textContent = `${list.length - 2} + intensity, hue`;
  decorateRows();
}
function syncPanel() {
  panelFrame = 0;
  if (!desk.panel || !panelDirty.size) return;
  const next = {};
  for (const id of panelDirty) next[id] = getValue(id);
  panelDirty = new Set();
  desk.panel.setValues(next);
}
function decorateRows() {
  if (!desk.panel) return;
  const d = binder.describe();
  for (const p of d.params) {
    const rec = desk.panel.rows.get(p.id);
    if (!rec) continue;
    let bind = rec.row.querySelector(".desk-bind");
    if (!bind) { bind = document.createElement("span"); bind.className = "desk-bind"; rec.row.append(bind); }
    bind.textContent = "";
    for (const c of p.controls) {
      const b = document.createElement("span");
      b.className = "desk-badge" + (c.how === "learned" ? " learned" : "") + (c.picked ? " picked" : "");
      b.textContent = c.control.replace(/^fader/, "F").replace(/^knob/, "K") + (c.fine ? "·" : "");
      b.title = `${c.control} (${c.how}${c.fine ? ", fine trim" : ""}${c.picked ? ", has caught the value" : ", catches it when it passes"})`;
      bind.append(b);
    }
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "desk-chip" + (d.learning === p.id ? " armed" : "");
    chip.textContent = d.learning === p.id ? "touch a control" : "learn";
    chip.title = "Learn: click, then move or touch any fader, knob or wheel. Right-click forgets learned controls.";
    chip.addEventListener("click", () => { binder.learn(p.id); decorateRows(); });
    chip.addEventListener("contextmenu", (ev) => { ev.preventDefault(); binder.unbindParam(p.id); decorateRows(); });
    bind.append(chip);
  }
}
let hotTimer = 0;
function markHot(id) {
  if (!desk.panel) return;
  for (const rec of desk.panel.rows.values()) rec.row.classList.toggle("hot", rec.d.id === id);
  clearTimeout(hotTimer);
  hotTimer = setTimeout(() => { for (const rec of desk.panel.rows.values()) rec.row.classList.remove("hot"); decorateRows(); }, 900);
}

// ------------------------------------------------------------------------------------------- scenes --
function paintScenes() {
  const ol = $("scene-list");
  ol.textContent = "";
  let pad = 0;
  for (const s of desk.scenes) {
    const li = document.createElement("li");
    li.className = "scene" + (s.ok ? "" : " broken") + (s.id === r.active ? " on" : "");
    li.style.setProperty("--scene-c", s.colour);
    const padNo = s.ok && pad < 8 ? ++pad : null;
    const p = document.createElement("span"); p.className = "scene-pad"; p.textContent = padNo ? `P${padNo}` : "";
    const n = document.createElement("span"); n.className = "scene-name"; n.textContent = s.label;
    li.title = s.ok ? `${s.label}${padNo ? ` (pad ${padNo})` : ""}${s.author ? " · " + s.author : ""}` : `${s.label}: ${s.log || "broken"}`;
    li.append(p, n);
    if (s.ok) li.addEventListener("click", () => binder.selectScene(s.id));
    ol.append(li);
  }
  $("scene-count").textContent = `${desk.scenes.filter((s) => s.ok).length} ok${desk.scenes.some((s) => !s.ok) ? ", " + desk.scenes.filter((s) => !s.ok).length + " broken" : ""}`;
}
function selectScene(id) {
  if (!r.select(id, { fadeMs: FADE_MS })) return false;
  const s = desk.scenes.find((x) => x.id === id);
  $("tag-name").textContent = s ? s.label : id;
  $("tag-sub").textContent = s && s.author ? `by ${s.author}` : "";
  try { history.replaceState(null, "", `?${new URLSearchParams({ ...Object.fromEntries(q), preset: id })}`); } catch { /* file:// */ }
  buildPanel();
  paintScenes();
  return true;
}

async function loadScenes() {
  let list;
  try {
    list = await listPresets();
  } catch (err) {
    showError(`Could not list Play's presets (${err.message}). Open this page from the arsenal server: http://127.0.0.1:8793/web/shader-desk.html`);
    return;
  }
  const scenes = [];
  for (const info of list) {
    if (!info || !info.url) continue;
    let src = "";
    try { src = await (await fetch(info.url, { cache: "no-store" })).text(); } catch (err) { src = ""; }
    const header = parseHeader(src) || {};
    const merged = { ...header, ...info, params: info.params && info.params.length ? info.params : header.params || [] };
    const res = src ? r.add(merged, src) : { ok: false, log: "could not fetch the file" };
    scenes.push({ id: String(info.id), label: merged.name || info.id, author: merged.author || "", ok: res.ok && !(info.problems || []).length,
      log: res.log || (info.problems || []).join("; "), colour: "" });
  }
  scenes.filter((s) => s.ok).forEach((s, i) => { s.colour = SCENE_COLOURS[i % SCENE_COLOURS.length]; });
  scenes.filter((s) => !s.ok).forEach((s) => { s.colour = "#444a52"; });
  desk.scenes = scenes;
  const want = q.get("preset");
  const first = scenes.find((s) => s.ok && s.id === want) || scenes.find((s) => s.ok);
  r.setGlobal("u_hue", desk.hue);
  r.setGlobal("u_intensity", desk.intensity);
  if (first) selectScene(first.id);
  else showError("No preset compiled. See the scene list for each one's log.");
  paintScenes();
  hud.refresh();
  r.start();
  desk.ready = true;
}

// ------------------------------------------------------------------------------------------- keys & footer --
function setPerform(on) { deskEl.classList.toggle("perform", on); }
if (q.get("ui") === "0") setPerform(true);
document.addEventListener("keydown", (e) => {
  if (e.target && /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName) && e.target.type !== "range") return;
  // a slider with keyboard focus keeps its own arrow, Home, End and Page keys
  if (e.target && e.target.type === "range" && /^(Arrow|Home$|End$|Page)/.test(e.key)) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key;
  if (k === "h" || k === "H") setPerform(!deskEl.classList.contains("perform"));
  else if (k === "f" || k === "F") { if (document.fullscreenElement) document.exitFullscreen(); else stage.requestFullscreen?.(); }
  else if (k === "ArrowRight") binder.stepScene(1);
  else if (k === "ArrowLeft") binder.stepScene(-1);
  else if (k === "b" || k === "B") r.setBlackout(!r.blackout);
  else if (k === "Escape") binder.cancelLearn();
  else if (/^[1-8]$/.test(k)) { const s = host.scenes()[Number(k) - 1]; if (s) binder.selectScene(s.id); }
  else return;
  e.preventDefault();
});
function paintFoot() {
  const s = r.stats(), st = client.status();
  const scale = s.lowered ? `scale ${s.scale} (lowered from ${s.lowered.from}: frames took ${s.lowered.gapMs} ms)` : `scale ${s.scale}`;
  $("foot-stats").textContent = `${s.w}×${s.h} · ${scale} · ${s.fps || "—"} fps · ${s.fb} · audio: ${s.audio} · KeyLab: ${st.source}`;
}
setInterval(paintFoot, 1000);

// ------------------------------------------------------------------------------------------- the test hook --
window.__desk = {
  ready: () => desk.ready,
  scenes: () => desk.scenes.map((s) => ({ ...s })),
  active: () => r.active,
  select: (id) => binder.selectScene(id),
  uniform: (name) => r.uniform(name),
  value: (id) => getValue(id),
  still: (o) => r.still(o),
  stats: () => r.stats(),
  keylab: () => client.status(),
  bindings: () => binder.describe(),
  readout: () => binder.readout,
  learn: (id) => binder.learn(id),
  option: (key, value) => binder.setOption(key, value),
  renderer: r,
};

loadScenes();
