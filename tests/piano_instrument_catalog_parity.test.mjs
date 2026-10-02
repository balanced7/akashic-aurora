// Node test, zero dependencies:  node tests/piano_instrument_catalog_parity.test.mjs
//
// RED FIRST. Three places list the piano's instruments, and on 2026-10-02 they disagreed three ways:
//
//   arsenal/web/piano.js:1239                    14 instruments   the real one, drives the menu and the gate
//   arsenal/web/piano/looks/registry.js:51       10               missing the four light sculptures
//   arsenal/web/piano-lab-instruments.js:16       6               missing EIGHT
//
// MEASURED IN A BROWSER, not inferred. Served from the live arsenal server, the lab's picker rendered
// six links -- vintage-synth, keylab88mk3, upright, suitcase-ep, concert-grand, glass-piano -- while
// the main page's selector offered fourteen and every one of them worked: the API, the select's change
// event, the instrument cards, persistence, and a cold boot with a light sculpture stored. So the
// visualizer's own selector is healthy. What is broken is that the LAB cannot reach eight of the
// instruments it exists to audition, including every instrument added since it was written: aether,
// solstice, nocturne, crystal-study and all four light sculptures.
//
// THE CAUSE IS A RITUAL, AND THE FILE ADMITS IT. piano-lab-instruments.js:7 reads
// "// Builders: add your instrument id to INSTRUMENTS." A builder who adds an instrument must remember
// to edit a second, and then a third, file. Eight instruments were added and none of the three lists
// agree, which is what a remembered ritual produces over time. registry.js:46 is the same story in a
// comment: it says its choices are "schemes and instruments piano.js:1205-1223", and that line range is
// ALREADY STALE -- the list now starts at 1239. The copy records where it was copied from and then
// drifts from it silently.
//
// WHY A PARITY PIN RATHER THAN THREE CORRECTED LISTS. Correcting the lists fixes today and leaves the
// ritual in place for the next instrument. This pin fails the moment any two of the three disagree, so
// the drift cannot return quietly. It is the same shape as the arm-command fix earlier today, where
// boot and the stop hook each built their own version of one string and handed out different answers.

import { INSTRUMENTS as CATALOG, BUILTIN_INSTRUMENT, MOUNTABLE_INSTRUMENT_IDS }
  from "../arsenal/web/piano/instruments/catalog.js";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
let pass = 0, fail = 0;
const check = (label, ok, detail = "") => { if (ok) { pass++; return; } fail++; console.log(`FAIL ${label}${detail ? ": " + detail : ""}`); };
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want), `\n     got  ${JSON.stringify(got)}\n     want ${JSON.stringify(want)}`);

// piano.js and registry.js are browser modules that import three.js and touch the DOM at import time,
// so their lists are read as TEXT rather than imported. Reading the source is the point here anyway:
// the pin is about what a human editing that file sees.
const idsFromSource = (relPath, startMarker) => {
  const src = readFileSync(join(ROOT, relPath), "utf8");
  const at = src.indexOf(startMarker);
  if (at < 0) return { error: `marker ${JSON.stringify(startMarker)} not found in ${relPath}` };
  // take the array literal that follows, to its first closing bracket at the same nesting
  const open = src.indexOf("[", at);
  let depth = 0, end = -1;
  for (let i = open; i < src.length; i++) {
    if (src[i] === "[") depth++;
    else if (src[i] === "]") { depth--; if (depth === 0) { end = i; break; } }
  }
  const body = src.slice(open, end + 1);
  // ids appear either as `id: "x"` (piano.js) or as opt("x", ...) (registry.js)
  // three spellings, one meaning: `id: "x"` (piano.js), `opt("x", ...)` (registry.js), and a bare
  // "x" in a string array (the lab). That three spellings exist at all is the defect this pin guards.
  const ids = /id:\s*"/.test(body) || /opt\(/.test(body)
    ? [...body.matchAll(/(?:id:\s*|opt\(\s*)"([a-z0-9-]+)"/g)].map((m) => m[1])
    : [...body.matchAll(/"([a-z0-9-]+)"/g)].map((m) => m[1]);
  return { ids };
};

const catalogIds = CATALOG.map((i) => i.id);

// ---------------------------------------------------------------- P1: the catalogue is the source
check("the catalogue exists and is non-trivial", catalogIds.length >= 14,
  `only ${catalogIds.length} instrument(s)`);
check("every catalogue entry has an id and a name",
  CATALOG.every((i) => typeof i.id === "string" && /^[a-z0-9-]+$/.test(i.id) && typeof i.name === "string" && i.name),
  JSON.stringify(CATALOG.filter((i) => !i.id || !i.name)));
check("catalogue ids are unique", new Set(catalogIds).size === catalogIds.length);

// ---------------------------------------------------------------- P2-P4: the three readers agree
// A reader may DERIVE from the catalogue -- it then cannot drift, which is the goal -- or keep its
// own list that happens to match today. Deriving passes outright; a copy is compared element for
// element, because a copy is exactly what drifted here before.
for (const [label, relPath, marker] of [
  ["piano.js", "arsenal/web/piano.js", "const INSTRUMENTS"],
  ["looks/registry.js", "arsenal/web/piano/looks/registry.js", "const INSTRUMENTS"],
  ["piano-lab-instruments.js", "arsenal/web/piano-lab-instruments.js", "export const INSTRUMENTS"],
]) {
  const src = readFileSync(join(ROOT, relPath), "utf8");
  if (src.includes("instruments/catalog.js")) {
    check(label + " derives from the catalogue", true);
    continue;
  }
  const got = idsFromSource(relPath, marker);
  check(label + " keeps its own list and it is readable", !got.error, got.error || "");
  if (!got.error) eq(label + " keeps its own list and it still matches", got.ids, catalogIds);
}

// ---------------------------------------------------------------- P5: every id has a module on disk
// A list that names an instrument with no file is the mirror defect: the menu offers something that
// cannot load. Checked against the directory rather than a second list.
const missingModule = catalogIds.filter((id) => {
  if (id === "page") return false;                       // the built-in, drawn by the page itself
  try { readFileSync(join(ROOT, "arsenal/web/piano/instruments", `${id}.js`), "utf8"); return false; }
  catch { return true; }
});
eq("every catalogued instrument has a module on disk", missingModule, []);

// ---------------------------------------------------------------- P6: no module is stranded
// The defect that started this: a file exists, the lab cannot reach it. Any instrument module on disk
// that no list mentions is invisible to everyone, which is how aether, solstice and nocturne sat
// unreachable in the lab while shipping on the main page.
const onDisk = readdirSync(join(ROOT, "arsenal/web/piano/instruments"))
  .filter((f) => f.endsWith(".js") && f !== "catalog.js")
  .map((f) => f.replace(/\.js$/, ""));
// NOT EVERY FILE HERE IS AN INSTRUMENT. crystal-study.js exports a factory, crystalInstrument(id),
// that aether, solstice and nocturne each import to build themselves. It has no DEFAULT export, and
// piano.js's own lookModuleProblem rejects a module without one ("the module has no default export
// object"), so presence on disk is the wrong test -- I nearly catalogued that helper as an
// instrument while writing this. An instrument is a module with a default export.
// A plain substring, not a regex. Three attempts to write this as a regex through a shell heredoc
// produced a LITERAL BACKSPACE where the  was meant and a doubled backslash where \s was, so the
// check silently returned false for every module -- which made the "stranded" pin pass VACUOUSLY,
// because filtering on an always-false predicate yields an empty list either way. A pin that can
// only pass is worse than no pin. The phrase is unambiguous; no regex is needed.
const hasDefaultExport = (id) =>
  readFileSync(join(ROOT, "arsenal/web/piano/instruments", id + ".js"), "utf8")
    .includes("export default");
const stranded = onDisk.filter((id) => hasDefaultExport(id) && !catalogIds.includes(id));
eq("no instrument module is stranded off the catalogue", stranded, []);

// And the mirror: nothing in the catalogue may be a helper rather than an instrument.
const notInstruments = catalogIds.filter((id) => id !== BUILTIN_INSTRUMENT && !hasDefaultExport(id));
eq("every catalogued id is a real instrument module, not a shared helper", notInstruments, []);

// ---------------------------------------------------------------- the built-in is not mountable
// A reader that MOUNTS an instrument imports instruments/<id>.js, and the built-in has no such file:
// the page draws its own keys. I shipped exactly this bug while wiring the lab to the catalogue --
// "page" appeared in its picker and selecting it died with "Failed to fetch dynamically imported
// module: .../instruments/page.js". Found by clicking the entry I had just added, which the parity
// pin could never have caught: the lists agreed perfectly and one of the ids was unusable.
check("the built-in is in the catalogue", catalogIds.includes(BUILTIN_INSTRUMENT));
check("the built-in is NOT offered as mountable",
  !MOUNTABLE_INSTRUMENT_IDS.includes(BUILTIN_INSTRUMENT),
  `${BUILTIN_INSTRUMENT} would 404 in any reader that imports instruments/<id>.js`);
eq("mountable is the catalogue minus the built-in",
  [...MOUNTABLE_INSTRUMENT_IDS], catalogIds.filter((id) => id !== BUILTIN_INSTRUMENT));
check("every mountable id really has a module on disk",
  MOUNTABLE_INSTRUMENT_IDS.every((id) => onDisk.includes(id)),
  JSON.stringify(MOUNTABLE_INSTRUMENT_IDS.filter((id) => !onDisk.includes(id))));

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
