# Comms Architecture — deepseek runner-seat position (2026-07-17)

Status: Independent answer to claude's mailbox-vs-queue question (Daniel-prompted,
pre-charter, no build authorized). Source: the runner consume loop
(scripts/bifrost_runner_deepseek.py:1070-1120) + cursor/lane machinery.

---

## 1. FROM THE RUNNER SEAT: what breaks if cursors go away?

**The consume loop gets SIMPLER, but the claim-contention race is REAL and DIFFERENT
from today's consumer-seat race.**

Today's loop (lines 1070-1120):
1. `bus.wait(timeout_ms=1500, advance=False)` — block on stream, detect-only
2. For each message: `_reply_already_sent` check → process → `_mark_reply_sent`
3. After batch: advance cursor to `batch_next`

In a mailbox world:
1. `query("to=deepseek AND state=unhandled")` — stateless, any seat, no cursor
2. For each message: `claim(msg_id, agent="deepseek", ttl=N)` — durable claim
3. Process → mark handled → release claim
4. On crash: claim TTL expires → message returns to unhandled → redelivered

**What gets SIMPLER:**
- No cursor. No lane flip. No cursor divergence. No `batch_next` tracking.
- No RB-26 killpoint drill (cursor commit IS the crash point — claims eliminate it).
- No `_reply_already_sent` dedup sentinel. The claim IS the dedup: "has anyone claimed
  this message?" → if yes and claim is valid (not expired), skip.
- No consumer-seat token. No claim_consumer race. Any runner can poll unhandled
  messages for its agent — if two runners poll, they both SEE the same messages but
  only one's CLAIM succeeds (atomic `claim_if_unclaimed`).
- No wake listener re-arm chore. The watcher becomes: `poll("unhandled for agent X is
  non-empty")` → level-triggered, race-free.

**What gets HARDER — claim-contention is the new race:**

Today: two runners race for the consumer-seat TOKEN. Loser degrades to peek. Winner
consumes. The race is at ACQUISITION time, not per-message.

Mailbox: two runners both query unhandled messages. Both see the same 5 messages.
Both try to claim them. For message 1: runner A's claim wins, runner B's claim fails
(atomic). Runner B tries message 2 — wins. Runner A tries message 2 — fails. Net:
both runners process DIFFERENT messages from the same batch. No message is processed
twice. No message is dropped.

**This is BETTER than today's race.** Today's race: one runner consumes everything,
the other degrades to peek and processes NOTHING. Mailbox race: both runners make
forward progress on different messages. The claim is per-MESSAGE, not per-SEAT.

**Where does RB-26 idempotency live?** In the claim lease TTL. Runner claims message,
TTL=600s. Processes. Marks handled. On crash before mark: claim expires, message
returns to unhandled, next runner claims it. On crash after mark: message is handled,
no redelivery.

**Is a claim-lease strictly better than a consumer-seat token?** YES, for three reasons:
1. **Granularity**: seat token blocks the WHOLE inbox. Claim lease blocks one MESSAGE.
   A stuck message doesn't block the queue.
2. **Observability**: "message X claimed by deepseek at T, expires at T+600" is
   inspectable per-message. "Consumer seat held by token Y" tells you nothing about
   WHICH messages are being processed.
3. **Recovery**: a crashed runner's claimed messages auto-recover when the claim TTL
   expires. A crashed runner's consumer-seat token blocks the ENTIRE inbox until TTL
   expiry or free_if_dead (300s grace, 900s stale — much slower).

---

## 2. ORDERING / BLAST RADIUS: is mailbox a layer on top of T047, or does it change T047?

**Mailbox-state IS a layer on top of the existing streams — but it changes what T047
should cut TO.**

Today: T047 retires the legacy stream. Post-T047, the work lane is the single source
of truth. Cursors advance over the work lane stream.

Mailbox: the append-only message log IS the stream. State (unhandled/claimed/handled)
is a DERIVED INDEX over the log. The log is append-only, immutable. The index is
rebuildable from the log.

**This means T047 should cut to: "the work lane is the append-only log."** The lane
shape doesn't change — it's still a Redis stream with XADD. What changes is what
CONSUMERS do with it:

- Pre-mailbox (T047 target): consumers advance a cursor. State = cursor position.
- Post-mailbox (layer on top): consumers query an index. State = per-message claims.

The stream is the same. The index can be added as a NON-BREAKING layer. T047 can ship
with cursor semantics, and mailbox can land as T047-b or a follow-up slice that adds
the claim index without changing the stream shape.

**BUT: if mailbox is the destination, T047 should NOT hard-code cursor semantics into
the lane contract.** The lane contract should say: "the work lane is an append-only
ordered log. Consumers MAY read via cursor or via state index." This keeps T047
future-compatible with mailbox without delaying it.

**Verdict: T047 proceeds as planned. Add a one-line compatibility note to the lane
contract: "cursor-based consumption is the INITIAL consumer model; a state-index
(mailbox) consumer model may be added as a non-breaking layer."**

---

## 3. TWO-TIER BUS: which kinds need queue vs mailbox?

**The honest answer IS a two-tier bus — but it maps CLEANLY onto the existing kind
taxonomy.**

| Tier | Kinds | Semantics | Consumer model |
|------|-------|-----------|----------------|
| **Firehose** (queue) | trace, thinking, tool, narration, ledger_update, resolved, hint | High-volume, order-sensitive for display, lossy retention OK, NEVER load-bearing | Cursors + ring buffers. Same as today's trace lane. No claims needed — messages have no lifecycle. |
| **Mailbox** (stateful) | handoff, request, reply, chat, question, inform, nudge, steer, completion, decision, blocker, note | Low-volume, each message has a lifecycle (unhandled→claimed→handled→acked), at-least-once delivery, expectation settlement | State index + per-message claims. Queries: "unhandled for agent X", "claimed by Y and not expired", "handled but unacked". |

**The mapping is clean because the existing lane taxonomy ALREADY splits on these
lines:**

- Trace lane: firehose. Already QoS0 ring. Already lossy. Already display-only.
  Cursors are correct here — the consumer just needs the latest N messages.
- Work lane + sig lane: mailbox. These carry directed asks, replies, handoffs, nudges.
  Every message has a sender waiting for a response. Every message has a lifecycle.
  Claims are correct here.

**The only kind that straddles: `note`.** Notes are sometimes firehose (telemetry,
heartbeat), sometimes mailbox (a directed status update). Rule: notes with
`meta.expects_ack=true` are mailbox. Notes without are firehose. Default: firehose.

---

## 4. WAKE / NOTIFY: level-triggered vs edge-triggered

**Level-triggered is strictly better for the runner. No runner-side reason to keep
edge-triggered.**

Today (edge-triggered): `bifrost_wake.py` blocks on `bus.wait()` until ANY message
lands, then exits. The harness re-invokes the agent. But:
- A trace message from another agent wakes the watcher → harness re-invokes → agent
  sees nothing answerable → wasted boot.
- If the watcher's exit races with a second message landing, the second message
  waits for the NEXT watcher arm → latency spike.
- The watcher is a one-shot: arm, fire, re-arm. The stop-hook nags when unarmed.
  T086-S3 was built entirely to suppress false nags from this chore.

Mailbox (level-triggered): `poll("unhandled for agent X count > 0")`. The watcher is
a dumb notifier. False positives are cheap — the agent queries unhandled count, sees
zero (all trace traffic), goes back to sleep. The watcher never needs re-arming
because it never "fires" — it just signals "something changed, check your mailbox."

**What the watcher becomes:** a 5-line loop:
```python
while True:
    count = query_unhandled_count(agent_id)
    if count > 0:
        signal_harness()  # "wake up, you have mail"
    sleep(poll_interval)  # 2-5 seconds
```
No seat file. No re-arm trigger. No stop-hook nag. No arming marker. T086-S1, S2a,
S3 — all the wake machinery — collapses to a poll loop.

**The runner's boot gets cheaper:** instead of "boot from scratch, read 6KB of
context, figure out what's going on," the runner queries "what's unhandled for me?"
→ processes the message(s) → updates claim state → done. No full boot needed for
a single handoff reply.

---

## 5. STEELMAN: the strongest argument AGAINST the mailbox reframe

**The current design is load-bearing in ONE way the mailbox reframe must replicate,
not discard: the generation fence (L1b).**

The consumer-seat token carries a MONOTONIC generation number. Every consume/advance
operation checks: "is my generation still current?" If a successor claims the seat
with a higher generation, my next consume attempt is fenced out with STALE_GENERATION.
This prevents the split-brain scenario: old runner crashes, new runner starts, old
runner recovers and tries to consume → fenced.

In a mailbox world, what prevents a ZOMBIE runner from processing messages after a
successor has started? The claim TTL alone doesn't prevent this: the zombie could
re-claim messages after the TTL expires, or claim NEW messages while the successor
is also claiming them.

**The answer: claims carry the runner's generation, and the claim operation is
generation-gated.** `claim(msg_id, agent, generation=N)` — only succeeds if the
agent's current generation is N. When a new runner starts, it increments the
generation. The old runner's claims are rejected. This is the SAME fence,
relocated from the consumer seat to the per-message claim.

**This means: claims ARE consumer-seat tokens, but per-message instead of per-inbox.**
The generation fence, TTL, and token identity all survive the transition. Nothing is
lost. The fence moves from "you may consume from this inbox" to "you may claim
messages for this agent."

**The second load-bearing mechanism: at-least-once delivery with effectively-once
replies (RB-26).** The cursor-commit-after-processing pattern guarantees: a crash
redelivers unhandled messages to the successor. The reply_sent sentinel guarantees:
a redelivered message we already answered is skipped.

In mailbox: the claim lease IS the at-least-once guarantee. A claimed-but-unhandled
message whose claim expires is redelivered. A handled message (claim released +
state=handled) is never redelivered. The reply_sent sentinel can RETIRE — the claim
state IS the dedup.

**The third: idempotency of the query itself.** "Unhandled for agent X" must return
the same results for ANY seat querying it. This is trivially true for a state index
over an append-only log — the index is deterministic from the log. Two seats running
the same query at the same wall-clock time see the same messages (minus claims that
landed between their queries — the claim operation serializes them).

---

## SUMMARY: my independent judgment

1. **Mailbox simplifies the runner loop.** Claims are per-message consumer-seat tokens
   with better granularity, observability, and recovery. The generation fence survives
   intact.

2. **T047 proceeds as planned.** Mailbox is a non-breaking layer on top of the same
   streams. Add a compatibility note to the lane contract.

3. **Two-tier bus maps cleanly.** Firehose (trace lane) = cursors + rings. Mailbox
   (work+sig lanes) = state index + claims. The existing kind taxonomy already splits
   this way.

4. **Level-triggered wake is strictly better.** The watcher becomes a 5-line poll
   loop. T086-S1/S2a/S3 machinery retires.

5. **The strongest argument against mailbox is the generation fence — and it transfers
   cleanly.** Claims carry generation; old-runner claims are fenced. Nothing is lost.

6. **What I would NOT change:** the append-only stream shape, the lane taxonomy, the
   expectation/redrive system (it works on top of claims too), the promoter (durable
   salient messages survive regardless of consumption model).

The reframe is correct. Daniel's intuition — "would this be made easier by actually
saving messages and not deleting them right away?" — points at exactly the right
architectural move. We already save messages (promoter, append-only lanes). What we
need is to STOP using cursors as the primary consumer model for directed asks. The
cursor is an implementation detail of the firehose tier. The mailbox tier is a
state index over the same log.
