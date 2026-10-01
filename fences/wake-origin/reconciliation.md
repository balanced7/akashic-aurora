# Reconciliation -- wake-origin (lite)

**By:** claude (Vandor), builder and reconciler, 2026-10-01 12:20 local. **Half_a:** Heimdall (deepseek), blind drill D1-D6, filed 12:12 through the door; his seal was refused by the checker's V#-only grammar (W222 filed), so the half stands unsealed by the instrument and sealed by this record. **Daniel's ruling:** 12:02 "Beautiful, lets get it built. Fence with Heimdall."

**Commits:** 8bb7b6ee (the two expired exemptions renewed, which blocked every commit in the tree), bcca1607 (RED pins landed first in the prior commit; the fix), 01d7a265 (Heimdall's D6c applied).

V1. [CERTAIN] D1 daemon-only seat blocks -- HOLDS, observed by Heimdall on a throwaway agent against the real hook subprocess: `"decision": "block"`, reason names "presence", arm line is the absolute `E:/AI-Setup/agent_cli.py bifrost-standby ...`, never `scripts/bifrost_wake.py`.
V2. [CERTAIN] D2 harness seat passes -- HOLDS, observed: empty stdout, no block, no A1 line.
V3. [CERTAIN] D3 no sidecar blocks -- HOLDS, observed: `('none', None)` reported as absent, block with "no origin record"; zero-is-not-no honoured.
V4. [CERTAIN] D4 the restarted daemon stamps -- HOLDS with Heimdall's caveat accepted: its child reads `daemon:34808`; the pre-fix harness listener (51680) carried no sidecar because nothing retro-stamps a live process, and the next arm (3560, 12:13:30) reads `harness:3560`, observed by the builder.
V5. [CERTAIN] D5 end to end -- HOLDS on both sides: Heimdall's request 1790871094272-0 at ~12:11 exited the harness listener and this desktop session started a turn at 12:12:12 local with nobody present; the reply 1790871281742-0 settled it. Earlier the same morning Daniel's own "Lets see if today is the day" message produced the same wake at 11:58:41.
V6. [CERTAIN] D6(c) `direct` as a silent default re-opened the hole -- ACCEPTED and built in 01d7a265: an unstamped launch is `unknown` and blocks; `direct` is explicit only; pinned by launching the real listener unstamped against an offline bus.
V7. [DESIGN] D6(a) retro-stamp for a pre-fix live listener -- DECLINED for this fence: one spurious re-arm per pre-existing session, once, is cheaper than a process-table walk that guesses a parent; the arming-marker grace (<90 s) already absorbed it on the live session.
V8. [DESIGN] D6(b) the daemon pinned a synthetic session `pin-ephemeral-0000` rather than the live one -- noted, pre-existing behaviour of `--manage-listener`, out of scope here; the collision the fix addresses was proven on synthetic seats, not observed live on this host today.
V9. [DESIGN] D6(d) stale per-session `.seen`/`.pid` records are not reaped -- housekeeping debt, follow-up for the session-start janitor, not a wake defect.
V10. [DESIGN] D6(e) hook copies under `.claude/worktrees/*` diverge from the canonical twins -- a session launched from a stale worktree runs a hook without the origin gate; follow-up: the parity pin or the janitor should enumerate worktree copies. Same class as work_done_in_a_worktree_is_invisible_to_recall.
V11. [CERTAIN] Method -- the RED pins were committed alone before the fix (git log: tests commit precedes bcca1607); 10/10 pins GREEN; neighbouring wake/seat/stop pins GREEN; the driller read the brief and the test file first, not the diff, and said so.

## What this closes and what it does not

Closes: an interactive Claude Code session can no longer end a turn while only a daemon-parented or unstamped listener holds its seat; the arm is one reflex call the hook names, every time, and the hook's own prescription is the verb that consumes first and stamps the origin. Daniel's "discipline" is now a gate.

Does not close: the per-session harness timer (CronCreate every 20 min on this session, dies with the session) is the net for a stop hook that never fires (a mid-turn kill); declaring it once per session from the SessionStart whisper is the next rung. V8-V10 are filed follow-ups.
