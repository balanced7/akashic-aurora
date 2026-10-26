// Virtual Stage v1: the cue sequencer and Daniel's phrase (arsenal/web/stage/phrases.js, the programmer's phrase layer,
// the director's plans). node --test tests/stage_phrases.test.mjs
//
// Daniel, 2026-10-25: "3 levels of light all shooting over the crowd ... top, midle then bottom pan up and down
// sequentially. or horizontal flash and pan, then vertical 1, 2, 3 then back to lasers, then a cool pattern of lights from
// the circular halo." / "i think it was once per beat. we could also do top and bottom, middle, top and bottom again".
// These run the whole logic chain (grid -> show -> phrases -> programmer -> lasers -> director) on a 60 fps virtual clock
// with no renderer, and measure the acceptance targets that live in the FrameState.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { BeatGrid, DemoBeats } from "../arsenal/web/stage/grid.js";
import { Programmer, H, HEAD_FLOATS, FlashGate } from "../arsenal/web/stage/programmer.js";
import { Show } from "../arsenal/web/stage/show.js";
import { PhraseRunner, playPhraseEvents, validatePhrases, compileRepeat, resolveMods, Deck, deepMerge, subst, cameraPlan, goLine }
  from "../arsenal/web/stage/phrases.js";
import { LaserEngine, extraHeadsFrom, SEG, SEG_FLOATS } from "../arsenal/web/stage/lasers.js";
import { Lasers3D } from "../arsenal/web/stage/lasers3d.js";
import { Director } from "../arsenal/web/stage/camera.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const THEME = { name: "source-violet", ...SCENE.themes["source-violet"] };
const FPS = 60, F = 1000 / FPS, FRAME_BEATS = 150 / 60 / FPS;     // 150 BPM: a frame is 1/24 beat

// The page's frame loop without the renderer. hooks: perFrame(ctx), and options to start a phrase by hand.
function runDemo({ frames, perFrame = () => {}, bpm = 150, demo = true, force = [] }) {
  const grid = new BeatGrid({ bpm, t0: 0 });
  const prog = new Programmer(RIG, { theme: THEME });
  const show = new Show(RIG, { demo });
  const runner = new PhraseRunner(RIG);
  runner.force = force.slice();
  const lasers = new LaserEngine({ seed: RIG.seed, clock: grid.clock(), colours: THEME.laser, heads: extraHeadsFrom(RIG.projectors) });
  const l3 = new Lasers3D(RIG.projectors, RIG.venue, { heads: lasers.heads });
  const director = new Director(RIG.cameras.shots, RIG.cameras.sequences);
  director.start("intro", 0);
  const beats = new DemoBeats({ bpm, startMs: 300 });
  let t = 0, section = "";
  const ctx = { grid, prog, show, runner, lasers, l3, director, steps: [], cuts: [] };
  for (let f = 0; f < frames; f++) {
    t += F;
    beats.tick(t, (o) => grid.beat(o, t));
    const tEval = t + grid.presentLagMs;
    const pos = grid.posAt(tEval);
    if (grid.locked) for (const ev of show.update(grid, pos)) {
      if (ev.type !== "section") continue;
      const sec = RIG.show.sections[ev.name];
      section = ev.name;
      prog.setLook(sec.look, ev.pos);
      if (sec.lasers) lasers.setLook(sec.lasers.look, sec.lasers.level ?? 1, sec.lasers.reach ?? 1);
      director.start(sec.camera, ev.pos);
      if (sec.phrase) runner.start(sec.phrase.name, ev.pos, { repeats: sec.phrase.repeats, camera: true, section: ev.name });
      else if (runner.cur && runner.cur.source === "show") runner.stopAtPos(ev.pos);
    }
    const entered = playPhraseEvents(runner.update(pos), { programmer: prog, lasers, director,
      onEnd: (e) => director.start(RIG.show.sections[section].camera, e.pos) });
    for (const e of entered) ctx.steps.push({ id: e.id, start: e.start, pos, variant: e.variant, repeat: e.repeat, mods: e.mods, frame: f });
    prog.tick(grid, tEval, 1 / FPS);
    const pose = director.update(pos);
    if (pose.cut) ctx.cuts.push({ pos, shot: pose.shot, why: director.cuts.at(-1).why, p0: director.cuts.at(-1).pos });
    const l2 = lasers.frame(tEval);
    Object.assign(ctx, { f, pos, tEval, section, l2, pose });
    perFrame(ctx);
  }
  return ctx;
}
const meanDim = (prog, g) => { let s = 0; for (let m = 0; m < g.n; m++) s += prog.heads[g.members[m] * HEAD_FLOATS + H.DIM]; return s / g.n; };
const meanCell = (prog, g) => { let s = 0; for (let m = 0; m < g.n; m++) s += prog.pixels[g.members[m] * 4 + 3]; return s / g.n; };
const DROP = 61;                                  // the demo's drop starts on beat 61 (intro 8 bars + build 8 from -3)

// ------------------------------------------------------------------------------------------------- the data --
test("the v1 phrases are valid; broken phrases are refused with sentences", () => {
  assert.deepEqual(validatePhrases(RIG), []);
  const bad = (edit) => { const s = JSON.parse(JSON.stringify(SCENE)); edit(s.phrases["halo-levels"]); return validatePhrases(expandScene(s)); };
  assert.ok(bad((p) => { p.steps[0].beats = 11; }).some((e) => e.includes("add up to")));
  assert.ok(bad((p) => { p.steps[0].lines[0].group = "halo.nope"; }).some((e) => e.includes("no group")));
  assert.ok(bad((p) => { p.steps[0].lines[0].effects = ["nope"]; }).some((e) => e.includes("no effect")));
  assert.ok(bad((p) => { p.steps[1].camera.shot = "NOPE"; }).some((e) => e.includes("no shot")));
  assert.ok(bad((p) => { p.steps[0].lines[0].values.Color = "$nope"; }).some((e) => e.includes("$nope")));
  assert.ok(bad((p) => { p.vary.deck.push("ghost"); }).some((e) => e.includes("no variant ghost")));
  assert.ok(bad((p) => { p.steps[3].lines[3].group = "lasers.Q"; }).some((e) => e.includes("no laser group")));
});

test("small tools: deepMerge, subst, per-repeat values, the deck", () => {
  assert.deepEqual(deepMerge({ a: 1, p: { from: 0, to: -360 } }, { p: { reverse: true } }), { a: 1, p: { from: 0, to: -360, reverse: true } });
  assert.deepEqual(subst({ g: "$g", v: ["$n", 2] }, { g: "halo", n: 1 }), { g: "halo", v: [1, 2] });
  const per = { c: { cycle: ["a", "b", "c"] }, d: { alternate: [1, -1] }, o: { add: 0.3, mod: 1 }, s: { seeded: [6, 12] } };
  const m = [0, 1, 2, 3].map((k) => resolveMods(per, k, 7));
  assert.deepEqual(m.map((x) => x.c), ["a", "b", "c", "a"]);
  assert.deepEqual(m.map((x) => x.d), [1, -1, 1, -1]);
  assert.ok(Math.abs(m[3].o - 0.9) < 1e-9 && Math.abs(m[4 - 1].o - 0.9) < 1e-9);
  assert.ok(m.every((x) => x.s >= 6 && x.s <= 12));
  assert.equal(resolveMods(per, 2, 7).s, m[2].s, "seeded values repeat for the same repeat");
  const deck = new Deck(["daniel", "pinch", "ascend", "rush", "depth"], { first: "daniel", seed: 3 });
  const dealt = Array.from({ length: 30 }, () => deck.next((n) => n !== "rush"));
  assert.equal(dealt[0], "daniel");
  for (let i = 1; i < dealt.length; i++) assert.notEqual(dealt[i], dealt[i - 1], "no neighbours alike");
  assert.ok(!dealt.includes("rush"), "an ineligible card is never dealt");
  // without replacement: every eligible card once per round of four
  assert.deepEqual([...dealt.slice(0, 4)].sort(), ["ascend", "daniel", "depth", "pinch"]);
});

test("compiling a repeat: base lines under every step, the variant's edits, $values filled, presets resolved", () => {
  const mods = resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 0, 1);
  const rep = compileRepeat(RIG, "halo-levels", "daniel", mods);
  assert.deepEqual(rep.steps.map((s) => s.id), ["A", "B", "C", "D", "E"]);
  assert.deepEqual(rep.steps.map((s) => s.beats), [12, 4, 4, 8, 4]);
  const A = rep.steps[0];
  const haloLine = A.lines.find((l) => l.group === "halo" && l.effects.length);
  assert.equal(haloLine.values.Color, mods.colour);
  assert.ok(haloLine.positions && haloLine.positions.length === 96, "the layers preset gives every halo head a pan and tilt");
  assert.deepEqual(haloLine.effects.map((e) => e.name), ["levels-step"]);
  assert.ok(A.lines.some((l) => l.group === "hrow" && l.positions), "the base line holds the lip row on the horizon in black");
  const las = A.lines.find((l) => l.kind === "lasers");
  assert.equal(las.laser.schedule, "levels-step");
  assert.equal(las.heads.length, 12);
  // pinch swaps the schedule; ascend reverses it; rush splits A into 8 + 4 beats
  const pinch = compileRepeat(RIG, "halo-levels", "pinch", mods).steps[0];
  assert.ok(pinch.lines.some((l) => l.effects && l.effects.some((e) => e.name === "pinch-step")));
  assert.equal(pinch.lines.find((l) => l.kind === "lasers").laser.schedule, "pinch-step");
  const asc = compileRepeat(RIG, "halo-levels", "ascend", mods).steps;
  assert.equal(asc[0].lines.find((l) => l.effects.some((e) => e.name === "levels-step")).effects[0].def.phase.reverse, true);
  assert.equal(asc[2].lines.find((l) => l.effects.some((e) => e.name === "vert-step")).effects[0].def.phase.reverse, true, "ascend runs the verticals outside in");
  // the pan's direction alternates by repeat (not by variant), and its ripple starts on the side the pan starts from
  const m1 = resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 1, 1);
  assert.equal(Math.sign(m1.hpan), -Math.sign(mods.hpan));
  assert.equal(m1.hpan_start, -m1.hpan); assert.equal(m1.hpan_reverse, true);
  const rush = compileRepeat(RIG, "halo-levels", "rush", mods).steps;
  assert.deepEqual(rush.map((s) => `${s.id}:${s.beats}`), ["A1:8", "A2:4", "B:4", "C:4", "D:8", "E:4"]);
  assert.ok(rush[1].lines.some((l) => l.effects && l.effects.some((e) => e.name === "levels-rush")));
  const depth = compileRepeat(RIG, "halo-levels", "depth", mods).steps[2];
  assert.ok(depth.lines.some((l) => l.group === "vert.depth") && depth.camera.shot === "SIDE_TRACK_PARALLEL");
});

test("the camera plan: one entry per step, D splits at beat 4, B is cut to one beat before its flash", () => {
  const rep = compileRepeat(RIG, "halo-levels", "daniel", resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 0, 1));
  const b = [0]; for (const s of rep.steps) b.push(b.at(-1) + s.beats);
  const plan = cameraPlan(rep.steps, b.map((x) => x + 100), 0);
  assert.deepEqual(plan.map((e) => [e.shot, e.p0, e.p1]), [["HALO_LOCK", 100, 111], ["WING_LAYERS", 111, 116], ["FOH_WIDE", 116, 120],
    ["CROWD_POV", 120, 124], ["WORM_RING", 124, 128], ["HALO_ORBIT", 128, 132]]);
  assert.equal(plan[1].why, "precut");
  // a split step: the rush variant's A2 carries A1's shot (the plan is built over the whole repeat)
  const rush = compileRepeat(RIG, "halo-levels", "rush", resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 0, 1));
  const rb = [0]; for (const s of rush.steps) rb.push(rb.at(-1) + s.beats);
  const rp = cameraPlan(rush.steps, rb, 0);
  assert.deepEqual(rp.slice(0, 2).map((e) => [e.shot, e.p0, e.p1]), [["HALO_LOCK", 0, 11], ["WING_LAYERS", 11, 16]]);
  // the director never shows an entry before its start
  const dir = new Director(RIG.cameras.shots, RIG.cameras.sequences);
  dir.start("drop", 0);
  dir.plan([{ shot: "HALO_ORBIT", p0: 8, p1: 12 }]);
  assert.notEqual(dir.update(4).shot, "HALO_ORBIT");
  assert.equal(dir.update(8).shot, "HALO_ORBIT");
  // rebuilt at step B, the entry keeps its p0 (the director sees the same entry: no second cut)
  const fromB = cameraPlan(rep.steps, b.map((x) => x + 100), 1);
  assert.deepEqual([fromB[0].shot, fromB[0].p0], ["WING_LAYERS", 111]);
});

test("goLine: a Go lands on the next bar line, or on the one just passed within 0.05 beat", () => {
  const g = new BeatGrid({ bpm: 150, t0: 0 }); g.barAnchor = 1;
  assert.equal(goLine(g, 2.5), 5); assert.equal(goLine(g, 5.03), 5); assert.equal(goLine(g, 5.2), 9);
});

// ------------------------------------------------------------------------------------- the demo, frame by frame --
test("target 1: the thirds fire top, middle, bottom on the beat lines (+-1 frame), one per beat, and A ends on a bar line", () => {
  const thirds = ["halo.top", "halo.mid", "halo.bot"].map((n) => RIG.groups[n]);
  const prev = [0, 0, 0];
  const onsets = [[], [], []];
  const ctx = runDemo({ frames: Math.round((DROP + 33) / FRAME_BEATS) + 30, perFrame: (c) => {
    const st = c.runner.status();
    if (!(st.state === "running" && st.step === "A")) { prev.fill(0); return; }
    // an onset: the first frame the third's dimmer is visibly up (10 %) after being dark
    thirds.forEach((g, k) => { const d = meanDim(c.prog, g); if (prev[k] < 0.1 && d >= 0.1) onsets[k].push(c.pos); prev[k] = d; });
  } });
  const A = ctx.steps.find((s) => s.id === "A");
  assert.equal(A.start, DROP, "the phrase starts on the drop's ONE");
  assert.ok(Math.abs(A.pos - A.start) <= FRAME_BEATS + 1e-9, "on its first frame");
  const all = onsets.flatMap((o, k) => o.map((p) => ({ k, p }))).sort((a, b) => a.p - b.p);
  assert.ok(all.length >= 11, `onsets: ${all.length}`);
  for (const { p } of all) assert.ok(Math.abs(p - Math.round(p)) <= FRAME_BEATS * 1.01, `an onset ${(Math.abs(p - Math.round(p)) / FRAME_BEATS).toFixed(2)} frames off its line at ${p}`);
  // the order: beat b of A lights third b mod 3 (top, middle, bottom, top, ...), bottom first when the repeat ascends
  const As = ctx.steps.filter((s) => s.id === "A");
  assert.ok(As.length >= 2, "two repeats");
  for (const { k, p } of all) {
    const a = [...As].reverse().find((s) => s.start <= p + 1e-6);
    const b = Math.round(p) - a.start;
    const want = a.variant === "ascend" ? 2 - (b % 3) : b % 3;
    if (a.variant === "pinch") continue;
    assert.equal(k, want, `repeat ${a.repeat} (${a.variant}) beat ${b} lit third ${k}`);
  }
  const B = ctx.steps.find((s) => s.id === "B");
  assert.equal(B.start - A.start, 12);
  assert.equal(((B.start - ctx.grid.barAnchor) % 4 + 4) % 4, 0, "A ends on a bar line");
});

test("target 1 (ascend) and Daniel's second pattern (pinch): bottom first when ascending; top+bottom, middle, top+bottom", () => {
  for (const variant of ["ascend", "pinch"]) {
    const grid = new BeatGrid({ bpm: 150, t0: 0 });
    grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
    const prog = new Programmer(RIG, { theme: THEME });
    prog.setLook("drop", 0);
    const rep = compileRepeat(RIG, "halo-levels", variant, resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 0, 1));
    prog.setOverlay(rep.steps[0].lines, 0);
    const thirds = ["halo.top", "halo.mid", "halo.bot"].map((n) => RIG.groups[n]);
    const lit = [];
    for (let f = 0; f <= 24 * 6; f++) {
      const t = f * F;
      prog.tick(grid, t, 1 / FPS);
      if (f % 24 === 12) lit.push(thirds.map((g) => (meanDim(prog, g) > 0.5 ? 1 : 0)).join(""));
    }
    if (variant === "ascend") assert.deepEqual(lit, ["001", "010", "100", "001", "010", "100"]);
    else assert.deepEqual(lit, ["101", "010", "101", "010", "101", "010"]);
  }
});

test("targets 6 and 7: one FlashGate grant on B's ONE, the pan sweeps -40 to +40 in 2 beats at dimmer >= 0.6; verticals 1-2-3 on beats 1, 2, 3, dark on beat 4", () => {
  const hrow = RIG.groups.hrow;
  const cols = [0, 1, 2].map((c) => Array.from({ length: RIG.groups.vert.n }, (_, m) => m).filter((m) => RIG.groups.vert.keys.column[m] === c));
  const vert = RIG.groups.vert;
  const rec = { pan: [], dimB: [], vert: [] };
  const ctx = runDemo({ frames: Math.round((DROP + 64 + 1) / FRAME_BEATS), perFrame: (c) => {
    const st = c.runner.status();
    if (st.state !== "running") return;
    const age = c.pos - st.start;
    if (st.step === "B") {
      rec.pan.push({ rep: st.repeat, age, pan: c.prog.heads[hrow.members[0] * HEAD_FLOATS + H.PAN] });
      if (age > 0.75) rec.dimB.push(meanDim(c.prog, hrow));
    }
    if (st.step === "C") rec.vert.push({ rep: st.repeat, variant: st.variant, age, cols: cols.map((ms) => ms.reduce((s, m) => s + c.prog.heads[vert.members[m] * HEAD_FLOATS + H.DIM], 0) / ms.length) });
  } });
  const Bs = ctx.steps.filter((s) => s.id === "B").map((s) => s.start);
  assert.deepEqual(ctx.prog.flashGate.grants, Bs, "exactly one grant per B, on its ONE");
  assert.deepEqual(ctx.prog.flashGate.refusals, []);
  assert.ok(Math.min(...rec.dimB) >= 0.6 - 1e-6, `the row holds >= 0.6 after the flash (min ${Math.min(...rec.dimB)})`);
  for (const r of [0, 1]) {
    const s = rec.pan.filter((x) => x.rep === r);
    const sign = Math.sign(s.at(-1).pan - s[0].pan);
    const leave = s.find((x) => sign * (x.pan - s[0].pan) > 1), arrive = s.find((x) => sign * (s.at(-1).pan - x.pan) < 1);
    const sweep = arrive.age - leave.age;
    assert.ok(Math.abs(sweep - 2) <= 0.1 + 2 * FRAME_BEATS, `repeat ${r}: the sweep takes ${sweep.toFixed(3)} beats`);
    assert.ok(Math.abs(s[0].pan - s.at(-1).pan) >= 79, `repeat ${r}: it covers ${Math.abs(s[0].pan - s.at(-1).pan).toFixed(1)} degrees`);
  }
  const dir = [0, 1].map((r) => { const s = rec.pan.filter((x) => x.rep === r); return Math.sign(s.at(-1).pan - s[0].pan); });
  assert.notEqual(dir[0], dir[1], "the pan direction alternates on repeats");
  for (const r of [0, 1]) {
    const v = rec.vert.filter((x) => x.rep === r);
    if (v[0].variant === "depth") continue;
    const ascend = v[0].variant === "ascend";
    for (let beat = 0; beat < 3; beat++) {
      const mid = v.find((x) => x.age >= beat + 0.5);
      const want = ascend ? 2 - beat : beat;
      assert.ok(mid.cols[want] > 0.9 && mid.cols.every((c, k) => k === want || c < 0.05), `repeat ${r} beat ${beat + 1}: ${mid.cols.map((c) => c.toFixed(2))}`);
      const on = v.find((x) => x.cols[want] >= 0.1);      // visibly up (10 %), as for the thirds
      assert.ok(Math.abs(on.age - (ascend ? 2 - want : want)) <= FRAME_BEATS * 1.01 + 1e-9, `column ${want} onset ${on.age.toFixed(3)} beats into C`);
    }
    const b4 = v.filter((x) => x.age >= 3.1);
    assert.ok(b4.every((x) => x.cols.reduce((a, b) => a + b, 0) / 3 <= 0.02), "beat 4 is dark (the hand-off)");
  }
});

test("target 8: the lasers enter on D's ONE (+-1 frame); during D the heads are dark and the LEDs at 10 % or less", () => {
  const halo = RIG.groups.halo, leds = RIG.groups["leds.all"], heads = RIG.groups["heads.all"];
  const rec = [];
  let firstLaser = null;
  runDemo({ frames: Math.round((DROP + 32 + 1) / FRAME_BEATS), perFrame: (c) => {
    const st = c.runner.status();
    if (st.state !== "running") return;
    if (st.step === "D") {
      if (firstLaser === null && c.l2.groups > 0) firstLaser = c.pos - st.start;
      if (c.pos - st.start > 0.25) rec.push({ halo: meanDim(c.prog, halo), heads: meanDim(c.prog, heads), led: Math.max(...Array.from(leds.members, (k) => c.prog.pixels[k * 4 + 3])) });
    }
    if (st.step === "C" && c.pos - st.start > 3.5) assert.equal(c.l2.groups, 0, "no phrase lasers before D");
  } });
  assert.ok(firstLaser !== null && Math.abs(firstLaser) <= FRAME_BEATS + 1e-9, `the first laser frame is ${firstLaser} beats from D's ONE`);
  assert.ok(rec.every((r) => r.halo <= 1e-6), `the halo heads are at 0 (max ${Math.max(...rec.map((r) => r.halo))})`);
  assert.ok(Math.max(...rec.map((r) => r.heads)) <= 0.12, `the heads are dark (KICK lifts the strand heads only): ${Math.max(...rec.map((r) => r.heads)).toFixed(3)}`);
  assert.ok(Math.max(...rec.map((r) => r.led)) <= 0.1 + 1e-9, `the LEDs are at 10 % or less: ${Math.max(...rec.map((r) => r.led))}`);
});

test("target 9: never static over 6 repeats: neighbours differ in variant, colour role and chopper direction; chopper starts 30+ degrees apart", () => {
  const runner = new PhraseRunner(RIG);
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  runner.start("halo-levels", 0, { repeats: 6, section: "drop" });
  const reps = [];
  for (let pos = 0; pos <= 6 * 32; pos += 0.5) for (const e of runner.update(pos)) if (e.type === "repeat") reps.push(e);
  assert.equal(reps.length, 6);
  for (let i = 1; i < 6; i++) {
    assert.notEqual(reps[i].variant, reps[i - 1].variant, `repeats ${i - 1}/${i} variant`);
    assert.notEqual(reps[i].mods.colour, reps[i - 1].mods.colour, `repeats ${i - 1}/${i} colour`);
    assert.notEqual(Math.sign(reps[i].mods.chop_to), Math.sign(reps[i - 1].mods.chop_to), `repeats ${i - 1}/${i} chopper direction`);
    // the chopper's start angle: offset x 180 degrees (two blades: a phase cycle is half a turn)
    let d = Math.abs(reps[i].mods.chop_offset - reps[i - 1].mods.chop_offset) * 180 % 180;
    d = Math.min(d, 180 - d);
    assert.ok(d >= 30, `chopper starts ${d.toFixed(1)} degrees apart`);
    assert.notEqual(reps[i].mods.halo_group, reps[i - 1].mods.halo_group);
  }
  assert.equal(reps[0].variant, "daniel", "the first repeat is Daniel's own");
  assert.ok(!reps.some((r) => r.variant === "rush"), "rush is for builds and breaks: not dealt in the drop");
  // in a build, rush can be dealt
  const r2 = new PhraseRunner(RIG);
  r2.start("halo-levels", 0, { repeats: 12, section: "build" });
  const seen = new Set();
  for (let pos = 0; pos <= 12 * 32; pos += 0.5) for (const e of r2.update(pos)) if (e.type === "repeat") seen.add(e.variant);
  assert.ok(seen.has("rush"));
});

test("the runner: Go arms on the next bar line, Next cuts a step to the next bar line, Stop ends on the next bar line", () => {
  const grid = new BeatGrid({ bpm: 150, t0: 0 }); grid.barAnchor = 0;
  const r = new PhraseRunner(RIG);
  r.go("halo-levels", grid, 1.3, { section: "groove" });
  assert.equal(r.state, "armed");
  let ev = r.update(3.9); assert.equal(ev.length, 0);
  ev = r.update(4.0);
  assert.deepEqual(ev.map((e) => e.type), ["start", "repeat", "step"]);
  assert.equal(ev[2].start, 4);
  r.next(grid, 5.5);                         // A (12 beats) is cut to the next bar line: beat 8
  ev = r.update(6);
  assert.equal(ev[0].type, "camera", "the camera plan follows the cut");
  ev = r.update(8);
  assert.equal(ev.find((e) => e.type === "step").id, "B");
  assert.equal(ev.find((e) => e.type === "step").start, 8);
  r.stop(grid, 9.1);
  ev = r.update(11.99); assert.ok(!ev.some((e) => e.type === "end"));
  ev = r.update(12); assert.deepEqual(ev.map((e) => e.type), ["end"]); assert.equal(ev[0].pos, 12);
  assert.equal(r.state, "idle");
  // a start may name its first repeat's variant (the deck deals the rest)
  const rv = new PhraseRunner(RIG);
  rv.start("halo-levels", 0, { repeats: 2, section: "build", variant: "rush" });
  const vs = [];
  for (let p = 0; p <= 64; p += 0.5) for (const e of rv.update(p)) if (e.type === "repeat") vs.push(e.variant);
  assert.equal(vs[0], "rush"); assert.notEqual(vs[1], "rush");
  const r3 = new PhraseRunner(RIG); r3.start("halo-levels", 0, { variant: "nope" });
  const ev3 = r3.update(0); assert.equal(ev3[0].type, "error"); assert.match(ev3[0].message, /no variant nope/); assert.equal(r3.state, "idle");
  // cues fire at their beat inside the step: E's move-in-black at beat 3
  const r2 = new PhraseRunner(RIG);
  r2.start("halo-levels", 0, { repeats: 1 });
  const cues = [];
  for (let p = 0; p <= 33; p += 0.25) for (const e of r2.update(p)) if (e.type === "cue") cues.push(e.pos);
  assert.deepEqual(cues, [31]);
});

test("a phrase that cannot compile leaves the runner idle with an error event; a preset's own $ values default to 0", () => {
  const rig = expandScene(SCENE);
  rig.phrases.bad = { name: "bad", steps: [{ id: "X", beats: 4, lines: [{ group: "halo", values: { Color: "$nope" } }] }] };
  rig.phrases.solo = { name: "solo", steps: [{ id: "L", beats: 4, lines: [{ group: "halo", preset: "layers", values: { Dimmer: 0 } }] }] };
  const r = new PhraseRunner(rig);
  r.start("bad", 4);
  const ev = r.update(4);
  assert.deepEqual(ev.map((e) => e.type), ["error"]);
  assert.match(ev[0].message, /\$nope/);
  assert.equal(r.state, "idle"); assert.equal(r.cur, null);
  r.start("solo", 8);
  assert.deepEqual(r.update(8).map((e) => e.type), ["start", "repeat", "step"], "the layers preset compiles without a per-repeat layer_shift");
});

test("the programmer's phrase layer: LTP over the look, dimmers crossfade over a line's fade, clearOverlay hands back to the look", () => {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const prog = new Programmer(RIG, { theme: THEME });
  prog.setLook("groove", 0, { fade: 0 });
  for (let f = 0; f < 30; f++) prog.tick(grid, f * F, 1 / FPS);
  const lip = RIG.groups["lip.heads"], strand = RIG.groups["strand.heads"];
  const before = meanDim(prog, strand);
  assert.ok(meanDim(prog, lip) > 0.3, "the groove look lights the lip");
  const line = { g: lip, kind: "heads", values: { Dimmer: 0 }, positions: null, effects: [], fade: 1, flash: null };
  prog.setOverlay([line], grid.posAt(30 * F));
  const p0 = grid.posAt(30 * F);
  let half = null;
  for (let f = 30; f < 120; f++) { prog.tick(grid, f * F, 1 / FPS); if (half === null && grid.posAt(f * F) - p0 >= 0.5) half = meanDim(prog, lip); }
  assert.ok(half > 0.1 && half < 0.6, `half-way through the fade: ${half}`);
  assert.ok(meanDim(prog, lip) < 0.01, "the overlay owns the lip");
  assert.ok(Math.abs(meanDim(prog, strand) - before) < 0.2, "the strand stays the look's");
  prog.clearOverlay(grid.posAt(120 * F), 0);
  for (let f = 120; f < 160; f++) prog.tick(grid, f * F, 1 / FPS);
  assert.ok(meanDim(prog, lip) > 0.3, "handed back to the look");
});

test("FLY-OUT bursts the truss and lip only: never the halo or the verticals a phrase is placing", () => {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const prog = new Programmer(RIG, { theme: THEME });
  prog.setLook("break", 0, { fade: 0 });
  for (let f = 0; f < 30; f++) prog.tick(grid, f * F, 1 / FPS);
  prog.pad("flyout", 1, grid.posAt(30 * F));
  let haloMax = 0, vertMax = 0, trussMax = 0;
  for (let f = 30; f < 60; f++) {
    prog.tick(grid, f * F, 1 / FPS);
    haloMax = Math.max(haloMax, meanDim(prog, RIG.groups.halo)); vertMax = Math.max(vertMax, meanDim(prog, RIG.groups.vert));
    trussMax = Math.max(trussMax, meanDim(prog, RIG.groups["truss.heads"]));
  }
  assert.ok(trussMax > 0.5, `the truss bursts (${trussMax.toFixed(2)})`);
  assert.equal(haloMax, 0); assert.equal(vertMax, 0);
});

test("the pre-roll: a bar before the drop the dark halo heads move in black to the layers; nothing lit moves, no dimmer changes", () => {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const prog = new Programmer(RIG, { theme: THEME });
  prog.setLook("build", 0, { fade: 0 });
  for (let f = 0; f < 10; f++) prog.tick(grid, f * F, 1 / FPS);
  const runner = new PhraseRunner(RIG);
  const lines = runner.prepareLines("halo-levels");
  const lipBefore = Array.from(RIG.groups["lip.heads"].members, (k) => prog.tH[k * 7]);
  const dimBefore = meanDim(prog, RIG.groups.hrow);
  prog.setOverlay(lines, grid.posAt(10 * F), { positionsOnly: true });
  for (let f = 10; f < 130; f++) prog.tick(grid, f * F, 1 / FPS);
  const halo = RIG.groups.halo, want = lines.find((l) => l.group === "halo" && l.positions).positions;
  for (let m = 0; m < halo.n; m += 7) {
    const k = halo.members[m];
    assert.ok(Math.abs(prog.heads[k * HEAD_FLOATS + H.TILT] - want[m * 2 + 1]) < 0.5, `halo head ${m} reached its layer tilt`);
  }
  assert.equal(meanDim(prog, halo), 0, "and stayed dark");
  // the lip is lit by the build: it keeps the look's position and dimmer
  assert.deepEqual(Array.from(RIG.groups["lip.heads"].members, (k) => prog.tH[k * 7]), lipBefore);
  assert.ok(Math.abs(meanDim(prog, RIG.groups.hrow) - dimBefore) < 0.35);
  // the demo's show says "prepare" one bar before the drop
  const show = new Show(RIG, { demo: true });
  const g2 = new BeatGrid({ bpm: 150, t0: 0 });
  g2.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const preps = [];
  for (let p = 0; p < 70; p += 0.25) for (const e of show.update(g2, p)) if (e.type === "prepare") preps.push(e);
  assert.equal(preps.length, 1);
  assert.equal(preps[0].section, "drop");
  assert.equal(preps[0].pos, show.planStart + 4 * 16, "the drop's ONE (intro 8 bars + build 8)");
});

test("the FlashGate: one grant per bar; a refused flash is a lift over an eighth of a beat", () => {
  const gate = new FlashGate();
  assert.equal(gate.request(0), true); assert.equal(gate.request(2), false); assert.equal(gate.request(4), true);
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const prog = new Programmer(RIG, { theme: THEME });
  prog.setLook("groove", 0, { fade: 0 });
  const hrow = RIG.groups.hrow;
  const line = (at) => ({ g: hrow, kind: "heads", values: { Dimmer: 0.6 }, positions: null, effects: [], fade: 0, flash: { at, to: 1, decay_beats: 0.5 } });
  prog.flashGate.request(-2);                 // a grant two beats ago: the next flash is refused
  prog.setOverlay([line(0)], 0);
  const lv = [];
  for (let f = 0; f <= 12; f++) { prog.tick(grid, f * F, 1 / FPS); lv.push(prog.tH[hrow.members[0] * 7 + 2]); }
  assert.equal(prog.flashGate.refusals.length, 1);
  assert.ok(lv[0] < 0.65 && lv[1] > lv[0] && lv[3] >= 0.95, `a lift: ${lv.slice(0, 5).map((x) => x.toFixed(2))}`);
});
