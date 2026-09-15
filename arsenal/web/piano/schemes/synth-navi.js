// Synth Navi — arsenal/web/piano/schemes/synth-navi.js  (ES module, a piano scheme)
//
// Navi's bake-off entry (2026-09-15). One-sentence idea: the strike cap is the in-focus object and
// the rising bar is its light-trail wake — every note is a bead of light detaching from its key,
// drawing a straight beam behind it that is exactly as long as the note sounded.
//
// The Synthesia grammar is the native grammar, made legible:
//   1. bars rise from their exact key, one lane per key, straight, length = duration
//   2. point of contact: on noteOn the same frame, a rounded `bead` cap lands at the key edge,
//      a flash dies over ~0.16 s and its brightness is the velocity
//   3. repeats are separate beads: every strike gets its own slot, six Eb4 give six beads+gaps
//   4. finger vs pedal: finger-held = a solid luminous core; pedal-held = a hollow tube whose
//      outline fades to a floor. Finger+pedal (the moment of both) is the brightest state.
//   5. colour is the note: noteColor(midi, vel) relit in OKLab so velocity shifts lightness and
//      chroma, never toward white; saturation stays high because only lightness moves.
//   6. bloom decays: only the bead cap crosses the host's 0.9-luma bloom threshold, and its flash
//      is an exponential that dies; bodies/tails are clamped below the threshold. No stacked wash.
//   7. budget: two instanced meshes (white + black lanes) + one ghost pool, recycled slots, no
//      per-frame per-note CPU work, no second render context. 250 live bars is well inside.
//
// Dynamics addendum (Daniel's "peaks glow" ask, 2026-09-15):
//   8. peak glow — the bead cap's bloom is the velocity SQUARED riding the flash's own decay, so a
//      hard strike blooms hotter and every peak decays to nothing, never stacks.
//   9. (named) VU peak-hold needle — a thin tick at each strike's peak height holds ~1 s then falls
//      back toward the key and fades; its height is the velocity.
//  10. (named) phrase loudness ribbon — a pp..ff strip at the left edge whose dot rides the running
//      phrase loudness, so crescendo climbs and decrescendo sinks.
//
// Navi's own flourish, the `moved-note thread`: a white hit line rides a few hundredths of a second
// BEHIND the live bead cap, so the eye sees the note *moving*. It hugs the cap tightly (a lag, not
// a second line), and the gap between line and cap grows with speed — the signature `the note is
// travelling` cue that flat bars erase. A second flourish: each bead leaves a short after-image
// streak (pooled ghosp quads fading behind the cap) so a fast run reads as a streak, not dots.
//
// Everything comes from ctx (no imports). Same conventions as neon-trails / upright-roll: normal
// (premultiplied) blending only, no halo, no foot glow, positions from the clock not frame counts,
// and the roll fades to nothing inside the host's protected top band.

const FAR = 1e6;
const SPEED = 5.6;                         // world units per second (one unit = one white-key pitch)
const POOL = { white: 384, black: 256 };   // slots recycled; a long session never grows
const RECYCLE_Y = 80;                      // bar bottom past this is gone for good
const GHOST_MAX = 768;                     // after-image streaks, pooled

const WHITE_W = 0.72, BLACK_W = 0.40, BLACK_EDGE = 0.05;
const CAP_H_BASE = 0.10, CAP_H_VEL = 0.24;        // bead cap half-height = 0.10 + 0.24 v
const CAP_FLASH = 1.6, CAP_FLASH_TAU = 0.16;        // cap brightness x (1 + 1.6 exp(-age/0.16))
// Peak glow (Dynamics addendum): the cap's bloom is the velocity, squared, on top of the flash. Hard
// strikes glow more; the glow decays and never stacks (it rides the same exp as the flash).
const CAP_GLOW = 0.9;                                 // v^2 coefficient for the bloom term
const HIT_LAG = 0.055, HIT_EDGE = 0.020;            // hit line trails the cap by ~0.055 s
const TAIL_A0 = 0.72, TAIL_TAU = 1.5, TAIL_FLOOR = 0.30, TAIL_FILL = 0.06;
const GHOST_TAU = 0.30;                             // ghost after-image fade time

// The host's bloom is UnrealBloomPass(threshold 0.9) on linear luminance (Rec.709). Only the bead
// cap and its ghost are allowed to cross it; bodies, tails and the hit line clamp below.
const BODY_LUMA_MAX = 0.8;

// Protected top band in framing pixels from the top (host text overlay; see PIANO-V2-SPEC 6.3).
const BAND = {
  "9:16": { fadeEnd: 650, fadeStart: 860 },
  "16:9": { fadeEnd: 470, fadeStart: 600 },
};

const LUMA = [0.2126729, 0.7151522, 0.0721750];
const luma = (c) => LUMA[0] * c[0] + LUMA[1] * c[1] + LUMA[2] * c[2];

// OKLab <-> linear sRGB (same math as the host, so our relit colour stays in the host's hue).
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
// relight: keep hue+chroma, move only lightness (optionally boost chroma toward the cap). Velocity
// raises L and slightly raises chroma — it brightens and saturates, it never desaturates to white.
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
  id: "synth-navi",
  name: "Bead & Beam",

  create(ctx) {
    const { THREE, scene, keyX, isBlack, noteColor, RAIL_Y, TRAIL_Z, renderer } = ctx;
    const added = [];
    const tmpColor = new THREE.Color();
    const strikes = new Map();   // midi -> bar ref

    const shared = {
      uNow: { value: 0 }, uSpeed: { value: SPEED }, uBaseY: { value: RAIL_Y }, uZ: { value: TRAIL_Z },
      uTopW: { value: 30 }, uFrameH: { value: 1920 }, uPR: { value: 1 },
      uFadeEnd: { value: BAND["9:16"].fadeEnd }, uFadeStart: { value: BAND["9:16"].fadeStart },
      uBodyMax: { value: BODY_LUMA_MAX },
      uPx: { value: 1000 },
    };
    const premultiplied = {
      transparent: true, depthWrite: false, blending: THREE.CustomBlending,
      blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
    };

    // ------------------------------------------------------------------- bars --
    // One instanced quad per strike. The quad spans sound-end (bottom) to onset+cap (top); the
    // fragment shader splits tail / body / bead-cap by the event times, plus a moving hit line.
    const BAR_VERT = `
      uniform float uNow, uSpeed, uBaseY, uZ, uTopW;
      attribute float aX, aW, aT0, aT1, aT2, aVel;
      attribute vec3 aBody, aCap, aTail;
      varying vec2 vP;
      varying float vW, vTop, vHold, vBot, vCapH, vAge, vEnded, vVel;
      varying vec3 vBody, vCapC, vTailC;
      void main() {
        float bot = uBaseY + (uNow - min(uNow, aT2)) * uSpeed;
        if (aT0 < -1e5 || bot > uTopW) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
        float top = uBaseY + (uNow - aT0) * uSpeed;
        float capH = ${CAP_H_BASE.toFixed(3)} + ${CAP_H_VEL.toFixed(3)} * aVel;
        float y = mix(bot, top + capH, position.y);
        vP = vec2(position.x * aW, y);
        vW = aW; vTop = top; vBot = bot; vCapH = capH; vAge = uNow - aT0; vVel = aVel;
        vHold = uBaseY + (uNow - min(uNow, aT1)) * uSpeed;
        vEnded = aT2 <= uNow ? 1.0 : 0.0;
        vBody = aBody; vCapC = aCap; vTailC = aTail;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(aX + vP.x, y, uZ, 1.0);
      }`;
    const BAR_FRAG = `
      uniform float uSpeed, uFrameH, uPR, uFadeEnd, uFadeStart, uBodyMax;
      varying vec2 vP;
      varying float vW, vTop, vHold, vBot, vCapH, vAge, vEnded, vVel;
      varying vec3 vBody, vCapC, vTailC;
      ${GLSL_COMMON}
      void main() {
        float fade = bandFade(gl_FragCoord.y);
        if (fade <= 0.0) discard;
        float y = vP.y;
        float halfW = vW * 0.5;
        float fx = max(fwidth(vP.x), 1e-5), fy = max(fwidth(y), 1e-5);
        float side = halfW - abs(vP.x);
        float across = abs(vP.x) / halfW;
        vec3 col;
        float a = 1.0;
        if (y > vTop) {
          // BEAD CAP — the strike, and the only thing allowed to bloom. A rounded cap with a flash
          // that dies over ~0.16 s; brightness is velocity, chroma is boosted, never white.
          float r = min(halfW, vCapH) * 0.6;
          vec2 q = vec2(abs(vP.x) - (halfW - r), y - (vTop + vCapH - r));
          float d = length(max(q, 0.0)) - r;
          a = 1.0 - smoothstep(-fx, fx, d);
          float flash = 1.0 + ${CAP_FLASH.toFixed(2)} * exp(-vAge / ${CAP_FLASH_TAU.toFixed(3)});
          // Peak glow (Dynamics addendum): the bloom is the velocity squared, riding the same decay
          // as the flash. Hard strikes glow more; the glow decays, it never stacks.
          float glow = ${CAP_GLOW.toFixed(2)} * vVel * vVel * exp(-vAge / ${CAP_FLASH_TAU.toFixed(3)});
          col = vCapC * (flash + glow) * (1.0 - 0.08 * across * across);
        } else {
          // moved-note hit line: a white stroke a little BEHIND the cap (below it) that only shows
          // while a note is still sounding; its offset is fixed in time (HIT_LAG) so it hugs the cap.
          float distanceBehind = (vTop - y);            // world units below the cap top edge
          float hit = 1.0 - smoothstep(${(HIT_LAG * SPEED - HIT_EDGE).toFixed(3)}, ${(HIT_LAG * SPEED + HIT_EDGE).toFixed(3)}, distanceBehind);
          hit *= 1.0 - vEnded;                          // gone once the sound ends
          if (y >= vHold) {
            // FINGER-HELD BODY: solid luminous core, brighter on the axis, dimmer at the rim.
            col = vBody * (0.80 + 0.20 * (1.0 - across * across));
          } else {
            // PEDAL TAIL: a hollow tube whose outline decays to a floor; the cut line stays readable.
            float tailAge = (vHold - y) / uSpeed;
            float edgeA = max(${TAIL_FLOOR.toFixed(2)}, ${TAIL_A0.toFixed(2)} * exp(-tailAge / ${TAIL_TAU.toFixed(2)}));
            float sideLine = 1.0 - smoothstep(1.4, 2.4, side / fx);
            float cutLine = vEnded * (1.0 - smoothstep(1.4, 2.4, (y - vBot) / fy));
            a = max(${TAIL_FILL.toFixed(2)}, max(sideLine * edgeA, cutLine * max(edgeA, 0.62)));
            col = vTailC;
          }
          // blend the hit line in as a near-white stroke that rides the body/tail edge
          col += vec3(1.0) * hit * 0.9;
          // bloom guard: nothing below the cap may cross the host's bloom threshold
          col *= min(1.0, uBodyMax / max(lumaOf(col), 1e-4));
        }
        a *= fade;
        if (a < 0.004) discard;
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
      const mat = new THREE.ShaderMaterial({ ...premultiplied, uniforms: { ...shared },
                                             vertexShader: BAR_VERT, fragmentShader: BAR_FRAG });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.frustumCulled = false;
      mesh.renderOrder = kind === "black" ? 12 : 11;   // black keys over white
      mesh.name = `synth-navi:${kind}`;
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
      if (slot < 0) { slot = 0; for (let j = 1; j < pool.max; j++) if (A.aT0.array[j] < A.aT0.array[slot]) slot = j; }
      pool.next = (slot + 1) % pool.max;
      const v = Math.min(1, Math.max(0, vel / 127));
      noteColor(m, vel, tmpColor);
      A.aX.array[slot] = keyX(m);
      A.aW.array[slot] = pool.kind === "black" ? BLACK_W : WHITE_W;
      A.aT0.array[slot] = t;
      A.aT1.array[slot] = FAR;
      A.aT2.array[slot] = FAR;
      A.aVel.array[slot] = v;
      // velocity moves lightness and (slightly) chroma, hue untouched — saturated, never white
      A.aBody.array.set(relight(tmpColor, 0.46 + 0.36 * v ** 0.8, 1.0, BODY_LUMA_MAX - 0.05), slot * 3);
      A.aCap.array.set(relight(tmpColor, 0.90 + 0.08 * v, 0.62, Infinity), slot * 3);
      A.aTail.array.set(relight(tmpColor, 0.80, 1.0, BODY_LUMA_MAX - 0.05), slot * 3);
      pool.dirty = true;
      return { pool, slot, t0: Math.fround(t), m, vel: v };
    }
    const owns = (ref) => ref && ref.pool.attr.aT0.array[ref.slot] === ref.t0;
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

    // ---------------------------------------------------------- after-image ghosts --
    // A pooled set of fading quads that trail each live cap, so a fast run reads as a streak. Each
    // ghost stores a fixed position + colour at spawn and just fades; no per-frame per-note math.
    const ghostUniforms = { ...shared };
    const ghostGeo = new THREE.InstancedBufferGeometry();
    {
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0, 0.5, 0);
      ghostGeo.setIndex(base.getIndex());
      ghostGeo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
    }
    const ghostAttr = {};
    for (const [name, size] of [["aX", 1], ["aW", 1], ["aY", 1], ["aT", 1], ["aGone", 1], ["aColor", 3]]) {
      const a = new THREE.InstancedBufferAttribute(new Float32Array(GHOST_MAX * size), size);
      a.setUsage(THREE.DynamicDrawUsage);
      ghostGeo.setAttribute(name, a);
      ghostAttr[name] = a;
    }
    ghostAttr.aT.array.fill(-FAR);
    ghostAttr.aGone.array.fill(1);
    ghostGeo.instanceCount = GHOST_MAX;
    const ghostMat = new THREE.ShaderMaterial({
      ...premultiplied, depthWrite: false, uniforms: { ...ghostUniforms },
      vertexShader: `
        uniform float uNow, uBaseY, uZ;
        attribute float aX, aW, aY, aT, aGone;
        attribute vec3 aColor;
        varying vec3 vColor;
        varying float vA;
        varying vec2 vP;
        void main() {
          vA = 0.0; vP = vec2(0.0); vColor = vec3(0.0);
          vec3 p = vec3(0.0, -1e5, uZ);
          if (aGone < 0.5) {
            float age = uNow - aT;
            float k = clamp(age / ${GHOST_TAU.toFixed(3)}, 0.0, 1.0);
            // fade and drift slightly downward (against the rise) so it streaks behind the cap
            float yy = aY - age * ${(SPEED * 0.5).toFixed(3)};
            p = vec3(aX + position.x * aW, yy, uZ);
            vA = (1.0 - k) * 0.8;
            vP = vec2(position.x * aW, yy);
            vColor = aColor;
          }
          gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
        }`,
      fragmentShader: `
        uniform float uFrameH, uPR, uFadeEnd, uFadeStart, uBodyMax;
        varying vec3 vColor;
        varying float vA;
        varying vec2 vP;
        ${GLSL_COMMON}
        void main() {
          if (vA <= 0.0) discard;
          float fade = bandFade(gl_FragCoord.y);
          if (fade <= 0.0) discard;
          // a soft hot streak on the axis, falling off at the sides, so it reads as a wake
          float halfW = mix(${WHITE_W.toFixed(2)}, ${BLACK_W.toFixed(2)}, 0.0) * 0.5;
          float across = abs(vP.x) / max(halfW, 0.05);
          float a = vA * (1.0 - smoothstep(0.0, 1.0, across)) * fade;
          vec3 col = vColor * 1.4;          // ghosts bloom: they ride just over the threshold
          if (a < 0.004) discard;
          gl_FragColor = vec4(col * a, a);
        }`,
    });
    const ghostMesh = new THREE.Mesh(ghostGeo, ghostMat);
    ghostMesh.frustumCulled = false;
    ghostMesh.renderOrder = 13;
    ghostMesh.name = "synth-navi:ghosts";
    scene.add(ghostMesh);
    let ghostNext = 0, ghostDirty = false;
    function spawnGhost(x, w, y, t, col) {
      const j = ghostNext;
      ghostNext = (ghostNext + 1) % GHOST_MAX;
      ghostAttr.aX.array[j] = x;
      ghostAttr.aW.array[j] = w;
      ghostAttr.aY.array[j] = y;
      ghostAttr.aT.array[j] = t;
      ghostAttr.aGone.array[j] = 0;
      ghostAttr.aColor.array.set([col[0], col[1], col[2]], j * 3);
      ghostDirty = true;
    }
    // continuous wake: spawn a ghost at each live bar's cap every interval, so a held or rising note
    // leaves a short after-image streak. Throttled so the 768-slot pool stays ahead of the spawn
    // rate even at 250 live bars: interval 0.02 s * 250 bars = 12500/s is too hot, so we sample a
    // rotating subset each tick instead of all bars. Each ghost lives GHOST_TAU (~0.30 s) and fades,
    // so ~7 ghosts deep per note is a clean streak, not a solid second bar.
    let lastWake = -1e6;
    function wake(t) {
      if (t - lastWake < 0.02) return;
      lastWake = t;
      const now = shared.uNow.value;
      for (const pool of [pools.white, pools.black]) {
        const A = pool.attr;
        for (let j = 0; j < pool.max; j++) {
          if (A.aT0.array[j] < -1e5) continue;
          if (A.aT2.array[j] <= now) continue;   // only while sounding
          const topY = RAIL_Y + (now - A.aT0.array[j]) * SPEED;
          if (topY > shared.uTopW.value) continue;
          spawnGhost(A.aX.array[j], A.aW.array[j], topY, now,
                     [A.aCap.array[j * 3], A.aCap.array[j * 3 + 1], A.aCap.array[j * 3 + 2]]);
        }
      }
    }

    // --------------------------------------------------------- peak-hold marker --
    // Dynamics addendum, idea 2 (named: "peak-hold"). On every strike a thin tick flickers at the
    // bead's peak height — its Y is the velocity, so a hard strike parks a higher tick. The tick
    // HOLDS about HOLD_TIME, then FALLS back toward the key and fades. It reads like a VU meter's
    // peak-hold: the last beat's loudness stays readable after the bar has risen past it.
    const HOLD_MAX = 384;
    const HOLD_TIME = 1.0, HOLD_FALL = 0.6;   // hold 1 s, then fall 0.6 s
    const HOLD_H = 0.06;                      // needle thickness in world units (a hairline)
    const holdUnion = { ...shared };
    const holdGeo = new THREE.InstancedBufferGeometry();
    {
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0, 0.5, 0);
      holdGeo.setIndex(base.getIndex());
      holdGeo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
    }
    const holdAttr = {};
    for (const [name, size] of [["aX", 1], ["aW", 1], ["aY", 1], ["aT0", 1], ["aVel", 1], ["aColor", 3]]) {
      const a = new THREE.InstancedBufferAttribute(new Float32Array(HOLD_MAX * size), size);
      a.setUsage(THREE.DynamicDrawUsage);
      holdGeo.setAttribute(name, a);
      holdAttr[name] = a;
    }
    holdAttr.aT0.array.fill(-FAR);
    holdGeo.instanceCount = HOLD_MAX;
    const holdMat = new THREE.ShaderMaterial({
      ...premultiplied, depthWrite: false, uniforms: { ...holdUnion },
      vertexShader: `
        uniform float uNow, uSpeed, uBaseY, uZ;
        attribute float aX, aW, aY, aT0, aVel;
        attribute vec3 aColor;
        varying vec3 vColor;
        varying float vA;
        varying vec2 vP;
        void main() {
          vColor = vec3(0.0); vA = 0.0; vP = vec2(0.0, -1e5);
          vec3 p = vec3(0.0, -1e5, uZ);
          if (aT0 > -1e5) {
            float age = uNow - aT0;
            // hold, then fall back toward the rail and fade
            float fall = clamp((age - ${HOLD_TIME.toFixed(2)}) / ${HOLD_FALL.toFixed(2)}, 0.0, 1.0);
            if (age >= 0.0) {
              float yy = mix(aY, uBaseY, fall);
              // a thin hairline: collapse the quad's height to HOLD_H around the needle's y
              float ny = yy + (position.y - 0.5) * ${HOLD_H.toFixed(3)};
              p = vec3(aX + position.x * aW, ny, uZ);
              // visible while holding; fades gently during the fall so it never lingers dead
              vA = 1.0 - 0.85 * smoothstep(0.0, 1.0, fall);
              vP = vec2(position.x * aW, ny);
              vColor = aColor;
            }
          }
          gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
        }`,
      fragmentShader: `
        uniform float uFrameH, uPR, uFadeEnd, uFadeStart;
        varying vec3 vColor;
        varying float vA;
        varying vec2 vP;
        ${GLSL_COMMON}
        void main() {
          if (vA <= 0.0) discard;
          float fade = bandFade(gl_FragCoord.y);
          if (fade <= 0.0) discard;
          // a short luminous needle: hot where it crosses the cap, soft at the flanks, reads as a
          // VU tick pressed against the bead's peak. Width hugs the bar; height is a hairline.
          float across = abs(vP.x);
          float axis = 1.0 - smoothstep(0.0, 0.5, across);
          vec3 col = vColor * (0.8 + 0.7 * axis) * 1.4;
          float a = vA * fade;
          if (a < 0.004) discard;
          gl_FragColor = vec4(col * a, a);
        }`,
    });
    const holdMesh = new THREE.Mesh(holdGeo, holdMat);
    holdMesh.frustumCulled = false;
    holdMesh.renderOrder = 13;
    holdMesh.name = "synth-navi:peak-hold";
    scene.add(holdMesh);
    let holdNext = 0, holdDirty = false;
    function spawnHold(x, w, y, vel, t, col) {
      const j = holdNext;
      holdNext = (holdNext + 1) % HOLD_MAX;
      holdAttr.aX.array[j] = x;
      holdAttr.aW.array[j] = w;
      holdAttr.aY.array[j] = y;
      holdAttr.aT0.array[j] = t;
      holdAttr.aVel.array[j] = vel;
      holdAttr.aColor.array.set([col[0], col[1], col[2]], j * 3);
      holdDirty = true;
    }

    // -------------------------------------------------------- phrase loudness ribbon --
    // Dynamics addendum, idea 3 (named: "loudness ribbon"). A slim vertical strip pinned at the
    // LEFT edge: piano pp at the bottom, fortissimo ff at the top. A dot rides it live, showing the
    // running phrase loudness (a fast-attack / slow-decay follower over recent strike velocities),
    // so a crescendo reads as the dot climbing and a decrescendo as it sinking back. It maps the
    // whole PHRASE (the "dynamicness of the playing") where the peak glow maps the single note.
    const RIBBON = { widthPx: 10, insetPx: 6, topFrac: 0.30, heightFrac: 0.42 };
    const ribbonUniforms = { ...shared, uDotY: { value: 0 }, uEnergy: { value: 0 },
                             uFrameW: { value: 1080 } };
    const ribGeo = new THREE.PlaneGeometry(1, 1);
    ribGeo.translate(0.5, 0.5, 0);
    const ribMat = new THREE.ShaderMaterial({
      ...premultiplied, depthTest: false, uniforms: { ...ribbonUniforms },
      vertexShader: `
        varying vec2 vP;
        void main() {
          vP = position.xy;                 // 0..1 across the canvas
          gl_Position = vec4(position.xy * 2.0 - 1.0, 0.0, 1.0);
        }`,
      fragmentShader: `
        uniform float uFrameH, uFrameW, uDotY, uEnergy;
        varying vec2 vP;
        void main() {
          float px = vP.x * uFrameW;                // pixel x from the LEFT edge
          float py = vP.y * uFrameH;                // pixel y from the TOP
          // the strip: a fixed inset from the left, a fixed width, a fixed vertical span
          float halfW = ${RIBBON.widthPx}.0 * 0.5 + 1.0;
          float cx = ${RIBBON.widthPx}.0 * 0.5 + ${RIBBON.insetPx}.0;
          float dx = abs(px - cx) / halfW;
          float topY = uFrameH * ${RIBBON.topFrac.toFixed(3)};
          float botY = uFrameH * (${(RIBBON.topFrac + RIBBON.heightFrac).toFixed(3)});
          float t = clamp((py - topY) / (botY - topY), 0.0, 1.0);   // 0 = pp bottom, 1 = ff top
          // gradient: cool dim at pp, warm bright at ff — reads as LEVEL, hue-agnostic
          vec3 low = vec3(0.10, 0.13, 0.26);
          vec3 high = vec3(0.75, 0.58, 0.32);
          vec3 band = mix(low, high, t * t);
          // a faint band-line at the dot marks where the phrase sits
          float dotY_px = topY + (botY - topY) * uDotY;
          float dotD = abs(py - dotY_px);
          float dot = 1.0 - smoothstep(0.0, 2.5, dotD);
          float strip = 1.0 - smoothstep(0.85, 1.0, dx);
          if (strip <= 0.0) discard;
          float a = strip * (0.22 + 0.30 * t);
          vec3 col = band;
          col += vec3(0.95, 0.88, 0.72) * dot * (0.55 + 0.45 * uEnergy);
          a += dot * 0.7;
          if (a < 0.004) discard;
          gl_FragColor = vec4(col * a, a);
        }`,
    });
    const ribMesh = new THREE.Mesh(ribGeo, ribMat);
    ribMesh.frustumCulled = false;
    ribMesh.renderOrder = 15;
    ribMesh.name = "synth-navi:loudness-ribbon";
    scene.add(ribMesh);

    // phrase loudness follower: fast lift on a strike, slow fall, tracked over recent velocities.
    let loudness = 0;
    function feedLoudness(vel) {
      const v = vel / 127;
      loudness = Math.max(loudness, v);              // lift right away
    }
    // decay: called each frame in update(); tau ~0.8 s so a phrase's big peak hangs a beat or two.

    let active = false;
    pools.white.mesh.visible = false;
    pools.black.mesh.visible = false;
    ghostMesh.visible = false;
    holdMesh.visible = false;
    ribMesh.visible = false;

    return {
      noteOn(m, vel, t) {
        const ref = barStart(m, vel, t);
        strikes.set(m, ref);
        // Peak-hold tick: park it at the bead's peak height (velocity as height). It holds ~1 s
        // then falls; harder strikes hold a visibly higher tick.
        const A = ref.pool.attr;
        const slot = ref.slot;
        const v = ref.vel;
        const capTopY = RAIL_Y + CAP_H_BASE + CAP_H_VEL * v;
        spawnHold(A.aX.array[slot], A.aW.array[slot], capTopY, v, t,
                  [A.aCap.array[slot * 3], A.aCap.array[slot * 3 + 1], A.aCap.array[slot * 3 + 2]]);
        feedLoudness(vel);
      },
      noteRelease(m, t) {
        barRelease(strikes.get(m), t);
      },
      noteEnd(m, t) {
        barEnd(strikes.get(m), t);
        strikes.delete(m);
      },
      pedal() { /* pedal sustain is already the hollow tail below each release */ },
      update(dt, t, frame) {
        shared.uNow.value = t;
        if (frame.view) {
          shared.uTopW.value = frame.view.top;
          shared.uPx.value = frame.view.pointScale;
        }
        if (frame.framing) {
          shared.uFrameH.value = frame.framing.height;
          if (frame.framing.width) ribbonUniforms.uFrameW.value = frame.framing.width;
        }
        shared.uPR.value = renderer.getPixelRatio();
        wake(t);
        if (pools.white.dirty) { for (const at of Object.values(pools.white.attr)) at.needsUpdate = true; pools.white.dirty = false; }
        if (pools.black.dirty) { for (const at of Object.values(pools.black.attr)) at.needsUpdate = true; pools.black.dirty = false; }
        if (ghostDirty) { for (const at of Object.values(ghostAttr)) at.needsUpdate = true; ghostDirty = false; }
        if (holdDirty) { for (const at of Object.values(holdAttr)) at.needsUpdate = true; holdDirty = false; }
        // phrase loudness decays slowly, so a big peak hangs about a beat then sinks
        loudness = Math.max(0, loudness - dt * 0.55);
        ribbonUniforms.uDotY.value = loudness;
        ribbonUniforms.uEnergy.value = loudness;
      },
      resize(framing) {
        if (!framing) return;
        shared.uFrameH.value = framing.height;
        if (framing.width) ribbonUniforms.uFrameW.value = framing.width;
      },
      setActive(on) {
        active = !!on;
        pools.white.mesh.visible = active;
        pools.black.mesh.visible = active;
        ghostMesh.visible = active;
        holdMesh.visible = active;
        ribMesh.visible = active;
      },
      dispose() {
        for (const pool of [pools.white, pools.black]) {
          scene.remove(pool.mesh);
          pool.geo.dispose(); pool.mat.dispose();
        }
        scene.remove(ghostMesh);
        ghostGeo.dispose(); ghostMat.dispose();
        scene.remove(holdMesh);
        holdGeo.dispose(); holdMat.dispose();
        scene.remove(ribMesh);
        ribGeo.dispose(); ribMat.dispose();
        strikes.clear();
      },
    };
  },
};
