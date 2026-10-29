// The thirty palettes (arsenal/web/palettes.js + palettes.json) driving the Stage. node --test tests/stage_palettes.test.mjs
//
// Daniel, 2026-10-28: "when i tried the color options on my phone the lights just turn amber, the dns strands just change
// amber sometimes or dont change at all, i love the built in gradients you built for the dna strands can we make more high
// quality color theme presets and animations. I want us to have 30 color palates that are high quality and what is used
// for driving the colors so it always looks careful and deliberate, perhaps for the lights we can also have color gradient
// patches as well as single colors". On the colour kick: "I want us to be able to have both, sometimes white is good other
// times color is good".
//
// What these pin (research/in-flight/palettes-2026-10-28/DESIGN.md): the shared validator (all thirty pass, the faults it
// exists for are refused, ?theme=molten loads), every palette through every look with no red and no warm white on a head,
// the colour kick's lift (each cell's own roles lifted, the helix kept, the pattern jumped a quarter cycle), the white kick
// that never turns a wheel, the wheel plans, the amber share, the switch (a neighbour crossfades over 4 bars, anything else
// dips through black for a beat, both landing on the next 16-bar line), the splits and pins, the tempo, the lasers.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { Programmer, H, HEAD_FLOATS, ROLE, ROLE_NAMES, LIFT, CELL_KIND, resolveTheme } from "../arsenal/web/stage/programmer.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import { LaserEngine, extraHeadsFrom, SEG, SEG_FLOATS } from "../arsenal/web/stage/lasers.js";
import * as KICK from "../arsenal/web/stage/kick.js";
import * as PAL from "../arsenal/web/palettes.js";
import { mountTouchBar, STAGE_PADS, STAGE_STRIPS } from "../arsenal/web/lib/touchbar.js";

const RAW = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const WHEEL_HEX = SCENE.types["beam-7r"].attrs.Color1.colours;
const LIB = PAL.loadPalettes(RAW, { wheel: WHEEL_HEX });
const FPS = 60, DT = 1 / FPS, W = "kick-white", C = "kick-colour";
const CTO = PAL.CTO_SLOT;
const clone = (o) => JSON.parse(JSON.stringify(o));
const locked = (bpm = 150) => { const g = new BeatGrid({ bpm, t0: 0 }); g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0); return g; };
const fresh = (id, look = "drop", seed = 7) => { const p = new Programmer(RIG, { theme: PAL.stageTheme(LIB.byId[id]), seed }); p.setLook(look, 0); return p; };
function play(p, g, a, b, each = null) {
  for (let t = a * g.period; t < b * g.period; t += 1000 / FPS) { const pos = g.posAt(t); if (each) each(pos, t); p.tick(g, t, DT); }
}
const cardIx = (name) => KICK.kickConfig(RIG).cards.findIndex((c) => c.name === name);
const force = (p, name) => { p.kick.deck.forceNext = cardIx(name); };
const headRGB = (p, i) => [p.heads[i * HEAD_FLOATS + H.R], p.heads[i * HEAD_FLOATS + H.G], p.heads[i * HEAD_FLOATS + H.B]];
const cellRGB = (p, c) => { const l = p.pixels[c * 4 + 3]; return l > 1e-5 ? [p.pixels[c * 4] / l, p.pixels[c * 4 + 1] / l, p.pixels[c * 4 + 2] / l] : null; };

// --------------------------------------------------------------------------------------------- the validator --
test("the library: thirty palettes, every one passes the shared validator against the rig's own wheel, in six family tabs", () => {
  assert.equal(RAW.palettes.length, 30);
  assert.equal(LIB.list.length, 30, `refused: ${JSON.stringify(LIB.refused)}`);
  assert.equal(new Set(LIB.ids).size, 30);
  assert.deepEqual(RAW.wheel.map((s) => s.hex), WHEEL_HEX, "palettes.json checked its plans against this rig's wheel");
  assert.deepEqual(Object.keys(LIB.families), ["violet", "pink", "blue", "green", "warm", "neutral"]);
  assert.equal(SCENE.show.palette, "source-violet", "the show's default palette is Source Violet (the strand pair Daniel loves)");
  const sv = LIB.byId["source-violet"];
  assert.deepEqual([sv.stage_theme.A, sv.stage_theme.B], ["#7a3cff", "#ff38d8"], "the loved strand pair, kept exactly");
  // the lift every palette declares is the one the programmer applies (programmer.js LIFT, swap 0)
  for (const p of LIB.list) {
    const st = p.stage_theme;
    for (const [role, hex] of Object.entries(p.kick.lift_by_stage_role)) {
      if (role === "pin") continue;
      const lifted = LIFT[0][role];
      const want = { bumpB: st.bumpB, bumpA: st.bumpA, accentLift: PAL.stageTheme(p).accentLift }[lifted];
      assert.equal(hex.toLowerCase(), want.toLowerCase(), `${p.id}: ${role} lifts to ${lifted}`);
    }
  }
});

test("the validator refuses what it exists for: a red bed, an amber kick in a cool palette, a head lift to the warm white or onto pink, a red laser, an unmatched ladder, a red gradient sample", () => {
  const sv = LIB.byId["source-violet"];
  const bad = (edit) => { const p = clone(sv); edit(p); return PAL.validatePalette(p, WHEEL_HEX); };
  const set = (p, role, hex) => { p.colours.find((c) => c.role === role).hex = hex; };
  assert.deepEqual(PAL.validatePalette(sv, WHEEL_HEX), []);
  assert.ok(bad((p) => set(p, "base", "#ff7a1a")).some((m) => /base .*red share/.test(m)), "the old Molten bed (linear red share 0.83)");
  assert.ok(bad((p) => { set(p, "kick", "#ffd166"); p.kick.ladder[0] = "#ffd166"; }).some((m) => /reads amber/.test(m)), "an amber kick");
  assert.ok(bad((p) => { p.heads.lift[0].to = 11; }).some((m) => /lift 9->11/.test(m)), "onto pink (the red sector)");
  assert.ok(bad((p) => { p.heads.lift[0] = { frm: 11, to: 12 }; }).some((m) => /lift target 12/.test(m)), "to the warm white");
  assert.ok(bad((p) => { p.heads.rest.slot = 12; }).some((m) => /rest slot 12/.test(m)), "resting on the warm white");
  assert.ok(bad((p) => { p.lasers[0] = "#ff2010"; }).some((m) => /laser 0/.test(m)), "a red laser");
  assert.ok(bad((p) => { set(p, "highlight", "#5a3d99"); p.kick.ladder[1] = "#5a3d99"; }).some((m) => /luminance ratio/.test(m)), "a re-strike that would flash");
  assert.ok(bad((p) => { p.gradients[0].samples32[5] = "#ff1010"; }).some((m) => /gradient strand: sample/.test(m)), "a red sample");
  // Molten is the one warm palette: amber is its declared bed, never a kick of another
  const m = clone(LIB.byId.molten);
  assert.deepEqual(PAL.validatePalette(m, WHEEL_HEX), []);
  m.warm_declared = false;
  assert.ok(PAL.validatePalette(m, WHEEL_HEX).some((x) => /amber|lift target 3/.test(x)), "Molten undeclared is refused");
  // a refused palette is left out; the rest load (a page never crashes on one)
  const raw = clone(RAW); raw.palettes[3].colours.find((c) => c.role === "base").hex = "#ff0000";
  const lib = PAL.loadPalettes(raw, { wheel: WHEEL_HEX });
  assert.equal(lib.list.length, 29); assert.equal(lib.refused[0].id, raw.palettes[3].id);
});

test("?theme=molten no longer crashes: Molten is a palette (the page looks palettes up first); the set's old Molten theme is still refused by the house rule", () => {
  assert.doesNotThrow(() => resolveTheme(PAL.stageTheme(LIB.byId.molten)));
  assert.throws(() => resolveTheme({ name: "molten", ...SCENE.themes.molten }), /saturated red/);
  const page = readFileSync(new URL("../arsenal/web/stage/stage.js", import.meta.url), "utf8");
  assert.match(page, /const PALETTE_ASKED = asName\(QS\.get\("palette"\)\) \|\| THEME_ASKED;/);
  assert.match(page, /const palAsked = palettes && PALETTE_ASKED && palettes\.byId\[PALETTE_ASKED\] \? PALETTE_ASKED : null;/);
  const g = locked(), p = fresh("molten", "drop");
  play(p, g, 0, 8);
  assert.ok(p.pixels.some((x) => x > 0), "Molten lights the rig");
});

// ------------------------------------------------------------------------------ every palette through every look --
test("every palette through every look and both kicks: no saturated red anywhere, no head ever on the red, pink or warm-white slot, every head on its palette's plan", () => {
  const report = [];
  for (const p0 of LIB.list) {
    const plan = PAL.planOf(p0);
    let redCells = 0, badSlots = 0, offPlan = 0, frames = 0;
    for (const look of ["intro", "build", "drop", "break", "groove"]) {
      const g = locked(), p = fresh(p0.id, look);
      let k = 0;
      play(p, g, 0, 4 + 4 * 3, (pos) => {
        if (pos >= 4 + 3 * k && k < 4) { p.pad(k % 2 ? W : C, 0.8, pos, { hold: true }); p.padRelease(k % 2 ? W : C, pos + 1.5); k++; }
        if (pos < 2) return;
        frames++;
        for (let i = 0; i < p.nH; i++) {
          if (!(p.heads[i * HEAD_FLOATS + H.DIM] > 0.01)) continue;
          const s = p.wheelSlotOf(i);
          if (s === 1 || s === 11 || s === CTO) badSlots++;
          if (!plan.slots.includes(s) && p.headSlotOv[i] < 0) offPlan++;
        }
        for (let c = 0; c < p.nC; c += 7) { const col = cellRGB(p, c); if (col && p.cellKind[c] !== CELL_KIND.PIN && PAL.isSaturatedRed(col)) redCells++; }
      });
    }
    report.push(`${p0.id.padEnd(17)} frames ${frames} red cells ${redCells} heads on 1/11/12 ${badSlots} off plan ${offPlan}`);
    assert.equal(redCells, 0, `${p0.id}: a saturated red cell`);
    assert.equal(badSlots, 0, `${p0.id}: a lit head on the red, pink or warm-white slot`);
    assert.equal(offPlan, 0, `${p0.id}: a lit head off its palette's plan`);
  }
  console.log(`  every palette, every look:\n  ${report.join("\n  ")}`);
});

// ------------------------------------------------------------------------------------------- the amber share --
// inventory.md's method: colour kicks on the head areas (halo, beams, strand), a bar apart, held 2 beats at velocity 0.7,
// each head measured 1.5 beats in; before (the combined build's themes): the halo on the warm white 100 % of the time in
// the violet themes, the beams 53-56 %.
export function amberShare(id, { looks = ["intro", "build", "drop", "break", "groove"], presses = 12 } = {}) {
  const pl = LIB.byId[id], plan = PAL.planOf(pl);
  const fam = [pl.kick.ladder[0], pl.kick.ladder[1], ...pl.colours.filter((c) => ["base", "partner", "mid", "accent"].includes(c.role)).map((c) => c.hex)].map(PAL.lchOf);
  let frames = 0, cto = 0, palette = 0, moved = 0, whiteMoves = 0, whiteFrames = 0;
  for (const look of looks) {
    const g = locked(), p = fresh(id, look);
    let k = 0, pending = null;
    play(p, g, 0, 4 + presses * 4 + 4, (pos) => {
      if (pos >= 4 + 4 * k && k < presses && !pending) {
        const kind = k % 3 === 2 ? W : C;
        force(p, ["halo", "beams", "strand"][k % 3]);
        const all = Array.from({ length: p.nH }, (_, i) => p.wheelSlotOf(i));
        const rec = p.pad(kind, 0.7, pos, { hold: true });
        const before = Array.from(rec.card.heads, (i) => all[i]);
        pending = { rec, kind, at: pos, before };
        k++;
      }
      if (pending && pos >= pending.at + 1.5) {
        const { rec, kind, before } = pending;
        rec.card.heads.forEach((i, m) => {
          const s = p.wheelSlotOf(i);
          if (kind === W) { whiteFrames++; if (s !== before[m]) whiteMoves++; return; }
          frames++;
          if (s === CTO) cto++;
          if (s !== before[m]) moved++;
          const h = PAL.lchOf(WHEEL_HEX[s]).h;
          if (s !== 0 && fam.some((f) => PAL.hueGap(f.h, h) <= 45)) palette++;
        });
        p.padRelease(kind, pos);
        pending = null;
      }
    });
  }
  return { id, frames, cto, ctoShare: frames ? cto / frames : 0, palette, paletteShare: frames ? palette / frames : 0, moved, whiteFrames, whiteMoves, plan: plan.slots };
}
test("the amber share: kicked moving heads never show the warm-white slot in any palette; colour-kick heads show a palette colour; the white kick never moves a wheel", () => {
  const rows = [];
  for (const id of LIB.ids) {
    const r = amberShare(id, { looks: ["intro", "drop", "groove"], presses: 6 });
    rows.push(`${id.padEnd(17)} colour-kick head frames ${String(r.frames).padStart(4)}: warm white ${(100 * r.ctoShare).toFixed(1)} %, palette colour ${(100 * r.paletteShare).toFixed(1)} %, moved ${r.moved}; white-kick head frames ${r.whiteFrames}, wheels moved ${r.whiteMoves}`);
    assert.equal(r.cto, 0, `${id}: ${r.cto} colour-kick head frames on the warm white`);
    assert.equal(r.whiteMoves, 0, `${id}: the white kick moved ${r.whiteMoves} wheels`);
    if (!PAL.planOf(LIB.byId[id]).whiteKicksOnly) assert.ok(r.paletteShare >= 0.5, `${id}: colour-kick heads on a palette colour ${(100 * r.paletteShare).toFixed(0)} %`);
  }
  console.log(`  the amber share (3 looks, 6 presses each):\n  ${rows.join("\n  ")}`);
});

test("the dealer: a colour kick never takes an area of heads alone that cannot change colour (the halo on white), and deals the strand at least once in every three presses while it shows", () => {
  for (const id of ["titanium", "noir", "rose-fans"]) {
    const g = locked(), p = fresh(id, "drop");
    const dealt = [];
    let k = 0;
    play(p, g, 0, 4 + 24 * 4, (pos) => { if (pos >= 4 + 4 * k && k < 24) { const r = p.pad(C, 0.8, pos, { hold: true }); dealt.push(r.card.name); p.padRelease(C, pos + 0.5); k++; } });
    assert.ok(!dealt.includes("halo"), `${id}: the colour kick dealt the white-resting halo (${dealt.join(", ")})`);
  }
  for (const id of ["source-violet", "glacier", "molten"]) {
    const g = locked(), p = fresh(id, "groove");
    const dealt = [];
    let k = 0;
    play(p, g, 0, 4 + 30 * 4, (pos) => { if (pos >= 4 + 4 * k && k < 30) { const kind = k % 2 ? W : C; const r = p.pad(kind, 0.8, pos, { hold: true }); dealt.push(r.card.name); p.padRelease(kind, pos + 0.5); k++; } });
    for (let i = 0; i + 3 <= dealt.length; i++) assert.ok(dealt.slice(i, i + 3).includes("strand"), `${id}: presses ${i}-${i + 2} never dealt the strand (${dealt.slice(i, i + 3).join(", ")})`);
    for (let i = 1; i < dealt.length; i++) assert.notEqual(dealt[i], dealt[i - 1], `${id}: ${dealt[i]} twice running`);
  }
});

// ---------------------------------------------------------------------------------- the strand under the kick --
test("the strand under a colour kick keeps its helix: every cube cell its own roles' lift at its own mix, two lift colours across the strand, and the pattern jumps a quarter cycle then eases back over a beat", () => {
  for (const id of ["source-violet", "violet-hold", "cyan-hold", "throne-world"]) {
    const g = locked(), p = fresh(id, "drop"), base = fresh(id, "drop");
    const cubes = RIG.groups["strand.cubes"].members;
    let rec = null, at = null, jumpNow = null, jumpLater = null, lifted = null;
    for (let t = 0; t < 16 * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && pos >= 8.1) { force(p, "strand"); rec = p.pad(C, 0.8, pos, { hold: true }); at = pos; }
      p.tick(g, t, DT); base.tick(g, t, DT);
      const inst = p.effects.get("strand.cubes:cube-colour");
      if (rec && jumpNow === null && pos > at) jumpNow = inst.jump;
      if (rec && jumpLater === null && pos > at + 1.05) jumpLater = inst.jump;
      if (rec && !lifted && pos >= at + 1.5) {
        const pre = p.kick.preC;
        let worst = 0;
        const hexes = new Set(), lumas = [];
        for (let m = 0; m < cubes.length; m += 3) {
          const c = cubes[m], b = c * 4, got = cellRGB(p, c);
          const want = p.liftOfCell(c, pre[b + 2] | 0, pre[b + 3] | 0, Math.max(0, Math.min(1, pre[b + 1])), rec.colour.lift);
          worst = Math.max(worst, PAL.deOK(got, want));
          hexes.add(PAL.linToHex(got));
          lumas.push(PAL.lumaOf(got));
        }
        const lad = rec.colour.lift ? [...LIB.byId[id].kick.ladder].reverse() : LIB.byId[id].kick.ladder;
        const near = (hex) => Math.min(...lad.map((h) => PAL.deOK(hex, h)));
        const span = Math.max(...[...hexes].map((h) => PAL.deOK(h, lad[0])));
        lifted = { worst, n: hexes.size, span, nearEnds: [...hexes].filter((h) => near(h) < 0.02).length, lumaSpread: Math.max(...lumas) / Math.min(...lumas) };
      }
    }
    assert.equal(rec.card.name, "strand");
    assert.ok(lifted.worst < 0.01, `${id}: each cube shows its own lift (dEOK up to ${lifted.worst.toFixed(4)})`);
    assert.ok(lifted.n >= 8 && lifted.span > 0.08, `${id}: the lifted strand is a gradient (${lifted.n} colours, ${lifted.span.toFixed(3)} across), not a flat wash`);
    assert.ok(lifted.nearEnds > 0, `${id}: the helix runs between the two lift colours`);
    assert.ok(Math.abs(jumpNow - KICK.PHASE_JUMP.size) < 0.02, `${id}: the helix jumped a quarter cycle on the hit (${jumpNow})`);
    assert.equal(jumpLater, 0, `${id}: and eased back within a beat`);
  }
});

test("the colour kick is light first: every palette's lift is brighter than its bed and at least 0.15 from white, and the re-strike ladder is luminance-matched (no bright/dark swing)", () => {
  for (const p of LIB.list) {
    const hx = Object.fromEntries(p.colours.map((c) => [c.role, c.hex]));
    assert.ok(PAL.lchOf(hx.kick).L - PAL.lchOf(hx.base).L >= 0.15 - 2e-3, `${p.id}: kick over the bed`);
    assert.ok(PAL.deOK(hx.kick, hx.white) >= 0.15 - 2e-3, `${p.id}: the colour kick is not white`);
    const a = PAL.lumaOf(PAL.hexToLin(hx.kick)), b = PAL.lumaOf(PAL.hexToLin(hx.highlight));
    assert.ok(Math.min(a, b) / Math.max(a, b) >= 0.80 - 5e-3, `${p.id}: ladder ratio ${(Math.min(a, b) / Math.max(a, b)).toFixed(2)}`);
  }
});

// --------------------------------------------------------------------------------------------- the switch --
test("a palette change lands on the next 16-bar line: a neighbour crossfades its roles in OKLCh over 4 bars from the line, anything else dips the rig to black for a beat and changes at the bottom", () => {
  assert.equal(PAL.landingPos(0.5, 0), 64); assert.equal(PAL.landingPos(63.9, 0), 64); assert.equal(PAL.landingPos(64, 0), 128);
  assert.equal(PAL.landingPos(70, 2), 130);
  const sv = LIB.byId["source-violet"], dc = LIB.byId["dreaming-city"], gl = LIB.byId.glacier, lr = LIB.byId["lime-rows"];
  assert.equal(PAL.needsDip(sv, dc, WHEEL_HEX), false, "Source Violet and Dreaming City are neighbours");
  assert.equal(PAL.needsDip(sv, gl, WHEEL_HEX), true, "violet to glacier dips");
  assert.equal(PAL.needsDip(sv, lr, WHEEL_HEX), true, "a split always dips");
  // the crossfade
  {
    const g = locked(), p = fresh("source-violet", "groove");
    const to = resolveTheme(PAL.stageTheme(dc));
    p.beginPalette(PAL.stageTheme(dc), 64, { beats: 16, dip: false });
    const A = [];
    play(p, g, 0, 84, (pos) => A.push([pos, p.roleRGB[ROLE.A].slice(), p.dipLevel]));
    const at = (b) => A.find(([pos]) => pos >= b)[1];
    assert.ok(PAL.deOK(at(63), resolveTheme(PAL.stageTheme(sv)).A) < 1e-6, "before the line: Source Violet");
    const mid = at(72);
    assert.ok(PAL.deOK(mid, to.A) > 0.03 && PAL.deOK(mid, resolveTheme(PAL.stageTheme(sv)).A) > 0.03, "half way: between the two");
    assert.ok(PAL.deOK(at(81), to.A) < 1e-6, "after 4 bars: Dreaming City");
    assert.ok(A.every(([, , d]) => d === 1), "a crossfade never dims");
    let worst = 0;
    for (let i = 1; i < A.length; i++) worst = Math.max(worst, PAL.deOK(A[i][1], A[i - 1][1]));
    assert.ok(worst < 0.01, `smooth: the largest frame-to-frame step dEOK ${worst.toFixed(4)}`);
    assert.equal(p.palette.id, "dreaming-city");
    assert.equal(p.effects.get("strand.cubes:cube-colour").phasor.measure, 32, "Dreaming City's slow helix: 32 beats a turn");
  }
  // the dip
  {
    const g = locked(), p = fresh("source-violet", "groove");
    p.beginPalette(PAL.stageTheme(gl), 64, { dip: true });
    const rows = [];
    play(p, g, 0, 70, (pos) => rows.push({ pos, dip: p.dipLevel, A: p.roleRGB[ROLE.A].slice(), heads: Array.from({ length: p.nH }, (_, i) => [p.wheelSlotOf(i), p.heads[i * HEAD_FLOATS + H.DIM]]) }));
    const at = (b) => rows.find((r) => r.pos >= b);
    assert.equal(at(63).dip, 1); assert.ok(at(63.9).dip < 0.2 && at(64.02).dip < 0.05, "black at the line"); assert.equal(at(65).dip, 1);
    assert.ok(PAL.deOK(at(63.9).A, resolveTheme(PAL.stageTheme(sv)).A) < 1e-6 && PAL.deOK(at(64.05).A, resolveTheme(PAL.stageTheme(gl)).A) < 1e-6, "the colours change at the bottom");
    // every head's wheel changed while it was dark
    let litMoves = 0;
    for (let k = 1; k < rows.length; k++) rows[k].heads.forEach(([s, d], i) => { if (s !== rows[k - 1].heads[i][0] && d > 0.02) litMoves++; });
    assert.equal(litMoves, 0, "no wheel turned while its head was lit");
    assert.equal(p.palette.id, "glacier");
  }
});

test("the switch's controls: the set maps KeyLab pads 11 and 12 to palette-next and palette-prev, the page answers them and key P, the phone bar has a PALETTE pad and the colour strip wears the lift colours", () => {
  assert.equal(SCENE.show.pads["11"], "palette-next");
  assert.equal(SCENE.show.pads["12"], "palette-prev");
  const page = readFileSync(new URL("../arsenal/web/stage/stage.js", import.meta.url), "utf8");
  assert.match(page, /action === "palette-next" && on\) stepPal\(1, tEval\)/);
  assert.match(page, /action === "palette-prev" && on\) stepPal\(-1, tEval\)/);
  assert.match(page, /e\.code === "KeyP"\) stepPal\(e\.shiftKey \? -1 : 1, tEval\)/);
  assert.match(page, /const at = landingPos\(pos, grid\.barAnchor \|\| 0, 16\)/);
  const pad = STAGE_PADS.find((x) => x.code === "KeyP");
  assert.ok(pad && pad.palette && pad.label === "palette");
  assert.equal(STAGE_STRIPS.find((x) => x.pad === 5).tint, "ladder");
  assert.equal(typeof mountTouchBar, "function");
  assert.equal(PAL.stepPalette(LIB, "noir", 1), "source-violet", "the step wraps round the library");
  assert.equal(PAL.stepPalette(LIB, "source-violet", -1), "noir");
});

// ------------------------------------------------------------------------------------- splits, pins, ramps, tempo --
test("splits and pins: Lime Rows' rows rest on lime and kick to green, Neomuna's second backbone is its pink wing, Dreaming City's window pin holds (never kicked, never chased)", () => {
  {
    const g = locked(), p = fresh("lime-rows", "drop");
    play(p, g, 0, 8);
    const truss = RIG.groups["truss.heads"].members;
    for (const i of truss) assert.equal(p.wheelSlotOf(i), 4, "the truss rests on lime");
    force(p, "beams");
    let rec = null;
    play(p, g, 8, 12, (pos) => { if (!rec && pos >= 8.1) rec = p.pad(C, 0.8, pos, { hold: true }); });
    for (const i of truss) assert.equal(p.wheelSlotOf(i), 5, "and kicks to green");
    const strips = RIG.groups["vert.strips"].members;
    assert.ok(Array.from(strips).every((c) => p.cellKind[c] === CELL_KIND.ACCENT), "the tower strips are the lime accent");
  }
  {
    const p = fresh("neomuna-neon", "drop"), g = locked();
    play(p, g, 0, 6);
    const cubes = RIG.groups["strand.cubes"];
    let a = 0, b = 0;
    for (let m = 0; m < cubes.n; m++) { if (cubes.keys.side[m] > 0) { b++; assert.equal(p.cellKind[cubes.members[m]], CELL_KIND.ACCENT); } else { a++; assert.equal(p.cellKind[cubes.members[m]], CELL_KIND.BED); } }
    assert.ok(a > 0 && b > 0);
    const pink = PAL.lchOf("#e250b5").h;
    let wingB = 0, n = 0;
    for (let m = 0; m < cubes.n; m += 5) if (cubes.keys.side[m] > 0) { const c = cellRGB(p, cubes.members[m]); if (c) { n++; if (PAL.hueGap(PAL.lchOfLin(c).h, pink) < 25) wingB++; } }
    assert.ok(n > 0 && wingB / n > 0.95, `the second backbone is pink: ${wingB} of ${n}`);
  }
  {
    const g = locked(), p = fresh("dreaming-city", "drop");
    const pins = Array.from(RIG.groups["strips.v1"].members);
    assert.ok(pins.every((c) => p.cellKind[c] === CELL_KIND.PIN));
    // a strobing chase on the pin's cells (as a phrase would run): the pin only follows slowly
    let worst = 0, last = null;
    play(p, g, 0, 12, (pos) => {
      const on = Math.floor(pos * 4) % 2 === 0 ? 1 : 0;              // eight flashes a beat asked of the pin
      for (const c of pins) p.baseC[c * 4] = on;
      const lv = p.pixels[pins[0] * 4 + 3];
      if (last !== null && pos > 1) worst = Math.max(worst, Math.abs(lv - last));
      last = lv;
    });
    assert.ok(worst < 0.03, `the pin holds: its level moves at most ${worst.toFixed(3)} a frame`);
    const pinHex = PAL.stageTheme(LIB.byId["dreaming-city"]).pin;
    const col = cellRGB(p, pins[0]);
    assert.ok(PAL.deOK(col, PAL.hexToLin(pinHex)) < 0.01, "in the pin's colour");
    const card = KICK.kickConfig(RIG).cards.find((c) => c.name === "beams");
    assert.ok(pins.every((c) => Array.from(card.cells).includes(c)), "the pin's cells sit in the beams' area");
    // held steady, then a kick on the beams (the area the pin's cells sit in)
    for (const c of pins) p.baseC[c * 4] = 0.6;
    play(p, g, 12, 40);
    force(p, "beams");
    const before = pins.map((c) => p.pixels[c * 4 + 3]);
    let r = null;
    play(p, g, 40, 42, (pos) => { if (!r && pos >= 40.1) r = p.pad(C, 1, pos, { hold: true }); });
    assert.equal(r.card.name, "beams");
    const after = pins.map((c) => p.pixels[c * 4 + 3]);
    assert.ok(after.every((x, i) => Math.abs(x - before[i]) < 0.05), "a kick on the beams leaves the pin as it was");
  }
});

test("3-stop strands sample the palette's own gradient (Lantern Walk, Aurora); Lantern Walk's bed walks a stop per 16-bar phrase; the tempo turns the helix at the palette's rate", () => {
  for (const id of ["lantern-walk", "aurora-borealis"]) {
    const p = fresh(id, "drop");
    assert.ok(p.ramp3, `${id}: a 3-stop strand table`);
    const sg = LIB.byId[id].gradients.find((g) => g.name === "strand");
    const mid = p.colourOfCell(RIG.groups["strand.cubes"].members[0], ROLE.A, ROLE.B, 0.5);
    assert.ok(PAL.deOK(mid, PAL.hexToLin(sg.stops[1].hex)) < 0.03, `${id}: the strand's middle is its mid stop ${sg.stops[1].hex}`);
  }
  assert.equal(fresh("source-violet").ramp3, null, "two stops keep the linear mix that made the loved helix");
  const g = locked(), p = fresh("lantern-walk", "groove");
  const seen = [];
  play(p, g, 0, 64 * 3 + 1, (pos) => { if (Math.abs(pos % 64 - 32) < 0.02) seen.push(PAL.linToHex(p.roleRGB[ROLE.A])); });
  assert.deepEqual(seen.slice(0, 3), LIB.byId["lantern-walk"].walk.slice(0, 3), "the bed walks one stop a phrase");
  for (const [id, m] of [["source-violet", 16], ["dreaming-city", 32], ["acid-raw", 8], ["source-ring", 32]]) {
    const q = fresh(id, "groove");
    assert.equal(q.effects.get("strand.cubes:cube-colour").phasor.measure, m, `${id}: the helix turns once in ${m} beats`);
  }
  assert.equal(fresh("source-ring", "groove").effects.get("rings.slats:ring-colour").phasor.measure, 64, "Source Ring's ladder is held (one turn in 16 bars)");
});

test("the lasers: a fan of the palette's first two colours is a gradient per beam; a red laser falls back to the palette's white, never to a warm white", () => {
  const pal = LIB.byId["source-violet"];
  const e = new LaserEngine({ seed: 7, colours: pal.lasers, heads: extraHeadsFrom(RIG.projectors) });
  const ramp = PAL.tableOf(pal.gradients.find((x) => x.name === "lasers"));
  e.setColours(pal.lasers, { white: PAL.hexToLin(pal.stage_theme.W), fanRamp: ramp });
  e.out.n = 0;
  e._fan(0, Math.PI / 2, 0.6, 5, 0, 1);
  const segs = Array.from({ length: e.out.n }, (_, k) => [e.out.seg[k * SEG_FLOATS + SEG.R], e.out.seg[k * SEG_FLOATS + SEG.G], e.out.seg[k * SEG_FLOATS + SEG.B]]);
  assert.equal(segs.length, 5);
  assert.ok(PAL.deOK(segs[0], PAL.hexToLin(pal.lasers[0])) < 0.01 && PAL.deOK(segs[4], PAL.hexToLin(pal.lasers[1])) < 0.01, "from the first colour to the second across the fan");
  assert.ok(PAL.deOK(segs[2], segs[0]) > 0.03 && PAL.deOK(segs[2], segs[4]) > 0.03, "a colour of its own in the middle");
  const r = new LaserEngine({ seed: 7, colours: ["#ff1010", "#ff2010", "#ff0000"] });
  r.setColours(["#ff1010", "#ff2010", "#ff0000"], { white: PAL.hexToLin("#f0eaff") });
  for (const c of r.palette) assert.ok(PAL.deOK(c, PAL.hexToLin("#f0eaff")) < 1e-6, "the palette's white");
});
