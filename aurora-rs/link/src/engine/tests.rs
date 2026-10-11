use super::*;
use crate::identity::{new_phrase, root_from_phrase};
use crate::sync::{self, Frame, JoinDoor, Session};

const T0: u64 = 10_000;
const DAY: u64 = 24 * 3600;

/// One fleet's device holding one link.
struct Node {
    dev: Device,
    link: Option<Link>,
    root: ed25519_dalek::SigningKey,
}

impl Node {
    fn new(label: &str) -> Self {
        let root = root_from_phrase(&new_phrase()).unwrap();
        Self {
            dev: Device::create(&root, label, false, T0 - 10).unwrap(),
            link: None,
            root,
        }
    }
    fn id(&self) -> String {
        self.dev.id_hex()
    }
}

fn clone_dev(n: &Node) -> Device {
    Device::from_json(&n.dev.to_json().unwrap()).unwrap()
}

fn link_of(n: &mut Node) -> &mut Link {
    n.link.as_mut().unwrap()
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

/// Run a full session between two nodes until neither has anything left to say, or one side
/// closes it (refuses a frame, as for a peer that just left). Returns every frame that crossed,
/// encoded.
fn sync_pair(a: &mut Node, b: &mut Node, now: u64) -> Vec<Vec<u8>> {
    let (aid, bid) = (a.id(), b.id());
    let (adev, bdev) = (clone_dev(a), clone_dev(b));
    let mut sa = Session::new();
    let mut sb = Session::new();
    let mut to_b = sync::hello(a.link.as_ref().unwrap(), &a.dev).unwrap();
    let mut to_a = sync::hello(b.link.as_ref().unwrap(), &b.dev).unwrap();
    let mut wire = Vec::new();
    for _ in 0..200 {
        if to_a.is_empty() && to_b.is_empty() {
            return wire;
        }
        for f in std::mem::take(&mut to_b) {
            let bytes = sync::encode(&f).unwrap();
            let f = sync::decode(&bytes[4..]).unwrap();
            wire.push(bytes);
            match sb.on_frame(link_of(b), &bdev, &aid, f, now) {
                Ok(out) => to_a.extend(out.replies),
                Err(_) => return wire,
            }
        }
        for f in std::mem::take(&mut to_a) {
            let bytes = sync::encode(&f).unwrap();
            let f = sync::decode(&bytes[4..]).unwrap();
            wire.push(bytes);
            match sa.on_frame(link_of(a), &adev, &bid, f, now) {
                Ok(out) => to_b.extend(out.replies),
                Err(_) => return wire,
            }
        }
    }
    panic!("sync did not settle");
}

/// All ACL entries in a join reply (it ends with `synced`).
fn entries_of(frames: Vec<Frame>) -> Vec<acl::Entry> {
    assert!(matches!(frames.last(), Some(Frame::Synced { .. })), "{frames:?}");
    frames
        .into_iter()
        .flat_map(|f| match f {
            Frame::Acl { entries } => entries,
            _ => vec![],
        })
        .collect()
}

/// `host` (the sequencer) invites `guest` with `role`; the guest joins through frames.
fn admit(host: &mut Node, guest: &mut Node, role: Role, now: u64) {
    let hdev = clone_dev(host);
    let secret = link_of(host).invite(&hdev, role, 3600, true, false, now).unwrap();
    let link_id = link_of(host).id().to_owned();
    let gid = guest.id();
    let hello = sync::join_hello(&link_id, &guest.dev, &secret).unwrap();
    let mut door = JoinDoor::new();
    let entries = entries_of(door.on_frame(link_of(host), &hdev, &gid, hello, now).unwrap());
    let proposal = sync::join_proposal(&entries, &guest.dev, &secret, &guest.dev.cert.label.clone(), now).unwrap();
    let entries = entries_of(
        door.on_frame(link_of(host), &hdev, &gid, Frame::Join { proposal }, now)
            .unwrap(),
    );
    guest.link = Some(Link::adopt(None, entries, now).unwrap());
}

/// Every chain entry of `from` that `to` lacks.
fn give_acl(from: &Node, to: &mut Node, now: u64) {
    let all = from.link.as_ref().unwrap().acl.all();
    let _ = link_of(to).add_acl(all, now);
}

/// A (owner, sequencer), B (writer) and M (mailbox).
fn trio() -> (Node, Node, Node) {
    trio_with(Policy::default())
}

fn trio_with(policy: Policy) -> (Node, Node, Node) {
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    let mut m = Node::new("mailbox");
    a.link = Some(Link::create(None, &a.dev, "partners", "fleet-a", policy, T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    admit(&mut a, &mut m, Role::Mailbox, T0 + 2);
    give_acl(&a, &mut b, T0 + 2);
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

fn status_of(n: &Node, id: &str) -> (String, Option<String>) {
    let sr = n.link.as_ref().unwrap().store.get(id).unwrap().unwrap();
    (sr.status, sr.reason)
}

fn is_admitted(a: &Admit) -> bool {
    matches!(a, Admit::Stored { status, .. } if status == store::ADMITTED)
}

#[test]
fn the_join_protocol_checks_before_it_stores() {
    let mut a = Node::new("a");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    let adev = clone_dev(&a);
    let secret = link_of(&mut a)
        .invite(&adev, Role::Writer, 3600, true, false, T0)
        .unwrap();
    let link_id = link_of(&mut a).id().to_owned();
    let guest = Node::new("guest");
    let thief = Node::new("thief");
    // A hello bound to another connection, or after expiry by our clock, gets nothing.
    let hello = sync::join_hello(&link_id, &guest.dev, &secret).unwrap();
    assert!(
        JoinDoor::new()
            .on_frame(link_of(&mut a), &adev, &thief.id(), hello.clone(), T0)
            .is_err()
    );
    assert!(
        JoinDoor::new()
            .on_frame(link_of(&mut a), &adev, &guest.id(), hello.clone(), T0 + 7200)
            .is_err()
    );
    // A join handed in after expiry is refused, even on a stream whose hello was verified in time.
    let entries = link_of(&mut a).acl.all();
    let late = sync::join_proposal(&entries, &guest.dev, &secret, "guest", T0).unwrap();
    let before = link_of(&mut a).acl.len();
    let mut door = JoinDoor::new();
    door.on_frame(link_of(&mut a), &adev, &guest.id(), hello, T0 + 10)
        .unwrap();
    assert!(
        door.on_frame(
            link_of(&mut a),
            &adev,
            &guest.id(),
            Frame::Join { proposal: late.clone() },
            T0 + 7200
        )
        .is_err()
    );
    assert_eq!(link_of(&mut a).acl.len(), before, "nothing was stored");
    // Someone else's join proposal, on our connection (after our own valid hello), is refused.
    let mut door = JoinDoor::new();
    let thief_hello = sync::join_hello(&link_id, &thief.dev, &secret).unwrap();
    door.on_frame(link_of(&mut a), &adev, &thief.id(), thief_hello, T0 + 20)
        .unwrap();
    assert!(
        door.on_frame(
            link_of(&mut a),
            &adev,
            &thief.id(),
            Frame::Join { proposal: late },
            T0 + 20
        )
        .is_err()
    );
    assert_eq!(link_of(&mut a).acl.len(), before, "nothing was stored");
}

#[test]
fn a_join_over_frames_gives_the_guest_the_key() {
    let (mut a, b, _m) = trio();
    let s = b.link.as_ref().unwrap().state();
    assert_eq!(s.members[b.dev.root_hex()].role, Role::Writer);
    b.link.as_ref().unwrap().read_key(&b.dev, s.epoch).unwrap();
    assert_eq!(b.link.as_ref().unwrap().acl.tip(), link_of(&mut a).acl.tip());
}

#[test]
fn partitioned_fleets_converge_with_no_duplicates_or_loss() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    for i in 0..5 {
        link_of(&mut a)
            .write(&adev, &mail("chat", &format!("a{i}")), T0 + 10)
            .unwrap();
        link_of(&mut b)
            .write(&bdev, &mail("question", &format!("b{i}")), T0 + 10)
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
    sync_pair(&mut a, &mut b, T0 + 30);
    assert_eq!(record_ids(&a).len(), 10);
    assert_eq!(events(&b).len(), 5);
}

#[test]
fn tampering_gaps_and_equivocation_are_refused() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let (_, r1) = link_of(&mut a).write(&adev, &mail("chat", "one"), T0 + 10).unwrap();
    let (_, r2) = link_of(&mut a).write(&adev, &mail("chat", "two"), T0 + 10).unwrap();
    let mut t = r1.clone();
    t.deps.push("ab".repeat(32));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &t, T0 + 11).unwrap(),
        Admit::Refused(_)
    ));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r2, T0 + 11).unwrap(),
        Admit::Gap { have: 0, .. }
    ));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r1, T0 + 11).unwrap(),
        Admit::Stored { .. }
    ));
    assert_eq!(link_of(&mut b).receive(&bdev, &r1, T0 + 11).unwrap(), Admit::Duplicate);
    // A forges a second seq-2 record: equivocation freezes A.
    let key = link_of(&mut a).read_key(&adev, 0).unwrap();
    let s = link_of(&mut a).state().clone();
    let fork = Record::seal(
        &adev,
        Seal {
            link: &s.link_id,
            seq: 2,
            ts: T0 + 12,
            prev: &r1.id().unwrap(),
            deps: vec![],
            acl: &s.pos(),
            epoch: 0,
            key: &key.0,
        },
        &mail("chat", "two, again"),
        &s.policy().kinds,
    )
    .unwrap();
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r2, T0 + 12).unwrap(),
        Admit::Stored { .. }
    ));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &fork, T0 + 12).unwrap(),
        Admit::Refused(_)
    ));
    assert!(link_of(&mut b).store.frozen(&a.id()).unwrap());
    assert_eq!(link_of(&mut b).store.alarms().unwrap()[0].1, "equivocation");
    let (_, r3) = link_of(&mut a).write(&adev, &mail("chat", "three"), T0 + 13).unwrap();
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r3, T0 + 13).unwrap(),
        Admit::Refused(_)
    ));
}

#[test]
fn a_mailbox_carries_mail_it_cannot_read_between_fleets_never_online_together() {
    let (mut a, mut b, mut m) = trio();
    sync_pair(&mut a, &mut m, T0 + 3);
    sync_pair(&mut b, &mut m, T0 + 3);
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    link_of(&mut a)
        .write(&adev, &mail("handoff", "for b"), T0 + 10)
        .unwrap();
    sync_pair(&mut a, &mut m, T0 + 11);
    link_of(&mut b).write(&bdev, &mail("reply", "for a"), T0 + 12).unwrap();
    sync_pair(&mut b, &mut m, T0 + 13);
    sync_pair(&mut a, &mut m, T0 + 14);
    assert_eq!(events(&b).len(), 1);
    assert_eq!(events(&a)[0]["body"]["content"], "for a");
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
    let adev = clone_dev(&a);
    link_of(&mut a).write(&adev, &mail("note", "a to c"), T0 + 10).unwrap();
    sync_pair(&mut a, &mut b, T0 + 11);
    sync_pair(&mut b, &mut c, T0 + 12);
    assert_eq!(events(&c)[0]["body"]["content"], "a to c");
    assert_eq!(events(&c)[0]["device"], a.id());
}

#[test]
fn a_removed_fleet_cannot_read_new_mail_or_write_past_its_cut() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    link_of(&mut b).write(&bdev, &mail("chat", "before"), T0 + 4).unwrap();
    sync_pair(&mut a, &mut b, T0 + 5);
    let broot = b.dev.root_hex().to_owned();
    let e = link_of(&mut a).remove_member(&adev, &broot, T0 + 6).unwrap();
    // The cut is B's feed head as the sequencer holds it.
    assert_eq!(e.entry().unwrap().cuts.get(&b.id()), Some(&1));
    assert_eq!(link_of(&mut a).state().epoch, 1);
    link_of(&mut a).write(&adev, &mail("chat", "after"), T0 + 7).unwrap();
    link_of(&mut b).write(&bdev, &mail("chat", "late"), T0 + 7).unwrap();
    let after = link_of(&mut a).missing_for(&BTreeMap::new(), 100).unwrap();
    give_acl(&a, &mut b, T0 + 8);
    for r in &after {
        let _ = link_of(&mut b).receive(&bdev, r, T0 + 8).unwrap();
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
    let late = b.link.as_ref().unwrap().store.range(&bid, 1, 2, 1).unwrap();
    assert!(
        matches!(
            link_of(&mut a).receive(&adev, &late[0], T0 + 9).unwrap(),
            Admit::Refused(_)
        ),
        "past the cut"
    );
}

#[test]
fn retention_drops_bodies_and_keeps_verifiable_headers() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    link_of(&mut a).write(&adev, &mail("chat", "old"), T0 + 10).unwrap();
    sync_pair(&mut a, &mut b, T0 + 10);
    let later = T0 + 91 * DAY;
    assert_eq!(link_of(&mut b).retire(later).unwrap(), 1);
    let r = link_of(&mut b).missing_for(&BTreeMap::new(), 10).unwrap();
    assert!(r.iter().all(|r| r.ct.is_none()));
    r[0].verify().unwrap();
    assert!(events(&b)[0]["body"].is_null());
}

#[test]
fn acks_give_delivered_receipts() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let (id, _) = link_of(&mut a).write(&adev, &mail("question", "q"), T0 + 10).unwrap();
    sync_pair(&mut a, &mut b, T0 + 11);
    link_of(&mut b).ack(&bdev, vec![id.clone()], T0 + 12).unwrap().unwrap();
    assert!(
        link_of(&mut b).ack(&bdev, vec![], T0 + 12).unwrap().is_none(),
        "nothing new to ack"
    );
    sync_pair(&mut a, &mut b, T0 + 13);
    let status = link_of(&mut a).status(&adev, T0 + 13).unwrap();
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
    let root = a.dev.root_hex().to_owned();
    let rogue = link_of(&mut a).self_monitor("", &root, &BTreeSet::new(), T0).unwrap();
    assert_eq!(rogue, vec![a.id()]);
    assert_eq!(link_of(&mut a).store.alarms().unwrap()[0].1, "unknown_own_device");
}

#[test]
fn the_store_survives_a_reopen() {
    let dir = std::env::temp_dir().join(format!("aurora-link-test-{}", hex(&crypto::random32())));
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    let link = Link::create(Some(&dir), &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap();
    let path = link.path.clone().unwrap();
    a.link = Some(link);
    admit(&mut a, &mut b, Role::Admin, T0 + 1);
    let adev = clone_dev(&a);
    link_of(&mut a).write(&adev, &mail("chat", "kept"), T0 + 2).unwrap();
    let before = link_of(&mut a).status(&adev, T0 + 3).unwrap();
    drop(a.link.take());
    let back = Link::open(&path).unwrap();
    assert_eq!(back.heads().unwrap()[&a.id()], 1);
    let after = back.status(&adev, T0 + 3).unwrap();
    for k in ["acl_tip", "acl_entries", "members", "sequencer", "epoch"] {
        assert_eq!(before[k], after[k], "{k}");
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn a_second_machine_trusts_the_devices_that_added_it_but_not_later_ones() {
    let root = root_from_phrase(&new_phrase()).unwrap();
    let first = Device::create(&root, "first", false, T0 - 10).unwrap();
    let second = Device::create(&root, "second", false, T0 - 10).unwrap();
    let rogue = Device::create(&root, "rogue", false, T0 - 10).unwrap();
    let mut link = Link::create(None, &first, "p", "us", Policy::default(), T0).unwrap();
    link.add_device(&first, second.cert.clone(), T0 + 1).unwrap();
    let mine: BTreeSet<String> = [second.id_hex()].into();
    assert!(
        link.self_monitor(&second.id_hex(), second.root_hex(), &mine, T0 + 2)
            .unwrap()
            .is_empty()
    );
    link.add_device(&first, rogue.cert.clone(), T0 + 3).unwrap();
    let flagged = link
        .self_monitor(&second.id_hex(), second.root_hex(), &mine, T0 + 4)
        .unwrap();
    assert_eq!(flagged, vec![rogue.id_hex()]);
}

#[test]
fn a_relay_cannot_strip_a_body_and_another_fleets_ack_is_only_a_receipt() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let (_, r) = link_of(&mut a).write(&adev, &mail("chat", "keep me"), T0 + 10).unwrap();
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r.retired(), T0 + 11).unwrap(),
        Admit::Refused(_)
    ));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r, T0 + 11).unwrap(),
        Admit::Stored { .. }
    ));
    assert_eq!(events(&b)[0]["body"]["content"], "keep me");
    let ack = link_of(&mut b).ack(&bdev, vec![], T0 + 12).unwrap().unwrap();
    sync_pair(&mut a, &mut b, T0 + 13);
    assert_eq!(status_of(&a, &ack).0, store::RECEIPT);
}

#[test]
fn a_permanent_gap_does_not_loop() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    let aid = a.id();
    link_of(&mut b).store.freeze(&aid, "test", T0).unwrap();
    for i in 0..3 {
        link_of(&mut a)
            .write(&adev, &mail("chat", &format!("{i}")), T0 + 4)
            .unwrap();
    }
    sync_pair(&mut a, &mut b, T0 + 5);
}

/// A joiner that cuts its own device before its accept must not stall upkeep (finding A4).
#[test]
fn upkeep_wraps_only_live_devices_and_still_rotates() {
    let mut a = Node::new("a");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    let adev = clone_dev(&a);
    let mut g = Node::new("g");
    let gdev = clone_dev(&g);
    let secret = link_of(&mut a)
        .invite(&adev, Role::Writer, 3600, true, false, T0 + 1)
        .unwrap();
    let join = sync::join_proposal(&link_of(&mut a).acl.all(), &gdev, &secret, "g", T0).unwrap();
    // The join lands without the sequencer's upkeep, so its accept is still owed.
    assert!(matches!(
        link_of(&mut a).offer(&adev, &join, T0 + 2).unwrap(),
        Offered::Included(_)
    ));
    assert_eq!(link_of(&mut a).state().pending_joins.len(), 1);
    g.link = Some(Link::adopt(None, link_of(&mut a).acl.all(), T0 + 2).unwrap());
    let gid = g.id();
    // G is no member device yet (pending accept), so it cannot propose: the owner removes it,
    // rotating in the same entry.
    link_of(&mut a).remove_device(&adev, &gid, T0 + 3).unwrap();
    assert!(!link_of(&mut a).state().rotation_due);
    let out = link_of(&mut a).upkeep(&adev, T0 + 4).unwrap();
    let s = link_of(&mut a).state();
    assert!(
        s.pending_joins.is_empty(),
        "the accept went through, wrapping to no cut device"
    );
    assert_eq!(s.epoch, 1);
    assert_eq!(out.len(), 1);
}

/// While a rotation is due, nobody seals under the old epoch; the sequencer rotates (A5).
#[test]
fn writers_wait_while_a_rotation_is_due() {
    let (mut a, mut b, _m) = trio();
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Writer, T0 + 3);
    give_acl(&a, &mut b, T0 + 4);
    let broot = b.dev.root_hex().to_owned();
    let bdev = clone_dev(&b);
    // A writer that leaves cannot pick the next key; its leave is a proposal.
    let acted = link_of(&mut b).remove_member(&bdev, &broot, T0 + 5).unwrap();
    assert!(acted.proposal().is_some());
    sync_pair(&mut b, &mut a, T0 + 5);
    assert!(link_of(&mut a).state().rotation_due);
    give_acl(&a, &mut c, T0 + 6);
    let cdev = clone_dev(&c);
    let err = link_of(&mut c)
        .write(&cdev, &mail("chat", "too soon"), T0 + 6)
        .unwrap_err();
    assert!(err.to_string().contains("rotation"), "{err}");
    let adev = clone_dev(&a);
    let (_, r) = link_of(&mut a)
        .write(&adev, &mail("chat", "rotated first"), T0 + 7)
        .unwrap();
    assert_eq!(r.epoch, 1);
    give_acl(&a, &mut c, T0 + 8);
    let (_, r) = link_of(&mut c).write(&cdev, &mail("chat", "now"), T0 + 8).unwrap();
    assert_eq!(r.epoch, 1);
}

/// A7 and L1: retention is judged by the record's own signed time.
#[test]
fn a_stripped_copy_is_judged_by_its_write_time_and_never_refilled_past_retention() {
    let policy = Policy {
        retention_days: 1,
        ..Policy::default()
    };
    let (mut a, mut b, mut m) = trio_with(policy);
    give_acl(&a, &mut m, T0 + 3);
    let w = T0 + 2 * DAY;
    let adev = clone_dev(&a);
    let (id, r) = link_of(&mut a).write(&adev, &mail("chat", "fresh"), w).unwrap();
    let bdev = clone_dev(&b);
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r.retired(), w + 5).unwrap(),
        Admit::Refused(_)
    ));
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r, w + 5).unwrap(),
        Admit::Stored { .. }
    ));
    let mdev = clone_dev(&m);
    let late = w + DAY + 10;
    assert!(matches!(
        link_of(&mut m).receive(&mdev, &r.retired(), late).unwrap(),
        Admit::Stored { .. }
    ));
    assert_eq!(link_of(&mut m).receive(&mdev, &r, late + 1).unwrap(), Admit::Duplicate);
    assert!(
        m.link
            .as_ref()
            .unwrap()
            .store
            .get(&id)
            .unwrap()
            .unwrap()
            .record
            .ct
            .is_none()
    );
}

/// A8: a record needs a certificate valid at its signed write time, and a sane time.
#[test]
fn records_need_a_certificate_valid_at_their_signed_time() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let (_, r1) = link_of(&mut a)
        .write(&adev, &mail("chat", "while certified"), T0 + 10)
        .unwrap();
    let expiry = a.dev.cert.not_after;
    assert!(matches!(
        link_of(&mut b).receive(&bdev, &r1, expiry + 10).unwrap(),
        Admit::Stored { .. }
    ));
    assert!(
        link_of(&mut a)
            .write(&adev, &mail("chat", "expired"), expiry + 1)
            .is_err()
    );
    let key = link_of(&mut a).read_key(&adev, 0).unwrap();
    let s = link_of(&mut a).state().clone();
    let prev = r1.id().unwrap();
    let forge = |ts: u64| {
        Record::seal(
            &adev,
            Seal {
                link: &s.link_id,
                seq: 2,
                ts,
                prev: &prev,
                deps: vec![],
                acl: &s.pos(),
                epoch: 0,
                key: &key.0,
            },
            &mail("chat", "forged"),
            &s.policy().kinds,
        )
        .unwrap()
    };
    let link = link_of(&mut b);
    for (ts, now, why) in [
        (expiry + 5, expiry + 10, "written after the certificate expired"),
        (T0 + 10_000, T0 + 20, "dated in the future"),
        (T0 + 5, T0 + 20, "dated before its predecessor"),
    ] {
        assert!(
            matches!(link.receive(&bdev, &forge(ts), now).unwrap(), Admit::Refused(_)),
            "{why}"
        );
    }
    assert!(!link.store.frozen(&a.id()).unwrap());
    assert!(matches!(
        link.receive(&bdev, &forge(T0 + 15), T0 + 20).unwrap(),
        Admit::Stored { .. }
    ));
}

fn with_blobs(text: &str, blobs: Vec<crate::record::BlobRef>) -> Body {
    Body {
        blobs,
        ..mail("note", text)
    }
}

fn big_blob(bytes: u64) -> crate::record::BlobRef {
    let (mut r, _) = crate::record::seal_blob("big", b"");
    r.id = hex(&crypto::random32());
    r.bytes = bytes;
    r
}

/// A9: blobs are listed from admitted bodies only, within caps, per link.
#[test]
fn blobs_are_listed_only_from_admitted_bodies_and_within_caps() {
    use crate::record::{MAX_BLOB_BYTES, blob_ct_len, seal_blob};
    let (mut a, mut b, mut m) = trio();
    let mut rd = Node::new("reader");
    admit(&mut a, &mut rd, Role::Reader, T0 + 3);
    sync_pair(&mut a, &mut b, T0 + 4);
    sync_pair(&mut a, &mut m, T0 + 4);
    let adev = clone_dev(&a);
    let (real, _) = seal_blob("playbook.md", b"# steps");
    link_of(&mut a)
        .write(&adev, &with_blobs("see attached", vec![real.clone()]), T0 + 10)
        .unwrap();
    assert!(link_of(&mut a).blob_allowed(&real.id).unwrap());
    sync_pair(&mut a, &mut b, T0 + 11);
    let bl = b.link.as_ref().unwrap();
    assert!(bl.blob_allowed(&real.id).unwrap());
    assert_eq!(bl.wanted_blobs().unwrap(), vec![(real.id.clone(), blob_ct_len(7))]);
    // A reader's mail is withheld, and its blobs are never listed.
    let (smuggled, _) = seal_blob("x", b"x");
    let rl = rd.link.as_ref().unwrap();
    let s = rl.state().clone();
    let key = rl.read_key(&rd.dev, s.epoch).unwrap();
    let forged = Record::seal(
        &rd.dev,
        Seal {
            link: &s.link_id,
            seq: 1,
            ts: T0 + 20,
            prev: "",
            deps: vec![],
            acl: &s.pos(),
            epoch: s.epoch,
            key: &key.0,
        },
        &with_blobs("not allowed", vec![smuggled.clone()]),
        &s.policy().kinds,
    )
    .unwrap();
    give_acl(&a, &mut b, T0 + 21);
    let bdev = clone_dev(&b);
    let got = link_of(&mut b).receive(&bdev, &forged, T0 + 21).unwrap();
    assert!(
        matches!(got, Admit::Stored { ref status, .. } if status == store::WITHHELD),
        "{got:?}"
    );
    assert!(!link_of(&mut b).blob_allowed(&smuggled.id).unwrap());
    let mut written = 0;
    for i in 0..10 {
        let refs = (0..3).map(|_| big_blob(MAX_BLOB_BYTES)).collect();
        match link_of(&mut a).write(&adev, &with_blobs(&format!("big {i}"), refs), T0 + 30) {
            Ok(_) => written += 1,
            Err(e) => {
                assert!(e.to_string().contains("attachment"), "{e}");
                break;
            }
        }
    }
    assert_eq!(written, 5, "1 GiB holds five records of three 64 MiB blobs");
    sync_pair(&mut a, &mut m, T0 + 31);
    let ml = m.link.as_ref().unwrap();
    assert_eq!(ml.wanted_blobs().unwrap().len(), 4, "the small blob and one big record");
    assert!(ml.store.alarms().unwrap().iter().any(|x| x.1 == "blob_cap"));
}

/// M3: an expired, never-removed key delivers no content once the retention has passed, and a
/// record dated inside its lifetime cannot name a position from after it.
#[test]
fn m3_an_expired_never_removed_key_delivers_no_content() {
    let policy = Policy {
        retention_days: 1,
        ..Policy::default()
    };
    let (mut a, mut b, _m) = trio_with(policy);
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let expiry = b.dev.cert.not_after;
    let s = link_of(&mut b).state().clone();
    let key = link_of(&mut b).read_key(&bdev, s.epoch).unwrap();
    let forge = |ts: u64, pos: &acl::AclPos, epoch: u64| {
        Record::seal(
            &bdev,
            Seal {
                link: &s.link_id,
                seq: 1,
                ts,
                prev: "",
                deps: vec![],
                acl: pos,
                epoch,
                key: &key.0,
            },
            &mail("chat", "stolen"),
            &s.policy().kinds,
        )
        .unwrap()
    };
    let r = forge(expiry - 100, &s.pos(), s.epoch);
    let got = link_of(&mut a).receive(&adev, &r, expiry + 2 * DAY).unwrap();
    assert!(
        matches!(got, Admit::Stored { ref status, .. } if status == store::OPAQUE),
        "{got:?}"
    );
    assert!(events(&a).is_empty());
    // A record dated long before the position it names is refused.
    let (mut a2, mut b2, _m2) = trio_with(Policy {
        retention_days: 1,
        ..Policy::default()
    });
    let (adev2, bdev2) = (clone_dev(&a2), clone_dev(&b2));
    let late_entry = T0 + 3 * DAY;
    link_of(&mut a2)
        .invite(&adev2, Role::Reader, 3600, true, false, late_entry)
        .unwrap();
    give_acl(&a2, &mut b2, late_entry);
    let s2 = link_of(&mut b2).state().clone();
    let key2 = link_of(&mut b2).read_key(&bdev2, s2.epoch).unwrap();
    let r3 = Record::seal(
        &bdev2,
        Seal {
            link: &s2.link_id,
            seq: 1,
            ts: T0 + 5,
            prev: "",
            deps: vec![],
            acl: &s2.pos(),
            epoch: s2.epoch,
            key: &key2.0,
        },
        &mail("chat", "old"),
        &s2.policy().kinds,
    )
    .unwrap();
    let got = link_of(&mut a2).receive(&adev2, &r3, late_entry + 10).unwrap();
    assert!(
        matches!(got, Admit::Refused(ref why) if why.contains("before the ACL position")),
        "{got:?}"
    );
}

/// L2: one blob id listed with two different sizes is refused.
#[test]
fn l2_a_blob_listed_with_another_size_is_refused() {
    let (mut a, _b, _m) = trio();
    let adev = clone_dev(&a);
    let small = big_blob(10);
    link_of(&mut a)
        .write(&adev, &with_blobs("first", vec![small.clone()]), T0 + 10)
        .unwrap();
    let mut bigger = small.clone();
    bigger.bytes = 1 << 20;
    let err = link_of(&mut a)
        .write(&adev, &with_blobs("again", vec![bigger]), T0 + 11)
        .unwrap_err();
    assert!(err.to_string().contains("another size"), "{err}");
}

/// A (owner, sequencer), B and C (writers) and M (mailbox), all holding one chain.
fn quartet() -> (Node, Node, Node, Node) {
    let (mut a, mut b, mut m) = trio();
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Writer, T0 + 3);
    for n in [&mut b, &mut m, &mut c] {
        give_acl(&a, n, T0 + 4);
    }
    (a, b, c, m)
}

/// R3-F3: a key holder that may rotate after the grace wraps junk; the owner's upkeep names it
/// and re-keys.
#[test]
fn upkeep_names_a_junk_wrap_and_recovers() {
    let (mut a, mut b, mut c, _m) = quartet();
    let (adev, bdev, cdev) = (clone_dev(&a), clone_dev(&b), clone_dev(&c));
    let broot = b.dev.root_hex().to_owned();
    link_of(&mut b).remove_member(&bdev, &broot, T0 + 10).unwrap();
    sync_pair(&mut b, &mut a, T0 + 10);
    give_acl(&a, &mut c, T0 + 11);
    let later = T0 + 10 + Link::ROTATION_GRACE_S;
    let s = link_of(&mut c).state().clone();
    let keyed = s.keyed_devices();
    let (mut kc, _) = s
        .new_key_change(&link_of(&mut c).read_key(&cdev, s.epoch).unwrap(), &keyed)
        .unwrap();
    let others: BTreeSet<String> = keyed.iter().filter(|d| **d != cdev.id_hex()).cloned().collect();
    let mut bad = s.make_wraps(&crypto::random32(), kc.epoch, &others).unwrap();
    for w in &mut bad {
        w.key_id = kc.key_id.clone();
    }
    kc.wraps.retain(|w| w.device == cdev.id_hex());
    kc.wraps.extend(bad);
    let p = link_of(&mut c).acl.propose(&cdev, &Op::RotateKey(kc)).unwrap();
    assert!(matches!(
        link_of(&mut a).offer(&adev, &p, later).unwrap(),
        Offered::Included(_)
    ));
    let junk_epoch = link_of(&mut a).state().epoch;
    assert!(link_of(&mut a).read_key(&adev, junk_epoch).is_err());
    let out = link_of(&mut a).upkeep(&adev, later + 2).unwrap();
    assert!(
        out.iter()
            .any(|x| x.entry().is_some_and(|e| e.actions() == ["rotate_key"])),
        "a recovery re-key"
    );
    let alarms = link_of(&mut a).store.alarms().unwrap();
    assert!(
        alarms
            .iter()
            .any(|(_, kind, author, _)| kind == "bad_wrap" && *author == cdev.id_hex()),
        "{alarms:?}"
    );
    let (_, r) = link_of(&mut a).write(&adev, &mail("chat", "back"), later + 3).unwrap();
    give_acl(&a, &mut c, later + 4);
    assert!(is_admitted(&link_of(&mut c).receive(&cdev, &r, later + 4).unwrap()));
}

// ---------------------------------------------------------------------- round 5: the chain

/// Proposals travel by sync to the sequencer, directly or relayed, and refusals travel back
/// signed, through any member.
#[test]
fn proposals_travel_to_the_sequencer_and_signed_refusals_travel_back() {
    let (mut a, mut b, mut c, _m) = quartet();
    let (adev, bdev) = (clone_dev(&a), clone_dev(&b));
    let broot = b.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &broot, Role::Admin, T0 + 5).unwrap();
    give_acl(&a, &mut b, T0 + 6);
    give_acl(&a, &mut c, T0 + 6);
    // B, an admin that does not sequence, invites: a proposal, carried by C to A.
    let t1 = link_of(&mut b)
        .invite(&bdev, Role::Reader, 3600, true, false, T0 + 7)
        .unwrap();
    sync_pair(&mut b, &mut c, T0 + 8);
    sync_pair(&mut c, &mut a, T0 + 9);
    assert!(
        link_of(&mut a).state().invites.contains_key(&t1.entry),
        "relayed and included"
    );
    sync_pair(&mut c, &mut b, T0 + 10);
    assert!(link_of(&mut b).state().invites.contains_key(&t1.entry));
    let st = link_of(&mut b).status(&bdev, T0 + 10).unwrap();
    assert!(st["proposals"].as_array().unwrap().is_empty(), "{st}");
    // B proposes again, but A demotes B before the proposal arrives: A refuses, with reasons.
    let t2 = link_of(&mut b)
        .invite(&bdev, Role::Reader, 3600, true, false, T0 + 11)
        .unwrap();
    link_of(&mut a).set_role(&adev, &broot, Role::Writer, T0 + 12).unwrap();
    sync_pair(&mut b, &mut c, T0 + 13);
    sync_pair(&mut c, &mut a, T0 + 14);
    assert!(!link_of(&mut a).state().invites.contains_key(&t2.entry));
    // The refusal reaches B through C, signed by the sequencer.
    sync_pair(&mut c, &mut b, T0 + 15);
    let st = link_of(&mut b).status(&bdev, T0 + 15).unwrap();
    let p = &st["proposals"][0];
    assert_eq!(p["status"], "refused", "{st}");
    assert!(p["why"].as_str().unwrap().contains("admin"), "{p}");
    // A forged refusal (not the sequencer's signature) is not taken.
    let t3 = link_of(&mut b).invite(&bdev, Role::Writer, 3600, true, false, T0 + 16);
    assert!(t3.is_err(), "B is no admin any more where it stands");
    let (cid, ctip) = (link_of(&mut c).id().to_owned(), link_of(&mut c).acl.tip());
    let fake = ProposalRefusal::sign(&bdev, &cid, &t1.entry, "no", ctip).unwrap();
    let cdev = clone_dev(&c);
    assert!(!link_of(&mut c).take_refusal(&cdev, &fake).unwrap_or(false));
}

/// R6-2 (probe `p2`): a refusal was taken from any device that may sequence, so an admin that is
/// not the sequencer could make the owner's other device drop its own proposal to remove that
/// admin, and make relays drop it too. Now only the device that sequenced at the refusal's
/// position counts, at or past the proposal's base; one's own proposal stays queued unless the
/// current sequencer refused it; the sequencer honours no refusal it did not sign.
#[test]
fn r6_p2_only_the_sequencer_at_the_position_refuses() {
    let (mut a, mut x, mut c) = (Node::new("a"), Node::new("x"), Node::new("c"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut x, Role::Writer, T0 + 1);
    admit(&mut a, &mut c, Role::Writer, T0 + 2);
    let (adev, xdev) = (clone_dev(&a), clone_dev(&x));
    let xroot = x.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &xroot, Role::Admin, T0 + 3).unwrap();
    let a2dev = Device::create(&a.root, "a2", false, T0 - 10).unwrap();
    link_of(&mut a).add_device(&adev, a2dev.cert.clone(), T0 + 4).unwrap();
    let mut a2 = Node {
        dev: a2dev,
        link: Some(Link::adopt(None, link_of(&mut a).acl.all(), T0 + 5).unwrap()),
        root: a.root.clone(),
    };
    give_acl(&a, &mut x, T0 + 5);
    give_acl(&a, &mut c, T0 + 5);
    let a2d = clone_dev(&a2);
    let Acted::Proposed(p) = link_of(&mut a2).remove_member(&a2d, &xroot, T0 + 6).unwrap() else {
        panic!("a2 does not sequence")
    };
    // X, an admin that does not sequence, forges a refusal at the tip.
    let (lid, tip) = (link_of(&mut x).id().to_owned(), link_of(&mut x).acl.tip());
    let fake = ProposalRefusal::sign(&xdev, &lid, &p.id().unwrap(), "refused by the sequencer", tip.clone()).unwrap();
    assert!(!link_of(&mut a2).take_refusal(&a2d, &fake).unwrap_or(false));
    assert_eq!(
        link_of(&mut a2).outstanding(32).unwrap().len(),
        1,
        "a2 keeps its proposal"
    );
    // A relay does not take it either.
    let cdev = clone_dev(&c);
    assert!(matches!(
        link_of(&mut c).offer(&cdev, &p, T0 + 6).unwrap(),
        Offered::Queued
    ));
    assert!(!link_of(&mut c).take_refusal(&cdev, &fake).unwrap_or(false));
    assert_eq!(link_of(&mut c).outstanding(32).unwrap().len(), 1);
    // A refusal by the real sequencer at a position before the proposal's base is not taken.
    let early = ProposalRefusal::sign(
        &adev,
        &lid,
        &p.id().unwrap(),
        "no",
        link_of(&mut a).acl.state_at(1).unwrap().pos(),
    )
    .unwrap();
    assert!(link_of(&mut c).take_refusal(&cdev, &early).is_err());
    // The sequencer honours no refusal it did not sign: it includes the removal.
    link_of(&mut a).offer(&adev, &p, T0 + 6).unwrap();
    sync_pair(&mut a2, &mut a, T0 + 7);
    assert!(link_of(&mut a).state().members[&xroot].removed, "X is removed");
    // After a handoff, the old sequencer's refusal of our own proposal is not final.
    let (mut b, mut y) = (Node::new("b"), Node::new("y"));
    b.link = Some(Link::create(None, &b.dev, "q", "fleet-b", Policy::default(), T0).unwrap());
    admit(&mut b, &mut y, Role::Admin, T0 + 1);
    let (bdev, ydev) = (clone_dev(&b), clone_dev(&y));
    let b2dev = Device::create(&b.root, "b2", false, T0 - 10).unwrap();
    link_of(&mut b).add_device(&bdev, b2dev.cert.clone(), T0 + 2).unwrap();
    let mut b2 = Node {
        dev: b2dev,
        link: Some(Link::adopt(None, link_of(&mut b).acl.all(), T0 + 3).unwrap()),
        root: b.root.clone(),
    };
    let b2d = clone_dev(&b2);
    link_of(&mut b2)
        .invite(&b2d, Role::Reader, 3600, true, false, T0 + 3)
        .unwrap();
    let q = link_of(&mut b2).outstanding(1).unwrap().remove(0);
    let (bid, btip) = (link_of(&mut b).id().to_owned(), link_of(&mut b).acl.tip());
    let old = ProposalRefusal::sign(&bdev, &bid, &q.id().unwrap(), "busy", btip).unwrap();
    link_of(&mut b).handoff(&bdev, &y.id(), T0 + 4).unwrap();
    give_acl(&b, &mut b2, T0 + 5);
    give_acl(&b, &mut y, T0 + 5);
    assert!(
        !link_of(&mut b2).take_refusal(&b2d, &old).unwrap(),
        "not the current sequencer's"
    );
    assert_eq!(link_of(&mut b2).outstanding(32).unwrap().len(), 1);
    // The new sequencer takes the proposal; the old one's refusal does not bind it.
    assert!(matches!(
        link_of(&mut y).offer(&ydev, &q, T0 + 6).unwrap(),
        Offered::Included(_)
    ));
}

/// A handoff moves the sequencer; proposals then go to the new one, and the old one proposes.
#[test]
fn after_a_handoff_the_new_sequencer_takes_the_proposals() {
    let (mut a, mut b, mut c, _m) = quartet();
    let (adev, bdev, cdev) = (clone_dev(&a), clone_dev(&b), clone_dev(&c));
    let broot = b.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &broot, Role::Admin, T0 + 5).unwrap();
    link_of(&mut a).handoff(&adev, &b.id(), T0 + 6).unwrap();
    assert!(!link_of(&mut a).is_sequencer(&adev));
    sync_pair(&mut a, &mut b, T0 + 7);
    assert!(link_of(&mut b).is_sequencer(&bdev));
    // The owner's next action is a proposal; the new sequencer includes it at the next session.
    let croot = c.dev.root_hex().to_owned();
    let acted = link_of(&mut a).set_role(&adev, &croot, Role::Reader, T0 + 8).unwrap();
    assert!(acted.proposal().is_some());
    sync_pair(&mut a, &mut b, T0 + 9);
    assert_eq!(link_of(&mut b).state().term, 2);
    assert_eq!(link_of(&mut b).state().members[&croot].role, Role::Reader);
    assert_eq!(link_of(&mut a).acl.tip(), link_of(&mut b).acl.tip());
    give_acl(&b, &mut c, T0 + 10);
    let st = link_of(&mut c).status(&cdev, T0 + 10).unwrap();
    assert_eq!(st["sequencer"]["device"], b.id());
    assert_eq!(st["sequencer"]["term"], 2);
}

/// The fixture for takeovers: A0 (owner, sequencer), a second owner device A1 that holds the
/// recovery phrase's root, a writer B and a writer C.
fn owner_pair() -> (Node, Node, Node, Node) {
    let (mut a, mut b, mut c, _m) = quartet();
    let adev = clone_dev(&a);
    let a1dev = Device::create(&a.root, "a1", false, T0 - 10).unwrap();
    link_of(&mut a).add_device(&adev, a1dev.cert.clone(), T0 + 5).unwrap();
    give_acl(&a, &mut b, T0 + 6);
    give_acl(&a, &mut c, T0 + 6);
    let a1 = Node {
        dev: a1dev,
        link: Some(Link::adopt(None, link_of(&mut a).acl.all(), T0 + 6).unwrap()),
        root: a.root.clone(),
    };
    (a, a1, b, c)
}

/// R5-5: whether a record sealed at a position a takeover dropped is withheld depends on the
/// record and the chain alone, not on when it arrived.
#[test]
fn r5_5_records_on_a_dropped_position_are_withheld_whenever_they_arrive() {
    let (mut a, mut a1, mut b, mut c) = owner_pair();
    let (adev, a1dev, bdev, cdev) = (clone_dev(&a), clone_dev(&a1), clone_dev(&b), clone_dev(&c));
    // The sequencer appends an entry that B and C get, then is lost; A1 never sees it.
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, T0 + 20)
        .unwrap();
    give_acl(&a, &mut b, T0 + 21);
    give_acl(&a, &mut c, T0 + 21);
    let (rid, r) = link_of(&mut b)
        .write(&bdev, &mail("chat", "on the lost entry"), T0 + 22)
        .unwrap();
    // C admits it before the takeover.
    assert!(is_admitted(&link_of(&mut c).receive(&cdev, &r, T0 + 23).unwrap()));
    // The owner takes over on A1 with the fleet root.
    let root = a1.root.clone();
    let t = link_of(&mut a1).takeover(&a1dev, &root, None, T0 + 30).unwrap();
    assert_eq!(t.term, 2);
    // C gets the takeover: the entry is dropped, and the admitted record is withheld.
    let got = link_of(&mut c).add_acl(vec![t.clone()], T0 + 31).unwrap();
    assert_eq!(got.dropped.len(), 1);
    assert_eq!(
        status_of(&c, &rid),
        (store::WITHHELD.to_owned(), Some(LOST_FORK.to_owned()))
    );
    assert!(events(&c).is_empty(), "no longer surfaced");
    // A1 (which never held the dropped entry) gets the record after the takeover: the same.
    let got = link_of(&mut a1).receive(&a1dev, &r, T0 + 32).unwrap();
    assert!(
        matches!(got, Admit::Stored { ref status, .. } if status == store::WITHHELD),
        "{got:?}"
    );
    assert_eq!(
        status_of(&a1, &rid),
        (store::WITHHELD.to_owned(), Some(LOST_FORK.to_owned()))
    );
    // B's feed goes on: its next record, on the new chain, is admitted everywhere.
    sync_pair(&mut a1, &mut b, T0 + 40);
    let (_, r2) = link_of(&mut b)
        .write(&bdev, &mail("chat", "on the new term"), T0 + 41)
        .unwrap();
    assert_eq!(r2.acl.term, 2);
    assert!(is_admitted(&link_of(&mut c).receive(&cdev, &r2, T0 + 42).unwrap()));
    // The lost sequencer's replica drops its entry too when it hears of the takeover.
    sync_pair(&mut a1, &mut a, T0 + 50);
    assert_eq!(link_of(&mut a).acl.tip(), link_of(&mut a1).acl.tip());
    assert!(!link_of(&mut a).is_sequencer(&adev));
}

/// A record naming a position this replica has not reached waits, and the chain is fetched.
#[test]
fn a_record_on_an_unreached_position_waits_and_the_chain_is_fetched() {
    let (mut a, mut b, mut c, _m) = quartet();
    let adev = clone_dev(&a);
    let croot = c.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &croot, Role::Admin, T0 + 5).unwrap();
    give_acl(&a, &mut c, T0 + 6);
    let cdev = clone_dev(&c);
    let (rid, r) = link_of(&mut c).write(&cdev, &mail("chat", "ahead"), T0 + 7).unwrap();
    let bdev = clone_dev(&b);
    assert_eq!(link_of(&mut b).receive(&bdev, &r, T0 + 8).unwrap(), Admit::Pending);
    assert_eq!(link_of(&mut b).pending_count(), 1);
    sync_pair(&mut c, &mut b, T0 + 9);
    assert_eq!(status_of(&b, &rid).0, store::ADMITTED);
    assert_eq!(link_of(&mut b).pending_count(), 0);
}

/// Equivocation over sync: both sides halt at the common prefix, show it, keep records beyond it
/// waiting, and a root takeover resolves it everywhere.
#[test]
fn an_equivocating_sequencer_halts_sync_until_the_owners_takeover() {
    let (mut a, mut a1, mut b, mut c) = owner_pair();
    let (adev, a1dev, bdev, cdev) = (clone_dev(&a), clone_dev(&a1), clone_dev(&b), clone_dev(&c));
    let prefix = link_of(&mut a).acl.tip();
    // The sequencer's key appends one entry to B's copy and another to C's.
    let mut fork = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 20).unwrap();
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, T0 + 20)
        .unwrap();
    fork.invite(&adev, Role::Admin, 3600, true, false, T0 + 20).unwrap();
    give_acl(&a, &mut b, T0 + 21);
    link_of(&mut c).add_acl(fork.acl.all(), T0 + 21).unwrap();
    let (rid, r) = link_of(&mut b)
        .write(&bdev, &mail("chat", "on one branch"), T0 + 22)
        .unwrap();
    let wire = sync_pair(&mut b, &mut c, T0 + 23);
    assert!(
        wire.len() < 40,
        "a halted pair settles instead of repeating ({} frames)",
        wire.len()
    );
    for n in [&b, &c] {
        let mut st = n
            .link
            .as_ref()
            .unwrap()
            .store
            .conn
            .prepare("SELECT reason FROM refusals")
            .unwrap();
        let reasons: Vec<String> = st.query_map([], |r| r.get(0)).unwrap().map(|r| r.unwrap()).collect();
        assert!(!reasons.iter().any(|r| r.contains("too many")), "{reasons:?}");
    }
    for (n, dev) in [(&b, &bdev), (&c, &cdev)] {
        let l = n.link.as_ref().unwrap();
        assert!(l.acl.halt().is_some());
        assert_eq!(l.acl.tip(), prefix);
        let st = l.status(dev, T0 + 23).unwrap();
        assert_eq!(st["equivocation"]["seq"], prefix.seq + 1, "{st}");
        assert!(l.store.alarms().unwrap().iter().any(|x| x.1 == "equivocation"));
    }
    assert_eq!(
        link_of(&mut c).pending_count(),
        1,
        "B's record names a position past the prefix"
    );
    assert!(link_of(&mut c).store.get(&rid).unwrap().is_none());
    // Nobody appends while halted: the sequencer neither.
    assert!(
        link_of(&mut c)
            .invite(&cdev, Role::Reader, 3600, true, false, T0 + 24)
            .is_err()
    );
    // The owner takes over after the common prefix; sync carries it to both.
    sync_pair(&mut a1, &mut b, T0 + 24);
    let root = a1.root.clone();
    let t = link_of(&mut a1).takeover(&a1dev, &root, None, T0 + 30).unwrap();
    assert_eq!(t.seq, prefix.seq + 1);
    sync_pair(&mut a1, &mut b, T0 + 31);
    sync_pair(&mut b, &mut c, T0 + 32);
    for n in [&b, &c] {
        let l = n.link.as_ref().unwrap();
        assert!(l.acl.halt().is_none());
        assert_eq!(l.acl.tip(), link_of(&mut a1).acl.tip());
    }
    // B's record named a dropped position: withheld, on both.
    let _ = link_of(&mut c).retry_pending(&cdev, T0 + 33).unwrap();
    assert_eq!(status_of(&c, &rid).1.as_deref(), Some(LOST_FORK));
    assert_eq!(status_of(&b, &rid).1.as_deref(), Some(LOST_FORK));
    let _ = r;
}

/// R6-1 (probe `p1`): an ex-sequencer (handed off, then demoted to writer) signs a second entry
/// at a position of its old term. Before: every replica halted there and folded back, so a member
/// removed since was active again, honest writers sealed under the pre-removal epoch, and the
/// default takeover dropped history. Now: a later term (another member's) started above it on
/// this chain, so it is an alarm only; nothing folds back; the default takeover drops nothing.
#[test]
fn r6_p1_an_ex_sequencers_old_key_neither_halts_nor_folds_back() {
    let mut a = Node::new("a");
    let (mut e, mut b, mut c) = (Node::new("e"), Node::new("b"), Node::new("c"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut e, Role::Writer, T0 + 1);
    admit(&mut a, &mut b, Role::Writer, T0 + 2);
    admit(&mut a, &mut c, Role::Writer, T0 + 3);
    let (adev, edev, bdev, cdev) = (clone_dev(&a), clone_dev(&e), clone_dev(&b), clone_dev(&c));
    let (eroot, broot) = (e.dev.root_hex().to_owned(), b.dev.root_hex().to_owned());
    link_of(&mut a).set_role(&adev, &eroot, Role::Admin, T0 + 4).unwrap();
    link_of(&mut a).handoff(&adev, &e.id(), T0 + 5).unwrap();
    give_acl(&a, &mut e, T0 + 6);
    assert!(link_of(&mut e).is_sequencer(&edev));
    // E keeps a private copy of the chain as it was when it became the sequencer.
    let mut fork = Link::adopt(None, link_of(&mut e).acl.all(), T0 + 6).unwrap();
    let Acted::Entry(back) = link_of(&mut e).handoff(&edev, &a.id(), T0 + 7).unwrap() else {
        panic!("E sequences")
    };
    give_acl(&e, &mut a, T0 + 8);
    // B's own copy of the chain before the handoff back (it holds the epoch-0 key there).
    let mut b_old = Link::adopt(None, link_of(&mut a).acl.all()[..back.seq as usize].to_vec(), T0 + 8).unwrap();
    // Term 3, the owner's: removes B (rotating) and demotes E to writer.
    link_of(&mut a).remove_member(&adev, &broot, T0 + 9).unwrap();
    link_of(&mut a).set_role(&adev, &eroot, Role::Writer, T0 + 10).unwrap();
    give_acl(&a, &mut c, T0 + 11);
    give_acl(&a, &mut e, T0 + 11);
    let (r1, r1r) = link_of(&mut a)
        .write(&adev, &mail("chat", "after B's removal"), T0 + 12)
        .unwrap();
    link_of(&mut c).receive(&cdev, &r1r, T0 + 12).unwrap();
    let epoch = link_of(&mut a).state().epoch;
    assert_eq!(epoch, 1);
    let tip = link_of(&mut c).acl.tip();
    // The attack: E signs another entry at the handoff's position, in its old term.
    fork.invite(&edev, Role::Reader, 3600, true, false, T0 + 7).unwrap();
    let forged = fork.acl.entry(back.seq).unwrap().clone();
    assert_eq!((forged.term, forged.seq), (back.term, back.seq));
    let r = link_of(&mut c).add_acl(vec![forged.clone()], T0 + 15).unwrap();
    let l = link_of(&mut c);
    assert!(!r.equivocation && l.acl.halt().is_none(), "an alarm, not a halt");
    assert!(
        l.store
            .alarms()
            .unwrap()
            .iter()
            .any(|x| x.1 == "equivocation" && x.3.contains("not halted")),
        "the old key signing twice is raised"
    );
    let pairs = l.store.evidence().unwrap();
    assert_eq!(pairs.len(), 1, "both entries are kept as one evidence pair");
    assert_eq!(pairs[0].theirs, forged);
    assert_eq!(l.acl.tip(), tip, "nothing folded back");
    assert!(l.state().active_device(&b.id()).is_none());
    assert!(!sync::may_sync(l, &b.id()));
    assert_eq!(l.state().members[&eroot].role, Role::Writer);
    // C still writes, under the epoch in force at the tip.
    let (r2id, r2) = l
        .write(&cdev, &mail("chat", "written after the evidence"), T0 + 16)
        .unwrap();
    assert_eq!((r2.epoch, r2.acl.clone()), (epoch, tip.clone()));
    // Removed B never reads it: its copy has not reached that position, and it holds no key.
    assert_eq!(b_old.receive(&bdev, &r2, T0 + 17).unwrap(), Admit::Pending);
    assert!(b_old.store.get(&r2id).unwrap().is_none());
    // B's new records are refused (its cut).
    let (_, rb) = b_old
        .write(&bdev, &mail("chat", "removed B writes again"), T0 + 18)
        .unwrap();
    assert!(matches!(
        link_of(&mut c).receive(&cdev, &rb, T0 + 19).unwrap(),
        Admit::Refused(_)
    ));
    // The evidence reaches the owner: no halt there either. Its default takeover drops nothing.
    sync_pair(&mut c, &mut a, T0 + 20);
    assert!(link_of(&mut a).acl.halt().is_none());
    let root = a.root.clone();
    let held = link_of(&mut a).acl.held_tip();
    let t = link_of(&mut a).takeover(&adev, &root, None, T0 + 30).unwrap();
    assert_eq!(t.seq, held.seq + 1, "the default `after` is the held tip");
    sync_pair(&mut a, &mut c, T0 + 31);
    let l = link_of(&mut c);
    assert!(l.acl.halt().is_none() && l.state().active_device(&b.id()).is_none());
    assert_eq!(status_of(&c, &r1), ("admitted".to_owned(), None));
}

/// R6-1: a real equivocation in the current term halts the chain, but never folds it back: while
/// halted, a member removed past the prefix stays removed for sync and records, roles are the
/// lower of the two states, and nothing is sealed (no pre-removal epoch, ever).
#[test]
fn r6_1_a_halt_never_brings_back_a_removed_member_or_an_old_epoch() {
    let (mut a, b, _m) = trio();
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Admin, T0 + 3);
    let adev = clone_dev(&a);
    let (bdev, cdev) = (clone_dev(&b), clone_dev(&c));
    let broot = b.dev.root_hex().to_owned();
    // The sequencer's key signs two entries at the next position: one goes on, the other is kept.
    let mut fork = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 4).unwrap();
    fork.invite(&adev, Role::Admin, 3600, true, false, T0 + 4).unwrap();
    let theirs = fork.acl.entry(fork.acl.tip().seq).unwrap().clone();
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, T0 + 4)
        .unwrap();
    let b_before = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 4).unwrap();
    // Past it, on the chain C holds: B is removed (with a rotation), C demoted to writer.
    link_of(&mut a).remove_member(&adev, &broot, T0 + 5).unwrap();
    let croot = c.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &croot, Role::Writer, T0 + 6).unwrap();
    give_acl(&a, &mut c, T0 + 7);
    let held_epoch = link_of(&mut c).state().epoch;
    assert_eq!(held_epoch, 1);
    let r = link_of(&mut c).add_acl(vec![theirs.clone()], T0 + 8).unwrap();
    assert!(r.equivocation);
    let l = link_of(&mut c);
    let h = l.acl.halt().unwrap();
    assert_eq!(h.seq, theirs.seq);
    // Held state kept; what C grants is narrowed, never widened.
    assert_eq!(l.acl.held_state().epoch, held_epoch);
    assert_eq!(l.state().epoch, held_epoch, "keys are the held tip's");
    assert!(l.state().active_device(&b.id()).is_none(), "B stays removed");
    assert!(!sync::may_sync(l, &b.id()));
    assert_eq!(
        l.state().members[&croot].role,
        Role::Writer,
        "the lower of admin and writer"
    );
    for d in l.state().sync_devices() {
        assert!(l.acl.held_state().active_device(&d).is_some());
    }
    // Nobody seals while halted.
    let err = l.write(&cdev, &mail("chat", "during the halt"), T0 + 9).unwrap_err();
    assert!(err.to_string().contains("takeover"), "{err}");
    assert_eq!(l.ack(&cdev, vec![], T0 + 9).unwrap(), None);
    // B's records past its cut are refused, as before the halt.
    let mut b_copy = b_before;
    let (_, rb) = b_copy
        .write(&bdev, &mail("chat", "B after its removal"), T0 + 10)
        .unwrap();
    assert!(matches!(l.receive(&cdev, &rb, T0 + 10).unwrap(), Admit::Refused(_)));
    // Status says which state it shows.
    let st = l.status(&cdev, T0 + 11).unwrap();
    assert_eq!(st["halted_view"], true);
    assert_eq!(st["acl_held_tip"]["seq"], l.acl.held_tip().seq);
}

/// R6-3: a replica that refuses the sequencer's next entry raises an alarm: the divergence is
/// never silent.
#[test]
fn a_refused_sequencer_entry_is_an_alarm() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, T0 + 100_000)
        .unwrap();
    let r = link_of(&mut b).add_acl(link_of(&mut a).acl.all(), T0 + 3).unwrap();
    assert!(r.diverged.is_some(), "{r:?}");
    assert!(
        link_of(&mut b)
            .store
            .alarms()
            .unwrap()
            .iter()
            .any(|x| x.1 == "acl_divergence")
    );
    // Junk from anyone else is a refusal, not an alarm.
    let (mut c, _, _) = trio();
    let cdev = clone_dev(&c);
    link_of(&mut c)
        .invite(&cdev, Role::Reader, 3600, true, false, T0 + 3)
        .unwrap();
    let r = link_of(&mut b).add_acl(link_of(&mut c).acl.all(), T0 + 3).unwrap();
    assert!(r.diverged.is_none());
}

fn proposal_rows(n: &Node) -> (i64, i64) {
    n.link
        .as_ref()
        .unwrap()
        .store
        .conn
        .query_row(
            "SELECT count(*), coalesce(sum(length(json)), 0) FROM proposals",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap()
}

/// R6-4 (probe `p4`): refused proposals piled up on the sequencer without bound, from self-made
/// fleets, with 1.5 MB strings, and refusals cost the session peer nothing. Now each kind has a
/// size cap; only an active member's device (or a join whose invite proof verifies) is kept;
/// refusals count against the peer's allowance; refused rows are trimmed; no origin flushes the
/// relay queue.
#[test]
fn r6_p4_refused_proposals_are_bounded_and_charged_to_the_peer() {
    let (mut a, mut w, _m) = trio();
    let (adev, wdev, wid) = (clone_dev(&a), clone_dev(&w), w.id());
    let link = link_of(&mut a).id().to_owned();
    let mut sess = Session::new();
    for f in sync::hello(link_of(&mut w), &wdev).unwrap() {
        sess.on_frame(link_of(&mut a), &adev, &wid, f, T0 + 2).unwrap();
    }
    let junk = "a".repeat(1_500_000);
    let (mut refusals, mut errors) = (0, Vec::new());
    let rows = proposal_rows(&a);
    for i in 0..40u64 {
        let fake = Node::new(&format!("f{i}"));
        let op = Op::Join(acl::Join {
            invite: junk.clone(),
            proof: "AA".into(),
            label: "x".into(),
        });
        let p = Proposal::sign(&fake.dev, &link, &op, acl::Base { term: 1, seq: 0 }, T0 + 3600).unwrap();
        let out = sess.on_frame(link_of(&mut a), &adev, &wid, Frame::Propose { proposal: p }, T0 + 3 + i);
        let out = out.unwrap();
        refusals += out
            .replies
            .iter()
            .filter(|f| matches!(f, Frame::Refusal { .. }))
            .count();
        errors.extend(out.refused);
    }
    assert_eq!(proposal_rows(&a), rows, "nothing kept");
    assert_eq!(refusals, 0, "nothing signed for junk");
    assert!(errors[0].contains("larger than"), "{}", errors[0]);
    assert!(
        errors[acl::MAX_MEMBER_PROPOSALS_PER_DAY].contains("allowance"),
        "{}",
        errors[acl::MAX_MEMBER_PROPOSALS_PER_DAY]
    );
    // An outsider's well-formed proposal, or a join whose proof fails, is not kept by a relay.
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Writer, T0 + 200);
    give_acl(&a, &mut w, T0 + 200);
    let cdev = clone_dev(&c);
    let outsider = Node::new("z");
    let op = acl::Op::Invite(acl::Invite {
        invite: hex(&[1u8; 32]),
        role: Role::Reader,
        expires: T0 + 3600,
        single_use: true,
        approval: false,
    });
    let p = link_of(&mut c).acl.propose(&outsider.dev, &op).unwrap();
    assert!(link_of(&mut c).offer(&cdev, &p, T0 + 201).is_err());
    let secret = link_of(&mut a)
        .invite(&adev, Role::Writer, 3600, true, false, T0 + 202)
        .unwrap();
    give_acl(&a, &mut c, T0 + 202);
    let joiner = Node::new("j");
    let wrong = acl::InviteTicket {
        secret: [7u8; 32],
        entry: secret.entry.clone(),
    };
    let bad = sync::join_proposal(&link_of(&mut c).acl.all(), &joiner.dev, &wrong, "j", T0 + 203).unwrap();
    assert!(link_of(&mut c).offer(&cdev, &bad, T0 + 203).is_err());
    let good = sync::join_proposal(&link_of(&mut c).acl.all(), &joiner.dev, &secret, "j", T0 + 203).unwrap();
    assert!(matches!(
        link_of(&mut c).offer(&cdev, &good, T0 + 203).unwrap(),
        Offered::Queued
    ));
    // A member flooding the relay keeps at most its share; another origin's proposal stays. (A
    // relay keeps only what holds on its chain: W is an admin here, so its invites do.)
    let wroot = w.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &wroot, Role::Admin, T0 + 203).unwrap();
    give_acl(&a, &mut w, T0 + 203);
    give_acl(&a, &mut c, T0 + 203);
    for k in 0..100u8 {
        let mut key = [0u8; 32];
        key[0] = k;
        let op = acl::Op::Invite(acl::Invite {
            invite: hex(&key),
            role: Role::Reader,
            expires: T0 + 3600,
            single_use: true,
            approval: false,
        });
        let p = link_of(&mut w).acl.propose(&wdev, &op).unwrap();
        link_of(&mut c).offer(&cdev, &p, T0 + 204 + u64::from(k)).unwrap();
    }
    let kept = link_of(&mut c).outstanding(10_000).unwrap();
    assert_eq!(
        kept.iter().filter(|p| p.proposer.device == wid).count(),
        MAX_RELAYED_PER_ORIGIN as usize
    );
    assert!(
        kept.iter().any(|p| p.id().unwrap() == good.id().unwrap()),
        "the join survives"
    );
    // The sequencer trims the rows of the proposals it refused the same way (W is a writer again
    // there, so it refuses W's invites; a day on, when W's charges as a peer above have lapsed).
    link_of(&mut a).set_role(&adev, &wroot, Role::Writer, T0 + 399).unwrap();
    for p in &kept {
        if p.proposer.device == wid {
            assert!(matches!(
                link_of(&mut a).offer(&adev, p, T0 + DAY + 400).unwrap(),
                Offered::Refused(_)
            ));
        }
    }
    let more: Vec<Proposal> = (100..200u8)
        .map(|k| {
            let mut key = [0u8; 32];
            key[0] = k;
            let op = acl::Op::Invite(acl::Invite {
                invite: hex(&key),
                role: Role::Reader,
                expires: T0 + 3600,
                single_use: true,
                approval: false,
            });
            link_of(&mut w).acl.propose(&wdev, &op).unwrap()
        })
        .collect();
    for (k, p) in more.iter().enumerate() {
        link_of(&mut a).offer(&adev, p, T0 + DAY + 500 + k as u64).unwrap();
    }
    let of_w: i64 = link_of(&mut a)
        .store
        .conn
        .query_row("SELECT count(*) FROM proposals WHERE grp = ?1", [&wroot], |r| r.get(0))
        .unwrap();
    assert_eq!(of_w, i64::from(MAX_RELAYED_PER_ORIGIN));
}

/// R6-7: `acl_done` counted progress as `upto > asked_from`, so a replica that refused every
/// entry of an answer asked for the same range again, until the frame limit closed the session.
/// Now only a tip that moved counts.
#[test]
fn r6_7_refused_entries_are_no_progress_and_are_not_asked_for_again() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    // Entries dated well ahead of B's clock: B refuses each one it is sent.
    for k in 0..3 {
        link_of(&mut a)
            .invite(&adev, Role::Reader, 3600, true, false, T0 + 100_000 + k)
            .unwrap();
    }
    let wire = sync_pair(&mut a, &mut b, T0 + 3);
    let wants = wire
        .iter()
        .filter(|f| String::from_utf8_lossy(&f[4..]).contains(r#""t":"acl_want""#))
        .count();
    assert_eq!(wants, 1, "asked once, not again after refusing the answer");
    assert!(link_of(&mut b).acl.tip().seq < link_of(&mut a).acl.tip().seq);
    let reasons: Vec<String> = {
        let l = link_of(&mut b);
        let mut st = l.store.conn.prepare("SELECT reason FROM refusals").unwrap();
        st.query_map([], |r| r.get(0)).unwrap().map(|r| r.unwrap()).collect()
    };
    assert!(!reasons.iter().any(|r| r.contains("too many")), "{reasons:?}");
}

/// A 5,000-entry chain syncs from scratch to a member that saw only the start, and to a joiner,
/// in frames of at most `ACL_FRAME_BYTES`.
#[test]
fn a_5000_entry_chain_syncs_from_scratch_with_bounded_frames() {
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    let adev = clone_dev(&a);
    let mut ts = T0 + 10;
    let t = std::time::Instant::now();
    while link_of(&mut a).acl.len() < 5_000 {
        ts += 1;
        link_of(&mut a)
            .invite(&adev, Role::Reader, 3600, true, false, ts)
            .unwrap();
    }
    let built = t.elapsed();
    ts += 1;
    let t = std::time::Instant::now();
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, ts)
        .unwrap();
    let one = t.elapsed();
    let hello = sync::hello(a.link.as_ref().unwrap(), &a.dev).unwrap();
    assert!(sync::encode(&hello[0]).unwrap().len() < 4096);
    let t = std::time::Instant::now();
    let wire = sync_pair(&mut a, &mut b, ts);
    let synced = t.elapsed();
    let bytes: usize = wire.iter().map(Vec::len).sum();
    eprintln!(
        "5,000 entries: built by appends in {built:?}, one more append {one:?}; a member synced in {synced:?} over {} frames, {bytes} bytes",
        wire.len()
    );
    assert_eq!(link_of(&mut b).acl.tip(), link_of(&mut a).acl.tip());
    let mut acl_frames = 0;
    for bytes in &wire {
        if let Ok(Frame::Acl { entries }) = sync::decode(&bytes[4..]) {
            acl_frames += 1;
            let n: usize = entries.iter().map(|e| serde_json::to_vec(e).unwrap().len()).sum();
            assert!(n <= sync::ACL_FRAME_BYTES, "an ACL frame carries {n} bytes of entries");
        }
    }
    assert!(acl_frames > 1, "the chain crossed in pages");
    // A joiner from scratch gets the whole chain through the join door, paged the same way.
    let mut c = Node::new("c");
    admit(&mut a, &mut c, Role::Writer, ts + 1);
    assert_eq!(link_of(&mut c).acl.tip(), link_of(&mut a).acl.tip());
    sync_pair(&mut a, &mut c, ts + 2);
}

/// R5-3: a hello sends no ACL at all; an ACL want is answered with exactly the range asked for,
/// and at most `ACL_BYTES_PER_MIN` (plus one entry) a minute per session.
#[test]
fn r5_3_acl_answers_are_bounded_by_the_range_and_the_session_budget() {
    let (mut a, b, _m) = trio();
    let adev = clone_dev(&a);
    let mut ts = T0 + 10;
    // Big entries: rotations wrapping to many devices make the budget bind quickly.
    for i in 0..1500u32 {
        ts += 1;
        let mut secret = [0u8; 32];
        secret[..4].copy_from_slice(&i.to_be_bytes());
        link_of(&mut a)
            .invite(&adev, Role::Reader, 3600, true, false, ts)
            .unwrap();
    }
    let bid = b.id();
    let mut s = Session::new();
    let hello = sync::hello(b.link.as_ref().unwrap(), &b.dev).unwrap().remove(0);
    let out = s.on_frame(link_of(&mut a), &adev, &bid, hello, ts).unwrap();
    assert!(
        !out.replies.iter().any(|f| matches!(f, Frame::Acl { .. })),
        "a hello alone sends no ACL entries"
    );
    // Exactly the range: three entries asked, three sent.
    let out = s
        .on_frame(link_of(&mut a), &adev, &bid, Frame::AclWant { from: 10, to: 13 }, ts)
        .unwrap();
    let got: Vec<u64> = out
        .replies
        .iter()
        .flat_map(|f| match f {
            Frame::Acl { entries } => entries.iter().map(|e| e.seq).collect(),
            _ => vec![],
        })
        .collect();
    assert_eq!(got, vec![11, 12, 13]);
    // Past the tip, or an empty range: nothing.
    let tip = link_of(&mut a).acl.tip().seq;
    let out = s
        .on_frame(
            link_of(&mut a),
            &adev,
            &bid,
            Frame::AclWant {
                from: tip,
                to: tip + 100,
            },
            ts,
        )
        .unwrap();
    assert_eq!(
        out.replies,
        vec![Frame::AclDone { upto: tip }],
        "only the end of the (empty) answer"
    );
    let out = s
        .on_frame(link_of(&mut a), &adev, &bid, Frame::AclWant { from: 20, to: 5 }, ts)
        .unwrap();
    assert_eq!(out.replies, vec![Frame::AclDone { upto: 20 }]);
    // The whole chain, asked for again and again within one minute: the budget holds.
    let req = sync::encode(&Frame::AclWant {
        from: 0,
        to: u64::from(u32::MAX),
    })
    .unwrap()
    .len();
    let mut sent = 0usize;
    let mut asks = 0usize;
    for _ in 0..100 {
        asks += 1;
        let out = s
            .on_frame(
                link_of(&mut a),
                &adev,
                &bid,
                Frame::AclWant {
                    from: 0,
                    to: u64::from(u32::MAX),
                },
                ts + 1,
            )
            .unwrap_or_default();
        sent += out
            .replies
            .iter()
            .map(|f| sync::encode(f).unwrap().len())
            .sum::<usize>();
    }
    let chain: usize = link_of(&mut a)
        .acl
        .all()
        .iter()
        .map(|e| serde_json::to_vec(e).unwrap().len())
        .sum();
    eprintln!(
        "chain {chain} bytes; {asks} asks of {req} bytes within a minute got {sent} bytes ({}x the requests)",
        sent / (asks * req)
    );
    assert!(
        sent <= sync::ACL_BYTES_PER_MIN + acl::MAX_ENTRY_BYTES + 64 * 1024,
        "{sent}"
    );
    // The next minute the budget is back.
    let out = s
        .on_frame(link_of(&mut a), &adev, &bid, Frame::AclWant { from: 0, to: 2 }, ts + 61)
        .unwrap();
    assert!(!out.replies.is_empty());
}

/// One want outstanding at a time: the asker waits for `acl_done`, asks for the rest only after
/// progress, and asks again at the peer's next ping when the peer's budget cut an answer short.
#[test]
fn an_acl_answer_cut_short_by_the_budget_is_asked_again_at_the_next_ping() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    for i in 0..5 {
        link_of(&mut a)
            .invite(&adev, Role::Reader, 3600, true, false, T0 + 10 + i)
            .unwrap();
    }
    let (aid, bdev) = (a.id(), clone_dev(&b));
    let mut s = Session::new();
    let hello = sync::hello(a.link.as_ref().unwrap(), &a.dev).unwrap().remove(0);
    let out = s.on_frame(link_of(&mut b), &bdev, &aid, hello, T0 + 20).unwrap();
    let from = link_of(&mut b).acl.tip().seq;
    let wants = |out: &sync::Outcome| {
        out.replies
            .iter()
            .filter(|f| matches!(f, Frame::AclWant { .. }))
            .count()
    };
    assert_eq!(wants(&out), 1, "B asks toward A's tip");
    // A's budget is spent: the answer is empty. B does not ask again at once...
    let out = s
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::AclDone { upto: from }, T0 + 21)
        .unwrap();
    assert_eq!(wants(&out), 0);
    let out = s
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::Ping {}, T0 + 22)
        .unwrap();
    assert_eq!(wants(&out), 1, "...but at A's next ping");
    // While that want is outstanding, a ping asks nothing more.
    let out = s
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::Ping {}, T0 + 23)
        .unwrap();
    assert_eq!(wants(&out), 0);
}

/// R4-8 kept: a session takes at most `MAX_ACL_FRAMES_PER_MIN` ACL-side frames a minute.
#[test]
fn acl_frames_per_session_are_rate_limited() {
    let (mut a, b, _m) = trio();
    let adev = clone_dev(&a);
    let bid = b.id();
    let mut s = Session::new();
    let h = sync::hello(b.link.as_ref().unwrap(), &b.dev).unwrap().remove(0);
    s.on_frame(link_of(&mut a), &adev, &bid, h, T0 + 60).unwrap();
    for _ in 0..sync::MAX_ACL_FRAMES_PER_MIN {
        s.on_frame(link_of(&mut a), &adev, &bid, Frame::Acl { entries: vec![] }, T0 + 60)
            .unwrap();
    }
    let err = s
        .on_frame(link_of(&mut a), &adev, &bid, Frame::AclWant { from: 0, to: 1 }, T0 + 61)
        .unwrap_err();
    assert!(err.to_string().contains("too many ACL frames"), "{err}");
    s.on_frame(link_of(&mut a), &adev, &bid, Frame::Acl { entries: vec![] }, T0 + 120)
        .unwrap();
}

/// A store reopened while halted is still halted, with its evidence.
#[test]
fn a_halted_store_stays_halted_after_a_reopen() {
    let dir = std::env::temp_dir().join(format!("aurora-link-test-{}", hex(&crypto::random32())));
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    let adev = clone_dev(&a);
    let mut stored = Link::adopt(Some(&dir), link_of(&mut a).acl.all(), T0 + 2).unwrap();
    let path = stored.path.clone().unwrap();
    let mut fork = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 2).unwrap();
    link_of(&mut a)
        .invite(&adev, Role::Reader, 3600, true, false, T0 + 3)
        .unwrap();
    fork.invite(&adev, Role::Admin, 3600, true, false, T0 + 3).unwrap();
    stored.add_acl(link_of(&mut a).acl.all(), T0 + 4).unwrap();
    stored.add_acl(fork.acl.all(), T0 + 4).unwrap();
    assert!(stored.acl.halt().is_some());
    let tip = stored.acl.tip();
    drop(stored);
    let back = Link::open(&path).unwrap();
    assert!(back.acl.halt().is_some());
    assert_eq!(back.acl.tip(), tip);
    std::fs::remove_dir_all(dir).unwrap();
}

fn temp_dir() -> std::path::PathBuf {
    std::env::temp_dir().join(format!("aurora-link-test-{}", hex(&crypto::random32())))
}

fn count(l: &Link, sql: &str) -> i64 {
    l.store.conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

/// A (owner), E (an admin that sequenced term 2: an invite at `k`, then the handoff back at
/// `k + 1`, and is a writer since) and C (writer). Returns the chain as E held it when term 2
/// started, and E's two entries.
fn ex_sequencer() -> (Node, Node, Node, acl::AclChain, acl::Entry, acl::Entry) {
    let mut a = Node::new("a");
    let (mut e, mut c) = (Node::new("e"), Node::new("c"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut e, Role::Writer, T0 + 1);
    admit(&mut a, &mut c, Role::Writer, T0 + 2);
    let (adev, edev) = (clone_dev(&a), clone_dev(&e));
    let eroot = e.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &eroot, Role::Admin, T0 + 3).unwrap();
    link_of(&mut a).handoff(&adev, &e.id(), T0 + 4).unwrap();
    give_acl(&a, &mut e, T0 + 5);
    let base = sync::chain_of(&link_of(&mut e).acl.all()).unwrap();
    let Acted::Entry(first) = link_of(&mut e).invite_acted(&edev, T0 + 6) else {
        panic!("E sequences")
    };
    let Acted::Entry(back) = link_of(&mut e).handoff(&edev, &a.id(), T0 + 7).unwrap() else {
        panic!("E sequences")
    };
    give_acl(&e, &mut a, T0 + 8);
    link_of(&mut a).set_role(&adev, &eroot, Role::Writer, T0 + 9).unwrap();
    give_acl(&a, &mut c, T0 + 10);
    give_acl(&a, &mut e, T0 + 10);
    (a, e, c, base, first, back)
}

impl Link {
    /// An invite by `device`, as `act` returns it (tests only).
    fn invite_acted(&mut self, device: &Device, now: u64) -> Acted {
        let op = Op::Invite(acl::Invite {
            invite: hex(&crypto::public_of(&acl::invite_key(&crypto::random32()))),
            role: Role::Reader,
            expires: now + 3600,
            single_use: true,
            approval: false,
        });
        self.act(device, op, now).unwrap()
    }
}

/// `n` distinct entries E signs at `seq` of its old term, each valid on its own there.
fn variants(base: &acl::AclChain, held: &[acl::Entry], edev: &Device, to: &str, n: u64) -> Vec<acl::Entry> {
    (0..n)
        .map(|i| {
            let mut ch = base.clone();
            assert_eq!(ch.insert(held.to_vec(), None).added, held.len());
            let op = if held.is_empty() {
                Op::Handoff(acl::Handoff { to: to.to_owned() })
            } else {
                Op::Invite(acl::Invite {
                    invite: hex(&crypto::public_of(&acl::invite_key(&crypto::random32()))),
                    role: Role::Reader,
                    expires: T0 + 3600,
                    single_use: true,
                    approval: false,
                })
            };
            ch.append(edev, Some(op), vec![], T0 + 6 + i, &|_| 0).unwrap()
        })
        .collect()
}

/// R7-1 (probe `p1`): a demoted ex-sequencer sent thousands of distinct valid entries at one
/// position of its old term. Each cost a fold and a dry application under the daemon's lock, was
/// stored as evidence without bound, and was checked again at every restart. Now a replica keeps
/// one pair per position and signer and one alarm per signer, decided before anything is
/// verified; an insert runs at most one check; each check is charged to the session; and a
/// restart checks only the current halt's pair.
#[test]
fn r7_p1_an_evidence_flood_is_checked_once_kept_once_and_charged_to_the_session() {
    let dir = temp_dir();
    let (mut a, e, _c, base, first, back) = ex_sequencer();
    let (edev, aid, eid) = (clone_dev(&e), a.id(), e.id());
    let mut c = Link::adopt(Some(&dir), link_of(&mut a).acl.all(), T0 + 11).unwrap();
    let path = c.path.clone().unwrap();
    let tip = c.acl.tip();
    let at_k = variants(&base, &[], &edev, &aid, 300);
    assert!(at_k.iter().all(|x| x.seq == first.seq && x.term == first.term));
    // One batch of 300: one check, one pair, one alarm, no halt.
    let r = c.add_acl(at_k[..150].to_vec(), T0 + 20).unwrap();
    assert_eq!((r.checks, r.added, r.equivocation), (1, 0, false), "{r:?}");
    assert!(c.acl.halt().is_none());
    // The same position again, in another batch: nothing is checked.
    let r = c.add_acl(at_k[150..].to_vec(), T0 + 21).unwrap();
    assert_eq!(r.checks, 0, "a pair for this position and signer is held");
    // E's other position of that term: one more alarm about E is not checked either.
    let at_k1 = variants(&base, std::slice::from_ref(&first), &edev, &aid, 20);
    assert!(at_k1.iter().all(|x| x.seq == back.seq));
    let r = c.add_acl(at_k1, T0 + 22).unwrap();
    assert_eq!(r.checks, 0, "E is already raised");
    assert_eq!(count(&c, "SELECT count(*) FROM acl_evidence"), 1);
    assert_eq!(count(&c, "SELECT count(*) FROM alarms WHERE kind = 'equivocation'"), 1);
    assert_eq!(c.acl.tip(), tip);
    // A restart checks only a halt's pair, and the position stays seen.
    drop(c);
    let mut c = Link::open(&path).unwrap();
    assert!(c.acl.halt().is_none());
    assert_eq!(c.acl.tip(), tip);
    let r = c.add_acl(variants(&base, &[], &edev, &aid, 3), T0 + 23).unwrap();
    assert_eq!(r.checks, 0);
    assert_eq!(count(&c, "SELECT count(*) FROM acl_evidence"), 1);
    // Entries E signs that do not apply on their own are no evidence, and each costs a check:
    // one per batch however many it carries, and the session pays for every one.
    let mut fresh = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 11).unwrap();
    let junk: Vec<acl::Entry> = at_k
        .iter()
        .map(|x| {
            let mut j = x.clone();
            // A handoff to E itself, which sequences that term: no sequencer could sign it.
            j.body = Some(Op::Handoff(acl::Handoff { to: eid.clone() }));
            j.resigned(&edev)
        })
        .collect();
    let r = fresh.add_acl(junk.clone(), T0 + 24).unwrap();
    assert_eq!((r.checks, r.added), (1, 0));
    assert!(fresh.acl.halt().is_none() && fresh.store.evidence().unwrap().is_empty());
    let fdev = clone_dev(&a);
    let mut sess = Session::new();
    let mut taken = 0;
    let err = loop {
        let f = Frame::Acl {
            entries: vec![junk[taken].clone()],
        };
        match sess.on_frame(&mut fresh, &fdev, &eid, f, T0 + 60) {
            Ok(_) => taken += 1,
            Err(err) => break err,
        }
        assert!(taken < 100, "the session never ran out");
    };
    assert!(err.to_string().contains("evidence checks"), "{err}");
    assert_eq!(
        taken,
        (sync::MAX_ACL_FRAMES_PER_MIN / (sync::EVIDENCE_CHECK_FRAMES + 1)) as usize
    );
    // The current sequencer's flood at its own position: one halt, one pair, and nothing more is
    // checked at or above it.
    let mut d = Link::adopt(None, base.all(), T0 + 6).unwrap();
    d.add_acl(vec![first.clone()], T0 + 6).unwrap();
    let r = d.add_acl(variants(&base, &[], &edev, &aid, 50), T0 + 30).unwrap();
    assert!(r.equivocation && r.checks == 1 && d.acl.halt().is_some());
    let r = d.add_acl(variants(&base, &[], &edev, &aid, 50), T0 + 31).unwrap();
    assert_eq!(r.checks, 0);
    assert_eq!(d.store.evidence().unwrap().len(), 1);
    std::fs::remove_dir_all(dir).unwrap();
}

/// R8-4: a frame about a signer already raised was screened by `settled_above`, a scan of the
/// whole chain that parses its proposals, before anything was charged: each such frame cost a
/// scan. Now the scan's answer is kept per signer and term until the chain changes.
#[test]
fn r8_4_frames_about_an_alarmed_signer_scan_the_chain_once() {
    let (mut a, e, _c, base, first, back) = ex_sequencer();
    let (adev, edev, aid) = (clone_dev(&a), clone_dev(&e), a.id());
    let mut c = Link::adopt(None, link_of(&mut a).acl.all(), T0 + 11).unwrap();
    let r = c.add_acl(variants(&base, &[], &edev, &aid, 1), T0 + 20).unwrap();
    assert_eq!(r.checks, 1, "the alarm about E");
    let scans = c.acl.settled_scans;
    assert_eq!(scans, 1);
    // One frame each at E's other position: every one screened out, by one scan in all.
    let at_k1 = variants(&base, std::slice::from_ref(&first), &edev, &aid, 40);
    assert!(at_k1.iter().all(|x| x.seq == back.seq));
    for x in &at_k1 {
        let r = c.add_acl(vec![x.clone()], T0 + 21).unwrap();
        assert_eq!(r.checks, 0);
    }
    assert_eq!(c.acl.settled_scans, scans, "the bound is kept while the chain stands");
    // The chain grows: the next frame scans once more, and the answer is unchanged.
    link_of(&mut a).invite_acted(&adev, T0 + 22);
    c.add_acl(link_of(&mut a).acl.all(), T0 + 22).unwrap();
    for x in &at_k1[..5] {
        let r = c.add_acl(vec![x.clone()], T0 + 23).unwrap();
        assert_eq!(r.checks, 0);
    }
    assert_eq!(c.acl.settled_scans, scans + 1);
    assert!(c.acl.halt().is_none());
}

/// R7-1: evidence rows are capped. At the cap an alarm-only pair is not kept, and a halt's pair
/// replaces the oldest pair that is not the current halt; only the current halt's pair is
/// checked again on a restart.
#[test]
fn r7_1_stored_evidence_stays_within_its_cap() {
    let (mut a, _e, _c, _base, first, back) = ex_sequencer();
    let l = link_of(&mut a);
    let pair = |seq: u64, kind: acl::EvidenceKind| {
        let mut theirs = back.clone();
        theirs.seq = seq;
        acl::Evidence {
            ours: first.clone(),
            theirs,
            kind,
        }
    };
    let cap = acl::MAX_EVIDENCE_PAIRS;
    for s in 0..u64::from(cap) + 50 {
        let kept = l
            .store
            .put_evidence(&pair(s, acl::EvidenceKind::Alarm), T0 + s, cap)
            .unwrap();
        assert_eq!(kept, s < u64::from(cap));
    }
    assert_eq!(count(l, "SELECT count(*) FROM acl_evidence"), i64::from(cap));
    assert!(
        l.store
            .put_evidence(&pair(9_999, acl::EvidenceKind::Halt), T0 + 9_999, cap)
            .unwrap()
    );
    assert_eq!(count(l, "SELECT count(*) FROM acl_evidence"), i64::from(cap));
    assert_eq!(
        count(l, "SELECT count(*) FROM acl_evidence WHERE seq = 0"),
        0,
        "the oldest went"
    );
    assert!(
        l.store
            .put_evidence(&pair(9_998, acl::EvidenceKind::Halt), T0 + 9_999, cap)
            .unwrap()
    );
    l.store
        .settle_evidence(Some(&pair(9_998, acl::EvidenceKind::Halt).key()))
        .unwrap();
    assert_eq!(count(l, "SELECT count(*) FROM acl_evidence WHERE kind = 'halt'"), 1);
    assert_eq!(count(l, "SELECT count(*) FROM acl_evidence WHERE kind = 'past'"), 1);
    l.store.settle_evidence(None).unwrap();
    assert_eq!(count(l, "SELECT count(*) FROM acl_evidence WHERE kind = 'halt'"), 0);
}

/// R7-4 (probe `p4`): a halt from evidence at the next position (`seq == len`) was lost on a
/// restart, because the restore only compared stored entries with held ones. The halt's pair is
/// now stored as a pair and checked again as an evidence frame is.
#[test]
fn r7_p4_a_halt_at_the_next_position_survives_a_restart() {
    let dir = temp_dir();
    let mut a = Node::new("a");
    let mut c = Node::new("c");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut c, Role::Writer, T0 + 1);
    let (adev, cdev) = (clone_dev(&a), clone_dev(&c));
    let mut cl = Link::adopt(Some(&dir), link_of(&mut a).acl.all(), T0 + 2).unwrap();
    let base = sync::chain_of(&link_of(&mut a).acl.all()).unwrap();
    let (mut b1, mut b2) = (base.clone(), base.clone());
    let inv = |ts: u64| {
        Some(Op::Invite(acl::Invite {
            invite: c.id(),
            role: Role::Reader,
            expires: ts + 3600,
            single_use: true,
            approval: false,
        }))
    };
    let x = b1.append(&adev, inv(T0 + 3), vec![], T0 + 3, &|_| 0).unwrap();
    let y = b2.append(&adev, inv(T0 + 3), vec![], T0 + 4, &|_| 0).unwrap();
    assert_eq!(x.seq as usize, cl.acl.len());
    assert!(cl.acl.note_evidence(&x, &y).unwrap());
    cl.add_acl(vec![], T0 + 5).unwrap();
    let halt = cl.acl.halt().map(|h| h.seq);
    assert_eq!(halt, Some(x.seq));
    let path = cl.path.clone().unwrap();
    drop(cl);
    let mut cl = Link::open(&path).unwrap();
    assert_eq!(cl.acl.halt().map(|h| h.seq), halt, "the halt survives the restart");
    assert!(cl.write(&cdev, &mail("chat", "after a restart"), T0 + 6).is_err());
    let r = cl.add_acl(vec![x], T0 + 7).unwrap();
    assert_eq!(r.added, 0);
    assert!(cl.acl.halt().is_some());
    std::fs::remove_dir_all(dir).unwrap();
}

/// R7-2 (probe `p2`): while halted, a replica's narrowed state leaves out every device added past
/// the prefix, its own included. The daemon's transport read it, so such a device dialed nobody
/// and refused everyone for the link, and never received the takeover; between two such devices
/// even the chain's own frames were refused. Now the chain's frames (`acl_want`, `acl_done`,
/// `evidence`) are taken from any device of the held tip, and the evidence and the takeover travel
/// both ways; records still need the narrowed `may_sync`.
#[test]
fn r7_p2_devices_added_past_a_halt_trade_evidence_and_take_the_takeover() {
    let mut a = Node::new("a");
    let (mut c, mut n, mut m) = (Node::new("c"), Node::new("n"), Node::new("m"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut c, Role::Writer, T0 + 1);
    let adev = clone_dev(&a);
    let a2dev = Device::create(&a.root, "a2", false, T0 - 10).unwrap();
    link_of(&mut a).add_device(&adev, a2dev.cert.clone(), T0 + 2).unwrap();
    let mut a2 = Node {
        dev: a2dev,
        link: Some(Link::adopt(None, link_of(&mut a).acl.all(), T0 + 3).unwrap()),
        root: a.root.clone(),
    };
    // A backup of the sequencer (a restored disk, a stolen key) signs at the next position.
    let mut backup = sync::chain_of(&link_of(&mut a).acl.all()).unwrap();
    admit(&mut a, &mut n, Role::Writer, T0 + 4);
    admit(&mut a, &mut m, Role::Writer, T0 + 5);
    for x in [&mut c, &mut a2, &mut n, &mut m] {
        give_acl(&a, x, T0 + 6);
    }
    let other = backup
        .append(
            &adev,
            Some(Op::Handoff(acl::Handoff { to: a2.id() })),
            vec![],
            T0 + 7,
            &|_| 0,
        )
        .unwrap();
    for x in [&mut n, &mut c, &mut a2] {
        link_of(x).add_acl(vec![other.clone()], T0 + 8).unwrap();
        assert!(link_of(x).acl.halt().is_some());
    }
    let (nid, mid) = (n.id(), m.id());
    let l = link_of(&mut n);
    assert!(
        l.state().active_device(&nid).is_none(),
        "the narrowed view leaves N out"
    );
    assert!(!sync::may_sync(l, &mid) && sync::may_sync_acl(l, &mid));
    // M has not seen the evidence. From N, a device the halt leaves out, it gets it.
    assert!(link_of(&mut m).acl.halt().is_none());
    sync_pair(&mut n, &mut m, T0 + 9);
    assert!(link_of(&mut m).acl.halt().is_some(), "the evidence reached M");
    // Both halted, each outside the other's narrowed view: their session keeps to the chain.
    let wire = sync_pair(&mut n, &mut m, T0 + 10);
    let frames: Vec<Frame> = wire.iter().map(|b| sync::decode(&b[4..]).unwrap()).collect();
    assert!(frames.iter().any(|f| matches!(f, Frame::Evidence { .. })));
    assert!(
        !frames
            .iter()
            .any(|f| matches!(f, Frame::Records { .. } | Frame::Synced { .. }))
    );
    // The owner's takeover, keeping this branch, reaches C; from C it reaches M, and from M (which
    // N's narrowed view leaves out) it reaches N.
    let held = link_of(&mut a2).acl.held_tip().seq;
    let a2d = clone_dev(&a2);
    let root = a2.root.clone();
    link_of(&mut a2).takeover(&a2d, &root, Some(held), T0 + 20).unwrap();
    give_acl(&a2, &mut c, T0 + 21);
    assert!(link_of(&mut c).acl.halt().is_none());
    sync_pair(&mut c, &mut m, T0 + 22);
    assert!(link_of(&mut m).acl.halt().is_none(), "M took the takeover from C");
    sync_pair(&mut m, &mut n, T0 + 23);
    let l = link_of(&mut n);
    assert!(l.acl.halt().is_none(), "N took the takeover from M");
    assert!(l.state().active_device(&nid).is_some());
    let ndev = clone_dev(&n);
    assert!(link_of(&mut n).write(&ndev, &mail("chat", "back"), T0 + 24).is_ok());
}

/// `admit`, returning the invite ticket the guest used (still in its hands after the join).
fn admit_ticket(host: &mut Node, guest: &mut Node, role: Role, now: u64) -> acl::InviteTicket {
    let hdev = clone_dev(host);
    let secret = link_of(host).invite(&hdev, role, 3600, true, false, now).unwrap();
    let link_id = link_of(host).id().to_owned();
    let gid = guest.id();
    let hello = sync::join_hello(&link_id, &guest.dev, &secret).unwrap();
    let mut door = JoinDoor::new();
    let entries = entries_of(door.on_frame(link_of(host), &hdev, &gid, hello, now).unwrap());
    let proposal = sync::join_proposal(&entries, &guest.dev, &secret, "guest", now).unwrap();
    let entries = entries_of(
        door.on_frame(link_of(host), &hdev, &gid, Frame::Join { proposal }, now)
            .unwrap(),
    );
    guest.link = Some(Link::adopt(None, entries, now).unwrap());
    secret
}

fn invite_op(now: u64) -> Op {
    Op::Invite(acl::Invite {
        invite: hex(&crypto::public_of(&acl::invite_key(&crypto::random32()))),
        role: Role::Reader,
        expires: now + 3600,
        single_use: true,
        approval: false,
    })
}

/// One `propose` frame through `sess` on `to` from `peer`: whether `to` kept it to relay, and
/// whether it signed a refusal.
fn propose_to(to: &mut Node, sess: &mut Session, peer: &str, p: Proposal, now: u64) -> (bool, bool, Vec<String>) {
    let dev = clone_dev(to);
    let o = sess
        .on_frame(link_of(to), &dev, peer, Frame::Propose { proposal: p }, now)
        .unwrap();
    let refusal = o.replies.iter().any(|f| matches!(f, Frame::Refusal { .. }));
    (!o.relay.is_empty(), refusal, o.refused)
}

/// R7-3 (probes `p3`, `p3b`): a relay kept any member's proposal and any join on a dead invite,
/// and the sequencer charged each refusal to the session peer: any member could make an honest
/// relay's fleet lose its allowance for a day (here, before it could relay the attacker's own
/// removal). Now a relay keeps only what holds on its chain (a join needs a live invite), and the
/// sequencer charges a refusal to the proposal's origin, so the relay pays nothing for what it
/// relays. A proposal signed with someone else's certificate charges the peer that sent it, never
/// the member it names.
#[test]
fn r7_p3_a_relay_keeps_only_what_holds_and_pays_nothing_for_what_it_relays() {
    let mut a = Node::new("a");
    let (mut x, mut m, mut w) = (Node::new("x"), Node::new("m"), Node::new("w"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut x, Role::Writer, T0 + 1);
    let ticket = admit_ticket(&mut a, &mut m, Role::Writer, T0 + 2);
    admit(&mut a, &mut w, Role::Writer, T0 + 3);
    let (adev, xdev, mdev) = (clone_dev(&a), clone_dev(&x), clone_dev(&m));
    let (xroot, mroot) = (x.dev.root_hex().to_owned(), m.dev.root_hex().to_owned());
    let (xid, mid, wid) = (x.id(), m.id(), w.id());
    link_of(&mut a).set_role(&adev, &xroot, Role::Admin, T0 + 4).unwrap();
    for n in [&mut x, &mut m, &mut w] {
        give_acl(&a, n, T0 + 5);
    }
    let relayed = |x: &Node| -> i64 {
        x.link
            .as_ref()
            .unwrap()
            .store
            .conn
            .query_row("SELECT count(*) FROM proposals WHERE mine = 0", [], |r| r.get(0))
            .unwrap()
    };
    // p3: M's junk joins on its used invite, from throwaway fleets: X keeps and relays none.
    let entries = link_of(&mut m).acl.all();
    let mut on_x = Session::new();
    // Each is charged to the invite, its origin; past the invite's allowance X drops the rest
    // without checking them.
    for i in 0..60u64 {
        let junk = Node::new(&format!("j{i}"));
        let p = sync::join_proposal(&entries, &junk.dev, &ticket, "junk", T0 + 10).unwrap();
        let (kept, _, why) = propose_to(&mut x, &mut on_x, &mid, p, T0 + 10);
        assert!(!kept, "a join on a used invite is relayed");
        let reason = if i < acl::MAX_MEMBER_PROPOSALS_PER_DAY as u64 {
            "live invite"
        } else {
            "origin reached"
        };
        assert!(why[0].contains(reason), "{i}: {why:?}");
    }
    // p3b: M's own proposals the sequencer would refuse (a writer inviting): none kept either.
    let mut on_x = Session::new();
    for i in 0..60 {
        let p = link_of(&mut m)
            .acl
            .propose_at(&mdev, &invite_op(T0 + 11), T0 + 11)
            .unwrap();
        let (kept, _, why) = propose_to(&mut x, &mut on_x, &mid, p, T0 + 11);
        assert!(!kept);
        // M is the peer and the origin: each distinct proposal is charged to M as their origin
        // (never to M as a peer, R8-1); past its allowance they are not checked.
        let reason = if i < acl::MAX_MEMBER_PROPOSALS_PER_DAY {
            "admin"
        } else {
            "origin reached"
        };
        assert!(why[0].contains(reason), "{i}: {why:?}");
    }
    assert_eq!(relayed(&x), 0);
    // A proposal under M's certificate but another key's signature charges the peer that sent
    // it (W), not M: W's allowance runs out, M's does not.
    let mut forger = Device::create(&root_from_phrase(&new_phrase()).unwrap(), "z", false, T0 - 10).unwrap();
    forger.cert = m.dev.cert.clone();
    let mut on_a_w = Session::new();
    let mut last = Vec::new();
    let (lid, t) = (link_of(&mut a).id().to_owned(), link_of(&mut a).acl.tip());
    for _ in 0..40 {
        let base = acl::Base {
            term: t.term,
            seq: t.seq,
        };
        let p = Proposal::sign(&forger, &lid, &invite_op(T0 + 12), base, T0 + 3600).unwrap();
        last = propose_to(&mut a, &mut on_a_w, &wid, p, T0 + 12).2;
    }
    assert!(last[0].contains("peer's fleet reached its daily allowance"), "{last:?}");
    // The sequencer is ahead of the relay: on X's chain M is an admin, on A's a writer again. X
    // keeps M's invites and relays them; A refuses each and charges M, its origin, not X.
    link_of(&mut a).set_role(&adev, &mroot, Role::Admin, T0 + 13).unwrap();
    give_acl(&a, &mut x, T0 + 13);
    give_acl(&a, &mut m, T0 + 13);
    link_of(&mut a).set_role(&adev, &mroot, Role::Writer, T0 + 14).unwrap();
    let (mut on_x, mut on_a) = (Session::new(), Session::new());
    let (mut refused, mut first) = (0, true);
    for k in 0..60u64 {
        let p = link_of(&mut m)
            .acl
            .propose_at(&mdev, &invite_op(T0 + 15), T0 + 15)
            .unwrap();
        let (kept, _, _) = propose_to(&mut x, &mut on_x, &mid, p.clone(), T0 + 15 + k);
        assert!(kept, "X relays what holds on its chain");
        let (_, signed, why) = propose_to(&mut a, &mut on_a, &xid, p, T0 + 15 + k);
        if first {
            assert!(signed, "M's first is refused with a signed reason, not as X's forgery");
            first = false;
        }
        refused += usize::from(signed);
        if !signed {
            assert!(why[0].contains("origin reached its daily allowance"), "{why:?}");
        }
    }
    assert_eq!(refused, acl::MAX_MEMBER_PROPOSALS_PER_DAY);
    // X's own proposal to remove M (a writer again, once X has A's chain) is still taken.
    give_acl(&a, &mut x, T0 + 99);
    let Acted::Proposed(p) = link_of(&mut x).remove_member(&xdev, &mroot, T0 + 100).unwrap() else {
        panic!("X does not sequence")
    };
    let o = on_a
        .on_frame(link_of(&mut a), &adev, &xid, Frame::Propose { proposal: p }, T0 + 101)
        .unwrap();
    assert_eq!(o.acl_added, 1, "{:?}", o.refused);
    assert!(link_of(&mut a).state().members[&mroot].removed);
}

/// R7-6: an ex-sequencer's key signed a fresh refusal at a position of its old term, and relays
/// dropped the proposal (one whose base was in that term). Only the current sequencer's refusal
/// is taken now.
#[test]
fn r7_6_an_ex_sequencers_fresh_refusal_is_not_taken() {
    let mut a = Node::new("a");
    let (mut e, mut x, mut c) = (Node::new("e"), Node::new("x"), Node::new("c"));
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut e, Role::Writer, T0 + 1);
    admit(&mut a, &mut x, Role::Writer, T0 + 2);
    admit(&mut a, &mut c, Role::Writer, T0 + 3);
    let (adev, edev, xdev, cdev) = (clone_dev(&a), clone_dev(&e), clone_dev(&x), clone_dev(&c));
    let (eroot, xroot) = (e.dev.root_hex().to_owned(), x.dev.root_hex().to_owned());
    link_of(&mut a).set_role(&adev, &eroot, Role::Admin, T0 + 4).unwrap();
    link_of(&mut a).handoff(&adev, &e.id(), T0 + 5).unwrap();
    give_acl(&a, &mut e, T0 + 6);
    let _ = link_of(&mut e).invite_acted(&edev, T0 + 7);
    for n in [&mut x, &mut c] {
        give_acl(&e, n, T0 + 8);
    }
    // X proposes to leave while E sequences; C keeps the proposal to relay.
    let Acted::Proposed(p) = link_of(&mut x).remove_member(&xdev, &xroot, T0 + 9).unwrap() else {
        panic!("X does not sequence")
    };
    assert!(matches!(
        link_of(&mut c).offer(&cdev, &p, T0 + 9).unwrap(),
        Offered::Queued
    ));
    let at = link_of(&mut c).acl.tip();
    assert_eq!((at.term, at.seq), (p.base.term, p.base.seq));
    // E hands back to A. Then E's key signs a refusal at a position of its old term.
    link_of(&mut e).handoff(&edev, &a.id(), T0 + 10).unwrap();
    give_acl(&e, &mut a, T0 + 11);
    give_acl(&a, &mut c, T0 + 11);
    let lid = link_of(&mut c).id().to_owned();
    let r = ProposalRefusal::sign(&edev, &lid, &p.id().unwrap(), "no", at).unwrap();
    assert!(!link_of(&mut c).take_refusal(&cdev, &r).unwrap());
    assert_eq!(link_of(&mut c).outstanding(32).unwrap().len(), 1, "C keeps relaying it");
    // The current sequencer includes it.
    assert!(matches!(
        link_of(&mut a).offer(&adev, &p, T0 + 12).unwrap(),
        Offered::Included(_)
    ));
}

// ---------------------------------------------------------------------------- property test

use proptest::prelude::*;

/// Six fleets for round 8: A (owner, sequencer), X (an admin), Y (a reader), M, R (a relay) and
/// W (writers), all holding A's chain.
fn sextet() -> [Node; 6] {
    let mut a = Node::new("a");
    let (mut x, mut y, mut m, mut r, mut w) = (
        Node::new("x"),
        Node::new("y"),
        Node::new("m"),
        Node::new("r"),
        Node::new("w"),
    );
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut x, Role::Writer, T0 + 1);
    admit(&mut a, &mut y, Role::Reader, T0 + 2);
    admit(&mut a, &mut m, Role::Writer, T0 + 3);
    admit(&mut a, &mut r, Role::Writer, T0 + 4);
    admit(&mut a, &mut w, Role::Writer, T0 + 5);
    let adev = clone_dev(&a);
    let xroot = x.dev.root_hex().to_owned();
    link_of(&mut a).set_role(&adev, &xroot, Role::Admin, T0 + 6).unwrap();
    for n in [&mut x, &mut y, &mut m, &mut r, &mut w] {
        give_acl(&a, n, T0 + 7);
    }
    [a, x, y, m, r, w]
}

/// R8-1: a refusal was charged to the proposal's origin on every replay. A member replayed one
/// proposal of X's that an honest change had made fail (A made Y a writer before X's proposal to
/// do the same reached it) to relay R, over fresh sessions: every replay cost X's fleet one of its
/// 512 a day, and because peers were charged under the same key, X's own devices could then relay
/// nothing to R, X's removal of the attacker included. Now an origin is charged once per
/// proposal, and a peer's charges are kept apart from its fleet's charges as an origin.
#[test]
fn r8_1_replaying_a_failing_proposal_charges_its_origin_once() {
    let [mut a, mut x, mut y, mut m, mut r, mut w] = sextet();
    let (adev, xdev, wdev) = (clone_dev(&a), clone_dev(&x), clone_dev(&w));
    let (xroot, yroot, mroot, wroot) = (
        x.dev.root_hex().to_owned(),
        y.dev.root_hex().to_owned(),
        m.dev.root_hex().to_owned(),
        w.dev.root_hex().to_owned(),
    );
    let Acted::Proposed(p) = link_of(&mut x).set_role(&xdev, &yroot, Role::Writer, T0 + 8).unwrap() else {
        panic!("X does not sequence")
    };
    link_of(&mut a).set_role(&adev, &yroot, Role::Writer, T0 + 9).unwrap();
    for n in [&mut x, &mut y, &mut m, &mut r, &mut w] {
        give_acl(&a, n, T0 + 10);
    }
    let mid = m.id();
    for i in 0..600u64 {
        // A fresh session each time (a reconnect): no frame budget is reached.
        let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &mid, p.clone(), T0 + 20 + i);
        assert!(!kept);
        assert!(why[0].contains("already has that role"), "{i}: {why:?}");
    }
    assert_eq!(
        link_of(&mut r).charged_origin(&xroot, T0 + 700),
        1,
        "one proposal, one charge"
    );
    assert_eq!(link_of(&mut r).charged_peer(m.dev.root_hex(), T0 + 700), 0);
    // X's removal of M, from X's own device, is kept to relay; so is W's leave relayed by X.
    let Acted::Proposed(rm) = link_of(&mut x).remove_member(&xdev, &mroot, T0 + 700).unwrap() else {
        panic!("X does not sequence")
    };
    let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &x.id(), rm, T0 + 701);
    assert!(kept, "{why:?}");
    let Acted::Proposed(leave) = link_of(&mut w).remove_member(&wdev, &wroot, T0 + 702).unwrap() else {
        panic!("W does not sequence")
    };
    let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &x.id(), leave, T0 + 703);
    assert!(kept, "{why:?}");
    // The charge never pre-empts the proposal: once Y is a reader again, X's proposal holds, and
    // R keeps it and A includes it.
    link_of(&mut a).set_role(&adev, &yroot, Role::Reader, T0 + 704).unwrap();
    give_acl(&a, &mut r, T0 + 705);
    let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &mid, p.clone(), T0 + 706);
    assert!(kept, "{why:?}");
    assert!(matches!(
        link_of(&mut a).offer_from(&adev, &p, &r.id(), T0 + 707).unwrap(),
        Offered::Included(_)
    ));
    // On the sequencer too: X's proposal to make W a reader fails once A did it first; replays
    // at a moving tip are refused again, each with a fresh signed refusal, and charged once.
    let Acted::Proposed(q) = link_of(&mut x).set_role(&xdev, &wroot, Role::Reader, T0 + 708).unwrap() else {
        panic!("X does not sequence")
    };
    link_of(&mut a).set_role(&adev, &wroot, Role::Reader, T0 + 709).unwrap();
    let before = link_of(&mut a).charged_origin(&xroot, T0 + 710);
    for i in 0..20u64 {
        let (_, signed, why) = propose_to(&mut a, &mut Session::new(), &mid, q.clone(), T0 + 710 + i);
        assert!(signed, "{why:?}");
        // The tip moves between replays.
        let rotated = link_of(&mut a).rotate_key(&adev, T0 + 710 + i);
        assert!(rotated.is_ok(), "{rotated:?}");
    }
    assert_eq!(link_of(&mut a).charged_origin(&xroot, T0 + 740), before + 1);
    // An origin's spent allowance does not silence its fleet as a peer: X's own distinct failing
    // proposals (W is a reader already, which X has not seen), relayed by Y, use up X's allowance as an origin at R;
    // X's device still relays Y's leave to R.
    give_acl(&a, &mut r, T0 + 741);
    let yid = y.id();
    let spent =
        |r: &mut Node, t: u64| link_of(r).charged_origin(&xroot, t) + link_of(r).state().proposals_today(&xroot, t);
    let left = acl::MAX_ADMIN_PROPOSALS_PER_DAY - spent(&mut r, T0 + 742);
    for i in 0..left as u64 {
        let Acted::Proposed(q) = link_of(&mut x)
            .set_role(&xdev, &wroot, Role::Reader, T0 + 742 + i)
            .unwrap()
        else {
            panic!("X does not sequence")
        };
        let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &yid, q, T0 + 742 + i);
        assert!(!kept && why[0].contains("already has that role"), "{i}: {why:?}");
    }
    let t = T0 + 742 + left as u64;
    assert_eq!(spent(&mut r, t), acl::MAX_ADMIN_PROPOSALS_PER_DAY);
    let ydev = clone_dev(&y);
    let Acted::Proposed(leave) = link_of(&mut y).remove_member(&ydev, &yroot, t).unwrap() else {
        panic!("Y does not sequence")
    };
    let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &x.id(), leave, t + 1);
    assert!(kept, "{why:?}");
}

/// Records of `n` bytes of content each, `count` of them, written by `node` at `now`.
fn feed(node: &mut Node, count: usize, n: usize, now: u64) {
    let dev = clone_dev(node);
    let pad = "x".repeat(n);
    for i in 0..count {
        link_of(node)
            .write(&dev, &mail("chat", &format!("{i} {pad}")), now)
            .unwrap();
    }
}

/// The record bytes in `frames`, as `record_frames` counts them.
fn record_bytes(frames: &[Frame]) -> usize {
    frames
        .iter()
        .map(|f| match f {
            Frame::Records { records } => records
                .iter()
                .map(|r| r.ct.as_ref().map_or(0, String::len) + 1024)
                .sum(),
            _ => 0,
        })
        .sum()
}

/// R8-2: `want` frames (and `heads` pages) were not counted against any budget, and each answer
/// loaded every record of each author from the store before keeping 4,096. A member asked for the
/// whole feed again and again (probe `p2`: 300 wants in a minute, 7.5 GB of replies, 39.5 s of
/// CPU under the daemon's lock). Now record-side frames are counted per session, and the record
/// bytes a session sends in answers are capped per minute.
#[test]
fn r8_2_wants_and_heads_pages_are_budgeted_per_session() {
    let (mut a, mut b, _m) = trio_with(Policy {
        rate_per_hour: 100_000,
        ..Policy::default()
    });
    feed(&mut a, 200, 100_000, T0 + 3);
    let (adev, bid) = (clone_dev(&a), b.id());
    let mut s = Session::new();
    let (mut sent, mut ended) = (0usize, None);
    for i in 0..400 {
        let want = Frame::Want {
            heads: Default::default(),
        };
        match s.on_frame(link_of(&mut a), &adev, &bid, want, T0 + 60) {
            Ok(o) => sent += record_bytes(&o.replies),
            Err(e) => {
                ended = Some((i, e.to_string()));
                break;
            }
        }
    }
    let one = 100_000 * 2 + 1024;
    assert!(
        sent <= sync::RECORD_BYTES_PER_MIN + one,
        "{sent} bytes of records in one minute"
    );
    let (i, why) = ended.expect("the session ends past its frame budget");
    assert_eq!(i as u32, sync::MAX_RECORD_FRAMES_PER_MIN, "{why}");
    assert!(why.contains("too many record frames"), "{why}");
    // Heads pages count against the same budget.
    let mut s = Session::new();
    let bdev = clone_dev(&b);
    let mut hello = sync::hello(link_of(&mut b), &bdev).unwrap().remove(0);
    if let Frame::Hello { more, .. } = &mut hello {
        *more = true;
    }
    s.on_frame(link_of(&mut a), &adev, &bid, hello, T0 + 120).unwrap();
    let mut ended = None;
    for i in 0..400 {
        let page = Frame::Heads {
            heads: Default::default(),
            more: true,
        };
        if let Err(e) = s.on_frame(link_of(&mut a), &adev, &bid, page, T0 + 120) {
            ended = Some((i, e.to_string()));
            break;
        }
    }
    let (i, why) = ended.expect("heads pages are budgeted");
    assert!(i as u32 <= sync::MAX_RECORD_FRAMES_PER_MIN, "{i}: {why}");
}

/// Round 8 (found while fixing R8-2): records a peer pushes were not counted either, and each costs
/// a signature check, duplicates included. Now a session looks at most at
/// `RECORD_BYTES_IN_PER_MIN` of them a minute and asks for the rest again at the next ping.
#[test]
fn r8_2_records_a_peer_sends_are_budgeted() {
    let (mut a, mut b, _m) = trio_with(Policy {
        rate_per_hour: 100_000,
        ..Policy::default()
    });
    feed(&mut a, 400, 100_000, T0 + 3);
    let all = link_of(&mut a).missing_for(&BTreeMap::new(), usize::MAX).unwrap();
    let (aid, bdev) = (a.id(), clone_dev(&b));
    let mut s = Session::new();
    let mut looked = 0usize;
    // The same frames twice: duplicates count too.
    for _ in 0..2 {
        for f in sync::record_frames(all.clone()) {
            s.on_frame(link_of(&mut b), &bdev, &aid, f, T0 + 60).unwrap();
        }
    }
    let held = link_of(&mut b).store.head(&aid).unwrap().map_or(0, |h| h.0) as usize;
    for r in &all[..held] {
        looked += r.frame_cost();
    }
    assert!(held < all.len(), "B looked at every record pushed");
    assert!(looked <= sync::RECORD_BYTES_IN_PER_MIN, "{looked}");
    // At the next ping B asks for the rest.
    let o = s
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::Ping {}, T0 + 120)
        .unwrap();
    assert!(
        o.replies.iter().any(|f| matches!(f, Frame::Want { .. })),
        "{:?}",
        o.replies.len()
    );
}

/// R8-2: an answer reads from the store only what it sends (plus at most a page): `Store::range`
/// had no LIMIT, so each answer loaded every record of each author it named.
#[test]
fn r8_2_a_store_range_reads_at_most_its_limit() {
    let (mut a, _b, _m) = trio();
    feed(&mut a, 300, 10, T0 + 3);
    let aid = a.id();
    let l = link_of(&mut a);
    assert_eq!(l.store.range(&aid, 0, u64::MAX, 7).unwrap().len(), 7);
    assert_eq!(l.store.range(&aid, 290, u64::MAX, 100).unwrap().len(), 10);
    let (sent, cut) = l
        .missing_for_authors(&BTreeMap::new(), 100, usize::MAX, |_| true)
        .unwrap();
    assert_eq!((sent.len(), cut), (100, true));
    let one = sent[0].frame_cost();
    let (sent, cut) = l
        .missing_for_authors(&BTreeMap::new(), 4096, 5 * one, |_| true)
        .unwrap();
    assert_eq!((sent.len(), cut), (5, true));
    let (sent, cut) = l.missing_for_authors(&BTreeMap::new(), 4096, 0, |_| true).unwrap();
    assert_eq!((sent.len(), cut), (0, true));
    let (sent, cut) = l
        .missing_for_authors(&BTreeMap::new(), 4096, usize::MAX, |_| true)
        .unwrap();
    assert_eq!((sent.len(), cut), (300, false));
    // The hourly quota's count reads an index, not every record of the author (each received
    // record runs it: 4,096 records took 4.2 s to store in release without it, 1.7 s with it).
    let plan: String = l
        .store
        .conn
        .query_row(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM records WHERE author = ?1 AND received_at >= ?2",
            rusqlite::params![aid, 0],
            |r| r.get(3),
        )
        .unwrap();
    assert!(plan.contains("records_by_author_received"), "{plan}");
}

/// R8-2: the record budget still lets an honest replica catch up with a large feed: a feed larger
/// than a minute's budget arrives over a few minutes of one session (asked again at each ping
/// when the budget cut an answer short), and a feed of more records than one pass (4,096)
/// arrives within one session.
#[test]
fn r8_2_honest_catch_up_of_a_large_feed_converges() {
    for (count, n) in [(200usize, 100_000usize), (5000, 100)] {
        let (mut a, mut b, _m) = trio_with(Policy {
            rate_per_hour: 100_000,
            ..Policy::default()
        });
        feed(&mut a, count, n, T0 + 3);
        let bytes: usize = link_of(&mut a)
            .missing_for(&BTreeMap::new(), usize::MAX)
            .unwrap()
            .iter()
            .map(|r| r.ct.as_ref().map_or(0, String::len) + 1024)
            .sum();
        let minutes = bytes.div_ceil(sync::RECORD_BYTES_PER_MIN) as u64 + 1;
        let aid = a.id();
        let held = |b: &mut Node| link_of(b).store.head(&aid).unwrap().map_or(0, |h| h.0);
        let (adev, bdev, bid) = (clone_dev(&a), clone_dev(&b), b.id());
        let (mut sa, mut sb) = (Session::new(), Session::new());
        let mut to_b = sync::hello(link_of(&mut a), &adev).unwrap();
        let mut to_a = sync::hello(link_of(&mut b), &bdev).unwrap();
        let mut now = T0 + 60;
        let mut took = None;
        'minutes: for minute in 0..=minutes + 1 {
            for _ in 0..400 {
                if to_a.is_empty() && to_b.is_empty() {
                    break;
                }
                for f in std::mem::take(&mut to_b) {
                    to_a.extend(sb.on_frame(link_of(&mut b), &bdev, &aid, f, now).unwrap().replies);
                }
                for f in std::mem::take(&mut to_a) {
                    to_b.extend(sa.on_frame(link_of(&mut a), &adev, &bid, f, now).unwrap().replies);
                }
            }
            if held(&mut b) == count as u64 {
                took = Some(minute);
                break 'minutes;
            }
            // A minute passes; each side pings.
            now += 60;
            to_a.push(Frame::Ping {});
            to_b.push(Frame::Ping {});
        }
        let took = took.unwrap_or_else(|| panic!("{count} records: B holds {} after {minutes} minutes", held(&mut b)));
        assert!(took <= minutes, "{count} records took {took} minutes");
    }
}

/// A live session between `a` and `b` as linkd runs it: each side handles its peer's frames in
/// arrival order, one at a time, and each pings every 45 s, for `minutes` of simulated time from
/// `start`. Returns the frames that crossed; panics if either side ends the session.
fn live(a: &mut Node, b: &mut Node, start: u64, minutes: u64) -> usize {
    use std::collections::VecDeque;
    let (aid, bid) = (a.id(), b.id());
    let (adev, bdev) = (clone_dev(a), clone_dev(b));
    let (mut sa, mut sb) = (Session::new(), Session::new());
    let mut to_a: VecDeque<Frame> = sync::hello(link_of(b), &bdev).unwrap().into();
    let mut to_b: VecDeque<Frame> = sync::hello(link_of(a), &adev).unwrap().into();
    let mut n = 0;
    let mut t = start;
    while t < start + minutes * 60 {
        for _ in 0..100_000 {
            if to_a.is_empty() && to_b.is_empty() {
                break;
            }
            if let Some(f) = to_b.pop_front() {
                n += 1;
                to_a.extend(sb.on_frame(link_of(b), &bdev, &aid, f, t).unwrap().replies);
            }
            if let Some(f) = to_a.pop_front() {
                n += 1;
                to_b.extend(sa.on_frame(link_of(a), &adev, &bid, f, t).unwrap().replies);
            }
        }
        t += 45;
        to_a.push_back(Frame::Ping {});
        to_b.push_back(Frame::Ping {});
    }
    n
}

fn held_of(n: &mut Node, author: &str) -> u64 {
    link_of(n).store.head(author).unwrap().map_or(0, |h| h.0)
}

/// R9-1 (probe `q1`), under the default policy: records written at chain positions the asker
/// lacks. The first record of the author waited (`Pending`, one per author) and the rest came as
/// gaps with no progress, so nothing asked again; the chain then arrived and stored the waiting
/// record, and the other 49 never came for the life of the session (pings asked for nothing).
/// Now the chain's arrival asks for them at once, and a tip that moves through another session
/// asks at the next ping.
#[test]
fn r9_1_records_written_at_chain_positions_the_asker_lacks_arrive_in_one_session() {
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    let mut d = Node::new("d");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    // B lacks D's admission, and A's records are written past it.
    admit(&mut a, &mut d, Role::Writer, T0 + 2);
    feed(&mut a, 50, 10, T0 + 4);
    let aid = a.id();
    assert!(link_of(&mut b).acl.tip().seq < link_of(&mut a).acl.tip().seq);
    live(&mut a, &mut b, T0 + 100, 10);
    assert_eq!(held_of(&mut b, &aid), 50, "B caught up within the session");
    // The chain through another session: B's session with A only learns that its tip moved.
    let (adev, bdev, bid) = (clone_dev(&a), clone_dev(&b), b.id());
    let mut e = Node::new("e");
    admit(&mut a, &mut e, Role::Writer, T0 + 200);
    feed(&mut a, 20, 10, T0 + 201);
    let mut s = Session::new();
    let hello = sync::hello(link_of(&mut b), &bdev).unwrap().remove(0);
    s.on_frame(link_of(&mut a), &adev, &bid, hello, T0 + 202).unwrap();
    let mut sb = Session::new();
    let ahello = sync::hello(link_of(&mut a), &adev).unwrap().remove(0);
    // B takes A's hello but not its chain, then A's records: they wait.
    let o = sb.on_frame(link_of(&mut b), &bdev, &aid, ahello, T0 + 202).unwrap();
    assert!(o.replies.iter().any(|f| matches!(f, Frame::AclWant { .. })));
    let missing = link_of(&mut a)
        .missing_for(&link_of(&mut b).heads().unwrap(), 4096)
        .unwrap();
    for f in sync::record_frames(missing) {
        sb.on_frame(link_of(&mut b), &bdev, &aid, f, T0 + 203).unwrap();
    }
    assert_eq!(held_of(&mut b, &aid), 50, "the new records wait for the chain");
    let o = sb
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::Ping {}, T0 + 240)
        .unwrap();
    assert!(
        !o.replies.iter().any(|f| matches!(f, Frame::Want { .. })),
        "nothing to ask while the tip has not moved"
    );
    give_acl(&a, &mut b, T0 + 250);
    // The ping after the tip moved asks once; the answer brings all 20.
    let o = sb
        .on_frame(link_of(&mut b), &bdev, &aid, Frame::Ping {}, T0 + 285)
        .unwrap();
    let want = o
        .replies
        .into_iter()
        .find(|f| matches!(f, Frame::Want { .. }))
        .expect("the ping after the tip moved asks again");
    let o = s.on_frame(link_of(&mut a), &adev, &bid, want, T0 + 286).unwrap();
    for f in o.replies {
        sb.on_frame(link_of(&mut b), &bdev, &aid, f, T0 + 287).unwrap();
    }
    assert_eq!(held_of(&mut b, &aid), 70);
}

/// R9-1 (probe `q6`), under the default policy (600 records an hour): a backlog of 1,000 records
/// of one author, written over three hours. The quota stopped it at 600 with a gap and no
/// progress, and nothing asked again for the life of the session. Now an author over quota is
/// told apart from a gap, and the first ping after the quota admits more asks again.
#[test]
fn r9_1_a_backlog_over_the_hourly_quota_arrives_once_the_quota_admits_it() {
    let mut a = Node::new("a");
    let mut b = Node::new("b");
    a.link = Some(Link::create(None, &a.dev, "p", "fleet-a", Policy::default(), T0).unwrap());
    admit(&mut a, &mut b, Role::Writer, T0 + 1);
    let adev = clone_dev(&a);
    for i in 0..1000u64 {
        link_of(&mut a)
            .write(&adev, &mail("chat", &format!("r{i}")), T0 + 10 + i * 11)
            .unwrap();
    }
    let aid = a.id();
    let start = T0 + 20_000;
    // One session of 65 minutes: the quota holds for the first hour, with no asking in a loop,
    // and the first ping after it admits more asks for the rest.
    let n = live(&mut a, &mut b, start, 65);
    assert_eq!(held_of(&mut b, &aid), 1000, "B caught up within the session");
    assert!(
        n < 250,
        "{n} frames: the over-quota batch was asked for again and again"
    );
}

/// R9-4 (probe `q5`): records `conflicts` sent for heads a peer names with a made-up id counted
/// against no budget. A member that named every author's seq 1 with a made-up id in each of its
/// 120 record frames a minute drew 960 records of 256 KiB (20x the 16 MiB budget, about 2,300x
/// the bytes it sent). Now those records count against the record budget, none is sent once it is
/// spent, and each claim is answered once a minute across the peer's sessions.
#[test]
fn r9_4_records_sent_for_made_up_head_ids_are_budgeted_and_sent_once() {
    let (mut a, mut b, _m) = trio();
    let adev = clone_dev(&a);
    let mut devs = vec![clone_dev(&a)];
    for k in 0..7u64 {
        let extra = Device::create(&a.root, &format!("a{k}"), false, T0 - 10).unwrap();
        link_of(&mut a)
            .add_device(&adev, extra.cert.clone(), T0 + 3 + k)
            .unwrap();
        devs.push(extra);
    }
    let big = "y".repeat(200_000);
    for d in &devs {
        link_of(&mut a).write(d, &mail("chat", &big), T0 + 20).unwrap();
    }
    give_acl(&a, &mut b, T0 + 21);
    let bid = b.id();
    let heads = sync::heads_of(link_of(&mut a)).unwrap();
    assert_eq!(heads.len(), 8);
    let lie = |id: String| -> sync::Heads {
        heads
            .keys()
            .map(|k| (k.clone(), sync::HeadRef { seq: 1, id: id.clone() }))
            .collect()
    };
    let records_in = |frames: &[Frame]| -> usize {
        frames
            .iter()
            .map(|f| match f {
                Frame::Records { records } => records.len(),
                _ => 0,
            })
            .sum()
    };
    // The same claims, 100 times in one minute: each answered once.
    let mut s = Session::new();
    let mut sent = 0;
    for _ in 0..100 {
        let o = s
            .on_frame(
                link_of(&mut a),
                &adev,
                &bid,
                Frame::Want {
                    heads: lie("00".repeat(32)),
                },
                T0 + 60,
            )
            .unwrap();
        sent += records_in(&o.replies);
    }
    assert_eq!(sent, 8, "each claim is answered once");
    // A reconnect shares the budget: the same claims get nothing more this minute.
    let mut again = Session::new();
    again.budget = s.budget.clone();
    let o = again
        .on_frame(
            link_of(&mut a),
            &adev,
            &bid,
            Frame::Synced {
                heads: lie("00".repeat(32)),
                more: false,
            },
            T0 + 61,
        )
        .unwrap();
    assert_eq!(
        records_in(&o.replies),
        0,
        "a reconnect does not refill the claims answered"
    );
    // Claims with ever new made-up ids: the record budget bounds them.
    let mut s = Session::new();
    let mut bytes = 0;
    for i in 0..100u32 {
        let o = s
            .on_frame(
                link_of(&mut a),
                &adev,
                &bid,
                Frame::Want {
                    heads: lie(format!("{i:064x}")),
                },
                T0 + 120,
            )
            .unwrap();
        bytes += record_bytes(&o.replies);
    }
    let one = 200_000 * 2 + 1024;
    assert!(
        bytes <= sync::RECORD_BYTES_PER_MIN + one,
        "{bytes} bytes of records for made-up head ids in one minute"
    );
    assert!(
        heads.keys().all(|k| !link_of(&mut a).store.frozen(k).unwrap()),
        "unsigned claims freeze nobody"
    );
}

/// R9-2 (probe `q2`): `ping` frames and empty or fully cut `records` frames counted against no
/// budget, and each built the set of every device of the link to check membership: a million of
/// either in a minute were all taken. Now every frame counts against `MAX_FRAMES_PER_MIN` per
/// (link, peer), and membership is a lookup in a set kept per held tip.
#[test]
fn r9_2_every_frame_counts_and_membership_is_a_lookup() {
    let (mut a, mut b, _m) = trio();
    let (adev, bdev, bid) = (clone_dev(&a), clone_dev(&b), b.id());
    let hello = sync::hello(link_of(&mut b), &bdev).unwrap().remove(0);
    let builds = |_: &mut Node| acl::AclChain::sync_builds();
    for (k, f) in [Frame::Ping {}, Frame::Records { records: vec![] }]
        .into_iter()
        .enumerate()
    {
        let now = T0 + 60 * (1 + k as u64);
        let mut s = Session::new();
        s.on_frame(link_of(&mut a), &adev, &bid, hello.clone(), now).unwrap();
        let before = builds(&mut a);
        let mut ended = None;
        for i in 1..1_000_000u32 {
            if let Err(e) = s.on_frame(link_of(&mut a), &adev, &bid, f.clone(), now) {
                ended = Some((i, e.to_string()));
                break;
            }
        }
        let (i, why) = ended.expect("the session ends past the frame budget");
        assert_eq!(i, sync::MAX_FRAMES_PER_MIN, "{f:?}: {why}");
        assert!(why.contains("too many frames"), "{why}");
        assert!(builds(&mut a) <= before + 1, "membership was built per frame");
        // A reconnect shares the budget.
        let mut again = Session::new();
        again.budget = s.budget.clone();
        assert!(
            again
                .on_frame(link_of(&mut a), &adev, &bid, hello.clone(), now)
                .is_err()
        );
        // The next minute takes frames again.
        again
            .on_frame(link_of(&mut a), &adev, &bid, hello.clone(), now + 60)
            .unwrap();
    }
    // The kept set follows the chain: a removal takes effect at the next frame.
    let mut s = Session::new();
    s.on_frame(link_of(&mut a), &adev, &bid, hello, T0 + 300).unwrap();
    let before = builds(&mut a);
    let broot = b.dev.root_hex().to_owned();
    link_of(&mut a).remove_member(&adev, &broot, T0 + 301).unwrap();
    let err = s
        .on_frame(
            link_of(&mut a),
            &adev,
            &bid,
            Frame::Records { records: vec![] },
            T0 + 302,
        )
        .unwrap_err();
    assert!(err.to_string().contains("member"), "{err}");
    assert!(
        builds(&mut a) <= before + 2,
        "the sets are built again once, for the new tip"
    );
}

/// Round 9 (the reviewer's observation on R8-1): an origin's charge for a proposal was
/// remembered for a day, while the proposal can be replayed for 7. One failing proposal could be
/// charged to its origin again once a day. Now the charge is remembered until the proposal
/// expires, and still counts against the allowance for one day only.
#[test]
fn r9_an_origin_is_charged_once_for_a_proposal_over_its_whole_life() {
    let [mut a, mut x, y, mut m, mut r, _w] = sextet();
    let (adev, xdev) = (clone_dev(&a), clone_dev(&x));
    let (xroot, yroot) = (x.dev.root_hex().to_owned(), y.dev.root_hex().to_owned());
    let Acted::Proposed(p) = link_of(&mut x).set_role(&xdev, &yroot, Role::Writer, T0 + 8).unwrap() else {
        panic!("X does not sequence")
    };
    assert!(p.expires >= T0 + 8 + 6 * DAY);
    link_of(&mut a).set_role(&adev, &yroot, Role::Writer, T0 + 9).unwrap();
    for n in [&mut x, &mut m, &mut r] {
        give_acl(&a, n, T0 + 10);
    }
    let mid = m.id();
    let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &mid, p.clone(), T0 + 20);
    assert!(!kept && why[0].contains("already has that role"), "{why:?}");
    assert_eq!(link_of(&mut r).charged_origin(&xroot, T0 + 21), 1);
    // Replays on each later day of the proposal's life: refused, and not charged again.
    for day in 1..7u64 {
        let t = T0 + 20 + day * DAY + 60;
        let (kept, _, why) = propose_to(&mut r, &mut Session::new(), &mid, p.clone(), t);
        assert!(!kept && why[0].contains("already has that role"), "day {day}: {why:?}");
        assert_eq!(
            link_of(&mut r).charged_origin(&xroot, t + 1),
            0,
            "day {day}: X was charged again for the same proposal"
        );
    }
}

fn cases(default: u32) -> u32 {
    std::env::var("PROPTEST_CASES")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(default)
}

proptest! {
    #![proptest_config(ProptestConfig { cases: cases(8), ..ProptestConfig::default() })]

    /// Random actions on random replicas (proposals from those that do not sequence), random
    /// sync sessions, then a full round: every replica holds the same chain and state.
    #[test]
    fn replicas_that_sync_agree(steps in proptest::collection::vec((0usize..4, 0usize..6, 0usize..4), 1..24)) {
        let (mut a, b, c, m) = quartet();
        let adev = clone_dev(&a);
        let broot = b.dev.root_hex().to_owned();
        link_of(&mut a).set_role(&adev, &broot, Role::Admin, T0 + 5).unwrap();
        let mut nodes = [a, b, c, m];
        let mut ts = T0 + 10;
        for (who, what, with) in steps {
            ts += 13;
            let dev = clone_dev(&nodes[who]);
            let roots: Vec<String> = nodes.iter().map(|n| n.dev.root_hex().to_owned()).collect();
            let target = roots[(who + 1 + what) % 4].clone();
            let link = link_of(&mut nodes[who]);
            let _ = match what {
                0 => link.invite(&dev, Role::Reader, 3600, true, false, ts).map(|_| ()),
                1 => link.rotate_key(&dev, ts).map(|_| ()),
                2 => link.set_role(&dev, &target, Role::Reader, ts).map(|_| ()),
                3 => link.set_role(&dev, &target, Role::Writer, ts).map(|_| ()),
                4 => link.write(&dev, &mail("chat", "x"), ts).map(|_| ()),
                _ => link.upkeep(&dev, ts).map(|_| ()),
            };
            if with != who {
                let (lo, hi) = (who.min(with), who.max(with));
                let (left, right) = nodes.split_at_mut(hi);
                sync_pair(&mut left[lo], &mut right[0], ts);
            }
        }
        for _ in 0..2 {
            for i in 0..4 {
                for j in (i + 1)..4 {
                    let (left, right) = nodes.split_at_mut(j);
                    ts += 1;
                    sync_pair(&mut left[i], &mut right[0], ts);
                }
            }
        }
        let tips: BTreeSet<String> = nodes.iter().map(|n| format!("{:?}", n.link.as_ref().unwrap().acl.tip())).collect();
        prop_assert_eq!(tips.len(), 1, "{:?}", tips);
        let epochs: BTreeSet<u64> = nodes.iter().map(|n| n.link.as_ref().unwrap().state().epoch).collect();
        prop_assert_eq!(epochs.len(), 1);
    }
}
