// VJ lasers v2: arsenal/web/vj-lasers.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_lasers.test.mjs.
//
// Daniel, 2026-10-24: "for the lasers perhaps we can do a triple strobe, or a one two flicker, it could be timed to the
// bpm of the track ... we can also alternate which lasers fire as well as have multi color bursts. I want there to be a
// lot of variety and strong color themes", then "we could have another button to make the lasors vibrate like how our
// piano strings do! t t tou blur blur flash would look so sick!, or if they did that in a 3d shape like a circle,
// triangle or any other cool looking pattern!", then "did we update the lasor to have more permutations and to have
// different effects depending on the rapidness of retrigger? also do we have multiple start locations beyond the 3, i
// want us to have two banks of laser."
//
// The build spec: research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-2026-10-24.md (slice S3).
// This module is the laser ENGINE. The page calls hit() / release() on pad 2, frame() once per animation frame, and draws
// the records frame() returns (a beam layer with no feedback; see "The output" below). It never touches the DOM, WebGL,
// the FlashGate or the clock's owner: it reads a clock and returns numbers.
//
// What it decides:
//   - TWO BANKS of heads: Bank A, 8 heads along the overhead truss; Bank B, 8 heads along the floor; 2 heads on each side
//     tower; and the hero head behind the centre. 21 start locations (today's burst cycles 4).               HEADS
//   - bank modes: A, B, alternate (hits switch banks), both, call (A fires, B answers on the off-beat), mirror (A and its
//     B twin together), or auto (dealt).                                                                   BANK_MODES
//   - PERMUTATIONS: shuffled decks (seeded, no repeat until a deck is used up) of 17 patterns, 12 head orders, 11 colour
//     modes, the bank and the start head, plus the hit seed's angle, spread and beam count. A hit's signature never
//     repeats within the last 32 hits, and consecutive hits differ on at least two axes.       PATTERNS ORDERS COLOUR_MODES
//   - RETRIGGER-SPEED TIERS, measured in beats since the previous press: more than a bar = one varied burst; within a bar
//     = escalate (more heads, a second colour; the third press is a crown from the hero, at most one hero in 6 hits);
//     within a beat = a one-two flicker; an eighth note or faster = a strobe roll locked to the grid (8ths, then 16ths);
//     held = a continuous gate (a roll that doubles with the build, push-pull on the drop). Velocity tiers: soft single,
//     medium one-two, hard triple (a named option inverts them). The edges sit halfway between the musical divisions,
//     never on them, so a human eighth-note stream stays one roll and quarter notes stay flickers.     TIERS RETRIGGER
//   - BPM-LOCKED GATES: 15 named gates on beat divisions, including Daniel's phrase "t t tou blur blur flash", scheduled
//     from the clock and lit in the frame whose picture lands just BEFORE the beat, never after it.            GATES
//   - VIBRATE: beams ring like plucked strings (three standing-wave modes with decaying envelopes, nodes at both ends),
//     with a blur output for motion-blur trails.                                                            VIB
//   - SHAPES: line-art figures round the hero (circle, triangle, square, star, spiral, Lissajous knot, tunnel, and
//     rotating 3D wireframes projected in perspective), morphing into each other on the beat.                SHAPES
//   - SAFETY, before anything is drawn: a CHANGE ESTIMATOR measures what WCAG 2.3.1 measures -- the share of each
//     one-third-frame window (slid over every position) whose luminance moves by 0.1 or more from one frame to the next,
//     with each line matched to itself in the frame before, so a beam that appears counts its lit band, a beam that moves
//     counts where it was and where it is, and a core strobing under a held halo counts only the core. Every new hit is
//     fitted to its budget (fast gates: 15 % of a window, 8 % of the frame; single onsets: 22 % / 8 %) over its whole
//     life -- its pulses wherever they can land (a loop's whole cycle on the finest grid it can run on, with every group
//     of heads it may light, so every position, figure and head it can show), its motion and its tail, by simulating
//     it; a dense figure sharpens or dims on its own, a ringing hit whose lines are blur-bound sharpens, and a pattern
//     that draws every step's heads gives way head by head -- and every frame is checked: the hit whose new or moving
//     beams change the most gives up its outermost beams (sticky, never given back mid-hit; a static beam is never taken,
//     since taking it would itself be a change), and a hit whose lines are (nearly) all new or moving dims; a frame that
//     cannot get under goes out as the best reduction found. A new hit PLAYS ALONE, so the fit of each hit alone is the
//     fit of the frame: a fast one chokes the hits before it, any other takes over from its first pulse (latest takes
//     precedence; a loop on the same grid hands over its off-beats), and it lights only once they are dark -- put out
//     AHEAD of time, in the frame before its first pulse, so that pulse still lands on its beat (and when the press
//     leaves no frame between, put out with it if what is left changes nothing measurable or fits the budget with the
//     new onset). A held loop starts on a grid point it can still light on time. Presses
//     faster than 3 a second count as a fast gate. A fast hit never moves while lit (a rapid press's velocity waits for
//     the next pulse, and never passes the velocity the roll was fitted at; barswap swaps on the pulse's own bar line).
//     A hit keeps the settings it was fitted to (Vibrate's plucks, the theme's colours) for its whole life. The strings
//     ring on their own clock, which never steps more than 1.2 frames at once, so a dropped frame cannot double a
//     ringing line's step. Red is never emitted.                                  estimateChange estimateArea BUDGET
//
// Coordinates: centred units, frame height = 1, +y up, x in [-aspect/2, +aspect/2] (the overlay's `p` in vj.js). The
// hero point is (0, 0.05), 45 % from the top. Widths and blur are pixels at 1080 lines (the shader scales by height/1080,
// as the overlay's `rs` does). Colours are LINEAR rgb (the beam layer adds light in linear space).
//
// The clock: any object {bpm, phaseAt(t), nextBeatAt(t)}; optional conf (0..1), posAt(t) (a continuous beat number,
// preferred when present) and alive(t). Times are milliseconds on the page's clock (performance.now()). The page's
// BeatClock (vj-core.js) plugs in through clockFromBeatClock(). With no clock (or a dead one) the engine runs on the last
// known tempo, else 150 BPM.
//
// THE OUTPUT (frame(t) returns the same object every call; copy what you keep):
//   seg      Float32Array(MAX_SEGMENTS * 8): n RECORDS of 2 RGBA texels. Upload it as an RGBA32F texture SEG_TEXELS (2)
//            wide and MAX_SEGMENTS tall; row i is record i. A pixel costs ONE fetch per record it is far from and TWO per
//            record it is near: read texel 0, cull by distance, and only then read texel 1.
//              texel 0  x0, y0, x1, y1: the line, centred units. A GROUP HEADER instead has w >= GROUP_MARK (1000):
//                       (cx, cy, radius, GROUP_MARK + count): the next `count` rows are the pieces of one figure (line
//                       art), all within `radius` of (cx, cy) (ring and blur included). A pixel farther than radius +
//                       halo cutoff skips the whole group (one fetch). Otherwise it keeps the NEAREST distance over the
//                       group's pieces (texel 0 only) and adds the group's light once, from the nearest piece's texel 1:
//                       adding pieces separately would double every joint into a bead.
//              texel 1  four 24-bit integers stored exactly in floats (every value below 2^24):
//                .x colour = R * 65536 + G * 256 + B, 8 bits each, square-root encoded: linear = (q / 255)^2
//                .y levels = I * 4096 + G, 12 bits each, value = q / 4095 * LEVEL_MAX (1.25). I: the core's level
//                   (0 in a gate's dark gap); G: glow, the overlay's Lorentzian halo, 1 / (1 + (d / 4 px)^2) at 16 px
//                   scale; in a fast gate held at 75 % through a gap when the next pulse fires the same heads of a still
//                   pattern, so only the cores strobe
//                .z shape = W + 64 * (H + 128 * (B + 128 * (kind + 2 * flags))): W core width = q / 16 px (never over
//                   3.6); H heat = q / 8, the white-core strength for hotCore() (the overlay's (1 + 2 vel) * e); B blur
//                   = q / 4 px, the motion-blur band (spread the core's light over width + 2 blur); kind 0 beam, 1 figure
//                   line; flags: 1 = the halo is held (only the core flashes), 2 = RINGING
//                .w ring = c1 + 256 * c2 + 65536 * c3, 8 bits each: a ringing beam (Vibrate) is ONE record bent by the
//                   shader: the displacement at u in [0, 1] along it is d(u) = sum (q_n - 128) * RING_Q[n] *
//                   sin(n pi u) px at 1080, along the left normal (-dy, dx) / len, still at both ends; its blur band is
//                   B * sin(pi u). The coefficients already carry the string's phase this frame.
//            Distances, widths and blur are px at 1080 lines (scale by height / 1080, as the overlay's `rs` does). The
//            light fades along a beam by exp(-along * BEAM_FALLOFF) (along in frame heights, from x0, y0); figures do
//            not fade. HALO_CUTOFF_PX (48 at 1080): the halo may be windowed off from half that radius to it; past it
//            a record contributes nothing (the cull radius). decodeSeg() is the reference decoder, in JavaScript.
//   n        records written (group headers included)
//   head     Int16Array(MAX_SEGMENTS): each record's head (index into HEADS; -1 for a group header); not uploaded
//   heads    Float32Array(21): each head's level this frame (0..1)
//   padGrid  Float32Array(12): head activity folded onto the KeyLab's 4 x 3 pad grid (row 1 = Bank A, row 2 = towers and
//            hero, row 3 = Bank B), for a "laser view" of the pad LEDs
//   pad      { level, rgb, tier }: pad 2's LED (tier brightness 0.6 / 0.8 / 1.0 while lasers run, 0 at rest; rgb = the
//            laser colour, linear; the page maps it to the theme's LED stand-in)
//   area     { frame, window, litFrame, litWindow, over }: frame and window = the estimated share of the frame, and of
//            the worst one-third window, whose light CHANGES this frame (what the budget holds); lit* = the share lit;
//            over = true if no beam could give way and the frame went out over its budget (the limiter's case)
//   solo     1, or 0.3 while a gate runs (the scene's idle beams dip, like a laser desk's Flash-Solo)
//   events   [{type: "pulse", hit, k, act} | {type: "flash", level} | {type: "pluck", head} | {type: "hero"}]; a
//            "flash" is the phrase's last syllable: the page may route a white flash through its FlashGate. The lasers
//            themselves never ask the FlashGate.
//   gate, pattern, tier, bank, order, colour: the newest running hit's labels, for the HUD
// stripBus(engine) packs the spec's strip head bus (texels 9-14 of row 2) for scenes tagged `laser-heads`.

export const LASERS_API = "arsenal.vj-lasers/v2";   // v2 (round 1): 2-texel records, area = change

const TAU = Math.PI * 2;
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const clamp01 = (x) => clamp(x, 0, 1);
const smooth = (x) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
const frac = (x) => x - Math.floor(x);
const hyp = (x, y) => Math.sqrt(x * x + y * y);      // (Math.hypot is several times slower, and the hot loops call this)
const REF_PX = 1080;

export const HERO = Object.freeze({ x: 0, y: 0.05 });
// the output record (see THE OUTPUT above)
export const SEG_FLOATS = 8;
export const SEG_TEXELS = 2;
export const MAX_SEGMENTS = 512;
export const SEG = Object.freeze({ X0: 0, Y0: 1, X1: 2, Y1: 3, COLOUR: 4, LEVELS: 5, SHAPE: 6, RING: 7 });
export const GROUP_MARK = 1000;
export const LEVEL_MAX = 1.25;
export const RING_Q = Object.freeze([0.15, 0.075, 0.04]);
export const HALO_CUTOFF_PX = 48;
export const BEAM_FALLOFF = 0.5;
export const FLAG = Object.freeze({ HELD: 1, RING: 2 });
export const KIND = Object.freeze({ BEAM: 0, FIGURE: 1 });
export const CORE_MAX_PX = 3.6;
// the engine's own record, one per line before packing (estimates and tests read it; the page never needs it)
export const W = Object.freeze({ X0: 0, Y0: 1, X1: 2, Y1: 3, R: 4, G: 5, B: 6, I: 7, WIDTH: 8, GLOW: 9, BLUR: 10,
  HEAT: 11, KIND: 12, HEAD: 13, FALLOFF: 14, FLAGS: 15, C1: 16, C2: 17, C3: 18, GROUP: 19 });
export const W_FLOATS = 20;

// The safety budget (spec 4.1 rule 3), on the share of a window and of the frame that CHANGES in one frame. Fast = a
// gate faster than 3 pulses per second, or presses faster than 3 a second. The frame share is held at 7.5 % for both,
// so that A5's pass line ("the frame stays at or below 8 %") holds with room for the estimate's error against a raster.
export const BUDGET = Object.freeze({
  fast: { window: 0.15, frame: 0.075, heads: 4, beams: 16, perHead: 12 },
  single: { window: 0.22, frame: 0.075, heads: 8, beams: 32, perHead: 24 },
});
// presses closer than this (ms) make the new hit a fast one (spec 4.1 rule 2: "faster than 3 per second")
export const FAST_PRESS_MS = 1000 / 3;
// The frame rules, in ms so other refresh rates follow: a pulse on at least 40 ms, a gap at least 30 ms, a step at
// least 83 ms (a faster step runs at half speed: a 16th roll above 180 BPM becomes an 8th roll).
export const FRAME_RULES = Object.freeze({ minOnMs: 40, minOffMs: 30, minStepMs: 83 });

// ============================================================================================================ seeds --
// splitmix32 seeds mulberry32 (both public-domain textbook generators); hash32 folds numbers and strings into a seed.
export function splitmix32(a) {
  return function next() {
    a = (a + 0x9e3779b9) | 0;
    let t = a ^ (a >>> 16);
    t = Math.imul(t, 0x21f0aaad);
    t ^= t >>> 15;
    t = Math.imul(t, 0x735a2d97);
    return (t ^ (t >>> 15)) >>> 0;
  };
}
export function mulberry32(a) {
  return function next() {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function strHash(s) {
  let h = 0x811c9dc5 | 0;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193);
  return h | 0;
}
export function hash32(...xs) {
  let h = 0x811c9dc5 | 0;
  for (const x of xs) {
    const v = typeof x === "number" ? (Number.isInteger(x) ? x | 0 : Math.floor(x * 1e6) | 0) : strHash(String(x));
    h = Math.imul(h ^ v, 0x01000193);
    h ^= h >>> 15; h = Math.imul(h, 0x2c1b3c6d); h ^= h >>> 12;
  }
  return h >>> 0;
}
export function makeRng(...seeds) { const sm = splitmix32(hash32(...seeds)); return mulberry32(sm()); }
function shuffled(arr, rng) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
  return a;
}

// A shuffled deck: each deal takes the next card; an empty deck reshuffles and never starts with the card it ended on.
// next(legal) deals the next LEGAL card and leaves the illegal ones for later in the same deck.
export class Deck {
  constructor(cards, rng) {
    this.cards = cards.slice();
    this.rng = rng;
    this.last = null;
    this.order = [];
    this.i = 0;
    this.shuffle();
  }
  shuffle() {
    const a = shuffled(this.cards, this.rng);
    if (a.length > 1 && a[0] === this.last) { const j = 1 + Math.floor(this.rng() * (a.length - 1)); const t = a[0]; a[0] = a[j]; a[j] = t; }
    this.order = a;
    this.i = 0;
  }
  // deal one of the next `look` legal cards: the one score() rates highest (ties keep deck order)
  next(legal = null, score = null, look = 1) {
    for (let pass = 0; pass < 2; pass++) {
      let best = -1, bestScore = -Infinity, seen = 0;
      for (let j = this.i; j < this.order.length && seen < look; j++) {
        const c = this.order[j];
        if (legal && !legal(c)) continue;
        seen++;
        const s = score ? score(c) : -seen;
        if (s > bestScore) { bestScore = s; best = j; }
      }
      if (best >= 0) {
        const c = this.order[best];
        this.order.splice(best, 1);
        this.order.splice(this.i, 0, c);
        this.i++;
        this.last = c;
        return c;
      }
      this.shuffle();
    }
    const c = this.cards.find((x) => !legal || legal(x));
    return c === undefined ? this.cards[0] : c;
  }
  first() { return this.cards[0]; }
}

// ============================================================================================================ heads --
// u = a fraction of the half-width (x = u * aspect / 2); y in frame heights. Bank A hangs along the top, Bank B stands
// along the bottom; each tower carries a low and a high head; HERO sits behind the hero point.
const BANK_U = [-0.84, -0.6, -0.36, -0.12, 0.12, 0.36, 0.6, 0.84];
const HEAD_DEFS = [
  ...BANK_U.map((u, i) => ({ name: `A${i + 1}`, bank: "A", row: "truss", u, y: 0.47 })),
  ...BANK_U.map((u, i) => ({ name: `B${i + 1}`, bank: "B", row: "floor", u, y: -0.47 })),
  { name: "SL1", bank: "S", row: "tower", u: -0.9, y: -0.12 },
  { name: "SL2", bank: "S", row: "tower", u: -0.9, y: 0.18 },
  { name: "SR1", bank: "S", row: "tower", u: 0.9, y: -0.12 },
  { name: "SR2", bank: "S", row: "tower", u: 0.9, y: 0.18 },
  { name: "HERO", bank: "H", row: "hero", u: 0, y: HERO.y },
];
const STAGE_ASPECT = 16 / 9;
export const HEADS = Object.freeze(HEAD_DEFS.map((d, i) => {
  const sx = d.u * STAGE_ASPECT / 2;
  const twin = HEAD_DEFS.findIndex((e) => Math.abs(e.u + d.u) < 1e-9 && Math.abs(e.y - d.y) < 1e-9);
  const flip = d.bank === "A" || d.bank === "B"
    ? HEAD_DEFS.findIndex((e) => e.bank === (d.bank === "A" ? "B" : "A") && Math.abs(e.u - d.u) < 1e-9) : i;
  const k = i % 8;
  const pad = d.bank === "A" ? 1 + (k >> 1) : d.bank === "B" ? 9 + (k >> 1) : d.bank === "H" ? 6 : d.u < 0 ? 5 : 8;
  return Object.freeze({ ...d, index: i, sx, side: d.u < -1e-9 ? -1 : d.u > 1e-9 ? 1 : 0, twin, flip,
    ring: Math.round(Math.abs(d.u) * 100), ang: Math.atan2(d.y - HERO.y, sx), pad });
}));
export const BANK_A = Object.freeze(HEADS.filter((h) => h.bank === "A").map((h) => h.index));
export const BANK_B = Object.freeze(HEADS.filter((h) => h.bank === "B").map((h) => h.index));
export const SIDE_HEADS = Object.freeze(HEADS.filter((h) => h.bank === "S").map((h) => h.index));
export const HERO_HEAD = HEADS.length - 1;
export const headIndex = (name) => HEADS.findIndex((h) => h.name === name);

export const BANK_MODES = Object.freeze({
  auto: "dealt per hit", A: "Bank A, the overhead truss", B: "Bank B, the floor", alternate: "successive hits switch banks",
  both: "both banks as one rig", call: "A fires, B answers on the off-beat", mirror: "each A head with its B twin",
});
const BANK_DEAL = ["A", "B", "alternate", "both", "call", "mirror"];

// ========================================================================================================= patterns --
const ALL = "all";
export const SECTIONS = Object.freeze(["any", "intro", "anti", "groove", "build", "drop", "climax", "break", "piano",
  "screech", "outro"]);
export const PATTERNS = Object.freeze({
  fan:      { label: "Fan Burst", help: "a fan opens from each head toward the hero (today's look)", sections: ALL },
  hot:      { label: "Hot Beam", help: "one tight beam per head, a fixed aim through the hero region", sections: ["intro", "anti", "screech", "piano", "break"] },
  scissors: { label: "Scissors", help: "mirrored pairs aim at mirrored foci that step on each beat", sections: ["groove", "anti", "drop", "climax"] },
  cross:    { label: "X Through the Hero", help: "the outermost heads cross at the hero", sections: ["drop", "climax"] },
  crown:    { label: "Crown", help: "even, mirrored beams rise from behind the hero", sections: ["drop", "climax", "break"] },
  star:     { label: "Starburst", help: "beams all round the hero, full count for a moment, then thinning", heroOnly: true, ungated: true },
  bloom:    { label: "Converge-Bloom", help: "every head aims at the hero, then the beams snap outward on the beat", heroOnly: true },
  sweep:    { label: "Scanner Sweep", help: "a fan sweeps side to side and eases to a stop on each beat", sections: ["drop", "climax", "groove"] },
  zigzag:   { label: "Zigzag", help: "a beam jumps between two angles on every gate step", sections: ["screech", "anti"] },
  tunnel:   { label: "Tunnel", help: "beams from a ring of heads meet round the hero, and the ring spins", sections: ["build"] },
  wave:     { label: "Phase Wave", help: "every head runs the same sweep, each offset by 1/N of a 4-beat cycle", sections: ["break", "piano", "climax"] },
  rain:     { label: "Rain", help: "vertical beams: down from the truss, up from the floor", sections: ["break", "outro", "piano"] },
  cage:     { label: "Cage", help: "two families of parallel beams cross; the cage turns on bar lines", sections: ["anti"] },
  ladder:   { label: "Ladder", help: "horizontal rungs from the towers stack one per step and clear on the bar", sections: ["build"] },
  chase:    { label: "Chase", help: "one beam walks from head to head, a step per pulse (domino)", sections: ["drop", "climax", "groove", "build"] },
  cone:     { label: "Cone", help: "beams from a head to a spinning ellipse round the hero: a 3D cone in haze", sections: ["drop", "climax", "build"] },
  figure:   { label: "Figure", help: "laser line art round the hero, morphing into the next figure on each beat", sections: ALL },
});
export const PATTERN_IDS = Object.freeze(Object.keys(PATTERNS));
const HERO_PATTERNS = ["crown", "star", "bloom"];
const PATTERN_CODE = Object.fromEntries(PATTERN_IDS.map((p, i) => [p, i + 1]));
const HOT_AIMS = [-0.2, -0.11, -0.04, 0.04, 0.11, 0.2];
const FOCI = [[-0.22, 0.14], [0.18, -0.12], [-0.08, -0.2], [0.26, 0.2], [0.02, 0.28], [-0.3, -0.04]];
const CAGE_TILT = [0.5, 0.74, 0.36, 0.62];
// Patterns whose picture holds still from pulse to pulse in a fast gate (the whole hit is frozen at its first onset), so
// their halo may be held lit through the gaps. Every other pattern moves between pulses (a spin, a flip, a sweep, a
// step of the foci): its halo goes off with its core, so each pulse is one clean on/off of its own light.
const STILL_IN_FAST = new Set(["fan", "cross", "crown", "rain", "ladder", "chase"]);
// patterns whose fans follow the hit's beam count (the others fire one or two beams per head)
const BEAM_SCALED = new Set(["fan", "sweep", "cone", "bloom", "scissors"]);
// patterns that draw the same heads whichever step (group) a pulse lights: the hero's own, the rig-wide cross and wave,
// the towers' ladder
const GROUP_FREE = new Set(["crown", "star", "figure", "cross", "wave", "ladder"]);
// patterns that fire a fixed one or two beams per head; the fit's last structural lever takes them to one (beamCap)
const PAIR_BEAMS = new Set(["cross", "zigzag", "scissors"]);
// [beats after which a pattern's picture repeats, beats between its changes (0: it moves every step)], as _pattern
// draws it from the beat position: the fit probes a loop at every such grid point over the cycle. (Patterns missing
// here hold still from step to step, or turn with the pulse count; the figure is probed beat by beat on its own terms.)
const PATTERN_CYCLE = Object.freeze({ wave: [4], sweep: [2], tunnel: [4], cone: [2], rain: [4], scissors: [6], cage: [16, 4],
  crown: [8], star: [8], bloom: [1] });
// a figure's level and blur band multipliers before the fit lowers them (see _fitHit)
const SHAPE_MUL_ONE = Object.freeze({ lvl: 1, blur: 1 });
// the lowest level the per-frame check may dim a hit to (see _giveWay)
const DIM_FLOOR = 0.03;
// the lowest light the fit dims a hit to once every structural lever (beams, heads, rungs, crown) is spent
const PEAK_FLOOR = 0.12;

// =========================================================================================================== orders --
export const ORDERS = Object.freeze({
  one: "one head, dealt (later pulses deal more)", lr: "chase left to right", rl: "chase right to left",
  alt: "alternate left and right", pairs: "mirrored pairs together", centreout: "centre-out: rings radiate from the hero",
  outsidein: "outside-in", oddeven: "odd heads, then even heads", rotor: "round the hero by angle",
  shuffle: "a seeded shuffle", rows: "rows: floor, towers, truss", all: "all heads at once",
});
export const ORDER_IDS = Object.freeze(Object.keys(ORDERS));

// ===================================================================================================== colour modes --
export const COLOUR_MODES = Object.freeze({
  mono: "one colour with a white core", split: "beams alternate the two laser colours",
  gradient: "the first colour to the second across the fan (OKLab, short arc)", hotcore: "a white centre beam, coloured sides",
  halves: "left heads the first colour, right heads the second", chase: "the second colour walks one head or beam per pulse",
  flip: "pulse k takes the theme's flicker roles", trinity: "the three pulses take the theme's triple roles (A, B, white)",
  headgrad: "a gradient across the rig by head position", burst: "a multi-colour burst: the theme's burst roles round the fan",
  barswap: "the sides swap colours on each bar line",
});
export const COLOUR_IDS = Object.freeze(Object.keys(COLOUR_MODES));
const TWO_COLOUR = new Set(["split", "gradient", "halves", "chase", "flip", "trinity", "headgrad", "burst", "barswap"]);
const BLENDING = new Set(["split", "gradient", "headgrad"]);      // never on split-only themes (their blends grey out)

// ============================================================================================================ gates --
// A short gate is a list of pulses {at, len} in beats from its anchor, then a tail on the last pulse. A loop repeats on a
// grid step until it ends (a tap runs `span` beats; a hold runs until release; a rapid roll until half a beat after the
// last press). act: on (default), tick (a thin flick), pluck (the beams start to ring), smear (the ring smears into
// trails), flash (every head of the hit, white-hot; emits a "flash" event), ramp (rises x^2 through the step).
const P = (at, len, act = "on") => Object.freeze({ at, len, act });
export const GATES = Object.freeze({
  single:    { label: "Single", kind: "short", grid: 1 / 4, pulses: [P(0, 1 / 8)], tail: 1 / 4 },
  onetwo:    { label: "One-Two Flicker", kind: "short", grid: 1 / 4, pulses: [P(0, 1 / 8), P(1 / 4, 1 / 8)], tail: 1 / 4 },
  triple:    { label: "Triple Strobe", kind: "short", grid: 1 / 4, pulses: [P(0, 1 / 8), P(1 / 4, 1 / 8), P(1 / 2, 1 / 8)], tail: 1 / 2 },
  triplet:   { label: "Triplet Triple", kind: "short", grid: 1 / 3, pulses: [P(0, 1 / 6), P(1 / 3, 1 / 6), P(2 / 3, 1 / 6)], tail: 1 / 2 },
  bar:       { label: "Bar Marker", kind: "short", grid: 1, pulses: [P(0, 1 / 8)], tail: 1 },
  tttou:     { label: "t t tou blur blur flash", kind: "short", grid: 1 / 4, tail: 1 / 2,
    pulses: [P(0, 1 / 8, "tick"), P(1 / 4, 1 / 8, "tick"), P(1 / 2, 1 / 2, "pluck"), P(1, 3 / 8, "smear"), P(3 / 2, 3 / 8, "smear"), P(2, 1 / 8, "flash")] },
  roll8:     { label: "1/8 Roll", kind: "loop", step: 1 / 2, len: 1 / 4, span: 1 },
  roll16:    { label: "1/16 Roll", kind: "loop", step: 1 / 4, len: 1 / 8, span: 1 },
  stutter:   { label: "Stutter", kind: "loop", step: 1 / 4, len: 1 / 8, span: 2, masks: ["xx.xx.x.", "x.xxx.x.", "xxx.x.x.", "x.x.xx.x"] },
  military:  { label: "Military Roll", kind: "loop", step: 1 / 4, len: 1 / 8, span: 4,
    masks: ["x.xxx.x.xx.xx...", "xx.x.xx.x.xx..x.", "x..xx.x.x..xxxx.", "x.x.xx..x.xxx.x."] },
  pushpull:  { label: "Push-Pull", kind: "loop", step: 1 / 2, len: 1 / 4, span: 2, sides: true },
  revbass:   { label: "Reverse-Bass Gate", kind: "loop", step: 1, offset: 1 / 2, len: 3 / 8, span: 2 },
  doubling:  { label: "Doubling Roll", kind: "loop", stages: [1, 1 / 2, 1 / 4], stageBeats: 4, len: 1 / 8, span: 12 },
  stopshort: { label: "Stop-Short", kind: "loop", step: 1 / 4, len: 1 / 8, span: 4, cutAt: 2.5 },
  inhale:    { label: "Inhale", kind: "loop", step: 1, len: 1, span: 1, ramp: true },
});
export const GATE_IDS = Object.freeze(Object.keys(GATES));
const ACT = Object.freeze({ on: { lvl: 1, w: 1, heat: 1 }, tick: { lvl: 0.8, w: 0.6, heat: 0.8 }, pluck: { lvl: 1, w: 1, heat: 1.1 },
  smear: { lvl: 0.55, w: 1, heat: 0.6 }, flash: { lvl: 1, w: 1, heat: 1.6 }, ramp: { lvl: 1, w: 1, heat: 1 } });
const STEP_UP = { single: "onetwo", onetwo: "triple", triple: "triplet", triplet: "triplet", bar: "single" };

// The retrigger edges, in beats since the previous press. Human taps are never exact, so no edge sits ON a musical
// division: each sits halfway (geometrically) between the divisions either side of it -- 16ths | 8ths at sqrt(1/8),
// 8ths | beats at sqrt(1/2), beats | half bars at sqrt(2), bars | two bars at sqrt(32). An eighth-note stream tapped with
// 20 ms of jitter at 180 BPM sits 3.4 standard deviations from its nearest edge. A rapid roll runs on rollHold beats past
// each press, longer than the rapid edge, so the next press of the stream always finds it running.
export const RETRIGGER = Object.freeze({ roll16: Math.sqrt(1 / 8), rapid: Math.SQRT1_2, flicker: Math.SQRT2,
  escalate: Math.sqrt(32), rollHold: 3 / 4 });
export const TIERS = Object.freeze({
  burst: "more than a bar since the last press (over 5.7 beats): one varied burst (velocity picks the gate)",
  escalate: "within a bar (1.4 to 5.7 beats): one tier up (more heads, a second colour, the gate steps up)",
  hero: "the third press within a bar: a crown, starburst or bloom from the hero (at most 1 in 6 hits)",
  flicker: "within a beat (0.7 to 1.4 beats): a one-two flicker on alternating heads",
  rapid: "an eighth note or faster (under 0.7 beats): a strobe roll locked to the grid (8ths; 16ths under 0.35 beats)",
  held: "held for half a beat: a continuous gate until release (doubling roll; push-pull on the drop)",
  phrase: "\"t t tou blur blur flash\": tick, tick, pluck-and-ring, smear, smear, flash",
});
export const TIER_LED = Object.freeze({ 1: 0.6, 2: 0.8, 3: 1.0 });

// ========================================================================================================== colours --
// the sRGB transfer pair, from the constants of IEC 61966-2-1
const SRGB_OFFSET = 0.055, SRGB_EXP = 2.4, SRGB_SLOPE = 12.92, SRGB_KNEE_LIN = 0.0031308, SRGB_KNEE_ENC = 0.04045;
const srgbToLin = (v) => (v > SRGB_KNEE_ENC ? ((v + SRGB_OFFSET) / (1 + SRGB_OFFSET)) ** SRGB_EXP : v / SRGB_SLOPE);
const linToSrgb = (v) => {
  const x = clamp01(v);
  return x > SRGB_KNEE_LIN ? (1 + SRGB_OFFSET) * x ** (1 / SRGB_EXP) - SRGB_OFFSET : x * SRGB_SLOPE;
};
export function hexToLin(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return [1, 1, 1];
  const v = parseInt(m[1], 16);
  return [srgbToLin(((v >> 16) & 255) / 255), srgbToLin(((v >> 8) & 255) / 255), srgbToLin((v & 255) / 255)];
}
// Saturated red (the theme library's rule): R/(R+G+B) >= 0.8 on encoded OR linear values. Such colours are held, never
// flashed, and never emitted by a laser.
export function isSaturatedRed(lin) {
  const s = lin[0] + lin[1] + lin[2];
  if (s > 1e-6 && lin[0] / s >= 0.8) return true;
  const e = [linToSrgb(lin[0]), linToSrgb(lin[1]), linToSrgb(lin[2])];
  const se = e[0] + e[1] + e[2];
  return se > 1e-6 && e[0] / se >= 0.8;
}
function linToOklab(c) {
  const l = Math.cbrt(0.4122214708 * c[0] + 0.5363325363 * c[1] + 0.0514459929 * c[2]);
  const m = Math.cbrt(0.2119034982 * c[0] + 0.6806995451 * c[1] + 0.1073969566 * c[2]);
  const s = Math.cbrt(0.0883024619 * c[0] + 0.2817188376 * c[1] + 0.6299787005 * c[2]);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}
function oklabToLin(o) {
  const l = (o[0] + 0.3963377774 * o[1] + 0.2158037573 * o[2]) ** 3;
  const m = (o[0] - 0.1055613458 * o[1] - 0.0638541728 * o[2]) ** 3;
  const s = (o[0] - 0.0894841775 * o[1] - 1.291485548 * o[2]) ** 3;
  return [clamp01(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    clamp01(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    clamp01(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)];
}
export function hueGapDeg(a, b) {
  const A = linToOklab(a), B = linToOklab(b);
  if (Math.hypot(A[1], A[2]) < 0.02 || Math.hypot(B[1], B[2]) < 0.02) return 0;     // an achromatic end: no hue gap
  let d = Math.abs(Math.atan2(A[2], A[1]) - Math.atan2(B[2], B[1])) * 180 / Math.PI;
  return d > 180 ? 360 - d : d;
}
function lerpOk(a, b, t, out) {
  const A = linToOklab(a), B = linToOklab(b);
  const c = oklabToLin([A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t]);
  out[0] = c[0]; out[1] = c[1]; out[2] = c[2];
  return out;
}

// Night Sea, from the v2 theme library (the spec's JSON): the default until the page hands over its theme.
export const DEFAULT_THEME = Object.freeze({ id: "night-sea", name: "Night Sea", A: "#0155bc", B: "#1cbde6", W: "#e8f8ff",
  beam: { A: "#1373f1", B: "#25bde5" }, lasers: ["B"], strobe: { triple: ["B", "B", "W"], flicker: ["A", "B"] },
  burst: ["A", "B", "W"], held: [], split_only: false });

// A theme from the library ({A, B, W, beam, lasers, strobe, burst, held, split_only}) or {L1, L2, W} hexes, resolved to
// the linear colours a laser may emit. Held roles and saturated reds resolve to white.
export function themeColours(theme) {
  const t = theme || DEFAULT_THEME;
  const held = new Set(t.held || []);
  let W = t.W && !held.has("W") ? hexToLin(t.W) : [1, 1, 1];
  if (isSaturatedRed(W)) W = [1, 1, 1];
  const roleHex = (r) => (r === "white" ? "#ffffff" : (t.beam && t.beam[r]) || t[r] || null);
  const res = (r) => {
    if (r === "W") return W;
    if (held.has(r)) return W;
    const h = roleHex(r);
    if (!h) return W;
    const c = hexToLin(h);
    return isSaturatedRed(c) ? W : c;
  };
  let L1, L2;
  if (t.L1) { L1 = hexToLin(t.L1); L2 = t.L2 ? hexToLin(t.L2) : W; if (isSaturatedRed(L1)) L1 = W; if (isSaturatedRed(L2)) L2 = W; }
  else {
    const lasers = (t.lasers || ["A"]).filter((r) => !held.has(r));
    L1 = lasers.length ? res(lasers[0]) : W;
    L2 = lasers.length > 1 ? res(lasers[1]) : W;
  }
  const list = (roles, fb) => (Array.isArray(roles) && roles.length ? roles.map(res) : fb);
  const strobe = t.strobe || {};
  const triple = list(strobe.triple, [L1, L1, W]), flicker = list(strobe.flicker, [L1, L2]), burst = list(t.burst, [L1, L2, W]);
  // the brightest of each cycle (by luminance, then by its brightest channel): what the fit draws a loop's pulse in
  const Y = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] + 1e-3 * Math.max(c[0], c[1], c[2]);
  const top = (cs) => cs.reduce((a, c) => (Y(c) > Y(a) ? c : a), cs[0]);
  return Object.freeze({ id: t.id || "custom", L1, L2, W, triple, flicker, burst, splitOnly: !!t.split_only,
    hueGap: hueGapDeg(L1, L2), top: Object.freeze({ pair: top([L1, L2]), triple: top(triple), flicker: top(flicker), burst: top(burst) }) });
}

// ========================================================================================================== Vibrate --
// The beams ring like plucked strings: three standing-wave modes sin(n pi u) with nodes at both ends (the head and the
// beam's far end), each decaying faster than the one below it, the overtones slightly sharp (stiff strings are
// inharmonic). Learned from the piano's string light (arsenal/web/piano/instruments/concert-grand.js: amplitude follows
// a decaying body, nodes stay put at both ends, the blur dies fast once the string is damped) but written here from
// scratch. Amplitudes and blur are px at 1080 lines.
export const VIB = Object.freeze({
  AMP_PX: 12,          // mode-1 peak displacement at full velocity
  MAX_PX: 18,          // re-plucks add up to this
  MODES: [1, 0.45, 0.25],
  TAU1_S: 0.55,        // mode-1 ring; mode n rings TAU1 / n^MODE_EXP
  MODE_EXP: 0.8,
  F1_HZ: 5.2,          // the visual fundamental (the piano's strings breathe at 3.1-9.5 Hz)
  INHARM: 0.004,       // f_n = n f1 (1 + INHARM n^2)
  TAU_OFF_S: 0.07,     // Vibrate switched off: the ring is damped this fast
  ATTACK_S: 0.035,     // a pluck's attack: the new ring rises, and the ring it replaces fades, with this time constant (an
                       // instant re-pluck made the string jump in one frame, a flash of its whole band)
  BLUR_GAIN: 0.6,      // blur band half-width = BLUR_GAIN * the local envelope
  BLUR_MAX_PX: 8,
  BLUR_FAST_PX: 4,     // the cap while a fast gate runs (the band must not strobe much area)
  SMEAR_GAIN: 2.2,     // the phrase's "blur blur": the band widens this much
});
// the mode amplitudes (px) of a pluck of `amp` px, ageS seconds after it, with Vibrate off for offS seconds (or null)
// how far a pluck's ring has risen ageS seconds after it (the old ring fades by the rest)
export function ringAttack(ageS) { return ageS <= 0 ? 0 : 1 - Math.exp(-ageS / VIB.ATTACK_S); }
export function vibModes(ageS, amp, offS = null) {
  const off = offS === null ? 1 : Math.exp(-Math.max(0, offS) / VIB.TAU_OFF_S);
  return VIB.MODES.map((a, i) => a * amp * Math.exp(-Math.max(0, ageS) / (VIB.TAU1_S / Math.pow(i + 1, VIB.MODE_EXP))) * off);
}
// the transverse displacement (px) at u in [0, 1] along the string
export function vibDisplacement(u, ageS, amp, phase = 0, offS = null) {
  const m = vibModes(ageS, amp, offS);
  let d = 0;
  for (let i = 0; i < m.length; i++) {
    const n = i + 1, f = VIB.F1_HZ * n * (1 + VIB.INHARM * n * n);
    d += m[i] * Math.sin(n * Math.PI * u) * Math.cos(TAU * f * ageS + phase + 1.3 * n);
  }
  return d;
}
// the envelope (px): how far the string swings at u, the motion-blur band
export function vibEnvelope(u, ageS, amp, offS = null) {
  const m = vibModes(ageS, amp, offS);
  let e = 0;
  for (let i = 0; i < m.length; i++) e += m[i] * Math.abs(Math.sin((i + 1) * Math.PI * u));
  return e;
}

// =========================================================================================================== shapes --
export const SHAPES = Object.freeze(["circle", "triangle", "square", "star", "spiral", "lissajous", "tunnel",
  "tetrahedron", "cube", "octahedron", "torusknot"]);
export const SHAPE_SEGS = 96;
const SOLIDS = {
  tetrahedron: { v: [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]].map((p) => p.map((c) => c / Math.sqrt(3))),
    e: [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]] },
  cube: { v: [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]].map((p) => p.map((c) => c / Math.sqrt(3))),
    e: [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]] },
  octahedron: { v: [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
    e: [[0, 2], [0, 3], [0, 4], [0, 5], [1, 2], [1, 3], [1, 4], [1, 5], [2, 4], [4, 3], [3, 5], [5, 2]] },
};
const PERSPECTIVE = 3;       // camera distance in figure radii
function rot3(p, ry, rx) {
  const cy = Math.cos(ry), sy = Math.sin(ry), cx = Math.cos(rx), sx = Math.sin(rx);
  const x = p[0] * cy + p[2] * sy, z0 = -p[0] * sy + p[2] * cy;
  return [x, p[1] * cx - z0 * sx, p[1] * sx + z0 * cx];
}
const project = (p) => { const k = PERSPECTIVE / (PERSPECTIVE + p[2]); return [p[0] * k, p[1] * k]; };
function polygon(n, r0 = 1, r1 = null, rot = Math.PI / 2) {
  const pts = [];
  const m = r1 === null ? n : 2 * n;
  for (let i = 0; i <= m; i++) {
    const r = r1 === null || i % 2 === 0 ? r0 : r1;
    const a = rot + TAU * i / m;
    pts.push([r * Math.cos(a), r * Math.sin(a)]);
  }
  return pts;
}
// A figure's strokes (polylines in unit radius) at beat position pos. 3D solids turn one revolution every 8 beats.
export function shapeStrokes(name, pos = 0) {
  const ry = TAU * pos / 8, rx = 0.45 + 0.2 * Math.sin(TAU * pos / 16);
  switch (name) {
    case "circle": return [polygon(48, 1, null, 0)];
    case "triangle": return [polygon(3)];
    case "square": return [polygon(4, 1, null, Math.PI / 4)];
    case "star": return [polygon(5, 1, 0.42)];
    case "spiral": {
      const pts = [];
      for (let i = 0; i <= 96; i++) { const s = i / 96, a = TAU * 3 * s + pos * Math.PI / 2; pts.push([s * Math.cos(a), s * Math.sin(a)]); }
      return [pts];
    }
    case "lissajous": {
      const pts = [], d = Math.PI / 2 * (1 + 0.25 * pos);
      for (let i = 0; i <= 120; i++) { const s = TAU * i / 120; pts.push([Math.sin(3 * s + d), Math.sin(2 * s)]); }
      return [pts];
    }
    case "tunnel": {
      const out = [];
      for (let r = 0; r < 4; r++) {
        const z = 3 * frac(r / 4 + pos / 4), k = PERSPECTIVE / (PERSPECTIVE + z);
        out.push(polygon(24, k, null, pos * 0.3 + r * 0.4));
      }
      return out;
    }
    case "torusknot": {
      const pts = [];
      for (let i = 0; i <= 120; i++) {
        const s = TAU * i / 120, r = (Math.cos(3 * s) + 2) / 3;
        pts.push(project(rot3([r * Math.cos(2 * s), r * Math.sin(2 * s), -Math.sin(3 * s) / 3], ry, rx)));
      }
      return [pts];
    }
    default: {
      const S = SOLIDS[name] || SOLIDS.cube;
      const v = S.v.map((p) => project(rot3(p, ry, rx)));
      return S.e.map(([a, b]) => [v[a], v[b]]);
    }
  }
}
// The figure resampled to exactly n segments (x0 y0 x1 y1 each), centred at (cx, cy) with radius R. Every figure has the
// same segment count, so two figures morph by lerping segment i into segment i.
export function shapeSegments(name, { pos = 0, R = 0.2, cx = HERO.x, cy = HERO.y, n = SHAPE_SEGS, out = null } = {}) {
  const strokes = shapeStrokes(name, pos);
  const lens = strokes.map((s) => { let L = 0; for (let i = 1; i < s.length; i++) L += hyp(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]); return L; });
  const total = lens.reduce((a, b) => a + b, 0) || 1;
  const counts = lens.map((L) => Math.max(1, Math.round(n * L / total)));
  let diff = n - counts.reduce((a, b) => a + b, 0);
  for (let guard = 0; diff !== 0 && guard < 10 * n; guard++) {
    let k = 0;
    for (let i = 1; i < counts.length; i++) if (diff > 0 ? lens[i] / counts[i] > lens[k] / counts[k] : (counts[i] > 1 && lens[i] / counts[i] < lens[k] / counts[k]) || counts[k] <= 1) k = i;
    if (diff < 0 && counts[k] <= 1) break;
    counts[k] += diff > 0 ? 1 : -1; diff += diff > 0 ? -1 : 1;
  }
  const o = out || new Float32Array(n * 4);
  let w = 0;
  // walk each stroke once: the points at arc lengths 0, L/m, 2L/m ... L, read off as the walk passes them
  const pts = [];
  for (let k = 0; k < strokes.length && w < n; k++) {
    const st = strokes[k], m = counts[k], L = lens[k];
    pts.length = 0;
    let i = 1, acc = 0, l = st.length > 1 ? hyp(st[1][0] - st[0][0], st[1][1] - st[0][1]) : 0;
    for (let j = 0; j <= m; j++) {
      const d = L * j / m;
      while (i < st.length - 1 && acc + l < d - 1e-12) { acc += l; i++; l = hyp(st[i][0] - st[i - 1][0], st[i][1] - st[i - 1][1]); }
      const u = l > 0 ? clamp01((d - acc) / l) : 0, a = st[Math.max(0, i - 1)], b = st[Math.min(i, st.length - 1)];
      pts.push(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u);
    }
    for (let j = 0; j < m && w < n; j++, w++) {
      o[w * 4] = cx + pts[2 * j] * R; o[w * 4 + 1] = cy + pts[2 * j + 1] * R;
      o[w * 4 + 2] = cx + pts[2 * j + 2] * R; o[w * 4 + 3] = cy + pts[2 * j + 3] * R;
    }
  }
  for (; w < n; w++) { o[w * 4] = o[w * 4 + 2] = cx; o[w * 4 + 1] = o[w * 4 + 3] = cy; }
  return o;
}

// ==================================================================================================== area estimate --
// WCAG 2.3.1 measures CHANGE: a pixel flashes between two frames when its relative luminance moves by 0.1 or more (the
// darker state below 0.8), and a flash over a quarter of any one-third-frame window is a general flash. So the budget
// holds the share of each window that CHANGES from one frame to the next, not the share that is lit: a moving beam
// changes about twice its lit area (where it was and where it is), and a core strobing under a held halo changes only
// the core.
//
// The estimate works on a 72 x 36 grid of small cells (about 27 x 30 px at 1080). Each line is sampled every half cell
// (a ringing beam along its bend); each sample deposits its counted band into its cell; each cell is capped at full, so
// beams that overlap count once. Windows are a third of the frame per side, slid over EVERY cell position, so the worst
// window anywhere is found, not only the 25 at half-window steps.
//
// The counted band of a line at a point (px at 1080), from the overlay's light model: the core gives I * its hot-core
// luminance over its width (+1 px of anti-aliasing each side), spread over width + 2 blur when it has a blur band; the
// halo gives glow * Y * 0.5 * L(d), L(d) = 1 / (1 + (d / 4 px)^2) (the overlay's Lorentzian at its 16 px scale), so on its
// own it reaches 0.1 out to d = 4 sqrt(5 glow Y - 1) px each side; both fade along a beam. LIT band: where the light is
// 0.1 or more. CHANGED band, matching each line to itself in the frame before by its key (hit, head, beam):
//   - a line that appears or vanishes: its lit band, where it is or where it was;
//   - a line that stays put: the band where its light moves by 0.1 or more (the same formulas on the change of its core
//     and halo levels);
//   - a line that moves by delta px: a strip delta wide at each edge whose light steps by 0.1 or more (the core's or its
//     blur band's two, the halo's two), plus the level change, and never more than the union of its old and new bands
//     (a pixel under 0.1 in both frames cannot change by 0.1); bands that no longer overlap count where each is.
const GX = 72, GY = 36, WIN_X = GX / 3, WIN_Y = GY / 3;
const LIT = new Float64Array(GX * GY), CHG = new Float64Array(GX * GY), SAT = new Float64Array((GX + 1) * (GY + 1));
const SEEN = new Uint8Array(MAX_SEGMENTS);
const PT = { x: 0, y: 0 }, PQ = { x: 0, y: 0 };

// the hot core's luminance (the overlay's hotCore whitening by heat) and the tint's
function hotLuma(Wa, o) {
  const r = Wa[o + W.R], g = Wa[o + W.G], b = Wa[o + W.B], h = Wa[o + W.HEAT], kw = h * h / (1 + h * h);
  return (1 - kw) * (0.2126 * r + 0.7152 * g + 0.0722 * b) + kw * Math.max(r, g, b);
}
const tintLuma = (Wa, o) => 0.2126 * Wa[o + W.R] + 0.7152 * Wa[o + W.G] + 0.0722 * Wa[o + W.B];
// the light at a line's centre: the core's level spread over its blur band, plus the halo's peak there
const coreLevel = (I, Yh, glowY, width, blur) => I * Yh * width / Math.max(1, width + 2 * blur) + 0.5 * glowY;
// the band (px at 1080) where a line's light is 0.1 or more
function bandPx(core, glowY, width, blur) {
  let w = core >= 0.1 ? width + 2 * blur + 2 : 0;
  const k = 5 * glowY;
  if (k > 1) w = Math.max(w, 8 * Math.sqrt(k - 1));
  return w;
}
// the point at u along record o into P (a ringing beam bent by its coefficients, along its left normal); returns the
// blur band there (a ringing beam's band follows sin(pi u))
function recPoint(Wa, o, u, len, P) {
  const x0 = Wa[o], y0 = Wa[o + 1], dx = Wa[o + 2] - x0, dy = Wa[o + 3] - y0;
  P.x = x0 + dx * u; P.y = y0 + dy * u;
  if (Wa[o + W.FLAGS] & FLAG.RING) {
    const s = Math.PI * u;
    const d = (Wa[o + W.C1] * Math.sin(s) + Wa[o + W.C2] * Math.sin(2 * s) + Wa[o + W.C3] * Math.sin(3 * s)) / REF_PX / (len || 1);
    P.x -= dy * d; P.y += dx * d;
    return Wa[o + W.BLUR] * Math.sin(s);
  }
  return Wa[o + W.BLUR];
}
// Checked frame by frame against an additive raster of the overlay's light model (960 x 540, windows slid in quarter
// steps), the bare bands read up to 14 % low on the worst frames (overlapping halos add up past each band's own edge,
// and anti-aliased edges spill), so every band counts EST_SCALE wide: the estimate errs high, never low.
export const EST_SCALE = 1.15;
function deposit(cells, x, y, area, aspect) {
  const hx = aspect / 2;
  if (!(x >= -hx && x <= hx && y >= -0.5 && y <= 0.5)) return;
  const cx = Math.min(GX - 1, Math.floor((x + hx) * GX / aspect)), cy = Math.min(GY - 1, Math.floor((y + 0.5) * GY));
  cells[cy * GX + cx] += area * EST_SCALE;
}
// cap each cell at full, then the frame's share and the worst window's (every position, via a summed-area table)
function windowShares(cells, aspect, out, keyW, keyF) {
  const cellA = aspect / GX / GY;
  let total = 0;
  for (let c = 0; c < cells.length; c++) { if (cells[c] > cellA) cells[c] = cellA; total += cells[c]; }
  for (let y = 0; y < GY; y++) {
    let row = 0;
    for (let x = 0; x < GX; x++) { row += cells[y * GX + x]; SAT[(y + 1) * (GX + 1) + x + 1] = SAT[y * (GX + 1) + x + 1] + row; }
  }
  let worst = 0;
  for (let y = 0; y + WIN_Y <= GY; y++) for (let x = 0; x + WIN_X <= GX; x++) {
    const s = SAT[(y + WIN_Y) * (GX + 1) + x + WIN_X] - SAT[y * (GX + 1) + x + WIN_X] - SAT[(y + WIN_Y) * (GX + 1) + x] + SAT[y * (GX + 1) + x];
    if (s > worst) worst = s;
  }
  out[keyF] = total / aspect;
  out[keyW] = worst / (WIN_X * WIN_Y * cellA);
}
// The share of a frame's lit lines (n records of Wa) whose 0.1 band is set by their blur band: the core spread over
// width + 2 blur still reaches 0.1, and that band is wider than the halo's. Halving such a line's blur narrows its band;
// dimming it does not, until its core drops under 0.1 at once. (Read at the line's brightest end.)
function blurBoundShare(Wa, n) {
  let lit = 0, bound = 0;
  for (let i = 0; i < n; i++) {
    const o = i * W_FLOATS, I = Wa[o + W.I], glow = Wa[o + W.GLOW];
    if (I < 0.002 && glow < 0.002) continue;
    lit++;
    const blur = Wa[o + W.BLUR];
    if (blur < 0.5) continue;
    const width = Wa[o + W.WIDTH], gY = glow * tintLuma(Wa, o), k = 5 * gY;
    if (coreLevel(I, hotLuma(Wa, o), gY, width, blur) >= 0.1 && width + 2 * blur + 2 > (k > 1 ? 8 * Math.sqrt(k - 1) : 0)) bound++;
  }
  return lit ? bound / lit : 0;
}
// one line's lit band into the cells; returns the area deposited
function depositLine(cells, Wa, o, step, aspect) {
  const I = Wa[o + W.I], glow = Wa[o + W.GLOW];
  if (I < 0.002 && glow < 0.002) return 0;
  const len = hyp(Wa[o + 2] - Wa[o], Wa[o + 3] - Wa[o + 1]);
  if (!(len > 0)) return 0;
  const m = Math.max(1, Math.ceil(len / step)), fall = Wa[o + W.FALLOFF], width = Wa[o + W.WIDTH];
  const Yh = hotLuma(Wa, o), Yt = tintLuma(Wa, o), da = len / m / REF_PX, fk = Math.exp(-fall * len / m);
  let total = 0, f = Math.exp(-fall * len * 0.5 / m);
  for (let j = 0; j < m; j++, f *= fk) {
    const blur = recPoint(Wa, o, (j + 0.5) / m, len, PT);
    const gY = glow * Yt * f, w = bandPx(coreLevel(I * f, Yh, gY, width, blur), gY, width, blur);
    if (w > 0) { const a = da * w; deposit(cells, PT.x, PT.y, a, aspect); total += a; }
  }
  return total;
}
// one line seen in both frames: what changed between them; res.moved = it moved by half a pixel or more
function depositPair(cells, Pa, po, Ca, co, step, aspect, res) {
  const lenC = hyp(Ca[co + 2] - Ca[co], Ca[co + 3] - Ca[co + 1]), lenP = hyp(Pa[po + 2] - Pa[po], Pa[po + 3] - Pa[po + 1]);
  res.moved = false;
  if (!(lenC > 0) && !(lenP > 0)) return 0;
  const m = Math.max(1, Math.ceil(Math.max(lenC, lenP) / step));
  const Ic = Ca[co + W.I], Ip = Pa[po + W.I], gc = Ca[co + W.GLOW], gp = Pa[po + W.GLOW];
  const YhC = hotLuma(Ca, co), YhP = hotLuma(Pa, po), YtC = tintLuma(Ca, co), YtP = tintLuma(Pa, po);
  const wC = Ca[co + W.WIDTH], wP = Pa[po + W.WIDTH], fallC = Ca[co + W.FALLOFF], fallP = Pa[po + W.FALLOFF];
  const aC = lenC / m / REF_PX, aP = lenP / m / REF_PX, kC = Math.exp(-fallC * lenC / m), kP = Math.exp(-fallP * lenP / m);
  let total = 0, maxD = 0, fc = Math.exp(-fallC * lenC * 0.5 / m), fp = Math.exp(-fallP * lenP * 0.5 / m);
  for (let j = 0; j < m; j++, fc *= kC, fp *= kP) {
    const u = (j + 0.5) / m;
    const bc = recPoint(Ca, co, u, lenC, PT), bp = recPoint(Pa, po, u, lenP, PQ);
    const gyc = gc * YtC * fc, gyp = gp * YtP * fp;
    const corec = coreLevel(Ic * fc, YhC, gyc, wC, bc), corep = coreLevel(Ip * fp, YhP, gyp, wP, bp);
    const bandC = bandPx(corec, gyc, wC, bc), bandP = bandPx(corep, gyp, wP, bp);
    // the band where the light moves by 0.1 or more if the line stood still
    let dB = Math.abs(corec - corep) >= 0.1 ? Math.max(wC + 2 * bc, wP + 2 * bp) + 2 : 0;
    const k = 5 * Math.abs(gyc - gyp);
    if (k > 1) dB = Math.max(dB, 8 * Math.sqrt(k - 1));
    const d = hyp(PT.x - PQ.x, PT.y - PQ.y) * REF_PX;
    if (d > maxD) maxD = d;
    // a shift by d px changes a strip d wide at each edge whose light steps by 0.1 or more: the core's (or its blur
    // band's) two edges when it is that bright, the halo's two when it reaches 0.1 on its own
    const edges = Math.max((corec >= 0.1 ? 2 : 0) + (5 * gyc > 1 ? 2 : 0), (corep >= 0.1 ? 2 : 0) + (5 * gyp > 1 ? 2 : 0));
    // ... and never more than the union of its old and new bands (a pixel under 0.1 in both frames cannot change by 0.1)
    const apart = d >= (bandC + bandP) / 2, union = apart ? bandC + bandP : Math.max(bandC, bandP, (bandC + bandP) / 2 + d);
    const est = d < 0.5 || edges === 0 ? dB : Math.min(union, edges * d + dB);
    if (apart && est >= union - 1e-9) {
      if (bandC > 0) { deposit(cells, PT.x, PT.y, bandC * aC, aspect); total += bandC * aC; }
      if (bandP > 0) { deposit(cells, PQ.x, PQ.y, bandP * aP, aspect); total += bandP * aP; }
    } else if (est > 0) { deposit(cells, PT.x, PT.y, est * aC, aspect); total += est * aC; }
  }
  res.moved = maxD >= 0.5;
  return total;
}
const PAIR = { moved: false };

// The share of the frame, and of the worst one-third window, that a frame's lines LIGHT (0.1 or more). Wa: the engine's
// own records (W_FLOATS each; engine.drawn.W after a frame), n of them.
export function estimateArea(Wa, n, aspect = 16 / 9, out = { frame: 0, window: 0 }, coarse = 1) {
  LIT.fill(0);
  const step = Math.min(aspect / GX, 1 / GY) / 2 * coarse;
  for (let i = 0; i < n; i++) depositLine(LIT, Wa, i * W_FLOATS, step, aspect);
  windowShares(LIT, aspect, out, "window", "frame");
  return out;
}
// The share of the frame, and of the worst one-third window, that CHANGES from the frame `prev` to the frame `cur`
// ({W, n, keys} each; prev also has map: key -> index; prev may be null for "from black"). Optional per current record:
// contrib[i] = the area it changed, state[i] = 0 stayed put, 1 new, 2 moved. coarse > 1 samples the lines more sparsely
// (the hit-time fit uses 2: twice as fast, a little rougher).
export function estimateChange(prev, cur, aspect = 16 / 9, out = { frame: 0, window: 0 }, contrib = null, state = null, coarse = 1) {
  CHG.fill(0);
  const step = Math.min(aspect / GX, 1 / GY) / 2 * coarse, pn = prev ? prev.n : 0;
  if (pn) SEEN.fill(0, 0, pn);
  for (let i = 0; i < cur.n; i++) {
    const o = i * W_FLOATS, j = pn ? prev.map.get(cur.keys[i]) : undefined;
    let a, s;
    if (j === undefined) { a = depositLine(CHG, cur.W, o, step, aspect); s = 1; }
    else { SEEN[j] = 1; a = depositPair(CHG, prev.W, j * W_FLOATS, cur.W, o, step, aspect, PAIR); s = PAIR.moved ? 2 : 0; }
    if (contrib) contrib[i] = a;
    if (state) state[i] = s;
  }
  for (let j = 0; j < pn; j++) if (!SEEN[j]) depositLine(CHG, prev.W, j * W_FLOATS, step, aspect);   // lines that went dark
  windowShares(CHG, aspect, out, "window", "frame");
  return out;
}
// a frame's worth of the engine's records: W (W_FLOATS each), keys (a line's identity from frame to frame), beam (the
// index of the beam that wrote it), n, and map (key -> index, built once the frame is final)
export function recordBuffer() {
  return { W: new Float64Array(MAX_SEGMENTS * W_FLOATS), keys: new Float64Array(MAX_SEGMENTS), beam: new Int32Array(MAX_SEGMENTS),
    n: 0, map: new Map() };
}
function indexKeys(buf) { buf.map.clear(); for (let i = 0; i < buf.n; i++) buf.map.set(buf.keys[i], i); return buf; }
// A frame's records as a key: two 32-bit FNV-style hashes of every value quantized to 1e-5 (the fit's probes reuse an
// estimate when they draw the same picture again)
function recordHash(Wa, n) {
  let a = 0x811c9dc5 | 0, b = 0x2545f491 | 0;
  for (let i = 0, m = n * W_FLOATS; i < m; i++) {
    const v = Math.round(Wa[i] * 1e5) | 0;
    a = Math.imul(a ^ v, 0x01000193);
    b = Math.imul(b ^ (v + i), 0x5bd1e995); b ^= b >>> 13;
  }
  return `${n}:${a >>> 0}:${b >>> 0}`;
}

// ========================================================================================================== packing --
// The output record (THE OUTPUT, above): texel 0 the line, texel 1 four 24-bit integers held exactly in floats.
const q8 = (v) => Math.round(Math.sqrt(clamp01(v)) * 255);
const q12 = (v) => Math.round(clamp01(v / LEVEL_MAX) * 4095);
function packRecord(Wa, i, seg, k) {
  const o = i * W_FLOATS, s = k * SEG_FLOATS;
  seg[s] = Wa[o]; seg[s + 1] = Wa[o + 1]; seg[s + 2] = Wa[o + 2]; seg[s + 3] = Wa[o + 3];
  seg[s + 4] = q8(Wa[o + W.R]) * 65536 + q8(Wa[o + W.G]) * 256 + q8(Wa[o + W.B]);
  seg[s + 5] = q12(Wa[o + W.I]) * 4096 + q12(Wa[o + W.GLOW]);
  // (the width rounds DOWN, so a core never decodes wider than the engine drew it, nor over CORE_MAX_PX)
  const w = clamp(Math.floor(Wa[o + W.WIDTH] * 16 + 1e-6), 0, 63), h = clamp(Math.round(Wa[o + W.HEAT] * 8), 0, 127);
  const b = clamp(Math.round(Wa[o + W.BLUR] * 4), 0, 127), kf = (Wa[o + W.KIND] ? 1 : 0) + 2 * (Wa[o + W.FLAGS] & 7);
  seg[s + 6] = w + 64 * (h + 128 * (b + 128 * kf));
  const c = (x, qs) => clamp(Math.round(x / qs) + 128, 0, 255);
  seg[s + 7] = c(Wa[o + W.C1], RING_Q[0]) + 256 * c(Wa[o + W.C2], RING_Q[1]) + 65536 * c(Wa[o + W.C3], RING_Q[2]);
}
// The reference decoder: record i of an output `seg` into r. A group header gives {header: true, cx, cy, radius, count};
// a line gives {x0, y0, x1, y1, r, g, b (linear), I, glow, width, heat, blur, kind, flags, held, ring, c1, c2, c3,
// falloff}. The shader decodes the same way (floor and mod on the integers).
export function decodeSeg(seg, i, r = {}) {
  const o = i * SEG_FLOATS;
  r.x0 = seg[o]; r.y0 = seg[o + 1]; r.x1 = seg[o + 2]; r.y1 = seg[o + 3];
  r.header = seg[o + 3] >= GROUP_MARK - 0.5;
  if (r.header) {
    r.cx = seg[o]; r.cy = seg[o + 1]; r.radius = seg[o + 2]; r.count = Math.round(seg[o + 3] - GROUP_MARK);
    r.I = 0; r.glow = 0; r.kind = KIND.FIGURE;
    return r;
  }
  const col = seg[o + 4], lv = seg[o + 5], ring = seg[o + 7];
  const sq = (q) => (q / 255) * (q / 255);
  r.r = sq(Math.floor(col / 65536)); r.g = sq(Math.floor(col / 256) % 256); r.b = sq(col % 256);
  r.I = Math.floor(lv / 4096) / 4095 * LEVEL_MAX; r.glow = (lv % 4096) / 4095 * LEVEL_MAX;
  let s = seg[o + 6];
  r.width = (s % 64) / 16; s = Math.floor(s / 64);
  r.heat = (s % 128) / 8; s = Math.floor(s / 128);
  r.blur = (s % 128) / 4; s = Math.floor(s / 128);
  r.kind = s % 2; r.flags = Math.floor(s / 2);
  r.held = (r.flags & FLAG.HELD) !== 0; r.ring = (r.flags & FLAG.RING) !== 0;
  r.c1 = (ring % 256 - 128) * RING_Q[0]; r.c2 = (Math.floor(ring / 256) % 256 - 128) * RING_Q[1]; r.c3 = (Math.floor(ring / 65536) - 128) * RING_Q[2];
  r.falloff = r.kind === KIND.FIGURE ? 0 : BEAM_FALLOFF;
  return r;
}
// a decoded ringing beam's displacement (px at 1080, along its left normal) and blur band at u in [0, 1]
export function ringOffsetPx(r, u) {
  if (!r.ring) return 0;
  const s = Math.PI * u;
  return r.c1 * Math.sin(s) + r.c2 * Math.sin(2 * s) + r.c3 * Math.sin(3 * s);
}
export function blurPx(r, u) { return r.ring ? r.blur * Math.sin(Math.PI * u) : r.blur; }

// ============================================================================================================ clock --
// The page's BeatClock (vj-core.js: bpm, conf, phase(now), nextBeatAt(now), alive(now)) as this module's clock.
export function clockFromBeatClock(bc) {
  return {
    get bpm() { return bc.bpm; },
    get conf() { return bc.conf; },
    phaseAt: (t) => bc.phase(t),
    nextBeatAt: (t) => bc.nextBeatAt(t),
    alive: (t) => (typeof bc.alive === "function" ? bc.alive(t) : bc.bpm > 0),
  };
}

// =========================================================================================================== engine --
const DEFAULTS = Object.freeze({
  seed: 1,
  aspect: 16 / 9,
  presentLagMs: 1000 / 60,    // rAF time -> photon: one frame
  onsetRule: "early",         // "early": a pulse lights in the last frame whose picture lands at or before its beat
                              //          (0 to one frame early, never late); "nearest": within half a frame either way
  fallbackBpm: 150,
  variety: 1,                 // 0 = every hit identical (rehearsal); 1 = the full deal
  bankMode: "auto",
  gateMode: "auto",           // or a GATES id: the dial's fixed gate
  patternMode: "auto",        // or a PATTERNS id (a pinned pattern)
  orderMode: "auto",
  colourMode: "auto",
  velocityTiers: "normal",    // "normal": soft single, medium one-two, hard triple; "inverted": hard = one heavy hit
  vibrate: false,
  shapeMode: null,            // null, "auto" (every hit draws a figure from the shape deck) or a SHAPES id
  section: "any",
  heroGap: 6,                 // a hero needs at least this many hits since the last hero
  antiRepeat: 32,             // a signature never repeats within this many hits
  maxHits: 4,                 // hits drawn at once, older ones fading out (a backstop: a new hit takes over from them)
});

const TINY = 1e-9;

export function createLaserEngine(opts = {}) { return new LaserEngine(opts); }

export class LaserEngine {
  constructor(opts = {}) {
    this.o = { ...DEFAULTS };
    this.clock = null;
    this.col = themeColours(DEFAULT_THEME);
    this.set(opts);
    this.reset();
  }

  // ---------------------------------------------------------------------------------------------------- settings --
  set(opts = {}) {
    for (const [k, v] of Object.entries(opts)) {
      if (k === "clock") this.clock = v || null;
      else if (k === "theme") this.setTheme(v);
      else if (k === "section") this.setSection(v);
      else if (k in DEFAULTS) this.o[k] = v;
    }
    this.o.variety = clamp01(Number(this.o.variety));
    return this;
  }
  setTheme(theme) { this.col = themeColours(theme); if (this.shapeFits) this.shapeFits.clear(); }
  setClock(clock) { this.clock = clock || null; }
  setVibrate(on, t = null) {
    this.o.vibrate = !!on;
    if (!this.vib) return;
    for (const v of this.vib) v.offT = on ? null : (t === null ? v.t0 : t);
  }
  setSection(name, t = null) {
    const s = SECTIONS.includes(name) ? name : "any";
    if (this.decks && s === this.o.section) return;
    this.o.section = s;
    if (this.decks) { this.sectionIdx++; this._makeDecks(); }
  }

  reset() {
    const seed = this.o.seed;
    this.hits = [];
    this.log = [];
    this.serial = 0;
    this.hitCount = 0;
    this.lastHitT = -Infinity;
    this.level = 0;
    this.sinceHero = Infinity;
    this.altCount = 0;
    this.padDown = false; this.padT = 0; this.padHit = null;
    this.recentStarts = [];
    this.sigs = [];
    this.lastDeal = null;
    this.pinned = false;
    this.lastShape = null;
    this.pending = [];
    this.vib = HEADS.map((h, i) => ({ t0: -1e9, amp: 0, ph: TAU * makeRng(seed, "vib", i)(), offT: null, rings: [] }));
    this.sectionIdx = 0;
    this._makeDecks();
    this.frameIdx = 0; this.F = 1000 / 60; this.tPrev = null; this.ringT = null; this.inFrame = false;
    this.tRef = null; this.posRef = 0;
    this.lastPeriod = 0;
    this.nowT = 0;
    this.beams = [];
    this.bn = 0;
    // the engine's own records: `drawn` = the frame last returned (what the next frame's change is measured against),
    // `work` = the frame being built; two more for the hit-time fit, which never touches the frame the page draws
    this.drawn = recordBuffer(); this.work = recordBuffer();
    this.probeA = recordBuffer(); this.probeB = recordBuffer();
    this.contrib = new Float64Array(MAX_SEGMENTS); this.state = new Uint8Array(MAX_SEGMENTS);
    this.chg = { frame: 0, window: 0 }; this.lit = { frame: 0, window: 0 };
    this.shapeCache = new Map();
    this.shapeFits = new Map();        // what each figure took in the fit, by context (see _fitShapesOnce)
    this.out = { t: 0, seg: new Float32Array(MAX_SEGMENTS * SEG_FLOATS), n: 0, head: new Int16Array(MAX_SEGMENTS),
      heads: new Float32Array(HEADS.length), padGrid: new Float32Array(12), pad: { level: 0, rgb: [0, 0, 0], tier: 0 },
      area: { frame: 0, window: 0, litFrame: 0, litWindow: 0, over: false },
      solo: 1, events: [], gate: "", pattern: "", tier: "", bank: "", order: "", colour: "" };
  }

  _makeDecks() {
    const rng = makeRng(this.o.seed, "decks", this.sectionIdx, this.o.section);
    this.dealRng = makeRng(this.o.seed, "deal", this.sectionIdx);
    const sec = this.o.section;
    const pats = PATTERN_IDS.filter((p) => !PATTERNS[p].heroOnly && (sec === "any" || PATTERNS[p].sections === ALL
      || PATTERNS[p].sections.includes(sec)));
    this.decks = {
      pattern: new Deck(pats, rng), hero: new Deck(HERO_PATTERNS, rng), order: new Deck(ORDER_IDS, rng),
      colour: new Deck(COLOUR_IDS, rng), bank: new Deck(BANK_DEAL, rng), shape: new Deck(SHAPES, rng),
      aim: new Deck([0, 1, 2, 3, 4, 5], rng), mask: new Deck([0, 1, 2, 3], rng),
    };
    this.headDecks = new Map();
    this.deckRng = rng;
  }

  // ------------------------------------------------------------------------------------------------------- clock --
  _clockOK(t) {
    const c = this.clock;
    return !!(c && c.bpm > 0 && (typeof c.alive !== "function" || c.alive(t)));
  }
  period(t = this.nowT) {
    if (this._clockOK(t)) this.lastPeriod = 60000 / this.clock.bpm;
    return this.lastPeriod > 0 ? this.lastPeriod : 60000 / this.o.fallbackBpm;
  }
  // the beat position at time t: the clock's own (posAt) when it has one, else unwrapped from its phase against the
  // position committed on the last frame; free-running on the last tempo with no clock
  posAt(t) {
    const c = this.clock, ok = this._clockOK(t);
    if (ok && typeof c.posAt === "function") { const p = c.posAt(t); if (Number.isFinite(p)) return p; }
    const per = this.period(t);
    if (this.tRef === null) {
      const ph = ok && typeof c.phaseAt === "function" ? c.phaseAt(t) : 0;
      return Number.isFinite(ph) ? clamp(ph, 0, 0.999) : 0;
    }
    const pred = this.posRef + (t - this.tRef) / per;
    if (!ok || typeof c.phaseAt !== "function") return pred;
    const ph = c.phaseAt(t);
    if (!Number.isFinite(ph)) return pred;
    let cand = Math.floor(pred) + ph;
    if (cand - pred > 0.5) cand -= 1; else if (pred - cand > 0.5) cand += 1;
    return cand;
  }
  _commitPos(t) {
    const p = this.posAt(t);
    if (this.tRef === null || p >= this.posRef) this.posRef = p;      // the position never runs backward
    this.tRef = t;
    return this.posRef;
  }
  // the beat position the frame at t is judged at: the picture's presentation time, nudged early by the onset rule
  _evalPos(t, pos) {
    const s = this.o.onsetRule === "nearest" ? this.F / 2 : this.F;
    const tE = t + this.o.presentLagMs + s - 1e-6;
    const c = this.clock;
    if (this._clockOK(t) && typeof c.posAt === "function") { const p = c.posAt(tE); if (Number.isFinite(p)) return Math.max(p, pos); }
    return pos + (tE - t) / this.period(t);
  }
  // the confidence ladder (spec 3.4): no loop step finer than this many beats
  _minStep(t) {
    if (!this._clockOK(t)) return 1 / 2;
    const conf = this.clock.conf;
    if (!(typeof conf === "number")) return 0;
    return conf >= 0.6 ? 0 : conf >= 0.3 ? 1 / 2 : 1;
  }

  // -------------------------------------------------------------------------------------------------- the press --
  // Pad 2 pressed at time t (ms) with velocity vel (0..1). Returns the hit's description (JSON-safe).
  hit(t, vel = 0.7, opts = {}) {
    vel = clamp01(Number(vel) || 0);
    if (!Number.isFinite(t)) t = this.nowT;           // a press with no usable time lands on the newest frame's time
    this.nowT = Math.max(this.nowT, t);
    const per = this.period(t), pH = this.posAt(t);
    const gapMs = Number.isFinite(this.lastHitT) ? t - this.lastHitT : Infinity, gap = gapMs / per;
    // presses faster than 3 a second strobe like a fast gate whatever gate each one fires (spec 4.1 rule 2)
    const rateFast = gapMs < FAST_PRESS_MS;
    this.padDown = !opts.noHold; this.padT = t;
    const v0 = this.o.variety <= 0;
    let kind;
    if (opts.phrase) kind = "phrase";
    else if (v0 || gap > RETRIGGER.escalate) kind = "burst";
    else if (gap > RETRIGGER.flicker) kind = "escalate";
    else if (gap > RETRIGGER.rapid) kind = "flicker";
    else kind = "rapid";
    const roll16 = gap <= RETRIGGER.roll16;
    this.lastHitT = t;

    // a rapid press extends the running roll (the roll is locked to the grid; each press advances its heads). Only a
    // LOOP can be extended: with the dial on a short gate (Single ... the phrase) every rapid press fires that gate as a
    // hit of its own, and a rapid-tier hit left over from such a press has no loop to stretch.
    const dialLoop = this.o.gateMode === "auto" || !GATES[this.o.gateMode] || GATES[this.o.gateMode].kind === "loop";
    if (kind === "rapid" && dialLoop) {
      const roll = this.hits.find((h) => h.tier === "rapid" && h.loop && !h.done && !h.fading);
      if (roll) {
        // the roll runs on past the press by more than the rapid edge, so the next press of the stream still finds it
        roll.loop.endP = Math.max(roll.loop.endP, pH + RETRIGGER.rollHold);
        roll.finished = false;
        if (roll16) roll.stepOverride = GATES.roll16.step;
        // The press's velocity reaches the roll at its next pulse (a lit figure's size and a lit beam's width follow the
        // velocity: changing it mid-pulse moved every line at once), and never past the velocity it was fitted at (a
        // harder press would widen and heat its beams past the fit, and its pulses would go dark over the budget).
        roll.velNext = Math.min(roll.fitVel, Math.max((roll.velNext ?? roll.vel) * 0.7, vel));
        roll.walk++;
        this.padHit = roll;
        const info = { ...roll.info, t, vel, ext: true, gate: roll.stepOverride ? "roll16" : roll.info.gate };
        this._log(info);
        return info;
      }
    }
    this.hitCount++;
    this.sinceHero++;

    let level = this.level || 1;
    if (kind === "burst") level = 1;
    else if (kind === "escalate") level = Math.min(3, level + 1);
    let tier = kind;
    if (kind === "escalate" && level === 3) {
      if (this.sinceHero >= this.o.heroGap) tier = "hero"; else level = 2;
    }
    if (kind !== "flicker" && kind !== "rapid" && kind !== "phrase") this.level = level;
    const rng = makeRng(this.o.seed, "hit", this.sectionIdx, this.hitCount);

    // the gate: the dial's fixed gate, else the tier's
    let gate;
    const vg = this._velocityGate(vel, rng);
    if (kind === "phrase") gate = "tttou";
    else if (this.o.gateMode !== "auto" && GATES[this.o.gateMode]) gate = this.o.gateMode;
    else if (v0) gate = "single";
    else if (tier === "hero") gate = "triple";
    else if (kind === "escalate") gate = this.o.vibrate && rng() < 1 / 3 ? "tttou" : STEP_UP[vg] || vg;
    else if (kind === "flicker") gate = "onetwo";
    else if (kind === "rapid") gate = roll16 ? "roll16" : "roll8";
    else gate = vg;
    const fast = rateFast || this._gateFast(gate, per);

    const deal = this._deal({ rng, tier, level, gate, fast, kind, vel });
    gate = deal.gate;
    const H = this._spawn(deal, { t, pH, per, vel, tier, level, gate, fast: rateFast || this._gateFast(gate, per), kind });
    if (tier === "hero") { this.sinceHero = 0; this.pending.push({ type: "hero" }); }
    this.padHit = H;
    this._log(H.info);
    return H.info;
  }
  // the pad let go: a held loop finishes its current step and stops
  release(t) {
    this.padDown = false;
    for (const H of this.hits) if (H.loop && H.loop.endP === Infinity) {
      H.loop.endP = H.loop.P;       // the next slot: the current step finishes, nothing new starts
      H.info.release = t;
    }
  }
  // Daniel's phrase as its own trigger (a button or a combo): "t t tou blur blur flash"
  phrase(t, vel = 0.9) { return this.hit(t, vel, { phrase: true, noHold: true }); }
  pin(on = true) { this.pinned = !!on; }

  _log(info) { this.log.push(info); if (this.log.length > 128) this.log.shift(); }

  _velocityGate(vel, rng) {
    const r = rng();
    const tier = vel < 0.45 ? 0 : vel <= 0.8 ? 1 : 2;
    const t = this.o.velocityTiers === "inverted" ? 2 - tier : tier;
    return t === 0 ? "single" : t === 1 ? "onetwo" : r < 0.25 ? "triplet" : "triple";
  }
  _gateFast(gate, per) {
    const G = GATES[gate];
    if (G.kind === "short") {
      if (G.pulses.length < 2) return false;
      let minStep = Infinity;
      for (let i = 1; i < G.pulses.length; i++) minStep = Math.min(minStep, G.pulses[i].at - G.pulses[i - 1].at);
      return 1000 / (minStep * per) > 3;
    }
    const step = G.stages ? Math.min(...G.stages) : G.step;
    return 1000 / (step * per) > 3;
  }

  // ------------------------------------------------------------------------------------------------- the deal --
  _deal({ rng, tier, level, gate, fast, kind, vel }) {
    const o = this.o, D = this.decks, v = o.variety;
    const v0 = v <= 0;
    const prev = this.lastDeal;
    const shapeOn = !!o.shapeMode;
    const legalPattern = (p) => {
      if (shapeOn) return p === "figure";
      if (fast && PATTERNS[p].ungated) return false;
      return true;
    };
    const requireTwo = tier === "escalate" || tier === "hero";
    const legalColour = (c) => {
      if (this.col.splitOnly && BLENDING.has(c)) return false;
      if (c === "gradient" && this.col.hueGap > 80) return false;
      if (requireTwo && !TWO_COLOUR.has(c)) return false;
      return true;
    };
    const pick = (axis, deck, legal, fixed, prevVal) => {
      if (fixed && fixed !== "auto") return fixed;
      if (v0) { const c = deck.cards.find((x) => !legal || legal(x)); return c === undefined ? deck.first() : c; }
      if (v < 1 && prevVal !== undefined && prevVal !== null && (!legal || legal(prevVal)) && rng() >= v) return prevVal;
      return deck.next(legal);
    };
    if (this.pinned && prev) return { ...prev, gate };

    let best = null;
    for (let attempt = 0; attempt < 9; attempt++) {
      let pattern = tier === "hero" ? pick("hero", D.hero, null, null, null)
        : pick("pattern", D.pattern, legalPattern, shapeOn ? "figure" : o.patternMode, prev && prev.pattern);
      let g = gate;
      if (tier === "hero" && pattern === "star") g = "single";           // the starburst is one ungated onset
      else if (fast && PATTERNS[pattern] && PATTERNS[pattern].ungated) pattern = "crown";
      const order = pick("order", D.order, null, o.orderMode, prev && prev.order);
      let colour = tier === "hero" ? (pattern === "star" ? "burst" : "trinity")
        : pick("colour", D.colour, legalColour, o.colourMode, prev && prev.colour);
      if (!legalColour(colour) && o.colourMode === "auto") colour = this.col.splitOnly ? "halves" : "split";
      let bankMode = o.bankMode;
      if (bankMode === "auto") bankMode = pick("bank", D.bank, null, null, prev && prev.bankMode);
      let bank = bankMode;
      // (the alternation counts hits, not redeal attempts, so a redeal never repeats a bank)
      if (bankMode === "alternate") bank = (this.altCount % 2 === 0) ? "A" : "B";
      const pool = this._pool(pattern, bank);
      const start = v0 ? pool[0] : this._dealStart(pool, rng);
      const shape = pattern === "figure"
        ? (shapeOn && o.shapeMode !== "auto" && SHAPES.includes(o.shapeMode) ? o.shapeMode : (v0 ? SHAPES[0] : D.shape.next()))
        : null;
      const deal = { pattern, order, colour, bankMode, bank, start, shape, gate: g };
      const sig = this._sig(deal);
      const axes = prev ? ["pattern", "gate", "order", "colour", "start"].filter((k) => deal[k] !== prev[k]).length : 5;
      best = deal;
      if (v0 || v < 1 || (!this.sigs.includes(sig) && axes >= 2)) break;
    }
    // the last word: if the combination still repeats, the start moves to the head used least recently
    if (!v0 && v >= 1 && this.sigs.includes(this._sig(best))) {
      const pool = this._pool(best.pattern, best.bank);
      for (const h of pool) { const d = { ...best, start: h }; if (!this.sigs.includes(this._sig(d))) { best = d; break; } }
    }
    // the hit seed's small variations: sweep direction, aim +-0.1 rad, beam count +-1, spread +-15 %
    best.dir = v0 ? 1 : rng() < 0.5 ? -1 : 1;
    best.angle = v0 ? 0 : (rng() * 2 - 1) * 0.1;
    best.beamJit = v0 ? 0 : Math.floor(rng() * 3) - 1;
    best.spreadMul = v0 ? 1 : 1 + (rng() * 2 - 1) * 0.15;
    best.aimIdx = v0 ? 0 : D.aim.next();
    best.focus = v0 ? 0 : Math.floor(rng() * FOCI.length);
    best.cage = v0 ? 0 : Math.floor(rng() * CAGE_TILT.length);
    best.mask = v0 ? 0 : D.mask.next();
    best.seed = hash32(this.o.seed, this.sectionIdx, this.hitCount);
    this.recentStarts.push(best.start);
    if (this.recentStarts.length > 8) this.recentStarts.shift();
    const sig = this._sig(best);
    this.sigs.push(sig);
    if (this.sigs.length > Math.max(1, this.o.antiRepeat)) this.sigs.shift();
    if (best.bankMode === "alternate") this.altCount++;
    this.lastDeal = best;
    return best;
  }
  _sig(d) { return `${d.pattern}|${d.gate}|${d.order}|${d.colour}|${HEADS[d.start].name}|${d.bank}`; }

  // the heads a pattern may use under a bank choice
  _pool(pattern, bank) {
    if (pattern === "crown" || pattern === "star" || pattern === "figure") return [HERO_HEAD];
    if (pattern === "ladder") return SIDE_HEADS.slice();
    const banks = bank === "A" || bank === "call" || bank === "mirror" ? BANK_A.slice() : bank === "B" ? BANK_B.slice()
      : BANK_A.concat(BANK_B);
    if (pattern === "tunnel") return banks.concat(SIDE_HEADS);
    return banks;
  }
  // a start head from the pool's deck: of the next three cards, the one farthest from the last four starts
  _dealStart(pool, rng) {
    if (pool.length === 1) return pool[0];
    const key = pool.join(",");
    let deck = this.headDecks.get(key);
    if (!deck) { deck = new Deck(pool, makeRng(this.o.seed, "heads", this.sectionIdx, key)); this.headDecks.set(key, deck); }
    const recent = this.recentStarts.slice(-4);
    const dist = (a, b) => Math.hypot(HEADS[a].sx - HEADS[b].sx, HEADS[a].y - HEADS[b].y);
    return deck.next(null, (c) => (recent.length ? Math.min(...recent.map((r) => dist(c, r))) : 1) + rng() * 0.05, 3);
  }

  // -------------------------------------------------------------------------------------------------- the steps --
  _steps(order, pool, start, w, maxHeads, rng) {
    if (!pool.length) return [[]];
    const byX = pool.slice().sort((a, b) => HEADS[a].sx - HEADS[b].sx || HEADS[b].y - HEADS[a].y);
    const rot = (arr, h) => { const i = Math.max(0, arr.indexOf(h)); return arr.slice(i).concat(arr.slice(0, i)); };
    const group = (seq, n) => { const out = []; for (let i = 0; i < seq.length; i += n) out.push(seq.slice(i, i + n)); return out; };
    const rings = () => {      // heads grouped by distance from the centre line, innermost first
      const m = new Map();
      for (const h of pool) { const k = HEADS[h].ring; if (!m.has(k)) m.set(k, []); m.get(k).push(h); }
      return [...m.keys()].sort((a, b) => a - b).map((k) => m.get(k));
    };
    let steps;
    switch (order) {
      case "one": steps = group([start, ...shuffled(pool.filter((h) => h !== start), rng)], w); break;
      case "lr": steps = group(rot(byX, start), w); break;
      case "rl": steps = group(rot(byX.slice().reverse(), start), w); break;
      case "alt": {
        const L = byX.filter((h) => HEADS[h].sx < 0).reverse(), R = byX.filter((h) => HEADS[h].sx >= 0);
        const first = HEADS[start].sx < 0 ? rot(L, start) : rot(R, start), second = HEADS[start].sx < 0 ? R : L;
        const seq = [];
        for (let i = 0; i < Math.max(first.length, second.length); i++) { if (first[i] !== undefined) seq.push(first[i]); if (second[i] !== undefined) seq.push(second[i]); }
        steps = group(seq, w);
        break;
      }
      case "pairs": {
        const seen = new Set(), pairs = [];
        for (const h of rot(byX.slice().sort((a, b) => HEADS[a].ring - HEADS[b].ring), start)) {
          if (seen.has(h)) continue;
          const t = pool.includes(HEADS[h].twin) ? HEADS[h].twin : h;
          seen.add(h); seen.add(t);
          pairs.push(t === h ? [h] : [h, t]);
        }
        steps = group(pairs, w).map((g) => g.flat());
        break;
      }
      case "centreout": steps = group(rings(), w).map((g) => g.flat()); break;
      case "outsidein": steps = group(rings().reverse(), w).map((g) => g.flat()); break;
      case "oddeven": steps = [byX.filter((_, i) => i % 2 === 0), byX.filter((_, i) => i % 2 === 1)].filter((s) => s.length); break;
      case "rotor": steps = group(rot(pool.slice().sort((a, b) => HEADS[a].ang - HEADS[b].ang), start), w); break;
      case "shuffle": steps = group([start, ...shuffled(pool.filter((h) => h !== start), rng)], w); break;
      case "rows": {
        const rows = ["floor", "tower", "truss", "hero"].map((r) => byX.filter((h) => HEADS[h].row === r)).filter((s) => s.length);
        steps = rows.length > 1 ? rows : group(byX, Math.max(1, Math.ceil(byX.length / 2)));
        break;
      }
      default: steps = [byX];
    }
    // a step never lights more heads than the cap (see capHeads)
    return steps.map((s) => capHeads(s, maxHeads));
  }

  // ------------------------------------------------------------------------------------------------- the spawn --
  _spawn(deal, { t, pH, per, vel, tier, level, gate, fast, kind, spare = null, loopSpan = null, loopAfter = -Infinity }) {
    const o = this.o, G = GATES[gate];
    const rng = makeRng(deal.seed, "spawn");
    const cap = fast ? BUDGET.fast : BUDGET.single;
    const pool = this._pool(deal.pattern, deal.bank);
    const w = kind === "flicker" || kind === "rapid" ? 1 : level >= 2 ? 2 : 1;
    const mirrorLike = deal.bank === "mirror";
    const perStepCap = mirrorLike ? Math.max(1, cap.heads >> 1) : cap.heads;
    let steps = this._steps(deal.order, pool, deal.start, w, perStepCap, rng);
    if (mirrorLike) steps = steps.map((s) => [...new Set(s.concat(s.map((h) => HEADS[h].flip)))]);
    let aLen = steps.length;
    if (deal.bank === "call") {
      const resp = steps.map((s) => s.map((h) => HEADS[h].flip));
      steps = steps.concat(resp);
    }
    const startName = HEADS[deal.start].name;
    // the fan size: velocity as today (3 + 9 vel beams, 0.4 + 1.3 vel rad), the hit seed's +-1 and +-15 %
    const beams = clamp(3 + Math.round(9 * vel) + deal.beamJit, 1, 12);
    const spread = (0.4 + 1.3 * vel) * deal.spreadMul;
    const H = {
      id: ++this.serial, t0: t, p0: pH, vel, fitVel: vel, tier, level, gate, fast, kind, deal,
      pattern: deal.pattern, order: deal.order, colour: deal.colour, bank: deal.bank, steps, aLen,
      beams, spread, pulses: null, pi: 0, loop: null, cur: null, fired: 0, walk: 0, done: false, fading: false,
      fadeT: 0, finished: false, finishFrame: 0, tailTau: 0, peak: 0.6 + 0.5 * vel, stepOverride: 0, smearFrame: -1,
      shapes: null, lastPulseP: pH, call: deal.bank === "call", crownN: 0, holdSpawned: false, started: false, pStart: pH,
      trimPri: Infinity, thin: false, choked: false, waitFor: null, onsetFrame: -1, ringScale: 1, shapeMul: null, blurMul: 1,
      headCap: Infinity, beamCap: Infinity,
      // the settings a hit is fitted to stay its own for its whole life: whether it plucks its strings (Vibrate, or the
      // phrase) and the theme's colours (a theme picked while it runs reaches the next hit, never a lit pulse)
      plucks: o.vibrate || gate === "tttou", col: this.col,
    };
    H.crownN = deal.pattern === "star" || (deal.pattern === "crown" && tier === "hero") ? (fast ? 12 : 24) : 12;
    if (deal.pattern === "figure") {
      const seq = [deal.shape];
      for (let i = 1; i < 16; i++) seq.push(this.decks.shape.next());
      H.shapes = seq;
      // A fast hit steps from the last hit's figure to its own on its first beat (each pulse frozen); a slow onset
      // would morph from it WHILE LIT, every piece sweeping across the frame in a quarter beat (up to 42 % of a window
      // in white), and the figure it morphs from is already dark (a new hit plays alone): it starts formed.
      H.shapeFrom = fast ? this.lastShape : null;
      this.lastShape = deal.shape;
    }
    const span = loopSpan === null ? G.span : loopSpan;
    if (G.kind === "short") this._anchorShort(H, G, pH, per);
    else this._startLoop(H, G, pH, per, span, loopAfter);
    // A new hit PLAYS ALONE, so that what the fit measured -- each hit by itself -- is what the frame shows. Hits fitted
    // alone and drawn together added up: two Reverse-Bass loops pressed a beat apart lit the same off-beats twice and
    // went dark in the same frame; a hero's starburst rang and decayed while the loop before it went dark.
    //   - A fast hit CHOKES the hits before it (a lit pulse finishes its minimum on-time, nothing new starts, then they
    //     go dark at once), and so is a running fast hit when any new press starts.
    //   - Any other new hit TAKES OVER (latest takes precedence, a lighting desk's LTP merge) from its first pulse: the
    //     hits before it fire nothing from there on (a pulse in progress -- the one lit as the press comes too --
    //     finishes, its length bounded to leave the frame rules' gap before the new first pulse), and what is left of
    //     them -- a tail -- goes dark in the frame BEFORE that pulse comes due (see _handOver). If a loop on the same
    //     grid is already lighting the very pulse a new loop would start on, the new loop starts one step later instead
    //     of lighting a second copy of it (the Reverse-Bass Gate pressed on its off-beat: one clean pulse per off-beat).
    // Either way the new hit's first pulse waits until they are dark, so one hit's "off" and the next one's "on" never
    // land in one frame -- unless that frame's change is measured to stay inside the budget (_cutsClean): a press that
    // comes within a frame of its beat leaves no frame to go dark in, and round 3's wait made such pulses late.
    const live = this.hits.filter((h) => !h.done && h !== spare);
    const choke = [], handover = [];
    for (const h of live) {
      if (fast || h.fast || !h.started || h.choked) { choke.push(h); continue; }     // (one choked already is still waited for)
      if (H.loop && h.loop && h.on && h.cur && Math.abs(h.cur.P - H.pStart) < 1e-6 && this._sameGrid(h, H)) {
        this._startLoop(H, G, pH, per, span, H.pStart + 1e-6);
      }
      handover.push(h);
    }
    if (spare) handover.push(spare);
    for (const h of handover) this._takeOver(h, H.pStart);
    this._fitHit(H, per, t);
    for (const h of choke) this._choke(h);
    const wait = choke.concat(handover);
    H.waitFor = wait.length ? wait : null;
    H.handover = handover.length ? handover : null;
    if (!fast) { const lit = live.filter((h) => !h.fading && !h.choked); if (lit.length >= o.maxHits) this._fade(lit[0], t); }
    this.hits.push(H);
    H.info = {
      id: H.id, t, vel: Math.round(vel * 1000) / 1000, tier, level, gate, pattern: deal.pattern, order: deal.order,
      colour: deal.colour, bank: deal.bank, start: startName,
      heads: [...new Set(steps.flat())].map((h) => HEADS[h].name), beams: H.beams, spread: Math.round(H.spread * 1000) / 1000,
      angle: Math.round(deal.angle * 1000) / 1000, dir: deal.dir, shape: deal.shape, hero: tier === "hero", fast,
      sig: this._sig(deal),
    };
    return H;
  }
  // a running loop h on the same grid as the new loop H: the same step, H's first pulse on one of h's grid points
  _sameGrid(h, H) {
    const a = h.loop, b = H.loop;
    const sa = a.slot ? a.slot.step : a.lastStep;
    if (!(sa > 0) || Math.abs(sa - b.lastStep) > 1e-6) return false;
    const d = (b.P - a.P) / sa;
    return Math.abs(d - Math.round(d)) <= 1e-4;
  }
  // A newer hit takes over at beat P: h fires no pulse at or after it, and a pulse it lights before leaves the frame
  // rules' gap before P (see _evalHit) -- the pulse lit right now as well (round 3 bounded only the pulses still to
  // come, so a pulse lit when the press came ran on into the frame the new first pulse was due, and held it back).
  _takeOver(h, P) {
    h.takeoverP = Math.min(h.takeoverP ?? Infinity, P);
    if (h.loop) h.loop.endP = Math.min(h.loop.endP, P);
    else if (h.pulses) {
      let n = h.pulses.length;
      while (n > h.pi && h.pulses[n - 1].P >= P - 1e-9) n--;
      if (n < h.pulses.length) h.pulses = h.pulses.slice(0, n);
    }
    if (h.cur && h.on && this.posE !== undefined) {
      const per = this.period(), f0 = this._nowFrame();
      const pos0 = this.inFrame ? this.posE : this.posE + this.F / per;       // the position frame f0 is judged at
      const due = f0 + Math.max(0, Math.ceil((P - pos0) * per / this.F - 1e-6));
      const minOff = Math.max(1, Math.ceil(FRAME_RULES.minOffMs / this.F - 1e-6));
      h.cur.N = Math.max(this._minOnFrames(), Math.min(h.cur.N, due - minOff - h.cur.onFrame));
    }
  }
  _fade(h, t, tau = 40) { if (!h.fading) { h.fading = true; h.fadeT = t; h.fadeTau = tau; } }
  _minOnFrames() { return Math.max(1, Math.ceil(FRAME_RULES.minOnMs / this.F - 1e-6)); }
  // the frame the next picture is: the one being built (inside frame()), else the one after the last built
  _nowFrame() { return this.inFrame ? this.frameIdx : this.frameIdx + 1; }
  _choke(h) {
    if (h.choked) return;
    h.choked = true;
    // A pulse already lit keeps its minimum on-time (40 ms), then goes off; nothing new starts. It goes off from the
    // next picture (_nowFrame): choked between frames, the next frame; choked while a frame is built (the frame before
    // a newer hit's first pulse, see _handOver), that very frame -- round 3 left it lit one frame more.
    if (h.cur && h.on) h.cur.N = Math.min(h.cur.N, Math.max(this._minOnFrames(), this._nowFrame() - h.cur.onFrame));
  }
  // put a hit out in this very frame (what is left of it lights nothing a frame's budget would miss: see _handOver)
  _cut(h) { h.choked = true; h.cut = true; }

  // Shrink a new hit until it fits its CHANGE budget (90 % of it for a fast hit, 80 % for a single onset) over its
  // whole life, measured before it is shown: each pulse's onset (all of its light appears) wherever the hit can be (see
  // _fitProbes: a loop's whole 16-beat cycle, so every figure it will morph into), and -- by simulating it frame by
  // frame -- its motion and its ringing while lit and through its tail (a moving beam changes where it was and where it
  // is), from its first onset and from its worst. For speed the fit works on the worst few onsets and checks every one
  // before it calls the hit done. A figure gives way shape by shape: a dense figure sharpens (a ringing one) or dims on
  // its own, so the sparse ones keep their light. The per-frame check stays as the backstop.
  _fitHit(H, per, t) {
    const cap = H.fast ? BUDGET.fast : BUDGET.single, aim = H.fast ? 0.9 : 0.8;
    const keep = { cur: H.cur, inten: H.inten, on: H.on, level01: H.level01, started: H.started, finished: H.finished,
      tailAge: H.tailAge, pulsesTotal: H.pulsesTotal, finishT: H.finishT, smearFrame: H.smearFrame };
    const asp = this.asp || this.o.aspect;
    this.asp = asp;
    // The strings this hit sets ringing (Vibrate, or the phrase's own pluck): for the probes each is plucked as this hit
    // will pluck it, on top of what still rings from before; all is put back after. A ringing hit's first lever is a
    // softer pluck (ringScale), so it keeps its beams and its brightness.
    // (A string still ringing from before rings this hit's lines too, though it plucks nothing itself: the phrase plucks
    // even with Vibrate off, and the hero string it rang carries into every figure and crown for seconds after. Round 2
    // fitted such a hit as still and it moved.)
    const plucks = H.plucks;
    const vibKeep = this.vib.map((v) => ({ ...v }));
    const rings = plucks || vibKeep.some((v) => this._ringState(v, t) !== null);
    // A hit that plucks again and again (Vibrate on a gate of several pulses; the phrase's pluck and smears) builds its
    // rings up to its own cap (MAX_PX * ringScale), so it is probed at that cap; a single pluck at its own size.
    const G0 = GATES[H.gate];
    const repluck = H.gate === "tttou" || (this.o.vibrate && (G0.kind === "loop" || G0.pulses.length > 1));
    const pluckAmp = !plucks ? 0 : repluck ? VIB.MAX_PX : VIB.AMP_PX * (0.6 + 0.4 * H.vel);
    // (risen = the ring is through its attack already: the onset probes, so a pulse is measured with the blur band it
    // will have by its end, the light that goes off with it; and the lives from a later pulse, whose strings still ring
    // from the pulses before (rings superpose, and in phase they swing as one ring at the cap). The life from the first
    // pulse plucks at its start, on top of what still rings from before, which is through its attack: two rings. Round 2
    // plucked every life from rest, one ring rising from nothing, and a figure ringing from its first pulse moved more
    // at its second pulse's tail than that life had measured.)
    const setRings = (risen = false) => {
      if (!rings) return;
      const cap = VIB.MAX_PX * H.ringScale, back = t - 3000 * VIB.ATTACK_S;
      for (let i = 0; i < this.vib.length; i++) {
        const k = vibKeep[i], v = this.vib[i], offS = k.offT === null ? null : Math.max(0, (t - k.offT) / 1000);
        let now = 0;
        for (const r of k.rings) { const age = (t - r.t0) / 1000; if (age >= 0 && age < 6) now += vibModes(age, r.amp, offS)[0] * ringAttack(age); }
        const amp = Math.max(now, Math.min(cap, now + pluckAmp * H.ringScale));
        v.rings = risen ? [{ t0: back, amp }] : [{ t0: back, amp: now }, { t0: t, amp: amp - now }].filter((r) => r.amp > 0);
        v.offT = null;
      }
    };
    const fits = (w, f) => w <= cap.window * aim && f <= cap.frame * aim;
    const area = { frame: 0, window: 0 };
    const fig = H.pattern === "figure" && !!H.shapes;
    if (fig && !H.shapeMul) H.shapeMul = {};
    // A loop's pulses take their colour from how many it has fired (masks skip, rapid presses walk), so any pulse may
    // show any colour of its mode's cycle: its probes draw each beam in the brightest colour it can take (_colour).
    this.fitBright = !!H.loop;
    this.fitBlur = true;               // (each ringing figure piece at its worst blur: see _write)
    // the onsets this hit can show (each where it will be: a fast hit's moving pattern freezes at each pulse's own beat
    // position, which moves the scissors' foci, the zigzag's side, the hot beam's aim, the figure, from pulse to pulse)
    // (a single slow onset is drawn a little into its own motion; a loop's pulse where it lands)
    const all = this._fitProbes(H);
    for (const pr of all) {
      pr.at = H.fast || pr.reach || H.loop ? pr.P : H.pStart + 0.3;
      if (fig) pr.shapes = this._figureAt(H, pr.at);
    }
    // Probes that draw the same records measure the same: each picture is estimated once (a loop's probes repeat many
    // pictures -- a still pattern at every position, a group whose heads light alike -- and the fit measures again
    // after each step of giving way, which only the pictures it changed need).
    const seen = new Map();
    const onset = (pr) => {               // an onset changes all of its lit band
      // (the ladder stacks a rung per pulse: probed with all its rungs, in the pulse's own colour -- round 2 drew the
      // rungs by forcing the pulse count to 7, which also turned the colour, and read a white rung as a cyan one)
      H.cur = { k: pr.k, allRungs: true, grp: pr.grp, merge: pr.merge, act: pr.act === "ramp" ? "on" : pr.act, onFrame: 0, N: 1, P: pr.P, t };
      H.inten = H.peak; H.on = true; H.level01 = H.peak; H.started = true; H.finished = false; H.tailAge = 0;
      H.smearFrame = pr.act === "smear" ? 0 : -1;
      H.pulsesTotal = H.pulses ? H.pulses.length : Infinity;
      this.bn = 0;
      this._geom(H, pr.at, per, t, cap);
      this._write(t, this.probeA);
      const key = recordHash(this.probeA.W, this.probeA.n), m = seen.get(key);
      if (m) { pr.w = m.w; pr.f = m.f; pr.blurBound = m.bb; return; }
      estimateArea(this.probeA.W, this.probeA.n, asp, area, 2);
      pr.w = area.window; pr.f = area.frame;
      pr.blurBound = rings ? blurBoundShare(this.probeA.W, this.probeA.n) : 0;
      if (seen.size >= 4096) seen.clear();
      seen.set(key, { w: pr.w, f: pr.f, bb: pr.blurBound });
    };
    const over = (pr) => Math.max(pr.w / (cap.window * aim), pr.f / (cap.frame * aim));
    // the life: from the first onset (and each act that lights differently), and from the worst onset when that is
    // another (a loop's worst figure or position); each simulated alone, with this hit's own plucks
    const measureLife = (worst) => {
      const res = { window: 0, frame: 0 };
      const add = (m) => { res.window = Math.max(res.window, m.window); res.frame = Math.max(res.frame, m.frame); };
      const done = new Set();
      for (const [idx, tail] of this._lifeProbes(H)) {
        setRings(idx > 0); add(this._probeLife(H, per, t, cap, idx, tail));
        if (H.pulses) done.add(`${idx}|${H.pulses[idx].P}`);
        // ... and a later pulse of a short gate also from a grid step on, where spec 3.3 moves it when the pulse before
        // was lit late (the onsets are probed there too; there a figure has formed, a pattern has stepped on)
        if (idx > 0 && H.pulses && !(H.fast && STILL_IN_FAST.has(H.pattern))) {   // (a still fast hit draws the same there)
          const p = H.pulses[idx], P = p.P + (GATES[H.gate].grid || 1 / 4);
          setRings(true); add(this._probeLife(H, per, t, cap, idx, tail, { k: idx, grp: p.grp, P }));
          done.add(`${idx}|${P}`);
        }
      }
      // ... and a short gate's worst onset, when it is another pulse than those (a later pulse of an act can light more
      // than the act's first: another colour of its cycle, another aim)
      if (H.pulses && worst && !done.has(`${worst.k}|${worst.P}`)) {
        const last = H.pulses.length - 1;
        setRings(worst.k > 0); add(this._probeLife(H, per, t, cap, worst.k, worst.k === last || !H.fast, worst));
      }
      if (!H.pulses && worst && worst !== all[0]) for (const tail of this._loopLifeTails(H)) { setRings(true); add(this._probeLife(H, per, t, cap, 0, tail, worst)); }
      return res;
    };
    let active = null, life = null, lifeOnset = 1, lifeOnsetF = 1, lives = 0;
    for (let guard = 0; guard < 96; guard++) {
      setRings(true);
      if (!active) {                       // every onset once; then the fit works on the first and the worst three
        for (const pr of all) onset(pr);
        if (fig) {                         // (a figure hit first fits each of its figures on its own)
          this._fitShapesOnce(H, all, onset, fits, over, rings);
          for (const pr of all) if (pr.shapes.length > 1 || H.shapeMul[pr.shapes[0]]) onset(pr);
        }
        active = new Set([all[0], ...all.slice().sort((a, b) => over(b) - over(a)).slice(0, 3)]);
      } else for (const pr of active) onset(pr);
      let oW = 0, oF = 0, worst = all[0];
      for (const pr of active) { if (pr.w > oW) { oW = pr.w; worst = pr; } if (pr.f > oF) oF = pr.f; }
      // The life, scaled from its last measurement by how far the onsets moved since (change goes with the light), and
      // measured again whenever that says the hit may now fit, so the fit ends on a measured life. (At most three
      // measurements a press: after that the scaled estimate decides, and the frame check backs it.)
      const scaled = (m, o0, o) => m * o / Math.max(o0, 1e-9);
      let mW = life ? scaled(life.window, lifeOnset, oW) : Infinity, mF = life ? scaled(life.frame, lifeOnsetF, oF) : Infinity;
      if (!life || (fits(oW, oF) && fits(mW, mF))) {
        if (!life || lives < 3) {
          lives++;
          life = measureLife(worst);
          lifeOnset = oW; lifeOnsetF = oF; mW = life.window; mF = life.frame;
        }
        if (fits(oW, oF) && fits(mW, mF)) {
          // ... and every other onset it can show, before it is called done (one over joins the worst and the fit goes on).
          // Giving way only takes light away -- fewer beams, heads, rungs, a dimmer or softer or sharper line -- so an
          // onset measured inside its aim stays inside it, and is not measured again. (Not quite for a fan: its spread
          // narrows as it loses beams, gathering the rest, so a fan's onset is skipped only under 3/4 of its aim.)
          setRings(true);
          const keeps = BEAM_SCALED.has(H.pattern) ? (pr) => over(pr) <= 0.75 : (pr) => over(pr) <= 1;
          let added = false;
          for (const pr of all) if (!active.has(pr) && !keeps(pr)) { onset(pr); if (!fits(pr.w, pr.f)) { active.add(pr); added = true; } }
          if (!added) break;
          continue;
        }
      }
      // A figure gives way shape by shape first (each figure whose onset is over dims on its own), so the sparse
      // figures of the hit keep their light.
      if (fig && this._fitShapes(H, active, fits, cap, aim)) continue;
      const worstW = Math.max(oW, mW), worstF = Math.max(oF, mF);
      // The order of giving way: a ringing hit rings softer (when the ringing is what is over); a crown thins to 12; a
      // fan loses outer beams (down to 3); the hit dims to 0.6 (a figure keeps its shape); a crown thins to 8, a fan to
      // 1 beam; the ladder's rungs; heads from every step; one beam a head for the cross, zigzag and scissors; fewer
      // heads a pulse (the cross, the wave, the cone); then a crown to 4 and the light down to 0.3, then to PEAK_FLOOR.
      // Each step is sized by how far over the hit is (the change goes roughly with the beam count), so it settles in a
      // few passes.
      const fanLike = BEAM_SCALED.has(H.pattern);
      const crownLike = H.pattern === "crown" || H.pattern === "star";
      const ratio = Math.min(cap.window * aim / Math.max(worstW, 1e-9), cap.frame * aim / Math.max(worstF, 1e-9));
      const fewer = (n, floor) => Math.max(floor, Math.min(n - 1, Math.floor(n * ratio)));
      const fewerEven = (n, floor) => Math.max(floor, Math.min(n - 2, 2 * Math.floor(Math.floor(n * ratio) / 2)));
      if (plucks && H.ringScale > 0.3 && lives < 3 && (mW > oW * 1.05 || mF > oF * 1.05)) {
        // the excess over the onset is the ringing's: scale the pluck by what would bring that excess under the line,
        // then measure the life again (a softer ring moves less, but its blur band may stay at its cap)
        const exW = Math.max(1e-9, mW - oW), roomW = Math.max(0, cap.window * aim - oW);
        H.ringScale = Math.max(0.3, Math.min(H.ringScale * 0.85, H.ringScale * roomW / exW));
        life = null;
        continue;
      }
      if (rings && H.blurMul > 0.25 + 1e-9 && worst.blurBound >= 0.5) {
        // most of its lines are widened past 0.1 by their blur band (the core's light spread over width + 2 blur), and
        // that band stays as wide from about 0.6 of full light down to 0.15, so dimming would not help: it sharpens
        // (spec 4.1 rule 4 keeps gated beams free of motion blur; this gives back what Vibrate added only when it must)
        H.blurMul = Math.max(0.25, H.blurMul * 0.5);
        life = null;
        continue;
      }
      if (crownLike && H.crownN > 12) { H.crownN = fewerEven(H.crownN, 12); continue; }
      if (fanLike && H.beams > 3) { const b = fewer(H.beams, 3); H.spread *= Math.pow(0.96, H.beams - b); H.beams = b; continue; }
      if (H.peak > 0.62) { H.peak = Math.max(0.6, H.peak * Math.min(0.85, ratio)); continue; }
      if (crownLike && H.crownN > 8) { H.crownN = fewerEven(H.crownN, 8); continue; }
      if (fanLike && H.beams > 1) { const b = fewer(H.beams, 1); H.spread *= Math.pow(0.96, H.beams - b); H.beams = b; continue; }
      if (H.pattern === "ladder" && (H.rungCap || 8) > 2) { H.rungCap = (H.rungCap || 8) - 1; continue; }
      // still over: every step (and push-pull side) drops its last head; then the patterns that fire a fixed pair of
      // beams per head fire one; then the heads a pulse draws are capped (the cross and the wave draw every step's heads
      // at once, so trimming the steps cannot thin them, and the cone adds its head's twin); then a crown thins to 4; then
      // the light dims to 0.3, and if it must, further (a hit is never left over its aim while it can still give way)
      const trim = (arr) => (arr.length > 1 ? arr.slice(0, -1) : arr);
      const before = JSON.stringify([H.steps, H.sides]);
      H.steps = H.steps.map(trim);
      if (H.sides) H.sides = H.sides.map(trim);
      if (JSON.stringify([H.steps, H.sides]) !== before) continue;
      if (PAIR_BEAMS.has(H.pattern) && H.beamCap > 1) { H.beamCap = 1; continue; }
      const drawn = this._headsDrawn(H);
      if (drawn > 1) { H.headCap = Math.max(1, Math.min(drawn - 1, Math.floor(drawn * ratio))); continue; }
      if (crownLike && H.crownN > 4) { H.crownN = fewerEven(H.crownN, 4); continue; }
      if (H.peak > 0.3 + 1e-9) { H.peak = Math.max(0.3, H.peak * Math.min(0.85, ratio)); continue; }
      if (H.peak > PEAK_FLOOR + 1e-9) { H.peak = Math.max(PEAK_FLOOR, H.peak * Math.min(0.85, ratio)); continue; }
      break;
    }
    // its first onset as fitted (giving way only takes light away, so the last measure bounds it): the hand-over reads
    // it when the hits before have to go out in the frame this one comes on in (_cutsClean)
    H.onsetEst = { window: all[0].w, frame: all[0].f };
    Object.assign(H, keep);
    for (let i = 0; i < this.vib.length; i++) Object.assign(this.vib[i], vibKeep[i]);
    this.bn = 0;
    this.fitBright = false; this.fitBlur = false;
    if (H.info) H.info.beams = H.beams;
  }
  // The hit alone, frame by frame from the onset of pulse `idx`, through that pulse's on-time and then either the gap
  // before the next pulse (a fast hit: a held halo may still ring there) or the tail, out to three time constants (a
  // single onset, a slow loop, a fast hit's last pulse). `at` (a loop's probe from _fitProbes, or a short gate's pulse
  // moved a grid step on) starts it at that pulse instead. Returns the worst change between consecutive frames.
  _probeLife(H, per, t, cap, idx = 0, tail = true, at = null) {
    const F = this.F, G = GATES[H.gate];
    let P0 = null, len, stepBeats = null;
    if (H.pulses) { P0 = H.pulses[idx]; len = P0.len; if (H.pulses[idx + 1]) stepBeats = H.pulses[idx + 1].P - P0.P; }
    else { const s = G.stages ? G.stages[0] : G.step; len = G.ramp ? 1 / 8 : Math.min(G.len || s / 2, s / 2); stepBeats = s; }
    const onF = Math.max(this._minOnFrames(), Math.round(len * per / F));
    const tau = Math.max(20, (H.tailBeats || 1 / 4) * per / 3);
    const gap = !tail && stepBeats ? Math.round(stepBeats * per / F) : 0;
    const L = gap ? Math.min(36, gap) : Math.min(36, onF + Math.ceil(3 * tau / F) + 1);
    const act = P0 && P0.act !== "ramp" ? P0.act : "on", P = at ? at.P : P0 ? P0.P : H.pStart;
    // (the ladder stacks a rung per pulse: its lives, like its onsets, are drawn with all its rungs)
    H.cur = { k: at ? at.k : idx, allRungs: true, grp: at ? at.grp : P0 ? P0.grp : (H.sides ? 100 : 0), merge: P0 ? P0.merge : undefined, act,
      onFrame: 0, N: onF, P, t, holdHalo: !tail && H.fast && STILL_IN_FAST.has(H.pattern) };
    H.started = true; H.smearFrame = act === "smear" ? 0 : -1;
    H.pulsesTotal = H.pulses ? H.pulses.length : Infinity;
    let a = this.probeA, b = this.probeB, have = -2;
    const worst = { window: 0, frame: 0 }, step = { window: 0, frame: 0 };
    for (let f = 0; f <= L; f++) {
      // every frame pair round the onset and the offset; elsewhere two frames in three (one pair in three): motion and
      // ringing change slowly from one pair to the next, and a press must stay cheap
      if (f > 2 && (f < onF - 1 || f > onF + 2) && f % 3 === 2) continue;
      const tf = t + f * F;
      if (f < onF) { H.on = true; H.finished = false; H.inten = H.peak * (ACT[act] || ACT.on).lvl; H.level01 = H.peak; H.tailAge = 0; }
      else if (gap) { H.on = false; H.finished = false; H.inten = 0; H.level01 = H.peak; H.tailAge = 0; }
      else {
        const age = (f - onF) * F; H.on = false; H.finished = true; H.finishT = tf - age; H.inten = H.peak * Math.exp(-age / tau); H.level01 = H.inten; H.tailAge = age;
        if (f > onF + 1 && H.inten * LEVEL_MAX < 0.1) break;      // too dim to change anything by 0.1 any more
      }
      this.bn = 0;
      this._geom(H, P + f * F / per, per, tf, cap);
      this._write(tf, b);
      if (have === f - 1) {
        estimateChange(indexKeys(a), b, this.asp, step, null, null, 3);
        if (step.window > worst.window) worst.window = step.window;
        if (step.frame > worst.frame) worst.frame = step.frame;
      }
      have = f;
      [a, b] = [b, a];                   // this frame becomes the one before
    }
    return worst;
  }
  // The lives the fit simulates: the first pulse, the first of each act that lights differently (the phrase's pluck,
  // its smears, its flash), each into the gap after it for a fast hit, and the last pulse into the tail.
  _lifeProbes(H) {
    const out = [];
    if (!H.pulses) { for (const tail of this._loopLifeTails(H)) out.push([0, tail]); return out; }
    const last = H.pulses.length - 1, seen = new Set();
    H.pulses.forEach((p, i) => {
      if (i !== 0 && (seen.has(p.act) || !(p.act === "pluck" || p.act === "smear" || p.act === "flash"))) return;
      seen.add(p.act);
      if (i !== last) out.push([i, !H.fast]);
    });
    out.push([last, true]);
    return out;
  }
  // A loop's lives from one pulse: into the gap after it (a fast loop) and into the tail. (The tail is needed even where
  // the gap drops straight to dark: a tail's colour settles toward the theme's laser colour, which may be brighter than
  // the pulse's own, so a decaying tail can light a wider band than the pulse did.)
  _loopLifeTails(H) { return H.fast ? [false, true] : [true]; }
  // The onsets a new hit can show, for the fit: a short gate's own pulses (with their groups, and each later one also a
  // grid step on); a loop's first steps and every grid point over its pattern's own cycle (PATTERN_CYCLE) -- each with
  // every group of heads it may light, on the finest grid it may run on. A loop may run on (held, or stretched by rapid
  // presses) and its picture keeps changing: the cage turns each bar, the foci, sweeps, waves and spins cycle within 16
  // beats, and a figure shows the next of its 16 figures each beat (probed at the first pulse of each beat, and where it
  // has formed: a pulse on the beat still shows the last figure, turned on). (A loop's colours that turn with the pulse
  // count -- burst, trinity, flip, chase -- are drawn at their brightest: see fitBright.)
  // Each probe: {k, grp, merge, act, P, reach}; reach = a pulse past the first steps (drawn where it lands, fast or not).
  _fitProbes(H) {
    const out = [];
    if (H.pulses) {
      // (and each later pulse a grid step on, and on again: spec 3.3 moves a pulse that would start too soon after the
      // one before to the next grid point, with the rest of the gate, and a pulse can be moved by each pulse before it
      // that was lit late -- a dropped frame -- up to three steps here; there it may show another figure or position.
      // Round 2 probed one step: a phrase's second smear moved two steps on lit a formed tetrahedron, smeared, at 16 %.)
      const g = GATES[H.gate].grid || 1 / 4;
      H.pulses.forEach((p, i) => {
        for (let m = 0; m <= Math.min(i, 3); m++) out.push({ k: i, grp: p.grp, merge: p.merge, act: p.act, P: p.P + m * g });
      });
      return out;
    }
    // (on the finest grid the loop can run on: a doubling roll's last stage, and for a rapid-tier roll the 16th grid a
    // faster stream of presses switches it to -- round 2 fitted a rapid Reverse-Bass figure on its own 1-beat grid, and
    // the presses that followed ran it in 16ths through figures and morphs the fit had never drawn)
    const G = H.loop.G, fig = H.pattern === "figure";
    let step = G.stages ? Math.min(...G.stages) : G.step;
    if (H.tier === "rapid") step = Math.min(step, GATES.roll16.step);
    const per = this.period(H.t0);
    while (step * per < FRAME_RULES.minStepMs - 1e-6) step *= 2;
    const grpOf = (j) => (H.sides ? 100 + (j % 2) : j % H.steps.length);
    // Which heads a loop's pulse lights is not tied to its position: the walk moves on with every rapid press and with
    // every pulse a mask skips, so any group can light at any grid point. Each position is probed with every group (a
    // pattern that draws the same heads whatever the group, once); a pattern whose picture also turns with the pulse
    // count (the zigzag's side, the hot beam's aim) with each of its turns.
    const nG = GROUP_FREE.has(H.pattern) ? 0 : H.sides ? 2 : H.steps.length;
    const kTurns = H.pattern === "zigzag" ? 2 : H.pattern === "hot" ? HOT_AIMS.length : 1;
    const push = (j, P, reach) => {
      for (let g = 0; g < Math.max(1, nG); g++) {
        const grp = !nG ? grpOf(j) : H.sides ? 100 + ((j + g) % 2) : (j + g) % nG;
        for (let dk = 0; dk < kTurns; dk++) out.push({ k: j + dk, grp, act: "on", P, reach });
      }
    };
    const nLoop = Math.min(8, Math.max(H.sides ? 2 : H.steps.length, 4));
    for (let j = 0; j < nLoop; j++) push(j, H.pStart + j * step, false);
    // ... every grid point over the pattern's own cycle (a moving picture is somewhere else at each step: the wave's
    // phase, the sweep's swing, the foci, the spin; the cage only turns on the bar line), and for a figure the first
    // pulse of each beat over its 16 figures
    const [cyc = 0, res = 0] = PATTERN_CYCLE[H.pattern] || [];
    const every = Math.max(1, Math.round(res / step));
    for (let j = nLoop; j * step < Math.min(16, cyc) - 1e-9; j++) if (j % every === 0) push(j, H.pStart + j * step, true);
    const b0 = Math.floor(H.pStart + 1e-9);
    for (let b = 0; fig && b < 16; b++) {
      const js = [];          // the loop's grid points in beat b
      for (let j = Math.max(0, Math.ceil((b0 + b - H.pStart) / step - 1e-9)); H.pStart + j * step < b0 + b + 1 - 1e-9; j++) js.push(j);
      if (!js.length) continue;
      const pick = [js[0]];
      if (fig) {           // ... and where the beat's figure has formed (a pulse on the beat shows the last one, turned on)
        const formed = js.find((q) => frac(H.pStart + q * step + 1e-9) >= 0.25 - 1e-6);
        if (formed !== undefined && formed !== js[0]) pick.push(formed);
      }
      for (const j of pick) push(j, H.pStart + j * step, true);
    }
    return out;
  }
  // the figure(s) a figure hit shows at beat position P (as _pattern draws it): [figure] once formed, [from, to] while
  // it morphs
  _figureAt(H, P) {
    const beat = Math.max(0, Math.floor(P - Math.floor(H.pStart + 1e-9) + 1e-9));
    const cur = H.shapes[beat % H.shapes.length], from = beat === 0 ? (H.shapeFrom || cur) : H.shapes[(beat - 1) % H.shapes.length];
    const m = smooth(frac(P) / 0.25);
    return from === cur || m >= 1 - 1e-9 ? [cur] : m <= 1e-9 ? [from] : [from, cur];
  }
  // A figure hit's figures fitted one by one, before the rest of the fit (see _fitHit). Each figure (by name) whose own
  // worst onset (of `probes`, measured, where it shows alone) is over its aim takes the brightest level that fits there,
  // found by halving (four tries between 5 % and all of the hit's light); a ringing figure is also tried with its blur
  // band at a quarter (the core's light spread over width + 2 blur is what widens a dim ringing line past 0.1), and the
  // sharper choice wins when it keeps at least a quarter more light. A ringing figure's onset is fitted to 85 % of the
  // aim, leaving its ringing (lines moving while lit) room, so the ring need not be cut to fit. What a figure took is
  // remembered for the next hit like it (same theme, brightest colour, figure, gate speed, ringing, light and size) and
  // tried first; every onset is still measured before the hit is done. `onset(pr)` measures a probe into pr.w and pr.f.
  _fitShapesOnce(H, probes, onset, fits, over, rings) {
    const worst = new Map();
    for (const pr of probes) {
      if (pr.shapes.length !== 1) continue;
      const w = worst.get(pr.shapes[0]);
      if (!w || over(pr) > over(w)) worst.set(pr.shapes[0], pr);
    }
    const room = rings ? 0.85 : 1, fitsR = (pr) => fits(pr.w / room, pr.f / room);
    // (the context: the brightest colour the hit's colour mode can emit, not the mode itself, so modes that light alike
    // share what they learned)
    const C = H.col || this.col, Y = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    const cols = H.colour === "mono" ? [C.L1] : H.colour === "hotcore" ? [C.L1, C.W] : H.colour === "flip" ? C.flicker
      : H.colour === "trinity" ? C.triple : H.colour === "burst" ? C.burst : [C.L1, C.L2];
    const ctx = `${Math.round(Math.max(...cols.map(Y)) * 20)}|${H.fast ? 1 : 0}|${rings ? 1 : 0}|${Math.round(H.peak * 20)}|${Math.round(H.vel * 16)}|${H.level >= 2 ? 1 : 0}|${Math.round((this.asp || 1) * 100)}`;
    for (const [s, pr] of worst) {
      if (fitsR(pr)) continue;
      const M = H.shapeMul[s] || (H.shapeMul[s] = { lvl: 1, blur: 1 });
      const key = `${s}|${ctx}`, known = this.shapeFits.get(key);
      if (known) {
        M.lvl = known.lvl; M.blur = known.blur; onset(pr);
        if (fitsR(pr)) continue;
        // (this hit turns the figure to an angle that needs less: the level is found below the one remembered, and the
        // lower one is remembered, so the memory settles on what every angle seen needs)
        let lo = 0.05, hi = known.lvl;
        for (let i = 0; i < 3; i++) { M.lvl = Math.sqrt(lo * hi); onset(pr); if (fitsR(pr)) lo = M.lvl; else hi = M.lvl; }
        M.lvl = lo; known.lvl = lo;
        onset(pr);
        continue;
      }
      // the brightest level in [lo, 1] that fits with this blur band (halving, `tries` times; lo is taken to fit)
      const search = (blur, lo = 0.05, tries = 4) => {
        M.blur = blur;
        M.lvl = 1; onset(pr);
        if (fitsR(pr)) return 1;
        let hi = 1;
        for (let i = 0; i < tries; i++) { M.lvl = Math.sqrt(lo * hi); onset(pr); if (fitsR(pr)) lo = M.lvl; else hi = M.lvl; }
        return lo;
      };
      let plain = 0, sharp = 0;
      if (rings) {
        // (the sharp figure first: the plain one wins only with more than 4/5 of its light, which one try can rule out)
        sharp = search(0.25);
        const bar = sharp / 1.25;
        M.blur = 1; M.lvl = bar; onset(pr);
        if (fitsR(pr)) plain = search(1, bar, 3);
      } else plain = search(1);
      if (sharp > 1.25 * plain) { M.blur = 0.25; M.lvl = sharp; } else { M.blur = 1; M.lvl = plain; }
      if (this.shapeFits.size >= 256) this.shapeFits.clear();
      this.shapeFits.set(key, { lvl: M.lvl, blur: M.blur });
      onset(pr);
    }
  }
  // One step for a figure hit whose onsets in `active` are still over (an onset the first search did not see, such as a
  // morph): each such figure's level drops in proportion to how far over it is (to 5 % at least). True if any moved.
  _fitShapes(H, active, fits, cap, aim) {
    let moved = false;
    const done = new Set();
    for (const pr of active) {
      if (!pr.shapes || fits(pr.w, pr.f)) continue;
      const r = Math.min(cap.window * aim / Math.max(pr.w, 1e-9), cap.frame * aim / Math.max(pr.f, 1e-9));
      for (const s of pr.shapes) {
        if (done.has(s)) continue;
        done.add(s);
        const M = H.shapeMul[s] || (H.shapeMul[s] = { lvl: 1, blur: 1 });
        if (M.lvl > 0.05 + 1e-9) { M.lvl = Math.max(0.05, M.lvl * Math.min(0.85, r)); moved = true; }
      }
    }
    return moved;
  }

  // Short gates anchor on the hit (spec 3.3): a grid point of the gate's step 60 ms or less ahead -> the first pulse
  // waits for it; otherwise pulse 1 fires now and the rest land on the following grid points, never closer than 83 ms.
  _anchorShort(H, G, pH, per) {
    const g = G.grid;
    const next = Math.ceil(pH / g - 1e-9) * g;
    const out = [];
    if ((next - pH) * per <= 60) {
      for (const p of G.pulses) out.push({ P: next + p.at, len: p.len, act: p.act });
    } else {
      out.push({ P: pH, len: G.pulses[0].len, act: G.pulses[0].act });
      if (G.pulses.length > 1) {
        let base = next;
        while ((base - pH) * per < FRAME_RULES.minStepMs) base += g;
        const a1 = G.pulses[1].at;
        for (let k = 1; k < G.pulses.length; k++) out.push({ P: base + G.pulses[k].at - a1, len: G.pulses[k].len, act: G.pulses[k].act });
      }
    }
    for (let k = 0; k < out.length; k++) out[k].grp = out[k].act === "flash" ? -1 : k % H.aLen;
    if (H.call) {       // call and response: bank B answers each pulse half a beat later
      const bLen = H.steps.length - H.aLen;
      const resp = out.map((p, k) => ({ P: p.P + 1 / 2, len: p.len, act: p.act === "flash" ? "flash" : p.act, grp: p.act === "flash" ? -1 : H.aLen + (k % Math.max(1, bLen)) }));
      out.push(...resp);
      out.sort((a, b) => a.P - b.P);
      // two pulses closer than a step merge (the answer that lands on a call's own pulse)
      for (let i = out.length - 1; i > 0; i--) {
        if ((out[i].P - out[i - 1].P) * per >= FRAME_RULES.minStepMs) continue;
        const a = out[i - 1], b = out[i];
        a.merge = [...(a.merge || [a.grp]), ...(b.merge || [b.grp])];
        a.grp = -2;
        out.splice(i, 1);
      }
    }
    H.pulses = out;
    H.pStart = out[0].P;
    H.tailBeats = G.tail;
  }
  // Loops anchor on the grid: the next grid point of their step, or the last one if it passed within 30 ms.
  _startLoop(H, G, pH, per, spanBeats, startAfter = -Infinity) {
    const step = G.stages ? G.stages[0] : G.step;
    const off = G.offset || 0;
    let base = Math.floor((pH - off) / step) * step + off;
    if ((pH - base) * per > 30) base += step;
    while (base < startAfter - 1e-9) base += step;
    H.pStart = base;
    H.loop = { G, P: base, startP: base, j: 0, endP: spanBeats === Infinity ? Infinity : base + spanBeats, fastRun: 0, rest: 0,
      maskIdx: H.deal.mask % (G.masks ? G.masks.length : 1), lastStep: step };
    H.tailBeats = (G.len || step) / 2;
    if (G.sides) {     // push-pull sides: the two banks when the hit spans both, else left and right
      const all = [...new Set(H.steps.flat())];
      const A = all.filter((h) => HEADS[h].bank === "A"), B = all.filter((h) => HEADS[h].bank === "B");
      H.sides = A.length && B.length ? [A, B] : [all.filter((h) => HEADS[h].side <= 0), all.filter((h) => HEADS[h].side > 0)];
      if (!H.sides[1].length) H.sides = [all, all];
    }
  }
  // the next slot of a loop (computed when it becomes next; the step uses the tempo at that moment)
  _loopSlot(H, per, t) {
    const L = H.loop, G = L.G;
    if (L.P >= L.endP - 1e-9) return null;
    if (L.slot && L.slot.P === L.P) return L.slot;
    let s = G.stages ? G.stages[Math.min(G.stages.length - 1, Math.floor((L.P - L.startP) / G.stageBeats + 1e-9))] : G.step;
    if (H.stepOverride) s = Math.min(s, H.stepOverride);
    while (s * per < FRAME_RULES.minStepMs - 1e-6) s *= 2;           // the frame rule: half speed when too fast
    s = Math.max(s, this._minStep(t));
    const fastLimit = this.o.section === "build" ? 16 : 8;            // fast rolls: 4 bars in a build, 2 elsewhere
    if (L.rest > 0) s = Math.max(s, 1 / 2);
    let fire = true;
    if (G.masks) { const m = G.masks[L.maskIdx]; fire = m[L.j % m.length] === "x"; }
    if (G.cutAt !== undefined && (L.P - L.startP) % 4 >= G.cutAt - 1e-9) fire = false;
    const len = G.ramp ? s : Math.min(G.len || s / 2, s / 2);
    let grp;
    if (G.sides) grp = 100 + (L.j % 2);
    else if (H.call) { const bLen = H.steps.length - H.aLen; grp = L.j % 2 === 0 ? (H.walk + (L.j >> 1)) % H.aLen : H.aLen + (H.walk + (L.j >> 1)) % Math.max(1, bLen); }
    else grp = (H.walk + H.fired) % H.steps.length;
    L.slot = { P: L.P, len, act: G.ramp ? "ramp" : "on", grp, fire, step: s };
    return L.slot;
  }
  _loopAdvance(H) {
    const L = H.loop, sl = L.slot, s = sl.step;
    if (L.rest > 0) L.rest -= s;
    else if (s <= 1 / 4 + 1e-9) { L.fastRun += s; if (L.fastRun >= (this.o.section === "build" ? 16 : 8) - 1e-9) { L.rest = 4; L.fastRun = 0; } }
    else L.fastRun = 0;
    L.P += s; L.j++; L.lastStep = s; L.slot = null;
  }

  // ------------------------------------------------------------------------------------------------- the frame --
  frame(t, opts = {}) {
    const out = this.out;
    if (opts.aspect) this.o.aspect = opts.aspect;
    out.events.length = 0;
    for (const e of this.pending) out.events.push(e);
    this.pending.length = 0;
    // The strings' clock: it follows the frame clock but never steps more than 1.2 frames at once, catching up 0.2 of a
    // frame each frame. A dropped frame would otherwise double a ringing line's step, and with it the change (the fit
    // measures the ringing at the display's own rate). After a stall (100 ms or more behind) it resyncs at once.
    this.ringT = this.ringT === null || t - this.ringT >= 100 ? t : Math.min(t, this.ringT + 1.2 * this.F);
    if (this.tPrev !== null) {
      const dt = t - this.tPrev;
      if (dt > 3 && dt < 100) this.F = this.F * 0.9 + dt * 0.1;
    }
    this.tPrev = t;
    this.nowT = t;
    this.frameIdx++;
    this.inFrame = true;              // (until the frame is built: see _nowFrame)
    const per = this.period(t);
    const pos = this._commitPos(t);
    const posE = this._evalPos(t, pos);
    this.posE = posE;
    // A new aspect (the window resized, fullscreen toggled) re-lays every line out: a hit fitted at the old one is
    // fitted again at the new one (its levers only take light away). Round 2 kept the old fit: a held crown roll fitted
    // in a 21:9 window lit 15.2 % of a window at every pulse once the window turned portrait.
    const aspChanged = this.asp !== undefined && Math.abs(this.o.aspect - this.asp) > 1e-3;
    this.asp = this.o.aspect;
    if (aspChanged) for (const H of this.hits) if (!H.done) this._fitHit(H, per, t);

    // hold: the pad still down half a beat after the press (200 ms with no clock) -> the section's loop
    const holdMs = this._clockOK(t) ? 0.5 * per : 200;
    const ph = this.padHit;
    if (this.padDown && ph && !ph.holdSpawned && !ph.done && ph.tier !== "rapid" && ph.tier !== "held" && t - this.padT >= holdMs) {
      ph.holdSpawned = true;
      this._spawnHold(ph, t, per);
    }

    this.bn = 0;
    let running = null, anyFast = false, gateRunning = false, maxLevel = 0;
    for (let i = this.hits.length - 1; i >= 0; i--) {
      const H = this.hits[i];
      this._evalHit(H, t, posE, per);
      if (H.done) continue;
      if (!running && H.started) running = H;
      // a fast hit keeps the fast caps through its tail: nothing pops in (but not through the half of a tail going out
      // under a newer hit's onset: it lights nothing measurable any more, and the newer hit is fitted to its own caps)
      if (H.started && H.fast && H.halveF !== this.frameIdx) anyFast = true;
      if (H.started && !H.finished && (H.pulsesTotal > 1 || H.loop)) gateRunning = true;
      maxLevel = Math.max(maxLevel, H.tier === "hero" ? 3 : H.level || 1);
    }
    this.hits = this.hits.filter((h) => !h.done);
    // build the beams, newest hit first (so caps keep the newest)
    const cap = anyFast ? BUDGET.fast : BUDGET.single;
    const headsUsed = new Set();
    let beamTotal = 0;
    for (let i = this.hits.length - 1; i >= 0; i--) {
      const H = this.hits[i];
      if (!H.started || H.level01 <= 0.002 || H.halveF === this.frameIdx) continue;   // (a halved tail: _writeHalved)
      const before = this.bn;
      let thinSeen = 0;
      this._geom(H, posE, per, t, cap);
      // caps: lit heads and lit beams (figure lines are line art; held-halo beams have no core)
      let kept = before;
      for (let b = before; b < this.bn; b++) {
        const B = this.beams[b];
        if (B.kind === KIND.BEAM) {
          if (B.pri > H.trimPri) continue;                         // trimmed once, trimmed for good: nothing pops back
          if (H.thin && (thinSeen++ & 1)) continue;
          if (!headsUsed.has(B.h) && headsUsed.size >= cap.heads) continue;
          if (beamTotal >= cap.beams) continue;
          headsUsed.add(B.h); beamTotal++;
        }
        if (kept !== b) { const tmp = this.beams[kept]; this.beams[kept] = B; this.beams[b] = tmp; }
        kept++;
      }
      this.bn = kept;
    }
    this._emit(anyFast, t);
    out.t = t;
    out.solo = gateRunning ? 0.3 : 1;
    out.pad.tier = running ? maxLevel : 0;
    out.pad.level = running ? TIER_LED[maxLevel] || 0.6 : 0;
    const c = this.col.L1; out.pad.rgb[0] = c[0]; out.pad.rgb[1] = c[1]; out.pad.rgb[2] = c[2];
    out.gate = running ? running.gate : ""; out.pattern = running ? running.pattern : ""; out.tier = running ? running.tier : "";
    out.bank = running ? running.bank : ""; out.order = running ? running.order : ""; out.colour = running ? running.colour : "";
    this.inFrame = false;
    return out;
  }

  _spawnHold(src, t, per) {
    if (src.loop) {                 // the press already runs a loop (a fixed loop gate): hold it open until release
      src.loop.endP = Infinity;
      src.finished = false;
      src.held = true;
      src.info.hold = src.gate;
      return src;
    }
    const sec = this.o.section;
    let gate = "doubling", pattern = src.pattern;
    if (sec === "drop" || sec === "climax" || sec === "groove") gate = src.vel > 0.8 ? "roll16" : "pushpull";
    else if (sec === "anti" || sec === "screech") gate = "military";
    else if (sec === "break" || sec === "piano" || sec === "outro" || sec === "intro") { gate = "roll8"; if (!this.o.shapeMode) pattern = "wave"; }
    if (this.o.gateMode !== "auto" && GATES[this.o.gateMode] && GATES[this.o.gateMode].kind === "loop") gate = this.o.gateMode;
    const deal = { ...src.deal, pattern, gate };
    // The loop starts after the press's own short gate, on the grid, and runs until release. It is anchored there
    // BEFORE it is fitted (it used to be fitted where a plain press would start it and moved after, so every probe of
    // a moving pattern or a figure stood at the wrong beat). The press's own hit hands over: what is left of it (its
    // tail) goes dark in the frame before the loop's first pulse, which lights on its beat, so the press's light
    // (fitted to the single budget) never goes dark under the loop's fast one.
    // ... and on a grid point it can still light ON TIME: one not yet due in this frame (the hold is the engine's own
    // timing, not a late hand, so spec 3.3's "or immediately if a grid point passed within 30 ms" has nothing to forgive;
    // and the frame before the loop's first pulse is the one the press's tail goes out in). The hold is known half a
    // beat after the press, which can be just after the loop's first grid point (a press on the beat with a one-two:
    // the push-pull's first point is half a beat on): rounds 1-3 then lit that point 33-45 ms late; now the loop
    // starts on the next one.
    const after = Math.max(src.pulses ? src.pulses[src.pulses.length - 1].P + 1 / 4 : -Infinity, this.posE + 1e-6);
    const H = this._spawn(deal, { t, pH: this.posAt(t), per, vel: src.vel, tier: "held", level: Math.max(2, src.level), gate,
      fast: this._gateFast(gate, per), kind: "held", spare: src, loopSpan: Infinity, loopAfter: after });
    src.fading = false;
    if (!this.padDown) H.loop.endP = H.loop.P;
    src.info.hold = gate;
    H.info.tier = "held"; H.info.from = src.id;
    this._log(H.info);
    return H;
  }

  // the pulse state of one hit this frame
  _evalHit(H, t, posE, per) {
    // a hit put out by a newer one goes dark in this frame (see _handOver); a hit choked before it ever lit is simply
    // gone; a new hit waits until the hits before it are dark (they are evaluated after it, so their last lit frame and
    // its first never coincide)
    if (H.cut || H.halveF < this.frameIdx || (!H.started && H.choked)) { H.on = false; H.inten = 0; H.level01 = 0; H.done = true; return; }
    if (!H.started && H.waitFor) {
      const wait = H.waitFor.filter((h) => !h.done);
      if (wait.length && !this._handOver(H, wait, t, posE, per)) { H.on = false; H.inten = 0; H.level01 = 0; return; }
      H.waitFor = null;
    }
    const F = this.F;
    const minOn = Math.max(1, Math.ceil(FRAME_RULES.minOnMs / F - 1e-6)), minOff = Math.max(1, Math.ceil(FRAME_RULES.minOffMs / F - 1e-6));
    let newest = null, newestStep = 1 / 4;
    // reach every pulse whose onset the picture has passed; fire only the newest (a jump drops the skipped ones). A
    // choked hit starts nothing new.
    if (H.choked) { /* no new pulses */ }
    else if (H.pulses) {
      while (H.pi < H.pulses.length && H.pulses[H.pi].P <= posE) { newest = H.pulses[H.pi]; H.pi++; }
      if (newest) newestStep = H.pi < H.pulses.length ? H.pulses[H.pi].P - newest.P : 1 / 4;
    } else if (H.loop) {
      for (let guard = 0; guard < 64; guard++) {
        const sl = this._loopSlot(H, per, t);
        if (!sl || sl.P > posE) break;
        if (sl.fire) newest = { ...sl };
        newestStep = sl.step;
        this._loopAdvance(H);
      }
    }
    H.pulsesTotal = H.pulses ? H.pulses.length : Infinity;
    if (newest && H.cur) {          // a pulse too close to the last one (a late first pulse, a jump): never a doubled flash
      const since = this.frameIdx - H.cur.onFrame;
      if (since - H.cur.N < minOff || since < Math.ceil(FRAME_RULES.minStepMs / F - 1e-6)) {
        if (H.pulses) {
          // Spec 3.3: a pulse that would start less than a step (83 ms) after the previous one MOVES to the next grid
          // point, and the rest of the gate moves with it, so the rhythm keeps its shape and no pulse is lost. (The
          // usual cause: a press so close to the beat that pulse 1 could only be lit late, while pulse 2 is on time.)
          // A loop simply goes on to its next slot.
          const idx = H.pulses.indexOf(newest), g = GATES[H.gate].grid || 1 / 4;
          for (let k = idx; k < H.pulses.length; k++) H.pulses[k] = { ...H.pulses[k], P: H.pulses[k].P + g };
          H.pi = idx;
        }
        newest = null;
      }
    }
    if (newest && !H.fading) {
      const lead = this.o.onsetRule === "nearest" ? F / 2 : F;
      const late = (posE - newest.P) * per - lead - this.o.presentLagMs;
      if (!H.started || late <= Math.max(newestStep * per / 4, 1.5 * F) + 1e-6) {
        let N = Math.max(minOn, Math.round(newest.len * per / F));
        // the next pulse's onset frame: leave at least minOff dark frames before it
        // (a hit a newer one takes over from leaves the gap before that one's first pulse: takeoverP)
        const nextP = H.pulses ? (H.pi < H.pulses.length ? H.pulses[H.pi].P : H.takeoverP ?? null)
          : H.loop ? (H.loop.P < H.loop.endP ? H.loop.P : H.takeoverP ?? null) : null;
        // (counted from THIS frame, not from the pulse's grid time: a pulse lit late must still leave the full gap)
        if (nextP !== null) { const framesTo = Math.ceil((nextP - posE) * per / F - 1e-6); N = Math.max(minOn, Math.min(N, framesTo - minOff)); }
        // the halo hold: this pulse's halo was already held lit if the last pulse held it over these same heads
        const prev = H.cur;
        const sameAsPrev = !!(prev && prev.holdHalo && sameHeads(this._litHeads(H, prev.grp, prev), this._litHeads(H, newest.grp, newest)));
        if (H.velNext !== undefined) { H.vel = H.velNext; H.velNext = undefined; }      // a rapid press's velocity (see hit)
        H.cur = { ...newest, onFrame: this.frameIdx, N, k: H.fired, t, sameAsPrev, holdHalo: false };
        H.fired++;
        if (!H.started) H.onsetFrame = this.frameIdx;
        H.started = true;
        H.finished = false;
        H.lastPulseP = newest.P;
        // ... and it holds through the coming gap only if the next pulse fires the same heads (else it goes off with
        // its core, so a walk to other heads changes one step's own light, never a held halo plus a new one)
        if (H.fast) {
          let nx = null;
          if (H.pulses) nx = H.pi < H.pulses.length ? H.pulses[H.pi] : null;
          else if (H.loop) nx = this._loopSlot(H, per, t);
          H.cur.holdHalo = !!(nx && STILL_IN_FAST.has(H.pattern) && sameHeads(this._litHeads(H, H.cur.grp, H.cur), this._litHeads(H, nx.grp, nx)));
        }
        this.out.events.push({ type: "pulse", hit: H.id, k: H.cur.k, act: newest.act });
        this._onAct(H, newest, t);
      }
    }
    const on = !!(H.cur && this.frameIdx - H.cur.onFrame < H.cur.N);
    // choked: once its lit pulse has had its time, the hit goes dark at once (a halved tail: the frame after its half)
    if (H.halveF === this.frameIdx) { H.on = false; H.inten = H.halfInten; H.level01 = H.halfLevel; H.tailAge = t - H.finishT; return; }
    if (H.choked && !on) { H.on = false; H.inten = 0; H.level01 = 0; H.done = true; return; }
    const exhausted = H.pulses ? H.pi >= H.pulses.length : (H.loop && H.loop.P >= H.loop.endP - 1e-9);
    if (exhausted && !on && H.started && !H.finished) {
      // The tail follows the last pulse. A loop that runs out while it is DARK (released, or handed over, in the gap
      // between two pulses) has already gone off: it must not light its last picture again as a "tail" (that was an
      // extra, off-grid flash of the whole picture). Only a halo held lit through the gap fades out from where it is.
      if (!H.on && !(H.fast && H.cur && H.cur.holdHalo)) { H.on = false; H.inten = 0; H.level01 = 0; H.done = true; return; }
      H.tailGlowOnly = !H.on;
      H.finished = true; H.finishFrame = this.frameIdx; H.finishT = t;
      H.tailTau = Math.max(20, H.tailBeats * per / 3);
    }
    if (!H.started && exhausted) { H.done = true; return; }
    let inten = 0;
    if (on) {
      const a = ACT[H.cur.act] || ACT.on;
      inten = H.peak * a.lvl;
      if (H.cur.act === "ramp") { const x = (this.frameIdx - H.cur.onFrame + 1) / Math.max(1, H.cur.N); inten *= x * x; }
    } else if (H.finished && !H.tailGlowOnly) {
      inten = H.peak * Math.exp(-(t - H.finishT) / H.tailTau);
    }
    let level = H.started ? (H.finished ? H.peak * Math.exp(-(t - H.finishT) / H.tailTau) : H.peak) : 0;
    if (H.fading) { const f = Math.exp(-Math.max(0, t - H.fadeT) / (H.fadeTau || 40)); inten *= f; level *= f; }
    H.on = on;
    H.inten = inten;
    H.level01 = level;
    H.tailAge = H.finished && !on ? t - H.finishT : 0;
    if (H.started && (H.finished || H.fading) && level < 0.004) H.done = true;
  }
  // the hit's first pulse is due at the frame judged at posE (it would light now if nothing held it back)
  _firstDue(H, posE, per, t) {
    if (H.pulses) return H.pi < H.pulses.length && H.pulses[H.pi].P <= posE;
    const sl = H.loop ? this._loopSlot(H, per, t) : null;
    return !!(sl && sl.P <= posE);
  }
  // THE HAND-OVER, AHEAD OF TIME. A new hit H waits for the hits before it (`wait`, those not dark yet) to be dark, so
  // that one hit's light going off and the next one's coming on never land in one frame unmeasured. Round 3 put them
  // out only in the frame H's first pulse was due: they went dark there and H lit a frame late (a held press's loop
  // 40 of 40 times at 150 BPM; Bar Marker taps 1.25 beats apart 360 of 400), breaking spec 3.3 (loops on the grid; a
  // slightly early hand lands on the beat) and A2's never late. Now:
  //   - in the frame BEFORE the first pulse is due (judged at the next frame's position, with half a frame to spare for
  //     a frame that comes late), the hits it takes over from go out, so that frame is the dark one and the beat's frame
  //     lights on time (a lit pulse keeps its 40 ms first, and _takeOver has already ended it the frame rules' gap
  //     before the new pulse);
  //   - when the first pulse is due now and they are not dark yet (the press came too close to its beat to leave a frame
  //     between), they go out in this very frame and H lights with them gone -- if what is left of them changes nothing
  //     measurable as it goes (a 1-3 % tail lights no pixel by 0.1), or if it and H's own onset, measured (the fit's
  //     estimate of it), fit the budget together with a tenth to spare; or, too bright for that but dim enough, it
  //     goes out in two halves that each change nothing measurable, the first under H's onset (see _cutsClean).
  //     Otherwise (a pulse still serving its minimum on-time; a bright tail too big to go with H's onset) H waits a
  //     frame, as before: that frame cannot be both dark and on time.
  // Returns true when H may light now.
  _handOver(H, wait, t, posE, per) {
    if (this._firstDue(H, posE, per, t)) {
      const how = this._cutsClean(H, wait);
      if (how === "cut") { for (const h of wait) this._cut(h); return true; }
      if (how === "halve") {
        // (each is drawn this frame as last frame's records at half their level -- _writeHalved -- and is gone the next:
        // _evalHit)
        for (const h of wait) { h.choked = true; h.halveF = this._nowFrame(); h.halfInten = 0.5 * h.inten; h.halfLevel = 0.5 * h.level01; }
        return true;
      }
      if (H.handover) for (const h of H.handover) this._choke(h);
      return false;
    }
    if (H.handover && this._firstDue(H, this._nextPos(t, posE, per), per, t)) for (const h of H.handover) this._choke(h);
    return false;
  }
  // the position the NEXT frame will be judged at (as _evalPos), from a frame one and a half frames on: a frame that
  // comes a little late still finds the hits before already dark
  _nextPos(t, posE, per) {
    const tN = t + 1.5 * this.F, c = this.clock;
    if (this._clockOK(t) && typeof c.posAt === "function") {
      const s = this.o.onsetRule === "nearest" ? this.F / 2 : this.F;
      const p = c.posAt(tN + this.o.presentLagMs + s - 1e-6);
      if (Number.isFinite(p)) return Math.max(p, posE);
    }
    return posE + 1.5 * this.F / per;
  }
  // May the hits in `wait` go out with H's first pulse coming on in this frame? Never mid-way through a pulse's minimum
  // on-time. "cut" (out in this frame) when their light in the frame last drawn changes nothing measurable as it goes
  // (no pixel by 0.1), or when that change and H's onset fit the budget (the fast one if H or any of them is fast)
  // together with a tenth to spare (two lit bands add at most their sum, in any window and in the frame). "halve" when
  // they are dim enough to go out in two steps that each change nothing measurable: halving every line's level (its
  // core, halo and heat) moves no pixel by 0.1, and leaves it under 0.1 (core) and its halo under 0.2, so it lights
  // nothing measurable any more under H's onset and goes out the next frame unmeasured too. Else false: H waits.
  _cutsClean(H, wait) {
    const now = this._nowFrame(), minOn = this._minOnFrames();
    for (const h of wait) if (h.on && h.cur && now - h.cur.onFrame < minOn) return false;
    const D = this._drawnLight(wait);
    if (!D || (D.area.window <= 1e-9 && D.area.frame <= 1e-9)) return "cut";
    // (a fast hit's light going dark is a fast gate's change: judged on the fast budget, though the frame it goes out in
    // has no fast hit left to say so)
    const cap = H.fast || wait.some((h) => h.fast) ? BUDGET.fast : BUDGET.single, e = H.onsetEst;
    if (e && D.area.window + e.window <= 0.9 * cap.window && D.area.frame + e.frame <= 0.9 * cap.frame) return "cut";
    if (D.drop < 0.1 && D.half < 0.1 && D.glowY < 0.4) return "halve";
    return false;
  }
  // The light the hits `hs` drew in the frame last drawn: area = what they light (0.1 or more), as estimateArea; glowY =
  // the brightest halo luminance among their lines; half = the brightest core level once halved, drop = the most a
  // core's level falls when halved (the white-core luminance moves with the heat, which halves too) -- each at a line's
  // bright end with its blur band left out (the most a pixel of it can hold), summed over the hits (their lines may
  // cross). null when they drew nothing.
  _drawnLight(hs) {
    const ids = new Map(hs.map((h) => [h.id, { glowY: 0, half: 0, drop: 0 }])), src = this.drawn, dst = this.probeB, Wa = src.W;
    let n = 0;
    for (let i = 0; i < src.n; i++) {
      // (a record's key carries its hit: see _write)
      const m = ids.get(Math.floor(src.keys[i] / 8192));
      if (!m) continue;
      const o = i * W_FLOATS, I = Wa[o + W.I], w = Wa[o + W.WIDTH], gY = Wa[o + W.GLOW] * tintLuma(Wa, o);
      const h2 = Wa[o + W.HEAT] / 2, kw2 = h2 * h2 / (1 + h2 * h2), mx = Math.max(Wa[o + W.R], Wa[o + W.G], Wa[o + W.B]);
      const core = coreLevel(I, hotLuma(Wa, o), gY, w, 0), half = coreLevel(I / 2, (1 - kw2) * tintLuma(Wa, o) + kw2 * mx, gY / 2, w, 0);
      m.glowY = Math.max(m.glowY, gY); m.half = Math.max(m.half, half); m.drop = Math.max(m.drop, core - half);
      dst.W.set(Wa.subarray(o, o + W_FLOATS), n * W_FLOATS);
      n++;
    }
    if (!n) return null;
    const D = { area: estimateArea(dst.W, n, this.asp || this.o.aspect, { frame: 0, window: 0 }), glowY: 0, half: 0, drop: 0 };
    for (const m of ids.values()) { D.glowY += m.glowY; D.half += m.half; D.drop += m.drop; }
    return D;
  }
  _onAct(H, p, t) {
    const heads = this._litHeads(H, p.grp);
    // (a hit the fit found too lively for its budget plucks softer: ringScale)
    const plucks = (amp) => { for (const h of (H.pattern === "figure" || H.pattern === "crown" || H.pattern === "star" ? [HERO_HEAD] : heads)) this._pluck(h, t, amp * H.ringScale, VIB.MAX_PX * H.ringScale); };
    if (p.act === "pluck") { plucks(VIB.AMP_PX * (0.6 + 0.4 * H.vel)); this.out.events.push({ type: "pluck", head: heads.length ? HEADS[heads[0]].name : "HERO" }); }
    else if (p.act === "smear") { H.smearFrame = this.frameIdx; plucks(VIB.AMP_PX * 0.4); }
    // (Vibrate switched on while a hit runs reaches it at its next press, not mid-hit: a hit fitted still would ring
    // past its fit -- a 16th roll fitted with Vibrate off rang at the full 18 px a second later)
    else if (this.o.vibrate && H.plucks) plucks(VIB.AMP_PX * (0.5 + 0.5 * H.vel));
    if (p.act === "flash") this.out.events.push({ type: "flash", level: H.peak });
  }
  // A pluck adds a ring to the string: the rings already there go on ringing (strings superpose; replacing one ring
  // with another made the string jump), the new one rises through its attack, and the sum never swings past the
  // plucking hit's cap (MAX_PX, less for a hit the fit made pluck softer).
  _pluck(h, t, amp, capPx = VIB.MAX_PX) {
    const v = this.vib[h];
    const offS = v.offT === null ? null : Math.max(0, (t - v.offT) / 1000);
    let cur = 0;
    const keep = [];
    for (const r of v.rings) {
      const age = (t - r.t0) / 1000, now = age < 6 ? vibModes(age, r.amp, offS)[0] * ringAttack(age) : 0;
      if (now < 0.3) continue;                                      // too small to see go
      // Vibrate was switched off and this pluck turns it on again: carry each ring on at the size it has damped to
      if (offS !== null) r.amp *= Math.exp(-offS / VIB.TAU_OFF_S);
      cur += now; keep.push(r);
    }
    const add = Math.min(amp, capPx - cur);
    if (add >= 0.5) keep.push({ t0: t, amp: add });
    v.rings = keep.slice(-4);
    v.t0 = t; v.amp = add > 0 ? add : 0;           // the newest pluck (for readers of a single ring)
    v.offT = null;
  }
  // the heads a pulse lights: its step, both push-pull sides' one, a merged call+answer, or every head (flash)
  _litHeads(H, grp, p = H.cur) {
    if (grp === -1) return [...new Set(H.steps.flat())].slice(0, H.fast ? BUDGET.fast.heads : BUDGET.single.heads);
    if (grp === -2 && p && p.merge) return [...new Set(p.merge.flatMap((g) => (g >= 0 ? H.steps[g] || [] : [])))];
    if (grp >= 100 && H.sides) return H.sides[grp - 100];
    return H.steps[((grp % H.steps.length) + H.steps.length) % H.steps.length] || [];
  }

  // ---------------------------------------------------------------------------------------------- the geometry --
  _beam() {
    let B = this.beams[this.bn];
    if (!B) { B = {}; this.beams[this.bn] = B; }
    this.bn++;
    return B;
  }
  _addRay(H, h, x, y, ang, b, nb, pri, wMul = 1) {
    const len = rayExit(x, y, ang, this.asp);
    if (len < 0.02) return;
    this._addSeg(H, h, x, y, x + Math.cos(ang) * len, y + Math.sin(ang) * len, b, nb, pri, KIND.BEAM, wMul);
  }
  _addSeg(H, h, x0, y0, x1, y1, b, nb, pri, kind, wMul = 1, iMul = 1, bMul = 1) {
    const B = this._beam();
    B.H = H; B.h = h; B.x0 = x0; B.y0 = y0; B.x1 = x1; B.y1 = y1; B.b = b; B.nb = nb; B.pri = pri; B.kind = kind;
    B.wMul = wMul; B.iMul = iMul; B.bMul = bMul; B.u0 = 0; B.u1 = 1;
    return B;
  }
  _geom(H, posE, per, t, cap) {
    const k = H.cur ? H.cur.k : 0;
    const grp = H.cur ? H.cur.grp : 0;
    let heads = this._litHeads(H, grp);
    if (H.finished && !H.on && H.cur && H.cur.grp === -1) heads = this._litHeads(H, -1);
    heads = capHeads(heads, H.headCap);                // (the fit's last structural levers: headCap, beamCap)
    // a fast hit never moves while lit: a still pattern is frozen for the whole hit, a moving one at each pulse's onset
    if (H.fast && H.cur) { if (STILL_IN_FAST.has(H.pattern)) { posE = H.pStart; t = H.t0; } else { posE = H.cur.P; t = H.cur.t; } }
    const ageB = posE - H.pStart, ageS = (t - H.t0) / 1000;
    const nH = Math.max(1, heads.length);
    const perHead = Math.max(1, Math.min(H.beams, H.beamCap, cap.perHead, Math.floor(cap.beams / nH)));
    this._pattern(H, heads, posE, t, ageB, ageS, k, perHead, cap);
  }
  _pattern(H, heads, posE, t, ageB, ageS, k, perHead, cap) {
    const asp = this.asp, vel = H.vel, d = H.deal;
    const spread = H.spread;
    const xy = (h) => [HEADS[h].u * asp / 2, HEADS[h].y];
    const sideOf = (h) => HEADS[h].side || 1;
    switch (H.pattern) {
      case "fan": {
        for (const h of heads) {
          const [x, y] = xy(h);
          // today's drift for a single onset; a fast gate keeps one aim for the whole hit (its held halo must not jump)
          const drift = H.fast ? 0 : (0.25 + 0.35 * vel) * (smooth(ageS / 0.9) - 0.5);
          const aim = aimHero(x, y) + d.angle * sideOf(h) + d.dir * sideOf(h) * drift;
          this._fan(H, h, x, y, aim, perHead, spread);
        }
        break;
      }
      case "hot": {
        for (const h of heads) { const [x, y] = xy(h); this._addRay(H, h, x, y, aimHero(x, y) + HOT_AIMS[(d.aimIdx + k) % 6] * sideOf(h), 0, 1, 0, 0.8); }
        break;
      }
      case "scissors": {
        const i = Math.floor(posE) + d.focus, e = smooth(frac(posE) / 0.45);
        const A = FOCI[((i - 1) % FOCI.length + FOCI.length) % FOCI.length], Bf = FOCI[(i % FOCI.length + FOCI.length) % FOCI.length];
        const fx = A[0] + (Bf[0] - A[0]) * e, fy = A[1] + (Bf[1] - A[1]) * e;
        for (const h of heads) {
          const [x, y] = xy(h);
          const tx = HERO.x + (HEADS[h].side < 0 ? fx : -fx), ty = HERO.y + fy;
          this._fan(H, h, x, y, Math.atan2(ty - y, tx - x), Math.min(2, perHead), 0.07);
        }
        break;
      }
      case "cross": {
        for (const h of this._crossEnds(H)) { const [x, y] = xy(h); this._fan(H, h, x, y, aimHero(x, y), Math.min(H.level >= 2 ? 2 : 1, H.beamCap), 0.025); }
        break;
      }
      case "crown": {
        // the crown opens by REVEALING its beams centre-out over an eighth of a beat (beams appear in place; a sweep of
        // 24 bright beams would change twice their area every frame)
        const n = Math.min(H.crownN, cap.beams), shown = H.fast ? n : Math.ceil(n * clamp01(0.15 + ageB / (1 / 8)));
        const sway = 0.04 * Math.sin(TAU * posE / 8);
        for (let r = 0; r < Math.min(n, shown); r++) {
          const b = centreOut(r, n);
          const a = Math.PI * (0.1 + 0.8 * (n > 1 ? b / (n - 1) : 0.5));
          this._addRay(H, HERO_HEAD, HERO.x, HERO.y, a + sway, b, n, r);
        }
        break;
      }
      case "star": {
        const n = Math.min(H.crownN, cap.beams), thin = ageB > 2 ? 4 : ageB > 1 ? 2 : 1;
        for (let b = 0; b < n; b++) {
          if (b % thin) continue;
          this._addRay(H, HERO_HEAD, HERO.x, HERO.y, TAU * b / n + 0.15 * posE + Math.PI / 2, b, n, b % 2);
        }
        break;
      }
      case "bloom": {
        const bloomP = H.pStart + 1 / 2;          // converge on the first pulse, bloom on the third (half a beat on)
        const o = smooth((posE - bloomP) / (1 / 8));
        for (const h of heads) {
          const [x, y] = xy(h);
          if (o <= 0) { this._addSeg(H, h, x, y, HERO.x, HERO.y, 0, 1, 0, KIND.BEAM); continue; }
          this._fan(H, h, x, y, aimHero(x, y) + sideOf(h) * o * 0.9, Math.min(3, perHead), 0.5 * o);
        }
        break;
      }
      case "sweep": {
        const s = frac(posE), e = s < 0.5 ? 4 * s * s * s : 1 - Math.pow(-2 * s + 2, 3) / 2;
        const x01 = (Math.floor(posE) & 1) ? 1 - 2 * e : -1 + 2 * e;
        for (const h of heads) { const [x, y] = xy(h); this._fan(H, h, x, y, aimHero(x, y) + 0.55 * x01 * d.dir, Math.min(6, perHead), 0.45); }
        break;
      }
      case "zigzag": {
        const parity = H.pulsesTotal > 1 ? k & 1 : Math.floor(posE * 4) & 1;
        for (const h of heads) { const [x, y] = xy(h); this._fan(H, h, x, y, aimHero(x, y) + (parity ? 0.32 : -0.32) * d.dir * sideOf(h), Math.min(H.level >= 2 ? 2 : 1, H.beamCap), 0.06); }
        break;
      }
      case "tunnel": {
        const spin = TAU * posE / 4 * (H.level >= 2 ? 2 : 1) * d.dir;
        for (const h of heads) {
          const [x, y] = xy(h), th = HEADS[h].ang + spin;
          this._addSeg(H, h, x, y, HERO.x + 0.07 * Math.cos(th), HERO.y + 0.07 * Math.sin(th), 0, 1, 0, KIND.BEAM);
        }
        break;
      }
      case "wave": {
        const all = capHeads([...new Set(H.steps.flat())].slice(0, cap.heads), H.headCap);
        all.forEach((h, i) => { const [x, y] = xy(h); this._addRay(H, h, x, y, aimHero(x, y) + 0.5 * Math.sin(TAU * (posE / 4 + i / all.length)), 0, 1, 0); });
        break;
      }
      case "rain": {
        heads.forEach((h, i) => {
          const [x, y] = xy(h), down = HEADS[h].y > HERO.y;
          this._addRay(H, h, x, y, (down ? -Math.PI / 2 : Math.PI / 2) + 0.05 * Math.sin(TAU * posE / 4 + i), 0, 1, 0, 0.8);
        });
        break;
      }
      case "cage": {
        const c = CAGE_TILT[(Math.floor(posE / 4) + d.cage) % CAGE_TILT.length];
        for (const h of heads) {
          const [x, y] = xy(h), left = HEADS[h].side < 0, top = HEADS[h].y > HERO.y;
          const ang = top ? (left ? -Math.PI / 2 + c : -Math.PI / 2 - c) : (left ? Math.PI / 2 - c : Math.PI / 2 + c);
          this._addRay(H, h, x, y, ang, 0, 1, 0, 0.8);
        }
        break;
      }
      case "ladder": {
        const RUNG = [16, 18, 17, 19, 16, 18, 17, 19], ELEV = [-0.04, -0.04, 0.04, 0.04, -0.11, -0.11, 0.11, 0.11];
        const count = Math.min(H.rungCap || 8, H.cur && H.cur.allRungs ? 8 : (H.level >= 2 ? 2 : 1) + (H.pulsesTotal > 1 ? k % 8 : 0));
        for (let r = 0; r < count; r++) {
          const h = RUNG[r], [x, y] = xy(h);
          this._addRay(H, h, x, y, (HEADS[h].side < 0 ? 0 : Math.PI) + ELEV[r] * (HEADS[h].side < 0 ? 1 : -1), r, 8, 8 - r, 0.8);
        }
        break;
      }
      case "chase": {
        for (const h of heads) { const [x, y] = xy(h); this._addRay(H, h, x, y, aimHero(x, y) + d.angle, 0, 1, 0); }
        break;
      }
      case "cone": {
        const origins = (H.level >= 2 && heads.length < 2 ? [heads[0], HEADS[heads[0]].twin] : heads.slice(0, 2)).slice(0, Math.max(1, H.headCap));
        // (as few as 3 beams when the fit has had to thin it; 6-10 as dealt)
        const n = clamp(perHead, 3, 10), rx = 0.15 * (1 + 0.4 * vel), ry = rx * 0.55, spin = TAU * posE / 2 * d.dir;
        for (const h of origins) {
          if (h === undefined) continue;
          const [x, y] = xy(h);
          for (let b = 0; b < n; b++) { const a = TAU * b / n + spin; this._addSeg(H, h, x, y, HERO.x + rx * Math.cos(a), HERO.y + ry * Math.sin(a), b, n, b % 3, KIND.BEAM); }
        }
        for (let s = 0; s < 24; s++) {
          const a0 = TAU * s / 24 + spin, a1 = TAU * (s + 1) / 24 + spin;
          const B = this._addSeg(H, HERO_HEAD, HERO.x + rx * Math.cos(a0), HERO.y + ry * Math.sin(a0), HERO.x + rx * Math.cos(a1), HERO.y + ry * Math.sin(a1), s, 24, 0, KIND.FIGURE, 0.7, 0.7);
          B.u0 = s / 24; B.u1 = (s + 1) / 24;
        }
        break;
      }
      case "figure": {
        const R = 0.2 * (0.9 + 0.2 * vel) * (H.level >= 2 ? 1.15 : 1);
        const beat = Math.max(0, Math.floor(posE - Math.floor(H.pStart + 1e-9) + 1e-9));
        const cur = H.shapes[beat % H.shapes.length];
        const from = beat === 0 ? (H.shapeFrom || cur) : H.shapes[(beat - 1) % H.shapes.length];
        const m = smooth(frac(posE) / 0.25);
        const A = this._shape(from, posE, R), Bs = this._shape(cur, posE, R);
        // each figure's own level and blur band, as the fit set them (a dense figure -- the 4-ring tunnel has 3.6 times
        // the line of a triangle -- may show dimmer or sharper than a sparse one); a morph blends the two figures'
        const mf = this._shapeMul(H, from), mc = this._shapeMul(H, cur);
        const iMul = mf.lvl + (mc.lvl - mf.lvl) * m, bMul = mf.blur + (mc.blur - mf.blur) * m;
        for (let s = 0; s < SHAPE_SEGS; s++) {
          const o = s * 4;
          const B = this._addSeg(H, HERO_HEAD, A[o] + (Bs[o] - A[o]) * m, A[o + 1] + (Bs[o + 1] - A[o + 1]) * m,
            A[o + 2] + (Bs[o + 2] - A[o + 2]) * m, A[o + 3] + (Bs[o + 3] - A[o + 3]) * m, s, SHAPE_SEGS, 0, KIND.FIGURE, 0.7, iMul, bMul);
          B.u0 = s / SHAPE_SEGS; B.u1 = (s + 1) / SHAPE_SEGS;
        }
        H.shapeNow = cur;
        break;
      }
    }
  }
  // the cross's heads: the outermost two of each bank among every step's heads (at most headCap of them)
  _crossEnds(H) {
    const all = [...new Set(H.steps.flat())];
    const ends = [];
    for (const bank of ["A", "B"]) {
      const inBank = all.filter((h) => HEADS[h].bank === bank).sort((a, b) => HEADS[a].sx - HEADS[b].sx);
      if (inBank.length) { ends.push(inBank[0]); if (inBank.length > 1) ends.push(inBank[inBank.length - 1]); }
    }
    return capHeads(ends, H.headCap);
  }
  // the most heads one pulse of H draws (for the fit's headCap lever)
  _headsDrawn(H) {
    if (H.pattern === "cross") return this._crossEnds(H).length;
    if (H.pattern === "wave") return capHeads([...new Set(H.steps.flat())].slice(0, (H.fast ? BUDGET.fast : BUDGET.single).heads), H.headCap).length;
    if (H.pattern === "cone") return Math.min(H.headCap, 2);
    if (GROUP_FREE.has(H.pattern)) return 1;
    let m = 1;
    for (const s of H.sides || H.steps) m = Math.max(m, s.length);
    return Math.min(m, H.headCap);
  }
  // a figure's own level and blur multipliers in hit H ({lvl, blur}, both 1 until the fit lowers them)
  _shapeMul(H, name) { return (H.shapeMul && H.shapeMul[name]) || SHAPE_MUL_ONE; }
  // a figure's segments, remembered (the spawn-time fit asks for each figure of a loop's cycle several times)
  _shape(name, pos, R) {
    const key = `${name}|${pos}|${R}`;
    let s = this.shapeCache.get(key);
    if (!s) {
      if (this.shapeCache.size >= 96) this.shapeCache.clear();
      s = shapeSegments(name, { pos, R });
      this.shapeCache.set(key, s);
    }
    return s;
  }
  _fan(H, h, x, y, aim, n, spread) {
    n = Math.max(1, n | 0);
    for (let r = 0; r < n; r++) {
      const b = centreOut(r, n);
      const off = n > 1 ? (b - (n - 1) / 2) * spread / (n - 1) : 0;
      this._addRay(H, h, x, y, aim + off, b, n, r);
    }
  }

  // ------------------------------------------------------------------------------------------------ the output --
  _colour(H, B, out) {
    const C = H.col || this.col, k = H.cur ? H.cur.k : 0, b = B.b, nb = B.nb, h = B.h;
    const fig = B.kind === KIND.FIGURE;
    const side = fig ? Math.sign((B.x0 + B.x1) / 2 - HERO.x) : HEADS[h].side;
    const u = fig ? clamp((B.x0 + B.x1) / this.asp, -1, 1) : HEADS[h].u;
    let c;
    // (the fit of a loop: a colour that turns with the pulse count is drawn in the brightest it can turn to; see _fitHit)
    const top = this.fitBright ? C.top : null;
    switch (H.colour) {
      case "split": c = b & 1 ? C.L2 : C.L1; break;
      case "gradient": {
        // across a fan: first colour to second; round a figure (a closed loop): there and back, so no seam
        const g = nb > 1 ? b / (nb - 1) : 0.5, u2 = fig ? 1 - Math.abs(2 * (b + 0.5) / nb - 1) : g;
        c = C.hueGap <= 80 ? lerpOk(C.L1, C.L2, u2, out) : (b & 1 ? C.L2 : C.L1);
        break;
      }
      case "hotcore": c = nb >= 3 && Math.abs(b - (nb - 1) / 2) < 0.6 ? C.W : C.L1; break;
      case "halves": c = side < 0 ? C.L1 : side > 0 ? C.L2 : (b & 1 ? C.L2 : C.L1); break;
      case "chase": {
        if (top) { c = top.pair; break; }
        const lit = this._litHeads(H, H.cur ? H.cur.grp : 0);
        c = (lit.length > 1 ? h === lit[k % lit.length] : b === k % Math.max(1, nb)) ? C.L2 : C.L1;
        break;
      }
      case "flip": c = top ? top.flicker : C.flicker[k % C.flicker.length]; break;
      case "trinity": c = top ? top.triple : C.triple[k % C.triple.length]; break;
      case "headgrad": c = lerpOk(C.L1, C.L2, (u + 1) / 2, out); break;
      case "burst": c = top ? top.burst : C.burst[(b + k) % C.burst.length]; break;
      case "barswap": {
        // (on the bar line the PULSE lands on, so a lit pulse never changes colour: the swap comes with the next onset)
        const swap = Math.floor((H.cur ? H.cur.P : this.posE) / 4) & 1, s = side;
        c = s === 0 ? (b & 1 ? C.L2 : C.L1) : (s < 0) !== !!swap ? C.L1 : C.L2;
        break;
      }
      default: c = C.L1;
    }
    if (c !== out) { out[0] = c[0]; out[1] = c[1]; out[2] = c[2]; }
    // a tail settles into the theme's laser colour within 200 ms; the bright head never outlasts a beat
    if (H.tailAge > 0) { const s = 1 - Math.exp(-H.tailAge / 70); for (let i = 0; i < 3; i++) out[i] += (C.L1[i] - out[i]) * s; }
    if (isSaturatedRed(out)) { out[0] = C.W[0]; out[1] = C.W[1]; out[2] = C.W[2]; }
    return out;
  }

  // The frame's safety check, then the output. The change from the frame last drawn must fit the budget; while it does
  // not, the hit whose NEW or MOVING beams change the most gives up its outermost beams (sticky: they never come back
  // mid-hit), then every other beam, and a hit whose every line is new or moving (an onset, a sweep, a ringing string or
  // figure) dims, for good. A beam that stays put is never taken: taking it would itself be a change. If nothing more
  // can give way and the frame is still over, it goes out as the BEST reduction found (never worse than any state tried,
  // the untouched frame included) and says so (area.over): going dark would be the biggest change of all; the page's
  // final-frame limiter is the backstop. (Light that goes dark cannot be taken back here: that is why a new hit plays
  // alone -- see _spawn -- and why each hit is fitted over its whole life.)
  _emit(anyFast, t) {
    const out = this.out, asp = this.asp, budget = anyFast ? BUDGET.fast : BUDGET.single;
    const stuck = new Set();
    let over = false, best = null, bnAll = 0;
    const score = () => Math.max(this.chg.window / budget.window, this.chg.frame / budget.frame);
    for (let guard = 0; ; guard++) {
      this._write(t, this.work, this.ringT); this._writeHalved(this.work);
      estimateChange(this.drawn, this.work, asp, this.chg, this.contrib, this.state);
      if (this.chg.window <= budget.window + 1e-9 && this.chg.frame <= budget.frame + 1e-9) break;
      // the best state so far, to go out if nothing gets under budget (giving way only reorders beams within the first
      // bnAll, so that whole prefix is kept: putting it back never aliases a pooled beam)
      if (!best) bnAll = this.bn;
      const s = score();
      if (!best || s < best.s - 1e-12) {
        best = { s, hits: this.hits.map((h) => [h, h.trimPri, h.thin, h.peak, h.inten, h.level01]), beams: this.beams.slice(0, bnAll), bn: this.bn };
      }
      const H = guard < 48 ? this._worstMover(stuck) : null;
      if (!H) { over = true; break; }
      if (!this._giveWay(H)) stuck.add(H);
    }
    if (over && best.s < score() - 1e-12) {
      // the last state tried was not the best: the best goes out
      for (const [h, tp, th, pk, it, lv] of best.hits) { h.trimPri = tp; h.thin = th; h.peak = pk; h.inten = it; h.level01 = lv; }
      for (let i = 0; i < bnAll; i++) this.beams[i] = best.beams[i];
      this.bn = best.bn;
      this._write(t, this.work, this.ringT); this._writeHalved(this.work);
      estimateChange(this.drawn, this.work, asp, this.chg, this.contrib, this.state);
    }
    const buf = this.work, Wa = buf.W;
    estimateArea(Wa, buf.n, asp, this.lit);
    const A = out.area;
    A.window = this.chg.window; A.frame = this.chg.frame; A.litWindow = this.lit.window; A.litFrame = this.lit.frame; A.over = over;
    this._pack(buf);
    out.heads.fill(0); out.padGrid.fill(0);
    for (let i = 0; i < buf.n; i++) {
      const o = i * W_FLOATS, h = Wa[o + W.HEAD], lv = Wa[o + W.I];
      if (h >= 0 && lv > out.heads[h]) out.heads[h] = lv;
    }
    for (let h = 0; h < HEADS.length; h++) {
      const p = HEADS[h].pad - 1;
      if (out.heads[h] > out.padGrid[p]) out.padGrid[p] = out.heads[h];
      if (h === HERO_HEAD && out.heads[h] > out.padGrid[6]) out.padGrid[6] = out.heads[h];
    }
    // this frame is the one the next frame's change is measured against
    const s = this.drawn; this.drawn = indexKeys(this.work); this.work = s;
  }
  // A hit going out in two halves under a newer hit's onset (see _handOver) is drawn, in its half frame, as the very
  // records it was drawn with last frame at half their level (core, halo, heat): nothing of it moves -- not its pattern's
  // motion, not its strings -- so its change is the level step alone, which moves no pixel by 0.1. (Drawing it afresh
  // let a moving or ringing tail change a strip along its edges: up to 3.2 % of a window in mashing.)
  _writeHalved(buf) {
    let ids = null;
    for (const H of this.hits) if (H.halveF === this.frameIdx) (ids || (ids = new Set())).add(H.id);
    if (!ids) return;
    const src = this.drawn, S = src.W, Wa = buf.W;
    for (let i = 0; i < src.n && buf.n < MAX_SEGMENTS; i++) {
      if (!ids.has(Math.floor(src.keys[i] / 8192))) continue;
      const o = buf.n * W_FLOATS;
      Wa.set(S.subarray(i * W_FLOATS, (i + 1) * W_FLOATS), o);
      Wa[o + W.I] *= 0.5; Wa[o + W.GLOW] *= 0.5; Wa[o + W.HEAT] *= 0.5;
      buf.keys[buf.n] = src.keys[i]; buf.beam[buf.n] = -1;
      buf.n++;
    }
  }
  // the hit (not yet stuck) whose new or moving beams change the most this frame (a halved tail's records have no beam)
  _worstMover(stuck) {
    const buf = this.work, sum = new Map();
    for (let i = 0; i < buf.n; i++) {
      if (this.state[i] === 0 || buf.beam[i] < 0) continue;
      const H = this.beams[buf.beam[i]].H;
      if (!stuck.has(H)) sum.set(H, (sum.get(H) || 0) + this.contrib[i]);
    }
    let best = null, bestV = 0;
    for (const [H, v] of sum) if (v > bestV) { bestV = v; best = H; }
    return best;
  }
  // one step of giving way for hit H; false when it has nothing left to give this frame
  _giveWay(H) {
    let maxPri = -1, nBeam = 0;
    for (let i = 0; i < this.bn; i++) { const B = this.beams[i]; if (B.H === H && B.kind === KIND.BEAM) { nBeam++; if (B.pri > maxPri) maxPri = B.pri; } }
    let drop;
    if (maxPri > 0) { H.trimPri = Math.min(H.trimPri, maxPri - 1); drop = (B) => B.pri > H.trimPri; }
    else if (nBeam > 1 && !H.thin) { H.thin = true; let s = 0; drop = () => (s++ & 1) === 1; }
    else if (H.peak > DIM_FLOOR && this._mostlyMoving(H)) {
      // (nearly) every line of it is new or moving this frame (an onset, a sweep, a ringing string or figure), so
      // dimming it adds little change of its own: it dims, for good. (A ringing figure counts though the pieces at its
      // nodes stand still: round 2 required every piece to move, and a figure ringing past its fit could not give way.
      // The frame keeps the best state it tried, so a dim that changes more is never sent.) (Down to almost nothing if
      // it must: a line's band stays as wide from about 0.6 down to 0.15 -- its blur band, or its halo -- and then drops
      // under 0.1 at once, so a floor any higher could leave a dense figure one step short.)
      const k = Math.max(DIM_FLOOR / H.peak, 0.7);
      H.peak *= k; H.inten *= k; H.level01 *= k;
      return true;
    } else return false;
    let kept = 0;
    for (let i = 0; i < this.bn; i++) {
      const B = this.beams[i];
      if (B.H === H && B.kind === KIND.BEAM && drop(B)) continue;
      if (kept !== i) { const tmp = this.beams[kept]; this.beams[kept] = B; this.beams[i] = tmp; }
      kept++;
    }
    this.bn = kept;
    return true;
  }
  // every line of H is new or moving this frame, but for at most a quarter that stand still (a ringing figure's nodes)
  _mostlyMoving(H) {
    const buf = this.work;
    let n = 0, still = 0;
    for (let i = 0; i < buf.n; i++) if (buf.beam[i] >= 0 && this.beams[buf.beam[i]].H === H) { n++; if (this.state[i] === 0) still++; }
    return n > 0 && still <= 0.25 * n;
  }
  // the output: each record packed into its 2 texels; a figure's pieces behind their group header
  _pack(buf) {
    const out = this.out, seg = out.seg, head = out.head, Wa = buf.W, n = buf.n;
    let k = 0;
    for (let i = 0; i < n;) {
      const o = i * W_FLOATS, grp = Wa[o + W.GROUP];
      if (grp < 0) {
        if (k >= MAX_SEGMENTS) break;
        packRecord(Wa, i, seg, k); head[k] = Wa[o + W.HEAD]; k++; i++;
        continue;
      }
      let j = i + 1;
      while (j < n && Wa[j * W_FLOATS + W.GROUP] === grp) j++;
      if (k + 1 + (j - i) > MAX_SEGMENTS) break;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, blur = 0;
      for (let q = i; q < j; q++) {
        const p = q * W_FLOATS;
        x0 = Math.min(x0, Wa[p], Wa[p + 2]); x1 = Math.max(x1, Wa[p], Wa[p + 2]);
        y0 = Math.min(y0, Wa[p + 1], Wa[p + 3]); y1 = Math.max(y1, Wa[p + 1], Wa[p + 3]);
        blur = Math.max(blur, Wa[p + W.BLUR]);
      }
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      let r = 0;
      for (let q = i; q < j; q++) {
        const p = q * W_FLOATS;
        r = Math.max(r, hyp(Wa[p] - cx, Wa[p + 1] - cy), hyp(Wa[p + 2] - cx, Wa[p + 3] - cy));
      }
      const h = k * SEG_FLOATS;
      seg[h] = cx; seg[h + 1] = cy; seg[h + 2] = r + (blur + CORE_MAX_PX) / REF_PX; seg[h + 3] = GROUP_MARK + (j - i);
      seg[h + 4] = 0; seg[h + 5] = 0; seg[h + 6] = 0; seg[h + 7] = 0;
      head[k] = -1; k++;
      for (let q = i; q < j; q++, k++) { packRecord(Wa, q, seg, k); head[k] = Wa[q * W_FLOATS + W.HEAD]; }
      i = j;
    }
    out.n = k;
  }
  // A string's state at time t, or null when it is still: terms = each ring's three mode amplitudes (scaled by its
  // attack) and its age; env = their widest swing summed (u = 1/2 or 1/4), for the blur band.
  _ringState(v, t) {
    if (!v.rings.length) return null;
    const offS = v.offT === null ? null : Math.max(0, (t - v.offT) / 1000);
    const swing = (q) => Math.max(q[0] + q[2], 0.7071 * (q[0] + q[2]) + q[1]);
    const terms = [];
    let top = 0, env = 0;
    for (const r of v.rings) {
      const age = (t - r.t0) / 1000;
      if (age < 0 || age >= 6) continue;
      const a = ringAttack(age), m = vibModes(age, r.amp, offS).map((x) => x * a);
      terms.push({ m, age }); top += m[0]; env += swing(m);
    }
    return top > 0.3 ? { terms, env } : null;
  }
  // The engine's records for the beams built this frame, into buf: one record per lit beam. A ringing beam stays ONE
  // record carrying its three mode coefficients this frame (the shader bends it); a ringing figure's pieces move along
  // their radii. A figure's pieces share a group (its header is added by _pack). tr: the strings' clock (see frame()).
  _write(t, buf, tr = t) {
    const Wa = buf.W, keys = buf.keys, bix = buf.beam, rgb = [0, 0, 0];
    const ringOf = [];                   // each head's string this frame, worked out once (a figure has 96 pieces)
    const figRing = new Map();           // a ringing figure's displacement at each joint and envelope at each piece's middle
    let n = 0;
    for (let i = 0; i < this.bn && n < MAX_SEGMENTS; i++) {
      const B = this.beams[i], H = B.H;
      const act = H.cur ? ACT[H.cur.act] || ACT.on : ACT.on;
      // The halo (spec 1.7): a single onset's halo follows its core. In a fast gate the halo breathes between 75 % (the
      // gap) and 100 % (the pulse) while the next pulse fires the same heads; it goes off with its core when the order
      // walks on; the tail decays smoothly. `held` marks a halo already lit before this pulse (only the core flashes).
      const inten = H.inten * B.iMul;
      let glow = inten, held = false;
      if (H.fast) {
        if (H.finished) { held = true; if (H.tailGlowOnly) glow = 0.75 * H.level01 * B.iMul; }
        else if (H.on) { glow = H.level01 * B.iMul; held = !!(H.cur && H.cur.sameAsPrev); }
        else { glow = H.cur && H.cur.holdHalo ? 0.75 * H.level01 * B.iMul : 0; held = true; }
      }
      if (inten < 0.002 && glow < 0.002) continue;
      this._colour(H, B, rgb);
      const fig = B.kind === KIND.FIGURE;
      let width = (fig ? 1.4 + 0.8 * H.vel : 1.2 + 2.4 * H.vel) * B.wMul * (H.on ? act.w : 1);
      width = Math.min(CORE_MAX_PX, width);
      let heat = (1 + 2 * H.vel) * inten * (H.on ? act.heat : 1);
      if (H.colour === "hotcore" && B.nb >= 3 && Math.abs(B.b - (B.nb - 1) / 2) < 0.6) heat *= 1.8;
      // Vibrate: the string's state for this beam's head -- the newest pluck's ring rising through its attack, the ring
      // it replaced fading under it (worked out once per head)
      const vh = fig ? HERO_HEAD : B.h, v = this.vib[vh];
      let rs = ringOf[vh];
      if (rs === undefined) rs = ringOf[vh] = this._ringState(v, tr);
      const ringing = rs !== null;
      const smear = H.smearFrame >= 0 && H.cur && H.cur.act === "smear" && H.on ? VIB.SMEAR_GAIN : 1;
      const blurCap = (H.fast && smear === 1 ? VIB.BLUR_FAST_PX : VIB.BLUR_MAX_PX) * B.bMul * H.blurMul;
      let x0 = B.x0, y0 = B.y0, x1 = B.x1, y1 = B.y1, blur = 0, c1 = 0, c2 = 0, c3 = 0, flags = held ? FLAG.HELD : 0;
      if (ringing && fig) {              // a closed figure rings as one loop: each end moves along its own radius
        let fr = figRing.get(vh);
        if (!fr) {
          // (the fit's onset probes write the same instant with the same rings again and again: kept while they are)
          const memo = this.figMemo;
          if (memo && memo.t === tr && memo.vh === vh && memo.rings === v.rings && memo.offT === v.offT && memo.ph === v.ph) fr = memo.fr;
          else { fr = figureModes(rs.terms); fr.ph = v.ph; fr.byN = new Map(); this.figMemo = { t: tr, vh, rings: v.rings, offT: v.offT, ph: v.ph, fr }; }
          figRing.set(vh, fr);
        }
        let d0, d1, e;
        if (B.u0 === B.b / B.nb && B.u1 === (B.b + 1) / B.nb) {
          // (pieces b of nb round the loop: each joint and middle worked out once per frame, not once per piece end)
          let tab = fr.byN.get(B.nb);
          if (!tab) {
            tab = { d: new Float64Array(B.nb + 1), e: new Float64Array(B.nb) };
            for (let j = 0; j <= B.nb; j++) tab.d[j] = figureRingAt(fr, j / B.nb, false) / REF_PX;
            for (let j = 0; j < B.nb; j++) tab.e[j] = figureRingAt(fr, 0.5 * (j / B.nb + (j + 1) / B.nb), true);
            fr.byN.set(B.nb, tab);
          }
          d0 = tab.d[B.b]; d1 = tab.d[B.b + 1]; e = tab.e[B.b];
        } else { d0 = figureRingAt(fr, B.u0, false) / REF_PX; d1 = figureRingAt(fr, B.u1, false) / REF_PX; e = figureRingAt(fr, 0.5 * (B.u0 + B.u1), true); }
        const r0 = hyp(x0 - HERO.x, y0 - HERO.y) || 1, r1 = hyp(x1 - HERO.x, y1 - HERO.y) || 1;
        x0 += (x0 - HERO.x) / r0 * d0; y0 += (y0 - HERO.y) / r0 * d0; x1 += (x1 - HERO.x) / r1 * d1; y1 += (y1 - HERO.y) / r1 * d1;
        blur = Math.min(blurCap, VIB.BLUR_GAIN * smear * Math.abs(e));
        // The fit (fitBlur): a piece's band is widest NOT at its widest blur -- the core spread over width + 2 blur
        // falls under 0.1 there and lights nothing -- but at the blur where the spread core just reaches 0.1, which the
        // ring passes through as it rises and decays. Each probe piece takes the blur that lights the most, up to its
        // ring's (a figure's piece is one level along its length, so this bounds every instant). Round 2 probed the
        // risen ring only: a ringing tunnel probed at 3.3 % of a window lit 16.9 % as its ring rose.
        if (this.fitBlur && blur > 0) {
          const Y = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2], kw = heat * heat / (1 + heat * heat);
          const Yh = (1 - kw) * Y + kw * Math.max(rgb[0], rgb[1], rgb[2]), q = 0.1 - 0.5 * glow * Y;
          if (q > 0) blur = Math.min(blur, Math.max(0, 0.98 * (inten * Yh * width / q - width) / 2));
        }
      } else if (ringing) {              // a string: the three modes' displacements now, nodes at both ends
        const ph = v.ph + B.b * 0.7, coef = (m, a, k) => m[k] * Math.cos(TAU * VIB.F1_HZ * (k + 1) * (1 + VIB.INHARM * (k + 1) * (k + 1)) * a + ph + 1.3 * (k + 1));
        for (const q of rs.terms) { c1 += coef(q.m, q.age, 0); c2 += coef(q.m, q.age, 1); c3 += coef(q.m, q.age, 2); }
        blur = Math.min(blurCap, VIB.BLUR_GAIN * smear * rs.env);
        flags |= FLAG.RING;
      }
      const o = n * W_FLOATS;
      Wa[o] = x0; Wa[o + 1] = y0; Wa[o + 2] = x1; Wa[o + 3] = y1;
      Wa[o + W.R] = rgb[0]; Wa[o + W.G] = rgb[1]; Wa[o + W.B] = rgb[2]; Wa[o + W.I] = inten;
      Wa[o + W.WIDTH] = width; Wa[o + W.GLOW] = glow; Wa[o + W.BLUR] = blur; Wa[o + W.HEAT] = heat;
      Wa[o + W.KIND] = B.kind; Wa[o + W.HEAD] = B.h; Wa[o + W.FALLOFF] = fig ? 0 : BEAM_FALLOFF; Wa[o + W.FLAGS] = flags;
      Wa[o + W.C1] = c1; Wa[o + W.C2] = c2; Wa[o + W.C3] = c3;
      Wa[o + W.GROUP] = fig ? H.id * 2 + (H.pattern === "cone" ? 1 : 0) : -1;
      keys[n] = ((H.id * 32 + B.h) * 128 + (B.b & 127)) * 2 + B.kind;
      bix[n] = i;
      n++;
    }
    buf.n = n;
    return n;
  }
}

// A closed loop's ring: modes sin(2 pi n s) round the figure (n = 2, 3, 4; no fixed ends), the same decay as the beams.
// For a string's rings this frame (terms: each ring's mode amplitudes m and age), the displacement at s is
//   0.6 * sum over rings and modes of m_i sin(2 pi n s + phase) cos(2 pi f_i age + 1.3 n),
// and the envelope 0.6 * sum m_i |sin(2 pi n s)|. Neither the cosine nor the phase depends on s, so the rings' amplitudes
// are summed once per frame: c = each mode's amplitude now, e = its envelope amplitude.
function figureModes(terms) {
  const c = [0, 0, 0], e = [0, 0, 0];
  for (const q of terms) {
    for (let i = 0; i < 3; i++) {
      const n = i + 2, f = VIB.F1_HZ * (i + 1) * (1 + VIB.INHARM * (i + 1) * (i + 1));
      c[i] += q.m[i] * Math.cos(TAU * f * q.age + 1.3 * n); e[i] += q.m[i];
    }
  }
  return { c, e };
}
function figureRingAt(fm, s, envelope) {
  let d = 0;
  for (let i = 0; i < 3; i++) d += envelope ? fm.e[i] * Math.abs(Math.sin(TAU * (i + 2) * s)) : fm.c[i] * Math.sin(TAU * (i + 2) * s + fm.ph);
  return d * 0.6;
}
const CENTRE_OUT = new Map();
function centreOut(r, n) {       // beam index r-th from the centre of an n-beam fan (so caps keep the centre)
  let a = CENTRE_OUT.get(n);
  if (!a) {
    a = Array.from({ length: n }, (_, i) => i).sort((x, y) => Math.abs(x - (n - 1) / 2) - Math.abs(y - (n - 1) / 2) || x - y);
    CENTRE_OUT.set(n, a);
  }
  return a[r];
}
// At most maxHeads of the heads s: whole mirrored rings (left and right, both banks), evenly spread from the outside in,
// so the rig stays symmetric
function capHeads(s, maxHeads) {
  if (s.length <= maxHeads) return s;
  const byRing = new Map();
  for (const h of s) { const r = HEADS[h].ring; if (!byRing.has(r)) byRing.set(r, []); byRing.get(r).push(h); }
  const rank = (h) => (HEADS[h].bank === "A" ? 0 : HEADS[h].bank === "B" ? 2 : 4) + (HEADS[h].side > 0 ? 1 : 0);
  const groups = [...byRing.keys()].sort((a, b) => b - a).map((r) => byRing.get(r).sort((a, b) => rank(a) - rank(b)));
  const size = Math.max(...groups.map((g) => g.length));
  const nG = Math.max(1, Math.floor(maxHeads / size));
  const out = [];
  for (let i = 0; i < nG && i < groups.length; i++) out.push(...groups[Math.round(i * (groups.length - 1) / Math.max(1, nG - 1))]);
  return [...new Set(out)].slice(0, maxHeads);
}
function aimHero(x, y) { return Math.atan2(HERO.y - y, HERO.x - x); }
function sameHeads(a, b) { if (a.length !== b.length) return false; for (const h of a) if (!b.includes(h)) return false; return true; }
function rayExit(x, y, ang, asp) {
  const dx = Math.cos(ang), dy = Math.sin(ang), hx = asp / 2;
  let t = Infinity;
  if (dx > 1e-9) t = Math.min(t, (hx - x) / dx); else if (dx < -1e-9) t = Math.min(t, (-hx - x) / dx);
  if (dy > 1e-9) t = Math.min(t, (0.5 - y) / dy); else if (dy < -1e-9) t = Math.min(t, (-0.5 - y) / dy);
  return Number.isFinite(t) ? Math.max(0, t) : 0;
}

// The spec's strip head bus (1.7) for scenes tagged `laser-heads` (the Laser Cathedral): 6 texels of row 2 as 24 floats,
// texel 9 .yzw = pattern id (0-17), step phase 0..1, solo; texels 10-12 = the 12 pad-grid heads, each colour slot + level
// (slot 0 = L1, 1 = L2, 2 = white; level in [0, 0.999]); texel 13 = L1 rgb + beams per fan; texel 14 = L2 rgb + spread.
export function stripBus(engine, out = new Float32Array(24)) {
  const f = engine.out, H = engine.hits.length ? engine.hits[engine.hits.length - 1] : null;
  out.fill(0);
  out[1] = f.pattern ? PATTERN_CODE[f.pattern] || 0 : 0;
  out[2] = engine.posE !== undefined ? frac(engine.posE) : 0;
  out[3] = f.solo;
  for (let p = 0; p < 12; p++) out[4 + p] = Math.min(0.999, f.padGrid[p]);
  const c = engine.col;
  out[16] = c.L1[0]; out[17] = c.L1[1]; out[18] = c.L1[2]; out[19] = H ? H.beams : 0;
  out[20] = c.L2[0]; out[21] = c.L2[1]; out[22] = c.L2[2]; out[23] = H ? H.spread : 0;
  return out;
}

// The catalogue, for the HUD and the mapping panel.
export function catalogue() {
  return {
    api: LASERS_API,
    heads: HEADS.map((h) => ({ name: h.name, bank: h.bank, row: h.row, u: h.u, y: h.y, pad: h.pad })),
    bankModes: Object.keys(BANK_MODES), patterns: PATTERN_IDS.slice(), gates: GATE_IDS.slice(), orders: ORDER_IDS.slice(),
    colourModes: COLOUR_IDS.slice(), shapes: SHAPES.slice(), tiers: Object.keys(TIERS),
  };
}
