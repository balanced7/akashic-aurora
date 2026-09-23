---
akashic_id: art_20260923_five-rungs-one-question-the-wake-path-au_d62dfb
akashic_sha: 9cc2f30208ca
schema_version: 1
status: current
type: report
arc: T386
date: 2026-09-23
title: five-rungs-one-question-the-wake-path-audit
gist: "One defect at five layers of the wake path: every rung answered a cheaper question than the one it gated. Found by four unread operator messages; four of the five were caught by verifying against the live system rather than the green suite."
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-23T03:15:31"
updated: "2026-09-23T03:15:31"
---
<!-- GENERATED PROJECTION of art_20260923_five-rungs-one-question-the-wake-path-au_d62dfb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# five-rungs-one-question-the-wake-path-audit

## The incident

Between 2026-09-17 and 2026-09-23 the operator sent four directed messages over Discord to the
`claude` seat. Two sat unread for five days. Two more, sent while a session was actively
working, were never seen at all. He eventually asked whether his answer had gone to the wrong
window, then whether the seat was reliably reachable, and then sent a single sad face.

Nothing in the transport failed. Every message was delivered, durably, to a seat that was LIVE
and beating the entire time. Every component reported success.

## The finding

Chasing it to the bottom found **one defect at five separate layers of one path**. Each layer
answered a cheaper question than the one it was gating, each was individually defensible, and
the errors composed rather than cancelled.

| layer | asked | needed to ask |
|---|---|---|
| `_is_seat_live` (Discord) | is a worklive entry LIVE | will this be **read** |
| `watcher_state` | is the pid alive | is a **watcher** alive |
| `any_armed` | is anything armed for this agent | is anything armed **for a living session** |
| stop hook | does a daemon own wakeability | is that daemon **consuming** what I leave it |
| `revive._live` | does a daemon **process** exist | is the daemon **doing its job** |

The failure never appears at any single rung. It appears only end to end, as silence.

## Why each one was reasonable

This is the part worth keeping, because "someone was careless" would be the wrong lesson and
would predict nothing.

A proxy predicate is **cheap to write, cheap to check, and almost right**. "Is a seat live" is
one Redis read; "will this message be read" requires knowing about watchers, sessions, daemons
and trigger consumption. Every author took the cheap adjacent question, and every author was
correct *about that question*. `_is_seat_live` never once lied about worklive state.

The composition is what kills. Each layer trusts the layer below to have asked the real
question. `_auto_wake` reads a True from `_is_seat_live` as *"the lane plus its armed wake
listener ARE the wake"* — an assumption about a layer it cannot see. When that assumption
silently fails, the honest cold-seat notice is never posted, and the operator receives silence
indistinguishable from being ignored.

## The tells, for next time

Four patterns repeated, and all four are greppable:

1. **A name containing `is_X_live` or `_exists` where the caller needs `will_X_act`.** The name
   is the defect. Fixing the body while keeping the name leaves the trap armed.
2. **A pid check with no command-line verification.** A filed lesson already said file presence
   proves nothing; pids are reused, and `watcher_state` returned `armed` for a pid that happened
   to be alive.
3. **An aggregate over an identity where the caller needs a specific instance.** `any_armed`
   answers for the *agent*; the wake reaches a *session*. One stray drill watcher made a wholly
   unreachable agent read as reachable.
4. **A supervisor checking for a PROCESS when it means a FUNCTION.** The rung whose entire job
   is noticing was itself the last to notice.

## The method that actually found them

Not the test suite. **Every one of these passed its tests**, including the first fix, which
shipped green and was proved wrong twenty minutes later by running it against the live system:

```
presence LIVE : True      any_armed : armed      REACHABLE : True
```

Three true statements and a false conclusion. The armed seat belonged to a session that no
longer existed.

So: **verify a fix against the running system, not against the suite that gated it.** A green
suite proves the code does what its author thought; only the live system says whether the author
was asking the right question. Four of the five were found this way, and two of those were found
by a fix I had already committed and believed.

## What changed

Five commits closed the five rungs, each RED-pinned before its mechanism:

- `f591f2f5` — presence → reachability on the Discord path, predicate renamed (the old name was
  the defect)
- `6d4cce6e` — reachability requires a session that still exists
- `60d826c1` — a watcher that checks the bus once and never again cannot report an outage that
  begins mid-shift; a quiet watch and a dead watch must never print the same sentence
- `ca294b8a` — wake tiers, so the operator cannot be starved by fleet volume
- `eb16da4a` — the reviver can tell a wedged daemon from a working one

A sixth thing did not change: the operator override in `bifrost_wake.py` was **correct the
entire time**. It names the operator by default and outranks the kind allowlist. It was never
consulted, because nothing was awake to consult it. The mechanism was never missing; the thing
that would have asked it was.

## The generalisation

This is the same law the house has now derived on six planes — `BoundaryOutcome` (T170), pointer
honesty (R14), the coverage frame, the kind registry (T176), `zero_is_not_no`, and now this.
Stated for this plane:

> **When a predicate gates a decision, write the decision as a sentence and check that the
> predicate answers THAT sentence, not a neighbouring one.**

And the corollary that makes it actionable rather than wise: the neighbouring question is always
the cheaper one, which is why it wins on every rung unless someone checks.
