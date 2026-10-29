// One palette library for the Stage and the VJ page (arsenal/web/palettes.js through vj-themes.js). node --test tests/vj_palettes.test.mjs
//
// Daniel, 2026-10-28: "I want us to have 30 color palates that are high quality and what is used for driving the colors so
// it always looks careful and deliberate". The design's default he approved: one palette library for the Stage and the VJ
// page (research/in-flight/palettes-2026-10-28/DESIGN.md, sections 6.3 and 8 question 7). These pin: the VJ library with
// the thirty palettes merged in validates (no errors, no warnings), each palette shows the Stage's colours, its family tab
// lands it on the next bar, every palette's look emits no saturated red, and the page's loader falls back to its own
// library when palettes.json does not load.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as T from "../arsenal/web/vj-themes.js";
import * as PAL from "../arsenal/web/palettes.js";

const RAW = JSON.parse(readFileSync(new URL("../arsenal/web/vj-themes.json", import.meta.url), "utf8"));
const PRAW = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
const PLIB = PAL.loadPalettes(PRAW);
const merged = T.withPalettes(RAW, PLIB);
const lib = T.loadLibrary(merged);
const grid = (beatMs = 500) => { const next = (now, every) => Math.ceil(now / every) * every;
  return { alive: () => true, beatMs: () => beatMs, nextBeatAt: (n) => next(n, beatMs), nextBarAt: (n) => next(n, 4 * beatMs), nextPhraseAt: (n) => next(n, 32 * beatMs) }; };

test("the VJ library with the thirty palettes merged in validates with no errors and no warnings; its own 37 themes are untouched and first", () => {
  const v = T.validateLibrary(merged);
  assert.deepEqual(v.errors, []); assert.deepEqual(v.warnings, []);
  assert.equal(lib.themes.length, RAW.themes.length + 30);
  assert.deepEqual(merged.themes.slice(0, RAW.themes.length), RAW.themes, "the library's own themes, as they were");
  assert.deepEqual(merged.fader_order, RAW.fader_order, "the fader is unchanged (it is full at 25): the palettes ride their family tabs");
  assert.deepEqual(T.paletteFamilies(lib), ["pal-violet", "pal-pink", "pal-blue", "pal-green", "pal-warm", "pal-neutral"]);
  for (const f of T.paletteFamilies(lib)) for (const id of Object.values(lib.families[f])) assert.ok(lib.byId.has(id) && id.startsWith("pal-"), `${f}: ${id}`);
  // Molten and Dreaming City exist on both pages: the VJ's own keep their ids and data, the palettes ride as pal-*
  assert.equal(lib.byId.get("molten").A, RAW.themes.find((t) => t.id === "molten").A);
  assert.ok(lib.byId.has("pal-molten") && lib.byId.has("pal-dreaming-city"));
});

test("one library: each palette theme on the VJ page carries the Stage's colours (A base, B partner, W white, the ground the air, the laser pair, the pad stand-ins)", () => {
  for (const p of PLIB.list) {
    const t = lib.byId.get(`pal-${p.id}`), st = PAL.stageTheme(p);
    assert.ok(t, p.id);
    assert.deepEqual([t.A, t.B, t.W, t.ground], [st.A, st.B, st.W, st.ambient], `${p.id}: the same colours on both pages`);
    assert.deepEqual([t.beam.A, t.beam.B], p.lasers.slice(0, 2), `${p.id}: the laser pair`);
    assert.deepEqual([t.led.A, t.led.B, t.led.W], [p.pads.A.hex, p.pads.B.hex, p.pads.W.hex], `${p.id}: the KeyLab pads`);
    assert.equal(t.name, p.name); assert.equal(t.family, `pal-${p.family}`); assert.equal(t.fader, false);
  }
});

test("every palette theme's look emits no saturated red (lasers, strobes, bursts, flash, shockwave, the kick glow), and its scene's four stops start at the palette's bed and partner", () => {
  for (const p of PLIB.list) {
    const L = T.themeLook(lib, `pal-${p.id}`);
    for (const c of [L.lasers.L1, L.lasers.L2, ...L.lasers.triple, ...L.lasers.flicker, ...L.lasers.burst, L.fx.flash, L.fx.shockwave, L.scene.kickGlow]) {
      assert.ok(!T.isSaturatedRed(c), `${p.id}: ${JSON.stringify(c)} is a saturated red`);
    }
    const stop = (k) => [L.scene.palette[k * 3], L.scene.palette[k * 3 + 1], L.scene.palette[k * 3 + 2]];
    assert.ok(PAL.deOK(stop(0), PAL.hexToLin(p.stage_theme.A)) < 0.02, `${p.id}: stop A is the bed`);
    assert.ok(PAL.deOK(stop(1), PAL.hexToLin(p.stage_theme.B)) < 0.02, `${p.id}: stop B is the partner`);
  }
});

test("a palette family tab lands one of its palettes on the next bar (the ThemeDirector, as F1-F8 do; Shift+F1-F6 on the page)", () => {
  const clock = grid(500);
  for (const f of T.paletteFamilies(lib)) {
    const d = new T.ThemeDirector(lib, { initial: "night-sea" });
    assert.ok(d.onFamilyTab(f, 100, clock));
    const ch = [];
    for (let t = 100; t <= 4200; t += 50) { const c = d.tick(t, clock); if (c) ch.push(c); }
    assert.equal(ch.length, 1, `${f}: one change`);
    assert.ok(ch[0].id.startsWith("pal-") && lib.byId.get(ch[0].id).family === f, `${f}: landed ${ch[0].id}`);
    assert.equal(ch[0].atMs, 2000, `${f}: on the next bar line`);
  }
  const page = readFileSync(new URL("../arsenal/web/vj.js", import.meta.url), "utf8");
  assert.match(page, /const pf = e\.shiftKey && themes\.lib \? paletteFamilies\(themes\.lib\) : null;/);
});

test("the page's loader merges palettes.json, and keeps its own library when palettes.json does not load or a palette is refused", async () => {
  const vjText = JSON.stringify(RAW);
  const fake = (palOk, palBody = PRAW) => async (url) => {
    const u = String(url);
    if (u.endsWith("vj-themes.json")) return { ok: true, status: 200, text: async () => vjText };
    if (!palOk) return { ok: false, status: 404 };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(palBody)) };
  };
  let rep = null;
  const a = await T.fetchLibrary(new URL("http://x/vj-themes.json"), fake(true), { palettesUrl: new URL("http://x/palettes.json"), onPalettes: (r) => { rep = r; } });
  assert.equal(a.themes.length, RAW.themes.length + 30); assert.equal(rep.ok, true); assert.equal(rep.count, 30);
  const b = await T.fetchLibrary(new URL("http://x/vj-themes.json"), fake(false), { palettesUrl: new URL("http://x/palettes.json"), onPalettes: (r) => { rep = r; } });
  assert.equal(b.themes.length, RAW.themes.length); assert.equal(rep.ok, false);
  const broken = JSON.parse(JSON.stringify(PRAW));
  broken.palettes[5].colours.find((c) => c.role === "kick").hex = "#ffb000";     // an amber kick in a cool palette
  const c = await T.fetchLibrary(new URL("http://x/vj-themes.json"), fake(true, broken), { palettesUrl: new URL("http://x/palettes.json"), onPalettes: (r) => { rep = r; } });
  assert.equal(c.themes.length, RAW.themes.length + 29); assert.deepEqual(rep.refused.map((r) => r.id), [broken.palettes[5].id]);
  const plain = await T.fetchLibrary(new URL("http://x/vj-themes.json"), fake(true), { palettesUrl: null });
  assert.equal(plain.themes.length, RAW.themes.length, "palettesUrl null: the library alone");
});
