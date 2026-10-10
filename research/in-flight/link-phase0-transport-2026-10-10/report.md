# Phase 0: the aurora-linkd transport spike, measured

Date: 2026-10-10. RFC: balanced7/akashic-aurora#70, addendum Phase 0 (replaced): spike `aurora-linkd`
on iroh 1.3's `Router`, with stdio JSON-RPC to Python, shipped as a wheel. The PyPI `iroh` binding is
the control measurement.

## Result

**Go.** The Rust daemon does everything Phase 0 asked for, and the binding could not have:

- **One accept loop, dispatch by ALPN.** `iroh::protocol::Router` carries four protocols on one
  endpoint: sync (`aurora/link/1`), join (`aurora/link-join/1`), iroh-gossip and iroh-blobs.
- **mDNS and relays.** Both are on by default; `--relay` points at a self-hosted relay.
- **stdio JSON-RPC to Python.** `aurora link serve` runs the daemon under `ManagedChild` with RPC
  on stdin and stdout, and the CLI uses its socket or named pipe.
- **Shipped as a wheel.** `akashic-aurora-linkd` is a py3-none wheel with the binary inside
  (9.7 MB on Linux x86_64). Installing it puts `aurora-linkd` beside Python.

The binding (PyPI `iroh` 1.1.0) exposes endpoints, connections and streams. It has no router, no
gossip and no blobs, as the addendum expected. On the same benchmark it is 6.6 times slower for
1 KiB messages and 50 times slower for 1 MiB ones (table below).

Alternative 2 (HTTP over Tailscale) is not needed as a fallback.

## Numbers

Machine: Linux 6.17 x86_64, Intel i9-7920X, 24 threads. Both endpoints in one process, release
builds. "Relayed" uses iroh's own relay server in process, with IP transports switched off on both
endpoints, so every byte goes through the relay.

| | connect (median of 20) | 1 KiB round trips | 1 MiB round trips | reconnect after a network change |
|---|---|---|---|---|
| Rust, direct (loopback) | 2.42 ms | 5,520/s (5.65 MB/s) | 179/s (187.6 MB/s) | 2.75 ms |
| Rust, relayed only | 2.79 ms | 2,415/s (2.47 MB/s) | 38.6/s (40.5 MB/s) | 2.60 ms |
| PyPI binding, direct (control) | 4.27 ms | 833/s (0.85 MB/s) | 3.5/s (3.71 MB/s) | not exposed |

A round trip sends the payload on a new bi-stream and reads back an 8-byte length.

What a link adds on top of the transport (two daemons in process, loopback):

| | |
|---|---|
| network join (fetch the log, hand over the join entry, take back the accept) | 32.9 ms |
| 200 records of 1 KiB, written by A until all are admitted at B | 778 records/s |
| 1 MiB attachment fetched as an iroh-blob | 13.1 ms |

The record rate includes signing, sealing, the ACL check, decryption and two SQLite writes per
record. Mail volume between fleets is many orders of magnitude below it.

## Through a public relay, with no direct path

Two real daemons on this machine, each started with `--relay-only` (`aurora-linkd serve --relay-only`
switches off every IP transport). So they can meet only the way two fleets on different networks
behind NAT do: through n0's production relay over the internet (`euc1-1.relay.n0.iroh.link`). Both
reported no IP addresses at all.

| | |
|---|---|
| network join, by invite code | 0.23 s (fingerprint matched the code) |
| a question, A to B | 0.10 s |
| a reply with a 1 MiB attachment, B to A | 0.04 s for the record; 15 s for the blob, mostly the fetcher's 15 s poll |
| B stopped, A wrote, B restarted | B caught up on reconnect, with no duplicates |

Run it with `python3 relay_only_internet.py <aurora-linkd> <scratch dir>` (it needs internet access).

## Three network stacks, and a mailbox on its own

`three_networks_docker.py` puts each fleet on its own network stack: A on this machine's LAN
(192.168.1.219), and B and a mailbox M each in a container on its own Docker bridge network (172.18.x
and 172.19.x) inside Docker Desktop's VM, behind its own NAT. Docker isolates the two bridges from
each other. The daemons run with their defaults: n0 address lookup, n0 relays, direct paths
wherever NAT allows.

| | |
|---|---|
| mailbox joins A's link over the network | 0.07 s |
| B joins over the network | 0.10 s |
| B offline; A sends a handoff with a 256 KiB file, then goes offline | the mailbox holds it at once |
| B back online, A still offline | B has A's mail in 0.2 s, and the file arrives intact |
| provenance at B | `fleet-a` (from the member log), seat claim `claude` |
| B replies, then goes offline; A comes back | A has the reply on reconnect |
| what the mailbox admitted | nothing: role `mailbox`, no read key, no events |

So mail and files flow both ways between two fleets that are never online together, through a
mailbox on a separate network stack that cannot read what it carries.

## What is not measured here, and where it is covered

- **Two machines owned by two people.** The runs above use separate network stacks and NATs (a VM's
  Docker bridges, and relay-only daemons through n0's public relay), on one physical host. The first
  real link between two fleets should post its `aurora link status` on the issue.
- **macOS and Windows.** CI's `link-os` job builds the daemon and runs the link tests, including
  the `ManagedChild` restart and the named-pipe RPC, on macOS and Windows. Windows is non-blocking
  until it has a green record, like the existing Windows smoke job.
- **A real network change.** `Endpoint::network_change()` simulates one. Reconnect stayed under
  3 ms on both paths.

## What the binding does not expose that a link needs

| needed | Rust iroh 1.3 | PyPI iroh 1.1.0 |
|---|---|---|
| Router: one accept loop, dispatch by ALPN | yes | no (only `accept_next`) |
| gossip | iroh-gossip 0.101 | no |
| blobs, with push disabled and gets gated | iroh-blobs 0.103.1 | no |
| mDNS lookup | iroh-mdns-address-lookup 0.6 | no |
| A refusal hook after the handshake | `EndpointHooks`, or a `ProtocolHandler` wrapper | no |
| Network-change notice | `network_change()` | a callback only |

## Reproduce

```bash
cd aurora-rs && cargo test -p aurora-linkd --release phase0 -- --ignored --nocapture
uv venv /tmp/pyiroh && uv pip install --python /tmp/pyiroh/bin/python iroh==1.1.0
/tmp/pyiroh/bin/python research/in-flight/link-phase0-transport-2026-10-10/control_pypi_iroh.py
```
