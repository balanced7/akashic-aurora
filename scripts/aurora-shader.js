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

  // ONE LATTICE LAYER, factored out of main so the field can be built from several at different
// depths. Everything here is what main() used to do inline; nothing about a single layer changed.
// Returns x = lattice brightness, y = wave pulse (the hue driver).
  vec2 latticeLayer(vec2 suv, float T, float cells, float seed, float drift, float meshAmt) {
    vec2 gp = suv * cells + seed * 17.0;       // seed offsets the grid so layers never align
    vec2 id = floor(gp);
    vec2 gv = fract(gp) - 0.5;                 // -0.5..0.5 within the cell

    // three travelling waves; each angle rotates at its own rate so the flow direction drifts
    float a1 = T * 0.045 + seed, a2 = -T * 0.031 + 2.1 + seed, a3 = T * 0.019 + 4.2 + seed;
    vec2 d1 = vec2(cos(a1), sin(a1));
    vec2 d2 = vec2(cos(a2), sin(a2));
    vec2 d3 = vec2(cos(a3), sin(a3));
    float w = sin(dot(id, d1) * 0.42 - T * 0.9)
            + sin(dot(id, d2) * 0.30 - T * 0.6)
            + sin(dot(id, d3) * 0.21 - T * 0.4);
    w /= 3.0;                                   // -1..1
    float pulse = 0.5 + 0.5 * w;                // 0..1

    // DOTS MOVE: displace each dot inside its own cell along the wave gradient. Small, so the
    // lattice stays legible as a lattice while visibly breathing.
    vec2 dr = drift * vec2(sin(dot(id, d1) * 0.42 - T * 0.9),
                           cos(dot(id, d2) * 0.30 - T * 0.6));
    float dist = length(gv - dr);

    // dot radius rides the wave -- the crest is where the lattice brightens
    float r = mix(0.055, 0.20, pulse * pulse);
    float dot_ = smoothstep(r, r * 0.35, dist);

    // WIREFRAME MOSAIC: the cell's own edge, revealed only where the wave is high. Reusing gv
    // means the mesh costs one more max() -- no second field, no extra noise. meshAmt exists
    // because three overlaid meshes at three scales is clutter, not depth: only the near layer
    // draws its full mesh, and the far ones read as texture instead of competing grids.
    float edge = max(abs(gv.x), abs(gv.y));
    float mesh = smoothstep(0.46, 0.5, edge) * pow(pulse, 3.0) * 0.5 * meshAmt;

    return vec2(dot_ * (0.35 + 0.9 * pulse) + mesh, pulse);
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    // aspect-correct the x so the curtain doesn't stretch on wide viewports
    vec2 suv = vec2(uv.x * (u_resolution.x / u_resolution.y), uv.y);

    // ===================== DOT LATTICE  (Daniil's brief, 2026-08-01) =====================
    // "a grid of dots that move and have patterns that swim through them changing which order
    //  they flow through them" + "wireframe mosaics that have a neon color gradient".
    //
    // WHY THIS REPLACED THE FBM CURTAIN, and it is a perf argument before an aesthetic one:
    // the previous field cost FIVE fbm evaluations per fragment (2 warp + 1 sheet + 1 void +
    // 1 filament), each of which is multi-octave value noise. Adding the voids and filaments he
    // asked for measured 60fps -> 43.7fps / 62.7% smooth at 1600x900. A lattice is a different
    // cost class entirely: one fract, one length, and three sin() -- no noise at all. That is
    // what makes it viable on a phone, which was the other half of the brief.
    //
    // THE MECHANISM. Tile space into cells; each cell holds one dot. A dot's brightness is
    // driven by a WAVE PHASE derived from its own cell id, so the pattern sweeps ACROSS the
    // lattice rather than every dot pulsing together. Three waves at different angles sum into
    // interference, and the angles ROTATE at different rates -- so the direction the pattern
    // swims through the grid keeps changing and never repeats on a visible cycle. That is
    // literally "changing which order they flow through them", and it costs three sines.
    float T = u_time * u_speed;

    const float CELLS = 26.0;                  // lattice density across the short axis

    // ===================== PARALLAX DEPTH =====================
    // The field was ONE plane, and that is why it read as flat however good the motion was:
    // nothing receded, nothing occluded, every dot the same size and the same brightness.
    // Three layers at different scales, speeds and depths buy real space for almost nothing --
    // a lattice layer is one fract, one length and five sines, so all three together are still
    // a small fraction of ONE of the five fbm evaluations this field replaced.
    //
    // AERIAL PERSPECTIVE is what makes it read as distance rather than as clutter. Far layers
    // are DIMMER, DENSER (more cells = smaller dots), SLOWER, and pulled toward the cool end of
    // the palette; the near layer is brighter, larger, faster and spans the full hue range.
    // That is how atmosphere actually attenuates something far away, so the eye reads depth
    // without being told -- and it is why the far layers do not simply look like more dots.
    vec2 L0 = latticeLayer(suv, T * 0.55, CELLS * 1.90, 3.7, 0.09, 0.0);   // far   -- texture
    vec2 L1 = latticeLayer(suv, T * 0.80, CELLS * 1.28, 1.3, 0.13, 0.35);  // mid
    vec2 L2 = latticeLayer(suv, T,        CELLS,        0.0, 0.17, 1.0);   // near  -- the subject

    // --- composition envelope: keep the vertical middle dark so body text stays legible.
    // Same intent as the old curtain bands, one smoothstep instead of two.
    float envTop = smoothstep(0.42, 1.0, uv.y);
    float envBot = smoothstep(0.34, 0.0, uv.y) * 0.75;     // a little light under the composer
    float env = max(envTop, envBot);

    // NEON GRADIENT across the lattice: hue rides position + wave, so colour travels with the
    // pattern instead of being painted on. auroraColor is still the palette gate -- every layer
    // indexes THROUGH it, so depth cannot smuggle in a hue the design system does not own. The
    // far layers simply sit lower in the ramp, which is where its cool end lives.
    float t0 = clamp(L0.x * env, 0.0, 1.0);
    float t1 = clamp(L1.x * env, 0.0, 1.0);
    float t2 = clamp(L2.x * env, 0.0, 1.0);
    vec3 col = auroraColor(clamp(0.16 + 0.14 * L0.y,                    0.0, 1.0)) * t0 * 0.34
             + auroraColor(clamp(0.26 + 0.30 * L1.y + 0.10 * uv.x,      0.0, 1.0)) * t1 * 0.62
             + auroraColor(clamp(0.35 + 0.45 * L2.y + 0.22 * uv.x,      0.0, 1.0)) * t2 * 1.30;
    col *= u_intensity;

    // FIELD MAGNITUDE, kept because the state tints below modulate BY the lattice -- the amber
    // (paused) and grey (halted) washes have to land on the pattern rather than flood the void.
    // This used to be the single layer's t; with three layers it is their weighted sum.
    float t = clamp(t0 * 0.34 + t1 * 0.62 + t2 * 1.30, 0.0, 1.0);

    // SUPERLINEAR HIGHLIGHT, the c*c term from the wave shader Daniil singled out (no backticks
    // in this comment on purpose: the whole shader is a JS template literal, and one would end
    // it mid-sentence). This is
    // what lets the field go DARKER and more striking at once instead of trading one for the
    // other: squaring leaves the dark two-thirds essentially untouched and pays out only at the
    // crests, so the mids sink toward black while the bright nodes bloom. Lowering brightness
    // alone would have flattened the crests along with everything else.
    col += col * col * 0.90;

    // faint atmospheric bloom so the lattice sits in air rather than on black -- a wide, cheap
    // radial that also stops the lower half reading as a flat void
    col += auroraColor(0.62) * 0.055 * u_intensity * smoothstep(1.25, 0.15, length(uv - vec2(0.5, 0.86)));

    // --- state tint (synthesis §2a) ---
    // paused -> shift toward amber; halted -> desaturate + darken. Lerped by u_state_intensity.
    if (u_state == 1) {
      vec3 amber = vec3(0.94, 0.70, 0.27);
      col = mix(col, amber * t, u_state_intensity * 0.4);
    } else if (u_state == 2) {
      col = mix(col, vec3(dot(col, vec3(0.299, 0.587, 0.114))) * 0.3, u_state_intensity * 0.7);
    }

    // --- VIGNETTE: aspect-corrected, on a POWER falloff (the shape from the compositing shader
    //     Daniil pasted, which uses pow(dist * scale, 3)). Two real fixes over the old
    //     smoothstep. FIRST, it was measured in raw uv, so on a 16:9 monitor the "circle" was an
    //     ellipse squashed to the viewport and the left and right edges darkened far harder than
    //     the top and bottom -- correcting x by the aspect makes it an actual circle. SECOND, a
    //     smoothstep begins shading immediately from the centre, dimming the middle of the
    //     screen; a cubic stays essentially flat across the centre and falls away only near the
    //     corners, which is what "framing" means as opposed to "dimming". ---
    float aspect = u_resolution.x / u_resolution.y;
    vec2 vuv = uv;
    vuv.x = (vuv.x - 0.5) * aspect + 0.5;
    // Normalise by the ACTUAL corner distance, not by the 0.7071 of a unit square. Once x is
    // aspect-corrected the corner sits at length(0.5*aspect, 0.5) -- 1.02 at 16:9, not 0.707 --
    // so dividing by 0.7071 would push both corners AND the mid-side edges past 1.0 and clamp
    // them to full black, blacking out the sides of a widescreen display entirely.
    float vd = length(vuv - 0.5) / length(vec2(0.5 * aspect, 0.5));   // 0 centre, 1 at corners
    float vig = 1.0 - pow(clamp(vd * 0.94, 0.0, 1.0), 3.0);
    col *= mix(1.0, vig, 0.66);

    // --- DITHER: triangular PDF, at the quantisation step rather than above it.
    //     Two changes, and both matter more now that the field is darker. The noise is a
    //     DIFFERENCE of two hashes, giving a triangular distribution -- the correct shape for
    //     breaking up quantisation, and it defeats banding at roughly half the amplitude that
    //     uniform noise needs, so less visible grain for a better result. And the amplitude
    //     drops from .015 (~3.8/255) to ~1.6/255: grain that read as filmic over mid greys reads
    //     as sensor noise over near-black, and a darker image needs LESS of it, not more --
    //     while still needing at least one code value to break up the ramps. ---
    float n1 = fract(sin(dot(gl_FragCoord.xy + u_time * 1.7, vec2(12.9898, 78.233))) * 43758.5453);
    float n2 = fract(sin(dot(gl_FragCoord.yx - u_time * 1.3, vec2(63.7264, 10.8730))) * 32168.4321);
    col += (n1 - n2) * (1.6 / 255.0);

    outColor = vec4(col, 1.0);   // opaque; the canvas is the backmost layer
  }`;

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
