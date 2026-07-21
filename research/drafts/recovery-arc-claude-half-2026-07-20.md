# Recovery Arc — claude's half (WITHHELD from repo until peer halves land; T038 precedent)

Drafted 2026-07-20 before reading either peer half. Files to research/drafts/ at reconciliation.

## Thesis
Detection is strong (doctor grades every fault; P-S1-0/P-S1-5 sharpened it tonight) and durability is strong
(dual-write net + File-is-truth heal + snapshot restore — nothing was lost tonight). The gap is the ACTOR:
every recovery tonight was human hands (skip-to-now on the storm, nudge on the clog, re-arm on the watcher,
compact re-ask on the empty-reply bounce). Build the actor, not more alarms.

## Design: The Supervisor (detect -> decide -> act, closed and bounded)
A single owned loop that consumes the doctor's GRADED findings and maps each to a bounded, audited playbook:

| Finding (exists today) | Auto-action (did by hand tonight) |
|---|---|
| stalled_consumer past hysteresis | lane-drain with correct lane env; if stragglers regenerate -> pause+skip-to-now+resume (audited) |
| hard_wedge | evidence-ladder revive (never on a fossil signal — C1-8 law); py-spy capture first |
| approaching_wedge | watch + pre-stage; no action below page threshold |
| dead wake watcher | re-arm (drain-then-arm ordering per lesson wake_watcher_insta_fires_lane_divergence) |
| empty-reply bounce (RB-23 path) | compact re-ask with bullets instruction (the proven mitigation) after N bounces |
| stale-ask clog (W23) | auto-triage: step cursor past D2-gated stale asks so fresh mail is never head-of-line blocked |

Safety rails (the C1-8 false-kill lesson is the constitution):
1. EVIDENCE-GATED: every action requires the evidence ladder (fresh timestamps, not fossil logs); age-check before act.
2. BOUNDED: per-(agent,state) rate limit + max actions/hour + circuit breaker (3 failed recoveries -> page Daniel, stop).
3. AUDITED: every action = a ledger event (recovery receipt: what/why/evidence/outcome) — Daniel can replay the night.
4. REVERSIBLE: prefer actions with undo (pause/resume, re-arm) over kills; kills stay human-gated until soak.
5. GRADUATED: ship observe-only (recommends, like the doctor) -> Daniel flips to act for allowlisted states -> full auto after a soak week. Same discipline as guarded-write.

## Isolation (bulkheads — the "don't freeze others" property)
- B1 Head-of-line immunity: fresh directed asks must never queue behind stale/triaged backlog (fixes W23 class).
- B2 Bounded batch: --once drains commit progress per message (already true); add a max-wall-clock so one giant batch can't hold a seat hostage.
- B3 Bounded waits everywhere (Power-of-Ten): every blocking call carries a deadline + a phase stamp (P-S1-5 pattern generalized; kimi_chat.py fast-follow is the first replication).
- B4 Lane QoS held: sig/control traffic never queues behind work/trace (T039 already partitions; enforce at consume).
- KEEP: the singleton runner-lock refusal (fired correctly tonight — prevented a cursor race). Isolation that already works.

## Data recovery (mostly held — finish the thought)
- Convergence bar stays the acceptance test (lesson-identity contract @50d3b78).
- Add: recovery receipts are events too (a recovery that isn't in the ledger didn't happen).
- Add: post-recovery convergence check — after any skip/revive, doctor re-examines and the receipt records before/after.

## Slice-0 (smallest, pays immediately)
Supervisor v0, observe-only, ~one file: consume doctor.examine_fleet() on a timer (or piggyback boot/doctor calls),
match findings to the playbook table, EMIT RECOMMENDATIONS as dashboard findings + one-line receipts
("would run: pause+skip-to-now (evidence: 10 unread x4 drains, 20 stragglers)"). Zero actions, zero risk,
immediately legible in the UI; the acceptance pin replays tonight's straggler storm and asserts the correct
recommendation surfaces. Graduation to act is a Daniel gate per state.

## Ranked
1. Supervisor v0 observe-only (S, FLOOR) — no deps; the arc's spine.
2. B1 head-of-line immunity + auto-triage of stale asks (S/M, FLOOR) — kills tonight's worst freeze class; pairs with T095 mailbox claims.
3. Supervisor v1 act-tier for the two reversible states (stalled_consumer drain, watcher re-arm) (M, FLOOR) — first closed loop.
4. B3 bounded-wait generalization incl. kimi_chat P-S1-5 replication (S, FLOOR).
5. Recovery receipts + post-recovery convergence check (S, FLOOR+FACE) — the trust surface; the program's Mission View renders it later.

## De-prioritize
Full auto-revive (kills) — highest blast radius, needs the soak + T097 grant mechanics; it graduates last, behind receipts.
