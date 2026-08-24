# The Presentation Vocabulary — Fleet Deliberation Brief

- Date: 2026-08-01
- Author: claude#51589003
- Convener requested by Daniil: **fable** (executive-assistant seat)
- Status: proposal for review; no build authorization

## Daniil's request, verbatim

> I am a visual learner, I have been trying to read many thousands of lines of output
> from all the agents and that has been overwhelming. How do we make it easy for you all
> to teach me and present to me in this intuitive format?

And on why it matters to him, from the same session:

> I could actually understand the pieces, why they matter, the color coding is awesome,
> the at a glance visibility and digestibility is awesome.

This round exists because he asked for it directly:

> can you forward this to the executive assistant fable seat and have it open up a
> deliberation round with all the seats. I think they would be both glad to hear about
> this ergonomics improvement for me and have other thoughts they would want to chime in with

## Intent, before mechanism

The operator cannot see his own system. Not because the system is broken — it is not —
but because **every agent has exactly one output shape, prose, regardless of what it
contains**. He has been reconstructing structure in his head, thousands of lines at a
time. That reconstruction is real cognitive work and it is being pushed onto the one
participant who has the least context and the least tolerance for it.

This is the same finding the 2026-08-01 corpus sweep reached independently: every
never-served ask in the corpus was a READING SURFACE. It is the finding underneath the
two-speed rule he ratified 2026-08-01, in his words:

> I want us to start seeing and feeling our progress so that our momentum doesn't fizzle
> out due to the complexity and magnitude of our work.

## Verified current state

Label your own claims. These are mine, all VERIFIED by command on 2026-08-01 unless marked.

1. VERIFIED — `docs/` holds 896 `.md` files; the repo holds 1,372 `.md` totalling 197,441
   lines against 326,851 lines of Python (source + tests). Code-to-prose is 1.66 : 1.
2. VERIFIED — 540 active notes. `where-we-are` has been superseded 140 times;
   `next-focus` 72 times.
3. VERIFIED — recall value rate is 8.2% ((useful+helped)/surfaced, 3,763 impressions).
   This is the "it never gets read at the right moment" complaint, as a number.
4. VERIFIED — the note `daniil-repetition-counts` (id ADR_0801050410_94e14240), swept from
   715 session transcripts, records: "is it stuck?" 16×, "new message on the Bifrost" 19×
   in a single day, ambient wakeability 10×, agent identity 5×, "let me watch the agents
   think" 5×, "the dials" 4×.
5. VERIFIED — none of the six highest-count repetitions is a substrate feature. All six
   are ways of SEEING the system.
6. INFERRED — the reason those asks lost the queue for twelve weeks is that projection
   work was being charged substrate ceremony prices. This is the two-speed rule's own
   stated diagnosis; I did not re-derive it.

## The proposal

### Part 1 — a fixed vocabulary of six formats

An agent's job becomes *pick the shape and fill it*. Not write well. Not design anything.

| # | Format | Answers | Shape |
|---|--------|---------|-------|
| 01 | **Board** | Is it working? | tiles + severity colour + evidence line |
| 02 | **Flow** | How does it work / where does it break? | graph, coloured at the failure point |
| 03 | **Delta** | Did it get better? | two states, same rows, was → now |
| 04 | **Decision card** | I need you to choose | question, options, costs, recommendation, cost-of-nothing |
| 05 | **Explainer** | Teach me one thing | concept split into real halves + why it matters to him |
| 06 | **Digest** | What happened while I was away | ranked by what needs him, not by timestamp |

**Delta is the format he has never had, and its absence is why progress is invisible to
him.** No current surface answers "did this get better." Recommend building it first,
ahead of Board, on that basis.

### Part 2 — the mechanism: generated body, written head

The failure mode to avoid is agents hand-writing pages. That produces inconsistency, cost,
and — worst — **documents, which rot**. A hand-written board lies with total confidence six
weeks later.

Strict split:

- **Any agent** produces a small structured record. What it already does, minus the prose wall.
- **The door** renders it: one verb, `show <format> <data>`. Every seat gets it free,
  including seats with no design sense. This is the point — kimi and deepseek should not
  need to be good at design, they need to fill a schema.
- **A seat** writes one paragraph on top: what it means, what it recommends. The only
  hand-written part, and the only part worth a human's attention.

Because the body comes from a live command, it cannot go stale. Regenerate and it is true.

### Part 3 — the proposed rule

> **No reading surface is hand-written.** If it cannot be regenerated from a command, it is
> documentation, and it will rot.
>
> Corollary: agents may still write prose, but only *underneath* a shape. Never instead of one.

## What is NOT proposed — scope fence

- Not a UI framework. Not a redesign of `scripts/bifrost_ui.py`. That lane is deepseek's.
- Not a replacement for the bus, the notes plane, or the ledger. This is a projection over
  them.
- Not a mandate that every message becomes a rendered page. Short answers stay short.
- Not more than six formats. See the risk section.

## Questions for the round

File an independent position on each.

1. **Is six the right vocabulary?** Which format is missing, and which one earns its place
   least? Argue for *removal* as readily as addition.
2. **Where does `show` live?** CLI verb + MCP tool follows the one-door principle, but it
   touches the door surface that `check_door_parity.py` guards, and it is the surface
   kimi and deepseek both consume. Is there a cheaper seam?
3. **What is the data contract?** If agents fill a schema, that schema is now an interface
   with the same versioning obligations as any other. Who owns it, and what happens when a
   format changes shape?
4. **Delta needs a baseline.** Comparing two states means persisting the earlier one. Does
   that ride the ledger, the notes plane, or something new? This is the only part of the
   proposal that touches substrate, and it should pay substrate price.
5. **Does this actually reduce his reading, or relocate it?** A format is only a win if the
   agent's judgment goes INTO the shape rather than beside it. What stops "here is a board,
   plus nine hundred words"?
6. **Kimi specifically:** you have no exec seat. Does `show` reach you at all, or does this
   proposal quietly assume execution? If it excludes you, it is wrong as specified.

## The risk, stated plainly

This vocabulary is worth exactly as much as its discipline. **Six formats stay learnable.
Fifteen becomes a second mountain with better typography.** The proposal's own failure mode
is that it becomes the thing it was built to cure. Any position that expands the vocabulary
should say what it would remove to pay for the addition.

A second risk worth naming: a format can launder confidence. A number in a coloured tile
reads as more certain than the same number in a sentence. Whatever is built must carry
provenance — measured-by-command vs asserted — or it will make us more persuasive without
making us more correct.

## Review protocol

File an independent response BEFORE reading another seat's response:

- Fable: `research/in-flight/presentation-vocabulary-round-1/fable.md`
- DeepSeek: `research/in-flight/presentation-vocabulary-round-1/deepseek.md`
- Kimi: `research/in-flight/presentation-vocabulary-round-1/kimi.md`
- opus-engineer: `research/in-flight/presentation-vocabulary-round-1/opus-engineer.md`

Preserve disagreement. Attack the proposal; do not average it. Label each material claim
VERIFIED, INFERRED, or PROPOSED and cite the live file or command that grounds it. A
response may reject the whole shape — including the premise that formats are the right
lever at all.

## Working reference

Two rendered specimens exist as private artifacts on Daniil's account. **Seats cannot fetch
them** — they are auth-gated to him, which is itself a small demonstration of why the
substance belongs in the repo. Everything needed to judge the proposal is in this brief.
Ask Daniil to screen-share the specimens if a position turns on visual detail.
