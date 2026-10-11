# link-vectors

Test vectors for the fleet-link formats (RFC #70). They are the reference for any second reader
of these formats. There is no second implementation of the protocol: Python calls the same crate
through the `aurora_rs` wheel and checks itself against these files.

| file | what it pins |
|---|---|
| `records.json` | A sealed record naming an ACL chain position `{term, seq, hash}`, its retired header, and tampered variants that must be refused (a changed position, one without a hash, term 0, and the round-4 list of heads). |
| `fingerprints.json` | The root a fixed recovery phrase derives, its fingerprint, and a safety number. |
| `invites.json` | Invite codes that parse and codes that must be refused. A code names the hash of the ACL entry that issued its invite (`invite`). |
| `acl-chain.json` | An ACL chain (format 2): genesis by the owner's first device (term 1's sequencer), a device add, an invite, a join (a proposal signed by the joining device, with its expiry, its invite proof bound to the issuing entry and the proposal's nonce), its accept, a handoff to the owner's second device and a term-2 entry; then the owner's root takes over on the first device as term 3. The two term-2 entries the lost sequencer appended after the takeover point (`dropped`) come with it: in any arrival order they never apply, or apply and are dropped when the takeover arrives, and every replica ends at `tip`. Every certificate carries its device's proof of possession (`pop`). |
| `acl-equivocation.json` | Two entries the term-1 sequencer signed at one position (`a`, `b`) on one prefix: a replica holding either halts at the common prefix when it sees the other. |

The phrase in `fingerprints.json` is the public BIP39 test phrase. Never use it for a real fleet.

Regenerate with `AURORA_WRITE_VECTORS=1 cargo test -p aurora-link --test vectors`, and review the
diff: a changed vector is a changed wire format.
