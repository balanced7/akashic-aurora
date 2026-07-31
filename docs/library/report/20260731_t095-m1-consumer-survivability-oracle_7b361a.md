---
akashic_id: art_20260731_t095-m1-consumer-survivability-oracle_7b361a
akashic_sha: cabd6ed5c0e5
schema_version: 1
status: current
type: report
arc: T095
date: 2026-07-31
title: t095-m1-consumer-survivability-oracle
gist: "# T095-M1 Consumer Survivability Oracle — deepseek 2026-07-31 **Scope:** Given the committed transport + mailbox code (universe 95e0c55 — T0"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [library]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-31T12:58:17"
updated: "2026-07-31T12:58:17"
---
<!-- GENERATED PROJECTION of art_20260731_t095-m1-consumer-survivability-oracle_7b361a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t095-m1-consumer-survivability-oracle

# T095-M1 Consumer Survivability Oracle — deepseek 2026-07-31

**Scope:** Given the committed transport + mailbox code (universe 95e0c55 — T095-M1 GREEN), replay on paper: logical mail arrives; incarnation A reads then dies before declaring intent; incarnation B later lists the same mail, opens its full body, and may act. Add Redis death + redrive/duplicate cases. Each step marks DERIVED / OBSERVED / UNKNOWN. Name the canonical object, or prove none exists.

**Constraint:** Only read current code + governing docs; zero product-code edits.

### ⚠️ PROVENANCE ERRATUM (2026-07-31) — READ BEFORE CITING

The original header (S1 filing) declared universe `9eb9482` (T095-M1 RED pre-registration, pins only, zero M1 implementation). Every claim below describes the **95e0c55** world (T095-M1 GREEN, where M1 landed). At `9eb9482`, `core/comm/mailbox.py` is the M0 shadow module only — `open()`, `declare_intent()`, `state_for()`, `seen_by()`, `identity_of()`, `body_of()`, and all body/intent/seen machinery **do not exist**. `_ingest_one()` at 9eb9482 stores exactly `{sha, kind, frm, ts, ids, ts_s}` — no body, no seen, no intent.

**Re-derived verdicts against 9eb9482 would read:**
- Authority matrix rows for seen receipt + intent: **UNKNOWN** (keys don't exist)
- Replay Steps 2, 5, 6 (open/seen_by/state_for): **UNKNOWN** (functions don't exist)
- KD-1 (double-act): **PARTIAL** — M0 has tiers, no seen/intent
- KD-2 (Redis amnesia): **N/A** — no M1 writes to lose
- KD-3 (truncated body): **N/A** — no body store in M0
- WA-2 (seen_by blocks open): **N/A**
- WA-4 (rebuild recovers seen/intent): **N/A**

The oracle is mechanically correct against 95e0c55 (verified independently by kimi, cross-steer S2, 10×10 table, zero factual errors). The breach was declaring the wrong commit — the RED pre-registration instead of the GREEN implementation. Preserved here rather than silently rewritten per Codex's S1 correction.

**Reconciliation gate:** S3 filed 2026-07-31. PAIR-KD-T095-01 closed. Two steers accepted (seen/intent falsifier → kill drill; fragmented-body → kill drill). One preserved disagreement (reply/handoff settlement seam, for M3).

---

## 1. Authority Matrix

| Object | Canonical Key | Reads | Writes | Survives incarnation death? | Re-derivable? |
|--------|--------------|-------|--------|----------------------------|---------------|
| Lane stream | `{ns}:{lane}:inbox:{agent}` | Bus._drain() | Bus._emit() | yes (Redis Stream) | no (the log) |
| Legacy stream | `{ns}:inbox:{agent}` | Bus._drain() | Bus._emit() | yes (Redis Stream) | no (the log) |
| Shared cursor | `{ns}:cursor:{agent}` | Bus._read_cursor() | Bus.advance_to() (Lua) | yes (Redis hash) | no (position of record) |
| Lane cursor | `{ns}:cursor:lane:{agent}[#{sid8}]` | Bus.read_lane_cursor() | Bus.advance_to() (Lua) | yes (Redis hash) | no (position of record) |
| Seat cursor | `{ns}:cursor:seat:{agent}#{sid8}` | Bus._drain() | plain HSET | yes | no |
| **Mailbox index entry** | `{ns}:mailbox:msg:{agent}:{sha}` | body_of() | catch_up._ingest_one() | **yes** (Redis hash, tiered retention) | **yes** (`rebuild()`) |
| **Mailbox seen receipt** | `{ns}:mailbox:seen:{agent}` field `{sha}\|{incarnation}` | seen_by() | open() | **yes** (Redis hash) | **no** (not in the log; lives only in `{ns}:mailbox:*`) |
| **Mailbox intent** | `{ns}:mailbox:intent:{agent}` field `{sha}` | state_for() | declare_intent() | **yes** (Redis hash) | **no** (not in the log) |
| Mailbox answered | `{ns}:mailbox:answered` | _resolve() | _ingest_one() | yes (Redis global) | yes (re-derived from lane) |
| Mailbox index positions | `{ns}:mailbox:pos:{agent}` | catch_up() | catch_up() | yes | yes (rebuilt from zero) |
| Consumer generation | `{ns}:generation:{agent}` | runner_lock.acquire() | runner_lock.acquire() (INCR) | yes | no |

**KEY INSIGHT:** Mailbox seen receipts + intents (the M1 writes) live in `{ns}:mailbox:*` — a container the governing design explicitly calls a "regenerable projection" (packet_spec.py:255-259). BUT: only the INDEX is rebuildable (`rebuild()` drops `pos`, `z`, and `msg:*` and re-derives them from streams). The `seen` and `intent` hashes are NOT rebuilt by `rebuild()` — grep `mailbox.py` confirms `rebuild()` only clears `z`, `pos`, and each `msg:`, never `seen` or `intent`. **These are durable but non-rebuildable: a Redis flush loses them permanently.**

---

## 2. Replay: The Happy Path + Death + Redrive

### Step 1: Logical mail arrives [OBSERVED]

Code path: `Bus._emit()` → lane-first `xadd` to `bifrost:work:inbox:deepseek`, legacy fallback `xadd` to `bifrost:inbox:deepseek`. `_emit()` returns the legacy mid. Mailbox `catch_up()` (called by any `query()`, `open()`, or `state_for()` consumer) reads BOTH sources from their last `pos` and calls `_ingest_one()`.

`_ingest_one()` (mailbox.py:174-222) does:
1. Compute sha via `identity_of()` — uses `message_id` > `idempotency_key` > `packet_sha` > content fallback.
2. Store in `{ns}:mailbox:msg:{agent}:{sha}` as a Redis hash with fields: `sha`, `kind`, `frm`, `to`, `ts`, `ids` (JSON map of source→stream_id), `ts_s`, **`body`** (up to 64KB), `body_truncated`, `body_len`, `identity_basis`.
3. `zadd` to `{ns}:mailbox:z:{agent}` with the timestamp score.

**The body is co-located with the index entry.** It does NOT point at the ephemeral lane; it stores the content in the same hash. This is the D2 fix (mailbox.py:468): "the BODY now lives on the entry, an entry and its body expire together by construction — the 30-day-index-pointing-at-a-7-day-stream promise can no longer be made."

### Step 2: Incarnation A reads [OBSERVED → DERIVED]

A calls `mailbox.query("bifrost", "deepseek")` → sees entry with sha X. A calls `mailbox.open("bifrost", "deepseek", sha_X, incarnation="session-abc123")`.

`open()` (mailbox.py:489-509):
1. Calls `body_of()` — reads the body from `{ns}:mailbox:msg:{agent}:{sha}` hash. Returns full body (or truncated flag if >64KB). **Body exists independent of lane stream survival.**
2. Writes one receipt: `HSET {ns}:mailbox:seen:{agent} "{sha}|session-abc123" = <unix_ts>`.
3. Returns `{"ok": True, "first_open_by_this_incarnation": True, "seen_by": [...], "sha": ..., "kind": ..., "body": "...", ...}`.

No cursor is advanced. The message remains "unhandled" in the mailbox tier since `open()` writes only to `seen:*`, never to any cursor, ack, or answers key.

### Step 3: Incarnation A dies before declaring intent [DERIVED]

A crashes. Process death. Runner lock TTL expires (`LOCK_TTL=20s` for runner, `SESSION_CONSUMER_TTL=1800s` for session consumer — runner_lock.py:43,47). The generation key `{ns}:generation:{agent}` remains at its last incremented value. The shared/lane cursors remain at whatever A advanced them to.

What remains in Redis:
- `{ns}:mailbox:seen:{agent}` — field `{sha}|session-abc123` = timestamp (A's seen receipt)
- `{ns}:mailbox:msg:{agent}:{sha}` — the full index entry with body
- `{ns}:mailbox:intent:{agent}` — **no field for sha_X** (A never declared intent)
- All streams, cursors, generations — untouched by `open()`.

### Step 4: Incarnation B boots and lists mail [DERIVED]

B calls `mailbox.query("bifrost", "deepseek")`. The index entry for sha_X is present (zset + msg hash). The entry's tier is "unhandled" (no ack, no reply, no cursor advance past it). The message appears in the unhandled count.

### Step 5: B opens the full body [DERIVED]

B calls `mailbox.open("bifrost", "deepseek", sha_X, incarnation="session-def456")`.

`open()` returns:
- `first_open_by_this_incarnation: True` (field `sha_X|session-def456` didn't exist)
- `seen_by: [{"incarnation": "session-abc123", "at": <ts>}]` — **B can see A read this mail.**
- Full body from the mailbox hash.

### Step 6: B may act [DERIVED]

B calls `mailbox.state_for("bifrost", "deepseek", sha_X)`. Returns:
```json
{
  "available": true, "found": true,
  "sha": "sha_X", "kind": "handoff", "body": "...",
  "seen_by": [{"incarnation": "session-abc123", "at": ...}],
  "intent": null,
  "read_but_undeclared": true,
  "retention_s": 2592000
}
```

`read_but_undeclared: true` is the load-bearing signal (mailbox.py:552): "somebody opened this and did not say what they would do. Silence is now visible instead of being indistinguishable from absence."

B can now call `declare_intent("act")` — the prior silence doesn't block intent; `declare_intent()` checks only that the sha exists in the mailbox msg hash (mailbox.py:537) and that the intent vocabulary is valid. **No "already seen by another incarnation" gate exists** — that would be the gap Daniil named. B can act.

### Step 7: Redis death between ingest and open [DERIVED]

Redis dies after catch_up ingests the entry but before open(). All mailbox state (`msg:*`, `seen:*`, `intent:*`, `z:*`, `pos:*`) is gone. But the lane streams survive Redis restart or not at all (Redis Streams are in-Redis only). 

If Redis restarts from persistence: the streams are there; the mailbox is empty. `catch_up()` will re-ingest from `pos=0-0` (all positions lost) and rebuild the full index. **The seen receipt is GONE** — `seen:*` is NOT re-derived by `rebuild()` or `catch_up()`. A's prior read becomes invisible.

If Redis is permanently lost: the mailbox is gone, the lane streams are gone. The entire transport state is reset. This is the known ephemeral-transport contract (bus.py:13): "Ephemeral, not the durable record."

### Step 8: Duplicate/redrive cases [DERIVED → OBSERVED]

**Dual-write duplicate (same send, two stream ids):** `_ingest_one()` is called twice (once per source — work inbox + legacy inbox). First call creates the msg hash with `ids: {"work_inbox": "X", "legacy_inbox": "Y"}`. Second call updates `ids` to add the second stream id. The body is never clobbered with an empty one (mailbox.py:207: "Never clobber a stored body with an empty one — the same message arrives on several sources and only some carry content"). `identity_of()` returns the same sha both times (same content/message_id). Result: ONE index entry, two stream ids in `ids`.

**Re-ask collapse (T112):** Bus._emit() → `_reask_original()` returns the prior mid if the same (from, to, kind, content) exists within the window AND the original is still in the stream. The re-ask never reaches the stream or the mailbox. The prior seen/intent records remain valid — same sha, same message.

**Redrive (expectations):** A redrive sends a NEW packet with `meta.redrive_of` set. Bus._emit() → `_reask_original()` checks for redrive_of and returns None (never collapses a redrive — bus.py:431-434). The new packet gets a new identity (new ts → new sha, or new message_id). It lands in the mailbox as a separate entry. **A prior seen/intent on the original does NOT transfer to the redrive copy.**

**Rehome (reaper):** Similar to redrive — carries `meta.rehomed_from`/`meta.original_mid`, explicitly exempted from re-ask collapse. New identity, new mailbox entry.

---

## 3. Three Kill Drills

### KD-1: Incarnation B acts on mail A already handled (the silent double-act)

**Setup:** A reads mail, declares `act`, processes it (advances cursor past the message), but the mailbox retains the msg entry (tiered retention, not evicted). B boots, queries mailbox, sees the entry as "consumed" (cursor advanced). B calls `open()` — gets `first_open_by_this_incarnation: true`, sees A's prior seen receipt + intent = "act". B calls `state_for()` — sees `intent: {intent: "act", by: "session-abc123", ...}`.

**Kill mechanism:** `state_for()` returns the prior intent. B must read it. There is NO machine-enforced block on B also declaring `act`. The governing design (mailbox.py:456-463) says: "Consumption stays the cursor's business; settlement stays the instrument's; judgement stays the agent's." The mailbox arms the operator, it does not enforce.

**What prevents disaster:** The cursor HAS advanced past the message — so if B tries to consume it via the normal drain path, the message is not re-delivered (cursor is past it). The risk is B acting through the mailbox path alone (query→open→declare_intent→act), bypassing the cursor entirely. This is the "advisory claims" gap — M1 is OBSERVATIONAL still for consumption; claim-driven consumption is M3.

### KD-2: Redis death wipes seen receipts; incarnation C re-adjudicates blindly

**Setup:** A reads mail, declares `decline`. Redis dies. Restarts. Mailbox rebuilds from streams — the msg hash is rebuilt, the zset is rebuilt. `seen:*` and `intent:*` are NOT rebuilt (grep confirms `rebuild()` clears `z`, `pos`, `msg:*` only — line 399-401). B boots, calls `state_for()` → `found: true, seen_by: [], intent: null, read_but_undeclared: false`. **A's decline is invisible.** B re-adjudicates from scratch.

**Kill mechanism:** The `seen` and `intent` hashes live in `{ns}:mailbox:*` but are outside `rebuild()`'s scope. The governing design (packet_spec.py:255-259) classifies the entire `{ns}:mailbox:*` namespace as a "regenerable projection" — but this is only true for the INDEX half. The M1 writes (seen/intent) are NOT regenerable from the log. They survive only as long as Redis survives. This is by design (the mailbox is an index, not the durable record), but it means a Redis flush is a full amnesia event for M1 state while the streams remain — the worst asymmetry.

### KD-3: Truncated body on oversize mail; incarnation opens partial content

**Setup:** Sender sends a 200KB message. `_emit()` fragments it (T043 auto-frag). Each fragment carries `frag={seq,of,whole_id,...}`. Reassembler buffers fragments in `Reassembler._buf`. The mailbox's `_ingest_one()` sees each fragment envelope independently — the fragment carries a partial `content` field. The BODY_MAX is 64KB. 

**What happens:** `_ingest_one()` stores `body = content[:BODY_MAX]` (64KB cap) with `body_truncated = "1"`. For a fragmented send, the FIRST fragment's content is a partial slice. The mailbox entry records the first fragment's partial content, NOT the reassembled whole. Later fragments update `ids` but the body is "never clobbered" (line 207) — so the first partial body persists.

**Kill mechanism:** `open()` returns `truncated: true` and `body_len: 200000` but the actual `body` field is only the first fragment's bytes. The caller sees truncated=true and can KNOW the body is incomplete, but cannot reconstruct the full 200KB from the mailbox alone — the remaining fragments aged out of the ephemeral lane streams. **The mailbox's body store is an MTU-bounded convenience, not a lossless archive for fragmented mail.** Recovery requires the lane streams, which are ephemeral.

---

## 4. Specific Wrong Answers

### WA-1: "`open()` advances the cursor"

**FALSE.** `open()` (mailbox.py:489-509) writes exactly one HSET to `{ns}:mailbox:seen:{agent}` and reads `body_of()`. Zero cursor writes. The governing docstring is explicit: "Does NOT advance any cursor. The falsifier for that claim is a pin, not this sentence." The cursor ONLY advances through `Bus.advance_to()` (guarded Lua) or the seat-cursor plain HSET.

### WA-2: "A prior `seen_by` blocks a later incarnation from opening"

**FALSE.** `open()` checks only that the sha exists in the msg hash. It writes a NEW receipt for the caller's incarnation regardless of how many prior incarnations have seen it. The return includes `seen_by: [...]` so the caller KNOWS about prior readers, but the call always succeeds for a valid sha. The machine never blocks.

### WA-3: "The mailbox's body is the same as the lane stream entry"

**FALSE — only for non-fragmented, non-dual-write cases.** For dual-write, `_ingest_one()` is called twice: first with body from whichever source arrives first (work lane carries content, legacy may not — only some sources carry content, line 207). For fragmented sends, the body is one fragment's partial content, not the reassembled whole. For truncation, body is capped at 64KB even if the original was larger. The body in the mailbox is a SNAPSHOT, not a pointer to the authoritative stream entry.

### WA-4: "`rebuild()` recovers seen receipts and intents"

**FALSE.** `rebuild()` (mailbox.py:393-414) deletes the zset, pos, and each `msg:*` key, then re-runs `catch_up()` from zero. It never touches `seen:*` or `intent:*`. Those survive a rebuild — but they do NOT survive a Redis flush. They are durable across rebuilds, ephemeral across Redis restarts. The asymmetry is undocumented in the mailbox module itself but visible in the packet_spec roster (line 259: `"*:mailbox:*"` classified as ephemeral Redis-only).

### WA-5: "A message redrive reuses the same mailbox entry"

**FALSE.** Redrive sends a NEW packet with `meta.redrive_of`. It gets a new identity (new ts, different sha via canonical_bytes which includes ts). It creates a NEW mailbox entry. The original entry with its seen/intent records remains separate. There is no cross-referencing between the original and the redrive copy in the mailbox — they share logical content but not identity.

---

## 5. Summary Verdict (amended per S3 reconciliation, Kimi cross-steer S1+S2)

The T095-M1 machinery correctly survives incarnation death for the READ path: a later incarnation can discover prior seen state and prior intent, and the body is co-located with the index entry (independent of ephemeral lane survival). The gaps are:

1. **No enforcement** — `state_for()` arms B with A's prior intent, but nothing prevents B from acting anyway. The mailbox is advisory; enforcement is M3.

2. **→ PROMOTED TO KILL DRILL (Kimi S1): Seen/intent amnesia on Redis restart** — the index is rebuildable from streams; the M1 writes are not. A full Redis restart makes prior reads invisible. This is not a "gap" — it is a **falsifier of the product receipt**: "B can see that A read it" fails after Redis restart. Kill drill: A opens → Redis FLUSHALL → rebuild() → B calls state_for() → `seen_by: [], read_but_undeclared: false`. Assert this is CORRECT for the current design. Product receipt amended to scope "survives incarnation death" to "within a single Redis lifetime." Falsifier: a canonical seen/intent store outside `{ns}:mailbox:*` — none exists.

3. **→ SPLIT INTO KD-3a + KD-3b (Kimi S2): Fragmented body hazards.** KD-3a: single oversize message > 64KB → `body_truncated="1"`, honest truncation. KD-3b: fragmented send with each fragment < 64KB → `body_truncated="0"` but body is a fragment slice, **a silent lie**. `_ingest_one()` has zero fragment awareness — never checks `meta.frag`. Kill drill: send 4×50KB fragments → mailbox stores 50KB slice → open() returns `truncated=false` for a 25% body. Assert this is WRONG. Falsifier: reassembler feeds mailbox, or `_ingest_one()` checks `meta.frag` — neither exists.

The canonical object a fresh incarnation consults is `state_for()` (mailbox.py:544), which in one Redis round-trip returns: the body, all seen receipts, the current intent, and the `read_but_undeclared` flag. The consumer survivability contract holds **within a single Redis lifetime**: logical mail arrives, A reads and dies, B lists/opens/acts — with visibility into A's ghost.
