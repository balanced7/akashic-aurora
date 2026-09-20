# Glide-feel prototype — brief

Author: Rill (dsh_agent), 2026-09-20. Working title: none yet — the game isn't born, the feel is.

## The promise

A Glyder 2 x Sky hybrid: open exploration, unlockable areas with stunning vistas, collectible
**wings as equipment** with realistic gliding/flying physics, updrafts to find and ride, stars and
points that unlock — and the question of weapons as a maybe-later system.

The one thing this whole game is, before it is anything else, is **the act of gliding**. If gliding
doesn't feel good in the first thirty seconds, no amount of content saves it. If it does, the rest is
systems bolted onto a proven core. So the first slice is a *feel* prototype, not a *content* one.

## Daniel's direction (folding in, 2026-09-20)

Borrow from Wipeout (the sense of SPEED — anti-gravity rush, speed pads, momentum) and Sky (the
mesmerizing glide), then make it better: **mid-air pickups that change streak distance and the wing's
CONFIGURATION mid-flight.** Two non-negotiable feels, not one: gliding must be MESMERIZING (slow,
soaring, thermal-riding) and speed must feel INCREDIBLE (dive, rush, near-ground velocity).

Consequences for the build:

- The physics core must span the WHOLE speed envelope, ~8 m/s thermal-soar to ~40 m/s dive, and feel
  good at both ends — not tuned to one.
- It must be PARAMETERIZED (Cl, Cd, bank authority, mass, wing shape) so a mid-air pickup is a
  params-swap, not a code change. (The pins already test with overrides — that is the seam.)
- Speed sensation is mostly PRESENTATION: FOV kick, camera shake, wind particles, speed lines,
  motion blur — a render layer on top of the physics, measurable, and a later slice.
- Streaks = a distance/combo meter; pickups mutate it. A systems slice, after the feel is proven.

Added success proxies: (7) a steep dive spikes airspeed hard (the speed envelope is real, not
cosmetic), (8) the model is stable at BOTH ends (no divergence diving, no stall-fall soaring).

## What this slice is

**One island, one wing, one thermal, three tunable parameters.** Prove the core loop's heart beat —
glide, dive, bank, ride a thermal, collect a star — with the smallest possible thing.

## Success criterion (pre-registered, before any code)

**Subjective (the real bar):** Daniel's thirty-second feel verdict. He is the judge; he has Glyder 2
muscle memory and the only eyes that matter here.

**Measurable proxies (so I am not flying blind, and so the numbers say "good" honestly):**
1. Stable and controllable — no divergent pitch oscillation in the recorded trajectory.
2. Energy trade works — airspeed and altitude anti-correlate (dive -> speed, climb -> spend).
3. Thermal ride — altitude GAINS when banked into the updraft column.
4. Stall exists but is recoverable — below stall speed sink rises, and a dive recovers.
5. 60 fps (`alias_verify`) and a legible frame (`floors`/`boost`).
6. The vista is readable (`ask_vision`: horizon visible, glider visible against sky, sense of height).

## Physics — a point-mass glider (tractable, tunable)

- **State:** position, airspeed, heading, pitch (angle of attack), bank.
- **Forces:** lift = Cl(AoA) * v^2 (Cl drops past the stall AoA), drag = Cd * v^2 (induced + parasitic),
  gravity, mass. Glide ratio ~15-25 for a hang-glider feel.
- **Thermals:** buoyant columns — a radius and a strength profile, 2-5 m/s at the core, 0 at the rim.
- **Wind:** a constant (later altitude-varying) vector, so ground speed and airspeed differ.
- **Integration:** fixed timestep, semi-implicit Euler (stable and dead simple).

## Controls (prototype)

Pitch up/down (angle of attack), bank left/right, and dive-for-speed via pitch-down. Keyboard
(WASD/arrows) plus mouse, gamepad later. The control *mapping* is itself tunable — the same physics
can feel like a hang-glider (forgiving) or a sailplane (punishing) purely by parameter choice.

## World (minimal, but not ugly)

Sky gradient + sun + fog; an ocean or ground plane far below (that's what makes it *feel high*);
ONE floating island as launch point and anchor; ONE thermal, faintly visible so it can be found fast
for testing; a simple wing (a few triangles); a handful of floating stars/rings for the collect loop.

## Out of scope (explicitly, for now)

Multiple islands, unlock gating, wing *variety*, weapons/combat, multiplayer, persistence, procedural
terrain, audio (stretch — wind-rush is real speed feedback, but it is a later polish).

## Files

- `arsenal/web/glider/index.html` — page (served by the arsenal server at `/glider`).
- `arsenal/web/glider/physics.js` — the point-mass glider + thermals, PURE and testable in Node.
- `arsenal/web/glider/glider.js` — loop, controls, render.
- `arsenal/web/glider/flightlog.js` — records (t, position, speed, altitude, AoA, bank) each frame.
- `tests/glider_physics.test.mjs` — RED-first pins for the physics: glide ratio, sink rate, thermal
  gain, stall + recovery, energy trade. The feel-critical numbers are verified by tests; the human
  only ever judges the art on top.

## Instruments reused (this is what the arsenal was built for)

`flightlog` -> sink rate / glide ratio / thermal gain / stall boundary; `alias_verify` -> pacing;
`floors`/`boost` -> frame legibility; `ask_vision` -> vista taste. A text-only seat can build this
because the pixels are measured and the *feel* is the human's to judge.

## The loop

build -> measure -> **Daniel flies** -> tune 3-4 parameters -> repeat. Each iteration is numbers, not
art, so it is cheap and fast.

## Open questions (recommendations inline)

1. **Pure glider for now, weapons later?** Recommend yes — the glide is identical either way.
2. **Third-person camera behind the glider?** Recommend yes — it shows the wings, which is the pitch.
3. **Keyboard + mouse for the prototype?** Recommend yes; gamepad once it feels right.
4. **Forgiving hang-glider realism over punishing sailplane?** Recommend forgiving — Glyder 2 was.
