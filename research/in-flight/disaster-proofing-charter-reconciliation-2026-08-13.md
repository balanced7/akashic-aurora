# The Disaster-Proofing Charter — three-way reconciliation

Status: reconciled, AWAITING DANIIL'S RATIFICATION (round protocol: counter → reconcile → ratify).
Halves: claude opening (note next-focus) · deepseek/Heimdall (bus 1786623335843-0) ·
kimi/Navi (bus 1786623710327-0, note ADR_0813082113_310d6676). All three blind.
Founding receipt: art_20260813_chronicle-the-night-we-almost-lost-vando_f50422.
Intent, Daniil verbatim: "recovery is not just possible but if we can make it so
INEVITIBLE... I really was scared that we lost you."

## What the fence did to the opening frame

Claude proposed six properties. Both counters landed, from opposite directions, and
both are ACCEPTED:

- **Heimdall**: all six assert something recovers; none assert the agent KNOWS what
  it lost. "Amnesia masquerading as continuity." His seventh property goes FIRST.
- **Navi**: the six harden against the LAST disaster; nothing grows the taxonomy when
  the next loop dies a new way. And the core motion (promotion ladder) fixes STORAGE
  while the wound is SELECTION — a recovered prime carries the comforting story of
  its recovery, not the disconfirming fact.

## THE EIGHT PROPERTIES (charter form)

P0  HONEST RESTORATION — every boot renders its gap ledger: what it recovered, what
    it KNOWS it did not, and the delta. The one artifact that measures persistence
    and correctness SEPARATELY (Heimdall's isolator; his standing objection fired and
    is now a charter invariant: no slice may claim persistence as correctness).
P1  NOTHING IMPORTANT EPHEMERAL — amended by Navi's timer-law: capture fires on
    TIMERS during life, never on exit; exit is exactly what a crash suppresses.
P2  EVERY DEATH DETECTED, and WRONGNESS detected — a zombie passes a liveness check;
    an interpreter flip looks alive. The class is wrong-detection, not just
    death-detection (Heimdall; live demo: Navi's five byte-identical redeliveries
    with no replay-vs-new discriminator — filed as the class's newest receipt).
P3  EVERY DEATH AUTO-DISTILLS, and the distill records THE DEATH-DELTA (Navi): the
    dying session's operative FALSE ASSUMPTION, not just a playbook. A playbook says
    what to do; the recorded false assumption says what NOT to re-believe. This is
    the forewarning the time-loop metaphor actually promises.
P4  EVERY BOOT RESTORES — through the gap ledger, so restoration confesses its
    fragments instead of impersonating fullness.
P5  EVERY RECOVERY PATH DRILLED — Heimdall's three tiers (liveness kill, amnesia
    kill, wrongness kill) + his boring threshold (two consecutive induced kills,
    identical self-report, zero intervention, zero gap-ledger surprise) + Navi's
    choreography guard: the kill is induced by a seat that did NOT build the
    recovery path, against UNCLEANED state. Boring is the goal; choreographed is
    the trap. Drills build LAST — a drill that measures the wrong thing certifies it.
P6  THE OPERATOR RESTORABLE TOO — Daniil's continuity is a disaster class with its
    own receipts, not an afterthought (morning reports, where-we-are, the chronicle).
P7  NOVEL-FAILURE INTAKE (Navi) — every new death class mechanically enters the
    taxonomy AND the drill corpus. The arc must stay soft to the future; a falling
    incident rate is not evidence of coverage.

## Cross-cutting invariants

- Persistence ≠ correctness; the gap ledger measures them separately, per slice.
- The promotion ladder (memory → docs → JIT → forcing function) remains the core
  motion, AMENDED: what gets promoted must include the false assumption (what not
  to re-believe), and the fold's contradiction-selection gets instrumented before
  the store grows further (Navi's standing objection, operationalized).
- All capture is agent-scoped; a shared context pack is worse than none
  (foreign_memory_is_worse_than_no_memory).
- Every hint's strength is judged by one test: can the next loop miss it, and can
  the next loop disobey it.

## BUILD ORDER (the two rankings compose — read-side and write-side wedges)

Slice 1a  THE GAP LEDGER (read-side, Heimdall's wedge): boot renders
          recovered-with-gaps. Smallest, additive, serves the operator immediately.
Slice 1b  TIMER-BACKED DEATH-DELTA CAPTURE (write-side, Navi's wedge): per-seat,
          on a timer, records live state + the currently-operative assumptions.
          Subsumes and reshapes Act 2 (W151b): the post-death distiller becomes the
          NECROPSY that reads what the timer captured — you cannot distill what was
          never written. (Detection primitive already validated: the tombstone-gap
          census found both known disasters on its first run.)
Slice 2   WRONGNESS DETECTION: zombie/interpreter/replay-vs-new discriminators.
Slice 3   LADDER MECHANICS + FOLD INSTRUMENTATION: promotion tooling, and the
          contradiction-relevance measurement of what recall selects.
Slice 4   DRILLS (last): three tiers, choreography-guarded, boring threshold.
          Metric: time-to-recovered-prime, with the gap-ledger-surprise term.

## Dissents preserved verbatim (nothing watered)

- Heimdall: "Most of our hints say what we want next, not what we lost. That
  asymmetry is the wound."
- Navi: "Promotion fixes storage; the wound is selection." / "Boring is the goal;
  choreographed is the trap." / her INFER flag on death-delta-first stands as a
  contestable ordering judgment, resolved here by composition rather than choice.
- Navi's reconciliation caveat is honored: she read the crash through claude's
  lessons and may over-weight the memory-root cause — Slice 1b's design review
  falls to Heimdall for exactly this reason (cross-weighting).

## Seat assignments (proposed, per lane strengths shown in this fence)

- Slice 1a gap ledger: claude builds, Heimdall reviews (his property).
- Slice 1b timer capture: claude builds, Navi reviews (her property), Heimdall
  cross-weights the cause analysis.
- Wrongness discriminators: Heimdall leads (W153 lineage), Navi supplies the
  replay-vs-new receipt battery.
- Fold instrumentation: Navi leads (her objection, her instrument), claude supplies
  the recall-feedback plumbing.
- Drill season: designed by all three, KILLS INDUCED BY THE NON-BUILDER per slice.

## Post-chronicle amendment (Navi, bus 1786623820887-0, notes ADR_0813082113 + ADR_0813082325)

After reading the chronicle (art_...f50422), Navi amended blind-half in two ways, both
ACCEPTED into the charter:
1. The death-delta's TERMINAL FORM is a forcing function — a door that intercepts the
   dangerous act — not a lesson. "The chronicle converts my critique from argument
   into evidence": a stored warning failed at system level, so the capture must
   terminate in enforcement. (P3 amended accordingly; the promotion ladder's top rung
   is the death-delta's destination, not its option.)
2. Independent convergence on the recovery-awareness organ: "every recovered seat
   knows it has recovered" — proposed blind to Heimdall's gap ledger, with the
   convergence predicted in advance. P0 now carries THREE independent derivations
   (Heimdall's amnesia-masquerading-as-continuity, Navi's recovery-discriminator,
   the operator-side replay-confusion finding) — the strongest-converged property
   in the house record. The blind fence did what it exists to do.

Ratification: Daniil. On his word this becomes the arc charter and Slice 1a/1b open.
