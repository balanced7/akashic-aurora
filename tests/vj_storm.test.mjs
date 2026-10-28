// The VJ storm receipt's own logic (arsenal/lanes/vj_storm.mjs): the schedules it plays and the floors it holds them to.
// node --test tests/vj_storm.test.mjs
//
// Fix round 2 (2026-10-27): the judge's must-fix 1 found the air receipts (airedge, airstir) had all run with no beam
// lit. airlasers plays the picture Daniel asked for -- lasers held through fog, then CO2 into the lit beams -- and holds
// gate v2 to a gain floor: the air's onset must stay inside the gate, so the limiter never darkens a corner.
import { test } from "node:test";
import assert from "node:assert/strict";
import { SCENARIOS, GAIN_FLOOR, stormSchedule } from "../arsenal/lanes/vj_storm.mjs";

test("airlasers: pad 2 held for the whole run, fog held then CO2 into the lit beams, a gain floor of 0.5", () => {
  const frames = 600, s = stormSchedule("airlasers", frames);
  assert.ok(SCENARIOS.airlasers && GAIN_FLOOR.airlasers === 0.5);
  assert.ok(s.some((e) => e.act === "theme" && e.id === "dreaming-city" && e.f === 0));
  const lasers = s.filter((e) => e.pad === 2);
  assert.equal(lasers.length, 1);
  assert.ok(lasers[0].f === 0 && lasers[0].f + lasers[0].hold > frames, "the beams stay lit to the end");
  const fog = s.filter((e) => e.pad === 6), co2 = s.filter((e) => e.pad === 3);
  assert.equal(fog.length, 2);
  assert.equal(co2.length, fog.length);
  fog.forEach((f, k) => {
    assert.equal(co2[k].f, f.f + f.hold, "CO2 fires as the fog push lets go (the judge's sequence)");
    assert.ok(co2[k].vel === 1 && co2[k].f + 60 < frames, "full velocity, with a second left to watch it bloom");
  });
  // the other storms ask no floor (the limiter is their backstop by design)
  for (const k of Object.keys(SCENARIOS)) if (k !== "airlasers") assert.equal(GAIN_FLOOR[k], undefined, k);
});
