/** Pure decisions for the shader renderer, kept free of the DOM so they can be tested. */

export interface Quality {
  /** Highest device pixel ratio worth rendering. */
  readonly dpr: number;
  /** Multiplies each preset's render scale. */
  readonly scale: number;
  /** Highest frame rate any preset runs at. */
  readonly fps: number;
}

/** Phones and small screens get fewer pixels and frames; the field is soft enough not to show it. */
export const qualityFor = ({
  coarse,
  width,
}: {
  coarse: boolean;
  width: number;
}): Quality =>
  coarse || width < 768
    ? { dpr: 1.5, scale: 0.75, fps: 30 }
    : { dpr: 1.5, scale: 1, fps: 60 };

/** The renderer judges the device over windows this long, so a slow device is judged as fast as a quick one. */
export const PROBE_MS = 1500;
/** A frame gap above this is slow: 60 fps leaves 16.7ms. */
export const SLOW_FRAME_MS = 22;
/** Below this render scale a field stops moving: one still frame, as under reduced motion. */
const MIN_SCALE = 0.3;

/**
 * Cut the work if more than half of a window's frames were slow: fewer pixels and 30 fps, and once
 * that is not enough either, a still frame (fps 0). Returns the same object when no cut is needed.
 */
export const degrade = (
  quality: Quality,
  frames: number,
  slowFrames: number,
): Quality => {
  if (slowFrames <= frames / 2) return quality;
  if (quality.scale * 0.6 < MIN_SCALE) return { ...quality, fps: 0 };
  return {
    ...quality,
    scale: quality.scale * 0.6,
    fps: Math.min(quality.fps, 30),
  };
};

export interface Slot {
  /** On screen, or close enough to be about to be. */
  readonly visible: boolean;
  /** A frame was drawn since the last resize or context restore. */
  readonly drawn: boolean;
  /** When the last frame was drawn, in rAF milliseconds. */
  readonly last: number;
  /** The preset's own frame rate. */
  readonly fps: number;
}

export interface Conditions {
  readonly reduced: boolean;
  readonly hidden: boolean;
  readonly quality: Quality;
}

/**
 * Whether a background draws this frame. Nothing draws in a hidden tab or off screen. Under reduced
 * motion, or on a device too slow to animate, a background draws exactly once, a still frame, and
 * again only after a resize.
 */
export const isDue = (slot: Slot, now: number, conditions: Conditions) => {
  if (conditions.hidden || !slot.visible) return false;
  if (!slot.drawn) return true;
  if (conditions.reduced || conditions.quality.fps === 0) return false;
  const fps = Math.min(slot.fps, conditions.quality.fps);
  // A little slack so a 30 fps field does not skip to 20 on a jittery 60 Hz clock.
  return now - slot.last >= 1000 / fps - 4;
};

/** Whether the loop must keep running: something visible still has frames to draw. */
export const needsLoop = (slots: Iterable<Slot>, conditions: Conditions) => {
  if (conditions.hidden) return false;
  for (const slot of slots) {
    const still = conditions.reduced || conditions.quality.fps === 0;
    if (slot.visible && (!still || !slot.drawn)) return true;
  }
  return false;
};

/**
 * Render size of a background in device pixels, for a DPR already capped by the quality, and
 * shrunk to fit what one GL drawing buffer may hold.
 */
export const renderSize = (
  width: number,
  height: number,
  dpr: number,
  scale: number,
  max = 2048,
) => {
  const factor = dpr * scale;
  const fit = Math.min(1, max / Math.max(width * factor, height * factor, 1));
  return {
    width: Math.max(1, Math.round(width * factor * fit)),
    height: Math.max(1, Math.round(height * factor * fit)),
  };
};
