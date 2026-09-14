// -------------------------------------------------------------- spectacle --
// LAB ONLY (piano-lab-vfx). Rarity tiers for musical moments; each tier is a stack of stage effects that escalates:
//   0 Common     a colour pulse along the rail
//   1 Uncommon   two rail pulses and a small ember lift
//   2 Rare       + a floor shockwave, a spark fountain, a shimmer band up the chord's columns, the banner
//   3 Epic       + light shafts, a second ring, a small camera push, old columns dimmed a little
//   4 Legendary  gold: three rings, a gold fountain, gold shafts, an aurora curtain, a dispersion shimmer, the chord
//                name in gold foil, a camera push, and the house lights dimmed on old columns so net light holds
// Design: research/in-flight/piano-spectacle-2026-09-13/design-vfx-director.md
// Rules: every effect is a pure function of the clock; nothing flashes the whole frame; effect light fades out of the
// chord name and staff rectangles (PROTECT); bodies stay under the bloom threshold (0.9), only thin crests cross it.
const TIER_NAMES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"];
const TIER_INK = [null, "#8fe8a8", "#79b8ff", "#c79bff", "#ffc766"];
// fractions of the frame, origin top-left: [x0, y0, x1, y1]
const PROTECT = {
  "9:16": { label: [0.17, 0.10, 0.83, 0.235], staff: [0.13, 0.30, 0.88, 0.54] },
  "16:9": { label: [0.01, 0.08, 0.47, 0.30], staff: [0.66, 0.06, 0.99, 0.46] },
};
const PAL_N = 8;
const fxShared = {
  uNow: { value: 0 }, uRes: { value: new THREE.Vector2(1080, 1920) },
  uProtA: { value: new THREE.Vector4() }, uProtB: { value: new THREE.Vector4() },
  uPal: { value: Array.from({ length: PAL_N }, () => new THREE.Color()) }, uPalN: { value: 1 },
  uSpan: { value: new THREE.Vector2() }, uGoldC: { value: new THREE.Color(1.0, 0.62, 0.22) },
};
const FX_GLSL = `
  uniform float uNow, uPalN;
  uniform vec2 uRes, uSpan;
  uniform vec4 uProtA, uProtB;
  uniform vec3 uPal[${PAL_N}];
  uniform vec3 uGoldC;
  float sq(float x) { return x * x; }
  float fxRect(vec2 p, vec4 r, float soft) {
    vec2 a = smoothstep(r.xy - soft, r.xy, p) * (1.0 - smoothstep(r.zw, r.zw + soft, p));
    return a.x * a.y;
  }
  // v2: a rectangle mask showed as a dark box. A super-ellipse with a wide feather has no edge or corner to see.
  float fxBlob(vec2 p, vec4 r, float feather) {
    vec2 c = 0.5 * (r.xy + r.zw);
    vec2 h = 0.5 * (r.zw - r.xy) + feather;
    vec2 q = abs(p - c) / h;
    float d = pow(pow(q.x, 4.0) + pow(q.y, 4.0), 0.25);
    return 1.0 - smoothstep(0.62, 1.0, d);
  }
  // effect light allowed here: about 0.12 at the heart of the chord name, 0.45 in the staff, 1 elsewhere
  float fxProtect() {
    vec2 p = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
    return (1.0 - 0.88 * fxBlob(p, uProtA, 0.09)) * (1.0 - 0.55 * fxBlob(p, uProtB, 0.06));
  }
  // the chord's colours, low note to high; f counts palette steps and wraps, with a short blend between neighbours
  vec3 fxPal(float f) {
    float n = max(uPalN, 1.0);
    float i = floor(mod(f, n));
    float j = mod(i + 1.0, n);
    float fr = smoothstep(0.35, 0.65, fract(f));
    return mix(uPal[int(i)], uPal[int(j)], fr);
  }
`;
const FX_WORLD_VS = `
  varying vec3 vWorld;
  void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const fxEase = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
function fxBump(age, rise, hold, fall) {
  if (age < 0) return 0;
  if (age < rise) return fxEase(age / rise);
  if (age < rise + hold) return 1;
  return 1 - fxEase((age - rise - hold) / fall);
}
function fxMaterial(uniforms, fragmentShader, vertexShader = FX_WORLD_VS) {
  return new THREE.ShaderMaterial({ uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
                                    vertexShader, fragmentShader: FX_GLSL + fragmentShader });
}

// Floor shockwave: rings on the stage floor, so the front arc crosses the empty floor below the keys and the back arc
// rises out from behind the rail. The piano body occludes it (depth test), which is what sells it as 3D.
const RING_N = 4;
const ringU = { ...fxShared,
  uRing: { value: Array.from({ length: RING_N }, () => new THREE.Vector4(0, 0, -1e6, 0)) },     // x, z, t0, gold
  uRingP: { value: Array.from({ length: RING_N }, () => new THREE.Vector4(0, 24, 1.6, 0.5)) } }; // gain, radius, duration, width
const ringMesh = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), fxMaterial(ringU, `
  uniform vec4 uRing[${RING_N}];
  uniform vec4 uRingP[${RING_N}];
  varying vec3 vWorld;
  void main() {
    vec3 col = vec3(0.0);
    for (int k = 0; k < ${RING_N}; k++) {
      float age = uNow - uRing[k].z;
      float dur = uRingP[k].z;
      if (age < 0.0 || age > dur) continue;
      vec2 q = vWorld.xz - uRing[k].xy;
      float r = uRingP[k].y * (1.0 - exp(-age / 0.5));        // fast out, slowing: a shockwave, not a ripple
      float d = length(q) - r;
      float w = uRingP[k].w * (0.35 + 1.2 * age / dur);       // the wave widens as it spends itself
      float aa = fwidth(d);                                    // a ring thinner than a pixel is widened, energy kept
      float we = max(w, aa * 2.0);
      float body = (d > 0.0 ? exp(-sq(d / (we * 0.3 + aa))) : exp(d / we)) * (w / we);
      float crest = exp(-sq(d / (aa * 1.5 + 0.06))) * min(1.0, 2.0 * w / we);
      float life = sq(1.0 - age / dur);
      float ang = atan(q.y, q.x) / 6.2831853 + 0.5;
      vec3 c = mix(fxPal(ang * uPalN * 2.0 + age * 1.5), uGoldC, uRing[k].w);
      col += (c * body * 0.32 + mix(c, vec3(1.0), 0.45) * crest * 1.1) * life * uRingP[k].x;
    }
    float fogK = 1.0 - smoothstep(55.0, 130.0, distance(vWorld, cameraPosition));
    gl_FragColor = vec4(col * fogK * fxProtect(), 1.0);
  }`));
ringMesh.rotation.x = -Math.PI / 2;
ringMesh.position.y = -2.27;
ringMesh.frustumCulled = false;
ringMesh.visible = false;
scene.add(ringMesh);

// Rail pulse: fronts of the chord's colours running outward along the gold rail line from under the chord.
const PULSE_N = 6;
const railU = { ...fxShared, uRailGold: { value: 0 }, uRailY: { value: RAIL_Y - 0.06 },
  uPulse: { value: Array.from({ length: PULSE_N }, () => new THREE.Vector4(0, -1e6, 40, 0)) } };  // cx, t0, speed, gain
const railFx = new THREE.Mesh(new THREE.PlaneGeometry(58, 1.4), fxMaterial(railU, `
  uniform vec4 uPulse[${PULSE_N}];
  uniform float uRailGold, uRailY;
  varying vec3 vWorld;
  void main() {
    float e = 0.0;
    for (int k = 0; k < ${PULSE_N}; k++) {
      float age = uNow - uPulse[k].y;
      if (age < 0.0 || age > 1.8) continue;
      float d = abs(vWorld.x - uPulse[k].x) - uPulse[k].z * age;
      float head = exp(-d * d / 0.35);
      float wake = d < 0.0 ? exp(d * 0.35) * 0.18 : 0.0;
      e += (head + wake) * exp(-age / 0.55) * uPulse[k].w;
    }
    float dy = vWorld.y - uRailY;
    float prof = exp(-dy * dy / 0.0035) + 0.22 * exp(-abs(dy) * 6.0);
    float ends = 1.0 - smoothstep(25.6, 26.6, abs(vWorld.x));
    float span = max(uSpan.y - uSpan.x, 0.001);
    vec3 c = mix(fxPal(clamp((vWorld.x - uSpan.x) / span, 0.0, 1.0) * (uPalN - 1.0)), uGoldC, uRailGold);
    vec3 col = c * e * prof * 1.4 + uGoldC * uRailGold * prof * 0.3;
    gl_FragColor = vec4(col * ends, 1.0);
  }`));
railFx.position.set(0, RAIL_Y - 0.06, -3.26);
railFx.frustumCulled = false;
railFx.visible = false;
scene.add(railFx);

// Fountain: ballistic sparks from the chord's keys (up, then falling back), separate from the rising embers.
const FXS_MAX = 2000;
const fxsU = { ...fxShared, uPx: sparkUniforms.uPx };
const fxsGeo = new THREE.BufferGeometry();
const fxsAttr = {};
for (const [name, size] of [["position", 3], ["aVel", 3], ["aBirth", 1], ["aLife", 1], ["aSize", 1], ["aSeed", 1], ["aColor", 3]]) {
  const attr = new THREE.BufferAttribute(new Float32Array(FXS_MAX * size), size);
  attr.setUsage(THREE.DynamicDrawUsage);
  fxsGeo.setAttribute(name, attr);
  fxsAttr[name] = attr;
}
fxsAttr.aBirth.array.fill(-FAR);
const fxsPoints = new THREE.Points(fxsGeo, fxMaterial(fxsU, `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float r = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, r);
    vec3 c = mix(vColor, vec3(1.0), 0.35 * a * a);  // a white-hot centre
    gl_FragColor = vec4(c * a * a * vAlpha * 2.6 * fxProtect(), 1.0);
  }`, `
  uniform float uNow, uPx;
  attribute vec3 aVel, aColor;
  attribute float aBirth, aLife, aSize, aSeed;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float age = uNow - aBirth;
    if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
    float k = age / aLife;
    float drag = (1.0 - exp(-age * 0.9)) / 0.9;
    vec3 p = position + aVel * drag + vec3(sin(age * 3.1 + aSeed) * 0.2 * k, -4.2 * age * age, 0.0);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float px = aSize * uPx * (1.0 - 0.45 * k) / max(-mv.z, 0.1);
    gl_PointSize = max(px, 2.5);
    float cover = min(1.0, (px * px) / 6.25);  // a point clamped up to 2.5 px keeps its energy: no sub-pixel flicker
    vAlpha = pow(1.0 - k, 1.6) * cover * (0.78 + 0.22 * sin(age * 11.0 + aSeed * 7.0));
    vColor = aColor;
  }`));
fxsPoints.frustumCulled = false;
fxsPoints.visible = false;
scene.add(fxsPoints);
let fxsNext = 0, fxsDirty = false;
function fxFountain(notes, t, tier) {
  const gold = tier >= 4;
  const total = [0, 90, 300, 520, 900][tier];
  const per = Math.max(6, Math.floor(total / notes.length));
  const spread = gold ? 0.55 : 0.35;
  const A = fxsAttr, G = fxShared.uGoldC.value;
  for (const m of notes) {
    const x = keyX(m), c = noteColor(m, 110);
    for (let i = 0; i < per; i++) {
      const j = fxsNext;
      fxsNext = (fxsNext + 1) % FXS_MAX;
      const up = [0, 4.0, 9.0, 10.0, 11.0][tier] * (0.45 + 0.55 * Math.random());
      A.position.array.set([x + (Math.random() - 0.5) * 0.5, RAIL_Y + 0.1, TRAIL_Z + 0.2], j * 3);
      A.aVel.array.set([(Math.random() - 0.5) * 2.4, up, (Math.random() - 0.3) * 1.2], j * 3);
      A.aBirth.array[j] = t + Math.random() * spread;
      A.aLife.array[j] = 1.0 + Math.random() * (gold ? 1.3 : 0.9);
      A.aSize.array[j] = 0.14 + Math.random() * 0.26;
      A.aSeed.array[j] = Math.random() * 6.283;
      const src = gold && Math.random() < 0.55 ? [G.r * 1.5, G.g * 1.5, G.b * 1.5] : [c.r * 1.2, c.g * 1.2, c.b * 1.2];
      A.aColor.array.set(src, j * 3);
    }
  }
  fxsDirty = true;
}

// Light shafts: a fan of seven beams from the rail under the chord, behind the columns, shooting up at 42 u/s.
const shaftU = { ...fxShared, uShaftT0: { value: -1e6 }, uShaftGain: { value: 0 }, uShaftGold: { value: 0 },
                 uShaftCx: { value: 0 }, uBaseY: { value: RAIL_Y } };
const shaftGeo = new THREE.PlaneGeometry(1, 1);
shaftGeo.translate(0, 0.5, 0);
const shaftMesh = new THREE.Mesh(shaftGeo, fxMaterial(shaftU, `
  uniform float uShaftT0, uShaftGain, uShaftGold, uShaftCx, uBaseY;
  varying vec3 vWorld;
  void main() {
    float age = uNow - uShaftT0;
    vec2 q = vec2(vWorld.x - uShaftCx, vWorld.y - uBaseY);
    float r = length(q);
    float a = atan(q.x, max(q.y, 1e-3));
    float env = smoothstep(0.0, 0.3, age) * (1.0 - smoothstep(1.7, 3.3, age));
    float reach = smoothstep(-4.0, 0.0, age * 42.0 - r);
    vec3 col = vec3(0.0);
    for (int k = 0; k < 7; k++) {
      float fk = float(k) - 3.0;
      float th = fk * 0.17 + 0.035 * sin(uNow * 0.6 + fk * 1.9);
      float wdt = 0.03 + 0.01 * abs(fk) + fwidth(a) * 0.7;
      float g = exp(-sq((a - th) / wdt));
      vec3 c = mix(uPal[int(mod(float(k), max(uPalN, 1.0)))], uGoldC, uShaftGold * (k == 3 ? 1.0 : 0.55));
      col += c * g * (1.0 - 0.12 * abs(fk));
    }
    float fall = exp(-r / 15.0) * smoothstep(0.4, 2.2, r);
    float motes = 0.8 + 0.2 * sin(r * 1.1 - uNow * 4.0);
    gl_FragColor = vec4(col * fall * reach * motes * env * uShaftGain * 0.55 * fxProtect(), 1.0);
  }`));
shaftMesh.scale.set(70, 40, 1);
shaftMesh.position.set(0, RAIL_Y, TRAIL_Z - 0.7);
shaftMesh.frustumCulled = false;
shaftMesh.visible = false;
scene.add(shaftMesh);

// Aurora curtain: far behind the piano, a folded curtain with a gold hem, rays fading upward.
const auroraU = { ...fxShared, uAurT0: { value: -1e6 }, uAurGain: { value: 0 }, uAurCx: { value: 0 }, uBaseY: { value: RAIL_Y } };
const auroraGeo = new THREE.PlaneGeometry(1, 1);
auroraGeo.translate(0, 0.5, 0);
const auroraMesh = new THREE.Mesh(auroraGeo, fxMaterial(auroraU, `
  uniform float uAurT0, uAurGain, uAurCx, uBaseY;
  varying vec3 vWorld;
  void main() {
    float age = uNow - uAurT0;
    float env = smoothstep(0.0, 0.9, age) * (1.0 - smoothstep(3.2, 5.2, age));
    float x = vWorld.x - uAurCx;
    float hem = uBaseY + 2.0 + 2.4 * sin(x * 0.09 + uNow * 0.31) + 1.3 * sin(x * 0.23 - uNow * 0.53) + 0.5 * sin(x * 0.57 + uNow * 0.97);
    float h = vWorld.y - hem;
    float curtain = smoothstep(-0.8, 0.6, h) * exp(-max(h, 0.0) / 4.5);  // v2: a low horizon curtain, not a sky of blurred rays
    float fold = 0.5 + 0.5 * sin(x * 0.8 + 1.6 * sin(x * 0.17 + uNow * 0.45) + uNow * 0.7);
    float rays = 0.45 + 0.55 * fold * fold * fold;
    float hemLine = exp(-sq(h / 0.9));
    vec3 low = mix(fxPal(x * 0.05 + uNow * 0.1), uGoldC, 0.65);
    vec3 high = fxPal(x * 0.04 + 2.0 + uNow * 0.07);
    vec3 col = mix(low, high, smoothstep(0.0, 6.0, h)) * curtain * rays * 0.3 + uGoldC * hemLine * 0.24;
    float side = 1.0 - smoothstep(40.0, 70.0, abs(x));
    gl_FragColor = vec4(col * env * side * uAurGain * fxProtect(), 1.0);
  }`));
auroraMesh.scale.set(150, 60, 1);
auroraMesh.position.set(0, RAIL_Y - 6, -30);
auroraMesh.frustumCulled = false;
auroraMesh.visible = false;
scene.add(auroraMesh);

// Overlay: the tier banner (between the chord name and the staff) and the gold foil on the chord name.
const BANNER = { "9:16": { cx: 540, cy: 540, w: 760, h: 100 }, "16:9": { cx: 500, cy: 400, w: 760, h: 96 } };
const fxOverlay = { banner: null, foil: null };
function fxBuildOverlay() {
  disposeLayer(fxOverlay.banner);
  if (fxOverlay.foil) { overlayScene.remove(fxOverlay.foil); fxOverlay.foil.geometry.dispose(); fxOverlay.foil.material.dispose(); }
  fxOverlay.banner = makeLayer({ ...BANNER[framing.id], align: "center" });
  fxOverlay.banner.mat.opacity = 0;
  fxOverlay.banner.mesh.renderOrder = 3;
  const L = overlay.label;
  fxOverlay.foil = new THREE.Mesh(new THREE.PlaneGeometry(L.spec.w, L.spec.h), new THREE.ShaderMaterial({
    uniforms: { map: { value: L.tex }, uAmt: { value: 0 }, uSweep: { value: -1 }, uOpacity: { value: 1 } },
    transparent: true, depthTest: false, depthWrite: false,
    vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      uniform sampler2D map;
      uniform float uAmt, uSweep, uOpacity;
      varying vec2 vUv;
      void main() {
        float a = texture2D(map, vUv).a;
        float yy = 1.0 - vUv.y;
        // glyph cores of the main name only: the glow halo is under 0.6 alpha, the note chips sit below yy 0.64
        float core = smoothstep(0.78, 0.98, a) * (1.0 - smoothstep(0.62, 0.68, yy));
        vec3 foil = mix(vec3(1.0, 0.93, 0.70), vec3(0.93, 0.60, 0.20), smoothstep(0.18, 0.56, yy));
        float band = exp(-pow((vUv.x - uSweep + (yy - 0.4) * 0.35) / 0.045, 2.0));
        vec3 col = min(foil + vec3(1.0, 0.98, 0.9) * band * 0.9, vec3(1.0));
        gl_FragColor = vec4(col, core * uAmt * uOpacity);
      }`,
  }));
  fxOverlay.foil.renderOrder = 2;
  overlayScene.add(fxOverlay.foil);
  const P = PROTECT[framing.id];
  fxShared.uProtA.value.set(...P.label);
  fxShared.uProtB.value.set(...P.staff);
  fxState.banner.t0 = -1e6;
}
function fxDrawBanner(tier) {
  const { ctx, spec, tex } = fxOverlay.banner;
  ctx.clearRect(0, 0, spec.w, spec.h);
  tex.needsUpdate = true;
  if (tier < 2) return;
  const text = TIER_NAMES[tier].toUpperCase();
  const size = Math.round(spec.h * 0.36);
  const cx = spec.w / 2, cy = spec.h * 0.42;
  const ink = TIER_INK[tier];
  ctx.font = `700 ${size}px ${FONT.display}`;
  ctx.letterSpacing = `${Math.round(size * 0.42)}px`;
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  const tw = ctx.measureText(text).width;
  for (const dir of [-1, 1]) {  // hairline rules that fade outward
    const x0 = cx + dir * (tw / 2 + size * 0.6), x1 = cx + dir * (tw / 2 + size * 4.0);
    const g = ctx.createLinearGradient(x0, 0, x1, 0);
    g.addColorStop(0, ink);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(Math.min(x0, x1), cy - 1.5, Math.abs(x1 - x0), 3);
  }
  ctx.shadowColor = "rgba(0,0,0,0.85)";
  ctx.shadowBlur = 14;
  if (tier === 4) {
    const g = ctx.createLinearGradient(0, cy - size / 2, 0, cy + size / 2);
    g.addColorStop(0, "#fff1c4");
    g.addColorStop(1, "#e59a2e");
    ctx.fillStyle = g;
  } else ctx.fillStyle = "rgba(244,241,234,0.95)";
  ctx.fillText(text, cx + size * 0.21, cy);
  ctx.shadowBlur = 0;
  ctx.letterSpacing = "0px";
  ctx.fillStyle = ink;  // one gem per tier step
  for (let i = 0; i < tier; i++) {
    const gx = cx + (i - (tier - 1) / 2) * size * 0.62, gy = cy + size * 1.0, r = size * 0.13;
    ctx.beginPath();
    ctx.moveTo(gx, gy - r); ctx.lineTo(gx + r, gy); ctx.lineTo(gx, gy + r); ctx.lineTo(gx - r, gy);
    ctx.closePath();
    ctx.fill();
  }
}

const fxCam = { push: 0, elev: 0, yaw: 0 };
const fxState = { dim: 1, fired: [-1e6, -1e6, -1e6, -1e6, -1e6], lastName: null, log: [], seen: new Map(),
                  auto: /[?&]fx=auto/.test(location.search), until: { ring: -1, rail: -1, fxs: -1, shaft: -1, aurora: -1 },
                  banner: { t0: -1e6, hold: 1, tier: 0 }, shimGain: 0,
                  tokens: { 2: 3, 3: 1, 4: 0.75 } };  // v2: rarity tokens; no Legendary before ~45 s of play
const fxSlot = (arr, key) => arr.reduce((best, v, i) => (v[key] < arr[best][key] ? i : best), 0);
function fxRing(cx, t0, gold, gain, radius, dur, width) {
  const i = fxSlot(ringU.uRing.value, "z");
  ringU.uRing.value[i].set(cx, -0.5, t0, gold);
  ringU.uRingP.value[i].set(gain, radius, dur, width);
  fxState.until.ring = Math.max(fxState.until.ring, t0 + dur);
}
function fxPulse(cx, t0, speed, gain) {
  const i = fxSlot(railU.uPulse.value, "y");
  railU.uPulse.value[i].set(cx, t0, speed, gain);
  fxState.until.rail = Math.max(fxState.until.rail, t0 + 1.8);
}
function fxTrigger(tier, t = clock(), notesIn = null, why = null) {
  const notes = [...new Set(notesIn || [...sounding.keys()])].filter((m) => m >= KEY.first && m <= KEY.last).sort((a, b) => a - b);
  if (!notes.length) return false;
  const xs = notes.map(keyX);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), cx = (x0 + x1) / 2;
  const seen = new Set();
  let n = 0;
  for (const m of notes) {
    const pc = Theory.mod(m, 12);
    if (seen.has(pc) || n >= PAL_N) continue;
    seen.add(pc);
    noteColor(m, 110, fxShared.uPal.value[n++]);
  }
  fxShared.uPalN.value = n;
  fxShared.uSpan.value.set(x0, x1);
  const gold = tier >= 4 ? 1 : 0;
  fxState.fired[tier] = t;
  fxState.log.push({ tier, name: TIER_NAMES[tier], t: +t.toFixed(3), chord: overlay.shown ? overlay.shown.name : null, notes, why });
  fxPulse(cx, t, tier >= 2 ? 44 : 36, [0.45, 0.8, 1.0, 1.1, 1.25][tier]);
  if (tier >= 1) { fxPulse(cx, t + 0.12, 36, 0.5); fxFountain(notes, t, tier); fxState.until.fxs = t + 3.2; }
  if (tier >= 4) fxPulse(cx, t + 0.26, 30, 0.8);
  if (tier >= 2) {
    fxRing(cx, t, gold, tier >= 4 ? 1.35 : 1.0, 26, 1.7, 0.55);
    trailUniforms.uShimT0.value = t + 0.03;
    trailUniforms.uShimX0.value = x0 - 0.6;
    trailUniforms.uShimX1.value = x1 + 0.6;
    trailUniforms.uShimGold.value = gold;
    // v2: the shimmer shares a budget: past 8 live columns under the chord it thins out instead of forming a bright bar
    let cols = 0;
    for (let j = 0; j < TRAIL_MAX; j++) {
      const A = trailAttr;
      if (A.aT0.array[j] < -1e5 || t - Math.min(t, A.aT2.array[j]) > LIGHT.endCut) continue;
      if (A.aX.array[j] >= x0 - 0.6 && A.aX.array[j] <= x1 + 0.6) cols++;
    }
    fxState.shimGain = (tier >= 4 ? 1.0 : 0.85) * Math.min(1, 8 / Math.max(cols, 1));
    fxState.banner = { t0: t + 0.05, hold: [0, 0, 1.2, 1.8, 2.8][tier], tier };
    fxDrawBanner(tier);
  }
  if (tier >= 3) {
    fxRing(cx, t + 0.18, 0, 0.7, 32, 1.9, 0.8);
    shaftU.uShaftT0.value = t + 0.05;
    shaftU.uShaftCx.value = cx;
    shaftU.uShaftGold.value = gold;
    shaftU.uShaftGain.value = tier >= 4 ? 1.2 : 0.9;
    shaftMesh.position.x = cx;
    fxState.until.shaft = t + 3.4;
  }
  if (tier >= 4) {
    fxRing(cx, t + 0.36, 1, 0.6, 38, 2.2, 0.35);
    auroraU.uAurT0.value = t + 0.1;
    auroraU.uAurCx.value = cx;
    auroraU.uAurGain.value = 1;
    auroraMesh.position.x = cx;
    fxState.until.aurora = t + 5.4;
  }
  return true;
}
// Fanciness score for a newly named chord (LAB v2; the design doc gives the production scorer).
//   harmony: finger-held notes plus pedal-held notes struck in the last 1.5 s (PIANO-V2-SPEC 6.1)
//   strike: notes whose onsets fall within 80 ms of the newest one
//   accent: the strike's velocity against the mean of the 20 s before it
const FX_TOKENS = { 2: { cap: 3, refill: 10 }, 3: { cap: 2, refill: 45 }, 4: { cap: 1, refill: 180 } };
const fxVelHist = [];
function fxNoteOn(vel, t) {
  fxVelHist.push([t, vel]);
  while (fxVelHist.length && t - fxVelHist[0][0] > 21) fxVelHist.shift();
}
function fxScore(info, t) {
  const parts = {};
  const entries = [...sounding.entries()];
  if (!info || !entries.length) return { score: 0, tier: 0, parts };
  const newest = Math.max(...entries.map(([, s]) => s.t0));
  const strike = entries.filter(([, s]) => newest - s.t0 < 0.08);
  const vel = strike.reduce((acc, [, s]) => acc + s.vel, 0) / strike.length;
  const before = fxVelHist.filter(([ht]) => ht < newest - 0.1 && newest - ht < 20);
  const mean = before.length >= 4 ? before.reduce((acc, [, v]) => acc + v, 0) / before.length : 80;
  const harmony = entries.filter(([, s]) => s.held || t - s.t0 < 1.5).map(([m]) => m);
  const h = harmony.length ? Theory.detect(harmony, keyGuess ? keyGuess.bias : 0) : null;
  if (h && h.kind === "chord") {
    const suf = h.suffix || "";
    parts.colour = /13|11/.test(suf) ? 3 : /9/.test(suf) ? 2.5 : /7|6/.test(suf) ? 1.5 : /sus|dim|aug/.test(suf) ? 1 : 0;
    if (h.bass) parts.slash = 0.5;
    const pcs = new Set(harmony.map((m) => Theory.mod(m, 12))).size;
    if (pcs > 4) parts.density = Math.min(1.5, 0.5 * (pcs - 4));
    if (keyGuess) {
      const scale = keyGuess.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11];
      if (harmony.some((m) => !scale.includes(Theory.mod(m - keyGuess.tonic, 12)))) parts.borrowed = 1.5;
    }
  }
  const sm = strike.map(([m]) => m);
  const span = Math.max(...sm) - Math.min(...sm);
  if (span >= 24) parts.span = span >= 36 ? 1.5 : 1;
  if (strike.length >= 4) parts.mass = strike.length >= 6 ? 1 : 0.5;
  const acc = vel - mean;
  if (acc >= 12) parts.accent = acc >= 22 ? 2 : 1;
  if (vel >= 112) parts.loud = 0.5;
  if (sustain && strike.length >= 3) parts.pedal = 0.5;
  const name = h ? h.name : info.name;
  const hist = (fxState.seen.get(name) || []).filter((x) => t - x < 60);
  if (!fxState.seen.has(name) && strike.length >= 3) parts.novelty = 0.5;
  if (hist.length >= 3) parts.fatigue = -1.5;
  fxState.seen.set(name, [...hist, t]);
  // v3: an arc. The third or later block strike in a run where each is louder than the last (by 4+, within 12 s),
  // ending at velocity 105+, is a climax, whatever its chord.
  if (strike.length >= 3) {
    const S = fxState.strikes || (fxState.strikes = []);
    if (!S.length || newest - S[S.length - 1].t > 0.2) S.push({ t: newest, vel });
    let run = 1;
    for (let i = S.length - 1; i > 0 && S[i].vel >= S[i - 1].vel + 4 && S[i].t - S[i - 1].t <= 12; i--) run++;
    if (run >= 3 && vel >= 105) parts.arc = 1.5;
  }
  const score = Object.values(parts).reduce((x, y) => x + y, 0);
  let tier = score >= 8 ? 4 : score >= 6 ? 3 : score >= 4.5 ? 2 : score >= 2.5 ? 1 : 0;
  const want = tier;
  const gates = [];
  if (tier >= 4 && !(strike.length >= 5 && (parts.accent === 2 || vel >= 112))) { tier = 3; gates.push("legendary needs 5+ struck and a real accent"); }
  if (tier >= 3 && !(strike.length >= 4 && parts.accent)) { tier = 2; gates.push("epic needs 4+ struck and an accent"); }
  if (tier >= 2 && strike.length < 3) { tier = 1; gates.push("rare needs 3+ struck together"); }
  while (tier >= 2 && fxState.tokens[tier] < 1) { gates.push("no " + TIER_NAMES[tier] + " token"); tier--; }
  if (tier >= 2) fxState.tokens[tier] -= 1;
  return { score: +score.toFixed(2), want, tier, gates, parts, harmony: name, strike: strike.length, vel: Math.round(vel), mean: Math.round(mean) };
}
function fxUpdate(dt, t) {
  for (const k of [2, 3, 4]) fxState.tokens[k] = Math.min(FX_TOKENS[k].cap, fxState.tokens[k] + dt / FX_TOKENS[k].refill);
  fxShared.uNow.value = t;
  fxShared.uRes.value.set(composer.readBuffer.width, composer.readBuffer.height);
  const shown = overlay.shown;
  if (!shown) fxState.lastName = null;
  else if (shown.name !== fxState.lastName) {
    fxState.lastName = shown.name;
    if (fxState.auto) { const s = fxScore(shown, t); fxTrigger(s.tier, t, null, s); }
  }
  const legend = t - fxState.fired[4], epic = t - fxState.fired[3];
  const L = fxBump(legend, 1.0, 0.8, 2.4), E = fxBump(epic, 0.8, 0.4, 1.8);
  fxCam.push = 0.055 * L + 0.025 * E * (1 - L);
  fxCam.elev = 0.02 * L + 0.008 * E * (1 - L);
  fxCam.yaw = 0.022 * L;
  fxState.dim = 1 - 0.35 * fxBump(legend, 0.25, 2.2, 1.2) - 0.15 * fxBump(epic, 0.2, 0.8, 1.0);
  railU.uRailGold.value = 0.9 * fxBump(legend, 0.1, 1.6, 1.4);
  ringMesh.visible = t < fxState.until.ring;
  railFx.visible = t < Math.max(fxState.until.rail, fxState.fired[4] + 3.2);
  fxsPoints.visible = t < fxState.until.fxs;
  shaftMesh.visible = t < fxState.until.shaft;
  auroraMesh.visible = t < fxState.until.aurora;
  trailUniforms.uShimGain.value = t - trailUniforms.uShimT0.value < 2.6 ? fxState.shimGain : 0;
  if (fxsDirty) { for (const attr of Object.values(fxsAttr)) attr.needsUpdate = true; fxsDirty = false; }
  const b = fxState.banner, bm = fxOverlay.banner;
  const bo = fxBump(t - b.t0, 0.14, b.hold, 0.6);
  bm.mat.opacity = bo;
  bm.mesh.scale.set(0.94 + 0.06 * fxEase((t - b.t0) / 0.35), 1, 1);
  const foil = fxOverlay.foil, lab = overlay.label;
  foil.material.uniforms.uAmt.value = fxBump(legend - 0.1, 0.18, 2.9, 0.8);
  foil.material.uniforms.uSweep.value = legend > 0.2 && legend < 1.3 ? lerp(0.12, 0.98, fxEase((legend - 0.2) / 1.0)) : -1;
  foil.material.uniforms.uOpacity.value = lab.mat.opacity;
  foil.position.copy(lab.mesh.position);
  foil.scale.copy(lab.mesh.scale);
  foil.visible = foil.material.uniforms.uAmt.value > 0;
}

