# Presence Autopilot — Design (blind half, deepseek) — 2026-07-15

Status: blind half (claude writes his in parallel; reconciliation follows).
Daniel directive: "make arm/claim/stand-down disappear as manual chores."

## 1. The Problem, Precisely Stated

Every agent in the fleet has a lifecycle that today requires HUMAN attention at
multiple points. The pieces exist — lock, listener, stop-hook, incarnation card,
daemon skeleton — but nothing CONNECTS them into a self-managing whole. The
result is a steady drip of operator toil:

| Chore | Frequency today | Root cause |
|-------|----------------|------------|
| Re-arm wake listener | ~15x/day (claude) | Listener exits on wake/deadline; harness re-invokes agent but does NOT re-arm; stop-hook blocks turn-end demanding re-arm |
| Stop-hook nag at turn-end | 6+ blocked turn-ends/day | wake_armed() returns False during the 1-2s seat-write race window; 1.5s grace recheck catches some but not all; the hook blocks the session |
| Marker litter | ~180 stale .alive files in tempdir | `touch_activity` writes markers forever; nothing reads most of them; nothing cleans them |
| Runner-down invisible | 6h outage unnoticed today | No status surface exists for runner liveness; presence card shows daemon but no runtime health |
| Redelivery mountain | 562 echoes today | Cursor-skip surgery needed because nothing detected the echo storm or paused consumption |

The pieces that COULD solve these already exist in tree:
- `DaemonLock` + `ManagedChild` (M1-delta, shipped today)
- `runner_lock` with TTL + heartbeat
- `wake_seat.janitor` (cleans DEAD-pid seats, K7/K8 safe)
- `incarnation.read_cards` (agent-level liveness snapshot)
- `bus.broadcast("blocker", ...)` (M1-delta circuit breaker, kind in WAKE_WORTHY_KINDS)

The gap is INTEGRATION: no single process owns the agent's full runtime lifecycle
end-to-end. The daemon skeleton exists but manages nothing. The stop-hook is a
one-shot subprocess with no memory. The listener is harness-spawned and
harness-forgotten.

## 2. The Autopilot: One Design, Four Responsibilities

The daemon (already the agent's continuous-presence body per M1-alpha) becomes
the AUTOPILOT: it owns EVERY runtime decision for its agent. The operator says
"start the daemon" — once. After that, arm/claim/stand-down are daemon-internal.

Four responsibilities:

### 2a. Runtime Ownership (listener + runner as ManagedChildren)

The daemon spawns BOTH the wake listener AND the runner as ManagedChild instances
(M1-delta already ships the runner path; M1-gamma adds the listener). When either
exits:

- **Exit 0 (benign — wake, stand-down, handover):** The daemon does NOT respawn
  (N1, already in ManagedChild). A listener that woke the agent STAYS down until
  the stop-hook (or the daemon's self-check) re-arms it. A runner that stood down
  stays down. This is deliberate: respawn-on-benign creates churn loops.
- **Exit ≠ 0 (crash):** Backoff restart per ManagedChild policy. Circuit breaker
  trips after 3 crashes in 5 minutes → `bus.broadcast("blocker", ...)` →
  daemon keeps presence, stops restarting.

The daemon reads both children's status into its presence card:
```
card["runtimes"] = {"runner": "live" | "down" | "blocked",
                     "listener": "live" | "down" | "blocked"}
```

This is read-only information — surfaced by `read_cards()` and rendered in
the whisper's SIBLINGS line and the doctor. **Runner-down becomes visible the
moment the daemon's next heartbeat refreshes (≤8s), not when a human notices
silence.**

### 2b. Bootstrap Ordering (who arms what when no daemon runs)

The strangler's hardest question: the daemon replaces manual arming, but
SOMETHING must arm the listener BEFORE the daemon is adopted. The answer is
TWO boot paths, not one:

**Path A — Daemon is LIVE** (checked via `DaemonLock` key existence):
- Stop-hook: `daemon_is_live(agent)` → True → **return instantly.** The daemon
  owns wakeability. No `wake_armed()` check, no 1.5s grace, no 25s loop guard.
  The stop-hook becomes: (1) promise audit, (2) K7 activity stamp, (3) done.
- Listener: spawned by daemon as ManagedChild. On wake-worthy mail, the daemon
  signals the session via ccd channel (`mcp__ccd_session_mgmt__send_message` —
  T073 Phase 5, already addressable). The daemon KNOWS which session the listener
  serves because the listener's seat file is `bifrost_wake_<agent>_<session>.pid`
  and the daemon spawned it with that session id.
- Re-arm after wake: the stop-hook, now fast-path, STILL detects "listener is
  down" and tells the daemon to re-arm. How? A one-line trigger file:
  `bifrost_wake_<agent>_<session>.rearm` — the daemon's main loop polls for
  `.rearm` files and spawns a fresh listener. The stop-hook writes the trigger
  (one `open().write()` — no subprocess, no wait). The daemon picks it up on
  its next tick (≤0.2s).

**Path B — Daemon is DOWN** (no `bifrost:daemon:<agent>` key):
- Stop-hook: falls through to the LEGACY path — `wake_armed()` check with
  1.5s grace + 25s loop guard. Same as today.
- Stop-hook ALSO prints: `[stop-hook] daemon not running — start it: py scripts/bifrost_daemon.py --agent claude` — once per session (latched).
- The listener is spawned by the harness (existing `run_in_background` path).
- When the daemon EVENTUALLY starts, it ADOPTS any harness-spawned listener by
  reading its PID from the seat file and wrapping it in a ManagedChild (PID-only
  monitoring — the daemon didn't spawn it, so it can't capture stdout; but it
  CAN poll the PID and restart on crash).

This two-path design means:
- **No daemon → today's behavior, plus a one-time nag to start the daemon.**
- **Daemon live → zero stop-hook blocks, zero manual re-arms.**
- **Migration is organic:** the operator starts the daemon when tired of the nag.
  The nag is ONCE per session, not every turn-end.

### 2c. Marker Janitor (the 180 stale .alive files)

The daemon, at startup and once per hour, walks tempdir and removes `.alive`
markers older than `wake_seat.fresh_minutes()` (default 30min, same K7 threshold
the seat janitor trusts). This is NOT a new mechanism — it's the EXISTING
`wake_seat.janitor` logic applied to markers instead of seats:

```
for name in os.listdir(tempdir):
    if name.startswith(f"bifrost_wake_{agent}_") and name.endswith(".alive"):
        age = now - os.path.getmtime(path)
        if age > fresh_minutes * 60:
            os.remove(path)  # stale marker → gone
```

The session-start janitor already cleans DEAD-pid seats. The daemon's periodic
sweep cleans stale markers. Together: tempdir stays clean without operator
attention. One sweep per hour costs one `listdir` — ~0.1ms for 200 files.

**Why the daemon, not the session-start hook?** The session-start hook fires
per-session and only sees its OWN agent's markers. The daemon is always-on and
sees ALL markers for its agent. Also: markers are per-agent, not per-session
(they're `bifrost_wake_<agent>_<sid>.alive`, but the daemon cleans only its
own agent's prefix — no cross-agent leakage).

### 2d. Stop-Hook Elimination (not removal — transformation)

The stop-hook today does THREE things. Under autopilot, each transforms:

| Today | Autopilot (daemon live) | Autopilot (daemon down) |
|-------|------------------------|------------------------|
| Wake check: `wake_armed()` + 1.5s grace + 25s loop guard + demand re-arm | **Gone.** One `daemon_is_live()` check (Redis GET, sub-ms) → return. Daemon owns wakeability. | Same as today (legacy path) + one-time nag to start daemon |
| Promise audit: `_promise_block()` | Unchanged — this is a content-quality gate, not a liveness concern | Unchanged |
| K7 activity stamp: `_touch_activity()` | Unchanged — the cheap liveness signal | Unchanged |
| Re-arm trigger: spawn new listener | **Gone.** Write `.rearm` trigger file; daemon picks it up | Same as today (harness spawns) |

The stop-hook is NOT removed. It keeps the promise audit (which catches a
different class of problem) and the K7 stamp (which feeds the incarnation
card's liveness signal). The only thing that disappears is the BLOCKING
wake-armed check and the manual listener re-arm.

**The nag is self-limiting:** once the daemon is started, the nag stops
forever. The operator's incentive is clear — start the daemon once, never
think about wakeability again.

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  bifrost_daemon.py                       │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ presence │  │ autopilot    │  │ marker janitor    │  │
│  │ (lock+hb)│  │ loop (0.2s)  │  │ (hourly sweep)    │  │
│  └──────────┘  └──────┬───────┘  └───────────────────┘  │
│                       │                                  │
│     ┌─────────────────┼──────────────────┐              │
│     │                 │                  │              │
│     ▼                 ▼                  ▼              │
│  ┌────────┐    ┌────────────┐    ┌──────────────┐      │
│  │ runner │    │ listener   │    │ .rearm poll  │      │
│  │ child  │    │ child      │    │ (trigger     │      │
│  │(delta) │    │ (gamma)    │    │  files from  │      │
│  └────────┘    └─────┬──────┘    │  stop-hook)  │      │
│                      │          └──────────────┘      │
│              ┌───────┴────────┐                        │
│              │ ccd channel    │                        │
│              │ (wake signal)  │                        │
│              └───────┬────────┘                        │
└──────────────────────┼─────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │ harness session │
              │ (Claude Code)   │
              │ stop-hook:      │
              │  daemon live?   │
              │   yes → return  │
              │   no  → legacy  │
              └─────────────────┘
```

## 4. Key Design Decisions

### 4a. The daemon does NOT consume the work lane (ruling 1 stands)

The daemon's autopilot loop polls: (a) ManagedChild status, (b) `.rearm` trigger
files, (c) marker sweep timer. It never touches the cursor. The runner child
consumes the work lane exactly as today. The listener child watches for
wake-worthy mail exactly as today. The daemon is the SUPERVISOR, not the worker.

### 4b. The ccd channel is the wake signal, not a replacement listener

When the daemon's listener child detects wake-worthy mail, the daemon signals
the session via ccd channel. The session's existing wake path handles the rest.
The listener child EXITS (the wake IS the delivery), and the daemon sees the
benign exit and does NOT respawn (N1). The next stop-hook firing writes the
`.rearm` trigger, and the daemon spawns a fresh listener.

This preserves the existing wake path byte-for-byte: the harness sees "background
task finished" and re-invokes Claude exactly as today. The only change is WHO
spawned the background task — daemon instead of harness.

### 4c. .rearm trigger files are the control surface, not a new bus message

Why a file and not a bus message? The stop-hook is a one-shot subprocess. Sending
a bus message requires Redis connectivity and bus initialization — ~200ms of
imports. Writing a file is one `open().write()` — ~0.1ms. The daemon polls for
`.rearm` files every tick (0.2s), so the latency is bounded at 0.2s. The file
IS the message; the filesystem IS the queue. Simple, crash-safe (a stale
`.rearm` file from a dead session is cleaned by the daemon's marker sweep).

### 4d. The daemon's presence card IS the status surface

No new bus messages, no new Redis keys, no new dashboard. The daemon's existing
presence card (already `bus.register(card=...)`) gains one field:
```
card["runtimes"] = {"runner": "live", "listener": "down"}
```

`read_cards("claude")` already returns this card. The whisper's SIBLINGS line
already renders cards. The doctor already reads cards. The status surface
exists — we just put runtime health ON it.

### 4e. No new daemon-to-daemon protocol

Each daemon manages ONE agent. Daemons don't coordinate. The bus roster
(`bus.register`) already lists every agent's presence. No new discovery
mechanism. If an agent's runner is down, its own daemon knows and reports it
on its own card. Other agents see it on the roster. No cross-daemon chatter.

## 5. Slice Plan (strangler, building on shipped M1 alpha/beta/delta)

### Slice A1 — Autopilot Core (claude builds, deepseek verifies)
**Builds on:** M1-alpha skeleton + M1-delta ManagedChild/DaemonLock

What: `daemon_is_live(agent)` function (one Redis EXISTS on `bifrost:daemon:<agent>`).
Stop-hook fast-path: call it, return if True. `.rearm` trigger file convention:
daemon polls for `bifrost_wake_<agent>_<sid>.rearm` in tempdir, spawns listener
child on detection. Marker janitor: daemon sweeps stale `.alive` markers at
startup + hourly. Presence card gains `runtimes` field.

Pins:
- A1-P1: `daemon_is_live("claude")` returns True while daemon runs, False within 1 TTL of daemon exit
- A1-P2: Stop-hook with live daemon returns in <1ms (no wake_armed, no grace sleep)
- A1-P3: Daemon detects `.rearm` trigger within 0.5s and spawns listener child
- A1-P4: Stale markers (>30min) removed by daemon sweep; fresh markers (<5min) survive
- A1-P5: Daemon card carries `runtimes.runner` and `runtimes.listener` — both "live" when children alive

### Slice A2 — Listener as Managed Child (claude builds, deepseek verifies)
**Builds on:** A1 + M1-gamma spec

What: Daemon spawns `bifrost_wake.py` as ManagedChild (listener tier, same
ManagedChild class as runner). ccd channel signaling: on listener benign exit
(wake-worthy mail detected), daemon signals session via ccd. Adoption path:
daemon detects harness-spawned listener (PID in seat file, no ManagedChild
wrapping it) → wraps in PID-only monitor.

Pins:
- A2-P1: Listener child detects wake-worthy mail → exits 0 → daemon signals session via ccd
- A2-P2: Daemon adopts harness-spawned listener (reads PID from seat file, polls liveness)
- A2-P3: Listener crash → backoff restart per ManagedChild policy; circuit breaker trips at 3/5min

### Slice A3 — Runner-Down Visibility (deepseek builds, claude verifies)
**Builds on:** A1 + M1-delta circuit breaker

What: `runtimes` field on daemon card updated every heartbeat. Doctor command:
`py agent_cli.py doctor` reads all agents' cards, flags `runner: "down"` or
`runner: "blocked"`. SIBLINGS whisper line surfaces runner status from card
summary. Optional: daemon re-publishes blocker broadcast if runner stays
down > 10min (operator escalation — "your runner has been down for 10 minutes").

Pins:
- A3-P1: After runner exits 0, daemon card shows `runtimes.runner: "down"` within one heartbeat (≤8s)
- A3-P2: `agent_cli.py doctor` flags `runner: "down"` with a warning line
- A3-P3: Whisper SIBLINGS line shows "runner: down 12m" when card carries down state + age

### Slice A4 — Adopt-and-Forget (joint, polish)
**Builds on:** A1+A2+A3

What: The operator types `py scripts/bifrost_daemon.py --agent claude --spawn-runner --spawn-listener` ONCE. After that: zero manual arming, zero stop-hook blocks, zero marker litter, runner-down visible in ≤8s, listener re-armed within 0.5s of stop-hook firing. The nag disappears because the daemon is running. The runbook shrinks to one page.

## 6. What Deliberately Does NOT Change

- `core/comm/bus.py` — zero changes
- `core/comm/runner_lock.py` — zero changes
- Consume path — unmoved (ruling 1)
- Stop-hook promise audit — unchanged
- K7 activity stamp — unchanged
- Wake listener's `watch()` loop — byte-identical; only the SPAWNER changes
- Existing seat file convention — unchanged
- Clean-death trio (M1-beta) — unchanged
- Incarnation cards (T074) — unchanged
- ManagedChild class — unchanged (listener is a second INSTANCE, same class)
- TTL crash net — unchanged (ruling 2)
- Kill switches — unchanged (ruling 4)

## 7. Non-Goals

1. **Full self-healing fleet.** A daemon crash still needs host-level restart (M1-epsilon, Windows Task Scheduler). This design makes the daemon the autopilot; it does not make the autopilot immortal.
2. **Cross-agent health aggregation.** Each daemon reports its own agent's health. A fleet dashboard that aggregates all daemon cards is a separate concern.
3. **Automatic daemon start.** The operator still types the command once. The host supervisor (Task Scheduler) can auto-start on boot — that's M1-epsilon's job, not autopilot's.
4. **Remote listener signaling.** The ccd channel works for local Claude sessions. Remote signaling (e.g., a daemon on a GPU box waking a Claude session on a laptop) is a networking concern.
5. **Graceful degradation under disk-full.** If tempdir is full, `.rearm` trigger writes fail → stop-hook falls through to legacy path. Acceptable — the daemon path is an optimization over manual arming, not a hard requirement.

## Verdicts (V-line — fence workspace law)

V1. The four chores (arm/claim/stand-down/nag) share one root cause: no single process owns the agent's full runtime lifecycle. The daemon, already the continuous-presence body, is the natural owner. [CERTAIN]

V2. The two-path bootstrap (daemon-live → fast-path stop-hook + .rearm trigger; daemon-down → legacy + one-time nag) is the minimal strangler migration. It adds exactly one Redis GET to the stop-hook and one file write. [CERTAIN]

V3. .rearm trigger files are the correct control surface for daemon↔stop-hook communication because (a) the stop-hook is a one-shot subprocess with no bus client, (b) filesystem writes are 0.1ms vs 200ms for bus init, (c) the daemon's 0.2s tick bounds latency. [INFERRED — untested latency measurement]

V4. The ccd channel is the correct wake signal because the harness ALREADY responds to it (T073 Phase 5). The daemon signals; the harness re-invokes Claude. No new protocol. [CERTAIN]

V5. Marker janitor in the daemon (not the session-start hook) is correct because (a) the daemon is always-on and sees all markers for its agent, (b) the session-start hook only fires per-session, (c) a periodic sweep costs one listdir per hour. [CERTAIN]

V6. The presence card's `runtimes` field is the correct status surface because `read_cards()` already exists, the whisper already renders cards, and the doctor already reads cards. No new bus messages, no new keys, no new dashboard. [CERTAIN]

V7. The daemon does NOT consume the work lane — ruling 1 stands unchanged. The autopilot is a supervisor, not a worker. This keeps the cursor where it is and the consume path byte-identical. [CERTAIN]

V8. ManagedChild's existing backoff + circuit breaker apply to the listener child without modification. A crashing listener is the same class of problem as a crashing runner — same restart policy, same breaker trip → blocker broadcast. [INFERRED — the listener's crash modes are less tested than the runner's]

V9. The nag ("start the daemon") appears ONCE per session when the daemon is down. This is the operator's incentive to start the daemon — but it is a nudge, not a block. The session proceeds without the daemon on the legacy path. [DESIGN — exact UX of the nag TBD by claude who owns the stop-hook]

## 8. Confidence

| Section | Confidence | Notes |
|---------|-----------|-------|
| §2a Runtime Ownership | HIGH | ManagedChild already shipped; listener is a second instance, same class |
| §2b Bootstrap | MEDIUM-HIGH | Two-path design is sound; `.rearm` trigger latency needs measurement |
| §2c Marker Janitor | HIGH | One listdir + os.remove per sweep; K7 threshold already trusted |
| §2d Stop-Hook Transformation | HIGH | `daemon_is_live()` is one Redis GET; the legacy fallback is byte-identical to today |
| §3 Architecture | HIGH | Pure composition of shipped primitives |
| §5 Slice Plan | MEDIUM-HIGH | A1 is ~100 lines of new code; A2 depends on M1-gamma (ccd channel integration); A3 is card-field + doctor-line |

**Overall: MEDIUM-HIGH.** The autopilot is an integration design, not a new-primitive design. Every component it composes already shipped today (DaemonLock, ManagedChild, circuit breaker, incarnation cards, wake_seat janitor, ccd channel). The only genuinely new mechanism is the `.rearm` trigger file convention — and that's a one-line file write in the stop-hook and a one-line `os.path.exists` poll in the daemon. The risk is in the ccd channel integration for A2, which depends on M1-gamma's plumbing.
