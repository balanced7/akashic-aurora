// Virtual Stage v0, the renderer: arsenal/web/stage/render.js. three.js r186 WebGLRenderer (WebGL2), the same pinned
// build the piano page ships; shaders are our own GLSL (shaders.js) composed with the house library. The renderer never
// sees music: it draws one FrameState (the design's section 4.7) per call.
//
// The frame graph (design 4.2, the v0 subset):
//   1. opaque pass into a scene-linear HDR target (RGBA16F, 4x MSAA, with a depth texture): the hall, the crowd, the
//      strand's trusses and cubes, the rings' frames, the fixtures' bodies; lit by the moving heads as spot lights (no
//      shadows in v0); then, additive and depth-tested, the LED emitters (dots, bars, slats, rims, lenses, laser dots) and
//      the laser ribbons;
//   2. wide beams at half resolution: one cone proxy per lit head (back faces, so the camera can sit inside a beam),
//      the ray-cone interval clipped by the scene's depth, the in-scatter integrated equiangularly in the shared medium;
//   3. composite: scene + beams (bilinear upsample; the depth-aware upsample is v1) + the haze veil (aerial perspective);
//   4. bloom (6 levels, Karis first) and the finish (house display-out: exposure, display curve, saturation, vignette,
//      sRGB, static dither) into an 8-bit frame;
//   5. the meter (4 x 4 cell sums of relative luminance and the WCAG red quantity, exact box sums over every pixel), read
//      back, judged by the stage's FrameLimiter (flash.js), and the apply pass onto the canvas.
// Units: scene light is in "units" of 30 nits (UNIT_NITS), so a half-float target holds a blinding lens (clamped at 6e4).
//
// v1 (2026-10-25): the crowd near the lens is culled (within 4 m) and its raised arms hold still (within 10 m) in the
// crowd's own vertex shader (shaders.js litVertex), the source of the v0 limiter interventions under TUNNEL_UP; the rig's
// v1 fixtures (the halo, the pods, the towers, the delay towers, the 24-head lip) draw through the same per-head and
// per-cell paths, as the scene's data says.

import * as THREE from "three";
import * as S from "./shaders.js";
import { elementMatrix, headPose, transformPoint, CELL_KIND } from "./rig.js";
import { roomHit, L3, L3_FLOATS } from "./lasers3d.js";
import { H, HEAD_FLOATS } from "./programmer.js";
import { hazeNoise3D } from "./atmos.js";
import { vfovOf } from "./camera.js";

export const UNIT_NITS = 30;
const U = 1 / UNIT_NITS;
const DEG = Math.PI / 180;
// the pass timings need wall-clock time even when a receipt has replaced performance.now with a virtual clock
const realNow = () => (globalThis.__realNow ? globalThis.__realNow() : performance.now());
// luminous efficacy per watt and channel, as linear-RGB units: Y of the result equals the beam's lumens (green 532 nm
// ~600 lm/W, red 638 nm ~137, blue 445 nm ~24; divided by each primary's luminance weight)
const LUM_PER_WATT = [644, 839, 331];

export const QUALITY = Object.freeze({
  high:    { msaa: 4, beamScale: 0.5, beamSamples: 6, bloomLevels: 6, crowd: 1 },
  receipt: { msaa: 4, beamScale: 0.5, beamSamples: 6, bloomLevels: 6, crowd: 1 },
  low:     { msaa: 0, beamScale: 0.34, beamSamples: 4, bloomLevels: 4, crowd: 1 },
});

function rngOf(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ------------------------------------------------------------------------------------------- geometry helpers --
// Merge boxes and other geometries into one indexed BufferGeometry (positions and normals), each with a matrix.
function mergeGeoms(parts) {
  const pos = [], nor = [], idx = [];
  let base = 0;
  for (const { geom, matrix } of parts) {
    const g = geom.index ? geom : geom;
    const p = g.attributes.position, n = g.attributes.normal;
    const nm = new THREE.Matrix3().getNormalMatrix(matrix);
    const v = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i).applyMatrix4(matrix); pos.push(v.x, v.y, v.z);
      v.fromBufferAttribute(n, i).applyMatrix3(nm).normalize(); nor.push(v.x, v.y, v.z);
    }
    if (g.index) for (let i = 0; i < g.index.count; i++) idx.push(g.index.getX(i) + base);
    else for (let i = 0; i < p.count; i++) idx.push(i + base);
    base += p.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
  out.setIndex(idx);
  return out;
}
const M4 = (x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) =>
  new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)), new THREE.Vector3(sx, sy, sz));
const BOX = new THREE.BoxGeometry(1, 1, 1);
// a bar from a to b (2D in a plane z = const), thickness t
function strut(ax, ay, bx, by, t = 0.08, z = 0, depth = null) {
  const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
  return { geom: BOX, matrix: M4((ax + bx) / 2, (ay + by) / 2, z, 0, 0, Math.atan2(dy, dx), len, t, depth ?? t) };
}

// The rung (procedural:rung-v1), in the element's frame: x along the rung, y up, z along the strand.
function rungGeometry() {
  const parts = [];
  // the diamond frame (a rotated square, 2.0 m across) round the centre
  const D = 1.0;
  for (const [a, b] of [[[D, 0], [0, D]], [[0, D], [-D, 0]], [[-D, 0], [0, -D]], [[0, -D], [D, 0]]]) parts.push(strut(a[0], a[1], b[0], b[1], 0.11, 0, 0.3));
  // the two straight box-truss segments (four chords each) carrying the pixel bars
  for (const s of [-1, 1]) {
    for (const [yy, zz] of [[0.13, 0.13], [-0.13, 0.13], [0.13, -0.13], [-0.13, -0.13]]) parts.push({ geom: BOX, matrix: M4(s * 2.0, yy, zz, 0, 0, 0, 2.0, 0.045, 0.045) });
    for (let k = 0; k < 6; k++) parts.push(strut(s * (1.05 + k * 0.32), -0.13, s * (1.21 + k * 0.32), 0.13, 0.03, 0.13));
    // the X node
    parts.push(strut(s * 3.05, -0.55, s * 4.05, 0.55, 0.1, 0, 0.12));
    parts.push(strut(s * 3.05, 0.55, s * 4.05, -0.55, 0.1, 0, 0.12));
    parts.push({ geom: BOX, matrix: M4(s * 3.55, 0, 0, 0, 0, 0, 1.0, 0.12, 0.28) });
    // the pickup plate
    parts.push({ geom: BOX, matrix: M4(s * 4.3, 0.62, 0, 0, 0, 0, 0.18, 0.08, 0.3) });
  }
  return mergeGeoms(parts);
}
function ringGeometry(outer, depth) {
  const parts = [];
  const inner = outer - depth;
  parts.push({ geom: new THREE.TorusGeometry(outer, 0.09, 6, 160), matrix: new THREE.Matrix4() });
  parts.push({ geom: new THREE.TorusGeometry(inner, 0.08, 6, 120), matrix: new THREE.Matrix4() });
  for (let i = 0; i < 48; i++) {
    const a = (i * 7.5) * DEG, r = inner + depth / 2;
    parts.push({ geom: BOX, matrix: M4(r * Math.cos(a), r * Math.sin(a), -0.05, 0, 0, a, depth, 0.07, 0.1) });
  }
  return mergeGeoms(parts);
}
// A crowd figure, low-poly but round (a box crowd reads as crates from up close): a tapered body, shoulders, a head;
// the raised-arm variant is two forearms-and-upper-arms in one piece each.
const BODY = new THREE.CylinderGeometry(0.17, 0.2, 1.36, 7);
const SHOULDERS = new THREE.SphereGeometry(0.23, 7, 3, 0, Math.PI * 2, 0, Math.PI / 2);
const HEADG = new THREE.SphereGeometry(0.115, 7, 5);
const ARM = new THREE.CylinderGeometry(0.04, 0.05, 0.68, 5);
function personGeometry(arms) {
  const parts = [];
  if (!arms) {
    parts.push({ geom: BODY, matrix: M4(0, 0.68, 0) });
    parts.push({ geom: SHOULDERS, matrix: M4(0, 1.32, 0, 0, 0, 0, 1, 0.45, 0.6) });
    parts.push({ geom: HEADG, matrix: M4(0, 1.6, 0) });
  } else {
    parts.push({ geom: ARM, matrix: M4(-0.25, 1.74, 0, 0, 0, 0.14) });
    parts.push({ geom: ARM, matrix: M4(0.25, 1.74, 0, 0, 0, -0.14) });
  }
  return mergeGeoms(parts);
}

// ------------------------------------------------------------------------------------------------- the renderer --
export class StageRenderer {
  constructor(canvas, rig, lib, { quality = "high", theme = null } = {}) {
    this.canvas = canvas;
    this.rig = rig;
    this.q = { ...(QUALITY[quality] || QUALITY.high) };
    this.qualityName = QUALITY[quality] ? quality : "high";
    this.features = { venue: true, crowd: true, strand: true, rings: true, beams: true, lasers: true, emitters: true, bloom: true, veil: true };
    this.profile = false;
    this.timings = {};
    this.preludeMain = lib.compose(["volume-phase", "dither-masks", "colour-transfer"], "webgl2");
    this.preludeFinish = lib.compose(["display-out", "colour-transfer"], "webgl2");
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, depth: true, stencil: false,
                                                        powerPreference: "high-performance", preserveDrawingBuffer: false });
    r.autoClear = false;
    r.info.autoReset = false;          // counted over the whole frame (reset in render())
    r.setPixelRatio(1);
    r.toneMapping = THREE.NoToneMapping;
    this.gl = r.getContext();
    this.camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.1, 420);
    this.world = new THREE.Scene();
    this.beamScene = new THREE.Scene();
    this.fsScene = new THREE.Scene();
    this.fsCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const tri = new THREE.BufferGeometry();
    tri.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
    this.fsMesh = new THREE.Mesh(tri);
    this.fsMesh.frustumCulled = false;
    this.fsScene.add(this.fsMesh);
    this._noise();
    this._uniforms();
    this._materials();
    this._build();
    this.w = 0; this.h = 0;
    this.cells = { L: new Float64Array(16), R: new Float64Array(16) };
    this.info = {};
  }

  _noise() {
    const N = 32;
    const tex = new THREE.Data3DTexture(hazeNoise3D(N, this.rig.seed), N, N, N);
    tex.format = THREE.RedFormat; tex.type = THREE.UnsignedByteType;
    tex.minFilter = THREE.LinearFilter; tex.magFilter = THREE.LinearFilter;
    tex.wrapS = tex.wrapT = tex.wrapR = THREE.RepeatWrapping;
    tex.unpackAlignment = 1; tex.generateMipmaps = false;
    tex.needsUpdate = true;
    this.noiseTex = tex;
  }

  _uniforms() {
    const n = S.MAX_SPOTS;
    this.spot = { uNSpot: { value: 0 }, uSpotPos: { value: new Float32Array(n * 3) }, uSpotDir: { value: new Float32Array(n * 3) },
                  uSpotCol: { value: new Float32Array(n * 3) }, uSpotShape: { value: new Float32Array(n * 3) },
                  uAmbient: { value: new THREE.Vector3(0.02, 0.02, 0.03) } };
    this.haze = { uNoise: { value: this.noiseTex }, uSigma0: { value: 0.006 }, uNoiseAmp: { value: 0.6 }, uWind: { value: new THREE.Vector3() },
                  uHazer: { value: new Float32Array(32) }, uHazerSigma: { value: new Float32Array(8) }, uG: { value: 0.75 },
                  uSigmaAvg: { value: 0.006 } };
    this.view = { uPixAngle: { value: 0.001 }, uRes: { value: new THREE.Vector2(1, 1) }, uMinPx: { value: 1.5 } };
  }

  _raw(vs, fs, uniforms, extra = {}) {
    return new THREE.RawShaderMaterial({ glslVersion: THREE.GLSL3, vertexShader: vs, fragmentShader: fs, uniforms, ...extra });
  }
  _materials() {
    const add = { transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
                  blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor };
    this.crowdNear = { uCullNear: { value: S.CROWD_CULL_NEAR_M }, uFreezeFar: { value: S.CROWD_FREEZE_M } };
    const lit = (albedo, emissive = [0, 0, 0], opts = {}) => this._raw(S.litVertex(opts), S.litFragment(this.preludeMain),
      { ...this.spot, ...(opts.nearCull ? this.crowdNear : {}), uAlbedo: { value: new THREE.Vector3(...albedo) }, uEmissive: { value: new THREE.Vector3(...emissive) } },
      { side: THREE.DoubleSide });
    this.mat = {
      floor: lit([0.05, 0.05, 0.055]), stand: lit([0.07, 0.07, 0.08]), roof: lit([0.02, 0.02, 0.025]), drape: lit([0.012, 0.012, 0.014]),
      truss: lit([0.32, 0.32, 0.34], [0, 0, 0], { instanced: true }), trussStatic: lit([0.3, 0.3, 0.32]),
      deck: lit([0.06, 0.06, 0.07]), body: lit([0.05, 0.05, 0.055], [0, 0, 0], { instanced: true }),
      person: lit([0.035, 0.032, 0.034], [0, 0, 0], { instanced: true, nearCull: true }),
      arms: this._raw(S.litVertex({ instanced: true, crowd: true }), S.litFragment(this.preludeMain),
        { ...this.spot, ...this.crowdNear, uAlbedo: { value: new THREE.Vector3(0.035, 0.032, 0.034) }, uEmissive: { value: new THREE.Vector3() },
          uBeatPhase: { value: 0 }, uEnergy: { value: 0.6 } }, { side: THREE.DoubleSide }),
      ring: lit([0.12, 0.12, 0.13]),
      chain: lit([0.18, 0.18, 0.2], [0, 0, 0], { instanced: true }),
      cube: this._raw(S.CUBE_VERTEX, S.CUBE_FRAGMENT(this.preludeMain), {}),
      emit: this._raw(S.EMIT_VERTEX, S.EMIT_FRAGMENT, { ...this.view }, add),
      laser: this._raw(S.LASER_VERTEX, S.LASER_FRAGMENT(this.preludeMain),
        { ...this.view, ...this.haze, uLumPerWatt: { value: new THREE.Vector3(LUM_PER_WATT[0] * U, LUM_PER_WATT[1] * U, LUM_PER_WATT[2] * U) } },
        { ...add, side: THREE.DoubleSide }),
    };
    this.beamUniforms = { ...this.haze, uDepth: { value: null }, uRes: { value: new THREE.Vector2(1, 1) }, uNear: { value: 0.1 }, uFar: { value: 420 },
                          uCamFwd: { value: new THREE.Vector3(0, 0, -1) } };
    this.mat.beam = this._raw(S.BEAM_VERTEX, S.BEAM_FRAGMENT(this.preludeMain, this.q.beamSamples), this.beamUniforms,
                              { ...add, depthTest: false, side: THREE.BackSide });
    const fs = (frag, uniforms) => this._raw(S.FS_VERTEX, frag, uniforms, { depthTest: false, depthWrite: false });
    this.post = {
      composite: fs(S.COMPOSITE_FRAGMENT, { uScene: { value: null }, uBeams: { value: null }, uDepth: { value: null }, uRes: { value: new THREE.Vector2() },
                                            uVeil: { value: new THREE.Vector3() }, uSigma0: { value: 0.006 }, uNear: { value: 0.1 }, uFar: { value: 420 }, uBeamsOn: { value: 1 } }),
      down: fs(S.BLOOM_DOWN_FRAGMENT, { uSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uRes: { value: new THREE.Vector2() }, uKaris: { value: 0 }, uCeil: { value: 40 } }),
      up: this._raw(S.FS_VERTEX, S.BLOOM_UP_FRAGMENT, { uSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uRes: { value: new THREE.Vector2() }, uRadius: { value: 1 } },
                    { depthTest: false, depthWrite: false, transparent: true, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
                      blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor }),
      finish: fs(S.FINISH_FRAGMENT(this.preludeFinish), { uHdr: { value: null }, uBloom: { value: null }, uRes: { value: new THREE.Vector2() },
                                                         uBloomMix: { value: 0.06 }, uExposure: { value: 1 }, uEv: { value: 0 }, uCurve: { value: 0 },
                                                         uSat: { value: 1.08 }, uVig: { value: 0.22 } }),
      meter1: fs(S.METER1_FRAGMENT(this.preludeMain), { uSrc: { value: null }, uSrcSize: { value: new THREE.Vector2() } }),
      meter2: fs(S.METER2_FRAGMENT, { uSrc: { value: null }, uSrcSize: { value: new THREE.Vector2() } }),
      present: fs(S.PRESENT_FRAGMENT(this.preludeMain), { uSrc: { value: null }, uPrev: { value: null }, uA: { value: new Float32Array(16).fill(1) },
                                                         uB: { value: new Float32Array(16) }, uM2: { value: new THREE.Vector2(1, 1) }, uIdentity: { value: 1 } }),
    };
    // int uniforms: three infers the GL type from the program, a Vector2 value for an ivec2 is fine
  }

  // ------------------------------------------------------------------------------------------------ the scene --
  _build() {
    const rig = this.rig, V = rig.venue, world = this.world;
    const add = (geom, mat, name, group = "venue") => { const m = new THREE.Mesh(geom, mat); m.name = name; m.userData.group = group; m.frustumCulled = false; world.add(m); return m; };
    const fx = V.floor.x, fz = V.floor.z, roof = V.roof_y ?? 38;
    // the bowl: floor, three raked stands, the roof, the black drape behind the stage, the rigging grid
    const fl = new THREE.PlaneGeometry(fx[1] - fx[0], fz[1] - fz[0]); fl.rotateX(-Math.PI / 2); fl.translate(0, 0, (fz[0] + fz[1]) / 2);
    add(fl, this.mat.floor, "floor");
    const rake = (V.stands && V.stands.rake_deg || 30) * DEG, top = V.stands && V.stands.top_y || 30, run = top / Math.tan(rake), slope = Math.hypot(top, run);
    const standL = new THREE.PlaneGeometry(slope, fz[1] - fz[0] + 2 * run); standL.rotateY(Math.PI / 2); standL.rotateZ(-(Math.PI / 2 - rake));
    const sl = add(standL, this.mat.stand, "stand-l"); sl.position.set(fx[0] - run / 2, top / 2, (fz[0] + fz[1]) / 2 + run / 2);
    const standR = standL.clone(); const sr = add(standR, this.mat.stand, "stand-r"); sr.scale.x = -1; sr.position.set(fx[1] + run / 2, top / 2, (fz[0] + fz[1]) / 2 + run / 2);
    const standB = new THREE.PlaneGeometry(fx[1] - fx[0] + 2 * run, slope); standB.rotateX(-(Math.PI / 2 - rake));
    const sb = add(standB, this.mat.stand, "stand-b"); sb.position.set(0, top / 2, fz[1] + run / 2);
    const rf = new THREE.PlaneGeometry(fx[1] - fx[0] + 2 * run, fz[1] - fz[0] + 2 * run); rf.rotateX(Math.PI / 2);
    const rm = add(rf, this.mat.roof, "roof"); rm.position.set(0, roof, (fz[0] + fz[1]) / 2);
    const dr = new THREE.PlaneGeometry(fx[1] - fx[0] + 30, roof); const dm = add(dr, this.mat.drape, "drape"); dm.position.set(0, roof / 2, fz[0]);
    const grid = [];
    const gy = V.grid_y ?? 33;
    for (let x = -36; x <= 36; x += 6) grid.push({ geom: BOX, matrix: M4(x, gy, (fz[0] + fz[1]) / 2, 0, 0, 0, 0.35, 0.5, fz[1] - fz[0]) });
    for (let z = fz[0]; z <= fz[1]; z += 8) grid.push({ geom: BOX, matrix: M4(0, gy + 0.6, z, 0, 0, 0, fx[1] - fx[0], 0.35, 0.3) });
    add(mergeGeoms(grid), this.mat.trussStatic, "grid");
    // the deck, the DJ booth, the PA hangs, the laser and beam trusses, the side towers, FOH
    const deck = V.deck || { x: [-24, 24], z: [-16, 0], y: 2 };
    const statics = [
      { geom: BOX, matrix: M4(0, deck.y / 2, (deck.z[0] + deck.z[1]) / 2, 0, 0, 0, deck.x[1] - deck.x[0], deck.y, deck.z[1] - deck.z[0]) },
      { geom: BOX, matrix: M4(0, deck.y + 0.6, -4, 0, 0, 0, 3.0, 1.2, 1.4) },
    ];
    for (const x of [-22, -13, -5, 5, 13, 22]) statics.push({ geom: BOX, matrix: M4(x, 12, Math.abs(x) > 6 ? -1 : -2, 0, 0, 0, 1.3, 6, 1.4) });
    add(mergeGeoms(statics), this.mat.deck, "deck");
    const truss = [
      { geom: BOX, matrix: M4(0, 22.4, -2, 0, 0, 0, 40, 0.45, 0.45) },          // Bank A's truss
      { geom: BOX, matrix: M4(0, 26.5, -5, 0, 0, 0, 40, 0.5, 0.5) },            // the beam truss
      { geom: BOX, matrix: M4(-22, 8, -2, 0, 0, 0, 0.6, 16, 0.6) }, { geom: BOX, matrix: M4(22, 8, -2, 0, 0, 0, 0.6, 16, 0.6) },
      { geom: BOX, matrix: M4(0, 1.2, 50, 0, 0, 0, 8, 2.4, 5) },                // FOH riser
      { geom: BOX, matrix: M4(-12, 5, 30, 0, 0, 0, 0.6, 10, 0.6) }, { geom: BOX, matrix: M4(12, 5, 30, 0, 0, 0, 0.6, 10, 0.6) },
      { geom: BOX, matrix: M4(-12, 5, 55, 0, 0, 0, 0.6, 10, 0.6) }, { geom: BOX, matrix: M4(12, 5, 55, 0, 0, 0, 0.6, 10, 0.6) },
    ];
    add(mergeGeoms(truss), this.mat.trussStatic, "trusses");
    // the crowd: silhouettes on the floor (instanced), a third of them with raised arms that move with the beat
    const nCrowd = Math.round((V.crowd && V.crowd.drawn_floor || 6000) * this.q.crowd);
    const rnd = rngOf(this.rig.seed * 31 + 7);
    const people = new THREE.InstancedMesh(personGeometry(false), this.mat.person, nCrowd);
    const armsIdx = [];
    const m = new THREE.Matrix4();
    for (let i = 0; i < nCrowd; i++) {
      let x, z;
      do { x = -33 + 66 * rnd(); z = 3 + 80 * Math.pow(rnd(), 0.8); } while (Math.abs(x) < 5 && z > 46 && z < 54);
      const s = 0.9 + 0.2 * rnd();
      m.compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), (rnd() - 0.5) * 0.8), new THREE.Vector3(s, s, s));
      people.setMatrixAt(i, m);
      if (rnd() < 0.34) armsIdx.push([x, z, s, rnd()]);
    }
    people.frustumCulled = false; people.userData.group = "crowd"; world.add(people);
    const arms = new THREE.InstancedMesh(personGeometry(true), this.mat.arms, armsIdx.length);
    const crowdAttr = new Float32Array(armsIdx.length * 4);
    armsIdx.forEach(([x, z, s, ph], i) => {
      m.compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion(), new THREE.Vector3(s, s, s));
      arms.setMatrixAt(i, m);
      crowdAttr[i * 4] = ph; crowdAttr[i * 4 + 1] = 1;
    });
    arms.geometry.setAttribute("iCrowd", new THREE.InstancedBufferAttribute(crowdAttr, 4));
    arms.frustumCulled = false; arms.userData.group = "crowd"; world.add(arms);
    this.crowdCount = nCrowd;
    // the strand: rungs (instanced truss), cubes (instanced, lit from inside), hoist chains
    this.rungEls = rig.elements.map((e, i) => (e.id === "rung" ? i : -1)).filter((i) => i >= 0);
    this.rungMesh = new THREE.InstancedMesh(rungGeometry(), this.mat.truss, this.rungEls.length);
    this.rungMesh.frustumCulled = false; this.rungMesh.userData.group = "strand"; world.add(this.rungMesh);
    this.cubeFix = rig.fixtures.map((f, i) => (f.type === "cube-6" ? i : -1)).filter((i) => i >= 0);
    const cubeGeo = new THREE.BoxGeometry(1.1, 1.1, 1.1);
    this.cubeEmit = new Float32Array(this.cubeFix.length * 3);
    cubeGeo.setAttribute("iEmit", new THREE.InstancedBufferAttribute(this.cubeEmit, 3));
    this.cubeMesh = new THREE.InstancedMesh(cubeGeo, this.mat.cube, this.cubeFix.length);
    this.cubeMesh.frustumCulled = false; this.cubeMesh.userData.group = "strand"; world.add(this.cubeMesh);
    const chainGeo = new THREE.BoxGeometry(0.035, 1, 0.035); chainGeo.translate(0, 0.5, 0);
    this.chainMesh = new THREE.InstancedMesh(chainGeo, this.mat.chain, this.rungEls.length * 2);
    this.chainMesh.frustumCulled = false; this.chainMesh.userData.group = "strand"; world.add(this.chainMesh);
    // the rings' frames (static pose in v0)
    this.ringMeshes = [];
    for (let i = 0; i < rig.elements.length; i++) {
      const e = rig.elements[i];
      if (e.id !== "ring") continue;
      const mesh = new THREE.Mesh(ringGeometry(e.params.diameter / 2, e.params.depth), this.mat.ring);
      const em = elementMatrix(e);
      mesh.matrixAutoUpdate = false;
      mesh.matrix.set(em[0], em[1], em[2], em[9], em[3], em[4], em[5], em[10], em[6], em[7], em[8], em[11], 0, 0, 0, 1);
      mesh.userData.group = "rings"; mesh.frustumCulled = false;
      world.add(mesh);
      this.ringMeshes.push(mesh);
    }
    // the fixtures' bodies: a base, and a head that follows pan and tilt
    const nH = rig.heads.length;
    this.baseMesh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.42, 0.16, 0.42), this.mat.body, nH);
    const headGeo = new THREE.CylinderGeometry(0.13, 0.15, 0.42, 12); headGeo.translate(0, -0.05, 0);
    this.headMesh = new THREE.InstancedMesh(headGeo, this.mat.body, nH);
    for (const mm of [this.baseMesh, this.headMesh]) { mm.frustumCulled = false; mm.userData.group = "venue"; world.add(mm); }
    // the emitters: strand and ring cells (not the cubes), the lenses, the laser dots
    const cells = rig.cells;
    this.emitCells = [];
    for (let c = 0; c < cells.n; c++) if (cells.kind[c] !== CELL_KIND.cube) this.emitCells.push(c);
    this.nEmitCells = this.emitCells.length;
    this.maxEmit = this.nEmitCells + nH + 512 + 32;
    const quad = new THREE.BufferGeometry();
    quad.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
    quad.setIndex([0, 1, 2, 0, 2, 3]);
    const eg = new THREE.InstancedBufferGeometry();
    eg.index = quad.index; eg.setAttribute("position", quad.attributes.position);
    this.ePos = new Float32Array(this.maxEmit * 3); this.eCol = new Float32Array(this.maxEmit * 3); this.eSize = new Float32Array(this.maxEmit);
    eg.setAttribute("iPos", new THREE.InstancedBufferAttribute(this.ePos, 3));
    eg.setAttribute("iCol", new THREE.InstancedBufferAttribute(this.eCol, 3));
    eg.setAttribute("iSize", new THREE.InstancedBufferAttribute(this.eSize, 1));
    eg.instanceCount = 0;
    this.emitGeo = eg;
    this.emitMesh = new THREE.Mesh(eg, this.mat.emit); this.emitMesh.frustumCulled = false; this.emitMesh.renderOrder = 10;
    this.emitMesh.userData.group = "emitters"; world.add(this.emitMesh);
    // the per-cell constants: kind luminance (nits) and the element each cell rides
    this.cellNits = new Float32Array(cells.n);
    for (let c = 0; c < cells.n; c++) {
      const f = rig.fixtures[cells.fixture[c]];
      this.cellNits[c] = (rig.types[f.type].nits || 10000) * U;
    }
    // the lasers: instanced ribbons
    const lq = new THREE.BufferGeometry();
    lq.setAttribute("position", new THREE.Float32BufferAttribute([0, -1, 0, 1, -1, 0, 1, 1, 0, 0, 1, 0], 3));
    lq.setIndex([0, 1, 2, 0, 2, 3]);
    const lg = new THREE.InstancedBufferGeometry();
    lg.index = lq.index; lg.setAttribute("position", lq.attributes.position);
    this.lA = new Float32Array(512 * 3); this.lB = new Float32Array(512 * 3); this.lPow = new Float32Array(512 * 3); this.lMisc = new Float32Array(512 * 3);
    lg.setAttribute("iA", new THREE.InstancedBufferAttribute(this.lA, 3)); lg.setAttribute("iB", new THREE.InstancedBufferAttribute(this.lB, 3));
    lg.setAttribute("iPow", new THREE.InstancedBufferAttribute(this.lPow, 3)); lg.setAttribute("iMisc", new THREE.InstancedBufferAttribute(this.lMisc, 3));
    lg.instanceCount = 0;
    this.laserGeo = lg;
    this.laserMesh = new THREE.Mesh(lg, this.mat.laser); this.laserMesh.frustumCulled = false; this.laserMesh.renderOrder = 11;
    this.laserMesh.userData.group = "lasers"; world.add(this.laserMesh);
    // the wide beams: one cone proxy per head, in their own scene
    const cone = new THREE.BufferGeometry();
    const seg = 16, cp = [], ci = [];
    for (const s of [0, 1]) for (let k = 0; k < seg; k++) { const a = (k / seg) * Math.PI * 2; cp.push(Math.cos(a), Math.sin(a), s); }
    cp.push(0, 0, 0);                  // the apex
    cp.push(0, 0, 1);                  // the far cap's centre
    for (let k = 0; k < seg; k++) {
      const k1 = (k + 1) % seg;
      ci.push(k, seg + k1, seg + k, k, k1, seg + k1);   // outward-facing sides: BackSide then draws the far wall
      ci.push(2 * seg, k1, k); ci.push(2 * seg + 1, seg + k, seg + k1);
    }
    cone.setAttribute("position", new THREE.Float32BufferAttribute(cp, 3));
    cone.setIndex(ci);
    const bg = new THREE.InstancedBufferGeometry();
    bg.index = cone.index; bg.setAttribute("position", cone.attributes.position);
    this.bApex = new Float32Array(nH * 3); this.bAxis = new Float32Array(nH * 3); this.bShape = new Float32Array(nH * 3);
    this.bLenN = new Float32Array(nH * 2); this.bCol = new Float32Array(nH * 3);
    bg.setAttribute("iApex", new THREE.InstancedBufferAttribute(this.bApex, 3)); bg.setAttribute("iAxis", new THREE.InstancedBufferAttribute(this.bAxis, 3));
    bg.setAttribute("iShape", new THREE.InstancedBufferAttribute(this.bShape, 3)); bg.setAttribute("iLenN", new THREE.InstancedBufferAttribute(this.bLenN, 2));
    bg.setAttribute("iCol", new THREE.InstancedBufferAttribute(this.bCol, 3));
    bg.instanceCount = 0;
    this.beamGeo = bg;
    this.beamMesh = new THREE.Mesh(bg, this.mat.beam); this.beamMesh.frustumCulled = false;
    this.beamScene.add(this.beamMesh);
    // per-head constants
    this.headConst = rig.heads.map((fi) => {
      const t = rig.types[rig.fixtures[fi].type];
      const fob = (t.beam && t.beam.field_over_beam) || 1.15;
      return { flux: (t.beam && t.beam.flux_lm) || 10000, lens: (t.beam && t.beam.lens_radius) || 0.07, fob,
               n: Math.log(Math.log(0.1) / Math.log(0.5)) / Math.log(fob) };
    });
    this.headOut = rig.heads.map(() => ({ lens: [0, 0, 0], dir: [0, 1, 0] }));
    this.elM = rig.elements.map((e) => elementMatrix(e));
  }

  // ------------------------------------------------------------------------------------------- render targets --
  resize(w, h) {
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    this.renderer.setSize(w, h, false);
    for (const t of this.targets || []) t.dispose();
    const hf = { type: THREE.HalfFloatType, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, depthBuffer: false };
    const depthTexture = new THREE.DepthTexture(w, h);
    depthTexture.minFilter = THREE.NearestFilter; depthTexture.magFilter = THREE.NearestFilter;
    this.sceneRT = new THREE.WebGLRenderTarget(w, h, { ...hf, depthBuffer: true, depthTexture, samples: this.q.msaa });
    const bw = Math.max(1, Math.round(w * this.q.beamScale)), bh = Math.max(1, Math.round(h * this.q.beamScale));
    this.beamRT = new THREE.WebGLRenderTarget(bw, bh, hf);
    this.hdrRT = new THREE.WebGLRenderTarget(w, h, hf);
    this.bloom = [];
    let mw = w, mh = h;
    for (let i = 0; i < this.q.bloomLevels; i++) { mw = Math.max(1, mw >> 1); mh = Math.max(1, mh >> 1); this.bloom.push(new THREE.WebGLRenderTarget(mw, mh, hf)); }
    const ldr = { type: THREE.UnsignedByteType, format: THREE.RGBAFormat, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false, depthBuffer: false };
    this.ldrRT = new THREE.WebGLRenderTarget(w, h, ldr);
    this.shownRT = [new THREE.WebGLRenderTarget(w, h, ldr), new THREE.WebGLRenderTarget(w, h, ldr)];
    this.shownIdx = 0;
    const fl = { type: THREE.FloatType, format: THREE.RGBAFormat, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false, depthBuffer: false };
    this.m1w = Math.ceil(w / 4); this.m1h = Math.ceil(h / 4); this.m2w = Math.ceil(this.m1w / 4); this.m2h = Math.ceil(this.m1h / 4);
    this.meter1RT = new THREE.WebGLRenderTarget(this.m1w, this.m1h, fl);
    this.meter2RT = new THREE.WebGLRenderTarget(this.m2w, this.m2h, fl);
    this.meterBuf = new Float32Array(this.m2w * this.m2h * 4);
    this.targets = [this.sceneRT, this.beamRT, this.hdrRT, ...this.bloom, this.ldrRT, ...this.shownRT, this.meter1RT, this.meter2RT];
    this.camera.aspect = w / h;
  }

  _fs(material, target, clear = false) {
    this.fsMesh.material = material;
    this.renderer.setRenderTarget(target);
    if (clear) this.renderer.clear(true, false, false);
    this.renderer.render(this.fsScene, this.fsCam);
  }
  // Pass timings (profile mode only). gl.finish() does not wait on SwiftShader (ANGLE defers the work to the next sync
  // point), so each pass is fenced by a readback that DEPENDS on its output: a 1 x 1 pass samples the pass's texture into
  // an 8-bit target, and reading that pixel back cannot return before the pass has finished.
  _fenceOn(tex) {
    if (!this.fenceRT) {
      this.fenceRT = new THREE.WebGLRenderTarget(1, 1, { type: THREE.UnsignedByteType, depthBuffer: false });
      this.fenceMat = this._raw(S.FS_VERTEX, S.FENCE_FRAGMENT, { uSrc: { value: null } }, { depthTest: false, depthWrite: false });
      this.fenceBuf = new Uint8Array(4);
    }
    if (!tex) { this.gl.readPixels(0, 0, 1, 1, this.gl.RGBA, this.gl.UNSIGNED_BYTE, this.fenceBuf); return; }
    this.fenceMat.uniforms.uSrc.value = tex;
    this._fs(this.fenceMat, this.fenceRT);
    this.renderer.readRenderTargetPixels(this.fenceRT, 0, 0, 1, 1, this.fenceBuf);
  }
  _t(name, fn, out = null) {
    if (!this.profile) { fn(); return; }
    const t0 = realNow();
    fn();
    this._fenceOn(typeof out === "function" ? out() : out);
    const ms = realNow() - t0;
    const r = this.timings[name] || (this.timings[name] = { n: 0, sum: 0, max: 0, list: [] });
    r.n++; r.sum += ms; r.max = Math.max(r.max, ms);
    if (r.list.length < 600) r.list.push(ms);
  }

  // ------------------------------------------------------------------------------------------------- one frame --
  // fs: {camera {pos, look, hfov, roll, ev}, poses [{y, roll}] per rung, heads (programmer), pixels (programmer),
  //      lasers {seg, n} (lasers3d), medium (atmos uniform), veil [r, g, b], beatPhase, energy}
  // limiter: (cells, t) -> {a, k, beta}; t: seconds
  render(fs, limiter, tSec) {
    const rig = this.rig, cam = this.camera, F = this.features;
    const w = this.w, h = this.h;
    // the camera
    const c = fs.camera;
    cam.position.set(c.pos[0], c.pos[1], c.pos[2]);
    const dx = c.look[0] - c.pos[0], dy = c.look[1] - c.pos[1], dz = c.look[2] - c.pos[2];
    const dl = Math.hypot(dx, dy, dz) || 1;
    if (Math.abs(dy / dl) > 0.985) {
      const hx = c.pos[0] - (c.orbitCentre ? c.orbitCentre[0] : c.look[0]), hz = c.pos[2] - (c.orbitCentre ? c.orbitCentre[2] : c.look[2]);
      const hl = Math.hypot(hx, hz) || 1;
      cam.up.set(-hx / hl, 0, -hz / hl);
    } else cam.up.set(0, 1, 0);
    cam.lookAt(c.look[0], c.look[1], c.look[2]);
    if (c.roll) cam.rotateZ(c.roll * DEG);
    cam.fov = vfovOf(c.hfov, w / h);
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
    const pixAngle = (2 * Math.tan((cam.fov * DEG) / 2)) / h;
    this.view.uPixAngle.value = pixAngle;
    this.view.uRes.value.set(w, h);
    const fwd = new THREE.Vector3(); cam.getWorldDirection(fwd);
    // the medium
    const md = fs.medium;
    this.haze.uSigma0.value = md.sigma0; this.haze.uSigmaAvg.value = md.sigma0; this.haze.uNoiseAmp.value = md.noiseAmp;
    this.haze.uWind.value.set(md.wind[0], md.wind[1], md.wind[2]); this.haze.uG.value = md.g;
    this.haze.uHazer.value.set(md.hazers); this.haze.uHazerSigma.value.set(md.hazerSigma);
    // element matrices: the rungs move, the rest is static
    for (let k = 0; k < this.rungEls.length; k++) {
      const ei = this.rungEls[k], p = fs.poses[k];
      elementMatrix(rig.elements[ei], p, this.elM[ei]);
      const em = this.elM[ei];
      const m4 = new THREE.Matrix4().set(em[0], em[1], em[2], em[9], em[3], em[4], em[5], em[10], em[6], em[7], em[8], em[11], 0, 0, 0, 1);
      this.rungMesh.setMatrixAt(k, m4);
      // chains from the pickups to the grid
      for (let s = 0; s < 2; s++) {
        const pp = transformPoint(em, [s ? 4.3 : -4.3, 0.66, 0]);
        const len = Math.max(0.1, (rig.venue.grid_y ?? 33) - pp[1]);
        this.chainMesh.setMatrixAt(k * 2 + s, new THREE.Matrix4().compose(new THREE.Vector3(pp[0], pp[1], pp[2]), new THREE.Quaternion(), new THREE.Vector3(1, len, 1)));
      }
    }
    this.rungMesh.instanceMatrix.needsUpdate = true; this.chainMesh.instanceMatrix.needsUpdate = true;
    // the cubes: pose, and the mean of their six cells as their light
    for (let k = 0; k < this.cubeFix.length; k++) {
      const f = rig.fixtures[this.cubeFix[k]];
      const em = this.elM[f.element];
      const p = transformPoint(em, f.local);
      const m4 = new THREE.Matrix4().set(em[0], em[1], em[2], p[0], em[3], em[4], em[5], p[1], em[6], em[7], em[8], p[2], 0, 0, 0, 1);
      this.cubeMesh.setMatrixAt(k, m4);
      let r = 0, g = 0, b = 0;
      for (let cI = f.cell0; cI < f.cell0 + f.ncell; cI++) { r += fs.pixels[cI * 4]; g += fs.pixels[cI * 4 + 1]; b += fs.pixels[cI * 4 + 2]; }
      const kk = this.cellNits[f.cell0] / f.ncell;
      this.cubeEmit[k * 3] = r * kk; this.cubeEmit[k * 3 + 1] = g * kk; this.cubeEmit[k * 3 + 2] = b * kk;
    }
    this.cubeMesh.instanceMatrix.needsUpdate = true; this.cubeMesh.geometry.attributes.iEmit.needsUpdate = true;
    // the heads: lens and direction, beams, spot lights, bodies, lens glints
    const nH = rig.heads.length;
    let nb = 0, ns = 0;
    const sp = this.spot, toCam = [0, 0, 0];
    let ePtr = this.nEmitCells;
    let beamPower = 0;
    const veil = [0, 0, 0];
    for (let i = 0; i < nH; i++) {
      const fi = rig.heads[i], f = rig.fixtures[fi], o = i * HEAD_FLOATS, hc = this.headConst[i];
      const ho = headPose(this.elM[f.element], f, fs.heads[o + H.PAN], fs.heads[o + H.TILT], this.headOut[i]);
      const dim = fs.heads[o + H.DIM];
      const half = (fs.heads[o + H.ZOOM] / 2) * DEG;
      const tanB = Math.tan(half), tanF = Math.tan(half * hc.fob);
      const I0 = hc.flux / (Math.PI * tanB * tanB);                       // cd on the axis (the profile's integral ~ pi tan^2)
      const cr = fs.heads[o + H.R], cg = fs.heads[o + H.G], cb = fs.heads[o + H.B];
      // bodies
      const base = transformPoint(this.elM[f.element], f.local);
      const em = this.elM[f.element];
      const hung = Math.abs(f.rot[0]) > 90;
      this.baseMesh.setMatrixAt(i, new THREE.Matrix4().compose(new THREE.Vector3(base[0], base[1] + (hung ? 0.05 : -0.05), base[2]),
        new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().set(em[0], em[1], em[2], 0, em[3], em[4], em[5], 0, em[6], em[7], em[8], 0, 0, 0, 0, 1)), new THREE.Vector3(1, 1, 1)));
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(ho.dir[0], ho.dir[1], ho.dir[2]));
      this.headMesh.setMatrixAt(i, new THREE.Matrix4().compose(new THREE.Vector3(ho.lens[0] - ho.dir[0] * 0.16, ho.lens[1] - ho.dir[1] * 0.16, ho.lens[2] - ho.dir[2] * 0.16), q, new THREE.Vector3(1, 1, 1)));
      // the lens as an emitter: blinding on the axis, a glint from the side
      toCam[0] = c.pos[0] - ho.lens[0]; toCam[1] = c.pos[1] - ho.lens[1]; toCam[2] = c.pos[2] - ho.lens[2];
      const dc = Math.hypot(toCam[0], toCam[1], toCam[2]) || 1;
      const cosA = (toCam[0] * ho.dir[0] + toCam[1] * ho.dir[1] + toCam[2] * ho.dir[2]) / dc;
      const ang = Math.acos(Math.max(-1, Math.min(1, cosA)));
      const prof = Math.pow(2, -Math.pow(Math.tan(ang) / Math.max(tanB, 1e-4), hc.n)) * (cosA > 0 ? 1 : 0);
      const lensL = Math.min(4000, (dim * I0 * (prof + 0.00005) * U) / (Math.PI * hc.lens * hc.lens));
      this.ePos[ePtr * 3] = ho.lens[0]; this.ePos[ePtr * 3 + 1] = ho.lens[1]; this.ePos[ePtr * 3 + 2] = ho.lens[2];
      this.eCol[ePtr * 3] = cr * lensL; this.eCol[ePtr * 3 + 1] = cg * lensL; this.eCol[ePtr * 3 + 2] = cb * lensL;
      this.eSize[ePtr] = hc.lens; ePtr++;
      if (dim <= 1e-4) continue;
      // the beam's length: to the first surface of the room
      const hit = roomHit(ho.lens, ho.dir, rig.venue);
      const len = Math.min(Number.isFinite(hit.t) ? hit.t : 150, 150);
      // the camera inside the cone, or within 2 m of its edge: fade the beam to 15 % (a camera crew never shoots from inside
      // a beam; in 3D a flythrough would otherwise wipe the frame white each time it crossed one)
      const ah = (c.pos[0] - ho.lens[0]) * ho.dir[0] + (c.pos[1] - ho.lens[1]) * ho.dir[1] + (c.pos[2] - ho.lens[2]) * ho.dir[2];
      let inBeam = 1;
      if (ah > 0 && ah < len) {
        const ax = c.pos[0] - ho.lens[0] - ho.dir[0] * ah, ay = c.pos[1] - ho.lens[1] - ho.dir[1] * ah, az = c.pos[2] - ho.lens[2] - ho.dir[2] * ah;
        const edge = Math.hypot(ax, ay, az) - (hc.lens + ah * tanF * 1.35);
        inBeam = Math.min(1, Math.max(0.15, 0.15 + 0.85 * (edge / 2)));
        if (inBeam < 1) this.inBeamFaded = (this.inBeamFaded || 0) + 1;
      }
      const Ic = dim * I0 * U * inBeam;
      this.bApex.set(ho.lens, nb * 3); this.bAxis.set(ho.dir, nb * 3);
      this.bShape[nb * 3] = tanB; this.bShape[nb * 3 + 1] = tanF; this.bShape[nb * 3 + 2] = hc.lens;
      this.bLenN[nb * 2] = len; this.bLenN[nb * 2 + 1] = hc.n;
      this.bCol[nb * 3] = cr * Ic; this.bCol[nb * 3 + 1] = cg * Ic; this.bCol[nb * 3 + 2] = cb * Ic;
      nb++;
      beamPower += dim * hc.flux;
      veil[0] += cr * dim * hc.flux; veil[1] += cg * dim * hc.flux; veil[2] += cb * dim * hc.flux;
      if (ns < S.MAX_SPOTS) {
        sp.uSpotPos.value.set(ho.lens, ns * 3); sp.uSpotDir.value.set(ho.dir, ns * 3);
        sp.uSpotCol.value[ns * 3] = cr * Ic; sp.uSpotCol.value[ns * 3 + 1] = cg * Ic; sp.uSpotCol.value[ns * 3 + 2] = cb * Ic;
        sp.uSpotShape.value[ns * 3] = tanB; sp.uSpotShape.value[ns * 3 + 1] = hc.lens; sp.uSpotShape.value[ns * 3 + 2] = hc.n;
        ns++;
      }
    }
    sp.uNSpot.value = ns;
    this.beamGeo.instanceCount = F.beams ? nb : 0;
    for (const k of ["iApex", "iAxis", "iShape", "iLenN", "iCol"]) this.beamGeo.attributes[k].needsUpdate = true;
    this.baseMesh.instanceMatrix.needsUpdate = true; this.headMesh.instanceMatrix.needsUpdate = true;
    // the LED cells
    const cells = rig.cells;
    let pixPower = [0, 0, 0];
    for (let j = 0; j < this.nEmitCells; j++) {
      const cI = this.emitCells[j];
      const em = this.elM[cells.element[cI]];
      const lx = cells.pos[cI * 3], ly = cells.pos[cI * 3 + 1], lz = cells.pos[cI * 3 + 2];
      this.ePos[j * 3] = em[0] * lx + em[1] * ly + em[2] * lz + em[9];
      this.ePos[j * 3 + 1] = em[3] * lx + em[4] * ly + em[5] * lz + em[10];
      this.ePos[j * 3 + 2] = em[6] * lx + em[7] * ly + em[8] * lz + em[11];
      const k = this.cellNits[cI];
      const r = fs.pixels[cI * 4], g = fs.pixels[cI * 4 + 1], b = fs.pixels[cI * 4 + 2];
      this.eCol[j * 3] = r * k; this.eCol[j * 3 + 1] = g * k; this.eCol[j * 3 + 2] = b * k;
      this.eSize[j] = cells.size[cI];
      pixPower[0] += r; pixPower[1] += g; pixPower[2] += b;
    }
    // the lasers: ribbons, and a dot where each ends on a surface
    const L = fs.lasers;
    let nl = 0;
    if (L && F.lasers) {
      for (let s = 0; s < L.n && nl < 512; s++) {
        const b = s * L3_FLOATS, seg = L.seg;
        this.lA[nl * 3] = seg[b + L3.OX]; this.lA[nl * 3 + 1] = seg[b + L3.OY]; this.lA[nl * 3 + 2] = seg[b + L3.OZ];
        this.lB[nl * 3] = seg[b + L3.EX]; this.lB[nl * 3 + 1] = seg[b + L3.EY]; this.lB[nl * 3 + 2] = seg[b + L3.EZ];
        this.lPow[nl * 3] = seg[b + L3.PR]; this.lPow[nl * 3 + 1] = seg[b + L3.PG]; this.lPow[nl * 3 + 2] = seg[b + L3.PB];
        this.lMisc[nl * 3] = seg[b + L3.W0]; this.lMisc[nl * 3 + 1] = seg[b + L3.DIV]; this.lMisc[nl * 3 + 2] = seg[b + L3.DIST0];
        nl++;
        if ((seg[b + L3.FLAGS] & 1) && ePtr < this.maxEmit) {
          // a diffuse dot: the beam's power spread over its spot, seen at albedo 0.3
          const dist = Math.hypot(seg[b + L3.EX] - seg[b + L3.OX], seg[b + L3.EY] - seg[b + L3.OY], seg[b + L3.EZ] - seg[b + L3.OZ]) + seg[b + L3.DIST0];
          const rad = Math.max(0.01, (seg[b + L3.W0] + seg[b + L3.DIV] * dist) / 2);
          const k = (0.3 / Math.PI) / (Math.PI * rad * rad) * U;
          this.ePos[ePtr * 3] = seg[b + L3.EX]; this.ePos[ePtr * 3 + 1] = seg[b + L3.EY] + 0.02; this.ePos[ePtr * 3 + 2] = seg[b + L3.EZ];
          this.eCol[ePtr * 3] = Math.min(6e4, seg[b + L3.PR] * LUM_PER_WATT[0] * k); this.eCol[ePtr * 3 + 1] = Math.min(6e4, seg[b + L3.PG] * LUM_PER_WATT[1] * k);
          this.eCol[ePtr * 3 + 2] = Math.min(6e4, seg[b + L3.PB] * LUM_PER_WATT[2] * k);
          this.eSize[ePtr] = rad; ePtr++;
        }
      }
    }
    this.laserGeo.instanceCount = nl;
    for (const k of ["iA", "iB", "iPow", "iMisc"]) this.laserGeo.attributes[k].needsUpdate = true;
    this.emitGeo.instanceCount = F.emitters ? ePtr : 0;
    for (const k of ["iPos", "iCol", "iSize"]) this.emitGeo.attributes[k].needsUpdate = true;
    // the veil: the room's light scattered back by the haze (the beams' flux and the LEDs, tinted)
    const amb = fs.ambient || [0.23, 0.1, 0.55];
    const vk = 0.5e-6 * U, pk = 0.0006 * U;
    this.post.composite.uniforms.uVeil.value.set(
      F.veil ? (veil[0] * vk + pixPower[0] * pk) * 0.6 + amb[0] * 0.02 : 0,
      F.veil ? (veil[1] * vk + pixPower[1] * pk) * 0.6 + amb[1] * 0.02 : 0,
      F.veil ? (veil[2] * vk + pixPower[2] * pk) * 0.6 + amb[2] * 0.02 : 0);
    this.post.composite.uniforms.uSigma0.value = md.sigma0;
    sp.uAmbient.value.set(0.004 + amb[0] * 0.01, 0.004 + amb[1] * 0.01, 0.006 + amb[2] * 0.01);
    this.mat.arms.uniforms.uBeatPhase.value = fs.beatPhase || 0;
    this.mat.arms.uniforms.uEnergy.value = fs.energy ?? 0.6;
    // visibility of the groups
    for (const o of this.world.children) {
      const g = o.userData.group;
      if (g) o.visible = F[g] !== false;
    }
    const R = this.renderer;
    R.info.reset();
    // 1. the opaque scene, emitters and lasers
    this._t("scene", () => {
      R.setRenderTarget(this.sceneRT);
      R.setClearColor(0x000000, 1);
      R.clear(true, true, false);
      R.render(this.world, cam);
    }, () => this.sceneRT.texture);
    // 2. the wide beams
    this._t("beams", () => {
      R.setRenderTarget(this.beamRT);
      R.clear(true, false, false);
      if (F.beams && nb > 0) {
        const bu = this.beamUniforms;
        bu.uDepth.value = this.sceneRT.depthTexture;
        bu.uRes.value.set(this.beamRT.width, this.beamRT.height);
        bu.uNear.value = cam.near; bu.uFar.value = cam.far;
        bu.uCamFwd.value.copy(fwd);
        R.render(this.beamScene, cam);
      }
    }, () => this.beamRT.texture);
    // 3. composite
    this._t("composite", () => {
      const u = this.post.composite.uniforms;
      u.uScene.value = this.sceneRT.texture; u.uBeams.value = this.beamRT.texture; u.uDepth.value = this.sceneRT.depthTexture;
      u.uRes.value.set(w, h); u.uNear.value = cam.near; u.uFar.value = cam.far; u.uBeamsOn.value = F.beams ? 1 : 0;
      this._fs(this.post.composite, this.hdrRT);
    }, () => this.hdrRT.texture);
    // 4. bloom and the finish
    this._t("bloom", () => {
      const d = this.post.down.uniforms, up = this.post.up.uniforms;
      let src = this.hdrRT;
      for (let i = 0; i < this.bloom.length; i++) {
        d.uSrc.value = src.texture; d.uTexel.value.set(1 / src.width, 1 / src.height); d.uRes.value.set(this.bloom[i].width, this.bloom[i].height);
        d.uKaris.value = i === 0 ? 1 : 0;
        d.uCeil.value = i === 0 ? 40 : 1e9;
        this._fs(this.post.down, this.bloom[i]);
        src = this.bloom[i];
      }
      for (let i = this.bloom.length - 2; i >= 0; i--) {
        const s2 = this.bloom[i + 1];
        up.uSrc.value = s2.texture; up.uTexel.value.set(1 / s2.width, 1 / s2.height); up.uRes.value.set(this.bloom[i].width, this.bloom[i].height);
        up.uRadius.value = 1.0;
        this._fs(this.post.up, this.bloom[i]);
      }
    }, () => this.bloom[0].texture);
    this._t("finish", () => {
      const u = this.post.finish.uniforms;
      u.uHdr.value = this.hdrRT.texture; u.uBloom.value = this.bloom[0].texture; u.uRes.value.set(w, h);
      u.uBloomMix.value = F.bloom ? (fs.bloomMix ?? 0.05) / Math.max(1, this.bloom.length) * this.bloom.length / 6 : 0;
      u.uEv.value = (c.ev || 0) + (fs.ev || 0);
      this._fs(this.post.finish, this.ldrRT);
    }, () => this.ldrRT.texture);
    // 5. the meter, the limiter, the apply pass
    let gains = { a: 1, b: 0, cellA: new Float64Array(16).fill(1), cellB: new Float64Array(16) };
    this._t("meter", () => {
      const m1 = this.post.meter1.uniforms, m2 = this.post.meter2.uniforms;
      m1.uSrc.value = this.ldrRT.texture; m1.uSrcSize.value.set(w, h);
      this._fs(this.post.meter1, this.meter1RT);
      m2.uSrc.value = this.meter1RT.texture; m2.uSrcSize.value.set(this.m1w, this.m1h);
      this._fs(this.post.meter2, this.meter2RT);
      R.readRenderTargetPixels(this.meter2RT, 0, 0, this.m2w, this.m2h, this.meterBuf);
      const Lc = this.cells.L, Rc = this.cells.R, cnt = new Float64Array(16);
      Lc.fill(0); Rc.fill(0);
      // the cells are the meter's own: 16-pixel blocks shared out four ways (the apply pass maps pixels the same way)
      for (let y = 0; y < this.m2h; y++) {
        const cy = Math.min(3, Math.floor((y * 4) / this.m2h));
        for (let x = 0; x < this.m2w; x++) {
          const cx = Math.min(3, Math.floor((x * 4) / this.m2w));
          const i = (y * this.m2w + x) * 4, ci = cy * 4 + cx;
          Lc[ci] += this.meterBuf[i]; Rc[ci] += this.meterBuf[i + 1]; cnt[ci] += this.meterBuf[i + 2];
        }
      }
      for (let i = 0; i < 16; i++) { Lc[i] /= Math.max(1, cnt[i]); Rc[i] /= Math.max(1, cnt[i]); }
      if (limiter) gains = limiter(this.cells, tSec);
    });
    this._t("present", () => {
      const p = this.post.present.uniforms;
      let identity = true;
      for (let i = 0; i < 16 && identity; i++) if (gains.cellA[i] !== 1 || gains.cellB[i] !== 0) identity = false;
      p.uSrc.value = this.ldrRT.texture; p.uPrev.value = this.shownRT[this.shownIdx].texture;
      p.uA.value.set(gains.cellA); p.uB.value.set(gains.cellB); p.uM2.value.set(this.m2w, this.m2h);
      p.uIdentity.value = identity ? 1 : 0;
      const next = 1 - this.shownIdx;
      this._fs(this.post.present, this.shownRT[next]);
      this._fs(this.post.present, null);
      this.shownIdx = next;
    }, () => this.shownRT[this.shownIdx].texture);
    this.info = { beams: nb, spots: ns, lasers: nl, emitters: ePtr, crowd: this.crowdCount, drawCalls: R.info.render.calls,
                  triangles: R.info.render.triangles, beamPowerLm: Math.round(beamPower), gains: { a: gains.a, b: gains.b } };
    return this.info;
  }

  // For receipts: the mean of a 9 x 9 grid of samples from each target of the last frame (scene, beams, composite, finish).
  debugTargets() {
    const R = this.renderer, out = {};
    const read = (rt, float) => {
      const half = float && rt.texture.type === THREE.HalfFloatType;
      const buf = half ? new Uint16Array(4) : float ? new Float32Array(4) : new Uint8Array(4);
      let s = [0, 0, 0], n = 0, nan = 0;
      for (let j = 1; j <= 9; j++) for (let i = 1; i <= 9; i++) {
        const x = Math.floor((rt.width * i) / 10), y = Math.floor((rt.height * j) / 10);
        try { R.readRenderTargetPixels(rt, x, y, 1, 1, buf); } catch { return { error: "unreadable" }; }
        for (let k = 0; k < 3; k++) { const v = half ? THREE.DataUtils.fromHalfFloat(buf[k]) : Number(buf[k]); if (!Number.isFinite(v)) nan++; else s[k] += v; }
        n++;
      }
      return { mean: s.map((v) => +(v / n).toFixed(4)), nonfinite: nan };
    };
    out.hdr = read(this.hdrRT, true);
    out.beams = read(this.beamRT, true);
    out.ldr = read(this.ldrRT, false);
    out.camera = { pos: this.camera.position.toArray().map((v) => +v.toFixed(2)), up: this.camera.up.toArray().map((v) => +v.toFixed(3)),
                   quat: this.camera.quaternion.toArray().map((v) => +v.toFixed(4)), fov: +this.camera.fov.toFixed(2) };
    return out;
  }

  // The fragment count of each pass's geometry this frame, for the op-count estimate: an overdraw count of the beam
  // proxies (at the beam target's size), the laser ribbons and the emitters (full size), read back and summed.
  overdraw() {
    const R = this.renderer;
    const rt = new THREE.WebGLRenderTarget(this.w, this.h, { type: THREE.FloatType, format: THREE.RGBAFormat, depthBuffer: false });
    const brt = new THREE.WebGLRenderTarget(this.beamRT.width, this.beamRT.height, { type: THREE.FloatType, format: THREE.RGBAFormat, depthBuffer: false });
    const count = new THREE.RawShaderMaterial({ glslVersion: THREE.GLSL3, transparent: true, depthTest: false, depthWrite: false,
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, side: THREE.DoubleSide,
      vertexShader: "", fragmentShader: "precision highp float;\nout vec4 fragColor;\nvoid main(){ fragColor = vec4(1.0); }" });
    const res = {};
    const measure = (mesh, target, side) => {
      const saved = mesh.material;
      const m = count.clone();
      m.vertexShader = saved.vertexShader; m.uniforms = saved.uniforms; m.side = side ?? saved.side;
      mesh.material = m;
      R.setRenderTarget(target); R.setClearColor(0x000000, 1); R.clear(true, false, false);
      const sc = new THREE.Scene(); const parent = mesh.parent; sc.add(mesh);
      R.render(sc, this.camera);
      parent.add(mesh);
      mesh.material = saved;
      const buf = new Float32Array(target.width * target.height * 4);
      R.readRenderTargetPixels(target, 0, 0, target.width, target.height, buf);
      let s = 0; for (let i = 0; i < buf.length; i += 4) s += buf[i];
      m.dispose();
      return s;
    };
    res.beams_frags = measure(this.beamMesh, brt, THREE.BackSide);
    res.laser_frags = measure(this.laserMesh, rt);
    res.emit_frags = measure(this.emitMesh, rt);
    res.beam_target = [this.beamRT.width, this.beamRT.height];
    rt.dispose(); brt.dispose(); count.dispose();
    return res;
  }
}
