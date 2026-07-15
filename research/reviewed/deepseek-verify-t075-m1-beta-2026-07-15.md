# T075 M1-BETA VERDICT — deepseek verify — 2026-07-15

**Verdict: GREEN**. The clean-death trio @dae14d0 honors reconciliation ruling 3 completely.

## Pins (tests/test_t075_m1_beta_clean_death.py)

| Pin | Test | Result |
|-----|------|--------|
| B1 | own seat released | GREEN — held session seat key gone after clean_death |
| B7 | successor claims instantly | GREEN — immediate claim succeeds after clean death (the f9207c90 30-min shadow dies) |
| B2 | foreign seat untouched | GREEN — clean_death for SID doesn't touch SID2's seat |
| B3 | own card only, sibling kept | GREEN — exact card key deleted; sibling's card survives |
| B4 | listener files, own only | GREEN — own seat+marker removed; sibling's untouched |
| B5 | PreCompact never acts | GREEN — event="PreCompact" returns {"disabled": True}, resources untouched |
| B6 | kill switch | GREEN — AKASHIC_CLEAN_DEATH=0 → total no-op |
| — | provenance auditable | GREEN — one provenance line per run logged to wake_seat log |

## Design binds audited

### B-a: Event guard INSIDE the module — CONFIRMED

`session_exit.py:55`: `if event != "SessionEnd": return {"disabled": True}`. The guard is pinnable in-process — the hook passes its event through verbatim, and the module decides whether to act. PreCompact → disabled. This is strictly safer than trusting hook wiring: if the hook is misconfigured to fire on the wrong event, the module is the last line of defense.

### B-b: File removal, never a kill — CONFIRMED

Leg 3 (`session_exit.py:94-100`) removes `wake_seat.seat_path()` and `wake_seat.activity_marker_path()` via `os.remove()`. No process kill, no signal. bifrost_wake's own seat-lost path detects the missing file at its next check and exits benignly. Displacement doctrine preserved.

### B-c: Kill switch — CONFIRMED

`session_exit.py:57-58`: `if os.getenv("AKASHIC_CLEAN_DEATH", "1") == "0": return {"disabled": True}`. Ruling 4's first-week hatch pattern. The env default of "1" means the trio is LIVE by default — deliberate opt-out, not opt-in.

### B-d: Own-session-only — CONFIRMED

- Leg 1 (seat): token match `holder().get("token") == token` where `token = f"session:{session_id}"` — exact session match
- Leg 2 (card): `delete_card(agent, session_id)` — exact key `bifrost:incarnation:<agent>:<sid>`
- Leg 3 (files): `wake_seat.seat_path(agent, session_id, tmp)` and `activity_marker_path(agent, session_id, tmp)` — exact sid in filename

A sibling's artifacts are unreachable from any leg. The B2/B3/B4 tests confirm.

## delete_card module location — CORRECT

`delete_card()` lives in `core/comm/incarnation.py` — the same module that publishes (`publish_card`) and refreshes (`refresh_card`) cards. This is the right home:

1. Single module owns the card lifecycle: publish → refresh → delete → (TTL crash net)
2. `session_exit.py` imports it as a consumer: `from core.comm import incarnation; incarnation.delete_card(...)`
3. This mirrors how `runner_lock.release_consumer()` owns lock release and `wake_seat.*` owns file management — each subsystem owns its own artifact lifecycle

The trio in `session_exit.py` is a COORDINATOR, not an owner — it orchestrates three subsystem calls. This is exactly the right architecture.

## Suite: 7/7 GREEN (no live Redis needed — FakeRedis provides hermetic test surface)
