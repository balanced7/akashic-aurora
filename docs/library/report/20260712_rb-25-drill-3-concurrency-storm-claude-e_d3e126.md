---
akashic_id: art_20260712_rb-25-drill-3-concurrency-storm-claude-e_d3e126
akashic_sha: 0c4e2df24c34
status: draft
type: report
date: 2026-07-12
title: "RB-25 Drill 3 (CONCURRENCY STORM) -- claude execution record, 2026-07-12"
gist: "# RB-25 Drill 3 (CONCURRENCY STORM) -- claude execution record, 2026-07-12 Runbook split (docs/rb25-exam-runbook-2026-07-11.md): deepseek AU"
tenant: solo
visibility: fleet
seats: []
category: [security, conducting, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea
    rel: cites
  - target: art_20260712_rb-25-drill-3-s3-wedge-root-cause-diagno_d92cb6
    rel: cites
created: "2026-07-12T14:00:22"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-drill-3-concurrency-storm-claude-e_d3e126 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-25 Drill 3 (CONCURRENCY STORM) -- claude execution record, 2026-07-12

# RB-25 Drill 3 (CONCURRENCY STORM) -- claude execution record, 2026-07-12

Runbook split (docs/rb25-exam-runbook-2026-07-11.md): deepseek AUTHORS the burst
(tests/rb25_drill3_burst.py, frozen), claude EXECUTES against a live fleet. This is the
execution half. **GATE = deepseek independent verify (pending; he was offline at run time).**

Storm id `d9b54722`. Isolated namespace `rb25drill3`, throwaway uuid ids, AKASHIC_DRILL_ECHO=1
(canned `[drill-echo]` replies, zero model calls). Live `bifrost` fleet untouched.

> **CORRECTION (2026-07-12, after root-cause): the S3 "backlog wedge" finding below is RETRACTED.**
> Root cause was NOT a backlog-drain bug. During the burst, runner A's reply RateLimiter tripped and
> set a **global pause** (`bifrost:control:paused`, by=d3a, ts=13:32:33), which froze the whole
> fleet -- so S3 and S5 were never actually exercised. A fresh runner drains a dead runner's backlog
> to 0 in ~2s once unpaused (confirmed). Full corrected diagnosis + proposed fixes:
> **research/claude-s3-diagnosis-2026-07-12.md**. Corrected grades: S1/S2/S4 PASS; S3/S5 UNTESTED
> (re-run needed after the control-plane fixes). The original text is kept below verbatim as the
> record of the first-pass (mis)reading.

## How it was run

Executor harness: `tests/rb25_drill3_orchestrate.py` (claude-authored; drives deepseek's frozen
burst UNMODIFIED). One deterministic process: launch 2 echo runners (`d3a`, `d3b`, different ids)
+ 2 twin watchers (`d3w`, same id / 2 sessions); drive the burst via programmatic stdin (feeds the
`--pause-at 20` resume a human would press Enter for); at the pause -- S4 dup-runner probe, hard
`taskkill /F` runner B (no clean release), `runner_lock.clear_if_pid` the corpse; resume -> msgs
21-50 land with B dead; start the successor (same id); wait for drain; dump the evidence bundle.

Artifacts:
- evidence: research/reviewed/rb25-drill3-evidence-d9b54722.json
- send-time ledger (deepseek's burst, pre-seeded): research/reviewed/rb25-drill3-ledger-d9b54722.json
- subprocess logs: research/reviewed/rb25-drill3-logs-d9b54722/

Harness fix landed (environmental, burst NOT edited): the frozen burst prints a U+2713 status char;
a piped child on Windows defaults to cp1252 and crashed on the first send. Fix = force UTF-8 on
children (`PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`). Lesson recorded:
learn:experiment:piped_win_child_needs_utf8.

## Bar readings (execution-side; deepseek grades the gate)

| Bar | Read | Basis |
|-----|------|-------|
| S1 NO UNACKED LOSS | **PASS** | 29 requests: 0 send-side lost, 20 answered, 9 visible-unconsumed, **0 unaccounted**. Nothing vanished silently -- I pulled all "unconsumed" back with one `wait()` (see S3). |
| S2 NO PHANTOM WAKE | **PASS** | Both twin watchers stayed blocked through the 11-trace + 6-steer flood; neither printed DETECTED; both still alive at teardown. SKIP_KINDS held under load. |
| S3 CURSOR PASSES THE CORPSE | **PARTIAL -> FINDING** | Seat handoff MECHANICALLY worked: corpse lock cleared by pid, successor acquired a fresh holder record (gen 2), pid differs, printed online. BUT "its commits succeed" is UNVERIFIED: the successor drained **nothing** (cursor never moved off the corpse position; b_pending stayed 16). See the finding below -- this is the drill's headline. |
| S4 SINGLE CONSUMER HOLDS | **PASS** | A second runner on `d3a`'s id was refused at the seat (exit 3, "another runner is already live ... one runner per agent avoids cursor races"). |
| S5 DUPLICATE DISCIPLINE | **NOT EXERCISED (blocked by S3 finding)** | `handoff` IS in ANSWERABLE (runner L53), so 0 handoff replies is NOT by-design. Both handoffs (seq 36/37) landed in the undrained tail -- handoff-037 sits unconsumed in A's inbox. Dedup couldn't be tested because the handoffs were never answered even once. |

## FINDING (S3-blocking, reproducible): non-virgin runner wedges before consuming

A deepseek runner started against a **non-virgin cursor with a pre-existing backlog consumes
nothing** -- not the backlog, and not even new mail arriving afterward.

Reproduction (after the storm, against the surviving `d3b` backlog of 16, lock free):
1. Start `bifrost_runner_deepseek.py --agent d3b-d9b54722` (echo). -> prints "online ... Waiting
   for messages", then **zero `<- ` consume lines**. `pending` stays **16**.
2. Send one fresh `request` to it. -> `pending` goes **16 -> 17**, still zero consume lines.

Contrast (bus integrity is intact -- the wedge is in the runner loop, NOT the bus):
- `Bus('d3b-...').wait(timeout_ms=1500)` returns all 16 backlog msgs in **0.01s**.
- Virgin-start runners consume fine: the storm's initial `d3a`/`d3b` (empty inbox at boot) answered
  20 requests during active traffic.

So the failure is specific to **starting a consumer against a cursor that is mid-stream with
work behind it** -- exactly the successor-to-a-dead-runner case S3 tests. The live runner `d3a`
shows the same shape at the tail (5 requests + handoff + 2 chats + steer left unconsumed after the
burst went quiescent).

Consume loop = bifrost_runner_deepseek.py:755-816: `bus_guard.beat(bus.probe())` (L756) ->
`bus.wait(1500ms, advance=False, since_out=batch_next)` (L782) -> generation-fenced
`advance_to(generation=lock_gen)` (L804/L815).

Candidate root causes for deepseek to adjudicate (UNVERIFIED -- his authored code, his lane):
1. **Drainer-death guard trips on a backlogged fresh start** -- `bus_guard.beat(bus.probe())` runs
   BEFORE the first `wait()`; a fresh runner with a deep backlog may look like a "dead drainer" and
   get paused. (Would be ironic: the resilience guard blocking recovery.)
2. **Generation/fencing self-block** -- evidence shows `generation_of(token)` returning 0 while the
   holder record carries gen 1/2; if `advance_to(generation=lock_gen)` sees a mismatch it returns
   STALE_GENERATION and the consumer stands down.
3. **Design, not bug** -- in production (non-echo) a fresh runner runs F2 `seed_cursor_at_tail`,
   deliberately SKIPPING the backlog; if so, "cursor passes the corpse" recovers via redelivery
   (RB-26 at-least-once), not by the successor replaying the corpse's cursor -- and S3's wording
   ("its commits succeed") should be re-grounded to whatever the real recovery path is.

## Asks for the verify

1. Grade S1/S2/S4 against the evidence bundle (execution read: PASS).
2. Adjudicate the S3 finding: is the non-virgin-start wedge a real gap in the successor-recovery
   path, a generation/guard bug, or an F2-by-design skip that re-grounds the bar? This decides
   whether drill 3 gates GREEN or spawns a fix slice before T029 can close.
3. With S3 resolved, S5 either gets a re-run (once successors drain) or is explicitly deferred.
4. Confirm the harness (`rb25_drill3_orchestrate.py`) is a faithful executor of your frozen burst.

Engine-first still governs: T029 (RB-25) must close before any packet-substrate BUILD ships.
Drill 4 (72h soak) remains gated on Daniel's soak-gating ruling.
