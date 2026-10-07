// Art directions layered onto the existing, mechanically complete Crystal Grand.
import glassGrand from './instruments/glass-piano.js';
import { damp } from './crystal-performance.mjs';
import { createSolsticeCanopy, CANOPY_FORMS } from './solstice-canopy.js';

export const STUDIES = {
  aether: { name: 'Aether', number: '01', subtitle: 'Light, suspended.',
    description: 'Prismatic crystal · platinum action · flowing spectral ribbons',
    accent: '#b6e8ee', color: 0x9cdeea, second: 0x9986ef, metal: 0xa6bac6, wood: 0x667f88,
    bg: 0x050b14, roughness: .12, iridescence: .38, dispersion: .12, bloom: .30, mode: 0 },
  solstice: { name: 'Solstice', number: '02', subtitle: 'The warmth within.',
    description: 'Opalescent glass · champagne brass · breathing resonator petals',
    accent: '#f3c798', color: 0xffbe72, second: 0xff8d9b, metal: 0xcda568, wood: 0xa77c51,
    bg: 0x130b09, roughness: .19, iridescence: .65, dispersion: .05, bloom: .26, mode: 1 },
  nocturne: { name: 'Nocturne', number: '03', subtitle: 'A sky held in glass.',
    description: 'Smoked crystal · violet titanium · a living aurora canopy',
    accent: '#c7b7ff', color: 0xaa82ff, second: 0x50dbc8, metal: 0x787f9f, wood: 0x494558,
    bg: 0x080715, roughness: .14, iridescence: .48, dispersion: .09, bloom: .32, mode: 2 },
};

// Geometry carries ribbon coordinates; all coherent deformation stays on the GPU.
const ribbonVertex = `
uniform float uTime, uEnergy, uMode, uMotion;
uniform float uNotes[88];
varying vec2 vUv;
varying float vLight;
void main() {
  vUv = uv;
  float a = uv.x * 6.2831853;
  float side = uv.y * 2.0 - 1.0;
  float lane = position.z;
  float index = uv.x * 86.0;
  int ni = int(floor(index));
  float n = mix(uNotes[ni], uNotes[ni + 1], smoothstep(0.0, 1.0, fract(index)));
  float wave = sin(a * 3.0 + uTime * .27 + lane * 1.8) * uMotion;
  vec3 p;
  if (uMode < .5) {
    float arc = uv.x * 4.4 - .6;
    float r = 33.0 + lane * 3.8 + .8 * wave;
    p = vec3(cos(arc) * r, 12.0 + sin(arc) * 15.0 + lane * 6.0, -59.0 - sin(arc) * r * .65);
    p.y += side * (.16 + n * .12) + n * .45;
    p.x += side * .14;
  } else if (uMode < 1.5) {
    float r = 43.0 + lane * 2.0 + sin(a * 9.0) * 2.8;
    p = vec3(cos(a) * r, -24.0 + lane * 1.8, -25.0 + sin(a) * r * .78);
    p.y += side * .2 + sin(a * 9.0 + uTime * .2) * (.4 + uEnergy) * uMotion;
  } else {
    float arc = uv.x * 3.8 - .25;
    float r = 40.0 + lane * 3.8;
    p = vec3(cos(arc) * r, 23.0 + sin(arc * 2.0 + uTime * .15) * 6.0 * uMotion, -58.0 - sin(arc) * r * .60);
    p.y += side * (2.8 + 1.1 * wave + n * .5) + lane * 4.0;
    p.x += sin(arc * 3.0 + uTime * .24) * (1.0 + uEnergy) * uMotion;
  }
  vLight = .5 + .5 * sin(a * 2.0 - uTime * .35 + lane);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;
const ribbonFragment = `
uniform vec3 uColor, uSecond;
uniform float uEnergy, uMode;
varying vec2 vUv;
varying float vLight;
void main() {
  float edge = abs(vUv.y * 2.0 - 1.0);
  float aa = max(fwidth(edge), .025);
  float cover = 1.0 - smoothstep(1.0 - aa, 1.0, edge);
  float core = exp(-edge * edge * (uMode > 1.5 ? 4.0 : 2.0));
  vec3 c = mix(uColor, uSecond, vLight) * (1.05 + uEnergy * .85);
  float opacity = uMode > 1.5 ? .105 : .28;
  float ends = smoothstep(0.0, .06, vUv.x) * (1.0 - smoothstep(.92, 1.0, vUv.x));
  gl_FragColor = vec4(c, cover * core * opacity * ends);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

function ribbonGeometry(T, lanes) {
  const pos = [], uv = [], indices = [], steps = 320;
  for (let lane = 0; lane < lanes; lane++) {
    const base = pos.length / 3;
    for (let i = 0; i <= steps; i++) for (let side = 0; side <= 1; side++) {
      pos.push(0, 0, lane); uv.push(i / steps, side);
    }
    for (let i = 0; i < steps; i++) {
      const k = base + i * 2; indices.push(k, k + 1, k + 2, k + 1, k + 3, k + 2);
    }
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2)); g.setIndex(indices);
  return g;
}

// Closed, tessellated shells: actual curved surfaces and edge thickness, without texture assets.
function shellGeometry(T, surface, thickness = .38, nu = 72, nv = 28) {
  const p = [], uv = [], ix = [], stride = nv + 1, layer = (nu + 1) * stride;
  const a = new T.Vector3(), b = new T.Vector3(), normal = new T.Vector3();
  for (let side = 0; side < 2; side++) for (let i = 0; i <= nu; i++) for (let j = 0; j <= nv; j++) {
    const u = i / nu, v = j / nv, c = surface(u, v), du = surface(u + .0001, v), dv = surface(u, v + .0001);
    a.set(du[0] - c[0], du[1] - c[1], du[2] - c[2]);
    b.set(dv[0] - c[0], dv[1] - c[1], dv[2] - c[2]); normal.crossVectors(a, b).normalize();
    const offset = (side ? -.5 : .5) * thickness;
    p.push(c[0] + normal.x * offset, c[1] + normal.y * offset, c[2] + normal.z * offset); uv.push(u, v);
  }
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
    const k = i * stride + j, l = k + layer;
    ix.push(k, k + stride, k + 1, k + 1, k + stride, k + stride + 1);
    ix.push(l, l + 1, l + stride, l + 1, l + stride + 1, l + stride);
  }
  const bridge = (x, y) => ix.push(x, y, x + layer, y, y + layer, x + layer);
  for (let i = 0; i < nu; i++) { bridge(i * stride, (i + 1) * stride); bridge((i + 1) * stride + nv, i * stride + nv); }
  for (let j = 0; j < nv; j++) { bridge(j + 1, j); bridge(nu * stride + j, nu * stride + j + 1); }
  const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(p, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2)); g.setIndex(ix); g.computeVertexNormals(); return g;
}

function sculptCase(T, group, id, spec, envMap, geos, mats) {
  const shellMat = new T.MeshPhysicalMaterial({ color: id === 'solstice' ? 0xffedcf : 0xe0ecff,
    metalness: id === 'solstice' ? .16 : .04, roughness: spec.roughness + .07,
    transmission: id === 'solstice' ? .22 : .92, thickness: .6, ior: 1.46,
    attenuationColor: new T.Color(spec.color), attenuationDistance: 18,
    iridescence: spec.iridescence, iridescenceThicknessRange: [170, 420],
    clearcoat: .8, clearcoatRoughness: .22, envMap, envMapIntensity: .6,
    side: T.DoubleSide });
  mats.push(shellMat);
  const addShell = (fn, material = shellMat, thick = .42) => {
    const g = shellGeometry(T, fn, thick); geos.push(g);
    const mesh = new T.Mesh(g, material); group.add(mesh); return mesh;
  };
  if (id === 'aether') {
    // A single asymmetrical cantilever: the lid rises out of the bass spine like a swept wing.
    addShell((u, v) => {
      const width = 56 * (1 - u * .73);
      return [-31 + width * v, 12 + Math.sin(v * 1.27) * (27 - u * 12) + Math.sin(u * Math.PI) * 7 * v,
        -10 - u * 65 - Math.sin(v * Math.PI) * Math.sin(u * Math.PI) * 9];
    });
    // Structural, tapered crystal runners replace the impression of a traditional turned leg.
    for (const sign of [-1, 1]) addShell((u, v) => [sign * (28 + Math.sin(u * Math.PI) * 3) + (v - .5) * (5 - u * 2),
      -2 - u * 28, -.5 - Math.sin(u * Math.PI) * 9 + (v - .5) * 1.5], shellMat, .8);
  } else if (id === 'solstice') {
    // Three porcelain sails fan out from the curved tail; open spaces leave the action visible.
    for (let piece = 0; piece < 3; piece++) addShell((u, v) => {
      const a = (-2.6 + piece * .74) + v * .59;
      const r = 9 + u * 41;
      return [-8 + Math.cos(a) * r, 12 + Math.sin(u * Math.PI * .78) * (20 + piece * 4),
        -65 - Math.sin(a) * r];
    }, shellMat, .65);
    // Continuous branches visibly attach each sail to the tail, with fine raised seams on the opal.
    const ribMat = new T.MeshStandardMaterial({ color: spec.metal, metalness: .8, roughness: .34, envMap, envMapIntensity: .65 });
    mats.push(ribMat);
    for (let piece = 0; piece < 3; piece++) {
      const a = -2.6 + piece * .74 + .295;
      const points = [new T.Vector3(-8, 3, -64)];
      for (let i = 0; i <= 32; i++) {
        const u = i / 32, r = 9 + u * 41;
        points.push(new T.Vector3(-8 + Math.cos(a) * r,
          11.7 + Math.sin(u * Math.PI * .78) * (20 + piece * 4), -65 - Math.sin(a) * r));
      }
      const g = new T.TubeGeometry(new T.CatmullRomCurve3(points), 80, .24, 10, false);
      geos.push(g); group.add(new T.Mesh(g, ribMat));
    }
  } else {
    // Two separate smoked wings and a deliberate central opening, instead of a conventional lid.
    for (const sign of [-1, 1]) addShell((u, v) => {
      const taper = 1 - u * .65;
      return [-u * 8 + sign * (4 + v * 27 * taper),
        13 + Math.sin(v * 1.6) * (22 + u * 5) + Math.sin(u * Math.PI) * 6,
        -12 - u * 61 - Math.sin(v * Math.PI) * 4];
    });
    const titanium = new T.MeshPhysicalMaterial({ color: spec.metal, metalness: .72, roughness: .32,
      iridescence: .6, envMap, envMapIntensity: .5 }); mats.push(titanium);
    // Arched titanium buttresses give the undercarriage a different silhouette, too.
    for (const sign of [-1, 1]) addShell((u, v) => [sign * (28 * (1 - u) + 12 * u) + (v - .5) * 1.1,
      -3 - Math.sin(u * Math.PI * .5) * 27, -u * 29 + (v - .5) * 2.5], titanium, .65);
  }
}

export function createStudy(ctx, id, envMap, options = {}) {
  const T = ctx.THREE, spec = STUDIES[id];
  if (!spec) throw new Error(`Unknown crystal study: ${id}`);
  const base = glassGrand.create({ ...ctx, options: { lid: 'off', desk: false, glass: 'crystal', edge: .52 } });
  // The rim itself changes silhouette. Keep the keyboard, plate, strings and action in their physical coordinates.
  const body = base.group.children.find(o => o.isMesh && o.material?.transmission > 0);
  if (body) {
    body.name = `sculpted-rim:${id}`;
    const positions = body.geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      const z = positions.getZ(i), y = positions.getY(i);
      const u = Math.max(0, Math.min(1, (-z - 12) / 62));
      const upper = Math.max(0, Math.min(1, (y - 2.9) / 8.6));
      const rise = id === 'aether' ? -3.5 * u : id === 'solstice' ? Math.sin(u * Math.PI * 3) * 1.7 : 3.8 * Math.sin(u * Math.PI);
      positions.setY(i, y + rise * upper);
    }
    positions.needsUpdate = true; body.geometry.computeVertexNormals();
    body.geometry.computeBoundingSphere();
  }
  const materialSet = new Set();
  base.group.traverse(o => { if (o.material) for (const m of [].concat(o.material)) materialSet.add(m); });
  for (const m of materialSet) {
    if (m.isMeshPhysicalMaterial) {
      const color = m.color.getHex();
      if (m.transmission > 0) {
        m.roughness = spec.roughness; m.clearcoatRoughness = .22;
        m.specularIntensity = .65; m.iridescence = spec.iridescence;
        m.iridescenceIOR = 1.32; m.iridescenceThicknessRange = [180, 430];
        m.dispersion = spec.dispersion;
        m.attenuationColor.setHex(spec.color); m.attenuationDistance = id === 'nocturne' ? 12 : 28;
        m.envMap = envMap; m.envMapIntensity = .20;
      } else if (color === 0xc8a052 || color === 0xd9b46c) {
        m.color.setHex(spec.metal); m.metalness = .72; m.roughness = .34;
        m.envMap = envMap; m.envMapIntensity = .6;
      } else if (color === 0x957250 || color === 0xc49a66) {
        m.color.setHex(spec.wood); m.roughness = .65;
      }
    }
    if (m.isShaderMaterial && m.uniforms.uMinPx) {
      // Minimum coverage is per actual render target; derivatives adapt the falloff to perspective.
      m.uniforms.uMinPx.value = .85;
      m.fragmentShader = m.fragmentShader
        .replace('smoothstep(1.0, 0.86, d)', '(1.0 - smoothstep(max(0.0, 1.0 - max(fwidth(vAcross), 0.14)), 1.0, d))')
        .replace('smoothstep(1.0, 0.72, d)', '(1.0 - smoothstep(max(0.0, 1.0 - max(fwidth(vAcross), 0.28)), 1.0, d))');
    }
  }

  const ornament = new T.Group(); ornament.name = `study:${id}`; base.group.add(ornament);
  const geos = [], mats = [];
  const sculpture = new T.Group(); ornament.add(sculpture);
  sculptCase(T, sculpture, id, spec, envMap, geos, mats);
  const canopy = id === 'solstice' ? createSolsticeCanopy(T, ornament, envMap, shellGeometry) : null;
  function setCanopy(form) {
    if (!canopy) return;
    form = CANOPY_FORMS.includes(form) ? form : 'ribbons';
    sculpture.visible = form === 'sails'; canopy.setForm(form);
  }
  setCanopy(options.canopy ?? 'ribbons');
  const notes = new Float32Array(88);
  const uniforms = {
    uTime: { value: 0 }, uEnergy: { value: 0 }, uMode: { value: spec.mode }, uMotion: { value: 1 },
    uNotes: { value: notes }, uColor: { value: new T.Color(spec.color) }, uSecond: { value: new T.Color(spec.second) },
  };
  const ribbonMat = new T.ShaderMaterial({ uniforms, vertexShader: ribbonVertex, fragmentShader: ribbonFragment,
    transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending });
  const ribbonGeo = ribbonGeometry(T, id === 'solstice' ? 2 : 3);
  geos.push(ribbonGeo); mats.push(ribbonMat);
  const ribbon = new T.Mesh(ribbonGeo, ribbonMat); ribbon.frustumCulled = false; ornament.add(ribbon);

  // Solstice's real solid petals catch the studio environment, individually opening on resonance.
  let petals = null;
  const matrix = new T.Object3D();
  if (id === 'solstice') {
    const g = new T.SphereGeometry(1, 20, 12);
    const m = new T.MeshPhysicalMaterial({ color: 0xe3bd89, metalness: .65, roughness: .3,
      iridescence: .4, clearcoat: .6, clearcoatRoughness: .22, envMap, envMapIntensity: .7 });
    petals = new T.InstancedMesh(g, m, 28); petals.instanceMatrix.setUsage(T.DynamicDrawUsage);
    petals.frustumCulled = false; ornament.add(petals); geos.push(g); mats.push(m);
  }

  // Instanced quads, never hardware point sprites: stable soft coverage at any device pixel ratio.
  const dust = new T.InstancedBufferGeometry();
  dust.setAttribute('position', new T.Float32BufferAttribute([-.5,-.5,0,.5,-.5,0,.5,.5,0,-.5,.5,0], 3));
  dust.setAttribute('uv', new T.Float32BufferAttribute([0,0,1,0,1,1,0,1], 2)); dust.setIndex([0,1,2,0,2,3]);
  const seed = [];
  for (let i = 0; i < 352; i++) seed.push(((i * 73) % 353) / 353, ((i * 137) % 359) / 359, i % 88);
  dust.setAttribute('aSeed', new T.InstancedBufferAttribute(new Float32Array(seed), 3)); dust.instanceCount = 352;
  const dustMat = new T.ShaderMaterial({ uniforms, transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    vertexShader: `
      attribute vec3 aSeed;
      uniform float uTime, uMode, uMotion, uNotes[88];
      varying vec2 vUv; varying float vAlpha;
      void main() {
        vUv = uv; float n = uNotes[int(aSeed.z)];
        float a = aSeed.x * 6.2831853 + uTime * .018 * uMotion;
        float r = 33.0 + aSeed.y * 28.0;
        float lift = mod(aSeed.y * 41.0 + uTime * .7 * uMotion, 45.0);
        vec3 p = vec3(cos(a) * r, -12.0 + lift, -27.0 + sin(a) * r * .7);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        float size = .24 + n * .26;
        mv.xy += position.xy * size;
        gl_Position = projectionMatrix * mv;
        float breathe = .65 + .35 * sin(uTime * .9 + aSeed.x * 21.0);
        vAlpha = (.18 + n * .7) * breathe * smoothstep(0.0, 4.0, lift) * (1.0 - smoothstep(36.0, 45.0, lift));
      }`,
    fragmentShader: `
      uniform vec3 uColor; varying vec2 vUv; varying float vAlpha;
      void main() { float d = length(vUv * 2.0 - 1.0); float a = exp(-d*d*5.0) * (1.0-smoothstep(.7,1.0,d));
        gl_FragColor = vec4(uColor * 1.8, a * vAlpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }` });
  const particles = new T.Mesh(dust, dustMat); particles.frustumCulled = false; ornament.add(particles);
  geos.push(dust); mats.push(dustMat);

  let energy = 0, motionTime = 0;
  return {
    spec, group: base.group, keyStyle: base.keyStyle, hints: base.hints, stage: base.stage,
    views: { hero: { from: [128, 86, 101], target: [-3, 1, -25], fov: 38 }, close: base.views.close },
    resize: f => base.resize(f), setActive: on => base.setActive(on),
    setCanopy, canopyCells: canopy?.cells ?? null,
    update(dt, t, state, motion = true) {
      base.update(dt, t, state);
      canopy?.update(dt, t, state, motion);
      // Reduced motion freezes ornamental movement, but leaves the playable mechanism intact.
      if (motion) motionTime += dt;
      uniforms.uTime.value = motionTime; uniforms.uMotion.value = motion ? 1 : 0;
      let sum = 0;
      for (let i = 0; i < 88; i++) {
        const e = state.sounding.get(i + 21);
        const target = e ? e.vel / 127 * (.3 + .7 * Math.exp(-(t - e.t0) / 2.4)) : 0;
        notes[i] = damp(notes[i], target, dt, target > notes[i] ? .065 : .65);
        sum += notes[i];
      }
      energy = damp(energy, Math.min(1, sum / 6), dt, .25); uniforms.uEnergy.value = energy;
      if (petals) {
        for (let i = 0; i < 28; i++) {
          const a = i / 28 * Math.PI * 2, n = notes[Math.floor(i / 28 * 87)];
          matrix.position.set(Math.cos(a) * 43, -20 + Math.sin(a) * 2, -25 + Math.sin(a) * 34);
          matrix.rotation.set(.15 + (motion ? energy * .12 + n * .22 : 0), -a, .18 * Math.sin(a));
          matrix.scale.set(4.8, .15, 1.2 + n * 1.2); matrix.updateMatrix(); petals.setMatrixAt(i, matrix.matrix);
        }
        petals.instanceMatrix.needsUpdate = true;
      }
      return energy;
    },
    dispose() {
      canopy?.dispose();
      ornament.removeFromParent(); base.dispose();
      if (petals) petals.dispose();
      geos.forEach(g => g.dispose()); mats.forEach(m => m.dispose());
    },
  };
}
