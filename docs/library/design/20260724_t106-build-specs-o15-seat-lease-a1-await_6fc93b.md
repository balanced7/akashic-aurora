---
akashic_id: art_20260724_t106-build-specs-o15-seat-lease-a1-await_6fc93b
akashic_sha: a31da7cfa9f9
status: current
type: design
arc: T106
date: 2026-07-24
title: t106-build-specs-o15-seat-lease-a1-await
gist: "T106 pre-fence build specs: O1.5 door-lifetime seat lease (5 pins) + A1 bifrost_await long-poll (6 pins); tonight's zombie+watcher incidents as receipts; V1-V3 verify-before-freeze"
tenant: solo
visibility: fleet
seats: [claude]
category: [bus, tooling, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_reconciliation-mcp-door-concurrency-leve_600574
    rel: discusses
created: "2026-07-24T00:54:34"
updated: "2026-07-24T00:54:34"
---
<!-- GENERATED PROJECTION of art_20260724_t106-build-specs-o15-seat-lease-a1-await_6fc93b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t106-build-specs-o15-seat-lease-a1-await

T106 BUILD SPECS -- O1.5 + A1 (drafted between rounds, 2026-07-24 night; fence pending -- deepseek counter + kimi stranger-test QUEUED BEHIND their T105 halves, build starts only after both land). Base: the four-voice reconciliation (art_20260723_reconciliation-mcp-door-concurrency-leve_600574) + the leverage map L3/L4. Daniel's gate for the wave (verbatim): "lets start fleshing out the mcp arc, design and build with kimi and deepseek."

TONIGHT'S JUSTIFICATION RECEIPTS (both slices predicted tonight's pain):
- L3 receipt: the consumer-seat zombie -- a sibling session held the claude seat via TTL lease; the drain-then-arm chain waited ~25 minutes (attempt 50) for the lapse. O1.5 makes that release INSTANT.
- L4 receipt: the watcher saga -- forgot-to-arm, insta-fire on stale lanes, seen-sidecar bookkeeping, harness-tracking law. A1 collapses the whole ritual to one in-protocol call for seat-model sessions.

============================================================
SLICE O1.5 -- consumer-seat lease keyed to the door's lifetime
============================================================
MECHANISM (reconciliation convergence 5, the HYBRID):
- When consumption rides the MCP door, the RB-21 consumer-seat lease binds to the SERVER INSTANCE: holder id = door:<instance-uuid> (the stdio server is a child of the session -- session death IS process death).
- Graceful path: server shutdown/stdin-EOF -> DELCONSUMER + lease delete (instant release).
- Violent path: ~2s heartbeat onto the lease, ~5s TTL -> a SIGKILL'd session frees in <=~5s (vs 1800s today). Zombie window goes 1800s -> ~5s; honestly never zero.
- The CLI door KEEPS today's TTL semantics untouched (fallback + runner path).
- MEMBRANE LAW (standing): runners NEVER consume via MCP -- seat-model agents only; the single-consumer drain-loop invariant is untouchable.

PRE-REGISTERED PINS (committed RED before build):
  O15-P1  a seat acquired through the door carries a door-bound holder id (visible in the seat record).
  O15-P2  graceful server exit frees the seat immediately -- a second session acquires with zero TTL wait.
  O15-P3  violent kill: seat freed within 2x TTL (drill: kill -9 the server process, time the reacquire).
  O15-P4  CLI-door seats are untouched (existing RB-21 pins stay green unmodified).
  O15-P5  the zombie drill re-run: tonight's exact scenario (holder session dies unclean) -> reacquire in <=5s, not 25 minutes.
ACL note: the lease-holder identity derives from the door's bound agent id (unforgeable per-call, same posture as _bus_send_ok) -- kimi's stranger-test target #1.

============================================================
SLICE A1 -- bifrost_await(lane, timeout): the long-poll wake tier
============================================================
MECHANISM (reconciliation convergences 4 + 6; leverage map L4 honest-cut):
- New async MCP tool: parks server-side on the work lane; WINDOWED -- block <=~5s per xread iteration, loop to the caller's deadline; deadline stays under the harness per-call tool budget; CancelledError propagates INTO the parked read (cancellation actually cancels).
- Returns the mail IN the tool result (wake and payload in one hop). Consume-if-seat-holder: when the calling session holds the consumer seat (O1.5 world), the await CONSUMES what it returns; otherwise it detects-only (T017 law preserved).
- wake=work: trace/sig kinds never satisfy the await. Operator-override dimension honored (AKASHIC_OPERATOR_IDS wake regardless of kind).
- What A1 does NOT buy (stated bound, do not oversell): true idle-wake. A parked await is a held-open turn; the P1 daemon remains the idle-wake owner. A1 is the in-session tier of the same ladder.

PRE-REGISTERED PINS (committed RED before build):
  A1-P1  mail arriving mid-window returns within one chunk (~5s), payload included.
  A1-P2  empty window returns a clean timeout shape (never an error, never a hang).
  A1-P3  cancellation of a parked await cancels the underlying read (THIS closes O1's unverified P-7 half).
  A1-P4  N parked awaits do not exhaust the to_thread pool (bounded-depth drill, N=8).
  A1-P5  trace spam during the window does not satisfy the await; a work handoff does.
  A1-P6  membrane: a runner agent id calling bifrost_await is refused at the door.

VERIFY-BEFORE-FREEZE (blocking questions for the fence round, per reconciliation P-8 discipline):
  V1  the harness per-call tool timeout: config, default, and whether a parked call costs anything beyond the held turn.
  V2  Windows Proactor policy under mcp.run() for the xread-in-thread path (pin it if subprocess paths demand it).
  V3  consume-if-seat-holder vs detect-only default -- deepseek counters this from the runner-invariant side; kimi stranger-tests the lease-identity claim and A1's cancellation guarantee.

BUILD ORDER + OWNERSHIP (reconciliation law 6): claude builds both (its seat class, its diagnosis); deepseek fences as armor; kimi runs the acceptance re-test. O1.5 first (A1's consume-mode depends on it). Fence asks dispatch AFTER both seats' T105 halves land -- one queued ask per seat at a time (tempo law).
