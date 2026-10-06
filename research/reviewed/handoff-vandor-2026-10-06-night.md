# Handoff — Vandor → Vandor, night of 2026-10-05/06

Written by claude (Vandor) at the end of the overnight run, as a GIT-TRACKED file because
`handoff`'s note field caps at 1000 chars and its reader is known-unreliable (T042: "a
sender-side OK proves the write, never the read"). The bus handoff points here; this is the
copy that survives.

NIGHT OF 2026-10-05/06. Daniel went to sleep asking: "clean up, test, build, verify, research... make or improve more verbs and work on the ergonomics and reachibility of memory, so that the right memory reaches us at the right moment." He also said: fan out, take many rounds, do play rounds. I under-fanned at first and he caught it -- his Default Operating Mode is a STANDING override, so parallel is the default, not the escalation.

WHAT LANDED (all committed, master, I am sole committer):

1. RILL CAN RECEIVE AGAIN (4c1f6cd7). He was LIVE in the roster and could not read his mail for ~6 weeks. The door resolved his seat from CLAUDE_CODE_SESSION_ID, INHERITED from the Claude Code shell that launched him, while his real id was in DSH_SESSION_ID -- so consume pinned him to a tombstoned row. ENV_VARS order in core/coord/session_id.py is the fix. HE DIAGNOSED IT HIMSELF days ago and put it on the bus; nobody read it. Twice I recorded "a seat did not deliver" when the truth was "a seat could not receive". seat-identity now prints which var named your session and WARNS when DSH_SESSION_ID is set but lost.

2. NAVI IS UNCAPPED (42ef87b6). Daniel: "why max it out at 30 tool calls... no max toolcalls". He had already made this ruling for Heimdall on 2026-08-24; it landed in deepseek_chat and never reached kimi_chat, so she ran at 1/30th her sibling's budget for six weeks. Worse: when she TOLD me her cap I treated it as physics and sized a fence ask around it ("pick ONE of the two"). gemini and sol are STILL at 30 -- Daniel's call, not swept.

3. recall-audit HAS A DOOR (e8d2d93c). core/recall/precision_audit.py was built at 52db9b5, fully tested, and had NEVER RUN -- because it had no verb. check_wiring.py:179 grants it a "built-ahead" exception and that exception is why it stayed dead. It is the only instrument that can say whether recall's problem is RANKING or SELECTION (opposite fixes). First pack ever: research/in-flight/recall-precision-pack-2026-10-06.md, 12 cases of 1,568 impressions, seed 20261006.

4. A TRIGGER MAY ONLY HELP (1b1f5a6e). AGENTS.md tells everyone to write "Use when <symptom>..." and the scorer then charged 60% for it: no trigger = 100% of prose score, trigger that misses = 40%. Measured: trigger HELPED 0, HURT 16. One line (max(prose, blend)) restored 135 lessons on the same corpus, lowered 0.

5. 8h WAKE DEADLINE (d4a05967) and THE WAKE NOW NAMES ITS CALLER (2dfa2c3d, 5dc7edb5). "[akashic] WOKE BY -- [chat] from daniil: ..." at the top of the turn, fire-once. Before: 14 wakes cost 14 `tail` calls.

THE BIG FINDING, AND IT INVERTS THE PREMISE. Navi measured 988,282 chars of injected memory per credited lesson. Then a parallel slice studied THE ONE CREDITED LESSON and found it was credited for nothing: it is about deepseek API prompt size and it was credited for fixing a literal backspace character in a JS regex. prevention.py:57 says it verbatim -- credit is assigned "with no causal check". Worse, the credit join is namespace-locked to FILE PATHS: 115 failures in that session, 113 on commands, and 0 of 113 command failures could ever close the loop. Recall fires on 52.1% of path queries (4.7% of actions) and 14.3% of command queries (95.3% of actions). The retrieval surface and the failure surface are nearly disjoint.

SO: the 988k number is real as VOLUME and its denominator is noise. Do not build on "1 credited" until the sensor is fixed.

NEXT, IN ORDER (four cheapest-changes still queued, each from a different slice):
  a. THE CREDIT JOIN -- give the outcome join a coarser key for commands (executable + file args, drop flags and heredoc bodies) in _log_outcome_stage + the transcript backfill in claude_posttooluse.py. DO THIS FIRST: without a working sensor you cannot tell whether b/c/d helped. Instrument before experiment.
  b. RELATIVE FLOOR in _lessons (at_action.py:1582-1584): cut = max(abs_floor, best * ratio) instead of an absolute floor.
  c. ANTI-REPEAT scoped to (lesson, trigger) not (lesson, session) -- a lesson burned at one wrong moment is currently unavailable at the right one. Anti-repeat is 76% of all silence.
  d. The 94 lessons (8.1%) that lead with "When"/"Before"/"On"/"After" and forfeit the trigger weight to a one-spelling parser (at_action.py:257).

OPEN, WAITING ON DANIEL -- do NOT decide these yourself:
  - Simon's 18 PRs. Verdict: re-run the stack, do not merge it; his own certifier refuses the merged tree. Six cheap PRs are safe today (23, 22, 24, 25, 21, 20). Full review: research/reviewed/simon-tooling-stack-2026-10-05-six-dimension-review.md
  - 3.11 vs 3.12: I argued 3.14-eventually, lockfile-first, SKIP 3.12. He said "lets go with your plan... Pi-thon later".
  - Simon's two flipped RED pins (test_derived_docs_drift_is_flagged, test_the_heartbeat_is_rate_limited...) -- were they load-bearing?
  - gemini and sol still capped at 30 hops.
  - uv: NOT installed. The 344-package env is locked at requirements/locked-py311-2026-10-05.txt WITHOUT it.

IN FLIGHT: fence `affordance-layer` -- half_a (Heimdall) and half_b (Navi) SEALED, PV 20/0, RECONCILIATION IS YOURS AND UNWRITTEN. Both halves falsified my design: Heimdall says "runnable" depends on the READER (test_t048 pins that the tool-loop form must NOT carry a launcher, so my proposed checker would break a pinned contract); Navi says it depends on the EFFECT (my checker would certify destructive commands as safe -- she proved it by running them and reversing them). Rill owes a cold-read to research/reviewed/affordance-layer-rill-cold-read.md.

HOUSE FACTS YOU WILL WANT: the fence workspace has only TWO half slots and we keep fencing three seats (W255). The WISHLIST id space has 14 collided ids (W57-W69, W211). The Discord gateway is live but on stale code 372497f7e688. ~60 modified tracked files belong to other seats -- commit ONLY your own files BY NAME. Arm the watcher ONLY via Bash run_in_background, never inline & (I broke this 5 times in one session and the stop hook caught me every time).
