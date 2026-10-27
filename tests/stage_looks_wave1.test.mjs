// Virtual Stage, looks wave 1: the looks that need no new rig axes, as phrases in sets/source-v1.json, and the stage
// themes that go with them. node --test tests/stage_looks_wave1.test.mjs
//
// The VJ V2 build spec, section F: "the wave-1 looks as phrase/preset data where no new rig axes are needed". The looks
// lane (research/reviewed/keylab-liberation-2026-10-22/vj-v2-research-2026-10-27/looks.research.md) names them; these
// five map onto today's groups, effects and laser shapes: L02 Single Thread, L04 (Twin) Pillars, L13 Drumroll Iris, L24
// Scissor Gates, L26 Tunnel Spokes. They are reached by ?phrase=<name> (pad 3 starts it); Daniel's halo-levels stays the
// set's first phrase, so pad 3 without the parameter is unchanged. Stage themes: ?theme=dreaming-city and three more.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { BeatGrid, DemoBeats } from "../arsenal/web/stage/grid.js";
import { Programmer, resolveTheme } from "../arsenal/web/stage/programmer.js";
import { PhraseRunner, playPhraseEvents, validatePhrases, compileRepeat, resolveMods, resolvePreset } from "../arsenal/web/stage/phrases.js";
import { LaserEngine, extraHeadsFrom, GROUP_SHAPES, groupGate, hexToLinear, isSaturatedRed } from "../arsenal/web/stage/lasers.js";
import { Director } from "../arsenal/web/stage/camera.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const VJ = JSON.parse(readFileSync(new URL("../arsenal/web/vj-themes.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const WAVE1 = ["single-thread", "pillars", "scissor-gates", "tunnel-spokes", "drumroll-iris"];
const STAGE_THEMES = ["dreaming-city", "genesis-indigo", "vex-conflux", "anti-sun"];
const FPS = 60, F = 1000 / FPS;

const mods = (name, k) => resolveMods(SCENE.phrases[name].vary.per_repeat, k, 1);
const line = (step, group) => step.lines.filter((l) => l.group === group).at(-1);
const meanCell = (prog, g) => { let s = 0; for (let m = 0; m < g.n; m++) s += prog.pixels[g.members[m] * 4 + 3]; return s / g.n; };

// One phrase played by hand from the first bar line after the grid locks, through the page's chain without a renderer:
// grid -> phrases -> programmer -> lasers -> director. perFrame(ctx) sees each frame; returns what it recorded.
function play(name, { repeats = 1, theme = "source-violet", perFrame = () => {} } = {}) {
  const ph = SCENE.phrases[name];
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  const th = { name: theme, ...SCENE.themes[theme] };
  const prog = new Programmer(RIG, { theme: th });
  const runner = new PhraseRunner(RIG);
  const lasers = new LaserEngine({ seed: RIG.seed, clock: grid.clock(), colours: th.laser, heads: extraHeadsFrom(RIG.projectors) });
  const director = new Director(RIG.cameras.shots, RIG.cameras.sequences);
  director.start("intro", 0);
  const beats = new DemoBeats({ bpm: 150, startMs: 300 });
  const ctx = { prog, lasers, runner, start: null, errors: [], laserFrames: 0, steps: [] };
  const frames = Math.ceil(((repeats * ph.bars * 4 + 12) * 400) / F);
  for (let f = 0, t = 0; f < frames; f++) {
    t += F;
    beats.tick(t, (o) => grid.beat(o, t));
    const tEval = t + grid.presentLagMs;
    const pos = grid.posAt(tEval);
    if (ctx.start === null && grid.locked) {
      ctx.start = Math.ceil(pos / 4) * 4;
      runner.start(name, ctx.start, { repeats, section: ph.sections[0], source: "pad" });
    }
    const ev = runner.update(pos);
    for (const e of ev) if (e.type === "error") ctx.errors.push(e.message);
    for (const e of playPhraseEvents(ev, { programmer: prog, lasers, director })) ctx.steps.push({ id: e.id, start: e.start });
    prog.tick(grid, tEval, 1 / FPS);
    director.update(pos);
    const l2 = lasers.frame(tEval);
    if (l2 && l2.groups > 0) ctx.laserFrames++;
    Object.assign(ctx, { pos, l2 });
    if (ctx.start !== null) perFrame(ctx);
  }
  return ctx;
}

// ----------------------------------------------------------------------------------------------------- the data --
test("the wave-1 phrases are valid and sit after Daniel's halo-levels, so pad 3 still starts his unless ?phrase= names one", () => {
  assert.deepEqual(validatePhrases(RIG), []);
  const names = Object.keys(SCENE.phrases);
  assert.equal(names[0], "halo-levels");
  assert.deepEqual(names.slice(1), WAVE1);
  for (const n of WAVE1) {
    const ph = SCENE.phrases[n];
    assert.match(ph.about, /Looks wave 1, L\d\d/, `${n} names its look`);
    assert.match(ph.about, new RegExp(`\\?phrase=${n}`), `${n} says how to reach it`);
    assert.equal(ph.steps.reduce((s, st) => s + st.beats, 0), ph.bars * 4, n);
  }
  // the page's door: the phrase and theme parameters are read as names, and only a name the set has is used
  const page = readFileSync(new URL("../arsenal/web/stage/stage.js", import.meta.url), "utf8");
  assert.match(page, /PHRASE_ASKED && rig\.phrases\[PHRASE_ASKED\] \? PHRASE_ASKED : Object\.keys\(rig\.phrases\)\[0\]/);
  assert.match(page, /THEME_ASKED && rig\.themes\[THEME_ASKED\] \? THEME_ASKED : show0\.theme/);
});

test("every variant of every wave-1 phrase compiles over four repeats, with legal laser shapes and gates", () => {
  let lines = 0;
  for (const n of WAVE1) {
    const v = SCENE.phrases[n].vary;
    for (const variant of v.deck) for (let k = 0; k < 4; k++) {
      const rep = compileRepeat(RIG, n, variant, mods(n, k));
      for (const st of rep.steps) for (const l of [...st.lines, ...st.cues.flatMap((c) => c.lines)]) {
        lines++;
        if (l.kind !== "lasers") continue;
        assert.ok(GROUP_SHAPES.includes(l.laser.shape), `${n}/${variant} ${l.group}: ${l.laser.shape}`);
        assert.doesNotThrow(() => groupGate(l.laser.gate, 0));
        assert.ok(l.laser.level > 0 && l.laser.level <= 1, `${n} ${l.group} level`);
        assert.ok([0, 1, 2].includes(l.laser.colour), `${n} ${l.group} colour ${l.laser.colour}`);
      }
    }
  }
  assert.ok(lines > 200);
});

test("never static: six repeats of each, neighbours differ in variant and in their per-repeat values", () => {
  for (const n of WAVE1) {
    const runner = new PhraseRunner(RIG);
    runner.start(n, 0, { repeats: 6, section: SCENE.phrases[n].sections[0] });
    const reps = [];
    for (let pos = 0; pos <= 6 * SCENE.phrases[n].bars * 4; pos += 0.5) for (const e of runner.update(pos)) if (e.type === "repeat") reps.push(e);
    assert.equal(reps.length, 6, n);
    for (let i = 1; i < 6; i++) {
      assert.notEqual(reps[i].variant, reps[i - 1].variant, `${n} repeats ${i - 1}/${i} variant`);
      assert.notDeepEqual(reps[i].mods, reps[i - 1].mods, `${n} repeats ${i - 1}/${i} per-repeat values`);
    }
  }
});

test("the darkness budget: every wave-1 step dims the room, and the laser looks keep the moving heads dark", () => {
  for (const n of WAVE1) for (const st of SCENE.phrases[n].steps) assert.ok(st.ambient <= 0.4, `${n} ${st.id} ambient ${st.ambient}`);
  for (const n of ["single-thread", "scissor-gates", "tunnel-spokes"]) {
    const base = SCENE.phrases[n].base.find((l) => l.group === "heads.all");
    assert.equal(base.values.Dimmer, 0, `${n}: heads.all at 0 under every step`);
  }
});

// ------------------------------------------------------------------------------------------------ each look --
test("Single Thread: one beam from the hero, the room at 0.1, still or a drift of 2 degrees over 8 bars", () => {
  for (let k = 0; k < 2; k++) {
    const st = compileRepeat(RIG, "single-thread", "front", mods("single-thread", k)).steps[0];
    const lasers = st.lines.filter((l) => l.kind === "lasers");
    assert.equal(lasers.length, 1);
    assert.equal(lasers[0].group, "lasers.hero");
    assert.equal(lasers[0].heads.length, 1);
    assert.equal(lasers[0].laser.beams, 1);
    assert.ok(lasers[0].laser.swing <= 2 && lasers[0].laser.measure === 32);
    assert.equal(st.ambient, 0.1);
  }
  const c = play("single-thread", { perFrame: (x) => { if (x.l2) x.maxSegs = Math.max(x.maxSegs || 0, x.l2.groups || 0); } });
  assert.deepEqual(c.errors, []);
  assert.ok(c.laserFrames > 0, "the thread is drawn");
});

test("Pillars: the delay towers' square clusters straight up, two columns 24 m apart, held still", () => {
  const g = RIG.groups["delay.30"];
  assert.equal(g.n, 8);
  const xs = [...new Set(Array.from({ length: g.n }, (_, m) => Math.round(g.keys.x[m] / 6) * 6))].sort((a, b) => a - b);
  assert.deepEqual(xs, [-12, 12], "two clusters, 24 m apart");
  const rep = compileRepeat(RIG, "pillars", "front", mods("pillars", 0));
  const B = rep.steps.find((s) => s.id === "B");
  for (const grp of ["delay.30", "vert.towers"]) {
    const l = line(B, grp);
    assert.equal(l.preset, "vertical", grp);
    assert.equal(l.effects.length, 0, `${grp}: nothing moves a monument`);
    for (let m = 0; m < l.g.n; m++) assert.equal(l.positions[m * 2 + 1], 0, `${grp} member ${m} tilts 0 (straight up)`);
  }
  const C = rep.steps.find((s) => s.id === "C");
  assert.equal(C.beats, 4);
  assert.deepEqual(["delay.30", "vert.towers"].map((grp) => [line(C, grp).values.Dimmer, line(C, grp).fade]), [[0, 2], [0, 2]], "released with a 2-beat fade");
  assert.deepEqual(play("pillars").errors, []);
});

test("Drumroll Iris: the chop's period halves every 2 bars as its arc narrows, one way per repeat, and the last beat is black", () => {
  const chop = (st) => line(st, "rings.slats").effects.find((e) => e.name === "ring-chopper").def;
  for (let k = 0; k < 2; k++) {
    const rep = compileRepeat(RIG, "drumroll-iris", "rings", mods("drumroll-iris", k));
    assert.deepEqual(rep.steps.map((s) => s.beats), [8, 8, 8, 8]);
    assert.deepEqual(rep.steps.map((s) => chop(s).measure), [4, 2, 1, 0.5], "a bar, half a bar, a beat, half a beat");
    const w = rep.steps.map((s) => chop(s).width);
    assert.ok(w.every((x, i) => i === 0 || x < w[i - 1]), `the arc narrows: ${w}`);
    assert.equal(Math.sign(chop(rep.steps[0]).phase.to), k % 2 ? 1 : -1, "one direction per repeat, alternating");
    const cue = rep.steps[3].cues[0];
    assert.equal(cue.at, 7);
    assert.deepEqual(cue.lines.map((l) => [l.group, l.values.Dimmer]), [["rings.slats", 0], ["rings.rims", 0]]);
  }
  // played: lit while it rolls, black in its last beat
  const slats = RIG.groups["rings.slats"];
  const lit = [], last = [];
  const c = play("drumroll-iris", { perFrame: (x) => {
    const b = x.pos - x.start;
    if (b > 1 && b < 7) lit.push(meanCell(x.prog, slats));
    if (b > 31.1 && b < 31.9) last.push(meanCell(x.prog, slats));
  } });
  assert.deepEqual(c.errors, []);
  assert.ok(Math.max(...lit) > 0.2, `the rings roll lit (${Math.max(...lit).toFixed(3)})`);
  assert.ok(last.length > 10 && Math.max(...last) <= 0.01, `the last beat is black (${Math.max(...last)})`);
});

test("Tunnel Spokes: one turning direction per repeat, changed only through the black beat that ends it", () => {
  const spin = (st) => line(st, "rings.slats").effects[0].def.phase.to;
  const signs = [];
  for (let k = 0; k < 4; k++) {
    const rep = compileRepeat(RIG, "tunnel-spokes", k % 2 ? "halo" : "hero", mods("tunnel-spokes", k));
    const [A, B, C] = rep.steps;
    assert.equal(Math.sign(spin(A)), Math.sign(spin(B)), "A and B turn the same way");
    signs.push(Math.sign(spin(A)));
    assert.equal(C.beats, 1);
    assert.equal(C, rep.steps.at(-1), "the black beat closes the repeat");
    assert.equal(C.lines.filter((l) => l.kind === "lasers").length, 0, "no lasers in the black beat");
    for (const grp of ["rings.slats", "rings.rims", "strand.heads"]) assert.equal(line(C, grp).values.Dimmer, 0, grp);
  }
  assert.deepEqual(signs, [-1, 1, -1, 1]);
  const c = play("tunnel-spokes");
  assert.deepEqual(c.errors, []);
  assert.ok(c.laserFrames > 0);
});

test("Scissor Gates: the X swaps its two colours between the towers and the bank, then opens into fans", () => {
  for (let k = 0; k < 3; k++) {
    const rep = compileRepeat(RIG, "scissor-gates", "towers", mods("scissor-gates", k));
    const [A, B] = rep.steps;
    const towers = line(A, "lasers.towers").laser, bank = line(A, "lasers.A").laser;
    assert.equal(towers.shape, "scissors");
    assert.deepEqual([towers.colour, towers.colour2], [bank.colour2, bank.colour], "the pair crosses sides");
    assert.notEqual(towers.colour, towers.colour2);
    assert.equal(line(B, "lasers.AS").laser.shape, "fans");
  }
  const floor = compileRepeat(RIG, "scissor-gates", "floor", mods("scissor-gates", 1)).steps[0];
  assert.ok(line(floor, "lasers.B") && !line(floor, "lasers.A"), "the floor variant crosses with Bank B");
  const c = play("scissor-gates", { repeats: 2 });
  assert.deepEqual(c.errors, []);
  assert.ok(c.laserFrames > 0);
});

// ------------------------------------------------------------------------------------------------- the themes --
test("the stage's wave-1 themes: no saturated red in any role or laser colour, and Dreaming City is the VJ library's", () => {
  for (const id of STAGE_THEMES) {
    const t = SCENE.themes[id];
    assert.ok(t && t.name, id);
    assert.doesNotThrow(() => resolveTheme({ name: id, ...t }), id);
    assert.equal(t.laser.length, 3);
    for (const hex of t.laser) assert.ok(!isSaturatedRed(hexToLinear(hex)), `${id} laser ${hex}`);
    assert.match(t.about, new RegExp(`\\?theme=${id}`));
  }
  const vj = VJ.themes.find((t) => t.id === "dreaming-city"), st = SCENE.themes["dreaming-city"];
  assert.deepEqual([st.A, st.B, st.W, st.warm], [vj.A, vj.B, vj.W, vj.line], "core, haze, glyph lines, window amber");
  assert.deepEqual(st.laser.slice(0, 2), [vj.beam.W, vj.beam.A], "the lasers draw the glyph lines, then the core's violet");
  // each wave-1 phrase plays under Dreaming City as well as under the show's own theme
  for (const n of WAVE1) assert.deepEqual(play(n, { theme: "dreaming-city" }).errors, [], n);
});
