// The chord-boundary gate (arsenal/web/piano/boundary.js): in pedal mode a note struck while old notes ring under
// the pedal holds the label's re-read for PEDAL_HOLD_SEC, so legato pedalling never reads old+new; the lift, the
// hold expiring, or the pedal being up releases it. Run: node tests/piano_chord_boundary.test.mjs
import assert from "node:assert/strict";
import { createBoundaryGate, BOUNDARY_MODES, PEDAL_HOLD_SEC } from "../arsenal/web/piano/boundary.js";

assert.deepEqual(BOUNDARY_MODES, ["notes", "pedal"], "two modes, one meaning each");
assert.ok(PEDAL_HOLD_SEC > 0.1 && PEDAL_HOLD_SEC < 1, "the hold covers a legato pedal change, not a phrase");

{ // legato pedalling: attack over ringing notes, lift 120 ms later -> the read waits for the lift
  const g = createBoundaryGate({ holdSec: 0.3 });
  g.attack(10.0, true);
  assert.equal(g.holds(10.05, true), true, "held: the lift has not come yet");
  assert.equal(g.holds(10.11, true), true);
  g.lift();
  assert.equal(g.holds(10.12, false), false, "after the lift the new chord is read at once");
  assert.equal(g.until, null);
}
{ // a melody note over a pedalled chord: no lift comes, the hold expires and the union is read
  const g = createBoundaryGate({ holdSec: 0.3 });
  g.attack(20.0, true);
  assert.equal(g.holds(20.29, true), true);
  assert.equal(g.holds(20.30, true), false, "expired: read the union as the notes mode would");
  assert.equal(g.holds(20.31, true), false, "and stays released");
}
{ // nothing ringing (the pedal holds no released note): never holds
  const g = createBoundaryGate();
  g.attack(30.0, false);
  assert.equal(g.holds(30.01, true), false);
}
{ // the pedal is up: a hold cannot apply (setSustain(false) cleared the ringing set already)
  const g = createBoundaryGate();
  g.attack(40.0, true);
  assert.equal(g.holds(40.01, false), false);
  assert.equal(g.until, null, "released, not merely skipped");
}
{ // reset (the Studio select changed): no stale hold survives a mode change
  const g = createBoundaryGate();
  g.attack(50.0, true);
  g.reset();
  assert.equal(g.holds(50.01, true), false);
}
console.log("piano_chord_boundary: ok");
