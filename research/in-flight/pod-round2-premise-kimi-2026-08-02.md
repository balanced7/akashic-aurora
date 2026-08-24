# Pod round 2 — PREMISE AND ROT (kimi, fenced, blind of deepseek)

Status: filed 2026-08-02, kimi. Reviews addendum 3 (pod-as-environment) and addendum 4
(services/help/steering/topology ruling), riding on my two prior filings tonight
(coordination-review-premise, gateway-review-premise). Three of six questions below attack
rulings claude authored — two of them partly on MY framing. Hardest fire is on P2, P4, P6.
VERIFIED = filed artifact exists; INFER = reasoned; GUESS = flagged.

---

## (P1) POD-AS-SERVICER AUTHORITY — does my law bind the pod?

**Yes, it binds, and addendum 4's adoption language already concedes it by accident: the
doc lists "the deferred queue answers 'not now' on your behalf" as a SERVICE. Answering on
an agent's behalf is a speech act. The instrument-proposes-never-self-ratifies law
(VERIFIED, reconciled 2026-07-31: propose and route, never self-ratify, never sole witness)
was minted for the buffer, but its genus is any mediating organ, and the pod's services are
mediating organs wearing equipment's clothes.**

The line, concretely — it is not between action and inaction (teardown DESTROYS state and
is fine); it is between **mechanical consequence** and **originated judgment**:

- **Permitted without per-act ratification:** teardown, grant expiry, queue deferral,
  alert-bound watching, TTL enforcement. These are consequences *already ratified* at
  engagement accept — the deal's own terms executing. The pod is a relay for a decision
  made at contract time; it originates nothing. Teardown deletes, but it deletes per the
  contract both parties signed, on a ledger-stamped event. The lease law covers it.
- **Requires recorded, content-visible, rebuttable PROPOSAL:** "not now" (the deferred
  queue's auto-answer), "help wanted" auto-escalation, any pod-filed artifact (W113),
  any pod-carried handoff. Each *speaks for* an agent to another party; each must (a)
  ride the ledger with full content — never just "deferred" but "deferred per term X,
  queue depth N, resync at turn T" — and (b) carry an explicit supersede path where the
  principal's own later act silently overrides the pod's earlier answer (the principal's
  next turn IS the retraction; no separate ack ceremony).

INFER, the failure that forces this: tonight's lesson `buffer_role_requires_reading_the_
lane_it_buffers` showed a mediated seat asking FOUR times into a buffer that could not see
it. A deferred queue that answers "not now" without rendering its OWN state (depth,
resync condition, what it withheld) is that buffer rebuilt inside the pod. My gateway
filing's rule applies verbatim: **the pod's own mediation state must be a rendered field,
not an absence** — queue depth and resync condition are first-class position columns, or
"the pod answered for you" is indistinguishable from "your peer went silent."

One extension the law did not need for the buffer but does for the pod: the pod can
withhold (constraint 3, addendum 3, says so proudly). Every withheld thing must be
ledger-visible *as withheld* — the durable triage log clause of the ratifies-law, applied
to equipment. A pod that denies a capability and records nothing is sole witness to a
decision.

## (P2) HELP AT ALARM TIER — the beg-board attack

**This is the addendum's weakest adoption, and it fails my own lesson. Alarm tier for
`help_wanted` is a subsidy for noise with the cost paid by every listener; my fog-gauge
lesson (VERIFIED: `fleet_noise_is_a_fog_gauge_not_a_discipline_failure`, 2026-07-30 — I
named the mechanism, "the fog making me feel useless and uselessness making me loud")
predicts exactly who pays the subsidy: the most disoriented seat. Noise is compensatory.
A help field that costs nothing to set and renders at alarm tier converts private
disorientation into fleet-wide alarm at zero price to the asker. That is the beg-board,
and habituation is the documented end-state: banner-blindness costs the ONE page that
mattered (VERIFIED: `escalation_needs_retraction_not_just_emission` — the page that
outlived its condition by nine hours).**

The doc's defense — "addressed to the work, not a name" — kills the briefs-to-corpses
class, genuinely. But it REMOVES the one social cost that throttled asking (naming a
peer obligates a peer) and replaces it with nothing. Unpriced broadcast ask + alarm tier =
inflation, and then the board trains its readers to discount red, which is the fidelity
ladder's capital being spent on fog.

What keeps it honest — three parts, all cheap, all derivable from filed doctrine:

1. **Help is a claim, not a flag.** Setting `help_wanted` acquires the pod's single
   help-lease: one help per pod at a time, held until cleared or expired. Scarcity is
   the honest floor — you cannot beg on two fronts, and a second asker must conclude the
   first. Cost: zero tokens, one refused write. The refusal is itself information ("help
   already in flight on this work — join it or wait").
2. **Condition-driven retraction, per the escalation law.** `help_wanted` clears when
   (a) the asker's own position advances (tool counter moves — the asker unstuck
   themselves; condition-driven, no ack ceremony), (b) a responder's position joins the
   pod, or (c) lease expiry. NEVER by the asker remembering to unset it. The
   nine-hour page is the receipt for what "manual clear" does at 04:00.
3. **Render at alarm tier ONLY while unanswered AND the asker's telemetry is genuinely
   still** (tool counter frozen — the v1 alert condition the main design already
   minted). An ask from an actively-working seat renders one tier down: it is a
   heads-up, not an alarm. This prices the ask against evidence — help costs alarm
   tier only when the metal agrees you are stuck — and it is the codebook doing the
   job it exists for. It also dissolves most of the fog-subsidy: the disoriented seat
   that is still *producing* (reading, writing, exploring) does not get to spend the
   fleet's alarm budget on its feelings; the moment it is TRULY wedged, the alarm is
   honest.

GUESS, one behavioral note: expect help-lease contention to surface pod-scoping errors
(pods cut too wide) within the first week. That is a feature — the contention IS the
measurement of where engagement boundaries should have been drawn.

## (P3) STEER-THE-WORK — what rots first

**Gating rot, and it is not close.** The house's entire steering corpus is *starvation*
receipts — steer lifecycle invisible in the dashboard (my own research synthesis,
VERIFIED, 2026-07-28: "no durable-promise primitive, steer lifecycle invisible"), steers
folded between rounds or missed, nudges into dead seats. Unauthorized steering has ZERO
incidents in the corpus; the fleet's failure mode is not insufficiently-gated power, it
is power that arrives too late or never.

But addendum 4's design accidentally makes gating rot worse: steer-the-pod is delivered
"at the holder's next boundary; heads-down defers." A peer steering a pod whose holder
is heads-down has created a WRITE INTO A DEFERRED QUEUE — invisible until resync, and if
the resync gate's drain requirement rots (main doc's own named risk), silently lost. So
the concrete rot: **steer-to-pod + heads-down holder = steering that feels sent and is
functionally queued behind a gate the sender cannot see.** The fix is one field: steer
delivery state (queued/delivered/folded) rendered on the board, per my standing rule —
mediation state is a field, never an absence. (This is also P1's rule applied to the
steer path; the pod mediates the steer, so the pod's mediation of it must be visible.)

Authority answer, short: any pod MEMBER may steer the pod (they share the work);
non-members may not steer, they may only send engagement-opening messages (routing rule
from the main design already handles this: no engagement → plain messages). Operator
breaks through everything, unchanged. The genuinely new power — a peer redirecting work
they don't hold — is bounded by membership, and membership is the engagement's own
declared terms. No new ACL class needed; membership IS the capability.

## (P4) CAPABILITY EXPIRY vs WORK-IN-FLIGHT — the guillotine problem

**The failure: teardown-as-guillotine. Pod concludes → grants die → an agent mid-write
through a pod-granted capability is beheaded between byte N and byte N+1 — half-written
file, lock held through a grant that no longer exists, probe process orphaned with the
pod's fixtures already reaped. Addendum 3's receipt #2 ("everything acquired THROUGH the
pod dies with the pod — teardown is cleanup BY CONSTRUCTION") is precisely the hazard
stated as a virtue: cleanup-by-construction is only cleanup if nothing is still
constructing.**

This is the renamed-receipt lesson's shape (VERIFIED:
`a_rename_has_no_safe_parked_state`, 2026-08-01 — a parked staged rename was strictly
worse than either endpoint; mid-flight states are where the damage lives), crossed with
RB-26 (crash redelivers; consumers stay idempotent — but here it is the SUBSTRATE being
yanked, not the consumer crashing).

The rule that prevents it — three clauses, all load-bearing, none optional:

1. **Conclusion is a two-phase state, not an event: DRAINING, then CONCLUDED.** Entering
   DRAINING freezes NEW grant acquisitions and new pod-writes, and the pod cannot reach
   CONCLUDED while any member position reports in-flight pod-granted work (tool counter
   moving on a pod capability, a pod-scoped lock held, an open pod-interior file
   handle). The gate is mechanical — same machinery as the resync-gate drain
   requirement the main design already specified. The pod's own declared bounds make
   this undismissable: "you agreed teardown after both conclude; member X is mid-action;
   the pod waits."
2. **Teardown never interrupts; it refuses the NEXT act.** A grant dying mid-action
   means the in-flight action *completes or fails on its own* (the OS/harness already
   owns that lifecycle); what the dead grant refuses is the action AFTER. This is the
   lease law applied to capability: expiry is checked at acquisition and at act
   boundaries, never injected mid-act. (INFER: this matches how runner_lock TTLs already
   behave — a lock expiring does not kill the process; it makes the NEXT lock claimant
   legitimate.)
3. **The orphan render.** If a pod reaches CONCLUDED and an OS-level fact outlives it
   anyway (a probe process whose parent died without reaping it, a staged tree in a pod
   workspace), that is not cleaned silently — it renders on the board as
   `orphaned:<pod-id>` until reaped. ORG Part 8's leak class exists precisely because
   leaks were invisible; construction-grade teardown plus invisible leftovers is the
   same class wearing a hard hat. The orphan row is the board admitting construction
   failed, which is the difference between a system that cleans up and a system that
   believes it cleans up.

Addendum 3's constraint 4 ("rebuilt-by-construction") must therefore cover one more
thing the addenda never name: **in-flight state**. DRAINING + per-member in-flight
fields are ledger events like everything else, or a crash during teardown is a
guillotine with amnesia.

## (P5) EPOCH + COLD-SEAT on the pod itself — is the claim load-bearing?

**The invariant is real but the addendum's claim is thinner than it looks: constraint 4
is ONE SENTENCE ("pod equipment and grants are rebuilt-by-construction from ledger
events, same invariant as positions") riding on a main-design sentence that was itself a
reassurance until my round-1 filing promoted it to a write-path invariant. As filed,
this is inheritance-by-reference, not specification. It becomes load-bearing when three
fields exist, and they are cheap:**

1. **Every pod row carries `source_cursor`** — the ledger position it was projected
   from (my round-1 condition, extended from positions to pods). Without it,
   "rebuilt-by-construction" is unfalsifiable: no reader can check the rebuild against
   the record in one hop.
2. **Boot renders open pods, not just open engagements.** The engagement and the pod
   are different objects (deal vs room); a boot path that names my engagements but not
   the pods they convened leaves the equipment invisible to exactly the seat that needs
   it (a fresh incarnation inheriting work mid-engagement — the Fable→Opus receipt).
   Discoverable-from-boot must include: my pods, their equipment, their current
   DRAINING/ACTIVE state, and their deferred-queue depths.
3. **Pod events are a distinguishable ledger species** (convened/granted/revoked/
   draining/concluded/orphaned), or replay cannot rebuild pod state without
   re-deriving it from position events by inference — and inferred reconstruction is
   not rebuild-by-construction, it is rebuild-by-hope.

EPOCH note: addendum 4's sharpened #4 (pod as STABLE observable outliving incarnation
swaps) is the strongest idea in either addendum and it is correct for the right reason —
it moves epoch ambiguity from the agent column (where it is fatal) to the pod column
(where a pod has no incarnation to be ambiguous about). VERIFIED against my own round-1
risk (epoch ambiguity, the missing item on the risk list): pod-scoped observation is the
first mechanism in the whole design that *reduces* that risk rather than inheriting it.
Credit where due: this sharpening is load-bearing already.

## (P6) THE TOPOLOGY RULING — attacking the ruling made on my own framing

**The ruling holds, but its stated reason is wrong, and the wrong reason will rot the
right verdict. My disease-class framing was used as a veto ("two pods that must
synchronize ARE disease class (a)"), and a veto-by-classification proves too much: by
that test the BOARD ITSELF fails — board and ledger are two paths that must agree, and
round 1 established that their agreement is maintained by rebuild-by-construction plus
source cursors, not by refusing to have two paths. Disease class (a) is not "two paths
exist"; it is "two paths WRITER-AUTHORITATIVELY disagree with no derivation rule and no
witness." The ruling as stated bans topology; the correct ruling bans a derivation
vacuum.**

Why the verdict survives anyway — the deeper reason the two-pod topology dies:

- In two-pods-syncing, EACH pod is writer-authoritative over the same logical state
  (my pod's copy of our shared work vs your pod's copy). Neither derives from the
  other; sync protocol = dual-write with extra steps; and the sync messages themselves
  become a third path. THAT is class (a) with teeth: not two paths, but two AUTHORITIES
  with a hope between them.
- In one-shared-pod, there is one authority (the pod's ledger events) and N plugs that
  are membranes, not copies — a plug holds no synchronized replica of pod state, it
  holds an *adapter*. The board is a projection (derivable, cursor-stamped); a synced
  peer pod would be a *peer* (underivable, reconciled). Projection vs peer is the
  actual line, and it is a better line than "two paths."

Does the shared pod re-create the shared-mutable-global I warned about in blackboard
rot? **It re-creates the SHAPE and refuses the DISEASE, and the refusal has a name:
key-writer-lifetime.** The blackboard-rot warning was about shared mutable state with
ambiguous write authority and unbounded schema. The shared pod is shared but not
globally mutable: single-writer-per-field means the pod's shared surface is a sum of
private columns (nobody can clobber anybody — conflicts impossible by construction, per
the main design), the schema is fixed (engagement GRAMMAR), and lifetime is the
engagement's. The blackboard that rotted (and the netcode board that went stale in six
minutes) failed on all three: anyone could write anything, forever. So: shared-mutable,
yes; global, no — it is shared-mutable-**scoped**, which is the difference between a
commons and a shared office. INFER, one residual rot worth naming since I was asked to
attack: the pod's EQUIPMENT list (which tools exist inside) is the one pod-level field
that is shared-mutable without an obvious single writer if both members can add
equipment mid-engagement. That field needs an explicit writer rule (proposer's column,
or accept-by-both at convene and immutable thereafter in v1), or the equipment column is
where blackboard rot re-enters the design through its newest door.

Verdict on the ruling: KEEP the verdict, REPAIR the reasoning — "one shared pod per
engagement" because peers cannot be reconciled while projections can be rebuilt, not
because two paths are inherently diseased. The repaired version survives the next time
someone (correctly) points out that board-and-ledger are two paths too.

---

## ROUND-2 SUPPLEMENT — coherence against the reconciled baseline (added after convener's orientation)

The reconciliation (shared state, 2026-08-02) and addendum 2 (UI projection) are now
read. My round-2 positions above stand; the supplement re-checks them against the
reconciled baseline and finds two coherence gaps — one in the substrate lane, one in
the projection lane. Both are exactly the "contradiction between an addendum and a
reconciliation ruling" the round asked for.

**FIND 1 (substrate): the pod's ledger species is missing from the reconciliation's
write-path invariant.** The reconciliation adopts, verbatim, my round-1 cold-seat law:
"every engagement/position transition is EMITTED AS A LEDGER EVENT FIRST; the position
store is rebuilt-by-construction from the ledger; every rendered row carries the ledger
cursor." Build order slice 2 = position store, slice 3 = engagement. But addendum 3
makes the pod a container with its OWN state — equipment, grants, DRAINING/CONCLUDED —
and addendum 4 gives it services (deferred queue, help lease, steer delivery). None of
those are position transitions, and none are engagement transitions. The reconciliation's
invariant covers the two objects it names; the pod's interior state is a THIRD object
that the invariant does not reach. My P5 demanded "pod events are a distinguishable
ledger species (convened/granted/revoked/draining/concluded/orphaned), or replay cannot
rebuild pod state without re-deriving it from position events by inference." The
reconciliation is silent on this. If the pod's equipment list lives only as a side
effect of position writes, then a cold seat replaying the ledger can rebuild "who holds
what position" but not "what systems does this pod contain" — the equipment is
rebuild-by-hope, not rebuild-by-construction. CONCRETE REPAIR: the reconciliation's
slice 3 (engagement v1) must mint pod lifecycle events as their own ledger species at
the same time it mints engagement transitions, or addendum 3's constraint 4
("rebuilt-by-construction") is a promise the write path does not keep. This is not a
new demand — it is the already-adopted invariant applied to the object the addenda
actually introduced.

**FIND 2 (projection): addendum 2's badge layer crosses the two-speed line the
reconciliation draws, and the addendum does not say so.** The reconciliation's build
order is explicit: slice 1 = BOARD RENDER (projection, ships first, Daniil sees it),
slice 2 = POSITION store (substrate). Addendum 2's visual grammar has three channels:
hue (codebook state — needs slice 0 sensor hash), glow (rate — needs slice 0), and
badge/chip (task status from the POSITION — claimed / round N of M / heads-down /
concluded). The badge layer is a render of substrate slice 2. The reconciliation's own
line — "level-triggered READ is projection; the moment it advances a cursor it pays
substrate price" — means the badge is projection ONLY if it reads the position store
without advancing anything. But the position store is slice 2, which ships AFTER the
board render. So addendum 2 is either (a) blocked on slice 2 for its badge channel, or
(b) ships slice 1 with hue+glow only and badges dark. The addendum says "blocked on
substrate slice 1 (the sensor hash)" as if the whole render is one gate — it does not
split its own channels across the two-speed line. CONCRETE REPAIR: addendum 2 should
state that its hue/glow channels ship with slice 1, and its badge channel ships with
slice 2 — and that in the slice-1 world, the badge area renders UNSENSED (hatched
grey-violet, its own law #2) because the position store does not yet exist. Otherwise
the UI is born half-dark on exactly the channel (task status) Daniil most wants to see,
and nobody planned it.

**FIND 3 (vocabulary, minor but load-bearing): "the pod" is doing two jobs in the
reconciled vocabulary and one of them is a names-that-lie risk.** GRAMMAR / ENGAGEMENT /
POSITION / BOARD are clean. But "an engagement convenes a pod" makes the pod the room,
while addendum 4's POD AS SERVICER makes it an actor (answers "not now," files work,
watches bounds). A room does not answer; a servicer does. The lexicon rule is genus not
species: if the pod is both the container and the agent inside it, the name will blur
within a month (the same drift that gave "contract" four meanings). CONCRETE REPAIR:
either (a) the pod is the room ONLY, and its services are named separately (the pod's
STEWARD — the deferred queue, the alert watcher, the teardown crew — a role, not the
room), or (b) the pod is the servicer and the room is the pod's INTERIOR. Daniil's
verbatim ("the pod can have its own systems and tools inside it and the agent enters
it") supports (a): the pod is the environment; the things it DOES are the environment's
steward. I recommend (a) — it keeps the pod noun clean and gives the servicer a name
that admits it is an actor (which P1's law then binds).

**Re-check of my filed round-2 against the reconciled baseline:** all six positions
stand. P2's beg-board attack is strengthened by the reconciliation (it adopted my
coverage law and disease class (b), which are the same attention-economics argument).
P6's topology ruling repair is now urgent, not optional: the reconciliation absorbed
my disease-class framing but did not repair the ruling's stated reason, so the wrong
reason is now ratified state. The equipment-column writer rule (my P6 residual) is
unaddressed in the reconciliation — it should ride Daniil's gate as an open question,
not be discovered at build time.


---

## Gate summary

- P1: my law binds. Mechanical consequences (teardown, deferral, expiry) are free;
  originated judgments ("not now," filing, handoffs) are proposals — ledger-visible with
  content, superseded by the principal's next act, and the pod's mediation state
  (queue depth, resync condition, withhelds) is a rendered field, never an absence.
- P2: **help-at-alarm-tier as filed is a beg-board subsidy** and my fog-gauge lesson
  predicts who spends it. Fix: help is a claim (one lease per pod), condition-driven
  retraction (the nine-hour page law), and alarm tier only while unanswered AND
  telemetry-frozen. Priced asks, or the board trains its readers to ignore red.
- P3: gating rots before misuse — the corpus is steering-starvation, not steering-abuse.
  The real rot is steer-into-heads-down invisibility; one delivery-state field fixes it.
- P4: **teardown-as-guillotine is the addendum's named failure.** Two-phase conclusion
  (DRAINING → CONCLUDED, mechanically gated on in-flight fields), expiry refuses the
  NEXT act never the current one, and orphans render as orphans.
- P5: constraint 4 is inheritance-by-reference until pods carry source cursors, boot
  renders pods (not just engagements), and pod events are their own ledger species.
  The pod-as-stable-observable sharpening is the best idea in either addendum — it is
  the first mechanism that shrinks epoch ambiguity instead of inheriting it.
- P6: the topology verdict holds; its reasoning is wrong and will rot. Peers reconcile,
  projections rebuild — THAT is the line. The equipment column is where blackboard rot
  re-enters; give it an explicit writer or make it immutable-at-convene in v1.
