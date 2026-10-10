//! The network: one iroh endpoint whose key is this device's key, and four protocols on it.
//!
//! - `aurora/link/1`: sync sessions (aurora_link::sync), one bi-stream per session;
//! - `aurora/link-join/1`: an invitee fetching the log and handing over its join entry;
//! - iroh-gossip: signed head adverts on a per-link topic, so peers sync as soon as there is news;
//! - iroh-blobs: encrypted attachments. Push is disabled, `get_many` is disabled, and `get` is
//!   allowed only for a blob of a link the requesting device is a member of.
//!
//! Every protocol except join refuses a device that is not a member of any of our links, with
//! one uniform close code and no reason on the wire. The real reason goes to the local log.

use std::collections::{BTreeMap, HashMap};
use std::str::FromStr;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::Duration;

use anyhow::{Context, anyhow, bail};
use aurora_link::codec::{hex, now, unhex};
use aurora_link::crypto;
use aurora_link::invite::InviteCode;
use aurora_link::record::{self, BlobRef, HeadAdvert};
use aurora_link::sync::{self as lsync, Frame, Session};
use iroh::endpoint::{Connection, RecvStream, SendStream, presets};
use iroh::protocol::{AcceptError, ProtocolHandler, Router};
use iroh::{Endpoint, EndpointAddr, EndpointId, RelayMode, RelayUrl, SecretKey};
use iroh_blobs::provider::events::{AbortReason, ConnectMode, EventMask, EventSender, ProviderMessage, RequestMode};
use iroh_blobs::store::fs::FsStore;
use iroh_blobs::{BlobsProtocol, Hash};
use iroh_gossip::api::{Event, GossipSender};
use iroh_gossip::{Gossip, TopicId};
use n0_future::StreamExt;
use serde_json::{Value, json};
use tokio::sync::mpsc;

use crate::daemon::{Dirs, Push, Shared};
use crate::rpc::{Ctx, Params, RpcError};

pub const LINK_ALPN: &[u8] = lsync::ALPN;
pub const JOIN_ALPN: &[u8] = b"aurora/link-join/1";
/// The one close code every refusal gets.
pub const CLOSE_REFUSED: u32 = 1;
const DIAL_EVERY: Duration = Duration::from_secs(30);
const MAX_BACKOFF_S: u64 = 600;

#[derive(Clone, Debug, Default)]
pub struct NetOpts {
    /// Publish and resolve addresses through n0's DNS (pkarr), and use n0's relays by default.
    pub n0: bool,
    pub mdns: bool,
    pub relays: Vec<String>,
    pub no_relay: bool,
    pub bind: Option<std::net::SocketAddr>,
}

pub struct Net {
    pub d: Shared,
    pub endpoint: Endpoint,
    pub gossip: Gossip,
    pub blobs: FsStore,
    router: OnceLock<Router>,
    live: Mutex<HashMap<(String, String), u64>>,
    topics: Mutex<BTreeMap<String, GossipSender>>,
    backoff: Mutex<HashMap<(String, String), (u64, u64)>>,
}

pub async fn blob_store(dirs: &Dirs) -> anyhow::Result<FsStore> {
    std::fs::create_dir_all(dirs.blobs())?;
    FsStore::load(dirs.blobs())
        .await
        .map_err(|e| anyhow!("{e}"))
        .context("opening the blob store")
}

/// Seal and store one attachment; returns the reference that goes in the record body.
pub async fn put_blob(store: &FsStore, name: &str, plain: &[u8]) -> anyhow::Result<BlobRef> {
    let (r, ct) = record::seal_blob(name, plain);
    let hash_and_format = store
        .blobs()
        .add_bytes(ct)
        .with_named_tag(format!("aurora-link/{}", r.id))
        .await?;
    if hex(hash_and_format.hash.as_bytes()) != r.id {
        bail!("blob store hashed the attachment differently");
    }
    Ok(r)
}

fn topic(link: &str) -> TopicId {
    TopicId::from_bytes(crypto::blake3(format!("aurora-link/v1/gossip/{link}").as_bytes()))
}

fn endpoint_id(device: &str) -> anyhow::Result<EndpointId> {
    Ok(EndpointId::from_bytes(&unhex::<32>(device)?)?)
}

// ------------------------------------------------------------------------------------- dial hints

pub fn peers_add(dirs: &Dirs, p: &Params) -> Result<Value, RpcError> {
    let device = p.str("device")?;
    unhex::<32>(&device)?;
    let addrs: Vec<String> = p.opt("addrs")?.unwrap_or_default();
    for a in &addrs {
        a.parse::<std::net::SocketAddr>()
            .map_err(|_| RpcError::invalid(format!("not an ip:port: {a}")))?;
    }
    let relay = p.opt_str("relay")?;
    if let Some(r) = &relay {
        RelayUrl::from_str(r).map_err(|_| RpcError::invalid("not a relay URL"))?;
    }
    let mut all = load_peers(dirs);
    all.insert(device.clone(), json!({"addrs": addrs, "relay": relay}));
    std::fs::create_dir_all(&dirs.state).map_err(|e| RpcError::internal(e.into()))?;
    std::fs::write(dirs.peers_file(), serde_json::to_vec_pretty(&all).expect("json"))
        .map_err(|e| RpcError::internal(e.into()))?;
    Ok(json!({"device": device}))
}

fn load_peers(dirs: &Dirs) -> BTreeMap<String, Value> {
    std::fs::read(dirs.peers_file())
        .ok()
        .and_then(|raw| serde_json::from_slice(&raw).ok())
        .unwrap_or_default()
}

fn addr_for(dirs: &Dirs, device: &str) -> anyhow::Result<EndpointAddr> {
    let mut addr = EndpointAddr::new(endpoint_id(device)?);
    if let Some(hint) = load_peers(dirs).get(device) {
        for a in hint["addrs"].as_array().into_iter().flatten().filter_map(Value::as_str) {
            if let Ok(sa) = a.parse() {
                addr = addr.with_ip_addr(sa);
            }
        }
        if let Some(r) = hint["relay"].as_str().and_then(|r| RelayUrl::from_str(r).ok()) {
            addr = addr.with_relay_url(r);
        }
    }
    Ok(addr)
}

// --------------------------------------------------------------------------------------- framing

async fn read_frame(recv: &mut RecvStream) -> anyhow::Result<Option<Frame>> {
    let mut len = [0u8; 4];
    match recv.read_exact(&mut len).await {
        Ok(()) => {}
        Err(_) => return Ok(None),
    }
    let n = u32::from_be_bytes(len) as usize;
    if n > lsync::MAX_FRAME {
        bail!("frame too large");
    }
    let mut body = vec![0u8; n];
    recv.read_exact(&mut body).await.context("short frame")?;
    Ok(Some(lsync::decode(&body)?))
}

async fn write_frame(send: &mut SendStream, f: &Frame) -> anyhow::Result<()> {
    send.write_all(&lsync::encode(f)?).await?;
    Ok(())
}

fn refuse(net: &Net, conn: &Connection, alpn: &str, why: &str) {
    net.d.log_refusal(&conn.remote_id().to_string(), alpn, why);
    conn.close(CLOSE_REFUSED.into(), b"");
}

// ------------------------------------------------------------------------------------- protocols

/// Admits only devices that are members of at least one of our links.
#[derive(Clone, Debug)]
struct Gated<P> {
    net: Arc<NetRef>,
    inner: P,
    name: &'static str,
}

/// A late-bound handle, so protocols can be built before the `Net` they serve.
#[derive(Debug, Default)]
struct NetRef(OnceLock<std::sync::Weak<Net>>);

impl NetRef {
    fn get(&self) -> Option<Arc<Net>> {
        self.0.get().and_then(std::sync::Weak::upgrade)
    }
}

impl std::fmt::Debug for Net {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Net")
    }
}

impl<P: ProtocolHandler> ProtocolHandler for Gated<P> {
    async fn accept(&self, conn: Connection) -> Result<(), AcceptError> {
        let Some(net) = self.net.get() else { return Ok(()) };
        let peer = hex(conn.remote_id().as_bytes());
        if !net.d.is_member_anywhere(&peer) {
            refuse(&net, &conn, self.name, "not a member of any link here");
            return Ok(());
        }
        self.inner.accept(conn).await
    }
}

#[derive(Clone, Debug)]
struct LinkProto(Arc<NetRef>);

impl ProtocolHandler for LinkProto {
    async fn accept(&self, conn: Connection) -> Result<(), AcceptError> {
        let Some(net) = self.0.get() else { return Ok(()) };
        let peer = hex(conn.remote_id().as_bytes());
        let Ok((send, mut recv)) = conn.accept_bi().await else {
            return Ok(());
        };
        let first = match read_frame(&mut recv).await {
            Ok(Some(f @ Frame::Hello { .. })) => f,
            _ => {
                refuse(&net, &conn, "link", "first frame was not a hello");
                return Ok(());
            }
        };
        let Frame::Hello { link, .. } = &first else {
            unreachable!()
        };
        let link = link.clone();
        if !net.d.peer_links().get(&peer).is_some_and(|ls| ls.contains(&link)) {
            refuse(&net, &conn, "link", "not a member of the link it asked for");
            return Ok(());
        }
        if let Err(e) = run_session(net.clone(), link, peer.clone(), conn.clone(), send, recv, Some(first)).await {
            tracing::debug!("session with {peer}: {e:#}");
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
struct JoinProto(Arc<NetRef>);

impl ProtocolHandler for JoinProto {
    async fn accept(&self, conn: Connection) -> Result<(), AcceptError> {
        let Some(net) = self.0.get() else { return Ok(()) };
        let Ok((mut send, mut recv)) = conn.accept_bi().await else {
            return Ok(());
        };
        let device = match net.d.device() {
            Ok(d) => d,
            Err(_) => return Ok(()),
        };
        // At most two frames: JoinHello, then Join.
        for _ in 0..2 {
            let frame = match tokio::time::timeout(Duration::from_secs(60), read_frame(&mut recv)).await {
                Ok(Ok(Some(f))) => f,
                _ => return Ok(()),
            };
            let link_id = match &frame {
                Frame::JoinHello { link, .. } => link.clone(),
                Frame::Join { entry } => entry.link.clone(),
                _ => {
                    refuse(&net, &conn, "join", "unexpected frame");
                    return Ok(());
                }
            };
            let is_join = matches!(frame, Frame::Join { .. });
            let result = net.d.with_link(&link_id, |l| {
                let before = l.acl.hashes();
                let out = lsync::serve_join(l, &device, frame, now())?;
                if is_join {
                    net.d.after_acl_change(l, &before)?;
                }
                Ok(out)
            });
            match result {
                Ok(replies) => {
                    for r in replies {
                        if write_frame(&mut send, &r).await.is_err() {
                            return Ok(());
                        }
                    }
                }
                Err(e) => {
                    refuse(&net, &conn, "join", &e.message);
                    return Ok(());
                }
            }
        }
        let _ = send.finish();
        conn.closed().await;
        Ok(())
    }
}

/// Gate blob `get`s: the requester must share a link with us that lists the blob.
fn blob_events(net: Arc<NetRef>) -> EventSender {
    let mask = EventMask {
        connected: ConnectMode::Intercept,
        get: RequestMode::Intercept,
        get_many: RequestMode::Disabled,
        push: RequestMode::Disabled,
        ..EventMask::DEFAULT
    };
    let (tx, mut rx) = EventSender::channel(64, mask);
    tokio::spawn(async move {
        let mut by_conn: HashMap<u64, String> = HashMap::new();
        while let Some(msg) = rx.recv().await {
            let Some(net) = net.get() else { continue };
            match msg {
                ProviderMessage::ClientConnected(msg) => {
                    let ok = msg
                        .endpoint_id
                        .map(|id| hex(id.as_bytes()))
                        .filter(|d| net.d.is_member_anywhere(d));
                    let res = match ok {
                        Some(d) => {
                            by_conn.insert(msg.connection_id, d);
                            Ok(())
                        }
                        None => Err(AbortReason::Permission),
                    };
                    msg.tx.send(res).await.ok();
                }
                ProviderMessage::ConnectionClosed(msg) => {
                    by_conn.remove(&msg.connection_id);
                }
                ProviderMessage::GetRequestReceived(msg) => {
                    let blob = hex(msg.request.hash.as_bytes());
                    let allowed = msg.request.ranges.is_blob()
                        && by_conn
                            .get(&msg.connection_id)
                            .is_some_and(|d| net.blob_shared_with(&blob, d));
                    if !allowed {
                        net.d.log_refusal(
                            by_conn.get(&msg.connection_id).map(String::as_str).unwrap_or("?"),
                            "blobs",
                            "blob not in a shared link",
                        );
                    }
                    msg.tx
                        .send(if allowed { Ok(()) } else { Err(AbortReason::Permission) })
                        .await
                        .ok();
                }
                _ => {}
            }
        }
    });
    tx
}

// ------------------------------------------------------------------------------------------- Net

impl Net {
    pub async fn start(d: Shared, opts: NetOpts) -> anyhow::Result<Arc<Net>> {
        let device = d.device().map_err(|e| anyhow!(e.message))?;
        let secret = SecretKey::from_bytes(&device.sign.to_bytes());
        if hex(secret.public().as_bytes()) != device.id_hex() {
            bail!("iroh derived a different node id from the device key");
        }
        let mut builder = if opts.n0 {
            Endpoint::builder(presets::N0)
        } else {
            Endpoint::builder(presets::Minimal)
        };
        builder = builder.secret_key(secret).alpns(vec![
            LINK_ALPN.to_vec(),
            JOIN_ALPN.to_vec(),
            iroh_gossip::ALPN.to_vec(),
            iroh_blobs::ALPN.to_vec(),
        ]);
        if opts.no_relay {
            builder = builder.relay_mode(RelayMode::Disabled);
        } else if !opts.relays.is_empty() {
            let urls: Vec<RelayUrl> = opts
                .relays
                .iter()
                .map(|r| RelayUrl::from_str(r))
                .collect::<Result<_, _>>()?;
            builder = builder.relay_mode(RelayMode::custom(urls));
        }
        if opts.mdns {
            builder = builder.address_lookup(iroh_mdns_address_lookup::MdnsAddressLookup::builder());
        }
        if let Some(bind) = opts.bind {
            builder = builder.bind_addr(bind)?;
        }
        let endpoint = builder.bind().await?;
        let gossip = Gossip::builder().spawn(endpoint.clone());
        let blobs = blob_store(&d.dirs).await?;
        let handle = Arc::new(NetRef::default());
        let blobs_proto = BlobsProtocol::new(&blobs, Some(blob_events(handle.clone())));
        let router = Router::builder(endpoint.clone())
            .accept(LINK_ALPN, LinkProto(handle.clone()))
            .accept(JOIN_ALPN, JoinProto(handle.clone()))
            .accept(
                iroh_gossip::ALPN,
                Gated {
                    net: handle.clone(),
                    inner: gossip.clone(),
                    name: "gossip",
                },
            )
            .accept(
                iroh_blobs::ALPN,
                Gated {
                    net: handle.clone(),
                    inner: blobs_proto,
                    name: "blobs",
                },
            )
            .spawn();
        let net = Arc::new(Net {
            d,
            endpoint,
            gossip,
            blobs,
            router: OnceLock::new(),
            live: Mutex::new(HashMap::new()),
            topics: Mutex::new(BTreeMap::new()),
            backoff: Mutex::new(HashMap::new()),
        });
        let _ = net.router.set(router);
        let _ = handle.0.set(Arc::downgrade(&net));
        tokio::spawn(dialer(net.clone()));
        tokio::spawn(blob_fetcher(net.clone()));
        Ok(net)
    }

    pub async fn shutdown(&self) {
        if let Some(r) = self.router.get() {
            let _ = r.shutdown().await;
        }
    }

    pub fn hints(&self) -> (Option<String>, Vec<String>) {
        let addr = self.endpoint.addr();
        (
            addr.relay_urls().next().map(|u| u.to_string()),
            addr.ip_addrs().take(4).map(|a| a.to_string()).collect(),
        )
    }

    pub fn live_peers(&self, link: &str) -> Vec<String> {
        self.live
            .lock()
            .expect("live")
            .keys()
            .filter(|(l, _)| l == link)
            .map(|(_, p)| p.clone())
            .collect()
    }

    pub fn status(&self) -> Value {
        let (relay, addrs) = self.hints();
        let live: Vec<Value> = self
            .live
            .lock()
            .expect("live")
            .iter()
            .map(|((l, p), since)| json!({"link": l, "peer": p, "since": since}))
            .collect();
        json!({"endpoint": hex(self.endpoint.id().as_bytes()), "relay": relay, "addrs": addrs, "sessions": live})
    }

    fn blob_shared_with(&self, blob: &str, device: &str) -> bool {
        let links = self.d.peer_links();
        let Some(shared) = links.get(device) else { return false };
        shared.iter().any(|l| {
            self.d
                .with_link(l, |link| Ok(link.store.blob_ids()?.iter().any(|b| b == blob)))
                .unwrap_or(false)
        })
    }

    /// Announce our feed's head on the link's gossip topic.
    pub fn advertise(self: &Arc<Self>, link: &str) {
        let net = self.clone();
        let link = link.to_owned();
        tokio::spawn(async move {
            let Ok(device) = net.d.device() else { return };
            let Ok(Some(advert)) = net.d.with_link(&link, |l| {
                Ok(match l.store.head(&device.id_hex())? {
                    Some((seq, id)) => Some(HeadAdvert::sign(&device, l.id(), seq, &id, now())?),
                    None => None,
                })
            }) else {
                return;
            };
            if let Ok(sender) = net.topic_sender(&link).await {
                let _ = sender
                    .broadcast(serde_json::to_vec(&advert).expect("json").into())
                    .await;
            }
        });
    }

    async fn topic_sender(self: &Arc<Self>, link: &str) -> anyhow::Result<GossipSender> {
        if let Some(s) = self.topics.lock().expect("topics").get(link) {
            return Ok(s.clone());
        }
        let me = self.d.device().map_err(|e| anyhow!(e.message))?.id_hex();
        let bootstrap: Vec<EndpointId> = self
            .d
            .peer_links()
            .into_iter()
            .filter(|(d, ls)| *d != me && ls.iter().any(|l| l == link))
            .filter_map(|(d, _)| endpoint_id(&d).ok())
            .collect();
        let (sender, mut receiver) = self.gossip.subscribe(topic(link), bootstrap).await?.split();
        self.topics
            .lock()
            .expect("topics")
            .insert(link.to_owned(), sender.clone());
        let net = self.clone();
        let link = link.to_owned();
        tokio::spawn(async move {
            while let Some(Ok(event)) = receiver.next().await {
                if let Event::Received(msg) = event {
                    let Ok(advert) = serde_json::from_slice::<HeadAdvert>(&msg.content) else {
                        continue;
                    };
                    if advert.link != link || advert.verify().is_err() {
                        continue;
                    }
                    let behind = net
                        .d
                        .with_link(&link, |l| {
                            let known = l.state().devices.contains_key(&advert.author);
                            Ok(known && l.store.head(&advert.author)?.map(|h| h.0).unwrap_or(0) < advert.seq)
                        })
                        .unwrap_or(false);
                    if behind {
                        net.d.wake.notify_waiters();
                    }
                }
            }
            net.topics.lock().expect("topics").remove(&link);
        });
        Ok(sender)
    }

    /// Join through the inviter named in the code: fetch its log, hand over our join entry,
    /// take the log back (with our accept when the invite needs no approval), then sync.
    pub async fn join(self: &Arc<Self>, code: &InviteCode, label: &str) -> Result<String, RpcError> {
        let mut addr = EndpointAddr::new(endpoint_id(&code.node).map_err(RpcError::internal)?);
        for a in &code.addrs {
            if let Ok(sa) = a.parse() {
                addr = addr.with_ip_addr(sa);
            }
        }
        if let Some(r) = code.relay.as_ref().and_then(|r| RelayUrl::from_str(r).ok()) {
            addr = addr.with_relay_url(r);
        }
        let fail = |e: &dyn std::fmt::Display| RpcError::unavailable(format!("could not reach the inviter: {e}"));
        let conn = tokio::time::timeout(Duration::from_secs(60), self.endpoint.connect(addr, JOIN_ALPN))
            .await
            .map_err(|e| fail(&e))?
            .map_err(|e| fail(&e))?;
        let (mut send, mut recv) = conn.open_bi().await.map_err(|e| fail(&e))?;
        let invite = hex(&crypto::public_of(&aurora_link::acl::invite_key(&code.secret_bytes()?)));
        write_frame(
            &mut send,
            &Frame::JoinHello {
                v: 1,
                link: code.link.clone(),
                invite,
            },
        )
        .await
        .map_err(|e| fail(&e))?;
        let refused = || RpcError::refused("the inviter refused: the code is used, expired, revoked or not theirs");
        let Some(Frame::Acl { entries }) = read_frame(&mut recv).await.map_err(|e| fail(&e))? else {
            return Err(refused());
        };
        let (entry, _) = self.d.join_with(code, entries, label)?;
        write_frame(&mut send, &Frame::Join { entry })
            .await
            .map_err(|e| fail(&e))?;
        let Some(Frame::Acl { entries }) = read_frame(&mut recv).await.map_err(|e| fail(&e))? else {
            return Err(refused());
        };
        let _ = send.finish();
        conn.close(0u32.into(), b"");
        let id = self.d.adopt(entries)?;
        if !code.addrs.is_empty() || code.relay.is_some() {
            let p =
                Params::new(json!({"device": code.node, "addrs": code.addrs, "relay": code.relay})).expect("object");
            let _ = peers_add(&self.d.dirs, &p);
        }
        self.d.wake.notify_waiters();
        Ok(id)
    }

    async fn dial(self: Arc<Self>, link: String, peer: String) {
        let key = (link.clone(), peer.clone());
        let t = now();
        {
            let backoff = self.backoff.lock().expect("backoff");
            if backoff.get(&key).is_some_and(|(next, _)| *next > t) {
                return;
            }
        }
        let addr = match addr_for(&self.d.dirs, &peer) {
            Ok(a) => a,
            Err(_) => return,
        };
        let result = async {
            let conn = tokio::time::timeout(Duration::from_secs(30), self.endpoint.connect(addr, LINK_ALPN)).await??;
            let (send, recv) = conn.open_bi().await?;
            run_session(self.clone(), link.clone(), peer.clone(), conn, send, recv, None).await
        }
        .await;
        let mut backoff = self.backoff.lock().expect("backoff");
        match result {
            Ok(()) => {
                backoff.remove(&key);
            }
            Err(e) => {
                let step = backoff.get(&key).map(|(_, s)| (*s * 2).min(MAX_BACKOFF_S)).unwrap_or(5);
                backoff.insert(key, (now() + step, step));
                tracing::debug!("dial {peer} for {link}: {e:#}");
            }
        }
    }
}

/// Dial every member we are not already talking to, every 30 s or when woken.
async fn dialer(net: Arc<Net>) {
    loop {
        let links: Vec<String> = net.d.links.lock().expect("links").keys().cloned().collect();
        for link in &links {
            let _ = net.topic_sender(link).await;
        }
        for (peer, links) in net.d.peer_links() {
            for link in links {
                if !net
                    .live
                    .lock()
                    .expect("live")
                    .contains_key(&(link.clone(), peer.clone()))
                {
                    tokio::spawn(net.clone().dial(link, peer.clone()));
                }
            }
        }
        tokio::select! {
            _ = tokio::time::sleep(DIAL_EVERY) => {}
            _ = net.d.wake.notified() => {
                net.backoff.lock().expect("backoff").clear();
            }
        }
    }
}

/// Fetch blobs our links list but our store lacks, from whoever is live on that link.
async fn blob_fetcher(net: Arc<Net>) {
    let downloader = net.blobs.downloader(&net.endpoint);
    let every = std::env::var("AURORA_LINKD_BLOB_POLL_S")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(15);
    loop {
        tokio::time::sleep(Duration::from_secs(every)).await;
        let wanted: Vec<(String, Vec<String>)> = {
            let links = net.d.links.lock().expect("links");
            links
                .iter()
                .map(|(id, l)| (id.clone(), l.store.blob_ids().unwrap_or_default()))
                .collect()
        };
        for (link, ids) in wanted {
            let providers: Vec<EndpointId> = net
                .live_peers(&link)
                .iter()
                .filter_map(|p| endpoint_id(p).ok())
                .collect();
            if providers.is_empty() {
                continue;
            }
            for id in ids {
                let Ok(raw) = unhex::<32>(&id) else { continue };
                let hash = Hash::from_bytes(raw);
                if net.blobs.blobs().has(hash).await.unwrap_or(false) {
                    continue;
                }
                if downloader.download(hash, providers.clone()).await.is_ok() {
                    let _ = net.blobs.tags().set(format!("aurora-link/{id}"), hash).await;
                }
            }
        }
    }
}

pub async fn blob_get(ctx: &Ctx, p: &Params) -> Result<Value, RpcError> {
    let (link, rid, blob, out) = (p.str("link")?, p.str("record_id")?, p.str("blob")?, p.str("out")?);
    let r: BlobRef = ctx.d.with_link(&link, |l| {
        let sr = l
            .store
            .get(&rid)?
            .ok_or_else(|| RpcError::unavailable("no such record"))?;
        let body: Value = serde_json::from_str(
            sr.body
                .as_deref()
                .ok_or_else(|| RpcError::unavailable("record body is not readable here"))?,
        )
        .map_err(|e| RpcError::internal(e.into()))?;
        let refs: Vec<BlobRef> = serde_json::from_value(body.get("blobs").cloned().unwrap_or(json!([])))
            .map_err(|e| RpcError::internal(e.into()))?;
        refs.into_iter()
            .find(|b| b.id.starts_with(&blob) || b.name == blob)
            .ok_or_else(|| RpcError::unavailable("no such blob on that record"))
    })?;
    let store = match ctx.net() {
        Some(net) => net.blobs.clone(),
        None => blob_store(&ctx.d.dirs).await.map_err(RpcError::internal)?,
    };
    let hash = Hash::from_bytes(unhex::<32>(&r.id)?);
    if !store.blobs().has(hash).await.unwrap_or(false) {
        let net = ctx
            .net()
            .ok_or_else(|| RpcError::unavailable("blob not here yet; start `aurora link serve` to fetch it"))?;
        let providers: Vec<EndpointId> = net
            .live_peers(&link)
            .iter()
            .filter_map(|p| endpoint_id(p).ok())
            .collect();
        let downloader = net.blobs.downloader(&net.endpoint);
        let mut last = String::new();
        for attempt in 0..3u64 {
            match downloader.download(hash, providers.clone()).await {
                Ok(_) => {
                    last.clear();
                    break;
                }
                Err(e) => last = e.to_string(),
            }
            tokio::time::sleep(Duration::from_millis(500 * (attempt + 1))).await;
        }
        if !last.is_empty() && !store.blobs().has(hash).await.unwrap_or(false) {
            return Err(RpcError::unavailable(format!("fetch failed: {last}")));
        }
    }
    let ct = store
        .blobs()
        .get_bytes(hash)
        .await
        .map_err(|e| RpcError::unavailable(format!("{e}")))?;
    let plain = record::open_blob(&r, &ct)?;
    std::fs::write(&out, &plain).map_err(|e| RpcError::internal(e.into()))?;
    Ok(json!({"out": out, "bytes": plain.len(), "name": r.name}))
}

// ------------------------------------------------------------------------------------- sessions

async fn run_session(
    net: Arc<Net>,
    link: String,
    peer: String,
    conn: Connection,
    mut send: SendStream,
    mut recv: RecvStream,
    first: Option<Frame>,
) -> anyhow::Result<()> {
    let device = net.d.device().map_err(|e| anyhow!(e.message))?;
    let key = (link.clone(), peer.clone());
    net.live.lock().expect("live").insert(key.clone(), now());
    let _guard = LiveGuard(net.clone(), key);
    net.d
        .with_link(&link, |l| Ok(l.store.contact(&peer, "direct", now())?))
        .ok();

    let (tx, mut rx) = mpsc::channel::<Frame>(64);
    let writer = tokio::spawn(async move {
        while let Some(f) = rx.recv().await {
            if write_frame(&mut send, &f).await.is_err() {
                break;
            }
        }
        let _ = send.finish();
    });
    let mut pushes = net.d.pushes(&link).subscribe();
    let mut session = Session::new();
    let hello = net
        .d
        .with_link(&link, |l| Ok(lsync::hello(l, &device)?))
        .map_err(|e| anyhow!(e.message))?;
    tx.send(hello).await?;
    let mut pending = first;
    loop {
        let frame = if let Some(f) = pending.take() {
            f
        } else {
            tokio::select! {
                f = read_frame(&mut recv) => match f? { Some(f) => f, None => break },
                p = pushes.recv() => {
                    match p {
                        Ok(Push::Records(rs)) => for f in session.push(&rs) { tx.send(f).await?; },
                        Ok(Push::Acl(entries)) => tx.send(Frame::Acl { entries }).await?,
                        Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => {
                            let h = net.d.with_link(&link, |l| Ok(l.heads()?)).map_err(|e| anyhow!(e.message))?;
                            tx.send(Frame::Synced { heads: h }).await?;
                        }
                        Err(_) => break,
                    }
                    continue;
                }
            }
        };
        if let Frame::Bye { .. } = frame {
            break;
        }
        let outcome = net.d.with_link(&link, |l| {
            let before = l.acl.hashes();
            let out = session.on_frame(l, &device, &peer, frame, now())?;
            if out.acl_added > 0 {
                net.d.after_acl_change(l, &before)?;
            }
            Ok(out)
        });
        let outcome = match outcome {
            Ok(o) => o,
            Err(e) => {
                refuse(&net, &conn, "link", &e.message);
                break;
            }
        };
        for f in outcome.replies {
            tx.send(f).await?;
        }
        if !outcome.stored.is_empty() {
            net.d.push(&link, Push::Records(outcome.stored));
            net.d.events.notify_waiters();
        }
    }
    drop(tx);
    let _ = writer.await;
    Ok(())
}

struct LiveGuard(Arc<Net>, (String, String));

impl Drop for LiveGuard {
    fn drop(&mut self) {
        self.0.live.lock().expect("live").remove(&self.1);
    }
}

/// Peers we have refused recently, for `doctor`.
pub fn recent_refusals(dirs: &Dirs, limit: usize) -> Vec<String> {
    std::fs::read_to_string(dirs.refusals_log())
        .map(|s| s.lines().rev().take(limit).map(str::to_owned).collect())
        .unwrap_or_default()
}
