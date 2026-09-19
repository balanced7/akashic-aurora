// arsenal/web/lib/raster-policy.js -- RESOLUTION POLICY: what size a render canvas should be.
//
// WHY THIS EXISTS. A render canvas serves two consumers with opposite requirements, and conflating
// them is the bug this module was born from:
//
//   the DISPLAY wants a raster sized to the viewing window (more pixels when the box is bigger,
//   and never more than the screen can show -- anything beyond that is paid for and thrown away);
//   the RECORDER wants a fixed capture tier, because a recording has to be a specified size.
//
// /piano served both from one number. The host sized its canvas from the capture tier
// (piano.js: renderer.setSize(framing.w * renderScale, framing.h * renderScale), framing 1080x1920
// and renderScale 4/3 for Ultra = 1440x2560) and then let CSS scale that into whatever box the
// layout gave it. Measured 2026-09-18 with arsenal/lanes/alias_verify.mjs: the backing store stayed
// 1440x2560 at every window size and devicePixelRatio -- 7.73x more pixels than the 518x921 box it
// was displayed in at 1920x1080, and unchanged at dpr 2 -- so the live view paid full price for
// resolution nobody could see, the browser resampled a 3.7 Mpx layer at a non-integer ratio every
// frame, and on a larger display the raster could not rise to meet it. The page's own 2D canvas
// already did this correctly (fill ratio 1.0 at both devicePixelRatios), so the rule was known and
// simply not applied to the 3D path.
//
// WHAT IT IS NOT: not a renderer, not a resize observer, and not a frame loop. It is the POLICY --
// a pure decision plus a small amount of stateful bookkeeping -- so it can be pinned in Node with no
// page at all, and adopted by any project that renders into a canvas.
//
// THE RULES, each one learned from something:
//   * the raster follows the DISPLAY, and the capture tier is a separate concern;
//   * a budget clamp NAMES itself, keeps the aspect, and never hides;
//   * a legibility floor beats an impossible budget, and the conflict is reported -- silently
//     rendering a smear to hit a pixel target would trade the wrong thing;
//   * a resolution change must be visible to justify itself (a buffer reallocation per resize event
//     is the classic thrash), so small changes do not commit;
//   * adaptive resolution is OFF unless asked for, steps down faster than it steps up, and NEVER
//     overscales past what the display can show -- over-rendering is the exact bug above;
//   * nothing here touches the page's own globals, so it runs headless and in any future page.

/** Supported logical frames, by aspect id. The frame is DESIGN SPACE, not a raster size. */
export const ASPECTS = { "9:16": 9 / 16, "16:9": 16 / 9, "1:1": 1 };

/** Interactive pixel budget. ~4.0 Mpx is a little above 1440p: past it, cost rises faster than
 *  anything an eye gains on a moving picture. Capture mode is expected to raise or lift it. */
export const DEFAULT_MAX_PIXELS = 4_000_000;

/** Never render below half the display's requirement: an unreadable frame is not a trade, it is a
 *  bug that reports itself as a performance win. */
export const DEFAULT_MIN_SCALE = 0.5;

/** A change smaller than this fraction of the pixel count is not worth a buffer reallocation. */
export const DEFAULT_HYSTERESIS = 0.10;

const isPos = (n) => Number.isFinite(n) && n > 0;

function requireBox(cssW, cssH) {
  if (!isPos(cssW) || !isPos(cssH)) {
    throw new Error(
      `a raster needs a real box, got ${cssW}x${cssH}. A zero box is a caller bug -- quietly ` +
      `rendering one pixel here would read as a black canvas three screens later.`);
  }
}

/** The logical frame: a design grid with an aspect, e.g. 9:16 at 1920 tall is 1080x1920.
 *  An unknown id is REFUSED rather than defaulted, because a typo that silently becomes 16:9 is a
 *  layout bug nobody can see. */
export function logicalFrame(aspectId, baseHeight) {
  const aspect = ASPECTS[aspectId];
  if (aspect === undefined) {
    throw new Error(`unknown aspect id ${JSON.stringify(aspectId)} (known: ${Object.keys(ASPECTS).join(", ")})`);
  }
  if (!isPos(baseHeight)) throw new Error(`baseHeight must be a positive number, got ${baseHeight}`);
  const h = Math.round(baseHeight);
  return { id: aspectId, aspect, w: Math.round(baseHeight * aspect), h };
}

/** Where the logical frame sits inside the box the layout gave us: contain-fit, centred, never
 *  overflowing. Returns CSS-pixel geometry; the raster decision is separate. */
export function containRect(frame, boxW, boxH) {
  requireBox(boxW, boxH);
  requireBox(frame && frame.w, frame && frame.h);
  const scale = Math.min(boxW / frame.w, boxH / frame.h);
  const w = frame.w * scale, h = frame.h * scale;
  return { x: (boxW - w) / 2, y: (boxH - h) / 2, w, h, scale };
}

/**
 * The raster decision for one display box.
 *
 * cssW/cssH  the space the canvas actually occupies, in CSS pixels
 * dpr        the display's devicePixelRatio (1 device pixel per CSS pixel at 1)
 * qualityScale  a deliberate supersample factor for anti-aliasing (1 = exact, 1.25 = mild SSAA)
 * maxPixels  the interactive budget; null/Infinity lifts it (capture mode)
 * minScale   the legibility floor, relative to the display requirement
 *
 * Returns { w, h, pixels, scale, clampedBy, reason } -- `clampedBy` and `reason` exist so a
 * downgrade can never be silent. A resolution nobody can explain is an absence rendering as normal.
 */
export function rasterFor({ cssW, cssH, dpr = 1, qualityScale = 1,
                           maxPixels = DEFAULT_MAX_PIXELS, minScale = DEFAULT_MIN_SCALE } = {}) {
  requireBox(cssW, cssH);
  if (!isPos(dpr)) throw new Error(`dpr must be a positive number, got ${dpr}`);
  if (!isPos(qualityScale)) throw new Error(`qualityScale must be a positive number, got ${qualityScale}`);

  const wantW = cssW * dpr * qualityScale;
  const wantH = cssH * dpr * qualityScale;
  let w = Math.round(wantW), h = Math.round(wantH);
  let scale = 1, clampedBy = null, reason = "sized to the viewing box at devicePixelRatio";

  const budget = Number.isFinite(maxPixels) && maxPixels > 0 ? maxPixels : Infinity;
  const over = (w * h) / budget;
  if (over > 1) {
    const shrink = Math.sqrt(1 / over);
    if (shrink < minScale) {
      // The legibility floor wins, and says so. The number is what gives, not the picture.
      w = Math.max(1, Math.round(wantW * minScale));
      h = Math.max(1, Math.round(wantH * minScale));
      scale = minScale;
      clampedBy = "minScale";
      reason = `a ${budget}px budget would need scale ${shrink.toFixed(3)}, below the legibility ` +
               `floor ${minScale}; the floor wins and the budget is exceeded at ${w * h}px`;
    } else {
      w = Math.max(1, Math.floor(wantW * shrink));
      h = Math.max(1, Math.floor(wantH * shrink));
      scale = shrink;
      clampedBy = "maxPixels";
      reason = `capped at the ${budget}px budget (scale ${shrink.toFixed(3)})`;
    }
  }
  return { w, h, pixels: w * h, scale, clampedBy, reason, cssW, cssH, dpr, qualityScale };
}

/** Is the pixel count different enough to justify reallocating buffers? Resize events arrive in
 *  storms; committing to each one is how a smooth page becomes a stuttery one. */
export function pixelsChanged(a, b, threshold = DEFAULT_HYSTERESIS) {
  if (!a || !b) return true;
  const pa = a.w * a.h, pb = b.w * b.h;
  if (!(pa > 0) || !(pb > 0)) return true;
  return Math.max(pa, pb) / Math.min(pa, pb) - 1 >= threshold;
}

/**
 * A policy with memory: it decides, it remembers what it committed to, and it can trade resolution
 * for frame time when asked. The caller owns the resize observer and the frame loop -- this takes
 * numbers and returns decisions, which is what makes it pinnable without a page.
 *
 * adaptive: null (default, OFF) or { targetMs, downAfter, upAfter, step, minScale }
 *   targetMs  the frame-time budget the resolution is protecting (default 16.7 = 60 Hz)
 *   downAfter / upAfter  consecutive slow / fast frames before a step (asymmetric on purpose:
 *                        resolution drops fast and returns slowly, which is what a player feels)
 */
export function createRasterPolicy(opts = {}) {
  const {
    maxPixels = DEFAULT_MAX_PIXELS, minScale = DEFAULT_MIN_SCALE,
    qualityScale = 1, hysteresis = DEFAULT_HYSTERESIS, adaptive = null,
  } = opts;

  const ad = {
    enabled: !!adaptive,
    scale: 1,
    steps_down: 0,
    steps_up: 0,
    slow: 0,
    fast: 0,
    reason: adaptive ? "at full resolution" : "adaptive resolution is off",
  };
  const targetMs = adaptive && isPos(adaptive.targetMs) ? adaptive.targetMs : 16.7;
  const downAfter = adaptive && isPos(adaptive.downAfter) ? adaptive.downAfter : 20;
  const upAfter = adaptive && isPos(adaptive.upAfter) ? adaptive.upAfter : 60;
  const step = adaptive && adaptive.step > 0 && adaptive.step < 1 ? adaptive.step : 0.85;
  const floor = adaptive && isPos(adaptive.minScale) ? Math.max(adaptive.minScale, 0) : minScale;

  const state = { box: null, dpr: 1, raster: null, changes: 0 };

  const decide = ({ cssW, cssH, dpr }) => rasterFor({
    cssW, cssH, dpr, qualityScale: qualityScale * ad.scale, maxPixels, minScale,
  });

  function resize(box = {}) {
    requireBox(box.cssW, box.cssH);
    const dpr = isPos(box.dpr) ? box.dpr : 1;
    const next = decide({ cssW: box.cssW, cssH: box.cssH, dpr });
    const dprMoved = state.box !== null && dpr !== state.dpr;
    const commit = state.raster === null || dprMoved
      || pixelsChanged({ w: state.raster.w, h: state.raster.h }, next, hysteresis);
    state.box = { cssW: box.cssW, cssH: box.cssH };
    state.dpr = dpr;
    if (commit) {
      state.raster = next;
      state.changes++;
    }
    return Object.assign({}, state.raster, { committed: commit });
  }

  /** Feed one frame's duration. Returns the current adaptive scale. */
  function observeFrameTime(ms) {
    if (!ad.enabled || !isPos(ms)) return ad.scale;
    if (ms > targetMs * 1.35) {
      ad.fast = 0;
      ad.slow++;
      if (ad.slow >= downAfter && ad.scale > floor) {
        ad.scale = Math.max(floor, ad.scale * step);
        ad.steps_down++;
        ad.slow = 0;
        ad.reason = `${ms.toFixed(1)}ms over a ${targetMs}ms budget for ${downAfter} frames: ` +
                    `stepped resolution to ${(ad.scale * 100).toFixed(0)}%`;
      }
    } else if (ms < targetMs * 0.75) {
      ad.slow = 0;
      ad.fast++;
      if (ad.fast >= upAfter && ad.scale < 1) {
        // Back up by the inverse of the step, so the resolution can RETURN in the same number of
        // steps it took to lose. Clamped at 1: rendering past the display requirement is the bug.
        ad.scale = Math.min(1, ad.scale / step);
        ad.steps_up++;
        ad.fast = 0;
        ad.reason = `headroom for ${upAfter} frames: restored resolution to ${(ad.scale * 100).toFixed(0)}%`;
      }
    } else {
      ad.slow = 0;
      ad.fast = 0;
    }
    return ad.scale;
  }

  function report() {
    return {
      box: state.box, dpr: state.dpr, qualityScale, maxPixels, minScale,
      raster: state.raster, changes: state.changes,
      clampedBy: state.raster ? state.raster.clampedBy : null,
      reason: state.raster ? state.raster.reason : "nothing sized yet",
      adaptive: {
        enabled: ad.enabled, scale: ad.scale, steps_down: ad.steps_down, steps_up: ad.steps_up,
        targetMs, reason: ad.reason,
      },
    };
  }

  return { resize, observeFrameTime, report };
}
