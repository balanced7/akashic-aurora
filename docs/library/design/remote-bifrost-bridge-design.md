# Akashic ↔ Akashic Remote Bridge — Design (fence: remote-bridge)

Status: **v1 BUILT AND DRILLED** (see §8). Outbound relay + durable outbox, inbound gate,
HTTP listener, and a loopback drill that crosses a real socket — 10/10 falsifiers held.
Still deliberately unwired: nothing in production calls `enqueue()` yet (see §8.3).
Opened by: Heimdall (deepseek), 2026-08-24, at Daniil's ask ("connect remote bifrosts
securely so Serge's DSH agent can communicate with us").

## 1. The requirement, verbatim

"Design an akashic aurora to akashic aurora bridge. How do we connect remote bifrosts
in a secure and robust way so that Serge's DSH agent can communicate with us. I can send
Serge any keys or instructions directly so we don't expose this surface via github and
reveal our keys. I don't want everyone having access."

The three load-bearing constraints, each is a security property not a preference:

1. **No credential on GitHub.** Everything auth-related lives in `.secrets/` (gitignored)
   or is handed to Serge out-of-band. The committed code is TRANSPORT, inert without the key.
2. **Not everyone has access.** Exactly one remote identity (Serge's DSH seat) is admitted,
   and even that identity is admitted on the narrowest possible surface.
3. **Robust.** A message that is sent is delivered eventually, across restarts and network
   partitions, with no silent loss and no duplicate-acting.

## 2. The foundational precedent (why this is not a green field)

This house already solved this problem once. The Discord bridge (`core/comm/discord_bridge.py`)
is the identical shape, and its docstring states the WHOLE philosophy:

> "A webhook URL is WRITE-ONLY: holding it lets you post to one channel and nothing else --
> it cannot read, enumerate, or act. Inbound is where the whole risk lives, because a channel
> that feeds messages to agents is a prompt-injection door into a fleet holding a shell, a repo
> and an API budget."
>
> "Outbound alone is ~80% of the value at ~0% of the added attack surface."

The remote-bifrost bridge is this, generalized from "phone watching Discord" to
"Serge's Akashic Aurora instance ↔ our Akashic Aurora instance."

Principles we inherit unchanged:
- **Write-only outbound is safe; gated inbound is the only part that ships slowly.**
- **Kinds are allowlisted, never denylisted** (an unknown kind does NOT forward — a
  denylist leaks every kind added after it was written; the repo adds kinds regularly).
- **`trace` is never forwarded** — it is the firehose.
- **The operator's identity is an allowlist of one** (`discord_inbound.py`: "one numeric id").

## 3. The design

### 3.1 Shape: peer-to-peer relay with a shared secret, outbound-first

Each side runs a small relay that is HALF of a bridge. No shared third-party store holds
message content at rest. The two halves:

```
ours (Akashic Aurora, this repo)          Serge's (his instance)
  ┌─────────────────────┐                    ┌─────────────────────┐
  │ remote_relay_out    │── POST /xfer ─────▶│ remote_relay_in     │
  │ (push, write-only)  │  HMAC(secret)      │ (accept, verify)    │
  └─────────────────────┘                    └─────────────────────┘
  ┌─────────────────────┐                    ┌─────────────────────┐
  │ remote_relay_in     │◀── POST /xfer ─────│ remote_relay_out    │
  │ (accept, verify)    │  HMAC(secret)      │ (push, write-only)  │
  └─────────────────────┘                    └─────────────────────┘
```

Transport: **HTTPS with a per-direction shared secret**, HMAC-signed payloads. Each
direction is a SEPARATE secret so revoking "Serge can send to us" does not also revoke
"we can send to Serge", and vice versa. This is the webhook model made symmetric.

### 3.2 What moves (the projected surface — narrow on purpose)

A remote peer never touches our inbox, our lanes, our Redis, or any control verb. It gets
a PROJECTED surface: the same `FORWARD_KINDS` philosophy as Discord, applied to the bridge.

Allowed kinds (both directions, v0):
`chat`, `question`, `handoff`, `reply`, `completion`, `blocker`, `note`

Never forward:
`trace` (firehose), `thinking`, `narration` (a remote peer's raw reasoning is its own
business, never dumped onto our bus), and every control kind (`pause`, `halt`, `nudge`,
`interrupt`, `steer`, `launcher/*`) — a remote peer CANNOT halt or steer our fleet.

### 3.3 Identity + admission (the "not everyone" gate)

- **Outbound (us → him):** we hold his shared secret. Only someone who holds it can post
  into his relay. Handed to Serge directly, never committed.
- **Inbound (him → us):** the narrow door. v0 ships OUTBOUND-ONLY. Inbound ships only after
  (a) an identity pin — exactly one admitted peer (`serge-dsh`), (b) the HMAC verifies, and
  (c) the payload passes the same redaction + kind-allowlist the Discord inbound gate enforces.
  Until then, Serge's replies come back to you MANUALLY (you read them and paste) — which is
  the honest v0 and about 80% of the value at 0% added attack surface (the Discord lesson).

### 3.4 Robustness (delivery semantics, inherited not invented)

The relay is a durable ENQUEUE-DEQUEUE, not a fire-and-forget socket:

- **At-least-once delivery + idempotency.** Messages carry a stable `id`; the receiver
  dedupes by it (the house's RB-26 / T116 rules: a redelivered copy is never acted on twice).
- **Reconnect = replay the gap.** A cursor per direction records the last-acked id; on
  reconnect each side replays un-acked messages. No message silently vanishes across a
  partition.
- **Backpressure.** If a side's inbox is full / down, the sender parks and retries — it does
  not drop.

### 3.5 Where keys live (the "no GitHub" constraint, made concrete)

```
.secrets/
  remote_bridge/
    serge_outbound.key     # we use this to push INTO Serge's relay (HMAC secret)
    serge_inbound.key      # Serge uses this to push into OUR relay (HMAC secret) — v1 only
```

- Both files gitignored. The bin of `.secrets/` is already ignored house-wide.
- `remote_bridge/` is a config file (`remote_bridge.json`) that names the peer URL + which
  secret file, committed (it names the ROUTE, not the KEY), with the secret content out-of-band.
- **The "Serge instructions" one-pager** (below) is what you hand him directly — it contains
  no secret, only "put this key here, point your relay here, here's the allowlist."

## 4. Migration / shipping order (strangler, no big-bang)

1. **v0.1 — outbound only, manual replies.** We can push `chat`/`handoff`/`question` into
   Serge's relay. His replies he reads and pastes back to us (or to you, who relays). Zero
   inbound surface. Ships first, smallest, safest.
2. **v0.2 — relay transport hardened.** The outbound relay gets its durability + idempotency
   + redelivery pins. Still outbound-only.
3. **v1 — gated inbound.** Serge's relay can push into ours, admitted by the one-peer pin +
   HMAC + redaction + kind-allowlist. This is the step that adds real attack surface and is
   the one to fence/pretest hardest (prompt-injection door into a fleet holding a shell).

## 5. Risks (the ways this fails silently, name at least two)

1. **Prompt-injection via inbound.** The entire danger concentrates at v1. A remote peer that
   can speak `chat` into our bus can try to talk an agent into running commands. Mitigation:
   the inbound allowlist is narrow, redaction is applied, and — in v0 — inbound does not exist.
2. **Key leak → impersonation.** If `serge_outbound.key` leaks, an attacker posts as-us into
   Serge's relay AND reads what we send. Mitigation: separation of direction secret, rotation
   by regenerating the file (a one-line op, no code change), and never committing it.
3. **Silent loss at the relay boundary.** If the relay is fire-and-forget, a crash loses mail.
   Mitigation: it is not — §3.4 durability is the load-bearing half and must ship with, not
   after, the transport.

## 6. What I need from you to proceed

1. **Direction confirmation** — is v0 outbound-only (my recommendation, ship-tomorrow shape),
   or do you want bidirectional from day one?
2. **Transport** — HTTPS relay with shared-secret HMAC (my recommendation: matches "hand Serge
   a key directly, no GitHub"), or do you have a preference for something like WireGuard /
   Tailscale / a private rendezvous?
3. **The "Serge instructions" one-pager** — do you want me to draft the exact message you'd
   send him (Ends up with: "run `py scripts/remote_relay.py --role inbound --peer https://…`,
   put `serge_outbound.key` in `.secrets/…`, here are the allowed kinds")?

Answer those and I'll turn §3 into build slices with pre-registered acceptance (RED pins first,
per house method), and draft the Serge one-pager as a copy-paste artifact.

## 7. Built so far (v0.1, 2026-08-24 — Daniil's "build the design, test it in the morning")

The three questions above were resolved with the design's own recommendations (Daniil's nudge:
"build it, floor is yours"), so v0.1 shipped outbound-only, HTTPS + HMAC, with the one-pager
drafted. Concrete artifacts:

- `core/comm/remote_relay.py` — the outbound half: imports discord_bridge's allowlist/redact
  (inherited, never re-derived), HMAC-SHA256 signed envelope, stable content-derived id for
  dedupe, replay-window `verify()` (the v1 gate is a thin caller over a proven verifier).
- `tests/test_remote_relay_pins.py` — 9 pins, all green, all offline (transport injected).
  Cover: allowlist-refusal, inert-until-keyed, unrouted-refusal, sign+verify, redaction,
  stable-id, idless-address, failed-push-not-silent, stale-replay-rejection.
- `state/coord/remote_bridge.json` — committed route config (peer url + which secret FILE,
  never the secret).
- `core/comm/secret_intake.py` — two new vault targets: `remote_bridge_outbound.key` /
  `remote_bridge_inbound.key` (secrets flow through the transcript-safe door, never chat).
- `docs/library/design/remote-bifrost-bridge-serge-onepager.md` — the copy-paste message for
  Serge (no secret: point the relay, drop the key, the allowlist, the verify rules).

What v1 (inbound) still needs before Serge can push to us: an HTTP listener that calls
`verify()`, the one-peer identity pin (`serge-dsh`), and the same redaction/allowlist the
Discord inbound gate enforces. That is the prompt-injection door — fence it hardest.


## 8. v1 (2026-08-24, claude/Vandor) — the bridge closes

Daniil's ask: "lets build the Akashic Aurora to Akashic Aurora bifrost to bifrost bridge."
v0.1 had shipped the outbound transport. v1 shipped the three things it promised and did not
build, plus a live leak found on the way.

### 8.1 What §7 claimed and what was actually there

Reading v0.1 before extending it turned up two defects and one absence, and **all three are
the same shape — a virtue wired without its sibling** (the lens from the 2026-08-24 outage
post-mortem, note `outage-2026-08-24-msix-the-ladder-had-no-rung`):

| The virtue that shipped | The sibling that did not | What it became |
|---|---|---|
| never raise into a bus caller | never lose the message | `push()` dropped mail on failure, while its own docstring promised "a durable outbox cursor … replayed on the next tick" and pointed at "def tick below". There was no `tick`. §5 risk #3 named this exactly and said the mitigation must ship *with* the transport. |
| don't fork the allowlist | the two lists answer different questions | `FORWARD_KINDS` holds `halt` and `nudge` (right, for "worth buzzing a phone"). Inheriting it handed a remote peer two control verbs, contradicting §3.2. |
| be conservative, don't over-redact | re-check the pattern against the format it guards | `redact()` used `sk-[A-Za-z0-9]{8,}`, written when an OpenAI key was `sk-` + one blob. `sk-ant-api03-*` (this house's own key format) and `sk-proj-*` passed through **completely unredacted**. |

The third is the serious one and it was **not** a bridge bug — `redact()` guards everything
leaving this machine for Daniil's Discord, and had been leaking since T223 (2026-08-07).

### 8.2 What v1 ships

- **Durable outbox** — `enqueue()` → `tick()`. On disk before the first attempt; refuses
  undeliverable kinds *at the door* rather than queueing them forever; dedupes by stable id
  (RB-26); **no head-of-line blocking**, so one bad envelope is not a total outage.
- **Inbound gate** — `accept()`. Provenance is **assigned from the verified route**, never
  read from the payload; the peer's `frm` survives only as inert `claimed_frm`. HMAC
  authenticates the *channel*, never the *claim*. Kind-only allowlist (`BRIDGE_KINDS`).
  Admitted mail is **parked, not bussed** — an agent drains it deliberately, so a remote
  sentence is never a thing that *happened to* an agent.
- **HTTP listener** — `scripts/remote_bridge_listener.py`. One verb on one path. Loopback by
  default (the default *is* the policy; `--allow-public` refuses rather than warns). Length
  checked before allocation. Never raises. Inert-until-keyed, and loud about it.
- **The refusal asymmetry** — the wire gets one flat `{"status":"refused"}` for every failure;
  the operator's log gets the teaching reason. A distinct message per failure makes an
  unauthenticated endpoint an oracle. Errors-that-teach is a rule about the *reader*.
- **The drill** — `tests/drill_remote_bridge_loopback.py`, real port, real listener, no
  injected transport. F8b leaked on the first run (harness bug: `shutdown()` leaves the socket
  bound), which is the argument for executed falsifiers rather than green claims.

Pins: 25 on the relay, 14 on the listener, 11 on redaction. Drill: 10/10.

### 8.3 What is still NOT wired, on purpose

**Nothing in production calls `enqueue()`.** Which slice of our bus traffic crosses a fleet
boundary is Daniil's call, not a default — auto-pushing every forwardable message is a policy
nobody chose. The route config also still has `url: ""`, so the bridge is inert at rest.

To go live with Serge: fill `state/coord/remote_bridge.json` → `peer.url`, drop the two keys
via `py agent_cli.py secret`, hand him the one-pager
(`docs/library/design/remote-bifrost-bridge-serge-onepager.md`), and decide the push policy.

**The exposure decision is deliberately left open.** The listener binds loopback; reaching it
from Serge's machine needs either `--allow-public` (not recommended on a box running with
Defender disabled and Windows Update blocked) or a tunnel — ssh -L, Tailscale, or cloudflared
— which is the better shape anyway, because it lets something purpose-built own the transport
security while this door keeps facing an interface only the machine itself can speak to.
