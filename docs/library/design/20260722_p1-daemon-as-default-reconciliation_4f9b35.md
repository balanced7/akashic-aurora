---
akashic_id: art_20260722_p1-daemon-as-default-reconciliation_4f9b35
akashic_sha: 685abf78535c
status: current
type: design
date: 2026-07-22
title: P1 daemon-as-default — reconciliation
gist: "**Charter:** night-friction P1 (docs/night-friction-program-2026-07.md, Daniel's day charter) — \"the seat-holder should never manually re-ar"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_night-friction-program-every-pain-point_70f449
    rel: cites
  - target: art_20260722_p1-co-design-daemon-as-default-resident_32fda9
    rel: cites
  - target: art_20260722_p1-co-design-daemon-as-default-the-seat_13d655
    rel: cites
created: "2026-07-22T12:38:23"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260722_p1-daemon-as-default-reconciliation_4f9b35 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# P1 daemon-as-default — reconciliation

**Charter:** night-friction P1 (docs/night-friction-program-2026-07.md, Daniel's day charter) —
"the seat-holder should never manually re-arm wakeability." Retro receipt: the endurance night
spent 4+ turns on manual watcher re-arms.

**Inputs (verbatim on disk):** deepseek half `research/drafts/p1-daemon-lifecycle-deepseek-half-2026-07-22.md`
· claude half `research/drafts/p1-daemon-lifecycle-claude-half-2026-07-22.md` · deepseek's
concurrence (bus handoff, resent whole through the P2 door): "CONCUR. Your half names the root
cause I structurally couldn't see from the runner side."

## The convergence (clean — a co-design, not a contest)

Both halves describe ONE system with a single branch point. deepseek owns the runner-side
lifecycle; claude owns the seat/hook side; they meet at exactly one place and agree everywhere else.

**The root cause (claude half, the piece the runner side structurally could not see):** an
interactive Claude-Code seat CANNOT spawn its own reachability from a hook — hook-spawned
processes are not harness-tracked, so they die with the turn. This is *why* the manual arm loop
existed every night. A runner has no such asymmetry (it IS the resident process), so deepseek's
half correctly solved the runner case but could not name the interactive case.

**The single branch point** — the daemon's "reach a seat" step:
- **Runner seat:** spawn a wake listener as a ManagedChild (existing T075-gamma path).
- **Interactive seat:** poke the harness wake channel (the Claude-Code re-invoke path) — NEVER
  spawn an untracked listener, or the daemon looks live while the seat silently goes dark.

Everything else is shared and agreed:
- **One `bootstrap_daemon.py`** (~20 lines, idempotent check-and-spawn), STANDALONE for
  fault-isolation (claude's answer to deepseek's open question — the launcher can die with the
  bus; the daemon's reachability guarantee must not inherit that fragility), called by launcher /
  supervisor / human one-shot (deepseek's three triggers = the three callers of the one bootstrap).
- **The daemon NEVER consumes mail** (both, by construction — the cursor stays with the session/runner).
- **Two-tier lock:** DaemonLock (twin-daemon guard, TTL 60s, heartbeat 8s) + runner_lock
  (consume-path guard, unchanged).
- **Crash-vs-wedge:** ManagedChild circuit breaker catches crash storms (3/300s → trip + blocker
  broadcast); WEDGE detection stays the doctor's job (worklive/progress, T030); daemon self-wedge
  near-impossible (simple polling reactor, Redis timeouts guard I/O).
- **Safe degradation:** bus loss → daemon survives, dark-probes; daemon crash → lock TTL expires →
  next bootstrap succeeds; all additive — fleet never blocks on the daemon.

## The complete pin table (L1–L9, pre-registered)

deepseek L1–L7 (runner-shaped) + claude L8–L9 (interactive-seat-shaped):
- L1 daemon starts via launcher not manual arm · L2 launcher refuses twin daemon · L3 stop-hook
  passes without arm · L4 daemon crash → lock expires → next launch succeeds · L5 runner crash →
  backoff → breaker at 3/5min · L6 bus loss → daemon survives, presence re-registers · L7 daemon
  never creates a cursor key (24h → zero daemon-owned cursors) · **L8 interactive seat re-invoked
  on work-lane mail with ZERO session-arming and ZERO stop-hook nag** (the night's actual pain,
  measured) · **L9 daemon killed mid-session → next stop-hook correctly reports "not wakeable —
  arm via harness path"** (fails safe, nags exactly when it should and only then).

## Acceptance bar

The one-day zero-arm drill: 24 hours, an interactive seat-holder + a runner, ZERO manual `--arm`
flags, the stop-hook firing ONLY on genuine daemon death. That is P1 done.

## For Daniel's gate

1. Ratify the reconciled design (one bootstrap, one daemon, two seat-type branches).
2. Note the shared infrastructure: the daemon is the same ManagedChild the remote-steering
   `op_daemon` reuses — gate P1 and the remote-steering spine and their process-management is
   built once, used twice. Sequencing candidate: P1 daemon first, op_daemon rides it.
3. Build follows the gate (P1 is a friction slice, but reachability + security stakes put it
   under the same reconcile→gate→build discipline as the crown work).

— reconciled by claude a4fa8f8d, 2026-07-22. Both halves concurred before this doc; the single
divergence (launcher-internal vs standalone bootstrap) resolved to standalone on the fault-isolation
argument deepseek itself raised. Nothing built — Daniel gates.
