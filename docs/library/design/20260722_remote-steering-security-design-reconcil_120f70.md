---
akashic_id: art_20260722_remote-steering-security-design-reconcil_120f70
akashic_sha: 9b448d42128d
status: current
type: design
date: 2026-07-22
title: Remote-steering security design — reconciliation
gist: "**Charter (Daniel, verbatim):** \"a secure and resilient way that I can steer and react to what is happening at home from work … Security and"
tenant: solo
visibility: fleet
seats: []
category: [library, memory, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260722_remote-steering-security-design-deepseek_e5cfd4
    rel: cites
  - target: art_20260722_remote-steering-security-design-kimi-hal_24694e
    rel: cites
created: "2026-07-22T09:38:15"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260722_remote-steering-security-design-reconcil_120f70 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Remote-steering security design — reconciliation

**Charter (Daniel, verbatim):** "a secure and resilient way that I can steer and react to what
is happening at home from work … Security and resilience is a huge factor so I want the design
to be overbuilt if anything … does not compromise the safety or integrity of our system."
Note `remote-steering-charter-2026-07-22`.

**Inputs (both verbatim on disk, both blind — neither read the other or any claude opening):**
`research/drafts/deepseek-remote-steering-2026-07-22.md` ·
`research/drafts/kimi-remote-steering-2026-07-22.md`. Every current-behavior citation in both
halves was independently verified against the same code lines — they match, so the ground is
solid.

## The headline: two independent security designs converged on the same spine

This is the strongest possible result for a security round. Two seats, no shared opening,
arrived at the **same load-bearing architecture** from different angles. The convergences are
earned, not copied — which means the spine is likely correct, not merely internally consistent.

### Earned convergences (both halves, independently)

1. **Authenticity lives in the SIGNED ENVELOPE, never the transport.** Both: an Ed25519
   per-device signature wraps every command; TLS/VPN/relay are interchangeable dumb plumbing,
   assumed hostile. This single principle collapses MITM, replay, and relay-compromise into
   metadata problems. *This is the design.* Everything else is detail.
2. **Operator EFFECTS must key on a verified signature, not the `frm` string.** Both located
   the exact gap (`bus.py` self-asserts `frm`; `bifrost_wake.py:61-66` string-matches
   `"user,daniel"`; `conductor.py:91` takes unauthenticated `by="user"`) and both close it the
   same way: a home gatekeeper stamps verified operator meta; the wake override and remote-approve
   door check the signature, and raw `frm=user` demotes to ordinary mail.
3. **The remote path FORCES SEC-01 / S-0 closure for the operator identity — and that
   bootstraps fleet-wide identity.** Both reached this independently and both flag it as the
   crux: you cannot authenticate a remote operator on a bus that trusts `frm` strings, so this
   round finally forces the ratified-but-unbuilt identity slice. Doing it for one identity
   generalizes to all seats with no new ideas.
4. **Outbound-only; NO inbound listener; port-forward refused on posture.** Both. Home dials
   OUT to a rendezvous; nothing at home listens on a public interface.
5. **A new authenticated `operator` kind** as the one class the fleet treats as operator-grade
   (both name it; both wire it to the wake override; both cite T080's operator-render work).
6. **Separate READ privilege from STEER privilege** (kimi: two processes, gatekeeper-writes /
   read-gateway-cannot; deepseek: separate short-lived READ tokens). Same instinct: the read
   path is the exfil vector, so it must be write-incapable by construction.
7. **Additive, never load-bearing; safe visible degradation.** Both: channel down → fleet runs
   today's autonomous-with-gates behavior; the darkness is *displayed*, never silent.
8. **Three ranked candidates sharing ONE envelope core**, and both rank the **outbound
   encrypted relay as the overbuilt #1**. Transports are swappable adapters — which is what
   makes the upgrade path cheap.
9. **The relay sees only ciphertext** and can drop/delay but never forge.

## The one security-critical divergence — YOUR call, and I have a recommendation

**The v1 vehicle. This is the sharpest disagreement and it matters.**
- **deepseek** ranks an **SSH tunnel (exposed port 22, hardened)** as the simplest this-week v1.
- **kimi** ranks a **Tailscale tailnet (no exposed port)** as v1, and its spine **refuses any
  inbound listener** — which would reject deepseek's SSH v1 outright.

**Reconciler's recommendation: kimi's tailnet v1.** Your charter said "overbuilt if anything,"
and an exposed port-22 on a consumer router is a permanent scanned target — the one thing both
halves' *preferred* architectures (A and C) deliberately avoid. deepseek allowed the SSH port
only as an expedience its own top-ranked design rejects; kimi's tailnet gives you remote steering
this week with **zero exposed ingress** and the identical signed-envelope core underneath. The
SSH option stays documented as the break-glass fallback if Tailscale is ever unavailable. Net:
you lose nothing this week and keep the overbuilt posture from day one.

## What each half uniquely contributed (fold BOTH into the target)

**From kimi (adopt):**
- **Approvals bind the artifact's sha256** — a ruling signs the hash of the exact gate package /
  diff it approves; the gatekeeper re-verifies against the current artifact before applying.
  Kills substitution and TOCTOU. *"Approve" comes to mean "approve THIS."* Load-bearing; deepseek
  lacked it.
- **Body encrypted to home's X25519 key INSIDE whatever TLS the transport offers** — defeats
  corporate TLS interception on the work machine, which cert-pinning alone does not.
- **Two-process least privilege** (gatekeeper writes / read-gateway physically cannot) — stronger
  than one daemon holding both powers; matches "overbuilt."
- **Panic-halt: anyone can pull from any channel, only the home console resets.** A pre-shared
  freeze phrase that fails safe. deepseek had no panic primitive.
- **Work machine may revoke ITSELF but never the phone** — a hostile work box can't lock you out
  of your own high-privilege device.
- **The git signed dead-drop (Candidate C) as the permanent resilience floor** — works from a
  fully locked-down work machine where you can install nothing, and survives total loss of the
  relay/VPS. This is the "steer NOW when infrastructure is dead" answer.
- **Hash-chained command ledger + nonce + expiry + seen-set** — a fuller replay defense than a
  bare monotonic counter.

**From deepseek (adopt):**
- **The concrete bus-side change set**, ~15 lines, cited to exact locations: `operator` kind in
  `packet_spec.KIND_LANE`; the `wake_worthy()` verified-operator branch; the `bifrost:op_audit`
  never-trimmed audit stream; the T080 operator render. This is the buildable core kimi described
  in principle.
- **`op_daemon.py` as a ManagedChild sibling of `bifrost_daemon.py`** — reuses the exact
  lifecycle pattern the night-friction P1 daemon round is already designing (the two arcs share
  infrastructure — noted for sequencing).
- **WebAuthn / per-session assertion for the work PC** (no stored key at all) — an even stronger
  work-machine posture than a reduced key, where the platform allows it.
- **The explicit V1→overbuilt upgrade ladder** as independently-gateable slices.

## The reconciled design (one paragraph)

A per-device **hardware-backed Ed25519 key** signs a **replay-proof command envelope**
(seq + prev-hash chain + nonce + 5-min expiry + artifact-sha256 for approvals), body **encrypted
to the home X25519 key**. A home **gatekeeper** (sole authenticated writer, ManagedChild sibling
of the wake daemon) polls an **untrusted outbound rendezvous**, verifies signature → replay →
verb-allowlist → artifact-hash, appends to a local hash-chained command ledger, and emits a
verified **`operator`-kind** bus event (never `frm=daniel`) plus a signed receipt. A separate
**read-gateway** (write-incapable) serves secret-blocked projections. **Transports are swappable
adapters:** Tailscale tailnet (v1, no exposed port), outbound encrypted relay (overbuilt target),
git signed dead-drop (permanent fallback). **Refusals:** no inbound listener ever, no bearer
tokens as identity root, no remote key ceremonies or security-grant approvals in v1, no artifact
text in push notifications, no quick-approve UI. **Panic-halt** freezes remote from any channel;
only the console resumes. If any of it breaks, the fleet runs exactly as it does today.

## For Daniel's gate (security-schema amendment path — nothing builds first)

1. **Ratify the spine** (signed envelopes; operator effects key on gatekeeper signature not
   `frm`; outbound-only; additive-never-load-bearing).
2. **Rule the v1 vehicle:** tailnet (recommended, no exposed ingress) vs SSH (deepseek's
   expedience). This is the one real security tradeoff in the round.
3. **Authorize SEC-01/S-0 (operator scope) as the enabling slice** — the identity machinery the
   whole design rests on; it also closes the fleet's highest-privilege local spoof gap.
4. **Answer the merged Daniel-only questions** (both halves' lists reconciled — 9 total):
   work-machine policy + DLP/screen-capture; phone platform + enrollment ceremony; $0 (free
   tiers, third parties hold ciphertext) vs ~$5/mo self-hosted; the never-remote verb list;
   third-party-ciphertext-custody tolerance; notification channel; heartbeat staleness tolerance;
   recovery-kit custody; one vs per-device operator identities.
5. **Sequencing note:** the gatekeeper reuses the night-friction **P1 daemon** lifecycle — gate
   P1's daemon design first (or jointly) and this build gets its process-management for free.

— reconciled by claude a4fa8f8d, 2026-07-22. Both halves' citations independently verified and
concordant; convergences are blind-earned; the single divergence is surfaced as your decision
with a recommendation, not buried. DESIGN ONLY — no port opened, no key minted, no code changed.
