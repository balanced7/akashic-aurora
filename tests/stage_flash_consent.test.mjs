// The flash protection choice (arsenal/web/lib/flash-consent.js): node --test tests/stage_flash_consent.test.mjs
// The decision and the remembered choice, without a page (the screen itself is checked headless: the lanes' consent
// phase and the toggle receipt in research/in-flight/flash-toggle-report-2026-10-28.md).
import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveChoice, flashProtection, STORE_KEY, WORDING } from "../arsenal/web/lib/flash-consent.js";

const memory = (v = null) => { let x = v; return { get: () => x, set: (y) => { x = y; return true; }, peek: () => x }; };
const broken = () => ({ get() { return null; }, set() { return false; } });

test("the order of the choice: URL, automation, remembered, first visit", () => {
  assert.deepEqual(resolveChoice({}), { on: true, show: true, source: "first-visit" });
  assert.deepEqual(resolveChoice({ stored: "off" }), { on: false, show: false, source: "stored" });
  assert.deepEqual(resolveChoice({ stored: "on" }), { on: true, show: false, source: "stored" });
  // the house's headless lanes: protection on, no screen, whatever was stored
  assert.deepEqual(resolveChoice({ automated: true }), { on: true, show: false, source: "automation" });
  assert.deepEqual(resolveChoice({ automated: true, stored: "off" }), { on: true, show: false, source: "automation" });
  // the URL decides over everything (tests, kiosks), and ?flash=ask always shows the screen
  assert.deepEqual(resolveChoice({ param: "off", automated: true }), { on: false, show: false, source: "url" });
  assert.deepEqual(resolveChoice({ param: "on", stored: "off" }), { on: true, show: false, source: "url" });
  assert.deepEqual(resolveChoice({ param: "ask", stored: "off" }), { on: false, show: true, source: "url" });
  assert.deepEqual(resolveChoice({ param: "ask" }), { on: true, show: true, source: "url" });
  // anything else in the URL is not a choice
  assert.deepEqual(resolveChoice({ param: "maybe" }), { on: true, show: true, source: "first-visit" });
});

test("the wording: one checkbox, 'Flash protection', and no 'recommended' anywhere", () => {
  assert.equal(WORDING.box, "Flash protection");
  for (const v of Object.values(WORDING)) assert.ok(!/recommend/i.test(v), v);
  assert.match(WORDING.body, /flashing lights and patterns/);
  assert.match(WORDING.body, /seizures/);
  assert.match(WORDING.body, /photosensitive epilepsy/);
});

test("the controller: no screen without a document; the quiet setting is remembered and heard", () => {
  const st = memory("off");
  const ctl = flashProtection({ search: "", storage: st, automated: false, doc: null });
  assert.equal(ctl.on, false);
  assert.equal(ctl.source, "stored");
  const heard = [];
  ctl.onChange((on) => heard.push(on));
  ctl.set(true);
  assert.equal(ctl.on, true);
  assert.equal(st.peek(), "on");
  assert.deepEqual(heard, [true]);
  ctl.set(true);                       // no change: nothing heard twice
  assert.deepEqual(heard, [true]);
  ctl.set(false);
  assert.equal(st.peek(), "off");
  assert.deepEqual(heard, [true, false]);
});

test("a URL choice is not stored (a kiosk or a test never overwrites the viewer's own)", async () => {
  const st = memory("on");
  const ctl = flashProtection({ search: "?flash=off", storage: st, automated: false, doc: null });
  assert.equal(await ctl.ready, false);
  assert.equal(st.peek(), "on");
});

test("without storage the page still works: the choice holds for the visit", async () => {
  const ctl = flashProtection({ search: "?flash=on", storage: broken(), automated: false, doc: null });
  assert.equal(await ctl.ready, true);
  ctl.set(false);
  assert.equal(ctl.on, false);
  assert.equal(STORE_KEY, "arsenal.flashProtection");
});
