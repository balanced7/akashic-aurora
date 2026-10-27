import { describe, expect, it } from "vitest";

import { minutesToRead, walkLabel } from "./meta";

describe("walkLabel", () => {
  it("pads the walk number to two digits", () => {
    expect(walkLabel(1)).toBe("Walk 01");
    expect(walkLabel(12)).toBe("Walk 12");
  });
});

describe("minutesToRead", () => {
  it("rounds up and never returns zero", () => {
    expect(minutesToRead(0)).toBe(1);
    expect(minutesToRead(60_000)).toBe(1);
    expect(minutesToRead(60_001)).toBe(2);
    expect(minutesToRead(23.5 * 60_000)).toBe(24);
  });
});
