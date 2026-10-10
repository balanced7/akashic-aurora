# Phase 0b: adopt or build (p2panda-spaces, -auth, -encryption 0.7.1)

Date: 2026-10-10. RFC: balanced7/akashic-aurora#70, addendum §2 point 6 and Phase 0b.
Scope: whether `p2panda-spaces`, `p2panda-auth` and `p2panda-encryption` 0.7.1 can be the membership and
encryption layer of `aurora-linkd`. Our stack: iroh 1.3.0, rusqlite 0.40.2 (plain SQLite), and our own signed
record envelope with JCS headers.

The spike crate is in `spike/` next to this file (`cargo test --test convergence`, `cargo test --test spaces`).

## Decision

**Build `acl` as the RFC specifies. Do not adopt p2panda-spaces 0.7.1.** The rule was "adopt only if all six
hold". Two hold, three hold only in part, and one does not hold.

The group CRDT in `p2panda-auth` is sound: a proptest over 20,000 random concurrent histories found no
divergence. Its data-encryption mode rotates the group secret on removal, as it should. The layer that ties the
two together, `p2panda-spaces`, is not ready to sit behind a network-facing daemon:

- Two valid wire messages crash every receiver: a `SpaceUpdate`, and any `Promote` or `Demote` from a manager.
  Both reach `unimplemented!()`. Both are reproduced. Under our `panic = "abort"` plus restart, the daemon would
  replay the same record and loop.
- It forces `sqlx` 0.8.6 into the build, and `sqlx` cannot link next to rusqlite 0.40.2.
- Access levels are only half enforced: a `Read` member can publish, and its messages are accepted.
- Consensus rules and stored formats change between minor versions, and more breaking changes are queued.

We copy two designs anyway (see "What we borrow"). Look again at 0.8 or later, once the panics are gone and the
store is decoupled.

## Verdicts

| # | Criterion | Verdict | Reason |
|---|---|---|---|
| 1 | Version its wire format behind our envelope | Partially | It imposes no transport or signing, so its messages fit inside our records. But the payload has no version, the rules change between versions, and two valid variants panic the receiver. |
| 2 | Storage fits SQLite or can be adapted | Partially | The store traits are small get/set blobs, easy to back with rusqlite. But `p2panda-spaces` hard-depends on `sqlx` 0.8.6, which cannot link next to rusqlite 0.40.2. |
| 3 | Pull-only role | Partially | `Pull` members get no keys and cannot decrypt (tested). But a level cannot change after a member is added: `Promote` and `Demote` panic the receivers. `Read` against `Write` is not enforced. |
| 4 | Data encryption rotates keys on removal | Holds | Every removal makes a new secret that only the remaining members receive. Old secrets stay in a bundle, so history stays readable, also for members who join later (tested). |
| 5 | Concurrent removals converge | Holds | 8 hand-written scenarios under every causal order, plus a proptest of 20,000 random DAGs times 6 orders each: no divergence. |
| 6 | The 0.6 to 0.7 churn is tolerable | Does not hold | The API port was small. But spaces did not exist in 0.6, consensus and stored formats changed, and more breaking changes are queued. |

## The six criteria

Paths are relative to `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`.

### 1. Wire format behind our record envelope: partially

What fits:

- p2panda-spaces does not sign, send or order anything itself. We supply a `Forge`
  (`p2panda-spaces-0.7.1/src/forge.rs:10-24`) that returns our own message type.
- It leaves signature checks to us: `SpacesMessage::verify` is `unreachable!` (`message.rs:41-43`). So our signed
  record can be the message, `SpacesArgs` (`message.rs:151-218`) an opaque payload in it, and our record hash its id.
- The author must be an Ed25519 key and the id a 32-byte BLAKE3 hash. Both fit.
- It needs causal delivery before `process` (`manager.rs:55-59`); `SpacesArgs::dependencies()` gives the edges.

What does not:

- **Remote panics.** A received `SpacesArgs::SpaceUpdate` reaches `unimplemented!()` at `manager.rs:274`. A
  received `Promote` or `Demote` passes p2panda-auth validation and then reaches `unimplemented!()` at
  `event.rs:249-250` (also `event.rs:297-298` and `space.rs:455` when a key set changes). Upstream `main` still has
  the `SpaceUpdate` one.
- **No payload version.** `SpacesArgs` is a bare serde enum. The persisted state says
  `// TODO: Introduce versioning and more efficient encoding.` (`store.rs:24`).
- **A version tag would not buy coexistence**, because the rules change: 0.7 lets a non-manager remove itself
  (`p2panda-auth-0.7.1/src/group/crdt/state.rs:254`) and a 0.6 peer refuses that. Mixed versions would compute
  different memberships.
- The unreleased changelog lists "Deterministic deserialization of `SpacesArgs` (#1264)" as a fix.

### 2. Storage: partially

- `Manager` needs one store implementing five traits plus `Transaction` (`manager.rs:77-83`), about 11 async
  methods, almost all get/set of one CBOR blob. A rusqlite adapter is roughly 150 to 250 lines.
- **The blocker:** `p2panda-spaces` depends on `p2panda-store` with `["sqlite","spaces"]`, which pulls
  `sqlx` 0.8.6 and `libsqlite3-sys` 0.30.1. rusqlite 0.40.2 needs `libsqlite3-sys` 0.38.2. Both declare
  `links = "sqlite3"`, so Cargo refuses the build. The ways round it: pin rusqlite 0.32.1, fork spaces without the
  store, or drop spaces and write its 2.5k lines of glue ourselves.
- The group state keeps a full membership snapshot per operation (`p2panda-auth-0.7.1/src/group/crdt/mod.rs:98`),
  re-encoded as one blob on every write. Fine at fleet scale, unbounded growth.
- `p2panda-auth` and `p2panda-encryption` alone build fine next to iroh 1.3.0 and rusqlite 0.40.2.

### 3. Pull-only role: partially

| p2panda level | Meaning | Aurora role |
|---|---|---|
| `Pull` | "Permission to sync a data set" (`access.rs:19`); left out of key distribution (`p2panda-spaces-0.7.1/src/utils.rs:39-46`) | Mailbox |
| `Read` | Gets group secrets | Reader |
| `Write` | Meant to publish | Writer |
| `Manage` | Changes membership (`crdt/mod.rs:527`) | Owner, admin |

- A `Pull` member received no keys and never saw plaintext, but held ciphertext it could re-serve. This part
  matches our mailbox.
- There is no promote or demote API in 0.7.1, and receiving one panics (`event.rs:249`). So a mailbox can never
  become a reader without remove and re-add.
- A `Read` member published, and the owner accepted and decrypted it: `handle_application_message` has no access
  check (`space.rs:463-487`). The fix (#1295) is unreleased.

### 4. Rotation on removal: holds

- `EncryptionGroup::remove` makes a new `GroupSecret` (`p2panda-encryption-0.7.1/src/data_scheme/group.rs:143-150`),
  sent by 2SM to every remaining member (`data_scheme/dcgka.rs:207-229`).
- Secrets carry an id and a strictly increasing timestamp (`group_secret.rs:248-257`); senders use the latest.
- New members get the whole bundle in a welcome (`dcgka.rs:249-269`).
- Test: after Carol's removal, `secret(m1) != secret(m2)`, Bob read m2, Carol got "unknown group secret", and Dave,
  added later, read both.
- Caveats: re-delivering one record emitted its plaintext twice (we dedupe by id anyway); messages from a
  concurrently removed member are not filtered in 0.7.1 (#1291, unreleased).

### 5. Concurrent removals converge: holds

Our own test drives `p2panda_auth::group::GroupCrdt` with the `StrongRemove` resolver.

| Scenario | Orders | Agreed members |
|---|---|---|
| A, B, C manage, D reads. A removes B, B removes A | 2 | C manage, D read |
| Only A, B manage. A removes B, B removes A | 2 | D read (**no manager left**) |
| A removes C, B removes C | 2 | A, B |
| A removes B, B adds E (manage), E removes C | 3 | A, C (B's branch invalidated) |
| Cycle A removes B, B removes C, C removes A | 6 | D read (everyone in the cycle is out) |
| A rm B, B rm A, C rm D, then C adds E | 6 | C manage, E read |
| A demotes B, B removes A | 2 | C only (**the demotion becomes a removal**) |
| A removes C, B removes C then re-adds C | 3 | A, B (the re-add is filtered) |

The proptest generates up to 13 random steps over 6 actors, keeps only operations valid against their own causal
past, and replays each DAG in 6 random causal orders: **20,000 cases, 0 divergences** (release build, about 60 s).
On 2,000 DAGs, 51% had concurrent siblings and 39% a mutual removal.

The two bold rows are design choices, not bugs, but the first is a real risk: two last managers removing each
other leave a group nobody can manage.

### 6. Churn from 0.6 to 0.7: does not hold

- `p2panda-spaces` was first published at 0.7.0, so there is no spaces upgrade to try.
- Porting a minimal 0.6.1 program of auth and 2SM to 0.7.1 took 3 compile rounds, 5 errors and 6 changed lines
  (`spike/port-0.6-to-0.7.diff`).
- What the port does not show: 13 breaking items in that minor step. Two change consensus or the wire: non-managers
  may now remove themselves, and the core header changed (`seq_num` and `payload_size` to u32, `version` to u16,
  `timestamp` removed, strict canonical CBOR on decode).
- The unreleased changelog already lists more: spaces API changes, deterministic decode, write-authority checks,
  sqlx 0.9 in the store, and a `Signer` trait in core.
- The changelog does not match the crates: the `src/` trees of auth, encryption, core and store are identical
  between 0.7.0 and 0.7.1.

## Other findings

| Item | Finding |
|---|---|
| MSRV | 1.96 for all p2panda 0.7.1 crates; iroh 1.3.0 is 1.91. Adopting would raise the daemon's MSRV. |
| Dependencies | iroh plus rusqlite: 242 unique crates. Adding auth and encryption: 296. |
| iroh | No conflict; these crates do not depend on iroh. |
| Duplicate crypto | `ed25519-dalek` 2.2 beside 3.0, and Cryspen `hpke-rs` beside the RustCrypto `hpke` the addendum picks. Two HPKE implementations in one daemon goes against premise P2. |
| Licence | MIT OR Apache-2.0. No AGPL in the tree. |
| Audit | None. The p2panda-encryption README says it has not had a security audit. |
| Advisories | None for p2panda. `cargo audit` flags RUSTSEC-2023-0071 (`rsa`) only in the lockfile, via sqlx-mysql. |

## What we borrow

Both are now in `aurora-rs/link/src/acl.rs`.

1. **Validate each operation where its author stood.** p2panda-auth admits an operation only if its author had the
   right in the state computed from the operation's own causal past (`crdt/mod.rs:521-527`). Our ACL now checks an
   entry twice: against the state along its own `prev` chain, and against the merged state when it is applied. An
   entry that was never valid is dropped, and one that lost its authority to a concurrent change is dropped too.
2. **Removals beat what they race, and the owner is the one identity nothing removes.** p2panda's strong-remove
   filters every operation concurrent with a removal of X that X authored. Our order gets the same result:
   at a fork, removals apply before other operations at the same depth, and each entry is re-checked against the
   merged state, so X's concurrent entries fail. Unlike p2panda, mutual removal between admins cannot happen here:
   only the owner may remove an admin, and nobody may remove the owner. That avoids the "no manager left" case in
   the second scenario above.

Also kept from p2panda-encryption: the readers are every member at `reader` or above, recomputed after each entry;
every removal rotates; and the previous key is sealed under the new one, so a member with the current key reads
all history. And from the probes: `Write` is enforced when a record is opened, and no decoded variant is ever
`unimplemented!()`. Every ACL op and frame type has a handler, and the fuzz targets feed all of them.

## How to reproduce

```bash
cd research/in-flight/link-phase0b-adopt-or-build-2026-10-10/spike
cargo test --test convergence -- --nocapture --test-threads=1
CASES=20000 cargo test --release --test convergence -- --nocapture
cargo test --test spaces -- --nocapture --test-threads=1     # the rotation test and the panic probes
cargo add rusqlite@=0.40.2 -F bundled                        # fails: two crates link sqlite3
```
