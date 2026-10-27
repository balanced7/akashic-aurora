// arsenal/web/glider/glider.js -- the playable glide: one island, one wing, one thermal.
//
// The glide-feel brief says the whole game is the act of gliding, and that a point-mass glider
// is enough for feel. This page makes that true on screen: the pinned physics (physics.js) run
// in a vertical plane that follows the wing's heading, bank steers, the thermal is a visible
// column of rising air, and every frame is recorded into the flight log so the pre-registered
// feel proxies print at the end of the run. Turning is control-feel, not physics-truth -- the
// same line physics.js drew; the vertical-plane model is untouched.
import * as THREE from 'three';
import { DEFAULTS, gliderForces, step, thermalUpdraft } from './physics.js';
import { report } from './flightlog.js';

// ---------------------------------------------------------------- world constants
const START = { y: 120, v: 9.2, aoa: 6 };
const THERMAL = { x: 25, z: 220, radius: 30, strength: 7 };
const SEA_LEVEL = 0.5;
const TRAIL_MAX = 900;
const TURN_RATE = 1.15;      // rad/s at full bank
const MAX_BANK = 0.85;       // rad visual roll
const TRIM_AOA = 6;          // degrees the stick returns to when released
const AOA_RATE = 28;         // deg/s of stick input
const AOA_MAX = 18, AOA_MIN = -4;
const SKY_COLOR = new THREE.Color(0x0d1330);
const TRAIL_HEAD = new THREE.Color(0xffc98a);
const TRAIL_TAIL = new THREE.Color(0x141c40);

// ---------------------------------------------------------------- renderer / scene
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(SKY_COLOR);

const scene = new THREE.Scene();
scene.background = SKY_COLOR;
scene.fog = new THREE.Fog(0x0d1330, 260, 2400);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 6000);
camera.position.set(0, 128, -14);

// sky: an inverted gradient dome -- warm at the horizon, deep indigo at the zenith
const skyDome = new THREE.Mesh(
  new THREE.SphereGeometry(3200, 32, 16),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: {
      uZenith: { value: new THREE.Color(0x0a0e26) },
      uHorizon: { value: new THREE.Color(0x3d3a66) },
      uGlow: { value: new THREE.Color(0x8a5a3a) },
    },
    vertexShader: `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      varying vec3 vP;
      uniform vec3 uZenith; uniform vec3 uHorizon; uniform vec3 uGlow;
      void main(){
        float t = clamp(normalize(vP).y, 0.0, 1.0);
        vec3 c = mix(uHorizon, uZenith, pow(t, 0.65));
        c = mix(c, uGlow, exp(-t * 9.0) * 0.55);
        gl_FragColor = vec4(c, 1.0);
      }`,
  })
);
scene.add(skyDome);

// dusk sun: a warm disc low on the horizon plus a soft halo
const sun = new THREE.Mesh(
  new THREE.CircleGeometry(210, 48),
  new THREE.MeshBasicMaterial({ color: 0xffb36b, fog: false })
);
sun.position.set(0, 14, -2900);
scene.add(sun);
const halo = new THREE.Mesh(
  new THREE.CircleGeometry(620, 48),
  new THREE.MeshBasicMaterial({
    color: 0xffa45c, fog: false, transparent: true, opacity: 0.16,
    blending: THREE.AdditiveBlending, depthWrite: false,
  })
);
halo.position.copy(sun.position);
scene.add(halo);

// a few stars, high and still
{
  const pts = [];
  for (let i = 0; i < 260; i++) {
    const a = Math.random() * Math.PI * 2, e = 0.15 + Math.random() * 1.25;
    pts.push(Math.cos(a) * Math.cos(e) * 3100, Math.sin(e) * 3100, Math.sin(a) * Math.cos(e) * 3100);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  scene.add(new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0xcdd6ff, size: 1.6, sizeAttenuation: false, fog: false,
    transparent: true, opacity: 0.7, depthWrite: false,
  })));
}

// sea, and the warm band where water meets sky
const sea = new THREE.Mesh(
  new THREE.CircleGeometry(4000, 48),
  new THREE.MeshBasicMaterial({ color: 0x0e1836 })
);
sea.rotation.x = -Math.PI / 2;
scene.add(sea);
const horizonBand = new THREE.Mesh(
  new THREE.TorusGeometry(3500, 3.5, 8, 96),
  new THREE.MeshBasicMaterial({
    color: 0x7a5a44, fog: false, transparent: true, opacity: 0.55,
    blending: THREE.AdditiveBlending, depthWrite: false,
  })
);
horizonBand.rotation.x = Math.PI / 2;
horizonBand.position.y = 3;
scene.add(horizonBand);

// islands: dark silhouettes, one with a small lamp as the eye's anchor
const ISLANDS = [
  { x: -70, z: 240, r: 46, h: 26 }, { x: 120, z: 340, r: 34, h: 18 },
  { x: -230, z: 520, r: 70, h: 40 }, { x: 260, z: 640, r: 52, h: 30 },
  { x: 60, z: 980, r: 90, h: 52 }, { x: -120, z: 1250, r: 64, h: 36 },
];
const islandMat = new THREE.MeshBasicMaterial({ color: 0x0a0f24 });
for (const i of ISLANDS) {
  const cone = new THREE.Mesh(new THREE.ConeGeometry(i.r, i.h, 5, 1, true), islandMat);
  cone.position.set(i.x, i.h / 2 - 1.5, i.z);
  scene.add(cone);
}
const lamp = new THREE.Mesh(
  new THREE.SphereGeometry(1.1, 12, 8),
  new THREE.MeshBasicMaterial({ color: 0xffc98a, fog: false })
);
lamp.position.set(-70, 26, 240);
scene.add(lamp);

// the thermal: two additive columns -- the outer edge and a brighter core
function makeThermalColumn(radius, opacity) {
  const m = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, 700, 24, 1, true),
    new THREE.MeshBasicMaterial({
      color: 0xffe9c8, transparent: true, opacity, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
    })
  );
  m.position.set(THERMAL.x, 350, THERMAL.z);
  scene.add(m);
  return m;
}
const thermalOuter = makeThermalColumn(THERMAL.radius, 0.07);
const thermalCore = makeThermalColumn(THERMAL.radius * 0.35, 0.12);

// the wing: a swept glider built from one BufferGeometry, warm-lit against the dusk
function buildWing() {
  const g = new THREE.Group();
  const top = new THREE.MeshPhongMaterial({ color: 0xe8d5b0, flatShading: true });
  const pod = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.28, 3.4), top);
  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.55, 0.55), top);
  fin.position.set(0, 0.4, -1.35);
  const wingGeo = new THREE.BufferGeometry();
  const V = [];   // vertices: right half then left half (mirrored)
  const rootLE = [0.16, 0, 0.7], rootTE = [0.16, 0, -0.7];
  const tipLE = [6.0, 0.45, -1.6], tipTE = [6.0, 0.45, -2.0];
  const half = (s) => [
    ...rootLE.map((c, i) => c * (i === 0 ? s : 1)),
    ...rootTE.map((c, i) => c * (i === 0 ? s : 1)),
    ...tipLE.map((c, i) => c * (i === 0 ? s : 1)),
    ...tipTE.map((c, i) => c * (i === 0 ? s : 1)),
  ];
  V.push(...half(1), ...half(-1));
  const idx = [0, 1, 2, 1, 3, 2, 4, 6, 5, 5, 6, 7];
  wingGeo.setAttribute('position', new THREE.Float32BufferAttribute(V, 3));
  wingGeo.setIndex(idx);
  wingGeo.computeVertexNormals();
  const wing = new THREE.Mesh(wingGeo, top);
  g.add(pod, fin, wing);
  return g;
}
const glider = buildWing();
scene.add(glider);

scene.add(new THREE.HemisphereLight(0x4a5a8a, 0x181028, 0.9));
const sunLight = new THREE.DirectionalLight(0xffc98a, 1.4);
sunLight.position.set(120, 60, -400);
scene.add(sunLight);

// the trail: the flight's history, warm at the head, cooling into the sky behind
const trailGeo = new THREE.BufferGeometry();
trailGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(TRAIL_MAX * 3), 3));
trailGeo.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(TRAIL_MAX * 3), 3));
trailGeo.setDrawRange(0, 0);
const trail = new THREE.Line(trailGeo, new THREE.LineBasicMaterial({
  vertexColors: true, transparent: true, opacity: 0.75, fog: false,
}));
scene.add(trail);
const trailPts = [];
const tmpColor = new THREE.Color();

// ---------------------------------------------------------------- flight state
let state = null;
let heading = 0;            // radians; forward = (sin h, 0, cos h)
let bank = 0;               // target roll, -1..1
let bankNow = 0;
let aoa = START.aoa;
let flying = false;
let samples = [];
let frames = 0, runStart = 0;
const keys = new Set();
const camPos = new THREE.Vector3();
const tmpV = new THREE.Vector3();

function reset() {
  state = { x: 0, y: START.y, vx: START.v, vy: 0 };
  heading = 0; bank = 0; bankNow = 0; aoa = START.aoa;
  samples = []; trailPts.length = 0;
  trailGeo.setDrawRange(0, 0);
  frames = 0; runStart = performance.now();
  flying = true;
  camPos.set(-Math.sin(heading) * 14, START.y + 5, -Math.cos(heading) * 14);
  document.getElementById('report').hidden = true;
}

function endRun() {
  if (!flying) return;
  flying = false;
  const r = report(samples, { stallAoa: DEFAULTS.AOA_STALL });
  const fps = frames / ((performance.now() - runStart) / 1000);
  showReport(r, fps);
}

// ---------------------------------------------------------------- feel report
function showReport(r, fps) {
  const lines = [
    ['stable and controllable', r.pitchReversals <= 4, `${r.pitchReversals} pitch oscillation(s)`],
    ['energy trade works', r.diveAccel > 1 && r.climbCost < -1,
      `dive +${r.diveAccel.toFixed(1)} m/s · climb ${r.climbCost.toFixed(1)} m/s`],
    ['thermal ride', r.thermalGain > 5, `${r.thermalGain.toFixed(1)} m gained in the column`],
    ['stall is recoverable', r.recoverable || !r.stallEntered,
      r.stallEntered ? (r.stallRecovered ? 'entered and recovered' : 'entered, NOT recovered') : 'not exercised'],
    ['speed envelope', r.maxSpeed >= 18, `soar ${r.minSpeed.toFixed(1)} → dive ${r.maxSpeed.toFixed(1)} m/s`],
    ['60 fps', fps >= 55, `${fps.toFixed(0)} fps`],
  ];
  const body = document.getElementById('report-body');
  body.innerHTML = '';
  for (const [label, ok, detail] of lines) {
    const row = document.createElement('div');
    row.className = 'report-line';
    row.innerHTML =
      `<span class="mark ${ok ? '' : 'no'}">${ok ? '✓' : '—'}</span>` +
      `<span>${label}</span><span>${detail}</span>`;
    body.appendChild(row);
  }
  document.getElementById('report').hidden = false;
}

// ---------------------------------------------------------------- the loop
const clock = new THREE.Clock();

function tick() {
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), 0.05);
  if (flying && dt > 0) {
    frames++;

    // controls: pitch from the stick, easing back to trim when released
    const up = keys.has('ArrowUp') || keys.has('KeyW') ? 1 : 0;
    const down = keys.has('ArrowDown') || keys.has('KeyS') ? 1 : 0;
    const left = keys.has('ArrowLeft') || keys.has('KeyA') ? 1 : 0;
    const right = keys.has('ArrowRight') || keys.has('KeyD') ? 1 : 0;
    if (up || down) aoa = Math.min(AOA_MAX, Math.max(AOA_MIN, aoa + (up - down) * AOA_RATE * dt));
    else aoa += (TRIM_AOA - aoa) * Math.min(1, dt * 2.2);
    bank = right - left;
    bankNow += (bank * MAX_BANK - bankNow) * Math.min(1, dt * 5);

    // physics: one step in the vertical plane, updraft from the world-position distance
    const updraft = (s) => {
      const wx = Math.sin(heading) * s.x, wz = Math.cos(heading) * s.x;
      return thermalUpdraft(wx - THERMAL.x, wz - THERMAL.z, THERMAL);
    };
    state = step(state, aoa, dt, { updraft });

    // world position: horizontal advance along the heading, altitude from the model
    const sinH = Math.sin(heading), cosH = Math.cos(heading);
    tmpV.copy(glider.position);
    tmpV.x += sinH * state.vx * dt;
    tmpV.z += cosH * state.vx * dt;
    tmpV.y = state.y;
    glider.position.copy(tmpV);
    heading -= bankNow * TURN_RATE * dt;

    // pose: nose follows the angle of attack, wings follow the bank
    glider.rotation.y = heading;
    glider.rotation.x = -THREE.MathUtils.degToRad(aoa) * 0.7;
    glider.rotation.z = -bankNow + (state && aoa > DEFAULTS.AOA_STALL
      ? (Math.random() - 0.5) * 0.05 : 0);   // a stall shudders

    // record + trail
    const inThermal = (() => {
      const dx = glider.position.x - THERMAL.x, dz = glider.position.z - THERMAL.z;
      return dx * dx + dz * dz < THERMAL.radius * THERMAL.radius;
    })();
    samples.push({
      t: performance.now() / 1000,
      x: state.x, y: state.y,
      v: Math.hypot(state.vx, state.vy), aoa, inThermal,
    });
    trailPts.push({ x: glider.position.x, y: glider.position.y, z: glider.position.z });
    if (trailPts.length > TRAIL_MAX) trailPts.shift();

    // HUD
    const f = gliderForces(Math.hypot(state.vx, state.vy), aoa);
    document.getElementById('hud-speed').textContent = Math.hypot(state.vx, state.vy).toFixed(1);
    document.getElementById('hud-alt').textContent = state.y.toFixed(0);
    document.getElementById('hud-aoa').textContent = aoa.toFixed(0);
    document.getElementById('hud-ratio').textContent = f.glideRatio.toFixed(1);
    const hudState = document.getElementById('hud-state');
    if (aoa > DEFAULTS.AOA_STALL) { hudState.textContent = 'stall'; hudState.className = 'hud-state stall'; }
    else if (inThermal) { hudState.textContent = 'riding the thermal'; hudState.className = 'hud-state thermal'; }
    else { hudState.textContent = '—'; hudState.className = 'hud-state'; }

    // thermal shimmer: a slow breathing pulse
    const pulse = 0.75 + 0.25 * Math.sin(performance.now() / 1000 * 1.7);
    thermalOuter.material.opacity = 0.07 * pulse;
    thermalCore.material.opacity = 0.12 * pulse;

    // the sea claims the wing
    if (state.y <= SEA_LEVEL) endRun();
  }

  // trail geometry: rebuild the rolling buffer, head warm, tail cooled into the sky
  const pos = trailGeo.attributes.position.array;
  const col = trailGeo.attributes.color.array;
  for (let i = 0; i < trailPts.length; i++) {
    const p = trailPts[i];
    pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z;
    const t = i / TRAIL_MAX;
    tmpColor.copy(TRAIL_TAIL).lerp(TRAIL_HEAD, t * t);
    col[i * 3] = tmpColor.r; col[i * 3 + 1] = tmpColor.g; col[i * 3 + 2] = tmpColor.b;
  }
  trailGeo.attributes.position.needsUpdate = true;
  trailGeo.attributes.color.needsUpdate = true;
  trailGeo.setDrawRange(0, trailPts.length);

  // chase camera: position, target and up move together, softly
  const fwd = tmpV.set(Math.sin(heading), 0, Math.cos(heading));
  const target = tmpV.set(
    glider.position.x + fwd.x * 10, glider.position.y + 1.5, glider.position.z + fwd.z * 10);
  const desired = tmpV.set(
    glider.position.x - fwd.x * 15, glider.position.y + 4.5, glider.position.z - fwd.z * 15);
  const k = 1 - Math.exp(-dt * 4.5);
  camPos.lerp(desired, k);
  camera.position.copy(camPos);
  camera.lookAt(target);

  renderer.render(scene, camera);
}

// ---------------------------------------------------------------- input
window.addEventListener('keydown', (e) => {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
  keys.add(e.code);
  if (e.code === 'KeyR') reset();
});
window.addEventListener('keyup', (e) => keys.delete(e.code));
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
document.getElementById('report-again').addEventListener('click', reset);

reset();
tick();
