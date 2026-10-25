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
// the segments frame() returns (a beam layer with no feedback; see "The output" below). It never touches the DOM, WebGL,
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
//   - SAFETY, before anything is drawn: an AREA ESTIMATOR (WCAG's one-third-frame windows, read from a fine grid that
//     counts the union of the light, with the halo's real lit width from its glow and colour) fits every new hit to its
//     budget (fast gates: 15 % of a window, 8 % of the frame; single onsets: 22 % / 10 %), and checks every frame (a
//     sticky trim takes outer beams if needed and never gives them back mid-hit). A fast hit never moves while lit, a
//     new fast hit chokes the old ones, and red is never emitted. Against a raster of the overlay's own core and halo,
//     every pattern x gate at 150 and 180 BPM, white beams at full velocity, changes at most ~18 % of any window per
//     frame (WCAG's line is 25 %).                                                                    estimateArea BUDGET
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
//   seg      Float32Array(MAX_SEGMENTS * 16): n segments, 16 floats = 4 RGBA texels each. Upload it as an RGBA32F texture
//            SEG_TEXELS (4) wide and MAX_SEGMENTS tall; row i is segment i (texelFetch(ivec2(k, i), 0)).
//              texel 0  x0, y0, x1, y1       the segment, centred units
//              texel 1  r, g, b, intensity   linear colour; intensity = the core's level (0 in a gate's dark gap)
//              texel 2  width, glow, blur, heat
//                       width: core width in px at 1080 (never over 3.6); glow: halo level for the overlay's Lorentzian
//                       halo (16 px at 1080); in a fast gate it is held at 75 % through a gap when the next pulse fires
//                       the same heads of a still pattern, so only the cores strobe; blur: motion-blur band half-width
//                       in px at 1080 (Vibrate; spread the core's light over it); heat: white-core strength for hotCore()
//                       (the overlay's (1 + 2 vel) * e)
//              texel 3  kind, head, falloff, flags
//                       kind: 0 beam, 1 figure line; head: index into HEADS; falloff: the light's fade along the segment
//                       per unit length (the overlay's exp(-along * 0.5)); flags, a bit field: 1 = the halo is held (only
//                       the core flashes), 2 = the segment runs on into the next one, 4 = it carries on from the one
//                       before: the pieces of a ringing string or of a figure's stroke are consecutive rows. Draw such a
//                       run as ONE line: keep the nearest distance over its pieces (a 4 continues the run, a piece without
//                       2 ends it) and add the run's light once. Adding each piece separately doubles every joint into a
//                       bead.
//   n        segments written
//   heads    Float32Array(21): each head's level this frame (0..1)
//   padGrid  Float32Array(12): head activity folded onto the KeyLab's 4 x 3 pad grid (row 1 = Bank A, row 2 = towers and
//            hero, row 3 = Bank B), for a "laser view" of the pad LEDs
//   pad      { level, rgb, tier }: pad 2's LED (tier brightness 0.6 / 0.8 / 1.0 while lasers run, 0 at rest; rgb = the
//            laser colour, linear; the page maps it to the theme's LED stand-in)
//   area     { frame, window }: the estimated share of the frame, and of the worst one-third window, the lasers light
//   solo     1, or 0.3 while a gate runs (the scene's idle beams dip, like a laser desk's Flash-Solo)
//   events   [{type: "pulse", hit, k, act} | {type: "flash", level} | {type: "pluck", head} | {type: "hero"}]; a
//            "flash" is the phrase's last syllable: the page may route a white flash through its FlashGate. The lasers
//            themselves never ask the FlashGate.
//   gate, pattern, tier, bank, order, colour: the newest running hit's labels, for the HUD
// stripBus(engine) packs the spec's strip head bus (texels 9-14 of row 2) for scenes tagged `laser-heads`.

export const LASERS_API = "arsenal.vj-lasers/v1";

const TAU = Math.PI * 2;
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const clamp01 = (x) => clamp(x, 0, 1);
const smooth = (x) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
const frac = (x) => x - Math.floor(x);
const REF_PX = 1080;

export const HERO = Object.freeze({ x: 0, y: 0.05 });
export const SEG_FLOATS = 16;
export const SEG_TEXELS = 4;
export const MAX_SEGMENTS = 512;
export const SEG = Object.freeze({ X0: 0, Y0: 1, X1: 2, Y1: 3, R: 4, G: 5, B: 6, I: 7, WIDTH: 8, GLOW: 9, BLUR: 10,
  HEAT: 11, KIND: 12, HEAD: 13, FALLOFF: 14, FLAGS: 15 });
export const KIND = Object.freeze({ BEAM: 0, FIGURE: 1 });
export const CORE_MAX_PX = 3.6;

// The safety budget (spec 4.1 rule 3). Fast = a gate faster than 3 pulses per second.
export const BUDGET = Object.freeze({
  fast: { window: 0.15, frame: 0.08, heads: 4, beams: 16, perHead: 12 },
  single: { window: 0.22, frame: 0.10, heads: 8, beams: 32, perHead: 24 },
});
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
  return Object.freeze({ id: t.id || "custom", L1, L2, W, triple: list(strobe.triple, [L1, L1, W]),
    flicker: list(strobe.flicker, [L1, L2]), burst: list(t.burst, [L1, L2, W]), splitOnly: !!t.split_only,
    hueGap: hueGapDeg(L1, L2) });
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
  BLUR_GAIN: 0.6,      // blur band half-width = BLUR_GAIN * the local envelope
  BLUR_MAX_PX: 8,
  BLUR_FAST_PX: 4,     // the cap while a fast gate runs (the band must not strobe much area)
  SMEAR_GAIN: 2.2,     // the phrase's "blur blur": the band widens this much
  SUBDIV: 8,           // a ringing beam is drawn as this many pieces
});
// the mode amplitudes (px) of a pluck of `amp` px, ageS seconds after it, with Vibrate off for offS seconds (or null)
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
  const lens = strokes.map((s) => { let L = 0; for (let i = 1; i < s.length; i++) L += Math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]); return L; });
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
    let i = 1, acc = 0, l = st.length > 1 ? Math.hypot(st[1][0] - st[0][0], st[1][1] - st[0][1]) : 0;
    for (let j = 0; j <= m; j++) {
      const d = L * j / m;
      while (i < st.length - 1 && acc + l < d - 1e-12) { acc += l; i++; l = Math.hypot(st[i][0] - st[i - 1][0], st[i][1] - st[i - 1][1]); }
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
// The area estimator: the spec's (4.2), made finer so that it measures the UNION of the light. Each lit segment is
// sampled every half cell, each sample carrying its counted width (below), into a 72 x 36 grid of small cells (about 27 x
// 30 px at 1080), each capped at full; the 25 windows (one third of the frame per side, WCAG 2.3.1's reference field, at
// half-window steps) are read from it. The spec's 6 x 6 grid ADDED overlapping beams, so the dozen beams meeting at a
// fan's origin counted a dozen times (a one-head 12-beam fan read about 3x its raster); the small capped cells count
// that spot once. Returns the share of the frame and of the worst window.
const GX = 72, GY = 36;
const CELLS = new Float64Array(GX * GY);
// The counted width (px at 1080) of a lit segment: the wider of its core band (core + 2 px) and the band its halo lights
// to a luminance step of 0.1 or more (the halo is centred on the core), plus the blur band where it is dense enough to
// count. The halo is the overlay's: glow * Y * 0.5 * L(d), L(d) = 0.0625 / (0.0625 + (d / 16 px)^2), so it lights out to
// d = 4 sqrt(5 glow Y - 1) px: about 8.5 px each side for a white beam at full glow, under 2 px for a dim blue. (The
// spec's flat core + 2 + 6 px read a white fan at a third of its raster and a blue one at twice it; measured against a
// raster of the overlay's own core and halo, this tracks it within a few tenths of a point.) A held halo only breathes
// by a quarter of its glow. fade is the overlay's fade along the beam at the point measured (exp(-falloff * distance)).
export function countedWidthPx(seg, o, fade = 1) {
  const core = seg[o + SEG.WIDTH], inten = seg[o + SEG.I] * fade, blur = seg[o + SEG.BLUR];
  const Y = 0.2126 * seg[o + SEG.R] + 0.7152 * seg[o + SEG.G] + 0.0722 * seg[o + SEG.B];
  const g = ((seg[o + SEG.FLAGS] & 1) ? 0.25 : 1) * seg[o + SEG.GLOW] * fade;
  let w = inten >= 0.05 ? core + 2 : 0;
  const k = 5 * g * Y;
  if (k > 1) w = Math.max(w, 8 * Math.sqrt(k - 1));      // the halo band is centred on the core: the wider one counts
  if (blur > 0) { const dens = inten * core / (core + 2 * blur); w += 2 * blur * clamp01(dens / 0.1); }
  return w;
}
export function estimateArea(seg, n, aspect = 16 / 9, out = { frame: 0, window: 0 }) {
  CELLS.fill(0);
  const cw = aspect / GX, ch = 1 / GY, cellA = cw * ch, hx = aspect / 2, step = Math.min(cw, ch) / 2;
  for (let i = 0; i < n; i++) {
    const o = i * SEG_FLOATS;
    if (!(seg[o + SEG.I] >= 0.05)) continue;
    const x0 = seg[o], y0 = seg[o + 1], x1 = seg[o + 2], y1 = seg[o + 3];
    const len = Math.hypot(x1 - x0, y1 - y0);
    if (len <= 0) continue;
    const m = Math.max(1, Math.ceil(len / step)), fall = seg[o + SEG.FALLOFF];
    const w0 = countedWidthPx(seg, o);
    for (let j = 0; j < m; j++) {
      const u = (j + 0.5) / m, x = x0 + (x1 - x0) * u, y = y0 + (y1 - y0) * u;
      if (x < -hx || x > hx || y < -0.5 || y > 0.5) continue;
      const cx = Math.min(GX - 1, Math.floor((x + hx) / cw)), cy = Math.min(GY - 1, Math.floor((y + 0.5) / ch));
      const w = fall > 0 ? countedWidthPx(seg, o, Math.exp(-fall * len * u)) : w0;
      CELLS[cy * GX + cx] += len / m * w / REF_PX;
    }
  }
  let total = 0, worst = 0;
  for (let c = 0; c < CELLS.length; c++) { if (CELLS[c] > cellA) CELLS[c] = cellA; total += CELLS[c]; }
  const wx = GX / 6, wy = GY / 6;          // half a window, in cells
  for (let j = 0; j < 5; j++) for (let i = 0; i < 5; i++) {
    let s = 0;
    for (let y = j * wy; y < j * wy + 2 * wy; y++) for (let x = i * wx; x < i * wx + 2 * wx; x++) s += CELLS[y * GX + x];
    if (s > worst) worst = s;
  }
  out.frame = total / aspect;
  out.window = worst / (4 * wx * wy * cellA);
  return out;
}

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
  maxHits: 4,                 // hits drawn at once (older ones fade out)
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
      else if (k === "theme") this.col = themeColours(v);
      else if (k === "section") this.setSection(v);
      else if (k in DEFAULTS) this.o[k] = v;
    }
    this.o.variety = clamp01(Number(this.o.variety));
    return this;
  }
  setTheme(theme) { this.col = themeColours(theme); }
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
    this.vib = HEADS.map((h, i) => ({ t0: -1e9, amp: 0, ph: TAU * makeRng(seed, "vib", i)(), offT: null }));
    this.sectionIdx = 0;
    this._makeDecks();
    this.frameIdx = 0; this.F = 1000 / 60; this.tPrev = null;
    this.tRef = null; this.posRef = 0;
    this.lastPeriod = 0;
    this.nowT = 0;
    this.beams = [];
    this.bn = 0;
    this.scratch = new Float32Array(MAX_SEGMENTS * SEG_FLOATS);   // hit-time fitting never touches the frame the page draws
    this.shapeCache = new Map();
    this.out = { t: 0, seg: new Float32Array(MAX_SEGMENTS * SEG_FLOATS), n: 0, heads: new Float32Array(HEADS.length),
      padGrid: new Float32Array(12), pad: { level: 0, rgb: [0, 0, 0], tier: 0 }, area: { frame: 0, window: 0 },
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
    const gap = Number.isFinite(this.lastHitT) ? (t - this.lastHitT) / per : Infinity;
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
        roll.vel = Math.max(roll.vel * 0.7, vel);
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
    const fast = this._gateFast(gate, per);

    const deal = this._deal({ rng, tier, level, gate, fast, kind, vel });
    gate = deal.gate;
    const H = this._spawn(deal, { t, pH, per, vel, tier, level, gate, fast: this._gateFast(gate, per), kind });
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
      if (bankMode === "alternate") bank = (this.altCount++ % 2 === 0) ? "A" : "B";
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
    // a step never lights more heads than the cap: it keeps whole mirrored rings (left and right, both banks), evenly
    // spread from the outside in, so the rig stays symmetric
    return steps.map((s) => {
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
    });
  }

  // ------------------------------------------------------------------------------------------------- the spawn --
  _spawn(deal, { t, pH, per, vel, tier, level, gate, fast, kind }) {
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
      id: ++this.serial, t0: t, p0: pH, vel, tier, level, gate, fast, kind, deal,
      pattern: deal.pattern, order: deal.order, colour: deal.colour, bank: deal.bank, steps, aLen,
      beams, spread, pulses: null, pi: 0, loop: null, cur: null, fired: 0, walk: 0, done: false, fading: false,
      fadeT: 0, finished: false, finishFrame: 0, tailTau: 0, peak: 0.6 + 0.5 * vel, stepOverride: 0, smearFrame: -1,
      shapes: null, lastPulseP: pH, call: deal.bank === "call", crownN: 0, holdSpawned: false, started: false, pStart: pH,
      trimPri: Infinity, thin: false,
    };
    H.crownN = deal.pattern === "star" || (deal.pattern === "crown" && tier === "hero") ? (fast ? 12 : 24) : 12;
    if (deal.pattern === "figure") {
      const seq = [deal.shape];
      for (let i = 1; i < 16; i++) seq.push(this.decks.shape.next());
      H.shapes = seq;
      H.shapeFrom = this.lastShape;
      this.lastShape = deal.shape;
    }
    if (G.kind === "short") this._anchorShort(H, G, pH, per);
    else this._startLoop(H, G, pH, per, G.span);
    this._fitHit(H, per, t);
    // a fast hit plays alone: the hits before it are choked at once, and the new hit's first pulse waits one frame if
    // one of them had its cores lit, so that "off" and the new "on" never land in one frame. Otherwise only the oldest
    // beyond maxHits fades out.
    const live = this.hits.filter((h) => !h.done && !h.fading);
    if (fast) for (const h of live) { if (h.on) H.deferFrame = this.frameIdx + 2; this._fade(h, t, 1); }
    else if (live.length >= o.maxHits) this._fade(live[0], t);
    this.hits.push(H);
    H.info = {
      id: H.id, t, vel: Math.round(vel * 1000) / 1000, tier, level, gate, pattern: deal.pattern, order: deal.order,
      colour: deal.colour, bank: deal.bank, start: startName,
      heads: [...new Set(steps.flat())].map((h) => HEADS[h].name), beams: H.beams, spread: Math.round(H.spread * 1000) / 1000,
      angle: Math.round(deal.angle * 1000) / 1000, dir: deal.dir, shape: deal.shape, hero: tier === "hero",
      sig: this._sig(deal),
    };
    return H;
  }
  _fade(h, t, tau = 40) { if (!h.fading) { h.fading = true; h.fadeT = t; h.fadeTau = tau; } }

  // Shrink a new hit until every pulse it will show fits inside 95 % (fast) or 75 % (single onset) of its budget,
  // measured at its first onset. The per-frame trim stays as the backstop, and it is sticky: a beam it takes never pops
  // back in.
  _fitHit(H, per, t) {
    // fast hits hold still while lit (a pulse changes its own area); single onsets drift, so they keep more headroom
    const cap = H.fast ? BUDGET.fast : BUDGET.single, aim = H.fast ? 0.95 : 0.75;
    const keep = { cur: H.cur, inten: H.inten, on: H.on, level01: H.level01, started: H.started, finished: H.finished, tailAge: H.tailAge, pulsesTotal: H.pulsesTotal };
    const asp = this.asp || this.o.aspect;
    this.asp = asp;
    const area = { frame: 0, window: 0 };
    for (let guard = 0; guard < 32; guard++) {
      let worstW = 0, worstF = 0;
      // the pulses this hit will really show: a short gate's own (with their groups), a loop's first eight steps
      const probe = H.pulses ? H.pulses.map((p, i) => ({ k: i, grp: p.grp, merge: p.merge, act: p.act }))
        : Array.from({ length: Math.min(H.sides ? 2 : H.steps.length, 8) }, (_, i) => ({ k: i, grp: H.sides ? 100 + i : i, act: "on" }));
      for (const pr of probe) {
        const k = H.pattern === "ladder" ? 7 : pr.k;
        H.cur = { k, grp: pr.grp, merge: pr.merge, act: pr.act === "ramp" ? "on" : pr.act, onFrame: 0, N: 1, P: H.pStart, t };
        H.inten = H.peak; H.on = true; H.level01 = H.peak; H.started = true; H.finished = false; H.tailAge = 0;
        H.pulsesTotal = H.pulses ? H.pulses.length : Infinity;
        this.bn = 0;
        this._geom(H, H.pStart + 0.3, per, t, cap);
        const n = this._write(H.fast, t, false, this.scratch, this.o.vibrate || H.gate === "tttou");
        estimateArea(this.scratch, n, asp, area);
        worstW = Math.max(worstW, area.window); worstF = Math.max(worstF, area.frame);
      }
      if (worstW <= cap.window * aim && worstF <= cap.frame * aim) break;
      // the order of giving way: a fan loses outer beams (down to 3), then the hit dims (a figure keeps its shape),
      // then a crown thins (down to 8, even), then a fan goes down to 1 beam, then the ladder's rungs, then heads
      // Each step is sized by how far over the hit is (area goes roughly with the beam count), so it settles in a
      // few passes and a press stays cheap.
      const fanLike = BEAM_SCALED.has(H.pattern);
      const crownLike = H.pattern === "crown" || H.pattern === "star";
      const ratio = Math.min(cap.window * aim / Math.max(worstW, 1e-9), cap.frame * aim / Math.max(worstF, 1e-9));
      const fewer = (n, floor) => Math.max(floor, Math.min(n - 1, Math.floor(n * ratio)));
      const fewerEven = (n, floor) => Math.max(floor, Math.min(n - 2, 2 * Math.floor(Math.floor(n * ratio) / 2)));
      if (crownLike && H.crownN > 12) { H.crownN = fewerEven(H.crownN, 12); continue; }
      if (fanLike && H.beams > 3) { const b = fewer(H.beams, 3); H.spread *= Math.pow(0.96, H.beams - b); H.beams = b; continue; }
      if (H.peak > 0.62) { H.peak = Math.max(0.6, H.peak * Math.min(0.85, ratio)); continue; }
      if (crownLike && H.crownN > 8) { H.crownN = fewerEven(H.crownN, 8); continue; }
      if (fanLike && H.beams > 1) { const b = fewer(H.beams, 1); H.spread *= Math.pow(0.96, H.beams - b); H.beams = b; continue; }
      if (H.pattern === "ladder" && (H.rungCap || 8) > 2) { H.rungCap = (H.rungCap || 8) - 1; continue; }
      // still over: every step (and push-pull side) drops its last head
      const trim = (arr) => (arr.length > 1 ? arr.slice(0, -1) : arr);
      const before = JSON.stringify([H.steps, H.sides]);
      H.steps = H.steps.map(trim);
      if (H.sides) H.sides = H.sides.map(trim);
      if (JSON.stringify([H.steps, H.sides]) === before) break;
    }
    Object.assign(H, keep);
    this.bn = 0;
    if (H.info) H.info.beams = H.beams;
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
    if (this.tPrev !== null) {
      const dt = t - this.tPrev;
      if (dt > 3 && dt < 100) this.F = this.F * 0.9 + dt * 0.1;
    }
    this.tPrev = t;
    this.nowT = t;
    this.frameIdx++;
    const per = this.period(t);
    const pos = this._commitPos(t);
    const posE = this._evalPos(t, pos);
    this.posE = posE;
    this.asp = this.o.aspect;

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
      if (H.started && H.fast) anyFast = true;     // a fast hit keeps the fast caps through its tail: nothing pops in
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
      if (!H.started || H.level01 <= 0.002) continue;
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
    const H = this._spawn(deal, { t, pH: this.posAt(t), per, vel: src.vel, tier: "held", level: Math.max(2, src.level), gate,
      fast: this._gateFast(gate, per), kind: "held" });
    // the loop starts after the press's own short gate, on the grid, and runs until release
    src.fading = false;
    const after = src.pulses ? src.pulses[src.pulses.length - 1].P + 1 / 4 : -Infinity;
    this._startLoop(H, GATES[gate], this.posAt(t), per, Infinity, after);
    if (!this.padDown) H.loop.endP = H.loop.P;
    src.info.hold = gate;
    H.info.tier = "held"; H.info.from = src.id;
    this._log(H.info);
    return H;
  }

  // the pulse state of one hit this frame
  _evalHit(H, t, posE, per) {
    if (!H.started && H.deferFrame && this.frameIdx < H.deferFrame) { H.on = false; H.inten = 0; H.level01 = 0; return; }
    const F = this.F;
    const minOn = Math.max(1, Math.ceil(FRAME_RULES.minOnMs / F - 1e-6)), minOff = Math.max(1, Math.ceil(FRAME_RULES.minOffMs / F - 1e-6));
    let newest = null, newestStep = 1 / 4;
    // reach every pulse whose onset the picture has passed; fire only the newest (a jump drops the skipped ones)
    if (H.pulses) {
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
        const nextP = H.pulses ? (H.pi < H.pulses.length ? H.pulses[H.pi].P : null) : (H.loop && H.loop.P < H.loop.endP ? H.loop.P : null);
        // (counted from THIS frame, not from the pulse's grid time: a pulse lit late must still leave the full gap)
        if (nextP !== null) { const framesTo = Math.ceil((nextP - posE) * per / F - 1e-6); N = Math.max(minOn, Math.min(N, framesTo - minOff)); }
        // the halo hold: this pulse's halo was already held lit if the last pulse held it over these same heads
        const prev = H.cur;
        const sameAsPrev = !!(prev && prev.holdHalo && sameHeads(this._litHeads(H, prev.grp, prev), this._litHeads(H, newest.grp, newest)));
        H.cur = { ...newest, onFrame: this.frameIdx, N, k: H.fired, t, sameAsPrev, holdHalo: false };
        H.fired++;
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
    const exhausted = H.pulses ? H.pi >= H.pulses.length : (H.loop && H.loop.P >= H.loop.endP - 1e-9);
    if (exhausted && !on && H.started && !H.finished) {
      H.finished = true; H.finishFrame = this.frameIdx; H.finishT = t;
      H.tailTau = Math.max(20, H.tailBeats * per / 3);
    }
    if (!H.started && exhausted) { H.done = true; return; }
    let inten = 0;
    if (on) {
      const a = ACT[H.cur.act] || ACT.on;
      inten = H.peak * a.lvl;
      if (H.cur.act === "ramp") { const x = (this.frameIdx - H.cur.onFrame + 1) / Math.max(1, H.cur.N); inten *= x * x; }
    } else if (H.finished) {
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
  _onAct(H, p, t) {
    const heads = this._litHeads(H, p.grp);
    const plucks = (amp) => { for (const h of (H.pattern === "figure" || H.pattern === "crown" || H.pattern === "star" ? [HERO_HEAD] : heads)) this._pluck(h, t, amp); };
    if (p.act === "pluck") { plucks(VIB.AMP_PX * (0.6 + 0.4 * H.vel)); this.out.events.push({ type: "pluck", head: heads.length ? HEADS[heads[0]].name : "HERO" }); }
    else if (p.act === "smear") { H.smearFrame = this.frameIdx; plucks(VIB.AMP_PX * 0.4); }
    else if (this.o.vibrate) plucks(VIB.AMP_PX * (0.5 + 0.5 * H.vel));
    if (p.act === "flash") this.out.events.push({ type: "flash", level: H.peak });
  }
  _pluck(h, t, amp) {
    const v = this.vib[h];
    const age = (t - v.t0) / 1000;
    const cur = v.offT === null || v.offT < v.t0 ? vibModes(age, v.amp, v.offT === null ? null : (t - v.offT) / 1000)[0] : 0;
    v.amp = Math.min(VIB.MAX_PX, cur * 0.5 + amp);
    v.t0 = t;
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
  _addSeg(H, h, x0, y0, x1, y1, b, nb, pri, kind, wMul = 1, iMul = 1) {
    const B = this._beam();
    B.H = H; B.h = h; B.x0 = x0; B.y0 = y0; B.x1 = x1; B.y1 = y1; B.b = b; B.nb = nb; B.pri = pri; B.kind = kind;
    B.wMul = wMul; B.iMul = iMul; B.u0 = 0; B.u1 = 1;
    return B;
  }
  _geom(H, posE, per, t, cap) {
    const k = H.cur ? H.cur.k : 0;
    const grp = H.cur ? H.cur.grp : 0;
    let heads = this._litHeads(H, grp);
    if (H.finished && !H.on && H.cur && H.cur.grp === -1) heads = this._litHeads(H, -1);
    // a fast hit never moves while lit: a still pattern is frozen for the whole hit, a moving one at each pulse's onset
    if (H.fast && H.cur) { if (STILL_IN_FAST.has(H.pattern)) { posE = H.pStart; t = H.t0; } else { posE = H.cur.P; t = H.cur.t; } }
    const ageB = posE - H.pStart, ageS = (t - H.t0) / 1000;
    const nH = Math.max(1, heads.length);
    const perHead = Math.max(1, Math.min(H.beams, cap.perHead, Math.floor(cap.beams / nH)));
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
        const all = [...new Set(H.steps.flat())];
        const ends = [];
        for (const bank of ["A", "B"]) {
          const inBank = all.filter((h) => HEADS[h].bank === bank).sort((a, b) => HEADS[a].sx - HEADS[b].sx);
          if (inBank.length) { ends.push(inBank[0]); if (inBank.length > 1) ends.push(inBank[inBank.length - 1]); }
        }
        for (const h of ends) { const [x, y] = xy(h); this._fan(H, h, x, y, aimHero(x, y), H.level >= 2 ? 2 : 1, 0.025); }
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
        for (const h of heads) { const [x, y] = xy(h); this._fan(H, h, x, y, aimHero(x, y) + (parity ? 0.32 : -0.32) * d.dir * sideOf(h), H.level >= 2 ? 2 : 1, 0.06); }
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
        const all = [...new Set(H.steps.flat())].slice(0, cap.heads);
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
        const count = Math.min(H.rungCap || 8, (H.level >= 2 ? 2 : 1) + (H.pulsesTotal > 1 ? k % 8 : 0));
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
        const origins = H.level >= 2 && heads.length < 2 ? [heads[0], HEADS[heads[0]].twin] : heads.slice(0, 2);
        const n = clamp(perHead, 6, 10), rx = 0.15 * (1 + 0.4 * vel), ry = rx * 0.55, spin = TAU * posE / 2 * d.dir;
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
        for (let s = 0; s < SHAPE_SEGS; s++) {
          const o = s * 4;
          const B = this._addSeg(H, HERO_HEAD, A[o] + (Bs[o] - A[o]) * m, A[o + 1] + (Bs[o + 1] - A[o + 1]) * m,
            A[o + 2] + (Bs[o + 2] - A[o + 2]) * m, A[o + 3] + (Bs[o + 3] - A[o + 3]) * m, s, SHAPE_SEGS, 0, KIND.FIGURE, 0.7);
          B.u0 = s / SHAPE_SEGS; B.u1 = (s + 1) / SHAPE_SEGS;
        }
        H.shapeNow = cur;
        break;
      }
    }
  }
  // a figure's segments, remembered for the frame (the spawn-time fit asks for the same figure several times)
  _shape(name, pos, R) {
    const key = `${name}|${pos}|${R}`;
    let s = this.shapeCache.get(key);
    if (!s) {
      if (this.shapeCache.size >= 8) this.shapeCache.clear();
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
    const C = this.col, k = H.cur ? H.cur.k : 0, b = B.b, nb = B.nb, h = B.h;
    const fig = B.kind === KIND.FIGURE;
    const side = fig ? Math.sign((B.x0 + B.x1) / 2 - HERO.x) : HEADS[h].side;
    const u = fig ? clamp((B.x0 + B.x1) / this.asp, -1, 1) : HEADS[h].u;
    let c;
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
        const lit = this._litHeads(H, H.cur ? H.cur.grp : 0);
        c = (lit.length > 1 ? h === lit[k % lit.length] : b === k % Math.max(1, nb)) ? C.L2 : C.L1;
        break;
      }
      case "flip": c = C.flicker[k % C.flicker.length]; break;
      case "trinity": c = C.triple[k % C.triple.length]; break;
      case "headgrad": c = lerpOk(C.L1, C.L2, (u + 1) / 2, out); break;
      case "burst": c = C.burst[(b + k) % C.burst.length]; break;
      case "barswap": {
        const swap = Math.floor(this.posE / 4) & 1, s = side;
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

  _emit(anyFast, t) {
    const out = this.out, seg = out.seg, asp = this.asp;
    const budget = anyFast ? BUDGET.fast : BUDGET.single;
    // the area budget: drop the outermost beams (highest pri) until the frame that is returned is inside it
    for (let guard = 0; guard < 24; guard++) {
      out.n = this._write(anyFast, t, true);
      const a = estimateArea(seg, out.n, asp, out.area);
      if (a.window <= budget.window && a.frame <= budget.frame) break;
      let maxPri = -1;
      for (let i = 0; i < this.bn; i++) if (this.beams[i].kind === KIND.BEAM && this.beams[i].pri > maxPri) maxPri = this.beams[i].pri;
      if (maxPri <= 0) {          // every head is down to its centre beam: thin every other beam instead
        let kept = 0, seen = 0;
        for (let i = 0; i < this.bn; i++) {
          const B = this.beams[i];
          if (B.kind === KIND.BEAM && (seen++ & 1)) { B.H.thin = true; continue; }
          if (kept !== i) { const tmp = this.beams[kept]; this.beams[kept] = B; this.beams[i] = tmp; }
          kept++;
        }
        if (kept === this.bn) break;
        this.bn = kept;
        continue;
      }
      let kept = 0;
      for (let i = 0; i < this.bn; i++) {
        const B = this.beams[i];
        if (B.kind === KIND.BEAM && B.pri === maxPri) { B.H.trimPri = Math.min(B.H.trimPri, maxPri - 1); continue; }
        if (kept !== i) { const tmp = this.beams[kept]; this.beams[kept] = B; this.beams[i] = tmp; }
        kept++;
      }
      this.bn = kept;
    }
    if (out.area.window > budget.window || out.area.frame > budget.frame) {   // still over: the frame goes dark
      out.n = 0;
      estimateArea(seg, 0, asp, out.area);
    }
    // polylines (ringing strings, figure strokes): flag each piece that runs on into the next, so the shader can leave
    // off its end cap and the joints never bead
    for (let i = 0; i + 1 < out.n; i++) {
      const o = i * SEG_FLOATS, q = o + SEG_FLOATS;
      if (seg[o + SEG.KIND] === seg[q + SEG.KIND] && seg[o + SEG.HEAD] === seg[q + SEG.HEAD]
        && Math.abs(seg[o + 2] - seg[q]) < 1e-6 && Math.abs(seg[o + 3] - seg[q + 1]) < 1e-6) {
        seg[o + SEG.FLAGS] = seg[o + SEG.FLAGS] | 2;
        seg[q + SEG.FLAGS] = seg[q + SEG.FLAGS] | 4;
      }
    }
    out.heads.fill(0); out.padGrid.fill(0);
    for (let i = 0; i < out.n; i++) {
      const o = i * SEG_FLOATS, h = seg[o + SEG.HEAD];
      if (h < 0) continue;
      const lv = seg[o + SEG.I];
      if (lv > out.heads[h]) out.heads[h] = lv;
    }
    for (let h = 0; h < HEADS.length; h++) {
      const p = HEADS[h].pad - 1;
      if (out.heads[h] > out.padGrid[p]) out.padGrid[p] = out.heads[h];
      if (h === HERO_HEAD && out.heads[h] > out.padGrid[6]) out.padGrid[6] = out.heads[h];
    }
  }
  // fitBlur: the spawn-time fit runs before the first pulse plucks the strings, so it assumes the blur band at its cap
  _write(anyFast, t, subdivide, seg = this.out.seg, fitBlur = false) {
    const rgb = [0, 0, 0];
    let n = 0;
    const put = (B, H, x0, y0, x1, y1, inten, width, glow, blur, heat, held) => {
      if (n >= MAX_SEGMENTS) return;
      const o = n * SEG_FLOATS;
      seg[o] = x0; seg[o + 1] = y0; seg[o + 2] = x1; seg[o + 3] = y1;
      seg[o + 4] = rgb[0]; seg[o + 5] = rgb[1]; seg[o + 6] = rgb[2]; seg[o + 7] = inten;
      seg[o + 8] = width; seg[o + 9] = glow; seg[o + 10] = blur; seg[o + 11] = heat;
      seg[o + 12] = B.kind; seg[o + 13] = B.h; seg[o + 14] = B.kind === KIND.FIGURE ? 0 : 0.5;
      seg[o + 15] = held ? 1 : 0;
      n++;
    };
    for (let i = 0; i < this.bn; i++) {
      const B = this.beams[i], H = B.H;
      const act = H.cur ? ACT[H.cur.act] || ACT.on : ACT.on;
      // The halo (spec 1.7): a single onset's halo follows its core. In a fast gate the halo breathes between 75 % (the
      // gap) and 100 % (the pulse) while the next pulse fires the same heads; it goes off with its core when the order
      // walks on; the tail decays smoothly. `held` tells the area estimator the halo was already lit (only the core flashes).
      const inten = H.inten * B.iMul;
      let glow = inten, held = false;
      if (H.fast) {
        if (H.finished) held = true;
        else if (H.on) { glow = H.level01 * B.iMul; held = !!(H.cur && H.cur.sameAsPrev); }
        else { glow = H.cur && H.cur.holdHalo ? 0.75 * H.level01 * B.iMul : 0; held = true; }
      }
      if (inten < 0.002 && glow < 0.002) continue;
      this._colour(H, B, rgb);
      let width = (B.kind === KIND.FIGURE ? 1.4 + 0.8 * H.vel : 1.2 + 2.4 * H.vel) * B.wMul * (H.on ? act.w : 1);
      width = Math.min(CORE_MAX_PX, width);
      let heat = (1 + 2 * H.vel) * inten * (H.on ? act.heat : 1);
      if (H.colour === "hotcore" && B.nb >= 3 && Math.abs(B.b - (B.nb - 1) / 2) < 0.6) heat *= 1.8;
      // Vibrate: the string's state for this beam's head
      const v = this.vib[B.kind === KIND.FIGURE ? HERO_HEAD : B.h];
      const ageS = (t - v.t0) / 1000, offS = v.offT === null ? null : Math.max(0, (t - v.offT) / 1000);
      const ringing = v.amp > 0 && ageS < 6 && vibModes(ageS, v.amp, offS)[0] > 0.3;
      const smear = H.smearFrame >= 0 && H.cur && H.cur.act === "smear" && H.on ? VIB.SMEAR_GAIN : 1;
      const blurCap = H.fast && smear === 1 ? VIB.BLUR_FAST_PX : VIB.BLUR_MAX_PX;
      if (fitBlur) { put(B, H, B.x0, B.y0, B.x1, B.y1, inten, width, glow, H.gate === "tttou" ? VIB.BLUR_MAX_PX : blurCap, heat, held); continue; }
      if (!subdivide || !ringing) {
        const blur = ringing ? Math.min(blurCap, VIB.BLUR_GAIN * smear * vibEnvelope(0.5 * (B.u0 + B.u1), ageS, v.amp, offS)) : 0;
        const fb = B.kind === KIND.FIGURE && ringing ? Math.min(blurCap, VIB.BLUR_GAIN * smear * figureRing(0.5 * (B.u0 + B.u1), ageS, v.amp, 0, offS, true)) : blur;
        put(B, H, B.x0, B.y0, B.x1, B.y1, inten, width, glow, fb, heat, held);
        continue;
      }
      const dx = B.x1 - B.x0, dy = B.y1 - B.y0, len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
      if (B.kind === KIND.FIGURE) {      // a closed figure rings as one loop: displace each end by its own arc place
        const d0 = figureRing(B.u0, ageS, v.amp, v.ph, offS) / REF_PX, d1 = figureRing(B.u1, ageS, v.amp, v.ph, offS) / REF_PX;
        const cx = HERO.x, cy = HERO.y;
        const r0 = Math.hypot(B.x0 - cx, B.y0 - cy) || 1, r1 = Math.hypot(B.x1 - cx, B.y1 - cy) || 1;
        const blur = Math.min(blurCap, VIB.BLUR_GAIN * smear * Math.abs(figureRing(0.5 * (B.u0 + B.u1), ageS, v.amp, 0, offS, true)));
        put(B, H, B.x0 + (B.x0 - cx) / r0 * d0, B.y0 + (B.y0 - cy) / r0 * d0, B.x1 + (B.x1 - cx) / r1 * d1, B.y1 + (B.y1 - cy) / r1 * d1,
          inten, width, glow, blur, heat, held);
        continue;
      }
      const K = VIB.SUBDIV;
      let px = B.x0, py = B.y0;
      for (let j = 1; j <= K; j++) {
        const u = j / K;
        const dd = j === K ? 0 : vibDisplacement(u, ageS, v.amp, v.ph + B.b * 0.7, offS) / REF_PX;
        const qx = B.x0 + dx * u + nx * dd, qy = B.y0 + dy * u + ny * dd;
        const blur = Math.min(blurCap, VIB.BLUR_GAIN * smear * vibEnvelope(u - 0.5 / K, ageS, v.amp, offS));
        put(B, H, px, py, qx, qy, inten, width, glow, blur, heat, held);
        px = qx; py = qy;
      }
    }
    return n;
  }
}

// a closed loop's ring: modes sin(2 pi n s) round the figure (no fixed ends), the same decay as the beams
function figureRing(s, ageS, amp, phase, offS, envelope = false) {
  const m = vibModes(ageS, amp, offS);
  let d = 0;
  for (let i = 0; i < m.length; i++) {
    const n = i + 2, f = VIB.F1_HZ * (i + 1) * (1 + VIB.INHARM * (i + 1) * (i + 1));
    d += envelope ? m[i] * Math.abs(Math.sin(TAU * n * s)) : m[i] * Math.sin(TAU * n * s + phase) * Math.cos(TAU * f * ageS + 1.3 * n);
  }
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
