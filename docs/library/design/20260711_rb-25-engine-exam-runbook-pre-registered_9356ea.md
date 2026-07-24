---
akashic_id: art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea
akashic_sha: cdc69b83be97
status: current
type: design
date: 2026-07-11
title: RB-25 Engine Exam -- runbook + pre-registered evidence bars
gist: "Class: exam-contract (T029 battery sec. RB-25; the gate the UI arc waits behind) PRE-REGISTRATION FENCE (M3): this runbook and every bar in "
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-25-engine-exam-runbook-review-deepsee_3bfc0b
    rel: cites
  - target: art_20260701_newborn-gauntlet-pre-registered-rubric-t_16fdb3
    rel: cites
created: "2026-07-11T21:55:06"
updated: "2026-07-23T21:42:06"
---
<!-- GENERATED PROJECTION of art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# RB-25 Engine Exam -- runbook + pre-registered evidence bars

Class: exam-contract (T029 battery sec. RB-25; the gate the UI arc waits behind)
PRE-REGISTRATION FENCE (M3): this runbook and every bar in it commit BEFORE any drill
runs. Scoring is pass/fail per bar against captured evidence; verdicts append here;
every transcript persists verbatim to research/reviewed/ (M6). Per-drill GATE lines
must cite their record (hook 4 enforces this mechanically now).

Roles: claude conducts + scores; deepseek co-runs -- the examiner never grades its own
performance alone, and the fence reviews this runbook before drill one. Execution split
(review clarification): claude LAUNCHES the newborn process (deepseek operates it via
bus only -- a genuine separate process, never an in-conversation roleplay); deepseek
AUTHORS the storm burst script, claude executes it.

AMENDED 2026-07-11 pre-drill per the fence review (GATE AMBER -> amendments -> drills):
research/reviewed/deepseek-rb25-runbook-review-2026-07-11.md. Load-bearing catch: the
original H3 demanded bidirectional heal resolution; the reconciler is UNIDIRECTIONAL by
design (File is source of truth, store.py reconcile() -- the Redis-ephemeral ruling
T030 affirmed). A drill bar must test the contract the code makes, not one it refuses.

Run order (isolation-driven): NEWBORN (needs pristine acl state) -> HEAL (isolated
stores) -> STORM (fleet chaos, recoverable) -> SOAK (72h tail, starts last and runs
in the background). Daniel's pending scope ruling: whether the UI arc opens at
soak-START (recommended: the soak is passive observation; a failure pauses UI work)
or soak-COMPLETE.

---

## Drill 1 -- NEWBORN ONBOARDING

Rubric: docs/newborn-gauntlet-rubric-2026-07.md (pre-registered 2026-07-10, before the
newborn existed; scored items N1.. live there and are NOT restated here -- one rubric,
one home). Pins: tests/test_newborn_gauntlet.py.
GATE bar: every N-item passes; every gated door the newborn touches refuses with a
TEACHING error (never a stack trace, never silence); the newborn reaches ONE correct
contribution unassisted.

## Drill 2 -- CONCURRENCY STORM

Setup: two wake watchers (twin sessions, one agent id) + two runners (deepseek + a
second runner id), a scripted burst of >= 40 mixed-kind messages (chat/request/trace/
steer interleaved), one runner TASKKILL'd mid-burst (no clean shutdown, no release).

Bars (pass/fail each):
- S1 NO UNACKED LOSS: every directed request sent in the burst is accounted for --
  answered by a live runner, redelivered to the successor (RB-26 at-least-once), or
  visible-unconsumed at storm end. Accounting = a send-time ledger PRE-SEEDED by the
  burst script itself (each id recorded at send, never reconstructed post-hoc). Zero
  silently-vanished messages.
- S2 NO PHANTOM WAKE: "wake" operationally = a watcher process EXIT with detected
  messages printed (exit 0 + the DETECTED block); a watcher that keeps blocking has not
  woken. The trace/steer flood alone never produces such an exit on an idle session
  (P0 SKIP_KINDS discipline under load, not just unit).
- S3 CURSOR PASSES THE CORPSE: after the mid-burst kill, the successor claims (TTL or
  fresh gen), its commits succeed, and the corpse's stale generation is REFUSED at the
  resource if its zombie writes race (L1b under real chaos).
- S4 SINGLE CONSUMER HOLDS: concurrent consume attempts from the twin sessions during
  the burst -- exactly one advances the shared cursor per agent id; every loser gets the
  RB-21 teaching shape (degraded peek, holder named), never silent loss.
- S5 DUPLICATE DISCIPLINE: redelivered handoffs are answered at most once within the
  reply-sent sentinel's TTL window (the sentinel is TTL-bounded -- a redelivery arriving
  AFTER sentinel expiry may legitimately re-answer; that window is the pre-acknowledged
  honest bound, M8, and the drill records it rather than pretending exactly-once is
  unconditional); duplicate chat replies are tolerated and COUNTED, not hidden.

Evidence: the burst script + sent-id ledger, both session transcripts, runner stdout
tails, generation counter reads before/after the kill -- all to research/reviewed/.

## Drill 3 -- STORE-DIVERGENCE HEAL

Setup: force Redis/file divergence twice -- (a) a record missing/differing in REDIS
(File ahead), (b) a record present ONLY in Redis (missing_in_file -- the gap the
contract deliberately does not backfill). Then boot.

Bars (amended per the fence review -- the original H3 demanded bidirectional resolution
the reconciler refuses BY DESIGN; a bar must test the contract the code makes):
- H1 THE HEAL CHOOSES PER CONTRACT: boot completes (no crash, no wedge) and reconcile()
  backfills Redis FROM the File snapshot -- File wins case (a), exactly as
  store.py's documented "Redis reconciled_from File" contract says.
- H2 THE CHOICE IS SAID OUT LOUD: what was backfilled (and counts) is logged/rendered --
  a silent heal fails this bar even if the choice was right.
- H2b THE GAP IS SURFACED HONESTLY: case (b)'s missing_in_file records are REPORTED by
  check_drift() and visibly rendered -- never silently dropped AND never silently
  backfilled into File (the contract refuses Redis->File; the drill proves the refusal
  is loud, not lossy-quiet).
- H4 DURABLE TRACE: the heal leaves a durable record (event/log) an operator can find
  after the fact.

Evidence: the divergence-injection script, pre/post store dumps, boot output, the heal's
durable record.

## Drill 4 -- LONG IDLE SOAK (~72h)

Setup: full system left running with light scheduled traffic (one directed ping to the
runner every 30 min, armed with --expect-reply-within 300 so the sweep itself is under
soak). Checkpoints at T0 / T24 / T48 / T72.

Bars:
- K1 MEMORY BOUNDED: runner + watcher RSS at each checkpoint; fail if either grows
  monotonically beyond +15% of its T0 baseline (named tolerance, M8).
- K2 SEAT HYGIENE: wake seats renew across the window; orphaned seats do not
  accumulate; the janitor/provenance log stays clean of kill-loop shapes.
- K3 RECONNECT UNDER SOAK: one induced Redis restart mid-window -- the runner degrades
  visibly (BusLossGuard), recovers without human touch, and the fleet doctor's read
  goes degraded -> healthy.
- K4 FIREHOSE BOUNDED: the event stream stays within its trim bounds; no consumer
  breaks on eviction.
- K5 TRAFFIC ANSWERED THROUGHOUT: every scheduled ping is answered inside its
  expectation window across all 72h -- zero expectation_dead events from idle drift
  (the RB-29 sweep proves itself over duration). The soak harness INVOKES
  sweep_expectations explicitly on each ping cycle (fence catch: the sweep runs only at
  render -- a 72h harness that never renders would never redrive, and K5 would measure
  nothing).

Evidence: checkpoint table (RSS, seat list, gen counters, funnel reads) appended to the
soak record at each checkpoint; the induced-restart transcript.

---

## VERDICTS (appended per drill after evidence lands -- empty at registration)

(none yet -- registration commit precedes all drills by construction)
