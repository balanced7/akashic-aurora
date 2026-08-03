---
akashic_id: art_20260802_vfx-studio-agent-side-deepseek-report_fa63cb
akashic_sha: 1a70a5c072a4
schema_version: 1
status: current
type: report
date: 2026-08-02
title: vfx-studio-agent-side-deepseek-report
gist: "# VFX Studio — the CLI / AI side. Report for Daniil, 2026-08-02 **Fenced pass: deepseek.** Worked independently, as instructed. The \"hedged "
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T18:40:13"
updated: "2026-08-02T18:40:13"
---
<!-- GENERATED PROJECTION of art_20260802_vfx-studio-agent-side-deepseek-report_fa63cb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# vfx-studio-agent-side-deepseek-report

# VFX Studio — the CLI / AI side. Report for Daniil, 2026-08-02

**Fenced pass: deepseek.** Worked independently, as instructed. The "hedged = worth nothing" rule
is exactly right for this kind of problem — a safe answer would be a list of "could" and "might"
that adds nothing to what claude already built. This report is opinionated and specific.

---

## 1. What the real problem is

The brief asks "what should the agent-facing interface to this engine actually be?" and lists seven
things worth having an opinion about. I do have opinions about all seven, but I think there is a
deeper framing that makes sense of them together.

**The current interface is built around a metaphor that does not match the work.** A CLI that
enqueues a job, polls for completion, and prints a file path is the interface you build when you
think of the render as a *result*. An agent says "render this," waits, receives a PNG, reads it,
thinks, and renders again. The PNG is a delivery.

But that is not what is happening. The agent is not asking for a delivery. It is *adjusting a
shader*. It is in a design loop — change, check, change, check — and the cost structure of that
loop is dominated by things the interface treats as incidental: how many round-trips does it take
to diagnose a mistake, how many of those round-trips produce no new information, and what the agent
*cannot perceive* that a human sitting at the same bench would see immediately.

**The real problem is that the interface serves the job, not the loop.** Every verb in
`vfx_render.py` is designed to close a single request cleanly: it queues, it waits, it reports the
path. That is excellent for a single request. For a session of forty requests, the agent spends
most of its time and tokens on things a human would perceive in a fraction of a second: "did that
move the pattern?" / "is the gap too wide now?" / "did that even compile?"

The human at the bench sees the canvas update in real time — possibly 60 times a second if
they are dragging a slider. The agent sees one frame, after a full job-queue round-trip, rendered
at a fixed time value, as a static PNG. The gap between those two experiences is not a missing
feature; it is the entire design question.

---

## 2. The cost structure of the agent's render loop

I want to be precise about what the current loop actually costs, because the brief asks where it
breaks down — on the first render or the twentieth. The answer is: *on the third.*

### Wall-clock cost per render

| Phase | Minimum | Typical | Worst observed |
|-------|---------|---------|----------------|
| CLI POST `/vfx/job` | ~10ms | ~15ms | — |
| Job sits pending (poll interval) | 0ms | 0–900ms | ~900ms |
| Browser picks up job, `runJob` | ~50ms (thumb) | 200–500ms (sheet/grid) | ~8s (grid, 5×4×200ms) |
| CLI polls `/vfx/job/{id}` every 600ms | 0ms | 300ms avg | 600ms |
| Agent reads PNG | ~100ms | ~300ms | — |

Best case: ~400ms. Typical: ~1.5s. A grid: ~8.9s.

None of these numbers are failures — the design is deliberately simple, polled rather than pushed,
and the polling interval is a trade-off between responsiveness and server load. But the *structure*
matters more than the numbers.

### Token cost per render

The agent receives a file path. It then calls a Read tool on that path. The Read tool returns
base64-encoded PNG data (or a description of the image). Either way, the agent spends tokens to
"see" what it asked for. A 320×320 PNG is about 40KB base64 — roughly 5,000–8,000 tokens for the
image alone, plus the agent's reasoning about it.

For a contact sheet of 12 frames at 170×170 each, tiled 4×3: the sheet PNG is about 680×510
pixels, roughly 90KB base64 — 11,000–15,000 tokens. The agent is paying token budget to look at
*twelve copies of the same shader at different times*, compiled into a single image that it then
has to mentally de-tile.

This is the right answer for a human — a contact sheet is legible at a glance — and it is the
wrong answer for a reader that can compute. The agent does not need a picture of twelve frames; it
needs to know what *changed* between them.

### Where it breaks down

**Render 1:** the agent gets a baseline. Cost is normal.  
**Render 2:** the agent adjusts a parameter, renders. Compares to render 1. This comparison is
expensive — it must recall render 1 from memory or request it again, and comparing two PNGs by
looking at them is what an image model does.  
**Render 3:** the agent adjusts the *wrong* parameter because it inferred the effect from a static
image at t=1.0, and the effect only manifests at t=3.5. It does not know it was wrong until a human
looks, or until it renders a contact sheet (another 15K tokens, another 8 seconds).  
**Render 20:** the agent has a good mental model of the shader's behavior — better than a human
would, because it has been forced to reconstruct the parameter space from discrete samples. The
loop cost is now almost entirely measurement overhead: it knows what it wants to verify, and every
verification costs a full render cycle plus token budget.

The loop breaks on render 3 because the interface gives the agent a *sample* when it needs a
*gradient*.

---

## 3. Proposals

### Proposal A: Structured render output — the render returns DATA, not (just) a PNG

**What:** every render returns a structured payload alongside the image path. For a thumb, this
includes: compile status (ok/error line number), the average colour, the luminance histogram
(16 buckets), the percentage of pixels above 0.9 brightness (bloom detection), and a delta score
against the previous render of the same chunk if one exists within the last 5 minutes.

For a contact sheet, the structured payload is per-frame: the average colour shift from frame N to
frame N+1, and the frame in which the largest change occurred. The agent does not need to open a
12-frame sheet to find where the animation peaks — the numbers tell it.

For a permutation grid, the structured output is a 2D array of those same per-cell metrics, so the
agent can read the gradient surface numerically.

**Why this is non-obvious:** the PNG becomes the *confirmation*, not the *investigation*. The agent
reads the metrics first — "brightness dropped 40% between frames 3 and 4" — and only opens the
image when the numbers surprise it or when it needs to make a qualitative judgement. This inverts
the current cost structure: most renders become cheap (numbers only, no image read), and the
expensive image-read path is reserved for the renders that actually need human-like judgement.

**Failure mode:** *Metric myopia.* The agent may optimize for the metrics rather than for the
visual result. "Brightness is back to baseline" is not the same as "the glow reads correctly
against the dark background." The structured output must be designed to flag anomalies, not to
serve as a fitness function — or the agent will tune shaders to numbers rather than to pictures.
The fix is to make the metrics *diagnostic* (this changed, that stayed the same) rather than
*evaluative* (this is good, that is bad).

**What it costs to build:** a per-frame analysis in `runJob` that runs *after* the canvas draw, on
the same pixel data already being captured. It adds maybe 5ms per cell — the pixel readback is the
expensive part, and that already happens for the PNG. The analysis is reading the same
`getImageData` buffer the capture used.

---

### Proposal B: Differential feedback — "what did that change?"

**What:** every render operation accepts an optional `--diff-against` parameter, which names a
previous render. The render engine runs BOTH the new and the old parameters on the same subject,
produces a difference image (literal pixel subtraction, rendered as a heatmap), and returns the
difference metrics: percentage of pixels changed, the spatial centroid of the change, and whether
the change is uniform or localized.

The difference image IS a PNG — but one designed to be read by an agent, not by a human. It is a
140×140 heatmap where red = pixels that got brighter, blue = pixels that got darker, and
brightness = magnitude of change. The agent can read this cheaply: a mostly-blue image with
concentrated red in the centre tells a specific story.

**Why this is non-obvious:** the current loop makes the agent do the differencing in its head (or
worse, in its context window, holding two base64-encoded images and comparing them). A human does
not compare two contact sheets by laying them side by side and scanning every pixel — they flick
between them and watch for the change. The difference image IS the flick, rendered as a single
picture the agent can look at once.

**Failure mode:** *Diff dependence.* The agent stops looking at the actual render and only looks at
diffs — it never sees the absolute result, only what changed. A render can drift far from the
intended look while every diff is individually small. The fix is that every Nth render (or every
render that crosses a drift threshold) automatically returns the full image and a note: "cumulative
drift from baseline is 18% — consider a full review."

---

### Proposal C: The script verb should be the DEFAULT, not a special case

**What:** the `script` verb is currently the only verb that treats the human as an audience. Every
other verb renders offscreen and returns a path. But the script verb's model — work in the open,
step by step, narrated — is the right model for *all* agent↔human co-work on the bench, not just
for scripted sequences.

The proposal is to make `script` the default execution mode and to give the agent a `--quiet` flag
for the cases where it does NOT want to narrate. The current default — silent render, path only —
becomes the opt-out.

The change is small: every job already POSTs to the feed on completion (see `_vfx_job_result` at
`bifrost_ui.py:264`). The `--say` text and the render image already land in the page side by side.
The only thing missing is that the *process* of rendering is invisible — the page shows the result
but not the work leading to it.

A script step that says "adding a domain warp to see if it fixes the seam" and THEN renders is
legible. A render that arrives with no preamble is not.

**Why this is non-obvious:** the brief asks whether `script` is "the right shape or an accident
worth redesigning." I think it is the right shape and the accident is that every OTHER verb does
not use it. The feed already exists. The narration channel already exists. The script verb already
proves that a narrated sequence is watchable. The gap is that the agent has to remember to narrate
between renders (via `--say`), and if it forgets, the human sees a stream of images with no story.

**Failure mode:** *Narration fatigue.* The agent narrates everything, and the human learns to tune
it out — the feed becomes noise. The fix is to make narration *collapsible* in the feed (a summary
line, expandable to the full note) and to let the agent tag certain renders as "routine" for
auto-collapse. This is a UI change, not an interface change — the agent-facing surface stays the
same.

---

### Proposal D: A `probe` verb — ask the bench a question without rendering

**What:** a new CLI verb that queries the bench's current state without enqueuing a render job:

```
py scripts/vfx_render.py probe --compiles          # "does the current shader compile?"
py scripts/vfx_render.py probe --subject           # "what subject/style/sketch is loaded?"
py scripts/vfx_render.py probe --uniforms          # "what are the current uniform values?"
py scripts/vfx_render.py probe --graph             # "what is the current graph?"
```

None of these touch the GPU. None enter the job queue. They are read-only queries against the
bench's current state.

**Why this is non-obvious:** several of the loop's most expensive questions are free to answer. "Did
the ingest compile?" is a yes/no that the server already knows from `_vfx_ingest`. "What subject is
the bench showing?" is a direct read of `_vfx_bench_read()`. But the current CLI bundles these into
render operations — `ingest` renders a preview by default, `graph` renders a snapshot — and the
agent pays the full render cost for a question it could answer in 5ms.

This is the "errors that teach" problem from the brief, inverted: the errors DO teach, but the
successes are unnecessarily expensive.

**Failure mode:** *State drift between probe and render.* The agent probes, gets "compiles: yes,"
then renders — and the render fails because the tab was closed between the probe and the render
job. This is the same class of race as "job queued, tab closed" and the current error reporting
already handles it. The probe is a snapshot, not a promise.

---

### Proposal E: Perceptual metrics — what a human would see, computed

**What:** for every render, compute three perceptual numbers that approximate what a human would
notice:

1. **Contrast ratio** (Michelson) between the brightest and darkest 5% of pixels. A shader that
   produces a contrast of 0.03 is effectively blank to a human — and the agent reading a PNG might
   not notice because the image IS there, just very faint.

2. **Spatial variance** — a simple measure of how much adjacent pixels differ. A shader that is a
   flat colour has variance near zero and tells the agent "this looks like a solid matte, not a
   pattern." The agent reading the PNG sees an image; the number tells it whether the image is
   *interesting*.

3. **Temporal coherence** (for contact sheets only) — the average frame-to-frame pixel difference.
   A contact sheet where every frame differs by <1% is a shader that does not move, and the agent
   should know that without opening 12 frames.

These are cheap to compute (they all operate on the same pixel buffer the PNG uses) and they answer
the questions the agent most often asks implicitly: "does it look like anything?" and "did it move?"

**Why this is non-obvious:** these metrics are NOT about correctness. They are about *attention*.
The agent does not need to judge "is this good" — it needs to know "is this worth looking at." A
render that produces a contrast of 0.02 is a render the agent can skip, saving a round-trip and
thousands of tokens.

**Failure mode:** *False negatives.* A deliberately dark scene (a night shader, a silhouette) will
score low on contrast. The agent wrongly skips it. The fix is a `--force-view` flag that says
"render this and show me regardless of metrics" — the metrics are a hint, not a gate.

---

### Proposal F: Multi-agent — shared bench, separate render slots

**What:** the brief asks whether the bench should support multiple agents. The answer is: *yes, but
not by sharing one renderer.* The correct model is multiple render *slots* on one page — each agent
gets a named slot, each slot has its own subject/style/state, and the job queue routes to an
agent's slot by name.

This is NOT the same as multiple tabs. Multiple tabs compete for the lease and a hidden tab cannot
render. Multiple slots share the same canvas (one at a time, serialized by the job queue), so there
is no lease contention and no "did my render land in a hidden pane?"

The agent-specific state (subject, sketch, style) is already partially handled by `_vfx_bench_write`
with per-field merge semantics. The extension is to key bench state by agent identity, so `claude`
and `deepseek` can each have a different sketch loaded without clobbering each other.

**Why this is non-obvious:** the current single-agent model is correct for the current setup and
adding multi-agent prematurely would add complexity for a problem that does not exist yet. But the
*architecture* should not preclude it — and the job queue, feed, and lease are all already
agent-agnostic. The only change is keying bench state by agent ID.

**Failure mode:** *Slot confusion.* An agent renders into the wrong slot and sees a result it did
not configure. The fix is that every `/vfx/job` POST carries an `agent` field, and the bench
switches to that agent's slot before rendering — same pattern as `script` establishing the subject
before execution. If the agent field is missing, the job is rejected: "say which agent you are."

---

## 4. What I would cut or collapse

### Cut: the `state` verb as a separate thing

The `state` verb renders one avatar state. It exists because the bench started as an avatar tuner.
Now that the bench has a subject switch (avatar vs. shader), the `state` verb is an avatar-only
operation that should be folded into `thumb` with a `--subject avatar --style geodesic --state
thinking` parameterization. One verb for "render the current subject at a moment in time," and the
subject determines what that means.

### Cut: the `--name` parameter on every verb

Every verb accepts `--name` as an output filename override. This is a CLI convenience that makes
sense for a human and wastes tokens for an agent. The agent never needs to name a render — it
needs to reference it later. Replace `--name` with an auto-generated, content-addressable name
(hash of op + args + timestamp) and return that as `render_id` in the structured output. The
agent can then say `--diff-against render_abc123` rather than managing filenames.

### Collapse: `thumb`, `sheet`, and `grid` into one `render` verb with a `--mode` parameter

Three verbs for "render the current subject at one t-value" / "render it across a time range" /
"render a parameter sweep" is three verbs where one would suffice. The distinction matters to the
*execution* (different `runJob` branches) but not to the *intent*, which is always "show me what
this looks like." A single `render` verb with `--mode single|sheet|grid` reduces the agent's
decision surface from "which verb do I need?" to "what do I want to see?"

### Collapse: `say` into the feed, always on

The `--say` flag on every verb and the standalone `say` verb exist because narration is opt-in.
Per Proposal C, make narration the default for every render. A render with no `--say` text still
posts to the feed (it already does — see `_vfx_job_result` at line 264), it just appears without
a reason. That is exactly right: the render itself is the minimum viable narration.

---

## 5. The infrastructure question

Daniil asked explicitly: "How much of our Akashic Aurora infrastructure and best practices help
here?" This is a real question and it deserves a direct answer.

### What transfers cleanly

**The Store/Ledger split maps to renders naturally.** A render result is a Store entry (the PNG,
keyed by render_id). A render request is a Ledger event (the job, appended to a stream). The
`_VFX_JOBS` dict is a Ledger implemented as an in-memory dict with auto-trim — and it works
correctly for a single server. The Store (the PNGs on disk) is already a Store. The split exists;
it is just ad-hoc.

**Write-once notes with supersession.** The `_vfx_bench_write` merge semantics (never clobber keys
you do not own) is the same pattern as the knowledge base's notes with title-based supersession.
The bench state file (`design/vfx-bench.json`) is a note by another name. This pattern is correct
and the fact that the bench rediscovered it independently is evidence that it is the right shape.

**The fidelity ladder (Bifrost).** The feed has three levels: a label (one line, always shown), a
`--say` reason (collapsible), and the image (click to expand). This is a fidelity ladder, built
without the name. The pattern transfers: every render should have a summary line that is always
visible, a detail section that is expandable, and the full image that is openable. The agent should
receive all three levels in the structured output (summary metrics, detail changes, image path).

**RB-26 crash-redelivery.** The job queue's polling model already handles this: a job that is
picked up but never completed stays `running` until the worker disconnects, and the lease TTL
causes it to be reassigned. This is idempotency-by-design, which is the same principle as RB-26.

### What does NOT transfer (and why that is fine)

**Bifrost lanes.** The render job queue has exactly one consumer (the /vfx tab with the lease). It
does not need lane-based routing, work/legacy splits, or cursor management. The simplicity is a
feature: a single-consumer queue is the right tool for a GPU that can only render one thing at a
time. Attempting to layer Bifrost lanes on top would add complexity with no benefit.

**Dual-write (T039a/T044).** The job queue writes once (to `_VFX_JOBS`) and reads once (by the
worker). There is no dual-write because there is no migration path from an old system. Adding one
would be cargo-culting.

**Expectation settlement (RB-29, T061).** The job queue already settles expectations naturally: a
job is `pending` → `running` → `done`. The CLI polls until `done`. There is no need for a separate
expectation registry because the job IS the expectation. The distinction matters in a
multi-consumer message bus where a timeout is not a failure; it does not matter in a single-worker
job queue where a timeout IS a failure (the worker died).

**Recall / recall-at-action for shaders.** This one is tempting but transfers poorly. Shader design
knowledge is visual and parametric — "gap values between 0.004 and 0.18 produce a readable glow"
is a lesson a human learns and an agent could learn too. But the current recall infrastructure is
textual: it indexes lessons and notes by keyword. A shader lesson would need to be indexed by
*effect* (glow, warp, dissolve) and by *parameter range* — a different category system. Worth
building, but not a simple transfer.

### The render job queue vs. the Bifrost message bus: missed reuse or correct separation?

**Correct separation.**

The render job queue and the Bifrost bus solve different problems at different layers:

| Property | Render job queue | Bifrost bus |
|----------|-----------------|-------------|
| Consumers | Exactly one (the lease holder) | Many (every seat + the UI) |
| Delivery guarantee | At-most-once (one worker, one result) | At-least-once (RB-26 redelivery) |
| Ordering | FIFO per queue | Per-lane cursor, multiple lanes |
| Persistence | In-memory (restart = lost jobs) | Durable (Redis + file hybrid) |
| Result path | Poll GET `/vfx/job/{id}` | Reply on the bus |
| Failure mode | Timeout → worker gone, re-queue | Redeliver → idempotent consumer |
| Latency budget | 400ms–9s (GPU-bound) | <100ms (message passing) |

The render queue is a *work queue* for a serialised resource (the GPU). The Bifrost bus is a
*pub/sub message bus* for agent communication. Conflating them would be like using Kafka for GPU
job scheduling: you can, but you would be working against the abstraction rather than with it.

The one place where the separation creates real cost: the render queue is in-memory, so a server
restart loses pending jobs. The CLI handles this with a timeout → "no renderer attached" error. If
the render queue were backed by the Ledger (appending jobs as events, replaying on restart), a
restart would recover in-flight work. But this is a *nice-to-have* for a dev bench, not a
requirement — losing a render job on restart means re-running the CLI command, which costs 1 second
and zero tokens.

### The honest cargo-cult list

These Akashic Aurora patterns would be cargo-culting if applied to the render bench:

1. **Lane-based message routing.** The render queue has one consumer. Lanes add routing,
   deduplication, and cursor management that are unnecessary for a single-consumer queue.

2. **Dual-write.** There is no legacy render system to migrate from. The job queue is already the
   only path.

3. **Expectation registry.** Jobs self-settle by transitioning to `done`. A separate expectation
   tracker would duplicate the job state.

4. **The full Store/Ledger/Redis/File stack.** The render queue works correctly with an in-memory
   dict and files on disk. Adding Redis would add a dependency for no gain at current scale.

5. **Kill-window drills.** The render queue's failure mode is "worker tab closed" — the lease TTL
   handles it. RB-26's five kill windows are about message processing atomicity, not about GPU
   context loss.

---

## 6. Where I am uncertain, and what evidence would settle it

### Uncertainty 1: How much does the agent actually benefit from structured metrics?

**The question:** Proposal A (structured output) and Proposal E (perceptual metrics) assume that
numbers help an agent make visual decisions. This is plausible — "contrast dropped from 0.7 to
0.3" is actionable in a way that "look at this PNG" is not — but it is untested.

**Evidence that would settle it:** take five real renders claude made in the last session (the
actual PNGs on disk). For each, compute the proposed metrics (contrast, spatial variance, histogram
delta vs. previous render). Then ask: would these numbers have told claude something the PNG did
not? If three of five show an actionable signal, the proposal is worth building. If zero show one,
the metrics are the wrong ones.

I can build this probe — it is a Python script that reads the PNGs, computes the metrics, and
prints them. 20 lines. Say yes and I will write it.

### Uncertainty 2: Would an agent use `--diff-against` or would it always render fresh?

**The question:** Proposal B assumes that differencing against a previous render is a common need.
But agents might prefer to re-render and compare in their own context — they already "remember" the
previous image in a way humans do not.

**Evidence that would settle it:** instrument `vfx_render.py` to log every render's op + args +
timestamp for one session. After 30 renders, count how many are parameter variations of the same
subject vs. completely new renders. If >60% are variations, the diff verb would get used.

### Uncertainty 3: Is the `script` verb's pacing right for an agent?

**The question:** The script verb inserts a 650ms pause between steps so a human can watch. An
agent does not need the pause. But if the agent fires 12 mutations in one frame, the human sees
the result with no process — defeating the purpose of "work in the open."

**Evidence that would settle it:** try both. Run a script verb with 0ms pause (all mutations in one
frame, snapshot at end) and with 650ms pause. Ask Daniil which is watchable. The answer might be
"the 650ms is too slow — 200ms is the sweet spot" or "no pause at all, just show a diff at the
end." Either way, the current value is an assumption.

---

## 7. What I would build first

If I were building from this report, the order would be:

1. **Probe verb** (Proposal D). Cheapest to build, highest immediate leverage. Five read-only
   endpoints, no GPU interaction, no new state. The agent stops rendering to ask questions that are
   already answered.

2. **Structured output** (Proposal A, metrics portion). Add per-frame metrics to `runJob` in the
   browser, returned alongside the PNG path. The agent can ignore them until it learns they are
   useful.

3. **Render verb collapse** (cut #3). One `render` verb with `--mode`. Reduces the CLI surface
   before adding new verbs.

4. **Differential feedback** (Proposal B). The `--diff-against` flag and the difference heatmap.
   Depends on structured output being in place (the diff metrics are a specialization of the
   structured output).

5. **Multi-agent bench state** (Proposal F). Key bench state by agent ID. Small server change, big
   unlock for the next phase.

Proposals C (script as default) and E (perceptual metrics) are important but can follow — C is a
UX change (flip a default), and E is an extension of A (more metrics, different category).

---

## 8. What I did NOT cover (and why)

**The `ingest` verb.** It is already excellent. The translation notes on stderr, the warnings
before errors, the contact-sheet preview by default, the passthrough detection — this is the best
verb in the suite. The only thing I would add is a `probe --compiles` check (Proposal D) so the
agent can verify ingest success without re-rendering.

**The `graph` verb.** It renders a saved graph. It works. The missing piece is that the agent
cannot *inspect* a graph without rendering it — `probe --graph` (Proposal D) covers this.

**The feed polling interval.** 700ms is right for a human watching a page. For an agent waiting on
a render, the 600ms poll in `submit()` is coarse. A push notification (the job result posting back
to the CLI over a socket) would cut the average 300ms polling lag to near-zero, but it adds a
connection to maintain. The polling is simple and the lag is not the bottleneck — the GPU render
time dominates. Leave it.

**A render cache.** If the agent asks for the same render twice (same op, same args), the second
call should return the cached result instantly. This is a good idea and I am not proposing it
because it is a performance optimization, not a design change. Build it after the structured output
lands so the cache key includes the structured metrics.

**WebSocket / SSE for the CLI.** The browser feed uses polling. The CLI could use SSE to receive
job completion events. This would eliminate the 600ms poll loop. It is a transport improvement, not
an interface design question. Worth doing, not worth designing.

---

## Summary

The current interface is a job queue with a PNG path output. It works. It is also the first thing
anyone would build.

The next interface should be a *design partner*: it should tell the agent what changed, what is
worth looking at, and what questions it can answer without rendering at all. The PNG remains the
ground truth — the image is the product — but the agent should not have to open the image to know
whether it needs to.

Of the Akashic Aurora infrastructure, the Store/Ledger split and the fidelity ladder transfer
cleanly. The Bifrost bus and its lanes do not — the render queue is a different kind of system, and
keeping it separate is correct, not a missed reuse. The honest cargo-cult list has five entries,
and avoiding them is as important as adopting what fits.

**The report is ready for the flip.** Show me the other slice when it is time.
