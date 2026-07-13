# claude half — T043 packet send-door hardening build plan (SEALED until deepseek's lands)

Status: current  (2026-07-13)
Class: build-plan cross-check (claude blind half; deepseek blind half fired separately)
Cites: docs/packet-spec-v1-2026-07.md (LAW) RIDING BUILD deliverable, 10 pins + 3-receipt drill
Slice: T043 (rides T040)

Blind half — written BEFORE reading deepseek's, fenced. Reconcile after his lands.

## A. MODULE LAYOUT
Per spec R6 (schemas live in packet_spec.py; code = source of truth):

- **NEW core/comm/packet_spec.py** — pure, no Redis/IO, trivially testable, shared by both doors:
  - Dials via env with defaults: `BUS_MAX_MESSAGE_BYTES`=65536, `PACKET_INTEGRITY_ENABLED`=True,
    `FRAG_REASSEMBLY_TTL`=300, `PACKET_INTEGRITY_TRACE`=False, `PACKET_SPEC_VERSION`=2.
  - `canonical_bytes(fields) -> bytes` — the exact hashable form (see C).
  - `compute_len_sha(fields) -> (int,str)`.
  - `stamp(env) -> env` — adds v/len/sha at the send door.
  - `verify_integrity(fields) -> (ok, reason)` — consume-door + sweep filter (see D).
  - `check_mtu(nbytes) -> (ok, reason, teaching_text)` — MTU gate, exact stderr text.
  - `fragment(env, max_bytes) -> [frag envs]` — split oversize (opt-in allow_frag) into {seq,of,whole_id}.
  - `Reassembler` — consumer-side buffer: `add(frag)->maybe whole`, `sweep_expired(now)->[timed-out]`.
- **core/comm/bus.py** — thin orchestration: `_emit` calls stamp + check_mtu (+ fragment when allow_frag);
  `_drain`/`_to_msg` call verify_integrity + Reassembler + drop-on-mismatch + integrity event.
- **scripts/deepseek_chat.py** — pin 8: check_mtu at the tool-arg dispatch bite site, refuse-loud.

## B. FRAG REASSEMBLY (the trickiest)
- Buffer lives in the **Bus instance** (per-consumer, in-memory): `self._reasm[whole_id] = {frags:{seq:env}, of, first_seen}`.
- **Advance the cursor PAST received frags and buffer them** — do NOT hold the cursor on a partial set.
  Each fragment is an independently valid stream entry (own len/sha); holding the cursor head-of-line-blocks
  ALL later mail and fights the RB-21 generation fencing. So: advance normally, accumulate, emit the whole
  Message to `out` only when the last seq completes the set (post-reassembly whole-len/sha verified).
- **Duplicate frag** (seq already have) = idempotent no-op.
- **Timeout**: each drain calls `Reassembler.sweep_expired(now)`; buffers older than FRAG_REASSEMBLY_TTL →
  LOUD `fragment_timeout` event NAMING the missing seq(s), discard partial. Cursor already advanced → no rewind.
- **Orphan** (seq>=of, or of mismatch) → LOUD orphan drop.
- **KNOWN v1 GAP (flag to reconcile)**: in-memory buffer → a consumer RESTART mid-reassembly loses the
  partial set silently (frags already past cursor, no buffer to time out). Defensible for v1 because
  work-lane frags are covered by the sender's L4 expectation redrive; fire-and-forget frags accept the gap.
  Alternative = Redis-backed reassembly hash (survives restart) at higher complexity. LEAN in-memory v1 +
  documented caveat; ask deepseek.

## C. CANONICAL len/sha
Stream fields are already strings: content/meta/parts are json.dumps'd at send; frm/to/kind/ts plain.
- **Hash the STRING fields exactly as they sit in the stream** (do NOT re-parse content/meta/parts). The
  consume door reads those exact bytes back from Redis, so hashing literals guarantees send==consume
  byte-for-byte; re-parse→re-serialize risks dict-order/float-repr drift.
- canonical_bytes = `json.dumps({frm,to,kind,content,ts,meta,parts}, sort_keys=True,
  separators=(",",":"), ensure_ascii=False).encode("utf-8")` over the 7 core fields ONLY (exclude
  v/len/sha/frag/lane/... — can't hash the hash; envelope-control fields are not content-integrity).
- len = len(canonical_bytes); sha = sha256(canonical_bytes).hexdigest().

## D. PIN 9 (RB-29 — dropped corrupt reply must not clear an expectation)
Root risk: `expectations.sweep()` scans replies via `_replies_since` RAW from Redis, bypassing the consume
door. A corrupt reply dropped at _drain still sits in the append-only stream and would be counted by sweep.
- **Fix (DRY, single source of truth)**: route `_replies_since` through `packet_spec.verify_integrity` and
  SKIP corrupt entries. One definition of "valid packet" honored by BOTH consume paths (_drain and sweep).
  A corrupt reply clears nothing, anywhere. Minimal, no dropped-id side-set, no race.

## E. PIN 8 tool-bridge
Wire `check_mtu` at the ToolBox dispatch in deepseek_chat.py (~:860, where parsed args are executed for
write_file/edit_file/knowledge_note). Oversize serialized args → return a REFUSED tool result (the exact
text the agent sees) with teaching text (fragment/resend), NEVER a clipped store. Confirm exact site by read.

## F. HOLES / P4 walk
- sha over 7 core fields catches any corruption of frm/to/kind/content/ts/meta/parts. Envelope-control
  fields (v/lane/family/pri/deadline_ts/seq/ecn/idempotency_key) are NOT content — their own validators
  guard them (bad format REFUSED at send/consume per the envelope table). A corrupt `frag.of` → reassembly
  waits → LOUD TTL timeout (degrades safe). Post-reassembly whole-len/sha is the real gate. Acceptable.
- **pin 10 wiring risk**: `_to_msg` must NOT whitelist-and-shed unknown stream fields — forward-compat floor
  requires unknown keys preserved (passthrough/stash). Verify _to_msg on read.
- Smallest-legal packet: bare chat gains only v+len+sha (frag/latch absent = no bytes). Cheap. Matches R5/P1.
- Candidate ADDED pin: a parts-bearing (media-by-ref) message round-trips integrity (parts is in canonical
  order but no pin exercises it). Minor; add if cheap.
