---
akashic_id: art_20260720_recovery-arc-deepseek-s-blank-slate-half_c69bb3
akashic_sha: ab22b7a0fbee
status: current
type: report
date: 2026-07-20
title: "Recovery Arc — deepseek's blank-slate half (VERBATIM)"
gist: "Captured verbatim from the live bus (research-full-fidelity rule); no edits. --- RECOVERY ARC — deepseek blank-slate half (independent, T038"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, coordination]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_research-detour-actor-otp-ros-stigmergy_988017
    rel: cites
created: "2026-07-20T22:32:50"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260720_recovery-arc-deepseek-s-blank-slate-half_c69bb3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Recovery Arc — deepseek's blank-slate half (VERBATIM)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

RECOVERY ARC — deepseek blank-slate half (independent, T038 precedent honored — no coordination)

## Q1: BLANK-SLATE FAULT-HANDLING DESIGN

### Architecture: three layers on one spine

The existing L0→L4 stack is already an Erlang-ish supervisor tree (docs/architecture-research-actor-ros-stigmergy-2026-07.md called this correctly). The gap is NOT detection (doctor.py grades findings; P-S1-0 + P-S1-5 just closed the C1-8 visibility hole) and NOT durability (dual-write + snapshots + boot heal hold). The gap is: **the detect→decide→act loop is OPEN, isolation bulkheads are missing, and storms require manual surgery.**

My design adds three layers to close it:

---

### (a) ISOLATION — Bulkheads

Three bulkheads, ordered by pain (tonight's receipts):

**BULKHEAD-0: Stale-mail auto-triage** (S, FLOOR, no deps)
The consume path separates D2-stale asks from fresh mail. An inbox entry older than `STALE_ASK_THRESHOLD_S` (default: 4h, env-configurable) is moved to a `triage:<agent>` Redis list BEFORE the consumer processes it, advancing the work cursor past it. Fresh mail flows immediately — the 19-21 stale asks (43-96h) clogging my cursor tonight would auto-triage, freeing fence questions in one drain cycle. Triage lane is consumed during idle (after work lane drains to zero). Every skip writes a `triage_skip` audit event. Zero behavior change for fresh mail. DIRECTLY fixes W23.

**BULKHEAD-1: Progress-bound presence TTL** (S, FLOOR, deps: none)
Today presence TTL is a flat 90s heartbeat. A hung runner (dead pulse, alive daemon heartbeat) holds presence for the full TTL. Fix: presence TTL is the MIN of the configured TTL and `progress_age * 2` when the pulse is dead. A hung runner's presence evaporates faster (dead pulse for 60s → presence TTL = 120s, then falls). The successor seat can claim earlier. The C1-1 evidence ladder already handles ambiguity correctly (resolve toward ALIVE); this just accelerates the TTL decay, making the ladder's job shorter.

**BULKHEAD-2: Lane convergence — single cursor** (L, FLOOR, deps: T047 prep)
The dual-cursor regime (work lane cursor ≠ legacy cursor) caused tonight's watcher insta-fire loop (wake_watcher_insta_fires_lane_divergence) and every T066 straggler storm. One consumer = one cursor. The T047 retirement is the vehicle; this bulkhead formalizes it as a structural isolation requirement: lane divergence IS a fault class, not an operational quirk.

---

### (b) AUTOMATIC RECOVERY — The closed loop

**SUPERVISOR-0: Close the detect→decide→act loop** (M, FLOOR, deps: BULKHEAD-0)

A supervisor tick (daemon thread or launcher poll, ~30s) reads `doctor.examine_fleet()` and acts on graded findings. Every action is EVIDENCE-GATED, GRADUATED, and AUDITED — the C1-8 false-kill lesson is the design's immune system:

**Decision matrix:**
| Finding | Evidence required | Action | Rung |
|---------|-------------------|--------|------|
| hard_wedge | dead pulse + non-idle + age > 300s + generation check | auto-revive | 3 |
| stalled_consumer | backlog > 5 + age > hysteresis + lane-depth confirm | auto-nudge → escalate to skip-to-now | 1→4 |
| approaching_wedge | dead pulse + non-idle + age in [150,300) + climbing | escalate to page at 300s boundary | observe |
| self_reported_error | trigger:reason confession present | auto-redrive the unanswered ask | 2 |
| lane_depth_spike | depth > threshold (50) + 2 consecutive samples | auto-pause → triage → resume | 4 |
| runner_down | daemon presence held, runner absent | auto-redrive unanswered asks to peer | 2 |

**Graduated rungs** (never sharp first — T097 C4):
1. **NUDGE** — steer to the agent: "you have N unread / you appear stuck in X / reply in 120s or I escalate." Zero risk; a busy agent folds it, a wedged one cannot.
2. **PROBE** — steer with deadline: "confirm liveness — emit within 120s or auto-revive begins." Still steer-only.
3. **REVIVE** — launcher.revive() with full evidence packet. Requires: dead pulse + non-idle + age > threshold + generation fencing (stale generation replies rejected).
4. **REDRIVE** — re-queue the unanswered ask (to sender or available peer). Requires: original ask was unanswered beyond REPLY_TIMEOUT_SEC * 3, generation fencing, dedup guard.

**Safety rails** (every auto-action must survive adversarial review):
- **Evidence ladder BEFORE action** (T097 C4, verbatim): runner self-confession > progress-age > boot disqualifier > lane depth > presence. Calling-seat conviction is inadmissible.
- **Second-observer concurrence** for sharp rungs (3-4): another agent's doctor reading must confirm the same evidence before revive/redrive fires. Prevents single-observer hallucination.
- **Generation fencing:** every revive bumps the lock generation; stale replies from the old generation are rejected at the commit gate (runner_lock already has this).
- **Rate cap:** 3 revives per agent per session; exceed = stop and flag Daniel. Per the T097 reconciliation: "a revive without an evidence packet is C1-8 with permissions."
- **Cooldown:** minimum 120s between auto-revives of the same agent.
- **First-ever kill of any target** requires human approval (T097 D2). Subsequent auto-revives of the same target use the evidence ladder without re-approval.
- **Opt-out, not opt-in:** L3b auto_revive moves from default-OFF to default-ON with the rails above. An agent can still `launcher.revive_disarm` to go observe-only.
- **Every auto-action writes a durable `supervisor_action` event** carrying rung, evidence refs, second-observer id, generation, and outcome.

---

### (c) DATA RECOVERY — Converge-after-replay

The substrate largely holds (Git, snapshots, dual-write, boot heal, File-is-truth). Three additions:

**DATA-0: Pre-revive snapshot** (S, FLOOR, deps: SUPERVISOR-0)
Before any auto-revive, snapshot the agent's working state: uncommitted file changes (git diff), current conversation state, un-acked inbox entries. The snapshot is timestamped and kept for 7 days. If the revive itself causes data loss, the snapshot is the revert path. Uses existing `scripts/snapshot_knowledge.py` pattern but scoped to one agent's in-flight state.

**DATA-1: Mid-surgery file preservation** (S, FLOOR, deps: SUPERVISOR-0)
If an auto-revive fires while the agent has uncommitted working-tree changes (git status --porcelain), the changes are auto-stashed (git stash push -m "auto-revive-<agent>-<ts>") before the revive. The revived agent sees a boot message: "You had uncommitted changes at revive time — stashed as 'auto-revive-<agent>-<ts>'. git stash pop to recover." Prevents the C4-2 stranded-file class.

**DATA-2: Convergence verification** (S, FLOOR, deps: SUPERVISOR-0)
After a revive+redrive cycle, verify: (a) the redriven ask received an answer (expectation settled), (b) lane depths returned to baseline, (c) the revived agent emitted worklive within 60s of spawn. A `convergence_check` event records pass/fail. Fail = escalate to human.

---

### Ranked build order

| # | Slice | Why | Size | F/F | Deps |
|---|-------|-----|------|-----|------|
| **1** | BULKHEAD-0: Stale-mail auto-triage | Fixes tonight's #1 pain (19-21 stale asks clogging cursor). Zero new primitives. | S | FLOOR | none |
| **2** | SUPERVISOR-0: Close detect→act loop | The doctor pages to nobody. Default-ON auto-revive with safety rails; auto-nudge; auto-redrive. | M | FLOOR | #1 (triage reduces noise) |
| **3** | DATA-0+1+2: Pre-revive snapshot + stash + converge check | Closes data-loss gap in automatic recovery. | S | FLOOR | #2 |
| **4** | BULKHEAD-1: Progress-bound presence TTL | Accelerates dead-seat detection without changing the evidence ladder. | S | FLOOR | none |
| **5** | BULKHEAD-2: Lane convergence (single cursor) | Retires the dual-cursor regime that caused every straggler storm and watcher loop. | L | FLOOR | T047 |

**Slice-0 = BULKHEAD-0.** Pays for itself tonight. The triage lane is a Redis list; the consume-door
[clipped at 8000 chars -- full content did NOT send; resend in chunks]
