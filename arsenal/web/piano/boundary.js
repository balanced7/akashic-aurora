// The chord-boundary gate (pure: no DOM, no clock, no Theory). Daniel, 2026-09-29: "adjust the chord detection
// logic to have a mode that utilizes when I let go of the sustain pedal to signify a note change. the current
// iteration still captures prior notes."
//
// Two modes, one meaning each:
//   "notes"  (the page as it was): the chord is whatever sounds -- keys held, and keys released while the pedal is
//            down. A new note under the pedal changes the chord at once.
//   "pedal"  a pedal lift ends the chord. The sounding set already drops every pedal-held note at the lift
//            (piano.js setSustain), so the one moment the label could still show "prior notes" is legato pedalling:
//            the new chord's keys go down a beat BEFORE the pedal comes up, and for those milliseconds the sounding
//            set is old-ringing + new-held. This gate holds the label's re-read for up to holdSec after such an
//            attack; if the lift arrives inside the hold, the read happens after it, on the new chord alone. If no
//            lift comes (a melody note over a pedalled chord), the hold expires and the union is read as before.
//            Nothing is consumed or dropped: the sounding set, the notes engine and the practice log see every note.
//
// Offline, the same word means the same thing: arsenal/practice.py harmonic_windows(boundary="pedal") cuts every
// window at a lift and stops the heard-extension there; the replay strip asks for the session's lifts.
export const BOUNDARY_MODES = ["notes", "pedal"];
export const PEDAL_HOLD_SEC = 0.3;  // legato pedalling: the lift lands well inside this after the new attack

export function createBoundaryGate({ holdSec = PEDAL_HOLD_SEC } = {}) {
  let until = null;  // page-clock seconds the hold runs to, or null
  return {
    // A note-on while the pedal is down. ringing: some sounding note is released-but-held-by-the-pedal, i.e. the
    // union the label would read includes notes the coming lift would clear.
    attack(t, ringing) { if (ringing) until = t + holdSec; },
    lift() { until = null; },
    reset() { until = null; },
    // Should the label keep its last reading at time t? Only while the pedal is still down and the hold runs.
    holds(t, sustain) {
      if (until === null) return false;
      if (!sustain || t >= until) { until = null; return false; }
      return true;
    },
    get until() { return until; },
  };
}
