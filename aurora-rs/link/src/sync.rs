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
    JoinHello {
        v: u32,
        link: String,
        invite: String,
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
                let entries = link.acl.missing_for(&acl);
                if !entries.is_empty() {
                    out.replies.push(Frame::Acl { entries });
                }
                out.replies
                    .extend(record_frames(link.missing_for(&heads, MAX_RECORDS_PER_PASS)?));
                out.replies.push(Frame::Synced { heads: link.heads()? });
            }
            Frame::Acl { entries } => {
                out.acl_added = link.add_acl(entries, now)?;
                if !link.state().sync_devices().contains(peer_device) {
                    return Err(refused("peer is not (or no longer) a member"));
                }
            }
            Frame::Records { records } => {
                let mut gap = false;
                for r in records {
                    match link.receive(me, &r, now)? {
                        Admit::Stored { .. } => {
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
                if gap {
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

/// The inviter's side of a join: check the invite is live, then accept the join entry.
pub fn serve_join(link: &mut Link, me: &Device, f: Frame, now: u64) -> Result<Vec<Frame>> {
    match f {
        Frame::JoinHello { v, link: id, invite } => {
            if v != 1 || id != link.id() {
                return Err(refused("join is for another link"));
            }
            let s = link.state();
            let live = s
                .invites
                .get(&invite)
                .is_some_and(|i| !i.revoked && !(i.single_use && i.used) && i.expires > now);
            if !live {
                return Err(refused("no live invite with that key"));
            }
            Ok(vec![Frame::Acl {
                entries: link.acl.missing_for(&BTreeSet::new()),
            }])
        }
        Frame::Join { entry } => {
            if entry.op != "join" {
                return Err(refused("expected a join entry"));
            }
            let hash = entry.hash()?;
            link.add_acl(vec![entry], now)?;
            if let Some((_, why)) = link.state().dropped.iter().find(|(h, _)| *h == hash) {
                return Err(refused(format!("join refused: {why}")));
            }
            link.upkeep(me, now)?;
            Ok(vec![Frame::Acl {
                entries: link.acl.missing_for(&BTreeSet::new()),
            }])
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
