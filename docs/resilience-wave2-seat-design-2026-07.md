# Wave 2 design (claude, FENCED): wake-seat ownership + nonviolent displacement

Status: current  (2026-07-10; committed BEFORE reading deepseek's parallel design -- the
standing fence. Targets docs/resilience-battery-2026-07.md section 6 kill conditions.)

## Core insight

The singleton already contains a NONVIOLENT displacement protocol: newest-wins seat write +
the older watcher's poll-and-stand-down. The kill loop exists because (a) the reap uses force
where displacement suffices, and (b) the stop hook trusts a name-keyed seat it cannot prove is
its own. Fix the OWNERSHIP question and the violence becomes unnecessary; nobody has to die.

## Design

D1. SEAT OWNERSHIP RECORD. The heartbeat file becomes JSON: {pid, session_id, started_at}.
    bifrost_wake gains --session <id>; claude_stop's arm instruction passes its own session id
    (available in the Stop hook stdin payload). Legacy plain-int seats parse as
    {pid, session_id: null} (ownerless) -- tolerated, displaced on the normal path, so no
    migration step. Writer stays newest-wins.

D2. STOP HOOK: wake_armed() = "MY live watcher holds the seat" -- seat parses AND pid alive
    AND cmdline contains bifrost_wake AND session_id == THIS session. Anything else (foreign,
    ownerless, dead pid, corrupt seat, missing file) -> arm my own watcher, which writes the
    seat (displacement). The displaced live watcher stands down at its next poll (<= one inner
    block). No process is ever killed to take a seat.

D3. REAP DEMOTED TO JANITOR. _reap_stale_watcher stops killing live processes entirely.
    Scope: if the seat's pid is DEAD -> delete the stale seat file; if ALIVE -> leave it
    (displacement handles duty transfer; a live foreign watcher is legitimate, not prey).
    Whenever the janitor acts it writes a one-line provenance file
    (bifrost_wake_<agent>.reap.log: who, when, what it found, what it did) so any later
    "watcher died" investigation is distinguishable from a crash. Identity-only taskkill is
    deleted -- the proven-orphanhood question dissolves: we never needed to kill orphan
    PROCESSES, only to free the SEAT, and dead-pid seats are the only truly stale seats.
    (A live watcher whose session died self-retires: it either stands down when displaced or
    exits at its own --deadline; its exit re-invokes a dead session = harmless no-op.)

D4. SEATLESS FAIL-OPEN CLOSED. bifrost_wake's poll: holder is None (missing/unreadable seat)
    -> RE-ASSERT my ownership record instead of watching invisibly. Verify on next poll;
    if a newer writer raced me, standard stand-down. Brief double-watch is harmless by
    detect-only design; INVISIBLE watchers become impossible.

D5. STAND-DOWN IS NOT A FAILURE. Stand-down (and quiet deadline expiry) exits 0 with a
    one-line provenance ("stood down: seat taken by pid N at ..."), because a watcher's exit
    code is operator-facing (the harness badges nonzero as a FAILED task -- this morning's
    phantom-failure noise). Nonzero stays reserved for real faults: WAKE_ERROR=1, OFFLINE=2.

SEMANTICS MADE EXPLICIT (docstring + AGENTS.md line): one wake seat per agent id; the seat
belongs to the most-recently-stopping session; older concurrent same-id sessions are
human-driven by definition (they hold no seat and get no bus wake). Multi-session wake
fan-out is a deliberate NON-goal.

## NOT built (scope discipline)

- No per-session wake fan-out (one seat per agent stands).
- No CTRL_BREAK / console-signal delivery to detached children (Windows-unreliable; the
  design removes the need by never force-killing).
- No supervisor for wedged watchers (--deadline self-expiry already bounds a wedge).
- No signed/authenticated seats (same trust bound as the rest of the fleet: local temp dir).
- No changes to wake_block cursor semantics (P0 detect-only is untouched).

## Kill-condition mapping (section 6)

1. Two concurrent sessions, 3 start/stop cycles, no murder: PASSES -- nothing kills a live
   watcher anymore; seats transfer by displacement (D2+D3).
2. Reap only on proven orphanhood: PASSES BY DISSOLUTION -- the janitor touches only
   dead-pid seat FILES; live processes are never reaped at all (D3).
3. No silent seatless watcher: PASSES -- holder=None self-heals or stands down loudly (D4).
4. Reap distinguishable from crash: PASSES -- janitor provenance log + stand-down exit 0
   with reason; nonzero exits now MEAN faults (D3+D5).
5. Zombie generations still end up off duty: PASSES -- displaced zombies stand down within
   one inner block; dead-pid seats are cleaned; the drill's kill-x5 script exercises D2-D4.

## Regression pins

Hermetic pytest (fake seat files + injected liveness/cmdline fns; no Redis):
- seat parse: JSON, legacy int, corrupt, missing -> ownership classification table
- wake_armed decision table: mine-alive / mine-dead / foreign-alive / foreign-dead /
  ownerless / corrupt -> exactly {pass, arm} per D2
- janitor: alive-pid seat untouched + no taskkill call path left to invoke; dead-pid seat
  deleted + provenance written
- holder=None poll -> re-assert; raced re-assert -> stand-down; stand-down/deadline exit 0,
  WAKE_ERROR still 1
Live drill (graded, runbook + evidence):
- two real sessions, alternating start/stop x3: zero watcher kills, seat always held by the
  last stopper, one directed message = exactly ONE wake
- zombie generation: kill a session, confirm its watcher stands down on displacement and the
  janitor clears its seat if the process is gone
