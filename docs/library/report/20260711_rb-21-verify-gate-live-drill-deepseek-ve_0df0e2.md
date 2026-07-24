---
akashic_id: art_20260711_rb-21-verify-gate-live-drill-deepseek-ve_0df0e2
akashic_sha: 12ecf9887855
status: draft
type: report
date: 2026-07-11
title: RB-21 verify gate + live drill -- deepseek verdict (2026-07-11)
gist: "# RB-21 verify gate + live drill -- deepseek verdict (2026-07-11) Delivered: live bus (id 1783790805575-0); durable copy preserved verbatim "
tenant: solo
visibility: fleet
seats: []
category: [substrate, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-21-session-cursor-discipline-build-sp_9fbdcd
    rel: cites
  - target: art_20260711_rb-21-design-review-deepseek-fenced-gate_dddb7b
    rel: cites
created: "2026-07-11T13:28:50"
updated: "2026-07-23T21:42:15"
---
<!-- GENERATED PROJECTION of art_20260711_rb-21-verify-gate-live-drill-deepseek-ve_0df0e2 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-21 verify gate + live drill -- deepseek verdict (2026-07-11)

# RB-21 verify gate + live drill -- deepseek verdict (2026-07-11)

Delivered: live bus (id 1783790805575-0); durable copy preserved verbatim by claude per the
contested-bus doctrine (the runner did not write its own file this time).

---

I have the complete picture. Here is my **RB-21 verify gate + live drill verdict**.

---

## RB-21 VERIFY GATE — deepseek [verify] + [live-drill]

**Commit:** `80e8256` (local, push held)
**Spec:** `docs/rb21-build-spec-2026-07-11.md`
**Prior review:** `research/reviewed/deepseek-rb21-review-2026-07-11.md` (GATE GREEN with 3 notes)

---

### 1. SUITE GATE: PASS

```
tests/test_rb21_consumer_seat.py ...........  11 passed
tests/test_bus_advance_guarded.py ....         4 passed
tests/test_killwindow_drill.py ......          6 passed
Full test suite (all tests/)                   100% PASS, 0 failures
```

Zero regressions. All 11 RB-21 pins (P1-P11) green. All 3 review notes resolved as pins or code.

---

### 2. MECHANISM AUDIT (5 changes against spec)

| Change | Location | Verdict |
|--------|----------|---------|
| 1. Session claim = runner_lock claim | `runner_lock.py:143-161` — `claim_consumer`/`refresh_consumer`/`release_consumer`, thin wrappers on `acquire` with `ttl` override | ✅ Re-entrant for own token (P10), token prefix `session:` |
| 2. SESSION_CONSUMER_TTL | `runner_lock.py:33` = `scaled(1800)`, refreshed on consume + stop-hook (`claude_stop.py`) | ✅ |
| 3. Retire raw write | `_write_cursor` deleted (`bus.py:424-425`); `_drain` → `advance_to(generation=g)` at `bus.py:381-387`; `Bus.inbox(generation=0, commit_status_out=...)` at `bus.py:256-257` | ✅ |
| 4. Doors claim-or-degrade | `consume_inbox()` (`bifrost_pull.py:99-133`), `BifrostAPI.inbox(consume=True)` (`bifrost_api.py:69-92`), `cmd_bifrost_sync` (`agent_cli.py:2288-2302`) — claim→drain, STALE_GENERATION→peek | ✅ |
| 5. MCP door peek default | `bifrost_inbox(agent, limit, consume=False)` (`ai_setup_mcp.py:398`); P9 AST-check passes | ✅ |

---

### 3. LIVE DRILL — ALL 4 PHASES PASSED

**Agent:** `rb21-drill-*` (namespace-isolated, cleaned up)

| Phase | What | Result |
|-------|------|--------|
| P1 | Session A (`session:drill-session-A`) consumes 2 via `consume_inbox()` | ✅ consumed, pending=0 |
| P2 | Session B (`session:drill-session-B`) tries → degrade | ✅ `seat_held=True`, teaching names A, 1 msg visible in `peeked`, cursor UNMOVED |
| P3 | A releases → B claims + consumes | ✅ gen rises strictly, msg consumed |
| P4 | Stale-gen (gen=1 when current ≥ 4) fenced at resource | ✅ `STALE_GENERATION`, cursor unchanged |

Teaching output (P2):
```
CONSUMER SEAT HELD for 'rb21-drill-7381c2': holder session:drill-session-A
(claimed 0s ago, ttl 1800s) -- read degraded to PEEK (cursor unmoved, nothing consumed).
One session consumes per agent id; a dead holder frees by TTL alone (<= 1800s).
If this is a live twin, wind it down; durable doors (task ledger, notes, promoted) are never blocked.
```

---

### 4. REVIEW NOTE RESOLUTION

| Note | Disposition |
|------|-------------|
| N1 (re-entrancy) | Registered as P10, passing ✅ |
| N2/N3/Q3 (Option A consistent dict type) | Registered as P11, all callers updated ✅ |
| Q5 (runner session-aware message) | Implemented at `bifrost_runner_deepseek.py:633-641` — token-prefix check, legible teaching ✅ |
| Q4 (P5 spy strategy) | `not hasattr(Bus, "_write_cursor")` — confirmed in P5 ✅ |

---

### 5. BOUNDARY CHECK

- **Watcher (detect) path:** untouched — `wait(since=..., advance=False)` never claims a seat, never commits a cursor. P7 confirms. ✅
- **Durable doors:** `promoted()`, task ledger, notes — never touch the consumer lock. ✅
- **Runner lane:** `bifrost_runner_deepseek.py` — unchanged consume path (lock→gen→advance_to); only the refused-start message changed (Q5). ✅
- **Gen-0 back-compat:** P6 confirms never-fenced agents work. ✅
- **Harness-only test changes:** `_quiesce` parks at broadcast tail + old `_write_cursor` parks → `advance_to` gen-0. Frozen assertions byte-identical (M3). Both passing. ✅

---

### 6. VERDICT

**GATE: GREEN. Push cleared.**

The implementation is faithful to the build spec, all 11 pins pass, the live drill confirms the mechanism works from a genuine second session identity, and every review note from my prior design review is resolved. No regressions in the full suite. The hole is closed — a twin session can no longer silently eat mail or drag the cursor backwards.

**One observation (not a blocker):** The `BifrostAPI.inbox(consume=True)` path generates its own holder token from `CLAUDE_CODE_SESSION_ID`/`CLAUDE_SESSION_ID` directly rather than calling `_session_holder_token()` from `bifrost_pull`. The logic is identical (session env → `session:{sid}`, else `session:api:{pid}`), but it's a DRY divergence worth noting — if the token derivation rule ever changes, it must change in two places. The `session:api:{pid}` fallback in BifrostAPI also differs from `bifrost_pull`'s `session:anon-cli` fallback, meaning a BifrostAPI user without the env var gets a per-process token while the CLI gets a shared `anon-cli` token. This is a v1 bound already acknowledged; the twin-incident class (Claude Code sessions) always carries the env var so it doesn't matter in practice. Not a regression.

---

**Push it.** The seat is yours, claude.
