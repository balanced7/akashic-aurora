import { createSolsticeSignals } from './solstice-signals.mjs';

export const CANOPY_FORMS = ['ribbons', 'fan', 'halo', 'sails'];

// The light is part of a solid opal diffuser. HDR emission blooms gently and the brass housing
// still receives the real studio lights. Only 36 floats and one phase uniform change each frame.
function diffuserMaterial(T, envMap, signals, phase) {
  const material = new T.MeshPhysicalMaterial({ color: 0x6e6155, roughness: .38, metalness: .05,
    clearcoat: .45, clearcoatRoughness: .3, envMap, envMapIntensity: .22, side: T.DoubleSide });
  material.onBeforeCompile = shader => {
    shader.uniforms.uCells = { value: signals.cells }; shader.uniforms.uFlowTime = phase;
    shader.vertexShader = 'attribute float aBand; varying vec2 vLedUv; varying float vBand;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>',
      '#include <begin_vertex>\nvLedUv = uv; vBand = aBand;');
    shader.fragmentShader = 'uniform float uCells[36]; uniform float uFlowTime; varying vec2 vLedUv; varying float vBand;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <emissivemap_fragment>', `
      #include <emissivemap_fragment>
      float x = min(vLedUv.x * 12.0, 11.9999);
      int column = int(floor(x)); int row = int(vBand + .5);
      float strength = uCells[row * 12 + column];
      float localX = fract(x);
      float edgeAA = max(fwidth(x), .015);
      float cell = smoothstep(.015, .015 + edgeAA, localX) * (1.0 - smoothstep(.985 - edgeAA, .985, localX));
      float edge = abs(vLedUv.y * 2.0 - 1.0);
      float diffuser = 1.0 - smoothstep(.48, 1.0, edge);
      float flow = .5 + .5 * sin(vLedUv.x * 8.0 - uFlowTime * .8 + vBand * 1.6);
      vec3 gold = vec3(1.0, .53, .18), rose = vec3(1.0, .23, .20), lilac = vec3(.63, .27, 1.0);
      vec3 tint = row == 0 ? mix(gold, rose, flow * .55) : (row == 1 ? mix(gold, rose, .35 + flow * .55) : mix(rose, lilac, .55 + flow * .4));
      vec3 core = mix(tint, vec3(1.0, .88, .68), .20);
      totalEmissiveRadiance += gold * .075 + core * strength * cell * diffuser * (3.4 + .5 * flow);
    `);
  };
  material.customProgramCacheKey = () => 'solstice-led-diffuser-v1';
  return material;
}

export function createSolsticeCanopy(T, parent, envMap, shellGeometry) {
  const signals = createSolsticeSignals(), phase = { value: 0 };
  const group = new T.Group(); group.name = 'solstice-led-canopy'; parent.add(group);
  const brass = new T.MeshPhysicalMaterial({ color: 0xc7a777, metalness: .78, roughness: .3,
    clearcoat: .45, clearcoatRoughness: .25, envMap, envMapIntensity: .65 });
  const diffuser = diffuserMaterial(T, envMap, signals, phase);
  const geometries = [];
  let form = null;
  const path = (kind, row, u, v = .5) => {
    if (kind === 'halo') {
      const a = u * Math.PI * 2 + Math.PI / 2, r = 26 + row * 5 + (v - .5) * 2.3;
      return [-5 + Math.cos(a) * r, 23 + row * 6 + Math.sin(a) * 1.6, -42 + Math.sin(a) * r * .64];
    }
    if (kind === 'fan') {
      const a = (u - .5) * 2.05, r = 48 - row * 9 + (v - .5) * 2.8;
      return [-7 + Math.sin(a) * r, 24 + row * 6 + Math.sin(u * Math.PI) * 3, -65 + Math.cos(a) * r];
    }
    return [(u - .5) * (57 - row * 3), 24 + row * 7 + Math.sin(u * Math.PI) * 2.5,
      -25 - row * 12 + (v - .5) * 3.0];
  };
  function clearGeometry() {
    group.clear(); geometries.splice(0).forEach(g => g.dispose());
  }
  function setForm(next) {
    if (!CANOPY_FORMS.includes(next)) next = 'ribbons';
    if (next === form) return;
    clearGeometry(); form = next; group.visible = next !== 'sails';
    if (next === 'sails') return;
    for (let row = 0; row < 3; row++) {
      const housing = shellGeometry(T, (u, v) => path(next, row, u, v), .55, next === 'halo' ? 192 : 96, 6);
      geometries.push(housing); group.add(new T.Mesh(housing, brass));
      const glow = shellGeometry(T, (u, v) => {
        const p = path(next, row, u * .994 + .003, .5 + (v - .5) * .74); p[1] += .34; return p;
      }, .17, next === 'halo' ? 192 : 96, 6);
      glow.setAttribute('aBand', new T.Float32BufferAttribute(new Float32Array(glow.attributes.position.count).fill(row), 1));
      geometries.push(glow); group.add(new T.Mesh(glow, diffuser));
      // Continuous supports grow out of the bass spine, so the lights read as built into the piano.
      const p = path(next, row, next === 'halo' ? .25 : 0);
      const support = new T.CatmullRomCurve3([
        new T.Vector3(-30, 9, -38 - row * 5), new T.Vector3(-32, 17, -40 - row * 5),
        new T.Vector3(p[0] - 1.5, p[1] - 3, p[2]), new T.Vector3(p[0], p[1] - .3, p[2]),
      ]);
      const g = new T.TubeGeometry(support, 32, .18, 10, false);
      geometries.push(g); group.add(new T.Mesh(g, brass));
    }
  }
  return {
    cells: signals.cells,
    setForm,
    update(dt, t, state, motion) { if (motion) phase.value += dt; signals.update(dt, t, state); },
    dispose() { clearGeometry(); brass.dispose(); diffuser.dispose(); parent.remove(group); },
  };
}
