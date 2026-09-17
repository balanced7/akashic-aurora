// Piano lab: instruments — arsenal/web/piano-lab-instruments.js
// Mounts one piano/instruments/<id>.js around a simple 88-key row that uses piano.js's key geometry and keyX, plays
// synthetic chords so reactive parts show, and exposes window.__lab (ready, snapshot, strike, release, play, pause).
// The stage mirrors piano.js: NeutralToneMapping, UnrealBloom (0.45, radius 0, threshold 0.9), the same three lights,
// fog and floor. The keys get a small dark-studio environment like piano.js's; instruments get none.
//
// Builders: add your instrument id to INSTRUMENTS.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

export const INSTRUMENTS = ["vintage-synth", "keylab88mk3", "upright", "suitcase-ep", "concert-grand", "glass-piano"];

const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const lab = { ready: false, error: null, id: null };
window.__lab = lab;
const fail = (e) => {
  lab.error = String(e && e.stack || e);
  const el = $("err"); el.hidden = false; el.textContent = lab.error;
  console.error(e);
};
window.addEventListener("error", (ev) => fail(ev.error || ev.message));
window.addEventListener("unhandledrejection", (ev) => fail(ev.reason));

// ------------------------------------------------------------ framing and keys (as piano.js) --
const FRAMINGS = {
  "9:16": { id: "9:16", w: 1080, h: 1920, fov: 31, minSpan: 16, follow: true },
  "16:9": { id: "16:9", w: 1920, h: 1080, fov: 23, minSpan: 56, follow: false },
};
const KEY = { first: 21, last: 108, whiteW: 0.94, whiteH: 0.8, whiteL: 6.2, blackW: 0.56, blackH: 0.64,
              blackL: 3.95, blackTop: 0.52, back: -3.1, pivotBack: 6.0 };
const mod = (a, n) => ((a % n) + n) % n;
const WHITE_OFFSET = [0, -1, 1, -1, 2, 3, -1, 4, -1, 5, -1, 6];
const BLACK_CENTER = { 1: 0.9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5.0, 10: 3 + 4 / 7 * 5.5 };
const isBlack = (m) => BLACK_CENTER[mod(m, 12)] !== undefined;
function keyX(m) {
  const oct = Math.floor(m / 12), pc = mod(m, 12);
  const x = isBlack(m) ? oct * 7 + BLACK_CENTER[pc] : oct * 7 + WHITE_OFFSET[pc] + 0.5;
  return x - 38;
}
const RAIL_Y = 1.12, TRAIL_Z = -3.42, FLOOR_Y = -2.3;

// ------------------------------------------------------------ colour (pitch by fifths, OKLCH) --
function oklchToLinear(L, C, hDeg) {
  const h = hDeg * Math.PI / 180, a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
          -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
          -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s].map((v) => Math.max(0, v));
}
const lumaOf = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
const pitchRGB = (() => {
  const raw = [];
  for (let pc = 0; pc < 12; pc++) raw.push(oklchToLinear(0.7, 0.16, mod(pc * 7 * 30 + 20, 360)));
  const mean = Math.exp(raw.reduce((s, c) => s + Math.log(Math.max(lumaOf(...c), 1e-4)), 0) / 12);
  return raw.map((c) => { const k = Math.pow(mean / Math.max(lumaOf(...c), 1e-4), 0.65); return c.map((v) => v * k); });
})();
function noteColor(midi, vel, target = new THREE.Color()) {
  const c = pitchRGB[mod(midi, 12)];
  return target.setRGB(c[0], c[1], c[2]);  // linear working space
}
function cssOf(midi) {
  const c = pitchRGB[mod(midi, 12)], mx = Math.max(...c, 1e-4);
  const enc = (v) => Math.round(255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));
  return `rgb(${enc(Math.min(1, c[0] / mx * 0.95))},${enc(Math.min(1, c[1] / mx * 0.95))},${enc(Math.min(1, c[2] / mx * 0.95))})`;
}

// ------------------------------------------------------------ chords --
// Voicings sit inside C2..C7 so a 61-key instrument frames them too. Key of D flat.
const CHORDS = {
  "D♭6/9": { nns: "1⁶ᐟ⁹", notes: [49, 56, 65, 70, 75] },
  "G♭maj7♯11": { nns: "4ᐞ⁷", notes: [42, 53, 58, 61, 72] },
  "E♭m9": { nns: "2m⁹", notes: [39, 54, 58, 61, 65] },
  "A♭13": { nns: "5¹³", notes: [44, 54, 60, 65, 70] },
};
const PROGRESSION = ["D♭6/9", "G♭maj7♯11", "E♭m9", "A♭13"];

// ------------------------------------------------------------ renderer and stage --
let framing = FRAMINGS["16:9"];
const canvas = $("lab");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "high-performance",
  preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x010206);
scene.fog = new THREE.Fog(0x010206, 95, 280);
const pmrem = new THREE.PMREMGenerator(renderer);
const envMap = (() => {
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.BoxGeometry(80, 40, 80), new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide })));
  const strip = (w, h, intensity, tint, x, y, z, rx, ry) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(tint).multiplyScalar(intensity), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.rotation.set(rx, ry, 0); env.add(m);
  };
  strip(44, 3.2, 5.0, 0xffffff, 0, 15, 10, Math.PI / 2, 0);
  strip(3.2, 18, 2.6, 0xffe1c2, -30, 6, -6, 0, Math.PI / 2);
  strip(3.2, 18, 2.2, 0xc2d2ff, 30, 6, -12, 0, -Math.PI / 2);
  strip(36, 1.6, 1.4, 0x9fb4ff, 0, 3, -34, 0, 0);
  return pmrem.fromScene(env, 0.02).texture;
})();
const camera = new THREE.PerspectiveCamera(framing.fov, framing.w / framing.h, 0.5, 900);
const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(framing.w, framing.h,
  { type: THREE.HalfFloatType, samples: 4 }));
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(framing.w, framing.h), 0.45, 0.0, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

const floor = new THREE.Mesh(new THREE.PlaneGeometry(900, 900), new THREE.MeshStandardMaterial({ color: 0x020203, roughness: 0.62 }));
floor.rotation.x = -Math.PI / 2;
floor.position.y = FLOOR_Y;
scene.add(floor);
scene.add(new THREE.HemisphereLight(0x8a9cc8, 0x040404, 0.22));
const keyLight = new THREE.DirectionalLight(0xfff0dc, 1.9);
keyLight.position.set(-16, 30, 24);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x9db6ff, 1.4);
rimLight.position.set(12, 16, -30);
scene.add(rimLight);
const noteLights = [0, 1, 2].map(() => {
  const light = new THREE.PointLight(0xffffff, 0, 9, 2);
  light.position.set(0, 2.1, -1.4);
  scene.add(light);
  return { light, level: 0 };
});
let noteLightNext = 0;

// ------------------------------------------------------------ keys --
const whiteGeo = new RoundedBoxGeometry(KEY.whiteW, KEY.whiteH, KEY.whiteL, 3, 0.07);
const blackGeo = new RoundedBoxGeometry(KEY.blackW, KEY.blackH, KEY.blackL, 3, 0.06);
const keys = new Map();
const tmpC = new THREE.Color();
function buildKeys(style = {}) {
  const white = new THREE.Color(style.whiteColor ?? 0xdedbd3), black = new THREE.Color(style.blackColor ?? 0x08080a);
  for (let m = KEY.first; m <= KEY.last; m++) {
    const b = isBlack(m), len = b ? KEY.blackL : KEY.whiteL;
    const material = new THREE.MeshPhysicalMaterial({ color: b ? black : white, roughness: b ? 0.3 : 0.36, metalness: 0,
      clearcoat: b ? 0.9 : 0.6, clearcoatRoughness: 0.12, envMap, envMapIntensity: b ? 0.8 : 0.45 });
    const pivot = new THREE.Group();
    const pivotZ = KEY.back - KEY.pivotBack;
    pivot.position.set(keyX(m), 0, pivotZ);
    const mesh = new THREE.Mesh(b ? blackGeo : whiteGeo, material);
    mesh.position.set(0, b ? KEY.blackTop - KEY.blackH / 2 : -KEY.whiteH / 2, KEY.back + len / 2 - pivotZ);
    pivot.add(mesh);
    scene.add(pivot);
    keys.set(m, { m, b, pivot, material, base: b ? black : white, lever: len + KEY.pivotBack, depth: 0, vel: 0, glow: 0 });
  }
}
function updateKeys(dt) {
  for (const k of keys.values()) {
    const held = state.pressed.get(k.m);
    const target = held ? 0.38 : 0;
    k.depth += (target - k.depth) * (1 - Math.exp(-dt / (held ? 0.018 : 0.06)));
    k.pivot.rotation.x = k.depth / k.lever;
    const g = held ? held.vel / 127 : 0;
    k.glow += (g - k.glow) * (1 - Math.exp(-dt / (held ? 0.02 : 0.25)));
    if (k.glow > 0.002) {
      noteColor(k.m, 100, tmpC);
      k.material.emissive.copy(tmpC).multiplyScalar(k.glow * (k.b ? 0.9 : 1.4));
      k.material.color.copy(k.base).lerp(tmpC, k.b ? 0.2 : 0.55 * k.glow);
    } else if (k.material.emissive.r || k.material.emissive.g || k.material.emissive.b) {
      k.material.emissive.setRGB(0, 0, 0);
      k.material.color.copy(k.base);
    }
  }
}

// ------------------------------------------------------------ state and playing --
// state.sounding is the host contract's sustain record (piano.js, the looks header): an entry lives exactly while the note
// sounds, finger or pedal. The lab has no notes engine, so it is derived from state.pressed and state.pedal each step —
// same shape, same rules, so an instrument behaves here as it does on the page.
const state = { pressed: new Map(), pedal: false, chord: null, notes: [], sounding: new Map() };
let t = 0;
function syncSounding() {
  for (const [m, p] of state.pressed) {
    const e = state.sounding.get(m);
    if (!e || e.t0 !== p.t0) state.sounding.set(m, { vel: p.vel, t0: p.t0, held: true, pedal: false, tRelease: null, strike: (e ? e.strike : 0) + 1 });
    else { e.held = true; e.pedal = false; e.tRelease = null; }
  }
  for (const [m, e] of state.sounding) {
    if (state.pressed.has(m)) continue;
    if (e.held) { e.held = false; e.pedal = true; e.tRelease = t; }
    if (!state.pedal) state.sounding.delete(m);   // no finger and no pedal: the sound ends
  }
}
function noteOn(m, vel) {
  state.pressed.set(m, { vel, t0: t });
  state.notes.push({ midi: m, vel, t });
  if (state.notes.length > 64) state.notes.shift();
  const nl = noteLights[noteLightNext++ % 3];
  nl.light.position.x = keyX(m);
  noteColor(m, vel, nl.light.color);
  nl.level = vel / 127;
}
function noteOff(m) { state.pressed.delete(m); }
function strike(name, vel = 118) {
  const ch = CHORDS[name];
  if (!ch) throw new Error(`unknown chord ${name}`);
  ch.notes.forEach((m, i) => noteOn(m, Math.max(1, Math.min(127, vel - i * 2))));
  state.chord = { name, nns: ch.nns, key: "D♭" };
  const el = $("chord");
  el.innerHTML = "";
  el.append(name);
  const small = document.createElement("small");
  small.textContent = ch.nns;
  el.append(small);
  el.style.color = cssOf(ch.notes[0]);
  el.style.opacity = "1";
}
function releaseAll() {
  state.pressed.clear();
  state.chord = null;
  $("chord").style.opacity = "0";
}
const demo = { on: params.get("demo") !== "0", next: 0.6, step: 0, offAt: Infinity, pedalUpAt: Infinity };
function runDemo() {
  if (!demo.on) return;
  if (t >= demo.pedalUpAt) { state.pedal = false; demo.pedalUpAt = Infinity; }
  if (t >= demo.offAt) { releaseAll(); demo.offAt = Infinity; }
  if (t >= demo.next) {
    const name = PROGRESSION[demo.step++ % PROGRESSION.length];
    strike(name, 70 + Math.round(Math.random() * 57));
    state.pedal = true;
    demo.offAt = t + 1.5;
    demo.pedalUpAt = t + 2.25;
    demo.next = t + 2.4;
  }
}

// ------------------------------------------------------------ instrument --
let inst = null, instDef = null;
const measureScene = new THREE.Scene();
function span() {
  const first = instDef?.keySpan?.first ?? KEY.first, last = instDef?.keySpan?.last ?? KEY.last;
  return { first: KEY.first, last: KEY.last, want: { first, last }, left: keyX(KEY.first) - 0.5, right: keyX(KEY.last) + 0.5,
    width: 52, keyTop: 0, blackTop: KEY.blackTop, keyFront: KEY.back + KEY.whiteL, keyBack: KEY.back, bedTop: -0.8,
    floorY: FLOOR_Y, mmPerUnit: 1225.7 / 52 };
}
function makeCtx() {
  return { THREE, scene, keyX, isBlack, KEY: { ...KEY }, noteColor, framing, RoundedBoxGeometry, RAIL_Y, TRAIL_Z, span: span() };
}

// ------------------------------------------------------------ views --
let viewName = params.get("view") || "hero";
const VIEW_FRAMING = { hero: "16:9", player: "9:16", close: "16:9", page: "16:9" };
const box3 = new THREE.Box3(), center = new THREE.Vector3(), size = new THREE.Vector3();
function applyFraming(id) {
  framing = FRAMINGS[id] || FRAMINGS["16:9"];
  renderer.setSize(framing.w, framing.h, false);
  composer.setSize(framing.w, framing.h);
  camera.fov = framing.fov;
  camera.aspect = framing.w / framing.h;
  camera.updateProjectionMatrix();
  inst?.resize?.(framing);
}
function instrumentBox() {
  box3.makeEmpty();
  if (inst) box3.expandByObject(inst.group);
  const s = instDef?.keySpan;
  box3.expandByPoint(new THREE.Vector3(keyX(s?.first ?? KEY.first) - 0.5, 0, KEY.back + KEY.whiteL));
  box3.expandByPoint(new THREE.Vector3(keyX(s?.last ?? KEY.last) + 0.5, 0, KEY.back));
  box3.getCenter(center); box3.getSize(size);
}
function placeCamera() {
  camera.clearViewOffset();
  instrumentBox();
  const deg = THREE.MathUtils.degToRad;
  if (viewName === "player" || viewName === "page") {
    // piano.js's camera: above and behind the keys, lens shifted so the keyboard sits low in the frame
    const vfov = deg(framing.fov), tanH = Math.tan(vfov / 2) * camera.aspect;
    const spanW = viewName === "page" ? 57 : Math.min(57, Math.max(framing.minSpan, size.x + 2));
    const dist = spanW / 2 / tanH + 7, elev = deg(framing.follow ? 22 : 17);
    const cx = viewName === "page" ? 0 : center.x;
    camera.position.set(cx, 0.4 + dist * Math.sin(elev), -0.5 + dist * Math.cos(elev));
    camera.lookAt(cx, 0.4, -0.5);
    const shift = framing.follow ? 0.25 : 0.29;
    camera.setViewOffset(framing.w, framing.h, 0, -shift * framing.h, framing.w, framing.h);
  } else if (viewName === "close") {
    let v = inst?.views?.close;
    if (typeof v === "function") v = v();
    const target = v?.target ? new THREE.Vector3(...v.target) : new THREE.Vector3(center.x + size.x * 0.25, 1, -3);
    const from = v?.from ? new THREE.Vector3(...v.from) : target.clone().add(new THREE.Vector3(5, 8, 16));
    camera.fov = v?.fov ?? framing.fov;
    camera.updateProjectionMatrix();
    camera.position.copy(from);
    camera.lookAt(target);
  } else if (inst?.views?.hero) {
    // an instrument may supply its own hero ({target, from, fov} or a function returning one)
    let v = inst.views.hero;
    if (typeof v === "function") v = v();
    camera.fov = v.fov ?? framing.fov;
    camera.updateProjectionMatrix();
    camera.position.set(...v.from);
    camera.lookAt(...v.target);
  } else {
    // hero: a three-quarter view from the front left, fitted to the instrument
    const yaw = deg(-34), elev = deg(24);
    const radius = size.length() / 2;
    const dist = radius / Math.sin(deg(framing.fov) / 2) * 0.62;
    const look = center.clone().add(new THREE.Vector3(0, -size.y * 0.1, 0));
    camera.position.set(look.x + dist * Math.sin(yaw) * Math.cos(elev), look.y + dist * Math.sin(elev),
      look.z + dist * Math.cos(yaw) * Math.cos(elev));
    camera.lookAt(look);
  }
  camera.updateMatrixWorld();
}

// ------------------------------------------------------------ loop --
let paused = false, last = performance.now(), fps = 0;
function step(dt) {
  t += dt;
  runDemo();
  syncSounding();
  updateKeys(dt);
  for (const nl of noteLights) { nl.level *= Math.exp(-dt / 0.5); nl.light.intensity = nl.level * 7; }
  inst?.update?.(dt, t, state);
}
function render() { composer.render(); }
function frame(now) {
  requestAnimationFrame(frame);
  if (paused) return;
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  fps = fps * 0.95 + (dt > 0 ? 1 / dt : 0) * 0.05;
  step(dt);
  render();
}

function countGroup(root) {
  let calls = 0, triangles = 0, meshes = 0, instances = 0;
  root.traverseVisible((o) => {
    if (!(o.isMesh || o.isLine || o.isPoints)) return;
    const g = o.geometry;
    const n = g.index ? g.index.count : g.attributes.position.count;
    const k = o.isInstancedMesh ? o.count : 1;
    calls++; meshes++; instances += k;
    if (o.isMesh) triangles += (n / 3) * k;
  });
  return { calls, triangles: Math.round(triangles), meshes, instances };
}
function measureInstrument() {
  if (!inst) return null;
  const parent = inst.group.parent;
  measureScene.add(inst.group);
  const autoReset = renderer.info.autoReset;
  renderer.info.autoReset = false;
  renderer.info.reset();
  renderer.render(measureScene, camera);
  const out = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
  renderer.info.autoReset = autoReset;
  (parent || scene).add(inst.group);
  return out;
}
function glInfo() {
  const gl = renderer.getContext();
  const ext = gl.getExtension("WEBGL_debug_renderer_info");
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
}

Object.assign(lab, {
  INSTRUMENTS, CHORDS, state, keyX, isBlack, KEY,
  play() { paused = false; demo.on = true; last = performance.now(); },
  pause() { paused = true; },
  strike(name = "D♭6/9", vel = 120) { strike(name, vel); },
  release() { releaseAll(); },
  // Pose a receipt frame: settle, strike the chord hard, advance `after` seconds, render once, report counts.
  async snapshot(opts = {}) {
    paused = true;
    demo.on = false;
    viewName = opts.view || viewName;
    applyFraming(opts.framing || VIEW_FRAMING[viewName] || "16:9");
    releaseAll(); state.pedal = false; state.notes.length = 0;
    for (let i = 0; i < 120; i++) step(1 / 60);          // let springs, tilt and decays settle
    placeCamera();
    strike(opts.chord || "D♭6/9", opts.vel ?? 124);
    state.pedal = opts.pedal ?? true;
    const after = opts.after ?? 0.1;
    for (let s = 0; s < after; s += 1 / 120) step(1 / 120);
    placeCamera();
    const instrument = { rendered: measureInstrument(), traversal: inst ? countGroup(inst.group) : null };
    renderer.info.autoReset = false;
    renderer.info.reset();
    render();
    const frameInfo = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
    renderer.info.autoReset = true;
    await new Promise((r) => requestAnimationFrame(() => r()));
    return { id: lab.id, view: viewName, framing: framing.id, t, chord: state.chord, gl: glInfo(), three: THREE.REVISION,
      instrument, frame: frameInfo, info: inst?.info ?? null, error: lab.error };
  },
  stats() { return { fps: Math.round(fps), frame: { ...renderer.info.render }, instrument: inst ? countGroup(inst.group) : null }; },
  handle() { return inst; },  // the mounted instrument's handle, for receipts
});

// ------------------------------------------------------------ boot --
(async () => {
  const id = params.get("id") || INSTRUMENTS[0];
  $("pick").innerHTML = INSTRUMENTS.map((n) => `<a href="?id=${n}&view=${viewName}">${n}</a>`).join("")
    + ["hero", "player", "close", "page"].map((v) => `<a href="?id=${id}&view=${v}">${v}</a>`).join("");
  if (!/^[a-z0-9-]+$/.test(id)) throw new Error(`bad instrument id ${id}`);
  framing = FRAMINGS[params.get("framing")] || FRAMINGS[VIEW_FRAMING[viewName]] || FRAMINGS["16:9"];
  instDef = (await import(`./piano/instruments/${id}.js`)).default;
  buildKeys(instDef.keyStyle);
  if (instDef.keySpan && params.get("allkeys") !== "1") {
    for (const k of keys.values()) k.pivot.visible = k.m >= instDef.keySpan.first && k.m <= instDef.keySpan.last;
  }
  inst = instDef.create(makeCtx());
  if (!inst.group.parent) scene.add(inst.group);
  inst.setActive?.(true);
  // An instrument that stands on the floor (an upright, a suitcase piano) says where the floor is; the lab only lowers it.
  const hintFloor = inst.stage?.floorY ?? inst.stageHints?.floorY;
  if (Number.isFinite(hintFloor) && hintFloor < FLOOR_Y) floor.position.y = hintFloor;
  lab.id = instDef.id;
  applyFraming(framing.id);
  step(1 / 60);
  placeCamera();
  render();
  lab.ready = true;
  requestAnimationFrame(frame);
})().catch(fail);
