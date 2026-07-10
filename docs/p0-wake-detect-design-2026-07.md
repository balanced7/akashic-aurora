# P0 -- Wake Listener: Detect, Don't Consume (T017 design)

Status: current (under adversarial review by deepseek before build)
Date: 2026-07-09
Fixes: T016 Exhibit A (docs/comms-pillar-synthesis-2026-07.md sec.1) -- a stale
bifrost_wake watcher consumed + discarded a directed kind=reply, silently.

## Constraints discovered in ground truth (why the naive fix is wrong)

1. THE WATCHER IS LOAD-BEARING AND HARNESS-ENFORCED. The stop hook
   (scripts/hooks/claude_stop.py) BLOCKS idling unless a bifrost_wake heartbeat is alive
   (heimdall_wake_from_idle invariant). Watchers legitimately span idle periods; "just don't
   run watchers" is not available.
2. THE BUSY-SPIN TRAP (why the original author consumed). bus.wait() defaults to
   advance=False (detect-only, test-pinned in tests/test_bifrost_wake.py). But wait() reads
   from the SHARED cursor: with a pending skip-kind message ahead of the cursor, detect-only
   wait() returns instantly EVERY call -- bifrost_wake's re-arm loop becomes a hot spin for
   up to --deadline seconds. advance=True was the spin fix; it created the message-eating.
   Any correct fix must give the watcher its OWN position tracking.
3. ORPHAN DOUBLE-FAILURE. A watcher outliving its session (a) kept consuming mail, and
   (b) its live heartbeat satisfied the stop hook's wake_armed() check, so the NEW session
   never armed its own watcher -- unwakeable AND leaking mail simultaneously.
4. One cursor per agent id, many possible consumers; runner_lock guards runners only.

## Design

D1. Bus gains a public cursor read + a `since` override (additive, no behavior change):
    - Bus.cursor() -> {"inbox": id, "bc": id} (the shared cursor, read-only accessor).
    - Bus.wait(timeout_ms, limit, advance=False, since=None): when `since` is given, xread
      starts from those ids and the SHARED CURSOR IS NEVER WRITTEN (advance is ignored;
      documented + asserted). Default path (since=None) byte-identical to today.

D2. BifrostAPI.wake_block becomes detect-only with a LOCAL cursor:
    - self._wake_since initialized from Bus.cursor() on first call; every call passes
      since=self._wake_since and afterwards advances _wake_since past ALL returned messages
      (stream told by m.to == "*" -> bc, else inbox). Shared cursor untouched, forever.
    - Skip-kind messages therefore return ONCE to the caller and never again (no spin),
      while remaining unread for the real consumer (bifrost-sync / inbox()).

D3. bifrost_wake.py:
    - Loop unchanged in shape; SKIP_KINDS continue is now safe (local-cursor skip).
    - WAKE-WORTHY SET CHANGE (deliberate, please attack): kind=reply moves OUT of
      SKIP_KINDS -- a directed reply arriving while the agent idles SHOULD wake it (T016's
      eaten reply was a 15KB fenced report the sleeping agent had explicitly requested).
      trace stays skip (display-only firehose). steer stays skip for now (its semantics are
      fold-into-CURRENT-task; when idle there is no current task -- open question below).
    - Self-singleton via the existing heartbeat file: each iteration re-reads the pid file;
      if it names another live pid, stand down quietly (newest watcher wins; mirrors
      runner_lock without new infrastructure).
    - On wake-worthy: print ledger state + detected messages (as today), exit 0, consuming
      NOTHING. The woken session syncs + consumes through the normal door.

D4. Orphan reap at session start:
    - The Akashic SessionStart hook kills a live bifrost_wake for this agent (verify the
      pid's command line contains bifrost_wake before killing -- never kill a recycled pid)
      and removes the heartbeat file. Rationale: an orphan's completion re-invokes a dead
      session; the new session must own its own watcher (stop hook will arm it at first
      idle). With D2/D3 an orphan is no longer able to eat mail, so this is hygiene +
      unwakeable-session prevention, not the core fix.

D5. Out of scope (P0 stays a bug fix): no ack lifecycle (P6), no ledger push (P3), no
    changes to runner replies or ANSWERABLE sets, no Redis-based watcher registry.

## Test plan (pins written to this contract)

T1. wait(since=...) returns only entries after `since`; shared cursor bit-identical after.
T2. REGRESSION PIN (Exhibit A): reply lands; wake_block returns it once; a second
    wake_block does NOT return it again (no spin); shared cursor untouched; inbox()/
    bifrost-sync still delivers it. (The exact scenario that lost the T016 report.)
T3. wake_block on wake-worthy kind: returned AND still consumable afterwards.
T4. bifrost_wake.watch(): pre-queued trace -> keeps waiting (returns quiet on deadline),
    trace still consumable; pre-queued chat -> exits reporting it, chat still consumable;
    pre-queued reply -> exits (new wake-worthy semantics), reply still consumable.
    (watch() gains an injectable api param for namespace-isolated testing.)
T5. Singleton: stomp the heartbeat with another live pid -> running watch() stands down
    within one inner block.
T6. Existing pins must stay green: tests/test_bifrost_wake.py (wait detect-only defaults),
    tests/test_bifrost_api.py, tests/test_bifrost_runner_deepseek.py (runner batch drain).

## Live drill (gate, deepseek as counterparty)

Arm a real watcher (short deadline). deepseek sends a directed kind=reply while it runs.
Assert: watcher exits (wake fires), the reply is fully readable via bifrost-sync afterwards,
shared cursor advanced only by the explicit consume. Then inverse: a broadcast kind=trace
does NOT exit the watcher. Then orphan drill: leave a watcher running, start a fresh session
context, verify reap + fresh arm.

## Open questions -- RESOLVED by adversarial review + build
(full review: research/reviewed/deepseek-p0-design-review-2026-07-09.md -- itself EATEN by a
second orphan watcher and recovered from the stream: the third live strike of this bug class)

Q1 (reply wake-worthy): YES with a carve-out -- only DIRECTED replies wake; broadcast
    replies are room chatter (review F5, adopted). Loop risk bounded: one wake per reply,
    full-turn processing gates any re-reply.
Q2 (steer while idle): skip stands; the quiet exit now reports the queued-steer count so
    the next boot knows to look (review F6, adopted).
Q3 (seed position): review F1 found the false-wake race (a "0"/virgin seed replays the whole
    stream; a concurrently-consuming live session makes shared-cursor drift stale). ADOPTED
    as a hybrid: seed = shared cursor when one exists, else the CONCRETE stream tail -- the
    review's "$" suggestion had its own hole (XREAD "$" skips mail landing BETWEEN two
    blocking reads; caught by the T017 pins live), so the tail id is materialized via the
    new Bus.tail(). Plus a per-call FAST-FORWARD of the local cursor to the shared cursor,
    so consumed mail never wakes the watcher (review F1 concurrency arm).
Q4 (heartbeat race): exists, self-heals within one inner block (<=120s of duplicate
    watcher, both harmless under detect-only); documented, accepted (review F7).
Q5 (reap vs live sessions): one live session per agent id is the operating contract --
    the reap ENFORCES newest-wins (the 2026-07-09 evening incident was precisely a zombie
    idle session re-arming old-code watchers via its own wake loop). Two deliberate
    concurrent same-id sessions break the shared cursor itself, not just watchers --
    out of scope by contract (review F8, accepted with this documentation).

KNOWN RESIDUAL (out of P0's reach, discovered post-ship 20:01): a zombie lane cannot be
neutralized by killing its watcher -- a killed background task still completes, so the kill
itself re-invokes the zombie for one more turn (one more consume + one more re-arm; observed
live: the T018 smoke reply was consumed by exactly this rebound). The reap (D4) prevents a
NEW session from inheriting the problem, and the detect-only watcher removes the watcher-side
eating, but a still-open idle session's own turn-start sync remains a consumer until the
human closes that window or per-session addressing lands (the P6+ arc; deepseek's seat-2
conversation independently named it). Operating rule until then: close superseded session
windows; do not kill their watchers expecting silence.

TWO EATING MECHANISMS confirmed live on 2026-07-09, both closed by P0:
  A) 09:08 -- an ORPHAN WATCHER (advance=True + SKIP_KINDS discard) consumed and dropped a
     directed reply with no session awake at all. Closed by D2/D3 (detect-only local cursor).
  B) 19:16 -- a ZOMBIE IDLE SESSION, woken by its own watcher, consumed the active session's
     mail through its perfectly-correct turn-start `bifrost-sync --consume`, replied on the
     bus as the same agent id, re-armed, and idled again. DeepSeek independently diagnosed
     the collision from its side of the conversation. Closed by D4: the reap at session
     start de-arms the older lane, making it dormant (it can never wake to consume again) --
     newest-wins enforced mechanically, which is exactly what the manual kill did today.

Review F2 (maxlen trim below a long-idle local cursor): degrades to BOUNDED paging under
since_out semantics (pinned by test); no head-clamp in P0 -- the shared cursor carries the
same pre-existing exposure, and that belongs to a bus-level slice if telemetry ever shows it.
Review F3 (stream-tag inference): moot -- the build computes the caller's next position
inside _drain (since_out), the review's own recommended alternative.
Review F4 (reap-then-arm gap): accepted as benign latency -- during the gap nothing can EAT
mail anymore; it is readable at the next sync, merely not wake-delivered until the first
stop re-arms.
