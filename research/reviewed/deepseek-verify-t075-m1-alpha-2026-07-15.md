# T075 M1-ALPHA VERDICT — deepseek verify — 2026-07-15

**Verdict: GREEN**. The daemon skeleton @ca764d6 honors my pin table exactly.

## Pins (tests/test_t075_m1_daemon.py)

| Pin | Test | Result |
|-----|------|--------|
| M1-P1 | start+lock+presence+survive | GREEN — daemon acquires runner lock w/ stable token, registers presence w/ runtime_class=daemon, survives scaled 60s window; cursor key never created (R-a2) |
| M1-P2 | heartbeat freshness w/o gen mint | GREEN — holder ts advances across refresh window, token stable, generation unchanged, TTL kept in band |
| M1-P11 | foreign-lock refusal, no steal | GREEN — pre-existing lock → exit 0 w/ "refused" teaching, lock record untouched |
| M1-P12 | stable dotfile token + gen increment + clean release | GREEN — token reused across restarts, gen increments, clean exit releases lock, dotfile persists |
| R-a1 | same-token twin refusal | GREEN — second daemon on same host (same dotfile→same token) refuses, first daemon unharmed |
| R-a2 | cursor-key-never | GREEN — asserted in every drill, daemon never creates ns:cursor:* |

## Flagged refinements

### R-a1: Same-token twin refusal — sound

The stable dotfile token (M1-P12) inverts runner_lock's pid:random convention. runner_lock would re-entrantly welcome a second process with the same token. The daemon's pre-acquire check at `bifrost_daemon.py:128-133` catches this: if `holder().token == my_token and holder().pid != os.getpid()`, the twin is refused with teaching text and exit 0.

**No pid liveness probe is the correct call.** `os.kill(pid, 0)` on Windows TERMINATES the target — it's not a probe, it's a kill. TTL truth resolves crashed predecessors: the crashed twin's lock expires within one TTL, the next launch succeeds. The host supervisor's retry absorbs the gap.

### R-a2: Cursor-key-never — confirmed

Every drill test asserts `not _C.exists(_cursor_key(ns, agent))`. The daemon never calls any consume-path function. This is ruling 1 of the reconciliation: no consume-path moves in wave 1.

### Disclosed harness fix — correct

The original `_reap` helper TerminateProcess'd refusal-path daemons mid-import, producing exit 1 instead of the pinned exit 0. The split into `_await_exit` (waits for natural exit via `communicate(timeout)`, only kills on timeout) and `_kill` (cleanup for run-forever drills) fixes this. Pin semantics unchanged — refusal daemons now reach their own exit 0 naturally. This is disclosed, not hidden.

## Open bind: Presence card on clean exit

**JUDGMENT: DEFER to M1-gamma.** The daemon's clean exit releases the lock and exits. Its presence card (registered via `bus.register(card=...)`) lives until its own TTL. The clean-death-trio symmetry says "drop it for instant accuracy" — but:

1. The bus API may not have an `unregister()` method today. Adding one is bus-surface work that belongs in its own slice.
2. A lingering presence card for a daemon with a released lock is a transient cosmetic issue, not a blocking regression. The lock is the occupancy signal; presence is the roster legibility signal. A roster entry for a lockless daemon tells the operator "something was here recently" — which is honest information.
3. The incarnation-card path already has `delete_card()` — but that's a different key (`incarnation:` vs `presence:`).

**Recommendation**: M1-gamma should add `bus.unregister(agent)` (or equivalent) and the daemon's clean-exit path should call it. Not alpha scope.

## Suite: 5/5 GREEN (live Redis drills in isolated namespace)
