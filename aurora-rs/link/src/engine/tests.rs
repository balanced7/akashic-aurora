use super::*;
use crate::identity::{new_phrase, root_from_phrase};
use crate::sync::{self, Frame, Session};

const T0: u64 = 10_000;

/// One fleet's device holding one link.
struct Node {
    dev: Device,
    link: Option<Link>,
}

impl Node {
    fn new(label: &str) -> Self {
        let root = root_from_phrase(&new_phrase()).unwrap();
        Self {
            dev: Device::create(&root, label, false, T0 - 10).unwrap(),
            link: None,
        }
    }
    fn id(&self) -> String {
        self.dev.id_hex()
    }
}

fn mail(kind: &str, text: &str) -> Body {
    Body {
        kind: kind.into(),
        seat: "claude".into(),
        to: "@any/codex".into(),
        content: text.into(),
        sent_at: T0,
        ..Body::default()
    }
}

/// Run a full session between two nodes until neither has anything left to say.
fn sync_pair(a: &mut Node, b: &mut Node, now: u64) {
    let (aid, bid) = (a.id(), b.id());
    let mut sa = Session::new();
    let mut sb = Session::new();
    let mut to_b = vec![sync::hello(a.link.as_ref().unwrap(), &a.dev).unwrap()];
    let mut to_a = vec![sync::hello(b.link.as_ref().unwrap(), &b.dev).unwrap()];
    for _ in 0..50 {
        if to_a.is_empty() && to_b.is_empty() {
            return;
        }
        for f in std::mem::take(&mut to_b) {
            let f = sync::decode(&sync::encode(&f).unwrap()[4..]).unwrap();
            let link = b.link.as_mut().unwrap();
            to_a.extend(sb.on_frame(link, &b.dev, &aid, f, now).unwrap().replies);
        }
        for f in std::mem::take(&mut to_a) {
            let link = a.link.as_mut().unwrap();
            to_b.extend(sa.on_frame(link, &a.dev, &bid, f, now).unwrap().replies);
        }
    }
    panic!("sync did not settle");
}

/// `host` (an admin) invites `guest` with `role`; the guest joins through frames.
fn admit(host: &mut Node, guest: &mut Node, role: Role, now: u64) {
    let secret = host
        .link
        .as_mut()
        .unwrap()
        .invite(&host.dev, role, 3600, true, false, now)
        .unwrap();
    let invite = hex(&crypto::public_of(&acl::invite_key(&secret)));
    let link_id = host.link.as_mut().unwrap().id().to_owned();
    let hdev = Device::from_json(&host.dev.to_json().unwrap()).unwrap();
    let Frame::Acl { entries } = sync::serve_join(
        host.link.as_mut().unwrap(),
        &hdev,
        Frame::JoinHello {
            v: 1,
            link: link_id,
            invite,
        },
        now,
    )
    .unwrap()
    .remove(0) else {
        panic!()
    };
    let entry = sync::join_entry(&entries, &guest.dev, &secret, "guest", now).unwrap();
    let Frame::Acl { entries } = sync::serve_join(host.link.as_mut().unwrap(), &hdev, Frame::Join { entry }, now)
        .unwrap()
        .remove(0)
    else {
        panic!()
    };
    guest.link = Some(Link::adopt(None, entries, now).unwrap());
}

fn trio() -> (Node, Node, Node) {
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    let mut m = Node::new("mailbox");
    a.link = Some(Link::create(None, &a.dev, "partners", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    admit(&mut a, &mut m, Role::Mailbox, T0 + 2);
    (a, b, m)
}

fn record_ids(n: &Node) -> BTreeSet<String> {
    let mut st = n
        .link
        .as_ref()
        .unwrap()
        .store
        .conn
        .prepare("SELECT id FROM records")
        .unwrap();
    st.query_map([], |r| r.get(0)).unwrap().map(|r| r.unwrap()).collect()
}

fn events(n: &Node) -> Vec<Value> {
    n.link.as_ref().unwrap().events_after(0, 1000).unwrap()
}

#[test]
fn a_join_over_frames_gives_the_guest_the_key() {
    let (a, b, _m) = trio();
    let s = b.link.as_ref().unwrap().state();
    assert_eq!(s.members[b.dev.root_hex()].role, Role::Writer);
    b.link.as_ref().unwrap().read_key(&b.dev, s.epoch).unwrap();
    assert!(
        b.link
            .as_ref()
            .unwrap()
            .acl
            .hashes()
            .is_subset(&a.link.as_ref().unwrap().acl.hashes())
    );
}

#[test]
fn partitioned_fleets_converge_with_no_duplicates_or_loss() {
    let (mut a, mut b, _m) = trio();
    for i in 0..5 {
        a.link
            .as_mut()
            .unwrap()
            .write(&a.dev, &mail("chat", &format!("a{i}")), T0 + 10)
            .unwrap();
        b.link
            .as_mut()
            .unwrap()
            .write(&b.dev, &mail("question", &format!("b{i}")), T0 + 10)
            .unwrap();
    }
    sync_pair(&mut a, &mut b, T0 + 20);
    assert_eq!(record_ids(&a), record_ids(&b));
    assert_eq!(record_ids(&a).len(), 10);
    let got: Vec<String> = events(&b)
        .iter()
        .map(|e| e["body"]["content"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(got, ["a0", "a1", "a2", "a3", "a4"]);
    assert_eq!(
        events(&b)[0]["fleet"],
        "fleet-a",
        "provenance comes from the ACL, not the body"
    );
    // A second sync changes nothing.
    sync_pair(&mut a, &mut b, T0 + 30);
    assert_eq!(record_ids(&a).len(), 10);
    assert_eq!(events(&b).len(), 5);
}

#[test]
fn tampering_gaps_and_equivocation_are_refused() {
    let (mut a, mut b, _m) = trio();
    let (_, r1) = a
        .link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "one"), T0 + 10)
        .unwrap();
    let (_, r2) = a
        .link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "two"), T0 + 10)
        .unwrap();
    let bdev = Device::from_json(&b.dev.to_json().unwrap()).unwrap();
    let acl = a.link.as_ref().unwrap().acl.missing_for(&BTreeSet::new());
    b.link.as_mut().unwrap().add_acl(acl, T0 + 11).unwrap();
    let mut t = r1.clone();
    t.epoch = 0;
    t.deps.push("ab".repeat(32));
    assert!(matches!(
        b.link.as_mut().unwrap().receive(&bdev, &t, T0 + 11).unwrap(),
        Admit::Refused(_)
    ));
    assert!(matches!(
        b.link.as_mut().unwrap().receive(&bdev, &r2, T0 + 11).unwrap(),
        Admit::Gap { have: 0, .. }
    ));
    assert!(matches!(
        b.link.as_mut().unwrap().receive(&bdev, &r1, T0 + 11).unwrap(),
        Admit::Stored { .. }
    ));
    assert_eq!(
        b.link.as_mut().unwrap().receive(&bdev, &r1, T0 + 11).unwrap(),
        Admit::Duplicate,
        "a replay is a no-op"
    );
    // A forges a second seq-2 record: equivocation freezes A.
    let key = a.link.as_mut().unwrap().read_key(&a.dev, 0).unwrap();
    let s = a.link.as_mut().unwrap().state().clone();
    let fork = Record::seal(
        &a.dev,
        Seal {
            link: &s.link_id,
            seq: 2,
            prev: &r1.id().unwrap(),
            deps: vec![],
            acl: &s.head,
            epoch: 0,
            key: &key.0,
        },
        &mail("chat", "two, again"),
        &s.policy().kinds,
    )
    .unwrap();
    assert!(matches!(
        b.link.as_mut().unwrap().receive(&bdev, &r2, T0 + 12).unwrap(),
        Admit::Stored { .. }
    ));
    assert!(matches!(
        b.link.as_mut().unwrap().receive(&bdev, &fork, T0 + 12).unwrap(),
        Admit::Refused(_)
    ));
    assert!(b.link.as_mut().unwrap().store.frozen(&a.id()).unwrap());
    assert_eq!(b.link.as_mut().unwrap().store.alarms().unwrap()[0].1, "equivocation");
    let (_, r3) = a
        .link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "three"), T0 + 13)
        .unwrap();
    assert!(
        matches!(
            b.link.as_mut().unwrap().receive(&bdev, &r3, T0 + 13).unwrap(),
            Admit::Refused(_)
        ),
        "a frozen author stays frozen"
    );
}

#[test]
fn a_mailbox_carries_mail_it_cannot_read_between_fleets_never_online_together() {
    let (mut a, mut b, mut m) = trio();
    // Everyone first learns the full membership.
    sync_pair(&mut a, &mut m, T0 + 3);
    sync_pair(&mut b, &mut m, T0 + 3);
    a.link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("handoff", "for b"), T0 + 10)
        .unwrap();
    sync_pair(&mut a, &mut m, T0 + 11); // a goes offline after this
    b.link
        .as_mut()
        .unwrap()
        .write(&b.dev, &mail("reply", "for a"), T0 + 12)
        .unwrap();
    sync_pair(&mut b, &mut m, T0 + 13); // b picks up a's mail, leaves its own
    sync_pair(&mut a, &mut m, T0 + 14); // a picks up b's mail
    assert_eq!(events(&b).len(), 1);
    assert_eq!(events(&a)[0]["body"]["content"], "for a");
    // The mailbox holds both, and could open neither.
    let mut st = m
        .link
        .as_ref()
        .unwrap()
        .store
        .conn
        .prepare("SELECT status, body FROM records")
        .unwrap();
    let rows: Vec<(String, Option<String>)> = st
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert_eq!(rows.len(), 2);
    assert!(rows.iter().all(|(s, b)| s == store::OPAQUE && b.is_none()));
    assert!(
        m.link.as_ref().unwrap().read_key(&m.dev, 0).is_err(),
        "a mailbox holds no read key"
    );
}

#[test]
fn a_third_fleet_relays_a_to_c() {
    let (mut a, mut b, _m) = trio();
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Writer, T0 + 3);
    sync_pair(&mut a, &mut b, T0 + 4);
    a.link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("note", "a to c"), T0 + 10)
        .unwrap();
    sync_pair(&mut a, &mut b, T0 + 11); // a leaves
    sync_pair(&mut b, &mut c, T0 + 12); // c never meets a
    assert_eq!(events(&c)[0]["body"]["content"], "a to c");
    assert_eq!(events(&c)[0]["device"], a.id());
}

#[test]
fn a_removed_fleet_cannot_read_new_mail_or_write_past_its_cut() {
    let (mut a, mut b, _m) = trio();
    sync_pair(&mut a, &mut b, T0 + 3);
    b.link
        .as_mut()
        .unwrap()
        .write(&b.dev, &mail("chat", "before"), T0 + 4)
        .unwrap();
    sync_pair(&mut a, &mut b, T0 + 5);
    let broot = b.dev.root_hex().to_owned();
    let adev = Device::from_json(&a.dev.to_json().unwrap()).unwrap();
    a.link.as_mut().unwrap().remove_member(&adev, &broot, T0 + 6).unwrap();
    assert_eq!(a.link.as_mut().unwrap().state().epoch, 1);
    a.link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "after"), T0 + 7)
        .unwrap();
    b.link
        .as_mut()
        .unwrap()
        .write(&b.dev, &mail("chat", "late"), T0 + 7)
        .unwrap();
    // B is no longer a member, so a session would be refused. Hand it the records directly.
    let after = a.link.as_mut().unwrap().missing_for(&BTreeMap::new(), 100).unwrap();
    let bdev = Device::from_json(&b.dev.to_json().unwrap()).unwrap();
    b.link
        .as_mut()
        .unwrap()
        .add_acl(a.link.as_mut().unwrap().acl.missing_for(&BTreeSet::new()), T0 + 8)
        .unwrap();
    for r in &after {
        let _ = b.link.as_mut().unwrap().receive(&bdev, r, T0 + 8).unwrap();
    }
    let opened: Vec<String> = events(&b)
        .iter()
        .filter_map(|e| e["body"]["content"].as_str().map(str::to_owned))
        .collect();
    assert!(
        !opened.contains(&"after".to_owned()),
        "epoch 1 is unreadable to the removed fleet"
    );
    let bid = b.id();
    let late = b.link.as_ref().unwrap().store.range(&bid, 1, 2).unwrap();
    assert_eq!(late.len(), 1);
    assert!(
        matches!(
            a.link.as_mut().unwrap().receive(&adev, &late[0], T0 + 9).unwrap(),
            Admit::Refused(_)
        ),
        "past the cut"
    );
}

#[test]
fn retention_drops_bodies_and_keeps_verifiable_headers() {
    let (mut a, mut b, _m) = trio();
    a.link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "old"), T0 + 10)
        .unwrap();
    sync_pair(&mut a, &mut b, T0 + 10);
    let later = T0 + 91 * 24 * 3600;
    assert_eq!(b.link.as_mut().unwrap().retire(later).unwrap(), 1);
    let r = b.link.as_mut().unwrap().missing_for(&BTreeMap::new(), 10).unwrap();
    assert!(r.iter().all(|r| r.ct.is_none()));
    r[0].verify().unwrap();
    assert!(events(&b)[0]["body"].is_null());
}

#[test]
fn acks_give_delivered_receipts() {
    let (mut a, mut b, _m) = trio();
    let (id, _) = a
        .link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("question", "q"), T0 + 10)
        .unwrap();
    sync_pair(&mut a, &mut b, T0 + 11);
    let bdev = Device::from_json(&b.dev.to_json().unwrap()).unwrap();
    b.link
        .as_mut()
        .unwrap()
        .ack(&bdev, vec![id.clone()], T0 + 12)
        .unwrap()
        .unwrap();
    assert!(
        b.link.as_mut().unwrap().ack(&bdev, vec![], T0 + 12).unwrap().is_none(),
        "nothing new to ack"
    );
    sync_pair(&mut a, &mut b, T0 + 13);
    let status = a.link.as_mut().unwrap().status(&a.dev, T0 + 13).unwrap();
    let receipts = status["sent"][0]["receipts"].as_str().unwrap().to_owned();
    assert!(
        receipts.contains("delivered") && receipts.contains("read"),
        "{receipts}"
    );
    assert_eq!(events(&a).len(), 0, "acks never surface as mail");
}

#[test]
fn self_monitoring_flags_a_device_we_never_certified() {
    let (mut a, _b, _m) = trio();
    let certified: BTreeSet<String> = BTreeSet::new();
    let rogue = a
        .link
        .as_mut()
        .unwrap()
        .self_monitor("", a.dev.root_hex(), &certified, T0)
        .unwrap();
    assert_eq!(rogue, vec![a.id()]);
    assert_eq!(
        a.link.as_mut().unwrap().store.alarms().unwrap()[0].1,
        "unknown_own_device"
    );
}

#[test]
fn the_store_survives_a_reopen() {
    let dir = std::env::temp_dir().join(format!("aurora-link-test-{}", hex(&crypto::random32())));
    let mut a = Node::new("a");
    let link = Link::create(Some(&dir), &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap();
    let path = link.path.clone().unwrap();
    a.link = Some(link);
    a.link
        .as_mut()
        .unwrap()
        .write(&a.dev, &mail("chat", "kept"), T0)
        .unwrap();
    drop(a.link.take());
    let back = Link::open(&path).unwrap();
    assert_eq!(back.heads().unwrap()[&a.id()], 1);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn a_second_machine_trusts_the_devices_that_added_it_but_not_later_ones() {
    let root = root_from_phrase(&new_phrase()).unwrap();
    let first = Device::create(&root, "first", false, T0 - 10).unwrap();
    let second = Device::create(&root, "second", false, T0 - 10).unwrap();
    let rogue = Device::create(&root, "rogue", false, T0 - 10).unwrap();
    let mut link = Link::create(None, &first, "p", "us", Policy::default(), T0).unwrap();
    let add = |link: &mut Link, by: &Device, d: &Device, t: u64| {
        let s = link.state().clone();
        let mut tmp = s.clone();
        tmp.devices.insert(
            d.id_hex(),
            acl::DeviceState {
                cert: d.cert.clone(),
                member: d.root_hex().into(),
                cut: None,
            },
        );
        let wraps = tmp
            .make_wraps(&link.read_key(by, s.epoch).unwrap().0, s.epoch, &[d.id_hex()].into())
            .unwrap();
        link.append(
            by,
            Op::AddDevice(acl::AddDevice {
                cert: d.cert.clone(),
                wraps,
            }),
            t,
        )
        .unwrap();
    };
    add(&mut link, &first, &second, T0 + 1);
    // The second machine certified only itself, yet the first device raises no alarm there.
    let mine: BTreeSet<String> = [second.id_hex()].into();
    assert!(
        link.self_monitor(&second.id_hex(), second.root_hex(), &mine, T0 + 2)
            .unwrap()
            .is_empty()
    );
    // A device added under our root afterwards, which neither machine certified, does.
    add(&mut link, &first, &rogue, T0 + 3);
    let flagged = link
        .self_monitor(&second.id_hex(), second.root_hex(), &mine, T0 + 4)
        .unwrap();
    assert_eq!(flagged, vec![rogue.id_hex()]);
}
