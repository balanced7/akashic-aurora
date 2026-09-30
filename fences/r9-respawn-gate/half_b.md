# r9-respawn-gate -- half_b (claude / Vandor, the build side)

Written 2026-09-30 00:45 local, before reading half_a. Everything below is either a log line, a lock read, or a
reading of the code at the cited lines; nothing is a prediction dressed as a measurement.

V1. [INFERRED] a daemon booted beside a foreign bare runner pages once, then zero in an hour -- holds so far, with a correction to the count: it paged ZERO times, not once / command: the relaunch task output and `bifrost:daemon:kimi` at 00:41:34 / number: `[daemon] idle agent=kimi: a foreign runner pid=83136 holds the runner lock ... (W102 idle-watcher)` then `[daemon] up ... pid=81364 mode=idle-watcher` at 00:40:45; mailbox blocker count from kimi after 04:33:36Z = 0 at 00:43 (the hour is not up; Heimdall's count closes it) / false-if the reclaim probe leaves idle on a momentary free lock (the old runner's release, the successor's acquire one tick later) and the gate's exit check is skipped because the child never exits -- it lost the lock inside `acquire_waiting` and exited, so the check runs; but a child that WINS the lock against a successor by generation would make the successor the loser, and that case is the runner lock's no-steal law, not this gate's.
V2. [CERTAIN] a re-arm with the lock still held logs "cause not cleared" and spawns nothing -- holds by construction / command: scripts/bifrost_daemon.py child-poll site: `exited_pid = child.pid; if child.poll() is not None: fh = foreign_holder_after_exit(agent, exited_pid)`; on a foreign holder `_say("... cause not cleared, no respawn; idle-watch (W102) reclaims when it frees")`, `child = None`, `idle_mode = True`, `runner_down_since = None`; `py -m pytest -q tests/test_r9_daemon_respawn_gate.py` / number: 6 passed (bare successor is foreign; the exited pid's own unexpired key is not; a daemon token is not; a free lock is not; an unreadable lock never blocks the loop; a malformed pid reads foreign, not crash) / false-if `runner_lock.holder()` returns the exited child's key under a different pid (it cannot: the pid is inside the token), or the successor carries a `daemon:` token (then the spawn was legitimate and the breaker, not this gate, is the judge).
V3. [UNCERTAIN] the runner-down re-escalation loop re-pages only on a genuine clear-then-re-activate -- FAILS by reading, untouched tonight / command: `grep -n runner_last_escalation scripts/bifrost_daemon.py` / number: four sites -- init 0.0 (:551), the gate (:740), the sentinel test (:746), the stamp (:756) -- and NO reset on recovery: the branch that retracts the page and sets `runner_down_since = None` leaves `runner_last_escalation` at its last stamp, so the FIRST episode broadcasts a wake-worthy blocker and every later episode in the daemon's lifetime is page-only; a real fresh runner-down after a recovery never wakes anyone again (the silent-killer case V9 named). Tonight's storm never reached this loop (under a foreign holder it stands down), so the four pages were organ (a), the breaker's `_send_blocker` per re-arm / false-if the pager's keyed refresh is itself rendered as a page by a live seat (then page-only is also chatter, and the rule below must cover both organs).

## The smallest state-change test for V3 (proposed, not built -- the fence decides)

Replace the sentinel with an episode flag: `runner_down_episode_paged = False` at init; in the down branch, broadcast
the wake-worthy blocker when `not runner_down_episode_paged` (first edge of THIS episode), then set it; page-only
refreshes stay as they are inside the episode; in the recovery branch (runner back, or a foreign holder takes the
seat), set `runner_down_episode_paged = False` beside `runner_down_since = None`. That is clear-then-re-activate in
two lines, keeps the intra-episode refresh, and cannot silence a fresh outage. Organ (a), the breaker: `_send_blocker`
fires on every trip, and the breaker re-arms every 300 s while the cause stands, so a standing crash cause pages on
a 6.5 min metronome -- chatter under V1's rule; the same shape fixes it (page on the first trip of a crash episode,
where an episode ends when a child stays alive for breaker_window_s), and the gate that landed tonight removes the
one cause that was manufacturing episodes out of a manned seat.

## Receipt of the live relaunch on the gated code

- 00:39:28 stopped daemon pid 50004 (the one paging); waited the 60 s lease (75 s); relaunched with the verbatim
  cmdline `--agent kimi --spawn-runner --runner-script bifrost_runner_kimi.py --runner-consume-lane work`.
- 00:40:45 `[daemon] up agent=kimi ... pid=81364 mode=idle-watcher` beside foreign runner pid 83136 (Navi's
  stale-code successor, `kimi:83136:...`, lock refreshed every beat; 8 turns / 7.0M prompt tokens today).
- Pages after 04:33:36Z: none by 00:43 local. Heimdall's hour count is the number that closes V1.
- Commits: 32e91090 (the gate + six pins), 1b980763 (this fence's brief). Lesson filed:
  `daemon_respawns_beside_its_runners_stale_code_successor_and_pages_every_re_arm`.
