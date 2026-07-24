---
akashic_id: art_20260711_rb-21-design-review-deepseek-fenced-gate_dddb7b
akashic_sha: 83e8d6e14170
status: draft
type: report
date: 2026-07-11
title: RB-21 Design Review — deepseek fenced gate (2026-07-11)
gist: "Governs: docs/rb21-build-spec-2026-07-11.md @2f89ca1 + tests/test_rb21_consumer_seat.py Fence: author+review (claude authors, deepseek gates"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-21-session-cursor-discipline-build-sp_9fbdcd
    rel: cites
created: "2026-07-11T12:59:58"
updated: "2026-07-23T21:42:15"
---
<!-- GENERATED PROJECTION of art_20260711_rb-21-design-review-deepseek-fenced-gate_dddb7b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-21 Design Review — deepseek fenced gate (2026-07-11)

Governs: docs/rb21-build-spec-2026-07-11.md @2f89ca1 + tests/test_rb21_consumer_seat.py
Fence: author+review (claude authors, deepseek gates impl)

## 1. GROUND TRUTH VERIFICATION (seam audit)

Verified every seam claim in the spec against the actual code at HEAD (75118d9, W3 RB-9..12 landed).

| Claim | Source | Verified? |
|-------|--------|-----------|
| Guarded commit EXISTS: `Bus.advance_to(inbox/bc, generation)` — L1b Lua | `core/comm/bus.py:419-463` | ✅ `_ADVANCE_LUA` at line 419, `advance_to()` at line 439. Refuses STALE_GENERATION + BACKWARDS. |
| Generation authority EXISTS: `runner_lock.acquire()` INCRs `bifrost:generation:{agent}` | `core/comm/runner_lock.py:96` | ✅ `gen = int(c.incr(GEN_PREFIX + str(agent)))` — atomic INCR per acquisition |
| DeepSeek runner lane disciplined: lock→gen→guarded commit→stand-down on STALE | `scripts/bifrost_runner_deepseek.py:695,738,741,749` | ✅ `lock_gen = runner_lock.generation_of(lock_token)` (695), `bus.advance_to(..., generation=lock_gen)` (738), STALE stand-down (741) |
| THE HOLE: `_drain(advance=True)` via raw `_write_cursor` — no generation, no backwards check | `core/comm/bus.py:370,405-408` | ✅ `self._write_cursor(next_inbox, next_bc)` at line 370 inside `_drain`. `_write_cursor` at 405-408 = raw HSET. |
| Reached from every session-lane consume door: `bifrost_pull.consume_inbox`, `ai_setup_mcp.bifrost_inbox`, `bifrost_api.inbox(consume=True)` | `agent/bifrost_pull.py:73-81`, `ai_setup_mcp.py:398-408`, `core/comm/bifrost_api.py:67-69` | ✅ All three call `bus.inbox(advance=True)` (MCP door: default `advance=True` via `Bus(agent).inbox(limit=limit)` — no explicit `advance=False`). |

**Verdict: ground truth is accurate.** Every seam exists as claimed. The hole is real.

## 2. INVARIANT ANALYSIS

> At most ONE cursor-advancer per agent id at any moment — runner or session, same lock.

**Affirmed.** The invariant reuses the existing `runner_lock` mechanism (lock key `bifrost:runner:{agent}`) without new primitives. A session claim locks the same key a runner claims — preventing both a concurrent runner AND a concurrent session. This is correct: the invariant is about cursor-advancers, not runners; a session consuming mail IS a cursor-advancer.

The sticky tenure (claim on first consume, not at boot) is the right call. Claiming at boot would widen the blackout window of an idle session for zero loss-prevention gain (cut list confirms). A session that never consumes never blocks anyone.

The per-call-mutex refusal is critical: a per-call mutex (claim-drain-release) would still let the twin eat whole batches in between — just politely. The sticky tenure is what makes the second session STAND DOWN (the slice text's demand), not merely slow down.

## 3. MECHANISM REVIEW (5 changes)

### Change 1: Session claim = runner_lock claim (sticky tenure)
**Affirmed.** `claim_consumer(agent, holder) -> (ok, generation, holder_info)` is a thin wrapper on the existing lock. The holder token prefix `session:` distinguishes session holders from runner holders (`agent_name:pid:uuid12`). The stickiness (claim-once, refresh-on-consume/hook-rearm) correctly implements the "stand down" demand.

**Note N1 — re-entrancy for same-session retry (addressed but unpinned):** If the SAME session calls consume twice, the second call's `claim_consumer` with the same holder token must succeed (refresh TTL, return current generation). This is implied by the sticky tenure but not explicitly pinned. The runner_lock pattern (re-entrant for own token — `runner_lock.py:102-108` already handles `rec.get("token") == token`) provides the template. Recommend adding a one-line assertion in the claim_consumer path or referencing the existing re-entrancy precedent in the code comment.

### Change 2: Session TTL != runner TTL
**Affirmed.** `SESSION_CONSUMER_TTL = scaled(1800)` (30 min / 90s drill) vs `LOCK_TTL = scaled(20)` (20s / 1s drill). The ratio is correct: a turn-based session cannot heartbeat in seconds. Worst-case dead-holder blackout = 30 min; detection/peek/durable doors unaffected. FM1 pre-acknowledged — TTL-only steal, no takeover verb in v1. The K7/K8 doctrine (never forcibly evict a live holder) is preserved.

### Change 3: Retire the raw write
**Affirmed.** `_drain(advance=True)` routes through `advance_to(generation=g)`; `_write_cursor` is deleted. `Bus.inbox()` gains `generation: int = 0`. The gen-0 strangler back-compat is correct: the existing L1b Lua already allows gen=0 when stored gen is 0 (the guard clause `if gen < stored` — 0 < 0 is False, pass). The first fenced claim permanently closes gen-0 for that agent — BY DESIGN (one twin claiming immediately protects both). The Lua script runs per-field (inbox, bc) which is the existing advance_to behavior — no new atomicity concern.

**P5 spy strategy (Q4 — answered below):** Prefer `assert not hasattr(Bus, "_write_cursor")`.

### Change 4: Doors claim-or-degrade
**Affirmed.** The flow: claim → drain(generation) → refresh. Claim refused → degrade to peek with teaching shape. The teaching shape is complete and actionable:

```
CONSUMER SEAT HELD for '{agent}': holder {holder} (claimed {age}s ago, ttl {ttl}s)
-- read degraded to PEEK (cursor unmoved, nothing consumed). One session consumes per
agent id; a dead holder frees by TTL alone (<= {ttl}s). If this is a live twin, wind it
down; durable doors (task ledger, notes, promoted) are never blocked.
```

This teaches exactly what the refused session needs to know: who holds it, when they claimed, how long until TTL frees it, and the durable fallback.

**Note N2 — consume_inbox return type change (Q3 — answered below):** `consume_inbox()` currently returns `List[Dict]`. Under the degrade shape, it returns `{"seat_held": True, ...}` — a dict, not a list. Callers iterating the result without checking `isinstance(res, dict)` will break. This needs explicit call-site audit.

### Change 5: MCP door default flips to PEEK
**Affirmed.** `bifrost_inbox(agent, limit, consume=False)`. Currently `ai_setup_mcp.py:398` calls `Bus(agent).inbox(limit=limit)` with default `advance=True` — silent consume. The spec's justification is sound: "a reader tool that silently advances the shared cursor is the eaten-mail class in tool form." The MCP door becomes a peek-by-default reader; explicit `consume=true` is the guarded path. Door-parity guard: `bifrost-sync` already defaults to peek; this closes a parity gap.

## 4. PIN AUDIT (P1-P9: coverage, unweakenability)

| Pin | What it proves | Coverage gap? |
|-----|---------------|---------------|
| P1 | Claim mints gen > 0, advance_to(gen) works | No — covers the happy path |
| P2 | Second claimant refused, holder info names first | No — covers the core invariant |
| P3 | Stale gen fenced AT THE RESOURCE, cursor unmoved | No — covers the Kleppmann guarantee |
| P4 | TTL frees dead holder (no release, no janitor, no SessionStart) | No — covers crash safety |
| P5 | _write_cursor retired; only guarded Lua writes | No — covers the hole closure |
| P6 | Never-fenced agent gen-0 still works | No — covers back-compat |
| P7 | Peek touches neither lock nor gen keys | No — covers detect-doesn't-consume |
| P8 | Door degrade shape: seat_held + peeked mail visible + cursor unmoved | No — covers the teaching shape |
| P9 | MCP door default consume=False (AST inspection) | No — covers the parity close |

**Pins are comprehensive.** Nine pins cover the five mechanism changes + back-compat + teaching shape + door parity. Each is falsifiable: a change that breaks any pin is caught. No weakening path found.

**One gap (minor):** No pin for the SAME-session retry case (same holder token re-claiming → refresh, not refusal). The existing re-entrancy in `runner_lock.acquire()` (lines 102-108) already handles this pattern, so the risk is low. See Note N1.

## 5. REVIEW QUESTIONS (Q1-Q5)

### Q1 — Session TTL value + refresh points

**Refresh points: consume + stop-hook re-arm — sufficient. Boot-time claim correctly cut.**

`SESSION_CONSUMER_TTL = scaled(1800)` is well-calibrated:
- Real: 30 min — long enough for a turn-based session to finish work between consumes, short enough that a dead session doesn't block the runner for more than 30 min.
- Drill: 90s at AKASHIC_TIMEOUT_MULTIPLIER=0.05 — drillable in sub-minute test runs.

Refresh on every consume keeps the seat alive as long as the session is actively reading. Refresh on stop-hook re-arm (the hook that already runs bus machinery) prevents expiry during idle-then-consume gaps. Boot-time claim is correctly cut: it would widen the blackout window of an idle session for zero loss-prevention gain.

**Edge case (pre-acknowledged as FM1):** A session that claims, sits idle for >30 min, then tries to consume again will find its seat expired and must re-claim. If a runner claimed in the interim, the session degrades to peek. This is correct behavior.

### Q2 — MCP door default flip: any consumer that RELIES on silent consume?

**No known consumer relies on the MCP door's silent consume.**

The MCP door (`ai_setup_mcp.py bifrost_inbox`) is called by Claude (and potentially other MCP-enabled agents) as a tool. It currently consumes by default. After the flip:
- Agents that call `bifrost_inbox("claude")` will PEEK — mail stays unread, visible on next call. This is strictly safer.
- Agents that need to consume must call `bifrost_inbox("claude", consume=True)` — explicit, visible in transcripts.

The runner's consume path (`bifrost_runner_deepseek.py`) does NOT use the MCP door — it uses `bus.wait()` + `bus.advance_to()` directly. No impact on the runner lane.

`bifrost-sync --consume` (`agent_cli.py`) uses `bifrost_pull.consume_inbox()`, not the MCP door. No impact.

**Recommendation:** The flip is low-risk. Any agent that silently relied on consumption will notice mail reappearing (harmless — mail visible, not lost). Document the change in the tool's docstring.

### Q3 — seat_held return shape for consume_inbox JSON callers

**This is the most impactful caller-facing change in the spec. Needs explicit treatment.**

Currently `consume_inbox(agent_id, limit) -> List[Dict]`. After the mechanism change, the degrade path returns `{"seat_held": True, "holder": ..., "peeked": [...]}` — a dict, not a list.

Callers currently iterate `for msg in consume_inbox(...)`. Under the degrade shape, iterating a dict yields keys (`"seat_held"`, `"holder"`, `"peeked"`), silently wrong.

**Recommendation:** Two options:

- **Option A (consistent type):** Always return a dict. Happy path: `{"consumed": [...], "seat_held": False}`. Degrade path: `{"seat_held": True, "peeked": [...], "holder": ...}`. Every caller checks `seat_held` first, then reads the appropriate field. One line of caller-side check.

- **Option B (union with sentinel):** Return `List[Dict]` on success, raise `ConsumerSeatHeldError(peeked_mail, holder_info)` on degrade. Callers catch the exception. Follows the RB-8/RB-10 pattern (SupersedeRaceError carries the winner's name). This keeps the happy-path type unchanged and forces callers to handle the degrade case.

**Recommend Option A** for the JSON callers (it's an API, not an internal primitive — callers outside this codebase may not expect a new exception class). The UI fold is straightforward: check `result.get("seat_held")`, if true render the teaching shape and the peeked mail as read-only, else render `result["consumed"]` as the consumed mail list.

The existing P8 pin asserts the degrade shape; it should be updated to also assert the happy-path shape for consistency.

### Q4 — P5 spy strategy

**Recommend `assert not hasattr(Bus, "_write_cursor")` — simpler, more maintainable, not brittle.**

`assert not hasattr(Bus, "_write_cursor")` is:
- A compile-time assertion: the attribute is GONE from the class. No Redis dependency, no eval counting.
- Unaffected by refactors that change eval call counts or key naming.
- The existing guarded Lua path (`advance_to`) already has dedicated test coverage in `tests/test_bus_advance_guarded.py`, so no coverage is lost.

Eval-interception is:
- Brittle: couples to eval call count (changes if advance_to gets a retry or if Lua is restructured).
- Requires Redis connectivity.
- Tests the implementation shape, not the invariant ("no unguarded cursor writes exist").

The `not hasattr` test + the existing `advance_to` tests together prove: (a) the unguarded path is gone, and (b) the guarded path works. That's sufficient.

**One addition:** also assert that `_drain`'s advance path calls `advance_to` (not directly relevant to P5, but a useful integration assertion). Could be done by spying on `advance_to` calls during an `inbox(advance=True)` — one call with the correct generation. Not required for the pin but worth a line in the integration smoke.

### Q5 — Runner lane when a session holds the seat

**The runner's current refused-start message does NOT distinguish a session holder. Needs a one-line fix.**

Current code at `bifrost_runner_deepseek.py:628-631`:
```python
h = runner_lock.holder(args.agent) or {}
print(f"bifrost_runner_deepseek: another '{args.agent}' runner is already live (pid {h.get('pid')}). "
      f"Refusing to start -- one runner per agent avoids cursor races.")
```

When a session holds the consumer seat, `h["token"]` = `"session:{uuid}"`. The message says "another runner" — misleading. The `pid` field belongs to the session process, which may be the same as the runner's process (e.g., a CLI session in the same terminal). The user would read "another runner is already live" and look for a rogue runner process — there is none.

**Recommendation:** Check the token prefix:
```python
h = runner_lock.holder(args.agent) or {}
token = h.get("token", "")
if token.startswith("session:"):
    print(f"bifrost_runner_deepseek: a session '{token}' holds the consumer seat for "
          f"'{args.agent}' (since {h.get('ts')}). Refusing to start — wind down the "
          f"session or wait ≤{runner_lock.SESSION_CONSUMER_TTL}s for TTL expiry.")
else:
    print(f"bifrost_runner_deepseek: another '{args.agent}' runner is already live "
          f"(pid {h.get('pid')}). Refusing to start — one runner per agent avoids "
          f"cursor races.")
```

This makes the teaching legible in both cases and gives the user the correct action (wind down session vs kill rogue runner). The TTL is printed so the user knows the max wait.

## 6. FENCE CHOICE DISSENT

**No dissent on the author+review fence.** Blind-dual would reproduce the same forced moves at double the token cost — the mechanism is tightly constrained by existing primitives (`runner_lock` + L1b guarded commit + `_drain`/`inbox`). A second agent designing from the same constraints would arrive at the same 5 changes. The token-frugality directive supports author+review here. My review role is exactly the right cost/benefit.

## 7. VERDICT

| Section | Ruling |
|---------|--------|
| Ground truth (seam audit) | AFFIRM — all 5 claims verified against live code |
| Invariant | AFFIRM — minimal, correct, reuses existing primitives |
| Mechanism (5 changes) | AFFIRM — each addressed; Notes N1, N2 are pre-impl refinements |
| Pins (P1-P9) | AFFIRM — comprehensive, unweakenable; one minor gap noted |
| Q1 (TTL + refresh points) | AFFIRM |
| Q2 (MCP door default flip) | AFFIRM — no known consumer relies on silent consume |
| Q3 (consume_inbox return shape) | AFFIRM with recommendation — Option A (consistent dict type) |
| Q4 (P5 spy strategy) | AFFIRM — `not hasattr(Bus, "_write_cursor")` preferred |
| Q5 (runner session-aware message) | AFFIRM with recommendation — token-prefix check needed |
| Fence choice | AFFIRM — no dissent |

**GATE: GREEN.** Three notes (N1, N2, N3 → Q5) are all addressable pre-impl refinements; none block the build. The mechanism is sound, the pins are comprehensive, the invariant holds against the ground truth. Proceed to impl.
