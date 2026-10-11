# Fleet links: composition review brief (2026-10-11, round 9)

**This brief reflects round 9.** Four rounds of clean-room review each found new critical or high
issues in the multi-parent DAG membership log, and the fifth concluded that the design was not
converging: in a DAG an author picks its entry's parents, so it picks what the entry is
"concurrent" with, and every rule that read time or precedence from a missing causal edge became a
weapon. The membership log is now a **linear chain ordered by one sequencer** (section 4). Record
sync stays multi-writer. [findings.md](findings.md) lists every finding of rounds 1 to 5, with its
fix and the test that pins it; its "Round 5" section explains the redesign and maps each earlier
attack class to why the chain rules it out. Round 6 hardened the chain's halt: evidence must apply
on its own, a halt narrows what a replica grants and never folds it back, and an old sequencer's
key below a later term is an alarm, not a veto ("Round 6" in findings, and 4.5 here). Round 7
bounded every input an attacker controls and charged it to its origin: evidence is kept once per
position and signer and checked at most once per batch, relays keep only what holds on their
chain and a refusal costs the proposer, not the relay, and a halt no longer cuts the transport of
a device added past the prefix ("Round 7" in findings; 4.3, 4.5 and 7 here). Round 8 found no
critical or high issue. It charges an origin once per proposal however often it is replayed. It
budgets the record side of a session (wants, `heads` pages, the bytes sent and received) and keeps
each device's budgets across its sessions. It gives each link its own lock ("Round 8" in findings;
4.3, 4.5 and 7 here). Round 9 found no critical or high issue either. It makes honest record
catch-up resume within a session, counts every frame and the records sent for disputed heads, and
keeps a busy link's lock off the daemon's async workers ("Round 9" in findings; 4.3 and 7 here).

**Read first, if you review this from outside:**

1. Section 0, for what a link is.
2. Section 4, membership: the chain, proposals, terms (handoff and root takeover), equivocation,
   and what the sequencer is trusted for. It is the newest code and replaces everything earlier
   rounds reviewed there.
3. Section 10, the questions we most want answered. The first eight are about the chain.
4. Section 5.3, records naming a chain position, then section 7, range sync and its budgets.
5. Section 6, key ids and wraps, and section 8, the local trust boundary.

Do not spend time on findings already fixed unless you think a fix is wrong. Section 11 lists where
the docs and the code still disagree.

This brief covers how the primitives are put together. It does not argue that the primitives
themselves are sound. Every claim points at the code. Where the docs and the code disagree, the
code is taken as the truth.

- **Snapshot:** branch `fix/link-composition-review` in the `link-review` worktree, as of
  2026-10-11: `d9faa07b` (fork `s1-f0/aurora`, `master`), then the review rounds; round 5 starts
  after `23eeea92`, round 6 after `a05cdf98`, round 7 after `6bcf9449`, round 8 after
  `2ae025c1`, round 9 after `72a68838`. Paths are relative to the repo root. Sections 4, 5.3, 7 and 10 name functions
  (`file: function` or `Type::method`), not lines. Elsewhere, `file:N` means line N at round 1;
  those lines may have drifted, and each pointer also names its function or constant.
- **Size:** `aurora-rs/link/src` is about 14,800 lines with tests and `aurora-rs/linkd/src` about
  4,600. The protocol core is `acl.rs` (3,288 lines, 2,109 more in its tests), `engine.rs`
  (1,883), `sync.rs` (1,567) and `record.rs` (652).
- **Tests at the snapshot:** `cargo test --workspace` passes: 127 unit tests in `aurora-link`
  (four property tests, also run at 600 cases in release), 5 vector tests, and 19 in
  `aurora-linkd` (17 pass and 2 are ignored, measurements). The seven Python link test files pass
  against the wheel and the debug daemon, 177 tests (findings, Round 9).
- **What changed in round 9:**
  - Records that could not be stored are asked for again when that can help: at once when the
    chain they waited for arrives, at the first `ping` after the tip moved, after a gap at the
    next `ping`, and once the hourly quota admits more (`Admit::OverQuota`) (7).
  - Records sent for a head the peer names with another id count against the 16 MiB record
    budget, and each claim is answered once a minute across the peer's sessions (7).
  - Every frame counts against 2,400 a minute per (link, peer), pings and `records` frames
    included. Membership is a lookup in device sets kept per held tip (7).
  - The daemon waits for and holds a link's lock off its async workers. `peer_links` reads a copy
    of each link's devices without any link's lock (7).
  - An origin's charge for a proposal is remembered until the proposal expires (4.3).
- **What changed in round 8:**
  - A proposal's origin is charged once per proposal a day, however often it is replayed, and a
    peer's charges are kept apart from its fleet's charges as an origin (4.3).
  - Record wants, `heads` pages, `synced` and adverts count against 120 frames a minute.
  - A session sends at most 16 MiB of records a minute in answers, and looks at most at 32 MiB of
    the records its peer sends. An answer cut short ends with `synced { more }`, and the asker
    asks again.
  - `Store::range` reads at most what it sends.
  - A device's budgets are kept per link across its sessions, and a device opens at most 10
    sessions per link a minute.
  - Each link has its own lock in the daemon.
  - `settled_above` is one kept bound per signer and term (4.5).
  - Records are indexed by author and arrival time, for the hourly quota (7).
- **What changed in round 7:** a replica keeps at most one evidence pair per position and signer,
  one alarm-only pair per signer and a halt only below the one it has, decides that before any
  check, runs at most one evidence check per insert and charges each to the session, keeps at most
  256 pairs, and checks only the halt's pair again on a restart, so a halt at the next position
  survives one (4.5); a self-started later term settles evidence once the owner's fleet or another
  member has removed or demoted the signer's device (4.5); while halted, the transport and the
  chain's own frames read the held state, so the evidence and the takeover reach a device added
  past the prefix (4.5, 7); relays keep only what holds on their chain, joins only on a live
  invite, and a refusal is charged to the proposal's origin (4.3); only the current sequencer's
  refusal is taken (4.3). Store schema 8 (evidence pairs).
- **What changed in round 6:** evidence counts only if each entry applies on its own (4.5); a halt
  keeps the held state and narrows what the replica grants to what the prefix grants too, and
  nothing is sealed while halted (4.5); evidence below a later term begun by a takeover or by
  another member is an alarm only (4.5); a takeover continues after the held tip by default (4.4);
  only the sequencer at a refusal's position refuses (4.3); proposals carry an expiry, are void on
  a base before the latest takeover, have a size cap per kind, and are kept only from members (or
  proven joins), with refusals charged to the session peer (4.3); `MAX_ENTRY_BYTES` is 512 KiB and
  a link has at most 32 members, so its largest entry fits (4.1); `acl_done` asks again only when
  the tip moved (7). Store schema 7.
- **What changed in round 5:** the ACL is a chain (4.1), proposals carry other devices' actions to
  the sequencer (4.3), terms move by handoff or root takeover (4.4), equivocation halts the chain
  (4.5), clock rules read the sequencer's `ts` (4.6), records name one chain position (5.3), sync
  pulls bounded ranges (7), and linkd caps sessions per peer and link and closes idle ones (7).
  Store schema 6, ACL entry format 2, record version 2, ALPNs `aurora/link/2` and
  `aurora/link-join/2`.
- **Earlier rounds, in one line each:** round 1 made resolution causal and added key ids, signed
  record times, padded blobs, the gated join door and the private RPC socket; round 2 made entries
  multi-parent; rounds 3 and 4 patched the DAG's pruning, settling, forks, claims and stubs, and
  added proofs of possession. Only the last survives in membership.

## 0. What a link is, in one paragraph

A **fleet** is one organisation's set of machines (its "devices"), all under one Ed25519 **root**
derived from a 24-word phrase. A **link** is a shared space between fleets. Its membership is an
append-only, signed, hash-linked **ACL chain** with one order, fixed by the link's **sequencer**
device; other devices' changes reach it as signed proposals. Its id is the hash of the chain's
genesis entry.
Each device writes its own signed, hash-chained **feed** of records. Record bodies are sealed under
the link's symmetric **read key** for the current **epoch**. That key is HPKE-wrapped to each
reading device in the ACL chain, and the chain names a public **key id** for it. Devices sync over
iroh (QUIC with raw-public-key TLS, where the node id is the device's Ed25519 key). Any member
relays any other member's records. A **mailbox** member stores and forwards ciphertext but never
gets a read key. A Rust daemon (`aurora-linkd`) holds every key and parses every untrusted byte.
Python talks to it over local JSON-RPC and alone decides whether an admitted record ever reaches
an agent ("promotion").

## 1. Primitives and crate versions

Versions are from `aurora-rs/Cargo.lock`. Manifests: `aurora-rs/link/Cargo.toml`,
`aurora-rs/linkd/Cargo.toml` (iroh crates are pinned with `=`).

| Primitive | Crate (locked) | Used for | Where |
|---|---|---|---|
| Ed25519, `verify_strict` | `ed25519-dalek 3.0.0` (`curve25519-dalek 5.0.0`) | Every protocol signature. Device keys also serve as the iroh node key | `crypto.rs:91-100` (`sign`, `verify`); key reuse `linkd/src/net.rs:472` |
| X25519 KEM (HPKE DHKEM(X25519, HKDF-SHA256)) | `hpke 0.14.1`, `x25519-dalek 3.0.0` | Wrap suite 1, which every device has | `crypto.rs:231-256` (`wrap`) |
| X-Wing KEM (ML-KEM-768 + X25519) | `hpke 0.14.1`, `x-wing 0.1.1`, `ml-kem 0.3.2` | Wrap suite 2, an *outer* layer around suite 1 | `crypto.rs:231-256`, `258` (`unwrap`) |
| HPKE KDF / AEAD | HKDF-SHA256 / ChaCha20-Poly1305 (inside `hpke`) | Both wrap suites, single-shot, mode **Base** | `crypto.rs:243` |
| XChaCha20-Poly1305 | `chacha20poly1305 0.11.0` | Record bodies, blobs, the sealed previous key, the sealed root. Random 24-byte nonce prefixed | `crypto.rs:113-140` (`seal`, `open`) |
| SHA-256 | `sha2 0.11.0` | `record_id`, `ct_hash`, ACL entry hash (= link id for genesis), **key id**, **blob key hash**, invite-key derivation, socket-name tag | `crypto.rs:65` (`sha256`), `crypto.rs:217` (`key_id`), `record.rs:63` (`blob_key_hash`), `record.rs:218` (`id`), `acl.rs:355` (`Entry::hash`), `acl.rs:403` (`invite_key`) |
| SHA-512 | `sha2 0.11.0` | Fleet fingerprint (5200 rounds); HMAC-SHA512 in SLIP-10 | `identity.rs:447` (`fleet_fingerprint`), `identity.rs:39` (`slip10_ed25519`) |
| HMAC | `hmac 0.13.0` | SLIP-10 only | `identity.rs:39-62` |
| BLAKE3 | `blake3 1.8.7` | Blob content address (iroh-blobs' own hash), gossip topic id | `record.rs:335` (`seal_blob`), `linkd/src/net.rs:153` (`topic`) |
| Argon2id v0x13 | `argon2 0.5.3` | Passphrase KEK for the stored root | `identity.rs:383` (`root_kek`) |
| Unicode NFC | `unicode-normalization 0.1.25` | The root passphrase, before Argon2 | `identity.rs` (`nfc`) |
| SLIP-10 (ed25519, hardened only) | own code, about 25 lines, pinned by the SLIP-10 spec vectors | Root derivation | `identity.rs:39-72`, vectors in the `identity.rs` tests |
| BIP39 | `bip39 3.0.0` | 24-word phrase, empty BIP39 passphrase | `identity.rs:66-86` (`new_phrase`, `root_from_phrase`) |
| JCS (RFC 8785), subset | own code | The bytes of everything signed. Floats and integers above 2^53-1 are refused | `codec.rs:67-150` (`jcs`, `canonical`) |
| Strict base64 / hex | `base64 0.22` + own checks | Canonical padded base64 is re-encoded and compared. Hex must be lowercase and exactly the right length | `codec.rs:17-66` |
| Transport | `iroh =1.3.0`, `iroh-gossip =0.101.0`, `iroh-blobs =0.103.1`, `iroh-mdns-address-lookup =0.6.0` | QUIC endpoint, gossip, blobs | `linkd/src/net.rs:465-540` |
| RNG | `getrandom 0.3` (OS) | All keys, nonces, secrets | `crypto.rs:48-60` |
| Zeroize | `zeroize 1.9.1` | Wipes key material on drop: `Secret32`, `KemSecrets`, SLIP-10 intermediates, the device file, the opened root | `crypto.rs:38`, `crypto.rs:179`, `identity.rs` |

Not used: no hybrid signatures, no ratchet or per-message forward secrecy. The body AEAD is not
key-committing on its own. Keys are committed by the key id (6) and blob keys by `key_hash` (5.5).
The module doc lists the "each used one way only" rule (`crypto.rs:1-13`).

## 2. Identity

### 2.1 Root

- The phrase comes from 32 bytes of OS entropy as 24 BIP39 words (`identity.rs:66`, `new_phrase`).
  Parsing joins on whitespace and lowercases, then checks words and checksum, and requires exactly
  24 words (`identity.rs:74-86`, `root_from_phrase`).
- `seed = BIP39 to_seed_normalized("")`, then **SLIP-10 ed25519 path `m/44'/7743'/0'`**
  (`AURORA_COIN = 7743`, `identity.rs:26`). The 32-byte SLIP-10 key is the Ed25519 seed of the
  root. The seed, every HMAC output and the chain code are wiped (`Zeroizing`).
- The root signs device certificates and, when the sequencer is lost or compromised, a
  **takeover** of the ACL chain (4.4), under its own purpose. Nothing else.
- `identity.init` returns a newly generated phrase once in the RPC result
  (`linkd/src/daemon.rs:409`, `identity_init`). So the phrase passes once through the JSON-RPC
  channel and the Python CLI, where it cannot be wiped. `--trace-rpc` redacts it (section 8).

### 2.2 Device keys and certificates

- A device has a random Ed25519 signing key, which is also its iroh node id and its `author` id
  everywhere. It also has a random X25519 KEM key and, optionally, a random 32-byte X-Wing seed.
  None of them is converted from Ed25519 (`identity.rs:224`, `Device::create`). `identity.init`
  turns X-Wing on by default (`linkd/src/daemon.rs:419`).
- **Certificate** (`identity.rs:90`, `DeviceCert`): `{v:1, device, root, label, x25519, xwing?,
  not_before, not_after, sig}`. The root signs **JCS of every field except `sig`** (`CertBody`,
  `identity.rs:104`) under the purpose `"cert"` (`identity.rs:152`).
- **Lifetime:** at most `CERT_MAX_LIFETIME_S = 90 days` (`identity.rs:27`). `verify()` refuses an
  empty or longer window and does **not** check the clock (`identity.rs:157`). Callers check
  `valid_at(t)`, which is `not_before <= t < not_after` (`identity.rs:178`).
- **Which time is checked:**
  - ACL entries and the proposals they include: at the entry's `ts`, which only the sequencer
    stamps, which never goes down along the chain, and which a replica refuses more than 600 s
    ahead of its clock (`AclState::apply_entry`, `AclState::author_for`). A stolen key that is
    never removed is contained by removal, not by time.
  - Records, **new:** a record signs its write time `ts` (5.1). It is refused when `ts` is at or
    after the author's latest `not_after`, more than 600 s ahead of the receiver's clock, more
    than 600 s before the chain entry it names, or before its own predecessor
    (`engine.rs:827`, `authorised`; `engine.rs:575-640`, `receive`). An expired device does not
    write (`engine.rs:506`, `write`).
  - Joins and new devices: at the entry's `ts` (`acl.rs:1227`, `apply_join`; `acl.rs:936`).
- **Renewal:** `CERT_RENEW_WITHIN_S = 30 days` before expiry (`identity.rs:29`, `265`). The root
  re-signs the same keys (`identity.rs:256`, `renew`). The daemon then appends a "renewal"
  `add_device` (same keys, later `not_after`, no wraps) to every link: an own entry on the
  sequencer, a proposal elsewhere. A renewal, by `add_device` or carried on an entry or proposal,
  must start at or before the stored certificate ends, come inside the renewal window, and come at
  most one lifetime after the stored end (`acl.rs: check_renewal`). Housekeeping renews hourly when the root is
  available (`linkd/src/daemon.rs:917`).
- **KEM keys cannot be rotated** without a new device id: `same_keys` compares device, root,
  x25519 and xwing (`identity.rs:194`).
- On disk, `<secrets>/link/device.json` holds the raw signing key and KEM secrets as base64 JSON.
  **New:** `write_secret` writes it through a fresh random temp name (`create_new`, so a planted
  file or symlink is never opened), sets 0600 explicitly, and renames it into a folder that
  `private_dir` makes 0700 and checks is ours (`linkd/src/daemon.rs:125-185`). On Windows the
  file gets no ACL of its own. The encoded strings are wiped after use (`Device::to_json`,
  `from_json`).

### 2.3 Fingerprints and safety numbers

`fleet_fingerprint(root)` (`identity.rs:447`, Signal-style):

```
d = 0x00 0x01 || root(32) || "aurora-link-fleet"
repeat 5200: d = SHA-512(d || root)
digits = for each of the six 5-byte chunks of d[0..30]: big-endian u40 mod 100000, zero-padded to 5
```

`safety_number(a, b)` sorts the two 30-digit halves and concatenates them into 60 digits
(`identity.rs:464`). Only fleet roots are compared, not device keys. Pinned by
`aurora-rs/link-vectors/fingerprints.json`. `link.verify` lists one number per other member, and
`--mark` stores it locally (`linkd/src/daemon.rs:670`, `link_verify`). Nothing in the protocol
requires verification before records flow. **New:** after a join, the summary computes the
safety number against the fleet that **published the invite**, not the owner
(`linkd/src/daemon.rs:626-650`, `joined_summary`).

### 2.4 Root sealing at rest (optional), format v2

`seal_root` (`identity.rs:393`) requires a passphrase of at least 12 characters after NFC. It uses
a 16-byte random salt and **Argon2id with m = 65536 KiB, t = 3, p = 1** and a 32-byte output. The
root's 32-byte seed is sealed with XChaCha20-Poly1305. **New in v2:** the AAD is
`"aurora-link/v1/root" || 0x00 || JCS{v, kdf, m_kib, t, p, salt}` (`identity.rs:376`, `root_aad`),
so the parameters cannot be changed unseen. `open_root` (`identity.rs:413`) accepts only format 2,
m 64-256 MiB, t 3-8 and p 1-4. A v1 file is refused and must be sealed again. The file is
`<secrets>/link/root.json`. The passphrase may also come from the environment variable
`AURORA_LINK_PASSPHRASE` (`linkd/src/daemon.rs:402`). Without `root.json`, the root exists only
while the phrase is being typed.

### 2.5 Self-monitoring

Every device keeps `certified.json`, the device ids its own root certified locally. An alarm
(`unknown_own_device`) fires when the chain lists an active device under our root that we neither
certified nor were preceded by (`engine.rs:424-450`, `self_monitor`). This is the only detection
of a misused root.

## 3. Domain separation

All signatures cover `CONTEXT || purpose || 0x00 || msg`, with `CONTEXT = "aurora-link/v1/"`
(`crypto.rs:28`, `crypto.rs:77-100`).

| Context (exact) | Kind | Key | Binds (`msg`) | Where |
|---|---|---|---|---|
| `aurora-link/v1/cert\0` | Ed25519 sig | fleet root | JCS of the certificate without `sig` | `identity.rs:152` |
| `aurora-link/v1/acl\0` | Ed25519 sig | the term's sequencer device | JCS of the entry without `sig`: `{v, link, term, seq, prev, ts, sequencer (full certificate), body?, proposals? (each with its own sig), cuts?}` | `acl.rs`: `Entry::unsigned_bytes`, `Entry::sign`, `Entry::verify_with` |
| `aurora-link/v1/acl-proposal\0` | Ed25519 sig | proposer device | JCS of `{v, link, kind, args, proposer (full certificate), base {term, seq}, nonce}` | `acl.rs`: `Proposal::unsigned_bytes`, `Proposal::sign`, `Proposal::verify_with` |
| `aurora-link/v1/acl-refusal\0` | Ed25519 sig | the sequencer device that refused | JCS of `{link, id, why, at {term, seq, hash}, by}` | `acl.rs`: `ProposalRefusal::sign`, `verify` |
| `aurora-link/v1/acl-takeover\0` | Ed25519 sig | **fleet root** (the owner's) | JCS of `{link, term, after {term, seq, hash}, sequencer}` | `acl.rs`: `takeover_bytes`, `AclChain::takeover`, checked in `AclState::apply_entry` |
| `aurora-link/v1/record\0` | Ed25519 sig, and the **preimage of `record_id`** | author device | JCS of the header `{v, link, author, seq, ts, prev, deps, blobs, blob_sizes, acl, epoch, size_class, ct_hash}` | `record.rs:197-222` |
| `aurora-link/v1/head\0` | Ed25519 sig | author device | JCS of `{v, link, author, seq, id, ts}` | `record.rs:378-420` |
| `aurora-link/v1/join\0` | Ed25519 sig | invite key | JCS of `{link, invite (the issuing action id), root, device, nonce (the join proposal's)}` | `acl.rs`: `join_proof_bytes`, checked in `AclState::apply_join` and at the door in `sync.rs: JoinDoor::on_frame` |
| `aurora-link/v1/join-hello\0` | Ed25519 sig | invite key | JCS of `{v, link, invite, device}` (device = the QUIC-authenticated peer) | `sync.rs: join_hello_bytes`, checked in `JoinDoor::on_frame` |
| `aurora-link/v1/wrap\0` + `owner_hex "\|" epoch_dec "\|" device_hex "\|" key_id_hex "\|" suite_byte` | HPKE `info` | n/a | owner root, epoch, recipient device, **key id**, **suite** (not the link id) | `acl.rs:535` (`AclState::wrap_info`), `crypto.rs:223` (`wrap_info`) |
| `aurora-link/v1/key-id\0` + `epoch_be(8)` + key | SHA-256 | n/a | the public name of a read key | `crypto.rs:217` (`key_id`) |
| `aurora-link/v1/blob-key\0` + key | SHA-256 | n/a | a blob key's commitment, `BlobRef.key_hash` | `record.rs:63` (`blob_key_hash`) |
| `aurora-link/v1/invite\0` + secret | SHA-256 KDF | n/a | invite secret, giving the invite Ed25519 seed | `acl.rs:403` (`invite_key`) |
| `aurora-link/v1/root\0` + JCS of the format fields | AEAD AAD | Argon2id KEK | the sealed root and its KDF parameters | `identity.rs:357`, `376` |
| `aurora-link/v1/blob` | AEAD AAD (a constant) | per-blob random key | nothing beyond the key | `record.rs:335-375` |
| JCS of the header without `ct_hash` | AEAD AAD (no prefix) | epoch read key | all header fields except `ct_hash`, now including `ts` and `blob_sizes` | `record.rs:207` (`aad`) |
| `link_id "\|prev\|" epoch_dec` | AEAD AAD (no prefix) | epoch k key | the sealed key of epoch k-1 | `acl.rs:620` (`prev_key_aad`), `625` |
| `"ed25519 seed"` | HMAC key | n/a | SLIP-10 master | `identity.rs:39` |
| `0x0001` + root + `aurora-link-fleet` | hash prefix | n/a | fingerprint | `identity.rs:447` |
| `aurora-link/v2/gossip-topic\0` + JCS of the whole genesis entry | BLAKE3 input | n/a | gossip topic id | `linkd/src/net.rs:153` (`topic`) |
| (none) SHA-256(JCS(full entry incl. `sig`)) | hash | n/a | ACL entry hash; the genesis hash is `link_id` | `acl.rs: Entry::hash` |
| (none) SHA-256(JCS(full proposal incl. `sig`)) | hash | n/a | proposal id (an action id: invites and joins are keyed by it) | `acl.rs: Proposal::id` |

Notes for the reviewer:

- **The fleet root signs two things now:** device certificates and, rarely, a takeover. Both are
  under distinct purposes.
- **Device signing key reuse across protocols.** The same Ed25519 secret is the iroh
  `SecretKey` (`linkd/src/net.rs:472`). With the default n0 preset, iroh uses it for TLS
  CertificateVerify, relay handshakes and pkarr DNS records. Separation from our messages rests on
  the `aurora-link/v1/` prefix never being a valid prefix of anything iroh signs.
- HPKE AAD: suite 1 uses `aad = ""`. Suite 2's outer X-Wing layer uses `aad = enc1` (the X25519
  encapsulation) over plaintext `ct1`, with the same `info` (`crypto.rs:231-256`). The suite byte
  is now in `info`, so the inner layer of an X-Wing wrap does not open as a suite-1 wrap (test
  `a_wrap_is_bound_to_its_suite`, `crypto.rs:353`).

## 4. Membership: the ACL chain

Round 5 replaced this section's subject. The `acl.rs` module doc states the rules; this section
walks the code. Pointers name `file: function` (or `Type::method`).

### 4.1 Entries and the fold

`Entry {v: 2, link, term, seq, prev, ts, sequencer, body?, proposals[], cuts{}, sig}`
(`acl.rs: Entry`). `sequencer` is the full certificate of the device that signs the entry; `body`
is the sequencer's own action (an `Op`), `proposals` are other devices' signed actions applied
after it, and `cuts` names, for each device the entry removes, the last feed seq still accepted.

- **Genesis** has term 1, seq 0, empty `prev` and `link`, no proposals or cuts, and a
  `Genesis {name, owner, label, policy, devices, sequencer, key}` body. Its signer is the owner's
  device it names as `sequencer`. Its hash is `link_id`.
- **Every later entry** must follow the chain's last entry: `seq` one more, `prev` its hash, `ts`
  not before its `ts`, and `link` the link id (`AclState::apply_entry`). It must carry an action.
  It must be signed by the term's sequencer (4.4), an active owner or admin device whose stored
  certificate has the same keys and is valid at `ts` (a carried renewal is bounded, 2.2).
- **The fold.** `AclChain::push` applies each entry to the state after the one before
  (`AclState::apply_entry`, on a copy: an error changes nothing). There is no resolution, no
  merge, no tie-break and no dropped list: an entry applies or the chain refuses it. A replica
  refuses an entry more than `MAX_FUTURE_SKEW_S` (600 s) ahead of its clock, or larger than
  `MAX_ENTRY_BYTES` (512 KiB). That is sized for the largest entry a policy allows: a key change
  wrapped to `MAX_LINK_MEMBERS` (32, the policy's cap, checked at genesis) x 8 X-Wing devices, in
  a proposal, is 469,745 bytes, and one entry always fits one 2 MiB frame. The sequencer signs no
  larger entry (`AclChain::append`), and a replica that refuses the sequencer's next entry raises
  an `acl_divergence` alarm (`Inserted::diverged`, `Link::add_acl`).
- **Cuts.** After the actions run, the set of devices they cut must equal `cuts`' keys exactly. The
  sequencer fills each cut with the feed head it holds for that device (`AclChain::append`, a dry
  run then the signed entry; `Link::held_head`).
- **Snapshots.** The state after every 256th entry is kept (`AclChain::checkpoints`, persistent
  maps, so a copy is O(1)); `AclChain::state_at` folds at most 255 entries from the nearest.
- **Storage.** `acl_entries` by seq (`Store::put_acl_from` rewrites from the lowest changed seq);
  reopening checks every entry again (`AclChain::restore`).

### 4.2 Roles and who may do what

Roles: `owner > admin > writer > reader > mailbox` (`Role`). The checks live in
`AclState::apply_action` (and `apply_join`, `apply_genesis`), against the state where the action
applies:

- Invite: an admin; `role` is never owner, and admin only from the owner. Expiry after the entry's
  `ts`, at most 30 days on.
- Join (always a proposal by the joining device, its only device for now): the invite exists,
  is not revoked or used (single-use), is unexpired at the entry's `ts`, and its inviter is still
  an active admin; the fleet is not already a live member; the link is not full; the label is
  sane, unique among live members and not 64 hex digits; the device is not already known; the
  proof verifies under the invite key over `{link, invite, root, device, nonce}`. A non-approval
  invite admits at once and waits for an `accept` to wrap the key.
- Accept: an admin holding the key; wraps cover exactly the member's live devices if it reads.
  Decline: an admin; the join must still be pending.
- AddDevice: the member itself or an admin; a new device needs a certificate valid at `ts` and,
  if the member reads, a wrap by an author holding the key; at most 8 devices. A renewal is the
  same keys with a later expiry, no wraps, in bounds (2.2); a device renewing itself already
  carries it.
- RemoveDevice: the member itself or an admin; an owner device only by the owner; an admin's device
  only by the owner or that admin (**new in round 5**); never the owner's last device; a device that
  removes itself picks no key.
- SetRole: only the owner changes an admin's role or grants admin; an admin may change other roles;
  never the owner role; not to the role the member has. Taking read access away must rotate in the
  same action.
- RemoveMember: an admin; an admin only by the owner; a leave by the member itself picks no key;
  never the owner.
- RotateKey: an admin at any time (a recovery re-key only by an admin); anyone else only a due
  rotation, as the designated device or after the grace (4.6).
- RevokeInvite: an admin; not already revoked, and not a used single-use invite.
- Handoff: the sequencer (own action) or an owner device (proposal); `to` is an active owner or
  admin device other than the sequencer; no handoff already waiting.

After every entry the sequencer (or a handoff's target) must still be an active owner or admin
device (`AclState::check_sequencer`): removing or demoting it needs a handoff (or a takeover)
first.

### 4.3 Proposals

`Proposal {v: 1, link, kind, args, proposer, base {term, seq}, expires, nonce, sig}`
(`acl.rs: Proposal`); `expires` is signed, and set `PROPOSAL_TTL_S` (7 days) after the proposer's
clock (`AclChain::propose_at`).
`kind`/`args` are an `Op` other than genesis and takeover. The id is the hash of the whole
proposal.

- **Making one.** `Link::act` appends on the sequencer and otherwise signs a proposal on the chain's
  tip (`AclChain::propose`), checks it locally against the chain as held (`check_proposal`), and
  keeps it in the store (`proposals`, `mine = 1`).
- **Carrying it.** Each sync session sends its side's queued proposals (`propose` frames, up to 32
  at a hello); a replica that does not sequence keeps a verified, unexpired proposal to relay, and
  the daemon pushes new ones to live sessions (`Push::Proposal`). A proposal is at most
  `Proposal::max_bytes` for its kind (16 KiB, 48 KiB for an accept, 480 KiB for a key change),
  checked with its signature. A replica keeps one only from an active member's device, or a join
  on a live invite (unused, unrevoked, unexpired, from an admin) whose proof verifies
  (`Link::check_origin`, `Link::invite_live`), and only if it holds against the chain as the
  replica has it (`AclChain::check_proposal`, review finding R7-3); a proposal whose base is past
  its chain is not kept until it catches up. It keeps at most 64 per origin (proposer root, or
  invite for joins) and 1,024 in all, never dropping its own (`Store::trim_relayed`).
- **Charging it** (`Link::offer_from`, R7-3). What the session peer could have checked itself (a
  proposal's shape, signature, size, expiry, a proposer or invite the chain never listed) is
  charged to the peer's fleet; a refusal, and anything else that depends on the chain (an inactive
  proposer, a dead invite, a relay's failed check), is charged to the proposal's origin (its
  proposer's root, or `invite:<id>`); a base the replica cannot judge yet is charged to nobody. A
  peer whose charges, or an origin whose charges and included proposals today, reach its daily
  allowance (32, or 512 for an admin fleet) gets no more taken, without a check or a signed
  refusal. An origin is charged at most once per proposal id, however often anyone replays that
  proposal: the charge counts against a day's allowance, and is remembered until the proposal
  expires (round 9; round 8 remembered it for a day, so a replay a day later was charged again).
  A replay is still checked and refused, and only charging is remembered, so a proposal that
  holds later is kept (R8-1). Peer charges and origin charges are separate tables, so an origin's
  spent allowance never stops its fleet's devices from relaying. The charges are kept in
  memory.
- **Including it.** The sequencer (`Link::offer`) applies its per-member allowance (32 a day, 512
  for an admin; policy, not validity), then appends it (`AclChain::append`), which runs
  `AclState::apply_proposal`: the proposer's certificate (with proof of possession) and signature,
  the link, never included before, the base on the chain and not before the latest root takeover
  (`AclState::takeover_at`: the takeover may have dropped an entry that included it), the entry's
  `ts` before `expires` and `expires` at most 7 days and 600 s after it, then the action's own
  checks against the current state. A join's
  author is the joining device; any other author must be an active member device with a
  certificate valid at the entry's `ts`.
- **Refusing it.** On error the sequencer signs a `ProposalRefusal {link, id, why, at, by, sig}`
  (`Link::offer`), stores it (refused rows are trimmed like relayed ones), and replies with a
  `refusal` frame. A replica takes a refusal for a proposal it holds queued only if its signer is
  the current sequencer (R7-6: an ex-sequencer's key can sign a fresh refusal at any position of
  its old term), which also sequenced at `at`, a position on its chain at or past the proposal's
  base; the sequencer takes no refusal it did not sign (`Link::take_refusal`). A proposal re-sent to a replica that knows its
  refusal gets the refusal back (on the sequencer, only its own, while the chain has not moved).
- **Action ids.** Invites are keyed by the action that issued them, and joins by their proposal id
  (`AclState::invites`, `pending_joins`): the entry hash for a sequencer's own action, the proposal
  id for a proposal. So a non-sequencer admin hands out an invite code before the sequencer
  includes the invite; the code works once it is included.

### 4.4 The sequencer and terms

- **Term 1** is sequenced by the owner's device that signed genesis (`Genesis::sequencer`).
- **Handoff.** A `Handoff {to}` action sets `handoff_to`; the next entry must be term + 1, signed by
  `to` (`apply_entry`). Until `to` appends, nothing else can (the old sequencer cannot continue its
  term). `AclState::next_sequencer` says who signs next and in which term.
- **Root takeover.** `Takeover {term, after, sequencer, sig}` is signed by the owner's fleet root
  (`AclChain::takeover`). The named device appends it as the body of the first entry of the new
  term, right after `after`; the entry is valid only if `after` is exactly the state's last
  position, `term` is later than `after`'s, the signature verifies under the genesis owner root,
  and the device is an active owner or admin device there. `link.takeover` takes the phrase (or
  the sealed root's passphrase); the term is one more than any term the replica holds, evidence
  included. `after` defaults to the replica's held tip, so nothing it holds is dropped; while
  halted below the held tip it must be given: the common prefix (every replica can take it, both
  branches are dropped) or a position on this branch (kept, but replicas holding the other branch
  stay halted until a takeover at or below the common prefix reaches them).
- **Fork choice** (`AclChain::insert_one`): an entry at a seq the replica already holds, whose
  `prev` links to the entry before, wins if its term is higher, or if it is a takeover and the held
  one is not in the same term. The winner must apply on the state after the entry before (it is
  folded from the nearest snapshot); then the replica drops its entries from that seq on and
  reports their positions (`Inserted::dropped`). A losing entry, and whatever builds on it in the
  same batch, is ignored. An entry that does not link makes the replica ask from 256 entries back
  (`Inserted::need_from`), until it finds the fork point.

### 4.5 Equivocation

Two different entries at one position on one prefix (same `prev`), in one term, are equivocation
only if each applies on its own on the state before them: a dry `apply_entry`, cuts skipped
(`AclChain::applies_alone`, from `check_equivocation` on insert and from `note_evidence` for an
`evidence` frame). That covers the sequencer's signature and authority, a takeover's root
signature, named device and `after` (two takeovers of one term by the root are evidence),
certificate validity at `ts`, and size. A forged copy proves nothing (R6-5). The replica:

- keeps the pair as evidence (`acl_evidence`, one row per `(signer, term, seq)` with what it did:
  `halt`, `alarm` or `past`) and raises an `equivocation` alarm;
- if its held chain has, above that position, a later term started by a root takeover or by a
  device of another member than the evidence's signer, or a later term of the signer's own member
  while the signer's device can no longer sequence and the owner's fleet or another member removed
  or demoted it (R7-5) (`AclChain::settled_above`), stops there: the alarm says it did not halt,
  and the entry loses fork choice (R6-1, findings "Evidence below a later term start");
- otherwise halts: it keeps its held chain and state (nothing is folded back); `prefix_len`,
  `tip`, `on_chain`, `range` and `all` stop at the entry before; what it acts on (`state()`: sync,
  record admission, status) is the held state narrowed to the prefix's grants too
  (`AclState::narrowed`: a device active in both, at the lower role; cuts and keys from the held
  tip); it refuses every entry except a root takeover of a later term, from any position it holds
  (`insert_one`), appends nothing (`append`), and seals nothing (`Link::write`);
- shows it in `link.status` (`equivocation`, `halted_view`, `acl_held_tip`) and in `aurora
  doctor` (with the takeover command for each choice of `after`), and sends its evidence to every
  peer (`evidence` frame at each hello and after detection).

A takeover settles it: once the chain holds a takeover of a later term past the equivocation, the
evidence no longer halts (also on reopening).

**Bounds** (R7-1). Before any signature is checked or any state folded (`AclChain::screen`), a
pair is ignored if the replica holds one for that `(signer, term, seq)` (the first wins), if a
halt at or below it already stands, or if it would be one more alarm about a signer already
raised. An `insert` runs at most one evidence check (a signature, a fold of at most 255 entries
and a dry application) and stops there (`Inserted::checks`); the session charges each check as 8
of its 120 ACL frames a minute (`sync::EVIDENCE_CHECK_FRAMES`). The store keeps at most 256 pairs
(`MAX_EVIDENCE_PAIRS`): at the cap an alarm-only pair is not kept (and raises no alarm), and a
halt's pair replaces the oldest pair that is not the current halt (`Store::put_evidence`). On a
restart only the current halt's pair is checked again, through `note_evidence`, so a halt at the
next position survives it (R7-4); the other pairs only mark their position as seen. The screen's
"one more alarm" case asks `settled_above`, which is one bound per signer and term, computed by
one scan and kept until the held tip changes (R8-4), so a flood of such frames costs a lookup each.

**While halted, the transport reads the held state** (R7-2). The narrowed view can leave out a
device the held tip lists, this replica's own included. linkd's `peer_links` (the dialer, the
inbound `Gated` and link gates, gossip bootstrap) reads the held state, and so does
`sync::may_sync_acl`, which admits the chain's own frames (`acl`, `acl_want`, `acl_done`,
`evidence`) and the daemon's ACL pushes; records, heads, proposals and blobs still need the
narrowed view (`sync::may_sync`, `Daemon::record_peer_links`), and other frames from a device the
halt leaves out pass unanswered instead of ending the session.

### 4.6 Read keys, key ids, epochs and rotation

Unchanged from round 4 except who rotates (`AclState::designated_rotator`, `may_rotate_due`,
`may_rotate`):

- A removal (or a role change that takes read access away) carries the new key for exactly the
  readers left, or leaves a rotation due; `rotation_due_since` is the `ts` of the entry that made it
  due, stamped by the sequencer.
- The designated rotator is the sequencer when it holds the key (otherwise the lowest admin device
  holding it, otherwise the lowest reading device holding it). The sequencer rotates at once
  (`Link::upkeep`, and `Link::rotation_gate` before it writes). Any other device holding the key
  proposes a rotation once the grace (1 h after `rotation_due_since`) has passed, by the entry's
  `ts`, and the sequencer takes it then.
- Writers do not seal new mail while a rotation is due (`Link::rotation_gate`).
- A wrap to another device cannot be checked by anyone else, so a rotating key holder can still wrap
  junk; the device that gets it raises `bad_wrap` naming the author, and an admin's daemon re-keys
  from the last epoch it can read (`KeyChange.from`, `recovery_key_change`, `read_key` /
  `walk_back`).
- Key ids, wrap `info` and the previous-key chain are as in section 6.

### 4.7 Invites and the join protocol

- `link.invite` appends (or proposes) an `Invite` with a fresh secret's public key; the code
  carries the secret, the issuing action id, dial hints and the inviter's fingerprint.
- The joiner dials the inviter on `aurora/link-join/2` (`sync.rs: JoinDoor`): a `join_hello` (proof
  over `{v, link, invite, device}`) must verify for a live invite, or for one this device's own
  join used up (so a joiner whose join was relayed can fetch the chain again); the door replies
  with the whole chain. The joiner checks it is the link the code names and that the inviting
  fleet has the code's fingerprint (`join_proposal_for`, `InviteCode::check_log`), then sends its
  join proposal. The door checks the proposal's signature, the invite, and the proof before
  anything is kept.
- If the inviter sequences the link it includes the join, its upkeep accepts it, and the door
  replies with the chain. Otherwise it queues the join for the sequencer, pushes it to its sessions,
  and waits up to 20 s (`JoinDoor::poll` in `linkd/src/net.rs: JoinProto`); then it replies with the
  chain, or `bye "queued: ..."`, and the joiner runs the same join later.
- Offline: `link.join` with the inviter's chain returns the proposal in a bundle; the inviter
  imports it (the sequencer includes it), and the joiner imports the inviter's next export.
- Join attempts are rate-limited per IP and per device id, and at most 8 run at once (7).

## 5. Records

### 5.1 Format

| Field | Signed (in header) | In body AEAD AAD | Notes |
|---|---|---|---|
| `v` = 2, `link`, `author`, `seq` (from 1), `prev` (`""` only at seq 1) | yes | yes | `record.rs: Record` |
| `ts`, the author's write time (**new**) | yes | yes | Retention and certificate validity are judged by it (5.2, 5.4) |
| `deps` (at most 16, other authors' head ids) | yes | yes | Not checked against the store on receipt |
| `blobs` (at most 16 blob ids, in the clear) | yes | yes | Must equal `body.blobs[].id` after decryption (`record.rs:304`, `open`) |
| `blob_sizes` (**new**), the padded ciphertext length of each blob | yes | yes | Each must be a bucket size (`record.rs:257`, `verify`). Must match `blob_ct_len(body.blobs[].bytes)` after decryption |
| `acl`, the chain position `{term, seq, hash}` the writer stood on | yes | yes | Checked against the chain (5.3) |
| `epoch`, `size_class` (a bucket) | yes | yes | |
| `ct_hash` = SHA-256(ct) | yes | **no** (it depends on ct) | `record.rs:197-216` |
| `ct` = nonce(24) ‖ XChaCha20-Poly1305(padded body) ‖ tag(16) | via `ct_hash` | n/a | Length must be `24 + size_class + 16` |
| `sig` | n/a | n/a | Ed25519 under `"record"` over the JCS header |

- `record_id = SHA-256("aurora-link/v1/record\0" || JCS(header))` (`record.rs:218`). It does
  not cover `sig` or `ct` itself; `ct` is bound only through `ct_hash`. A record and its stripped
  copy share an id by design. A whole copy of a record held stripped is a duplicate (5.4).
- **Body**, encrypted (`record.rs:109`): `{kind, seat, to, content, reply_to?, blobs[{id, key,
  key_hash, name, bytes}], sent_at, acks{}, read[]}`. `seat` is an unauthenticated claim and
  `sent_at` is advisory. `kind` must be in the link policy and `BRIDGE_KINDS` (`blocker, chat,
  completion, handoff, note, question, reply`), or be `ack` (receipts only). It is checked at write
  and again at read (`record.rs:132`, `Body::check`).
- **Padding:** a 4-byte big-endian length, then the body, then zeros up to the smallest of
  **4096 / 16384 / 65536 / 262144** bytes. Non-zero padding is refused (`crypto.rs:35`,
  `143-175`). Larger content must go in a blob.

### 5.2 Admission order (`Link::receive`, `engine.rs:575-655`)

1. `verify()`: shape, sizes, blob-size buckets, `ct_hash`, signature. Then check the link id.
   A record already held is a duplicate, also when the held copy is a stripped header (round 2:
   refill is gone, L1).
2. **New:** refused if `ts` is more than 600 s ahead of our clock.
3. `member_check` (`engine.rs`): the author is a known device, its member is not pending, the
   record's `seq` is at most `cut` if the device was removed, the member has not been removed (if
   the device has no cut), the role is **at least reader** (writers are checked later), `ts` is
   before the author's `not_after`, and the author is not frozen. The chain position is checked
   last (5.3).
4. A missing `ct` is accepted only when the record is past retention (5.4). A whole record past
   retention on arrival is stored as a header only.
5. Equivocation: a different record already at `(author, seq)` **freezes** the author locally and
   raises an alarm. A `prev` that does not match the stored head is a broken chain, with the same
   result. A gap returns `Gap`. **New:** a record dated before its predecessor is refused. Over the
   per-author hourly quota, counted by local arrival, it returns `Gap` (`engine.rs:600-645`).
   Freezes are permanent and local. Peers now exchange the two conflicting records (7).
6. Open with the key for `r.epoch` (`engine.rs:676`, `open_here`). Without a key the record is
   `opaque`. If it fails to open it is `withheld`, with an alarm. A non-ack from a member without
   write rights at its position or now is `withheld`. Otherwise the record is `own`,
   `receipt` (another fleet's ack) or `admitted` (`store.rs:54-59`). Only `admitted` records get a
   cursor and reach Python.
7. **New:** blobs are listed only from a body opened and admitted here, or, on a mailbox, from the
   signed header of a whole record (5.5).

There is no later pass that retries `opaque` records once a key arrives. The `keys` table
(`store.rs:35`) is unused.

### 5.3 Records name the chain position they stood on

A record's `acl` is the chain position `{term, seq, hash}` its writer stood on: the tip of the
writer's chain (`Link::write`), sealed under the epoch in force there. On receipt, after the feed
checks, `Link::position` reads it:

- **On the chain** (`AclChain::on_chain`: the seq is in the prefix and the term and hash match):
  `Link::check_at` against the state there (`AclChain::state_at`): the author was an active device
  there, the record's epoch is the epoch in force there, and its `ts` plus 600 s is not before that
  entry's `ts`. Write rights must hold there and now (`Link::open_here`).
- **Not reached** (the seq is past the prefix, or the chain holds another entry of the same or a
  lower term there): the record waits (`Admit::Pending`, one per author, in memory), the session asks
  the peer for the range (`Link::wanted_acl`), and the record is checked again whenever the chain
  grows (`Link::retry_pending`). A same-term conflict, once the entry arrives, is checked as
  equivocation evidence.
- **Lost** (the chain's term at that seq, or at its end before it, is later than the position's:
  terms never go down along a chain, so the position can never be on it): the record is stored
  `withheld` with reason `LOST_FORK`, so its author's feed goes on, and it is never opened. When a
  takeover drops positions, every record already stored on them is withheld the same way
  (`Store::lose_positions`, by `records.acl_hash`), its cached body and cursor removed. Either way the
  status is a function of the record and the chain.

Nothing requires the named position to be recent: a writer may name an older position and seal
under that epoch's key, as long as its `ts` is not more than the skew before that entry. The honest
daemon names its tip and waits while a rotation is due. Pinned by
`r5_5_records_on_a_dropped_position_are_withheld_whenever_they_arrive`,
`a_record_on_an_unreached_position_waits_and_the_chain_is_fetched` and
`m3_an_expired_never_removed_key_delivers_no_content` (`engine/tests.rs`);
`link-vectors/records.json` pins a record naming a position.

### 5.4 Retention, and F2 (fixed)

Retention clears `ct`, the cached plaintext and the record's blob listing for records whose
**signed write time** is older than `retention_days` (`store.rs: retire_before`, by
`written_at = min(ts, arrival)`; `Link::retire`). The signed header stays. A record is past
retention when `ts` plus retention is at or before our clock, or before the ACL chain's frontier, the
latest entry `ts`, which every replica sees alike (`Link::past_retention`, `AclState.frontier_ts`).
A record that arrives without `ct` is refused until then. **Round 2:** a whole record that arrives
past retention is stored as a header only, and a stripped row is never filled back in (`refill`
and `fill_body` are removed; M3, L1). F2 (a relay stripping a fresh record whose ACL head was old)
no longer works. Tests: `a_stripped_copy_is_judged_by_its_write_time_and_never_refilled_past_retention`,
`m3_an_expired_never_removed_key_delivers_no_content`.

The store schema is now version 8 (`store.rs: SCHEMA_VERSION`): the chain by seq, equivocation
evidence as pairs (one per position and signer, with what each did), proposals with their origin,
and each record's position. A store of another version is refused, and its
link must be synced again.

### 5.5 Blobs

Each attachment gets a fresh random 32-byte key. **New:** it is zero-padded to a power of two of
at least 4 KiB (`record.rs:46`, `blob_ct_len`), then sealed with XChaCha20-Poly1305 under AAD
`"aurora-link/v1/blob"`, and `id = BLAKE3(ciphertext)` (`record.rs:335`, `seal_blob`). The key,
`key_hash`, name and length travel only inside the encrypted body. The ids and padded sizes travel
in the clear in the header. `open_blob` (`record.rs:351`) checks the id, the exact padded length,
the key commitment, the AEAD and zero padding. At most 64 MiB of plaintext per blob.

Listing and caps (`Link::blob_room`, `Link::register_blobs`): a blob id already listed with
another size is refused (round 2, L2). A link lists blobs only from admitted bodies,
or, on a mailbox, from whole records' headers. A link's listing is capped at 1 GiB of ciphertext.
A mailbox lists at most 256 MiB per author. Past a cap the blob is not listed and an alarm says
so. The daemon serves a blob only to a peer that shares a link listing it, and fetches only listed
blobs, stopping at the signed length (`linkd/src/net.rs:849`, `fetch_listed_blob`).

## 6. Encryption: key wrapping

- **Wrap** (`crypto.rs:231-290`): HPKE base mode, single-shot.
  - Suite 1 (`suite = 1`): `enc1 (32) || ct1 (32+16)`.
  - Suite 2 (`suite = 2`, when the certificate lists X-Wing): `ct2 = HPKE_XWing(info,
    aad = enc1, pt = ct1)`, sent as `enc = enc1 || enc2 (32+1120)` and `ct2 (64)`. Breaking it
    needs both KEMs broken.
  - The sender is not authenticated by HPKE. The wrap is authenticated only because it sits in an
    ACL entry signed by an authorised author.
- **info** = `"aurora-link/v1/wrap\0" || owner_root_hex || "|" || epoch || "|" || device_hex ||
  "|" || key_id_hex || "|" || suite` (`acl.rs:535`, `crypto.rs:223`). It binds the **owner root,
  not the link id**, because genesis wraps exist before the link id does. A wrap moved from
  another link with the same owner carries that link's key id, which is not the one in force, so
  it is refused. If its key id field is edited to match, it no longer opens.
- **Which key encrypts what:** a record body uses the read key of the record's `epoch`. The
  previous-key chain uses each epoch's key (`acl.rs:620-640`). A blob uses its own random key,
  carried in the body and committed by `key_hash`.
- **Key commitment:** XChaCha20-Poly1305 is not key-committing. The key id makes each epoch's key
  a single public value, which every reader checks. A malicious admin who wraps divergent keys is
  caught by the recipients whose key does not match: `read_key` fails for them and their records
  stay `opaque`. It is not caught by anyone else.

## 7. Sync and transport

| Item | Value | Where |
|---|---|---|
| ALPNs | `aurora/link/2` (sync), `aurora/link-join/2` (join), iroh-gossip, iroh-blobs | `sync.rs: ALPN`, `linkd/src/net.rs: JOIN_ALPN` |
| Framing | 4-byte BE length + `serde_json` (not JCS). `MAX_FRAME = 2 MiB`. The first frame of a link or join connection is at most **64 KiB within 30 s** | `sync.rs:27`, `105`; `linkd/src/net.rs:216-217` |
| Session | `hello{v: 2, link, device, acl: the chain tip {term, seq, hash}, heads (at most 128 authors), more}`; `device` must equal the QUIC peer. The side behind asks `acl_want{from, to}` and gets exactly `from < seq <= to` in `acl` frames of at most 256 KiB of entries, at most 8 MiB a minute per (peer, link) (plus one entry), then `acl_done{upto}`; one want is outstanding at a time, the asker asks again after `acl_done` only if its tip moved (refused entries are no progress), and a want the budget cut short is asked again at the next `ping`. A hello alone triggers no ACL transfer. Then queued `propose` frames (and `refusal` back), `evidence` if halted, records per author in seq order (up to 4096 per pass, and within the minute's record budget), the records where heads name different ids (`conflicts`), then `synced { heads, more }`, then live pushes (records, new entries, proposals, refusals). An answer to a hello, its `heads` pages or a `want` ends with `synced`; `more` says it was cut short, and the asker asks again with a `want`: at once if the answer stored something, at its next `ping` if it was empty, never if what came was refused (R8-2). Records that could not be stored are asked for again when that can help (**new**, R9-1): at once when the chain they waited for arrives in this session, at the first `ping` after our tip moved, after a gap at the next `ping`, and for an author over its hourly quota at the first `ping` after the quota admits more (`Admit::OverQuota { until }`). One want is outstanding at a time | `sync.rs: Session::on_frame`, `want_toward`, `answer_hello`, `answer_records`, `want`; `engine.rs: Link::missing_for_authors`, `Link::receive`; `store.rs: Store::quota_frees_at`; `AclChain::range` |
| Session limits | At most 2,400 frames of any kind a minute from a peer, pings and `records` frames included, counted first (**new**, R9-2). At most 120 ACL-side frames a minute from a peer (`acl`, `acl_want`, `acl_done`, `propose`, `refusal`, `evidence`), each evidence check its frames cause costing 8 more (R7-1). At most 120 record-side frames a minute (`want`, `heads`, `synced`, `advert`). At most 16 MiB of records a minute sent in answers (by `Record::frame_cost`). At most 32 MiB a minute of the records the peer sends are looked at; the rest is asked for again at the next ping (**new**, R8-2). What a peer has spent is a `Budget`, kept by the daemon per (link, peer) across all its sessions, so a reconnect does not refill it; a device opens at most 10 sync sessions per link a minute (R8-3). At most 2 sync sessions per (peer, link), inbound and outbound; a session with no frame for 120 s is closed, and each side pings every 45 s | `sync.rs: MAX_FRAMES_PER_MIN`, `Session::acl_frame`, `charge_checks`, `rec_frame`, `answer_records`, `Budget`; `linkd/src/net.rs: SessionCount`, `run_session`, `Net::budget`, `keep_budget`, `SESSION_STARTS_PER_MIN` |
| Locks (round 8; **changed**, R9-3) | Each link is behind its own lock in the daemon; the map of links is locked only to find or add one. Sessions and RPCs of one link run one at a time. Waiting for a link's lock and the work under it run off the async workers (`block_in_place` in a multi-threaded runtime), so a busy link holds up no worker, and so no other link, timer or the RPC socket. `peer_links` (the inbound gates, the dialer) reads each link's kept device sets without its lock. `link.list` and `events.wait` take each link's lock in turn | `linkd/src/daemon.rs: Held`, `LinkCell::with`, `LinkCell::sync_sets`, `off_worker`, `with_link`, `links_by` |
| Store reads (**new**, R8-2) | `Store::range` has a `LIMIT`, and an answer reads pages of 64 rows only until it is full; an ack's receipts are one statement (`Store::delivered_upto`); records are indexed by `(author, received_at)` for the hourly quota's count | `store.rs: Store::range`, `delivered_upto`, `SCHEMA` |
| Membership in a session | Checked on every frame, as a lookup in device sets the chain keeps per held tip and halt (**new**, R9-2: it built the set of every device per frame). A hello from a device not yet known as a member is held, unanswered; we ask it for its chain, and answer once its entries show it is a member. The daemon re-checks the peer before each push and closes the session of a removed device. While halted (**new**, R7-2), a device of the held tip that the narrowed view leaves out still trades the chain's frames and gets ACL pushes and our evidence; its other frames pass unanswered | `sync.rs: Session::on_frame`, `may_sync`, `may_sync_acl`; `acl.rs: AclChain::sync_devices`, `held_sync_devices`; `linkd/src/net.rs: run_session` |
| Equivocation | Two records at one seq are exchanged when heads are compared, so both sides freeze the author on two signed records. A signed head advert naming another id at a held seq freezes the author (`check_advert`). The records sent for heads that name another id count against the 16 MiB record budget, none once it is spent; each claim (author, seq, claimed id) is answered once a minute across the peer's sessions, at most 256 claims a minute (**new**, R9-4) | `sync.rs: Session::conflicts`, `check_advert`, `MAX_CONFLICTS_PER_MIN` |
| Non-member | Sync: after reading the first frame, a peer that is not a member of **that** link is closed with code `1` and an empty reason (`linkd/src/net.rs:316`). At most 256 sync sessions at once. Gossip and blobs: `Gated` admits only devices that are members of **any** of our links (`linkd/src/net.rs:260-295`). Membership here is the held state of a halted link (R7-2); a blob `get` checks the narrowed one. Join: open to anyone, rate-limited, at most two 64 KiB frames, refused unless a live invite and a valid proof are presented. Reasons go only to the local refusal log, which is capped at 1 MiB with one rotated file and stripped of control characters (`linkd/src/daemon.rs:189-210`, `964`) | `linkd/src/net.rs:251-400`; `error.rs:1-5` |
| Gossip (**changed**) | Topic = `BLAKE3("aurora-link/v2/gossip-topic\0" || JCS(genesis entry))`, so the link id in an invite code does not give it. Messages are `HeadAdvert`s signed under `"head"`. An advert counts only when the device that delivered it may sync that link. It wakes the dialer at most once per link every 2 s and clears that peer's backoff. Adverts are hints and never authority. They expose `author, seq, record id, ts` to every topic subscriber. Ex-members keep the genesis entry, so they can still compute the topic | `linkd/src/net.rs:153`, `640-690` |
| iroh-blobs | `push: Disabled`, `get_many: Disabled`, `connected` and `get` intercepted. A `get` must be a whole-blob request, from a connection whose device shares a link with us that lists that blob id. A refused `get` gets `AbortReason::Permission` | `linkd/src/net.rs:405-460` |
| Mailbox | The `mailbox` **role** gets no wraps and stores records `opaque`. It syncs, relays and fetches blobs like any member, within its per-author blob cap. The `--mailbox` daemon flag only shows in status | `linkd/src/main.rs:52`, `linkd/src/daemon.rs:449` |
| Discovery defaults | The n0 preset (pkarr DNS publishing of the node's addresses, n0 relays) and mDNS are **on** unless `--no-n0` / `--no-mdns`. The endpoint binds a UDP socket (`--bind`). `relay.config` emits an iroh-relay allowlist of member device ids | `linkd/src/main.rs:60-70`, `linkd/src/net.rs:465-500`, `linkd/src/rpc.rs:373` |
| Sneakernet | `bundle.export` / `bundle.import`: the whole chain, records and queued proposals (the sequencer includes them on import), verified as if from the wire, with no transport identity | `linkd/src/daemon.rs: bundle_export`, `bundle_import` |

What a mailbox or relaying member sees: every header (author device, seq, signed write time,
epoch, the chain position, size bucket, blob ids and size buckets, deps), the whole ACL chain
(member roots, labels, device certificates, invite public keys, key ids, wrap ciphertexts, every
proposal with its proposer), proposals it relays and refusals, and timing.

## 8. Trust boundaries

```
remote peers --QUIC/iroh--> aurora-linkd (Rust: keys, ACL, store, parsing)
                                 |  JSON-RPC 2.0, one request per line, max 8 MiB
                                 |  stdio (ManagedChild) or Unix socket / named pipe (CLI)
                                 v
                           Python core/link/* --(quarantine stream bifrost:remote:<link>)--> promotion policy --> bus --> agents
```

- The daemon has no Redis credentials and no shell, and it never touches the bus. Admitted
  records leave only as `events.wait` results. Provenance (`fleet`, `fleet_root`, `device`) comes
  from the ACL. The body's `seat` is passed on as `seat_claim` (`engine.rs:980`).
- **The RPC socket has no caller authentication.** Access control is the file system:
  - Unix (**changed**): the socket is `state/link/rpc/linkd.sock`, or, if that path is over 100
    bytes, a per-uid folder in `$XDG_RUNTIME_DIR` or the temp dir (`linkd/src/daemon.rs:84`,
    `Dirs::socket`). Either way `private_socket_dir` (`linkd/src/daemon.rs:229`) tightens our own
    folder to 0700 and refuses one that is not ours or not a folder. So the socket is never
    reachable by another user, even between `bind` and the `chmod 0600` that follows
    (`linkd/src/rpc.rs:722-745`).
  - Windows (**changed**): a named pipe `\\.\pipe\aurora-linkd-<hash>` with
    `reject_remote_clients(true)` and a protected DACL that grants only this user's SID, on every
    instance. The first instance must be the first of its name (`linkd/src/rpc.rs:757-870`,
    `pipe_security`). The Python client (`core/link/client.py`) opens the pipe by name and does
    not check the server's user.
- **What any same-user process with socket access can do:** `identity.init force=true`, which
  replaces the identity (`linkd/src/daemon.rs:409`); membership ops; `link.send` with
  `attachments[].path`, which reads any file the daemon can read and ships it to the link
  (`linkd/src/rpc.rs:554-580`); `blob.get` with `out`, which writes a file anywhere
  (`linkd/src/net.rs:878`); `promotion.record`, which accepts any `by`
  (`linkd/src/daemon.rs:846`); and `daemon.shutdown`. Unknown parameters are refused
  (`linkd/src/rpc.rs:469`).
- **`--trace-rpc` (changed)** logs each line with secret fields redacted by name (phrase,
  passphrase, code, secret, key material). A line that is not JSON is logged only as its length
  (`linkd/src/rpc.rs:421-460`, `redacted`).
- **Quarantine and promotion** happen in Python, not the daemon. Admitted records go to the Redis
  stream `bifrost:remote:<link_id>`, which no seat reads by default (`core/link/quarantine.py`).
  `promote.py` applies `state/link/<link_id>/promote.toml`. That file is local, never synced, and
  `mode = "manual"` by default. Rules may never auto-promote `handoff`, and promoted mail carries
  `authority: none` (`core/link/promote.py`). The daemon's `promotion.record` only records
  idempotence and refuses records that are not `admitted`. The guarantee that remote mail never
  reaches agents without local policy therefore rests on agents being unable to reach the RPC
  socket, the Redis quarantine stream or `promote.toml`.

## 9. Stated threat model, non-goals and documented residual risks

There is no written threat model document. The design docs (ADR 0011, `bridge.mdx`), the module
docs and [findings.md](findings.md) state the following.

**Stated goals**

- Only members with read access read content, kinds and seat names. A mailbox cannot read what it
  stores. It does see headers, size buckets, the ACL chain and timing (ADR 0011, `bridge.mdx`).
- No record forgery. Replays are no-ops. A gap, reorder or forgery is visible (`engine.rs` module
  doc).
- A removed member cannot read mail written after the rotation lands, or write past its cut.
- Every membership action is checked, on every replica, against the chain's state at the point it
  applies, and nobody but the term's sequencer can place an entry (`acl.rs` module doc).
- **The sequencer is trusted for order and time, and for nothing else.** It cannot act with anyone
  else's authority (`acl.rs` module doc, ADR 0011).
- A non-member learns nothing from refusals: one close code, no reason.
- Two implementations of the signature scheme are themselves a risk, so there is one Rust
  implementation, and Python calls the same crate through PyO3 (`aurora-rs/README.md`).
- Admission never implies authority over agents (`engine.rs`, `core/link/promote.py`).

**Explicit or implicit non-goals in the code**

- Liveness of membership changes without the sequencer: they queue (records keep flowing).
- Byzantine fault tolerance of the sequencer: it can delay, reorder or censor valid proposals, and
  pick `ts` within each replica's 600 s skew; a compromised one is replaced by the owner's takeover.
- Metadata privacy against members and mailboxes, and against iroh/n0 infrastructure.
- Forward secrecy within an epoch, and history secrecy against newly admitted members.
- Protection of plaintext at rest (`records.body` is a plaintext cache on purpose).
- Authenticated seat identity: `seat` is a claim, vouched for by the device signature.
- KEM key rotation for a live device (only removal).
- Consensus on record admission limits: the per-author hourly quota and the join door's limits use
  each receiver's own clock and holdings.

**Residual risks the code documents** (findings, "Known trade-offs" of rounds 5, 6 and 7):

- The sequencer is a liveness dependency and a trusted orderer; a takeover needs the recovery phrase,
  and does not itself remove the lost or stolen device.
- An equivocation halts membership and new mail until the owner's takeover; while halted, a
  replica grants only what both its held tip and the prefix grant. A split that the equivocator
  carries past a handoff on both branches, to other members' devices, is an alarm, not a halt.
- One want for the whole chain is answered in full, up to the budget: the bound is per minute and
  per (peer, link), not per request. Records likewise: at most 16 MiB a minute sent to a peer in
  answers, and 32 MiB looked at from it, so a large backlog takes minutes (round 8). A backlog
  over an author's hourly quota arrives an hour at a time (round 9). Every frame counts against
  2,400 a minute per (link, peer); past it the session ends, and the next minute's session takes
  up where it left off (round 9).
- A record may name an old position and its epoch, as before.
- Proposals expire 7 days after their proposer signs them, and a takeover voids every proposal
  signed before it.
- A refusal is charged to the proposal's origin (its proposer's root, or the invite for a join),
  once per proposal, and to the session peer only for what it could have checked itself. A replay
  is checked again but charged to nobody (round 8). The charges live in memory, so a restarted
  daemon forgets them. Budgets are per device and link, shared across sessions: a member with
  several devices, or in several links, has a budget for each.
- Evidence at the store's cap (256 pairs) that would only raise an alarm is not kept and raises
  none. Expensive ACL work (an evidence check, a proposal check) runs under the link's own lock,
  bounded per minute and per (peer, link), and off the async workers (round 9). `link.list` and
  `events.wait` wait for the frame in progress on each link.
- `ct_hash` rather than `ct` is signed, so retention can drop bodies.
- Head adverts are hints only; a leaked invite code is a narrow risk (single-use, short-lived).
- Wrap `info` binds the owner, not the link, by necessity.

**Test coverage a reviewer should know.**

- The vectors (`aurora-rs/link-vectors/*`, checked by `aurora-rs/link/tests/vectors.rs`) pin
  records, fingerprints, invite codes, an ACL chain with a handoff and a root takeover (its lost
  entries in any arrival order), and an equivocation. They do not pin wraps, X-Wing, key changes or
  JCS edge cases.
- Four property tests: random proposal sequences, where two replicas applying one chain in any
  chunking, and a restore, agree with the sequencer at every position
  (`replicas_of_one_chain_always_agree`); random actions on four replicas with random sessions,
  after which all hold one chain (`replicas_that_sync_agree`); and random proposal sequences with
  evidence injected at a random position by insert, evidence frame or a pair at the next
  position, after which no device is active (or has a higher role) in what the replica acts on
  than at its held tip, and nothing is sealed under an older epoch
  (`evidence_never_widens_access_or_seals_under_an_older_epoch`); and random histories followed
  by random floods of evidence and of proposals (valid, refusable, outsiders', forged, joins on
  unknown and dead invites) at a relay or the sequencer, after which evidence and proposal rows
  are within their caps, nothing was included, and nothing is granted beyond the held tip
  (`floods_stay_within_their_caps_and_never_widen_access`).
- The fuzz targets check only for panics; `frame.rs` drives a live session and `acl_entries.rs` the
  chain's insertion, positions, ranges, proposal checks and evidence.
- Each probe shape of rounds 5 to 9 has a permanent test (findings, Rounds 5 to 9). Each test of
  rounds 6 to 9 was checked to fail with its fix disabled. Round 8's R8-1 and R8-2 tests were also
  run first against the round-7 code, and failed there. Round 7 adds a daemon test over real iroh
  endpoints (`net_tests.rs: r7_2_...`), and round 8 adds another (`r8_3_...`: budgets across a
  reconnect, and rated session starts). Round 9 adds `r9_3_peer_links_...` (the inbound gate does
  not wait for a busy link) and an ignored measurement of the `q4` shape through `with_link`. In
  tests, every `settled_above` answer is compared with
  the round-7 scan. Untested: the gossip sender check, the blob fetch length limit, and the
  Windows pipe DACL.

## 10. Questions we most want an outside reviewer to answer

The first eight are about the sequenced chain (section 4), which is new in round 5 and hardened in
rounds 6 and 7.

1. **Fork choice and truncation.** `AclChain::insert_one` lets an entry with a higher term (or a
   takeover over a handoff in the same term) replace a replica's suffix, after checking it on the
   state folded from a snapshot. Can a replica end on a different chain than a peer holding the same
   entries, in any arrival order, chunking or interleaving with equivocation evidence? Is "the
   first differing entry's term decides" the right rule when a takeover names an `after` deep in the
   past while a later handoff term exists?
2. **What the sequencer can still do.** It is trusted for order and time only. Within that, can it
   turn order or `ts` into authority it should not have: for example by reordering a removal after
   the removed member's own pending proposals, picking `ts` to make an invite expire or a grace pass
   early (bounded by each replica's 600 s skew and monotonicity), or censoring the owner's handoff?
   Which of these matter, and should replicas refuse a sequencer whose `ts` runs far behind their
   clocks?
3. **Takeover authority.** A takeover is signed by the genesis owner root and names the new
   sequencer device. Is the owner root the right authority (it is also the only signer of device
   certificates, and lives offline)? Is the takeover's binding (`{link, term, after, sequencer}`)
   enough, given that a captured takeover can be replayed by its named device at that one position
   only? Should the takeover also remove the old sequencer device?
4. **Equivocation handling.** Evidence is two entries at one position on one prefix, each of which
   applies on its own there (`check_equivocation`, `note_evidence`, `applies_alone`). Can an
   attacker without the term's sequencer key (or the root, for takeovers) make a replica halt, or a
   halted replica refuse the owner's takeover? While halted, a replica acts on its held state
   narrowed to the prefix's grants (`AclState::narrowed`): is anything still read from the prefix
   alone (an invite, a pending join, a key) that a removal past the prefix should have retired?
   The transport and the chain's own frames read the held state instead (R7-2): does that let a
   device the narrowed view leaves out do anything but trade the chain? Evidence is screened
   before it is checked (one pair per position and signer, one alarm per signer, nothing at or
   above a standing halt): can an attacker use "the first pair wins" to pre-empt a pair that
   would halt?
5. **Proposals.** A proposal is checked against the current state, not its base; it carries an
   expiry, and a base before the latest takeover voids it. Is replay closed (included ids per
   chain, the nonce, the expiry, the takeover rule)? Should a proposal also bind the proposer's view
   of the target (for example "remove member X as of seq N")? Are the relay rules (members only,
   joins on a live invite, only what holds on the relay's chain, a share per origin) and the
   charging split (the peer for what it could have checked, the origin for a refusal or anything
   that depends on the chain, nobody for a base the relay cannot judge yet) enough against a
   member that floods valid proposals, or that exploits a relay behind the sequencer?
6. **Evidence below a later term start.** Evidence below a term begun by a root takeover, or by a
   device of another member than the evidence's signer, is an alarm, not a halt
   (`AclChain::settled_above`), so an ex-sequencer's key holds no lasting veto. The price: a
   sequencer that keeps two branches apart until it has handed off on both, to other members'
   devices, leaves both sides running with an alarm until the owner's takeover. Is that the right
   trade, is "another member" the right test (a self-handoff does not count), and does fork choice
   (first differing entry, the incumbent on a tie) keep a branch that climbed terms from winning?
   Round 7 lets a self-started term settle once the signer's device cannot sequence and the owner's
   fleet or another member removed or demoted it (R7-5): an owner fleet's own removal counts, a
   non-owner member's removal of its own old device does not. Is that the right line?
7. **Action ids as keys.** Invites are keyed by the issuing entry's hash (own action) or the
   proposal id (proposal), and joins by their proposal id. Can two actions collide, or can an invite
   code for a proposal that was refused ever be satisfied by another action?
8. **Records and positions.** `Link::position` and `check_at` judge a record at its named position
   and its write right there and now; a position past the prefix waits, one whose term the chain
   passed is lost for good. Can a writer abuse old positions (old epochs) or positions far in the
   future (a record that waits for ever, blocking only its own feed)? Is the lost rule ("the
   chain's term at that seq, or at its end before it, is later") complete?
9. **Sync budgets.** One want for the whole range is answered in full, up to 8 MiB of ACL entries
   and 16 MiB of records a minute per (peer, link), shared by that device's sessions (at most 2 at
   once, 10 new ones a minute). Is that enough against a member that multiplies links or devices?
   Are the "one want outstanding, resumed at a ping" rules free of stalls, for both the chain
   (`Session::want_toward`, `acl_done`) and records (`Session::want`, `synced { more }`)?
10. **Self-asserted time.** Records still carry an author-claimed `ts`, bounded by the receiver's
    clock, the author's certificate, the previous record and the named position's `ts`. Can a member
    move retention or certificate checks to its advantage?
11. **Key ids and divergent wraps.** Does the key id close the divergent-key attack, given that only
    the recipient can check its wrap and that a rotating key holder can still wrap junk (4.6)? Is
    binding `owner|epoch|device|key_id|suite` in HPKE `info` enough without the link id?
12. **The X-Wing nesting.** Is "HPKE-X25519 inside HPKE-X-Wing with `aad = enc1` and the same
    `info`" a sound hybrid, compared with a single combined KEM?
13. **Device key reuse.** One Ed25519 key is the iroh TLS identity (and pkarr signer under the n0
    preset) and our protocol signer. Is the `aurora-link/v1/<purpose>\0` prefix enough separation?
14. **The join door.** The door hands the whole chain to anyone holding a live code (or to the device
    whose join used it), relays a join it cannot include, and waits up to 20 s. Is that enough, and
    is the offline bundle join (which skips the inviter-clock check) acceptable?
15. **The local trust boundary.** The RPC has no caller authentication; its methods can read and
    write arbitrary paths, record promotions, and now take the recovery phrase for a takeover. Agents
    typically run as the same OS user. Is the quarantine guarantee real?
16. **Equivocation of record feeds and metadata.** Record freezes are local and permanent, with
    conflicting records exchanged between session peers: is that adequate with relays? What do the
    headers, the signed write time, the chain position, relayed proposals and the gossip adverts
    reveal to a mailbox or an ex-member?

## 11. Doc/code mismatches

The state after round 9's docs pass on 2026-10-11. Rows fixed in earlier rounds are left out.
Round 7 updated `bridge.mdx`, `link-two-fleets.mdx` and ADR 0011 for the relay and refusal rules,
the bounded evidence, the retired device's alarm and the transport during a halt. Round 8 updated
`bridge.mdx` for the once-per-proposal charge, the record budget and the rated sessions. Round 9
updated it for the backlog over the hourly quota, every message counting, and busy links.

| Claim | Source | State |
|---|---|---|
| "The link then stops at the last entry everyone agrees on" (a halt goes back to the prefix's member list); "the default takeover continues after the last good entry" | `bridge.mdx`, ADR 0011, `link-two-fleets.mdx`, `agent_cli.py --after`, `link.takeover` | **Fixed in round 6.** All describe the narrowed halt (the held list, granting only what the last agreed entry grants too, no new mail), the alarm-only case below a later term, and `--after` (default: the held tip; required while halted below it, with what each choice drops) |
| `--mailbox`: "Pull-only mailbox: stores and serves ciphertext, never holds a read key." | `linkd/src/main.rs` | **Still a mismatch** (code doc). The flag is only reported in `daemon.status`. "No read key" comes from the `mailbox` role. A mailbox also gets live pushes, so it is not pull-only |
| `identity.renew` "needs ... the passphrase for root.age" | earlier `linkd/src/rpc.rs` | **Fixed earlier**: the summary says root.json |
| "Every protocol except join refuses a device that is not a member of any of our links, with one uniform close code" | `linkd/src/net.rs` module doc | **Still a mismatch** (code doc). A blob `get` from a member for a blob it may not have is refused with iroh-blobs' `AbortReason::Permission`, which is distinguishable. This leaks only to members |
| Rotation wording ("an admin's daemon appends it", "the designated device (the lowest admin holding the key)") | `core/link/cli.py`, `core/link/health.py` | **Fixed in round 5.** Both now say the sequencer appends it, and takes one from any key holder after 1 h |
| Membership described as a forking, merging log | `bridge.mdx`, ADR 0011, `link-two-fleets.mdx` | **Fixed in round 5.** All three describe the sequencer, proposals, handoff, takeover and equivocation; ADR 0011 records why the DAG was replaced |

`docs/ARCHITECTURE.md` describes the link daemon's role, not its security rules, and needed no
change.
