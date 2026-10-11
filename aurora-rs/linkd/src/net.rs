//! The network: one iroh endpoint whose key is this device's key, and four protocols on it.
//!
//! - `aurora/link/1`: sync sessions (aurora_link::sync), one bi-stream per session;
//! - `aurora/link-join/1`: an invitee fetching the log and handing over its join entry;
//! - iroh-gossip: signed head adverts on a per-link topic, so peers sync as soon as there is news.
//!   The topic id is derived from the link's genesis entry, which only those who were given the
//!   log hold (the link id alone, which invite codes carry, does not give it), and an advert
//!   counts only when it arrives from a device of that link;
//! - iroh-blobs: encrypted attachments. Push is disabled, `get_many` is disabled, and `get` is
//!   allowed only for a blob of a link the requesting device is a member of.
//!
//! Every protocol except join refuses a device that is not a member of any of our links, with
//! one uniform close code and no reason on the wire. The real reason goes to the local log.
//! (A member that asks for a blob its links don't list gets iroh-blobs' own permission refusal;
//! only members can see that difference.)
//! Join attempts are rate-limited per remote id and per IP address, and joins and sync sessions
//! each have a cap on how many run at once. A device holds at most `MAX_SESSIONS_PER_PEER_LINK`
//! sync sessions per link with us, and a session with no frame for `IDLE_TIMEOUT` is closed;
//! each side sends a `ping` every `PING_EVERY`, so a quiet but live session stays open (review
//! finding R5-4). A device opens at most `SESSION_STARTS_PER_MIN` sessions per link a minute with
//! us, and what its frames spend of the sync budgets (`lsync::Budget`) is kept per link and device
//! across sessions, so a reconnect starts where the last session left off (review finding R8-3).

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
use iroh::endpoint::{Accepting, Connection, IncomingAddr, RecvStream, SendStream, presets};
use iroh::protocol::{AcceptError, ProtocolHandler, Router};
use iroh::{Endpoint, EndpointAddr, EndpointId, RelayMode, RelayUrl, SecretKey};
use iroh_blobs::api::downloader::{DownloadProgressItem, Downloader};
use iroh_blobs::api::proto::BlobStatus;
use iroh_blobs::protocol::{ChunkRanges, ChunkRangesExt, GetRequest};
use iroh_blobs::provider::events::{AbortReason, ConnectMode, EventMask, EventSender, ProviderMessage, RequestMode};
use iroh_blobs::store::fs::FsStore;
use iroh_blobs::{BlobsProtocol, Hash};
use iroh_gossip::api::{Event, GossipSender};
use iroh_gossip::{Gossip, TopicId};
use n0_future::StreamExt;
use serde_json::{Value, json};
use tokio::sync::{Semaphore, mpsc};

use crate::daemon::{Dirs, Push, Shared};
use crate::rpc::{Ctx, Params, RpcError};

pub const LINK_ALPN: &[u8] = lsync::ALPN;
pub const JOIN_ALPN: &[u8] = b"aurora/link-join/2";
/// The one close code every refusal gets.
pub const CLOSE_REFUSED: u32 = 1;
const DIAL_EVERY: Duration = Duration::from_secs(30);
const MAX_BACKOFF_S: u64 = 600;
/// Join attempts one remote id, and one IP address, may make per minute.
const JOINS_PER_ID_PER_MIN: u32 = 6;
const JOINS_PER_IP_PER_MIN: u32 = 20;
/// Joins, and sync sessions, served at once.
const MAX_JOINS_AT_ONCE: usize = 8;
const MAX_SESSIONS_AT_ONCE: usize = 256;
/// Sync sessions one device may hold with us per link at once (review finding R5-4).
pub const MAX_SESSIONS_PER_PEER_LINK: usize = 2;
/// Sync sessions one device may open with us per link a minute (review finding R8-3). Honest
/// dialers try a peer they are not talking to every 30 s, with a backoff on failure.
pub const SESSION_STARTS_PER_MIN: u32 = 10;
/// A session with no frame from its peer for this long is closed (pings count).
pub const IDLE_TIMEOUT: Duration = Duration::from_secs(120);
/// How often each side of a session sends a ping.
const PING_EVERY: Duration = Duration::from_secs(45);
/// How long the join door waits for the sequencer to include a join it handed on.
const JOIN_WAIT: Duration = Duration::from_secs(20);
/// At most one gossip-triggered wake of the dialer per link this often.
const ADVERT_WAKE_EVERY_S: u64 = 2;

/// At most `max` events per key per `window_s` seconds (a fixed window). The table is bounded:
/// when it is full of live windows, a new key is refused rather than an old one forgotten.
#[derive(Debug)]
pub struct Limiter {
    max: u32,
    window_s: u64,
    seen: Mutex<HashMap<String, (u64, u32)>>,
}

const LIMITER_KEYS: usize = 4096;

impl Limiter {
    pub fn new(max: u32, window_s: u64) -> Self {
        Self {
            max,
            window_s,
            seen: Mutex::new(HashMap::new()),
        }
    }

    pub fn allow(&self, key: &str, t: u64) -> bool {
        let mut seen = self.seen.lock().expect("limiter");
        if seen.len() >= LIMITER_KEYS && !seen.contains_key(key) {
            seen.retain(|_, (start, _)| *start + self.window_s > t);
            if seen.len() >= LIMITER_KEYS {
                return false;
            }
        }
        let e = seen.entry(key.to_owned()).or_insert((t, 0));
        if e.0 + self.window_s <= t {
            *e = (t, 0);
        }
        e.1 = e.1.saturating_add(1);
        e.1 <= self.max
    }
}

#[derive(Clone, Debug, Default)]
pub struct NetOpts {
    /// Publish and resolve addresses through n0's DNS (pkarr), and use n0's relays by default.
    pub n0: bool,
    pub mdns: bool,
    pub relays: Vec<String>,
    pub no_relay: bool,
    pub bind: Option<std::net::SocketAddr>,
    /// No IP transports at all: every byte goes through a relay. For fleets behind networks that
    /// block UDP, and for testing what two fleets on different networks see.
    pub relay_only: bool,
    /// Close a session with no frame for this long (default `IDLE_TIMEOUT`; tests shorten it).
    pub idle: Option<Duration>,
}

pub struct Net {
    pub d: Shared,
    pub endpoint: Endpoint,
    pub gossip: Gossip,
    pub blobs: FsStore,
    router: OnceLock<Router>,
    live: Mutex<HashMap<(String, String), u64>>,
    /// Sync sessions per (link, peer), both directions.
    pub sessions: Arc<SessionCount>,
    idle: Duration,
    topics: Mutex<BTreeMap<String, GossipSender>>,
    backoff: Mutex<HashMap<(String, String), (u64, u64)>>,
    joins_by_id: Limiter,
    joins_by_ip: Limiter,
    join_slots: Arc<Semaphore>,
    session_slots: Arc<Semaphore>,
    /// When each link last woke the dialer from gossip.
    advert_wakes: Mutex<HashMap<String, u64>>,
    /// New sync sessions per (link, peer), a minute.
    session_starts: Limiter,
    /// What each (link, peer) has spent of the sync budgets this minute, across its sessions.
    budgets: Mutex<HashMap<(String, String), lsync::Budget>>,
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

/// A link's gossip topic: derived from its whole genesis entry (signature included), which every
/// member holds and keeps across key rotations, and which the link id (its hash, carried in
/// invite codes) does not reveal. A device that never got the log cannot even name the topic.
pub(crate) fn topic(l: &aurora_link::engine::Link) -> anyhow::Result<TopicId> {
    let genesis = l.acl.entry(0).context("the link's genesis entry is missing")?;
    let bytes = aurora_link::codec::canonical(genesis)?;
    Ok(TopicId::from_bytes(crypto::blake3(
        &[b"aurora-link/v2/gossip-topic\0".as_slice(), &bytes].concat(),
    )))
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
    read_frame_max(recv, lsync::MAX_FRAME).await
}

/// The first frame of a connection comes from a peer nobody has checked yet: keep it small. A
/// hello always fits (`aurora_link::sync::hello`), however large the log.
const MAX_FIRST_FRAME: usize = lsync::MAX_FIRST_FRAME;
const FIRST_FRAME_WITHIN: Duration = Duration::from_secs(30);

async fn read_frame_max(recv: &mut RecvStream, max: usize) -> anyhow::Result<Option<Frame>> {
    let mut len = [0u8; 4];
    match recv.read_exact(&mut len).await {
        Ok(()) => {}
        Err(_) => return Ok(None),
    }
    let n = u32::from_be_bytes(len) as usize;
    if n > max {
        bail!("frame too large");
    }
    let mut body = vec![0u8; n];
    recv.read_exact(&mut body).await.context("short frame")?;
    Ok(Some(lsync::decode(&body)?))
}

/// What the inviter answered on a join stream.
enum JoinReply {
    /// The chain, up to `synced`.
    Chain(Vec<aurora_link::acl::Entry>),
    /// A `bye` with its reason (a join queued for the sequencer, or refused by it).
    Bye(String),
    /// The inviter closed.
    Closed,
}

async fn read_log(recv: &mut RecvStream) -> anyhow::Result<JoinReply> {
    let mut out = Vec::new();
    loop {
        match read_frame(recv).await? {
            Some(Frame::Acl { entries }) => out.extend(entries),
            Some(Frame::Synced { .. }) => return Ok(JoinReply::Chain(out)),
            Some(Frame::Bye { reason }) => return Ok(JoinReply::Bye(reason)),
            _ => return Ok(JoinReply::Closed),
        }
    }
}

/// Live sync sessions per (link, peer): at most `MAX_SESSIONS_PER_PEER_LINK` each.
#[derive(Debug, Default)]
pub struct SessionCount(Mutex<HashMap<(String, String), usize>>);

impl SessionCount {
    /// A slot for one more session of `peer` on `link`, if it has fewer than the cap.
    pub fn take(self: &Arc<Self>, link: &str, peer: &str) -> Option<SessionSlot> {
        let key = (link.to_owned(), peer.to_owned());
        let mut m = self.0.lock().expect("sessions");
        let n = m.entry(key.clone()).or_insert(0);
        if *n >= MAX_SESSIONS_PER_PEER_LINK {
            return None;
        }
        *n += 1;
        Some(SessionSlot(self.clone(), key))
    }

    #[cfg(test)]
    pub fn count(&self, link: &str, peer: &str) -> usize {
        self.0
            .lock()
            .expect("sessions")
            .get(&(link.to_owned(), peer.to_owned()))
            .copied()
            .unwrap_or(0)
    }
}

/// One session's place in `SessionCount`, given back on drop.
pub struct SessionSlot(Arc<SessionCount>, (String, String));

impl Drop for SessionSlot {
    fn drop(&mut self) {
        let mut m = self.0.0.lock().expect("sessions");
        if let Some(n) = m.get_mut(&self.1) {
            *n = n.saturating_sub(1);
            if *n == 0 {
                m.remove(&self.1);
            }
        }
    }
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
        let first = match tokio::time::timeout(FIRST_FRAME_WITHIN, read_frame_max(&mut recv, MAX_FIRST_FRAME)).await {
            Ok(Ok(Some(f @ Frame::Hello { .. }))) => f,
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
        if !net.session_starts.allow(&format!("{link} {peer}"), now()) {
            refuse(
                &net,
                &conn,
                "link",
                "too many new sync sessions from this device for this link this minute",
            );
            return Ok(());
        }
        let Ok(_slot) = net.session_slots.clone().try_acquire_owned() else {
            refuse(&net, &conn, "link", "too many sync sessions at once");
            return Ok(());
        };
        let Some(per_peer) = net.sessions.take(&link, &peer) else {
            refuse(
                &net,
                &conn,
                "link",
                "too many sync sessions from this device for this link",
            );
            return Ok(());
        };
        if let Err(e) = run_session(
            net.clone(),
            link,
            peer.clone(),
            conn.clone(),
            send,
            recv,
            Some(first),
            per_peer,
        )
        .await
        {
            tracing::debug!("session with {peer}: {e:#}");
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
struct JoinProto(Arc<NetRef>);

impl ProtocolHandler for JoinProto {
    /// Before the handshake costs us anything: a per-IP budget for join attempts.
    async fn on_accepting(&self, accepting: Accepting) -> Result<Connection, AcceptError> {
        if let (Some(net), IncomingAddr::Ip(sa)) = (self.0.get(), accepting.remote_addr())
            && !net.joins_by_ip.allow(&sa.ip().to_string(), now())
        {
            net.d
                .log_refusal("?", "join", &format!("too many join attempts from {}", sa.ip()));
            return Err(AcceptError::from_err(std::io::Error::other("rate limited")));
        }
        Ok(accepting.await?)
    }

    async fn accept(&self, conn: Connection) -> Result<(), AcceptError> {
        let Some(net) = self.0.get() else { return Ok(()) };
        let peer = hex(conn.remote_id().as_bytes());
        if !net.joins_by_id.allow(&peer, now()) {
            refuse(&net, &conn, "join", "too many join attempts from this device");
            return Ok(());
        }
        let Ok(_slot) = net.join_slots.clone().try_acquire_owned() else {
            refuse(&net, &conn, "join", "too many joins at once");
            return Ok(());
        };
        let Ok((mut send, mut recv)) = conn.accept_bi().await else {
            return Ok(());
        };
        let device = match net.d.device() {
            Ok(d) => d,
            Err(_) => return Ok(()),
        };
        // At most two frames, JoinHello then Join, from a peer nobody has vouched for: small and
        // quick. The door ties the Join to the verified JoinHello of this same stream.
        let mut door = lsync::JoinDoor::new();
        for _ in 0..2 {
            let frame = match tokio::time::timeout(FIRST_FRAME_WITHIN, read_frame_max(&mut recv, MAX_FIRST_FRAME)).await
            {
                Ok(Ok(Some(f))) => f,
                _ => return Ok(()),
            };
            let link_id = match &frame {
                Frame::JoinHello { link, .. } => link.clone(),
                Frame::Join { proposal } => proposal.link.clone(),
                _ => {
                    refuse(&net, &conn, "join", "unexpected frame");
                    return Ok(());
                }
            };
            let proposal = match &frame {
                Frame::Join { proposal } => Some(proposal.clone()),
                _ => None,
            };
            let result = net.d.with_link(&link_id, |l| {
                let before = l.acl.tip();
                let out = door.on_frame(l, &device, &peer, frame, now())?;
                if proposal.is_some() {
                    net.d.after_acl_change(l, &before)?;
                }
                Ok(out)
            });
            let mut replies = match result {
                Ok(replies) => replies,
                Err(e) => {
                    refuse(&net, &conn, "join", &e.message);
                    return Ok(());
                }
            };
            // A join this replica cannot include (it does not sequence the link) goes on toward
            // the sequencer; the joiner waits a little for it here.
            if let (Some(p), true) = (proposal, door.queued.is_some()) {
                net.d.push(&link_id, Push::Proposal(p));
                let deadline = tokio::time::Instant::now() + JOIN_WAIT;
                replies = loop {
                    match net.d.with_link(&link_id, |l| Ok(door.poll(l))) {
                        Ok(Some(Ok(frames))) => break frames,
                        Ok(Some(Err(e))) => {
                            refuse(&net, &conn, "join", &e.to_string());
                            return Ok(());
                        }
                        _ if tokio::time::Instant::now() >= deadline => {
                            break vec![Frame::Bye {
                                reason: "queued: the join waits for the link's sequencer; run the join again later"
                                    .into(),
                            }];
                        }
                        _ => tokio::time::sleep(Duration::from_millis(250)).await,
                    }
                };
            }
            for r in replies {
                if write_frame(&mut send, &r).await.is_err() {
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
        if opts.relay_only {
            builder = builder.clear_ip_transports();
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
            sessions: Arc::new(SessionCount::default()),
            idle: opts.idle.unwrap_or(IDLE_TIMEOUT),
            topics: Mutex::new(BTreeMap::new()),
            backoff: Mutex::new(HashMap::new()),
            joins_by_id: Limiter::new(JOINS_PER_ID_PER_MIN, 60),
            joins_by_ip: Limiter::new(JOINS_PER_IP_PER_MIN, 60),
            join_slots: Arc::new(Semaphore::new(MAX_JOINS_AT_ONCE)),
            session_slots: Arc::new(Semaphore::new(MAX_SESSIONS_AT_ONCE)),
            advert_wakes: Mutex::new(HashMap::new()),
            session_starts: Limiter::new(SESSION_STARTS_PER_MIN, 60),
            budgets: Mutex::new(HashMap::new()),
        });
        let _ = net.router.set(router);
        let _ = handle.0.set(Arc::downgrade(&net));
        tokio::spawn(dialer(net.clone()));
        tokio::spawn(blob_fetcher(net.clone()));
        Ok(net)
    }

    /// What `peer` has spent of the sync budgets on `link` this minute, over all its sessions.
    pub fn budget(&self, link: &str, peer: &str, now: u64) -> lsync::Budget {
        self.budgets
            .lock()
            .expect("budgets")
            .get(&(link.to_owned(), peer.to_owned()))
            .cloned()
            .filter(|b| b.current(now))
            .unwrap_or_default()
    }

    /// Keep `peer`'s budget on `link` after a frame. Only budgets of the current minute are kept,
    /// and only members reach a session, so the table holds at most one per member device and link.
    pub fn keep_budget(&self, link: &str, peer: &str, b: lsync::Budget, now: u64) {
        let mut budgets = self.budgets.lock().expect("budgets");
        if budgets.len() >= 4096 {
            budgets.retain(|_, b| b.current(now));
        }
        budgets.insert((link.to_owned(), peer.to_owned()), b);
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
        // Record data: the narrowed view of a halted link (review finding R7-2).
        let links = self.d.record_peer_links();
        let Some(shared) = links.get(device) else { return false };
        shared.iter().any(|l| {
            self.d
                .with_link(l, |link| Ok(link.blob_allowed(blob)?))
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
        let topic_id = self
            .d
            .with_link(link, |l| topic(l).map_err(RpcError::internal))
            .map_err(|e| anyhow!(e.message))?;
        let bootstrap: Vec<EndpointId> = self
            .d
            .peer_links()
            .into_iter()
            .filter(|(d, ls)| *d != me && ls.iter().any(|l| l == link))
            .filter_map(|(d, _)| endpoint_id(&d).ok())
            .collect();
        let (sender, mut receiver) = self.gossip.subscribe(topic_id, bootstrap).await?.split();
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
                    let from = hex(msg.delivered_from.as_bytes());
                    let says = net.d.with_link(&link, |l| {
                        // Per topic: only a device of this link may tell us about it.
                        if !lsync::may_sync(l, &from) {
                            return Ok(None);
                        }
                        Ok(Some(lsync::check_advert(l, &advert, now())?))
                    });
                    match says {
                        Ok(Some(lsync::AdvertSays::Behind)) => net.advert_wake(&link, &advert.author),
                        Ok(Some(lsync::AdvertSays::Equivocation)) => net.d.events.notify_waiters(),
                        Ok(None) => net
                            .d
                            .log_refusal(&from, "gossip", "advert from a device not in that link"),
                        _ => {}
                    }
                }
            }
            net.topics.lock().expect("topics").remove(&link);
        });
        Ok(sender)
    }

    /// An advert says a peer is ahead: forget that peer's dial backoff (it is evidently online)
    /// and wake the dialer, at most once per link every few seconds however many adverts arrive.
    fn advert_wake(&self, link: &str, author: &str) {
        self.backoff
            .lock()
            .expect("backoff")
            .remove(&(link.to_owned(), author.to_owned()));
        let t = now();
        let mut last = self.advert_wakes.lock().expect("advert wakes");
        if last.get(link).is_some_and(|at| t < at + ADVERT_WAKE_EVERY_S) {
            return;
        }
        last.insert(link.to_owned(), t);
        self.d.wake.notify_waiters();
    }

    /// Join through the inviter named in the code: fetch its chain, hand over our join proposal,
    /// take the chain back (with our accept when the invite needs no approval), then sync. When
    /// the inviter is not the sequencer and the sequencer is out of reach, the join is queued:
    /// the result is then the pending summary, and the same code fetches the chain later.
    pub async fn join(self: &Arc<Self>, code: &InviteCode, label: &str) -> Result<Joined, RpcError> {
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
        let me = self.d.device()?;
        let hello = lsync::join_hello(&code.link, &me, &code.ticket()?)?;
        write_frame(&mut send, &hello).await.map_err(|e| fail(&e))?;
        let refused = || RpcError::refused("the inviter refused: the code is used, expired, revoked or not theirs");
        let first = match read_log(&mut recv).await.map_err(|e| fail(&e))? {
            JoinReply::Chain(entries) => entries,
            JoinReply::Bye(why) => return Err(RpcError::refused(format!("the inviter said: {why}"))),
            JoinReply::Closed => return Err(refused()),
        };
        let mine = aurora_link::sync::chain_of(&first)?
            .state()
            .devices
            .contains_key(&me.id_hex());
        let entries = if mine {
            // Our join was included since we last asked (it was queued): just take the chain.
            first
        } else {
            let (proposal, _) = self.d.join_with(code, first.clone(), label)?;
            write_frame(&mut send, &Frame::Join { proposal })
                .await
                .map_err(|e| fail(&e))?;
            match read_log(&mut recv).await.map_err(|e| fail(&e))? {
                JoinReply::Chain(entries) => entries,
                JoinReply::Bye(why) if why.starts_with("queued") => {
                    let _ = send.finish();
                    conn.close(0u32.into(), b"");
                    let mut summary = self.d.pending_join_summary(code, &first)?;
                    summary["queued"] = json!(true);
                    summary["note"] = json!(why);
                    return Ok(Joined::Queued(summary));
                }
                JoinReply::Bye(why) => return Err(RpcError::refused(format!("the join was refused: {why}"))),
                JoinReply::Closed => return Err(refused()),
            }
        };
        let _ = send.finish();
        conn.close(0u32.into(), b"");
        // The log handed back must still be the link the code names.
        let genesis = entries
            .iter()
            .find(|e| e.seq == 0)
            .ok_or_else(|| RpcError::refused("the inviter's log has no genesis"))?;
        if genesis.hash()? != code.link {
            return Err(RpcError::refused(
                "the inviter handed back another link than the code names; not joining",
            ));
        }
        let id = self.d.adopt(entries)?;
        if !code.addrs.is_empty() || code.relay.is_some() {
            let p =
                Params::new(json!({"device": code.node, "addrs": code.addrs, "relay": code.relay})).expect("object");
            let _ = peers_add(&self.d.dirs, &p);
        }
        self.d.wake_now();
        Ok(Joined::Adopted(id))
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
        let Some(slot) = self.sessions.take(&link, &peer) else {
            return;
        };
        let result = async {
            let conn = tokio::time::timeout(Duration::from_secs(30), self.endpoint.connect(addr, LINK_ALPN)).await??;
            let (send, recv) = conn.open_bi().await?;
            run_session(self.clone(), link.clone(), peer.clone(), conn, send, recv, None, slot).await
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
        let links = net.d.link_ids();
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
                // Only an explicit `sync.now` (or a join) forgets every backoff; a gossip advert
                // already cleared the one peer it concerns.
                if net.d.reset_backoff.swap(false, std::sync::atomic::Ordering::Relaxed) {
                    net.backoff.lock().expect("backoff").clear();
                }
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
        let wanted: Vec<(String, Vec<(String, u64)>)> = net
            .d
            .held_links()
            .into_iter()
            .map(|(id, cell)| {
                let blobs = cell.with(|l| l.wanted_blobs().unwrap_or_default());
                (id, blobs)
            })
            .collect();
        for (link, blobs) in wanted {
            let providers: Vec<EndpointId> = net
                .live_peers(&link)
                .iter()
                .filter_map(|p| endpoint_id(p).ok())
                .collect();
            if providers.is_empty() {
                continue;
            }
            for (id, ct_len) in blobs {
                let Ok(raw) = unhex::<32>(&id) else { continue };
                let hash = Hash::from_bytes(raw);
                if net.blobs.blobs().has(hash).await.unwrap_or(false) {
                    continue;
                }
                if fetch_listed_blob(&net.blobs, &downloader, hash, ct_len, providers.clone())
                    .await
                    .is_ok()
                {
                    let _ = net.blobs.tags().set(format!("aurora-link/{id}"), hash).await;
                }
            }
        }
    }
}

/// Download one listed blob, asking for no more than the exact ciphertext length its record
/// signed (`ct_len`) and aborting if the provider sends more. The blob counts as fetched only when
/// it is complete at exactly that length; anything else is left untagged.
async fn fetch_listed_blob(
    store: &FsStore,
    downloader: &Downloader,
    hash: Hash,
    ct_len: u64,
    providers: Vec<EndpointId>,
) -> anyhow::Result<()> {
    if ct_len == 0 || ct_len > record::MAX_BLOB_CT_BYTES {
        bail!("listed blob length {ct_len} is out of range");
    }
    let request = GetRequest::blob_ranges(hash, ChunkRanges::bytes(..ct_len));
    let mut progress = downloader.download(request, providers).stream().await?;
    while let Some(item) = progress.next().await {
        match item {
            // Dropping the stream on return abandons the download.
            DownloadProgressItem::Progress(n) if n > ct_len => {
                bail!("blob is longer than the {ct_len} bytes its record signed")
            }
            DownloadProgressItem::Error(e) => bail!("blob download failed: {e}"),
            DownloadProgressItem::DownloadError => bail!("blob download failed"),
            _ => {}
        }
    }
    match store.blobs().status(hash).await? {
        BlobStatus::Complete { size } if size == ct_len => Ok(()),
        _ => bail!("blob does not have the {ct_len} bytes its record signed"),
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
    let ct_len = ctx
        .d
        .with_link(&link, |l| Ok(l.store.blob_listed(&r.id)?))?
        .ok_or_else(|| RpcError::unavailable("this link does not list that blob"))?;
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
            match fetch_listed_blob(&store, &downloader, hash, ct_len, providers.clone()).await {
                Ok(()) => {
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

#[allow(clippy::too_many_arguments)]
async fn run_session(
    net: Arc<Net>,
    link: String,
    peer: String,
    conn: Connection,
    mut send: SendStream,
    mut recv: RecvStream,
    first: Option<Frame>,
    _slot: SessionSlot,
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
    for f in hello {
        tx.send(f).await?;
    }
    let mut pending = first;
    let mut ping = tokio::time::interval(PING_EVERY.min(net.idle / 2));
    ping.tick().await;
    let mut last_frame = tokio::time::Instant::now();
    loop {
        let frame = if let Some(f) = pending.take() {
            f
        } else {
            tokio::select! {
                f = read_frame(&mut recv) => match f? { Some(f) => { last_frame = tokio::time::Instant::now(); f }, None => break },
                _ = tokio::time::sleep_until(last_frame + net.idle) => {
                    refuse(&net, &conn, "link", "no frame from the peer for too long");
                    break;
                }
                _ = ping.tick() => {
                    tx.send(Frame::Ping {}).await?;
                    continue;
                }
                p = pushes.recv() => {
                    // Every push (an ACL change included) re-checks the peer first: a device
                    // removed since the session began gets nothing more, and the session closes.
                    // A device of the held tip that a halt leaves out still gets the chain's
                    // entries (the takeover), and nothing else (review finding R7-2).
                    let (member, chain) = net
                        .d
                        .with_link(&link, |l| Ok((lsync::may_sync(l, &peer), lsync::may_sync_acl(l, &peer))))
                        .unwrap_or((false, false));
                    if !member && !chain {
                        refuse(&net, &conn, "link", "peer is no longer a member");
                        break;
                    }
                    match p {
                        Ok(Push::Acl(entries)) => for f in lsync::acl_frames(entries) { tx.send(f).await?; },
                        _ if !member => {}
                        Ok(Push::Records(rs)) => for f in session.push(&rs) { tx.send(f).await?; },
                        Ok(Push::Proposal(proposal)) => tx.send(Frame::Propose { proposal }).await?,
                        Ok(Push::Refusal(refusal)) => tx.send(Frame::Refusal { refusal }).await?,
                        Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => {
                            let h = net.d.with_link(&link, |l| Ok(lsync::heads_of(l)?)).map_err(|e| anyhow!(e.message))?;
                            // Pushes were dropped: tell the peer we hold more, so it asks.
                            tx.send(Frame::Synced { heads: h, more: true }).await?;
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
            let before = l.acl.tip();
            let t = now();
            // The peer's budgets carry over from its other and earlier sessions (R8-3).
            session.budget = net.budget(&link, &peer, t);
            let out = session.on_frame(l, &device, &peer, frame, t);
            net.keep_budget(&link, &peer, std::mem::take(&mut session.budget), t);
            let out = out?;
            if out.acl_added > 0 || l.acl.tip() != before {
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
        for p in outcome.relay {
            net.d.push(&link, Push::Proposal(p));
        }
        for r in outcome.refusals {
            net.d.push(&link, Push::Refusal(r));
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

/// What a network join became.
pub enum Joined {
    /// The join is on the chain: the link is adopted here.
    Adopted(String),
    /// The join waits for the link's sequencer: the pending summary.
    Queued(Value),
}

/// Peers we have refused recently, for `doctor`.
pub fn recent_refusals(dirs: &Dirs, limit: usize) -> Vec<String> {
    std::fs::read_to_string(dirs.refusals_log())
        .map(|s| s.lines().rev().take(limit).map(str::to_owned).collect())
        .unwrap_or_default()
}
