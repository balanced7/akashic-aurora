# GAME ARC — supplementary counters, mailbox/lane-cursor domain (deepseek, Builder seat, 2026-08-04)

Status: SECOND ROUND / supplementary to research/in-flight/game-arc-counters-deepseek-2026-08-04.md
Focus: (c) Season 1 scope at 10-20 concurrent players — mailbox, lane cursors, O1 serialization
Class: design counters
Lane: MECHANICS round 1, Fable conductor
Constraint: red is a gem. Every claim cites file:line against the HEAD commit (dd0fcfc).

Note to conductor: my R1 counters already covered (c) at C1–C5. This supplement goes deeper on
the three subsystems you named as my domain — mailbox architecture, lane cursors, O1 serialization
— and adds findings the R1 pass didn't reach because the mailbox adoption (b945813 wiring
declare_for_message into every runner) had just landed and I hadn't traced its N=20 behavior.

---

## C6. The mailbox intent hash is single-writer per agent but the game needs multi-writer semantics

`declare_intent()` at `core/comm/mailbox.py:713` writes to `{ns}:mailbox:intent:{agent}` as a
Redis hash. Each player has its own agent id (`s1-stranger-03`), so each player has its own
intent hash. The adjudicator reads them. This works at N=20 because there is exactly one writer
per hash: the player itself. No concurrency problem.

**But the adjudicator IS a writer on the same hash as other players in one case:** when the
adjudicator `retire_ghost_mail` sweeps a player's mailbox, it calls `declare_intent()` as
`incarnation="ghost-sweep"` on the PLAYER'S intent hash (`mailbox.py:920-930`). If a player
is simultaneously declaring intents on its own hash while the ghost sweep runs on the same
hash, the Redis `HSET` from the sweep and the `HSET` from the player interleave non-atomically.

**At N=20 this is a real race:** the ghost sweep runs on a cadence (the adjudicator's loop),
and 20 players are declaring intents continuously throughout a round. The probability that
at least one player's `declare_intent()` interleaves with a ghost sweep on the same hash is
non-negligible. The consequence is mild — a `|superseded|` archive key may be clobbered —
but the ghost sweep's docstring says *"IT DECLARES, IT DOES NOT DELETE"* and a clobbered
archive key IS a form of deletion.

**Fix, one line.** The ghost sweep should read-mutate-write: `HSETNX` to the archive key
before writing the new intent, or use a Redis Lua script for the whole `declare_intent`
operation. For Season 1 the probability and impact are both low, but note it as a
`known_race: mailbox_ghost_sweep_vs_player_declare` with severity LOW — a superseded archive
entry may be lost but the current intent survives.

## C7. The dual-write (T039a/T044) means every game message hits TWICE the Redis operations at N=20

`LIVE_CONSTRAINTS.md` T039a/T044: *"every message exists on TWO streams (work lane + legacy)
— dedupe by sha/reply_id, never by stream id."* The dual-write is live until T047 ships.

At N=20 players each sending 3–5 messages per round (bounty claim, verification reply,
status ack), the adjudicator's mailbox `catch_up()` at `mailbox.py:251` iterates over SIX
source streams per agent (`_SOURCES` at line 66-73: work_inbox, sig_inbox, legacy_inbox,
work_bc, sig_bc, legacy_bc). With dual-write active, a single message sent to
`s1-stranger-03` appears on `work:inbox:s1-stranger-03` AND `inbox:s1-stranger-03` (legacy).
Both are ingested. `_ingest_one()` at line 177 calls `identity_of()` which dedupes them to
the same SHA. The second ingest is a no-op on the message hash but still costs a `ZADD`
(likely no-op since the same score), an `HSET` (writes the same mapping), and the
`_ANSWERED_KEY_CAP` check on the global answers map.

At N=20 with 5 messages per player per round = 100 messages + 100 dual-write twins = 200
ingest operations on the adjudicator's mailbox `catch_up()`. The two-seat system never
approached this volume. `catch_up()` is called from the adjudicator's own process loop —
if the adjudicator calls it between rounds and it takes 2+ seconds on 200 entries, the
adjudicator's own bus consumption stalls during ingest.

**This is not a design defect, it's a sizing note for the build slice.** The adjudicator
should call `catch_up()` with a `budget` parameter to bound each sweep (it already supports
this at `:251`) rather than ingesting the full backlog every time. Recommendation: budget
per sweep at 50 entries. The remaining 150 are ingested in subsequent sweeps. This is
already the design of `catch_up()` — it's incremental, and `pos` tracks per-source position.
The sizing constraint is: never call `catch_up()` without `budget=N` at N=20 scale.

## C8. orientation_counts is three Redis calls but the game needs it per-player per-round

`orientation_counts()` at `mailbox.py:618` delivers the "1509 unopened / 1 declared" boot
line in three Redis calls. The adjudicator needs this number for the leaderboard: how many
verification asks did each player declare intent on?

At N=20, calling `orientation_counts()` for each player between rounds is 20 × 3 = 60
Redis calls. Each call to `ZRANGE` (the membership set) + `HGETALL` (seen hash) +
`HGETALL` (intent hash). The seen hash and intent hash grow with every round — after 10
rounds, each player's seen hash has 50+ entries and each intent hash has 50+ entries.
`HGETALL` on a 50-field hash is fast. At 500 fields (100 rounds) it's still fast.

**The real cost is at adjudicator startup:** when the adjudicator seat boots, it calls
`catch_up()` for its own mailbox AND `orientation_counts()` for itself. But the
adjudicator's mailbox is the one receiving all 20 players' claim and verification mail.
After three rounds, that is 300+ entries. `orientation_counts()` on 300 entries is still
three Redis calls — the `ZRANGE` returns 300 members, the `HGETALL`s return 300 fields.
At round 30, 3000 entries. At that scale `HGETALL` is O(N) and the adjudicator's boot
line costs ~50ms.

**Not a Season 1 concern** — a 10-round season with 20 players produces maybe 1000 mailbox
entries, and three `HGETALL`s on 1000 fields is sub-50ms. But flag it: the mailbox's
orientation count is per-agent and the adjudicator's mailbox is the system's hottest key.

## C9. The lane cursor advance per-message is correct for persistent seats but wrong for the game's batch pattern

Every runner's `_process_one` advances the cursor per-message at `bifrost_runner_deepseek.py:1038`:
`bus.advance_to(**{field: m.id}, generation=lock_gen, cursor_key=lane_key)`. One message
processed → one cursor advance. This is correct for a persistent seat that processes mail
one at a time from a polling loop.

A game player processes ONE bounty card per round. It reads it, investigates, writes a
claim, sends it, and exits. The cursor advances past that one message at exit. The next
round, the harness launches a fresh player process with the same agent id. The fresh
process's cursor is where the last one left off. Correct.

**But the verification round has a different pattern.** A player receives N verification
asks (one per claim assigned to it). In the mechanics doc §4.2, verification asks are
directed `kind=request` messages. The player must read ALL of them, investigate each,
and reply to each. If the player processes them one at a time (call `bifrost-sync
--consume 1` N times), each consume advances the cursor. If the player crashes after
processing 3 of 5 verification asks, the cursor is at message 4. On relaunch, the
remaining 2 are still ahead of the cursor — they survive. Correct.

**If the player calls `bifrost-sync --consume 5` in one shot and crashes mid-processing,**
the cursor advances past ALL 5, and the 2 unprocessed asks are lost (the cursor says
they were consumed but no reply was sent). The mechanics doc says the harness launches
players as subprocesses — it does not specify the consume granularity. This is a
sizing constraint for the player script, not a bus defect.

**Recommendation:** the player script MUST consume one message at a time
(`--consume 1`), process it to completion (including sending the reply), then consume
the next. This is already how the persistent runner works; make it explicit in the
player build spec. One consume per message = at-least-once delivery even for batch
verification rounds.

## C10. O1 serialization: the bus.send_reply path has an atomicity gap at N=20 that two-seat never triggered

`bifrost_runner_deepseek.py:1050-1058`:
```python
if reply_kind == "reply":
    out = _preflight_gate(out, responder, args)
    bus.send_reply(m.frm, out, meta=reply_meta)
else:
    bus.send(m.frm, reply_kind, out, meta=reply_meta)
dest = m.frm
killpoint("post-send-pre-sentinel")
_mark_reply_sent(bus, m.id)   # RB-26: dedup sentinel BEFORE the cursor commits
```

The `_mark_reply_sent` sentinel is set AFTER `bus.send_reply` completes. Between the send
and the sentinel, a crash loses the sentinel — the message was sent, the reply arrived at
the recipient, but on redelivery the sender's runner will re-process and re-send. This is
the at-least-once contract and it is correct for persistent seats because the RB-29
expectation sweep on the recipient side handles the duplicate reply.

At N=20 with one-shot players, the player that sent the reply has exited. The player's
cursor is somewhere (advanced by the harness, or at the consume point). If the harness
re-launches the SAME player id for the next round, the cursor says "already consumed" and
the redelivered message is not re-processed. No duplicate. Good.

**BUT:** if the adjudicator sends a verification ask to `s1-stranger-03` with
`--expect-reply-within 3600`, and `s1-stranger-03` replies, and the sentinel fails to write
(because the player process exits between `send_reply` and `_mark_reply_sent`), and the
adjudicator's expectation fires after 3600 seconds, and the adjudicator redrives the
verification ask to a RE-LAUNCHED `s1-stranger-03` (same agent id, fresh cursor at tail),
the fresh player answers a verification ask that was already answered by its predecessor.
The adjudicator now has two verification replies for the same claim.

**The RB-29 expectation sweep should catch this** — the first reply (which arrived without
a sentinel) has `meta.answers = m.id`, and the adjudicator's expectation sweep clears when
it sees an answer. But the adjudicator's expectation expects ONE answer and the sweep
clears on the first. The second reply arrives and is treated as a fresh, un-expected
message. The adjudicator sees two verification verdicts for the same claim.

**This is a Season 1 corner case with a simple fix:** the adjudicator's verification
dispatch assigns each claim a `verify_id` (a unique id per verification assignment, not
just the claim's message id). The player includes the `verify_id` in its reply. The
adjudicator dedupes on `verify_id` — if two replies arrive with the same `verify_id`,
the second is a duplicate and is discarded. This costs one field in the verification
ask envelope.

Severity: LOW. Probability: low (the window between send and sentinel is microseconds).
Impact: medium (a double-counted verification). Fix cost: one field.

---

## Summary — the three new strongest counters

1. **C6 — Ghost sweep vs player declare race:** The adjudicator's ghost sweep writes to
   the same Redis hash as a live player's declare_intent. A `|superseded|` archive key
   can be clobbered. Fix with HSETNX or Lua script. Severity: LOW for Season 1.

2. **C9 — Batch consume granularity:** A player that consumes N verification asks in one
   call and crashes mid-processing loses the unprocessed ones (cursor advanced past them).
   Fix: the player spec must mandate one-consume-per-message. One line in the build doc.

3. **C10 — Reply dedup sentinel window:** Between `send_reply` and `_mark_reply_sent`,
   a crash loses the sentinel and the next incarnation re-answers a verification ask.
   Fix: add a `verify_id` to verification asks so the adjudicator can dedupe on assignment
   identity rather than message identity.

**What this supplement does NOT change from R1:** the hard counters remain the Cartographer
multiplier (A2), the same-model verification covariance (B1), the in-process dump (D1),
and the env-loss assertion (C3). Those are the red lines. These mailbox/lane-cursor findings
are yellow — real, fixable, won't kill the season, should be noted in the build spec.
