//! The network's refusals, in process: a non-member gets the uniform close, and nobody can push a
//! blob into our store (iroh-blobs 0.94-0.103.0 accepted pushes by default; we disable them).

use std::sync::Arc;
use std::time::Duration;

use aurora_link::codec::hex;
use aurora_link::sync::{self as lsync, Frame};
use iroh::EndpointAddr;
use iroh_blobs::protocol::{ChunkRangesSeq, PushRequest};
use serde_json::json;

use crate::daemon::{Daemon, Dirs, Shared};
use crate::net::{CLOSE_REFUSED, LINK_ALPN, Net, NetOpts};
use crate::rpc::Params;

async fn node(label: &str) -> (Shared, Arc<Net>, std::path::PathBuf) {
    let (d, dir, _) = daemon(label);
    (d.clone(), start(d).await, dir)
}

/// A daemon with a fresh identity and no network yet; returns its recovery phrase too.
fn daemon(label: &str) -> (Shared, std::path::PathBuf, String) {
    let dir = std::env::temp_dir().join(format!(
        "linkd-test-{}-{}",
        label,
        hex(&aurora_link::crypto::random32()[..6])
    ));
    let d = Daemon::open(Dirs::new(&dir, None), false).unwrap();
    let id = d.identity_init(&Params::new(json!({"label": label})).unwrap()).unwrap();
    let phrase = id["phrase"].as_str().unwrap().to_owned();
    (d, dir, phrase)
}

async fn start(d: Shared) -> Arc<Net> {
    let opts = NetOpts {
        n0: false,
        mdns: false,
        relays: vec![],
        no_relay: true,
        bind: Some("127.0.0.1:0".parse().unwrap()),
        relay_only: false,
        idle: Some(Duration::from_secs(3)),
    };
    Net::start(d, opts).await.unwrap()
}

fn addr_of(net: &Net) -> EndpointAddr {
    let mut a = EndpointAddr::new(net.endpoint.id());
    for ip in net.endpoint.addr().ip_addrs() {
        if ip.ip().is_loopback() {
            a = a.with_ip_addr(*ip);
        }
    }
    a
}

#[tokio::test(flavor = "multi_thread")]
async fn a_non_member_gets_the_uniform_close_and_the_reason_is_logged() {
    let (a, net_a, dir_a) = node("a").await;
    let (_x, net_x, dir_x) = node("x").await;
    let link = a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap()["link"]
        .as_str()
        .unwrap()
        .to_owned();
    let conn = net_x.endpoint.connect(addr_of(&net_a), LINK_ALPN).await.unwrap();
    let (mut send, _recv) = conn.open_bi().await.unwrap();
    let hello = Frame::Hello {
        v: lsync::HELLO_VERSION,
        link: link.clone(),
        device: hex(net_x.endpoint.id().as_bytes()),
        acl: aurora_link::acl::AclPos {
            term: 1,
            seq: 0,
            hash: link.clone(),
        },
        heads: Default::default(),
        more: false,
    };
    send.write_all(&lsync::encode(&hello).unwrap()).await.unwrap();
    let closed = tokio::time::timeout(Duration::from_secs(10), conn.closed())
        .await
        .unwrap();
    let text = format!("{closed:?}");
    assert!(
        text.contains(&format!("error_code: {CLOSE_REFUSED}")) || text.contains("ApplicationClosed"),
        "{text}"
    );
    assert!(!text.contains("member"), "the wire carries no reason: {text}");
    let log = std::fs::read_to_string(a.dirs.refusals_log()).unwrap();
    assert!(log.contains("not a member"), "{log}");
    net_a.shutdown().await;
    net_x.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_x);
}

#[tokio::test(flavor = "multi_thread")]
async fn a_member_cannot_push_a_blob_into_our_store() {
    let (a, net_a, dir_a) = node("a").await;
    let (b, net_b, dir_b) = node("b").await;
    a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap();
    let inv = a
        .link_invite(&Params::new(json!({"link": "p"})).unwrap(), None, net_a.hints().1)
        .unwrap();
    let code = aurora_link::invite::InviteCode::parse(inv["code"].as_str().unwrap()).unwrap();
    net_b.join(&code, "b").await.unwrap();
    assert!(a.is_member_anywhere(&b.device().unwrap().id_hex()));
    // B stores something and tries to push it to A over the blobs protocol.
    let r = crate::net::put_blob(&net_b.blobs, "x", b"unsolicited").await.unwrap();
    let hash = iroh_blobs::Hash::from_bytes(aurora_link::codec::unhex::<32>(&r.id).unwrap());
    let conn = net_b.endpoint.connect(addr_of(&net_a), iroh_blobs::ALPN).await.unwrap();
    let pushed = net_b
        .blobs
        .remote()
        .execute_push(conn, PushRequest::new(hash, ChunkRangesSeq::root()))
        .await;
    let _ = pushed; // the pushing client is not told; what matters is our store
    tokio::time::sleep(Duration::from_millis(500)).await;
    assert!(
        !net_a.blobs.blobs().has(hash).await.unwrap(),
        "the pushed blob reached our store"
    );

    // Control: the same protocol does serve a GET for a blob A shares in the link.
    let shared = crate::net::put_blob(&net_a.blobs, "playbook.md", b"steps")
        .await
        .unwrap();
    let body = aurora_link::record::Body {
        kind: "note".into(),
        seat: "claude".into(),
        to: "@b".into(),
        content: "attached".into(),
        blobs: vec![shared.clone()],
        sent_at: 1,
        ..Default::default()
    };
    a.link_send("p", body, None).unwrap();
    let want = iroh_blobs::Hash::from_bytes(aurora_link::codec::unhex::<32>(&shared.id).unwrap());
    net_b
        .blobs
        .downloader(&net_b.endpoint)
        .download(want, vec![net_a.endpoint.id()])
        .await
        .unwrap();
    assert!(net_b.blobs.blobs().has(want).await.unwrap());

    // And a GET for a blob that is in A's store but in no link shared with B is refused.
    let private = crate::net::put_blob(&net_a.blobs, "private", b"not yours")
        .await
        .unwrap();
    let hidden = iroh_blobs::Hash::from_bytes(aurora_link::codec::unhex::<32>(&private.id).unwrap());
    let got = net_b
        .blobs
        .downloader(&net_b.endpoint)
        .download(hidden, vec![net_a.endpoint.id()])
        .await;
    assert!(
        got.is_err() && !net_b.blobs.blobs().has(hidden).await.unwrap(),
        "an unshared blob was served"
    );
    net_a.shutdown().await;
    net_b.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_b);
}

#[derive(Debug)]
struct Allow(Vec<iroh::EndpointId>);

impl iroh_relay::server::AccessControl for Allow {
    async fn on_connect(&self, request: &iroh_relay::server::ClientRequest) -> iroh_relay::server::Access {
        if self.0.contains(&request.endpoint_id()) {
            iroh_relay::server::Access::Allow
        } else {
            iroh_relay::server::Access::Deny { reason: None }
        }
    }
}

/// An endpoint that can only use the given relay: no IP transports at all.
async fn relay_only(map: iroh::RelayMap, sk: iroh::SecretKey) -> iroh::Endpoint {
    iroh::Endpoint::builder(iroh::endpoint::presets::Minimal)
        .secret_key(sk)
        .relay_mode(iroh::RelayMode::Custom(map))
        .ca_tls_config(iroh::tls::CaTlsConfig::insecure_skip_verify())
        .clear_ip_transports()
        .alpns(vec![b"aurora/test/0".to_vec()])
        .bind()
        .await
        .unwrap()
}

/// A self-hosted relay with an allowlist (what `relay.config` writes) carries members only: two
/// members with no IP path reach each other through it, and a non-member cannot reach a member.
#[tokio::test(flavor = "multi_thread")]
async fn an_authenticated_relay_carries_members_only() {
    let (a_sk, b_sk, x_sk) = (
        iroh::SecretKey::generate(),
        iroh::SecretKey::generate(),
        iroh::SecretKey::generate(),
    );
    let access = Arc::new(Allow(vec![a_sk.public(), b_sk.public()]));
    let (map, url, _server) = iroh::test_utils::run_relay_server_with_access(true, access)
        .await
        .unwrap();
    let a = relay_only(map.clone(), a_sk).await;
    let b = relay_only(map.clone(), b_sk).await;
    let x = relay_only(map.clone(), x_sk).await;
    let accept = {
        let b = b.clone();
        tokio::spawn(async move {
            let conn = b.accept().await.unwrap().await.unwrap();
            let (mut send, mut recv) = conn.accept_bi().await.unwrap();
            let got = recv.read_to_end(64).await.unwrap();
            send.write_all(&got).await.unwrap();
            send.finish().unwrap();
            conn.closed().await;
        })
    };
    let to_b = EndpointAddr::new(b.id()).with_relay_url(url.clone());
    let conn = tokio::time::timeout(Duration::from_secs(20), a.connect(to_b.clone(), b"aurora/test/0"))
        .await
        .unwrap()
        .unwrap();
    let (mut send, mut recv) = conn.open_bi().await.unwrap();
    send.write_all(b"via the relay").await.unwrap();
    send.finish().unwrap();
    assert_eq!(recv.read_to_end(64).await.unwrap(), b"via the relay");
    conn.close(0u32.into(), b"");
    let _ = accept.await;
    let x_try = tokio::time::timeout(Duration::from_secs(8), x.connect(to_b, b"aurora/test/0")).await;
    assert!(
        !matches!(x_try, Ok(Ok(_))),
        "a non-member reached a member through the members-only relay"
    );
}

// ------------------------------------------------------------------------- Phase 0 measurements
//
// `cargo test -p aurora-linkd --release phase0 -- --ignored --nocapture` prints one JSON line.
// The same transport benchmark as the PyPI-binding control (research/in-flight/link-phase0-*),
// plus what a link adds on top: records end to end, a 1 MiB attachment, and reconnecting after
// a network change.

const BENCH: &[u8] = b"aurora/bench/0";

async fn bench_ep(map: Option<iroh::RelayMap>) -> iroh::Endpoint {
    let mut b = iroh::Endpoint::builder(iroh::endpoint::presets::Minimal).alpns(vec![BENCH.to_vec()]);
    b = match map {
        Some(m) => b
            .relay_mode(iroh::RelayMode::Custom(m))
            .ca_tls_config(iroh::tls::CaTlsConfig::insecure_skip_verify())
            .clear_ip_transports(),
        None => b
            .relay_mode(iroh::RelayMode::Disabled)
            .bind_addr("127.0.0.1:0".parse::<std::net::SocketAddr>().unwrap())
            .unwrap(),
    };
    b.bind().await.unwrap()
}

fn echo_len(server: iroh::Endpoint) {
    tokio::spawn(async move {
        while let Some(inc) = server.accept().await {
            tokio::spawn(async move {
                let Ok(conn) = inc.await else { return };
                while let Ok((mut send, mut recv)) = conn.accept_bi().await {
                    let data = recv.read_to_end(4 << 20).await.unwrap_or_default();
                    let _ = send.write_all(&(data.len() as u64).to_be_bytes()).await;
                    let _ = send.finish();
                }
            });
        }
    });
}

async fn roundtrip(conn: &iroh::endpoint::Connection, payload: &[u8]) -> u64 {
    let (mut send, mut recv) = conn.open_bi().await.unwrap();
    send.write_all(payload).await.unwrap();
    send.finish().unwrap();
    u64::from_be_bytes(recv.read_to_end(8).await.unwrap().try_into().unwrap())
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    (v[v.len() / 2] * 100.0).round() / 100.0
}

async fn transport(label: &str, map: Option<iroh::RelayMap>, url: Option<iroh::RelayUrl>) -> serde_json::Value {
    let server = bench_ep(map.clone()).await;
    let client = bench_ep(map).await;
    let addr = match url {
        Some(u) => {
            server.online().await;
            EndpointAddr::new(server.id()).with_relay_url(u)
        }
        None => addr_of_ep(&server),
    };
    echo_len(server.clone());
    let mut connects = vec![];
    for _ in 0..20 {
        let t = std::time::Instant::now();
        let conn = client.connect(addr.clone(), BENCH).await.unwrap();
        roundtrip(&conn, b"x").await;
        connects.push(t.elapsed().as_secs_f64() * 1000.0);
        conn.close(0u32.into(), b"");
    }
    let conn = client.connect(addr.clone(), BENCH).await.unwrap();
    let mut out = json!({"path": label, "connect_ms_median": median(connects)});
    for (name, size, n) in [("1KiB", 1024usize, 500u32), ("1MiB", 1 << 20, 20)] {
        let payload = vec![0u8; size];
        let t = std::time::Instant::now();
        for _ in 0..n {
            assert_eq!(roundtrip(&conn, &payload).await, size as u64);
        }
        let dt = t.elapsed().as_secs_f64();
        out[format!("{name}_per_s")] = json!((f64::from(n) / dt * 10.0).round() / 10.0);
        out[format!("{name}_MBps")] = json!((f64::from(n) * size as f64 / dt / 1e4).round() / 100.0);
    }
    // Reconnect after a network change: tell the client its network changed, then time the next
    // successful round trip on a fresh connection.
    let t = std::time::Instant::now();
    client.network_change().await;
    let conn2 = client.connect(addr, BENCH).await.unwrap();
    roundtrip(&conn2, b"x").await;
    out["reconnect_after_network_change_ms"] = json!((t.elapsed().as_secs_f64() * 100_000.0).round() / 100.0);
    out
}

fn addr_of_ep(ep: &iroh::Endpoint) -> EndpointAddr {
    let mut a = EndpointAddr::new(ep.id());
    for ip in ep.addr().ip_addrs() {
        if ip.ip().is_loopback() {
            a = a.with_ip_addr(*ip);
        }
    }
    a
}

#[tokio::test(flavor = "multi_thread")]
#[ignore = "measurement, not a check: run with --ignored --nocapture"]
async fn phase0_measure() {
    let direct = transport("direct (loopback)", None, None).await;
    let (map, url, _server) = iroh::test_utils::run_relay_server().await.unwrap();
    let relayed = transport("relayed (local iroh-relay, no IP path)", Some(map), Some(url)).await;

    // What a link adds: records end to end through two daemons, and a 1 MiB attachment.
    let (a, net_a, dir_a) = node("a").await;
    let (b, net_b, dir_b) = node("b").await;
    a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap();
    let inv = a
        .link_invite(&Params::new(json!({"link": "p"})).unwrap(), None, net_a.hints().1)
        .unwrap();
    let code = aurora_link::invite::InviteCode::parse(inv["code"].as_str().unwrap()).unwrap();
    let t = std::time::Instant::now();
    net_b.join(&code, "b").await.unwrap();
    let join_ms = t.elapsed().as_secs_f64() * 1000.0;
    let body = |i: usize| aurora_link::record::Body {
        kind: "chat".into(),
        seat: "claude".into(),
        to: "@b".into(),
        content: format!("{i:04} {}", "x".repeat(1000)),
        sent_at: 1,
        ..Default::default()
    };
    let wait_events = |n: usize| {
        let b = b.clone();
        async move {
            let deadline = std::time::Instant::now() + Duration::from_secs(60);
            while b.events_after(&Default::default(), 1000).unwrap().len() < n {
                assert!(std::time::Instant::now() < deadline, "records did not arrive");
                tokio::time::sleep(Duration::from_millis(5)).await;
            }
        }
    };
    a.link_send("p", body(0), None).unwrap();
    wait_events(1).await;
    let t = std::time::Instant::now();
    for i in 1..=200 {
        a.link_send("p", body(i), None).unwrap();
    }
    wait_events(201).await;
    let records_dt = t.elapsed().as_secs_f64();
    let blob = crate::net::put_blob(&net_a.blobs, "big.bin", &vec![7u8; 1 << 20])
        .await
        .unwrap();
    let hash = iroh_blobs::Hash::from_bytes(aurora_link::codec::unhex::<32>(&blob.id).unwrap());
    let mut att = body(999);
    att.blobs.push(blob);
    a.link_send("p", att, None).unwrap();
    wait_events(202).await;
    let t = std::time::Instant::now();
    net_b
        .blobs
        .downloader(&net_b.endpoint)
        .download(hash, vec![net_a.endpoint.id()])
        .await
        .unwrap();
    let blob_ms = t.elapsed().as_secs_f64() * 1000.0;
    let link = json!({
        "join_ms": (join_ms * 100.0).round() / 100.0,
        "records_1KiB_end_to_end_per_s": (200.0 / records_dt * 10.0).round() / 10.0,
        "blob_1MiB_fetch_ms": (blob_ms * 100.0).round() / 100.0,
    });
    println!(
        "{}",
        json!({"iroh": "1.3.0", "transport": [direct, relayed], "link": link})
    );
    net_a.shutdown().await;
    net_b.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_b);
}

/// R5-4: at most two sync sessions per (peer, link), and a slot comes back when its session ends.
#[test]
fn sessions_are_capped_per_peer_and_link() {
    let count = Arc::new(crate::net::SessionCount::default());
    let a = count.take("l", "p").unwrap();
    let b = count.take("l", "p").unwrap();
    assert!(
        count.take("l", "p").is_none(),
        "a third session of one peer on one link"
    );
    assert!(count.take("l", "q").is_some(), "another peer has its own slots");
    assert!(count.take("m", "p").is_some(), "and so has another link");
    assert_eq!(count.count("l", "p"), crate::net::MAX_SESSIONS_PER_PEER_LINK);
    drop(a);
    assert_eq!(count.count("l", "p"), 1);
    let _c = count.take("l", "p").unwrap();
    drop(b);
}

/// R5-4: a member's session that sends nothing (not even pings) is closed after the idle timeout,
/// and a third session from the same member is refused while two are open.
#[tokio::test(flavor = "multi_thread")]
async fn an_idle_session_is_closed_and_a_third_is_refused() {
    let (a, net_a, dir_a) = node("a").await;
    let (b, net_b, dir_b) = node("b").await;
    a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap();
    let inv = a
        .link_invite(&Params::new(json!({"link": "p"})).unwrap(), None, net_a.hints().1)
        .unwrap();
    let code = aurora_link::invite::InviteCode::parse(inv["code"].as_str().unwrap()).unwrap();
    net_b.join(&code, "b").await.unwrap();
    let link = code.link.clone();
    let bid = b.device().unwrap().id_hex();
    let tip = a.with_link(&link, |l| Ok(l.acl.tip())).unwrap();
    let hello = Frame::Hello {
        v: lsync::HELLO_VERSION,
        link: link.clone(),
        device: bid.clone(),
        acl: tip,
        heads: Default::default(),
        more: false,
    };
    // Let B's own dialer settle, then hold raw sessions from B's endpoint that never answer.
    tokio::time::sleep(Duration::from_millis(500)).await;
    let mut conns = Vec::new();
    for _ in 0..3 {
        let conn = net_b.endpoint.connect(addr_of(&net_a), LINK_ALPN).await.unwrap();
        let (mut send, recv) = conn.open_bi().await.unwrap();
        send.write_all(&lsync::encode(&hello).unwrap()).await.unwrap();
        conns.push((conn, send, recv));
        tokio::time::sleep(Duration::from_millis(300)).await;
    }
    assert!(net_a.sessions.count(&link, &bid) <= crate::net::MAX_SESSIONS_PER_PEER_LINK);
    // Silent sessions are closed after the (shortened) idle timeout.
    let closed = tokio::time::timeout(Duration::from_secs(15), conns[0].0.closed()).await;
    assert!(closed.is_ok(), "an idle session stays open");
    let log = std::fs::read_to_string(a.dirs.refusals_log()).unwrap();
    assert!(
        log.contains("too many sync sessions from this device") || log.contains("no frame"),
        "{log}"
    );
    net_a.shutdown().await;
    net_b.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_b);
}

#[test]
fn the_join_limiter_caps_each_key_per_window_and_bounds_its_table() {
    let l = crate::net::Limiter::new(3, 60);
    assert!((0..3).all(|_| l.allow("1.2.3.4", 100)));
    assert!(!l.allow("1.2.3.4", 110), "a fourth attempt in the window");
    assert!(l.allow("5.6.7.8", 110), "another key has its own budget");
    assert!(l.allow("1.2.3.4", 160), "a new window");
}

#[test]
fn the_gossip_topic_needs_the_log_and_survives_a_rotation() {
    use aurora_link::acl::Policy;
    use aurora_link::engine::Link;
    use aurora_link::identity::{Device, new_phrase, root_from_phrase};
    let dev = Device::create(&root_from_phrase(&new_phrase()).unwrap(), "a", false, 1_000).unwrap();
    let mut l = Link::create(None, &dev, "p", "fleet-a", Policy::default(), 1_000).unwrap();
    let t = crate::net::topic(&l).unwrap();
    // Not computable from the link id (which invite codes carry), as the old topic was.
    let old = aurora_link::crypto::blake3(format!("aurora-link/v1/gossip/{}", l.id()).as_bytes());
    assert_ne!(t.as_bytes(), &old);
    l.rotate_key(&dev, 1_001).unwrap();
    assert_eq!(crate::net::topic(&l).unwrap(), t, "stable across key rotations");
    let other = Link::create(None, &dev, "q", "fleet-a", Policy::default(), 1_000).unwrap();
    assert_ne!(crate::net::topic(&other).unwrap(), t);
}

/// Tell `d` where `net` listens.
fn knows(d: &Shared, net: &Net) {
    let addrs: Vec<String> = addr_of(net).ip_addrs().map(|a| a.to_string()).collect();
    let device = hex(net.endpoint.id().as_bytes());
    crate::net::peers_add(
        &d.dirs,
        &Params::new(json!({"device": device, "addrs": addrs})).unwrap(),
    )
    .unwrap();
}

/// R7-2 (probe `p2`), through the daemon: a device added past a halt's prefix is left out of its
/// own narrowed view, and the transport read that view, so the device dialed nobody for the link
/// and refused everyone, and never received the owner's takeover. The transport now reads the
/// held state: it dials, accepts, takes the takeover, and is a member again.
#[tokio::test(flavor = "multi_thread")]
async fn r7_2_a_device_added_past_a_halt_dials_accepts_and_takes_the_takeover() {
    use aurora_link::acl::{Op, Role};
    use aurora_link::engine::Link;
    let (a, dir_a, phrase) = daemon("a");
    let (n, dir_n, _) = daemon("n");
    let link = a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap()["link"]
        .as_str()
        .unwrap()
        .to_owned();
    let (adev, ndev) = (a.device().unwrap(), n.device().unwrap());
    let (aid, nid) = (adev.id_hex(), ndev.id_hex());
    // A backup of A's chain, then N joins (through the join door, in process).
    let backup = a.with_link(&link, |l| Ok(l.acl.all())).unwrap();
    let t = aurora_link::codec::now();
    a.with_link(&link, |l| {
        let ticket = l.invite(&adev, Role::Writer, 3600, true, false, t)?;
        let mut door = lsync::JoinDoor::new();
        let hello = lsync::join_hello(&link, &ndev, &ticket)?;
        let entries: Vec<_> = door
            .on_frame(l, &adev, &nid, hello, t)?
            .into_iter()
            .flat_map(|f| match f {
                Frame::Acl { entries } => entries,
                _ => vec![],
            })
            .collect();
        let proposal = lsync::join_proposal(&entries, &ndev, &ticket, "n", t)?;
        door.on_frame(l, &adev, &nid, Frame::Join { proposal }, t)?;
        Ok(())
    })
    .unwrap();
    let all = a.with_link(&link, |l| Ok(l.acl.all())).unwrap();
    let mine = Link::adopt(Some(&n.dirs.state), all, t).unwrap();
    n.hold(mine);
    // A's backup signs another entry at N's join's position: N halts there.
    let mut fork = lsync::chain_of(&backup).unwrap();
    let op = Op::Invite(aurora_link::acl::Invite {
        invite: hex(&aurora_link::crypto::random32()),
        role: Role::Reader,
        expires: t + 3600,
        single_use: true,
        approval: false,
    });
    let other = fork.append(&adev, Some(op), vec![], t, &|_| 0).unwrap();
    assert_eq!(other.seq as usize, backup.len());
    n.with_link(&link, |l| Ok(l.add_acl(vec![other], t)?)).unwrap();
    assert!(n.with_link(&link, |l| Ok(l.acl.halt().is_some())).unwrap());
    assert!(
        n.with_link(&link, |l| Ok(l.state().active_device(&nid).is_none()))
            .unwrap(),
        "the narrowed view leaves N out"
    );
    // The transport still sees the link and its peers.
    assert!(
        n.peer_links().get(&aid).is_some_and(|ls| ls.contains(&link)),
        "N's transport drops the link"
    );
    assert!(n.is_member_anywhere(&aid));
    assert!(!n.record_peer_links().contains_key(&aid));
    // The owner's takeover on A (not halted: it continues after A's tip, keeping N's join).
    a.link_takeover(&Params::new(json!({"link": link, "phrase": phrase})).unwrap())
        .unwrap();
    // Only now do the two come online.
    let net_a = start(a.clone()).await;
    let net_n = start(n.clone()).await;
    knows(&n, &net_a);
    knows(&a, &net_n);
    let mut recovered = false;
    for _ in 0..60 {
        n.wake_now();
        a.wake_now();
        tokio::time::sleep(Duration::from_millis(250)).await;
        if n.with_link(&link, |l| Ok(l.acl.halt().is_none())).unwrap() {
            recovered = true;
            break;
        }
    }
    assert!(recovered, "N never took the takeover");
    assert!(
        n.with_link(&link, |l| Ok(l.state().active_device(&nid).is_some()))
            .unwrap()
    );
    net_a.shutdown().await;
    net_n.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_n);
}

/// R8-3: the sync budgets were per session, and new sessions were not rated: a member that
/// reconnected got a fresh budget each time. Now what a device's frames spend is kept per link and
/// device across its sessions, and a device opens at most `SESSION_STARTS_PER_MIN` sessions per
/// link a minute.
#[tokio::test(flavor = "multi_thread")]
async fn r8_3_budgets_survive_a_reconnect_and_new_sessions_are_rated() {
    let (a, net_a, dir_a) = node("a").await;
    let (b, net_b, dir_b) = node("b").await;
    a.link_create(&Params::new(json!({"name": "p"})).unwrap()).unwrap();
    let inv = a
        .link_invite(&Params::new(json!({"link": "p"})).unwrap(), None, net_a.hints().1)
        .unwrap();
    let code = aurora_link::invite::InviteCode::parse(inv["code"].as_str().unwrap()).unwrap();
    net_b.join(&code, "b").await.unwrap();
    let link = code.link.clone();
    let bid = b.device().unwrap().id_hex();
    let tip = a.with_link(&link, |l| Ok(l.acl.tip())).unwrap();
    let hello = Frame::Hello {
        v: lsync::HELLO_VERSION,
        link: link.clone(),
        device: bid.clone(),
        acl: tip,
        heads: Default::default(),
        more: false,
    };
    let want = lsync::encode(&Frame::AclWant { from: 0, to: 0 }).unwrap();
    let log = || std::fs::read_to_string(a.dirs.refusals_log()).unwrap_or_default();
    tokio::time::sleep(Duration::from_millis(500)).await;
    // Both sessions within one minute of A's clock.
    let into_minute = aurora_link::codec::now() % 60;
    if into_minute > 30 {
        tokio::time::sleep(Duration::from_secs(61 - into_minute)).await;
    }
    // Session one: 100 ACL frames (within the 120 a minute), then it closes.
    let session = |frames: usize| {
        let (net_a, net_b, hello, want) = (net_a.clone(), net_b.clone(), hello.clone(), want.clone());
        async move {
            let conn = net_b.endpoint.connect(addr_of(&net_a), LINK_ALPN).await.unwrap();
            let (mut send, _recv) = conn.open_bi().await.unwrap();
            send.write_all(&lsync::encode(&hello).unwrap()).await.unwrap();
            for _ in 0..frames {
                if send.write_all(&want).await.is_err() {
                    break;
                }
            }
            let settle = if frames == 0 { 200 } else { 1500 };
            tokio::time::sleep(Duration::from_millis(settle)).await;
            conn.close(0u32.into(), b"bye");
        }
    };
    session(100).await;
    assert!(!log().contains("too many ACL frames"), "{}", log());
    // Session two, a reconnect: 30 more frames run past the budget it shares with session one.
    session(30).await;
    assert!(
        log().contains("too many ACL frames this minute"),
        "a reconnect started a fresh budget: {}",
        log()
    );
    // New sessions are rated per device and link.
    for _ in 0..=crate::net::SESSION_STARTS_PER_MIN {
        session(0).await;
    }
    assert!(log().contains("too many new sync sessions"), "{}", log());
    net_a.shutdown().await;
    net_b.shutdown().await;
    let _ = std::fs::remove_dir_all(dir_a);
    let _ = std::fs::remove_dir_all(dir_b);
}

/// Round 8: each link has its own lock. Work on one link (here held for a second) no longer
/// holds up another link's sessions and RPCs, as the daemon-wide lock did.
#[test]
fn a_busy_link_does_not_hold_up_another() {
    let (d, dir, _) = daemon("a");
    let one = d.link_create(&Params::new(json!({"name": "one"})).unwrap()).unwrap()["link"]
        .as_str()
        .unwrap()
        .to_owned();
    d.link_create(&Params::new(json!({"name": "two"})).unwrap()).unwrap();
    let (held, release) = std::sync::mpsc::channel::<()>();
    let busy = {
        let d = d.clone();
        std::thread::spawn(move || {
            d.with_link(&one, |_| {
                held.send(()).unwrap();
                std::thread::sleep(Duration::from_secs(1));
                Ok(())
            })
            .unwrap();
        })
    };
    release.recv().unwrap();
    let t = std::time::Instant::now();
    let name = d.with_link("two", |l| Ok(l.name().to_owned())).unwrap();
    assert_eq!(name, "two");
    assert!(
        t.elapsed() < Duration::from_millis(500),
        "link two waited {:?} for link one",
        t.elapsed()
    );
    busy.join().unwrap();
    let _ = std::fs::remove_dir_all(dir);
}

/// R9-3: `peer_links` (the inbound gates of every protocol and the dialer) took each link's lock
/// in turn, so an inbound connection waited for the frame in progress on every link. Now it reads
/// each link's kept copy of who may sync, refreshed after every change, with no link's lock.
#[test]
fn r9_3_peer_links_takes_no_link_lock_and_follows_the_chain() {
    let (d, dir, phrase) = daemon("a");
    d.link_create(&Params::new(json!({"name": "one"})).unwrap()).unwrap();
    let device = d.device().unwrap();
    let root = aurora_link::identity::root_from_phrase(&phrase).unwrap();
    let other = aurora_link::identity::Device::create(&root, "a2", false, aurora_link::codec::now()).unwrap();
    let oid = other.id_hex();
    assert!(!d.peer_links().contains_key(&oid));
    d.with_link("one", |l| {
        Ok(l.add_device(&device, other.cert.clone(), aurora_link::codec::now())?)
    })
    .unwrap();
    assert!(d.peer_links().contains_key(&oid), "a device added is a peer at once");
    let (held, release) = std::sync::mpsc::channel::<()>();
    let busy = {
        let d = d.clone();
        std::thread::spawn(move || {
            d.with_link("one", |_| {
                held.send(()).unwrap();
                std::thread::sleep(Duration::from_secs(1));
                Ok(())
            })
            .unwrap();
        })
    };
    release.recv().unwrap();
    let t = std::time::Instant::now();
    assert!(d.is_member_anywhere(&oid));
    assert!(
        t.elapsed() < Duration::from_millis(300),
        "the inbound gate waited {:?} for a busy link",
        t.elapsed()
    );
    busy.join().unwrap();
    d.with_link("one", |l| {
        Ok(l.remove_device(&device, &oid, aurora_link::codec::now())?)
    })
    .unwrap();
    assert!(!d.is_member_anywhere(&oid), "a device removed is no peer at once");
    let _ = std::fs::remove_dir_all(dir);
}

/// R9-3 (probe `q4`): the per-link lock is a std `Mutex`, taken on tokio workers. Sessions of one
/// busy link that wait for it each held a worker, so once they outnumbered the workers a frame
/// on a quiet link waited too (`q4`, 4 workers, 16 sessions busy on link X: p99 27.9 ms, max
/// 35.6 ms). Now `with_link` runs its wait and its body off the workers (`LinkCell::with`), and
/// `peer_links` reads a copy of each link's devices without its lock. A measurement: run it in
/// release with `--ignored --nocapture`.
#[test]
#[ignore = "measurement: run in release with --ignored --nocapture"]
fn r9_3_a_busy_link_holds_up_no_worker() {
    let (d, dir, _) = daemon("a");
    for name in ["x", "y"] {
        d.link_create(&Params::new(json!({"name": name})).unwrap()).unwrap();
    }
    let device = d.device().unwrap();
    let pad = "x".repeat(20_000);
    d.with_link("x", |l| {
        for i in 0..600 {
            let body = aurora_link::record::Body {
                kind: "chat".into(),
                seat: "claude".into(),
                to: "@b".into(),
                content: format!("{i} {pad}"),
                sent_at: 1,
                ..Default::default()
            };
            l.write(&device, &body, aurora_link::codec::now())?;
        }
        Ok(())
    })
    .unwrap();
    let rt = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(4)
        .enable_all()
        .build()
        .unwrap();
    let mut worst = 0.0f64;
    for busy in [0usize, 2, 16] {
        let d = d.clone();
        let (lat, held, wall) = rt.block_on(async move {
            let stop = Arc::new(std::sync::atomic::AtomicBool::new(false));
            let mut tasks = Vec::new();
            for _ in 0..busy {
                let (d, stop) = (d.clone(), stop.clone());
                tasks.push(tokio::spawn(async move {
                    let mut held = Duration::ZERO;
                    while !stop.load(std::sync::atomic::Ordering::Relaxed) {
                        // What a session's `want` does under the lock: read up to a minute's
                        // budget of records.
                        d.with_link("x", |l| {
                            let t = std::time::Instant::now();
                            let (rs, _) =
                                l.missing_for_authors(&Default::default(), 4096, lsync::RECORD_BYTES_PER_MIN, |_| {
                                    true
                                })?;
                            held += t.elapsed();
                            Ok(rs.len())
                        })
                        .unwrap();
                        tokio::task::yield_now().await;
                    }
                    held
                }));
            }
            tokio::time::sleep(Duration::from_millis(300)).await;
            let mut lat = Vec::new();
            let wall = std::time::Instant::now();
            for _ in 0..200 {
                let t = std::time::Instant::now();
                // A frame on quiet link Y, from its own task, as a session of Y runs it.
                let d2 = d.clone();
                tokio::spawn(async move { d2.with_link("y", |l| Ok(l.name().to_owned())).unwrap() })
                    .await
                    .unwrap();
                lat.push(t.elapsed().as_secs_f64() * 1e3);
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
            // 200 sleeps of 10 ms: about 2 s when the timers run on time.
            let wall = wall.elapsed();
            stop.store(true, std::sync::atomic::Ordering::Relaxed);
            let mut held = Duration::ZERO;
            for t in tasks {
                held += t.await.unwrap();
            }
            lat.sort_by(|a, b| a.partial_cmp(b).unwrap());
            (lat, held, wall)
        });
        let pct = |p: usize| lat[(lat.len() * p / 100).min(lat.len() - 1)];
        println!(
            "workers 4, {busy:>2} sessions busy on link X: a frame on quiet link Y waits p50 {:.2} ms, p90 {:.2} ms, p99 {:.2} ms, max {:.2} ms; 200 rounds with a 10 ms sleep took {:.1} s (X's lock held {:.1} s in all)",
            pct(50),
            pct(90),
            pct(99),
            lat[lat.len() - 1],
            wall.as_secs_f64(),
            held.as_secs_f64()
        );
        worst = worst.max(pct(99));
    }
    assert!(worst < 10.0, "a frame on a quiet link waited {worst:.2} ms at p99");
    let _ = std::fs::remove_dir_all(dir);
}
