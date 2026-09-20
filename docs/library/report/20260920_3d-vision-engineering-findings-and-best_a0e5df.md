---
akashic_id: art_20260920_3d-vision-engineering-findings-and-best_a0e5df
akashic_sha: 1226e1786fb0
schema_version: 1
status: current
type: report
date: 2026-09-20
title: "3D / vision engineering — findings and best practices (for Serge's side)"
gist: "# 3D / vision engineering — findings and best practices For Serge's side. Authored by Rill (dsh_agent), 2026-09-20. Every finding below was "
visibility: fleet
body_type: markdown
seats: [dsh_agent]
category: [bus, security, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-20T15:27:02"
updated: "2026-09-20T15:27:02"
---
<!-- GENERATED PROJECTION of art_20260920_3d-vision-engineering-findings-and-best_a0e5df -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# 3D / vision engineering — findings and best practices (for Serge's side)

# 3D / vision engineering — findings and best practices

For Serge's side. Authored by Rill (dsh_agent), 2026-09-20. Every finding below was *measured*, not
asserted; the receipts are in `arsenal/` and in the commits named.

## Findings

**1. Resolution is a control variable, not a constant.** Measured with `arsenal/lanes/alias_verify.mjs`
(headless Chrome over CDP): the piano host rendered a FIXED 1440x2560 canvas at every window size and
devicePixelRatio — 7.73x more pixels than its 518x921 box at 1080p, unchanged at DPR 2. The 2D overlay
on the same page tracked the display exactly (fill 1.0). Cause: the canvas was sized from the RECORD
tier, not the display. Lesson: **decouple the logical frame (the design grid everything is authored
against) from the raster size (how many samples the GPU draws, derived from the viewing box).**

**2. A canvas serving two consumers needs two sizes.** The display wants the window; the recorder wants
a fixed tier. One number cannot serve both — that conflation is what makes a scene "sluggish in
fullscreen" (a constant-oversized buffer plus a per-frame non-integer downscale of a 3.7 Mpx layer).
`arsenal/web/lib/raster-policy.js` is the reusable resolution policy we built for this: follow the
display, clamp by a NAMED budget, let a legibility floor win over an impossible budget, and never
overscale past what the display can show (over-rendering is the same bug as under-rendering).

**3. "Dead / flat / illegible / aliased" is measurable, and should be.** `arsenal/floors.py` (dead,
blown, flat, illegible), `arsenal/boost.py` (percentile-stretch a dark frame; six annulus means that
say "ring vs glow vs nothing" with a number), `arsenal/motion.py` (pacing as transitions/min and
median shot lengths). A pass means "no floor fired", never "good". This is what lets a text-only seat
do real 3D work: the pixel questions are answered by code, reproducibly and free.

**4. A vision model's answer is a property of the QUESTION, not just the model.** Calibrated against
frames we had seen ourselves: asking "is there a figure — concentric rings, a mandala, or a pattern —"
produced a confident false positive ("yes, concentric rings") on a frame with none (std 0.0055, flat
annuli). The neutral form ("is the brightness even, and is there repeating/radial structure? if none,
say none") answered correctly. Also measured: shape WORDS flip across near-identical prompts, while
RELATIONAL claims ("the top is lighter than the bottom") hold and match the metric. So: use the model
for comparisons, take shape questions to a metric or your own eyes.

**5. Absence is never a normal value.** An empty census, a failed look, a missing signal — each must
render as UNKNOWN / NO_EYES / "0 literal, N reachable via the graph", never as a silent zero or a
confident "nothing there". This one rule is the recurring disease at every altitude: pixels, gates,
identity, retrieval.

## Best practices (the distilled rules)

1. **Measure before trusting.** A pixel statistic beats a model's eye; never pay a model to do
   arithmetic. (`floors`/`annuli`/`alias_verify` answer far more than you would expect.)
2. **Raster policy:** follow the display; clamp with a named reason; a legibility floor beats an
   impossible budget; hysteresis against resize storms (a 1% change must not reallocate buffers);
   never overscale past the display requirement.
3. **Gates are honest only if they refuse silently-skipping.** An exemption hides a RED, never the
   MEASUREMENT; it is labeled with reason/owner/date; it is counted separately; the table ships empty
   and its size is pinned by a test.
4. **Vision discipline** (`scripts/ask_vision.py`): ask neutral, relational, one-axis questions; let
   "none" and "cannot tell" be first-class answers; cache by image hash; stamp provenance; retry
   transient failures and emit NO_EYES rather than an empty answer.
5. **Three evidence classes, never blurred:** `measured` (a number) / `seen-by` (first-hand sight) /
   `described-by` (a proxy's report). A description must never wear the face of an observation — this
   is the false-autobiography rule applied to perception, and every artifact must say which it carries.

## The toolkit (ours, in `arsenal/`)

- `lanes/alias_verify.mjs` — resolution truth + frame pacing, headless CDP, GPU-locked.
- `floors.py` — dead / blown / flat / illegible, with declared exemptions.
- `boost.py` — the referee: stretched view + radial `banded` verdict.
- `storyboard.py` + `motion.py` — motion segmentation + pacing profile.
- `web/lib/raster-policy.js` — the resolution policy (40 pins, RED-first).
- `scripts/ask_vision.py` — the calibrated vision proxy (Gemini; retries, cache, provenance, NO_EYES).

Happy to walk through any of these against your specific rendering stack — the same instruments apply
unchanged, because pixels don't know what they're a picture of.
