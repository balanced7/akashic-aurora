// VJ motion library: arsenal/web/vj-motions.js (pure ES module: no DOM, no WebGL, no imports). Tests: tests/vj_motions.test.mjs.
//
// Daniel, 2026-10-27: "a library of epic satisfying motions that all fit various time budgets ... 16 variant (or however
// many are appropriate) for each of the feels, 1/32, 1/16, 1/8 etc"; before that, "repeated triggers don't do the exact
// same thing in the exact same space"; and the north star, "visual spectacle increase as well as driveable in a dynamic way
// ergonomically from the pads where each button does something worth doing visually".
//
// The build spec: research/in-flight/vj-v2-build-spec-2026-10-27.md, section A: Heimdall's design
// (research/in-flight/vj-v2-motion-library-heimdall-2026-10-27.md) with Vandor's amendment, and the pads lane's per-budget
// templates, dealer and transform deck (research/reviewed/keylab-liberation-2026-10-22/vj-v2-research-2026-10-27/
// pads.research.md). Our own code throughout; the named moves come from lighting-desk and animation vocabulary.
//
// THE SPLIT. A gate owns the PULSE cadence: when the light is on. A motion owns the MACRO cadence: where the light points
// while the pulses come, and how that look winds up, acts and settles. They compose -- the gate's pulses sample the
// motion -- so a held pad is a STANDING MOTION with its gate as the pulse carrier.
//
// What is here:
//   CLASSES     the time budgets, M32 (1/8 beat: a 1/32 note) to M4b (16 beats: four bars). M32 and M16 are TEXTURE
//               classes: a shimmer or flutter of a few pixels that never leaves a beam's own lit band. They are never a
//               whole-frame motion (at 150 BPM a whole look cycling every 1/16 is a strobe). Each whole class carries its
//               phase template (anticipation, action and settle shares, overshoot, settle swings) and its landing grid.
//   MOTIONS     the library as data: 16 named variants for every whole class M8 to M2b, 8 for M4b, 4 textures each for
//               M32 and M16. A variant is a recipe over the knobs a laser rig has -- each head's aim, the fan's spread, the
//               rotation of a figure round the hero -- in one of four forms and one easing family. The 8-card symmetry
//               deck (TRANSFORMS) makes each of them 8 renderings: 128 per whole class M8 to M2b.
//   evaluate    a variant's value at u in [0, 1] of its cycle: 0 at the start and EXACTLY its end value from u = 1 on, so it
//               lands at any frame rate and through a tempo change.
//   landing     the one landing rule: the start is never delayed (no added latency); the end stretches by 0.75x to 1.75x
//               so the settle lands on the class's grid line.
//   valueAt     a dealt motion's value at a beat position for one head: the head's place in the order (the lag across
//               heads), the transform, and the cycles of a looping motion (one that ends at a new rest swings back and
//               forth, so a loop never jumps).
//   THE FLASH RULE, at deal time: a motion whose actions would come closer than 1/3 s (more than 3 a second) is refused
//               and the dealer moves on -- another variant, a slower class, a texture, or none. It is never drawn dimmer
//               instead ("a dim stroboscope is still a stroboscope"). The laser engine's per-hit fit and per-frame check
//               stay the backstop for the AREA a motion changes.
//   MotionDealer  the five dealing layers: a shuffle-bag motion deck per class (the last two dealt never open the next
//               round), the symmetry deck, the accent of the press's place in the bar, phrase memory (a motion dealt again
//               within the last four grows; the phrase's first beat rhymes with the last phrase's), and call-and-response
//               (the answering bank plays the asking bank's motion mirrored, on the same timing). Consecutive signatures
//               differ on at least two of motion, class and transform.
//
// THE AMENDMENT (Vandor): repetition always grows SIZE (the motion's amplitude, so the spread, the aim and the rotation;
// the laser engine's own tiers add heads and a second colour), but grows PERIOD only when the player's presses leave room:
// a one-shot motion's landed end comes no later than the median of the last three press intervals after the press, so it
// lands before the next likely hit. Faster playing tightens motions; sparse playing lets escalation lengthen them
// (M8 -> M4 -> M2 -> M1). Velocity is amplitude: a soft press plays a small version, a hard one the full version.
//
// THE API (the laser engine uses all of it; a pad host or the Stage can deal motions without the 2D engine):
//   CLASSES, CLASS_IDS, MOTIONS, MOTION_IDS, TRANSFORMS, TRANSFORM_IDS, EASE      the data
//   evaluate(m, u) / valueAt(st, pos, rank, n) / landing(cls, pos) / headSign(mode, head, rank)
//   actionRateHz(m, spanBeats, perMs, {looping, intervalBeats}) / refused(...)   the flash rule
//   metricAccent(pos)   the press's place in the bar: {level, name, mul}
//   new MotionDealer({seed}) .press(pos) for EVERY press, .deal(ctx) for each hit that should move (see deal()), .reseed()
//   catalogue()         the library for a HUD or a LEVELS page

export const MOTIONS_API = "arsenal.vj-motions/v1";

const TAU = Math.PI * 2;
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const clamp01 = (x) => clamp(x, 0, 1);

// ============================================================================================================ seeds --
// A small seeded generator of the module's own (FNV-1a folding the seeds, then mulberry32, a public-domain textbook
// generator): the module imports nothing, so the Stage and the pads can deal motions without the 2D laser engine.
function seedOf(xs) {
  let h = 0x811c9dc5 | 0;
  for (const s of xs.map(String).join("|")) h = Math.imul(h ^ s.charCodeAt(0), 0x01000193);
  return h >>> 0;
}
export function seededRng(...seeds) {
  let a = seedOf(seeds);
  return function next() {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ========================================================================================================== classes --
// [id, beats, the musical division, name, texture, landing grid in beats, the phase template]. The template (pads lane,
// after grandMA3's phaser step layers and Lasseter's timing): a = anticipation share (a counter-move of depth c), T =
// action share, the rest is the settle; o = overshoot past a new rest; N = half-swings in the settle (a spring). Shares
// are of the LANDED span. The grid: strikes land on their own division, a beat or two on a beat, a bar or two on a bar
// line, four bars on a four-bar line.
const CLASS_DEFS = [
  ["M32", 1 / 8, "1/32", "Shimmer", true, 1 / 8, { a: 0, T: 0.17, o: 0, N: 0, c: 0 }],
  ["M16", 1 / 4, "1/16", "Flutter", true, 1 / 4, { a: 0, T: 0.25, o: 0, N: 0, c: 0 }],
  ["M8", 1 / 2, "1/8", "Step", false, 1 / 2, { a: 0.2, T: 0.25, o: 0.12, N: 1, c: 0.1 }],
  ["M4", 1, "1/4", "Beat", false, 1, { a: 0.25, T: 0.25, o: 0.1, N: 2, c: 0.1 }],
  ["M2", 2, "1/2", "Passage", false, 1, { a: 0.25, T: 0.35, o: 0.08, N: 1, c: 0.12 }],
  ["M1", 4, "1 bar", "Gesture", false, 4, { a: 0.25, T: 0.5, o: 0.05, N: 1, c: 0.08 }],
  ["M2b", 8, "2 bars", "Phrase", false, 4, { a: 0.125, T: 0.75, o: 0, N: 0, c: 0.05 }],
  ["M4b", 16, "4 bars", "Section", false, 16, { a: 0.25, T: 0.5, o: 0, N: 0, c: 0 }],
];
export const CLASSES = Object.freeze(Object.fromEntries(CLASS_DEFS.map(([id, beats, note, name, texture, grid, tpl]) =>
  [id, Object.freeze({ id, beats, note, name, texture, grid, tpl: Object.freeze(tpl) })])));
export const CLASS_IDS = Object.freeze(CLASS_DEFS.map((d) => d[0]));
const WHOLE = Object.freeze(CLASS_IDS.filter((c) => !CLASSES[c].texture));
// one class slower (longer), n times, within the whole classes
export function slower(cls, n = 1) { return WHOLE[clamp(WHOLE.indexOf(cls) + n, 0, WHOLE.length - 1)]; }
// the slowest whole class a gate's lit life can carry (at least M8)
export function lifeClass(lifeBeats) {
  let c = WHOLE[0];
  for (const k of WHOLE) if (CLASSES[k].beats <= Math.max(1 / 2, lifeBeats) + 1e-9) c = k;
  return c;
}
// a held pad's standing motion, by section: the stare-at-it band in the quiet sections, a bar where the floor moves
export function heldClass(section) {
  return ["break", "piano", "intro", "outro"].includes(section) ? "M2b" : section === "anti" || section === "screech" ? "M2" : "M1";
}

// ============================================================================================================= ease --
// The action's easing families (each 0 -> 1 on [0, 1]).
export const EASE = Object.freeze({
  smooth: (x) => x * x * (3 - 2 * x),
  smoother: (x) => x * x * x * (x * (6 * x - 15) + 10),
  sine: (x) => (1 - Math.cos(Math.PI * x)) / 2,
  cubic: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  expo: (x) => (x >= 1 ? 1 : (1 - Math.pow(2, -10 * x)) / (1 - Math.pow(2, -10))),    // a strike: most of the move at once
  whip: (x) => x * x * x,                                                                 // slow, then all at once
  jump: (x) => (x < 0.5 ? 0 : 1),            // a blanked jump: only ever drawn sampled at a pulse, so it moves in the dark
});

// =========================================================================================================== motions --
// A variant: V(id, label, class, recipe). The recipe's knobs, at full amplitude:
//   aim     radians each head's beams turn (by the head's sign, see headSign); rot: radians a figure, a crown or a cone
//           turns round the hero (default: aim); spread: the fan's spread multiplier, 1 + spread * value
//   mode    the sign each head takes: same (the rig turns as one), wing (left against right: a fold), parity (alternate
//           heads), bank (truss against floor), cross (wing x bank: mirrored pairs cross)
//   lag     the share of the cycle the head order is spread over (overlapping action: a domino, a ripple, a wave); every
//           head still lands at the end
//   form    pulse (anticipation -> action -> settle, the class template), pendulum (out one way, through, out the other,
//           back: two actions), double (two strokes: `first` then `second` sized), shimmer (a texture)
//   end     the value it rests at: 0 = back to rest, 1 = a new rest (a state change), between = part of the way back
//   ease    the action's easing family; jump = a blanked jump, which is always `sampled` (drawn at each pulse)
//   a T o N c   overrides of the class template
// Derived: flashes (the actions per cycle the flash rule counts), feel (settle / whip / gather) and stats (the value's
// extremes and its steepest slope, which the laser engine's fit probes and pre-aiming read).
const TEX_AIM = 0.0028;      // a texture's turn: 3 px at the far end of a full-height beam, inside the beam's own lit band
const TEX_SPREAD = 0.004;    // a texture's spread breath: under a pixel at the fan's outer beams
function V(id, label, cls, r = {}) { return { id, label, cls, ...r }; }
const LIBRARY = [
  // ---- M32: Shimmer (texture only: a sub-band accent on beams the gate holds) ----
  V("shimmer", "Shimmer", "M32", { form: "shimmer", aim: TEX_AIM }),
  V("sparkle", "Sparkle", "M32", { form: "shimmer", aim: TEX_AIM, mode: "parity" }),
  V("glint", "Glint", "M32", { form: "shimmer", aim: TEX_AIM, lag: 0.5 }),
  V("sizzle", "Sizzle", "M32", { form: "shimmer", spread: TEX_SPREAD }),
  // ---- M16: Flutter (texture only) ----
  V("flutter", "Flutter", "M16", { form: "shimmer", spread: TEX_SPREAD }),
  V("quiver", "Quiver", "M16", { form: "shimmer", aim: TEX_AIM, mode: "wing" }),
  V("tremor", "Tremor", "M16", { form: "shimmer", aim: TEX_AIM, mode: "bank" }),
  V("ripple-shimmer", "Ripple Shimmer", "M16", { form: "shimmer", aim: TEX_AIM, lag: 0.6 }),
  // ---- M8: Step, the crisp command (strike plus a buffered anticipation) ----
  V("point", "Point", "M8", { spread: -0.45, end: 1, ease: "smooth" }),
  V("release", "Release", "M8", { spread: 0.4, end: 1, ease: "expo" }),
  V("fan-open", "Fan Open", "M8", { spread: 0.5, ease: "expo" }),
  V("fan-close", "Fan Close", "M8", { spread: -0.4, ease: "smooth" }),
  V("swing", "Swing", "M8", { aim: 0.3, ease: "sine" }),
  V("domino", "Domino", "M8", { aim: 0.18, lag: 0.5, ease: "expo" }),
  V("whip-step", "Whip Step", "M8", { aim: 0.21, ease: "whip", N: 2 }),
  V("wing-fold", "Wing Fold", "M8", { aim: 0.26, mode: "wing", end: 1, ease: "smooth" }),
  V("cross-lock", "Cross Lock", "M8", { aim: -0.22, mode: "wing", end: 1, ease: "cubic" }),
  V("comb", "Comb", "M8", { aim: 0.14, mode: "parity", ease: "expo" }),
  V("rotor-45", "Rotor 45", "M8", { aim: 0.25, rot: Math.PI / 4, end: 1, ease: "smoother" }),
  V("rise", "Rise", "M8", { aim: 0.17, mode: "bank", lag: 0.25, ease: "expo" }),
  V("pinch", "Pinch", "M8", { aim: -0.17, mode: "wing", ease: "smooth" }),
  V("burst", "Burst", "M8", { aim: 0.17, mode: "wing", end: 0.3, ease: "expo" }),
  V("scissor-snap", "Scissor Snap", "M8", { aim: 0.14, mode: "cross", ease: "expo" }),
  V("step", "Step", "M8", { aim: 0.2, end: 1, ease: "jump" }),
  // ---- M4: Beat, the smallest narrative (lands on the beat) ----
  V("sweep", "Sweep", "M4", { aim: 0.5, ease: "cubic", N: 0 }),
  V("bloom-catch", "Bloom Catch", "M4", { spread: 0.6, ease: "expo", N: 1 }),
  V("tidal", "Tidal", "M4", { aim: 0.25, mode: "wing", lag: 0.4, ease: "sine" }),
  V("scissor-pass", "Scissor Pass", "M4", { aim: 0.3, mode: "cross", ease: "smooth" }),
  V("wave", "Wave", "M4", { aim: 0.25, lag: 0.6, ease: "sine" }),
  V("ping-pong", "Ping-Pong", "M4", { form: "pendulum", aim: 0.3, ease: "sine" }),
  V("rotor-90", "Rotor 90", "M4", { aim: 0.3, rot: Math.PI / 2, end: 1, ease: "smoother" }),
  V("breathe", "Breathe", "M4", { spread: 0.4, ease: "sine", N: 0 }),
  V("nod", "Nod", "M4", { aim: 0.21, mode: "bank", ease: "smooth" }),
  V("zigzag", "Zigzag", "M4", { form: "double", aim: 0.2, mode: "parity", first: 1, second: -1, ease: "expo" }),
  V("cone-turn", "Cone Turn", "M4", { aim: 0.2, mode: "wing", rot: Math.PI / 2, end: 1, ease: "smoother" }),
  V("mirror-slide", "Mirror Slide", "M4", { aim: 0.3, end: 1, ease: "smooth" }),
  V("stutter-step", "Stutter Step", "M4", { form: "double", aim: 0.3, first: 0.5, second: 1, ease: "expo" }),
  V("volley", "Volley", "M4", { form: "pendulum", aim: 0.22, mode: "parity", ease: "sine" }),
  V("bounce", "Bounce", "M4", { aim: 0.18, mode: "bank", ease: "expo", N: 3 }),
  V("shrug", "Shrug", "M4", { form: "pendulum", aim: 0.2, mode: "bank", ease: "sine" }),
  // ---- M2: Passage (two beats: a real wind-up, a real decay) ----
  V("arc", "Arc", "M2", { aim: 0.5, ease: "sine", N: 0 }),
  V("the-whip", "The Whip", "M2", { aim: 0.45, ease: "whip", c: 0.35, N: 2 }),
  V("call-answer", "Call and Answer", "M2", { aim: 0.3, mode: "bank", lag: 0.5, ease: "expo" }),
  V("wings-breathe", "Wings Breathe", "M2", { aim: 0.25, mode: "wing", spread: 0.3, ease: "sine" }),
  V("slide-x", "Slide X", "M2", { aim: 0.25, mode: "cross", ease: "smooth" }),
  V("domino-return", "Domino Return", "M2", { form: "pendulum", aim: 0.25, lag: 0.5, ease: "sine" }),
  V("iris", "Iris", "M2", { form: "pendulum", spread: -0.5, ease: "sine" }),
  V("unwind", "Unwind", "M2", { aim: 0.3, rot: 2.1, lag: 0.3, end: 1, ease: "smoother" }),
  V("star-turn", "Star Turn", "M2", { aim: 0.15, rot: Math.PI / 6, spread: -0.2, end: 1, ease: "cubic" }),
  V("pendulum", "Pendulum", "M2", { form: "pendulum", aim: 0.45, ease: "sine" }),
  V("fold-unfold", "Fold-Unfold", "M2", { form: "pendulum", aim: 0.3, mode: "wing", ease: "sine" }),
  V("tower-cross", "Tower Cross", "M2", { aim: -0.35, mode: "wing", ease: "cubic" }),
  V("helix-half", "Helix Half", "M2", { aim: 0.25, rot: Math.PI, lag: 0.25, end: 1, ease: "smoother" }),
  V("swell", "Swell", "M2", { spread: 0.45, lag: 0.3, ease: "smooth" }),
  V("recoil", "Recoil", "M2", { aim: 0.3, ease: "expo", N: 3 }),
  V("seesaw", "Seesaw", "M2", { form: "pendulum", aim: 0.3, mode: "bank", ease: "sine" }),
  // ---- M1: Gesture (a bar: a beginning, a peak and a land on the next ONE) ----
  V("phase-wave", "Phase Wave", "M1", { aim: 0.35, lag: 0.75, ease: "sine" }),
  V("gather-crown", "Gather to Crown", "M1", { spread: -0.55, ease: "smooth" }),
  V("ribbon", "Ribbon", "M1", { form: "pendulum", aim: 0.35, lag: 0.9, ease: "sine" }),
  V("storm-front", "Storm Front", "M1", { aim: 0.4, mode: "bank", lag: 0.3, ease: "cubic" }),
  V("sweep-return", "Sweep and Return", "M1", { aim: 0.55, ease: "sine", N: 0 }),
  V("rotor-180", "Rotor 180", "M1", { aim: 0.4, rot: Math.PI, end: 1, ease: "smoother" }),
  V("cage-turn", "Cage Turn", "M1", { aim: 0.4, mode: "wing", end: 1, ease: "cubic" }),
  V("converge-release", "Converge and Release", "M1", { spread: -0.6, ease: "expo", N: 2 }),
  V("cross-bloom", "Cross Bloom", "M1", { aim: 0.3, mode: "cross", spread: 0.4, ease: "smooth" }),
  V("bloom-bar", "Bloom", "M1", { spread: 0.6, ease: "sine" }),
  V("curtain", "Curtain", "M1", { aim: 0.3, lag: 0.8, ease: "smooth" }),
  V("wings-bar", "Wings", "M1", { aim: 0.3, mode: "wing", spread: 0.25, ease: "sine" }),
  V("climb", "Climb", "M1", { aim: 0.3, mode: "bank", lag: 0.75, ease: "smooth" }),
  V("tower-trade", "Tower Trade", "M1", { form: "pendulum", aim: 0.3, mode: "parity", ease: "sine" }),
  V("crest", "Crest", "M1", { aim: 0.3, mode: "bank", lag: 0.6, ease: "sine" }),
  V("tsunami", "Tsunami", "M1", { aim: 0.45, lag: 0.5, spread: 0.3, ease: "cubic" }),
  // ---- M2b: Phrase (two bars: the "stare at it for a long time" band) ----
  V("cathedral", "Cathedral", "M2b", { aim: 0.15, rot: TAU, spread: -0.5, ease: "smoother" }),
  V("breathing-room", "Breathing Room", "M2b", { spread: 0.45, ease: "sine" }),
  V("cascade", "Cascade", "M2b", { aim: 0.35, lag: 0.85, ease: "smoother" }),
  V("orbit", "Orbit", "M2b", { form: "pendulum", aim: 0.4, rot: 0.8, ease: "sine" }),
  V("lissajous", "Lissajous", "M2b", { form: "pendulum", aim: 0.3, mode: "wing", lag: 0.5, ease: "sine" }),
  V("rotor-360", "Rotor 360", "M2b", { aim: 0.45, rot: TAU, end: 1, ease: "smoother" }),
  V("wings-open", "Wings Open", "M2b", { aim: 0.42, mode: "wing", end: 1, ease: "smoother" }),
  V("fan-to-cage", "Fan to Cage", "M2b", { aim: 0.3, mode: "wing", spread: -0.4, end: 1, ease: "smoother" }),
  V("wheel", "Wheel", "M2b", { form: "pendulum", aim: 0.3, lag: 0.9, ease: "sine" }),
  V("tidal-long", "Long Tide", "M2b", { aim: 0.35, mode: "bank", lag: 0.6, ease: "sine" }),
  V("helix", "Helix", "M2b", { aim: 0.3, rot: Math.PI, lag: 0.4, end: 1, ease: "smoother" }),
  V("swell-long", "Long Swell", "M2b", { spread: 0.5, ease: "smoother" }),
  V("drift-wide", "Wide Drift", "M2b", { aim: 0.25, ease: "sine" }),
  V("constellation-turn", "Constellation Turn", "M2b", { aim: 0.2, mode: "parity", rot: 0.8, end: 1, ease: "smoother" }),
  V("mirror-world", "Mirror World", "M2b", { form: "pendulum", aim: 0.3, mode: "bank", ease: "sine" }),
  V("charge", "Charge", "M2b", { spread: -0.6, ease: "whip", N: 1 }),
  // ---- M4b: Section (four bars: almost still, never frozen) ----
  V("drift", "Drift", "M4b", { aim: 0.1, rot: Math.PI / 2, ease: "sine" }),
  V("ember", "Ember", "M4b", { form: "pendulum", spread: 0.3, ease: "sine" }),
  V("sky-turn", "Sky Turn", "M4b", { aim: 0.2, rot: Math.PI, end: 1, ease: "smoother" }),
  V("tide", "Tide", "M4b", { aim: 0.25, mode: "bank", lag: 0.5, ease: "sine" }),
  V("glacier", "Glacier", "M4b", { aim: 0.15, mode: "wing", ease: "smoother" }),
  V("halo-drift", "Halo Drift", "M4b", { form: "pendulum", aim: 0.12, rot: 0.6, ease: "sine" }),
  V("long-wave", "Long Wave", "M4b", { aim: 0.25, lag: 0.8, ease: "sine" }),
  V("vault", "Vault", "M4b", { aim: 0.3, mode: "wing", spread: -0.3, end: 1, ease: "smoother" }),
];

// the value at u (0 -> 1): anticipation, action, settle (the class template), forced exactly to `end` from u = 1 on
export function evaluate(m, u) {
  if (!(u > 0)) return 0;
  if (u >= 1) return m.end;
  switch (m.form) {
    case "pendulum": return Math.sin(TAU * EASE[m.ease](u));
    case "double": return u < 0.5 ? m.first * stroke(m, 2 * u) : m.second * stroke(m, 2 * u - 1);
    case "shimmer": return Math.sin(TAU * u);
    default: return pulse(m, u);
  }
}
// the settle's window: 1 -> 0 with no slope at either end (so the settle never kinks into rest)
const settleWindow = (s) => 1 - s * s * (3 - 2 * s);
function pulse(m, u) {
  const { a, T, c, end } = m, peak = end > 0 ? 1 + m.o : 1;
  if (u < a) return -c * EASE.sine(u / a);
  const s0 = a + T;
  if (u < s0) return -c + (peak + c) * EASE[m.ease]((u - a) / T);
  const s = (u - s0) / (1 - s0);
  return end + (peak - end) * settleWindow(s) * Math.cos(Math.PI * m.N * s);
}
// one stroke of a double: out on the action, back through the settle, at rest at both ends
function stroke(m, x) {
  if (x < m.T) return EASE[m.ease](x / m.T);
  const s = (x - m.T) / (1 - m.T);
  return settleWindow(s) * Math.cos(Math.PI * m.N * s);
}

function finish(v) {
  const C = CLASSES[v.cls];
  const form = v.form || "pulse";
  const m = { form, ease: "smooth", aim: 0, spread: 0, mode: "same", lag: 0, end: 0, first: 1, second: -1, sampled: false,
    ...C.tpl, ...v };
  if (form !== "pulse") m.end = 0;                       // two-sided forms always come back to rest
  if (m.ease === "jump") m.sampled = true;
  if (m.rot === undefined) m.rot = m.aim;
  m.texture = C.texture;
  m.flashes = m.texture ? 0 : form === "pendulum" || form === "double" ? 2 : 1;
  m.feel = m.spread < 0 ? "gather" : m.ease === "whip" || m.ease === "expo" || m.N >= 2 || form === "double" ? "whip" : "settle";
  // the extremes and the steepest slope, sampled (the laser engine's fit probes the extremes; pre-aiming reads the slope)
  const K = 512;
  let max = -Infinity, min = Infinity, argMax = 0, argMin = 0, slope = 0, argSlope = 0, prev = evaluate(m, 0);
  for (let i = 1; i <= K; i++) {
    const u = i / K, x = evaluate(m, u);
    if (x > max) { max = x; argMax = u; }
    if (x < min) { min = x; argMin = u; }
    const d = Math.abs(x - prev) * K;
    if (d > slope && m.ease !== "jump") { slope = d; argSlope = u; }
    prev = x;
  }
  m.stats = Object.freeze({ max, min, argMax, argMin, slope, argSlope });
  return Object.freeze(m);
}
export const MOTIONS = Object.freeze(Object.fromEntries(LIBRARY.map((v) => [v.id, finish(v)])));
export const MOTION_IDS = Object.freeze(Object.keys(MOTIONS));
export const CLASS_MOTIONS = Object.freeze(Object.fromEntries(CLASS_IDS.map((c) =>
  [c, Object.freeze(MOTION_IDS.filter((id) => MOTIONS[id].cls === c))])));

// ========================================================================================================== landing --
// The one landing rule. The start is the press (or the first pulse): never delayed, so a motion adds no latency. The end
// is the first grid line of the class at or after start + 0.75 of its length, so the span stretches by 0.75x to 1.75x
// and the settle lands exactly on the grid (a beat, a bar line). Pure beats: a tempo change moves the times, never the
// landing. Returns {p0, p1, k = the stretch}.
export function landing(cls, pos) {
  const C = CLASSES[cls] || CLASSES.M4;
  const p1 = Math.ceil((pos + 0.75 * C.beats) / C.grid - 1e-9) * C.grid;
  return { p0: pos, p1, k: (p1 - pos) / C.beats };
}

// The heads' signs (which way each head turns) for a mode. head = {side: -1 | 0 | 1, bank: "A" | "B" | "S" | "H", lower:
// below the hero}; rank = the head's place in the order. The hero (bank H) turns the motion's own way in every mode.
export function headSign(mode, head, rank = 0) {
  if (head.bank === "H") return 1;
  const side = head.side || 1, bank = head.lower ? -1 : 1;
  switch (mode) {
    case "wing": return side;
    case "parity": return rank & 1 ? -1 : 1;
    case "bank": return bank;
    case "cross": return side * bank;
    default: return 1;
  }
}

// A dealt motion's cycle position at beat pos: u in [0, 1] and the cycle's index c. A one-shot runs once from p0 to p1; a
// looping motion's first cycle runs p0 -> p1 (landed on the grid) and each next one `beats` long, so every cycle ends on
// a grid line.
export function cycleAt(st, pos) {
  if (!(pos > st.p0)) return { u: 0, c: 0 };
  if (!st.looping || pos < st.p1) return { u: clamp01((pos - st.p0) / Math.max(1e-9, st.p1 - st.p0)), c: 0 };
  const x = (pos - st.p1) / st.beats;
  return { u: x - Math.floor(x), c: 1 + Math.floor(x) };
}
// A dealt motion's value at beat pos for the head of rank `rank` of n (signs not applied). st = {m, p0, p1, beats,
// looping, rev, rotK}. A looping motion that ends at a new rest swings back on every other cycle (a loop never jumps).
// Rev runs the head order and the time backward; Rot(k) starts the order wave k heads round. A texture never lands: it
// is a standing shimmer locked to its class's grid, showing at each grid point the next of five phases (2/5 of a turn
// apart), so a gate that samples it every 1, 2 or 4 grid points still sees it change; the order spreads its phase.
export function valueAt(st, pos, rank = 0, n = 1) {
  const m = st.m;
  let r = rank;
  if (n > 1) { if (st.rev) r = n - 1 - r; if (st.rotK) r = (r + st.rotK) % n; }
  const spread = n > 1 ? r / (n - 1) : 0;
  if (m.texture) return Math.sin(TAU * (0.4 * (pos - st.p0) / st.beats + m.lag * spread));
  const { u, c } = cycleAt(st, pos);
  const back = !!st.rev !== (st.looping && m.end !== 0 && (c & 1) === 1);
  const uh = m.lag > 0 && n > 1 ? clamp01((u - m.lag * spread) / (1 - m.lag)) : u;
  return evaluate(m, back ? 1 - uh : uh);
}

// ======================================================================================================= flash rule --
// The flash rule (gate v2's 3 a second, applied to the MACRO cadence, at deal time): an action is a swing of the light
// out and back over the same ground. Its rate is the actions per cycle over the cycle (a looping motion's cycles follow
// each other); for a one-shot, its own actions' spacing, or -- with one action -- the press interval (the next press brings
// the next action). A motion over 3 a second is refused, never drawn dimmer. Textures have no action (they never leave
// their beams' lit band). spanBeats: the landed span (the shortest cycle).
export const MAX_FLASH_HZ = 3;
export function actionRateHz(m, spanBeats, perMs, { looping = false, intervalBeats = Infinity } = {}) {
  if (!(m.flashes > 0)) return 0;
  const cycle = Math.max(1e-6, spanBeats * perMs);
  let gap = looping || m.flashes > 1 ? cycle / m.flashes : Infinity;
  if (!looping && Number.isFinite(intervalBeats)) gap = Math.min(gap, intervalBeats * perMs);
  return 1000 / gap;
}
export function refused(m, spanBeats, perMs, opts = {}) { return actionRateHz(m, spanBeats, perMs, opts) > MAX_FLASH_HZ + 1e-9; }

// =================================================================================================== metric accent --
// Where the press lands in the bar sets the motion's size (Lerdahl and Jackendoff's metrical grid: an accent falls where
// many beat levels line up; the multipliers are the pads lane's design values). Within 1/16 beat of the point counts.
export const ACCENTS = Object.freeze([
  { level: 6, name: "phrase", grid: 32, off: 0, mul: 1.1 }, { level: 5, name: "bar", grid: 4, off: 0, mul: 1 },
  { level: 4, name: "beat 3", grid: 4, off: 2, mul: 0.85 }, { level: 3, name: "beat", grid: 1, off: 0, mul: 0.75 },
  { level: 2, name: "off-beat", grid: 1 / 2, off: 0, mul: 0.65 }, { level: 1, name: "16th", grid: 1 / 4, off: 0, mul: 0.55 },
]);
const ACCENT_32ND = Object.freeze({ level: 0, name: "32nd", mul: 0.45 });
export function metricAccent(pos, tol = 1 / 16) {
  for (const A of ACCENTS) {
    const d = (((pos - A.off) % A.grid) + A.grid) % A.grid;
    if (Math.min(d, A.grid - d) <= tol + 1e-9) return A;
  }
  return ACCENT_32ND;
}

// ======================================================================================================= transforms --
// The symmetry deck (8 cards). Mx: every head turns the other way. My: the floor bank and the lower heads turn against
// the truss. Rev: the head order and the time run backward (anticipation and settle swap). Rot: the order wave starts k
// heads round. Col: the hit's two laser colours swap roles.
export const TRANSFORMS = Object.freeze({
  I: Object.freeze({ mx: 0, my: 0, rev: 0, rot: 0, col: 0 }), Mx: Object.freeze({ mx: 1, my: 0, rev: 0, rot: 0, col: 0 }),
  My: Object.freeze({ mx: 0, my: 1, rev: 0, rot: 0, col: 0 }), MxMy: Object.freeze({ mx: 1, my: 1, rev: 0, rot: 0, col: 0 }),
  Rev: Object.freeze({ mx: 0, my: 0, rev: 1, rot: 0, col: 0 }), RevMx: Object.freeze({ mx: 1, my: 0, rev: 1, rot: 0, col: 0 }),
  Rot: Object.freeze({ mx: 0, my: 0, rev: 0, rot: 1, col: 0 }), Col: Object.freeze({ mx: 0, my: 0, rev: 0, rot: 0, col: 1 }),
});
export const TRANSFORM_IDS = Object.freeze(Object.keys(TRANSFORMS));
// a transform's name from its flags (a response's My on top of the ask's card can make a pair no single card names)
function xfName(f) {
  const id = TRANSFORM_IDS.find((k) => { const t = TRANSFORMS[k]; return t.mx === f.mx && t.my === f.my && t.rev === f.rev && t.rot === f.rot && t.col === f.col; });
  if (id) return id;
  return [f.rev && "Rev", f.mx && "Mx", f.my && "My", f.rot && "Rot", f.col && "Col"].filter(Boolean).join("+");
}
// the phrase rhyme: the first beat of each phrase plays the last phrase's opening motion through the next card here
const RHYME = Object.freeze(["I", "Mx", "Rev", "RevMx"]);

// ============================================================================================================ dealer --
// A shuffle-bag: every card once a round, and never either of the two cards dealt last while another legal card is left
// (so a new round never opens with them). next() looks at up to `look` legal cards and deals the one score() rates highest
// (ties keep bag order); null if no card is legal.
class Bag {
  constructor(cards, rng) { this.cards = cards.slice(); this.rng = rng; this.hist = []; this.shuffle(); }
  shuffle() {
    const a = this.cards.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(this.rng() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
    this.order = a; this.i = 0;
  }
  next(legal = null, score = null, look = 1) {
    const fresh = (c) => !this.hist.includes(c) && (!legal || legal(c));
    return this._scan(fresh, score, look) ?? this._scan(legal, score, look);
  }
  _scan(legal, score, look) {
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
        this.order.splice(best, 1); this.order.splice(this.i, 0, c); this.i++;
        this.hist.push(c); if (this.hist.length > 2) this.hist.shift();
        return c;
      }
      this.shuffle();
    }
    return null;
  }
}
// what makes two variants look alike (the farthest-of-three draw keeps consecutive hits apart)
const featureOf = (m) => [m.form, m.mode, Math.sign(m.spread), m.lag > 0, m.end > 0, m.ease];
const distance = (a, b) => a.reduce((n, x, i) => n + (x !== b[i] ? 1 : 0), 0);

export const AMP_MAX = 1.6;              // the most a motion grows (hard velocity, a phrase accent, escalation, memory)
export const RESPOND_BEATS = Math.sqrt(32);     // an answer within this many beats of the ask (the laser engine's escalate edge)
const DEAL_DEFAULTS = Object.freeze({
  pos: 0, perMs: 400, vel: 0.7, tier: "burst", level: 1, looping: false, lifeBeats: 1 / 2, section: "any", bank: "both",
  variety: 1, pin: null, pinClass: null, colourSame: false, twoColours: true, fine: false, gaps: true, stillFast: false,
});

export class MotionDealer {
  constructor({ seed = 1 } = {}) { this.seed = seed; this.presses = []; this.reseed(seed, 0); }
  // new decks and a fresh phrase memory (a new section starts its own story); the press history carries on (the pace)
  reseed(seed = this.seed, salt = 0) {
    this.seed = seed;
    this.rng = seededRng(seed, "motions", salt);
    this.bags = new Map();
    this.xfBag = new Bag(TRANSFORM_IDS, seededRng(seed, "transforms", salt));
    this.mem = []; this.recent = []; this.last = null; this.phraseOne = null;
  }
  // every press, including those that only extend a running roll (they set the player's pace)
  press(pos) { if (Number.isFinite(pos)) { this.presses.push(pos); if (this.presses.length > 4) this.presses.shift(); } }
  // the last three press intervals (beats), newest last
  intervals() { const p = this.presses, out = []; for (let i = Math.max(1, p.length - 3); i < p.length; i++) out.push(p[i] - p[i - 1]); return out; }
  medianInterval() {
    const iv = this.intervals().sort((a, b) => a - b);
    return iv.length ? (iv.length % 2 ? iv[iv.length >> 1] : (iv[iv.length / 2 - 1] + iv[iv.length / 2]) / 2) : Infinity;
  }
  _bag(cls) {
    let b = this.bags.get(cls);
    if (!b) { b = new Bag(CLASS_MOTIONS[cls], seededRng(this.seed, "bag", cls, this.bags.size)); this.bags.set(cls, b); }
    return b;
  }

  // Deal one hit's motion, or null (no motion). ctx (all optional):
  //   pos, perMs        the press's beat position and the beat's length now (ms)
  //   vel, level        velocity 0..1; the laser engine's escalation level 1..3 (repetition within a bar)
  //   tier              burst | escalate | hero | flicker | rapid | held | phrase (the laser engine's tiers)
  //   looping, lifeBeats  a loop's motion cycles until it stops; a one-shot's class is sized to the gate's lit life
  //   section, bank     the section (a held motion's class); the hit's bank (A | B | ...: call-and-response)
  //   variety, pin, pinClass   0 = rehearsal (one motion, as written); a pinned motion id ("off" = none); a pinned class
  //   colourSame, twoColours   no colour-swap card while the colour is held or the theme has one laser colour
  //   fine              a 16th roll (its texture is M32)
  //   gaps              the hit has dark gaps between pulses (a blanked jump needs one to move in)
  //   stillFast         a fast hit on a still pattern: it holds its halos through the gaps, so no texture
  // Returns {id, label, cls, beats, m, xf, mx, my, rev, rot, rotK, col, amp, esc, accent, response, rhyme, looping, p0, p1,
  // sig, bank} (p0/p1 landed from pos; a host that starts the motion elsewhere re-lands it with landing()).
  deal(ctx = {}) {
    const c = { ...DEAL_DEFAULTS, ...ctx };
    if (c.pin === "off" || (c.pin && !MOTIONS[c.pin])) return null;
    const v0 = c.variety <= 0;
    const interval = this.medianInterval();
    const esc = c.tier === "hero" ? 2 : clamp((c.level | 0) - 1, 0, 2);
    const accent = metricAccent(c.pos);
    const span = (cls) => { const L = landing(cls, c.pos); return Math.min(L.p1 - L.p0, CLASSES[cls].beats); };
    const ok = (id, cls) => {
      const m = MOTIONS[id];
      if (m.sampled && !c.gaps) return false;
      return !refused(m, span(cls), c.perMs, { looping: c.looping, intervalBeats: interval });
    };
    // a motion carried over (an answer, a kept motion) swaps the colours only while that is still allowed
    const colOk = c.twoColours && !c.colourSame;
    const carry = (r, my = r.my) => ({ mx: r.mx, my, rev: r.rev, rot: r.rot, col: colOk ? r.col : 0 });
    // the classes to try, best first
    let classes;
    if (c.pin) classes = [c.pinClass && CLASSES[c.pinClass] ? c.pinClass : MOTIONS[c.pin].cls];
    else if (c.pinClass && CLASSES[c.pinClass]) classes = [c.pinClass];
    else if (c.tier === "rapid") classes = c.stillFast ? [] : [c.fine ? "M32" : "M16"];
    else if (c.looping) {
      // a loop lands every cycle, so its class only has to pass the flash rule: from the wanted class, slower
      const base = c.tier === "held" ? heldClass(c.section) : lifeClass(c.lifeBeats);
      classes = WHOLE.slice(WHOLE.indexOf(slower(base, esc)));
    } else {
      // a one-shot: sized to the gate's lit life, one class longer with escalation, and never longer than lands before
      // the next likely press (the amendment); then the textures, when no whole motion lands in time or passes
      const want = slower(lifeClass(c.lifeBeats), Math.min(esc, 1));
      classes = WHOLE.slice(0, WHOLE.indexOf(want) + 1).reverse()
        .filter((k) => landing(k, c.pos).p1 - c.pos <= interval + 1e-9);
      if (!c.stillFast) classes.push("M16", "M32");
    }
    const pressGap = this.presses.length >= 2 ? this.presses[this.presses.length - 1] - this.presses[this.presses.length - 2] : Infinity;
    for (const cls of classes) {
      const legal = (id) => ok(id, cls);
      let id = null, flags = null, rhyme = -1, response = false;
      const pf = this.phraseOne, last = this.last;
      if (c.pin) {
        id = legal(c.pin) ? c.pin : null;            // (a pin plays at its own class or the pinned one, past the bags)
        if (v0) flags = { ...TRANSFORMS.I };
      } else if (!v0 && accent.level === 6 && pf && pf.cls === cls && legal(pf.id)) {
        rhyme = (pf.rhyme + 1) % RHYME.length; id = pf.id; flags = { ...TRANSFORMS[RHYME[rhyme]] };
      } else if (!v0 && last && !last.response && last.cls === cls && pressGap <= RESPOND_BEATS + 1e-9
        && ((last.bank === "A" && c.bank === "B") || (last.bank === "B" && c.bank === "A")) && legal(last.id)) {
        // the answering bank plays the asking bank's motion, mirrored top for bottom, on the same timing
        response = true; id = last.id; flags = carry(last, 1 - last.my);
      } else if (v0) {
        id = CLASS_MOTIONS[cls].find(legal) || null; flags = { ...TRANSFORMS.I };
      } else if (c.variety < 1 && last && last.cls === cls && legal(last.id) && this.rng() >= c.variety) {
        id = last.id; flags = carry(last);
      } else {
        const recent = this.recent;
        id = this._bag(cls).next(legal, (k) => (recent.length ? Math.min(...recent.map((f) => distance(featureOf(MOTIONS[k]), f))) : 1)
          + this.rng() * 0.05, 3);
      }
      if (!id) continue;
      const m = MOTIONS[id];
      if (!flags) flags = { ...TRANSFORMS[this._dealTransform(m, id, cls, c)] };
      return this._record(m, id, cls, flags, c, { esc, accent, response, rhyme });
    }
    return null;
  }
  // a fresh transform card: Col only with two laser colours and the colour not held, Rot only for a motion with an order
  // wave; and the signature (motion, class, transform) differs from the last on at least two axes (a pinned motion only
  // has the transform left to vary)
  _dealTransform(m, id, cls, c) {
    const last = this.last, colOk = c.twoColours && !c.colourSame;
    const legal = (x) => {
      const t = TRANSFORMS[x];
      if (t.col && !colOk) return false;
      if (t.rot && !(m.lag > 0)) return false;
      if (!last || c.variety <= 0 || c.pin) return true;
      return (id !== last.id) + (cls !== last.cls) + (x !== last.xf) >= 2;
    };
    return this.xfBag.next(legal) || this.xfBag.next((x) => legal(x) || x === "I") || "I";
  }
  _record(m, id, cls, flags, c, { esc, accent, response, rhyme }) {
    const L = landing(cls, c.pos);
    const memBoost = 1 + 0.15 * this.mem.filter((x) => x === id).length;
    const amp = Math.min(AMP_MAX, (0.4 + 0.6 * clamp01(c.vel)) * accent.mul * (1 + 0.2 * esc) * memBoost * (response ? 1.1 : 1));
    const xf = xfName(flags);
    const rec = { id, label: m.label, cls, beats: CLASSES[cls].beats, m, xf, mx: flags.mx, my: flags.my, rev: flags.rev,
      rot: flags.rot, rotK: flags.rot ? 1 + Math.floor(this.rng() * 7) : 0, col: flags.col, amp, esc, accent: accent.name,
      response, rhyme: rhyme >= 0, looping: !!c.looping, p0: L.p0, p1: L.p1, sig: `${id}|${cls}|${xf}`, bank: c.bank };
    this.mem.push(id); if (this.mem.length > 4) this.mem.shift();
    this.recent.push(featureOf(m)); if (this.recent.length > 4) this.recent.shift();
    if (accent.level === 6) this.phraseOne = { id, cls, rhyme: Math.max(0, rhyme) };
    this.last = rec;
    return rec;
  }
}

// The library, for a HUD or a LEVELS page.
export function catalogue() {
  return {
    api: MOTIONS_API,
    classes: CLASS_IDS.map((id) => { const C = CLASSES[id]; return { id, beats: C.beats, note: C.note, name: C.name, texture: C.texture, count: CLASS_MOTIONS[id].length }; }),
    motions: MOTION_IDS.map((id) => { const m = MOTIONS[id]; return { id, label: m.label, cls: m.cls, feel: m.feel, texture: m.texture, form: m.form }; }),
    transforms: TRANSFORM_IDS.slice(),
  };
}
