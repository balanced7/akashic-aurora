---
akashic_id: art_20260701_recovery-arc-reconciled-design-superviso_ce9a9e
akashic_sha: 5ba2dbb2150f
status: current
type: design
date: 2026-07-01
title: Recovery Arc — Reconciled Design (Supervisor/Steward)
gist: "Halves (all filed before any was read by another author — T038 blind protocol held): - claude: research/drafts/recovery-arc-claude-half-2026"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, security, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260720_recovery-arc-claude-s-half-withheld-from_1eb043
    rel: cites
  - target: art_20260720_recovery-arc-kimi-s-blank-slate-half-ver_35a556
    rel: cites
  - target: art_20260720_recovery-arc-deepseek-s-blank-slate-half_c69bb3
    rel: cites
created: "2026-07-20T22:35:15"
updated: "2026-07-23T21:42:06"
---
<!-- GENERATED PROJECTION of art_20260701_recovery-arc-reconciled-design-superviso_ce9a9e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Recovery Arc — Reconciled Design (Supervisor/Steward)

Halves (all filed before any was read by another author — T038 blind protocol held):
- claude: research/drafts/recovery-arc-claude-half-2026-07-20.md (withheld until peers landed)
- kimi (STEWARD, 2 parts): research/reviewed/recovery-arc-kimi-half-2026-07-20.md
- deepseek (BULKHEADS + SUPERVISOR-0): research/reviewed/recovery-arc-deepseek-half-2026-07-20.md

Daniel's charge (2026-07-20): robustness/reliability/intelligent recovery; seamless fault handling so
processes don't freeze other aspects; recovery that is automatic and recovers data. NASA-grade bar (T098).

## Where all three converged, independently

1. **The gap is the ACTOR, not detection or durability.** Doctor grades findings; dual-write/heal/snapshot
   held under fire tonight; every recovery was human hands. Build the bounded actor that closes
   detect → decide → act. (claude "Supervisor", kimi "STEWARD", deepseek "SUPERVISOR-0" — one organ, three names.)
2. **Same slice-0, chosen blind by all three:** the stale-mail / head-of-line / storm class.
   (claude B1 + observe-v0; kimi RANK-1 R4 bulkhead+auto-clear; deepseek #1 BULKHEAD-0 auto-triage.)
3. **The C1-8 false-kill lesson is the constitution.** Evidence bars before action (two-signal doctrine),
   never act on a fossil signal. All three made it the first safety rail.
4. **Receipts on every action.** A recovery that isn't in the ledger didn't happen
   (claude receipts; kimi W26 first-class receipt artifact + dissent D1; deepseek supervisor_action events).
5. **The actor is itself a supervised, fail-open seat** — its own worklive/pulse/doctor findings; an
   internal error stops it loudly, never wedges the fleet (kimi P4; deepseek ManagedChild composition).
6. **Data recovery = re-projection + convergence**, never edit-in-place (lesson-identity contract
   generalized; kimi P5 + W29 replay-check; deepseek DATA-0/1/2; claude post-recovery convergence check).

## The load-bearing unique contributions (folded whole)

- **kimi P1 — CATALOG, not policy engine.** The actor picks only from a fixed, fenced recovery catalog
  (trigger → preconditions → action → evidence bar → rollback → blast radius). It cannot invent a
  recovery; a new fault class is a new fenced catalog entry. This is the design choice that makes the
  actor trustable. ADOPTED as the governing principle.
- **kimi P3 — per-seat CORDON with sender-visible state.** A faulting seat is quarantined; senders get an
  immediate loud "X is in recovery, ask parked" instead of silence into a damming inbox (W28). Recovery
  never takes a lock/cursor/lane a live seat holds (fencing generations respected).
- **deepseek rungs — graduated force: NUDGE → PROBE → REVIVE → REDRIVE**, with second-observer
  concurrence + rate cap (3/agent/session) + cooldown (120s) + first-ever-kill-human (T097 D2)
  on the sharp rungs.
- **deepseek BULKHEAD-1 — progress-bound presence TTL** (dead pulse accelerates presence decay; the
  evidence ladder's job gets shorter without changing its verdicts).
- **deepseek BULKHEAD-2 — lane divergence IS a fault class.** Single-cursor convergence (T047 the vehicle)
  retires the dual-cursor regime behind tonight's watcher loop and every straggler storm.
- **deepseek DATA-1 — pre-revive auto-stash** of uncommitted working-tree changes (+ DATA-0 in-flight
  snapshot, 7-day retention) so an automatic revive can never eat work.
- **claude — drain-then-arm ordering, empty-reply → compact-re-ask playbook entry, bounded-wait
  generalization** (P-S1-5 phase-stamp pattern to every blocking call; kimi_chat.py first replication).

## The one genuine tension (for Daniel's gate)

Auto-revive posture: deepseek argues **default-ON with rails** (opt-out; the doctor pages to nobody
today); kimi ranks auto-revive third with a **mandatory, non-negotiable evidence bar** and a short,
sacred human-gate list; claude ships **observe-only first**, graduation per catalog entry.

RECONCILED RECOMMENDATION: graduation per catalog entry, fast but explicit — S1 ships observe-only
(recommendations + receipts, zero risk); Daniel flips act-tier per entry starting with the reversible
rungs (nudge/probe/re-arm/triage); REVIVE goes auto only after its receipts prove correct in soak,
with deepseek's rails (second observer, rate cap, cooldown, first-kill-human) intact from day one.
This honors deepseek's urgency (the loop closes this week), kimi's constitution, and keeps every
graduation an auditable Daniel decision. **Daniel rules on this at the gate.**

## Sliced build plan (each slice fenced, pins RED-first, receipts)

- **S0 — Stale-mail auto-triage + storm auto-clear** (S/M, FLOOR; = deepseek BULKHEAD-0 ∪ kimi R4 ∪ claude B1).
  Consume path parts stale asks (> STALE_ASK_THRESHOLD_S, default 4h) to a triage surface BEFORE the
  consumer, advancing the cursor past them; fresh mail flows immediately. Storm signature (lane-depth
  slope + repeat-delivery count) triggers auto pause→triage→resume with a receipt. Kills W23/W27-class
  freezes. Acceptance pin replays tonight's straggler storm + the 19-stale-ask clog.
- **S1 — Supervisor v0, observe-only** (S, FLOOR). Ticks over doctor.examine_fleet(); matches findings to
  the CATALOG; emits recommendations as dashboard findings + one-line receipts ("would run: skip-to-now;
  evidence: …"). Own worklive + fail-open. The catalog ships with tonight's six entries.
- **S2 — Act-tier, reversible rungs** (M, FLOOR). NUDGE/PROBE + dead-watcher re-arm (drain-then-arm) +
  compact-re-ask on empty-reply bounce + auto-redrive on self-confessed error. Per-entry Daniel flip.
- **S3 — Data leg** (S, FLOOR). Pre-revive snapshot + auto-stash (DATA-0/1) + post-recovery convergence
  check (DATA-2) + `doctor --replay-check <agent>` (kimi W29). Declares per-surface replay sources
  (cursor/presence/worklive become re-projectable; kimi's RPO declaration).
- **S4 — REVIVE rung** (M, FLOOR; integrates T097). REVIVE_PEER cap implemented here; second-observer
  concurrence; the T097 grant mechanics land as designed (deepseek ACL lane). Human-gated until soak.
- **S5 — Cordon + sender-visible recovering-state** (M, FLOOR+FACE; kimi P3/W28) + progress-bound
  presence TTL (BULKHEAD-1).
- **S6 — Lane convergence, single cursor** (L, FLOOR; = T047 executed as a recovery slice; retires the
  divergence fault class structurally).

Cross-cutting bars: catalog-not-policy-engine; evidence ladder before every action; receipt on every
action (surfaced in delta + UI); the actor never grades its own recoveries (kimi D1 — doctor re-examine
or peer fence confirms clearance); recovery drill harness (deepseek W32) grows one drill per slice.

Wishes absorbed: kimi W25-W29, deepseek W30-W32 (+ his unstick/receipt/self-clearing folded into
kimi's W25/W26/W27), claude W23/W24 adjacency. Program tie: receipts + cordon-state render in the
T098 Mission View later (FACE); everything above is FLOOR the program stands on.

## Gate asks for Daniel
1. Approve the arc + slice order (S0 → S1 → S2 → S3, then S4-S6 sequencing at your call).
2. Rule on the auto-revive posture (reconciled recommendation above).
3. S0 starts on approval — it is the same-night-payoff slice.
