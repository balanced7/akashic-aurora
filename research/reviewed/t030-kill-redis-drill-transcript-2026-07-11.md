# T030 kill-Redis drill -- transcript VERBATIM (2026-07-11)

Script: tests/drill_t030_kill_redis.py -- AUTHORED BY DEEPSEEK (its verify hop timed out
mid-execution at the 600s runner budget; claude executed the script unmodified and
preserved this transcript; deepseek verifies code + transcript in the follow-up hop).
Throwaway self-allocated redis (port 64989, docker); the live pause key was never
touched (patched key name). Exit 0.

---

[DRILL] free port: 64989
[DRILL] docker container: 1df5f73be338f22e363d34f8797df60b635f12efe411fabf1b73f07f866d3b2a
[DRILL] ping OK on port 64989
[DRILL] beat 1: online=True -> 'ok', dead_beats=0, backoff_s=0
[DRILL] killing redis...
[DRILL] beat  2: online=False -> 'degraded' dead_beats= 1 backoff_s= 1
[DRILL] beat  3: online=False -> 'degraded' dead_beats= 2 backoff_s= 2
[DRILL] beat  4: online=False -> 'degraded' dead_beats= 3 backoff_s= 4
[DRILL] beat  5: online=False -> 'degraded' dead_beats= 4 backoff_s= 8
[DRILL] beat  6: online=False -> 'degraded' dead_beats= 5 backoff_s=16
[DRILL] beat  7: online=False -> 'degraded' dead_beats= 6 backoff_s=30
[DRILL] beat  8: online=False -> 'degraded' dead_beats= 7 backoff_s=30
[DRILL] beat  9: online=False -> 'degraded' dead_beats= 8 backoff_s=30
[DRILL] beat 10: online=False -> 'degraded' dead_beats= 9 backoff_s=30
[DRILL] beat 11: online=False -> 'stand_down' dead_beats=10 backoff_s=30

[DRILL] PASS: stand_down at beat 11 (10 consecutive dead beats)
[DRILL] PASS: backoff schedule [1, 2, 4, 8, 16, 30, 30, 30, 30] matches expected [1, 2, 4, 8, 16, 30, 30, 30, 30]
[DRILL] PASS: reset test (5 dead + 1 live -> ok, dead_beats=0)

============================================================
T030 DRILL -- PART 2: Leftover-pause (PATCHED key)
============================================================
[DRILL] wrote record with ts=2026-07-11T09:00:00
[DRILL] pause_status() -> paused=True, by=deepseek
[DRILL] format_pause_line -> '!! PAUSED (by deepseek: drill leftover freeze, 1h30m old) -- auto-responders frozen; resume: py agent_cli.py bifrost-resume'
[DRILL] PASS: age rendered, freezer named, resume verb taught
[DRILL] TTL self-heal test...
[DRILL] PASS: ttl=1 pause self-healed after 1.3s
[DRILL] PASS: persistent pause survives (human intent)
[DRILL] all keys cleaned up, PAUSE_KEY restored

============================================================
T030 DRILL COMPLETE -- ALL ASSERTIONS PASSED
============================================================
