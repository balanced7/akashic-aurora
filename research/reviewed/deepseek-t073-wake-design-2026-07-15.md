# T073 Wake Reliability Design — deepseek blind half

Date: 2026-07-15
Pattern: blind half (claude's half unread; reconciliation to follow)
Agent: deepseek
Task: T073 — "agents stalled or unreachable" — Daniel directive

## Ground Truth (code-level census, this session)

### Participant classes and their delivery channels

| Class | Wake channel | Consume channel | Lifecycle owner | Re-arm mechanism |
|-------|-------------|-----------------|-----------------|------------------|
| **Runner** (deepseek) | `bifrost_wake.py` — but NOT needed; runner is an in-process `bus.wait()` loop in `bifrost_runner_deepseek.py:875+` | `bus.inbox(advance=True)` / lane-mode `work_drain()` | `runner_lock.py` (TTL heartbeat) + launcher `_monitor_loop` | Auto: the loop is always consuming |
| **Claude session** (turn-based) | `bifrost_wake.py` — background task (`run_in_background`) → completion re-invokes session | `bifrost-sync --consume` (CLI) or inline `BifrostAPI.consume_inbox()` | Harness (Claude Desktop/CLI) — hooks fire on turn boundaries | **Manual**: `claude_stop.py` blocks if `wake_armed() == False` → model re-arms |
| **Future daemon** (hypothetical) | Same doorbell subscription as Dispatcher, or lane-based wake | Own cursor, own lock | Supervisor tree (launcher lineage) | Auto: daemon loop |

### The harness constraint (receipt 1)

`claude_stop.py:220`: the stop hook TELLS the model to launch `bifrost_wake.py` as a `run_in_background` task. But a `run_in_background` launches a subprocess — and ONLY a background task the SESSION ITSELF launches re-invokes that session when it completes. Hook-spawned processes ARE invisible to the harness. The stop hook cannot spawn the watcher directly; it can only block and TEACH the model to spawn it.

This is the root of the re-arm fragility: every turn, the model must remember to re-arm. The stop hook catches failure but cannot fix it — it blocks, the model re-arms, and the NEXT turn the watcher has already exited (because mail in the window woke it). The model consumes the mail, does work, stops — and the cycle repeats. ~15x noise-fires in tonight's session.

### The twin-wake impossible (receipt 2)

`bifrost_wake.py:129`: `if frm == agent: continue` — this SKIPS messages FROM the same agent. Correct for echo prevention (a runner answering its own broadcast should not wake itself). FATAL for incarnation mail: when two Claude sessions run concurrently (twin session), session A's handoff to session B has `frm=claude`, and session B's watcher ALSO has `agent=claude` → SKIPS it. Daniel hand-bridged.

Root cause: the agent identity `agent` is a LOGICAL agent id ("claude"), but wake dispatch needs to distinguish INCARNATIONS (sessions) of the same logical agent. The per-session seat (`bifrost_wake_claude_<session>.pid`) solved the seat-collision problem (K6-K8), but the `frm == agent` filter still uses the logical id, which collapses all sessions into one.

### Stall inventory (receipt 3)

| Root cause | Fixed? | Lesson |
|-----------|--------|--------|
| Wake loop: bc cursor stale, 1280 traces hiding one handoff | PARTIAL (T045 lane-mode removes the class; legacy still vulnerable) | `wake_loop_from_unconsumed_broadcast` |
| Eaten-confirm: consume without triage = silent mail loss | YES (RB-26 + discipline) | `consume_to_null_eats_mail` |
| Lane-cursor divergence: legacy + lane cursors out of sync | PARTIAL (T045 lane-first consume; legacy still a straggler) | `lane_pending_check_needs_wake_worthiness` |
| Runner lifecycle orphans: exit-127 wrapper death orphaning healthy child | NO | `twin_session_diagnosis_first` (symptom, not fix) |
| Stale singleton locks: runner killed, lock TTL not expired, restart blocked | YES (`clear_if_pid` + `runner_lock_stale_after_kill`) | Fixed |
| Reply-path stranding (T066): lane reply not consumed by legacy-only consumer | YES | Fixed |
| Global pause freeze (runner_wedge): RateLimiter → global pause → all runners silent | PARTIAL (diagnosable, not prevented) | `runner_wedge_check_pause_first` |

---

## (a) Protocol: perfectly reliable wake+communicate for every participant class

### The invariant

> **A seat MUST fire if and only if there is actionable mail for THAT incarnation.**

"Actionable" = the message's kind is wake-worthy AND the message is addressed to this incarnation (not just this logical agent). "That incarnation" = the specific session/process, not any other session of the same logical agent.

### The three delivery channels each class actually has

**1. Runner (in-process loop)**
- Primary: `bus.wait()` / `bus.inbox(advance=True)` — always on, no arm needed
- Doorbell: `Dispatcher` pub/sub — redundant for runners; they're already consuming
- Weakness: the runner IS the consumer; if it wedges (model hang, pipe stall, global pause), nothing external can reach it except a kill+restart

**2. Claude session (turn-based, harness-managed)**
- Primary: `bifrost_wake.py` as `run_in_background` task — completion wakes the session
- Doorbell: `Dispatcher` pub/sub — NOT wired; the harness has no doorbell listener
- Weakness: every re-arm is a manual act by the model, gated by the stop hook
- **Only channel that actually works for an idle session**: the background task completion callback

**3. Future daemon**
- Primary: `Dispatcher` pub/sub + per-daemon invoker (the W3 registry)
- Doorbell: same `bifrost:bell:*` channel, or lane-specific subscription
- Weakness: the W3 invoker registry doesn't exist yet (frozen per `wiring_investigate_before_acting`)

### The protocol: per-incarnation addressing + incarnation-aware filter

**Incarnation identity.** Every session/runner/daemon gets an `incarnation_id`:
- Runner: `{agent}:runner:{pid}:{token_suffix}` (already minted in `instance_token()`)
- Claude session: `session:{session_id}` (already the `session_holder_token()`)
- Future daemon: `{agent}:daemon:{name}:{pid}`

**Incarnation-aware wake filter.** Replace `frm == agent` with:
```
frm_incarnation == my_incarnation → skip (echo)
frm_agent == my_agent AND to is a different incarnation of me → DELIVER (incarnation mail)
frm_agent != my_agent → deliver (cross-agent mail)
```

The key insight: `frm == agent` was correct for ECHO (I sent it, I shouldn't wake on it). It was WRONG for incarnation mail (another session of me sent it TO me — I MUST wake on it). The fix is to check `frm_incarnation` (which the sender stamps) against `my_incarnation`, not `frm_agent` against `my_agent`.

**Incarnation stamp on every send.** `Bus.send()` and `bus.send_reply()` already carry `meta.frm`. Add `meta.frm_incarnation` — the sender's stable incarnation id. The receiver's wake filter compares it to its own incarnation.

**Directed incarnation addressing.** `to` already supports agent ids. Add `to_incarnation` — when set, ONLY that incarnation wakes. When unset, ALL incarnations of the agent wake (fan-out — the ledger + locks absorb twins). This is how session A says "wake session B specifically" vs. "wake any claude that's listening."

---

## (b) The resident-dispatcher question

### What `core/comm/dispatcher.py` IS

A pure, tested, zero-token triage gate over `PSUBSCRIBE bifrost:bell:*`. It receives doorbell notices, applies `should_escalate()` (kind ∈ {request, handoff, question, blocker} or importance high/urgent), peeks the target's inbox (non-consuming), and calls an `invoker(agent, digest, notice)`.

### What it is NOT

- **Not wired.** The `invoker` (W3 wake-adapter registry) doesn't exist. `run()` has no production caller. It was frozen by `wiring_investigate_before_acting` (2026-07-08) because its dependency (the W3 registry) was missing.
- **Not a watcher-of-watchers.** It dispatches on doorbell rings; it does not monitor watcher health, re-arm dead watchers, or detect orphaned seats.
- **Not crash-proof.** If the dispatcher dies, doorbell notices go unhandled until restart. The safety net is the periodic boot peek (agents check on their own at session start), not the dispatcher itself.

### Is a supervised dispatcher the root fix?

**No.** The root causes of tonight's stalls are:

1. **Re-arm fragility** (the harness constraint) — the dispatcher cannot fix this because it CANNOT spawn a background task for a Claude session. Only the session itself can. The dispatcher could SEND A MESSAGE to the session ("you have mail, re-arm your watcher"), but the session can't receive it without a watcher — circular.

2. **Incarnation blindness** — the `frm == agent` filter is in `bifrost_wake.py:129`, not in the dispatcher. The dispatcher doesn't filter by sender at all; it dispatches by recipient.

3. **Noise-floor** — the dispatcher already has `should_escalate()` which is a coarse filter. But the real noise isn't at the doorbell level; it's in the wake loop itself (trace floods, legacy dual-write twins, self-frm gaps, skip-kind accumulation).

**What the dispatcher COULD become**: the W3 registry + a supervised dispatcher is the right architecture for a multi-runtime fleet. But it doesn't solve tonight's specific problems because:
- It can't re-arm a session's watcher (harness constraint)
- It can't fix the incarnation filter (that's in the watcher)
- It adds a new crash surface (who watches the dispatcher?)

**Verdict**: The dispatcher is a FUTURE architectural piece (W3), not tonight's fix. The fixes for tonight are in the watcher itself and the incarnation protocol.

### Who watches the watcher?

The janitor (`wake_seat.janitor()`, run at session-start) already watches watchers — it reaps dead seats, migrates legacy ghosts (K6), and detects orphans (K7/K8). It runs at session start, which is exactly the wrong cadence for a watcher that dies MID-session. Options:

1. **Periodic janitor** (a daemon that runs every N minutes, not just at session start) — watches all seats, reaps dead ones, and NOTIFIES the owning session (via a doorbell notice that the session will see on its next natural wake). Cannot re-arm (harness constraint).
2. **Heartbeat-based liveness** (watcher writes a heartbeat every M seconds to its seat file; janitor detects stall when heartbeat goes stale) — already partially done (K7 activity marker), but the marker is written by the STOP HOOK, not the watcher. An idle session's marker goes stale even though the session is alive.
3. **Self-healing watcher** — the watcher itself detects its own impending death (deadline approaching) and re-arms a successor BEFORE exiting. This is the `arm-zero` path below.

---

## (c) Wake = work: the noise-floor design

### What guarantees a seat NEVER fires without actionable mail?

The current filter chain in `bifrost_wake.py:watch()`:

```
1. wake_block() returns messages (detect-only, local cursor)
2. for each message:
   a. frm == agent → skip          ← INCARNATION BUG: skips twin-session mail
   b. kind in SKIP_KINDS → skip    ← correct: trace/steer/resolved/ledger_update never wake
   c. kind == reply AND to == * → skip  ← correct: broadcast replies are room chatter
   d. everything else → WAKE
```

Plus the lane-mode `_wake_block_lane()` arm-time check:
```
- pending = bus.wait(timeout_ms=1, limit=10)  ← peek shared cursor
- filter out PENDING_SKIP_KINDS                ← skip trace/steer/resolved/ledger_update/note/status
- if anything wake-worthy remains → WAKE immediately
```

### The noise sources that STILL cause false wakes

| Noise | Mechanism | Fix status |
|-------|-----------|------------|
| Legacy dual-write twins | Same message on work lane AND legacy; lane-mode dedup drops legacy twin at consume, but watcher sees BOTH | T047 (strangle dual-write) removes the class |
| Self-frm incarnation mail | `frm == agent` skips ALL same-agent mail, including twin-session handoffs | **Fix in (a) above** |
| Trace flood hiding one handoff | 1280 bc traces + 1 handoff → watcher wades ALL of them every time | T045 lane-mode wake removes the class (lane has no trace flood) |
| Steer accumulation | Steers are skipped but COUNTED; they still consume wake_block iterations | Lane-mode: steers ride the work lane, not legacy bc |
| Stale legacy cursor | bc cursor never advances for session agents → same messages re-detected forever | T045 lane-mode: watcher watches lane, not legacy bc |

### The noise-floor guarantee (design)

**L1 — Lane-only wake.** When `BIFROST_WAKE_LANE=work`, the watcher reads ONLY the work lane. Trace/sig floods, legacy dual-write twins, and stranded broadcast junk are structurally invisible. This is already SHIPPED (T045 stage 1). The lane carries only `kind ∈ {chat, note, request, handoff, reply, steer, completion, blocker, question}` — no firehose kinds.

**L2 — Incarnation-stamped skip.** `frm_incarnation == my_incarnation → skip` (true echo). `frm_agent == my_agent AND frm_incarnation != my_incarnation → deliver` (incarnation mail). This single change fixes the twin-wake impossible.

**L3 — Wake-worthy kind allowlist (invert the skip list).** Instead of skipping known-noise kinds, ALLOW only known-wake-worthy kinds: `{request, handoff, reply, blocker, question, completion}`. Everything else is noise. A new kind added to the system is silent-by-default until explicitly added to the allowlist. This is the "ratchet" equivalent of the T067-1 check_door_parity approach — a new kind cannot accidentally wake agents.

**L4 — Directed-only replies.** Already correct: `kind == reply AND to == *` is skipped. Only `to == <specific agent>` replies wake.

**L5 — Post-wake dedup.** After the watcher fires and the session consumes, the NEXT arm seeds past the consumed messages (consume-then-arm discipline, `wake_consume_then_arm`). Already practiced, not automated.

**Combined filter (single pass, in order):**
```
1. kind not in WAKE_WORTHY_KINDS → skip       (L3: allowlist)
2. kind == reply AND to == * → skip            (L4: broadcast replies)
3. frm_incarnation == my_incarnation → skip    (L2a: echo)
4. frm_agent == my_agent AND frm_incarnation != my_incarnation → DELIVER  (L2b: incarnation mail)
5. frm_agent != my_agent → DELIVER             (cross-agent mail)
```

---

## (d) Arm-zero: designs where NO session ever manually arms anything

### The harness constraint, precisely stated

The Claude Code harness has exactly ONE mechanism for a background process to wake an idle session: the session launches a `run_in_background` task, and when that task completes, the harness re-invokes the session. Hook-spawned processes (SessionStart, Stop, PreToolUse, etc.) are NOT background tasks — they are synchronous subprocess calls whose output is consumed by the hook system, not the session scheduler.

Therefore: **any solution that requires an external process to wake the session MUST be launched BY the session as a background task.** The stop hook can block and teach, but cannot launch.

### Arm-zero designs, ranked by feasibility

**Design 1: Self-re-arming watcher (FEASIBLE, LOW RISK)**

The watcher, before exiting (deadline reached, mail found), spawns its OWN successor as a background task. The mechanism:
- `bifrost_wake.py` already exits when it finds mail or hits its deadline
- Before exit, it writes a "re-arm" instruction to a well-known temp file
- The session, on its NEXT turn (which just started because the watcher's completion woke it), reads the instruction and the FIRST action is to re-launch the watcher
- This is a CONVENTION, not a mechanism — the model must still do it
- BUT: combined with the stop-hook enforcement, the session cannot stop without a watcher armed, so the re-arm becomes inevitable

**Problem**: Still requires model cooperation on the intake turn. If the model ignores the re-arm instruction and does work instead, the session is unwakeable until the next stop.

**Design 2: Watcher-as-daemon (FEASIBLE, MEDIUM RISK)**

Instead of a per-turn watcher that exits, run ONE long-lived watcher daemon per session. The daemon:
- Launched at session start (SessionStart hook, or the session's first background task)
- Holds a per-session seat file
- Runs until the session ends (detected via activity marker staleness + parent chain dead — K7/K8 logic)
- On each wake-worthy message, writes to a "wake trigger" file that the session's next turn reads
- The session polls the trigger file at turn start (or the boot whisper includes it)

**Problem**: "Launched at session start" — the SessionStart hook CAN launch a process, but that process is NOT a background task. Its completion does NOT re-invoke the session. So the daemon must use a DIFFERENT wake mechanism: write a file that the session's boot context reads, or send a Bifrost message to the session's inbox (which the session reads on its next natural turn). This is "poll-at-boot," not "wake-from-idle."

**Design 3: Never-exit watcher with periodic self-check (FEASIBLE, MEDIUM RISK)**

The watcher runs as a `run_in_background` task with a VERY long deadline (hours). It loops internally:
- Block on the lane for N minutes
- If mail arrives → exit (waking the session)
- If deadline approaches → exit AND write re-arm trigger → session wakes, re-arms, continues
- If seat lost → exit (session died or another watcher took over)

This is essentially Design 1 with the deadline extended to "whole session." The watcher stays alive for the session's duration, re-arming is needed only if it exits (mail found, deadline truly reached, or session restart).

**Problem**: A background task with an hours-long deadline might be killed by the harness (resource limits, session pause/resume). The seat file + janitor provides crash-safety.

**Design 4: Harness-patch: hook-spawned background task (NOT FEASIBLE under current harness)**

If the harness allowed hooks to register background tasks (not just the session), the stop hook could directly arm the watcher. This requires a harness change, which is outside our control.

**Design 5: External supervisor with harness-independent wake (FEASIBLE, HIGH EFFORT)**

A supervisor process (the launcher, or a new daemon) watches all sessions and, when mail arrives for an idle session, uses a harness-specific mechanism to wake it:
- For Claude Desktop: send a custom HTTP request to the local server? (Doesn't exist)
- For Claude CLI: send a signal? (No signal-to-wake mapping)
- For runners: already self-waking

This requires harness APIs that don't exist.

### Recommended path: Design 3 (long-lived watcher) + Design 1 (self-re-arm) as fallback

**Primary**: The watcher is launched ONCE per session (at first stop or session start) with a 4-hour deadline. It blocks on the lane in 120s chunks. Mail → exit → session wakes. Near deadline → exit + re-arm trigger → session wakes and re-launches.

**Fallback**: If the watcher dies (crash, harness kill, seat loss), the stop hook detects `wake_armed() == False` and blocks — exactly as today. The model re-arms. The difference is this happens rarely (only on watcher death), not every turn.

**Migration**: The stop-hook block becomes a BACKSTOP, not the primary path. The `arm_cmd` text in the block message changes from "launch this every turn" to "your watcher died — re-launch it once."

---

## (e) Pins + migration path

### Pins (acceptance tests)

| Pin | What | How to verify |
|-----|------|---------------|
| P1 | Incarnation filter: twin sessions wake each other | Two claude sessions, session A sends handoff to session B. Session B's watcher fires. |
| P2 | Incarnation filter: self-echo still suppressed | Session sends a message; its own watcher does NOT fire on it. |
| P3 | Incarnation filter: cross-agent mail still delivered | Deepseek sends handoff to claude; claude's watcher fires. |
| P4 | Wake-worthy allowlist: new unknown kind does NOT wake | Add a `kind=zz_test` message; watcher stays quiet. |
| P5 | Wake-worthy allowlist: known kind DOES wake | `kind=request` message; watcher fires. |
| P6 | Lane-only wake: trace flood invisible | 1000 trace messages on legacy bc + 1 handoff on work lane; watcher fires ONCE on the handoff. |
| P7 | Long-lived watcher: survives 30+ min without re-arm | Launch watcher with 4h deadline; check seat file PID alive after 30 min. |
| P8 | Self-re-arm: watcher near-deadline exit writes trigger | Set deadline to 30s; watcher exits; trigger file exists with re-arm instruction. |
| P9 | Stop-hook backstop: dead watcher blocks stop | Kill watcher; session tries to stop; hook blocks with re-arm message. |
| P10 | Incarnation stamp on send: frm_incarnation in meta | Send any message; `bifrost-sync --consume` shows `meta.frm_incarnation` set. |
| P11 | Directed incarnation addressing: to_incarnation routes to ONE session | Two sessions; send with `to_incarnation=sid1`; only session 1's watcher fires. |
| P12 | No regression: existing lane-mode wake still works | Existing T045 pins still green. |

### Migration path (strangler, T045 pattern)

**Phase 1 — Incarnation filter fix (smallest, highest-impact)**
- Add `frm_incarnation` to `Bus.send()` / `bus.send_reply()` meta
- Change `bifrost_wake.py:129` from `frm == agent` to incarnation-aware check
- Pin: P1, P2, P3, P10
- Files: `core/comm/bus.py`, `scripts/bifrost_wake.py`
- This ALONE fixes tonight's twin-wake impossible

**Phase 2 — Wake-worthy allowlist (ratchet the noise floor)**
- Define `WAKE_WORTHY_KINDS` in `bifrost_wake.py`
- Replace `SKIP_KINDS` skip logic with `kind in WAKE_WORTHY_KINDS` allow logic
- Pin: P4, P5
- Files: `scripts/bifrost_wake.py`
- This guarantees new kinds are silent-by-default

**Phase 3 — Long-lived watcher (arm-zero primary path)**
- Add `--deadline` support for 4-hour runs to `bifrost_wake.py`
- Add near-deadline self-re-arm trigger (write trigger file, exit clean)
- Update stop hook message from "arm every turn" to "your watcher died — re-arm once"
- Pin: P7, P8, P9
- Files: `scripts/bifrost_wake.py`, `scripts/hooks/claude_stop.py`

**Phase 4 — Directed incarnation addressing (optimization)**
- Add `to_incarnation` to send meta
- Wake filter checks `to_incarnation` when present
- Pin: P11
- Files: `core/comm/bus.py`, `scripts/bifrost_wake.py`

**Phase 5 — Dispatcher W3 wiring (future arc, not tonight)**
- Build the W3 invoker registry
- Wire `Dispatcher.run()` as a supervised daemon
- Doorbell notices → dispatcher → invoker → per-runtime wake
- This is the multi-runtime fleet architecture; not needed for the current two-participant system

### What we do NOT do

- **Do NOT wire the Dispatcher now.** Its dependency (W3 registry) doesn't exist. Wiring it without the registry is fake integration. The incarnation fix + allowlist + long-lived watcher solve tonight's problems without it.
- **Do NOT change the harness.** We cannot. The harness constraint is a given. We work within it.
- **Do NOT remove the stop-hook block.** It becomes a backstop, not the primary path. Removing it removes the safety net.
- **Do NOT touch the runner's consume loop.** Runners don't have the re-arm problem. They don't use `bifrost_wake.py` at all (they use `bus.wait()` inline). The incarnation filter is the only change that affects them.

### Files touched (Phase 1-3)

```
core/comm/bus.py              — frm_incarnation in send/send_reply meta
scripts/bifrost_wake.py        — incarnation-aware filter, allowlist, long-lived mode, self-re-arm
scripts/hooks/claude_stop.py   — updated block message (backstop, not primary)
tests/test_t073_wake_incarnation.py  — P1-P5, P10
tests/test_t073_wake_longlived.py    — P7-P9
```

Estimated: ~120 lines across 3 production files + ~150 lines of pins.
