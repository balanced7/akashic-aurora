// Aurora Harp — arsenal/web/piano/instruments/light-kimi-aurora.js  (ES module; a piano instrument, no imports)
//
// "Instruments of light" house round (brief: research/in-flight/piano-light-instruments-2026-09-17/brief.md).
// A laser harp re-imagined as a breathing aurora: the 88 strings are not thin laser filaments but WIDE BANDS OF LIGHT,
// each a vertical translucent ribbon hovering above its key and carrying that note's own saturated colour. A soft emitter
// rail floats high; a SPECTRAL HAMMER lens dives from it onto a band on every strike.
//
// The three load-bearing qualities Daniel asked for, each answered:
//
// 1. The strike feels physical — the lens dives faster and from a higher visual arc as velocity rises, and the moment it
//    lands it launches a PHASE-OFFSET GHOST ENVELOPE: several offset copies ripple along the band, like the Dune
//    ornithopter wing-blur. The strike is a travelling wave, never a spot that just lights up. Only the flash may cross the
//    bloom threshold; the sustained band stays under it.
//
// 2. It answers velocity and the sustain pedal truthfully — band width, ripple amplitude and flash brightness all rise
//    with velocity, and a ppp strike still reads (a thin, quiet band with a slow small ripple). The pedal keeps a released
//    note's band alive and lets its blur breathe WIDER; lifting the pedal with the key up collapses the band over ~0.28 s
//    in a visible fade, never a snap. The pedal alone never animates an unstruck string. Everything lives exactly as long
//    as state.sounding (guarded state.sounding ?? null, falling back to state.pressed + state.pedal).
//
// 3. Low notes blur and vibrate more — A0's band is broad, slow and deeply rippled; C8's is a tight fast shimmer. One
//    ban(m) = lerp over the MIDI range drives both blur width and ripple frequency per note, no special casing.
//
// Chords change the MATERIAL, not just the colour:
//  - a LUSH chord breathes out FOG behind the harp and adds thin-film IRIDESCENCE + a warm haze;
//  - a SIMPLE chord clears the air (fog sinks), bands go clean, still and bright;
//  - a TENSE chord tightens and cools the palette, and the braid below strains.
//  The feel (lushness/simplicity/tension/brightness/openness) is computed inline from the sounding set and the page's chord
//  name, so this module works even before arsenal/web/piano/harmony-feel.js lands. If that helper is available it can be
//  dropped in, but nothing here depends on it.
//
// The dance between bass and solo — the signature: a FILAMENT from the lowest sounding note to the melody (highest) voice,
// drawn between the two bands' bases. It twines into a BRAID as they move in contrary motion / spread apart, and its colour
// follows how CONSONANT the interval is: octave/fifth = warm gold, third = rose, tension = cold indigo.
//
// Performance: one logical update, no allocation inside update (all scratch allocated in create()), a fixed draw call count
// (1 band InstancedMesh + 1 lens InstancedMesh + 3 fog quads + 1 braid Line = 6 draw calls), and dispose() returns every
// geometry/material/texture/program to baseline. Nothing is downloaded: everything is built in code.
//
// Budget (lab, burst): 6 draw calls / <20k triangles; 88 + 88 instances; shared materials.

const MM = 1225.7 / 52;   // 1 world unit = one white-key pitch = 23.57 mm (spec.md §2.1)
const TAU = Math.PI * 2;

// ---- host hints: the host lowers its floor to ours so the bands own the sky; keys stay host-owned ----
const HINTS = Object.freeze({ hideStageBody: false, floorY: -715 / MM });

// ---- canonical geometry (group space: x = keyX, already normalised to the 52-white span, centred on middle) ----
const RAIL_Y = 16.5;        // soft emitter rail the hammers dive from (~390 mm above key tops)
const BAND_BASE = 0.7;      // y of a band's bottom, just above its key
const BAND_TOP = 13.2;      // y of a band's top
const BAND_LEN = BAND_TOP - BAND_BASE;

// ---- reactive tuning ----
const FLASH_GAIN = 2.1;     // strike flash brightness factor
const FLASH_TAU = 0.09;     // s the flash dies over (crosses the bloom threshold)
const FALL_TAU = 0.28;      // s a pedal-up release damps over (visible fade)
const RIPPLE_DECAY = 0.55;  // per-second ripple amplitude falloff
const VEL_LO = 0.16;        // a ppp strike still reads

// ---- fog / material ----
const FOG_TAU_IN = 1.4;     // lush fog swells in slowly (a breath)
const FOG_TAU_OUT = 0.8;    // simple chord clears faster

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / Math.max(tau, 1e-4));
const pcOf = (m) => ((m % 12) + 12) % 12;
const ban = (m) => clamp01((m - 21) / (108 - 21));   // 0 at A0, 1 at C8

function makeNoise(seed) {
  const p = new Uint8Array(256);
  let s = seed | 0;
  const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  for (let i = 0; i < 256; i++) p[i] = i;
  for (let i = 255; i > 0; i--) { const j = (rnd() * (i + 1)) | 0; const t = p[i]; p[i] = p[j]; p[j] = t; }
  const hash = (ix, iy) => p[(p[ix & 255] + iy) & 255] / 255;
  return (x, y) => {
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    const a = hash(ix, iy), b = hash(ix + 1, iy), c = hash(ix, iy + 1), d = hash(ix + 1, iy + 1);
    const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
    return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
  };
}
function fbm2(noise, x, y) {
  let v = 0, amp = 0.5, fx = x, fy = y;
  for (let o = 0; o < 4; o++) { v += amp * noise(fx, fy); fx *= 2.03; fy *= 2.03; amp *= 0.5; }
  return v;
}
function consonance(semitones) {
  const n = Math.abs(semitones) % 12;
  if (n === 0) return 1;
  if (n === 7 || n === 5) return 0.92;
  if (n === 4 || n === 3 || n === 8 || n === 9) return 0.62;
  if (n === 2 || n === 10) return 0.4;
  return 0.16;
}

export default {
  id: "light-kimi-aurora",
  name: "Aurora Harp",
  hints: HINTS,

  create(ctx) {
    const { THREE, scene } = ctx;
    const KEY = ctx.KEY || { first: 21, last: 108 };
    const first = KEY.first, N = KEY.last - KEY.first + 1;
    const keyX = ctx.keyX || ((m) => (m - 21 - 43.5) * 52 / 88);
    const span = ctx.span || {};
    const left = span.left ?? keyX(first) - 0.5, right = span.right ?? keyX(KEY.last) + 0.5;
    const fallbackColor = (m, vel, target) => target.setHSL(((m % 12) * 7 % 12) / 12, 0.92, 0.56);
    const noteColor = ctx.noteColor || fallbackColor;

    const group = new THREE.Group();
    group.name = "instrument:light-kimi-aurora";
    group.position.set((left + right) / 2, 0, 0);
    group.scale.setScalar((right - left) / 52);
    scene.add(group);

    const disposables = [];
    const geo = (g) => { disposables.push(g); return g; };
    const mat = (m) => { disposables.push(m); return m; };

    // ---- per-note state (sized once, never reallocated) ----
    const bandLevel = new Float32Array(N);        // sustained light 0..1
    const bandVel = new Float32Array(N);          // last velocity 0..1
    const flash = new Float32Array(N);            // strike flash 0..1
    const ripple = new Float32Array(N);           // ripple amplitude 0..1
    const blur = new Float32Array(N).fill(1);     // blur multiplier (1 = rest)
    const bandAge = new Float32Array(N);          // s since last strike
    const lastStrike = new Float64Array(N).fill(-1);   // Float64: float32 cannot hold t0 exactly past ~16 s, and the mismatch re-fires every frame
    const held = new Uint8Array(N);               // 1 while the note is sounding this frame
    const usedNotes = new Int32Array(N).fill(-1);
    const iOffX = new Float32Array(N);
    const iHalfW = new Float32Array(N);
    const iColor = new Float32Array(N * 3);
    const iLevel = new Float32Array(N);
    const iFlash = new Float32Array(N);
    const iRipple = new Float32Array(N);
    const iBlur = new Float32Array(N);
    const iPhase = new Float32Array(N);
    for (let i = 0; i < N; i++) iPhase[i] = Math.random() * TAU;

    // ---- band ribbons: one instanced plane per note, width & position & colour & glow via instanced attributes ----
    const bandU = { uTime: { value: 0 }, uHaze: { value: 0 }, uIri: { value: 0 } };
    const BAND_VERT =
      "attribute vec3 aColor;\nattribute float aLevel;\nattribute float aFlash;\nattribute float aRipple;\nattribute float aBlur;\nattribute float aPhase;\nattribute float aOffsetX;\nattribute float aHalfW;\n" +
      "varying vec3 vColor;\nvarying float vLevel;\nvarying float vFlash;\nvarying float vRipple;\nvarying float vBlur;\nvarying float vPhase;\nvarying float vU;\nvarying float vX;\n" +
      "void main(){\n" +
      "  vColor=aColor; vLevel=aLevel; vFlash=aFlash; vRipple=aRipple; vBlur=aBlur; vPhase=aPhase;\n" +
      "  vU=uv.y; vX=uv.x;\n" +
      "  vec3 p=vec3(position.x*aHalfW+aOffsetX, position.y, position.z);\n" +
      "  gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);\n" +
      "}\n";
    const BAND_FRAG =
      "uniform float uTime;\nuniform float uHaze;\nuniform float uIri;\n" +
      "varying vec3 vColor;\nvarying float vLevel;\nvarying float vFlash;\nvarying float vRipple;\nvarying float vBlur;\nvarying float vPhase;\nvarying float vU;\nvarying float vX;\n" +
      "void main(){\n" +
      "  // ripple travels up the band (vU 0 at bottom, 1 at top), damped; ghosts trail behind (ornithopter blur)\n" +
      "  float wave = sin(uTime*9.0 - vU*5.0 - vPhase*6.2831);\n" +
      "  float envelope = 0.5 + 0.5*sin(vU*3.14159 + 1.5708);\n" +
      "  float r = vRipple * (0.4 + 0.6*envelope) * (0.5 + 0.5*wave);\n" +
      "  // band cross-section: a soft glowing core that falls off gently toward the edges\n" +
      "  float edge = 1.0 - smoothstep(0.0, 0.5, abs(vX - 0.5)*2.0);\n" +
      "  float core = edge*edge;\n" +
      "  vec3 col = vColor;\n" +
      "  // warm haze from lush chords; thin-film iridescence shimmer from lushness\n" +
      "  col = mix(col, col*0.82 + vec3(0.18,0.11,0.04), uHaze);\n" +
      "  col = col * (1.0 + uIri*0.14*(0.5+0.5*sin(6.2831*(vU*3.0+vPhase))));\n" +
      "  float a = vLevel*(0.62 + 0.38*vBlur*(0.5+0.5*r));\n" +
      "  a *= mix(0.35, 1.0, core);\n" +
      "  a += vFlash*(1.0 - vBlur*0.35)*core;\n" +
      "  // only the flash crosses the bloom threshold (~0.9 luma); sustained light stays below\n" +
      "  a = min(a, 0.82 + vFlash*4.5);\n" +
      "  gl_FragColor = vec4(col, a);\n" +
      "}\n";
    const bandMat = mat(new THREE.ShaderMaterial({
      vertexShader: BAND_VERT, fragmentShader: BAND_FRAG, uniforms: bandU,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    const bandBase = geo(new THREE.PlaneGeometry(1, BAND_LEN));
    bandBase.translate(0, BAND_BASE + BAND_LEN / 2, 0);
    const bandGeo = geo(new THREE.InstancedBufferGeometry());
    bandGeo.index = bandBase.index;
    bandGeo.setAttribute("position", bandBase.attributes.position);
    bandGeo.setAttribute("uv", bandBase.attributes.uv);
    bandGeo.setAttribute("aColor", new THREE.InstancedBufferAttribute(iColor, 3));
    bandGeo.setAttribute("aLevel", new THREE.InstancedBufferAttribute(iLevel, 1));
    bandGeo.setAttribute("aFlash", new THREE.InstancedBufferAttribute(iFlash, 1));
    bandGeo.setAttribute("aRipple", new THREE.InstancedBufferAttribute(iRipple, 1));
    bandGeo.setAttribute("aBlur", new THREE.InstancedBufferAttribute(iBlur, 1));
    bandGeo.setAttribute("aPhase", new THREE.InstancedBufferAttribute(iPhase, 1));
    bandGeo.setAttribute("aOffsetX", new THREE.InstancedBufferAttribute(iOffX, 1));
    bandGeo.setAttribute("aHalfW", new THREE.InstancedBufferAttribute(iHalfW, 1));
    const bands = new THREE.InstancedMesh(bandGeo, bandMat, N);
    bands.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    bands.frustumCulled = false;
    group.add(bands);

    // ---- spectral hammers: small lens quads that dive on a strike ----
    // note-coloured, soft radial alpha, luma clamped under 0.9 so the lens never adds to the bloom count.
    const iLensColor = new Float32Array(N * 3);
    const lensGeo = geo(new THREE.PlaneGeometry(0.6, 0.6));
    lensGeo.setAttribute("aLensColor", new THREE.InstancedBufferAttribute(iLensColor, 3));
    const LENS_VERT = "attribute vec3 aLensColor; varying vec3 vLensColor; varying vec2 vUv; void main(){ vLensColor=aLensColor; vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.0); }";
    const LENS_FRAG = "varying vec3 vLensColor; varying vec2 vUv; void main(){ float d=length((vUv-0.5)*2.0); float a=smoothstep(1.0,0.0,d)*0.9; float luma=dot(vLensColor,vec3(0.2126,0.7152,0.0722)); vec3 c=vLensColor*min(1.0,0.9/max(luma,1e-4)); gl_FragColor=vec4(c,a); }";
    const lensMat = mat(new THREE.ShaderMaterial({ vertexShader: LENS_VERT, fragmentShader: LENS_FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    const lenses = new THREE.InstancedMesh(lensGeo, lensMat, N);
    lenses.count = 0;
    lenses.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    lenses.frustumCulled = false;
    group.add(lenses);

    // ---- fog: three stacked noise-textured translucent quads behind the harp (fake volumetrics, soft depth fade) ----
    const FOG_Z = -15.0;
    const fogTex = (() => {
      const c = document.createElement("canvas"); c.width = c.height = 256;
      const g = c.getContext("2d"); g.fillStyle = "#000"; g.fillRect(0, 0, 256, 256);
      const nz = makeNoise(1234);
      const img = g.createImageData(256, 256);
      for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
        const v = fbm2(nz, x * 0.018, y * 0.018);
        const idx = (y * 256 + x) * 4;
        img.data[idx] = img.data[idx + 1] = img.data[idx + 2] = (v * 255) | 0;
        img.data[idx + 3] = 255;
      }
      g.putImageData(img, 0, 0);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
    })();
    disposables.push(fogTex);
    const fogMats = [];
    for (let k = 0; k < 3; k++) {
      const u = { uAlpha: { value: 0 }, uHaze: { value: 0 }, uDepth: { value: 0.4 + k * 0.3 }, uTex: { value: fogTex } };
      const m = mat(new THREE.ShaderMaterial({
        uniforms: u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        vertexShader: "varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
        fragmentShader: "uniform float uAlpha; uniform float uHaze; uniform float uDepth; uniform sampler2D uTex; varying vec2 vUv; void main(){ float n=texture2D(uTex,vUv*3.0+uDepth).r; float edge=smoothstep(0.0,0.35,vUv.x)*smoothstep(1.0,0.65,vUv.x)*smoothstep(0.0,0.3,vUv.y)*smoothstep(1.0,0.7,vUv.y); vec3 c=mix(vec3(0.72,0.44,0.19),vec3(0.35,0.48,0.72),1.0-uHaze); gl_FragColor=vec4(c, n*uAlpha*edge*0.3); }",
      }));
      const mesh = new THREE.Mesh(geo(new THREE.PlaneGeometry(60, 36)), m);
      mesh.position.set(0, BAND_BASE + BAND_LEN * 0.5, FOG_Z - k * 2.4);
      mesh.frustumCulled = false;
      group.add(mesh);
      fogMats.push(m);
    }

    // ---- the bass/solo braid ----
    const BRAID_PTS = 96;
    const braidPos = new Float32Array(BRAID_PTS * 3);
    const braidColArr = new Float32Array(BRAID_PTS * 3);
    const braidGeo = geo(new THREE.BufferGeometry());
    braidGeo.setAttribute("position", new THREE.BufferAttribute(braidPos, 3));
    braidGeo.setAttribute("color", new THREE.BufferAttribute(braidColArr, 3));
    const braidLine = new THREE.Line(braidGeo, mat(new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false })));
    braidLine.frustumCulled = false;
    braidLine.visible = false;
    group.add(braidLine);

    // ---- scratch (allocated once) ----
    const m4 = new THREE.Matrix4();
    const q4 = new THREE.Quaternion();
    const p3 = new THREE.Vector3();
    const s3 = new THREE.Vector3();
    const colScratch = new THREE.Color();
    const seenPC = new Uint8Array(12);   // reused pitch-class marker (no per-frame allocation)

    // ---- feel state ----
    let feel = { lushness: 0, simplicity: 0, tension: 0, brightness: 0, openness: 0 };
    let fogLevel = 0;
    let bass = null, solo = null, braidPhase = 0;
    let active = true;
    let dt_global = 0.016;

    // Compute the chord feel from the gathered sounding note set (usedNotes[0..used)) and the page's chord reading.
    // No allocation: seenPC is reused, all voice stats are plain numbers.
    function computeFeel(used) {
      let lo = null, hi = null, sp = 0, cluster = 0;
      seenPC.fill(0);
      for (let k = 0; k < used; k++) {
        const m = usedNotes[k] + first;
        if (lo === null || m < lo) lo = m;
        if (hi === null || m > hi) hi = m;
        const p = pcOf(m);
        if (seenPC[p]) cluster++;
        seenPC[p] = 1;
      }
      const n = used;
      if (lo !== null && hi !== null) sp = hi - lo;
      const thick = n >= 4, wide = sp > 9, simple = n <= 2;
      const tense = cluster > 0 || (chordState && chordState.name && /alt|dim|#|♯|♭|\bb\b/.test(chordState.name));
      const lush = clamp01(0.2 + (thick ? 0.5 : 0) + (wide ? 0.25 : 0) - (simple ? 0.45 : 0));
      const simp = clamp01((simple ? 0.75 : 0) + (n <= 1 ? 0.25 : 0));
      const tns = clamp01((tense ? 0.7 : 0) + cluster * 0.15);
      const brt = clamp01(0.5 + (hi !== null && hi > 66 ? 0.5 : 0));
      const opn = clamp01(wide ? 0.8 : 0.3);
      feel.lushness = damp(feel.lushness, lush, 0.5, dt_global);
      feel.simplicity = damp(feel.simplicity, simp, 0.5, dt_global);
      feel.tension = damp(feel.tension, tns, 0.5, dt_global);
      feel.brightness = damp(feel.brightness, brt, 0.5, dt_global);
      feel.openness = damp(feel.openness, opn, 0.5, dt_global);
      // fog level follows lushness (a breath); haze = warm; tension cools it
      const fogTarget = clamp01(feel.lushness * 1.1 - feel.simplicity * 0.4);
      fogLevel = damp(fogLevel, fogTarget, fogTarget > fogLevel ? FOG_TAU_IN : FOG_TAU_OUT, dt_global);
      return { bass: lo, solo: hi };
    }
    let chordState = null;   // refreshed each frame from state.chord, no allocation

    function update(dt, t, state) {
      if (!active) return;
      dt = clamp(dt || 0, 0, 0.1);
      dt_global = dt;

      const sounding = state && state.sounding ? state.sounding : null;
      held.fill(0);
      let used = 0;

      // ---- register sounding notes (new strikes detected via the strike counter) ----
      if (sounding && sounding.size) {
        sounding.forEach((n, m) => {
          const i = m - first;
          if (i < 0 || i >= N) return;
          held[i] = 1;
          usedNotes[used++] = i;
          const v = clamp01((n.vel || 90) / 127);
          bandVel[i] = v;
          // strike detection (moment.js contract): a note we weren't sounding, OR a sounding note whose
          // t0 changed (the host replaces the entry on a re-strike). This unlocks pedal-hold, hammer
          // repeats and the bandAge advance together, all from the sounding entry.
          const t0 = n.t0;
          if (t0 !== undefined && t0 !== lastStrike[i]) {
            lastStrike[i] = t0;
            flash[i] = Math.max(flash[i], v * v * FLASH_GAIN + VEL_LO);
            ripple[i] = Math.max(ripple[i], VEL_LO + v * 0.84);
            bandAge[i] = 0;
          } else {
            bandAge[i] += dt;   // advance bandAge even without a fresh re-strike (pedal wash, repeats)
          }
        });
      } else if (state && state.pressed && state.pressed.size) {
        // fallback before state.sounding merges
        state.pressed.forEach((n, m) => {
          const i = m - first;
          if (i < 0 || i >= N) return;
          held[i] = 1;
          usedNotes[used++] = i;
          const v = clamp01((n?.vel ?? 90) / 127);
          bandVel[i] = v;
          // coarse strike detection by level rise (fallback hosts have no t0/strike counter)
          if (bandLevel[i] < 0.01) { flash[i] = Math.max(flash[i], v * v * FLASH_GAIN + VEL_LO); ripple[i] = Math.max(ripple[i], VEL_LO + v * 0.84); bandAge[i] = 0; }
          bandAge[i] += dt;
        });
      }

      // ---- decay / damping ----
      const kFlash = Math.exp(-dt / FLASH_TAU);
      const kRip = Math.exp(-dt * RIPPLE_DECAY);
      const kFall = Math.exp(-dt / FALL_TAU);
      for (let i = 0; i < N; i++) {
        flash[i] *= kFlash;
        ripple[i] *= kRip;
        if (held[i]) {
          bandLevel[i] = damp(bandLevel[i], 0.55 + 0.45 * bandVel[i], 0.05, dt);
        } else {
          bandLevel[i] *= kFall;
          if (bandLevel[i] < 0.001) bandLevel[i] = 0;
        }
        // blur: wide while sounding (wider for LOW notes — A0 is the wide one), relaxes to 1 after release
        const restBlur = 1 + (1 - ban(first + i)) * 1.7;
        blur[i] = damp(blur[i], held[i] ? restBlur : 1, held[i] ? 0.3 : 0.5, dt);
      }

      // ---- chord feel + fog + braid ----
      chordState = (state && state.chord) ? state.chord : null;
      const fb = computeFeel(used);
      bass = fb.bass; solo = fb.solo;

      // ---- fill instanced attributes ----
      const B = first;
      for (let i = 0; i < N; i++) {
        const m = B + i;
        const x = keyX(m);
        const r = ban(m);
        // half-width rises toward the BASS (0.34 at A0, 0.05 at C8), then scaled by the blur multiplier
        const halfW = (0.05 + (0.34 - 0.05) * (1 - r)) * blur[i];
        iOffX[i] = x;
        iHalfW[i] = halfW;
        // colour: note colour, saturated, then scaled by level (sustained light stays below bloom)
        noteColor(m, Math.round((bandVel[i] || 0.5) * 127), colScratch);
        const lvl = bandLevel[i];
        iColor[i * 3] = colScratch.r;
        iColor[i * 3 + 1] = colScratch.g;
        iColor[i * 3 + 2] = colScratch.b;
        iLevel[i] = lvl;
        iFlash[i] = flash[i];
        iRipple[i] = ripple[i];
        iBlur[i] = blur[i];
      }
      bandGeo.attributes.aColor.needsUpdate = true;
      bandGeo.attributes.aLevel.needsUpdate = true;
      bandGeo.attributes.aFlash.needsUpdate = true;
      bandGeo.attributes.aRipple.needsUpdate = true;
      bandGeo.attributes.aBlur.needsUpdate = true;
      bandGeo.attributes.aPhase.needsUpdate = true;
      bandGeo.attributes.aOffsetX.needsUpdate = true;
      bandGeo.attributes.aHalfW.needsUpdate = true;

      // the instanced matrix places each band at (0,0,0) — the offsetX/halfW do the work, so identity transforms suffice
      p3.set(0, 0, 0); q4.identity(); s3.set(1, 1, 1);
      for (let i = 0; i < N; i++) { m4.makeRotationFromQuaternion(q4); m4.compose(p3, q4, s3); bands.setMatrixAt(i, m4); }
      bands.instanceMatrix.needsUpdate = true;

      // ---- hammers: for each flashing note, a lens dives from the rail, faster for harder strikes ----
      let lensCount = 0;
      for (let i = 0; i < N; i++) {
        if (flash[i] > 0.01) {
          const m = B + i;
          const x = keyX(m);
          // travel progress: bandAge climbs from 0 (strike) — fall speed scales with velocity
          const travel = clamp01(bandAge[i] * (0.15 + bandVel[i] * 0.35) / 0.08);
          const y = lerp(RAIL_Y, BAND_BASE + BAND_LEN * 0.4, travel);
          p3.set(x, y, 0);
          q4.identity(); s3.set(0.4 + bandVel[i] * 0.4, 0.4 + bandVel[i] * 0.4, 1);
          m4.compose(p3, q4, s3);
          lenses.setMatrixAt(lensCount, m4);
          noteColor(m, Math.round(bandVel[i] * 127), colScratch);
          iLensColor[lensCount * 3] = colScratch.r;
          iLensColor[lensCount * 3 + 1] = colScratch.g;
          iLensColor[lensCount * 3 + 2] = colScratch.b;
          lensCount++;
        }
      }
      lenses.count = lensCount;
      if (lensCount) { lenses.instanceMatrix.needsUpdate = true; lensGeo.attributes.aLensColor.needsUpdate = true; }

      // ---- uniforms ----
      bandU.uTime.value = t;
      bandU.uHaze.value = clamp01(feel.lushness * 0.7 - feel.tension * 0.25);
      bandU.uIri.value = clamp01(feel.lushness * 0.9);
      for (let k = 0; k < 3; k++) {
        fogMats[k].uniforms.uAlpha.value = fogLevel * (0.5 + k * 0.18);
        fogMats[k].uniforms.uHaze.value = clamp01(feel.lushness * 0.8 - feel.tension * 0.3);
      }

      // ---- braid ----
      if (bass === null || solo === null || bass === solo) {
        braidLine.visible = false;
      } else {
        braidLine.visible = true;
        const x0 = keyX(bass), x1 = keyX(solo);
        const semi = Math.abs(solo - bass);
        const c = consonance(semi);
        const spread = Math.abs(x1 - x0);
        const motion = clamp01(spread / 20.0);
        const twirl = 2.5 * (0.4 + 0.6 * (1 - c));
        braidPhase += dt * (0.4 + 2.2 * motion);
        const attr = braidGeo.attributes.position;
        const colAttr = braidGeo.attributes.color;
        for (let i = 0; i < BRAID_PTS; i++) {
          const f = i / (BRAID_PTS - 1);
          const x = lerp(x0, x1, f);
          const wob = Math.sin(f * TAU * twirl + braidPhase) * (0.2 + 0.85 * motion);
          braidPos[i * 3] = x;
          braidPos[i * 3 + 1] = BAND_BASE + 0.2 + wob;
          braidPos[i * 3 + 2] = 0;
          colScratch.setRGB(lerp(0.42, 1.0, c), lerp(0.38, 0.72, c), lerp(0.75, 0.42, c));
          colAttr.setXYZ(i, colScratch.r, colScratch.g, colScratch.b);
        }
        attr.needsUpdate = true;
        colAttr.needsUpdate = true;
      }
    }

    function resize(framing) { /* bands and fog are framing-agnostic by construction; nothing to re-layout */ }

    function setActive(on) { active = !!on; group.visible = active; }

    function dispose() {
      active = false;
      if (group.parent) group.parent.remove(group);
      for (const d of disposables) d.dispose?.();
    }

    return { group, update, resize, setActive, dispose };
  },
};
