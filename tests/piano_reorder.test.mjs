// Node tests for the pure parts of arsenal/web/piano/studio/reorder.js (the drag handle every preset list on the page
// shares). Zero dependencies:  node tests/piano_reorder.test.mjs
// The pointer and keyboard behaviour needs a browser; the headless smoke run drives it. Here: the kept-order merge that
// keeps a camera mode or an instrument added later from being lost, the move, the localStorage round trip, the grip markup.
import { GRIP, HELP_ID, handleHtml, loadOrder, mergeOrder, moveItem, saveOrder } from "../arsenal/web/piano/studio/reorder.js";

let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
function fakeStorage(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), map: m };
}
const CAMERAS = ["auto", "performance", "sculpture", "detail", "orbit"];

// ------------------------------------------------------------ mergeOrder --
eq("nothing kept: the default order", mergeOrder(null, CAMERAS), CAMERAS);
eq("a kept order wins", mergeOrder(["performance", "auto", "orbit", "detail", "sculpture"], CAMERAS),
  ["performance", "auto", "orbit", "detail", "sculpture"]);
eq("a mode the kept order doesn't know yet is appended, never lost", mergeOrder(["performance", "auto"], CAMERAS),
  ["performance", "auto", "sculpture", "detail", "orbit"]);
eq("a kept id that no longer exists is dropped", mergeOrder(["gone", "orbit", "auto"], CAMERAS), ["orbit", "auto", "performance", "sculpture", "detail"]);
eq("a repeated kept id counts once", mergeOrder(["orbit", "orbit", "auto"], CAMERAS), ["orbit", "auto", "performance", "sculpture", "detail"]);
eq("junk instead of a list: the default order", mergeOrder({ a: 1 }, CAMERAS), CAMERAS);
eq("one flat kept list serves each section on its own", mergeOrder(["upright", "aether", "page", "solstice"], ["aether", "solstice", "nocturne"]),
  ["aether", "solstice", "nocturne"]);

// -------------------------------------------------------------- moveItem --
eq("move down", moveItem(["a", "b", "c", "d"], 0, 2), ["b", "c", "a", "d"]);
eq("move up", moveItem(["a", "b", "c", "d"], 3, 0), ["d", "a", "b", "c"]);
const src = ["a", "b"];
moveItem(src, 0, 1);
eq("moveItem never changes its input", src, ["a", "b"]);

// ------------------------------------------------- loadOrder / saveOrder --
{
  const s = fakeStorage();
  eq("load with nothing stored", loadOrder("arsenal.piano.camera-order", CAMERAS, s), CAMERAS);
  check("save", saveOrder("arsenal.piano.camera-order", ["performance", "auto", "sculpture", "detail", "orbit"], s));
  eq("... stored as a JSON list", JSON.parse(s.map.get("arsenal.piano.camera-order")), ["performance", "auto", "sculpture", "detail", "orbit"]);
  eq("... and loaded back", loadOrder("arsenal.piano.camera-order", CAMERAS, s)[0], "performance");
  eq("an unreadable stored order gives the default", loadOrder("k", CAMERAS, fakeStorage({ k: "{not json" })), CAMERAS);
  const blocked = { getItem() { throw new Error("SecurityError"); }, setItem() { throw new Error("QuotaExceeded"); } };
  eq("blocked storage loads the default", loadOrder("k", CAMERAS, blocked), CAMERAS);
  check("... and a save into it reports false instead of throwing", saveOrder("k", CAMERAS, blocked) === false);
  check("no storage at all", saveOrder("k", CAMERAS, null) === false && loadOrder("k", CAMERAS, null).length === 5);
}

// ------------------------------------------------------------ handleHtml --
{
  const h = handleHtml(`Rain "at" <night>`);
  check("the grip is a button", /^<button type="button" class="rr-handle"/.test(h), h);
  check("... named for its row, escaped", h.includes('aria-label="Move Rain &quot;at&quot; &lt;night&gt;"'), h);
  check("... described by the one help text", h.includes(`aria-describedby="${HELP_ID}"`), h);
  check("... drawing the six-dot grip", h.includes(GRIP) && (GRIP.match(/<circle/g) || []).length === 6);
  check("... enabled by default", !/ disabled/.test(h));
  check("disabled on request, with its own title", / disabled>/.test(handleHtml("x", { disabled: true, title: "Stop recording" }))
    && handleHtml("x", { title: "Stop recording" }).includes('title="Stop recording"'));
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
