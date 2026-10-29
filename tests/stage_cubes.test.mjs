// Virtual Stage, the HAL 4000 cubes' pure half (arsenal/web/stage/cubes.js): the style a viewer gets, the cube's two
// colours (never hard-coded: from the programmer's light and the palette's roles, or a setup's), the gradient along the
// strand, and the tumble. node --test tests/stage_cubes.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CUBE_STYLES, HAL, TUMBLE_RATES, cubeStyleOf, cubeTintOf, cubeColours, tumbleAngles, unitHue } from "../arsenal/web/stage/cubes.js";
import { stageTheme } from "../arsenal/web/palettes.js";
import { hexToLinear } from "../arsenal/web/stage/lasers.js";

const close = (a, b, eps = 1e-9) => a.every((x, i) => Math.abs(x - b[i]) <= eps);

test("style: ?cubes= wins, automation stays solid, a viewer gets HAL", () => {
  assert.deepEqual([...CUBE_STYLES], ["hal", "solid"]);
  assert.equal(cubeStyleOf("hal", true), "hal");
  assert.equal(cubeStyleOf("solid", false), "solid");
  assert.equal(cubeStyleOf(null, true), "solid");
  assert.equal(cubeStyleOf(null, false), "hal");
  assert.equal(cubeStyleOf("glass", false), "hal");
  assert.equal(cubeStyleOf("glass", true), "solid");
});

test("unitHue: brightest channel 1, black and junk give black", () => {
  assert.deepEqual(unitHue([2, 1, 0.5]), [1, 0.5, 0.25]);
  assert.deepEqual(unitHue([0, 0, 0]), [0, 0, 0]);
  assert.deepEqual(unitHue([NaN, -1, Infinity]), [0, 0, 0]);
  assert.deepEqual(unitHue([-3, 0.2, 0.1]), [0, 1, 0.5]);
});

test("tint: the palette's deep and B by default, a setup's colours on top, one core end fills both", () => {
  const deep = [0.02, 0.005, 0.2], B = [1, 0.04, 0.7];
  const t = cubeTintOf({ deep, B });
  assert.deepEqual(t.glowTop, deep); assert.deepEqual(t.glowBottom, B);
  assert.equal(t.coreTop, null); assert.equal(t.coreBottom, null);
  assert.equal(t.glowMix, HAL.glowMix);
  t.glowTop[0] = 9;                                 // a copy, never the programmer's own array
  assert.equal(deep[0], 0.02);
  const o = cubeTintOf({ deep, B }, { glowBottom: [0, 0, 1], coreTop: [1, 1, 1], glowMix: 3 });
  assert.deepEqual(o.glowTop, deep); assert.deepEqual(o.glowBottom, [0, 0, 1]);
  assert.deepEqual(o.coreTop, [1, 1, 1]); assert.deepEqual(o.coreBottom, [1, 1, 1]);
  assert.equal(o.glowMix, 1);
  const bad = cubeTintOf({ deep, B }, { glowTop: [1, "x"], coreBottom: "red" });
  assert.deepEqual(bad.glowTop, deep); assert.equal(bad.coreTop, null);
  const none = cubeTintOf(null);
  assert.ok(none.glowTop.every(Number.isFinite) && none.glowBottom.every(Number.isFinite));
});

test("colours: the core is the programmer's light, the glow leans to the strand's colour, the gradient runs along it", () => {
  const tint = cubeTintOf({ deep: [0, 0.05, 1], B: [1, 0, 0.5] });
  const core = [0, 0, 0], glow = [0, 0, 0];
  const emit = [0.6, 4.0, 4.4];                      // a cyan cube at 4.4 units
  const lvl = cubeColours(emit, 0, tint, core, glow);
  assert.equal(lvl, 4.4);
  assert.deepEqual(core, emit);                      // the programmer's light untouched
  assert.ok(Math.max(...glow) === 1, "the glow is a hue at unit brightness");
  const cyan = unitHue(emit), blue = [0, 0.05, 1];
  const want = unitHue(cyan.map((c, i) => c + (blue[i] - c) * HAL.glowMix));
  assert.ok(close(glow, want, 1e-12));
  // at the strand's far end the glow leans to B
  const glowEnd = [0, 0, 0];
  cubeColours(emit, 1, tint, core, glowEnd);
  assert.ok(glowEnd[0] > glow[0] + 0.3, "B is red-violet: the far end's glow is redder");
  // halfway is between the two
  const glowMid = [0, 0, 0];
  cubeColours(emit, 0.5, tint, core, glowMid);
  assert.ok(glowMid[0] > glow[0] && glowMid[0] < glowEnd[0]);
  // glowMix 0: the glow is the core's own hue; 1: the strand's alone
  cubeColours(emit, 0, { ...tint, glowMix: 0 }, core, glow); assert.ok(close(glow, cyan, 1e-12));
  cubeColours(emit, 0, { ...tint, glowMix: 1 }, core, glow); assert.ok(close(glow, blue, 1e-12));
});

test("colours: a setup's core hue at the programmer's brightness; a dark cube stays dark with a finite glow", () => {
  const tint = cubeTintOf({ deep: [0, 0, 1], B: [0, 0, 1] }, { coreTop: [1, 1, 1], coreBottom: [1, 0.5, 0] });
  const core = [0, 0, 0], glow = [0, 0, 0];
  cubeColours([0.1, 2.0, 0.3], 0, tint, core, glow);
  assert.ok(close(core, [2, 2, 2]));                 // white at the cube's level
  cubeColours([0.1, 2.0, 0.3], 1, tint, core, glow);
  assert.ok(close(core, [2, 1, 0]));                 // the far end's amber, same level
  const lvl = cubeColours([0, 0, 0], 0.3, cubeTintOf({ deep: [0, 0, 1], B: [1, 0, 0] }), core, glow);
  assert.equal(lvl, 0); assert.deepEqual(core, [0, 0, 0]);
  assert.ok(glow.every(Number.isFinite) && Math.max(...glow) === 1);
  cubeColours([NaN, -1, 2], 0, null, core, glow);
  assert.deepEqual(core, [0, 0, 2]); assert.deepEqual(glow, [0, 0, 1]);
});

test("tumble: three incommensurate rates, a phase per cube, 0 holds the cube square", () => {
  const [a, b, c] = TUMBLE_RATES;
  assert.ok(Math.abs(b / a - Math.SQRT2) < 1e-12 && Math.abs(c / a - (1 + Math.sqrt(5)) / 2) < 1e-12);
  assert.ok(2 * Math.PI / a > 50, "gentle: the slowest axis takes most of a minute per turn");
  assert.deepEqual(tumbleAngles(3, 12.5, 0), [0, 0, 0]);
  const p = tumbleAngles(0, 10), q = tumbleAngles(1, 10);
  assert.ok(p.every((x, i) => x !== q[i]), "neighbouring cubes are out of phase");
  const t0 = tumbleAngles(2, 0), t1 = tumbleAngles(2, 1);
  assert.ok(close(t1.map((x, i) => x - t0[i]), TUMBLE_RATES, 1e-12));
  assert.ok(tumbleAngles(0, NaN, NaN).every((x) => x === 0));
});

test("every palette gives the HAL cubes a finite, coloured glow at both ends of the strand", () => {
  const lib = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
  const core = [0, 0, 0], glow = [0, 0, 0];
  for (const p of lib.palettes) {
    const th = stageTheme(p);
    const tint = cubeTintOf({ deep: hexToLinear(th.ambient), B: hexToLinear(th.B) });
    for (const u of [0, 1]) {
      cubeColours(hexToLinear(th.A).map((x) => x * 5), u, tint, core, glow);
      assert.ok(glow.every(Number.isFinite) && Math.abs(Math.max(...glow) - 1) < 1e-12, `${p.id} at ${u}`);
    }
  }
});
