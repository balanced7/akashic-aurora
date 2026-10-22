---
akashic_id: art_20261022_a16-d2-bindings-faders-knobs_72e3da
akashic_sha: e32747c3e549
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d2-bindings-faders-knobs
gist: "A16 D2: faders and knobs unbound by default, touch-and-pick learn, pickup takeover, shader colour/intensity"
visibility: fleet
body_type: markdown
seats: [claude]
category: []
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:19"
updated: "2026-10-22T14:29:19"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d2-bindings-faders-knobs_72e3da -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d2-bindings-faders-knobs

# A16 D2: faders and knobs link to anything (shader colour and intensity first)

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Wish W297 · Builds on D0 (control events), D1 (MIX mode).

## The ask
- "for shaders the fades and knobs can change shader parameters like color or intensity."
- "the fades for mixer is dumb, i want them unassociated so I can link them to whatever by default."

## What exists today (evidence)
- **One param schema for every surface** already exists. `arsenal/params.py` and `arsenal/web/lib/params.js`
  (ef5c2a3d) define descriptors:
  `{id, group, label, type: range|choice|toggle|colour|vec, range{min,max,step}, default, curve: linear|log|exp, uniform, cost, recBlocked}`.
  Controls are generated from them by `params-ui.js`, whose consumers are the bench Inspector, the Studio
  drawer, First Light, Play, Gyre and Wind (research/.../evidence-shader-params-vfx-2026-10-22.md §1).
- **First Light already has MIDI learn:** CC → `hue` / `intensity`, persisted in localStorage
  (arsenal/web/first-light.js:763-843). Its spec says "a knob on his Arturia KeyLab 88 mk3 turns the hue"
  (arsenal/FIRST-LIGHT-SPEC.md:8).
- **Piano look parameters** (`intensity`, `motion`, `journey`, …) live in the looks registry with `apply()`
  functions (arsenal/web/piano/looks/registry.js:107-177). `fromLooksDescriptor()` adapts them into the shared
  schema (params.js:737-751).
- **Shader Lab live rendering is behind a switch that stays off** until its README's owed items close
  (arsenal/web/shaderlab/README.md).
- The hardware:
  - faders CC 105-113 are absolute, with capacitive touch CC 28-37;
  - knobs CC 91-104 are relative around 64, with touch CC 8-15 and 38;
  - LCD screens 28/29 draw a knob or fader graphic with a live 0-127 bar;
  - Arturia's script has no soft takeover: a fader jumps the parameter (evidence-control-map §1, §4, §5).

## Design

**Unbound by default.** Out of the box, no fader or knob means anything. Daniel's rule beats FL's habit of
making them mixer strips.

**A binding** links one control to one target. It belongs to the lease holder's mode (D1), and it is saved
per page and per mode. The targets are:
- `param`: any descriptor a page declares, for example First Light `intensity`, a piano look `motion`, or a VFX
  Bench uniform.
- `fl`: a plugin or mixer parameter through our FL script (D8), only if Daniel binds one.
- `obs`: a source volume or a filter value (D5).
- `hub`: the hub's own settings, for example pad brightness and theme hue.

Pages **declare** their parameters to the hub (`POST /api/intent {declare: [descriptors]}`) with the schema
they already use, so the hub never needs page-specific code.

**Learning a binding, in one gesture:**
1. **Touch** the fader or knob. Its touch sensor fires, and the LCD asks "bind fader 3 to…?".
2. Then do either of these:
   - click the parameter's control on the page, which posts `declare + pick`;
   - or turn the dial through the page's declared list on the LCD and click it.
3. Done. The binding shows on the LCD in the parameter's colour.

A long touch on a bound control with the dial clicked unbinds it. First Light's existing learn moves to the
hub, and its local map is migrated once.

**Moving a bound control:**
- **Knobs** are relative, so they never jump: a detent maps to the descriptor's `step`, and the `curve` is
  honoured.
- **Faders** are absolute, so they use **pickup**. While the fader's position and the parameter's value
  disagree, the fader does nothing until it crosses the value. The LCD's fader screen shows both marks, so
  your hand knows which way to go. Touching the fader shows that screen at once. This is the soft takeover
  that W297 promised and Arturia never built.
- **Colour parameters** (`type: colour`) take three controls at once, picked in OKLCH: lightness, chroma, hue.
  The default is three adjacent faders. The pads under them preview the colour, snapped LED-safe.
- **Rate:** the hub forwards events immediately and coalesces each control at the page's frame rate (at most
  120 Hz). Shader uniforms update on the next frame.

**Safety:**
- A descriptor flagged `cost: true` (it changes GPU cost) moves only in MIX mode with the LCD showing
  "costly".
- `recBlocked` parameters ignore controls while the page is recording.
- Shader Lab targets refuse binding while its live switch is off, and the LCD says why.

## Requirements
- R2.1 MUST: no control has a binding by default, on any page or mode.
- R2.2 MUST: pages declare targets in the existing param schema. The hub has no page-specific parameter code.
- R2.3 MUST: learning is touch plus pick, with no menus to dig through.
- R2.4 MUST: a bound fader never jumps its parameter; it takes over only on crossing the value (pinned with
  synthetic fader streams).
- R2.5 MUST: knob deltas honour the descriptor's step, range and curve.
- R2.6 MUST: colour targets are picked perceptually (OKLCH) and previewed on the pads with the LED-safe snap.
- R2.7 MUST: bindings persist per page and per mode, and survive a hub restart.
- R2.8 MUST: `cost`, `recBlocked` and the Shader Lab live switch are respected.
- R2.9 SHOULD: fader movement to page uniform stays under 16 ms p95 on the host leg.

## Deliverables
- D2.1 the binding table and pickup logic in the hub. Accepted when pins (synthetic streams) cover no-jump
  pickup, relative step and curve, persistence and refusals, all green in a clean worktree.
- D2.2 a page client helper, `arsenal/web/lib/keylab-client.js`. It declares the page's descriptors, receives
  control events and applies them through the page's own setter. Accepted on First Light: you touch a fader,
  click "intensity", and the glow follows the fader with no jump (video).
- D2.3 the VFX Bench on the same helper. This is a cross-arc edge into A12's page, delivered as a snippet that
  the page's owner mounts. Accepted when a knob turns a bench uniform live.
- D2.4 the LCD fader/knob screens (28/29). Accepted when touching a bound control shows its name, value bar and
  pickup mark.

## Probes it depends on
- P2: the control census, confirming the CC numbers and touch on this unit.
- P15: the native knob and fader popups.
- P21: latency.

## Open questions for Daniel
- Should fader 9 (master) stay free like the rest, or always be the "master intensity" of whatever page is in
  front?
- Colour on faders: three faders for lightness, chroma and hue, or one fader for hue with chroma and lightness
  on knobs?

## Out of scope
FL mixer-strip mode (it exists only if you bind it); the sound room's macro pages (R track).
