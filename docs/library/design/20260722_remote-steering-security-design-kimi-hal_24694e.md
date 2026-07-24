---
akashic_id: art_20260722_remote-steering-security-design-kimi-hal_24694e
akashic_sha: 61a589339061
status: draft
type: design
date: 2026-07-22
title: Remote-steering security design — kimi half (BLIND)
gist: "Blind declaration: written without reading deepseek's half or any claude opening. Every current-behavior claim below was verified against th"
tenant: solo
visibility: fleet
seats: []
category: [memory, security, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260722_remote-steering-design-brief-blind-halve_ffc9cc
    rel: cites
  - target: art_20260709_agent-security-schema-design-proposal_cdccf1
    rel: cites
created: "2026-07-22T09:33:59"
updated: "2026-07-23T21:42:10"
---
<!-- GENERATED PROJECTION of art_20260722_remote-steering-security-design-kimi-hal_24694e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Remote-steering security design — kimi half (BLIND)

Blind declaration: written without reading deepseek's half or any claude opening. Every current-behavior claim below was verified against the cited code line this morning.

---

## 0. Spine principles (the five everything else hangs from)

1. **The channel is always hostile; authenticity lives in the envelope, never the transport.**
   Every steer/ruling is a *signed command envelope* from a hardware-backed per-device key. TLS,
   VPNs, meshes, relays are interchangeable plumbing — any of them may be compromised without the
   design noticing, because none of them is trusted. This one principle dissolves most of the
   threat model (MITM, replay, relay compromise, exposed transport) and buys transport plurality
   (resilience) for free.
2. **Quarantine-by-default for everything inbound.** Remote input lands in a quarantine queue as
   inert bytes. Only a verifier (the *gatekeeper*) may promote an envelope to an effect. Unsigned
   or unverifiable content never becomes bus traffic, never reaches a seat's context, never
   touches the ledger. Seats never read the remote queue directly.
3. **Two-process least privilege at home.** A *gatekeeper* (the only writer) and a *read gateway*
   (no write capability at all) are separate processes with separate keys. The read path — the
   exfil vector — is read-only by construction, not by policy.
4. **Additive, never load-bearing.** If the remote path is down, muted, or actively hostile, the
   fleet runs exactly today's behavior (autonomous-with-gates). Nothing blocks waiting on Daniel;
   nothing degrades except Daniel's visibility — and that degradation is *displayed*, not silent.
5. **Approvals bind what was reviewed.** A ruling signature covers the sha256 of the artifact
   being approved (gate package, task entry, diff). The gatekeeper re-verifies the hash against
   the current artifact before applying the effect. This kills substitution and TOCTOU attacks
   and makes "approve" mean "approve *this*".

Non-goals (stated so reconcile can check me): physical access to the home machine, coercion of
Daniel, model/supply-chain compromise, and employer screen-visibility of whatever Daniel chooses
to display on a managed monitor.

---

## 1. Current state — verified citations (what we are actually standing on)

| Claim | Citation |
|---|---|
| Bus identity is a self-asserted string: `frm` is set to `self.agent_id` at send; nothing authenticates it | `core/comm/bus.py:293`, `core/comm/bus.py:359` (`env = {"frm": self.agent_id, ...}`) |
| Packet "integrity" is an *unkeyed* sha256 — corruption detection, **not** authentication; anyone can recompute it over tampered fields | `core/comm/packet_spec.py:96-100` (`compute_len_sha`), `core/comm/packet_spec.py:116` (`verify_integrity`), consumed at `core/comm/bus.py:626` |
| The operator override — the highest-value spoof target — is a plain string match: `AKASHIC_OPERATOR_IDS` defaults to `"user,daniel"`, and matching `frm` wakes any seat regardless of kind | `scripts/bifrost_wake.py:61-66` |
| The ledger's human gate is a CLI verb whose `by` is an unauthenticated string parameter | `core/coord/conductor.py:91` (`def approve(tid, *, by="user", ...)`) |
| The console binds loopback only and is documented "never exposed" | `scripts/bifrost_ui.py:522` (`--host default="127.0.0.1"`), docstring at `scripts/bifrost_ui.py:7` |
| Redis is loopback (localhost:16379); Redis auth is an unbuilt slice (S-6) | `core/foundation/redis_connection.py:51-80`, `docs/security-schema-proposal.md` §8/S-6, `docs/PORTS.md` |
| The security schema (quarantine-by-default, super-admin-or-human gates, time-boxed grants, audited events) is a ratified *proposal*; its identity slice S-0 (HMAC signing) is unbuilt — SEC-01 (`frm` unverified) is open | `docs/security-schema-proposal.md` (Status line; §1; §8 S-0) |
| Secret-material hygiene pattern already exists: `.secrets/` gitignored, and the tool layer hard-blocks `.secrets/`, `*.key/*.pem/*.crt`, `.env`, `id_rsa`, `credentials` unless explicitly overridden | `.gitignore:70-71`, `scripts/deepseek_chat.py:23-24` |
| No remote-access tooling exists anywhere in the repo (no tailscale/wireguard/ngrok/tunnel/push service) — the remote surface is greenfield | repo-wide grep, 2026-07-22 |
| The repo is public; nothing secret may land in git, including command contents | brief constraint; `balanced7/akashic-aurora` |

Two facts follow. **First**: today *any* local process that can XADD to the Redis stream can send
`frm=user` and wake the entire fleet — the operator channel is currently the weakest-authenticated
and highest-privilege path in the system. **Second**: the remote design cannot be bolted on
without closing SEC-01 for at least the operator identity — the remote path *forces* the identity
slice, and doing it for one identity bootstraps doing it for all (§6).

---

## 2. Threat matrix (threat → control → residual risk)

| # | Threat | Controls (this design) | Residual |
|---|---|---|---|
| T1 | Stolen/lost phone | Hardware-backed non-exportable signing key, biometric-gated per signature; per-device keys (revoke one, keep others); panic-halt callable from any channel (§3.4); auto-lockout of a device key after N verification failures; remote phone-revocation is home-console-only so a thief racing Daniel wins nothing by attacking the work machine | An *unlocked* phone in hand can sign until halted/revoked — bounded to steer-class verbs; gate approvals additionally require the artifact-hash display the thief must fake *and* (overbuilt) a TOTP. Low, time-boxed |
| T2 | Compromised work machine | Work machine gets a *separate, reduced-privilege* device key: read + comment-class steers only — never approvals, grants, enrollment, revocation. No secrets ever typed there. Assume screen/keystrokes/DLP visible: sensitive-projection mode for that device | Employer sees whatever Daniel displays (policy question → Q1). Envelope signatures are unforgeable from observed traffic. Content confidentiality on that screen: unsolvable by us, flagged |
| T3 | Channel MITM (incl. corporate TLS interception) | End-to-end: envelope signed by device key AND body encrypted to home's X25519 public key, *inside* whatever TLS the transport offers. Transport may be fully hostile | Metadata (timing, sizes, endpoints). Accepted |
| T4 | Replay of captured steers | Per-device monotonic `seq` + hash-chain (`prev` = sha256 of previous command; a gap alarms) + random nonce + 5-minute expiry + persisted seen-set at the gatekeeper | ~zero: a replayed envelope fails seq/prev/expiry even inside its window |
| T5 | frm-spoofing onto the bus | Operator-grade *effects* (wake override, remote approve) require the gatekeeper's own signature in bus meta — `frm` demoted to a display label for these paths. `bifrost_wake.py:_operator_ids()` string-match becomes insufficient on its own | Until full S-0 lands, *non-operator* frm spoof stays open locally (any seat can still claim to be another seat for ordinary mail) — scoped and documented in §6 |
| T6 | Prompt-injection via remote-delivered content | Inbound: unsigned content is inert quarantine data; seats never read the queue; the only thing with effects is a verified envelope (authenticity *is* the sanitization). Outbound (fleet→Daniel): push notifications carry opaque event IDs + severity only, never artifact text; the client renders all fleet text escaped, offers **no** quick-action buttons, and labels seat-authored text "treat as data" | Daniel himself socially engineered by crafted fleet text into signing something — mitigated, not eliminated, by the artifact-hash display at signing time |
| T7 | Exposed-ingress scanning | Zero inbound listeners in architectures A and C; tailnet-only binding in B. Port-forward ingress is *refused outright* (§4) | B: compromise of the Tailscale coordination account lets an attacker *reach* the gatekeeper port — where they meet envelope verification and fail. Reachable ≠ useful |
| T8 | Credential theft from client | No bearer tokens exist in the design. Device keys non-exportable (Secure Enclave / Android Keystore). Relay/transport credentials (the only copyable secrets) are scoped, low-value, and grant no operator authority | Jailbroken/rooted phone: key extraction via kernel exploit. Optional device attestation in the overbuilt target |
| T9 | Exfiltration via the read path | Read gateway serves *projections*, never raw filesystem: secret patterns hard-blocked per the existing tool-layer discipline (`deepseek_chat.py:23-24`); per-device projection scope (work machine gets the redacted set); responses signed by the home read-key so a relay can't substitute fabricated "all quiet" state | Legitimate-but-sensitive artifacts rendered on a hostile screen (T2). Rate of change of projection scope is audited |
| T10 | Availability attack on the channel | Fleet doesn't care (principle 4 — current behavior continues). Signed heartbeat every N min; client shows heartbeat age prominently (silence is a visible signal, not a quiet failure); overbuilt: second independent transport, notifications dual-pathed | Daniel blind/muted during the attack window. Accepted and *displayed*; never mistaken for fleet failure |
| T11 | Malicious/compromised seat luring a bad approval | Approvals bind artifact sha256; the client displays the hash + summary at signing time; gatekeeper re-verifies hash against current artifact before effect | Daniel approving without reading. Human factor; design makes the honest path the easy path |
| T12 | Rendezvous/provider compromise (relay holds the queue) | Relay sees ciphertext + timing only; forged/altered blobs fail envelope verification; availability attack → heartbeat staleness + fallback transport | Traffic metadata. Accepted |

---

## 3. Candidate architectures, RANKED

All three share the same home stack and the same envelope format — transports are adapters
(swappable without redesign, which is what makes the §5 upgrade path cheap).

**The command envelope** (identical in every candidate):

```json
{
  "v": 1,
  "device": "phone-1",
  "seq": 417,
  "prev": "sha256 of this device's previous envelope",
  "ts": "2026-07-22T17:04:11Z",
  "expires": "2026-07-22T17:09:11Z",
  "nonce": "random-128b",
  "verb": "ledger.approve",
  "args": {"task": "T080", "artifact_sha256": "…"},
  "sig": "ed25519(device-key) over canonical JSON of all fields above"
}
```

Closed verb set, deny-by-default. v1 verbs: `read.fetch` (implicit), `steer.note` (verified
operator bus message), `ledger.approve`, `panic.halt`. Everything else is added deliberately,
one verb at a time, each with its own gate in the security schema.

### 3.1 Candidate A — "Envelope-over-relay": outbound-only rendezvous, untrusted relay — RANK 1 (the overbuilt target)

**Shape.** Home runs the gatekeeper + read gateway (localhost services) plus a small forwarder
that *dials out* to a rendezvous (a $5 VPS running a ~100-line encrypted-blob queue, or a
managed queue — Cloudflare Queues / equivalent). Daniel's client (PWA on the phone) POSTs
encrypted signed envelopes to the relay; home polls/fetches; receipts and read projections
return the same way. Notifications ride a push topic (self-hosted ntfy on the VPS, or
equivalent) carrying opaque event IDs only. **No process at home ever listens on a non-loopback,
non-mesh interface.**

**End-to-end trust chain (finger on phone → operator event on the bus):**
1. Biometric unlock → Secure-Enclave/Keystore device key signs the envelope (key never leaves hardware).
2. Envelope encrypted to home's X25519 pubkey → HTTPS POST to relay. Relay is *untrusted*: it stores ciphertext.
3. Home forwarder polls out (no listener), pulls the blob, hands it to the gatekeeper as inert bytes.
4. Gatekeeper: schema check → ed25519 verify against enrolled device pubkey → replay checks (seq > last, prev-hash matches chain head, nonce unseen, not expired) → verb in allowlist → for approvals, `artifact_sha256` matches the *current* artifact → append to the local append-only, hash-chained **command ledger** (contents stay local; only chain-head hashes may be published) → execute via the verb's narrow door (verified-operator bus send, or the conductor's signature-checked remote-approve door) → emit a **signed receipt** `{cmd_hash, effect, ts}`.
5. Bus consumers of operator-grade effects (wake override, remote approve) require the gatekeeper's signature in message meta — never the `frm` string.
6. Receipt rides the read path back; the client displays effect-vs-intent.

**Ops burden, priced:** VPS $5/mo (or managed-queue free tier) + quarterly patching of a dumb
relay that holds no secrets and can be rebuilt from scratch in an hour; ntfy optional; one-time
enrollment ceremony ~15 min at the home console (device pubkey + recovery kit printed); home
services auto-start via Scheduled Task with a watchdog. Estimate: one evening to stand up after
the gated build, ~1 h/month to own.

### 3.2 Candidate B — "Private mesh, still signed": Tailscale tailnet + the identical envelope core — RANK 2 (the v1 vehicle)

**Shape.** Home, phone (and optionally work machine) join a Tailscale tailnet; ACLs pin the
gatekeeper/read-gateway ports to Daniel's devices. Same home stack, same envelopes, same
verification — WireGuard transport *under* message-level signatures, two independent layers.

**Trust chain:** identical to A with step 2–3 replaced by "envelope POSTed over WireGuard to the
gatekeeper's tailnet-only port." The signature chain (steps 1, 4, 5, 6) is unchanged — tailnet
membership is *reachability*, never *authorization*.

**Ops burden:** lowest of the three — Tailscale free tier, ACLs configured once, no server to
patch, no CGNAT/port-forward fights. The full home stack (gatekeeper, gateway, ledger, receipts)
is still required; B is cheap in *transport*, not in *skipping the security core*.
**Cost of the cheapness:** a new trust dependency — the Tailscale coordination account (2FA'd
Google/MS login). Its compromise grants reachability to the gatekeeper port, where forged
envelopes still fail. Acceptable for v1; A removes the dependency.

### 3.3 Candidate C — "Signed dead-drop": async command mailbox via private git repo — RANK 3 (the resilience floor; permanent fallback under A)

**Shape.** Daniel commits signed envelopes as files to a *private* repo (or a dedicated mailbox
equivalent); home polls every 60s, verifies, effects, commits signed receipts back. Git itself is
the audit trail.

**Trust chain:** identical envelope and gatekeeper stages; transport = git push/poll. Latency is
minutes, not seconds.

**Ops burden:** near zero; works from *any* device that can reach a browser — including a
locked-down work machine where installing anything is impossible. **This is also the answer to
"the relay/VPS is dead and I need to steer NOW"**: C survives the total loss of A's
infrastructure, which is why it stays in the overbuilt target as the fallback path rather than
being discarded.

### Why not inbound (the refused fourth)

A hardened inbound listener (WireGuard or mTLS reverse proxy behind a router port-forward) was
considered and rejected: a permanent scanned target on a consumer router, CGNAT fragility,
Windows host exposure, and a standing violation of the no-exposed-ingress posture — in exchange
for *nothing* the outbound designs don't already provide. WireGuard's silent-drop property makes
it the least-bad inbound option if A/B/C ever all become impossible; that day is not in view.

---

## 4. What the design REFUSES (No is information)

**Candidate A refuses:** any inbound listener, anywhere; any verb outside the closed set;
command *contents* in git (hashes only — the repo is public); trusting the relay for anything
but storage-and-forward.

**Candidate B refuses:** treating tailnet membership as authorization (envelopes still required);
full-privilege keys on the work machine.

**Candidate C refuses:** interactive steering, sub-minute latency, anything needing liveness.

**Global refusals (all candidates, all versions):**
1. **No bearer tokens as the root of operator identity.** Anything copyable is not Daniel.
2. **No remote key ceremonies.** Enrolling a device, revoking the *phone*, rotating operator
   keys, and resuming from panic-halt happen at the home console or not at all. (The work
   machine may revoke *itself*; it may never kill the phone — a hostile work box must not be
   able to lock Daniel out of his own high-privilege device.)
3. **No remote security-grant approvals in v1** (security-schema escalations/grants stay
   home-console; the overbuilt target may admit them under dual-signal: phone key + TOTP).
4. **No artifact content in push notifications** — IDs + severity only. The phone fetches
   details over the authenticated read path.
5. **No quick-approve UI.** Every approval shows the artifact hash and requires the explicit
   signing flow. Convenience that bypasses the ceremony is an attack feature.
6. **No fleet dependency on the channel.** No gate, seat, or runner may block waiting on a
   remote response. The remote path informs and steers; it never carries the fleet's weight.
7. **Panic-halt is easy to pull and hard to reset.** Anyone (even an unsigned pre-shared panic
   phrase from any channel) can freeze all remote operations; only the home console resumes
   them. Attackers can at worst mute Daniel — which the fleet survives by principle 4.

---

## 5. Minimal SAFE v1 (this week) vs the overbuilt target

**V1 is not a toy.** The signature core — envelope format, gatekeeper, command ledger, receipts,
artifact-hash binding — ships in v1 at full strength. What v1 skips is *redundancy and second
factors*, never *verification*.

| Component | Safe v1 (this week) | Overbuilt target |
|---|---|---|
| Transport | B (Tailscale tailnet) | A (outbound relay) primary + C (dead-drop) fallback |
| Device keys | Phone only, hardware-backed, one key | Phone (full) + work machine (read + comment-class) + attestation where the platform allows |
| Verbs | `read.fetch`, `steer.note`, `ledger.approve` (artifact-hash-bound), `panic.halt` | + `grant.approve` (dual-signal), `fleet.mode` (pause/resume lanes), rotation verbs |
| Second factor for approvals | Artifact-hash display at signing | + TOTP (enrolled at console, independent of signing key) |
| Notifications | Push topic, IDs+severity only, single path | Dual-path (relay + dead-drop), heartbeat watchdog alerts Daniel's client when the *heartbeat itself* goes stale |
| Replay defense | seq + prev-hash + nonce + expiry + seen-set | same + cross-device chain-head cross-check |
| SEC-01 closure | Operator-identity scope: gatekeeper-signed meta required for operator effects (`bifrost_wake.py` operator override and the remote-approve door check it; raw `frm=user` demoted to ordinary mail) | Full S-0: per-agent signing keys for the whole fleet per `docs/security-schema-proposal.md` §8 |
| Lockout | N failed verifications → device key quarantined + console banner | + auto-notification to surviving devices + graded response (steer-freeze vs full remote freeze) |
| Read path | Projections, secret-blocked, phone-scope | + per-device scopes, sensitive-projection mode for the work machine, read-audit sampling |

**Upgrade path (v1 → target) without redesign:** add the relay adapter beside the tailnet adapter
(same envelope), enroll the work-machine key at reduced scope, enroll TOTP, stand up the
dead-drop poller, extend S-0 from operator-identity to all seats. Each step is an independent,
separately gateable slice — none invalidates anything v1 built.

**Safe degradation ladder (what failure looks like, by layer):** relay down → tailnet/dead-drop
still steer; all remote down → fleet runs current behavior, client shows DARK by heartbeat age;
gatekeeper process dead → remote dark, fleet fine, watchdog restarts it; suspected compromise →
panic-halt freezes remote, fleet fine, resume at console.

---

## 6. What this implies for the LOCAL path (the SEC-01 tail)

The brief asks for the honest implication: **you cannot authenticate a remote operator while the
bus trusts `frm` strings.** Minimum closure, v1 scope:

1. The gatekeeper holds its own signing key; its bus injections carry `meta.operator_sig` over
   the message body.
2. `scripts/bifrost_wake.py:_operator_ids()` (lines 61-66) stops being sufficient alone: the
   wake override requires a valid `operator_sig`; raw `frm=user` mail still delivers, but as
   *ordinary* mail — no always-wake, no operator render.
3. `core/coord/conductor.py:approve(by=...)` gains a signature-checked remote door; local
   console approval (physical presence is its own factor) is unchanged.
4. This *is* the security schema's S-0 slice, scoped to one identity — the machinery
   (`.secrets/agent_keys/`, sign-at-emit, verify-at-consume, fail-closed to quarantine per
   `registry.resolve(..., verified=False)`) then generalizes to the fleet with no new ideas.
   Recommendation: once the operator path proves the pattern, land full S-0; every month it
   waits, the local spoof gap (any seat as any seat) stays open underneath the hardened remote
   door.

---

## 7. Open questions only Daniel can answer

1. **Work-machine policy**: may personal/fleet traffic touch the managed machine at all? Are
   employer root certs / DLP / screen capture in play, and does that relegate it to read-only —
   or to nothing?
2. **Phone platform** (iOS/Android) and willingness to do a biometric enrollment ceremony at the
   console — determines PWA-with-WebAuthn vs thin native client.
3. **Cost tolerance**: $0/mo (Tailscale + Cloudflare free tiers, third parties hold ciphertext
   and metadata) vs ~$5/mo self-hosted VPS relay (fewer third parties, one more thing to patch)?
4. **The never-remote list**: my defaults — device enrollment, phone revocation, security-grant
   approvals (v1), resume-from-panic. Ratify, or move items?
5. **Third-party trust floor**: is a managed queue / private GitHub holding *encrypted* blobs
   acceptable, or must every rendezvous be self-hosted from day one?
6. **Notification channel preference** given IDs-only content: ntfy topic, email, or other?
7. **Heartbeat cadence/staleness tolerance** — how dark is DARK before the client alarms?
8. **Recovery-kit custody**: the printed recovery key (phone-loss resume path) lives where?

---

## 8. Summary for reconcile (the load-bearing claims to test)

- Authenticity lives in signed envelopes, not transports → MITM/replay/relay-compromise collapse
  to metadata problems.
- Operator *effects* must be keyed on a gatekeeper signature, not `frm` — the remote path forces
  SEC-01 closure for the operator identity, and that slice bootstraps full S-0.
- Approvals bind artifact sha256 → substitution and TOCTOU die at the signature.
- Three candidates, one envelope: relay (target), tailnet (v1), dead-drop (permanent fallback);
  inbound port-forward refused on posture.
- v1 ships the full verification core and defers only redundancy/second-factors — no throwaway
  phase.
- Panic-halt: anyone can pull, only home can reset. Remote is additive, never load-bearing.
