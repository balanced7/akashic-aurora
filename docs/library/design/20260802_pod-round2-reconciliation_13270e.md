---
akashic_id: art_20260802_pod-round2-reconciliation_13270e
akashic_sha: e9baaf05f3a0
schema_version: 1
status: current
type: design
date: 2026-08-02
title: pod-round2-reconciliation
gist: "# Pod round 2 — RECONCILIATION (at Daniil's gate) Status: current (2026-08-02, claude#30e6af5c). Synthesis of the two blind round-2 reviews "
visibility: fleet
body_type: markdown
seats: []
category: [method, conducting, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T03:45:23"
updated: "2026-08-02T03:45:23"
---
<!-- GENERATED PROJECTION of art_20260802_pod-round2-reconciliation_13270e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# pod-round2-reconciliation

# Pod round 2 — RECONCILIATION (at Daniil's gate)

Status: current (2026-08-02, claude#30e6af5c). Synthesis of the two blind round-2 reviews
(deepseek mechanism, kimi premise) over addenda 3+4 and the reconciliation. Supersedes
nothing; AMENDS the package. Dissents verbatim. NOTHING BUILDS BEFORE DANIIL'S WORD.

## HEADLINE

The package holds. Both reviewers independently upheld the topology ruling (one shared
pod, per-agent plugs). Two HIGH findings require design changes before slice-1; five
contradictions are all resolvable; one convener ruling had the right verdict for the
wrong reason and is repaired below.

## THE CONTRADICTION THAT ISN'T — and it completes a design

deepseek (M2): "Help is intentionally claimless. The role_queue pattern is the wrong tool
here. The board row itself is the coordination primitive."
kimi (P2): "Help is a claim, not a flag. Setting help_wanted acquires the pod's single
help-lease: one help per pod at a time."

These read as opposite and are not: deepseek reasons about the ANSWER side (two helpers
answering is redundancy, not collision), kimi about the ASK side (unpriced asking is the
beg-board). Blind, different lenses, they specify the two halves of one field:

  ASKING is leased   — one help_wanted per pod, a second asker must conclude the first;
                       the refusal is information ("help already in flight — join or wait")
  ANSWERING is claimless — CAS on help_answered_by, stale-answer timeout, many may answer

ADOPTED as the complete help design. Neither reviewer saw the other's half.

## HIGH-1 (deepseek M1): pod-scoped capability DOES NOT COMPOSE as written

Addendum 3 constraint 2 said "time-boxed entry in the EXISTING ACL keyed to pod id."
Traced against the code, three pieces are missing: the ACL has NO live-reload (trust
registry loads at process start); it is keyed by agent_id, not pod_id; and only claude
(super_admin) can write it, so nothing can provision a grant at pod entry.

Worse, deepseek found the ACL's expires_at field is null on EVERY active grant, deliberately:
the 07-05 incident had "the whole-grant time-box silently quarantine the entire admin role
at expiry — revoke by editing this record, never by expiry." So the design principle
across the house is revoke-by-editing, and addendum 3 proposed time-boxing into a system
that abandoned time-boxing on purpose.

ADOPTED FIX (deepseek's): a per-call pod-membership check at the EXISTING tool-dispatcher
gates (run_command / write_file / bifrost_send already gate separately), backed by a TTL'd
Redis key. The ACL stays the authority on WHAT an agent may hold; pod membership controls
WHEN. Process flags (--allow-exec) remain the coarse latch; the pod adds the FINE latch
that can close mid-process. Constraint 2's spirit survives (a TIME dimension on the
existing ACL, not a new capability source) but its LETTER is amended — this is not an ACL
entry.

## HIGH-2 (kimi P4): TEARDOWN-AS-GUILLOTINE

kimi, verbatim: "Addendum 3's receipt #2 ('everything acquired THROUGH the pod dies with
the pod — teardown is cleanup BY CONSTRUCTION') is precisely the hazard stated as a
virtue: cleanup-by-construction is only cleanup if nothing is still constructing."

The failure: an agent mid-write through a pod-granted capability is beheaded between byte
N and N+1 — half-written file, lock held through a grant that no longer exists, probe
process orphaned with its fixtures already reaped.

ADOPTED FIX, all three clauses load-bearing:
1. CONCLUSION IS TWO-PHASE: DRAINING then CONCLUDED. DRAINING freezes new grant
   acquisition and new pod-writes; the pod cannot reach CONCLUDED while any member
   position reports in-flight pod-granted work (tool counter moving on a pod capability,
   pod-scoped lock held, open pod-interior handle). Mechanically gated, same machinery as
   the resync-gate drain requirement.
2. TEARDOWN NEVER INTERRUPTS; IT REFUSES THE NEXT ACT. Expiry is checked at acquisition
   and act boundaries, never injected mid-act — the lease law applied to capability
   (matches how runner_lock TTLs already behave: expiry does not kill the process, it
   makes the next claimant legitimate).
3. THE ORPHAN RENDER: if an OS-level fact outlives CONCLUDED, it renders as
   orphaned:<pod-id> until reaped. "Construction-grade teardown plus invisible leftovers
   is the same class wearing a hard hat."
Plus: constraint 4's rebuild-by-construction must cover IN-FLIGHT STATE (DRAINING +
per-member in-flight fields are ledger events), "or a crash during teardown is a
guillotine with amnesia."

## HIGH-3 (kimi P2): help at alarm tier is a BEG-BOARD SUBSIDY

kimi, verbatim: "A help field that costs nothing to set and renders at alarm tier converts
private disorientation into fleet-wide alarm at zero price to the asker." Its own
fog-gauge lesson predicts who pays: the most disoriented seat, because noise is
compensatory. End-state is habituation — "the board trains its readers to discount red,
which is the fidelity ladder's capital being spent on fog."

Sharpest point: addressing help to the WORK genuinely kills the briefs-to-corpses class,
but it REMOVES the social cost that throttled asking (naming a peer obligates a peer) and
replaces it with nothing.

ADOPTED FIX: the lease above (scarcity), PLUS condition-driven retraction — help_wanted
clears when the asker's own tool counter moves (they unstuck themselves), a responder
joins, or the lease expires; NEVER by the asker remembering to unset it (the nine-hour
stale page is the receipt). PLUS: alarm tier renders ONLY while unanswered AND the asker's
telemetry is genuinely frozen. An ask from an actively-working seat renders one tier down.
This prices the ask against evidence — "help costs alarm tier only when the metal agrees
you are stuck" — which is the codebook doing the job it exists for.

## RULING REPAIRED (kimi P6): right verdict, wrong reason

kimi attacked the convener's own topology ruling, which had leaned on kimi's disease-class
framing as a veto: "a veto-by-classification proves too much: by that test the BOARD ITSELF
fails — board and ledger are two paths that must agree." Correct, and the repair is better
than the original:

  DISEASE CLASS (a) IS NOT "two paths exist." It is "two paths WRITER-AUTHORITATIVELY
  disagree with no derivation rule and no witness."

The verdict survives on the repaired reason: in two-pods-syncing, EACH pod is
writer-authoritative over the same logical state, neither derives from the other, and the
sync messages become a third path — "two AUTHORITIES with a hope between them." In
one-shared-pod there is one authority (pod ledger events) and N plugs that are membranes,
not replicas. THE LINE IS: PEERS RECONCILE, PROJECTIONS REBUILD. Adopted verbatim; it also
survives the next time someone correctly notes that board-and-ledger are two paths.

deepseek reached the same verdict independently by a different route: "the pod is Redis
keys with TTLs + ledger events; the plug is the runner process. They are different
substrates and different failure domains." Both blind, both upheld it.

## OTHER ADOPTED FINDINGS

- (deepseek M4) "THE PLUG ALREADY EXISTS" IS FALSE — it "undersells the work by a factor
  of 6." The membrane is the right seam but is agent-scoped throughout; six per-path
  additions needed (steer drain, hint push, nudge, write gate, exec gate, send
  addressing). Each small, none a new store. Addendum 4's language is amended to: "the
  plug is the existing membrane, EXTENDED with pod-id scoping on every channel."
- (deepseek M3) Pod-addressed steer: bifrost:steer:pod:<pod_id> + holder check at drain.
  Steers MUST carry a task_id so a new holder can verify "is this still my task?" before
  folding — otherwise a steer written for the old holder's dead context arrives coherent
  but nonsensical. Note: steer is in SKIP_KINDS, so it never wakes a seat — correct for
  fold-into-current-work, but it means steer-to-idle waits or expires (15-min TTL).
- (kimi P3) GATING ROTS BEFORE MISUSE: "the corpus is steering-STARVATION, not
  steering-abuse — unauthorized steering has ZERO incidents." The real rot is
  steer-into-heads-down: "steering that feels sent and is functionally queued behind a
  gate the sender cannot see." Fix: steer delivery state (queued/delivered/folded)
  rendered on the board. Authority: any pod MEMBER may steer the pod; membership IS the
  capability, no new ACL class.
- (kimi P1) THE INSTRUMENT LAW BINDS THE POD. Line drawn: MECHANICAL CONSEQUENCE
  (teardown, expiry, deferral, TTL enforcement) is free — already ratified at engagement
  accept, the pod originates nothing. ORIGINATED JUDGMENT ("not now," pod-filed artifacts,
  pod-carried handoffs) is a PROPOSAL: ledger-visible with full content ("deferred per
  term X, queue depth N, resync at turn T" — never bare "deferred"), superseded by the
  principal's own next act (no separate ack ceremony). And: every WITHHELD thing must be
  ledger-visible as withheld — "a pod that denies a capability and records nothing is sole
  witness to a decision."
- (kimi P5) Constraint 4 is INHERITANCE-BY-REFERENCE until three cheap fields exist:
  every pod row carries source_cursor (else rebuild-by-construction is unfalsifiable);
  BOOT RENDERS OPEN PODS, not just open engagements (the deal and the room are different
  objects; a fresh incarnation inheriting mid-engagement work needs the equipment
  visible); and POD EVENTS ARE THEIR OWN LEDGER SPECIES (convened/granted/revoked/
  draining/concluded/orphaned) or replay is "rebuild-by-hope."
- (kimi P5, credit) POD-AS-STABLE-OBSERVABLE is "the best idea in either addendum... the
  first mechanism in the whole design that REDUCES epoch ambiguity rather than inheriting
  it" — a pod has no incarnation to be ambiguous about.
- (kimi P6, new rot) THE EQUIPMENT COLUMN is the one pod-level field that is
  shared-mutable without an obvious single writer if both members can add equipment
  mid-engagement — "where blackboard rot re-enters the design through its newest door."
  v1 RULE: equipment is fixed at convene, immutable thereafter.
- (deepseek M6) FIVE CONTRADICTIONS, all resolvable: (1) ACL time-boxing vs no-live-reload
  → the Redis TTL pattern above; (2) cold-seat ledger-first WRITES vs O(1) membership
  READS → the existing task-ledger Redis-mirror pattern (writes from ledger events, reads
  direct); (3) incarnation_ref needs an agent_id companion for cross-agent pod rows;
  (4) help_answered_by ADVANCES COORDINATION STATE, so it is substrate, not projection —
  the board row carrying it must be ledger-first (the addendum never acknowledged this
  lane change); (5) THE POD IS BOTH SUBSTRATE AND PROJECTION and the addenda never draw
  the boundary — slice-1's "terms + positions + deferred queue, nothing more" accidentally
  draws it by limiting scope to substrate fields; the observation-scope and comm-channel
  uses are PROJECTION LAYERS ON TOP, and must be labeled as such.

## WHAT CHANGES IN THE BUILD ORDER

No reordering. Slice-1 pod scope is UNCHANGED (terms + positions + deferred queue).
Amendments land as constraints on the slices that were already sequenced:
- Slice 0/0.5 (sensors, codebook): unchanged.
- Slice 1 (board render): + gateway_coverage, + steer delivery state, + orphan rows.
- Slice 2 (position store): + source_cursor, + agent_id beside incarnation_ref, + pod
  events as a ledger species, + boot renders open pods.
- Slice 3 (engagement/pod v1): + two-phase DRAINING→CONCLUDED, + equipment immutable at
  convene, + help as lease-to-ask / CAS-to-answer, + per-call pod-membership gate at the
  tool dispatcher (this is where pod-scoped capability actually lands).
- Slice 4 (heads-down): unchanged, still last, still behind the operator-breakthrough
  kill drill.

## GATE DECISIONS (updated)

(1) Ratify names: GRAMMAR / ENGAGEMENT / POD / POSITION / BOARD.
(2) Ratify the REPAIRED topology reason: peers reconcile, projections rebuild.
(3) Approve build order 0→4 with the amendments above.
(4) Mint T-numbers (sensor+gateway, codebook, board+UI, position store, engagement/pod v1).
(5) Keys-in-gateway: yes/no/later.
(6) kimi spend: at ~$172 of $225 (hard refuse $203) — further kimi rounds are his call.
