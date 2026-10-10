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
