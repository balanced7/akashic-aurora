//! The daemon's state and every RPC method that needs no network.
//!
//! Layout under the Aurora data root (`--home`):
//!
//! - `state/link/<link_id>.db`: one SQLite store per link (aurora-link's `Store`);
//! - `state/link/blobs/`: the iroh-blobs store (encrypted attachments only);
//! - `state/link/linkd.sock`: the RPC socket while `serve` runs (a named pipe on Windows);
//! - `<secrets>/link/device.json`: this install's keys and certificate (mode 0600);
//! - `<secrets>/link/root.json`: the fleet root, age-encrypted with a passphrase, only when the
//!   operator chose to keep it here (otherwise the recovery phrase re-derives it on demand);
//! - `<secrets>/link/certified.json`: the devices our root has certified (self-monitoring).
//!
//! The daemon holds keys and parses untrusted bytes. It has no Redis credentials and no shell,
//! and never touches the bus: admitted records leave only as `events.wait` results.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};

use anyhow::Context;
use aurora_link::acl::{self, Policy, Role};
use aurora_link::codec::{self, hex, now};
use aurora_link::crypto;
use aurora_link::ed25519_dalek;
use aurora_link::engine::{Admit, Link};
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
    Acl(Vec<acl::Entry>),
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
    /// The RPC socket: beside the store when the path is short enough for AF_UNIX (about 108
    /// bytes), otherwise in the runtime or temp directory under a name derived from the home.
    pub fn socket(&self) -> PathBuf {
        let near = self.state.join("linkd.sock");
        if near.as_os_str().len() <= 100 {
            return near;
        }
        let tag = &aurora_link::codec::hex(&crypto::sha256(&[self.home.to_string_lossy().as_bytes()]))[..16];
        let dir = std::env::var_os("XDG_RUNTIME_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir);
        dir.join(format!("aurora-linkd-{tag}.sock"))
    }
    pub fn refusals_log(&self) -> PathBuf {
        self.home.join("state").join("logs").join("linkd-refusals.log")
    }
}

/// Write a secret file readable by its owner only.
pub fn write_secret(path: &Path, data: &[u8]) -> anyhow::Result<()> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let tmp = path.with_extension("tmp");
    #[cfg(unix)]
    {
        use std::io::Write;
        use std::os::unix::fs::OpenOptionsExt;
        let mut f = std::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(0o600)
            .open(&tmp)?;
        f.write_all(data)?;
        f.sync_all()?;
    }
    #[cfg(not(unix))]
    std::fs::write(&tmp, data)?;
    std::fs::rename(&tmp, path)?;
    Ok(())
}

pub struct Daemon {
    pub dirs: Dirs,
    pub mailbox: bool,
    pub device: RwLock<Option<Arc<Device>>>,
    pub links: Mutex<BTreeMap<String, Link>>,
    pub events: Notify,
    pushes: Mutex<BTreeMap<String, broadcast::Sender<Push>>>,
    /// Wakes the dialer (a new peer hint, a gossip advert, `sync.now`).
    pub wake: Notify,
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
                        links.insert(link.id().to_owned(), link);
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
            started: now(),
        }))
    }

    pub fn device(&self) -> Result<Arc<Device>, RpcError> {
        self.device
            .read()
            .expect("device lock")
            .clone()
            .ok_or_else(|| RpcError::unavailable("no fleet identity on this install yet: run `aurora link init`"))
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
    pub fn resolve(&self, links: &BTreeMap<String, Link>, key: &str) -> Result<String, RpcError> {
        if links.contains_key(key) {
            return Ok(key.to_owned());
        }
        let hits: Vec<&String> = links
            .iter()
            .filter(|(id, l)| l.name() == key || (key.len() >= 8 && id.starts_with(key)))
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

    /// Run `f` on one link under the lock.
    pub fn with_link<T>(&self, key: &str, f: impl FnOnce(&mut Link) -> Result<T, RpcError>) -> Result<T, RpcError> {
        let mut links = self.links.lock().expect("links lock");
        let id = self.resolve(&links, key)?;
        f(links.get_mut(&id).expect("resolved"))
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

    /// After the ACL of a link changed: an admin's upkeep, self-monitoring, and a push to peers.
    pub fn after_acl_change(&self, link: &mut Link, before: &BTreeSet<String>) -> Result<(), RpcError> {
        let device = self.device()?;
        let t = now();
        link.upkeep(&device, t)?;
        link.self_monitor(device.root_hex(), &self.certified(), t)?;
        let fresh = link.acl.missing_for(before);
        if !fresh.is_empty() {
            self.push(link.id(), Push::Acl(fresh));
        }
        Ok(())
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
        let mut links = self.links.lock().expect("links lock");
        for link in links.values_mut() {
            if link.state().active_device(&device.id_hex()).is_some() {
                let before = link.acl.hashes();
                let op = acl::Op::AddDevice(acl::AddDevice {
                    cert: device.cert.clone(),
                    wraps: vec![],
                });
                link.append(&device, op, t)?;
                self.after_acl_change(link, &before)?;
                renewed.push(link.id().to_owned());
            }
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
        if links.values().any(|l| l.name() == name) {
            return Err(RpcError::refused(format!("a link called {name:?} already exists here")));
        }
        let label = p.opt_str("label")?.unwrap_or_else(|| device.cert.label.clone());
        let link = Link::create(Some(&self.dirs.state), &device, &name, &label, policy, now())?;
        let id = link.id().to_owned();
        links.insert(id.clone(), link);
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
        let links = self.links.lock().expect("links lock");
        Ok(Value::Array(
            links
                .values()
                .map(|l| {
                    let s = l.state();
                    json!({
                        "link": l.id(), "name": l.name(), "epoch": s.epoch,
                        "role": s.active_device(&me).map(|(m, _)| m.role.as_str()),
                        "members": s.members.values().filter(|m| !m.removed).count(),
                        "alarms": l.store.alarms().map(|a| a.len()).unwrap_or(0),
                        "last_cursor": l.store.last_cursor().unwrap_or(0),
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
            let before = l.acl.hashes();
            let t = now();
            let secret = l.invite(&device, role, ttl, single_use, approval, t)?;
            self.after_acl_change(l, &before)?;
            let code = InviteCode {
                v: 1,
                link: l.id().to_owned(),
                name: l.name().to_owned(),
                secret: hex(&secret),
                node: device.id_hex(),
                relay: relay.clone(),
                addrs: addrs.clone(),
                fingerprint: fleet_fingerprint(&root),
            };
            Ok(json!({
                "code": code.encode()?, "link": l.id(), "role": role.as_str(), "approval": approval,
                "expires": t + ttl.clamp(60, acl::MAX_INVITE_TTL_S),
                "fingerprint": grouped(&fleet_fingerprint(&root)),
                "invite": hex(&crypto::public_of(&acl::invite_key(&secret))),
                "acl": l.acl.missing_for(&BTreeSet::new()),
            }))
        })
    }

    /// The offline half of a join: given the inviter's log, write our join entry and adopt the
    /// link locally. The network join (net.rs) calls this with entries it fetched.
    pub fn join_with(
        &self,
        code: &InviteCode,
        entries: Vec<acl::Entry>,
        label: &str,
    ) -> Result<(acl::Entry, String), RpcError> {
        let device = self.device()?;
        let entry = aurora_link::sync::join_entry(&entries, &device, &code.secret_bytes()?, label, now())?;
        Ok((entry, code.link.clone()))
    }

    pub fn adopt(&self, entries: Vec<acl::Entry>) -> Result<String, RpcError> {
        let device = self.device()?;
        let mut links = self.links.lock().expect("links lock");
        let genesis = entries
            .iter()
            .find(|e| e.seq == 0)
            .ok_or_else(|| RpcError::refused("no genesis"))?;
        let id = genesis.hash()?;
        if let Some(link) = links.get_mut(&id) {
            let before = link.acl.hashes();
            link.add_acl(entries, now())?;
            self.after_acl_change(link, &before)?;
            return Ok(id);
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
        let before = BTreeSet::new();
        self.after_acl_change(&mut link, &before)?;
        links.insert(id.clone(), link);
        Ok(id)
    }

    pub fn joined_summary(&self, id: &str, code: &InviteCode) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(id, |l| {
            let mine = codec::unhex::<32>(device.root_hex())?;
            let s = l.state();
            let owner = codec::unhex::<32>(&s.owner)?;
            let member = s.members.get(device.root_hex());
            Ok(json!({
                "link": l.id(), "name": l.name(),
                "our_fingerprint": grouped(&fleet_fingerprint(&mine)),
                "their_fingerprint": grouped(&code.fingerprint),
                "safety_number": grouped(&safety_number(&mine, &owner)),
                "fingerprint_matches_code": fleet_fingerprint(&owner) == code.fingerprint,
                "pending": member.is_none_or(|m| m.pending),
                "has_key": l.read_key(&device, s.epoch).is_ok(),
            }))
        })
    }

    pub fn link_accept(&self, p: &Params, decline: bool) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.hashes();
            let join = p.str("join")?;
            let s = l.state();
            let join = s
                .pending_joins
                .keys()
                .find(|j| j.starts_with(&join))
                .cloned()
                .ok_or_else(|| RpcError::refused("no such pending join"))?;
            let e = if decline {
                l.decline(&device, &join, now())?
            } else {
                l.accept(&device, &join, now())?
            };
            self.after_acl_change(l, &before)?;
            Ok(json!({"entry": e.hash()?}))
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
                let m = &l.state().members[&root];
                if only
                    .as_ref()
                    .is_some_and(|o| !root.starts_with(o.as_str()) && m.label != *o)
                {
                    continue;
                }
                let theirs = codec::unhex::<32>(&root)?;
                let sn = safety_number(&mine, &theirs);
                if mark {
                    l.store.mark_verified(&root, &sn, now())?;
                }
                out.push(json!({"member": root, "label": m.label, "safety_number": grouped(&sn),
                                "verified": l.store.verified(&root)?.is_some_and(|v| v == sn)}));
            }
            Ok(Value::Array(out))
        })
    }

    pub fn link_membership(&self, p: &Params, what: &str) -> Result<Value, RpcError> {
        let device = self.device()?;
        self.with_link(&p.str("link")?, |l| {
            let before = l.acl.hashes();
            let t = now();
            let member = |l: &Link, key: &str| -> Result<String, RpcError> {
                l.state()
                    .members
                    .values()
                    .find(|m| m.root == key || m.label == key || (key.len() >= 8 && m.root.starts_with(key)))
                    .map(|m| m.root.clone())
                    .ok_or_else(|| RpcError::refused(format!("no member {key:?}")))
            };
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
                    let s = l.state().clone();
                    let reads = s.members.get(&cert.root).is_some_and(|m| m.role.reads());
                    let wraps = if reads {
                        let mut tmp = s.clone();
                        tmp.devices.insert(
                            cert.device.clone(),
                            acl::DeviceState {
                                cert: cert.clone(),
                                member: cert.root.clone(),
                                cut: None,
                            },
                        );
                        tmp.make_wraps(&l.read_key(&device, s.epoch)?.0, s.epoch, &[cert.device.clone()].into())?
                    } else {
                        vec![]
                    };
                    if cert.root == device.root_hex() {
                        self.add_certified(&cert.device).map_err(RpcError::internal)?;
                    }
                    l.append(&device, acl::Op::AddDevice(acl::AddDevice { cert, wraps }), t)?
                }
                other => return Err(RpcError::invalid(format!("unknown membership op {other}"))),
            };
            self.after_acl_change(l, &before)?;
            Ok(json!({"entry": e.hash()?, "epoch": l.state().epoch, "rotation_due": l.state().rotation_due}))
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
                "fleet_root": fleet_root, "fleet": s.members.get(&fleet_root).map(|m| m.label.clone()),
                "body": sr.body.as_deref().map(serde_json::from_str::<Value>).transpose().map_err(|e| RpcError::internal(e.into()))?,
                "promoted": l.store.promoted(&rid)?.map(|(seat, by, bus, at)| json!({"seat": seat, "by": by, "bus_id": bus, "at": at})),
            }))
        })
    }

    /// Admitted records past each link's cursor (all links when `cursors` names none).
    pub fn events_after(&self, cursors: &BTreeMap<String, i64>, limit: u32) -> Result<Vec<Value>, RpcError> {
        let links = self.links.lock().expect("links lock");
        let mut out = Vec::new();
        for (id, l) in links.iter() {
            let c = cursors.get(id).copied().unwrap_or(0);
            out.extend(l.events_after(c, limit)?);
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
            let records = if with_records { l.missing_for(&BTreeMap::new(), usize::MAX)? } else { vec![] };
            Ok(json!({"v": 1, "kind": "aurora-link-bundle", "link": l.id(), "acl": l.acl.missing_for(&BTreeSet::new()), "records": records}))
        })
    }

    pub fn bundle_import(&self, p: &Params) -> Result<Value, RpcError> {
        let bundle: Value = p.parse("bundle")?;
        let entries: Vec<acl::Entry> = serde_json::from_value(bundle.get("acl").cloned().unwrap_or(json!([])))
            .map_err(|e| RpcError::invalid(format!("bundle acl: {e}")))?;
        let records: Vec<Record> = serde_json::from_value(bundle.get("records").cloned().unwrap_or(json!([])))
            .map_err(|e| RpcError::invalid(format!("bundle records: {e}")))?;
        let id = self.adopt(entries)?;
        let mut links = self.links.lock().expect("links lock");
        let link = links.get_mut(&id).expect("adopted");
        let mut sorted = records;
        sorted.sort_by_key(|r| r.seq);
        let admits = self.take_records(link, sorted, "bundle")?;
        let stored = admits.iter().filter(|a| matches!(a, Admit::Stored { .. })).count();
        let refused = admits.iter().filter(|a| matches!(a, Admit::Refused(_))).count();
        Ok(json!({"link": id, "acl_entries": link.acl.len(), "records_stored": stored, "records_refused": refused}))
    }

    /// Retention, and certificate renewal when the root is at hand. Run hourly by `serve`.
    pub fn housekeeping(&self) -> Result<Value, RpcError> {
        let t = now();
        let mut retired = 0;
        {
            let links = self.links.lock().expect("links lock");
            for l in links.values() {
                retired += l.retire(t)?;
            }
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

    /// Every device of every link we sync with, and which links each one shares with us.
    pub fn peer_links(&self) -> BTreeMap<String, Vec<String>> {
        let me = self
            .device
            .read()
            .expect("device lock")
            .as_ref()
            .map(|d| d.id_hex())
            .unwrap_or_default();
        let links = self.links.lock().expect("links lock");
        let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for (id, l) in links.iter() {
            if l.state().active_device(&me).is_none() {
                continue;
            }
            for d in l.state().sync_devices() {
                if d != me {
                    out.entry(d).or_default().push(id.clone());
                }
            }
        }
        out
    }

    pub fn is_member_anywhere(&self, device: &str) -> bool {
        self.peer_links().contains_key(device)
    }

    pub fn log_refusal(&self, device: &str, alpn: &str, why: &str) {
        let line = format!("{} {} {} {}\n", now(), device, alpn, why);
        let path = self.dirs.refusals_log();
        if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        let _ = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .and_then(|mut f| {
                use std::io::Write;
                f.write_all(line.as_bytes())
            });
        tracing::info!("refused {device} on {alpn}: {why}");
    }
}

/// Parse a JSON body into the record body type, strictly.
pub fn body_from(v: &Value) -> Result<Body, RpcError> {
    let b: Body = serde_json::from_value(v.clone()).map_err(|e| RpcError::invalid(format!("body: {e}")))?;
    Ok(b)
}
