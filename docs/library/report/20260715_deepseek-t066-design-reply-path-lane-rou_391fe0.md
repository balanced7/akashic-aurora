---
akashic_id: art_20260715_deepseek-t066-design-reply-path-lane-rou_391fe0
akashic_sha: 37bb4ef3c0e5
status: draft
type: report
date: 2026-07-15
title: DeepSeek T066 Design — Reply-Path Lane Router + Double-Delivery Bug (2026-07-15)
gist: "Author: deepseek (tracing my OWN reply path through the three files) Evidence: event:events:raw:1784082287759-0 + 1784003725351-0 (Daniel's "
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T23:08:48"
updated: "2026-07-14T23:08:48"
---
<!-- GENERATED PROJECTION of art_20260715_deepseek-t066-design-reply-path-lane-rou_391fe0 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T066 Design — Reply-Path Lane Router + Double-Delivery Bug (2026-07-15)

Author: deepseek (tracing my OWN reply path through the three files)
Evidence: event:events:raw:1784082287759-0 + 1784003725351-0 (Daniel's seat)
Files under design: `scripts/bifrost_runner_deepseek.py` `_process_one` reply path,
`scripts/deepseek_chat.py` `Agent.send` reply path, `core/comm/bus.py` `_emit` lane router
seam, `core/comm/bifrost_api.py` `work_drain` straggler net.

---

## PART (a): TRACE — The Reply Send Path and the Lane-Router Miss

### The reply path, end to end

**1. The runner dispatches the reply** (`bifrost_runner_deepseek.py:598-614`):

```python
reply_kind = "note" if nonanswer else "reply"
...
if str(m.to) == "*":
    bus.broadcast(reply_kind, out, meta=reply_meta)
else:
    bus.send(m.frm, reply_kind, out, meta=reply_meta)
```

For a directed reply to claude: `bus.send("claude", "reply", out, ...)`.

**2. `bus.send()` → `bus._emit()`** (`bus.py:220-241`):

```python
mid = str(self._client.xadd(stream, env, ...))  # legacy write: bifrost:inbox:claude
self._touch()
self._lane_write(env, to=to, kind=str(kind))     # lane mirror: bifrost:work:inbox:claude
self._ring_bell(to, mid, str(kind))
```

The legacy write lands the reply on `bifrost:inbox:claude`. Then `_lane_write` attempts to mirror it.

**3. `_lane_write()` → `packet_spec.lane_for("reply")` → `"work"`** (`bus.py:257-291`):

```python
lane = packet_spec.lane_for(kind)        # "reply" → "work" ✓
if lane is None:
    return                                # census miss
target = None if to == BROADCAST_TO else to  # "claude"
key = packet_spec.lane_stream_key(self.ns, lane, to=target)
    # → "bifrost:work:inbox:claude"
self._client.xadd(key, fields, ...)      # ← THIS CAN FAIL SILENTLY
```

**4. The lane xadd is wrapped in bare `except Exception: pass`** (`bus.py:287-288`):

```python
except Exception:
    pass   # advisory in P0; the legacy write above is the delivery
```

### ROOT CAUSE OF THE LANE-ROUTER MISS

**The lane write (`_lane_write`) is best-effort advisory. Any failure — Redis timeout, connection hiccup, stream-not-writable, memory pressure — is silently eaten. The legacy write succeeded (the reply landed on `bifrost:inbox:claude`), but the lane mirror to `bifrost:work:inbox:claude` failed silently.**

The T039a P0 dual-write soak contract (bus.py:263) explicitly declares this: "NOT load-bearing until the T039b cutover — consumers still read legacy, and lane cursors initialize tail-at-flip (A4), so this phase is a live soak of the lane write path, not a data migration."

The contract is CORRECT for T039a — but the system has moved PAST T039a. My runner is in lane-mode (`BIFROST_CONSUME_LANE=work`). Claude's runner is in lane-mode. The work lane IS load-bearing for consumption. But the send side is still on the P0 best-effort dual-write — the lane write can silently fail with zero visibility except for the straggler-net LOUD message on the receiver side.

**The mismatch: consumption is lane-first (T045 stage 2 live), but sending is still legacy-first with lane-as-advisory (T039a P0).** When the lane write fails, the reply lands legacy-only. The lane consumer misses it on the work lane. The straggler net catches it from the legacy shadow — but only on the NEXT `work_drain` cycle (~2min wake-listener re-arm). That's the "landed legacy-only" half of the bug.

---

## PART (b): TRACE — The Double-Delivery

### The straggler-net double-delivery mechanism

`work_drain` at `bifrost_api.py:230-340` reads from THREE sources in order:

1. **Sig lane** (1ms peek) — fidelity-ladder traffic
2. **Work lane** (blocking budget) — the primary consume surface
3. **Legacy straggler net** (1ms peek) — catches packets whose lane write failed

The straggler net (step 3, lines 304-340):

```python
if packet_spec.dual_write_enabled():
    legacy = self.bus.wait(timeout_ms=1, limit=limit,
                           since={"inbox": sh_in, "bc": sh_bc}, since_out=shnxt)
    stragglers = [m for m in legacy
                  if self._dedup_key(m) not in seen
                  and packet_spec.lane_for(...) in ("work", None)]
```

The `seen` set is populated from steps 1 and 2 — it de-duplicates WITHIN ONE `work_drain` call using `_dedup_key(m) = (frm, ts, kind)`.

**Scenario producing double-delivery:**

1. My runner sends `bus.send("claude", "reply", out, ...)` → legacy xadd succeeds, lane xadd silently FAILS
2. Claude's lane-mode runner calls `work_drain()`
3. Step 2 (work lane): the work lane has NO copy (lane write failed) → empty
4. Step 3 (straggler net): reads from legacy shadow, finds the reply → `_dedup_key` not in `seen` → **DELIVERED as straggler** (with `_lane_src="legacy"`)
5. The reply is PROCESSED by claude's runner. The legacy shadow cursor advances past it.
6. Claude's LEGACY consumer (or a second lane consumer on a different cycle with a different shadow position) reads the SAME reply from the legacy inbox
7. The reply is PROCESSED AGAIN

**Why the `_dedup_key` within one `work_drain` call doesn't prevent this**: the two deliveries happen in DIFFERENT `work_drain` calls, or the legacy consumer reads from the shared cursor (not the lane cursor's shadow fields). The `seen` set is per-call, not persistent.

**Why the `_reply_already_sent` sentinel doesn't prevent this**: the sentinel prevents MY runner from re-answering a redelivered message. It does NOT prevent claude's runner from receiving the same reply twice through different consumption paths.

**Why the `answers` meta doesn't prevent this**: the reply carries `meta.answers = m.id` — linking it to the message it answers. But claude's expectation sweep clears on `kind="reply"` — if the straggler delivers it as `kind="reply"` (it does — the lane write failed but the xadd to legacy put the packet there with kind="reply"), the expectation IS cleared. The second delivery still arrives as a bus message, even if no expectation is armed for it.

### The 2-minute gap explained

The first delivery happens through the straggler net in `work_drain` step 3 (1ms peek). The second delivery happens when claude's wake listener re-arms (~2 minutes later) and re-reads the legacy inbox from the shared cursor — which may not have advanced past the reply if the lane consumer's shadow cursor is separate.

**OR**: the first delivery comes from the work lane (the lane write eventually succeeded on retry or a subsequent `_lane_write` call), and the second comes from the straggler net on the next cycle. The `_dedup_key` within one `work_drain` call catches the simultaneous case, but if the lane write is DELAYED (Redis eventual consistency, pipeline batching), the work-lane copy and legacy copy arrive on DIFFERENT `work_drain` cycles.

---

## PART (c): SPEC + PINS

### The two bugs, stated precisely

**Bug 1 (Lane-router miss):** The runner's reply send path (`bus.send` → `_emit` → `_lane_write`) treats the lane write as best-effort advisory (T039a P0 contract). The lane write can silently fail. When it fails, the reply lands on the legacy inbox only. Lane-mode consumers (claude) miss it on the work lane. The straggler net catches it, but only after a delay (~2 min wake cycle).

**Bug 2 (Double-delivery):** The straggler net and the legacy consumer (or a second work_drain cycle) can both deliver the same reply. The `_dedup_key` is per-call, not persistent. The `answers` meta clears the expectation on first delivery; the second delivery arrives as an unexpected duplicate.

### The fix

**The runner's reply send must ensure the lane write succeeds BEFORE declaring the reply sent.** The lane is load-bearing for consumption (T045 stage 2 is live); the send side must match.

#### Spec

**S1 — Reply send is lane-first, not legacy-first.** In `_process_one`, after constructing the reply, the runner writes to the lane stream DIRECTLY (not through `_emit`'s advisory `_lane_write`), verifies the write succeeded, and ONLY THEN writes to the legacy stream as fallback.

**S2 — Lane write failures are LOUD and block the reply.** If the lane xadd fails, retry once (transient Redis blip). If it still fails, the reply goes out as a `"note"` with content `"(lane write failed -- reply may not reach lane consumers; retrying legacy-only)"` — and the legacy write is the fallback. The runner logs the failure at ERROR level.

**S3 — The lane write is the PRIMARY delivery; legacy is the FALLBACK.** The `_lane_write` call in `_emit` stays as-is for non-reply kinds (T039a P0 soak continues). For `kind="reply"` specifically, the runner's `_process_one` calls a NEW method `bus.send_reply(to, content, meta)` that writes lane-first, legacy-fallback.

**S4 — Double-delivery guard: reply carries a unique idempotency key.** Every reply from the runner carries `meta.reply_id = <unique-per-reply-id>`. The receiver's consume loop checks a persistent dedup set (Redis key with TTL = REPLY_TIMEOUT_S * 2) before processing. A duplicate reply_id within the TTL window is skipped.

#### Pins (pre-registered RED → GREEN)

| Pin | Description | Test |
|-----|-------------|------|
| P1 | `bus.send_reply(to, content, meta)` writes to `bifrost:work:inbox:<to>` FIRST, verifies success, THEN writes to `bifrost:inbox:<to>` as fallback | `test_reply_is_lane_first` |
| P2 | Lane write failure → retry once → if still failed → legacy fallback + LOUD log | `test_reply_lane_failure_falls_back` |
| P3 | Reply carries `meta.reply_id` — unique per reply (uuid or timestamp+content hash) | `test_reply_carries_idempotency_key` |
| P4 | Receiver skips duplicate `reply_id` within TTL window (persistent dedup, Redis-backed) | `test_reply_dedup_receiver_side` |
| P5 | Non-reply kinds (chat, note, handoff) continue through existing `_lane_write` path unchanged (T039a P0 soak untouched) | `test_non_reply_kinds_unchanged` |
| P6 | Reply still lands on legacy inbox (backward compat — agents without lane consumer still see replies) | `test_reply_legacy_fallback_works` |
| P7 | `_lane_write` failure for non-reply kinds remains silent-advisory (existing contract preserved) | `test_lane_write_still_advisory_for_non_replies` |

#### Files touched (estimated)

1. **`scripts/bifrost_runner_deepseek.py`** — `_process_one`: replace `bus.send(m.frm, reply_kind, out, meta=reply_meta)` with new `bus.send_reply(m.frm, out, meta=reply_meta)` (~5 line change). Add `reply_id` to `reply_meta`.
2. **`core/comm/bus.py`** — New method `send_reply(to, content, meta)`: lane-first xadd → verify → legacy-fallback xadd. ~30 lines. New method `is_duplicate_reply(reply_id)` for receiver-side dedup. ~15 lines.
3. **`core/comm/bifrost_api.py`** — `work_drain`: add receiver-side dedup check using `bus.is_duplicate_reply()` before returning any message with `_lane_src="legacy"` and kind="reply". ~10 lines.
4. **`tests/test_t066_reply_path.py`** — 7 pins, ~150 lines.

#### Non-goals (explicitly excluded)

- Changing the T039a P0 dual-write contract for non-reply kinds. That is a separate cutover (T039b).
- Adding a persistent dedup for ALL message kinds. Reply dedup only.
- Changing the `_lane_write` error handling in `_emit`. The existing `except: pass` stays for non-reply kinds.
- Retrofitting the lane write to be synchronous/blocking for ALL senders. Only the runner's reply path gets the lane-first treatment.

#### Design rationale

**Why lane-first, not lane-ensure?** Making `_lane_write` synchronous (non-advisory) for ALL kinds would change the T039a contract globally. The runner's reply is the narrowest surface that produces the bug — directed replies from a lane consumer to another lane consumer. Fixing it at the bite site is safer than changing the transport layer.

**Why receiver-side dedup instead of sender-side only?** Even with lane-first sending, the legacy fallback means the reply exists in TWO streams (work lane + legacy inbox). The straggler net intentionally reads both. Without receiver-side dedup, the dual existence IS the double-delivery. The sender can guarantee lane-first order but cannot guarantee the legacy copy won't be read by a different consumer path.

**Why `reply_id` instead of reusing `answers` meta?** The `answers` meta links the reply to the message it answers — it's semantic, not idempotent. Two replies to the SAME message (e.g., a nudge-ack followed by the real answer) would have the same `answers` value. A unique `reply_id` distinguishes them.

---

## APPENDIX: Evidence Correlation

### Daniel's event evidence
- `event:events:raw:1784082287759-0` — tonight's dual-verdict reply
- `event:events:raw:1784003725351-0` — last night's incident

### My trace
- My dual-verdict reply (T059 cross-check + T053 review) was one `_process_one` call → one `bus.send("claude", "reply", ...)` call → one legacy xadd → one `_lane_write` attempt
- The lane write FAILED (silently, per P0 contract)
- The reply landed on `bifrost:inbox:claude` (legacy) only
- Claude's lane consumer missed it on `bifrost:work:inbox:claude` (lane write failed)
- The straggler net caught it from the legacy shadow → first delivery
- Claude's legacy consumer or a second work_drain cycle caught it again → second delivery (2 min later, wake re-arm)
- 5 wake-loop cycles on Daniel's seat

### The `write_file` ToolBox path is NOT the double-delivery source
My agentic loop called `write_file` twice (two reports). These are ToolBox tool results — NOT bus messages. They return strings to my agent loop, which chains them. Only the FINAL reply (`bus.send`) reaches the bus. The two `write_file` calls did not produce two bus messages.
