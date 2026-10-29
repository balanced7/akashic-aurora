// Stage stills (arsenal/web/stage/stills.js): candidate shots from window.__extraShots, checked and merged over the set's
// shots; ?shot= forces one by hand. node --test tests/stage_stills.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { shotProblems, withExtraShots, askedShot, kindOf } from "../arsenal/web/stage/stills.js";
import { Director } from "../arsenal/web/stage/camera.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const SHOTS = SCENE.cameras.shots;

test("every shot of source-v1 passes the candidate check (the check is no stricter than the set)", () => {
  for (const [id, def] of Object.entries(SHOTS)) if (!id.startsWith("_")) assert.deepEqual(shotProblems(id, def), [], id);
});

test("a bad candidate is refused with its reason, the good ones join, an existing id is replaced", () => {
  const extra = {
    WIDE_TEST: { kind: "static", pos: [0, 30, 120], look: [0, 12, -10], hfov: 70 },
    ORBIT_NO_KIND: { orbit: { centre: [0, 14, -11], radius: 80, height: 30, from_deg: -20, to_deg: 20 }, hfov: 60 },
    FOH_WIDE: { kind: "static", pos: [0, 6, 60], look: [0, 13, -4], hfov: 64 },
    NO_LOOK: { kind: "static", pos: [0, 1, 2] },
    SELF: { kind: "static", pos: [0, 1, 2], look: [0, 1, 2] },
    BAD_LENS: { kind: "static", pos: [0, 1, 2], look: [0, 1, 3], hfov: 200 },
    "bad id!": { kind: "static", pos: [0, 1, 2], look: [0, 1, 3] },
    _note: "underscore keys are comments",
  };
  const r = withExtraShots(SHOTS, extra);
  assert.deepEqual(r.added.sort(), ["ORBIT_NO_KIND", "WIDE_TEST"]);
  assert.deepEqual(r.replaced, ["FOH_WIDE"]);
  assert.equal(r.problems.length, 4, r.problems.join("\n"));
  assert.equal(r.shots.ORBIT_NO_KIND.kind, "orbit");
  assert.deepEqual(r.shots.FOH_WIDE.pos, [0, 6, 60]);
  assert.equal(SHOTS.FOH_WIDE.pos[2], 56, "the set's own table is untouched");
  // the Director prepares the merged table like the set's (and the sequences still resolve)
  const d = new Director(r.shots, SCENE.cameras.sequences);
  assert.ok(d.shots.WIDE_TEST && d.shots.ORBIT_NO_KIND._ease);
});

test("kindOf reads a shot's kind from its fields when it does not say", () => {
  assert.equal(kindOf({ pos_path: [[0, 0, 0], [1, 1, 1]] }), "path");
  assert.equal(kindOf({ strand: { s: [0, 1] } }), "strand");
  assert.equal(kindOf({ pos: [0, 0, 0], look: [0, 0, 1] }), "static");
});

test("?shot= forces a known shot (played, or held at ?shot_u=)", () => {
  assert.deepEqual(askedShot(new URLSearchParams("shot=FOH_WIDE"), SHOTS), { id: "FOH_WIDE", u: null });
  assert.deepEqual(askedShot(new URLSearchParams("shot=HALO_ORBIT&shot_u=0.25"), SHOTS), { id: "HALO_ORBIT", u: 0.25 });
  assert.equal(askedShot(new URLSearchParams("shot=NOPE"), SHOTS), null);
  assert.equal(askedShot(new URLSearchParams(""), SHOTS), null);
});
