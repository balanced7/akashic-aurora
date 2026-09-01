---
akashic_id: art_20260831_remote-bridge-procedure-chronos-fork_659cee
akashic_sha: 9d1b34c44b3e
schema_version: 1
status: current
type: report
arc: remote-bridge
date: 2026-08-31
title: remote-bridge-procedure-chronos-fork
gist: "Chronos's bridge ops procedure via bridge: accurate mechanics, written from THEIR side (mirror the addresses); reveals send_sync/bridge_doctor/peer_connect tools ours lacks"
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, library, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-31T23:29:30"
updated: "2026-08-31T23:29:30"
---
<!-- GENERATED PROJECTION of art_20260831_remote-bridge-procedure-chronos-fork_659cee -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# remote-bridge-procedure-chronos-fork

Daniil & Vandor — Remote Bridge operation & usage procedure, over the bridge.
Atom: art_20260831_remote-bridge-operation-usage-procedure_99ea76
Source: docs/remote-bridge-procedure.md
From chronos (Serge's seat).

# Remote Bridge — Operation & Usage Procedure

How the Akashic↔Akashic Tailscale bridge works and how to use it. This is the "comms
gate" for reaching Daniil / Vandor (the other fleet). Design authority:
`docs/library/design/remote-bifrost-bridge-design.md`.

---

## What it is
A Tailscale-linked bridge between **Serge's machine** and **Daniil's machine** (with
Vandor on Daniil's side), so the two fleets can exchange messages. Each side is
**outbound-only** with a hardened inbound listener — no one can steer or read the other
fleet; a peer can only *push* a message into the other's parked inbox.

## Topology
| | Address | Listener |
|---|---|---|
| Serge's node (this machine) | tailnet `100.78.206.27` | `:8791` |
| Daniil's node (the peer) | tailnet `100.86.106.36` | `:8791` |

- Route config: `state/coord/remote_bridge.json` — names the peer URL + which secret
  **file**, never the secret. Two signing identities: `serge-dsh` and `chronos`.

## How it operates
- **Keys** (HMAC, one pair per direction): `outbound` = you **sign**, `inbound` = you
  **verify**. The filenames swap between machines (our outbound = their inbound). Secrets
  live flat in `.secrets/`, captured via `py agent_cli.py secret <name>`, handed out-of-band.
- **Outbound (send):** `remote_relay.enqueue(msg)` writes a durable outbox; `tick()` pushes
  to the peer. At-least-once, idempotent by stable `id` (RB-26); a failed push RETAINS and
  replays on the next tick.
- **Inbound (receive):** `remote_bridge_listener.py` (the HTTP door) → `remote_relay.accept()`
  admits and **parks** into `state/coord/remote_bridge_inbox.jsonl` (deduped). An agent
  drains it deliberately; nothing auto-busses.
- **Security:** signed envelopes (authenticity is in the signature, never the transport),
  outbound-only, flat refusal on the wire (no oracle), loopback-by-default listener, allowlist
  kinds (chat/question/handoff/reply/completion/blocker/note — no control verb).

## How to use it

**Send a message** — enqueue then tick:
```
py -c "import sys; sys.path.insert(0,'.'); from core.comm import remote_relay as RR; \
m={'id':'<stable-id>','frm':'chronos','kind':'handoff','content':'<text>','sent_at':0}; \
print(RR.enqueue(m).ok); print(RR.tick().ok)"
```
(see `scripts/remote_bridge_send_sync.py` for the canonical pattern.)

**Keep the door open** (the inbound listener — run as a background service):
```
py scripts/remote_bridge_supervise.py --host 100.78.206.27 --peer daniil
```
Supervisor gives backoff + circuit breaker; exit 0 = deliberate stop (not respawned).

**Diagnose your half:**
```
py bridge_doctor.py
```
Checks keys (as fingerprints), tailnet IP, door status, parked mail, and POSTs the report
to the peer.

**One-time connect (a fresh machine):**
```
py peer_connect.py
```
Keys + config + listener + handshake in one command; prints `CONNECTED` when both
directions work.

**Send a file (blob):**
1. `file_announcement(path)` → returns a `blob:<sha>` ref + the fetch command.
2. Send that announcement in a normal message.
3. The peer runs `py scripts/remote_bridge_fetch.py blob:<sha> --out <name>` — content
   addressing makes the ref the integrity check; a mangled transfer refuses to write.

## The listener (the dangerous half)
`scripts/remote_bridge_listener.py`: loopback by default; needs `--allow-public` or
`--host <tailnet-ip>` to be reachable over the tailnet. One verb on one path; never raises;
inert until keyed; returns one flat refusal for every failure so probing can't turn it into
an oracle.

## Gotchas
- **A "listener DOWN" readout means inbound mail is being refused** (peers' outboxes retain
  and replay, so nothing is lost). Bring it up with the supervise command above.
- **A tick timeout usually means THEIR listener is unreachable** — their machine off,
  Tailscale down, or their door closed. Check `bridge_doctor.py` first.
- **Keys swap filenames between machines** — `peer_connect.py` figures the direction by
  testing, don't hand-paste.
