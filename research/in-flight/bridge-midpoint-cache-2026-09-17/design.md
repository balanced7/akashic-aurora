# A midpoint mail cache for the Akashic↔Akashic bridge (design, 2026-09-17)

Daniel's ask, verbatim: "figure out a schema for reliable mail caching in a midpoint so that we can
communicate even if one of the endpoints is down. Could we host it in a secure and nonhackable way
through akashiclabs.io?"

Design authority for the existing link: `docs/library/design/remote-bifrost-bridge-design.md`. This
extends that design; it does not replace it. Every property §3 of that doc calls load-bearing is kept.

## 1. The defect, demonstrated tonight rather than argued

The bridge today is a direct peer-to-peer link: each side runs a listener, each side holds a durable
outbox that retries. That survives ONE endpoint being down **while the other stays running**. It does
not survive the two being up at different times, and it never survives a sender that is powered off.

Tonight, 2026-09-17, all three failure modes were visible inside one hour:

- Our listener had been down since ~09-04. Thirteen days of their mail was refused at the wire — not
  parked. A mailbox behind a closed door captures nothing.
- Six minutes after I reopened our door, two of their messages arrived, one of them composed on 09-15.
  Their relay had been retaining and replaying correctly for two days. The transport worked; the
  schedule did not.
- Our three messages to them are queued at 3 attempts and cannot leave: their door is shut right now.
- **The file they offered is unreachable.** Blob transport announces a ref and serves the bytes FROM
  THE SENDER'S NODE, so `remote_bridge_fetch` needs the sender online at fetch time. Their playbook
  blob is sitting in our inbox as an unfollowable pointer. This is the sharpest instance of the class:
  the message arrived and its payload did not.

Two fleets on intermittent machines have an availability *overlap* problem, and a direct link requires
overlap by construction. A store-and-forward midpoint removes the requirement: each side talks to the
midpoint on its own schedule and never needs the other awake.

## 2. Shape

    fleet A  ──push──▶  MIDPOINT (dumb, deaf, durable)  ◀──pull──  fleet B
       └──────────── direct Tailscale link (kept, preferred) ────────────┘

**The direct path stays and stays first.** Try direct; fall back to the midpoint. Direct is faster,
private, and involves no third party — and every message that goes direct is one the midpoint never
sees, including in its metadata. The midpoint is a fallback and a cache, never a replacement.

**The midpoint is untrusted by construction.** This is the whole security argument, so it is stated as
a rule: *the midpoint must never hold anything it can read, and must never be able to forge anything.*
Today's HMAC gives authenticity but NOT confidentiality — correct for a direct link between two trusted
endpoints, fatal for a third party. So the first change is end-to-end encryption, independent of where
the midpoint is hosted or who runs it.

## 3. The schema

### 3.1 Inner message (only the recipient fleet can read this)

Unchanged from the existing bridge message, so nothing downstream has to learn a new shape:

```json
{ "id": "<stable id>", "frm": "vandor", "kind": "handoff",
  "content": "<text>", "sent_at": 1789700000,
  "blobs": [{"sha": "<sha256>", "name": "playbook.md", "bytes": 5693}] }
```

`kind` stays on the allowlist (chat / question / handoff / reply / completion / blocker / note). No
control verb crosses a fleet boundary in either direction, and because `kind` lives INSIDE the
ciphertext, the midpoint cannot even observe which kinds are flowing, let alone alter one.

### 3.2 Cache envelope (what the midpoint stores — this is all it can see)

```json
{
  "v": 1,
  "id":         "vandor-recall-truncation-20260917",
  "to":         "serge",
  "from":       "daniil",
  "seq":        42,
  "prev":       "vandor-reachability-findings-20260917",
  "created_at": 1789700000,
  "expires_at": 1792292000,
  "alg":        "x25519-xsalsa20poly1305/ed25519-v1",
  "nonce":      "<24 bytes, base64>",
  "ct":         "<base64 ciphertext of §3.1>",
  "sig":        "<ed25519 over canonical(header) || ct>"
}
```

Field by field, and why each one earns its place:

| Field | Purpose |
|---|---|
| `id` | Sender-assigned, stable. The idempotency key at every hop — re-deposit is a no-op, re-delivery is deduped on arrival. This is RB-26, already how the bridge behaves. |
| `to` / `from` | Routing only. Provenance is still assigned locally from the route and the verifying key, never read off the payload — the rule the current listener already enforces. |
| `seq` | Per (sender → recipient) monotonic counter. **Gap detection**: the receiver can say "I am missing 7". Today a dropped message is simply absent and nobody learns anything. |
| `prev` | The previous id on that pair. Chains the mailbox, so a gap is detectable even if `seq` is tampered with, and the chain is inside the signature. |
| `created_at` | Replay window. Reject outside ±N minutes (the current bridge uses 300 s). |
| `expires_at` | The midpoint's licence to delete. Bounded storage is a security property: a dead peer must not be able to fill the disk. |
| `nonce`, `ct` | The sealed body. |
| `sig` | Detached Ed25519 over the canonical header bytes **and** the ciphertext. |

**Why a detached signature when the box is already authenticated.** NaCl `Box` (X25519 +
XSalsa20-Poly1305) authenticates the *body* to the recipient. It says nothing about `to`, `seq` or
`prev`, which live outside the ciphertext because the midpoint has to route on them. A midpoint that
could rewrite `seq` or `prev` could silently erase a gap — hiding exactly the loss this design exists
to detect. The signature covers the header, so it cannot.

Padding: pad `ct` to size buckets (4 / 16 / 64 / 256 KB) before sealing. The midpoint learns a bucket,
not a length. Cheap, and it blunts the one thing the midpoint genuinely can observe.

### 3.3 Blobs go through the midpoint too

This is the fix for the unfollowable pointer sitting in our inbox tonight. A blob is content-addressed
by sha256, sealed with the same scheme, and PUT to the midpoint rather than served from the sender's
node. The ref stays the integrity check — a mangled transfer still refuses to write. The sender may
deposit the blob before, with, or after the message that announces it; the receiver fetches whenever it
next wakes, with nobody else online.

### 3.4 The API — four verbs, deliberately

```
PUT    /mbox/{to}/{id}     deposit one envelope     (idempotent; re-PUT of same id = 200, no-op)
GET    /mbox/{me}?after={cursor}&limit={n}          list envelopes addressed to me
DELETE /mbox/{me}/{id}     acknowledge              (only after a DURABLE local park)
GET    /health
```

Plus `PUT /blob/{sha}` and `GET /blob/{sha}` under the same auth. That is the entire surface. No
search, no enumeration of other fleets' mailboxes, no admin verb, no way to ask the midpoint who else
exists. A small API is not an aesthetic preference here; every verb is attack surface on a public host.

**Ack only after durable local park, never on receipt.** At-least-once delivery plus idempotency by
stable id gives effectively-once at the application layer, which is what the bridge already provides
locally and what makes a retry storm harmless.

## 4. What a compromised midpoint gets, stated plainly

Assume the midpoint WILL eventually be compromised; design so that it does not matter much. With the
scheme above, an attacker holding the midpoint entirely can:

- **See metadata**: who corresponds with whom, when, how often, and a size bucket. Traffic analysis is
  the one real disclosure, and padding plus the preferred direct path both shrink it.
- **Withhold or delete** undelivered mail — denial of service. Detectable: `seq`/`prev` gaps make a
  withheld message visible to the recipient rather than silent, which is the property today's bridge
  lacks entirely.
- **Replay** old envelopes. Defeated by id dedupe plus the `created_at` window.
- **Serve garbage**, which fails signature verification and is discarded at the door.

It cannot read a single message, cannot forge one from either fleet, and cannot inject a control verb —
the allowlist is inside the sealed body.

**On "nonhackable".** No hosted service is unhackable, and I would not ship a design that claims it.
The achievable and much better goal is a midpoint that is *not worth hacking*: breaking in yields
ciphertext, routing metadata, and the ability to annoy us. That is the bar this design is written to.

## 5. Hosting: the honest answer about akashiclabs.io

**akashiclabs.io cannot host this as it stands.** The site is an Astro **static** build deployed to
**GitHub Pages** (`.github/workflows/deploy.yml`, `withastro/action` → `actions/deploy-pages`). GitHub
Pages serves static files and cannot run server code at all. There is no backend to add an endpoint to,
so "host it through akashiclabs.io" means introducing new infrastructure and pointing a subdomain at
it — the domain can be used, the current hosting cannot.

Ranked, with the trade-offs that decide it:

**(A) Object storage behind `mail.akashiclabs.io` — recommended.** Cloudflare R2 or S3, per-fleet
prefixes, scoped credentials, lifecycle rule for TTL. The security argument is structural rather than
diligent: *there is no application to exploit.* No request parser, no auth code of ours, no process to
get RCE on — only a storage API maintained by a vendor with a security team. The four verbs map
directly onto object PUT/GET/DELETE and a prefix listing. The domain is ours, so the address is
`mail.akashiclabs.io` and the bytes never touch the site's host.

**(B) A third always-on node inside the tailnet.** A cheap VPS joined to Tailscale, running the
existing listener code with a mailbox role. Zero public exposure — the strongest posture available,
since an attacker must first be on the tailnet. Costs an always-on machine, and it is more of our code
running somewhere. Both fleets are already tailnet members, so this needs no new trust relationship.

**(C) A service on the site's host — not recommended.** It would mean standing up a server where none
exists, on our public face, and a compromise of the mail relay becomes a compromise of the box serving
akashiclabs.io. A public endpoint on a known domain is also scanned and probed continuously. If it is
ever done anyway: separate host from the site origin, own subdomain, own process, own credentials, no
shared state with the site.

Note: Serge's fleet sent us a Static Site Operations playbook at 19:53 tonight covering
"static + minimal-backend architecture behind a CDN tunnel", SSH hardening and two-front backups. They
have solved adjacent problems and it should be read before a final hosting choice. It is currently
unfetchable because their node is down — which is itself the argument for this whole design.

## 6. Shipping order (strangler, no big-bang)

1. **Sealed envelope on the existing direct link.** End-to-end encryption is worth having with or
   without a midpoint, and it can ship first with no new infrastructure: same transport, sealed body.
   Keys exchanged out-of-band, the same ceremony as today's HMAC secrets.
2. **`seq` / `prev` gap detection**, also on the direct link. This is the piece that would have told us
   on 09-05 that we were missing mail, instead of discovering it thirteen days later.
3. **Midpoint deposit/poll** as a fallback after a direct attempt fails, behind a config flag, off by
   default.
4. **Blobs through the midpoint**, retiring the pull-from-sender path.
5. Only then consider retiring anything.

Nothing here requires a new dependency: `cryptography` 46.0.7 and PyNaCl 1.6.2 are both already
installed and available in this environment.

## 7. Daniel's rulings (2026-09-17, on the §7 questions)

1. **Midpoint: object storage.** Behind our own domain, per §5(A).
2. **Blobs may ride the midpoint.** His words: *"yes for now, until i get my laptop up or we come up
   with a better idea."* So third-party blob storage is a provisional answer with a named exit, not a
   settled one — an always-on machine of his own would retire it.
3. **Retention: retire at 30 days, and retirement is not deletion.** His design, verbatim: *"we can
   either clear it manually later, or have it be pullable and requestable from local on demand. we
   could have a retire to local storage option and a request gets queued at the midpoint."*

   This is better than the TTL I proposed and it changes the model, so it is spelled out:

   - At 30 days an envelope is **retired**, not dropped: the owning fleet pulls the bytes down to local
     storage and the midpoint keeps a **tombstone** — id, to/from, seq, prev, created_at, the sha, and
     `retired: true`. The chain stays intact, so a retired message is still visible to gap detection;
     it is the BODY that moved, not the record.
   - A fleet asking for a retired body gets a **queued request** at the midpoint
     (`POST /request/{id}`), which the owning fleet drains on its next wake and answers by re-depositing
     the body with a fresh `expires_at`.
   - Consequence worth stating: this makes the midpoint a **cache, not an archive**, which is the
     property that keeps the storage bill bounded and keeps the durable copy on machines we own. It
     also means a request can go unanswered indefinitely if the owning fleet never wakes — so the
     requester must be able to see that its request is still queued rather than assume silence is a no.
4. **Begin now** with §6 steps 1 and 2 on the existing direct link, which need no infrastructure.

## 8. Still open

- Whether the retire-to-local step is automatic at 30 days or operator-triggered.
- Where retired bodies live locally (repo-adjacent store vs a blobs directory outside every checkout —
  note the filed lesson that per-worktree blob dirs make refs dangle across trees).
- Serge's fleet has not yet countered the schema; §6 order deliberately starts with the two steps that
  are useful to us whatever they answer.

## 9. Open decisions originally put to Daniel

1. **Which midpoint** — (A) object storage behind `mail.akashiclabs.io`, or (B) a tailnet VPS. My
   recommendation is (A) for the no-server-code property; (B) is stronger on exposure if you would
   rather nothing be reachable from the public internet at all.
2. **Whether the midpoint may hold blobs** as well as messages (it is the fix for the unfetchable
   file, but it means our shared files sit on third-party storage, encrypted).
3. **Retention** — 30 days and a per-mailbox quota is my proposal.
4. This design goes to Serge's fleet as a **proposal to counter**, not a decision. Chronos's fleet runs
   the other endpoint and should shape the schema before either side builds it.
