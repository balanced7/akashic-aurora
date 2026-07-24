---
akashic_id: art_20260717_t093-crash-path-analysis-deepseek-indepe_6e9d21
akashic_sha: a8c1f2927254
status: draft
type: design
date: 2026-07-17
title: T093 Crash-Path Analysis — DeepSeek Independent Half — 2026-07-17
gist: "*Renamed from T091 → T093 per codex_root steer: T091 already = packet-routing wave; T092 = reasoning spine. T093 = crash-path durable long-j"
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-17T09:29:32"
updated: "2026-07-17T09:29:32"
---
<!-- GENERATED PROJECTION of art_20260717_t093-crash-path-analysis-deepseek-indepe_6e9d21 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T093 Crash-Path Analysis — DeepSeek Independent Half — 2026-07-17

*Renamed from T091 → T093 per codex_root steer: T091 already = packet-routing wave; T092 = reasoning spine. T093 = crash-path durable long-job supervision.*

## 0. Directive

T093 as assigned: *"Crash-path durable long-job supervision: eliminate yielded exec-cell as sole completion path using out-of-band deadline. Same failure evidence: ship.py in yielded cell 376; fifth 30s wait at 03:38:09 ET never returned and outer 20m timeout never surfaced; recovery restarted app-server only at 07:30:45; no native crash/Crashpad/OOM; full pytest receipt lost. Trace repo-native process lifecycle and identify how to remove dependence on an in-memory exec cell: durable stdout/stderr, pid/heartbeat/result receipt, independent deadline, cancel/quiesce semantics, restart recovery. Compare nearest working runners/wake scripts. Return smallest patch surface, RED tests/kill drills, and risks; do not edit until reconciliation."*

## 1. Evidence Chain

Source: `session_logs/ledger/events_codex_root_raw.jsonl`, event #18, `learn:experiment:codex_wait_cell_lost_completion`.

### 1.1 Timeline

| Time (ET) | Event |
|---|---|
| 03:35:36 | `ship.py` launched from yielded Codex exec cell 376 with `timeout_ms=1200000` (20 min). Polling started: 30-second `wait` calls |
| 03:35:36–03:38:09 | Four `wait` calls returned normally. The pytest suite was running |
| 03:38:09 | Fifth `wait` call issued. It **never produced a `function_call_output`** |
| 03:38:09–07:30:45 | Turn wedged for **3 hours 52 minutes 36 seconds**. The outer 20-minute shell timeout **also never surfaced** |
| 07:30:45 | UI recovery: only `codex.exe` app-server restarted. No Windows Application Error, Reliability record, WER/Crashpad dump, native UI-process restart, OOM condition, commit, or repo data loss |

### 1.2 What was lost

- Full pytest suite result: **unknowable**. `ship.py` emitted no durable progress receipt before its process tree was canceled.
- The pytest output (which gate passed, which failed, at which test) is irrecoverable.
- The ~3h52m gap represents unknown system state — was `ship.py` still running? Hung in a specific test? Killed by something? The answer is permanently unknowable.

### 1.3 Root cause

The in-memory yielded exec cell was the **sole completion path** for a 10+ minute monolithic gate. When the cell's internal communication channel died (or the process that owned it), there was:

- **No independent deadline** — the only timeout was on the dead channel
- **No durable stdout/stderr** — all output was in the cell's memory, lost with the channel
- **No PID/heartbeat** — the caller had zero visibility into whether the child process still existed
- **No result receipt** — when the channel died, the outcome became permanently unknowable

## 2. Process Lifecycle Audit: What Exists vs. What ship.py Needs

### 2.1 Capability Matrix

| Property | bifrost_runner_deepseek.py | bifrost_daemon.py | bifrost_child.py (ManagedChild) | ship.py (TODAY) |
|---|---|---|---|---|
| Durable stdout/stderr | ✅ Ring buffer (drainer thread, `_RING_LINES=200`) + trace bus | ✅ Daemon prints + child stdout ring | ✅ Bounded ring buffer + `on_exit(code, tail)` callback | ❌ **Nothing** — all output in `subprocess.run` capture, lost on channel death |
| Independent deadline | ✅ `REPLY_TIMEOUT_SEC` (600s) via `threading.Event.wait` + `BusLossGuard` | ✅ `max_runtime` hatch + bus-loss guard with `guard_every` probes | ✅ Non-blocking poll (`_next_spawn_at` timestamp, never `sleep()` inside tick) + circuit breaker (3 crashes / 300s) | ❌ **Nothing** — only the caller's timeout on the dead channel |
| PID / heartbeat | ✅ Runner lock heartbeat (5s, independent daemon thread) + `worklive` pulse + `PULSE_GEN` fencing | ✅ `DaemonLock.heartbeat()` with F5 nx-reclaim + card registration at every beat | ✅ `ManagedChild.pid` property + `alive` property (`.poll()` is None) + `spawn()` only when backoff elapsed | ❌ **Nothing** |
| Result receipt | ✅ Turn metrics to Redis + exit summary JSON (`_write_exit_summary`) + `_RUN_STATS` | ✅ Card `runtimes` field (child state of every managed child) + blocker broadcast + pager escalation | ✅ `last_summary` dict + `on_exit` callback + `format_summary_for_prompt` | ❌ **Nothing** |
| Cancel / quiesce | ✅ SIGINT/SIGBREAK handler → `finally` block releases lock + writes exit summary | ✅ SIGINT/SIGBREAK/SIGTERM handler → `_STOP` flag → `child.terminate()` → `dlock.release()` | ✅ `terminate()` with SIGTERM → 5s wait → SIGKILL → 3s wait | ❌ **Nothing** — SIGTERM kills the process; no receipt, no quiesce |
| Restart recovery | ✅ `_reply_already_sent` sentinel (Redis + durable store) + `_mark_reply_sent` + RB-26 cursor discipline | ✅ `_stable_token` (survives daemon restart) + summary injection (`--inject-summary`) + `on_exit` reads `last_summary` for the next child | ✅ Circuit breaker auto-reset on daemon restart + N1 benign-exit-is-handover (exit 0 = no auto-respawn) | ❌ **Nothing** — every crash is a cold start |

### 2.2 Key Insight: The Machinery Already Exists

The project has already solved this problem **three times over** in its own runners. The gap is that `ship.py` is a monolithic gate, not a runner, and inherits none of the infrastructure. The fix is not building new primitives — it's **connecting `ship.py` to the existing ones**.

## 3. Smallest Patch Surface

Three files, approximately 40 lines of new code. Every addition is opt-in via flags (`--log`, `--receipt`); the zero-flag path is byte-identical to today.

### 3.1 `scripts/ship.py` — Three additions (~25 lines)

#### A. `--log FILE` flag: durable progress log

```python
# In build_plan / _run: before each gate step, write to the log file.
# Line-buffered; fsync'd at each gate boundary.
# If the process is kill-9'd, the log survives up to the last fsync'd line.
_LOG_FP = None  # set in main() when --log is passed

def _run(label, cmd):
    if _LOG_FP:
        _LOG_FP.write(f"{time.strftime('%H:%M:%S')} START {label}: {' '.join(cmd)}\n")
        _LOG_FP.flush()
    print(f"\n=== {label} ===")
    ok = subprocess.run(cmd, cwd=ROOT).returncode == 0
    if _LOG_FP:
        _LOG_FP.write(f"{time.strftime('%H:%M:%S')} {'OK' if ok else 'FAIL'} {label}\n")
        _LOG_FP.flush()
    return ok
```

#### B. `--receipt FILE` flag: result receipt

```python
# ship.py writes a JSON receipt at exit. Three writes:
#   1. AT START: {"pid": ..., "started": ..., "status": "running"}
#   2. (optional) HEARTBEAT: update "last_gate" / "last_beat" every N seconds
#      via a signal-handler-driven daemon thread (same pattern as the runner's
#      heartbeat thread — 5 lines)
#   3. AT EXIT: {"exit_code": ..., "verdict": "ok|fail|timeout|killed",
#                "gates": [...], "log_tail": [...]}
#
# Atomic write: tmpfile + os.replace() — no torn file on kill-9
# (same pattern as _stable_token in bifrost_daemon.py).

# The receipt file is the ONE source of truth the caller watches,
# independent of the cell/pipe/channel.
```

#### C. SIGTERM handler: killed receipt

```python
# In main(), install a signal handler that:
#   1. Sets a _KILLED flag
#   2. Writes the receipt with verdict="killed" + log tail
#   3. Re-raises to let the default handler terminate the process
# This converts "mystery death" into "definitive outcome."
```

### 3.2 `tests/test_t093_crash_path.py` — Four kill drills (~15 lines each)

Pre-registered RED tests: must FAIL before the fix, PASS after.

#### D1 — Kill-9 receipt survives

```
Start: ship.py --receipt <tmpfile> --dry-run
Action: os.kill(pid, signal.SIGKILL) after 0.5s
Assert: receipt file exists on disk
Assert: receipt["verdict"] == "killed"
Assert: receipt["log_tail"] is non-empty list
Today: FAIL (no receipt file at all)
```

#### D2 — Hung-child independent deadline

```
Start: ship.py --receipt <tmpfile> with a fake gate that sleeps 999s
Action: Wait 3s, then os.kill(pid, signal.SIGTERM)
Assert: receipt["verdict"] in ("timeout", "killed")
Assert: receipt["gates"][-1] names the hung gate
Today: FAIL (hangs until the outer timeout on a potentially dead channel)
```

#### D3 — Pipe-death log survival

```
Start: ship.py --log <logfile> --dry-run in a subprocess
Action: Close the subprocess's stdout pipe (simulate dead cell channel)
Action: Wait 2s, then kill the process
Assert: log file on disk contains at least the first gate label
Assert: log file is valid UTF-8 text
Today: FAIL (no log file)
```

#### D4 — Torn-file immunity

```
Start: ship.py --receipt <tmpfile> --dry-run
Action: Kill -9 mid-execution (repeat 20x to surface torn writes)
Assert: Every receipt file is either absent (pre-first-write) OR valid JSON
Assert: Zero torn/partial files
Today: N/A (no receipt file)
Mechanism: write to tmpfile + os.replace() (same pattern as
           _stable_token in bifrost_daemon.py)
```

### 3.3 `scripts/bifrost_child.py` — Extract `pipe_watcher()` (optional stretch, ~10 lines)

If the drainer thread pattern in `ManagedChild.__init__` is extracted into a standalone `pipe_watcher(path, ring_size=200)` function, `ship.py --log` can call it directly instead of reimplementing the ring buffer. This is a refactor, not new behavior — deferrable to a follow-up slice.

## 4. Nearest Working Runners (patterns to borrow)

| Source | Pattern | Applicability to ship.py |
|---|---|---|
| `bifrost_child.py:ManagedChild` | **Drainer thread** (F1): reads `proc.stdout` line-by-line into bounded ring buffer. Pipe never fills; child never blocks on print. `on_exit(code, tail)` callback receives ring contents. | `ship.py --log` uses the same pattern: open a file, write each line, fsync at gate boundaries. A pipe watcher isn't needed for a one-shot gate — the file IS the ring buffer. |
| `bifrost_child.py:ManagedChild` | **Non-blocking poll** (F2): `_next_spawn_at` timestamp stored; `spawn()` checks `time.time() >= _next_spawn_at`. No `sleep()` inside the daemon tick. Circuit breaker (3 crashes / 300s → trip). | `ship.py` doesn't need backoff (it's one-shot), but the **circuit breaker pattern** is relevant: if `ship.py` is called repeatedly and fails 3 times, stop trying and escalate. |
| `bifrost_runner_deepseek.py:_process_one` | **Wall-clock timeout**: `threading.Event.wait(timeout=REPLY_TIMEOUT_SEC)`. The API client's own socket timeout is L0; this is L1. Independent, non-cancellable by a hung stream. | `ship.py --receipt` enables the CALLER to use the same pattern: poll the receipt file with an independent timeout, kill the child if the receipt goes stale. The timeout lives OUTSIDE the cell/channel. |
| `bifrost_runner_deepseek.py:_write_exit_summary` | **Exit summary**: `json.dump({"exit_code": ..., "turns": ..., "verdict": ..., "timestamp": ...})` to a file. Fail-silent. | Directly applicable: `ship.py --receipt` writes the same shape. |
| `bifrost_daemon.py:_on_runner_exit` | **Exit hook**: reads `child.last_summary` from the receipt file, formats it for the card, logs it. The daemon never reads the child's stdout pipe directly. | The CALLER of ship.py should watch the receipt file, not the stdout pipe. Same pattern. |
| `bifrost_daemon.py:_stable_token` | **Atomic write**: `tmp + os.replace()` → no torn files even on kill-9. | `ship.py --receipt` uses the same pattern for the receipt file. |
| `core/comm/runner_lock.py:free_if_dead` | **Evidence ladder**: activity marker → listener pid → staleness. Multiple independent signals; every ambiguity resolves toward ALIVE. | The caller's poll of the receipt file is the same pattern: receipt age < grace → alive; receipt age > stale with no heartbeat → dead; no receipt at all → not started yet. |
| `core/comm/session_exit.py:clean_death` | **Tombstone first**: write the durable "this ended" fact BEFORE releasing locks. Even a mid-trio crash leaves the discriminator. | `ship.py --receipt` writes "running" at start BEFORE any gate runs. If the process dies, the receipt shows it was mid-flight, not never-started. |

## 5. Cancel/Quiesce Semantics

### Current state
`ship.py` runs as `subprocess.run(cmd).returncode`. The only cancel path is SIGTERM/SIGKILL from the parent. No quiesce, no receipt.

### Proposed state
Three-tier cancel:

1. **SIGTERM** → signal handler writes `{"verdict": "killed", "killed_at": "..."}` to the receipt file. The currently-running gate step's subprocess also receives SIGTERM. The handler then re-raises for default termination.

2. **SIGKILL** → no handler possible. The receipt file on disk has the last state before the kill. The log file has the last gate boundary. Combined, the caller knows "it was killed during gate X."

3. **Deadline exceeded** (caller-side) → the watcher polls the receipt file; sees `last_beat` older than deadline → sends SIGTERM → waits grace → sends SIGKILL → reads final receipt. The receipt shows `verdict: "timeout"` if the SIGTERM handler wrote it, or `verdict: "killed"` if SIGKILL was necessary.

### Restart recovery
`ship.py` is idempotent by nature (it gates, commits, pushes). A restart re-runs the full suite. The receipt file tells the caller whether the previous run succeeded, failed, or was killed — no guessing. The `--log` file shows exactly how far the previous run got.

## 6. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `ship.py` is already a monolithic gate; more flags make it heavier | Low | Both `--log` and `--receipt` are opt-in. The zero-flag path is byte-identical to today. The additions are ~25 lines total. |
| The receipt watcher itself could hang | Low | The watcher is a 30-line poll loop (same pattern as `ManagedChild.poll()`, proven in production for weeks). Its timeout is independent of the child. If the watcher hangs, the outer deadline (the daemon/caller's own timeout) still fires. |
| Fragmentation: `ship.py` grows toward an ad-hoc runner | Medium | Bounded by design: `ship.py` stays a one-shot gate. If the receipt/log additions grow beyond ~50 lines, extract into a reusable `scripts/gate_runner.py`. The extraction is mechanical — file copy, not redesign. |
| The real fix should be in the Codex cell/exec layer, not `ship.py` | Medium | Agreed, but `ship.py` is what we control. `codex_wait_cell_lost_completion`'s own recommendation is: *"don't use an in-memory yielded cell as the only completion path for a long monolithic gate."* The receipt file is the escape hatch for ANY tool runner, not just ship.py. When the cell layer gains durable receipts, `ship.py`'s receipt file feeds into it. |
| Teaches the wrong lesson: "add receipts to everything" | Low | The fix is surgical — `ship.py` because it's the longest-running, highest-stakes gate. Not every `subprocess.run` call needs a receipt. The pattern is documented here; future gates adopt it by copying the `--receipt` flag. |
| Duplicates work with Fable's half | Low | By design: both halves are independent. Reconciliation identifies convergent findings (both likely land on "durable receipt file" and "independent deadline") and divergent ones (implementation details, scope, sequencing). The T093 directive says "NO EDITS until sync." |

## 7. What Must NOT Be Built (Contraindications)

1. **Do NOT turn ship.py into a daemon.** It's a one-shot gate. Adding a heartbeat thread or a long-lived poll loop inside `ship.py` is over-engineering. The receipt file provides observability; the CALLER provides the poll loop.

2. **Do NOT add Redis dependency to ship.py.** The receipt file is a local file. `ship.py` is a pre-push gate — if Redis is down, the gate should still run. The file survives the process; Redis might not.

3. **Do NOT change the existing `subprocess.run` path.** The `--log` and `--receipt` flags are additive. The existing `_run()` function gains two conditional writes. Nothing else changes.

4. **Do NOT build a generic "process supervisor" from scratch.** The project already has `ManagedChild` (bifrost_child.py), the daemon, and the runner lock. `ship.py` should use the receipt file pattern from those, not duplicate their process management.

5. **Do NOT attempt to make the Codex cell layer durable in this slice.** That's a separate problem. This slice makes `ship.py` robust to a dead cell — whatever kills the cell, the receipt survives.

## 8. Summary

**Patch surface:** 3 files, ~40 lines.

- `scripts/ship.py`: `--log` flag (durable gate-by-gate progress), `--receipt` flag (JSON receipt: pid/started/heartbeat/exit_code/verdict/log_tail), SIGTERM handler (killed receipt). ~25 lines.
- `tests/test_t093_crash_path.py`: D1-D4 kill drills. ~15 lines each.
- `scripts/bifrost_child.py`: Extract `pipe_watcher()` (optional, deferrable). ~10 lines.

**Design principle:** The project has already solved this problem three times (runner, daemon, ManagedChild). The fix is connecting `ship.py` to the existing patterns — a durable receipt file watched by an independent deadline, not an in-memory channel trusted as the sole completion path.

**Fenced:** This is DeepSeek's independent half. Do not reconcile with Fable's half until both are filed and the sync round begins. Do not edit any code.

*Filed: 2026-07-17 ~09:15 ET. Renamed T091→T093 2026-07-17 ~09:22 ET per codex_root ID-collision steer.*
