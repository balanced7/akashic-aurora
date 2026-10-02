// Node test, zero dependencies:  node tests/piano_label_holds_through_silence.test.mjs
//
// The big chord label used to read "Listen to the space" whenever nothing was sounding. Daniel asked
// for it to go, and the reason is measurable rather than a matter of taste: in the 2026-10-02 take he
// was playing at 143 bpm with a MEDIAN GAP OF 196 ms between attacks, so the prompt appeared and
// vanished several times a second. At that rate it is not a message, it is a flicker.
//
// It now HOLDS the last chord through the silence and dims it. The eye gets something stable, and
// the colour carries the state the text used to spell out.
//
// Only this decision is pinned. The rest of draw() needs a canvas and a WebGL context, which is
// exactly why the decision was lifted out into a pure function.

import { labelState, LABEL_HELD, LABEL_HELD_SUB } from "../arsenal/web/piano/harmony-renderer.js";

let pass = 0, fail = 0;
const check = (label, ok, detail = "") => {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
};
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);

const READ = { nnsMode: "chord", nns: "1m", key: { name: "D minor" } };
const Dm = { name: "Dm7", root: 2, notes: [{ midi: 50 }, { midi: 53 }, { midi: 57 }] };

// ---------------------------------------------------------------- sounding
const live = labelState(Dm, READ, { text: "", number: null });
eq("a sounding chord is shown", live.text, "Dm7");
check("a sounding chord reports sounding", live.sounding === true);

// ---------------------------------------------------------------- the whole point
const held = labelState(null, READ, { text: "Dm7", number: "1m" });
eq("silence HOLDS the last chord", held.text, "Dm7");
check("silence reports NOT sounding", held.sounding === false);
check("silence never invents a prompt",
  !/listen|space|silence|play something/i.test(held.text), `got ${held.text}`);

// ---------------------------------------------------------------- before the first note
const cold = labelState(null, READ, { text: "", number: null });
eq("with nothing ever played the label is empty, not a greeting", cold.text, "");
check("and it is still marked not sounding", cold.sounding === false);

// ---------------------------------------------------------------- the memory must not go stale
const a = labelState({ name: "Bb", root: 10, notes: [{ midi: 46 }] }, READ, { text: "Dm7", number: "1m" });
eq("a new chord replaces what is held", a.text, "Bb");
check("and it is sounding, so the caller will store it", a.sounding === true);

// ---------------------------------------------------------------- numbers mode still works
const nums = labelState(Dm, { ...READ, nnsMode: "numbers", nns: "1m" }, { text: "", number: null });
eq("numbers mode shows the number, not the chord name", nums.text, "1m");

// ---------------------------------------------------------------- the note-soup case survives
const soup = { name: "D A Bb B C F G E", root: null, notes: Array.from({ length: 8 }, (_, i) => ({ midi: 50 + i })) };
eq("a rootless pile of notes is summarised by its count", labelState(soup, READ, { text: "", number: null }).text, "8 notes");

// ---------------------------------------------------------------- the inks differ and are dim
check("the held ink is defined and distinct from the live ink", LABEL_HELD && LABEL_HELD !== "#e4ecdf");
check("the held sub-ink is dimmer still than the held ink",
  parseInt(LABEL_HELD_SUB.slice(1), 16) < parseInt(LABEL_HELD.slice(1), 16),
  `${LABEL_HELD_SUB} vs ${LABEL_HELD}`);

// ---------------------------------------------------------------- robustness
check("a missing reading does not throw", (() => {
  try { labelState(null, undefined, undefined); return true; } catch { return false; }
})());

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
