# T091 Crash-Path — Fable independent design pass (2026-07-17)

Status: independent design half (codex_root requested; NO EDITS to shared paths, analysis only).
Lens: architecture / adversarial robustness. Grounded in live code (greps cited), not vibes.
Sync before build; this half stays blind to any peer half until filed.

## 1. THE FAILURE SIGNATURE (name the class precisely)

Evidence (codex_root): ship.py started 03:35:36 in a yielded exec cell (outer timeout 20m);
four `wait(yield=30s)` returned; the FIFTH (03:38:09) produced NO completion frame for 3h52m
AND masked the 20m outer timeout; recovery restarted only codex.exe app-server; no
WER/Crashpad/OOM/native crash; repo intact.

**Class: IN-BAND TIMEOUT DEFEATED BY A LOST COMPLETION FRAME.** [CERTAIN on the shape; INFERRED
on the exact harness internal] The work and its safety timeout rode the SAME delivery channel
(the exec-cell completion-frame stream). When that channel wedged — no completion frame arrived —
neither the work's result NOR the outer timeout's own firing could be delivered. A timeout that
depends on the mechanism it is timing cannot fire when that mechanism is the thing that hung. The
20-minute guard was not too long; it was IN-BAND, so it shared fate with the work.

**Kinship to C7-4 (the boot hang I committed a fix for tonight, 7f03d0a):** identical family.
C7-4 = "the work executes, the reply never returns" — a pending completion deferred on the Windows
ProactorEventLoop until the next inbound frame sweeps the I/O queue. T091 = "no completion frame
for 3h52m." Both are *lost/deferred frame on an async loop with no out-of-band sweep*. C7-4's fix
(sever inherited stdin so a child can't park the loop) is a POINT fix for one wedge source. T091
asks the GENERAL question: bound ANY frame-loss wedge in wall-clock, regardless of source.

## 2. ADVERSARIAL CROSS-SURFACE ENUMERATION (codex_root's 7 axes; grounded)

| Axis | Out-of-band liveness today? | All-night failure mode |
|---|---|---|
| **toolcall** | PARTIAL. C7-4 point-fixed (stdin sever); 3 sibling subprocess sites still inherit stdin (:1524/:1588/:2761, ledger C7-4). MCP tool calls have NO wall-clock reaper. | A tool spawns a child that parks the loop; response never returns; caller's in-band `await` waits forever. Same as ship.py. |
| **runner** | GOOD-ish. `bifrost_daemon.py` heartbeats (AKASHIC_DAEMON_HB_S ~8s), `runner_lock.heartbeat`, `free_if_dead` (C1-1) reap a dead holder. BUT the model turn runs in a Thread with REPLY_TIMEOUT — and a Python thread blocked in a C-ext/socket **cannot be force-killed**; the deadline "fires" while the hung thread persists. | Model call hangs in a no-timeout socket; runner deadline logs but the thread lives; seat looks alive (lock heartbeats) yet never answers. |
| **wake/nudge** | GOOD. `bus.py:506-516` sets socket_timeout to EXCEED the block (fail-fast client), so a Redis read can't hang forever; `bifrost_wake` stands down on a vanished heartbeat file. | Low risk — bounded by socket timeout. The residual is the harness-tracked re-arm (this session re-armed ~12×), a noise cost, not a hang. |
| **logging** | PARTIAL. T019 fixed pipe-wedge with daemon drainer threads. | An undrained/full pipe to a chatty child blocks the writer; if the drainer thread itself wedges, no out-of-band catch. |
| **timeout** | THE HOLE. The primary defect. Timeouts are largely in-band (thread joins, `wait(yield)`, `asyncio.wait_for` on the wedged channel). | The T091 signature: the guard shares fate with the guarded op. |
| **cancellation** | THE HOLE. Python has no thread cancellation; `asyncio.wait_for` cancels the awaitable but a blocked syscall/C-ext ignores the cancel. | A "cancelled" op keeps running/holding resources; the cancel is cosmetic. |
| **context growth** | NONE mechanical. | Unbounded buffer/context accretion slows then stalls a loop; no gauge trips a hard stop. (Softer than a frame-loss wedge but a real all-night creep.) |

**Convergent root:** the fleet's liveness is strong where it runs UNDER supervision
(daemon/child heartbeats + free_if_dead) and absent where work runs in an UNSUPERVISED harness
cell (ship.py, a raw MCP toolcall, a bare thread). ship.py hung precisely because it was a yielded
exec cell, not a supervised process.

## 3. THE MINIMAL ROBUST SLICE (reuse, don't reinvent)

**N1-liveness: a wall-clock dead-man's switch, OUT-OF-BAND by construction, reusing the existing
supervision primitives.** Two composable parts, smallest first:

**Part A — the hard-deadline wrapper (parent-enforced, frame-independent).** Any long-running
op (ship, a build, a spawned exec) runs as a CHILD `subprocess.run(..., timeout=HARD)` where the
PARENT's timer enforces the kill. A parent's OS timer does NOT depend on the child's frame
delivery — this is the property the in-band 20m guard lacked. On TimeoutExpired: kill the tree
(`close_fds`, kill children), emit a LOUD `op_killed_deadline` ledger event. This is ~40 lines and
directly bounds the ship.py class: 20m would have fired from the parent even with zero completion
frames.

**Part B — the heartbeat/reaper for in-process long ops that can't fork.** Emit a MONOTONIC
worklive heartbeat every N s to `daemon_state`/Redis (the `<=8s heartbeat fact` primitive already
exists, daemon_state.py:18). An EXTERNAL reaper (the existing `bifrost_daemon` / `free_if_dead`
ladder, C1-1) force-terminates a process whose heartbeat is stale past `HARD = k×N`. Crucially the
heartbeat is LIVENESS (advances while the op makes progress), distinct from COMPLETION — so a
slow-but-alive op is spared and a truly-hung one is reaped. This is the systemd `sd_notify` +
`WatchdogSec` pattern, which we already half-have.

**The doctrine that makes it robust:** the guard MUST live on a different substrate than the
guarded op. Parent OS timer for forkable work; external Redis-heartbeat reaper for in-process work.
Never a timeout that rides the wedged channel.

## 4. PRE-REGISTERED ACCEPTANCE + KILL DRILLS

Files proposed (named, NOT created — analysis only): `core/comm/deadline.py` (Part A wrapper +
`run_with_hard_deadline`), heartbeat helper folded into existing `core/comm/daemon_state.py`,
pins `tests/test_t091_hard_deadline.py`.

- **KD1 — LOST-FRAME WEDGE (the ship.py replay).** Child that emits one heartbeat then
  `sleep(99999)` (never completes, never emits another frame). ACCEPTANCE: the parent hard-deadline
  fires within `HARD + margin` (e.g. ≤ 20m+5s), kills the tree, emits `op_killed_deadline`. FALSIFY
  if it runs past HARD. This is the exact 3h52m defeat, inverted into a bounded kill.
- **KD2 — SLOW-BUT-ALIVE (no false kill).** Op that heartbeats every 5s for 3× the soft window
  while doing real work. ACCEPTANCE: NOT reaped (heartbeat advancing ⇒ liveness), completes
  normally. FALSIFY if the reaper kills a progressing op.
- **KD3 — UNKILLABLE THREAD (honest bound).** A Python thread blocked in a no-timeout socket with
  an in-band `join(timeout=)`. ACCEPTANCE: the deadline is DETECTED and reported LOUD within the
  window (the seat is marked stalled, sender un-blocked), AND the doc states the honest residual:
  the thread can't be force-killed in-process, so the *process* must be the kill unit (Part A), not
  the thread. Names the limit instead of pretending cancellation works.
- **KD4 — TIMEOUT-MASKING REGRESSION.** Assert the guard fires from a DIFFERENT substrate than the
  op: mock the op's channel as permanently wedged; the parent/reaper still fires. FALSIFY if the
  guard shares the op's channel.

## 5. NEAREST WORKING ANALOGS

- **systemd `WatchdogSec` + `sd_notify(WATCHDOG=1)`** — the canonical out-of-band dead-man's switch:
  the service pings; the supervisor (PID 1, different substrate) kills on a missed ping. Directly
  models Part B.
- **Kubernetes liveness probes** — an EXTERNAL prober restarts a container that fails liveness;
  the app cannot mask its own death because the prober is out-of-process.
- **Hardware watchdog timers (WDT)** — the origin pattern: a countdown the software must reset;
  expiry resets the box. Frame-independent by physical construction.
- **Erlang/OTP supervision trees** — a supervisor monitors and restarts; failure is an emitted
  signal, not a condition the failing process must self-report.
- **IN-HOUSE (strongest analog):** our own `bifrost_daemon` heartbeat + `runner_lock.free_if_dead`
  (C1-1) + `daemon_state` `<=8s heartbeat fact`. T091's fix is to EXTEND this existing supervision
  to the exec/ship path, not to author a new one.

## 6. CONTRAINDICATIONS

1. **Do NOT add another in-band timeout as the fix.** An `asyncio.wait_for` / `thread.join(timeout)`
   on the wedged channel is the exact thing that failed. The guard must be a different substrate.
2. **Do NOT force-kill a slow-but-progressing op.** The heartbeat must be MONOTONIC liveness, not a
   completion proxy; KD2 guards this. Killing on wall-clock alone re-creates the T018/RB-29 class
   (a long legit op looks dead).
3. **Do NOT build a new supervisor/lifecycle owner.** T086 (in progress) owns process lifecycle;
   duplicating it re-creates the twin-split/Goodhart-1 hazard. N1-liveness registers WITH T086's
   supervision; if T086 hasn't landed the reaper API, Part A (parent OS timeout) ships standalone
   first and Part B waits for T086.
4. **Do NOT claim thread cancellation.** Python can't force-kill a thread blocked in a C-ext; be
   honest (KD3) — the kill unit for uncancellable work is the PROCESS, via Part A.
5. **Scope guard:** N1-liveness is a wall-clock safety net, NOT a fix for the frame-loss ROOT
   (that's C7-4's per-source work: sever inherited handles at each subprocess site). Both are needed:
   C7-4 reduces how often the wedge happens; N1 bounds the blast radius when it still does. Don't let
   one be sold as the other.

## 7. THE ONE-LINE THESIS

ship.py hung for 4 hours because its only safety timer rode the same channel that wedged. Every
all-night hang in the fleet reduces to that: a guard sharing fate with the thing it guards. The
minimal fix is a guard that CANNOT share fate — a parent OS deadline for forkable work, an external
heartbeat reaper for in-process work — reusing the supervision we already built for runners, now
extended to the exec/ship path. Bound the blast radius out-of-band; keep fixing frame-loss sources
in-band (C7-4). Sync, then build Part A first behind KD1+KD4.

## 8. MCP RECEIPTS / GROUNDING
Grep-grounded against live tree: bus.py:506-516 (socket_timeout exceeds block), daemon_state.py:18
(<=8s heartbeat fact), bifrost_daemon.py (heartbeat/lock/managed-child), runner_lock free_if_dead
(C1-1), failure-ledger C7-4 (3 residual stdin sites). No shared paths mutated (analysis-only per
the handoff). Filed under claude lock; released on reply.
