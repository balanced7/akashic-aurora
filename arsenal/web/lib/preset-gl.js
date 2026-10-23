// Play's preset bank, rendered by a small module: arsenal/web/lib/preset-gl.js (ES module, raw WebGL2, no build step).
//
// Play (arsenal/web/play.js) is one IIFE whose runtime cannot be imported, so a page that wants its presets under its
// own controls (the Shader Desk) needs the same contract in a module. This is that contract, kept to Play's rules
// (arsenal/PLAY-NIGHT-SPEC.md, arsenal/presets.py UNIFORMS): First Light's fullscreen triangle with v_uv (0,0) at the
// bottom left; every preset renders into its own ping-pong pair at the canvas size, so u_prev is its own last frame;
// u_video is black (u_has_video 0) because the desk has no clip; u_audio is the 512 x 2 R8 texture (row 0 spectrum,
// row 1 waveform); a crossfade between the outgoing and incoming preset is smoothstep-eased in a blit that also
// clamps NaN and Inf to black. Every uniform is set on every frame; an optimised-out one is a no-op.
//
// What differs from Play, on purpose: the audio texture is drawn from the VJ engine's three bands (bass, mid, high) and
// its hits, not from an AnalyserNode, so a spectrum-drawing preset shows the engine's picture of the music, and says
// so (stats().audio = "engine bands" or "silence"). The frame clock is the page clock, as in Play.
//
//   const r = createPresetRenderer(canvas, { scale: 1 });
//   r.add({ id, name, params, url }, source)  -> { ok, log }      compile now (synchronously)
//   r.select(id, { fadeMs: 600 })
//   r.setKnob(id, k /*1..8*/, v /*0..1*/);  r.setGlobal("u_hue", deg);  r.setGlobal("u_intensity", 0..1)
//   r.setBands({ bass, mid, high, level }); r.hit(strength); r.beat(1)
//   r.start() / r.stop()                       the requestAnimationFrame loop
//   r.still({ time, frames })                  for checks: clear the active preset's history, draw `frames` frames at a
//                                              fixed time, return { hash, mean, w, h } of the canvas
//   r.uniform(name)                            the active program's uniform AS THE GPU HOLDS IT (gl.getUniform)

export const PRESET_GL_API = "arsenal.preset-gl/v1";
export const UNIFORM_NAMES = Object.freeze([
  "u_video", "u_prev", "u_audio", "u_res", "u_video_res", "u_time", "u_media_time", "u_frame",
  "u_has_video", "u_pulse", "u_beat", "u_level", "u_bass", "u_mid", "u_high", "u_flux",
  "u_hue", "u_intensity", "u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8",
]);
const K_UNIFORMS = ["u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8"];
const AUDIO_W = 512;
const SPEC_LO_HZ = 20, SPEC_HI_HZ = 16000;
const BEAT_DECAY_S = 0.18, PULSE_ATTACK_S = 0.012, PULSE_RELEASE_S = 0.18, BAND_RELEASE_S = 0.12;

const VERT = `#version 300 es
precision highp float;
out vec2 v_uv;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  vec2 p = pos[gl_VertexID];
  v_uv = (p + 1.0) * 0.5;
  gl_Position = vec4(p, 0.0, 1.0);
}`;
// Play's blit, verbatim in effect: eased mix, NaN/Inf to black, clamp, a static per-pixel dither.
const BLIT = `#version 300 es
precision highp float;
uniform sampler2D u_a;
uniform sampler2D u_b;
uniform float u_mix;
uniform float u_gain;
in vec2 v_uv;
out vec4 outColor;
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
void main() {
  vec3 a = texture(u_a, v_uv).rgb;
  vec3 b = texture(u_b, v_uv).rgb;
  float m = clamp(u_mix, 0.0, 1.0);
  m = m * m * (3.0 - 2.0 * m);
  vec3 c = mix(a, b, m);
  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
  c = clamp(c, 0.0, 1.0) * u_gain;
  c += (h12(gl_FragCoord.xy) - 0.5) / 255.0 * u_gain;
  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

const clamp = (x, a, b) => Math.min(Math.max(x, a), b);

export function createPresetRenderer(canvas, opts = {}) {
  const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, premultipliedAlpha: false,
    preserveDrawingBuffer: !!opts.preserveDrawingBuffer, powerPreference: opts.powerPreference || "high-performance" });
  if (!gl) throw new Error("WebGL2 is not available in this browser");
  const now = opts.now || (() => performance.now());
  let scale = clamp(opts.scale ?? 1, 0.25, 2);
  const fbHalf = !!gl.getExtension("EXT_color_buffer_float");
  let fbInternal = fbHalf ? gl.RGBA16F : gl.RGBA8, fbType = fbHalf ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE;

  const tex = (filter) => {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    return t;
  };
  const black = tex(gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
  const audioTex = tex(gl.LINEAR);
  const audioBytes = new Uint8Array(AUDIO_W * 2);
  audioBytes.fill(128, AUDIO_W);   // a silent waveform sits at 128
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, AUDIO_W, 2, 0, gl.RED, gl.UNSIGNED_BYTE, audioBytes);

  function compile(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { const log = gl.getShaderInfoLog(s) || "compile failed"; gl.deleteShader(s); throw new Error(log); }
    return s;
  }
  const vert = compile(gl.VERTEX_SHADER, VERT);
  function link(fragSrc) {
    const f = compile(gl.FRAGMENT_SHADER, fragSrc);
    const p = gl.createProgram();
    gl.attachShader(p, vert); gl.attachShader(p, f);
    gl.linkProgram(p);
    gl.deleteShader(f);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { const log = gl.getProgramInfoLog(p) || "link failed"; gl.deleteProgram(p); throw new Error(log); }
    return p;
  }
  const blit = link(BLIT);
  const blitU = { a: gl.getUniformLocation(blit, "u_a"), b: gl.getUniformLocation(blit, "u_b"), mix: gl.getUniformLocation(blit, "u_mix"), gain: gl.getUniformLocation(blit, "u_gain") };
  gl.useProgram(blit); gl.uniform1i(blitU.a, 0); gl.uniform1i(blitU.b, 1);
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);

  const presets = new Map();
  const globals = { u_hue: 0, u_intensity: 0.8 };
  const feat = { level: 0, bass: 0, mid: 0, high: 0, flux: 0 };
  const target = { level: 0, bass: 0, mid: 0, high: 0 };
  let beatV = 0, pulse = 0, hitV = 0, active = null, from = null, fadeStart = 0, fadeMs = 600, blackout = false;
  let raf = 0, last = 0, frozenTime = null, audioMode = "silence", lastBands = -1e9;
  const stats = { frames: 0, fps: 0, slow: 0, w: 0, h: 0, errors: [], scale, lowered: null };
  // First Light's watchdog (Play keeps it too): 20 frames in a row slower than twice the 60 Hz budget halve the
  // backing scale, down to 0.5, and stats().lowered says so (never a silent drop: the page shows it).
  const watchdog = opts.watchdog !== false;
  let slowStreak = 0;
  let fpsWin = { t: 0, n: 0 };

  function makePair(w, h) {
    const pair = { w, h, texs: [], fbos: [], read: 0 };
    for (let i = 0; i < 2; i++) {
      const t = tex(gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, fbInternal, w, h, 0, gl.RGBA, fbType, null);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
      pair.texs.push(t); pair.fbos.push(fb);
    }
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    if (!ok && fbInternal !== gl.RGBA8) {
      dropPair(pair);
      fbInternal = gl.RGBA8; fbType = gl.UNSIGNED_BYTE;
      return makePair(w, h);
    }
    clearPair(pair);
    return pair;
  }
  function dropPair(pair) {
    if (!pair) return;
    pair.texs.forEach((t) => gl.deleteTexture(t));
    pair.fbos.forEach((f) => gl.deleteFramebuffer(f));
  }
  function clearPair(pair) {
    gl.clearColor(0, 0, 0, 1);
    for (const fb of pair.fbos) { gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.viewport(0, 0, pair.w, pair.h); gl.clear(gl.COLOR_BUFFER_BIT); }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    pair.read = 0;
  }
  function resize() {
    const dpr = Math.min(globalThis.devicePixelRatio || 1, 2) * scale;
    const w = Math.max(1, Math.round((canvas.clientWidth || canvas.width) * dpr));
    const h = Math.max(1, Math.round((canvas.clientHeight || canvas.height) * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    stats.w = canvas.width; stats.h = canvas.height;
    for (const p of presets.values()) if (p.fb && (p.fb.w !== canvas.width || p.fb.h !== canvas.height)) { dropPair(p.fb); p.fb = null; }
  }

  function add(info, source) {
    const id = String(info.id);
    const old = presets.get(id);
    const knobs = old ? old.knobs : defaultKnobs(info.params);
    const p = { id, name: info.name || id, author: info.author || "", tags: info.tags || [], params: info.params || [],
      program: null, u: null, fb: old ? old.fb : null, frame: 0, knobs, log: "", ok: false };
    try {
      p.program = link(source);
      p.u = Object.fromEntries(UNIFORM_NAMES.map((n) => [n, gl.getUniformLocation(p.program, n)]));
      gl.useProgram(p.program);
      if (p.u.u_video) gl.uniform1i(p.u.u_video, 0);
      if (p.u.u_prev) gl.uniform1i(p.u.u_prev, 1);
      if (p.u.u_audio) gl.uniform1i(p.u.u_audio, 2);
      p.ok = true;
    } catch (err) {
      p.log = String(err && err.message ? err.message : err);
    }
    if (old && old.program && old.program !== p.program) gl.deleteProgram(old.program);
    presets.set(id, p);
    if (active && active.id === id) active = p;
    return { ok: p.ok, log: p.log };
  }
  function defaultKnobs(params) {
    const k = [0, 0, 0, 0, 0, 0, 0, 0];
    for (const pr of params || []) if (pr && pr.k >= 1 && pr.k <= 8 && typeof pr.default === "number") k[pr.k - 1] = clamp(pr.default, 0, 1);
    return k;
  }
  function select(id, o = {}) {
    const p = presets.get(id);
    if (!p || !p.ok) return false;
    if (active === p) return true;
    if (active && (o.fadeMs ?? fadeMs) > 0) { from = active; fadeStart = now(); fadeMs = o.fadeMs ?? fadeMs; }
    else from = null;
    active = p;
    return true;
  }

  // t drives the ripple (the page clock, or a check's fixed clock); live = the engine sent bands in the last 1.5 s.
  function writeAudio(t, live = now() - lastBands < 1500) {
    audioMode = live ? "engine bands" : "silence";
    const lb = Math.log(SPEC_LO_HZ), span = Math.log(SPEC_HI_HZ) - lb;
    for (let i = 0; i < AUDIO_W; i++) {
      if (!live) { audioBytes[i] = 0; audioBytes[AUDIO_W + i] = 128; continue; }
      const hz = Math.exp(lb + span * (i / (AUDIO_W - 1)));
      // each band is a soft hill on the log axis; a little ripple keeps a spectrum-drawing preset from looking frozen
      const wB = Math.exp(-((Math.log(hz / 70)) ** 2) / 0.9), wM = Math.exp(-((Math.log(hz / 600)) ** 2) / 1.4), wH = Math.exp(-((Math.log(hz / 5000)) ** 2) / 1.6);
      const ripple = 0.85 + 0.15 * Math.sin(i * 0.37 + t * 0.004) * Math.sin(i * 0.11 - t * 0.0023);
      const v = clamp((feat.bass * wB + feat.mid * wM + feat.high * wH) * ripple + hitV * 0.25 * wB, 0, 1);
      audioBytes[i] = Math.round(v * 255);
      const wave = Math.sin(i / AUDIO_W * Math.PI * 2 * 3 + t * 0.006) * (0.55 * feat.bass + 0.3 * feat.mid) + Math.sin(i * 0.9 + t * 0.03) * 0.2 * feat.high;
      audioBytes[AUDIO_W + i] = Math.round(clamp(wave * 0.5 + 0.5, 0, 1) * 255);
    }
    gl.bindTexture(gl.TEXTURE_2D, audioTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, AUDIO_W, 2, gl.RED, gl.UNSIGNED_BYTE, audioBytes);
  }
  function stepFeatures(dt) {
    for (const k of ["level", "bass", "mid", "high"]) {
      const tg = target[k];
      feat[k] = tg > feat[k] ? tg : feat[k] + (tg - feat[k]) * (1 - Math.exp(-dt / BAND_RELEASE_S));
    }
    feat.flux = hitV;
    hitV *= Math.exp(-dt / 0.15);
    beatV *= Math.exp(-dt / BEAT_DECAY_S);
    const want = Math.max(feat.level, hitV);
    pulse += (want - pulse) * (1 - Math.exp(-dt / (want > pulse ? PULSE_ATTACK_S : PULSE_RELEASE_S)));
  }

  function renderOne(p, time) {
    if (!p || !p.ok) return;
    if (!p.fb) p.fb = makePair(canvas.width, canvas.height);
    const fb = p.fb, write = 1 - fb.read;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb.fbos[write]);
    gl.viewport(0, 0, fb.w, fb.h);
    gl.useProgram(p.program);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, black);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fb.texs[fb.read]);
    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, audioTex);
    const u = p.u;
    gl.uniform2f(u.u_res, fb.w, fb.h);
    gl.uniform2f(u.u_video_res, 1, 1);
    gl.uniform1f(u.u_time, time);
    gl.uniform1f(u.u_media_time, 0);
    gl.uniform1f(u.u_frame, p.frame);
    gl.uniform1f(u.u_has_video, 0);
    gl.uniform1f(u.u_pulse, pulse);
    gl.uniform1f(u.u_beat, beatV);
    gl.uniform1f(u.u_level, feat.level);
    gl.uniform1f(u.u_bass, feat.bass);
    gl.uniform1f(u.u_mid, feat.mid);
    gl.uniform1f(u.u_high, feat.high);
    gl.uniform1f(u.u_flux, feat.flux);
    gl.uniform1f(u.u_hue, globals.u_hue);
    gl.uniform1f(u.u_intensity, globals.u_intensity);
    for (let k = 0; k < 8; k++) gl.uniform1f(u[K_UNIFORMS[k]], p.knobs[k]);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    fb.read = write;
    p.frame++;
  }
  function present(mix) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    if (!active || !active.fb) { gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT); return; }
    const a = from && from.fb ? from : active;
    gl.useProgram(blit);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, a.fb.texs[a.fb.read]);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, active.fb.texs[active.fb.read]);
    gl.uniform1f(blitU.mix, a === active ? 1 : mix);
    gl.uniform1f(blitU.gain, blackout ? 0 : 1);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  function frame(t, timeSec) {
    const dt = last ? clamp((t - last) / 1000, 0, 0.1) : 0;
    const gap = last ? t - last : 0;
    last = t;
    stepFeatures(dt);
    resize();
    writeAudio(t);
    let mix = 1;
    if (from) {
      mix = clamp((t - fadeStart) / Math.max(1, fadeMs), 0, 1);
      if (mix >= 1) { if (from.fb) { dropPair(from.fb); from.fb = null; } from = null; }
    }
    const time = timeSec ?? (frozenTime ?? t / 1000);
    if (from) renderOne(from, time);
    renderOne(active, time);
    present(mix);
    stats.frames++;
    if (gap > 50) stats.slow++;
    slowStreak = gap > 2000 / 60 && gap < 1000 ? slowStreak + 1 : 0;   // a gap over 1 s is a hidden tab, not a slow frame
    if (watchdog && slowStreak >= 20 && scale > 0.5) {
      const from = scale;
      scale = Math.max(0.5, scale / 2);
      slowStreak = 0;
      stats.scale = scale;
      stats.lowered = { from, to: scale, gapMs: Math.round(gap), at: new Date().toISOString() };
      resize();
    }
    fpsWin.n++;
    if (t - fpsWin.t >= 1000) { stats.fps = Math.round(fpsWin.n * 10000 / (t - fpsWin.t)) / 10; fpsWin = { t, n: 0 }; }
  }
  function loop(t) {
    raf = requestAnimationFrame(loop);
    try { frame(t); } catch (err) { if (stats.errors.length < 5) stats.errors.push(String(err && err.message || err)); }
  }

  // A check's frame: no history, a fixed clock, then a signature of what the canvas shows.
  function still({ time = 2, frames = 1 } = {}) {
    if (!active) return null;
    if (from) { if (from.fb) { dropPair(from.fb); from.fb = null; } from = null; }
    resize();
    if (active.fb) clearPair(active.fb);
    active.frame = 0;
    const savedLast = last;
    for (let i = 0; i < frames; i++) { last = 0; stepFeatures(0); writeAudio(time * 1000); renderOne(active, time); }
    last = savedLast;
    present(1);
    const w = canvas.width, h = canvas.height;
    const px = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    // a hash of every pixel, the mean colour, and a 32 x 18 grid of mean luma (0..255) to measure how much changed
    const GW = 32, GH = 18, grid = new Float64Array(GW * GH), cnt = new Uint32Array(GW * GH);
    let hash = 2166136261;
    const sum = [0, 0, 0];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      sum[0] += px[i]; sum[1] += px[i + 1]; sum[2] += px[i + 2];
      hash = Math.imul(hash ^ px[i], 16777619) >>> 0; hash = Math.imul(hash ^ px[i + 1], 16777619) >>> 0; hash = Math.imul(hash ^ px[i + 2], 16777619) >>> 0;
      const c = Math.min(GH - 1, Math.floor(y * GH / h)) * GW + Math.min(GW - 1, Math.floor(x * GW / w));
      grid[c] += 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2];
      cnt[c]++;
    }
    const n = w * h;
    return { hash: hash.toString(16).padStart(8, "0"), mean: sum.map((s) => Math.round((s / n) * 100) / 100), w, h,
      grid: Array.from(grid, (g, i) => Math.round((g / Math.max(1, cnt[i])) * 100) / 100), gridW: GW, gridH: GH };
  }

  return {
    api: PRESET_GL_API, gl, canvas,
    add, select, has: (id) => presets.has(id) && presets.get(id).ok,
    // live[k-1] is false when the compiled program has no u_k<k> (the shader never reads it: a dead knob)
    info: (id) => { const p = presets.get(id); return p ? { id: p.id, name: p.name, ok: p.ok, log: p.log, knobs: p.knobs.slice(), params: p.params,
      live: K_UNIFORMS.map((n) => !!(p.u && p.u[n])) } : null; },
    get active() { return active ? active.id : null; },
    setKnob(id, k, v) { const p = presets.get(id); if (p && k >= 1 && k <= 8) p.knobs[k - 1] = clamp(+v || 0, 0, 1); },
    knob(id, k) { const p = presets.get(id); return p ? p.knobs[k - 1] : null; },
    setGlobal(name, v) { if (name in globals) globals[name] = +v || 0; },
    global: (name) => globals[name],
    setBands(b) { for (const k of ["level", "bass", "mid", "high"]) if (typeof b[k] === "number") target[k] = clamp(b[k], 0, 1); lastBands = now(); },
    hit(s) { hitV = Math.max(hitV, clamp(+s || 0, 0, 1)); lastBands = now(); },
    beat(v = 1) { beatV = Math.max(beatV, clamp(v, 0, 1)); },
    setBlackout(on) { blackout = !!on; },
    get blackout() { return blackout; },
    setScale(s) { scale = clamp(s, 0.25, 2); stats.scale = scale; stats.lowered = null; resize(); },
    freeze(t) { frozenTime = t === null || t === undefined ? null : +t; },
    start() { if (!raf) { last = 0; raf = requestAnimationFrame(loop); } },
    stop() { if (raf) cancelAnimationFrame(raf); raf = 0; },
    renderFrame: (t) => frame(t ?? now()),
    still,
    // The active program's uniform as the GPU holds it (gl.getUniform), not what this module thinks it set.
    uniform(name) {
      if (!active || !active.ok || !active.u || !active.u[name]) return null;
      return gl.getUniform(active.program, active.u[name]);
    },
    stats: () => ({ ...stats, audio: audioMode, fb: fbInternal === gl.RGBA16F ? "RGBA16F" : "RGBA8", active: active ? active.id : null,
      renderer: (() => { const e = gl.getExtension("WEBGL_debug_renderer_info"); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); })() }),
    destroy() { this.stop(); for (const p of presets.values()) { if (p.program) gl.deleteProgram(p.program); dropPair(p.fb); } presets.clear(); },
  };
}

// Play's preset list (GET /api/presets on the arsenal server), or the one header line of each file when the list is
// not there. Returns [{ id, name, author, tags, params, url, problems }].
export async function listPresets(fetchFn = fetch, base = "") {
  const r = await fetchFn(base + "/api/presets", { cache: "no-store" });
  if (!r.ok) throw new Error(`GET /api/presets: HTTP ${r.status}`);
  const data = await r.json();
  return Array.isArray(data && data.presets) ? data.presets : [];
}
// The `//! {json}` header on line 2 of a preset file (presets.py's format).
export function parseHeader(src) {
  const line = String(src).split(/\r?\n/)[1] || "";
  if (!line.startsWith("//!")) return null;
  try { return JSON.parse(line.slice(3)); } catch { return null; }
}
