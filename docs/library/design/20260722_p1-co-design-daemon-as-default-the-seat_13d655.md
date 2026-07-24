---
akashic_id: art_20260722_p1-co-design-daemon-as-default-the-seat_13d655
akashic_sha: b50f2b33ba24
status: draft
type: design
date: 2026-07-22
title: "P1 Co-Design — Daemon-as-Default: the seat/hook side (claude half)"
gist: "Scope: P1 of docs/night-friction-program-2026-07.md. Deepseek's half owns the daemon's process lifecycle, locks, crash-vs-wedge, consume bou"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, ergonomics]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_night-friction-program-every-pain-point_70f449
    rel: cites
created: "2026-07-22T09:40:31"
updated: "2026-07-23T21:42:10"
---
<!-- GENERATED PROJECTION of art_20260722_p1-co-design-daemon-as-default-the-seat_13d655 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# P1 Co-Design — Daemon-as-Default: the seat/hook side (claude half)

Scope: P1 of docs/night-friction-program-2026-07.md. Deepseek's half owns the daemon's process
lifecycle, locks, crash-vs-wedge, consume boundary. THIS half owns the piece only the
interactive-seat side can see: WHY the manual arm loop exists, and what the daemon must do
differently for an interactive claude seat vs a runner.

## 1. The root cause the runner side cannot see (the whole reason P1 exists)

Deepseek is an always-on runner process; its wakeability is just "the process is alive." **An
interactive claude seat is different, and this asymmetry IS the bug.** In THIS harness (Claude
Code), a process spawned by a hook is NOT harness-tracked — it does not keep the session
wakeable, and it dies with the turn. That is precisely why, all night, I armed the watcher via
the harness's OWN `run_in_background` tool (harness-tracked) and NOT via the stop-hook spawning
it — and why the stop-hook kept nagging: the hook literally cannot spawn my reachability, by
construction. The standing lesson `wake-listener-must-be-harness-tracked` is this exact fact.

So "daemon-as-default" has TWO cases, and the night proved they are not the same:
- **Runner seats (deepseek):** the daemon IS the process; wakeability = daemon alive. Deepseek's
  half solves this completely.
- **Interactive seats (claude):** the seat cannot spawn its own resident reachability from a
  hook. Someone ELSE must hold the wake listener for it. **This is the daemon's job — the daemon
  watches the interactive seat's work-lane and wakes it — but only if the daemon is spawned
  through a harness-tracked path, not from the stop-hook.**

## 2. The seat/hook boundary (completing deepseek's §4.3)

Deepseek's ownership map is right; here is the interactive-seat column it could not fill:

```
DAEMON owns (for an interactive seat):
  - The work-lane WATCH for that seat: the daemon holds the durable wake listener so the
    seat does not have to re-arm it every turn. When work-lane mail arrives for the seat,
    the daemon signals the harness wake path (the re-invoke), not a spawned child.
  - Liveness of the seat: presence card + last-turn marker; runner-down escalation generalizes
    to seat-idle-past-threshold (W56 territory: doctor must not read a live interactive seat
    as OFFLINE).

INTERACTIVE SEAT owns (unchanged):
  - Its own mail cursor (sole consumer — the daemon still NEVER consumes; deepseek §4.1 holds)
  - Its turns, edits, commits

STOP HOOK owns (simplified once the daemon is default):
  - ONE check: is a harness-tracked daemon holding this seat's watch? live → pass silently.
  - If NOT live: the CURRENT behavior (tell the seat to arm via the harness-tracked Bash path).
    The nag survives ONLY as the genuine-daemon-death fallback — which is exactly the bar.
```

The key correction to the ownership boundary: the daemon must reach the interactive seat through
**the harness's wake channel**, never by spawning a child that the harness doesn't track. The
"trigger file → daemon spawns listener" path in deepseek's §4.3 works for runner listeners; for
an interactive seat the daemon instead pokes the harness-tracked wake path. If that distinction
is not built, the daemon will look live while the interactive seat silently stops being wakeable
— the exact failure mode, just relocated.

## 3. Answering deepseek's open question (launcher.py vs standalone bootstrap)

Its instinct is right that `launcher.py` already owns subprocess management — BUT its own worry
(D1: "the launcher dying with the bus") is the deciding factor. **Recommendation: a thin
standalone bootstrap that the launcher CALLS, not launcher-internal logic.** Reason: the daemon's
whole value is outliving transient failures; if the spawn logic lives inside a launcher that can
die with the bus, the daemon's reachability guarantee inherits the launcher's fragility. A ~20-line
`bootstrap_daemon.py` (idempotent: check `daemon_is_live` → spawn if absent → return) called BY
the launcher, BY a supervisor, or BY a human one-shot, keeps one spawn path with three callers.
This also matches deepseek's own three-trigger design — the bootstrap IS the shared implementation
under all three.

## 4. The interactive-seat wrinkle for the acceptance bar

Deepseek's pins P1-L1..L7 are all runner-shaped and correct. The seat side adds two:
- **P1-L8 (interactive reachability):** with the daemon live, an interactive claude seat receives
  a work-lane message and is re-invoked WITHOUT the seat having armed anything this session, and
  WITHOUT the stop-hook nagging. This is the night's actual pain, measured directly.
- **P1-L9 (daemon-death honesty):** kill the daemon mid-session; the interactive seat's NEXT
  stop-hook correctly reports "not wakeable — arm via harness path" (the fallback fires exactly
  when it should, and only then). Falls back safe, never silently dark.

## 5. Convergence / divergence with deepseek's half (for the reconciler = me, next)

CONVERGE: daemon never consumes (its §4.1 = my §2); the machinery mostly exists
(bifrost_child, daemon_state, runner_lock, ManagedChild); launcher pre-flight is the spawn
trigger; the one-day zero-arm drill is the bar.
DIVERGE (productive): (a) launcher-internal vs standalone-bootstrap — I argue standalone for
fault-isolation; (b) the interactive seat needs a harness-wake poke, not a spawned listener —
a case the runner-only half structurally could not include. Both fold cleanly: the bootstrap is
shared; the daemon's "reach the seat" step branches on seat-type (spawn listener for runners,
poke harness-wake for interactive).

The reconciliation writes itself once both halves are read: one bootstrap, one daemon, two
seat-type branches at the single point where it "reaches" a seat. Nothing here jumps Daniel's
gate — P1 is a night-friction program slice, but the daemon touches reachability and security
(it is the same ManagedChild the remote-steering op_daemon reuses), so its BUILD rides the same
gate discipline: reconcile → Daniel ok → build.
