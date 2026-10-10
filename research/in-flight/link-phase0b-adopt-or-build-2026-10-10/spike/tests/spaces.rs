//! Phase 0b criteria 3 and 4 (pull role, rotation on removal) plus robustness probes, run
//! against p2panda-spaces 0.7.1 through its own `test_utils` harness (SQLite via sqlx, in memory).
use std::borrow::Borrow;

use p2panda_auth::Access;
use p2panda_auth::group::{GroupAction, GroupMember};
use p2panda_core::traits::Digest;
use p2panda_spaces::test_utils::{TestForge, TestOperation, TestPeer};
use p2panda_spaces::{Event, Forge, SpaceId, SpacesArgs};

async fn peers(n: u8) -> Vec<TestPeer> {
    let mut ps = vec![];
    for i in 0..n {
        ps.push(TestPeer::new(i).await);
    }
    for a in &ps {
        for b in &ps {
            if a.id != b.id {
                a.manager.register_member(&b.manager.me().await.unwrap()).await.unwrap();
            }
        }
    }
    ps
}

/// Persist and process messages in order; return a summary of events (or the error).
async fn deliver(p: &TestPeer, msgs: &[TestOperation]) -> Vec<String> {
    let mut out = vec![];
    for m in msgs {
        p.persist_operation(m).await.unwrap();
        match p.manager.process_persisted(m).await {
            Ok(evs) => out.extend(evs.into_iter().map(|e| match e {
                Event::Application { data, .. } => {
                    format!("APP:{}", String::from_utf8_lossy(&data))
                }
                other => format!("{:?}", other).chars().take(40).collect(),
            })),
            Err(e) => out.push(format!("ERR:{e}")),
        }
    }
    out
}

fn secret_id(m: &TestOperation) -> [u8; 32] {
    let SpacesArgs::Application { group_secret_id, .. } = m.borrow() else { panic!() };
    *group_secret_id
}

fn direct_recipients(m: &TestOperation) -> Vec<String> {
    let SpacesArgs::SpaceMembership { direct_messages, .. } = m.borrow() else { panic!() };
    direct_messages.iter().map(|d| d.recipient.to_hex()[..8].to_string()).collect()
}

fn apps(evs: &[String]) -> Vec<&String> {
    evs.iter().filter(|e| e.starts_with("APP:") || e.starts_with("ERR:")).collect()
}

#[tokio::test]
async fn c4_removal_rotates_secret_and_history_stays_readable() {
    let ps = peers(4).await;
    let (alice, bob, carol, dave) = (&ps[0], &ps[1], &ps[2], &ps[3]);
    let sid = SpaceId::digest(b"c4");
    let (space, create) = alice
        .manager
        .create_space_persisted(sid, &[(bob.manager.id(), Access::read()), (carol.manager.id(), Access::read())])
        .await
        .unwrap();
    let m1 = space.publish_persisted(b"m1 before removal").await.unwrap();
    let mut log = create.clone();
    log.push(m1.clone());
    println!("bob   <- create,m1: {:?}", apps(&deliver(bob, &log).await));
    println!("carol <- create,m1: {:?}", apps(&deliver(carol, &log).await));

    // Alice removes Carol.
    let (rm_auth, rm_space) = space.remove_persisted(carol.manager.id()).await.unwrap();
    println!("carol={} bob={}", &carol.manager.id().to_hex()[..8], &bob.manager.id().to_hex()[..8]);
    println!("removal direct messages go to: {:?}", direct_recipients(&rm_space));
    let m2 = space.publish_persisted(b"m2 after removal").await.unwrap();
    println!("secret(m1) != secret(m2): {}", secret_id(&m1) != secret_id(&m2));
    assert_ne!(secret_id(&m1), secret_id(&m2), "group secret must rotate on removal");

    let tail = vec![rm_auth.clone(), rm_space.clone(), m2.clone()];
    let bob_ev = deliver(bob, &tail).await;
    println!("bob   <- remove,m2: {:?}", apps(&bob_ev));
    assert!(bob_ev.iter().any(|e| e == "APP:m2 after removal"));
    let carol_ev = deliver(carol, &tail).await;
    println!("carol <- remove,m2: {carol_ev:?}");
    assert!(!carol_ev.iter().any(|e| e == "APP:m2 after removal"));

    // Late joiner: does Dave get the whole secret bundle and read m1 (old secret) and m2?
    let (add_auth, add_space) = space.add_persisted(dave.manager.id(), Access::read()).await.unwrap();
    let mut all = log.clone();
    all.extend(tail);
    all.push(add_auth);
    all.push(add_space);
    // Re-send the old application messages after the welcome, as a sync would.
    all.push(m1.clone());
    all.push(m2.clone());
    let dave_ev = deliver(dave, &all).await;
    println!("dave (added later) <- everything: {:?}", apps(&dave_ev));
}

#[tokio::test]
async fn c3_pull_member_gets_no_keys() {
    let ps = peers(2).await;
    let (alice, pully) = (&ps[0], &ps[1]);
    let sid = SpaceId::digest(b"c3");
    let (space, create) = alice
        .manager
        .create_space_persisted(sid, &[(pully.manager.id(), Access::pull())])
        .await
        .unwrap();
    println!("create direct messages go to: {:?} (pully={})", direct_recipients(&create[1]), &pully.manager.id().to_hex()[..8]);
    let m1 = space.publish_persisted(b"secret for readers").await.unwrap();
    let mut log = create.clone();
    log.push(m1.clone());
    let ev = deliver(pully, &log).await;
    println!("pully <- create,m1: {ev:?}");
    assert!(!ev.iter().any(|e| e.contains("secret for readers")));
    // The ciphertext is still an ordinary message pully can store and re-serve:
    let SpacesArgs::Application { ciphertext, .. } = m1.borrow() else { panic!() };
    println!("pully holds {} ciphertext bytes it cannot open", ciphertext.len());
}

/// A manager-authored Promote (e.g. Pull -> Read) reaching a peer. The Spaces API has no
/// promote/demote method, but p2panda-auth accepts the action, and spaces maps it with
/// `unimplemented!()`.
#[tokio::test]
async fn probe_remote_promote_panics_receiver() {
    let ps = peers(2).await;
    let (alice, bob) = (&ps[0], &ps[1]);
    let sid = SpaceId::digest(b"promote");
    let (space, create) = alice
        .manager
        .create_space_persisted(sid, &[(bob.manager.id(), Access::read())])
        .await
        .unwrap();
    deliver(bob, &create).await;
    let group_id = space.group_id().await.unwrap();
    let forge = TestForge::new(alice.store.clone(), alice.credentials.signing_key());
    let promote = forge
        .forge(SpacesArgs::Auth {
            group_id,
            group_action: GroupAction::Promote {
                member: GroupMember::Individual(bob.manager.id()),
                access: Access::write(),
            },
            auth_dependencies: vec![create[0].hash()],
        })
        .await
        .unwrap();
    let bob_mgr = bob.manager.clone();
    bob.persist_operation(&promote).await.unwrap();
    let res = tokio::spawn(async move { bob_mgr.process_persisted(&promote).await.map(|_| ()) }).await;
    println!("remote Promote -> receiver: {:?}", res.as_ref().map_err(|e| format!("PANIC: {e}")));
    assert!(res.is_err() && res.unwrap_err().is_panic());
}

/// A `SpaceUpdate` message (a variant of the public wire enum) reaching a peer.
#[tokio::test]
async fn probe_remote_space_update_panics_receiver() {
    let ps = peers(2).await;
    let (alice, bob) = (&ps[0], &ps[1]);
    let sid = SpaceId::digest(b"update");
    let (space, create) = alice
        .manager
        .create_space_persisted(sid, &[(bob.manager.id(), Access::read())])
        .await
        .unwrap();
    deliver(bob, &create).await;
    let forge = TestForge::new(alice.store.clone(), alice.credentials.signing_key());
    let upd = forge
        .forge(SpacesArgs::SpaceUpdate {
            space_id: sid,
            group_id: space.group_id().await.unwrap(),
            space_dependencies: vec![create[1].hash()],
        })
        .await
        .unwrap();
    let bob_mgr = bob.manager.clone();
    bob.persist_operation(&upd).await.unwrap();
    let res = tokio::spawn(async move { bob_mgr.process_persisted(&upd).await.map(|_| ()) }).await;
    println!("remote SpaceUpdate -> receiver: {:?}", res.as_ref().map_err(|e| format!("PANIC: {e}")));
    assert!(res.is_err() && res.unwrap_err().is_panic());
}

/// Access levels below Write are not enforced on application messages in 0.7.1
/// (upstream "Validate write authority when processing application messages" #1295 is unreleased).
#[tokio::test]
async fn probe_read_member_can_publish() {
    let ps = peers(2).await;
    let (alice, bob) = (&ps[0], &ps[1]);
    let sid = SpaceId::digest(b"readonly");
    let (_space, create) = alice
        .manager
        .create_space_persisted(sid, &[(bob.manager.id(), Access::read())])
        .await
        .unwrap();
    deliver(bob, &create).await;
    let bob_space = bob.manager.space(sid).await.unwrap().unwrap();
    let m = bob_space.publish_persisted(b"written by a Read member").await.unwrap();
    let ev = deliver(alice, &[m]).await;
    println!("alice <- message from Read-only bob: {:?}", apps(&ev));
}
