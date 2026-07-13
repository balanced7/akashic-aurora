# DeepSeek half -- T043 send-door hardening build plan (VERBATIM, blind fence 2026-07-13)

Status: current  (2026-07-13)
Class: build-plan cross-check (deepseek blind half; paired with claude-t043-build-plan-2026-07-13.md)
Cites: docs/packet-spec-v1-2026-07.md RIDING BUILD. Fired blind via ask_deepseek (model deepseek-v4-pro), no claude plan shared.

---

A. MODULE LAYOUT
- New `core/comm/packet_spec.py`:
  - Constants: `BUS_MAX_MESSAGE_BYTES = 65536`, `FRAG_REASSEMBLY_TTL = 300`, `PACKET_INTEGRITY_ENABLED = True` (reads from config, default True), `PACKET_INTEGRITY_TRACE = False` (configurable).
  - Function `compute_content_byte_len(content: str) -> int`: `len(content.encode('utf-8'))`.
  - Function `canonical_sha(frm, to, kind, content, ts, meta, parts) -> str`:
    ```python
    payload = {"frm": frm, "to": to, "kind": kind, "content": content,
               "ts": ts, "meta": meta, "parts": parts}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    ```
  - Function `build_v2_envelope(frm, to, kind, content, meta, parts, allow_frag=False) -> dict`:
    1. Content is JSON string of original content (already done by caller; for tool bridge we’ll pass json.dumps-ed). Actually `_emit` currently json.dumps; we'll move serialization here. So this function receives the raw content dict and serializes it with `json.dumps(content, default=str)` producing `content_str`. Same for meta/parts (but they are already strings). Better: accept already serialized strings; caller passes strings. We'll keep `_emit` responsible for serialization after MTU check? We'll design `build_v2_envelope` to take string versions of content/meta/parts.
    2. Compute `l = compute_content_byte_len(content_str)`.
    3. Build base dict: `{"frm": frm, "to": to, "kind": kind, "content": content_str, "ts": _now(), "meta": meta_str, "parts": parts_str}`.
    4. Add `"sha": canonical_sha(**base)`.
    5. Add `"len": str(l)`.
    6. Add `"v": "2"`.
    7. Check total size: `total_bytes = sum(len(k.encode()) + len(v.encode()) for k,v in env.items())`. If `total_bytes > BUS_MAX_MESSAGE_BYTES`:
       - If not `allow_frag`: raise `PacketMTURefused(f"Message size {total_bytes} > {BUS_MAX_MESSAGE_BYTES}")`; caller logs stderr teaching text.
       - Else fragment: compute overhead per fragment (envelope minus content). Split `content_str` into chunks so each chunk + overhead <= BUS_MAX_MESSAGE_BYTES. For each chunk i:
         frag_env = copy of base dict but with content=chunk, frag=json.dumps({"seq":i,"of":n,"whole_id":whole_id}) (whole_id is new random). recompute len/sha per chunk. Return list of fragment envelopes.
    8. Return single envelope dict if no fragment.
  - Function `validate_envelope(fields: dict) -> Tuple[bool, Optional[str]]`:
    - Strips fields; expects `"v"`, `"len"`, `"sha"`, etc.
    - Check `v`: parse int; if >2 log “downgrade unknown version” but proceed.
    - If `PACKET_INTEGRITY_ENABLED == False`: for messages where integrity is dial-optional (trace) we might skip; but we’ll always validate for required kinds. For simplicity, always validate; if disabled, just log mismatch and pass True.
    - Recompute `len_actual = len(fields["content"].encode('utf-8'))`; compare with `int(fields.get("len", -1))`; if mismatch return (False, "length mismatch").
    - Recompute `sha_actual = canonical_sha(fields["frm"], fields["to"], fields["kind"], fields["content"], fields["ts"], fields["meta"], fields["parts"])`; compare with `fields.get("sha", "")`; if mismatch return (False, "SHA mismatch").
    - Return (True, None).
- `core/comm/bus.py` modifications:
  - `_emit(self, stream, *, to, kind, content, parts=None, meta=None, allow_frag=False)`:
    1. Serialize content/meta/parts to strings: `content_str = json.dumps(content, default=str)`, `meta_str = json.dumps(meta or {}, default=str)`, `parts_str = json.dumps([p.to_dict() if isinstance(p, Part) else p for p in (parts or [])], default=str)`.
    2. Call `build_v2_envelope(frm=self.agent_id, to=to, kind=kind, content=content_str, meta=meta_str, parts=parts_str, allow_frag=allow_frag)`.
    3. If returns list of fragment envelopes: loop `xadd(stream, frag_env, ...)`; return id of first fragment.
    4. Else single envelope: `xadd`, return mid.
  - `_drain(self, ...)`:
    - After reading entries, process sequentially in `_drain_loop(entries)`.
    - Maintain `frag_assembler` instance (per consumer, stored as `self._frag_assembler`).
    - For each `(sid, fields)`:
      - `valid, err = packet_spec.validate_envelope(fields)`. If not valid: log integrity event; then mark `sid` as to-be-acked (corrupt). Continue.
      - If `"frag"` in fields:
        - parse frag dict `{"seq": seq, "of": of, "whole_id": wid}`.
        - `msg_or_none = frag_assembler.add_fragment(wid, seq, of, sid, fields)`
        - if `msg_or_none` is a complete message: yield it; mark all fragment `sid`s of that whole as acked (so cursor can advance past them). Else (fragment buffered but whole not complete): we stop processing further entries (first incomplete fragment blocks the batch). So we must **break** after adding, unless we already have a completed whole (in which case we continue only if no incomplete fragments remain). Simpler: after buffering, if whole not complete, break loop; else yield and continue. To keep deterministic, we implement: after add, if assembly is not complete, we set a flag `held = True`; we break from the for-loop. If complete, we yield message, record fragment IDs as ackable, and continue.
      - else (no frag): valid message, yield as is, mark `sid` ackable.
    - After loop, call `advance_to(last_ackable_id)` where `last_ackable_id` is the max ID among entries we marked ackable (including corrupt ones and completed fragments). This Lua script must ack those IDs via XACK and set last_delivered_id. We'll extend `rb21_advance.lua` to accept a list of IDs to ack before advancing.
    - For timed-out wholes: `frag_assembler` should track creation times. On each `add_fragment` or periodically, drop wholes that exceed TTL; emit event with missing seq numbers, mark all fragments of that whole as ackable (so they can be advanced past). During the batch processing, those fragments (from pending re-delivery) will be seen again; we can then detect whole timed out, skip buffering, mark them as ackable (corrupt-like). So timeout is handled inline.
- `core/comm/expectations.py` (`_replies_since` function):
  - Currently reads raw Redis stream entries. Modify to import `packet_spec.validate_envelope`.
  - For each reply entry, before using it to match expectations, call `valid, _ = validate_envelope(fields)`. If not valid, skip that entry entirely. This ensures a corrupt reply never clears an armed expectation.
- `scripts/deepseek_chat.py` (pin 8 bite site):
  - Around line 853-860 where tool call arguments are assembled and dispatched, add check:
    ```python
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if func_name in ("write_file", "edit_file", "knowledge_note"):
            payload_str = json.dumps({"function": func_name, "args": args}, default=str)
            if len(payload_str.encode('utf-8')) > packet_spec.BUS_MAX_MESSAGE_BYTES:
                logger.error(f"Tool {func_name} args size {len(payload_str)} > MTU {packet_spec.BUS_MAX_MESSAGE_BYTES}, REFUSED loudly")
                # emit error response to model
                continue
        # proceed with bus._emit or ToolBox.handle
    ```

B. FRAG REASSEMBLY
- State: `core/comm/packet_spec.FragAssembler` instance held per consumer in `bus.py` `_drain`.
  - `dict whole_id -> { "fragments": dict mapping seq -> (entry_id, fields)`, `"expected_of": int`, `"creation_ts": float`, `"max_entry_id": str` }.
- Interaction with generation-fenced cursor:
  - `_drain` processes entries sequentially. After processing a fragment that completes the whole, the whole is delivered; we add all fragment `entry_id`s of that whole to the `ackable_ids` set. The cursor advances past the highest such id at the end of the batch (via Lua that acks them and sets last_delivered_id).
  - If a fragment does not complete the whole, we buffer it, do **not** add its id to ackable, and **break** the processing loop (no further entries in this batch processed). The cursor stays before this fragment’s id; next `_drain` will reread it.
  - On startup, the buffer is empty; pending fragments from before restart will be redelivered and re-buffered.
  - **Timeout**: During `add_fragment`, if `now - creation_ts > FRAG_REASSEMBLY_TTL`, mark whole timed out. Event emitted with missing sequence numbers. All fragments for that whole (including the current one) are treated as corrupt: they are not saved; their entry_ids are added to `ackable_ids`. The whole is dropped. This clears the hold, allowing the cursor to eventually advance past them.
  - When a timed-out whole's fragments are re-delivered later (if any were before the hold but after ack), they will be processed again; `add_fragment` will see `whole_id` in `_timed_out` set, and immediately treat entry as ackable, not storing.
- **Cursor logic**: modified Lua `advance_to` takes a list of stream IDs to `XACK` for the consumer group, then sets `XGROUP SETID ... <last_delivered_id>` to the given `safe_id` (which should be max of ackable IDs). Generation fence remains: increment and check a generation key to prevent concurrent advance.

C. CANONICAL LEN/SHA
- `len`: bytes of UTF-8 encoding of the `content` string as stored in the envelope. `len(content.encode('utf-8'))`.
- `sha`: SHA-256 of a JSON object with keys `frm, to, kind, content, ts, meta, parts`, in that order, values are the raw string fields from the envelope. Serialization: `json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))`. No whitespace. Example for a chat message:
  ```json
  {"content":"{\"text\":\"hi\"}","frm":"agent1","kind":"chat","meta":"{}","parts":"[]","to":"agent2","ts":"2026-07-12T10:00:00Z"}
  ```
  NB: keys sorted alphabetically anyway; `frm` before `to`? But spec order is `frm,to,kind,content,ts,meta,parts`; using `sort_keys=True` will reorder keys to alphabetical: `content, frm, kind, meta, parts, to, ts`. That breaks specified order! The spec says "CANONICAL ORDER (frm,to,kind,content,ts,meta,parts)". So we must NOT sort keys; we must construct the JSON string manually preserving that exact key order. So we'll build a string using `json.dumps` with a custom approach: create an `OrderedDict` with those keys in order, then `json.dumps(od, separators=(',',':'))`. That will maintain insertion order. So:
  ```python
  from collections import OrderedDict
  od = OrderedDict([("frm", frm), ("to", to), ("kind", kind), ("content", content), ("ts", ts), ("meta", meta), ("parts", parts)])
  raw = json.dumps(od, separators=(',', ':'))
  ```
  That yields `'{"frm":"...","to":"...","kind":"...",...}'`. Perfect.

D. PIN 9 (RB-29) FIX
- In `core/comm/expectations.py`, function `_replies_since` (raw Redis XREVRANGE reader):
  - After reading each entry `(sid, fields)`, call `packet_spec.validate_envelope(fields)`.
  - If validation fails (corrupt), skip that entry entirely—do not include it in the reply list for expectation matching.
  - This ensures a DROPPED corrupt reply cannot clear an expectation, yet avoids double-reading because the raw scan remains, but corrupted entries are filtered out cheaply.

E. PIN 8 TOOL-BRIDGE
- **Exact wiring point**: Inside the tool-call dispatch loop in `deepseek_chat.py`, after extracting `func_name` and parsing `args` (around line ~853-855), but before any call to `ToolBox.handle` or `bus._emit`.
- Insert:
  ```python
  if func_name in ("write_file", "edit_file", "knowledge_note"):
      test_payload = json.dumps({"function": func_name, "args": args}, default=str)
      if len(test_payload.encode('utf-8')) > packet_spec.BUS_MAX_MESSAGE_BYTES:
          self._logger.error(f"T043 MTU refuse: {func_name} args {len(test_payload)}B exceeds {packet_spec.BUS_MAX_MESSAGE_BYTES}B – not sent")
          # emit loud refusal to model (return error tool response)
          tool_responses.append({"tool_call_id": tool_call.id, "role": "tool", "content": "Error: tool arguments too large"})
          continue
  ```
- The MTU check thus happens at the bite site (the tool bridge), before any silent clipping at the note door.

F. HOLES & MISSING PINS
- **Missing: trace spot-check (R5 amend E)**. The spec requires “every 1000th trace packet spot-checked” even when `PACKET_INTEGRITY_TRACE` is off. Our plan currently always computes len/sha for all packets, which satisfies spot-check implicitly (consumer can validate if desired). If we want to strictly save bytes on trace, we would need a counter and conditional inclusion; but since we always include them (cheap), this is safe. Still, the spec might expect a toggle; we can add an `add_integrity` flag parameter to `build_v2_envelope` that is forced on for required kinds and forced on every 1000th trace. Not required for passing the 10 acceptance pins, but is a spec compliance point.
- **Smallest-legal-packet ceremony**: a bare chat message stays cheap: v, len, sha only, no frag/latch. Our envelope adds exactly those fields (plus meta/parts which exist). Overhead ~ few dozen bytes. Acceptable.
- **Frag `seq` validation**: missing seq (e.g., duplicates, out-of-range) should be treated as corruption and drop whole. Add check in `add_fragment`: if seq already present or seq >= of, mark whole corrupt/drop. Not explicitly listed in 10 pins but is implied by pin 6 (missing fragment) and general integrity.
- **Cursor hold for fragments may cause head-of-line blocking**, but acceptable for initial implementation; TTL ensures dead wholes eventually clear.
- **Consumer group rebalance**: If multiple consumers in a group, fragment state must be per-consumer, which our in-memory `frag_assembler` satisfies. No cross-consumer coordination needed.
- **PACKET_INTEGRITY_ENABLED kill-switch**: When False, `validate_envelope` should still verify and log but allow delivery. Included.

All 10 pins covered. No silent loss points remain.

