# VFX studio — synthesis and sliced plan, 2026-08-02

Synthesised by claude from a fenced two-seat design arc Daniil commissioned. Sources, all preserved
in full:

- kimi, human side — `vfx-studio-human-side-kimi-report-2026-08-02.md` (adopted; projection at
  `docs/library/report/20260802_vfx-studio-human-side-kimi-report_da2c3d.md`)
- deepseek, agent side — `vfx-studio-agent-side-deepseek-report-2026-08-02.md` (adopted;
  `docs/library/report/20260802_vfx-studio-agent-side-deepseek-report_fa63cb.md`)
- deepseek, flip — `vfx-studio-flip-deepseek-2026-08-02.md`
- kimi, flip — pending at time of writing (see §7)
- claude, evidence — two probes run for this synthesis, §4

**The fence held.** Neither seat saw the other's brief, output, or my reading until the flip. What
follows leans on that: the convergence below is a measurement, not a consensus I steered.

---

## 1. Both seats rejected the framing, independently, and landed on the same hole

kimi was asked what would make the UI better. deepseek was asked what the agent interface should
be. Neither answered the question as posed.

> **kimi:** "The bench is a brilliant single-canvas instrument and a broken studio. It lets Daniil
> make THE thing on screen very well. It gives him no way to hold TWO things at once, to go BACK,
> or to know what he changed. Remix is a memory act before it is a motor act."

> **deepseek:** "The interface serves the job, not the loop… the interface gives the agent a
> *sample* when it needs a *gradient*."

These are one finding in two currencies. **The bench can render states and cannot represent
change.** The human therefore cannot compare (and taste is comparative — it is the faculty that
cannot operate from memory). The agent therefore cannot perceive difference (and pays tokens to
re-derive what it already saw). Same hole; the human pays in attention, the agent pays in tokens.

kimi verified the hole rather than asserting it: grep for `version|compare|history|undo|fork|
lineage|revert` across the bench returns **zero hits**. Four ways to store, none that model
versions of one thing or two things side by side.

Daniil's three asks — drag-drop, mini shader windows, previews — are, on kimi's reading, taste
vocabulary reaching for *"let me see this AND that, and go back"* and naming the nearest UI objects
there are words for. I find that persuasive, and the evidence in §4 supports it from a second angle.

---

## 2. The coupling (deepseek's flip, and the real payoff of the exercise)

Neither seat could see this from inside its fence. Condensed:

- **A — the take strip is the diff vocabulary.** Human clicks "compare to #4"; agent types
  `--diff-against take:4`. Build the human memory surface and the agent's reference catalogue is
  free.
- **B — split-take IS the agent's comparison render.** kimi's side-by-side and deepseek's diff
  heatmap are the same feature at two fidelities. One PNG containing both halves is one image read
  for the agent and a live comparison for the human. Two proposals, one surface.
- **C — stale-tile detection serves both.** Hash the chain into each cached tile; human sees stale
  tiles marked, agent queries `probe --stale` and batch-re-renders. One detector, two consumers.
- **D — the agent is a source of takes, not just a consumer of renders.** deepseek's sharpest point,
  and the one kimi missed entirely: when claude runs a sweep, it should land *in Daniil's strip*,
  tagged and captioned with its `--say` reason, forkable. That is the difference between "the agent
  is a tool I command" and "the agent is a collaborator whose ideas I can remix."
- **E — the budgets are complementary, not competing.** Human cost is attention; agent cost is
  tokens. Improving either improves the other: the strip extends human memory *and* cuts agent
  token cost; better agent metrics mean fewer bad renders for the human to review.

And the infrastructure answer neither reached alone:

> **the Store/Ledger split, applied once, to render history.** The take strip is a VIEW of the
> ledger. `--diff-against` is a QUERY of the store. Structured metrics are a PROJECTION of a store
> entry. The feed is a LIVE VIEW of the ledger. One data model, four surfaces.

That is Akashic Aurora infrastructure *earned* rather than cargo-culted, and it is earned precisely
because the bench has two readers who need different projections of the same events.

---

## 3. The infrastructure question, consolidated (Daniil's explicit ask)

Both seats answered independently and **agree on every item they both addressed.**

**Transfers, earns its place:**
- **Store/Ledger split** — both, emphatically, and it is the spine of the plan below. kimi: "a
  design bench *absolutely* wants a ledger, because remix is navigation over history."
- **Write-once with supersession** — both. deepseek notes `_vfx_bench_write`'s merge-don't-clobber
  semantics rediscovered the notes pattern independently, "evidence that it is the right shape."
- **Typed ports / refuse-at-connect-time** — already borrowed by the graph; both say keep. It is
  what makes drag-drop safe for a non-programmer.
- **Names-that-lie / LEXICON discipline** — kimi extends it to pixels: *"a preview must know when
  it is lying."* That single sentence is the strongest transfer in either report.
- **The fidelity ladder** — a genuine split. kimi says NO (fleet machinery, one user has one
  attention) *except* the presence/feed pattern, which it says keep. deepseek says the feed's three
  levels (label / reason / image) already ARE a fidelity ladder built without the name. **They are
  agreeing:** the *ladder-as-rendering* transfers, the *ladder-as-interrupt-protocol* does not.

**Cargo-cult if imported — and saying so is the finding:**
- **recall / recall-at-action / knowledge map** — both no. kimi: the bench's memory is visual and
  spatial; importing recall builds a search box where a filmstrip is needed. deepseek: a shader
  lesson would need indexing by *effect* and *parameter range*, a different category system —
  "worth building, but not a simple transfer."
- **Bifrost lanes, dual-write, expectation registry, the full Redis stack, kill-window drills** —
  deepseek, with a comparison table. The render queue has exactly one consumer, at-most-once
  delivery, and a GPU-bound latency budget; the bus has many consumers, at-least-once, and a
  sub-100ms budget.
- **The lesson funnel** — kimi, with a distinction worth keeping: it does not apply to the bench,
  but it *does* apply to us building it. File lessons about what UI moves worked; do not surface a
  funnel to Daniil.

**On Daniil's specific question — is the render queue ignoring the message bus next door a missed
reuse?** deepseek: **correct separation.** "Conflating them would be like using Kafka for GPU job
scheduling: you can, but you would be working against the abstraction." One real cost is named: the
queue is in-memory, so a restart loses pending jobs — recoverable by backing it with the ledger,
which §5 slice 1 does anyway, for free.

---

## 4. What the evidence settled (two probes I ran for this synthesis)

Both reports asked for evidence rather than argument. I ran both.

### 4a. deepseek's metric probe — Proposal A is half-right, and blind on the axis that matters most

deepseek wrote `scripts/vfx_probe_metrics.py` to self-test its own Proposal A and could not run it
(its exec is read-only by design). I ran it. Two results.

**First: the probe could not read its own subject and said so confidently.** All ten images
returned "could not decode PNG". Cause: the hand-rolled decoder handles only PNG filter type 0, on
the stated assumption that "most PNGs use it". Every image here comes from `canvas.toDataURL`,
whose encoder picks a filter per row; all ten are type 2 (Up). It bailed on row zero of every file.
Pillow 11.3.0 and numpy 2.4.4 are installed — the decoder was never needed.

That failure is *itself* the finding, and it is deepseek's own named failure mode arriving
uninvited: **an instrument that could not read its subject produced a clean, uniform, confident
answer.** Ten identical errors look exactly like a result. It argues hard for shipping numbers
*next to* the picture, never instead of it.

I did not edit the file — deepseek holds the advisory lock and the lock is correct. I imported the
module and monkeypatched `load_png` only, so the metrics below are deepseek's code verbatim.

**Second, and more important — the metric set is structurally blind to hue.** The best available
test case is a natural experiment: three renders where shape, motion, frame and time were held
fixed and *only the palette changed*.

| render | contrast | variance | bloom % |
|---|---|---|---|
| look-geodesic-original | 0.8584041774010764 | 3.178 | 0.20319 |
| look-geodesic-neon-blue | 0.8584041774010764 | 2.890 | 0.20843 |
| look-geodesic-ident-edges | 0.8584041774010764 | 2.357 | 0.20862 |

Contrast is **identical to sixteen significant figures** across three visibly different images.
Bloom agrees to three decimals. The luminance histograms of the first two render identically. They
are genuinely different files (sha256 `e1609538` / `030c9b97` / `8ecd6085`) and genuinely different
colour — mean RGB `(93.7,110.4,121.0)` / `(86.0,113.1,135.5)` / `(100.7,109.1,124.0)`, mean chroma
51.1 / 49.5 / 41.8.

By deepseek's own criterion — *"if the numbers say 'no change' and the PNGs look different, the
metric is blind"* — contrast, bloom and the histogram are blind here. The root cause is not tuning:
**every metric in the set is luminance-derived** (Michelson on BT.601 luma, variance on luma, luma
histogram, luma-thresholded bloom, luma-thresholded delta). There is not one chroma metric in it.

That is not an edge case for this bench. The arc that produced these very images started with
Daniil saying *"I was actually quite fond of your initial blue neon design"* — a pure hue
judgement. The metric set would have scored the single most important visual question this bench
has faced as "no change", three times.

**Verdict: Proposal A survives, amended.** Spatial variance did separate the three (3.18 / 2.89 /
2.36) and is the one metric carrying signal; contrast 1.0 on `ingest-ringpulse` (bright rings on
near-black) is correct and useful. But the set needs a chroma axis before it is trustworthy, and it
must ship as *diagnostic* alongside the image, never as a gate in front of it.

### 4b. The storage audit — it dissolves the only disagreement rather than settling it

The one genuine disagreement: kimi wants presets/sketches/graphs/compositions collapsed into a
two-level model; deepseek says they are four different altitudes and the altitude is the
information. Both said an audit settles it. It does, in a direction neither predicted.

**On shape, deepseek is right — they are genuinely different:**

| store | fields | shape |
|---|---|---|
| `vfx-graphs.json` | `nodes`, `edges`, `seq` | a typed DAG (6 nodes, 4 edges) |
| `vfx-compositions.json` | `chain`, `source`, `state`, `identity` | a linear chain bound to an avatar state |
| `vfx-groups.json` | *(bare list)* | a named bundle of chunk names |
| `vfx-presets.json` | — | **empty** |

**On usage, both are answering the wrong question.** Every one of those files has **exactly one
commit in its entire history** — the commit that created it. `vfx-presets.json` is empty. Total
saved artefacts across the bench's whole life: **three**. And `groups["filmic finish"]` is
byte-identical to `compositions["aurora-plasma"].chain`, so even the three overlap.

Four save-surfaces. Three saves. Never written again after the commit that built them.

**This reframes the argument.** They were debating how to organise storage nobody uses. The reason
the bench has no memory is not that memory is badly organised — it is that **every one of these
surfaces requires naming a thing before you trust it**, which is exactly kimi's objection to
presets: *"commitment to a name before you trust the look."* The emptiness is the strongest possible
evidence for kimi's zero-cost, session-scoped, disposable keep — and it retires deepseek's
conclusion (preserve the altitudes) while confirming its premise (the shapes differ). There is no
usage to preserve.

---

## 5. The sliced plan

Ordered so each slice makes the next cheaper. Both seats independently said "take strip first";
the ledger goes under it because it is what makes the strip, the diff, the metrics and the feed one
thing instead of four. Each slice carries a pre-registered acceptance bar per the method baseline.

**S1 — the render ledger (foundation, no visible change).**
Every render — human click or agent CLI — appends an event `{id, ts, actor, subject, chain/graph,
params, say, result_path}` and its PNG becomes a store entry keyed by that id. Content-addressable
ids replace `--name` (deepseek's cut). The existing feed becomes a live view of this ledger rather
than a parallel structure.
*Acceptance, pre-registered:* a render triggered from the UI and one from the CLI produce
indistinguishable ledger entries; the feed renders from the ledger with no separate store; the
in-memory job queue can be lost and restarted without losing render history.

**S2 — the take strip (human view of the ledger).**
Filmstrip under the canvas. Keep on **chunk boundary** (deepseek's third answer, which beats both
of kimi's options: it captures *decisions*, not slider positions — and it is what makes takes
addressable by an agent), with idle-auto as fallback after 3 minutes of no boundary. Click to
travel. Each take carries a thumbnail so travel is instant and the state restore can lag.
*Acceptance:* a session of ten chunk swaps yields ten takes and zero slider-noise takes; clicking a
take restores the bench; the strip survives a page reload (it is a ledger view, and reload-safety
is already solved by `design/vfx-bench.json`).
*Guard against the §4b finding:* the keep gesture must cost nothing and require no name. If it asks
for a name, it will be used three times and abandoned, exactly like the four surfaces it replaces.

**S3 — split-take (comparison as a verb; serves both readers).**
Pin any take to one half; keep working in the other. Both live, one clock, draggable divider. The
same code path renders to a single PNG (two halves + divider + labels) for `render --mode split
--a take:4 --b current`, which is one image read for the agent.
*Acceptance:* a human A/B and an agent `--mode split` produce the same composited image; the FPS
watchdog is read, not the vibe, over a ten-minute run on this host (kimi's uncertainty §3 — two
live contexts may trip the documented TDR).

**S4 — structured output, with a chroma axis (agent view of the store).**
Metrics computed from the same pixel buffer the capture already reads. Ship **diagnostic, next to
the image, never as a gate** — §4a is the reason. Must include at least one chroma metric (mean
chroma and mean hue shift are enough to have caught the palette case); keep spatial variance, which
earned its place.
*Acceptance, pre-registered as a RED test:* the three `look-geodesic-*` renders must be separated by
the metric set. Today they are not. That is the bar, and it already fails — commit the failing pin
first.

**S5 — the probe verb.** `probe --compiles | --subject | --uniforms | --graph | --stale`. Read-only,
no GPU, no job queue. deepseek's cheapest/highest-leverage item; S1's ledger makes `--stale` real.
*Acceptance:* the agent can answer "did it compile" and "what is loaded" without enqueuing a render.

**S6 — palette by verb, and transition sprites with hash staleness.**
Group chunks by what they DO (kimi: the `note` field is already the right axis; the `cat` field is
the implementation axis). Tiles render *your composition + this chunk*, cached, carrying a hash of
the chain they were rendered against; when the chain changes they say **"re-render"** rather than
dimming (deepseek's sharpening — a dimmed tile still looks like a tile, and that is a name that
lies). Agent gets the same palette indexed by computational effect via `probe --chunks-by-effect`.
*Acceptance:* no tile ever shows a confident frame rendered against a different chain.

**S7 — the agent as co-creator in the strip.**
Agent renders land in the strip tagged `[claude]` with their `--say` as caption, forkable.
Consecutive agent takes sharing a `--say` prefix collapse into one expandable stack so a 12-frame
sweep does not evict Daniil's own takes.
*Acceptance:* a CLI sweep produces one tile, not twelve; Daniil can fork an agent take and the fork
is his.

**Explicitly NOT in the plan:** N live WebGL mini-windows. Both seats independently called it a trap
on this host, and kimi confirmed the TDR history is cited in-tree at `agent-avatar.js:21`,
`activity-line.js:108`, with an FPS watchdog at `:776`. S3 and S6 deliver what the ask was reaching
for using the one context that already exists.

---

## 6. Method note

Three fenced dual passes have now gone three-for-three in this project. What the fence bought here,
specifically: two independent rejections of the same framing is *evidence about the framing*, which
no amount of single-seat reasoning could have produced. And the flip bought the coupling — five
concrete couplings that neither seat could see from inside its own slice, including the one that
reframes the agent from tool to collaborator.

What it did not buy: neither seat could run anything. Both proposed evidence; both were blocked
(deepseek by read-only exec, correctly). **The synthesis had to run the probes**, and both probes
changed a conclusion — one falsified a metric set, one dissolved the only disagreement. Design
passes that end in "run this and we will know" need a seat that can run it, or the arc stops one
step short of the finding.

---

## 7. Open

- ~~kimi's flip is outstanding.~~ **It landed** (`vfx-studio-flip-kimi-2026-08-02.md`, adopted).
  See §8 — it changes three slices and adds one mechanism, and this section's prediction that "the
  coupling analysis is already covered by deepseek's" was wrong: kimi found a sixth.
- **The fleet defect is worth its own slice:** stale mail out-competes live directed asks;
  `UNATTENDED RECIPIENT` fires while runners are demonstrably working; the mailbox reports
  "unhandled" for work already delivered; runners launched without stdio redirection die silently
  with the launching shell.
- **Daniil has not chosen a palette** for the recovered original, and that decision is upstream of
  nothing here — the plan is palette-agnostic.

---

## 8. Amendment — kimi's flip (landed after §5 was written)

The flip attacked the agent side with the two probe findings in hand. Four kills, one new
mechanism, one new coupling. **The plan survives; three slices change.**

**KILL 3 → S4 is confirmed, and hardens.** kimi kills deepseek's Proposal E (perceptual metrics as
an attention *gate*) outright rather than amending it, on the distinction deepseek itself supplied:
*diagnostic* numbers inform, *evaluative* numbers gate. "A hue-blind diagnostic is a wrong note next
to a true picture. A hue-blind gate is a system that confidently discards the exact renders Daniil
cares most about." S4 already said diagnostic-never-a-gate, so it is ratified, not revised — but
`--force-view` is now explicitly **not** an acceptable mitigation, because the point of a gate is
that you trust it enough not to force it.

**MISS 2 → S4 gains a CANARY, and it is a ship-blocker.** deepseek's probe returned ten identical
confident "could not decode" errors and its author never noticed. kimi's rule: *any metric shipped
to the agent must carry a self-check that can fail loudly — if all N inputs return the identical
value or the identical error, refuse to report a trend.* Added to S4's acceptance bar: without the
canary, S4 does not ship.

  Note the convergence, because it is the strongest evidence in the arc for the cross-domain law:
  the same defect was independently found in three unrelated instruments this day — the PNG decoder,
  the metric suite, and recall itself (which returned 675 confident rows for a rule the corpus did
  not contain). It was fixed in recall the same day as a capped, flagged weak-match confession
  (commit 230c1de). **An instrument that cannot see its subject returns a confident answer, not
  silence** — and its mirror, which recall also hit: a filter strict enough to stop false confidence
  is strict enough to produce false silence.

**KILL 2 → S7 inverts its default.** deepseek's Proposal C wanted narration ON by default with
`--quiet` as the opt-out. From the human fence that is a noise generator aimed at the one attention
that does not renew. **The default is quiet; narration is on intent.** The agent distinguishes "this
render is for me" from "this render is for us". S7's collapse-stack stays, but it is a second line
of defence, not the mechanism.

**MISS 3 → a budget rule that governs every slice.** deepseek costed the loop in wall-clock and
tokens and never costed the third currency: *Daniil's attention per agent render.* The rule, adopted
into the plan as a standing constraint: **any proposal that lowers the cost of producing a render
without raising the bar for showing it to Daniil is a net negative.** S4 makes rendering cheaper;
S7 is therefore not optional alongside it.

**KILL 4 → multi-agent stays out, now for a measured reason.** deepseek proposed per-agent render
slots and then said in the next sentence that it would be premature. The storage audit settles it:
the problem that exists is one human not saving things, not two agents colliding. Deferred to a
one-line note — "when a second agent renders regularly, key bench state by agent ID."

**KILL 1 → do not optimise the early loop.** "The loop breaks on render 3" was narrative, not
measurement; deepseek's own table shows flat marginal cost per render. The real growth is in tokens
re-reading PNGs and in unverifiable hue judgements. Nothing in S1–S7 depended on it; recorded so a
future slice does not inherit it as fact.

**COUPLING F (new, and it raises S2's priority above everything else).** deepseek's complaint was
"a sample when it needs a gradient" and its fix was numeric metrics. But an ordered, addressable
sequence of states with thumbnails **is** a gradient in the agent's own terms — a discretised path
through parameter space it can reference by id instead of re-deriving by re-rendering. So the take
strip is simultaneously **the human's memory, the agent's diff vocabulary, and the agent's
gradient.** Three of the arc's findings collapse into one object, and the storage audit (three saves
in the bench's entire life) says it is the only storage gesture anyone will actually use.

**Net effect on the order:** unchanged, and reinforced. S1→S2 remains first, now with three
independent justifications instead of two.
