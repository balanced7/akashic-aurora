use super::*;
use crate::identity::{new_phrase, root_from_phrase};

const T0: u64 = 10_000;

/// One fleet: a root and its devices.
struct Fleet {
    root: SigningKey,
    devs: Vec<Device>,
}

impl Fleet {
    fn new(n: usize) -> Self {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let devs = (0..n)
            .map(|i| Device::create(&root, &format!("d{i}"), false, T0 - 10).unwrap())
            .collect();
        Self { root, devs }
    }
    /// A fleet whose `n` devices all carry X-Wing keys (the largest wraps).
    fn xwing(n: usize) -> Self {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let devs = (0..n)
            .map(|i| Device::create(&root, &format!("x{i}"), true, T0 - 10).unwrap())
            .collect();
        Self { root, devs }
    }
    fn d(&self, i: usize) -> &Device {
        &self.devs[i]
    }
    fn root_hex(&self) -> String {
        hex(&crypto::public_of(&self.root))
    }
}

fn zero(_: &str) -> u64 {
    0
}

/// A link owned by a fresh fleet of `n` devices; device 0 sequences it.
fn link(n: usize) -> (AclChain, Fleet) {
    let a = Fleet::new(n);
    let (mut chain, _) = genesis(a.d(0), "p", "owner", Policy::default(), T0).unwrap();
    for i in 1..n {
        let s = chain.state().clone();
        let key = s.read_key(0, &a.d(0).id_hex(), &a.d(0).kem).unwrap();
        let mut tmp = s.clone();
        tmp.devices
            .insert(a.d(i).id_hex(), DeviceState::new(a.d(i).cert.clone(), a.root_hex()));
        let wraps = tmp.make_wraps(&key.0, s.epoch, &[a.d(i).id_hex()].into()).unwrap();
        own(
            &mut chain,
            a.d(0),
            Op::AddDevice(AddDevice {
                cert: a.d(i).cert.clone(),
                wraps,
            }),
            T0,
        );
    }
    (chain, a)
}

/// The sequencer's own action.
fn own(chain: &mut AclChain, seq: &Device, op: Op, ts: u64) -> Entry {
    chain.append(seq, Some(op), Vec::new(), ts, &zero).unwrap()
}

/// The sequencer includes `p`.
fn include(chain: &mut AclChain, seq: &Device, p: &Proposal, ts: u64) -> Result<Entry> {
    chain.append(seq, None, vec![p.clone()], ts, &zero)
}

fn invite_op(secret: &[u8; 32], role: Role, approval: bool, ts: u64) -> Op {
    Op::Invite(Invite {
        invite: hex(&crypto::public_of(&invite_key(secret))),
        role,
        expires: ts + DEFAULT_INVITE_TTL_S,
        single_use: true,
        approval,
    })
}

/// The sequencer invites; returns the ticket.
fn invite(chain: &mut AclChain, seq: &Device, role: Role, approval: bool, ts: u64) -> InviteTicket {
    let secret = crypto::random32();
    let e = own(chain, seq, invite_op(&secret, role, approval, ts), ts);
    InviteTicket {
        secret,
        entry: e.hash().unwrap(),
    }
}

fn base_of(chain: &AclChain) -> Base {
    let t = chain.tip();
    Base {
        term: t.term,
        seq: t.seq,
    }
}

/// `dev` joins through `ticket`; the sequencer includes it. Returns the join id.
fn join(chain: &mut AclChain, seq: &Device, dev: &Device, ticket: &InviteTicket, label: &str, ts: u64) -> String {
    let p = make_join(dev, ticket, chain.link_id(), base_of(chain), label, ts + PROPOSAL_TTL_S).unwrap();
    include(chain, seq, &p, ts).unwrap();
    p.id().unwrap()
}

fn accept(chain: &mut AclChain, seq: &Device, join: &str, ts: u64) {
    let s = chain.state().clone();
    let root = &s.pending_joins[join];
    let m = &s.members[root];
    let devices = if m.role.reads() {
        m.devices.clone()
    } else {
        BTreeSet::new()
    };
    let key = s.read_key(s.epoch, &seq.id_hex(), &seq.kem).unwrap();
    let wraps = s.make_wraps(&key.0, s.epoch, &devices).unwrap();
    own(
        chain,
        seq,
        Op::Accept(Accept {
            join: join.to_owned(),
            wraps,
        }),
        ts,
    );
}

/// A new member fleet of `n` devices with `role`, joined, accepted and with every device added.
fn admit(chain: &mut AclChain, seq: &Device, role: Role, n: usize, ts: u64) -> Fleet {
    admit_fleet(chain, seq, role, Fleet::new(n), ts)
}

/// `f` joins with `role`, is accepted, and has every device of it added.
fn admit_fleet(chain: &mut AclChain, seq: &Device, role: Role, f: Fleet, ts: u64) -> Fleet {
    let n = f.devs.len();
    let t = invite(chain, seq, role, false, ts);
    let j = join(chain, seq, f.d(0), &t, &format!("m{}", &f.root_hex()[..6]), ts + 1);
    if chain.state().pending_joins.contains_key(&j) {
        accept(chain, seq, &j, ts + 2);
    }
    for i in 1..n {
        let s = chain.state().clone();
        let wraps = if role.reads() {
            let key = s.read_key(s.epoch, &seq.id_hex(), &seq.kem).unwrap();
            let mut tmp = s.clone();
            tmp.devices
                .insert(f.d(i).id_hex(), DeviceState::new(f.d(i).cert.clone(), f.root_hex()));
            tmp.make_wraps(&key.0, s.epoch, &[f.d(i).id_hex()].into()).unwrap()
        } else {
            vec![]
        };
        own(
            chain,
            seq,
            Op::AddDevice(AddDevice {
                cert: f.d(i).cert.clone(),
                wraps,
            }),
            ts + 3,
        );
    }
    f
}

fn active(s: &AclState, root: &str) -> bool {
    s.members.get(root).is_some_and(|m| !m.removed && !m.pending)
}

/// A removal of `root` by `by`, rotating to the readers left (when `by` holds the key).
fn remove_member_op(s: &AclState, by: &Device, root: &str) -> Op {
    let m = &s.members[root];
    let mut keyed = s.keyed_devices();
    keyed.retain(|d| !m.devices.contains(d));
    let rotate = s
        .read_key(s.epoch, &by.id_hex(), &by.kem)
        .ok()
        .map(|k| s.new_key_change(&k, &keyed).unwrap().0);
    Op::RemoveMember(RemoveMember {
        member: root.to_owned(),
        rotate,
    })
}

/// A second replica holding exactly `chain`'s entries.
fn replica(chain: &AclChain) -> AclChain {
    let mut r = AclChain::new();
    let got = r.insert(chain.all(), None);
    assert!(got.refused.is_none(), "{:?}", got.refused);
    r
}

fn summary(s: &AclState) -> String {
    let members: Vec<String> = s
        .members
        .values()
        .map(|m| format!("{}:{:?}:{}:{}:{:?}", m.root, m.role, m.pending, m.removed, m.devices))
        .collect();
    let devices: Vec<String> = s.devices.iter().map(|(d, x)| format!("{d}:{:?}", x.cut)).collect();
    format!(
        "{}|{}|{}|{:?}|{:?}|{}|{:?}|{}|{:?}",
        s.seq,
        s.term,
        s.tip,
        members,
        devices,
        s.epoch,
        s.key_ids,
        s.rotation_due,
        s.invites.keys().collect::<Vec<_>>()
    )
}

#[test]
fn genesis_starts_term_one_sequenced_by_the_owners_device() {
    let (chain, a) = link(1);
    let s = chain.state();
    assert_eq!((s.term, s.seq), (1, 0));
    assert_eq!(s.link_id, chain.hash_at(0).unwrap());
    assert_eq!(s.sequencer, a.d(0).id_hex());
    assert_eq!(s.next_sequencer(), (a.d(0).id_hex(), 1));
    let e = chain.entry(0).unwrap();
    assert!(e.prev.is_empty() && e.link.is_empty());
    assert!(replica(&chain).state().members[&a.root_hex()].role == Role::Owner);
}

#[test]
fn entries_follow_one_another_and_only_the_sequencer_signs() {
    let (mut chain, a) = link(2);
    let b = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    for w in chain.all().windows(2) {
        assert_eq!(w[1].seq, w[0].seq + 1);
        assert_eq!(w[1].prev, w[0].hash().unwrap());
        assert!(w[1].ts >= w[0].ts);
    }
    // Nobody but the sequencer appends: an admin's own append is refused.
    let err = chain
        .append(
            b.d(0),
            Some(invite_op(&[1; 32], Role::Writer, false, T0 + 20)),
            vec![],
            T0 + 20,
            &zero,
        )
        .unwrap_err();
    assert!(err.to_string().contains("does not sequence"), "{err}");
    // Not even the owner's other device.
    assert!(
        chain
            .append(
                a.d(1),
                Some(invite_op(&[1; 32], Role::Writer, false, T0 + 20)),
                vec![],
                T0 + 20,
                &zero
            )
            .is_err()
    );
    // An entry another device signs at the next position is refused by every replica.
    let s = chain.state().clone();
    let forged = Entry::sign(
        b.d(0),
        &s.link_id,
        s.term,
        s.seq + 1,
        &s.tip,
        T0 + 20,
        Some(invite_op(&[2; 32], Role::Writer, false, T0 + 20)),
        vec![],
        BTreeMap::new(),
    )
    .unwrap();
    let r = chain.insert(vec![forged], None);
    assert_eq!(r.added, 0);
    assert!(r.refused.unwrap().contains("sequencer"));
}

#[test]
fn a_replica_refuses_entries_dated_ahead_of_its_clock_or_before_the_last() {
    let (mut chain, a) = link(1);
    own(
        &mut chain,
        a.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 5),
        T0 + 5,
    );
    let mut ahead = chain.clone();
    let e = own(
        &mut ahead,
        a.d(0),
        invite_op(&[2; 32], Role::Writer, false, T0 + 5000),
        T0 + 5000,
    );
    let mut r = replica(&chain);
    let got = r.insert(vec![e.clone()], Some(T0 + 5000 - MAX_FUTURE_SKEW_S - 1));
    assert!(got.refused.unwrap().contains("future"));
    assert_eq!(r.insert(vec![e], Some(T0 + 5000)).added, 1);
    // `append` never dates an entry before the last; a forged one is refused.
    let s = chain.state().clone();
    let back = Entry::sign(
        a.d(0),
        &s.link_id,
        s.term,
        s.seq + 1,
        &s.tip,
        T0 + 1,
        Some(invite_op(&[3; 32], Role::Writer, false, T0 + 1)),
        vec![],
        BTreeMap::new(),
    )
    .unwrap();
    assert!(chain.insert(vec![back], None).refused.unwrap().contains("dated before"));
}

#[test]
fn a_gap_asks_for_what_is_missing_and_any_arrival_order_gives_one_state() {
    let (mut chain, a) = link(2);
    admit(&mut chain, a.d(0), Role::Writer, 2, T0 + 10);
    admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 20);
    let all = chain.all();
    let mut r = AclChain::new();
    r.insert(all[..3].to_vec(), None);
    let got = r.insert(all[6..].to_vec(), None);
    assert_eq!((got.added, got.need_from), (0, Some(2)));
    let mut rev = all.clone();
    rev.reverse();
    let mut r2 = AclChain::new();
    assert_eq!(r2.insert(rev, None).added, all.len());
    assert_eq!(summary(r2.state()), summary(chain.state()));
}

/// The spec's "a proposal checked against a state that changed since its base".
#[test]
fn a_proposal_is_checked_against_the_chain_as_it_stands_when_it_is_appended() {
    let (mut chain, a) = link(1);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    let m = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    // X proposes to remove M; the proposal is valid where X stood (its base).
    let op = remove_member_op(chain.state(), x.d(0), &m.root_hex());
    let p = chain.propose(x.d(0), &op).unwrap();
    chain.check_proposal(&p, T0 + 30).unwrap();
    // Before it reaches the sequencer, the owner removes X.
    let op = remove_member_op(chain.state(), a.d(0), &x.root_hex());
    own(&mut chain, a.d(0), op, T0 + 40);
    let err = include(&mut chain, a.d(0), &p, T0 + 50).unwrap_err();
    assert!(err.to_string().contains("not an active member"), "{err}");
    assert!(active(chain.state(), &m.root_hex()));
    // And a proposal whose key change was built before a rotation names the wrong epoch.
    let y = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 60);
    let stale = remove_member_op(chain.state(), y.d(0), &m.root_hex());
    let p = chain.propose(y.d(0), &stale).unwrap();
    let s = chain.state().clone();
    let k = s.read_key(s.epoch, &a.d(0).id_hex(), &a.d(0).kem).unwrap();
    own(
        &mut chain,
        a.d(0),
        Op::RotateKey(s.new_key_change(&k, &s.keyed_devices()).unwrap().0),
        T0 + 70,
    );
    let err = include(&mut chain, a.d(0), &p, T0 + 80).unwrap_err();
    assert!(err.to_string().contains("epoch"), "{err}");
}

/// Round-5 probe P1 (R5-1): a dormant writer's backdated "witness" dated after an invite's
/// expiry evicted an old honest join and undid the attacker's own removal. In a chain the
/// writer can only propose; its proposal is checked now, where it was removed.
#[test]
fn r5_p1_a_removed_dormant_device_cannot_backdate_a_witness() {
    let (mut chain, a) = link(1);
    let b = admit(&mut chain, a.d(0), Role::Writer, 2, T0 + 4);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    // B0's add_device of B1 is a proposal on its old horizon (signed now, before its removal).
    let s = chain.state().clone();
    let witness = chain
        .propose(
            b.d(0),
            &Op::RemoveDevice(RemoveDevice {
                device: b.d(1).id_hex(),
                rotate: None,
            }),
        )
        .unwrap();
    // X (admin) removes B, through the sequencer.
    let op = remove_member_op(&s, x.d(0), &b.root_hex());
    let p = chain.propose(x.d(0), &op).unwrap();
    include(&mut chain, a.d(0), &p, T0 + 20).unwrap();
    // A day and more later the witness reaches the sequencer: B is not a member any more.
    let late = T0 + 10 + DEFAULT_INVITE_TTL_S + 5;
    let err = include(&mut chain, a.d(0), &witness, late).unwrap_err();
    assert!(err.to_string().contains("not an active member"), "{err}");
    let s = chain.state();
    assert!(active(s, &x.root_hex()), "the honest join stands");
    assert!(s.members[&b.root_hex()].removed, "the removal stands");
    // A forged entry in B's name at an old position is not the sequencer's: refused.
    let old = chain.entry(5).unwrap().clone();
    let forged = Entry::sign(
        b.d(0),
        &old.link,
        old.term,
        old.seq,
        &old.prev,
        late,
        old.body.clone(),
        vec![],
        BTreeMap::new(),
    )
    .unwrap();
    let r = chain.insert(vec![forged], None);
    assert_eq!(r.added, 0);
    assert!(!r.equivocation, "only the term's sequencer can equivocate");
    assert!(chain.halt().is_none());
}

/// Round-5 probe P1b: a member removed long ago, with a self-renewed certificate, signs a leave
/// 200 days later on its old horizon. Its proposal has expired, and it is not a member.
#[test]
fn r5_p1b_a_long_removed_member_cannot_act_on_its_old_horizon() {
    let (mut chain, a) = link(1);
    let mut b = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 4);
    let horizon = base_of(&chain);
    let op = remove_member_op(chain.state(), a.d(0), &b.root_hex());
    own(&mut chain, a.d(0), op, T0 + 30);
    let mut ys = vec![];
    for k in 0..3 {
        ys.push(admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 100 + 10 * k));
    }
    // Two months later (the probe used 200 days and a renewed certificate; the owner's own
    // certificate would need renewing too, which changes nothing here).
    let late = T0 + 60 * 86_400;
    let root = b.root.clone();
    b.devs[0].renew(&root, late - 10).unwrap();
    let leave = Proposal::sign(
        b.d(0),
        chain.link_id(),
        &Op::RemoveMember(RemoveMember {
            member: b.root_hex(),
            rotate: None,
        }),
        horizon,
        T0 + PROPOSAL_TTL_S,
    )
    .unwrap();
    let err = include(&mut chain, a.d(0), &leave, late).unwrap_err();
    assert!(err.to_string().contains("expired"), "{err}");
    // On a fresh base it is still not a member.
    let fresh = chain
        .propose_at(
            b.d(0),
            &Op::RemoveMember(RemoveMember {
                member: b.root_hex(),
                rotate: None,
            }),
            late,
        )
        .unwrap();
    let err = include(&mut chain, a.d(0), &fresh, late).unwrap_err();
    assert!(err.to_string().contains("not an active member"), "{err}");
    assert!(ys.iter().all(|y| active(chain.state(), &y.root_hex())));
}

/// Round-5 probe P2 (R5-2): a plain admin's spare device backdated the removal of a member the
/// owner had since promoted to admin. Checked now, only the owner removes an admin.
#[test]
fn r5_p2_a_plain_admin_cannot_remove_an_admin_the_owner_promoted() {
    let (mut chain, a) = link(1);
    let m = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 4);
    let x = admit(&mut chain, a.d(0), Role::Admin, 2, T0 + 10);
    let horizon_op = remove_member_op(chain.state(), x.d(1), &m.root_hex());
    let p = chain.propose(x.d(1), &horizon_op).unwrap();
    own(
        &mut chain,
        a.d(0),
        Op::SetRole(SetRole {
            member: m.root_hex(),
            role: Role::Admin,
            wraps: vec![],
            rotate: None,
        }),
        T0 + 1000,
    );
    let err = include(&mut chain, a.d(0), &p, T0 + 2000).unwrap_err();
    assert!(err.to_string().contains("only the owner may remove an admin"), "{err}");
    assert_eq!(chain.state().members[&m.root_hex()].role, Role::Admin);
}

/// Round-5 probe P3: a plain admin's decline, signed before the owner's accept, arrives later.
/// There is no pending join to decline any more.
#[test]
fn r5_p3_a_decline_after_the_accept_is_refused() {
    let (mut chain, a) = link(1);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    let n = Fleet::new(1);
    let t = invite(&mut chain, a.d(0), Role::Writer, true, T0 + 20);
    let jn = join(&mut chain, a.d(0), n.d(0), &t, "n", T0 + 21);
    let decline = chain
        .propose(x.d(0), &Op::Decline(Decline { join: jn.clone() }))
        .unwrap();
    accept(&mut chain, a.d(0), &jn, T0 + 22);
    own(
        &mut chain,
        a.d(0),
        Op::SetRole(SetRole {
            member: n.root_hex(),
            role: Role::Admin,
            wraps: vec![],
            rotate: None,
        }),
        T0 + 5000,
    );
    let err = include(&mut chain, a.d(0), &decline, T0 + 100_000).unwrap_err();
    assert!(err.to_string().contains("no such pending join"), "{err}");
    assert!(active(chain.state(), &n.root_hex()));
    assert_eq!(chain.state().members[&n.root_hex()].role, Role::Admin);
}

/// Round-5 probe P4: no attacker; a device offline longer than an invite's lifetime acts before
/// it syncs. Its proposal lands after the join, which nothing can evict.
#[test]
fn r5_p4_an_honest_offline_device_evicts_nobody() {
    let (mut chain, a) = link(2);
    let offline = replica(&chain);
    let y = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 10);
    // A1 comes back two days later and proposes an invite on its stale base.
    let p = offline
        .propose(a.d(1), &invite_op(&[5; 32], Role::Writer, false, T0 + 2 * 86_400))
        .unwrap();
    include(&mut chain, a.d(0), &p, T0 + 2 * 86_400).unwrap();
    let mut back = offline;
    assert_eq!(back.insert(chain.all(), None).refused, None);
    for c in [&chain, &back] {
        assert!(active(c.state(), &y.root_hex()));
    }
    assert_eq!(summary(back.state()), summary(chain.state()));
}

/// Round-5 probe P5: a plain admin's lower role change of a member the owner promoted. Changing
/// an admin's role is the owner's alone, and nothing is vetoed retroactively.
#[test]
fn r5_p5_a_role_change_cannot_veto_an_owner_promotion() {
    let (mut chain, a) = link(1);
    let m = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 4);
    let x = admit(&mut chain, a.d(0), Role::Admin, 2, T0 + 10);
    let veto = chain
        .propose(
            x.d(1),
            &Op::SetRole(SetRole {
                member: m.root_hex(),
                role: Role::Writer,
                wraps: vec![],
                rotate: None,
            }),
        )
        .unwrap();
    own(
        &mut chain,
        a.d(0),
        Op::SetRole(SetRole {
            member: m.root_hex(),
            role: Role::Admin,
            wraps: vec![],
            rotate: None,
        }),
        T0 + 1000,
    );
    // M, now an admin, invites Y, who joins.
    let ty = {
        let secret = crypto::random32();
        let p = chain
            .propose(m.d(0), &invite_op(&secret, Role::Writer, false, T0 + 2000))
            .unwrap();
        include(&mut chain, a.d(0), &p, T0 + 2000).unwrap();
        InviteTicket {
            secret,
            entry: p.id().unwrap(),
        }
    };
    let y = Fleet::new(1);
    let jy = join(&mut chain, a.d(0), y.d(0), &ty, "y", T0 + 2010);
    accept(&mut chain, a.d(0), &jy, T0 + 2020);
    let err = include(&mut chain, a.d(0), &veto, T0 + 40 * 86_400).unwrap_err();
    assert!(err.to_string().contains("expired"), "{err}");
    // Signed again on a fresh base, it is checked against M as an admin: the owner's call.
    let again = chain
        .propose_at(
            x.d(1),
            &Op::SetRole(SetRole {
                member: m.root_hex(),
                role: Role::Writer,
                wraps: vec![],
                rotate: None,
            }),
            T0 + 40 * 86_400,
        )
        .unwrap();
    let err = include(&mut chain, a.d(0), &again, T0 + 40 * 86_400).unwrap_err();
    assert!(err.to_string().contains("may not make that role change"), "{err}");
    assert_eq!(chain.state().members[&m.root_hex()].role, Role::Admin);
    assert!(active(chain.state(), &y.root_hex()));
}

#[test]
fn a_single_use_invite_admits_the_first_join_and_refuses_the_second() {
    let (mut chain, a) = link(1);
    let t = invite(&mut chain, a.d(0), Role::Writer, false, T0 + 10);
    let (b, c) = (Fleet::new(1), Fleet::new(1));
    let first = make_join(b.d(0), &t, chain.link_id(), base_of(&chain), "b", T0 + PROPOSAL_TTL_S).unwrap();
    let second = make_join(c.d(0), &t, chain.link_id(), base_of(&chain), "c", T0 + PROPOSAL_TTL_S).unwrap();
    include(&mut chain, a.d(0), &first, T0 + 11).unwrap();
    let err = include(&mut chain, a.d(0), &second, T0 + 12).unwrap_err();
    assert!(err.to_string().contains("already used"), "{err}");
    assert!(chain.state().members.contains_key(&b.root_hex()));
    assert!(!chain.state().members.contains_key(&c.root_hex()));
    // The same proposal again is refused too: a proposal is included once.
    let err = include(&mut chain, a.d(0), &first, T0 + 13).unwrap_err();
    assert!(err.to_string().contains("already"), "{err}");
}

#[test]
fn a_join_proof_is_bound_to_its_invite_device_and_nonce() {
    let (mut chain, a) = link(1);
    let t = invite(&mut chain, a.d(0), Role::Writer, false, T0 + 10);
    let b = Fleet::new(1);
    let good = make_join(b.d(0), &t, chain.link_id(), base_of(&chain), "b", T0 + PROPOSAL_TTL_S).unwrap();
    // The same proof under another nonce (a re-signed proposal) does not verify.
    let Op::Join(j) = good.parsed().unwrap() else {
        unreachable!()
    };
    let moved = Proposal::sign(
        b.d(0),
        chain.link_id(),
        &Op::Join(j.clone()),
        base_of(&chain),
        good.expires,
    )
    .unwrap();
    assert!(
        include(&mut chain, a.d(0), &moved, T0 + 11)
            .unwrap_err()
            .to_string()
            .contains("proof")
    );
    // A thief replaying the proof under its own device does not verify either.
    let thief = Fleet::new(1);
    let stolen = Proposal::sign_with_nonce(
        thief.d(0),
        chain.link_id(),
        &Op::Join(j),
        base_of(&chain),
        good.expires,
        &good.nonce,
    )
    .unwrap();
    assert!(include(&mut chain, a.d(0), &stolen, T0 + 11).is_err());
    include(&mut chain, a.d(0), &good, T0 + 11).unwrap();
}

#[test]
fn invite_expiry_is_judged_by_the_entry_time_the_sequencer_stamps() {
    let (mut chain, a) = link(1);
    let t = invite(&mut chain, a.d(0), Role::Writer, false, T0 + 10);
    let b = Fleet::new(1);
    let p = make_join(b.d(0), &t, chain.link_id(), base_of(&chain), "b", T0 + PROPOSAL_TTL_S).unwrap();
    let expiry = T0 + 10 + DEFAULT_INVITE_TTL_S;
    let err = include(&mut chain, a.d(0), &p, expiry).unwrap_err();
    assert!(err.to_string().contains("expired"), "{err}");
    let mut fresh = link(1);
    let t = invite(&mut fresh.0, fresh.1.d(0), Role::Writer, false, T0 + 10);
    let p = make_join(
        b.d(0),
        &t,
        fresh.0.link_id(),
        base_of(&fresh.0),
        "b",
        T0 + PROPOSAL_TTL_S,
    )
    .unwrap();
    include(&mut fresh.0, fresh.1.d(0), &p, expiry - 1).unwrap();
    // Once in, a join stays in: nothing later reads its time again.
    own(
        &mut fresh.0,
        fresh.1.d(0),
        invite_op(&[9; 32], Role::Reader, false, expiry + 10),
        expiry + 10,
    );
    assert!(fresh.0.state().members.contains_key(&b.root_hex()));
}

#[test]
fn a_handoff_moves_the_next_term_to_its_target() {
    let (mut chain, a) = link(1);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    // Only to an active owner or admin device.
    let err = chain
        .append(
            a.d(0),
            Some(Op::Handoff(Handoff { to: w.d(0).id_hex() })),
            vec![],
            T0 + 30,
            &zero,
        )
        .unwrap_err();
    assert!(err.to_string().contains("owner or admin"), "{err}");
    let h = own(
        &mut chain,
        a.d(0),
        Op::Handoff(Handoff { to: x.d(0).id_hex() }),
        T0 + 30,
    );
    assert_eq!(chain.state().next_sequencer(), (x.d(0).id_hex(), 2));
    // The old sequencer cannot continue its term.
    let err = chain
        .append(
            a.d(0),
            Some(invite_op(&[1; 32], Role::Writer, false, T0 + 31)),
            vec![],
            T0 + 31,
            &zero,
        )
        .unwrap_err();
    assert!(err.to_string().contains("does not sequence"), "{err}");
    let s = chain.state().clone();
    let stale = Entry::sign(
        a.d(0),
        &s.link_id,
        1,
        s.seq + 1,
        &s.tip,
        T0 + 31,
        Some(invite_op(&[1; 32], Role::Writer, false, T0 + 31)),
        vec![],
        BTreeMap::new(),
    )
    .unwrap();
    assert!(replica(&chain).insert(vec![stale], None).refused.is_some());
    // The target starts term 2 with its next entry; the owner now proposes.
    let mut r = replica(&chain);
    let e = own(
        &mut chain,
        x.d(0),
        invite_op(&[2; 32], Role::Writer, false, T0 + 40),
        T0 + 40,
    );
    assert_eq!((e.term, e.prev.clone()), (2, h.hash().unwrap()));
    assert_eq!(r.insert(vec![e], None).added, 1);
    assert_eq!(r.state().sequencer, x.d(0).id_hex());
    let p = chain
        .propose(a.d(0), &invite_op(&[3; 32], Role::Reader, false, T0 + 50))
        .unwrap();
    include(&mut chain, x.d(0), &p, T0 + 50).unwrap();
    // The sequencer cannot be removed or demoted without handing off first.
    let op = remove_member_op(chain.state(), a.d(0), &x.root_hex());
    let p = chain.propose(a.d(0), &op).unwrap();
    let err = include(&mut chain, x.d(0), &p, T0 + 60).unwrap_err();
    assert!(err.to_string().contains("hand the sequencer off first"), "{err}");
    // An owner device may propose the handoff back.
    let p = chain
        .propose(a.d(0), &Op::Handoff(Handoff { to: a.d(0).id_hex() }))
        .unwrap();
    include(&mut chain, x.d(0), &p, T0 + 70).unwrap();
    assert_eq!(chain.state().next_sequencer(), (a.d(0).id_hex(), 3));
}

/// A chain where the owner's device 0 sequenced up to `upto` entries, then two replicas diverge.
fn takeover_fixture() -> (AclChain, Fleet, Fleet) {
    let (mut chain, a) = link(2);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    (chain, a, x)
}

#[test]
fn a_root_takeover_drops_the_lost_sequencers_later_entries() {
    let (chain, a, x) = takeover_fixture();
    let after = chain.tip();
    // The sequencer (A0) appends three more entries that only some replicas got...
    let mut lost = chain.clone();
    let mut later = Vec::new();
    for k in 0..3u8 {
        later.push(own(
            &mut lost,
            a.d(0),
            invite_op(&[k; 32], Role::Writer, false, T0 + 100),
            T0 + 100 + u64::from(k),
        ));
    }
    // ...then is lost. The owner, holding only up to `after`, takes over with its root on A1.
    let mut owner = chain.clone();
    let t = owner.takeover(a.d(1), &a.root, None, T0 + 500).unwrap();
    let Some(Op::Takeover(tk)) = &t.body else {
        unreachable!()
    };
    assert_eq!((t.term, tk.after.clone()), (2, after.clone()));
    assert_eq!(owner.state().sequencer, a.d(1).id_hex());
    // A replica on the lost branch drops its term-1 entries after `after`.
    let r = lost.insert(vec![t.clone()], Some(T0 + 500));
    assert_eq!(r.added, 1);
    assert_eq!(
        r.dropped.iter().map(|p| p.hash.clone()).collect::<Vec<_>>(),
        later.iter().map(|e| e.hash().unwrap()).collect::<Vec<_>>()
    );
    assert_eq!(summary(lost.state()), summary(owner.state()));
    // The dropped entries offered again are stale: ignored.
    let r = owner.insert(later.clone(), None);
    assert_eq!(r.added, 0);
    assert_eq!(owner.tip(), lost.tip());
    // The new term goes on; X proposes to A1.
    let p = owner
        .propose(x.d(0), &invite_op(&[7; 32], Role::Reader, false, T0 + 600))
        .unwrap();
    include(&mut owner, a.d(1), &p, T0 + 600).unwrap();
    assert!(lost.insert(owner.all(), None).refused.is_none());
    assert_eq!(summary(lost.state()), summary(owner.state()));
}

#[test]
fn a_takeover_needs_the_owners_root_and_an_owner_or_admin_device() {
    let (mut chain, a, x) = takeover_fixture();
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    // Another root: refused before anything is signed.
    let other = Fleet::new(1);
    assert!(chain.clone().takeover(a.d(1), &other.root, None, T0 + 100).is_err());
    // A takeover entry whose root signature is someone else's is refused by replicas.
    let s = chain.state().clone();
    let at = chain.tip();
    let forge = |dev: &Device, root: &SigningKey, term: u64| {
        let sig = crypto::sign(
            root,
            "acl-takeover",
            &takeover_bytes(&s.link_id, term, &at, &dev.id_hex()).unwrap(),
        );
        Entry::sign(
            dev,
            &s.link_id,
            term,
            s.seq + 1,
            &s.tip,
            T0 + 100,
            Some(Op::Takeover(Takeover {
                term,
                after: at.clone(),
                sequencer: dev.id_hex(),
                sig: b64(&sig),
            })),
            vec![],
            BTreeMap::new(),
        )
        .unwrap()
    };
    let r = chain.clone().insert(vec![forge(x.d(0), &x.root, 2)], None);
    assert!(r.refused.unwrap().contains("fleet root"));
    // Offered in place of a held entry (a fork), the forged takeover is refused before anything
    // is folded again: its root signature is checked first.
    let mut ahead = chain.clone();
    own(
        &mut ahead,
        a.d(0),
        invite_op(&[1; 32], Role::Reader, false, T0 + 50),
        T0 + 50,
    );
    let r = ahead.insert(vec![forge(x.d(0), &x.root, 2)], None);
    assert!(r.refused.unwrap().contains("fleet root"));
    // A later term with no takeover and no handoff before it: refused the same way.
    let s2 = ahead.state().clone();
    let held = ahead.entry(s2.seq).unwrap().clone();
    let bogus = Entry::sign(
        x.d(0),
        &s2.link_id,
        5,
        held.seq,
        &held.prev,
        T0 + 60,
        Some(invite_op(&[2; 32], Role::Reader, false, T0 + 60)),
        vec![],
        BTreeMap::new(),
    )
    .unwrap();
    let r = ahead.insert(vec![bogus], None);
    assert!(r.refused.as_deref().unwrap_or("").contains("handoff"), "{r:?}");
    // The root's takeover naming a writer's device: refused (only owner or admin devices).
    let r = chain.clone().insert(vec![forge(w.d(0), &a.root, 2)], None);
    assert!(r.refused.unwrap().contains("owner or admin"));
    // Naming an admin's device is fine; a term that does not go up is not.
    assert!(
        chain
            .clone()
            .insert(vec![forge(x.d(0), &a.root, 1)], None)
            .refused
            .is_some()
    );
    assert_eq!(chain.insert(vec![forge(x.d(0), &a.root, 2)], None).added, 1);
    assert_eq!(chain.state().sequencer, x.d(0).id_hex());
}

#[test]
fn a_takeover_beats_a_handoff_in_the_same_term() {
    let (mut chain, a, x) = takeover_fixture();
    let mut owner = chain.clone();
    own(
        &mut chain,
        a.d(0),
        Op::Handoff(Handoff { to: x.d(0).id_hex() }),
        T0 + 50,
    );
    let handed = own(
        &mut chain,
        x.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 60),
        T0 + 60,
    );
    assert_eq!(handed.term, 2);
    // The owner, who did not see the handoff, takes over after the entry before it: term 2 too.
    let t = owner.takeover(a.d(1), &a.root, None, T0 + 70).unwrap();
    assert_eq!(t.term, 2);
    let r = chain.insert(vec![t], None);
    assert_eq!((r.added, r.dropped.len()), (1, 2));
    assert_eq!(chain.state().sequencer, a.d(1).id_hex());
    // And the handed-off branch offered to the owner loses.
    assert_eq!(owner.insert(vec![handed], None).added, 0);
    assert_eq!(owner.tip(), chain.tip());
}

#[test]
fn equivocation_halts_the_chain_until_a_root_takeover() {
    let (chain, a, x) = takeover_fixture();
    let prefix = chain.tip();
    // The sequencer's key signs two different entries at the next position.
    let (mut left, mut right) = (chain.clone(), chain.clone());
    let e1 = own(
        &mut left,
        a.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 100),
        T0 + 100,
    );
    let e1b = own(
        &mut left,
        a.d(0),
        invite_op(&[3; 32], Role::Writer, false, T0 + 101),
        T0 + 101,
    );
    let e2 = own(
        &mut right,
        a.d(0),
        invite_op(&[2; 32], Role::Admin, false, T0 + 100),
        T0 + 100,
    );
    assert_eq!((e1.seq, e1.term), (e2.seq, e2.term));
    let mut ahead = left.clone();
    let e4 = own(
        &mut ahead,
        a.d(0),
        invite_op(&[8; 32], Role::Writer, false, T0 + 105),
        T0 + 105,
    );
    // A replica holding the left branch sees the right one: fail closed at the common prefix.
    let r = left.insert(vec![e2.clone()], None);
    assert!(r.equivocation);
    let h = left.halt().unwrap();
    assert_eq!((h.term, h.seq), (1, e1.seq));
    assert_eq!(left.tip(), prefix, "the state is the common prefix's");
    assert_eq!(left.prefix_len() as u64, e1.seq);
    assert_eq!(left.len(), chain.len() + 2, "its own branch is kept, as evidence");
    let ev = left.take_evidence();
    assert_eq!(ev.len(), 1);
    assert!(ev[0].halts());
    // Never folded back: the held state is the held tip's; what the replica grants is narrowed.
    assert_eq!(left.held_tip(), e1b.pos().unwrap());
    assert_eq!(left.held_state().seq, e1b.seq);
    assert!(left.on_chain(&prefix) && !left.on_chain(&e1.pos().unwrap()));
    // Nothing advances it: not the sequencer's next entry on either branch.
    let e3 = own(
        &mut right,
        a.d(0),
        invite_op(&[4; 32], Role::Writer, false, T0 + 102),
        T0 + 102,
    );
    let r = left.insert(vec![e3], None);
    assert_eq!(r.added, 0, "the right branch's next entry does not link here");
    assert!(left.insert(vec![e4], None).refused.unwrap().contains("equivocated"));
    assert_eq!(left.tip(), prefix);
    assert!(
        left.append(
            a.d(0),
            Some(invite_op(&[5; 32], Role::Writer, false, T0 + 103)),
            vec![],
            T0 + 103,
            &zero
        )
        .is_err()
    );
    // A proposal is not taken either (the sequencer would include it nowhere).
    let p = left
        .propose(x.d(0), &invite_op(&[6; 32], Role::Reader, false, T0 + 104))
        .unwrap();
    assert!(left.append(a.d(0), None, vec![p], T0 + 104, &zero).is_err());
    // A replica that only saw evidence frames halts too.
    let mut third = chain.clone();
    assert!(third.note_evidence(&e1, &e2).unwrap());
    assert_eq!(third.tip(), prefix);
    // Halted below its own tip, the owner must say where the takeover continues.
    let err = left.clone().takeover(a.d(1), &a.root, None, T0 + 200).unwrap_err();
    assert!(err.to_string().contains("give `after` explicitly"), "{err}");
    // The owner takes over after the common prefix: both branches are dropped everywhere.
    let t = left.takeover(a.d(1), &a.root, Some(prefix.seq), T0 + 200).unwrap();
    assert_eq!(t.term, 2);
    assert!(left.halt().is_none());
    assert_eq!(left.tip().seq, prefix.seq + 1);
    for other in [&mut right, &mut third] {
        let r = other.insert(vec![t.clone()], None);
        assert_eq!(r.added, 1);
        assert!(other.halt().is_none());
        assert_eq!(summary(other.state()), summary(left.state()));
    }
    // The halt does not come back when the evidence is offered again.
    let mut again = left.clone();
    assert!(!again.note_evidence(&e1, &e2).unwrap());
    assert_eq!(again.insert(vec![e1, e1b, e2], None).added, 0);
    assert!(again.halt().is_none());
}

/// Re-sign `e` as `dev` (any certificate at all), the way `Entry::sign` does.
fn resign(mut e: Entry, dev: &Device) -> Entry {
    e.sequencer = dev.cert.clone();
    e.sig = String::new();
    e.sig = b64(&crypto::sign(&dev.sign, "acl", &e.unsigned_bytes().unwrap()));
    e
}

/// R6-5 (probe `p5`): "two takeovers of one term" waived the same-signer rule and checked neither
/// takeover, so an outsider's self-made certificate with a junk root signature halted the link
/// after every takeover and folded it back. Now each entry of a pair must apply on its own on the
/// common prefix: a forged copy is not evidence, by insert or by an evidence frame.
#[test]
fn r6_p5_a_forged_takeover_copy_is_not_evidence() {
    let (mut chain, a, x) = takeover_fixture();
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    let t = chain.clone().takeover(a.d(1), &a.root, None, T0 + 30).unwrap();
    assert_eq!(chain.insert(vec![t.clone()], None).added, 1);
    let outsider = Fleet::new(1);
    let mut f = t.clone();
    if let Some(Op::Takeover(tk)) = f.body.as_mut() {
        tk.sig = b64(&[0u8; 64]);
        tk.sequencer = outsider.d(0).id_hex();
    }
    let f = resign(f, outsider.d(0));
    let before = summary(chain.state());
    let r = chain.insert(vec![f.clone()], None);
    assert!(!r.equivocation && chain.halt().is_none(), "{r:?}");
    assert!(chain.take_evidence().is_empty());
    assert_eq!(summary(chain.state()), before);
    // A copy re-signed by a member device (with the junk root signature, or naming a writer).
    let mut g = t.clone();
    if let Some(Op::Takeover(tk)) = g.body.as_mut() {
        tk.sequencer = w.d(0).id_hex();
    }
    let g = resign(g, w.d(0));
    assert!(!chain.insert(vec![g.clone()], None).equivocation);
    // By an evidence frame, on a replica that holds the takeover.
    let mut other = replica(&chain);
    assert!(!other.note_evidence(&f, &t).unwrap());
    assert!(!other.note_evidence(&t, &g).unwrap());
    assert!(other.halt().is_none());
    // And on a replica that holds only the position before: neither pair is evidence.
    let mut behind = chain.clone();
    behind.truncate(t.seq).unwrap();
    assert!(!behind.note_evidence(&t, &f).unwrap());
    assert!(behind.halt().is_none());
    // The root really signing two takeovers of one term is still evidence.
    let mut twice = chain.clone();
    twice.truncate(t.seq).unwrap();
    let t2 = twice.clone().takeover(x.d(0), &a.root, None, T0 + 30).unwrap();
    assert_eq!(t2.term, t.term);
    assert!(twice.note_evidence(&t, &t2).unwrap());
}

/// R6-1: evidence below a later term start halts nothing when another member started that term
/// (honest replicas have committed to it), but a term the equivocator started for itself (a
/// handoff to its own fleet's other device) buys no immunity, and fork choice never prefers a
/// branch for the terms it reached later.
#[test]
fn r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork() {
    let (mut chain, a) = link(1);
    let e = admit(&mut chain, a.d(0), Role::Admin, 2, T0 + 10);
    own(
        &mut chain,
        a.d(0),
        Op::Handoff(Handoff { to: e.d(0).id_hex() }),
        T0 + 20,
    );
    own(
        &mut chain,
        e.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 21),
        T0 + 21,
    );
    let at = chain.tip().seq;
    let base = chain.clone();
    // E's old key at `at`, a second entry.
    let mut alt = base.clone();
    alt.truncate(at).unwrap();
    let forged = own(
        &mut alt,
        e.d(0),
        invite_op(&[2; 32], Role::Reader, false, T0 + 21),
        T0 + 21,
    );
    // E hands off to its own other device: a term start by the same member.
    let mut selfish = base.clone();
    own(
        &mut selfish,
        e.d(0),
        Op::Handoff(Handoff { to: e.d(1).id_hex() }),
        T0 + 22,
    );
    own(
        &mut selfish,
        e.d(1),
        invite_op(&[3; 32], Role::Writer, false, T0 + 23),
        T0 + 23,
    );
    let r = selfish.insert(vec![forged.clone()], None);
    assert!(
        r.equivocation && selfish.halt().is_some(),
        "no immunity from a self-handoff"
    );
    // E hands back to the owner: another member started the later term, so it is an alarm only.
    let mut honest = base.clone();
    own(
        &mut honest,
        e.d(0),
        Op::Handoff(Handoff { to: a.d(0).id_hex() }),
        T0 + 22,
    );
    own(
        &mut honest,
        a.d(0),
        invite_op(&[4; 32], Role::Writer, false, T0 + 23),
        T0 + 23,
    );
    let tip = honest.tip();
    let r = honest.insert(vec![forged.clone()], None);
    assert!(!r.equivocation && honest.halt().is_none());
    let ev = honest.take_evidence();
    assert_eq!(ev.len(), 1);
    assert!(!ev[0].halts());
    // A malicious branch from the forged entry climbs terms by self-handoffs: it never wins.
    let mut climb = alt.clone();
    let mut devs = [e.d(0), e.d(1)];
    for k in 0..4u64 {
        own(
            &mut climb,
            devs[0],
            Op::Handoff(Handoff { to: devs[1].id_hex() }),
            T0 + 30 + 2 * k,
        );
        own(
            &mut climb,
            devs[1],
            invite_op(&[10 + k as u8; 32], Role::Reader, false, T0 + 31 + 2 * k),
            T0 + 31 + 2 * k,
        );
        devs.swap(0, 1);
    }
    assert!(climb.state().term > honest.state().term);
    let r = honest.insert(climb.all(), None);
    assert_eq!(r.added, 0);
    assert_eq!(
        honest.tip(),
        tip,
        "the branch with the later terms loses at its first differing entry"
    );
    // Offered only its later-term tail, the replica asks further back, and still keeps its own.
    let tail: Vec<Entry> = climb.all().into_iter().skip(at as usize + 3).collect();
    let r = honest.insert(tail, None);
    assert!(r.need_from.is_some() && r.added == 0);
    assert_eq!(honest.tip(), tip);
    // The climbing branch, holding its own self-started terms, halts on the honest entry.
    let honest_at = honest.entry(at).unwrap().clone();
    let r = climb.insert(vec![honest_at], None);
    assert!(r.equivocation && climb.halt().is_some());
}

fn remove_device_op(device: &Device) -> Op {
    Op::RemoveDevice(RemoveDevice {
        device: device.id_hex(),
        rotate: None,
    })
}

/// R7-5: after a self-handoff, the old device, retired and removed by the owner's fleet, kept a
/// halt switch over its term's positions (the later term was its own member's). It no longer
/// does once it cannot sequence and an action it could not have authored itself removed it. A
/// member that hands off to itself and removes its own old device on its own branch still buys
/// nothing (`r6_1_a_self_handoff_buys_no_immunity_and_wins_no_fork` builds the rest).
#[test]
fn r7_5_a_retired_and_removed_device_holds_no_halt_switch() {
    let (mut chain, a) = link(2);
    admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 10);
    let at = chain.tip().seq + 1;
    let mut alt = chain.clone();
    own(
        &mut chain,
        a.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 20),
        T0 + 20,
    );
    let forged = own(
        &mut alt,
        a.d(0),
        invite_op(&[2; 32], Role::Reader, false, T0 + 20),
        T0 + 20,
    );
    assert_eq!(forged.seq, at);
    own(
        &mut chain,
        a.d(0),
        Op::Handoff(Handoff { to: a.d(1).id_hex() }),
        T0 + 21,
    );
    own(
        &mut chain,
        a.d(1),
        invite_op(&[3; 32], Role::Writer, false, T0 + 22),
        T0 + 22,
    );
    // Retired only: the later term is its own member's, and it may still sequence. A halt.
    let mut retired = chain.clone();
    assert!(retired.insert(vec![forged.clone()], None).equivocation);
    // Removed by the owner's fleet: an alarm, no halt.
    own(&mut chain, a.d(1), remove_device_op(a.d(0)), T0 + 23);
    let r = chain.insert(vec![forged.clone()], None);
    assert!(!r.equivocation && chain.halt().is_none(), "{r:?}");
    let ev = chain.take_evidence();
    assert_eq!(ev.len(), 1);
    assert!(!ev[0].halts());

    // The round-6 attack with a self-removal: admin E hands off to its own other device, which
    // removes E's old one on E's branch. Still a halt there.
    let (mut chain, a) = link(1);
    let e = admit(&mut chain, a.d(0), Role::Admin, 2, T0 + 10);
    own(
        &mut chain,
        a.d(0),
        Op::Handoff(Handoff { to: e.d(0).id_hex() }),
        T0 + 20,
    );
    own(
        &mut chain,
        e.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 21),
        T0 + 21,
    );
    let at = chain.tip().seq;
    let mut alt = chain.clone();
    alt.truncate(at).unwrap();
    let forged = own(
        &mut alt,
        e.d(0),
        invite_op(&[2; 32], Role::Reader, false, T0 + 21),
        T0 + 21,
    );
    own(
        &mut chain,
        e.d(0),
        Op::Handoff(Handoff { to: e.d(1).id_hex() }),
        T0 + 22,
    );
    let mut owner_removes = chain.clone();
    own(&mut chain, e.d(1), remove_device_op(e.d(0)), T0 + 23);
    assert!(!chain.state().may_sequence(&e.d(0).id_hex()));
    let r = chain.insert(vec![forged.clone()], None);
    assert!(
        r.equivocation && chain.halt().is_some(),
        "no immunity from its own removal"
    );
    // The owner removing E's old device (a proposal E's other device includes) does settle it.
    let p = owner_removes.propose(a.d(0), &remove_device_op(e.d(0))).unwrap();
    include(&mut owner_removes, e.d(1), &p, T0 + 23).unwrap();
    let r = owner_removes.insert(vec![forged], None);
    assert!(!r.equivocation && owner_removes.halt().is_none(), "{r:?}");
}

/// An X-Wing owner fleet of 8 devices sequencing a link with `policy`, and `members` X-Wing
/// member fleets of 8 devices each (the first an admin): every device the policy allows reads.
fn xwing_link(policy: Policy, members: usize) -> (AclChain, Fleet, Vec<Fleet>) {
    let a = Fleet::xwing(MAX_DEVICES_PER_MEMBER);
    let (mut chain, _) = genesis(a.d(0), "p", "owner", policy, T0).unwrap();
    for i in 1..a.devs.len() {
        let s = chain.state().clone();
        let key = s.read_key(0, &a.d(0).id_hex(), &a.d(0).kem).unwrap();
        let mut tmp = s.clone();
        tmp.devices
            .insert(a.d(i).id_hex(), DeviceState::new(a.d(i).cert.clone(), a.root_hex()));
        let wraps = tmp.make_wraps(&key.0, s.epoch, &[a.d(i).id_hex()].into()).unwrap();
        own(
            &mut chain,
            a.d(0),
            Op::AddDevice(AddDevice {
                cert: a.d(i).cert.clone(),
                wraps,
            }),
            T0,
        );
    }
    let ms = (0..members)
        .map(|k| {
            let role = if k == 0 { Role::Admin } else { Role::Writer };
            admit_fleet(&mut chain, a.d(0), role, Fleet::xwing(MAX_DEVICES_PER_MEMBER), T0 + 10)
        })
        .collect();
    (chain, a, ms)
}

/// R6-3 (probe `p3`): `append` had no size check, and a key rotation in a link at the default
/// policy's capacity (16 members x 8 X-Wing devices) was larger than `MAX_ENTRY_BYTES`: the
/// sequencer signed it and every other replica refused it, silently. Now the largest entry a
/// policy allows fits; the sequencer signs nothing larger; a refused sequencer entry is an alarm.
#[test]
fn r6_p3_a_rotation_at_the_policys_capacity_fits_and_nothing_larger_is_signed() {
    let (mut chain, a, ms) = xwing_link(Policy::default(), 15);
    let readers = chain.state().keyed_devices().len();
    assert_eq!(readers, 128);
    let mut other = replica(&chain);
    let s = chain.state().clone();
    let key = s.read_key(s.epoch, &a.d(0).id_hex(), &a.d(0).kem).unwrap();
    let rot = own(
        &mut chain,
        a.d(0),
        Op::RotateKey(s.new_key_change(&key, &s.keyed_devices()).unwrap().0),
        T0 + 20,
    );
    let size = codec::canonical(&rot).unwrap().len();
    assert!(size > 192 * 1024 && size <= MAX_ENTRY_BYTES, "{size}");
    let r = other.insert(vec![rot], None);
    assert!(r.refused.is_none() && r.added == 1, "{r:?}");
    // The sequencer signs nothing larger than any replica takes: a pile of proposals.
    let admin = &ms[0];
    let props: Vec<Proposal> = (0..400u16)
        .map(|k| {
            let mut secret = [0u8; 32];
            secret[..2].copy_from_slice(&k.to_be_bytes());
            chain
                .propose(admin.d(0), &invite_op(&secret, Role::Reader, false, T0 + 30))
                .unwrap()
        })
        .collect();
    let tip = chain.tip();
    let err = chain.append(a.d(0), None, props, T0 + 30, &zero).unwrap_err();
    assert!(err.to_string().contains("larger than"), "{err}");
    assert_eq!(chain.tip(), tip);
    // A replica that refuses the sequencer's next entry says so (a divergence, not silence).
    let mut late = replica(&chain);
    let e = own(
        &mut chain,
        a.d(0),
        invite_op(&[9; 32], Role::Reader, false, T0 + 10_000),
        T0 + 10_000,
    );
    let r = late.insert(vec![e], Some(T0));
    assert!(r.refused.is_some() && r.diverged.is_some(), "{r:?}");
}

/// R6-3: the largest entry the largest policy allows (a rotation proposed by an X-Wing admin,
/// wrapped to `MAX_LINK_MEMBERS` x `MAX_DEVICES_PER_MEMBER` X-Wing devices) fits one entry and
/// one sync frame; a policy allowing more members is refused at genesis.
#[test]
fn the_largest_policy_fits_one_entry_and_one_frame() {
    let policy = Policy {
        max_members: MAX_LINK_MEMBERS,
        ..Policy::default()
    };
    let too_many = Policy {
        max_members: MAX_LINK_MEMBERS + 1,
        ..Policy::default()
    };
    let f = Fleet::new(1);
    let err = genesis(f.d(0), "p", "owner", too_many, T0).err().unwrap();
    assert!(err.to_string().contains("out of range"), "{err}");
    let (mut chain, a, ms) = xwing_link(policy, MAX_LINK_MEMBERS as usize - 1);
    assert_eq!(chain.state().keyed_devices().len(), 256);
    let s = chain.state().clone();
    let admin = ms[0].d(0);
    let key = s.read_key(s.epoch, &admin.id_hex(), &admin.kem).unwrap();
    let op = Op::RotateKey(s.new_key_change(&key, &s.keyed_devices()).unwrap().0);
    let p = chain.propose(admin, &op).unwrap();
    let e = include(&mut chain, a.d(0), &p, T0 + 20).unwrap();
    let size = codec::canonical(&e).unwrap().len();
    assert!(size <= MAX_ENTRY_BYTES, "{size}");
    let frame = crate::sync::encode(&crate::sync::Frame::Acl { entries: vec![e] }).unwrap();
    assert!(frame.len() <= crate::sync::MAX_FRAME);
    eprintln!("the largest rotation: {size} bytes of {MAX_ENTRY_BYTES}");
}

#[test]
fn a_restored_chain_keeps_its_halt_and_its_state() {
    let (chain, a, _) = takeover_fixture();
    let (mut left, mut right) = (chain.clone(), chain.clone());
    let e1 = own(
        &mut left,
        a.d(0),
        invite_op(&[1; 32], Role::Writer, false, T0 + 100),
        T0 + 100,
    );
    let e2 = own(
        &mut right,
        a.d(0),
        invite_op(&[2; 32], Role::Writer, false, T0 + 100),
        T0 + 100,
    );
    left.insert(vec![e2.clone()], None);
    let pairs = left.take_evidence();
    assert_eq!(
        (pairs.len(), pairs[0].ours.clone(), pairs[0].theirs.clone()),
        (1, e1, e2)
    );
    let mut back = AclChain::new();
    back.restore(
        (0..left.len() as u64).map(|s| left.entry(s).unwrap().clone()).collect(),
        pairs,
    )
    .unwrap();
    assert!(back.halt().is_some());
    assert_eq!(summary(back.state()), summary(left.state()));
}

#[test]
fn cuts_name_exactly_the_devices_an_entry_removes() {
    let (mut chain, a) = link(1);
    let b = admit(&mut chain, a.d(0), Role::Writer, 2, T0 + 10);
    let op = remove_member_op(chain.state(), a.d(0), &b.root_hex());
    let heads = |d: &str| if d == b.d(0).id_hex() { 7 } else { 3 };
    let e = chain.append(a.d(0), Some(op.clone()), vec![], T0 + 20, &heads).unwrap();
    assert_eq!(e.cuts.len(), 2);
    assert_eq!(chain.state().devices[&b.d(0).id_hex()].cut, Some(7));
    assert_eq!(chain.state().devices[&b.d(1).id_hex()].cut, Some(3));
    // A sequencer's entry whose cuts leave a removed device out is refused by replicas.
    let r0 = replica(&chain);
    let mut r = AclChain::new();
    r.insert(chain.all()[..chain.len() - 1].to_vec(), None);
    let s = r.state().clone();
    let mut cuts = e.cuts.clone();
    cuts.remove(&b.d(1).id_hex());
    let bad = Entry::sign(
        a.d(0),
        &s.link_id,
        1,
        s.seq + 1,
        &s.tip,
        T0 + 20,
        Some(op),
        vec![],
        cuts,
    )
    .unwrap();
    assert!(r.insert(vec![bad], None).refused.unwrap().contains("cuts"));
    assert_eq!(summary(r0.state()), summary(chain.state()));
}

#[test]
fn renewals_are_bounded_on_both_sides() {
    let (mut chain, a) = link(1);
    let mut w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 10);
    let stored = chain.state().devices[&w.d(0).id_hex()].cert.clone();
    let root = w.root.clone();
    let renew = |w: &mut Fleet, at: u64| {
        let mut d = Device::from_json(&w.d(0).to_json().unwrap()).unwrap();
        d.renew(&root, at).unwrap();
        d
    };
    // Before the renewal window: refused.
    let early = renew(&mut w, T0 + 20);
    let p = chain
        .propose(&early, &invite_op(&[1; 32], Role::Reader, false, T0))
        .unwrap();
    let err = include(&mut chain, a.d(0), &p, T0 + 30).unwrap_err();
    assert!(
        err.to_string().contains("window") || err.to_string().contains("admin"),
        "{err}"
    );
    let add = |d: &Device| {
        Op::AddDevice(AddDevice {
            cert: d.cert.clone(),
            wraps: vec![],
        })
    };
    assert!(
        chain
            .clone()
            .append(a.d(0), Some(add(&early)), vec![], T0 + 30, &zero)
            .unwrap_err()
            .to_string()
            .contains("window")
    );
    // The owner's sequencer renews its own certificate first (its entries carry it), so it can
    // sign entries past the original expiry.
    let mut seq = Device::from_json(&a.d(0).to_json().unwrap()).unwrap();
    seq.renew(&a.root, stored.not_after - 1000).unwrap();
    own(
        &mut chain,
        &seq,
        invite_op(&[4; 32], Role::Reader, false, stored.not_after - 900),
        stored.not_after - 900,
    );
    // A renewal that starts after the stored certificate ends: refused.
    let gap = renew(&mut w, stored.not_after + 10);
    let at = stored.not_after + 20;
    let err = chain
        .clone()
        .append(&seq, Some(add(&gap)), vec![], at, &zero)
        .unwrap_err();
    assert!(err.to_string().contains("start"), "{err}");
    // More than one lifetime after the stored one ended: refused (the renewed cert would not even
    // be valid then).
    let ts = stored.not_after + CERT_MAX_LIFETIME_S + 1;
    let mut late = Device::from_json(&w.d(0).to_json().unwrap()).unwrap();
    late.renew(&root, stored.not_after - 5).unwrap();
    assert!(
        check_renewal(&stored, &late.cert, ts)
            .unwrap_err()
            .to_string()
            .contains("lifetime")
    );
    // Inside the window, starting before the stored end: taken.
    let good = renew(&mut w, stored.not_after - 100);
    chain
        .append(&seq, Some(add(&good)), vec![], stored.not_after - 50, &zero)
        .unwrap();
    assert_eq!(
        chain.state().devices[&w.d(0).id_hex()].cert.not_after,
        good.cert.not_after
    );
    // A certificate without its device's proof of possession never verifies.
    let mut squat = good.cert.clone();
    squat.pop = squat.sig.clone();
    assert!(squat.verify().is_err());
}

/// A device renewing its own certificate (the daemon's `identity.renew`): on the sequencer an
/// own action, elsewhere a proposal; either way the renewal it carries is the one taken.
#[test]
fn a_device_renews_itself_on_the_sequencer_and_by_proposal() {
    let (mut chain, a) = link(1);
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 10);
    let stored = chain.state().devices[&a.d(0).id_hex()].cert.clone();
    let at = stored.not_after - 1000;
    let mut seq = Device::from_json(&a.d(0).to_json().unwrap()).unwrap();
    seq.renew(&a.root, at).unwrap();
    let add = |d: &Device| {
        Op::AddDevice(AddDevice {
            cert: d.cert.clone(),
            wraps: vec![],
        })
    };
    chain.append(&seq, Some(add(&seq)), vec![], at, &zero).unwrap();
    assert_eq!(chain.state().devices[&seq.id_hex()].cert.not_after, seq.cert.not_after);
    let mut wd = Device::from_json(&w.d(0).to_json().unwrap()).unwrap();
    wd.renew(&w.root, at).unwrap();
    let p = chain.propose(&wd, &add(&wd)).unwrap();
    include(&mut chain, &seq, &p, at + 1).unwrap();
    assert_eq!(chain.state().devices[&wd.id_hex()].cert.not_after, wd.cert.not_after);
    assert_eq!(summary(replica(&chain).state()), summary(chain.state()));
}

#[test]
fn a_rotation_is_taken_from_the_designated_device_or_any_key_holder_after_the_grace() {
    let (mut chain, a) = link(1);
    let r = admit(&mut chain, a.d(0), Role::Reader, 1, T0 + 10);
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    // W leaves: a rotation is due (a leaver picks no key).
    let leave = chain
        .propose(
            w.d(0),
            &Op::RemoveMember(RemoveMember {
                member: w.root_hex(),
                rotate: None,
            }),
        )
        .unwrap();
    let due_at = T0 + 30;
    include(&mut chain, a.d(0), &leave, due_at).unwrap();
    let s = chain.state().clone();
    assert!(s.rotation_due && s.rotation_due_since == due_at);
    assert_eq!(
        s.designated_rotator(None),
        Some(a.d(0).id_hex()),
        "the sequencer holds the key"
    );
    let k = s.read_key(s.epoch, &r.d(0).id_hex(), &r.d(0).kem).unwrap();
    let change = s.new_key_change(&k, &s.keyed_devices()).unwrap().0;
    let p = chain.propose(r.d(0), &Op::RotateKey(change)).unwrap();
    let err = include(&mut chain, a.d(0), &p, due_at + ROTATION_GRACE_S - 1).unwrap_err();
    assert!(err.to_string().contains("designated"), "{err}");
    include(&mut chain, a.d(0), &p, due_at + ROTATION_GRACE_S).unwrap();
    assert!(!chain.state().rotation_due);
}

#[test]
fn junk_wraps_raise_an_alarm_and_an_admin_recovers() {
    let (mut chain, a) = link(1);
    let r = admit(&mut chain, a.d(0), Role::Reader, 1, T0 + 10);
    let w = admit(&mut chain, a.d(0), Role::Writer, 1, T0 + 20);
    let leave = chain
        .propose(
            w.d(0),
            &Op::RemoveMember(RemoveMember {
                member: w.root_hex(),
                rotate: None,
            }),
        )
        .unwrap();
    include(&mut chain, a.d(0), &leave, T0 + 30).unwrap();
    // After the grace, R rotates but wraps junk to the owner under the right key id.
    let s = chain.state().clone();
    let k = s.read_key(s.epoch, &r.d(0).id_hex(), &r.d(0).kem).unwrap();
    let (mut change, next) = s.new_key_change(&k, &s.keyed_devices()).unwrap();
    let junk = s
        .make_wraps(&[0xAA; 32], change.epoch, &[a.d(0).id_hex()].into())
        .unwrap();
    for w in change.wraps.iter_mut().filter(|w| w.device == a.d(0).id_hex()) {
        w.enc.clone_from(&junk[0].enc);
        w.ct.clone_from(&junk[0].ct);
    }
    let _ = next;
    let p = chain.propose(r.d(0), &Op::RotateKey(change)).unwrap();
    include(&mut chain, a.d(0), &p, T0 + 30 + ROTATION_GRACE_S).unwrap();
    let s = chain.state().clone();
    assert_eq!(
        s.bad_wrap(s.epoch, &a.d(0).id_hex(), &a.d(0).kem),
        Some(r.d(0).id_hex())
    );
    // The owner re-keys from the last epoch it reads; the reader reads again.
    let old = s.read_key(s.epoch - 1, &a.d(0).id_hex(), &a.d(0).kem).unwrap();
    let (rk, _) = s.recovery_key_change(s.epoch - 1, &old, &s.keyed_devices()).unwrap();
    own(&mut chain, a.d(0), Op::RotateKey(rk), T0 + 40 + ROTATION_GRACE_S);
    let s = chain.state();
    assert!(s.read_key(s.epoch, &a.d(0).id_hex(), &a.d(0).kem).is_ok());
    assert!(s.read_key(s.epoch, &r.d(0).id_hex(), &r.d(0).kem).is_ok());
    assert!(
        s.read_key(0, &r.d(0).id_hex(), &r.d(0).kem).is_ok(),
        "history before the junk too"
    );
}

#[test]
fn a_proposals_base_must_be_on_the_chain_and_it_expires() {
    let (mut chain, a) = link(1);
    let x = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 10);
    let op = invite_op(&[1; 32], Role::Reader, false, T0 + 20);
    let exp = T0 + PROPOSAL_TTL_S;
    let ahead = Proposal::sign(x.d(0), chain.link_id(), &op, Base { term: 1, seq: 999 }, exp).unwrap();
    assert!(
        include(&mut chain, a.d(0), &ahead, T0 + 20)
            .unwrap_err()
            .to_string()
            .contains("base")
    );
    let wrong_term = Proposal::sign(x.d(0), chain.link_id(), &op, Base { term: 5, seq: 1 }, exp).unwrap();
    assert!(include(&mut chain, a.d(0), &wrong_term, T0 + 20).is_err());
    // A proposal carries its own expiry: no entry at or after it includes the proposal...
    let late = 2 * PROPOSAL_TTL_S;
    let short = chain
        .propose_at(x.d(0), &invite_op(&[2; 32], Role::Reader, false, T0 + late), T0 + 20)
        .unwrap();
    let err = include(&mut chain, a.d(0), &short, T0 + 20 + PROPOSAL_TTL_S).unwrap_err();
    assert!(err.to_string().contains("expired"), "{err}");
    // ...and the expiry it names is never further ahead than a proposal may last.
    let far = Proposal::sign(
        x.d(0),
        chain.link_id(),
        &invite_op(&[3; 32], Role::Reader, false, T0 + 30),
        base_of(&chain),
        T0 + 30 + PROPOSAL_TTL_S + MAX_FUTURE_SKEW_S + 1,
    )
    .unwrap();
    let err = include(&mut chain, a.d(0), &far, T0 + 30).unwrap_err();
    assert!(err.to_string().contains("further ahead"), "{err}");
    // On a quiet chain a proposal made now on an old tip is good: nothing ages it but its expiry.
    let quiet = chain
        .propose_at(x.d(0), &invite_op(&[4; 32], Role::Reader, false, T0 + late), T0 + late)
        .unwrap();
    include(&mut chain, a.d(0), &quiet, T0 + late + 1).unwrap();
}

/// R6-6: a proposal included in an entry that a takeover dropped could be included again,
/// bringing back an invite with `used = false`. Now a proposal on a base before the latest
/// takeover is void until its proposer signs it again.
#[test]
fn r6_6_a_proposal_on_a_dropped_position_is_void_until_signed_again() {
    let (mut chain, a, x) = takeover_fixture();
    let after = chain.tip();
    // X's invite is included, and a join uses it; the owner's takeover drops both.
    let p = chain
        .propose(x.d(0), &invite_op(&[5; 32], Role::Writer, false, T0 + 40))
        .unwrap();
    let e = include(&mut chain, a.d(0), &p, T0 + 40).unwrap();
    let ticket = InviteTicket {
        secret: [5; 32],
        entry: p.id().unwrap(),
    };
    let j = Fleet::new(1);
    join(&mut chain, a.d(0), j.d(0), &ticket, "j", T0 + 41);
    assert!(chain.state().invites[&ticket.entry].used);
    let t = chain.takeover(a.d(1), &a.root, Some(after.seq), T0 + 50).unwrap();
    assert!(chain.entry(e.seq).unwrap().hash().unwrap() == t.hash().unwrap());
    assert!(!chain.state().invites.contains_key(&ticket.entry));
    // The same proposal again: void, so the invite does not come back unused.
    let err = include(&mut chain, a.d(1), &p, T0 + 60).unwrap_err();
    assert!(err.to_string().contains("takeover"), "{err}");
    assert!(!chain.state().invites.contains_key(&ticket.entry));
    // Signed again on the new term, it is a new action (a new id, so the old code is dead).
    let again = chain
        .propose(x.d(0), &invite_op(&[5; 32], Role::Writer, false, T0 + 61))
        .unwrap();
    include(&mut chain, a.d(1), &again, T0 + 61).unwrap();
    assert_ne!(again.id().unwrap(), ticket.entry);
    assert!(!chain.state().invites.contains_key(&ticket.entry));
}

#[test]
fn removing_an_admins_device_is_the_owners_alone() {
    let (mut chain, a) = link(1);
    let x = admit(&mut chain, a.d(0), Role::Admin, 2, T0 + 10);
    let y = admit(&mut chain, a.d(0), Role::Admin, 1, T0 + 20);
    let p = chain
        .propose(
            y.d(0),
            &Op::RemoveDevice(RemoveDevice {
                device: x.d(1).id_hex(),
                rotate: None,
            }),
        )
        .unwrap();
    assert!(
        include(&mut chain, a.d(0), &p, T0 + 30)
            .unwrap_err()
            .to_string()
            .contains("owner")
    );
    // X removes its own other device; the owner removes any.
    let p = chain
        .propose(
            x.d(0),
            &Op::RemoveDevice(RemoveDevice {
                device: x.d(1).id_hex(),
                rotate: None,
            }),
        )
        .unwrap();
    include(&mut chain, a.d(0), &p, T0 + 40).unwrap();
}

#[test]
fn a_5000_entry_chain_folds_from_scratch_quickly_and_positions_are_cheap() {
    let (mut chain, a) = link(1);
    let mut ts = T0;
    for i in 0..5000u32 {
        ts += 1;
        let mut s = [0u8; 32];
        s[..4].copy_from_slice(&i.to_be_bytes());
        own(&mut chain, a.d(0), invite_op(&s, Role::Reader, false, ts), ts);
    }
    let t = std::time::Instant::now();
    let r = replica(&chain);
    let fold = t.elapsed();
    assert_eq!(summary(r.state()), summary(chain.state()));
    let t = std::time::Instant::now();
    for seq in [17u64, 1000, 2555, 4999] {
        assert_eq!(r.state_at(seq).unwrap().seq, seq);
    }
    eprintln!("5,000 entries: fold {fold:?}, four positions {:?}", t.elapsed());
}

// ---------------------------------------------------------------------------- property test

use proptest::prelude::*;

fn cases(default: u32) -> u32 {
    std::env::var("PROPTEST_CASES")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(default)
}

/// One random proposal or own action against the current state; refused ones are skipped.
fn act(chain: &mut AclChain, a: &Fleet, members: &[Fleet], who: usize, what: usize, ts: u64) {
    let s = chain.state().clone();
    let pick = |i: usize| -> &Device {
        if i == 0 {
            a.d(0)
        } else {
            members[(i - 1) % members.len()].d(0)
        }
    };
    let dev = pick(who);
    let target = &members[what % members.len()];
    let op = match what % 7 {
        0 => invite_op(&crypto::random32(), Role::Reader, false, ts),
        1 => remove_member_op(&s, dev, &target.root_hex()),
        2 => Op::SetRole(SetRole {
            member: target.root_hex(),
            role: if what.is_multiple_of(2) {
                Role::Writer
            } else {
                Role::Admin
            },
            wraps: vec![],
            rotate: None,
        }),
        3 => match s.read_key(s.epoch, &dev.id_hex(), &dev.kem) {
            Ok(k) => Op::RotateKey(s.new_key_change(&k, &s.keyed_devices()).unwrap().0),
            Err(_) => return,
        },
        4 => Op::RemoveMember(RemoveMember {
            member: dev.cert.root.clone(),
            rotate: None,
        }),
        5 => Op::RevokeInvite(RevokeInvite {
            invite: s.invites.keys().next().cloned().unwrap_or_default(),
        }),
        _ => Op::Handoff(Handoff {
            to: pick(what).id_hex(),
        }),
    };
    let seq = s.next_sequencer().0;
    let seq_dev = std::iter::once(a.d(0))
        .chain(members.iter().map(|m| m.d(0)))
        .find(|d| d.id_hex() == seq)
        .expect("the sequencer is a test device");
    if dev.id_hex() == seq {
        let _ = chain.append(seq_dev, Some(op), vec![], ts, &zero);
    } else if let Ok(p) = chain.propose(dev, &op) {
        let _ = chain.append(seq_dev, None, vec![p], ts, &zero);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: cases(24), ..ProptestConfig::default() })]

    /// Random proposal sequences: two replicas applying the same chain, in any chunking and any
    /// order within a chunk, and a store restore, always agree with the sequencer.
    #[test]
    fn replicas_of_one_chain_always_agree(
        steps in proptest::collection::vec((0usize..5, 0usize..40), 1..40),
        cut in 1usize..10,
    ) {
        let (mut chain, a) = link(1);
        let members: Vec<Fleet> = (0..3)
            .map(|k| admit(&mut chain, a.d(0), if k == 0 { Role::Admin } else { Role::Writer }, 1, T0 + 10 * k as u64))
            .collect();
        let mut ts = T0 + 100;
        for (who, what) in steps {
            ts += 7;
            act(&mut chain, &a, &members, who, what, ts);
        }
        let all = chain.all();
        let mut r1 = AclChain::new();
        for chunk in all.chunks(cut) {
            let mut c = chunk.to_vec();
            c.reverse();
            let got = r1.insert(c, None);
            prop_assert!(got.refused.is_none(), "{:?}", got.refused);
        }
        let mut r2 = AclChain::new();
        r2.restore(all.clone(), vec![]).unwrap();
        prop_assert_eq!(summary(r1.state()), summary(chain.state()));
        prop_assert_eq!(summary(r2.state()), summary(chain.state()));
        for seq in 0..all.len() as u64 {
            prop_assert_eq!(summary(&r1.state_at(seq).unwrap()), summary(&r2.state_at(seq).unwrap()));
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: cases(24), ..ProptestConfig::default() })]

    /// R6-1: random proposal sequences, then evidence injected at a random position (the
    /// sequencer there signing a second entry) by a random channel: an insert, an evidence frame,
    /// or a pair at the next position. Whatever it does (a halt, an alarm, nothing), no device is
    /// active in the state the replica acts on that is not active at its held tip, no role is
    /// higher, and no record is sealed under an epoch older than the newest held.
    #[test]
    fn evidence_never_widens_access_or_seals_under_an_older_epoch(
        steps in proptest::collection::vec((0usize..5, 0usize..40), 1..40),
        at in any::<proptest::sample::Index>(),
        how in 0usize..3,
    ) {
        let (mut chain, a) = link(1);
        let members: Vec<Fleet> = (0..3)
            .map(|k| admit(&mut chain, a.d(0), if k == 0 { Role::Admin } else { Role::Writer }, 1, T0 + 10 * k as u64))
            .collect();
        let mut ts = T0 + 100;
        for (who, what) in steps {
            ts += 7;
            act(&mut chain, &a, &members, who, what, ts);
        }
        let devs: Vec<&Device> = std::iter::once(a.d(0)).chain(members.iter().map(|m| m.d(0))).collect();
        let len = chain.len();
        let j = 1 + at.index(len);
        // A second entry at `j`, signed by whoever sequences there.
        let forge = |nonce: u8| -> Option<Entry> {
            let mut alt = chain.clone();
            alt.truncate(j as u64).ok()?;
            let next = alt.state().next_sequencer().0;
            let dev = devs.iter().find(|d| d.id_hex() == next)?;
            let mut secret = crypto::random32();
            secret[0] = nonce;
            alt.append(dev, Some(invite_op(&secret, Role::Reader, false, ts)), vec![], ts, &zero).ok()
        };
        let mut l = crate::engine::Link::adopt(None, chain.all(), ts + 1).unwrap();
        match (how, j < len) {
            (0, true) => {
                if let Some(f) = forge(1) {
                    l.add_acl(vec![f], ts + 1).unwrap();
                }
            }
            (1, true) => {
                if let Some(f) = forge(1) {
                    let ours = chain.entry(j as u64).unwrap().clone();
                    let _ = l.acl.note_evidence(&ours, &f);
                    l.add_acl(vec![], ts + 1).unwrap();
                }
            }
            _ => {
                if let (Some(f), Some(g)) = (forge(1), forge(2)) {
                    let _ = l.acl.note_evidence(&f, &g);
                    l.add_acl(vec![], ts + 1).unwrap();
                }
            }
        }
        // The held tip is the chain the replica took before any evidence: what the evidence
        // may narrow, never widen.
        let held = chain.state().clone();
        prop_assert_eq!(summary(l.acl.held_state()), summary(&held), "the held state is never folded back");
        let view = l.state().clone();
        for d in view.devices.keys() {
            if let Some((m, _)) = view.active_device(d) {
                let h = held.active_device(d);
                prop_assert!(h.is_some(), "{d} active only in the halted view");
                prop_assert!(m.role <= h.unwrap().0.role, "{d} has a higher role in the halted view");
            }
        }
        prop_assert!(view.sync_devices().is_subset(&held.sync_devices()));
        prop_assert_eq!(view.epoch, held.epoch);
        for (i, dev) in devs.iter().enumerate() {
            let body = crate::record::Body {
                kind: "note".into(),
                seat: "claude".into(),
                to: "@any/codex".into(),
                content: format!("from {i}"),
                sent_at: ts,
                ..crate::record::Body::default()
            };
            if let Ok((_, r)) = l.write(dev, &body, ts + 2) {
                prop_assert!(l.acl.halt().is_none(), "nothing is sealed while halted");
                // (A sequencer's write may append a due rotation first: the newest held.)
                prop_assert_eq!(r.epoch, l.acl.held_state().epoch, "sealed under an older epoch");
                prop_assert!(r.epoch >= held.epoch, "sealed under an older epoch");
            }
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: cases(24), ..ProptestConfig::default() })]

    /// R7-1, R7-3: random histories, then a random flood of evidence (second entries at random
    /// positions by whoever sequenced there, by insert batches, evidence frames and pairs at the
    /// next position) and of proposals (valid ones from admins, refusable ones from members,
    /// outsiders' ones, a member's certificate under another key, joins on unknown and on dead
    /// invites), offered from random member peers to the replica as a relay or as the sequencer.
    /// Stored evidence stays one pair per position and signer, at most one alarm per signer and
    /// one halt, within `MAX_EVIDENCE_PAIRS`; relayed and refused proposal rows stay within their
    /// caps; nothing is included; and the replica never grants more than its held tip, which no
    /// flood changes.
    #[test]
    fn floods_stay_within_their_caps_and_never_widen_access(
        steps in proptest::collection::vec((0usize..5, 0usize..40), 1..30),
        evidence in proptest::collection::vec((any::<proptest::sample::Index>(), 0usize..3, any::<u8>()), 0..24),
        proposals in proptest::collection::vec((0usize..8, 0usize..3), 0..200),
        as_sequencer in any::<bool>(),
    ) {
        use crate::engine::{Link, MAX_RELAYED, MAX_RELAYED_PER_ORIGIN};
        let (mut chain, a) = link(1);
        let members: Vec<Fleet> = (0..3)
            .map(|k| admit(&mut chain, a.d(0), if k == 0 { Role::Admin } else { Role::Writer }, 1, T0 + 10 * k as u64))
            .collect();
        // An invite that is dead by the time of the flood (it expires).
        let dead = invite(&mut chain, a.d(0), Role::Writer, false, T0 + 50);
        let mut ts = T0 + 100;
        for (who, what) in steps {
            ts += 7;
            act(&mut chain, &a, &members, who, what, ts);
        }
        let now = ts + 2 * DEFAULT_INVITE_TTL_S;
        let devs: Vec<&Device> = std::iter::once(a.d(0)).chain(members.iter().map(|m| m.d(0))).collect();
        let len = chain.len();
        let forge = |j: usize, nonce: u8| -> Option<Entry> {
            let mut alt = chain.clone();
            alt.truncate(j as u64).ok()?;
            let next = alt.state().next_sequencer().0;
            let dev = devs.iter().find(|d| d.id_hex() == next)?;
            let mut secret = crypto::random32();
            secret[0] = nonce;
            alt.append(dev, Some(invite_op(&secret, Role::Reader, false, ts)), vec![], ts, &zero).ok()
        };
        let mut l = Link::adopt(None, chain.all(), ts + 1).unwrap();
        for (at, how, nonce) in evidence {
            let j = 1 + at.index(len);
            match (how, j < len) {
                (0, true) => {
                    let batch: Vec<Entry> = (0..3).filter_map(|k| forge(j, nonce.wrapping_add(k))).collect();
                    let _ = l.add_acl(batch, ts + 1);
                }
                (1, true) => {
                    if let Some(f) = forge(j, nonce) {
                        let ours = chain.entry(j as u64).unwrap().clone();
                        let _ = l.acl.note_evidence(&ours, &f);
                        let _ = l.add_acl(vec![], ts + 1);
                    }
                }
                _ => {
                    if let (Some(f), Some(g)) = (forge(len, nonce), forge(len, nonce.wrapping_add(1))) {
                        let _ = l.acl.note_evidence(&f, &g);
                        let _ = l.add_acl(vec![], ts + 1);
                    }
                }
            }
        }
        let held = chain.state().clone();
        prop_assert_eq!(summary(l.acl.held_state()), summary(&held), "evidence never folds back");
        // The proposal flood.
        let s = l.state().clone();
        let seq = s.next_sequencer().0;
        let me = if as_sequencer {
            devs.iter().find(|d| d.id_hex() == seq)
        } else {
            devs.iter().find(|d| d.id_hex() != seq)
        };
        let me: &Device = me.expect("a test device");
        let admins: Vec<&Device> = devs
            .iter()
            .copied()
            .filter(|d| s.active_device(&d.id_hex()).is_some_and(|(m, _)| m.role.admin()))
            .collect();
        let others: Vec<&Device> = devs
            .iter()
            .copied()
            .filter(|d| s.active_device(&d.id_hex()).is_some_and(|(m, _)| !m.role.admin()))
            .collect();
        let outsider = Fleet::new(1);
        let joiner = Fleet::new(1);
        let mut forger = Fleet::new(1).devs.remove(0);
        forger.cert = members[1].d(0).cert.clone();
        let peers: Vec<String> = devs.iter().map(|d| d.id_hex()).filter(|d| *d != me.id_hex()).collect();
        let tip = l.acl.tip();
        let base = Base { term: tip.term, seq: tip.seq };
        for (kind, peer) in proposals {
            let fresh = crypto::random32();
            let op = invite_op(&fresh, Role::Reader, false, now);
            let p = match kind {
                // Valid where it is kept, and so only offered to a relay.
                0 | 6 | 7 if !as_sequencer => match admins.first() {
                    Some(d) => Proposal::sign(d, l.id(), &op, base, now + PROPOSAL_TTL_S),
                    None => continue,
                },
                1 => match others.first() {
                    Some(d) => Proposal::sign(d, l.id(), &op, base, now + PROPOSAL_TTL_S),
                    None => continue,
                },
                2 => Proposal::sign(outsider.d(0), l.id(), &op, base, now + PROPOSAL_TTL_S),
                3 => Proposal::sign(&forger, l.id(), &op, base, now + PROPOSAL_TTL_S),
                4 => {
                    let t = InviteTicket { secret: fresh, entry: hex(&fresh) };
                    make_join(joiner.d(0), &t, l.id(), base, "j", now + PROPOSAL_TTL_S)
                }
                _ => make_join(joiner.d(0), &dead, l.id(), base, "j", now + PROPOSAL_TTL_S),
            };
            let Ok(p) = p else { continue };
            let _ = l.offer_from(me, &p, &peers[peer % peers.len()], now);
        }
        prop_assert_eq!(l.acl.len(), len, "nothing invalid is included");
        prop_assert_eq!(summary(l.acl.held_state()), summary(&held));
        // Within the caps.
        let count = |sql: &str| -> i64 { l.store.conn.query_row(sql, [], |r| r.get(0)).unwrap() };
        prop_assert!(count("SELECT count(*) FROM acl_evidence") <= i64::from(MAX_EVIDENCE_PAIRS));
        prop_assert!(count("SELECT count(*) FROM acl_evidence WHERE kind = 'halt'") <= 1);
        prop_assert!(count("SELECT coalesce(max(n), 0) FROM (SELECT count(*) AS n FROM acl_evidence WHERE kind = 'alarm' GROUP BY signer)") <= 1);
        prop_assert_eq!(
            count("SELECT count(*) FROM (SELECT DISTINCT signer, term, seq FROM acl_evidence)"),
            count("SELECT count(*) FROM acl_evidence")
        );
        prop_assert!(count("SELECT count(*) FROM proposals WHERE mine = 0") <= i64::from(MAX_RELAYED));
        prop_assert!(
            count("SELECT coalesce(max(n), 0) FROM (SELECT count(*) AS n FROM proposals WHERE mine = 0 GROUP BY grp)")
                <= i64::from(MAX_RELAYED_PER_ORIGIN)
        );
        // Never wider than the held tip.
        let view = l.state().clone();
        for d in view.devices.keys() {
            if let Some((m, _)) = view.active_device(d) {
                let h = held.active_device(d);
                prop_assert!(h.is_some(), "{d} active only in the halted view");
                prop_assert!(m.role <= h.unwrap().0.role, "{d} has a higher role in the halted view");
            }
        }
        prop_assert!(view.sync_devices().is_subset(&held.sync_devices()));
    }
}
