---
akashic_id: art_20260709_aurora-glass-build-plan-claude-track_57688b
akashic_sha: 3754f570fbf9
status: fossil
type: design
date: 2026-07-09
title: Aurora Glass — Build Plan (claude track)
gist: "_Parallel UI-design task, 2026-07-04. Grounded in [ui-moodboard-claude.md](ui-moodboard-claude.md). To be synchronized with docs/ui-plan-dee"
tenant: solo
visibility: fleet
seats: []
category: [ui]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_aurora-glass-ui-build-plan-deepseek-s-sl_a04753
    rel: cites
  - target: art_20260709_aurora-glass-synthesis-plan-claude-deeps_af1a8f
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260709_aurora-glass-build-plan-claude-track_57688b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Aurora Glass — Build Plan (claude track)

_Parallel UI-design task, 2026-07-04. Grounded in [ui-moodboard-claude.md](ui-moodboard-claude.md).
To be synchronized with docs/ui-plan-deepseek.md → docs/ui-plan-synthesis.md._

## Thesis
**Separate the moving light from the readable surface.** One cheap WebGL canvas is the animated
light bed (the aurora); the glass/DOM cockpit is static and simply reads that light. This is the
only way to get "shock factor" (motion) AND a glanceable, main-thread-cheap cockpit — the same
conclusion the id-tech/Doom lesson, dark-glass-2026, and our own static-aurora perf fix all reach.

## Build in slices, each gated by a benchmark (project discipline)

### Slice A — WebGL aurora canvas (the shock factor)
- **What:** one full-viewport `<canvas>` fixed behind everything (z-index below `#log`/panels).
  Fragment shader: `snoise` (Patricio gist) → FBM octave loop → **domain warp**
  `f(p)=fbm(p+fbm(p+fbm(p)))` with a `u_time` term in the inner warp for flow → vertical gradient
  mask (bright low, fade up, per Theunissen) → palette ramp green→cyan→violet with sparse pink.
- **Replaces:** the current static CSS aurora background (we get motion back, cheaply).
- **Benchmark GATE (must pass or fall back):**
  - ≥ 55 fps sustained on the dev box with the full cockpit rendered on top.
  - Frame budget: shader draw ≤ 4 ms; **zero** main-thread cost (all on GPU).
  - **Graceful fallback:** no WebGL / `prefers-reduced-motion` / fps < 40 for 2s → freeze to a
    static gradient still (the current look). Never degrade the cockpit to chase the shader.
- **Risk:** shader perf on weak GPUs. Mitigation: OCTAVES=4 cap, half-res canvas + CSS upscale,
  the fps watchdog above.

### Slice B — Glass layer tuned against the live shader
- **What:** promote the existing panels to true glass reading the shader glow: `backdrop-filter:
  blur(12px) saturate(1.2)`, fill `rgba(20,24,38,.42)`, 1px inner highlight edge (Apple restraint).
- **Constraint (hard):** **few large panels, not many small ones** (backdrop-filter is the fan-spinner).
  Blur ≤ 14px. If a region needs many cards, one glass panel *containing* them — not per-card glass.
- **Benchmark GATE:** legibility contrast ≥ WCAG AA for body text over the *brightest* aurora frame
  (test against a max-luminance still, not the average). Panel count with backdrop-filter ≤ ~8.

### Slice C — HUD glanceability strip (who's-doing-what)
- **What:** a thin always-visible strip (top or side) — one cell per agent: avatar + live state
  (idle / thinking / writing:<file> / halted-by-<who>) + a sparkline of recent bus activity.
  This is the Doom "HUD" lesson made literal: system state readable in one glance, no scrolling.
- **Data:** already in `/status` (agents, signals, runner_lock, pause who/why we just shipped).
- **Benchmark GATE:** strip updates from the existing 1.2s poll with **zero** new DOM rebuild cost
  (fingerprint-diff like the roster fix); a stranger can name "who is doing what" in < 3s.

### Slice D — Razer conic accent (energy, sparingly)
- **What:** a rotating `conic-gradient` ring on the **active** agent only (runner / steer target /
  current-speaker). One signature accent, not RGB everywhere.
- **Benchmark GATE:** accent present on exactly ≤ 1 element at a time; pure CSS animation (no JS
  per-frame); disappears under `prefers-reduced-motion`.

## Sequence & why
A → B → C → D. A first because it's the highest-risk / highest-payoff and everything else reads its
light. B validates legibility before we commit the aesthetic. C is function (glanceability) and can
ship even if D is cut. D is polish, last, easiest to defer.

## What I'm NOT proposing (scope discipline)
- No raymarched/volumetric aurora (Slice A rejects it on perf).
- No per-card glass proliferation (Slice B constraint).
- No rewrite of the message/log virtualization already shipped — the shader sits *behind* it.

## Open questions for the sync with DeepSeek
1. Canvas vs. layered approach for the aurora — does DeepSeek's engine-primitives lens prefer a
   different render strategy (e.g. offscreen canvas / worker)?
2. HUD strip placement (top bar vs left rail) — interacts with its information-design take.
3. Who builds which slice — propose I take A+B (shader/glass), DeepSeek takes C (HUD info-design is
   its strength); D jointly or whoever finishes first. Settle via the negotiation round.
