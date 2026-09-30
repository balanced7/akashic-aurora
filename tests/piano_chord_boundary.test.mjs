// The chord-boundary gate (arsenal/web/piano/boundary.js): in pedal mode a note struck while old notes ring under
// the pedal LATCHES the label's last reading until the lift, so legato pedalling never reads old+new -- for however
// long the lift takes (Heimdall measured attack-to-lift gaps on Daniel's 2026-09-28 session: median 1232 ms, p90
// 3550 ms; the earlier 300 ms hold covered 21% of them). The lift, the pedal being up, or a mode change releases it.
// Run: node tests/piano_chord_boundary.test.mjs
import assert from "node:assert/strict";
import { createBoundaryGate, BOUNDARY_MODES } from "../arsenal/web/piano/boundary.js";

assert.deepEqual(BOUNDARY_MODES, ["notes", "pedal"], "two modes, one meaning each");

{ // legato pedalling: attack over ringing notes, the lift 1.2 s later (the measured median) -> the read waits for it
  const g = createBoundaryGate();
  g.attack(10.0, true);
  assert.equal(g.holds(10.05, true), true, "held: the lift has not come yet");
  assert.equal(g.holds(10.3, true), true, "still held past the old 300 ms hold");
  assert.equal(g.holds(11.23, true), true, "still held at the measured median gap");
  assert.equal(g.holds(13.55, true), true, "and at the p90");
  g.lift();
  assert.equal(g.holds(13.6, false), false, "after the lift the new chord is read at once");
  assert.equal(g.since, null);
}
{ // more attacks while latched (a chord's notes landing one by one) keep the first attack's latch
  const g = createBoundaryGate();
  g.attack(20.0, true);
  g.attack(20.4, true);
  g.attack(20.8, false);
  assert.equal(g.since, 20.0, "the latch is the first attack over ringing notes");
  assert.equal(g.holds(21.0, true), true);
}
{ // nothing ringing (the pedal holds no released note): never holds
  const g = createBoundaryGate();
  g.attack(30.0, false);
  assert.equal(g.holds(30.01, true), false);
  assert.equal(g.since, null);
}
{ // the pedal is up: a latch cannot apply (setSustain(false) cleared the ringing set already)
  const g = createBoundaryGate();
  g.attack(40.0, true);
  assert.equal(g.holds(40.01, false), false);
  assert.equal(g.since, null, "released, not merely skipped");
}
{ // reset (the Studio select changed): no stale latch survives a mode change
  const g = createBoundaryGate();
  g.attack(50.0, true);
  g.reset();
  assert.equal(g.holds(50.01, true), false);
}
console.log("piano_chord_boundary: ok");
