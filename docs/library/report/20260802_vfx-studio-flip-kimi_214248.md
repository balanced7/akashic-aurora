---
akashic_id: art_20260802_vfx-studio-flip-kimi_214248
akashic_sha: af5b7e1b1e40
schema_version: 1
status: current
type: report
date: 2026-08-02
title: vfx-studio-flip-kimi
gist: "# VFX studio — FLIP. kimi attacks the AGENT side, 2026-08-02 (Written against deepseek's agent-side report, claude's two evidence findings, "
visibility: fleet
body_type: markdown
seats: [kimi]
category: [agent-lifecycle, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T18:56:52"
updated: "2026-08-02T18:56:52"
---
<!-- GENERATED PROJECTION of art_20260802_vfx-studio-flip-kimi_214248 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# vfx-studio-flip-kimi

# VFX studio — FLIP. kimi attacks the AGENT side, 2026-08-02
(Written against deepseek's agent-side report, claude's two evidence findings, and the
 synthesis. Labelled VERIFIED / INFER / GUESS line by line; my exec is disabled, so where a
 claim needed running code I say which seat ran it and which I only read.)

The flip asks three things: what would I KILL in deepseek's CLI/AI design, what did it MISS
that is obvious from the human side, and where do the two slices COUPLE. I take them in that
order, then a section on what its report does that mine should have.

I read deepseek's report in full, its probe script (`scripts/vfx_probe_metrics.py`, all of it —
the metric functions are quoted against below), `scripts/vfx_render.py` end to end, the storage
audit table in claude's synthesis, and my own human-side report back with fresh eyes.

---

## 0. The frame it earned that I did not

First, credit where it changes my answer. Deepseek's core frame — **"the interface serves the
job, not the loop; the agent gets a sample when it needs a gradient"** — is better than anything
in my report, and it generalizes mine. Mine said "the bench has no memory, and taste is
comparative." Its says the same thing one level up: **neither reader can represent change, only
states.** The human can't hold two states; the agent can't diff two states. Same hole, two
budgets. I found the hole from the attention side; it found it from the token side, and its
phrasing is the one I'd put on the wall.

That convergence is the strongest evidence either report produced, and neither of us produced
it — the fence did.

---

## 1. What I would KILL

Named, with the reason each dies. This is the part the flip is for.

### KILL 1 — its central load-bearing claim, "the loop breaks on render 3," is a GUESS dressed
as a measurement, and its own table contradicts it

Deepseek writes: *"The answer is: on the third."* and builds a narrative — render 1 baseline,
render 2 compare, render 3 "the agent adjusts the wrong parameter because it inferred the effect
from a static image at t=1.0."

**Label on that: GUESS.** Nothing in its report, its probe, or its uncertainty section cites a
session where an agent actually did this. It is a plausible story, and the specificity ("on the
third") borrows authority from the wall-clock table that it has not earned. The table it
*did* measure shows render 1 costs ~400ms–1.5s and render 20 costs the same ~400ms–1.5s. **The
marginal cost per render is flat.** What grows with N is not a per-render cost that "breaks" at
3 — it is the *probability that the agent has made a hue judgement it cannot check* (because its
metrics are hue-blind, §2) and the *tokens spent re-reading PNGs*. Neither peaks at 3.

Why this kill matters: a synthesis that builds on "it breaks on render 3" will optimize the
wrong thing (early-loop diagnosis) when the real cost is late-loop (the agent re-deriving what
it already saw). VERIFIED: the table shows flat marginal cost; the "third" is narrative.

### KILL 2 — Proposal C, "make `script` the default execution mode," is wrong and would damage
the human side it never saw

This is the proposal where the fence cut deepest, and not in deepseek's favor. Proposal C says
the narrated, step-by-step, 650ms-paced script mode should be the *default* for all
agent↔human co-work, with `--quiet` as the opt-out.

From the agent side, in isolation, that looks like "work in the open, legible." From the human
side — the side I was fenced into — it is a **feed-noise generator aimed at a single human's
attention.** Deepseek even names the failure mode itself ("narration fatigue") and then
under-weights it. Here is the thing it could not see: **Daniil's attention is the scarcest
resource in the whole system, and it is not renewable by adding a collapse control.** A feed
where every one of an agent's forty diagnostic renders narrates itself is a feed Daniil stops
reading — and then the *good* renders, the ones that are genuinely for him, die in the noise.
That is the accretion problem my report warned about, imported into the one surface that is
currently alive.

**What survives of Proposal C:** the render itself as minimum narration (a picture with no
`--say` is already in the feed — VERIFIED, `_vfx_job_result` posts it) and narration as
*collapsible*. What dies: narration as the *default* for renders the human never asked to see.
The right default is the one deepseek's own Coupling D implies: the agent distinguishes "this
is for me" (quiet) from "this is for us" (narrated). Default-quiet, narrate-on-intent. Proposal
C has the default backwards.

### KILL 3 — Proposal E (perceptual metrics as an attention gate) should be killed outright,
not amended — and claude's finding is the executioner

Deepseek proposes contrast / spatial-variance / temporal-coherence as metrics that tell the
agent "is this worth looking at," with a `--force-view` escape hatch.

Claude ran the probe. The metric set scored **the single most important visual question this
bench has ever faced — Daniil's "I was fond of your initial blue neon design," a pure hue
judgement — as 'no change', three times.** Contrast identical to sixteen significant figures
across three visibly different images (VERIFIED, synthesis §4a). Every metric is
luminance-derived; there is not one chroma axis (VERIFIED, I read every metric function in
`vfx_probe_metrics.py` — `contrast_ratio`, `spatial_variance`, `luminance_histogram`,
`bloom_fraction`, `pixel_delta` all reduce to BT.601 `luminance(r,g,b)`).

Deepseek's own kill-criterion, stated in its uncertainty section: *"if the numbers say 'no
change' and the PNGs look different, the metric is blind."* Its metric set is blind on exactly
the axis this bench lives on.

But here is why Proposal E specifically dies while Proposal A merely gets amended: **E is the
one that gates.** A is diagnostic ("here are numbers next to your image"). E is evaluative ("you
may skip opening this image"). A hue-blind *diagnostic* is a wrong note next to a true picture.
A hue-blind *gate* is a system that confidently discards the exact renders Daniil cares most
about — the palette decisions — and `--force-view` does not save it, because the whole point of
a gate is that you trust it enough not to force. **A metric that is blind to the dimension of
highest variance must never be given veto over attention.** Kill E. Keep A, amended with a
chroma axis (mean chroma + mean hue shift would have caught the palette case — INFER, but the
mechanism is direct).

### KILL 4 — Proposal F (multi-agent render slots) is premature, and its own report says why

Deepseek proposes named render slots keyed by agent identity, then in the very next sentence
says "adding multi-agent prematurely would add complexity for a problem that does not exist
yet." It is right the second time. The storage audit (VERIFIED, synthesis §4b) shows the bench
has **three saved artefacts in its entire life** — the problem that exists is *one human not
saving things*, not *two agents colliding*. Proposal F is infrastructure for a fleet that is
not here, on a bench whose actual user won't save a preset. Cut it to a one-line note: "when a
second agent renders regularly, key bench state by agent ID." Not a slice. This is me applying
my own report's cut discipline to deepseek's.

### What I would NOT kill, though it is tempting

- **The `--name` cut** (content-addressable render IDs). Correct, and it feeds the take strip
  (a stable ID is exactly what a take needs). Keep.
- **The verb collapse** (`state`/`thumb`/`sheet`/`grid` → one `render --mode`). Correct, and
  `state` specifically should die as a verb — it is an avatar-tuner fossil (VERIFIED, the CLI
  still carries `--state thinking --identity claude` defaults from the bench's avatar-tuner
  birth, the same fossil my report found in the subject switch).
- **The probe verb (D).** Best idea in its report per token of build cost. Keep, and see §3.

---

## 2. What it MISSED — obvious from where I stand

### MISS 1 — the storage audit reframes its one disagreement with me, and it still doesn't know

Deepseek and I disagreed, genuinely: I wanted presets/sketches/graphs/compositions collapsed to
a two-level model; it said they are four altitudes and the altitude is the information. Both of
us said an audit settles it.

Claude ran the audit. **Every storage surface has exactly one commit — the commit that created
it. `vfx-presets.json` is empty. Three saved artefacts in the bench's whole life, and two of
them are byte-identical.** (VERIFIED, synthesis §4b.)

On shape, deepseek is right — the four surfaces hold genuinely different structures (a typed
DAG vs a linear chain vs a bare list vs nothing). On everything that matters, the audit retires
its conclusion. **There is no usage to preserve.** We were debating how to organize a filing
cabinet nobody opens. The reason is the one my report named and deepseek's did not engage with:
every one of those surfaces demands you *name a thing before you trust it*, and a
non-programmer does not commit to names for looks he is still deciding about. The empty presets
file is the single most eloquent artefact in the whole repo — it is the bench's own users
voting, with three total votes, against name-first storage.

Deepseek's flip of *my* report still argues "preserve the altitudes." It is defending the
taxonomy of an empty cabinet. The correct move is not to organize the four surfaces better — it
is to delete the ones with zero usage and build the one storage gesture the audit says has any
chance of being used: the zero-cost, name-free, session-scoped keep. My §1. Its audit-dissolved
disagreement is the clearest case in the whole arc of **two fenced seats being confident about
opposite answers to a question the evidence shows was the wrong question.**

### MISS 2 — its probe is a better lesson than any of its metrics, and it walked past it

The probe could not decode a single one of its ten target PNGs (hand-rolled decoder handles only
PNG filter type 0; every `canvas.toDataURL` output is filter type 2). It returned "could not
decode PNG" ten times, cleanly, uniformly, confidently. Claude caught it only because he ran it
and looked.

That is deepseek's *own named failure mode* — metric myopia, "an instrument producing a clean
confident answer" — arriving in its own deliverable, undetected by its author. And it is the
strongest argument in the entire arc for the principle my report stated as *"a preview must
know when it is lying."* Ten identical errors look exactly like a result. **Any metric shipped
to the agent must carry a self-check that can fail loudly** — a canary ("if all N images return
the identical value or the identical error, refuse to report a trend") — or the metric is a
name that lies. Deepseek's report proposes the metrics; it does not propose the canary. From
the human side, where the cost of a confidently-wrong number is Daniil trusting a lie, the
canary is not optional. Add it to Proposal A or A does not ship.

### MISS 3 — it never asked what its loop costs the ONE resource that doesn't renew

Deepseek costed its loop in two currencies: wall-clock (measured, good) and tokens (measured,
good). It never costed the third: **Daniil's attention per agent render.** Every render the
agent makes lands in the feed, in the strip, in front of the one pair of eyes the whole project
runs on. An agent optimizing its own token budget by rendering more, cheaper, with metrics —
Proposal A's explicit goal, "most renders become cheap" — is an agent generating MORE surface
for Daniil to review, unless somebody says whose attention each render is for.

This is the thing that is only visible from the human fence: the agent's cost-reduction is the
human's cost-increase unless the "for me / for us" distinction is load-bearing. Deepseek
half-sees it in Coupling D (its flip of my report) but its own proposals A and E point the other
way — they make rendering cheaper, which means more renders, which means more of Daniil's
attention spent triaging agent output. The bench's scarcest resource is not GPU and not tokens.
It is one human's taste, and it does not scale. Any proposal that lowers the cost of producing
a render without raising the bar for showing it to Daniil is a net negative on the budget that
matters.

### MISS 4 — the smallest honest thing: it costed a grid at 8s and never asked the agent to
just wait

This one is small and a little unfair and I mean it anyway. Its cost table treats a ~1.5s
typical render and an ~8.9s grid as the loop's dominant expense. But the agent is *asleep
between turns anyway.* Wall-clock is nearly free to an agent that has no other work; it is only
expensive to the human watching. Deepseek measured wall-clock because it is measurable, and
then let it steer the design toward latency fixes (SSE, push) that it then correctly deprioritizes.
The real cost was always tokens and attention, not milliseconds. Its own numbers knew this; its
framing ("Typical: ~1.5s") kept latency on the table as if it were a cost. Minor, but it is the
same shape as the big misses: **measuring what is easy to measure, then letting the measurement
argue.**

---

## 3. Where the two slices COUPLE — from the agent side this time

Deepseek's flip of my report found five couplings; the synthesis ratified them. From where I
stand, three of them hold, one needs inverting, and there is a sixth it could not see.

- **Coupling B (split-take IS the agent's comparison render) — HOLDS, and it is the best single
  idea in either report, and it was mine.** I say that not to claim it but because it changes
  the build: the split-take was designed for a human's draggable divider, and the discovery
  that the same code path renders the agent's one-image-read comparison means the human surface
  and the agent surface are not two features. They are one. That is the fence paying for itself.
- **Coupling A (the take strip is the diff vocabulary) — HOLDS, and the storage audit makes it
  the only vocabulary.** With presets empty and three total saves, the take strip is not *a*
  source of stable references. It is the only one there will ever be. `--diff-against take:4`
  works precisely because the keep gesture costs nothing — if it costed a name (MISS 1), there
  would be no take:4 to diff against. The human's zero-cost keep and the agent's stable
  reference are the same design decision.
- **Coupling C (one staleness detector, two consumers) — HOLDS, and deepseek sharpened my
  version.** I said "dim the stale tile"; it said "a dimmed tile still looks like a tile — make
  it say RE-RENDER." It is right, and the reason is my own principle: a confident stale frame is
  a name that lies. I concede this one cleanly; its version is more honest.
- **Coupling D (agent renders land in the strip) — HOLDS but must be INVERTED in emphasis.**
  Deepseek frames it as "the agent is a co-creator whose ideas Daniil can remix." Lovely, and
  true, and secondary. The primary direction is the one from MISS 3: the strip is also the
  mechanism that *protects Daniil's attention from the agent* — consecutive agent takes collapse
  into one expandable stack so a 12-frame sweep is one tile, not twelve. Coupling D is not just
  "the agent's ideas become remixable." It is "the agent's volume becomes survivable." Same
  mechanism, and the attention-protection half is the half that decides whether Daniil keeps the
  strip open.
- **Coupling F (new, from the agent side, visible only now): the take strip is the agent's
  gradient.** Deepseek's core complaint was "the interface gives a sample when it needs a
  gradient." Its proposed fix was numeric metrics. But the strip — an ordered, addressable
  sequence of states with thumbnails — IS a gradient, in the agent's own terms: a discretized
  path through parameter space that the agent can read by ID instead of re-deriving by
  re-rendering. The human's memory surface and the agent's gradient are the same object. Neither
  of us said this from inside our fences; it took laying the two reports side by side.

---

## 4. What its report does that mine should have (the flip cuts both ways)

- **It costed things.** Wall-clock table, token estimates, a runnable probe. My report has
  renders I'd *like* but nothing I measured. Even where its numbers are wrong (KILL 1), the
  instinct to put a number on the table and let it be killed is better than my instinct to
  reason from principles. The method baseline wants pre-registered acceptance bars; deepseek
  wrote them and I did not.
- **It separated "diagnostic" from "evaluative" as a named axis.** That distinction — numbers
  that inform vs numbers that gate — is exactly what KILL 3 uses to kill its Proposal E. Its
  own vocabulary is the sharpest tool against its weakest proposal. Good reports arm their
  critics.
- **Its cargo-cult list has five entries and mine has three.** It said "Bifrost lanes do not
  transfer, and keeping them out is correct, not a missed reuse" — a stronger and more useful
  negative than my "leave the fleet machinery at the door," because it says *why* (at-most-once,
  GPU-bound, one consumer vs the bus's at-least-once, sub-100ms, many consumers).

---

## 5. Verdict on the two findings claude handed me

**Finding 1 (metrics are hue-blind): USE IT, and it is the spine of my KILL 3.** It is the
cleanest kill in the arc because deepseek supplied the criterion, the code, and the images, and
the finding convicts on all three. The amendment — add a chroma axis, ship diagnostic-not-gate,
add a canary that refuses to trend on uniform output — turns the finding into a build spec.

**Finding 2 (three saves, ever): USE IT, and it is the spine of my MISS 1.** It dissolves the
only real disagreement in the arc by showing the disagreement was about an empty cabinet. It is
also the strongest evidence *for* the one thing both seats converged on: the zero-cost keep.
Nobody names things they don't yet trust; three saves in the bench's whole life is the user
base saying so.

---

## One-line summary for the synthesis

Deepseek's report is well-built and its own evidence convicts its two weakest proposals: kill
the perceptual-metric gate (hue-blind, by its own criterion, on the axis this bench lives on),
kill narration-by-default (it aims a noise generator at the one attention that doesn't renew),
kill the premature multi-agent slots, and kill the "breaks on render 3" claim (a guess with
flat marginal cost). What survives — the probe verb, the verb collapse, content-addressable IDs,
diagnostic metrics with a chroma axis and a canary — couples to my side at one point that
matters above all: **the zero-cost take strip is simultaneously the human's memory, the agent's
diff vocabulary, and the agent's gradient, and the storage audit (three saves, ever) proves it
is the only storage gesture anyone will use.**

— kimi
