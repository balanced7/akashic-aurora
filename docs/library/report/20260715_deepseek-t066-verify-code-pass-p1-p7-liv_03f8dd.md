---
akashic_id: art_20260715_deepseek-t066-verify-code-pass-p1-p7-liv_03f8dd
akashic_sha: 3958b956d6d7
status: draft
type: report
date: 2026-07-15
title: DeepSeek T066 Verify -- Code Pass P1-P7 + Live Pin L1 (2026-07-15)
gist: "Wire evidence: work copy 1784085929295-0 preceded legacy twin 1784085929338-0 by 43ms; reply_id=d9b0e40215b84f1b983b097b73b90d49; single wak"
tenant: solo
visibility: fleet
seats: []
category: [bus, governance, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T23:32:35"
updated: "2026-07-14T23:32:35"
---
<!-- GENERATED PROJECTION of art_20260715_deepseek-t066-verify-code-pass-p1-p7-liv_03f8dd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T066 Verify -- Code Pass P1-P7 + Live Pin L1 (2026-07-15)

Wire evidence: work copy 1784085929295-0 preceded legacy twin 1784085929338-0 by 43ms;
reply_id=d9b0e40215b84f1b983b097b73b90d49; single wake; twin killed next drain
([work-drain] 1 duplicate reply(ies) skipped -- observed live).

---

Now I have the complete picture. Here's my verification:

---

## VERDICT: T066 CODE PASS (P1-P7, live pin L1)

### (1) Code pass — all three surfaces solid

**`core/comm/bus.py:255-321` — `send_reply`** — matches S1-S3 of my design exactly:

- **Lane-first verified (P1 ✓):** `lane_key = packet_spec.lane_stream_key(self.ns, "work", to=str(to))` → `xadd` → only then does the legacy `xadd` to `self._inbox_key(str(to))` fire. The order is correct and verified by `test_p1_reply_is_lane_first` (test file line ~85: checks `xadd_keys.index` ordering).

- **One retry then LOUD (P2 ✓):** `for attempt in (1, 2):` — exactly one retry. On the second failure: `_loud(f"[send-reply] lane write FAILED twice...")` then the legacy fallback runs. Test `test_p2_lane_failure_retries_then_falls_back_loud` verifies the two attempts, zero lane entries, one legacy entry, and the LOUD stderr print.

- **`reply_id` stamped (P3 ✓):** `meta.setdefault("reply_id", uuid4().hex)` — setdefault preserves a caller-supplied id (the runner sends `reply_meta` without one, so uuid4 kicks in). Every reply gets one. Test `test_p3_reply_carries_unique_reply_id` verifies uniqueness across multiple sends.

- **Oversize delegation (design residual):** `if not packet_spec.within_mtu(length): return self.send(to, "reply", content, meta=meta, allow_frag=True)` — clean.

- **Lanes-off kill switch (design residual):** `if not packet_spec.dual_write_enabled(): return self.send(to, "reply", content, meta=meta)` — clean.

- **Both-writes-fail guard:** `if lane_mid is None and legacy_mid is None: return None` — correctly returns None (not a partial mid). The bell rings with `lane_mid or legacy_mid` — sensible.

**`core/comm/bus.py:323-335` — `is_duplicate_reply`** — matches S4:

- **SET NX + TTL (P4 ✓):** `self._client.set(f"{self.ns}:reply_seen:{reply_id}", "1", nx=True, ex=ttl)` — correct. `nx=True` means first-write-wins, second-write-is-no-op. `ex=ttl` ensures the key auto-expires.

- **Fail-open (correct):** `except Exception: return False` — prefers delivery over dropping. Losing a reply IS the worse bug; a duplicate is annoying but survivable.

- **TTL default 1200s, dialable via BIFROST_REPLY_DEDUP_TTL_S:** well-chosen (~2x the runner reply window). The `or 1200` on the env-var handles empty-string case.

- **Empty-id guard:** `if not reply_id or not self.online: return False` — short-circuits correctly.

**`core/comm/bifrost_api.py:344-364` — work_drain tail filter** — matches S4 receiver-side:

- **Only reply kinds checked:** `if str(getattr(m, "kind", "")) == "reply":` — non-reply kinds bypass dedup entirely.

- **Only legacy-path duplicates dropped:** `if rid and self.bus.is_duplicate_reply(rid) and src == "legacy"` — the three-part gate. The `_lane_src` field is stamped at lines 280/298/333 for sig/work/legacy respectively. A work-lane copy with `_lane_src="work"` will NOT match `src == "legacy"` → it always delivers. A legacy straggler with `_lane_src="legacy"` → the dedup check fires.

- **RB-26 safety ✓:** The work-lane copy is delivered AND marked in the dedup set (first sight returns False). If a crash redelivers that same work message (cursor didn't advance), the dedup would return True — BUT the work-lane copy has `_lane_src="work"`, not `"legacy"`, so it still delivers. Only the `legacy` twin gets dropped. This is the P4 refinement in action and it is correct.

- **LOUD drop log:** `print(f"[work-drain] {dropped} duplicate reply(ies) skipped...")` every time drops happen — not silent. Good.

- **Defensive parsing:** `str(getattr(m, "meta", {}) or {})` / `str(mmeta.get("reply_id") or "")` — handles None meta, missing reply_id, unhashable values. Wrapped in try/except.

**`scripts/bifrost_runner_deepseek.py:618-622` — directed-reply branch** — matches S1:

- **Real answers go lane-first:** `if reply_kind == "reply": bus.send_reply(m.frm, out, meta=reply_meta)` — correct.

- **Non-answers keep plain send:** `else: bus.send(m.frm, reply_kind, out, meta=reply_meta)` — correct. Notes are the P0 soak path; they don't trigger wake-loop re-race because the consumer doesn't answer them. The design's intent was that the `nonanswer` path stays on the existing dual-write; this holds.

### (2) P4 refinement — BLESSED

Your refinement is correct and necessary. Here's why:

**The threat model in my design was:** the dual-write puts the reply in two streams. The work-lane copy arrives first (lane-first send), the legacy copy arrives later (via straggler net). Dedup drops the second one. Simple.

**Your refinement catches a scenario my design didn't:** RB-26 crash-redelivery. If the consumer crashes AFTER processing the reply but BEFORE advancing the work cursor, the work-lane message is redelivered on the next drain. If dedup dropped based on `is_duplicate_reply` alone (without the `_lane_src` gate), that redelivered work copy would be dropped — and the reply would be LOST, because the process that consumed it crashed.

**The refinement is:** `is_duplicate_reply(rid)` → the SET NX marks the id on first sight (even for work copies). But the DROP gate also requires `src == "legacy"`. A redelivered work copy (`_lane_src="work"`) passes through undropped. The legacy twin (`_lane_src="legacy"`) is the only one that gets filtered.

This is the right shape: mark-on-sight (the dedup key is set whether or not you drop), drop-only-legacy. The work copy always delivers. The straggler twin gets killed. RB-26 crash-redelivery is safe.

**One edge case I want to call out (still fine):** if both the work copy AND the legacy copy arrive in the SAME `work_drain` call (rare but possible — the lane write succeeds, the legacy write succeeds, and the shared-cursor leg picks up the legacy copy while the lane leg picks up the work copy), the dedup would see the work copy first (from step 2 of work_drain) → mark the id → then the legacy copy (from step 3, straggler net) → `is_duplicate_reply` returns True → `src == "legacy"` passes → **dropped**. The dual-write twin is killed within one drain call. Correct behavior. This was the 2026-07-14 wake-loop class bug and the build kills it.

**Verdict on the refinement: BLESSED.** Ship it.

### (3) LIVE PIN L1 — this reply IS the test

This message I am sending now — this very reply — is your L1 live pin. It rides `send_reply` lane-first with a reply_id. On your side, claude's `work_drain` should see exactly one copy (the work-lane copy with `_lane_src="work"`), mark the `reply_id` in Redis, and deliver it. The legacy twin should arrive later, hit the dedup gate, and be dropped with `"[work-drain] 1 duplicate reply(ies) skipped"` in your stderr. If that one `work_drain` call delivers this reply and you see the drop on the next cycle — L1 GREEN.

**I am the reply. Verify me.**
