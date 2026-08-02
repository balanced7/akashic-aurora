// aurora-shader.js — Aurora Glass "shock factor" background (claude's lane)
//
// A single full-viewport WebGL2 canvas that renders a slow, flowing aurora curtain as the
// cockpit's animated light bed. The DOM/glass sits ON TOP and simply reads this light — the UI
// never goes through WebGL, so it stays responsive and the shader is independently throttleable.
//
// Settled spec: docs/ui-plan-synthesis.md. Built on DeepSeek's GLSL draft (ui-plan-deepseek.md),
// with claude's changes: (1) higher-quality gradient noise in place of the value-noise placeholder
// [swap-benchmarked per the plan; invariants are the FBM loop + domain warp + blackbody LUT, not
// the noise fn]; (2) center-dark envelope (aurora lives in the top/margins, never behind body text);
// (3) blackbody-temperature colour LUT; (4) the locked interface contract: setState(0|1|2).
//
// INTERFACE CONTRACT (synthesis §2a — do not break):
//   const a = new AuroraShader(canvasEl); a.start();
//   a.setState(0 | 1 | 2)  // 0=normal, 1=paused (amber tint), 2=halted (desaturate+darken)
// The status layer (DeepSeek's applyStatus) owns WHEN to switch; the shader owns the visual.
// Neither side reaches across the seam.
//
// Fail-safe: if WebGL2 is unavailable or prefers-reduced-motion is set, callers should skip
// construction and keep the CSS gradient fallback. isSupported() is provided for that gate.

(function (global) {
  'use strict';

  // --- SWARMS + VOLUME ------------------------------------------------------------------------
  // Three swarms of six. NPT is what the march loops over per step, so it is the single number
  // that sets the cost of everything: STEPS x NPT is the inner product of this whole shader.
  const SWARMS = 3, PER_SWARM = 6, NPT = SWARMS * PER_SWARM;
  const TRAILP = 6, TRAIL_DT = 0.13;
  // March parameters. STEPS x MARCH_DT must span the depth the swarms actually occupy or the
  // volume clips them; CAMZ 3.6 with a 0.30 start and 26 x 0.20 of march covers z in -3.3..+1.9,
  // and the swarms live inside +/-2.6.
  const STEPS = 26, MARCH_DT = 0.20, SIGMA = 3.2, CAMZ = 3.6, FOCAL = 1.35;

  // SWARM IDENTITY. Two cool and one warm, which is a deliberate reading of what makes the
  // tunnel shader's colour work: it opposes vec4(1e1,2,1) against vec4(1,2,1e1) -- warm against
  // cool -- rather than sweeping a wide hue range. Two periwinkle-violet swarms against one
  // coral gives that opposition while staying inside the design system, because coral is already
  // the identity accent and not a fourth invented hue. It is used at lower brightness so it
  // reads as an accent among the cool rather than as a competing subject.
  const SWARM_COL = [
    [0.48, 0.64, 0.97],   // #7aa2f7 periwinkle
    [0.62, 0.49, 0.97],   // #9d7cf7 violet
    [0.97, 0.52, 0.42]    // coral, the warm minority
  ];
  const SWARM_GAIN = [1.0, 0.92, 0.45];

  function frac(x) { return x - Math.floor(x); }

  // Per-particle constants. Each particle orbits its swarm's centre at its own radius, rate and
  // phase, so the swarm holds together as a body while no two members trace the same figure --
  // which is what separates a flock from a rigid constellation being flown around.
  const PT = (function () {
    const out = [];
    for (let s = 0; s < SWARMS; s++) {
      for (let k = 0; k < PER_SWARM; k++) {
        const i = s * PER_SWARM + k;
        const h1 = frac(Math.sin((i + 1) * 12.9898) * 43758.5453);
        const h2 = frac(Math.sin((i + 1) * 78.2330) * 22578.1459);
        const h3 = frac(Math.sin((i + 1) * 39.4250) * 19349.1170);
        out.push({
          swarm: s,
          rad:   0.30 + h1 * 0.30,
          rate:  0.62 + h2 * 0.70,
          phase: (k / PER_SWARM) * 6.2831 + h3 * 1.4,
          tilt:  1.3 + h3 * 1.1,           // vertical orbit rate: the altitude spread within a swarm
          bright: 0.55 + h2 * 0.55
        });
      }
    }
    return out;
  })();

  // --- GLSL -----------------------------------------------------------------------------------
  // Fullscreen triangle: no vertex buffer, positions synthesized from gl_VertexID.
  const VERT = `#version 300 es
  void main() {
    // 3 verts covering the viewport (the classic oversized triangle)
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
  }`;

  const FRAG = `#version 300 es
  precision highp float;
  out vec4 outColor;

  uniform vec2  u_resolution;
  uniform float u_time;
  uniform int   u_state;            // 0 normal, 1 paused, 2 halted
  uniform float u_state_intensity;  // 0..1 lerp on state change
  uniform float u_speed;            // motion multiplier (Shader Park: live-tunable param)
  uniform float u_intensity;        // brightness multiplier (live-tunable param)

  // --- gradient (Perlin-style) value-of-gradients noise: smoother than hash value-noise,
  //     textureless, GPU-stable. This is claude's swap-in candidate vs DeepSeek's hash noise. ---
  vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }
  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);          // smoothstep interpolation
    float a = dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0));
    float b = dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0));
    float c = dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0));
    float d = dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0));
    return 0.5 + 0.5 * mix(mix(a, b, u.x), mix(c, d, u.x), u.y);   // -> 0..1
  }

  // FBM — 4 octaves (INVARIANT: octave loop, lacunarity 2, gain 0.5)
  float fbm(vec2 p) {
    float value = 0.0, amp = 0.5, freq = 1.0;
    for (int i = 0; i < 4; i++) {
      value += amp * noise(p * freq);
      freq *= 2.0;
      amp  *= 0.5;
    }
    return value;
  }

  // Blackbody-ish temperature LUT (INVARIANT). t in 0..1 -> aurora colour, fading to void at both
  // ends. Palette keys from the synthesis: teal(deepseek) -> aurora green -> edge violet.
  vec3 auroraColor(float t) {
    // PALETTE: cool indigo -> periwinkle -> soft violet. Analogous, not a rainbow.
    //
    // WHY THE OLD ONE READ AS DATED (Daniil: "ugly and not modern"): it ran teal -> #48e6bf neon
    // green -> violet, which is three hues spanning ~180 degrees. A wide multi-hue sweep at high
    // saturation is the 2018 gradient-mesh look. Modern dark surfaces use an ANALOGOUS set --
    // neighbours on the wheel -- at lower saturation and higher luminance range, so the light
    // reads as one light source rather than four.
    //
    // These are the palette's OWN hues, not a new invention: #7aa2f7 and #9d7cf7 are the
    // deepseek identity pair already in design/refs/aurora-glass-tokens.css. The background now
    // harmonises with the identity colours instead of competing with them, which is also why the
    // coral claude avatars will finally read as an accent -- they are the only warm thing on
    // screen instead of one warm thing among four.
    vec3 deep   = vec3(0.04, 0.05, 0.13);   // near-black indigo, the floor
    vec3 indigo = vec3(0.22, 0.28, 0.62);
    vec3 peri   = vec3(0.48, 0.64, 0.97);   // #7aa2f7
    vec3 violet = vec3(0.62, 0.49, 0.97);   // #9d7cf7
    if (t < 0.30) return mix(vec3(0.0), deep,   t / 0.30);
    if (t < 0.52) return mix(deep,   indigo, (t - 0.30) / 0.22);
    if (t < 0.74) return mix(indigo, peri,   (t - 0.52) / 0.22);
    if (t < 0.88) return mix(peri,   violet, (t - 0.74) / 0.14);
    return mix(violet, vec3(0.0), (t - 0.88) / 0.12);
  }

  // ===================== SWARMS IN FOG =====================
  // Daniil's brief: "multiple swarms of particles with trails... use the fog shader as they
  // move... the background to be black and to have this fog be something the particles traverse
  // and displace." Expense explicitly accepted, spectacle explicitly requested.
  //
  // THE ARCHITECTURAL CALL, and it is what makes this affordable at all: the dancing-man shader
  // gets its look from a post chain -- LittleBloom, LittleGlow, RadialBlur -- each a separate
  // buffer pass. Every one of those is a FAKE OF LIGHT SCATTERING THROUGH A MEDIUM. Marching an
  // actual participating medium produces all three natively and in a single pass: bloom is
  // in-scattering near a source, god rays are in-scattering along the view ray, and the radial
  // streak is what a bright emitter does to fog behind it. Simulating the cause is cheaper here
  // than approximating three of its symptoms, and it cannot disagree with itself.
  uniform vec4 u_pt[NPT];        // xyz world position, w brightness
  uniform vec3 u_ptc[NPT];       // emitter colour (swarm identity)
  uniform vec4 u_tr[NTR];        // xy projected screen pos, z depth, w particle index

  // IQ's textureless value noise (Rainforest, shadertoy 4ttSWf) -- the same one the Christopher
  // Wallis fog shader uses, chosen because it has to be evaluated once per march step and a
  // texture fetch per step would dominate everything else.
  float hash1(float n) { return fract(n * 17.0 * fract(n * 0.3183099)); }
  float vnoise(vec3 x) {
    vec3 p = floor(x), w = fract(x);
    vec3 u = w * w * w * (w * (w * 6.0 - 15.0) + 10.0);
    float n = p.x + 317.0 * p.y + 157.0 * p.z;
    float a = hash1(n +   0.0), b = hash1(n +   1.0), c = hash1(n + 317.0), d = hash1(n + 318.0);
    float e = hash1(n + 157.0), f = hash1(n + 158.0), g = hash1(n + 474.0), h = hash1(n + 475.0);
    float k0 = a, k1 = b - a, k2 = c - a, k3 = e - a, k4 = a - b - c + d;
    float k5 = a - c - e + g, k6 = a - b - e + f, k7 = -a + b + c - d + e - f - g + h;
    return -1.0 + 2.0 * (k0 + k1*u.x + k2*u.y + k3*u.z + k4*u.x*u.y
                       + k5*u.y*u.z + k6*u.z*u.x + k7*u.x*u.y*u.z);
  }
  // Two octaves, not four. The march samples this STEPS times per pixel, so an octave here costs
  // as much as everything outside the loop put together; the third and fourth would add detail
  // finer than a fog bank has any business showing.
  float fbm2(vec3 p) { return 0.62 * vnoise(p) + 0.30 * vnoise(p * 2.03 + 11.7); }

  float segDist(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h);
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float aspect = u_resolution.x / u_resolution.y;
    vec2 sc = (uv - 0.5) * vec2(aspect, 1.0);
    float T = u_time * u_speed;

    vec3 ro = vec3(0.0, 0.0, -CAMZ);
    vec3 rd = normalize(vec3(sc, 1.35));

    // STATIC per-pixel jitter, and this is what lets the film grain go. The fog shader Daniil
    // pasted jitters its march with hash12(fragCoord + iTime) to break the banding that fixed
    // step marching always produces -- but jitter that varies per FRAME is, precisely, crawling
    // film grain, which is the thing he asked me to remove. A jitter fixed per pixel breaks the
    // banding exactly as well and does not shimmer, so the separate grain term is gone entirely
    // rather than merely turned down.
    float jit = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);

    float trans = 1.0;              // transmittance along the view ray (Beer-Lambert)
    vec3  scat  = vec3(0.0);        // accumulated in-scattered light
    float t = 0.30 + jit * MARCH_DT;

    for (int i = 0; i < STEPS; i++) {
      vec3 p = ro + rd * t;

      // The medium: drifting noise with a height falloff, so it reads as a bank the swarms fly
      // through rather than a uniform haze filling the room.
      float dens = fbm2(p * 0.62 + vec3(0.0, -T * 0.05, T * 0.03));
      // THRESHOLD HIGH, and this is the difference between fog and haze. fbm2 spans about
      // +/-0.92, so a low floor here admits half the volume as medium and every ray accumulates
      // something everywhere -- measured as 46% of the screen lit and a median pixel at 9/255,
      // when the brief was a BLACK background. Taking only the top of the noise range leaves
      // sparse banks with genuine emptiness between them, which is what lets a swarm fly out of
      // the dark into a lit cloud instead of swimming through uniform soup.
      dens = smoothstep(0.34, 0.90, dens) * exp(-abs(p.y) * 0.45);

      // ONE PASS OVER THE EMITTERS SERVES BOTH JOBS, because both want the same squared
      // distance: how brightly this particle lights the medium here, and how much it has pushed
      // the medium OUT of here. Computing r2 once makes "particles displace the fog they light"
      // very nearly free -- and, better, physically coherent: the particle shoulders the medium
      // aside and then illuminates the cavity it just made, so the wake is visible as a lit
      // hollow rather than as an absence. That coupling is the whole effect Daniil asked for.
      vec3 lit = vec3(0.0);
      float carve = 1.0;
      for (int j = 0; j < NPT; j++) {
        vec3 dv = u_pt[j].xyz - p;
        float r2 = dot(dv, dv);
        // Inverse-square, softened at r=0, and the coefficient is deliberately steep: eighteen
        // emitters all contributing a long tail is how a swarm turns into a floodlight. Tight
        // falloff keeps each particle a lamp with a reach rather than an ambient source.
        lit += u_ptc[j] * (u_pt[j].w / (0.04 + r2 * 4.2));
        carve *= 1.0 - 0.82 * exp(-r2 * 5.5);                // the wake
      }
      dens *= carve;

      float a = dens * MARCH_DT * SIGMA;
      if (a > 0.0004) {
        scat  += trans * a * lit;
        trans *= exp(-a);
      }
      t += MARCH_DT;
      if (trans < 0.02) break;     // saturated: nothing behind this can matter
    }

    vec3 col = scat;

    // ---- TRAILS ----
    // Kept OUT of the march deliberately. Lighting the volume from every trail point would be
    // STEPS x NPT x TRAILP evaluations, an order of magnitude more than the heads alone, for a
    // contribution the fog glow already implies. Drawn analytically in screen space instead and
    // attenuated by the transmittance the march measured, so fog still occludes them.
    //
    // THINNER, as asked: the width constant is 0.014 against the previous 0.030, and the
    // inverse-square falloff means halving the width does not merely thin the line, it tightens
    // its halo by a factor of four.
    vec3 lines = vec3(0.0);
    for (int i = 0; i < NPT; i++) {
      vec3 fc = u_ptc[i];
      for (int k = 0; k < SEGN; k++) {
        vec4 a = u_tr[i * TRAILP + k];
        vec4 b = u_tr[i * TRAILP + k + 1];
        float d = segDist(sc, a.xy, b.xy);
        float depth = 0.5 * (a.z + b.z);
        float w = 0.014 / depth;
        float fade = 1.0 - float(k) / float(SEGN);
        float g = w / (d + w * 0.45);
        lines += fc * (g * g * 2.6) * fade * fade;
      }
    }
    col += lines * mix(0.22, 1.0, trans);

    // ---- STATE TINT ----
    // Modulated by what is actually lit, so the wash lands on the scene rather than flooding a
    // black frame -- the reason this needs a magnitude at all.
    float mag = clamp(dot(col, vec3(0.6)), 0.0, 1.0);
    if (u_state == 1) {
      col = mix(col, vec3(0.94, 0.70, 0.27) * mag, u_state_intensity * 0.4);
    } else if (u_state == 2) {
      col = mix(col, vec3(dot(col, vec3(0.299, 0.587, 0.114))) * 0.3, u_state_intensity * 0.7);
    }

    col *= u_intensity;

    // Superlinear highlight, then the tanh shoulder. Order matters: tanh must be LAST of the two
    // or the highlight re-expands what the shoulder just compressed.
    col += col * col * 0.85;
    col = tanh(col);

    // Aspect-corrected cubic vignette, normalised by the ACTUAL corner distance -- dividing by
    // the 0.7071 of a unit square would push the mid-side edges past 1.0 and black out the sides
    // of a widescreen display.
    vec2 vuv = uv;
    vuv.x = (vuv.x - 0.5) * aspect + 0.5;
    float vd = length(vuv - 0.5) / length(vec2(0.5 * aspect, 0.5));
    col *= mix(1.0, 1.0 - pow(clamp(vd * 0.94, 0.0, 1.0), 3.0), 0.60);

    // NO GRAIN TERM. The march jitter above already dithers the only gradients that band, and it
    // does so without animating. The background is black where nothing lights it, which is the
    // brief -- so there is deliberately no ambient, no base wash and no floor colour here.
    outColor = vec4(col, 1.0);
  }`
  // GLSL array sizes must be compile-time literals, so the counts are injected rather than
  // duplicated. Duplicating them invites silent corruption: raise a count in JS, forget the
  // shader, and the loop reads past the uploaded data into whatever the driver left in those
  // uniform slots -- which renders as stray geometry rather than as an error.
  .replace(/NPT/g,      String(NPT))
  .replace(/NTR/g,      String(NPT * TRAILP))
  .replace(/TRAILP/g,   String(TRAILP))
  .replace(/SEGN/g,     String(TRAILP - 1))
  .replace(/STEPS/g,    String(STEPS))
  .replace(/MARCH_DT/g, MARCH_DT.toFixed(3))
  .replace(/SIGMA/g,    SIGMA.toFixed(2))
  .replace(/CAMZ/g,     CAMZ.toFixed(2));

  // --- Driver ---------------------------------------------------------------------------------
  function isSupported() {
    if (typeof document === 'undefined') return false;
    try {
      if (global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return false;
      }
      return !!document.createElement('canvas').getContext('webgl2');
    } catch (e) {
      return false;
    }
  }

  class AuroraShader {
    constructor(canvas) {
      this.canvas = canvas;
      this.gl = canvas.getContext('webgl2', {
        alpha: false, antialias: false,
        powerPreference: 'low-power',      // don't wake the discrete GPU
        preserveDrawingBuffer: false,
      });
      if (!this.gl) throw new Error('webgl2 unavailable');
      this.state = 0;
      this.stateLerp = 1.0;                // 1 = fully at target
      this.speed = 1.0;                    // live-tunable params (Shader Park ethos); UI sliders call the setters
      this.intensity = 0.7;                // dark-first: aurora present in the top bands, not an overpowering wash
      this.startTime = (global.performance ? performance.now() : 0) / 1000;
      this.animating = false;
      this._frames = 0;                    // for the fps watchdog
      this._compile();
      this._resize();
      this._bind();
    }

    // INTERFACE CONTRACT — the only cross-seam control. 0=normal, 1=paused, 2=halted.
    setState(state) {
      state = state | 0;
      if (state !== this.state) { this.state = state; this.stateLerp = 0.0; }
    }

    // Live-tunable params (Shader Park inspiration) — the future settings-panel sliders call these.
    setSpeed(v) { this.speed = Math.max(0, +v || 0); }
    setIntensity(v) { this.intensity = Math.max(0, +v || 0); }

    _compile() {
      const gl = this.gl;
      const sh = (type, src) => {
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
          throw new Error('aurora shader compile: ' + gl.getShaderInfoLog(s));
        }
        return s;
      };
      const prog = gl.createProgram();
      gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        throw new Error('aurora link: ' + gl.getProgramInfoLog(prog));
      }
      gl.useProgram(prog);
      this.prog = prog;
      this.u_resolution = gl.getUniformLocation(prog, 'u_resolution');
      this.u_time = gl.getUniformLocation(prog, 'u_time');
      this.u_state = gl.getUniformLocation(prog, 'u_state');
      this.u_state_intensity = gl.getUniformLocation(prog, 'u_state_intensity');
      this.u_speed = gl.getUniformLocation(prog, 'u_speed');
      this.u_intensity = gl.getUniformLocation(prog, 'u_intensity');
      this.u_pt  = gl.getUniformLocation(prog, 'u_pt');
      this.u_ptc = gl.getUniformLocation(prog, 'u_ptc');
      this.u_tr  = gl.getUniformLocation(prog, 'u_tr');
      this._ptBuf  = new Float32Array(NPT * 4);          // xyz world + brightness
      this._ptcBuf = new Float32Array(NPT * 3);          // colour
      this._trBuf  = new Float32Array(NPT * TRAILP * 4); // xy screen, z depth, w unused
      for (let i = 0; i < NPT; i++) {
        const c = SWARM_COL[PT[i].swarm], g = SWARM_GAIN[PT[i].swarm];
        this._ptcBuf[i * 3] = c[0] * g;
        this._ptcBuf[i * 3 + 1] = c[1] * g;
        this._ptcBuf[i * 3 + 2] = c[2] * g;
      }
    }

    // SWARM CENTRES travel intertwined loops -- the sin/cos phase pair that makes the two paths
    // in Daniil's first shader swirl around one another, generalised to three. Circling in xz
    // while oscillating in y at an incommensurate rate gives a wandering helix rather than a
    // ring, so the swarms pass through each other's space without ever colliding on a cycle.
    _swarmCentre(s, t, out) {
      const ph = s * 2.0944;                       // 120 degrees apart
      const a = t * 0.17 + ph;
      out[0] = Math.sin(a) * 2.15;
      out[1] = Math.cos(a * 1.31 + ph) * 0.85;
      out[2] = Math.cos(a) * 2.15;
    }

    // The whole scene's geometry, once per frame. NPT x TRAILP path evaluations here replace the
    // same work multiplied by every pixel on screen -- see the note above u_pt in the shader.
    _updateSwarms(t) {
      const pb = this._ptBuf, tb = this._trBuf, c = this._ctr || (this._ctr = [0, 0, 0]);
      let o = 0;
      for (let i = 0; i < NPT; i++) {
        const p = PT[i];
        for (let k = 0; k < TRAILP; k++) {
          // Sampling the path BACKWARDS in time IS the trail -- the motion is analytic, so the
          // past is a function call rather than a history buffer.
          const tt = t - k * TRAIL_DT;
          this._swarmCentre(p.swarm, tt, c);
          const orb = p.phase + tt * p.rate;
          const x = c[0] + Math.cos(orb) * p.rad;
          const y = c[1] + Math.sin(orb * p.tilt) * p.rad * 0.8;
          const z = c[2] + Math.sin(orb) * p.rad;
          if (k === 0) {
            pb[i * 4] = x; pb[i * 4 + 1] = y; pb[i * 4 + 2] = z;
            // A slow individual pulse, so a swarm shimmers rather than glowing as one lamp.
            pb[i * 4 + 3] = p.bright * (0.72 + 0.28 * Math.sin(tt * 1.7 + p.phase * 2.0));
          }
          // Project here: the perspective divide is per-point, not per-pixel. Depth is clamped so
          // a particle swinging through the camera plane cannot divide by ~0 and fling a trail
          // segment to infinity -- which draws as a full-screen streak, not as a missing line.
          const depth = Math.max(z + CAMZ, 0.30);
          const inv = FOCAL / depth;
          tb[o++] = x * inv; tb[o++] = y * inv; tb[o++] = depth; tb[o++] = 0;
        }
      }
    }

    _resize() {
      // RENDER BELOW DISPLAY RESOLUTION, ON PURPOSE. The backing store is stretched to the
      // element by the compositor, which is free; fragment shading is not, and it scales with
      // pixel COUNT. This aurora is a soft, blurred, low-frequency field with no edges to
      // alias, so it is the ideal candidate for undersampling -- there is no detail to lose.
      //
      // MEASURED, and this is why the constant exists rather than a guess: the canvas had been
      // stuck at its intrinsic 300x150 because the CSS never sized it (the "corner band" bug).
      // Fixing that to a real 1440x900 viewport took the console from 60fps/100% smooth to
      // 44.6fps/65.5% -- roughly 57x the pixels. Half-resolution restores the frame budget at
      // ~4x fewer fragments than full 2x DPR, and design/CONTRACT.md makes 60fps the bar.
      //
      // AKASHIC_AURORA_SCALE dials it (1 = native) for a machine that can afford more.
      const dpr = Math.min(global.devicePixelRatio || 1, 2);   // cap at 2x
      let scale = parseFloat(global.AKASHIC_AURORA_SCALE);
      if (!(scale > 0 && scale <= 1)) scale = 0.5;
      const eff = Math.max(0.35, dpr * scale);   // never below 0.35 -- banding becomes visible
      const w = Math.max(1, Math.floor(this.canvas.clientWidth * eff));
      const h = Math.max(1, Math.floor(this.canvas.clientHeight * eff));
      this.canvas.width = w; this.canvas.height = h;
      this.gl.viewport(0, 0, w, h);
    }

    _bind() {
      this._onResize = () => this._resize();
      global.addEventListener('resize', this._onResize);
      // Zero GPU work while the tab is hidden (perf gate).
      this._onVis = () => { document.hidden ? this.stop() : this.start(); };
      document.addEventListener('visibilitychange', this._onVis);
    }

    _tick() {
      if (!this.animating) return;
      global.requestAnimationFrame(() => this._tick());
      const gl = this.gl;
      const time = (performance.now() / 1000) - this.startTime;
      this.stateLerp = Math.min(1.0, this.stateLerp + 0.016 / 1.5);   // ~1.5s transition
      gl.uniform2f(this.u_resolution, this.canvas.width, this.canvas.height);
      gl.uniform1f(this.u_time, time);
      gl.uniform1i(this.u_state, this.state);
      gl.uniform1f(this.u_state_intensity, this.stateLerp);
      gl.uniform1f(this.u_speed, this.speed);
      gl.uniform1f(this.u_intensity, this.intensity);
      // Flock time rides u_speed like everything else, so the speed slider still governs the
      // whole field rather than desynchronising the trails from the lattice behind them.
      this._updateSwarms(time * this.speed);
      gl.uniform4fv(this.u_pt, this._ptBuf);
      gl.uniform3fv(this.u_ptc, this._ptcBuf);
      gl.uniform4fv(this.u_tr, this._trBuf);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      this._frames++;
    }

    start() { if (!this.animating) { this.animating = true; this._tick(); } }
    stop() { this.animating = false; }
    destroy() {
      this.stop();
      global.removeEventListener('resize', this._onResize);
      document.removeEventListener('visibilitychange', this._onVis);
    }
  }

  const api = { AuroraShader, isSupported };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;   // node --check / test
  global.AuroraShader = AuroraShader;
  global.AuroraGlass = api;
})(typeof window !== 'undefined' ? window : globalThis);
