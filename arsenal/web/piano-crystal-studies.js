import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { STUDIES, createStudy } from './piano/crystal-studies.js';
import { damp, createPerformance, frameStats } from './piano/crystal-performance.mjs';
import { CANOPY_FORMS } from './piano/solstice-canopy.js';
import { PITCH_CLASSES, LIGHT_ROWS } from './piano/solstice-signals.mjs';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const fail = error => {
  $('error').hidden = false; $('error').textContent = String(error?.stack || error);
  $('loading').hidden = true; console.error(error);
};
addEventListener('error', e => fail(e.error || e.message));
addEventListener('unhandledrejection', e => fail(e.reason));

const canvas = $('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(1); // The buffer below already includes DPR. Never multiply twice.
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.info.autoReset = false;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050b14);
scene.fog = new THREE.FogExp2(0x050b14, .0032);
const camera = new THREE.PerspectiveCamera(38, 16 / 9, .5, 900);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = .07;
controls.minDistance = 48; controls.maxDistance = 340; controls.maxPolarAngle = Math.PI * .49;
controls.target.set(-3, 1, -25);
camera.position.set(128, 86, 101); controls.update();
const home = { position: camera.position.clone(), target: controls.target.clone() };

const pmrem = new THREE.PMREMGenerator(renderer);
const studio = new THREE.Scene();
const envResources = [];
function softbox(w, h, color, intensity, position, rotation) {
  const g = new THREE.PlaneGeometry(w, h);
  const m = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, m); mesh.position.set(...position); mesh.rotation.set(...rotation);
  studio.add(mesh); envResources.push(g, m);
}
softbox(48, 14, 0xddeaff, 3.5, [0, 32, 8], [Math.PI / 2, 0, 0]);
softbox(12, 28, 0xffe6c8, 2, [-40, 12, -10], [0, Math.PI / 2, 0]);
softbox(12, 28, 0xb6c9ff, 2.2, [40, 12, -20], [0, -Math.PI / 2, 0]);
softbox(40, 8, 0xc4cbff, 1.2, [0, 10, -60], [0, 0, 0]);
const envTarget = pmrem.fromScene(studio, .08);
envResources.forEach(r => r.dispose()); pmrem.dispose();
const envMap = envTarget.texture;

scene.add(new THREE.HemisphereLight(0xb8c8e8, 0x18131c, .55));
const keyLight = new THREE.DirectionalLight(0xfff0dd, 2.7); keyLight.position.set(-25, 55, 25); scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0xa2bdff, 2.4); rimLight.position.set(20, 30, -50); scene.add(rimLight);
const fillLight = new THREE.DirectionalLight(0xffffff, .8); fillLight.position.set(50, 10, 20); scene.add(fillLight);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000),
  new THREE.MeshStandardMaterial({ color: 0x111521, roughness: .48, metalness: .28, envMap, envMapIntensity: .14 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -30.4; scene.add(floor);

// Soft analytic pool under the instrument, not a full-resolution canvas texture or another scene render.
const pool = new THREE.Mesh(new THREE.PlaneGeometry(155, 145), new THREE.ShaderMaterial({
  uniforms: { uColor: { value: new THREE.Color(0x7197bc) } },
  vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader: `uniform vec3 uColor; varying vec2 vUv;
    void main(){ vec2 p=(vUv-.5)*2.0; float a=exp(-dot(p,p)*4.5)*.22;
      gl_FragColor=vec4(uColor,a);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
}));
pool.rotation.x = -Math.PI / 2; pool.position.set(0, -30.32, -25); scene.add(pool);

const renderTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, renderTarget);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .3, .35, 1.1); composer.addPass(bloom);
const smaa = new SMAAPass(); composer.addPass(smaa); // r186 SMAA operates before OutputPass, in linear space.
composer.addPass(new OutputPass());

const KEY = { first: 21, last: 108, whiteW: .94, whiteH: .8, whiteL: 6.2,
  blackW: .56, blackH: .64, blackL: 3.95, blackTop: .52, back: -3.1, pivotBack: 6 };
const whiteOffset = [0,-1,1,-1,2,3,-1,4,-1,5,-1,6];
const blackCenter = { 1: .9, 3: 2.1, 6: 3 + 4 / 7 * 1.5, 8: 5, 10: 3 + 4 / 7 * 5.5 };
const isBlack = m => blackCenter[m % 12] !== undefined;
const keyX = m => Math.floor(m / 12) * 7 + (isBlack(m) ? blackCenter[m % 12] : whiteOffset[m % 12] + .5) - 38;
let studyId = STUDIES[params.get('study')] ? params.get('study') : 'aether';
const noteColors = Array.from({ length: 88 }, () => new THREE.Color());
function tuneColors() {
  const s = STUDIES[studyId], a = new THREE.Color(s.color), b = new THREE.Color(s.second);
  for (let i = 0; i < 88; i++) noteColors[i].copy(a).lerp(b, ((i + 21) * 7 % 12) / 11);
}
tuneColors();
const noteColor = (m, velocity, target = new THREE.Color()) => target.copy(noteColors[Math.max(0, Math.min(87, m - 21))]);
const whiteGeo = new RoundedBoxGeometry(KEY.whiteW, KEY.whiteH, KEY.whiteL, 3, .07);
const blackGeo = new RoundedBoxGeometry(KEY.blackW, KEY.blackH, KEY.blackL, 3, .06);
const keys = [];
for (let m = 21; m <= 108; m++) {
  const black = isBlack(m), len = black ? KEY.blackL : KEY.whiteL;
  const base = new THREE.Color(black ? 0x0b101b : 0xe5e3df);
  const material = new THREE.MeshPhysicalMaterial({ color: base, roughness: .36, clearcoat: .55,
    clearcoatRoughness: .25, envMap, envMapIntensity: .35 });
  const pivot = new THREE.Group(); pivot.position.set(keyX(m), 0, KEY.back - KEY.pivotBack);
  const mesh = new THREE.Mesh(black ? blackGeo : whiteGeo, material);
  mesh.position.set(0, black ? KEY.blackTop - KEY.blackH / 2 : -KEY.whiteH / 2, len / 2 + KEY.pivotBack);
  pivot.add(mesh); scene.add(pivot);
  keys.push({ midi: m, pivot, material, base, depth: 0, glow: 0, lever: len + KEY.pivotBack });
}

const performanceState = createPerformance();
const state = performanceState.state;
let t = 0, study, energy = 0, width = 1, height = 1, runningDemo = true;
let sample = null, report = null, lastStatus = 0, last = performance.now(), rolling = [];
let cameraMode = 'drift', followX = 0, userOrbit = false;
let canopyForm = CANOPY_FORMS.includes(params.get('canopy')) ? params.get('canopy') : 'ribbons';
let lightLesson = null, lastLightStatus = 0;
const ledCells = [];
$('canopy-form').value = canopyForm;
const blank = document.createElement('span'); $('light-matrix').append(blank);
for (const pitch of PITCH_CLASSES) { const label = document.createElement('span'); label.className = 'pitch-label'; label.textContent = pitch; $('light-matrix').append(label); }
for (let row = 0; row < 3; row++) {
  const label = document.createElement('span'); label.className = 'row-label'; label.textContent = LIGHT_ROWS[row]; $('light-matrix').append(label);
  for (let col = 0; col < 12; col++) {
    const cell = document.createElement('i'); cell.className = 'light-cell'; cell.title = `${LIGHT_ROWS[row]} · ${PITCH_CLASSES[col]}`;
    cell.style.setProperty('--led-color', ['#ffc277','#ff947e','#bc8bff'][row]); $('light-matrix').append(cell); ledCells.push(cell);
  }
}
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
$('motion').checked = !reducedMotion.matches;
if (['4k', '1440'].includes(params.get('resolution'))) $('resolution').value = params.get('resolution');

function context() {
  return { THREE, scene, KEY, keyX, isBlack, noteColor, RoundedBoxGeometry, RAIL_Y: 1.12, TRAIL_Z: -3.42,
    floorY: -30.34, framing: { id: '16:9', w: width, h: height },
    span: { first: 21, last: 108, left: -26, right: 26, width: 52, keyTop: 0, blackTop: .52,
      keyFront: 3.1, keyBack: -3.1, bedTop: -.8, floorY: -30.34, mmPerUnit: 1225.7 / 52 } };
}
function invalidateMeasurement(reason) {
  if (sample) { sample = null; $('measure').disabled = false; $('measure-status').textContent = `Measurement cancelled: ${reason}.`; }
}
function canopyDescription() {
  $('light-caption').textContent = canopyForm === 'halo'
    ? 'Inner / low: attack · middle: held · outer / high: pedal-only sustain. C starts at the front; pitches run around each ring.'
    : 'Front / low: attack · middle: held · back / high: pedal-only sustain. C to B runs left to right along each strip.';
  if (studyId === 'solstice') $('study-description').textContent = canopyForm === 'sails'
    ? STUDIES.solstice.description : 'Champagne brass · opal LED ribbons · light that follows the music';
}
function selectStudy(id) {
  if (!STUDIES[id]) return;
  invalidateMeasurement('study changed');
  study?.dispose(); studyId = id; tuneColors();
  study = createStudy(context(), id, envMap, { canopy: canopyForm });
  $('canopy-controls').hidden = id !== 'solstice';
  $('light-legend').hidden = canopyForm === 'sails';
  const s = STUDIES[id];
  document.documentElement.style.setProperty('--accent', s.accent);
  $('study-number').textContent = s.number; $('study-name').textContent = s.name;
  $('study-subtitle').textContent = s.subtitle; $('study-description').textContent = s.description;
  canopyDescription();
  scene.background.setHex(s.bg); scene.fog.color.setHex(s.bg); bloom.strength = s.bloom;
  pool.material.uniforms.uColor.value.setHex(s.color); rimLight.color.setHex(s.second);
  keyLight.color.setHex(id === 'solstice' ? 0xffe1b2 : 0xeaf2ff);
  for (const button of document.querySelectorAll('[data-study]')) {
    const active = button.dataset.study === id;
    button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
  }
  const url = new URL(location.href); url.searchParams.set('study', id); history.replaceState(null, '', url);
  rolling = []; report = null; $('metrics').textContent = 'Waiting for a measurement.';
}
$('canopy-form').addEventListener('change', () => {
  invalidateMeasurement('overhead light shape changed'); canopyForm = $('canopy-form').value;
  study?.setCanopy(canopyForm); $('light-legend').hidden = canopyForm === 'sails';
  const url = new URL(location.href); url.searchParams.set('canopy', canopyForm); history.replaceState(null, '', url);
  canopyDescription();
});
function resize() {
  invalidateMeasurement('render size changed');
  const mode = $('resolution').value;
  if (mode === '4k') [width, height] = [3840, 2160];
  else if (mode === '1440') [width, height] = [2560, 1440];
  else { width = Math.max(1, Math.round(innerWidth * devicePixelRatio)); height = Math.max(1, Math.round(innerHeight * devicePixelRatio)); }
  renderer.setSize(width, height, false); composer.setSize(width, height);
  camera.aspect = width / height; camera.updateProjectionMatrix();
  canvas.style.objectFit = 'contain';
  rolling = [];
}
addEventListener('resize', resize);
$('resolution').addEventListener('change', () => {
  resize(); const url = new URL(location.href); url.searchParams.set('resolution', $('resolution').value); history.replaceState(null, '', url);
});
// Check DPR independently of CSS resize when moving between displays.
let currentDpr = devicePixelRatio;
setInterval(() => { if (currentDpr !== devicePixelRatio) { currentDpr = devicePixelRatio; if ($('resolution').value === 'native') resize(); } }, 1000);
$('smoothing').addEventListener('change', () => {
  invalidateMeasurement('antialiasing changed');
  const on = $('smoothing').checked;
  for (const rt of [composer.renderTarget1, composer.renderTarget2]) { rt.dispose(); rt.samples = on ? 4 : 0; }
  smaa.enabled = on; rolling = [];
});
$('motion').addEventListener('change', () => invalidateMeasurement('motion changed'));
reducedMotion.addEventListener('change', e => { $('motion').checked = !e.matches; });

// A deterministic, lightly arpeggiated performance; each chord breathes through its pedal release.
const chords = [
  { name: 'D♭ 6/9', notes: [37, 49, 56, 65, 70, 75] },
  { name: 'G♭ maj9 ♯11', notes: [30, 42, 53, 58, 65, 72] },
  { name: 'E♭ m9', notes: [39, 46, 54, 58, 61, 65] },
  { name: 'A♭ 13', notes: [32, 44, 54, 60, 65, 70] },
];
let demoTime = 0, lastStep = -1;
const releases = new Map();
function demo(dt) {
  if (lightLesson) { runLightLesson(dt); return; }
  if (!runningDemo) return;
  demoTime += dt;
  const step = Math.floor(demoTime / .34), phrase = Math.floor(step / 16), beat = step % 16;
  if (step !== lastStep) {
    lastStep = step;
    const chord = chords[phrase % chords.length];
    state.chord = { name: chord.name, notes: chord.notes };
    if (beat === 0) {
      performanceState.pedal(false); performanceState.pedal(true);
      for (const m of chord.notes.slice(0, 2)) { performanceState.noteOn(m, 83, t); releases.set(m, t + .85); }
    }
    if (beat === 14) performanceState.pedal(false);
    if (beat < 14) {
      const index = [2, 3, 4, 5, 4, 3, 2, 4, 5, 3, 4, 5, 4, 2][beat];
      const midi = chord.notes[index] + (beat === 11 ? 12 : 0);
      performanceState.noteOn(midi, 65 + ((step * 17) % 36), t); releases.set(midi, t + .45);
    }
  }
  for (const [midi, release] of releases) if (t >= release) { performanceState.noteOff(midi, t); releases.delete(midi); }
}
function setDemo(on) {
  lightLesson = null; $('light-cue').textContent = '';
  invalidateMeasurement('performance changed'); runningDemo = on;
  performanceState.clear(); releases.clear(); demoTime = 0; lastStep = -1;
  $('demo').setAttribute('aria-pressed', String(on)); $('play-icon').textContent = on ? 'Ⅱ' : '▷';
  $('demo-label').textContent = on ? 'Pause performance' : 'Play performance';
  $('source').textContent = on ? 'GENERATIVE PERFORMANCE' : 'LIVE PERFORMANCE';
}
$('demo').addEventListener('click', () => setDemo(!runningDemo));

// A visible, repeatable musical example doubles as an end-to-end check without a MIDI device.
const lightSteps = [
  { at: 0, cue: '1 / Attack · C, E and G flare together', run() { for (const m of [60,64,67]) performanceState.noteOn(m, 108, t); } },
  { at: 1.4, cue: '2 / Held · the middle layer carries the chord', run() {} },
  { at: 3, cue: '3 / Pedal · fingers lift, the upper layer stays lit', run() { performanceState.pedal(true); for (const m of [60,64,67]) performanceState.noteOff(m, t); } },
  { at: 5, cue: '4 / New notes · D and A above the sustained chord', run() { for (const m of [62,69]) performanceState.noteOn(m, 116, t); } },
  { at: 6.5, cue: '5 / Release · the pedal layer fades away', run() { performanceState.pedal(false); for (const m of [62,69]) performanceState.noteOff(m, t); } },
];
$('light-demo').addEventListener('click', () => {
  const resume = runningDemo; setDemo(false);
  lightLesson = { elapsed: 0, start: performance.now(), step: 0, resume }; $('source').textContent = 'LIGHT DEMONSTRATION';
});
function runLightLesson(dt) {
  lightLesson.elapsed = (performance.now() - lightLesson.start) / 1000;
  while (lightLesson.step < lightSteps.length && lightLesson.elapsed >= lightSteps[lightLesson.step].at) {
    const step = lightSteps[lightLesson.step++]; step.run(); $('light-cue').textContent = step.cue;
  }
  if (lightLesson.elapsed >= 9) { const resume = lightLesson.resume; setDemo(resume); $('light-cue').textContent = 'Attack → held → pedal → release'; }
}

const typing = e => ['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(e.target.tagName);
const typingKeys = { a: 60, w: 61, s: 62, e: 63, d: 64, f: 65, t: 66, g: 67, y: 68, h: 69, u: 70, j: 71, k: 72 };
addEventListener('keydown', e => {
  if (typing(e) || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
  if (typingKeys[e.key.toLowerCase()] !== undefined || e.code === 'Space') {
    e.preventDefault(); if (runningDemo || lightLesson) setDemo(false);
    if (e.code === 'Space') performanceState.pedal(true);
    else performanceState.noteOn(typingKeys[e.key.toLowerCase()], 103, t);
  }
});
addEventListener('keyup', e => {
  if (e.code === 'Space') { if (!typing(e)) e.preventDefault(); performanceState.pedal(false); }
  else if (typingKeys[e.key.toLowerCase()] !== undefined) performanceState.noteOff(typingKeys[e.key.toLowerCase()], t);
});
addEventListener('blur', () => { if (!runningDemo) performanceState.clear(); });
let midiAccess;
$('midi').addEventListener('click', async () => {
  if (!navigator.requestMIDIAccess) { $('midi').textContent = 'MIDI unavailable in this browser'; return; }
  try {
    midiAccess ??= await navigator.requestMIDIAccess({ sysex: false });
    setDemo(false);
    const attach = () => {
      let count = 0;
      for (const input of midiAccess.inputs.values()) {
        if (input.state === 'connected') count++;
        input.onmidimessage = ({ data }) => {
          const cmd = data[0] & 0xf0, m = data[1], v = data[2];
          if (runningDemo || lightLesson) setDemo(false);
          if (cmd === 0x90 && v > 0) performanceState.noteOn(m, v, t);
          else if (cmd === 0x80 || cmd === 0x90) performanceState.noteOff(m, t);
          else if (cmd === 0xb0 && m === 64) performanceState.pedal(v >= 64);
          else if (cmd === 0xb0 && [120, 123].includes(m)) performanceState.clear();
        };
      }
      $('midi').textContent = count ? `MIDI connected · ${count}` : 'Waiting for a MIDI keyboard';
    };
    attach(); midiAccess.onstatechange = e => { if (e.port.state === 'disconnected') performanceState.clear(); attach(); };
  } catch (e) { $('midi').textContent = 'MIDI access was not granted'; }
});

function setCameraMode(mode) {
  invalidateMeasurement('camera changed'); cameraMode = mode; userOrbit = mode === 'orbit';
  $('camera').value = mode;
}
controls.addEventListener('start', () => setCameraMode('orbit'));
$('camera').addEventListener('change', e => setCameraMode(e.target.value));
const goalPosition = new THREE.Vector3(), goalTarget = new THREE.Vector3();
function updateCamera(dt) {
  if (userOrbit) { controls.update(); return; }
  let sum = 0, weight = 0;
  for (const [midi, e] of state.sounding) { sum += keyX(midi) * e.vel; weight += e.vel; }
  followX = damp(followX, weight ? sum / weight : 0, dt, 1.4);
  const motion = $('motion').checked, phase = motion ? t * .045 : 0;
  goalPosition.copy(home.position); goalTarget.copy(home.target);
  if (cameraMode === 'detail') {
    goalPosition.set(46 + followX * .2, 42, 32); goalTarget.set(followX * .35, 3, -20);
  } else {
    if (motion) { goalPosition.x += Math.sin(phase) * 8; goalPosition.y += Math.sin(phase * .7) * 2.5; }
    if (cameraMode === 'follow') { goalTarget.x += followX * .32; goalPosition.x += followX * .5; }
  }
  const fit = Math.max(1, (cameraMode === 'detail' ? 1.15 : 1.55) / camera.aspect);
  goalPosition.sub(goalTarget).multiplyScalar(fit).add(goalTarget);
  // Frame-rate-independent easing avoids speed changes between 60 Hz and high-refresh displays.
  const a = 1 - Math.exp(-dt / 1.1);
  camera.position.lerp(goalPosition, a); controls.target.lerp(goalTarget, a); controls.update();
}

function settings(open) { $('settings').hidden = !open; $('settings-button').setAttribute('aria-expanded', String(open)); }
$('settings-button').addEventListener('click', () => settings($('settings').hidden));
$('close-settings').addEventListener('click', () => settings(false));
$('fullscreen').addEventListener('click', async () => {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
  catch { $('fullscreen').title = 'Fullscreen is unavailable in this browser window'; }
});
for (const button of document.querySelectorAll('[data-study]')) button.addEventListener('click', () => selectStudy(button.dataset.study));
document.addEventListener('visibilitychange', () => {
  invalidateMeasurement('tab visibility changed'); last = performance.now(); rolling = [];
  if (document.hidden) {
    if (lightLesson) setDemo(lightLesson.resume);
    performanceState.clear(); releases.clear();
  }
});

$('measure').addEventListener('click', () => {
  const gl = renderer.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info');
  sample = { warmUntil: performance.now() + 3000, end: performance.now() + 18000, intervals: [], cpu: [],
    config: { study: studyId, width, height, aa: smaa.enabled ? '4x MSAA + SMAA' : 'off',
      camera: cameraMode, demo: runningDemo, canopy: studyId === 'solstice' ? canopyForm : null, motion: $('motion').checked, dpr: devicePixelRatio,
      three: THREE.REVISION, gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER) } };
  $('measure').disabled = true; $('measure-status').textContent = 'Warming up for 3 seconds…';
});
function updateMeasurement(now, interval, cpuMs) {
  if (!sample) return;
  if (now < sample.warmUntil) return;
  if (now < sample.end) {
    sample.intervals.push(interval); sample.cpu.push(cpuMs);
    return;
  }
  const cpu = [...sample.cpu].sort((a, b) => a - b);
  report = { ...sample.config, ...frameStats(sample.intervals),
    cpuP95Ms: +(cpu[Math.ceil(cpu.length * .95) - 1] || 0).toFixed(2),
    calls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
    geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures,
    measuredAt: new Date().toISOString() };
  $('metrics').textContent = JSON.stringify(report, null, 2);
  $('measure-status').textContent = 'Complete · visible frame intervals, not a monitor scanout measurement.';
  $('measure').disabled = false; sample = null;
}
function frame(now) {
  requestAnimationFrame(frame);
  if (document.hidden) { last = now; return; }
  const interval = now - last; last = now;
  const dt = Math.min(.05, Math.max(0, interval) / 1000); t += dt;
  const cpuStart = performance.now();
  demo(dt);
  for (const k of keys) {
    const held = state.pressed.get(k.midi);
    k.depth = damp(k.depth, held ? .38 : 0, dt, held ? .018 : .065);
    k.glow = damp(k.glow, held ? held.vel / 127 : 0, dt, held ? .04 : .4);
    k.pivot.rotation.x = k.depth / k.lever;
    k.material.emissive.copy(noteColors[k.midi - 21]).multiplyScalar(k.glow * .8);
    k.material.color.copy(k.base).lerp(noteColors[k.midi - 21], k.glow * .22);
  }
  energy = study.update(dt, t, state, $('motion').checked); updateCamera(dt);
  if (study.canopyCells && now - lastLightStatus > 90) {
    lastLightStatus = now;
    for (let i = 0; i < ledCells.length; i++) {
      const level = study.canopyCells[i]; ledCells[i].style.opacity = String(.12 + level * .88);
      ledCells[i].dataset.level = level.toFixed(3);
    }
  }
  renderer.info.reset(); composer.render(dt);
  updateMeasurement(now, interval, performance.now() - cpuStart);
  if (interval > 0) rolling.push(interval);
  if (rolling.length > 180) rolling.shift();
  if (now - lastStatus > 500) {
    lastStatus = now;
    const stats = frameStats(rolling);
    $('render-status').textContent = `${width} × ${height}  /  ${stats?.fps.toFixed(0) || '—'} FPS  /  ${smaa.enabled ? 'SMOOTH' : 'AA OFF'}`;
    $('harmony').textContent = runningDemo ? state.chord?.name || 'D♭ 6/9' : `${state.sounding.size} voices`;
    $('sustain').textContent = state.pedal ? 'Sustain held · resonance unfolding' : '88 keys · physical action';
    $('energy').style.width = `${Math.min(100, energy * 100)}%`;
    if (sample && now >= sample.warmUntil) $('measure-status').textContent = `Measuring… ${Math.ceil((sample.end - now) / 1000)} seconds remaining`;
  }
}

resize(); selectStudy(studyId);
study.update(1 / 60, 0, state, $('motion').checked);
composer.render(); $('loading').hidden = true;
last = performance.now(); requestAnimationFrame(frame);
