# link-vectors

Test vectors for the fleet-link formats (RFC #70). They are the reference for any second reader
of these formats. There is no second implementation of the protocol: Python calls the same crate
through the `aurora_rs` wheel and checks itself against these files.

| file | what it pins |
|---|---|
| `records.json` | A sealed record, its retired header, and tampered variants that must be refused. |
| `fingerprints.json` | The root a fixed recovery phrase derives, its fingerprint, and a safety number. |
| `invites.json` | Invite codes that parse and codes that must be refused. |
| `acl-fork.json` | An ACL log forked by the owner and an admin; every arrival order resolves alike. |

The phrase in `fingerprints.json` is the public BIP39 test phrase. Never use it for a real fleet.

Regenerate with `AURORA_WRITE_VECTORS=1 cargo test -p aurora-link --test vectors`, and review the
diff: a changed vector is a changed wire format.
