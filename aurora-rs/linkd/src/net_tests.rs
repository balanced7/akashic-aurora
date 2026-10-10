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
    let dir = std::env::temp_dir().join(format!(
        "linkd-test-{}-{}",
        label,
        hex(&aurora_link::crypto::random32()[..6])
    ));
    let d = Daemon::open(Dirs::new(&dir, None), false).unwrap();
    d.identity_init(&Params::new(json!({"label": label})).unwrap()).unwrap();
    let opts = NetOpts {
        n0: false,
        mdns: false,
        relays: vec![],
        no_relay: true,
        bind: Some("127.0.0.1:0".parse().unwrap()),
        relay_only: false,
    };
    let net = Net::start(d.clone(), opts).await.unwrap();
    (d, net, dir)
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
        v: 1,
        link: link.clone(),
        device: hex(net_x.endpoint.id().as_bytes()),
        acl: Default::default(),
        heads: Default::default(),
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
