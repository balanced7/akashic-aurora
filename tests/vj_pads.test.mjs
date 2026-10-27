// Tests for arsenal/web/vj-pads.js: pads v2 (VJ V2 build spec section B). The rows keep their meaning; velocity is size;
// a second press within a bar escalates; a one-shot's life lands on the grid; repeats move (a motion and a spot dealt
// per press); holds become standing motions; a tap of a hold pad plays its short version; the hero's charge; build then
// drop; one Safety pad. Zero dependencies, no GPU:
//   node --test tests/vj_pads.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_PAD_MAP, PAD_ACTIONS, glitchPlan, GLITCH_MODES } from "../arsenal/web/vj-core.js";
import { CLASSES } from "../arsenal/web/vj-motions.js";
import * as P from "../arsenal/web/vj-pads.js";

const press = (play, pad, pos, opt = {}) => play.press(pad, DEFAULT_PAD_MAP[pad - 1], { perMs: 400, vel: 0.7, nowMs: pos * 400, live: true, ...opt, pos });

test("every default pad speaks a verb, and the rows keep their meaning: 1-4 hits, 5-8 holds, 9-12 moves", () => {
  DEFAULT_PAD_MAP.forEach((action, i) => {
    const v = P.verbOf(action);
    assert.ok(v, `pad ${i + 1}: ${action}`);
    assert.equal(v.row, Math.floor(i / 4) + 1, `pad ${i + 1} (${action}) in row ${v.row}`);
  });
  assert.equal(DEFAULT_PAD_MAP[1], "laser", "pad 2 stays the lasers");
  for (const a of Object.keys(P.PAD_VERBS)) assert.ok(PAD_ACTIONS.includes(a), `${a} is a pad action`);
  for (const a of ["strobe", "particles", "kaleido", "freeze"]) assert.ok(P.PAD_VERBS[a].hold && P.PAD_VERBS[a].motion, `${a}: a hold that moves`);
});

test("lineAfter: the first grid line at or after pos + minAhead", () => {
  assert.equal(P.lineAfter(0, 4), 0);
  assert.equal(P.lineAfter(0.01, 4), 4);
  assert.equal(P.lineAfter(3.3, 1 / 2, 1 / 8), 3.5);
  assert.equal(P.lineAfter(3.4, 1 / 2, 1 / 8), 4);
  assert.equal(P.lineAfter(1.2, 4, 1), 4);
  assert.equal(P.lineAfter(3.2, 4, 1), 8);
});

test("velocity is size; a downbeat plays bigger than an off-beat; without a live beat every press is mid-weight", () => {
  const sz = (pos, vel, live = true) => press(new P.PadPlay(), 1, pos, { vel, live }).size;
  assert.ok(sz(0, 1) > sz(0, 0.3) * 1.5, "hard is much bigger than soft");
  assert.ok(sz(0, 0.8) > sz(0.5, 0.8), "the ONE over the off-beat");
  assert.ok(sz(4, 0.8) > sz(4.25, 0.8), "a bar line over a 16th");
  assert.equal(sz(0.37, 0.8, false), sz(4, 0.8, false), "no beat: no accent");
  const play = new P.PadPlay();
  for (let k = 0; k < 40; k++) assert.ok(press(play, 1, k * 0.7, { vel: 1 }).size <= P.SIZE_MAX + 1e-9);
});

test("a second press within a bar escalates (to three); a press more than ~a bar on starts over; faster than 3 a second never grows", () => {
  const play = new P.PadPlay();
  assert.equal(press(play, 1, 0).esc, 1);
  assert.equal(press(play, 1, 2).esc, 2);
  assert.equal(press(play, 1, 4).esc, 3);
  assert.equal(press(play, 1, 6).esc, 3, "three is the top");
  assert.equal(press(play, 1, 12).esc, 1, "6 beats on: a fresh first hit");
  assert.equal(press(play, 4, 12.5).esc, 1, "each pad has its own ladder");
  const a = press(play, 1, 13);
  const r = play.press(1, "shockwave", { pos: 13.2, perMs: 400, vel: 0.7, nowMs: 13 * 400 + 100, live: true });
  assert.ok(r.rapid && r.esc === a.esc, "a rapid press keeps the level");
  assert.ok(r.size < press(new P.PadPlay(), 1, 13.2).size, "and plays smaller");
  play.reset();
  assert.equal(press(play, 1, 13.5).esc, 1, "Choke starts every ladder over");
  // the light previews it: the level the next press would reach
  const q = new P.PadPlay();
  assert.equal(q.ledLevel(1, 0), P.ESC_LED[0]);
  press(q, 1, 0);
  assert.equal(q.ledLevel(1, 3), P.ESC_LED[1]);
  press(q, 1, 3);
  assert.equal(q.ledLevel(1, 4), P.ESC_LED[2]);
  assert.equal(q.ledLevel(1, 20), P.ESC_LED[0]);
  assert.ok(P.ESC_LED[0] < P.ESC_LED[1] && P.ESC_LED[1] < P.ESC_LED[2], "brighter the higher the next press reaches");
});

test("a one-shot's life lands on its grid: never shorter than three quarters of its stretched length", () => {
  const play = new P.PadPlay();
  for (const [pad, verb] of [[1, P.PAD_VERBS.shockwave], [4, P.PAD_VERBS.glitch], [12, P.PAD_VERBS.zoom]]) {
    for (const pos of [0, 0.13, 0.5, 0.99, 3.71, 7.06]) for (const vel of [0.2, 0.6, 1]) {
      const h = press(play, pad, pos + pad * 100, { vel });
      const stretch = 0.6 + 0.8 * vel;
      const g = h.endPos / verb.grid;
      assert.ok(Math.abs(g - Math.round(g)) < 1e-9, `pad ${pad} at ${pos}: ends on its grid (${h.endPos})`);
      assert.ok(h.lifeBeats >= 0.75 * verb.life * stretch - 1e-9 && h.lifeBeats < 0.75 * verb.life * stretch + verb.grid + 1e-9, `pad ${pad}: ${h.lifeBeats}`);
    }
  }
  assert.equal(press(new P.PadPlay(), 1, 0.3, { vel: 1 }).endPos, 4, "a hard ring at 0.3 rings until beat 4");
  assert.equal(press(new P.PadPlay(), 5, 0.3).endPos, null, "a hold pad's end waits for its release");
});

test("repeats move: each press deals a spot (never one of the last two) and a motion of the pad's own deck", () => {
  const play = new P.PadPlay({ seed: 7 });
  const spots = [], motions = [];
  for (let k = 0; k < 32; k++) {
    const h = press(play, 1, k * 8);
    spots.push(h.spot); motions.push(h.motion && h.motion.id);
    assert.ok(h.spot >= 0 && h.spot < P.SPOTS.length);
    assert.ok(h.motion && !h.motion.m.texture, `press ${k}: a whole motion`);
  }
  for (let k = 2; k < spots.length; k++) assert.ok(spots[k] !== spots[k - 1] && spots[k] !== spots[k - 2], `spot ${k}`);
  for (let r = 0; r + 8 <= 32; r += 8) assert.ok(new Set(spots.slice(r, r + 8)).size >= 6, `round ${r / 8}: the stage gets walked`);
  for (let k = 1; k < motions.length; k++) assert.notEqual(motions[k], motions[k - 1], `motion ${k}`);
  assert.ok(new Set(motions).size >= 6, "a varied deck");
  assert.equal(press(play, 2, 300).motion, null, "the lasers deal their own motion (vj-lasers.js)");
  assert.equal(press(play, 2, 300).spot, null);
  // the seed is the deal: the same seed, the same run
  const again = new P.PadPlay({ seed: 7 });
  assert.deepEqual(Array.from({ length: 32 }, (_, k) => press(again, 1, k * 8).spot), spots);
});

test("a hold becomes a standing motion after half a beat, of its section's budget; a held hit pad strikes on every beat", () => {
  const play = new P.PadPlay();
  press(play, 5, 1.0);
  assert.equal(play.hold(5, { pos: 1.4 }), null);
  const h = play.hold(5, { pos: 1.5, section: "drop" });
  assert.ok(h && h.held && h.standing && h.standing.looping, "a standing motion");
  assert.equal(h.standing.cls, "M1", "a bar in a drop");
  assert.equal(play.hold(5, { pos: 1.6 }), null, "once");
  assert.ok(play.isHeld(5) && play.standing(5) === h.standing);
  press(play, 6, 10);
  assert.equal(play.hold(6, { pos: 10.6, section: "break" }).standing.cls, "M2b", "two bars in a break");
  // the ring held ripples on each beat line, once a frame, never a burst after a skipped frame
  press(play, 1, 20.2);
  assert.equal(play.repeats(1, 20.6), 0, "not a hold yet");
  play.hold(1, { pos: 20.7 });
  assert.equal(play.repeats(1, 20.9), 0);
  assert.equal(play.repeats(1, 21.0), 1, "the next beat");
  assert.equal(play.repeats(1, 21.5), 0);
  assert.equal(play.repeats(1, 24.4), 1, "a long frame: one strike");
  assert.equal(play.repeats(1, 24.6), 0);
  play.release(1, { pos: 24.7 });
  assert.equal(play.repeats(1, 26), 0, "let go: no more");
});

test("a tap of a hold pad plays its short version; a release after a hold lands on the eighth grid", () => {
  const play = new P.PadPlay();
  press(play, 5, 1.2);                                   // the shutters, tapped: a bar's worth, to the next bar line
  assert.deepEqual(play.release(5, { pos: 1.3 }).endPos, 4);
  press(play, 5, 3.6);
  assert.equal(play.release(5, { pos: 3.7 }).endPos, 8, "at least a beat: beat 4 is too close, the next bar line");
  press(play, 3, 10.1);                                  // CO2, tapped: a puff to the next eighth at least a quarter on
  assert.equal(play.release(3, { pos: 10.15 }).endPos, 10.5);
  press(play, 8, 2.0);                                   // the freeze, tapped: a hit-stop to the next quarter of a beat
  assert.equal(play.release(8, { pos: 2.05 }).endPos, 2.25);
  press(play, 5, 20);
  play.hold(5, { pos: 21 });
  const r = play.release(5, { pos: 23.3 });
  assert.ok(r.held && !r.tap);
  assert.equal(r.endPos, 23.5, "the exit lands on the next eighth, at least an eighth of a beat on");
  assert.equal(play.release(5, { pos: 24 }), null, "already up");
});

test("CO2 held lets go by itself after 3 s (a real cannon never fires for ever)", () => {
  const play = new P.PadPlay();
  play.press(3, "co2", { pos: 0, perMs: 400, vel: 1, nowMs: 1000 });
  assert.ok(play.hold(3, { pos: 0.6, nowMs: 1240 }).held);
  assert.equal(play.hold(3, { pos: 7, nowMs: 3900 }), null);
  assert.deepEqual(play.hold(3, { pos: 7.6, nowMs: 4000 }), { expire: true });
  assert.equal(play.hold(3, { pos: 8, nowMs: 4100 }), null, "once");
});

test("the hero: charged at the start; the payoff lands on the next ONE; the charge refills over 8 bars", () => {
  const h = new P.HeroCharge();
  assert.equal(h.charge(0), 1);
  assert.deepEqual(h.press(1.3), { at: 4 });
  assert.equal(h.press(1.5), null, "booked: no second payoff");
  assert.equal(h.due(3.95), null);
  assert.equal(h.due(4.01), 4);
  assert.equal(h.due(4.2), null, "once");
  assert.equal(h.fired, 1);
  assert.equal(h.charge(20), 0.5);
  assert.equal(h.press(20), null, "still charging");
  assert.ok(h.ready(36));
  assert.deepEqual(h.press(36.04), { at: 36 }, "a press just after the line plays on it");
  assert.equal(h.due(36.04), 36);
});

test("build then drop: a tap builds 4, 8 or 16 bars by velocity and drops on the bar line; a second tap drops on the next one", () => {
  const b = new P.BuildDrop();
  assert.deepEqual(b.press(1.0, 0.3), { act: "build", bars: 4, at: 16 });
  b.release(1.1);
  assert.ok(Math.abs(b.progress(8.5) - 0.5) < 1e-9);
  assert.equal(b.division(5), 1); assert.equal(b.division(10), 1 / 2); assert.equal(b.division(15), 1 / 4);
  assert.equal(b.tick(15.9), null);
  assert.equal(b.tick(16), "drop");
  assert.equal(b.tick(16.1), null, "once");
  assert.equal(b.phase, "drop");
  b.tick(16 + 4 * P.DROP_BARS);
  assert.equal(b.phase, "idle", "the drop's section runs its 16 bars");
  const c = new P.BuildDrop();
  assert.equal(c.press(0.2, 1).at, 64, "hard: 16 bars");
  c.release(0.3);
  assert.deepEqual(c.press(5.1, 0.5), { act: "drop-next", at: 8 }, "again: the next downbeat at least a beat on");
  c.release(5.2);
  assert.equal(c.tick(8), "drop");
  assert.equal(P.buildBarsFor(0.6), 8);
});

test("build then drop: held a beat it is a riser, and the release drops on the next downbeat", () => {
  const b = new P.BuildDrop();
  b.press(10, 0.5);
  assert.equal(b.hold(10.5), false);
  assert.equal(b.hold(11), true);
  assert.equal(b.hold(12), false, "once");
  assert.ok(b.progress(14) > 0 && b.progress(14) < 1);
  assert.equal(b.tick(40), null, "a riser waits for the release");
  assert.deepEqual(b.release(41.3), { act: "drop", at: 44 });
  assert.equal(b.tick(44), "drop");
  const c = new P.BuildDrop();
  c.press(1, 0.5); c.hold(2.5);
  assert.equal(c.release(8.04).at, 8, "a release just after the line drops on it");
});

test("Safety: a tap dampens, a hard tap chokes", () => {
  assert.equal(P.safetyAct(0.6), "dampen");
  assert.equal(P.safetyAct(0.8), "dampen");
  assert.equal(P.safetyAct(0.81), "choke");
  assert.ok(P.PAD_VERBS.safety.hold, "held: black while held");
});

test("motions dealt to the pads honour the flash rule: no whole motion acts more than 3 a second, rapid presses get textures", () => {
  const play = new P.PadPlay({ seed: 3 });
  for (let k = 0; k < 64; k++) {
    const pos = k * 0.5, h = press(play, 7, pos, { nowMs: pos * 400 });          // presses every half beat at 150 BPM
    if (!h.motion) continue;
    const m = h.motion;
    const spanMs = (m.p1 - m.p0) * 400;
    if (!m.m.texture) assert.ok(1000 * m.m.flashes / Math.max(spanMs, 1) <= 3 + 1e-6 || spanMs >= 1000 / 3, `${m.id} ${m.cls}`);
  }
  const fast = new P.PadPlay();
  press(fast, 6, 0, { nowMs: 0 });
  const r = fast.press(6, "particles", { pos: 0.25, perMs: 400, vel: 0.9, nowMs: 100, live: true });
  assert.ok(r.rapid && (!r.motion || CLASSES[r.motion.cls].texture), "a rapid press shimmers at most");
});

test("CO2: a row of 2 to 8 jets centred on the spot, 1/16 beat apart in a dealt order, harder with size and escalation", () => {
  const hit = (size, esc, spot) => ({ size, esc, spot });
  const soft = P.co2Jets(hit(0.3, 1, 0)), hard = P.co2Jets(hit(1.4, 1, 0)), top = P.co2Jets(hit(1.4, 3, 0));
  assert.ok(soft.length >= 2 && soft.length < hard.length && top.length === 8, `${soft.length} ${hard.length} ${top.length}`);
  for (const jets of [soft, hard, top]) {
    for (const j of jets) {
      assert.ok(j.x01 >= 0 && j.x01 <= 1 && j.strength > 0 && j.strength <= 1);
      assert.ok(j.delay <= (jets.length - 1) * P.CO2_STEP_BEATS + 1e-9 && j.delay < 1 / 2, "the whole row within half a beat");
    }
    for (let i = 1; i < jets.length; i++) assert.ok(jets[i].x01 > jets[i - 1].x01, "left to right along the floor");
  }
  assert.ok(top[0].strength > soft[0].strength);
  const left = P.co2Jets(hit(1, 1, 5)), right = P.co2Jets(hit(1, 1, 6));
  const mid = (js) => js.reduce((a, j) => a + j.x01, 0) / js.length;
  assert.ok(mid(left) < 0.5 && mid(right) > 0.5, "the row stands where the spot was dealt");
  const orders = new Set();
  for (let spot = 0; spot < 8; spot++) for (const esc of [1, 2, 3]) orders.add(P.co2Jets(hit(1, esc, spot)).map((j) => j.delay).join());
  assert.ok(orders.size >= 4, "the order changes with the spot and the level");
});

test("the Glitch Lift pressed again within a bar: a second mode at any velocity, then harder and in bigger blocks", () => {
  for (let k = 0; k < 40; k++) {
    const seed = (k * 0.618034) % 1;
    for (const vel of [0.3, 0.9]) {
      const plan = glitchPlan(seed, vel);
      assert.deepEqual(P.escalateGlitch(plan, 1, GLITCH_MODES), plan, "the first press is the plan as it was");
      const two = P.escalateGlitch(plan, 2, GLITCH_MODES), three = P.escalateGlitch(plan, 3, GLITCH_MODES);
      assert.ok(two.secondary >= 0 && two.secondary !== two.primary && two.names.length === 2, `seed ${seed} vel ${vel}`);
      assert.equal(two.amount, plan.amount);
      assert.ok(three.amount >= plan.amount && three.amount <= 1 && three.size >= 0.85);
      assert.equal(three.primary, plan.primary, "the same strike, made bigger");
    }
  }
});

test("a clock that changes under the pads (the beat comes or goes) never sticks them", () => {
  const play = new P.PadPlay();
  press(play, 1, 10000);
  assert.equal(press(play, 1, 12).esc, 1, "a gap running backward is a fresh hit");
  const h = new P.HeroCharge();
  h.press(10000); h.due(10000);
  assert.equal(h.charge(50), 1, "a payoff on the old clock does not hold the charge");
  const h2 = new P.HeroCharge();
  h2.press(10001);
  assert.equal(h2.due(50), null);
  assert.equal(h2.pendingAt, 52, "a booking on the old clock moves to this clock's next ONE");
  const b = new P.BuildDrop();
  b.press(10000.5, 0.3); b.release(10000.6);
  const len = b.dropAt - b.start;
  assert.equal(b.tick(20), null);
  assert.ok(Math.abs(b.dropAt - b.start - len) < 1e-9 && b.start === 20, "the build keeps its length on the new clock");
});
