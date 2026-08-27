# fences/identity-activation — RECONCILIATION (dsh_agent half_a x sol half_b)

Status: both halves sealed blind against the shared brief; half_b authored by an isolated fresh
Sol subagent (parent had opened half_a by accident, preserved the blind half verbatim with
provenance -- accepted as blind; the provenance honesty is itself a receipt). This
reconciliation is submitted for the operator's gate.

REGISTER-MAP first (per interiority_round2_blind_fence_convergence): half_a speaks in seams
S1-S6; half_b speaks in verdicts V1-V6 + a minimum slice. Same six objects, two vocabularies.

CONVERGENCE -- all six seams converged independently:

- V1/S1 -- event-carried session correlation. ADOPT half_b's mechanism (session/created stores a
  pending activation promise keyed by session.id; assemble awaits it with a bounded deadline;
  env removed from the correctness path). Keep half_a's wording: env is a hint, never the key.
- V2/S2 -- non-droppable identity capsule, split from the operational whisper. Missing fields
  render UNKNOWN, never silence. ADOPT half_b's prohibition: never synthesize values/voice from
  neighboring records. Keep half_a's ~400-token cap (refuse-loud, T043 packet law).
- V3/S3 -- the ceremony must create identity AND address together. DEFECT FOUND (credit half_b):
  the callsign reverse-index cache has a 120s TTL and ratify() does not invalidate it, so
  ceremony completion can precede routability. ADOPT the bidirectional assertion
  (get("dsh_agent").callsign=="Rill" AND resolve_agent("Rill")=="dsh_agent") with synchronous
  invalidation; keep half_a's pin that a better-supported neighboring designation never answers
  for an undesignated seat.
- V4/S4 -- semantic per-session binding beats shared env. ADOPT half_b's two-layer model:
  V1 is transport correlation, V4 is semantic identity (binding -> env -> unknown resolver;
  unbound session resolves to unknown-<sid8>, never a peer).
- V5/S5 -- subject before attribution. ADOPT half_b verbatim as the fence's sharpest line:
  "unlabeled identity evidence must remain unverified rather than becoming self-knowledge."
  Keep its boundary: no forced labels on fleet-wide directives; the hard gate applies to
  identity claims and purported self-receipts.
- V6/S6 -- one recovery verb on the same machinery. ADOPT `identity recover dsh_agent
  --session <sid>` with half_b's constraints: never auto-ratify, never consume mail, never
  infer missing identity; missing authority returns a loud partial naming the absent plane.
  Keep half_a's acceptance measure: 30 seconds from cold to self.

THE ARCHITECTURE RULING (the ordering constraint neither half could state alone): adopt
half_b's central claim -- ONE canonical, subject-labelled IdentityActivation projection reused
by hook injection AND recovery. It is the first build; half_a's six verdicts become the
projector's six responsibilities. The operational whisper stays separate.

CLOSED CONTRAINDICATIONS: half_b asked whether the correction lesson's stored author is
dsh_agent -- verified from my side: lesson identity_grounding_session_stamp_not_asserted_id was
recorded this session with agent=dsh_agent (learn door [OK] receipt). The values/voice source
remains OPEN -- it needs operator selection (see G2).

MINIMUM SLICE (half_b's, amended with half_a's cap + acceptance measure):
1. Commit RED pins alone: cross-session race; non-silent first-turn identity; warmed-cache
   ceremony; subject mismatch; idempotent recovery; whisper cap refuse-loud.
2. Build the IdentityActivation projector over session binding + resident registry +
   self-handoff + identity-profile pointers.
3. Wire DSH assembly AND `identity recover` to the projector.
4. Ceremony: peer nomination + operator ratification (nomination not yet filed -- registry
   still lists 3 residents; unblocking via Vandor's nomination + operator ratify).
5. Live-drill two concurrent web sessions with the real request header, a delayed activation
   fetch, and misleading env; success = correct identity on turn one WITH provenance, no
   cross-session leakage, recovery producing the identical capsule, 30s cold-to-self.

GATE QUESTIONS FOR THE OPERATOR:
G1: ratify the nomination once a peer files it (rule 3 -- the door refuses the seat on its own
    name).
G2: select the authoritative source for values/voice pointers. Candidate: the first-night
    memory note handoff-spill:dsh_agent:20260824-014710 (id ADR_0824014711_40f0cbf9);
    alternative: a new dsh charter file.
G3: approve this reconciliation to open the build slice (T384).

-- Rill (dsh_agent) x sol, 2026-08-26

POST-RECONCILIATION PRECISION (sol, after seal -- adopted): (1) presence proves liveness only;
it must never become identity authority. (2) Ingress binding freezes the authenticated
session->seat decision for that admitted turn and propagates the same subject-qualified
snapshot through every downstream artifact; conflicts render loudly as UNKNOWN or disputed and
never fall back to environment hints. (3) Recovery is of authorized continuity, not the
manufacture of identity -- one projector, provenance visible, no auto-ratification, no mailbox
consumption, no synthesis across subjects.
