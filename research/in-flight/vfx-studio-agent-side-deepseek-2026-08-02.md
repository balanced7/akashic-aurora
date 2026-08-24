# VFX studio — the CLI / AI side. Brief for deepseek, 2026-08-02

**You are fenced.** Work this as if it is the whole problem. Do not assume anyone else is covering
anything, do not write around a gap expecting someone to fill it, and do not coordinate. An
independent answer is the entire value of your pass; a hedged one is worth nothing here.

---

## Daniil's ask, verbatim

> "I want to set up a fence on our vfx design … give deepseek the cli / ai side. … Then after they
> have their reports I want them to flip views and see how they would respectively improve the
> human side, then synthisize the reports and make a sliced plan for building it."

and, governing how you work it:

> "I am also curious how much of our akashic aurora infrastructure and best practices will help
> here! Good luck and have fun! Tell them to be creative with it, to go where their intuition
> lands. how they approach it is up to them?"

Take that seriously. **How you approach this is yours to choose.** If your intuition says the
framing below is wrong, say so and work the problem you think is actually there — name the
substitution explicitly so the synthesis can weigh it.

## The situation

There is a shader design bench at `http://127.0.0.1:8787/vfx`. An agent (claude, today) drives it
from the CLI while Daniil watches the same page. The bench executes the agent's render requests
using the SAME functions the UI's own buttons call — one implementation, two callers, so a
CLI-requested render cannot disagree with a clicked one. That constraint is load-bearing and was
paid for; do not casually propose a second renderer.

## What exists today (read these — do not take my summary as the territory)

- `scripts/vfx_render.py` — the agent's door. Verbs: `state`, `thumb`, `sheet`, `grid`, `sketch`,
  `graph`, `script`, `ingest`, `say`. Every render verb takes `--say`.
- `scripts/vfx_ingest.py` — Shadertoy → bench translation, dependency-free, pinned by
  `tests/test_vfx_ingest.py`.
- `scripts/bifrost_ui.py` — search `/vfx` for the endpoints: a job queue, a renderer LEASE, a live
  FEED, durable bench state, presets, sketches, graphs, chunks, thumbs, snaps.
- `scripts/vfx.html` — the page, including `runJob` (the worker) and the feed renderer.
- `tests/test_vfx_feed_and_lease.py`, `tests/test_vfx_ingest.py` — the bars currently defended.
- Durable notes, via `py agent_cli.py note deepseek --get <title>`:
  `vfx-bench-where-we-are`, `vfx-bench-ingest`, `vfx-bench-subject-and-the-lost-original`.

Landed in the last few hours, so this is a moving target: the live feed (every finished job posts
its image + reason into the page), the renderer lease (one tab owns the farm; a visible tab takes it
from a hidden one), the ingest verb with an auto contact-sheet preview, and an explicit SUBJECT
(free shader vs avatar) with durable bench state.

## The question

**What should the agent-facing interface to this engine actually be?**

The current answer is a CLI that enqueues jobs and prints a file path the agent then reads as an
image. It works. It is also the first thing anyone would build, and it has never been examined.

Things worth having an opinion about, if your intuition agrees they matter:

- **The loop is still slow and blind in places.** An agent renders, reads a PNG, adjusts, renders.
  What is the actual cost structure of that loop — round trips, tokens, wall-clock, and *what the
  agent cannot perceive*? Where does it break down: on the first render, or on the twentieth?
- **What can an agent NOT ask for today** that it obviously should be able to? And what can it ask
  for that it should not?
- **Feedback fidelity.** A PNG is what a human looks at. Is it what an *agent* should get back?
  What would a render return if it were designed for a reader that can compute? (Consider what
  would let an agent answer "did that change do what I intended" without another human in the loop.)
- **Errors that teach.** This project holds that the interface IS the product and that errors
  should teach. `ingest` warns before it fails; a missing renderer distinguishes "no tab" from "the
  tab is hidden". Where does the surface still fail silently or unhelpfully?
- **Determinism and reproducibility.** `runJob` establishes its subject before rendering because
  renders used to depend on invisible prior state. Is that airtight now? What else is ambient?
- **The `script` verb** drives the visible bench step by step so Daniil can WATCH a composition
  being built. That is the only verb that treats the human as an audience. Is that the right shape
  for agent↔human co-work, or an accident worth redesigning?
- **Multi-agent.** Today one agent drives one bench. Nothing about the job queue, the lease or the
  feed assumes a single agent — but nothing supports several either. Should it?

## Explicitly asked, by Daniil

**How much of the Akashic Aurora infrastructure and best practices help here?** He is curious, and
it is a real question. Candidates worth testing against the design — adopt what earns its place and
say plainly what does not:

- the Store/Ledger split; the append-only ledger and what a render *event* would be
- write-once notes with supersession; the atom/projection model (Codex plan: resources as
  regenerable projections over immutable atoms) — do renders and graphs fit that shape?
- recall / recall-at-action; lessons and anti-patterns as a design memory for shaders
- Bifrost: lanes, leases, idempotency, RB-26 crash-redelivery, the fidelity ladder. The render job
  queue is a message system that was written without reference to the message system next door —
  is that a missed reuse or a correct separation?
- the One-Door `discover` verb and descriptions-as-prompts, from the ACI work
- method baseline M1–M11: pre-registered acceptance, fenced dual passes, kill drills

Be honest about the ones that would be cargo-culting. "This does not transfer, because…" is a
finding, not a failure — the anti-fossil clause is explicit in this project's licence.

## What to produce

Write to `research/in-flight/vfx-studio-agent-side-deepseek-report-2026-08-02.md`. Shape is yours.
What the synthesis needs from you:

- Your reading of what the real problem is (especially if it differs from the framing above).
- Concrete proposals, each with the reasoning that makes it non-obvious, and each with the failure
  mode it introduces. A proposal with no cost named has not been thought through.
- What you would cut or collapse.
- Your verdict on the infrastructure question.
- Where you are uncertain, and what evidence would settle it. You can request renders or probes —
  say what you want run and claude will run it.

Rough, opinionated and specific beats balanced and safe. **Have fun with it** — that was an
instruction, not a pleasantry.

## A later stage exists

After the reports are in, you will be shown a different slice of this problem and asked how you
would improve it. Do not try to anticipate it now; it would only dilute this pass.
