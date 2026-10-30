// Virtual Stage, SETUPS: a palette x a placement, rotating on the 16-bar lines (arsenal/web/stage/setups.js,
// sets/setups.json, programmer.js "THE SETUP LAYER", stage.js). node --test tests/stage_setups.test.mjs
//
// Daniel, 2026-10-29, with a screenshot of the drop: "also amber is perhaps a touch overrepresented ... in the screenshot the
// middle row being white with the other lights being blue and lasers flashing green or purple or pink, can you think of a
// few cool color palates using the screenshot as a reference for placement and ideas, we could also leverage gradients on
// the led cubes" ... "not permantly only orange and gold, i want the lights to cycle different color palates and setups".
//
// What these pin: every setup in the library is valid and places every group; no red anywhere (every colour, every
// crossfade sample, every rendered member at every bank); amber only in the setups about it, and never the first; every
// crossfade between two setups (and from and back to every palette's own colours) has a clean path; kick 5's bank turns
// every non-pinned group on every press and a pinned group never (in the tables and in the programmer's own output); the
// centre row stays white; the sides split; the white kick stays white; the lasers and the HAL cubes follow the setup; the
// rotation lands on the 16-bar lines and O on the next bar line. The screen's receipt is stage_verify --phases setups.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { Programmer, H, HEAD_FLOATS, ROLE_NAMES, BANK_GROUPS, resolveTheme, nearestSlot } from "../arsenal/web/stage/programmer.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import * as PAL from "../arsenal/web/palettes.js";
import * as SU from "../arsenal/web/stage/setups.js";

const RAW = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/setups.json", import.meta.url), "utf8"));
const PRAW = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const WHEEL_HEX = SCENE.types["beam-7r"].attrs.Color1.colours;
const PLIB = PAL.loadPalettes(PRAW, { wheel: WHEEL_HEX });
const LIB = SU.loadSetups(RAW);
const FPS = 60, DT = 1 / FPS;
const locked = (bpm = 150) => { const g = new BeatGrid({ bpm, t0: 0 }); g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0); return g; };
const rolesOf = (id) => { const t = resolveTheme(PAL.stageTheme(PLIB.byId[id])); return ROLE_NAMES.map((r) => t[r]); };
function play(p, g, a, b) { for (let t = a * g.period; t < b * g.period; t += 1000 / FPS) p.tick(g, t, DT); }
const fresh = (pal = "source-violet", look = "drop") => { const p = new Programmer(RIG, { theme: PAL.stageTheme(PLIB.byId[pal]), seed: 7 }); p.setLook(look, 0); return p; };
const SIX = ["ice-spine", "gold-sapphire", "ember-cathedral", "neon-split", "aurora-column", "black-and-one"];
// a group's lit LEDs' mean colour (level-weighted) and its lit heads' wheel slots, as the programmer outputs them
function groupState(p, name) {
  const gi = p.bankG.names.indexOf(name), m = [0, 0, 0, 0], slots = [];
  for (let c = 0; c < p.nC; c++) { if (p.bankG.cellG[c] !== gi) continue; const l = p.pixels[c * 4 + 3]; if (l < 0.05) continue; m[0] += p.pixels[c * 4]; m[1] += p.pixels[c * 4 + 1]; m[2] += p.pixels[c * 4 + 2]; m[3] += l; }
  for (let i = 0; i < p.nH; i++) if (p.bankG.headG[i] === gi && p.heads[i * HEAD_FLOATS + H.DIM] > 0.02) slots.push(Math.round(p.wheelPos[i]) % 14);
  return { cells: m[3] > 0 ? [m[0] / m[3], m[1] / m[3], m[2] / m[3]] : null, slots };
}

test("the library: every setup loads (none refused), at least eight, Daniel's six among them, the groups are the bank's", () => {
  assert.deepEqual(LIB.refused, [], JSON.stringify(LIB.refused, null, 1));
  assert.ok(LIB.ids.length >= 8, `${LIB.ids.length} setups`);
  for (const id of SIX) assert.ok(LIB.byId[id], `${id} is in the library`);
  assert.deepEqual([...SU.SETUP_GROUPS], [...BANK_GROUPS]);
  assert.deepEqual(LIB.ids, RAW.order, "the rotation order is the file's");
  assert.equal(LIB.cfg.rotate_bars, 16);
});

test("every setup places every one of the 13 groups, and a placement that misses one, names an unknown colour or a red is refused", () => {
  for (const s of RAW.setups) {
    assert.deepEqual(SU.validateSetup(s), [], s.id);
    for (const g of BANK_GROUPS) assert.ok(s.place[g], `${s.id} places ${g}`);
  }
  const base = structuredClone(RAW.setups[0]);
  const miss = structuredClone(base); delete miss.place["strand.bars"];
  assert.ok(SU.validateSetup(miss).some((m) => /strand\.bars: missing/.test(m)));
  const unknown = structuredClone(base); unknown.place.halo = { a: "nope" };
  assert.ok(SU.validateSetup(unknown).some((m) => /place\.halo\.a/.test(m)));
  const red = structuredClone(base); red.colours.blue = "#ff1010";
  assert.ok(SU.validateSetup(red).some((m) => /red share|red sector/.test(m)));
  const amber = structuredClone(base); amber.colours.sky = "#ffb030";
  assert.ok(SU.validateSetup(amber).some((m) => /reads amber/.test(m)), "an amber colour in a setup not about it");
  const flat = structuredClone(base); flat.cycle = ["blue", "blue"];
  assert.ok(SU.validateSetup(flat).length);
  const pinned = structuredClone(base); pinned.place.halo = { a: "white", pin: true, join: 1 };
  assert.ok(SU.validateSetup(pinned).some((m) => /pinned and joining/.test(m)));
});

test("no red: every colour of every setup, every colour any group shows at any bank, every laser", () => {
  for (const S of LIB.list) {
    for (const n of S.names) { const c = SU.colourOf(S, n); assert.ok(PAL.redMax(c) <= PAL.RED_CAP + 1e-9 && !PAL.inRedSector(PAL.lchOfLin(c)), `${S.id} ${n}`); }
    const t = new Float32Array(SU.NR * 3);
    for (let k = 0; k <= 6; k++) {
      for (const g of BANK_GROUPS) for (let part = 0; part < 3; part++) {
        SU.tableInto(S, g, part, k, null, t);
        for (let r = 0; r < SU.NR; r++) assert.ok(!PAL.isSaturatedRed([t[r * 3], t[r * 3 + 1], t[r * 3 + 2]]), `${S.id} ${g} bank ${k}`);
      }
      const L = SU.lasersAt(S, k);
      for (const c of L.colours) assert.ok(PAL.redMax(c) <= PAL.RED_CAP + 1e-9, `${S.id} laser bank ${k}`);
      for (let i = 0; i < 32; i++) if (L.fanRamp) assert.ok(!PAL.isSaturatedRed(Array.from(L.fanRamp.subarray(i * 3, i * 3 + 3))), `${S.id} fan bank ${k}`);
    }
  }
});

test("amber and gold only in the setups about it (warm: true), and never the first look: Daniel's \"not permantly only orange and gold\"", () => {
  const warm = LIB.list.filter((s) => s.warm).map((s) => s.id).sort();
  assert.deepEqual(warm, ["ember-cathedral", "gold-sapphire"]);
  assert.ok(!LIB.byId[LIB.ids[0]].warm, "the first setup is not a warm one");
  assert.ok(!LIB.byId[SCENE.show.setups.first].warm, "the set's first setup is not a warm one");
  const ambered = (c) => { const L = PAL.lchOfLin(c); return L.C >= 0.06 && L.h >= PAL.AMBER[0] && L.h <= PAL.AMBER[1]; };
  for (const S of LIB.list) if (!S.warm) for (const n of S.names) assert.ok(!ambered(SU.colourOf(S, n)), `${S.id} ${n}`);
  // and two warm setups never follow one another in the rotation
  for (let i = 0; i < LIB.ids.length; i++) assert.ok(!(LIB.byId[LIB.ids[i]].warm && LIB.byId[LIB.ids[(i + 1) % LIB.ids.length]].warm), LIB.ids[i]);
});

test("the centre row: in Daniel's screenshot setup (Ice Spine) the strand's heads, dots and bars are pinned white at every bank", () => {
  const S = LIB.byId["ice-spine"], t = new Float32Array(SU.NR * 3);
  for (const g of ["strand.heads", "strand.dots", "strand.bars"]) {
    assert.ok(S.place[g].pin, g);
    for (let k = 0; k <= 6; k++) { SU.tableInto(S, g, 0, k, null, t); for (let r = 0; r < SU.NR; r++) assert.ok(PAL.lchOfLin([t[r * 3], t[r * 3 + 1], t[r * 3 + 2]]).C < 0.03, `${g} bank ${k}`); }
  }
});

test("the bank within a setup: every non-pinned group's a, b, gradient middle and whites change on every press; a pinned group never", () => {
  for (const S of LIB.list) assert.deepEqual(SU.bankProblems(S), [], S.id);
});

test("the crossfades: every colour of every setup to every other (from banks 0-3), from every palette's own roles and back, has a clean path (no red, no wash-out)", () => {
  const a = new Float32Array(SU.NR * 3), b = new Float32Array(SU.NR * 3), at = (t, r) => [t[r * 3], t[r * 3 + 1], t[r * 3 + 2]];
  const counts = [0, 0, 0, 0];
  const check = (A, B, tag) => { for (let r = 0; r < SU.NR; r++) { const x = at(A, r), y = at(B, r), p = SU.pathOf(x, y); counts[p]++; assert.notEqual(p, SU.PATH.CUT, `${tag} role ${ROLE_NAMES[r]} ${PAL.linToHex(x)}->${PAL.linToHex(y)}`); assert.ok(SU.pathClean(x, y, p), tag); } };
  for (const S of LIB.list) for (const T of LIB.list) {
    if (S === T) continue;
    for (let k = 0; k < 4; k++) for (const g of BANK_GROUPS) for (let part = 0; part < 3; part++) {
      SU.tableInto(S, g, part, k, null, a); SU.tableInto(T, g, part, 0, null, b);
      check(a, b, `${S.id}@${k} -> ${T.id} ${g}.${part}`);
    }
  }
  for (const pal of PLIB.ids) {
    const roles = rolesOf(pal), own = new Float32Array(SU.NR * 3);
    roles.forEach((c, r) => own.set(c, r * 3));
    for (const S of LIB.list) for (const g of BANK_GROUPS) {
      SU.tableInto(S, g, 0, 0, null, b);
      check(own, b, `${pal} -> ${S.id} ${g}`);
      check(b, own, `${S.id} -> ${pal} ${g}`);
    }
  }
  assert.ok(counts[0] > 0 && counts[1] + counts[2] > 0, `paths used: ${counts.map((n, i) => `${SU.PATH_NAMES[i]} ${n}`).join(", ")}`);
});

test("the paths themselves: gold to sapphire never passes through grey (the straight line would), orange to magenta never through red", () => {
  const gold = PAL.hexToLin("#ffc83a"), sapphire = PAL.hexToLin("#2a48e0"), orange = PAL.hexToLin("#ff9a2e"), magenta = PAL.hexToLin("#e044e0");
  assert.equal(SU.pathClean(gold, sapphire, SU.PATH.LAB), false, "the straight OKLab line greys out");
  const p = SU.pathOf(gold, sapphire);
  assert.notEqual(p, SU.PATH.LAB);
  const q = SU.pathOf(orange, magenta);
  assert.equal(SU.pathClean(orange, magenta, SU.PATH.LCH_SHORT), false, "the short way runs through red");
  assert.equal(q, SU.PATH.LCH_LONG);
  for (let i = 0; i <= 16; i++) assert.ok(!PAL.inRedSector(PAL.lchOfLin(SU.mixPath(orange, magenta, i / 16, q))));
});

test("the programmer: a setup lands, every group shows it, kick 5 turns every lit non-pinned group every press, the pinned hold, no red, the heads on the setup's slots", () => {
  for (const S of LIB.list) {
    const g = locked(), p = fresh();
    play(p, g, 0, 8);
    p.setSetupNow(S);
    play(p, g, 8, 12);
    const red = p.redSlotsOf(0);
    let prev = Object.fromEntries(BANK_GROUPS.map((n) => [n, groupState(p, n)]));
    for (let press = 1; press <= 4; press++) {
      assert.ok(p.bankAdvance(g.posAt((12 + press * 2) * g.period)), `${S.id} press ${press}`);
      play(p, g, 12 + press * 2, 14 + press * 2);
      const now = Object.fromEntries(BANK_GROUPS.map((n) => [n, groupState(p, n)]));
      for (const n of BANK_GROUPS) {
        const a = prev[n].cells, b = now[n].cells;
        if (a && b) {
          if (S.place[n].pin) assert.ok(PAL.deOK(a, b) < 0.02, `${S.id} ${n} pinned, press ${press}: ${PAL.linToHex(a)} -> ${PAL.linToHex(b)}`);
          else assert.ok(PAL.deOK(a, b) > 0.04, `${S.id} ${n} press ${press}: ${PAL.linToHex(a)} -> ${PAL.linToHex(b)}`);
        }
        for (const s of now[n].slots) assert.ok(!red.includes(s), `${S.id} ${n} on a red slot`);
      }
      for (let c = 0; c < p.nC; c++) { const l = p.pixels[c * 4 + 3]; if (l > 0.05) assert.ok(!PAL.isSaturatedRed([p.pixels[c * 4] / l, p.pixels[c * 4 + 1] / l, p.pixels[c * 4 + 2] / l]), `${S.id} cell ${c}`); }
      for (let i = 0; i < p.nH; i++) if (p.wheels[i]) assert.ok(p._setupAllowed(i).includes(Math.round(p.wheelPos[i]) % 14) || p.sx.fading, `${S.id} head ${i} off the setup's slots`);
      prev = now;
    }
  }
});

test("Neon Split: the left beams pink and the right cyan, and a press swaps them through violet", () => {
  const g = locked(), p = fresh();
  play(p, g, 0, 4);
  p.setSetupNow(LIB.byId["neon-split"]);
  play(p, g, 4, 10);
  const sides = () => {
    const gi = p.bankG.names.indexOf("truss.heads"), out = { 1: new Set(), 2: new Set() };
    for (let i = 0; i < p.nH; i++) if (p.bankG.headG[i] === gi) out[p.headSG[i] - gi * 3]?.add(Math.round(p.wheelPos[i]) % 14);
    return [[...out[1]], [...out[2]]];
  };
  const [L0, R0] = sides();
  assert.ok(L0.every((s) => s === 10 || s === 11), `left ${L0}`);
  assert.deepEqual(R0, [6], `right ${R0}`);
  p.bankAdvance(g.posAt(10 * g.period));
  play(p, g, 10, 16);
  const [L1, R1] = sides();
  assert.deepEqual(L1, [6], `left after a press ${L1}`);
  assert.ok(R1.every((s) => s === 9 || s === 13), `right after a press ${R1} (violet)`);
});

test("the white kick under a setup stays white, at bank 0 and after presses, while the look's own whites take the colour", () => {
  const g = locked(), p = fresh();
  play(p, g, 0, 4);
  p.setSetupNow(LIB.byId["ice-spine"]);
  play(p, g, 4, 8);
  p.bankAdvance(g.posAt(8 * g.period)); p.bankAdvance(g.posAt(8.5 * g.period));
  play(p, g, 8.5, 10);
  const k = p.pad("kick-white", 1, g.posAt(10 * g.period), { hold: true });
  assert.ok(k, "a white kick was dealt");
  play(p, g, 10, 10.5);
  let n = 0;
  for (const c of k.card.cells) {
    const b = c * 4, l = p.pixels[b + 3];
    if (l < 0.3 || !((p.tC[b + 3] | 0) === ROLE_NAMES.indexOf("W") && p.tC[b + 1] > 0.95)) continue;
    n++;
    assert.ok(PAL.lchOfLin([p.pixels[b] / l, p.pixels[b + 1] / l, p.pixels[b + 2] / l]).C < 0.03, `cell ${c} under the white kick`);
  }
  if (k.card.cells.length) assert.ok(n > 0, "some kicked cells read");
  assert.ok(SU.whitesTurn(LIB.byId["ice-spine"], "truss.heads") && !SU.whitesTurn(LIB.byId["ice-spine"], "strand.bars"));
});

test("a crossfade lands ON its line: nothing changes before it, the colours move along clean paths after it, the target after its beats", () => {
  const g = locked(), p = fresh();
  play(p, g, 0, 8);
  p.setSetupNow(LIB.byId["ice-spine"]);
  play(p, g, 8, 12);
  const before = p.sx.shown.slice();
  p.beginSetup(LIB.byId["gold-sapphire"], 16, { beats: 4 });
  play(p, g, 12, 15.9);
  assert.ok(p.sx.shown.every((v, i) => Math.abs(v - before[i]) < 1e-6), "unchanged before the line");
  assert.equal(p.setupStatus().id, "ice-spine");
  play(p, g, 15.9, 18);
  assert.equal(p.setupStatus().id, "gold-sapphire");
  assert.ok(p.sx.fading, "half way through the crossfade");
  for (let e = 0; e < p.sx.shown.length; e += 3) assert.ok(!PAL.isSaturatedRed([p.sx.shown[e], p.sx.shown[e + 1], p.sx.shown[e + 2]]));
  play(p, g, 18, 20.1);
  assert.ok(!p.sx.fading);
  assert.ok(p.sx.shown.every((v, i) => Math.abs(v - p.sx.T[i]) < 1e-6), "the target after the crossfade");
  const ev = p.takeSetupEvents().map((e) => e.type);
  assert.deepEqual(ev.slice(-2), ["swap", "landed"]);
  // and back to the palette's own looks: the layer switches off once the crossfade ends
  p.beginSetup(null, 24, { beats: 4 });
  play(p, g, 20.1, 28.1);
  assert.equal(p.setupOn, false);
});

test("the lasers and the HAL cubes follow the setup: its own laser colours at bank 0, every laser another colour on every press, the cubes' glow turning with the strand", () => {
  for (const S of LIB.list) {
    const L0 = SU.lasersAt(S, 0);
    assert.deepEqual(L0.names, S.lasers, S.id);
    for (let k = 0; k < 6; k++) {
      const a = SU.lasersAt(S, k), b = SU.lasersAt(S, k + 1);
      for (let i = 0; i < a.colours.length; i++) assert.ok(PAL.deOK(a.colours[i], b.colours[i]) >= 0.08, `${S.id} laser ${i} bank ${k}->${k + 1}`);
      for (const c of b.colours) assert.ok(PAL.lchOfLin(c).L >= SU.SETUP_LIMITS.laser_floor - 2e-3, `${S.id} laser bright enough`);
    }
    const c0 = SU.cubesAt(S, 0), c1 = SU.cubesAt(S, 1);
    if (!S.place["strand.cubes"].pin) assert.ok(PAL.deOK(c0.glowTop, c1.glowTop) > 0.04 || PAL.deOK(c0.glowBottom, c1.glowBottom) > 0.04, `${S.id} cube glow turns`);
  }
  assert.deepEqual(SU.cubesAt(LIB.byId["ice-spine"], 0).names.glow, ["blue", "violet"]);
  // the programmer hands the page its setup's lasers and cube tint
  const g = locked(), p = fresh();
  play(p, g, 0, 2);
  p.setSetupNow(LIB.byId["neon-split"]);
  play(p, g, 2, 3);
  assert.deepEqual(p.sx.lasers.names, ["green"]);
  const s0 = p.sx.laserSerial;
  p.bankAdvance(g.posAt(3 * g.period));
  assert.ok(p.sx.laserSerial > s0);
  assert.deepEqual(p.sx.lasers.names, ["cyan"]);
  assert.ok(p.sx.cube && p.sx.cube.glowTop.length === 3);
});

test("the rotation: the next change on the next 16-bar line at least 8 bars after the last landing; O on the next bar line; stepping wraps", () => {
  assert.equal(SU.nextAutoLine(0, 0, 0), 64);
  assert.equal(SU.nextAutoLine(63.9, 0, 0), 64);
  assert.equal(SU.nextAutoLine(64, 0, 64), 128);
  assert.equal(SU.nextAutoLine(60, 0, 40), 128, "landed by hand at bar 10: bar 16 is too soon, bar 32 it is");
  assert.equal(SU.nextAutoLine(10, 2, -Infinity), 66);
  assert.equal(SU.nextBarLine(5, 0), 8);
  assert.equal(SU.nextBarLine(8, 0), 12);
  assert.equal(SU.nextBarLine(5.5, 2), 6);
  assert.equal(SU.stepSetup(LIB, LIB.ids[LIB.ids.length - 1], 1), LIB.ids[0]);
  assert.equal(SU.stepSetup(LIB, LIB.ids[0], -1), LIB.ids[LIB.ids.length - 1]);
});

test("a setup may draw its colours from the active palette (@Role), resolved live and checked against the palette", () => {
  const raw = { id: "spine-test", name: "Spine test", colours: { white: "@W", bed: "@A", partner: "@B" }, cycle: ["bed", "partner"],
                place: Object.fromEntries(BANK_GROUPS.map((n) => [n, n.startsWith("strand.") && n !== "strand.cubes" ? { a: "white", pin: true } : { a: n === "halo" ? "partner" : "bed" }])), lasers: "@lasers" };
  const roles = rolesOf("source-violet");
  assert.deepEqual(SU.validateSetup(raw, { roles }), []);
  const S = SU.compileSetup(raw);
  assert.deepEqual(SU.colourOf(S, "bed", roles), roles[ROLE_NAMES.indexOf("A")]);
  assert.equal(SU.lasersAt(S, 1, roles), null, "the palette's own lasers");
});

test("the page wires it: the set's pads 13 and 14, key O, the pad actions, the HUD, the api door, the URL options, the stills lane's --setup", () => {
  assert.equal(SCENE.show.pads["13"], "setup-next");
  assert.equal(SCENE.show.pads["14"], "setup-prev");
  const page = readFileSync(new URL("../arsenal/web/stage/stage.js", import.meta.url), "utf8");
  assert.match(page, /e\.code === "KeyO"\) setupGo\(e\.shiftKey \? -1 : 1, tEval\)/);
  assert.match(page, /action === "setup-next" && on\) setupGo\(1, tEval\)/);
  assert.match(page, /action === "setup-prev" && on\) setupGo\(-1, tEval\)/);
  assert.match(page, /setup: \(id, \{ now = false \} = \{\}\) => setupGo/);
  assert.match(page, /QS\.get\("setup"\)/);
  assert.match(page, /\["hold", "off", "rotate"\]\.includes\(QS\.get\("setups"\)\)/);
  assert.match(page, /setup \$\{cs \? cs\.name/);
  const html = readFileSync(new URL("../arsenal/web/stage/index.html", import.meta.url), "utf8");
  assert.match(html, /<kbd>O<\/kbd> next setup/);
  const lane = readFileSync(new URL("../arsenal/lanes/stage_stills.mjs", import.meta.url), "utf8");
  assert.match(lane, /setup: \{ type: "string"/);
});

// THE BEAMS FOLLOW THE SETUP (Lane S job 1, 2026-10-30). The report that opened this: "in Ice Spine, Aurora Column, Source Fan
// and Ember Cathedral the moving heads' beams stay on the palette's wheel plan (violet), so those setups change the halo,
// cubes and lasers but not the beams". What is pinned here is the mechanism that claim is about: a head's wheel range is
// derived from the colours the setup places on ITS OWN GROUP over the whole bank turn -- so a beam can only ever show its own
// placement, can never take a colour another part of the rig owns, and can never fall back onto the palette's plan. The
// colours below are read from the library JSON directly (not from setups.js), so this is not the same derivation the code
// does: it is an independent re-statement of "the truss got gold, so the truss may only show gold's slot".
const roleColour = (v, roles) => (v.startsWith("#") ? PAL.hexToLin(v.toLowerCase()) : roles[PAL.STAGE_ROLES.indexOf(v.slice(1))]);
const nonRed = (wheel, red) => wheel.map((_, i) => i).filter((i) => !red.includes(i));
function groupNames(raw, gname) {
  const pl = raw.place[gname], out = new Set([pl.a]);
  if (pl.b) out.add(pl.b);
  out.add(pl.w || "white");
  for (const side of ["left", "right"]) if (pl[side]) { out.add(pl[side].a); if (pl[side].b) out.add(pl[side].b); }
  // the bank turns every colour that is on the cycle to the next ones, so the group may show the whole cycle; a group whose
  // colours are all off it but which says it JOINS takes cycle colours from the first press (setups.js compileSetup)
  if (Number.isInteger(pl.join) || [...out].some((n) => raw.cycle.includes(n))) for (const c of raw.cycle) out.add(c);
  return out;
}
test("the beams follow the setup: a head group's wheel range is the colours the setup places on THAT group, never another part's", () => {
  const planSlots = new Set([0]);
  for (const id of PLIB.ids) { const pl = PAL.planOf(PLIB.byId[id]); for (const s of pl.slots) planSlots.add(s); }
  for (const raw of RAW.setups) {
    const S = LIB.byId[raw.id], p = fresh(), g = locked(150);
    p.setLook("drop", 0); play(p, g, 0, 8); p.setSetupNow(S); play(p, g, 8, 12);
    for (let gi = 0; gi < p.bankG.names.length; gi++) {
      const gname = p.bankG.names[gi];
      for (let i = 0; i < p.nH; i++) {
        if (p.bankG.headG[i] !== gi || !p.wheels[i]) continue;
        const wheel = p.wheels[i], red = p.redSlotsOf(i), allowed = nonRed(wheel, red);
        const want = new Set([0]);
        for (const n of groupNames(raw, gname)) want.add(nearestSlot(wheel, roleColour(raw.colours[n], p.roleRGB), allowed));
        const got = p._setupAllowed(i);
        assert.deepEqual(got, [...want].sort((a, b) => a - b), `${raw.id} ${gname} head ${i}: the range is the group's own colours`);
        // the palette's plan slots are NOT reachable, unless this group itself has a colour that maps to one
        const mine = new Set([...want]);
        for (const s of planSlots) if (raw.place[gname] && !mine.has(s) && s !== 0) assert.ok(!got.includes(s), `${raw.id} ${gname} head ${i}: slot ${s} is the palette's plan, not this group's`);
      }
    }
  }
});
test("the beams follow the setup: every lit beam sits on the slot nearest the colour its group was given, at every bank", () => {
  for (const raw of RAW.setups) {
    const S = LIB.byId[raw.id], p = fresh(), g = locked(150);
    p.setLook("drop", 0); play(p, g, 0, 8); p.setSetupNow(S); play(p, g, 8, 12);
    const seen = new Map();
    for (let press = 0; press < 4; press++) {
      const slots = groupState(p, "truss.heads");
      for (const s of slots.slots) seen.set(s, (seen.get(s) || 0) + 1);
      p.pad("kick-colour", 0.9, g.posAt(12 * g.period + press * 4 * g.period));
      play(p, g, 12 + press * 4, 13 + press * 4);
    }
    assert.ok(seen.size >= 1, `${raw.id}: the truss beams are lit under the drop and show a colour`);
    const truss = [...Array(p.nH).keys()].find((i) => p.bankG.names[p.bankG.headG[i]] === "truss.heads" && p.wheels[i]);
    assert.ok(truss >= 0, `${raw.id}: the rig has truss heads with a wheel`);
    for (const s of seen.keys()) {
      assert.ok(!p.redSlotsOf(truss).includes(s), `${raw.id}: the beams never rest on a red slot`);
      // the beam's colour is the wheel's, and it is one of the truss group's own (never the palette's plan unless it has it)
      assert.ok(p._setupAllowed(truss).includes(s), `${raw.id}: beam slot ${s} is in the truss group's own range`);
    }
  }
});

// THE PHONE BAR'S COLOUR STRIP (Lane S job 2b, 2026-10-30). The strip wore the palette's two kick LIFT colours, which is what
// kick 5 dealt while it was a palette-lift colour kick; kick 5 then became the colour BANK (kick.js header, KICK round 3), so
// the strip promised colours a press no longer deals and stage_verify's phonebar check kept asserting the stale pair. Now the
// page publishes the bank's colours on its palette and setup events, the strip wears them, and both the check and these pins
// read the same source -- a strip that falls back to the ladder while the bank deals something else is the stale state the
// re-registered check fails on.
test("the bank's colours (kick 5) as hex: the setup's own cycle under a setup, the palette's bank cycle without one", () => {
  for (const id of LIB.ids) {
    const S = LIB.byId[id], p = fresh(), g = locked(150);
    p.setLook("drop", 0); play(p, g, 0, 8); p.setSetupNow(S); play(p, g, 8, 12);
    const hex = p.bankHex(), cy = SU.cycleOf(S, p.roleRGB);
    assert.equal(hex.length, cy.length, `${id}: one colour for every colour on the cycle`);
    for (let i = 0; i < cy.length; i++) assert.equal(hex[i].toLowerCase(), PAL.linToHex(SU.colourOf(S, cy[i], p.roleRGB).slice()).toLowerCase(), `${id}: ${cy[i]}`);
  }
  const q = fresh(), g = locked(150); q.setLook("drop", 0); play(q, g, 0, 8);
  const hex = q.bankHex();
  assert.ok(hex.length >= 2 && hex.every((h) => /^#[0-9a-f]{6}$/i.test(h)), `the palette's bank: ${hex.join(" ")}`);
  // the page publishes them on BOTH events and the strip reads them (the wiring the phonebar phase then exercises on the GPU)
  const page = readFileSync(new URL("../arsenal/web/stage/stage.js", import.meta.url), "utf8");
  assert.equal((page.match(/bank: programmer\.bankHex\(\)/g) || []).length, 2, "both the palette and the setup events carry the bank");
  const bar = readFileSync(new URL("../arsenal/web/lib/touchbar.js", import.meta.url), "utf8");
  assert.match(bar, /Array\.isArray\(d\.bank\)/);
  assert.match(bar, /addEventListener\("arsenal:setup"/);
  const lane = readFileSync(new URL("../arsenal/lanes/stage_verify.mjs", import.meta.url), "utf8");
  assert.match(lane, /the colour strip wears the bank's colours/);
  assert.match(lane, /deals kick 5's bank one place/);
});
