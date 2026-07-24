---
akashic_id: art_20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf
akashic_sha: cfe7ce1f55a4
status: current
type: design
date: 2026-07-01
title: "Wave 2 design (claude, FENCED): wake-seat ownership + nonviolent displacement"
gist: "standing fence. Targets docs/resilience-battery-2026-07.md section 6 kill conditions.) Class: rationale ## Core insight The singleton alread"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_the-resilience-battery-stress-tests-vali_7b7b49
    rel: cites
  - target: art_20260710_deepseek-t029-wave-2-fenced-design-sessi_9f1fb7
    rel: cites
created: "2026-07-10T09:29:08"
updated: "2026-07-23T21:42:07"
---
<!-- GENERATED PROJECTION of art_20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Wave 2 design (claude, FENCED): wake-seat ownership + nonviolent displacement

standing fence. Targets docs/resilience-battery-2026-07.md section 6 kill conditions.)
Class: rationale

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

---

# RECONCILIATION (claude x deepseek, 2026-07-10 -- both designs committed blind first)

DeepSeek's blind design: research/reviewed/deepseek-wave2-seat-design-2026-07-10.md.

## Convergences (both blind passes agree -- highest confidence)
- Never kill a live session's watcher; the reap's identity-only check is the root defect.
- Close the holder=None fail-open with a LOUD exit, not silent watching.
- No Windows graceful-kill gymnastics; no heartbeat TTL; no new registration protocol;
  session id trust bound = the session arms its own watcher.

## Divergences -> resolutions
1. SEAT ARCHITECTURE -- his per-session seats (every live session wakeable, fan-out) vs my
   single per-agent seat (one wake, newest-stopper holds duty). ADOPT HIS. The morning
   incident itself refutes my heuristic: Daniel was driving the OLDER session while the
   newest stopper held the seat -- single-seat wakes the wrong window. Fan-out is
   self-selecting (the driven session is mid-turn and just works; an idle twin wakes, reads
   the ledger/locks, yields). Cost: one extra re-invoke per message per extra live session;
   N is small. Semantics documented in AGENTS.md.
2. LIVENESS SIGNAL -- his stop-hook marker freshness vs my parent-chain walk. THE CATCH
   (recon finding, must be pinned): marker freshness measures TURN CADENCE, not session
   life. An idle-but-alive session (user reading; no turns for an hour; watcher armed --
   the exact state wake exists to serve) has a stale marker -> his reap kills its LIVE
   watcher -> the kill loop returns THROUGH the fix. RESOLUTION: two-factor liveness --
   marker fresh (AKASHIC_WAKE_MARKER_FRESH_MIN, default 30) = alive, fast path, no WMI;
   marker stale -> parent-chain decides (WMI; ANY error = alive; pid-recycle guard: an
   "ancestor" younger than the watcher is a recycled pid = dead). Reap ONLY when marker
   stale AND chain dead.
3. EXIT CODES -- his design leaves STAND_DOWN_RC=4, so benign displacement/seat-loss still
   badges a LIVE session's task as FAILED (same-session newest-wins fires rc=4 into the
   session that just re-armed). ADOPT MINE (D5): stand-down, seat-lost, quiet-deadline all
   exit 0 with a one-line provenance; nonzero = real faults only (WAKE_ERROR=1, OFFLINE=2).
4. OWNERSHIP ENCODING -- my JSON-in-file vs his session-in-FILENAME. ADOPT HIS: filename
   encoding is glob-enumerable for the janitor and keeps the pid-only file parse untouched.
5. MIGRATION -- ADOPT HIS K6 self-heal (the old name-keyed watcher is invisible to the new
   glob and has no seatless branch in old code): at first new-code session start, kill the
   old name-keyed watcher if alive, remove the old seat file. The one remaining legitimate
   live-process kill, bounded to the migration moment, provenance-logged.
6. His flaw-B+C double-seat-loss race: dissolves under per-session files (no shared file).

## Amended kill conditions
K6 (deepseek): migration self-heal -- after one full fleet cycle, zero name-keyed seats.
K7 (recon): IDLE-SESSION IMMUNITY -- stale stop marker + live process chain is NEVER
reaped; pinned by test_reap_idle_but_alive_not_reaped.

## Build plan (the reconciled slices)
B1 bifrost_wake.py: --session arg; session-scoped seat path; seatless -> stand down; all
   benign exits 0 w/ provenance line.
B2 claude_stop.py: session_id from hook stdin; session-scoped HEARTBEAT + MARKER; arm
   instruction carries --session; legacy fallback when session_id absent.
B3 claude_sessionstart.py: reap -> enumerate bifrost_wake_<agent>_*.pid + legacy file;
   dead pid = clean file only; alive pid = identity check, then two-factor liveness;
   reap/janitor actions append one-line provenance to bifrost_wake_<agent>.reap.log;
   K6 migration branch.
B4 pins: deepseek tests 1-6 + exit-code pins + K7 idle-immunity pin + janitor
   provenance pin; live drills 7-8 + fan-out observation (record wake count per message
   with 2 live sessions; expected = one per live idle session, BY DESIGN).
B5 docs: AGENTS.md wake-contract line (per-session seats, fan-out semantics);
   battery sec. 6 disposition update after the build ships.
