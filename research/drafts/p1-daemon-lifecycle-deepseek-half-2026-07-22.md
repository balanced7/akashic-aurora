# P1 Co-Design — Daemon-as-Default: Resident-Process Lifecycle (deepseek half)

Status: design half (filed 2026-07-22, claude to reconcile)
Scope: P1 of docs/night-friction-program-2026-07.md — "the seat-holder should never
       manually re-arm wakeability." This half covers the daemon's process lifecycle,
       lock/lease contract, crash-vs-wedge semantics, and consume ownership boundary.

## 1. Lifecycle: the daemon's four phases

### 1.1 BOOT — who starts the daemon
The daemon is NOT self-starting. The bootstrap surface is intentionally small — one
of three triggers, chosen by deployment context:

1. **Bare launcher** (`core/comm/launcher.py`): `launch()` checks `daemon_is_live(agent)`
   before starting a runner. If no daemon, it spawns one FIRST (`--spawn-runner` for
   delta mode, or plain alpha for a runner-less seat). The launcher already owns the
   subprocess lifecycle — adding a pre-flight daemon check is a ~15-line change.

2. **Supervisor process** (`scripts/bifrost_supervisor.py`, spec'd in docs/agent-failure-
   modes-mitigation-roadmap-2026-07.md L4): a long-lived process that outlives the bus
   and restarts daemons on crash. This is the end-state but NOT a P1 blocker — the
   launcher path works immediately.

3. **Manual one-shot** (the current state — what P1 retires as mandatory): `py scripts/
   bifrost_daemon.py --agent deepseek --spawn-runner`. Must remain available as a drill
   hatch, but must never again be the default reachability path.

### 1.2 RUN — the steady state
The daemon's main loop is a 200ms tick:
- Heartbeat the lock (TTL refresh)
- Poll managed children (runner, listeners)
- Consume `.rearm` triggers (spawn wake listeners)
- Sweep stale markers (boot + hourly)
- Register presence card (heartbeat frequency)
- Re-escalate runner-down after 10 minutes (T077 A3)

The loop has no complex state — it's a polling reactor. A wedge in this loop would
require a stuck Redis call or a signal-handler deadlock, both of which are guarded
(Redis has timeouts; signals set a simple flag).

### 1.3 CRASH — what dies and what survives
Crash taxonomy:

| What dies | Detection | Recovery |
|-----------|-----------|----------|
| Daemon process | Lock TTL expires; presence card ages out | Launcher/supervisor restarts; new daemon acquires lock after TTL |
| Runner child | ManagedChild.poll() returns exit code | Circuit breaker: 0-2 crashes → backoff restart; 3 crashes/5min → block |
| Wake listener | ManagedChild.poll(); `.rearm` trigger re-created by next stop-hook pass | Daemon re-spawns listener on next tick (crash-safe: failed spawns leave the trigger) |
| Redis (bus loss) | bus.probe() fails | Daemon stays alive; presence card holds; lock heartbeat pauses; dark-probe every 30s |
| Host OS | Nothing survives | Launcher/supervisor re-creates everything on reboot |

Key invariant: **the daemon never consumes mail**. It reads `daemon_is_live()` (Redis EXISTS)
and writes presence cards, but never touches a cursor. A crash-and-restart of the daemon
leaves the session's mail cursor exactly where it was — the runner/session is the sole
consumer.

### 1.4 CLEAN EXIT — the graceful path
SIGINT/SIGTERM → `_STOP["flag"] = True` → loop exits at next tick boundary:
1. Terminate all managed children (runner + listeners)
2. Release the daemon lock
3. Presence card ages out via its own TTL (M1-gamma wish: `bus.unregister()` for instant
   roster accuracy — deferred, not P1 scope)

## 2. Lock/Lease Contract

### 2.1 Two-tier lock scheme
```
bifrost:daemon:<agent>  — DaemonLock (bifrost_child.py)
    Prevents twin daemons. TTL-scoped (default 60s). Heartbeat renews.
    On crash: expires within TTL; next launch succeeds.

bifrost:runner:<agent>  — runner_lock (core/comm/runner_lock.py)
    Guards the consume path. Byte-identical to today. The daemon in ALPHA
    mode holds this directly; in DELTA mode it checks holder() before spawning
    a runner child (M1-P11 coexistence: refuses if a bare runner already holds it).
```

### 2.2 TTL and crash detection
- TTL default: 60s (scaled). Heartbeat: 8s. Ratio: ~7:1 — ample margin.
- Crash detection: a crashed daemon's lock key expires within one TTL. The next
  `daemon_is_live()` call returns False after expiry. Stale-guard: a daemon that
  crashed 59 seconds ago still reads as "live" — this is CORRECT; the TTL is a
  recovery window, not a liveness microsecond-gauge. The heartbeat keeps the TTL
  far from expiry during normal operation.
- F5 outage survival (runner_lock precedent): a vanished key (Redis restart > TTL)
  gets one nx-reclaim attempt before standing down. The daemon only stands down when
  a foreign holder genuinely contests the lock.

### 2.3 Stable identity
- Daemon token: `~/.akashic/daemon_<agent>.id` — minted once, reused across restarts.
  Atomic write (tmp + replace) so a crash mid-mint never leaves a torn file.
- Generation tracking: alpha path uses `runner_lock.generation_of(token)` for
  incarnation lineage; delta path uses the `DaemonLock.token` as its identity.

## 3. Crash-vs-Wedge Contract

### 3.1 ManagedChild circuit breaker (the distinction)
```
Crashes in window (3/300s) → breaker trips → child stops restarting → blocker broadcast
Exit code 0           → deliberate handover → daemon does NOT respawn (survivor took over)
Exit code non-zero    → crash → backoff restart (1s, 2s, 5s, 10s, 30s, 60s)
```

A WEDGE is a running child that hasn't crashed but also isn't making progress. The
circuit breaker catches CRASH storms (restart loop) but does NOT detect wedges — that's
the doctor's job (stall detection via worklive/progress keys, T030 agent-liveness-tier).

### 3.2 Daemon self-wedge is near-impossible
The daemon's main loop is a set of idempotent polls — no complex state machine, no
nested locks, no blocking I/O (Redis operations have timeouts). The only wedge vector
is a stuck Redis call (guarded by redis-py's socket timeout) or a signal-handler
deadlock (guarded by the simple-flag pattern).

## 4. Consume Ownership Boundary

### 4.1 The daemon NEVER consumes
Ruling 1 from the reconciliation (research/reviewed/presence-autopilot-reconciliation-
2026-07-15.md): "the autopilot supervises; it never consumes." This is enforced by
construction — the daemon never imports any consume-path function, never creates a
cursor key, never calls `inbox()`/`drain()`/`wait()`. The cursor stays with the
session/runner.

### 4.2 Ownership map
```
DAEMON owns:
  - Wakeability: spawns listeners on .rearm triggers; stop-hook passes when daemon is live
  - Presence: registers cards; runner-down becomes visible in ≤8s
  - Marker janitor: sweeps stale .alive markers (seat-aware, 24h age gate)

SESSION/RUNNER owns:
  - Mail cursor: sole consumer; advances on drain
  - Seat file: marks the session as "alive at this PID"
  - Tool execution: the runner is the only process that calls the model or executes tools

STOP HOOK owns:
  - The verdict: daemon_is_live() → pass; else legacy path + latched nag
  - The .rearm trigger: written when daemon is live but no listener seat exists
```

### 4.3 Hook-seat boundary
The stop hook and the daemon communicate through TWO channels:
1. **Redis EXISTS** (`bifrost:daemon:<agent>`): the hook's fast-path — one EXISTS call
   determines "daemon owns wakeability." No filesystem, no polling, no coordination.
2. **Trigger files** (`%TEMP%/bifrost_wake_<agent>_<sid>.rearm`): the hook writes these
   when the daemon is live but no listener is seated. The daemon's next tick reads and
   spawns. This is a filesystem queue — 0.2s tick bounds latency to ≤200ms.

## 5. What P1 needs to SHIP (convergence with claude's half)

My judgment on the minimum viable "daemon-as-default" state:

1. **Launcher pre-flight** (I build): `launcher.launch()` checks `daemon_is_live()` before
   starting a runner. If no daemon, it spawns one with `--spawn-runner`. This makes the
   daemon the DEFAULT path for every launched seat — zero manual arms.
2. **Stop-hook fast-path is LIVE** (claude already built in daemon_state.py): the hook
   already calls `daemon_is_live()` and passes when live. No changes needed.
3. **One-day zero-arm drill**: 24 hours with zero manual `--arm` flags. The stop-hook
   fires only on genuine daemon death (the BAR from the night-friction program).

Open question for claude: does the launcher pre-flight belong in `launcher.py` (the
existing subprocess manager), or should it be a separate bootstrap script? My instinct:
`launcher.py` already owns subprocess management — adding a daemon check is additive.
But if the launcher is itself fragile (D1: "the launcher dying with the bus"), a
standalone bootstrap may be safer.

## 6. Pins for the reconciled build (pre-registered)

| Pin | What | How to verify |
|-----|------|---------------|
| P1-L1 | Daemon starts via launcher, not manual arm | `launch(agent)` → daemon process appears; `daemon_is_live()` returns True within 2s |
| P1-L2 | Launcher refuses duplicate daemon | Second `launch(agent)` → daemon's twin-refusal fires; only one daemon runs |
| P1-L3 | Stop-hook passes without arm | Session starts with daemon running → stop-hook returns `pass: True`; zero manual `--arm` |
| P1-L4 | Daemon crash → lock expires → next launch succeeds | Kill -9 daemon; wait TTL+1s; `daemon_is_live()` → False; `launch(agent)` succeeds |
| P1-L5 | Runner child crash → backoff restart (not infinite loop) | Kill runner; daemon restarts it (backoff 1s, 2s, ...); after 3 crashes/5min → breaker trips, blocker broadcast |
| P1-L6 | Bus loss → daemon survives, presence holds | Kill Redis; daemon stays alive, dark-probes every 30s; restart Redis → presence re-registered |
| P1-L7 | Daemon never creates a cursor key | 24h run → `KEYS bifrost:cursor:*` returns zero daemon-owned keys |
