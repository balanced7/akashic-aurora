//! The sync protocol, transport-agnostic: frames, their codec, and one session's logic.
//!
//! A session over any duplex byte stream (an iroh bi-stream in the daemon, an in-memory pipe in
//! tests) runs:
//!
//! 1. `hello {v, link, device, acl, heads, more}` in both directions. `acl` is the sender's ACL
//!    chain tip `(term, seq, hash)`; `heads` names at most `MAX_HELLO_AUTHORS` authors' record
//!    heads (a seq and the id of the record there), the rest following in `heads` frames;
//! 2. the side that is behind on the chain asks for a range with `acl_want {from, to}`; the
//!    side ahead answers with exactly the entries `from < seq <= to` it holds, in `acl` frames of
//!    at most `ACL_FRAME_BYTES`, and never more than `ACL_BYTES_PER_MIN` a minute per session,
//!    then `acl_done {upto}`. The asker keeps one want outstanding: it asks for the rest after
//!    `acl_done` when its tip moved (entries it refused are no progress, review finding R6-7),
//!    and after a `ping` when the budget cut an answer short. A
//!    received entry that does not link to the chain makes the receiver ask from further back,
//!    until the fork point (a root takeover's `after`, or an equivocation) is found. A tip
//!    conflict at one `(term, seq)` is checked as equivocation evidence, and a halted side sends
//!    its `evidence`;
//! 3. each side sends its queued `propose` frames (its own proposals and those it relays). The
//!    sequencer includes or refuses each; a signed `refusal` travels back the same way. A refusal
//!    counts against the proposal's origin's daily allowance, and a proposal the peer could have
//!    found invalid itself against the peer's (`Link::offer_from`);
//! 4. then the records the other lacks, per author in seq order, then `synced`. An answer (to a
//!    hello, its `heads` pages, or a `want`) holds at most `MAX_RECORDS_PER_PASS` records and
//!    what is left of `RECORD_BYTES_PER_MIN` for the minute, and ends with `synced`; one cut
//!    short says `more`, and the asker asks again with a `want`: at once if the answer stored
//!    something, at its next `ping` if the answer was empty (review finding R8-2). Records
//!    that could not be stored are asked for again only when that can help (review finding
//!    R9-1): records that waited for a chain position as soon as the chain arrives here (at
//!    once, or at the first `ping` after our tip moved); an author over its hourly quota at the
//!    first `ping` after the quota admits more; records pushed past a gap at the next `ping`.
//!    Records behind a refused one are not asked for again. Records sent for a head the peer
//!    names with another id (`conflicts`) count against the same byte budget, each claim
//!    answered once a minute (review finding R9-4);
//! 5. then live: new records and new ACL entries are pushed as they come, and `ping` keeps an
//!    idle session open.
//!
//! A hello never triggers an ACL transfer by itself (review finding R5-3): only an explicit,
//! bounded want does. A session takes at most `MAX_ACL_FRAMES_PER_MIN` ACL-side frames (`acl`,
//! `acl_want`, `propose`, `refusal`, `evidence`) a minute from its peer, and each evidence check
//! its frames cause costs `EVIDENCE_CHECK_FRAMES` more (review finding R7-1); and at most
//! `MAX_RECORD_FRAMES_PER_MIN` record-side frames (`want`, `heads`, `synced`, `advert`; review
//! finding R8-2); and it looks at most at `RECORD_BYTES_IN_PER_MIN` of the records the peer sends
//! (the rest is asked for again at the next `ping`). Every frame, pings and `records` frames
//! included, counts against `MAX_FRAMES_PER_MIN`, checked before anything else (review finding
//! R9-2). What a peer has spent is a `Budget`, which the daemon keeps per link and peer across all
//! its sessions, so a reconnect does not refill it (review finding R8-3). Membership is checked on
//! every frame, as a lookup in device sets the chain keeps per held tip (R9-2).
//!
//! While the chain is halted, records, heads and proposals need `may_sync` (the narrowed view),
//! but the chain's own frames are traded with any device of the held tip (`may_sync_acl`), so a
//! device the halt leaves out still gets the evidence and the owner's takeover (review finding
//! R7-2).
//!
//! Any member relays any other member's records (they are signed and sealed), so A reaches C
//! through B when A and C are never online together. A mailbox is just a member that can't read.

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::acl::{AclPos, Entry, InviteTicket, Proposal, ProposalRefusal};
use crate::engine::{Admit, Link, Offered};
use crate::error::{Result, refused};
use crate::identity::Device;
use crate::record::{HeadAdvert, Record};

/// The sync protocol: 2 is the sequenced ACL chain (review round 5).
pub const ALPN: &[u8] = b"aurora/link/2";
pub const HELLO_VERSION: u32 = 2;
pub const MAX_FRAME: usize = 2 * 1024 * 1024;
/// The first frame of a connection comes from a peer nobody has checked yet; the daemon reads it
/// with this cap. A hello always fits, whatever the size of the chain.
pub const MAX_FIRST_FRAME: usize = 64 * 1024;
/// Authors whose record heads one hello lists, at most; the rest follow in `heads` frames.
pub const MAX_HELLO_AUTHORS: usize = 128;
/// Authors one `heads` frame lists, at most.
const MAX_AUTHORS_PER_FRAME: usize = 4096;
/// Authors whose heads a held hello (from a peer not yet known as a member) may collect.
const MAX_HELD_AUTHORS: usize = 4 * MAX_AUTHORS_PER_FRAME;
/// ACL-side frames (`acl`, `acl_want`, `acl_done`, `propose`, `refusal`, `evidence`) one session
/// takes from its peer per minute.
pub const MAX_ACL_FRAMES_PER_MIN: u32 = 120;
/// What one evidence check (a signature, a fold of the chain and a dry application) costs from
/// the same budget, in frames (review finding R7-1): a session gets at most
/// `MAX_ACL_FRAMES_PER_MIN / EVIDENCE_CHECK_FRAMES` checks a minute, whatever its frames carry.
pub const EVIDENCE_CHECK_FRAMES: u32 = 8;
/// The most ACL entry bytes in one `acl` frame (one entry always fits: `acl::MAX_ENTRY_BYTES`).
pub const ACL_FRAME_BYTES: usize = 256 * 1024;
/// The most ACL entry bytes one session sends its peer per minute (plus at most one entry).
pub const ACL_BYTES_PER_MIN: usize = 8 * 1024 * 1024;
/// Frames of any kind one peer sends us on one link a minute, across its sessions (review finding
/// R9-2): pings and records frames included, which no other budget counts. A link of the default
/// 16 members has at most 128 devices; each writing at the default quota (600 records an hour)
/// is about 1,300 live pushes a minute, so this leaves room for twice that.
pub const MAX_FRAMES_PER_MIN: u32 = 2400;
/// Record-side frames (`want`, `heads`, `synced`, `advert`) one session takes from its peer per
/// minute (review finding R8-2): each may make us read and send records.
pub const MAX_RECORD_FRAMES_PER_MIN: u32 = 120;
/// The most record bytes (`Record::frame_cost`) one session sends its peer per minute in answer to
/// its hello, `heads` pages and `want`s (plus at most one record); live pushes of new records are
/// not counted. An answer the budget cuts short says so (`synced` with `more`), and the peer asks
/// again (review finding R8-2). 16 MiB a minute is about 1 GB an hour, past what the default
/// hourly quota per author (600 records) admits for any realistic record size.
pub const RECORD_BYTES_PER_MIN: usize = 16 * 1024 * 1024;
/// The most record bytes (`Record::frame_cost`) we look at from one peer per minute: twice what an
/// honest peer sends in answers (`RECORD_BYTES_PER_MIN`), leaving as much for live pushes. Past
/// it, records are not checked (each costs a signature), and we ask for them again at the next
/// ping (review round 8).
pub const RECORD_BYTES_IN_PER_MIN: usize = 2 * RECORD_BYTES_PER_MIN;
/// Proposals one side sends at a hello, at most (the rest go at the next session).
pub const MAX_PROPOSALS_AT_HELLO: usize = 32;
/// Records per `records` frame are cut to stay well under MAX_FRAME.
const BATCH_BYTES: usize = 1024 * 1024;
const MAX_RECORDS_PER_PASS: usize = 4096;
/// Authors whose heads disagree with ours that one frame answers (each costs a record and a want).
const MAX_CONFLICTS_PER_FRAME: usize = 64;
/// Head claims that disagree with ours (author, seq, claimed id) one peer has answered a minute,
/// at most (review finding R9-4). Each is answered once in the minute.
pub const MAX_CONFLICTS_PER_MIN: usize = 256;

/// One author's head as a peer reports it: the seq and the id of the record at that seq.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HeadRef {
    pub seq: u64,
    pub id: String,
}

/// Every author's head, as `hello`, `want` and `synced` carry them.
pub type Heads = BTreeMap<String, HeadRef>;

/// This link's heads, with ids.
pub fn heads_of(link: &Link) -> Result<Heads> {
    Ok(link
        .store
        .heads()?
        .into_iter()
        .map(|(a, (seq, id))| (a, HeadRef { seq, id }))
        .collect())
}

/// Seqs only, for the record plan.
fn seqs(heads: &Heads) -> BTreeMap<String, u64> {
    heads.iter().map(|(a, h)| (a.clone(), h.seq)).collect()
}

// Frames live only between a read and its handling, so their size spread costs nothing.
#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "t", rename_all = "snake_case", deny_unknown_fields)]
pub enum Frame {
    Hello {
        v: u32,
        link: String,
        device: String,
        /// The sender's ACL chain tip.
        acl: AclPos,
        /// Record heads of at most `MAX_HELLO_AUTHORS` authors.
        heads: Heads,
        /// More record heads follow in `heads` frames.
        more: bool,
    },
    /// More of the sender's record heads, after a hello that said `more`.
    Heads {
        heads: Heads,
        more: bool,
    },
    /// A contiguous run of ACL chain entries, lowest seq first.
    Acl {
        entries: Vec<Entry>,
    },
    /// "Send me the chain entries with `from < seq <= to`."
    AclWant {
        from: u64,
        to: u64,
    },
    /// The end of the answer to an `acl_want`: the last seq sent (`from` when none was).
    AclDone {
        upto: u64,
    },
    /// A proposal on its way to the sequencer.
    Propose {
        proposal: Proposal,
    },
    /// The sequencer's signed refusal of a proposal, on its way back to the proposer.
    Refusal {
        refusal: ProposalRefusal,
    },
    /// Two entries the same sequencer signed at one position.
    Evidence {
        ours: Entry,
        theirs: Entry,
    },
    Records {
        records: Vec<Record>,
    },
    /// "Send me everything after these heads" (after a gap).
    Want {
        heads: Heads,
    },
    /// The end of an answer to a hello, its `heads` pages or a `want`: the sender's heads, and
    /// whether it holds more that the peer lacks (the answer was cut short): then ask again.
    Synced {
        heads: Heads,
        #[serde(default, skip_serializing_if = "std::ops::Not::not")]
        more: bool,
    },
    Advert {
        advert: HeadAdvert,
    },
    /// Keeps an idle session open (the daemon closes a session silent for too long).
    Ping {},
    /// A joiner asks the inviter for the chain, proving nothing yet but which invite it holds.
    /// `proof` signs (link, invite, this connection's device) with the invite key.
    JoinHello {
        v: u32,
        link: String,
        invite: String,
        proof: String,
    },
    /// The joiner's join proposal.
    Join {
        proposal: Proposal,
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

/// Our opening frames: a hello that always fits `MAX_FIRST_FRAME`, then, when we hold heads of
/// more authors than one hello lists, `heads` frames with the rest.
pub fn hello(link: &Link, me: &Device) -> Result<Vec<Frame>> {
    let all: Vec<(String, HeadRef)> = heads_of(link)?.into_iter().collect();
    let first: Heads = all.iter().take(MAX_HELLO_AUTHORS).cloned().collect();
    let rest: Vec<&[(String, HeadRef)]> = all
        .get(MAX_HELLO_AUTHORS..)
        .unwrap_or(&[])
        .chunks(MAX_AUTHORS_PER_FRAME)
        .collect();
    let mut out = vec![Frame::Hello {
        v: HELLO_VERSION,
        link: link.id().to_owned(),
        device: me.id_hex(),
        acl: link.acl.tip(),
        heads: first,
        more: !rest.is_empty(),
    }];
    for (i, page) in rest.iter().enumerate() {
        out.push(Frame::Heads {
            heads: page.iter().cloned().collect(),
            more: i + 1 < rest.len(),
        });
    }
    Ok(out)
}

/// Split ACL entries (a contiguous run) into frames of at most `ACL_FRAME_BYTES` each.
pub fn acl_frames(entries: Vec<Entry>) -> Vec<Frame> {
    let mut out = Vec::new();
    let mut batch = Vec::new();
    let mut size = 0;
    for e in entries {
        let n = serde_json::to_vec(&e).map(|v| v.len()).unwrap_or(ACL_FRAME_BYTES);
        if size + n > ACL_FRAME_BYTES && !batch.is_empty() {
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
    /// New chain entries this step (the daemon pushes them to other sessions).
    pub acl_added: usize,
    /// Proposals newly queued here, to relay toward the sequencer through other sessions.
    pub relay: Vec<Proposal>,
    /// Refusals newly learned, to relay toward their proposers.
    pub refusals: Vec<ProposalRefusal>,
    pub refused: Vec<String>,
}

/// What a peer's hello said, as an answer needs it.
#[derive(Clone, Debug)]
struct PeerHello {
    heads: Heads,
    more: bool,
}

/// What one peer has spent of its per-minute budgets, each as (the minute by our clock, the
/// amount in it). A `Session` starts with a fresh one; the daemon keeps one per link and peer and
/// hands it to every frame of every session of that peer, so a reconnect or a second session
/// starts where the last left off (review finding R8-3).
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Budget {
    /// Frames of any kind the peer sent (review finding R9-2).
    frames: (u64, u32),
    /// ACL-side frames the peer sent (and evidence checks they caused, `EVIDENCE_CHECK_FRAMES`
    /// each).
    acl_rate: (u64, u32),
    /// ACL entry bytes we sent the peer.
    acl_sent: (u64, usize),
    /// Record-side frames the peer sent.
    rec_rate: (u64, u32),
    /// Record bytes we sent the peer in answers.
    rec_sent: (u64, usize),
    /// Record bytes the peer sent us that we looked at.
    rec_in: (u64, usize),
    /// Head claims (author, seq, the id the peer named) we answered with our record at that seq
    /// (review finding R9-4).
    conflicts: (u64, BTreeSet<(String, u64, String)>),
}

impl Budget {
    /// Whether anything was spent in the minute of `now` (an older budget is a fresh one).
    pub fn current(&self, now: u64) -> bool {
        let minute = now / 60;
        [
            self.frames.0,
            self.acl_rate.0,
            self.acl_sent.0,
            self.rec_rate.0,
            self.rec_sent.0,
            self.rec_in.0,
            self.conflicts.0,
        ]
        .contains(&minute)
    }
}

/// One sync session's state.
#[derive(Debug, Default)]
pub struct Session {
    pub peer: Option<String>,
    pub peer_heads: BTreeMap<String, u64>,
    pub synced: bool,
    /// The peer's chain tip as its hello named it.
    pub peer_tip: Option<AclPos>,
    /// A hello from a device we do not (yet) know as a member: answered only once ACL entries
    /// show it is one, never before.
    held: Option<PeerHello>,
    /// While the peer's record heads come in `heads` frames: the authors it has listed so far.
    paging: Option<BTreeSet<String>>,
    /// What the peer has spent of its budgets this minute. The daemon keeps it per link and peer
    /// across frames, so concurrent sessions and reconnects share it (review finding R8-3).
    pub budget: Budget,
    /// An `acl_want` of ours is not answered yet (its `acl_done` has not come).
    awaiting: bool,
    /// Our chain tip when we sent the outstanding (or last) want: the answer made progress only
    /// if the tip moved since (review finding R6-7).
    tip_at_ask: Option<AclPos>,
    /// While the peer pages its heads: whether an answer to a page was cut short.
    paging_cut: bool,
    /// A record `want` of ours is not answered yet (its `synced` has not come).
    rec_awaiting: bool,
    /// Since our last record `want` (or the session's start): records came, and some were stored.
    rec_got: bool,
    rec_progress: bool,
    /// Another want was due while one was outstanding: ask once it is answered, if it helped.
    rec_again: bool,
    /// The peer's budget cut an answer short and sent nothing, or records came past a gap that
    /// nothing in their frame explains: ask again at the next ping (review finding R9-1).
    rec_retry: bool,
    /// Records wait for a chain position we lacked (`Admit::Pending`): our chain tip then. Once
    /// it moves (the chain came through this session or another), the next ping asks for them
    /// again; a position that never comes asks nothing (review finding R9-1).
    rec_wait_tip: Option<AclPos>,
    /// An author was at its hourly quota here: when the quota admits another of its records. The
    /// first ping from then asks again (review finding R9-1).
    rec_quota_at: Option<u64>,
    /// Since our last record `want`: authors one of whose records waited, was over quota or was
    /// refused. Their later records are gaps that asking again does not close by itself.
    rec_blocked: BTreeSet<String>,
}

impl Session {
    pub fn new() -> Self {
        Self::default()
    }

    /// Handle one frame from the peer. `peer_device` is the key the transport authenticated.
    ///
    /// Membership is checked on every frame, so a device removed mid-session is dropped at its
    /// next frame. The only frames a device we do not know as a member may send are its hello
    /// (held, unanswered), its `heads` pages, ACL entries (which may show it is a member) with
    /// their `acl_done`, and pings. While halted, the chain's own frames (`acl_want`, `acl_done`,
    /// `evidence`) are taken from any device of the held tip (`may_sync_acl`), so evidence and the
    /// owner's takeover reach a device added past the prefix and travel on from it (review finding
    /// R7-2); records, heads and proposals still need `may_sync`.
    pub fn on_frame(&mut self, link: &mut Link, me: &Device, peer_device: &str, f: Frame, now: u64) -> Result<Outcome> {
        // Every frame counts first, before any lookup (review finding R9-2).
        let minute = now / 60;
        if self.budget.frames.0 != minute {
            self.budget.frames = (minute, 0);
        }
        self.budget.frames.1 += 1;
        if self.budget.frames.1 > MAX_FRAMES_PER_MIN {
            return Err(refused("too many frames this minute"));
        }
        let mut out = Outcome::default();
        let held_heads = matches!(f, Frame::Heads { .. } | Frame::AclDone { .. }) && self.held.is_some();
        let chain_frame = matches!(
            f,
            Frame::AclWant { .. } | Frame::AclDone { .. } | Frame::Evidence { .. }
        );
        if !matches!(f, Frame::Hello { .. } | Frame::Acl { .. } | Frame::Ping {})
            && !held_heads
            && !may_sync(link, peer_device)
        {
            if !may_sync_acl(link, peer_device) {
                return Err(refused("peer is not (or no longer) a member"));
            }
            // A device of the held tip that the halt leaves out: the chain's frames are taken,
            // anything else is let pass unanswered (a peer that is not halted answers our hello in
            // full), so the session lives on for the takeover.
            if !chain_frame {
                return Ok(out);
            }
        }
        match f {
            Frame::Hello {
                v,
                link: id,
                device,
                acl,
                heads,
                more,
            } => {
                if v != HELLO_VERSION || id != link.id() || device != peer_device {
                    return Err(refused("hello does not match this link or this connection"));
                }
                if self.peer.is_some() || self.held.is_some() {
                    return Err(refused("one hello per session"));
                }
                if heads.len() > MAX_HELLO_AUTHORS {
                    return Err(refused("hello lists more heads than one hello may"));
                }
                self.peer_tip = Some(acl);
                let hello = PeerHello { heads, more };
                if may_sync(link, peer_device) {
                    out.replies = self.answer_hello(link, peer_device, hello, now)?;
                } else {
                    // Its chain may show it is a member: ask for what it has that we lack. A device
                    // of our held tip that the halt leaves out gets our evidence too (R7-2).
                    out.replies.extend(self.want_toward(link));
                    if may_sync_acl(link, peer_device) {
                        out.replies.extend(evidence_frame(link));
                    }
                    self.held = Some(hello);
                }
            }
            Frame::Heads { heads, more } => {
                self.rec_frame(now)?;
                if heads.len() > MAX_AUTHORS_PER_FRAME {
                    return Err(refused("a heads frame lists too many authors"));
                }
                // A held hello (its sender not yet known as a member) keeps its pages with it.
                if let Some(h) = self.held.as_mut() {
                    if !h.more || h.heads.len() + heads.len() > MAX_HELD_AUTHORS {
                        return Err(refused("record heads that no hello announced"));
                    }
                    h.heads.extend(heads);
                    h.more = more;
                    return Ok(out);
                }
                let Some(listed) = self.paging.as_mut() else {
                    return Err(refused("record heads that no hello announced"));
                };
                listed.extend(heads.keys().cloned());
                for (a, h) in &heads {
                    let n = self.peer_heads.entry(a.clone()).or_insert(0);
                    *n = (*n).max(h.seq);
                }
                let page: BTreeSet<String> = heads.keys().cloned().collect();
                let theirs = seqs(&heads);
                let cut = self.answer_records(link, &theirs, |a| page.contains(a), &mut out.replies, now)?;
                self.paging_cut |= cut;
                out.replies.extend(self.conflicts(link, &heads, now)?);
                if !more {
                    let listed = self.paging.take().unwrap_or_default();
                    let cut =
                        self.answer_records(link, &BTreeMap::new(), |a| !listed.contains(a), &mut out.replies, now)?;
                    let more = std::mem::take(&mut self.paging_cut) || cut;
                    out.replies.push(Frame::Synced {
                        heads: heads_of(link)?,
                        more,
                    });
                }
            }
            Frame::Acl { entries } => {
                self.acl_frame(now)?;
                let first = entries.first().map(|e| e.seq);
                let r = link.add_acl(entries, now)?;
                self.charge_checks(r.checks, now)?;
                out.acl_added = r.added;
                if let Some(why) = &r.refused {
                    link.store.refusal(peer_device, why, now)?;
                    out.refused.push(why.clone());
                }
                if r.equivocation {
                    out.replies.extend(evidence_frame(link));
                }
                if !may_sync_acl(link, peer_device) && self.held.is_none() {
                    return Err(refused("peer is not (or no longer) a member"));
                }
                match r.need_from {
                    // The run does not link here: ask from further back (never forever: each
                    // ask starts lower than the run that did not link).
                    Some(from) if first.is_none_or(|f| from < f) => {
                        let to = self.peer_tip.as_ref().map_or(from + 1, |t| t.seq.max(from + 1));
                        out.replies.push(self.ask(link, from, to));
                    }
                    Some(_) => {}
                    // An unasked push that left us behind: ask for the rest. While a want is
                    // outstanding its `acl_done` decides; and never after a frame that added
                    // nothing (a halted chain, a stale branch).
                    None if r.added > 0 => out.replies.extend(self.want_toward(link)),
                    None => {}
                }
                // Records that waited for a chain position may read now. Their authors' later
                // records came as gaps behind them: ask for those at once (review finding R9-1).
                let woke = link.retry_pending(me, now)?;
                if !woke.is_empty() && may_sync(link, peer_device) {
                    self.rec_progress = true;
                    self.rec_wait_tip = None;
                    out.replies.extend(self.want(link)?);
                }
                out.stored.extend(woke);
                if may_sync(link, peer_device)
                    && let Some(hello) = self.held.take()
                {
                    out.replies.extend(self.answer_hello(link, peer_device, hello, now)?);
                }
            }
            Frame::AclWant { from, to } => {
                self.acl_frame(now)?;
                let minute = now / 60;
                if self.budget.acl_sent.0 != minute {
                    self.budget.acl_sent = (minute, 0);
                }
                let left = ACL_BYTES_PER_MIN.saturating_sub(self.budget.acl_sent.1);
                if left > 0 {
                    // Exactly the range asked for, and never past the session's budget.
                    let entries = link.acl.range(from, to, left);
                    let n: usize = entries
                        .iter()
                        .map(|e| crate::codec::canonical(e).map_or(0, |b| b.len()))
                        .sum();
                    self.budget.acl_sent.1 += n;
                    let upto = entries.last().map_or(from, |e| e.seq);
                    out.replies.extend(acl_frames(entries));
                    out.replies.push(Frame::AclDone { upto });
                } else {
                    out.replies.push(Frame::AclDone { upto: from });
                }
            }
            Frame::AclDone { .. } => {
                self.acl_frame(now)?;
                // Our want is answered. Ask for more only if our tip moved since we asked: entries
                // we refused are no progress, however far `upto` reached (review finding R6-7). A
                // want the peer's budget cut short is asked again at its next ping.
                let progress = self.awaiting && self.tip_at_ask.as_ref() != Some(&link.acl.tip());
                self.awaiting = false;
                if progress {
                    out.replies.extend(self.want_toward(link));
                }
            }
            Frame::Propose { proposal } => {
                self.acl_frame(now)?;
                match link.offer_from(me, &proposal, peer_device, now) {
                    Ok(Offered::Included(e)) => {
                        out.acl_added += 1;
                        out.replies.push(Frame::Acl { entries: vec![e] });
                    }
                    Ok(Offered::Refused(r)) => out.replies.push(Frame::Refusal { refusal: r }),
                    Ok(Offered::Queued) => out.relay.push(proposal),
                    Ok(Offered::Known) => {}
                    Err(e) => {
                        link.store.refusal(peer_device, &e.to_string(), now)?;
                        out.refused.push(e.to_string());
                    }
                }
            }
            Frame::Refusal { refusal } => {
                self.acl_frame(now)?;
                match link.take_refusal(me, &refusal) {
                    Ok(true) => out.refusals.push(refusal),
                    Ok(false) => {}
                    Err(e) => {
                        link.store.refusal(peer_device, &e.to_string(), now)?;
                        out.refused.push(e.to_string());
                    }
                }
            }
            Frame::Evidence { ours, theirs } => {
                self.acl_frame(now)?;
                let found = link.acl.note_evidence(&ours, &theirs)?;
                let r = link.add_acl(Vec::new(), now)?;
                self.charge_checks(r.checks, now)?;
                if found {
                    out.refused.push("the sequencer equivocated".into());
                }
            }
            Frame::Records { records } => {
                let minute = now / 60;
                if self.budget.rec_in.0 != minute {
                    self.budget.rec_in = (minute, 0);
                }
                let mut gap = false;
                let mut progress = false;
                let mut waiting = false;
                let mut quota: Option<u64> = None;
                for r in records {
                    // Past this minute's budget, the rest is not looked at; ask again at the next
                    // ping (each record costs a signature check, duplicates included).
                    let n = r.frame_cost();
                    if self.budget.rec_in.1 > 0 && self.budget.rec_in.1.saturating_add(n) > RECORD_BYTES_IN_PER_MIN {
                        self.rec_retry = true;
                        break;
                    }
                    self.budget.rec_in.1 = self.budget.rec_in.1.saturating_add(n);
                    self.rec_got = true;
                    match link.receive(me, &r, now)? {
                        Admit::Stored { .. } => {
                            progress = true;
                            let n = self.peer_heads.entry(r.author.clone()).or_insert(0);
                            *n = (*n).max(r.seq);
                            out.stored.push(r);
                        }
                        Admit::Duplicate => {}
                        Admit::Pending => {
                            waiting = true;
                            self.block(&r.author);
                        }
                        Admit::OverQuota { author, until } => {
                            quota = Some(quota.map_or(until, |q| q.min(until)));
                            self.block(&author);
                        }
                        Admit::Gap { author, .. } => gap |= !self.rec_blocked.contains(&author),
                        Admit::Refused(why) => {
                            self.block(&r.author);
                            link.store.refusal(peer_device, &why, now)?;
                            out.refused.push(why);
                        }
                    }
                }
                self.rec_progress |= progress;
                // A gap that nothing in this frame explains (records pushed past ones we lack):
                // ask at once after progress, else at the next ping, one bounded ask each
                // (review finding R9-1). A gap behind a refused record is not asked for: that
                // would resend the same batch for ever.
                if gap {
                    if progress {
                        out.replies.extend(self.want(link)?);
                    } else {
                        self.rec_retry = true;
                    }
                }
                // Over quota: ask again once the quota admits more, not sooner (R9-1).
                if let Some(t) = quota {
                    self.rec_quota_at = Some(self.rec_quota_at.map_or(t, |q| q.min(t)));
                }
                // A record waits for a chain position we have not reached: ask the peer, and ask
                // for the records again once our tip moves (R9-1).
                if waiting {
                    self.rec_wait_tip = Some(link.acl.tip());
                    if !self.awaiting
                        && let Some((from, to)) = link.wanted_acl()
                    {
                        out.replies.push(self.ask(link, from, to));
                    }
                }
            }
            Frame::Want { heads } => {
                self.rec_frame(now)?;
                let more = self.answer_records(link, &seqs(&heads), |_| true, &mut out.replies, now)?;
                out.replies.extend(self.conflicts(link, &heads, now)?);
                out.replies.push(Frame::Synced {
                    heads: heads_of(link)?,
                    more,
                });
            }
            Frame::Synced { heads, more } => {
                self.rec_frame(now)?;
                self.synced = true;
                out.replies.extend(self.conflicts(link, &heads, now)?);
                for (a, h) in heads {
                    let n = self.peer_heads.entry(a).or_insert(0);
                    *n = (*n).max(h.seq);
                }
                // An answer is complete. If it was cut short (or a want waited for it), ask for the
                // rest now when it helped, at the next ping when it brought nothing (the peer's
                // budget for this minute is spent), and not at all when what came was refused (as
                // for a gap, that would resend the same batch for ever).
                self.rec_awaiting = false;
                if more || std::mem::take(&mut self.rec_again) {
                    if self.rec_progress {
                        out.replies.extend(self.want(link)?);
                    } else if !self.rec_got {
                        self.rec_retry = true;
                    }
                }
            }
            Frame::Advert { advert } => {
                self.rec_frame(now)?;
                if check_advert(link, &advert, now)? == AdvertSays::Behind {
                    out.replies.extend(self.want(link)?);
                }
            }
            // A live session's keepalive: also when a record want is asked again, one at most:
            // after an answer the peer's budget cut short, a gap, records that waited for a chain
            // position once our tip moved, or an hourly quota once it admits more (review
            // findings R8-2, R9-1).
            Frame::Ping {} => {
                if may_sync_acl(link, peer_device) || self.held.is_some() {
                    out.replies.extend(self.want_toward(link));
                }
                if may_sync(link, peer_device) && !self.rec_awaiting {
                    let moved = self.rec_wait_tip.as_ref().is_some_and(|t| *t != link.acl.tip());
                    let quota = self.rec_quota_at.is_some_and(|t| now >= t);
                    if moved {
                        self.rec_wait_tip = None;
                    }
                    if quota {
                        self.rec_quota_at = None;
                    }
                    if std::mem::take(&mut self.rec_retry) || moved || quota {
                        out.replies.extend(self.want(link)?);
                    }
                }
            }
            Frame::JoinHello { .. } | Frame::Join { .. } => {
                return Err(refused("join frames belong to a join session"));
            }
            Frame::Bye { .. } => {}
        }
        Ok(out)
    }

    /// An `acl_want`, now outstanding.
    fn ask(&mut self, link: &Link, from: u64, to: u64) -> Frame {
        self.awaiting = true;
        self.tip_at_ask = Some(link.acl.tip());
        Frame::AclWant { from, to }
    }

    /// An `acl_want` toward the peer's chain tip, when none is outstanding and the peer is ahead
    /// of us (a longer chain of our term, or a later term) or its tip conflicts with ours at one
    /// position.
    fn want_toward(&mut self, link: &Link) -> Option<Frame> {
        if self.awaiting {
            return None;
        }
        let theirs = self.peer_tip.clone()?;
        let ours = link.acl.tip();
        if link.acl.is_empty() {
            return Some(self.ask(link, 0, theirs.seq));
        }
        if theirs.hash == ours.hash {
            return None;
        }
        if theirs.seq > ours.seq && theirs.term >= ours.term {
            return Some(self.ask(link, ours.seq, theirs.seq));
        }
        // A later term below our tip, or another entry at our tip's position: ask for its tip
        // entry; if it does not link, the answer makes us ask further back.
        if theirs.term > ours.term || (theirs.term == ours.term && theirs.seq == ours.seq) {
            return Some(self.ask(link, theirs.seq.saturating_sub(1), theirs.seq));
        }
        None
    }

    /// Our answer to a member's hello: a want toward its chain if it is ahead, our queued
    /// proposals, evidence if we are halted, the records it lacks and those where our heads
    /// disagree, then `synced` (after its last `heads` frame, when it said `more`).
    fn answer_hello(&mut self, link: &mut Link, peer: &str, hello: PeerHello, now: u64) -> Result<Vec<Frame>> {
        self.peer = Some(peer.to_owned());
        self.peer_heads = seqs(&hello.heads);
        let mut out: Vec<Frame> = self.want_toward(link).into_iter().collect();
        out.extend(evidence_frame(link));
        for p in link.outstanding(MAX_PROPOSALS_AT_HELLO)? {
            out.push(Frame::Propose { proposal: p });
        }
        let theirs = self.peer_heads.clone();
        if hello.more {
            // Only the authors it listed so far: the others come in its `heads` frames.
            let listed: BTreeSet<String> = hello.heads.keys().cloned().collect();
            self.paging_cut = self.answer_records(link, &theirs, |a| listed.contains(a), &mut out, now)?;
            out.extend(self.conflicts(link, &hello.heads, now)?);
            self.paging = Some(listed);
            return Ok(out);
        }
        let more = self.answer_records(link, &theirs, |_| true, &mut out, now)?;
        out.extend(self.conflicts(link, &hello.heads, now)?);
        out.push(Frame::Synced {
            heads: heads_of(link)?,
            more,
        });
        Ok(out)
    }

    /// The records the peer lacks given `theirs`, for the authors `only` selects, within one pass
    /// and what is left of this minute's `RECORD_BYTES_PER_MIN` (review finding R8-2), appended
    /// to `out` as frames. Returns whether the answer was cut short.
    fn answer_records(
        &mut self,
        link: &Link,
        theirs: &BTreeMap<String, u64>,
        only: impl Fn(&str) -> bool,
        out: &mut Vec<Frame>,
        now: u64,
    ) -> Result<bool> {
        let minute = now / 60;
        if self.budget.rec_sent.0 != minute {
            self.budget.rec_sent = (minute, 0);
        }
        let left = RECORD_BYTES_PER_MIN.saturating_sub(self.budget.rec_sent.1);
        let (records, cut) = link.missing_for_authors(theirs, MAX_RECORDS_PER_PASS, left, only)?;
        self.budget.rec_sent.1 += records.iter().map(Record::frame_cost).sum::<usize>();
        out.extend(record_frames(records));
        Ok(cut)
    }

    /// A record `want` for everything after our heads, unless one is outstanding (then it is
    /// asked once that one is answered, if the answer helped).
    fn want(&mut self, link: &Link) -> Result<Option<Frame>> {
        if self.rec_awaiting {
            self.rec_again = true;
            return Ok(None);
        }
        self.rec_awaiting = true;
        self.rec_got = false;
        self.rec_progress = false;
        self.rec_blocked.clear();
        Ok(Some(Frame::Want { heads: heads_of(link)? }))
    }

    /// Note an author whose record waited, was over quota or was refused since our last want. The
    /// set is capped (a refused record may name any author): past it, a gap is asked for again
    /// at the next ping, one bounded ask.
    fn block(&mut self, author: &str) {
        if self.rec_blocked.len() < MAX_HELD_AUTHORS {
            self.rec_blocked.insert(author.to_owned());
        }
    }

    /// Count one record-side frame from the peer against `MAX_RECORD_FRAMES_PER_MIN` (review
    /// finding R8-2).
    fn rec_frame(&mut self, now: u64) -> Result<()> {
        let minute = now / 60;
        if self.budget.rec_rate.0 != minute {
            self.budget.rec_rate = (minute, 0);
        }
        self.budget.rec_rate.1 += 1;
        if self.budget.rec_rate.1 > MAX_RECORD_FRAMES_PER_MIN {
            return Err(refused("too many record frames this minute"));
        }
        Ok(())
    }

    /// Count one ACL-side frame from the peer against `MAX_ACL_FRAMES_PER_MIN`.
    fn acl_frame(&mut self, now: u64) -> Result<()> {
        let minute = now / 60;
        if self.budget.acl_rate.0 != minute {
            self.budget.acl_rate = (minute, 0);
        }
        self.budget.acl_rate.1 += 1;
        if self.budget.acl_rate.1 > MAX_ACL_FRAMES_PER_MIN {
            return Err(refused("too many ACL frames this minute"));
        }
        Ok(())
    }

    /// Charge `checks` evidence checks the peer's frames made us run against the same budget
    /// (review finding R7-1). Past it, the session ends, like any frame past the budget.
    fn charge_checks(&mut self, checks: u32, now: u64) -> Result<()> {
        if checks == 0 {
            return Ok(());
        }
        let minute = now / 60;
        if self.budget.acl_rate.0 != minute {
            self.budget.acl_rate = (minute, 0);
        }
        self.budget.acl_rate.1 = self
            .budget
            .acl_rate
            .1
            .saturating_add(checks.saturating_mul(EVIDENCE_CHECK_FRAMES));
        if self.budget.acl_rate.1 > MAX_ACL_FRAMES_PER_MIN {
            return Err(refused("too many evidence checks this minute"));
        }
        Ok(())
    }

    /// Heads the peer reports that name another record than the one we hold at that seq: the
    /// author signed two records at one seq. We send ours (the peer's own admission check then
    /// freezes the author) and ask for theirs from the seq before (ours then does). Unsigned head
    /// claims alone never freeze anyone; only the two signed records do.
    ///
    /// The records sent count against `RECORD_BYTES_PER_MIN` like any answer, and none is sent
    /// once it is spent. Each claim (author, seq, the id the peer names) is answered at most once
    /// in the budget's minute, across the peer's sessions, and at most `MAX_CONFLICTS_PER_MIN`
    /// claims a minute (review finding R9-4): a claim with a made-up id cost a record, outside
    /// every budget.
    fn conflicts(&mut self, link: &Link, theirs: &Heads, now: u64) -> Result<Vec<Frame>> {
        let minute = now / 60;
        if self.budget.rec_sent.0 != minute {
            self.budget.rec_sent = (minute, 0);
        }
        if self.budget.conflicts.0 != minute {
            self.budget.conflicts = (minute, BTreeSet::new());
        }
        let mut ours = Vec::new();
        let mut want: Option<Heads> = None;
        let mut n = 0;
        for (author, h) in theirs {
            if n >= MAX_CONFLICTS_PER_FRAME
                || self.budget.rec_sent.1 >= RECORD_BYTES_PER_MIN
                || self.budget.conflicts.1.len() >= MAX_CONFLICTS_PER_MIN
            {
                break;
            }
            // A record id is 64 hex digits: anything else names no record, and is not kept.
            if h.seq == 0 || h.id.len() != 64 {
                continue;
            }
            let Some(mine) = link.store.record_at(author, h.seq)? else {
                continue;
            };
            if mine == h.id || link.store.frozen(author)? {
                continue;
            }
            if !self.budget.conflicts.1.insert((author.clone(), h.seq, h.id.clone())) {
                continue;
            }
            n += 1;
            let rs = link.store.range(author, h.seq - 1, h.seq, 1)?;
            self.budget.rec_sent.1 += rs.iter().map(Record::frame_cost).sum::<usize>();
            ours.extend(rs);
            let before = link.store.record_at(author, h.seq - 1)?.unwrap_or_default();
            let w = match want.as_mut() {
                Some(w) => w,
                None => want.insert(heads_of(link)?),
            };
            w.insert(
                author.clone(),
                HeadRef {
                    seq: h.seq - 1,
                    id: before,
                },
            );
        }
        let mut out = record_frames(ours);
        if let Some(heads) = want {
            out.push(Frame::Want { heads });
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

/// The evidence frame of a halted chain, if it is halted.
fn evidence_frame(link: &Link) -> Option<Frame> {
    link.acl.halt().map(|h| Frame::Evidence {
        ours: h.ours.clone(),
        theirs: h.theirs.clone(),
    })
}

/// Whether `device` may hold a sync session with us on this link right now: records, heads and
/// proposals. While halted, this is the narrowed state's answer (`AclChain::state`).
pub fn may_sync(link: &Link, device: &str) -> bool {
    link.acl.sync_devices().contains(device)
}

/// Whether `device` may trade the chain's own frames with us (`acl`, `acl_want`, `acl_done`,
/// `evidence`): a device of the held tip, halted or not (review finding R7-2). A halt narrows what
/// a replica grants, but a device the held tip lists must still reach, and be reached by, the
/// evidence and the owner's takeover. When not halted this is `may_sync`.
pub fn may_sync_acl(link: &Link, device: &str) -> bool {
    link.acl.held_sync_devices().contains(device)
}

/// What a verified head advert tells us.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AdvertSays {
    /// Nothing new (or not about this link, or not from one of its devices).
    Nothing,
    /// The author is ahead of us: sync.
    Behind,
    /// The author signed this advert for a seq where we hold another of its records: two signed
    /// statements for one seq. The author is now frozen and an alarm raised.
    Equivocation,
}

/// Check one head advert (from a session or from gossip) against what we hold.
pub fn check_advert(link: &Link, advert: &HeadAdvert, now: u64) -> Result<AdvertSays> {
    advert.verify()?;
    if advert.link != link.id() || !link.state().devices.contains_key(&advert.author) {
        return Ok(AdvertSays::Nothing);
    }
    if let Some(mine) = link.store.record_at(&advert.author, advert.seq)?
        && mine != advert.id
    {
        if !link.store.frozen(&advert.author)? {
            let detail = format!("advert names {} at seq {} but we hold {mine}", advert.id, advert.seq);
            link.store.freeze(&advert.author, &detail, now)?;
            link.store.alarm("equivocation", &advert.author, &detail, now)?;
        }
        return Ok(AdvertSays::Equivocation);
    }
    let have = link.store.head(&advert.author)?.map(|h| h.0).unwrap_or(0);
    Ok(if have < advert.seq {
        AdvertSays::Behind
    } else {
        AdvertSays::Nothing
    })
}

fn join_hello_bytes(link: &str, invite: &str, device: &str) -> Result<Vec<u8>> {
    crate::codec::jcs(&serde_json::json!({"v": HELLO_VERSION, "link": link, "invite": invite, "device": device}))
}

/// The joiner's first frame: proves it holds the invite secret, bound to this connection.
pub fn join_hello(link: &str, me: &Device, ticket: &InviteTicket) -> Result<Frame> {
    let key = crate::acl::invite_key(&ticket.secret);
    let proof = crate::crypto::sign(
        &key,
        "join-hello",
        &join_hello_bytes(link, &ticket.entry, &me.id_hex())?,
    );
    Ok(Frame::JoinHello {
        v: HELLO_VERSION,
        link: link.to_owned(),
        invite: ticket.entry.clone(),
        proof: crate::codec::b64(&proof),
    })
}

/// The inviter's side of one join stream. A `join_hello` whose proof holds must come first, and
/// the `join` that follows must use the same invite; a stream carries at most one of each.
#[derive(Debug, Default)]
pub struct JoinDoor {
    invite: Option<String>,
    joined: bool,
    /// A join this door handed on toward the sequencer, by proposal id.
    pub queued: Option<String>,
}

impl JoinDoor {
    pub fn new() -> Self {
        Self::default()
    }

    /// One join frame. A join that this replica cannot include itself (it does not sequence the
    /// link) is queued for the sequencer: the reply is then empty, and `poll` gives the chain
    /// once the join is included.
    pub fn on_frame(
        &mut self,
        link: &mut Link,
        me: &Device,
        peer_device: &str,
        f: Frame,
        now: u64,
    ) -> Result<Vec<Frame>> {
        match f {
            Frame::JoinHello {
                v,
                link: id,
                invite,
                proof,
            } => {
                if self.invite.is_some() {
                    return Err(refused("one join_hello per join stream"));
                }
                let key = link
                    .invite_live(&invite, now, Some(peer_device))
                    .filter(|_| v == HELLO_VERSION && id == link.id())
                    .ok_or_else(|| refused("no live invite with that key for this link"))?;
                let msg = join_hello_bytes(&id, &invite, peer_device)?;
                crate::crypto::verify(
                    &crate::codec::unhex::<32>(&key)?,
                    "join-hello",
                    &msg,
                    &crate::codec::unb64(&proof)?,
                )?;
                self.invite = Some(invite);
                Ok(chain_reply(link))
            }
            Frame::Join { proposal } => {
                let Some(hello) = self.invite.clone() else {
                    return Err(refused("a join needs a verified join_hello first"));
                };
                if self.joined {
                    return Err(refused("one join per join stream"));
                }
                if proposal.kind != "join" || proposal.proposer.device != peer_device || proposal.link != link.id() {
                    return Err(refused("expected this connection's own join proposal"));
                }
                let crate::acl::Op::Join(j) = proposal.parsed()? else {
                    return Err(refused("expected a join proposal"));
                };
                if j.invite != hello {
                    return Err(refused("the join uses another invite than the join_hello"));
                }
                let Some(key) = link.invite_live(&j.invite, now, None) else {
                    return Err(refused("no live invite with that key for this link"));
                };
                // Authenticate before anything is kept: the proposal's own signature, and the
                // invite key's proof over this link, this invite, this device and this nonce.
                proposal.verify_signature()?;
                crate::crypto::verify(
                    &crate::codec::unhex::<32>(&key)?,
                    "join",
                    &crate::acl::join_proof_bytes(
                        link.id(),
                        &j.invite,
                        &proposal.proposer.root,
                        &proposal.proposer.device,
                        &proposal.nonce,
                    )?,
                    &crate::codec::unb64(&j.proof)?,
                )?;
                self.joined = true;
                let id = proposal.id()?;
                match link.offer(me, &proposal, now)? {
                    Offered::Included(_) => {
                        link.upkeep(me, now)?;
                        Ok(chain_reply(link))
                    }
                    Offered::Refused(r) => Err(refused(format!("join refused: {}", r.why))),
                    Offered::Queued | Offered::Known => {
                        self.queued = Some(id);
                        Ok(self.poll(link).unwrap_or(Ok(Vec::new()))?)
                    }
                }
            }
            _ => Err(refused("expected a join frame")),
        }
    }

    /// For a join queued toward the sequencer: the reply once it is included (the chain, then
    /// `synced`), or a `bye` once it is refused; `None` while it waits.
    pub fn poll(&self, link: &Link) -> Option<Result<Vec<Frame>>> {
        let id = self.queued.as_deref()?;
        if link.acl.included(id).is_some() {
            return Some(Ok(chain_reply(link)));
        }
        match link.refusal_of(id) {
            Ok(Some(r)) => Some(Ok(vec![Frame::Bye {
                reason: format!("refused: {}", r.why),
            }])),
            Ok(None) => None,
            Err(e) => Some(Err(e)),
        }
    }
}

/// The whole chain, then `synced`: what a joiner verifies and adopts.
fn chain_reply(link: &Link) -> Vec<Frame> {
    let mut out = acl_frames(link.acl.all());
    out.push(Frame::Synced {
        heads: BTreeMap::new(),
        more: false,
    });
    out
}

/// The joiner's side: a join proposal against the inviter's chain, includable for
/// `acl::PROPOSAL_TTL_S` after `now`.
pub fn join_proposal(entries: &[Entry], me: &Device, ticket: &InviteTicket, label: &str, now: u64) -> Result<Proposal> {
    let chain = chain_of(entries)?;
    if chain.state().devices.contains_key(&me.id_hex()) {
        return Err(refused("this device is already in that link's chain"));
    }
    let t = chain.tip();
    crate::acl::make_join(
        me,
        ticket,
        chain.link_id(),
        crate::acl::Base {
            term: t.term,
            seq: t.seq,
        },
        label,
        now.saturating_add(crate::acl::PROPOSAL_TTL_S),
    )
}

/// A chain from entries handed over by a peer (checked like any other).
pub fn chain_of(entries: &[Entry]) -> Result<crate::acl::AclChain> {
    let mut chain = crate::acl::AclChain::new();
    let r = chain.insert(entries.to_vec(), None);
    if chain.is_empty() {
        return Err(refused(
            r.refused.unwrap_or_else(|| "no genesis among the entries".into()),
        ));
    }
    Ok(chain)
}

/// The joiner's side, checked against the invite code first: the chain is the link the code
/// names (its genesis hashes to `code.link`), and the fleet that published the invite has the
/// fingerprint the code carries. Returns the proposal and the inviter's root.
pub fn join_proposal_for(
    entries: &[Entry],
    me: &Device,
    code: &crate::invite::InviteCode,
    label: &str,
    now: u64,
) -> Result<(Proposal, String)> {
    let chain = chain_of(entries)?;
    let inviter = code.check_log(chain.state())?;
    let p = join_proposal(entries, me, &code.ticket()?, label, now)?;
    Ok((p, inviter))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::acl::{Policy, Role};
    use crate::codec::hex;
    use crate::identity::{fleet_fingerprint, new_phrase, root_from_phrase};
    use crate::invite::InviteCode;
    use crate::record::Body;

    const T0: u64 = 10_000;

    fn device(label: &str) -> Device {
        Device::create(&root_from_phrase(&new_phrase()).unwrap(), label, false, T0 - 10).unwrap()
    }

    fn entries_of(frames: Vec<Frame>) -> Vec<Entry> {
        assert!(matches!(frames.last(), Some(Frame::Synced { .. })), "{frames:?}");
        frames
            .into_iter()
            .flat_map(|f| match f {
                Frame::Acl { entries } => entries,
                _ => vec![],
            })
            .collect()
    }

    /// `guest` joins `host`'s link through one join stream, with an invite `host` (the
    /// sequencer) publishes.
    fn join(host: &mut Link, hdev: &Device, guest: &Device, role: Role, now: u64) -> Link {
        let secret = host.invite(hdev, role, 3600, true, false, now).unwrap();
        let gid = guest.id_hex();
        let mut door = JoinDoor::new();
        let hello = join_hello(host.id(), guest, &secret).unwrap();
        let entries = entries_of(door.on_frame(host, hdev, &gid, hello, now).unwrap());
        let proposal = join_proposal(&entries, guest, &secret, &guest.cert.label, now).unwrap();
        let entries = entries_of(door.on_frame(host, hdev, &gid, Frame::Join { proposal }, now).unwrap());
        Link::adopt(None, entries, now).unwrap()
    }

    /// Run a session between two links until neither has anything left to say.
    fn sync_pair(a: &mut Link, ad: &Device, b: &mut Link, bd: &Device, now: u64) {
        let (mut sa, mut sb) = (Session::new(), Session::new());
        let mut to_b = hello(a, ad).unwrap();
        let mut to_a = hello(b, bd).unwrap();
        for _ in 0..50 {
            if to_a.is_empty() && to_b.is_empty() {
                return;
            }
            for f in std::mem::take(&mut to_b) {
                let f = decode(&encode(&f).unwrap()[4..]).unwrap();
                to_a.extend(sb.on_frame(b, bd, &ad.id_hex(), f, now).unwrap().replies);
            }
            for f in std::mem::take(&mut to_a) {
                let f = decode(&encode(&f).unwrap()[4..]).unwrap();
                to_b.extend(sa.on_frame(a, ad, &bd.id_hex(), f, now).unwrap().replies);
            }
        }
        panic!("sync did not settle");
    }

    fn note(text: &str) -> Body {
        Body {
            kind: "note".into(),
            seat: "claude".into(),
            to: "@any/codex".into(),
            content: text.into(),
            sent_at: T0,
            ..Body::default()
        }
    }

    fn code_for(link: &Link, inviter: &Device, secret: &InviteTicket, fingerprint_of: &str) -> InviteCode {
        InviteCode {
            v: 1,
            link: link.id().to_owned(),
            name: link.name().to_owned(),
            secret: hex(&secret.secret),
            invite: secret.entry.clone(),
            node: inviter.id_hex(),
            relay: None,
            addrs: vec![],
            fingerprint: fleet_fingerprint(&crate::codec::unhex::<32>(fingerprint_of).unwrap()),
        }
    }

    #[test]
    fn a_join_checks_the_link_id_and_the_fingerprint_of_the_fleet_that_invited() {
        let (ad, bd, cd) = (device("a"), device("b"), device("c"));
        let mut a = Link::create(None, &ad, "p", "fleet-a", Policy::default(), T0).unwrap();
        let mut b = join(&mut a, &ad, &bd, Role::Admin, T0 + 1);
        // B, an admin but not the sequencer, invites C: a proposal the owner includes.
        let secret = b.invite(&bd, Role::Writer, 3600, true, false, T0 + 2).unwrap();
        sync_pair(&mut a, &ad, &mut b, &bd, T0 + 2);
        assert!(
            a.state().invites.contains_key(&secret.entry),
            "the owner included B's invite"
        );
        let log = b.acl.all();
        let good = code_for(&b, &bd, &secret, bd.root_hex());
        let (_, inviter) = join_proposal_for(&log, &cd, &good, "c", T0).unwrap();
        assert_eq!(inviter, bd.root_hex(), "the inviter is B's fleet, not the owner");
        let owners = code_for(&b, &bd, &secret, ad.root_hex());
        let err = join_proposal_for(&log, &cd, &owners, "c", T0).unwrap_err();
        assert!(err.to_string().contains("fingerprint"), "{err}");
        let mut other = good.clone();
        other.link = "ab".repeat(32);
        let err = join_proposal_for(&log, &cd, &other, "c", T0).unwrap_err();
        assert!(err.to_string().contains("another link"), "{err}");
        let mut stray = good.clone();
        stray.secret = hex(&[9u8; 32]);
        assert!(join_proposal_for(&log, &cd, &stray, "c", T0).is_err());
    }

    #[test]
    fn the_join_door_wants_a_hello_and_a_live_inviter() {
        let (ad, bd, gd) = (device("a"), device("b"), device("guest"));
        let mut a = Link::create(None, &ad, "p", "fleet-a", Policy::default(), T0).unwrap();
        let secret = a.invite(&ad, Role::Writer, 3600, true, false, T0).unwrap();
        let gid = gd.id_hex();
        let proposal = join_proposal(&a.acl.all(), &gd, &secret, "guest", T0).unwrap();
        let before = a.acl.len();
        // A join with no verified hello on its stream is refused, though its proof holds.
        let err = JoinDoor::new()
            .on_frame(
                &mut a,
                &ad,
                &gid,
                Frame::Join {
                    proposal: proposal.clone(),
                },
                T0 + 1,
            )
            .unwrap_err();
        assert!(err.to_string().contains("join_hello"), "{err}");
        assert_eq!(a.acl.len(), before, "nothing was stored");
        // Another connection's join is refused.
        let mut door = JoinDoor::new();
        let other = device("other");
        let hello = join_hello(a.id(), &other, &secret).unwrap();
        door.on_frame(&mut a, &ad, &other.id_hex(), hello, T0 + 1).unwrap();
        assert!(
            door.on_frame(
                &mut a,
                &ad,
                &other.id_hex(),
                Frame::Join {
                    proposal: proposal.clone()
                },
                T0 + 1
            )
            .is_err()
        );
        // A forged proof is refused at the door, and nothing is stored.
        let mut door = JoinDoor::new();
        let hello = join_hello(a.id(), &gd, &secret).unwrap();
        door.on_frame(&mut a, &ad, &gid, hello, T0 + 3).unwrap();
        let wrong = InviteTicket {
            secret: [7u8; 32],
            entry: secret.entry.clone(),
        };
        let forged = join_proposal(&a.acl.all(), &gd, &wrong, "guest", T0).unwrap();
        assert!(
            door.on_frame(&mut a, &ad, &gid, Frame::Join { proposal: forged }, T0 + 3)
                .is_err()
        );
        assert_eq!(a.acl.len(), before, "nothing was stored");
        // An invite whose inviter is no longer an admin is dead at the door, at the hello.
        let mut b = join(&mut a, &ad, &bd, Role::Admin, T0 + 4);
        let b_secret = b.invite(&bd, Role::Writer, 3600, true, false, T0 + 5).unwrap();
        sync_pair(&mut a, &ad, &mut b, &bd, T0 + 5);
        let hello = join_hello(a.id(), &gd, &b_secret).unwrap();
        JoinDoor::new()
            .on_frame(&mut a, &ad, &gid, hello.clone(), T0 + 6)
            .unwrap();
        a.set_role(&ad, bd.root_hex(), Role::Writer, T0 + 6).unwrap();
        assert!(JoinDoor::new().on_frame(&mut a, &ad, &gid, hello, T0 + 7).is_err());
    }

    #[test]
    fn a_join_handed_to_an_admin_that_does_not_sequence_waits_for_the_sequencer() {
        let (ad, bd, gd) = (device("a"), device("b"), device("guest"));
        let mut a = Link::create(None, &ad, "p", "fleet-a", Policy::default(), T0).unwrap();
        let mut b = join(&mut a, &ad, &bd, Role::Admin, T0 + 1);
        let secret = b.invite(&bd, Role::Writer, 3600, true, false, T0 + 2).unwrap();
        sync_pair(&mut a, &ad, &mut b, &bd, T0 + 2);
        let gid = gd.id_hex();
        let mut door = JoinDoor::new();
        let hello = join_hello(b.id(), &gd, &secret).unwrap();
        let entries = entries_of(door.on_frame(&mut b, &bd, &gid, hello, T0 + 3).unwrap());
        let proposal = join_proposal(&entries, &gd, &secret, "guest", T0).unwrap();
        let reply = door
            .on_frame(&mut b, &bd, &gid, Frame::Join { proposal }, T0 + 3)
            .unwrap();
        assert!(reply.is_empty(), "B queued the join for the sequencer");
        assert!(door.poll(&b).is_none());
        // B's next session with the sequencer carries it; the sequencer includes it.
        sync_pair(&mut b, &bd, &mut a, &ad, T0 + 4);
        let entries = entries_of(door.poll(&b).unwrap().unwrap());
        let g = Link::adopt(None, entries, T0 + 5).unwrap();
        assert!(g.state().active_device(&gid).is_some());
        // Later, the joiner may fetch the chain again with the same code (its join used it).
        let mut again = JoinDoor::new();
        let hello = join_hello(b.id(), &gd, &secret).unwrap();
        assert!(again.on_frame(&mut b, &bd, &gid, hello, T0 + 6).is_ok());
    }

    /// A, B and C in one link, all holding the same chain.
    fn trio() -> ((Link, Device), (Link, Device), (Link, Device)) {
        let (ad, bd, cd) = (device("a"), device("b"), device("c"));
        let mut a = Link::create(None, &ad, "p", "fleet-a", Policy::default(), T0).unwrap();
        let mut b = join(&mut a, &ad, &bd, Role::Writer, T0 + 1);
        let mut c = join(&mut a, &ad, &cd, Role::Writer, T0 + 2);
        sync_pair(&mut a, &ad, &mut b, &bd, T0 + 3);
        sync_pair(&mut a, &ad, &mut c, &cd, T0 + 3);
        ((a, ad), (b, bd), (c, cd))
    }

    #[test]
    fn two_records_at_one_seq_are_caught_when_heads_are_compared() {
        let ((mut a, ad), (mut b, bd), (mut c, cd)) = trio();
        let mut a2 = Link::adopt(None, a.acl.all(), T0 + 4).unwrap();
        let (id1, r1) = a.write(&ad, &note("one"), T0 + 4).unwrap();
        let (id2, r2) = a2.write(&ad, &note("other"), T0 + 4).unwrap();
        assert_ne!(id1, id2);
        assert!(matches!(b.receive(&bd, &r1, T0 + 5).unwrap(), Admit::Stored { .. }));
        assert!(matches!(c.receive(&cd, &r2, T0 + 5).unwrap(), Admit::Stored { .. }));
        sync_pair(&mut b, &bd, &mut c, &cd, T0 + 6);
        assert!(b.store.frozen(&ad.id_hex()).unwrap(), "B saw both records and froze A");
        assert!(c.store.frozen(&ad.id_hex()).unwrap(), "C saw both records and froze A");
    }

    #[test]
    fn an_advert_for_another_record_at_a_held_seq_freezes_its_author() {
        let ((mut a, ad), (mut b, bd), _) = trio();
        let (_, r1) = a.write(&ad, &note("one"), T0 + 4).unwrap();
        b.receive(&bd, &r1, T0 + 5).unwrap();
        let honest = HeadAdvert::sign(&ad, a.id(), 1, &r1.id().unwrap(), T0 + 5).unwrap();
        assert_eq!(check_advert(&b, &honest, T0 + 5).unwrap(), AdvertSays::Nothing);
        let ahead = HeadAdvert::sign(&ad, a.id(), 2, &"cd".repeat(32), T0 + 5).unwrap();
        assert_eq!(check_advert(&b, &ahead, T0 + 5).unwrap(), AdvertSays::Behind);
        assert!(!b.store.frozen(&ad.id_hex()).unwrap());
        let lie = HeadAdvert::sign(&ad, a.id(), 1, &"ab".repeat(32), T0 + 6).unwrap();
        let mut s = Session::new();
        s.on_frame(&mut b, &bd, &ad.id_hex(), Frame::Advert { advert: lie }, T0 + 6)
            .unwrap();
        assert!(
            b.store.frozen(&ad.id_hex()).unwrap(),
            "two signed ids at one seq froze A"
        );
    }

    #[test]
    fn a_removed_peer_is_dropped_on_its_next_frame() {
        let ((mut a, ad), (b, bd), _) = trio();
        let mut s = Session::new();
        let h = hello(&b, &bd).unwrap().remove(0);
        s.on_frame(&mut a, &ad, &bd.id_hex(), h, T0 + 4).unwrap();
        a.remove_member(&ad, bd.root_hex(), T0 + 5).unwrap();
        let synced = Frame::Synced {
            heads: heads_of(&b).unwrap(),
            more: false,
        };
        let err = s.on_frame(&mut a, &ad, &bd.id_hex(), synced, T0 + 6).unwrap_err();
        assert!(err.to_string().contains("member"), "{err}");
    }
}
