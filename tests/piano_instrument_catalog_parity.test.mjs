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

import { INSTRUMENTS as CATALOG } from "../arsenal/web/piano/instruments/catalog.js";
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
const page = idsFromSource("arsenal/web/piano.js", "const INSTRUMENTS");
check("piano.js's instrument list is readable", !page.error, page.error || "");
if (!page.error) eq("piano.js matches the catalogue", page.ids, catalogIds);

const reg = idsFromSource("arsenal/web/piano/looks/registry.js", "const INSTRUMENTS");
check("registry.js's instrument list is readable", !reg.error, reg.error || "");
if (!reg.error) eq("looks/registry.js matches the catalogue", reg.ids, catalogIds);

// The lab module cannot be IMPORTED here: it touches `location` and `document` at module scope
// (piano-lab-instruments.js:18-19), so Node throws before the export is reachable. Read it as text,
// the same way as the other two. That is not a workaround -- a pin about what a human editing the
// file sees should read what is in the file.
const lab = idsFromSource("arsenal/web/piano-lab-instruments.js", "export const INSTRUMENTS");
check("piano-lab-instruments.js's list is readable", !lab.error, lab.error || "");
if (!lab.error) eq("piano-lab-instruments.js matches the catalogue", lab.ids, catalogIds);

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
const stranded = onDisk.filter((id) => !catalogIds.includes(id));
eq("no instrument module is stranded off the catalogue", stranded, []);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
