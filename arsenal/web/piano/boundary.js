// The chord-boundary gate (pure: no DOM, no clock, no Theory). Daniel, 2026-09-29: "adjust the chord detection
// logic to have a mode that utilizes when I let go of the sustain pedal to signify a note change. the current
// iteration still captures prior notes."
//
// Two modes, one meaning each:
//   "notes"  (the page as it was): the chord is whatever sounds -- keys held, and keys released while the pedal is
//            down. A new note under the pedal changes the chord at once.
//   "pedal"  a pedal lift ends the chord. The sounding set already drops every pedal-held note at the lift
//            (piano.js setSustain), so the one moment the label could still show "prior notes" is legato pedalling:
//            the new chord's keys go down BEFORE the pedal comes up, and until it does the sounding set is
//            old-ringing + new-held. This gate LATCHES the label's last reading at such an attack and releases it at
//            the lift: the read happens after the lift, on the new chord alone. It is a latch, not a timeout. The
//            first cut of this gate held for 300 ms; Heimdall measured the attack-to-lift gap on Daniel's 2026-09-28
//            session (6628 attacks over ringing notes) at median 1232 ms, p90 3550 ms -- the hold expired before 79%
//            of the lifts and the union flashed, which is exactly "still captures prior notes". A melody note over a
//            pedalled chord therefore keeps the chord's label until the next lift; in this mode that is what the
//            word means. Nothing is consumed or dropped: the sounding set, the notes engine and the practice log see
//            every note.
//
// Offline, the same word means the same thing: arsenal/practice.py harmonic_windows(boundary="pedal") cuts every
// window at a lift, stops the heard-extension there, and no merge (before or after naming) joins across one; the
// replay strip asks for the session's lifts.
export const BOUNDARY_MODES = ["notes", "pedal"];

export function createBoundaryGate() {
  let since = null;  // page-clock seconds of the attack that latched the label, or null
  return {
    // A note-on while the pedal is down. ringing: some sounding note is released-but-held-by-the-pedal, i.e. the
    // union the label would read includes notes the coming lift would clear.
    attack(t, ringing) { if (ringing && since === null) since = t; },
    lift() { since = null; },
    reset() { since = null; },
    // Should the label keep its last reading at time t? While the pedal is still down and no lift has come.
    holds(t, sustain) {
      if (since === null) return false;
      if (!sustain) { since = null; return false; }
      return true;
    },
    get since() { return since; },
  };
}
