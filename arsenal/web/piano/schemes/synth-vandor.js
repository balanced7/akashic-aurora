// Straight Roll — arsenal/web/piano/schemes/synth-vandor.js  (ES module, a piano scheme; Vandor's Synthesia entry)
// The original straight light columns, beefed up (lookdev2 straight-lines-proposal.md section 3):
//   - W's glass tubes: one straight lane per key, rising at a steady 6.5 u/s from one onset row the keys hide;
//     a solid glossy core while the finger holds, a hollow rim over tinted glass while only the pedal holds;
//     finger + pedal together is the brightest state
//   - the velocity cap: the head's length is the velocity (W x (0.45 + 2.1 v)); on the strike it flashes and
//     glows, and that glow is the ONLY part of the picture that crosses the bloom threshold; it decays, and a
//     hard strike glows brighter and wider than a soft one. The in-cap flash and the halo are one mesh, the only
//     additive draw, and it draws last
//   - X's attack at the key edge, in the same frame: a flash with an anamorphic streak, a ring across the key
//     tops and sparks, all scaled by velocity
//   - bloom budget: every other light layer (board, floor, flash, ring, sparks) is composited as luma-bounded
//     light, premultiplied with alpha = luma / LIGHT_CAP. Over a pixel at or under LIGHT_CAP the result stays at
//     or under LIGHT_CAP, and over a brighter pixel its luma never rises, however many layers stack. (Plain
//     additive layers, each capped on its own, summed past the 0.9 threshold on lit bars and keys.)
//   - peak-hold meter (the second dynamics cue): each lane has a glass sleeve and a needle; a strike throws the
//     needle to a height set by velocity, it holds about 1 s, then falls. A chord leaves a skyline of needles,
//     so "which voice was loudest" can still be read after the flash is gone
//   - the lane board behind the bars: faint key guides, slow 2 s time lines, lane light at the contact line,
//     warm guides while the pedal is down and one amber line where the pedal lifted, rising with the roll
//   - a still glass floor in front of the piano that catches the lane light (no ripple, no squiggle)
//   - beads: a re-struck note's previous bar ends at least max(0.16 u, 5 px) before the new onset
//   - history: an ended bar dims and desaturates over 3.5 s; everything fades out under the host's title band
//
// Contract (PIANO-V2-SPEC.md section 1): no imports, everything from ctx; draws only the music (no words: chord
// names and onset stamps belong to the host). Pooled instanced geometry, every position from the clock in the
// vertex shader, uploads only on note events (update ranges), no allocation in update(). 10 draw calls.

const FAR = 1e6;
const SLOTS = 768;                 // bars; recycled, so a long session never grows
const HITS = 128;                  // flash + ring
const SPARKS = 2048;
const PED_SEGS = 12;
const SPEED = 6.5;                 // world units per second (one unit = one white-key pitch)
const BASE = -0.10;                // one onset row for every bar, inside the key, so the key hides the foot
const Z_OFF = 0.42;                // bar plane = TRAIL_Z + 0.42 = -3.0: 0.1 in front of the key backs
const KEY_TOP = { white: 0.0, black: 0.52 };   // the host's key geometry (piano.js KEY.blackTop)
const FLOOR_Y = -2.3, FLOOR_FRONT_Z = 3.3;     // the host's floor and the piano's front edge
const W_WHITE = 0.84, W_BLACK = 0.50;
const BLOOM_SAFE = 0.80;           // linear luma cap for everything except the peak (host bloom threshold 0.9)
const LIGHT_CAP = 0.85;            // the fixed point of luma-bounded light: a stack of these layers never exceeds it
const METER = { y0: 0.60, height: 4.2, hold: 1.0, gravity: 6.0 };   // a hard peak falls for about 1.2 s after its hold
// Screen band (fraction of the drawing buffer height, from the bottom) where the roll fades out, under the
// host's words: 9:16 per the reconciliation (0.665-0.77); 16:9 clears the heading block.
const BAND = { "9:16": [0.665, 0.77], "16:9": [0.80, 0.95] };
const LANE_TEX = 1024, LANE_X0 = -27.5, LANE_SPAN = 55;

const LUMA = [0.2126729, 0.7151522, 0.0721750];
const clamp01 = (v) => Math.min(1, Math.max(0, v));

// OKLab relight into a preallocated array: keep the host colour's hue, choose lightness and chroma.
const lab = new Float64Array(3);
function relightInto(c, L, chroma, maxLuma, out, off) {
  const l = Math.cbrt(0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b);
  const m = Math.cbrt(0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b);
  const s = Math.cbrt(0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b);
  lab[1] = (1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s) * chroma;
  lab[2] = (0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s) * chroma;
  const ll = (L + 0.3963377774 * lab[1] + 0.2158037573 * lab[2]) ** 3;
  const mm = (L - 0.1055613458 * lab[1] - 0.0638541728 * lab[2]) ** 3;
  const ss = (L - 0.0894841775 * lab[1] - 1.2914855480 * lab[2]) ** 3;
  let r = Math.max(0, 4.0767416621 * ll - 3.3077115913 * mm + 0.2309699292 * ss);
  let g = Math.max(0, -1.2684380046 * ll + 2.6097574011 * mm - 0.3413193965 * ss);
  let b = Math.max(0, -0.0041960863 * ll - 0.7034186147 * mm + 1.7076147010 * ss);
  const y = LUMA[0] * r + LUMA[1] * g + LUMA[2] * b;
  if (y > maxLuma) { const k = maxLuma / y; r *= k; g *= k; b *= k; }
  out[off] = r; out[off + 1] = g; out[off + 2] = b;
}

// Luma-bounded light. Premultiplied colour c (luma l <= BLOOM_SAFE) with alpha l / LIGHT_CAP, blended One,
// OneMinusSrcAlpha: result luma = l + (1 - l / LIGHT_CAP) x dst luma, which is <= LIGHT_CAP whenever dst luma is, and
// < dst luma whenever dst is brighter. It is the smallest alpha that keeps that promise, so over a dark stage the layer
// still reads as added light.
const LIGHT_GLSL = `
  float lumaOf(vec3 c) { return dot(c, vec3(${LUMA.join(", ")})); }
  vec4 boundedLight(vec3 c) {
    c = max(c, vec3(0.0));
    float l = lumaOf(c);
    float k = min(1.0, ${BLOOM_SAFE.toFixed(2)} / max(l, 1e-5));
    return vec4(c * k, min(1.0, l * k / ${LIGHT_CAP.toFixed(2)}));
  }`;
const GLSL_COMMON = `
  ${LIGHT_GLSL}
  float bandFade(float fragY) { return 1.0 - smoothstep(uBand.x, uBand.y, fragY / uResY); }
  float pedalAt(float te) {
    float p = 0.0;
    for (int i = 0; i < ${PED_SEGS}; i++) {
      vec4 s = uPed[i];
      if (s.x < -1e5) continue;
      p = max(p, step(s.x, te) * step(te, s.y));
    }
    return p;
  }`;
const COLLAPSE = "gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return;";

export default {
  id: "synth-vandor",
  name: "Straight Roll",

  create(ctx) {
    const { THREE, scene, camera, renderer, keyX, isBlack, noteColor, KEY, TRAIL_Z } = ctx;
    const Z = TRAIL_Z + Z_OFF;
    const added = [];
    const tmpColor = new THREE.Color();
    const tmpV2 = new THREE.Vector2();
    const p0 = new THREE.Vector3(), p1 = new THREE.Vector3();

    const pedSegs = Array.from({ length: PED_SEGS }, () => new THREE.Vector4(-FAR, -FAR, 0, 0));
    const U = {
      uNow: { value: 0 }, uSpeed: { value: SPEED }, uBase: { value: BASE }, uZ: { value: Z },
      uTop: { value: 32 }, uWpp: { value: 0.03 }, uResY: { value: 1920 },
      uBand: { value: new THREE.Vector2(...BAND["9:16"]) }, uGlowOn: { value: 1 }, uPed: { value: pedSegs },
    };
    const premultiplied = {
      transparent: true, depthWrite: false, depthTest: true, blending: THREE.CustomBlending,
      blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
    };
    const additive = { transparent: true, depthWrite: false, depthTest: true, blending: THREE.AdditiveBlending };
    function unitQuad(geo) {
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0, 0.5, 0);       // x in [-0.5, 0.5], y in [0, 1]
      geo.setIndex(base.getIndex());
      geo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
      return geo;
    }
    function addMesh(obj, name, order) {
      obj.frustumCulled = false;
      obj.renderOrder = order;
      obj.name = `synth-vandor:${name}`;
      obj.visible = false;
      scene.add(obj);
      added.push(obj);
      return obj;
    }
    function instanced(geo, spec, count) {
      const attr = {};
      for (const [name, size] of spec) {
        const a = new THREE.InstancedBufferAttribute(new Float32Array(count * size), size);
        a.setUsage(THREE.DynamicDrawUsage);
        geo.setAttribute(name, a);
        attr[name] = a;
      }
      geo.instanceCount = count;
      return attr;
    }
    // Upload only the slots that changed since the last frame (one range per attribute set).
    const range = () => ({ lo: Infinity, hi: -1, list: null });
    const touch = (r, i) => { if (i < r.lo) r.lo = i; if (i > r.hi) r.hi = i; };
    function flush(r) {
      if (r.hi < r.lo) return;
      const list = r.list;
      for (let k = 0; k < list.length; k++) {
        const a = list[k];
        if (a.clearUpdateRanges) { a.clearUpdateRanges(); a.addUpdateRange(r.lo * a.itemSize, (r.hi - r.lo + 1) * a.itemSize); }
        a.needsUpdate = true;
      }
      r.lo = Infinity; r.hi = -1;
    }

    // ------------------------------------------------------------------ bars --
    const barGeo = unitQuad(new THREE.InstancedBufferGeometry());
    const B = instanced(barGeo, [["aX", 1], ["aW", 1], ["aBlack", 1], ["aT0", 1], ["aT1", 1], ["aT2", 1], ["aNext", 1],
                                 ["aVel", 1], ["aBody", 3], ["aRim", 3], ["aHot", 3]], SLOTS);
    B.aT0.array.fill(-FAR); B.aT1.array.fill(-FAR); B.aT2.array.fill(-FAR); B.aNext.array.fill(-FAR);
    const barRange = range();
    barRange.list = Object.values(B);
    const slotMidi = new Int16Array(SLOTS).fill(-1);

    const BAR_ATTR = `
      attribute float aX, aW, aBlack, aT0, aT1, aT2, aNext, aVel;
      attribute vec3 aBody, aRim, aHot;`;
    // Bottom, head and gap all come from the clock. A re-struck bar (aNext = the next onset on its key) ends at
    // least max(0.16 u, 5 px) before that onset, and never loses more than 45% of its length.
    const BAR_PLACE = `
      float top = uBase + (uNow - aT0) * uSpeed;
      float ended = step(aT2, uNow);
      float bot = uBase + (uNow - min(uNow, aT2)) * uSpeed;
      float len = max(top - bot, 0.0);
      float need = max(0.16, 5.0 * uWpp);
      float natural = (aNext - aT2) * uSpeed;
      bot += aNext > -1e5 ? clamp(need - natural, 0.0, 0.45 * len) * ended : 0.0;`;
    const BAR_VERT = `
      uniform float uNow, uSpeed, uBase, uZ, uTop, uWpp, uPass;
      ${BAR_ATTR}
      varying vec2 vP;
      varying float vW, vTop, vBot, vHold, vT0, vGone, vVel, vEnded;
      varying vec3 vBody, vRim, vHot;
      void main() {
        if (aT0 < -1e5 || abs(aBlack - uPass) > 0.5) { ${COLLAPSE} }
        ${BAR_PLACE}
        if (bot > uTop) { ${COLLAPSE} }
        float pad = max(0.08 * aW, 2.0 * uWpp);
        float y = mix(bot - pad, top + pad, position.y);
        float x = position.x * (aW + 2.0 * pad);
        vP = vec2(x, y);
        vW = aW; vTop = top; vBot = bot; vT0 = aT0; vVel = aVel; vEnded = ended;
        vGone = uNow - min(uNow, aT2);
        vHold = uBase + (uNow - min(uNow, aT1)) * uSpeed;   // above this height the finger was down
        vBody = aBody; vRim = aRim; vHot = aHot;
        gl_Position = projectionMatrix * viewMatrix * vec4(aX + x, y, uZ, 1.0);
      }`;
    const BAR_FRAG = `
      uniform float uNow, uSpeed, uBase, uResY, uGlowOn, uPass;
      uniform vec2 uBand;
      uniform vec4 uPed[${PED_SEGS}];
      varying vec2 vP;
      varying float vW, vTop, vBot, vHold, vT0, vGone, vVel, vEnded;
      varying vec3 vBody, vRim, vHot;
      ${GLSL_COMMON}
      float sdBar(vec2 p, vec2 b, float rTop, float rBot) {
        float r = p.y > 0.0 ? rTop : rBot;
        vec2 q = abs(p) - b + r;
        return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
      }
      void main() {
        float h = max(vTop - vBot, 1e-3);
        float hw = vW * 0.5;
        vec2 q = vP - vec2(0.0, 0.5 * (vTop + vBot));
        float d = sdBar(q, vec2(hw, 0.5 * h), min(hw, 0.5 * h) * 0.92, min(0.12 * vEnded, 0.5 * h));
        float fx = max(fwidth(vP.x), 1e-5), fy = max(fwidth(vP.y), 1e-5);
        float aa = max(fwidth(d), 1e-5) * 0.8;
        float inside = 1.0 - smoothstep(-aa, aa, d);
        if (inside < 0.002) discard;
        float te = clamp(uNow - (vP.y - uBase) / uSpeed, vT0, uNow);   // the moment this height sounded
        float v = clamp(vVel, 0.0, 1.0);
        float u = clamp(vP.x / hw, -1.0, 1.0);
        float nz = sqrt(max(1.0 - u * u, 0.0));
        float ped = pedalAt(te);
        float solid = smoothstep(vHold - fy, vHold + fy, vP.y);        // finger down at that moment
        // the column is the note's life: bright attack, a gentle sag, then history dims after the sound ends
        float sag = 0.74 + 0.26 * exp(-(te - vT0) / 4.0);
        float hist = 0.30 + 0.70 * (0.54 * exp(-vGone / 0.35) + 0.46 * exp(-vGone / 3.5));
        float diff = 0.60 + 0.40 * (0.85 * nz - 0.30 * u);
        float spec = exp(-pow((u + 0.40) / 0.17, 2.0)) * 0.42;
        float boost = mix(1.0, 1.22, ped);                               // finger + pedal = brightest
        vec3 solidC = vBody * diff * sag * hist * boost + vRim * spec * sag * hist;
        // velocity cap: its length is the velocity, and it keeps a settled brightness for the bar's life
        float headLen = min(h, vW * (0.45 + 2.1 * v));
        float capMask = smoothstep(vTop - headLen, vTop - headLen * 0.55, vP.y);
        vec3 capC = vBody * diff * (1.08 + 0.80 * v) * hist * boost + vRim * spec * 1.4 * hist;
        solidC = mix(solidC, capC, capMask);
        // pedal-only: a hollow rim over tinted glass (rim at least 0.07 u and 2.4 px)
        float rimT = max(0.07, 2.4 * fx);
        float ring = smoothstep(-rimT - aa, -rimT + aa, d);
        vec3 hollowC = mix(vBody * 0.50 * sag * hist, vRim * 1.05 * hist * (0.75 + 0.25 * nz), ring);
        vec3 col = mix(hollowC, solidC, solid);
        float a = mix(mix(0.24, 1.0, ring), 1.0, solid);
        if (uPass > 0.5) {
          // black-key bars carry a dark outline so they read over the white-key bars they overlap
          float ow = max(0.05, 1.6 * fx);
          float ol = smoothstep(-ow - aa, -ow + aa, d);
          col = mix(col, vec3(0.004, 0.005, 0.008), 0.85 * ol);
          a = max(a, 0.85 * ol);
        } else {
          float ow = max(0.035, 1.0 * fx);
          col *= 1.0 - 0.55 * smoothstep(-ow - aa, -ow + aa, d) * solid;
        }
        col = mix(col, vec3(lumaOf(col)), 0.45 * (1.0 - exp(-vGone / 3.5)));   // history desaturates
        col *= min(1.0, ${BLOOM_SAFE.toFixed(2)} / max(lumaOf(col), 1e-4));      // bloom guard
        // (the strike flash inside the cap is drawn by the peak-glow mesh, last, so no later layer dims it)
        a *= inside * bandFade(gl_FragCoord.y);
        if (a < 0.002) discard;
        gl_FragColor = vec4(col * a, a);
      }`;
    const barMat = (pass) => new THREE.ShaderMaterial({ ...premultiplied, uniforms: { ...U, uPass: { value: pass } },
                                                        vertexShader: BAR_VERT, fragmentShader: BAR_FRAG });
    const barsWhite = addMesh(new THREE.Mesh(barGeo, barMat(0)), "bars-white", 10);
    const barsBlack = addMesh(new THREE.Mesh(barGeo, barMat(1)), "bars-black", 11);

    // --------------------------------------------------------- peak glow --
    // THE PEAK, the one thing allowed to bloom, in one additive mesh that draws after everything else:
    //   - the strike flash inside the cap: v^1.35 x 2.2 e^(-age/0.16), where the finger was down;
    //   - a halo that hugs the cap: v^1.35 x (2.2 e^(-age/0.16) + 0.6 e^(-age/0.8)), reach W x (0.22 + 0.8 v), cut
    //     short once the sound ends.
    // Both are a little brighter with the pedal down at the onset. Nothing sums over time: each bar's glow only decays.
    const GLOW_VERT = `
      uniform float uNow, uSpeed, uBase, uZ, uTop, uWpp, uGlowOn;
      uniform vec4 uPed[${PED_SEGS}];
      ${BAR_ATTR}
      varying vec2 vP;
      varying float vW, vTop, vHL, vGI, vFlash, vHoldY, vLen, vReach, vY0, vY1;
      varying vec3 vHot;
      ${GLSL_COMMON.replace(/float bandFade[^\n]*\n/, "")}
      void main() {
        float age = uNow - aT0;
        if (aT0 < -1e5 || age < 0.0 || age > 3.0 || uGlowOn < 0.5) { ${COLLAPSE} }
        float v = clamp(aVel, 0.0, 1.0);
        float pk = pow(v, 1.35) * mix(1.0, 1.2, pedalAt(aT0));
        float flash = pk * 2.2 * exp(-age / 0.16);
        float gi = pk * (2.2 * exp(-age / 0.16) + 0.60 * exp(-age / 0.8));
        gi *= aT2 <= uNow ? exp(-(uNow - aT2) / 0.25) : 1.0;
        if (max(gi, flash) < 0.004) { ${COLLAPSE} }
        ${BAR_PLACE}
        float hl = min(max(len, 1e-3), aW * (0.45 + 2.1 * v));
        float reach = aW * (0.22 + 0.80 * v);
        vY0 = top - hl - 3.0 * reach; vY1 = top + 4.0 * reach;
        float x = position.x * (aW + 8.0 * reach);
        float y = mix(vY0, vY1, position.y);
        vP = vec2(x, y); vW = aW; vTop = top; vHL = hl; vGI = gi; vFlash = flash; vLen = max(len, 1e-3);
        vHoldY = uBase + (uNow - min(uNow, aT1)) * uSpeed;   // above this height the finger was down
        vReach = reach; vHot = aHot;
        gl_Position = projectionMatrix * viewMatrix * vec4(aX + x, y, uZ + 0.01, 1.0);
      }`;
    const GLOW_FRAG = `
      uniform float uResY;
      uniform vec2 uBand;
      varying vec2 vP;
      varying float vW, vTop, vHL, vGI, vFlash, vHoldY, vLen, vReach, vY0, vY1;
      varying vec3 vHot;
      float bandFade(float fragY) { return 1.0 - smoothstep(uBand.x, uBand.y, fragY / uResY); }
      void main() {
        float hw = vW * 0.5, r = min(hw, vHL * 0.5);
        vec2 q = abs(vP - vec2(0.0, vTop - vHL * 0.5)) - vec2(hw, vHL * 0.5) + r;
        float d = min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
        float halo = exp(-max(d, 0.0) / vReach);
        float core = 1.0 - smoothstep(-0.02, 0.02, d);
        float wx = 1.0 - smoothstep(0.65, 1.0, abs(vP.x) / (hw + 4.0 * vReach));
        float wy = smoothstep(vY0, vY0 + 1.5 * vReach, vP.y) * (1.0 - smoothstep(vY1 - 2.0 * vReach, vY1, vP.y));
        vec3 col = vHot * vGI * 0.55 * halo * (1.0 - 0.5 * core) * wx * wy;
        // the in-cap flash, clipped to the bar's own outline (top corners rounded as the bar's)
        float rt = 0.92 * min(hw, 0.5 * vLen);
        vec2 p = vP - vec2(0.0, vTop - vHL * 0.5);
        float rr = p.y > 0.0 ? rt : 0.0;
        vec2 qc = abs(p) - vec2(hw, vHL * 0.5) + rr;
        float dc = min(max(qc.x, qc.y), 0.0) + length(max(qc, 0.0)) - rr;
        float aa = max(fwidth(dc), 1e-5) * 0.8, fy = max(fwidth(vP.y), 1e-5);
        float inside = 1.0 - smoothstep(-aa, aa, dc);
        float u = clamp(vP.x / hw, -1.0, 1.0), nz = sqrt(max(1.0 - u * u, 0.0));
        float capMask = smoothstep(vTop - vHL, vTop - vHL * 0.55, vP.y);
        float solid = smoothstep(vHoldY - fy, vHoldY + fy, vP.y);
        col += vHot * vFlash * (0.45 + 0.55 * nz) * capMask * solid * inside;
        gl_FragColor = vec4(col * bandFade(gl_FragCoord.y), 1.0);
      }`;
    const glowMesh = addMesh(new THREE.Mesh(barGeo, new THREE.ShaderMaterial({ ...additive, uniforms: U,
      vertexShader: GLOW_VERT, fragmentShader: GLOW_FRAG })), "peak-glow", 17);   // last: the only additive draw

    // -------------------------------------------------------- peak-hold meter --
    // One instance per key: a glass sleeve from the meter floor up to the needle, and the needle. A strike
    // throws the needle to y0 + height x v (only if that beats where the needle is now), it holds 1 s, then
    // falls under gravity and fades as it lands.
    const LANES = KEY.last - KEY.first + 1;
    const meterGeo = unitQuad(new THREE.InstancedBufferGeometry());
    const M = instanced(meterGeo, [["aX", 1], ["aW", 1], ["aV", 1], ["aT", 1], ["aCol", 3]], LANES);
    M.aT.array.fill(-FAR);
    for (let m = KEY.first; m <= KEY.last; m++) {
      const i = m - KEY.first;
      M.aX.array[i] = keyX(m);
      M.aW.array[i] = isBlack(m) ? W_BLACK : W_WHITE;
    }
    const meterRange = range();
    meterRange.list = [M.aV, M.aT, M.aCol];
    const MU = { uY0: { value: METER.y0 }, uH: { value: METER.height }, uHold: { value: METER.hold }, uG: { value: METER.gravity } };
    const METER_VERT = `
      uniform float uNow, uZ, uWpp, uKind, uY0, uH, uHold, uG;
      attribute float aX, aW, aV, aT;
      attribute vec3 aCol;
      varying vec2 vP;
      varying float vW, vYT, vA, vTh;
      varying vec3 vC;
      void main() {
        float age = uNow - aT;
        if (aT < -1e5 || age < 0.0) { ${COLLAPSE} }
        float fall = max(age - uHold, 0.0);
        float yt = mix(uY0, uY0 + uH * aV, 1.0 - exp(-age / 0.025)) - 0.5 * uG * fall * fall;
        if (yt <= uY0 + 0.02) { ${COLLAPSE} }
        float th = max(0.09, 3.0 * uWpp);
        vec2 P;
        if (uKind < 0.5) {
          P = vec2(position.x * aW * 1.28, mix(uY0, yt, position.y));
        } else {
          float pad = 2.5 * uWpp;
          P = vec2(position.x * (aW * 1.62 + 2.0 * pad), mix(yt - 0.5 * th - pad, yt + 0.5 * th + pad, position.y));
        }
        vP = P; vW = aW; vYT = yt; vTh = th; vC = aCol;
        vA = smoothstep(uY0, uY0 + 0.35, yt);
        gl_Position = projectionMatrix * viewMatrix * vec4(aX + P.x, P.y, uZ + 0.04, 1.0);
      }`;
    const METER_FRAG = `
      uniform float uKind, uY0, uResY;
      uniform vec2 uBand;
      varying vec2 vP;
      varying float vW, vYT, vA, vTh;
      varying vec3 vC;
      float bandFade(float fragY) { return 1.0 - smoothstep(uBand.x, uBand.y, fragY / uResY); }
      void main() {
        float fx = max(fwidth(vP.x), 1e-5), fy = max(fwidth(vP.y), 1e-5);
        float fade = vA * bandFade(gl_FragCoord.y);
        if (uKind < 0.5) {
          float hw = vW * 0.64;
          float k = clamp((vP.y - uY0) / max(vYT - uY0, 1e-3), 0.0, 1.0);
          float edge = 1.0 - smoothstep(0.5 * fx, 2.0 * fx, hw - abs(vP.x));
          float a = (0.04 + 0.10 * k * k + edge * 0.30 * k) * fade;
          if (a < 0.002) discard;
          gl_FragColor = vec4(vC * a, a);
        } else {
          float dd = max((abs(vP.x) - vW * 0.81) / fx, (abs(vP.y - vYT) - 0.5 * vTh) / fy);   // in pixels
          float core = 1.0 - smoothstep(-0.7, 0.7, dd);
          float outline = 1.0 - smoothstep(0.5, 2.2, dd);
          float a = max(core, 0.75 * outline) * fade;
          if (a < 0.002) discard;
          gl_FragColor = vec4(vC * core * fade, a);   // the outline is dark: colour 0, alpha only
        }
      }`;
    const meterMat = (kind) => new THREE.ShaderMaterial({ ...premultiplied, uniforms: { ...U, ...MU, uKind: { value: kind } },
                                                          vertexShader: METER_VERT, fragmentShader: METER_FRAG });
    const sleeveMesh = addMesh(new THREE.Mesh(meterGeo, meterMat(0)), "meter-sleeve", 9);
    const needleMesh = addMesh(new THREE.Mesh(meterGeo, meterMat(1)), "meter-needle", 13);
    function needleLevel(i, t) {        // where lane i's needle is now, as a velocity (0..1)
      const T = M.aT.array[i];
      if (T < -1e5 || t < T) return 0;
      const fall = Math.max(t - T - METER.hold, 0);
      return Math.max(0, M.aV.array[i] - 0.5 * METER.gravity * fall * fall / METER.height);
    }

    // ------------------------------------------------------------ strike --
    const hitGeo = unitQuad(new THREE.InstancedBufferGeometry());
    const HA = instanced(hitGeo, [["aPos", 3], ["aCol", 3], ["aT0", 1], ["aVel", 1]], HITS);
    HA.aT0.array.fill(-FAR);
    const hitRange = range();
    hitRange.list = Object.values(HA);
    let hitNext = 0;
    const FLASH_VERT = `
      uniform float uNow;
      attribute vec3 aPos, aCol;
      attribute float aT0, aVel;
      varying vec2 vQ;
      varying float vK, vVel, vR, vL;
      varying vec3 vC;
      void main() {
        float age = uNow - aT0, dur = 0.14 + 0.26 * aVel;
        if (aT0 < -1e5 || age < 0.0 || age > dur) { ${COLLAPSE} }
        float R = 0.45 + 1.15 * aVel, L = 1.2 + 6.5 * aVel;
        vec2 ext = vec2(max(2.2 * R, 1.1 * L), 2.2 * R);
        vec4 mv = viewMatrix * vec4(aPos, 1.0);
        vQ = vec2(position.x, position.y - 0.5) * 2.0 * ext;
        mv.xy += vQ;
        vK = age / dur; vVel = aVel; vR = R; vL = L; vC = aCol;
        gl_Position = projectionMatrix * mv;
      }`;
    // Flash, ring and sparks are luma-bounded light (boundedLight): their colour is at most 0.55 luma, and the gains keep
    // the flash's centre (core + streak) at 0.55 x (0.85 + 0.40) = 0.69 luma at v = 1, the ring at 0.41 and a spark at 0.66.
    const FLASH_FRAG = `
      varying vec2 vQ;
      varying float vK, vVel, vR, vL;
      varying vec3 vC;
      ${LIGHT_GLSL}
      void main() {
        float fall = (1.0 - vK) * (1.0 - vK);
        float core = exp(-dot(vQ, vQ) / (vR * vR * 0.30));
        float streak = exp(-abs(vQ.y) / (0.025 + 0.025 * vVel)) * exp(-abs(vQ.x) / (vL * 0.4));
        gl_FragColor = boundedLight(vC * (core * (0.30 + 0.55 * vVel) + streak * (0.12 + 0.28 * vVel)) * fall);
      }`;
    const RING_VERT = `
      uniform float uNow;
      attribute vec3 aPos, aCol;
      attribute float aT0, aVel;
      varying vec2 vQ;
      varying float vK, vVel, vR;
      varying vec3 vC;
      void main() {
        float age = uNow - aT0, dur = 0.30 + 0.25 * aVel;
        if (aT0 < -1e5 || age < 0.0 || age > dur) { ${COLLAPSE} }
        float R = 0.25 + age * (4.0 + 9.0 * aVel);
        vQ = vec2(position.x, position.y - 0.5) * 2.0 * (R + 0.5);
        vK = age / dur; vVel = aVel; vR = R; vC = aCol;
        gl_Position = projectionMatrix * viewMatrix * vec4(aPos + vec3(vQ.x, 0.012, vQ.y), 1.0);   // across the key tops
      }`;
    const RING_FRAG = `
      varying vec2 vQ;
      varying float vK, vVel, vR;
      varying vec3 vC;
      ${LIGHT_GLSL}
      void main() {
        float r = length(vQ), w = 0.05 + 0.08 * vVel;
        float ring = exp(-pow((r - vR) / w, 2.0));
        gl_FragColor = boundedLight(vC * ring * pow(1.0 - vK, 1.5) * (0.25 + 0.50 * vVel));
      }`;
    const ringMesh = addMesh(new THREE.Mesh(hitGeo, new THREE.ShaderMaterial({ ...premultiplied, side: THREE.DoubleSide, uniforms: { uNow: U.uNow },
      vertexShader: RING_VERT, fragmentShader: RING_FRAG })), "strike-ring", 14);
    const flashMesh = addMesh(new THREE.Mesh(hitGeo, new THREE.ShaderMaterial({ ...premultiplied, uniforms: { uNow: U.uNow },
      vertexShader: FLASH_VERT, fragmentShader: FLASH_FRAG })), "strike-flash", 15);

    const sparkGeo = new THREE.BufferGeometry();
    const SA = {};
    for (const [name, size] of [["position", 3], ["aV", 3], ["aCol", 3], ["aT0", 1], ["aLife", 1], ["aSize", 1]]) {
      const a = new THREE.BufferAttribute(new Float32Array(SPARKS * size), size);
      a.setUsage(THREE.DynamicDrawUsage);
      sparkGeo.setAttribute(name, a);
      SA[name] = a;
    }
    SA.aT0.array.fill(-FAR);
    const sparkRange = range();
    sparkRange.list = Object.values(SA);
    let sparkNext = 0;
    const sparkU = { uNow: U.uNow, uPx: { value: 1000 } };
    const sparkMesh = addMesh(new THREE.Points(sparkGeo, new THREE.ShaderMaterial({ ...premultiplied, uniforms: sparkU,
      vertexShader: `
        uniform float uNow, uPx;
        attribute vec3 aV, aCol;
        attribute float aT0, aLife, aSize;
        varying vec3 vC;
        varying float vA;
        void main() {
          float age = uNow - aT0;
          if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
          float k = age / aLife;
          vec3 p = position + aV * (1.0 - exp(-age * 2.2)) / 2.2 + vec3(0.0, -2.8 * age * age, 0.0);
          vec4 mv = viewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = max(1.0, aSize * uPx * (1.0 - 0.6 * k) / max(-mv.z, 0.1));
          vA = (1.0 - k) * (1.0 - k);
          vC = aCol;
        }`,
      fragmentShader: `
        varying vec3 vC;
        varying float vA;
        ${LIGHT_GLSL}
        void main() {
          float r = length(gl_PointCoord - 0.5);
          float a = smoothstep(0.5, 0.0, r);
          if (a * vA < 0.004) discard;
          gl_FragColor = boundedLight(vC * a * a * vA * 1.2);
        }`,
    })), "sparks", 16);
    // A tiny deterministic generator: a replayed passage makes the same spray.
    let seed = 0x5f3759df;
    const rand = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);

    // ------------------------------------------------- lane board + glass floor --
    const laneData = new Uint8Array(LANE_TEX * 4);
    const laneTex = new THREE.DataTexture(laneData, LANE_TEX, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
    laneTex.magFilter = laneTex.minFilter = THREE.LinearFilter;
    laneTex.needsUpdate = true;
    const laneAcc = new Float32Array(LANE_TEX * 3);
    let laneWasLit = true;
    const BOARD_VERT = `
      uniform float uBase, uTop, uZ;
      varying vec2 vP;
      void main() {
        vP = vec2(position.x * ${LANE_SPAN.toFixed(1)}, mix(uBase, uTop + 2.0, position.y));
        gl_Position = projectionMatrix * viewMatrix * vec4(vP, uZ - 0.08, 1.0);
      }`;
    const BOARD_FRAG = `
      uniform float uNow, uSpeed, uBase, uResY;
      uniform vec2 uBand;
      uniform vec4 uPed[${PED_SEGS}];
      uniform sampler2D uLane;
      varying vec2 vP;
      ${GLSL_COMMON}
      void main() {
        float x = vP.x, y = vP.y;
        float fx = max(fwidth(x), 1e-4), fy = max(fwidth(y), 1e-4);
        float te = uNow - (y - uBase) / uSpeed;
        float ped = 0.0, lift = 0.0, liftGlow = 0.0;
        for (int i = 0; i < ${PED_SEGS}; i++) {
          vec4 p = uPed[i];
          if (p.x < -1e5) continue;
          ped = max(ped, step(p.x, te) * step(te, p.y));
          if (p.y < uNow) {
            float dl = abs(te - p.y) * uSpeed;
            lift = max(lift, 1.0 - smoothstep(0.066, 0.066 + 1.5 * fy, dl));
            liftGlow = max(liftGlow, exp(-dl / 0.45));
          }
        }
        // octave guides only (B|C), faint: no per-key grid behind the bars
        float od = abs(mod(x - 4.0 + 3.5, 7.0) - 3.5);
        float oct = (1.0 - smoothstep(0.0, 1.2 * fx + 0.012, od)) * (1.0 - smoothstep(0.12, 0.5, fx));
        float bd = abs(fract(te / 2.0 + 0.5) - 0.5) * 2.0 * uSpeed;   // a slow time line every 2 s
        float beat = 1.0 - smoothstep(0.02, 0.02 + 1.4 * fy, bd);
        vec3 cool = vec3(0.10, 0.13, 0.34), amber = vec3(1.0, 0.56, 0.16);
        vec3 col = mix(cool * 0.16, amber * 0.12, ped) * oct;         // guides run warm while the pedal holds
        col += cool * 0.30 * beat + amber * 0.012 * ped;
        col += amber * (lift + 0.22 * liftGlow);
        vec3 lane = texture2D(uLane, vec2((x - ${LANE_X0.toFixed(1)}) / ${LANE_SPAN.toFixed(1)}, 0.5)).rgb;
        float s = max(y, 0.0);
        col += lane * (0.70 * exp(-s / 1.1) + 0.08 * exp(-s / 9.0));
        col += (vec3(0.05, 0.065, 0.15) + 1.0 * lane) * exp(-abs(y - 0.03) / max(0.03, 1.2 * fy));   // contact line
        col *= (1.0 - smoothstep(25.5, 27.5, abs(x))) * bandFade(gl_FragCoord.y);
        gl_FragColor = boundedLight(col);   // light over the host's stage that can never lift a pixel past LIGHT_CAP
      }`;
    const boardMesh = addMesh(new THREE.Mesh(unitQuad(new THREE.BufferGeometry()), new THREE.ShaderMaterial({
      ...premultiplied, uniforms: { ...U, uLane: { value: laneTex } }, vertexShader: BOARD_VERT, fragmentShader: BOARD_FRAG,
    })), "lane-board", 5);
    const floorMesh = addMesh(new THREE.Mesh(unitQuad(new THREE.BufferGeometry()), new THREE.ShaderMaterial({
      ...premultiplied, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -8,
      uniforms: { uLane: { value: laneTex } },
      vertexShader: `
        varying vec2 vP;
        void main() {
          vP = vec2(position.x * ${LANE_SPAN.toFixed(1)}, position.y * 30.0);
          gl_Position = projectionMatrix * viewMatrix * vec4(vP.x, ${(FLOOR_Y + 0.004).toFixed(3)}, ${FLOOR_FRONT_Z.toFixed(2)} + vP.y, 1.0);
        }`,
      fragmentShader: `
        uniform sampler2D uLane;
        varying vec2 vP;
        ${LIGHT_GLSL}
        void main() {
          float u = (vP.x - ${LANE_X0.toFixed(1)}) / ${LANE_SPAN.toFixed(1)}, o = 0.5 / ${LANE_SPAN.toFixed(1)};
          vec3 l = (texture2D(uLane, vec2(u - o, 0.5)) + 2.0 * texture2D(uLane, vec2(u, 0.5)) + texture2D(uLane, vec2(u + o, 0.5))).rgb * 0.25;
          float k = 0.28 * exp(-vP.y / 5.5) * (1.0 - smoothstep(24.0, 27.5, abs(vP.x))) * smoothstep(0.0, 0.4, vP.y);
          gl_FragColor = boundedLight(l * k + vec3(0.004, 0.005, 0.012) * exp(-vP.y / 2.0));   // still glass: no ripple
        }`,
    })), "glass-floor", 6);

    // ------------------------------------------------------------ note state --
    const lastSlot = new Int32Array(128).fill(-1);
    const lastT0 = new Float32Array(128);
    const laneT0 = new Float32Array(128).fill(-FAR);
    const laneVel = new Float32Array(128);
    const laneHeld = new Uint8Array(128);
    const laneSound = new Uint8Array(128);
    const laneCol = new Float32Array(128 * 3);
    let pedalOpen = -1, pedalNext = 0;
    let barNext = 0;
    let framingId = "9:16";
    let active = false, lastT = 0;

    function applyFraming(f) {
      if (!f) return;
      framingId = BAND[f.id] ? f.id : (f.height > f.width ? "9:16" : "16:9");
      U.uBand.value.set(BAND[framingId][0], BAND[framingId][1]);
    }
    applyFraming(ctx.framing);

    const owns = (m) => lastSlot[m] >= 0 && B.aT0.array[lastSlot[m]] === lastT0[m];
    function allocSlot(t) {
      const T0 = B.aT0.array, T2 = B.aT2.array, limit = U.uTop.value + 6;
      for (let i = 0; i < SLOTS; i++) {
        const j = (barNext + i) % SLOTS;
        if (T0[j] < -1e5 || (T2[j] < t && BASE + (t - T2[j]) * SPEED > limit)) { barNext = (j + 1) % SLOTS; return j; }
      }
      let oldest = 0;
      for (let j = 1; j < SLOTS; j++) if (T0[j] < T0[oldest]) oldest = j;
      barNext = (oldest + 1) % SLOTS;
      return oldest;
    }
    function endBar(m, t, sound) {
      if (!owns(m)) return;
      const j = lastSlot[m];
      const tt = Math.max(t, B.aT0.array[j]);
      if (B.aT1.array[j] > tt) B.aT1.array[j] = tt;
      if (sound && B.aT2.array[j] > tt) B.aT2.array[j] = tt;
      touch(barRange, j);
    }

    function strike(m, v, t, black) {
      const x = keyX(m), y = black ? KEY_TOP.black : KEY_TOP.white;
      const h = hitNext;
      hitNext = (hitNext + 1) % HITS;
      HA.aPos.array[h * 3] = x; HA.aPos.array[h * 3 + 1] = y + 0.04; HA.aPos.array[h * 3 + 2] = Z + 0.02;
      relightInto(tmpColor, 0.78, 1.25, 0.55, HA.aCol.array, h * 3);
      HA.aT0.array[h] = t;
      HA.aVel.array[h] = v;
      touch(hitRange, h);
      const n = Math.round(3 + 36 * v * v);
      relightInto(tmpColor, 0.86, 1.25, 0.55, laneCol, 0);   // scratch row 0 (midi 0 never sounds)
      for (let i = 0; i < n; i++) {
        const k = sparkNext;
        sparkNext = (sparkNext + 1) % SPARKS;
        const up = (1.5 + 7.0 * v) * (0.35 + 0.65 * rand());
        SA.position.array[k * 3] = x + (rand() - 0.5) * (black ? 0.4 : 0.7);
        SA.position.array[k * 3 + 1] = y + 0.08;
        SA.position.array[k * 3 + 2] = Z + 0.05;
        SA.aV.array[k * 3] = (rand() - 0.5) * (1.0 + 5.0 * v);
        SA.aV.array[k * 3 + 1] = up;
        SA.aV.array[k * 3 + 2] = rand() * 2.0 * v;
        SA.aCol.array[k * 3] = laneCol[0]; SA.aCol.array[k * 3 + 1] = laneCol[1]; SA.aCol.array[k * 3 + 2] = laneCol[2];
        SA.aT0.array[k] = t;
        SA.aLife.array[k] = 0.25 + 0.55 * rand() * (0.5 + v);
        SA.aSize.array[k] = 0.05 + 0.10 * rand() * (0.5 + v);
        touch(sparkRange, k);
      }
    }

    // ---------------------------------------------------------- per frame --
    function paintLanes(t) {
      let lit = false;
      laneAcc.fill(0);
      for (let m = KEY.first; m <= KEY.last; m++) {
        const age = t - laneT0[m];
        let e = 0;
        if (laneSound[m]) e = laneHeld[m] ? 0.45 + 0.35 * laneVel[m] : 0.16;
        if (age >= 0 && age < 1.2) e += 0.9 * laneVel[m] * Math.exp(-age / 0.22);
        if (e < 0.003) continue;
        lit = true;
        const kx = keyX(m), sig = (isBlack(m) ? W_BLACK : W_WHITE) * 0.42;
        const i0 = Math.max(0, Math.floor((kx - 3 * sig - LANE_X0) / LANE_SPAN * LANE_TEX));
        const i1 = Math.min(LANE_TEX - 1, Math.ceil((kx + 3 * sig - LANE_X0) / LANE_SPAN * LANE_TEX));
        const r = laneCol[m * 3] * e, g = laneCol[m * 3 + 1] * e, b = laneCol[m * 3 + 2] * e;
        for (let i = i0; i <= i1; i++) {
          const wx = (i + 0.5) / LANE_TEX * LANE_SPAN + LANE_X0;
          const w = Math.exp(-((wx - kx) ** 2) / (2 * sig * sig));
          laneAcc[i * 3] += r * w; laneAcc[i * 3 + 1] += g * w; laneAcc[i * 3 + 2] += b * w;
        }
      }
      if (!lit && !laneWasLit) return;
      for (let i = 0; i < LANE_TEX; i++) {
        laneData[i * 4] = Math.min(255, laneAcc[i * 3] * 255);
        laneData[i * 4 + 1] = Math.min(255, laneAcc[i * 3 + 1] * 255);
        laneData[i * 4 + 2] = Math.min(255, laneAcc[i * 3 + 2] * 255);
        laneData[i * 4 + 3] = 255;
      }
      laneTex.needsUpdate = true;
      laneWasLit = lit;
    }

    function liveBars(t) {
      const out = { white: 0, black: 0, held: 0, tails: 0 };
      const top = U.uTop.value;
      for (let j = 0; j < SLOTS; j++) {
        const t0 = B.aT0.array[j];
        if (t0 < -1e5 || t0 > t) continue;
        const t2 = B.aT2.array[j];
        if (BASE + (t - Math.min(t, t2)) * SPEED > top) continue;
        if (B.aBlack.array[j] > 0.5) out.black++; else out.white++;
        if (B.aT1.array[j] > t) out.held++;
        else if (t2 > B.aT1.array[j] + 1e-6) out.tails++;
      }
      return out;
    }

    return {
      noteOn(m, vel, t) {
        const v = clamp01(vel / 127);
        const black = isBlack(m);
        // a re-strike: the previous bar on this key becomes a bead that ends before this onset
        if (owns(m)) {
          const j = lastSlot[m];
          if (B.aT2.array[j] >= t - 1.0) { endBar(m, t, true); B.aNext.array[j] = t; touch(barRange, j); }
        }
        const j = allocSlot(t);
        noteColor(m, vel, tmpColor);
        B.aX.array[j] = keyX(m);
        B.aW.array[j] = black ? W_BLACK : W_WHITE;
        B.aBlack.array[j] = black ? 1 : 0;
        B.aT0.array[j] = t; B.aT1.array[j] = FAR; B.aT2.array[j] = FAR; B.aNext.array[j] = -FAR;
        B.aVel.array[j] = v;
        relightInto(tmpColor, 0.48 + 0.30 * v ** 0.8, 1 + 0.40 * v, 0.62, B.aBody.array, j * 3);
        relightInto(tmpColor, 0.80, 1.10, 0.72, B.aRim.array, j * 3);
        relightInto(tmpColor, 0.82, 1.30, 0.70, B.aHot.array, j * 3);
        touch(barRange, j);
        slotMidi[j] = m;
        lastSlot[m] = j;
        lastT0[m] = B.aT0.array[j];
        laneT0[m] = t; laneVel[m] = v; laneHeld[m] = 1; laneSound[m] = 1;
        relightInto(tmpColor, 0.70, 1.10, 0.50, laneCol, m * 3);
        if (m >= KEY.first && m <= KEY.last) {
          const i = m - KEY.first;
          if (v >= needleLevel(i, t) - 1e-3) {
            M.aV.array[i] = v;
            M.aT.array[i] = t;
            relightInto(tmpColor, 0.86, 1.20, 0.76, M.aCol.array, i * 3);
            touch(meterRange, i);
          }
        }
        strike(m, v, t, black);
      },
      noteRelease(m, t) {
        endBar(m, t, false);
        laneHeld[m] = 0;
      },
      noteEnd(m, t) {
        endBar(m, t, true);
        laneHeld[m] = 0;
        laneSound[m] = 0;
      },
      pedal(down, raw, t) {
        if (down) {
          if (pedalOpen >= 0) return;
          pedalOpen = pedalNext;
          pedalNext = (pedalNext + 1) % PED_SEGS;
          pedSegs[pedalOpen].set(t, FAR, 0, 0);
        } else {
          if (pedalOpen < 0) return;
          pedSegs[pedalOpen].y = t;
          pedalOpen = -1;
        }
      },
      update(dt, t, frame) {
        lastT = t;
        U.uNow.value = t;
        if (frame && frame.framing && frame.framing.id !== framingId) applyFraming(frame.framing);
        const top = frame && frame.view && Number.isFinite(frame.view.top) ? frame.view.top : 30;
        U.uTop.value = top + 2;
        renderer.getDrawingBufferSize(tmpV2);
        U.uResY.value = tmpV2.y;
        camera.updateMatrixWorld();
        p0.set(camera.position.x, 1, Z).project(camera);
        p1.set(camera.position.x, 2, Z).project(camera);
        const pxPerUnit = Math.abs(p1.y - p0.y) * 0.5 * tmpV2.y;
        U.uWpp.value = pxPerUnit > 1e-3 ? 1 / pxPerUnit : 0.03;
        sparkU.uPx.value = tmpV2.y / (2 * Math.tan(camera.fov * Math.PI / 360));
        paintLanes(t);
        flush(barRange); flush(meterRange); flush(hitRange); flush(sparkRange);
      },
      resize(framing) {
        applyFraming(framing);
      },
      setActive(on) {
        active = !!on;
        for (let i = 0; i < added.length; i++) added[i].visible = active;
      },
      dispose() {
        const geos = new Set(), mats = new Set();
        for (const obj of added) { scene.remove(obj); geos.add(obj.geometry); mats.add(obj.material); }
        for (const g of geos) g.dispose();
        for (const m of mats) m.dispose();
        laneTex.dispose();
        added.length = 0;
        lastSlot.fill(-1);
      },
      stats(t = lastT) {
        const bars = liveBars(t);
        let needles = 0;
        for (let i = 0; i < LANES; i++) if (needleLevel(i, t) > 0.005) needles++;
        return { trailsLive: bars.white + bars.black, trailCap: SLOTS, bars, needles, pedalOpen: pedalOpen >= 0, active };
      },
      // For the harness and the receipts: switches and the facts behind the pictures.
      debug: {
        constants: { SPEED, BASE, Z, W_WHITE, W_BLACK, METER, BAND, BLOOM_SAFE, SLOTS },
        objects: () => [...added],
        setGlow(on) { U.uGlowOn.value = on ? 1 : 0; glowMesh.visible = active && !!on; },
        drawCalls: () => added.filter((o) => o.visible).length,
        // every live bar in drawing-buffer pixels: [{m, black, t0, t1, t2, next, xPx, topPx, botPx}]
        barsOnScreen(t = lastT) {
          const out = [];
          const H = U.uResY.value;
          renderer.getDrawingBufferSize(tmpV2);
          const Wd = tmpV2.x;
          for (let j = 0; j < SLOTS; j++) {
            const t0 = B.aT0.array[j];
            if (t0 < -1e5 || t0 > t) continue;
            const t1 = B.aT1.array[j], t2 = B.aT2.array[j], nx = B.aNext.array[j];
            const top = BASE + (t - t0) * SPEED;
            let bot = BASE + (t - Math.min(t, t2)) * SPEED;
            if (bot > U.uTop.value) continue;
            const len = Math.max(top - bot, 0);
            if (nx > -1e5 && t2 <= t) bot += Math.min(Math.max(Math.max(0.16, 5 * U.uWpp.value) - (nx - t2) * SPEED, 0), 0.45 * len);
            const x = B.aX.array[j];
            const hold = Math.max(bot, BASE + (t - Math.min(t, t1)) * SPEED);   // below this the finger was up
            p0.set(x, hold, Z).project(camera);
            const holdPx = +((1 - p0.y) / 2 * H).toFixed(1);
            p0.set(x + 0.5 * B.aW.array[j], top, Z).project(camera);
            const halfWPx = (p0.x + 1) / 2 * Wd;
            p0.set(x, top, Z).project(camera);
            p1.set(x, bot, Z).project(camera);
            out.push({ m: slotMidi[j], black: B.aBlack.array[j] > 0.5, t0: +t0.toFixed(4), t1: t1 > 1e5 ? null : +t1.toFixed(4),
                       t2: t2 > 1e5 ? null : +t2.toFixed(4), next: nx > -1e5 ? +nx.toFixed(4) : null,
                       xPx: +((p0.x + 1) / 2 * Wd).toFixed(1), halfWPx: +(halfWPx - (p0.x + 1) / 2 * Wd).toFixed(1),
                       topPx: +((1 - p0.y) / 2 * H).toFixed(1), holdPx, botPx: +((1 - p1.y) / 2 * H).toFixed(1) });
          }
          return out.sort((a, b) => a.m - b.m || a.t0 - b.t0);
        },
        needles(t = lastT) {
          const out = [];
          for (let i = 0; i < LANES; i++) { const lv = needleLevel(i, t); if (lv > 0.005) out.push({ m: i + KEY.first, level: +lv.toFixed(3) }); }
          return out;
        },
      },
    };
  },
};
