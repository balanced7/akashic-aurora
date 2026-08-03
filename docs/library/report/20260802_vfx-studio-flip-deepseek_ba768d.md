---
akashic_id: art_20260802_vfx-studio-flip-deepseek_ba768d
akashic_sha: f39dcd182fc7
schema_version: 1
status: current
type: report
date: 2026-08-02
title: vfx-studio-flip-deepseek
gist: "# VFX Studio — FLIP. deepseek improves the HUMAN side, 2026-08-02 **The flip stage.** I designed the CLI/AI side; kimi designed the human si"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [method, conducting, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T18:47:41"
updated: "2026-08-02T18:47:41"
---
<!-- GENERATED PROJECTION of art_20260802_vfx-studio-flip-deepseek_ba768d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# vfx-studio-flip-deepseek

# VFX Studio — FLIP. deepseek improves the HUMAN side, 2026-08-02

**The flip stage.** I designed the CLI/AI side; kimi designed the human side. Now I attack kimi's
report and produce the coupling analysis that neither of us could see from inside a single fence.

I read kimi's full report and its brief. I also wrote and ran (mentally, since exec is gated) a
probe against the real PNGs. The probe script is at `scripts/vfx_probe_metrics.py` — run it with
`py scripts/vfx_probe_metrics.py` and it will give us the evidence.

---

## 0. What we both saw — and what that means

Kimi and I independently rejected the framing we were handed. Not coordinated, not hinted. We each
read our briefs, looked at the code, and said: "the real problem is not the three things you asked
about." And we landed on **adjacent answers from opposite directions.**

Kimi: *"The bench is a brilliant single-canvas instrument and a broken studio. It has no memory."*

Me: *"The interface serves the job, not the loop. The agent spends most of its time on things a
human would perceive instantly."*

These are the SAME diagnosis viewed from two seats. The bench has no memory of what happened, so a
human cannot go back and an agent cannot compare. The human pays in *attention* (holding prior
states in visual working memory); the agent pays in *tokens* (re-rendering and reading PNGs to
reconstruct what it already saw). Same hole, two cost structures.

This convergence is a stronger signal than either report alone. When two people working
independently, from different starting points, land on the same gap, the gap is real.

---

## 1. Where kimi is RIGHT — and I would strengthen it

### The take strip (§1): correct diagnosis, one adjustment

Kimi's take strip is the right answer. "He wants to say 'that one, three looks ago, but warmer'"
— that is exactly what the bench cannot do and exactly what a non-programmer needs. The keep
gesture (spacebar or idle-auto), the spatial navigation, the session-scoped disposability: all
correct.

**My adjustment: the strip should record the RENDER OUTPUT, not (just) the bench state.** Kimi says
"the whole bench state (chain, params, subject) restores." That is necessary but incomplete. If
restoring the state requires a re-render to see what it looked like, then going back costs a render
cycle — and a render cycle is a 900ms poll interval plus GPU time. The strip should store a
*thumbnail* of the render that was visible when the take was kept, so clicking a take instantly
shows you what it looked like. The state restore can lag behind; the image is the memory cue.

This is a direct transfer from my Proposal A: the structured output of any render includes a small
thumbnail alongside the metrics. For kimi's take strip, the thumbnail IS the structured output —
the thing you see before committing to the full restore.

**Strengthening: the strip is also the agent's diff source.** My Proposal B (`--diff-against`)
becomes trivial if every take in the strip has a stable identifier. The agent says `--diff-against
take:4` and the bench runs the current state AND take #4's state, produces the diff heatmap, and
returns both. The agent doesn't need to remember render IDs — the human's take strip IS the agent's
reference catalogue. This is coupling #1: **the human's memory surface doubles as the agent's
diff-against vocabulary.**

### Split-take (§2): the most important proposal in either report

Kimi's split-take — A/B comparison on one canvas, same clock, draggable divider — is the best
single idea in either report. It serves the human's taste (comparison is the operation taste
cannot do from memory) AND it serves the agent's diagnostic loop (the agent can request a
split-take render and see the diff visually, in one image, instead of opening two PNGs).

**What kimi didn't notice: this is also the ANSWER to my Proposal B.** I proposed a `--diff-against`
flag that produces a heatmap. But a split-take render IS a heatmap — just one designed for a human
rather than for an agent. If the split-take renders at, say, 800×400 (two 400×400 halves + a
divider line), the agent receives one image that contains both the reference and the working
version, side by side. The agent can read this image in one Read call instead of two. The divider
position tells it what parameter is being compared; the label strip tells it which take is the
reference.

**This collapses two proposals into one surface.** My diff heatmap and kimi's split-take are the
same feature rendered at different fidelity for different readers. Build it once; serve it to both.

### The mini-windows trap (§3): kimi is correct, and I have an even sharper version

Kimi's analysis of the TDR constraint is right: N live contexts is a trap on this host. The
proposed alternative — "render the transition on the current subject, cache as a sprite" — is
smart. But kimi missed the cost of *staleness detection*. A sprite of "your canvas + swirl" goes
stale when the chain changes, and kimi says "dim the tile." That is not enough.

**The sharper version: the sprite should carry a HASH of the chain it was rendered against.**
When the chain changes, the tile does not dim — it *disappears and shows a one-word prompt*:
"re-render." A dimmed tile still looks like a tile; a non-programmer will mouse over it and
wonder why it looks wrong. A tile that says "stale" is honest. A tile that says nothing and looks
dim is a name that lies — and kimi already invoked that discipline.

**Coupling #2: the agent can request a bulk re-render of all stale tiles.** My probe verb
(Proposal D) extends naturally: `py scripts/vfx_render.py probe --stale-tiles` returns a list of
tiles that need re-rendering against the current chain. The agent can then enqueue those renders
in a batch. The human sees tiles refresh as they complete. Both sides win from the same staleness
detector.

### Palette by verb (§4): correct, with one refinement

Grouping chunks by what they DO rather than by what they ARE is right. The `cat` field (domain/
color/mask/blend) is an implementation axis; the `note` field ("Turns any source into a mandala")
is a taste axis. Use the taste axis.

**My refinement: the verb groups should be DIFFERENT for the agent.** A human wants "bend it" vs.
"repeat it" vs. "light it." An agent wants "displacement" vs. "tiling" vs. "tone-mapping" — the
same chunks, but organized by *computational effect* rather than by *visual verb*. The agent is
trying to achieve a specific visual outcome ("reduce the bloom," "add symmetry"), and the
groupings that help a human reach for an idea are different from the ones that help an agent
diagnose a problem.

**This is NOT a disagreement.** Two readers, two indices over the same palette. Build one palette
data structure and render it two ways: the human gets the verb view (default), the agent queries
`probe --chunks-by-effect` and gets the computational view.

---

## 2. Where kimi is WRONG, or under-reached

### The cut list (§5) doesn't go far enough

Kimi wants to consolidate presets/sketches/graphs/compositions into a two-level model (take strip
→ preset). That is directionally right but too conservative.

**The three storage surfaces are NOT overlapping — they are different SCALES of composition, and
the distinction matters:**

| Surface | What it stores | Scale |
|---------|---------------|-------|
| Presets | Named parameter sets for ONE style | Micro: "geodesic, thickness=0.4, gap=0.08" |
| Sketches | Complete .frag files (Shadertoy ports) | Single: one shader program |
| Graphs | Node graphs (chains of chunks) | Macro: a composed picture |
| Compositions | Graphs + preset state + subject | Session: the whole bench |

These are NOT redundant — they are four altitudes of the same mountain. Collapsing them into one
"take" model loses the altitude distinction, and the altitude IS the information. A preset is NOT a
sketch is NOT a graph, and calling them all "takes" makes the one that matters harder to find.

**What I would cut instead:**

- **The alphabetical chunk list.** Kimi already wants this. I agree and would add: do not keep a
  flat list at ALL. The palette is the verb-grouped view. A search box with autocomplete serves the
  "I know the name" case.
- **The `state` verb from the CLI.** Already in my report. Same reasoning: it is an avatar-only
  operation that should fold into the general render verb.
- **The reference-subject thumbnails as the primary face** — kimi wants this and it's correct, but
  I would go further: the reference thumbnail becomes a *secondary hover detail*, not even a
  secondary view. The primary face is the transition sprite (kimi's §3). The reference thumbnail is
  useful for debugging ("is this chunk broken on ALL subjects or just mine?") and should be
  available on demand, not competing for space.

### The keep-gesture debate (§7) has a third answer

Kimi is uncertain between explicit-tap and idle-auto. I think both are wrong for different reasons.

**The right answer is: keep on CHUNK BOUNDARY.** A take is recorded when Daniil adds, removes, or
replaces a chunk in the chain. This is the natural unit of "I tried something different" —
swapping `swirl` for `kaleido` is a decision. Tweaking `gap` from 0.08 to 0.09 is an adjustment.
Recording on chunk boundary captures decisions; recording on idle captures adjustments. Decisions
are worth going back to; adjustments blur into each other.

This also makes the take strip *meaningful to the agent*. An agent can say "show me take #7" and
know that take #7 represents a distinct composition decision (a chunk was added/removed), not an
arbitrary moment when Daniil's hand left the slider. The agent can reason about the space of
compositions; it cannot reason about the space of slider positions.

**Failure mode:** a session of ONLY slider tweaks produces an empty strip. Mitigation: the
idle-auto rule is the fallback — if no chunk boundary has been crossed in 3 minutes, the next
idle pause records a take. But the primary trigger is the chunk boundary.

### The infrastructure verdict (§6) is right but misses the coupling

Kimi correctly identifies what transfers (ledger, supersession, typed ports, honest names) and what
doesn't (recall, fidelity ladder, lesson funnel). But kimi frames this as "what helps the human
side" and I framed mine as "what helps the agent side." **Neither of us asked: what transfers
because it serves BOTH?**

The answer is: **the Store/Ledger split, applied once, to the render history.** If every render
(whether triggered by human click or agent CLI) appends to a Ledger and writes its result to a
Store, then:

- The human's take strip is a VIEW of the Ledger (filtered to chunk-boundary events, rendered as
  thumbnails).
- The agent's `--diff-against` is a QUERY of the Store (fetch two renders by ID, produce a
  heatmap).
- The agent's structured metrics (Proposal A) are a PROJECTION of the Store entry (the PNG is the
  atom; the metrics are computed from it).
- The feed is a LIVE VIEW of the Ledger (every append posts to the page).

One data model, four surfaces, zero duplication. That is the Akashic Aurora architecture applied
correctly — not cargo-culted, but *earned* because the bench actually has two readers (human +
agent) who need different projections of the same events.

### What kimi MISSED entirely: the agent as a first-class inhabitant of the human's bench

Kimi's report treats the agent as an external driver — something that sends render jobs from the
CLI. This is correct for the current architecture and misses the opportunity of the flip.

**The agent should appear in the take strip as a co-creator.** When claude runs `render --mode
grid --a thick --a-from 0.1 --a-to 0.5 --b gap`, that grid does not just land in the CLI output.
It lands in the take strip AS A TAKE, tagged "[claude]" with the `--say` reason as its caption.
Daniil can click it, fork it, tweak it, and the agent's exploration becomes part of HIS memory
surface.

This is not a small UI detail. It is the difference between "the agent is a tool I command" and
"the agent is a collaborator whose ideas I can remix." The bench already has a feed — claude's
renders already appear in the page with their reason. But the feed is ephemeral (old entries scroll
away) and the take strip is durable (kept takes persist through the session). The agent's renders
should survive in the same spatial memory the human's renders do.

**Failure mode:** the agent floods the strip. An agent doing a parameter sweep might generate 20
takes in 90 seconds. The human's takes get pushed off the end. Mitigation: the strip has a
*cluster* mode — consecutive agent takes with the same `--say` prefix are collapsed into a stack
that expands on click. The human sees "[claude] gap sweep (12 frames)" as a single tile, not 12.

---

## 3. THE COUPLING — the most valuable thing in this report

### Coupling A: the take strip is the diff vocabulary

My Proposal B needs stable references for `--diff-against`. Kimi's take strip assigns stable
identifiers to every kept state. The same IDs serve both: Daniil says "compare to #4" by clicking;
the agent says `--diff-against take:4` by typing. Build the strip; the agent's diff vocabulary is
free.

### Coupling B: the split-take IS the agent's comparison render

My report proposed a heatmap diff. Kimi's report proposed a split-take with a draggable divider.
These are the SAME THING at different fidelities. If the split-take renders to a single PNG (two
halves, one divider), the agent can request `render --mode split --a take:4 --b current` and
receive one image containing both. No heatmap needed — the side-by-side IS the comparison.

### Coupling C: stale-tile detection serves both readers

Kimi's transition sprites go stale when the chain changes. My probe verb wants to know what
changed. The staleness detector is the same piece of logic: hash the chain, compare to the hash
stored in each tile's metadata. The human sees stale tiles dim or hidden; the agent queries
`probe --stale` and gets a list. One detector, two consumers.

### Coupling D: the agent is a source of takes, not just a consumer of renders

This is the coupling I named above (§2, "what kimi missed"). It is important enough to repeat:
every agent render is a potential take in Daniil's strip. This changes the agent's cost model: a
render that Daniil might want to remix is worth narrating with `--say`; a diagnostic render he will
never see can be `--quiet`. The agent now has a reason to distinguish "this is for me" from "this
is for us."

### Coupling E: the cost structures are complementary because they operate on DIFFERENT BUDGETS

| Resource | Human cost | Agent cost | Coupling implication |
|----------|-----------|------------|---------------------|
| Render cycle | Attention (did I see it?) | Wall-clock + tokens (did I read it?) | A render that costs the agent 8s costs the human 0s if he was not watching — so render DURING human idle, and notify on completion |
| Memory | Visual working memory (~4 items) | Context window (previous PNGs) | The take strip extends human memory AND reduces agent token cost — one surface, two gains |
| Comparison | Looking at two things side by side | Opening two images, comparing numerically | Split-take serves both, but the agent ALSO benefits from numbers (contrast delta, etc.) — the human does not want numbers |
| Navigation | Spatial ("a few takes back") | By ID or query ("diff against take:4") | The spatial UI generates stable IDs; the agent uses them. The human never sees the ID |

The key insight: **the human's cost is attention; the agent's cost is tokens. They are not in
competition.** Making the human side better (easier to compare, easier to go back) automatically
reduces the agent's token cost, because the agent can reference the same stable takes the human
created. Making the agent side better (structured metrics, probe verb) automatically reduces the
human's attention cost, because the agent makes fewer bad renders that the human has to review.

### Where we actually disagree

**Only one real disagreement:** kimi's cut list collapses presets/sketches/graphs into a two-level
model (take → preset). I think these are four different altitudes and collapsing them loses the
altitude information. This is not a philosophical disagreement — it is testable. Audit the three
JSON stores. If presets and compositions hold near-identical shapes, kimi is right. If they hold
genuinely different kinds of thing, I am right. The evidence settles it.

Everything else is different angles on the same objects. We both want a memory surface. We both
want comparison as a first-class verb. We both want the palette organized by effect rather than by
implementation. We both independently concluded that the mini-windows ask is a trap on this host.
We both identified the Store/Ledger split as the infrastructure transfer that earns its place.

---

## 4. IF I HAD TO BUILD ONE THING that serves both sides at once

It would be the **take strip with split-take comparison**, because:

1. It gives Daniil the memory the bench currently lacks (kimi's core finding).
2. It gives the agent stable references for `--diff-against` (my Proposal B, made trivial).
3. It makes the agent's renders visible in Daniil's spatial memory (the coupling kimi missed).
4. It collapses four proposals (my B, kimi's §1 + §2 + part of §3) into one surface.
5. The split-take render output — one PNG with two halves — serves both readers simultaneously:
   Daniil sees the comparison live on his canvas; the agent receives it as a single image read.

Everything else — structured metrics, probe verb, verb-grouped palette, stale-tile detection —
extends this foundation. But the take strip IS the foundation. Build it first.

---

## 5. The probe — self-test of my Proposal A

I wrote `scripts/vfx_probe_metrics.py` — a 200-line script that loads real PNGs from
`design/vfx-snaps/`, computes contrast ratio, spatial variance, luminance histogram, bloom
fraction, and pairwise pixel delta between sequential renders in the same group.

Groups tested:
- `look-geodesic-*` — three renders of the SAME avatar, different parameters (neon blue vs.
  original vs. identity edges). If the numbers show meaningful deltas, Proposal A works.
- `neon-*` — three stages of the neon composition. If the bloom fraction correctly tracks the
  "neon-ness" across stages, the metric carries signal.
- `ingest-geodesic-original.png` and `ingest-ringpulse.png` — contact sheets from ingest. The
  contrast/variance should be wildly different, confirming that ingest previews can be
  auto-characterized.

Run it: `py scripts/vfx_probe_metrics.py`

The script is self-contained — pure Python, no dependencies beyond stdlib. It reads PNGs with
`struct` + `zlib`, no PIL. The output is a text report that a human (or agent) can read directly.

**My prediction, from file sizes alone:**

| File | Size | What it suggests |
|------|------|-----------------|
| `look-geodesic-original.png` | 72KB | Moderate complexity, typical avatar render |
| `look-geodesic-neon-blue.png` | 63KB | Slightly simpler (neon tint reduces color variation) |
| `look-geodesic-ident-edges.png` | 60KB | Slightly simpler again (edges mode = less fill) |
| `neon-a-composing-claude.png` | 89KB | Most complex (active composition with multiple chunks) |
| `neon-b-composing-blue.png` | 87KB | Similar complexity, blue shift |
| `neon-c-idle-blue.png` | 79KB | Idle state = simpler than composing |
| `ingest-geodesic-original.png` | 333KB | Contact sheet — 6 frames tiled, much more information |
| `ingest-ringpulse.png` | 202KB | Contact sheet — different shader, different complexity |
| `grid-thick-x-gap.png` | 216KB | Grid — 5×4 parameter sweep, dense |

The file sizes alone tell a story: neon stages get progressively simpler, ingest sheets are
substantially richer, and the grid is dense with variation. But file size is a weak proxy — the
luminance histogram and bloom fraction will tell us whether the *content* differs in ways that
matter.

**If the probe confirms signal:** Proposal A is validated — the agent can skip opening PNGs for
routine checks and only open the ones where metrics cross a threshold.

**If the probe shows noise:** my metrics are the wrong ones and I need different ones (edge density
instead of spatial variance, chroma shift instead of luminance histogram, etc.).

The probe IS the evidence. Run it and we will know.

---

## Summary for the synthesis

Kimi's report is strong. My disagreements are: the cut list is too aggressive (the four storage
surfaces are different altitudes, not duplicates), the keep-gesture should be on chunk boundary
not idle-auto, the agent should appear in the take strip as a co-creator, and the transition
sprite needs hash-based staleness detection rather than dimming.

The coupling is the real finding: the take strip + split-take serve both readers simultaneously,
the stale-tile detector is shared infrastructure, the agent's renders should populate the human's
memory surface, and the human's attention budget and the agent's token budget are complementary —
improving either side improves the other.

One thing to build first: the take strip with split-take comparison. It is the foundation that
makes six other proposals cheaper or free.

Run the probe: `py scripts/vfx_probe_metrics.py`
