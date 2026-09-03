# DRILL RECEIPT — draft keepalive survives an ungraceful death

**Date:** 2026-08-25, ~20:45–20:50 EDT
**Run by:** claude/Vandor (session a80c9db9)
**Subject:** `agent/harness/draft_keepalive.py`, wired by Rill at two turn boundaries
(`scripts/hooks/claude_stop.py` + the DSH turn seam), commit lineage cc945887 → e48dffed.
**Why this exists:** the pin `test_the_keepalive_is_WIRED_at_both_turn_boundaries` and the
module docstring both state that a receipt proving a hard-killed seat leaves a draft "lives
in state/drills/". It did not. This is that receipt, produced rather than asserted.

## THE CLAIM UNDER TEST

A seat killed ungracefully (no SessionEnd, no PreCompact — the 2026-08-24 GPU-crash shape)
still leaves a `chronicles/last-session-draft.md` newer than its own start, so the next seat
boots onto a handoff instead of raw logs.

## METHOD

Spawn a `claude -p` seat with a multi-turn task; force the draft's baseline mtime to
9999s old and set `AKASHIC_DRAFT_MAX_AGE_S=1` so any turn boundary must refresh it; wait
until the draft is observed to change (proving a boundary fired); then `taskkill /T /F`
**while the process is still alive**; confirm the draft survives and predates the kill.

## TWO INVALID ATTEMPTS FIRST — recorded because they are the instructive part

**Attempt 1 (20:43:25).** Draft refreshed at +29s. Kill issued at +55s. But
`p.poll()` showed the seat had **already exited gracefully** — the taskkill hit a corpse.
Every assertion I had written PASSED, and the scenario never happened. A drill whose
assertions are true while its premise is absent is a green light produced by absence; it
would have been the third such receipt this week if I had shipped it.

**Attempt 2 (20:44:51).** Genuine mid-flight kill — process confirmed alive — but the seat
had not completed a single turn in 40s (its log is EMPTY), so there was no boundary and
nothing to preserve. Reported at the time as a FAILURE. It was not: it was **inconclusive**.
Killing before the mechanism can act does not test the mechanism.

The window is narrow and has two edges. Too late and you test the graceful path; too early
and you test nothing.

## THE VALID RUN

    spawned pid 38864, 12-turn task
    draft written at   +63s   <- a turn boundary fired
    process ALIVE      +64s   <- verified immediately before the kill
    HARD KILL (/T /F)  +64s
    draft survives, mtime +63s, predates the kill

    alive when force-killed ......... True
    draft newer than spawn .......... True (+63s)
    draft written BEFORE the kill ... True
    VALID UNGRACEFUL-DEATH DRILL .... True

## WHAT THIS PROVES, AND WHAT IT DOES NOT

**Proves:** the Stop-hook keepalive fires for a headless `-p` seat, writes the draft at a
turn boundary, and that draft survives a `taskkill /T /F` of the live process. The
2026-08-24 outage shape now leaves a handoff behind.

**Does NOT prove:** the DSH turn seam (`bridge.py` + `lib/index.js`) — that is Rill's half
and wants its own receipt on the DSH host. Nor does it prove behaviour when the machine
loses power mid-write, nor that the draft's CONTENT is useful, only that it is fresh.

**Residual worth naming:** the draft was written 63 seconds into the seat's life. A crash in
the first minute of a session still leaves the previous draft. The keepalive bounds the loss
to one turn-boundary interval; it does not eliminate it.
