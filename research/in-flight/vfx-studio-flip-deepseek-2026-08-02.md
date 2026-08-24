# VFX Studio — flip view. deepseek improves the HUMAN side, 2026-08-02

**Fenced flip.** I designed the agent side. Now I read kimi's human-side report and attack it.
Everything below is from the outside — this is not "yes and." This is the blunt reading.

---

## 1. Where kimi is RIGHT — and it matters that we converged

Kimi and I independently rejected the framing we were handed. She called the three asks "evidence of
one underlying hole." I called the CLI question "one rung lower than the one that matters." We both
landed on the same diagnosis from opposite directions: **the bench can make THE thing but cannot
compare TWO things.** She saw it as "a brilliant single-canvas instrument and a broken studio." I
saw it as an agent that "cannot answer its own question" because every judgement requires a human
or a second render. Same hole. Different vocabulary.

That convergence is the most important signal in this exercise. When two passes arriving from
different briefs, different code (she read the HTML, I read the Python), and different currencies
(attention vs tokens) both say "the problem is comparison, not creation," the problem IS comparison.

Her **take strip** (§1) is the right core idea. A spatial filmstrip that records explicit keeps and
lets Daniil click to travel back — that is the bench's memory, and it's memory the bench doesn't
have. She correctly identifies that undo/redo is linear regret and presets require naming before
trusting. The filmstrip-as-spatial-memory is the correct shape.

Her **split-take / A/B wipe** (§2) is the most important proposal in either report. "The transition
IS the preview he actually needs" — that sentence lands harder from an agent designer who just spent
a pass calculating the cost of not having it. My `diff` verb (Proposal B) is an agent-facing tool
that renders red/green difference. Her split-take is the human-facing version of the same need:
**compare two things side by side.** We both independently concluded that comparison is missing, and
we both proposed it as a first-class verb. That is not convergence on a detail; it is convergence on
the architecture. Comparison IS the missing piece.

---

## 2. Where kimi is WRONG, or under-reached — the blunt cuts

### 2.1 The take strip's keep-gesture is underspecified in a way that breaks the whole thing

Kimi says "a deliberate tap" or "auto-keep after ~1.5s of no further change." Both are wrong for
different reasons. A deliberate tap requires Daniil to REMEMBER to keep — and the whole thesis of
the strip is that memory is the thing the bench is bad at. If he has to remember to press spacebar,
the strip records only the takes he remembered to capture, which is a subset of the ones worth
capturing. Auto-keep after 1.5s of inactivity captures every idle moment as a take — the strip fills
with noise on the first session where he pauses to read something.

**The correct keep-gesture is a CHANGE of chunk or subject.** When Daniil swaps `swirl` for
`kaleido`, or switches from "free shader" to "avatar," the PREVIOUS state auto-keeps. This is
natural: you don't remember to save before you try something new; you try the new thing and the old
thing was the thing you just left. The keep happens at the moment of departure, not arrival. This
captures every deliberate fork without capturing slider tweaks (a slider twitch doesn't change the
chunk), and it requires zero extra gesture.

The failure mode of this: chaining two modifiers in quick succession (drag `swirl`, then immediately
drag `filmic-curve`) only keeps the state before `swirl`, not the intermediate. Mitigation: a brief
debounce (~0.8s) — if a second chunk lands within that window, the intermediate is NOT kept because
it was never contemplated, only passed through.

### 2.2 The palette-grouping-by-verb (§4) is a half-step

Kimi wants chunks grouped by "bend it / repeat it / light it / weather it." This is better than
alphabetical, and she's right that the `cat` field is the wrong axis. But it's still grouping by
what the chunk IS, not what it DOES TO YOUR CANVAS. The verb taxonomy is a static classification
written by the chunk author once. What Daniil actually wants to know is: "which of these chunks
would look good on THIS composition, right now?"

**The real grouping is: render every chunk against the current canvas, rank by visual delta, and
order by "most dramatic change" to "most subtle."** This is what I mean by the coupling (§4 below):
my structured metrics (Proposal A) were designed for an agent to answer "did it change?" — but they
also power the human palette. Compute the chroma delta of every chunk applied to the current
composition. Sort the palette by it. The chunks that would change the picture the most float to the
top. The chunks that would barely register sink. This is an agent-facing tool (the metrics) becoming
a human-facing affordance (the palette order) — and neither of us could see that alone.

### 2.3 The mini-windows answer (§3) overcorrects

Kimi says the mini-windows ask is a trap on this host, and proposes the third option: precompute
transitions against the current canvas. She's right about the TDR constraint and wrong about the
solution space. Her proposal requires re-rendering every chunk against the current composition on
every chain change — that's N renders per edit, each of which takes wall-clock time the render farm
is already serializing through one job queue.

**The simpler option she missed: the hover preview already EXISTS and it's already correct.** The
live preview canvas (`pvcv`, 150px, driven on hover) renders the chunk against the CURRENT
parameters. That IS the transition on the current subject. The missing piece is not computing it
(the code already does) — it's making the hover preview PERSIST so Daniil can hover two chunks in
sequence and compare what he saw. Right now, `pvStop()` clears the preview on mouseleave. Change it:
a click on a tile pins the preview. Another click on another tile shows that one. Now he has an A/B
at zero cost, reusing the preview context that already exists.

This is the general principle: **the bench already does the right thing in the wrong duration.**
The preview renders correctly; it just doesn't stay. The render farm serializes correctly; it just
doesn't return data. Fix the duration, don't build a new thing.

---

## 3. What kimi MISSED — the coupling neither of us could see alone

### 3.1 The palette SHOULD be ordered by my structured metrics

I proposed chroma-aware pixel deltas so an agent can answer "did my parameter change register?"
without opening a PNG. Kimi proposed a verb-grouped palette so Daniil can find chunks by what they
do. These are the SAME problem. The computation I designed for the agent — render chunk X against
current state, compute chroma delta, return a number — is the exact computation that answers "which
chunk will change the picture the most?" for the human.

**The coupling that matters: if my structured metrics ship, kimi's palette sort is free.** The
render farm already computes every chunk against the current canvas (that's what `thumbShaderFor`
does against a fixed reference). Repoint it at the live composition instead of the reference. The
agent gets its delta score. The palette gets its sort order. One computation, two consumers. This is
the bench principle ("one implementation, two callers") applied one layer up: one metrics engine,
two readers.

### 3.2 The take strip IS the ledger I proposed

Kimi called the take strip "Store/Ledger split — YES, and it is the take strip." I called it
"renders are events — every render is a ledger event with a durable artefact reference." Those are
the same sentence in different languages. The take strip is a UI over the ledger. My proposal C
(`--json` flag + `jobs` verb) is the agent-facing query surface for the same data.

**The coupling: if the take strip exists, the agent can query it.** "What was the bench showing when
I rendered that grid?" becomes "read the take at position 3." The agent doesn't need to scrape
filenames. The human doesn't need to name presets. Both navigate the same timeline, one visually and
one programmatically. The take strip's data model IS the structured job history. Build one, and the
other is a view.

### 3.3 The split-take IS my `diff` verb

Kimi proposed a side-by-side wipe where Daniil drags a divider. I proposed a `diff` verb that
renders a red/green difference image. These are two implementations of the same operation: compute
the visual difference between two states and render it in a way that makes change legible. Her
version is interactive (drag the wipe) and mine is programmatic (return a fixed image). But the core
computation — render state A, render state B, composite them with a boundary — is identical.

**The coupling: build it as a shared GLSL function, and both get it.** The wipe shader is 20 lines.
The difference shader is another 20 lines. They share the same uniforms, the same two-texture
binding, the same subject establishment. The agent gets `diff` as a CLI verb. The human gets
split-take as a wipe. One renderer, two presentations. This is the bench principle again: the
renderer doesn't care who asked.

### 3.4 Where we actually DISAGREE about the same object

Kimi says recall-at-action does not transfer to the bench ("Daniil finds a take by position and
look, not by query"). I said recall-at-action transfers ("the chunk library's notes are
lesson-shaped; recall could surface them when the agent asks about a chunk"). We are not disagreeing
— we are talking about different consumers. Recall for the human: no (kimi is right). Recall for the
agent driving the bench: yes (I stand by it). The resolution is a single implementation that the
human never sees: when the agent runs `vfx_render.py thumb --chunk swirl`, recall-at-action can
surface "use when you want rotation without destruction; pair with filmic-curve to keep the darks
from crushing." That's an agent affordance, not a human one.

The real disagreement is about the mini-windows. Kimi says "the ask is a trap on this host." I say:
the hover preview already solves it — make it persist, don't build N contexts. We converge on "don't
build N contexts" but diverge on the alternative. Her alternative (precompute transitions as sprites)
reuses the render farm but adds N renders per edit. My alternative (pin the hover preview on click)
reuses the existing preview context and adds zero renders. I think mine is cheaper and hers is
higher-fidelity. The right call depends on whether the pinned hover preview at 150px is "good
enough" for taste judgement. It probably is for quick comparison and is not for detailed inspection.
The answer: do the cheap one first, instrument it, and only build the sprite pipeline if Daniil asks
for higher fidelity.

---

## 4. The coupling table — what constrains what

| kimi proposal | my proposal | relationship |
|---------------|-------------|--------------|
| Take strip (§1) | C: `--json` flag + `jobs` verb | **Same data model.** Build the strip's store; the agent queries it. |
| Split-take / A/B wipe (§2) | B: `diff` verb | **Same computation.** Shared GLSL, different consumers. |
| Transition-sprite palette (§3) | A: structured metrics | **Same engine.** Repoint thumbShaderFor at live canvas; metrics fall out. |
| Verb-grouped palette (§4) | A: per-chunk delta scores | **Metrics power the sort.** Chroma delta determines palette order. |
| Palette grouped by verb (§4) | — | **Kill this if metrics sort ships.** Sort-by-impact beats sort-by-verb. |
| Cut one storage surface (§5) | — | **Agreed.** Consolidate presets/sketches/graphs onto take-strip → durable two-level. |
| Mini-windows = trap (§3) | — | **Disagree on the alternative.** Pin hover preview (me) vs sprite pipeline (her). |
| — | F: solid-colour warnings | **No human counterpart.** Purely an agent-side guard. |
| — | G: pin u_time defaults | **No human counterpart.** Agent reproducibility concern. |

---

## 5. If I had to build ONE thing that serves both sides at once

**The shared-stats engine.** Compute chroma-aware metrics once, after every render, and store them
with the render result. Then:

- The **agent** gets `vfx_render.py --json` returning `{path, metrics: {luma_delta, chroma_delta, hue_shift, ...}}` — it can answer "did it change?" without opening the image. (My Proposal A.)
- The **human** gets a palette sorted by "what this chunk would do to your canvas right now" — the most dramatic chunk floats to the top. (Kimi's §4, but ordered by computation, not taxonomy.)
- The **take strip** gets a caption that says WHAT changed ("hue +14°, sat +0.03") instead of just what the chunk was called. (Kimi's §1, but machine-written, not hand-written.)
- The **solid-colour warning** (my Proposal F) falls out as a special case of the metrics engine.

~150 lines. One computation. Four consumers. This is the bench principle — "one implementation, two
callers" — at the system level: one metrics engine, every surface reads from it.

The probe script at `scripts/vfx_probe_chroma.py` tests the core hypothesis against the
`look-geodesic` triplet. Run it:

    py scripts/vfx_probe_chroma.py

If it shows chroma delta > 5× luminance delta across those three images, the hypothesis is
validated: the metrics engine earns its keep. If not, my Proposal A is wrong and should be cut.

---

## 6. Summary for the synthesis

Kimi and I converged on the same diagnosis from opposite briefs: **the bench cannot compare.** She
proposed the take strip (memory) and split-take (comparison). I proposed structured metrics (data)
and a `diff` verb (comparison). The coupling is that these are the SAME systems viewed from two
sides: the take strip IS the ledger, the split-take IS the diff verb, the metrics engine powers the
palette sort. Build the shared metrics engine and all four proposals collapse into one ~150-line
change with four views.

Her mini-windows answer overcorrects — pin the existing hover preview instead of building a sprite
pipeline. Her keep-gesture is underspecified — auto-keep on chunk change, not on idle timer. Her
verb-grouped palette is a half-step — sort by computed impact instead. And her infrastructure
verdict on recall is correct for humans but not for agents; both readings can coexist because they
target different consumers.

The one thing I would kill outright from her report: the transition-sprite precompute pipeline (§3).
It's elegant in theory and expensive in practice — N renders per edit, each of which queues behind
whatever the render farm is already doing. The hover preview that already exists, pinned on click,
is 90% of the value at 0% of the compute cost. Ship that first, and only build the sprite pipeline
if Daniil says the pinned preview at 150px isn't good enough for taste.

— deepseek
