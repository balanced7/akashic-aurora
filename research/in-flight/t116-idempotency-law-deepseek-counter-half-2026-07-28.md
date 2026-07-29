# T116 IDEMPOTENCY LAW — deepseek counter-design half (BLIND vs sol's)
# 2026-07-28 ~01:00 UTC — C arc opens

## GROUNDING (what exists today — the doc-vs-reality lie + the three point-fix patches)

### The claim in role_queue.py:33
> "bus sends already are (packet sha + idempotency_key, T040/T043)"

TRUTH: `idempotency_key` appears in exactly TWO places in the entire codebase:
1. `core/comm/packet_spec.py:22` — header comment listing it as a transport field
2. `core/comm/role_queue.py:33` — the claim above

ZERO implementation. No setter, no getter, no consumer check, no producer stamp.
The word "idempotency_key" is prose-only — a wish written as a description of reality.

### The packet sha dedup we DO have (bus.py:832 — T044 dual-delivery twin dedup)
- `_seat_seen(sha)` drops a legacy copy when the work-lane copy was already delivered
- This is TRANSPORT dedup (same packet, two streams), NOT logical dedup (same request, two sends)
- It cannot tell that two byte-identical asks 39 minutes apart are the SAME request
- It cannot tell that a redrive (RB-26 crash-redelivery) is the SAME work item as the original

### T117's three point-fix patches (the things the contracted seam subsumes)

1. **Dual-id alias (T117 P6/P7, commit 10f1f60):** `_emit` records `{ns}:idalias:<id> -> <sibling>`
   at the ONE place both ids are known. `expectations._resolve_link` consults the alias.
   This is a POINT FIX for the "reply meant for new ask settles old ask" bug.
   The contracted seam would make the idalias unnecessary — a producer-assigned
   `idempotency_key` travels WITH the packet and the consumer deduplicates BEFORE settlement.

2. **Per-reply settled markers (`_reply_already_sent` in runner):** The runner checks a
   Redis sentinel to see if it already answered a redelivered message. This is a POINT FIX
   for RB-26 idempotency at the application layer — every consumer builds its own.
   The contracted seam moves this to the CONSUMER DOOR: one `idempotency_key` check
   before the message enters any consumer's work loop.

3. **Re-ask collapse (T112, commit a38b813):** `_emit` hashes the whole `(to, kind, content)`
   and returns the original mid if a byte-identical send lands within a time window.
   This is a POINT FIX for duplicate sends at the SEND DOOR.
   The contracted seam makes the producer STAMP the key; the consumer SKIPS at receive
   time, never sending a duplicate to begin with.

All three are correct and working. All three are point fixes that a properly-contracted
`idempotency_key` seam at the packet layer would subsume into ONE mechanism.

---

## DEEPSEND-SPECIFIC: my runner's send-seam defect (notes bypass the lane-router)

### The defect (lesson: deepseek_runner_note_path_skips_lane_router)
- 23 LEGACY STRAGGLERS across 3 consecutive drains, every sender=deepseek runner,
  every kind=note/triage-receipt
- Work-lane write FAILED upstream each time
- M2 dual-write net caught all 23 (zero loss — the legacy copy always landed)

### Root-cause map

The send path for a runner note:

```
runner: bus.send(m.frm, "note", ...)
  → Bus.send() [bus.py:273]
    → _emit() [bus.py:377]
      → lane_for("note") → "work"  [packet_spec.py:196 — note IS mapped]
      → packet_spec.dual_write_enabled() → True
      → lane_key = "bifrost:work:inbox:<to>"  (directed) or "bifrost:work:broadcast" (broadcast)
      → self._client.xadd(lane_key, lane_env, ...)  ← FAILS HERE
      → retry once → still fails → lane_outcome = "failure"
      → legacy xadd succeeds (the straggler net delivers)
```

The triage parker path (triage_park.py:62):
```
triage_park.park()
  → Bus(agent).broadcast("note", ...)  ← FRESH Bus instance
    → _emit(bc_key, to="*", kind="note", ...)
      → lane_for("note") → "work"
      → lane_key = "bifrost:work:broadcast"
      → xadd fails → legacy succeeds
```

**The lane write fails on Redis xadd.** The lane router IS called, the kind IS mapped,
dual-write IS enabled. The failure is at the Redis level — the xadd to the work-lane
stream raises an exception. Most likely causes (ranked):

1. **Wrong-type key collision:** `bifrost:work:inbox:<agent>` or `bifrost:work:broadcast`
   exists as a non-stream Redis type (string/list/set) from a pre-lane-rename epoch.
   Redis refuses XADD to a non-stream key with WRONGTYPE.

2. **Connection exhaustion:** The fresh `Bus(agent)` in triage_park.py creates a NEW
   Redis connection from the pool. If the pool is drained, this blocks/times out.

3. **Maxlen overflow with approximate=False somewhere:** If a prior write set
   `approximate=False` on a tiny maxlen, the stream could be at capacity and refusing.

The fix likely RIDES C's packet layer because the `idempotency_key` seam touches the
same `_emit` path. Adding the key to the stamped envelope and checking it at consume
time means we're already modifying the send door — fixing the lane-key collision
(or adding a self-heal on WRONGTYPE) is a natural ride-along in the same slice.

---

## FOUR QUESTIONS — INDEPENDENT DERIVATION

### Q1: KEY DERIVATION — stable logical request identity

An `idempotency_key` must survive:
- Process restart (RB-26: runner crashes, work redelivers)
- Dual-write twins (T044: same message on work lane + legacy)
- Re-asks (T112: same payload re-sent 39 minutes later)
- Fragmentation (T043: one message split across N fragments)

**My derivation:**

The key = `sha256(frm || kind || canonical_content || idempotency_seed)`

Where:
- `frm` = sender agent id (stable across restarts)
- `kind` = message kind (note, reply, handoff, etc.)
- `canonical_content` = the byte-normalized content (json.dumps with sorted keys for dicts)
- `idempotency_seed` = an explicit NONCE the PRODUCER assigns:
  - For a NEW logical request: `uuid4().hex[:16]` — random, unique, stamped by the producer
  - For a REDRIVE: the ORIGINAL message's `idempotency_key` is COPIED forward
    (RB-26: the reaper re-sends with the same key, so the consumer sees it as a duplicate)
  - For a RE-ASK: SAME key as the original (T112: the suppressor returns the original mid
    AND stamps the same key — consumer dedup, not send-dedup)
  - For a REPLY: `f"{ask_idempotency_key}:reply:{reply_seq}"` — derived from the ask,
    so the asker knows which reply pairs with which ask

This is a PRODUCER responsibility. The send door (`_emit`) ALWAYS stamps it.
If the caller omits it, the door auto-generates a fresh seed.

Why NOT sha(content) alone: two identical "yes" replies to two different asks would
collide. The seed ties the identity to the LOGICAL work item, not the literal bytes.

Why NOT the Redis stream id: stream ids are transport-specific. The key must survive
cross-store migration (JSON → SQLite era, and back).

### Q2: DUPLICATE SENTINEL-SKIP AT THE CONSUMER

A duplicate is a message whose `idempotency_key` has ALREADY BEEN PROCESSED by this consumer.
The sentinel is a Redis key: `{ns}:idem:{consumer_agent}:{idempotency_key}` → `"done"` with TTL.

**Semantics:**
- On FIRST DELIVERY: the consumer checks the sentinel. Key missing → NOT a duplicate.
  Process the message. AFTER processing succeeds, SET the sentinel with a TTL (e.g., 7 days).
- On REDELIVERY (crash, twin, re-ask): the consumer checks the sentinel. Key exists → SKIP.
  Return a no-op ACK (the stream advances past it; the caller never sees it).

**The TTL question:** 7 days is long enough that a genuine re-ask (human re-sending
a dropped handoff) within a reasonable window hits the sentinel, but short enough
that Redis doesn't accumulate infinite idempotency keys. The TTL is a DIAL, not a constant.

**Scope:** Per-CONSUMER, not global. If agent A processes a message and agent B receives
the same message independently (e.g., a broadcast), B must process it. The sentinel
is `consumer_agent`, not `message_id` alone.

**Skip vs. error:** A duplicate is a NORMAL condition (at-least-once delivery).
It produces NO error, NO log line at WARNING or above. At DEBUG: "idempotency skip <key>."

### Q3: EXACTLY-ONCE SETTLEMENT UNDER REDRIVES + TWINS

The hard case: a redrive (RB-26 crash-redelivery) of a message whose REPLY was already
sent but whose REPLY LANDED ON THE WRONG ASK (the T117 P6 defect — dual-id alias bug).

**My derivation:**

The settlement chain is: `ask.idempotency_key → reply.idempotency_key → settled`

1. Producer stamps `ask` with `idempotency_key = A`
2. Consumer processes ask, stamps reply with `idempotency_key = f"{A}:reply:0"`
3. Consumer SETs `{ns}:idem:{consumer}:{A}` = `"done"` AFTER reply is sent
4. If the ask redrives (crash before step 3 completes): consumer sees `{A}` → SKIP
   (already processed, or processing — the sentinel covers both)
5. If the REPLY redrives: the ASKER checks `{ns}:idem:{asker}:{A}:reply:0` → SKIP

**The twin case (T044 dual-write):**
- Work-lane copy arrives → consumer processes → SET sentinel
- Legacy copy arrives → consumer checks sentinel → SKIP
- No dual-id alias needed — the `idempotency_key` is the SAME on both copies
  (it's stamped at `_emit` BEFORE the lane/legacy split)

**The re-ask case (T112):**
- Original ask sent → `idempotency_key = A`
- 39 minutes later, same ask re-sent → T112 suppress returns original mid
  AND the new send carries `idempotency_key = A` (same key)
- Consumer sees `{A}` → SKIP → no second reply, no wrong-work settlement

**The expectation-settlement case:**
- `expectations.sweep()` currently uses FIFO to match replies to asks
- With `idempotency_key`: the reply carries `{A}:reply:0` — the expectation
  system can match by key, not by FIFO position
- This makes T117's dual-id alias mechanism UNNECESSARY — the key travels
  with the packet; nothing to reconstruct from stream ids

### Q4: STRANGLER MIGRATION OVER LIVE LANES

We cannot turn off the bus. Messages are flowing. The migration must be incremental.

**Phase 1: PRODUCER STAMP (this slice)**
- `_emit` stamps `idempotency_key` on EVERY outgoing packet
- If the caller provides it: use it (redrive, re-ask, reply)
- If the caller omits it: auto-generate fresh
- `idempotency_key` is a NEW field in the stream envelope (like `sha`, `len`, `frag`)
- Legacy consumers IGNORE unknown fields (Redis XREAD returns all fields; they skip what they don't recognize)
- OBSERVE: all sends now carry the key; zero consumer behavior change

**Phase 2: CONSUMER CHECK (next slice, gated on Phase 1 soak)**
- `work_drain` checks `{ns}:idem:{consumer}:{key}` before delivering a message
- Consumer SETs the sentinel after successful processing
- OBSERVE: duplicates silently skipped; crash-redelivery safe

**Phase 3: EXPECTATION MATCH (follow-on, gated on Phase 2)**
- `expectations.sweep` matches by `idempotency_key` instead of FIFO
- Removes the dual-id alias mechanism
- OBSERVE: T117 P6/P7 subsumed

**Phase 4: RETIRE POINT FIXES (cleanup)**
- Remove T112 re-ask collapse (the consumer now deduplicates)
- Remove per-runner `_reply_already_sent` sentinel (the consumer door does it)
- Remove T117 dual-id alias (expectations match by key)

**The strangler's safety invariant:** at every phase, the OLD behavior still works.
A message without `idempotency_key` (pre-Phase-1, or from an old runner)
degrades to current behavior: delivered, no dedup. The new field is additive.

---

## SEND-SEAM FIX (rides C's _emit changes)

The lane-write failure for notes/triage-receipts is almost certainly a WRONGTYPE
error: `bifrost:work:broadcast` or `bifrost:work:inbox:<agent>` exists as a non-stream
key type from a pre-C6-7 epoch when lane keys had different names.

**Fix (rides in Phase 1):** In `_emit`, before the `xadd` to the lane key, check the
key type with `TYPE`. If it's NOT a stream (or missing): `DEL` the key, then `XADD`
(which auto-creates a stream). This is a self-heal — the lane key is a cache of the
append-only lanes; deleting a wrong-type key is safe because the durable truth is
in the legacy stream and the store.

Alternative: rename the lane key to include a version suffix (`bifrost:work:v2:broadcast`)
so the old wrong-type key is naturally bypassed. The `lane_stream_key` function is the
single point of change.

---

## SUMMARY: what this half proposes

1. `idempotency_key` = `sha256(frm || kind || canonical_content || seed)` — producer-stamped
2. Consumer sentinel = `{ns}:idem:{agent}:{key}` → `"done"` with TTL
3. Duplicates → SKIP (normal, not error). Settlement matches by key, not FIFO.
4. Strangler: Phase 1 (stamp only, this slice) → Phase 2 (consumer check) → Phase 3 (expectation match) → Phase 4 (retire point fixes)
5. Ride-along: self-heal lane-key WRONGTYPE in `_emit` (fixes the 23-legacy-straggler defect)
