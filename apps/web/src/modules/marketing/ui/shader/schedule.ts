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

/** After this many timed frames the renderer judges whether the device keeps up. */
export const PROBE_FRAMES = 90;
/** A frame gap above this is slow: 60 fps leaves 16.7ms. */
export const SLOW_FRAME_MS = 22;

/** Halve the work once if more than half the probed frames were slow. */
export const degrade = (quality: Quality, slowFrames: number): Quality =>
  slowFrames > PROBE_FRAMES / 2
    ? { ...quality, scale: quality.scale * 0.6, fps: Math.min(quality.fps, 30) }
    : quality;

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
 * motion a background draws exactly once, a still frame, and again only after a resize.
 */
export const isDue = (slot: Slot, now: number, conditions: Conditions) => {
  if (conditions.hidden || !slot.visible) return false;
  if (!slot.drawn) return true;
  if (conditions.reduced) return false;
  const fps = Math.min(slot.fps, conditions.quality.fps);
  // A little slack so a 30 fps field does not skip to 20 on a jittery 60 Hz clock.
  return now - slot.last >= 1000 / fps - 4;
};

/** Whether the loop must keep running: something visible still has frames to draw. */
export const needsLoop = (slots: Iterable<Slot>, conditions: Conditions) => {
  if (conditions.hidden) return false;
  for (const slot of slots) {
    if (slot.visible && (!conditions.reduced || !slot.drawn)) return true;
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
