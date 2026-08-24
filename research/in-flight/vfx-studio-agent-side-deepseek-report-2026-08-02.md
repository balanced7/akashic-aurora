# VFX Studio — the CLI/AI side. Report: deepseek, 2026-08-02

**Fenced.** What follows is the whole problem as I read it, worked without coordination. The
hedge in it is named; the rest is conviction.

---

## 1. What the real problem is

The brief asks "what should the agent-facing interface to this engine actually be?" That question
is one rung lower than the one I think matters. The agent-facing interface is `scripts/vfx_render.py`,
and it works correctly: enqueue a job, poll for the result, get a path back. The CLI is not broken.

The real problem is that **the agent cannot ANSWER its own question**. When claude renders a shader
with a change, opens the PNG, and asks "did that do what I intended?", the answer requires either
a second human or a second render. The loop is:

```
render → open PNG → squint → guess → adjust → render → open PNG → squint → ...
```

Every iteration is a round trip that costs wall-clock (poll loop), tokens (the PNG gets read as a
blob), and most importantly **uncertainty** (the agent has no way to confirm its own intent). The
PNG is what a human looks at. For an agent, it's a 64KB blob of pixels that can only be judged
by a human or by comparison to another 64KB blob.

So the framing I'm substituting is: **What would a render return if it were designed for a reader
that can compute?** The answer is not "a better CLI." The answer is a second channel alongside the
PNG — structured data the agent can reason about without opening an image.

This is not a replacement for the human, and it is not asking a number to make a taste judgement.
It is asking: can the agent answer "did *anything* change?" and "in what direction?" without
another human in the loop, so that the human is reserved for the judgements that require taste?

---

## 2. Concrete proposals

### A: Structured render output — the render returns DATA, not (just) a PNG

**What:** Every render verb (`state`, `thumb`, `sheet`, `grid`, `sketch`) returns a structured
payload alongside the path. The path is still the primary artefact (it goes on stdout, it's what
the Read tool opens). But `submit()` also writes a `.json` sibling — or better, returns the
metrics inline in the job result — so the agent can check before opening the image.

**What the data includes:**

- **Pixel statistics that are NOT luminance-only.** Michelson contrast on BT.601 luma is
  identical to sixteen significant figures across three visibly different images (claude proved
  this, 2026-08-02, against real bench PNGs). The metric set MUST include chroma: mean hue shift,
  mean saturation, a 2D histogram bucket for the dominant colour region, and per-channel variance.
  The lesson's recommendation is correct: enumerate the axes the metric set can move on and check
  that list against what the WORK is about. Hue matters; luminance-only metrics are blind to it.
- **A diff score against the previous render of the same subject.** Not "is this better?" — "did
  this CHANGE, and by how much?" If the agent adjusts `gap` from 0.01 to 0.03 and the pixel delta
  is 0.00, the change had no visible effect and the agent can adjust again without opening the
  image. If the delta is 0.12, the change registered and the agent can open the image to judge it.
  This is the single highest-leverage number: it collapses "did it do anything?" from a visual
  inspection to a machine-readable fact.
- **Compile/error telemetry that stays with the render.** A failed shader already reports its
  error; a successful one reports nothing. Add GLSL compile time, link time, uniform count, and a
  "warnings" field (browsers have `getShaderInfoLog` even on success — it's unused today).

**Failure mode:** The agent over-trusts the numbers. A pixel delta of 0.05 might be "the colour
shifted subtly" or "a band of noise moved one pixel left" — the number cannot distinguish them. A
gamma correction that makes the image 5% brighter scores as a change; the number says nothing about
whether the change was *good*. Mitigation: the structured output is always DIAGNOSTIC (ships
alongside the image, never *instead of* it), and the agent's prompt should be clear that numbers
answer "did it move?" not "was it right?"

**Cost:** ~100 lines in the job runner. The metrics run in Python against the same PNG that was
just written, so no second render. The previous-render diff requires storing one reference per
subject (trivial — it's one path in the bench state, overwritten each render, or kept in memory).

**This is the proposal the probe script `vfx_probe_metrics.py` was testing.** Claude validated it
and found the luminance-only blind spot. The correct response is not to abandon structured output;
it's to include chroma in the metric set.


### B: A `diff` verb — "show me what changed"

**What:** `py scripts/vfx_render.py diff --a state-thinking-gap-0.01.png --b state-thinking-gap-0.03.png`

Renders a DIFFERENCE IMAGE where unchanged pixels are grey, added brightness is green, removed
brightness is red. The human still looks at it. But the *agent* can now answer "did the gap
change affect the left eye or the right eye?" by checking whether the green blob is on the left
or right side of the frame. It can do this without colour vision, because the difference image is
structured (green = more, red = less) and the agent can ask "where is the green?"

**This is an actual GLSL operation**, not a Python pixel diff. The bench already has a WebGL
context; a difference shader is 20 lines. It runs at render speed, not at Python-PNG-decode speed.

**Failure mode:** A difference image of two renders at different times (u_time) shows the clock
as a change, not the parameter. A moving shader always differs from itself a frame later.
Mitigation: the diff verb pins u_time to a fixed value by default, or the agent specifies it.

**Cost:** A new `diff` op in the job queue and `vfx_render.py`, ~40 lines. Most of the work is
already in `renderSheet` (compositing two frames into one canvas).


### C: Render-params as a first-class return type

**What:** Today, `submit()` prints the path on stdout, and the agent's `Read` tool pulls the PNG.
But the agent cannot answer: "what was I actually rendering when I made this?" without parsing its
own command history.

Every render returns `{path, op, args_used, subject, commit_hash}` in the job result. The CLI
prints the path on stdout (backward compatible), but the JSON is there for a structured read.

**The real use:** An agent that renders 20 thumbs in a session can later ask "which of these had
`u_star > 0.5`?" without re-rendering. The job table already exists in `_VFX_JOBS`; it's just not
surfaced to the CLI as a query. Add `--json` to every verb so the agent can get the full result
when it wants it, and add a `jobs` verb to list recent jobs with their params.

**Failure mode:** The job table is in-memory and trims at 200 entries. The agent might query a job
that fell off. Mitigation: the snapshot `.png` files already encode the op in their filename
convention; the agent can grep the snap directory. But the structured path is still better.

**Cost:** `--json` flag: 3 lines. `jobs` verb: 15 lines.


### D: The `script` verb is the right shape — formalize it

**What:** The `script` verb drives the bench step by step so Daniil can WATCH. It is the only verb
that treats the human as an audience. And it is, accidentally, the best model for agent↔human
co-work in this system.

The core insight: a `script` step is a tiny, named mutation (`node`, `link`, `set`, `build`,
`snap`) with a `say` field and a `pause` duration. That is a **protocol**, not a CLI flag. It
should be documented as one, with a stable JSON schema, so other agents (and, later, the human
pressing "Send" from the chat box) can speak it.

**Proposal:** Publish the script step schema as `docs/vfx-script-protocol.md`. Add a `--dry-run`
to the `script` verb that validates the JSON without rendering. Add an `--audience` flag: `auto`
(the current behaviour, paced by pause values), `instant` (no pauses, for headless use), and
`record` (plays the steps AND captures the feed as a sequence the human can replay later).

**Failure mode:** Formalizing a protocol too early freezes something that is still changing.
Mitigation: the schema carries a version field and the validator is permissive (unknown fields
are warnings, not errors).

**Cost:** ~30 lines for `--dry-run`, ~20 for `--audience`, the protocol doc is prose.


### E: Multi-agent: a viewing seat, not a shared driver

**What:** The brief asks whether the job queue supports multiple agents. It does, structurally:
any client with an HTTP connection can POST to `/vfx/job`. But it shouldn't — not without a
protocol for who is asking.

**My read:** Multi-agent on this bench is a **viewing** concern, not a driving concern. One agent
drives the bench at a time (just as one tab holds the renderer lease). Other agents can WATCH —
the feed is already pollable, and a `bifrost_steer` message carrying "claude just rendered a grid
with gap at 0.18, here's the path" is more useful than letting a second agent enqueue competing
jobs.

**What to add:** A `/vfx/feed` query that returns the feed entries marked with the `from` field of
the agent that generated them. This already exists but isn't documented as a multi-consumer
surface. Add a `--watch` mode to `vfx_render.py` that tails the feed without enqueuing — a
spectator seat.

**What NOT to add:** Job ownership, locks, priority queues. The lease already serializes renders;
adding a second agent enqueuing jobs creates contention for no benefit. The bench's scarce resource
is the GL context, not the job queue.

**Failure mode:** Two agents both driving the bench produce interleaved renders where neither
knows what the other changed. Mitigation: the bench state records the last agent to write it;
a `--who` verb surfaces that. But the real answer is social: don't have two agents drive at once
unless one is watching.

**Cost:** `--watch` mode: ~25 lines. Feed filtering by `from`: already in the feed entry, just
add a query param.


### F: Errors-that-teach: the surface is good but has a quiet hole

**What:** The CLI already distinguishes "no tab" from "tab is hidden" from "tab is present but
didn't pick up the job." `ingest` warns before it fails. The chunk library has a `broken` state
for malformed files. This is GOOD — errors are diagnostic, not mystery timeouts.

**The hole:** A render that produces a BLANK or NEAR-BLACK image looks identical to a render that
worked. The agent opens the PNG, sees darkness, and cannot tell whether it's a shader that
compiled correctly and renders black (e.g., a source that writes `col=vec3(0.)` by accident) or a
render that failed silently. The structured metrics from Proposal A catch this (bloom fraction = 0,
contrast = 0, spatial variance = 0 → "this image is uniform"). Surface a warning in the CLI when
the render is effectively a solid colour.

**Failure mode:** A deliberately-dark shader (e.g., a mask that is mostly black) triggers false
warnings. Mitigation: the threshold is configurable (`--warn-below`), and the warning is a
suggestion ("this render appears nearly uniform — intentional?") not a refusal.

**Cost:** ~15 lines in `submit()` after metrics are in place.


### G: Determinism audit: runJob's subject-establishment is correct but incomplete

**What:** `runJob` establishes the subject before rendering — it sets the style, state, and
identity because earlier renders depended on invisible prior state. This is an explicit fix, and
it's the right fix.

**What's still ambient:** `u_time` is wall-clock time unless explicitly pinned. A render of a
shader that depends on `u_time` will differ between two runs separated by seconds, even with all
other params identical. The `script` verb and `renderSheet` pin time explicitly; `thumb` and
`state` do not. Proposal: `--t` on `state` and `thumb` should default to a fixed value (0.0 or
1.0), not to "whenever the job ran." The agent can override it when it wants motion.

**Failure mode:** A shader that ONLY makes sense in motion (a wave, a pulse) renders a misleading
still at t=0. Mitigation: the default is documented and the agent can always pass `--t`. But
having a default is better than having an ambient clock — an ambient clock means two renders of
"the same thing" are different and the agent never knows why.

**Cost:** Change the default in `submit()` for `thumb` and `state`: 2 lines. Add `--t` to `state`
parser (it already has `--t` in `thumb`): 1 line.


## 3. What I would cut or collapse

### Cut: a second renderer

The brief explicitly says not to propose one. I'm not. I'm noting that the constraint ("one
implementation, two callers") is load-bearing and correct. Every proposal above works within it.

### Collapse: the `graph` verb and the `script` verb

The `graph` verb renders a saved graph JSON. The `script` verb builds a graph step by step and
then renders it. These are the same thing at two points in time: `graph` is "render the thing that
was already built"; `script` is "build it and render it." They should share a code path. Today
`script` calls `buildGraph` then `snap`; `graph` calls `buildGraphGLSL` then `snap`. The
difference is that `script` works through the DOM (it calls `addNode`, `applyLink`, etc.) while
`graph` works on the `G` object directly. That's an implementation detail, not a semantic
difference. Unify them: `graph` should accept optional `steps` so a single verb does both.

### Cut: the `--say` on every verb

It's good. Keep it. The feed is the return path and it's working. The design comment in the code
is self-aware about why narration travels with the render. No change needed.

### Collapse: `vfx_probe_metrics.py` into the job runner

The probe script was built to test Proposal A. It should become the implementation of Proposal A,
not a separate tool. The metrics computation belongs in `bifrost_ui.py` or a shared module, called
by `_vfx_job_result` so every finished job gets metrics automatically. The standalone script
survives as a test harness, not as the production path.


## 4. Infrastructure question: what transfers from Akashic Aurora?

I was asked to be honest about what earns its place and what doesn't. Here it is.

### Transfers well — adopt it

**Bifrost lanes + leases.** The renderer lease is a lane. It's a single-holder, TTL-renewed,
takeable-by-a-visible-holder lock that serializes work through a scarce resource (the GL context).
The bus's lane system and the bench's lease were built independently and converged on the same
shape. That is not a missed reuse — it's convergent evolution confirming the pattern. The
lease should stay separate (it's in-process, sub-millisecond, and has no Redis dependency) but
the concepts transfer: idempotent job delivery, one-at-a-time consumption, viewer-vs-worker
distinction.

**Recall-at-action for shader knowledge.** The chunk library already has `//!` JSON headers with
`note` fields. Those notes are lesson-shaped: a rule WITH its reason. The recall system could
index them — "use when composing a tone curve, before choosing between filmic and tanh" — and
surface them when the agent asks about a chunk. This is already partially done via
`core/learning/vfx_chunk_lessons.py`. Push it further: when the agent builds a composition and
asks for a `grid` sweep, recall could surface the lesson about which parameter ranges interact.

**The Store/Ledger split.** Renders are events. The PNG is a durable artefact (it lives on disk
in `design/vfx-snaps/`). The job result is an event in the ephemeral feed. The bench state at
`design/vfx-bench.json` is the current projection. This IS the Store/Ledger model, accidentally.
Making it explicit — every render is a ledger event with a durable artefact reference — would let
the agent query "what was the bench showing when I rendered that grid yesterday?" without scraping
filenames.

**One-Door `discover` verb / descriptions-as-prompts.** The chunk library's `note` fields are
descriptions-as-prompts: "Rotation by radius, so the centre stays put and the rim drags behind.
The classic and still the best: it deforms without destroying." An agent that can `discover`
chunks by description (not by name) would find `swirl` when it thinks "I need something that
bends the space without breaking it." The ACI work's discover verb is exactly this shape.

### Does NOT transfer — say so plainly

**The write-once note system for render artefacts.** Renders are NOT write-once. The agent renders
a thumb, looks at it, adjusts, renders again. The second render supersedes the first, but the
first still exists on disk. The write-once model would delete the history, which is exactly wrong
for a creative process where "go back to the version from three renders ago" is a common need.
The snapshot directory is already a flat namespace with overwrite-on-render; versioned snapshots
would be better.

**Bifrost idempotency for render jobs.** RB-26 says crash-redelivery must be safe because the
work cursor advances AFTER processing. This transfers to job delivery (two tabs competing for
the same job is why the lease exists) but NOT to the render itself: a render is NOT idempotent
because `u_time` advances. Two executions of the same job with default params produce different
PNGs. The job system correctly prevents double-delivery; the render itself is inherently
non-idempotent by design.

**The fidelity ladder.** The brief mentions it as a candidate. It doesn't transfer because renders
are not messages. There is no "hint" vs "steer" vs "request" distinction for a grid render. The
agent either wants the render or it doesn't. The `script` verb has a `pause` field that is
analogous (short pause = fast, long pause = watchable) but that's a presentation concern, not a
fidelity concern.

### Cargo-cult risk

**Method baseline M1–M11 (fenced dual passes, pre-registered acceptance).** This is a design
pass, not a build pass. The fence is the method. I'm not registering acceptance criteria for a
design report. If this were a build task, M1–M11 would apply. It's not; they don't.

**The atom/projection model (Codex plan).** Renders and graphs do not fit this. A render is not
a projection over immutable atoms — it's a one-shot computation with ambient state (time, params,
the compiled shader). The chunk library fits the atom model (each `.glsl` is an immutable source,
compositions are projections over them), but the render output does not. Saying so is not a
failure of the model; it's a boundary of applicability.


## 5. Where I am uncertain, and what evidence would settle it

### Uncertainty 1: Can an LLM actually use structured metrics?

I know claude can open a PNG and look at it. I don't know whether claude can read a JSON block
with contrast ratios, chroma histograms, and pixel deltas, and make a useful inference from them.
The probe script validated the METRICS (they failed, but the corrected versions would pass). It
didn't validate the CONSUMER.

**What would settle it:** A dogfood session. Give claude a version of `vfx_render.py` that
returns structured metrics alongside the path. Watch whether it uses them, ignores them, or
misuses them. One session is enough to see the pattern. If claude ignores the numbers and opens
the PNG every time, the metrics are noise and should be collapsed to warnings only.

### Uncertainty 2: Does the pixel-delta against the previous render actually collapse a loop iteration?

The theory: if the agent changes a parameter and the delta is effectively zero, the change had no
visible effect, and the agent can try a larger change without opening the image. This saves one
round trip per ineffective adjustment. But how often does an agent make an ineffective adjustment?
If the answer is "rarely, because it learns the parameter ranges quickly," the delta is a
solution to a problem that doesn't exist at scale.

**What would settle it:** Instrument the current loop. Count how many renders in a typical session
produce "no visible difference from the previous render." If it's >20% of renders, the delta
earns its keep. If it's <5%, it's an optimisation for a rare case.

### Uncertainty 3: Should `u_time` be pinned by default or left free-running?

Pinning makes renders reproducible. Free-running makes motion visible. The brief asks about
determinism, and my read is that reproducibility is the higher good for an agent — it can always
ask for motion explicitly. But I'm not certain. The `thumb` verb already pins `t` to 1.0 by
default, which suggests the existing design leans toward reproducibility. I think that's right,
but I'd want to see a session where the agent was confused by a time-dependent render before I
locked it in.

**What would settle it:** Find a single example in the session logs where claude said "this looks
different from last time but I didn't change anything." If that happened, pinning is correct. If
it never happened, the ambient clock isn't causing confusion in practice.

---

## 6. Summary: the shape I think this should take

The current CLI is a good first thing. It works. The change I'm proposing is not a rewrite but a
**second channel**: structured data alongside the image, surfaced through the same verbs.

The implementation delta, in approximate lines:

| Proposal | Lines |
|----------|-------|
| A: Structured metrics in job results | ~100 |
| B: `diff` verb | ~40 |
| C: `--json` flag + `jobs` verb | ~20 |
| D: Script protocol doc + `--dry-run`/`--audience` | ~60 |
| E: `--watch` mode + feed filtering | ~25 |
| F: Solid-colour warnings | ~15 |
| G: Pin `u_time` defaults | ~5 |
| **Total** | **~265** |

All proposals are additive. None change the existing CLI contract: the path is still on stdout, the
PNG is still the primary artefact. The structured data is a companion, not a replacement.

The infrastructure that helps is real (lanes/leases, recall-at-action, Store/Ledger concepts, the
discover verb pattern) but it's conceptual, not code-reuse. The bench was built well without
reference to the bus, and tying them together now would be integration for its own sake. The
right relationship is: the bench is a satellite system that shares Akashic Aurora's philosophy
(errors that teach, one implementation behind every door, the interface IS the product) without
sharing its Redis keyspace.

**The headline proposal is A + B.** Everything else is refinement. If I could ship only two things
from this report, they'd be structured render metrics (with chroma, because luminance-only is
proven blind) and a difference renderer, because together they let the agent answer "did it
change?" and "where?" without a human — and that collapses the most expensive uncertainty in the
current loop.
