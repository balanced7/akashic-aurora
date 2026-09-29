# Deck Craft Playbook — how to make a deck that teaches one reader and stays true

Status: current  (v1, 2026-09-28 — distilled from the Mail-and-Wake v2 run: 5 ground passes,
4 stances, 4 judges, per-slide build+verify; the judges' catches below are that run's receipts.)
Type: method · Arc: presentation-craft · Seats: any seat that builds a deck; claude conducts
Sibling: docs/presentation-primitives.md (the atom/template/token/target family; referenced, not
repeated). The format grammar (format/craft/layout/styles/diagrams/diagram-recipes.md) ships with
the slides artifact type; this playbook distils it and says WHY, it does not replace it.

**Daniel's ask, verbatim:** "I really want to understand this." and, after v1: "We can use this
research to make it easier for us to make that kind of quality."

**The thesis.** A report lists what is true; a presentation makes one reader hold one idea at a
time and feel why it matters. Quality here is not decoration — it is a fixed pipeline whose every
stage exists because skipping it produced a measurable defect in v1 or in one of the four v2
designs. The pipeline is a macro. Its parameters are the audience, the sources, the stances and
the judges; everything else is the same every time.

## 1. The shape: ground → design → judge → synthesize → build → verify → method

Each stage is one agent call or a fan-out; the stage's output is the next stage's input verbatim.

1. **GROUND (fan-out, 5 blind passes).** `craft` reads the six reference files and returns the
   rulebook with every number copied, not estimated. `content` opens the sources and returns an
   ARGUMENT MAP: every claim with its file:line or measured number. `analogies` returns a bank
   where each analogy states where it is exact and where it BREAKS. `narrative` returns the spine
   and a titles-only outline in one grammar. `substrate` measures what exists today (verbs, kits,
   render targets) so nothing proposed is later drawn as built.
   WHY five: one grounder mixes rules with claims and analogies leak into the argument map. Blind
   halves are the house verification grade (collaborative-means-iterative). WHY before design: a
   designer who has not seen the rulebook invents (v1: left-border cards, 1600px body text).
2. **DESIGN (fan-out, N stances, same ground).** Each stance is a forced bias: diagram-first,
   story-first, analogy-first, family-first. WHY stances rather than N free designs: free designs
   converge on the median; a stance makes each one commit to something the others will not, so
   the judges have real choices and synthesis has parts worth grafting.
3. **JUDGE (fan-out, one judge per value).** clarity (for THE reader), craft (against the rulebook,
   with arithmetic), accuracy (against the argument map and substrate), portability (against the
   primitive family). Each scores 1–10 and lists defects as `design-N:slide-id → claim → why`.
   WHY separate judges: the clearest design of this run (family-first, clarity 9) was the least
   accurate (6/10: a wrong mechanism claim on a teaching slide). One judge with four hats would
   have averaged that away. WHY judges state confidence: two designs arrived truncated and the
   judges said so and scored provisionally — an honest partial verdict beats a confident wrong one.
4. **SYNTHESIZE (one agent, two stages: PLAN then one SPEC per slide).** Take the winning
   direction, graft the named best slides from the runners-up, resolve EVERY accuracy defect
   (drop or correct; never keep an unsupported number; never draw a proposed verb or a designed-only
   target as existing). WHY two stages: a single synthesizer returning 22 slides of structured
   atoms hit the 64K output ceiling and nothing after it ran. Small responses pipeline per slide.
5. **BUILD (fan-out, one builder per slide).** Each builder receives the spec, the system (palette,
   fonts, type scale, template markup) and the accuracy judge's full text, and returns ONE
   `<section>`: the slides-html projection of that slide's atoms. WHY per slide: isolation — one
   bad slide cannot take the deck down, and the builder count is the slide count, so it saturates.
6. **VERIFY (one verifier per built slide).** Re-derives the geometry (budget sum, widths, node
   list, lint) and returns `{ok, issues, html}`; a failing slide is fixed or dropped, never squeezed.
7. **METHOD (this file + the family).** The run writes its own lessons down while the receipts are
   fresh. WHY: the house's rule that a method that lives only in a transcript is not a method.

## 2. The audience profile — write it before the rulebook is opened

One paragraph, verbatim where possible, stating: who (one person, not "stakeholders"); what they
already know natively (for Daniel: interrupts, polling, caches, registers, pipelines from the
hardware-analysis world; rhythm, count-ins, hits and rests from drumming); what they asked for in
their own words; the humour register (the joke and the truth are the same sentence, never forced);
what they value above polish (honesty about mistakes). This paragraph is a PARAMETER: it is pasted
into the ground, design and clarity-judge prompts unchanged.
WHY: analogies (§4), titles and the clarity judge ("for ONE reader") are all tested against it — a
deck for everyone moves no one. WHY verbatim: paraphrase drifts toward the writer's taste.

## 3. The accuracy discipline — argument map first, every slide cites, existing ≠ proposed

- **Argument map before any slide.** Every claim the deck will make, with a receipt: `file:line`,
  a measured number with its timestamp, or a quote with its speaker and file. A claim without a
  receipt is not in the map and therefore not in the deck.
- **Two readings of one fact are two numbers.** brief.md:28 measured Rill at 155 unsettled, oldest
  848h; v1's verbs slide, measured later the same night, says 157 and 857h. Both true. A slide
  uses ONE and its footer carries the time it was measured. Never average, never "about".
- **Line numbers rot within the session.** The task text said cmd_alias 9657; a grep at method time
  found 9660 (run 9688, kit 10239, flow 5805); the accuracy judge had already moved registry.py
  88-91 → 83 and agent_cli.py 9330 → 9333. Re-grep every cited line at BUILD time, not ground time.
- **Existing vs proposed is a visual token, not a caption.** Today: alias/run/kit/flow exist and
  ran tonight; reroute/owe/settle do not exist; present.slides-html exists as a page but the
  scene→page renderer is designed only (gen_deck.py is a hand projection). Design 1 drew
  "slides-html · EXISTS" with no caveat; Design 1 also listed `broadcast` as an existing verb with
  no census behind it. The family gives absent-vs-present its own token (§9) so a builder cannot
  blur it with "muted".
- **One incident per claim.** Design 1 mapped tonight's 8 operator chats onto half-navi.md:190,
  which describes the 09-23 incident (4 operator messages under ~1,383 standing). Same shape,
  different night, different numbers. The judge caught it because the map carried dates.
- **A pin is a pin of one kind.** "all VERIFIED, kata pins" was wrong: one was a session pin.
- **Say what you did not verify.** Every design ends with a not-verified list; the synthesizer
  keeps it as a footer or drops the claim.

## 4. Analogy testing — every analogy names where it breaks

Rule: an analogy enters the bank only with three lines — where it is exact, where it breaks, and
what false thing it would teach if the break were not said aloud. On a slide, the break is spoken
in the note or shown as the odd box; never left for the reader to discover.
Worked, kept: edge vs level trigger for arrival vs existence (half-heimdall.md:81-84 is the exact
half; break: a crash makes "unhandled" true again with NO arrival, so the wire has no edge — the
analogy is exact precisely because it breaks there). The drummer line the clarity judge named
best: "the hit is the edge, the ring is the level, the choke is the ack." Driver pattern for the
resolution: "on enable read the status register once; then sleep on the line; never spin on the
register" — with the on-slide honesty that the arm-time level check already exists (SEED rule,
wake_tiers.py:12-14).
Worked, rejected: "header, connection, driver" for the three planes. "Connection" does not mean
"what is owed" to anyone; a TCP connection tracks unacked bytes but nobody hears it as debt. The
judge swapped in "letter, books, desk". Test: say the analogy to the audience profile and ask what
they would infer — if the inference is false, the analogy is out, however elegant.

## 5. The titles-only outline test

Write every title before any slide, in ONE grammar (topic titles OR action phrases). Read only the
titles: they must tell the story. A title INTRODUCES the slide; it is not the punchline. Share the
list in chat before building. Claude-isms to strike: verdict titles, drama, fake tension ("It's
not X. It's Y."), faux-insight ("The magic moment"), and scaffolding in the title — Design 1
carried "[VERB 1/4]" and "Part V" inside headings; that is chrome, not content.
WHY: the outline is the cheapest place to find a missing beat or a doubled one; it is also the
first thing the narrative grounder returns, so the deck's spine is fixed before a pixel exists.

## 6. The rulebook, distilled — with the arithmetic

**Hard format (a violation drops the slide).** One `<section>` per slide, inline styles only, no
classes/`<style>` rules/`<script>`/`on*=`. Allowed tags: h1–h3, p, one-level ul/ol, br, div, img
(file beside the html), table/tr/th/td plain text, hr, x-shape, x-connector, x-icon (fixed name
list), svg (no `<text>`, no comments, size attrs = viewBox), x-embed (direct pinned child), one
`<aside>` LAST. Inline marks only b/i/u/a/span-with-color — v1 used `<b style="color:…">`, outside
the grammar. Units px or bare; `%` only where listed. font-size and font-weight NEVER inherit
into headings — set both on every one. Footer band: one pinned 24px row at `bottom:64px`, the
only thing allowed past y=952; that slide pads `128px 128px 160px`.

**Type scale.** 4–5 sizes, reused. Eyebrow 24–28 uppercase, letter-spacing 2–4. Headings are
statements. Body 28–32 in a column. Nothing under 24px anywhere (labels, cells, footers): "if it
only fits at 20px there is too much text". Big number 160–200 at line-height 1.

**Vertical budget arithmetic (824 inside 128 margins; 792 with a footer).** One line ≈ font-size ×
line-height. Two-line h2 at 64/1.1 ≈ 141; two-line h1 at 96/1.1 ≈ 210. Table row ≈ 2.1 × font per
line; a two-line cell counts twice. Card = lines × font × line-height + padding. Diagram slide =
64px title (~70) + 40 gap + 700 host = 810/824; with footer use 16 gap → 786/792. An h2 at 64/600
holds ~39 characters per line, so a 51-character title is TWO lines and 141 + 16 + 700 = 857 > 792:
shorten the title or drop the footer. Any squeeze (text shrinking toward 60%) is a bug: split.
Worked, caught by the craft judge: a 5-column 6-row 24px table whose columns wrapped 2/3/3/3/2/3
= 16 lines × 50 = 800, plus header 50, plus two-line h2 141, plus gap 32 ≈ 1023 of 792. Its receipt
column (326px) could not hold "half-heimdall.md:144-147" (24 chars × 0.6 × 24 = 346px) and its
status column (126px) could not hold "CONSTRAINT" (158px): mid-word breaks. The design's own
budget note said it fit. Do the arithmetic; do not trust the note.

**Width discipline.** Body sentences in 800–1000px (`width:960px` or `flex:1` beside something).
Word wrap only at spaces: a box is ≥ 0.6 × font-size per character of its longest word (+10% for
bold or caps) + padding. v1 ran body text at 1500–1640px on every content slide — wrong.

**Heading position.** Content slides top-aligned, no `justify-content:center`; the heading sits at
the same height on every content slide (v1 drifted 62/66px between neighbours). Spread the BODY
with `space-between` or a `flex:1` spacer. Centre only headingless statement/quote/closing slides.

**Backgrounds and effects.** Always set `background`. Dark for open and close, light for content,
the accent colour on ONE statement slide (the number to remember). Hairline borders one step off
the background; at most one soft shadow; most decks need no effect at all.

**One idea per slide.** Decide the FORM per slide — diagram, big number, quote, table, card row,
statement — and never a paragraph under a heading with nothing below. Visual-first is binding the
moment a deck has notes: the `<aside>` carries the script, the slide keeps the headline, the
figure, the diagram and the receipt. v1 had an aside on all 16 slides AND paragraphs on every one:
the script had leaked onto the slides. Design 1 put a 330-character paragraph inside a diagram
node ("a paragraph wearing a node"); Design 4's nodes carried 30-word sentences.

## 7. The AI-slop list (craft.md, verbatim in spirit; v1 receipts)

Gradient backgrounds used aggressively; emoji; containers with rounded corners AND a left-border
accent colour (v1 planes.html and build.html: `border-left:8px … border-radius:14px`, the exact
trope); Inter/Roboto/Arial/Fraunces; "data slop" — numbers, icons and stats that decorate rather
than carry; placeholder or padding content; three bullet slides where one statement would do. Add
from this run: bracket-tag scaffolding in titles; a table ABOUT pictures that do not exist (a
render-target matrix on a slide); six CLI flags crammed into a 320×200 node at 24px.

## 8. Diagram idioms — which, when, and the two-pass discipline

**Boxes first, in the file; lines second.** Pass 1: title + host + lanes + boxes + the node-list
comment (`<!-- A 0,0,320,120  B 448,0,320,120 … -->`), build. Pass 2: connectors and labels, every
coordinate READ off that list, build until no `note: layout:` lines. If you are computing
connector coordinates before the boxes exist, stop and write the boxes.
- **Flow chain / small tree** (straight chain, ≤2 branch levels, ≤4 leaves): flex column with
  32×24 `arrow-down` shapes or 32px flow connectors between steps. Never a stretched block arrow.
- **Rows recipe** (pinned): bigger trees, org charts, decision trees with >4 outcomes, brackets.
  Leaves set the columns (6 leaves: 240 wide at 0/285/570/854/1139/1424); parent→children is a
  BUS at B = C−24, never elbows between top and bottom edges. Design 1's slide 19 used exactly
  these numbers and passed the pre-save check untouched — recipes are cheaper than invention.
- **Pinned host** (`position:relative; width:1664px; height:700px`) for loops, crossings,
  swimlanes, two parents, maps: children in order boxes → connectors → labels, ≤24 pinned. Past
  24: pin to the section (+128 x, +240 y; +220 with a footer).
- **Swimlanes** for who-does-what across seats: 3 lanes 200 tall at tops 0/215/430; hand-offs stay
  in one column. The run's best 400px-survivor was 3 lanes × 3 nodes, zero edges: it restacks.
- **SVG curves** only when a line must curve; svg listed FIRST in the host so path numbers = box
  numbers; if you cannot name the box edge a path ends on, use a straight x-connector.
Connectors leave edge MIDPOINTS only; legs run in the row/column gaps; labels ≥8px clear of every
line and box; the lowest row ends below y=600 or it reads unfinished. The geometry IS the check.

## 9. Composing from the primitive family (see docs/presentation-primitives.md)

A slide names its TEMPLATE (cover, section, statement, content, diagram, comparison, closing)
and its ATOMS (headline, statement, quote, number, list, table, code, diagram, timeline,
comparison, note) as structured payloads placed into the template's named REGIONS, in logical
canvas units (1920×1080, 128px margins, 824 vertical budget). Text carries a ROLE (display, h1,
h2, body, caption), never a size; diagrams are geometry (nodes x/y/w/h, edges from/to/route/head),
never pictures; the note is a first-class atom. The spec IS the scene model; the builders are its
slides-html projection, exactly as core/coord/orient.py:6 renders one `orient.scene.v1` for CLI,
MCP and Discord and arsenal modules declare what they preserve and drop per port.
Rules the portability judge earned this run:
- **Absent vs present is its own token.** Design 4 overloaded `tone: muted` for both
  "de-emphasised" and "does not exist"; the family's most important semantic had no name.
- **Every edge ends on a node.** Pseudo-nodes (`bus-l`, `bus-r`) that are not in the node list
  force every other renderer to special-case them. A bus is a recipe, so declare it as one.
- **Duration follows the note.** Every slide sat at the 8 s video default while its note ran
  100–170 words (40–70 s). A note atom of N words implies a duration; a renderer that cannot hold
  it says so in `drops`.
- **Declare the fallback.** Waveform paths cannot survive a 400px panel (uniform scale 0.21 turns
  24px text into 5px). A target declares reflow or a fallback atom, or it declares that it drops.
- **A slide that needs an element the family lacks is a defect in the family.** Extend the family
  with a reason (Design 4 recorded `bars`, `comparison.side.tone`, lanes as extensions, each with
  its why); never hand-roll the element on one slide.

## 10. The pipeline is a macro — its parameters and the alias

Fixed: the seven stages, the schemas between them, the rulebook grounder, the verify step.
Parameters: `audience` (§2, verbatim), `sources` (the files that ARE the evidence base — nothing
outside them may be cited), `stances` (the design biases; four this run), `judges` (the values;
four this run), plus `slides` (a 14–22 band) and the render `target`. Tonight it ran as
scratchpad/wf2/check.mjs with those parameters in its header; the house's macro substrate is
`alias … mint` (agent_cli.py:9660), `run … --dry` (:9688), `kit` (:10239), `flow` (:5805), and
the belt refuses a step naming a verb that does not exist (core/toolbelt/registry.py:83-84,
"registry cannot mint capabilities"). The alias, once `present` verbs exist:

    alias claude mint present-deck \
      --step 'ground $1 --sources $2 --passes craft,content,analogies,narrative,substrate' \
      --step 'design $1 --stances diagram-first,story-first,analogy-first,family-first' \
      --step 'judge --judges clarity,craft,accuracy,portability' \
      --step 'synthesize --plan-then-slides' \
      --step 'present build --target slides-html' --step 'present verify' --step 'method' \
      --family CONSTRUCTORS --evidence INFER --tested-against <this run's receipt> \
      --why 'a deck of judged quality from one word, with --dry showing the plan first'

Today that mint is REFUSED at registry.py:83 because ground/design/judge/synthesize/present are
not agent_cli verbs. The refusal is the safety property: untested sugar confesses (agent_cli.py
:9333, `--evidence` defaults to GUESS). A kit `present` would carry this alias plus
`present-verify` and `present-method`; "recovery is a LOADOUT, not a memory" (core/toolbelt/
kit.py:49) applies to craft exactly as to recovery. Not verified: whether any `present.*` verb
has been started by the sibling stage; this file does not claim it.

## 11. What the judges caught this run — the short list, as a drill

| stage | catch | rule it became |
|---|---|---|
| clarity | "connection" as the obligation plane teaches something false | §4 analogy break test |
| clarity | six flags in a 320×200 node; a table about pictures that do not exist | §7 slop list |
| craft | 1023px of content in a 792px budget, self-reported as fitting | §6 do the arithmetic |
| craft | 51-char titles wrap; heading heights differ across slides | §6 39-char h2 rule |
| craft | paragraphs inside nodes; script on the slide | §6 visual-first |
| accuracy | `broadcast` drawn as existing; slides-html "EXISTS" without caveat | §3 existing ≠ proposed |
| accuracy | two incidents merged under one plane claim | §3 one incident per claim |
| accuracy | cited lines off by 3–5 in three files | §3 re-grep at build |
| portability | `muted` meaning both "dim" and "absent" | §9 absent token |
| portability | 8 s default under a 60 s note; no 400px fallback for waveforms | §9 duration, fallback |
| pipeline | one synthesizer hit the 64K ceiling; two designs reached judges truncated | §1 plan-then-slides; cap design length |

## 12. Pre-flight checklist (one pass per deck, then one per slide)

Deck: audience paragraph verbatim · sources listed and closed · argument map with receipts ·
analogy bank with breaks · titles-only outline in one grammar, shared · system fixed (palette by
role, ≤4 families, 4–5 sizes) · existing/proposed token defined · notes requested? then
visual-first is binding · every stage's output saved to a file before the next stage runs.
Slide: template + atoms named, no prose-describing-a-visual · background set · padding 128 (160
bottom with footer) · h2 at the same top, font-size and weight explicit, ≤39 chars or planned
two-line · body column 800–1000px · ≥24px everywhere · ≤3 div levels · vertical sum ≤824/792
written in the spec · no left-border+radius cards, no gradients, no emoji · tables: first-row
widths on every cell, one padded cell, rows counted, longest word fits · diagrams: node-list
comment, boxes → connectors → labels, edge midpoints, 8px label clearance, host used past y=600
· svg: no `<text>`, size attrs = viewBox, listed first · footer 24px at bottom:64 with the receipt
· `<aside>` last, the script not the bullets · title introduces, does not conclude · every number
traces to the map with its timestamp · proposed things drawn with the absent token · not-verified
list present · last build printed no `note: layout:` line.
