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

## What is not measured here, and where it is covered

- **Two networks, through a public relay.** Not reproducible on one machine. The relayed row forces
  every byte through a relay, which is the slow path. The first real link between two fleets should
  post its `aurora link status` and `net.status` numbers on the issue.
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
