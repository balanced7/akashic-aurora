# Fleet links: review findings and their fixes (2026-10-11)

This file lists what an internal clean-room review of the link composition found, and what the fix
did about each finding. Two reviews ran: a **crypto review** (ids 1-11) and a **protocol review**
(ids A1-A14, B1-B2). Each reviewer read only the code, with no context from the people who wrote
it. Writing [brief.md](brief.md) turned up two more, **F1** and **F2**, each reproduced against
commit `d9faa07b`.

- **Base:** commit `d9faa07b` plus the fix. The table names functions, not lines, so it survives
  edits.
- **Sources:** the diff and the tests it adds. Each name in the "Pinned by" column is a test that
  exists. `cargo test -p aurora-link -p aurora-linkd` passes: 83 unit tests in `aurora-link`, 4
  vector tests, and 11 in `aurora-linkd` (1 ignored, a measurement).
- **Severity:** as the reviewer graded it.

## Summary

| Status | Count | Ids |
|---|---|---|
| Fixed | 25 | 1, 2, 3, 4, 5, 6, 7, 8, 10; A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12; B1, B2; F1, F2 |
| Partly fixed | 1 | 9 |
| Open | 3 | 11, A13, A14 |

F1 is A1 and F2 is A7, found on their own. A8 is crypto 4 seen from the protocol side. That leaves
26 distinct problems. All the critical, high and medium ones are fixed. The three open ones are
low or informational.

## Crypto review

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| 1 | medium-high | A wrap made under a rotation that lost a fork can be filed under the winning rotation's epoch. Wraps named only an epoch, not which key. | Fixed | `link/src/crypto.rs`: `key_id` (SHA-256 over context, epoch and key). `link/src/acl.rs`: `KeyChange.key_id` and `prev_id`; `Wrap.key_id`; `AclState::check_wrap_shapes` (a wrap's id must be the id in force); `plan_key_change` (`prev_id` must be the current key's id); `check_key_id`, called by `read_key` for every key unwrapped or unsealed; `wrap_info` (the key id is in HPKE `info`) | `acl/tests.rs`: `a_wrap_of_a_losing_rotations_key_is_refused`, `a_wrap_issued_beside_a_rotation_is_refused_not_misfiled`; `crypto.rs`: `key_ids_bind_epoch_and_key` |
| 2 | medium | The joiner never checked that the log it adopts is the link the code names. It also compared the owner's fingerprint with the code's, which carries the inviter's. | Fixed | `link/src/invite.rs`: `InviteCode::check_log`, `inviter`. `link/src/sync.rs`: `join_entry_for` (checks before anything is signed). `linkd/src/daemon.rs`: the join entry goes through `join_entry_for`; `joined_summary` computes the safety number and `fingerprint_matches_code` against the inviting fleet. `linkd/src/net.rs`: `Net::join` refuses a handed-back log whose genesis hash is not `code.link` | `sync.rs` tests: `a_join_checks_the_link_id_and_the_fingerprint_of_the_fleet_that_invited`. No test covers the genesis check in `Net::join` |
| 3 | medium (defence in depth) | HPKE `info` binds owner, epoch and device but not the link. Two links with one owner had interchangeable wraps, and nothing tied a wrap to its suite. | Fixed | `link/src/acl.rs`: `AclState::wrap_info` adds the key id. A wrap moved from another link carries that link's key id and is refused (`check_wrap_shapes`). If its id field is edited, it no longer opens. `link/src/crypto.rs`: `wrap_info` adds the suite byte. The link id is still not in `info`, because genesis wraps exist before the link id | `crypto.rs`: `a_wrap_is_bound_to_its_suite`. No test moves a wrap between links |
| 4 | low-medium | Certificate expiry was checked at the author's own `ts` for ACL entries, and not at all for records. | Fixed | `link/src/engine.rs`: `Link::authorised` refuses a record whose signed `ts` is at or past `not_after`, or more than the skew before its ACL head. `Link::receive` refuses one dated in the future or before its predecessor. `Link::write`: an expired device does not write. `link/src/acl.rs`: `AclLog::check_structure` refuses a new leaf entry whose author's certificate expired more than `CERT_EXPIRY_GRACE_S` (24 h) before the receiver's clock | `engine/tests.rs`: `records_need_a_certificate_valid_at_their_signed_time`; `acl/tests.rs`: `a_long_expired_device_cannot_add_backdated_entries` |
| 5 | low | No key commitment. A malicious admin could wrap different keys to different devices, and one blob reference could open to two plaintexts. | Fixed | Epoch keys: the key id (finding 1) commits each epoch's key in the log, and every reader checks the key it unwraps against it. Blobs: `link/src/record.rs`: `BlobRef.key_hash`, `blob_key_hash`, checked in `Body::check` and `open_blob`. The record-body AEAD is still XChaCha20-Poly1305, which does not commit to its key on its own | `crypto.rs`: `key_ids_bind_epoch_and_key`; `record.rs`: `blob_references_commit_to_their_key` |
| 6 | low | `serve --trace-rpc` logged whole request and response lines, with phrases, passphrases and invite codes. | Fixed | `linkd/src/rpc.rs`: `secret_field`, `redact_value` and `redacted`, used by `handle_line`. A line that is not JSON is logged only as its length. Redaction goes by field name, so a secret under an unexpected name would still be logged | `rpc.rs`: `trace_lines_carry_no_secrets` |
| 7 | low | Secrets were left in memory: SLIP-10 intermediates, the BIP39 seed, the device file's base64 strings and the opened root. | Fixed (Rust side) | `link/src/identity.rs`: `slip10_ed25519` and `split64` return `Zeroizing`; `root_from_phrase`; `Device::to_json` (a pre-sized buffer, then `DeviceFile::wipe`); `Device::from_json` and `keys_of`; `root_kek`; `seal_root`; `open_root`. `crypto::KemSecrets` zeroizes on drop and no longer derives `Clone`. The phrase still crosses JSON-RPC and Python once, at `identity.init`, and Python cannot wipe it | No test checks the wiping. The SLIP-10 spec vectors in `identity.rs` pin that derivation did not change |
| 8 | low | `write_secret` used a fixed temp name (a planted symlink was followed), relied on the umask, and did not check the folder. | Fixed | `linkd/src/daemon.rs`: `write_secret` (random temp name, `create_new`, explicit 0600, rename, cleanup on error); `private_dir` (0700, ours, not a symlink) | `daemon.rs`: `a_secret_is_written_0600_in_a_0700_folder_and_never_through_a_planted_link` |
| 9 | low / info | Padding and metadata: blobs were unpadded, so their exact size showed, and the header shows a lot to a mailbox. | Partly fixed | `link/src/record.rs`: `seal_blob` pads to a power of two of at least 4 KiB (`blob_ct_len`); `open_blob` checks the padding is zero; `Record.blob_sizes` signs each padded size; `Record::verify` checks they are buckets. Still visible to any holder: author device, seq, signed write time (new), epoch, ACL head, deps, body bucket, blob ids and buckets, the whole ACL log, and timing | `record.rs`: `blobs_are_padded_to_buckets`, `blob_sizes_are_signed_and_bucketed` |
| 10 | info | `open_root` took Argon2 parameters from the file with no lower bound, and the parameters were not authenticated. | Fixed | `link/src/identity.rs`: format v2 (`ROOT_FORMAT`). `root_aad` binds `v, kdf, m_kib, t, p, salt` into the AEAD data. `open_root` accepts only m 64-256 MiB, t 3-8 and p 1-4. The passphrase is NFC-normalised (`nfc`). A v1 file is refused and must be sealed again (`identity.init --force`) | `identity.rs`: `a_sealed_root_refuses_kdf_parameters_outside_the_window`, `the_passphrase_is_nfc_normalised_on_seal_and_open` |
| 11 | info | An author can sign a second entry on the same parent (a re-signed entry), which forks the log. | Open | No change. Such a fork resolves like any other: by `seq`, then branch rank, and removals win causally (A1). The hash tie-break can be ground (A13) | none |

## Protocol review

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| A1 | critical | Backdated entries. A removed admin (or its invitee) builds on a head from before the removal. Ordering by `seq` applied that entry first, and the removal was dropped. Same as F1. | Fixed | `link/src/acl.rs`: `AclLog::resolve` now runs `Dag::causal` (each entry where its author stood), then `Dag::expired_joins`, then `Dag::merged`. When a removal, revocation or admin demotion applies, `Dag::victims_of` and `Dag::victims` drop every concurrent entry that depends on what it took away. If one had already applied, the merge runs again without it. In the merge, `plan_removal_key` never drops a removal because its rotation no longer fits: it files the wraps that still fit and leaves a rotation due | `acl/tests.rs`: `a_backdated_join_via_a_removed_admins_invite_is_dropped`, `a_backdated_join_via_a_revoked_invite_is_dropped`, `a_backdated_join_via_an_expired_invite_is_dropped`, `a_removed_device_cannot_act_on_an_old_branch`, `a_removal_stands_when_a_concurrent_reader_lacks_a_wrap` |
| A2 | high | A member that leaves, or removes its own device, chooses its own cut, and may name one far past its real head. | Fixed | `link/src/acl.rs`: `AclState.provisional_cuts`. In `apply_inner` (`RemoveDevice`), an admin with authority over the member may lower a self-chosen cut once. An admin's cut is final. `link/src/engine.rs`: `Link::upkeep` does this on its own, through `cuts_to_lower` and `lower_cut`. It lowers the cut to the last seq that admin's daemon holds from the device. Records the leaver wrote before leaving that the admin had not yet received are cut off with it | `acl/tests.rs`: `a_self_chosen_cut_is_provisional_and_an_admin_can_lower_it`, `an_admins_cut_cannot_be_reopened`; `engine/tests.rs`: `upkeep_lowers_a_self_chosen_cut_to_the_head_it_holds` |
| A3 | high | `resolve` cloned the whole state per entry and was quadratic on a long log. Nothing capped the log's growth. | Fixed | `link/src/acl.rs`: `Dag` splits the log into runs with no fork and copies state only where it forks. `AclLog::check_structure` adds `MAX_ACL_ENTRIES` (100,000) and `MAX_ENTRIES_PER_DEVICE_HOUR` (120, by `ts`). `apply_inner` (`AddDevice`) takes a renewal only inside its renewal window. A log with many forks has not been measured | `acl/tests.rs`: `a_long_linear_log_resolves_fast` (20,000 entries: 149 ms release, 410 ms debug), `one_device_cannot_flood_the_log`, `a_renewal_far_from_expiry_is_refused` |
| A4 | medium | A joiner that cut a device before its accept made the accept fail, and one failed accept stopped `upkeep` before the due rotation. | Fixed | `link/src/engine.rs`: `Link::accept` wraps only live devices. `Link::upkeep` handles each item on its own, and a failure becomes an alarm | `engine/tests.rs`: `upkeep_wraps_only_live_devices_and_still_rotates` |
| A5 | medium | A reader demoted to mailbox kept reading new mail. The demotion only marked a rotation due, and writers kept sealing under the old key. | Fixed | `link/src/acl.rs`: `SetRole.rotate`. Where its author stood, a change that takes read access away must carry the new key (`apply_inner`). `link/src/engine.rs`: `Link::set_role` builds it. `Link::rotation_gate`, called by `write`, refuses new mail while a rotation is due. The exception is the device whose turn it is to rotate: it rotates first. Receipts wait too. A writer that has not yet seen the change still seals under the old key | `acl/tests.rs`: `a_downgrade_to_mailbox_rotates_inline`; `engine/tests.rs`: `writers_wait_while_a_rotation_is_due` |
| A6 | medium | Two records at one seq went unnoticed when peers held different ones, because heads carried only seqs. | Fixed | `link/src/sync.rs`: `HeadRef` and `heads_of` (a head is a seq plus a record id). In `conflicts`, each side sends its record and asks for the other's, so both freeze the author on two signed records. In `check_advert`, a signed advert naming another id at a held seq freezes the author. `linkd/src/net.rs`: gossip adverts go through `check_advert` | `sync.rs` tests: `two_records_at_one_seq_are_caught_when_heads_are_compared`, `an_advert_for_another_record_at_a_held_seq_freezes_its_author` |
| A7 | medium | Body stripping. Retention was judged by the named ACL entry's `ts`, so a relay could strip a fresh record. The id excludes `ct`, so the whole copy then counted as a duplicate. Same as F2. | Fixed | `link/src/record.rs`: `Record.ts`, signed in the header. `link/src/engine.rs`: `Link::receive` refuses a stripped copy until `ts` plus retention has passed. `Link::refill` and `store.rs`: `Store::fill_body` let a later whole copy fill in a stripped row. `Store::retire_before` goes by `written_at` (the signed `ts`, never later than arrival) | `engine/tests.rs`: `a_stripped_copy_is_judged_by_its_write_time_and_a_whole_copy_refills_it` |
| A8 | medium | Expired certificates: a stolen key whose certificate had expired could still write records, and could add ACL entries backdated into its lifetime. | Fixed | Same as crypto finding 4 | Same as crypto finding 4 |
| A9 | medium | Blob flooding and cross-link fetches. Any record's header listed blobs, with no size cap. A blob listed in one link was served to a peer from another. | Fixed | `link/src/engine.rs`: `register_blobs` lists blobs only from a body opened and admitted here, or, on a mailbox, from a whole record's signed header. `blob_room` caps a link at 1 GiB (`MAX_LINK_BLOB_BYTES`) and a mailbox at 256 MiB per author. Also `blob_allowed` and `wanted_blobs`. `record.rs`: `MAX_BLOB_BYTES` (64 MiB). `store.rs`: blobs keyed by `(id, record_id)`, with author and padded size. `linkd/src/net.rs`: a blob is served only for a link the peer shares that lists it. `fetch_listed_blob` stops at the signed length | `engine/tests.rs`: `blobs_are_listed_only_from_admitted_bodies_and_within_caps`. No test covers the fetch length limit |
| A10 | low | The join door was ungated. A `join` needed no verified `join_hello` on the same stream. The proof was checked only inside the log. Nothing limited attempts. The refusal log grew without bound and took newlines from the wire. | Fixed | `link/src/sync.rs`: `JoinDoor` (one verified hello, then one join with the same invite); `serve_join`, now private (the join must extend the current head; the signature and the proof are checked before the log sees it); `invite_live` (the inviter must still be an active admin). `linkd/src/net.rs`: `Limiter`; `JoinProto::on_accepting` (20 a minute per IP, before the handshake); `JoinProto::accept` (6 a minute per device id, 8 joins at once). `linkd/src/daemon.rs`: `log_refusal` (control characters dropped, 300 characters at most); `append_capped` (1 MiB, one rotated file) | `sync.rs` tests: `the_join_door_wants_a_hello_the_current_head_and_a_live_inviter`; `net_tests.rs`: `the_join_limiter_caps_each_key_per_window_and_bounds_its_table`; `daemon.rs`: `the_refusal_log_is_capped_and_keeps_one_rotated_file` |
| A11 | low | Gossip topics were not gated. The topic id came from the link id, which invite codes carry. An advert from any device passed if its author was known. | Fixed | `linkd/src/net.rs`: `topic` hashes the whole genesis entry, signature included, under `aurora-link/v2/gossip-topic`. An advert counts only when the device that delivered it may sync that link (`sync::may_sync`). Otherwise it goes to the refusal log. `advert_wake` wakes the dialer at most once per link every 2 s | `net_tests.rs`: `the_gossip_topic_needs_the_log_and_survives_a_rotation`. No test covers the sender check |
| A12 | low | A device removed mid-session kept its live session and kept getting pushes. | Fixed | `link/src/sync.rs`: `Session::on_frame` checks membership on every frame. A hello from an unknown device is held until its ACL frames prove it is a member. `linkd/src/net.rs`: `run_session` checks the peer again before each push and closes the session | `sync.rs` tests: `a_removed_peer_is_dropped_on_its_next_frame` |
| A13 | low / info | Fork-rank steering: the last tie-break, the lower entry hash, can be ground until an entry sorts first among concurrent siblings. | Open | Documented in the `acl.rs` module doc. The rank only orders entries that both hold. It cannot make an entry beat a removal, which wins causally (A1) | none |
| A14 | info | Label spoofing: a joining fleet picks its own label, so it can choose one that looks like another member's. | Open | No change. A label must be unique, at most 64 characters and not 64 hex digits, but it is still the joiner's free choice. The safety number is the real check | none |
| B1 | low-medium (Windows) | The Windows RPC pipe used the default DACL. | Fixed | `linkd/src/rpc.rs`: `pipe_security::owner_only` (a protected DACL that grants only this user's SID). `serve_socket` (Windows) uses it on every instance, and the first instance must be the first of its name | none: Windows only; CI's Windows link job runs the daemon with it |
| B2 | low | The Unix socket was chmodded after `bind`, in a folder that was not checked. | Fixed | `linkd/src/daemon.rs`: `Dirs::socket` puts it in `state/link/rpc/`. `private_socket_dir` now always runs: it tightens our own folder to 0700 and refuses one that is not ours or not a folder. `linkd/src/rpc.rs`: `serve_socket` | `daemon.rs`: `the_rpc_socket_is_bound_inside_a_private_folder` |

## The brief's own findings

| Id | Severity | Finding | Status | Fix | Pinned by |
|---|---|---|---|---|---|
| F1 | critical (as A1) | A removed admin can undo its own removal with a backdated fork (section 4.6 of the brief at `d9faa07b`). | Fixed | Same as A1 | Same as A1. `a_backdated_join_via_a_removed_admins_invite_is_dropped` is the brief's scenario |
| F2 | medium (as A7) | A relay can strip the body from a fresh record (section 5.4 of the brief at `d9faa07b`). | Fixed | Same as A7 | Same as A7 |

## Known trade-offs of the fix

The fixers reported these, and each one follows from the code above.

1. **Writers block while a rotation is due.** A removal or demotion may not carry the new key. Then
   `Link::write` refuses new mail on every device except the one designated to rotate. The
   designated admin rotates at once. Any other admin rotates after `ROTATION_GRACE_S` (1 h). If no
   admin holding the key is online, mail waits.
2. **An honest join can be dropped.** `Dag::expired_joins` drops a join when the log holds a
   concurrent entry dated at or after its invite's expiry. So a join that reaches the network after
   such an entry is dropped, even if the joiner acted in time.
3. **Ex-members can still compute the gossip topic id.** The id comes from the genesis entry, which
   an ex-member keeps. Its adverts are ignored, because the device that delivers an advert must be
   able to sync that link. If it is still a member of another of our links, it passes the
   connection gate. It can then subscribe and see adverts (author, seq, record id, time).
4. **Certificate expiry and the rate caps are local admission, not consensus.** These checks use
   what the receiver holds, and its own clock, when an entry arrives: the expired-leaf rule,
   `MAX_ACL_ENTRIES`, `MAX_ENTRIES_PER_DEVICE_HOUR` and the join limits. So two members can admit
   different sets for a while. The future-skew check already worked this way.
5. **The Python client does not check the Windows pipe server's user.** `core/link/client.py` opens
   the pipe by name. The DACL keeps other users out of the daemon's pipe. The first-instance flag
   makes the daemon fail rather than share a name someone else holds. But a client started while a
   squatter holds the name would talk to the squatter.
6. **Two admins can lower the same self-chosen cut at once.** The second lowering is refused in the
   merged order and dropped. Nothing breaks, but no admin is designated for it.
7. **A blob that fails the size check stays in the store untagged.** iroh-blobs has no public
   delete. It is never tagged or served as fetched, and `open_blob` checks the content anyway.

## Notes for whoever reads the tests

- A few doc comments in `acl/tests.rs` use other ids than the table above.
  `a_wrap_of_a_losing_rotations_key_is_refused` says A4,
  `a_long_expired_device_cannot_add_backdated_entries` says A6,
  `a_renewal_far_from_expiry_is_refused` says A3, and the first backdated-join test says "A1 / B3".
  The table follows the review ids.
- The vectors changed with the formats. Headers in `link-vectors/records.json` now carry `ts` and
  `blob_sizes`. `link-vectors/acl-fork.json` now carries key ids.
- The store schema is now version 2. A version-1 store is refused (`Store::open`), and its link
  must be synced again.

## Round 2

An independent re-review of the round-1 fixes found the problems below, and reproduced C1, H1,
H2 and M1 with a probe crate. Each one is fixed here except where the status says otherwise.

- **Base:** the round-1 fix (commit `29741fcc` in the `link-review` worktree) plus this round.
  Like the tables above, this one names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 103 unit tests in
  `aurora-link` (two of them property tests), 4 vector tests, and 11 in `aurora-linkd` (1
  ignored, a measurement). The Python link tests pass against the new wheel and daemon (172).
- **Design change.** ACL entries are now multi-parent: `prev` is the sorted set of open heads the
  author held (at most `MAX_PARENTS`, 16), and `aseq` counts the author device's own earlier
  entries in the entry's causal past. "Where its author stood" is `Resolve(anc(e))`, the
  resolved state of the entry's whole causal past, and the merged state is `Resolve(all)`.
  Records name the set of ACL heads their writer stood on. The `acl.rs` module doc states the
  rules. [brief.md](brief.md) describes the round-1 design; its sections 4.1 to 4.6 and 5.3 are
  superseded by the module docs of `acl.rs` and `engine.rs`.
- **Formats changed.** ACL entries (`prev` is a list, new `aseq`), record headers (`acl` is a
  list), the join proof (binds the parent set), and the store (schema 3, which also keeps each
  entry's facts). A store of schema 2 is refused and its link must be synced again. The vectors
  and the fuzz seeds were regenerated.

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| C1 | critical | Single-parent entries never merge. With the head on a branch that lacks a concurrent key change, every later key change and every writer's record is refused for good, and an invite on a non-head branch is unusable. | Fixed | `link/src/acl.rs`: `Entry.prev` (a parent set) and `Entry.aseq`; `AclLog::parents_for`, `next_seq`, `append` (every append names every open head, so the log returns to one head); `AclLog::resolve`, `Dag::after_states` and `Dag::where_stood` (each new entry against `Resolve(anc(e))`, computed from its latest cut vertex, `Node.tparent`, the lowest common ancestor in the tree of cut vertices); `Dag::scan` (the merged reading, shared by `Resolve(all)` and the pasts of merges); `AclLog::state_at`, `epoch_for`, `resolve_named`. `link/src/record.rs`: `Record.acl` is a head set. `link/src/engine.rs`: `Link::write` names the heads and seals under their epoch; `Link::authorised` checks the record's epoch against the heads' past; `Link::base` builds each op on the state it will stand on. `link/src/sync.rs`: `serve_join` wants `prev` to be the door's head set; `join_entry` builds on it | `acl/tests.rs`: `c1_a_branch_beside_a_rotation_merges_and_key_changes_go_on`, `c1_a_self_removal_beside_a_rotation_leaves_a_rotation_that_lands`, `c1_an_invite_from_either_branch_of_a_fork_can_be_used`, `forks_resolve_identically_whatever_the_arrival_order` (property); `engine/tests.rs`: `c1_after_a_fork_a_writers_record_is_admitted_everywhere`, `c1_a_self_removal_beside_a_rotation_does_not_stop_mail`, `forks_merge_and_every_replica_agrees` (property: 4 members, rotations, removals, role and device changes, invites and a join, every delivery order, then one merge, a rotation and a record admitted everywhere); vectors: `acl_fork` (a three-way fork merged by a two-parent entry) |
| H1 | high | Any member could fill the log to `MAX_ACL_ENTRIES`, freezing it (even its own removal could not be appended), and push resolve cost up (20k siblings: 7 s, 486 MB). | Fixed | `link/src/acl.rs`: the global cap is gone. (a) `AclState::capped`: removals and a due rotation are never capped; caps are per member, so nobody else's flood touches them. (b) `AclState::check_log_rules` and `absorb`: a per-member cap in each entry's own past, charged to the author's root (`MAX_MEMBER_ENTRIES_PER_DAY` 32, `MAX_ADMIN_ENTRIES_PER_DAY` 512, per `RATE_WINDOW_S`); siblings by one device are a device fork (`Dag::scan`: two entries with one `aseq`), whose every variant is dropped and, beyond `FORK_EVIDENCE` (2), pruned. (c) `AclLog::prune` and `DropKind`: entries the merged order drops for good (fork variants, superseded entries, and lost races for a single-use invite, the last seat or the last device slot, `kind_of`) are pruned with everything built on them; a pruned entry is remembered (`pruned`, `parked`) and taken back when re-offered after the log changed. (d) `Link::add_acl` no longer clones the log; `AclState` holds persistent maps (`imbl::OrdMap`, new dependency, MPL-2.0), so copying it at a fork is O(1); an entry's facts are stored (`Store::put_acl`, `AclLog::restore`), so reopening does not check pasts again; `Entry::verify_signature_with` checks one certificate once per batch | `acl/tests.rs`: `h1_a_sibling_flood_is_pruned_and_never_freezes_the_log`, `h1_removals_and_due_rotations_are_never_capped`, `a_forked_device_is_dropped_whichever_variants_a_replica_holds`; `engine/tests.rs`: `a_store_reopened_after_a_fork_resolves_the_same`. Measured with `probe flood` (below) |
| H2 | high | The hourly cap and the log cap were judged against what each replica held, so replicas kept different subsets for good, and an attacker could choose the split (`probe cap`). | Fixed | Every admission limit is now a function of the entry's causal past (`AclState::check_log_rules`, counting the member's entries in `Resolve(anc(e))`) or of the merged order (pruning), never of arrival order. `check_structure` keeps only the future-skew check against the receiver's clock, which can only delay an entry | `acl/tests.rs`: `h2_caps_are_decided_by_the_causal_past_alone` (one batch against one entry at a time, newest first, gives the same entries); `probe cap` now gives identical hash sets, heads and applied lists |
| M1 | medium | The leaf cert-expiry rule (local clock) was bypassed by a junk child (`probe leaf`). | Fixed | `AclLog::check_structure`: the local-clock rule is gone. An entry is valid only if its author's certificate is valid at its own `ts` (`AclState::apply_inner`) and its `ts` is not before any parent's. A stolen key that is never removed can still sign entries dated inside its certificate: removal contains it, and renewals move `not_after` only forward (module doc, "Time and volume") | `acl/tests.rs`: `m1_entries_are_judged_by_their_own_time_not_the_clock` (the same outcome at any receiver clock, with or without the child) |
| M2 | medium | The same leaf rule could stall honest sync at frame boundaries. | Fixed | Same as M1: nothing in admission depends on whether an entry has a child in the batch | Same as M1 |
| M3 | medium | Records from an expired, never-removed device key were accepted forever. | Fixed | `link/src/engine.rs`: `Link::authorised`: a record must be dated before its author's `not_after`, and not more than the skew before the newest head it names, so a key past expiry must name heads from inside its lifetime. `Link::past_retention` and `receive`: a record past the link's retention when it arrives, by our clock or by the ACL frontier (`AclState::frontier_ts`, the latest entry time, which every replica sees alike), is stored as a header only. So such a key can extend its feed with headers, but delivers no content once the retention has passed. Refusing the record instead would break the author's gapless feed for honest late copies, so it is stripped, not refused | `engine/tests.rs`: `m3_an_expired_never_removed_key_delivers_no_content` |
| M4 | medium | A member's other device could lower its own provisional cut, a removal carrying `rotate` on a self-cut device was refused, and records dated after a leave were accepted. | Fixed | `AclState::apply_inner` (`RemoveDevice`): lowering needs an admin with authority over the member, never the member itself; it may confirm the cut (`cut <= old`) and may carry the rotation the leave left due. `DeviceState.cut_ts`: set to the leave's `ts`; `Link::authorised` refuses the device's records dated after it. `Link::remove_device` on a self-cut device builds a lowering with the rotation | `acl/tests.rs`: `m4_only_an_admin_with_authority_lowers_a_self_chosen_cut`; `engine/tests.rs`: `m4_records_dated_after_a_leave_are_refused`; the round-1 `a_self_chosen_cut_is_provisional_and_an_admin_can_lower_it` and `upkeep_lowers_a_self_chosen_cut_to_the_head_it_holds` still pass |
| M5 | medium | A leave set `rotation_due` and blocked every writer until an admin was online. | Fixed | `AclState::apply_inner` (`RotateKey`): while a rotation is due, any reading member device that holds the key may append it (an admin may rotate at any time). This is sound because a rotation only re-keys to exactly the devices that may read, which is checked where its author stood. `link/src/engine.rs`: `may_rotate_now` (the designated device is the lowest admin holding the key, or, with none, the lowest reader holding it; every other key holder after `ROTATION_GRACE_S`), `rotates_now`, `upkeep` (readers run the rotation step) | `acl/tests.rs`: `m5_a_reader_with_the_key_appends_a_due_rotation`; `engine/tests.rs`: `m5_a_leave_never_stops_mail_for_longer_than_the_grace` |
| L1 | low | A whole copy refilled a stripped row even past retention. | Fixed | `Link::receive`: a record held only as a header is a duplicate. A row is only ever stripped past retention, so the refill path (`Link::refill`, `Store::fill_body`) could never apply and was removed | `engine/tests.rs`: `a_stripped_copy_is_judged_by_its_write_time_and_never_refilled_past_retention` |
| L2 | low | A blob id listed by two records with different sizes was fetched at the larger. | Fixed | `Link::blob_room`: a blob id already listed with another size is refused (an attachment at write, an alarm on receipt) | `engine/tests.rs`: `l2_a_blob_listed_with_another_size_is_refused` |
| L3 | low | Resolve must stay near-linear on a long log. | Fixed (measured) | A linear log is one pass (`Dag::after_states` copies state only where the cut-vertex tree branches) | `acl/tests.rs`: `a_long_linear_log_resolves_fast` (20,000 entries from scratch: 0.17 s release, 1.1 s debug) |
| L4 | low | ... and on a deep comb of forks and merges. | Fixed (measured) | Each merge resolves from its latest cut vertex, so it rescans only its own branches; persistent maps make each copy O(1). Before the maps, the same comb took 5.2 s | `acl/tests.rs`: `a_deep_comb_of_forks_and_merges_resolves_near_linearly` (9,002 entries from scratch: 0.13 s release) |
| L5 | low | ... and on a wide fan; exclusions must be recomputed, not accumulated. | Fixed (measured); partly open for one adversarial shape | `Dag::scan` recomputes its exclusions on every resolve. A wide fan by one device is a fork and is pruned. **Open:** a member that keeps one chain concurrent with every merge (never building on the merges) leaves no recent cut vertex, so checking a whole log from scratch costs the sum of the merges' pasts, which is quadratic. An incremental insert stays one pass, and reopening uses the stored facts, so only a joiner adopting such a log pays it. The member's cap (32 a day) bounds how long the chain grows | `acl/tests.rs`: `a_wide_fan_resolves_near_linearly` (2,000 siblings, resolve and prune: 0.13 s release), `a_lagging_chain_beside_every_merge_is_measured` (3,002 entries from scratch: 2.6 s release; one more merge inserted: 18 ms) |

### Probe results, before and after

The reviewer's probe (`probe fork`, `fork2`, `flood N`, `cap`, `leaf`), adapted to the new entry
API, on the release build.

| Probe | Before (round 1) | After (round 2) |
|---|---|---|
| `fork` (a writer removes its own device while the owner rotates) | Owner rotation refused ("not valid where its author stood"); writes refused for good ("a key rotation is due") | Merged epoch 1 with 2 heads, the heads' own past at epoch 1; the owner rotates, owner and writer write |
| `fork2` (a mailbox adds a device while the owner rotates) | The writer's record refused everywhere ("record epoch does not match its ACL head"); owner rotation refused | Record admitted on the other replica; the owner invites and rotates |
| `cap` (121 siblings split two ways across two replicas) | Different hash sets on the two replicas, for good | Same hash sets (5 entries: the fork evidence), heads and applied lists |
| `leaf` (an entry whose author expired, with a junk child) | Refused alone, kept with the child | Kept in both cases (dated inside the certificate); the child, dated after it, refused in both |
| `flood 20000` (siblings by one device) | `add_acl` 7.0 s, log 20,023 entries, next honest append 2.6 s, max RSS 500 MB | `add_acl` 3.0 s, log 25 entries (19,998 pruned), owner removes the flooder in 0.8 ms, next append 0.5 ms, max RSS 121 MB; the same flood offered again: 0.3 s (skipped by the pruned index) |
| `comb 20000` (a chain with a sibling at every step) | `add_acl` 1.1 s, log 37 entries | `add_acl` 0.46 s, log 25 entries (the member's daily cap refuses the rest) |

The remaining flood cost is one entry signature and one new-device certificate per sibling,
checked before the entry is known to be a fork variant.

### Changes to round-1 rows

- **4 / A8 (expired certificates):** the expired-leaf rule and `CERT_EXPIRY_GRACE_S` are gone;
  see M1 and M3. `a_long_expired_device_cannot_add_backdated_entries` is replaced by
  `m1_entries_are_judged_by_their_own_time_not_the_clock`.
- **A3 (log growth):** `MAX_ACL_ENTRIES` and `MAX_ENTRIES_PER_DEVICE_HOUR` are gone; see H1 and
  H2. `one_device_cannot_flood_the_log` is replaced by the H1 and H2 tests.
- **A7 / F2 (body stripping):** still fixed; the refill half is removed (L1).
- **Trade-off 4 (local admission):** resolved for ACL entries. Only the future-skew check and the
  join door's limits still use the receiver's clock and holdings.

### Known trade-offs of round 2

1. **Pruning converges through re-offers.** A replica prunes against what it holds. Which dead
   entries two replicas store can differ until they sync, because a peer that still holds one
   offers it again (sync sends what the other lacks) and it is checked again once the log has
   changed. What applies does not differ: the property test checks the applied state at once and
   the stored set after an exchange. An entry every replica pruned is gone everywhere, and all
   agree on the state without it.
2. **A forked device is done.** Two entries by one device with one `aseq` (a cloned or restored
   device key) drop every entry by that device from the fork on, and it appends nothing more.
   The member's other devices are unaffected; an admin or the member removes the forked device
   and certifies a new one.
3. **Caps are per member, and a rotation that is not due counts.** The review asked that no
   rotation be capped. A due rotation and every removal are never capped. A rotation that is not
   due draws on the rotating member's own allowance (512 a day for an admin), so a rogue admin
   cannot grow the log without bound before the owner removes it. Nobody else's entries touch
   that allowance.
4. **Quadratic from-scratch check for one adversarial shape** (L5 above).
5. **No global size cap.** The log's size is bounded by the per-member caps and pruning, times
   the members admins let in.
6. **More than 16 open heads.** An entry names 16 (its author's own first, then the latest) and
   is checked against the state those stand on; the next entries merge the rest.
7. **Records naming pruned heads.** A pruned head stands for its own past (its parents), so the
   record is still read. If the epoch then differs from the one sealed, the record is kept for
   the author's feed and never opened.
8. **Pruned entries leave the status.** `link.status` reports `acl_pruned` (a count) and
   `forked_devices`; a pruned entry is no longer listed among the dropped ones.
9. **New dependency:** `imbl` 7.0.2 (MPL-2.0, allowed by `deny.toml`) for persistent maps.

## Round 3

A third independent review found new high issues in machinery that round 2 had added (pruning,
the device-fork rule, the 16-parent cap, any-reader rotation, accumulating exclusions), and
reproduced each with a probe crate (`probe3`). The guiding rule for this round: remove or narrow a
mechanism rather than add one, and keep only rules that are (a) a function of the entry set,
(b) never able to penalise an honest device that has not forked and was not removed, and
(c) recoverable by an admin. Where a rule could not meet that, it was dropped and the cost is
written down below.

- **Base:** the round-2 head (commit `6b108f74`) plus this round. Like the tables above, this one
  names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 121 unit tests in
  `aurora-link` (three of them property tests, also run once at 600 cases each in release),
  4 vector tests, and 11 in `aurora-linkd` (1 ignored, a measurement). The Python link tests pass
  against the new wheel and debug daemon (172). `cargo fmt --check`, `cargo clippy --all-targets
  -- -D warnings`, `cargo deny check` and the fuzz smoke (`fuzz/smoke.sh 10`) are clean.
- **Formats changed.** A join no longer counts toward its device's `aseq` (it is always 0, and
  the next entry of a joined device has `aseq` 0). `KeyChange` has an optional `from` (a recovery
  re-key). The sync `hello` lists the stubs a side holds, a new `stubs` frame carries stubs, and a
  bundle carries them as `stubs`. The store is schema 4 (it keeps stubs); a store of schema 3 is
  refused and its link must be synced again. The vectors and the fuzz seeds were regenerated.

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R3-F1 | high | Pruning a superseded or lost entry of an honest device broke that device's `aseq` chain: on any replica where the pruned entry had a child, the device's next entry made two entries at one `aseq`, a fork. Any member could pin a pruned entry on purpose. A join that lost the last seat but had an accept built on it banned its device from ever joining again. | Fixed | `link/src/acl.rs`: `AclLog::prune` prunes only (i) entries of a forked device at or past its fork beyond the two kept as evidence, and (ii) joins that did not apply, and in both cases only when nothing held builds on them. `DropKind`, `kind_of` and the "superseded" and "lost" prune classes are gone. `AclState::absorb`, `check_log_rules` and `Dag::scan`: a join counts toward no device sequence and no fork (its `aseq` is always 0), so pruning a join never touches a sequence, and a device whose join lost joins again with `aseq` 0. Entries of removed devices are **not** pruned (see trade-off 1) | `acl/tests.rs`: `r3_f1_a_superseded_entry_of_an_honest_device_is_never_pruned` (the probe's shape, three replicas), `r3_f1_a_device_whose_join_lost_may_join_again`; `h1_a_sibling_flood_is_pruned_and_never_freezes_the_log` still passes; vectors: `acl_fork` (the superseded invite is now kept) |
| R3-F2 | high | Exclusions only grew: an entry dropped because of removal R stayed dropped after R itself was dropped (X's removal of its stolen device, dropped by an admin's removal of X, which the owner's demotion of the admin then dropped, left the stolen device active). | Fixed | `link/src/acl.rs`: `Dag::settle` decides which superseding entries take effect before any applies: one dropped by another in effect never takes effect, so a removal by a concurrently removed or demoted author drops nothing. They are decided in topological order of the graph "s drops t" (Tarjan's strongly connected components), and inside a cycle (devices of one member, or admins, removing each other's devices) the first in application order wins. `Dag::scan` then makes one pass; a candidate in effect that fails there (or a role change that did not take admin away) is taken out and everything is settled again. Termination: every extra round removes a candidate, so at most `candidates + 1` rounds, each with at most `joins + 1` passes for invite expiry. `Dag::pass` is the one pass. The concurrent victims of each superseding entry are cached across resolves (`AclLog::cuts`, `update_cuts`), and concurrency is decided by lifting through the cut-vertex tree (`Dag::in_past`) instead of a graph walk per entry | `acl/tests.rs`: `r3_f2_an_entry_dropped_by_a_dropped_removal_comes_back` (the probe's shape), `r3_f2_devices_removing_each_other_settle_the_same_everywhere`, `r3_removals_of_each_others_authors_settle_alike` (property: an owner demoting or removing two admins, the admins removing writers and each other's devices, writers removing their own devices and leaving, on three replicas with random exchanges; every arrival order and one-entry-at-a-time delivery give the same state, and no entry is dropped by an entry that did not apply; it fails on the round-2 code) |
| R3-F3 | high | A wrap to another device cannot be checked, so a reader allowed to rotate (round 2's any-key-holder rule) could wrap junk relabelled with the real key id to every other device, and nobody could rotate afterwards. | Fixed, with a documented limit | `link/src/acl.rs`: (1) **recovery re-key**: `KeyChange.from`, `AclState::recovery_key_change`, `plan_key_change`, `read_key` / `walk_back` (a recovery's `prev` seals the key of the last epoch the admin reads, with the gap declared and bound into the AAD; only an admin re-keys so; readers read again, history before the junk included). (2) **alarm**: `AclState::wrapped_by` and `bad_wrap`; `link/src/engine.rs`: `Link::upkeep` raises `bad_wrap` naming the author of the junk entry and the epoch, and an admin's daemon re-keys at once (`Link::rotate_key` falls back to `Link::recovery`). (3) **narrowed rotation**: `AclState::designated_rotator`, `may_rotate_due`, `may_rotate` and the `RotateKey` arm: a device that is no admin rotates only a due rotation, and only if it is the designated device (the lowest admin device holding the key, or with none the lowest reader holding it) or the rotation has been due `ROTATION_GRACE_S` by the entry's own time; a non-admin attaches a rotation to removing its own device only on the same terms. `Link::may_rotate_now` and `remove_device` follow the same rule, so M5 (mail waits at most the grace) holds. (4) the module doc says plainly that a malicious current reader can always leak or junk keys, and that recovery is an admin's re-key plus removing the author | `acl/tests.rs`: `r3_f3_a_reader_picks_no_key_for_its_own_removal_unless_designated` (the probe's shape), `r3_f3_an_admin_recovers_from_a_junk_rotation`, `m5_a_reader_with_the_key_appends_a_due_rotation` (now after the grace); `engine/tests.rs`: `r3_f3_upkeep_names_a_junk_wrap_and_recovers`, `m5_a_leave_never_stops_mail_for_longer_than_the_grace` |
| R3-F4 | medium | A record could name any 2 to 16 held entries, and each uncached set rebuilt state before the feed-gap and quota checks. | Fixed (narrowed) | `link/src/engine.rs`: `Link::receive` checks membership (`member_check`), the feed's order, the predecessor's time and the quota before the ACL heads (`acl_view`). The named heads must be an antichain (`AclLog::is_antichain`), as every honest writer's are. A head set not answered at once (current heads, one entry, or the cache) costs one of `MAX_RESOLVES_PER_HOUR` (64) resolutions of its author's; past it the record waits (`Admit::Gap`). `link/src/acl.rs`: `EpochCache` (an LRU of 4,096 head sets, replacing a 256-entry map cleared when full), filled by every new merge entry with its parents' epoch (`Walk.epoch_before`). The review's "not older than the author's previous record's heads" rule was built and then **dropped**: an honest writer's head set can step back (after its replica prunes a head, or past `MAX_PARENTS` heads), and a refused record stops its feed for good. The budget bounds the cost instead and only ever delays | `engine/tests.rs`: `r3_f4_named_heads_must_be_an_antichain` (an older set than the predecessor's is taken), `r3_f4_resolutions_per_author_are_budgeted`, `r3_f4_records_naming_arbitrary_heads_cost_little`; `m3_an_expired_never_removed_key_delivers_no_content` (reordered: equivocation is now found before the heads) |
| R3-F5 | high | With more than 16 open heads, `parents_for` could leave out the author's own last entry, so its next entry reused an `aseq` and forked itself. | Fixed | `link/src/acl.rs`: `AclLog::parents_for` (with an author) names the latest heads and, when none of them has the author's own latest entry in its past (`AclLog::reaches`), that entry itself in place of the last head; the set stays an antichain. `AclLog::append` refuses to sign when the parents' count of the device's own entries differs from the merged state's | `acl/tests.rs`: `r3_f5_more_than_max_parents_heads_never_make_an_author_fork_itself` (the probe's shape: 17 heads), `r3_f5_the_parents_an_author_names_hold_all_its_own_entries` |
| R3-F6 | high (liveness) | Records naming a pruned head were refused by joiners and after restarts: the pruned index lived in memory, was capped, and was never sent to anyone. | Fixed | `link/src/acl.rs`: `Stub` (hash, parents, author, `seq`, `aseq`, `ts`) for every pruned entry, kept uncapped (`AclLog::pruned`), `add_stubs` from peers (shape-checked, never over a held entry, at most `MAX_PEER_STUBS`), `restore_stubs`, `stubs_missing_for`, `take_changes` (`AclChanges`); `resolve_named`, `reaches` and `is_antichain` read through stubs. `link/src/store.rs`: table `acl_stubs`, `put_stub`, `delete_stub`, `acl_stubs` (schema 4). `link/src/engine.rs`: `Link::open` restores stubs, `persist_acl` stores them, `add_stubs`; a record naming a head never seen is kept aside (`Admit::Pending`, one per author, in memory) and checked again when the ACL grows (`Link::retry_pending`). `link/src/sync.rs`: `hello.stubs`, `Frame::Stubs`, `stub_frames`; sessions retry waiting records after ACL and stub frames. `linkd/src/daemon.rs`: bundles carry stubs | `engine/tests.rs`: `r3_f6_a_joiner_reads_a_record_naming_a_head_pruned_before_it_joined` (the probe's shape, over a real sync session), `r3_f6_a_reopened_store_keeps_the_stubs_of_pruned_entries`, `r3_f6_a_record_on_an_unseen_head_waits_for_it`, `a_record_naming_a_pruned_head_is_still_read` (now on a pruned join) |
| R3-L1 | low-medium | `needs_admin` treated removing one's own other device as admin-only, so a demotion dropped a demoted admin's concurrent removal of its own stolen device. | Fixed | `link/src/acl.rs`: `needs_admin` asks whether the removed device belongs to the author's own member (`Dag.root_of`, from the entries that introduced each device) | `acl/tests.rs`: `r3_l1_a_demotion_keeps_a_concurrent_removal_of_ones_own_device` |
| R3-L2 | low-medium (suspected) | A from-scratch resolve with many merges and superseding replays could exceed the documented quadratic case. | Measured; bounded | Round 2 replayed and walked the graph per superseding entry. Now `settle` decides up front, rounds are bounded (R3-F2), concurrency is O(log n) by lifting (`Dag::in_past`, regions cached per merge), and each entry's concurrent victims are found once and cached (`update_cuts`) | `acl/tests.rs`: `r3_l2_a_joiner_adopts_many_merges_and_supersessions` (a merge and a superseded entry every round; 3,004 entries with 1,000 supersessions, from scratch: 0.45 to 0.52 s release). See the measurements below |

### Probe results, before and after

`probe3` is the reviewer's crate, unchanged, release build, run against the round-2 head and
against this round.

| Probe | Before (round 2) | After (round 3) |
|---|---|---|
| `f1_demotion_kills_honest_device` | rB pruned the superseded invite; B's next entry reused `aseq` 1; B forked on every replica, its entry dropped, and it could not even leave | The invite is kept everywhere; B's entry has `aseq` 1 after the invite's 0, applies on every replica, no fork, B leaves |
| `f1b_lost_join_bans_device` | Rejoin refused ("author sequence 0 does not follow the author's 1 earlier entries") | Rejoin applies; no fork |
| `f2_stale_exclusion` | X's removal of its stolen device dropped and gone; the stolen device active; the admin's removal dropped too | X's removal applies; the stolen device stays removed; the demoted admin's removal is dropped as superseded by the demotion; X stays |
| `f3_reader_bricks_key` | Junk rotation accepted; the owner could not read the key or build any rotation | Junk rotation refused (the reader is not designated); the owner reads and can rotate. After the grace a reader may rotate junk, and then the owner's recovery re-key restores it (tests above) |
| `f5_head_flood_forks_the_owner` | 17 heads; the owner's append refused as a fork of its own device; its entry E dropped | 17 heads; the owner's append applies; no fork; E applied; the owner's other device appends |
| `f6_joiner_cannot_read_pruned_heads` | Old replica: substituted; joiner: unknown (refused) | The probe's invite is no longer pruned (R3-F1), so both read it as held. The pruned-join version of this shape is the test above: the joiner keeps the record waiting, the first sync brings the stub, and the record is admitted |
| `f4_epoch_for_cost` (300 uncached `epoch_for` calls, 3,000 entries) | 3.1 s | 3.7 s: `epoch_for` itself is unchanged (it rebuilds the DAG); what changed is that records no longer reach it unchecked (below) |

The round-2 flood probe (`probe flood 20000` and `comb 20000`, release), rerun on both trees on
the same machine:

| Probe | Round 2 | Round 3 |
|---|---|---|
| `flood 20000` (siblings by one device) | `add_acl` 3.13 s, log 25 entries (19,998 pruned), offered again 0.31 s, the owner removes the flooder in 0.87 ms, next append 0.52 ms, max RSS 180 MB | `add_acl` 3.24 s, log 25 entries (19,998 pruned, each now a stored stub), offered again 0.31 s, removal 0.89 ms, next append 0.47 ms, max RSS 190 MB |
| `comb 20000` | `add_acl` 0.37 s, log 25 entries | `add_acl` 0.36 s, log 25 entries |

So the H1 bound holds without pruning honest entries: a device that floods siblings is forked by
definition and its siblings are pruned; a linear chain is capped in its own causal past.

### Measurements

A small crate (`measure`, in the review scratchpad) built against both trees, release:

| Shape | Round 2 | Round 3 |
|---|---|---|
| 300 records by one writer naming (ancestor, descendant) pairs of a 3,000-entry log, each refused | 3.01 s (each resolves part of the log before its epoch is found wrong) | 0.26 s (refused as not an antichain, before any resolution) |
| 1,000 rounds of a merge beside a demotion with a concurrent victim, built by appends | 110 s for 2,004 entries (superseded invites pruned) | 56 s for 3,004 entries (superseded invites kept) |
| The same log checked from scratch by a joiner | 0.15 s (2,004 entries) | 0.45 s (3,004 entries, the cut cache built from nothing) |
| 3,000 linear appends; one more at 3,005 entries | 26.9 s; 21 ms | 30.0 s; 22 ms |

The last row is unchanged by this round and worth knowing: every insert re-resolves the whole log,
so one append costs O(n), about 20 ms at 3,000 entries (trade-off 8).

### Mechanisms removed or narrowed

- **Pruning**, narrowed to forked devices' entries beyond the evidence and joins that did not
  apply. Removed: the "superseded" and "lost" prune classes, `DropKind`, `kind_of`, and the
  in-memory pruned index with its 65,536 cap (replaced by stored stubs, which F6 needs).
- **The device-fork rule**, narrowed: a join is no longer part of a device's sequence.
- **Accumulating exclusions** and the retroactive replay loop, removed: superseding entries are
  settled before they apply, in bounded rounds.
- **Any-key-holder rotation** (round-2 M5), narrowed to the designated device, or any key holder
  after the grace, judged by the ACL at the entry's own time; the same for a non-admin's rotation
  on removing its own device.
- **`needs_admin`**, narrowed for removing a device of one's own member.
- **The epoch cache**, a 256-entry map cleared when full, replaced by an LRU of 4,096 sets.
- **The forward-only head rule** the review asked for, built and then removed (not honest-safe),
  replaced by the per-author resolution budget.
- **Graph walks for concurrency** (`Dag::reach`, `tree_ancestor`), removed in favour of
  `Dag::in_past`.

Added, because a finding needed it: stubs (stored, synced, bundled), waiting records, the
resolution budget, the recovery re-key, the junk-wrap alarm with `wrapped_by`, the settling step
and its cut cache, and the own-entry rule in `parents_for` with its guard in `append`.

### Changes to round-2 rows

- **H1 (c):** pruning is narrowed as R3-F1 says; the flood bound is unchanged (measured above).
- **M5:** a non-admin rotates only as designated, or after the grace; mail still waits at most
  the grace.
- **Trade-off 1 (convergence through re-offers):** still true, for the narrower set of pruned
  entries.
- **Trade-off 6 (more than 16 heads):** an entry names the latest 15 heads and its author's own
  latest entry when no chosen head has it in its past.
- **Trade-off 7 (records naming pruned heads):** stubs are stored and synced, so every replica
  reads such a record alike; a head never seen keeps the record waiting.
- **Trade-off 8 (status):** `acl_pruned` now counts the stubs held.

### Known trade-offs of round 3

1. **A removed member's stale branch is kept.** Entries of a removed (not forked) device on a
   branch that never sees its removal are dropped but not pruned, because a removal can still be
   undone by a concurrent removal or demotion of its author, and a pruned entry of a device that
   becomes active again would fork it. They grow the log by at most the member's cap (32 a day, or
   512 for an admin) per day of entry time (an entry is never dated more than the skew ahead of
   the receiver's clock), for each of its devices that keeps a branch of its own. On that branch
   it can even renew its own certificates, so this lasts as long as its root signs renewals. A
   joiner checking such a log pays round 2's L5 cost for that shape.
2. **A pruned join that would later apply** (the join that beat it was itself dropped) comes back
   only if some replica still holds it and offers it again. If every replica pruned it, all agree
   on the state without it, and the fleet joins again with a fresh invite.
3. **Stubs are unsigned claims.** A peer's stub is used only to read a record through to held
   entries, never as an entry, never over a held entry, and at most `MAX_PEER_STUBS` are taken. A
   fake stub can at worst make a record read as standing on a pruned head (kept but never opened
   when its epoch differs). The stubs of a large sibling flood are stored too (one per pruned
   sibling, about 300 bytes each).
4. **Waiting records live in memory**, one per author. After a restart the record comes again
   with the next sync, and a record whose head never arrives waits (its author's later records
   ask again as a gap), which only that author's own bad record can cause.
5. **A malicious current reader can always leak the key or wrap junk** when it may rotate (as the
   designated device, or after the grace), and an admin can wrap junk in an accept or a new
   device. Every device names the junk's author in an alarm; recovery is an admin's re-key and
   removing that author.
6. **The resolution budget is local**, like the record quota: it delays a record (a gap), never
   refuses one, so it cannot split replicas for good.
7. **No forward-only rule for record heads** (R3-F4 above): a writer may name an older antichain
   than its last, within its budget.
8. **An append costs O(n)** in the log's size (about 20 ms at 3,000 entries), as in round 2:
   every insert re-resolves the merged state from scratch. Making it incremental is a separate
   piece of work.
9. **A cycle of superseding entries** is broken by application order, whose last tie-break is the
   hash (A13 applies).
10. **No protocol version bump.** As in round 2, peers and stores on the earlier formats are
    refused rather than translated; every replica must run this round's code.

## Round 4

A fourth independent review again found new critical and high issues, and reproduced each with
a probe crate (`probe4 p1..p6`). Two causes kept coming back. (1) The application order sorts by
`seq`, which an author chooses by picking old parents, so any security-relevant race decided by
"first in the application order" goes to whoever backdates. (2) Each round added machinery that
was trusted without being checked: unsigned stubs, and device certificates without proof that
the device key's holder agreed. The rule for this round: **no security-relevant outcome may depend
on the application order between concurrent entries; a conflict between concurrent entries fails
closed (both lose) and is recoverable by an admin or by trying again; nothing unsigned is
trusted.** Where a rule fails closed, its bound and its recovery are written down below.
Mechanisms were deleted where possible.

- **Base:** the round-3 head (commit `5835687b`) plus this round. Like the tables above, this
  one names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 143 unit tests in
  `aurora-link` (three of them property tests, also run once at 600 cases each in release),
  4 vector tests, and 11 in `aurora-linkd` (1 ignored, a measurement). The 7 Python link test
  files pass against the new wheel and debug daemon (172 tests). `cargo fmt --check`,
  `cargo clippy --all-targets -- -D warnings`, `cargo deny check` and the fuzz smoke
  (`fuzz/smoke.sh 10`) are clean.
- **Formats changed.** A device certificate carries `pop`, the device key's own signature over
  the certificate body (purpose `cert-pop`). A join lists exactly the device that signs it, and
  its `invite` is the hash of the entry that issued the invite, not the invite key; the join
  proof and the `join_hello` proof bind that hash. `revoke_invite` names the issuing entry too,
  and an invite code carries it (`invite`). The sync `hello` is `{v, link, device, acl,
  acl_count, heads, more}`: `acl` is at most 64 open heads, `heads` at most 128 authors, and
  `more` announces `heads` frames with the rest. A new `acl_want {want, have}` frame asks for ACL
  entries by hash. The `stubs` frame, `hello.stubs` and a bundle's `stubs` are gone. A fleet
  label cannot contain `~`. The store is schema 5 (no `acl_stubs` table); a store of schema 4
  is refused and its link must be synced again. The vectors and the fuzz seeds were regenerated.

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R4-1 | critical | The first `hello` of a session listed every ACL entry hash and every stub hash (about 67 bytes each), but the accepting daemon reads a first frame with a 64 KiB cap: an honest link stopped syncing at about 950 entries, and a stub flood triggered it at once, fleet-wide. Record heads were listed per author without a bound too. | Fixed | `link/src/sync.rs`: `hello` returns the opening frames: a `hello` naming at most `MAX_HELLO_ACL_HEADS` (64) open ACL heads (`AclLog::latest_heads`), the entry count, and at most `MAX_HELLO_AUTHORS` (128) authors' record heads, then `Frame::Heads` pages with the rest (`more`). The answer sends the entries outside the causal past of the peer's known heads (`AclLog::missing_for_heads`): a superset when a hello left heads out, never short of what the peer lacks. Records are sent only for the authors a partial hello listed until its last page (`Link::missing_for_authors`). Entries a side still lacks (a child whose parent is missing, a record's head) are asked for by hash with `Frame::AclWant` and answered with their past outside the asker's heads (`AclLog::missing_for_want`). `sync::MAX_FIRST_FRAME` is the cap the daemon reads with (`linkd/src/net.rs`); no frame needs to be larger. A held hello (its sender not yet known as a member) keeps its pages | `engine/tests.rs`: `r4_1_a_hello_stays_small_and_a_5000_entry_log_syncs` (5,000 entries: the hello is under 4 KiB; a member that saw only the first entries and a joiner from scratch both sync), `r4_1_record_heads_page_after_the_hello` (300 authors: a hello of 128, then a page, under the cap; the session settles) |
| R4-2 | critical (with p2) | Stubs were unsigned claims: any member that may sync could send a forged stub for an honest head a victim had not yet seen, and the victim withheld the honest record for good (p2); stubs also fed R4-1 and R4-10. | Fixed (stubs removed) | `link/src/acl.rs`: `Stub`, `add_stubs`, `restore_stubs`, `stubs_missing_for`, `resolve_named` and `NamedHeads` are gone; nothing pruned leaves anything behind. Pruning is storage only: `AclLog::prune` removes only entries a **fork** dropped (`AclState::fork_dropped`) beyond the evidence it keeps (two variants at a device's fork sequence, the two joins of a device that joined twice through one invite, a concurrent pair of joins through a forked invite), when nothing held builds on them and no waiting record names them (`AclLog::set_pins`). Forked entries claim nothing and never apply, so pruning changes nothing that applies. An entry a replica lacks is fetched by hash: a child with a missing parent (`AclLog::take_orphans`), a record's head (`Link::wanted_acl`, asked of the peer that sent the record and of every peer at the next hello). `link/src/engine.rs`: a record naming a head not held waits (`Admit::Pending`), never refused or withheld for missing data; a head refused for good refuses the record (`AclLog::refused_for_good`). A record withheld as sealed under a rotation that lost a fork (`LOST_FORK`) is checked again whenever the log's keys change (`Link::recheck_withheld`, `Store::reopen`), and opens if its key is the one in force after all. `link/src/store.rs`: schema 5, no `acl_stubs`. `linkd/src/daemon.rs`: bundles carry no stubs | `engine/tests.rs`: `r4_2_a_record_on_a_pruned_head_waits_and_is_fetched` (a forked device's five variants; a replica keeps two; a record on a pruned one waits, the session asks for it, it is kept while the record waits, and the record is admitted), `r4_2_an_entry_with_a_missing_parent_is_fetched`, `r4_2_a_withheld_record_opens_when_its_rotation_wins_after_all`, `r3_f6_a_joiner_reads_a_record_naming_a_head_that_lost_before_it_joined` and `r3_f6_a_reopened_store_keeps_entries_that_lost` (rewritten: a lost join is kept, not stubbed); `acl/tests.rs`: `r4_6_a_join_flood_through_one_invite_forks_it_and_is_pruned` |
| R4-3 | high | Joins counted toward no sequence and never forked, so a device could sign any number of joins (through one invite, or several), and failed joins were pruned, which round 3 relied on to let a lost join's device join again. | Fixed | `link/src/acl.rs`: `Dag::forks_and_claims`: two joins by one device through one invite fork the device (`AclState::join_forks`, `forks` at 0): every entry by it is dropped, joins included, and `check_log_rules` refuses any later entry of it. A join whose device already joined through the same invite in its causal past is never valid (`AclState::joined_via`); a device whose join lost joins again only through another invite. Failed joins are no longer pruned (only fork-dropped ones are, beyond the evidence), see R4-2 and trade-off 3 | `acl/tests.rs`: `r4_3_two_joins_through_one_invite_fork_the_device`, `r3_f1_a_device_whose_join_lost_may_join_again` (rewritten: the join loses to a concurrent revocation; through the same invite again it is refused, through a new one it joins, unforked) |
| R4-4 | high | `DeviceCert::verify` checked only the root's signature, so a member could certify another fleet's device id under its own root and squat it (p6: a mailbox's backdated add took a newly added device of another member, with the attacker's KEM key, blocking the honest add). | Fixed | `link/src/identity.rs`: `DeviceCert.pop`, the device key's signature over the certificate body (purpose `cert-pop`, apart from the root's `cert`); `DeviceCert::issue` takes the device's signing key; `verify` checks both, wherever a certificate is accepted (entry authors, genesis devices, joins, adds, device files). `Device::create` and `renew` sign it. `link/src/acl.rs`: `apply_join`: a join lists exactly the device that signs it, so every device it lists signed it | `identity.rs`: `certificates_verify_expire_and_renew` (a squat certificate and a copied root signature fail); `acl/tests.rs`: `r4_4_a_device_id_cannot_be_squatted_without_its_key` (p6's shape), `r4_4_a_join_lists_only_its_signing_device` |
| R4-5 | high | In a settle cycle the first in the application order won, so a thief holding a member's second device beat the honest device's removal of it by signing "b1 removes b0" on old parents (p3). | Fixed | `link/src/acl.rs`: `Dag::settle`: a strongly connected component is decided as a whole: every member not dropped from outside the cycle takes effect, and those a cycle peer drops apply anyway (`Mode::forced`: the author check accepts a device a peer cut, and the owner's last-device guard does not stop a cycle). Both devices are cut; an admin adds a fresh device for the member. No cycle outcome depends on `seq` or hash. Two concurrent removals of one device or member both stand: the lower cut wins and an admin's makes it final (`apply_inner`, lenient `RemoveDevice` and `RemoveMember`) | `acl/tests.rs`: `r4_5_a_backdated_counter_removal_cannot_win_a_cycle` (p3's shape, both arrival orders, then recovery), `r4_5_mutual_admin_removals_both_take_effect`, `r4_5_owner_devices_removing_each_other_are_both_cut`, `r3_f2_devices_removing_each_other_settle_the_same_everywhere` (now both cut), `r3_removals_of_each_others_authors_settle_alike` (property, now with concurrent role changes) |
| R4-6 | high | Uniqueness conflicts between concurrent entries were decided by order: a device id already listed, a join's "already known", a duplicate invite key, the last seat, a fleet label; a duplicate invite key published by another admin could take a join over. | Fixed, two by design not failing closed | `link/src/acl.rs`: (1) **invites by entry**: `AclState::invites` is keyed by the hash of the issuing entry (`InviteState.key` holds the key), joins and revocations name it, the join proof binds it (`join_proof_bytes`, `InviteTicket`, `sync::join_hello`), so a duplicate key names another invite; the "invite key already used" check is gone. (2) **claims fail closed**: `Dag::forks_and_claims`, `Dag::claims`: two concurrent entries claiming one device id (a join, or an add that renews nothing, `Dag::renews`) or one fleet root both fail; with R4-4 only that key's or root's holder can make such a pair. (3) **invite forks**: two concurrent joins through one single-use invite drop every join through it concurrent with another and use the invite up (`AclState::invite_forks`); a join made after the invite expired (`Dag::late_joins`) forks nothing. (4) **role changes**: of two concurrent role changes of one member the lower stands, settled like a removal (`Victims::Roles`), so an admin cannot win by inflating its `seq`. (5) a decline beats a concurrent accept (`Victims::Accepts`). (6) **by design not both-fail**: the last seat, a member's last device slot, and a fleet label are checked where the entry stood and taken as they are in the merged order; both concurrent joins stand. Failing both would let any live-invite holder evict an honest member after the fact by backdating a join. Clashing labels are shown with a root suffix while both are live (`AclState::display_label`, used by `status`, events and the daemon's member lookup); `~` is not allowed in labels | `acl/tests.rs`: `r4_6_a_duplicate_invite_key_cannot_take_a_join_over`, `r4_6_concurrent_claims_of_one_device_both_fail`, `r4_6_a_join_flood_through_one_invite_forks_it_and_is_pruned`, `r4_6_an_invite_cannot_be_forked_after_it_expired`, `r4_6_concurrent_role_changes_the_lower_role_stands` (both halves: the lower stands; if its author is removed concurrently, the higher stands), `r4_6_a_decline_beats_a_concurrent_accept`, `r4_6_concurrent_joins_for_the_last_seat_and_one_label_both_stand` |
| R4-7 | medium | `rotation_due_since` was the `ts` of the entry that made the rotation due, so a backdated due-making entry let a reader that was not the designated device rotate at once (p4). | Fixed | `link/src/acl.rs`: `Dag::pass` starts the grace no earlier than the newest `ts` of any entry concurrent with the due-making entry (`Dag::concurrent_ts`): a backdated entry is not known to be visible before then. Where an entry stood and in the merged order alike | `acl/tests.rs`: `r4_7_a_backdated_due_does_not_skip_the_grace` (p4's shape: refused inside the grace, taken after it) |
| R4-8 | medium | A never-valid entry cost a full re-resolve of the log each time it was sent again, under the link lock (p5: about 21 ms each at 3,000 entries). | Fixed | `link/src/acl.rs`: `AclLog::refused` (bounded LRU of 65,536 hashes, `Recent`): an entry never valid where its author stood, or malformed for good, is refused again at the cost of its hash (`check_structure`, `Lasting`); `insert_at` checks a small batch (`PRECHECK_BATCH`, 8) on our own heads where it stood before any resolve (a copy of the merged state). `link/src/sync.rs`: a session takes at most `MAX_ACL_FRAMES_PER_MIN` (120) `acl` and `acl_want` frames a minute (`Session::acl_frame`) | `engine/tests.rs`: `r4_8_a_refused_entry_sent_again_is_cheap`, `r4_8_acl_frames_per_session_are_rate_limited` |
| R4-9 | low | The renewal window (`CERT_RENEW_WITHIN_S`) was not enforced where an entry's embedded certificate replaced the stored one. | Fixed | `link/src/acl.rs`: `apply_inner` refuses an entry carrying a renewed certificate before the stored one's renewal window, with the author checks (before anything changes) | `acl/tests.rs`: `r4_9_an_embedded_renewal_outside_its_window_is_refused` |
| R4-10 | low | Stub walks ran before the author's budget was charged (p7). | Fixed (moot) | Stubs are gone (R4-2). Asking peers for a record's heads is charged to the record's author once per waiting record (`Link::receive`, `Link::charge`, the same `MAX_RESOLVES_PER_HOUR` budget as uncached head sets); past it the record waits like one over quota. Answering an `acl_want` costs a walk, bounded by the session's ACL frame limit (R4-8) | `engine/tests.rs`: `r4_2_a_record_on_a_pruned_head_waits_and_is_fetched`, `r3_f4_resolutions_per_author_are_budgeted` |

### Probe results, before and after

`probe4` is the reviewer's crate, release build, run against the round-3 head. `probe4-after` is
the same crate adapted to the new interfaces (no stubs to forge; a certificate needs its device
key; invites are tickets), run against this round.

| Probe | Before (round 3) | After (round 4) |
|---|---|---|
| `p1` hello size | 500 entries: 33,703 bytes; 950: 63,853 (at the 64 KiB cap); 1,500: 100,703 (refused). 1,000 forged stubs taken from one frame; a 2-entry link's hello then 67,269 bytes, relaying all 1,000 | 500, 950, 1,500 and 5,000 entries: 288 to 289 bytes. There are no stubs to forge |
| `p2` forged stub | With the forged stub, the honest record was stored `withheld` for good ("sealed under an ACL branch that lost a fork"), though the victim later held the head | No stub frame exists; a tampered copy of the head is refused. The record waits (`Pending`), is read once the head arrives, and is admitted, attack or not |
| `p3` cycle by backdating | The thief's removal (seq 6) applied, the honest one (seq 26) did not: b0 cut, b1 (the thief) active | Both removals apply: b0 and b1 cut |
| `p4` grace bypass | `rotation_due_since` = the backdated entry's `ts` (10,009 s before); the non-designated reader's immediate rotation applied | `rotation_due_since` = the newest concurrent entry's `ts`; the immediate rotation is refused (1,000 s into the 3,600 s grace) |
| `p5` replaying a refused entry | 20.9 ms per replay at 3,005 entries | 22.8 µs per replay |
| `p6` device squat | The backdated squat applied; the honest add did not; b1 belonged to the mailbox with the attacker's X25519 key | The squat certificate does not verify (no proof of possession); the entry is never valid; the honest add stands |

The round-2 flood probe (`probe flood 20000` and `comb 20000`, release), rerun on both trees on
the same machine:

| Probe | Round 3 | Round 4 |
|---|---|---|
| `flood 20000` (siblings by one device) | `add_acl` 3.21 s, log 25 entries (19,998 pruned), offered again 0.31 s, the owner removes the flooder in 0.90 ms, next append 0.49 ms, max RSS 190 MB | `add_acl` 4.19 s, log 25 entries (19,998 pruned, nothing left behind), offered again 0.35 s, removal 1.04 ms, next append 0.63 ms, max RSS 207 MB |
| `comb 20000` | `add_acl` 0.36 s, log 25 entries | `add_acl` 0.41 s, log 25 entries |

The H1 bound holds. The flood's extra second is the proof-of-possession check: each of the
20,000 added certificates now costs two signature checks instead of one.

### Measurements

The `measure` crate from round 3, built against both trees, release, the same machine:

| Shape | Round 3 | Round 4 |
|---|---|---|
| 3,000 linear appends; then 20 more at about 3,020 entries, each | 30.0 s; 21.1 ms | 29.5 to 30.0 s; 20.4 to 21.5 ms |
| 300 records naming (ancestor, descendant) pairs of a 3,000-entry log, each refused | 0.27 s | 0.25 s |
| 1,000 rounds of a merge beside a demotion with a concurrent victim, built by appends | 60.0 s for 3,004 entries | 58.1 s for 3,004 entries |
| The same log checked from scratch by a joiner | 0.46 s | 0.66 s |
| `r4_1` test: a 5,000-entry log built and synced to a member and a joiner (release) | n/a | 2.3 s |

The per-insert full re-resolve (about 21 ms at 3,000 entries) is unchanged: this round adds no
per-insert cost to an honest append. The settling step does more work up front (forks, late
joins and claims, each structural), which the measurements above include. Checking from scratch
got slower in the supersession shape (0.46 to 0.66 s): it changes one member's role 2,000 times,
and each role change is now a superseding entry whose victims are that member's other role
changes, so k role changes of one member cost O(k^2) concurrency checks once, when a log is
checked from scratch (each new entry adds only its own, through the cut cache).

### Mechanisms removed or narrowed

- **Stubs**, removed entirely: `Stub`, the `stubs` frame, `hello.stubs`, a bundle's `stubs`, the
  `acl_stubs` table, `add_stubs`, `restore_stubs`, `stubs_missing_for`, `MAX_PEER_STUBS`,
  `resolve_named` and its substituted heads, and the `stale_epoch` path that withheld records on
  a stub.
- **The full ACL listing in `hello`**, removed: a hello names at most 64 heads.
- **"First in the application order wins"** in settle cycles, removed (every cycle member takes
  effect), and the cycle losers' list with it.
- **The owner's last-device guard** inside a settled cycle, removed (an admin adds a new owner
  device).
- **The invite-key uniqueness check**, removed: invites are known by their issuing entry.
- **Multi-device joins**, removed: a join lists exactly its signer.
- **Pruning of failed joins**, removed: only fork-dropped entries are ever pruned.
- **Merged-order refusals for the last seat, the last device slot and a taken label**, removed
  (both concurrent entries stand; labels are disambiguated for display).
- **The expired-join pass loop** (re-run after each pass against applied entries), replaced by
  one structural check (`Dag::late_joins`).
- **Pruning's in-memory index of stub versions**, replaced by a bounded LRU of recently pruned
  hashes that is never synced, stored or read through.

Added, because a finding needed it: proofs of possession, invite tickets, `acl_want` with
orphans, pins and wanted heads, `heads` paging, the refused-entry cache, the small-batch check on
our own heads, the per-session ACL frame limit, join forks, invite forks, claims, forced cycle
members, display labels, decline and role supersession, the grace start, and the withheld
re-check.

### Changes to round-3 rows

- **R3-F1:** a lost join is no longer pruned; a device whose join lost joins again only through
  another invite.
- **R3-F2:** a cycle no longer has a winner by order; every member takes effect (R4-5).
- **R3-F4:** the budget also pays for fetching a waiting record's heads (R4-10).
- **R3-F6:** stubs are removed (R4-2); a record on a head a replica lacks waits and the head is
  fetched; nothing that lost is pruned except by a fork.
- **Trade-off 2 (a pruned join that would later apply):** gone: joins are pruned only when a
  fork dropped them, and those never apply.
- **Trade-off 3 (stubs are unsigned claims):** gone with the stubs.
- **Trade-off 9 (a cycle broken by order):** gone (R4-5).

### Known trade-offs of round 4

1. **A cycle cuts the honest device too.** A thief holding one of a member's devices can take the
   honest device down with it once (both are cut); it cannot touch the fresh device an admin
   adds, since every entry of its own that could name it stands on its cut. If the owner's only
   two devices remove each other, the owner has no device until an admin adds one: keep a spare
   owner device, or an admin.
2. **An invite's secret holders can make its joins fail while it is live.** Two concurrent joins
   through one single-use invite both fail. The invitee can only hurt itself; the inviter can
   evict, until the invite expires (at most 30 days, 24 hours by default), a member who joined
   through it, even one the owner has since promoted beyond the inviter's reach. After the
   expiry a backdated join is late and forks nothing.
3. **Failed joins are kept.** The review asked to cap them per invite as storage only, but a join
   that failed for another reason than a fork can still decide what applies: it claims a device
   and a root (its concurrent claimants fail with it), and a join dropped by a superseding entry
   comes back if that entry is itself dropped. Pruning it would make replicas disagree, so only
   fork-dropped joins are pruned. Their volume is bounded by the invites: each needs an admin's
   invite, and concurrent joins through one single-use invite are a fork (pruned to two).
4. **Concurrent claims of one device id or root both fail.** Only the holder of that device key
   (with its proof of possession) or of that root can make the pair, so this hurts nobody else;
   the device is added once more.
5. **The member cap, device slots and labels are soft between concurrent entries.** Concurrent
   joins can take a link over `max_members` by at most the number of invites live at once (new
   joins are refused until it is back under), and a member can go over 8 devices by its own
   concurrent adds. A live-invite holder can force an honest member's displayed label to carry a
   root suffix by joining with the same label, for as long as both are members; it never gets
   the bare label. Failing both instead would have let any invite holder evict an honest member
   after the fact.
6. **A lower concurrent role change wins.** An admin can veto a concurrent role upgrade of a
   non-admin member by backdating a lower one; recovery is the owner demoting or removing that
   admin, after which the upgrade stands.
7. **A pruned entry is offered again.** A replica holding a forked device's extra variants sends
   them in every session's ACL diff (the peer's heads never cover them); the peer skips them while
   its log has not changed (`MAX_RECENTLY_PRUNED`), and keeps one only while a waiting record
   names it.
8. **A hello truncated at 64 heads** gets a superset of what the peer lacks (duplicates are
   ignored), never less.
9. **The refused-entry cache is bounded.** An attacker cycling more than 65,536 distinct
   never-valid entries pays a resolve per frame on entries it sends on old parents or in large
   batches, and a session takes 120 ACL frames a minute.
10. **Withheld records are checked again 256 at a time** per change of the log's keys.
11. **The grace can be pushed back** by entries made concurrent with the entry that made a
    rotation due (old parents, a current `ts`). This only delays the fallback; the designated
    device rotates at once.
12. **An append costs O(n)** (about 21 ms at 3,000 entries), as before.
13. **No protocol version bump.** Peers, stores and invite codes from round 3 are refused.
14. **`brief.md` still describes round 3's stubs**; this file and the module docs describe the
    current design.

## Round 5

A fifth independent review found new critical, high and medium issues and reproduced each with a
probe crate (`probe5 p1 p1b p2 p3 p4 p5 p6`). Its conclusion was that the design was not
converging: every round had added structure faster than it removed attack surface. It recommended
an ACL ordered by one owner or admin device, failing over by signed handoff, with record sync
staying multi-writer. This round does that. The multi-parent DAG ACL is deleted, not kept beside
the new design.

- **Base:** the round-4 head (commit `23eeea92`) plus this round. Like the tables above, this one
  names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 96 unit tests in
  `aurora-link` (two of them property tests, also run once at 600 cases each in release), 5 vector
  tests, and 13 in `aurora-linkd` (1 ignored, a measurement). The seven Python link test files pass
  against the new wheel and debug daemon (176 tests, one of them a new real-daemon test of
  proposals, a relayed join, a handoff and a takeover). `cargo fmt --check`, `cargo clippy
  --all-targets -- -D warnings`, `cargo deny check` and the fuzz smoke (`fuzz/smoke.sh 10`) are
  clean.
- **Formats changed.** ACL entries are format 2 (`{v, link, term, seq, prev, ts, sequencer, body,
  proposals, cuts, sig}`); proposals and signed refusals are new; a removal's cuts moved from the
  op to the entry; a join is a proposal (`{invite, proof, label}`, proof bound to the proposal's
  nonce); genesis names its sequencer. Records are version 2 and name one chain position
  (`acl: {term, seq, hash}`). The sync ALPN is `aurora/link/2` and the join ALPN
  `aurora/link-join/2`; `hello` carries the chain tip; `acl_want {from, to}` asks for a seq range,
  answered by `acl` pages and `acl_done {upto}`; `propose`, `refusal`, `evidence` and `ping` are
  new frames; `join` carries a proposal. The store is schema 6 (`acl_entries` by seq,
  `acl_evidence`, `proposals`, and each record's `acl_seq` and `acl_hash`). Stores, peers and
  codes from round 4 are refused; there is no translation. The vectors (`acl-chain.json`,
  `acl-equivocation.json`, records) and the fuzz seeds were rebuilt.

### Why the DAG was dropped

In the DAG an author chooses its entry's parents, so it chooses what the entry is "concurrent"
with. A dormant or removed device can sign on old parents with a later `ts`, and the entry then
looks concurrent with everything since. Every rule that read time or precedence from a missing
causal edge could be used that way: late joins (R5-1), "decline beats accept", "of two role
changes the lower stands", the rotation grace, caps counted in an entry's causal past, and settle
cycles (R5-2). An honest device offline for long enough did the same by accident (probe `p4`).
Rounds 1 to 4 patched each rule and added new structure each time (claims, forks, witnesses,
settling, pruning with evidence), and each round found the new structure attackable.

From first principles: if exactly one key fixes the order, nobody can place an entry before an
earlier one, and authorisation is a plain check of each entry against the linear state where it
applies. There is nothing to resolve, so there are no tie-breaks to win and no causal gaps to read
time from. The price is a trusted role, the sequencer, and its liveness.

### Round-5 findings

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R5-1 | critical | `late_joins` treated a missing causal edge as proof of time: a dormant or removed device signed a "witness" on old parents dated after an invite's expiry, evicting every later join through it and undoing the attacker's own removal (`p1`, `p1b`); an honest offline device did it by accident (`p4`). Entry-carried renewals were bounded only from below | Fixed (mechanism removed) | `link/src/acl.rs`: the DAG is gone. `AclState::apply_entry`: an entry must follow the chain's last entry (`prev`, `seq + 1`, `ts` not going down) and be signed by its term's sequencer. A non-sequencer's action is a `Proposal`, checked by `AclState::apply_proposal` against the state where the sequencer appends it: a removed device is no active member; a stale `base` (the chain moved past it more than `PROPOSAL_MAX_AGE_S` before) is refused. Invite expiry is checked once, against the entry's sequencer-stamped `ts` (`apply_join`); nothing later reads a join's time again. `check_renewal`: a renewal must start at or before the stored certificate's end, come inside the renewal window, and come at most one lifetime after the stored end | `acl/tests.rs`: `r5_p1_a_removed_dormant_device_cannot_backdate_a_witness`, `r5_p1b_a_long_removed_member_cannot_act_on_its_old_horizon`, `r5_p4_an_honest_offline_device_evicts_nobody`, `invite_expiry_is_judged_by_the_entry_time_the_sequencer_stamps`, `renewals_are_bounded_on_both_sides`, `a_device_renews_itself_on_the_sequencer_and_by_proposal` |
| R5-2 | high | A dormant device's backdating horizon was unbounded. The pass ordered entries by `seq`, so a backdated removal was checked against its target's old state (`p2`); "decline beats accept" (`p3`) and "the lower role stands" (`p5`) vetoed owner promotions, and removing the vetoer did not undo the veto | Fixed (mechanism removed) | `link/src/acl.rs`: the chain has one order, fixed by the sequencer at append time, so every check sees the target as it is then. `AclState::apply_action`: only the owner removes an admin (or, new, an admin's device) or changes an admin's role; a decline needs a join still pending. `Victims`, supersession and settling are deleted | `acl/tests.rs`: `r5_p2_a_plain_admin_cannot_remove_an_admin_the_owner_promoted`, `r5_p3_a_decline_after_the_accept_is_refused`, `r5_p5_a_role_change_cannot_veto_an_owner_promotion`, `a_proposal_is_checked_against_the_chain_as_it_stands_when_it_is_appended`, `removing_an_admins_device_is_the_owners_alone` |
| R5-3 | medium | `acl_want` with an empty `have`, or a fresh hello, returned the whole log: 106 bytes in, 1,533,190 out (14,464x), and at 120 frames a minute 183 MB a minute per session (`p6`) | Fixed | `link/src/sync.rs`: a hello carries only the chain tip and triggers no ACL transfer. `acl_want {from, to}` is answered with exactly `from < seq <= to` (`AclChain::range`), in frames of at most `ACL_FRAME_BYTES` (256 KiB), never more than `ACL_BYTES_PER_MIN` (8 MiB) a minute per session (plus at most one entry), then `acl_done`. The asker keeps one want outstanding (`Session::want_toward`, `Session::ask`); a want the budget cut short is asked again at the next ping | `engine/tests.rs`: `r5_3_acl_answers_are_bounded_by_the_range_and_the_session_budget`, `an_acl_answer_cut_short_by_the_budget_is_asked_again_at_the_next_ping`, `a_5000_entry_chain_syncs_from_scratch_with_bounded_frames` |
| R5-4 | medium | linkd allowed 256 sessions in all, with no cap per peer and no idle timeout | Fixed | `linkd/src/net.rs`: `SessionCount` and `SessionSlot` hold at most `MAX_SESSIONS_PER_PEER_LINK` (2) sync sessions per (link, peer), inbound and outbound; `run_session` closes a session with no frame for `IDLE_TIMEOUT` (120 s) and sends a `ping` every 45 s, which counts as a frame. The per-session ACL frame limit (120 a minute) is kept | `linkd/src/net_tests.rs`: `sessions_are_capped_per_peer_and_link`, `an_idle_session_is_closed_and_a_third_is_refused`; `engine/tests.rs`: `acl_frames_per_session_are_rate_limited` |
| R5-5 | low | `lost_fork` status depended on when a record arrived, and records admitted before a retroactive change stayed admitted | Fixed | `link/src/engine.rs`: `Link::position` decides a record's named position from the record and the chain alone: on the chain (checked against the state there, `Link::check_at`), not reached yet (`Admit::Pending`, the range is fetched), or lost (the chain's term at that seq, or at its end before it, is later than the position's). A lost position stores the record `withheld` as `LOST_FORK`, which is final. When a takeover drops positions, `Store::lose_positions` withholds every record already stored on them (body cleared, cursor removed) | `engine/tests.rs`: `r5_5_records_on_a_dropped_position_are_withheld_whenever_they_arrive`, `an_equivocating_sequencer_halts_sync_until_the_owners_takeover`, `a_record_on_an_unreached_position_waits_and_the_chain_is_fetched` |

### The new rules, in brief

The `acl.rs` module doc states them; `engine.rs` and `sync.rs` document admission and sync.

1. **The chain.** Each entry follows the previous one (`prev`, `seq + 1`, `ts` monotonic) and is
   signed by its term's sequencer. Membership is the fold of the entries in order
   (`AclChain::push`, `AclState::apply_entry`). State snapshots every 256 entries make the state at
   any position at most 255 applications away (`AclChain::state_at`).
2. **Proposals.** Any authorised action by another device is a `Proposal {link, kind, args,
   proposer, base, nonce, sig}`, carried by sync (`propose` frames, relayed by any member, at most
   1,024 queued for relay). The sequencer checks it against the current state when it appends,
   includes it with the proposer's signature, or refuses it with a `ProposalRefusal` it signs, which
   any member relays back. A proposal is included at most once; its base must be on the chain, and
   the chain must not have moved past it more than 7 days before. The sequencer's own actions are
   entries with a self-authored body. An action's id (an invite's key in `AclState::invites`, a
   join's in `pending_joins`) is the entry hash for a body and the proposal id for a proposal.
3. **Clock rules** read the entry's `ts`: invite expiry, the rotation grace, certificate validity,
   the renewal window and its new upper bound. A replica refuses an entry more than 600 s ahead of
   its clock. The sequencer is trusted for order and time, and the docs say so.
4. **Terms.** Term 1's sequencer is the owner's device that signs genesis. `handoff {to}` (by the
   sequencer, or proposed by an owner device) makes the next entry term + 1, signed by `to`, an
   active owner or admin device. A root `Takeover {term, after, sequencer, sig}`, signed by the
   owner's fleet root, starts a later term right after `after`; replicas drop their entries after
   it. Where two branches differ, the one whose first differing entry has the higher term wins, and
   in one term a takeover beats a handoff's successor (`AclChain::insert_one`). The sequencer must
   stay an active owner or admin device: removing or demoting it needs a handoff first.
5. **Equivocation.** Two entries at one position on one prefix, signed by that term's sequencer,
   halt the chain at the common prefix (`AclChain::check_equivocation`, `note_evidence`). Both are
   kept as evidence (`acl_evidence`), raised as an alarm, shown in `link.status` and health, and
   sent to peers (`evidence` frame). Nothing advances until a root takeover of a later term.
   Records naming a position past the prefix stay Pending.
6. **Records** stay multi-writer. A record names `(term, seq, hash)`; see R5-5. Its author must
   have been an active device there, its epoch the one in force there, and write rights must hold
   there and now; the removal entry's cut (the device's feed head as the sequencer holds it)
   bounds a removed device's feed.
7. **Key rotation.** A removal without a key leaves a rotation due. The designated rotator is the
   sequencer when it holds the key, so the sequencer rotates at once; it takes a rotation proposal
   from any other key holder once `ts` is past due + 1 h. The junk-wrap alarm and the admin's
   recovery re-key are kept: a rotating key holder can still wrap junk to others.
8. **Sync** pulls ranges (R5-3); a tip conflict at one position is asked for and checked as
   evidence; a received entry that does not link makes the asker go back 256 entries at a time
   until the fork point. linkd caps sessions per (peer, link) and closes idle ones (R5-4).
9. **Invites** stay single-use, expiring, and keyed by the action that issued them; the first join
   included uses one up, and the sequencer refuses a second. The join door hands a join it cannot
   include to the sequencer and waits up to 20 s; otherwise the joiner runs the join again later,
   and the door then hands it the chain (its own join used the invite).

### How each earlier attack class is ruled out by construction

| Attack class (rounds) | Why it worked in the DAG | Why it cannot work on the chain |
|---|---|---|
| Backdated entries on old parents (A1, F1, R4-5 `p3`, R5-1, R5-2) | The author chose its parents, so its entry sorted early and looked concurrent with what it should have seen | Only the sequencer places entries, at the end; a proposal's base is advisory and every check runs against the state at append time |
| Late joins and witnesses (R4-6, R5-1, `p4`) | A missing causal edge was read as proof of time | Expiry is checked once, at the sequencer's `ts`; nothing re-reads it |
| "Decline beats accept", "the lower role stands" (R4-6, R5-2) | Concurrent entries needed a deterministic loser | There are no concurrent entries; the second action meets the state the first left |
| Settle cycles and supersession (R3-F2, R4-5) | Removals of each other's authors needed settling | Each removal checks its author is active when it applies |
| Grace start from a backdated entry (R4-7) | The due time came from an author-claimed `ts` | It is the `ts` of the entry that made it due, stamped by the sequencer, monotonic |
| Caps counted in the causal past (H1, H2) | An author chose which of its entries its past held | No validity caps remain; the sequencer's per-member allowance is admission policy |
| Device forks and `aseq` (H1, R3-F1, R3-F5, R4-3) | A device could sign two entries in one place | A device's entry exists only if the sequencer includes it; two proposals are two actions, checked one after the other |
| Claims (one device id, one root, one label) (R4-6) | Concurrent claims needed both to fail | The second claim meets the first's state and is refused (device known, member exists, label used) |
| Pruning, stubs, parked entries, orphans (H1, R3-F6, R4-2) | Dead branches had to be stored, pruned and fetched | Nothing is dropped except by a takeover, which drops whole suffixes, and the evidence of an equivocation |
| Hello size and amplification (R4-1, R5-3) | A hello listed heads; a want answered the past of a head set | A hello names one tip; a want names a seq range, budgeted per frame and per minute |
| Antichain heads, resolution budgets, epoch LRU (R3-F4, R4-10) | A record could name any head set and cost a resolve | A record names one position; the state there is a snapshot plus at most 255 applications |
| Refused-entry cache and small-batch prechecks (R4-8) | A never-valid entry cost a full resolve each time | An entry either follows the tip or does not; checking it costs one application |

### Probe results, before and after

`probe5` is the reviewer's crate, release build, run against the round-4 head (`probe5-before`,
the crate unchanged). `probe5-after` runs the same shapes on the chain: each attacker's action is a
proposal signed on the base it saw, offered to the sequencer later.

| Probe | Before (round 4) | After (round 5) |
|---|---|---|
| `p1` removed dormant writer's witness | Inserted; X (the honest join) evicted, B's removal undone, B active with 2 devices, epoch 0 readable by B | Refused ("author is not an active member device"); X a member, B removed. An entry in B's name at an old position is not the sequencer's: ignored, no halt |
| `p1b` removed member, 200 days on, renewed certificate | Inserted; all three later joiners evicted | Refused on its old base (stale) and on a fresh base (not a member); joiners active. (Run at 60 days: at 200 days the owner's own certificate would need renewing too) |
| `p2` plain admin removes an owner-promoted admin | Inserted at seq 9; M removed, the promotion and M's invite dropped | Refused ("only the owner may remove an admin"); M an admin |
| `p3` decline after the owner's accept | Inserted; N removed, its promotion dropped | Refused ("no such pending join"); N an admin, active |
| `p4` honest device offline two days | Y evicted on both replicas ("its invite expired at an entry it did not see") | The proposal is included; Y active on both replicas; one tip |
| `p5` lower role change 40 days later | Inserted; M a writer, Y evicted; removing X undid nothing | Refused on its old base (stale) and on a fresh base ("this author may not make that role change"); M an admin |
| `p6` amplification | 1,505 entries: request 106 B, reply 1,533,190 B (14,464x); 183 MB a minute per session | A fresh hello: 0 bytes of ACL. One want for the whole range: 45 B in, 1,427,409 B out (the whole chain, 31,720x), but 100 such wants in one minute get 8,402,051 B in all (the 8 MiB budget plus one entry). A want for 10 < seq <= 13 gets entries 11, 12, 13 |

### Measurements

Release build, this machine.

| Shape | Round 4 | Round 5 |
|---|---|---|
| A 5,000-entry chain checked from scratch by a replica (signatures, certificates, every rule) | n/a (3,000-entry DAG from scratch: 0.66 s in the supersession shape) | 0.47 s |
| The state at four positions of that chain | per head set: a resolve of the past | 3.7 ms in all |
| 5,000 appends; one more at 5,001 entries | 3,000 appends 30 s; one more about 21 ms (a full re-resolve) | 1.45 s; 0.28 ms (one application) |
| A 5,000-entry chain synced to a member that saw only the start | 2.3 s (with a joiner, R4-1 test) | 0.67 s, 25 frames, 4.7 MB, each `acl` frame at most 256 KiB of entries |
| Property tests at 600 cases | 3 tests | 2 tests (`replicas_of_one_chain_always_agree`, `replicas_that_sync_agree`): 25.8 s together |

### Mechanisms removed

- **The DAG and its resolution** (`acl.rs`, about 2,100 of its 4,004 lines): `Dag`, `Node`, `Walk`,
  `Upfront`, `Victims`, `Dag::settle` with Tarjan's strongly connected components, `Mode::forced`
  and `lenient`, `Dag::forks_and_claims`, `Dag::late_joins`, `Dag::concurrent_ts`, `Dag::lca`,
  `Dag::region`, `Dag::in_past`, `update_cuts` and the cut cache, `needs_admin`.
- **Multi-parent entries:** `prev` as a set, `MAX_PARENTS`, `aseq`, `dev_count`, `parents_for`,
  `latest_own`, `reaches`, `next_seq`, antichain checks (`is_antichain`, `past_of`), `latest_heads`,
  `heads` in the state.
- **Forks and claims:** `forks`, `join_forks`, `invite_forks`, `joined_via`, `fork_dropped`,
  `FORK_EVIDENCE`, display labels with a root suffix (`display_label`, `LABEL_SUFFIX`).
- **Caps in the causal past:** `check_log_rules`, `capped`, `absorb`, `recent`,
  `MAX_MEMBER_ENTRIES_PER_DAY`, `MAX_ADMIN_ENTRIES_PER_DAY`, `RATE_WINDOW_S`.
- **Storage of dead branches:** `prune`, `parked`, `Recent` (the LRU), `MAX_RECENTLY_PRUNED`,
  `MAX_PARKED`, `pins`, `set_pins`, `orphans`, `take_orphans`, the refused-entry cache
  (`MAX_REFUSED`, `refused_for_good`), `PRECHECK_BATCH`, `Facts` and `Meta` in the store.
- **Record head sets and their budgets:** `EpochCache` (the epoch LRU), `epoch_for`,
  `epoch_is_cheap`, `unknown_of`, `MAX_RESOLVES_PER_HOUR` and `Link::charge`, `AclView`, `Heads`,
  `MAX_WANT`, `recheck_withheld` and `keys_seen` (a lost position is final), `Store::withheld`,
  `Store::reopen`.
- **Provisional cuts:** `provisional_cuts`, `cut_ts`, `cuts_to_lower`, `lower_cut`, and cuts chosen
  by the remover (the sequencer fills them from the feed heads it holds).
- **Sync over heads:** `acl_count`, `missing_for`, `missing_for_heads`, `missing_for_want`, the
  head-set `acl_want`.

`acl.rs` went from 4,004 lines to 2,644 (34 % fewer; 3,817 to 2,556 without the module doc), and
its tests from 2,993 to 1,378 lines. Across `aurora-rs/link/src` and `aurora-rs/linkd/src` the
round adds 5,064 lines and removes 7,917. What was added: proposals and signed refusals, terms with
handoff and root takeover, fork choice and equivocation evidence, renewal upper bounds, chain
storage with snapshots, the proposal queue in the store, range sync with `acl_done`, the session
caps and the idle timeout.

### Known trade-offs of round 5

1. **The sequencer is trusted for order and time.** It cannot sign for anyone, and every replica
   checks every action, but it decides which valid proposals go in, in which order and with which
   `ts` (within 600 s of each replica's clock, never going down). It can delay or censor
   membership changes. The remedy is a handoff, or the owner's takeover.
2. **Liveness depends on the sequencer.** While it is offline, membership changes (joins through
   other admins, removals, role changes, rotations by others) queue as proposals; records keep
   flowing. A due rotation waits for it: writers stop sealing new mail until then (as before, but
   no other device may stand in without the sequencer including it).
3. **A takeover needs the recovery phrase**, kept offline, as certificate renewal does. A fleet
   whose owner lost the phrase cannot replace a lost sequencer; it can still hand off while the
   sequencer lives. The takeover does not remove the lost or stolen device: the owner removes it
   next.
4. **An equivocation halts membership** on every replica that sees it until the owner's takeover.
   Records naming positions before the halt keep flowing. While halted, the sync gate and record
   checks use the prefix's state, so a device removed after the prefix still syncs.
5. **A takeover whose `after` lies on a branch a replica does not hold** (the other side of an
   equivocation) cannot apply there; the CLI's default `after` is the common prefix.
6. **Amplification per request is still large** when a member asks for the whole chain, which is
   how a fresh replica syncs; the bound is per session (8 MiB a minute plus one entry) and per
   (peer, link) (2 sessions).
7. **A record may name an old position** and be sealed under that epoch's key, as before. Write
   rights are checked there and now; a removed device is bounded by its cut.
8. **Proposals can go stale.** One whose base the chain moved past more than 7 days earlier is
   refused, and the proposer proposes again (the daemon does so for rotations; other changes are
   shown as refused in `link.status`).
9. **Departures from today's roles:** removing an admin's device is now the owner's (or the admin's
   own) alone, matching "only the owner removes an admin"; a role change to the role a member
   already has is refused instead of being a no-op; labels are unique among live members (no root
   suffix).
10. **The sequencer's per-member allowance** (32 proposals a day, 512 for an admin) is its
    admission policy, not a validity rule; a malicious sequencer can grow the chain, and the
    owner's remedy is a takeover.
11. **No protocol negotiation.** Peers, stores and invite codes from round 4 are refused; every
    replica must run this round's code, and stores must be synced again.

### Changes to round-4 rows

- **R4-1** (hello size): the hello now names one tip (R5-3).
- **R4-2, R4-3, R4-5, R4-6, R4-7, R4-10:** the mechanisms they patched are gone; each attack class
  is ruled out by the chain (table above).
- **R4-4** (proof of possession): kept everywhere, for entry sequencers, proposers, genesis devices
  and added devices.
- **R4-8** (re-sent refused entries): the refused-entry cache is gone; an entry that does not follow
  the tip costs one application. The per-session ACL frame limit is kept.
- **R4-9** (renewal window): kept, with the new upper bound (R5-1).
- Every round-4 trade-off that concerned the DAG (cycles cutting the honest device, invite holders
  failing joins while live, failed joins kept, soft member caps and labels, the lower role change
  winning, pruned entries offered again, truncated hellos, the bounded refused cache, withheld
  rechecks, the grace pushed back, the O(n) append) no longer applies.

## Round 6

A sixth independent review read the sequenced chain of round 5 and found two critical issues
(R6-1, R6-5), three medium (R6-2, R6-3, R6-4) and two low (R6-6, R6-7), each
reproduced with a probe crate (`probe6 p1` to `p5`). Its common thread: the halt that round 5 added
as a fail-closed reaction to equivocation could be pulled by keys that no longer held any power, or
by no key at all, and pulling it folded authorisation back to an older state. This round fixes
each finding under four rules:

1. **A halt never widens access.** Evidence may stop ACL appends and is an alarm; it never folds
   authorisation back.
2. **Evidence must be real.** Two entries count only if each would apply on its own on the common
   prefix: a dry `apply_entry` with cuts skipped (signature and authority, a takeover's root
   signature, named device and `after`, certificate validity at `ts`, size).
3. **No device keeps a veto it no longer holds.** An ex-sequencer's old key is not a lasting halt
   switch.
4. **Only the sequencer's word is final.**

- **Base:** the round-5 head (`a05cdf98`) plus this round (nine local commits, `ef39fc3b` to the
  docs commit). Like the tables above, this one names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 108 unit tests in
  `aurora-link` (three of them property tests, also run once at 600 cases each in release, 26.1 s
  together), 5 vector tests, and 13 in `aurora-linkd` (1 ignored, a measurement). The seven Python
  link test files pass against the new wheel and debug daemon (177 tests, one new). `cargo fmt
  --check`, `cargo clippy --all-targets -- -D warnings`, `cargo deny check`, the fuzz smoke
  (`fuzz/smoke.sh 10`), ruff and ty on the changed Python files, and the docs checker are clean;
  `openrpc.json` and `rpc_types.py` are current.
- **Formats changed.** A proposal carries a signed `expires` (`{v, link, kind, args, proposer,
  base, expires, nonce, sig}`). `MAX_ENTRY_BYTES` is 512 KiB (was 192 KiB), and a link's policy
  allows at most `MAX_LINK_MEMBERS` (32) members. The store is schema 7 (`proposals.grp`, the
  origin of a kept proposal). `link.status` adds `acl_held_tip` and `halted_view`. The
  `acl-chain.json` vector and the fuzz seeds that carry a proposal were rebuilt. Round-5 stores
  are refused, as before; there is no translation.
- **How the tests were checked to fail before the fix:** each fix was disabled in turn in a scratch
  worktree (folding back on a halt, `settled_above` always false, `applies_alone` always true, the
  round-5 `take_refusal`, no size check with the old 192 KiB limit, no origin check or size caps
  or charges, no takeover voiding, and `acl_done` progress by `upto`). Each disabled fix fails its
  permanent test below; folding back, or a view of the prefix alone, also fails the property test.

### Round-6 findings

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R6-1 | critical | An old sequencer's key could halt the link at any position of its old term, and the halt ran `self.state = fold_to(e.seq - 1)`, bringing back removed members and old epochs for sync, records and sealing (`p1`: a removed member synced and wrote again, honest writers sealed under the pre-removal epoch, and the default takeover dropped later history) | Fixed | `link/src/acl.rs`: `AclChain::set_halt` keeps the held state; `AclChain::state` returns, while halted, `AclState::narrowed` (a device active in both the held tip's state and the prefix's, at the lower role; cuts and keys from the held tip; positions from the prefix). `AclChain::settled_above`: evidence below a term start on the held chain by a root takeover, or by a device of another member than the evidence's signer, is an alarm, not a halt. `AclChain::takeover`: `after` defaults to the held tip, and must be given while halted below it. `link/src/engine.rs`: `Link::halt_gate` (nothing is sealed while halted), `Link::ack`, `Link::self_monitor` (reads the held state), the alarm text | `engine/tests.rs`: `r6_p1_an_ex_sequencers_old_key_neither_halts_nor_folds_back`, `r6_1_a_halt_never_brings_back_a_removed_member_or_an_old_epoch`; `acl/tests.rs`: `r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork`, `equivocation_halts_the_chain_until_a_root_takeover`, and the property test `evidence_never_widens_access_or_seals_under_an_older_epoch` |
| R6-5 | critical | "Two takeovers of one term" waived `same_signer` and checked neither takeover, so an outsider's self-made certificate with a junk root signature halted the link after every takeover and folded it back (`p5`), by insert or by an evidence frame | Fixed | `link/src/acl.rs`: `AclChain::check_equivocation` and `note_evidence` count a pair only if each entry applies on its own on the common prefix (`AclChain::applies_alone`, a dry `apply_entry`); a takeover's root signature is checked before any fold | `acl/tests.rs`: `r6_p5_a_forged_takeover_copy_is_not_evidence` (the root really signing two takeovers of one term still halts) |
| R6-2 | medium | `take_refusal` accepted a refusal from any device that may sequence, so a non-sequencer admin made the owner's other device drop its own proposal to remove that admin, and made relays drop it too (`p2`) | Fixed | `link/src/engine.rs`: `Link::take_refusal` takes a refusal only from the device that sequenced at `r.at`, a position on this chain at or past the proposal's base; one's own proposal stays queued unless the current sequencer refused it; the sequencer takes none it did not sign. `Link::offer`: the sequencer answers with a stored refusal only if it signed it and the chain has not moved since | `engine/tests.rs`: `r6_p2_only_the_sequencer_at_the_position_refuses`, `proposals_travel_to_the_sequencer_and_signed_refusals_travel_back` |
| R6-3 | medium | `append` had no size check, so the sequencer signed entries every other replica refused; a rotation with X-Wing wraps to about 106 or more readers was larger than `MAX_ENTRY_BYTES`, at the default policy's capacity (`p3`: 121 readers, 222,337 bytes), and the divergence was silent | Fixed | `link/src/acl.rs`: `MAX_ENTRY_BYTES` = 512 KiB and `MAX_LINK_MEMBERS` = 32 (genesis refuses more), so the largest entry a policy allows fits (32 x 8 X-Wing wraps in a proposal: 469,745 bytes); `AclChain::append` signs nothing larger (so `Link::offer` refuses such a proposal); `AclChain::insert` reports a refused entry that is the sequencer's next one (`Inserted::diverged`), and `Link::add_acl` raises an `acl_divergence` alarm | `acl/tests.rs`: `r6_p3_a_rotation_at_the_policys_capacity_fits_and_nothing_larger_is_signed`, `the_largest_policy_fits_one_entry_and_one_frame`; `engine/tests.rs`: `a_refused_sequencer_entry_is_an_alarm` |
| R6-4 | medium | Refused proposals piled up on the sequencer without bound, from self-made fleets, with 1.5 MB strings (`p4`: 165 MB sent in two minutes of one session, 111 rows and 165 MB kept); the relay queue could be flushed by one member | Fixed | `link/src/acl.rs`: `Proposal::max_bytes` (a cap per kind, checked with the signature). `link/src/engine.rs`: `Link::check_origin` (a non-join only from an active member's device, a join only once its invite proof verifies); `Link::offer_from` charges each refusal to the session peer's fleet and stops taking its proposals at its daily allowance; refused rows are trimmed. `link/src/store.rs`: `Store::trim_relayed` keeps at most `MAX_RELAYED_PER_ORIGIN` (64) per origin and 1,024 in all. `link/src/sync.rs`: `propose` frames go through `offer_from` | `engine/tests.rs`: `r6_p4_refused_proposals_are_bounded_and_charged_to_the_peer` |
| R6-6 | low | A proposal included in an entry that a takeover dropped could be included again, bringing back an invite with `used = false`; refusals did not survive a handoff | Fixed | `link/src/acl.rs`: `Proposal::expires` (signed; an entry at or after it does not include the proposal, and it is at most `PROPOSAL_TTL_S` + 600 s ahead of the entry), replacing the 7-day staleness rule; `AclState::takeover_at`: a proposal on a base before the latest takeover is void until signed again. A refusal binds only the sequencer that signed it (R6-2), and an expiry bounds how long a refused proposal can come back | `acl/tests.rs`: `r6_6_a_proposal_on_a_dropped_position_is_void_until_signed_again`, `a_proposals_base_must_be_on_the_chain_and_it_expires`, `r5_p1b_a_long_removed_member_cannot_act_on_its_old_horizon` |
| R6-7 | low | In `acl_done`, `progress = upto > asked_from` looped on entries the asker refused | Fixed | `link/src/sync.rs`: `Session::ask` records our tip; `acl_done` asks again only if the tip moved | `engine/tests.rs`: `r6_7_refused_entries_are_no_progress_and_are_not_asked_for_again` |

### Evidence below a later term start: the rule

**The rule** (`AclChain::settled_above`). Evidence at seq `s` (two entries of term `t`, each
applying on its own on the prefix) does not halt this replica if its held chain, above `s`, has
an entry of a later term that is a root takeover, or that was signed by a device of another
member than the evidence's signer. It is then kept as evidence and raised as an alarm ("not
halted"), and the entry loses fork choice. Otherwise it halts, narrowed as R6-1 says.

**Why it is safe for the branch that has the later term.** Fork choice compares two branches at
their first differing entry: the higher term wins there, and in one term a takeover beats a
handoff's successor. Both entries of the pair are in term `t`, so neither wins; the incumbent stays.
A replica holding the later term start has committed to its branch, and so has every honest replica
that holds it. Halting it would stop the current sequencer, which did nothing wrong, and the old
key would hold a veto it gave up with its handoff (principle 3). Nothing is folded back either way.

**Why self-handoffs buy nothing.** A malicious ex-sequencer can grow its own branch from the forged
entry and hand off to its own fleet's other devices to climb terms. Its term starts are by its own
member, so they do not count: a replica that holds such a branch halts when it sees the honest
entry. A replica on the honest branch never switches to it: the branches differ first at `s`, in
one term, so the incumbent stays, and the later terms the attacker reached never come into it (an
entry above `s` on the other branch does not link, and the walk back meets the losing entry). The
test `r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork` builds both.

**Why a real split is still caught.** A sequencer that signs two entries during its own term, and
keeps both branches apart, halts every replica that sees both before a later term starts on its
branch: that is the usual case, since replicas compare tips at every session. What the rule gives
up: if the equivocator keeps the branches apart until it has handed off on both of them, each to
a device of another member, the replicas on each branch raise an alarm and go on. The split stays
visible (records written on one branch wait on the other, and `aurora doctor` names the alarm)
until the owner's takeover. That needs the equivocating sequencer and two other members' devices
that take its handoffs, and it is listed as a trade-off below.

**The candidate checked and kept.** This is the review's candidate, with one change: a later term
counts only if a root takeover or another member started it, which is what keeps fork choice from
rewarding a self-handoff branch.

### Probe results, before and after

`probe6` is the reviewer's crate, release build, run against the round-5 head (`probe6-before`,
the crate unchanged). `probe6-after` runs the same shapes on this round's code, with the API
changes it needs (a proposal's expiry, `take_refusal`'s device, `join_proposal`'s clock) and no
panics on the outcomes that are now refused.

| Probe | Before (round 5) | After (round 6) |
|---|---|---|
| `p1` ex-sequencer, demoted to writer, signs at its old handoff | Halted at (2, 12); C folded back to seq 11: B active and `may_sync(B)`, E an admin, epoch 0; C sealed new mail under epoch 0, which removed B read; C admitted removed B's new record; the default takeover dropped seq 12 on, so C's honest record was withheld | No halt (`equivocation=false`), an alarm; C stays at seq 17 term 3, epoch 1, B removed, E a writer, `may_sync(B)` false; C seals under epoch 1; B's copy keeps the record waiting (it holds no position or key for it); B's new record is refused ("removed before this record"); the owner is not halted, and its default takeover continues after seq 17, so C's honest record stays admitted |
| `p2` non-sequencer admin forges a refusal | The owner's device took it (`Ok(true)`) and dropped its own removal of that admin; a relay took it too; the admin stayed | Refused at both ("signed by the device that sequenced the link at the position it names"); the owner's device keeps its proposal; the sequencer includes it and the admin is removed |
| `p3` rotation at the policy's capacity, X-Wing | 121 readers: 222,337 bytes (limit 196,608); the sequencer appended it, every other replica refused it, and stayed behind for good with no alarm | Fits (limit 524,288): the replica adds it, and after a session both hold seq 152. Larger entries are refused by `append`; a refused sequencer entry is an `acl_divergence` alarm |
| `p4` refused proposals from self-made fleets, 1.5 MB each | 165 MB sent; 110 signed refusals; 111 rows, 165 MB kept | 165 MB sent; no refusal signed and nothing kept (the one row is the setup's join): each is over its kind's cap, and after the peer's daily allowance (32) the session takes no more |
| `p5` forged second takeover (outsider's certificate, junk root signature) | Halted after the takeover and folded back to the old sequencer; again after the owner's second takeover (W, removed after it, active again, epoch 0); by an evidence frame too | Not evidence: no halt, tip and sequencer unchanged, W stays removed at epoch 1; the evidence frame returns `false` |

### Measurements

Release build, this machine.

| Shape | Round 5 | Round 6 |
|---|---|---|
| The largest entry a policy allows: a rotation proposed by an X-Wing admin to 32 x 8 X-Wing devices | not allowed (over 192 KiB at about 106 readers) | 469,745 bytes, under 524,288; one `acl` frame under 2 MiB |
| Property tests at 600 cases | 2 tests: 25.8 s | 3 tests (with `evidence_never_widens_access_or_seals_under_an_older_epoch`): 26.1 s |
| Evidence check | a signature | the fold to the prefix (at most 255 entries, signatures already checked) and one dry application; an evidence frame is still one of 120 ACL frames a minute per session |

### Known trade-offs of round 6

These replace round 5's trade-offs 4, 5 and 8; the others stand.

1. **An equivocation halts membership and new mail** on every replica that sees it, until the
   owner's takeover (was trade-off 4). Records written before keep flowing; nothing is sealed while
   halted (`Link::write` refuses, to be retried), because any position past the prefix may be
   dropped by the takeover and halted peers would keep the record waiting anyway. While halted, a
   replica grants only what both its held tip and the prefix grant: a device added past the prefix
   cannot sync with it until the takeover, and a removed one stays removed.
2. **A takeover continues after the replica's held tip by default** (was trade-off 5). Halted below
   it, the owner must choose `after`: the common prefix (every replica can take it; both branches
   of the equivocation are dropped, records on them withheld) or the held tip (this branch is kept;
   replicas holding the other branch stay halted until a takeover at or below the common prefix
   reaches them). `aurora doctor` and `aurora link status` name both commands.
3. **Proposals expire** (was trade-off 8): seven days after the proposer signs them, and a takeover
   voids every proposal signed on a base before it. The proposer signs again; the daemon does so for
   rotations.
4. **A split carried past a handoff on both sides is an alarm, not a halt.** If a sequencer keeps
   two branches apart until it has handed off on each, to devices of other members, each side goes
   on and raises an alarm (rule above). The owner resolves it with a takeover.
5. **Any member can spend an honest relay's allowance** (wording corrected in round 7; fixed
   there as R7-3). Every proposal a session peer hands over that is refused, or that fails a check,
   counts against that peer's fleet's allowance (32 a day for a member, 512 for an admin),
   together with the proposals the chain included from that fleet. A relay kept any member's
   proposal and any join with a verifying proof, used invite or not, so a member that sent it
   proposals the sequencer refuses used up the relay's fleet's allowance, and the sequencer took
   none of that fleet's own proposals for a day. The charges are kept in memory: a restarted
   daemon forgets them.
6. **The relay queue keeps a share per origin** (64 per proposer root, or per invite for joins, and
   1,024 in all). A relay behind on the chain keeps no proposal from a device it does not know yet,
   and no join for an invite it does not hold.
7. **A link has at most 32 members** (each with at most 8 devices), so its largest entry fits.

### Changes to round-5 rows

- **R5-1** (backdated witnesses): the staleness rule that bounded a proposal's base is replaced by
  the proposal's own expiry (R6-6).
- **R5-5** (records on dropped positions): unchanged, but fewer positions are dropped, since a
  takeover now continues after the held tip by default.
- The round-5 rule "the state a halted replica reports is the prefix's" is gone (R6-1).

## Round 7

A seventh review read round 6 and found one high issue (R7-1), two medium (R7-2, R7-3) and three
low (R7-4, R7-5, R7-6), each but R7-5 and R7-6 reproduced with a probe crate (`probe7 p1`, `p2`,
`p3`, `p3b`, `p4`). Their common thread: inputs an attacker controls were not bounded, or were
charged to someone else. Evidence cost a fold under the daemon's lock and a stored row each, with
no "already seen"; a relay paid for what it relayed; and the narrowed view of a halt, read by the
transport, cut off the very devices the takeover had to reach. This round fixes each under the
round-6 principle, made concrete: **no device keeps a power it no longer holds; every input an
attacker controls is bounded in storage and CPU, and charged to its origin.**

- **Base:** the round-6 head (`6bcf9449`) plus this round (local commits, `698f7123` to the docs
  commit). Like the tables above, this one names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes: 116 unit tests in
  `aurora-link` (four of them property tests, also run once at 600 cases each in release, 41.0 s
  together), 5 vector tests, and 15 in `aurora-linkd` (14 pass and 1 is ignored, a measurement;
  one is new, over real iroh endpoints). The seven Python link test files (`tests/test_link_*.py` and
  `tests/test_accel_parity.py`) pass against the new wheel and debug daemon (177 tests). `cargo fmt
  --check`, `cargo clippy --all-targets -- -D warnings`, `cargo deny check`, the fuzz smoke
  (`fuzz/smoke.sh 10`) and the docs checker are clean; no Python file changed, and `openrpc.json`
  and `rpc_types.py` are current (no RPC changed).
- **Formats changed.** The store is schema 8: `acl_evidence` keeps pairs, one per `(signer, term,
  seq)`, with what each did (`halt`, `alarm`, `past`). Round-6 stores are refused, as before; there
  is no translation. No wire format, vector or fuzz seed changed.
- **How the tests were checked to fail before the fix:** each fix was switched off in turn in the
  working tree (the screen before a check; the one-alarm-per-signer rule; the stop after one check
  per insert; the session charge per check; the evidence cap; the round-6 restore; the R7-5 rule,
  and a naive R7-5 that counts any removal; the session gate and the evidence sent to a held peer
  for R7-2, and `peer_links` reading the narrowed view in the daemon test, both with and without
  its direct assertion; the relay's `check_proposal`; the live-invite check; a refusal charged to
  the peer; and the round-6 `take_refusal`). Each failed its permanent test below. Switching off
  the alarm-per-signer rule, the screen, or the relay queue's per-origin trim also fails the new
  property test.

### Round-7 findings

| Id | Severity | Finding | Status | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R7-1 | high | Alarm-only evidence had no "already seen" bound. A demoted ex-sequencer sent thousands of distinct valid entries at one position of its old term; each cost a fold and a dry application under the daemon-wide `links` lock, was stored in `acl_evidence` without trimming, and was checked again on every restart (`p1`: 3,000 entries, 5.08 s of CPU, 3,000 rows of 2.6 MB, 4.31 s to open) | Fixed | `link/src/acl.rs`: `AclChain::screen` (before any signature or fold: a pair held for that `(signer, term, seq)`, the first winning; a halt at or below it; one more alarm about a signer already raised) gives `Found::Seen`; `AclChain::record` keeps the pair as seen, the signer as alarmed; `AclChain::insert` stops at the first evidence check, alarm or seen pair, and reports `Inserted::checks`; `AclChain::restore` checks only the halt's pair again; `MAX_EVIDENCE_PAIRS` = 256. `link/src/store.rs`: `Store::put_evidence` (pairs, the cap), `settle_evidence`, schema 8. `link/src/sync.rs`: `Session::charge_checks` (`EVIDENCE_CHECK_FRAMES` = 8 of the 120 ACL frames a minute per check). `link/src/engine.rs`: `Link::persist_acl` (no alarm for a pair the store does not keep) | `engine/tests.rs`: `r7_p1_an_evidence_flood_is_checked_once_kept_once_and_charged_to_the_session`, `r7_1_stored_evidence_stays_within_its_cap`; `acl/tests.rs`: the property test `floods_stay_within_their_caps_and_never_widen_access` |
| R7-2 | medium | While halted, `state()` is the narrowed view, which leaves out a device added past the prefix, this replica's own included. linkd's `peer_links` read it, so the dialer, the inbound gates, `Gated` and gossip dropped the link, and the device never received the takeover; between two such devices even `acl_want` and `evidence` were refused (`p2`) | Fixed | `linkd/src/daemon.rs`: `Daemon::peer_links` (and so `is_member_anywhere`) reads the held state; `record_peer_links` keeps the narrowed view for blobs (`net.rs: blob_shared_with`). `link/src/sync.rs`: `may_sync_acl` (a device of the held tip); `Session::on_frame` takes `acl_want`, `acl_done` and `evidence` from such a device, sends it our evidence at its hello, and lets its other frames pass unanswered instead of ending the session. `linkd/src/net.rs`: `run_session` pushes ACL entries to it and nothing else | `engine/tests.rs`: `r7_p2_devices_added_past_a_halt_trade_evidence_and_take_the_takeover`; `linkd/src/net_tests.rs`: `r7_2_a_device_added_past_a_halt_dials_accepts_and_takes_the_takeover` (two daemons over iroh) |
| R7-3 | medium | Relays kept any member's proposal and any join with a verifying proof on a dead invite, and the sequencer charged each refusal to the session peer (the relay): any member could silence an honest relay's fleet for 24 h, blocking for example the attacker's own removal (`p3`: 520 junk joins on a used invite; `p3b`: a writer's invites; X's removal of M then refused for its allowance) | Fixed | `link/src/engine.rs`: `Link::offer_charged` (a relay runs `AclChain::check_proposal` against its chain and drops what fails; a base past its chain is not kept, uncharged); `Link::check_origin` (a join needs a live invite, `Link::invite_live`, moved from `sync.rs`); `Link::offer_from` charges the peer (`Charge::Peer`) only for what it could have checked itself (shape, signature, size, expiry, a proposer or invite the chain never listed), the origin (`Charge::Origin`: the proposer's root, or `invite:<id>`) for a refusal and everything else that depends on the chain, and stops taking from a peer or an origin at its allowance | `engine/tests.rs`: `r7_p3_a_relay_keeps_only_what_holds_and_pays_nothing_for_what_it_relays` (also: a proposal under a member's certificate but another key charges the peer that sent it, never that member) |
| R7-4 | low | A halt from evidence at the next position (`seq == len`) was lost on restart, because `restore` only compared stored entries with held ones (`p4`) | Fixed | `link/src/acl.rs`: the pair is stored as a pair with its kind; `AclChain::restore` checks the halt's pair again through `note_evidence`, which handles the next position | `engine/tests.rs`: `r7_p4_a_halt_at_the_next_position_survives_a_restart`; `acl/tests.rs`: `a_restored_chain_keeps_its_halt_and_its_state` |
| R7-5 | low | After a self-handoff, the old device, retired and removed, kept a halt switch over its term's positions: the later term was its own member's, so evidence below it still halted | Fixed | `link/src/acl.rs`: `AclChain::settled_above` also counts a self-started later term once the signer's device cannot sequence at the held tip and an action above the position that it could not have authored itself removed or demoted it: one by the owner's fleet, or by another member (rule below) | `acl/tests.rs`: `r7_5_a_retired_and_removed_device_holds_no_halt_switch`, and `r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork` still passes |
| R7-6 | low | An ex-sequencer signed a fresh refusal naming a position of its old term, and relays dropped the proposal (one whose base was in that term) | Fixed | `link/src/engine.rs`: `Link::take_refusal` takes a refusal only from the current sequencer (checked first, before any fold), which also sequenced at its position | `engine/tests.rs`: `r7_6_an_ex_sequencers_fresh_refusal_is_not_taken`; `r6_p2_only_the_sequencer_at_the_position_refuses` and `proposals_travel_to_the_sequencer_and_signed_refusals_travel_back` (a forged refusal is now "not taken" rather than an error) |

### Decisions, and why

- **One alarm per signer, not one per position.** The review asked for one pair per `(signer,
  term, seq)`. That alone still lets an ex-sequencer of a long term make one check and one row per
  position of its term. An alarm-only pair changes no access; its only use is to say "this key
  signs twice", and one pair says that. So a second alarm about a signer is screened out before
  it is checked. Halting pairs are bounded differently: a new one counts only below the current
  halt, so they shrink towards the prefix.
- **What happens at the cap (256 pairs).** At the cap an alarm-only pair is not kept and raises no
  alarm (the screen still remembers it in memory until the daemon restarts); a halt's pair is always
  kept, and replaces the oldest pair that is not the current halt (`past` first, then `alarm`).
  Reaching the cap takes 256 distinct equivocating signers, or halts that each went lower: by then
  the owner has every proof needed, and the one pair that matters for access, the current halt's,
  is never evicted.
- **A check is charged after it runs.** A frame cannot say in advance whether it will need a
  check, so the session pays when it did: each check costs 8 of the session's 120 ACL frames a
  minute, and an insert never runs more than one, so a session gets at most 13 a minute (`p1`
  after). Entries that pass the signature but do not apply on their own are no evidence and are
  not remembered (only the signer of that term can make them), but each still costs the session.
  A failure budget per signer was rejected: a malicious current sequencer could spend its own and
  then equivocate unseen.
- **The peer is charged only for what it could have checked.** "What the peer could have checked"
  is read narrowly: what is the same on every chain (shape, signature, size, expiry) and what no
  honest relay passes on (a proposer or invite this chain never listed, while the proposal's base
  is on it). Anything that depends on the chain's state, which a relay may hold at an older tip,
  is charged to the origin. A base past this replica's chain is charged to nobody and not kept:
  the proposer still holds it and sends it again.
- **Forged refusals are "not taken", not an error.** R7-6 checks the signer against the current
  sequencer first, which costs nothing, before the fold that `state_at` needs. A refusal from a
  device that is not the current sequencer is dropped as stale, uncharged, because an honest relay
  may pass on a refusal it learned before a handoff.
- **The daemon-wide lock is a follow-up.** Every session frame runs under `Daemon::links`, one
  mutex over all links. Moving ACL work out from under it means a lock per link (`with_link` and
  nine direct lock sites), and would not separate sessions of one link. With this round's bounds
  the expensive work per session is at most 13 evidence checks a minute (a fold of at most 255
  entries each, about 1.7 ms in release) plus proposal checks inside the proposal budget. Per-link
  locks are left for later. *(Reworded in round 8: this round first said "so the lock is no longer
  an amplifier". That was wrong. The bound held per session only, and a member that reconnected
  got a fresh budget each time (R8-3). Record wants and pushed records had no budget at all, and
  one want loaded a whole feed under the lock (R8-2; probe `p2`: 39 s of CPU in one minute of one
  session). The ACL work was bounded per session; the lock still amplified everything else.)*

### Evidence below a later term start: the round-7 rule

**The rule** (`AclChain::settled_above`, extended). Round 6's rule stands: evidence at seq `s`
does not halt if the held chain above `s` has a later term started by a root takeover or by a
device of another member than the signer's. Round 7 adds: or a later term of the signer's own
member, once the signer's device cannot sequence at the held tip **and** an action above `s`
removed or demoted it (`remove_device` of it, `remove_member` of its root, `set_role` of its root
to a role that does not sequence) **whose author is the owner's fleet, or another member** (the
entry's sequencer for its own body, the proposer for an included proposal).

**Why the author test.** The review's candidate counted any removal or demotion. That reopens the
round-6 attack: admin E equivocates at `s`, hands off to its own other device E2 on its branch, and
E2 removes E's old device, which a member may do to its own device. Replicas on E's branch would
then see "a later term, and the signer removed", and alarm instead of halting, so E would carry a
split past a self-handoff alone, where round 6 needed two other members' devices. With the author
test, E's removal of its own device counts for nothing; the test
`r7_5_a_retired_and_removed_device_holds_no_halt_switch` builds that branch and checks that it
still halts, and that the naive rule does not (switched on, the assertion "no immunity from its own
removal" fails).

**Why the owner's fleet counts for itself.** The finding's case is the owner handing off from one
of its devices to another and then removing the old one. The owner's root is already the final
authority (it signs every takeover), so an action by the owner's fleet is not an attacker buying
immunity, unless the attacker holds two of the owner's devices, which is a compromise of the owner.
For a non-owner member the old device still holds a halt switch until the owner, another member,
or a later term by another member settles it; that is listed below.

**Why `r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork` still holds.** Its self-handoff
branch never removes E's device, and E's device may still sequence there, so the new clause does
not apply; the honest branch is settled by the owner's term, as before; and fork choice is
unchanged, so the climbing branch still loses at its first differing entry.

### Probe results, before and after

`probe7` is the reviewer's crate, release build, run against the round-6 head (`probe7-before`,
the crate unchanged). `probe7-after` runs the same shapes on this round's code, with the store's
new columns, and adds what the fix makes observable (the flood again after the restart, a junk
flood against a fresh replica's session, and a session in `p2`).

| Probe | Before (round 6) | After (round 7) |
|---|---|---|
| `p1` evidence flood: 3,000 distinct valid entries at one old position from a demoted ex-sequencer, in 2 frames of one session | C spent 5.08 s (1.69 ms an entry); 3,000 rows, 2,631 KB; 1 alarm; `Link::open` 4.31 s (every stored entry checked again); no halt | C spent 9.4 ms (3.1 µs an entry): one check, then everything is screened; 1 row, 1 KB; 1 alarm; `Link::open` 37 ms; no halt. The 3,000 again after the restart: 0 checks, 3.2 ms. Junk that costs a check each, one per frame: the session takes 13 frames, then ends ("too many evidence checks this minute") |
| `p2` a device added past the halt's prefix | N's narrowed view lists N inactive; linkd's `peer_links` skips the link, so N dials nobody and refuses everyone for it, and stays halted after the takeover | The narrowed view still lists N inactive (by design), but its held state lists it, and that is what `peer_links` reads; N trades chain frames with C; one session N to C (8 frames) and N is no longer halted and is active. Through two daemons: `r7_2_...` |
| `p3` 520 junk joins on M's used invite, sent to relay X | X queued and relayed 520; A refused 512, charged to X's fleet; X's own removal of M refused ("this peer's fleet reached its daily allowance"); M not removed | X kept and relayed none (a used invite; after 32, the invite's allowance at X, without a check); A saw nothing; X's removal of M included, M removed |
| `p3b` M's own refusable proposals (a writer inviting), relayed by X | A refused 512 relayed by X; X's removal of M refused for its allowance | X relayed none (they fail its check, charged to M); X's removal of M included |
| `p4` a halt from evidence at the next position, then a restart | Halted at 4, 2 rows; after the restart not halted, a write succeeded at seq 3, and one of the two entries was added | Halted at 4, 1 row; after the restart still halted at 4; the write refused (new mail waits for the takeover); neither entry added |

### Measurements

Release build, this machine.

| Shape | Round 6 | Round 7 |
|---|---|---|
| `p1` flood of 3,000 entries at one position (256-entry chain) | 5.08 s CPU, 3,000 rows (2.6 MB), open 4.31 s | 9.4 ms CPU, 1 row (1 KB), open 37 ms |
| Evidence checks a session can cause | one per entry: up to 120 frames x 2,391 entries a minute | at most 13 a minute (one per insert, 8 frames each) |
| Evidence rows a replica keeps | unbounded | at most 256 pairs; one per position and signer, one alarm per signer |
| Property tests at 600 cases | 3 tests: 26.1 s | 4 tests (with `floods_stay_within_their_caps_and_never_widen_access`): 41.0 s |

### Known trade-offs of round 7

These replace round 6's trade-off 5; the others stand.

1. **A refusal is charged to the proposal's origin** (replaces round 6's trade-off 5). The
   proposer's fleet, or the invite a join uses, pays for each refusal and for anything else that
   depends on the chain; the session peer only for what it could have checked itself. An honest
   relay behind the sequencer pays nothing for what it relays. A peer, or an origin, at its
   allowance gets no more taken, without a check and without a signed refusal, so its proposer
   learns nothing more that day and its own proposals wait. The charges are kept in memory: a
   restarted daemon forgets them.
2. **A relay keeps only what holds on its chain.** A relay behind the proposer (the base past its
   chain) keeps nothing until it catches up; the proposer sends its proposal again at each
   session.
3. **Evidence is kept once.** One pair per position and signer, the first; one alarm-only pair
   per signer; a halt only below the one standing; at most 256 pairs, and at the cap an alarm-only
   pair raises no alarm. The alarm names the first position a key was seen to sign twice, not
   every one.
4. **Budgets are per session.** The evidence-check charge, like the frame budget, starts again with
   each session; linkd caps sessions per peer and link, and closes idle ones, but does not rate
   new ones.
5. **A non-owner member that retires its own device after a self-handoff keeps that key's halt
   switch over its old term's positions** until the owner (or another member) removes or demotes
   the device, or another member's term or a root takeover follows. The owner's own retirements
   settle at once.
6. **Expensive ACL work still runs under the daemon-wide lock**, now bounded per session (a
   follow-up, above).

### Changes to round-6 rows

- **R6-1** (old key below a later term): the rule also counts a self-started later term once the
  owner's fleet or another member has retired the signer's device (R7-5).
- **R6-2** (who refuses): only the current sequencer's refusal is taken, by anyone (R7-6); a
  refusal by any other device is "not taken", not an error.
- **R6-4** (refused proposals): refusals are charged to the origin, not the session peer, and a
  relay keeps only what holds on its chain (R7-3). The round-6 test now makes its flooding member
  an admin, so the relay keeps its invites, then a writer again at the sequencer, which refuses
  them, a day after the peer's own charges.
- **R6-5** (forged evidence): unchanged; the screen runs before the checks it added, and a forged
  pair still occupies no slot (only a pair that passes them is kept).

## Round 8

An eighth review read round 7. It found no critical or high issue and judged the design ready for
a human outside review. It raised two medium findings (R8-1, R8-2) and two low ones (R8-3, R8-4).
It wrote no probes, so both medium findings were code traces. This round first reproduced each
finding as a failing test against the round-7 code, and as a probe (`probe8`, run on the round-7
head and on this round). Only then did it fix them. **All four reproduced.** Their common thread:
a bound that held per frame or per session, but not per proposal, per minute across sessions, or
per screen. The bound was also missing entirely on the record side of a session.

- **Base:** the round-7 head (`2ae025c1`) plus this round (local commits, `d1717351` to the docs
  commit). This table, like the ones above, names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes:
  - `aurora-link`: 122 unit tests. Four of them are property tests, also run once at 600 cases each
    in release (40.9 s together).
  - 5 vector tests.
  - `aurora-linkd`: 17 tests. 16 pass and 1 is ignored, a measurement. Two are new, one of them
    over real iroh endpoints.

  The seven Python link test files (`tests/test_link_*.py` and `tests/test_accel_parity.py`) pass
  against the new wheel and debug daemon (177 tests). These are clean: `cargo fmt --check`,
  `cargo clippy --all-targets -- -D warnings`, `cargo deny check`, the fuzz smoke
  (`fuzz/smoke.sh 10`) and the docs checker. No Python file changed. `openrpc.json` and
  `rpc_types.py` are current (no RPC changed).
- **Formats changed.** The `synced` frame gains an optional `more`. It is left out when false, so
  an old `synced` encodes the same. An answer to a `want` now ends with `synced`. The store gains
  one index, `records(author, received_at)`, which `CREATE INDEX IF NOT EXISTS` adds to a
  schema-8 store when it opens. The schema version, the vectors and the fuzz seeds are unchanged.
- **How the tests were checked to fail before the fix.** The R8-1 and R8-2 tests were written
  first and run against the round-7 code:
  - `r8_1_...` failed at the 512th replay ("this proposal's origin reached its daily allowance").
  - `r8_2_wants_...` failed at "28,048,320,000 bytes of records in one minute".
  - `r8_2_honest_catch_up_...` failed at "5000 records: B holds 4096 after 3 minutes".

  Then each fix was switched off in turn in the working tree, and each failed its permanent test
  below:
  - R8-1: charging an origin again for a proposal it already paid for; and the peer gate counting
    the fleet's charges as an origin and its included proposals, as in round 7.
  - R8-2: the `LIMIT` in `Store::range`; the record frame budget; the record byte budget; counting
    `heads` pages; asking again after `synced` with `more`; the budget on records a peer sends; and
    the new index.
  - R8-3: carrying the budget across sessions; the session-start rate.
  - R8-4: the kept bound (41 scans instead of 1).
  - The per-link lock: holding the map's lock through `with_link` (link two waited 1.0 s).

  The R8-4 bound is also compared with the round-7 scan on every call in the tests, the property
  tests included.

### Round-8 findings

| Id | Severity | Finding | Reproduced | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R8-1 | medium | A refusal was charged to the proposal's origin on every replay, since nothing was stored for a relay's failed check, or for the sequencer's failed `check_origin` or refusal at a moved tip. Peers were charged under the same key (the fleet root) as origins. So any member could replay one of X's proposals that had honestly come to fail, and drain X's allowance. X's own devices could then relay nothing for a day, the removal of the attacker included | **Yes.** `probe8 p1`: X proposed `set_role(Y, writer)`, and A made the change first. M replayed X's proposal to relay R 600 times over fresh sessions: R charged X 512 times and then refused at X's allowance. X's removal of M, from X's device, was then refused ("this peer's fleet reached its daily allowance"), and so was W's leave relayed by X | `link/src/engine.rs`: `Link::offer_from` and `Link::charge_origin`. An origin is charged at most once per proposal id a day, and a replay costs it nothing more. The origin table holds `(time, id)` and stays bounded, because an origin at its allowance is not checked again. `peer_charges` and `origin_charges` are separate tables, and the peer gate counts only charges the peer earned as a peer. `Charge::Origin { key, id }`. The refusal itself is not cached: every replay is checked again, so a proposal that holds later is kept and included | `engine/tests.rs`: `r8_1_replaying_a_failing_proposal_charges_its_origin_once`. It covers 600 replays, one charge, and X's removal of M and W's leave both relayed. Once Y is a reader again, X's proposal is kept and included. On the sequencer, 20 replays at a moving tip, each refused with a fresh signature, add one charge. An origin spent to its allowance by X's own failing proposals does not stop X's device relaying Y's leave. `r7_p3_...` now expects "origin reached" for M's own flood, where it expected "peer's fleet reached" |
| R8-2 | medium | Record `want` frames, and `heads` pages, counted against no budget. `Link::missing_for_authors` called `Store::range` with no `LIMIT`, so it loaded each author's whole feed before keeping 4,096 records, under the daemon-wide lock. Found while fixing it: records a peer pushes counted against no budget either, and each costs a signature check, duplicates included. An answer cut at 4,096 records ended with `synced`, and the asker never asked again, so an honest feed longer than 4,096 records stalled until the next session. The hourly quota's `COUNT` per received record scanned the author's whole feed | **Yes.** `probe8 p2`: one want for a 20,000-record feed took 125 ms, reading the whole feed for 4,096 records. 300 wants in one minute of one session were all answered: 7,515 MB of replies and 38.9 s of CPU. `p4`: the same 4,096 records pushed 20 times in a minute cost 11.9 s under the lock, about 0.4 s a push. The round-7 code stalls at 4,096 records (test above) | `link/src/store.rs`: `Store::range` takes a limit, and the SQL has `LIMIT`. Its bounds are clamped, because `u64::MAX as i64` was -1 and matched nothing. `Store::delivered_upto` writes the receipts of an ack in one statement, where `take_receipts` loaded the whole feed. There is an index on `records(author, received_at)`. `link/src/engine.rs`: `missing_for_authors` pages 64 rows at a time within a record limit and a byte budget, and reports whether the answer was cut short. `link/src/record.rs`: `Record::frame_cost`. `link/src/sync.rs`: `want`, `heads`, `synced` and `advert` count against `MAX_RECORD_FRAMES_PER_MIN` = 120 (`Session::rec_frame`). The record bytes a session sends in answers count against `RECORD_BYTES_PER_MIN` = 16 MiB a minute (`Session::answer_records`). Every answer ends with `synced { more }`. The asker asks again at once if the answer stored something, at its next `ping` if it was empty, and not at all if what came was refused (`Session::want`). The records a peer sends count against `RECORD_BYTES_IN_PER_MIN` = 32 MiB a minute, by `frame_cost`. Past that they are not looked at, and they are asked for again at the next ping | `engine/tests.rs`: `r8_2_wants_and_heads_pages_are_budgeted_per_session` (400 wants: at most 16 MiB of records and 120 frames, then the session ends; `heads` pages the same). `r8_2_honest_catch_up_of_a_large_feed_converges` (200 records of 100 KB, 27 MB, in 2 minutes; 5,000 small records in one session). `r8_2_a_store_range_reads_at_most_its_limit` (also the query plan of the quota's count). `r8_2_records_a_peer_sends_are_budgeted` |
| R8-3 | low | The evidence and other budgets were per session, and new sessions were not rated. A member that reconnected got a fresh budget each time | **Yes**, by the daemon test below with the fix off: a second session, a reconnect, took 30 more ACL frames after the first took 100 | `link/src/sync.rs`: `Budget` holds what a peer has spent this minute: ACL frames and evidence checks, ACL bytes sent, record frames, record bytes sent and received. It is `Session::budget`. `linkd/src/net.rs`: `run_session` hands each frame the budget of its `(link, peer)` (`Net::budget`) and keeps what it spent (`Net::keep_budget`). Concurrent and successive sessions of one device share one budget. `SESSION_STARTS_PER_MIN` = 10 new sync sessions per `(link, peer)` a minute, checked before any slot is taken (`LinkProto::accept`) | `linkd/src/net_tests.rs`: `r8_3_budgets_survive_a_reconnect_and_new_sessions_are_rated`, over real iroh endpoints. It covers 100 frames, a reconnect, 30 more and "too many ACL frames this minute", then 11 session starts and "too many new sync sessions" |
| R8-4 | low | `AclChain::screen` ran `settled_above`, an O(chain) scan that parses proposals, before any charge, on every frame whose signer had already raised an alarm | **Yes.** `r8_4_...` with the fix off: 40 frames, one at each other position of the alarmed signer's term, ran 41 scans. In time it is small on a chain without proposals. `probe8 p5`, on a 2,204-entry chain under the R7-5 rule: 0.082 ms a frame before, 0.040 ms after. The scan grows with the proposals the chain carries | `link/src/acl.rs`: `AclChain::settled_above` is `s < bound`. One bound per (signer, root, term) comes from one scan (`settled_bound`: each clause holds exactly when an entry with its property sits above `s`, and the bound is the highest such index). It is kept until the held tip changes, for at most 256 keys. `screen` takes the signer from the held entry without cloning it | `engine/tests.rs`: `r8_4_frames_about_an_alarmed_signer_scan_the_chain_once` (40 frames, one scan; the chain grows, one more). In tests, `settled_above` asserts its answer equals the round-7 scan (`settled_above_by_scan`) on every call |

### Decisions, and why

- **Charge once per proposal; remember no verdict.** The review offered two choices. One was to
  answer replays without charging the origin. The other was to charge the replaying peer instead.
  The second would punish an honest relay that resends what it holds queued at every session. So
  a replay is free for its origin, and is still checked: the refusal is computed again each time.
  Caching the refusal per tip would save that check, about 0.4 ms (a state clone; `p1`: 600
  replays in 251 ms). But a check also reads the clock (expiry, the day's allowance), so a cached
  verdict could pre-empt a proposal that would hold later. Charging is the only thing remembered,
  so the cache cannot refuse anything. The replay's check is paid from the replaying session's
  120 ACL frames a minute, which since R8-3 are shared across its reconnects.
- **Why the table of charged ids stays bounded.** Only the proposer can make another proposal of
  its origin, and only the invite's holder another join on it. An origin at its allowance is not
  checked, so it is charged no more. Each origin holds at most its allowance of ids, and each
  entry is dropped after a day. The origins are the chain's member roots and invites.
- **The peer gate counts only what the peer earned as a peer.** Round 7 counted the fleet's
  included proposals too, so an admin fleet busy with its own changes could not relay. Those
  proposals are the origin's business, and the origin gate counts them.
- **Record budgets, and their size.** There are 120 record-side frames a minute, like the ACL
  side. The answers to them are capped at 16 MiB a minute, about 1 GB an hour. The default hourly
  quota per author is 600 records, so it lets in less than that for any realistic record size. An
  honest backlog of 27 MB arrives in 2 minutes (test above). The cap on records a peer sends is
  twice that, so an honest peer's answers and its live pushes both fit. Live pushes of new records
  are not counted on the sending side.
- **`synced { more }` instead of a new frame.** A cut-short answer has to say so, or the asker
  cannot tell "complete, but I refused some" from "more to come". Asking again only after
  progress (as a gap already did) keeps a refused or over-quota batch from looping. Asking again
  at a ping after an empty answer is how the ACL side resumes (round 5), and it means a spent
  budget delays the asker but does not stall it. As a side effect, an honest feed longer than one
  pass (4,096 records) now arrives within one session. Before, it waited for the next session.
- **Budgets per (link, peer) in the daemon, plus a session-start rate.** Sharing the budget makes
  a reconnect worthless to an attacker: it starts where the last session stopped, and two
  concurrent sessions share one budget. The start rate (10 a minute) bounds what the budget does
  not cover: the handshake and the hello. It is higher than any honest dialer needs, since the
  dialer tries every 30 s with a backoff. The budget table holds only budgets of the current
  minute, of members.
- **The per-link lock is done** (about 90 lines, `linkd/src/daemon.rs: Held`, `with_link`,
  `held_links`). With round 8's budgets, one device can make a replica do a bounded amount of
  work under a link's lock each minute (`p3`: every record and ACL budget spent took 28 ms and
  44 ms of lock time in release). Nothing bounded how that added up across links. With a lock per
  link, a member of one link cannot slow another link's sessions or RPCs
  (`a_busy_link_does_not_hold_up_another`). No code holds two link locks at once, and none
  awaits a link's lock while it holds the map's. The map's lock is taken only to find or add a
  link: `adopt` holds it while it builds a new link, which nothing else can reach yet. What
  remains coupled:
  - Sessions of one link still run one frame at a time.
  - Calls that read every link (`peer_links`, which the inbound gates and the dialer use,
    `link.list` and `events.wait`) take each link's lock in turn, so each waits for the frame in
    progress on each link. With the budgets that is milliseconds.
  - Making `peer_links` lock-free would need a per-link snapshot of its devices, refreshed after
    every chain change. That is left as a follow-up.
- **The index on `records(author, received_at)`.** Every received record runs the hourly quota's
  `COUNT`, which read every record of its author. It made storing a 4,096-record catch-up take
  4.2 s in release, quadratic in the feed's length. With the index it takes 1.7 s (`p4`, first
  push).

### Probe results, before and after

`probe8-before` builds the probe crate against the round-7 head (`2ae025c1`, in a temporary
worktree). `probe8-after` builds it against this round. Both are release builds on this machine,
in the scratchpad.

| Probe | Before (round 7) | After (round 8) |
|---|---|---|
| `p1`: M replays X's honestly failing proposal to relay R 600 times, over fresh sessions | R charged X 512 times, then refused it at X's allowance. X's removal of M, sent by X's device, was refused at the peer's allowance. W's leave relayed by X was refused too | R checked all 600 replays and refused each, and charged X once. X's removal of M and W's leave relayed by X are both kept to relay |
| `p2`: one want for a 20,000-record feed of about 2 KB records | 4,096 records in 125 ms, reading the whole feed (31 µs a record) | 2,565 records (the 16 MiB budget) in 16 ms (6 µs a record) |
| `p2`: 300 wants in one minute of one session | All answered: 7,515 MB of replies, 38.9 s of CPU | 120 answered, 15.7 MB; then the session ends ("too many record frames this minute") |
| `p3`: lock time one device can cause in a minute, with every budget spent | Wants: 400 answered, 10,020 MB, 52.0 s. Proposals: 120 frames, 27 ms | Wants: 120 answered, 15.7 MB, 28 ms. Proposals: 120 frames, 44 ms |
| `p4`: the same 4,096 records pushed 20 times in one minute | 4.2 s to store the first push, then about 0.4 s for each duplicate push, without end: 11.9 s in all | 1.7 s to store (the index), 0.1 s for one duplicate push, then about 4 ms a push (not looked at, asked for again at the next ping): 1.9 s in all |
| `p5`: 199 frames about an alarmed signer, one per position of its old term, on a 2,204-entry chain | 16.3 ms (0.082 ms a frame), one scan each | 8.0 ms (0.040 ms a frame), one scan in all |

### Measurements

Release build, this machine.

| Shape | Round 7 | Round 8 |
|---|---|---|
| Origin charges from replays of one proposal | One per replay, up to the allowance (512 for an admin) | One |
| Record bytes a session sends in answers a minute | Unbounded (`p2`: 7.5 GB) | At most 16 MiB plus one record |
| Record frames a session takes a minute | Unbounded | 120 |
| Record bytes a session looks at from its peer a minute | Unbounded | At most 32 MiB plus one record |
| Rows read for one want | Every record of each author named | The records sent plus at most one page of 64 |
| Budgets after a reconnect | Fresh | Shared per (link, peer); at most 10 new sessions a minute |
| `settled_above` scans for 40 frames about an alarmed signer | 41 | 1 (until the chain changes) |
| Storing 4,096 received records | 4.2 s | 1.7 s |
| Property tests at 600 cases | 4 tests: 41.0 s | 4 tests: 40.9 s |

### Known trade-offs of round 8

These replace round 7's trade-offs 4 and 6. The others stand.

1. **A replay is free for its origin and still costs a check.** Each replay of a failing proposal
   is checked again (about 0.4 ms) and refused, within the replaying device's ACL frames. Only the
   first failure is charged. The charges are kept in memory, so a restarted daemon forgets them,
   as before.
2. **Records arrive at most 16 MiB a minute from each peer**, and a replica looks at most at
   32 MiB a minute of what one peer sends. A large backlog from one peer takes minutes. A peer
   whose live pushes exceed 32 MiB in a minute has the rest asked for again a minute later. Live
   pushes are not counted on the sending side.
3. **Budgets are per (link, peer), shared across sessions** (replaces round 7's trade-off 4). They
   are per device: a member with 8 devices has 8 budgets on each link, and a fleet in several
   links has a budget in each. New sessions are rated at 10 a minute per (link, peer).
4. **Each link has its own lock** (replaces round 7's trade-off 6; reworded in round 9). The
   sessions of one link still run one frame at a time. The lock is a std `Mutex`, taken on the
   daemon's async workers, so a session waiting for a busy link holds a worker while it waits.
   Once such sessions outnumber the workers, other links' sessions, the timers and the RPC socket
   wait too (R9-3, fixed in round 9). Calls that read every link (`peer_links`, `link.list`,
   `events.wait`) wait on each link for the frame in progress, and, since the lock is not fair,
   possibly for frames queued behind it.
5. **An answer to a `want` now ends with `synced`.** A `synced` without `more` changes nothing on
   the asker, which still runs its usual checks.

### Changes to round-7 rows

- **R7-3** (charging): the origin is charged once per proposal. Peer and origin charges are
  separate tables, and the peer gate no longer counts the fleet's included proposals.
- **R7-1** (evidence budget): the evidence-check charge is part of the shared `Budget`, so a
  reconnect no longer refills it (R8-3).
- **Round 7's decision on the daemon-wide lock** is reworded above, and the lock is replaced by
  one per link.

## Round 9

A ninth review read round 8. Its verdict was "ready for a human outside review": no critical or
high issue, and every regression shape of rounds 5 to 8 still holds. It raised two medium findings
(R9-1, R9-4), two low ones (R9-2, R9-3) and one observation, each with a probe (`probe9`: `r9`
`q1`, `q2`, `q3`, `q5`, `q6`, and `q4`). This round turned each into a permanent test, checked
that each test fails with its fix switched off, and fixed them. Their common thread: work that
honest peers need (catch-up) stopped when a batch made no progress, and work that dishonest peers
can cause (pings, empty frames, disputed heads) sat outside the budgets that round 8 added.

- **Base:** the round-8 head (`72a68838`) plus this round (local commits, `d9d5405d` to the docs
  commit). This table, like the ones above, names functions, not lines.
- **Sources:** the diff and its tests. `cargo test --workspace` passes:
  - `aurora-link`: 127 unit tests, five of them new. Four are property tests, also run once
    at 600 cases each in release (40.0 s together).
  - 5 vector tests.
  - `aurora-linkd`: 19 tests. 17 pass and 2 are ignored, both measurements (one is new, the `q4`
    shape). One new test checks the inbound gate against a busy link.

  The seven Python link test files (`tests/test_link_*.py` and `tests/test_accel_parity.py`) pass
  against the new wheel and debug daemon (177 tests). These are clean: `cargo fmt --check`,
  `cargo clippy --all-targets -- -D warnings`, `cargo deny check`, the fuzz smoke
  (`fuzz/smoke.sh 10`) and the docs checker. No Python file changed. `openrpc.json` and
  `rpc_types.py` are current (no RPC changed).
- **Formats changed:** none. No frame, store schema, vector or fuzz seed changed. `Admit` gains a
  variant (`OverQuota`), and `sync::Budget` is no longer `Copy`; both are crate APIs, not formats.
- **How the tests were checked to fail before the fix.** Each fix was switched off in turn in the
  working tree, and each failed its permanent test below:
  - R9-1: asking at once when the chain stores a waiting record ("B caught up within the
    session": 1 of 50); asking at the ping after the tip moved ("the ping after the tip moved asks
    again"); telling an author over quota from a gap (593 frames in 65 minutes, against fewer than
    250).
  - R9-4: answering each claim once (the same claims drew records again on every frame until the budget ran out); counting the records against the
    budget (89.8 MB in a minute).
  - R9-2: the frame budget (a million pings taken); the kept device sets (the set built on every
    frame).
  - R9-3: `block_in_place` (p99 33.7 ms on the quiet link; see below); `peer_links` reading the
    kept sets ("the inbound gate waited 1.0 s for a busy link"); refreshing them ("a device added
    is a peer at once").
  - The origin charge: remembering it for the proposal's life ("day 1: X was charged again for
    the same proposal").

### Round-9 findings

| Id | Severity | Finding | Reproduced | Fix (file: function) | Pinned by |
|---|---|---|---|---|---|
| R9-1 | medium (liveness) | Honest record catch-up stalled for the whole life of a session when a batch made no progress, and pings kept that session open, so the dialer never redialed. Two triggers. `Admit::Pending` keeps one record per author, so the rest came back as gaps, and nothing asked for them once the chain arrived: `retry_pending` stored the waiting record but sent no `want`. And the hourly quota: a backlog above `rate_per_hour` got a gap at record 601, and nothing ever asked again | **Yes.** `q1`: B lacked one membership change; after a 10-minute live session B held 1 of A's 50 records, and the rest came only with a reconnect. `q6`: a 1,000-record backlog under the default policy; after a 3-hour live session B held 600 | `link/src/sync.rs`, `Session::on_frame`. In the `acl` arm, records that `retry_pending` stores make us ask for the rest at once. In the `records` arm, records that wait note our tip (`rec_wait_tip`), and the first `ping` after the tip moved asks again (the chain may come through another session). A gap that nothing in the answer explains asks at the next `ping` (`rec_retry`), one bounded ask. Authors whose record waited, was over quota or was refused are noted per answer (`rec_blocked`, capped), so their later records are not mistaken for such gaps. `link/src/engine.rs`: `Link::receive` returns `Admit::OverQuota { until }`, with `until` from `store.rs: Store::quota_frees_at` (the index). The first `ping` from then asks again (`rec_quota_at`). A `ping` asks only when no want is outstanding | `engine/tests.rs`: `r9_1_records_written_at_chain_positions_the_asker_lacks_arrive_in_one_session` (the `q1` shape, default policy: 50 of 50 in one session; then the chain through another session, where the ping asks only after the tip moved). `r9_1_a_backlog_over_the_hourly_quota_arrives_once_the_quota_admits_it` (the `q6` shape, default policy: 1,000 records within one 65-minute session, in fewer than 250 frames) |
| R9-4 | medium | The records `conflicts` sends for heads the peer names with another id counted against no budget. A head claim needs no signature, so any member could name every author's head with a made-up id, in every record frame | **Yes.** `q5`: 8 feeds of one 256 KiB record. 120 `want` frames of 1,218 B in one minute drew 960 records, 336.6 MB: 20.1x the 16 MiB budget, about 2,300x the bytes sent, and 467 ms under the lock | `link/src/sync.rs`: `conflicts` is now `Session::conflicts`. The records it sends count against `rec_sent`, the 16 MiB a minute, and none is sent once it is spent. Each claim (author, seq, claimed id) is answered at most once a minute, kept in `Budget::conflicts`, so it carries across sessions. At most `MAX_CONFLICTS_PER_MIN` = 256 claims a minute, and only ids of 64 characters are kept | `engine/tests.rs`: `r9_4_records_sent_for_made_up_head_ids_are_budgeted_and_sent_once`. 100 frames with the same claims draw 8 records, and a reconnect with the shared budget draws none. Ever new made-up ids draw at most 16 MiB plus one record. Nobody is frozen |
| R9-2 | low | `ping` frames, and `records` frames that are empty or cut entirely by the received-bytes budget, counted against no budget. Each built the set of every device of the link to check membership | **Yes.** `q2`: a million pings in one minute (link of 23 devices) were all taken, 4.1 s under the lock; a million empty `records` frames, 2.1 s. `q3`: four ping-flooding sessions took 79,319 pings in 2 s, and an honest session's wants on that link fell from 8,781 to 5,541 | `link/src/sync.rs`: every frame counts against `MAX_FRAMES_PER_MIN` = 2,400 per (link, peer), checked first, in `Budget::frames`. `may_sync` and `may_sync_acl` read `link/src/acl.rs: AclChain::sync_devices` and `held_sync_devices`, sets built once per held tip, entry count, halt and view (`SyncCache`) | `engine/tests.rs`: `r9_2_every_frame_counts_and_membership_is_a_lookup`. Pings, then empty `records` frames: 2,400 taken, then "too many frames this minute"; a reconnect with the shared budget is refused; the next minute takes frames. At most one set is built per run of frames, and a removal takes effect at the next frame |
| R9-3 | low | The per-link lock is a std `Mutex`, taken on tokio workers. Sessions that waited for a busy link each held a worker, so 16 of them stalled other links and the timers. `peer_links` (the inbound gates of every protocol, and the dialer) took each link's lock in turn | **Yes.** `q4`: 4 workers, 16 sessions busy on link X; a frame on quiet link Y waited p99 27.9 ms, max 35.6 ms. Through the daemon's own `with_link`, with the fix off: p99 33.7 ms, max 35.1 ms, and 200 rounds with a 10 ms sleep took 35.7 s instead of 2.3 s: the timers stalled too | `linkd/src/daemon.rs`: `LinkCell`. `LinkCell::with` runs the wait and the body in `block_in_place` when on a multi-threaded runtime (`off_worker`), and inline elsewhere. Each link keeps a copy of its sync device sets, refreshed after any body that moved them (`Arc::ptr_eq`), and `links_by` (`peer_links`, `record_peer_links`) reads those copies without any link's lock. Every site that took a link's lock directly now goes through `LinkCell::with` | `linkd/src/net_tests.rs`: `r9_3_peer_links_takes_no_link_lock_and_follows_the_chain` (the gate answers in well under 300 ms while a link is held for 1 s; a device added or removed shows at once). `r9_3_a_busy_link_holds_up_no_worker`, the `q4` shape through `with_link`, ignored as a measurement: p99 0.17 ms, max 0.27 ms, with 16 sessions busy, and the 200 rounds take 2.3 s |
| Observation | — | An origin's charge for a proposal was remembered for a day, while a proposal lives 7 days, so one failing proposal could be charged to its origin again once a day | **Yes**, by the test below with the fix off (charged again on day 1) | `link/src/engine.rs`: `Link::charge_origin` keeps `(time, id, until)`, with `until` the proposal's `expires` (capped at 7 days and the clock skew ahead). A charge counts against the allowance for a day, and is remembered until `until`, so a replay on any later day of the proposal's life is free | `engine/tests.rs`: `r9_an_origin_is_charged_once_for_a_proposal_over_its_whole_life` (replays on each of days 1 to 6, each checked and refused, none charged) |

### Decisions, and why

- **R9-1: ask again when it can help, not on every ping.** The review suggested setting
  `rec_retry` whenever records wait. A record can name a chain position this replica never
  reaches (its author may name any position). Asking on every ping would then fetch the same
  batch every 45 s for the life of the session. So records that wait are asked for again only
  once our tip has moved: at once when the chain arrives in this session, at the next ping when
  it came through another. Refused records are still never asked for again.
- **R9-1: over quota is not a gap.** `Admit::OverQuota { until }` says when the quota admits
  another record of that author, from the `records(author, received_at)` index. Round 8 treated
  it as a gap after progress, and asked at once for a batch that was refused again. Now nothing
  is asked until `until`, and the first ping after it asks once. An honest backlog over the quota
  arrives an hour at a time within one session.
- **R9-1: which gaps are real.** A gap behind a record that waited, was over quota or was refused
  is explained, and is not asked for. Those authors are noted until our next want (`rec_blocked`),
  because an answer spans several frames. Any other gap, for example records pushed live past
  ones we lack, is asked for at the next ping, once.
- **R9-4: once per claim, in the shared budget.** The records `conflicts` sends now spend the same
  16 MiB a minute as any answer. A peer that spends it on claims delays only its own catch-up.
  Each claim is answered once a minute: an honest peer that sees our record once has what it
  needs to freeze the author. Ids that are not 64 characters name no record and are not kept,
  so the memory per peer is bounded (256 claims).
- **R9-2: a frame budget, and its size.** 2,400 frames a minute per (link, peer) is counted
  before any other work. A link of the default 16 members has at most 128 devices; each writing
  at the default quota of 600 records an hour is about 1,300 live pushes a minute. The budget
  leaves room for twice that, plus the ACL and record budgets. Past it, the session ends like any
  over-budget session, and the next minute's session takes up where it stopped.
- **R9-2: the device sets are kept in the chain.** They are rebuilt only when the held tip, the
  number of entries, the halt or the narrowed view changes. They sit behind a small lock in
  `AclChain`, so a reader with `&Link` can fill them. The same sets now feed the daemon's
  `peer_links`.
- **R9-3: `block_in_place`, not a tokio mutex or `spawn_blocking`.** `with_link` is synchronous
  and has about 40 callers, many of them synchronous RPC handlers. A tokio mutex would make all of
  them async. `spawn_blocking` needs `'static` closures, but session bodies borrow the session's
  state. `block_in_place` keeps every call as it is: it moves the worker's other tasks to another
  thread before it blocks. Outside a multi-threaded runtime (tests, one-shot commands) it runs the
  body inline. `peer_links` no longer locks at all. It was the remaining follow-up from round 8.
- **The origin charge lives as long as the proposal.** The charge still counts against the
  origin's allowance for one day, as before. Only the memory that it was paid lasts until the
  proposal's `expires`, capped at 7 days ahead. Each origin then holds at most its allowance of
  ids for each day a proposal lives.

### Probe results, before and after

`probe9-*.txt` are the review's runs against the round-8 head. `probe9-after-*.txt` are this
round's, built with the same probe sources against the round-9 code (release, this machine, in
the scratchpad). The regression shapes `r5` to `r7` were also run against the round-8 head
(`probe9-before-r5.txt` to `r7`, built in a temporary worktree).

| Probe | Before (round 8) | After (round 9) |
|---|---|---|
| `q1`: catch-up of 50 records written at a chain position B lacks, one 10-minute live session | B holds 1 of 50 (34 frames); the rest came only with a reconnect | B holds 50 of 50 (37 frames) |
| `q6`: a 1,000-record backlog at the default quota, one 3-hour live session | B holds 600 of 1,000 | B holds 1,000 of 1,000 (494 frames) |
| `q2`: a million pings, then a million empty `records` frames, in one minute | All taken: 4.07 s and 2.12 s under the lock | 2,399 pings taken after the hello, then "too many frames this minute". The empty frames, in the same session and minute, are refused at once |
| `q3`: ping-flooding sessions against an honest session's wants on one link | 4 flooders: 79,319 pings in 2 s; 5,541 honest wants, p99 8.31 ms (alone: 8,781, p99 7.18 ms) | Each flooding session ended at 2,400 frames, within the 200 ms before the measurement: 0 pings in the 2 s; 9,021 honest wants, p99 6.90 ms (alone: 9,142, p99 6.93 ms) |
| `q5`: 120 `want` frames a minute naming 8 heads with a made-up id | 960 records, 336.6 MB (20.1x the budget), 467 ms under the lock | 8 records, 3.0 MB (0.2x), 11 ms; then "too many record frames this minute" |
| `q4`: 4 workers, 16 sessions busy on link X, a frame on quiet link Y | p99 27.9 ms, max 35.6 ms | The probe takes its own std `Mutex` on the workers, not `with_link`, so it cannot see the fix: p99 13.2 ms, max 13.6 ms. The same shape through the daemon's `with_link` (`r9_3_a_busy_link_holds_up_no_worker`): p99 33.7 ms and 35.7 s for 200 rounds of 10 ms with the fix off; 0.17 ms and 2.3 s with it |

### Regression shapes after round 9

Every regression shape holds. The `r5` to `r8` outputs after this round match the round-8 runs
line for line, apart from timings.

| Shape | After round 9 |
|---|---|
| `r5 P1`, `P1b`: a removed member acts on its old base, or a fresh one | Refused: "author is not an active member device"; the joiners stay active |
| `r5 P2`, `P5`: a plain admin's spare device removes or lowers a member the owner promoted | Refused; M stays an admin |
| `r5 P3`: a plain admin's decline signed before the owner's accept | Refused: "no such pending join"; N active |
| `r5 P4`: an honest device offline two days acts before it syncs | Kept; the same tip after it syncs |
| `r5 P6`: `acl_want` amplification | A hello sends no ACL; 100 whole-range wants a minute stay at 8 MiB plus one entry; a range want gets exactly that range |
| `r6 p1`: an ex-sequencer's equivocation at an old position | No halt; the removed device's records refused; the takeover works |
| `r6 p2`: a non-sequencer admin forges a refusal | Not taken (`Ok(false)`); X is removed |
| `r6 p3`: a 222 KB rotation entry | Taken by another replica; both at the same tip after a session |
| `r7 p1`: an evidence flood from an ex-sequencer | One evidence row, one alarm, no halt; junk evidence ends the session at its check budget |
| `r7 p2`: a device added past a halt's prefix | Trades the chain's frames, and takes the takeover |
| `r7 p3`: junk joins on a used invite | Nothing relayed; X's removal of M is included |
| `r7 p4`: a halt from next-position evidence | Survives a restart |
| `r8 p1`: 600 replays of one failing proposal | Checked and refused 600 times, charged once; X's removal of M and W's leave are kept |
| `r8 p2`, `p3`: wants over a 20,000-record feed | 120 answered, 15.7 MB; then "too many record frames this minute" |
| `r8 p4`: the same 4,096 records pushed 20 times | 1.7 s to store, then about 4 ms a push |
| `r8 p5`: 199 frames about an alarmed signer | 0 checks, 6.8 ms |

### Measurements

Release build, this machine.

| Shape | Round 8 | Round 9 |
|---|---|---|
| Records B holds after one live session, `q1` (50 behind a chain change) | 1 | 50 |
| Records B holds after one live session, `q6` (1,000, default quota) | 600 | 1,000 |
| Frames one peer may send on a link a minute | Unbounded (`q2`: a million) | 2,400 |
| Device sets built for a run of frames | One per frame | One per held tip |
| Record bytes sent for made-up head ids a minute | Unbounded (`q5`: 336.6 MB) | Within the 16 MiB record budget, each claim once |
| A quiet link's frame, 16 sessions busy on another link, 4 workers (p99, through `with_link`) | 33.7 ms | 0.17 ms |
| The inbound gate while another link is held for 1 s | Waits 1.0 s | Does not wait |
| Origin charges for one failing proposal replayed daily over its life | Up to 7 | 1 |
| Property tests at 600 cases | 4 tests: 40.9 s | 4 tests: 40.0 s |

### Known trade-offs of round 9

These add to round 8's. Round 8's trade-off 4 is reworded above. The others stand.

1. **A backlog over an author's hourly quota arrives an hour at a time.** In between, the session
   pings and asks for nothing from that author.
2. **Records that wait for a chain position are asked for again only once the tip moves.** A
   record that names a position this replica never reaches is not asked for again in that
   session.
3. **2,400 frames a minute per (link, peer).** A link whose devices push more than that to one
   peer, for example more than about 240 devices writing at the default quota, has its session
   ended for the rest of the minute. The next minute's session resumes, and what was missed is
   asked for again.
4. **Records sent for disputed heads share the record budget with answers.** A peer that spends
   it on claims delays only its own catch-up. An honest claim is answered once a minute.
5. **`block_in_place` costs a thread handoff** when it runs on a worker, microseconds per frame.
   `link.list` and `events.wait` still take each link's lock in turn, now off the workers.
6. **The origin charge table lives up to 7 days.** Each origin holds at most its allowance of
   ids for each day a proposal lives. It is still kept in memory, so a restarted daemon forgets
   it.

### Changes to round-8 rows

- **R8-1** (charging once per proposal): the charge is remembered until the proposal expires, not
  for a day.
- **R8-2** (record budgets): records sent for disputed heads count against the 16 MiB a minute
  (R9-4); an answer that made no progress is asked for again when that can help (R9-1).
- **Round 8's decision on the per-link lock** held only while workers were free: a session
  waiting for a busy link held a worker. R9-3 moves the wait and the work off the workers, and
  `peer_links` no longer locks any link. Round 8's trade-off 4 is reworded above.
