// Neon Trails — arsenal/web/piano/schemes/neon-trails.js  (ES module, a piano scheme)
// Today's look, extracted from piano.js behind the scheme interface (PIANO-V2-SPEC.md section 1):
// one instanced mesh of glowing trails rising from the back rail, and a spark burst per strike.
//
// The core owns keys, camera, stage and overlay. This module owns only what it adds to the scene,
// and it draws nothing while inactive. Everything comes from ctx: no imports, so the module needs
// no import map and is cheap to load with import().
//
// Changes from piano.js, all from the sustain rules (PIANO-V2-SPEC.md section 2):
// - trail energy is multiplied by a per-frame uniform, 1 / sqrt(1 + sounding / 10), so a dense
//   pedalled passage cannot add up to a white wall
// - trails end. piano.js compared a Float32 start time with the full-precision one, so release and
//   end were silently skipped and every trail stayed a column on the rail forever; here a released
//   note's bar lifts off the rail and rises away when its sound ends
// - the pedal tail below the release point starts at the held bar's energy (no step) and decays to
//   a floor, so a pedalled note still reads as a column standing on the rail until the pedal lifts

const FAR = 1e6;
const TRAIL_MAX = 640;          // the cap: slots are recycled, so a long session never grows
const TRAIL_SPEED = 6.5;        // world units per second
const SPARK_MAX = 2400;
const TAIL_FLOOR = 0.3;         // pedal tail energy it decays to (x velocity), relative to the held bar
const TAIL_TAU = 0.85;          // seconds of sustain over which the tail falls from 1 toward the floor

const damp = (current, target, tau, dt) => current + (target - current) * (1 - Math.exp(-dt / Math.max(tau, 1e-4)));

export default {
  id: "neon-trails",
  name: "Neon Trails",

  create(ctx) {
    const { THREE, scene, keyX, isBlack, noteColor, RAIL_Y, TRAIL_Z } = ctx;

    // --------------------------------------------------------------- trails --
    // One instanced draw for every trail. Each instance stores its note's start, release and
    // sound-end times; the vertex shader places the bar from the clock, so a trail costs nothing
    // per frame on the CPU. The bright part is the held duration; the dim tail is pedal sustain.
    const trailUniforms = { uNow: { value: 0 }, uSpeed: { value: TRAIL_SPEED }, uBaseY: { value: RAIL_Y },
                            uZ: { value: TRAIL_Z }, uTop: { value: 30 }, uEnergy: { value: 1 } };
    const trailGeo = new THREE.InstancedBufferGeometry();
    {
      const base = new THREE.PlaneGeometry(1, 1);
      base.translate(0, 0.5, 0);
      trailGeo.setIndex(base.getIndex());
      trailGeo.setAttribute("position", base.getAttribute("position"));
      base.dispose();
    }
    const trailAttr = {};
    for (const [name, size] of [["aX", 1], ["aW", 1], ["aT0", 1], ["aT1", 1], ["aT2", 1], ["aVel", 1], ["aColor", 3]]) {
      const attr = new THREE.InstancedBufferAttribute(new Float32Array(TRAIL_MAX * size), size);
      attr.setUsage(THREE.DynamicDrawUsage);
      trailGeo.setAttribute(name, attr);
      trailAttr[name] = attr;
    }
    trailAttr.aT0.array.fill(-FAR);
    trailAttr.aT1.array.fill(-FAR);
    trailAttr.aT2.array.fill(-FAR);
    trailGeo.instanceCount = TRAIL_MAX;
    const trailMat = new THREE.ShaderMaterial({
      uniforms: trailUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: `
        uniform float uNow, uSpeed, uBaseY, uZ, uTop;
        attribute float aX, aW, aT0, aT1, aT2, aVel;
        attribute vec3 aColor;
        varying vec2 vP;
        varying float vBot, vTop, vHold, vW, vVel, vSounding, vHeld;
        varying vec3 vColor;
        void main() {
          float bot = uBaseY + (uNow - min(uNow, aT2)) * uSpeed;
          if (aT0 < -1e5 || bot > uTop) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
          float top = uBaseY + (uNow - aT0) * uSpeed;
          float pad = aW * 1.2;
          float w = aW + pad * 2.0;
          float y = mix(bot - pad, max(top, bot + 0.001) + pad, position.y);
          vP = vec2(position.x * w, y);
          vBot = bot; vTop = top; vHold = uBaseY + (uNow - min(uNow, aT1)) * uSpeed;
          vW = aW; vVel = aVel; vColor = aColor; vSounding = aT2 > uNow ? 1.0 : 0.0; vHeld = aT1 > uNow ? 1.0 : 0.0;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(aX + vP.x, y, uZ, 1.0);
        }`,
      fragmentShader: `
        #define TAIL_FLOOR ${TAIL_FLOOR.toFixed(3)}
        #define TAIL_TAU ${TAIL_TAU.toFixed(3)}
        uniform float uTop, uSpeed, uEnergy;
        varying vec2 vP;
        varying float vBot, vTop, vHold, vW, vVel, vSounding, vHeld;
        varying vec3 vColor;
        float sdRoundBox(vec2 p, vec2 b, float r) {
          vec2 q = abs(p) - b + r;
          return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
        }
        void main() {
          float h = max(vTop - vBot, 0.0);
          float r = min(vW * 0.5, h * 0.5);
          float d = sdRoundBox(vP - vec2(0.0, 0.5 * (vTop + vBot)), vec2(vW * 0.5, h * 0.5), r);
          float core = 1.0 - smoothstep(-0.025, 0.025, d);
          float halo = exp(-max(d, 0.0) * 4.5 / max(vW, 0.1)) * (1.0 - core);
          float axis = 1.0 - smoothstep(0.0, vW * 0.5, abs(vP.x));
          float held = smoothstep(vHold - 0.1, vHold + 0.1, vP.y);
          // below the release point the bar is pedal sustain: an afterglow that starts at full energy
          // (no step at the release point) and decays to a floor, so a pedalled note stays a column
          // standing on the rail, as today, while a long pedalled passage cannot pile up into a wall
          float tailAge = max(vHold - vP.y, 0.0) / max(uSpeed, 0.1);
          float tail = TAIL_FLOOR + (1.0 - TAIL_FLOOR) * exp(-tailAge / TAIL_TAU);
          float energy = mix(0.5, 1.0, vVel) * mix(tail, 1.0, held);
          float fade = 1.0 - smoothstep(uTop * 0.6, uTop, vP.y);
          vec3 col = vColor * (core * (0.75 + 1.15 * axis * axis) + halo * 0.24) * energy;
          col += vec3(1.0) * core * pow(axis, 3.0) * 0.14 * energy;
          float fd = length((vP - vec2(0.0, vBot)) * vec2(1.0 / max(vW, 0.1), 1.4));
          col += vColor * mix(0.2 * vSounding, 1.0, vHeld) * exp(-fd * 1.9) * 1.5 * mix(0.5, 1.0, vVel);
          // uEnergy: density scaling from the sustain rules, so brightness stays bounded with note count
          gl_FragColor = vec4(col * fade * uEnergy, 1.0);
        }`,
    });
    const trailMesh = new THREE.Mesh(trailGeo, trailMat);
    trailMesh.frustumCulled = false;
    scene.add(trailMesh);

    let trailsDirty = false;
    let trailNext = 0;
    function trailStart(m, vel, t) {
      const A = trailAttr;
      let slot = -1;
      for (let i = 0; i < TRAIL_MAX; i++) {
        const j = (trailNext + i) % TRAIL_MAX;
        const gone = A.aT0.array[j] < -1e5 || (A.aT2.array[j] < t && RAIL_Y + (t - A.aT2.array[j]) * TRAIL_SPEED > 80);
        if (gone) { slot = j; break; }
      }
      if (slot < 0) slot = trailNext;  // every slot busy: recycle the oldest in ring order
      trailNext = (slot + 1) % TRAIL_MAX;
      A.aX.array[slot] = keyX(m);
      A.aW.array[slot] = isBlack(m) ? 0.44 : 0.64;
      A.aT0.array[slot] = t;
      A.aT1.array[slot] = FAR;
      A.aT2.array[slot] = FAR;
      A.aVel.array[slot] = vel / 127;
      const c = noteColor(m, vel);
      A.aColor.array.set([c.r, c.g, c.b], slot * 3);
      trailsDirty = true;
      return { slot, t0: t };
    }
    // A slot may have been recycled by a later strike; the stored t0 tells a stale ref apart.
    const owns = (ref) => ref && trailAttr.aT0.array[ref.slot] === Math.fround(ref.t0);
    function trailRelease(ref, t) {
      if (!owns(ref)) return;
      trailAttr.aT1.array[ref.slot] = Math.min(trailAttr.aT1.array[ref.slot], t);
      trailsDirty = true;
    }
    function trailEnd(ref, t) {
      if (!owns(ref)) return;
      trailAttr.aT1.array[ref.slot] = Math.min(trailAttr.aT1.array[ref.slot], t);
      trailAttr.aT2.array[ref.slot] = Math.min(trailAttr.aT2.array[ref.slot], t);
      trailsDirty = true;
    }
    function liveCount(t) {
      let n = 0;
      const top = trailUniforms.uTop.value;
      for (let j = 0; j < TRAIL_MAX; j++) {
        const t2 = trailAttr.aT2.array[j];
        if (trailAttr.aT0.array[j] > -1e5 && RAIL_Y + (t - Math.min(t, t2)) * TRAIL_SPEED <= top) n++;
      }
      return n;
    }

    // --------------------------------------------------------------- sparks --
    const sparkUniforms = { uNow: { value: 0 }, uPx: { value: 1000 } };
    const sparkGeo = new THREE.BufferGeometry();
    const sparkAttr = {};
    for (const [name, size] of [["position", 3], ["aVel", 3], ["aBirth", 1], ["aLife", 1], ["aSize", 1], ["aSeed", 1], ["aColor", 3]]) {
      const attr = new THREE.BufferAttribute(new Float32Array(SPARK_MAX * size), size);
      attr.setUsage(THREE.DynamicDrawUsage);
      sparkGeo.setAttribute(name, attr);
      sparkAttr[name] = attr;
    }
    sparkAttr.aBirth.array.fill(-FAR);
    const sparkMat = new THREE.ShaderMaterial({
      uniforms: sparkUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: `
        uniform float uNow, uPx;
        attribute vec3 aVel, aColor;
        attribute float aBirth, aLife, aSize, aSeed;
        varying vec3 vColor;
        varying float vAlpha;
        void main() {
          float age = uNow - aBirth;
          if (age < 0.0 || age > aLife) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
          float k = age / aLife;
          vec3 p = position + aVel * age + vec3(sin(age * 2.7 + aSeed) * 0.35 * k, 0.9 * age * age, 0.0);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = aSize * uPx * (1.0 - 0.6 * k) / max(-mv.z, 0.1);
          vAlpha = (1.0 - k) * (1.0 - k);
          vColor = aColor;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vAlpha;
        void main() {
          float r = length(gl_PointCoord - 0.5);
          float a = smoothstep(0.5, 0.0, r);
          gl_FragColor = vec4(vColor * a * a * vAlpha * 3.2, 1.0);
        }`,
    });
    const sparkPoints = new THREE.Points(sparkGeo, sparkMat);
    sparkPoints.frustumCulled = false;
    scene.add(sparkPoints);
    let sparkNext = 0;
    let sparksDirty = false;
    function burst(m, vel, t) {
      const count = Math.round(6 + 20 * (vel / 127));
      const c = noteColor(m, vel);
      const x = keyX(m);
      for (let i = 0; i < count; i++) {
        const j = sparkNext;
        sparkNext = (sparkNext + 1) % SPARK_MAX;
        sparkAttr.position.array.set([x + (Math.random() - 0.5) * 0.5, RAIL_Y + 0.05, TRAIL_Z + 0.1], j * 3);
        sparkAttr.aVel.array.set([(Math.random() - 0.5) * 1.8, 1.6 + Math.random() * 4.5 * (0.5 + vel / 254),
                                  (Math.random() - 0.3) * 0.9], j * 3);
        sparkAttr.aBirth.array[j] = t;
        sparkAttr.aLife.array[j] = 0.7 + Math.random() * 1.6;
        sparkAttr.aSize.array[j] = 0.16 + Math.random() * 0.26;
        sparkAttr.aSeed.array[j] = Math.random() * 6.283;
        sparkAttr.aColor.array.set([c.r * 1.2 + 0.08, c.g * 1.2 + 0.08, c.b * 1.2 + 0.08], j * 3);
      }
      sparksDirty = true;
    }

    // ------------------------------------------------------------- instance --
    const strikes = new Map();  // midi -> trail ref of the strike that is sounding
    let active = false;
    let energy = 1;
    trailMesh.visible = false;
    sparkPoints.visible = false;

    return {
      noteOn(m, vel, t) {
        strikes.set(m, trailStart(m, vel, t));
        burst(m, vel, t);
      },
      noteRelease(m, t) {
        trailRelease(strikes.get(m), t);
      },
      noteEnd(m, t) {
        trailEnd(strikes.get(m), t);
        strikes.delete(m);
      },
      pedal() { /* the trails already draw pedal sustain as the dim tail below each release */ },
      update(dt, t, frame) {
        trailUniforms.uNow.value = t;
        sparkUniforms.uNow.value = t;
        if (frame.view) {
          trailUniforms.uTop.value = frame.view.top;
          sparkUniforms.uPx.value = frame.view.pointScale;
        }
        // Density scaling: falls at once when notes pile up, recovers gently when they end.
        const target = 1 / Math.sqrt(1 + frame.sounding.size / 10);
        energy = target < energy ? target : damp(energy, target, 0.25, dt);
        trailUniforms.uEnergy.value = energy;
        if (trailsDirty) { for (const attr of Object.values(trailAttr)) attr.needsUpdate = true; trailsDirty = false; }
        if (sparksDirty) { for (const attr of Object.values(sparkAttr)) attr.needsUpdate = true; sparksDirty = false; }
      },
      resize() { /* uTop and the point scale arrive with every frame's view */ },
      setActive(on) {
        active = !!on;
        trailMesh.visible = active;
        sparkPoints.visible = active;
      },
      dispose() {
        scene.remove(trailMesh);
        scene.remove(sparkPoints);
        trailGeo.dispose();
        trailMat.dispose();
        sparkGeo.dispose();
        sparkMat.dispose();
        strikes.clear();
      },
      stats(t) {
        return { trailsLive: liveCount(t), trailCap: TRAIL_MAX, energy: +energy.toFixed(3), active };
      },
    };
  },
};
