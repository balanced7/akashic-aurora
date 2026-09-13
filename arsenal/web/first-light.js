// arsenal/web/first-light.js
// First Light page logic. No external libraries. Plain script, loaded with
// `defer` so the DOM is already parsed by the time this runs.
// Contract: arsenal/FIRST-LIGHT-SPEC.md > "Page (arsenal/web)".
// All network paths are root-relative (no scheme/host) so the page works
// regardless of the port it is actually served from.

(function () {
  "use strict";

  // ------------------------------------------------------------ constants --

  var EVENT_TIMEBASE_DEN = 90000; // take-event t.ticks timebase
  var ANALYSIS_TIMEBASE_DEN = 48000; // audio_features sampling timebase
  var MIDI_MAP_KEY = "arsenal.firstlight.midiMap";
  var FLUSH_INTERVAL_MS = 500;
  var HUD_INTERVAL_MS = 100;
  var LIGHT_INTERVAL_MS = 60;
  var LIGHT_ON_MS = 140;
  var LATENCY_MAX_SAMPLES = 200;
  var EVENT_HZ_LIMIT_MS = 100; // 10 Hz cap for midi/param events
  var WATCHDOG_STREAK = 20;
  var FRAME_BUDGET_MS = 1000 / 60;
  var DPR_CAP = 2;
  var BACKING_SCALE_MIN = 0.5;
  var ANALYSIS_POLL_MS = 600;
  var EVENT_QUEUE_CAP = 1000;

  // ------------------------------------------------------------- shaders --

  var VERT_SRC = [
    "#version 300 es",
    "precision highp float;",
    "out vec2 v_uv;",
    "void main() {",
    "  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));",
    "  vec2 p = pos[gl_VertexID];",
    "  v_uv = (p + 1.0) * 0.5;", // (0,0) at bottom-left, matching UNPACK_FLIP_Y_WEBGL upload
    "  gl_Position = vec4(p, 0.0, 1.0);",
    "}"
  ].join("\n");

  // Built-in fallback effect: perceptual (HSV) hue rotation -- never an RGB
  // lerp, which would pass through a desaturated grey-brown -- plus a pulse
  // glow and a pulse-driven zoom. Used whenever the external shader is
  // missing or fails to compile. Letterboxes itself exactly like the real
  // effect, using the same uniform contract.
  var FALLBACK_FRAG_SRC = [
    "#version 300 es",
    "precision highp float;",
    "uniform sampler2D u_video;",
    "uniform vec2  u_res;",
    "uniform vec2  u_video_res;",
    "uniform float u_time;",
    "uniform float u_pulse;",
    "uniform float u_hue;",
    "uniform float u_intensity;",
    "uniform float u_bass, u_mid, u_high, u_flux;",
    "in vec2 v_uv;",
    "out vec4 outColor;",
    "",
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
    "  float ca = u_res.x / u_res.y;",
    "  float va = u_video_res.x / max(u_video_res.y, 1.0);",
    "  vec2 uv = v_uv;",
    "  if (va > ca) {",
    "    float h = ca / va; float y0 = 0.5 - 0.5 * h; float y1 = 0.5 + 0.5 * h;",
    "    if (uv.y < y0 || uv.y > y1) { outColor = vec4(0.0, 0.0, 0.0, 1.0); return; }",
    "    uv.y = (uv.y - y0) / (y1 - y0);",
    "  } else {",
    "    float w = va / ca; float x0 = 0.5 - 0.5 * w; float x1 = 0.5 + 0.5 * w;",
    "    if (uv.x < x0 || uv.x > x1) { outColor = vec4(0.0, 0.0, 0.0, 1.0); return; }",
    "    uv.x = (uv.x - x0) / (x1 - x0);",
    "  }",
    "",
    "  vec2 c = uv - 0.5;",
    "  float zoom = 1.0 + 0.12 * u_pulse * sin(u_time * 1.4);",
    "  c /= zoom;",
    "  vec2 suv = c + 0.5;",
    "",
    "  vec3 col = texture(u_video, suv).rgb;",
    "",
    "  if (u_hue > 0.5 || u_hue < -0.5) {",
    "    vec3 hsv = rgb2hsv(col);",
    "    hsv.x = fract(hsv.x + u_hue / 360.0);",
    "    col = hsv2rgb(hsv);",
    "  }",
    "",
    "  float glow = u_pulse * 0.35 * u_intensity;",
    "  col += col * glow;",
    "  col += 0.02 * u_flux;",
    "  col *= mix(0.2, 1.0, u_intensity);",
    "",
    "  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);",
    "}"
  ].join("\n");

  // -------------------------------------------------------------- state --

  var state = {
    gl: null,
    program: null,
    usingFallback: false,
    shaderLog: "",
    uniforms: {},
    videoTexture: null,
    glLost: false,
    backingScale: 1,
    slowStreak: 0,
    loopGeneration: 0,
    lastFrameNow: 0,

    epoch: 0,
    justSeeked: false,
    lastMediaTime: null,

    clip: null, // resolved/library clip metadata, or null for an out-of-library blob
    blobFile: null,
    objectUrl: null,
    probe: null,
    decodingInfo: null,

    analysis: null,
    analysisReady: false,
    analysisToken: 0,
    lastFeatureIdx: null,
    pulseEnv: { value: 0, initialized: false },
    frame: { bass: 0, mid: 0, high: 0, flux: 0 },
    params: { hue: 0, intensity: 0.8 },

    midiInputName: null,
    lastCC: null,
    pendingLatency: [],
    latencySamples: [],

    takeId: null,
    takeOpening: false,
    takeEventCount: 0,
    eventQueue: [],
    eventThrottle: {},
    graphTemplate: null,

    libraryClips: []
  };

  var MIDI = {
    access: null,
    input: null,
    learnQueue: ["hue", "intensity"],
    learnIndex: 0,
    learning: null,
    mappings: {}
  };

  // ------------------------------------------------------------- utils --

  function clamp(x, lo, hi) {
    return Math.min(hi, Math.max(lo, x));
  }

  function errText(err) {
    return err && err.message ? err.message : String(err);
  }

  function formatTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ":" + (s < 10 ? "0" + s : String(s));
  }

  function formatBytes(n) {
    if (typeof n !== "number" || !isFinite(n)) return "";
    var units = ["B", "KB", "MB", "GB"];
    var v = n, i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return (i === 0 ? String(v) : v.toFixed(1)) + units[i];
  }

  function mediaTimeRef(mediaTime) {
    return {
      clock: "media",
      epoch: state.epoch,
      ticks: Math.round(mediaTime * EVENT_TIMEBASE_DEN),
      timebase: "1/" + EVENT_TIMEBASE_DEN
    };
  }

  function logIssue(msg) {
    // "log it" (spec, 409 handling) -- console is the durable-enough sink
    // for a page with no server-side client-log route.
    console.warn("[first-light]", msg);
  }

  function percentile(samples, p) {
    if (!samples.length) return null;
    var sorted = samples.slice().sort(function (a, b) { return a - b; });
    var idx = clamp(Math.ceil((p / 100) * sorted.length) - 1, 0, sorted.length - 1);
    return sorted[idx];
  }

  function latencyStats() {
    return {
      p50: percentile(state.latencySamples, 50),
      p95: percentile(state.latencySamples, 95)
    };
  }

  function pushLatencySample(ms) {
    state.latencySamples.push(ms);
    if (state.latencySamples.length > LATENCY_MAX_SAMPLES) {
      state.latencySamples.shift();
    }
  }

  function playbackQuality() {
    if (!video || typeof video.getVideoPlaybackQuality !== "function") return null;
    var q = video.getVideoPlaybackQuality();
    return { dropped: q.droppedVideoFrames, total: q.totalVideoFrames };
  }

  function safeLocalStorageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (err) {
      return null;
    }
  }

  function safeLocalStorageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      // private mode, quota exceeded, or storage disabled -- never fatal
    }
  }

  var CONTENT_TYPE_BY_EXT = {
    mp4: 'video/mp4; codecs="avc1.640028"',
    m4v: 'video/mp4; codecs="avc1.640028"',
    mov: 'video/mp4; codecs="avc1.640028"',
    webm: 'video/webm; codecs="vp09.00.10.08"',
    mkv: 'video/webm; codecs="vp09.00.10.08"'
  };

  // Codec strings keyed by the probe's FFmpeg codec name. Ask about the codec the file really holds:
  // the OBS recordings are HEVC, and an answer about H.264 would be evidence about the wrong decoder.
  var CODECS_BY_NAME = {
    hevc: "hvc1.1.6.L123.B0",
    h264: "avc1.640028",
    av1: "av01.0.08M.08",
    vp9: "vp09.00.10.08",
    vp8: "vp8"
  };

  function guessContentType(ext, codecName) {
    var codecs = CODECS_BY_NAME[String(codecName || "").toLowerCase()];
    if (!codecs) return CONTENT_TYPE_BY_EXT[ext] || CONTENT_TYPE_BY_EXT.mp4;
    var webm = /^vp/.test(codecs) || (codecs.indexOf("av01") === 0 && (ext === "webm" || ext === "mkv"));
    return (webm ? "video/webm" : "video/mp4") + '; codecs="' + codecs + '"';
  }

  // ---------------------------------------------------------- DOM cache --

  var canvas, video, stageEl, layoutEl, hintEl, bannerEl, bannerTextEl;
  var playBtn, loopBtn, seekEl, timeCurEl, timeDurEl, fullscreenBtn;
  var midiBtn, midiStatusEl, rackBtn;
  var libSearchEl, libListEl;
  var learnBtn, mapListEl, mapStatusEl;
  var planTextEl;
  var hudEpochEl, hudTimeEl, hudDecoderEl, hudFramesEl, hudMidiEl,
      hudLatencyEl, hudTakeEl, hudShaderEl, hudAnalysisEl, hudScaleEl, shaderLogEl;

  function cacheDom() {
    canvas = document.getElementById("gl");
    video = document.getElementById("video");
    stageEl = document.getElementById("stage");
    layoutEl = document.getElementById("layout");
    hintEl = document.getElementById("hint");
    bannerEl = document.getElementById("banner");
    bannerTextEl = document.getElementById("banner-text");

    playBtn = document.getElementById("btn-play");
    loopBtn = document.getElementById("btn-loop");
    seekEl = document.getElementById("seek");
    timeCurEl = document.getElementById("time-cur");
    timeDurEl = document.getElementById("time-dur");
    fullscreenBtn = document.getElementById("btn-fullscreen");

    midiBtn = document.getElementById("btn-midi");
    midiStatusEl = document.getElementById("midi-status");
    rackBtn = document.getElementById("btn-rack");

    libSearchEl = document.getElementById("lib-search");
    libListEl = document.getElementById("lib-list");

    learnBtn = document.getElementById("btn-learn");
    mapListEl = document.getElementById("map-list");
    mapStatusEl = document.getElementById("map-status");

    planTextEl = document.getElementById("plan-text");

    hudEpochEl = document.getElementById("hud-epoch");
    hudTimeEl = document.getElementById("hud-time");
    hudDecoderEl = document.getElementById("hud-decoder");
    hudFramesEl = document.getElementById("hud-frames");
    hudMidiEl = document.getElementById("hud-midi");
    hudLatencyEl = document.getElementById("hud-latency");
    hudTakeEl = document.getElementById("hud-take");
    hudShaderEl = document.getElementById("hud-shader");
    hudAnalysisEl = document.getElementById("hud-analysis");
    hudScaleEl = document.getElementById("hud-scale");
    shaderLogEl = document.getElementById("shader-log");
  }

  // ------------------------------------------------------------ banners --

  function setBanner(text) {
    bannerTextEl.textContent = text;
    bannerEl.hidden = false;
  }

  function hideBanner() {
    bannerEl.hidden = true;
    bannerTextEl.textContent = "";
  }

  // ------------------------------------------------------------- HUD -----

  function setAnalysisStatus(text) {
    hudAnalysisEl.textContent = text;
  }

  function formatDecoderEvidence() {
    if (!state.decodingInfo) return "unavailable";
    var d = state.decodingInfo;
    var out = "power-efficient: " + (d.powerEfficient ? "yes" : "no");
    if (typeof d.smooth === "boolean") out += " · smooth: " + (d.smooth ? "yes" : "no");
    return out;
  }

  function reportShaderStatus() {
    if (state.usingFallback) {
      hudShaderEl.textContent = "fallback (built-in effect)";
      shaderLogEl.hidden = false;
      shaderLogEl.textContent = state.shaderLog || "(no compile log)";
    } else {
      hudShaderEl.textContent = "compiled: shaders/first-light.frag";
      shaderLogEl.hidden = true;
      shaderLogEl.textContent = "";
    }
  }

  function updateHud() {
    hudEpochEl.textContent = String(state.epoch);

    var mt = video.currentTime || 0;
    var ticks = Math.round(mt * EVENT_TIMEBASE_DEN);
    hudTimeEl.textContent = ticks + "/" + EVENT_TIMEBASE_DEN + " · " + mt.toFixed(3) + "s";

    hudDecoderEl.textContent = formatDecoderEvidence();

    var pq = playbackQuality();
    hudFramesEl.textContent = pq ? (pq.dropped + " / " + pq.total) : "—";

    var midiText = state.midiInputName || "not connected";
    if (state.lastCC) midiText += " · cc" + state.lastCC.cc + "=" + state.lastCC.value;
    hudMidiEl.textContent = midiText;

    var lat = latencyStats();
    hudLatencyEl.textContent = lat.p50 != null
      ? (Math.round(lat.p50) + "ms / " + Math.round(lat.p95) + "ms")
      : "—";

    hudTakeEl.textContent = state.takeId
      ? (state.takeId + " · " + state.takeEventCount + " events")
      : "—";

    hudScaleEl.textContent = state.backingScale.toFixed(2);
  }

  // --------------------------------------------------------- patch lights --

  var LIGHT_IDS = {
    clip: "light-clip",
    decode: "light-decode",
    features: "light-features",
    fx: "light-fx",
    midi: "light-midi",
    screen: "light-screen"
  };
  var lightFiredAt = {};

  function pulseLight(name) {
    lightFiredAt[name] = performance.now();
  }

  function tickLights() {
    var now = performance.now();
    for (var name in LIGHT_IDS) {
      if (!Object.prototype.hasOwnProperty.call(LIGHT_IDS, name)) continue;
      var el = document.getElementById(LIGHT_IDS[name]);
      if (!el) continue;
      var last = lightFiredAt[name] || 0;
      var on = now - last < LIGHT_ON_MS;
      if (on) el.classList.add("on"); else el.classList.remove("on");
    }
  }

  // -------------------------------------------------------------- GL -----

  function compileShader(gl, type, src) {
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

  function linkProgram(gl, vsSrc, fsSrc) {
    var vs = compileShader(gl, gl.VERTEX_SHADER, vsSrc);
    var fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSrc);
    var prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      var log = gl.getProgramInfoLog(prog) || "unknown link error";
      gl.deleteProgram(prog);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      throw new Error(log);
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    return prog;
  }

  function cacheUniformLocations() {
    var names = ["u_video", "u_res", "u_video_res", "u_time", "u_pulse",
                 "u_hue", "u_intensity", "u_bass", "u_mid", "u_high", "u_flux"];
    state.uniforms = {};
    for (var i = 0; i < names.length; i++) {
      state.uniforms[names[i]] = state.gl.getUniformLocation(state.program, names[i]);
    }
  }

  function createVideoTexture(gl) {
    var tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    return tex;
  }

  // Loads /web/shaders/first-light.frag and links it against the built-in
  // vertex shader. On any fetch or compile/link failure, falls back to the
  // built-in effect and records the log for the HUD -- the page must still
  // work with the shader missing or broken.
  function setupEffect() {
    var usedFallback = false;
    var log = "";
    return fetch("/web/shaders/first-light.frag", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("fetch failed: HTTP " + res.status);
        return res.text();
      })
      .then(function (fragSrc) {
        // GLSL ES needs #version on the first line, and house shaders open with a //! metadata header.
        var versionAt = fragSrc.indexOf("#version");
        if (versionAt > 0) fragSrc = fragSrc.slice(versionAt);
        state.program = linkProgram(state.gl, VERT_SRC, fragSrc);
      })
      .catch(function (err) {
        usedFallback = true;
        log = errText(err);
        try {
          state.program = linkProgram(state.gl, VERT_SRC, FALLBACK_FRAG_SRC);
        } catch (err2) {
          log += "\nfallback effect also failed to compile: " + errText(err2);
          state.program = null;
        }
      })
      .then(function () {
        state.usingFallback = usedFallback;
        state.shaderLog = log;
        if (state.program) cacheUniformLocations();
        reportShaderStatus();
      });
  }

  function initGL() {
    var gl = canvas.getContext("webgl2", { alpha: false, antialias: false });
    if (!gl) {
      logIssue("WebGL2 is unavailable in this browser");
      setBanner("WebGL2 unavailable — First Light needs Chrome with WebGL2");
      return Promise.resolve();
    }
    state.gl = gl;
    state.videoTexture = createVideoTexture(gl);
    return setupEffect();
  }

  function resizeCanvasIfNeeded() {
    var rect = stageEl.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
    var scale = state.backingScale;
    var w = Math.max(1, Math.round(rect.width * dpr * scale));
    var h = Math.max(1, Math.round(rect.height * dpr * scale));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
  }

  function uploadVideoFrame() {
    var gl = state.gl;
    gl.bindTexture(gl.TEXTURE_2D, state.videoTexture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    try {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);
    } catch (err) {
      // A frame mid-seek/mid-decode can throw (e.g. zero-size source); skip
      // this upload and keep whatever the texture already holds.
    }
  }

  function drawFrame(mediaTime) {
    var gl = state.gl;
    if (!gl || !state.program) return;
    resizeCanvasIfNeeded();
    uploadVideoFrame();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.useProgram(state.program);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, state.videoTexture);

    var u = state.uniforms;
    if (u.u_video) gl.uniform1i(u.u_video, 0);
    if (u.u_res) gl.uniform2f(u.u_res, canvas.width, canvas.height);
    if (u.u_video_res) gl.uniform2f(u.u_video_res, video.videoWidth || 1, video.videoHeight || 1);
    if (u.u_time) gl.uniform1f(u.u_time, mediaTime);
    if (u.u_pulse) gl.uniform1f(u.u_pulse, state.pulseEnv.value);
    if (u.u_hue) gl.uniform1f(u.u_hue, state.params.hue);
    if (u.u_intensity) gl.uniform1f(u.u_intensity, state.params.intensity);
    if (u.u_bass) gl.uniform1f(u.u_bass, state.frame.bass);
    if (u.u_mid) gl.uniform1f(u.u_mid, state.frame.mid);
    if (u.u_high) gl.uniform1f(u.u_high, state.frame.high);
    if (u.u_flux) gl.uniform1f(u.u_flux, state.frame.flux);

    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  function watchdogTick(durationMs) {
    if (durationMs > FRAME_BUDGET_MS * 2) {
      state.slowStreak++;
      if (state.slowStreak >= WATCHDOG_STREAK) {
        state.backingScale = Math.max(BACKING_SCALE_MIN, state.backingScale / 2);
        state.slowStreak = 0;
        logIssue("watchdog: backing scale reduced to " + state.backingScale);
      }
    } else {
      state.slowStreak = 0;
    }
  }

  // ----------------------------------------------------------- epochs ----

  function bumpEpoch(reason, atMediaTime) {
    var mt = typeof atMediaTime === "number" ? atMediaTime : (video.currentTime || 0);
    state.epoch += 1;
    state.pulseEnv = { value: 0, initialized: false };
    state.eventQueue.length = 0; // drop queued events from the old epoch
    state.eventThrottle = {};
    enqueueEvent({ kind: "epoch", epoch: state.epoch, reason: reason, t: mediaTimeRef(mt) });
  }

  function checkEpochTriggers(mediaTime) {
    if (state.justSeeked) {
      state.justSeeked = false;
      state.lastMediaTime = mediaTime;
      return;
    }
    if (state.lastMediaTime != null && state.lastMediaTime - mediaTime > 0.5) {
      bumpEpoch("loop", mediaTime);
    }
    state.lastMediaTime = mediaTime;
  }

  // ---------------------------------------------------------- analysis ---

  function sampleFeatures(mediaTime) {
    var a = state.analysis;
    if (!a || !a.frames || !a.frames.length) return null;
    var ticks = Math.round(mediaTime * ANALYSIS_TIMEBASE_DEN);
    var idx = Math.floor((ticks - a.start_ticks) / a.hop_ticks);
    idx = clamp(idx, 0, a.frames.length - 1);
    var row = a.frames[idx];
    var out = { _idx: idx };
    for (var i = 0; i < a.names.length; i++) out[a.names[i]] = row[i];
    return out;
  }

  function updatePulse(mediaTime, dtSeconds) {
    var target = 0;
    if (state.analysisReady && state.analysis) {
      var f = sampleFeatures(mediaTime);
      if (f) {
        target = clamp(0.65 * f.bass + 0.35 * f.flux, 0, 1);
        state.frame.bass = f.bass;
        state.frame.mid = f.mid;
        state.frame.high = f.high;
        state.frame.flux = f.flux;
        if (f._idx !== state.lastFeatureIdx) {
          state.lastFeatureIdx = f._idx;
          pulseLight("features");
        }
      }
    } else {
      state.frame.bass = state.frame.mid = state.frame.high = state.frame.flux = 0;
    }

    var env = state.pulseEnv;
    var tauMs = target > env.value ? 12 : 180;
    var alpha = env.initialized ? 1 - Math.exp(-dtSeconds / (tauMs / 1000)) : 1;
    env.value += (target - env.value) * alpha;
    env.initialized = true;
    emitParam("pulse", Math.round(env.value * 1000) / 1000);
  }

  function startAnalysisPoll(clipId) {
    state.analysis = null;
    state.analysisReady = false;
    state.lastFeatureIdx = null;
    var myToken = ++state.analysisToken;

    if (!clipId) {
      setAnalysisStatus("unavailable: outside library roots (declared degradation)");
      return;
    }

    setAnalysisStatus("computing…");
    poll();

    function poll() {
      if (myToken !== state.analysisToken) return; // superseded by a newer clip
      fetch("/api/analysis/" + clipId, { cache: "no-store" })
        .then(function (res) {
          if (myToken !== state.analysisToken) return null;
          if (res.status === 202) {
            return res.json().catch(function () { return {}; }).then(function (data) {
              var pct = typeof data.progress === "number" ? Math.round(data.progress * 100) : null;
              setAnalysisStatus("computing" + (pct != null ? " " + pct + "%" : "…"));
              setTimeout(poll, ANALYSIS_POLL_MS);
            });
          }
          if (res.status === 200) {
            return res.json().then(function (data) {
              state.analysis = data.features;
              state.analysisReady = true;
              setAnalysisStatus("ready");
            });
          }
          return res.json().catch(function () { return {}; }).then(function (data) {
            state.analysisReady = false;
            setAnalysisStatus("unavailable: " + (data.error || ("HTTP " + res.status)) + " (declared degradation)");
          });
        })
        .catch(function (err) {
          if (myToken !== state.analysisToken) return;
          state.analysisReady = false;
          setAnalysisStatus("unavailable: " + errText(err) + " (declared degradation)");
        });
    }
  }

  // -------------------------------------------------------------- probe --

  function fetchProbe(id) {
    return fetch("/api/probe/" + id, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) { state.probe = data; })
      .catch(function () { state.probe = null; })
      .then(queryDecodingInfo);
  }

  function queryDecodingInfo() {
    if (!navigator.mediaCapabilities || !navigator.mediaCapabilities.decodingInfo) {
      state.decodingInfo = null;
      return;
    }
    var width = video.videoWidth || (state.probe && state.probe.video && state.probe.video.width) || 0;
    var height = video.videoHeight || (state.probe && state.probe.video && state.probe.video.height) || 0;
    if (!width || !height) { state.decodingInfo = null; return; }

    var framerate = 30;
    var rate = state.probe && state.probe.video && state.probe.video.rate;
    if (rate) {
      var parts = String(rate).split("/").map(Number);
      if (parts[1]) framerate = parts[0] / parts[1];
    }

    var ext = (state.clip && state.clip.ext) ||
      (state.blobFile && state.blobFile.name && state.blobFile.name.split(".").pop()) || "mp4";
    ext = String(ext).replace(/^\./, "").toLowerCase();

    var config = {
      type: "file",
      video: {
        contentType: guessContentType(ext, state.probe && state.probe.video && state.probe.video.codec),
        width: width,
        height: height,
        bitrate: 8000000,
        framerate: framerate
      }
    };

    navigator.mediaCapabilities.decodingInfo(config).then(function (result) {
      state.decodingInfo = {
        contentType: config.video.contentType,
        supported: result.supported,
        smooth: result.smooth,
        powerEfficient: result.powerEfficient
      };
    }).catch(function () {
      state.decodingInfo = null;
    });
  }

  // --------------------------------------------------------------- MIDI --

  function setMidiStatusText(text) {
    midiStatusEl.textContent = text;
  }

  function connectMIDI() {
    if (!navigator.requestMIDIAccess) {
      setMidiStatusText("MIDI: unavailable in this browser");
      return;
    }
    navigator.requestMIDIAccess().then(function (access) {
      MIDI.access = access;
      var inputs = Array.from(access.inputs.values());
      var preferred = inputs.find(function (i) { return /keylab/i.test(i.name || ""); }) || inputs[0] || null;
      if (!preferred) {
        setMidiStatusText("MIDI: no input found");
        return;
      }
      setMidiInput(preferred);
      access.onstatechange = function () {
        var stillThere = Array.from(access.inputs.values()).some(function (i) { return i.id === preferred.id; });
        if (!stillThere) setMidiStatusText("MIDI: " + preferred.name + " disconnected");
      };
    }).catch(function (err) {
      setMidiStatusText("MIDI: connect failed (" + errText(err) + ")");
    });
  }

  function setMidiInput(input) {
    if (MIDI.input) MIDI.input.onmidimessage = null;
    MIDI.input = input;
    input.onmidimessage = onMidiMessage;
    state.midiInputName = input.name || "MIDI input";
    setMidiStatusText("MIDI: " + state.midiInputName);
  }

  function onMidiMessage(ev) {
    var data = ev.data;
    if (!data || data.length < 3) return;
    var status = data[0] & 0xf0;
    if (status !== 0xb0) return; // control change only
    var cc = data[1];
    var value = data[2];
    var receivedAt = ev.timeStamp;

    pulseLight("midi");
    state.lastCC = { cc: cc, value: value };

    if (MIDI.learning) {
      var target = MIDI.learning;
      var range = target === "hue" ? [0, 360] : [0, 1];
      MIDI.mappings[target] = { cc: cc, range: range };
      MIDI.learning = null;
      mapStatusEl.textContent = "";
      persistMappings();
      renderMapPanel();
    }

    for (var param in MIDI.mappings) {
      if (!Object.prototype.hasOwnProperty.call(MIDI.mappings, param)) continue;
      var map = MIDI.mappings[param];
      if (map.cc !== cc) continue;
      var norm = value / 127;
      var scaled = map.range[0] + norm * (map.range[1] - map.range[0]);
      state.params[param] = scaled;
      state.pendingLatency.push({ param: param, timeStamp: receivedAt });
      enqueueEvent({
        kind: "midi", t: mediaTimeRef(video.currentTime),
        cc: cc, value: value, param: param, mapped: scaled
      });
      emitParam(param, scaled);
    }
  }

  function armLearn() {
    if (!MIDI.input) {
      mapStatusEl.textContent = "connect MIDI first";
      return;
    }
    var target = MIDI.learnQueue[MIDI.learnIndex % MIDI.learnQueue.length];
    MIDI.learnIndex++;
    MIDI.learning = target;
    mapStatusEl.textContent = "listening for a CC to bind " + target + "…";
  }

  function persistMappings() {
    safeLocalStorageSet(MIDI_MAP_KEY, JSON.stringify(MIDI.mappings));
  }

  function loadMappings() {
    var raw = safeLocalStorageGet(MIDI_MAP_KEY);
    if (!raw) return;
    try {
      var parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") MIDI.mappings = parsed;
    } catch (err) {
      // corrupt/foreign value -- ignore and start clean
    }
  }

  function renderMapPanel() {
    mapListEl.innerHTML = "";
    var entries = Object.keys(MIDI.mappings);
    if (!entries.length) {
      var empty = document.createElement("li");
      empty.className = "map-empty";
      empty.id = "map-empty";
      empty.textContent = "no mappings learned";
      mapListEl.appendChild(empty);
      return;
    }
    entries.forEach(function (param) {
      var map = MIDI.mappings[param];
      var li = document.createElement("li");
      li.textContent = "map midi.cc(" + map.cc + ") -> fx." + param +
        " {range: " + map.range[0] + ".." + map.range[1] + "}";
      mapListEl.appendChild(li);
    });
  }

  // ------------------------------------------------------- take/events ---

  function stripInternal(evt) {
    var out = {};
    for (var k in evt) {
      if (k !== "__retried" && Object.prototype.hasOwnProperty.call(evt, k)) out[k] = evt[k];
    }
    return out;
  }

  function emitParam(name, value) {
    enqueueEvent({ kind: "param", t: mediaTimeRef(video.currentTime), name: name, value: value });
  }

  function enqueueEvent(evt) {
    var key = null;
    if (evt.kind === "midi") key = "midi:" + evt.cc;
    else if (evt.kind === "param") key = "param:" + evt.name;

    if (key) {
      var now = performance.now();
      var last = state.eventThrottle[key] || 0;
      if (now - last < EVENT_HZ_LIMIT_MS) return; // at most 10 Hz per key
      state.eventThrottle[key] = now;
    }

    state.eventQueue.push(evt);
    if (state.eventQueue.length > EVENT_QUEUE_CAP) {
      state.eventQueue.splice(0, state.eventQueue.length - EVENT_QUEUE_CAP);
    }
  }

  function buildFilledGraph() {
    if (!state.graphTemplate) return null;
    var graph = JSON.parse(JSON.stringify(state.graphTemplate));
    var uri = state.clip ? (state.clip.path || state.clip.id) : (video.currentSrc || video.src || null);
    graph.assets = graph.assets || {};
    graph.assets.clip = { uri: uri };
    return graph;
  }

  function ensureTakeOpen() {
    if (state.takeId || state.takeOpening) return Promise.resolve();
    state.takeOpening = true;
    var graph = buildFilledGraph();
    var meta = {
      userAgent: navigator.userAgent,
      decodingInfo: state.decodingInfo || null,
      midi: state.midiInputName || null
    };
    return fetch("/api/take/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph: graph, clip_id: state.clip ? state.clip.id : null, meta: meta })
    }).then(function (res) {
      if (!res.ok) { logIssue("take/open failed: HTTP " + res.status); return; }
      return res.json().then(function (data) {
        state.takeId = data.take_id;
        state.takeEventCount = 0;
      });
    }).catch(function (err) {
      logIssue("take/open error: " + errText(err));
    }).then(function () {
      state.takeOpening = false;
    });
  }

  function flushEvents() {
    if (!state.takeId || !state.eventQueue.length) return;
    var batch = state.eventQueue.splice(0, state.eventQueue.length);
    fetch("/api/take/" + state.takeId + "/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: batch.map(stripInternal) })
    }).then(function (res) {
      if (res.status === 409) {
        logIssue("take/events: 409 stale epoch — dropped " + batch.length + " event(s)");
        return;
      }
      if (!res.ok) {
        requeue(batch, "HTTP " + res.status);
        return;
      }
      return res.json().catch(function () { return {}; }).then(function (data) {
        state.takeEventCount += typeof data.accepted === "number" ? data.accepted : batch.length;
      });
    }).catch(function (err) {
      requeue(batch, errText(err));
    });

    function requeue(batch, reason) {
      var retry = batch.filter(function (e) { return !e.__retried; });
      retry.forEach(function (e) { e.__retried = true; });
      if (retry.length) {
        state.eventQueue = retry.concat(state.eventQueue).slice(0, EVENT_QUEUE_CAP);
        logIssue("take/events: " + reason + " — requeued " + retry.length + " event(s)");
      } else {
        logIssue("take/events: " + reason + " — dropped " + batch.length + " event(s) after retry");
      }
    }
  }

  function buildTakeSummary() {
    var lat = latencyStats();
    var pq = playbackQuality();
    return {
      latency_ms: { p50: lat.p50, p95: lat.p95 },
      frames: pq || { dropped: null, total: null },
      decoding: state.decodingInfo || null
    };
  }

  function sendBestEffort(url, body, useBeacon) {
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    } else {
      fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true
      }).catch(function () {});
    }
  }

  function closeTake(useBeacon) {
    if (!state.takeId) return;
    var id = state.takeId;
    if (state.eventQueue.length) {
      var batch = state.eventQueue.splice(0, state.eventQueue.length).map(stripInternal);
      sendBestEffort("/api/take/" + id + "/events", JSON.stringify({ events: batch }), useBeacon);
    }
    sendBestEffort("/api/take/" + id + "/close", JSON.stringify({ summary: buildTakeSummary() }), useBeacon);
    state.takeId = null;
    state.takeEventCount = 0;
  }

  // ------------------------------------------------------------- plan ----

  function refreshPlan() {
    var ready = state.graphTemplate
      ? Promise.resolve(state.graphTemplate)
      : fetch("/api/graph/first-light", { cache: "no-store" })
          .then(function (res) {
            if (!res.ok) throw new Error("HTTP " + res.status);
            return res.json();
          })
          .then(function (data) { state.graphTemplate = data; return data; });

    ready.then(function () {
      var graph = buildFilledGraph();
      if (!graph) { planTextEl.textContent = "no plan yet — load a clip"; return; }
      return fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph: graph })
      }).then(function (res) {
        if (res.ok) {
          return res.json().then(function (data) {
            planTextEl.textContent = data.text || JSON.stringify(data.plan, null, 2);
          });
        }
        return res.json().catch(function () { return {}; }).then(function (data) {
          var problems = Array.isArray(data.problems) ? data.problems.join("\n") : ("HTTP " + res.status);
          planTextEl.textContent = "plan rejected:\n" + problems;
        });
      });
    }).catch(function (err) {
      planTextEl.textContent = "plan unavailable: " + errText(err);
    });
  }

  // ----------------------------------------------------------- library ---

  function loadLibrary() {
    fetch("/api/library", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        state.libraryClips = Array.isArray(data.clips) ? data.clips : [];
      })
      .catch(function (err) {
        state.libraryClips = [];
        logIssue("library load failed: " + errText(err));
      })
      .then(renderLibrary);
  }

  function renderLibrary() {
    var q = (libSearchEl.value || "").trim().toLowerCase();
    var items = state.libraryClips.filter(function (c) {
      return !q || (c.name || "").toLowerCase().indexOf(q) !== -1;
    });
    libListEl.innerHTML = "";
    if (!items.length) {
      var li = document.createElement("li");
      li.className = "lib-empty";
      li.textContent = state.libraryClips.length ? "no matches" : "library empty";
      libListEl.appendChild(li);
      return;
    }
    items.forEach(function (clip) {
      var item = document.createElement("li");
      item.className = "lib-item";
      item.tabIndex = 0;
      if (state.clip && state.clip.id === clip.id) item.classList.add("active");

      var name = document.createElement("div");
      name.className = "name";
      name.textContent = clip.name || clip.id;

      var meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = formatBytes(clip.size) + " · " + String(clip.ext || "").toUpperCase();

      item.appendChild(name);
      item.appendChild(meta);
      item.addEventListener("click", function () { loadClip({ kind: "library", clip: clip }); });
      item.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          loadClip({ kind: "library", clip: clip });
        }
      });
      libListEl.appendChild(item);
    });
  }

  // ----------------------------------------------------------- player ----

  function loadClip(source) {
    if (state.takeId) closeTake(false);

    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = null;
    }

    state.analysisToken++; // invalidate any in-flight poll for the previous clip
    state.epoch = 0;
    state.pulseEnv = { value: 0, initialized: false };
    state.eventQueue = [];
    state.eventThrottle = {};
    state.lastMediaTime = null;
    state.justSeeked = false;
    state.analysis = null;
    state.analysisReady = false;
    state.lastFeatureIdx = null;
    state.probe = null;
    state.decodingInfo = null;
    hideBanner();

    if (source.kind === "blob") {
      state.clip = null;
      state.blobFile = source.file;
      state.objectUrl = source.objectUrl;
      video.src = source.objectUrl;
      setBanner("analysis unavailable: outside library roots");
      startAnalysisPoll(null);
    } else {
      state.clip = source.clip;
      state.blobFile = null;
      video.src = "/api/media/" + source.clip.id;
      startAnalysisPoll(source.clip.id);
      fetchProbe(source.clip.id);
    }

    pulseLight("clip");
    stageEl.classList.add("has-clip");
    renderLibrary();
    refreshPlan();
    video.load();
  }

  function resolveDroppedFile(file) {
    var qs = new URLSearchParams({ name: file.name, size: String(file.size) });
    return fetch("/api/resolve?" + qs.toString())
      .then(function (res) {
        if (res.ok) return res.json().then(function (data) { loadClip({ kind: "resolved", clip: data.clip }); });
        var objectUrl = URL.createObjectURL(file);
        loadClip({ kind: "blob", file: file, objectUrl: objectUrl });
      })
      .catch(function (err) {
        logIssue("resolve failed: " + errText(err));
        var objectUrl = URL.createObjectURL(file);
        loadClip({ kind: "blob", file: file, objectUrl: objectUrl });
      });
  }

  function updateSeekUi() {
    if (video.duration) {
      seekEl.value = String(Math.round((video.currentTime / video.duration) * 1000));
    }
    timeCurEl.textContent = formatTime(video.currentTime);
    timeDurEl.textContent = formatTime(video.duration || 0);
  }

  function toggleLoop() {
    video.loop = !video.loop;
    loopBtn.setAttribute("aria-pressed", String(video.loop));
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(function () {});
    } else if (stageEl.requestFullscreen) {
      stageEl.requestFullscreen().catch(function () {});
    }
  }

  function togglePlay() {
    if (video.paused) video.play().catch(function (err) { logIssue("play() rejected: " + errText(err)); });
    else video.pause();
  }

  // --------------------------------------------------------- frame loop --

  // `gen` (a loop generation stamp) guards against video.load() cutting the
  // recursive rVFC/rAF chain out from under a clip change: ensureLoopRunning
  // bumps the generation and starts a fresh chain unconditionally every time
  // a clip's metadata loads, and any older, superseded callback that still
  // fires (whether or not the browser actually cancelled it) checks its own
  // stamp and quietly stops instead of drawing stale frames or -- worse --
  // running two concurrent chains at once.
  function scheduleNextFrame(gen) {
    if ("requestVideoFrameCallback" in video) {
      video.requestVideoFrameCallback(function (now, metadata) {
        if (gen !== state.loopGeneration) return;
        onVideoFrame(metadata.mediaTime, metadata.expectedDisplayTime, metadata, gen);
      });
    } else {
      requestAnimationFrame(function () {
        if (gen !== state.loopGeneration) return;
        onVideoFrame(video.currentTime, performance.now(), null, gen);
      });
    }
  }

  function ensureLoopRunning() {
    state.loopGeneration++;
    state.lastFrameNow = performance.now();
    scheduleNextFrame(state.loopGeneration);
  }

  function drainLatency(expectedDisplayTime) {
    if (!state.pendingLatency.length) return;
    for (var i = 0; i < state.pendingLatency.length; i++) {
      pushLatencySample(expectedDisplayTime - state.pendingLatency[i].timeStamp);
    }
    state.pendingLatency.length = 0;
  }

  function onVideoFrame(mediaTime, expectedDisplayTime, metadata, gen) {
    var nowPerf = performance.now();
    var dt = clamp((nowPerf - (state.lastFrameNow || nowPerf)) / 1000, 0, 0.1);
    state.lastFrameNow = nowPerf;

    checkEpochTriggers(mediaTime);
    updatePulse(mediaTime, dt);
    drainLatency(expectedDisplayTime);

    if (!state.glLost) {
      drawFrame(mediaTime);
      pulseLight("decode");
      pulseLight("fx");
      pulseLight("screen");
    }

    var durationMs = performance.now() - nowPerf;
    watchdogTick(durationMs);
    scheduleNextFrame(gen);
  }

  // ------------------------------------------------------- context loss --

  function wireContextEvents() {
    canvas.addEventListener("webglcontextlost", function (e) {
      e.preventDefault();
      state.glLost = true;
      stageEl.classList.add("gl-bypass");
      setBanner("WebGL context lost — showing the video directly (bypass)");
      enqueueEvent({ kind: "degraded", t: mediaTimeRef(video.currentTime), reason: "context-lost" });
    });
    canvas.addEventListener("webglcontextrestored", function () {
      state.glLost = false;
      stageEl.classList.remove("gl-bypass");
      initGL().then(function () {
        bumpEpoch("restore", video.currentTime);
        hideBanner();
      });
    });
  }

  // ------------------------------------------------------------ keyboard --

  function isTypingTarget(el) {
    if (!el) return false;
    var tag = el.tagName;
    if (tag === "TEXTAREA") return true;
    if (tag === "INPUT") {
      var type = (el.type || "text").toLowerCase();
      return type === "text" || type === "search";
    }
    return false;
  }

  function wireKeyboard() {
    window.addEventListener("keydown", function (e) {
      if (isTypingTarget(document.activeElement)) return;
      if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "l" || e.key === "L") {
        toggleLoop();
      } else if (e.key === "f" || e.key === "F") {
        toggleFullscreen();
      }
    });
  }

  // --------------------------------------------------------------- wire --

  function wireEvents() {
    video.addEventListener("loadedmetadata", function () {
      updateSeekUi();
      queryDecodingInfo();
      ensureLoopRunning();
    });
    video.addEventListener("error", function () {
      var err = video.error;
      var reason = err ? ("code " + err.code + (err.message ? ": " + err.message : "")) : "unknown error";
      setBanner("video failed to load — " + reason);
      logIssue("video element error: " + reason);
      enqueueEvent({ kind: "degraded", t: mediaTimeRef(video.currentTime || 0), reason: "video-error: " + reason });
    });
    video.addEventListener("seeking", function () {
      bumpEpoch("seek", video.currentTime);
      state.justSeeked = true;
      enqueueEvent({ kind: "seek", t: mediaTimeRef(video.currentTime), to: video.currentTime });
    });
    video.addEventListener("play", function () {
      playBtn.setAttribute("aria-pressed", "true");
      playBtn.textContent = "Pause";
      ensureTakeOpen().then(function () {
        enqueueEvent({ kind: "play", t: mediaTimeRef(video.currentTime) });
      });
    });
    video.addEventListener("pause", function () {
      playBtn.setAttribute("aria-pressed", "false");
      playBtn.textContent = "Play";
      enqueueEvent({ kind: "pause", t: mediaTimeRef(video.currentTime) });
    });
    video.addEventListener("timeupdate", updateSeekUi);

    playBtn.addEventListener("click", togglePlay);
    loopBtn.addEventListener("click", toggleLoop);
    fullscreenBtn.addEventListener("click", toggleFullscreen);
    seekEl.addEventListener("input", function () {
      if (!video.duration) return;
      video.currentTime = (Number(seekEl.value) / 1000) * video.duration;
    });

    midiBtn.addEventListener("click", connectMIDI);
    learnBtn.addEventListener("click", armLearn);
    rackBtn.addEventListener("click", function () {
      var collapsed = layoutEl.classList.toggle("rack-collapsed");
      rackBtn.setAttribute("aria-pressed", String(!collapsed));
    });

    libSearchEl.addEventListener("input", renderLibrary);

    stageEl.addEventListener("dragover", function (e) {
      e.preventDefault();
      stageEl.classList.add("drag-over");
    });
    stageEl.addEventListener("dragleave", function () {
      stageEl.classList.remove("drag-over");
    });
    stageEl.addEventListener("drop", function (e) {
      e.preventDefault();
      stageEl.classList.remove("drag-over");
      var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) resolveDroppedFile(file);
    });

    window.addEventListener("resize", resizeCanvasIfNeeded);
    window.addEventListener("pagehide", function () {
      closeTake(true);
    });

    wireContextEvents();
    wireKeyboard();
  }

  // -------------------------------------------------------------- init ---

  function init() {
    cacheDom();
    loadMappings();
    renderMapPanel();
    wireEvents();

    initGL().then(function () {
      resizeCanvasIfNeeded();
      loadLibrary();
      refreshPlan();
      updateHud();

      setInterval(updateHud, HUD_INTERVAL_MS);
      setInterval(tickLights, LIGHT_INTERVAL_MS);
      setInterval(flushEvents, FLUSH_INTERVAL_MS);
    });
  }

  // `defer` guarantees the DOM is fully parsed before this script runs, so
  // no DOMContentLoaded listener is needed.
  init();
})();
