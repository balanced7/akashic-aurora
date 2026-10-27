// Node tests for the motion library (arsenal/web/vj-motions.js) and its use by the laser engine (arsenal/web/vj-lasers.js).
// Zero dependencies, no GPU:  node --test tests/vj_motions.test.mjs
//
// Daniel, 2026-10-27: "a library of epic satisfying motions that all fit various time budgets ... 16 variant (or however
// many are appropriate) for each of the feels, 1/32, 1/16, 1/8 etc". The build spec: research/in-flight/
// vj-v2-build-spec-2026-10-27.md section A. What is pinned here: the classes and the library (16 variants for every whole
// class M8 to M2b, textures only at M32 and M16), every variant landing exactly on the grid at any frame rate and through
// a tempo change, the flash rule at deal time (no motion's actions more than 3 a second, at any tempo), the five dealing
// layers, Vandor's amendment (repetition grows size; the period only when the presses leave room), and in the laser engine:
// the hits carry motions, a held pad is a standing motion, a fast or pre-aimed motion never moves a lit beam, and no frame
// goes over its budget with motions on. Every number here is synthetic: nothing reads Daniel's playing.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as M from "../arsenal/web/vj-motions.js";
import * as L from "../arsenal/web/vj-lasers.js";

const F = 1000 / 60;
const WHOLE = ["M8", "M4", "M2", "M1", "M2b", "M4b"];
const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length % 2 ? s[s.length >> 1] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };
const onGrid = (p, g) => Math.abs(p / g - Math.round(p / g)) < 1e-9;

// ------------------------------------------------------------------------------------------- 1. the library --
test("classes: eight budgets from a 1/32 note to four bars, M32 and M16 textures only, every template inside its span", () => {
  assert.deepEqual(M.CLASS_IDS, ["M32", "M16", "M8", "M4", "M2", "M1", "M2b", "M4b"]);
  M.CLASS_IDS.forEach((c, i) => {
    const C = M.CLASSES[c];
    assert.equal(C.beats, 2 ** i / 8, `${c} beats`);
    assert.equal(C.texture, i < 2, `${c} texture`);
    assert.ok(C.tpl.a + C.tpl.T < 1, `${c}: anticipation + action leave a settle`);
    assert.ok(C.grid > 0 && C.beats / C.grid === Math.round(C.beats / C.grid), `${c}: its length is whole grid steps, so every cycle lands`);
  });
});

test("the library: 16 variants for every whole class M8 to M2b (128 renderings with the symmetry deck), textures only at M32 and M16", () => {
  const ids = new Set(M.MOTION_IDS);
  assert.equal(ids.size, M.MOTION_IDS.length, "ids unique");
  for (const c of ["M8", "M4", "M2", "M1", "M2b"]) {
    assert.equal(M.CLASS_MOTIONS[c].length, 16, `${c} variants`);
    assert.equal(M.CLASS_MOTIONS[c].length * M.TRANSFORM_IDS.length, 128, `${c} renderings`);
    const feels = new Set(M.CLASS_MOTIONS[c].map((id) => M.MOTIONS[id].feel));
    assert.ok(feels.size >= 2, `${c} spans the feels (${[...feels]})`);
  }
  assert.ok(M.CLASS_MOTIONS.M4b.length >= 8);
  assert.equal(M.TRANSFORM_IDS.length, 8);
  for (const id of M.MOTION_IDS) {
    const m = M.MOTIONS[id];
    if (m.texture) {
      assert.ok(["M32", "M16"].includes(m.cls), `${id}: a texture lives in a texture class`);
      assert.equal(m.flashes, 0);
      // a texture never leaves its beams' lit band: under 5 px at the far end of a full-height beam at its largest
      assert.ok(Math.abs(m.aim) * M.AMP_MAX * 1080 <= 5, `${id}: texture turn ${(m.aim * M.AMP_MAX * 1080).toFixed(1)} px`);
      assert.ok(Math.abs(m.spread) * M.AMP_MAX <= 0.01, `${id}: texture spread`);
    } else {
      assert.ok(WHOLE.includes(m.cls), `${id} class`);
      assert.ok(m.aim !== 0 || m.spread !== 0 || m.rot !== 0, `${id} moves something`);
      assert.ok(m.flashes >= 1);
      assert.ok(["settle", "whip", "gather"].includes(m.feel));
    }
  }
  const cat = M.catalogue();
  assert.equal(cat.motions.length, M.MOTION_IDS.length);
  assert.equal(cat.classes.find((c) => c.id === "M16").texture, true);
});

test("evaluate: every variant starts at rest, lands EXACTLY on its end value from u = 1, never jumps unless it is pre-aimed", () => {
  for (const id of M.MOTION_IDS) {
    const m = M.MOTIONS[id];
    assert.equal(M.evaluate(m, 0), 0, `${id} at 0`);
    assert.equal(M.evaluate(m, -0.3), 0);
    for (const u of [1, 1.0000001, 1.5, 9]) assert.equal(M.evaluate(m, u), m.end, `${id} at ${u}`);
    let prev = 0, jump = 0, peak = 0;
    for (let i = 1; i <= 4000; i++) {
      const v = M.evaluate(m, i / 4000);
      assert.ok(Number.isFinite(v));
      jump = Math.max(jump, Math.abs(v - prev)); peak = Math.max(peak, Math.abs(v)); prev = v;
    }
    assert.ok(peak <= 1.3, `${id} peak ${peak}`);
    if (!m.sampled && !m.texture) assert.ok(jump <= 0.03, `${id}: largest step between 1/4000s ${jump.toFixed(4)}`);
    if (!m.texture) assert.ok(Math.abs(M.evaluate(m, 0.9995) - m.end) < 0.01, `${id} settles into its landing`);
  }
});

// --------------------------------------------------------------------------------------------- 2. landing --
test("landing: the start is never delayed and the end lands on the class's grid line, the span stretched by 0.75x to 1.75x", () => {
  const r = M.seededRng("landing");
  for (const c of M.CLASS_IDS) {
    const C = M.CLASSES[c];
    for (let i = 0; i < 400; i++) {
      const pos = r() * 200 - 20;
      const Ld = M.landing(c, pos);
      assert.equal(Ld.p0, pos, "no added latency");
      assert.ok(onGrid(Ld.p1, C.grid), `${c} from ${pos}: lands on ${Ld.p1}`);
      assert.ok(Ld.k >= 0.75 - 1e-9 && Ld.k < 1.75 + 1e-9, `${c}: stretch ${Ld.k}`);
    }
  }
});

// At 60, 144 and 240 Hz and 128 to 200 BPM, with the tempo changing mid-motion: the first frame at or after the landing
// shows exactly the end value, and no frame before it does early (the pads lane's landing receipt: within one frame).
test("landing: every variant lands within one frame at 60, 144 and 240 Hz, through a tempo change mid-motion", () => {
  const r = M.seededRng("frames");
  let checked = 0;
  for (const hz of [60, 144, 240]) for (const [b0, b1] of [[128, 128], [150, 174], [200, 160]]) {
    const dt = 1000 / hz;
    for (const id of M.MOTION_IDS.filter((x) => !M.MOTIONS[x].texture)) {
      const m = M.MOTIONS[id], press = 2000 + r() * 1000, tChange = press + 300;
      // the tempo: b0 until tChange, b1 after; the beat position integrates it
      const posAt = (t) => (t <= tChange ? t * b0 / 60000 : tChange * b0 / 60000 + (t - tChange) * b1 / 60000);
      const Ld = M.landing(m.cls, posAt(press));
      const st = { m, p0: Ld.p0, p1: Ld.p1, beats: M.CLASSES[m.cls].beats, looping: false };
      const tLand = tChange + (Ld.p1 - posAt(tChange)) * 60000 / b1;
      const tl = posAt(tChange) >= Ld.p1 ? Ld.p1 * 60000 / b0 : tLand;
      let landed = null;
      for (let t = press; t < tl + 3 * dt; t += dt) {
        if (M.valueAt(st, posAt(t)) === m.end && posAt(t) >= Ld.p1 - 1e-12) { landed = t; break; }
      }
      assert.ok(landed !== null, `${id} at ${hz} Hz lands`);
      assert.ok(landed - tl < dt + 1e-6 && landed >= tl - 1e-6, `${id} at ${hz} Hz, ${b0}->${b1} BPM: landed ${(landed - tl).toFixed(2)} ms after the grid line`);
      checked++;
    }
  }
  assert.ok(checked > 700);
});

test("looping: every cycle ends on a grid line, and no head jumps across a cycle -- a motion with a new rest swings back", () => {
  for (const id of M.MOTION_IDS.filter((x) => !M.MOTIONS[x].texture && !M.MOTIONS[x].sampled)) {
    const m = M.MOTIONS[id], C = M.CLASSES[m.cls], Ld = M.landing(m.cls, 3.3);
    for (const xf of [{ rev: 0, rotK: 0 }, { rev: 1, rotK: 3 }]) {
      const st = { m, p0: Ld.p0, p1: Ld.p1, beats: C.beats, looping: true, ...xf };
      for (let c = 0; c < 4; c++) assert.ok(onGrid(Ld.p1 + c * C.beats, C.grid), `${id}: cycle ${c} ends on the grid`);
      const n = 8, span = Ld.p1 - Ld.p0 + 3 * C.beats, steps = Math.ceil(span / C.beats * 2000);
      for (let r = 0; r < n; r++) {
        let prev = M.valueAt(st, Ld.p0, r, n), jump = 0;
        for (let i = 1; i <= steps; i++) { const v = M.valueAt(st, Ld.p0 + span * i / steps, r, n); jump = Math.max(jump, Math.abs(v - prev)); prev = v; }
        assert.ok(jump < 0.06, `${id} (rev ${xf.rev}) head ${r}: a jump of ${jump.toFixed(3)} in a loop`);
      }
    }
  }
});

// ------------------------------------------------------------------------------------------ 3. the flash rule --
test("the flash rule: actions more than 3 a second are refused -- by tempo, class, form and press pace; textures have none", () => {
  const sweep = M.MOTIONS["swing"], pend = M.MOTIONS["ping-pong"], m2p = M.MOTIONS["pendulum"], tex = M.MOTIONS["shimmer"];
  // looping at 150 BPM (400 ms a beat): an M8 swing cycles every 200 ms (5 a second) -- refused; an M4 one-action (2.5) passes
  assert.ok(M.refused(sweep, 0.5, 400, { looping: true }));
  assert.ok(!M.refused(M.MOTIONS["sweep"], 1, 400, { looping: true }));
  // a pendulum swings twice a cycle: at M4 that is 5 a second (refused); at M2, 2.5 (passes)
  assert.ok(M.refused(pend, 1, 400, { looping: true }));
  assert.ok(!M.refused(m2p, 2, 400, { looping: true }));
  // at 90 BPM an M8 loop is 3.0 a second: on the line, allowed
  assert.ok(!M.refused(sweep, 0.5, 60000 / 90, { looping: true }));
  // a one-shot with one action is paced by the presses: none known, free; presses 0.6 beats apart at 150 BPM, refused
  assert.ok(!M.refused(sweep, 0.5, 400));
  assert.ok(M.refused(sweep, 0.5, 400, { intervalBeats: 0.6 }));
  // a one-shot with two actions in one cycle: their own spacing counts
  assert.ok(M.refused(pend, 1, 400));
  assert.equal(M.actionRateHz(tex, 1 / 8, 400, { looping: true }), 0);
});

// Every motion the dealer deals, at every tempo from 60 to 220 BPM, every tier, looping or not, at random press paces,
// passes the flash rule recomputed here from scratch.
test("the flash rule at deal time: nothing dealt at 60-220 BPM, in any tier or pace, has actions more than 3 a second", () => {
  const r = M.seededRng("sweep");
  let dealt = 0, none = 0, textures = 0;
  for (const bpm of [60, 75, 90, 110, 128, 140, 150, 160, 174, 180, 200, 220]) {
    const per = 60000 / bpm, d = new M.MotionDealer({ seed: bpm });
    let pos = 0;
    for (let i = 0; i < 160; i++) {
      pos += [0.25, 0.5, 0.75, 1, 1.5, 2.5, 6][Math.floor(r() * 7)] + (r() - 0.5) * 0.05;
      d.press(pos);
      const tier = ["burst", "escalate", "hero", "flicker", "rapid", "held", "phrase"][Math.floor(r() * 7)];
      const looping = tier === "rapid" || tier === "held" || r() < 0.15;
      const ctx = { pos, perMs: per, vel: r(), tier, level: 1 + Math.floor(r() * 3), looping, lifeBeats: [0.375, 0.625, 1.125, 2.625, 2][Math.floor(r() * 5)],
        section: ["drop", "break", "anti", "build"][Math.floor(r() * 4)], bank: ["A", "B", "both", "call"][Math.floor(r() * 4)], fine: r() < 0.5 };
      const rec = d.deal(ctx);
      if (!rec) { none++; continue; }
      dealt++;
      if (rec.m.texture) { textures++; continue; }
      const span = Math.min(rec.p1 - rec.p0, rec.beats);
      const hz = M.actionRateHz(rec.m, span, per, { looping, intervalBeats: d.medianInterval() });
      assert.ok(hz <= M.MAX_FLASH_HZ + 1e-9, `${bpm} BPM ${tier}${looping ? " loop" : ""}: ${rec.sig} acts ${hz.toFixed(2)} a second`);
      if (!looping) assert.ok(rec.p1 - pos <= d.medianInterval() + 1e-9, `${rec.sig} lands before the next likely press`);
    }
  }
  console.log(`  flash rule sweep: ${dealt} dealt (${textures} textures), ${none} hits with no motion`);
  assert.ok(dealt > 1500 && textures > 50);
});

// ------------------------------------------------------------------------------------------- 4. the dealer --
function stream(d, n, { gap = 6, start = 1, tier = "burst", level = 1, vel = 0.7, bank = "both", life = 1.125, ...rest } = {}) {
  const out = [];
  let pos = start;
  for (let i = 0; i < n; i++) {
    d.press(pos);
    out.push(d.deal({ pos, perMs: 400, vel, tier, level, lifeBeats: life, bank, ...rest }));
    pos += typeof gap === "function" ? gap(i) : gap;
  }
  return out;
}

test("the dealer: the same seed deals the same, another seed differs; Variety 0 deals one motion as written", () => {
  const a = stream(new M.MotionDealer({ seed: 4 }), 40).map((x) => x.sig);
  const b = stream(new M.MotionDealer({ seed: 4 }), 40).map((x) => x.sig);
  const c = stream(new M.MotionDealer({ seed: 5 }), 40).map((x) => x.sig);
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, c);
  const z = stream(new M.MotionDealer({ seed: 4 }), 20, { variety: 0 });
  assert.equal(new Set(z.map((x) => x.sig)).size, 1, "rehearsal: one signature");
  assert.equal(z[0].xf, "I");
});

test("the dealer: a shuffle-bag that never deals either of the last two again, and consecutive signatures differ on two axes", () => {
  const d = new M.MotionDealer({ seed: 9 });
  const recs = stream(d, 300, { gap: (i) => (i % 2 ? 6.25 : 5.75) });       // (never on a phrase's first beat: no rhyme)
  for (let i = 0; i < recs.length; i++) {
    const r = recs[i];
    assert.ok(!r.rhyme && !r.response);
    if (i >= 1) assert.notEqual(r.id, recs[i - 1].id, `deal ${i} repeats the last`);
    if (i >= 2 && recs[i - 2].cls === r.cls) assert.notEqual(r.id, recs[i - 2].id, `deal ${i} repeats the one before the last`);
    if (i >= 1) {
      const p = recs[i - 1], axes = (r.id !== p.id) + (r.cls !== p.cls) + (r.xf !== p.xf);
      assert.ok(axes >= 2, `deals ${i - 1} and ${i}: ${p.sig} then ${r.sig}`);
    }
  }
  const renders = new Set(recs.slice(0, 32).map((x) => `${x.id}|${x.xf}`));
  assert.ok(renders.size >= 24, `32 presses, ${renders.size} renderings`);
  assert.ok(new Set(recs.map((x) => x.xf)).size >= 7, "the symmetry deck is dealt through");
});

test("the amendment: repetition always grows the size; the period grows only when the presses leave room", () => {
  // the same press at levels 1-3: the amplitude grows each time
  const amps = [1, 2, 3].map((level) => new M.MotionDealer({ seed: 2 }).deal({ pos: 8, vel: 0.6, tier: "escalate", level, lifeBeats: 1.125 }).amp);
  assert.ok(amps[0] < amps[1] && amps[1] < amps[2], `amplitudes ${amps.map((a) => a.toFixed(2))}`);
  // velocity is amplitude; the downbeat is bigger than the off-beat
  const at = (vel, pos) => new M.MotionDealer({ seed: 2 }).deal({ pos, vel, lifeBeats: 1.125 }).amp;
  assert.ok(at(0.2, 8) < at(1, 8));
  assert.ok(at(0.7, 9.5) < at(0.7, 8));
  // sparse presses (a bar and a half apart): escalation lengthens a triple's motion from M4 to M2
  const sparse = stream(new M.MotionDealer({ seed: 3 }), 6, { gap: 6, tier: "escalate", level: 2 });
  assert.ok(sparse.slice(3).every((x) => x.cls === "M2"), sparse.map((x) => x.cls).join(" "));
  const calm = stream(new M.MotionDealer({ seed: 3 }), 6, { gap: 6, tier: "burst", level: 1 });
  assert.ok(calm.slice(3).every((x) => x.cls === "M4"), calm.map((x) => x.cls).join(" "));
  // presses a beat and a quarter apart: the same escalation stays short enough to land before the next press
  const tight = stream(new M.MotionDealer({ seed: 3 }), 8, { gap: 1.25, tier: "escalate", level: 2 });
  for (const x of tight.slice(3)) assert.ok(x.p1 - x.p0 <= 1.25 + 1e-9 && ["M8", "M4"].includes(x.cls), `${x.sig} over ${(x.p1 - x.p0).toFixed(2)} beats`);
  // presses 0.6 beats apart at 150 BPM (240 ms): no whole motion may act that often -- a texture
  const rapid = stream(new M.MotionDealer({ seed: 3 }), 8, { gap: 0.6, tier: "flicker" });
  assert.ok(rapid.slice(3).every((x) => x.m.texture), rapid.map((x) => x.cls).join(" "));
});

test("call and response: the answering bank plays the asking bank's motion mirrored top for bottom; the next ask is fresh", () => {
  assert.ok(stream(new M.MotionDealer({ seed: 6 }), 6, { gap: 2.5, bank: "A" }).every((x) => !x.response), "one bank never answers itself");
  const d2 = new M.MotionDealer({ seed: 6 });
  d2.press(1.5); const a = d2.deal({ pos: 1.5, bank: "A", lifeBeats: 1.125 });
  d2.press(4); const b = d2.deal({ pos: 4, bank: "B", lifeBeats: 1.125 });
  d2.press(6.5); const c = d2.deal({ pos: 6.5, bank: "A", lifeBeats: 1.125 });
  assert.ok(b.response, "B answers A");
  assert.equal(b.id, a.id); assert.equal(b.cls, a.cls);
  assert.equal(b.my, 1 - a.my); assert.equal(b.mx, a.mx); assert.equal(b.rev, a.rev);
  assert.ok(b.amp > a.amp * 1.05, "the answer is louder");
  assert.ok(!c.response, "an answer is not asked back");
});

test("phrase memory: the first beat of a phrase rhymes with the last phrase's opening motion through the next card", () => {
  const d = new M.MotionDealer({ seed: 8 });
  const deal = (pos) => { d.press(pos); return d.deal({ pos, lifeBeats: 1.125, bank: "both" }); };
  const one = deal(32);
  for (const p of [38, 44, 50, 56]) deal(p);
  const two = deal(64);
  for (const p of [70, 76, 82, 88]) deal(p);
  const three = deal(96);
  assert.equal(one.accent, "phrase");
  assert.ok(two.rhyme && three.rhyme);
  assert.equal(two.id, one.id); assert.equal(three.id, one.id);
  assert.equal(two.xf, "Mx"); assert.equal(three.xf, "Rev");
  // and a motion dealt again within the last four grows
  const e = new M.MotionDealer({ seed: 1 });
  e.press(0); const p0 = e.deal({ pos: 4, pin: "sweep", lifeBeats: 1.125 });
  e.press(6); const p1 = e.deal({ pos: 8, pin: "sweep", lifeBeats: 1.125 });
  assert.ok(p1.amp > p0.amp * 1.1, `memory: ${p0.amp.toFixed(2)} then ${p1.amp.toFixed(2)}`);
});

test("the dealer's own lanes: textures for rapid rolls (none on a still fast pattern), section classes for held pads, pins", () => {
  const d = new M.MotionDealer({ seed: 5 });
  d.press(1);
  assert.equal(d.deal({ pos: 1, tier: "rapid", looping: true }).cls, "M16");
  assert.equal(d.deal({ pos: 1, tier: "rapid", looping: true, fine: true }).cls, "M32");
  assert.equal(d.deal({ pos: 1, tier: "rapid", looping: true, stillFast: true }), null);
  for (const [section, cls] of [["drop", "M1"], ["break", "M2b"], ["anti", "M2"], ["build", "M1"]]) {
    const h = d.deal({ pos: 1, tier: "held", looping: true, section });
    assert.equal(h.cls, cls, `${section} holds a ${cls}`);
    assert.equal(h.looping, true);
  }
  assert.equal(d.deal({ pos: 1, tier: "held", looping: true, section: "drop", level: 2 }).cls, "M2b", "escalated: a longer hold");
  assert.equal(d.deal({ pos: 1, pin: "the-whip" }).id, "the-whip");
  assert.equal(d.deal({ pos: 1, pinClass: "M2" }).cls, "M2");
  assert.equal(d.deal({ pos: 1, pin: "off" }), null);
  // a blanked jump needs a dark gap to move in
  for (let i = 0; i < 40; i++) assert.notEqual(d.deal({ pos: 1 + i * 6, lifeBeats: 0.375, gaps: false }).id, "step");
  // the colour-swap card: never while the colour is held, never with one laser colour
  for (const opt of [{ colourSame: true }, { twoColours: false }]) {
    const recs = stream(new M.MotionDealer({ seed: 12 }), 64, opt);
    assert.ok(recs.every((x) => !x.col), JSON.stringify(opt));
  }
  assert.ok(stream(new M.MotionDealer({ seed: 12 }), 64).some((x) => x.col));
});

// ------------------------------------------------------------------------------------- 5. in the laser engine --
function steadyClock(bpm) {
  const per = 60000 / bpm;
  return { bpm, conf: 1, phaseAt: (t) => { const x = t / per; return x - Math.floor(x); }, nextBeatAt: (t) => Math.ceil(t / per - 1e-12) * per, posAt: (t) => t / per };
}
function drive(eng, events, { from, to, onFrame = null }) {
  const ev = events.slice().sort((a, b) => a.t - b.t);
  let ei = 0;
  for (let j = 0; ; j++) {
    const t = from + j * F;
    if (t > to) break;
    while (ei < ev.length && ev[ei].t <= t) { const e = ev[ei++]; e.fn(eng, e.t); }
    const out = eng.frame(t);
    if (onFrame) onFrame(out, t, j);
  }
}
const tap = (t, vel, hold = 60) => [{ t, fn: (e, x) => e.hit(x, vel) }, { t: t + hold, fn: (e, x) => e.release(x) }];
const lines = (out) => { const a = [], r = {}; for (let i = 0; i < out.n; i++) { L.decodeSeg(out.seg, i, r); if (!r.header && r.I > 0.002) a.push([r.x0, r.y0, r.x1, r.y1]); } return a; };

test("pad 2: every press carries a motion, a held pad its section's standing motion; motion off deals none", () => {
  const per = 400;
  for (const [section, held] of [["drop", "M1"], ["break", "M2b"]]) {
    const eng = L.createLaserEngine({ seed: 4, clock: steadyClock(150), section });
    const ev = [...tap(2000, 0.8), ...tap(2000 + 6 * per, 0.5), ...tap(2000 + 12 * per, 0.7, 3 * per)];
    drive(eng, ev, { from: 1950, to: 2000 + 18 * per });
    const presses = eng.log.filter((x) => x.tier !== "held");
    assert.ok(presses.every((x) => x.motion && M.MOTIONS[x.motion]), presses.map((x) => x.motion).join(" "));
    const h = eng.log.find((x) => x.tier === "held");
    assert.ok(h && h.motion, "the hold has a motion");
    assert.equal(h.motionClass, held, `${section}: held ${h.motionClass}`);
  }
  const off = L.createLaserEngine({ seed: 4, clock: steadyClock(150), motion: "off" });
  drive(off, tap(2000, 0.8), { from: 1950, to: 3000 });
  assert.equal(off.log[0].motion, "");
  assert.ok(L.catalogue().motions.length === M.MOTION_IDS.length && L.catalogue().motionClasses.includes("M2b"));
});

test("a held pad is a standing motion: its pulses land at different aims through the cycle; with motion off they repeat", () => {
  const per = 400;
  const run = (motion) => {
    const eng = L.createLaserEngine({ seed: 3, clock: steadyClock(150), section: "drop", patternMode: "fan", bankMode: "A", orderMode: "all", motion,
      motionClass: motion === "off" ? "auto" : "M1" });
    const shots = [];
    let lastOn = -1;
    drive(eng, tap(2000, 0.6, 10 * per), { from: 1950, to: 2000 + 10 * per, onFrame: (out) => {
      const H = eng.hits.find((h) => h.tier === "held" && h.on);
      if (H && H.cur.onFrame !== lastOn) { lastOn = H.cur.onFrame; shots.push(JSON.stringify(lines(out).map((l) => l.map((v) => v.toFixed(3))))); }
    } });
    return shots;
  };
  const on = run("auto"), off = run("off");
  assert.ok(on.length >= 8 && off.length >= 8);
  assert.ok(new Set(on).size >= 5, `motion on: ${new Set(on).size} distinct pictures in ${on.length} pulses`);
  assert.ok(new Set(off.slice(2)).size <= 2, `motion off: ${new Set(off.slice(2)).size} distinct pictures`);
});

// Fast gates at 150 BPM on moving and still patterns (the motion steps between pulses); and the blanked jump pinned on a
// SLOW loop (the Reverse-Bass Gate, a pulse a beat) over patterns that hold still on their own: it is pre-aimed, so it
// shows a new aim at a pulse but never moves one.
test("a fast hit never moves while lit, and a pre-aimed jump moves only in the dark between pulses", () => {
  const per = 400;
  const cases = [
    ...["triple", "roll16", "pushpull"].flatMap((g) => ["fan", "sweep", "crown", "figure", "cone"].map((p) => [{ gateMode: g }, p])),
    ...["chase", "cross", "hot"].map((p) => [{ gateMode: "revbass", motion: "step", motionClass: "M2" }, p]),
  ];
  for (const [c, pattern] of cases) {
    const eng = L.createLaserEngine({ seed: 5, clock: steadyClock(150), section: "climax", patternMode: pattern, shapeMode: pattern === "figure" ? "auto" : null, ...c });
    let prevKey = null, prev = null, moved = 0, litPairs = 0;
    const pictures = new Set();
    drive(eng, tap(2000, 0.9, 6 * per), { from: 1950, to: 2000 + 7 * per, onFrame: (out) => {
      const H = eng.hits.find((h) => h.started && !h.done && h.on);
      const key = H ? `${H.id}:${H.cur.onFrame}` : null, xs = H ? lines(out).flat() : null;
      if (key && key === prevKey && prev && prev.length === xs.length) { litPairs++; if (xs.some((x, i) => Math.abs(x - prev[i]) > 1e-9)) moved++; }
      if (key && key !== prevKey) pictures.add(JSON.stringify(xs.map((v) => v.toFixed(3))));
      prevKey = key; prev = xs;
    } });
    const what = `${c.gateMode}/${pattern}${c.motion ? " " + c.motion : ""}`;
    assert.ok(litPairs > 3, `${what}: ${litPairs} lit frame pairs`);
    assert.equal(moved, 0, `${what}: a lit picture moved in ${moved} frames`);
    if (c.motion === "step") {
      assert.ok(eng.log[0].motion === "step", `${what}: dealt ${eng.log[0].motion}`);
      assert.ok(pictures.size >= 2, `${what}: the jump shows at a new pulse (${pictures.size} pictures)`);
    }
  }
});

test("a motion that moves lit beams (a slow loop, a single onset) stays inside the change budget: the fit simulates it", () => {
  const per = 60000 / 128;
  let frames = 0, moving = 0;
  for (const motion of ["sweep-return", "the-whip", "arc", "rotor-180", "breathing-room", "cathedral", "fan-open", "swing"]) {
    for (const gateMode of ["revbass", "inhale", "single", "bar"]) {
      const eng = L.createLaserEngine({ seed: 11, clock: steadyClock(128), section: "climax", gateMode, motion, theme: { L1: "#ffffff", L2: "#ffffff" } });
      const ev = gateMode === "revbass" || gateMode === "inhale" ? tap(2000, 1, 8 * per) : [0, 6, 12].flatMap((b) => tap(2000 + b * per, 1));
      drive(eng, ev, { from: 1950, to: 2000 + 16 * per, onFrame: (out) => {
        frames++;
        assert.ok(!out.area.over, `${motion} on ${gateMode}: a frame over budget`);
        assert.ok(out.area.window <= L.BUDGET.single.window + 1e-9 && out.area.frame <= L.BUDGET.single.frame + 1e-9);
        if (eng.hits.some((h) => h.on && h.motion && !h.motion.sampled && !h.fast)) moving++;
      } });
    }
  }
  console.log(`  motions moving lit beams: ${moving} of ${frames} frames, none over budget`);
  assert.ok(moving > 100, "the motions really move lit beams");
});

// A smaller cousin of vj_lasers' realistic mashing, with the motion library dealing: bursts, escalations, rolls, holds,
// the phrase, every motion class pinned in turn, steady and with dropped frames.
test("realistic play with motions on: no frame goes out over its budget (fresh seeds, every class pinned in turn)", () => {
  const rows = [];
  for (const [run, cls, drop] of [[31, "auto", false], [32, "auto", true], [33, "M8", false], [34, "M4", false], [35, "M2", true], [36, "M1", false], [37, "M2b", false], [38, "M4b", true], [39, "M16", false], [40, "auto", false]]) {
    const r = L.makeRng(run, "motions-mash");
    const pick = (a) => a[Math.floor(r() * a.length)];
    const bpm = pick([128, 140, 150, 160, 174, 180]), per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: run, clock: steadyClock(bpm), motionClass: cls, section: pick(["climax", "drop", "build", "groove", "anti", "break"]),
      vibrate: r() < 0.4, shapeMode: r() < 0.25 ? "auto" : null, gateMode: r() < 0.7 ? "auto" : pick(L.GATE_IDS), theme: r() < 0.5 ? { L1: "#ffffff", L2: "#e8f8ff" } : L.DEFAULT_THEME });
    const ev = [], end = 2000 + 12000;
    for (let t = 2000; t < end;) {
      const s = r();
      if (s < 0.3) { const div = pick([0.5, 0.25]), n = 4 + Math.floor(r() * 8); for (let i = 0; i < n; i++) ev.push(...tap(t + i * div * per, 0.5 + 0.5 * r(), 35)); t += n * div * per; }
      else if (s < 0.55) { const div = pick([1, 1.5, 2.5]), n = 2 + Math.floor(r() * 4); for (let i = 0; i < n; i++) ev.push(...tap(t + i * div * per, r(), 50)); t += n * div * per; }
      else if (s < 0.75) { const hold = (1 + Math.floor(r() * 6)) * per; ev.push(...tap(t, 0.4 + 0.6 * r(), hold)); t += hold + per * r(); }
      else if (s < 0.85) { ev.push({ t, fn: (e, x) => e.phrase(x, 0.8) }); t += 3 * per; }
      else { ev.push(...tap(t, 0.6 + 0.4 * r())); t += 6 * per; }
    }
    const dr = L.makeRng(run, "drops");
    let over = 0, frames = 0, motions = new Set();
    const evs = ev.slice().sort((a, b) => a.t - b.t);
    let ei = 0;
    for (let t = 1950; t < end + 3 * per; t += drop && dr() < 0.04 ? 33.33 : F) {
      while (ei < evs.length && evs[ei].t <= t) { const e = evs[ei++]; e.fn(eng, e.t); }
      const out = eng.frame(t);
      frames++; if (out.area.over) over++;
      if (out.motion) motions.add(out.motion);
    }
    rows.push(`run ${run} ${cls} ${bpm}${drop ? " drops" : ""}: ${motions.size} motions, ${over}/${frames} over`);
    assert.equal(over, 0, `run ${run} (${cls}, ${bpm} BPM${drop ? ", dropped frames" : ""}): ${over} frames over budget`);
  }
  console.log("  " + rows.join("; "));
});

test("the colour-swap card swaps the hit's two laser colours; Colour Same never deals it", () => {
  const theme = { L1: "#1373f1", L2: "#25bde5" };
  const eng = L.createLaserEngine({ seed: 2, clock: steadyClock(150), theme });
  const ev = [];
  for (let i = 0; i < 40; i++) ev.push(...tap(2000 + i * 6 * 400, 0.7));
  const swapped = [];
  drive(eng, ev, { from: 1950, to: 2000 + 241 * 400, onFrame: () => { for (const h of eng.hits) if (h.motion && h.motion.rec.col) swapped.push(h); } });
  assert.ok(swapped.length, "dealt at least once in 40 hits");
  for (const h of swapped) { assert.deepEqual(h.col.L1, eng.col.L2); assert.deepEqual(h.col.L2, eng.col.L1); }
  const same = L.createLaserEngine({ seed: 2, clock: steadyClock(150), theme, colourSame: true });
  drive(same, ev, { from: 1950, to: 2000 + 241 * 400 });
  assert.ok(same.log.every((x) => !/Col/.test(x.motionXf)), "Colour Same: no swap");
});
