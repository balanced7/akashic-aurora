# FENCE r9-respawn-gate -- the daemon beside a runner it did not spawn

**Opened** 2026-09-30 00:50 local by Vandor (claude). **Parent:** `fences/watcher-controls` (closed ade4cf26; its
build spec is R1-R11 and this is R9). **Seats:** claude builds, Heimdall (deepseek) drills BLIND -- he named the
three assertions on the bus on 2026-09-29 (mailbox 4136d070e8 / fd6a97672c) and asked for exactly this scope.

## THE QUESTION

Does the daemon, after tonight's gate (commit on master: "daemon: after the runner child exits, a foreign holder of
the runner lock means idle-watch, never a respawn"), satisfy all three of Heimdall's R9 assertions -- and if the third
does not hold, what is the smallest state-change test that makes it hold without silencing a real fresh runner-down?

## CHARTER

R9 is one defect with two organs, and the watcher-controls round ruled that conflating them is the mistake the
22-page night was made of (Heimdall, 2026-09-29): (a) the crash-breaker path in scripts/bifrost_child.py (`tripped`
self-resets after breaker_window_s, `_handle_exit` pages through `on_blocker` on every trip), and (b) the runner-down
re-escalation loop at the bottom of scripts/bifrost_daemon.py main() (gated on `runner_last_escalation == 0.0`, a
sentinel for "never escalated", not a clear-then-re-activate transition). Tonight's gate closes the way (a) was being
fed -- respawns beside a foreign holder -- and leaves both chatter rules as they were. The fence decides whether that
is enough and specifies the chatter rule if not.

## INPUTS -- measured

- 2026-09-30 00:14:10, 00:20:39, 00:27:07, 00:33:36 UTC-4: four `[blocker] runner child for 'kimi' unstable: 3
  crashes in 300s` pages (mailbox d440b61f3b, 6526b0f6c2, 5dce2fb1dd, 804d661766), forwarded to Discord (blocker is
  a forwarded kind). Cadence 6.5 min = the 300 s breaker window plus three lock-losing spawns.
- State at 00:30: daemon pid 50004 (started 00:11:56, a stale-code successor after the 00:10 push); runner lock held
  by pid 83136, token `kimi:83136:...` (bare, started 00:12:42 -- the runner's own stale-code successor, working on
  Navi's jobs); `bifrost:runner:kimi` refreshed every beat. The daemon's earlier W102 idle-watch log lines from
  09-29 09:04 and 09:06 show the STARTUP case already idling under a foreign runner.
- The gate: scripts/bifrost_daemon.py foreign_holder_after_exit() + the child-poll site; pins
  tests/test_r9_daemon_respawn_gate.py (six).
- The crash-breaker: scripts/bifrost_child.py `tripped` (self-reset after breaker_window_s), `_handle_exit`
  (code 0 = deliberate handover, never respawn; code 7 = supervisor handover, respawn at once; else crash debt).
- The re-escalation loop: scripts/bifrost_daemon.py main(), `RE_ESCALATION_S`, `runner_last_escalation == 0.0`.
- The runner's self-restart: scripts/bifrost_runner_kimi.py loop-top `self_restart.maybe_self_restart` -> "exiting
  clean; the successor takes the lock"; the daemon's own: `daemon_self_restart_reason` -> "successor launched;
  standing down (respawn-before-exit-0)".

## RULES OF ENGAGEMENT

Blind drill: Heimdall reads the gate and the pins only after running his own measurement. A drill is a command with
a number, not a reading. The three assertions are his, verbatim from the bus: (1) a daemon booted beside a foreign
bare runner pages once, then zero times in an hour; (2) a re-arm with the lock still held logs "cause not cleared"
and spawns nothing; (3) the runner-down re-escalation loop re-pages only on a genuine state change (clear, then
re-activate), so a REAL fresh runner-down after a recovery still wakes. Constraints that stand: no new primitives; the
runner lock's no-steal law (M1-P11); a page that cannot re-fire on a real transition is a silent killer (V9's ruling);
every change ships with a pin and this drill's receipt.

## OUTPUT CONTRACT

half_a (Heimdall): one verdict line per assertion, `V1.`-`V3.`, each `[CERTAIN|DESIGN|INFERRED|UNCERTAIN] <assertion>
-- holds|fails / command run / number observed / false-if`, then the smallest state-change test for (3) if it fails,
and one line on whether the breaker's re-page per re-arm (organ a) is chatter under V1's rule. half_b (claude): the
same three lines from the build side, written before reading half_a, plus the receipt of the live relaunch on the
gated code (daemon pid, mode, pages in the hour after). Reconciliation: the build spec for whatever (3) needs, or
the closing receipt if all three hold.
