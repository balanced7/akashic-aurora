# RB-21 -- Session-cursor discipline (build spec, claude half)

Status: current  (2026-07-11)
Class: build-spec (the artifact the RB-21 gated ship cites -- T031 hook 1)
Governs: T029 RB-21 (docs/resilience-battery-slices-2026-07.md sec. RB-21).
Fence: author+review (claude authors, deepseek fenced design-review gates impl) -- chosen
over blind-dual because the mechanism is constrained by existing primitives (runner_lock +
L1b guarded commit); blind-dual would reproduce the same forced moves at double cost
(token-frugality directive). Deepseek dissent on THIS choice is itself review scope.

## Problem + receipts

Two live sessions for one agent id share one inbox cursor with no ownership guard.
- 2026-07-10/11 overnight: the twin session ate two verify verdicts + six deliveries off
  the shared cursor (RB-21 promotion receipts, claude-ruled under Daniel delegation).
- The watcher half (detect) was fixed by T017/P0 (local cursor, detect-don't-consume) and
  T029 Wave 2 (per-session seats, K6-K8 janitor). The CONSUME half is still open.

## Ground truth (verified in code 2026-07-11)

- The guarded commit EXISTS: `Bus.advance_to(inbox/bc, generation)` -- L1b Lua validated
  at the resource (refuses `STALE_GENERATION` and `BACKWARDS`); legacy generation 0
  passes only while the stored generation is 0 (built-in strangler back-compat).
- The generation authority EXISTS: `core/comm/runner_lock.py` -- single-holder TTL lock
  per agent id, heartbeat-refreshed, TTL-only steal (never evict a live holder), atomic
  INCR generation minted per acquisition (`bifrost:generation:{agent}`).
- The deepseek runner lane is fully disciplined: lock -> generation -> guarded commit ->
  stand-down on STALE (bifrost_runner_deepseek.py:729-752).
- THE HOLE: `Bus._drain(advance=True)` commits via `_write_cursor()` -- a raw HSET with
  no generation and no backwards check (core/comm/bus.py:370,405). It can silently clobber
  the runner lane's fenced commits, including moving the cursor BACKWARDS.
- Reached from every session-lane consume door:
  - `agent/bifrost_pull.py consume_inbox()` (bifrost-sync --consume)
  - `ai_setup_mcp.py bifrost_inbox()` (MCP door -- consumes BY DEFAULT, silently)
  - `core/comm/bifrost_api.py receive(consume=True)` (embedder/UI door)

## The invariant

At most ONE cursor-advancer per agent id at any moment -- runner or session, same lock.
The consumer seat IS the runner lock (zero new primitives: one lock, one generation
counter, one guarded commit; a session is just a short-lived "runner" of the consume verb).

## Mechanism (5 changes)

1. **Session claim = runner_lock claim, sticky tenure.** New thin helpers in
   runner_lock.py (same module -- it IS the consumer lock): `claim_consumer(agent,
   holder) -> (ok, generation, holder_info)` and `refresh_consumer / release_consumer`.
   Holder token: `session:{session_id or pid+uuid}` via the existing instance_token
   shape. Tenure is SESSION-STICKY: claim on first consume, refreshed on every consume,
   TTL-expiry frees it -- NOT a per-call mutex (a per-call mutex still lets the twin eat
   whole batches, just politely; the slice text says the second session STANDS DOWN).
2. **Session TTL != runner TTL.** Runner keeps LOCK_TTL=scaled(20) with its continuous
   heartbeat. A turn-based session cannot heartbeat in seconds; its claim carries
   `SESSION_CONSUMER_TTL = scaled(1800)` (future T034 dial), refreshed at every consume
   and at every stop-hook re-arm (the hook already runs bus machinery). Worst-case
   dead-holder consume blackout = TTL; detection is NOT blocked (watchers + peek stay
   seatless), durable doors are never blocked.
3. **Retire the raw write.** `_drain(advance=True)` commits via `advance_to(...,
   generation=g)` -- `_write_cursor` is deleted outright (single caller today).
   `Bus.inbox()` gains `generation: int = 0`. Generation 0 keeps working on a
   never-fenced agent (the Lua already allows it) -- strangler back-compat for any
   out-of-tree caller; the first fenced claim on an agent permanently closes gen-0 writes
   for it (BY DESIGN: one twin claiming immediately protects both).
4. **Doors claim-or-degrade.** consume_inbox / receive(consume=True) / MCP door: claim ->
   drain(generation) -> refresh. Claim refused (live foreign holder) -> the read DEGRADES
   TO PEEK (advance=False) and returns/prints the teaching shape below -- mail is shown,
   never eaten, cursor unmoved. STALE_GENERATION on commit (fenced mid-drain) -> same
   teaching shape, and the drain result is still shown as peek (the successor will
   redeliver: at-least-once, RB-26 lineage).
5. **MCP door consume default flips to PEEK.** `bifrost_inbox(agent, limit, consume=False)`
   -- a reader tool that silently advances the shared cursor is the eaten-mail class in
   tool form. Explicit `consume=true` routes through the same claim helper. (Door-parity
   guard: bifrost-sync default is already peek; this CLOSES a parity gap, not opens one.)

## Teaching shape (exact, door-printed)

CONSUMER SEAT HELD for '{agent}': holder {holder} (claimed {age}s ago, ttl {ttl}s)
-- read degraded to PEEK (cursor unmoved, nothing consumed). One session consumes per
agent id; a dead holder frees by TTL alone (<= {ttl}s). If this is a live twin, wind it
down; durable doors (task ledger, notes, promoted) are never blocked.

## Pre-registered pins (tests/test_rb21_consumer_seat.py, committed BEFORE impl, M3)

Live-Redis pins (skip when bus offline), uuid-namespaced, mirroring the differential
harness pattern. Contract frozen:
  runner_lock.claim_consumer(agent, holder) -> (bool, int, dict)
  runner_lock.SESSION_CONSUMER_TTL  (scaled; > runner LOCK_TTL)
  Bus.inbox(..., generation: int = 0); Bus._write_cursor GONE
  consume_inbox() teaching-degrade shape: {"seat_held": True, "holder": ..., "peeked": [...]}

- P1 session_claim_mints_generation: claim -> gen > 0, advance_to(gen) == OK.
- P2 second_claimant_refused_while_holder_alive: A claims; B claim -> ok=False + holder
  info names A; cursor unmoved by B's degraded read.
- P3 stale_generation_fenced_at_resource: A claims g1; TTL-steal -> B claims g2 > g1;
  A's advance_to(g1) == STALE_GENERATION and cursor field unchanged.
- P4 ttl_frees_dead_holder_alone: A claims with tiny scaled TTL; A vanishes (no release,
  no janitor, no SessionStart); B claims successfully after expiry; gen strictly rises.
- P5 raw_write_retired: Bus has no _write_cursor attribute; _drain(advance=True) moves
  the cursor ONLY via the guarded Lua (spy on eval / assert cursor+gen semantics).
- P6 unfenced_backcompat: never-fenced agent, gen-0 consume advances OK (out-of-tree
  callers unbroken until first claim).
- P7 peek_stays_seatless: inbox(advance=False) + wait(since=...) touch neither lock nor
  generation keys.
- P8 door_degrade_shape: consume_inbox under a foreign live holder returns seat_held
  shape with peeked mail visible and cursor unmoved.
- P9 mcp_door_peek_default: bifrost_inbox default consume=False leaves cursor unmoved.

## Live drill (deepseek [live-drill] + [verify], per the battery)

Second session for agent id 'claude' runs `bifrost-sync claude --consume` while the first
holds the seat: exactly one consumes; the other prints the teaching shape with the mail
still visible; provenance in both transcripts. Then kill the holder uncleanly; within TTL
the second session's consume succeeds with a HIGHER generation. Acceptance IS the drill
transcript + P1-P9 green.

## Failure modes (pre-acknowledged)

- FM1 dead-holder blackout <= session TTL: consume blocked, detect/peek/durable unaffected.
  Accepted; TTL dialable; cut-list item for an explicit takeover verb (NOT v1 -- a --steal
  flag re-opens the kill-loop class the K7/K8 protocol just closed).
- FM2 no rightful-owner oracle: first-claim-wins cannot know which session Daniel wants
  consuming. The win is silent loss -> LOUD taught contention (the refused session's
  transcript names the holder; wind the twin down). Same doctrine as wake seats.
- FM3 generation churn: sticky tenure makes it negligible (one INCR per session, not per
  call).

## Cut list

- Takeover/--steal verb (FM1) -- revisit only with a real starvation incident.
- Per-lane (inbox vs bc) split seats -- no evidence any consumer wants half a seat.
- Claiming at session START (vs first consume) -- earlier claim widens the blackout
  window of an idle session for zero loss-prevention gain.

## Review questions (deepseek, fenced)

- Q1 session TTL value + refresh points (consume + stop-hook re-arm enough? boot too?)
- Q2 MCP door default flip: any consumer that RELIES on silent consume?
- Q3 the seat_held return shape for consume_inbox JSON callers (UI folds it how?)
- Q4 P5's spy strategy: assert-no-attribute vs eval-interception -- pick the less brittle.
- Q5 anything the runner lane needs when a SESSION holds the seat at runner start
  (runner acquire() already refuses on a live foreign holder -- confirm the teaching line
  it prints names a session holder legibly).
