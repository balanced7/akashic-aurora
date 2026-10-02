// THE instrument catalogue. One list, three readers.
//
// WHY THIS FILE EXISTS (2026-10-02). The piano's instruments were listed in three places and all
// three disagreed:
//
//   arsenal/web/piano.js                 14 entries   the menu and the selectInstrument gate
//   arsenal/web/piano/looks/registry.js  10           missing the four light sculptures
//   arsenal/web/piano-lab-instruments.js  6           missing eight
//
// So the standalone lab, whose whole job is auditioning one instrument, could not reach aether,
// solstice, nocturne, crystal-study or any of the four light sculptures -- every instrument added
// since the lab was written. Measured in a browser: the lab's picker rendered six links while the
// main page's selector offered fourteen and every one of them worked.
//
// NOT EVERY FILE IN THIS DIRECTORY IS AN INSTRUMENT, and the distinction is load-bearing rather
// than tidy. crystal-study.js exports a FACTORY, `crystalInstrument(id)`, which aether.js,
// solstice.js and nocturne.js each import to build themselves; it has no default export, so
// piano.js's own lookModuleProblem would reject it with "the module has no default export object".
// An instrument module is one with a DEFAULT EXPORT, and that is what the parity pin checks, not
// mere presence on disk. I nearly put this helper in the menu while writing the catalogue.
//
// Both copies admitted what they were. The lab carried "// Builders: add your instrument id to
// INSTRUMENTS", a ritual a builder has to remember in a third file; and the registry said its
// choices came from "piano.js:1205-1223", a line range that was already stale. A copy that records
// where it was copied from still drifts, and drifts silently.
//
// ADDING AN INSTRUMENT IS NOW ONE EDIT: drop <id>.js in this directory and add its row here.
// tests/piano_instrument_catalog_parity.test.mjs fails if any reader disagrees with this list, if a
// catalogued id has no module on disk, or if a module on disk is missing from this list -- that last
// one being the defect that started it.
//
// ORDER IS THE MENU ORDER and it is deliberate: the page's own keys first, then controllers and
// acoustic instruments, then the crystal collection, then the light sculptures. `page` is the
// built-in (LOOK_BUILTIN.instrument in piano.js) and is drawn by the page itself, so it is the one
// id with no module file.

export const INSTRUMENTS = Object.freeze([
  { id: "page", name: "Page keys" },
  { id: "keylab88mk3", name: "KeyLab 88 mk3" },
  { id: "concert-grand", name: "Concert grand" },
  { id: "upright", name: "Upright" },
  { id: "suitcase-ep", name: "Suitcase EP" },
  { id: "vintage-synth", name: "Vintage synth" },
  { id: "glass-piano", name: "Crystal grand" },
  { id: "aether", name: "Aether" },
  { id: "solstice", name: "Solstice" },
  { id: "nocturne", name: "Nocturne" },
  { id: "light-kimi-aurora", name: "Aurora Harp" },
  { id: "light-deepseek-orrery", name: "Orrery of Light" },
  { id: "light-vandor-ornithopter", name: "Ornithopter" },
  { id: "light-vandor-abyssal", name: "Abyssal" },
].map(Object.freeze));

/** Ids only, in menu order. */
export const INSTRUMENT_IDS = Object.freeze(INSTRUMENTS.map((i) => i.id));

/** The one id with no module file: the page draws its own keys. */
export const BUILTIN_INSTRUMENT = "page";

/**
 * Ids that have a module to import, i.e. everything but the built-in.
 *
 * For readers that MOUNT an instrument by importing `instruments/<id>.js`, which the built-in has
 * no file for. The standalone lab is one: pointing it at `?id=page` fails with "Failed to fetch
 * dynamically imported module: .../instruments/page.js". I introduced exactly that while wiring the
 * lab to this catalogue and caught it by clicking the entry I had just added, which is the argument
 * for driving a UI after changing the list behind it rather than trusting the parity pin.
 */
export const MOUNTABLE_INSTRUMENT_IDS = Object.freeze(
  INSTRUMENTS.filter((i) => i.id !== BUILTIN_INSTRUMENT).map((i) => i.id),
);
