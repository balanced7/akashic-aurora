// Afterglow Roll: arsenal/web/piano/schemes/synth-sol.js (Sunshine, sol seat), a Synthesia bake-off entry.
// Written by Sunshine in his guarded worktree and relayed over Bifrost in three parts (1789488499033-0, 1789488517906-0,
// 1789488543392-0) plus a one-line correction to updateBreathline; assembled verbatim by Vandor. Design and dynamics note:
// research/in-flight/piano-synthesia-mode-2026-09-15/entry_sol.md. Scheme contract: the piano-next.js scheme host.

const clamp01 = (v) => Math.max(0, Math.min(1, v));

export default {
  id: "synth-sol",
  name: "Afterglow Roll",

  create(ctx) {
    const {
      THREE, scene, keyX, isBlack, noteColor,
      KEY, RAIL_Y, TRAIL_Z,
    } = ctx;

    const MAX = 512;
    const SPEED = 6.5;
    const REPEAT_GAP_S = 0.014;
    const group = new THREE.Group();
    group.name = "synth-sol-afterglow-roll";
    group.visible = false;
    scene.add(group);

    const unitBox = new THREE.BoxGeometry(1, 1, 0.16);
    const railBox = new THREE.BoxGeometry(1, 1, 0.19);
    const beadGeo = new THREE.SphereGeometry(0.5, 10, 7);
    const flashGeo = new THREE.RingGeometry(0.42, 0.58, 18);

    const bodyMat = new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.72,
      depthWrite: false, toneMapped: true,
    });
    const historyMat = new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.30,
      depthWrite: false, toneMapped: true,
    });
    const shellMat = new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.80,
      depthWrite: false, toneMapped: true,
    });
    const peakMat = new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.96,
      depthWrite: false, toneMapped: false,
    });
    const flashMat = new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.92,
      depthWrite: false, side: THREE.DoubleSide, toneMapped: false,
    });

    const bodies = new THREE.InstancedMesh(unitBox, bodyMat, MAX);
    const histories = new THREE.InstancedMesh(unitBox, historyMat, MAX);
    const shellRails = new THREE.InstancedMesh(railBox, shellMat, MAX * 2);
    const peaks = new THREE.InstancedMesh(beadGeo, peakMat, MAX);
    const flashes = new THREE.InstancedMesh(flashGeo, flashMat, 48);
    for (const mesh of [bodies, histories, shellRails, peaks, flashes]) {
      mesh.count = 0;
      mesh.frustumCulled = false;
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      group.add(mesh);
    }

    const BREATH_POINTS = 48;
    const BREATH_SECONDS = 7.5;
    const breathPositions = new Float32Array(BREATH_POINTS * 3);
    const breathGeo = new THREE.BufferGeometry();
    const breathAttr = new THREE.BufferAttribute(breathPositions, 3);
    breathAttr.setUsage(THREE.DynamicDrawUsage);
    breathGeo.setAttribute("position", breathAttr);
    const breathMat = new THREE.LineBasicMaterial({
      color: 0x52d9ff, transparent: true, opacity: 0.64,
      depthWrite: false, toneMapped: true,
    });
    const breathline = new THREE.Line(breathGeo, breathMat);
    breathline.frustumCulled = false;
    group.add(breathline);

    const CROWN_MAX = 16;
    const crownPositions = new Float32Array(CROWN_MAX * 3);
    const crownGeo = new THREE.BufferGeometry();
    const crownAttr = new THREE.BufferAttribute(crownPositions, 3);
    crownAttr.setUsage(THREE.DynamicDrawUsage);
    crownGeo.setAttribute("position", crownAttr);
    crownGeo.setDrawRange(0, 0);
    const crownMat = new THREE.LineBasicMaterial({
      color: 0xa855ff, transparent: true, opacity: 0,
      depthWrite: false, toneMapped: true,
    });
    const crown = new THREE.Line(crownGeo, crownMat);
    crown.visible = false;
    crown.frustumCulled = false;
    group.add(crown);

    const bars = [];
    const live = new Map();
    const dynamics = [];
    const recentOns = [];
    let pedalDown = false;
    let pedalRaw = 0;
    let lastArrival = -Infinity;
    let arrivalTime = -Infinity;
    let lastColourMidi = 60;
    let lastColourVel = 88;

    const matrix = new THREE.Matrix4();
    const colour = new THREE.Color();

    function widthFor(bar) {
      const velocityWidth = 0.40 + 0.28 * clamp01(bar.vel / 127);
      return velocityWidth * (isBlack(bar.midi) ? 0.82 : 1.0);
    }

    function setInstance(mesh, slot, sx, sy, sz, x, y, z, c, gain) {
      matrix.makeScale(sx, sy, sz);
      matrix.setPosition(x, y, z);
      mesh.setMatrixAt(slot, matrix);
      colour.copy(c).multiplyScalar(gain);
      mesh.setColorAt(slot, colour);
    }

    function closeRetrigger(midi, t0) {
      const prior = live.get(midi);
      if (!prior) return;
      const closeAt = Math.max(prior.t0 + 0.001, t0 - REPEAT_GAP_S);
      prior.tRel ??= closeAt;
      prior.tEnd ??= closeAt;
      live.delete(midi);
    }

    function trimEventLists(now) {
      while (dynamics.length && now - dynamics[0].t > BREATH_SECONDS + 2) dynamics.shift();
      while (recentOns.length && now - recentOns[0].t > 0.14) recentOns.shift();
    }

    function triggerCrown(t0) {
      if (recentOns.length < 3 || t0 - lastArrival < 0.75) return;
      let count = 0;
      for (let i = 0; i < recentOns.length && count < CROWN_MAX; i += 1) {
        const event = recentOns[i];
        let duplicate = false;
        for (let j = 0; j < count; j += 1) {
          if (crownPositions[j * 3] === keyX(event.midi)) { duplicate = true; break; }
        }
        if (duplicate) continue;
        const p = count * 3;
        crownPositions[p] = keyX(event.midi);
        crownPositions[p + 1] = RAIL_Y + 0.14 + 0.42 * (event.vel / 127);
        crownPositions[p + 2] = TRAIL_Z + 0.09;
        count += 1;
      }
      if (count < 3) return;
      crownGeo.setDrawRange(0, count);
      crownAttr.needsUpdate = true;
      crown.position.y = 0;
      crown.visible = true;
      crownMat.opacity = 0.76;
      crownMat.color.copy(noteColor(lastColourMidi, lastColourVel)).multiplyScalar(0.72);
      arrivalTime = t0;
      lastArrival = t0;
    }

    function noteOn(midi, vel, t0) {
      closeRetrigger(midi, t0);
      if (bars.length >= MAX) {
        const removed = bars.shift();
        if (live.get(removed.midi) === removed) live.delete(removed.midi);
      }
      const bar = { midi, vel, t0, tRel: null, tEnd: null };
      bars.push(bar);
      live.set(midi, bar);
      dynamics.push({ t: t0, vel });
      recentOns.push({ t: t0, midi, vel });
      lastColourMidi = midi;
      lastColourVel = vel;
      trimEventLists(t0);
      triggerCrown(t0);
    }

    function noteRelease(midi, t) {
      const bar = live.get(midi);
      if (bar) bar.tRel = t;
    }

    function noteEnd(midi, t) {
      const bar = live.get(midi);
      if (!bar) return;
      bar.tRel ??= t;
      bar.tEnd = t;
      live.delete(midi);
    }

    function updateBreathline(t, frameTop) {
      const left = keyX(KEY.first) - 0.72;
      const inward = 0.64;
      for (let i = 0; i < BREATH_POINTS; i += 1) {
        const age = (i / (BREATH_POINTS - 1)) * BREATH_SECONDS;
        const sampleT = t - age;
        let value = 0;
        for (let j = dynamics.length - 1; j >= 0; j -= 1) {
          const event = dynamics[j];
          if (event.t > sampleT) continue;
          const eventAge = sampleT - event.t;
          if (eventAge > 1.8) break;
          value += (event.vel / 127) * Math.exp(-eventAge * 2.2);
        }
        value = clamp01(value);
        const p = i * 3;
        breathPositions[p] = left + inward * value;
        breathPositions[p + 1] = RAIL_Y + age * SPEED;
        breathPositions[p + 2] = TRAIL_Z + 0.12;
      }
      breathAttr.needsUpdate = true;
      breathMat.color.copy(noteColor(lastColourMidi, lastColourVel)).multiplyScalar(0.58);
    }

    function update(dt, t, frame) {
      let bodyCount = 0;
      let historyCount = 0;
      let shellCount = 0;
      let peakCount = 0;
      let flashCount = 0;

      for (let n = 0; n < bars.length; n += 1) {
        const bar = bars[n];
        const end = bar.tEnd ?? t;
        const top = RAIL_Y + (t - bar.t0) * SPEED;
        const bottom = RAIL_Y + (t - end) * SPEED;
        if (bottom > frame.view.top + 0.5) continue;

        const height = Math.max(0.045, top - bottom);
        const width = widthFor(bar);
        const x = keyX(bar.midi);
        const y = bottom + height * 0.5;
        const baseColour = noteColor(bar.midi, bar.vel);
        const pedalHeld = bar.tRel !== null && bar.tEnd === null;
        const ended = bar.tEnd !== null;

        if (pedalHeld) {
          const railWidth = Math.max(0.045, width * 0.105);
          const offset = width * 0.5 - railWidth * 0.5;
          setInstance(shellRails, shellCount++, railWidth, height, 1, x - offset, y, TRAIL_Z, baseColour, 0.74);
          setInstance(shellRails, shellCount++, railWidth, height, 1, x + offset, y, TRAIL_Z, baseColour, 0.74);
        } else if (ended) {
          setInstance(histories, historyCount++, width, height, 1, x, y, TRAIL_Z, baseColour, 0.48);
        } else {
          setInstance(bodies, bodyCount++, width, height, 1, x, y, TRAIL_Z, baseColour, 0.66);
        }

        const strikeAge = Math.max(0, t - bar.t0);
        const velocity = clamp01(bar.vel / 127);
        const peakDecay = Math.exp(-strikeAge * 7.0);
        const peakScale = (0.15 + 0.16 * velocity) * (0.82 + 0.18 * peakDecay);
        const peakGain = 0.64 + peakDecay * (0.72 + 1.15 * velocity);
        setInstance(peaks, peakCount++, peakScale, peakScale * 0.72, peakScale, x, top, TRAIL_Z + 0.055, baseColour, peakGain);

        if (strikeAge < 0.48 && flashCount < 48) {
          const life = 1 - strikeAge / 0.48;
          const radius = (0.18 + 0.52 * velocity) * (1.0 + 0.55 * (1 - life));
          const flashGain = 0.12 + life * life * (1.0 + 1.45 * velocity);
          setInstance(flashes, flashCount++, radius, radius * 0.58, 1, x, RAIL_Y + 0.025, TRAIL_Z + 0.10, baseColour, flashGain);
        }
      }

      bodies.count = bodyCount;
      histories.count = historyCount;
      shellRails.count = shellCount;
      peaks.count = peakCount;
      flashes.count = flashCount;
      for (const mesh of [bodies, histories, shellRails, peaks, flashes]) {
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      }

      updateBreathline(t, frame.view.top);

      if (crown.visible) {
        const age = t - arrivalTime;
        crown.position.y = age * SPEED;
        crownMat.opacity = 0.76 * Math.exp(-age * 2.15);
        if (age > 1.8 || crown.position.y + RAIL_Y > frame.view.top + 1) crown.visible = false;
      }
    }

    return {
      noteOn,
      noteRelease,
      noteEnd,
      pedal(down, raw, t) {
        pedalDown = down;
        pedalRaw = raw;
        void pedalDown;
        void pedalRaw;
        void t;
      },
      update,
      resize(framing) { void framing; },
      setActive(on) { group.visible = on; },
      dispose() {
        scene.remove(group);
        for (const mesh of [bodies, histories, shellRails, peaks, flashes]) mesh.dispose();
        unitBox.dispose();
        railBox.dispose();
        beadGeo.dispose();
        flashGeo.dispose();
        bodyMat.dispose();
        historyMat.dispose();
        shellMat.dispose();
        peakMat.dispose();
        flashMat.dispose();
        breathGeo.dispose();
        breathMat.dispose();
        crownGeo.dispose();
        crownMat.dispose();
      },
    };
  },
};
