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
        summary: "Renew the device certificate (needs the phrase, or the passphrase for the sealed root.json) and announce it in every link.",
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
        summary: "Members, devices, heads, receipts, invites and alarms of one link; the ACL chain tip, its sequencer (term, a pending handoff), an equivocation if one halted the chain, and this device's queued or refused proposals.",
        params: &[("link", "string", true)],
        network: false,
    },
    Method {
        name: "link.invite",
        summary: "Publish an invite and return its code. The code also carries the bundle-free dial hints. `invite` is the id of the action that issued it (joins and revocations name it), `invite_key` its public key. On a device that does not sequence the link the invite is a proposal (`queued`): the code works once the sequencer includes it.",
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
        summary: "Join with an invite code. With `acl` (the inviter's chain from a bundle) it works offline and returns our join proposal in a bundle for the inviter to import; without, it dials the inviter. The result names the link, both fleet fingerprints, `inviter_root` (the fleet that published the invite), `owner_root`, the safety number, `fingerprint_matches_code`, `pending`, `has_key`, and `queued` when the join waits for the link's sequencer.",
        params: &[
            ("code", "string", true),
            ("label", "string", false),
            ("acl", "array", false),
        ],
        network: false,
    },
    Method {
        name: "link.accept",
        summary: "Admit a pending join (wraps the read key to it). Appended on the sequencer; elsewhere a proposal (`proposal`, `queued`).",
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
        summary: "Remove a fleet and rotate the read key. Appended on the sequencer; elsewhere a proposal for it to include.",
        params: &[("link", "string", true), ("member", "string", true)],
        network: false,
    },
    Method {
        name: "link.leave",
        summary: "Leave a link (a proposal; the sequencer then rotates the key, or any device holding the key after the grace).",
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
        summary: "Start a new read-key epoch. An admin that cannot read the key in force (junk wrapped to it by a rogue key holder) re-keys from the last epoch it can read.",
        params: &[("link", "string", true)],
        network: false,
    },
    Method {
        name: "link.revoke_invite",
        summary: "Kill an unused invite, named by the hash of the entry that issued it (`invite` in `link.invite` and `link.status`).",
        params: &[("link", "string", true), ("invite", "string", true)],
        network: false,
    },
    Method {
        name: "link.handoff",
        summary: "Hand the link's sequencer to another active owner or admin device (by the current sequencer, or proposed by an owner device). Its next entry starts the next term.",
        params: &[("link", "string", true), ("device", "string", true)],
        network: false,
    },
    Method {
        name: "link.takeover",
        summary: "The owner's takeover when the sequencer is lost or compromised: the fleet root (the phrase, or the passphrase for root.json) makes this device the sequencer of a new term after entry `after` (default: this replica's last held entry, so nothing it holds is dropped). Later entries of older terms are dropped on every replica; an equivocation halt ends. While halted below its last held entry, `after` is required: the halt's seq - 1 drops both branches and every replica can take it; the last held entry keeps this replica's branch, and replicas holding the other branch stay halted until a takeover at or below the halt's seq - 1 reaches them.",
        params: &[
            ("link", "string", true),
            ("phrase", "string", false),
            ("passphrase", "string", false),
            ("after", "integer", false),
        ],
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
        summary: "The whole log and the records of a link, for sneakernet.",
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
    Method {
        name: "relay.config",
        summary: "An iroh-relay config whose allowlist is every device of every link here: a self-hosted relay only members can use.",
        params: &[("http_bind", "string", false)],
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

/// Log every request and response line (`serve --trace-rpc`), secrets redacted.
pub static TRACE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

/// Whether a field may hold a secret: a recovery phrase, a passphrase, an invite code (it carries
/// the invite secret), or key material of any kind.
fn secret_field(name: &str) -> bool {
    let n = name.to_ascii_lowercase();
    matches!(n.as_str(), "code" | "sign" | "key" | "kek" | "seed" | "bundle")
        || ["phrase", "secret", "recovery", "private", "seed", "_key", "password"]
            .iter()
            .any(|s| n.contains(s))
}

fn redact_value(v: &mut Value) {
    match v {
        Value::Object(m) => {
            for (k, x) in m.iter_mut() {
                if secret_field(k) && !x.is_null() && !x.is_boolean() {
                    *x = Value::String("<redacted>".into());
                } else {
                    redact_value(x);
                }
            }
        }
        Value::Array(xs) => xs.iter_mut().for_each(redact_value),
        _ => {}
    }
}

/// A request or response line as `--trace-rpc` logs it: secret fields replaced, anywhere in it.
/// A line that does not parse is not logged at all, only its length.
pub fn redacted(line: &str) -> String {
    match serde_json::from_str::<Value>(line) {
        Ok(mut v) => {
            redact_value(&mut v);
            v.to_string()
        }
        Err(_) => format!("<{} bytes that are not JSON>", line.len()),
    }
}

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
                    // Offline: our join proposal goes back to the inviter in a bundle; the link is
                    // ours once we import a bundle whose chain includes the join.
                    let (proposal, id) = d.join_with(&code, entries.clone(), &label)?;
                    let mut summary = d.pending_join_summary(&code, &entries)?;
                    summary["queued"] = json!(true);
                    summary["bundle"] = json!({"v": 2, "kind": "aurora-link-bundle", "link": id, "acl": entries,
                                               "records": [], "proposals": [proposal]});
                    Ok(summary)
                }
                None => {
                    let net = ctx.net().ok_or_else(|| {
                        RpcError::unavailable(
                            "joining over the network needs `aurora link serve`, or pass the inviter's bundle",
                        )
                    })?;
                    match net.join(&code, &label).await? {
                        crate::net::Joined::Adopted(id) => d.joined_summary(&id, &code),
                        crate::net::Joined::Queued(summary) => Ok(summary),
                    }
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
        "link.handoff" => d.link_membership(&p, "handoff"),
        "link.takeover" => d.link_takeover(&p),
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
            d.wake_now();
            Ok(json!({"dialing": true}))
        }
        "housekeeping" => d.housekeeping(),
        "relay.config" => {
            let mut devices: std::collections::BTreeSet<String> = d.peer_links().into_keys().collect();
            if let Ok(me) = d.device() {
                devices.insert(me.id_hex());
            }
            let bind = p.opt_str("http_bind")?.unwrap_or_else(|| "[::]:3340".into());
            let list: Vec<String> = devices.iter().map(|x| format!("  \"{x}\",")).collect();
            let toml = format!(
                "# iroh-relay config: `cargo install iroh-relay`, then `iroh-relay --config-path relay.toml`.\n\
                 # Written by aurora-linkd: only the devices of our links may relay through it.\n\
                 # Add a [tls] section for a public host, and regenerate after membership changes.\n\
                 http_bind_addr = \"{bind}\"\n\
                 access.allowlist = [\n{}\n]\n",
                list.join("\n")
            );
            Ok(json!({"toml": toml, "devices": devices.len()}))
        }
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
        tracing::info!("rpc <- {}", redacted(line));
    }
    let result = dispatch(ctx, &method, params).await;
    let id = id?;
    let out = match result {
        Ok(v) => json!({"jsonrpc": "2.0", "id": id, "result": v}),
        Err(e) => json!({"jsonrpc": "2.0", "id": id, "error": {"code": e.code, "message": e.message}}),
    }
    .to_string();
    if trace {
        tracing::info!("rpc -> {}", redacted(&out));
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
    // The socket is bound inside a folder only we can enter, so it is never reachable by
    // another user, not even between the bind and the chmod below.
    crate::daemon::private_socket_dir(&path)?;
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

/// The pipe's security: a protected DACL granting this user (by SID) full access and nobody
/// else anything, so another local user can neither connect nor create a rival instance.
#[cfg(windows)]
mod pipe_security {
    use std::io;
    use std::ptr::null_mut;

    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE, LocalFree};
    use windows_sys::Win32::Security::Authorization::{
        ConvertSidToStringSidW, ConvertStringSecurityDescriptorToSecurityDescriptorW, SDDL_REVISION_1,
    };
    use windows_sys::Win32::Security::{
        GetTokenInformation, PSECURITY_DESCRIPTOR, SECURITY_ATTRIBUTES, TOKEN_QUERY, TOKEN_USER, TokenUser,
    };
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};

    pub struct OwnerOnly {
        sd: PSECURITY_DESCRIPTOR,
        pub attrs: SECURITY_ATTRIBUTES,
    }

    // SAFETY: the descriptor is owned by this value alone and only read by the OS.
    unsafe impl Send for OwnerOnly {}

    impl Drop for OwnerOnly {
        fn drop(&mut self) {
            // SAFETY: `sd` came from ConvertStringSecurityDescriptorToSecurityDescriptorW.
            unsafe { LocalFree(self.sd) };
        }
    }

    /// This process's user SID, as a string ("S-1-5-21-...").
    fn user_sid() -> io::Result<String> {
        // SAFETY: plain Win32 calls with checked results; the token buffer is u64-aligned and
        // sized by the first call, and every handle and allocation is released.
        unsafe {
            let mut token: HANDLE = null_mut();
            if OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut token) == 0 {
                return Err(io::Error::last_os_error());
            }
            let mut len = 0u32;
            GetTokenInformation(token, TokenUser, null_mut(), 0, &mut len);
            let mut buf = vec![0u64; (len as usize).div_ceil(8).max(1)];
            let ok = GetTokenInformation(token, TokenUser, buf.as_mut_ptr().cast(), len, &mut len);
            CloseHandle(token);
            if ok == 0 {
                return Err(io::Error::last_os_error());
            }
            let user = &*(buf.as_ptr() as *const TOKEN_USER);
            let mut wide = null_mut();
            if ConvertSidToStringSidW(user.User.Sid, &mut wide) == 0 {
                return Err(io::Error::last_os_error());
            }
            let mut n = 0;
            while *wide.add(n) != 0 {
                n += 1;
            }
            let sid = String::from_utf16_lossy(std::slice::from_raw_parts(wide, n));
            LocalFree(wide.cast());
            Ok(sid)
        }
    }

    pub fn owner_only() -> io::Result<OwnerOnly> {
        let sddl: Vec<u16> = format!("D:P(A;;GA;;;{})", user_sid()?)
            .encode_utf16()
            .chain(std::iter::once(0))
            .collect();
        let mut sd: PSECURITY_DESCRIPTOR = null_mut();
        // SAFETY: a NUL-terminated SDDL string in, a LocalAlloc'd descriptor out (freed on drop).
        if unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.as_ptr(), SDDL_REVISION_1, &mut sd, null_mut())
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        Ok(OwnerOnly {
            sd,
            attrs: SECURITY_ATTRIBUTES {
                nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
                lpSecurityDescriptor: sd,
                bInheritHandle: 0,
            },
        })
    }
}

#[cfg(windows)]
pub async fn serve_socket(ctx: Arc<Ctx>, path: std::path::PathBuf) -> anyhow::Result<()> {
    use tokio::net::windows::named_pipe::{NamedPipeServer, ServerOptions};
    let name = pipe_name(&path);
    let mut security = pipe_security::owner_only()?;
    // The first instance must be the first of its name (FILE_FLAG_FIRST_PIPE_INSTANCE): if
    // anyone squats the name, we fail rather than share it. Every instance carries the
    // owner-only DACL, so nobody else can connect to it or add instances.
    let mut create = |first: bool| -> std::io::Result<NamedPipeServer> {
        let mut opts = ServerOptions::new();
        opts.first_pipe_instance(first).reject_remote_clients(true);
        // SAFETY: `security.attrs` points at a valid descriptor that outlives the call.
        unsafe { opts.create_with_security_attributes_raw(&name, std::ptr::from_mut(&mut security.attrs).cast()) }
    };
    let mut server = create(true)?;
    loop {
        server.connect().await?;
        let connected = server;
        server = create(false)?;
        let ctx = ctx.clone();
        tokio::spawn(async move {
            let (r, w) = tokio::io::split(connected);
            if let Err(e) = serve_stream(ctx, r, w).await {
                tracing::debug!("rpc client: {e:#}");
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trace_lines_carry_no_secrets() {
        let req = json!({"jsonrpc": "2.0", "id": 1, "method": "identity.init",
            "params": {"phrase": "abandon ability able", "passphrase": "correct horse", "label": "laptop"}});
        let out = redacted(&req.to_string());
        assert!(!out.contains("abandon") && !out.contains("horse"), "{out}");
        assert!(out.contains("laptop"), "{out}");
        let resp = json!({"jsonrpc": "2.0", "id": 2, "result": {"code": "aurora-invite1:SECRET", "invite": "ab",
            "phrase": "zoo zoo", "nested": [{"secret": "s3", "recovery_phrase": "r"}], "has_key": true}});
        let out = redacted(&resp.to_string());
        for leak in ["SECRET", "zoo", "s3", "\"r\""] {
            assert!(!out.contains(leak), "{leak} in {out}");
        }
        assert!(out.contains("\"has_key\":true"), "{out}");
        assert!(!redacted("not json with a phrase").contains("phrase"));
    }
}
