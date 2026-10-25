// HDR check (arsenal/web/hdr-check.html): what Chrome and the display report, and still test patches for the OLED.
//
// Brighter-than-white output uses the only shipping route in Chrome: a WebGPU canvas configured rgba16float with
// toneMapping {mode: "extended"} (Chrome 129+; getConfiguration() reports what was kept since Chrome 131). A float
// canvas in the "srgb" or "display-p3" colour space takes values encoded with the sRGB curve, extended past 1.0
// (CSS Color 4), so a patch meant to be N times SDR white is written as srgbEncode(N). A "display-p3-linear" canvas
// (expected in Chrome 157) takes N as it is; the page uses one when the browser accepts it.
//
// Chrome does not tone-map extended canvases: anything above the display's headroom is clipped further down the chain.
// That is why patch 2 asks the viewer to find the headroom by eye; the browser does not expose it (fingerprinting).
//
// Safety: nothing animates. Canvases are drawn once and again only on resize or when the screen's dynamic range changes.
// Every patch above 1.0 is small. A lost WebGPU device is reported and never retried automatically.
//
// ?fallback=1 asks WebGPU for the software fallback adapter only, so headless checks never open a device on the real GPU.
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const params = new URLSearchParams(location.search);
  const FORCE_FALLBACK = params.get("fallback") === "1";
  const STORE_KEY = "hdr-check.headroom.v1";

  const WHITE_STEPS = [1, 2, 4, 8];
  const LADDER_STEPS = [1, 1.25, 1.5, 2, 3, 4, 6, 8];
  const BEAM_HDR_GAIN = 6;
  // the six colours of the gamut tiles, as sRGB / P3 / Rec.2020 coordinates in 0..1
  const HUES = [["red", [1, 0, 0]], ["yellow", [1, 1, 0]], ["green", [0, 1, 0]],
                ["cyan", [0, 1, 1]], ["blue", [0, 0, 1]], ["magenta", [1, 0, 1]]];
  const SHADOW_STEPS = [0.001, 0.003, 0.01, 0.03];  // linear light, 1 = SDR white

  const report = { page: "hdr-check/v1", url: location.href, at: new Date().toISOString(), facts: {}, errors: [] };
  const state = { screen: null, browser: null, webgl: null, canvas2d: null, css: null, gpu: null, deviceLost: null };
  window.hdrCheck = { report, ready: null };

  const noteError = (where, err) => {
    const msg = `${where}: ${err && err.message ? err.message : String(err)}`;
    report.errors.push(msg);
    const el = $("#errors");
    if (el) el.textContent = "Page errors:\n" + report.errors.join("\n");
  };
  window.addEventListener("error", (e) => noteError("script", e.error || e.message));
  window.addEventListener("unhandledrejection", (e) => noteError("promise", e.reason));

  // ------------------------------------------------------------------------------------------------- colour maths
  const enc1 = (x) => {  // the sRGB transfer curve, extended symmetrically past 0 and 1 (CSS Color 4)
    const a = Math.abs(x);
    const e = a <= 0.0031308 ? 12.92 * a : 1.055 * Math.pow(a, 1 / 2.4) - 0.055;
    return x < 0 ? -e : e;
  };
  const enc = (c) => c.map(enc1);
  const dec1 = (v) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
  // linear sRGB to linear Display-P3 (same white point, D65)
  const SRGB_TO_P3 = [[0.8224621, 0.1775380, 0.0], [0.0331941, 0.9668058, 0.0], [0.0170827, 0.0723974, 0.9105199]];
  const mul3 = (m, v) => m.map((r) => r[0] * v[0] + r[1] * v[1] + r[2] * v[2]);
  const srgbToP3Encoded = (c) => enc(mul3(SRGB_TO_P3, c.map(dec1)));
  const fmt = (n, d = 3) => (Number.isFinite(n) ? String(+n.toFixed(d)) : String(n));

  // ---------------------------------------------------------------------------------------------- detection
  const mq = (q) => { const m = matchMedia(q); return { parses: m.media !== "not all", matches: m.matches }; };

  function detectScreen() {
    const gamut = mq("(color-gamut: rec2020)").matches ? "rec2020" : mq("(color-gamut: p3)").matches ? "p3"
      : mq("(color-gamut: srgb)").matches ? "srgb" : "unknown";
    const dpr = window.devicePixelRatio || 1;
    return {
      hdr: mq("(dynamic-range: high)").matches,
      videoHdr: mq("(video-dynamic-range: high)").matches,
      gamut, colorDepth: screen.colorDepth, dpr,
      cssSize: [screen.width, screen.height],
      deviceSize: [Math.round(screen.width * dpr), Math.round(screen.height * dpr)],
    };
  }

  async function detectBrowser() {
    let name = "", major = 0;
    try {
      if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
        const v = await navigator.userAgentData.getHighEntropyValues(["fullVersionList"]);
        const list = v.fullVersionList || [];
        const pick = list.find((b) => b.brand === "Google Chrome") || list.find((b) => /Chrom|Edge|Opera/.test(b.brand));
        if (pick) name = `${pick.brand} ${pick.version}`;
      }
    } catch { /* low-entropy fallback below */ }
    const m = navigator.userAgent.match(/(HeadlessChrome|Chrome|Firefox|Version)\/([\d.]+)/);
    if (!name) name = m ? `${m[1]} ${m[2]}` : navigator.userAgent;
    const mm = name.match(/(\d+)\./);
    major = mm ? Number(mm[1]) : 0;
    return { name, major, headless: /HeadlessChrome/.test(navigator.userAgent) };
  }

  function detectWebGL2() {
    const out = { available: false };
    const c = document.createElement("canvas");
    c.width = c.height = 8;
    let gl = null;
    // alpha stays on (the default): drawingBufferStorage refuses a context made with alpha: false
    try { gl = c.getContext("webgl2", { antialias: false }); } catch (e) { out.error = e.message; }
    if (!gl) return out;
    out.available = true;
    try {
      const dbg = gl.getExtension("WEBGL_debug_renderer_info");
      out.renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    } catch { out.renderer = "(hidden)"; }
    out.ext = {};
    for (const name of ["EXT_color_buffer_float", "EXT_color_buffer_half_float", "EXT_float_blend", "OES_texture_float_linear"]) {
      out.ext[name] = !!gl.getExtension(name);
    }
    out.p3 = false;
    if ("drawingBufferColorSpace" in gl) {
      try { gl.drawingBufferColorSpace = "display-p3"; out.p3 = gl.drawingBufferColorSpace === "display-p3"; } catch { out.p3 = false; }
    }
    out.linear = false;
    try { gl.drawingBufferColorSpace = "display-p3-linear"; out.linear = gl.drawingBufferColorSpace === "display-p3-linear"; } catch { out.linear = false; }
    try { gl.drawingBufferColorSpace = "srgb"; } catch { /* older browsers have no such property */ }
    out.float16 = false;
    if (typeof gl.drawingBufferStorage === "function") {
      try { gl.drawingBufferStorage(gl.RGBA16F, 8, 8); out.float16 = gl.drawingBufferFormat === gl.RGBA16F; } catch (e) { out.float16Error = e.message; }
      if (out.float16) {
        // write values outside 0..1 and read them back: a float buffer keeps them
        gl.clearColor(2.5, 0.5, -0.25, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const px = new Float32Array(4);
        try { gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.FLOAT, px); out.readback = Array.from(px.slice(0, 3), (v) => +v.toFixed(3)); } catch (e) { out.readbackError = e.message; }
        gl.getError();
      }
    }
    out.toneMappingApi = typeof gl.drawingBufferToneMapping === "function";
    out.toneMappingExtended = false;
    if (out.toneMappingApi) {
      try {
        gl.drawingBufferToneMapping({ mode: "extended" });
        const tm = gl.drawingBufferToneMapping();
        out.toneMappingExtended = !!tm && tm.mode === "extended";
      } catch (e) { out.toneMappingError = e.message; }
    }
    const lose = gl.getExtension("WEBGL_lose_context");
    if (lose) lose.loseContext();
    return out;
  }

  function detectCanvas2D() {
    const out = { p3: false, float16: false };
    try {
      const ctx = document.createElement("canvas").getContext("2d", { colorSpace: "display-p3" });
      out.p3 = !!ctx && !!ctx.getContextAttributes && ctx.getContextAttributes().colorSpace === "display-p3";
    } catch { out.p3 = false; }
    try {
      const ctx = document.createElement("canvas").getContext("2d", { colorType: "float16" });
      out.float16 = !!ctx && !!ctx.getContextAttributes && ctx.getContextAttributes().colorType === "float16";
    } catch { out.float16 = false; }
    return out;
  }

  function detectCss() {
    const s = (p, v) => { try { return CSS.supports(p, v); } catch { return false; } };
    return { p3: s("color", "color(display-p3 1 0 0)"), rec2020: s("color", "color(rec2020 1 0 0)"),
             dynamicRangeLimit: s("dynamic-range-limit", "no-limit") };
  }

  async function initWebGPU() {
    const out = { api: "gpu" in navigator, adapter: null, device: null, extended: false, p3: false, linear: false,
                  colorSpace: "display-p3", forcedFallback: FORCE_FALLBACK };
    if (!out.api) { out.why = "navigator.gpu is missing: WebGPU is switched off in this browser"; return out; }
    try { out.preferredFormat = navigator.gpu.getPreferredCanvasFormat(); } catch { /* informational only */ }
    let adapter = null;
    try {
      adapter = await navigator.gpu.requestAdapter(FORCE_FALLBACK ? { forceFallbackAdapter: true } : {});
    } catch (e) { out.why = `requestAdapter threw: ${e.message}`; return out; }
    if (!adapter) {
      out.why = FORCE_FALLBACK ? "no software fallback adapter (the page was opened with ?fallback=1)"
        : "no adapter: Chrome blocked WebGPU on this GPU, or the GPU is running in software";
      return out;
    }
    const info = adapter.info || {};
    out.adapter = {
      vendor: info.vendor || "", architecture: info.architecture || "", device: info.device || "",
      description: info.description || "",
      fallback: !!(info.isFallbackAdapter !== undefined ? info.isFallbackAdapter : adapter.isFallbackAdapter),
    };
    try { out.device = await adapter.requestDevice(); } catch (e) { out.why = `requestDevice failed: ${e.message}`; return out; }
    const device = out.device;
    device.addEventListener("uncapturederror", (e) => noteError("webgpu", e.error));
    device.lost.then((info) => onDeviceLost(info));

    // Configure a throwaway canvas the HDR way and ask the browser what it kept.
    const probe = document.createElement("canvas");
    probe.width = probe.height = 4;
    const ctx = probe.getContext("webgpu");
    if (!ctx) { out.why = "the canvas refused a webgpu context"; return out; }
    out.getConfiguration = typeof ctx.getConfiguration === "function";
    device.pushErrorScope("validation");
    try {
      ctx.configure({ device, format: "rgba16float", colorSpace: "display-p3", toneMapping: { mode: "extended" }, alphaMode: "opaque" });
      const conf = out.getConfiguration ? ctx.getConfiguration() : null;
      // with no getConfiguration (Chrome 129-130) the answer is unknown; treat it as worth trying
      out.extended = conf ? !!(conf.toneMapping && conf.toneMapping.mode === "extended") : null;
      out.p3 = conf ? conf.colorSpace === "display-p3" : null;
    } catch (e) { out.configureError = e.message; }
    const scopeErr = await device.popErrorScope();
    if (scopeErr) { out.configureError = scopeErr.message; out.extended = false; }
    try {
      ctx.unconfigure();
      ctx.configure({ device, format: "rgba16float", colorSpace: "display-p3-linear", toneMapping: { mode: "extended" }, alphaMode: "opaque" });
      out.linear = !!(out.getConfiguration && ctx.getConfiguration().colorSpace === "display-p3-linear");
    } catch { out.linear = false; }  // a TypeError before Chrome 157: the colour space is not in the enum yet
    try { ctx.unconfigure(); } catch { /* nothing configured */ }
    out.colorSpace = out.linear ? "display-p3-linear" : "display-p3";
    return out;
  }

  function onDeviceLost(info) {
    state.deviceLost = info && info.message ? info.message : "lost";
    if (info && info.reason === "destroyed") return;
    noteError("webgpu", `device lost (${state.deviceLost}). Reload the page to try again; it does not retry by itself.`);
    renderVerdict();
  }

  // ----------------------------------------------------------------------------------------- facts table
  function readSavedHeadroom() {
    try { const raw = localStorage.getItem(STORE_KEY); return raw ? JSON.parse(raw) : null; } catch { return null; }
  }
  function writeSavedHeadroom(value) {
    const s = state.screen;
    const rec = { headroom: value, at: new Date().toISOString(), screen: `${s.deviceSize[0]}x${s.deviceSize[1]}`, dpr: s.dpr,
                  browser: state.browser ? state.browser.name : "" };
    try { localStorage.setItem(STORE_KEY, JSON.stringify(rec)); return rec; } catch { return null; }
  }

  function buildFacts() {
    const rows = [];
    const add = (key, label, value, meaning, tone = "", raw = value) => { rows.push({ label, value, meaning, tone }); report.facts[key] = raw; };
    const s = state.screen, b = state.browser, gl = state.webgl, c2 = state.canvas2d, css = state.css, g = state.gpu;

    add("browser", "Browser", b.name,
      b.major && b.major < 157 ? "Linear colour spaces arrive in Chrome 157 (stable 2026-11-03); WebGL HDR is still behind a flag."
        : "Recent enough for everything this page tests.", "", b);
    add("dynamicRange", "Screen says HDR (dynamic-range: high)", s.hdr ? "yes" : "no",
      s.hdr ? "Windows HDR is on for the screen this window is on. It does not say how much room above white there is: patch 2 does."
        : "Chrome sees an SDR screen, so nothing can be brighter than white. Turn on Windows HDR, or move the window to the HDR screen.",
      s.hdr ? "ok" : "bad", s.hdr);
    add("gamut", "Colour gamut (color-gamut)", s.gamut === "rec2020" ? "Rec.2020" : s.gamut === "p3" ? "Display-P3" : s.gamut,
      s.gamut === "srgb" ? "The screen is reported as sRGB only: the deeper colours of patches 4 and 5 will not show."
        : "Wider than sRGB: deeper reds, greens and cyans are possible.", s.gamut === "srgb" ? "warn" : "ok", s.gamut);
    add("colorDepth", "Colour depth", `${s.colorDepth} bits`,
      s.colorDepth >= 30 ? "30 usually means the 10-bit HDR desktop. A hint only." : "24 means 8 bits per channel. A hint only.", "", s.colorDepth);
    add("screen", "Screen size", `${s.deviceSize[0]} x ${s.deviceSize[1]} px at ${fmt(s.dpr, 2)}x scale`,
      "The screen this window is on.", "", { css: s.cssSize, device: s.deviceSize, dpr: s.dpr });

    if (g.device) {
      const a = g.adapter;
      const desc = [a.vendor, a.architecture, a.description || a.device].filter(Boolean).join(" / ") || "(no details)";
      add("webgpu", "WebGPU", `yes: ${desc}${a.fallback ? " (software fallback)" : ""}`,
        "WebGPU is the only shipping way for a page to go brighter than white.", a.fallback ? "warn" : "ok", a);
    } else {
      add("webgpu", "WebGPU", "no", g.why || "not available", "bad", { why: g.why });
    }
    if (g.device) {
      const ext = g.extended;
      add("extended", "Brighter-than-white canvas (WebGPU rgba16float, extended)",
        ext === true ? "works" : ext === null ? "unknown (no getConfiguration)" : "refused",
        ext === true ? (s.hdr ? "The browser accepted extended range. How bright it really gets depends on Windows' headroom: see patches 1 and 2."
          : "The browser accepted extended range, but the screen is in SDR mode, so it will look like plain white.")
          : ext === null ? "This Chrome cannot report what it kept; the patches try anyway."
          : `The browser dropped the extended mode${g.configureError ? ` (${g.configureError})` : ""}, so nothing goes above white.`,
        ext === true ? (s.hdr ? "ok" : "warn") : ext === null ? "warn" : "bad", ext);
      add("gpuP3", "WebGPU Display-P3 canvas", g.p3 === true ? "yes" : g.p3 === null ? "unknown" : "no",
        g.p3 ? "HDR patches can use the wider P3 primaries." : "HDR patches are limited to sRGB primaries.", g.p3 ? "ok" : "warn", g.p3);
      add("gpuLinear", "Linear colour spaces (display-p3-linear)", g.linear ? "yes" : "not yet",
        g.linear ? "Shaders can write linear light directly; this page does." : "Expected in Chrome 157; until then shaders encode with the sRGB curve (this page does).",
        "", g.linear);
    }

    if (gl.available) {
      add("webgl2", "WebGL2", gl.renderer || "yes", "What the VJ rig renders with today.", "ok", gl.renderer);
      add("glP3", "WebGL2 Display-P3 drawing buffer", gl.p3 ? "yes" : "no",
        gl.p3 ? "The rig can reach P3 colours at normal (SDR) brightness: patch 5." : "The rig is limited to sRGB colours in this browser.",
        gl.p3 ? "ok" : "warn", gl.p3);
      const rb = gl.readback ? `wrote (2.5, 0.5, -0.25), read (${gl.readback.join(", ")})` : "";
      add("glFloat16", "WebGL2 float16 drawing buffer", gl.float16 ? `yes; ${rb}` : "no",
        gl.float16 ? "Smoother dark gradients (patch 6). Values above 1 survive inside the buffer, but WebGL output is still clipped at white."
          : "Only 8-bit drawing buffers here, so dark gradients can band.", gl.float16 ? "ok" : "warn", { ok: gl.float16, readback: gl.readback });
      const e = gl.ext;
      add("glExt", "WebGL2 float render targets",
        `float ${e.EXT_color_buffer_float ? "yes" : "no"}, half-float ${e.EXT_color_buffer_half_float ? "yes" : "no"}, ` +
        `float blend ${e.EXT_float_blend ? "yes" : "no"}, float filtering ${e.OES_texture_float_linear ? "yes" : "no"}`,
        "What the rig's bloom and feedback passes can render into.", e.EXT_color_buffer_float ? "ok" : "warn", e);
      add("glToneMapping", "WebGL2 HDR output (drawingBufferToneMapping)",
        gl.toneMappingExtended ? "available (experimental flag on)" : gl.toneMappingApi ? "present but refused" : "not available",
        gl.toneMappingExtended ? "WebGL can try to go above white directly; patch 1 shows an extra square drawn this way."
          : "Only behind chrome://flags \"Experimental Web Platform features\" in this Chrome. Not needed: WebGPU covers it.",
        gl.toneMappingExtended ? "ok" : "", gl.toneMappingExtended);
    } else {
      add("webgl2", "WebGL2", "no", gl.error || "WebGL2 is not available, so the VJ rig cannot run here.", "bad", false);
    }
    add("canvas2d", "Canvas 2D", `Display-P3 ${c2.p3 ? "yes" : "no"}, float16 ${c2.float16 ? "yes" : "no"}`,
      "Not used by the rig; listed for completeness.", "", c2);
    add("css", "Page colours (CSS)", `display-p3 ${css.p3 ? "yes" : "no"}, rec2020 ${css.rec2020 ? "yes" : "no"}`,
      "Whether the page itself can name colours beyond sRGB (patch 4).", css.p3 ? "ok" : "warn", css);
    const saved = readSavedHeadroom();
    add("savedHeadroom", "Headroom you picked", saved ? `${fmt(saved.headroom, 2)}x (picked ${saved.at.slice(0, 10)} on ${saved.screen})` : "not picked yet",
      "From patch 2. Saved in this browser only.", "", saved);

    const tbody = $("#facts tbody");
    tbody.textContent = "";
    for (const r of rows) {
      const tr = document.createElement("tr");
      const td = (cls, text) => { const el = document.createElement("td"); el.className = cls; el.textContent = text; tr.appendChild(el); return el; };
      td("label", r.label);
      const v = td("value", r.value);
      if (r.tone) v.classList.add(`tone-${r.tone}`);
      td("meaning", r.meaning);
      tbody.appendChild(tr);
    }
    report.rows = rows.map((r) => ({ label: r.label, value: r.value }));
  }

  function renderVerdict() {
    const s = state.screen, g = state.gpu, gl = state.webgl;
    const lines = [];
    if (state.deviceLost) lines.push(["bad", "The WebGPU device was lost (a driver reset, perhaps). Reload the page to try again."]);
    if (g && g.device && g.extended !== false && s.hdr) {
      lines.push(["ok", "Brighter-than-white output works in this browser. Patches 1 and 2 show how much room above white Windows actually gives it."]);
    } else if (g && g.device && g.extended !== false) {
      lines.push(["warn", "The browser can draw brighter than white, but this screen is in SDR mode right now, so it will all look like plain white."]);
    } else if (g && g.device) {
      lines.push(["bad", "WebGPU works but refused the extended range, so nothing here can go brighter than white."]);
    } else {
      lines.push(["bad", `No WebGPU here (${g ? g.why : "not checked"}), so nothing can go brighter than white.`]);
    }
    if (s.gamut !== "srgb" && gl && gl.p3) lines.push(["ok", "Wide colour is available, in page colours and in WebGL2 (the rig's way): see patches 4 and 5."]);
    else if (s.gamut !== "srgb") lines.push(["warn", "The screen reports wide colour, but WebGL2 cannot use a P3 drawing buffer here."]);
    else lines.push(["warn", "The screen is reported as sRGB, so the deeper colours will not show."]);
    if (s.hdr) lines.push(["", "Note: \"HDR on\" alone does not prove there is room above white. On 2026-10-24 Windows gave Chrome only 6% (see the box below)."]);
    const el = $("#verdict");
    el.textContent = "";
    for (const [tone, text] of lines) {
      const p = document.createElement("p");
      p.className = "line" + (tone ? ` tone-${tone}` : "");
      p.textContent = text;
      el.appendChild(p);
    }
    report.verdict = lines.map(([, t]) => t);
  }

  // -------------------------------------------------------------------------------------------- WebGPU patches
  const gpuOk = () => state.gpu && state.gpu.device && state.gpu.extended !== false && !state.deviceLost;

  function sizeCanvas(canvas) {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(r.width * dpr)), h = Math.max(1, Math.round(r.height * dpr));
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;
    return { w, h, dpr };
  }

  function gpuContext(canvas, extended = true) {
    const g = state.gpu;
    const ctx = canvas.getContext("webgpu");
    ctx.configure({ device: g.device, format: "rgba16float", colorSpace: g.colorSpace,
                    toneMapping: { mode: extended ? "extended" : "standard" }, alphaMode: "opaque" });
    return ctx;
  }

  // a flat patch: the canvas is cleared to `times` x SDR white (neutral grey, so it means the same in any primaries)
  function drawFlat(canvas, times) {
    const g = state.gpu;
    sizeCanvas(canvas);
    const ctx = gpuContext(canvas, true);
    const v = g.linear ? times : enc1(times);
    const encoder = g.device.createCommandEncoder();
    const pass = encoder.beginRenderPass({ colorAttachments: [{ view: ctx.getCurrentTexture().createView(),
      loadOp: "clear", storeOp: "store", clearValue: { r: v, g: v, b: v, a: 1 } }] });
    pass.end();
    g.device.queue.submit([encoder.finish()]);
  }

  // a flat patch drawn through WebGL2's experimental tone mapping (only with the Chrome flag), for an A/B with WebGPU
  function drawFlatWebGL(canvas, times) {
    const { w, h } = sizeCanvas(canvas);
    const gl = canvas.getContext("webgl2", { antialias: false });  // alpha stays on: drawingBufferStorage requires it
    if (!gl || !useFloat16Buffer(gl, w, h)) return false;
    gl.drawingBufferToneMapping({ mode: "extended" });
    const v = enc1(times);
    gl.viewport(0, 0, w, h);
    gl.clearColor(v, v, v, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    return true;
  }

  // A float16 drawing buffer needs a context made with alpha: true (the default) and a float colour-buffer extension
  // enabled first; without them drawingBufferStorage fails with INVALID_OPERATION or INVALID_ENUM.
  function useFloat16Buffer(gl, w, h) {
    if (typeof gl.drawingBufferStorage !== "function") return false;
    if (!gl.getExtension("EXT_color_buffer_half_float") && !gl.getExtension("EXT_color_buffer_float")) return false;
    gl.drawingBufferStorage(gl.RGBA16F, w, h);
    return gl.drawingBufferFormat === gl.RGBA16F;
  }

  function squareEl(label) {
    const wrap = document.createElement("span");  // spans: the ladder puts these inside buttons
    wrap.className = "sq";
    const canvas = document.createElement("canvas");
    const cap = document.createElement("span");
    cap.className = "caption";
    cap.textContent = label;
    wrap.append(canvas, cap);
    return { wrap, canvas };
  }

  function renderWhiteSquares() {
    const box = $("#white-squares"), note = $("#white-note");
    box.textContent = "";
    note.textContent = "";
    const glFlag = !!(state.webgl && state.webgl.toneMappingExtended);
    if (!gpuOk() && !glFlag) {
      note.textContent = `Hidden: this browser could not open an extended-range canvas (${whyNoHdr()}), so it cannot show anything brighter than white here.`;
      return;
    }
    const viaGl = !gpuOk();  // WebGPU cannot, but WebGL2's experimental tone mapping can try
    for (const t of WHITE_STEPS) {
      const { wrap, canvas } = squareEl(t === 1 ? "SDR white 1x" : `${t}x`);
      box.appendChild(wrap);
      if (viaGl) { if (!drawFlatWebGL(canvas, t)) wrap.remove(); } else drawFlat(canvas, t);
    }
    if (!viaGl && glFlag) {
      const { wrap, canvas } = squareEl("4x via WebGL2 (flag)");
      box.appendChild(wrap);
      if (!drawFlatWebGL(canvas, 4)) wrap.remove();
    }
    const lines = [];
    if (viaGl) lines.push(`Drawn with WebGL2's experimental tone mapping, because WebGPU could not (${whyNoHdr()}).`);
    if (!state.screen.hdr) lines.push("The screen is in SDR mode right now, so all of these will look the same.");
    else lines.push("With the settings read on 2026-10-24 (SDR white 480 nits, panel peak about 400) expect all of them to look the same.");
    note.textContent = lines.join(" ");
  }

  function renderLadder() {
    const box = $("#ladder"), note = $("#ladder-note"), savedEl = $("#ladder-saved");
    box.textContent = "";
    note.textContent = "";
    const saved = readSavedHeadroom();
    const showSaved = (rec) => {
      savedEl.textContent = "";
      if (!rec) { savedEl.textContent = "Nothing picked yet on this browser."; return; }
      savedEl.append("Saved for this screen: ");
      const b = document.createElement("b");
      b.textContent = `${fmt(rec.headroom, 2)}x white`;
      savedEl.append(b, ` (picked ${rec.at.slice(0, 10)} on ${rec.screen}).`);
    };
    showSaved(saved);
    if (!gpuOk()) {
      note.textContent = `Hidden: needs a brighter-than-white canvas (${whyNoHdr()}).`;
      return;
    }
    const buttons = [];
    for (const t of LADDER_STEPS) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.title = `Pick ${t}x as the last step that still gets brighter`;
      btn.setAttribute("aria-pressed", saved && saved.headroom === t ? "true" : "false");
      const { wrap, canvas } = squareEl(`${t}x`);
      btn.appendChild(wrap);
      btn.addEventListener("click", () => {
        const rec = writeSavedHeadroom(t);
        for (const other of buttons) other.setAttribute("aria-pressed", other === btn ? "true" : "false");
        if (rec) { showSaved(rec); buildFacts(); } else savedEl.textContent = "This browser would not let the page save it (private window?).";
      });
      buttons.push(btn);
      box.appendChild(btn);
      drawFlat(canvas, t);
    }
  }

  const BEAM_WGSL = /* wgsl */ `
struct U { size: vec2f, dpr: f32, gain: f32, linearOut: f32, p0: f32, p1: f32, p2: f32 }
@group(0) @binding(0) var<uniform> u: U;

@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  var p = array<vec2f, 3>(vec2f(-1.0, -3.0), vec2f(-1.0, 1.0), vec2f(3.0, 1.0));
  return vec4f(p[i], 0.0, 1.0);
}

fn enc(x: f32) -> f32 {
  let a = abs(x);
  let e = select(1.055 * pow(max(a, 1e-8), 1.0 / 2.4) - 0.055, 12.92 * a, a <= 0.0031308);
  return sign(x) * e;
}

// a thin beam: a gaussian core about 2 css px wide plus a faint halo, fading out at both ends
fn beam(p: vec2f, a: vec2f, b: vec2f, w: f32) -> f32 {
  let fromA = p - a;
  let span = b - a;
  let along = dot(fromA, span) / dot(span, span);   // where p projects onto the segment, 0 at a and 1 at b
  let h = min(max(along, 0.0), 1.0);
  let d = length(fromA - span * h);
  let core = exp(-0.5 * d * d / (w * w));
  let halo = 0.035 * exp(-d / (5.0 * w));
  let ends = smoothstep(0.0, 0.12, h) * (1.0 - smoothstep(0.88, 1.0, h));  // WGSL rejects low >= high
  return (core + halo) * ends;
}

@fragment fn fs(@builtin(position) fc: vec4f) -> @location(0) vec4f {
  let W = u.size.x;
  let H = u.size.y;
  let w = 0.8 * u.dpr;
  var cols = array<vec3f, 3>(vec3f(0.0, 1.0, 0.0), vec3f(1.0, 0.0, 0.0), vec3f(0.0, 0.0, 1.0));
  var c = vec3f(0.0);
  for (var i = 0u; i < 3u; i = i + 1u) {
    let x0 = W * (f32(i) + 0.06) / 3.0;
    let x1 = W * (f32(i) + 0.94) / 3.0;
    c = c + cols[i] * beam(fc.xy, vec2f(x0, H * 0.70), vec2f(x1, H * 0.30), w);
  }
  c = c * u.gain;
  if (u.linearOut < 0.5) { c = vec3f(enc(c.x), enc(c.y), enc(c.z)); }
  return vec4f(c, 1.0);
}`;

  let beamPipeline = null;
  function getBeamPipeline() {
    if (beamPipeline) return beamPipeline;
    const device = state.gpu.device;
    const module = device.createShaderModule({ code: BEAM_WGSL });
    beamPipeline = device.createRenderPipeline({
      layout: "auto",
      vertex: { module, entryPoint: "vs" },
      fragment: { module, entryPoint: "fs", targets: [{ format: "rgba16float" }] },
      primitive: { topology: "triangle-list" },
    });
    return beamPipeline;
  }

  function drawBeams(canvas, gain, extended) {
    const g = state.gpu, device = g.device;
    const { w, h, dpr } = sizeCanvas(canvas);
    const ctx = gpuContext(canvas, extended);
    const pipeline = getBeamPipeline();
    const ubuf = device.createBuffer({ size: 32, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(ubuf, 0, new Float32Array([w, h, dpr, gain, g.linear ? 1 : 0, 0, 0, 0]));
    const bind = device.createBindGroup({ layout: pipeline.getBindGroupLayout(0), entries: [{ binding: 0, resource: { buffer: ubuf } }] });
    const encoder = device.createCommandEncoder();
    const pass = encoder.beginRenderPass({ colorAttachments: [{ view: ctx.getCurrentTexture().createView(),
      loadOp: "clear", storeOp: "store", clearValue: { r: 0, g: 0, b: 0, a: 1 } }] });
    pass.setPipeline(pipeline);
    pass.setBindGroup(0, bind);
    pass.draw(3);
    pass.end();
    device.queue.submit([encoder.finish()]);
    ubuf.destroy();  // freed once the submitted work is done
  }

  function renderBeams() {
    const note = $("#beam-note"), sdr = $("#beam-sdr"), hdr = $("#beam-hdr");
    note.textContent = "";
    const g = state.gpu;
    if (!g || !g.device || state.deviceLost) {
      hdr.closest(".beam-row").hidden = true;
      sdr.closest(".beam-row").hidden = true;
      note.textContent = `Hidden: the beams need WebGPU (${g ? g.why || "device lost" : "not checked"}).`;
      return;
    }
    sdr.closest(".beam-row").hidden = false;
    drawBeams(sdr, 1, false);  // standard tone mapping: clipped at white, exactly what a normal page gets
    if (gpuOk()) {
      hdr.closest(".beam-row").hidden = false;
      drawBeams(hdr, BEAM_HDR_GAIN, true);
      if (!state.screen.hdr) note.textContent = "The screen is in SDR mode right now, so both rows will look the same.";
    } else {
      hdr.closest(".beam-row").hidden = true;
      note.textContent = `HDR beams hidden: no brighter-than-white canvas (${whyNoHdr()}).`;
    }
  }

  function whyNoHdr() {
    const g = state.gpu;
    if (!g) return "not checked";
    if (state.deviceLost) return "the WebGPU device was lost";
    if (!g.device) return g.why || "no WebGPU";
    if (g.extended === false) return g.configureError || "WebGPU refused toneMapping extended";
    return "unknown";
  }

  // -------------------------------------------------------------------------------------------- WebGL2 patches
  const FULLSCREEN_VS = `#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;
  const RAMP_FS = `#version 300 es
precision highp float;
uniform vec2 uSize;
uniform float uDpr;
out vec4 o;
float enc(float x) { return x <= 0.0031308 ? 12.92 * x : 1.055 * pow(x, 1.0 / 2.4) - 0.055; }
void main() {
  vec2 p = vec2(gl_FragCoord.x, uSize.y - gl_FragCoord.y);
  float t = clamp((p.x - 0.5) / max(uSize.x - 1.0, 1.0), 0.0, 1.0);
  float band = uSize.y / 3.0;
  float row = floor(p.y / band);
  float inRow = p.y - row * band;
  float gap = 5.0 * uDpr;
  vec3 c = vec3(0.0);
  if (inRow > gap * 0.5 && inRow < band - gap * 0.5) {
    if (row < 0.5) c = vec3(enc(0.02 * t));                     // black to 2% grey (linear light)
    else if (row < 1.5) c = vec3(0.0, 0.0, enc(0.06 * t));      // black to a deep blue
    else c = vec3(t);                                           // black to white, evenly stepped in display values
  }
  o = vec4(c, 1.0);
}`;

  function compile(gl, vsSrc, fsSrc) {
    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || "shader compile failed");
      return s;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vsSrc));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fsSrc));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || "program link failed");
    return prog;
  }

  const glCache = new WeakMap();  // canvas -> { gl, prog }
  function rampContext(canvas) {
    let entry = glCache.get(canvas);
    if (entry && !entry.gl.isContextLost()) return entry;
    const gl = canvas.getContext("webgl2", { antialias: false, depth: false, stencil: false });  // alpha on: see drawingBufferStorage
    if (!gl) return null;
    entry = { gl, prog: compile(gl, FULLSCREEN_VS, RAMP_FS) };
    glCache.set(canvas, entry);
    return entry;
  }

  function drawRamp(canvas, float16) {
    const { w, h, dpr } = sizeCanvas(canvas);
    const entry = rampContext(canvas);
    if (!entry) return false;
    const { gl, prog } = entry;
    if (float16 && !useFloat16Buffer(gl, w, h)) return false;
    gl.viewport(0, 0, w, h);
    gl.useProgram(prog);
    gl.uniform2f(gl.getUniformLocation(prog, "uSize"), w, h);
    gl.uniform1f(gl.getUniformLocation(prog, "uDpr"), dpr);
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    return true;
  }

  function renderRamps() {
    const note = $("#ramp-note");
    note.textContent = "";
    if (!state.webgl.available) { note.textContent = "Hidden: WebGL2 is not available."; return; }
    drawRamp($("#ramp-8"), false);
    const c16 = $("#ramp-16");
    if (state.webgl.float16 && drawRamp(c16, true)) {
      c16.hidden = false;
      c16.previousElementSibling.hidden = false;
    } else {
      c16.hidden = true;
      c16.previousElementSibling.hidden = true;
      note.textContent = "No float16 drawing buffer in this browser, so only the 8-bit strips are shown.";
    }
  }

  function renderGlTiles() {
    const canvas = $("#gl-tiles"), note = $("#gl-tiles-note");
    note.textContent = "";
    if (!state.webgl.available) { note.textContent = "Hidden: WebGL2 is not available."; return; }
    const { w, h, dpr } = sizeCanvas(canvas);
    const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, depth: false, stencil: false });
    if (!gl) { note.textContent = "Hidden: the canvas refused a WebGL2 context."; return; }
    const p3 = !!state.webgl.p3;
    if (p3) gl.drawingBufferColorSpace = "display-p3";  // set before drawing: changing it clears the buffer
    gl.viewport(0, 0, w, h);
    gl.disable(gl.SCISSOR_TEST);
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.SCISSOR_TEST);
    const n = HUES.length;
    const slot = w / n;
    const outer = Math.floor(Math.min(slot - 10 * dpr, h - 8 * dpr, 64 * dpr));
    const inner = Math.floor(outer * 0.56);
    HUES.forEach(([, c], i) => {
      const cx = Math.round(slot * (i + 0.5)), cy = Math.round(h / 2);
      // outer: the most saturated sRGB colour, re-expressed in the buffer's P3 values
      const o = p3 ? srgbToP3Encoded(c) : c;
      gl.scissor(cx - (outer >> 1), cy - (outer >> 1), outer, outer);
      gl.clearColor(o[0], o[1], o[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      // inner: the most saturated P3 colour (same as the outer one when the buffer is sRGB)
      gl.scissor(cx - (inner >> 1), cy - (inner >> 1), inner, inner);
      gl.clearColor(c[0], c[1], c[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
    });
    gl.disable(gl.SCISSOR_TEST);
    if (!p3) note.textContent = "This browser cannot give WebGL2 a P3 drawing buffer, so the inner squares match the outer ones.";
  }

  // ---------------------------------------------------------------------------------------------- CSS patches
  function renderCssTiles() {
    const box = $("#css-tiles"), note = $("#css-note");
    box.textContent = "";
    note.textContent = "";
    const css = state.css;
    for (const [name, c] of HUES) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.style.background = `rgb(${c.map((v) => v * 255).join(" ")})`;
      const p3 = document.createElement("div");
      p3.className = "p3";
      p3.style.background = css.p3 ? `color(display-p3 ${c.join(" ")})` : tile.style.background;
      const dot = document.createElement("div");
      dot.className = "r2020";
      dot.style.background = css.rec2020 ? `color(rec2020 ${c.join(" ")})` : p3.style.background;
      p3.appendChild(dot);
      tile.appendChild(p3);
      const wrap = document.createElement("div");
      wrap.className = "tile-wrap";
      const cap = document.createElement("div");
      cap.className = "caption";
      cap.textContent = name;
      wrap.append(tile, cap);
      box.appendChild(wrap);
    }
    if (!css.p3) note.textContent = "This browser cannot name P3 colours in CSS, so the tiles are flat.";
    else if (state.screen.gamut === "srgb") note.textContent = "The screen is reported as sRGB, so the inner squares will not stand out.";
  }

  function renderSteps() {
    const box = $("#steps");
    box.textContent = "";
    const cell = (cls, text) => { const d = document.createElement("div"); d.className = cls; if (text) d.textContent = text; box.appendChild(d); return d; };
    cell("rowtag", "");
    for (const l of SHADOW_STEPS) cell("coltag", `${fmt(l * 100, 1)}%`);
    const rows = [["exact sRGB curve", (l) => enc1(l)], ["gamma 2.2 (the rig today)", (l) => Math.pow(l, 1 / 2.2)]];
    report.facts.nearBlackCodes = {};
    for (const [label, f] of rows) {
      cell("rowtag", label);
      const codes = [];
      for (const l of SHADOW_STEPS) {
        const code = Math.round(f(l) * 255);
        codes.push(code);
        const chip = cell("chip", "");
        chip.style.background = `rgb(${code} ${code} ${code})`;
        chip.title = `${fmt(l * 100, 1)}% of white, code ${code}/255`;
      }
      report.facts.nearBlackCodes[label] = codes;
    }
  }

  // --------------------------------------------------------------------------------------------------- driving
  function safely(name, fn) { try { fn(); } catch (e) { noteError(name, e); } }

  function renderPatches() {
    safely("brighter than white", renderWhiteSquares);
    safely("headroom ladder", renderLadder);
    safely("beams", renderBeams);
    safely("css tiles", renderCssTiles);
    safely("webgl tiles", renderGlTiles);
    safely("ramps", renderRamps);
    safely("near-black steps", renderSteps);
  }

  function refresh() {
    state.screen = detectScreen();
    safely("facts", buildFacts);
    safely("verdict", renderVerdict);
    renderPatches();
  }

  async function copyReport() {
    const status = $("#copy-status");
    const lines = [`HDR check ${report.at} (${location.href})`];
    for (const v of report.verdict || []) lines.push(`* ${v}`);
    for (const r of report.rows || []) lines.push(`${r.label}: ${r.value}`);
    if (report.errors.length) lines.push(`errors: ${report.errors.join(" | ")}`);
    const text = lines.join("\n");
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = "Copied. Paste it into the chat.";
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.rows = Math.min(24, lines.length + 1);
      ta.style.cssText = "width:100%;background:#0c0f15;color:#d3d8e0;border:1px solid #2c3342;border-radius:8px;font:12px ui-monospace,monospace;margin-top:8px";
      status.textContent = "Could not copy automatically; select the text below.";
      status.after(ta);
      ta.select();
    }
  }

  async function main() {
    state.screen = detectScreen();
    state.browser = await detectBrowser();
    state.webgl = detectWebGL2();
    state.canvas2d = detectCanvas2D();
    state.css = detectCss();
    try { state.gpu = await initWebGPU(); } catch (e) { state.gpu = { device: null, why: e.message }; noteError("webgpu", e); }
    refresh();

    $("#copy").addEventListener("click", copyReport);
    // the window moved to another screen, or Windows HDR was switched: check again
    for (const q of ["(dynamic-range: high)", "(color-gamut: p3)", "(color-gamut: rec2020)"]) {
      matchMedia(q).addEventListener("change", refresh);
    }
    let resizeTimer = 0;
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderPatches, 200); });
    document.documentElement.dataset.ready = "1";
    return report;
  }

  window.hdrCheck.ready = main().catch((e) => { noteError("main", e); document.documentElement.dataset.ready = "error"; return report; });
})();
