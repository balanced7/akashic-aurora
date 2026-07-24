---
akashic_id: art_20260715_t060-m1-continuous-presence-design-blind_ebd800
akashic_sha: e4d243dc9a1a
status: draft
type: report
date: 2026-07-15
title: "T060-M1 Continuous Presence — Design (blind half, deepseek) — 2026-07-15"
gist: "## 1. Ground Truth: Components That Exist + Their Lifecycles ### 1a. DeepSeek Runner (`scripts/bifrost_runner_deepseek.py`) **Lifecycle:** H"
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T03:17:56"
updated: "2026-07-15T03:17:56"
---
<!-- GENERATED PROJECTION of art_20260715_t060-m1-continuous-presence-design-blind_ebd800 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T060-M1 Continuous Presence — Design (blind half, deepseek) — 2026-07-15

## 1. Ground Truth: Components That Exist + Their Lifecycles

### 1a. DeepSeek Runner (`scripts/bifrost_runner_deepseek.py`)
**Lifecycle:** Human-launched foreground process → `runner_lock.acquire()` (:798) → consume loop (:900–980) with 5s heartbeat thread (:870–885) → `runner_lock.release()` in `finally` (:972). **Supervision:** The lock IS the supervisor — TTL=20s (`LOCK_TTL`, runner_lock.py:49). A crash leaves the key to expire; next launch acquires clean. **Restart:** Manual. No harness tracks this process; no watchdog respawns it. A dead runner = agent unreachable until a human notices. **Failure modes:** Bus loss → `BusLossGuard` stand-down (:912–918). Stale generation → fenced out of cursor commit (:962–965). API timeout → `REPLY_TIMEOUT_SEC` (600s, :61) with error reply.

### 1b. Wake Listener (`scripts/bifrost_wake.py`)
**Lifecycle:** Launched by Claude as `run_in_background` (harness-tracked). `main()` (:218–243): writes PID seat file BEFORE heavy imports (T050 Q6, :225), then `watch()` (:119–175). Blocks in `api.wake_block()` chunks (120s default). Exits on: wake-worthy mail (`WAKE_WORTHY_KINDS`, :67), 30-min deadline (:149), seat loss (newest-wins singleton, :139–145), or bus offline (:126). `finally` removes seat if still ours (:236–240). **Supervision:** The harness — "background task finished" re-invokes Claude. The stop hook is BACKSTOP, not primary (T073 Phase 3). **Restart:** Claude re-arms on next turn OR stop-hook demands re-arm. **Seat per session** (:14–16): `bifrost_wake_{agent}_{session}.pid` under tempdir.

### 1c. Stop Hook (`scripts/hooks/claude_stop.py`)
**Lifecycle:** Fires EVERY turn-end (harness-injected). Two latched checks: WAKE (`wake_armed()`, :130) with 1.5s grace recheck (:149) + 25s loop guard (:154); PROMISE (`_promise_block()`, :137) — once-per-session latch. `_touch_activity()` (:54–63) stamps K7 liveness. `refresh_consumer()` (:62–65) refreshes RB-21 session consumer seat. **Supervision:** None — a hook is a one-shot subprocess; if it crashes, the turn ends without blocking (fail-open). **Restart:** Next turn-end spawns a fresh hook.

### 1d. Runner Lock (`core/comm/runner_lock.py`)
**Lifecycle:** `acquire()` (:87) — atomic `SET NX` with TTL. `heartbeat()` (:127) refreshes TTL. `release()` (:164) on clean shutdown. Crash-safe by TTL expiry. **Fencing** (L1b): `generation_of()` (:70) — monotonic INCR per acquisition; guarded cursor write refuses lower generations. **Session variant** (RB-21): `SESSION_CONSUMER_TTL` (1800s, :55), `claim_consumer()` / `refresh_consumer()`. **Who watches:** No one — TTL is the only guardrail. A hung process holding the lock silently fences successors for `LOCK_TTL` seconds.

### 1e. Dispatcher (`core/comm/dispatcher.py`)
**Lifecycle:** `run()` with `PSUBSCRIBE bifrost:bell:*` (:74). `handle_notice()` → `should_escalate()` → `_invoker(agent, digest, notice)`. **Status:** PARKED. No W3 invoker registry exists; T073 ruled it out of that arc and parked it for "Phase 5 / M1." No process runs it in production. Test-only harness exists.

### 1f. Summary: Who Spawns / Watches / Restarts What
| Component | Spawned by | Watched by | Restarted by |
|-----------|-----------|------------|-------------|
| Runner | Human (`py scripts/bifrost_runner_deepseek.py`) | Lock TTL | Human (manual relaunch) |
| Wake listener | Claude harness (`run_in_background`) | Harness (task completion) + stop hook (backstop) | Harness re-invokes Claude → stop hook demands re-arm |
| Stop hook | Harness (every turn-end) | Nothing (one-shot subprocess) | Next turn-end |
| Runner lock | Runner / session consumer | TTL expiry | Next acquire() |
| Dispatcher | (not running) | — | — |


## 2. The Design: Daemon-Peer Architecture

### 2a. Core Principle
Every agent is a **daemon peer**: a supervised, auto-restarting process with a durable identity that survives session boundaries. A directed message ALWAYS finds its target — no "Claude is unreachable because his last session ended cleanly and the wake listener TTL'd out 30 minutes ago." The architecture formalizes what the lock + wake listener already half-implement: presence that outlives any single session.

### 2b. The Peer Daemon (one per agent)
A long-lived supervisor process — `bifrost_daemon.py --agent <id>` — that OWNS the agent's presence on the bus and manages its RUNTIMES. Three responsibilities:

1. **Presence & lock**: Acquires the singleton runner lock (:87, runner_lock.py) and holds it INDEFINITELY (heartbeat every 5s, no TTL-based surrender). The agent EXISTS on the roster as long as the daemon lives. This is the "always reachable" half.

2. **Runtime supervision**: Manages zero or more child RUNTIMES (one per active harness tier — a Claude session, a Cursor process, the DeepSeek runner). Each runtime is a subprocess the daemon spawns, monitors, and restarts per policy. The daemon is the PARENT; runtimes are its children.

3. **Inbox fan-out**: Consumes the agent's work lane and fans messages to the correct runtime (or queues them if no runtime is live). The daemon IS the consumer — runtimes receive pre-triaged mail, never consume directly.

### 2c. Runtime Tiers (what "runtime" means per harness)

**Tier 1 — Claude Code session:** The daemon spawns `bifrost_wake.py` as a MANAGED child (not a background task). When wake-worthy mail arrives, the daemon signals the session via the ccd channel (`mcp__ccd_session_mgmt__send_message` — T073 Phase 5 adoption). The session's existing wake path handles the rest. The daemon monitors the wake listener's liveness; if it dies, the daemon restarts it. The stop hook becomes PURELY a promise-audit hook — the "are you wakeable" check is the daemon's problem now.

**Tier 2 — DeepSeek runner:** The daemon IS a runner variant. When agentic mode is on, the daemon embeds the consume→reply loop directly. When off, the daemon spawns `bifrost_runner_deepseek.py` as a child and restarts it on crash. The human no longer launches the runner — the daemon owns it.

**Tier 3 — Cursor / generic LSP peer:** The daemon holds presence and queues mail. A lightweight sidecar (the "Cursor adapter") polls the daemon and injects context into the IDE. TBD detail — this tier is the least grounded.

### 2d. Failure Modes & Restart Policy
- **Daemon crash**: The daemon IS the presence. A dead daemon = agent offline. Mitigation: host-level auto-restart (systemd / launchd / Windows Service). The daemon's lock TTL is LONG (hours, not seconds) — a transient restart re-acquires without fencing.
- **Runtime crash**: Daemon restarts per tier policy. Claude wake listener: immediate restart (seat file re-written). DeepSeek runner: exponential backoff (1s → 2s → 4s → ... → 60s cap). Max 3 restarts per 5-min window, then the daemon sends a `blocker` to the bus and waits for human intervention.
- **Bus loss**: Daemon stands down (same BusLossGuard, :912), then polls Redis every 30s. Reconnects cleanly with cursor intact.
- **Lock stolen**: Daemon detects `heartbeat()` returning False, logs FATAL, exits. The host-level supervisor restarts it; the new daemon races for the lock.

### 2e. Identity / Seat Interaction
The daemon's identity IS the agent's identity. The runner_lock's `instance_token` becomes STABLE — no longer `pid:random`, but a daemon UUID written to a dotfile. Respawns reuse the same token, so `generation_of()` survives daemon restarts (the fencing generation still increments on each acquisition — the token is stable, the tenure is not). This is the "always resumable" half: thread state (per-peer convos, LEDGER_FOLDS, context_hints ring) lives in the daemon's memory across runtime restarts.

### 2f. Architecture Diagram (text)
```
┌──────────────────────────────────────────────┐
│              bifrost_daemon.py                │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  │
│  │ presence   │  │ inbox    │  │ runtime   │  │
│  │ (lock+hb)  │  │ fan-out  │  │ supervisor│  │
│  └────────────┘  └──────────┘  └─────┬─────┘  │
│                                      │         │
│         ┌────────────────────────────┼─────┐   │
│         │        child runtimes      │     │   │
│         │  ┌────────┐ ┌──────────┐   │     │   │
│         │  │ wake   │ │ runner   │   │     │   │
│         │  │ listener│ │ (api)    │   │     │   │
│         │  └────────┘ └──────────┘   │     │   │
│         └────────────────────────────┘     │   │
└──────────────────────────────────────────────┘
         ↑ host-level supervisor (systemd / launchd)
```


## 3. Exists-vs-Missing Table

| Capability | Exists? | Where / Why Not | M1 Action |
|-----------|---------|-----------------|-----------|
| Agent presence on bus | ✅ | `bus.register(card=CARD)` — runner (:860, :929, :943) and wake listener | Daemon owns it permanently |
| Singleton lock (one consumer) | ✅ | `runner_lock.acquire()` (:87) + `heartbeat()` (:127) | Daemon holds it; TTL → hours |
| Crash-safe lock release | ✅ | TTL expiry (LOCK_TTL=20s, :49) | Longer TTL for daemon |
| Fencing generation | ✅ | L1b: `generation_of()` (:70), guarded cursor writes (:962) | Survives daemon restart (stable identity token) |
| Wake listener (per-session) | ✅ | `bifrost_wake.py` `watch()` (:119) | Daemon-spawned, not harness-spawned |
| Stop-hook wake check | ✅ | `claude_stop.py` `wake_armed()` (:130) | Downgraded to backstop-only; daemon owns wakeability |
| Harness-tracked background task | ✅ | Claude Code `run_in_background` | Daemon replaces this for wake; harness still tracks other tasks |
| Dispatcher (doorbell→wake) | ⚠️ Parked | `dispatcher.py` `run()` — no W3 invoker registry (T073) | Daemon IS the dispatcher for its agent |
| Daemon process (supervisor) | ❌ | Does not exist | **BUILD**: `scripts/bifrost_daemon.py` |
| Child runtime supervision | ❌ | Runner is foreground; wake listener is harness-spawned | **BUILD**: daemon spawns + monitors children |
| Inbox fan-out (one consumer → many runtimes) | ❌ | Runner consumes directly from bus | **BUILD**: daemon consumes, fans to runtimes via internal queue |
| Restart policy (backoff, max retries) | ❌ | Crash = manual relaunch | **BUILD**: exponential backoff, 3/5min circuit breaker |
| Stable daemon identity token | ❌ | `instance_token` = `pid:random` (:81) | **BUILD**: UUID dotfile, survives restart |
| Per-peer conversation survival | ⚠️ Partial | `convos` dict (:399) lives in runner memory — dies with process | Daemon holds convos across runner restarts |
| LEDGER_FOLDS survival | ⚠️ Partial | `LEDGER_FOLDS` dict (:102) — cleared after each turn | Daemon holds across restarts; drain-on-delivery |
| Host-level auto-restart | ❌ | Nothing restarts a dead runner | **BUILD**: systemd/launchd unit (or Windows Service); runbook |
| ccd channel integration | ✅ | `mcp__ccd_session_mgmt__send_message` (T073) | Daemon uses this to ping Claude sessions |
| Bus-loss resilience | ✅ | `BusLossGuard` (:912) + backoff | Daemon reconnects; queued mail delivers on reconnect |
| Per-tier runtime variation | ❌ | All agents share the same runner/wake pattern | **BUILD**: daemon's runtime registry maps tier → spawn strategy |


## 4. Acceptance Pins (M1-P1 through M1-P12)

| Pin | Assertion | Verification |
|-----|----------|-------------|
| M1-P1 | `scripts/bifrost_daemon.py --agent claude` starts, acquires lock, registers presence, and survives 60s without crashing | Manual: launch, check roster, wait |
| M1-P2 | Daemon heartbeat keeps lock TTL fresh: after 30s, `runner_lock.holder("claude")` returns the daemon's token with `ts` within last 10s | Integration: start daemon, poll lock key |
| M1-P3 | Daemon spawns `bifrost_wake.py` as a child; when wake-worthy mail arrives, daemon signals Claude via ccd channel AND the wake listener's exit triggers harness re-invoke | E2E: send mail to Claude while daemon is live; Claude wakes and answers |
| M1-P4 | Wake listener crash → daemon restarts it within 2s; seat file is re-written; stop hook sees armed listener | Fault-injection: kill wake listener PID, observe respawn |
| M1-P5 | Daemon crash → host supervisor restarts it; lock re-acquired with new fencing generation; cursor commits under old generation are fenced out (STALE_GENERATION) | Kill daemon, confirm restart + fence |
| M1-P6 | DeepSeek runner mode: daemon embeds consume→reply loop; API timeout/crash → daemon sends error note, keeps running | Send malformed prompt, observe error reply + daemon still alive |
| M1-P7 | Per-peer conversation state survives runner restart: send "remember X", kill runner child, daemon restarts it, send "what did I ask you to remember?" → answer includes X | E2E with kill -9 on runner child |
| M1-P8 | Stop hook no longer blocks on wake check when daemon is live (daemon owns wakeability; hook is backstop only) | Session with daemon: stop hook fires, no block |
| M1-P9 | Circuit breaker: 3 runner child crashes in 5 minutes → daemon sends `blocker` to bus, stops restarting, waits for human | Fault-injection loop |
| M1-P10 | Bus loss → daemon stands down (BusLossGuard), polls every 30s, reconnects with cursor intact; queued mail delivers | Kill Redis, wait, restart Redis, observe delivery |
| M1-P11 | Migration path: existing runner launched standalone still works; daemon detects pre-existing lock and REFUSES (no steal) | Start runner, then start daemon — daemon exits cleanly |
| M1-P12 | Stable identity: daemon UUID written to `~/.akashic/daemon_{agent}.id`; restart reuses it; fencing generation still increments | Two daemon launches, same token, different generations |


## 5. Who-Builds-What + Migration Path

### 5a. Build Order (strangler, no big-bang)

**Slice M1-A — Daemon Skeleton** (claude builds, deepseek verifies)
- New file: `scripts/bifrost_daemon.py` — argparse, lock acquisition (reuses `runner_lock`), presence registration (reuses `bus.register`), heartbeat thread, BusLossGuard. NO child runtimes yet. Exits cleanly on SIGINT/SIGTERM. Stable identity token via `~/.akashic/daemon_{agent}.id` dotfile.
- Test: M1-P1, M1-P2, M1-P11, M1-P12.

**Slice M1-B — Wake Listener as Managed Child** (claude builds, deepseek verifies)
- Daemon spawns `bifrost_wake.py` as `subprocess.Popen`. Monitors via `poll()`. On exit: if exit code 0 (benign wake), signal Claude via ccd channel. If exit code ≠ 0 (crash), restart per policy. Seat file management moves into daemon (daemon writes it before spawning child).
- Stop hook change: `wake_armed()` check gains a DAEMON fast-path — if daemon seat file exists AND PID alive, skip the block (M1-P8). The check stays as backstop for daemon-dead scenarios.
- Test: M1-P3, M1-P4, M1-P8.

**Slice M1-C — Runner as Managed Child + Circuit Breaker** (deepseek builds, claude verifies)
- Daemon spawns `bifrost_runner_deepseek.py` as child (or embeds loop directly — flag `--embedded-runner`). Circuit breaker: `collections.deque` of crash timestamps, 3 in 5min → blocker + pause.
- Per-peer conversation survival: daemon holds `convos` dict; on child restart, injects conversation summary into the new child's prompt. This is the "thread state survives" claim from M1-P7.
- Note: embedding the runner loop directly (same process) is the simpler path for DeepSeek; spawning as child preserves the existing runner code for migration safety. Build the child-path first; embed later if perf demands it.
- Test: M1-P5, M1-P6, M1-P7, M1-P9.

**Slice M1-D — Host-Level Supervisor + Runbook** (joint)
- systemd unit file (Linux), launchd plist (macOS), Windows Service wrapper — all three in `deploy/`. Runbook: `docs/runbooks/m1-daemon.md` — how to start, stop, check status, read logs, force-restart.
- Test: M1-P5 (host-level), M1-P10.

### 5b. Migration Path (Strangler Fig)

**Phase 1 — Coexistence.** Daemon launches alongside existing infrastructure. It detects pre-existing lock and refuses to start (M1-P11). The operator chooses: stop the old runner → start daemon, OR keep old runner → daemon waits. No automatic eviction.

**Phase 2 — Daemon-preferred.** Wake listener launches via daemon, not harness `run_in_background`. The harness still CAN launch it (backstop); daemon detects the harness-spawned seat and adopts it (PID in daemon's seat file → daemon monitors it instead of spawning its own). Stop hook downgrades to backstop.

**Phase 3 — Daemon-only.** The harness's "arm wake listener" instruction becomes "ensure daemon is running." `bifrost_wake.py` is deprecated as a standalone entry point (still importable; `watch()` becomes an internal helper). Old runner launches get a deprecation warning.

### 5c. What Does NOT Change
- `core/comm/bus.py` — zero changes. The daemon is a consumer like any other.
- `core/comm/runner_lock.py` — zero API changes. The daemon calls the same `acquire`/`heartbeat`/`release`. TTL becomes configurable (env var override), but the code surface is unchanged.
- `core/comm/dispatcher.py` — still parked. The daemon IS the dispatcher for its agent; the multi-agent dispatcher remains a future W3 concern.
- The lane protocol (T045) — the daemon consumes from the work lane exactly as the runner does today.


## 6. Non-Goals

1. **Multi-agent dispatcher (W3).** The daemon manages ONE agent. The parked `dispatcher.py` (multi-agent doorbell fan-out with pluggable invokers) is a SEPARATE concern — M1 does not touch it. When W3 lands, daemons register their invoker with the dispatcher; until then, each agent's daemon is its own dispatcher.

2. **Cross-machine presence.** The daemon runs on the SAME host as its agent's harness. Remote-agent wake (e.g., a DeepSeek runner on a GPU box) is a networking concern — M1 assumes localhost Redis and local subprocess management.

3. **Signed identity / auth.** The daemon's identity token is a UUID dotfile — trust-by-filesystem, not cryptographic. The fencing generation prevents stale writes, not impersonation. Signed messages are TBD.

4. **Graceful degradation under host resource pressure.** The daemon's restart policy handles child crashes, not "the machine is swapping and everything is slow." That's an ops concern.

5. **Daemon-to-daemon peer discovery.** Daemons don't discover each other. The bus roster (`bus.register`) already lists every agent. No new discovery protocol.

6. **Configuration hot-reload.** Changing restart policy / TTL / tiers requires a daemon restart. SIGHUP reload is future.

7. **The Cursor / LSP adapter (Tier 3).** Named in the design for architectural completeness; NOT in scope for M1 build. The adapter's protocol (polling? Unix socket? stdin/stdout JSON-RPC?) is undefined and needs its own design wave.

8. **Removing the stop hook.** The stop hook stays. It loses the wake-armed check (daemon backstop only) but keeps the promise audit and K7 activity stamp. Removing it entirely would require rewriting the harness contract — out of scope.

9. **Daemon as a Windows Service with proper SCM integration.** The `deploy/` tier includes a Windows Service wrapper, but it's a thin `py daemon.py` launcher, not a native SCM binary. Full Windows service parity is future.

10. **Embedded runner as the DEFAULT path for DeepSeek.** M1-C builds child-process supervision first. Embedding the runner loop in-process is an optimization flag (`--embedded-runner`), not the primary path, to preserve migration safety.


## 7. Confidence + Grounding Quality (T049 Structured Uncertainty)

| Section | Confidence | Grounding | Notes |
|---------|-----------|-----------|-------|
| §1 Ground Truth | **HIGH** | Every claim cites file:line from live code read during this design session. The runner's lifecycle (:798–980), wake listener's watch() (:119–175), stop hook's checks (:130–165), runner_lock's acquire/heartbeat (:87–160), dispatcher's parked state (T073 reconciliation doc). | I LIVE in the runner — this is my own infrastructure. |
| §2 The Design (daemon architecture) | **MEDIUM-HIGH** | Grounded in patterns that already exist: the lock's TTL supervision (:49), BusLossGuard's reconnect (:912), heartbeat thread (:870), context_hints ring, LEDGER_FOLDS dict. The daemon is a COMPOSITION of existing primitives, not a new primitive. | Risk: inbox fan-out (one consumer → many runtimes) is the only genuinely new mechanism. The rest is lifecycle management over things that already run. |
| §2d Failure Modes | **MEDIUM** | Restart policy (exponential backoff, circuit breaker) is standard but UNTESTED in this codebase. Bus loss recovery is proven (BusLossGuard in production). Lock-stolen detection works (heartbeat returns False). | The interaction between daemon crash → host restart → lock re-acquisition → fencing generation increment is the highest-risk sequence. Needs drill coverage (M1-P5). |
| §2e Identity / Seat | **MEDIUM** | Stable identity token (UUID dotfile) is a NEW concept — the current `instance_token` is `pid:random` (:81). Fencing generation already supports stable tokens (it's keyed on the token string, :70–72), so the mechanism exists; the migration from pid-based to UUID-based identity is the risk. | A daemon restart with the same token but new generation MUST fence its predecessor's cursor writes. L1b already does this — the question is whether the guarded cursor write path (:962) handles the "same token, higher generation" case correctly. I believe it does (the guard checks generation ≥ stored, not token equality). |
| §2c Tier 3 (Cursor) | **LOW** | This is architectural placeholder, not a design. No Cursor harness has been studied; the "polling sidecar" pattern is speculative. | Explicitly non-goal for M1 build (§6.7). Included for architectural honesty. |
| §3 Exists-vs-Missing | **HIGH** | Every "Exists" row cites a specific file:line. Every "Missing" row names the build slice that fills it (§5a). | The table IS the gap analysis. |
| §4 Acceptance Pins | **MEDIUM-HIGH** | 12 pins, each with a concrete verification action. M1-P1 through M1-P4 are direct extensions of existing test patterns (the runner's lock acquisition test, wake listener's seat test). M1-P7 (conversation survival) is the riskiest — it depends on serializing Agent state, which `deepseek_chat.Agent` does not currently support. | M1-P7 may need its own design sub-wave (conversation serialization format). Flagged for reconciliation. |
| §5 Build Order + Migration | **HIGH** | Four slices in dependency order. M1-A has zero new primitives — pure composition. M1-B changes one existing behavior (stop hook downgrade). M1-C introduces the circuit breaker (new). M1-D is documentation + deploy artifacts. Strangler phases (coexistence → daemon-preferred → daemon-only) follow the T045/T073 migration pattern that already succeeded. | The migration path is the STRONGEST part of this design — it mirrors exactly what worked for lane cutover. |
| §6 Non-Goals | **HIGH** | Explicitly scoped exclusions prevent scope creep. Each non-goal names what IS in scope instead. | Standard M1 discipline. |

### 7a. Overall Confidence: MEDIUM-HIGH
The daemon is architecturally conservative: it composes existing primitives (lock, heartbeat, BusLossGuard, bus.register, subprocess) into a new lifecycle. The only genuinely NEW mechanisms are (a) inbox fan-out (one consumer, N runtime children) and (b) conversation state serialization. Both are scoped to specific slices with fallback positions (fan-out can start as pass-through to single child; conversation survival can start as summary injection rather than full state transfer). The migration path is proven (strangler fig, T045/T073 precedent). The biggest risk is the fencing generation interaction on daemon restart — this needs drill coverage before M1 seals.

### 7b. Open Questions for Reconciliation (claude's mirror)
1. **Conversation survival depth** (§5a M1-C): Full Agent state serialization vs. summary injection? The pin (M1-P7) tests "remember X → restart → recall X" but doesn't specify fidelity.
2. **Daemon's consume model**: Does the daemon consume AND fan-out (this design) or does it ONLY supervise and let children consume directly? I chose consume-and-fan because it keeps the cursor in one place — but it adds a hop.
3. **Host supervisor**: systemd/launchd/Windows Service — which one is the priority for the Akashic host (Windows today)?
4. **Stop hook downgrade timing**: M1-B proposes immediate downgrade; should it be kill-switched (env var) for the first week?

## Verdicts (fence M1-CF lines — transcribed 1:1 from sec.7 by claude for the seal; wording deepseek's, note t060-m1-fence-integrity)

V1. Ground-truth lifecycles (runner / wake listener / stop hook / runner_lock / dispatcher) are as cited, file:line grounded from live code [CERTAIN]
V2. The daemon composes existing primitives (lock TTL, heartbeat, BusLossGuard, subprocess); inbox fan-out is the ONLY genuinely new mechanism [DESIGN]
V3. Restart policy (exponential backoff + 3-in-5min circuit breaker) is standard but untested in this codebase; daemon-crash -> host-restart -> lock-reacquire + fencing is the highest-risk sequence [INFERRED]
V4. Stable UUID identity token works because fencing generations key on the token string (guard checks generation, not token equality) [INFERRED]
V5. Tier-3 Cursor adapter is an architectural placeholder, not a design [UNCERTAIN]
V6. scripts/bifrost_daemon.py and docs/runbooks/m1-daemon.md are FUTURE build targets named by the plan, not claims about existing code [DESIGN]
V7. The strangler migration (coexistence -> daemon-preferred -> daemon-only) mirrors the proven T045/T073 pattern [CERTAIN]

