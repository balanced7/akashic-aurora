# P0 wake-detect design -- DeepSeek adversarial review (T017)

Recovered verbatim from bus msg 1783639013873-0 (2026-07-09, kind=reply).
NOTE: eaten AGAIN by an orphan watcher -- the morning session's stop hook armed a
fresh OLD-CODE watcher at session end, before the P0 fix existed. Third strike of
the Exhibit A class; recovered from the stream as before.

---

Good. Now I have complete ground truth. Let me compile the adversarial review.

---

# T017 / P0 Adversarial Design Review — DeepSeek (Red Team)

## Numbered Findings (severity-tagged)

### 🔴 F1 — CRITICAL: Redis stream ID `0` means "beginning," not "nothing"

**The failure:** Redis Stream IDs are in the format `<millisecondsTime>-<sequenceNumber>` (e.g. `1752086123456-0`). The cursor initializer `_read_cursor()` returns `"0"` for both inbox and bc when no cursor is stored. Redis interprets `"0"` as "the beginning of the stream." But stream IDs are lexicographically ordered strings — and `"0"` sorts BEFORE any timestamp-based ID. So initializing `_wake_since` from `Bus.cursor()` on a fresh agent returns `{"inbox": "0", "bc": "0"}` — the shared cursor has never been written.

Now: the design says (D3) "Local-cursor initialization: from the shared cursor (sees pending backlog → immediate wake on pre-queued wake-worthy mail, matching today's 'returns pending immediately' test)." This is correct for the FIRST call. But on the SECOND call, `_wake_since` is advanced past the returned messages. What if the shared cursor was ALSO `"0"` (never written — agent has never consumed)? The first `wake_block` with `since="0"` sees the full backlog, returns wake-worthy items, advances `_wake_since` past them. The shared cursor stays at `"0"`. So far, fine. But:

**The actual race:** Between the watcher's `_wake_since` initialization and the first `wait(since=...)`, a concurrent live session (e.g. `bifrost-sync --consume`) advances the shared cursor from `"0"` to `"1752086123456-0"`. The watcher then calls `wait(since={"inbox":"0", "bc":"0"})`. Redis returns ALL messages from the beginning — including messages the live session already consumed. The watcher sees them as "new" and wakes on them, even though the real consumer already handled them. This is a **false wake on already-consumed mail.**

It's not message-eating (the shared cursor is untouched), but it IS a noisy-wake bug: the watcher exits on mail the session has already seen. The design's "sees pending backlog" convenience becomes a liability under concurrency.

**Severity:** 🔴 Critical — breaks the "detect, don't consume" contract under the exact deployment (watcher + live session) that the fix targets.

**Mitigation:** Initialize `_wake_since` to `$` (stream tail) instead of the shared cursor when the shared cursor is `"0"` (never-written). This means the watcher starts from NOW, not from the beginning of time. The "returns pending immediately" behavior (Q3) is only correct when there's no concurrent live consumer — but when there IS a live consumer, `$` is the only safe starting point. The design can check: if `cursor() == {"inbox":"0","bc":"0"}`, use `$`; otherwise use the shared cursor (the agent has consumed before, so the cursor reflects the real frontier).

---

### 🔴 F2 — CRITICAL: Redis Stream `maxlen` trimming races a long-idle local cursor

**The failure:** `_emit()` calls `xadd(..., maxlen=self.maxlen, approximate=True)`. `DEFAULT_MAXLEN = 10_000`. The `MAXLEN` argument trims the stream to ~10,000 entries, dropping the oldest. If a watcher's local cursor (`_wake_since`) points to an entry that has been TRIMMED from the stream, `XREAD` from that ID returns a Redis error or behaves unpredictably (Redis returns `ERR` if the ID is before the stream's first entry, or in some versions silently rewinds to `0`). 

**Concrete scenario:** An agent is idle for many hours, the stream fills with 10,000 trace/broadcast messages, the oldest entries (including the one `_wake_since` points to) are trimmed. The watcher's next `XREAD` with `since=<trimmed_id>` — what happens? Redis documentation: "If the ID specified is less than the first ID in the stream, XREAD will return all the elements in the stream." So the watcher gets the ENTIRE stream as "new" — a massive false wake with 10,000 messages. Even worse: since `since` suppresses `advance`, the watcher gets this firehose on EVERY subsequent call (because `_wake_since` is only advanced past what's returned, but if the stream has been trimmed, subsequent calls still start from the trimmed ID and get the full stream again).

**Severity:** 🔴 Critical — silent correctness failure under normal operating conditions (busy stream + long-idle agent). The watcher either (a) gets the full stream as "new" on every iteration (infinite wake storm) or (b) Redis errors. Either way, the invariant is broken.

**Mitigation:** In `wait(since=...)`, before calling `XREAD`, check whether `since["inbox"]` / `since["bc"]` is still within the stream by querying `XLEN` or `XINFO STREAM`. If the since-ID is before the stream's first entry (trimmed), reset to the first available entry or `$`. This needs to happen inside `wait()` and must be documented as a required guard for `since` callers.

---

### 🟡 F3 — HIGH: `_wake_since` advancement uses stream-tag inference that doesn't exist in the `wait()` path

**The failure:** D2 says "advances `_wake_since` past ALL returned messages (stream told by `m.to == "*"` -> bc, else inbox)." But `Message.to` for a broadcast is `"*"` (set in `_emit`: `to=BROADCAST_TO`). Good — that works. But the design says `wait()` gains a `since` parameter and when `since` is given, `advance` is ignored and the shared cursor is never written. The `since` path will return messages via `_drain`, but `_drain` currently returns `List[Message]` without any per-message stream-tag in the `Message` object itself. The stream-tag is tracked in the local variable `out_streams` inside `_drain`, which is NOT part of the return value.

So when `wake_block` calls `bus.wait(since=self._wake_since)`, it gets back `List[Message]`. To advance `_wake_since`, it needs to know which stream each message came from. The only way to infer it from the returned `Message` is `m.to == "*"` → broadcast, else inbox. BUT: a direct message to the agent (`to="deepseek"`) arrives via the INBOX stream, and a broadcast message (`to="*"`) arrives via the BC stream. The `m.to` field is sufficient for this inference. However:

**Edge case:** What if `to` is the agent's own ID? `m.to == self.agent_id` → inbox. `m.to == "*"` → bc. What if `m.to` is `None` or missing? The current `_to_msg` defaults to `""`. Need a robust rule: if `m.to in ("*", BROADCAST_TO)` → bc, else inbox. The design mentions this rule but doesn't flag that a `to=""` (malformed) would be treated as inbox, which could slightly mis-advance `_wake_since` for the bc stream.

**Severity:** 🟡 High — not a showstopper, but the `_wake_since` advancement logic depends on a stream inference that the `Message` object doesn't natively carry. The inference IS correct for all real messages (the `m.to` field is reliable), but the design should make this explicit and add an assertion: if `m.to not in ("*", self.agent_id) and m.to != ""` — this is an anomaly, log it. **Also:** the design should add a `stream` field to the `Message` dataclass so this inference isn't needed at all — `_drain` already knows which stream each message came from (the `out_streams` tracking); it just doesn't put it on `Message`.

---

### 🟡 F4 — HIGH: The stop-hook / heartbeat / reap triple has a window where the session becomes unwakeable

**The failure:** D4 says "The Akashic SessionStart hook kills a live bifrost_wake for this agent." The stop hook (`claude_stop.py`) checks `wake_armed()` — which reads the heartbeat PID file and checks if that PID is alive — and BLOCKS idling if no watcher is armed.

**Scenario:** 
1. Session A ends, stop hook fires → armed. Good.
2. Session B starts (new tab). SessionStart hook fires. D4: kill the old watcher (PID from heartbeat file) AND remove the heartbeat file.
3. But Session B hasn't armed its OWN watcher yet — the harness re-invokes with a boot, the agent works for a turn, then idles. The stop hook fires. `wake_armed()` returns False (heartbeat file was removed in step 2). The stop hook blocks. The agent must arm a watcher. It does.
4. But between step 2 (kill old watcher) and step 4 (arm new watcher), there's a GAP where no watcher exists. If a message arrives in that gap, the session is unreachable.

This is a genuine window, but it's SHORT (a single turn of work). The stop hook catches it at the NEXT idle. The real question: **does the SessionStart hook run BEFORE or AFTER the first turn?** If it runs AFTER the model's first reply, there's no gap (the old watcher is still alive during the first thinking turn, and the new watcher is armed at the first idle stop hook). If it runs BEFORE the model is even invoked, there IS a gap during the first thinking turn.

**Severity:** 🟡 High — narrow window, but it's the exact moment mail is most likely (the new session just started, peers may be responding to the handoff). Mitigation: D4 should specify that kill happens AFTER the new session confirms its own watcher is armed, not before. Or: kill is deferred until the stop hook's first block (if the old PID is not the current session's watcher, kill it then).

---

### 🟡 F5 — HIGH: `reply` as wake-worthy — the loop risk is real but contained (Q1 analysis)

**The failure:** Q1 asks about echo/loop risk from `reply` becoming wake-worthy. Let me trace the full cycle:

1. DeepSeek runner sends `kind=reply` to claude (directed, `to="claude"`).
2. Claude's watcher sees `kind=reply` from someone who is NOT claude → exits (wake fires).
3. Claude's harness re-invokes. Claude boots, syncs inbox, consumes the `reply`.
4. Claude's turn processes the reply. Does Claude respond? If Claude sends another message to deepseek, deepseek's runner replies → another `reply` → another wake. This IS a potential echo, but it's gated by:
   - The reply is a DIRECT message (not broadcast), so only Claude's watcher sees it
   - Claude's harness re-invoke is a FULL TURN, not an auto-responder
   - Claude's turn can decide "I've seen this, no further action needed" — unlike a runner's auto-reply loop

**The actual risk:** What if Claude's boot + sync includes MULTIPLE reply messages in the inbox (from prior exchanges)? Each one could in theory trigger a separate wake. But the watcher exits on the FIRST wake-worthy message; subsequent messages wait for the next idle cycle. So the worst case is one extra wake per reply, not an infinite loop.

**The real subtlety:** `reply` is also what the runner sends for a BROADCAST response. If deepseek sends a broadcast reply (`to="*"`), Claude's watcher sees it (broadcast goes to everyone's BC stream). Claude wakes. But Claude wasn't the intended recipient — the broadcast was for the whole room. Is waking on someone else's broadcast reply desirable? The design says "a directed reply arriving while the agent idles SHOULD wake it." A BROADCAST reply is not directed. The watcher can't distinguish them without inspecting `m.to`.

**Verdict:** `reply` as wake-worthy is correct for DIRECTED replies. For BROADCAST replies, it's noise — waking Claude because deepseek broadcast a reply to everyone. Mitigation: only wake on `kind=reply` when `m.to == agent` (directed), not when `m.to == "*"` (broadcast). The watcher already has `agent` available.

**Severity:** 🟡 High — not a loop (one wake per reply, gated by full-turn processing), but broadcast replies will cause unnecessary wakes.

---

### 🟠 F6 — MEDIUM: Q2 steer-while-idle — skip is correct for P0, but the doc should say why explicitly

**The failure:** The design says "steer stays skip for now (its semantics are fold-into-CURRENT-task; when idle there is no current task)." This is correct reasoning. But the doc doesn't address what happens when a steer arrives during a LONG idle period: the steer sits unread on the stream. When the agent next boots, does `bifrost-sync` surface it? Yes — `peek_inbox` returns all unread messages, including the steer. But steers are DESIGNED to be folded into the CURRENT task. On boot, there IS a new task — so should the agent see queued steers at boot? 

The current behavior: `boot` shows unread bifrost messages via `peek_inbox` (advance=False). The steer will be visible. But boot doesn't SAY "this is a steer — it was meant for your PREVIOUS task, treat it as context, not a directive." The agent might over-weight it. This is a boot-presentation issue, not a wake issue — outside P0 scope per D5.

**Verdict:** Skip is correct for P0. The one improvement: the design should note that a `kind=steer` arriving while the watcher is armed should increment a counter visible in the watcher's exit message ("quiet, but 2 steers queued for next boot"), so the agent knows to check. This is a D5-scope addition.

**Severity:** 🟠 Medium — skip is the correct call, but the missed-steer signal is a genuine UX gap.

---

### 🟠 F7 — MEDIUM: Q4 heartbeat-file singleton — the race is real but bounded

**The failure:** Two watchers start simultaneously for the same agent. Both write their PID to the heartbeat file. Both read it back. The design says "each iteration re-reads the pid file; if it names another live pid, stand down quietly (newest watcher wins)." The race:

1. Watcher A writes PID 1000, reads back → sees 1000 → stays.
2. Watcher B writes PID 1001, reads back → sees 1001 → stays.
3. Both think they're the owner.

This happens if B writes BETWEEN A's write and A's read. The window is tiny (a few microseconds between `write` and `open+read`), but non-zero. However, on the NEXT iteration (after `inner_block_ms`, default 120 seconds), both re-read. B sees 1001 and stays. A re-reads, sees 1001 (B's PID), checks if 1001 is alive → yes, stands down. So the race resolves within one inner_block (120s max). Both watchers are alive for ≤120s, during which one of them might also exit on a wake-worthy message — and both exits are harmless (the harness only re-invokes once per background-task completion, and the second completion is a no-op if the session is already active).

**Verdict:** The race EXISTS but self-heals within one inner block. Not a correctness bug — just a brief duplicate-watcher window. The design should document this bound explicitly.

**Severity:** 🟠 Medium — self-healing within 120s, no data loss, bounded noise.

---

### 🟠 F8 — MEDIUM: Q5 two concurrent Claude sessions — D4 kill can kill the WRONG watcher

**The failure:** Two Claude sessions (tabs) for the SAME agent_id ("claude"). Session A has a watcher (PID 1000). Session B starts. SessionStart hook fires. It reads the heartbeat file → PID 1000. It kills PID 1000. But PID 1000 is Session A's watcher — and Session A is still LIVE, actively working. Killing its watcher makes Session A unwakeable. Session B then arms its own watcher. When Session A next idles, the stop hook sees no watcher (it was killed) and blocks.

**Is this a real deployment scenario?** The design asks: "two concurrent claude sessions — is that a real deployment here?" The answer depends on whether Daniel ever opens two Claude tabs. I don't know, but the stake is high enough that D4 should be defensive: before killing, check whether the watcher's PID was started by a DIFFERENT session context. The simplest guard: the heartbeat file should also store a session ID or start timestamp. If the watcher's session-start time is within the last N minutes AND the current session is clearly different, warn and don't kill — or prompt the human.

**Severity:** 🟠 Medium — depends on deployment pattern. If two concurrent Claude sessions never happen, this is harmless. If they do, this kills a live watcher. The fix is cheap (store session-id in heartbeat file).

---

### 🟠 F9 — MEDIUM: Missing test pin: `since` with a trimmed cursor (F2 scenario)

**The failure:** The test plan (T1-T6) doesn't cover the `maxlen` trimming scenario from F2. T1 tests `since` with a clean cursor. T2 tests the Exhibit A regression. But no test verifies that `wait(since=...)` behaves correctly when the since-ID points to an entry that has been trimmed from the stream. This would pass all T1-T6 while the F2 bug survives.

**Test to add (T7):** Write 10,001 messages to fill the stream past maxlen, set a since-ID to the first message (which is now trimmed), call `wait(since=...)`. Assert it doesn't error and doesn't return the full stream as "new."

**Severity:** 🟠 Medium — the missing test means the F2 bug would ship undetected.

---

### 🟡 F10 — HIGH: `cursor()` accessor — `_read_cursor` is private; a public accessor that reads from Redis is correct but the design doesn't address Redis-unavailable fallback

**The failure:** D1 says `Bus.cursor()` is a public read-only accessor. `_read_cursor()` currently returns `{"inbox": "0", "bc": "0"}` on Redis error (fail-open). This is correct for the shared cursor (the agent's real position). But for the watcher's `_wake_since` initialization, returning `"0"` on Redis failure means the watcher will scan from the BEGINNING — and if Redis comes back, it gets the full stream as "new" (F1 variant). The design should specify: if `cursor()` fails (Redis down), `_wake_since` should be initialized to `$` or the watcher should refuse to arm (better to be unreachable than to false-wake).

**Severity:** 🟡 High — Redis flaps are rare but this behavior on flap is exactly wrong (flood of false wakes).

---

## Answers to Q1–Q5

### Q1: reply as wake-worthy — right call?
**Yes, with a carve-out.** Directed replies (`to=agent`) should wake. Broadcast replies (`to="*"`) should NOT wake — they're room-level chatter, not "someone is talking to you specifically." The loop risk is bounded (one wake per reply, full-turn processing gates re-reply). No infinite loop. Add the `m.to == "*"` filter to the watcher's wake-worthy check.

### Q2: steer while idle — skip, wake, or queue-visible-at-next-boot?
**Skip (current), with a visibility improvement.** Fold-into-CURRENT-task semantics mean a steer during idle is a category error — there's no task to fold into. The steer sits on the stream, visible at next boot/sync. The improvement: the watcher's "quiet" exit should report queued steer count so the agent knows to look.

### Q3: local-cursor from shared cursor vs `$`?
**`$` when shared cursor is `"0"`, shared cursor otherwise.** See F1. Starting from `"0"` creates a false-wake window under concurrency. Starting from `$` always is safe but loses the "detect pre-queued wake-worthy mail immediately" behavior that today's test expects. The hybrid rule (F1 mitigation) preserves the intent while eliminating the race.

### Q4: heartbeat-file singleton race?
**Race exists, self-heals within one inner_block, bounded to ≤120s of duplicate watcher.** Acceptable for P0. Document the bound.

### Q5: kill-at-session-start killing a live session's watcher?
**Yes, if two concurrent Claude sessions for the same agent_id exist.** Mitigation: store session-id in heartbeat file; only kill if session-id differs AND the PID's command line confirms it's a watcher for a DIFFERENT session.

---

## Test Pins to Add

- **T7 (F2 coverage):** `wait(since=<trimmed_id>)` — fill stream past maxlen, verify `since` pointing to a trimmed entry doesn't error or return the full stream.
- **T8 (F1 coverage):** Concurrent `wait(since=...)` with a live `inbox(advance=True)` consumer — verify the watcher doesn't false-wake on already-consumed mail.
- **T9 (F5 coverage):** Broadcast `reply` (`to="*"`) does NOT wake the watcher; directed `reply` (`to=agent`) DOES.
- **T10 (F10 coverage):** `cursor()` returns `"0"` when Redis is down; `wake_block` handles this by using `$` or refusing to arm.
- **T11 (F3 coverage):** `_wake_since` advancement correctly handles mixed inbox+bc returns — after a batch with one inbox message and one broadcast message, both stream cursors in `_wake_since` are advanced to their respective last-returned IDs, not cross-contaminated.

---

# Seat-2: line-level DIFF review verdict (same day, post-build)

Delivered via bus msg after a deliver-now unstick reprompt (the runner's first reply
ended promise-shaped -- the T018 defect). Detected by the NEW detect-only watcher
(wake fired, nothing consumed) and read through the normal door: the P0 live drill's
final component, passed on this very message. Verbatim:

1. 🟠 MEDIUM — `_id_key("0") == _id_key("0-0")`: both sort to `(0,0)`. A `since` dict hand-crafted with `"0-0"` vs a local cursor at `"0"` fails the `>` fast-forward guard because they compare equal. Not reachable in production (virgin cursors route to `tail()`, and `tail()` never returns `"0-0"` for an empty stream), but the sort function is not injective for all legal stream IDs. Fix: `if sid == "0": return (-1, -1)` before the parse branch. File: `core/comm/bifrost_api.py`, `_id_key()`.

2. 🟠 MEDIUM — `wake_block` fast-forward write-back `shared[stream]` without `.get()` fallback. Guard condition `_id_key(shared.get(stream,"0")) > _id_key(local)` prevents the KeyError path (comparison is False when key is absent), but a future `cursor()` that returns `{"inbox":"..."}` without `"bc"` would crash on the write-back line if the comparison ever became True. Defensive: `shared.get(stream, self._wake_since.get(stream, "0"))`. File: `core/comm/bifrost_api.py`, `wake_block()` fast-forward block.

3. 🟠 MEDIUM — `_reap_stale_watcher` verifies command line contains `"bifrost_wake"` but not session ownership. A same-session double-fire of SessionStart (misconfigured matchers) kills its own watcher. Self-healing (stop hook re-arms at next idle), and documented as within the one-live-session-per-agent-id contract. File: `scripts/hooks/claude_sessionstart.py`, `_reap_stale_watcher()`.

All other paths — `_drain` since/since_out handoff, truncation branch under since-mode, shared-cursor default-path byte-identity, `tail()` concrete-ID seeding, fast-forward regression guard, broadcast-vs-directed reply wake filter, local-cursor per-stream advancement through filtered own-broadcasts, `since_out` empty-result handling, singleton stand-down exit code, heartbeat ownership cleanup — are correct. Zero critical or high-severity bugs. No holds.
