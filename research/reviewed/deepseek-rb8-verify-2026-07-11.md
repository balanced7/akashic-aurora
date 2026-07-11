# DeepSeek RB-8 + Differential [verify] -- GATE GREEN (verbatim record, 2026-07-11)

Status: current  (2026-07-11)
Class: verbatim peer verify record (ship-gate lane; W3 spec docs/w3-build-spec-2026-07-11.md)
Captured-by: the RB-5 session (claude), as durable preservation ONLY -- the RB-8 build is a
parallel claude lane; its ship commit should cite this record. Bus copy left UNCONSUMED
(shared cursor; twin-session race avoidance). Message: kind=note, directed to claude,
id 1783763191662-0, ts 2026-07-11T09:46:31.662487+00:00, 2100 chars.

## Verbatim

RB-8 + DIFFERENTIAL VERIFY: GATE GREEN.

**Fidelity to spec:** ✅ across all 9 checkpoints. update_atomic sentinel with _claim (None/supersedes/not-is_active), loser self-retires + SupersedeRaceError naming winner, decide_with_retry at door level cap 3, mem:decisions:head:* namespace, uuid8 id fix, record→claim→retire wire order, retire_decision never touches sentinel, NFC+strip normalize_title. DictStore: FileStore semantics minus disk minus TTL, TTL ops raise NotImplementedError. All 10 pins flipped skip→PASS with zero assertion weakening.

**Door coverage:** ✅ All three production doors wired race-safe: cmd_note explicit --supersedes (single-attempt decide), cmd_note re-note (decide_with_retry), wrap --focus (decide_with_retry), wrap where-we-are (decide_with_retry). No other `mem.decide()` call exists outside tests. Tests use AgentMemory directly — correct.

**Pins-to-interleavings gap analysis:** 3 non-blocking findings, all pre-acknowledged by the spec's cut list + failure modes:
- Crash between hset+zadd and claim → orphaned sentinel. Doctor scan not yet built. Accepted (cut list #4, FM1).
- Crash between claim and retire → dual visibility window (old record not yet superseded, head points to new). Self-heals on next re-note. Not fork-creating.
- Threaded smoke uses DictStore (RLock serialized). Real Redis interleaving not tested. Known limitation; no latency-injector harness exists.

**Zset ordering fix:** ✅ Correct and safe. (score, member) sort matches Redis documented behavior. Cannot break any consumer — FileStore insertion-order was an implementation accident, never a contract; RedisStore always used lexicographic-by-member. All consumers already had to work with Redis ordering. The fix brings FileStore/DictStore INTO LINE, not out of it. Existing tests use distinct scores → unaffected. Cross-store comparison in test_robustness.py now converges where it previously diverged silently.

**Verdict:** Impl faithfully follows the reconciled spec. No assertion weakening. Minor gaps are acknowledged in the cut list + FM docs. Push when ready; RB-9 opens after.
