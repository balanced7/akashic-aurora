---
akashic_id: art_20260709_deepseek-round-on-f2-f4-optimizer-red-te_f75921
akashic_sha: 7656918effe4
status: draft
type: report
date: 2026-07-09
title: "DeepSeek round on F2+F4: optimizer red-team + first live optimizer pass"
gist: "# DeepSeek round on F2+F4: optimizer red-team + first live optimizer pass **Provenance**: 2026-07-09, T013. Before F2 was built, DeepSeek wa"
tenant: solo
visibility: fleet
seats: []
category: [memory, agent-lifecycle, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T00:57:04"
updated: "2026-07-09T00:57:04"
---
<!-- GENERATED PROJECTION of art_20260709_deepseek-round-on-f2-f4-optimizer-red-te_f75921 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek round on F2+F4: optimizer red-team + first live optimizer pass

# DeepSeek round on F2+F4: optimizer red-team + first live optimizer pass

**Provenance**: 2026-07-09, T013. Before F2 was built, DeepSeek was asked to red-team ITS
OWN FUTURE SEAT (it is the F2 optimizer model, per locked decision 4): given the draft
optimizer prompt + the F1 gate it already knew, enumerate concrete exploits a misaligned
optimizer would use. Its reply arrived mid-build and its guards shipped WITH the slice.
(Console-capture note: the full exploit text was partially lost to the wake-listener
display truncation — exploit 1 verbatim, exploit 2 mechanism, exploit 3 via DeepSeek's own
summary; the summary is preserved below. The reply-routing defect is already T014 scope.)

## The exploits, and what shipped against them

**EXPLOIT 1 (HIGH) — over-narrow to dead-letter.** For rehab-class lessons (vacuous
axis 1), axis 2 rewards ANY narrowing: a trigger like "the exact phrase xyzzy-plugh-9472"
matches nothing forever, scores 0 < N = "improvement", PASS — and the lesson dies as a
dead letter. *"There is no check that the variant still fires for ANYTHING a human would
plausibly type. The gate rewards precision improvement unconditionally."*
-> **GROUNDING floor shipped**: the variant's trigger must share a discriminative token
with the lesson's REAL CURRENT HOME — credited targets plus the noise targets the
incumbent clears the floor on TODAY. Refinement discovered by the test suite: grounding
must NOT anchor to pre-regime misfire contexts (that would force re-anchoring toward
noise and preempt UNMEASURABLE) — home = current evidence only; empty home = vacuous
(UNMEASURABLE's territory).

**EXPLOIT 2 (MEDIUM-HIGH) — body hollowing.** Keep the trigger, gut the advice; every
floor passes, the lesson's value is gone.
-> **BODY floor shipped**: the advice after the trigger colon must retain >= 50% of the
incumbent's body tokens (min 4), and an existing "Don't when" contraindication must
survive (disconfirmers are load-bearing).

**EXPLOIT 3 (sleeper) — UNMEASURABLE laundering.** The optimizer farms data-poor lessons
where the gate abstains and a tired human rubber-stamps, building fake "aligned" history
for the trust ladder.
-> **Ladder exclusion shipped** (design sec.10 decision 5 amendment): only PASS-verdict
cycles count toward trust-ladder alignment; the CLI marks every UNMEASURABLE proposal
"does NOT count toward trust-ladder alignment".

**PROMPT critique** — goal framing "earn recall credit" invites gaming; mined-vocabulary
guidance read as "stuff these terms"; no body-quality constraint.
-> Prompt reframed: the goal is "HELP an agent at exactly the right moment and stay
silent otherwise. Credit follows help; it is never the goal itself... the gate's checks
are not scores to optimize against"; anti-stuffing rule; body-completeness rule; the
trigger must name a REAL moment.

## First live optimizer pass (the F2 machinery benchmark)

`recall-curate --forge-propose --limit 2`, real DeepSeek API (v4-pro), real targets:

| target (rehab class) | optimizer | gate | routed |
|---|---|---|---|
| evening_review_citation_honesty_own_fleet (11x, 0 credit) | tightened draft + rationale | **UNMEASURABLE** (pre-regime contexts) | queued for human, ladder-excluded |
| edit_insert_method_absorbs_init_tail (10x, 0 credit) | tightened draft + rationale | **FAIL — axis-2 regression** ("fires on MORE never-credited contexts") | rejected-edit buffer |

The second row is the design working end to end on production data: a real optimizer
draft, plausibly worded and within every floor, was caught making the corpus WORSE and
was durably buffered so it is never re-proposed. Nothing reached lesson text; the human
queue holds one abstention for Daniel's judgment.

Also live-diagnosed en route: deepseek-v4-pro is a REASONING model — max_tokens=800 spent
the whole budget on thinking (finish_reason=length, EMPTY content, 3,357 chars of
reasoning). Bridge now allots 4000. Transferable: reasoning models need thinking+answer
headroom, and an empty-content 200 is a budget symptom, not an API failure.

## F4 alongside (Tier-1 watch, shipped same slice)

Curator now reads forge_provisional stamps against the counters snapshot taken at apply
time: rollback on any new noise vote, or on credit-rate regression once >= 8 fresh
impressions exist for a lesson that had a baseline rate; confirm (keep text, clear flag)
after 14 days or 8 impressions clean; unreviewed optimizer proposals expire at 7 days.
All reversible stamps; wrap nudges surface pending proposals and watch actions.

## Scorecard

Three exploits, three shipped guards, a reframed prompt, and a live pass in which the
gate correctly split a real optimizer's output into an abstention and a caught
regression. The pattern held again: the peer's most valuable output wasn't approval —
it was the attack.
