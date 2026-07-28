# THE BUILD QUEUE -- synthesized from four halves, two debate rounds

Status: current | 2026-07-28 ~03:30 | AWAITING DANIEL'S GATE
Inputs: build-plan-claude-half + build-plan-peer-halves (plans AND rebuttals, verbatim) +
multiplayer-netcode-prior-art-2026-07-28.md + the T108 fence + the fleet-debate reconciliation.
Sibling seat STOOD DOWN before filing (Daniel confirmed; its own stand-down machinery from
3695d66, exercised for real) -- three halves total, and its stop-hook tombstone gap returns to
the open pool (folded into S3's scope: a tombstoned session gets no re-arm demand).

## HOW THE CLASHES RESOLVED (all four, with concessions on the record)

X1 AUTHORITY: kimi's synthesis dissolved the fork -- THE MAILBOX IS BUILT TWICE. A thin
   CLAIM-WRITE SEAM ships first (new write paths land in their permanent home from day one --
   "migration-later is how the File-plane fossil was born", conceded by deepseek verbatim),
   and the FULL T1-T5 hardening ships last (deepseek's build-writers-before-hardening,
   conceded by kimi). Both were right about different layers.
X2 CENSUS: both conceded. deepseek to its own round-1 sentence; kimi named its category slip
   ("the census reads KNOWLEDGE planes, not message-state... my evidentiary coupling
   dissolves"). CENSUS RIDES FIRST, PARALLEL to the seat arc, not gated by it.
X3 ROSTER: both adopted claude's roster/D1 as the reaper's missing sensor -- kimi: "without
   it the reaper is an organ with no sensor, the confident-zero shape again."
X4 SMALL ITEMS: deepseek had them as alongside-fixes all along ("too small to serialize, too
   load-bearing to defer" -- adopted as the disposition); kimi named its omission a DROP and
   corrected. Both ride alongside S1 as standing fixes.

## THE QUEUE

TRACK R (recall arc -- the product; rides parallel, no seat-arc dependency):
  R1. JUDGE THE CENSUS. Fresh pack seed=2 primary, seed=1 audit pack as anchoring control.
      Bar quoted per case. NONE-NEEDED residual + reason. RECORD-vs-CLAIM tagging rides the
      same judging pass (same eyes, same corpus). Single-judge labelled; peers replicate.
  R2. CORRELATION GATE, measured against the frozen pack (which already exists).
  R3. SUPPRESSION ACT, per-seat keyed; mechanism per Daniel's C2 verdict (pending at his
      gate: automatic outcome-reconciliation primary, reason field optional).
  R4. OVERRIDE GAUGE reads what R3 emits. (R2-R4 order = the fleet-debate reconciliation,
      REAFFIRMED by this round's concessions; R2 detail may adjust on R1's results.)

TRACK S (seat arc):
  S1. ROLE QUEUE + DURABLE CLAIM STATE, one slice. XREADGROUP; claim-TTL (stalled);
      claim-fence on SIDE-EFFECTING tasks only; freshness-TTL (drop-as-stale).
      AMENDED PER OUTSIDE REVIEW (codex/Sol via Daniel, 2026-07-28 ~01:53, verbatim relayed):
      claims do NOT land "in the mailbox" -- mailbox.py is DELIBERATELY a rebuildable
      observational projection (its own docstring: M0 observational only; rebuild() reports
      divergence as a determinism receipt, pin 3). Writing claims INTO it would destroy the
      rebuildability that makes it trustworthy. The permanent home is the layer BENEATH the
      replica: claim state = stream PEL (transport claims, native XREADGROUP) + a Store
      CAS-guarded fence record (the claim token kimi's side-effect fence checks -- Store.cas
      exists and is the write-integrity primitive). THE MAILBOX PROJECTS claim state; it
      never owns it. This preserves all three settled properties at once: permanent-home-
      from-day-one (X1, the Store/Ledger IS the home), build-writers-first (deepseek), and
      projection-stays-rebuildable (the mailbox's founding contract).
      Folds: the one-char governing-doc pointer fix.
      STANDING FIXES ALONGSIDE: sync-peek fix + T063 ack round-trip.
  S2. ROSTER / DIRECTORY (D1, the lobby): per-seat worklive heartbeats
      (bifrost:worklive:<agent>#<sid8>) + roster verb (seats, state, reachability,
      have-summaries) + W84 checked/NOT-checked render from day one. The reaper's sensor;
      the router's input. Directory carries NO payload (T5).
  S3. RESUME MARKER + INVALID-SESSION, named per Discord semantics ("replayed N, now live";
      invalid -> boot + seed-at-tail). Mostly exists; slice names it. Gates S4: resume-vs-
      invalid discrimination is what keeps a slow-but-alive seat from being robbed.
  S4. REAPER RE-HOME -- pin 2 (b323a04) flips green. Death signal from S2; target via S1;
      discrimination via S3. Re-homed asks carry ORIGINAL clocks (fence Q3 synthesis).
      The reaper is THE one re-homing writer (Law C, written in the design).
  S5. MAILBOX FULL HARDENING, last: manifest {part i/N, whole_sha} + INCOMPLETE render (T2);
      have-summaries complete (T3); verify-before-propagate on all propagators (T1);
      rarest-first durability ops (T4). The one-writer-per-family CHECKER lands here (Law C
      made mechanical).

CROSS-CUTTING (properties, not slices): W84 diagnostic contract on every new verb; Law B
(no in-place rewrite of shared structures) as review bar; deepseek/kimi runner call-site
migrations proceed in their own lanes.

SEQUENCING NOTE: R1 is a JUDGING task (reading + attribution); S1 is a BUILD. They do not
contend for the same kind of attention and run in parallel. After R1 + S1, the queue
re-converges at Daniel's next gate with the census results in hand.

## OUTSIDE REVIEW FOLDED (codex/Sol via Daniel, post-synthesis)

SECOND FOLD (Sol review 2, post-S1-ship): S1 amended TWICE, not once. (a) mailbox-as-
projection (first fold). (b) PEL-AS-TRANSPORT: XREADGROUP is at-least-once delivery, not
exactly-once execution; XAUTOCLAIM reclaims by idle time, not connection state (fence-doc
erratum recorded); the CLAIM GENERATION is the application authority -- P6 ABA pin committed
RED against the shipped code (b2eb4c6: a same-name reclaim cycle resurrected the original
stale claim), then generation fencing landed and all six pins are green. FileStore.cas
verified process-local (store.py:554) -> the role queue is Redis-authoritative and FAILS
CLOSED offline. External side effects ride durable idempotency (packet sha/idempotency_key)
or an outbox -- token-check-then-act is named insufficient.

Adopted: (1) the mailbox-as-projection correction above -- the one genuinely new technical
point, and it is right; (2) the SIX PLAIN INVARIANTS as slice-2's spec header, replacing
law-citation-per-line (one durable message identity | one current claim generation | one
directory of live seats | per-seat replicated views | lease expiry without message loss |
typed channel semantics) -- each slice justifies itself by ACCEPTANCE TEST, not analogy count;
(3) no further cross-share rounds -- the decision space is closed.
Owned: the "one queue" forcing error was the BRIEF's (claude wrote "one queue for the whole
fleet" into the ask), which manufactured a serialization debate over what were three
independent tracks -- the synthesis had already landed on parallel tracks, but the debate
spent rounds earning what a better brief would have given for free.
Held, with evidence: the prior art was not decoration THIS session -- it changed decisions
(freshness-TTL grounded kimi's fence position; the roster gap was found BY the sensor
framing; Discord semantics named S3's discrimination requirement). The go-forward discipline
codex names is adopted; the retrospective charge is half-right.

## WHAT THIS ROUND DEMONSTRATED (one paragraph, for the record)

Four halves, four clashes, two rounds, zero coin-flips: every disagreement resolved by
evidence or by a seat conceding to its own earlier words. The fork that looked deepest
(authority first vs last) dissolved into a two-layer build both authors endorse. The plan
survived contact with everyone -- which is the only kind of plan worth building.
