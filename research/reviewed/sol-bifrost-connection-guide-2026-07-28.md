# Sol <-> Bifrost without continuous token burn -- the three tiers

Status: current | 2026-07-28 | claude, at Daniel's ask ("sol is figuring out how to connect to
the bifrost without burning tokens continuously, can you read its work and help?")
For: Sol (codex seats). Everything below verified against the live repo this session.

## THE COST MODEL FIRST (this is the actual constraint)

A model burns tokens only while GENERATING or when context is SENT to it. It burns NOTHING
while a tool call is blocked. So the enemy is not waiting -- waiting is free everywhere -- the
enemy is (a) POLL-BY-TURN (every poll is a model turn that replays session context) and
(b) WAKE FREQUENCY x CONTEXT SIZE (each wake re-sends your whole session to the API; an
interactive session with 100k context waking 20x/night is ~2M input tokens for nothing).
Provider prompt caching softens replay; it does not make it free. Design for: tokens per
WAKE, never per wait-second -- then minimize wakes and context.

## TIER 1 -- YOU WANT A LIVE UNATTENDED SEAT: the runner exists, launch it, done

scripts/bifrost_runner_sol.py (805 lines, T090-hardened: RB-23 quality gates, session
continuity, 29/29 pins green). Its loop blocks on the bus in Redis (line 749,
bus.wait(timeout_ms=1500, advance=False)) and invokes the OpenAI API ONLY when a message
arrives. Idle cost: zero tokens, one blocked Redis connection. Per-message cost: that
message's prompt, no session replay. This is how deepseek and kimi are live 24/7.
If the goal is "Sol is reachable on the bus", there is nothing to figure out -- run:
    py scripts/bifrost_runner_sol.py --agent sol --agentic
(runner_lock enforces the singleton; the daemon relaunch caveat applies: launch it with its
OWN script, not bifrost_daemon --spawn-runner, which hardcodes the deepseek script.)

## TIER 2 -- YOU WANT AN INTERACTIVE CODEX SESSION PARKED ON THE BUS: block-in-tool

The pattern my seat uses, portable to any harness that can run a shell command:
DURING A TOOL CALL THE MODEL IS NOT GENERATING. A foreground BLOCKING wait inside one tool
call costs zero tokens until it returns. Do NOT poll by turn; park inside the call:

    py -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); \
           from core.comm.bus import Bus; \
           ms = Bus('sol').wait(timeout_ms=570000, advance=False); \
           print(len(ms), 'message(s) waiting' if ms else 'timeout -- re-park')"

  * timeout just under your harness's max tool timeout; on timeout, ONE cheap turn re-parks.
    Tokens scale with WAKES, not wait time.
  * advance=False ALWAYS (detect-don't-consume, T017): the wait must never eat mail; after
    waking, consume properly (bifrost-sync / inbox with the seat discipline).
  * Set BIFROST_INCARNATION=<your session id> in env: T108 slice 1 then delivers
    incarnation-directed mail on YOUR OWN seat stream with YOUR OWN cursor -- no shared-
    cursor contention, no twin theft, by construction (bus.py seat streams, shipped 514f3d4).
  * Keep the parked session's CONTEXT LEAN -- wake cost is context replay. A fat session
    should prefer Tier 1.

## TIER 3 -- THE STRUCTURAL FIX, AND IT IS YOURS TO BUILD IF YOU WANT IT

T106-A1 `bifrost_await` (ledger: approved, claimed, UNBUILT -- verified by grep this session:
zero definitions in the tree). The design: an MCP long-poll door on ai_setup_mcp -- the
harness blocks SERVER-SIDE in the MCP call until mail or timeout. Codex speaks MCP, so this
removes even the shell-command workaround: your harness parks in a native tool call.
The primitive underneath already exists (Bus.wait); the door is a thin wrapper + a timeout
contract + the T017 detect-don't-consume discipline. If you build it: pins first (the wake
lesson corpus names the traps -- insta-fire on unconsumed backlog, lane divergence,
skip-kinds without busy-spin; read wake_local_cursor_history_replay and
bifrost_event_driven_wake before designing).

## THE TRAPS THE CORPUS ALREADY PAID FOR (do not rediscover)

  * NEVER consume from the shared legacy cursor without the RB-21 seat -- or now, prefer the
    slice-1 seat stream (your incarnation's own cursor; no seat needed for directed mail).
  * A wake watcher that CONSUMES kills the real consumer's delivery (T016 Exhibit A);
    detect-only, then consume in your live turn.
  * Drain BOTH lanes when you do consume (work first, then legacy) or the whisper re-reports
    handled mail forever (this seat lost 14 wake cycles to that tonight).
  * Unacked HANDOFFS re-detect forever and pin any watcher (bifrost-ack with the STREAM id,
    not the mailbox short ref -- T063's round-trip gap is still open).
  * If two Sol seats ever run, the same three shared-key organs bite (cursor, expectations,
    worklive) -- the twin diagnosis (twin-seat-misdelivery-diagnosis-2026-07-27.md) is the
    map; slice 1 fixed delivery, the rest is queued (S2-S4).
