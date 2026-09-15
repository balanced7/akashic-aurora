// Harmonic Wave — arsenal/web/piano/schemes/harmonic-wave.js  (ES module, a piano scheme)
// Navi's idea (research/in-flight/piano-ideas-2026-09-13/navi-kimi.md, PIANO-V2-SPEC.md 6.4):
// above the keys, one bloomed line that is the literal summed waveform of the harmony's frequencies.
//
//   y(u) = sum_i a_i * sin(k_i * (u - 0.5 + scroll)),   k_i = 2*pi * cycles(ref) * f_i / f_ref
//
// u runs 0..1 across the frame. Each sine keeps its note's real frequency ratio to the lowest
// sounding note (ref), so a chord's shape is its physics: y(u) is exactly the air pressure of those
// sines at time tau(u) = cycles * (u - 0.5 + scroll) / f_ref (see waveTime). cycles(ref) is about 3,
// so the lowest note shows about three periods. The waveform travels slowly (scroll), clock-driven.
//
// Two strands:
//   A  the harmony set (finger-held notes, pedal-held notes struck within 1.5 s, and the lowest
//      pedal-held note when it is the lowest sounding note), amplitude 1 each. Bright; thickness
//      follows velocity; only its finger-held core and attacks cross the bloom threshold.
//   B  everything sounding: the harmony at 1 plus pedal-only notes at half amplitude. Thin, dim,
//      under the bloom threshold, and shown only while the pedal holds notes outside the harmony,
//      so a pedal lift is one visible clearing: B collapses into A in 150 ms.
//
// A chord change is a 150 ms crossfade of sine amplitudes (smoothstep), so the line never jumps.
// Light never sums: each strand is drawn as capsule segments whose pixels are merged by MAXIMUM
// (a pixel shows its distance to the nearest part of the line, however many segments overlap it),
// and colour is bounded by the note palette. Silence leaves a faint resting line; a single note is a
// clean sine.
//
// Everything comes from ctx (no imports), so node can import this file to test the pure helpers.

const TAU = Math.PI * 2;
export const MORPH_S = 0.15;          // a chord change crossfades over this long
export const RECENT_S = 1.5;          // pedal-held notes struck within this long still name the harmony
export const PEDAL_AMP = 0.5;         // pedal-only notes add into strand B at half amplitude
export const SCROLL_PER_S = 0.045;    // how fast the waveform travels, in frame widths per second
const MIN_SAMPLES = 256;
const MAX_SAMPLES = 1600;
const SAMPLES_PER_PERIOD = 14;
const STOPS = 17;                     // colour table resolution across the frame
const SPREAD = 4.2;                   // line radius (core + soft halo) in core half-widths

// Where the wave lives, in output pixels. It sits above the projected back rail and never rises
// above `top`, which clears the core's overlay boxes as piano-next.js lays them out today: in 9:16
// the staff layer ends at y 1100 (so the spec's 230-630 band is cleared by far), in 16:9 at y 532.
const LAYOUT = {
  "9:16": { top: 1132, railGap: 20, minHalf: 70, maxHalf: 150 },
  "16:9": { top: 590, railGap: 20, minHalf: 60, maxHalf: 120 },
};

// ------------------------------------------------------------------ pure helpers (node-tested) --
export const midiFreq = (m) => 440 * 2 ** ((m - 69) / 12);
// About three periods of the lowest note; a touch fewer in the bass and more in the treble, so
// even a lone note says roughly where it is (A0 2.26, C4 3.00, C8 4.24).
export const cyclesFor = (refM) => 3 * 2 ** ((refM - 60) / 96);
export const waveNumber = (m, refM) => TAU * cyclesFor(refM) * 2 ** ((m - refM) / 12);
export const ease = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

// The harmony set (PIANO-V2-SPEC.md 6.1), computed locally until the host's Theory provides it.
// sounding: Map or iterable of [midi, {held, vel, t0, inRange?}]. Returns ascending MIDI numbers.
export function harmonySet(sounding, t) {
  const notes = [];
  let lowest = Infinity, lowestPedal = Infinity;
  for (const [m, st] of sounding) {
    if (!st || st.inRange === false) continue;
    if (m < lowest) lowest = m;
    if (st.held) {
      notes.push(m);
    } else {
      if (t - st.t0 <= RECENT_S) notes.push(m);
      if (m < lowestPedal) lowestPedal = m;
    }
  }
  if (lowest !== Infinity && lowestPedal === lowest && !notes.includes(lowest)) notes.push(lowest);
  return notes.sort((a, b) => a - b);
}

// components: [{k, a}]. The one function every drawn sample comes from.
export function sampleWave(components, u, scroll = 0) {
  let y = 0;
  for (const c of components) y += c.a * Math.sin(c.k * (u - 0.5 + scroll));
  return y;
}
// The physical time (seconds) that position u shows: sampleWave(u) == sum a_i sin(2 pi f_i waveTime(u)).
export const waveTime = (u, refM, scroll = 0) => cyclesFor(refM) * (u - 0.5 + scroll) / midiFreq(refM);

// Fill out[0..n-1] with sampleWave at u = i / (n - 1).
export function sampleInto(components, scroll, n, out) {
  out.fill(0, 0, n);
  const last = n - 1;
  for (const c of components) {
    if (!(Math.abs(c.a) > 1e-6)) continue;
    for (let i = 0; i < n; i++) out[i] += c.a * Math.sin(c.k * (i / last - 0.5 + scroll));
  }
  return out;
}

// A strand is a set of sine components that crossfade toward targets. One component per (note, ref):
// a new lowest note gives every note a new wave number, so the old shape crossfades into the new one.
export function createStrand() {
  return { comps: [] };
}
export function componentAmp(c, t) {
  return c.from + (c.to - c.from) * ease((t - c.ts) / MORPH_S);
}
// targets: Map midi -> amplitude. Retargets from the current amplitude, so a change mid-morph is continuous.
export function retarget(strand, targets, refM, t) {
  const kept = new Set();
  for (const c of strand.comps) {
    const live = c.refM === refM && targets.has(c.m);
    if (live) kept.add(c.m);
    const want = live ? targets.get(c.m) : 0;
    if (want !== c.to) { c.from = componentAmp(c, t); c.to = want; c.ts = t; }
  }
  if (refM !== null && refM !== undefined) {
    for (const [m, amp] of targets) {
      if (!kept.has(m)) strand.comps.push({ m, refM, k: waveNumber(m, refM), from: 0, to: amp, ts: t, a: 0 });
    }
  }
  let w = 0;
  for (const c of strand.comps) if (!(c.to === 0 && t - c.ts >= MORPH_S)) strand.comps[w++] = c;
  strand.comps.length = w;
}
// Display gain: the sum is scaled by 1 / max(peak, 1), with a peak follower that rises at once and
// falls with a 0.6 s time constant. A fading chord therefore shrinks toward the resting line, and a
// scaled sum is still the sum (one gain for the whole strand, never a per-sample squash).
export const followPeak = (pk, peak, dt) => Math.max(peak, pk * Math.exp(-dt / 0.6));
export const gainFor = (pk) => 1 / Math.max(pk, 1);
export function evalStrand(strand, t) {
  let sum = 0, maxK = 0;
  for (const c of strand.comps) {
    c.a = componentAmp(c, t);
    sum += c.a;
    if (c.a > 1e-3 && c.k > maxK) maxK = c.k;
  }
  return { sum, maxK };
}

// ------------------------------------------------------------------------------------ scheme --
const damp = (current, target, tau, dt) => current + (target - current) * (1 - Math.exp(-dt / Math.max(tau, 1e-4)));
const REST = [0.10, 0.15, 0.34];      // the resting line's colour (linear)

export default {
  id: "harmonic-wave",
  name: "Harmonic Wave",

  create(ctx) {
    const { THREE, scene, camera, noteColor, RAIL_Y, TRAIL_Z } = ctx;
    const hostHarmony = ctx.Theory && typeof ctx.Theory.harmonySet === "function" ? ctx.Theory.harmonySet : null;
    let W = ctx.framing.width, H = ctx.framing.height, fid = ctx.framing.id;

    // ---------------------------------------------------------------------------------- lines --
    // One mesh per strand: a quad per segment, positioned in output pixels (screen-anchored, so the
    // line stays clear of the overlay whatever the camera does). The fragment shader measures the
    // pixel's distance to its own segment and draws a core, a hot centre and a soft halo from it.
    // MAX blending merges overlapping segments, so joints, folds and sharp peaks never double up.
    const SEG = MAX_SAMPLES - 1;
    function makeLine(order) {
      const geo = new THREE.BufferGeometry();
      const corner = new Float32Array(SEG * 4 * 3);
      for (let s = 0; s < SEG; s++) corner.set([-1, -1, 0, -1, 1, 0, 1, -1, 0, 1, 1, 0], s * 12);
      geo.setAttribute("position", new THREE.BufferAttribute(corner, 3));   // the quad corner (along, across)
      const attr = (size) => {
        const a = new THREE.BufferAttribute(new Float32Array(SEG * 4 * size), size);
        a.setUsage(THREE.DynamicDrawUsage);
        return a;
      };
      const aA = attr(2), aB = attr(2), aU = attr(1), aColor = attr(3);
      geo.setAttribute("aA", aA);
      geo.setAttribute("aB", aB);
      geo.setAttribute("aU", aU);
      geo.setAttribute("aColor", aColor);
      const index = new Uint16Array(SEG * 6);
      for (let s = 0; s < SEG; s++) { const a = s * 4; index.set([a, a + 1, a + 2, a + 1, a + 3, a + 2], s * 6); }
      geo.setIndex(new THREE.BufferAttribute(index, 1));
      geo.setDrawRange(0, 0);
      const uniforms = { uRes: { value: new THREE.Vector2(W, H) }, uHW: { value: 3 }, uRadius: { value: 12 },
                         uIntensity: { value: 1 }, uHot: { value: 0 }, uAlpha: { value: 1 }, uHalo: { value: 0.2 } };
      const mat = new THREE.ShaderMaterial({
        uniforms, transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
        blending: THREE.CustomBlending, blendEquation: THREE.MaxEquation,
        blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
        vertexShader: `
          uniform vec2 uRes;
          uniform float uRadius;
          attribute vec2 aA, aB;
          attribute float aU;
          attribute vec3 aColor;
          varying vec2 vP, vA, vB;
          varying float vU;
          varying vec3 vColor;
          void main() {
            vec2 d = aB - aA;
            float len = length(d);
            vec2 dir = len > 1e-4 ? d / len : vec2(1.0, 0.0);
            vec2 nrm = vec2(-dir.y, dir.x);
            vec2 p = (position.x < 0.0 ? aA : aB) + dir * position.x * uRadius + nrm * position.y * uRadius;
            vP = p; vA = aA; vB = aB; vU = aU; vColor = aColor;
            gl_Position = vec4(p.x / uRes.x * 2.0 - 1.0, 1.0 - p.y / uRes.y * 2.0, 0.0, 1.0);
          }`,
        fragmentShader: `
          uniform float uHW, uRadius, uIntensity, uHot, uAlpha, uHalo;
          varying vec2 vP, vA, vB;
          varying float vU;
          varying vec3 vColor;
          void main() {
            vec2 pa = vP - vA, ba = vB - vA;
            float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
            float d = length(pa - ba * h);
            if (d > uRadius) discard;
            float core = 1.0 - smoothstep(uHW - 0.85, uHW + 0.85, d);
            float halo = 1.0 - smoothstep(uHW, uRadius, d);
            halo *= halo;
            float hot = 1.0 - smoothstep(0.0, uHW * 0.62, d);
            float taper = smoothstep(0.0, 0.045, vU) * (1.0 - smoothstep(0.955, 1.0, vU));
            vec3 coreCol = (vColor * uIntensity + vec3(hot * uHot)) * core;
            vec3 haloCol = vColor * 0.6 * halo * uHalo;
            float k = uAlpha * taper;
            gl_FragColor = vec4(max(coreCol, haloCol) * k, max(core, halo * uHalo) * k);
          }`,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.frustumCulled = false;
      mesh.renderOrder = order;
      mesh.visible = false;
      scene.add(mesh);
      return { geo, mat, mesh, aA, aB, aU, aColor, uniforms };
    }
    const lineB = makeLine(40);   // the pedal strand
    const lineA = makeLine(41);   // the harmony strand

    // ---------------------------------------------------------------------------------- state --
    const strandA = createStrand();
    const strandB = createStrand();
    const targetsA = new Map();
    const targetsB = new Map();
    const yA = new Float64Array(MAX_SAMPLES);
    const yB = new Float64Array(MAX_SAMPLES);
    const px = new Float32Array(MAX_SAMPLES * 2);
    const cols = new Float32Array(MAX_SAMPLES * 3);
    const colour = new THREE.Color();
    const railPoint = new THREE.Vector3();
    // colour tables (STOPS x rgb) per strand: `from` is a snapshot, `to` the target gradient
    const palette = () => ({ from: new Float32Array(STOPS * 3), to: new Float32Array(STOPS * 3),
                             now: new Float32Array(STOPS * 3), ts: -1e9, sig: null });
    const palA = palette(), palB = palette();
    let refM = null;
    let lastOn = { t: -1e9, vel: 0 };
    let strikes = 0, strikesAt = -1e9;   // strikes in a decaying 0.5 s window
    let vel = 0.6, held = 0, presB = 0, pkA = 1, pkB = 1;
    let active = false;
    let lastHarmony = [];
    let lastN = 0, lastScroll = 0, lastCentre = 0, lastHalf = 0, gainA = 1, gainB = 1;
    const centreA = new Float32Array(MAX_SAMPLES);  // the drawn centreline of strand A, px (for inspect)

    function gradientInto(pal, notes, velOf, t) {
      const sig = notes.join(",");
      if (sig === pal.sig || !notes.length) return;
      if (pal.sig === null) {
        fillGradient(pal.to, notes, velOf);
        pal.from.set(pal.to);
        pal.now.set(pal.to);
      } else {
        pal.from.set(pal.now);
        fillGradient(pal.to, notes, velOf);
      }
      pal.ts = t;
      pal.sig = sig;
    }
    // Stops evenly across the frame, lowest pitch on the left; at most eight, picked evenly.
    function fillGradient(table, notes, velOf) {
      let pick = notes;
      if (notes.length > 8) pick = Array.from({ length: 8 }, (_, i) => notes[Math.round(i * (notes.length - 1) / 7)]);
      const rgb = pick.map((m) => { noteColor(m, velOf(m), colour); return [colour.r, colour.g, colour.b]; });
      for (let s = 0; s < STOPS; s++) {
        const x = (s / (STOPS - 1)) * pick.length - 0.5;
        const i0 = Math.max(0, Math.min(pick.length - 1, Math.floor(x)));
        const i1 = Math.max(0, Math.min(pick.length - 1, i0 + 1));
        const f = Math.max(0, Math.min(1, x - i0));
        for (let c = 0; c < 3; c++) table[s * 3 + c] = rgb[i0][c] + (rgb[i1][c] - rgb[i0][c]) * f;
      }
    }
    function blendPalette(pal, t) {
      const e = ease((t - pal.ts) / MORPH_S);
      for (let i = 0; i < STOPS * 3; i++) pal.now[i] = pal.from[i] + (pal.to[i] - pal.from[i]) * e;
    }

    // Writes one strand: sample points in pixels, then one quad per segment.
    function writeLine(line, ys, n, gain, centre, half, hw, pal, restMix, keepCentre) {
      const x0 = -0.01 * W, x1 = 1.01 * W;
      for (let i = 0; i < n; i++) {
        const u = i / (n - 1);
        px[i * 2] = x0 + u * (x1 - x0);
        px[i * 2 + 1] = centre - ys[i] * gain * half;
        if (keepCentre) centreA[i] = px[i * 2 + 1];
        const s = u * (STOPS - 1);
        const s0 = Math.min(STOPS - 2, Math.floor(s));
        const f = s - s0;
        for (let c = 0; c < 3; c++) {
          const g = pal.now[s0 * 3 + c] + (pal.now[(s0 + 1) * 3 + c] - pal.now[s0 * 3 + c]) * f;
          cols[i * 3 + c] = g + (REST[c] - g) * restMix;
        }
      }
      const A = line.aA.array, B = line.aB.array, U = line.aU.array, C = line.aColor.array;
      for (let s = 0; s < n - 1; s++) {
        const ax = px[s * 2], ay = px[s * 2 + 1], bx = px[s * 2 + 2], by = px[s * 2 + 3];
        const ua = s / (n - 1), ub = (s + 1) / (n - 1);
        for (let v = 0; v < 4; v++) {
          const j = s * 4 + v;
          A[j * 2] = ax; A[j * 2 + 1] = ay;
          B[j * 2] = bx; B[j * 2 + 1] = by;
          const endB = v >= 2;
          U[j] = endB ? ub : ua;
          const src = (endB ? s + 1 : s) * 3;
          C[j * 3] = cols[src]; C[j * 3 + 1] = cols[src + 1]; C[j * 3 + 2] = cols[src + 2];
        }
      }
      line.uniforms.uRes.value.set(W, H);
      line.uniforms.uHW.value = hw;
      line.uniforms.uRadius.value = hw * SPREAD + 1;
      line.geo.setDrawRange(0, (n - 1) * 6);
      for (const [a, size] of [[line.aA, 2], [line.aB, 2], [line.aU, 1], [line.aColor, 3]]) {
        a.clearUpdateRanges();
        a.addUpdateRange(0, (n - 1) * 4 * size);
        a.needsUpdate = true;
      }
    }

    function layout() {
      const L = LAYOUT[fid] || LAYOUT["9:16"];
      camera.updateMatrixWorld();
      railPoint.set(camera.position.x, RAIL_Y, TRAIL_Z).project(camera);
      const railPx = (1 - railPoint.y) / 2 * H;
      const bottom = Number.isFinite(railPx) ? Math.min(railPx - L.railGap, H - 40) : H * 0.68;
      const half = Math.max(L.minHalf, Math.min(L.maxHalf, (bottom - L.top) / 2));
      return { centre: Math.max(L.top + half, bottom - half), half };
    }

    const velOf = (sounding) => (m) => { const st = sounding.get(m); return st ? st.vel : 90; };

    function update(dt, t, frame) {
      const f = frame.framing || ctx.framing;
      if (f && (f.width !== W || f.height !== H || f.id !== fid)) { W = f.width; H = f.height; fid = f.id; }
      const sounding = frame.sounding;

      // 1. what sounds, and what names the harmony
      const harmony = hostHarmony ? [...hostHarmony(sounding, t)].sort((a, b) => a - b) : harmonySet(sounding, t);
      lastHarmony = harmony;
      targetsA.clear();
      targetsB.clear();
      for (const m of harmony) targetsA.set(m, 1);
      let lowest = Infinity, anyHeld = false, velSum = 0;
      const all = [];
      for (const [m, st] of sounding) {
        if (!st || st.inRange === false) continue;
        all.push(m);
        if (m < lowest) lowest = m;
        targetsB.set(m, targetsA.has(m) ? 1 : PEDAL_AMP);
      }
      for (const m of harmony) {
        const st = sounding.get(m);
        if (st) { velSum += st.vel; if (st.held) anyHeld = true; }
      }
      all.sort((a, b) => a - b);
      if (lowest !== Infinity) refM = lowest;
      retarget(strandA, targetsA, refM, t);
      retarget(strandB, targetsB, refM, t);
      const evA = evalStrand(strandA, t);
      const evB = evalStrand(strandB, t);

      // 2. colour, thickness and brightness
      gradientInto(palA, harmony, velOf(sounding), t);
      gradientInto(palB, all, velOf(sounding), t);
      blendPalette(palA, t);
      blendPalette(palB, t);
      if (harmony.length) {
        const v = velSum / harmony.length / 127;
        vel = damp(vel, v, v > vel ? 0.04 : 0.3, dt);
      }
      held = damp(held, anyHeld ? 1 : 0, anyHeld ? 0.04 : 0.2, dt);
      presB = damp(presB, targetsB.size > targetsA.size ? 1 : 0, 0.05, dt);
      // Attacks may cross the bloom threshold, but a storm of them must not light the frame: the flash
      // shrinks with the strike rate (8 strikes/s gives a third), so bloom follows accents, not density.
      const rate = strikes * Math.exp(-Math.max(0, t - strikesAt) / 0.5) / 0.5;
      const age = t - lastOn.t;
      const attack = age >= 0 ? (lastOn.vel / 127) * Math.exp(-age / 0.14) / (1 + rate / 4) : 0;
      const restMix = 1 - Math.min(1, evA.sum);

      // 3. samples: enough for SAMPLES_PER_PERIOD at the highest audible partial
      const periods = Math.max(evA.maxK, evB.maxK) / TAU;
      const n = Math.max(MIN_SAMPLES, Math.min(MAX_SAMPLES, Math.ceil(periods * SAMPLES_PER_PERIOD) + 1));
      const scroll = t * SCROLL_PER_S;
      sampleInto(strandA.comps, scroll, n, yA);
      let peak = 0;
      for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(yA[i]));
      pkA = followPeak(pkA, peak, dt);
      gainA = gainFor(pkA);

      const { centre, half } = layout();
      const periodsA = evA.maxK / TAU;
      const densityW = Math.max(0.42, Math.min(1, Math.sqrt(12 / Math.max(periodsA, 12))));
      const densityI = 1 / Math.sqrt(1 + Math.max(0, evA.sum - 1) / 3);
      const hwBase = (2.1 + 5.2 * Math.pow(vel, 0.9)) * densityW;
      const hwA = hwBase * (1 + 0.65 * attack) * (1 - restMix) + 1.4 * restMix;

      const uA = lineA.uniforms;
      uA.uIntensity.value = ((1.15 + 0.95 * held + 2.2 * attack) * densityI) * (1 - restMix) + 0.9 * restMix;
      uA.uHot.value = ((0.08 + 0.42 * held + 0.9 * attack) * densityI) * (1 - restMix);
      uA.uAlpha.value = 1 - 0.5 * restMix;
      uA.uHalo.value = 0.22 - 0.1 * restMix;
      writeLine(lineA, yA, n, gainA, centre, half, hwA, palA, restMix, true);
      lineA.mesh.visible = active;

      if (presB > 0.004 && strandB.comps.length) {
        sampleInto(strandB.comps, scroll, n, yB);
        peak = 0;
        for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(yB[i]));
        pkB = followPeak(pkB, peak, dt);
        gainB = gainFor(pkB);
        const uB = lineB.uniforms;
        uB.uIntensity.value = 0.8;
        uB.uHot.value = 0;
        uB.uAlpha.value = 0.55 * presB;
        uB.uHalo.value = 0.12;
        writeLine(lineB, yB, n, gainB, centre, half, Math.max(1.1, hwBase * 0.42), palB, 0, false);
        lineB.mesh.visible = active;
      } else {
        lineB.mesh.visible = false;
        pkB = 1;
      }
      lastN = n; lastScroll = scroll; lastCentre = centre; lastHalf = half;
    }

    return {
      noteOn(m, v, t) {
        lastOn = { t, vel: v };
        strikes = strikes * Math.exp(-Math.max(0, t - strikesAt) / 0.5) + 1;
        strikesAt = t;
      },
      noteRelease() { /* frame.sounding carries held vs pedalled */ },
      noteEnd() { /* the strands follow frame.sounding; an ended note fades out over MORPH_S */ },
      pedal() { /* strand B shows the pedal; a lift ends its notes and B collapses into A */ },
      update(dt, t, frame) {
        if (!active) return;
        update(dt, t, frame);
      },
      resize(framing) {
        if (framing) { W = framing.width; H = framing.height; fid = framing.id; }
      },
      setActive(on) {
        active = !!on;
        if (!active) { lineA.mesh.visible = false; lineB.mesh.visible = false; }
      },
      dispose() {
        for (const line of [lineA, lineB]) {
          scene.remove(line.mesh);
          line.geo.dispose();
          line.mat.dispose();
        }
        strandA.comps.length = 0;
        strandB.comps.length = 0;
      },
      stats() {
        return { active, harmony: [...lastHarmony], ref: refM, samples: lastN,
                 componentsA: strandA.comps.length, componentsB: strandB.comps.length,
                 gainA: +gainA.toFixed(4), gainB: +gainB.toFixed(4), pedalStrand: +presB.toFixed(3),
                 source: hostHarmony ? "Theory.harmonySet" : "local harmonySet" };
      },
      // For the harness: the components and the drawn centreline of strand A on the last frame.
      inspect() {
        return { n: lastN, scroll: lastScroll, centre: lastCentre, half: lastHalf, gain: gainA, width: W, height: H,
                 components: strandA.comps.map((c) => ({ m: c.m, refM: c.refM, k: c.k, a: c.a })),
                 centreline: Array.from(centreA.subarray(0, lastN)) };
      },
    };
  },
};
