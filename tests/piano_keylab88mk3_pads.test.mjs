// Node test, zero dependencies:  node tests/piano_keylab88mk3_pads.test.mjs
//
// The piano page's 3D KeyLab (arsenal/web/piano/instruments/keylab88mk3.js) lays its 12 pads out where they sit on the
// real unit, and each pad lights for the note that pad really plays.
//
// Daniel, 2026-10-23, at the device: "your pad representation shows pad 1 on the right when its actually the top left
// most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is 9-12 ^__^!" Until then the twin drew a 2 x 6 block
// in pitch-class order (front row C..F, back row F#..B), which is not the unit's shape. The truth is 3 rows x 4:
//     back row (farthest from the player)   pads 1-4  = notes 44-47 = G# A A# B
//     middle row                            pads 5-8  = notes 40-43 = E F F# G
//     front row (nearest the player)        pads 9-12 = notes 36-39 = C C# D D#
// Both halves are read from arsenal/keylab/protocol.py itself (GRID and PAD_NOTE), so the twin cannot drift from the
// device facts. Only the order and the row count are confirmed; the millimetre geometry stays an estimate, except that
// the block stays centred where the old one was (the close camera frames that spot).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { PAD_LAYOUT } from "../arsenal/web/piano/instruments/keylab88mk3.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
let pass = 0, fail = 0;
const check = (label, ok, detail = "") => { if (ok) { pass++; return; } fail++; console.log(`FAIL ${label}${detail ? ": " + detail : ""}`); };
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want), `\n     got  ${JSON.stringify(got)}\n     want ${JSON.stringify(want)}`);

// the device facts, from the one copy
const protocol = readFileSync(join(ROOT, "arsenal", "keylab", "protocol.py"), "utf8");
const gridSrc = /^GRID = (\[\[.*\]\])\s*$/m.exec(protocol);
const noteSrc = /^PAD_NOTE = (\{.*\})\s*$/m.exec(protocol);
check("protocol.py has one GRID line and one PAD_NOTE line", !!gridSrc && !!noteSrc);
const GRID = JSON.parse(gridSrc[1]);                                             // rows top to bottom
const PAD_NOTE = JSON.parse(noteSrc[1].replace(/(\d+):/g, '"$1":'));
eq("protocol.GRID is 4 across x 3 down in reading order", GRID, [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]);

// the twin
check("12 pads", PAD_LAYOUT.length === 12, String(PAD_LAYOUT.length));
eq("instance i is pitch class i (what update() lights)", PAD_LAYOUT.map((p) => p.pc), [...Array(12).keys()]);
eq("every pad number once", PAD_LAYOUT.map((p) => p.pad).sort((a, b) => a - b), [...Array(12).keys()].map((i) => i + 1));
for (const p of PAD_LAYOUT) {
  check(`pad ${p.pad} lights its own note's pitch class (PAD_NOTE ${PAD_NOTE[p.pad]} -> ${PAD_NOTE[p.pad] % 12})`, PAD_NOTE[p.pad] % 12 === p.pc, `pc ${p.pc}`);
  check(`pad ${p.pad} sits where GRID puts it (row ${p.row} from the front, column ${p.col})`, GRID[GRID.length - 1 - p.row][p.col] === p.pad);
}

// 3 rows x 4, by position: the row index, the column index and the millimetres all agree
const zs = [...new Set(PAD_LAYOUT.map((p) => p.zmm))].sort((a, b) => a - b);
const xs = [...new Set(PAD_LAYOUT.map((p) => p.xmm))].sort((a, b) => a - b);
check("3 rows (3 distinct depths) x 4 columns (4 distinct x)", zs.length === 3 && xs.length === 4, `rows ${zs} cols ${xs}`);
check("12 distinct positions", new Set(PAD_LAYOUT.map((p) => `${p.xmm},${p.zmm}`)).size === 12);
for (const p of PAD_LAYOUT) {
  check(`pad ${p.pad}: depth matches its row, x matches its column`, zs.indexOf(p.zmm) === p.row && xs.indexOf(p.xmm) === p.col);
}
const rowPcs = (r) => PAD_LAYOUT.filter((p) => p.row === r).sort((a, b) => a.col - b.col);
eq("front row (nearest the player), left to right: pads 9-12 = C C# D D#", rowPcs(0).map((p) => [p.pad, p.pc]), [[9, 0], [10, 1], [11, 2], [12, 3]]);
eq("middle row: pads 5-8 = E F F# G", rowPcs(1).map((p) => [p.pad, p.pc]), [[5, 4], [6, 5], [7, 6], [8, 7]]);
eq("back row: pads 1-4 = G# A A# B", rowPcs(2).map((p) => [p.pad, p.pc]), [[1, 8], [2, 9], [3, 10], [4, 11]]);
const leftmost = PAD_LAYOUT.reduce((a, b) => (b.xmm < a.xmm || (b.xmm === a.xmm && b.zmm > a.zmm) ? b : a));
check("pad 1 is the back-left pad (the unit's top-left, farthest from the player)", leftmost.pad === 1, `got pad ${leftmost.pad}`);

// geometry: same 33 mm pitch, block centred where the 2 x 6 block was (x 306.5 + 2.5 x 33 = 389, z (212 + 245) / 2 = 228.5)
check("33 mm pitch both ways", xs.every((x, i) => i === 0 || x - xs[i - 1] === 33) && zs.every((z, i) => i === 0 || z - zs[i - 1] === 33), `${xs} / ${zs}`);
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
check("centred where the old block was (389, 228.5)", mean(xs) === 389 && mean(zs) === 228.5, `${mean(xs)}, ${mean(zs)}`);

console.log(`keylab88mk3 pads: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
