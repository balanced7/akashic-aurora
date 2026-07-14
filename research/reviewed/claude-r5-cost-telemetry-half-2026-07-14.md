# R5 Cost Telemetry — claude design half (BLIND, 2026-07-14)

Status: current (2026-07-14)
Class: full-fence design half per research/r5-cost-telemetry-design-brief-2026-07-14.md.
Written BLIND: deepseek's half unread at commit time (M1). Tags per M1-CF.

## The central move: READ-side join, zero write-path changes

The brief tiered this slice full-fence because "the join stamps the TASK LEDGER's write
path." My half REFUTES the premise that any stamp is needed:

- turn_metrics already RECORDS every turn's facts {ts, agent, ask_kind, duration_s,
  progress_points, tool_count, outcome, tokens?} to a capped Redis list AND a
  "best-effort firehose event (durable analytics tail; never on the hot path)"
  (CERTAIN: core/comm/turn_metrics.py module docstring + record()).
- The ledger's OWN transition events already timestamp every claim/start/done
  (CERTAIN: T023 ledger_update events; the task record carries transition history).
- Therefore a task's cost window = [claim_ts, done_ts] DERIVED at render time, and its
  cost = an aggregation query over the DURABLE firehose rows inside that window.
  New code = one query + one render line. The ledger write path is untouched; the
  Redis capped list is not even read (the firehose is the durable source of truth).

Consequence for the tier: the build as designed here would be FENCE-LITE by the gate
(render-only, no coordination-primitive writes). The fence already ran full — fine
(over-fencing once costs a fence, under-fencing costs an incident); the reconciliation
should RECORD the resolved tier for the build slice. (DESIGN)

## (a) WHAT — and the attribution refusal

Cost of a task = the FLEET's measured activity during the task's active window:
  turns (row count) | wall duration (sum duration_s) | tool calls (sum tool_count) |
  tokens (sum where present) | commits in window (git log --since/--until count).
ATTRIBUTION IS REFUSED, LOUDLY (DESIGN): under concurrent agents and shared work
(a fence review serves two tasks at once), any per-task or per-agent split is
fabricated precision. The render says "window cost (fleet, shared)" — a true number
honestly labeled, never a false number precisely split. This is the brief's tension
(a) answered by refusal, per M8 honest bounds.
Token coverage is UNCERTAIN (tokens is Optional in record(); populated only where the
runner passes it) — the render shows tokens only when >=80% of window rows carry them,
else "(tokens: partial telemetry)". Measure coverage at build.

## (b) WHEN — no stamps

No new writes at any transition. The window derives from existing transition
timestamps at RENDER time. Tasks re-opened (verifying -> in_progress bounce) use the
FIRST claim and the LAST done (the full arc). (CERTAIN: transitions are recorded;
DESIGN: the window rule.)

## (c) RENDER

`task list --costs` (opt-in flag; default render unchanged — packet law, no new
standing bytes) adds ONE line under each DONE/VERIFYING task:
  cost: 2.1h window | 84 turns | 412 tool-calls | ~156k tokens (fleet, shared window)
The wrap-time arc scorecard (M-practice) gains the same line per arc — that is where
Daniel reads ROI. No live tasks ever render cost (see (f)). (DESIGN)

## (d) BACKFILL

As far as the firehose goes: the events tail is durable and time-indexed, so any past
task whose window falls inside firehose history renders a real cost. Absent telemetry
renders "cost: (no telemetry in window)" — never a fabricated zero. (CERTAIN on the
firehose durability claim — the turn_metrics docstring names it; verify depth at build.)

## (e) FAILURE modes

- Capped-list reset / counter rollover: IRRELEVANT by construction — windowed queries
  over durable events, not counter deltas. (This is the design's quiet win.)
- Runner restarts mid-task: irrelevant, same reason.
- Firehose gaps (Redis-down stretches where best-effort rows dropped): the render
  computes covered-fraction from row density vs window length heuristically? NO —
  fabricated precision again. Simpler honesty: if the FILE-side event log has zero
  rows for a >10min stretch inside the window, append "(partial telemetry)". (DESIGN)
- Clock: all timestamps from one source family (event log ts) — no cross-source skew.

## (f) GOODHART guard

1. Costs render ONLY for done/verifying tasks — a live task never shows a number, so
   pace pressure has no surface (never codify pace).
2. No per-agent split in v1 — you cannot score what is not split (the strongest guard).
3. The label "(fleet, shared window)" makes the number an ROI read, not a performance
   read, every time it appears.
4. The wrap scorecard is the intended consumer; `--costs` is opt-in for Daniel's
   deliberate reading, never ambient. (DESIGN)

## Refuted candidates (refute-first, own half)

1. COUNTER SNAPSHOTS stamped on the task record at transitions — REFUTED: the counters
   live in capped ephemeral lists (reset breaks deltas, retention breaks backfill);
   stamps add coordination-primitive write surface for data the firehose already holds
   durably; two sources of truth drift.
2. PER-AGENT ATTRIBUTION — REFUTED above (fabricated precision + Goodhart squared).
3. LIVE COST ON ACTIVE TASKS — REFUTED: pace-scoring pressure; also mid-window numbers
   are always partial and would train readers to distrust the final ones.
4. NEW METRICS PIPELINE (dedicated cost recorder) — REFUTED: the recorder lesson
   (renew_two_birds_bus_recorder) says add readers at existing seams, never new
   hot-path writers; turn_metrics already writes everything needed.

## Build shape (for the reconciliation, not binding)

core/coord/task_costs.py (window derivation + firehose aggregation + render line;
READ-only) -> task list --costs flag -> wrap scorecard line. Pins: window derivation
(first-claim/last-done), attribution label always present, absent-telemetry honesty,
live-task refusal, opt-in default-off. Tier for the build: FENCE-LITE (render-only)
-- reviewer confirms.
