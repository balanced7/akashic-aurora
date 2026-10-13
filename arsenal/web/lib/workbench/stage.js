// arsenal/web/lib/workbench/stage.js -- the STAGE: one canvas that can host the shader lab runtime
// (arsenal/web/shaderlab/toy-runtime.js), behind a still, behind a button.
//
// WHY A BUTTON BEFORE ANY PIXEL. Daniel's machine has an AMD display-driver crash (TDR) history, and Windows resets the
// GPU when one submission runs past about two seconds. A page that starts a strangers' raymarcher the moment it opens
// is how that history repeats. Ruling 5 (build-spec-reconciled.md) makes the lab safe by default, and this file is
// where it is kept:
//
//   * VIEW ONLY UNTIL A DELIBERATE LOCAL SETTING. The whole live path sits behind ONE switch, read once when the Stage
//     mounts (liveSwitch): it is on only when the page's address asks for it (?live=1) AND this browser holds the key
//     (localStorage 'arsenal.shaderlab.live' set to 'on'); either alone is off, and so is a storage that cannot be read.
//     Off, which is the default, the Stage shows the subject's SwiftShader still and plays its filmstrip (a window
//     stepped across the contact sheet: an image, no GPU work), says "Live runs are off until their safety review
//     clears", and has no Run button, no scale, no Stop and no Take. Nothing then loads the runtime, makes a canvas or
//     asks for a WebGL context: the one place that does all three (build) and the one that loads the runtime (loadLive)
//     both begin with mustBeLive(), which throws while the switch is off, and every way in (start, resume, rebuild,
//     setScale, setParams) returns before reaching them. arsenal/web/shaderlab/README.md says how to turn it on. With
//     the switch on, everything below holds.
//   * NOTHING RENDERS LIVE ON PAGE LOAD. A subject arrives as a pre-rendered still (SwiftShader, under the lock). The
//     runtime module is not even imported, no canvas exists and no WebGL context is asked for, until someone presses
//     "Run live on this GPU". tests/workbench_lab.test.mjs counts all three.
//   * THE BUTTON NAMES THE COST FIRST. Before the click it says the subject's cost class (C0 straight-line arithmetic ...
//     C4 stateful) and the scale it will start at, at most. A subject whose class is not known is treated as the
//     heaviest. A shader found at load to keep render targets (buffers), or a card one of whose modules is heavier than
//     its own, is raised before its first frame, and the stage says so.
//   * C3 AND C4 START AT HALF SCALE AT MOST. Half the width and half the height is a quarter of the pixels, so a quarter
//     of the work per frame: the first frame of a heavy shader is the one most likely to stall.
//   * A PRE-FLIGHT BEFORE ANY FULL-SIZE FRAME. The first frames a program ever shades on this GPU are tiny ones
//     (64 x 36), after one draw that shades a single pixel (scissored to 1 x 1) so that a driver's compile at first draw
//     is not billed to them. Frame 0 is timed on purpose (the live run starts on it, and a shader may do its heaviest
//     work there), then frame 1, and the slower counts. Each is timed with the queue drained first, so nothing queued
//     before it (a compile, a buffer reallocation, another program's frame) is billed to it, and ended by a wait the GPU
//     must honour: gl.finish() and then a one-pixel readPixels (drainGl). gl.finish() alone did not wait on SwiftShader
//     through ANGLE (2026-10-13): ldSfWV's 128 x 72 frames read 0 ms, its prediction after a window grew was 227 ms and
//     the next frame took 615 ms; with the read-back the same frames read 11 ms, the prediction was 305 ms and the
//     frames took 238 to 250 ms. A reading under 1 ms is repeated and averaged, so one tick of the timer is not read as
//     cost. A tiny frame that alone takes over 200 ms is refused outright: nothing more runs. When even the heaviest
//     growth (the cube, below) keeps it under the one-frame limit, a second pair at 128 x 72 (four times the pixels)
//     shows how the cost grows with the pixels, as an exponent (1 when it goes with them, 2 when it goes with their
//     square); a tiny frame too heavy for that (from about 7.8 ms) gets its second pair at 90 x 51 (about twice the
//     pixels) when the cube keeps that under the limit, so a heavy one, or one a stall inflated, is not refused on one
//     reading. Guarded only to the square, a cube-law tiny frame of 20 ms drew a 1280 ms 128 x 72 one. Part of every
//     frame does not grow: the read-back's round trip and the submission, paid whatever the size. The one-pixel draw,
//     timed the same way, measures that part, and the growth is judged on the rest, the pixels' own work: behind 0.1 ms
//     of it a square-law cost of 0.03 ms at 64 x 36 reads 0.13 and 0.58 ms, which as totals look linear (and drew a
//     300 ms first frame). It is read twice, before the second pair and after it, and the smaller kept: a hiccup in the
//     timing (a GC pause, the scheduler) only ever adds time. It is in every frame, so it is never taken to be more than
//     the smallest one, and a reading above that is the hiccup, set aside: the part is then anywhere from nothing to
//     that frame. One slow draw read as the part (10 ms beside a 0.34 ms tiny frame) left no work to grow, and the
//     guard below drew a 576 ms pre-flight frame. Each reading is uncertain by the timer's resolution over the draws it
//     averaged, and the stage takes the MOST growth the readings allow: growth they cannot rule out is taken to be
//     there, the way a cost class not declared runs as C4. Far above the resolution that is close to the truth (2.07
//     for a cost that goes with the square of its pixels, read at 0.5 and 8 ms); within it the readings cannot bound
//     the growth, and it is the heaviest, the cube of the pixels. Taking
//     the least they allow instead (as this stage did until 2026-10-13) read two readings within the resolution as
//     linear: a square-law cost read at 0.005 ms at 64 x 36 was predicted at 7.7 ms and drew a 750 ms first frame. One
//     reading alone (a tiny frame too heavy for a second) shows no growth and is taken at the heaviest. While the two
//     largest readings leave the growth unproven (the least and the most they allow more than 0.1 apart), larger pairs
//     follow, four times the pixels each (256 x 144, 512 x 288, 1024 x 576), each only when even the heaviest growth of
//     the pixels' work keeps it under the ladder's 150 ms step cap and it is no larger than the frame at the largest
//     scale the class lets it start at (a C4 subject's half scale): a cheap shader is measured on frames big enough to
//     show its growth, nearer the size it will be drawn at, and never on a frame larger than any it may start on. The
//     work behind every guard and prediction is taken at its most: the reading at its most, less the per-frame part at
//     its LEAST (taking the part at its most off it predicted 25.2 ms for a 25.41 ms frame). Each scale's prediction is
//     the per-frame part at its most plus the largest reading's work at its most, grown to that scale's pixels at that
//     exponent, and never below any reading times its pixel ratio (the spec's linear prediction): for a cost that is a
//     fixed part plus any power of its pixels up to the cube, no prediction is below the frame while the readings are
//     within their uncertainty (and the part's two readings hold at most one hiccup between them). The stage starts at
//     the largest scale whose predicted frame fits the 30 ms budget (never above the class's own start). If even the
//     smallest scale would take past the watchdog's one-frame limit (500 ms), it is refused too; between the budget and
//     that limit it starts at the smallest scale and says so. Think of a crane's test lift: a small load first, and the
//     rated load is worked out from what the small one did, at the worst the lift allows.
//   * THE SIZE THE PRE-FLIGHT MEASURED IS LOCKED. The drawing buffer is the stage box times the device pixel ratio times
//     the scale, and the pre-flight's prediction holds for that size only. So the canvas never changes size while it
//     draws: when the box, the pixel ratio (a window maximised, browser zoom, another monitor) or the scale changes, the
//     stage stops drawing and runs the pre-flight again at the new size before its next frame. It watches the window's
//     resize, the box's own size and a matchMedia query on the pixel ratio, and checks the size before every frame as
//     well. After a change the stage keeps its scale when that draws no more pixels than were measured AND is predicted
//     under the ladder's 150 ms step cap (the bar a step up must meet); otherwise it starts over at the new size as Run
//     does (the 30 ms budget, never above the scale it was at), the frames drawn so far counted with the pre-flight. Run
//     again after a Stop does the same when the size moved meanwhile.
//   * RAISING THE SCALE IS A LADDER. One step at a time above the scale last measured (also when chosen while
//     stopped), only after a few frames have been measured there, each step predicted from the SLOWEST of the recent
//     frames (a spike every few frames is what the next step meets, so not their median) grown by the real pixel count
//     of the step (the box as it is now) to the pre-flight's growth exponent. A step is allowed only under a 150 ms cap, well below the 500 ms one-frame limit (Windows resets
//     at about 2 s). The step itself is a size change, so the pre-flight runs again there, and the step is kept only if
//     the fresh numbers agree; a reading that came out high once caps one attempt, never the whole run. Measured on
//     SwiftShader (ldSfWV at a device pixel ratio of 2, 2026-10-13, timed then with gl.finish() alone): one tiny frame
//     predicted 271 ms at 1 x, and a jump to 1 x drew a 2174 ms frame; its cost also grows as its buffers fill, which
//     no first frame can see. With the ladder (read-back wait, 150 ms cap) lfscD7 climbed to 0.75 x, 1 x was refused at
//     368 ms predicted, and its slowest frame was 207.5 ms.
//   * THE HOUSE WATCHDOG, WITH A TIME BUDGET. While requestAnimationFrame is actually firing, a frame more than 55 ms
//     after the last one is slow. The stage stops and HOLDS THE LAST FRAME when 45 slow frames come in a row (the agent
//     avatar's rule, scripts/agent-avatar.js, for light stutter), when the slow frames in a row add up past 2500 ms, or
//     at once when one frame arrives more than 500 ms after the last. After ANY hold, Run again measures the program
//     again and continues below the frames that held: no more pixels than one scale step below the drawing buffer that
//     tripped, at the box and pixel ratio as they are then (a window moved to a 2x display while held finds 0.25 x
//     there as large as the 0.5 x that held). When no scale is that small, nothing more runs for that subject, and a
//     refusal lasts for the page: picking the same subject again does not run it. The frame in flight when the loop
//     stops for anything but a hold (Stop, the Shelf tab, a knob change, a size change, another subject) is judged
//     first, its queue drained, as the next frame would have judged it; and each frame judges the one before it ahead
//     of anything else. The avatar's lesson stands: a hidden tab throttles rAF, so only frames delivered while the page
//     is visible are judged.
//   * LEAVING THE STAGE STOPS IT. A hidden tab, or the Shelf tab in front (any view that hides the Stage), cancels the
//     loop (not merely skips it), and coming back does NOT restart it: Run again is an explicit click, which continues
//     the clock where it stopped (iTime does not jump) from a fresh watchdog window.
//   * A KNOB NEVER DRAWS OUTSIDE THE LOOP. A knob change rebuilds the program only while the stage is drawing: the loop
//     stops before the compile (which holds the main thread), the program on stage finishes its queued frame (they share
//     one GPU) and that frame is judged, the rebuilt program is pre-flighted at Run's own budget, and only then swapped
//     in. One that does not compile, or that the pre-flight refuses, is freed and the loop goes on from a fresh watchdog
//     window: the compile and the refused tiny frames held the main thread, not the GPU. On a stopped, held or hidden
//     stage the change waits for Run again. Overlapping rebuilds land in order: only the newest knob values are ever
//     swapped in.
//
//   const stage = mountStage(doc, el, { loadRuntime: () => import('/lab/toy-runtime.js'), onReceipt, onTake, isAway });
//   stage.setSubject({ kind, id, title, byline, licence, cost: 'C3', poster: [urls], swiftshader: {warmMs, size},
//                      film: {sheet, frames, to}, standIns: [...], load: async (params) => ({ shader, mediaUrl,
//                      cost: {cls, why}, receipt: {modules, sha, ...} }) });
//   stage.suspend('you switched to the Shelf');   // a host hiding the Stage
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, takes the document as an argument.
import { COSTS, costRank, h, imgFrom, normCost, panel, put, setClass, standInLines } from './common.js';
import { FILM, sheetFrame } from './shelf.js';

// ------------------------------------------------------------------------------------------ the switch --
// The one switch in front of the live path (arsenal/web/shaderlab/README.md, "Live runs: off until a deliberate local
// setting"). On only when the page's address asks for it (?live=1) AND this browser holds the key (localStorage[key]
// === 'on'): a link alone cannot turn it on, and neither can a key left behind on a page opened without ?live=1.
export const LIVE_SWITCH = Object.freeze({ param: 'live', value: '1', key: 'arsenal.shaderlab.live', keyValue: 'on' });
export const LIVE_OFF_WORDS = 'Live runs are off until their safety review clears.';

/** {on, asked, set} for a page with this location and storage (default: the page's own). asked: the address carries
 *  ?live=1; set: the key holds 'on' (read only when asked). Anything unreadable (no location, a storage that throws in a
 *  private window or with blocked site data) is off. */
export function liveSwitch(env = globalThis) {
  let asked = false, set = false;
  try {
    const search = env && env.location ? String(env.location.search || '') : '';
    asked = new URLSearchParams(search).get(LIVE_SWITCH.param) === LIVE_SWITCH.value;
  } catch (e) { asked = false; }
  if (asked) {
    try {
      const s = env.localStorage;
      set = !!s && typeof s.getItem === 'function' && s.getItem(LIVE_SWITCH.key) === LIVE_SWITCH.keyValue;
    } catch (e) { set = false; }
  }
  return Object.freeze({ on: asked && set, asked, set });
}

// The avatar's numbers (agent-avatar.js:809-811), plus the time budget and the one-frame limit.
export const WATCHDOG = Object.freeze({ slowMs: 55, trip: 45, budgetMs: 2500, gapMs: 500 });
export const SCALES = Object.freeze([0.25, 0.5, 0.75, 1]);
export const HEAVY_SCALE = 0.5;
export const MAX_SIDE = 4096;            // a drawing buffer never exceeds this on either side
// The pre-flight: frames 0 and 1 at w x h (the slower counts); refused when that alone takes over refuseMs; the start
// scale keeps the predicted full frame within budgetMs. A second pair at twice each side (w2 x h2: four times the
// pixels) is drawn when even the heaviest growth (the cube) keeps it under the watchdog's one-frame limit, so a cost
// that grows faster than the pixels shows before any larger frame; when it does not, a pair at `mid` (about twice the
// pixels) is drawn instead if that keeps under it. A reading under repsUnderMs is drawn again (up to maxReps, until
// about repsTargetMs in all) and averaged; the timer's resolution (resolutionMs, divided by the draws averaged) is each
// reading's uncertainty. While the two largest readings leave the growth unproven (the least and the most they allow
// differ by more than growthTolerance), larger pairs are drawn in turn (`grow`, four times the pixels each), each only
// when even the heaviest growth keeps it under the ladder's step cap and it is no larger than the frame at the largest
// scale the plan may choose (the class's start).
export const PREFLIGHT = Object.freeze({ w: 64, h: 36, w2: 128, h2: 72, mid: Object.freeze([90, 51]), refuseMs: 200, budgetMs: 30,
  repsUnderMs: 1, repsTargetMs: 2, maxReps: 8, resolutionMs: 0.1,
  grow: Object.freeze([Object.freeze([256, 144]), Object.freeze([512, 288]), Object.freeze([1024, 576])]),
  growthTolerance: 0.1 });
// The heaviest growth the pre-flight takes a cost to have: the cube of its pixels. Growth the readings cannot rule out
// is taken to be there, up to this, the way a cost class not declared is run as the heaviest (C4).
export const HEAVIEST_GROWTH = 3;
// After a hold, Run again draws no more pixels than one scale step below the buffer that tripped; this much allowance
// absorbs the rounding of odd sides (a step is at least 1.27 times the pixels of the next, so it never merges two).
const STEP_SLACK = 1.05;
// The scale menu is a ladder: one step up at a time, and only after this many frames have been measured at the
// current scale; each step is predicted from the slowest of the last `window` frames and refused past stepCapMs.
export const LADDER = Object.freeze({ frames: 6, window: 15, stepCapMs: 150 });
const PARAM_DEBOUNCE_MS = 250;           // a knob drag rebuilds the program at most four times a second

/** A millisecond figure as the stage says it: one decimal at most ("4", "62.5", "716"). */
export const fmtMs = (x) => String(Math.round(Number(x) * 10) / 10);
const r1 = (x) => Math.round(Number(x) * 10) / 10;
const scaleWords = (s) => (s === 1 ? 'full scale' : s === 0.5 ? 'half scale' : s === 0.25 ? 'quarter scale' : `${s} scale`);
const px = (wh) => `${wh[0]} × ${wh[1]}`;

const GL_RGBA = 0x1908, GL_UNSIGNED_BYTE = 0x1401;
const ONE_PIXEL = new Uint8Array(4);
/** Wait until the GPU has done everything queued on gl: gl.finish(), then a one-pixel readPixels from the framebuffer
 *  the runtime leaves bound after a frame (the canvas), which cannot return before that frame is drawn. A finish alone
 *  may return at once on some stacks; the read is the wait every WebGL implementation must honour. Absent either (a
 *  test's fake), whatever is there is used. */
export function drainGl(gl) {
  if (!gl) return;
  if (typeof gl.finish === 'function') gl.finish();
  if (typeof gl.readPixels === 'function') {
    try { gl.readPixels(0, 0, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, ONE_PIXEL); } catch (e) { /* a lost context: nothing is queued */ }
  }
}

/** The scale one step below s (null at the smallest), and one step above (null at the largest). */
export const stepBelow = (s) => { const lower = SCALES.filter((q) => q < s); return lower.length ? lower[lower.length - 1] : null; };
export const stepAbove = (s) => SCALES.find((q) => q > s) ?? null;

/** What frames drawn now say a frame of `pixels` would take: the evidence ({ms: the slowest recent frame gap, px: the
 *  pixels it was drawn at}) grown by the pixel ratio to the pre-flight's growth exponent (1 for a cost that goes with
 *  the pixels). */
export function liveGrowth(live, pixels, exponent = 1) {
  return Number(live.ms) * (Number(pixels) / Number(live.px)) ** Math.max(1, Number(exponent) || 1);
}

// ------------------------------------------------------------------------------------------ the gate --
/** What the Run button says and does for a cost class: {cls, known, heavy, scale, words, label}. */
export function costGate(cls) {
  const c = normCost(cls);
  const measured = 'A pre-flight frame measures it first and may start it lower.';
  if (!c) {
    return { cls: null, known: false, heavy: true, scale: HEAVY_SCALE,
      words: 'not declared, so treated as the heaviest (C4)',
      line: `Cost not declared, so it is treated as the heaviest (C4). It starts at half scale at most: a quarter of the pixels. ${measured}`,
      label: 'Run live on this GPU · cost unknown · half scale' };
  }
  const heavy = c === 'C3' || c === 'C4';
  return { cls: c, known: true, heavy, scale: heavy ? HEAVY_SCALE : 1, words: COSTS[c].words,
    line: `${c}, ${COSTS[c].words}. ${heavy ? 'It starts at half scale at most: a quarter of the pixels.' : 'It starts at full scale at most.'} ${measured}`,
    label: `Run live on this GPU · ${c} · ${heavy ? 'half scale' : 'full scale'}` };
}

/** The five cost classes as a small scale with the subject's class lit (an unknown one lights C4, marked assumed). */
export function costScale(doc, gate) {
  const box = h(doc, 'div', 'wb-cost-scale', null, { role: 'img',
    'aria-label': gate.known ? `Cost class ${gate.cls} of C0 to C4` : 'Cost class not declared; treated as C4' });
  for (const c of Object.keys(COSTS)) {
    const lit = gate.known ? c === gate.cls : c === 'C4';
    const seg = h(doc, 'span', `wb-cost-seg is-${c.toLowerCase()}${lit ? ' is-current' : ''}${lit && !gate.known ? ' is-assumed' : ''}`,
      c, { title: `${c}: ${COSTS[c].words}` });
    box.appendChild(seg);
  }
  return box;
}

/** 'C4' when a saved shader owns render targets (a buffer or a cubemap pass), else null: a floor under any claim. */
export function costFloorFromShader(json) {
  const rp = json && (json.renderpass || (json.Shader && json.Shader.renderpass));
  if (!Array.isArray(rp)) return null;
  return rp.some((p) => /^(buffer|cubemap)$/i.test(String(p && p.type))) ? 'C4' : null;
}

// How heavy a gate is for raising: an unknown class is run as C4, so it ranks with C4.
const gateRank = (g) => (g.known ? costRank(g.cls) : COSTS.C4.rank);

/** The house watchdog: tick(now) once per animation frame while the page is visible. A frame more than `slowMs` after
 *  the previous one is slow; it trips on `trip` slow frames in a row (light stutter), on slow frames in a row adding up
 *  past `budgetMs`, or at once on one frame more than `gapMs` after the last. An on-time frame resets the streak and its
 *  sum; reset() starts a fresh window. `reason` says which rule tripped: 'count', 'budget' or 'gap'. */
export function createWatchdog({ slowMs = WATCHDOG.slowMs, trip = WATCHDOG.trip, budgetMs = WATCHDOG.budgetMs,
  gapMs = WATCHDOG.gapMs } = {}) {
  let last = null, streak = 0, streakMs = 0, tripped = false, worst = 0, reason = null, lastGap = 0;
  return {
    tick(now) {
      if (tripped) return { slow: false, streak, tripped, gap: 0, reason };
      let gap = 0, slow = false;
      if (last !== null) {
        gap = now - last;
        lastGap = gap;
        slow = gap > slowMs;
        if (slow) { streak += 1; streakMs += gap; worst = Math.max(worst, gap); } else { streak = 0; streakMs = 0; }
        if (gap > gapMs) { tripped = true; reason = 'gap'; }
        else if (streak >= trip) { tripped = true; reason = 'count'; }
        else if (streakMs > budgetMs) { tripped = true; reason = 'budget'; }
      }
      last = now;
      return { slow, streak, tripped, gap, reason };
    },
    reset() { last = null; streak = 0; streakMs = 0; tripped = false; worst = 0; reason = null; lastGap = 0; },
    get tripped() { return tripped; },
    get streak() { return streak; },
    get streakMs() { return streakMs; },
    get worst() { return worst; },
    get gap() { return lastGap; },
    get reason() { return reason; },
  };
}

/** What every frame pays whatever its size (the read-back's round trip, the submission), as bounds {lo, hi, setAside},
 *  from its reading (`overhead`, {ms, err}: the one-pixel draw timed, uncertain by err) and the frames' readings
 *  ([{ms, err}]). Every frame pays it, so it is never more than the smallest frame at its most (hi). A hiccup in the
 *  timing (a GC pause, the scheduler) only ever adds time, so a reading whose least is above that is the hiccup, not the
 *  cost: it is set aside, and the part every frame pays is then known only to lie between nothing and that frame. Null
 *  when nothing was read. */
export function perFrameBounds(overhead, frames = []) {
  if (!overhead) return null;
  if (Number.isFinite(Number(overhead.lo)) && Number.isFinite(Number(overhead.hi))) {
    const lo = Math.max(0, Number(overhead.lo));
    return { lo, hi: Math.max(lo, Number(overhead.hi)), setAside: !!overhead.setAside };
  }
  const om = Math.max(0, Number(overhead.ms) || 0), eo = Math.max(0, Number(overhead.err) || 0);
  const caps = (Array.isArray(frames) ? frames : []).filter((q) => q && Number.isFinite(Number(q.ms)))
    .map((q) => Math.max(0, Number(q.ms)) + Math.max(0, Number(q.err) || 0));
  const cap = caps.length ? Math.min(...caps) : Infinity;
  const lo = Math.max(0, om - eo);
  if (lo > cap) return { lo: 0, hi: cap, setAside: true };
  return { lo, hi: Math.min(om + eo, cap), setAside: false };
}

/** The most a frame of `px` pixels can take, from a reading r ({ms, px, err}) whose pixels' work grows as the pixels to
 *  the power `exponent` at most, behind a per-frame part within `perFrame` ({lo, hi}, perFrameBounds; null: none taken
 *  off): that part at its most, plus the reading's work at its most (the reading at its most, less the part at its
 *  LEAST), grown to `px`. For a cost that is that part plus a power of the pixels no steeper than `exponent`, it is
 *  never below the frame while the readings are within their uncertainty. */
export function frameAtMost(r, px, exponent, perFrame = null) {
  const lo = perFrame ? perFrame.lo : 0, hi = perFrame ? perFrame.hi : 0;
  const work = Math.max(0, (Number(r.ms) || 0) + Math.max(0, Number(r.err) || 0) - lo);
  return hi + work * (Number(px) / Number(r.px)) ** exponent;
}

/** How the pixels' own cost grows from reading a to a larger reading b ({ms, px, err}: a frame's time, its pixels, and
 *  its uncertainty, the timer's resolution over the draws it averaged), as an exponent of the pixels (1: it goes with
 *  the pixels, 2: with their square): {low, high, proven}. A frame's time is a cost every frame pays whatever its size
 *  (`overhead`: the read-back's round trip and the submission, measured by a draw that shades one pixel, as {ms, err}
 *  or as perFrameBounds' {lo, hi}) plus its pixels' work, and only the work grows. low and high are the least and the
 *  most growth the readings allow with each, the overhead included, anywhere within its bounds, clamped to
 *  [1, HEAVIEST_GROWTH]. When the smaller reading's work is within its uncertainty of nothing, nothing bounds the growth
 *  from above and high is the heaviest. proven: low and high are within PREFLIGHT.growthTolerance of each other. */
export function growthBounds(a, b, overhead = null) {
  const r = Number(b && b.px) / Number(a && a.px);
  if (!(r > 1)) return { low: 1, high: HEAVIEST_GROWTH, proven: false };
  const am = Number(a.ms) || 0, bm = Number(b.ms) || 0;
  const ea = Math.max(0, Number(a.err) || 0), eb = Math.max(0, Number(b.err) || 0);
  // The most growth: the larger reading at its most over the smaller at its least, with the most overhead taken from
  // both (taking more from both makes the ratio steeper); the least: the other way round. The overhead is never more
  // than either reading (perFrameBounds), and a reading of it above them is set aside.
  const ob = perFrameBounds(overhead, [a, b]);
  const oHi = ob ? ob.hi : 0, oLo = ob ? ob.lo : 0;
  const clamp = (x) => Math.min(HEAVIEST_GROWTH, Math.max(1, x));
  const hiTop = bm + eb - oHi, hiBottom = am - ea - oHi;
  const high = hiBottom > 0 && hiTop > 0 ? clamp(Math.log(hiTop / hiBottom) / Math.log(r)) : HEAVIEST_GROWTH;
  const loTop = bm - eb - oLo, loBottom = am + ea - oLo;
  const low = loTop > 0 && loBottom > 0 ? clamp(Math.log(loTop / loBottom) / Math.log(r)) : 1;
  return { low, high, proven: high - low <= PREFLIGHT.growthTolerance };
}
// An upper bound kept an upper bound when it is shown to two decimals.
const up2 = (x) => Math.ceil(Number(x) * 100 - 1e-6) / 100;

/** The pre-flight's verdict from its readings. tinyMs: what the tiny frame took (the slower of frames 0 and 1, the
 *  read-back wait included); tinyPx, fullPx: its pixels and the full frame's at scale 1; classScale: the largest scale
 *  it may choose (the class's start, or the scale a run was at), which the pre-flight may lower, never raise. Larger
 *  readings: secondMs at secondPx (four times the tiny frame's pixels), then `readings` ([{ms, px, resolutionMs}], the
 *  larger frames the pre-flight drew beyond it). Each reading is uncertain by its timer resolution over the draws it
 *  averaged (resolutionMs for the tiny one; secondResolutionMs, by default the same, for the second). overheadMs, when
 *  measured (a draw that shades one pixel, uncertain by overheadResolutionMs), is what every frame pays whatever its
 *  size; it does not grow with the pixels. It is never taken to be more than the smallest reading, and a reading of it
 *  above that is a hiccup, set aside (perFrameBounds; overheadSetAside says so): the part is then anywhere from nothing
 *  to that reading.
 *
 *  The growth is the MOST the pixels' work in the two largest readings allows (growthBounds' high): growth they cannot
 *  rule out is taken to be there, and one reading alone, which shows none, is taken at the heaviest (pixels cubed), the
 *  way a cost class not declared runs as C4. Each scale's prediction is the overhead at its most plus the largest
 *  reading's work at its most (that reading at its most, less the overhead at its least: frameAtMost) grown to the
 *  scale's pixels at that exponent, and never below any reading times its pixel ratio (the spec's linear prediction
 *  from the tiny frame): for a cost that is a fixed overhead plus any power of its pixels up to the cube, no prediction
 *  is below the frame while the readings are within their uncertainty. With live evidence ({ms, px}: the slowest recent frame gap
 *  and the pixels it was drawn at), each scale's prediction is the larger of the pre-flight's and that evidence grown
 *  to its pixels. pxByScale gives each scale's real pixel count (else fullPx times the scale squared). Returns {ok,
 *  scale, predictedMs, predictedFullMs, perScale: [{scale, px, ms, pf, live}], overBudget, refused, exponent, growth:
 *  {low, high, proven, readings}, overheadMs, ...}; refused (a sentence) when the tiny frame alone is over refuseMs, or
 *  when even the smallest scale would take past limitMs. */
export function preflightPlan({ tinyMs, tinyPx, fullPx, classScale = 1, secondMs = null, secondPx = null, readings = null,
  overheadMs = null, overheadResolutionMs = null,
  scales = SCALES, budgetMs = PREFLIGHT.budgetMs, refuseMs = PREFLIGHT.refuseMs, limitMs = WATCHDOG.gapMs,
  resolutionMs = PREFLIGHT.resolutionMs, secondResolutionMs = null, live = null, pxByScale = null } = {}) {
  const ms = Math.max(0, Number(tinyMs) || 0);
  const tPx = Math.max(1, Number(tinyPx) || 1);
  const fPx = Math.max(1, Number(fullPx) || 1);
  const ratio = fPx / tPx;
  const errOf = (x, otherwise) => (x === null || x === undefined ? otherwise : Math.max(0, Number(x) || 0));
  const err1 = errOf(resolutionMs, 0);
  // The readings, smallest first, each with its uncertainty. One no larger than the reading before it is left out.
  const pts = [{ ms, px: tPx, err: err1 }];
  const add = (m, p, err) => {
    if (m === null || m === undefined || !(Number(m) >= 0) || !(Number(p) > pts[pts.length - 1].px)) return;
    pts.push({ ms: Number(m), px: Number(p), err });
  };
  add(secondMs, secondPx, errOf(secondResolutionMs, err1));
  for (const q of Array.isArray(readings) ? readings : []) if (q) add(q.ms, q.px, errOf(q.resolutionMs, err1));
  const top = pts[pts.length - 1];
  // What every frame pays whatever its size, when it was measured ({ms, err}); not measured, nothing is taken off. It is
  // part of every frame, so it is never more than the smallest of them; a reading above that is a hiccup in the timing,
  // set aside (perFrameBounds): a 10 ms reading beside a 0.34 ms tiny frame zeroed the work of a cube-law cost and
  // predicted 129 ms for a 25 s frame.
  const over = overheadMs === null || overheadMs === undefined || !(Number(overheadMs) >= 0) ? null
    : { ms: Number(overheadMs), err: errOf(overheadResolutionMs, err1) };
  const perFrame = perFrameBounds(over, pts);
  // Within the timer's resolution two readings allow anything up to the cube: 0.005 and 0.08 ms averaged over 8 draws
  // each are taken at 3 (as their least, linear, they predicted 7.7 ms for a 750 ms frame). Far above it, the most they
  // allow is close to the truth: 0.5 and 8 ms averaged over 4 draws and read once give 2.05 for a true 2. A fixed cost
  // per frame is taken off first: behind 0.1 ms of it, a square-law cost of 0.03 ms at 64 x 36 reads 0.13 and 0.58 ms,
  // which as totals allow no more than 1.19 (a 300 ms frame predicted at 27 ms); as the pixels' work they allow the cube.
  const g = pts.length > 1 ? growthBounds(pts[pts.length - 2], top, perFrame) : { low: 1, high: HEAVIEST_GROWTH, proven: false };
  const exponent = g.high;
  // The per-frame part at its most, plus the largest reading's work at its most (that reading at its most, less the
  // part at its LEAST) grown at that exponent (frameAtMost); never below any reading times its pixel ratio. Taking the
  // part at its most off the work too predicted 25.2 ms for a 25.41 ms frame.
  const model = (p) => Math.max(frameAtMost(top, p, exponent, perFrame), ...pts.map((q) => q.ms * (p / q.px)));
  const ev = live && Number(live.ms) > 0 && Number(live.px) > 0 ? { ms: Number(live.ms), px: Number(live.px) } : null;
  const predict = (p) => Math.max(model(p), ev ? liveGrowth(ev, p, exponent) : 0);
  const pxAt = (s, i) => (Array.isArray(pxByScale) && Number(pxByScale[i]) > 0 ? Number(pxByScale[i]) : fPx * s * s);
  const perScale = scales.map((s, i) => {
    const p = pxAt(s, i);
    return { scale: s, px: Math.round(p), ms: r1(predict(p)), pf: r1(model(p)), live: ev ? r1(liveGrowth(ev, p, exponent)) : null };
  });
  const base = { tinyMs: r1(ms), ratio: r1(ratio), predictedFullMs: r1(predict(fPx)), perScale, budgetMs, refuseMs, limitMs,
    exponent: up2(exponent), growth: { low: Math.round(g.low * 100) / 100, high: up2(g.high), proven: g.proven, readings: pts.length },
    overheadMs: over ? Math.round(over.ms * 100) / 100 : null, overheadSetAside: !!(perFrame && perFrame.setAside),
    live: ev ? { ms: r1(ev.ms), px: ev.px } : null };
  if (ms > refuseMs) {
    return { ...base, ok: false, scale: null, predictedMs: null, overBudget: true,
      refused: `the tiny pre-flight frame alone took ${fmtMs(ms)} ms (the limit is ${refuseMs} ms)` };
  }
  const allowed = perScale.filter((p) => p.scale <= classScale + 1e-9);
  const pool = allowed.length ? allowed : perScale.slice(0, 1);
  const fits = pool.filter((p) => p.ms <= budgetMs);
  if (fits.length) {
    const pick = fits[fits.length - 1];
    return { ...base, ok: true, scale: pick.scale, predictedMs: pick.ms, overBudget: false, refused: null };
  }
  const smallest = pool[0];
  if (smallest.ms > limitMs) {
    // Say when the growth behind the number is one the readings could not prove.
    const steep = g.proven ? '' : pts.length < 2
      ? ', taking the heaviest growth (pixels cubed): one reading cannot show how its cost grows'
      : `, taking the steepest growth its readings allow (pixels to the power ${up2(exponent)})`;
    return { ...base, ok: false, scale: null, predictedMs: smallest.ms, overBudget: true,
      refused: `even at ${smallest.scale} × a frame would take about ${fmtMs(smallest.ms)} ms, past the watchdog's ${limitMs} ms one-frame limit${steep}` };
  }
  return { ...base, ok: true, scale: smallest.scale, predictedMs: smallest.ms, overBudget: true, refused: null };
}

// ------------------------------------------------------------------------------------- cards and params --
/** A test card (arsenal/web/glsl/cards/<module>.card): its leading //! lines are one JSON header
 *  ({card, uses, t, size, note}), the rest a Shadertoy mainImage body. Throws when there is no header. */
export function parseCard(text) {
  const lines = String(text || '').replace(/\r\n?/g, '\n').split('\n');
  let n = 0;
  while (n < lines.length && /^[ \t]*\/\/!/.test(lines[n])) n++;
  if (!n) throw new Error('a card starts with a //! JSON header');
  let header;
  try { header = JSON.parse(lines.slice(0, n).map((l) => l.replace(/^[ \t]*\/\/!/, '')).join(' ')); } catch (e) {
    throw new Error(`the card's //! header is not JSON (${e.message})`);
  }
  if (!header || typeof header !== 'object' || Array.isArray(header)) throw new Error("the card's //! header is not an object");
  return { header, body: lines.slice(n).join('\n') };
}

/** The Shadertoy-shaped document a card runs as: Common = the composed library text, Image = the card's body. */
export function cardShader(name, common, body) {
  return {
    info: { id: `card-${name}`, name: `${name} card`, username: 'house', description: 'a house module test card (Apache-2.0)' },
    renderpass: [
      { name: 'Common', type: 'common', code: String(common || ''), inputs: [], outputs: [] },
      { name: 'Image', type: 'image', code: String(body || ''), inputs: [], outputs: [{ id: '4dfGRr', channel: 0 }] },
    ],
  };
}

const lit = (x) => { const n = Number(x); if (!Number.isFinite(n)) return '0.0'; const s = String(n); return /[.eE]/.test(s) ? s : `${s}.0`; };
const VEC_N = { vec2: 2, vec3: 3, vec4: 4 };
/** The GLSL type a descriptor's value takes when nothing declares it: toggle bool, choice int (the index), a list a
 *  vector of its length, anything else float. */
function naturalType(d, v) {
  if (d.type === 'toggle') return 'bool';
  if (d.type === 'choice') return 'int';
  if (Array.isArray(v)) return v.length === 2 ? 'vec2' : v.length === 4 ? 'vec4' : 'vec3';
  return 'float';
}
/** v written as a literal of GLSL type `type` (a declared uniform's own type wins over the descriptor's). */
function literalAs(type, d, v) {
  if (type === 'bool') return v ? 'true' : 'false';
  if (type === 'int') {
    const i = d.type === 'choice' ? (d.values || []).findIndex((o) => o.value === v) : Math.round(Number(v));
    return String(Number.isFinite(i) && i >= 0 ? i : 0);
  }
  if (VEC_N[type]) {
    const xs = Array.isArray(v) ? v : [v];
    const n = VEC_N[type];
    return `${type}(${Array.from({ length: n }, (_, k) => lit(xs[Math.min(k, xs.length - 1)] ?? 0)).join(', ')})`;
  }
  return lit(Array.isArray(v) ? v[0] : v);
}
const esc = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Bind a recipe's params into a card as constants. The runtime binds Shadertoy's uniforms only, so a param uniform
 *  (u_<name>) reaches the card in one of three ways: the text declares it as a uniform (`uniform float u_gain;` becomes
 *  `const float u_gain = 1.5;`); the card declares it as a const holding its default (`const float u_gain = 1.0;`, the
 *  convention that also renders through `py -m arsenal shader card`, which binds no uniforms; the knob's value replaces
 *  the default); or the text only reads it (a const is declared once, at the top). A param none of these reaches is
 *  reported unread: its knob does not reach this card, and the Inspector says so instead of a knob that does nothing. */
export function bindParams(common, body, descriptors, values = {}) {
  let c = String(common || ''), b = String(body || '');
  const head = [], bound = [], unread = [];
  for (const d of descriptors || []) {
    if (!d || d.derived || !d.uniform) continue;
    const v = Object.prototype.hasOwnProperty.call(values, d.id) ? values[d.id] : d.default;
    const decl = new RegExp(`^([ \\t]*)uniform[ \\t]+(?:(?:highp|mediump|lowp)[ \\t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \\t]+${esc(d.uniform)}[ \\t]*;`, 'm');
    const use = new RegExp(`\\b${esc(d.uniform)}\\b`);
    let hit = false;
    const declare = (text) => text.replace(decl, (_, indent, type) => `${indent}const ${type} ${d.uniform} = ${literalAs(type, d, v)};`);
    if (decl.test(c)) { c = declare(c); hit = true; }
    if (decl.test(b)) { b = declare(b); hit = true; }
    // The card convention: `const float u_gain = 1.0;` holds the default the CLI renders; the knob's value replaces it.
    const constDecl = new RegExp(`^([ \\t]*)const[ \\t]+(?:(?:highp|mediump|lowp)[ \\t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \\t]+${esc(d.uniform)}[ \\t]*=[^;\\n]*;`, 'm');
    const reassign = (text) => text.replace(constDecl, (_, indent, type) => `${indent}const ${type} ${d.uniform} = ${literalAs(type, d, v)};`);
    if (!hit && constDecl.test(c)) { c = reassign(c); hit = true; }
    if (!hit && constDecl.test(b)) { b = reassign(b); hit = true; }
    if (!hit && (use.test(c) || use.test(b))) {
      const type = naturalType(d, v);
      head.push(`const ${type} ${d.uniform} = ${literalAs(type, d, v)};`);
      hit = true;
    }
    (hit ? bound : unread).push(d.id);
  }
  if (head.length) c = `// params bound by the Workbench\n${head.join('\n')}\n${c}`;
  return { common: c, body: b, bound, unread };
}


// --------------------------------------------------------------------------------------------- the panel --
function nowFn() { return (globalThis.performance && performance.now) ? performance.now() : Date.now(); }

export function mountStage(doc, root, opts = {}) {
  // The one switch (liveSwitch), read once, here. Off, the two places that could start the live path refuse first:
  // loadLive() (the runtime) and build() (a canvas and its WebGL context); every way in returns before reaching them.
  const sw = liveSwitch(opts.env === undefined ? globalThis : opts.env);
  const live = sw.on === true;
  function mustBeLive(what) {
    if (!live) throw new Error(`${what} refused: ${LIVE_OFF_WORDS}`);
  }
  const loadRuntime = opts.loadRuntime || (() => Promise.reject(new Error('no runtime loader was given to the stage')));
  async function loadLive() {
    mustBeLive('loading the shader runtime');
    return loadRuntime();
  }
  const raf = opts.raf || ((fn) => globalThis.requestAnimationFrame(fn));
  const caf = opts.caf || ((id) => globalThis.cancelAnimationFrame(id));
  const now = opts.now || nowFn;
  const dpr = opts.dpr || (() => globalThis.devicePixelRatio || 1);
  const isHidden = opts.isHidden || (() => !!(globalThis.document && globalThis.document.visibilityState === 'hidden'));
  // A host that can hide the Stage (the Workbench's Shelf tab) says so: a reason (a phrase) while it is hidden, else null.
  const isAway = typeof opts.isAway === 'function' ? opts.isAway : () => null;
  const onReceipt = typeof opts.onReceipt === 'function' ? opts.onReceipt : () => {};
  const onTake = typeof opts.onTake === 'function' ? opts.onTake : () => {};
  const setTimer = opts.setTimeout || ((fn, ms) => setTimeout(fn, ms));
  const clearTimer = opts.clearTimeout || ((t) => clearTimeout(t));
  // onResize(fn) -> unsubscribe: who tells the stage it may have changed size. By default the window's resize, the
  // box's ResizeObserver and a matchMedia query on the pixel ratio; the loop checks before every frame regardless.
  const watchSize = typeof opts.onResize === 'function' ? opts.onResize : null;

  const { side, body } = panel(doc, root, 'wb-stage', 'Stage', '');
  const box = h(doc, 'div', 'wb-stage-box');
  const caption = h(doc, 'div', 'wb-stage-caption');
  const costRow = h(doc, 'div', 'wb-cost-row');
  const run = h(doc, 'button', 'wb-btn wb-primary wb-run', 'Run live on this GPU', { type: 'button' });
  const stopBtn = h(doc, 'button', 'wb-btn wb-quiet wb-stop', 'Stop', { type: 'button', disabled: true });
  const takeBtn = h(doc, 'button', 'wb-btn wb-quiet wb-take', 'Take a still', { type: 'button', disabled: true,
    title: 'Keep this frame in the Strip, with the receipt of what ran' });
  const scaleSel = h(doc, 'select', 'wb-scale', null, { 'aria-label': 'Render scale', disabled: true,
    title: 'Fraction of the stage size the shader draws at (each side). Half scale is a quarter of the pixels.' });
  const scaleOpts = new Map();
  for (const s of SCALES) {
    const o = h(doc, 'option', null, `${s === 1 ? '1' : s} ×`, { value: String(s) });
    scaleOpts.set(s, o);
    scaleSel.appendChild(o);
  }
  const scaleLabel = put(h(doc, 'label', 'wb-scale-label'), h(doc, 'span', null, 'Scale'), scaleSel);
  const status = h(doc, 'p', 'wb-stage-status', null, { role: 'status', 'aria-live': 'polite' });
  // View only, the filmstrip's button stands where Run would; the live controls are not put in the page at all.
  const filmBtn = h(doc, 'button', 'wb-btn wb-film-play', 'Play the filmstrip', { type: 'button', hidden: true,
    'aria-pressed': 'false', title: 'The frames rendered on SwiftShader, one after another: a picture, no work for this GPU' });
  const controls = live ? put(h(doc, 'div', 'wb-stage-controls'), run, scaleLabel, stopBtn, takeBtn)
    : put(h(doc, 'div', 'wb-stage-controls'), filmBtn);
  const bar = put(h(doc, 'div', 'wb-stage-bar'), costRow, controls, status);
  body.replaceChildren(box, caption, bar);

  const st = {
    subject: null, gate: costGate(null), raised: null, toy: null, canvas: null, running: false, tripped: false,
    halted: null,        // why a toy on stage is not drawing: 'stopped' | 'tripped' | 'hidden' | 'away' | 'error' | 'refused'
    scale: 1,            // the scale asked for: the one drawn at while running; Run again's while stopped
    t0: 0, haltedAt: null, pausedTotal: 0, rafId: null, token: 0, receipt: null, frames: 0,
    params: null, paramTimer: null, paramSeq: 0, paramsPending: false, busy: false,
    preflight: null, refused: null, trip: null, loaded: null,
    gaps: [],            // frame gaps measured at the locked size (the ladder's evidence)
    basis: null,         // {w, h, dpr}: the stage box and the pixel ratio the last pre-flight measured
    locked: null,        // [w, h]: the drawing buffer that pre-flight measured; the canvas never leaves it while drawing
    lockedScale: null,   // the scale `locked` was taken at
    measures: 0,         // pre-flights of the program on stage (the first, then one per size change)
    worstGap: 0,         // the slowest frame gap since Run (for the receipt and the screenshot driver)
    inFlight: false,     // a live frame was drawn that no watchdog tick has judged yet
    pausedBy: null,      // the knob rebuild (its number) that holds the loop while it compiles and measures
    leaving: false,      // the subject is being replaced: its last frame is judged, but its receipt is not sent
  };
  const watchdog = createWatchdog();
  // Refusals last for the page: a subject refused once is not run again when it is picked again (kind:id -> words).
  const refusals = new Map();
  const subjectKey = (s) => (s ? `${s.kind || ''}:${s.id || s.title || ''}` : null);
  function markRefused(words) {
    st.refused = words;
    const k = subjectKey(st.subject);
    if (k) refusals.set(k, words);
  }

  function say(text, tone) {
    status.textContent = text;
    status.dataset.tone = tone || 'info';
    // A warning (a hold, a refusal, a run over budget) must be read: bring it into view if the panel has scrolled it off.
    if (tone === 'warn' && typeof status.scrollIntoView === 'function') status.scrollIntoView({ block: 'nearest' });
  }
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  // The button always names the class and the scale: before the first run, while running (disabled), and after any stop.
  const runLabel = (mode) => `${mode === 'running' ? 'Running' : mode ? 'Run again' : 'Run live'} on this GPU · `
    + `${st.gate.known ? st.gate.cls : 'cost unknown'} · ${scaleWords(st.scale)}`;
  // The cost line before anything runs: with the switch on it names the start Run would use; view only, the class.
  const gateLine = () => (live ? st.gate.line : st.gate.known ? `${st.gate.cls}, ${COSTS[st.gate.cls].words}.`
    : 'Cost not declared: a live run would treat it as the heaviest (C4).');

  // ---- view only: the filmstrip, played on the Stage ----
  // The contact sheet `py -m arsenal shader filmstrip` draws, stepped through a window the size of the Stage (the
  // Shelf's flipbook, shelf.js): one picture rendered on SwiftShader, a background-position change per step, and no
  // work for this GPU. It plays when its button is pressed, never by itself.
  let poster = { sprite: null, badge: null, badgeText: '' };
  let film = null;   // {sprite, timer, i, n}: the filmstrip playing
  const filmLabel = () => `Play the filmstrip · ${Number((st.subject && st.subject.film && st.subject.film.frames) || 0)} frames`;
  function stopFilm() {
    if (!film) return;
    if (film.timer !== null) clearTimer(film.timer);
    setClass(film.sprite, 'is-playing', false);
    if (poster.badge) { poster.badge.textContent = poster.badgeText; setClass(poster.badge, 'is-film', false); }
    film = null;
    filmBtn.textContent = filmLabel();
    filmBtn.setAttribute('aria-pressed', 'false');
  }
  function playFilm() {
    const f = st.subject && st.subject.film;
    if (live || !f || !poster.sprite) return;
    stopFilm();
    const sprite = poster.sprite;
    const n = Math.max(2, Math.floor(Number(f.frames) || 0));
    // The sheet's own spacing (to / (frames - 1) seconds) is real time; sparse frames are held long enough to read.
    const spacing = Number(f.to) > 0 ? (Number(f.to) / (n - 1)) * 1000 : 250;
    const dt = Math.max(80, Math.min(400, spacing));
    sprite.style.backgroundImage = `url("${f.sheet}")`;
    film = { sprite, timer: null, i: 0, n };
    setClass(sprite, 'is-playing', true);
    // Each cell of the sheet carries its own t = label in its lower-left corner: the badge moves aside while it plays.
    if (poster.badge) setClass(poster.badge, 'is-film', true);
    filmBtn.textContent = 'Pause the filmstrip';
    filmBtn.setAttribute('aria-pressed', 'true');
    const step = () => {
      if (!film || film.sprite !== sprite) return;
      // Sized from the Stage as it is at each step, so a resized window keeps the frame filling the box (both 16:9).
      const r = typeof box.getBoundingClientRect === 'function' ? box.getBoundingClientRect() : null;
      const g = sheetFrame(film.i, n);
      const k = (r && r.width > 0 ? r.width : FILM.cell[0]) / g.cw;
      sprite.style.backgroundSize = `${Math.round(g.w * k)}px ${Math.round(g.h * k)}px`;
      sprite.style.backgroundPosition = `${-Math.round(g.x * k)}px ${-Math.round(g.y * k)}px`;
      if (poster.badge) poster.badge.textContent = `filmstrip · frame ${film.i + 1} of ${n} · SwiftShader`;
      film.i = (film.i + 1) % n;
      film.timer = setTimer(step, dt);
    };
    step();
  }
  const viewOnlyWords = () => `${LIVE_OFF_WORDS} What you see was rendered on SwiftShader (the CPU) under the house GPU `
    + `lock${poster.sprite ? '; play the filmstrip to see it move.' : '.'}`;

  function showEmpty() {
    stopFilm();
    box.replaceChildren(put(h(doc, 'div', 'wb-stage-empty'), h(doc, 'p', 'wb-stage-empty-title', 'Nothing on stage yet'),
      h(doc, 'p', null, 'Pick a module card in the Library, or put a loved shader on stage from the Shelf.')));
    poster = { sprite: null, badge: null, badgeText: '' };
    caption.replaceChildren();
    costRow.replaceChildren();
    side.textContent = '';
    run.hidden = true;
    scaleLabel.hidden = true; stopBtn.hidden = true; takeBtn.hidden = true; filmBtn.hidden = true;
    say(live ? 'Safe by default: pictures here are pre-rendered on SwiftShader, and nothing runs on this GPU until you press Run.'
      : `${LIVE_OFF_WORDS} Every picture here is pre-rendered on SwiftShader (the CPU), under the house GPU lock.`);
  }

  function showPoster(s) {
    stopFilm();
    const urls = s.poster || [];
    const still = h(doc, 'div', 'wb-stage-still');
    if (urls.length) {
      still.appendChild(imgFrom(doc, urls, { alt: `${s.title}: a still rendered on SwiftShader`, cls: 'wb-stage-img', lazy: false,
        onNone: (img) => { img.remove(); still.appendChild(put(h(doc, 'div', 'wb-stage-empty'),
          h(doc, 'p', 'wb-stage-empty-title', 'No still rendered yet'), h(doc, 'p', null, s.posterHint || 'Render one with the shader verbs; or run it live.'))); } }));
    } else {
      still.appendChild(put(h(doc, 'div', 'wb-stage-empty'), h(doc, 'p', 'wb-stage-empty-title', s.blocked ? s.blocked.title : 'No still'),
        h(doc, 'p', null, s.blocked ? s.blocked.why : (s.posterHint || 'No pre-rendered picture for this subject yet.'))));
    }
    // View only, the filmstrip plays over the still in a layer of its own (shown only while playing).
    const f = s.film;
    const sprite = !live && !s.blocked && f && f.sheet && Number(f.frames) > 1
      ? h(doc, 'div', 'wb-stage-film', null, { 'aria-hidden': 'true' }) : null;
    if (sprite) still.appendChild(sprite);
    const subs = Array.isArray(s.standIns) ? s.standIns : [];
    const badge = h(doc, 'span', `wb-badge${subs.length ? ' has-standins' : ''}`,
      subs.length ? 'still · SwiftShader · stand-in inputs' : 'still · SwiftShader',
      subs.length ? { title: `Rendered with stand-ins for inputs the corpus lacks:\n${standInLines(subs).join('\n')}` } : null);
    still.appendChild(badge);
    poster = { sprite, badge, badgeText: badge.textContent };
    box.replaceChildren(still);
  }

  // ---- sizing: the drawing buffer is the box times the pixel ratio times the scale, measured and then locked ----
  function boxSize() {
    const r = typeof box.getBoundingClientRect === 'function' ? box.getBoundingClientRect() : null;
    const w = r && r.width > 0 ? r.width : 640;
    return [w, r && r.height > 0 ? r.height : Math.round(w * 9 / 16)];
  }
  /** The stage box and the device pixel ratio as they are now. */
  function basisNow() { const [w, hh] = boxSize(); return { w, h: hh, dpr: Number(dpr()) || 1 }; }
  /** The drawing buffer [w, h] at a scale over a basis: the box times the pixel ratio times the scale, capped. */
  function sizeAt(scale, b) {
    const k = Math.max(0.05, b.dpr * scale);
    let w = Math.max(1, Math.round(b.w * k)), hh = Math.max(1, Math.round(b.h * k));
    const over = Math.max(w, hh) / MAX_SIDE;
    if (over > 1) { w = Math.max(1, Math.floor(w / over)); hh = Math.max(1, Math.floor(hh / over)); }
    return [w, hh];
  }
  const area = (wh) => (wh ? wh[0] * wh[1] : 0);
  /** True when the next frame would be drawn at a size the last pre-flight did not measure: the box, the pixel ratio
   *  or the scale moved. */
  function sizeMoved() {
    if (!st.locked) return true;
    const t = sizeAt(st.scale, basisNow());
    return t[0] !== st.locked[0] || t[1] !== st.locked[1];
  }
  /** Draw at `scale` over basis `b` from now on: the size a pre-flight just measured, locked. */
  function lockAt(scale, b) {
    st.scale = scale;
    st.basis = b;
    st.locked = sizeAt(scale, b);
    st.lockedScale = scale;
    scaleSel.value = String(scale);
    st.toy.resize(st.locked[0], st.locked[1]);
  }
  /** Where Run again may draw after a hold: the largest scale whose drawing buffer, over the box and pixel ratio as
   *  they are now, has no more pixels than one scale step below the buffer that tripped (its pixels times the square of
   *  the step's ratio, with STEP_SLACK for odd sides). Null when no scale is that small: the hold was at the smallest
   *  scale, or the window moved to a higher pixel ratio while held (0.25 x on a 2x display is the 0.5 x that held). */
  function stepDown(trip, b = basisNow()) {
    if (!trip || !trip.size) return null;
    const below = stepBelow(trip.scale);
    if (below === null) return null;
    const most = area(trip.size) * (below / trip.scale) ** 2 * STEP_SLACK;
    const fits = SCALES.filter((s) => area(sizeAt(s, b)) <= most);
    return fits.length ? fits[fits.length - 1] : null;
  }

  // ---- the ladder ----
  /** The frames measured at the locked size, as evidence: the SLOWEST recent gap (a spike every few frames is what the
   *  next step meets), with the pixels they were drawn at and how many; null while fewer than LADDER.frames have been
   *  measured, unless `any` (a hold, a size change: whatever was measured counts). */
  function liveEvidence(any = st.tripped) {
    const g = st.gaps.slice(-LADDER.window);
    if (!st.locked || !g.length || (g.length < LADDER.frames && !any)) return null;
    return { ms: Math.max(...g), px: area(st.locked), n: g.length };
  }
  const exponentNow = () => (st.preflight && Number(st.preflight.exponent)) || 1;
  /** A step to scale s as the frames drawn now predict it, at the pixel count it would really have (the box and the
   *  ratio as they are now); null when too few frames have been measured. */
  function stepPredict(s) {
    const live = liveEvidence();
    if (!live) return null;
    const pixels = area(sizeAt(s, basisNow()));
    return { ms: r1(liveGrowth(live, pixels, exponentNow())), liveMs: r1(live.ms), n: live.n, px: pixels };
  }
  // The scale the ladder climbs from: the one last measured (while stopped, the scale asked for may differ from it).
  const ladderBase = () => (st.lockedScale !== null ? st.lockedScale : st.scale);
  // Which scales can be chosen now: any lower one; the next step above the scale last measured only when the frames
  // drawn now put it under the ladder's step cap; nothing beyond it; and after a hold nothing higher until Run again.
  function markScales() {
    const base = ladderBase();
    const next = stepAbove(base);
    for (const [s, o] of scaleOpts) {
      if (!st.toy || s <= st.scale) { o.disabled = false; o.title = ''; continue; }
      if (st.tripped) { o.disabled = true; o.title = 'after a hold the stage continues lower: Run again first'; continue; }
      if (s <= base) { o.disabled = false; o.title = ''; continue; }
      if (s !== next) { o.disabled = true; o.title = `one step at a time: ${next} × first`; continue; }
      const p = stepPredict(s);
      o.disabled = !p || p.ms > LADDER.stepCapMs;
      o.title = !p ? `after ${LADDER.frames} frames measured at ${base} ×`
        : `about ${fmtMs(p.ms)} ms a frame${o.disabled ? `: past the ladder's ${LADDER.stepCapMs} ms step cap` : ''}`;
    }
  }

  function teardown() {
    st.token++;
    st.paramSeq++;
    stopLoop();
    stopFilm();
    if (st.paramTimer) { clearTimer(st.paramTimer); st.paramTimer = null; }
    if (st.toy) { try { st.toy.destroy(); } catch (e) { /* a lost context has nothing to free */ } }
    st.toy = null; st.canvas = null; st.running = false; st.tripped = false; st.receipt = null; st.frames = 0;
    st.raised = null; st.halted = null; st.haltedAt = null; st.pausedTotal = 0; st.preflight = null; st.refused = null;
    st.trip = null; st.loaded = null; st.gaps = []; st.paramsPending = false; st.busy = false;
    st.basis = null; st.locked = null; st.lockedScale = null; st.measures = 0; st.worstGap = 0;
    st.inFlight = false; st.pausedBy = null;
    setClass(box, 'is-held', false);   // a hold's outline belongs to the program it held, not to the next still
    markScales();
    stopBtn.disabled = true; takeBtn.disabled = true; scaleSel.disabled = true;
  }

  function setSubject(s) {
    // A frame in flight from the subject leaving is judged first: a refusal it earns is remembered for that subject.
    // Its receipt is not sent: the host has moved on to the next subject (the Workbench has already cleared the
    // Inspector's receipt for it), and the leaving one's would land beside the new datasheet.
    if (st.running) {
      st.leaving = true;
      try { judgeInFlight(); } finally { st.leaving = false; }
    }
    teardown();
    st.subject = s || null;
    st.params = null;
    if (!s) { showEmpty(); return; }
    st.gate = costGate(s.cost);
    st.scale = st.gate.scale;
    scaleSel.value = String(st.scale);
    side.textContent = s.kind === 'shelf' ? 'a loved shader' : s.kind === 'card' ? 'a module card' : '';
    caption.replaceChildren();
    put(caption, put(h(doc, 'div', 'wb-stage-titles'), h(doc, 'h3', 'wb-stage-title', s.title),
      s.byline && h(doc, 'p', 'wb-byline', s.byline)),
    s.licence && h(doc, 'span', `wb-licence is-${s.licenceClass || 'unknown'}`, s.licence));
    showCost(s.costWhy ? `${gateLine()} ${s.costWhy}` : null);
    run.textContent = runLabel(false);
    run.hidden = !!s.blocked || typeof s.load !== 'function';
    run.disabled = false;
    scaleLabel.hidden = run.hidden; stopBtn.hidden = run.hidden; takeBtn.hidden = run.hidden;
    showPoster(s);
    filmBtn.hidden = live || !poster.sprite;
    filmBtn.textContent = filmLabel();
    st.refused = live && !run.hidden ? refusals.get(subjectKey(s)) || null : null;
    if (!live) say(s.blocked ? `${s.blocked.why} ${LIVE_OFF_WORDS}` : viewOnlyWords());
    else if (s.blocked) say(s.blocked.why);
    else if (typeof s.load !== 'function') say(s.posterHint || 'Nothing to run for this subject yet.');
    else if (st.refused) {
      run.disabled = true;
      run.textContent = 'Refused on this GPU';
      say(`Refused earlier on this page: ${st.refused}. Nothing more runs on this GPU for this subject.`, 'warn');
    } else say('A still from SwiftShader. Nothing runs on this GPU until you press Run.');
  }

  // The SwiftShader receipt's warm frame time, when the subject has one: a second cost signal beside the class. It is
  // the CPU's time, so it ranks shaders against each other rather than predicting this GPU.
  function swiftLine() {
    const sw = st.subject && st.subject.swiftshader;
    if (!sw || !Number.isFinite(Number(sw.warmMs))) return null;
    const at = Array.isArray(sw.size) && sw.size.length === 2 ? ` at ${px(sw.size)}` : '';
    return h(doc, 'p', 'wb-cost-line wb-cost-sw',
      `SwiftShader (the CPU) drew a frame${at} in ${fmtMs(sw.warmMs)} ms, warm: a second cost signal, for comparing shaders.`);
  }

  function showCost(extra) {
    costRow.replaceChildren(costScale(doc, st.gate), put(h(doc, 'div', 'wb-cost-lines'),
      h(doc, 'p', 'wb-cost-line', extra || gateLine()), swiftLine()));
  }

  /** Raise the subject's class (never lower it): cls null means unknown, which is run as C4. Before the first run the
   *  button and the scale follow; at load the run starts at the raised class. True when it raised. */
  function raise(cls, why, atLoad = false) {
    const next = costGate(cls);
    if (gateRank(next) <= gateRank(st.gate)) return false;
    st.raised = { from: st.gate.known ? st.gate.cls : null, to: next.known ? next.cls : null, why, atLoad };
    st.gate = next;
    st.scale = Math.min(st.scale, next.scale);
    scaleSel.value = String(st.scale);
    const name = next.known ? next.cls : 'unknown (run as C4)';
    showCost(`Raised to ${name}${atLoad ? ' at load' : ''}: ${why}. ${live && next.heavy ? 'It starts at half scale at most.' : ''}`.trim());
    if (!st.toy && !st.refused) run.textContent = runLabel(false);
    return true;
  }

  // ---- the pre-flight ----
  // One timed draw of frame f at the toy's current size: the queue is drained first (drainGl), so nothing queued
  // before it (a compile, a buffer reallocation, another program's frame) is billed to it, and drained again to end it.
  // A draw under repsUnderMs is drawn again, up to maxReps or about repsTargetMs in all, and averaged.
  function timeDraw(toy, finish, timeSec, f) {
    finish();
    let t0 = now();
    toy.render({ time: timeSec, frame: f });
    finish();
    let total = now() - t0, reps = 1;
    if (total >= PREFLIGHT.repsUnderMs) return { ms: total, reps };
    while (reps < PREFLIGHT.maxReps && total < PREFLIGHT.repsTargetMs) {
      t0 = now();
      toy.render({ time: timeSec, frame: f });
      finish();
      total += now() - t0;
      reps++;
    }
    return { ms: total / reps, reps };
  }

  // The readings, at the stage's size now: frames 0 and 1 at PREFLIGHT size (the slower counts), after one draw that
  // shades one pixel; then, when they leave room, frames 0 and 1 at four times the pixels (about twice, for a heavy
  // tiny frame) with what a frame costs whatever its size (that one-pixel draw, timed) read before and after them, and
  // larger pairs while those leave the growth unproven, none larger than the frame at maxScale (the largest scale the
  // plan may choose: the class's start, or the scale a run is at); then the toy is reset so its live run starts at
  // frame 0 with clean buffers. A frame that throws is a refusal.
  function measure(toy, canvas, timeSec, maxScale = 1) {
    const basis = basisNow();
    const fullSize = sizeAt(1, basis);
    const gl = toy && toy.gl;
    const timedWith = !gl ? 'render' : [typeof gl.finish === 'function' && 'gl.finish',
      typeof gl.readPixels === 'function' && 'readPixels'].filter(Boolean).join(' + ') || 'render';
    const finish = () => drainGl(gl);
    const SCISSOR_TEST = 0x0C11;
    const scissors = !!gl && typeof gl.enable === 'function' && typeof gl.scissor === 'function';
    // One draw that shades a single pixel (scissored to 1 x 1), timed like a frame when `timed`.
    const onePixel = (timed) => {
      gl.enable(SCISSOR_TEST);
      gl.scissor(0, 0, 1, 1);
      try {
        if (timed) return timeDraw(toy, finish, timeSec, 0);
        toy.render({ time: timeSec, frame: 0 });
        return null;
      } finally { gl.disable(SCISSOR_TEST); }
    };
    let size = [PREFLIGHT.w, PREFLIGHT.h], compileMs = null, a0 = null, a1 = null, second = null, overhead = null;
    const more = [];
    try {
      toy.resize(PREFLIGHT.w, PREFLIGHT.h);
      size = [canvas.width || PREFLIGHT.w, canvas.height || PREFLIGHT.h];
      finish();
      // A draw that shades ONE pixel first (scissored to 1 x 1): a driver that compiles a pipeline at its first draw
      // (SwiftShader does; ANGLE can) does it here, so the compile is not billed to the timed frame. A draw scissored
      // to nothing is not enough: SwiftShader skips a fully clipped draw before compiling its pixel stage. Measured on
      // SwiftShader through ANGLE (2026-10-13, timed with the read-back wait): with a 0 x 0 warm-up, frame 0 of Ms2XWc
      // (C0) read 2.8 ms against 0.3 ms for frame 1; with 1 x 1 the compile (17 ms; lfscD7's 88.5 ms) lands here and
      // frame 0 reads 0.5 ms.
      if (scissors) {
        const c0 = now();
        onePixel(false);
        finish();
        compileMs = now() - c0;
      }
      // Frame 0 is the frame the live run starts on, and the one a shader may do its heaviest work on (filling its
      // buffers); frame 1 stands for the frames after it. A frame 0 already past the refusal limit ends it there.
      a0 = timeDraw(toy, finish, timeSec, 0);
      if (a0.ms <= PREFLIGHT.refuseMs) a1 = timeDraw(toy, finish, timeSec, 1);
      const ms = Math.max(a0.ms, a1 ? a1.ms : 0);
      const errOf = (reps) => PREFLIGHT.resolutionMs / (reps || 1);
      const tinyAt = a1 && a1.ms > a0.ms ? a1 : a0;
      const tiny = { ms, px: area(size), err: errOf(tinyAt.reps) };
      // The second point: four times the pixels, drawn only when the first leaves room for even the heaviest growth
      // the stage takes (the cube: 64 times its time) under the one-frame limit. Guarded only to the square (16 times),
      // a cube-law tiny frame of 20 ms drew a 1280 ms 128 x 72 one. When four times could pass the limit, about twice
      // the pixels (PREFLIGHT.mid, 8 times the time at the cube) if that cannot: a heavy tiny frame, or one a stall
      // inflated (25 ms), still gets a second reading, and one inflated reading does not refuse the subject. Nothing
      // is taken off for what every frame pays here: the tiny frame at its most is a bound on its own work. timeDraw
      // drains the queue first, so the reallocation the resize queues is not billed to it.
      const at2 = ms <= PREFLIGHT.refuseMs ? [[PREFLIGHT.w2, PREFLIGHT.h2], PREFLIGHT.mid]
        .find(([w2, h2]) => frameAtMost(tiny, w2 * h2, HEAVIEST_GROWTH) <= WATCHDOG.gapMs) : null;
      if (at2) {
        // What every frame pays whatever its size (the read-back's round trip, the submission): the one-pixel draw
        // again, timed as the frames are. Only the rest grows with the pixels, and left in the readings it hides that
        // growth: behind 0.1 ms of it a square-law cost of 0.03 ms at 64 x 36 reads 0.13 and 0.58 ms, which looks linear.
        const o1 = scissors ? onePixel(true) : null;
        toy.resize(at2[0], at2[1]);
        const size2 = [canvas.width || at2[0], canvas.height || at2[1]];
        const b0 = timeDraw(toy, finish, timeSec, 0);
        const b1 = b0.ms <= WATCHDOG.gapMs ? timeDraw(toy, finish, timeSec, 1) : null;
        const slow2 = b1 && b1.ms > b0.ms ? b1 : b0;
        second = { size: size2, ms: slow2.ms, frame0Ms: b0.ms, laterMs: b1 ? b1.ms : null, reps: slow2.reps };
        // ...and read once more, after that pair. A hiccup in the timing (a GC pause, the scheduler) only ever adds
        // time, so the smaller of the two readings is kept, uncertain by the larger of their resolutions: one slow draw
        // (a 10 ms reading for a 0.2 ms cost) zeroed the pixels' work, and a 576 ms pre-flight frame was drawn.
        const o2 = o1 && scissors ? onePixel(true) : null;
        if (o1) {
          const kept = o2 && o2.ms < o1.ms ? o2 : o1;
          overhead = { ms: kept.ms, reps: kept.reps, err: Math.max(errOf(o1.reps), o2 ? errOf(o2.reps) : 0),
            reads: [o1, o2].filter(Boolean).map((q) => ({ ms: q.ms, reps: q.reps })) };
        }
      }
      // Larger points, four times the pixels each, while the two largest readings leave the pixels' growth unproven
      // (their work near the timer's resolution, or hidden behind the overhead), each only when even the heaviest growth
      // of that work keeps the next frame under the ladder's step cap (the bar a step up meets), and none larger than
      // the frame at maxScale (a C4 subject's half scale: 1024 x 576 has more pixels than half of 1920 x 1080): each
      // larger reading stands further above both and nearer the size that will be drawn. A pixels-squared cost read at
      // 0.01 ms at 64 x 36 (0.16 ms at 128 x 72) allows anything from linear to the cube; its 256 x 144 frame (2.56 ms)
      // narrows that to about 1.9 to 2.1. The guard takes the work at its most: the larger reading at its most, less
      // what every frame pays at its LEAST, which is never more than the tiny frame (perFrameBounds sets a hiccup aside).
      if (second) {
        const mostPx = area(sizeAt(Math.min(1, Math.max(SCALES[0], Number(maxScale) || 1)), basis));
        let prev = tiny;
        let last = { ms: second.ms, px: area(second.size), err: errOf(second.reps) };
        const o = perFrameBounds(overhead ? { ms: overhead.ms, err: overhead.err } : null, [prev, last]);
        for (const [gw, gh] of PREFLIGHT.grow) {
          const nextPx = gw * gh;
          if (growthBounds(prev, last, o).proven || nextPx > mostPx) break;
          if (frameAtMost(last, nextPx, HEAVIEST_GROWTH, o) > LADDER.stepCapMs) break;
          toy.resize(gw, gh);
          const at = [canvas.width || gw, canvas.height || gh];
          const c0 = timeDraw(toy, finish, timeSec, 0);
          const c1 = c0.ms <= LADDER.stepCapMs ? timeDraw(toy, finish, timeSec, 1) : null;
          const pick = c1 && c1.ms > c0.ms ? c1 : c0;
          more.push({ size: at, ms: pick.ms, frame0Ms: c0.ms, laterMs: c1 ? c1.ms : null, reps: pick.reps });
          prev = last;
          last = { ms: pick.ms, px: area(at), err: errOf(pick.reps) };
        }
      }
      if (typeof toy.reset === 'function') toy.reset();
    } catch (e) {
      return { failed: `the pre-flight frame failed (${(e && e.message) || e})`, basis, size, fullSize, timedWith,
        compileMs, frame0Ms: a0 ? a0.ms : null, laterMs: a1 ? a1.ms : null, reps: 1 };
    }
    const slow = a1 && a1.ms > a0.ms ? a1 : a0;
    return { basis, size, fullSize, timedWith, compileMs, ms: slow.ms, frame0Ms: a0.ms, laterMs: a1 ? a1.ms : null,
      reps: slow.reps, resolutionMs: PREFLIGHT.resolutionMs / slow.reps, second, more, overhead };
  }

  /** The plan from a measurement: the largest scale up to classScale that fits the budget (preflightPlan), with live
   *  evidence folded in when given, each scale at its real pixel count over the measured basis. */
  function planFor(m, classScale, live = null) {
    const facts = { size: m.size, fullSize: m.fullSize, basis: m.basis, timedWith: m.timedWith,
      compileMs: m.compileMs === null || m.compileMs === undefined ? null : r1(m.compileMs),
      frame0Ms: m.frame0Ms === null || m.frame0Ms === undefined ? null : r1(m.frame0Ms),
      laterMs: m.laterMs === null || m.laterMs === undefined ? null : r1(m.laterMs), reps: m.reps || 1 };
    if (m.failed) {
      return { ...facts, ok: false, scale: null, ms: null, predictedMs: null, predictedFullMs: null, overBudget: true,
        refused: m.failed, perScale: [], second: null, more: [], overhead: null, exponent: null, growth: null, live: null };
    }
    const more = m.more || [];
    const plan = preflightPlan({ tinyMs: m.ms, tinyPx: area(m.size), fullPx: area(m.fullSize), classScale,
      secondMs: m.second ? m.second.ms : null, secondPx: m.second ? area(m.second.size) : null,
      readings: more.map((q) => ({ ms: q.ms, px: area(q.size), resolutionMs: PREFLIGHT.resolutionMs / (q.reps || 1) })),
      overheadMs: m.overhead ? m.overhead.ms : null,
      overheadResolutionMs: !m.overhead ? null : Number.isFinite(m.overhead.err) ? m.overhead.err
        : PREFLIGHT.resolutionMs / (m.overhead.reps || 1),
      resolutionMs: m.resolutionMs, secondResolutionMs: m.second ? PREFLIGHT.resolutionMs / (m.second.reps || 1) : null,
      live, pxByScale: SCALES.map((s) => area(sizeAt(s, m.basis))) });
    const shown = (q) => ({ size: q.size, ms: r1(q.ms), frame0Ms: r1(q.frame0Ms), laterMs: q.laterMs === null ? null : r1(q.laterMs),
      reps: q.reps || 1 });
    // What every frame pays, as read (the smaller of its two readings, and both), and whether it was set aside.
    const ms2 = (x) => Math.round(Number(x) * 100) / 100;
    return { ...plan, ...facts, ms: plan.tinyMs, second: m.second ? shown(m.second) : null, more: more.map(shown),
      overhead: m.overhead ? { ms: ms2(m.overhead.ms), reps: m.overhead.reps || 1,
        readsMs: (m.overhead.reads || []).map((q) => ms2(q.ms)), setAside: !!plan.overheadSetAside } : null };
  }
  const rowAt = (pf, s) => ((pf && pf.perScale) || []).find((q) => q.scale === s) || null;
  // The plan as run at scale s: 'start' (Run's rule), 'kept' (no more pixels than were measured, under the step cap),
  // 'raised' (a step); `why` is the reason it was measured again (null for Run's first measurement).
  function withScale(pf, s, how, why = null) {
    const row = rowAt(pf, s);
    return { ...pf, scale: s, predictedMs: row ? row.ms : pf.predictedMs, overBudget: how === 'start' ? !!pf.overBudget : false,
      how, why };
  }
  // The cost line once it has run: what was measured, and what it chose (it supersedes "a pre-flight measures it first").
  function preflightLine(pf, why) {
    const raised = st.raised ? `Raised to ${st.raised.to || 'unknown (run as C4)'}${st.raised.atLoad ? ' at load' : ''}: ${st.raised.why}. ` : '';
    const lead = why ? `Measured again (${why}): a` : 'Pre-flight: one';
    const which = pf.laterMs !== null && pf.laterMs !== undefined ? ' (the slower of frames 0 and 1)' : '';
    const big = (pf.more && pf.more.length ? pf.more[pf.more.length - 1] : pf.second) || null;
    const then = big ? ` and a ${px(big.size)} one ${fmtMs(big.ms)} ms` : '';
    // The growth behind the prediction, when it is more than the pixels' own or one the readings could not prove.
    const gr = pf.growth || null;
    const grows = !gr ? '' : gr.readings < 2 ? ', taking the heaviest growth (pixels cubed): one reading cannot show how its cost grows'
      : !gr.proven ? `, taking the steepest growth its readings allow (pixels to the power ${pf.exponent})`
        : pf.exponent >= 1.1 ? `, its cost growing as pixels to the power ${pf.exponent}` : '';
    const head = `${lead} ${px(pf.size)} frame took ${fmtMs(pf.ms)} ms${which}${then}, so a full ${px(pf.fullSize)} frame would take `
      + `about ${fmtMs(pf.predictedFullMs)} ms${grows}`;
    const verb = pf.how === 'kept' ? 'it stays at' : pf.how === 'raised' ? 'it stepped up to' : why ? 'it continues at' : 'it started at';
    const tail = `${verb} ${pf.scale} × (about ${fmtMs(pf.predictedMs)} ms a frame)`;
    return `${raised}${head}; ${tail}${pf.overBudget ? `, over the ${PREFLIGHT.budgetMs} ms budget even at the smallest scale` : ''}.`;
  }
  const pfReceipt = (pf) => (pf ? { size: pf.size, ms: pf.ms, fullSize: pf.fullSize, predictedFullMs: pf.predictedFullMs ?? null,
    scale: pf.scale, predictedMs: pf.predictedMs ?? null, overBudget: !!pf.overBudget, refused: pf.refused || null,
    perScale: pf.perScale || [], budgetMs: PREFLIGHT.budgetMs, refuseMs: PREFLIGHT.refuseMs, limitMs: WATCHDOG.gapMs,
    stepCapMs: LADDER.stepCapMs, timedWith: pf.timedWith || null, compileMs: pf.compileMs ?? null, second: pf.second || null,
    more: pf.more || [], overhead: pf.overhead || null, exponent: pf.exponent ?? null, growth: pf.growth || null,
    frame0Ms: pf.frame0Ms ?? null, laterMs: pf.laterMs ?? null, reps: pf.reps ?? null,
    basis: pf.basis || null, how: pf.how || null, why: pf.why || null, live: pf.live || null } : null);

  // ---- the loop ----
  // A rebuild that holds the loop (st.pausedBy) starts it again itself; nothing else may in the meantime.
  function schedule() { if (st.rafId === null && st.pausedBy === null) st.rafId = raf(frame); }
  function stopLoop() { if (st.rafId !== null) { caf(st.rafId); st.rafId = null; } }
  // iTime in ms: frozen while the loop is stopped, so Run again continues where it stopped.
  const clockMs = () => (st.haltedAt !== null ? st.haltedAt : now()) - st.t0 - st.pausedTotal;

  // The watchdog's verdict on the frame drawn last, at time t: its gap is the ladder's evidence, and a trip holds the
  // last frame. True when it held.
  function judge(t) {
    const w = watchdog.tick(t);
    st.inFlight = false;
    if (w.gap > 0) {
      st.gaps.push(w.gap);
      st.worstGap = Math.max(st.worstGap, w.gap);
      if (st.gaps.length > LADDER.window * 2) st.gaps.splice(0, st.gaps.length - LADDER.window);
      if (st.gaps.length >= LADDER.frames) markScales();
    }
    if (w.tripped) { hold(); return true; }
    return false;
  }
  /** The loop is about to stop for something other than a hold (Stop, the Shelf, a knob change, a size change, another
   *  subject): judge the frame in flight as the next animation frame would have, with the queue drained first so its
   *  GPU time is in. Nothing to judge when no frame was drawn since the last verdict, or while the tab is hidden (its
   *  rAF is the browser's throttle, not the GPU). True when it held. */
  function judgeInFlight() {
    if (!st.running || !st.toy || !st.inFlight || isHidden()) return false;
    try { drainGl(st.toy.gl); } catch (e) { /* a lost context: nothing is queued */ }
    return judge(now());
  }

  function frame() {
    st.rafId = null;
    if (!st.running || !st.toy) return;
    if (isHidden()) { halt('hidden', HIDDEN_WORDS); return; }
    // The frame drawn last is judged before anything else can stop the loop (the Shelf, a size change).
    const t = now();
    if (judge(t)) return;
    const away = isAway();
    if (away) { halt('away', awayWords(away)); return; }
    // The size the pre-flight measured is locked: a box, ratio or scale change measures again before any frame.
    if (sizeMoved()) { continueAfter(remeasure('size', st.scale, 'the stage changed size')); return; }
    try {
      st.toy.render({ time: (t - st.t0 - st.pausedTotal) / 1000 });
      st.frames++;
      st.inFlight = true;
    } catch (e) {
      halt('error', `Stopped: ${(e && e.message) || e}. The last frame holds.`, 'warn');
      return;
    }
    schedule();
  }

  const HIDDEN_WORDS = 'Stopped: the tab was hidden. Press Run again to continue from this frame.';
  const awayWords = (why) => `Stopped: ${why}. Press Run again to continue from this frame.`;
  const PENDING_WORDS = 'The knob change applies when you press Run again: nothing is drawn while the stage is stopped.';

  // Stop the loop, freeze the clock and say why; the canvas and its last frame stay.
  function halt(why, words, tone) {
    stopLoop();
    if (st.haltedAt === null) st.haltedAt = now();
    st.running = false;
    st.inFlight = false;
    st.halted = why;
    stopBtn.disabled = true;
    run.disabled = !!st.refused;
    run.textContent = runLabel('again');
    if (words) say(words, tone);
  }

  function tripLead(w) {
    return w.reason === 'gap'
      ? `one frame took ${fmtMs(w.gap)} ms (the limit is ${WATCHDOG.gapMs} ms; Windows resets the GPU at about 2 s)`
      : w.reason === 'budget'
        ? `slow frames in a row added up to ${fmtMs(w.streakMs)} ms (the budget is ${WATCHDOG.budgetMs} ms; the slowest took ${fmtMs(w.worst)} ms)`
        : `${WATCHDOG.trip} slow frames in a row (each more than ${WATCHDOG.slowMs} ms after the last; the slowest ${fmtMs(w.worst)} ms)`;
  }
  function tripWords(lower) {
    const next = lower === null
      ? 'It was already at the smallest scale, so nothing more runs on this GPU for this subject.'
      : `Run again measures it first and continues no higher than ${lower} × (fewer pixels than the frames that held).`;
    return `Held the last frame: ${tripLead(watchdog)}, so the stage stopped to protect the GPU. ${next}`;
  }
  // What a hold at the smallest scale is refused for, by the rule that tripped.
  function heldFor(t) {
    const at = t.size ? ` at ${px(t.size)}` : '';
    return t.reason === 'gap' ? `one frame took ${fmtMs(t.gapMs)} ms${at}`
      : t.reason === 'budget' ? `slow frames in a row added up to ${fmtMs(t.streakMs)} ms${at}`
        : `${t.slowFrames} slow frames in a row${at}`;
  }

  // The watchdog tripped: hold the last frame. Whatever the rule, the same size is not drawn again: Run again measures
  // first and continues below the frames that held (stepDown), and when nothing is below them it is refused.
  function hold() {
    st.trip = { reason: watchdog.reason, gapMs: Math.round(watchdog.gap), streakMs: Math.round(watchdog.streakMs),
      slowFrames: watchdog.streak, worstMs: Math.round(watchdog.worst), frames: st.frames, scale: st.scale,
      size: st.locked ? st.locked.slice() : null, basis: st.basis ? { ...st.basis } : null };
    st.tripped = true;
    const lower = stepDown(st.trip);
    if (lower === null) markRefused(`${heldFor(st.trip)}, at the smallest scale`);
    halt('tripped', tripWords(lower), 'warn');
    if (lower === null) {
      run.disabled = true;
      run.textContent = 'Refused after the hold';
      scaleSel.disabled = true;
    } else {
      st.scale = lower;
      scaleSel.value = String(lower);
      run.textContent = runLabel('again');
    }
    markScales();
    setClass(box, 'is-held', true);
    if (st.receipt) { st.receipt = { ...st.receipt, held: st.trip }; if (!st.leaving) onReceipt(st.receipt); }
  }

  // A measurement refused the program (a tiny frame over the refusal limit, even the smallest scale past the one-frame
  // limit at the new size, or nothing smaller than the frames that held): free it, put the still back, and nothing
  // more runs for this subject.
  function refuseRun(words, pf, lead = 'Refused by the pre-flight') {
    stopLoop();
    st.preflight = pf || st.preflight;
    markRefused(words);
    st.running = false; st.halted = 'refused'; st.tripped = false; st.inFlight = false;
    if (st.receipt) { st.receipt = { ...st.receipt, preflight: pfReceipt(st.preflight), refusedLater: words }; onReceipt(st.receipt); }
    try { st.toy.destroy(); } catch (e) { /* gone */ }
    st.toy = null; st.canvas = null; st.locked = null; st.lockedScale = null;
    setClass(box, 'is-held', false);
    if (st.subject) showPoster(st.subject);
    stopBtn.disabled = true; takeBtn.disabled = true; scaleSel.disabled = true;
    run.disabled = true;
    run.textContent = lead;
    say(`${lead}: ${words}. Nothing more runs on this GPU for this subject.`, 'warn');
  }

  /** Stop drawing and measure the program on stage again, at the size the stage has now, before its next frame. kind
   *  'raise' asks for one step up (`want`): kept only when the fresh numbers and the frames drawn so far both put it
   *  under the ladder's step cap, else it falls back as a size change at the scale it was drawing. Any other change
   *  ('size': the box, the ratio, the scale, or Run again after a hold) keeps `want` when that draws no more pixels than
   *  were measured and is predicted under the ladder's step cap; otherwise it starts over at the new size as Run does
   *  (the budget, never above `want`), the frames drawn so far counted with the pre-flight. Returns {ok, note}. */
  function remeasure(kind, want, why) {
    stopLoop();
    const live = liveEvidence(true);
    const fromPx = area(st.locked);
    const m = measure(st.toy, st.canvas, clockMs() / 1000, want);
    st.measures++;
    st.inFlight = false;
    let pf = planFor(m, want, live), scale = null, how = null, note = null;
    const outright = !!m.failed || m.ms > PREFLIGHT.refuseMs;
    if (!outright && kind === 'raise') {
      const row = rowAt(pf, want);
      if (row && row.ms <= LADDER.stepCapMs) { scale = want; how = 'raised'; }
      else {
        note = `measured again, ${want} × would take about ${fmtMs(row ? row.ms : NaN)} ms a frame, past the ladder's `
          + `${LADDER.stepCapMs} ms step cap`;
        want = st.lockedScale !== null && st.lockedScale < want ? st.lockedScale : (stepBelow(want) ?? SCALES[0]);
        pf = planFor(m, want, live);
      }
    }
    if (!outright && scale === null) {
      const row = rowAt(pf, want);
      // Kept: no more pixels than were measured, and predicted under the ladder's step cap (the bar a step up meets).
      if (row && area(sizeAt(want, m.basis)) <= fromPx && row.ms <= LADDER.stepCapMs) { scale = want; how = 'kept'; }
      else if (pf.ok) { scale = pf.scale; how = 'start'; }
    }
    if (scale === null) {
      refuseRun(pf.refused || `even at ${SCALES[0]} × a frame would take past the watchdog's ${WATCHDOG.gapMs} ms one-frame limit`, pf);
      return { ok: false, note };
    }
    pf = withScale(pf, scale, how, why);
    st.preflight = pf;
    lockAt(scale, m.basis);
    st.gaps = [];
    watchdog.reset();   // the measurement held the main thread; its time is not a frame's
    markScales();
    showCost(preflightLine(pf, why));
    if (st.receipt) {
      st.receipt = { ...st.receipt, scale, size: [st.canvas.width, st.canvas.height], preflight: pfReceipt(pf), measures: st.measures };
      onReceipt(st.receipt);
    }
    run.textContent = runLabel(st.running ? 'running' : 'again');
    return { ok: true, note };
  }
  // After a measurement the loop was running for: say what it chose, and draw on.
  function continueAfter(r) {
    if (!r.ok || !st.running) return;
    say(r.note ? `${cap(r.note)}; it runs at ${st.scale} ×. ${runningWords()}` : `Measured again at the new size. ${runningWords()}`,
      r.note || (st.preflight && st.preflight.overBudget) ? 'warn' : 'info');
    schedule();
  }

  // Continue a toy already on stage (after Stop, a hold, a hidden tab or the Shelf): a fresh watchdog window, and the
  // clock picks up where it stopped. After a hold, Run again never draws the frames that held again: it is capped below
  // them (stepDown, at the window as it is now; refused when nothing is below) and always measures first. Knob values
  // set while stopped are built (and measured) first; a size that moved while stopped is measured first.
  async function resume() {
    if (!live || !st.toy || st.refused || st.running || st.busy) return;
    let afterHold = false;
    if (st.tripped) {
      const below = stepDown(st.trip);
      if (below === null) {
        const smallest = sizeAt(SCALES[0], basisNow());
        refuseRun(`after the hold at ${px(st.trip.size || [0, 0])}, no scale draws fewer pixels at this window's size and pixel `
          + `ratio (even ${SCALES[0]} × is ${px(smallest)})`, null, 'Refused after the hold');
        return;
      }
      st.scale = Math.min(st.scale, below);
      scaleSel.value = String(st.scale);
      afterHold = true;
    }
    let rebuilt = false;
    if (st.paramsPending) {
      st.busy = true;
      run.disabled = true;
      say('Rebuilding with the knob values you set, and measuring it, before any frame...');
      let ok = false;
      try { ok = await rebuild(st.paramSeq, true); } finally { st.busy = false; }
      if (!st.toy || st.refused || st.running) return;
      if (!ok) { run.disabled = false; if (st.paramsPending) say(PENDING_WORDS); return; }
      rebuilt = true;   // measured just now, at the size the stage has, never above the scale asked for
    }
    if (st.haltedAt !== null) { st.pausedTotal += now() - st.haltedAt; st.haltedAt = null; }
    st.running = true; st.tripped = false; st.halted = null;
    setClass(box, 'is-held', false);
    stopBtn.disabled = false; run.disabled = true;
    run.textContent = runLabel('running');
    if (isHidden()) { halt('hidden', HIDDEN_WORDS); return; }
    const away = isAway();
    if (away) { halt('away', awayWords(away)); return; }
    let note = null;
    if (!rebuilt && (afterHold || sizeMoved())) {
      const raising = !afterHold && st.lockedScale !== null && st.scale > st.lockedScale;
      const why = afterHold ? 'below the frames that held' : raising ? 'a step up the ladder' : 'the size changed while it was stopped';
      const r = remeasure(raising ? 'raise' : 'size', st.scale, why);
      if (!r.ok) return;
      note = r.note;
    }
    watchdog.reset();
    run.textContent = runLabel('running');
    say(note ? `${cap(note)}; it runs at ${st.scale} ×. ${runningWords()}` : runningWords(), note ? 'warn' : 'info');
    schedule();
  }

  if (live && typeof opts.onVisibilityChange === 'function') {
    // Hidden stops the loop; visible again does not restart it (Run is an explicit click).
    opts.onVisibilityChange(() => { if (isHidden() && st.running) halt('hidden', HIDDEN_WORDS); });
  }

  /** A host hiding the Stage (the Shelf tab in front) stops the loop with a reason; nothing restarts it but Run. The
   *  frame in flight is judged first; view only, the filmstrip stops. */
  function suspend(why) {
    stopFilm();
    if (!st.running) return false;
    if (judgeInFlight()) return true;
    halt('away', awayWords(why || 'the Stage is not in view'));
    return true;
  }

  const runningWords = () => {
    const c = st.canvas;
    return `Running live at ${st.scale} × (${c ? `${c.width} × ${c.height} px` : '?'}). Leaving the Stage stops it; the watchdog `
      + `holds the last frame if frames struggle (${WATCHDOG.budgetMs} ms of slow frames, or one over ${WATCHDOG.gapMs} ms).`;
  };

  function emitReceipt(loaded, compile) {
    const info = st.toy && typeof st.toy.info === 'function' ? st.toy.info() : {};
    const stats = st.toy && typeof st.toy.stats === 'function' ? st.toy.stats() : {};
    const extra = (loaded && loaded.receipt) || {};
    const c = st.canvas;
    st.receipt = {
      api: 'arsenal.workbench-run/v1', subject: st.subject.title, kind: st.subject.kind, id: st.subject.id,
      renderer: info.renderer || null, vendor: info.vendor || null, scale: st.scale,
      size: c && st.toy ? [c.width, c.height] : null, cost: st.gate.cls, costKnown: st.gate.known, raised: st.raised,
      compile: compile ? { ok: !!compile.ok, drawable: !!compile.drawable,
        firstError: ((compile.passes || []).find((p) => !p.ok) || {}).firstError || null, warnings: compile.warnings || [] } : null,
      preflight: pfReceipt(st.preflight), measures: st.measures,
      swiftshader: st.subject.swiftshader || null,
      substituted: stats.substituted || [], unsupported: stats.unsupported || [],
      startedAt: new Date().toISOString(), ...extra,
    };
    onReceipt(st.receipt);
  }

  // Build a toy on a fresh canvas and compile it. Returns {toy, canvas, compile} or throws with a reason. The ONLY place
  // a canvas and a WebGL context are made: it refuses first while the switch is off.
  async function build(runtime, loaded) {
    mustBeLive('a live canvas');
    const canvas = h(doc, 'canvas', 'wb-canvas', null, { 'aria-label': `${st.subject.title}, running live` });
    const toy = runtime.createToy(canvas, loaded.shader, { mediaUrl: loaded.mediaUrl || null, pixelRatio: 1, fps: 60,
      dateBase: null });
    await (toy.ready || Promise.resolve());
    const compile = toy.compile();
    return { toy, canvas, compile };
  }

  // What a load found that raises the class: buffers (render targets), or a module heavier than the subject's own.
  function raiseFromLoad(loaded) {
    const floor = costFloorFromShader(loaded.shader);
    if (floor) raise(floor, 'it keeps render targets between frames (buffers)', true);
    if (loaded.cost && typeof loaded.cost === 'object') raise(loaded.cost.cls ?? null, loaded.cost.why || 'a module it uses is heavier', true);
  }

  async function start() {
    if (!live) return;
    const s = st.subject;
    if (!s || typeof s.load !== 'function' || s.blocked || st.refused) return;
    if (st.toy) { await resume(); return; }
    const token = ++st.token;
    run.disabled = true;
    say('Loading the runtime...');
    let runtime, loaded;
    try { runtime = await loadLive(); } catch (e) {
      if (token !== st.token) return;
      run.disabled = false;
      say(`The runtime did not load: ${(e && e.message) || e}.`, 'warn');
      return;
    }
    if (token !== st.token) return;
    say(`Fetching ${s.title}...`);
    try { loaded = await s.load(st.params); } catch (e) {
      if (token !== st.token) return;
      run.disabled = false;
      say(`Could not load ${s.title}: ${(e && e.message) || e}.`, 'warn');
      return;
    }
    if (token !== st.token) return;
    raiseFromLoad(loaded);
    let built;
    try { built = await build(runtime, loaded); } catch (e) {
      if (token !== st.token) return;
      run.disabled = false;
      say(`The runtime refused it: ${(e && e.message) || e}.`, 'warn');
      return;
    }
    if (token !== st.token) { try { built.toy.destroy(); } catch (e) { /* gone */ } return; }
    st.toy = built.toy; st.canvas = built.canvas;
    if (!built.compile.drawable) {
      const first = (built.compile.passes || []).find((p) => !p.ok);
      emitReceipt(loaded, built.compile);
      try { st.toy.destroy(); } catch (e) { /* gone */ }
      st.toy = null; st.canvas = null;
      run.disabled = false;
      say(`It did not compile here: ${first ? first.firstError || first.name : 'no Image pass'}. Nothing ran.`, 'warn');
      return;
    }
    // The pre-flight: tiny frames decide whether, and at what scale, this program draws a full-size frame here.
    const startAt = Math.min(st.scale, st.gate.scale);
    const m = measure(built.toy, built.canvas, 0, startAt);
    let pf = planFor(m, startAt);
    st.preflight = pf;
    st.measures = 1;
    if (!pf.ok) {
      emitReceipt(loaded, built.compile);
      try { st.toy.destroy(); } catch (e) { /* gone */ }
      st.toy = null; st.canvas = null;
      markRefused(pf.refused);
      run.disabled = true;
      run.textContent = 'Refused by the pre-flight';
      say(`Refused by the pre-flight: ${pf.refused}. Nothing more runs on this GPU for this subject.`, 'warn');
      return;
    }
    pf = withScale(pf, pf.scale, 'start');
    st.preflight = pf;
    st.gaps = []; st.worstGap = 0;
    const still = h(doc, 'span', 'wb-badge is-live', 'live · this GPU');
    box.replaceChildren(built.canvas, still);
    lockAt(pf.scale, m.basis);
    markScales();
    st.t0 = now(); st.pausedTotal = 0; st.haltedAt = null; st.frames = 0;
    st.running = true; st.tripped = false; st.halted = null; st.trip = null; st.inFlight = false;
    watchdog.reset();
    setClass(box, 'is-held', false);
    stopBtn.disabled = false; takeBtn.disabled = false; scaleSel.disabled = false;
    run.textContent = runLabel('running');
    showCost(preflightLine(pf));
    say(runningWords(), pf.overBudget ? 'warn' : 'info');
    emitReceipt(loaded, built.compile);
    st.loaded = loaded;
    if (isHidden()) { halt('hidden', HIDDEN_WORDS); return; }
    const away = isAway();
    if (away) { halt('away', awayWords(away)); return; }
    schedule();
  }

  function stop() {
    if (!live || !st.toy || !st.running) return;
    if (judgeInFlight()) return;   // the frame in flight held: the hold says why, and Run again continues lower
    halt('stopped', 'Stopped. The last frame holds; nothing is drawing. Run again continues from this frame.');
  }

  // A scale change is a size change: while drawing, the stage measures again at the new size before its next frame;
  // while stopped, the scale is kept for Run again, which measures first. A raise is a ladder step (above), one step
  // above the scale last measured, also while stopped; after a hold only a lower scale until Run again.
  function setScale(x) {
    if (!live) return;
    let s = Number(x);
    if (!SCALES.includes(s)) return;
    if (!st.toy) { st.scale = s; scaleSel.value = String(s); run.textContent = runLabel(null); return; }
    if (st.busy || st.pausedBy !== null) { scaleSel.value = String(st.scale); return; }
    // The frame in flight is judged before anything here can stop the loop.
    if (st.running && judgeInFlight()) { scaleSel.value = String(st.scale); return; }
    const refuse = (words) => { scaleSel.value = String(st.scale); say(words, 'warn'); };
    if (st.tripped && s > st.scale) {
      refuse(`After a hold the stage continues lower, never higher: Run again first (it continues no higher than ${st.scale} ×).`);
      return;
    }
    const base = ladderBase();
    let stepped = null;
    if (s > base && s > st.scale) {
      const next = stepAbove(base);
      const p = stepPredict(next);
      if (!p) {
        refuse(`Let it draw a moment at ${base} × first: a larger scale is predicted from the frames drawn there `
          + `(${Math.min(st.gaps.length, LADDER.frames)} of ${LADDER.frames} measured).`);
        return;
      }
      if (p.ms > LADDER.stepCapMs) {
        refuse(`${next} × would take about ${fmtMs(p.ms)} ms a frame by the frames drawn at ${base} × (the slowest of `
          + `the last ${p.n} took ${fmtMs(p.liveMs)} ms), past the ladder's ${LADDER.stepCapMs} ms step cap; the stage stays at ${st.scale} ×.`);
        return;
      }
      if (s > next) {
        stepped = `One step at a time: ${next} × now (about ${fmtMs(p.ms)} ms a frame predicted, and measured again there). `
          + 'Raise again once it has drawn a moment there.';
      }
      s = next;
    }
    if (s === st.scale && !sizeMoved()) { scaleSel.value = String(s); return; }
    const raising = st.lockedScale !== null && s > st.lockedScale;
    st.scale = s;
    scaleSel.value = String(s);
    if (!st.running) {
      run.textContent = runLabel('again');
      markScales();
      say(stepped || `Scale set to ${s} ×. Nothing draws until Run again, which measures it at that size first.`);
      return;
    }
    const r = remeasure(raising ? 'raise' : 'size', s, raising ? 'a step up the ladder' : 'a new scale');
    if (!r.ok) return;
    if (r.note) say(`${cap(r.note)}; the stage stays at ${st.scale} ×.`, 'warn');
    else say(stepped || runningWords());
    schedule();
  }

  function take() {
    if (!live || !st.canvas || typeof st.canvas.toDataURL !== 'function') return null;
    let url;
    try { url = st.canvas.toDataURL('image/png'); } catch (e) { say(`Could not take a still: ${(e && e.message) || e}.`, 'warn'); return null; }
    const t = { url, receipt: { ...(st.receipt || {}), t: Math.round(clockMs() / 10) / 100, takenAt: new Date().toISOString() } };
    onTake(t);
    return t;
  }

  // Knob values for a card that reads them. While drawing: rebuild the program (debounced) on a fresh canvas, and only
  // the newest values ever land (each change takes a number; an older rebuild that finishes later is dropped). Before
  // the compile, which holds the main thread, the loop stops, the program on stage finishes its queued frame (they
  // share one GPU) and that frame is judged: a hold there leaves the values for Run again. The rebuilt program then
  // starts at Run's own budget, never above the scale it replaces, and one that does not compile or that the pre-flight
  // refuses is never swapped in; the loop then goes on from a fresh watchdog window (the compile and the refused tiny
  // frames held the main thread, not the GPU). While stopped, held or hidden nothing is built or drawn: the values wait
  // for Run again.
  async function rebuild(seq, forRun = false) {
    const token = st.token;
    const stale = () => token !== st.token || seq !== st.paramSeq || !st.toy;
    let runtime, loaded, built = null;
    const drop = () => { if (built) { try { built.toy.destroy(); } catch (e) { /* gone */ } built = null; } };
    // The loop this rebuild holds starts again from a fresh watchdog window, unless a newer rebuild holds it now or the
    // stage stopped meanwhile.
    const carryOn = () => {
      if (st.pausedBy !== seq) return;
      st.pausedBy = null;
      if (st.running && st.toy) { watchdog.reset(); schedule(); }
    };
    try {
      runtime = await loadLive();
      if (stale()) return false;
      loaded = await st.subject.load(st.params);
      if (stale()) return false;
      if (!st.running && !forRun) { st.paramsPending = true; say(PENDING_WORDS); return false; }
      if (st.running) {
        stopLoop();
        st.pausedBy = seq;
        if (judgeInFlight()) { st.pausedBy = null; st.paramsPending = true; return false; }   // held: Run again builds it
        try { drainGl(st.toy.gl); } catch (e) { /* lost: nothing queued */ }
      }
      built = await build(runtime, loaded);
    } catch (e) {
      drop();
      if (!stale()) { st.paramsPending = false; say(`The knob change did not rebuild: ${(e && e.message) || e}. The stage keeps the last good program.`, 'warn'); }
      carryOn();
      return false;
    }
    if (stale()) { drop(); carryOn(); return false; }
    if (!built.compile.drawable) {
      drop();
      st.paramsPending = false;
      say('That knob value did not compile; the stage keeps the last good program.', 'warn');
      carryOn();
      return false;
    }
    if (!st.running && !forRun) { drop(); st.paramsPending = true; say(PENDING_WORDS); carryOn(); return false; }
    stopLoop();
    try { drainGl(st.toy.gl); } catch (e) { /* lost: nothing queued */ }
    const m = measure(built.toy, built.canvas, clockMs() / 1000, st.scale);
    let pf = planFor(m, st.scale);
    if (!pf.ok) {
      drop();
      st.paramsPending = false;
      say(`That knob value did not pass the pre-flight: ${pf.refused}. The stage keeps the last good program.`, 'warn');
      carryOn();
      return false;
    }
    try { st.toy.destroy(); } catch (e) { /* gone */ }
    st.toy = built.toy; st.canvas = built.canvas; st.loaded = loaded;
    const compile = built.compile;
    built = null;
    pf = withScale(pf, pf.scale, 'start');
    st.preflight = pf;
    st.measures = 1;
    st.paramsPending = false;
    box.replaceChildren(st.canvas, h(doc, 'span', 'wb-badge is-live', 'live · this GPU'));
    lockAt(pf.scale, m.basis);
    st.gaps = [];
    st.inFlight = false;
    showCost(preflightLine(pf));
    markScales();
    run.textContent = runLabel(st.running ? 'running' : 'again');
    watchdog.reset();   // the rebuild held the main thread; its gap is not the GPU's
    emitReceipt(loaded, compile);
    if (st.pausedBy === seq) st.pausedBy = null;
    if (st.running && st.pausedBy === null) schedule();
    return true;
  }

  function setParams(p) {
    st.params = p || null;
    if (!live || !st.toy || !st.subject || !st.subject.acceptsParams) return;
    const seq = ++st.paramSeq;
    if (st.paramTimer) { clearTimer(st.paramTimer); st.paramTimer = null; }
    if (!st.running) { st.paramsPending = true; say(PENDING_WORDS); return; }
    st.paramTimer = setTimer(() => { st.paramTimer = null; return rebuild(seq); }, PARAM_DEBOUNCE_MS);
  }

  /** Before any run: a heavier class learned after the subject was set (a card's own `uses`) raises the gate. */
  function raiseCost(cls, why) {
    if (st.toy || !st.subject) return false;
    return raise(cls, why, false);
  }

  // ---- watching the size: the window, the box and the pixel ratio (the loop also checks before every frame) ----
  function onSizeEvent() {
    if (!st.running || !st.toy || st.busy || st.pausedBy !== null || !sizeMoved()) return;
    if (judgeInFlight()) return;   // the frame in flight held: nothing is measured or drawn until Run again
    continueAfter(remeasure('size', st.scale, 'the stage changed size'));
  }
  function watchSizeDefault(fn) {
    const g = globalThis, offs = [];
    try {
      if (typeof g.addEventListener === 'function') { g.addEventListener('resize', fn); offs.push(() => g.removeEventListener('resize', fn)); }
      if (typeof g.ResizeObserver === 'function') {
        const ro = new g.ResizeObserver(() => fn());
        ro.observe(box);
        offs.push(() => ro.disconnect());
      }
      if (typeof g.matchMedia === 'function') {
        // (resolution: Ndppx) stops matching when the ratio moves (zoom, another monitor): listen, then re-arm at the new one.
        let mq = null;
        const listen = (on) => {
          if (!mq) return;
          if (on) { if (mq.addEventListener) mq.addEventListener('change', onRatio); else if (mq.addListener) mq.addListener(onRatio); }
          else if (mq.removeEventListener) mq.removeEventListener('change', onRatio); else if (mq.removeListener) mq.removeListener(onRatio);
        };
        const arm = () => { listen(false); mq = g.matchMedia(`(resolution: ${Number(dpr()) || 1}dppx)`); listen(true); };
        const onRatio = () => { arm(); fn(); };
        arm();
        offs.push(() => listen(false));
      }
    } catch (e) { /* the loop's own check before every frame still holds */ }
    return () => { for (const off of offs) { try { off(); } catch (e) { /* gone */ } } };
  }
  // View only, nothing draws, so nothing needs to know the size.
  const unwatch = live ? ((watchSize || watchSizeDefault)(onSizeEvent) || (() => {})) : () => {};

  run.addEventListener('click', () => { start(); });
  stopBtn.addEventListener('click', stop);
  takeBtn.addEventListener('click', take);
  scaleSel.addEventListener('change', () => setScale(scaleSel.value));
  filmBtn.addEventListener('click', () => { if (film) stopFilm(); else playFilm(); });
  showEmpty();

  return {
    el: root, live, setSubject, run: start, stop, suspend, setScale, take, setParams, raiseCost,
    // live: a toy is on stage (a live run exists); liveSwitch: the switch, as read at mount
    state: () => ({ liveSwitch: { on: live, asked: sw.asked, set: sw.set }, running: st.running, tripped: st.tripped,
      halted: st.halted, scale: st.scale, cost: st.gate.cls,
      costKnown: st.gate.known, frames: st.frames, subject: st.subject ? st.subject.id : null, live: !!st.toy,
      preflight: pfReceipt(st.preflight), measures: st.measures, basis: st.basis, locked: st.locked,
      worstGapMs: r1(st.worstGap), recentGapsMs: st.gaps.slice(-LADDER.window).map(r1), paramsPending: st.paramsPending,
      trip: st.trip, refused: st.refused, status: status.textContent, label: run.textContent,
      film: film ? { frame: film.i, frames: film.n } : null,
      canvas: st.canvas && st.toy ? [st.canvas.width, st.canvas.height] : null }),
    destroy() { teardown(); unwatch(); },
  };
}
