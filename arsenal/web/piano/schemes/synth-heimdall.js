// Synth Heimdall — arsenal/web/piano/schemes/synth-heimdall.js  (ES module, a piano scheme, a Synthesia bake-off entry)
//
// A dedicated Synthesia mode: straight bars rise from the exact key that played them, the bar's
// length is how long the note sounded, and the strike cap is the one part that blooms.
//
// Grammar kept (brief "What every entry must do"):
//  1. bars from keys, one lane per key, straight, length = duration, steady rise.
//  2. point of contact: an onset cap at the key edge in the same frame, scaled by velocity.
//  3. repeats are beads: every strike gets its own slot; six Eb4 in 2 s = six bars with gaps.
//  4. finger vs pedal: finger-held = solid core (brighter on axis); pedal-held = hollow tail that
//     decays to a floor; finger + pedal = the brightest state, by construction.
//  5. colour is the note (noteColor(midi, vel)), relit in OKLab so velocity moves lightness and
//     chroma only — hue untouched, never white.
//  6. bloom decays: only the cap and its fading echo cross the host's bloom threshold; bodies,
//     tails and the lane clamp below it (uBodyMax). Bloom hugs the source; its magnitude rides an
//     exponential so it fades, it never stacks.
//  7. budget: two instanced pools (white 384 + black 256), all positions from the clock, no
//     per-note allocation in update(), premultiplied blending, no second render context.
//
// Dynamics (Daniel's newest ask — peaks glow + more):
//  - velocity reading he recognises: the cap HEIGHT is the velocity (capH = CAP_BASE + CAP_VEL·v),
//    laid on top of Asta's translucent velocity columns. Read at a glance.
//  - peaks glow and decay: the cap is the one blooming part; its bloom is v^2 riding
//    exp(-age/GLOW_TAU). Hard strikes glow more and the glow dies out — the peak decays, it
//    never stacks into a white bar.
//  - named choice (beyond the brief's list): the GLOW ECHO — a fading, rising "needle ghost" that
//    lifts off the cap and climbs toward the top of the frame for ~0.8 s while it dims. I chose it
//    because Daniel already reads velocity as cap height; the echo keeps that same reading alive
//    AFTER the bar's cap has climbed out of view, so "how hard was that last strike" stays legible
//    through a run. It is a per-note VU needle, not a single global meter, and it is pure decay, so
//    it satisfies "peaks glow, harder glow more" without ever summing to a wash.
//
// This module owns only what it adds to the scene and draws nothing while inactive. Everything
// comes from ctx: no imports, so no import map is needed (neon-trails.js precedent).

const FAR = 1e6;
const SPEED = 6.0;                          // world units per second (one unit = one white-key pitch)
const POOL = { white: 384, black: 256 };    // slots per pool, recycled so a long session never grows
const RECYCLE_Y = 80;                       // a bar whose bottom has risen past this is gone for good
const ECHO_MAX = 512;                       // pooled rising ghosts (needle) — bounded, recycled

const WHITE_W = 0.72, BLACK_W = 0.40, BLACK_EDGE = 0.05;
const CAP_BASE = 0.10, CAP_VEL = 0.26;              // cap height = 0.10 + 0.26 v (world units)
const CAP_FLASH = 1.4, CAP_TAU = 0.16;              // cap brightness x (1 + 1.4 exp(-age / 0.16))
const GLOW_TAU = 0.34;                              // the bloom's decay time constant (seconds)
const TAIL_A0 = 0.68, TAIL_TAU = 1.5, TAIL_FLOOR = 0.28, TAIL_FILL = 0.06;
const ECHO_LIFE = 0.8, ECHO_RISE = 2.4;             // seconds; world units per second of climb
const ECHO_MIN_VEL = 0.12;                          // below this a strike is too gentle to echo

// The host renders bloom with UnrealBloomPass(threshold 0.9) on linear luminance (Rec.709 weights).
// Bodies, tails and the lane are clamped below BODY_LUMA_MAX, so only caps and echoes cross.
const BLOOM_THRESHOLD = 0.9;
const BODY_LUMA_MAX = 0.8;

// The protected top band (host overlay), in framing pixels from the top: the roll is fully
// transparent above fadeEnd and fully opaque below fadeStart (9:16 follows the spec band; 16:9
// clears the staff's bottom line at the host's LAYOUT).
const BAND = {
  "9:16": { fadeEnd: 650, fadeStart: 860 },
  "16:9": { fadeEnd: 470, fadeStart: 600 },
};

const VIEW_HINT = Object.freeze({ lensShift: Object.freeze({ "9:16": 0.20 }) });

const LUMA = [0.2126729, 0.7151522, 0.0721750];
const luma = (c) => LUMA[0] * c[0] + LUMA[1] * c[1] + LUMA[2] * c[2];

// OKLab <-> linear sRGB, so the scheme can re-light the host's note colour (any colour mode) while
// keeping its hue: body, cap, tail and echo differ in lightness and chroma, never in hue.
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
  // 1 below the band, 0 above it: screen-space, so the band holds whatever the camera does.
  float bandFade(float fragY) {
    float yTop = uFrameH - fragY / uPR;
    return smoothstep(uFadeEnd, uFadeStart, yTop);
  }`;

export default {
  id: "synth-heimdall",
  name: "Glow Echo",
  view: VIEW_HINT,

  create(ctx) {
    const { THREE, scene, camera, renderer, keyX, isBlack, noteColor, RAIL_Y, TRAIL_Z } = ctx;
    const added = [];
    const tmpColor = new THREE.Color();
    let lastT = 0;

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

    // ---------------------------------------------------------------- bars --
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
          // onset cap: the strike. Rounded top corners; a flash that dies in about a quarter second;
          // the bloom rides the SAME exponential (v^2 scaling) so it decays, never stacks.
          if (uNoCap > 0.5) discard;
          float r = min(halfW, vCapH) * 0.55;
          vec2 q = vec2(abs(vP.x) - (halfW - r), y - (vTop + vCapH - r));
          float d = length(max(q, 0.0)) - r;
          a = 1.0 - smoothstep(-fx, fx, d);
          col = vCapC * (1.0 + ${CAP_FLASH.toFixed(2)} * exp(-vAge / ${CAP_TAU.toFixed(3)})) * (1.0 - 0.08 * across * across);
          float seam = 1.0 - smoothstep(0.6, 1.6, (y - vTop) / fy);
          col *= 1.0 - 0.35 * seam * step(vHold, vTop - 0.001);
        } else if (y >= vHold) {
          col = vBody * (0.80 + 0.20 * (1.0 - across * across));
        } else {
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
      mesh.name = `synth-heimdall:${kind}`;
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

    // ------------------------------------------------------------ glow echo --
    // The named dynamics idea: a fading, rising "needle ghost" lifts off each cap and climbs toward
    // the top of the frame while it dims. Its brightness is v^2 at birth and it rides a pure
    // exponential decay, so hard strikes echo longer and brighter and the echo never stacks. It is
    // one instanced point cloud, all positions from the clock, zero per-frame allocation.
    const echoUniforms = { ...shared, uPx: { value: 1000 } };
    const echoGeo = new THREE.BufferGeometry();
    const echoAttr = {};
    for (const [name, size] of [["position", 3], ["aBirth", 1], ["aLife", 1], ["aVel", 1], ["aSeed", 1], ["aColor", 3]]) {
      const a = new THREE.BufferAttribute(new Float32Array(ECHO_MAX * size), size);
      a.setUsage(THREE.DynamicDrawUsage);
      echoGeo.setAttribute(name, a);
      echoAttr[name] = a;
    }
    echoAttr.aBirth.array.fill(-FAR);
    const echoMat = new THREE.ShaderMaterial({
      ...premultiplied, uniforms: echoUniforms,
      vertexShader: `
        uniform float uNow, uSpeed, uBaseY, uTopW, uPx;
        attribute float aBirth, aLife, aVel, aSeed;
        attribute vec3 aColor;
        varying vec3 vColor;
        varying float vAlpha;
        void main() {
          float age = uNow - aBirth;
          if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
          float k = age / aLife;
          // The ghost lifts off the cap and climbs (a slow-breathing sideways drift keeps the eye on
          // the motion, not a dead vertical line).
          float rise = ${ECHO_RISE.toFixed(2)} * age;
          float sway = sin(age * 2.2 + aSeed) * 0.14 * k;
          vec3 p = position + vec3(sway, rise, 0.0);
          p.y = min(p.y, uTopW - 0.2);                     // stays inside the picture
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = max(2.0, aVel * uPx * 0.12 * (1.0 - 0.55 * k) / max(-mv.z, 0.1));
          vAlpha = (1.0 - k) * (1.0 - k) * (0.35 + 0.65 * aVel);
          vColor = aColor;
        }`,
      fragmentShader: `
        uniform float uFrameH, uPR, uFadeEnd, uFadeStart, uBodyMax;
        varying vec3 vColor;
        varying float vAlpha;
        ${GLSL_COMMON}
        void main() {
          float r = length(gl_PointCoord - 0.5);
          float a = (1.0 - smoothstep(0.15, 0.5, r)) * vAlpha * bandFade(gl_FragCoord.y);
          // The echo is a bloom object: it deliberately crosses the threshold so a hard strike's
          // peak visibly glows as it climbs, then fades. Sparse points cannot stack into a wash.
          vec3 col = vColor * min(1.0, ${BLOOM_THRESHOLD.toFixed(2)} / max(lumaOf(vColor), 1e-4));
          if (a < 0.002) discard;
          gl_FragColor = vec4(col * a, a);
        }`,
    });
    const echoPoints = new THREE.Points(echoGeo, echoMat);
    echoPoints.frustumCulled = false;
    echoPoints.renderOrder = 13;
    echoPoints.name = "synth-heimdall:echo";
    scene.add(echoPoints);
    added.push(echoPoints);
    let echoNext = 0, echoDirty = false;
    // A tiny deterministic generator: a replayed passage makes the same ghost.
    let seed = 0x51eb09;
    const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
    function spawnEcho(m, vel, t) {
      const v = vel / 127;
      if (v <= ECHO_MIN_VEL) return;
      const j = echoNext;
      echoNext = (echoNext + 1) % ECHO_MAX;
      const x = keyX(m);
      const capH = CAP_BASE + CAP_VEL * v;
      noteColor(m, vel, tmpColor);
      // Slightly hotter, slightly desaturated versus the cap, so it reads as the glow of the strike
      // rather than a second cap.
      const c = relight(tmpColor, 0.94, 0.5);
      echoAttr.position.array.set([x + (rand() - 0.5) * 0.12, RAIL_Y + capH, TRAIL_Z + 0.15], j * 3);
      echoAttr.aBirth.array[j] = t;
      echoAttr.aLife.array[j] = ECHO_LIFE * (0.75 + 0.5 * v);
      echoAttr.aVel.array[j] = v;
      echoAttr.aSeed.array[j] = rand() * 6.283;
      echoAttr.aColor.array.set(c, j * 3);
      echoDirty = true;
    }

    // ------------------------------------------------------------- instance --
    const strikes = new Map();  // midi -> bar ref of the strike that is sounding
    let active = false;
    let lastApplied = null;

    function applyFraming(framing) {
      const id = framing && framing.id ? framing.id : "9:16";
      const band = BAND[id] || BAND["9:16"];
      shared.uFadeEnd.value = band.fadeEnd;
      shared.uFadeStart.value = band.fadeStart;
      shared.uFrameH.value = framing ? framing.height : 1920;
    }
    applyFraming(ctx.framing);

    function liveBars(t) {
      let white = 0, black = 0;
      const top = shared.uTopW.value;
      for (const pool of Object.values(pools)) {
        const A = pool.attr;
        for (let j = 0; j < pool.max; j++) {
          const t0 = A.aT0.array[j], t2 = A.aT2.array[j];
          if (t0 > -1e5 && RAIL_Y + (t - Math.min(t, t2)) * SPEED <= top) {
            if (pool.kind === "black") black++; else white++;
          }
        }
      }
      return { white, black };
    }

    return {
      id: "synth-heimdall",
      name: "Glow Echo",
      noteOn(m, vel, t) {
        strikes.set(m, barStart(m, vel, t));
        spawnEcho(m, vel, t);
      },
      noteRelease(m, t) {
        barRelease(strikes.get(m), t);
      },
      noteEnd(m, t) {
        barEnd(strikes.get(m), t);
        strikes.delete(m);
      },
      pedal() { /* pedal sustain is already the dim tail below each release */ },
      update(dt, t, frame) {
        lastT = t;
        shared.uNow.value = t;
        echoUniforms.uNow.value = t;
        const framingNow = frame && frame.framing ? frame.framing : ctx.framing;
        if (framingNow && (!lastApplied || framingNow.id !== lastApplied.id || framingNow.height !== lastApplied.height)) {
          applyFraming(framingNow);
          lastApplied = framingNow;
        }
        if (frame && frame.view) {
          if (typeof frame.view.top === "number") shared.uTopW.value = frame.view.top;
          if (typeof frame.view.pointScale === "number") echoUniforms.uPx.value = frame.view.pointScale;
        } else {
          shared.uTopW.value = 30;
        }
        shared.uPR.value = renderer.getPixelRatio();
        for (const pool of Object.values(pools)) {
          if (pool.dirty) { for (const a of Object.values(pool.attr)) a.needsUpdate = true; pool.dirty = false; }
        }
        if (echoDirty) { for (const a of Object.values(echoAttr)) a.needsUpdate = true; echoDirty = false; }
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
        const bars = liveBars(t);
        let echoes = 0;
        for (let j = 0; j < ECHO_MAX; j++) { const age = t - echoAttr.aBirth.array[j]; if (age >= 0 && age <= echoAttr.aLife.array[j]) echoes++; }
        return { trailsLive: bars.white + bars.black, trailCap: POOL.white + POOL.black, bars, echoesLive: echoes, echoCap: ECHO_MAX, active };
      },
      // For the harness and the receipt: measurement switches and the facts behind the pictures.
      debug: {
        constants: { SPEED, BLOOM_THRESHOLD, BODY_LUMA_MAX, BAND, TAIL_A0, TAIL_TAU, TAIL_FLOOR, ECHO_LIFE, ECHO_RISE, ECHO_MIN_VEL, CAP_BASE, CAP_VEL, GLOW_TAU },
        objects: () => [...added],
        setEchoes(on) { echoPoints.visible = active && !!on; },
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
