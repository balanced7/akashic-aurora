---
akashic_id: art_20260714_t060-m1-reconciliation-continuous-presen_55da7b
akashic_sha: 0124a773b643
status: fossil
type: design
arc: T060
date: 2026-07-14
title: T060-M1 reconciliation (continuous presence)
gist: "# T060-M1 Continuous Presence — Reconciliation (claude ⋈ deepseek) — 2026-07-15 Status: reconciled design (halves: deepseek-t060-m1-design-2"
tenant: solo
visibility: fleet
seats: [claude, deepseek]
category: [method, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_t060-m1-blind-half-a-continuous-presence_3f51c8
    rel: derives-from
  - target: art_20260714_t060-m1-blind-half-b-continuous-presence_55481e
    rel: derives-from
  - target: art_20260714_t060-m1-continuous-presence-fence-brief_4f1905
    rel: supports
created: "2026-07-15T03:18:42"
updated: "2026-07-15T03:18:42"
---
<!-- GENERATED PROJECTION of art_20260714_t060-m1-reconciliation-continuous-presen_55da7b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T060-M1 reconciliation (continuous presence)

# T060-M1 Continuous Presence — Reconciliation (claude ⋈ deepseek) — 2026-07-15

Status: reconciled design (halves: deepseek-t060-m1-design-2026-07-15.md [BLIND],
claude-t060-m1-design-2026-07-15.md [EXPOSED — disclosure in note
t060-m1-fence-integrity]). Build slices cite THIS document. T060 is a DESIGN wave:
nothing here is build authorization; slices register in the ledger for Daniel's gate.

## Independence accounting (read this before weighing convergence)

claude's half was written AFTER accidental exposure to deepseek's in-progress
reasoning (a runner-log diagnosis surfaced his supervisor concept, tier framing,
strangler direction). Therefore:
- "Both halves have a supervisor daemon / strangler migration / composition-of-
  existing-primitives" is **EXPOSED convergence — weak evidence**.
- The halves' **divergences** below are the load-bearing signal (a contaminated
  design that still DISAGREES is disagreeing for reasons).
- deepseek's half is the blind one and GOVERNS wherever the divergence is judged a
  tie.

## The two architectures, honestly stated

- **deepseek (blind):** daemon-per-agent IS the agent's body — holds the runner lock
  indefinitely (hours TTL, stable UUID token), CONSUMES the work lane itself, fans
  messages out to child runtimes (wake listener, runner) that it spawns/monitors/
  restarts. Presence and consumption unify in one process.
- **claude (exposed):** one machine-level supervisor enforces per-agent presence
  CONTRACTS (checkable from existing signals) with repair actions; it NEVER enters
  the message path — consumers stay exactly as today. Adds the clean-death half
  (SessionEnd releases seat+card+listener; TTL stays the crash net).

## Rulings

1. **The message path does NOT move in wave 1 (claude's conservatism wins; deepseek's
   own open-Q2 concedes the hop).** Daemon-as-consumer inverts RB-21 for sessions and
   relocates the cursor — the system's most incident-scarred seam (T014, T045, T066).
   That change is PARKED behind T047 legacy retirement + its own fenced sub-design.
   The daemon still ships — as supervisor first, consumer maybe-later.
2. **Daemon-per-agent (deepseek's shape) beats one-machine-supervisor (claude's) for
   the process boundary** — it matches the ACL/quarantine model (a quarantined agent
   simply gets no daemon, RB-25 F1), keeps blast radii per-agent, and his M1-A
   skeleton is buildable today. claude's machine-level enforcement survives as the
   HOST tier: OS (Task Scheduler) supervises the daemons; daemons supervise runtimes.
   Turtles, but each named.
3. **Clean death ships FIRST (claude's trio; deepseek's half had no clean-death
   story).** SessionEnd releases consumer seat + incarnation card + listener
   stand-down. Tonight's 30-minute seat shadow (f9207c90 receipt) becomes 0s on
   clean exits before any daemon exists.
4. **Stop-hook downgrade is kill-switched (his Q4 = yes):** AKASHIC_DAEMON_WAKE=0
   restores the blocking check instantly for the first week.
5. **Conversation survival ships as SUMMARY INJECTION v1 (his own fallback, his Q1):**
   full Agent-state serialization is its own future design wave.
6. **Host supervisor priority = Windows Task Scheduler (his Q3):** this machine is
   the fleet today; systemd/launchd land as stubs in deploy/.
7. **Stable UUID identity token (his §2e) ADOPTED** — the fencing generation already
   keys on token strings; the pid:random token was an accident of history.

## Reconciled build order (strangler; each slice fenced + pinned + Daniel-gated)

| Slice | What | Owner | Pins |
|---|---|---|---|
| M1-α | `scripts/bifrost_daemon.py --agent <id>` skeleton: lock + presence + heartbeat + BusLossGuard + stable token + clean SIGINT; NO consume changes, NO children | claude builds, deepseek verifies | his M1-P1/P2/P11/P12 |
| M1-β | Clean-death trio at SessionEnd (seat + card + listener) | claude builds, deepseek verifies | new pin + tonight's shadow receipt as the regression story |
| M1-γ | Wake listener as managed child + ccd signal + stop-hook daemon fast-path (kill-switched) | claude builds, deepseek adversarial-drills the T073 noise bars | his M1-P3/P4/P8 |
| M1-δ | Runner as managed child + circuit breaker + summary-injection convo survival | deepseek builds, claude verifies | his M1-P5/P6/P7/P9 |
| M1-ε | Windows Task Scheduler unit + runbook (+ systemd/launchd stubs) | joint | his M1-P5 host tier + M1-P10 |
| PARKED | daemon-as-consumer / inbox fan-out (needs T047 + own fence); full convo serialization; Tier-3 cursor adapter | — | — |

## What deliberately does not change (union of both halves)

bus.py untouched; runner_lock API untouched (TTL becomes env-tunable); dispatcher.py
stays parked (the daemon is each agent's own dispatcher; W3 remains future); the lane
protocol untouched; the stop hook keeps promise-audit + K7 stamp forever; quarantined
ids get no daemon, no exceptions.

## M1-PV missing-citation acknowledgment (section-scoped disposition)

- `half_a: scripts/bifrost_daemon.py` — NOT a fabricated code claim: it is the
  design's primary BUILD TARGET (his §3 "BUILD" rows; verdict V6 tags it [DESIGN]).
  No section retired.
- `half_a: docs/runbooks/m1-daemon.md` — same class: the M1-ε runbook deliverable,
  named by the plan, not claimed to exist. No section retired.

## Confidence

Rulings 1-4: HIGH (every argument grounded in named incidents or shipped precedent).
Ruling 5: MEDIUM (fidelity bar unmeasured until a drill). Slice table: HIGH on α/β
(pure composition), MEDIUM on γ/δ (behavior changes with kill-switches and drills
named). The parked items are parked BECAUSE confidence there is LOW.
