// Virtual Stage, KICK v2 (arsenal/web/stage/kick.js through programmer.js). node --test tests/stage_kick.test.mjs
//
// Daniel, 2026-10-27, on the phone bar: "Hitting kick sometimes had an impact at other times nothing changed"; then "Can
// we make kick trigger different rows of lights and or lasers with a peak in brightness or a row turning on and panning,
// it could be also lit for duration of press and on keylab velocity can change parameters too"; then "lets make it a
// vertically longer button that presses and holds the light while the finger is on it and you can sweep up and down to
// adjust brightness! Lets have two kick buttons with vertical "velocity" one kick for white one kick for color, you can
// press both at same time and two rows can light up at once!"
//
// The first test is the pinned acceptance: NO DEAD KICKS. It was written before kick.js and run on the code that was
// there (the strand-only lift) to show it red; it imports nothing from kick.js and owns its own definition of visible.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { Programmer, H, HEAD_FLOATS, ROLE_NAMES } from "../arsenal/web/stage/programmer.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import { FrameLimiter } from "../arsenal/web/stage/flash.js";

let KICK = null;
try { KICK = await import("../arsenal/web/stage/kick.js"); } catch { KICK = null; }

const SCENE1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const SCENE0 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const RIG1 = expandScene(SCENE1);
const RIG0 = expandScene(SCENE0);
const THEME1 = { name: "source-violet", ...SCENE1.themes["source-violet"] };
const THEME0 = { name: "source-violet", ...SCENE0.themes["source-violet"] };
const FPS = 60, DT = 1 / FPS;

function locked(bpm) {
  const g = new BeatGrid({ bpm, t0: 0 });
  g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  return g;
}

// ------------------------------------------------------------------------------------------ what "visible" means --
// A press is VISIBLE when the row it lit shows, within one beat of the press, either
//   an intensity lift: the row's mean rendered level (heads: the dimmer after the motor; LED cells: the cell's level),
//   with the kick minus the same frame without it, of at least 0.15 (the simulation that found the dead kicks called
//   a press dead under 0.10; 0.15 is half again that, a sixth of the whole range, on every member of the row on average);
//   or, for the WHITE kick only, a shift toward white: the row's mean drop in HSV saturation of the rendered colour
//   (sRGB-encoded, as the screen shows it), counted on members lit to 0.1 or more and averaged over the whole row, of at
//   least 0.20. On the theme's violet A (#7a3cff, saturation 0.76) a drop of 0.20 is the step to #936fff, CIE76 dE 31; on
//   its pink B (#ff38d8) dE 19, on warm (#ffb86a) dE 21 (a just-noticeable difference is about 2.3): a colour change
//   nobody misses, and it is the case where the row is already at full and has no intensity left to give. (The white kick
//   itself goes all the way to the theme's white, #f0eaff: dE 61 to 110 from those colours.)
// The COLOUR kick paints the theme's colour, not white, so only the lift counts for it: it must find a row whose level in
// that look leaves headroom (a dark row, or one lit low enough), which is the dealer's job.
const LIFT = 0.15, WHITE = 0.2;
const srgb = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
function satOf(r, g, b) {
  const R = srgb(Math.max(0, r)), G = srgb(Math.max(0, g)), B = srgb(Math.max(0, b));
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B);
  return mx > 1e-6 ? (mx - mn) / mx : 0;
}
// the rows a press lit: KICK v2 returns them on the press's record; the code before it lifted the strand (its heads and
// its cubes), and that is what is measured for it
function rowsOf(rec, p) {
  if (rec && rec.card) return [{ name: rec.card.name, heads: Array.from(rec.card.heads), cells: Array.from(rec.card.cells) }];
  const heads = [], cells = [];
  for (let i = 0; i < p.nH; i++) if (p.strandHead[i]) heads.push(i);
  for (let c = 0; c < p.nC; c++) if (p.strandCell[c] && p.rig.cells.kind[c] === 2) cells.push(c);
  return [{ name: "strand.heads", heads, cells: [] }, { name: "strand.cubes", heads: [], cells }];
}
function rowNow(pW, pB, row) {
  let lift = 0, white = 0, n = 0;
  for (const i of row.heads) {
    const o = i * HEAD_FLOATS, dW = pW.heads[o + H.DIM], dB = pB.heads[o + H.DIM];
    lift += dW - dB;
    if (dW >= 0.1) white += satOf(pB.heads[o + H.R], pB.heads[o + H.G], pB.heads[o + H.B]) - satOf(pW.heads[o + H.R], pW.heads[o + H.G], pW.heads[o + H.B]);
    n++;
  }
  for (const c of row.cells) {
    const b = c * 4, aW = pW.pixels[b + 3], aB = pB.pixels[b + 3];
    lift += aW - aB;
    if (aW >= 0.1) {
      const sB = aB > 1e-4 ? satOf(pB.pixels[b] / aB, pB.pixels[b + 1] / aB, pB.pixels[b + 2] / aB) : satOf(...colourOfCell(pB, c));
      white += sB - satOf(pW.pixels[b] / aW, pW.pixels[b + 1] / aW, pW.pixels[b + 2] / aW);
    }
    n++;
  }
  return n ? { lift: lift / n, white: white / n } : { lift: 0, white: 0 };
}
// a dark cell's colour (its level is zero, so the pixels carry none): its roles and mix
function colourOfCell(p, c) {
  const b = c * 4, mix = Math.max(0, Math.min(1, p.tC[b + 1]));
  const c1 = p.roleRGB[p.tC[b + 2] | 0], c2 = p.roleRGB[p.tC[b + 3] | 0];
  return [c1[0] + (c2[0] - c1[0]) * mix, c1[1] + (c2[1] - c1[1]) * mix, c1[2] + (c2[2] - c1[2]) * mix];
}

// One look, one tempo: a run with no presses (the baseline) and, in lockstep, one run per kick kind with 20 presses at
// velocity 0.8, three beats apart (every earlier kick has died away), at phases 0, 1/20, ..., 19/20 of their beat. Each
// press is held a quarter of a beat (a keyboard tap) and measured over the beat after it.
function pressRun(look, bpm, kinds) {
  const g = locked(bpm);
  const base = new Programmer(RIG1, { theme: THEME1, seed: 7 });
  base.setLook(look, 0);
  const runs = kinds.map((kind) => { const p = new Programmer(RIG1, { theme: THEME1, seed: 7 }); p.setLook(look, 0); return { kind, p, next: 0, cur: null, out: [] }; });
  const at = (k) => 8 + 3 * k + k / 20;
  for (let f = 0; f < FPS * 600; f++) {
    const t = f * (1000 / FPS), pos = g.posAt(t);
    for (const r of runs) {
      const v2 = typeof r.p.padRelease === "function";
      if (r.next < 20 && pos >= at(r.next)) {
        const rec = r.p.pad(v2 ? r.kind : "kick", 0.8, pos, { hold: true });
        r.cur = { k: r.next, phase: r.next / 20, pos, rows: rowsOf(rec, r.p).map((row) => ({ ...row, lift: 0, white: 0 })), rel: !v2 };
        r.next++;
      }
      if (r.cur && !r.cur.rel && pos >= r.cur.pos + 0.25) { r.p.padRelease(r.kind, pos); r.cur.rel = true; }
    }
    base.tick(g, t, DT);
    for (const r of runs) r.p.tick(g, t, DT);
    let busy = false;
    for (const r of runs) {
      if (!r.cur) { busy = busy || r.next < 20; continue; }
      busy = true;
      for (const row of r.cur.rows) { const v = rowNow(r.p, base, row); row.lift = Math.max(row.lift, v.lift); row.white = Math.max(row.white, v.white); }
      if (pos > r.cur.pos + 1) { r.out.push(r.cur); r.cur = null; }
    }
    if (!busy) break;
  }
  return runs.map((r) => ({ kind: r.kind, presses: r.out.map((c) => {
    const best = c.rows.reduce((a, row) => (row.lift > a.lift ? row : a), c.rows[0]);
    const vis = c.rows.some((row) => row.lift >= LIFT || (r.kind === "kick-white" && row.white >= WHITE));
    return { k: c.k, phase: c.phase, rows: c.rows.map((row) => row.name).join("+"), lift: +best.lift.toFixed(3),
             white: +Math.max(...c.rows.map((row) => row.white)).toFixed(3), visible: vis };
  }) }));
}

test("no dead kicks: in every look of source-v1, both kicks pressed at 20 phases across a beat at velocity 0.8 change what is seen, every press", () => {
  const looks = Object.keys(SCENE1.looks);
  assert.ok(["intro", "build", "drop", "break"].every((l) => looks.includes(l)), `the set's looks: ${looks}`);
  const table = [], dead = [];
  for (const bpm of [128, 150]) {
    for (const look of looks) {
      for (const run of pressRun(look, bpm, ["kick-white", "kick-colour"])) {
        const d = run.presses.filter((x) => !x.visible);
        const minLift = Math.min(...run.presses.map((x) => x.lift));
        table.push(`${String(bpm).padStart(3)} BPM ${look.padEnd(6)} ${run.kind.padEnd(11)} dead ${String(d.length).padStart(2)}/20  min lift ${minLift.toFixed(2)}  rows ${[...new Set(run.presses.map((x) => x.rows))].join(", ")}`);
        for (const x of d) dead.push(`${bpm} ${look} ${run.kind} phase ${x.phase.toFixed(2)}: ${x.rows} lift ${x.lift} white ${x.white}`);
        assert.equal(run.presses.length, 20, `${look} ${run.kind}: 20 presses measured`);
      }
    }
  }
  console.log(`  no dead kicks (lift >= ${LIFT}, or for the white kick a shift toward white >= ${WHITE}):\n  ${table.join("\n  ")}`);
  assert.deepEqual(dead, [], `dead presses:\n${dead.slice(0, 24).join("\n")}`);
});

// ----------------------------------------------------------------------------------------------- the rest of v2 --
const need = () => assert.ok(KICK, "arsenal/web/stage/kick.js is there");
const W = "kick-white", C = "kick-colour";
function fresh({ rig = RIG1, theme = THEME1, look = "drop", seed = 7 } = {}) {
  const p = new Programmer(rig, { theme, seed });
  p.setLook(look, 0);
  return p;
}
// tick a programmer from beat a to beat b (60 fps) on grid g, calling each(pos, t) before every tick
function play(p, g, a, b, each = null) {
  const per = g.period;
  for (let t = a * per; t < b * per; t += 1000 / FPS) {
    const pos = g.posAt(t);
    if (each) each(pos, t);
    p.tick(g, t, DT);
  }
}
const rowLevel = (p, card) => {
  let s = 0, n = 0;
  for (const i of card.heads) { s += p.heads[i * HEAD_FLOATS + H.DIM]; n++; }
  for (const c of card.cells) { s += p.pixels[c * 4 + 3]; n++; }
  return n ? s / n : 0;
};

test("the deck: seeded and deterministic, never the same row twice running for a kick, and no row again until the deck has gone round", () => {
  need();
  const deal = (seed) => {
    const g = locked(150), p = fresh({ look: "intro", seed });
    const rows = [], rounds = [];
    let k = 0;
    play(p, g, 0, 200, (pos) => {
      if (pos >= 4 + 2 * k && k < 90) {
        const kind = k % 3 === 2 ? C : W;
        const rec = p.pad(kind, 0.6, pos, { hold: true });
        rows.push({ kind, name: rec.card.name, round: rec.round });
        p.padRelease(kind, pos + 0.01);
        k++;
      }
    });
    return rows;
  };
  const a = deal(7), b = deal(7), c = deal(8);
  assert.deepEqual(a.map((x) => x.name), b.map((x) => x.name), "the same seed deals the same rows");
  assert.notDeepEqual(a.map((x) => x.name), c.map((x) => x.name), "another seed deals another order");
  for (const kind of [W, C]) {
    const mine = a.filter((x) => x.kind === kind);
    for (let i = 1; i < mine.length; i++) assert.notEqual(mine[i].name, mine[i - 1].name, `${kind}: the same row twice running at deal ${i}`);
  }
  for (let i = 1; i < a.length; i++) assert.notEqual(a[i].name, a[i - 1].name, `the deck dealt ${a[i].name} twice running`);
  // inside one round of the deck no row comes twice (a row skipped as not visible stays in the round for later)
  const byRound = new Map();
  for (const x of a) { const s = byRound.get(x.round) || []; assert.ok(!s.includes(x.name), `round ${x.round}: ${x.name} twice`); s.push(x.name); byRound.set(x.round, s); }
  const cards = KICK.kickConfig(RIG1).cards.length;
  assert.ok(byRound.size >= Math.floor(a.length / cards), `${byRound.size} rounds for ${a.length} deals of ${cards} cards`);
  assert.ok(new Set(a.map((x) => x.name)).size >= cards - 2, `the deck reaches its rows: ${[...new Set(a.map((x) => x.name))].join(", ")}`);
});

// a card by name (the receipts' door deals it next: p.kick.deck.forceNext)
const cardIx = (name) => KICK.kickConfig(RIG1).cards.findIndex((c) => c.name === name);
const force = (p, name) => { const i = cardIx(name); assert.ok(i >= 0, `the deck has ${name}`); p.kick.deck.forceNext = i; };

test("hold = gate: a held kick stays lit at its level for as long as it is held, then fades in about a third of a beat; a tap is a quick hit", () => {
  need();
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "delay.30");                                       // a head row no look lights: the kick alone on it
  let rec = null;
  const lv = [];
  play(p, g, 0, 20, (pos) => {
    if (!rec && pos >= 6) rec = p.pad(W, 0.7, pos, { hold: true });
    if (rec && rec.releasedAt === null && pos >= 14) p.padRelease(W, pos);
    if (rec) lv.push([pos, rowLevel(p, rec.card)]);
  });
  assert.equal(rec.card.name, "delay.30");
  const held = lv.filter(([pos]) => pos >= 6.3 && pos < 14);
  const lo = Math.min(...held.map((x) => x[1])), hi = Math.max(...held.map((x) => x[1]));
  assert.ok(lo > 0.69 && hi < 0.71, `held for 8 beats at level 0.7 the row stayed in ${lo.toFixed(3)}..${hi.toFixed(3)}`);
  const at = (b) => lv.find(([pos]) => pos >= b)[1];
  assert.ok(at(14.3) < at(14) * 0.45 && at(14.3) > at(14) * 0.2, `released at 14: ${at(14).toFixed(3)} -> ${at(14.3).toFixed(3)} a third of a beat later (1/e = 0.37)`);
  assert.ok(at(16) < 0.01, `two beats after the release it is gone: ${at(16).toFixed(4)}`);
  // a tap: pressed and released at once, a tenth of a beat early: it lights on its line and holds an eighth of a beat
  const p2 = fresh({ look: "break" });
  force(p2, "delay.55");
  let r2 = null; const lv2 = [];
  play(p2, locked(150), 0, 12, (pos) => {
    if (!r2 && pos >= 7.9) { r2 = p2.pad(W, 0.9, pos, { hold: true }); p2.padRelease(W, pos); }
    if (r2) lv2.push([pos, rowLevel(p2, r2.card)]);
  });
  const peak = Math.max(...lv2.map((x) => x[1]));
  const lit = lv2.filter((x) => x[1] > 0.5 * peak);
  assert.ok(peak > 0.89 && peak <= 0.9 + 1e-9, `the tap peaked at its level: ${peak.toFixed(3)}`);
  assert.ok(lit[0][0] >= 8 - 1e-9 && lit[0][0] < 8.1, `an early tap waits for its line: lit from ${lit[0][0].toFixed(3)}`);
  assert.ok(lit.at(-1)[0] > 8.125 && lit.at(-1)[0] < 8.125 + 0.3, `then holds an eighth of a beat and fades: lit until ${lit.at(-1)[0].toFixed(3)}`);
  assert.equal(p2.stats.kicks.at(-1), 8);
});

test("velocity picks the animation: soft = a peak (the heads stay put), medium = a sweep, hard = a sweep with twice the throw, within the tilt motor", () => {
  need();
  const cfg = KICK.kickConfig(RIG1);
  const band = (v) => KICK.bandFor(cfg, v).name;
  assert.equal(band(0), "peak"); assert.equal(band(0.44), "peak");
  assert.equal(band(0.45), "sweep"); assert.equal(band(0.8), "sweep");
  assert.equal(band(0.85), "drive"); assert.equal(band(1), "drive");
  // on a head row: the tilt the motor shows, with and without the kick
  const tiltSwing = (vel) => {
    const g = locked(150), p = fresh({ look: "intro" }), b = fresh({ look: "intro" });
    force(p, "truss.heads");
    let rec = null, swing = 0;
    for (let t = 0; t < 16 * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && pos >= 8) rec = p.pad(C, vel, pos, { hold: true });
      p.tick(g, t, DT); b.tick(g, t, DT);
      if (rec) for (const i of rec.card.heads) swing = Math.max(swing, Math.abs(p.heads[i * HEAD_FLOATS + H.TILT] - b.heads[i * HEAD_FLOATS + H.TILT]));
    }
    return { swing, rec };
  };
  const soft = tiltSwing(0.3), med = tiltSwing(0.7), hard = tiltSwing(0.9);
  assert.equal(soft.rec.card.name, "truss.heads");
  assert.equal(soft.rec.band, "peak"); assert.equal(soft.rec.motion, null);
  assert.ok(soft.swing < 0.5, `a peak leaves the heads where they are (${soft.swing.toFixed(2)} deg)`);
  assert.equal(med.rec.band, "sweep"); assert.equal(hard.rec.band, "drive");
  assert.ok(med.rec.motion && med.swing > 4, `a sweep moves them (${med.swing.toFixed(1)} deg, ${med.rec.motion && med.rec.motion.id})`);
  assert.ok(hard.rec.motion && hard.swing > 4, `a hard sweep moves them (${hard.swing.toFixed(1)} deg, ${hard.rec.motion && hard.rec.motion.id})`);
  // the hard band asks twice the throw at the same velocity; the motor may cut both, never the hard one below the medium one
  assert.ok(Math.abs(KICK.bandFor(cfg, 0.9).sweep.deg / KICK.bandFor(cfg, 0.7).sweep.deg - 2) < 1e-9, "drive is twice sweep");
  assert.ok(hard.rec.motion.want > 1.5 * med.rec.motion.want, `asked: ${hard.rec.motion.want.toFixed(1)} vs ${med.rec.motion.want.toFixed(1)} deg`);
  assert.ok(hard.rec.motion.deg >= med.rec.motion.deg - 1e-9, `thrown: ${hard.rec.motion.deg.toFixed(1)} vs ${med.rec.motion.deg.toFixed(1)} deg`);
  // the motor: no sweep asks a tilt faster than 80 % of the head's motor (270 deg in 1.4 s)
  for (const r of [med.rec, hard.rec]) assert.ok(r.motion.peakDegPerS <= (270 / 1.4) * 0.8 + 1e-6, `${r.motion.id}: ${r.motion.peakDegPerS.toFixed(0)} deg/s asked`);
  // and on an LED row the sweep bands chase: the members' levels differ along the row while it is held
  const g = locked(150), p = fresh({ look: "intro" });
  force(p, "rings.r0.slats");
  let rec = null, spread = 0;
  play(p, g, 0, 16, (pos) => {
    if (!rec && pos >= 8) rec = p.pad(W, 0.7, pos, { hold: true });
    if (rec && pos > 9) {
      let lo = 1, hi = 0;
      for (const c of rec.card.cells) { const a = p.pixels[c * 4 + 3]; lo = Math.min(lo, a); hi = Math.max(hi, a); }
      spread = Math.max(spread, hi - lo);
    }
  });
  assert.ok(rec.motion && spread > 0.15, `the chase runs along the ring (level spread ${spread.toFixed(2)})`);
});

test("two kicks at once: white and colour held together light two different rows, never one row twice; white goes white, colour stays a colour", () => {
  need();
  const g = locked(150), p = fresh({ look: "drop" });
  const pairs = [];
  let k = 0;
  play(p, g, 0, 4 + 50 * 4, (pos) => {
    const slot = Math.floor((pos - 4) / 4);
    if (pos >= 4 && slot === k && k < 50) {
      const w = p.pad(W, 0.55 + 0.35 * ((k * 7) % 10) / 10, pos, { hold: true });
      const c = p.pad(C, 0.5 + 0.4 * ((k * 3) % 10) / 10, pos + 0.01, { hold: true });
      pairs.push({ w, c, at: pos, checked: false, released: false });
      k++;
    }
    const cur = pairs.at(-1);
    if (cur && !cur.checked && pos >= cur.at + 1) {
      cur.checked = true;
      cur.lw = rowLevel(p, cur.w.card); cur.lc = rowLevel(p, cur.c.card);
      cur.sw = meanSat(p, cur.w.card, true); cur.sc = meanSat(p, cur.c.card, true);
      cur.live = p.kick.list.filter((x) => x.held).map((x) => x.card.name);
    }
    if (cur && cur.checked && pos >= cur.at + 2 && !cur.released) { p.padRelease(W, pos); p.padRelease(C, pos); cur.released = true; }
  });
  assert.equal(pairs.length, 50);
  const rows = new Set();
  for (const x of pairs) {
    assert.notEqual(x.w.card.name, x.c.card.name, `pair at ${x.at.toFixed(2)}: one row twice`);
    assert.deepEqual(x.live.sort(), [x.w.card.name, x.c.card.name].sort(), "both held at once");
    assert.ok(x.lw > 0.25 && x.lc > 0.25, `both rows lit: ${x.w.card.name} ${x.lw.toFixed(2)}, ${x.c.card.name} ${x.lc.toFixed(2)}`);
    if (x.w.card.cells.length) assert.ok(x.sw < 0.2, `white row ${x.w.card.name}: its LEDs at saturation ${x.sw.toFixed(2)}`);
    if (x.c.card.cells.length) assert.ok(x.sc > 0.3, `colour row ${x.c.card.name}: its LEDs at saturation ${x.sc.toFixed(2)}`);
    rows.add(x.w.card.name); rows.add(x.c.card.name);
  }
  assert.ok(rows.size >= 8, `the two buttons went round the stage: ${[...rows].join(", ")}`);
});
test("a row still fading is not the other button's: forced at it, the colour kick is dealt another row; the same button's re-press may take its own", () => {
  need();
  const g = locked(150), p = fresh({ look: "break" });
  let w = null, c = null, w2 = null;
  play(p, g, 0, 12, (pos) => {
    if (!w && pos >= 6) { force(p, "delay.30"); w = p.pad(W, 0.8, pos, { hold: true }); }
    if (w && w.releasedAt === null && pos >= 7) p.padRelease(W, pos);
    if (w && !c && pos >= 7.2) { force(p, "delay.30"); c = p.pad(C, 0.8, pos, { hold: true }); }
    if (c && !w2 && pos >= 7.3) { force(p, "delay.30"); w2 = p.pad(W, 0.8, pos, { hold: true }); }
  });
  assert.equal(w.card.name, "delay.30");
  assert.notEqual(c.card.name, "delay.30", "the colour kick never takes the white kick's fading row");
  assert.equal(w2.card.name, "delay.30", "the white button's re-press takes its own fading row over");
  assert.ok(w.dead, "and the old kick on it has gone");
});
function meanSat(p, card, cellsOnly = false) {
  let s = 0, n = 0;
  for (const c of card.cells) { const a = p.pixels[c * 4 + 3]; if (a < 0.1) continue; s += satOf(p.pixels[c * 4] / a, p.pixels[c * 4 + 1] / a, p.pixels[c * 4 + 2] / a); n++; }
  if (!cellsOnly) for (const i of card.heads) { const o = i * HEAD_FLOATS; if (p.heads[o + H.DIM] < 0.1) continue; s += satOf(p.heads[o + H.R], p.heads[o + H.G], p.heads[o + H.B]); n++; }
  return n ? s / n : 0;
}

test("live level while held: padLevel moves the held row's brightness with the finger, monotone and slewed (no zipper)", () => {
  need();
  const g = locked(128), p = fresh({ look: "intro" });
  force(p, "delay.30");
  let rec = null, si = 0;
  const steps = [[8, 0.2], [10, 0.4], [12, 0.6], [14, 0.8], [16, 0.9]];
  const seen = [];
  play(p, g, 0, 18.5, (pos) => {
    if (!rec && pos >= 7) rec = p.pad(W, 0.3, pos, { hold: true });
    if (si < steps.length && pos >= steps[si][0]) { p.padLevel(W, steps[si][1]); si++; }
    if (rec) seen.push([pos, rowLevel(p, rec.card)]);
  });
  assert.equal(rec.card.name, "delay.30");
  const settled = steps.map(([b, v]) => [v, seen.filter(([pos]) => pos > b + 1.5 && pos < b + 1.9).map((x) => x[1])]);
  for (const [v, xs] of settled) assert.ok(xs.length && xs.every((x) => Math.abs(x - v) < 0.01), `level ${v}: the row settled at ${xs[0] && xs[0].toFixed(3)}`);
  for (let i = 1; i < settled.length; i++) assert.ok(settled[i][1][0] > settled[i - 1][1][0], "brighter with every step up");
  // slewed: no frame jumps more than a third of a 0.2 step (a zipper would jump it all in one frame)
  let worst = 0;
  for (let i = 1; i < seen.length; i++) if (seen[i][0] > 8) worst = Math.max(worst, Math.abs(seen[i][1] - seen[i - 1][1]));
  assert.ok(worst < 0.2 / 3, `the largest one-frame step ${worst.toFixed(3)}`);
  // and it gets there in about a tenth of a second
  const t10 = seen.find(([pos, x]) => pos > 12 && x >= 0.6 - 0.02)[0];
  assert.ok((t10 - 12) * g.period < 200, `0.4 -> 0.6 within ${((t10 - 12) * g.period).toFixed(0)} ms`);
  // a level for a button that is not held changes nothing
  p.padLevel(C, 0.1);
  assert.ok(p.kick.list.every((x) => x.kind !== C));
});

test("the strobe: only while the live level is in the top band (>= 0.95), on and off as the level crosses it, never more than 4 edges in any 1.01 s, and the limiter never has to act on it", () => {
  need();
  const report = [];
  for (const bpm of [100, 128, 150, 174]) {
    const g = locked(bpm), p = fresh({ look: "break" });
    force(p, "delay.30");
    let rec = null;
    const series = [];
    // held at 0.9 for 4 s, then 1.0 for 6 s, then back to 0.9 for 3 s, then released
    const tA = 2000, tB = tA + 4000, tC = tB + 6000, tD = tC + 3000;
    const marks = [[tB, 1], [tC, 0.9]];
    let mi = 0, released = false;
    for (let t = 0; t < tD + 2000; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && t >= tA) rec = p.pad(W, 0.9, pos, { hold: true });
      if (mi < marks.length && t >= marks[mi][0]) { p.padLevel(W, marks[mi][1]); mi++; }
      if (!released && t >= tD) { p.padRelease(W, pos); released = true; }
      p.tick(g, t, DT);
      if (rec) series.push([t, rowLevel(p, rec.card), rec.strobing]);
    }
    const edges = [];
    let on = series[0][1] > 0.45;
    for (const [t, x] of series) { const now = x > 0.45; if (now !== on) { edges.push(t); on = now; } }
    const inside = (a, b) => edges.filter((t) => t >= a && t < b);
    assert.equal(inside(tA + 300, tB).length, 0, `${bpm} BPM: no strobe at level 0.9 (${inside(tA + 300, tB).length} edges)`);
    assert.ok(inside(tB, tC).length >= 6, `${bpm} BPM: it strobes at level 1.0 (${inside(tB, tC).length} edges in 6 s)`);
    assert.ok(inside(tB, tB + 400).length >= 1, `${bpm} BPM: the strobe engages as the level reaches the band (first edge ${(inside(tB, tC)[0] - tB).toFixed(0)} ms later)`);
    assert.ok(series.some(([t, , s]) => t > tB && t < tC && s) && !series.some(([t, , s]) => t > tC + 600 && s), `${bpm} BPM: strobing only in the band`);
    assert.equal(inside(tC + 600, tD).length, 0, `${bpm} BPM: the strobe stops below the band (${inside(tC + 600, tD).length} edges)`);
    let most = 0;
    for (let i = 0; i < edges.length; i++) most = Math.max(most, edges.filter((t) => t >= edges[i] && t < edges[i] + 1010).length);
    assert.ok(most <= 4, `${bpm} BPM: ${most} edges inside one 1.01 s window`);
    const flashes = inside(tB, tC).length / 2 / 6;
    assert.ok(flashes <= KICK.STROBE_HZ_CAP + 0.05, `${bpm} BPM: ${flashes.toFixed(2)} flashes a second`);
    // the limiter, fed a frame whose every cell is this row (the worst case: the strobing row fills the screen), never acts
    const lim = new FrameLimiter();
    for (const [t, x] of series) lim.step({ L: new Float64Array(16).fill(0.6 * x), R: new Float64Array(16) }, t / 1000, DT);
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames`);
    report.push(`${bpm} BPM: ${flashes.toFixed(2)} flashes/s, most edges in 1.01 s ${most}, limiter interventions ${lim.stats().interventions}`);
  }
  console.log(`  the strobe alone, the whole screen strobing:\n  ${report.join("\n  ")}`);
});

test("two kicks strobing together stay inside the gate by themselves: the strobes share one beat-locked clock", () => {
  need();
  for (const bpm of [128, 150]) {
    const g = locked(bpm), p = fresh({ look: "break" });
    let w = null, c = null, rel = false;
    const series = [];
    for (let t = 0; t < 14000; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!w && t >= 1000) { force(p, "delay.30"); w = p.pad(W, 1, pos, { hold: true }); }
      if (!c && t >= 1700) { force(p, "delay.55"); c = p.pad(C, 1, pos, { hold: true }); }
      if (!rel && t >= 12000) { p.padRelease(W, pos); p.padRelease(C, pos); rel = true; }
      p.tick(g, t, DT);
      if (w && c) series.push([t, (rowLevel(p, w.card) + rowLevel(p, c.card)) / 2, rowLevel(p, w.card), rowLevel(p, c.card)]);
    }
    assert.notEqual(w.card.name, c.card.name);
    // after the second one joins, the two rows go dark and light together
    const apart = series.filter(([t, , a, b]) => t > 2600 && t < 12000 && (a > 0.5) !== (b > 0.5)).length;
    assert.ok(apart <= 2, `${bpm} BPM: ${apart} frames with one row lit and the other dark`);
    const lim = new FrameLimiter();
    for (const [t, x] of series) lim.step({ L: new Float64Array(16).fill(0.6 * x), R: new Float64Array(16) }, t / 1000, DT);
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames`);
  }
});

test("without a kick block (source-v0) KICK is the v0 strand lift: the strand's cubes and heads, 0.6 + 0.4 x velocity, decaying over 0.3 beat", () => {
  need();
  assert.equal(KICK.kickConfig(RIG0).legacy, true);
  const g = locked(150), p = fresh({ rig: RIG0, theme: THEME0, look: "break" });
  const cube = RIG0.cells.kind.indexOf(2);
  let rec = null; const lv = [];
  play(p, g, 0, 12, (pos) => { if (!rec && pos >= 7.9) rec = p.pad("kick", 0.5, pos); lv.push([pos, p.kickLevel(pos), p.pixels[cube * 4 + 3]]); });
  assert.ok(rec.card.cells.includes(cube) && rec.card.heads.length === 12, "the strand: its heads and its cube cells");
  for (const [pos, k] of lv) {
    const want = pos < 8 - 1e-6 ? 0 : 0.8 * Math.exp(-(pos - 8) / 0.3);
    assert.ok(Math.abs(k - want) < 1e-6 || (want < 0.004 && k === 0), `at ${pos.toFixed(3)}: ${k} (v0: ${want})`);
  }
  const line = lv.find(([pos]) => pos >= 8 - 1e-9);
  assert.ok(line[2] >= 0.8 - 1e-4, `the cube at the line: ${line[2]}`);
});

test("the kick block is checked: source-v1's is valid; unknown rows, rows shared by two cards, and a strobe above the house cap are refused", () => {
  need();
  assert.deepEqual(KICK.validateKick(RIG1), []);
  assert.deepEqual(KICK.validateKick(RIG0), [], "no block is valid (the v0 kick)");
  const bad = (patch) => KICK.validateKick({ ...RIG1, kick: { ...SCENE1.kick, ...patch } });
  assert.ok(bad({ deck: [{ row: "no.such.group" }] }).some((m) => /no\.such\.group/.test(m)));
  assert.ok(bad({ deck: [{ row: "halo" }, { row: "halo.top" }] }).some((m) => /share/.test(m)));
  assert.ok(bad({ strobe: { ...SCENE1.kick.strobe, max_hz: 3 } }).some((m) => /strobe/.test(m)));
  assert.ok(bad({ bands: [{ name: "x", from: 0.2 }] }).some((m) => /bands/.test(m)));
  // the acceptance numbers and the dealer's are one; the roles are the programmer's
  assert.deepEqual({ ...KICK.KICK_VISIBLE }, { lift: LIFT, white: WHITE });
  assert.deepEqual([...KICK.KICK_ROLES], [...ROLE_NAMES]);
  // the set's pads: KICK white on pad 1 (MIDI pad 1 still kicks), colour on pad 5
  assert.equal(SCENE1.show.pads["1"], "kick-white");
  assert.equal(SCENE1.show.pads["5"], "kick-colour");
});
