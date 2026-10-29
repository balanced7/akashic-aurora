// Virtual Stage, the HAL 4000 cubes' pure half (arsenal/web/stage/cubes.js): the style a viewer gets, the cube's two
// colours (never hard-coded: from the programmer's light and the palette's roles, or a setup's), the gradient along the
// strand, the kick's hold on the glow, and the spin. node --test tests/stage_cubes.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CUBE_STYLES, HAL, SPIN_RATE, WOBBLE_RATES, HAL_WOBBLE, cubeStyleOf, cubeTintOf, cubeColours, cubeKickOf, tumbleAngles, unitHue } from "../arsenal/web/stage/cubes.js";
import { stageTheme, lchOfLin, hueGap, satOf } from "../arsenal/web/palettes.js";
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
  assert.ok(close(glow, want, 1e-6));
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
  cubeColours(emit, 0, { ...tint, glowMix: 1 }, core, glow); assert.ok(close(glow, blue, 1e-6));
});

test("colours: a setup's core hue at the programmer's brightness; a dark cube stays dark with a finite glow", () => {
  const tint = cubeTintOf({ deep: [0, 0, 1], B: [0, 0, 1] }, { coreTop: [1, 1, 1], coreBottom: [1, 0.5, 0] });
  const core = [0, 0, 0], glow = [0, 0, 0];
  cubeColours([0.1, 2.0, 0.3], 0, tint, core, glow);
  assert.ok(close(core, [2, 2, 2], 1e-5));                 // white at the cube's level
  cubeColours([0.1, 2.0, 0.3], 1, tint, core, glow);
  assert.ok(close(core, [2, 1, 0], 1e-5));                 // the far end's amber, same level
  const lvl = cubeColours([0, 0, 0], 0.3, cubeTintOf({ deep: [0, 0, 1], B: [1, 0, 0] }), core, glow);
  assert.equal(lvl, 0); assert.deepEqual(core, [0, 0, 0]);
  assert.ok(glow.every(Number.isFinite) && Math.max(...glow) === 1);
  cubeColours([NaN, -1, 2], 0, null, core, glow);
  assert.deepEqual(core, [0, 0, 2]); assert.deepEqual(glow, [0, 0, 1]);
});

test("spin: on the rung's axle with a gentle wobble, a phase per cube, 0 holds the cube square, never past 1", () => {
  const [w1, w2] = WOBBLE_RATES;
  assert.ok(Math.abs(w2 / w1 - (1 + Math.sqrt(5)) / 2 / Math.SQRT2) < 1e-12, "the wobbles never line up");
  assert.ok(2 * Math.PI / SPIN_RATE > 30 && 2 * Math.PI / SPIN_RATE < 60, "gentle: a turn in under a minute, over half of one");
  assert.deepEqual(tumbleAngles(3, 12.5, 0), [0, 0, 0]);
  const p = tumbleAngles(0, 10), q = tumbleAngles(1, 10);
  assert.ok(p.every((x, i) => x !== q[i]), "neighbouring cubes are out of phase");
  const t0 = tumbleAngles(2, 0), t1 = tumbleAngles(2, 1);
  assert.ok(Math.abs(t1[0] - t0[0] - SPIN_RATE) < 1e-12, "the spin about the axle runs at its rate");
  // the axle stays the axle: over ten minutes the off-axis angles never pass the wobble
  for (let t = 0; t < 600; t += 0.37) for (let k = 0; k < 24; k++) {
    const a = tumbleAngles(k, t);
    assert.ok(Math.abs(a[1]) <= HAL_WOBBLE + 1e-12 && Math.abs(a[2]) <= HAL_WOBBLE + 1e-12);
  }
  assert.ok(HAL_WOBBLE < 0.2, "a wobble, not a tumble: the dot strip meets the inner face within ~11 degrees of square");
  assert.deepEqual(tumbleAngles(1, 5, 3), tumbleAngles(1, 5, 1), "an amount past 1 is 1");
  assert.ok(tumbleAngles(0, NaN, NaN).every((x) => x === 0));
});

test("the gradient runs the whole strand: each end at unit brightness, mixed through OKLCh (no B swamping a dark deep, no white middle)", () => {
  const core = [0, 0, 0], glow = [0, 0, 0];
  // a deep 50x darker than B (the palettes' own ratio): halfway along, the hue is halfway (it was B's by the second rung)
  const deep = [0.004, 0.0, 0.03], B = [1.0, 0.03, 0.55];
  const tint = cubeTintOf({ deep, B });
  const hOf = (u) => { cubeColours([0, 0, 0], u, { ...tint, glowMix: 1 }, core, glow); return lchOfLin(glow).h; };
  const h0 = hOf(0), h1 = hOf(1), hm = hOf(0.5), hq = hOf(1 / 11);
  const span = hueGap(h0, h1);
  assert.ok(span > 20, `the ends differ (${span.toFixed(1)} deg)`);
  assert.ok(Math.abs(hueGap(h0, hm) - span / 2) < span * 0.12, `halfway is halfway (${hueGap(h0, hm).toFixed(1)} of ${span.toFixed(1)})`);
  assert.ok(hueGap(h0, hq) < span * 0.2, `the second rung is still near the deep end (${hueGap(h0, hq).toFixed(1)})`);
  // complements turn round the circle: the middle keeps its colour
  const comp = cubeTintOf({ deep: [0, 0.2, 1], B: [1, 0.6, 0] });
  for (const u of [0, 0.25, 0.5, 0.75, 1]) {
    cubeColours([0, 0, 0], u, { ...comp, glowMix: 1 }, core, glow);
    assert.ok(satOf(glow) > 0.5, `complements at ${u}: saturation ${satOf(glow).toFixed(2)} (not white)`);
  }
});

test("a steady frame reuses the tint: same object, same ramp, rebuilt only when an end moves", () => {
  const out = {}, deep = [0.02, 0.005, 0.2], B = [1, 0.04, 0.7];
  const t1 = cubeTintOf({ deep, B }, null, out), lut = t1.glowLut, top = t1.glowTop;
  const t2 = cubeTintOf({ deep, B }, null, out);
  assert.equal(t2, t1); assert.equal(t2.glowLut, lut); assert.equal(t2.glowTop, top);
  const before = Array.from(lut);
  cubeTintOf({ deep, B: [0, 1, 0] }, null, out);
  assert.notDeepEqual(Array.from(out.glowLut), before, "B moved: the ramp follows");
  assert.equal(out.glowLut, lut, "into the same array");
  cubeTintOf({ deep, B }, { coreTop: [1, 1, 1] }, out); assert.ok(out.coreLut);
  cubeTintOf({ deep, B }, null, out); assert.equal(out.coreLut, null);
});

test("a kick takes the glow with it: colour or white on the cube's cells, back to the gradient as it fades", () => {
  const nC = 12, kickC = new Float32Array(nC * 4), tC = new Float64Array(nC * 4), W = 2;
  for (let c = 0; c < nC; c++) { tC[c * 4 + 2] = 0; tC[c * 4 + 3] = 1; tC[c * 4 + 1] = 0.3; }   // A to B at rest
  const src = { kickC, tC, whiteRole: W };
  assert.equal(cubeKickOf(src, 6, 6), 0);
  assert.equal(cubeKickOf(null, 0, 6), 0);
  kickC[7 * 4 + 3] = 0.75;                                  // a colour kick on one of the cube's cells
  assert.equal(cubeKickOf(src, 6, 6), 0.75);
  assert.equal(cubeKickOf(src, 0, 6), 0, "another cube's cells are not this one's");
  kickC.fill(0);
  tC[8 * 4 + 3] = W; tC[8 * 4 + 1] = 0.6;                   // the white kick: W over the look's role at its weight
  assert.equal(cubeKickOf(src, 6, 6), 0.6);
  tC[9 * 4 + 2] = W; tC[9 * 4 + 1] = 0;                     // white as the first role, mix 0: all white
  assert.equal(cubeKickOf(src, 6, 6), 1);
  // the glow: at rest it leans to the strand's colour; kicked it is the core's own (white kick: white)
  const tint = cubeTintOf({ deep: [0.6, 0, 1], B: [1, 0, 0.6] }), core = [0, 0, 0], glow = [0, 0, 0];
  cubeColours([3, 0.4, 2.4], 0.5, tint, core, glow, 0);
  assert.ok(glow[1] < 0.2, "at rest: the palette's pink-violet");
  cubeColours([3, 3, 3], 0.5, tint, core, glow, 1);
  assert.ok(close(glow, [1, 1, 1], 1e-9), "a full white kick: a white glow, as the solid cube goes white");
  const half = [0, 0, 0];
  cubeColours([3, 3, 3], 0.5, tint, core, half, 0.5);
  assert.ok(half[1] > 0.2 && half[1] < 1, "fading: between the two");
});

test("every palette gives the HAL cubes a finite glow at both ends of the strand, coloured as its own roles are", () => {
  const lib = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
  const core = [0, 0, 0], glow = [0, 0, 0];
  for (const p of lib.palettes) {
    const th = stageTheme(p);
    const deep = hexToLinear(th.ambient), B = hexToLinear(th.B);
    const tint = cubeTintOf({ deep, B });
    for (const [u, end] of [[0, deep], [1, B]]) {
      cubeColours(hexToLinear(th.A).map((x) => x * 5), u, tint, core, glow);
      assert.ok(glow.every(Number.isFinite) && Math.abs(Math.max(...glow) - 1) < 1e-12, `${p.id} at ${u}`);
      // the strand's own colour at this end (glowMix 1): the end's hue at its own chroma (a neutral palette's grey stays
      // grey, a coloured one's colour stays a colour)
      cubeColours([0, 0, 0], u, { ...tint, glowMix: 1 }, core, glow);
      const want = unitHue(end), g = lchOfLin(glow), w = lchOfLin(want);
      assert.ok(Math.abs(g.C - w.C) < 0.02, `${p.id} at ${u}: chroma ${g.C.toFixed(3)} for ${w.C.toFixed(3)}`);
      if (w.C > 0.05) assert.ok(hueGap(g.h, w.h) < 3, `${p.id} at ${u}: hue ${g.h.toFixed(1)} for ${w.h.toFixed(1)}`);
      // the deep end of every coloured palette is a colour (OKLCh chroma 0.13 or more at unit brightness; the three
      // neutral palettes' deeps are their own steel, bone and black greys, 0.05 to 0.08)
      if (p.family !== "neutral" && u === 0) assert.ok(g.C > 0.1, `${p.id} at ${u}: a coloured palette's glow is a colour (C ${g.C.toFixed(3)})`);
    }
  }
});
