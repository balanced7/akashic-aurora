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
    vec3 teal   = vec3(0.29, 0.42, 0.46);
    vec3 green  = vec3(0.28, 0.90, 0.75);   // #48e6bf — the signature neon
    vec3 violet = vec3(0.46, 0.18, 0.54);
    if (t < 0.3) return mix(vec3(0.0), teal,  t / 0.3);
    if (t < 0.5) return mix(teal,  green,  (t - 0.3) / 0.2);
    if (t < 0.7) return mix(green, violet, (t - 0.5) / 0.2);
    return mix(violet, vec3(0.0), (t - 0.7) / 0.3);
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    // aspect-correct the x so the curtain doesn't stretch on wide viewports
    vec2 suv = vec2(uv.x * (u_resolution.x / u_resolution.y), uv.y);

    // --- domain warp (INVARIANT): fbm(uv + fbm(uv + time)) — the folded-curtain look ---
    vec2 q = vec2(
      fbm(suv * 2.0 + vec2(0.0, u_time * 0.03)),
      fbm(suv * 2.0 + vec2(5.2, 1.3) + u_time * 0.04)
    );
    float aurora = fbm(suv * 2.0 + 1.2 * q + vec2(0.0, u_time * 0.02));

    // --- center-dark envelope (claude): two faint bands high in the frame; hard-clamp so nothing
    //     reaches the vertical center where body text lives. uv.y: 0 bottom, 1 top. ---
    float band1 = smoothstep(0.58, 0.74, uv.y) * (1.0 - smoothstep(0.80, 0.98, uv.y));
    float band2 = smoothstep(0.66, 0.82, uv.y) * (1.0 - smoothstep(0.88, 1.02, uv.y)) * 0.6;
    float curtain = aurora * (band1 + band2);
    curtain *= smoothstep(0.50, 0.62, uv.y);          // keep the lower/center dark for legibility

    float t = clamp(curtain, 0.0, 1.0);
    vec3 col = auroraColor(t) * t * 1.6;              // energy toward the bright ribs

    // --- state tint (synthesis §2a) ---
    // paused -> shift toward amber; halted -> desaturate + darken. Lerped by u_state_intensity.
    if (u_state == 1) {
      vec3 amber = vec3(0.94, 0.70, 0.27);
      col = mix(col, amber * t, u_state_intensity * 0.4);
    } else if (u_state == 2) {
      col = mix(col, vec3(dot(col, vec3(0.299, 0.587, 0.114))) * 0.3, u_state_intensity * 0.7);
    }

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
    }

    _resize() {
      const dpr = Math.min(global.devicePixelRatio || 1, 2);   // cap at 2x
      const w = Math.max(1, Math.floor(this.canvas.clientWidth * dpr));
      const h = Math.max(1, Math.floor(this.canvas.clientHeight * dpr));
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
