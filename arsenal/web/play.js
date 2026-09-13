// arsenal/web/play.js
// Play: First Light turned into a MilkDrop-style instrument. No external libraries, no build
// step: one IIFE, loaded with `defer`. Contract: arsenal/PLAY-NIGHT-SPEC.md (extends
// arsenal/FIRST-LIGHT-SPEC.md). Proven First Light patterns are reused: library + drag/drop
// resolve, the take ledger client, Web MIDI connect/learn, WebGL2 setup with context loss, the
// slow-frame watchdog and the HUD.
//
// Frame model: requestAnimationFrame drives rendering at the display rate, so audio-reactive
// feedback never drops to the clip's frame rate. requestVideoFrameCallback (with a rAF fallback)
// tells the loop when a new video frame is ready to upload, and it carries the epoch checks.
// One WebGL2 context: every preset renders into its own ping-pong framebuffer pair, and a
// built-in blit shader mixes the outgoing and incoming presets to the default framebuffer.
//
// Test hook: window.__play (members fixed by Vandor's play_verify.mjs; thin by design).

(function () {
  "use strict";

  // ------------------------------------------------------------ constants --

  var EVENT_TIMEBASE_DEN = 90000;          // media-clock take events
  var ANALYSIS_TIMEBASE_DEN = 48000;       // server audio_features sampling
  var MIDI_MAP_KEY = "arsenal.play.midiMap";
  var AUDIO_PREF_KEY = "arsenal.play.audio";
  var FLUSH_INTERVAL_MS = 500;
  var HUD_INTERVAL_MS = 100;
  var LATENCY_MAX_SAMPLES = 200;
  var EVENT_HZ_LIMIT_MS = 100;             // 10 Hz cap per midi/param key
  var EVENT_QUEUE_CAP = 1000;
  var WATCHDOG_STREAK = 20;
  var FRAME_BUDGET_MS = 1000 / 60;
  var DPR_CAP = 2;
  var BACKING_SCALE_MIN = 0.5;
  var XFADE_DEFAULT_MS = 600;
  var XFADE_MAX_MS = 5000;
  var TOAST_MS = 1500;
  var PERF_HINT_MS = 2000;
  var PRESET_RETRY_MS = 5000;
  var TAKE_RETRY_MS = 5000;
  var ANALYSIS_POLL_MS = 600;
  var BUILTIN_ID = "builtin";
  var SLOT_COUNT = 12;
  var DEFAULT_INTENSITY = 0.8;             // First Light's default

  // audio engine (PLAY-NIGHT-SPEC.md "Audio engine")
  var FFT_SIZE = 2048;
  var AUDIO_TEX_W = 512;
  var SPEC_LO_HZ = 20, SPEC_HI_HZ = 16000;
  var SPEC_DB_LO = -90, SPEC_DB_HI = -20;
  var BANDS = { bass: [20, 150], mid: [150, 2000], high: [2000, 16000] };
  var AGC_GATE_DB = -80, AGC_MIN_SPAN_DB = 12, AGC_CEIL_FALL_DBPS = 6, AGC_FLOOR_RISE_DBPS = 3;
  var LOG_EPS = 1e-12;
  var BEAT_RATIO = 1.35, BEAT_MIN = 0.3, BEAT_REFRACTORY_MS = 180, BEAT_WINDOW_MS = 1000;
  var BEAT_DECAY_S = 0.18;
  var PULSE_ATTACK_MS = 12, PULSE_RELEASE_MS = 180;

  var UNIFORM_NAMES = [
    "u_video", "u_prev", "u_audio", "u_res", "u_video_res", "u_time", "u_media_time", "u_frame",
    "u_has_video", "u_pulse", "u_beat", "u_level", "u_bass", "u_mid", "u_high", "u_flux",
    "u_hue", "u_intensity", "u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8"
  ];

  // ------------------------------------------------------------- shaders --

  // First Light's fullscreen triangle, verbatim: v_uv (0,0) is the bottom-left.
  var VERT_SRC = [
    "#version 300 es",
    "precision highp float;",
    "out vec2 v_uv;",
    "void main() {",
    "  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));",
    "  vec2 p = pos[gl_VertexID];",
    "  v_uv = (p + 1.0) * 0.5;",
    "  gl_Position = vec4(p, 0.0, 1.0);",
    "}"
  ].join("\n");

  // Built-in preset "Passthrough": the letterboxed video, untouched, or without video a
  // simple spectrum scope (u_audio row 0 as bars, row 1 as a waveform line). Silence reads
  // as a dotted baseline and a flat line. Four texture reads per pixel at most.
  var PASSTHROUGH_FRAG_SRC = [
    "#version 300 es",
    "precision highp float;",
    "uniform sampler2D u_video;",
    "uniform sampler2D u_audio;",
    "uniform vec2 u_res, u_video_res;",
    "uniform float u_has_video, u_beat, u_hue, u_intensity;",
    "in vec2 v_uv;",
    "out vec4 outColor;",
    "",
    "vec2 video_uv(vec2 uv) {",
    "  float ca = u_res.x / max(u_res.y, 1.0), va = u_video_res.x / max(u_video_res.y, 1.0);",
    "  vec2 s = va > ca ? vec2(1.0, ca / va) : vec2(va / ca, 1.0);",
    "  return (uv - 0.5) / s + 0.5;",
    "}",
    "vec3 rgb2hsv(vec3 c) {",
    "  vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0);",
    "  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));",
    "  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));",
    "  float d = q.x - min(q.w, q.y);",
    "  float e = 1.0e-10;",
    "  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);",
    "}",
    "vec3 hsv2rgb(vec3 c) {",
    "  vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);",
    "  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);",
    "  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);",
    "}",
    "",
    "void main() {",
    "  if (u_has_video > 0.5) {",
    "    vec2 vu = video_uv(v_uv);",
    "    if (vu.x < 0.0 || vu.x > 1.0 || vu.y < 0.0 || vu.y > 1.0) { outColor = vec4(0.0, 0.0, 0.0, 1.0); return; }",
    "    outColor = vec4(texture(u_video, vu).rgb, 1.0);",
    "    return;",
    "  }",
    "  vec2 uv = v_uv;",
    "  float px = 1.0 / max(u_res.y, 1.0);",
    "  vec3 teal = vec3(0.298, 0.761, 0.729);",
    "  vec3 amber = vec3(0.941, 0.643, 0.263);",
    "  float lift = 1.0 - smoothstep(0.0, 0.55, uv.y);",
    "  vec3 col = vec3(0.028, 0.031, 0.039) + amber * 0.045 * u_beat * lift;",
    "",
    "  // spectrum bars, 96 across, sampled at each bar's centre",
    "  float nb = 96.0;",
    "  float bx = (floor(uv.x * nb) + 0.5) / nb;",
    "  float h = texture(u_audio, vec2(bx, 0.25)).r;",
    "  float inBar = step(abs(fract(uv.x * nb) - 0.5), 0.34);",
    "  float base = 0.12;",
    "  float top = base + max(h * 0.6, 2.0 * px);",
    "  float bar = inBar * step(base, uv.y) * step(uv.y, top);",
    "  vec3 barCol = mix(teal, amber, clamp((uv.y - base) / 0.6, 0.0, 1.0));",
    "  col = mix(col, barCol * (0.5 + 0.5 * h), bar);",
    "  float refl = inBar * step(uv.y, base) * step(base - h * 0.07, uv.y);",
    "  col += teal * 0.16 * refl;",
    "",
    "  // waveform: the min/max of three neighbouring samples, so steep edges stay joined",
    "  float dx = 1.0 / max(u_res.x, 1.0);",
    "  float c0 = 0.86, amp = 0.2;",
    "  float ya = c0 + (texture(u_audio, vec2(uv.x - dx, 0.75)).r - 0.5) * amp;",
    "  float yb = c0 + (texture(u_audio, vec2(uv.x, 0.75)).r - 0.5) * amp;",
    "  float yc = c0 + (texture(u_audio, vec2(uv.x + dx, 0.75)).r - 0.5) * amp;",
    "  float lo = min(yb, 0.5 * (ya + yb));",
    "  lo = min(lo, 0.5 * (yb + yc));",
    "  float hi = max(yb, 0.5 * (ya + yb));",
    "  hi = max(hi, 0.5 * (yb + yc));",
    "  float d = max(lo - uv.y, uv.y - hi) / px;",
    "  float line = 1.0 - smoothstep(0.6, 1.8, d);",
    "  col = mix(col, mix(vec3(0.85, 0.9, 0.92), amber, 0.5 * u_beat), line);",
    "",
    "  if (u_hue > 0.5 || u_hue < -0.5) {",
    "    vec3 hsv = rgb2hsv(col);",
    "    hsv.x = fract(hsv.x + u_hue / 360.0);",
    "    col = hsv2rgb(hsv);",
    "  }",
    "  col *= mix(0.3, 1.0, clamp(u_intensity, 0.0, 1.0));",
    "  outColor = vec4(col, 1.0);",
    "}"
  ].join("\n");

  // Built-in blit: smoothstep-eased mix of the outgoing (a) and incoming (b) preset outputs,
  // presented to the default framebuffer. NaN/Inf from a misbehaving preset shows as black,
  // colour is clamped to 0..1, alpha is ignored. The dither is static per pixel (never per
  // frame, which would crawl) and only breaks banding when 16-bit feedback meets an 8-bit screen.
  var BLIT_FRAG_SRC = [
    "#version 300 es",
    "precision highp float;",
    "uniform sampler2D u_a;",
    "uniform sampler2D u_b;",
    "uniform float u_mix;",
    "uniform float u_gain;",
    "in vec2 v_uv;",
    "out vec4 outColor;",
    "float h12(vec2 p) {",
    "  vec3 p3 = fract(vec3(p.xyx) * 0.1031);",
    "  p3 += dot(p3, p3.yzx + 33.33);",
    "  return fract((p3.x + p3.y) * p3.z);",
    "}",
    "void main() {",
    "  vec3 a = texture(u_a, v_uv).rgb;",
    "  vec3 b = texture(u_b, v_uv).rgb;",
    "  float m = clamp(u_mix, 0.0, 1.0);",
    "  m = m * m * (3.0 - 2.0 * m);",
    "  vec3 c = mix(a, b, m);",
    "  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);",
    "  c = clamp(c, 0.0, 1.0) * u_gain;",
    "  c += (h12(gl_FragCoord.xy) - 0.5) / 255.0 * u_gain;",
    "  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);",
    "}"
  ].join("\n");

  // -------------------------------------------------------------- state --

  var state = {
    gl: null,
    glLost: false,
    fbInternal: null,          // gl.RGBA16F or gl.RGBA8
    fbType: null,
    fbFormat: "RGBA8",
    parallelExt: null,
    videoTex: null,
    blackTex: null,
    audioTex: null,
    blitProg: null,
    blitU: {},
    pool: [],                  // spare framebuffer pairs
    width: 1,
    height: 1,
    backingScale: 1,
    slowStreak: 0,
    lastRafNow: 0,
    gapHist: [],
    fps: 0,
    fpsCount: 0,
    fpsWindowStart: 0,
    renderDropped: 0,
    renderTotal: 0,

    presets: [],
    builtin: null,
    active: null,
    fadeFrom: null,
    fadeStart: 0,
    fadeMs: 0,
    pendingSelect: null,
    restoreSelect: null,
    xfadeMs: XFADE_DEFAULT_MS,
    blackout: false,
    params: { hue: 0, intensity: DEFAULT_INTENSITY },
    presetsStatus: "loading",
    presetsError: null,
    presetsRetryTimer: null,
    presetSwitches: 0,
    errors: [],

    audioCtx: null,
    analyser: null,
    mediaNode: null,
    inputStream: null,
    inputNode: null,
    source: "clip",
    sourcePinned: false,
    inputDeviceId: "",
    inputLabel: "",
    inputSettings: null,
    devices: [],
    audioNote: "",
    freqDb: null,
    timeBuf: null,
    prevMag: null,
    fluxPrimed: false,
    bandBins: null,
    fluxBins: null,
    specPos: null,
    audioBytes: new Uint8Array(AUDIO_TEX_W * 2),
    agc: {},
    feat: { level: 0, bass: 0, mid: 0, high: 0, flux: 0 },
    beat: 0,
    pendingBeat: 0,
    beatHist: [],
    beatHistSum: 0,
    lastBeatAt: -1e9,
    pulseEnv: { value: 0, initialized: false },

    analysis: null,
    analysisReady: false,
    analysisToken: 0,
    analysisStatus: "",

    clip: null,
    blobFile: null,
    objectUrl: null,
    probe: null,
    decodingInfo: null,
    epoch: 0,
    justSeeked: false,
    lastMediaTime: null,
    videoFrameReady: false,
    videoUploaded: false,
    videoFrameMeta: null,
    rvfcGen: 0,

    midiInputName: null,
    lastControl: null,
    pendingLatency: [],
    latencySamples: [],

    takeId: null,
    takeOpening: false,
    takeToken: 0,
    takeEventCount: 0,
    takeError: null,
    takeRetryAt: 0,
    eventQueue: [],
    eventThrottle: {},
    graphTemplate: null,

    perf: false,
    toastTimer: null,
    hintTimer: null,
    libraryClips: []
  };

  var MIDI = {
    access: null,
    input: null,
    learning: null,            // {target, kind: "continuous" | "trigger"}
    bindings: []               // [{target, type: "cc" | "note", ch, num}]
  };

  var CONTINUOUS_TARGETS = ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "hue", "intensity", "xfade"];
  var TRIGGER_TARGETS = ["next", "prev", "random", "blackout"];
  for (var s = 1; s <= SLOT_COUNT; s++) TRIGGER_TARGETS.push("slot" + s);

  // ------------------------------------------------------------- utils --

  function clamp(x, lo, hi) {
    return Math.min(hi, Math.max(lo, x));
  }

  function errText(err) {
    return err && err.message ? err.message : String(err);
  }

  function firstLine(text) {
    var lines = String(text || "").split(/\r?\n/);
    for (var i = 0; i < lines.length; i++) {
      var t = lines[i].trim();
      if (t) return t;
    }
    return "";
  }

  function formatTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60);
    var ss = Math.floor(sec % 60);
    return m + ":" + (ss < 10 ? "0" + ss : String(ss));
  }

  function formatBytes(n) {
    if (typeof n !== "number" || !isFinite(n)) return "";
    var units = ["B", "KB", "MB", "GB"];
    var v = n, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return (i === 0 ? String(v) : v.toFixed(1)) + units[i];
  }

  function percentile(samples, p) {
    if (!samples.length) return null;
    var sorted = samples.slice().sort(function (a, b) { return a - b; });
    var idx = clamp(Math.ceil((p / 100) * sorted.length) - 1, 0, sorted.length - 1);
    return sorted[idx];
  }

  function latencyStats() {
    return { p50: percentile(state.latencySamples, 50), p95: percentile(state.latencySamples, 95) };
  }

  function pushLatencySample(ms) {
    state.latencySamples.push(ms);
    if (state.latencySamples.length > LATENCY_MAX_SAMPLES) state.latencySamples.shift();
  }

  function safeLocalStorageGet(key) {
    try { return localStorage.getItem(key); } catch (err) { return null; }
  }

  function safeLocalStorageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (err) { /* never fatal */ }
  }

  function logIssue(msg) {
    console.warn("[play]", msg);
  }

  // Everything __play.errors() reports: compile, link, runtime and watchdog issues.
  function recordError(kind, id, message) {
    state.errors.push({ kind: kind, id: id || null, message: String(message), at: Math.round(performance.now()) });
    if (state.errors.length > 200) state.errors.shift();
  }

  // ---------------------------------------------------------- DOM cache --

  var canvas, video, stageEl, layoutEl, bannerEl, bannerTextEl;
  var playBtn, loopBtn, seekEl, timeCurEl, timeDurEl, fullscreenBtn, ejectBtn;
  var midiBtn, midiStatusEl, audioStatusEl, rackBtn, performBtn;
  var presetListEl, presetCountEl, presetNoteEl, prevBtn, nextBtn, randomBtn, xfadeBtn, blackoutBtn, rescanBtn;
  var tagPresetEl, tagFadeEl, tagBlackoutEl, toastEl, toastNameEl, toastAuthorEl, perfHintEl;
  var hudFpsEl, hudPresetEl, hudCompileEl, hudFeedbackEl, hudAudioEl, hudMidiEl, hudLatencyEl,
      hudFramesEl, hudClockEl, hudTakeEl, shaderLogEl, scaleBtn;
  var sourceSelEl, pinBtn, deviceSelEl, inputsBtn, audioNoteEl;
  var macroListEl, triggerGridEl, mapListEl, mapStatusEl, clearMapBtn;
  var libSearchEl, libListEl;
  var meterEls = {};
  var macroRows = {};
  var triggerEls = {};

  function byId(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function cacheDom() {
    canvas = byId("gl");
    video = byId("video");
    stageEl = byId("stage");
    layoutEl = byId("layout");
    bannerEl = byId("banner");
    bannerTextEl = byId("banner-text");

    playBtn = byId("btn-play");
    loopBtn = byId("btn-loop");
    seekEl = byId("seek");
    timeCurEl = byId("time-cur");
    timeDurEl = byId("time-dur");
    fullscreenBtn = byId("btn-fullscreen");
    ejectBtn = byId("btn-eject");

    midiBtn = byId("btn-midi");
    midiStatusEl = byId("midi-status");
    audioStatusEl = byId("audio-status");
    rackBtn = byId("btn-rack");
    performBtn = byId("btn-perform");

    presetListEl = byId("preset-list");
    presetCountEl = byId("preset-count");
    presetNoteEl = byId("preset-note");
    prevBtn = byId("btn-prev");
    nextBtn = byId("btn-next");
    randomBtn = byId("btn-random");
    xfadeBtn = byId("btn-xfade");
    blackoutBtn = byId("btn-blackout");
    rescanBtn = byId("btn-rescan");

    tagPresetEl = byId("tag-preset");
    tagFadeEl = byId("tag-fade");
    tagBlackoutEl = byId("tag-blackout");
    toastEl = byId("perf-toast");
    toastNameEl = byId("perf-toast-name");
    toastAuthorEl = byId("perf-toast-author");
    perfHintEl = byId("perf-hint");

    hudFpsEl = byId("hud-fps");
    hudPresetEl = byId("hud-preset");
    hudCompileEl = byId("hud-compile");
    hudFeedbackEl = byId("hud-feedback");
    hudAudioEl = byId("hud-audio");
    hudMidiEl = byId("hud-midi");
    hudLatencyEl = byId("hud-latency");
    hudFramesEl = byId("hud-frames");
    hudClockEl = byId("hud-clock");
    hudTakeEl = byId("hud-take");
    shaderLogEl = byId("shader-log");
    scaleBtn = byId("btn-scale");

    sourceSelEl = byId("audio-source");
    pinBtn = byId("btn-pin");
    deviceSelEl = byId("audio-device");
    inputsBtn = byId("btn-inputs");
    audioNoteEl = byId("audio-note");

    macroListEl = byId("macro-list");
    triggerGridEl = byId("trigger-grid");
    mapListEl = byId("map-list");
    mapStatusEl = byId("map-status");
    clearMapBtn = byId("btn-clear-map");

    libSearchEl = byId("lib-search");
    libListEl = byId("lib-list");

    var meters = document.querySelectorAll(".meter");
    for (var i = 0; i < meters.length; i++) {
      meterEls[meters[i].getAttribute("data-meter")] = {
        fill: meters[i].querySelector(".meter-fill"),
        val: meters[i].querySelector(".meter-val")
      };
    }
  }

  function setBanner(text) {
    bannerTextEl.textContent = text;
    bannerEl.hidden = false;
  }

  function hideBanner() {
    bannerEl.hidden = true;
    bannerTextEl.textContent = "";
  }

  // -------------------------------------------------------------- GL -----

  function createTexture(gl, filter) {
    var tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    return tex;
  }

  function compileShaderSync(gl, type, src) {
    var sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      var log = gl.getShaderInfoLog(sh) || "unknown shader compile error";
      gl.deleteShader(sh);
      throw new Error(log);
    }
    return sh;
  }

  // Built-in programs link synchronously: the first frame needs them.
  function linkProgramSync(gl, fsSrc) {
    var vs = compileShaderSync(gl, gl.VERTEX_SHADER, VERT_SRC);
    var fs;
    try {
      fs = compileShaderSync(gl, gl.FRAGMENT_SHADER, fsSrc);
    } catch (err) {
      gl.deleteShader(vs);
      throw err;
    }
    var prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    var ok = gl.getProgramParameter(prog, gl.LINK_STATUS);
    var log = ok ? "" : (gl.getProgramInfoLog(prog) || "unknown link error");
    gl.detachShader(prog, vs);
    gl.detachShader(prog, fs);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!ok) {
      gl.deleteProgram(prog);
      throw new Error(log);
    }
    return prog;
  }

  // Presets compile without blocking the render loop when KHR_parallel_shader_compile exists
  // (a rescan mid-performance must not stall a frame). Rejects with err.kind "compile" or "link".
  function compileProgramAsync(gl, fsSrc) {
    return new Promise(function (resolve, reject) {
      var vs = gl.createShader(gl.VERTEX_SHADER);
      var fs = gl.createShader(gl.FRAGMENT_SHADER);
      gl.shaderSource(vs, VERT_SRC);
      gl.compileShader(vs);
      gl.shaderSource(fs, fsSrc);
      gl.compileShader(fs);
      var prog = gl.createProgram();
      gl.attachShader(prog, vs);
      gl.attachShader(prog, fs);
      gl.linkProgram(prog);
      var ext = state.parallelExt;

      function finish() {
        if (gl.isContextLost()) { reject(new Error("WebGL context lost during compile")); return; }
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
          var kind = "link";
          var log = "";
          if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
            kind = "compile";
            log = gl.getShaderInfoLog(fs) || "";
          } else if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
            kind = "compile";
            log = gl.getShaderInfoLog(vs) || "";
          } else {
            log = gl.getProgramInfoLog(prog) || "";
          }
          gl.deleteProgram(prog);
          gl.deleteShader(vs);
          gl.deleteShader(fs);
          var e = new Error(log || (kind + " failed without a log"));
          e.kind = kind;
          reject(e);
          return;
        }
        gl.detachShader(prog, vs);
        gl.detachShader(prog, fs);
        gl.deleteShader(vs);
        gl.deleteShader(fs);
        resolve(prog);
      }

      if (!ext) { finish(); return; }
      (function poll() {
        if (gl.isContextLost()) { reject(new Error("WebGL context lost during compile")); return; }
        if (gl.getProgramParameter(prog, ext.COMPLETION_STATUS_KHR)) finish();
        else setTimeout(poll, 10);
      })();
    });
  }

  function cacheUniforms(gl, prog) {
    var u = {};
    for (var i = 0; i < UNIFORM_NAMES.length; i++) {
      u[UNIFORM_NAMES[i]] = gl.getUniformLocation(prog, UNIFORM_NAMES[i]);
    }
    gl.useProgram(prog);
    if (u.u_video) gl.uniform1i(u.u_video, 0);
    if (u.u_prev) gl.uniform1i(u.u_prev, 1);
    if (u.u_audio) gl.uniform1i(u.u_audio, 2);
    return u;
  }

  function initGL() {
    var gl = state.gl || canvas.getContext("webgl2", {
      alpha: false, antialias: false, depth: false, stencil: false,
      premultipliedAlpha: false, preserveDrawingBuffer: false, powerPreference: "high-performance"
    });
    if (!gl) {
      setBanner("WebGL2 unavailable — Play needs Chrome with WebGL2");
      recordError("runtime", null, "WebGL2 is unavailable in this browser");
      return false;
    }
    state.gl = gl;
    state.parallelExt = gl.getExtension("KHR_parallel_shader_compile");
    var half = gl.getExtension("EXT_color_buffer_half_float");
    var full = gl.getExtension("EXT_color_buffer_float");
    if (half || full) {
      state.fbInternal = gl.RGBA16F;
      state.fbType = gl.HALF_FLOAT;
      state.fbFormat = "RGBA16F";
    } else {
      state.fbInternal = gl.RGBA8;
      state.fbType = gl.UNSIGNED_BYTE;
      state.fbFormat = "RGBA8";
    }
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);

    state.videoTex = createTexture(gl, gl.LINEAR);
    state.videoUploaded = false;
    state.blackTex = createTexture(gl, gl.LINEAR); // every texture a preset sees: CLAMP_TO_EDGE + LINEAR
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
    state.audioTex = createTexture(gl, gl.LINEAR);
    resetAudioBytes();
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, AUDIO_TEX_W, 2, 0, gl.RED, gl.UNSIGNED_BYTE, state.audioBytes);
    state.pool = [];

    try {
      state.blitProg = linkProgramSync(gl, BLIT_FRAG_SRC);
      state.blitU = {
        a: gl.getUniformLocation(state.blitProg, "u_a"),
        b: gl.getUniformLocation(state.blitProg, "u_b"),
        mix: gl.getUniformLocation(state.blitProg, "u_mix"),
        gain: gl.getUniformLocation(state.blitProg, "u_gain")
      };
      gl.useProgram(state.blitProg);
      gl.uniform1i(state.blitU.a, 0);
      gl.uniform1i(state.blitU.b, 1);
    } catch (err) {
      state.blitProg = null;
      recordError("compile", "blit", errText(err));
      setBanner("the built-in blit shader failed to compile — see the HUD");
    }

    var b = state.builtin;
    try {
      b.program = linkProgramSync(gl, PASSTHROUGH_FRAG_SRC);
      b.uniforms = cacheUniforms(gl, b.program);
      b.status = "ok";
      b.log = "";
      b.problem = null;
    } catch (err) {
      b.program = null;
      b.status = "broken";
      b.log = errText(err);
      b.problem = firstLine(b.log);
      recordError("compile", BUILTIN_ID, b.log);
    }
    return true;
  }

  // ------------------------------------------------ feedback framebuffers --

  function createPair(w, h) {
    var gl = state.gl;
    var pair = { w: w, h: h, texs: [], fbos: [], read: 0 };
    for (var i = 0; i < 2; i++) {
      var tex = createTexture(gl, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, state.fbInternal, w, h, 0, gl.RGBA, state.fbType, null);
      var fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      pair.texs.push(tex);
      pair.fbos.push(fbo);
    }
    var complete = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    if (!complete && state.fbInternal !== gl.RGBA8) {
      deletePair(pair);
      recordError("runtime", null, "RGBA16F framebuffer incomplete; feedback falls back to RGBA8");
      state.fbInternal = gl.RGBA8;
      state.fbType = gl.UNSIGNED_BYTE;
      state.fbFormat = "RGBA8";
      return createPair(w, h);
    }
    clearPair(pair);
    return pair;
  }

  function deletePair(pair) {
    var gl = state.gl;
    if (!gl || !pair) return;
    for (var i = 0; i < pair.texs.length; i++) gl.deleteTexture(pair.texs[i]);
    for (var j = 0; j < pair.fbos.length; j++) gl.deleteFramebuffer(pair.fbos[j]);
  }

  function clearPair(pair) {
    var gl = state.gl;
    gl.clearColor(0, 0, 0, 1);
    for (var i = 0; i < 2; i++) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, pair.fbos[i]);
      gl.viewport(0, 0, pair.w, pair.h);
      gl.clear(gl.COLOR_BUFFER_BIT);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    pair.read = 0;
  }

  function takePair(w, h) {
    for (var i = 0; i < state.pool.length; i++) {
      if (state.pool[i].w === w && state.pool[i].h === h) {
        var pair = state.pool.splice(i, 1)[0];
        clearPair(pair);
        return pair;
      }
    }
    return createPair(w, h);
  }

  function releaseFb(p) {
    if (!p || !p.fb) return;
    state.pool.push(p.fb);
    p.fb = null;
    while (state.pool.length > 2) deletePair(state.pool.shift());
  }

  function dropPool() {
    for (var i = 0; i < state.pool.length; i++) deletePair(state.pool[i]);
    state.pool = [];
  }

  // A preset's pair exists at the canvas backing size; a new or resized pair starts black.
  function ensureFb(p) {
    var w = state.width, h = state.height;
    if (p.fb && (p.fb.w !== w || p.fb.h !== h)) {
      deletePair(p.fb);
      p.fb = null;
    }
    if (!p.fb) {
      p.fb = takePair(w, h);
      p.needsClear = false;
    } else if (p.needsClear) {
      clearPair(p.fb);
      p.needsClear = false;
    }
  }

  // ------------------------------------------------------- preset model --

  function makePreset(info) {
    return {
      id: String(info.id),
      name: info.name || String(info.id),
      author: info.author || "",
      tags: Array.isArray(info.tags) ? info.tags.slice() : [],
      params: Array.isArray(info.params) ? info.params.slice() : [],
      problems: Array.isArray(info.problems) ? info.problems.slice() : [],
      url: info.url || null,
      builtin: !!info.builtin,
      source: null,
      status: "pending",
      log: "",
      problem: null,
      program: null,
      uniforms: null,
      fb: null,
      needsClear: false,
      frame: 0,
      knobs: [0, 0, 0, 0, 0, 0, 0, 0],
      compileToken: 0
    };
  }

  function knobDefaults(p) {
    var k = [0, 0, 0, 0, 0, 0, 0, 0];
    for (var i = 0; i < p.params.length; i++) {
      var pr = p.params[i];
      if (pr && pr.k >= 1 && pr.k <= 8 && typeof pr.default === "number") k[pr.k - 1] = clamp(pr.default, 0, 1);
    }
    return k;
  }

  function paramName(p, k) {
    if (!p) return null;
    for (var i = 0; i < p.params.length; i++) {
      if (p.params[i] && p.params[i].k === k) return p.params[i].name;
    }
    return null;
  }

  function findPreset(id) {
    for (var i = 0; i < state.presets.length; i++) {
      if (state.presets[i].id === id) return state.presets[i];
    }
    return null;
  }

  function markBroken(p, log, errorKind) {
    p.status = "broken";
    p.log = String(log || "broken").replace(/\u0000/g, "").trim() || "broken"; // ANGLE logs end in a NUL
    p.problem = firstLine(p.log) || "broken";
    if (p.program && state.gl) state.gl.deleteProgram(p.program);
    p.program = null;
    p.uniforms = null;
    if (errorKind) recordError(errorKind, p.id, p.log);
    if (state.pendingSelect === p) state.pendingSelect = null;
    if (state.restoreSelect === p) state.restoreSelect = null;
    if (state.active === p) selectPreset(state.builtin, "auto", 0);
    if (state.fadeFrom === p) state.fadeFrom = null;
    releaseFb(p);
  }

  // ----------------------------------------------------- preset loading --

  var presetsErrorRecorded = false;

  function loadPresetList() {
    clearTimeout(state.presetsRetryTimer);
    state.presetsRetryTimer = null;
    return fetch("/api/presets", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        state.presetsStatus = "ok";
        state.presetsError = null;
        applyPresetList(Array.isArray(data && data.presets) ? data.presets : []);
      })
      .catch(function (err) {
        state.presetsStatus = "error";
        state.presetsError = errText(err);
        logIssue("preset list unavailable: " + state.presetsError);
        if (!presetsErrorRecorded) {
          presetsErrorRecorded = true;
          recordError("runtime", null, "GET /api/presets failed: " + state.presetsError);
        }
        if (state.presets.length <= 1) state.presetsRetryTimer = setTimeout(loadPresetList, PRESET_RETRY_MS);
        renderPresetList();
      });
  }

  function applyPresetList(list) {
    var existing = {};
    state.presets.forEach(function (p) { if (!p.builtin) existing[p.id] = p; });
    var next = [state.builtin];
    var seen = {};
    list.forEach(function (info) {
      if (!info || typeof info.id !== "string" || seen[info.id]) return;
      seen[info.id] = true;
      var p = existing[info.id];
      if (!p) {
        p = makePreset(info);
      } else {
        p.name = info.name || info.id;
        p.author = info.author || "";
        p.tags = Array.isArray(info.tags) ? info.tags.slice() : [];
        p.params = Array.isArray(info.params) ? info.params.slice() : [];
        p.problems = Array.isArray(info.problems) ? info.problems.slice() : [];
        p.url = info.url || null;
      }
      if (info.id === BUILTIN_ID) p.problems.push("the id 'builtin' is reserved for the page's Passthrough preset");
      next.push(p);
    });
    state.presets.forEach(function (p) {
      if (p.builtin || seen[p.id]) return;
      p.compileToken++;
      if (p.program && state.gl) state.gl.deleteProgram(p.program);
      p.program = null;
      if (state.active === p) selectPreset(state.builtin, "auto", 0);
      if (state.fadeFrom === p) state.fadeFrom = null;
      releaseFb(p);
    });
    state.presets = next;
    next.forEach(function (p) {
      if (p.builtin) return;
      if (p.problems.length) {
        p.compileToken++;
        p.source = null;
        markBroken(p, p.problems.join("\n"), null);
        return;
      }
      refreshPresetSource(p);
    });
    renderPresetList();
  }

  function refreshPresetSource(p) {
    var token = ++p.compileToken;
    if (!p.url) {
      markBroken(p, "the preset has no url", null);
      return;
    }
    fetch(p.url, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("fetch failed: HTTP " + res.status);
        return res.text();
      })
      .then(function (src) {
        if (token !== p.compileToken) return;
        if (src === p.source && p.status !== "pending") { renderPresetList(); return; }
        p.source = src;
        compilePreset(p, token);
      })
      .catch(function (err) {
        if (token !== p.compileToken) return;
        p.source = null;
        markBroken(p, errText(err), "runtime");
        renderPresetList();
      });
  }

  function compilePreset(p, token) {
    var gl = state.gl;
    if (!gl || state.glLost || p.source == null) return;
    if (p.status !== "ok") p.status = "pending";
    renderPresetList();
    compileProgramAsync(gl, p.source).then(function (prog) {
      if (token !== p.compileToken || state.glLost) { if (!gl.isContextLost()) gl.deleteProgram(prog); return; }
      if (p.program) gl.deleteProgram(p.program);
      p.program = prog;
      p.uniforms = cacheUniforms(gl, prog);
      p.status = "ok";
      p.log = "";
      p.problem = null;
      if (state.pendingSelect === p) {
        state.pendingSelect = null;
        selectPreset(p, "click");
      } else if (state.restoreSelect === p) {
        state.restoreSelect = null;
        selectPreset(p, "auto", 0);
      }
      renderPresetList();
    }).catch(function (err) {
      if (token !== p.compileToken || state.glLost) return;
      markBroken(p, errText(err), err.kind || "compile");
      renderPresetList();
    });
  }

  function renderShaderLog() {
    var parts = [];
    state.presets.forEach(function (p) {
      if (p.status === "broken") parts.push(p.id + ": " + p.log);
    });
    shaderLogEl.hidden = !parts.length;
    shaderLogEl.textContent = parts.join("\n\n");
  }

  function renderPresetList() {
    if (!presetListEl) return;
    presetListEl.innerHTML = "";
    var ok = 0, broken = 0, pending = 0;
    state.presets.forEach(function (p, idx) {
      if (p.status === "ok") ok++;
      else if (p.status === "broken") broken++;
      else pending++;
      var li = el("li", "preset-item status-" + p.status +
        (p.status === "broken" ? " broken" : "") +
        (p === state.active ? " active" : "") +
        (p === state.fadeFrom ? " fading" : ""));
      li.setAttribute("data-preset-id", p.id);
      li.setAttribute("data-status", p.status);
      li.tabIndex = 0;
      var statusText = p.builtin ? "built-in" : (p.status === "ok" ? "ok" : (p.status === "pending" ? "compiling" : "broken"));
      li.appendChild(el("span", "preset-slot", String(idx + 1)));
      li.appendChild(el("span", "preset-name", p.name));
      li.appendChild(el("span", "preset-meta", (p.author || "—") + " · " + statusText));
      if (p.status === "broken") {
        li.appendChild(el("span", "preset-problem", p.problem || "broken"));
        li.title = p.log;
      } else {
        li.title = p.name + (p.author ? " by " + p.author : "") + (p.tags.length ? " · " + p.tags.join(", ") : "");
      }
      li.addEventListener("click", function () { onPresetClick(p); });
      li.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); onPresetClick(p); }
      });
      presetListEl.appendChild(li);
    });
    presetCountEl.textContent = ok + " ok" + (broken ? " · " + broken + " broken" : "") + (pending ? " · " + pending + " compiling" : "");
    var note = "";
    if (state.presetsStatus === "loading") note = "loading presets…";
    else if (state.presetsStatus === "error") {
      note = "preset list unavailable (" + state.presetsError + ")" + (state.presetsRetryTimer ? ", retrying" : "") + "; Passthrough still runs";
    } else if (state.presets.length === 1) {
      note = "no presets in arsenal/web/presets yet; Passthrough runs. Rescan when authors finish.";
    }
    presetNoteEl.textContent = note;
    renderShaderLog();
  }

  // --------------------------------------------------- preset selection --

  var K_UNIFORMS = ["u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8"];

  function onPresetClick(p) {
    return requestPreset(p, "click");
  }

  // The one path every UI surface uses: list click, keys, MIDI triggers and __play.select.
  function requestPreset(p, reason) {
    if (!p) return false;
    if (p.status === "broken") {
      presetNoteEl.textContent = p.name + " is broken: " + (p.problem || "see the HUD log");
      return false;
    }
    if (p.status === "pending") {
      state.pendingSelect = p;
      presetNoteEl.textContent = p.name + " is still compiling; it shows when ready";
      return true;
    }
    return selectPreset(p, reason);
  }

  function fadeProgress(now) {
    if (!state.fadeFrom || state.fadeMs <= 0) return 1;
    return clamp((now - state.fadeStart) / state.fadeMs, 0, 1);
  }

  // reason: "init" (no event), "auto" (recorded if a take is open), anything else is a user
  // switch, which also opens a take. A switch in the middle of a crossfade keeps whichever
  // preset dominates the screen as the outgoing one, so the jump is at most half a fade.
  function selectPreset(p, reason, xfadeOverride) {
    if (!p || p.status !== "ok" || !p.program) return false;
    if (p === state.active) return true;
    var now = performance.now();
    var prevActive = state.active;
    var prevFrom = state.fadeFrom;
    var outgoing = prevActive;
    if (prevFrom && prevFrom !== p && fadeProgress(now) < 0.5) outgoing = prevFrom;
    if (prevFrom && prevFrom !== p && prevFrom !== outgoing) releaseFb(prevFrom);
    if (prevActive && prevActive !== p && prevActive !== outgoing) releaseFb(prevActive);

    var continuing = p === prevFrom && !!p.fb;
    state.active = p;
    if (state.pendingSelect && state.pendingSelect !== p && reason !== "auto") state.pendingSelect = null;
    if (!continuing) {
      p.knobs = knobDefaults(p);
      p.frame = 0;
      p.needsClear = true;
    }

    var ms = typeof xfadeOverride === "number" ? xfadeOverride : state.xfadeMs;
    if (reason === "init") ms = 0;
    if (ms > 0 && outgoing && outgoing !== p && outgoing.program && state.gl && !state.glLost) {
      state.fadeFrom = outgoing;
      state.fadeStart = now;
      state.fadeMs = ms;
    } else {
      if (outgoing && outgoing !== p) releaseFb(outgoing);
      state.fadeFrom = null;
      state.fadeMs = 0;
      ms = 0;
    }

    if (reason !== "init") {
      state.presetSwitches++;
      if (reason !== "auto") ensureTakeOpen();
      enqueueEvent({ kind: "preset", t: nowRef(), id: p.id, from: prevActive ? prevActive.id : null, xfade_ms: ms });
      showToast(p);
    }
    syncMacroUi();
    renderPresetList();
    updateStageTags();
    return true;
  }

  function selectByPosition(n, reason) {
    return requestPreset(state.presets[n - 1], reason);
  }

  function stepPreset(dir, reason) {
    var list = state.presets;
    var n = list.length;
    if (!n) return false;
    var start = Math.max(0, list.indexOf(state.active));
    for (var i = 1; i <= n; i++) {
      var p = list[(start + dir * i + n * n) % n];
      if (p.status === "ok" && p !== state.active) return selectPreset(p, reason);
    }
    return false;
  }

  function randomPreset(reason) {
    var choices = state.presets.filter(function (p) { return p.status === "ok" && p !== state.active; });
    if (!choices.length) return false;
    return selectPreset(choices[Math.floor(Math.random() * choices.length)], reason);
  }

  function setXfadeMs(ms, origin) {
    state.xfadeMs = clamp(Math.round(ms), 0, XFADE_MAX_MS);
    xfadeBtn.textContent = state.xfadeMs > 0 ? "XFade " + state.xfadeMs + "ms" : "Cut";
    xfadeBtn.setAttribute("aria-pressed", String(state.xfadeMs > 0));
    if (origin !== "init") emitParam("xfade", state.xfadeMs);
    syncMacroValue("xfade");
  }

  function toggleXfade() {
    setXfadeMs(state.xfadeMs > 0 ? 0 : XFADE_DEFAULT_MS, "key");
  }

  function toggleBlackout() {
    state.blackout = !state.blackout;
    blackoutBtn.setAttribute("aria-pressed", String(state.blackout));
    emitParam("blackout", state.blackout ? 1 : 0);
    updateStageTags();
  }

  function updateStageTags() {
    var p = state.active;
    tagPresetEl.textContent = p ? p.name : "—";
    tagFadeEl.hidden = !state.fadeFrom;
    if (state.fadeFrom) tagFadeEl.textContent = "fade from " + state.fadeFrom.name;
    tagBlackoutEl.hidden = !state.blackout;
  }

  function showToast(p) {
    if (!state.perf || !p) return;
    toastNameEl.textContent = p.name;
    toastAuthorEl.textContent = p.author ? "by " + p.author : (p.builtin ? "built-in" : "");
    toastEl.classList.add("show");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, TOAST_MS);
  }

  // --------------------------------------------------------- frame loop --

  function hasClip() {
    return !!(state.clip || state.blobFile);
  }

  function videoIsBound() {
    return hasClip() && state.videoUploaded && video.videoWidth > 0;
  }

  function resizeCanvasIfNeeded() {
    var rect = stageEl.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
    var w = Math.max(1, Math.round(rect.width * dpr * state.backingScale));
    var h = Math.max(1, Math.round(rect.height * dpr * state.backingScale));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      dropPool(); // presets reallocate at the new size, starting black, on their next render
    }
    state.width = canvas.width;
    state.height = canvas.height;
  }

  function uploadVideoIfNeeded() {
    if (!hasClip() || video.readyState < 2 || !video.videoWidth) return;
    var fresh = state.videoFrameReady || !state.videoUploaded || !("requestVideoFrameCallback" in video);
    if (!fresh) return;
    state.videoFrameReady = false;
    var gl = state.gl;
    gl.bindTexture(gl.TEXTURE_2D, state.videoTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    try {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);
      state.videoUploaded = true;
    } catch (err) {
      // a frame mid-seek can throw; keep whatever the texture already holds
    }
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  }

  function uploadAudioTexture() {
    var gl = state.gl;
    gl.bindTexture(gl.TEXTURE_2D, state.audioTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, AUDIO_TEX_W, 2, gl.RED, gl.UNSIGNED_BYTE, state.audioBytes);
  }

  function renderPreset(p, fc) {
    var gl = state.gl;
    if (!p || !p.program) return false;
    ensureFb(p);
    var fb = p.fb;
    var read = fb.read;
    var write = 1 - read;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb.fbos[write]);
    gl.viewport(0, 0, fb.w, fb.h);
    gl.useProgram(p.program);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, fc.hasVideo ? state.videoTex : state.blackTex);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, fb.texs[read]);
    gl.activeTexture(gl.TEXTURE2);
    gl.bindTexture(gl.TEXTURE_2D, state.audioTex);

    // Every uniform on every frame; a null location (optimised out) is a no-op.
    var u = p.uniforms;
    gl.uniform2f(u.u_res, fb.w, fb.h);
    gl.uniform2f(u.u_video_res, fc.videoW, fc.videoH);
    gl.uniform1f(u.u_time, fc.time);
    gl.uniform1f(u.u_media_time, fc.mediaTime);
    gl.uniform1f(u.u_frame, p.frame);
    gl.uniform1f(u.u_has_video, fc.hasVideo ? 1 : 0);
    gl.uniform1f(u.u_pulse, state.pulseEnv.value);
    gl.uniform1f(u.u_beat, state.beat);
    gl.uniform1f(u.u_level, state.feat.level);
    gl.uniform1f(u.u_bass, state.feat.bass);
    gl.uniform1f(u.u_mid, state.feat.mid);
    gl.uniform1f(u.u_high, state.feat.high);
    gl.uniform1f(u.u_flux, state.feat.flux);
    gl.uniform1f(u.u_hue, state.params.hue);
    gl.uniform1f(u.u_intensity, state.params.intensity);
    for (var k = 0; k < 8; k++) gl.uniform1f(u[K_UNIFORMS[k]], p.knobs[k]);

    gl.drawArrays(gl.TRIANGLES, 0, 3);
    fb.read = write;
    p.frame++;
    return true;
  }

  function present(fc) {
    var gl = state.gl;
    var b = state.active;
    var a = state.fadeFrom && state.fadeFrom.fb ? state.fadeFrom : b;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, state.width, state.height);
    if (!state.blitProg || !b || !b.fb) {
      gl.clearColor(0, 0, 0, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      return;
    }
    gl.useProgram(state.blitProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, a.fb.texs[a.fb.read]);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, b.fb.texs[b.fb.read]);
    gl.uniform1f(state.blitU.mix, a === b ? 1.0 : fc.fade);
    gl.uniform1f(state.blitU.gain, state.blackout ? 0.0 : 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  var frameErrorRecorded = false;

  function onAnimationFrame(rafNow) {
    requestAnimationFrame(onAnimationFrame);
    var gap = state.lastRafNow ? rafNow - state.lastRafNow : 0;
    state.lastRafNow = rafNow;
    var dt = clamp(gap / 1000, 0, 0.1);
    trackFrameTiming(gap, rafNow);

    var mediaTime = hasClip() ? (video.currentTime || 0) : 0;
    if (hasClip() && !("requestVideoFrameCallback" in video)) checkEpochTriggers(mediaTime);

    updateAudio(dt, mediaTime);

    if (state.gl && !state.glLost && state.active) {
      try {
        resizeCanvasIfNeeded();
        uploadVideoIfNeeded();
        uploadAudioTexture();
        var hasVideo = videoIsBound();
        var fade = 1;
        if (state.fadeFrom) {
          fade = fadeProgress(performance.now());
          if (fade >= 1) {
            releaseFb(state.fadeFrom);
            state.fadeFrom = null;
            renderPresetList();
            updateStageTags();
          }
        }
        var fc = {
          time: rafNow / 1000,
          mediaTime: mediaTime,
          hasVideo: hasVideo,
          videoW: hasVideo ? video.videoWidth : 1,
          videoH: hasVideo ? video.videoHeight : 1,
          fade: fade
        };
        if (state.fadeFrom) renderPreset(state.fadeFrom, fc);
        renderPreset(state.active, fc);
        present(fc);
      } catch (err) {
        if (!frameErrorRecorded) {
          frameErrorRecorded = true;
          recordError("runtime", state.active && state.active.id, "render: " + errText(err));
          console.error("[play] render error", err);
        }
      }
    }
    drainLatency(rafNow);
    if (!state.perf) updateMeterFills();
  }

  var intervalCache = 1000 / 60;

  function frameInterval() {
    return intervalCache;
  }

  // fps over one-second windows, a render-loop dropped-frame estimate, and First Light's
  // watchdog: 20 consecutive frames slower than twice the 60 Hz budget halve the backing scale
  // (minimum 0.5). Frames are timed gap to gap, because GPU work never shows up in JS draw time;
  // a gap over 250 ms is a stall or a hidden tab, not a slow frame.
  function trackFrameTiming(gap, rafNow) {
    if (!state.fpsWindowStart) state.fpsWindowStart = rafNow;
    state.fpsCount++;
    if (rafNow - state.fpsWindowStart >= 1000) {
      state.fps = (state.fpsCount * 1000) / (rafNow - state.fpsWindowStart);
      state.fpsCount = 0;
      state.fpsWindowStart = rafNow;
    }
    if (gap <= 0) return;
    if (gap > 250) {
      state.slowStreak = 0;
      return;
    }
    state.gapHist.push(gap);
    if (state.gapHist.length > 120) state.gapHist.shift();
    if (state.gapHist.length % 30 === 0) intervalCache = clamp(percentile(state.gapHist, 50), 4, 50);
    var frames = Math.max(1, Math.round(gap / intervalCache));
    state.renderTotal += frames;
    if (gap > intervalCache * 1.5) state.renderDropped += frames - 1;

    if (gap > FRAME_BUDGET_MS * 2) {
      state.slowStreak++;
      if (state.slowStreak >= WATCHDOG_STREAK) {
        state.slowStreak = 0;
        if (state.backingScale > BACKING_SCALE_MIN) {
          state.backingScale = Math.max(BACKING_SCALE_MIN, state.backingScale / 2);
          var msg = "20 slow frames in a row; backing scale reduced to " + state.backingScale.toFixed(2);
          recordError("watchdog", state.active && state.active.id, msg);
          logIssue("watchdog: " + msg);
        }
      }
    } else {
      state.slowStreak = 0;
    }
  }

  function drainLatency(rafNow) {
    if (!state.pendingLatency.length) return;
    var meta = state.videoFrameMeta;
    var shownAt = meta && meta.at === rafNow ? meta.expectedDisplayTime : rafNow + frameInterval();
    for (var i = 0; i < state.pendingLatency.length; i++) {
      pushLatencySample(shownAt - state.pendingLatency[i]);
    }
    state.pendingLatency.length = 0;
  }

  // rVFC flags a fresh video frame for upload and carries First Light's epoch checks. The
  // generation stamp stops a superseded chain after a clip change.
  function scheduleVideoFrame(gen) {
    if (!("requestVideoFrameCallback" in video)) return;
    video.requestVideoFrameCallback(function (now, meta) {
      if (gen !== state.rvfcGen) return;
      state.videoFrameReady = true;
      state.videoFrameMeta = { at: now, expectedDisplayTime: meta.expectedDisplayTime, mediaTime: meta.mediaTime };
      checkEpochTriggers(meta.mediaTime);
      scheduleVideoFrame(gen);
    });
  }

  function restartVideoFrameChain() {
    state.rvfcGen++;
    scheduleVideoFrame(state.rvfcGen);
  }

  function checkEpochTriggers(mediaTime) {
    if (state.justSeeked || video.seeking) {
      if (!video.seeking) state.justSeeked = false;
      state.lastMediaTime = mediaTime;
      return;
    }
    if (state.lastMediaTime != null && state.lastMediaTime - mediaTime > 0.5) bumpEpoch("loop", mediaTime);
    state.lastMediaTime = mediaTime;
  }

  // ------------------------------------------------------- context loss --

  function wireContextEvents() {
    canvas.addEventListener("webglcontextlost", function (e) {
      e.preventDefault();
      state.glLost = true;
      if (hasClip()) stageEl.classList.add("gl-bypass");
      setBanner(hasClip() ? "WebGL context lost — showing the video directly (bypass)"
                          : "WebGL context lost — waiting for the GPU to restore it");
      recordError("runtime", null, "webglcontextlost");
      enqueueEvent({ kind: "degraded", t: nowRef(), reason: "context-lost" });
      state.pool = [];
      state.fadeFrom = null;
      state.presets.forEach(function (p) {
        p.program = null;
        p.uniforms = null;
        p.fb = null;
        p.compileToken++;
      });
    });
    canvas.addEventListener("webglcontextrestored", function () {
      var shown = state.active;
      initGL();
      state.glLost = false;
      stageEl.classList.remove("gl-bypass");
      state.active = state.builtin;
      state.builtin.needsClear = true;
      state.restoreSelect = shown && !shown.builtin ? shown : null;
      state.presets.forEach(function (p) {
        if (p.builtin || p.status === "broken") return;
        if (p.source == null) {
          if (p.url) refreshPresetSource(p);
          return;
        }
        p.status = "pending";
        compilePreset(p, ++p.compileToken);
      });
      if (hasClip()) bumpEpoch("restore", video.currentTime);
      enqueueEvent({ kind: "degraded", t: nowRef(), reason: "context-restored" });
      hideBanner();
      renderPresetList();
      updateStageTags();
      syncMacroUi();
    });
  }

  // --------------------------------------------------------- audio engine --

  function resetAudioBytes() {
    var b = state.audioBytes;
    for (var i = 0; i < AUDIO_TEX_W; i++) {
      b[i] = 0;                 // row 0: spectrum, silence reads 0
      b[AUDIO_TEX_W + i] = 128; // row 1: waveform, silence reads 0.5
    }
  }

  function resetAudioAnalysis() {
    state.agc = {};
    state.fluxPrimed = false;
    state.beatHist = [];
    state.beatHistSum = 0;
    state.pulseEnv = { value: 0, initialized: false };
    state.feat.level = state.feat.bass = state.feat.mid = state.feat.high = state.feat.flux = 0;
  }

  // Bins whose centre frequency i*binHz lies in [lo, hi).
  function binRange(lo, hi, binHz, n) {
    return [Math.max(0, Math.ceil(lo / binHz)), Math.min(n - 1, Math.ceil(hi / binHz) - 1)];
  }

  function ensureAudioGraph() {
    if (state.audioCtx) return state.audioCtx;
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) {
      state.audioNote = "Web Audio is unavailable in this browser";
      return null;
    }
    var ctx;
    try {
      ctx = new AC({ latencyHint: "interactive" });
    } catch (err) {
      recordError("runtime", null, "AudioContext: " + errText(err));
      return null;
    }
    var an = ctx.createAnalyser();
    an.fftSize = FFT_SIZE;
    an.smoothingTimeConstant = 0;
    var n = an.frequencyBinCount;
    var binHz = ctx.sampleRate / FFT_SIZE;
    state.audioCtx = ctx;
    state.analyser = an;
    state.freqDb = new Float32Array(n);
    state.timeBuf = new Float32Array(FFT_SIZE);
    state.prevMag = new Float32Array(n);
    state.bandBins = {
      bass: binRange(BANDS.bass[0], BANDS.bass[1], binHz, n),
      mid: binRange(BANDS.mid[0], BANDS.mid[1], binHz, n),
      high: binRange(BANDS.high[0], BANDS.high[1], binHz, n)
    };
    state.fluxBins = binRange(SPEC_LO_HZ, SPEC_HI_HZ, binHz, n);
    state.specPos = new Float32Array(AUDIO_TEX_W);
    for (var j = 0; j < AUDIO_TEX_W; j++) {
      var f = SPEC_LO_HZ * Math.pow(SPEC_HI_HZ / SPEC_LO_HZ, j / (AUDIO_TEX_W - 1));
      state.specPos[j] = Math.min(f / binHz, n - 1);
    }
    try {
      state.mediaNode = ctx.createMediaElementSource(video);
      state.mediaNode.connect(ctx.destination); // the clip is still heard
    } catch (err) {
      state.mediaNode = null;
      recordError("runtime", null, "createMediaElementSource: " + errText(err));
    }
    ctx.onstatechange = updateAudioUi;
    routeAudio();
    return ctx;
  }

  function resumeAudio() {
    var ctx = state.audioCtx;
    if (ctx && ctx.state === "suspended") ctx.resume().catch(function () {});
  }

  // The clip feeds the analyser only while it is the source; it always feeds the speakers.
  // A live input feeds the analyser and nothing else: Loopback already carries the speaker mix.
  function routeAudio() {
    var an = state.analyser;
    if (!an) return;
    if (state.mediaNode) {
      try { state.mediaNode.disconnect(an); } catch (err) { /* was not connected */ }
    }
    if (state.inputNode) {
      try { state.inputNode.disconnect(); } catch (err) { /* was not connected */ }
    }
    if (state.source === "clip" && state.mediaNode) state.mediaNode.connect(an);
    if (state.source === "input" && state.inputNode) state.inputNode.connect(an);
  }

  function inputConstraints(deviceId) {
    var c = { echoCancellation: false, noiseSuppression: false, autoGainControl: false };
    var md = navigator.mediaDevices;
    var sup = md && md.getSupportedConstraints ? md.getSupportedConstraints() : {};
    if (sup.voiceIsolation) c.voiceIsolation = false;
    if (deviceId) c.deviceId = { exact: deviceId };
    return c;
  }

  function listDevices() {
    var md = navigator.mediaDevices;
    if (!md || !md.enumerateDevices) return Promise.resolve([]);
    return md.enumerateDevices().then(function (all) {
      state.devices = all.filter(function (d) { return d.kind === "audioinput"; });
      renderDeviceSelect();
      return state.devices;
    });
  }

  function hasDeviceLabels() {
    return state.devices.some(function (d) { return !!d.label; });
  }

  // Labels stay empty until permission is granted, so ask once, then list by label.
  function ensureInputPermission() {
    var md = navigator.mediaDevices;
    if (!md || !md.getUserMedia) return Promise.reject(new Error("getUserMedia is unavailable"));
    return listDevices().then(function () {
      if (hasDeviceLabels()) return state.devices;
      return md.getUserMedia({ audio: inputConstraints(null), video: false }).then(function (stream) {
        stream.getTracks().forEach(function (t) { t.stop(); });
        return listDevices();
      });
    });
  }

  function preferredDeviceId() {
    var ids = state.devices.map(function (d) { return d.deviceId; });
    if (deviceSelEl.value && ids.indexOf(deviceSelEl.value) !== -1) return deviceSelEl.value;
    var pref = loadAudioPref();
    if (pref.deviceId && ids.indexOf(pref.deviceId) !== -1) return pref.deviceId;
    var loop = state.devices.filter(function (d) { return /loopback/i.test(d.label || ""); })[0];
    if (loop) return loop.deviceId;
    return state.devices.length ? state.devices[0].deviceId : "";
  }

  function closeInput() {
    if (state.inputNode) {
      try { state.inputNode.disconnect(); } catch (err) { /* already */ }
      state.inputNode = null;
    }
    if (state.inputStream) {
      state.inputStream.getTracks().forEach(function (t) { t.stop(); });
      state.inputStream = null;
    }
    state.inputLabel = "";
    state.inputSettings = null;
  }

  function openInput(deviceId) {
    var ctx = ensureAudioGraph();
    if (!ctx) return Promise.reject(new Error("Web Audio is unavailable"));
    resumeAudio();
    return navigator.mediaDevices.getUserMedia({ audio: inputConstraints(deviceId), video: false }).then(function (stream) {
      closeInput();
      var track = stream.getAudioTracks()[0] || null;
      state.inputStream = stream;
      state.inputNode = ctx.createMediaStreamSource(stream);
      state.inputLabel = track ? track.label : "";
      state.inputSettings = track && track.getSettings ? track.getSettings() : null;
      state.inputDeviceId = (state.inputSettings && state.inputSettings.deviceId) || deviceId || "";
      if (track) {
        track.addEventListener("ended", function () {
          state.audioNote = "input ended: " + (state.inputLabel || "device");
          updateAudioUi();
        });
      }
      return listDevices();
    });
  }

  var sourceToken = 0;

  // kind: "clip" | "input" | "analysis". opts.deviceId picks an input device.
  function setAudioSource(kind, opts) {
    opts = opts || {};
    var token = ++sourceToken;
    if (kind !== "input" && kind !== "analysis") kind = "clip";
    if (kind === "input") {
      state.audioNote = "opening the input…";
      updateAudioUi();
      return ensureInputPermission().then(function () {
        if (token !== sourceToken) return false;
        var id = opts.deviceId != null ? opts.deviceId : preferredDeviceId();
        return openInput(id).then(function () {
          if (token !== sourceToken) return false;
          applySource("input");
          return true;
        });
      }).catch(function (err) {
        if (token !== sourceToken) return false;
        state.audioNote = "input failed: " + errText(err);
        recordError("runtime", null, "audio input: " + errText(err));
        updateAudioUi();
        return false;
      });
    }
    closeInput();
    applySource(kind);
    return Promise.resolve(true);
  }

  function applySource(kind) {
    var changed = state.source !== kind || kind === "input";
    state.source = kind;
    ensureAudioGraph();
    routeAudio();
    resetAudioAnalysis();
    if (kind === "analysis") {
      startAnalysisPoll(state.clip ? state.clip.id : null);
    } else {
      state.analysisToken++;
      state.analysis = null;
      state.analysisReady = false;
      state.analysisStatus = "";
    }
    state.audioNote = kind === "input" ? describeInputSettings() : "";
    saveAudioPref();
    if (changed) {
      enqueueEvent({ kind: "audio_source", t: nowRef(), source: kind,
                     device_label: kind === "input" ? (state.inputLabel || null) : null });
    }
    updateAudioUi();
  }

  function loadAudioPref() {
    var raw = safeLocalStorageGet(AUDIO_PREF_KEY);
    if (!raw) return {};
    try {
      var o = JSON.parse(raw);
      return o && typeof o === "object" ? o : {};
    } catch (err) {
      return {};
    }
  }

  function saveAudioPref() {
    safeLocalStorageSet(AUDIO_PREF_KEY, JSON.stringify({
      source: state.source,
      deviceId: state.inputDeviceId || (deviceSelEl && deviceSelEl.value) || "",
      label: state.inputLabel || "",
      pinned: state.sourcePinned
    }));
  }

  // ------------------------------------------- analysis (server features) --

  function startAnalysisPoll(clipId) {
    state.analysis = null;
    state.analysisReady = false;
    var myToken = ++state.analysisToken;
    if (!clipId) {
      state.analysisStatus = hasClip() ? "unavailable: outside library roots" : "needs a library clip";
      updateAudioUi();
      return;
    }
    state.analysisStatus = "computing…";
    poll();

    function poll() {
      if (myToken !== state.analysisToken) return;
      fetch("/api/analysis/" + clipId, { cache: "no-store" })
        .then(function (res) {
          if (myToken !== state.analysisToken) return null;
          if (res.status === 202) {
            return res.json().catch(function () { return {}; }).then(function (data) {
              var pct = typeof data.progress === "number" ? Math.round(data.progress * 100) : null;
              state.analysisStatus = "computing" + (pct != null ? " " + pct + "%" : "…");
              setTimeout(poll, ANALYSIS_POLL_MS);
            });
          }
          if (res.status === 200) {
            return res.json().then(function (data) {
              state.analysis = data.features;
              state.analysisReady = true;
              state.analysisStatus = "ready";
            });
          }
          return res.json().catch(function () { return {}; }).then(function (data) {
            state.analysisStatus = "unavailable: " + (data.error || ("HTTP " + res.status));
          });
        })
        .catch(function (err) {
          if (myToken !== state.analysisToken) return;
          state.analysisStatus = "unavailable: " + errText(err);
        });
    }
  }

  function sampleFeatures(mediaTime) {
    var a = state.analysis;
    if (!a || !a.frames || !a.frames.length) return null;
    var ticks = Math.round(mediaTime * ANALYSIS_TIMEBASE_DEN);
    var idx = clamp(Math.floor((ticks - a.start_ticks) / a.hop_ticks), 0, a.frames.length - 1);
    var row = a.frames[idx];
    var out = {};
    for (var i = 0; i < a.names.length; i++) out[a.names[i]] = row[i];
    return out;
  }

  // ------------------------------------------------- per-frame analysis --

  function zeroFeatures() {
    var f = state.feat;
    f.level = f.bass = f.mid = f.high = f.flux = 0;
  }

  function updateAudio(dt, mediaTime) {
    var f = state.feat;
    if (state.source === "analysis") {
      var row = state.analysisReady && hasClip() ? sampleFeatures(mediaTime) : null;
      if (row) {
        f.level = row.rms || 0;
        f.bass = row.bass || 0;
        f.mid = row.mid || 0;
        f.high = row.high || 0;
        f.flux = row.flux || 0;
      } else {
        zeroFeatures();
      }
      resetAudioBytes(); // precomputed features carry no spectrum or waveform
    } else if (state.analyser && (state.source === "clip" ? !!state.mediaNode : !!state.inputNode)) {
      analyseFrame(dt);
    } else {
      zeroFeatures();
      resetAudioBytes();
    }

    var nowMs = performance.now();
    state.beat *= Math.exp(-dt / BEAT_DECAY_S);
    detectBeat(nowMs);
    if (state.pendingBeat > 0) {
      state.beat = Math.max(state.beat, state.pendingBeat);
      state.pendingBeat = 0;
    }

    // First Light's pulse: 0.65*bass + 0.35*flux, 12 ms attack, 180 ms release
    var target = clamp(0.65 * f.bass + 0.35 * f.flux, 0, 1);
    var env = state.pulseEnv;
    var tau = target > env.value ? PULSE_ATTACK_MS : PULSE_RELEASE_MS;
    var alpha = env.initialized ? 1 - Math.exp(-dt / (tau / 1000)) : 1;
    env.value += (target - env.value) * alpha;
    env.initialized = true;
    emitParam("pulse", Math.round(env.value * 1000) / 1000);
  }

  // Per signal, relative to its own recent average, as MilkDrop does it: a 1.5 s average of linear
  // power, and value = r / (1 + r) where r = power / average. Steady sound reads 0.5 and a kick
  // stands well above it. (Peak-tracking auto-gain pinned sustained music at 1.0, so no beat could
  // stand out.) A frame under the -80 dB gate reads 0 and leaves the average alone, so silence
  // doesn't drag it down and music returns at full range. For signals passed as 20*log10 dB the
  // "power" is amplitude squared, which only sharpens the ratio.
  var REL_AVG_TAU_S = 1.5;
  function agcStep(key, db, dt) {
    var s = state.agc[key];
    if (!s) s = state.agc[key] = { avg: 0, ratio: 0 };
    if (!(db >= AGC_GATE_DB)) {
      s.ratio = 0;
      return 0;
    }
    var power = Math.pow(10, db / 10);
    if (!(s.avg > 0)) s.avg = power;
    s.avg += (power - s.avg) * (1 - Math.exp(-dt / REL_AVG_TAU_S));
    s.ratio = power / Math.max(s.avg, 1e-30);
    return clamp(s.ratio / (1 + s.ratio), 0, 1);
  }

  function bandDb(range) {
    var db = state.freqDb;
    var sum = 0, count = 0;
    for (var i = range[0]; i <= range[1]; i++) {
      if (db[i] > -1000) sum += Math.pow(10, db[i] / 10); // -Infinity is digital silence: power 0
      count++;
    }
    return 10 * Math.log10((count ? sum / count : 0) + LOG_EPS);
  }

  // At display rates above the audio callback rate (a 240 Hz screen against 10 ms audio buffers),
  // back-to-back frames can read identical audio, and flux between two identical reads is a
  // false 0 that makes the pulse flicker. Features advance only on new audio, carrying the
  // elapsed time; a buffer unchanged for 50 ms is analysed anyway, so digital silence reads as silence.
  function sameAsLastRead(td) {
    var last = state.lastTd;
    if (!last || last.length !== td.length) {
      state.lastTd = new Float32Array(td);
      return false;
    }
    for (var i = 0; i < td.length; i++) {
      if (td[i] !== last[i]) {
        last.set(td);
        return false;
      }
    }
    return true;
  }

  function analyseFrame(dt) {
    var an = state.analyser;
    var db = state.freqDb;
    var td = state.timeBuf;
    var f = state.feat;
    an.getFloatTimeDomainData(td);
    state.audioDt = (state.audioDt || 0) + dt;
    if (sameAsLastRead(td) && state.audioDt < 0.05) return;
    dt = Math.min(state.audioDt, 0.1);
    state.audioDt = 0;
    an.getFloatFrequencyData(db);

    f.bass = agcStep("bass", bandDb(state.bandBins.bass), dt);
    f.mid = agcStep("mid", bandDb(state.bandBins.mid), dt);
    f.high = agcStep("high", bandDb(state.bandBins.high), dt);

    // positive spectral flux of linear magnitude, 20 Hz to 16 kHz (dB as analysis.py: 20*log10)
    var fb = state.fluxBins;
    var prev = state.prevMag;
    var flux = 0;
    for (var i = fb[0]; i <= fb[1]; i++) {
      var m = db[i] > -1000 ? Math.pow(10, db[i] / 20) : 0;
      if (state.fluxPrimed) {
        var d = m - prev[i];
        if (d > 0) flux += d;
      }
      prev[i] = m;
    }
    state.fluxPrimed = true;
    f.flux = agcStep("flux", 20 * Math.log10(flux + LOG_EPS), dt);

    var sumSq = 0;
    for (var t = 0; t < td.length; t++) sumSq += td[t] * td[t];
    f.level = agcStep("level", 20 * Math.log10(Math.sqrt(sumSq / td.length) + LOG_EPS), dt);

    writeAudioBytes(db, td);
  }

  // u_audio row 0: 512 log-spaced columns, 20 Hz..16 kHz, linearly interpolated in dB between the
  // two nearest bins, -90..-20 dB -> 0..255. Row 1: 512 samples spread evenly over the whole
  // 2048-sample time-domain frame, -1..1 -> 0..255.
  function writeAudioBytes(db, td) {
    var bytes = state.audioBytes;
    var pos = state.specPos;
    var n = db.length;
    var span = SPEC_DB_HI - SPEC_DB_LO;
    for (var j = 0; j < AUDIO_TEX_W; j++) {
      var x = pos[j];
      var i0 = Math.floor(x);
      var i1 = Math.min(i0 + 1, n - 1);
      var d0 = db[i0] > -200 ? db[i0] : -200;
      var d1 = db[i1] > -200 ? db[i1] : -200;
      var v = (d0 + (d1 - d0) * (x - i0) - SPEC_DB_LO) / span;
      bytes[j] = v <= 0 ? 0 : (v >= 1 ? 255 : Math.round(v * 255));
    }
    var stride = td.length / AUDIO_TEX_W;
    for (var k = 0; k < AUDIO_TEX_W; k++) {
      var w = (td[Math.floor(k * stride)] + 1) * 0.5;
      bytes[AUDIO_TEX_W + k] = w <= 0 ? 0 : (w >= 1 ? 255 : Math.round(w * 255));
    }
  }

  // A beat from live audio: bass power at least 1.6x its own 1.5 s average and rising since the
  // last analysed frame, at most once per 180 ms. Precomputed analysis rows carry no power ratio,
  // so that source keeps the value-based rule below.
  var BEAT_POWER_RATIO = 1.6;
  function detectBeat(nowMs) {
    if (state.source === "analysis") return detectBeatFromValues(nowMs);
    var s = state.agc.bass;
    var ratio = s ? s.ratio : 0;
    var rising = ratio > (state.lastBassRatio || 0);
    state.lastBassRatio = ratio;
    if (ratio >= BEAT_POWER_RATIO && rising && nowMs - state.lastBeatAt >= BEAT_REFRACTORY_MS) {
      state.beat = 1;
      state.lastBeatAt = nowMs;
    }
  }

  // For precomputed analysis: bass above 0.3 and above 1.35x its moving average over the previous
  // second, at most once per 180 ms.
  function detectBeatFromValues(nowMs) {
    var hist = state.beatHist;
    var bass = state.feat.bass;
    while (hist.length && nowMs - hist[0].t > BEAT_WINDOW_MS) state.beatHistSum -= hist.shift().v;
    var avg = hist.length ? Math.max(0, state.beatHistSum / hist.length) : 0;
    if (bass > BEAT_MIN && bass > BEAT_RATIO * avg && nowMs - state.lastBeatAt >= BEAT_REFRACTORY_MS) {
      state.beat = 1;
      state.lastBeatAt = nowMs;
    }
    hist.push({ t: nowMs, v: bass });
    state.beatHistSum += bass;
  }

  // ------------------------------------------------------------ audio UI --

  function renderDeviceSelect() {
    var current = state.inputDeviceId || deviceSelEl.value || loadAudioPref().deviceId || "";
    deviceSelEl.innerHTML = "";
    if (!state.devices.length) {
      var none = el("option", null, "(no input devices)");
      none.value = "";
      deviceSelEl.appendChild(none);
      return;
    }
    var chosen = null;
    state.devices.forEach(function (d, i) {
      var opt = el("option", null, d.label || ("input " + (i + 1) + " (enable inputs for names)"));
      opt.value = d.deviceId;
      deviceSelEl.appendChild(opt);
      if (d.deviceId === current) chosen = d.deviceId;
    });
    if (!chosen) {
      var loop = state.devices.filter(function (d) { return /loopback/i.test(d.label || ""); })[0];
      chosen = loop ? loop.deviceId : state.devices[0].deviceId;
    }
    deviceSelEl.value = chosen;
    inputsBtn.hidden = hasDeviceLabels();
  }

  function describeInputSettings() {
    var s = state.inputSettings || {};
    function onOff(v) { return v === false ? "off" : (v === true ? "ON" : "n/a"); }
    return (state.inputLabel || "input") +
      (s.sampleRate ? " · " + s.sampleRate + " Hz" : "") +
      (s.channelCount ? " · " + s.channelCount + " ch" : "") +
      " · echo " + onOff(s.echoCancellation) +
      " · noise " + onOff(s.noiseSuppression) +
      " · agc " + onOff(s.autoGainControl) +
      " · analysed only, never routed to the speakers";
  }

  function audioSourceText() {
    var ctxState = state.audioCtx ? state.audioCtx.state : "not started";
    var t;
    if (state.source === "input") t = "input: " + (state.inputLabel || (state.inputNode ? "device" : "not open"));
    else if (state.source === "analysis") t = "analysis: " + (state.analysisStatus || "idle");
    else t = "clip" + (hasClip() ? (video.paused ? " (paused)" : "") : " (no clip)");
    if (state.sourcePinned) t += " · pinned";
    if (state.source !== "analysis" && ctxState !== "running") {
      t += " · audio " + ctxState + (ctxState === "suspended" ? " (click or press a key)" : "");
    }
    return t;
  }

  function updateAudioUi() {
    if (!sourceSelEl) return;
    sourceSelEl.value = state.source;
    pinBtn.setAttribute("aria-pressed", String(state.sourcePinned));
    audioNoteEl.textContent = state.audioNote || "A live input is analysed only. It is never routed to the speakers.";
    audioStatusEl.textContent = "audio: " + audioSourceText();
  }

  var METER_KEYS = ["level", "bass", "mid", "high", "flux", "beat", "pulse"];

  function meterValue(key) {
    if (key === "beat") return state.beat;
    if (key === "pulse") return state.pulseEnv.value;
    return state.feat[key] || 0;
  }

  function updateMeterFills() {
    for (var i = 0; i < METER_KEYS.length; i++) {
      var m = meterEls[METER_KEYS[i]];
      if (m) m.fill.style.transform = "scaleX(" + clamp(meterValue(METER_KEYS[i]), 0, 1).toFixed(3) + ")";
    }
  }

  function updateMeterValues() {
    for (var i = 0; i < METER_KEYS.length; i++) {
      var m = meterEls[METER_KEYS[i]];
      if (m) m.val.textContent = clamp(meterValue(METER_KEYS[i]), 0, 1).toFixed(2);
    }
  }


  // ---------------------------------------------------------------- MIDI --

  function setMidiStatusText(text) {
    midiStatusEl.textContent = text;
  }

  function connectMIDI() {
    if (MIDI.access && MIDI.input) return Promise.resolve(true);
    if (!navigator.requestMIDIAccess) {
      setMidiStatusText("MIDI: unavailable in this browser");
      return Promise.resolve(false);
    }
    return navigator.requestMIDIAccess().then(function (access) {
      MIDI.access = access;
      access.onstatechange = function () { pickMidiInput(); };
      return pickMidiInput();
    }).catch(function (err) {
      setMidiStatusText("MIDI: connect failed (" + errText(err) + ")");
      return false;
    });
  }

  // Prefer an input whose name contains "KeyLab"; otherwise the first connected input.
  function pickMidiInput() {
    var inputs = Array.from(MIDI.access.inputs.values()).filter(function (i) { return i.state !== "disconnected"; });
    var preferred = inputs.filter(function (i) { return /keylab/i.test(i.name || ""); })[0] || inputs[0] || null;
    if (!preferred) {
      if (MIDI.input) MIDI.input.onmidimessage = null;
      MIDI.input = null;
      state.midiInputName = null;
      setMidiStatusText(MIDI.access.inputs.size ? "MIDI: input disconnected" : "MIDI: no input found");
      midiBtn.setAttribute("aria-pressed", "false");
      return false;
    }
    if (MIDI.input !== preferred) setMidiInput(preferred);
    return true;
  }

  function setMidiInput(input) {
    if (MIDI.input && MIDI.input !== input) MIDI.input.onmidimessage = null;
    MIDI.input = input;
    input.onmidimessage = onMidiMessage;
    state.midiInputName = input.name || "MIDI input";
    setMidiStatusText("MIDI: " + state.midiInputName);
    midiBtn.setAttribute("aria-pressed", "true");
  }

  function onMidiMessage(ev) {
    var d = ev.data;
    if (!d || d.length < 3) return;
    var status = d[0] & 0xf0;
    var ch = (d[0] & 0x0f) + 1;
    var now = performance.now();
    var ts = typeof ev.timeStamp === "number" && ev.timeStamp > 0 && ev.timeStamp <= now + 50 ? ev.timeStamp : now;
    if (status === 0x90 && d[2] > 0) onNoteOn(ch, d[1], d[2], ts);
    else if (status === 0xb0) onControlChange(ch, d[1], d[2], ts);
  }

  function bindingsFor(type, ch, num) {
    return MIDI.bindings.filter(function (b) { return b.type === type && b.ch === ch && b.num === num; });
  }

  function bindingForTarget(target) {
    for (var i = 0; i < MIDI.bindings.length; i++) {
      if (MIDI.bindings[i].target === target) return MIDI.bindings[i];
    }
    return null;
  }

  // Defaults hold for whatever has not been learned: a learned CC does its learned job, and a
  // learned hue or intensity replaces that target's default CC.
  function onControlChange(ch, cc, value, ts) {
    state.lastControl = { type: "cc", ch: ch, num: cc, value: value };
    if (MIDI.learning && MIDI.learning.kind === "continuous") bindControl(MIDI.learning.target, "cc", ch, cc);
    var targets = bindingsFor("cc", ch, cc).map(function (b) { return b.target; });
    if (!targets.length) {
      if (cc === 1 && !bindingForTarget("hue")) targets = ["hue"];
      else if (cc === 7 && !bindingForTarget("intensity")) targets = ["intensity"];
    }
    if (!targets.length) return;
    targets.forEach(function (target) {
      var mapped = applyContinuous(target, value / 127, "midi");
      enqueueEvent({ kind: "midi", t: nowRef(), cc: cc, channel: ch, value: value, param: target, mapped: mapped });
    });
    state.pendingLatency.push(ts);
  }

  // Every note-on flashes u_beat at velocity/127; a learned note also fires its trigger.
  function onNoteOn(ch, note, velocity, ts) {
    state.lastControl = { type: "note", ch: ch, num: note, value: velocity };
    var v = velocity / 127;
    state.pendingBeat = Math.max(state.pendingBeat, v);
    var targets = [];
    if (MIDI.learning && MIDI.learning.kind === "trigger") {
      bindControl(MIDI.learning.target, "note", ch, note); // the learning press binds; it does not fire
    } else {
      targets = bindingsFor("note", ch, note).map(function (b) { return b.target; });
      targets.forEach(applyTrigger);
    }
    enqueueEvent({ kind: "midi", t: nowRef(), note: note, channel: ch, velocity: velocity,
                   param: targets.length ? targets.join(",") : "beat", mapped: targets.length ? null : v });
    state.pendingLatency.push(ts);
  }

  function applyContinuous(target, norm, origin) {
    norm = clamp(norm, 0, 1);
    var m = /^k([1-8])$/.exec(target);
    if (m) {
      if (state.active) state.active.knobs[Number(m[1]) - 1] = norm;
      emitParam(target, norm);
      syncMacroValue(target);
      return norm;
    }
    if (target === "hue") {
      state.params.hue = norm * 360;
      emitParam("hue", state.params.hue);
      syncMacroValue("hue");
      return state.params.hue;
    }
    if (target === "intensity") {
      state.params.intensity = norm;
      emitParam("intensity", norm);
      syncMacroValue("intensity");
      return norm;
    }
    if (target === "xfade") {
      setXfadeMs(norm * XFADE_MAX_MS, origin);
      return state.xfadeMs;
    }
    return null;
  }

  function applyTrigger(target) {
    if (target === "next") return stepPreset(1, "midi");
    if (target === "prev") return stepPreset(-1, "midi");
    if (target === "random") return randomPreset("midi");
    if (target === "blackout") return toggleBlackout();
    var m = /^slot(\d+)$/.exec(target);
    if (m) return selectByPosition(Number(m[1]), "midi");
    return false;
  }

  // ---------------------------------------------------------------- learn --

  function targetKind(target) {
    return CONTINUOUS_TARGETS.indexOf(target) !== -1 ? "continuous" : "trigger";
  }

  function targetLabel(target) {
    var m = /^slot(\d+)$/.exec(target);
    return m ? "slot " + m[1] : target;
  }

  function targetRange(target) {
    if (target === "hue") return [0, 360];
    if (target === "xfade") return [0, XFADE_MAX_MS];
    return [0, 1];
  }

  function describeControl(type, ch, num) {
    return (type === "cc" ? "cc" : "note ") + num + (ch !== 1 ? " ch" + ch : "");
  }

  function armLearn(target) {
    if (MIDI.learning && MIDI.learning.target === target) {
      cancelLearn();
      return;
    }
    MIDI.learning = { target: target, kind: targetKind(target) };
    mapStatusEl.textContent = (MIDI.learning.kind === "continuous" ? "move a knob or fader for " : "press a key or pad for ") +
      targetLabel(target) + "… (Esc cancels)";
    renderLearnState();
    if (!MIDI.input) {
      connectMIDI().then(function (ok) {
        if (!ok && MIDI.learning) mapStatusEl.textContent = "no MIDI input to learn from (" + midiStatusEl.textContent + ")";
      });
    }
  }

  function cancelLearn() {
    MIDI.learning = null;
    mapStatusEl.textContent = "";
    renderLearnState();
  }

  // One control does one job and one target has one control: learning replaces both.
  function bindControl(target, type, ch, num) {
    MIDI.bindings = MIDI.bindings.filter(function (b) {
      return b.target !== target && !(b.type === type && b.ch === ch && b.num === num);
    });
    MIDI.bindings.push({ target: target, type: type, ch: ch, num: num });
    MIDI.learning = null;
    mapStatusEl.textContent = "learned " + describeControl(type, ch, num) + " -> " + targetLabel(target);
    persistMappings();
    renderMapPanel();
  }

  function clearBinding(target) {
    MIDI.bindings = MIDI.bindings.filter(function (b) { return b.target !== target; });
    persistMappings();
    renderMapPanel();
  }

  function persistMappings() {
    safeLocalStorageSet(MIDI_MAP_KEY, JSON.stringify({ version: 1, bindings: MIDI.bindings }));
  }

  function loadMappings() {
    var raw = safeLocalStorageGet(MIDI_MAP_KEY);
    if (!raw) return;
    try {
      var parsed = JSON.parse(raw);
      var list = parsed && Array.isArray(parsed.bindings) ? parsed.bindings : [];
      MIDI.bindings = list.filter(function (b) {
        if (!b || typeof b !== "object") return false;
        var okTarget = (b.type === "cc" && CONTINUOUS_TARGETS.indexOf(b.target) !== -1) ||
                       (b.type === "note" && TRIGGER_TARGETS.indexOf(b.target) !== -1);
        return okTarget && b.ch >= 1 && b.ch <= 16 && b.num >= 0 && b.num <= 127;
      });
    } catch (err) {
      MIDI.bindings = []; // corrupt or foreign value: start clean
    }
  }

  function renderMapPanel() {
    mapListEl.innerHTML = "";
    MIDI.bindings.forEach(function (b) {
      var chNote = b.ch !== 1 ? "  # ch" + b.ch : "";
      var text = b.type === "cc"
        ? "map midi.cc(" + b.num + ") -> bank." + b.target + " {range: " + targetRange(b.target).join("..") + "}" + chNote
        : "map midi.note(" + b.num + ") -> bank." + b.target + chNote;
      mapListEl.appendChild(el("li", null, text));
    });
    mapListEl.appendChild(el("li", "map-default", "map midi.note(any) -> bank.beat {range: 0..1}  # default, velocity/127"));
    if (!bindingForTarget("hue")) mapListEl.appendChild(el("li", "map-default", "map midi.cc(1) -> bank.hue {range: 0..360}  # default"));
    if (!bindingForTarget("intensity")) mapListEl.appendChild(el("li", "map-default", "map midi.cc(7) -> bank.intensity {range: 0..1}  # default"));
    renderLearnState();
  }

  function renderLearnState() {
    var learning = MIDI.learning ? MIDI.learning.target : null;
    Object.keys(macroRows).forEach(function (target) {
      var row = macroRows[target];
      var b = bindingForTarget(target);
      row.chip.textContent = learning === target ? "listening" : (b ? describeControl(b.type, b.ch, b.num) : "learn");
      row.chip.classList.toggle("bound", !!b);
      row.chip.classList.toggle("listening", learning === target);
    });
    Object.keys(triggerEls).forEach(function (target) {
      var t = triggerEls[target];
      var b = bindingForTarget(target);
      t.bind.textContent = learning === target ? "listening…" : (b ? describeControl(b.type, b.ch, b.num) : "—");
      t.root.classList.toggle("bound", !!b);
      t.root.classList.toggle("listening", learning === target);
    });
  }

  // ------------------------------------------------------ macros & grid --

  var MACRO_KEYS = { intensity: "int", xfade: "xf" };
  var MACRO_NAMES = { hue: "hue", intensity: "intensity", xfade: "crossfade" };

  function buildMacroRows() {
    macroListEl.innerHTML = "";
    CONTINUOUS_TARGETS.forEach(function (target) {
      var row = el("div", "macro");
      var key = el("span", "macro-key", MACRO_KEYS[target] || target);
      var name = el("span", "macro-name", MACRO_NAMES[target] || "—");
      var range = document.createElement("input");
      range.type = "range";
      range.min = "0";
      range.max = "1000";
      range.step = "1";
      range.className = "macro-range";
      range.setAttribute("aria-label", target);
      var val = el("span", "macro-val", "");
      var chip = el("button", "learn-chip", "learn");
      chip.type = "button";
      chip.title = "Learn a MIDI CC for " + target + " (right-click clears)";
      range.addEventListener("input", function () { applyContinuous(target, Number(range.value) / 1000, "ui"); });
      chip.addEventListener("click", function () { armLearn(target); });
      chip.addEventListener("contextmenu", function (e) { e.preventDefault(); clearBinding(target); });
      row.appendChild(key);
      row.appendChild(name);
      row.appendChild(range);
      row.appendChild(val);
      row.appendChild(chip);
      macroListEl.appendChild(row);
      macroRows[target] = { row: row, name: name, range: range, val: val, chip: chip };
    });
  }

  function buildTriggerGrid() {
    triggerGridEl.innerHTML = "";
    TRIGGER_TARGETS.forEach(function (target) {
      var btn = el("button", "trigger");
      btn.type = "button";
      btn.title = "Learn a note for " + targetLabel(target) + " (right-click clears)";
      var bind = el("span", "trigger-bind", "—");
      btn.appendChild(el("span", "trigger-name", targetLabel(target)));
      btn.appendChild(bind);
      btn.addEventListener("click", function () { armLearn(target); });
      btn.addEventListener("contextmenu", function (e) { e.preventDefault(); clearBinding(target); });
      triggerGridEl.appendChild(btn);
      triggerEls[target] = { root: btn, bind: bind };
    });
  }

  function syncMacroUi() {
    var p = state.active;
    for (var k = 1; k <= 8; k++) {
      var r = macroRows["k" + k];
      if (!r) continue;
      var nm = paramName(p, k);
      r.name.textContent = nm || "—";
      r.row.classList.toggle("unnamed", !nm);
    }
    CONTINUOUS_TARGETS.forEach(syncMacroValue);
  }

  function syncMacroValue(target) {
    var r = macroRows[target];
    if (!r) return;
    var norm, text;
    var m = /^k([1-8])$/.exec(target);
    if (m) {
      norm = state.active ? state.active.knobs[Number(m[1]) - 1] : 0;
      text = norm.toFixed(2);
    } else if (target === "hue") {
      norm = state.params.hue / 360;
      text = Math.round(state.params.hue) + "°";
    } else if (target === "intensity") {
      norm = state.params.intensity;
      text = norm.toFixed(2);
    } else {
      norm = state.xfadeMs / XFADE_MAX_MS;
      text = state.xfadeMs + "ms";
    }
    if (document.activeElement !== r.range) r.range.value = String(Math.round(norm * 1000));
    r.val.textContent = text;
  }


  // ------------------------------------------------------ take / events --

  function mediaTimeRef(mediaTime) {
    return {
      clock: "media",
      epoch: state.epoch,
      ticks: Math.round((mediaTime || 0) * EVENT_TIMEBASE_DEN),
      timebase: "1/" + EVENT_TIMEBASE_DEN
    };
  }

  // With a clip, First Light's media clock; without one, the presentation clock in milliseconds.
  function nowRef() {
    if (hasClip()) return mediaTimeRef(video.currentTime || 0);
    return { clock: "presentation", epoch: 0, ticks: Math.round(performance.now()), timebase: "1/1000" };
  }

  function emitParam(name, value) {
    if (!state.takeId && !state.takeOpening) return;
    var evt = { kind: "param", t: nowRef(), name: name, value: value };
    if (/^k[1-8]$/.test(name) && state.active) evt.preset = state.active.id;
    enqueueEvent(evt);
  }

  function enqueueEvent(evt) {
    var continuous = evt.kind === "param" || evt.kind === "midi";
    if (continuous && !state.takeId && !state.takeOpening) return; // the take's opening snapshot carries state
    if (continuous) {
      var key = evt.kind === "param" ? "param:" + evt.name
        : (evt.cc != null ? "midi:cc:" + evt.channel + ":" + evt.cc : "midi:note:" + evt.channel + ":" + evt.note);
      var now = performance.now();
      if (now - (state.eventThrottle[key] || 0) < EVENT_HZ_LIMIT_MS) return; // at most 10 Hz per key
      state.eventThrottle[key] = now;
    }
    state.eventQueue.push(evt);
    if (state.eventQueue.length > EVENT_QUEUE_CAP) {
      var drop = state.eventQueue.length - EVENT_QUEUE_CAP;
      state.eventQueue = state.eventQueue.filter(function (e) {
        if (drop > 0 && e.kind !== "epoch") { drop--; return false; }
        return true;
      });
    }
  }

  // Epochs are per clip (media clock only). Queued events from the old epoch are dropped, but
  // queued epoch announcements stay, so the ledger's chain of epochs is never broken.
  function bumpEpoch(reason, atMediaTime) {
    if (!hasClip()) return;
    var mt = typeof atMediaTime === "number" ? atMediaTime : (video.currentTime || 0);
    state.epoch += 1;
    state.pulseEnv = { value: 0, initialized: false };
    state.eventQueue = state.eventQueue.filter(function (e) { return e.kind === "epoch"; });
    state.eventThrottle = {};
    enqueueEvent({ kind: "epoch", epoch: state.epoch, reason: reason, t: mediaTimeRef(mt) });
    if (state.active) state.active.needsClear = true;
    if (state.fadeFrom) state.fadeFrom.needsClear = true;
  }

  function loadGraphTemplate() {
    if (state.graphTemplate) return Promise.resolve(state.graphTemplate);
    return fetch("/api/graph/play-night", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("graph play-night: HTTP " + res.status);
        return res.json();
      })
      .then(function (g) { state.graphTemplate = g; return g; });
  }

  function buildFilledGraph() {
    var graph = JSON.parse(JSON.stringify(state.graphTemplate));
    var uri = state.clip ? (state.clip.path || state.clip.id) : (state.blobFile ? (video.currentSrc || "") : "");
    graph.assets = graph.assets || {};
    graph.assets.clip = { uri: uri };
    return graph;
  }

  // A take opens on the first play or the first preset switch.
  function ensureTakeOpen() {
    if (state.takeId || state.takeOpening) return Promise.resolve();
    if (state.takeError && performance.now() < state.takeRetryAt) return Promise.resolve();
    state.takeOpening = true;
    var token = state.takeToken;
    var clipId = state.clip ? state.clip.id : null;
    return loadGraphTemplate().then(function () {
      var meta = {
        page: "play",
        userAgent: navigator.userAgent,
        midi: state.midiInputName || null,
        clock: hasClip() ? "media" : "presentation",
        audio_source: state.source,
        device_label: state.source === "input" ? (state.inputLabel || null) : null,
        feedback_format: state.fbFormat,
        backing_scale: state.backingScale,
        decodingInfo: state.decodingInfo || null,
        presets: state.presets.map(function (p) { return { id: p.id, status: p.status }; })
      };
      return fetch("/api/take/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph: buildFilledGraph(), clip_id: clipId, meta: meta })
      });
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw new Error((data.problems && data.problems.join("; ")) || data.error || ("HTTP " + res.status));
        if (token !== state.takeToken) {
          sendBestEffort("/api/take/" + data.take_id + "/close",
                         JSON.stringify({ summary: { abandoned: "the clip changed while the take was opening" } }), false);
          return;
        }
        state.takeId = data.take_id;
        state.takeEventCount = 0;
        state.takeError = null;
        enqueueSnapshot();
      });
    }).catch(function (err) {
      state.takeError = errText(err);
      state.takeRetryAt = performance.now() + TAKE_RETRY_MS;
      logIssue("take/open failed: " + state.takeError);
    }).then(function () {
      state.takeOpening = false;
    });
  }

  // The state a take starts from, so a take can be read back without the page.
  function enqueueSnapshot() {
    var t = nowRef();
    var p = state.active;
    state.eventQueue.push({ kind: "preset", t: t, id: p ? p.id : null, from: null, xfade_ms: 0, initial: true });
    state.eventQueue.push({ kind: "audio_source", t: t, source: state.source,
                            device_label: state.source === "input" ? (state.inputLabel || null) : null, initial: true });
    [["hue", state.params.hue], ["intensity", state.params.intensity], ["xfade", state.xfadeMs],
     ["blackout", state.blackout ? 1 : 0]].forEach(function (kv) {
      state.eventQueue.push({ kind: "param", t: t, name: kv[0], value: kv[1], initial: true });
    });
    if (p) {
      p.knobs.forEach(function (v, i) {
        state.eventQueue.push({ kind: "param", t: t, name: "k" + (i + 1), value: v, preset: p.id, initial: true });
      });
    }
  }

  function stripInternal(evt) {
    var out = {};
    for (var k in evt) {
      if (k !== "__retried" && Object.prototype.hasOwnProperty.call(evt, k)) out[k] = evt[k];
    }
    return out;
  }

  function flushEvents() {
    if (!state.takeId || !state.eventQueue.length) return;
    var id = state.takeId;
    var batch = state.eventQueue.splice(0, state.eventQueue.length);
    fetch("/api/take/" + id + "/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: batch.map(stripInternal) })
    }).then(function (res) {
      if (res.status === 409) {
        logIssue("take/events: 409 — dropped " + batch.length + " event(s)");
        return;
      }
      if (!res.ok) {
        requeue("HTTP " + res.status);
        return;
      }
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (state.takeId === id) state.takeEventCount += typeof data.accepted === "number" ? data.accepted : batch.length;
      });
    }).catch(function (err) {
      requeue(errText(err));
    });

    function requeue(reason) {
      if (state.takeId !== id) return;
      var retry = batch.filter(function (e) { return !e.__retried; });
      retry.forEach(function (e) { e.__retried = true; });
      if (retry.length) {
        state.eventQueue = retry.concat(state.eventQueue).slice(0, EVENT_QUEUE_CAP);
        logIssue("take/events: " + reason + " — requeued " + retry.length + " event(s)");
      } else {
        logIssue("take/events: " + reason + " — dropped " + batch.length + " event(s) after a retry");
      }
    }
  }

  function playbackQuality() {
    if (!hasClip() || typeof video.getVideoPlaybackQuality !== "function") return null;
    var q = video.getVideoPlaybackQuality();
    return { dropped: q.droppedVideoFrames, total: q.totalVideoFrames };
  }

  function buildTakeSummary() {
    var lat = latencyStats();
    return {
      latency_ms: { p50: lat.p50, p95: lat.p95 },
      frames: playbackQuality() || { dropped: null, total: null },
      render_frames: { dropped: state.renderDropped, total: state.renderTotal },
      decoding: state.decodingInfo || null,
      preset_switches: state.presetSwitches,
      feedback_format: state.fbFormat,
      backing_scale: state.backingScale,
      audio_source: state.source
    };
  }

  function sendBestEffort(url, body, useBeacon) {
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
      return Promise.resolve();
    }
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true })
      .catch(function () {});
  }

  function closeTake(useBeacon) {
    if (!state.takeId) return;
    var id = state.takeId;
    var batch = state.eventQueue.splice(0, state.eventQueue.length).map(stripInternal);
    var closeBody = JSON.stringify({ summary: buildTakeSummary() });
    state.takeId = null;
    state.takeEventCount = 0;
    if (useBeacon) {
      if (batch.length) sendBestEffort("/api/take/" + id + "/events", JSON.stringify({ events: batch }), true);
      sendBestEffort("/api/take/" + id + "/close", closeBody, true);
      return;
    }
    var first = batch.length ? sendBestEffort("/api/take/" + id + "/events", JSON.stringify({ events: batch }), false) : Promise.resolve();
    first.then(function () { sendBestEffort("/api/take/" + id + "/close", closeBody, false); });
  }

  // ------------------------------------------------ decoder evidence ----

  var CODECS_BY_NAME = { hevc: "hvc1.1.6.L123.B0", h264: "avc1.640028", av1: "av01.0.08M.08", vp9: "vp09.00.10.08", vp8: "vp8" };

  function guessContentType(ext, codecName) {
    var codecs = CODECS_BY_NAME[String(codecName || "").toLowerCase()];
    if (!codecs) return (ext === "webm" || ext === "mkv") ? 'video/webm; codecs="vp09.00.10.08"' : 'video/mp4; codecs="avc1.640028"';
    var webm = /^vp/.test(codecs) || (codecs.indexOf("av01") === 0 && (ext === "webm" || ext === "mkv"));
    return (webm ? "video/webm" : "video/mp4") + '; codecs="' + codecs + '"';
  }

  function fetchProbe(id) {
    return fetch("/api/probe/" + id, { cache: "no-store" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(function (data) { if (state.clip && state.clip.id === id) state.probe = data; })
      .catch(function () { state.probe = null; })
      .then(queryDecodingInfo);
  }

  function queryDecodingInfo() {
    if (!navigator.mediaCapabilities || !navigator.mediaCapabilities.decodingInfo) return;
    var pv = state.probe && state.probe.video;
    var width = video.videoWidth || (pv && pv.width) || 0;
    var height = video.videoHeight || (pv && pv.height) || 0;
    if (!width || !height) return;
    var framerate = 30;
    if (pv && pv.rate) {
      var parts = String(pv.rate).split("/").map(Number);
      if (parts[1]) framerate = parts[0] / parts[1];
    }
    var ext = String((state.clip && state.clip.ext) || (state.blobFile && state.blobFile.name.split(".").pop()) || "mp4").toLowerCase();
    var config = { type: "file", video: { contentType: guessContentType(ext, pv && pv.codec), width: width, height: height, bitrate: 8000000, framerate: framerate } };
    navigator.mediaCapabilities.decodingInfo(config).then(function (r) {
      state.decodingInfo = { contentType: config.video.contentType, supported: r.supported, smooth: r.smooth, powerEfficient: r.powerEfficient };
    }).catch(function () { state.decodingInfo = null; });
  }

  // ----------------------------------------------------------- library ---

  function loadLibrary() {
    return fetch("/api/library", { cache: "no-store" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(function (data) { state.libraryClips = Array.isArray(data.clips) ? data.clips : []; })
      .catch(function (err) {
        state.libraryClips = [];
        logIssue("library load failed: " + errText(err));
      })
      .then(renderLibrary);
  }

  function renderLibrary() {
    var q = (libSearchEl.value || "").trim().toLowerCase();
    var items = state.libraryClips.filter(function (c) { return !q || (c.name || "").toLowerCase().indexOf(q) !== -1; });
    libListEl.innerHTML = "";
    if (!items.length) {
      libListEl.appendChild(el("li", "lib-empty", state.libraryClips.length ? "no matches" : "library empty"));
      return;
    }
    items.forEach(function (clip) {
      var item = el("li", "lib-item" + (state.clip && state.clip.id === clip.id ? " active" : ""));
      item.tabIndex = 0;
      item.setAttribute("data-clip-id", clip.id);
      item.appendChild(el("div", "name", clip.name || clip.id));
      item.appendChild(el("div", "meta", formatBytes(clip.size) + " · " + String(clip.ext || "").toUpperCase()));
      item.addEventListener("click", function () { loadClip({ kind: "library", clip: clip }, { autoplay: true }); });
      item.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); loadClip({ kind: "library", clip: clip }, { autoplay: true }); }
      });
      libListEl.appendChild(item);
    });
  }

  // ------------------------------------------------------------ player ---

  // source: {kind: "library"|"resolved", clip} | {kind: "blob", file, objectUrl} | null (eject).
  // A clip change closes the open take and opens the next one straight away.
  function loadClip(source, opts) {
    opts = opts || {};
    var hadTake = !!state.takeId;
    if (state.takeId) closeTake(false);
    state.takeToken++;
    state.takeError = null;
    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = null;
    }
    state.analysisToken++;
    state.epoch = 0;
    state.pulseEnv = { value: 0, initialized: false };
    state.eventQueue = [];
    state.eventThrottle = {};
    state.lastMediaTime = null;
    state.justSeeked = false;
    state.probe = null;
    state.decodingInfo = null;
    state.videoUploaded = false;
    state.videoFrameReady = false;
    state.videoFrameMeta = null;
    hideBanner();

    if (!source) {
      state.clip = null;
      state.blobFile = null;
      video.pause();
      video.removeAttribute("src");
      video.load();
      stageEl.classList.remove("has-clip");
    } else if (source.kind === "blob") {
      state.clip = null;
      state.blobFile = source.file;
      state.objectUrl = source.objectUrl;
      video.src = source.objectUrl;
      setBanner("analysis unavailable: outside library roots");
      stageEl.classList.add("has-clip");
    } else {
      state.clip = source.clip;
      state.blobFile = null;
      video.src = "/api/media/" + source.clip.id;
      fetchProbe(source.clip.id);
      stageEl.classList.add("has-clip");
    }

    if (source) {
      ensureAudioGraph();
      resumeAudio();
      if (!state.sourcePinned && state.source !== "clip") setAudioSource("clip");
      else if (state.source === "analysis") startAnalysisPoll(state.clip ? state.clip.id : null);
    }
    renderLibrary();
    updateAudioUi();
    if (hadTake) ensureTakeOpen();
    if (!source) return Promise.resolve(true);
    video.load();
    if (!opts.autoplay) return Promise.resolve(true);
    return video.play().then(function () { return true; }).catch(function (err) {
      logIssue("play() rejected: " + errText(err));
      return false;
    });
  }

  function resolveDroppedFile(file) {
    var qs = new URLSearchParams({ name: file.name, size: String(file.size) });
    return fetch("/api/resolve?" + qs.toString())
      .then(function (res) {
        if (res.ok) return res.json().then(function (data) { loadClip({ kind: "resolved", clip: data.clip }, { autoplay: true }); });
        loadClip({ kind: "blob", file: file, objectUrl: URL.createObjectURL(file) }, { autoplay: true });
      })
      .catch(function (err) {
        logIssue("resolve failed: " + errText(err));
        loadClip({ kind: "blob", file: file, objectUrl: URL.createObjectURL(file) }, { autoplay: true });
      });
  }

  function updateSeekUi() {
    if (video.duration && isFinite(video.duration)) seekEl.value = String(Math.round((video.currentTime / video.duration) * 1000));
    timeCurEl.textContent = formatTime(video.currentTime);
    timeDurEl.textContent = formatTime(video.duration || 0);
  }

  function toggleLoop() {
    video.loop = !video.loop;
    loopBtn.setAttribute("aria-pressed", String(video.loop));
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen().catch(function () {});
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(function () {});
  }

  function togglePlay() {
    if (!hasClip()) return;
    if (video.paused) video.play().catch(function (err) { logIssue("play() rejected: " + errText(err)); });
    else video.pause();
  }

  // ------------------------------------------------- performance mode ---

  function setPerf(on) {
    state.perf = !!on;
    document.body.classList.toggle("perf", state.perf);
    performBtn.setAttribute("aria-pressed", String(state.perf));
    if (state.perf) {
      showPerfHint();
    } else {
      clearTimeout(state.hintTimer);
      perfHintEl.classList.remove("show");
      toastEl.classList.remove("show");
      document.body.classList.remove("cursor-idle");
    }
  }

  function showPerfHint() {
    if (!state.perf) return;
    perfHintEl.classList.add("show");
    document.body.classList.remove("cursor-idle");
    clearTimeout(state.hintTimer);
    state.hintTimer = setTimeout(function () {
      perfHintEl.classList.remove("show");
      if (state.perf) document.body.classList.add("cursor-idle");
    }, PERF_HINT_MS);
  }

  // ------------------------------------------------------------ keyboard --

  function isTypingTarget(node) {
    if (!node) return false;
    var tag = node.tagName;
    if (tag === "TEXTAREA" || tag === "SELECT" || node.isContentEditable) return true;
    if (tag === "INPUT") {
      var type = (node.type || "text").toLowerCase();
      return ["range", "checkbox", "radio", "button", "submit", "reset", "color", "file"].indexOf(type) === -1;
    }
    return false;
  }

  function onKeyDown(e) {
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    var active = document.activeElement;
    if (isTypingTarget(active)) return;
    if (e.key === "Escape") {
      if (MIDI.learning) cancelLearn();
      return;
    }
    if (e.repeat) return;
    var key = e.key;
    if (key === "ArrowRight" || key === "ArrowLeft") {
      if (active && active.tagName === "INPUT" && active.type === "range") return;
      e.preventDefault();
      stepPreset(key === "ArrowRight" ? 1 : -1, "key");
      return;
    }
    if (/^[1-9]$/.test(key)) {
      e.preventDefault();
      selectByPosition(Number(key), "key");
      return;
    }
    switch (key.toLowerCase()) {
      case "r": randomPreset("key"); break;
      case "x": toggleXfade(); break;
      case "h": setPerf(!state.perf); break;
      case "f": toggleFullscreen(); break;
      case "l": toggleLoop(); break;
      case "b": toggleBlackout(); break;
      case " ": e.preventDefault(); togglePlay(); break;
      default:
        if (key.length === 1) state.pendingBeat = 1; // any other key hit flashes u_beat
    }
  }

  // --------------------------------------------------------------- HUD --

  function updateHud() {
    var p = state.active;
    hudFpsEl.textContent = state.fps ? state.fps.toFixed(0) + " fps · " + frameInterval().toFixed(1) + " ms" : "—";

    var presetText = p ? p.name : "—";
    if (state.fadeFrom) presetText += " ← " + state.fadeFrom.name + " " + Math.round(fadeProgress(performance.now()) * 100) + "%";
    if (state.blackout) presetText += " · blackout";
    hudPresetEl.textContent = presetText;

    var ok = 0, broken = 0, pending = 0;
    state.presets.forEach(function (q) {
      if (q.status === "ok") ok++;
      else if (q.status === "broken") broken++;
      else pending++;
    });
    hudCompileEl.textContent = (p ? (p.status === "ok" ? "active compiled" : "active " + p.status) : "no active preset") +
      " · " + ok + " ok / " + broken + " broken" + (pending ? " / " + pending + " compiling" : "") +
      (state.presetsStatus === "error" ? " · list: " + state.presetsError : "");

    hudFeedbackEl.textContent = state.fbFormat + " · scale " + state.backingScale.toFixed(2) + " · " + state.width + "×" + state.height;
    scaleBtn.hidden = state.backingScale >= 1;

    hudAudioEl.textContent = audioSourceText();
    audioStatusEl.textContent = "audio: " + audioSourceText();

    var midiText = state.midiInputName || "not connected";
    var lc = state.lastControl;
    if (lc) midiText += " · " + describeControl(lc.type, lc.ch, lc.num) + "=" + lc.value;
    hudMidiEl.textContent = midiText;

    var lat = latencyStats();
    hudLatencyEl.textContent = lat.p50 != null ? Math.round(lat.p50) + "ms / " + Math.round(lat.p95) + "ms" : "—";

    var pq = playbackQuality();
    hudFramesEl.textContent = (pq ? "video " + pq.dropped + "/" + pq.total + " · " : "") + "render " + state.renderDropped + "/" + state.renderTotal;

    hudClockEl.textContent = hasClip()
      ? "media · epoch " + state.epoch + " · " + (video.currentTime || 0).toFixed(3) + "s"
      : "presentation · epoch 0";

    hudTakeEl.textContent = state.takeId
      ? state.takeId + " · " + state.takeEventCount + " events"
      : (state.takeOpening ? "opening…" : (state.takeError ? "open failed: " + state.takeError : "— (opens on play or a preset switch)"));

    updateMeterValues();
  }

  // --------------------------------------------------------- test hook --

  // window.__play: the members Vandor's play_verify.mjs drives. Each one runs the same path as
  // the UI (select = a list click, loadClip = a library click, setAudioSource = the Audio panel).
  function installTestHook() {
    window.__play = {
      presets: function () {
        return state.presets.map(function (p) {
          return {
            id: p.id, name: p.name, author: p.author, broken: p.status === "broken",
            problem: p.status === "broken" ? (p.problem || firstLine(p.log) || null) : null
          };
        });
      },
      active: function () {
        var p = state.active;
        if (!p) return null;
        return { id: p.id, name: p.name, compiled: p.status === "ok" && !!p.program, log: p.log || "" };
      },
      select: function (id) {
        var p = findPreset(id);
        if (!p || p.status === "broken") return false;
        return onPresetClick(p);
      },
      stats: function () {
        var pq = playbackQuality();
        return {
          fps: Math.round(state.fps * 10) / 10,
          dropped: pq ? pq.dropped : 0,
          total: pq ? pq.total : 0,
          hasVideo: videoIsBound(),
          audio: {
            source: state.source, level: state.feat.level, bass: state.feat.bass, mid: state.feat.mid,
            high: state.feat.high, flux: state.feat.flux, beat: state.beat
          },
          take: { id: state.takeId, events: state.takeEventCount }
        };
      },
      errors: function () {
        return state.errors.map(function (e) { return { kind: e.kind, id: e.id, message: e.message, at: e.at }; });
      },
      loadClip: function (id) {
        return loadLibrary().then(function () {
          var clip = state.libraryClips.filter(function (c) { return c.id === id; })[0];
          if (!clip) return false;
          return loadClip({ kind: "library", clip: clip }, { autoplay: true });
        });
      },
      setAudioSource: function (kind) {
        if (kind !== "input") return setAudioSource(kind);
        return ensureInputPermission().then(function () {
          return setAudioSource("input", { deviceId: state.devices.length ? state.devices[0].deviceId : "" });
        }).catch(function (err) {
          state.audioNote = "input failed: " + errText(err);
          updateAudioUi();
          return false;
        });
      }
    };
  }

  // -------------------------------------------------------------- wire ---

  function wireEvents() {
    video.addEventListener("loadedmetadata", function () {
      updateSeekUi();
      queryDecodingInfo();
      restartVideoFrameChain();
    });
    video.addEventListener("loadeddata", function () { state.videoFrameReady = true; });
    video.addEventListener("seeked", function () { state.videoFrameReady = true; });
    video.addEventListener("error", function () {
      if (!hasClip()) return;
      var err = video.error;
      var reason = err ? ("code " + err.code + (err.message ? ": " + err.message : "")) : "unknown error";
      setBanner("video failed to load — " + reason);
      recordError("runtime", null, "video element error: " + reason);
      enqueueEvent({ kind: "degraded", t: nowRef(), reason: "video-error: " + reason });
    });
    video.addEventListener("seeking", function () {
      if (!hasClip()) return;
      bumpEpoch("seek", video.currentTime);
      state.justSeeked = true;
      enqueueEvent({ kind: "seek", t: mediaTimeRef(video.currentTime), to: video.currentTime });
    });
    video.addEventListener("play", function () {
      playBtn.setAttribute("aria-pressed", "true");
      playBtn.textContent = "Pause";
      ensureTakeOpen().then(function () { enqueueEvent({ kind: "play", t: nowRef() }); });
    });
    video.addEventListener("pause", function () {
      playBtn.setAttribute("aria-pressed", "false");
      playBtn.textContent = "Play";
      if (hasClip()) enqueueEvent({ kind: "pause", t: nowRef() });
    });
    video.addEventListener("timeupdate", updateSeekUi);
    video.addEventListener("durationchange", updateSeekUi);

    playBtn.addEventListener("click", togglePlay);
    loopBtn.addEventListener("click", toggleLoop);
    fullscreenBtn.addEventListener("click", toggleFullscreen);
    ejectBtn.addEventListener("click", function () { if (hasClip()) loadClip(null); });
    seekEl.addEventListener("input", function () {
      if (video.duration && isFinite(video.duration)) video.currentTime = (Number(seekEl.value) / 1000) * video.duration;
    });

    midiBtn.addEventListener("click", connectMIDI);
    performBtn.addEventListener("click", function () { setPerf(!state.perf); });
    rackBtn.addEventListener("click", function () {
      var collapsed = layoutEl.classList.toggle("rack-collapsed");
      rackBtn.setAttribute("aria-pressed", String(!collapsed));
    });

    prevBtn.addEventListener("click", function () { stepPreset(-1, "click"); });
    nextBtn.addEventListener("click", function () { stepPreset(1, "click"); });
    randomBtn.addEventListener("click", function () { randomPreset("click"); });
    xfadeBtn.addEventListener("click", toggleXfade);
    blackoutBtn.addEventListener("click", toggleBlackout);
    rescanBtn.addEventListener("click", loadPresetList);
    scaleBtn.addEventListener("click", function () {
      state.backingScale = 1;
      state.slowStreak = 0;
    });

    sourceSelEl.addEventListener("change", function () {
      var kind = sourceSelEl.value;
      setAudioSource(kind, kind === "input" && deviceSelEl.value ? { deviceId: deviceSelEl.value } : {});
    });
    pinBtn.addEventListener("click", function () {
      state.sourcePinned = !state.sourcePinned;
      saveAudioPref();
      updateAudioUi();
    });
    deviceSelEl.addEventListener("change", function () {
      if (state.source === "input") setAudioSource("input", { deviceId: deviceSelEl.value });
      else saveAudioPref();
    });
    inputsBtn.addEventListener("click", function () {
      ensureInputPermission().then(function () {
        state.audioNote = state.devices.length + " input device(s) listed; choose Input as the source to analyse one";
        updateAudioUi();
      }).catch(function (err) {
        state.audioNote = "inputs unavailable: " + errText(err);
        updateAudioUi();
      });
    });
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener("devicechange", function () { listDevices().catch(function () {}); });
    }

    clearMapBtn.addEventListener("click", function () {
      MIDI.bindings = [];
      cancelLearn();
      persistMappings();
      renderMapPanel();
    });

    libSearchEl.addEventListener("input", renderLibrary);

    stageEl.addEventListener("dragover", function (e) {
      e.preventDefault();
      stageEl.classList.add("drag-over");
    });
    stageEl.addEventListener("dragleave", function () { stageEl.classList.remove("drag-over"); });
    stageEl.addEventListener("drop", function (e) {
      e.preventDefault();
      stageEl.classList.remove("drag-over");
      var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) resolveDroppedFile(file);
    });

    // Resume the AudioContext on user gestures (the first one creates it).
    function onGesture() {
      ensureAudioGraph();
      resumeAudio();
    }
    window.addEventListener("pointerdown", onGesture, true);
    window.addEventListener("keydown", onGesture, true);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousemove", function () { if (state.perf) showPerfHint(); });

    document.addEventListener("visibilitychange", function () {
      state.slowStreak = 0;
      state.lastRafNow = 0;
    });
    window.addEventListener("pagehide", function () {
      closeTake(true);
      closeInput();
    });
    window.addEventListener("error", function (e) {
      recordError("runtime", null, (e && e.message) || "uncaught error");
    });
    window.addEventListener("unhandledrejection", function (e) {
      recordError("runtime", null, "unhandled rejection: " + errText(e && e.reason));
    });

    wireContextEvents();
  }

  function restoreAudioInput(pref) {
    if (pref.source !== "input" || !navigator.mediaDevices || !navigator.permissions || !navigator.permissions.query) return;
    navigator.permissions.query({ name: "microphone" }).then(function (status) {
      if (status.state !== "granted") return;
      return listDevices().then(function () {
        return setAudioSource("input", pref.deviceId ? { deviceId: pref.deviceId } : {});
      });
    }).catch(function () { /* the Audio panel still works by hand */ });
  }

  // -------------------------------------------------------------- init ---

  function init() {
    cacheDom();
    state.builtin = makePreset({ id: BUILTIN_ID, name: "Passthrough", author: "arsenal", tags: ["built-in"], builtin: true });
    state.presets = [state.builtin];
    loadMappings();
    buildMacroRows();
    buildTriggerGrid();
    renderMapPanel();
    var pref = loadAudioPref();
    state.sourcePinned = !!pref.pinned;
    wireEvents();
    installTestHook();

    if (initGL()) {
      resizeCanvasIfNeeded();
      selectPreset(state.builtin, "init");
    }
    setXfadeMs(XFADE_DEFAULT_MS, "init");
    updateStageTags();
    syncMacroUi();
    renderPresetList();
    updateAudioUi();

    requestAnimationFrame(onAnimationFrame);
    loadPresetList();
    loadLibrary();
    loadGraphTemplate().catch(function (err) { logIssue(errText(err)); });
    restoreAudioInput(pref);

    updateHud();
    setInterval(updateHud, HUD_INTERVAL_MS);
    setInterval(flushEvents, FLUSH_INTERVAL_MS);
  }

  // `defer` guarantees the DOM is parsed before this runs.
  init();
})();
