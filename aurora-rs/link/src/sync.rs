//! The sync protocol, transport-agnostic: frames, their codec, and one session's logic.
//!
//! A session over any duplex byte stream (an iroh bi-stream in the daemon, an in-memory pipe in
//! tests) runs:
//!
//! 1. `hello {link, device, acl, heads}` in both directions;
//! 2. each side sends the ACL entries the other lacks, so membership is current before any
//!    record is checked;
//! 3. then the records the other lacks, per author in seq order, then `synced`;
//! 4. then live: new records are pushed as they are written or relayed.
//!
//! Any member relays any other member's records (they are signed and sealed), so A reaches C
//! through B when A and C are never online together. A mailbox is just a member that can't read.

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::acl::Entry;
use crate::engine::{Admit, Link};
use crate::error::{Result, refused};
use crate::identity::Device;
use crate::record::{HeadAdvert, Record};

pub const ALPN: &[u8] = b"aurora/link/1";
pub const MAX_FRAME: usize = 2 * 1024 * 1024;
/// Records per `records` frame are cut to stay well under MAX_FRAME.
const BATCH_BYTES: usize = 1024 * 1024;
const MAX_RECORDS_PER_PASS: usize = 4096;

// Frames live only between a read and its handling, so their size spread costs nothing.
#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "t", rename_all = "snake_case", deny_unknown_fields)]
pub enum Frame {
    Hello {
        v: u32,
        link: String,
        device: String,
        acl: BTreeSet<String>,
        heads: BTreeMap<String, u64>,
    },
    Acl {
        entries: Vec<Entry>,
    },
    Records {
        records: Vec<Record>,
    },
    /// "Send me everything after these heads" (after a gap).
    Want {
        heads: BTreeMap<String, u64>,
    },
    Synced {
        heads: BTreeMap<String, u64>,
    },
    Advert {
        advert: HeadAdvert,
    },
    /// A joiner asks the inviter for the log, proving nothing yet but which invite it holds.
    /// `proof` signs (link, this connection's device) with the invite key: holding the invite's
    /// public key (which every member sees in the log) is not enough to read the log.
    JoinHello {
        v: u32,
        link: String,
        invite: String,
        proof: String,
    },
    Join {
        entry: Entry,
    },
    Bye {
        reason: String,
    },
}

pub fn encode(f: &Frame) -> Result<Vec<u8>> {
    let body = serde_json::to_vec(f).map_err(|e| refused(e.to_string()))?;
    if body.len() > MAX_FRAME {
        return Err(refused("frame too large"));
    }
    let mut out = (body.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(&body);
    Ok(out)
}

/// Decode one frame body (without its 4-byte length).
pub fn decode(body: &[u8]) -> Result<Frame> {
    if body.len() > MAX_FRAME {
        return Err(refused("frame too large"));
    }
    serde_json::from_slice(body).map_err(|e| refused(format!("frame is malformed: {e}")))
}

/// Pull complete frames out of a buffer (for transports that hand over arbitrary chunks).
pub fn split(buf: &mut Vec<u8>) -> Result<Vec<Frame>> {
    let mut out = Vec::new();
    loop {
        if buf.len() < 4 {
            return Ok(out);
        }
        let n = u32::from_be_bytes(buf[..4].try_into().expect("4 bytes")) as usize;
        if n > MAX_FRAME {
            return Err(refused("frame too large"));
        }
        if buf.len() < 4 + n {
            return Ok(out);
        }
        out.push(decode(&buf[4..4 + n])?);
        buf.drain(..4 + n);
    }
}

pub fn hello(link: &Link, me: &Device) -> Result<Frame> {
    Ok(Frame::Hello {
        v: 1,
        link: link.id().to_owned(),
        device: me.id_hex(),
        acl: link.acl.hashes(),
        heads: link.heads()?,
    })
}

/// Split ACL entries into frames under the batch budget.
pub fn acl_frames(entries: Vec<Entry>) -> Vec<Frame> {
    let mut out = Vec::new();
    let mut batch = Vec::new();
    let mut size = 0;
    for e in entries {
        let n = serde_json::to_vec(&e).map(|v| v.len()).unwrap_or(BATCH_BYTES);
        if size + n > BATCH_BYTES && !batch.is_empty() {
            out.push(Frame::Acl {
                entries: std::mem::take(&mut batch),
            });
            size = 0;
        }
        size += n;
        batch.push(e);
    }
    if !batch.is_empty() {
        out.push(Frame::Acl { entries: batch });
    }
    out
}

/// Split records into frames under the batch budget.
pub fn record_frames(records: Vec<Record>) -> Vec<Frame> {
    let mut out = Vec::new();
    let mut batch = Vec::new();
    let mut size = 0;
    for r in records {
        let n = r.ct.as_ref().map(String::len).unwrap_or(0) + 1024;
        if size + n > BATCH_BYTES && !batch.is_empty() {
            out.push(Frame::Records {
                records: std::mem::take(&mut batch),
            });
            size = 0;
        }
        size += n;
        batch.push(r);
    }
    if !batch.is_empty() {
        out.push(Frame::Records { records: batch });
    }
    out
}

/// What one session learned, for the daemon to act on.
#[derive(Debug, Default)]
pub struct Outcome {
    pub replies: Vec<Frame>,
    /// Records newly stored this step (to relay to other live sessions).
    pub stored: Vec<Record>,
    pub acl_added: usize,
    pub refused: Vec<String>,
}

/// One sync session's state.
#[derive(Debug, Default)]
pub struct Session {
    pub peer: Option<String>,
    pub peer_heads: BTreeMap<String, u64>,
    pub synced: bool,
}

impl Session {
    pub fn new() -> Self {
        Self::default()
    }

    /// Handle one frame from the peer. `peer_device` is the key the transport authenticated.
    pub fn on_frame(&mut self, link: &mut Link, me: &Device, peer_device: &str, f: Frame, now: u64) -> Result<Outcome> {
        let mut out = Outcome::default();
        match f {
            Frame::Hello {
                v,
                link: id,
                device,
                acl,
                heads,
            } => {
                if v != 1 || id != link.id() || device != peer_device {
                    return Err(refused("hello does not match this link or this connection"));
                }
                self.peer = Some(device);
                self.peer_heads = heads.clone();
                out.replies.extend(acl_frames(link.acl.missing_for(&acl)));
                out.replies
                    .extend(record_frames(link.missing_for(&heads, MAX_RECORDS_PER_PASS)?));
                out.replies.push(Frame::Synced { heads: link.heads()? });
            }
            Frame::Acl { entries } => {
                // A refused entry is the sender's problem, not a reason to drop the session.
                match link.add_acl(entries, now) {
                    Ok(n) => out.acl_added = n,
                    Err(e) => {
                        link.store.refusal(peer_device, &e.to_string(), now)?;
                        out.refused.push(e.to_string());
                    }
                }
                if !link.state().sync_devices().contains(peer_device) {
                    return Err(refused("peer is not (or no longer) a member"));
                }
            }
            Frame::Records { records } => {
                let mut gap = false;
                let mut progress = false;
                for r in records {
                    match link.receive(me, &r, now)? {
                        Admit::Stored { .. } => {
                            progress = true;
                            let n = self.peer_heads.entry(r.author.clone()).or_insert(0);
                            *n = (*n).max(r.seq);
                            out.stored.push(r);
                        }
                        Admit::Duplicate => {}
                        Admit::Gap { .. } => gap = true,
                        Admit::Refused(why) => {
                            link.store.refusal(peer_device, &why, now)?;
                            out.refused.push(why);
                        }
                    }
                }
                // Ask again only after progress: a gap behind a refused or over-quota record would
                // otherwise make both sides resend the same batch for ever.
                if gap && progress {
                    out.replies.push(Frame::Want { heads: link.heads()? });
                }
            }
            Frame::Want { heads } => {
                out.replies
                    .extend(record_frames(link.missing_for(&heads, MAX_RECORDS_PER_PASS)?));
            }
            Frame::Synced { heads } => {
                self.synced = true;
                for (a, s) in heads {
                    let n = self.peer_heads.entry(a).or_insert(0);
                    *n = (*n).max(s);
                }
            }
            Frame::Advert { advert } => {
                advert.verify()?;
                if advert.link == link.id() && link.heads()?.get(&advert.author).copied().unwrap_or(0) < advert.seq {
                    out.replies.push(Frame::Want { heads: link.heads()? });
                }
            }
            Frame::JoinHello { .. } | Frame::Join { .. } => {
                return Err(refused("join frames belong to a join session"));
            }
            Frame::Bye { .. } => {}
        }
        Ok(out)
    }

    /// Records to push live: those the peer has not been seen to hold.
    pub fn push(&mut self, records: &[Record]) -> Vec<Frame> {
        let fresh: Vec<Record> = records
            .iter()
            .filter(|r| self.peer_heads.get(&r.author).copied().unwrap_or(0) < r.seq)
            .cloned()
            .collect();
        for r in &fresh {
            let n = self.peer_heads.entry(r.author.clone()).or_insert(0);
            *n = (*n).max(r.seq);
        }
        record_frames(fresh)
    }
}

fn join_hello_bytes(link: &str, device: &str) -> Result<Vec<u8>> {
    crate::codec::jcs(&serde_json::json!({"link": link, "device": device}))
}

/// The joiner's first frame: proves it holds the invite secret, bound to this connection.
pub fn join_hello(link: &str, me: &Device, secret: &[u8; 32]) -> Result<Frame> {
    let key = crate::acl::invite_key(secret);
    let proof = crate::crypto::sign(&key, "join-hello", &join_hello_bytes(link, &me.id_hex())?);
    Ok(Frame::JoinHello {
        v: 1,
        link: link.to_owned(),
        invite: crate::codec::hex(&crate::crypto::public_of(&key)),
        proof: crate::codec::b64(&proof),
    })
}

/// A live invite by the verifier's clock: present, unrevoked, unused if single-use, unexpired.
fn invite_live(link: &Link, invite: &str, now: u64) -> bool {
    link.state()
        .invites
        .get(invite)
        .is_some_and(|i| !i.revoked && !(i.single_use && i.used) && i.expires > now)
}

/// The inviter's side of a join. Nothing is stored until the invite is live by our own clock
/// and the proof holds; the replies end with `synced`.
pub fn serve_join(link: &mut Link, me: &Device, peer_device: &str, f: Frame, now: u64) -> Result<Vec<Frame>> {
    let reply = |link: &Link| -> Vec<Frame> {
        let mut out = acl_frames(link.acl.missing_for(&BTreeSet::new()));
        out.push(Frame::Synced { heads: BTreeMap::new() });
        out
    };
    match f {
        Frame::JoinHello {
            v,
            link: id,
            invite,
            proof,
        } => {
            if v != 1 || id != link.id() || !invite_live(link, &invite, now) {
                return Err(refused("no live invite with that key for this link"));
            }
            let msg = join_hello_bytes(&id, peer_device)?;
            crate::crypto::verify(
                &crate::codec::unhex::<32>(&invite)?,
                "join-hello",
                &msg,
                &crate::codec::unb64(&proof)?,
            )?;
            Ok(reply(link))
        }
        Frame::Join { entry } => {
            if entry.op != "join" || entry.author != peer_device || entry.link != link.id() {
                return Err(refused("expected this connection's own join entry"));
            }
            let crate::acl::Op::Join(j) = entry.parsed()? else {
                return Err(refused("expected a join entry"));
            };
            if !invite_live(link, &j.invite, now) {
                return Err(refused("no live invite with that key for this link"));
            }
            let hash = entry.hash()?;
            link.add_acl(vec![entry], now)?;
            if !link.acl.contains(&hash) || link.state().dropped.iter().any(|(h, _)| *h == hash) {
                return Err(refused("join refused"));
            }
            link.upkeep(me, now)?;
            Ok(reply(link))
        }
        _ => Err(refused("expected a join frame")),
    }
}

/// The joiner's side: build a join entry against the inviter's log.
pub fn join_entry(entries: &[Entry], me: &Device, secret: &[u8; 32], label: &str, now: u64) -> Result<Entry> {
    let mut log = crate::acl::AclLog::new();
    log.insert(entries.to_vec())?;
    let s = log.state();
    crate::acl::make_join(me, secret, &s.link_id, &s.head, s.head_seq, label, now)
}
