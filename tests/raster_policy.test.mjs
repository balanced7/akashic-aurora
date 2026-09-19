// Node pins for arsenal/web/lib/raster-policy.js -- the reusable RESOLUTION POLICY.
// Zero dependencies:  node tests/raster_policy.test.mjs
//
// WHY THIS EXISTS. A render canvas must serve two consumers with opposite requirements: the DISPLAY
// wants a raster sized to the viewing window, and the RECORDER wants a fixed capture tier. The host
// page conflated them -- it renders the record tier (framing 1080x1920 x renderScale 4/3 = 1440x2560)
// and then CSS-scales that into whatever box the layout gives, so the live view paid for 7.7x more
// pixels than it showed at 1920x1080 and could not gain detail on a big display. Measured
// 2026-09-18 by arsenal/lanes/alias_verify.mjs. The policy below is that separation, as data.
//
// The pins state the RULES, not the implementation: the raster follows the DISPLAY, the tier is for
// capture, the budget and the legibility floor both declare themselves, and a resolution change
// never happens for a change too small to see (a buffer reallocation per resize event is the classic
// thrash). Numbers are hand-computed from the box sizes in the measurement above.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  ASPECTS, containRect, createRasterPolicy, logicalFrame, pixelsChanged, rasterFor,
} from "../arsenal/web/lib/raster-policy.js";

let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  report.push(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
const near = (label, got, want, eps = 0.01) => check(label, Math.abs(got - want) <= eps,
  `got ${got} want ${want} (+-${eps})`);
const here = (p) => fileURLToPath(new URL(p, import.meta.url));

// --------------------------------------------------------------- the logical frame is design space
const portrait = logicalFrame("9:16", 1920);
eq("a 9:16 frame at 1920 tall is 1080 wide", [portrait.w, portrait.h], [1080, 1920]);
eq("...and carries its own aspect", portrait.aspect, 0.5625);
eq("a 16:9 frame at 1080 tall is 1920 wide", [logicalFrame("16:9", 1080).w, logicalFrame("16:9", 1080).h], [1920, 1080]);
check("ASPECTS names every supported ratio", ASPECTS["9:16"] === 9 / 16 && ASPECTS["16:9"] === 16 / 9);
let threw = false;
try { logicalFrame("9:16-ish", 1920); } catch { threw = true; }
check("an unknown aspect id is REFUSED, never silently defaulted to 16:9", threw);

// ----------------------------------------------------------------- the stage inside the window box
// The box is the space the layout actually gives the stage; the frame is letterboxed inside it.
const fit = containRect(portrait, 1920, 1080);
eq("a portrait frame in a landscape box fits by HEIGHT, centred", [fit.h, fit.y], [1080, 0]);
near("...its width is frame.w scaled by 0.5625", fit.w, 607.5);
near("...and it is centred horizontally", fit.x, 656.25);
const tight = containRect(portrait, 400, 900);
near("a narrow box fits by WIDTH instead", tight.w, 400);
check("...never overflowing its box", tight.w <= 400 + 1e-6 && tight.h <= 900 + 1e-6);

// --------------------------------------------------- THE HEADLINE: the raster follows the DISPLAY
// 518x921 is the CSS box the /piano layout gave the 3D canvas at 1920x1080 (alias_verify, dpr 1).
const displayed = rasterFor({ cssW: 518, cssH: 921, dpr: 1 });
eq("the raster is the box, not the record tier", [displayed.w, displayed.h], [518, 921]);
eq("...477,078 pixels instead of the 3,686,400 it was paying for", displayed.pixels, 477078);
eq("...and nothing was clamped", displayed.clampedBy, null);
check("...which is the very rule the 2D sibling canvas already follows",
  JSON.stringify([rasterFor({ cssW: 518, cssH: 921, dpr: 2 }).w, rasterFor({ cssW: 518, cssH: 921, dpr: 2 }).h])
  === JSON.stringify([1036, 1842]));
eq("the 2D sibling's pixel count at dpr 2", rasterFor({ cssW: 518, cssH: 921, dpr: 2 }).pixels, 1908312);
eq("a 1.25 supersample is a deliberate cost, applied exactly",
  [rasterFor({ cssW: 518, cssH: 921, dpr: 1, qualityScale: 1.25 }).w,
   rasterFor({ cssW: 518, cssH: 921, dpr: 1, qualityScale: 1.25 }).h,
   rasterFor({ cssW: 518, cssH: 921, dpr: 1, qualityScale: 1.25 }).pixels], [648, 1151, 745848]);

// --------------------------------------------------------------------------- the budget, declared
const clamped = rasterFor({ cssW: 1920, cssH: 1080, dpr: 2 });   // raw would be 3840x2160 = 8,294,400
check("over budget, the raster is clamped", clamped.pixels <= 4000000, `${clamped.pixels}`);
eq("...and the clamp is NAMED, never silent", clamped.clampedBy, "maxPixels");
check("...while keeping the aspect", Math.abs(clamped.w / clamped.h - 16 / 9) < 0.01, `${clamped.w}x${clamped.h}`);
check("...and saying why in words", typeof clamped.reason === "string" && clamped.reason.length > 0);

// The legibility floor beats the budget, and the conflict is VISIBLE rather than hidden.
const floored = rasterFor({ cssW: 1920, cssH: 1080, dpr: 2, maxPixels: 100000, minScale: 0.5 });
eq("a legibility floor wins over an impossible budget", [floored.w, floored.h], [1920, 1080]);
eq("...and names itself as the deciding constraint", floored.clampedBy, "minScale");
check("...so the over-budget conflict is reported, not swallowed", floored.pixels > 100000);

// A zero or nonsense box is a CALLER bug: refuse it rather than rendering a 1px picture that reads
// as a black canvas later ("absence renders as normal").
let refused = false;
try { rasterFor({ cssW: 0, cssH: 921, dpr: 1 }); } catch { refused = true; }
check("a zero-width box is refused, not quietly rendered", refused);

// ------------------------------------------------------------------ the thrash guard (hysteresis)
eq("a 1% pixel change is not worth reallocating buffers",
  pixelsChanged({ w: 518, h: 921 }, { w: 520, h: 924 }), false);
eq("a 83% change is", pixelsChanged({ w: 518, h: 921 }, { w: 700, h: 1245 }), true);

// ------------------------------------------------------------------- the policy as a live object
const policy = createRasterPolicy({ maxPixels: 4000000 });
const first = policy.resize({ cssW: 518, cssH: 921, dpr: 1 });
eq("the first resize commits", [first.committed, first.w, first.h], [true, 518, 921]);
const jitter = policy.resize({ cssW: 519, cssH: 922, dpr: 1 });
eq("a jittery resize does NOT reallocate", jitter.committed, false);
eq("...and the raster it reports is the one still in use", [jitter.w, jitter.h], [518, 921]);
const big = policy.resize({ cssW: 1100, cssH: 1956, dpr: 1 });
eq("a real resize commits", [big.committed, big.w, big.h], [true, 1100, 1956]);
eq("...and the change count is honest about how often buffers were made", policy.report().changes, 2);

// ----------------------------------------------------------- adaptive resolution is off by default
const still = createRasterPolicy({});
for (let i = 0; i < 40; i++) still.observeFrameTime(50);
eq("with adaptive off, slow frames change nothing", still.report().adaptive.scale, 1);
eq("...and the report says it is off", still.report().adaptive.enabled, false);
eq("...with no steps taken", still.report().adaptive.steps_down, 0);

// ...and when asked for, it steps down on a slow budget and back up to the DISPLAY requirement only.
const adaptive = createRasterPolicy({ adaptive: { targetMs: 8, downAfter: 20, upAfter: 40 } });
adaptive.resize({ cssW: 1100, cssH: 1956, dpr: 1 });
for (let i = 0; i < 25; i++) adaptive.observeFrameTime(40);
check("slow frames step the resolution down", adaptive.report().adaptive.scale < 1,
  `${adaptive.report().adaptive.scale}`);
check("...and the step is counted", adaptive.report().adaptive.steps_down >= 1);
const cheaper = adaptive.resize({ cssW: 1100, cssH: 1956, dpr: 1 });
check("...so the same box now renders fewer pixels", cheaper.w * cheaper.h < 1100 * 1956,
  `${cheaper.w}x${cheaper.h}`);
for (let i = 0; i < 90; i++) adaptive.observeFrameTime(2);
eq("headroom restores the full resolution", adaptive.report().adaptive.scale, 1);
check("...and NEVER overshoots the display requirement (over-rendering is the bug this module kills)",
  adaptive.report().adaptive.scale <= 1);

// --------------------------------------------------------------- portable: no page globals inside
// The policy must run headless (in this test) and in any future page, so it may not reach for the
// page's own ambient objects. Prose is allowed to DESCRIBE them; the check is for real references.
const source = readFileSync(here("../arsenal/web/lib/raster-policy.js"), "utf8");
check("the policy never touches the DOM (portable to Node and to any future page)",
  !/\bdocument\s*\.|\bwindow\s*\.|requestAnimationFrame/.test(source));

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
