---
akashic_id: art_20260711_rb-25-engine-exam-runbook-review-deepsee_3bfc0b
akashic_sha: 535e8986b427
status: current
type: report
date: 2026-07-11
title: "RB-25 Engine Exam -- Runbook Review (deepseek, fenced pre-drill)"
gist: "Class: review (gate: the fence reviewing the runbook before drill one) Source: docs/rb25-exam-runbook-2026-07-11.md @HEAD (commit 80dc64a) C"
tenant: solo
visibility: fleet
seats: []
category: [bus, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea
    rel: cites
created: "2026-07-12T02:20:42"
updated: "2026-07-23T21:42:15"
---
<!-- GENERATED PROJECTION of art_20260711_rb-25-engine-exam-runbook-review-deepsee_3bfc0b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# RB-25 Engine Exam -- Runbook Review (deepseek, fenced pre-drill)

Class: review (gate: the fence reviewing the runbook before drill one)
Source: docs/rb25-exam-runbook-2026-07-11.md @HEAD (commit 80dc64a)
Contract: M3 pre-registration fence -- amendments before drill one ARE the fence working.

## Verdict summary (bus line)

GATE: AMBER -- PASS AFTER 6 AMENDMENTS (zero bar removals; 1 new bar H2b, 2 clarifications
A1+A2, 1 tolerance tightened A3, 1 full rewrite A4, 1 clarification A6). The runbook is
honest, falsifiable, and correctly structured.
The findings below are the fence at work; none should delay the drill.

---

## 1. STORM BARS S1-S5 -- falsifiability + sufficiency review

### S1 (NO UNACKED LOSS) -- PASS, with one clarification

Falsifiable: a sent-id ledger vs consumed/replied ids is deterministic and auditable.
The three acceptable categories (answered / redelivered / visible-unconsumed) are
exhaustive and mutually exclusive. Zero silently-vanished messages is the claim.

**Minor gap**: the sent-id ledger must be seeded BEFORE the burst starts (not inferred
from stream contents afterward). The runbook should specify: "Accounting = a
pre-seeded sent-id ledger (the burst script records every send's msg id), compared
against consumed/replied ids at storm end."

**AMENDMENT 1** (S1): Add one sentence: "The burst script MUST record every sent
message id AT SEND TIME (pre-seeded ledger); post-hoc reconstruction from stream
contents is not acceptable accounting."

### S2 (NO PHANTOM WAKE) -- PASS, falsifiable

The claim "trace/steer flood alone never wakes an idle session" is testable with
precise definitions: a "wake" = the watcher process fires its callback (exits with a
non-skip code, or prints a wake line). The mixed-kind burst naturally exercises
SKIP_KINDS under load.

**Minor gap**: "wake" needs an operational definition in the evidence section. What
constitutes a phantom wake — the watcher exiting nonzero? Printing a "wake firing"
line? Firing the callback? State this explicitly so the scorer can't move the
goalposts.

**AMENDMENT 2** (S2): Add: "Evidence: watcher stdout/stderr captured; a 'wake' for
scoring purposes = the watcher printing its wake-firing line OR invoking its callback
(NOT mere idle-poll exits). Every such wake during the burst must be attributable to a
wake-worthy kind in the sent-id ledger."

### S3 (CURSOR PASSES THE CORPSE) -- PASS, fully falsifiable + sufficient

Good. The mid-burst TASKKILL of a runner, followed by a successor claiming (TTL or
fresh gen), and the zombie's stale generation REFUSED at the resource — this directly
exercises L1b (fencing generation in `advance_to` Lua, `core/comm/bus.py:440-467`).
The "commits succeed" and "STALE_GENERATION refusal" claims are both observable from
runner stdout and generation counter reads.

**Sufficiency**: the TASKKILL creates a genuine unclean death (no release, no cleanup),
which is the exact L1b scenario. The successor's claim path goes through
`runner_lock.acquire` → INCR generation → `advance_to(generation=new_gen)` — the
zombie's stale generation being REFUSED at the resource is the Kleppmann fence
validated live. Good.

**Clarification gap**: "one runner TASKKILL'd" — which runner? The setup specifies
"two runners (deepseek + a second runner id)." The bar should specify whether the
killed runner is the one DEEPSEEK drives or the OTHER runner. Since deepseek "drives
the storm," it should likely be the OTHER runner killed (so deepseek's runner remains
alive to observe and score). But this is a drill-execution detail, not a bar defect.

### S4 (SINGLE CONSUMER HOLDS) -- PASS, fully falsifiable + sufficient

Exercises RB-21 directly: twin sessions (same agent id) both attempt consume; exactly
one advances the cursor; the loser gets the teaching shape. This is the exact scenario
RB-21 was built for (`claim_consumer` → refused → degraded peek,
`core/comm/runner_lock.py:181-198`).

**Sufficiency**: the "concurrent consume attempts" under the message burst means the
twin sessions are racing while mail is landing — the realest possible test of the
RB-21 claim-or-degrade path.

### S5 (DUPLICATE DISCIPLINE) -- PASS, with a documentation note

Exercises RB-26's dedup: `reply_sent:<msg_id>` sentinel (set after bus.send, before
cursor advance; `core/comm/bus.py` L1 build spec) for handoffs; chat duplicates
tolerated and COUNTED. Falsifiable: count duplicates; handoff duplicates must be 0 or
1 at most; chat duplicates tolerated but enumerated.

**Note**: the bar says "redelivered handoffs are answered at most once." The current
dedup sentinel TTL is REPLY_TIMEOUT_SEC+60. If a redelivery arrives AFTER the sentinel
expires, the handoff would be answered again. This is an honest bound (named in the L1
build spec: "past the sentinel's TTL the sender has long moved on") but the bar should
acknowledge it — a handoff redelivered at T+700s when REPLY_TIMEOUT_SEC=600 would get
a duplicate answer, and that's BY DESIGN. The bar as written ("at most once") is too
absolute. Amend to: "at most once within the sentinel TTL window; duplicates beyond
the TTL are counted and the window is named."

**AMENDMENT 3** (S5): Add: "The sentinel TTL is REPLY_TIMEOUT_SEC+60; a duplicate
handoff reply beyond this window is counted (named honest bound), not a bar failure.
Evidence records the window size alongside the duplicate count."

### S1-S5 combined sufficiency verdict: PASS

The >=40 mixed-kind message burst with mid-burst TASKKILL exercises L1b (S3 generation
fencing), RB-21 (S4 consumer contention), and RB-26 (S1/S5 redelivery+dedup) in a
single integrated chaos scenario. The mixed kinds ensure S2's SKIP_KINDS is tested
under load. The design is tight — no superfluous bars, no unfalsifiable claims.

---

## 2. HEAL BARS H1-H4 -- H3 contract mismatch (CRITICAL FINDING)

### H1 (THE HEAL CHOOSES) -- PASS

The reconciler runs at boot (`agent_cli.py:165-171`): `check_drift()` → if
`missing_in_redis` is non-empty → `reconcile()`. If there's no divergence, it's a
no-op. If Redis is down, `reconcile()` returns `{"status": "skipped"}`. Boot completes
in all cases. Falsifiable: inject divergence, verify boot completes without crash or
wedge.

### H2 (THE CHOICE IS SAID OUT LOUD) -- PASS (needs evidence capture discipline)

The boot path prints `[boot] healed Redis divergence: backfilled X key-structures from
File (Redis was behind)` to stderr. This names the direction (File→Redis), the scope
(N key-structures), and says it out loud. The evidence capture must include boot
stderr.

If `missing_in_file` is non-empty (keys in Redis but not in File), the current code
reports it in `check_drift()`'s return value but does NOT act on it and does NOT print
a boot line about it. The boot path only triggers on `missing_in_redis`. So "the choice
is said out loud" currently only fires in one direction. This is correct behavior given
the contract (see H3), but the bar should acknowledge: the loud line fires for
File→Redis divergence; Redis→File divergence is reported by `check_drift()` but NOT
healed and NOT printed at boot.

### H3 (THE CHOICE IS CORRECT) -- FAILS AS WRITTEN; AMENDMENT REQUIRED

**THE FINDING**: H3 demands "one case where Redis is right and one where the file side
is right — both must resolve correctly, so 'always trust one side' cannot pass by
accident."

The reconciler (`core/foundation/store.py:789-850`) is **unidirectional: File ALWAYS
wins**. The docstring is explicit:

- `check_drift()` (line 793): "File is the source of truth, so 'missing_in_redis' is
  the set Redis must be backfilled with (the usual case after Redis was down during
  writes)."
- `reconcile()` (line 816): "Heal divergence by backfilling Redis from the durable File
  snapshot. Semantic Relationship: Redis reconciled_from File (File is source of truth)"

The `missing_in_file` set is COMPUTED by `check_drift()` and returned in the drift
report (transparency), but `reconcile()` NEVER acts on it. Reconciliation ALWAYS
blasts File→Redis. There is no code path where Redis data is written back to File.

The tests confirm this (`tests/test_sync_reconciler.py`):
- `test_reconcile_redis_down`: safe no-op when Redis is down
- `test_reconcile_backfill_if_redis`: File→Redis backfill only
- There is NO test for Redis→File direction, because there is NO implementation for it.

**H3 as written is IMPOSSIBLE under the current contract.** "Both must resolve
correctly" demands a Redis-wins path that does not exist.

This is the fence working — the bar caught a mismatch between the runbook's assumption
and the code's contract. The question is: does the contract need to change, or does the
bar?

**Analysis of the dual-write precedence**: The project's write path goes through
HybridStore, which writes to File first (durable), then Redis (ephemeral). If Redis is
down during a write, File has the data and Redis doesn't — the "missing_in_redis" case,
which reconcile handles correctly. If File is corrupted or lost, Redis might have more
recent data — but the system was designed with File as the durable source of truth.
Redis is explicitly ephemeral (T030 design review AFFIRMED, "Redis-ephemeral"). The
"Redis is right" scenario (Redis has data File doesn't) can only happen through
out-of-band Redis writes or File corruption — both are outside the designed failure
model.

**Recommendation**: H3 must be amended to match the ACTUAL contract. Do not add a
Redis→File backfill path (that would contradict the "File is source of truth" design
and the Redis-ephemeral ruling). Instead:

**AMENDMENT 4** (H3): Replace the current text with:

> H3 THE CHOICE IS CORRECT per the documented dual-write precedence (the contract
> `tests/test_sync_reconciler.py` pins): File is the source of truth; reconciliation
> backfills Redis from File. The drill uses ONE case where File is ahead (Redis
> missing keys — backfill succeeds) and ONE case where Redis has keys File doesn't
> (the `missing_in_file` set is reported honestly by `check_drift`, the gap is
> surfaced, reconciliation does NOT overwrite File — it correctly leaves
> File-absent keys alone). Both cases must resolve as the contract specifies: the
> first heals, the second reports the gap without corrupting File. "Always trust one
> side" is the DESIGN, not an accident — verify it holds correctly.

This also introduces an **AMENDMENT 5** (NEW BAR H2b):

> H2b THE GAP IS SURFACED: when `missing_in_file` is non-empty (Redis has keys absent
> from File), `check_drift()` reports them. The evidence must show the drift report
> with `missing_in_file` populated, and the operator can see it. Boot does not
> silently continue with invisible divergence.

### H4 (DURABLE TRACE) -- CONDITIONAL PASS

The reconcile path prints to stderr (boot output): `[boot] healed Redis divergence:
backfilled X key-structures from File (Redis was behind)`. This is NOT a durable event
(no `capture_event` call, no event log entry). It's a console line.

For the drill: the evidence capture includes "boot output" and "the heal's durable
record." If the drill transcript captures boot stderr, the trace is "durable" within
the evidence archive. But an operator after the fact (beyond the drill) has no
persistent record of the heal — the console line scrolls away.

This is an honest bound of the current implementation. I recommend:
- For the drill: the evidence capture (boot transcript) IS the durable record.
  Acceptable for a drill — the bar is satisfied by the evidence protocol.
- Post-drill: consider adding a `capture_event("store_reconciled", ...)` call in the
  reconcile path so the heal leaves a durable event log entry. But this is a separate
  improvement, not a bar amendment.

**H4 passes as-is for the drill, with the note that "durable record" = the captured
boot transcript in the evidence package.**

---

## 3. SOAK BARS K1-K5 -- tolerance honesty

### K1 (MEMORY BOUNDED) -- PASS, honest tolerance

+15% of T0 baseline, monotonic growth beyond that fails. Named tolerance (M8). The
"monotonically" qualifier is important — a spike that recedes is not a failure; a
creeping leak that never drops is. Good.

### K2 (SEAT HYGIENE) -- PASS, falsifiable

Wake seats renew, no orphan accumulation, janitor log clean of kill-loop shapes. The
janitor (Wave 2, `core/comm/wake_seat.py`) has a provenance log; checking it for
kill-loop shapes (rapid reap/re-arm cycles) is a concrete check.

### K3 (RECONNECT UNDER SOAK) -- PASS, with dependency note

Induced Redis restart → runner degrades visibly (BusLossGuard) → recovers without
human touch → fleet doctor read goes degraded→healthy.

The fleet doctor (`core/comm/doctor.py`) is SHIPPED (L2/RB-27b, commit history
confirms). The doctor reads `BusLossGuard` state via the liveness probes. This bar is
testable with current code.

**Minor concern**: "degraded visibly" — what is "visibly"? The runner's own output?
The doctor's read? The UI? Specify: "the runner logs BusLossGuard degradation; the
fleet doctor's read for this agent shows degraded state; after Redis recovers, the
doctor's read returns to healthy without human intervention."

### K4 (FIREHOSE BOUNDED) -- PASS, testable

The canonical firehose has `CANONICAL_MAXLEN` (`core/events/event_log.py:43`). The bar
is: the stream stays within trim bounds; no consumer breaks on eviction. Testable by
inspecting stream length after 72h and verifying consumers don't error on missing
entries.

### K5 (TRAFFIC ANSWERED THROUGHOUT) -- PASS, honest budget

One directed ping every 30 min, armed with `--expect-reply-within 300`, across 72h =
~144 pings. With REDRIVES=3, each ping can retry up to 3 times before exhaustion
(~15 min of tail per ping worst case). The sweep runs at render time (boot /
bifrost-sync), NOT on a fixed schedule daemon — so the sweep is as frequent as the
sender checks in.

Budget analysis:
- 144 pings × (1 + 3 redrives) = 576 max sends across 72h
- Each send is a single Redis command; each sweep is a few Redis reads
- The runner's loop processes at most 144 real messages across 72h
- Memory is the real concern (K1), not CPU or Redis load

The 300s window is generous — in a 72h window with a healthy runner, every ping should
be answered in well under 300s. The bar claims "zero expectation_dead events from idle
drift." This is honest: expectation_dead fires when all REDRIVES are exhausted (~900s
of cumulative deadline with REDRIVES=3 × 300s each if deadlines cascade). If the
runner is truly idle and healthy, no ping should take >900s to answer.

**One concern**: the runbook says "the RB-29 sweep proves itself over duration." RB-29
sweep runs at render (boot / bifrost-sync). If the runner being soaked does NOT
regularly boot or bifrost-sync during the 72h, the sweep never runs, deadlines are
never evaluated, and pings appear unanswered not because the runner is dead but because
the sender never checked. The soak setup must ensure the sender (or the runner itself)
calls bifrost-sync or boots at regular intervals, OR the soak script must invoke the
sweep explicitly.

**AMENDMENT 6** (K5): Add: "The soak harness MUST invoke sweep_expectations (via
bifrost-sync or an explicit sweep call) at least every 30 min — without this, the
deadline evaluator never runs and expectation_dead events are a harness defect, not a
system failure."

---

## 4. RUN ORDER + ROLES -- review

### Run order (isolation-driven): NEWBORN → HEAL → STORM → SOAK

This ordering is correct:
- NEWBORN first: pristine ACL state (no prior knowledge of `newborn-gauntlet-1`)
- HEAL second: isolated stores (divergence injection touches Redis + File; doesn't
  interfere with other drills)
- STORM third: fleet chaos that's recoverable — if it leaves artifacts, SOAK hasn't
  started yet. The storm's cleanup at end ensures a clean fleet for SOAK.
- SOAK last: 72h background — starts after all destructive drills complete

### Roles

"claude conducts + scores; deepseek co-runs (plays the newborn, starts twin sessions,
drives the storm)"

My role is clear but has execution gaps:

**NEWBORN**: The previous drill (2026-07-10) diverged because deepseek roleplayed
within its own runner instead of launching a real `newborn-gauntlet-1` process. The
re-run MUST use a genuine separate runner process. Who launches it? I can write the
launch command, but the ACTUAL process launch may need to be done by claude (since I
can't execute shell freely, and the newborn MUST be a different process from my own
runner). Clarify: "claude launches the newborn runner process; deepseek operates it via
the bus — the newborn runner is deepseek's model but a SEPARATE process under a
different agent id."

**STORM**: "deepseek drives the storm." This means I write the burst script, the
sent-id ledger, and direct the TASKKILL timing. Claude executes the script (since
shell execution is gated). Clarify in the runbook: "deepseek authors the burst script
+ ledger; claude executes it; deepseek observes and records from its runner's
perspective."

**Twin sessions**: "deepseek starts twin sessions." This means I initiate two session
processes for the same agent id. The "second runner id" in the setup is separate from
the twin sessions (twin sessions share one agent id; the two runners are two different
agent ids). The runbook should distinguish: "two wake watchers (twin sessions, one
agent id) + two runners (different agent ids, e.g. claude + a drill-runner)."

### Daniel's scope ruling (SOAK start gate)

The runbook notes this is pending: "whether the UI arc opens at soak-START (recommended
... a failure pauses UI work) or soak-COMPLETE." My recommendation aligns with the
runbook's lean: start UI work at soak-START with the understanding that a soak failure
pauses (not reverts) the UI arc. The soak is passive observation; waiting 72h of idle
before opening the UI arc is unnecessary — the soak's job is to catch a long-horizon
leak, and if one exists, the UI work is paused, not thrown away.

---

## 5. AMENDMENTS REGISTER (summary)

| # | Bar | Type | Change |
|---|-----|------|--------|
| A1 | S1 | Clarification | Pre-seeded sent-id ledger (record at send time, not post-hoc) |
| A2 | S2 | Clarification | Operational definition of "wake" for scoring |
| A3 | S5 | Honest-bound | Sentinel TTL window named; duplicate beyond TTL = counted, not fail |
| A4 | H3 | CONTRACT (critical) | Replaced: File is source of truth; missing_in_file gap is surfaced, not healed |
| A5 | H2b | NEW BAR | missing_in_file is reported by check_drift; the gap is operator-visible |
| A6 | K5 | Harness | sweep_expectations must be invoked regularly by the soak harness |

Zero bar removals. One new bar (H2b). H3 rewritten to match the actual code contract.

---

## 6. GATE VERDICT

**AMBER — PASS AFTER AMENDMENTS A1-A6 APPLIED.**

The runbook is well-structured, every bar is falsifiable or becomes so with the
amendments above, and the combined storm scenario correctly exercises L1b + RB-21 +
RB-26 in an integrated chaos drill. H3 was the load-bearing find — the fence caught a
contract mismatch that would have produced a false FAIL (the bar demands behavior the
code explicitly does not implement, by design). Amending the bar to match the design is
the correct resolution; adding a Redis→File backfill would contradict the
Redis-ephemeral ruling affirmed in T030 design review.

The drill can proceed once these amendments land in the runbook. I am ready to co-run
my roles (newborn player, twin-session starter, storm driver) on claude's signal.
