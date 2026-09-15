// Upright Roll — arsenal/web/piano/schemes/upright-roll.js  (ES module, a piano scheme)
// A piano roll stood on its end (PIANO-V2-SPEC.md 6.3, panel-synthesis.md "Build first"): every note
// grows straight up out of the key that played it.
//   - solid body   = the finger is on the key (kept under the bloom threshold)
//   - onset cap    = the strike; its thickness is the velocity, and it is the only part that blooms
//   - hollow tail  = the pedal holds the note after the key came up; it decays to a floor
//   - one cut      = a pedal lift ends every hollow tail at the same instant, so on one line
//   - amber lane   = the pedal itself, drawn once, as a 12 px strip pinned inside the left edge
//
// Rules this module keeps (6.2): normal (premultiplied) blending only, never summed light; no halo,
// no foot glow; sparks only above velocity 0.7; the roll fades to nothing before the protected top
// band; every position comes from the clock (uNow and the event times), never from frame counts.
//
// Like neon-trails.js, everything comes from ctx: no imports, so no import map is needed.

const FAR = 1e6;
const SPEED = 5.6;                         // world units per second (one unit = one white-key pitch)
const POOL = { white: 384, black: 256 };   // slots per pool; recycled, so a long session never grows
const RECYCLE_Y = 80;                      // a bar whose bottom has risen past this is gone for good
const LANE_MAX = 64;
const SPARK_MAX = 640;

const WHITE_W = 0.72, BLACK_W = 0.40, BLACK_EDGE = 0.05;
const CAP_BASE = 0.10, CAP_VEL = 0.22;             // cap height = 0.10 + 0.22 v (world units)
const CAP_FLASH = 1.2, CAP_FLASH_TAU = 0.12;       // cap brightness x (1 + 1.2 exp(-age / 0.12))
const TAIL_A0 = 0.7, TAIL_TAU = 1.5, TAIL_FLOOR = 0.28, TAIL_FILL = 0.07;
const SPARK_MIN_VEL = 0.7;
// piano-next.js renders bloom with UnrealBloomPass(threshold 0.9) on linear luminance (Rec.709 weights).
// Bodies, tails and the lane are clamped below BODY_LUMA_MAX in the shader, so only caps and sparks cross.
const BLOOM_THRESHOLD = 0.9;
const BODY_LUMA_MAX = 0.8;

// The protected top band, in framing pixels from the top: the roll is fully transparent above fadeEnd
// and fully opaque below fadeStart. 9:16 follows the spec band (y 230-630); 16:9 clears the staff's
// bottom line at the host's LAYOUT (y ~452).
const BAND = {
  "9:16": { fadeEnd: 650, fadeStart: 860 },
  "16:9": { fadeEnd: 470, fadeStart: 600 },
};
const LANE = { widthPx: 12, insetPx: 8 };

// For the host: this scheme wants the keyboard a little higher in 9:16, so the key fronts sit at or
// above y 1520 (spec 6.3). The camera is the core's, so the host applies it (or ignores it).
// Measured in the harness at the follow camera's tightest span (16 keys): the white keys' front bottom
// edge lands at y 1607 with the host's 0.25, 1530 with the panel's 0.21, and ~1511 with 0.20.
const VIEW_HINT = Object.freeze({ lensShift: Object.freeze({ "9:16": 0.20 }) });

const LUMA = [0.2126729, 0.7151522, 0.0721750];
const luma = (c) => LUMA[0] * c[0] + LUMA[1] * c[1] + LUMA[2] * c[2];

// OKLab <-> linear sRGB, so the scheme can re-light the host's note colour (any colour mode) while
// keeping its hue: body, cap and tail differ in lightness, not in hue.
function linearToOklab(r, g, b) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
          1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
          0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
function oklabToLinear(L, a, b) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [Math.max(0, 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
          Math.max(0, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
          Math.max(0, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)];
}
function relight(c, L, chroma = 1, maxLuma = Infinity) {
  const [, a, b] = linearToOklab(c.r, c.g, c.b);
  const rgb = oklabToLinear(L, a * chroma, b * chroma);
  const y = luma(rgb);
  if (y > maxLuma) for (let i = 0; i < 3; i++) rgb[i] *= maxLuma / y;
  return rgb;
}

const GLSL_COMMON = `
  float lumaOf(vec3 c) { return dot(c, vec3(${LUMA.join(", ")})); }
  // 1 below the band, 0 above it: screen-space, so the band holds whatever the camera does
  float bandFade(float fragY) {
    float yTop = uFrameH - fragY / uPR;
    return smoothstep(uFadeEnd, uFadeStart, yTop);
  }`;

export default {
  id: "upright-roll",
  name: "Upright Roll",
  view: VIEW_HINT,

  create(ctx) {
    const { THREE, scene, camera, renderer, keyX, isBlack, noteColor, RAIL_Y, TRAIL_Z } = ctx;
    const added = [];
    const tmpColor = new THREE.Color();

    const shared = {
      uNow: { value: 0 }, uSpeed: { value: SPEED }, uBaseY: { value: RAIL_Y }, uZ: { value: TRAIL_Z },
      uTopW: { value: 30 }, uFrameH: { value: 1920 }, uPR: { value: 1 },
      uFadeEnd: { value: BAND["9:16"].fadeEnd }, uFadeStart: { value: BAND["9:16"].fadeStart },
      uBodyMax: { value: BODY_LUMA_MAX }, uNoCap: { value: 0 },
    };
    const premultiplied = {
      transparent: true, depthWrite: false, blending: THREE.CustomBlending,
      blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
    };

    // ----------------------------------------------------------------- bars --
    // One instanced quad per strike. The quad spans from the sound's end (bottom) to the onset plus
    // the cap (top); the fragment shader splits it into tail, body and cap by the event times.
    const BAR_VERT = `
      uniform float uNow, uSpeed, uBaseY, uZ, uTopW;
      attribute float aX, aW, aT0, aT1, aT2, aVel;
      attribute vec3 aBody, aCap, aTail;
      varying vec2 vP;
      varying float vW, vTop, vHold, vBot, vCapH, vAge, vEnded;
      varying vec3 vBody, vCapC, vTailC;
      void main() {
        float bot = uBaseY + (uNow - min(uNow, aT2)) * uSpeed;
        if (aT0 < -1e5 || bot > uTopW) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
        float top = uBaseY + (uNow - aT0) * uSpeed;
        float capH = ${CAP_BASE.toFixed(3)} + ${CAP_VEL.toFixed(3)} * aVel;
        float y = mix(bot, top + capH, position.y);
        vP = vec2(position.x * aW, y);
        vW = aW; vTop = top; vBot = bot; vCapH = capH; vAge = uNow - aT0;
        vHold = uBaseY + (uNow - min(uNow, aT1)) * uSpeed;
        vEnded = aT2 <= uNow ? 1.0 : 0.0;
        vBody = aBody; vCapC = aCap; vTailC = aTail;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(aX + vP.x, y, uZ, 1.0);
      }`;
    const BAR_FRAG = `
      uniform float uSpeed, uFrameH, uPR, uFadeEnd, uFadeStart, uBodyMax, uNoCap, uBlack;
      varying vec2 vP;
      varying float vW, vTop, vHold, vBot, vCapH, vAge, vEnded;
      varying vec3 vBody, vCapC, vTailC;
      ${GLSL_COMMON}
      void main() {
        float fade = bandFade(gl_FragCoord.y);
        if (fade <= 0.0) discard;
        float y = vP.y;
        float halfW = vW * 0.5;
        float fx = max(fwidth(vP.x), 1e-5), fy = max(fwidth(y), 1e-5);
        float side = halfW - abs(vP.x);            // world units in from the side edge
        float across = abs(vP.x) / halfW;          // 0 at the axis, 1 at the edge
        vec3 col;
        float a = 1.0;
        bool cap = y > vTop;
        if (cap) {
          // onset cap: the strike. Rounded top corners; a flash that dies in about a quarter second.
          if (uNoCap > 0.5) discard;
          float r = min(halfW, vCapH) * 0.55;
          vec2 q = vec2(abs(vP.x) - (halfW - r), y - (vTop + vCapH - r));
          float d = length(max(q, 0.0)) - r;
          a = 1.0 - smoothstep(-fx, fx, d);
          col = vCapC * (1.0 + ${CAP_FLASH.toFixed(2)} * exp(-vAge / ${CAP_FLASH_TAU.toFixed(3)})) * (1.0 - 0.10 * across * across);
          // a hairline seam where the cap meets the body keeps the cap a separate, readable object
          float seam = 1.0 - smoothstep(0.6, 1.6, (y - vTop) / fy);
          col *= 1.0 - 0.35 * seam * step(vHold, vTop - 0.001);
        } else if (y >= vHold) {
          // finger-held body: solid, lit a little brighter along the axis, a little darker at the rim
          col = vBody * (0.80 + 0.20 * (1.0 - across * across));
        } else {
          // pedal tail: a hollow tube whose outline decays to a floor; the cut line stays readable
          float tailAge = (vHold - y) / uSpeed;
          float edgeA = max(${TAIL_FLOOR.toFixed(2)}, ${TAIL_A0.toFixed(2)} * exp(-tailAge / ${TAIL_TAU.toFixed(2)}));
          float dSide = side / fx;
          float dBot = (y - vBot) / fy;
          float sideLine = 1.0 - smoothstep(1.4, 2.4, dSide);
          float cutLine = vEnded * (1.0 - smoothstep(1.4, 2.4, dBot));
          a = max(${TAIL_FILL.toFixed(2)}, max(sideLine * edgeA, cutLine * max(edgeA, 0.62)));
          col = vTailC;
        }
        if (uBlack > 0.5 && y >= vHold) {
          // black-key bars carry a dark rim, so they read on top of the white bars they overlap
          float rim = 1.0 - smoothstep(${BLACK_EDGE.toFixed(3)} - fx, ${BLACK_EDGE.toFixed(3)} + fx, side);
          col = mix(col, vec3(0.004, 0.005, 0.008), rim);
          a = max(a, rim * step(vBot, y));
        }
        if (!cap) col *= min(1.0, uBodyMax / max(lumaOf(col), 1e-4));   // the bloom guard
        a *= fade;
        if (a < 0.002) discard;
        gl_FragColor = vec4(col * a, a);
      }`;

    function makePool(kind) {
      const max = POOL[kind];
      const geo = new THREE.InstancedBufferGeometry();
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0, 0.5, 0);
      geo.setIndex(base.getIndex());
      geo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
      const attr = {};
      for (const [name, size] of [["aX", 1], ["aW", 1], ["aT0", 1], ["aT1", 1], ["aT2", 1], ["aVel", 1],
                                  ["aBody", 3], ["aCap", 3], ["aTail", 3]]) {
        const a = new THREE.InstancedBufferAttribute(new Float32Array(max * size), size);
        a.setUsage(THREE.DynamicDrawUsage);
        geo.setAttribute(name, a);
        attr[name] = a;
      }
      attr.aT0.array.fill(-FAR);
      attr.aT1.array.fill(-FAR);
      attr.aT2.array.fill(-FAR);
      geo.instanceCount = max;
      const mat = new THREE.ShaderMaterial({ ...premultiplied, uniforms: { ...shared, uBlack: { value: kind === "black" ? 1 : 0 } },
                                             vertexShader: BAR_VERT, fragmentShader: BAR_FRAG });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.frustumCulled = false;
      mesh.renderOrder = kind === "black" ? 12 : 11;   // black keys over white
      mesh.name = `upright-roll:${kind}`;
      scene.add(mesh);
      added.push(mesh);
      return { kind, max, geo, mat, mesh, attr, next: 0, dirty: false };
    }
    const pools = { white: makePool("white"), black: makePool("black") };

    function barStart(m, vel, t) {
      const pool = isBlack(m) ? pools.black : pools.white;
      const A = pool.attr;
      let slot = -1;
      for (let i = 0; i < pool.max; i++) {
        const j = (pool.next + i) % pool.max;
        if (A.aT0.array[j] < -1e5 || (A.aT2.array[j] < t && RAIL_Y + (t - A.aT2.array[j]) * SPEED > RECYCLE_Y)) { slot = j; break; }
      }
      if (slot < 0) {  // every slot busy: recycle the oldest onset
        slot = 0;
        for (let j = 1; j < pool.max; j++) if (A.aT0.array[j] < A.aT0.array[slot]) slot = j;
      }
      pool.next = (slot + 1) % pool.max;
      const v = Math.min(1, Math.max(0, vel / 127));
      noteColor(m, vel, tmpColor);
      A.aX.array[slot] = keyX(m);
      A.aW.array[slot] = pool.kind === "black" ? BLACK_W : WHITE_W;
      A.aT0.array[slot] = t;
      A.aT1.array[slot] = FAR;
      A.aT2.array[slot] = FAR;
      A.aVel.array[slot] = v;
      A.aBody.array.set(relight(tmpColor, 0.46 + 0.36 * v ** 0.8, 1.0, BODY_LUMA_MAX - 0.05), slot * 3);
      A.aCap.array.set(relight(tmpColor, 0.92, 0.55), slot * 3);
      A.aTail.array.set(relight(tmpColor, 0.80, 1.0, BODY_LUMA_MAX - 0.05), slot * 3);
      pool.dirty = true;
      return { pool, slot, t0: Math.fround(t), m };
    }
    const owns = (ref) => ref && ref.pool.attr.aT0.array[ref.slot] === ref.t0;
    // A release or end never precedes its own onset (the core's clock is monotonic; this keeps a bar whole anyway).
    function barRelease(ref, t) {
      if (!owns(ref)) return;
      const A = ref.pool.attr;
      t = Math.max(t, A.aT0.array[ref.slot]);
      A.aT1.array[ref.slot] = Math.min(A.aT1.array[ref.slot], t);
      ref.pool.dirty = true;
    }
    function barEnd(ref, t) {
      if (!owns(ref)) return;
      const A = ref.pool.attr;
      t = Math.max(t, A.aT0.array[ref.slot]);
      A.aT1.array[ref.slot] = Math.min(A.aT1.array[ref.slot], t);
      A.aT2.array[ref.slot] = Math.min(A.aT2.array[ref.slot], t);
      ref.pool.dirty = true;
    }

    // ---------------------------------------------------------- pedal lane --
    // Screen-pinned in x (a 12 px strip inside the left edge), world-true in y: each end of a pedal
    // segment is projected from the trail plane at the lane's own depth, so it lines up with the bars.
    const laneUniforms = { ...shared, uLaneX: { value: -8 }, uNdcX0: { value: -1 }, uNdcX1: { value: -0.98 },
                           uAmber: { value: new THREE.Vector3(...oklabToLinear(0.80, 0.045, 0.125)) } };
    const laneGeo = new THREE.InstancedBufferGeometry();
    {
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0.5, 0.5, 0);
      laneGeo.setIndex(base.getIndex());
      laneGeo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
    }
    const laneAttr = {};
    for (const name of ["aT0", "aT2", "aKind"]) {
      const a = new THREE.InstancedBufferAttribute(new Float32Array(LANE_MAX + 1), 1);
      a.setUsage(THREE.DynamicDrawUsage);
      laneGeo.setAttribute(name, a);
      laneAttr[name] = a;
    }
    laneAttr.aT0.array.fill(-FAR);
    laneAttr.aT2.array.fill(-FAR);
    laneAttr.aKind.array.fill(1);
    laneAttr.aKind.array[LANE_MAX] = 0;   // the last instance is the always-on track
    laneAttr.aT0.array[LANE_MAX] = 0;
    laneGeo.instanceCount = LANE_MAX + 1;
    const laneMat = new THREE.ShaderMaterial({
      ...premultiplied, depthTest: false, uniforms: laneUniforms,
      vertexShader: `
        uniform float uNow, uSpeed, uBaseY, uZ, uTopW, uLaneX, uNdcX0, uNdcX1;
        attribute float aT0, aT2, aKind;
        varying float vY, vBot, vTop, vKind, vEnded, vDown;
        float ndcY(float y) { vec4 c = projectionMatrix * viewMatrix * vec4(uLaneX, y, uZ, 1.0); return c.y / c.w; }
        void main() {
          float bot = uBaseY, top = uTopW + 2.0;
          if (aKind > 0.5) {
            bot = uBaseY + (uNow - min(uNow, aT2)) * uSpeed;
            top = uBaseY + (uNow - aT0) * uSpeed;
            if (aT0 < -1e5 || bot > uTopW) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
          }
          vY = mix(bot, top, position.y);
          vBot = bot; vTop = top; vKind = aKind;
          vEnded = aT2 <= uNow ? 1.0 : 0.0;
          vDown = aT2 > uNow ? 1.0 : 0.0;
          gl_Position = vec4(mix(uNdcX0, uNdcX1, position.x), mix(ndcY(bot), ndcY(top), position.y), 0.0, 1.0);
        }`,
      fragmentShader: `
        uniform float uFrameH, uPR, uFadeEnd, uFadeStart, uBodyMax;
        uniform vec3 uAmber;
        varying float vY, vBot, vTop, vKind, vEnded, vDown;
        ${GLSL_COMMON}
        void main() {
          float fade = bandFade(gl_FragCoord.y);
          if (fade <= 0.0) discard;
          float fy = max(fwidth(vY), 1e-5);
          float a;
          vec3 col = uAmber;
          if (vKind < 0.5) {
            a = 0.10;                                   // the track: the lane is visible with the pedal up
          } else {
            float edge = 1.0 - smoothstep(1.0, 2.0, min((vY - vBot) / fy + (1.0 - vEnded) * 99.0, (vTop - vY) / fy));
            a = mix(0.78, 1.0, edge);
            col *= mix(1.0, 1.12, edge);
          }
          col *= min(1.0, uBodyMax / max(lumaOf(col), 1e-4));
          a *= fade;
          if (a < 0.002) discard;
          gl_FragColor = vec4(col * a, a);
        }`,
    });
    const laneMesh = new THREE.Mesh(laneGeo, laneMat);
    laneMesh.frustumCulled = false;
    laneMesh.renderOrder = 14;
    laneMesh.name = "upright-roll:pedal-lane";
    scene.add(laneMesh);
    added.push(laneMesh);
    let laneNext = 0, laneOpen = -1, laneDirty = false;

    // --------------------------------------------------------------- sparks --
    // Accents only: a small spray from the cap of a strike harder than velocity 0.7.
    const sparkUniforms = { ...shared, uPx: { value: 1000 } };
    const sparkGeo = new THREE.BufferGeometry();
    const sparkAttr = {};
    for (const [name, size] of [["position", 3], ["aVel", 3], ["aBirth", 1], ["aLife", 1], ["aSize", 1], ["aColor", 3]]) {
      const a = new THREE.BufferAttribute(new Float32Array(SPARK_MAX * size), size);
      a.setUsage(THREE.DynamicDrawUsage);
      sparkGeo.setAttribute(name, a);
      sparkAttr[name] = a;
    }
    sparkAttr.aBirth.array.fill(-FAR);
    const sparkMat = new THREE.ShaderMaterial({
      ...premultiplied, uniforms: sparkUniforms,
      vertexShader: `
        uniform float uNow, uPx;
        attribute vec3 aVel, aColor;
        attribute float aBirth, aLife, aSize;
        varying vec3 vColor;
        varying float vAlpha;
        void main() {
          float age = uNow - aBirth;
          if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
          float k = age / aLife;
          // drag: the spray decelerates, so it stays a short accent near the strike
          vec3 p = position + aVel * (1.0 - exp(-age * 3.0)) / 3.0;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = max(1.5, aSize * uPx * (1.0 - 0.7 * k) / max(-mv.z, 0.1));
          vAlpha = (1.0 - k) * (1.0 - k);
          vColor = aColor;
        }`,
      fragmentShader: `
        uniform float uFrameH, uPR, uFadeEnd, uFadeStart;
        varying vec3 vColor;
        varying float vAlpha;
        ${GLSL_COMMON}
        void main() {
          float r = length(gl_PointCoord - 0.5);
          float a = (1.0 - smoothstep(0.18, 0.5, r)) * vAlpha * bandFade(gl_FragCoord.y);
          if (a < 0.002) discard;
          gl_FragColor = vec4(vColor * a, a);
        }`,
    });
    const sparkPoints = new THREE.Points(sparkGeo, sparkMat);
    sparkPoints.frustumCulled = false;
    sparkPoints.renderOrder = 13;
    sparkPoints.name = "upright-roll:sparks";
    scene.add(sparkPoints);
    added.push(sparkPoints);
    let sparkNext = 0, sparksDirty = false;
    // A tiny deterministic generator: a replayed passage makes the same spray.
    let seed = 0x2f6b1d;
    const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
    function burst(m, vel, t) {
      const v = vel / 127;
      if (v <= SPARK_MIN_VEL) return;
      const count = Math.round(6 + 14 * (v - SPARK_MIN_VEL) / (1 - SPARK_MIN_VEL));
      noteColor(m, vel, tmpColor);
      const c = relight(tmpColor, 0.97, 0.45);
      const x = keyX(m);
      const capH = CAP_BASE + CAP_VEL * v;
      for (let i = 0; i < count; i++) {
        const j = sparkNext;
        sparkNext = (sparkNext + 1) % SPARK_MAX;
        sparkAttr.position.array.set([x + (rand() - 0.5) * 0.5, RAIL_Y + capH, TRAIL_Z + 0.2], j * 3);
        sparkAttr.aVel.array.set([(rand() - 0.5) * 3.2, 2.5 + rand() * 5.5 * v, (rand() - 0.2) * 1.2], j * 3);
        sparkAttr.aBirth.array[j] = t;
        sparkAttr.aLife.array[j] = 0.35 + rand() * 0.45;
        sparkAttr.aSize.array[j] = 0.07 + rand() * 0.09;
        sparkAttr.aColor.array.set(c, j * 3);
      }
      sparksDirty = true;
    }

    // ------------------------------------------------------------- per frame --
    const ray = new THREE.Vector3();
    // World y on the trail plane under a screen point (NDC), or null when the ray misses the plane.
    function planeAt(ndcX, ndcY) {
      ray.set(ndcX, ndcY, 0.5).unproject(camera).sub(camera.position);
      if (Math.abs(ray.z) < 1e-6) return null;
      const k = (TRAIL_Z - camera.position.z) / ray.z;
      if (k <= 0) return null;
      return { x: camera.position.x + ray.x * k, y: camera.position.y + ray.y * k };
    }
    let band = BAND["9:16"];
    let framingNow = { id: "9:16", width: 1080, height: 1920 };
    function applyFraming(f) {
      if (!f) return;
      framingNow = f;
      band = BAND[f.id] || (f.height > f.width ? BAND["9:16"] : BAND["16:9"]);
      shared.uFadeEnd.value = band.fadeEnd;
      shared.uFadeStart.value = band.fadeStart;
      shared.uFrameH.value = f.height;
    }
    applyFraming(ctx.framing);

    // ------------------------------------------------------------- instance --
    const strikes = new Map();  // midi -> bar ref of the strike that is sounding
    let active = false;
    for (const obj of added) obj.visible = false;
    let lastT = 0;

    function liveBars(t) {
      const out = { white: 0, black: 0, held: 0, tails: 0 };
      const top = shared.uTopW.value;
      for (const pool of Object.values(pools)) {
        const A = pool.attr;
        for (let j = 0; j < pool.max; j++) {
          if (A.aT0.array[j] < -1e5) continue;
          const t2 = A.aT2.array[j];
          if (RAIL_Y + (t - Math.min(t, t2)) * SPEED > top) continue;
          out[pool.kind]++;
          if (A.aT1.array[j] > t) out.held++;
          else if (A.aT2.array[j] > A.aT1.array[j] + 1e-6) out.tails++;
        }
      }
      return out;
    }

    return {
      noteOn(m, vel, t) {
        if (strikes.has(m)) barEnd(strikes.get(m), t);   // defensive: the core already ends a repeat first
        strikes.set(m, barStart(m, vel, t));
        burst(m, vel, t);
      },
      noteRelease(m, t) {
        barRelease(strikes.get(m), t);
      },
      noteEnd(m, t) {
        barEnd(strikes.get(m), t);
        strikes.delete(m);
      },
      pedal(down, value, t) {
        if (down) {
          if (laneOpen >= 0) return;
          laneOpen = laneNext;
          laneNext = (laneNext + 1) % LANE_MAX;
          laneAttr.aT0.array[laneOpen] = t;
          laneAttr.aT2.array[laneOpen] = FAR;
        } else {
          if (laneOpen < 0) return;
          laneAttr.aT2.array[laneOpen] = t;
          laneOpen = -1;
        }
        laneDirty = true;
      },
      update(dt, t, frame) {
        lastT = t;
        shared.uNow.value = t;
        if (frame && frame.framing && frame.framing !== framingNow &&
            (frame.framing.id !== framingNow.id || frame.framing.height !== framingNow.height)) applyFraming(frame.framing);
        shared.uPR.value = renderer.getPixelRatio();
        // Where the band's fade line and the left edge land on the trail plane, from this frame's camera.
        camera.updateMatrixWorld();
        const h = framingNow.height, w = framingNow.width;
        const ndcFadeEnd = 1 - 2 * band.fadeEnd / h;
        let topW = -Infinity;
        for (const nx of [-1, 0, 1]) { const p = planeAt(nx, ndcFadeEnd); if (p) topW = Math.max(topW, p.y); }
        shared.uTopW.value = Number.isFinite(topW) ? topW + 0.5 : (frame && frame.view ? frame.view.top : 30);
        const laneCenterPx = LANE.insetPx + LANE.widthPx / 2;
        const ndcLaneX = -1 + 2 * laneCenterPx / w;
        const rail = planeAt(ndcLaneX, 0);
        if (rail) laneUniforms.uLaneX.value = rail.x;
        laneUniforms.uNdcX0.value = -1 + 2 * LANE.insetPx / w;
        laneUniforms.uNdcX1.value = -1 + 2 * (LANE.insetPx + LANE.widthPx) / w;
        sparkUniforms.uPx.value = h / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
        for (const pool of Object.values(pools)) {
          if (pool.dirty) { for (const a of Object.values(pool.attr)) a.needsUpdate = true; pool.dirty = false; }
        }
        if (laneDirty) { for (const a of Object.values(laneAttr)) a.needsUpdate = true; laneDirty = false; }
        if (sparksDirty) { for (const a of Object.values(sparkAttr)) a.needsUpdate = true; sparksDirty = false; }
      },
      resize(framing) {
        applyFraming(framing);
      },
      setActive(on) {
        active = !!on;
        for (const obj of added) obj.visible = active;
      },
      dispose() {
        for (const obj of added) {
          scene.remove(obj);
          obj.geometry.dispose();
          obj.material.dispose();
        }
        added.length = 0;
        strikes.clear();
      },
      stats(t = lastT) {
        let sparks = 0;
        for (let j = 0; j < SPARK_MAX; j++) { const age = t - sparkAttr.aBirth.array[j]; if (age >= 0 && age <= sparkAttr.aLife.array[j]) sparks++; }
        let lane = 0;
        for (let j = 0; j < LANE_MAX; j++) {
          const t0 = laneAttr.aT0.array[j], t2 = laneAttr.aT2.array[j];
          if (t0 > -1e5 && RAIL_Y + (t - Math.min(t, t2)) * SPEED <= shared.uTopW.value) lane++;
        }
        const bars = liveBars(t);
        return { trailsLive: bars.white + bars.black, trailCap: POOL.white + POOL.black, bars, laneSegments: lane,
                 pedalOpen: laneOpen >= 0, sparksLive: sparks, topW: +shared.uTopW.value.toFixed(3), active };
      },
      // For the harness and the receipt: measurement switches and the facts behind the pictures.
      debug: {
        constants: { SPEED, BLOOM_THRESHOLD, BODY_LUMA_MAX, BAND, LANE, TAIL_A0, TAIL_TAU, TAIL_FLOOR, SPARK_MIN_VEL },
        objects: () => [...added],
        setCaps(on) { shared.uNoCap.value = on ? 0 : 1; },
        setSparks(on) { sparkPoints.visible = active && !!on; },
        // every bar that has a pedal tail and whose sound has ended: [{m, x, black, t0, t1, t2}]
        endedTails(t = lastT) {
          const out = [];
          for (const pool of Object.values(pools)) {
            const A = pool.attr;
            for (let j = 0; j < pool.max; j++) {
              const t1 = A.aT1.array[j], t2 = A.aT2.array[j];
              if (A.aT0.array[j] < -1e5 || t2 > t || !(t2 > t1 + 1e-6)) continue;
              out.push({ x: A.aX.array[j], black: pool.kind === "black", t0: A.aT0.array[j], t1, t2 });
            }
          }
          return out;
        },
      },
    };
  },
};
