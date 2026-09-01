---
akashic_id: art_20260825_arc-content-and-survey-loop_b268f7
akashic_sha: e47bb071a944
schema_version: 1
status: current
type: report
arc: T382
date: 2026-08-25
title: arc-content-and-survey-loop
gist: "# ARC — The Adjudication Loop (content, survey, and calibration as one organ) Status: proposed Class: arc Owner: Daniil (direction) · Vandor"
visibility: fleet
body_type: markdown
seats: [claude]
category: [conducting, tooling, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-25T23:55:52"
updated: "2026-08-25T23:55:52"
---
<!-- GENERATED PROJECTION of art_20260825_arc-content-and-survey-loop_b268f7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# arc-content-and-survey-loop

# ARC — The Adjudication Loop (content, survey, and calibration as one organ)

Status: proposed
Class: arc
Owner: Daniil (direction) · Vandor (build)
Opened: 2026-08-26

## CHARTER (Daniil, verbatim)

"A loop where we generate and mine content from our work and from our surveys of recent news,
we could package state of the art analysis, learn about it and improve our tooling. I think
that would be a really helpful workflow."

And the target it serves, his words: "I do want to be an AI Agent Engineer or Integration
specialist and this house enables that kind of work."

## THE CLEVER PART, AND IT IS THE WHOLE ARC

**Do not summarise the news. ADJUDICATE it against the corpus.**

Every AI newsletter on earth summarises the field. That content is worthless because it is
undifferentiated -- an LLM with a search tool produces it in nine seconds and so does everyone
else's.

We hold something nobody else has: **1,120 documented failures with root causes, outcomes, and
dates.** So when a paper, tool or technique appears, we do not ask "what is it". We ask:

- Does our corpus already hold a lesson that CONFIRMS this? (we paid for it first, with receipts)
- Does our corpus REFUTE it? (we tried that and here is what broke, on this date)
- Does this OBSOLETE one of our lessons? (the field solved it; our workaround is now harmful)
- Does it SETTLE a forecast we registered? (score it, calibration accrues)

That is an analysis product no one else can make, because the fuel is the scar tissue and the
scar tissue took two years to accumulate. It is also the only version of this loop that makes
the ENGINEERING better rather than just making content.

## FOUR OUTPUTS FROM ONE PASS

Each cycle is one survey and four deliverables. This is the efficiency claim: the same read
pays four ways.

1. **CONTENT.** The delta between what the field claims and what our corpus measured. This is
   the Clarke & Dawe fuel -- the format works precisely because the comedy needs receipts, and
   the receipts are what we have. Deadpan explanation of a real absurdity, cited to a timestamp.
2. **LESSON STALENESS.** A lesson that says "X is hard, work around it" becomes ACTIVELY
   HARMFUL the day the field ships a fix for X. Recall will keep surfacing it and keep costing
   us the workaround. `core/recall/staleness.py` exists; the survey is the trigger it lacks.
   This is a garbage collector for the corpus and nobody else's news-reader does it.
3. **FORECAST SCORING.** We register predictions at gates already. The survey is what SETTLES
   them. `forecast score` + `--calibration` turns the loop into a dated, public, scored track
   record of calls about AI infrastructure.
4. **TOOLING ADOPTION.** What should we actually take? Filed as a wish or a defer with the
   evidence attached, not as a vague "we should look at X".

## THE META-LEVERAGE (why this beats a content calendar)

**A dated, scored, public track record of correct calls about agent infrastructure is exactly
the credential that gets an AI Agent Engineer hired.** It is verifiable, it is rare, and it
cannot be faked by someone who started last month. Most candidates assert judgement; this
produces evidence of it.

So the content and the career target are the same artifact, not two projects competing for the
same evenings. And per the IP assessment (2026-08-26), every published episode is also a dated
DEFENSIVE PUBLICATION -- it establishes prior art and blocks anyone patenting what we built.
Three strategies, one output.

## COMPOSE, DO NOT BUILD -- the organs already exist

Checked 2026-08-26 before designing, per the house rule that cost us a rebuild once already:

- `agent_cli.py scout` -- pre-flight survey worn by a RESIDENT role, role memory shared across
  wearers. The survey half already exists and already accumulates.
- `agent_cli.py sift` -- the nested ask: evidence -> hat fan -> curator pairs -> DISSENT FIRST.
  Run the adjudication through this and the analysis carries built-in disagreement instead of
  being one agent's confident summary.
- `agent_cli.py forecast register|score|list --calibration` -- the full registry with scoring.
- `agent_cli.py recall` / `recall-at` -- the corpus side of the adjudication.
- `research:web:*` lesson prefix -- web findings already land as first-class lessons.
- `ask_gemini_web` / `ask_gemini_panel` -- the fan for the survey itself.

**Nothing new is required to run cycle one.** What is missing is the WIRING and the cadence,
not the parts.

## THE CYCLE (one pass)

    1. SURVEY    scout/ask_gemini_panel over the week's agent-infra news -> research:web: lessons
    2. ADJUDICATE  for each finding: recall the corpus. confirms / refutes / obsoletes / settles?
                   run through sift so dissent surfaces before the verdict
    3. SETTLE    forecast score on anything the week decided; register new ones at the same gate
    4. RETIRE    flag obsoleted lessons for staleness review (never auto-delete -- propose)
    5. DRAFT     the content artifact from the DELTA, not from the summary
    6. FILE      tooling adoptions as wishes/defers with evidence refs

## SEQUENCING (deliberately small first)

The failure mode here is building the pipeline instead of making the thing. So:

- **Cycle 1 is manual and produces ONE written piece.** Prove the delta is interesting before
  automating the machine that finds it.
- **Cycle 2 adds the Clarke & Dawe pilot** -- one segment, from real session numbers, no toolkit.
- **The toolkit is built only after the format proves out**, and it is built ON the house so
  every episode is simultaneously marketing, a capability demo, and a regression test.

## PINS (pre-registered, so this cannot quietly become a content calendar)

- P1: a cycle that produces zero corpus-adjudicated claims is a FAILED cycle, not a quiet one.
  Summary without adjudication is the thing we are explicitly not building.
- P2: every content claim cites a lesson id or a measured number. No unreceipted assertions.
- P3: staleness proposals are PROPOSED, never auto-applied. The corpus is append-only and a
  retirement is a ratified act.
- P4: forecasts registered in a cycle must have a `--dies-when`, or they are unfalsifiable and
  do not count toward calibration.

## OPEN, FOR DANIIL

- Cadence: weekly feels right (matches the Forest Walks ritual); it must not become a chore.
- Publication channel per the strategy read: one flagship written piece first, YouTube long-form
  for depth, TikTok/Shorts for the sketches -- knowing they serve different funnels.
- Does the loop run autonomously and present a draft, or does it wait to be invoked?
