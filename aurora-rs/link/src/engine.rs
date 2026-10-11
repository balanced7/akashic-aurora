//! One link, as this device holds it: its ACL chain, its store and the rules that join them.
//!
//! ## Membership
//!
//! Every membership change goes through [`Link::act`]: on the link's sequencer it is appended to
//! the ACL chain at once; anywhere else it becomes a signed proposal, kept in the store and sent
//! toward the sequencer by every sync session ([`Link::offer`] on the receiving side). The
//! sequencer checks a proposal against the chain as it stands when it appends, and refuses an
//! invalid one with a signed reason that any member relays back ([`Link::take_refusal`]: only the
//! current sequencer's refusal counts, at a position it sequenced, review finding R7-6). A replica
//! keeps another device's proposal only from an active member's device, or a join on a live
//! invite whose proof verifies, and only if it holds against the chain as the replica has it,
//! within a size cap per kind and a share per origin (review finding R7-3). Costs are charged
//! ([`Link::offer_from`]): to the sync peer for what it could have checked itself, and to the
//! proposal's origin (its proposer's root, or the invite a join uses) for a refusal and anything
//! else that depends on the chain, so an honest relay never pays for what it relays. An origin
//! pays once per proposal, however often and however late in the proposal's life anyone replays
//! it (the charge counts against a day's allowance), and what a fleet's devices cost as peers is
//! counted apart from what its proposals cost as an origin (review finding R8-1, round 9). While
//! the sequencer is offline, membership changes queue; records keep flowing.
//!
//! ## While halted
//!
//! An equivocation halts the chain but never folds it back (review finding R6-1): this replica
//! acts on its held state narrowed to the prefix's grants too (`AclChain::state`), so sync,
//! admission and status never grant a device more than the held tip does. Nothing new is sealed
//! ([`Link::write`] refuses, to be retried, as for a due rotation): any position past the prefix
//! may be dropped by the owner's takeover. A refused entry that the sequencer signed as the
//! chain's next one raises an `acl_divergence` alarm. The narrowed view can leave out devices the
//! held tip lists, this one included; the transport and the chain's own frames read the held
//! state (`sync::may_sync_acl`), so the evidence and the owner's takeover still reach every such
//! device (review finding R7-2).
//!
//! ## Records
//!
//! Admission of a record is four checks in a fixed order, cheapest first:
//!
//! 1. **Authentic**: shape, ciphertext hash and the author's signature (`Record::verify`).
//! 2. **Authorised now**: the author is a device of the link whose member is not pending; a
//!    removed device only up to its cut (the removal entry carries it); nobody frozen; its
//!    certificate was valid at the record's signed write time, which is not ahead of our clock.
//! 3. **In order**: the author's feed is gapless, the record is not dated before its predecessor,
//!    and the author is within its hourly quota (`Admit::OverQuota` says when it admits more,
//!    review finding R9-1). The same seq with a different record is equivocation: the author is
//!    frozen and an alarm raised.
//! 4. **Its ACL position**: the record names the chain position `(term, seq, hash)` it was
//!    written at. On this replica's chain, the author must have been an active device there, the
//!    record's epoch must be the epoch in force there, and the record not dated before it. A
//!    position this replica has not reached keeps the record waiting (`Admit::Pending`) while the
//!    chain is fetched. A position whose term the chain has moved past (a root takeover dropped
//!    it) makes the record `withheld` as [`LOST_FORK`], however and whenever it arrived; records
//!    already stored on positions a takeover drops are withheld the same way. Each is a function
//!    of the record and the chain alone.
//!
//! A record past the link's retention when it arrives (by our clock, or by the ACL chain's
//! latest entry time) is kept as a header only. Only then is the body opened, and only for this
//! fleet's own reading. Whether it reaches an agent is not decided here at all: admitted records
//! become events for Python's quarantine.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use ed25519_dalek::SigningKey;
use serde_json::{Value, json};

use crate::acl::{self, AclChain, AclPos, AclState, Entry, Inserted, Op, Policy, Proposal, ProposalRefusal, Role};
use crate::codec::{self, hex, unhex};
use crate::crypto::{self, Secret32};
use crate::error::{LinkError, Result, refused};
use crate::identity::{Device, fleet_fingerprint, safety_number};
use crate::record::{ACK_KIND, Body, Record, Seal};
use crate::store::{self, Store};

/// What happened to one received record.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Admit {
    /// Stored, with its status (`admitted`, `own`, `opaque`, `receipt` or `withheld`).
    Stored { id: String, status: String },
    /// Already held: a replay or a second path. A no-op.
    Duplicate,
    /// Not the next record of its author's feed; ask again from `have`.
    Gap { author: String, have: u64 },
    /// The next record of its author's feed, but the author is at its hourly quota here: ask
    /// again from `until`, when the quota admits another (review finding R9-1). Not a gap: asking
    /// sooner brings the same records back.
    OverQuota { author: String, until: u64 },
    /// The next record of its author's feed, but it names a chain position this replica has not
    /// reached. Kept aside; checked again whenever the chain grows (`Link::retry_pending`).
    Pending,
    /// Refused. The reason is for the local log only.
    Refused(String),
}

/// What a membership action became.
// Values live only between an action and its report, so their size spread costs nothing.
#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug)]
pub enum Acted {
    /// Appended to the chain (this device is the sequencer).
    Entry(Entry),
    /// Signed as a proposal, queued for the sequencer.
    Proposed(Proposal),
}

impl Acted {
    /// The action id: the entry hash, or the proposal id.
    pub fn id(&self) -> Result<String> {
        match self {
            Acted::Entry(e) => e.hash(),
            Acted::Proposed(p) => p.id(),
        }
    }

    pub fn entry(&self) -> Option<&Entry> {
        match self {
            Acted::Entry(e) => Some(e),
            Acted::Proposed(_) => None,
        }
    }

    pub fn proposal(&self) -> Option<&Proposal> {
        match self {
            Acted::Entry(_) => None,
            Acted::Proposed(p) => Some(p),
        }
    }
}

/// What a proposal offered to this replica became.
#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug)]
pub enum Offered {
    /// This device sequences the link and included it.
    Included(Entry),
    /// This device sequences the link and refused it (or knew it refused before).
    Refused(ProposalRefusal),
    /// Kept to relay toward the sequencer (new here).
    Queued,
    /// Already included, or already queued here.
    Known,
}

pub struct Link {
    pub store: Store,
    pub acl: AclChain,
    pub path: Option<PathBuf>,
    /// Per author, the next record of its feed while it waits for a chain position
    /// (`Admit::Pending`). In memory only: after a restart the record comes again.
    pending: BTreeMap<String, Record>,
    /// Per peer fleet root, when a proposal one of its devices handed us in a session failed a
    /// check the peer could have made itself (counted against its allowance as a peer,
    /// `offer_from`). In memory only.
    peer_charges: BTreeMap<String, Vec<u64>>,
    /// Per origin (a proposer's root, or `invite:<id>`), when and for which proposal a refusal or
    /// another chain-dependent failure was charged to it, and until when that proposal can be
    /// replayed (its `expires`): at most once per proposal, however often and however late it is
    /// replayed (review finding R8-1, and round 9: the charge counts against the allowance for a
    /// day, and is remembered until the proposal expires). Kept apart from `peer_charges`, so an
    /// origin's spent allowance never stops its fleet's devices from relaying. In memory only.
    origin_charges: BTreeMap<String, Vec<(u64, String, u64)>>,
}

/// Why a record sealed at a chain position a root takeover dropped is withheld. Final: a dropped
/// position never comes back.
pub const LOST_FORK: &str = "written at an ACL position a root takeover dropped";
/// Proposals of others this replica keeps (to relay, or refused), at most (its own are never
/// dropped).
pub const MAX_RELAYED: u32 = 1024;
/// Of those, at most this many from one origin: a proposer's root, or the invite a join uses.
pub const MAX_RELAYED_PER_ORIGIN: u32 = 64;

/// Whom handling a proposal is charged to (review finding R7-3).
enum Charge {
    None,
    /// The session peer: it could have checked this itself.
    Peer,
    /// The proposal's origin (`origin_of`), for the proposal `id`: it depends on the chain, which
    /// a relay may hold at another tip than ours. Charged once per proposal (review finding R8-1).
    Origin {
        key: String,
        id: String,
    },
}

/// A proposal's origin: its proposer's root, or `invite:<id>` for a join (the same key the relay
/// queue shares by, `Store::trim_relayed`).
fn origin_of(p: &Proposal) -> String {
    match p.parsed() {
        Ok(Op::Join(j)) => format!("invite:{}", j.invite),
        _ => p.proposer.root.clone(),
    }
}

/// How a record's named position reads here.
enum Position {
    /// On the chain: the state there.
    On(Box<AclState>),
    /// Not reached yet (or the chain is halted before it): the record waits.
    Unseen,
    /// The chain has moved past its term: a takeover dropped it.
    Lost,
}

pub fn db_path(dir: &Path, link_id: &str) -> PathBuf {
    dir.join(format!("{link_id}.db"))
}

impl Link {
    /// Create a new link owned by this device's fleet; this device sequences term 1.
    pub fn create(
        dir: Option<&Path>,
        device: &Device,
        name: &str,
        label: &str,
        policy: Policy,
        now: u64,
    ) -> Result<Self> {
        let (acl, _) = acl::genesis(device, name, label, policy, now)?;
        let mut link = Self::empty(dir, acl.link_id())?;
        link.acl = acl;
        link.store.set_meta("link_id", link.acl.link_id())?;
        link.persist_acl(now)?;
        Ok(link)
    }

    /// A link first seen through its ACL entries (joining, or a mailbox taking it on).
    pub fn adopt(dir: Option<&Path>, entries: Vec<Entry>, now: u64) -> Result<Self> {
        let genesis = entries
            .iter()
            .find(|e| e.seq == 0)
            .ok_or_else(|| refused("no genesis among the entries"))?;
        let link_id = genesis.hash()?;
        let mut link = Self::empty(dir, &link_id)?;
        link.store.set_meta("link_id", &link_id)?;
        let r = link.add_acl(entries, now)?;
        if link.acl.is_empty() {
            return Err(refused(
                r.refused.unwrap_or_else(|| "the genesis does not apply".into()),
            ));
        }
        Ok(link)
    }

    fn empty(dir: Option<&Path>, link_id: &str) -> Result<Self> {
        let (store, path) = match dir {
            Some(d) => {
                let p = db_path(d, link_id);
                (Store::open(&p)?, Some(p))
            }
            None => (Store::in_memory()?, None),
        };
        Ok(Self {
            store,
            acl: AclChain::new(),
            path,
            pending: BTreeMap::new(),
            peer_charges: BTreeMap::new(),
            origin_charges: BTreeMap::new(),
        })
    }

    pub fn open(path: &Path) -> Result<Self> {
        let store = Store::open(path)?;
        let mut acl = AclChain::new();
        acl.restore(store.acl_entries()?, store.evidence()?)?;
        if acl.is_empty() {
            return Err(LinkError::Unavailable(format!("{} holds no link", path.display())));
        }
        Ok(Self {
            store,
            acl,
            path: Some(path.to_owned()),
            pending: BTreeMap::new(),
            peer_charges: BTreeMap::new(),
            origin_charges: BTreeMap::new(),
        })
    }

    pub fn id(&self) -> &str {
        self.acl.link_id()
    }

    pub fn state(&self) -> &AclState {
        self.acl.state()
    }

    pub fn name(&self) -> &str {
        &self.state().name
    }

    /// Merge ACL entries from a peer or a bundle. What a takeover drops is persisted at once, and
    /// records sealed at dropped positions are withheld (`LOST_FORK`).
    pub fn add_acl(&mut self, entries: Vec<Entry>, now: u64) -> Result<Inserted> {
        let next = self.state().next_sequencer().0;
        let r = self.acl.insert(entries, Some(now));
        self.persist_acl(now)?;
        if let Some(why) = &r.diverged {
            self.store.alarm(
                "acl_divergence",
                &next,
                &format!("this replica refuses the sequencer's next entry ({why}); it cannot follow the chain"),
                now,
            )?;
        }
        Ok(r)
    }

    /// The chain range this link wants from its peers for the records waiting on it, if any.
    pub fn wanted_acl(&self) -> Option<(u64, u64)> {
        let len = self.acl.prefix_len() as u64;
        let mut from = u64::MAX;
        let mut to = 0;
        for r in self.pending.values() {
            if r.acl.seq >= len {
                from = from.min(len.saturating_sub(1));
            } else {
                // Same term, another entry: the entry the record names is asked for, and
                // checked as evidence.
                from = from.min(r.acl.seq.saturating_sub(1));
            }
            to = to.max(r.acl.seq);
        }
        (from != u64::MAX).then_some((from, to))
    }

    /// Store what the chain changed: rows from the lowest changed seq, new evidence, and records
    /// sealed at positions a takeover dropped.
    fn persist_acl(&mut self, now: u64) -> Result<()> {
        if let Some(from) = self.acl.take_dirty() {
            let rows: Vec<Entry> = (from..self.acl.len() as u64)
                .filter_map(|s| self.acl.entry(s).cloned())
                .collect();
            self.store.put_acl_from(from, &rows, now)?;
            for (id, seq) in self.included_ids(from) {
                let _ = seq;
                self.store.set_proposal(&id, "included", None, None)?;
            }
        }
        for ev in self.acl.take_evidence() {
            // Kept within the cap; a pair the store does not keep raises no alarm either (review
            // finding R7-1: at the cap there are already that many proofs on record).
            if !self.store.put_evidence(&ev, now, acl::MAX_EVIDENCE_PAIRS)? {
                continue;
            }
            let e = &ev.theirs;
            let detail = if ev.halts() {
                format!(
                    "the sequencer signed two entries at term {} seq {}; membership waits for the owner's takeover",
                    e.term, e.seq
                )
            } else {
                format!(
                    "the sequencer of term {} signed a second entry at seq {}, below a later term this chain \
                     has started; not halted (the old term's key is not a veto), but that key is known to \
                     sign twice, and a replica that holds the other entry is on another branch",
                    e.term, e.seq
                )
            };
            self.store.alarm("equivocation", &e.sequencer.device, &detail, now)?;
        }
        // Only the current halt's pair is checked again on a restart.
        self.store
            .settle_evidence(self.acl.halt().map(acl::Equivocation::key).as_ref())?;
        let dropped = self.acl.take_dropped();
        if !dropped.is_empty() {
            let hashes: Vec<String> = dropped.into_iter().map(|p| p.hash).collect();
            self.store.lose_positions(&hashes, LOST_FORK)?;
        }
        Ok(())
    }

    /// Proposal ids included in the chain from seq `from` on.
    fn included_ids(&self, from: u64) -> Vec<(String, u64)> {
        let mut out = Vec::new();
        for s in from..self.acl.prefix_len() as u64 {
            if let Some(e) = self.acl.entry(s) {
                out.extend(e.proposals.iter().filter_map(|p| p.id().ok()).map(|id| (id, s)));
            }
        }
        out
    }

    pub fn read_key(&self, device: &Device, epoch: u64) -> Result<Secret32> {
        self.state().read_key(epoch, &device.id_hex(), &device.kem)
    }

    pub fn my_role(&self, device: &Device) -> Option<Role> {
        self.state().active_device(&device.id_hex()).map(|(m, _)| m.role)
    }

    /// Whether this device signs the link's next entry (and the chain is not halted).
    pub fn is_sequencer(&self, device: &Device) -> bool {
        self.acl.halt().is_none() && self.state().next_sequencer().0 == device.id_hex()
    }

    /// The feed head this replica holds for `device`: the cut a removal carries.
    fn held_head(store: &Store, device: &str) -> u64 {
        store.head(device).ok().flatten().map_or(0, |h| h.0)
    }

    /// Append `op` to the chain when this device sequences the link; otherwise sign it as a
    /// proposal (checked here first against the chain as we hold it) and queue it.
    pub fn act(&mut self, device: &Device, op: Op, now: u64) -> Result<Acted> {
        if self.is_sequencer(device) {
            let store = &self.store;
            let cut_of = |d: &str| Self::held_head(store, d);
            let result = self.acl.append(device, Some(op), Vec::new(), now, &cut_of);
            self.persist_acl(now)?;
            return result.map(Acted::Entry);
        }
        let p = self.acl.propose_at(device, &op, now)?;
        self.acl.check_proposal(&p, now)?;
        self.store.put_proposal(&p.id()?, &p, true, now)?;
        Ok(Acted::Proposed(p))
    }

    /// A proposal from a peer (or our own, again). On the sequencer it is included or refused
    /// with a signed reason; elsewhere it is kept to relay, if it holds against the chain as this
    /// replica has it (review finding R7-3).
    pub fn offer(&mut self, device: &Device, p: &Proposal, now: u64) -> Result<Offered> {
        self.offer_charged(device, p, now).0
    }

    /// `offer`, and whom its cost is charged to (review finding R7-3): the session peer only for
    /// what it could have checked itself, the proposal's origin for what depends on the chain,
    /// and nobody when this replica cannot judge yet.
    fn offer_charged(&mut self, device: &Device, p: &Proposal, now: u64) -> (Result<Offered>, Charge) {
        let id = match p.id() {
            Ok(id) => id,
            Err(e) => return (Err(e), Charge::Peer),
        };
        if p.link != self.id() {
            return (Err(refused("proposal belongs to another link")), Charge::Peer);
        }
        if self.acl.included(&id).is_some() {
            return (Ok(Offered::Known), Charge::None);
        }
        let sequencer = self.is_sequencer(device);
        // A refusal we hold answers a re-sent proposal: anywhere, so it travels back to the
        // proposer; on the sequencer only its own, and only while the chain has not moved since
        // (it never honours a refusal it did not sign, review finding R6-2).
        match self.store.proposal_status(&id) {
            Ok(Some((status, _, Some(r))))
                if status == "refused" && (!sequencer || (r.by == device.id_hex() && r.at == self.acl.tip())) =>
            {
                return (Ok(Offered::Refused(r)), Charge::None);
            }
            Err(e) => return (Err(e), Charge::None),
            _ => {}
        }
        if let Err(e) = p.verify_signature() {
            return (Err(e), Charge::Peer);
        }
        if p.expires <= now {
            return (Err(refused("the proposal expired")), Charge::Peer);
        }
        // Its base past our chain (or on another branch): we cannot judge it yet, and keep it
        // only once we can. The proposer still holds it and sends it again.
        let s = p.base.seq;
        if (s as usize) >= self.acl.prefix_len() || self.acl.entry(s).is_none_or(|e| e.term != p.base.term) {
            return (
                Err(refused("the proposal's base is not on this replica's chain yet")),
                Charge::None,
            );
        }
        let origin = origin_of(p);
        if self.charged_origin(&origin, now) + self.state().proposals_today(&origin, now) >= self.allowance(&origin) {
            return (
                Err(refused(
                    "this proposal's origin reached its daily allowance of proposals",
                )),
                Charge::None,
            );
        }
        if let Err((e, charge)) = self.check_origin(p, &id, now) {
            return (Err(e), charge);
        }
        if !sequencer {
            // A relay keeps only what the sequencer would take on the chain as we hold it.
            if let Err(e) = self.acl.check_proposal(p, now) {
                return (Err(e), Charge::Origin { key: origin, id });
            }
            let kept = self.store.put_proposal(&id, p, false, now).and_then(|fresh| {
                self.store
                    .trim_relayed(MAX_RELAYED, MAX_RELAYED_PER_ORIGIN)
                    .map(|()| fresh)
            });
            return match kept {
                Ok(true) => (Ok(Offered::Queued), Charge::None),
                Ok(false) => (Ok(Offered::Known), Charge::None),
                Err(e) => (Err(e), Charge::None),
            };
        }
        let why = match self.admit_proposal(p, now) {
            Ok(()) => {
                let store = &self.store;
                let cut_of = |d: &str| Self::held_head(store, d);
                match self.acl.append(device, None, vec![p.clone()], now, &cut_of) {
                    Ok(e) => {
                        let stored = self
                            .store
                            .put_proposal(&id, p, false, now)
                            .and_then(|_| self.persist_acl(now));
                        return (stored.map(|()| Offered::Included(e)), Charge::None);
                    }
                    Err(e) => e.to_string(),
                }
            }
            Err(e) => e.to_string(),
        };
        let refusal = (|| {
            let r = ProposalRefusal::sign(device, self.id(), &id, &why, self.acl.tip())?;
            self.store.put_proposal(&id, p, false, now)?;
            self.store.set_proposal(&id, "refused", Some(&r.why), Some(&r))?;
            self.store.trim_relayed(MAX_RELAYED, MAX_RELAYED_PER_ORIGIN)?;
            Ok(Offered::Refused(r))
        })();
        (refusal, Charge::Origin { key: origin, id })
    }

    /// A proposal from a sync peer: offered as `offer` does, and charged (review findings R6-4,
    /// R7-3, R8-1): to the peer's fleet for what the peer could have checked itself (shape,
    /// signature, size, expiry, an unknown proposer or invite), to the proposal's origin (its
    /// proposer's root, or the invite a join uses) for what depends on the chain (a refusal, an
    /// inactive proposer, a dead invite), so an honest relay never pays for what it relays. An
    /// origin pays once per proposal a day, however often that proposal is replayed, and its
    /// charges are kept apart from its fleet's charges as a peer. A peer whose charges reach its
    /// daily allowance, or an origin whose charges and included proposals today do, gets no more
    /// taken.
    pub fn offer_from(&mut self, device: &Device, p: &Proposal, peer: &str, now: u64) -> Result<Offered> {
        let peer_key = self
            .state()
            .active_device(peer)
            .map_or_else(|| peer.to_owned(), |(m, _)| m.root.clone());
        if self.charged_peer(&peer_key, now) >= self.allowance(&peer_key) {
            return Err(refused(
                "this peer's fleet reached its daily allowance of proposals (refusals count): no more today",
            ));
        }
        let (out, charge) = self.offer_charged(device, p, now);
        match charge {
            Charge::Peer => self.charge_peer(peer_key, now),
            Charge::Origin { key, id } => self.charge_origin(key, id, p.expires, now),
            Charge::None => {}
        }
        out
    }

    /// Charges against a peer's fleet within the last day.
    fn charged_peer(&self, key: &str, now: u64) -> usize {
        let day = now.saturating_sub(24 * 3600);
        self.peer_charges
            .get(key)
            .map_or(0, |v| v.iter().filter(|t| **t > day).count())
    }

    /// Charges against an origin (a fleet root, or `invite:<id>`) within the last day: distinct
    /// proposals.
    fn charged_origin(&self, key: &str, now: u64) -> usize {
        let day = now.saturating_sub(24 * 3600);
        self.origin_charges
            .get(key)
            .map_or(0, |v| v.iter().filter(|(t, _, _)| *t > day).count())
    }

    fn charge_peer(&mut self, key: String, now: u64) {
        let day = now.saturating_sub(24 * 3600);
        // A key with nothing charged within a day is dropped, so the table holds only that. Each
        // key holds at most its allowance: a peer at it is not looked at again.
        self.peer_charges.retain(|_, v| {
            v.retain(|t| *t > day);
            !v.is_empty()
        });
        self.peer_charges.entry(key).or_default().push(now);
    }

    /// Charge `key` for the proposal `id`, unless it was charged for it already: a replay of the
    /// same proposal costs its origin nothing more (review finding R8-1). The charge counts
    /// against the origin's allowance for a day, and is remembered until the proposal expires
    /// (`expires`, at most `PROPOSAL_TTL_S` ahead), so a replay a day later is not charged again
    /// either (round 9). Only the proposal's own author can make another proposal of the same
    /// origin, and an origin at its allowance is not checked again, so each key holds at most its
    /// allowance of ids for each day a proposal lives.
    fn charge_origin(&mut self, key: String, id: String, expires: u64, now: u64) {
        let day = now.saturating_sub(24 * 3600);
        self.origin_charges.retain(|_, v| {
            v.retain(|(t, _, until)| *t > day || *until > now);
            !v.is_empty()
        });
        let until = expires.min(now.saturating_add(acl::PROPOSAL_TTL_S + acl::MAX_FUTURE_SKEW_S));
        let ids = self.origin_charges.entry(key).or_default();
        if !ids.iter().any(|(_, i, _)| *i == id) {
            ids.push((now, id, until));
        }
    }

    /// The daily allowance of `key`: an admin fleet's, or a member's (any other fleet, and an
    /// invite's joins).
    fn allowance(&self, key: &str) -> usize {
        let admin = self
            .state()
            .members
            .get(key)
            .is_some_and(|m| !m.removed && m.role.admin());
        if admin {
            acl::MAX_ADMIN_PROPOSALS_PER_DAY
        } else {
            acl::MAX_MEMBER_PROPOSALS_PER_DAY
        }
    }

    /// Who may hand us a proposal to keep (review findings R6-4, R7-3): an active member's device,
    /// for anything but a join; a join only for a live invite, once its invite proof verifies. A
    /// proposer or invite this chain never listed is the peer's to have checked; one the chain
    /// has since retired is charged to the origin.
    fn check_origin(&self, p: &Proposal, id: &str, now: u64) -> std::result::Result<(), (LinkError, Charge)> {
        let s = self.state();
        let peer = |why: &str| (refused(why.to_owned()), Charge::Peer);
        if p.kind != "join" {
            if s.devices.get(&p.proposer.device).is_none() {
                return Err(peer("a proposal is kept only from a member's device"));
            }
            return match s.active_device(&p.proposer.device) {
                Some(_) => Ok(()),
                None => Err((
                    refused("a proposal is kept only from an active member's device"),
                    Charge::Origin {
                        key: origin_of(p),
                        id: id.to_owned(),
                    },
                )),
            };
        }
        let Ok(Op::Join(j)) = p.parsed() else {
            return Err(peer("expected a join"));
        };
        let inv = s
            .invites
            .get(&j.invite)
            .ok_or_else(|| peer("a join is kept only for an invite this replica holds"))?;
        let proof = acl::join_proof_bytes(
            s.link_id.as_str(),
            &j.invite,
            &p.proposer.root,
            &p.proposer.device,
            &p.nonce,
        )
        .map_err(|e| (e, Charge::Peer))?;
        let key = unhex::<32>(&inv.key).map_err(|e| (e, Charge::Peer))?;
        let sig = codec::unb64(&j.proof).map_err(|e| (e, Charge::Peer))?;
        crypto::verify(&key, "join", &proof, &sig).map_err(|_| peer("the join's invite proof does not verify"))?;
        if self.invite_live(&j.invite, now, None).is_none() {
            return Err((
                refused("a join is kept only for a live invite (unused, unrevoked, unexpired, from an admin)"),
                Charge::Origin {
                    key: origin_of(p),
                    id: id.to_owned(),
                },
            ));
        }
        Ok(())
    }

    /// A live invite (by the action id that issued it) by the verifier's clock: present,
    /// unrevoked, unused if single-use, unexpired, and published by a fleet that is still an active
    /// admin (or the owner) of the link. Returns its key. With `rejoiner`, an invite that device's
    /// own join used up also counts, so a joiner whose join was relayed can fetch the chain again.
    pub fn invite_live(&self, invite: &str, now: u64, rejoiner: Option<&str>) -> Option<String> {
        let s = self.state();
        let i = s.invites.get(invite)?;
        let mine = rejoiner.is_some_and(|d| i.used_by.as_deref() == Some(d));
        let live = mine
            || (!i.revoked
                && !(i.single_use && i.used)
                && i.expires > now
                && s.members
                    .get(&i.by)
                    .is_some_and(|m| !m.removed && !m.pending && m.role.admin()));
        live.then(|| i.key.clone())
    }

    /// The sequencer's own admission policy for a proposal: a per-member daily allowance.
    fn admit_proposal(&self, p: &Proposal, now: u64) -> Result<()> {
        if p.kind == "join" {
            return Ok(());
        }
        let s = self.state();
        let admin = s.active_device(&p.proposer.device).is_some_and(|(m, _)| m.role.admin());
        let cap = if admin {
            acl::MAX_ADMIN_PROPOSALS_PER_DAY
        } else {
            acl::MAX_MEMBER_PROPOSALS_PER_DAY
        };
        if s.proposals_today(&p.proposer.root, now) >= cap {
            return Err(refused("this member reached its daily allowance of proposals"));
        }
        Ok(())
    }

    /// A sequencer's signed refusal relayed to us: kept if it is genuine and about a proposal we
    /// hold queued. Returns whether it was news.
    ///
    /// Genuine means (review findings R6-2, R7-6): signed by the current sequencer, which also
    /// sequenced the link at the position the refusal names (`at`, on this chain), and that
    /// position is at or past the proposal's base, so the refuser was the sequencer when the
    /// proposal could reach it. An older term's word on a proposal is not final, whoever holds it:
    /// that key may sign a fresh refusal at any position of its old term. The sequencer takes no
    /// refusal it did not sign.
    pub fn take_refusal(&mut self, device: &Device, r: &ProposalRefusal) -> Result<bool> {
        if r.link != self.id() {
            return Ok(false);
        }
        r.verify()?;
        let next = self.state().next_sequencer().0;
        if self.is_sequencer(device) && r.by != device.id_hex() {
            return Ok(false);
        }
        // Only the current sequencer's word is final (review finding R7-6): an ex-sequencer's key
        // can sign a fresh refusal at any position of its old term.
        if r.by != next {
            return Ok(false);
        }
        if (r.at.seq as usize) >= self.acl.prefix_len() {
            // Past our chain: we cannot tell who sequenced there yet.
            return Ok(false);
        }
        if !self.acl.on_chain(&r.at) {
            return Err(refused("a refusal names a position that is not on this chain"));
        }
        if self.acl.state_at(r.at.seq)?.next_sequencer().0 != r.by {
            return Err(refused(
                "a refusal must be signed by the device that sequenced the link at the position it names",
            ));
        }
        let Some(q) = self.store.proposal(&r.id)? else {
            return Ok(false);
        };
        if q.status != "queued" {
            return Ok(false);
        }
        if r.at.seq < q.proposal.base.seq {
            return Err(refused("a refusal names a position before the proposal's base"));
        }
        self.store.set_proposal(&r.id, "refused", Some(&r.why), Some(r))?;
        Ok(true)
    }

    /// Proposals to send toward the sequencer: queued and not yet included, ours first.
    pub fn outstanding(&mut self, limit: usize) -> Result<Vec<Proposal>> {
        let mut out = Vec::new();
        let queued = self.store.proposals("queued")?;
        let (mine, relayed): (Vec<_>, Vec<_>) = queued.into_iter().partition(|q| q.mine);
        for q in mine.into_iter().chain(relayed) {
            if self.acl.included(&q.id).is_some() {
                self.store.set_proposal(&q.id, "included", None, None)?;
                continue;
            }
            if out.len() < limit {
                out.push(q.proposal);
            }
        }
        Ok(out)
    }

    /// Refusals we hold for the proposals `ids` (so a re-sent proposal learns its fate).
    pub fn refusal_of(&self, id: &str) -> Result<Option<ProposalRefusal>> {
        Ok(match self.store.proposal_status(id)? {
            Some((status, _, r)) if status == "refused" => r,
            _ => None,
        })
    }

    // ------------------------------------------------------------------------------ membership

    /// Publish an invite. Returns the ticket (the secret, and the action id that issued the
    /// invite) that goes into the invite code. On a device that does not sequence the link the
    /// invite is a proposal: the code works once the sequencer includes it.
    pub fn invite(
        &mut self,
        device: &Device,
        role: Role,
        ttl_s: u64,
        single_use: bool,
        approval: bool,
        now: u64,
    ) -> Result<acl::InviteTicket> {
        let secret = crypto::random32();
        let op = Op::Invite(acl::Invite {
            invite: hex(&crypto::public_of(&acl::invite_key(&secret))),
            role,
            expires: now + ttl_s.clamp(60, acl::MAX_INVITE_TTL_S),
            single_use,
            approval,
        });
        let acted = self.act(device, op, now)?;
        Ok(acl::InviteTicket {
            secret,
            entry: acted.id()?,
        })
    }

    pub fn accept(&mut self, device: &Device, join: &str, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let root = s
            .pending_joins
            .get(join)
            .ok_or_else(|| refused("no such pending join"))?;
        let m = &s.members[root];
        // Live devices only, exactly as the ACL checks it.
        let devices: BTreeSet<String> = if m.role.reads() {
            m.devices
                .iter()
                .filter(|d| s.devices.get(*d).is_some_and(|x| x.cut.is_none()))
                .cloned()
                .collect()
        } else {
            BTreeSet::new()
        };
        let key = s.read_key(s.epoch, &device.id_hex(), &device.kem)?;
        let wraps = s.make_wraps(&key.0, s.epoch, &devices)?;
        self.act(
            device,
            Op::Accept(acl::Accept {
                join: join.to_owned(),
                wraps,
            }),
            now,
        )
    }

    pub fn decline(&mut self, device: &Device, join: &str, now: u64) -> Result<Acted> {
        self.act(device, Op::Decline(acl::Decline { join: join.to_owned() }), now)
    }

    /// A new key for everyone who may still read, if this device holds the current one.
    fn rotation(s: &AclState, device: &Device, keyed: &BTreeSet<String>) -> Result<Option<acl::KeyChange>> {
        match s.read_key(s.epoch, &device.id_hex(), &device.kem) {
            Ok(key) => Ok(Some(s.new_key_change(&key, keyed)?.0)),
            Err(_) => Ok(None),
        }
    }

    pub fn remove_member(&mut self, device: &Device, root: &str, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let member = s.members.get(root).ok_or_else(|| refused("no such member"))?;
        let leaving = s.devices.get(&device.id_hex()).is_some_and(|d| d.member == root);
        let mut keyed = s.keyed_devices();
        keyed.retain(|d| !member.devices.contains(d));
        let rotate = if leaving {
            None
        } else {
            Self::rotation(&s, device, &keyed)?
        };
        self.act(
            device,
            Op::RemoveMember(acl::RemoveMember {
                member: root.to_owned(),
                rotate,
            }),
            now,
        )
    }

    pub fn remove_device(&mut self, device: &Device, target: &str, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let mut keyed = s.keyed_devices();
        keyed.remove(target);
        // A member that is no admin picks the next key for its own device's removal only when it
        // is the device the ACL lets rotate now; otherwise the removal leaves it due.
        let admin = s.active_device(&device.id_hex()).is_some_and(|(m, _)| m.role.admin());
        let since = if s.rotation_due { s.rotation_due_since } else { now };
        let rotate =
            if target == device.id_hex() || (!admin && !s.may_rotate_due(&device.id_hex(), now, since, Some(target))) {
                None
            } else {
                Self::rotation(&s, device, &keyed)?
            };
        self.act(
            device,
            Op::RemoveDevice(acl::RemoveDevice {
                device: target.to_owned(),
                rotate,
            }),
            now,
        )
    }

    /// Rotate the read key. When the key in force is junk to this device (a rogue key holder
    /// wrapped it so) and the device is an admin, this is a recovery re-key from the last epoch
    /// it can read.
    pub fn rotate_key(&mut self, device: &Device, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let change = match Self::rotation(&s, device, &s.keyed_devices())? {
            Some(change) => change,
            None => Self::recovery(&s, device)?,
        };
        self.act(device, Op::RotateKey(change), now)
    }

    /// A recovery re-key by an admin that cannot read the key in force.
    fn recovery(s: &AclState, device: &Device) -> Result<acl::KeyChange> {
        let me = device.id_hex();
        if !s.active_device(&me).is_some_and(|(m, _)| m.role.admin()) {
            return Err(refused("this device does not hold the read key"));
        }
        let (from, old) = (0..s.epoch)
            .rev()
            .filter(|e| s.has_wrap(*e, &me) || s.prev_keys.contains_key(&(e + 1)))
            .find_map(|e| s.read_key(e, &me, &device.kem).ok().map(|k| (e, k)))
            .ok_or_else(|| refused("this device can read no epoch of this link"))?;
        Ok(s.recovery_key_change(from, &old, &s.keyed_devices())?.0)
    }

    pub fn set_role(&mut self, device: &Device, root: &str, role: Role, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let m = s.members.get(root).ok_or_else(|| refused("no such member"))?;
        let wraps = if role.reads() && !m.role.reads() {
            let live: BTreeSet<String> = m
                .devices
                .iter()
                .filter(|d| s.devices.get(*d).is_some_and(|x| x.cut.is_none()))
                .cloned()
                .collect();
            let key = s.read_key(s.epoch, &device.id_hex(), &device.kem)?;
            s.make_wraps(&key.0, s.epoch, &live)?
        } else {
            vec![]
        };
        // Taking read access away rotates in the same action (the ACL refuses it otherwise).
        let rotate = if m.role.reads() && !role.reads() {
            let mut keyed = s.keyed_devices();
            keyed.retain(|d| !m.devices.contains(d));
            Self::rotation(&s, device, &keyed)?
        } else {
            None
        };
        self.act(
            device,
            Op::SetRole(acl::SetRole {
                member: root.to_owned(),
                role,
                wraps,
                rotate,
            }),
            now,
        )
    }

    pub fn revoke_invite(&mut self, device: &Device, invite: &str, now: u64) -> Result<Acted> {
        self.act(
            device,
            Op::RevokeInvite(acl::RevokeInvite {
                invite: invite.to_owned(),
            }),
            now,
        )
    }

    /// Hand the sequencer to `to`, an active owner or admin device: the next entry is theirs.
    pub fn handoff(&mut self, device: &Device, to: &str, now: u64) -> Result<Acted> {
        self.act(device, Op::Handoff(acl::Handoff { to: to.to_owned() }), now)
    }

    /// The owner's takeover with its fleet root: this device sequences a new term after entry
    /// `after` (the chain's last good entry by default); later entries of older terms are dropped
    /// everywhere.
    pub fn takeover(&mut self, device: &Device, root: &SigningKey, after: Option<u64>, now: u64) -> Result<Entry> {
        let result = self.acl.takeover(device, root, after, now);
        self.persist_acl(now)?;
        result
    }

    /// Add a device of a member (or renew one, with no wraps), from its certificate.
    pub fn add_device(&mut self, device: &Device, cert: crate::identity::DeviceCert, now: u64) -> Result<Acted> {
        let s = self.state().clone();
        let reads = s.members.get(&cert.root).is_some_and(|m| m.role.reads());
        let renewal = s.devices.contains_key(&cert.device);
        let wraps = if reads && !renewal {
            let mut tmp = s.clone();
            tmp.devices.insert(
                cert.device.clone(),
                acl::DeviceState::new(cert.clone(), cert.root.clone()),
            );
            tmp.make_wraps(
                &self.read_key(device, s.epoch)?.0,
                s.epoch,
                &[cert.device.clone()].into(),
            )?
        } else {
            vec![]
        };
        self.act(device, Op::AddDevice(acl::AddDevice { cert, wraps }), now)
    }

    /// What a daemon does unasked. Every reading device: raise an alarm for a junk wrap (an
    /// admin re-keys). The sequencer: include the proposals it holds, wrap the key to joins that
    /// need no approval, and append a due rotation. Any other device holding the key: propose a
    /// due rotation when it is the designated device or the grace has passed. Returns what it did.
    ///
    /// Best effort per item: one that fails is raised as an alarm and skipped.
    pub fn upkeep(&mut self, device: &Device, now: u64) -> Result<Vec<Acted>> {
        let mut out = Vec::new();
        let me = device.id_hex();
        if self.is_sequencer(device) {
            for q in self.store.proposals("queued")? {
                match self.offer(device, &q.proposal, now) {
                    Ok(Offered::Included(e)) => out.push(Acted::Entry(e)),
                    Ok(_) => {}
                    Err(e) => self
                        .store
                        .alarm("upkeep", &me, &format!("proposal {}: {e}", q.id), now)?,
                }
            }
        }
        if !self.my_role(device).is_some_and(Role::reads) {
            return Ok(out);
        }
        let epoch = self.state().epoch;
        if let Some(by) = self.state().bad_wrap(epoch, &me, &device.kem) {
            self.store.alarm(
                "bad_wrap",
                &by,
                &format!("epoch {epoch}: the key wrapped to {me} is not the key the log names"),
                now,
            )?;
            if self.my_role(device).is_some_and(Role::admin) && !self.queued_rotation(epoch)? {
                match self.rotate_key(device, now) {
                    Ok(a) => out.push(a),
                    Err(e) => self.store.alarm("upkeep", &me, &format!("recovery re-key: {e}"), now)?,
                }
            }
        }
        if self.read_key(device, self.state().epoch).is_err() {
            return Ok(out);
        }
        if self.is_sequencer(device) {
            let auto: Vec<String> = self
                .state()
                .pending_joins
                .iter()
                .filter(|(_, root)| self.state().members.get(*root).is_some_and(|m| !m.pending))
                .map(|(j, _)| j.clone())
                .collect();
            for join in auto {
                match self.accept(device, &join, now) {
                    Ok(a) => out.push(a),
                    Err(e) => self.store.alarm("upkeep", &me, &format!("accept {join}: {e}"), now)?,
                }
            }
        }
        let epoch = self.state().epoch;
        if self.state().rotation_due && self.may_rotate_now(device, now) && !self.queued_rotation(epoch)? {
            match self.rotate_key(device, now) {
                Ok(a) => out.push(a),
                Err(e) => self.store.alarm("upkeep", &me, &format!("rotation: {e}"), now)?,
            }
        }
        Ok(out)
    }

    /// Whether one of our own proposals already rotates away from `epoch`.
    fn queued_rotation(&self, epoch: u64) -> Result<bool> {
        Ok(self.store.proposals("queued")?.iter().any(|q| {
            q.mine
                && q.proposal.kind == "rotate_key"
                && q.proposal.args.get("epoch").and_then(Value::as_u64) == Some(epoch + 1)
        }))
    }

    /// How long a due rotation waits for its designated device before any key holder proposes it.
    pub const ROTATION_GRACE_S: u64 = acl::ROTATION_GRACE_S;

    /// Whether this device rotates a due rotation now: the sequencer always (it appends it);
    /// any other device holding the key when it is the designated device, or after the grace.
    fn may_rotate_now(&self, device: &Device, now: u64) -> bool {
        let s = self.state();
        let me = device.id_hex();
        if self.is_sequencer(device) {
            return s.may_rotate(&me, now);
        }
        s.may_rotate(&me, now)
            && (s.designated_rotator(None).as_deref() == Some(me.as_str())
                || now >= s.rotation_due_since.saturating_add(Self::ROTATION_GRACE_S))
    }

    /// Self-monitoring: every device the log lists under our own root must be one we certified.
    /// Returns the unknown ones (and raises an alarm for each).
    ///
    /// A device also vouches for the devices of its own fleet that were already in the log when it
    /// was added (one of them added it), so a fleet's second machine does not raise an alarm
    /// about its first. Anything added under our root later must be one we certified ourselves.
    pub fn self_monitor(&self, me: &str, my_root: &str, certified: &BTreeSet<String>, now: u64) -> Result<Vec<String>> {
        let vouched = self.devices_before(me, my_root);
        // The held state: a device added past a halt's prefix is still one under our root.
        let rogue: Vec<String> = self
            .acl
            .held_state()
            .devices
            .iter()
            .filter(|(d, s)| s.member == my_root && s.cut.is_none() && !certified.contains(*d) && !vouched.contains(*d))
            .map(|(d, _)| d.clone())
            .collect();
        for d in &rogue {
            self.store.alarm(
                "unknown_own_device",
                d,
                "the link lists a device under our root that we never certified",
                now,
            )?;
        }
        Ok(rogue)
    }

    /// Devices under `root` the chain introduced up to (and with) the action adding `me`.
    fn devices_before(&self, me: &str, root: &str) -> BTreeSet<String> {
        let mut seen = BTreeSet::new();
        for e in self.acl.all() {
            let mut added: Vec<String> = Vec::new();
            match &e.body {
                Some(Op::Genesis(g)) => {
                    added.extend(g.devices.iter().filter(|c| c.root == root).map(|c| c.device.clone()))
                }
                Some(Op::AddDevice(a)) if a.cert.root == root => added.push(a.cert.device.clone()),
                _ => {}
            }
            for p in &e.proposals {
                match p.parsed() {
                    Ok(Op::Join(_)) if p.proposer.root == root => added.push(p.proposer.device.clone()),
                    Ok(Op::AddDevice(a)) if a.cert.root == root => added.push(a.cert.device.clone()),
                    _ => {}
                }
            }
            let found = added.iter().any(|d| d == me);
            seen.extend(added);
            if found {
                return seen;
            }
        }
        BTreeSet::new()
    }

    // -------------------------------------------------------------------------------- records

    /// Whether this device appends a due rotation right now: it sequences the link and holds
    /// the key.
    fn rotates_now(&self, device: &Device, now: u64) -> bool {
        self.is_sequencer(device)
            && self.read_key(device, self.state().epoch).is_ok()
            && self.may_rotate_now(device, now)
    }

    /// While a rotation is due, the current key still opens for whoever was just removed or
    /// demoted, so nothing new is sealed under it. The sequencer rotates first; everyone else's
    /// mail waits (refused, to be retried) until the rotation reaches them.
    fn rotation_gate(&mut self, device: &Device, now: u64) -> Result<()> {
        if !self.state().rotation_due {
            return Ok(());
        }
        if self.rotates_now(device, now) {
            self.rotate_key(device, now)?;
            return Ok(());
        }
        Err(LinkError::Unavailable(
            "a key rotation is due on this link (a reader was removed or demoted); new mail waits \
             until a device holding the key appends it"
                .into(),
        ))
    }

    /// While the chain is halted, nothing new is sealed (review finding R6-1). Every position
    /// past the prefix may be dropped by the owner's takeover, and the prefix's epoch may be one a
    /// later removal retired; halted peers would keep the record waiting anyway. Mail waits
    /// (refused, to be retried), as it does for a due rotation.
    fn halt_gate(&self) -> Result<()> {
        match self.acl.halt() {
            Some(h) => Err(LinkError::Unavailable(format!(
                "this link's sequencer signed two entries at term {} seq {}; new mail waits for the \
                 owner's takeover",
                h.term, h.seq
            ))),
            None => Ok(()),
        }
    }

    /// Write one record to this device's feed.
    pub fn write(&mut self, device: &Device, body: &Body, now: u64) -> Result<(String, Record)> {
        self.halt_gate()?;
        self.rotation_gate(device, now)?;
        let s = self.state();
        let me = device.id_hex();
        let (member, _) = s
            .active_device(&me)
            .ok_or_else(|| refused("this device is not an active member of the link"))?;
        if body.kind != ACK_KIND && !member.role.writes() {
            return Err(refused("this fleet may read the link but not write to it"));
        }
        if !member.role.reads() {
            return Err(refused("a mailbox writes nothing"));
        }
        if !device.cert.valid_at(now) {
            return Err(LinkError::Unavailable(
                "this device's certificate has expired; renew it before writing".into(),
            ));
        }
        let position = self.acl.tip();
        let epoch = s.epoch;
        let key = self.read_key(device, epoch)?;
        let (seq, prev) = match self.store.head(&me)? {
            Some((seq, id)) => (seq + 1, id),
            None => (1, String::new()),
        };
        let mut others: Vec<(String, (u64, String))> =
            self.store.heads()?.into_iter().filter(|(a, _)| *a != me).collect();
        others.sort();
        let deps: Vec<String> = others
            .into_iter()
            .map(|(_, (_, id))| id)
            .take(crate::record::MAX_DEPS)
            .collect();
        let link = s.link_id.clone();
        let kinds = s.policy().kinds;
        let r = Record::seal(
            device,
            Seal {
                link: &link,
                seq,
                ts: now,
                prev: &prev,
                deps,
                acl: &position,
                epoch,
                key: &key.0,
            },
            body,
            &kinds,
        )?;
        let id = r.verify()?;
        let blobs: Vec<(String, String, u64)> = body
            .blobs
            .iter()
            .map(|b| (b.id.clone(), b.name.clone(), crate::record::blob_ct_len(b.bytes)))
            .collect();
        if let Some(why) = self.blob_room(&me, &blobs, false)? {
            return Err(refused(format!("attachment not sent: {why}")));
        }
        let plain = codec::canonical(body)?;
        self.store
            .put_record(&id, &r, store::OWN, Some(&String::from_utf8_lossy(&plain)), None, now)?;
        for (blob, name, n) in &blobs {
            self.store.put_blob(blob, &id, &me, name, *n)?;
        }
        Ok((id, r))
    }

    /// Check and store one record from a peer. `me` opens bodies; a mailbox simply cannot.
    pub fn receive(&mut self, me: &Device, r: &Record, now: u64) -> Result<Admit> {
        let id = match r.verify() {
            Ok(id) => id,
            Err(e) => return Ok(Admit::Refused(e.to_string())),
        };
        if r.link != self.id() {
            return Ok(Admit::Refused("record belongs to another link".into()));
        }
        let past = self.past_retention(r, now);
        // The id covers the header, not the ciphertext, so a whole copy of a record held only as
        // its header is a duplicate too: a row is only ever stripped past retention, and past
        // retention its body is not wanted any more (finding L1).
        if self.store.get(&id)?.is_some() {
            return Ok(Admit::Duplicate);
        }
        if r.ts > now + acl::MAX_FUTURE_SKEW_S {
            return Ok(Admit::Refused("record is dated in the future".into()));
        }
        if let Err(e) = self.member_check(r) {
            return Ok(Admit::Refused(e.to_string()));
        }
        // A body may be gone only once the link's retention has passed, by the record's own signed
        // write time. Earlier, a missing body means a relay stripped it: refuse this copy, store
        // nothing, and wait for a whole one.
        if r.ct.is_none() && !past {
            return Ok(Admit::Refused(
                "record arrived without its body, inside the retention period".into(),
            ));
        }
        // Past retention when it arrives, it is kept as a header only: the feed stays whole, and
        // a long-expired device key cannot deliver new content dated inside its old certificate.
        let stripped;
        let r = if past && r.ct.is_some() {
            stripped = r.retired();
            &stripped
        } else {
            r
        };
        // In order, or equivocation.
        if let Some(other) = self.store.record_at(&r.author, r.seq)? {
            debug_assert_ne!(other, id);
            let detail = format!("two records at seq {}: {other} and {id}", r.seq);
            self.store.freeze(&r.author, &detail, now)?;
            self.store.alarm("equivocation", &r.author, &detail, now)?;
            return Ok(Admit::Refused("equivocation".into()));
        }
        let have = self.store.head(&r.author)?;
        let (have_seq, have_id) = have.clone().unwrap_or((0, String::new()));
        if r.seq != have_seq + 1 {
            return Ok(Admit::Gap {
                author: r.author.clone(),
                have: have_seq,
            });
        }
        if r.prev != have_id {
            let detail = format!(
                "seq {} names prev {} but seq {} is {}",
                r.seq, r.prev, have_seq, have_id
            );
            self.store.freeze(&r.author, &detail, now)?;
            self.store.alarm("broken_chain", &r.author, &detail, now)?;
            return Ok(Admit::Refused("broken chain".into()));
        }
        // A feed's clock never runs backwards, so an expired device cannot backdate past its own
        // last record into its certificate's lifetime.
        if let Some(prev) = self.store.get(&have_id)?
            && r.ts < prev.record.ts
        {
            return Ok(Admit::Refused("record is dated before its predecessor".into()));
        }
        let quota = self.state().policy().rate_per_hour;
        let since = now.saturating_sub(3600);
        if self.store.count_recent(&r.author, since)? >= quota {
            return Ok(Admit::OverQuota {
                author: r.author.clone(),
                until: self.store.quota_frees_at(&r.author, since, quota)?,
            });
        }
        // The ACL position last: the record names where on the chain it was written.
        let at = match self.position(&r.acl) {
            Position::On(at) => at,
            Position::Unseen => {
                self.pending.insert(r.author.clone(), r.clone());
                return Ok(Admit::Pending);
            }
            Position::Lost => {
                self.pending.remove(&r.author);
                self.store
                    .put_record(&id, r, store::WITHHELD, None, Some(LOST_FORK), now)?;
                return Ok(Admit::Stored {
                    id,
                    status: store::WITHHELD.to_owned(),
                });
            }
        };
        if let Err(e) = self.check_at(r, &at) {
            return Ok(Admit::Refused(e.to_string()));
        }
        self.pending.remove(&r.author);

        // Only now open it, and only to read it here.
        let writes_at = at.active_device(&r.author).is_some_and(|(m, _)| m.role.writes());
        let (status, body, reason, opened) = self.open_here(me, r, &id, writes_at, now)?;
        self.store
            .put_record(&id, r, status, body.as_deref(), reason.as_deref(), now)?;
        self.register_blobs(me, r, &id, status, opened.as_ref(), now)?;
        Ok(Admit::Stored {
            id,
            status: status.to_owned(),
        })
    }

    /// Check the records waiting for a chain position again (call it whenever the chain grows).
    /// Returns those now stored, to relay.
    pub fn retry_pending(&mut self, me: &Device, now: u64) -> Result<Vec<Record>> {
        let waiting: Vec<Record> = std::mem::take(&mut self.pending).into_values().collect();
        let mut stored = Vec::new();
        for r in waiting {
            if let Admit::Stored { .. } = self.receive(me, &r, now)? {
                stored.push(r);
            }
        }
        Ok(stored)
    }

    /// How `pos` reads on this replica's chain: on it (with the state there), not reached yet,
    /// or lost (the chain's term at that seq, or at its end before it, is later than the
    /// position's: terms never go down along a chain, so it can never be on it).
    fn position(&self, pos: &AclPos) -> Position {
        let len = self.acl.prefix_len() as u64;
        if len == 0 {
            return Position::Unseen;
        }
        if self.acl.on_chain(pos) {
            return match self.acl.state_at(pos.seq) {
                Ok(s) => Position::On(Box::new(s)),
                Err(_) => Position::Unseen,
            };
        }
        let probe = pos.seq.min(len - 1);
        match self.acl.entry(probe) {
            Some(e) if e.term > pos.term => Position::Lost,
            _ => Position::Unseen,
        }
    }

    /// The record against the state at the position it names: its author was an active device
    /// there, its epoch is the one in force there, and it is not dated before that entry.
    fn check_at(&self, r: &Record, at: &AclState) -> Result<()> {
        if at.active_device(&r.author).is_none() {
            return Err(refused("author was not an active device at the ACL position it names"));
        }
        if at.epoch != r.epoch {
            return Err(refused("record epoch is not the epoch in force at its ACL position"));
        }
        if r.ts + acl::MAX_FUTURE_SKEW_S < at.frontier_ts {
            return Err(refused("record is dated before the ACL position it names"));
        }
        Ok(())
    }

    /// How many records wait for a chain position.
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }

    fn retention_s(&self) -> u64 {
        self.state().policy().retention_days * 24 * 3600
    }

    /// Whether `r` is past the link's retention: by our clock, or by the ACL chain's latest entry
    /// time, which every replica sees alike.
    fn past_retention(&self, r: &Record, now: u64) -> bool {
        let until = r.ts.saturating_add(self.retention_s());
        until <= now || until < self.state().frontier_ts
    }

    /// Open a verified, authorised, in-order record for this device: its status, cached body text,
    /// reason, and the opened body when it may be used here.
    #[allow(clippy::type_complexity)]
    fn open_here(
        &self,
        me: &Device,
        r: &Record,
        id: &str,
        writes_at: bool,
        now: u64,
    ) -> Result<(&'static str, Option<String>, Option<String>, Option<Body>)> {
        let s = self.state();
        let author_member = s.devices[&r.author].member.clone();
        let my_root = s
            .devices
            .get(&me.id_hex())
            .map(|d| d.member.clone())
            .unwrap_or_default();
        let own_fleet = my_root == author_member;
        // Write rights at the position it names, and still now.
        let writes = writes_at && s.members[&author_member].role.writes();
        let kinds = s.policy().kinds;
        Ok(match self.read_key(me, r.epoch) {
            _ if r.ct.is_none() => (
                store::OPAQUE,
                None,
                Some("retired before it reached us".to_owned()),
                None,
            ),
            Err(_) => (store::OPAQUE, None, None, None),
            Ok(key) => match r.open(&key.0, &kinds) {
                Err(e) => {
                    self.store.alarm("withheld", &r.author, &format!("{id}: {e}"), now)?;
                    (store::WITHHELD, None, Some(e.to_string()), None)
                }
                Ok(b) if b.kind != ACK_KIND && !writes => {
                    let why = "a fleet without write rights sent mail";
                    self.store.alarm("withheld", &r.author, &format!("{id}: {why}"), now)?;
                    (store::WITHHELD, None, Some(why.to_owned()), None)
                }
                Ok(b) => {
                    let text = String::from_utf8_lossy(&codec::canonical(&b)?).into_owned();
                    // Another fleet's ack is a receipt, never "own": promotion rules trust "own".
                    let status = if own_fleet {
                        store::OWN
                    } else if b.kind == ACK_KIND {
                        store::RECEIPT
                    } else {
                        store::ADMITTED
                    };
                    if b.kind == ACK_KIND {
                        self.take_receipts(&my_root, &author_member, &b, now)?;
                    }
                    (status, Some(text), None, Some(b))
                }
            },
        })
    }

    // ---------------------------------------------------------------------------------- blobs

    /// Total ciphertext a link's blob listing may reach. Past it, new blobs are not listed (so
    /// neither fetched nor served) and an alarm says so; own attachments are refused at write.
    pub const MAX_LINK_BLOB_BYTES: u64 = 1 << 30;
    /// On a mailbox, which cannot open bodies: the ciphertext one author's records may list.
    pub const MAILBOX_BLOB_BYTES_PER_AUTHOR: u64 = 256 << 20;

    /// Why `blobs` (id, name, ciphertext bytes) by `author` cannot be listed, if they cannot.
    fn blob_room(&self, author: &str, blobs: &[(String, String, u64)], mailbox: bool) -> Result<Option<String>> {
        let fresh: BTreeMap<&str, u64> = blobs
            .iter()
            .filter(|(id, _, _)| self.store.blob_listed(id).ok().flatten().is_none())
            .map(|(id, _, n)| (id.as_str(), *n))
            .collect();
        let adding: u64 = fresh.values().sum();
        for (id, _, n) in blobs {
            if let Some(listed) = self.store.blob_listed(id)?
                && listed != *n
            {
                return Ok(Some(format!("blob {id} is already listed with another size")));
            }
        }
        if blobs.iter().any(|(_, _, n)| *n > crate::record::MAX_BLOB_CT_BYTES) {
            return Ok(Some("a blob is over the size cap".into()));
        }
        if self.store.blob_bytes(None)? + adding > Self::MAX_LINK_BLOB_BYTES {
            return Ok(Some(format!(
                "the link's blobs would pass {} bytes",
                Self::MAX_LINK_BLOB_BYTES
            )));
        }
        if mailbox && self.store.blob_bytes(Some(author))? + adding > Self::MAILBOX_BLOB_BYTES_PER_AUTHOR {
            return Ok(Some(format!(
                "this author's blobs would pass {} bytes on this mailbox",
                Self::MAILBOX_BLOB_BYTES_PER_AUTHOR
            )));
        }
        Ok(None)
    }

    /// List a stored record's blobs, so they are fetched and served for this link. Only from a
    /// body opened and admitted here (whose blobs `Record::open` matched against the header), or,
    /// on a mailbox, from the signed header of a record it holds whole, within a per-author cap.
    /// Never from a withheld record, a receipt, or a header we could not open as a reader.
    fn register_blobs(
        &self,
        me: &Device,
        r: &Record,
        id: &str,
        status: &str,
        opened: Option<&Body>,
        now: u64,
    ) -> Result<()> {
        let mailbox = self.my_role(me) == Some(Role::Mailbox);
        let blobs: Vec<(String, String, u64)> = match opened {
            Some(b) if status == store::ADMITTED || status == store::OWN => b
                .blobs
                .iter()
                .map(|x| (x.id.clone(), x.name.clone(), crate::record::blob_ct_len(x.bytes)))
                .collect(),
            None if mailbox && status == store::OPAQUE && r.ct.is_some() => r
                .blobs
                .iter()
                .zip(&r.blob_sizes)
                .map(|(x, n)| (x.clone(), String::new(), *n))
                .collect(),
            _ => return Ok(()),
        };
        if blobs.is_empty() {
            return Ok(());
        }
        if let Some(why) = self.blob_room(&r.author, &blobs, mailbox)? {
            self.store.alarm("blob_cap", &r.author, &format!("{id}: {why}"), now)?;
            return Ok(());
        }
        for (blob, name, n) in &blobs {
            self.store.put_blob(blob, id, &r.author, name, *n)?;
        }
        Ok(())
    }

    /// Whether this link lists `blob`: the network layer serves a blob to a peer only for a link
    /// the peer shares with us AND that lists it, and fetches only listed blobs.
    pub fn blob_allowed(&self, blob: &str) -> Result<bool> {
        Ok(self.store.blob_listed(blob)?.is_some())
    }

    /// The blobs to fetch for this link, with the exact ciphertext length each record signed
    /// (never above `record::MAX_BLOB_CT_BYTES`): a fetcher refuses anything longer.
    pub fn wanted_blobs(&self) -> Result<Vec<(String, u64)>> {
        self.store.wanted_blobs()
    }

    /// The membership half of admission (header only, so a mailbox can apply it too), against the
    /// current state; the chain position the record names is checked after the feed's order
    /// (`position`, `check_at`).
    fn member_check(&self, r: &Record) -> Result<()> {
        let s = self.state();
        let dev = s
            .devices
            .get(&r.author)
            .ok_or_else(|| refused("author is not a device of this link"))?;
        let member = &s.members[&dev.member];
        if member.pending {
            return Err(refused("author's fleet is still pending"));
        }
        match dev.cut {
            Some(cut) if r.seq > cut => return Err(refused("author was removed before this record")),
            Some(_) => {}
            None if member.removed => return Err(refused("author's fleet was removed")),
            None => {}
        }
        if !member.role.reads() {
            return Err(refused("a mailbox writes nothing"));
        }
        // Renewals only ever extend `not_after`, so the latest certificate decides expiry: a record
        // written while the device was certified stays valid; one written after is refused.
        if r.ts >= dev.cert.not_after {
            return Err(refused("author's certificate had expired when the record was written"));
        }
        if self.store.frozen(&r.author)? {
            return Err(refused("author is frozen after equivocating"));
        }
        Ok(())
    }

    /// Receipts from `fleet`'s ack, for records written by our own fleet's devices.
    fn take_receipts(&self, my_root: &str, fleet: &str, ack: &Body, now: u64) -> Result<()> {
        let mine: BTreeSet<String> = self
            .state()
            .devices
            .iter()
            .filter(|(_, d)| d.member == my_root)
            .map(|(k, _)| k.clone())
            .collect();
        for (author, upto) in &ack.acks {
            if !mine.contains(author) {
                continue;
            }
            self.store.delivered_upto(author, *upto, fleet, now)?;
        }
        for id in &ack.read {
            self.store.receipt(id, fleet, "read", now)?;
        }
        Ok(())
    }

    /// An `ack` covering every other author we hold, if it says something new.
    pub fn ack(&mut self, device: &Device, read: Vec<String>, now: u64) -> Result<Option<String>> {
        let me = device.id_hex();
        let my_member = self
            .state()
            .devices
            .get(&me)
            .map(|d| d.member.clone())
            .unwrap_or_default();
        let acks: BTreeMap<String, u64> = self
            .store
            .heads()?
            .into_iter()
            .filter(|(a, _)| self.state().devices.get(a).is_some_and(|d| d.member != my_member))
            .map(|(a, (seq, _))| (a, seq))
            .collect();
        if (self.state().rotation_due && !self.rotates_now(device, now)) || self.acl.halt().is_some() {
            return Ok(None); // receipts wait for the new key (or the takeover) like any other mail
        }
        let summary = serde_json::to_string(&acks).expect("map serialises");
        if read.is_empty() && (acks.is_empty() || self.store.meta("last_ack")?.as_deref() == Some(&summary)) {
            return Ok(None);
        }
        let body = Body {
            kind: ACK_KIND.into(),
            sent_at: now,
            acks,
            read,
            ..Body::default()
        };
        let (id, _) = self.write(device, &body, now)?;
        self.store.set_meta("last_ack", &summary)?;
        Ok(Some(id))
    }

    /// Per author, what the peer lacks given its heads, in seq order: at most `limit` records.
    pub fn missing_for(&self, theirs: &BTreeMap<String, u64>, limit: usize) -> Result<Vec<Record>> {
        Ok(self.missing_for_authors(theirs, limit, usize::MAX, |_| true)?.0)
    }

    /// As `missing_for`, for the authors `only` selects, and within `bytes` (as
    /// `Record::frame_cost` counts them; the first record always fits). Returns the records, and
    /// whether the answer was cut short (by `limit` or `bytes`) with more left to send. Only what
    /// is sent, plus at most one page, is read from the store (review finding R8-2).
    pub fn missing_for_authors(
        &self,
        theirs: &BTreeMap<String, u64>,
        limit: usize,
        bytes: usize,
        only: impl Fn(&str) -> bool,
    ) -> Result<(Vec<Record>, bool)> {
        const PAGE: usize = 64;
        let mut out = Vec::new();
        let mut size = 0usize;
        for (author, (mine, _)) in self.store.heads()? {
            if !only(&author) {
                continue;
            }
            let mut have = theirs.get(&author).copied().unwrap_or(0);
            while mine > have {
                if bytes == 0 || out.len() >= limit || (size >= bytes && !out.is_empty()) {
                    return Ok((out, true));
                }
                let page = self.store.range(&author, have, mine, PAGE.min(limit - out.len()))?;
                let Some(last) = page.last().map(|r| r.seq) else {
                    break;
                };
                for r in page {
                    let n = r.frame_cost();
                    if !out.is_empty() && size.saturating_add(n) > bytes {
                        return Ok((out, true));
                    }
                    size = size.saturating_add(n);
                    out.push(r);
                }
                have = last;
            }
        }
        Ok((out, false))
    }

    pub fn heads(&self) -> Result<BTreeMap<String, u64>> {
        Ok(self.store.heads()?.into_iter().map(|(a, (s, _))| (a, s)).collect())
    }

    /// Drop bodies past the link's retention period.
    pub fn retire(&self, now: u64) -> Result<usize> {
        self.store.retire_before(now.saturating_sub(self.retention_s()))
    }

    // --------------------------------------------------------------------------- read models

    /// Admitted records after `cursor`, with provenance from the ACL, never from the body.
    pub fn events_after(&self, cursor: i64, limit: u32) -> Result<Vec<Value>> {
        let s = self.state();
        let mut out = Vec::new();
        for (id, sr) in self.store.events_after(cursor, limit)? {
            let body: Value = sr
                .body
                .as_deref()
                .map(serde_json::from_str)
                .transpose()
                .unwrap_or(None)
                .unwrap_or(Value::Null);
            let fleet_root = s
                .devices
                .get(&sr.record.author)
                .map(|d| d.member.clone())
                .unwrap_or_default();
            let fleet = s.label_of(&fleet_root);
            out.push(json!({
                "cursor": sr.cursor, "link": s.link_id, "link_name": s.name, "record_id": id,
                "device": sr.record.author, "fleet_root": fleet_root, "fleet": fleet,
                "seq": sr.record.seq, "epoch": sr.record.epoch, "received_at": sr.received_at,
                "seat_claim": body.get("seat").cloned().unwrap_or(Value::Null),
                "body": body,
            }));
        }
        Ok(out)
    }

    pub fn status(&self, device: &Device, now: u64) -> Result<Value> {
        let s = self.state();
        let heads = self.store.heads()?;
        let contacts: BTreeMap<String, u64> = {
            let mut st = self.store.conn.prepare("SELECT device, at FROM contacts")?;
            let rows = st.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)? as u64)))?;
            rows.collect::<std::result::Result<_, _>>()?
        };
        let me = device.id_hex();
        let my_root = device.root_hex();
        let members: Vec<Value> = s
            .members
            .values()
            .map(|m| {
                let devices: Vec<Value> = m
                    .devices
                    .iter()
                    .map(|d| {
                        let st = &s.devices[d];
                        json!({
                            "device": d, "label": st.cert.label, "removed": st.cut.is_some(), "cut": st.cut,
                            "cert_expires": st.cert.not_after, "cert_expired": !st.cert.valid_at(now),
                            "head": heads.get(d).map(|h| h.0).unwrap_or(0), "last_contact": contacts.get(d),
                            "frozen": self.store.frozen(d).unwrap_or(false), "me": *d == me,
                        })
                    })
                    .collect();
                let root = unhex::<32>(&m.root).unwrap_or([0; 32]);
                let mine = unhex::<32>(my_root).unwrap_or([0; 32]);
                let safety = safety_number(&mine, &root);
                json!({
                    "root": m.root, "label": m.label, "role": m.role.as_str(), "pending": m.pending,
                    "removed": m.removed, "us": m.root == my_root, "fingerprint": fleet_fingerprint(&root),
                    "safety_number": safety,
                    "verified": self.store.verified(&m.root).ok().flatten().is_some_and(|v| v == safety),
                    "devices": devices,
                })
            })
            .collect();
        let alarms: Vec<Value> = self
            .store
            .alarms()?
            .into_iter()
            .map(|(at, kind, author, detail)| json!({"at": at, "kind": kind, "author": author, "detail": detail}))
            .collect();
        let invites: Vec<Value> = s
            .invites
            .iter()
            .map(|(k, i)| {
                json!({"invite": k, "key": i.key, "role": i.role.as_str(), "expires": i.expires, "used": i.used,
                                  "revoked": i.revoked, "approval": i.approval, "expired": i.expires <= now})
            })
            .collect();
        let pending: Vec<Value> = s
            .pending_joins
            .iter()
            .map(|(j, root)| {
                json!({"join": j, "root": root, "label": s.members.get(root).map(|m| m.label.clone()),
                                     "needs_approval": s.members.get(root).is_some_and(|m| m.pending)})
            })
            .collect();
        let mut st = self.store.conn.prepare(
            "SELECT r.id, r.seq, r.body,
                    (SELECT GROUP_CONCAT(fleet || ':' || state) FROM receipts WHERE record_id = r.id)
             FROM records r WHERE r.author = ?1 ORDER BY r.seq DESC LIMIT 20",
        )?;
        let sent: Vec<Value> = st
            .query_map([&me], |r| {
                let body: Option<String> = r.get(2)?;
                let kind = body
                    .as_deref()
                    .and_then(|b| serde_json::from_str::<Value>(b).ok())
                    .and_then(|v| v.get("kind").cloned())
                    .unwrap_or(Value::Null);
                Ok(
                    json!({"record_id": r.get::<_, String>(0)?, "seq": r.get::<_, i64>(1)?, "kind": kind,
                          "receipts": r.get::<_, Option<String>>(3)?.unwrap_or_default()}),
                )
            })?
            .collect::<std::result::Result<_, _>>()?;
        let queued: i64 = self.store.conn.query_row(
            "SELECT COUNT(*) FROM records WHERE status = 'admitted' AND id NOT IN (SELECT record_id FROM promotions)",
            [],
            |r| r.get(0),
        )?;
        let (next, next_term) = s.next_sequencer();
        let label_of_device = |d: &str| {
            s.devices
                .get(d)
                .map(|x| format!("{}/{}", s.label_of(&x.member), x.cert.label))
                .unwrap_or_default()
        };
        let sequencer = json!({
            "device": s.sequencer, "label": label_of_device(&s.sequencer), "term": s.term,
            "handoff_to": s.handoff_to, "next": next, "next_label": label_of_device(&next), "next_term": next_term,
            "me": self.is_sequencer(device),
        });
        let equivocation = self.acl.halt().map(|h| {
            json!({"term": h.term, "seq": h.seq, "sequencer": h.ours.sequencer.device,
                   "ours": h.ours.hash().unwrap_or_default(), "theirs": h.theirs.hash().unwrap_or_default()})
        });
        let mut proposals = Vec::new();
        for status in ["queued", "refused"] {
            for q in self.store.proposals(status)?.into_iter().filter(|q| q.mine) {
                proposals
                    .push(json!({"id": q.id, "kind": q.proposal.kind, "status": q.status, "why": q.why, "at": q.at}));
            }
        }
        Ok(json!({
            "link": s.link_id, "name": s.name, "owner": s.owner, "epoch": s.epoch, "policy": s.policy(),
            "my_device": me, "my_role": self.my_role(device).map(Role::as_str), "rotation_due": s.rotation_due,
            "acl_entries": self.acl.prefix_len(), "acl_tip": self.acl.tip(), "acl_held_tip": self.acl.held_tip(),
            "halted_view": self.acl.halt().is_some(), "sequencer": sequencer,
            "equivocation": equivocation, "proposals": proposals,
            "members": members, "invites": invites,
            "pending_joins": pending, "alarms": alarms, "quarantine_unpromoted": queued, "sent": sent,
            "last_cursor": self.store.last_cursor()?,
        }))
    }
}

#[cfg(test)]
mod tests;
