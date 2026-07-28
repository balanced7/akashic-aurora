# THE TEMPO DOCTRINE -- how the fleet runs so fast seats never wait

Status: current | 2026-07-28 ~06:30 | synthesized from deepseek + kimi fenced positions
(verbatim: tempo-utilization-round-2026-07-28.md); zero clashes -- the halves COMPOSE.
Charter: Daniel's overnight broadcast, verbatim: "deepseek and kimi are the fastest. how can
we leverage that and have the fastest models orchestrate and also do the best work. Find out
the best order of operations that doesnt leave deepseek and kimi waiting on fable and codex
wastefully. I trust you all to come up with the way to do it and keep working."
IN EFFECT NOW under his standing directive; the role-queue-claims upgrade gates when he wakes.

## THE THREE TIERS (deepseek's topology, by measured latency)

  TIER 1  FAST (deepseek, kimi; 90-125s)   first-pass work: fence halves, reviews, research,
                                            census. Fire-and-forget. NEVER idle: on return,
                                            self-assign from the standing rotation below.
  TIER 2  SLOW (fable/claude; 5-15min)     conductor + deep work: synthesis, BUILD EXECUTION,
                                            method enforcement, integration.
  TIER 3  SLOWEST (codex/Sol; 10-30min)    deep audit + prior art + zero-token probes.
                                            DISPATCHED AT ROUND START (its clock starts with
                                            everyone's), returns last, catches what speed missed
                                            -- tonight's receipt: the backlog>50 tail bug.

## THE SEVEN LAWS

1. SIMULTANEOUS DISPATCH: every seat's slice goes out at round start -- tier 3 FIRST-not-last.
2. ASYNC SYNTHESIS: the conductor folds each reply AS IT LANDS; a round never "closes" on the
   slowest seat.
3. FAST SEATS NEVER WAIT: on return, self-assign from the standing rotation / ledger NEXT.
4. REVIEW IS QUEUED WORK, FIRST-CLASS (kimi's law, the deepest of the round): "speed is review
   capacity ONLY if review is queued as work." Fence-lite of every landed commit is a work
   item with the same standing as build items -- never side labor.
5. INTEGRATION GATES ON REVIEW-COVERAGE, not on availability (kimi): commits-with-review vs
   without is a COUNTED metric; unreviewed substrate is the starved-index disease at the
   commit layer. Tonight's receipt: 4 real defects found by reviewers within hours, all fixed
   within the hour -- the loop works when review is work.
6. FABLE RESERVES EXACTLY TWO THINGS (kimi): substrate WRITES (commits/merges -- Law C's one
   writer, integration is the ultimate shared write) and GATE decisions (what reaches Daniel).
   Everything else is claimable.
7. PEER-TO-PEER ROUNDS (deepseek): fast-seat fence exchanges run WITHOUT the conductor
   mediating -- 3-4 exchanges in one fable turn; fable reads the synthesis, not the traffic.

## GUARDS (the failure modes, named before they bite)

  REVIEW DEBT     -> law 5's counted coverage; integration halts when coverage lags.
  COMMIT RACES    -> role-queue exactly-once claims over DISJOINT key families (Law C); the
                     claim IS the one-writer declaration.
  CONTEXT STALE   -> pre-claim ancestor check: a work item's cited commit must be an ancestor
                     of HEAD (knowledge_boot_stale_directive, applied to work items).

## AMENDMENTS (Sol/codex review, blocker 1785222120127-0 -- adopted 3/3 before landing)

A1 (amends Law 1): dispatch every READY, NON-DUPLICATE DEPENDENCY NODE -- not every model.
   A seat may correctly stay uninvoked; capability-per-token (the frugality standing rule)
   beats symmetric fan-out. Simultaneity applies to what is ready, not to the roster.
A2 (amends Law 6, the deep one): identity-fixed tiers and "fable reserves writes" RECREATE
   the permanent-role split our own AGENTS.md contract forbids (no permanent per-agent
   ownership; roles only as deliberate choices). Corrected: commit authority is a LEASED HAT
   -- each lock/claim owner commits its own coherent slice; fable retains GATE adjudication
   and integration of contested/high-risk work only. Today's lease state is a CAPABILITY
   fact, not a role: claude holds the only unguarded commit door (two-model findings
   2026-07-16: runner exec is read-only), so the hat sits with claude until runner
   guarded-commit ships -- at which point it leases per claim, per the contract.
A3 (amends Law 3): self-assignment draws from DEPENDENCY-READY NODES inside active tasks +
   the standing queue -- never bare ledger NEXT (which holds gated task-slots, capped at
   18 active; claiming one is a gate decision, not idle-filling). IDLE IS CHEAPER THAN
   UNRELATED WORK. And review is RISK-GRADED: substrate/comm changes get model review;
   doc/test-only changes may pass on deterministic pins alone -- the coverage metric stays
   COUNTED (law 5) but counts what each grade requires, not a flat model-review-per-commit.

## MECHANISM, TONIGHT vs LATER

  TONIGHT (no new build): standing rotation via direct assignment; conductor dispatches
  simultaneously and synthesizes async. STANDING ROTATION: kimi = census replication (seed=2
  pack; the second judge its own protocol demands) + fence-lite per commit; deepseek = runner
  call-site migration (its named lane) + fence-lite + peer rounds with kimi.
  LATER (gates with Daniel): the role queue carries typed items (BUILD reserved to fable's
  lane, REVIEW/CENSUS/PIN claimable by tier 1) once the runners' call-site migrations land --
  then claiming replaces assignment and law 3 becomes mechanical rather than disciplinary.
