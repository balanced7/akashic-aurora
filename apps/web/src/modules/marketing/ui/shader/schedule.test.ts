import { describe, expect, it } from "vitest";

import { shaderPresets } from "./presets";
import {
  degrade,
  isDue,
  needsLoop,
  PROBE_FRAMES,
  qualityFor,
  renderSize,
} from "./schedule";

import type { Conditions, Slot } from "./schedule";

const desktop = qualityFor({ coarse: false, width: 1440 });
const running: Conditions = { reduced: false, hidden: false, quality: desktop };
const slot = (overrides: Partial<Slot> = {}): Slot => ({
  visible: true,
  drawn: true,
  last: 0,
  fps: 30,
  ...overrides,
});

describe("qualityFor", () => {
  it("gives phones fewer pixels and frames", () => {
    expect(qualityFor({ coarse: true, width: 1200 })).toEqual({
      dpr: 1.5,
      scale: 0.75,
      fps: 30,
    });
    expect(qualityFor({ coarse: false, width: 390 }).fps).toBe(30);
    expect(desktop).toEqual({ dpr: 1.5, scale: 1, fps: 60 });
  });
});

describe("degrade", () => {
  it("halves the work once most probed frames were slow", () => {
    expect(degrade(desktop, PROBE_FRAMES / 2)).toBe(desktop);
    const slow = degrade(desktop, PROBE_FRAMES / 2 + 1);
    expect(slow.scale).toBeCloseTo(0.6);
    expect(slow.fps).toBe(30);
  });
});

describe("isDue", () => {
  it("draws nothing off screen or in a hidden tab", () => {
    expect(isDue(slot({ visible: false, drawn: false }), 1000, running)).toBe(
      false,
    );
    expect(
      isDue(slot({ drawn: false }), 1000, { ...running, hidden: true }),
    ).toBe(false);
  });

  it("draws one still frame under reduced motion, and again after a resize", () => {
    const reduced = { ...running, reduced: true };
    expect(isDue(slot({ drawn: false }), 1000, reduced)).toBe(true);
    expect(isDue(slot({ drawn: true, last: 0 }), 99_999, reduced)).toBe(false);
  });

  it("holds each preset to its own frame rate, capped by the device", () => {
    expect(isDue(slot({ fps: 30, last: 1000 }), 1016, running)).toBe(false);
    expect(isDue(slot({ fps: 30, last: 1000 }), 1033, running)).toBe(true);
    expect(isDue(slot({ fps: 60, last: 1000 }), 1016, running)).toBe(true);
    const phone = {
      ...running,
      quality: qualityFor({ coarse: true, width: 390 }),
    };
    expect(isDue(slot({ fps: 60, last: 1000 }), 1016, phone)).toBe(false);
  });
});

describe("needsLoop", () => {
  it("stops when nothing visible needs a frame", () => {
    expect(needsLoop([slot({ visible: false })], running)).toBe(false);
    expect(needsLoop([slot()], running)).toBe(true);
    expect(needsLoop([slot()], { ...running, hidden: true })).toBe(false);
    expect(needsLoop([slot()], { ...running, reduced: true })).toBe(false);
    expect(
      needsLoop([slot({ drawn: false })], { ...running, reduced: true }),
    ).toBe(true);
  });
});

describe("renderSize", () => {
  it("scales CSS pixels by DPR and preset scale", () => {
    expect(renderSize(1440, 800, 1.5, 0.5)).toEqual({
      width: 1080,
      height: 600,
    });
  });

  it("shrinks to fit one drawing buffer, keeping the aspect", () => {
    const size = renderSize(1440, 6000, 1.5, 0.6);
    expect(size.height).toBe(2048);
    expect(size.width).toBe(Math.round((2048 * 1440) / 6000));
  });

  it("never returns an empty canvas", () => {
    expect(renderSize(0, 0, 1, 0.5)).toEqual({ width: 1, height: 1 });
  });
});

describe("shaderPresets", () => {
  it.each(Object.entries(shaderPresets))(
    "%s is a complete program with a fallback",
    (_, preset) => {
      expect(preset.fragment).toContain("precision highp float;");
      expect(preset.fragment).toMatch(/void main\(\)/);
      // Every preset ends on the static dither, so dark ramps do not band.
      expect(preset.fragment).toContain("finish(");
      expect(preset.fallback).toBeTruthy();
      expect([30, 60]).toContain(preset.fps);
      expect(preset.scale).toBeGreaterThan(0);
      expect(preset.scale).toBeLessThanOrEqual(1);
    },
  );
});
