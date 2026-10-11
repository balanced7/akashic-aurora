//! The daemon's state and every RPC method that needs no network.
//!
//! Layout under the Aurora data root (`--home`):
//!
//! - `state/link/<link_id>.db`: one SQLite store per link (aurora-link's `Store`);
//! - `state/link/blobs/`: the iroh-blobs store (encrypted attachments only);
//! - `state/link/rpc/linkd.sock`: the RPC socket while `serve` runs, in a folder only this user
//!   can enter (a named pipe with an owner-only DACL on Windows);
//! - `<secrets>/link/device.json`: this install's keys and certificate (mode 0600);
//! - `<secrets>/link/root.json`: the fleet root, sealed under a passphrase (Argon2id), only when the
//!   operator chose to keep it here (otherwise the recovery phrase re-derives it on demand);
//! - `<secrets>/link/certified.json`: the devices our root has certified (self-monitoring).
//!
//! The daemon holds keys and parses untrusted bytes. It has no Redis credentials and no shell,
//! and never touches the bus: admitted records leave only as `events.wait` results.
//!
//! Each link is behind its own lock (`Held`, `LinkCell`); the map of links is locked only to find
//! or add one. Sessions and RPCs on one link run one at a time, and never wait for another link's,
//! except where a call reads every link (`link.list`, `events.wait`): it takes each link's lock in
//! turn, so it waits at most for the frame or call in progress on each. Waiting for a link's lock
//! and the work under it run off the async workers (`LinkCell::with`), so a busy link holds up no
//! worker, and with it no other link, timer or the RPC socket. `peer_links`, which the inbound
//! gates and the dialer read, takes no link's lock: each link keeps a copy of who may sync on it,
//! refreshed after every change (review finding R9-3).

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};

use anyhow::{Context, bail};
use aurora_link::acl::{self, Policy, Role};
use aurora_link::codec::{self, hex, now};
use aurora_link::crypto;
use aurora_link::ed25519_dalek;
use aurora_link::engine::{Acted, Admit, Link, Offered};
use aurora_link::identity::{self, Device, DeviceCert, fleet_fingerprint, grouped, safety_number};
use aurora_link::invite::InviteCode;
use aurora_link::record::{Body, Record};
use serde_json::{Value, json};
use tokio::sync::{Notify, broadcast};

use crate::rpc::{Params, RpcError};

/// What a session pushes to its peer outside the request/response flow.
#[derive(Clone, Debug)]
pub enum Push {
    Records(Vec<Record>),
    /// New chain entries (a contiguous run).
    Acl(Vec<acl::Entry>),
    /// A proposal on its way to the sequencer.
    Proposal(acl::Proposal),
    /// A sequencer's refusal on its way back to the proposer.
    Refusal(acl::ProposalRefusal),
}

#[derive(Clone, Debug)]
pub struct Dirs {
    pub home: PathBuf,
    pub state: PathBuf,
    pub secrets: PathBuf,
}

impl Dirs {
    pub fn new(home: &Path, secrets: Option<&Path>) -> Self {
        let state = home.join("state").join("link");
        let secrets = secrets
            .map(Path::to_path_buf)
            .unwrap_or_else(|| home.join(".secrets"))
            .join("link");
        Self {
            home: home.to_owned(),
            state,
            secrets,
        }
    }
    pub fn device_file(&self) -> PathBuf {
        self.secrets.join("device.json")
    }
    pub fn root_file(&self) -> PathBuf {
        self.secrets.join("root.json")
    }
    pub fn certified_file(&self) -> PathBuf {
        self.secrets.join("certified.json")
    }
    pub fn peers_file(&self) -> PathBuf {
        self.state.join("peers.json")
    }
    pub fn blobs(&self) -> PathBuf {
        self.state.join("blobs")
    }
    /// Where clients find the RPC endpoint: a file holding the socket path (or pipe name).
    pub fn addr_file(&self) -> PathBuf {
        self.state.join("linkd.addr")
    }
    /// The RPC socket: in a private folder beside the store when the path is short enough for
    /// AF_UNIX (about 108 bytes), otherwise in the runtime or temp directory under a name derived
    /// from the home. Either way its folder is ours alone (`private_socket_dir`).
    pub fn socket(&self) -> PathBuf {
        let near = self.state.join("rpc").join("linkd.sock");
        if near.as_os_str().len() <= 100 {
            return near;
        }
        let tag = &aurora_link::codec::hex(&crypto::sha256(&[self.home.to_string_lossy().as_bytes()]))[..16];
        // Never a bare file in a shared directory: a private folder (mode 0700, see
        // `private_socket_dir`) so another local user cannot squat the name.
        let base = std::env::var_os("XDG_RUNTIME_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir);
        base.join(format!("aurora-linkd-{}", user_tag()))
            .join(format!("{tag}.sock"))
    }
    pub fn refusals_log(&self) -> PathBuf {
        self.home.join("state").join("logs").join("linkd-refusals.log")
    }
}

/// The member a person named: an exact root first, then exactly one live member whose label or
/// root prefix matches. Never "the first match": labels are chosen by the members themselves.
pub fn member_root(l: &Link, key: &str) -> Result<String, RpcError> {
    let s = l.state();
    let members = &s.members;
    if members.contains_key(key) {
        return Ok(key.to_owned());
    }
    // Labels are unique among live members (the chain refuses a second one).
    let hits: Vec<&String> = members
        .values()
        .filter(|m| !m.removed && (m.label == key || (key.len() >= 8 && m.root.starts_with(key))))
        .map(|m| &m.root)
        .collect();
    match hits.as_slice() {
        [one] => Ok((*one).clone()),
        [] => Err(RpcError::refused(format!("no member {key:?}"))),
        _ => Err(RpcError::refused(format!(
            "{key:?} names more than one member; use the root"
        ))),
    }
}

/// Create a folder for secrets as ours alone (mode 0700), tightening one we already own.
pub fn private_dir(dir: &Path) -> anyhow::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
        if !dir.exists() {
            std::fs::DirBuilder::new().recursive(true).mode(0o700).create(dir)?;
        }
        let meta = std::fs::symlink_metadata(dir)?;
        if !meta.is_dir() || meta.uid() != user_tag().parse::<u32>().unwrap_or(u32::MAX) {
            bail!(
                "{} is not a folder of this user; refusing to keep secrets there",
                dir.display()
            );
        }
        if meta.permissions().mode() & 0o077 != 0 {
            std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o700))?;
        }
    }
    #[cfg(not(unix))]
    std::fs::create_dir_all(dir)?;
    Ok(())
}

/// Write a secret file readable by its owner only: into a fresh, randomly named file that must
/// not exist yet (so a planted file or symlink is never opened, let alone followed), mode 0600
/// set explicitly whatever the umask, then renamed over the target.
pub fn write_secret(path: &Path, data: &[u8]) -> anyhow::Result<()> {
    use std::io::Write;
    let dir = path
        .parent()
        .filter(|d| !d.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    private_dir(dir)?;
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();
    let tmp = dir.join(format!(".{name}.{}.tmp", hex(&crypto::random_bytes(8))));
    let mut opts = std::fs::OpenOptions::new();
    opts.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    let written = (|| -> anyhow::Result<()> {
        let mut f = opts.open(&tmp)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            f.set_permissions(std::fs::Permissions::from_mode(0o600))?;
        }
        f.write_all(data)?;
        f.sync_all()?;
        std::fs::rename(&tmp, path)?;
        Ok(())
    })();
    if written.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    written
}

/// The refusal log is capped: past this size it is rotated to `<name>.1` (one old file kept).
pub const REFUSALS_LOG_MAX: u64 = 1024 * 1024;

/// Append one line to a log, rotating it first when the line would take it past `cap`.
pub fn append_capped(path: &Path, line: &str, cap: u64) -> std::io::Result<()> {
    use std::io::Write;
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let len = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);
    if len > 0 && len + line.len() as u64 > cap {
        let mut old = path.as_os_str().to_owned();
        old.push(".1");
        std::fs::rename(path, PathBuf::from(old))?;
    }
    std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?
        .write_all(line.as_bytes())
}

/// A per-user tag for the private socket folder.
fn user_tag() -> String {
    #[cfg(unix)]
    {
        // SAFETY: getuid has no preconditions and cannot fail.
        unsafe extern "C" {
            fn getuid() -> u32;
        }
        unsafe { getuid() }.to_string()
    }
    #[cfg(not(unix))]
    {
        std::env::var("USERNAME").unwrap_or_else(|_| "user".into())
    }
}

/// Create the socket's folder as ours alone (mode 0700), refusing one that someone else owns or
/// can enter. Our own folder with a looser mode (an older layout) is tightened.
#[cfg(unix)]
pub fn private_socket_dir(socket: &Path) -> anyhow::Result<()> {
    use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
    let Some(dir) = socket.parent() else { return Ok(()) };
    if !dir.exists() {
        std::fs::DirBuilder::new().recursive(true).mode(0o700).create(dir)?;
    }
    let meta = std::fs::symlink_metadata(dir)?;
    let mine = user_tag().parse::<u32>().unwrap_or(u32::MAX);
    if meta.is_dir() && meta.uid() == mine && meta.permissions().mode() & 0o077 != 0 {
        std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o700))?;
    }
    let meta = std::fs::symlink_metadata(dir)?;
    if !meta.is_dir() || meta.uid() != mine || meta.permissions().mode() & 0o077 != 0 {
        bail!(
            "{} is not a private folder of this user; refusing to serve RPC there",
            dir.display()
        );
    }
    Ok(())
}

/// One link this daemon holds, behind its own lock: work on one link never waits for another's
/// (round 8). The name is kept beside it, so resolving a link by name takes no link's lock.
pub struct Held {
    pub name: String,
    pub link: LinkCell,
}

impl Held {
    fn new(link: Link) -> Self {
        Self {
            name: link.name().to_owned(),
            link: LinkCell::new(link),
        }
    }
}

/// The devices that may sync on a link: by its state (narrowed while halted), and by its held
/// state (`sync::may_sync`, `sync::may_sync_acl`).
type SyncSets = (Arc<BTreeSet<String>>, Arc<BTreeSet<String>>);

/// One link behind its lock, with a copy of who may sync on it that is read without the lock.
///
/// A body runs off the async workers (review finding R9-3): the link's lock is a std `Mutex`, and
/// sessions of one busy link that wait for it each held a tokio worker, so once they outnumbered
/// the workers every other link's sessions, the RPC socket and the timers waited too. Within a
/// multi-threaded runtime the wait and the body run in `block_in_place`, which hands the worker's
/// other tasks to another thread first.
#[derive(Clone)]
pub struct LinkCell {
    link: Arc<Mutex<Link>>,
    /// The link's `SyncSets`, refreshed after every body that moved them: what `peer_links` (the
    /// inbound gates and the dialer) reads, without waiting for any link's lock (R9-3).
    sync: Arc<RwLock<SyncSets>>,
}

impl LinkCell {
    fn new(link: Link) -> Self {
        let sync = (link.acl.sync_devices(), link.acl.held_sync_devices());
        Self {
            link: Arc::new(Mutex::new(link)),
            sync: Arc::new(RwLock::new(sync)),
        }
    }

    /// Run `f` on the link under its lock, off the async workers.
    pub fn with<T>(&self, f: impl FnOnce(&mut Link) -> T) -> T {
        off_worker(|| {
            let mut link = self.link.lock().expect("link lock");
            let out = f(&mut link);
            let (view, held) = (link.acl.sync_devices(), link.acl.held_sync_devices());
            let same = {
                let s = self.sync.read().expect("sync lock");
                Arc::ptr_eq(&s.0, &view) && Arc::ptr_eq(&s.1, &held)
            };
            if !same {
                *self.sync.write().expect("sync lock") = (view, held);
            }
            out
        })
    }

    /// Who may sync on this link, as of the last body that ran on it: no link lock is taken.
    pub fn sync_sets(&self) -> SyncSets {
        self.sync.read().expect("sync lock").clone()
    }
}

/// Run `f`, which may block on a link's lock, without holding up the tokio worker it was called
/// on (review finding R9-3). Outside a multi-threaded runtime (tests, one-shot commands) it just
/// runs.
fn off_worker<T>(f: impl FnOnce() -> T) -> T {
    match tokio::runtime::Handle::try_current() {
        Ok(h) if h.runtime_flavor() == tokio::runtime::RuntimeFlavor::MultiThread => tokio::task::block_in_place(f),
        _ => f(),
    }
}

pub struct Daemon {
    pub dirs: Dirs,
    pub mailbox: bool,
    pub device: RwLock<Option<Arc<Device>>>,
    /// The links, by id. The map's lock is held only to find or add a link, and never while a
    /// link's own lock is awaited; no code holds two links' locks at once.
    pub links: Mutex<BTreeMap<String, Held>>,
    pub events: Notify,
    pushes: Mutex<BTreeMap<String, broadcast::Sender<Push>>>,
    /// Wakes the dialer (a new peer hint, a gossip advert, `sync.now`).
    pub wake: Notify,
    /// Set with a wake that should also forget every dial backoff (`sync.now`, a join), not just
    /// cut a sleep short (a gossip advert).
    pub reset_backoff: std::sync::atomic::AtomicBool,
    /// Serialises appends to (and rotation of) the refusal log.
    refusals: Mutex<()>,
    pub started: u64,
}

pub type Shared = Arc<Daemon>;

impl Daemon {
    pub fn open(dirs: Dirs, mailbox: bool) -> anyhow::Result<Shared> {
        std::fs::create_dir_all(&dirs.state)?;
        let device = match std::fs::read(dirs.device_file()) {
            Ok(raw) => Some(Arc::new(Device::from_json(&raw).context("device.json is unreadable")?)),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
            Err(e) => return Err(e.into()),
        };
        let mut links = BTreeMap::new();
        for entry in std::fs::read_dir(&dirs.state)? {
            let path = entry?.path();
            if path.extension().is_some_and(|e| e == "db") {
                match Link::open(&path) {
                    Ok(link) => {
                        links.insert(link.id().to_owned(), Held::new(link));
                    }
                    Err(e) => tracing::warn!("skipping {}: {e}", path.display()),
                }
            }
        }
        Ok(Arc::new(Self {
            dirs,
            mailbox,
            device: RwLock::new(device),
            links: Mutex::new(links),
            events: Notify::new(),
            pushes: Mutex::new(BTreeMap::new()),
            wake: Notify::new(),
            reset_backoff: std::sync::atomic::AtomicBool::new(false),
            refusals: Mutex::new(()),
            started: now(),
        }))
    }

    pub fn device(&self) -> Result<Arc<Device>, RpcError> {
        if let Some(d) = self.device.read().expect("device lock").clone() {
            return Ok(d);
        }
        // Another process (a one-shot `aurora link init`) may have created the identity since
        // this daemon started: pick it up rather than run without a network for ever.
        if let Ok(raw) = std::fs::read(self.dirs.device_file())
            && let Ok(d) = Device::from_json(&raw)
        {
            let d = Arc::new(d);
            *self.device.write().expect("device lock") = Some(d.clone());
            return Ok(d);
        }
        Err(RpcError::unavailable(
            "no fleet identity on this install yet: run `aurora link init`",
        ))
    }

    pub fn pushes(&self, link: &str) -> broadcast::Sender<Push> {
        self.pushes
            .lock()
            .expect("push lock")
            .entry(link.to_owned())
            .or_insert_with(|| broadcast::channel(256).0)
            .clone()
    }

    pub fn push(&self, link: &str, p: Push) {
        let _ = self.pushes(link).send(p);
    }

    /// Resolve a link by id, unique id prefix (8+ characters) or unique name.
    pub fn resolve(&self, links: &BTreeMap<String, Held>, key: &str) -> Result<String, RpcError> {
        if links.contains_key(key) {
            return Ok(key.to_owned());
        }
        let hits: Vec<&String> = links
            .iter()
            .filter(|(id, h)| h.name == key || (key.len() >= 8 && id.starts_with(key)))
            .map(|(id, _)| id)
            .collect();
        match hits.as_slice() {
            [one] => Ok((*one).clone()),
            [] => Err(RpcError::unavailable(format!("no link called {key:?}"))),
            _ => Err(RpcError::invalid(format!(
                "{key:?} names more than one link; use its id"
            ))),
        }
    }

    /// Run `f` on one link under its own lock (the map's lock is released first), off the async
    /// workers (`LinkCell::with`).
    pub fn with_link<T>(&self, key: &str, f: impl FnOnce(&mut Link) -> Result<T, RpcError>) -> Result<T, RpcError> {
        let cell = {
            let links = self.links.lock().expect("links lock");
            let id = self.resolve(&links, key)?;
            links[&id].link.clone()
        };
        cell.with(f)
    }

    /// Every link we hold, by id, without holding the map's lock while each is used.
    pub fn held_links(&self) -> Vec<(String, LinkCell)> {
        self.links
            .lock()
            .expect("links lock")
            .iter()
            .map(|(id, h)| (id.clone(), h.link.clone()))
            .collect()
    }

    /// The ids of the links we hold.
    pub fn link_ids(&self) -> Vec<String> {
        self.links.lock().expect("links lock").keys().cloned().collect()
    }

    /// Hold `link` (tests that build a link by hand).
    #[cfg(test)]
    pub fn hold(&self, link: Link) {
        self.links
            .lock()
            .expect("links lock")
            .insert(link.id().to_owned(), Held::new(link));
    }

    fn certified(&self) -> BTreeSet<String> {
        std::fs::read(self.dirs.certified_file())
            .ok()
            .and_then(|raw| serde_json::from_slice(&raw).ok())
            .unwrap_or_default()
    }

    fn add_certified(&self, device: &str) -> anyhow::Result<()> {
        let mut set = self.certified();
        set.insert(device.to_owned());
        write_secret(&self.dirs.certified_file(), &serde_json::to_vec_pretty(&set)?)
    }

    /// Wake the dialer and forget every dial backoff (an operator asked, or a join just landed).
    pub fn wake_now(&self) {
        self.reset_backoff.store(true, std::sync::atomic::Ordering::Relaxed);
        self.wake.notify_waiters();
    }

    /// After the ACL of a link changed (or a membership action was taken): upkeep (the
    /// sequencer includes what it holds), self-monitoring, and a push to peers: the new chain
    /// entries since `before`, and our own new proposals. The push reaches every live session of
    /// the link, and each one re-checks its peer's membership before it sends anything: a removed
    /// device's session closes there.
    pub fn after_acl_change(&self, link: &mut Link, before: &acl::AclPos) -> Result<(), RpcError> {
        let device = self.device()?;
        let t = now();
        for acted in link.upkeep(&device, t)? {
            if let Acted::Proposed(p) = acted {
                self.push(link.id(), Push::Proposal(p));
            }
        }
        link.self_monitor(&device.id_hex(), device.root_hex(), &self.certified(), t)?;
        let fresh = acl_since(link, before);
        if !fresh.is_empty() {
            self.push(link.id(), Push::Acl(fresh));
        }
        Ok(())
    }

    /// A membership action's result for the RPC caller, after pushing it to peers.
    fn acted(&self, link: &mut Link, acted: &Acted, before: &acl::AclPos) -> Result<Value, RpcError> {
        if let Acted::Proposed(p) = acted {
            self.push(link.id(), Push::Proposal(p.clone()));
        }
        self.after_acl_change(link, before)?;
        let s = link.state();
        let (sequencer, _) = s.next_sequencer();
        Ok(match acted {
            Acted::Entry(e) => json!({"entry": e.hash()?, "epoch": s.epoch, "rotation_due": s.rotation_due}),
            Acted::Proposed(p) => json!({
                "proposal": p.id()?, "queued": true, "sequencer": sequencer, "epoch": s.epoch,
                "rotation_due": s.rotation_due,
            }),
        })
    }

    // ------------------------------------------------------------------------------- identity

    fn root_from(&self, p: &Params) -> Result<Option<ed25519_dalek::SigningKey>, RpcError> {
        if let Some(phrase) = p.opt_str("phrase")? {
            return Ok(Some(identity::root_from_phrase(&phrase)?));
        }
        let passphrase = p
            .opt_str("passphrase")?
            .or_else(|| std::env::var("AURORA_LINK_PASSPHRASE").ok());
        match (std::fs::read(self.dirs.root_file()), passphrase) {
            (Ok(sealed), Some(pass)) => Ok(Some(identity::open_root(&sealed, &pass)?)),
            _ => Ok(None),
        }
    }

    pub fn identity_init(&self, p: &Params) -> Result<Value, RpcError> {
        if self.device.read().expect("device lock").is_some() && !p.opt_bool("force")?.unwrap_or(false) {
            return Err(RpcError::refused("this install already has a device identity"));
        }
        let (phrase, generated) = match p.opt_str("phrase")? {
            Some(ph) => (ph, false),
            None => (identity::new_phrase(), true),
        };
        let root = identity::root_from_phrase(&phrase)?;
        let label = p.opt_str("label")?.unwrap_or_else(|| "aurora".into());
        let device = Device::create(&root, &label, p.opt_bool("xwing")?.unwrap_or(true), now())?;
        write_secret(&self.dirs.device_file(), &device.to_json()?).map_err(RpcError::internal)?;
        self.add_certified(&device.id_hex()).map_err(RpcError::internal)?;
        let mut root_stored = false;
        if let Some(pass) = p.opt_str("passphrase")? {
            let sealed = identity::seal_root(&root, &pass)?;
            write_secret(&self.dirs.root_file(), &sealed).map_err(RpcError::internal)?;
            root_stored = true;
        }
        let out = json!({
            "device": device.id_hex(), "root": device.root_hex(), "label": label,
            "fingerprint": grouped(&fleet_fingerprint(&crypto::public_of(&root))),
            "root_stored": root_stored, "cert_expires": device.cert.not_after,
            "phrase": if generated { Value::String(phrase) } else { Value::Null },
        });
        *self.device.write().expect("device lock") = Some(Arc::new(device));
        Ok(out)
    }

    pub fn identity_status(&self) -> Result<Value, RpcError> {
        let Some(d) = self.device.read().expect("device lock").clone() else {
            return Ok(json!({"initialized": false}));
        };
        let t = now();
        let root = codec::unhex::<32>(d.root_hex())?;
        Ok(json!({
            "initialized": true, "device": d.id_hex(), "root": d.root_hex(), "label": d.cert.label,
            "fingerprint": grouped(&fleet_fingerprint(&root)), "cert_expires": d.cert.not_after,
            "cert_valid": d.cert.valid_at(t), "needs_renewal": d.needs_renewal(t),
            "xwing": d.cert.xwing.is_some(), "root_stored": self.dirs.root_file().exists(),
            "cert": d.cert, "mailbox": self.mailbox,
        }))
    }

    /// Renew this device's certificate (needs the root: phrase, or root.json plus passphrase),
    /// then announce the renewal in every link.
    pub fn identity_renew(&self, p: &Params) -> Result<Value, RpcError> {
        let root = self.root_from(p)?.ok_or_else(|| {
            RpcError::unavailable("renewal needs the root: give the phrase, or the passphrase for root.json")
        })?;
        let mut device = Device::from_json(&self.device()?.to_json()?)?;
        let t = now();
        device.renew(&root, t)?;
        write_secret(&self.dirs.device_file(), &device.to_json()?).map_err(RpcError::internal)?;
        let device = Arc::new(device);
        *self.device.write().expect("device lock") = Some(device.clone());
        let mut renewed = Vec::new();
        for (_, cell) in self.held_links() {
            cell.with(|link| {
                if link.state().active_device(&device.id_hex()).is_some() {
                    let before = link.acl.tip();
                    let acted = link.add_device(&device, device.cert.clone(), t)?;
                    self.acted(link, &acted, &before)?;
                    renewed.push(link.id().to_owned());
                }
                Ok::<_, RpcError>(())
            })?;
        }
        Ok(json!({"cert_expires": device.cert.not_after, "links": renewed}))
    }

    /// Certify another device of this fleet (a second machine) from its public certificate
    /// request; the new machine ran `identity.init` with the same phrase.
    pub fn identity_certified(&self, p: &Params) -> Result<Value, RpcError> {
        let cert: DeviceCert = p.parse("cert")?;
        cert.verify()?;
        if cert.root != self.device()?.root_hex() {
            return Err(RpcError::refused("that certificate is under another fleet's root"));
        }
        self.add_certified(&cert.device).map_err(RpcError::internal)?;
        Ok(json!({"device": cert.device}))
    }

    // ---------------------------------------------------------------------------------- links

    pub fn link_create(&self, p: &Params) -> Result<Value, RpcError> {
        let device = self.device()?;
        let name = p.str("name")?;
        let mut policy = Policy::default();
        if let Some(kinds) = p.opt::<Vec<String>>("kinds")? {
            policy.kinds = kinds;
        }
        if let Some(days) = p.opt::<u64>("retention_days")? {
            policy.retention_days = days;
        }
        let mut links = self.links.lock().expect("links lock");
        if links.values().any(|h| h.name == name) {
            return Err(RpcError::refused(format!("a link called {name:?} already exists here")));
        }
        let label = p.opt_str("label")?.unwrap_or_else(|| device.cert.label.clone());
        let link = Link::create(Some(&self.dirs.state), &device, &name, &label, policy, now())?;
        let id = link.id().to_owned();
        links.insert(id.clone(), Held::new(link));
        let root = codec::unhex::<32>(device.root_hex())?;
        Ok(json!({"link": id, "name": name, "fingerprint": grouped(&fleet_fingerprint(&root))}))
    }

    pub fn link_list(&self) -> Result<Value, RpcError> {
        let me = self
            .device
            .read()
            .expect("device lock")
            .as_ref()
            .map(|d| d.id_hex())
            .unwrap_or_default();
        Ok(Value::Array(
            self.held_links()
                .into_iter()
                .map(|(_, cell)| {
                    cell.with(|l| {
                        let s = l.state();
                        json!({
                            "link": l.id(), "name": l.name(), "epoch": s.epoch,
                            "role": s.active_device(&me).map(|(m, _)| m.role.as_str()),
                            "members": s.members.values().filter(|m| !m.removed).count(),
                            "alarms": l.store.alarms().map(|a| a.len()).unwrap_or(0),
                            "last_cursor": l.store.last_cursor().unwrap_or(0),
                        })
                    })
                })
                .collect(),
        ))
    }

    pub fn link_status(&self, p: &Params) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(&p.str("link")?, |l| Ok(l.status(&device, now())?))
    }

    /// Publish an invite and return the code. `addrs` and `relay` are dial hints for the joiner.
    pub fn link_invite(&self, p: &Params, relay: Option<String>, addrs: Vec<String>) -> Result<Value, RpcError> {
        let device = self.device()?;
        let role = Role::parse(&p.opt_str("role")?.unwrap_or_else(|| "writer".into()))?;
        let ttl = p.opt::<u64>("ttl_s")?.unwrap_or(acl::DEFAULT_INVITE_TTL_S);
        let single_use = p.opt_bool("single_use")?.unwrap_or(true);
        let approval = p.opt_bool("approval")?.unwrap_or(false);
        let root = codec::unhex::<32>(device.root_hex())?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.tip();
            let t = now();
            let ticket = l.invite(&device, role, ttl, single_use, approval, t)?;
            let queued = !l.state().invites.contains_key(&ticket.entry);
            if queued && let Some(q) = l.store.proposals("queued")?.into_iter().find(|q| q.id == ticket.entry) {
                self.push(l.id(), Push::Proposal(q.proposal));
            }
            self.after_acl_change(l, &before)?;
            let code = InviteCode {
                v: 1,
                link: l.id().to_owned(),
                name: l.name().to_owned(),
                secret: hex(&ticket.secret),
                invite: ticket.entry.clone(),
                node: device.id_hex(),
                relay: relay.clone(),
                addrs: addrs.clone(),
                fingerprint: fleet_fingerprint(&root),
            };
            Ok(json!({
                "code": code.encode()?, "link": l.id(), "role": role.as_str(), "approval": approval,
                "expires": t + ttl.clamp(60, acl::MAX_INVITE_TTL_S),
                "fingerprint": grouped(&fleet_fingerprint(&root)),
                "invite": ticket.entry, "invite_key": ticket.key(), "queued": queued,
                "acl": l.acl.all(),
            }))
        })
    }

    /// The offline half of a join: given the inviter's chain, sign our join proposal. The
    /// network join (net.rs) calls this with entries it fetched.
    pub fn join_with(
        &self,
        code: &InviteCode,
        entries: Vec<acl::Entry>,
        label: &str,
    ) -> Result<(acl::Proposal, String), RpcError> {
        let device = self.device()?;
        // The chain must be the link the code names, and the invite in it published by the fleet
        // whose fingerprint the code carries; otherwise nothing is signed or sent.
        let (proposal, _inviter) = aurora_link::sync::join_proposal_for(&entries, &device, code, label, now())?;
        Ok((proposal, code.link.clone()))
    }

    /// What a joiner shows before its join is included: both fingerprints and the safety number,
    /// from the inviter's chain alone.
    pub fn pending_join_summary(&self, code: &InviteCode, entries: &[acl::Entry]) -> Result<Value, RpcError> {
        let device = self.device()?;
        let chain = aurora_link::sync::chain_of(entries)?;
        let mine = codec::unhex::<32>(device.root_hex())?;
        let inviter = codec::unhex::<32>(&code.inviter(chain.state())?)?;
        Ok(json!({
            "link": chain.link_id(), "name": chain.state().name,
            "our_fingerprint": grouped(&fleet_fingerprint(&mine)),
            "their_fingerprint": grouped(&code.fingerprint),
            "inviter_root": hex(&inviter), "owner_root": chain.state().owner,
            "safety_number": grouped(&safety_number(&mine, &inviter)),
            "fingerprint_matches_code": fleet_fingerprint(&inviter) == code.fingerprint,
            "pending": true, "has_key": false,
        }))
    }

    pub fn adopt(&self, entries: Vec<acl::Entry>) -> Result<String, RpcError> {
        let device = self.device()?;
        let mut links = self.links.lock().expect("links lock");
        let genesis = entries
            .iter()
            .find(|e| e.seq == 0)
            .ok_or_else(|| RpcError::refused("no genesis"))?;
        let id = genesis.hash()?;
        if let Some(cell) = links.get(&id).map(|h| h.link.clone()) {
            drop(links);
            return cell.with(|link| {
                let before = link.acl.tip();
                link.add_acl(entries, now())?;
                self.after_acl_change(link, &before)?;
                Ok(id)
            });
        }
        let mut link = Link::adopt(Some(&self.dirs.state), entries, now())?;
        if !link.state().devices.contains_key(&device.id_hex()) {
            let path = link.path.clone();
            drop(link);
            if let Some(path) = path {
                let _ = std::fs::remove_file(path);
            }
            return Err(RpcError::refused("this device is not in that link's log"));
        }
        let before = acl::AclPos {
            term: 0,
            seq: 0,
            hash: String::new(),
        };
        self.after_acl_change(&mut link, &before)?;
        links.insert(id.clone(), Held::new(link));
        Ok(id)
    }

    pub fn joined_summary(&self, id: &str, code: &InviteCode) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(id, |l| {
            let mine = codec::unhex::<32>(device.root_hex())?;
            let s = l.state();
            // The fleet that published the invite (an admin, not necessarily the owner) is the
            // one whose fingerprint the code carries and whose safety number the person compares.
            let inviter = codec::unhex::<32>(&code.inviter(s)?)?;
            let member = s.members.get(device.root_hex());
            Ok(json!({
                "link": l.id(), "name": l.name(),
                "our_fingerprint": grouped(&fleet_fingerprint(&mine)),
                "their_fingerprint": grouped(&code.fingerprint),
                "inviter_root": hex(&inviter), "owner_root": s.owner,
                "safety_number": grouped(&safety_number(&mine, &inviter)),
                "fingerprint_matches_code": fleet_fingerprint(&inviter) == code.fingerprint,
                "pending": member.is_none_or(|m| m.pending),
                "has_key": l.read_key(&device, s.epoch).is_ok(),
            }))
        })
    }

    pub fn link_accept(&self, p: &Params, decline: bool) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.tip();
            let join = p.str("join")?;
            let s = l.state();
            let join = s
                .pending_joins
                .keys()
                .find(|j| j.starts_with(&join))
                .cloned()
                .ok_or_else(|| RpcError::refused("no such pending join"))?;
            let acted = if decline {
                l.decline(&device, &join, now())?
            } else {
                l.accept(&device, &join, now())?
            };
            self.acted(l, &acted, &before)
        })
    }

    pub fn link_verify(&self, p: &Params) -> Result<Value, RpcError> {
        let device = self.device()?;
        let mine = codec::unhex::<32>(device.root_hex())?;
        let mark = p.opt_bool("mark")?.unwrap_or(false);
        let only = p.opt_str("member")?;
        self.with_link(&p.str("link")?, |l| {
            let mut out = Vec::new();
            let roots: Vec<String> = l
                .state()
                .members
                .values()
                .filter(|m| !m.removed && m.root != device.root_hex())
                .map(|m| m.root.clone())
                .collect();
            for root in roots {
                if only
                    .as_ref()
                    .is_some_and(|o| !root.starts_with(o.as_str()) && l.state().label_of(&root) != *o)
                {
                    continue;
                }
                let theirs = codec::unhex::<32>(&root)?;
                let sn = safety_number(&mine, &theirs);
                if mark {
                    l.store.mark_verified(&root, &sn, now())?;
                }
                out.push(
                    json!({"member": root, "label": l.state().label_of(&root), "safety_number": grouped(&sn),
                                "verified": l.store.verified(&root)?.is_some_and(|v| v == sn)}),
                );
            }
            Ok(Value::Array(out))
        })
    }

    pub fn link_membership(&self, p: &Params, what: &str) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.tip();
            let t = now();
            let member = |l: &Link, key: &str| member_root(l, key);
            let e = match what {
                "remove_member" => {
                    let root = member(l, &p.str("member")?)?;
                    l.remove_member(&device, &root, t)?
                }
                "leave" => {
                    let root = device.root_hex().to_owned();
                    l.remove_member(&device, &root, t)?
                }
                "remove_device" => {
                    let key = p.str("device")?;
                    let dev = l
                        .state()
                        .devices
                        .keys()
                        .find(|d| d.starts_with(&key))
                        .cloned()
                        .ok_or_else(|| RpcError::refused("no such device"))?;
                    l.remove_device(&device, &dev, t)?
                }
                "rotate_key" => l.rotate_key(&device, t)?,
                "revoke_invite" => {
                    let key = p.str("invite")?;
                    let inv = l
                        .state()
                        .invites
                        .keys()
                        .find(|i| i.starts_with(&key))
                        .cloned()
                        .ok_or_else(|| RpcError::refused("no such invite"))?;
                    l.revoke_invite(&device, &inv, t)?
                }
                "set_role" => {
                    let root = member(l, &p.str("member")?)?;
                    l.set_role(&device, &root, Role::parse(&p.str("role")?)?, t)?
                }
                "add_device" => {
                    let cert: DeviceCert = p.parse("cert")?;
                    cert.verify()?;
                    if cert.root == device.root_hex() {
                        self.add_certified(&cert.device).map_err(RpcError::internal)?;
                    }
                    l.add_device(&device, cert, t)?
                }
                "handoff" => {
                    let key = p.str("device")?;
                    let to = l
                        .state()
                        .devices
                        .keys()
                        .find(|d| d.starts_with(&key))
                        .cloned()
                        .ok_or_else(|| RpcError::refused("no such device"))?;
                    l.handoff(&device, &to, t)?
                }
                other => return Err(RpcError::invalid(format!("unknown membership op {other}"))),
            };
            self.acted(l, &e, &before)
        })
    }

    /// The owner's takeover: with the fleet root (the recovery phrase, or root.json and its
    /// passphrase), this device sequences a new term after entry `after` (default: the last entry
    /// this replica holds; required while halted below it, see `AclChain::takeover`). Later
    /// entries of older terms are dropped on every replica.
    pub fn link_takeover(&self, p: &Params) -> Result<Value, RpcError> {
        let root = self.root_from(p)?.ok_or_else(|| {
            RpcError::unavailable("a takeover needs the fleet root: give the phrase, or the passphrase for root.json")
        })?;
        let device = self.device()?;
        let after = p.opt::<u64>("after")?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.tip();
            let e = l.takeover(&device, &root, after, now())?;
            self.after_acl_change(l, &before)?;
            Ok(json!({"entry": e.hash()?, "term": e.term, "seq": e.seq, "sequencer": device.id_hex()}))
        })
    }

    // ------------------------------------------------------------------------------- records

    /// Write one record. Idempotent by `source` (the bus message id the exporter sends).
    pub fn link_send(&self, link: &str, body: Body, source: Option<&str>) -> Result<Value, RpcError> {
        let device = self.device()?;
        let (id, r) = self.with_link(link, |l| {
            if let Some(src) = source
                && let Some(existing) = l.store.exported(src)?
            {
                return Ok((existing, None));
            }
            let t = now();
            let (id, r) = l.write(&device, &body, t)?;
            if let Some(src) = source {
                l.store.export(src, &id, t)?;
            }
            Ok((id, Some((l.id().to_owned(), r))))
        })?;
        let fresh = r.is_some();
        if let Some((link_id, r)) = r {
            self.push(&link_id, Push::Records(vec![r]));
        }
        Ok(json!({"record_id": id, "new": fresh}))
    }

    pub fn link_read(&self, p: &Params) -> Result<Value, RpcError> {
        let device = self.device()?;
        let ids: Vec<String> = p.parse("record_ids")?;
        let (ack, link_id, rec) = self.with_link(&p.str("link")?, |l| {
            let ack = l.ack(&device, ids, now())?;
            let rec = match &ack {
                Some(id) => l.store.get(id)?.map(|s| s.record),
                None => None,
            };
            Ok((ack, l.id().to_owned(), rec))
        })?;
        if let Some(r) = rec {
            self.push(&link_id, Push::Records(vec![r]));
        }
        Ok(json!({"ack": ack}))
    }

    pub fn record_get(&self, p: &Params) -> Result<Value, RpcError> {
        let rid = p.str("record_id")?;
        self.with_link(&p.str("link")?, |l| {
            let sr = l.store.get(&rid)?.ok_or_else(|| RpcError::unavailable("no such record"))?;
            let s = l.state();
            let fleet_root = s.devices.get(&sr.record.author).map(|d| d.member.clone()).unwrap_or_default();
            Ok(json!({
                "record_id": rid, "status": sr.status, "reason": sr.reason, "received_at": sr.received_at,
                "device": sr.record.author, "seq": sr.record.seq, "epoch": sr.record.epoch,
                "fleet_root": fleet_root, "fleet": s.members.get(&fleet_root).map(|_| s.label_of(&fleet_root)),
                "body": sr.body.as_deref().map(serde_json::from_str::<Value>).transpose().map_err(|e| RpcError::internal(e.into()))?,
                "promoted": l.store.promoted(&rid)?.map(|(seat, by, bus, at)| json!({"seat": seat, "by": by, "bus_id": bus, "at": at})),
            }))
        })
    }

    /// Admitted records past each link's cursor (all links when `cursors` names none).
    pub fn events_after(&self, cursors: &BTreeMap<String, i64>, limit: u32) -> Result<Vec<Value>, RpcError> {
        let mut out = Vec::new();
        for (id, cell) in self.held_links() {
            let c = cursors.get(&id).copied().unwrap_or(0);
            out.extend(cell.with(|l| l.events_after(c, limit))?);
        }
        Ok(out)
    }

    pub fn promotion_record(&self, p: &Params) -> Result<Value, RpcError> {
        let rid = p.str("record_id")?;
        self.with_link(&p.str("link")?, |l| {
            let sr = l
                .store
                .get(&rid)?
                .ok_or_else(|| RpcError::unavailable("no such record"))?;
            if sr.status != aurora_link::store::ADMITTED {
                return Err(RpcError::refused(format!("record is {}, not admitted", sr.status)));
            }
            let first = l.store.promote(
                &rid,
                &p.str("seat")?,
                &p.str("by")?,
                &p.opt_str("bus_id")?.unwrap_or_default(),
                now(),
            )?;
            Ok(json!({"first": first}))
        })
    }

    /// Records received from peers through any path: verify, admit, notify.
    pub fn take_records(&self, link: &mut Link, records: Vec<Record>, peer: &str) -> Result<Vec<Admit>, RpcError> {
        let device = self.device()?;
        let t = now();
        let mut out = Vec::new();
        let mut stored = Vec::new();
        for r in records {
            let a = link.receive(&device, &r, t)?;
            if let Admit::Stored { .. } = &a {
                stored.push(r);
            }
            if let Admit::Refused(why) = &a {
                link.store.refusal(peer, why, t)?;
            }
            out.push(a);
        }
        if !stored.is_empty() {
            self.push(link.id(), Push::Records(stored));
            self.events.notify_waiters();
        }
        Ok(out)
    }

    /// A bundle for sneakernet: the whole log and every record this device holds.
    pub fn bundle_export(&self, p: &Params) -> Result<Value, RpcError> {
        let with_records = p.opt_bool("records")?.unwrap_or(true);
        self.with_link(&p.str("link")?, |l| {
            let records = if with_records {
                l.missing_for(&BTreeMap::new(), usize::MAX)?
            } else {
                vec![]
            };
            let proposals: Vec<acl::Proposal> = l.outstanding(usize::MAX)?;
            Ok(
                json!({"v": 2, "kind": "aurora-link-bundle", "link": l.id(), "acl": l.acl.all(), "records": records,
                      "proposals": proposals}),
            )
        })
    }

    pub fn bundle_import(&self, p: &Params) -> Result<Value, RpcError> {
        let bundle: Value = p.parse("bundle")?;
        let entries: Vec<acl::Entry> = serde_json::from_value(bundle.get("acl").cloned().unwrap_or(json!([])))
            .map_err(|e| RpcError::invalid(format!("bundle acl: {e}")))?;
        let records: Vec<Record> = serde_json::from_value(bundle.get("records").cloned().unwrap_or(json!([])))
            .map_err(|e| RpcError::invalid(format!("bundle records: {e}")))?;
        let proposals: Vec<acl::Proposal> =
            serde_json::from_value(bundle.get("proposals").cloned().unwrap_or(json!([])))
                .map_err(|e| RpcError::invalid(format!("bundle proposals: {e}")))?;
        let id = self.adopt(entries)?;
        let device = self.device()?;
        let cell = self.links.lock().expect("links lock")[&id].link.clone();
        cell.with(|link| self.take_bundle(link, &id, &device, proposals, records))
    }

    /// The rest of `bundle_import`, on the adopted link under its lock.
    fn take_bundle(
        &self,
        link: &mut Link,
        id: &str,
        device: &Device,
        proposals: Vec<acl::Proposal>,
        records: Vec<Record>,
    ) -> Result<Value, RpcError> {
        // Proposals in a bundle (an offline join, or queued changes): the sequencer includes
        // them; anyone else keeps them to relay.
        let before = link.acl.tip();
        let mut included = 0;
        for p in &proposals {
            if let Ok(Offered::Included(_)) = link.offer(device, p, now()) {
                included += 1;
            }
        }
        if included > 0 {
            self.after_acl_change(link, &before)?;
        }
        let mut sorted = records;
        sorted.sort_by_key(|r| r.seq);
        let admits = self.take_records(link, sorted, "bundle")?;
        let stored = admits.iter().filter(|a| matches!(a, Admit::Stored { .. })).count();
        let refused = admits.iter().filter(|a| matches!(a, Admit::Refused(_))).count();
        Ok(
            json!({"link": id, "acl_entries": link.acl.prefix_len(), "records_stored": stored, "records_refused": refused,
                  "proposals_included": included}),
        )
    }

    /// Retention, and certificate renewal when the root is at hand. Run hourly by `serve`.
    pub fn housekeeping(&self) -> Result<Value, RpcError> {
        let t = now();
        let mut retired = 0;
        for (_, cell) in self.held_links() {
            retired += cell.with(|l| l.retire(t))?;
        }
        let mut renewed = false;
        if let Ok(d) = self.device()
            && d.needs_renewal(t)
            && let Ok(Some(_)) = self.root_from(&Params::empty())
        {
            renewed = self.identity_renew(&Params::empty()).is_ok();
        }
        Ok(json!({"retired": retired, "renewed": renewed}))
    }

    /// Every device of every link we sync with, and which links each one shares with us: the
    /// transport's view (dialing, the inbound gates, gossip). While a link is halted this reads
    /// its held state, not the narrowed one (review finding R7-2): a device added past the halt's
    /// prefix, this one included, must still reach and be reached by the owner's takeover. What a
    /// session then grants is the sync protocol's own check (`sync::may_sync`, narrowed).
    pub fn peer_links(&self) -> BTreeMap<String, Vec<String>> {
        self.links_by(true)
    }

    /// `peer_links` as the narrowed state of a halted link says: who may fetch record data such
    /// as blobs.
    pub fn record_peer_links(&self) -> BTreeMap<String, Vec<String>> {
        self.links_by(false)
    }

    fn links_by(&self, held: bool) -> BTreeMap<String, Vec<String>> {
        let me = self
            .device
            .read()
            .expect("device lock")
            .as_ref()
            .map(|d| d.id_hex())
            .unwrap_or_default();
        let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
        // Each link's kept copy of who may sync: no link's lock is taken, so the inbound gates
        // and the dialer never wait for a busy link (review finding R9-3).
        for (id, cell) in self.held_links() {
            let (view, held_sets) = cell.sync_sets();
            let s = if held { held_sets } else { view };
            if !s.contains(&me) {
                continue;
            }
            for d in s.iter() {
                if *d != me {
                    out.entry(d.clone()).or_default().push(id.clone());
                }
            }
        }
        out
    }

    pub fn is_member_anywhere(&self, device: &str) -> bool {
        self.peer_links().contains_key(device)
    }

    pub fn log_refusal(&self, device: &str, alpn: &str, why: &str) {
        // One line per refusal whatever the peer put in it: no newlines from the wire.
        let why: String = why
            .chars()
            .take(300)
            .map(|c| if c.is_control() { ' ' } else { c })
            .collect();
        let line = format!("{} {} {} {}\n", now(), device, alpn, why);
        {
            let _one = self.refusals.lock().expect("refusals lock");
            let _ = append_capped(&self.dirs.refusals_log(), &line, REFUSALS_LOG_MAX);
        }
        tracing::info!("refused {device} on {alpn}: {why}");
    }
}

/// The chain entries a link holds after `before`: from the first entry that differs, when a
/// takeover replaced part of the chain since (the peer drops what it replaces).
pub fn acl_since(link: &Link, before: &acl::AclPos) -> Vec<acl::Entry> {
    if before.hash.is_empty() {
        return link.acl.all();
    }
    let mut from = before.seq.min(link.acl.prefix_len().saturating_sub(1) as u64);
    while from > 0
        && link.acl.hash_at(from) != Some(before.hash.as_str())
        && link.acl.entry(from).is_some_and(|e| e.term > before.term)
    {
        from -= 1;
    }
    link.acl.range(from, u64::MAX, usize::MAX)
}

/// Parse a JSON body into the record body type, strictly.
pub fn body_from(v: &Value) -> Result<Body, RpcError> {
    let b: Body = serde_json::from_value(v.clone()).map_err(|e| RpcError::invalid(format!("body: {e}")))?;
    Ok(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("linkd-daemon-{tag}-{}", hex(&crypto::random_bytes(6))));
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[cfg(unix)]
    #[test]
    fn a_secret_is_written_0600_in_a_0700_folder_and_never_through_a_planted_link() {
        use std::os::unix::fs::PermissionsExt;
        let base = scratch("secret");
        let dir = base.join("secrets").join("link");
        let target = dir.join("device.json");
        std::fs::create_dir_all(&dir).unwrap();
        // The old temp name was predictable: plant a symlink there pointing elsewhere.
        let elsewhere = base.join("elsewhere");
        std::fs::write(&elsewhere, b"untouched").unwrap();
        std::os::unix::fs::symlink(&elsewhere, dir.join("device.tmp")).unwrap();
        write_secret(&target, b"{\"secret\": 1}").unwrap();
        assert_eq!(
            std::fs::read(&elsewhere).unwrap(),
            b"untouched",
            "the planted link was followed"
        );
        assert_eq!(std::fs::read(&target).unwrap(), b"{\"secret\": 1}");
        let mode = |p: &Path| std::fs::metadata(p).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode(&target), 0o600);
        assert_eq!(mode(&dir), 0o700);
        let left: Vec<_> = std::fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
            .filter(|n| n.ends_with(".tmp") && n != "device.tmp")
            .collect();
        assert!(left.is_empty(), "temp files left behind: {left:?}");
        let _ = std::fs::remove_dir_all(base);
    }

    #[cfg(unix)]
    #[test]
    fn the_rpc_socket_is_bound_inside_a_private_folder() {
        use std::os::unix::fs::PermissionsExt;
        let base = scratch("sock");
        let dirs = Dirs::new(&base, None);
        std::fs::create_dir_all(&dirs.state).unwrap();
        let sock = dirs.socket();
        private_socket_dir(&sock).unwrap();
        let folder = sock.parent().unwrap();
        assert_ne!(folder, dirs.state.as_path(), "the socket shares the store's folder");
        assert_eq!(std::fs::metadata(folder).unwrap().permissions().mode() & 0o777, 0o700);
        let _ = std::fs::remove_dir_all(base);
    }

    #[test]
    fn the_refusal_log_is_capped_and_keeps_one_rotated_file() {
        let base = scratch("refusals");
        let log = base.join("logs").join("linkd-refusals.log");
        let line = format!("{}\n", "x".repeat(99));
        for _ in 0..100 {
            append_capped(&log, &line, 1000).unwrap();
        }
        assert!(std::fs::metadata(&log).unwrap().len() <= 1000);
        let rotated = base.join("logs").join("linkd-refusals.log.1");
        assert!(std::fs::metadata(&rotated).unwrap().len() <= 1000);
        assert_eq!(std::fs::read_dir(base.join("logs")).unwrap().count(), 2);
        let _ = std::fs::remove_dir_all(base);
    }
}
