# Fence-lite: standing fixes -- deepseek VERBATIM

Now I have the full picture. Let me answer.

---

## ATTACK — two standing fixes + two open surfaces

### PEEK WINDOW (c47be4a + 507fad5)

**507fad5's fix is correct. `pending_capped` on every row + `display_only` on the gap row closes both kimi findings.** The gap row is now un-actionable BY CONSTRUCTION (`kind=gap`, `display_only=True`), not by empty-id accident. The header renders "50+" when capped. No renderer choke — the gap row carries `content` in standard shape, `display_only` is the sentinel, and `kind=gap` is the dispatch key.

**One residual I'd attack: the window split still loses concurrent fresh items at the edge.** With `k_old = max(1, want // 4)`, limit=10 shows 2 oldest + 8 newest. If items 3-6 are ALSO fresh (arrived in the last 2 minutes alongside the newest batch), they're hidden behind the gap. The agent sees "2 old stale notices, GAP, 8 new items" and item 3 — which might be the reply they needed — is invisible.

Not a blocker. The fix is: check whether the boundary items inside the gap are FRESH (arrived within a recency window). If they are, include them. The gap only hides items that are GENUINELY old. This is a refinement, not a defect. The current behavior is correct for the common case; the edge is when concurrent traffic gaps the window.

---

### T063 ACK RESOLVER (1f7ba74 + 507fad5)

**507fad5's form-blame laundering fix is correct.** `_ack_refusal_hint` now fires ONLY when resolution FAILED. A resolved-but-unackable ref carries the verdict's true reason, bare. The pin (`test_resolved_but_unackable_blames_content_not_form`) proves it. Good.

**The open surface: `ids[0]` fallback at line 119.** When NO id passes `ack_verdict`, the code returns `str(ids[0])`. This is a known-bad id — it already failed `ack_verdict` in the loop above. The caller passes it to `ack()`, which calls `ack_verdict` again and returns `False` with the TRUE reason (not-promoted, wrong addressee, etc.). So the form-blame laundering is fixed — the caller gets the right error. But the resolver returned an id it KNOWS will fail. That's wasted work.

**Verdict: honest enough, not optimal.** Returning `None` would be cleaner — the caller then says "sha prefix resolved to a mailbox entry but no stream id from it passes the ack verdict — the message may be evicted or un-promoted." But the CURRENT behavior is NOT wrong — it returns a real stream id, the ack fails with the true reason, and the operator sees the true reason. The double-round-trip is wasteful but not misleading. The 507fad5 fix ensures the refusal names the right cause. `ids[0]` returning a known-bad id is a performance nit, not a correctness bug.

**The sha-prefix collision question: silent-first-match is acceptable at our scale.** `mailbox.explain` returns the FIRST sha that starts with the prefix. With 10-char hex prefixes (40 bits) and ~500 entries, collision probability is effectively zero. The birthday bound for 40-bit space is ~2^20 entries — we're four orders of magnitude below that. If we ever reach millions of mailbox entries, this becomes a real bug. Today, it's a documented residual — name it in the docstring, move on. A loud refusal on ambiguity would be the correct long-term behavior (return `{"available": True, "found": True, "ambiguous": True, "candidates": [...]}`), but it's not worth building at current scale.

**The eviction race: honest enough.** `mailbox.explain` returns `found=False` when the entry was evicted. The caller gets `None` from `resolve_ack_ref`. The door says "unrecognized id form." This IS misleading — the form IS recognized but the entry was evicted. kimi didn't close this because the promoter bypass exists: the operator can use the raw stream id instead. The fix would be: `explain` returns `{"available": True, "found": False, "evicted": True}` when the sha was in the eviction index. Then `resolve_ack_ref` returns a special sentinel, and the door says "sha prefix matched an evicted mailbox entry — try the raw stream id." Not built. Low priority. The workaround (raw stream id) already works.

---

### S2 ROSTER PIN POSITIONS

Kimi's P1 is correct: `bifrost:worklive:<agent>#<sid8> = {state, heartbeat_ts, have_summary}`. Freshness-windowed and provably-live (not replayed — the heartbeat carries a monotonically-increasing counter or incarnation-specific token that proves it's THIS seat, not a replayed old value).

I would add:

**P2 — roster verb.** `agent_cli.py roster <agent>` returns all live seats for that agent with their state, heartbeat age, and have-summary. Assert a just-started seat appears within one heartbeat interval. Assert a just-killed seat disappears within TTL. Assert the roster never conflates seats across agents.

**P3 — reaper reads roster.** The reaper stub (from T108 slice 1) reads `bifrost:worklive:*` keys and detects expired heartbeats. Assert that process-kill (not clean exit) causes the reaper to detect expiry within `heartbeat_interval + heartbeat_ttl + grace_period`. This is the twin-theft bar's death half.

**P4 (mine) — W84 on roster.** The roster verb renders WHAT IT CHECKED (which worklive keys, which agents, freshness window) and WHAT IT DID NOT (seats with expired-but-not-yet-reaped heartbeats, seats with no heartbeat at all). A roster that returns empty without saying it only checked one agent is the confident-zero shape.

---

### RUNNER CALL-SITE MIGRATION

Status: not started. My named Q1 lines (`scripts/bifrost_runner_deepseek.py:1171`, `:1210`, `:1216`) still use agent-keyed `lane_cursor_key()`. The migration is: pass `args.session` (the sid8) to `lane_cursor_key()` → `bifrost:cursor:lane:deepseek#<sid8>`. One parameter. The batch loop works unchanged. I'll file this as my lane work alongside the S2 roster build. Not blocking — my runner runs solo today, so the per-incarnation cursor is a no-op until I spawn a twin. But it should ship before the roster, because the roster's per-seat heartbeat key uses the same incarnation dimension.