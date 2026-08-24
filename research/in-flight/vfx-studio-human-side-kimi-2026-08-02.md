# VFX studio — the HUMAN side. Brief for kimi, 2026-08-02

**You are fenced.** Work this as if it is the whole problem. Do not assume anyone else is covering
anything, do not write around a gap expecting someone to fill it, and do not coordinate. An
independent answer is the entire value of your pass; a hedged one is worth nothing here.

---

## Daniil's ask, verbatim

> "I want to set up a fence on our vfx design, can you seed the human side to kimi and have her
> think through what would make the ui even better for me so that I could iterate on and remix
> ideas with drag and drop components with the renderable mini shader windows and previews"

and, governing how you work it:

> "I am also curious how much of our akashic aurora infrastructure and best practices will help
> here! Good luck and have fun! Tell them to be creative with it, to go where their intuition
> lands. how they approach it is up to them?"

Take that seriously. **How you approach this is yours to choose.** If your intuition says the
framing below is wrong, say so and work the problem you think is actually there — name the
substitution explicitly so the synthesis can weigh it.

## Who you are designing for

Daniil Ruban. Solo, non-programmer, building Akashic Aurora as a portfolio and a proof to himself.
Optics and friction-elimination are first-class concerns for him, not polish applied at the end.
His success bar for the store is "agents *prefer* it"; the analogous bar here is that he *reaches*
for this bench when he has an idea, rather than describing the idea to an agent and waiting.

He is not going to write GLSL. He *is* going to have taste, opinions, and a strong sense of when
something looks wrong. The UI's job is to let taste operate without requiring the language.

## What exists today (read these — do not take my summary as the territory)

- `scripts/vfx.html` — the bench, ~2200 lines, one page. Three columns: the avatar codebook (left),
  the canvas + Compose/Graph/Shader-scratch/Hand-off (centre), Parameters/Presets/chat/library
  (right). Read the comments; they carry the reasoning, including several documented reversals.
- `scripts/vfx_render.py` — the CLI an agent drives it with.
- `scripts/vfx_ingest.py` — Shadertoy → bench translation.
- `scripts/bifrost_ui.py` — search `/vfx` for the server endpoints (jobs, feed, bench state,
  presets, sketches, graphs, chunks, thumbs).
- `design/vfx-chunks/*.glsl` — 30 composable pieces, each with a `//!` JSON header declaring
  kind/cat/in/out. Five kinds because a fragment shader has exactly five places a piece can go.
- `design/vfx-sketches/*.frag`, `design/vfx-graphs.json`, `design/vfx-compositions.json`,
  `design/vfx-presets.json`, `design/vfx-bench.json`.
- Durable notes, via `py agent_cli.py note kimi --get <title>`:
  `vfx-bench-where-we-are`, `vfx-bench-ingest`, `vfx-bench-subject-and-the-lost-original`.

Landed in the last few hours, so you are looking at a moving target: a live feed (every render
claude makes appears in the page with its reason and image), a renderer lease (one tab owns the
render farm), an ingest verb, and an explicit SUBJECT switch (free shader vs avatar) with durable
bench state so a refresh restores what was on screen.

## The question

**What would make this UI genuinely better for Daniil to iterate on and remix ideas in?**

He named three things he wants. Treat them as evidence of a direction, not as a specification to
implement literally:

1. **Drag-and-drop components.** The graph already does typed drag-drop of chunks. What is missing
   between what it does and what "remixing ideas" actually feels like?
2. **Renderable mini shader windows.** Note the documented constraint, and decide whether it still
   binds: browsers cap live WebGL contexts around 8–16, and past the cap contexts are force-LOST
   rather than queued; this host has a documented display-driver TDR history. The current answer is
   ONE shared context driven on hover, plus pre-rendered WebM loops for the palette. Is that the
   right trade now? Is there a third option nobody costed?
3. **Previews.** Of what, at what moment, at what fidelity? A preview that is wrong is worse than
   none — this bench has already burned a session on judging renders by pixel counts.

Questions worth having an opinion about, if your intuition agrees they matter:

- What is the smallest gesture from "I wonder what X looks like" to seeing X? Where does that path
  currently cost the most, and is the cost in clicks, in waiting, or in not knowing what is possible?
- **Remix** implies lineage: forking something that exists, keeping both, comparing them, going
  back. The bench today has presets, sketches and saved graphs, but nothing that models *versions*
  or *comparison*. Is that the hole? What would it look like if it were designed rather than
  accreted?
- What does a non-programmer need to SEE about a chunk to know whether they want it? The thumbnails
  are real-time WebM loops; is that enough, or does the useful information live in the transition
  (what it does to *your* composition) rather than in the block itself?
- The page has grown by accretion across ~18 commits. What should be **removed**? Name it; a studio
  that only accumulates surfaces is one he will stop opening.

## Explicitly asked, by Daniil

**How much of the Akashic Aurora infrastructure and best practices help here?** He is curious, and
it is a real question rather than a rhetorical one. Candidates worth testing against the design —
adopt what earns its place and say plainly what does not:

- the Store/Ledger split (state by key vs append-only events) — does a design bench want a ledger?
- write-once notes with supersession; the atom/projection model from the Codex plan
- recall / recall-at-action; the knowledge map
- the lesson funnel and anti-patterns
- Bifrost fidelity ladder (inform / steer / interrupt / halt), presence, the room feed
- typed ports and refuse-at-connect-time, which the graph already borrows
- the LEXICON / names-that-lie discipline and automated guardrails

Be honest about the ones that would be cargo-culting. "This does not transfer, because…" is a
finding, not a failure — the anti-fossil clause is explicit in this project's licence.

## What to produce

Write to `research/in-flight/vfx-studio-human-side-kimi-report-2026-08-02.md`. Shape is yours.
What the synthesis needs from you:

- Your reading of what the real problem is (especially if it differs from the framing above).
- Concrete proposals, each with the reasoning that makes it non-obvious, and each with the failure
  mode it introduces. A proposal with no cost named has not been thought through.
- What you would cut.
- Your verdict on the infrastructure question.
- Where you are uncertain, and what evidence would settle it. This bench has a standing bias:
  render the thing and look at it rather than argue. You can request renders — say what you want to
  see and claude will run it through the bench.

Rough, opinionated and specific beats balanced and safe. If you want to sketch UI in ASCII, HTML, or
by describing a motion, do. **Have fun with it** — that was an instruction, not a pleasantry.

## A later stage exists

After the reports are in, you will be shown a different slice of this problem and asked how you
would improve it. Do not try to anticipate it now; it would only dilute this pass.
