// Node pins for arsenal/boost.py -- the REFEREE: make a dark frame legible, and measure whether it
// has radial structure. Zero dependencies:  node tests/boost.test.mjs  ... via the python twin.
//
// WHY THIS EXISTS. On 2026-09-18 two observers disagreed about a frame whose whole signal sits in
// the bottom 5% of the luma range (std 0.0055): a vision model said "concentric rings", a human
// eye said "near-uniform with a faint smear". Arguing settles nothing; what both readers need is
// the SAME frame with its range stretched so the structure is visible or provably absent, plus a
// number that needs no eyes at all. boost() is the stretched view; annuli() is the number -- the
// mean luma of concentric annuli, centre to edge. A monotone fall is a glow or a gradient; a rise
// AWAY from the centre and a later fall is radial banding (rings). That one test settled the
// dispute in a single command.
//
// These pins drive the Python module through its own CLI to avoid reimplementing its math here;
// the arithmetic under test is the ANNULUS GEOMETRY and the BANDED verdict, which are what a wrong
// referee would get wrong silently.
import { execFileSync } from "node:child_process";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// The frames are built in Python (numpy is there); here we only drive it and assert the JSON.
const py = `
import json, sys, numpy as np
sys.path.insert(0, r"E:/AI-Setup")
from arsenal import boost as B

def frame(kind, shape=(180, 240)):
    a = np.zeros(shape, np.float32)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((yy - h/2)/(h/2))**2 + ((xx - w/2)/(w/2))**2)
    if kind == "centre":
        a[r < 0.25] = 1.0
    elif kind == "ring":
        a[(r >= 0.25) & (r < 0.5)] = 1.0
    elif kind == "flat":
        a[:] = 0.23
    return (a * 255).astype(np.uint8)

print(json.dumps({
  "centre": B.radial_summary(frame("centre")),
  "ring":   B.radial_summary(frame("ring")),
  "flat":   B.radial_summary(frame("flat")),
  "boost_shape": list(B.boost(frame("ring")).shape),
  "boost_minmax": [int(B.boost(frame("ring")).min()), int(B.boost(frame("ring")).max())],
  "boost_dtype": str(B.boost(frame("ring")).dtype),
}))
`;

let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  report.push(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const dir = mkdtempSync(join(tmpdir(), "boost-test-"));
try {
  const script = join(dir, "probe.py");
  writeFileSync(script, py, "utf8");
  const out = execFileSync("py", [script], { encoding: "utf8", cwd: "E:/AI-Setup" });
  const d = JSON.parse(out);
  const ann = (k) => d[k].annuli;

  // ------------------------------------------------------------ the annulus geometry
  check("a centre blob peaks at the CENTRE annulus", ann("centre")[0] > ann("centre")[1]);
  check("...and falls monotonically outward",
    ann("centre").every((v, i) => i === 0 || ann("centre")[i - 1] >= v - 1e-9));
  check("a ring peaks at an INTERIOR annulus, not the centre", ann("ring")[1] > ann("ring")[0]);
  check("...and the ring frame is not monotone", !ann("ring").every((v, i) => i === 0 || ann("ring")[i - 1] >= v - 1e-9));
  check("a flat frame's annuli are all equal",
    ann("flat").every((v) => Math.abs(v - ann("flat")[0]) < 1e-6));

  // ------------------------------------------------------------ the banded verdict
  check("radial banding is DETECTED on the ring", d.ring.banded === true, JSON.stringify(d.ring));
  check("...and NOT on the centre blob", d.centre.banded === false, JSON.stringify(d.centre));
  check("...and NOT on the flat frame", d.flat.banded === false, JSON.stringify(d.flat));
  check("the verdict carries a reason in words", typeof d.ring.reason === "string" && d.ring.reason.length > 0);

  // ------------------------------------------------------------ the boosted view
  check("boost preserves the frame shape", JSON.stringify(d.boost_shape) === JSON.stringify([180, 240, 3]));
  check("boost returns uint8", d.boost_dtype === "uint8");
  check("boost stretches to the full range", d.boost_minmax[0] === 0 && d.boost_minmax[1] === 255);
} finally {
  rmSync(dir, { recursive: true, force: true });
}

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
