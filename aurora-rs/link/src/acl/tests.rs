use super::*;
use crate::identity::{Device, new_phrase, root_from_phrase};
use proptest::prelude::*;

const T0: u64 = 1_000;

struct Fleet {
    root: SigningKey,
    devs: Vec<Device>,
}

impl Fleet {
    fn new(devices: usize, xwing: bool) -> Self {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let devs = (0..devices)
            .map(|i| Device::create(&root, &format!("d{i}"), xwing && i == 0, T0).unwrap())
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

fn key_of(log: &AclLog, dev: &Device) -> Secret32 {
    let s = log.state();
    s.read_key(s.epoch, &dev.id_hex(), &dev.kem).unwrap()
}

fn invite(log: &mut AclLog, by: &Device, role: Role, approval: bool, ts: u64) -> [u8; 32] {
    let secret = crypto::random32();
    let op = Op::Invite(Invite {
        invite: hex(&crypto::public_of(&invite_key(&secret))),
        role,
        expires: ts + DEFAULT_INVITE_TTL_S,
        single_use: true,
        approval,
    });
    log.append(by, op, ts).unwrap();
    secret
}

fn join(log: &mut AclLog, who: &Device, secret: &[u8; 32], ts: u64) -> Result<String> {
    let s = log.state();
    let e = make_join(who, secret, &s.link_id, &s.head, s.head_seq, &who.id_hex()[..12], ts)?;
    let h = e.hash()?;
    log.insert(vec![e])?;
    match log.state().dropped.iter().find(|(d, _)| *d == h) {
        Some((_, why)) => Err(refused(why.clone())),
        None => Ok(h),
    }
}

fn accept(log: &mut AclLog, admin: &Device, join_hash: &str, ts: u64) {
    let s = log.state().clone();
    let root = &s.pending_joins[join_hash];
    let m = &s.members[root];
    let devices = if m.role.reads() {
        m.devices.clone()
    } else {
        BTreeSet::new()
    };
    let wraps = s.make_wraps(&key_of(log, admin).0, s.epoch, &devices).unwrap();
    log.append(
        admin,
        Op::Accept(Accept {
            join: join_hash.to_owned(),
            wraps,
        }),
        ts,
    )
    .unwrap();
}

/// Owner fleet A (2 devices) with partner B joined as `role` and admitted.
fn two_fleets(role: Role) -> (AclLog, Fleet, Fleet) {
    let a = Fleet::new(2, true);
    let b = Fleet::new(2, false);
    let (mut log, _) = genesis(a.d(0), "partners", "owner", Policy::default(), T0 + 1).unwrap();
    log.append(
        a.d(0),
        Op::AddDevice(add_device_op(&log, a.d(0), &a.devs[1].cert)),
        T0 + 2,
    )
    .unwrap();
    let secret = invite(&mut log, a.d(0), role, false, T0 + 3);
    let j = join(&mut log, b.d(0), &secret, T0 + 4).unwrap();
    accept(&mut log, a.d(0), &j, T0 + 5);
    (log, a, b)
}

fn add_device_op(log: &AclLog, author: &Device, cert: &DeviceCert) -> AddDevice {
    let s = log.state();
    let mut tmp = s.clone();
    tmp.devices.insert(
        cert.device.clone(),
        DeviceState {
            cert: cert.clone(),
            member: cert.root.clone(),
            cut: None,
        },
    );
    let wraps = tmp
        .make_wraps(&key_of(log, author).0, s.epoch, &[cert.device.clone()].into())
        .unwrap();
    AddDevice {
        cert: cert.clone(),
        wraps,
    }
}

#[test]
fn genesis_gives_the_owner_a_read_key_and_a_link_id() {
    let a = Fleet::new(1, true);
    let (log, g) = genesis(a.d(0), "partners", "owner", Policy::default(), T0 + 1).unwrap();
    assert_eq!(log.link_id(), g.hash().unwrap());
    assert_eq!(log.state().members[&a.root_hex()].role, Role::Owner);
    key_of(&log, a.d(0));
}

#[test]
fn invite_join_accept_gives_the_joiner_the_key() {
    let (log, _a, b) = two_fleets(Role::Writer);
    let s = log.state();
    let m = &s.members[&b.root_hex()];
    assert!(!m.pending && m.role == Role::Writer);
    assert!(s.pending_joins.is_empty());
    key_of(&log, b.d(0));
    assert!(s.sync_devices().contains(&b.d(0).id_hex()));
}

#[test]
fn an_invite_is_single_use_expires_and_can_be_revoked() {
    let a = Fleet::new(1, false);
    let b = Fleet::new(1, false);
    let c = Fleet::new(1, false);
    let (mut log, _) = genesis(a.d(0), "p", "owner", Policy::default(), T0 + 1).unwrap();
    let secret = invite(&mut log, a.d(0), Role::Writer, false, T0 + 2);
    join(&mut log, b.d(0), &secret, T0 + 3).unwrap();
    assert!(
        join(&mut log, c.d(0), &secret, T0 + 4).is_err(),
        "single-use invite used twice"
    );

    let late = invite(&mut log, a.d(0), Role::Writer, false, T0 + 5);
    assert!(
        join(&mut log, c.d(0), &late, T0 + 5 + DEFAULT_INVITE_TTL_S).is_err(),
        "expired invite"
    );

    let revoked = invite(&mut log, a.d(0), Role::Writer, false, T0 + 6);
    let invite_pub = hex(&crypto::public_of(&invite_key(&revoked)));
    log.append(a.d(0), Op::RevokeInvite(RevokeInvite { invite: invite_pub }), T0 + 7)
        .unwrap();
    assert!(join(&mut log, c.d(0), &revoked, T0 + 8).is_err(), "revoked invite");

    let wrong = crypto::random32();
    assert!(join(&mut log, c.d(0), &wrong, T0 + 9).is_err(), "unknown invite secret");
}

#[test]
fn an_approval_join_waits_and_can_be_declined() {
    let a = Fleet::new(1, false);
    let b = Fleet::new(1, false);
    let (mut log, _) = genesis(a.d(0), "p", "owner", Policy::default(), T0 + 1).unwrap();
    let secret = invite(&mut log, a.d(0), Role::Reader, true, T0 + 2);
    let j = join(&mut log, b.d(0), &secret, T0 + 3).unwrap();
    assert!(log.state().members[&b.root_hex()].pending);
    assert!(
        !log.state().sync_devices().contains(&b.d(0).id_hex()),
        "pending members do not sync"
    );
    log.append(a.d(0), Op::Decline(Decline { join: j }), T0 + 4).unwrap();
    assert!(log.state().members[&b.root_hex()].removed);
}

#[test]
fn roles_limit_who_may_append_what() {
    let (mut log, a, b) = two_fleets(Role::Writer);
    let secret = crypto::random32();
    let op = Op::Invite(Invite {
        invite: hex(&crypto::public_of(&invite_key(&secret))),
        role: Role::Reader,
        expires: T0 + 100,
        single_use: true,
        approval: false,
    });
    assert!(log.append(b.d(0), op, T0 + 10).is_err(), "a writer cannot invite");
    let set = Op::SetRole(SetRole {
        member: b.root_hex(),
        role: Role::Admin,
        wraps: vec![],
    });
    log.append(a.d(0), set, T0 + 11).unwrap();
    let c = Fleet::new(1, false);
    let secret = invite(&mut log, b.d(0), Role::Writer, false, T0 + 12);
    join(&mut log, c.d(0), &secret, T0 + 13).unwrap();
    let to_admin = Op::SetRole(SetRole {
        member: c.root_hex(),
        role: Role::Admin,
        wraps: vec![],
    });
    assert!(
        log.append(b.d(0), to_admin, T0 + 14).is_err(),
        "only the owner makes admins"
    );
    let remove_owner = Op::RemoveMember(RemoveMember {
        member: a.root_hex(),
        cut: BTreeMap::new(),
        rotate: None,
    });
    assert!(
        log.append(b.d(0), remove_owner, T0 + 15).is_err(),
        "nobody removes the owner"
    );
}

#[test]
fn removal_rotates_and_the_removed_device_cannot_read_new_keys() {
    let (mut log, a, b) = two_fleets(Role::Writer);
    let old_key = key_of(&log, b.d(0));
    let s = log.state().clone();
    let mut keyed = s.keyed_devices();
    keyed.retain(|d| *d != b.d(0).id_hex());
    let (change, new_key) = s.new_key_change(&key_of(&log, a.d(0)), &keyed).unwrap();
    let cut = [(b.d(0).id_hex(), 7)].into();
    log.append(
        a.d(0),
        Op::RemoveMember(RemoveMember {
            member: b.root_hex(),
            cut,
            rotate: Some(change),
        }),
        T0 + 10,
    )
    .unwrap();
    let s = log.state();
    assert_eq!(s.epoch, 1);
    assert!(
        s.read_key(1, &b.d(0).id_hex(), &b.d(0).kem).is_err(),
        "removed device has no wrap for epoch 1"
    );
    assert_eq!(s.read_key(1, &a.d(1).id_hex(), &a.d(1).kem).unwrap(), new_key);
    // History stays readable to remaining members through the chained previous key.
    assert_eq!(s.read_key(0, &a.d(1).id_hex(), &a.d(1).kem).unwrap(), old_key);
    assert_eq!(s.devices[&b.d(0).id_hex()].cut, Some(7));
    assert!(!s.sync_devices().contains(&b.d(0).id_hex()));
}

#[test]
fn leaving_marks_a_rotation_due_which_an_admin_appends() {
    let (mut log, a, b) = two_fleets(Role::Writer);
    let leave = Op::RemoveMember(RemoveMember {
        member: b.root_hex(),
        cut: BTreeMap::new(),
        rotate: None,
    });
    log.append(b.d(0), leave, T0 + 10).unwrap();
    assert!(log.state().rotation_due);
    let s = log.state().clone();
    let (change, _) = s.new_key_change(&key_of(&log, a.d(0)), &s.keyed_devices()).unwrap();
    log.append(a.d(0), Op::RotateKey(change), T0 + 11).unwrap();
    assert!(!log.state().rotation_due && log.state().epoch == 1);
}

#[test]
fn wraps_must_cover_exactly_the_readers() {
    let (mut log, a, b) = two_fleets(Role::Writer);
    let s = log.state().clone();
    let mut short = s.keyed_devices();
    short.remove(&b.d(0).id_hex());
    let (change, _) = s.new_key_change(&key_of(&log, a.d(0)), &short).unwrap();
    assert!(log.append(a.d(0), Op::RotateKey(change), T0 + 10).is_err());
}

#[test]
fn a_member_adds_and_renews_its_own_devices() {
    let (mut log, _a, b) = two_fleets(Role::Writer);
    let op = add_device_op(&log, b.d(0), &b.devs[1].cert);
    log.append(b.d(0), Op::AddDevice(op), T0 + 10).unwrap();
    key_of(&log, b.d(1));
    let mut renewed = Device::from_json(&b.d(1).to_json().unwrap()).unwrap();
    renewed.renew(&b.root, T0 + 50).unwrap();
    log.append(
        b.d(0),
        Op::AddDevice(AddDevice {
            cert: renewed.cert.clone(),
            wraps: vec![],
        }),
        T0 + 60,
    )
    .unwrap();
    assert_eq!(log.state().devices[&b.d(1).id_hex()].cert, renewed.cert);
}

#[test]
fn a_tampered_entry_is_refused() {
    let (log, a, _) = two_fleets(Role::Writer);
    let mut e = log.ordered().last().unwrap().1.clone();
    e.ts += 1;
    assert!(e.verify_signature().is_err());
    let mut fresh = AclLog::new();
    let mut all: Vec<Entry> = log.ordered().into_iter().map(|(_, e)| e.clone()).collect();
    all.last_mut().unwrap().body["join"] = Value::String("00".repeat(32));
    let n = all.len();
    assert_eq!(fresh.insert(all).unwrap(), n - 1, "the tampered entry alone is refused");
    assert_eq!(fresh.len(), n - 1);
    let _ = a;
}

#[test]
fn junk_that_was_never_valid_is_not_kept() {
    let (mut log, _a, _b) = two_fleets(Role::Writer);
    let stranger = Fleet::new(1, false);
    // A self-certified stranger signs a well-formed entry onto our head: it can never apply.
    let s = log.state().clone();
    let op = Op::RevokeInvite(RevokeInvite {
        invite: "ab".repeat(32),
    });
    let junk = Entry::sign(stranger.d(0), &s.link_id, s.head_seq + 1, &s.head, &op, T0 + 30).unwrap();
    let before = log.len();
    assert!(log.insert(vec![junk]).is_err());
    assert_eq!(log.len(), before, "a refused entry is neither stored nor relayed");
}

#[test]
fn entries_from_the_future_or_before_their_parent_are_refused() {
    let (mut log, a, _b) = two_fleets(Role::Writer);
    let s = log.state().clone();
    let op = Op::RevokeInvite(RevokeInvite {
        invite: "cd".repeat(32),
    });
    let early = Entry::sign(a.d(0), &s.link_id, s.head_seq + 1, &s.head, &op, T0).unwrap();
    assert!(log.insert(vec![early]).is_err(), "dated before its parent");
    let late = Entry::sign(a.d(0), &s.link_id, s.head_seq + 1, &s.head, &op, T0 + 100_000).unwrap();
    assert!(log.insert_at(vec![late], Some(T0 + 10)).is_err(), "dated in the future");
}

/// Entries of `log`, as a peer would receive them.
fn entries(log: &AclLog) -> Vec<Entry> {
    log.ordered().into_iter().map(|(_, e)| e.clone()).collect()
}

fn summary(log: &AclLog) -> String {
    let s = log.state();
    let members: Vec<String> = s
        .members
        .values()
        .map(|m| format!("{}:{:?}:{}:{}", &m.root[..8], m.role, m.pending, m.removed))
        .collect();
    format!(
        "{:?}|{:?}|{}|{}|{:?}",
        s.applied,
        members,
        s.epoch,
        s.head,
        s.dropped.iter().map(|d| &d.0).collect::<Vec<_>>()
    )
}

#[test]
fn two_admins_removing_each_other_resolve_the_same_everywhere() {
    let (mut base, a, b) = two_fleets(Role::Writer);
    base.append(
        a.d(0),
        Op::SetRole(SetRole {
            member: b.root_hex(),
            role: Role::Admin,
            wraps: vec![],
        }),
        T0 + 6,
    )
    .unwrap();
    let c = Fleet::new(1, false);
    let secret = invite(&mut base, a.d(0), Role::Admin, false, T0 + 7);
    let j = join(&mut base, c.d(0), &secret, T0 + 8).unwrap();
    accept(&mut base, a.d(0), &j, T0 + 9);

    // B and C, both admins but neither the owner, remove each other at the same head.
    let mut left = base.clone();
    let mut right = base.clone();
    let rm = |m: &Fleet| {
        Op::RemoveMember(RemoveMember {
            member: m.root_hex(),
            cut: BTreeMap::new(),
            rotate: None,
        })
    };
    let rm_c = left.append(b.d(0), rm(&c), T0 + 20);
    let rm_b = right.append(c.d(0), rm(&b), T0 + 20);
    // Only the owner may remove an admin, so both are refused at the source...
    assert!(rm_c.is_err() && rm_b.is_err());

    // ...and so the concurrent case that matters is the owner against an admin.
    let mut left = base.clone();
    let mut right = base.clone();
    left.append(a.d(0), rm(&b), T0 + 20).unwrap();
    let secret2 = crypto::random32();
    let by_b = Op::Invite(Invite {
        invite: hex(&crypto::public_of(&invite_key(&secret2))),
        role: Role::Writer,
        expires: T0 + 1_000,
        single_use: true,
        approval: false,
    });
    right.append(b.d(0), by_b, T0 + 20).unwrap();
    let mut x = AclLog::new();
    x.insert(entries(&left)).unwrap();
    x.insert(entries(&right)).unwrap();
    let mut y = AclLog::new();
    y.insert(entries(&right)).unwrap();
    y.insert(entries(&left)).unwrap();
    assert_eq!(summary(&x), summary(&y));
    assert!(x.state().members[&b.root_hex()].removed, "the owner's removal wins");
    assert_eq!(
        x.state().dropped.len(),
        1,
        "the removed admin's concurrent invite is dropped"
    );
}

#[test]
fn a_removal_beats_a_concurrent_action_by_the_removed_party() {
    let (base, a, b) = two_fleets(Role::Writer);
    // B (a writer) adds a device while A removes B, at the same head.
    let mut left = base.clone();
    let mut right = base.clone();
    left.append(
        a.d(0),
        Op::RemoveMember(RemoveMember {
            member: b.root_hex(),
            cut: BTreeMap::new(),
            rotate: None,
        }),
        T0 + 20,
    )
    .unwrap();
    let op = add_device_op(&right, b.d(0), &b.devs[1].cert);
    right.append(b.d(0), Op::AddDevice(op), T0 + 20).unwrap();
    for order in [[&left, &right], [&right, &left]] {
        let mut m = AclLog::new();
        m.insert(entries(order[0])).unwrap();
        m.insert(entries(order[1])).unwrap();
        assert!(m.state().members[&b.root_hex()].removed);
        assert!(!m.state().sync_devices().contains(&b.d(1).id_hex()));
    }
}

#[derive(Clone, Debug)]
enum Action {
    Invite(usize),
    Promote(usize),
    Demote(usize),
    Remove(usize),
    Rotate,
}

fn action() -> impl Strategy<Value = Action> {
    prop_oneof![
        (0usize..3).prop_map(Action::Invite),
        (0usize..3).prop_map(Action::Promote),
        (0usize..3).prop_map(Action::Demote),
        (0usize..3).prop_map(Action::Remove),
        Just(Action::Rotate),
    ]
}

/// Try one action by `fleets[by]` against `log`; refused actions are simply skipped.
fn act(log: &mut AclLog, fleets: &[Fleet], by: usize, a: &Action, ts: u64) {
    let dev = fleets[by].d(0);
    let target = |i: usize| fleets[(by + 1 + i) % fleets.len()].root_hex();
    let op = match a {
        Action::Invite(r) => Op::Invite(Invite {
            invite: hex(&crypto::random32()),
            role: [Role::Reader, Role::Writer, Role::Mailbox][*r],
            expires: ts + 100,
            single_use: true,
            approval: false,
        }),
        Action::Promote(t) => Op::SetRole(SetRole {
            member: target(*t),
            role: Role::Admin,
            wraps: vec![],
        }),
        Action::Demote(t) => Op::SetRole(SetRole {
            member: target(*t),
            role: Role::Writer,
            wraps: vec![],
        }),
        Action::Remove(t) => Op::RemoveMember(RemoveMember {
            member: target(*t),
            cut: BTreeMap::new(),
            rotate: None,
        }),
        Action::Rotate => {
            let s = log.state().clone();
            let Ok(key) = s.read_key(s.epoch, &dev.id_hex(), &dev.kem) else {
                return;
            };
            let Ok((change, _)) = s.new_key_change(&key, &s.keyed_devices()) else {
                return;
            };
            Op::RotateKey(change)
        }
    };
    let _ = log.append(dev, op, ts);
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 48, ..ProptestConfig::default() })]

    /// Three replicas append concurrently from one base, then exchange entries in arbitrary
    /// orders. Every replica must resolve to the same applied sequence, members and epoch.
    #[test]
    fn forks_resolve_identically_whatever_the_arrival_order(
        plans in proptest::collection::vec(proptest::collection::vec(action(), 1..4), 3),
        order in Just((0usize..3).collect::<Vec<_>>()).prop_shuffle(),
    ) {
        let (mut base, a, b) = two_fleets(Role::Writer);
        base.append(a.d(0), Op::SetRole(SetRole { member: b.root_hex(), role: Role::Admin, wraps: vec![] }), T0 + 6).unwrap();
        let c = Fleet::new(1, false);
        let secret = invite(&mut base, a.d(0), Role::Admin, false, T0 + 7);
        let j = join(&mut base, c.d(0), &secret, T0 + 8).unwrap();
        accept(&mut base, a.d(0), &j, T0 + 9);
        let fleets = [a, b, c];

        let mut replicas: Vec<AclLog> = (0..3).map(|_| base.clone()).collect();
        for (who, plan) in plans.iter().enumerate() {
            for (k, step) in plan.iter().enumerate() {
                act(&mut replicas[who], &fleets, who, step, T0 + 20 + k as u64);
            }
        }
        let mut merged: Vec<AclLog> = Vec::new();
        for start in 0..3 {
            let mut m = AclLog::new();
            for i in 0..3 {
                m.insert(entries(&replicas[order[(start + i) % 3]])).unwrap();
            }
            merged.push(m);
        }
        let mut rev = AclLog::new();
        for i in (0..3).rev() {
            rev.insert(entries(&replicas[order[i]])).unwrap();
        }
        merged.push(rev);
        let first = summary(&merged[0]);
        for m in &merged[1..] {
            prop_assert_eq!(&first, &summary(m));
        }
        prop_assert!(!merged[0].state().members[&fleets[0].root_hex()].removed, "the owner is never removed");
    }
}

#[test]
fn a_wrap_issued_beside_a_rotation_is_refused_not_misfiled() {
    let (mut base, a, b) = two_fleets(Role::Writer);
    base.append(
        a.d(0),
        Op::SetRole(SetRole {
            member: b.root_hex(),
            role: Role::Admin,
            wraps: vec![],
        }),
        T0 + 6,
    )
    .unwrap();
    let c = Fleet::new(1, false);
    let secret = invite(&mut base, a.d(0), Role::Mailbox, false, T0 + 7);
    let j = join(&mut base, c.d(0), &secret, T0 + 8).unwrap();
    let _ = j;
    // The owner rotates while admin B, at the same head, makes C a reader with epoch-0 wraps.
    let mut left = base.clone();
    let mut right = base.clone();
    let s = left.state().clone();
    let (change, _) = s.new_key_change(&key_of(&left, a.d(0)), &s.keyed_devices()).unwrap();
    left.append(a.d(0), Op::RotateKey(change), T0 + 20).unwrap();
    let s = right.state().clone();
    let wraps = s
        .make_wraps(&key_of(&right, b.d(0)).0, 0, &s.members[&c.root_hex()].devices)
        .unwrap();
    right
        .append(
            b.d(0),
            Op::SetRole(SetRole {
                member: c.root_hex(),
                role: Role::Reader,
                wraps,
            }),
            T0 + 20,
        )
        .unwrap();
    let mut m = AclLog::new();
    m.insert(entries(&left)).unwrap();
    m.insert(entries(&right)).unwrap();
    let st = m.state();
    assert_eq!(st.epoch, 1);
    assert_eq!(
        st.members[&c.root_hex()].role,
        Role::Mailbox,
        "the stale grant is dropped"
    );
    assert!(
        !st.wraps
            .get(&1)
            .is_some_and(|w| w.iter().any(|w| st.devices[&w.device].member == c.root_hex()))
    );
}
