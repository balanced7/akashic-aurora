# RB-25 Engine Exam -- runbook + pre-registered evidence bars

Status: current  (2026-07-11)
Class: exam-contract (T029 battery sec. RB-25; the gate the UI arc waits behind)
PRE-REGISTRATION FENCE (M3): this runbook and every bar in it commit BEFORE any drill
runs. Scoring is pass/fail per bar against captured evidence; verdicts append here;
every transcript persists verbatim to research/reviewed/ (M6). Per-drill GATE lines
must cite their record (hook 4 enforces this mechanically now).

Roles: claude conducts + scores; deepseek co-runs (plays the newborn, starts twin
sessions, drives the storm) -- the examiner never grades its own performance alone,
and the fence reviews this runbook before drill one.

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
  visible-unconsumed at storm end. Accounting = sent-id ledger vs consumed/replied ids.
  Zero silently-vanished messages.
- S2 NO PHANTOM WAKE: the watchers wake ONLY on wake-worthy kinds during the burst --
  the trace/steer flood alone never wakes an idle session (P0 SKIP_KINDS discipline
  under load, not just unit).
- S3 CURSOR PASSES THE CORPSE: after the mid-burst kill, the successor claims (TTL or
  fresh gen), its commits succeed, and the corpse's stale generation is REFUSED at the
  resource if its zombie writes race (L1b under real chaos).
- S4 SINGLE CONSUMER HOLDS: concurrent consume attempts from the twin sessions during
  the burst -- exactly one advances the shared cursor per agent id; every loser gets the
  RB-21 teaching shape (degraded peek, holder named), never silent loss.
- S5 DUPLICATE DISCIPLINE: redelivered handoffs are answered at most once (reply-sent
  sentinel + ack tier); duplicate chat replies are tolerated and COUNTED, not hidden.

Evidence: the burst script + sent-id ledger, both session transcripts, runner stdout
tails, generation counter reads before/after the kill -- all to research/reviewed/.

## Drill 3 -- STORE-DIVERGENCE HEAL

Setup: force Redis/file divergence twice -- (a) a decision record (notes) differing
between backends, (b) task-ledger state differing. Then boot.

Bars:
- H1 THE HEAL CHOOSES: boot completes (no crash, no wedge) and the reconciler picks a
  side for each divergence.
- H2 THE CHOICE IS SAID OUT LOUD: which side won and WHY is logged/rendered -- a silent
  heal fails this bar even if the choice was right.
- H3 THE CHOICE IS CORRECT per the documented dual-write precedence (the contract
  tests/test_sync_reconciler.py pins); the drill uses one case where Redis is right and
  one where the file side is right -- both must resolve correctly, so "always trust one
  side" cannot pass by accident.
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
  (the RB-29 sweep proves itself over duration).

Evidence: checkpoint table (RSS, seat list, gen counters, funnel reads) appended to the
soak record at each checkpoint; the induced-restart transcript.

---

## VERDICTS (appended per drill after evidence lands -- empty at registration)

(none yet -- registration commit precedes all drills by construction)
