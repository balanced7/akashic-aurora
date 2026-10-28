import { describe, expect, it } from "vitest";

import { hslToHex } from "../common";

describe("hslToHex", () => {
  it.each([
    [0, 1, 0.5, "#ff0000"],
    [120, 1, 0.5, "#00ff00"],
    [240, 1, 0.5, "#0000ff"],
    [0, 0, 0, "#000000"],
    [0, 0, 1, "#ffffff"],
  ])("should convert HSL to hex correctly", (h, s, l, expected) => {
    expect(hslToHex(h, s, l)).toBe(expected);
  });
});
