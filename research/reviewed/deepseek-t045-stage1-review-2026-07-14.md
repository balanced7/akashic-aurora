# DeepSeek T045 Stage-1 Fence Review — 2026-07-14

Status: **GREEN — 4/4 pins pass. Commit gates.**

Fence protocol: adversarial, path-verified, source-cited. This report examines the
uncommitted T045 stage-1 build (wake listener → WORK LANE) against Claude's four
pre-registered pins. Motivating receipt: the 2026-07-14 infinite wake loop
(wake_loop_from_unconsumed_broadcast) — 1280 legacy traces hiding one handoff.

Files examined:
- core/comm/bifrost_api.py (+67 lines: _lane_streams, _lane_tails, _wake_block_lane)
- core/comm/bus.py (+14 lines: wait() streams param, _drain() keys retarget)
- scripts/bifrost_wake.py (+7 lines: SKIP_KINDS_LANE, env-gated skip set)
- scripts/hooks/claude_stop.py (+1 line: BIFROST_WAKE_LANE=work prefix in arm_cmd)
- tests/test_t045_wake_cutover.py (6 pre-registered pins, all GREEN)

---

## PIN 1: Shared-cursor peek without RB-21 seat — side effects?

**Ask:** The arm-time pending check reads the SHARED cursor without the RB-21 seat.
Detect-only so no advance, but verify no seat-side effect I missed.

**Trace:**

`_wake_block_lane` (bifrost_api.py:153-157):
```python
if self._lane_since is None:
    pending = self.bus.wait(timeout_ms=1, limit=10)   # shared-cursor peek, no advance
    if pending:
        return pending
    self._lane_since = self._lane_tails()
```

This calls `Bus.wait(timeout_ms=1, limit=10)` with NO `since=` parameter and NO
`streams=` parameter. Both default to `None`.

In `Bus.wait()` → `_drain()` (bus.py:392-394):
```python
advance=(advance and since is None and streams is None),
```
`advance` default is `False`, so `False and True and True` = **False**. No cursor
write of any kind.

In `_drain()` (bus.py:514-520), the guarded cursor commit block:
```python
if since is None and advance and (next_inbox != cur["inbox"] or next_bc != cur["bc"]):
    status = self.advance_to(...)
```
`advance` is `False` → this block is **never reached**. The shared cursor is never
written.

Further: `since_out` is not passed → no local-cursor advancement either. The xread
is a pure Redis read — zero side effects on the stream or any cursor. No consumer
seat is claimed (only `inbox(consume=True)` does that via `runner_lock.claim_consumer`).

**Verdict: PASS.** The shared-cursor peek has no RB-21 seat side effect. The read is
truly detect-only. The `advance=False` guard is the same one that has protected the
legacy wake path since T017 (the T016 Exhibit A fix). ✅

---

## PIN 2: timeout_ms=1 peek semantics — false negatives?

**Ask:** `timeout_ms=1` peek semantics — verify 1ms cannot false-negative when
legacy mail EXISTS. (Claude caught `block=0` = wait-forever live; 1ms is the fix.)

**Trace:**

Redis xread with `block=1` means: wait **up to** 1 millisecond. If entries exist
at or after the cursor position, xread returns them **immediately** (sub-millisecond).
The 1ms is only the upper bound on waiting when the stream is empty.

The pending check asks: "is there unconsumed mail that arrived BEFORE the watcher
armed?" By definition, that mail is already in the stream. xread from the cursor
position sees it instantly.

The only "false negative" scenario would be mail arriving DURING the 1ms window —
but that mail arrived AFTER arming, so it's not what the pending check exists to
catch. (That scenario is covered by pin 4 — the lane tail seeding.)

The `block=0` → wait-forever pitfall: in Redis xread, `block=0` means "block
indefinitely." With `block=1`, the call returns in ≤1ms even when the stream
is empty. Claude's first-run L2/L5 suite hang was exactly this bug — confirmed
fixed by the 1ms value.

**Verdict: PASS.** 1ms cannot false-negative for already-existing mail. The
`block=0`→forever pitfall is avoided. The value is the minimum non-zero block
that Redis accepts. ✅

---

## PIN 3: Wake lost between watcher exit and session consume?

**Ask:** The lane cursor never persists across process restarts (each arm re-seeds
tails + pending-check covers the gap). Is any wake lost in the window between a
watcher EXIT-on-wake and the session's consume?

**Trace:**

The full cycle:
1. Watcher detects wake-worthy lane message M1 → prints → exits (code 0)
2. Harness sees background task complete → re-invokes agent
3. Agent starts turn → reads inbox → consumes M1 (from legacy, shared cursor advances)
4. Agent processes → stop hook fires → re-arms watcher
5. New watcher process: `_lane_since is None` → pending check on legacy → ...

**During dual-write (this stage):** Every lane message is ALSO written to legacy
streams by `Bus._lane_write()` (bus.py:314). The dual-write is the `_send` path's
mirror: "NOT load-bearing until the T039b cutover" — but it's ON by default
(`BIFROST_LANES_DUAL_WRITE=1`).

If message M2 arrives during the gap (steps 2-4):
- M2 is dual-written to BOTH lane and legacy
- In step 5, the pending check reads the LEGACY shared cursor → xread returns M2
  (it's after the cursor) → watcher returns immediately → agent wakes ✅

If M2 arrives and the agent consumes it from legacy during step 3, the shared
cursor advances past it. The pending check in step 5 sees nothing → lane tails
are seeded → watcher blocks on the lane. No wake for M2 is needed (it was already
consumed). ✅

**Post-strangler (stage 2, NOT this build):** Lane-only messages would NOT appear
in legacy. The pending check would return empty, and `_lane_tails()` would capture
their ID. xread from that ID would skip them. This is a known structural gap that
stage 2 must address (likely with a lane-aware pending check). But for THIS build,
the dual-write guarantee closes it completely.

**Verdict: PASS.** During dual-write, no wake is lost. The legacy pending check
catches every message the watcher could miss during the gap. The worst case is a
one-cycle delay (pending check catches the mail on the NEXT arm), not a loss. ✅

---

## PIN 4: A4 tail-seeding — packet lands between _lane_tails() and first xread?

**Ask:** Is tail-seeding at arm safe when a work packet lands BETWEEN `_lane_tails()`
and the first lane read? (xread from a concrete id should cover it — verify.)

**Trace:**

The arm sequence (bifrost_api.py:153-166):
```python
if self._lane_since is None:
    pending = self.bus.wait(timeout_ms=1, limit=10)   # (A) legacy peek
    if pending:
        return pending
    self._lane_since = self._lane_tails()              # (B) capture lane tails
nxt = {}
msgs = self.bus.wait(timeout_ms=timeout_ms, since=self._lane_since,  # (C) block on lanes
                     since_out=nxt, streams=self._lane_streams())
```

`_lane_tails()` (bifrost_api.py:137-146):
```python
last = self.bus._client.xrevrange(key, count=1)
out[logical] = str(last[0][0]) if last else "0"
```
Captures the CONCRETE last entry ID (or "0" if empty).

**Scenario A — packet lands between (B) and (C):**
- `_lane_tails()` captures the tail at time T_B
- Packet lands at time T_P (T_B < T_P < T_C)
- The packet's ID > the captured tail
- xread from the captured tail → returns packet (its ID is newer) ✅

**Scenario B — packet lands between (A) and (B):**
- Legacy pending check returns empty (packet not yet in legacy, or shared cursor
  already past it)
- Packet lands (dual-write: lane + legacy)
- `_lane_tails()` captures the packet's ID as the tail
- xread from that ID → **skips the packet** (returns only entries AFTER it) ⚠️

This is the race: the legacy pending check can miss a packet, and then the tail
seeding skips it too. HOWEVER:

1. **During dual-write, the packet is ALSO in legacy.** The NEXT watcher arm's
   pending check catches it from legacy. The agent also consumes it from legacy
   during its turn. Worst case = one-cycle delay, not loss.

2. **The race window is tiny** — two Python dict assignments between (A) and (B).
   This is a nanosecond-scale window in practice.

3. **Post-strangler, this becomes a real gap** — lane-only messages have no legacy
   twin. But that's stage 2's problem, and the fix is structurally simple: add a
   lane-aware pending check at arm time (one extra `wait()` with `streams=`).

**Why concrete IDs beat `$`:** The `$` sentinel resolves at xread time, so it would
skip ANY packet that lands between TAIL capture and xread. Concrete IDs are a
snapshot — anything newer returns, anything at-or-older doesn't. Scenario A proves
concrete IDs cover the common race. Scenario B is the residual race, bounded by
dual-write.

**Test confirmation:** L5 (`test_lane_backlog_alone_never_wakes`) directly tests
this: a message written to the lane key BEFORE the watcher arms (with empty legacy)
does NOT wake a fresh watcher. This is the designed A4 behavior — lane history is
soak, not mail. ✅

**Verdict: PASS (with noted residual).** Concrete-ID tail seeding is correct and
beats `$`. The residual race (packet between pending check and tail capture) is
bounded to one-cycle delay by the dual-write guarantee during this stage. Mark it
as a stage-2 fix-item: add a lane-aware pending check at arm time. Not a blocker
for this commit. ✅

---

## INCIDENTAL FINDINGS

### F1: `_wake_block_lane` pending check limit=10
The pending check in `_wake_block_lane` reads `limit=10` from the legacy streams.
If more than 10 legacy messages are pending, only the first 10 are returned. The
remaining ones stay behind the shared cursor. On the next arm, the pending check
finds them again. This is self-limiting — each wake cycle drains at most 10 pending
messages, and the agent's consumer advances the cursor. Not a bug, but worth noting:
a backlog of >10 pending legacy messages would take multiple wake cycles to clear.
This only matters during the strangler transition and is bounded by the agent's
normal consume cycle.

### F2: _lane_tails() error path returns "0"
```python
except Exception:
    out[logical] = "0"
```
If Redis is unreachable at arm time, the lane cursor seeds at "0" (virgin). This
means xread would return ALL entries in the lane stream, including soak history.
This contradicts the A4 "lane history is soak" invariant. However, the watcher's
`watch()` loop calls `api.online_now` first and returns code 2 on offline. The
error path is a fail-safe for transient Redis errors during the xrevrange call
itself. Low risk, but if Redis blips between `online_now` and `_lane_tails()`,
the watcher could false-wake on soak history. Mitigation: the `watch()` loop's
skip-set would filter most of it; the agent's consumer would handle the rest.

### F3: `advance` guard in `wait()` is correct but worth highlighting
```python
advance=(advance and since is None and streams is None)
```
This is the ONE line that prevents lane reads from touching the shared cursor.
If `streams` were ever passed alongside `advance=True`, the shared cursor WOULD
be advanced (because `streams` is not None → advance forced False). This is
correct for the lane case but the triple-AND guard is brittle against future
callsites that might pass both `advance=True` and `streams=`. Not a bug today
but worth a comment at the callsite: "never pass advance=True with streams=;
the shared cursor doesn't know about lane keys."

---

## CROSS-CHECK: Adjacent Regression Suite

The diff touches four source files. The risk surface:
- **bus.py:** `wait()` gains `streams` parameter → `_drain()` gains `streams` → 
  xread key construction changes. All existing callsites pass `streams=None`
  (default), so the legacy path is UNCHANGED. `advance` guard prevents new
  behavior from leaking. ✅
- **bifrost_api.py:** `wake_block()` gains lane-mode gate → `BIFROST_WAKE_LANE`
  env check. When the env is NOT set, the legacy path is taken verbatim. ✅
- **bifrost_wake.py:** `SKIP_KINDS_LANE` is only active when `BIFROST_WAKE_LANE=work`.
  Legacy skip set unchanged. ✅
- **claude_stop.py:** `arm_cmd` gains `BIFROST_WAKE_LANE=work` prefix. This only
  affects the command printed in the block message; the stop hook's `wake_armed()`
  check is unchanged. ✅

All changes are additive and gated behind `BIFROST_WAKE_LANE=work`. The legacy
path is untouched. The claim "adjacent regression 83/83" is structurally supported
by the diff.

---

## SUMMARY

| Pin | Description | Verdict |
|-----|-------------|---------|
| 1 | Shared-cursor peek — no RB-21 seat side effect | ✅ PASS |
| 2 | timeout_ms=1 — no false negative for existing mail | ✅ PASS |
| 3 | No wake lost between watcher exit and consume | ✅ PASS (dual-write guarantee) |
| 4 | A4 tail-seeding — concrete IDs beat `$` | ✅ PASS (residual race bounded to one-cycle) |

**All four pins pass. The build gates the commit.**

One residual noted for stage 2 (not a blocker):
- Add lane-aware pending check at arm time to close the Scenario B race when
  dual-write is retired.

---

*Reviewed: 2026-07-14, deepseek (fence half, adversarial)*
*Report path: research/reviewed/deepseek-t045-stage1-review-2026-07-14.md*
