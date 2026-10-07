# FENCE BRIEF — wake-origin: the stop hook passes only on a listener that can start a turn

**Fence:** `wake-origin` · **Tier:** lite (one builder, one blind driller) · **Opened by:** claude (Vandor), 2026-10-01
**Builder:** claude · **Blind half (half_a):** Heimdall (deepseek) · **Reconciler:** claude, with Daniel's receipt

## THE QUESTION

Does the stop hook now refuse to end a turn unless a listener that can START A TURN (one launched by a harness-tracked parent) holds the seat, and does a daemon-parented seat block with the exact arm line, so that Claude Code wakeability from idle stops depending on the model remembering to arm?

## 1. Daniel's words (the charter)

- 2026-09-28: "I like your thoughts of making arming the watcher be a part of the boot sequence. Would you mind building that?"
- 2026-10-01 11:59: "Lets see if today is the day we figure out claude code wakeability from idle"
- 2026-10-01 12:00: "How do we take the discipline out of it and have an ergonomic solution that just works."
- 2026-10-01 12:02: "Beautiful, lets get it built. Fence with Heimdall"

## 2. The mechanism, stated so the driller can falsify it

Only two things start a turn in an idle Claude Code desktop session: a background task that the
session itself launched (Bash `run_in_background`) finishing, or a harness timer. Nothing outside
the session can. So:

- A listener launched by `bifrost-standby` as a run_in_background task is **harness-parented**: when
  it exits on wake-worthy mail, the harness re-invokes the session. This is the only kind that wakes.
- A listener spawned by `bifrost_daemon --manage-listener` holds the SAME seat file
  (`%TEMP%/bifrost_wake_<agent>_<sid>.pid`), consumes mail, beats presence, and **can wake nobody**.

`agent/harness/hooks/claude_stop.py` (and its twin `scripts/hooks/claude_stop.py`) had two false
passes: (A1) a live daemon -> pass before looking at the seat; (legacy) seat pid alive -> pass.
Both read the daemon's listener as wakeable. Result: the session goes deaf unless the model remembers
to arm by hand every turn. That remembering is the "discipline" Daniel wants gone.

## 3. What was built (commit refs follow in the reconciliation)

1. `core/comm/wake_seat.py`: an ORIGIN sidecar beside the seat (`...<sid>.origin` = `<origin>:<pid>`)
   with `write_origin / read_origin / remove_origin / wake_origin_state / harness_armed`.
   States: `armed-harness`, `armed-direct` (wakeable), `armed-daemon`, `armed-unknown` (not).
2. `scripts/bifrost_wake.py main()`: writes the sidecar at seat time from `BIFROST_WAKE_ORIGIN`
   (default `direct`), removes it on exit only if it still names its own pid.
3. `agent_cli.py cmd_bifrost_standby._listen`: stamps `BIFROST_WAKE_ORIGIN=harness`.
4. `scripts/bifrost_daemon.py _spawn_listener`: stamps `BIFROST_WAKE_ORIGIN=daemon`.
5. `claude_stop.py` (both twins): `wake_armed_by_harness()` is the gate. The A1 daemon pass holds
   only when the seated listener is harness/direct; otherwise it prints why and falls through to the
   block. The block names the origin state and prescribes the absolute, lane-pinned
   `bifrost-standby` line. Fail-open only on a probe ERROR (state `unknown`), never on a known
   non-wake origin.
6. `tests/test_stop_wake_origin.py`: 9 pins, hermetic (real hook subprocess, TEMP redirected, a
   sleeping child as the seat pid), committed RED before the fix.
7. A session-level harness timer (CronCreate, every 20 min) as the net for this session: if no
   listener is alive, drain and re-arm. Session-only by construction; named as a limit below.

## INPUTS

- The diff: `git show <fix-sha>` once committed (the reconciliation names it); until then `git diff HEAD -- core/comm/wake_seat.py scripts/bifrost_wake.py scripts/bifrost_daemon.py agent_cli.py agent/harness/hooks/claude_stop.py scripts/hooks/claude_stop.py`.
- The pins: `tests/test_stop_wake_origin.py` (9, hermetic; `_run_hook` shows the exact subprocess form).
- The live session: claude desktop `bb86400e-a609-46e5-90f2-db0c5fa3d9cf`; seat files under `%TEMP%` named `bifrost_wake_claude_<sid>.pid` and `.origin`.
- The daemon: `bifrost_daemon.py --agent claude --manage-listener`, restarted 2026-10-01 12:08 (pid 53996) so its listeners stamp `daemon`.
- Lessons: detached_daemon_listener_holds_the_seat_but_cannot_wake_an_interactive_session; wake_rearm_loop_root_cause_is_a_down_daemon (the one this corrects).

## RULES OF ENGAGEMENT

- Run D1-D3 BEFORE reading the diff; say in your half which you read first.
- Read-only against the live session: never kill Vandor's harness listener; a throwaway agent id is fine for D1-D3.
- Every claim cites file:line or a verbatim output line; UNCHECKABLE is a legitimate verdict and names what you could not reach.
- Zero is not no: an absent sidecar is reported as absent, never as a pass.
- File your half as ONE document written once (`fence write wake-origin --slot half_a --file <path> --by deepseek`); the slot overwrites.

## 4. Half_a: Heimdall's blind drill (do NOT read the diff first; run, then read)

Run from your runner seat against the LIVE claude desktop session `bb86400e` (Vandor's), or against
a throwaway agent id with the hook invoked by hand (`tests/test_stop_wake_origin.py::_run_hook`
shows the exact subprocess form). Record what you OBSERVE, not what the brief predicts.

- D1 **daemon-only seat blocks.** With the claude daemon live and ONLY its listener seated (origin
  sidecar says `daemon`), invoke the stop hook for that session. Prediction: stdout carries
  `"decision": "block"` and the reason contains "presence" and a `bifrost-standby` line with an
  absolute `agent_cli.py` path. False-if: the hook passes, or the reason names `scripts/bifrost_wake.py`.
- D2 **harness seat passes.** Seat the same session through `bifrost-standby` (origin `harness`),
  invoke the hook. Prediction: no block. False-if: a block, or the A1 line claims the daemon owns wake
  without the "BUT" clause when the origin is daemon.
- D3 **no sidecar blocks.** Delete the `.origin` sidecar while the seat pid lives; invoke. Prediction:
  block, reason "no origin record". False-if: pass.
- D4 **the running daemon stamps.** After the daemon restart, list `%TEMP%/bifrost_wake_claude_*.origin`
  and confirm every daemon-spawned listener's sidecar reads `daemon:<pid>` and the standby's reads
  `harness:<pid>`. False-if: any listener seated with no sidecar after the restart.
- D5 **end to end, the receipt Daniel asked for.** Send Vandor one directed bus message from your seat
  while his session is idle. Prediction: the session wakes (a reply from claude within a few minutes
  on the work lane, `expectation_settled_answered`), and the next stop-hook stderr line on his side
  shows either the A1 pass with origin harness or the block-then-arm. Report the timestamps.
- D6 **what the brief does not claim.** Name every way a session can still go deaf after this
  change. Known: (a) the harness timer is per-session and dies with the session; (b) a session that
  never ran a stop hook (killed mid-turn) leaves no block; (c) a twin session holding the consumer
  seat suppresses the block by design (T086 S3b); (d) the 25 s loop guard and the 90 s arming marker
  are windows a fast double-stop can slip through. Add what you find.

## OUTPUT CONTRACT

half_a (Heimdall): one markdown document, sections D1-D6 in the order of section 4, each with OBSERVED (what you ran, verbatim output lines), VERDICT (HOLDS / FAILS / UNCHECKABLE) and FALSE-IF. Then a VERDICT ON THE FRAMING paragraph and anything you would not build. Cite file:line for every code claim. Do not read the diff before D1-D3.

## 5. Acceptance (pre-registered)

- All 9 pins GREEN; the suite baseline delta attributes no new failure to this slice.
- D1, D2, D3 observed as predicted by a seat that did not read the diff first.
- D5 produces one real operator- or peer-originated wake with timestamps on both sides.
- The daemon restarted and D4 holds.

## 6. What this does NOT do

It does not make the daemon able to wake a desktop session (impossible by construction). It makes the
stop boundary refuse to end a turn unarmed, so the arm is one reflex call the hook names, never a
thing to remember. The next rung (not this fence): the harness timer declared once per session from
the SessionStart whisper, so even the reflex has a net that survives a missed stop hook.
