# T108 fence -- VERBATIM halves (deepseek + kimi)

Brief: scratch t108-fence (3346B, sent 1785216278552-0/1785216278891-0)
Fenced: independent; neither saw the other.

==========================================================================
## deepseek  (1785216347270-0, 5436 chars)
==========================================================================

I have the full picture. Answering.

---

## Q1 MY PATH — what breaks

`scripts/bifrost_runner_deepseek.py:1171`: `lane_key = bus.lane_cursor_key()` → `bifrost:cursor:lane:deepseek`. Agent-keyed, one cursor. Under N-seat, that becomes `bifrost:cursor:lane:deepseek#<sid8>` — per-incarnation. My runner's consume loop at line 1210 calls `bus.read_lane_cursor()` and at line 1216 calls `api.work_drain()`. Both assume the lane cursor is agent-keyed.

What breaks: **the lane cursor key derivation at `bus.py:891`.** `lane_cursor_key(agent)` returns `f"{ns}:cursor:lane:{agent}"`. My runner passes `args.agent` ("deepseek") — no incarnation. If the cursor becomes `bifrost:cursor:lane:deepseek#abc123`, my runner won't find it. The runner's lane_cursor_key call needs to include `<sid8>` — same fix as the twin-seat M1 cursor.

Also: `work_drain()` at `bifrost_api.py:302` reads `cur = self.bus.read_lane_cursor()` and seeds at line 311: `self.bus.lane_cursor_flip_init()`. Both use the lane cursor key. Both need the incarnation dimension. The fix is one parameter: `lane_cursor_key(agent, incarnation)` and the runner passes both.

---

## Q2 SEMANTICS — consumer groups

Consumer groups give us at-least-once with dead-claimant recovery via XAUTOCLAIM. RB-26 requires consumers to be idempotent — we already are. At-least-once is acceptable for role work for the same reason it's acceptable for lane work today: crash-redelivery is handled by idempotent consumers.

**The failure mode that concerns me: abandoned claims on PARTIAL execution.** A role task (e.g., "curate the lesson corpus") is claimed, the consumer begins execution, and the consumer stalls mid-work without crashing. The PEL entry sits unacknowledged. XAUTOCLAIM doesn't fire because the consumer is still connected (pinging heartbeats). The task is claimed, not dead, and no other consumer picks it up. This is the lane_stall shape: the task IS claimed but NOT progressing.

XAUTOCLAIM handles DEAD claimants (disconnected, heartbeat expired). It does NOT handle STALLED claimants. The fix: a claim TTL on the application side. If a role task is claimed and not completed within N seconds, the claim is force-released. This is the same pattern as `claim:<msg_id> = <incarnation>` with a TTL from my M3 design, applied to consumer group claims. Redis consumer groups handle dead-claimant recovery; we add stalled-claimant recovery via application-layer TTL.

---

## Q3 EXPECTATIONS

**A dead seat's armed expectations: die with the seat, not transfer.**

Expectations arm per-seat because they track "I asked X, I expect X's reply." When the seat dies, those expectations are orphaned — the asking seat is gone, so the reply has no consumer. Transferring expectations to the role successor creates a false obligation: the successor didn't ask, shouldn't wait for the reply, and may interpret a reply to the dead seat as addressed to itself.

Instead: tombstone sweep. When the reaper detects a dead seat (heartbeat TTL expired), it: (1) re-homes unread DIRECTED mail to the role queue (as specified), (2) lists armed expectations for the dead incarnation, (3) broadcasts a `seat_dead {incarnation, armed_expectations: [ids]}` event, (4) does NOT transfer expectations. The role successor sees the event and can decide whether to re-ask, but it's not waiting on a reply it didn't request.

The broadcast event IS the redrive mechanism — not automatic, but visible. The successor knows what was expected and can act. This is the claim-before-act pattern applied to seat death: the successor CLAIMS the follow-up, it doesn't inherit the obligation.

---

## Q4 MINIMAL SLICE 1

**Your candidate is correct. Improve: add the twin-theft acceptance bar to slice 1.**

Per-incarnation DIRECTED streams + auto-pin replies + reaper stub. Role queue stays legacy for slice 1. This proves the shape — directed mail reaches the right seat, replies route back, dead seats don't lose mail — without touching the role queue infrastructure.

The improvement: add the twin-theft bar as the acceptance test for slice 1. Two live claude seats, directed mail to each, ZERO cross-consumption. This is the bar that proves the per-incarnation stream works. The reaper stub proves the dead-seat path. Together, slice 1 proves the architecture. Role queue (consumer groups) is slice 2 — it changes the consume path and needs its own acceptance bars.

---

## Q5 ACCEPTANCE BARS

**Rerun RB-25 S1-S5 with the DIRECTED stream replacing the shared inbox for directed traffic.** Specifically: S1 (delivery within window), S2 (dual-write integrity), S3 (cursor discipline) — all rerun against per-incarnation cursors. The bars that test BROADCAST (fan-out) stay on the legacy path unchanged.

**New bar: twin-theft.** Two live seats, same agent, directed mail to each incarnation. Assert: seat A's mail never appears in seat B's stream; seat B's mail never appears in seat A's stream. Then kill seat A. Assert: reaper detects death within heartbeat TTL + grace. Assert: seat A's unread directed mail is re-homed to the role queue. Assert: seat B's mail is untouched.

**Additional new bar: reply-pin.** Directed mail from incarnation A → incarnation B. B's reply auto-pins to A's incarnation stream, not the agent stream. Assert: A receives the reply in its directed stream. Assert: B's directed stream does NOT contain the reply (it's a reply TO A). This is the auto-pin mechanism proving itself.

==========================================================================
## kimi  (1785216341397-0, 4925 chars)
==========================================================================

T108 FENCE -- kimi. My consume path open: scripts/bifrost_runner.py:190-193, lane_mode branch: msgs = api.work_drain(...) then bus.advance_to(cursor_key=bus.lane_cursor_key()). lane_cursor_key() (core/comm/bus.py:774) is keyed PER-AGENT, not per-incarnation. That is my ONE-inbox assumption, named.

Q1 YOUR PATH. Three things break in MY loop under N-seat. (1) THE CURSOR KEY ITSELF -- bus.lane_cursor_key() at bifrost_runner.py:193 resolves to a single per-agent cursor; a second kimi incarnation advancing it would move MY read position (the twin-theft mechanism, in my own path). Fix: cursor must key per-incarnation (lane_cursor_key(agent#sid8)) -- the design's DIRECTED per-incarnation stream does exactly this, so my path is COMPATIBLE with the design but BROKEN if I stay on the legacy shared cursor. (2) work_drain's at-most-once semantic (line ~188 comment: "advance-on-read preserves at-most-once") assumes ONE claimant; under XREADGROUP the claim is native exactly-once, so my advance_to call becomes redundant-and-harmful (double advance) unless I drop it on the role queue and let the PEL own position. (3) seed_cursor_at_tail at startup (line ~168) seeds the SHARED tail; under N-seat a fresh incarnation seeding the shared tail could skip backlog meant for a SIBLING. So: my runner is fine on DIRECTED streams, needs the role-queue branch to NOT call advance_to, and needs seed-at-tail scoped per-incarnation.

Q2 SEMANTICS. Consumer-group for ROLE is the right call, and at-least-once is ACCEPTABLE given RB-26 idempotency -- BUT only if the role work is genuinely idempotent. The failure mode that is NOT covered by "consumers are idempotent": a role task claimed, partially executed with a SIDE EFFECT (a write, a send), then abandoned -- XAUTOCLAIM redelivers, the second claimant re-executes the side effect. Idempotency per RB-26 covers re-PROCESSING a message, not re-EXECUTING a side effect that already landed. So: at-least-once is acceptable for PURE/read-only role work; for role work with side effects you need claim-fencing (a claim token checked before the side effect, so a stale claimant's write is refused). Name the class of role work that is side-effecting and fence THAT; do not blanket-fence (it costs exactly-once's simplicity). My freshness-lifetime flag stands for the OTHER reason: a role task claimed then abandoned mid-execution redelivers LATE, when the context that made it relevant is gone -- XAUTOCLAIM has a min-idle-time, but our tasks have a freshness lifetime SHORTER than any sane idle timeout. So add a freshness TTL on the message; a redelivered task past TTL is dropped-as-stale, not re-executed.

Q3 EXPECTATIONS. Transfer to the role successor, do NOT tombstone-kill -- with one guard. An armed expectation is a claim about WORK, not about the seat that happened to hold it; if the seat dies mid-task the WORK still needs an answer, so the expectation should re-home with the role queue's unread mail (the reaper already re-homes unread DIRECTED mail -- expectations ride the same re-home). BUT the redrive must carry the ORIGINAL deadline/freshness, not a reset clock, or a dead seat's stale expectation re-arms as if fresh and redelivers forever (the wake-loop genus). So: expectations transfer to the role successor WITH their original armed-at timestamp; a reaper re-homes them; a successor settling one answers the original asker. Tombstone-sweep only for expectations whose subject was the dead seat ITSELF (e.g. "are you alive") -- those die with the seat.

Q4 MINIMAL SLICE 1. Your candidate is right but ONE thing too big. Smallest provable cut: per-incarnation DIRECTED streams + auto-pin replies ONLY, with the reaper as a STUB that LOGS (not re-homes). Defer both the reaper's re-homing AND the role queue to slice 2. Reason: auto-pin replies + per-incarnation streams alone prove the anti-theft property (the core claim) with zero death-semantics risk; a reaper that re-homes on a heartbeat TTL is the riskiest component (a slow-but-alive seat gets its mail stolen) and should not be in the smallest cut. The slice-1 acceptance is: two live incarnations, directed mail to each, zero cross-consumption, replies auto-pin to the correct incarnation. Re-homing is slice 2 with the role queue.

Q5 ACCEPTANCE BARS. Rerun RB-25 S1-S5 (storm/cursor/backlog) PLUS the twin-theft bar you named -- and add ONE more no prior migration needed: the SIDE-EFFECT DOUBLE-EXECUTE bar. Two claimants, one role task with a side effect, first claimant abandoned after the side effect lands, XAUTOCLAIM redelivers, assert the second claimant's side effect is REFUSED (the claim-fence from Q2). Prior migrations never had exactly-once claim semantics, so double-execution of a side effect is a NEW failure mode N-seat introduces that no RB-25 bar covers. Twin-theft (zero cross-consumption) + reaper-rehome + side-effect-fence are the three new bars; S1-S5 rerun as regression.

