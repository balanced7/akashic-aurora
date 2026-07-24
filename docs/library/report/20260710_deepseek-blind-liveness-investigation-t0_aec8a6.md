---
akashic_id: art_20260710_deepseek-blind-liveness-investigation-t0_aec8a6
akashic_sha: 89b9b3d64af7
status: draft
type: report
date: 2026-07-10
title: "DeepSeek blind liveness investigation -- T030 (verbatim, committed by claude)"
gist: "# DeepSeek blind liveness investigation -- T030 (verbatim, committed by claude) Provenance: bus msg 1783732340971-0, 2026-07-10; his runner "
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79
    rel: cites
created: "2026-07-10T21:18:27"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260710_deepseek-blind-liveness-investigation-t0_aec8a6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek blind liveness investigation -- T030 (verbatim, committed by claude)

# DeepSeek blind liveness investigation -- T030 (verbatim, committed by claude)

Provenance: bus msg 1783732340971-0, 2026-07-10; his runner is write-gated so claude persists it.
Fence held: forensics doc + own code-read only; no access to docs/agent-liveness-tier-2026-07.md.

Here is the complete blind investigation.

---

## DeepSeek Liveness Investigation — T030 (BLIND, fenced)

**Date**: 2026-07-10  
**Reviewer**: deepseek  
**Method**: code-read of all 5 source files + forensics document. No access to `docs/agent-liveness-tier-2026-07.md`.

---

### 1. EVERY FAILURE MODE (including modes the incident did NOT hit)

I classify by WHERE the agent is in the consume→process→reply pipeline when death/wedge strikes.

---

#### CLASS A: Message consumed (cursor advanced), agent dies before reply — THE INCIDENT

**Root mechanism**: `bus.wait(advance=True)` at `bifrost_runner_deepseek.py:502` moves the shared inbox cursor BEFORE `_process_one()` runs. Death in the window between them = message consumed by one process, answered by none.

| Mode | Where in pipeline | How triggered |
|------|-------------------|---------------|
| **A1** | Between `wait(advance=True)` and `_process_one()` start | Pipe kill (the incident — stdout write 31 triggers `Select-Object -First 30` SIGPIPE/SIGTERM), OOM killer, `kill -9`, power loss |
| **A2** | Inside `_process_one()`, after phase flip to "handling" (line 329) but before `bus.send()` reply (line 354) | Same as A1; also: Python segfault, C extension crash, disk-full during logging |
| **A3** | After replying to message N but before message N+1 in same batch | Multi-message batch: cursor advances past entire batch; death mid-batch loses N+1..end |
| **A4** | REPLY_TIMEOUT_SEC (600s) fires — worker thread abandoned, error reply sent | NOT a loss: error string is sent. But handoff is deliberately NOT auto-acked on error replies (line 383: `answered_ok = finished and ... and not out.startswith("(deepseek")`) — correct behavior |
| **A5** | Model API error mid-stream caught by `_call()` → error reply sent | NOT a loss; same as A4 |

**Current detection**: P6 ack tier — `promoted()` with `with_acks=True` + `now` shows `unhandled=True` after `DIRECTED_UNHANDLED_HOURS=2` (or 6 for broadcasts). **Timescale: hours.**  
**Current healing**: **None.** No redelivery. Human re-sends.  
**The incident was A1** (pipe kill on the `print("<- ...")` at line 318, after cursor advance, before reply).

---

#### CLASS B: Agent wedged — process alive, loop stuck

| Mode | Mechanism | Detection | Timescale |
|------|-----------|-----------|-----------|
| **B1** | Model API call hangs beyond L0 socket timeout. Worker thread stuck in `client.chat.completions.create()`. Main loop blocked in `worker_done.wait(REPLY_TIMEOUT_SEC)` (line 347). | Worklive stuck in "handling" phase, `since_ts` ageing. `wedge_view().wedged=True` after 300s. | 300s → flagged; 600s → timeout reply |
| **B2** | Bus/Redis connection lost mid-session. `Bus._client` is live but broken. `_drain()` catches `ConnectionError` → returns `[]` (line 249 of bus.py). Runner spins: wait→[]→wait→[]. Heartbeat thread `except: pass` → presence expires (90s). Lock TTL expires (20s) but heartbeat returns True (fail-open) so runner loop never breaks. | Presence vanishes from roster after 90s. Worklive record expires after 45s (WORKLIVE_TTL). Agent is invisible but still running. | 45-90s |
| **B3** | `runner_lock.heartbeat()` returns False — another runner acquired the lock (lock expired during long GC pause, or deliberate takeover). Runner loop breaks (line 498). `finally` releases lock. | Runner logs "lost the singleton lock" and exits. In-flight message lost (Class A). | Immediate exit |
| **B4** | `control.is_halted()` = True — runner freezes in 0.4s sleep loop (line 501). Deliberate (pause). | Presence stays "online-but-frozen" (line 500: `bus.register()` refreshes). Deliberate. | Until human resumes |
| **B5** | stdout pipe full, no reader. `print()` at line 318 blocks → entire runner freezes mid-`_process_one`. Phase already flipped to "handling". Reply never sent. | Worklive stuck in "handling" > 300s. | 300s → wedge flag; message lost |
| **B6** | Rate-limit auto-pause (line 315-321). Runner pauses itself. Deliberate. | Bus note sent. | Until human resumes |

---

#### CLASS C: Runner starts, never picks up the message

| Mode | Mechanism | Detection | Timescale |
|------|-----------|-----------|-----------|
| **C1** | Runner v(N+1) starts AFTER cursor already past the message (the incident's v2). Cursor is shared state in Redis — advances with v1's `wait(advance=True)`, survives v2's restart. | P6 ack tier (hours). Runner v2 idles cleanly — worklive "idle", presence fresh, lock held, everything looks healthy. | Hours |
| **C2** | Runner starts but bus is offline → exits with code 2. Messages queue in Streams. | Runner exits immediately. | Immediate |
| **C3** | Runner starts but API key missing → exits with code 2. Same as C2. | Immediate exit. | Immediate |
| **C4** | Sender uses durable boot-lane verb (`agent_cli.py handoff`) → delivers to lane the LIVE runner never reads. Runner is running, healthy, idling. | P6 ack tier (hours). | Hours |

---

#### CLASS D: Transport-level loss (bus drops message before delivery)

| Mode | Mechanism | Detection | Timescale |
|------|-----------|-----------|-----------|
| **D1** | Stream maxlen eviction. Runner offline for long period; >10000 messages arrive; oldest messages (including a handoff) evicted. Cursor advances past evicted range on next consume. | P6 ack tier (hours) — handoff never delivered. | Hours |
| **D2** | Cursor corruption. Manual Redis edit, partial-persistence restart, or bug moves cursor past undelivered messages. | P6 ack tier. | Hours |
| **D3** | Broadcast never read. Runner's broadcast cursor advances past a broadcast message because `_drain` filters own-broadcasts and advances to last-read-id for "no truncation" path. Wait — re-reading... Actually the own-broadcast filter correctly skips delivery but the cursor does advance past filtered entries (line 270-271 of bus.py: `new_bc = sid` for every entry read, even filtered ones). So a filtered own-broadcast does NOT block cursor advancement for subsequent messages from others. This is correct — the T014 fix. | Not a failure mode; cursor logic is correct. |

---

#### CLASS E: Concurrency / two-runner race

| Mode | Mechanism | Detection | Timescale |
|------|-----------|-----------|-----------|
| **E1** | Runner lock TTL expires (GC pause > 20s). Second runner starts, acquires lock, both consume from same cursor. Race condition. | First runner detects lock loss on next heartbeat → exits. Second runner operates normally. Messages consumed during overlap window may be lost. | Sub-minute |
| **E2** | Two runners for DIFFERENT agent IDs but same inbox (misconfiguration). Cursor is keyed by agent_id — separate cursors, no conflict. | Not a failure. | N/A |

---

#### CLASS F: Worklive/presence false negatives (agent alive, reads dead)

| Mode | Mechanism | Detection problem |
|------|-----------|-------------------|
| **F1** | Presence expires while agent alive. Heartbeat thread's Redis ops fail (Redis down). Agent vanishes from roster. | Roster shows agent absent; agent is actually running. No message loss (messages queue in Stream). |
| **F2** | Worklive `wedged=True` on a legitimately long operation (5-min generation, long test suite). `wedge_view` docstring admits this ambiguity. | False wedge → if auto-revive is armed, kills a working agent. |

---

### 2. CURRENT DETECTION & HEALING — GAPS

| What | Today | Gap |
|------|-------|-----|
| Message consumed, unreplied | P6 ack tier: `unhandled=True` after 2-6 hours | **Hours latency**. The sender waits blind. |
| Process dead | Launcher monitor (2s poll) detects exit, classifies reason | Only when launched via launcher. Ad-hoc shell spawns unmonitored. |
| Process wedged in phase | Worklive `wedged=True` after 300s, auto-revive (if armed) | 300s granularity. No intra-phase progress signal. |
| Redelivery / retry | **Nothing** | Once cursor advances, message is gone. No consumer-group, no dead-letter, no re-read. |
| Sender-side timeout | **Nothing** | Sender has no way to say "I expect a reply within N seconds." |
| Heartbeat thread death | `beat_age` grows → `wedge_view` eventually flags it | 45s TTL on worklive. But the agent's own loop can't self-detect a dead heartbeat thread. |

---

### 3. FIX DESIGN — smallest reversible slices

#### RB-26: At-least-once inbox delivery (cursor-after-processing)

**What**: Move cursor advancement from BEFORE to AFTER successful reply. `bus.wait(advance=True)` becomes `bus.wait(advance=False)` (detect only), then advance the cursor explicitly after `bus.send()` succeeds. On crash/restart, the cursor still points BEFORE the message → redelivery.

**Seam**: `bifrost_runner_deepseek.py:502` (the `wait` call) + new per-message cursor-advance after line ~354 (after `bus.send`). The `advance=True` → `advance=False` swap + explicit `bus._write_cursor()` call.

**Kill-condition drill**: Launch runner → send handoff → kill runner mid-reply (SIGTERM after `wait` but before `bus.send`) → relaunch runner → **message is re-delivered and answered**. Today: message is lost (reproducible with the PowerShell pipe trick from the incident).

**Edge cases**:
- Crash AFTER reply but BEFORE cursor advance → message delivered TWICE (duplicate reply). Acceptable: at-least-once semantics; duplicate reply is better than silent loss. The sender sees two replies and deduplicates by message id.
- Multi-message batch: cursor advances ONLY for messages successfully replied to. Unreplied messages in the batch are re-delivered on restart.
- The cursor key is per-agent; other agents are unaffected.

**Not built**: Consumer groups (Redis consumer groups would require XACK and add complexity; cursor-after-processing is simpler and sufficient for a single-runner-per-agent model).

---

#### RB-27: L2 intra-phase progress pulse

**What**: A second, finer-grained heartbeat from the worker thread (not just the daemon heartbeat thread). Every ~1s during a model call, the worker touches a `bifrost:progress:<agent>` key (TTL 5s). The wedge detector reads it: if the agent is in "handling" phase AND the progress key is absent (worker thread dead/hung), it's a real wedge. If the progress key is fresh, the agent is genuinely working.

**Seam**: `_process_one`'s worker thread (line 341) pulses a progress key in a sub-loop. `liveness.wedge_view()` gains a `progress_age` field. Launcher's `_check_auto_revive()` already reads wedge_view — it automatically benefits.

**Kill-condition drill**: Start a model call with a 5-min runtime → poll `wedge_view` → `wedged=False` (progress key is fresh). Kill the worker thread (simulate hang) → after 5s, `wedged=True`. Today: both cases read `wedged=True` after 300s.

**Not built**: Streaming-progress integration with the model's own token stream. That's an optimization; a simple 1s pulse is the honest baseline.

---

#### RB-28: Sender-side delivery deadline + auto-redrive

**What**: A `bifrost-send` flag `--expect-reply-within N` (default 300s for handoffs). The sender's CLI polls for a reply (a bus message with `kind=reply` referencing the sent message id). If no reply within the deadline, the CLI auto-resends the message with a `[REDRIVE]` prefix and bumps a retry counter. After 3 redrives, it alerts the human and stops.

Additionally: a lightweight "read receipt" — when a runner finishes processing a handoff (auto-acks it via P6), the sender gets a durable notification. Today the sender has zero feedback until the ack tier fires hours later.

**Seam**: `agent_cli.py` bifrost-send path + `bus.wait()` with a `since` cursor tracking the expected reply. No runner changes needed — this is sender-side only.

**Kill-condition drill**: Send handoff → kill recipient runner before reply → sender auto-redrives at deadline → relaunched runner picks up redrive → reply arrives. Today: sender waits forever (or human re-sends manually minutes later, as in the incident).

**Not built**: Full transactional outbox pattern with guaranteed exactly-once delivery. Overengineered for a 2-agent fleet.

---

#### RB-29: Non-blocking stdout + pipe-kill immunity

**What**: At runner startup, install a SIGPIPE handler that catches the signal and logs it rather than dying. On Windows (`Select-Object -First N` kills the process via pipe termination, not SIGPIPE), wrap `sys.stdout` in a wrapper that catches `BrokenPipeError` / `OSError` on write and degrades to `os.devnull`. The runner survives any pipe configuration.

**Seam**: `bifrost_runner_deepseek.py` main(), before the loop. ~5 lines.

**Kill-condition drill**: `py scripts/bifrost_runner_deepseek.py --agentic 2>&1 | Select-Object -First 5` → runner survives the pipe kill and continues processing (just with no stdout). Today: dies on the 5+Nth print.

**Not built**: Full syslog/journald integration. stdout is the runner's log; making it kill-proof is sufficient.

---

### 4. WHAT I WOULD NOT BUILD (and why)

1. **Consumer groups (Redis XREADGROUP/XACK)** — Overengineered for a single-runner-per-agent model. The cursor-after-processing approach (RB-26) gives at-least-once without consumer-group complexity, pending-ack lists, or idle-consumer reclamation. Consumer groups matter when you have N competing consumers on one stream (horizontal scaling); we have exactly one runner per agent.

2. **Dead-letter queue** — A DLQ is the right pattern when you want to isolate poison messages that crash the handler. Our messages are plain text handoffs/requests with no schema; a "poison message" doesn't exist. If the runner crashes on a message, it'll crash on every message — the problem is the runner, not the message. Fix the runner (RB-28 redrive + RB-29 pipe-kill immunity handle this).

3. **Heartbeat thread self-monitor** — A watchdog thread watching the heartbeat thread watching the main loop. The heartbeat thread is a 5-line `while not stop.wait(5): try...except` loop. It can't crash permanently (every iteration is independent). The failure mode is "Redis is down" which has its own signals (presence expires). Adding a watcher-of-watchers adds complexity for a mode that's already detectable.

4. **Signed bus identity for at-least-once** — RB-1/RB-2 already name signed identity as the honest bound. Adding it as a dependency for RB-26 would couple the liveness fix to an auth system that doesn't exist yet. RB-26 works with the same trust model as today.

5. **Per-message phase tracking in worklive** — Tracking individual message IDs through the pipeline would give perfect per-message observability, but at the cost of a Redis write per message per phase transition. For a 1000-message burst, that's 3000 Redis ops. RB-27's progress pulse gives the wedge/non-wedge distinction with constant overhead.

---

**Top 3 findings, one-line each**:

1. **The cursor advances before processing — this is the single root cause**: every message-loss mode (death, wedge, lock-theft, pipe-kill) shares the same shape: `wait(advance=True)` moves the cursor, then the agent dies before replying, and the message is gone forever because no redelivery path exists.

2. **Every liveness signal the forensics checked is a LAGGING indicator**: presence/singleton lock refresh from an independent daemon thread (by design, survives main-loop wedge), worklive showed "idle" (v1 died before phase flip, v2 never flips), CPU showed zero (genuinely idle). All true, all useless for detecting the consume-then-die window. The ONLY signal that would have caught it is the P6 ack tier — at 2-hour granularity.

3. **The incident would have been a non-event with three lines of code**: `advance=True` → `advance=False` on the wait call + explicit cursor advance after successful reply (RB-26). The runner v2 would have seen the handoff on its first poll cycle and answered it. No architecture, no new Redis keys, no protocol changes — just swapping the order of two operations that are already adjacent.

---

Full investigation text ready for commit. My runner's `--allow-write` is gated off; deliver the file content via bus or start me with `--allow-write` and I'll write `research/reviewed/deepseek-liveness-invest-2026-07-10.md`.
