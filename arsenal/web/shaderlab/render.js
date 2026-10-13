// arsenal/web/shaderlab/render.js -- the still-maker: one shader in, deterministic PNG frames out, and never a hang.
//
// WHY THIS EXISTS. A text-only seat cannot look at a shader; it can read a PNG and a receipt. The headless driver
// (arsenal/shaders/headless.mjs) loads this page in Chrome forced onto SwiftShader, waits for window.__render.done,
// and writes what it finds. So everything a reader needs is in window.__render, and the page always finishes:
//
//   render.html?src=<url of shader.json or a .frag>&t=0,1.5,4&w=480&h=270&fps=60&media=<prefix for /media/a/ files>
//     fps: the fixed step of a walk and the iFrame numbering of a still, default 60 (Shadertoy runs at about 60, and
//          shaders that count iFrame or integrate iTimeDelta were tuned at that rate)
//     optional: &budget=<ms> (the watchdog, default 120000), &cube=<face size> (default 1024), &hw=0|1 (HW_PERFORMANCE),
//               &parity=0|1 (the GPU-parity shims of toy-runtime.js, default 1; 0 shows SwiftShader's own answers)
//
//   window.__render = {done, ok, renderer, compile: {...}, frames: [{t, png, ms, frames, frame, reset, jumped}],
//                      warmMs, history, substituted: [], unsupported: [], errors: [], stage, params, stats}
//
// THE RULES IT KEEPS
//   * CPU only. It reads the renderer string (WEBGL_debug_renderer_info) before compiling anything and REFUSES to draw
//     unless it names SwiftShader and no hardware (judgeRenderer, the headless driver's own rule). This host has an
//     AMD display-driver crash history; a page that would happily render on the real GPU when someone opens it in an
//     ordinary browser is how that history repeats.
//   * Reproducible stills. A feedback shader (toy.history: some buffer reads an earlier frame) reaches each t with
//     toy.advance from a reset, at a fixed dt of 1 / fps, so it gives the same pixels for the same t. Times are
//     rendered in ascending order and the walk continues from the previous t only when that t sat on the frame grid --
//     then the frames are exactly a fresh run's; otherwise it resets first. A shader without history draws only the
//     frame that walk would end on (toy.jump: same iFrame, iTime, iTimeDelta and iFrameRate), so a slow raymarcher's
//     t=4 costs one frame, not 241. iDate is pinned (DATE_BASE + t) so a clock shader is reproducible too.
//   * An honest cost. warmMs is one more frame, drawn after the stills are saved and timed to completion: the first
//     draw of a program on SwiftShader includes its compile, so a still's ms overstates the per-frame cost.
//   * Never a hang. A watchdog timer marks the page done with an error when the budget is spent, and the frame walk
//     yields to the event loop every YIELD_EVERY_MS so that timer can fire. One draw call that never returns blocks
//     the page itself; that case is the driver's deadline to handle (it kills the Chrome it started).
//
// Our own code; nothing here comes from the corpus or from shadertoy.com.

import {
  createToy, CONTEXT_ATTRIBUTES, rendererInfo, onFrameGrid, normalizeShader, shaderFromGlsl, DEFAULT_FPS,
  API as RUNTIME_API,
} from './toy-runtime.js';

export const RENDER_API = 'arsenal.shaderlab-render/v1';
export const DEFAULTS = Object.freeze({ times: [0], w: 480, h: 270, fps: DEFAULT_FPS, budgetMs: 120000, cube: 1024, hw: 1, parity: 1 });
export const LIMITS = Object.freeze({ maxSide: 4096, maxFps: 240, maxTimes: 64, maxT: 3600, minBudgetMs: 1000,
  maxBudgetMs: 600000, maxCube: 2048 });
// iDate for every still: 2026-01-01 at noon, plus the frame's iTime.
export const DATE_BASE = Object.freeze([2026, 0, 1, 12 * 3600]);
const YIELD_EVERY_MS = 50;
const WARM_MARGIN_MS = 1000;   // the warm timing frame runs only with this much budget left beyond twice a frame's cost
const FETCH_TIMEOUT_MS = 20000;
const MEDIA_TIMEOUT_MS = 15000;
const MEDIA_SITE_PREFIX = '/media/a/';
const HOUSE_MEDIA_PREFIX = '/corpus/media/';   // where `py -m arsenal shader serve` serves the corpus media

function intIn(raw, def, lo, hi) {
  if (raw === null || raw === undefined || raw === '') return def;
  const n = Number(raw);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, Math.round(n))) : NaN;
}

/**
 * The query, checked. {src, times, w, h, fps, media, budgetMs, cube, hw, parity, errors}. A bad value is an error the
 * receipt names, never a silent default. media: the param, else /corpus/media/ when served by the house lab server
 * (a path under /lab/), else null (every texture becomes a listed stand-in).
 */
export function parseParams(search, pathname = '') {
  const q = new URLSearchParams(search || '');
  const errors = [];
  const src = q.get('src') || '';
  if (!src) errors.push('missing ?src= (the url of a shader.json or a .frag)');
  const tRaw = q.get('t');
  let times = DEFAULTS.times.slice();
  if (tRaw !== null && tRaw !== '') {
    times = tRaw.split(',').map((s) => s.trim()).filter(Boolean).map(Number);
    const bad = times.filter((t) => !Number.isFinite(t) || t < 0 || t > LIMITS.maxT);
    if (bad.length || !times.length) errors.push(`bad t list "${tRaw}" (non-negative seconds up to ${LIMITS.maxT}, comma separated)`);
    if (times.length > LIMITS.maxTimes) errors.push(`too many times (${times.length}; at most ${LIMITS.maxTimes})`);
  }
  const w = intIn(q.get('w'), DEFAULTS.w, 1, LIMITS.maxSide);
  const h = intIn(q.get('h'), DEFAULTS.h, 1, LIMITS.maxSide);
  const fps = intIn(q.get('fps'), DEFAULTS.fps, 1, LIMITS.maxFps);
  const budgetMs = intIn(q.get('budget'), DEFAULTS.budgetMs, LIMITS.minBudgetMs, LIMITS.maxBudgetMs);
  const cube = intIn(q.get('cube'), DEFAULTS.cube, 1, LIMITS.maxCube);
  const hw = intIn(q.get('hw'), DEFAULTS.hw, 0, 1);
  const parity = intIn(q.get('parity'), DEFAULTS.parity, 0, 1);
  for (const [k, v] of Object.entries({ w, h, fps, budget: budgetMs, cube, hw, parity })) {
    if (Number.isNaN(v)) errors.push(`bad ${k}=${q.get(k)}`);
  }
  let media = q.get('media');
  if (media === null) media = String(pathname || '').startsWith('/lab/') ? HOUSE_MEDIA_PREFIX : null;
  if (media === '') media = null;
  return { src, times, w, h, fps, media, budgetMs, cube, hw, parity, errors };
}

/** mediaUrl for the runtime: a site path /media/a/<file> becomes <prefix><file>; anything else has no url. */
export function mediaResolver(prefix) {
  if (!prefix) return () => null;
  const p = prefix.endsWith('/') ? prefix : `${prefix}/`;
  return (src) => {
    const s = String(src || '');
    return s.startsWith(MEDIA_SITE_PREFIX) && s.length > MEDIA_SITE_PREFIX.length ? p + s.slice(MEDIA_SITE_PREFIX.length) : null;
  };
}

/** The shader behind a fetched body: JSON (saved shader, API envelope, or list), else a bare .frag/.glsl source. */
export function shaderFromBody(text, src) {
  const name = String(src || '').split(/[?#]/)[0].split('/').pop() || 'sketch';
  if (/\.(frag|glsl|fs)$/i.test(name)) return shaderFromGlsl(text, { name });
  let json;
  try { json = JSON.parse(text); } catch (e) {
    if (/\bmainImage\s*\(/.test(text)) return shaderFromGlsl(text, { name });
    throw new Error(`${name} is neither JSON nor GLSL with a mainImage`);
  }
  return normalizeShader(json);
}

function compileSummary(c) {
  return {
    ok: c.ok, drawable: c.drawable, warnings: c.warnings,
    passes: c.passes.map((p) => ({ name: p.name, type: p.type, key: p.key, ok: p.ok, lines: p.lines, parity: p.parity,
      firstError: p.firstError, mappedLog: p.mappedLog })),
  };
}

const yieldToBrowser = () => new Promise((resolve) => setTimeout(resolve, 0));

async function fetchText(url, timeoutMs) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctl.signal, cache: 'no-store' });
    if (!res.ok) throw new Error(`fetching ${url}: HTTP ${res.status}`);
    return await res.text();
  } catch (e) {
    throw new Error(e && e.name === 'AbortError' ? `fetching ${url}: timed out after ${timeoutMs} ms` : (e && e.message) || String(e));
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  const t0 = performance.now();
  const R = Object.assign(window.__render || {}, {
    api: RENDER_API, runtime: RUNTIME_API, done: false, ok: false, stage: 'start', renderer: null, compile: null,
    frames: [], substituted: [], unsupported: [], errors: [], params: null, stats: null, ms: 0,
  });
  window.__render = R;
  const statusEl = document.getElementById('status');
  const say = (text) => { if (statusEl) statusEl.textContent = text; };
  let finished = false;
  let watchdog = null;
  const finish = (fields) => {
    if (finished) return;
    finished = true;
    clearTimeout(watchdog);
    Object.assign(R, fields, { done: true, ms: Math.round(performance.now() - t0) });
    say(`${R.ok ? 'done' : 'failed'} in ${R.ms} ms${R.errors.length ? `\n${R.errors.join('\n')}` : ''}`);
  };
  addEventListener('error', (e) => { if (!finished) R.errors.push(`page error: ${e.message || 'unknown'}`); });
  addEventListener('unhandledrejection', (e) => {
    if (!finished) R.errors.push(`unhandled rejection: ${(e.reason && e.reason.message) || e.reason}`);
  });

  const p = parseParams(location.search, location.pathname);
  R.params = p;
  if (p.errors.length) { R.errors.push(...p.errors); finish({ ok: false }); return; }
  const deadline = t0 + p.budgetMs;
  const left = () => deadline - performance.now();
  watchdog = setTimeout(() => {
    R.errors.push(`watchdog: the ${p.budgetMs} ms budget was spent at stage "${R.stage}"`);
    finish({ ok: false, timedOut: true });
  }, p.budgetMs);

  let toy = null;
  try {
    // 1. The gate: a CPU rasteriser or nothing.
    R.stage = 'gate';
    say('checking the renderer');
    const canvas = document.createElement('canvas');
    canvas.width = p.w;
    canvas.height = p.h;
    document.body.appendChild(canvas);
    const gl = canvas.getContext('webgl2', CONTEXT_ATTRIBUTES);
    if (!gl) throw new Error('WebGL2 is not available in this browser');
    const info = rendererInfo(gl);
    R.renderer = info.renderer;
    if (!info.swiftshader) {
      R.errors.push(`refused: ${info.judged.reason}. This page renders on SwiftShader (the CPU) only, and only when `
        + 'the renderer names no hardware (GPU safety: this host has a display-driver crash history). '
        + 'Load it through the headless driver.');
      finish({ ok: false, refused: true });
      return;
    }

    // 2. The shader.
    R.stage = 'fetch';
    say(`fetching ${p.src}`);
    const srcUrl = new URL(p.src, location.href).href;
    const shader = shaderFromBody(await fetchText(srcUrl, Math.max(1, Math.min(FETCH_TIMEOUT_MS, left()))), p.src);
    if (finished) return;

    // 3. Compile.
    R.stage = 'compile';
    say('compiling');
    toy = createToy(canvas, shader, {
      mediaUrl: (() => { const r = mediaResolver(p.media); return (s) => { const u = r(s); return u ? new URL(u, location.href).href : null; }; })(),
      pixelRatio: 1, cubeSize: p.cube, hwPerformance: p.hw, parity: p.parity === 1, fps: p.fps, dateBase: DATE_BASE,
      mediaTimeoutMs: Math.max(1, Math.min(MEDIA_TIMEOUT_MS, Math.floor(p.budgetMs / 3))),
    });
    const compiled = toy.compile();
    R.compile = compileSummary(compiled);
    if (!compiled.drawable) {
      const failed = compiled.passes.filter((x) => !x.ok && x.key !== 'sound');
      R.errors.push(...(failed.length ? failed.map((x) => `compile: ${x.name}: ${x.firstError}`) : compiled.warnings.map((w) => `compile: ${w}`)));
      const st = toy.stats();
      finish({ ok: false, substituted: st.substituted, unsupported: st.unsupported, stats: st });
      return;
    }
    if (finished) return;

    // 4. Media (each file has its own timeout; a missing one becomes a listed stand-in).
    R.stage = 'media';
    say('loading media');
    await toy.ready;
    if (finished) return;

    // 5. The frames. A shader without history (no buffer reads an earlier frame) draws each still as one frame, the
    // exact frame the walk would end on (toy.jump); a feedback shader walks from a reset.
    R.stage = 'render';
    R.history = toy.history;
    const ascending = [...new Set(p.times)].sort((a, b) => a - b);
    const byT = new Map();
    let needReset = true;
    for (const t of ascending) {
      const started = performance.now();
      if (!toy.history) {
        const j = toy.jump(t, { fps: p.fps });
        const png = canvas.toDataURL('image/png');
        byT.set(t, { t, png, ms: Math.round(performance.now() - started), frames: 1, frame: j.frame, reset: false, jumped: true });
        if (left() <= 0 && t !== ascending[ascending.length - 1]) throw new Error(`watchdog: the budget ran out after t=${t}`);
        await yieldToBrowser();
        if (finished) return;
        continue;
      }
      const didReset = needReset;
      if (needReset) toy.reset();
      let frames = 0;
      for (;;) {
        const sliceStart = performance.now();
        let r;
        do {
          r = toy.advance(t, { fps: p.fps, maxFrames: 1 });
          frames += r.frames;
        } while (!r.reached && performance.now() - sliceStart < YIELD_EVERY_MS);
        if (r.reached) break;
        if (r.behind) throw new Error(`internal: the walk passed t=${t}`);
        R.progress = { t, frame: r.frame, time: r.time };
        say(`t=${t}: frame ${r.frame} (time ${r.time.toFixed(3)})`);
        if (left() <= 0) throw new Error(`watchdog: the budget ran out walking to t=${t} (frame ${r.frame})`);
        await yieldToBrowser();
        if (finished) return;
      }
      const png = canvas.toDataURL('image/png');
      const st = toy.stats();
      byT.set(t, { t, png, ms: Math.round(performance.now() - started), frames, frame: st.frame - 1, reset: didReset });
      needReset = !onFrameGrid(t, p.fps);
      if (left() <= 0 && t !== ascending[ascending.length - 1]) {
        throw new Error(`watchdog: the budget ran out after t=${t}`);
      }
      await yieldToBrowser();
      if (finished) return;
    }
    // 6. One warm frame, timed. SwiftShader compiles a program at its first draw, so a still's ms (above all the first
    // one's) is mostly compile time; this frame, drawn after every still is saved, is the per-frame cost a reader can
    // compare across shaders. A 1x1 readPixels makes the timer wait for the draw to finish.
    let warmMs = null;
    const slowest = Math.max(0, ...[...byT.values()].map((f) => f.ms / Math.max(1, f.frames)));
    if (left() > 2 * slowest + WARM_MARGIN_MS) {
      const w0 = performance.now();
      toy.render({});
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4));
      warmMs = Math.round((performance.now() - w0) * 10) / 10;
    }
    const st = toy.stats();
    if (st.glErrors.length) R.errors.push(...st.glErrors.map((e) => `GL error ${e.error} at ${e.where} (frame ${e.frame})`));
    finish({
      ok: true, stage: 'done', frames: p.times.map((t) => byT.get(t)), warmMs,
      substituted: st.substituted, unsupported: st.unsupported, stats: st,
    });
  } catch (e) {
    R.errors.push(String((e && e.message) || e));
    let st = null;
    try { st = toy ? toy.stats() : null; } catch (_) { /* the context may be gone */ }
    finish({ ok: false, substituted: st ? st.substituted : R.substituted, unsupported: st ? st.unsupported : R.unsupported, stats: st });
  }
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') main();
