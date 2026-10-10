//! The local JSON-RPC 2.0 channel: one request per line, one response per line.
//!
//! It runs over stdio when `ManagedChild` spawns the daemon (`serve --stdio`), and over a Unix
//! socket (a named pipe on Windows) for the CLI while `serve` runs. The method table below is the
//! contract: `aurora-linkd openrpc` prints it as an OpenRPC document, `openrpc.json` is the
//! checked-in copy, and `core/link/rpc_types.py` is generated from it.

use std::collections::BTreeMap;
use std::sync::Arc;

use aurora_link::LinkError;
use aurora_link::codec::now;
use serde::de::DeserializeOwned;
use serde_json::{Value, json};
use tokio::io::{AsyncBufReadExt, AsyncRead, AsyncWrite, AsyncWriteExt, BufReader};

use crate::daemon::{self, Shared};
use crate::net::Net;

pub const MAX_LINE: usize = 8 * 1024 * 1024;

#[derive(Debug)]
pub struct RpcError {
    pub code: i64,
    pub message: String,
}

impl RpcError {
    pub fn invalid(m: impl Into<String>) -> Self {
        Self {
            code: -32602,
            message: m.into(),
        }
    }
    pub fn refused(m: impl Into<String>) -> Self {
        Self {
            code: -32001,
            message: m.into(),
        }
    }
    pub fn unavailable(m: impl Into<String>) -> Self {
        Self {
            code: -32002,
            message: m.into(),
        }
    }
    pub fn internal(e: anyhow::Error) -> Self {
        Self {
            code: -32003,
            message: format!("{e:#}"),
        }
    }
}

impl From<LinkError> for RpcError {
    fn from(e: LinkError) -> Self {
        match e {
            LinkError::Refused(m) => Self::refused(m),
            LinkError::Unavailable(m) => Self::unavailable(m),
            other => Self {
                code: -32003,
                message: other.to_string(),
            },
        }
    }
}

/// Typed access to a request's `params` object.
pub struct Params(serde_json::Map<String, Value>);

impl Params {
    pub fn new(v: Value) -> Result<Self, RpcError> {
        match v {
            Value::Object(m) => Ok(Self(m)),
            Value::Null => Ok(Self(Default::default())),
            _ => Err(RpcError::invalid("params must be an object")),
        }
    }
    pub fn empty() -> Self {
        Self(Default::default())
    }
    pub fn opt<T: DeserializeOwned>(&self, k: &str) -> Result<Option<T>, RpcError> {
        match self.0.get(k) {
            None | Some(Value::Null) => Ok(None),
            Some(v) => serde_json::from_value(v.clone())
                .map(Some)
                .map_err(|e| RpcError::invalid(format!("{k}: {e}"))),
        }
    }
    pub fn parse<T: DeserializeOwned>(&self, k: &str) -> Result<T, RpcError> {
        self.opt(k)?
            .ok_or_else(|| RpcError::invalid(format!("missing parameter {k}")))
    }
    pub fn str(&self, k: &str) -> Result<String, RpcError> {
        self.parse(k)
    }
    pub fn opt_str(&self, k: &str) -> Result<Option<String>, RpcError> {
        self.opt(k)
    }
    pub fn opt_bool(&self, k: &str) -> Result<Option<bool>, RpcError> {
        self.opt(k)
    }
}

/// One RPC method: name, summary, parameters (name, JSON type, required) and whether it needs
/// the network (an offline one-shot daemon refuses those).
pub struct Method {
    pub name: &'static str,
    pub summary: &'static str,
    pub params: &'static [(&'static str, &'static str, bool)],
    pub network: bool,
}

pub const METHODS: &[Method] = &[
    Method {
        name: "rpc.discover",
        summary: "This contract as an OpenRPC document.",
        params: &[],
        network: false,
    },
    Method {
        name: "daemon.status",
        summary: "Version, mode, uptime and network state.",
        params: &[],
        network: false,
    },
    Method {
        name: "daemon.shutdown",
        summary: "Stop the daemon cleanly (exit code 0, not restarted).",
        params: &[],
        network: false,
    },
    Method {
        name: "identity.init",
        summary: "Create this install's device under a fleet root. Without a phrase, a new 24-word phrase is made and returned once.",
        params: &[
            ("phrase", "string", false),
            ("label", "string", false),
            ("passphrase", "string", false),
            ("xwing", "boolean", false),
            ("force", "boolean", false),
        ],
        network: false,
    },
    Method {
        name: "identity.status",
        summary: "This install's device, root fingerprint and certificate.",
        params: &[],
        network: false,
    },
    Method {
        name: "identity.renew",
        summary: "Renew the device certificate (needs the phrase, or the passphrase for root.age) and announce it in every link.",
        params: &[("phrase", "string", false), ("passphrase", "string", false)],
        network: false,
    },
    Method {
        name: "identity.certify",
        summary: "Record a certificate of another device of this fleet as ours (self-monitoring).",
        params: &[("cert", "object", true)],
        network: false,
    },
    Method {
        name: "link.create",
        summary: "Create a link owned by this fleet.",
        params: &[
            ("name", "string", true),
            ("label", "string", false),
            ("kinds", "array", false),
            ("retention_days", "integer", false),
        ],
        network: false,
    },
    Method {
        name: "link.list",
        summary: "Links this install holds.",
        params: &[],
        network: false,
    },
    Method {
        name: "link.status",
        summary: "Members, devices, heads, receipts, invites and alarms of one link.",
        params: &[("link", "string", true)],
        network: false,
    },
    Method {
        name: "link.invite",
        summary: "Publish an invite and return its code. The code also carries the bundle-free dial hints.",
        params: &[
            ("link", "string", true),
            ("role", "string", false),
            ("ttl_s", "integer", false),
            ("single_use", "boolean", false),
            ("approval", "boolean", false),
        ],
        network: false,
    },
    Method {
        name: "link.join",
        summary: "Join with an invite code. With `acl` (the inviter's log from a bundle) it works offline and returns our join entry as a bundle; without, it dials the inviter.",
        params: &[
            ("code", "string", true),
            ("label", "string", false),
            ("acl", "array", false),
        ],
        network: false,
    },
    Method {
        name: "link.accept",
        summary: "Admit a pending join (wraps the read key to it).",
        params: &[("link", "string", true), ("join", "string", true)],
        network: false,
    },
    Method {
        name: "link.decline",
        summary: "Refuse a pending join.",
        params: &[("link", "string", true), ("join", "string", true)],
        network: false,
    },
    Method {
        name: "link.verify",
        summary: "Safety numbers for each member; with mark=true, record that they were compared.",
        params: &[
            ("link", "string", true),
            ("member", "string", false),
            ("mark", "boolean", false),
        ],
        network: false,
    },
    Method {
        name: "link.remove_member",
        summary: "Remove a fleet and rotate the read key.",
        params: &[("link", "string", true), ("member", "string", true)],
        network: false,
    },
    Method {
        name: "link.leave",
        summary: "Leave a link (an admin's daemon then rotates the key).",
        params: &[("link", "string", true)],
        network: false,
    },
    Method {
        name: "link.remove_device",
        summary: "Remove one device and rotate the read key.",
        params: &[("link", "string", true), ("device", "string", true)],
        network: false,
    },
    Method {
        name: "link.add_device",
        summary: "Add another device of a member, from its certificate.",
        params: &[("link", "string", true), ("cert", "object", true)],
        network: false,
    },
    Method {
        name: "link.rotate_key",
        summary: "Start a new read-key epoch.",
        params: &[("link", "string", true)],
        network: false,
    },
    Method {
        name: "link.revoke_invite",
        summary: "Kill an unused invite.",
        params: &[("link", "string", true), ("invite", "string", true)],
        network: false,
    },
    Method {
        name: "link.set_role",
        summary: "Change a member's role (owner > admin > writer > reader > mailbox).",
        params: &[
            ("link", "string", true),
            ("member", "string", true),
            ("role", "string", true),
        ],
        network: false,
    },
    Method {
        name: "link.send",
        summary: "Write one record. `source` makes it idempotent (the exporter passes the bus message id). Attachments become encrypted blobs.",
        params: &[
            ("link", "string", true),
            ("body", "object", true),
            ("source", "string", false),
            ("attachments", "array", false),
        ],
        network: false,
    },
    Method {
        name: "link.read",
        summary: "Send read receipts for records a seat has read.",
        params: &[("link", "string", true), ("record_ids", "array", true)],
        network: false,
    },
    Method {
        name: "record.get",
        summary: "One stored record with its body and provenance.",
        params: &[("link", "string", true), ("record_id", "string", true)],
        network: false,
    },
    Method {
        name: "events.wait",
        summary: "Admitted records after the given per-link cursors; waits up to timeout_ms for the first one.",
        params: &[
            ("cursors", "object", false),
            ("timeout_ms", "integer", false),
            ("limit", "integer", false),
        ],
        network: false,
    },
    Method {
        name: "promotion.record",
        summary: "Record that a person or rule promoted a record onto the bus. Returns first=false when it already was.",
        params: &[
            ("link", "string", true),
            ("record_id", "string", true),
            ("seat", "string", true),
            ("by", "string", true),
            ("bus_id", "string", false),
        ],
        network: false,
    },
    Method {
        name: "bundle.export",
        summary: "The whole log and records of a link, for sneakernet.",
        params: &[("link", "string", true), ("records", "boolean", false)],
        network: false,
    },
    Method {
        name: "bundle.import",
        summary: "Merge a bundle: every entry and record is verified as if it came over the wire.",
        params: &[("bundle", "object", true)],
        network: false,
    },
    Method {
        name: "blob.get",
        summary: "Fetch (if needed), verify and decrypt one attachment of a record into a file.",
        params: &[
            ("link", "string", true),
            ("record_id", "string", true),
            ("blob", "string", true),
            ("out", "string", true),
        ],
        network: false,
    },
    Method {
        name: "peers.add",
        summary: "Remember dial hints (direct addresses, a relay URL) for a device.",
        params: &[
            ("device", "string", true),
            ("addrs", "array", false),
            ("relay", "string", false),
        ],
        network: false,
    },
    Method {
        name: "net.status",
        summary: "Our endpoint id, addresses, relay and live sessions.",
        params: &[],
        network: true,
    },
    Method {
        name: "sync.now",
        summary: "Dial every member of a link (or all links) now.",
        params: &[("link", "string", false)],
        network: true,
    },
    Method {
        name: "housekeeping",
        summary: "Run retention and certificate renewal now.",
        params: &[],
        network: false,
    },
];

pub fn openrpc() -> Value {
    let methods: Vec<Value> = METHODS
        .iter()
        .map(|m| {
            let params: Vec<Value> = m
                .params
                .iter()
                .map(|(n, t, req)| json!({"name": n, "required": req, "schema": {"type": t}}))
                .collect();
            json!({"name": m.name, "summary": m.summary, "params": params, "paramStructure": "by-name",
                   "result": {"name": "result", "schema": {}}, "x-network": m.network})
        })
        .collect();
    json!({
        "openrpc": "1.3.2",
        "info": {"title": "aurora-linkd", "version": env!("CARGO_PKG_VERSION"),
                 "description": "The local channel between Aurora's Python side and its fleet-link daemon."},
        "methods": methods,
    })
}

/// Everything a method may use.
pub struct Ctx {
    pub d: Shared,
    /// Set once the network is up (after an identity exists, and never in offline mode).
    pub net_cell: Arc<std::sync::OnceLock<Arc<Net>>>,
    pub offline: bool,
    pub shutdown: tokio::sync::watch::Sender<bool>,
}

impl Ctx {
    pub fn net(&self) -> Option<&Arc<Net>> {
        self.net_cell.get()
    }
}

/// Log every request and response line (`serve --trace-rpc`).
pub static TRACE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

pub async fn dispatch(ctx: &Ctx, method: &str, params: Value) -> Result<Value, RpcError> {
    let spec = METHODS.iter().find(|m| m.name == method).ok_or(RpcError {
        code: -32601,
        message: format!("no method {method}"),
    })?;
    let p = Params::new(params)?;
    for (name, _, required) in spec.params {
        if *required && p.0.get(*name).is_none_or(Value::is_null) {
            return Err(RpcError::invalid(format!("missing parameter {name}")));
        }
    }
    if let Some(unknown) = p.0.keys().find(|k| !spec.params.iter().any(|(n, _, _)| n == k)) {
        return Err(RpcError::invalid(format!("unknown parameter {unknown}")));
    }
    let wants_net = spec.network || (method == "link.join" && p.0.get("acl").is_none_or(Value::is_null));
    if wants_net && !ctx.offline {
        // The endpoint comes up a moment after start (or after identity.init); wait for it.
        for _ in 0..100 {
            if ctx.net().is_some() || ctx.d.device().is_err() {
                break;
            }
            tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        }
    }
    if spec.network && ctx.net().is_none() {
        return Err(RpcError::unavailable(
            "this needs the network: start `aurora link serve`",
        ));
    }
    let d = &ctx.d;
    match method {
        "rpc.discover" => Ok(openrpc()),
        "daemon.status" => Ok(json!({
            "version": env!("CARGO_PKG_VERSION"), "pid": std::process::id(), "started": d.started,
            "uptime_s": now().saturating_sub(d.started), "mailbox": d.mailbox, "offline": ctx.offline,
            "network": ctx.net().is_some(), "home": d.dirs.home, "links": d.links.lock().expect("links").len(),
            "recent_refusals": crate::net::recent_refusals(&d.dirs, 10),
        })),
        "daemon.shutdown" => {
            let _ = ctx.shutdown.send(true);
            Ok(json!({"stopping": true}))
        }
        "identity.init" => d.identity_init(&p),
        "identity.status" => d.identity_status(),
        "identity.renew" => d.identity_renew(&p),
        "identity.certify" => d.identity_certified(&p),
        "link.create" => d.link_create(&p),
        "link.list" => d.link_list(),
        "link.status" => {
            let mut v = d.link_status(&p)?;
            if let Some(net) = ctx.net() {
                v["live_sessions"] = json!(net.live_peers(v["link"].as_str().unwrap_or_default()));
            }
            Ok(v)
        }
        "link.invite" => {
            let (relay, addrs) = match ctx.net() {
                Some(net) => net.hints(),
                None => (None, vec![]),
            };
            d.link_invite(&p, relay, addrs)
        }
        "link.join" => {
            let code = aurora_link::invite::InviteCode::parse(&p.str("code")?)?;
            let label = p.opt_str("label")?.unwrap_or_else(|| "fleet".into());
            match p.opt::<Vec<aurora_link::acl::Entry>>("acl")? {
                Some(entries) => {
                    let (entry, _) = d.join_with(&code, entries.clone(), &label)?;
                    let mut all = entries;
                    all.push(entry);
                    let id = d.adopt(all.clone())?;
                    let mut summary = d.joined_summary(&id, &code)?;
                    summary["bundle"] =
                        json!({"v": 1, "kind": "aurora-link-bundle", "link": id, "acl": all, "records": []});
                    Ok(summary)
                }
                None => {
                    let net = ctx.net().ok_or_else(|| {
                        RpcError::unavailable(
                            "joining over the network needs `aurora link serve`, or pass the inviter's bundle",
                        )
                    })?;
                    let id = net.join(&code, &label).await?;
                    d.joined_summary(&id, &code)
                }
            }
        }
        "link.accept" => d.link_accept(&p, false),
        "link.decline" => d.link_accept(&p, true),
        "link.verify" => d.link_verify(&p),
        "link.remove_member" => d.link_membership(&p, "remove_member"),
        "link.leave" => d.link_membership(&p, "leave"),
        "link.remove_device" => d.link_membership(&p, "remove_device"),
        "link.add_device" => d.link_membership(&p, "add_device"),
        "link.rotate_key" => d.link_membership(&p, "rotate_key"),
        "link.revoke_invite" => d.link_membership(&p, "revoke_invite"),
        "link.set_role" => d.link_membership(&p, "set_role"),
        "link.send" => {
            let mut raw = p.parse::<Value>("body")?;
            if let Some(obj) = raw.as_object_mut() {
                obj.entry("sent_at").or_insert(json!(now()));
            }
            let mut body = daemon::body_from(&raw)?;
            if let Some(atts) = p.opt::<Vec<Value>>("attachments")? {
                // One FsStore per directory: reuse the network's, or open one when offline.
                let blobs = match ctx.net() {
                    Some(net) => net.blobs.clone(),
                    None => crate::net::blob_store(&d.dirs).await.map_err(RpcError::internal)?,
                };
                for a in atts {
                    let path: String = serde_json::from_value(a.get("path").cloned().unwrap_or(Value::Null))
                        .map_err(|_| RpcError::invalid("attachment needs a path"))?;
                    let name = a
                        .get("name")
                        .and_then(Value::as_str)
                        .map(str::to_owned)
                        .unwrap_or_else(|| {
                            std::path::Path::new(&path)
                                .file_name()
                                .map(|n| n.to_string_lossy().into_owned())
                                .unwrap_or_default()
                        });
                    let data = std::fs::read(&path).map_err(|e| RpcError::invalid(format!("{path}: {e}")))?;
                    body.blobs.push(
                        crate::net::put_blob(&blobs, &name, &data)
                            .await
                            .map_err(RpcError::internal)?,
                    );
                }
            }
            let link = p.str("link")?;
            let out = d.link_send(&link, body, p.opt_str("source")?.as_deref())?;
            if let Some(net) = ctx.net() {
                net.advertise(&link);
            }
            Ok(out)
        }
        "link.read" => d.link_read(&p),
        "record.get" => d.record_get(&p),
        "events.wait" => {
            let cursors: BTreeMap<String, i64> = p.opt("cursors")?.unwrap_or_default();
            let timeout = p.opt::<u64>("timeout_ms")?.unwrap_or(0).min(60_000);
            let limit = p.opt::<u32>("limit")?.unwrap_or(200).clamp(1, 1000);
            let deadline = tokio::time::Instant::now() + std::time::Duration::from_millis(timeout);
            loop {
                let notified = d.events.notified();
                let events = d.events_after(&cursors, limit)?;
                if !events.is_empty() || tokio::time::Instant::now() >= deadline {
                    return Ok(json!({"events": events}));
                }
                let _ = tokio::time::timeout_at(deadline, notified).await;
            }
        }
        "promotion.record" => d.promotion_record(&p),
        "bundle.export" => d.bundle_export(&p),
        "bundle.import" => d.bundle_import(&p),
        "blob.get" => crate::net::blob_get(ctx, &p).await,
        "peers.add" => crate::net::peers_add(&d.dirs, &p),
        "net.status" => Ok(ctx.net().expect("checked").status()),
        "sync.now" => {
            d.wake.notify_waiters();
            Ok(json!({"dialing": true}))
        }
        "housekeeping" => d.housekeeping(),
        other => Err(RpcError {
            code: -32601,
            message: format!("no method {other}"),
        }),
    }
}

/// Handle one request line; returns the response line (None for a notification).
pub async fn handle_line(ctx: &Ctx, line: &str) -> Option<String> {
    let req: Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(e) => {
            return Some(
                json!({"jsonrpc": "2.0", "id": null, "error": {"code": -32700, "message": e.to_string()}}).to_string(),
            );
        }
    };
    let id = req.get("id").cloned();
    let method = req.get("method").and_then(Value::as_str).unwrap_or_default().to_owned();
    if req.get("jsonrpc").and_then(Value::as_str) != Some("2.0") || method.is_empty() {
        return Some(
            json!({"jsonrpc": "2.0", "id": id, "error": {"code": -32600, "message": "not a JSON-RPC 2.0 request"}})
                .to_string(),
        );
    }
    let params = req.get("params").cloned().unwrap_or(Value::Null);
    let trace = TRACE.load(std::sync::atomic::Ordering::Relaxed);
    if trace {
        tracing::info!("rpc <- {line}");
    }
    let result = dispatch(ctx, &method, params).await;
    let id = id?;
    let out = match result {
        Ok(v) => json!({"jsonrpc": "2.0", "id": id, "result": v}),
        Err(e) => json!({"jsonrpc": "2.0", "id": id, "error": {"code": e.code, "message": e.message}}),
    }
    .to_string();
    if trace {
        tracing::info!("rpc -> {out}");
    }
    Some(out)
}

/// Serve requests from one byte stream until it closes. Requests run one at a time per stream,
/// except `events.wait`, which a client should give its own connection.
pub async fn serve_stream<R: AsyncRead + Unpin, W: AsyncWrite + Unpin>(
    ctx: Arc<Ctx>,
    r: R,
    mut w: W,
) -> anyhow::Result<()> {
    let mut lines = BufReader::new(r);
    let mut buf = String::new();
    loop {
        buf.clear();
        let n = (&mut lines).take(MAX_LINE as u64).read_line(&mut buf).await?;
        if n == 0 {
            return Ok(());
        }
        if !buf.ends_with('\n') && n as usize >= MAX_LINE {
            anyhow::bail!("request line too long");
        }
        let line = buf.trim();
        if line.is_empty() {
            continue;
        }
        if let Some(resp) = handle_line(&ctx, line).await {
            w.write_all(resp.as_bytes()).await?;
            w.write_all(b"\n").await?;
            w.flush().await?;
        }
    }
}

use tokio::io::AsyncReadExt as _;

/// The endpoint string written to `linkd.addr`: a socket path, or a pipe name on Windows.
pub fn endpoint_name(path: &std::path::Path) -> String {
    #[cfg(windows)]
    return pipe_name(path);
    #[cfg(not(windows))]
    path.to_string_lossy().into_owned()
}

#[cfg(unix)]
pub async fn serve_socket(ctx: Arc<Ctx>, path: std::path::PathBuf) -> anyhow::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    if path.exists() {
        // A live daemon answers; a stale socket file is left by a crash.
        if tokio::net::UnixStream::connect(&path).await.is_ok() {
            anyhow::bail!("another aurora-linkd is already serving {}", path.display());
        }
        std::fs::remove_file(&path)?;
    }
    let listener = tokio::net::UnixListener::bind(&path)?;
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600))?;
    loop {
        let (stream, _) = listener.accept().await?;
        let ctx = ctx.clone();
        tokio::spawn(async move {
            let (r, w) = stream.into_split();
            if let Err(e) = serve_stream(ctx, r, w).await {
                tracing::debug!("rpc client: {e:#}");
            }
        });
    }
}

#[cfg(windows)]
pub fn pipe_name(path: &std::path::Path) -> String {
    let h = aurora_link::codec::hex(&aurora_link::crypto::sha256(&[path.to_string_lossy().as_bytes()]));
    format!(r"\\.\pipe\aurora-linkd-{}", &h[..16])
}

#[cfg(windows)]
pub async fn serve_socket(ctx: Arc<Ctx>, path: std::path::PathBuf) -> anyhow::Result<()> {
    use tokio::net::windows::named_pipe::ServerOptions;
    let name = pipe_name(&path);
    let mut server = ServerOptions::new()
        .first_pipe_instance(true)
        .reject_remote_clients(true)
        .create(&name)?;
    loop {
        server.connect().await?;
        let connected = server;
        server = ServerOptions::new().reject_remote_clients(true).create(&name)?;
        let ctx = ctx.clone();
        tokio::spawn(async move {
            let (r, w) = tokio::io::split(connected);
            if let Err(e) = serve_stream(ctx, r, w).await {
                tracing::debug!("rpc client: {e:#}");
            }
        });
    }
}
