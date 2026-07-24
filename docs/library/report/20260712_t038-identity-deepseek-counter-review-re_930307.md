---
akashic_id: art_20260712_t038-identity-deepseek-counter-review-re_930307
akashic_sha: eb112c6ab711
status: draft
type: report
date: 2026-07-12
title: "T038 identity — DeepSeek counter-review (RESOLUTION section, 2026-07-12)"
gist: "# T038 identity — DeepSeek counter-review (RESOLUTION section, 2026-07-12) **Status:** adversarial counter-review per Daniel steer **Subject"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, identity]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_t038-identity-primitive-closure-amend-ag_c5b02c
    rel: cites
created: "2026-07-12T12:54:55"
updated: "2026-07-23T21:42:16"
---
<!-- GENERATED PROJECTION of art_20260712_t038-identity-deepseek-counter-review-re_930307 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T038 identity — DeepSeek counter-review (RESOLUTION section, 2026-07-12)

# T038 identity — DeepSeek counter-review (RESOLUTION section, 2026-07-12)

**Status:** adversarial counter-review per Daniel steer
**Subject:** research/reviewed/t038-identity-closure-2026-07-12.md — RESOLUTION section
**Claim under review:** T038 keys (c)/(d)/(f) on `session_holder_token()` — the session id the seat already carries as its `token` field. NO new primitive, NO record-shape change.
**Method:** source-grounded adversarial verify — every claim checked against live code (runner_lock.py, expectations.py, intent.py read this session), every residual risk attacked for silent-failure paths.

---

## 1. THE CLAIM — restated for attack

The RESOLUTION asserts: `session_holder_token()` (runner_lock.py:172-178, = `"session:{CLAUDE_CODE_SESSION_ID}"`) satisfies BOTH required properties:

| Property | Mechanism | Confidence |
|----------|-----------|------------|
| **Turn-stable** | Env var inherited by all turn-processes. Same value at arm-time and sweep-time | ~90% (documented) |
| **Twin-distinct** | Different sessions have different UUIDs | ~95% (by design, not formal guarantee) |

This value is ALREADY the seat's `token` field (written at runner_lock.py:90/132/146 via `claim_consumer` → `acquire(agent, holder_token)`). No new field, no new write-site, no new primitive.

**Verdict on the claim: HOLDS under source verification, with two residual risks that are both fail-safe.**

---

## 2. SOURCE VERIFICATION — six assertions checked

### A1. session_holder_token() is turn-stable

**Claim:** Env var inherited by all turn-processes → same value at arm, sweep, and act boundaries.

**Source:** `session_holder_token()` at runner_lock.py:172-178 reads `os.getenv("CLAUDE_CODE_SESSION_ID")`. The env is inherited by subprocesses. A session's turn-processes (CLI invocation, boot, bifrost-sync, stop-hook) all inherit from the session harness.

**Attack:** Is there any turn-context where the env is NOT inherited? Two candidates:
- **The runner subprocess:** launched by the launcher (core/comm/launcher.py). Does the launcher scrub or modify `CLAUDE_CODE_SESSION_ID`? I do not have launcher.py read this session. However, the RUNNER is not a T038 actor — it answers messages, it doesn't negotiate tokens. T038's actors are the door paths (agent_cli.py / MCP / bifrost_pull). These DO inherit env.
- **The /compact or /clear boundary:** Does the session ID persist across `/clear`? The closure rates this at ~70%. If the ID changes, `verify_still_held` false-negatives. This is the softest spot in the resolution. See §4 for attack.

**Verdict: HOLDS for T038's actor set.** The arm/sweep/act contexts are all env-inheriting processes. The runner is not a T038 work-negotiator.

### A2. session_holder_token() is twin-distinct

**Claim:** Different sessions have different CLAUDE_CODE_SESSION_ID UUIDs. Two real concurrent sessions (e.g., the Opus twin and the Fable seat) carry different IDs.

**Source:** Live empirical evidence from the concurrency trial: the Opus twin (e59d8882) and the Fable seat (46bf68d6) carry DIFFERENT session IDs. They share the AGENT id (`claude`) but have distinct session tokens. The session_holder_token for one is `session:e59d8882-...` and for the other is `session:46bf68d6-...`. They are distinct.

**Attack:** Could two sessions share a CLAUDE_CODE_SESSION_ID? Only in the sidecar case (T035 re-entrancy) — a subprocess launched under another session's env. The closure correctly scopes this out: the sidecar is NOT a T038 actor (it doesn't negotiate work). The sidecar is a T036 seat-integrity concern.

**Verdict: HOLDS for T038's actor set.** The env-sharing case (sidecar) is not a work-negotiator.

### A3. The seat's token field IS session_holder_token()

**Claim:** `holder(agent).get("token")` already returns `session_holder_token()`. No new field needed.

**Source:** `claim_consumer(agent, holder_token)` at runner_lock.py:181 calls `acquire(agent, holder_token, ...)`. The holder_token comes from the caller. On the consumer path (bifrost_pull.py:112), it IS `session_holder_token()` (bifrost_pull.py:77). The acquire writes at :90-91: `c.set(_key(agent), json.dumps({"token": token, "pid": ..., "ts": ..., "gen": gen}))`. So the seat's `token` field IS whatever holder_token was passed.

**Attack:** Is there any path where claim_consumer is called with a DIFFERENT token? The runner path (bifrost_runner_deepseek.py:663) uses `instance_token(args.agent)`, NOT session_holder_token. But the runner acquires via `acquire(agent, lock_token)` — NOT via `claim_consumer`. The runner and the session consumer share the SAME lock key (`_key(agent)`), so whichever acquires first holds it. If a runner holds it, `holder().get("token")` returns the runner's instance_token, not a session token. But T038's `verify_still_held` runs in the SESSION context (the session that negotiated the token), not the runner context. The runner doesn't call `verify_still_held` — it's running, not negotiating. This is a non-issue.

**Verdict: HOLDS.** The consumer-path seat carries session_holder_token() as its `token`. T038 reads from the same seat.

### A4. verify_still_held comparison is correct

**Claim:** `caller_session_token == holder(agent).get("token")` — no new field, no cross-turn mismatch.

**Source:** `holder(agent)` at runner_lock.py:229-238 returns the raw dict verbatim (`json.loads(raw)`), which includes `token`. `session_holder_token()` returns the same value at every turn for the same session. So arm-turn's session_holder_token() == sweep-turn's session_holder_token() == act-turn's session_holder_token().

**Attack:** What if another session claimed the seat between arm and act? Then `holder().get("token")` would be the NEW session's token, and the comparison would correctly return False — the original session no longer holds it. This is INTENDED behavior.

**Verdict: HOLDS.**

### A5. Expectations ownership split is sound

**Claim:** Ownership hash key = `session_holder_token()`. Inbox read stays `Bus(agent)`. Exact-linkage clear still works across sessions.

**Source:** expectations.py:43-44: `_key(sender) = EXPECT_PREFIX + str(sender)`. Currently `sender` = agent. Change: `sender` → `session_holder_token()` for the ownership hash. `_replies_since` at :90-98 still uses `Bus(agent)` — the shared inbox.

**Attack 1: Can session B's sweep accidentally clear session A's expectations?** No. The exact-linkage pass (:128-133) checks `a in recs` where `recs` are from the sweeping session's OWN hash (keyed on its session token). A's offer IDs aren't in B's hash. The FIFO fallback (:134-146) is scoped to non-work-token records (via `wt: true` marker). So B's sweep cannot touch A's offers.

**Attack 2: Can session B's sweep CURSOR-ADVANCE steal A's clearances?** No. `_replies_since` uses `since=` (caller-owned local cursor, bus.py inbound path), not the shared cursor. Each sweep has an independent stream read.

**Verdict: HOLDS.**

### A6. Intent conflicts re-key is sound

**Claim:** `conflicts()` at intent.py:83-88 changes from `i.get("agent") != agent` to `i.get("session_token") != my_session_token`. Two real sessions go RED; same-session re-declare stays green.

**Source:** intent.py:83-88: `[i for i in active(...) if slug(i.get("intent","")) == tag and i.get("agent") != agent]`. The change is: add `session_token` to the intent record (declare() at :105-106) and filter on it. Same-session re-declare (any turn) has the same session token → green.

**Attack:** Could two sessions with the same agent id declare non-conflicting intents that are WRONGLY flagged as conflicts? No — the conflict check is on the INTENT TAG, not the agent. Two sessions with different intents but overlapping scope files are flagged AMBER by `_scope_conflicts` (intent.py:210-222), which would now group by session_token instead of agent. This is correct — two sessions touching the same file SHOULD be aware of each other.

**Verdict: HOLDS.**

---

## 3. THE NO-RELOCATION ARGUMENT — verified

The resolution claims NO new write-site and NO new field. Verified:

| Claim | Source check |
|-------|-------------|
| `token` already written at 3 seat sites | :90-91 (acquire nx), :132-133 (heartbeat vanished), :146-147 (heartbeat own-token). Three `c.set(_key(agent), ...)`. Confirmed. |
| No fourth writer | release() :161 DELETE, clear_if_pid() :220 DELETE. No other `c.set(_key(agent), ...)` in runner_lock.py. Confirmed. |
| T036 edit-5 prevents twin restamp | :137 token check + edit-5 pid-guard BEFORE :146 write. Non-holding twin stands down before the write. The guard set is complete. |
| No new INCR | `GEN_PREFIX+agent` at :89 is the only `c.incr` in the tree. Confirmed. |

**Verdict: NO RELOCATION. The fix adds ZERO new write-sites and ZERO new fields.** The identity T038 needs already exists at the correct sites. This is the strongest argument for the resolution — it's not just correct, it's minimal.

---

## 4. RESIDUAL RISKS — adversarial attack

### Risk 1: Concurrent-distinctness ~95% (not formal guarantee)

**The risk:** Two distinct sessions COULD, in theory, receive the same CLAUDE_CODE_SESSION_ID UUID. The probability is astronomically low (UUID4 collision is ~2^-122), but the closure rates it at 95% because there's no formal documented guarantee from the harness.

**Attack:** If two sessions share a session ID, their session_holder_tokens are identical. They CANNOT be distinguished by T038. Both would pass `verify_still_held`. Both would see each other's intents as re-entrant-self rather than RED.

**Fail-safe analysis:** Even with identical session tokens, the consumer seat is SINGLE-HOLDER (acquire nx at :90). Only ONE session's claim_consumer wins. The loser gets the RB-21 teaching shape ("seat held by session X"). So the loser cannot consume mail, cannot negotiate tokens (can't verify_still_held — it doesn't hold the seat), and CANNOT co-work. The collision degrades to: the loser is locked out of ALL bus consumption, not just T038. This is worse than "fail-safe for T038" — it's a broader denial, but it IS safe (no co-consumption, no silent conflict). And it requires a UUID collision, which has never been observed in practice.

**Verdict: FAIL-SAFE. The seat's single-holder semantics are the backstop.** If session IDs collide, T038's identity check degrades, but the seat prevents co-consumption.

### Risk 2: /clear-/compact session-id stability ~70%

**The risk:** If the session ID changes across `/clear` or `/compact`, `session_holder_token()` returns a DIFFERENT value for the SAME logical session. The owner's `verify_still_held` would false-negative — "I don't hold my own token" — and be forced to re-negotiate.

**Attack:** How bad is forced re-negotiation?

1. The owner loses its token mid-work.
2. It re-enters negotiation. It may re-win the same scope (no peer contested it) or lose to a peer.
3. If it LOSES: the work it already did is in its git branch. The peer picks up the scope. The peer sees the partial work. This is a coordination event — not data loss.
4. If it RE-WINS: it continues where it left off. The interruption cost is one negotiation round (~seconds).
5. C2 advisory locks on the scope files prevent concurrent edits during the window. The commit gate catches conflicts.

**Verdict: FAIL-SAFE. Work is never lost, only re-coordinated.** The cost is a spurious negotiation round. The window is narrow (/compact events are rare, session-ID changes across them are undocumented, and the re-negotiation is bounded). This is an acceptable residual risk.

### Risk 3: Sidecar co-tenant and verify_still_held

**The risk:** A sidecar process (T035 re-entrancy) shares the session token. It could call `verify_still_held` and PASS — because it has the same `session_holder_token()` as the real session.

**Attack:** Would the sidecar ever call `verify_still_held`? T038's work-token negotiation is an AGENT-LEVEL protocol. The sidecar doesn't send offers, doesn't declare intents, doesn't negotiate. It handles tool calls. The `verify_still_held` is called at the ACT BOUNDARY — before the token holder acts on its scope. If the sidecar isn't acting on T038 scopes, it never reaches this boundary.

**What if a sidecar DOES try to negotiate?** The sidecar's claim_consumer would hit the re-entrant branch (same token → True, runner_lock.py:98-104). It would share the consumer seat. If it then tries to declare intent or send offers, it would use the same session token → same identity. The real session would see these offers as re-entrant self (not conflicts). This is a THEORETICAL hole: a sidecar could impersonate its parent session in T038 negotiation.

**But:** T036 edit-5 pid-guard already prevents the sidecar from restamping the seat during heartbeat. It does NOT prevent the sidecar from acquiring re-entrantly. So the sidecar CAN hold the consumer seat alongside the real session. Whether this matters for T038 depends on whether the sidecar actually participates in negotiation. Currently: no. The MCP sidecar handles tool calls, not coordination protocols.

**Verdict: THEORETICAL RISK, NOT PRACTICAL.** The sidecar doesn't negotiate. If a future sidecar DOES participate in T038, the token-sharing becomes a real hole — but that's a T035/T036 fix, not a T038 identity issue. The identity primitive is correct; the re-entrancy check is what needs fixing for that case.

---

## 5. COUNTER-REVIEW VERDICT

**The RESOLUTION holds under adversarial source-verify.** The identity primitive (`session_holder_token()`) satisfies both required properties for T038's actor set, is already present on the durable record, and introduces zero new write-sites.

### Verdict table

| Assertion | Verdict |
|-----------|---------|
| session_holder_token() is turn-stable for T038 actors | **HOLDS** |
| session_holder_token() is twin-distinct for T038 actors | **HOLDS** (sidecar scoped out correctly) |
| Seat's `token` field IS the session_holder_token | **HOLDS** (source-verified) |
| verify_still_held needs no new field | **HOLDS** |
| Expectations ownership split is sound | **HOLDS** (exact-linkage survives) |
| Intent conflicts re-key is sound | **HOLDS** |
| No relocation (zero new write-sites) | **HOLDS** (confirmed: 3 seat sites, no others) |
| Risk 1 (UUID collision) | **FAIL-SAFE** (seat single-holder backstop) |
| Risk 2 (/compact ID change) | **FAIL-SAFE** (spurious re-negotiation, work preserved) |
| Risk 3 (sidecar impersonation) | **THEORETICAL** (sidecar doesn't negotiate; T035/T036 fix if it ever does) |

### One amendment: confidence ratings

The closure rates Risk 2 at ~70% ("/compact stability undocumented"). I believe this understates the actual reliability. `/compact` and `/clear` are session-management operations, not routine events. If the session ID changed across them, it would break session transcript storage, `--resume`, and the stop-hook payload's session_id. These are MORE load-bearing than T038. The harness has strong incentives to keep the session ID stable. I'd rate it closer to ~90% — the undocumented nature is a documentation gap, not a mechanical instability.

### What I would ADD (not required for the fence, but sharpens the fix)

**A. Add `assert` parity check at claim time.** In `claim_consumer`, assert that `token.startswith("session:")` — a non-session token on the consumer path is a bug. This catches the runner's `instance_token` accidentally landing on the consumer seat.

**B. Document the identity split explicitly in runner_lock.py's module docstring.** "Two identities: seat-holder-liveness = pid (T036, LIVE-distinctness); work-ownership = session token (T038, TURN-STABLE distinctness). Do not conflate them." This prevents the v4 recurrence.

**C. Verify the harness guarantee empirically.** Before building T038, run a probe: arm a test expectation via CLI, trigger a `/compact` (if possible), sweep — does the session ID survive? If yes, bump Risk 2 confidence from ~70% to ~95%. If no, fall back to the mint-and-persist candidate (a durable session-scoped UUID written on first claim, re-read not re-minted).

---

*End of counter-review.*
