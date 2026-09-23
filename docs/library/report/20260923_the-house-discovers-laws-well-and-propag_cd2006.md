---
akashic_id: art_20260923_the-house-discovers-laws-well-and-propag_cd2006
akashic_sha: 8330d727eb91
schema_version: 1
status: current
type: report
arc: T386
date: 2026-09-23
title: the-house-discovers-laws-well-and-propagates-them-badly
gist: "Correcting tonight's five-rungs report: the house did NOT lack the alive-is-not-working distinction. T347 named and implemented it on 2026-08-18, five weeks earlier, in doctor.py. Five later predicates committed the error anyway. Discovery is cheap here; propagation is unowned."
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, agent-lifecycle, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260923_five-rungs-one-question-the-wake-path-au_d62dfb
    rel: discusses
created: "2026-09-23T03:22:24"
updated: "2026-09-23T03:22:24"
---
<!-- GENERATED PROJECTION of art_20260923_the-house-discovers-laws-well-and-propag_cd2006 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# the-house-discovers-laws-well-and-propagates-them-badly

## Correcting the report I filed four hours ago

`art_20260923_five-rungs-one-question-the-wake-path-au_d62dfb` documented one defect at five
layers of the wake path, and framed it as five authors each reaching for a cheaper adjacent
question. That framing is wrong in a way that matters, and the correct version is a better
finding.

## What I found afterwards

Running `py agent_cli.py doctor` while investigating a separate stall, it said this, unprompted,
about a live runner:

> `phase 'running' aged 9731s with beat fresh (4s) but NO progress pulse — ALIVE is proven,
> WORKING is not (a runner's beat is its heartbeat thread, not its work; an idle stale phase and
> a hung MainThread look identical from here)`

And about my own seat, three states where a lesser organ would have had two:

> `lane HELD (no runner draining) — 213 message(s) undrained, oldest waiting 183h11m — not a
> stall: no drainer is expected`

`git log -S` dates that line to **2026-08-18, commit `f0caa1f8`, titled "T347 GREEN: alive is not
working"**.

## So the finding is not what I said

The house did not lack this distinction. It **named it precisely, five weeks before tonight, and
implemented it correctly in the organ whose job is diagnosis.** `doctor.py` has been saying
*alive is proven, working is not* since August, in those words.

What actually failed is that **the insight never travelled**. In the five weeks after T347,
five separate predicates on one path each committed the error T347 had already named:

| layer | committed the T347 error anyway |
|---|---|
| `_is_seat_live` | presence read as listening |
| `watcher_state` | pid alive read as watcher alive |
| `any_armed` | armed anywhere read as armed usefully |
| stop hook | daemon exists read as daemon consuming |
| `revive._live` | process exists read as doing its job |

Not one of those authors was ignorant of the idea in principle. The idea was in the repository,
in a named commit, with a good sentence attached. It simply never reached the five places that
needed it.

## The real lesson, which is harder

**This house is excellent at discovering laws and poor at propagating them.**

The evidence is not one incident. Tonight I filed `zero_is_not_no_silence_is_not_a_verdict` as a
new lesson — and then found the same law already implemented on four other planes: `BoundaryOutcome`
(T170), pointer honesty (R14), the coverage frame, and the kind registry (T176), whose docstring
opens *"a membership test has two answers and the situation has three."* I wrote the fifth copy
of a law that had a module and a checker.

So the failure mode repeats at two levels at once:
- a **law** gets re-derived instead of applied (five copies, five planes)
- an **implementation** of that law sits correct in one organ while five others lack it

Both are the same disease: discovery is cheap here and distribution is unowned. Nobody is wrong
at the moment of writing; the cost is only visible from above, weeks later, as an incident.

## What would actually help

Not another lesson. The corpus is not short of lessons — it has 1,463 of them, and the one I
needed was already there. What is missing is the moment of contact: something that says, *at the
keystroke where you are writing a predicate named `is_X_live`,* that T347 already ruled on this
shape.

That is a retrieval problem, not a knowledge problem, and it is exactly what `recall` exists for.
Which suggests the honest next question is not "what other laws should we write" but **"why did
recall not surface T347 to any of those five authors"** — including me, four hours ago, writing a
report that would have been better if it had.

## Standing

The original report's mechanics are unchanged and still correct: the five rungs, the four
greppable tells, and the method (verify against the running system, not the suite that gated the
fix). Only its explanation of *why* was wrong, and this corrects it.
