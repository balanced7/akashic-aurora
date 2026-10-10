"""core.link -- fleet links (RFC #70): Aurora's side of the aurora-linkd daemon.

The Rust daemon (aurora-rs/linkd) owns everything that touches keys or untrusted bytes: identity,
the ACL log, signed and sealed records, the per-link store and the network. This package owns what
touches agents, and nothing else:

- client.py      -- the JSON-RPC channel to the daemon (socket, or a one-shot child)
- rpc_types.py   -- the contract, generated from aurora-rs/linkd/openrpc.json
- quarantine.py  -- admitted records -> bifrost:remote:<link>, never an inbox
- promote.py     -- the local promotion policy (default: a person decides)
- export.py      -- bus mail with an @fleet/seat address -> our feed, under export.toml
- serve.py       -- `aurora link serve`: the supervised daemon plus the quarantine pump
- cli.py, panel.py, health.py -- the terminal, console and doctor doors
- legacy.py      -- the cutover: mail the retired HMAC bridge parked
"""
