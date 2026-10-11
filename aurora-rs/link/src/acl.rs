//! The link ACL: who is in a link, with which role, which devices, and which read key.
//!
//! ## One chain, one sequencer
//!
//! The ACL is a **linear chain** of entries. Each entry is
//! `{v, link, term, seq, prev, ts, sequencer, body, proposals, cuts, sig}`, signed by the device
//! that sequences its term. `seq` goes up by exactly one, `prev` is the hash of the entry before,
//! and `ts` never goes down. `link_id` is the hash of the genesis entry (`seq` 0, term 1).
//!
//! Membership is a pure fold: the state after entry `n` is entry `n` applied to the state after
//! entry `n - 1`. There is no resolution, no merge and no tie-break, because one key fixes the
//! order: nobody but the sequencer can place an entry, so nobody can backdate one into an
//! earlier position. Every authorisation check is a plain check against the linear state at the
//! point the entry applies. (The DAG of review rounds 1 to 4 let an author choose its parents,
//! and so what it was "concurrent" with; every rule that read time or precedence from a missing
//! causal edge became a weapon. Review round 5 is why it was replaced; see ADR 0011.)
//!
//! **The sequencer is trusted for order and time.** It cannot forge anyone's authority (every
//! proposal it includes carries its proposer's signature, and every check runs on every replica),
//! but it decides which valid proposals go in, in which order, and with which `ts`. A replica
//! refuses an entry dated more than `MAX_FUTURE_SKEW_S` ahead of its own clock.
//!
//! ## Proposals
//!
//! A device that is not the sequencer signs a [`Proposal`] `{link, kind, args, proposer, base,
//! expires, nonce}` (`base` is the chain position it saw). It travels to the sequencer by sync,
//! directly or relayed by any member (a relay keeps only what holds against the chain as it has
//! it, a join only on a live invite, within a size cap per kind: review finding R7-3). The
//! sequencer checks it against the chain's current state at the point it appends, not against
//! `base`, and includes it in an entry, which keeps the proposer's signature, so authority is
//! auditable. It refuses an invalid one with a reason it signs ([`ProposalRefusal`]); only the
//! current sequencer's refusal counts, at a position it sequenced (review finding R7-6). A proposal is included at most once (its id is its
//! hash), before its `expires` (at most `PROPOSAL_TTL_S` ahead of the entry), and its `base` must
//! be on the chain and not before the latest root takeover: a takeover may have dropped the entry
//! that included it, so it is void until signed again (review finding R6-6). The
//! sequencer's own actions are entries with a self-authored `body`.
//!
//! An action is known by its **action id**: the entry hash for a self-authored body, the
//! proposal id for a proposal. Invites are keyed by the action id that issued them, so a
//! non-sequencer admin can hand out an invite code before its proposal is included.
//!
//! ## Terms
//!
//! Term 1's sequencer is the owner's device that signs genesis (`Genesis::sequencer`). The
//! sequencer hands off with `handoff {to}`: the next entry must be term + 1, signed by `to`, an
//! active owner or admin device. When the sequencer is lost or compromised, the owner's **fleet
//! root** (the recovery phrase) signs [`Takeover`] `{link, term, after, sequencer}`; the named
//! device appends it as the first entry of the new term, right after `after`. Every replica then
//! drops the entries after `after`. Where two branches differ, the one whose first differing
//! entry has the higher term wins, and in one term a root takeover beats a handoff. The sequencer
//! must stay an active owner or admin device: to remove or demote it, hand off first (or take
//! over).
//!
//! **Equivocation**: two different entries at one `(term, seq)` on one prefix, each of which
//! applies on its own on the state before it (a dry run of every rule but cuts: the sequencer's
//! signature and authority, a takeover's root signature, named device and `after`, certificate
//! validity at `ts`, size). Anything less is not evidence: a forged copy proves nothing (review
//! finding R6-5). A replica that sees it keeps both entries as evidence ([`Equivocation`]),
//! raises an alarm, takes no entry past the common prefix but a root takeover, and waits for one.
//!
//! **A halt narrows, it never widens** (review finding R6-1). The replica keeps the state of
//! the chain it holds; what it acts on while halted ([`AclChain::state`]) is that state narrowed
//! to what the prefix grants too ([`AclState::narrowed`]): a device must be active in both, at the
//! lower of its two roles, and keys are the held tip's. Nothing new is sealed while halted.
//!
//! **Evidence below a later term start is an alarm, not a halt.** Once this replica's chain has
//! started a later term above the evidence's position, by a root takeover or by a device of
//! another member than the evidence's signer, honest replicas holding that term have committed to
//! it: fork choice keeps the branch whose first differing entry has the higher term, and both
//! entries of the pair share one. Halting then would protect nobody and would hand the old term's
//! key a veto it no longer holds. A term the signer started for itself (a handoff to its own
//! fleet's other device) does not count, so a malicious branch buys no immunity with
//! self-handoffs, and fork choice never prefers a branch for the terms it reached later. It does
//! count once the signer's device can no longer sequence and an action it could not have
//! authored itself (the owner's fleet's, or another member's) removed or demoted it (review
//! finding R7-5): a retired, removed device keeps no halt switch.
//!
//! **Evidence is bounded** (review finding R7-1). A replica keeps at most one pair per position
//! and signer (the first), one alarm-only pair per signer, and a halt only below the one it has,
//! and it decides that before any signature is checked or any state folded. An insert runs at
//! most one evidence check and stops there; the session that sent it pays for each check. The
//! store keeps at most [`MAX_EVIDENCE_PAIRS`]; only the current halt's pair is checked again when
//! the chain is restored, and it is checked as an evidence frame is, so a halt at the next
//! position survives a restart (R7-4).
//!
//! A root takeover continues after the replica's held tip by default; while halted below it,
//! `after` must be given (`AclChain::takeover` says what each choice drops).
//!
//! ## Rules that read the clock
//!
//! Invite expiry, the rotation grace, certificate validity and the renewal window are checked
//! against the entry's `ts`, which only the sequencer stamps and which is monotonic along the
//! chain. A renewed certificate (carried by an entry or a proposal, or by `add_device`) must
//! start at or before the stored one ends, come inside the renewal window, and come within one
//! lifetime after the stored one ends. Every certificate carries its device's proof of
//! possession (`identity::DeviceCert::verify`).
//!
//! ## Read keys
//!
//! Epoch 0's key is wrapped to the creator's devices in genesis. Every later change of who may
//! read carries wraps for exactly the devices that may read after it. A removal, and a role
//! change that takes read access away, either rotates in the same action or marks a rotation
//! due. An admin rotates at any time. While a rotation is due, the sequencer takes a rotation
//! from the designated device (`AclState::designated_rotator`: the sequencer itself when it holds
//! the key, else the lowest admin device holding it, else the lowest reading device holding it)
//! at once, and from any other reading device holding the key once `ROTATION_GRACE_S` has passed
//! since the entry that made it due. Each new key carries the previous key sealed under it.
//!
//! A wrap to another device cannot be checked by anyone but that device, so a malicious current
//! reader that may rotate can wrap junk. The device that gets junk finds it
//! (`AclState::bad_wrap`) and raises an alarm naming the author; an admin recovers with a
//! **recovery re-key** (`KeyChange.from`), which seals the key of the last epoch it can read.
//! Every key has a public key id (`crypto::key_id`), every wrap names the id of the key inside,
//! and readers check every key they unwrap against it.
//!
//! ## Cuts
//!
//! An entry that removes devices carries `cuts`: for each device it removes, the last feed seq
//! still accepted, the device's feed head as the sequencer holds it. `cuts` must name exactly
//! the devices the entry removes.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::sync::Arc;

use ed25519_dalek::SigningKey;
use imbl::OrdMap;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::codec::{self, b64, hex, unb64, unhex};
use crate::crypto::{self, KemSecrets, SUITE_X25519, SUITE_X25519_XWING, Secret32};
use crate::error::{LinkError, Result, refused};
use crate::identity::{CERT_MAX_LIFETIME_S, CERT_RENEW_WITHIN_S, Device, DeviceCert, MAX_LABEL};

/// The bridge kinds: the single allowlist, the same set as `core/comm/remote_relay.BRIDGE_KINDS`
/// (tests/test_link_contract.py pins the two together). No control kind crosses, ever.
pub const BRIDGE_KINDS: [&str; 7] = ["blocker", "chat", "completion", "handoff", "note", "question", "reply"];

/// The ACL entry format: 2 is the sequenced chain (1 was the DAG of review rounds 1 to 4).
pub const ENTRY_VERSION: u32 = 2;
pub const PROPOSAL_VERSION: u32 = 1;
pub const MAX_DEVICES_PER_MEMBER: usize = 8;
pub const MAX_INVITE_TTL_S: u64 = 30 * 24 * 3600;
pub const DEFAULT_INVITE_TTL_S: u64 = 24 * 3600;
/// How far an entry's timestamp may run ahead of the verifier's clock.
pub const MAX_FUTURE_SKEW_S: u64 = 600;
/// The most members a link's policy may allow (`Policy::max_members`).
pub const MAX_LINK_MEMBERS: u64 = 32;
/// The largest single ACL entry, canonical bytes. It is sized so the largest entry a link's
/// policy allows always fits (review finding R6-3): a key change wrapped to every device the
/// policy allows (`MAX_LINK_MEMBERS` x `MAX_DEVICES_PER_MEMBER`, all X-Wing, about 1,840 bytes
/// each) carried by a proposal, with both certificates, is about 480 KiB. One entry always fits
/// one sync frame (`sync::MAX_FRAME`, 2 MiB). The sequencer signs no larger entry.
pub const MAX_ENTRY_BYTES: usize = 512 * 1024;
/// How long a due rotation waits for its designated device before the sequencer takes one from
/// any other reading device holding the key.
pub const ROTATION_GRACE_S: u64 = 3600;
/// How long a proposal stays includable: it carries its own expiry (`Proposal::expires`), at most
/// this far (plus `MAX_FUTURE_SKEW_S`) ahead of the entry that includes it. Proposers set it this
/// far ahead of their clock.
pub const PROPOSAL_TTL_S: u64 = 7 * 24 * 3600;
/// The sequencer takes at most this many proposals per member root per day (its own admission
/// policy, not a validity rule; an admin gets `MAX_ADMIN_PROPOSALS_PER_DAY`).
pub const MAX_MEMBER_PROPOSALS_PER_DAY: usize = 32;
pub const MAX_ADMIN_PROPOSALS_PER_DAY: usize = 512;
/// A state snapshot is kept every this many entries, so the state at any position is at most
/// this many applications away.
const CHECKPOINT_EVERY: u64 = 256;
/// How far back a replica asks when a received entry does not link to its chain.
pub const BACKOFF_STEP: u64 = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    /// Pull-only: fetches and serves ciphertext, never holds a read key.
    Mailbox,
    Reader,
    Writer,
    Admin,
    Owner,
}

impl Role {
    pub fn reads(self) -> bool {
        self >= Role::Reader
    }
    pub fn writes(self) -> bool {
        self >= Role::Writer
    }
    pub fn admin(self) -> bool {
        self >= Role::Admin
    }
    pub fn parse(s: &str) -> Result<Self> {
        serde_json::from_value(Value::String(s.to_owned())).map_err(|_| refused(format!("unknown role {s:?}")))
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Role::Mailbox => "mailbox",
            Role::Reader => "reader",
            Role::Writer => "writer",
            Role::Admin => "admin",
            Role::Owner => "owner",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Policy {
    /// Kinds this link carries; a subset of `BRIDGE_KINDS`.
    pub kinds: Vec<String>,
    /// After this many days, bodies and blobs are dropped and signed headers kept.
    pub retention_days: u64,
    pub max_members: u64,
    /// Per-author record quota per hour; past it, records wait for the next hour.
    pub rate_per_hour: u64,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            kinds: BRIDGE_KINDS.iter().map(|k| (*k).to_owned()).collect(),
            retention_days: 90,
            max_members: 16,
            rate_per_hour: 600,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Wrap {
    /// The epoch whose key this wraps: it must be the epoch in force where the action applies.
    pub epoch: u64,
    /// The key id (`crypto::key_id`) of the key inside.
    pub key_id: String,
    pub device: String,
    pub suite: u8,
    pub enc: String,
    pub ct: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct KeyChange {
    pub epoch: u64,
    /// The key id of the new key.
    pub key_id: String,
    pub wraps: Vec<Wrap>,
    /// The previous epoch's key, sealed under this one (absent only for epoch 0).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prev: Option<String>,
    /// The key id of the key `prev` seals.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prev_id: Option<String>,
    /// A recovery re-key: the epoch whose key `prev` seals, when it is not the one in force
    /// (that key was junk to its author). Only an admin holding a wrap at `from` rotates so.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub from: Option<u64>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Genesis {
    pub name: String,
    pub owner: String,
    /// The owner fleet's name, as members see it.
    pub label: String,
    pub policy: Policy,
    pub devices: Vec<DeviceCert>,
    /// Term 1's sequencer: the owner's device that signs genesis.
    pub sequencer: String,
    pub key: KeyChange,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Invite {
    /// The invite key's public half; a join's proof must verify under it.
    pub invite: String,
    pub role: Role,
    pub expires: u64,
    pub single_use: bool,
    pub approval: bool,
}

/// A join, always a proposal by the joining device (which is its only device for now).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Join {
    /// The action id that issued the invite.
    pub invite: String,
    /// The invite key's signature over (link, invite, root, device, nonce): `join_proof_bytes`.
    pub proof: String,
    pub label: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Accept {
    /// The join's proposal id.
    pub join: String,
    pub wraps: Vec<Wrap>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Decline {
    pub join: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AddDevice {
    pub cert: DeviceCert,
    pub wraps: Vec<Wrap>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RemoveDevice {
    pub device: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rotate: Option<KeyChange>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SetRole {
    pub member: String,
    pub role: Role,
    /// Wraps for the member's devices when the change gives it read access.
    #[serde(default)]
    pub wraps: Vec<Wrap>,
    /// The new key, required when the change takes read access away.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rotate: Option<KeyChange>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RemoveMember {
    pub member: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rotate: Option<KeyChange>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RevokeInvite {
    /// The action id that issued the invite.
    pub invite: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Handoff {
    /// The device that sequences the next term.
    pub to: String,
}

/// A chain position: what a record names, and what a takeover continues after.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AclPos {
    pub term: u64,
    pub seq: u64,
    pub hash: String,
}

/// The owner root's order to start a new term after `after`, sequenced by `sequencer`.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Takeover {
    pub term: u64,
    pub after: AclPos,
    pub sequencer: String,
    /// The fleet root's signature (purpose `acl-takeover`) over `takeover_bytes`.
    pub sig: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "op", content = "body", rename_all = "snake_case")]
pub enum Op {
    Genesis(Genesis),
    Invite(Invite),
    Join(Join),
    Accept(Accept),
    Decline(Decline),
    AddDevice(AddDevice),
    RemoveDevice(RemoveDevice),
    SetRole(SetRole),
    RemoveMember(RemoveMember),
    RotateKey(KeyChange),
    RevokeInvite(RevokeInvite),
    Handoff(Handoff),
    Takeover(Takeover),
}

impl Op {
    pub fn name(&self) -> &'static str {
        match self {
            Op::Genesis(_) => "genesis",
            Op::Invite(_) => "invite",
            Op::Join(_) => "join",
            Op::Accept(_) => "accept",
            Op::Decline(_) => "decline",
            Op::AddDevice(_) => "add_device",
            Op::RemoveDevice(_) => "remove_device",
            Op::SetRole(_) => "set_role",
            Op::RemoveMember(_) => "remove_member",
            Op::RotateKey(_) => "rotate_key",
            Op::RevokeInvite(_) => "revoke_invite",
            Op::Handoff(_) => "handoff",
            Op::Takeover(_) => "takeover",
        }
    }

    fn args(&self) -> Result<Value> {
        let tagged = serde_json::to_value(self).map_err(|e| refused(e.to_string()))?;
        Ok(tagged["body"].clone())
    }

    fn from_parts(kind: &str, args: &Value) -> Result<Self> {
        serde_json::from_value(json!({"op": kind, "body": args}))
            .map_err(|e| refused(format!("ACL action {kind:?} is malformed: {e}")))
    }
}

// ------------------------------------------------------------------------------------- proposals

/// The chain position a proposer saw.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Base {
    pub term: u64,
    pub seq: u64,
}

/// An action signed by a device that is not the sequencer, for the sequencer to include.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Proposal {
    pub v: u32,
    pub link: String,
    pub kind: String,
    pub args: Value,
    pub proposer: DeviceCert,
    pub base: Base,
    /// No entry dated at or after this includes it (review finding R6-6).
    pub expires: u64,
    /// 16 random bytes, hex: two proposals of the same action differ.
    pub nonce: String,
    pub sig: String,
}

impl Proposal {
    fn unsigned_bytes(&self) -> Result<Vec<u8>> {
        codec::jcs(&json!({
            "v": self.v, "link": self.link, "kind": self.kind, "args": self.args,
            "proposer": serde_json::to_value(&self.proposer).map_err(|e| refused(e.to_string()))?,
            "base": {"term": self.base.term, "seq": self.base.seq}, "expires": self.expires,
            "nonce": self.nonce,
        }))
    }

    /// The proposal id: sha256 of the canonical proposal, signature included.
    pub fn id(&self) -> Result<String> {
        Ok(hex(&crypto::sha256(&[&codec::canonical(self)?])))
    }

    pub fn parsed(&self) -> Result<Op> {
        Op::from_parts(&self.kind, &self.args)
    }

    /// Sign `op` as `device`, on the chain position `base`, includable until `expires`.
    pub fn sign(device: &Device, link: &str, op: &Op, base: Base, expires: u64) -> Result<Self> {
        Self::sign_with_nonce(device, link, op, base, expires, &hex(&crypto::random_bytes(16)))
    }

    fn sign_with_nonce(device: &Device, link: &str, op: &Op, base: Base, expires: u64, nonce: &str) -> Result<Self> {
        if matches!(op, Op::Genesis(_) | Op::Takeover(_)) {
            return Err(refused("genesis and takeover are never proposed"));
        }
        let mut p = Proposal {
            v: PROPOSAL_VERSION,
            link: link.to_owned(),
            kind: op.name().to_owned(),
            args: op.args()?,
            proposer: device.cert.clone(),
            base,
            expires,
            nonce: nonce.to_owned(),
            sig: String::new(),
        };
        p.sig = b64(&crypto::sign(&device.sign, "acl-proposal", &p.unsigned_bytes()?));
        Ok(p)
    }

    /// Shape, the proposer's certificate (with its proof of possession) and its signature.
    pub fn verify_signature(&self) -> Result<()> {
        self.verify_with(&mut HashSet::new())
    }

    /// The largest proposal of `kind`, canonical bytes (review finding R6-4): a key change may
    /// wrap to every reading device the policy allows; an accept to one member's devices; every
    /// other action is a certificate or two and a few ids.
    pub fn max_bytes(kind: &str) -> usize {
        match kind {
            "rotate_key" | "remove_member" | "remove_device" | "set_role" => MAX_ENTRY_BYTES - 32 * 1024,
            "accept" => 48 * 1024,
            _ => 16 * 1024,
        }
    }

    fn verify_with(&self, certs: &mut HashSet<String>) -> Result<()> {
        if self.v != PROPOSAL_VERSION {
            return Err(refused("unknown proposal version"));
        }
        if codec::canonical(self)?.len() > Self::max_bytes(&self.kind) {
            return Err(refused(format!("a {} proposal is larger than it may be", self.kind)));
        }
        if unhex::<16>(&self.nonce).is_err() {
            return Err(refused("a proposal's nonce is 16 bytes, hex"));
        }
        if matches!(self.kind.as_str(), "genesis" | "takeover") {
            return Err(refused("genesis and takeover are never proposed"));
        }
        check_cert(&self.proposer, certs)?;
        crypto::verify(
            &unhex::<32>(&self.proposer.device)?,
            "acl-proposal",
            &self.unsigned_bytes()?,
            &unb64(&self.sig)?,
        )
    }
}

/// The sequencer's signed refusal of a proposal, so any member can relay it to the proposer.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProposalRefusal {
    pub link: String,
    pub id: String,
    pub why: String,
    /// The chain position the proposal was checked against.
    pub at: AclPos,
    /// The sequencer device that refused it.
    pub by: String,
    pub sig: String,
}

impl ProposalRefusal {
    fn bytes(&self) -> Result<Vec<u8>> {
        codec::jcs(&json!({
            "link": self.link, "id": self.id, "why": self.why,
            "at": {"term": self.at.term, "seq": self.at.seq, "hash": self.at.hash}, "by": self.by,
        }))
    }

    pub fn sign(device: &Device, link: &str, id: &str, why: &str, at: AclPos) -> Result<Self> {
        let mut r = ProposalRefusal {
            link: link.to_owned(),
            id: id.to_owned(),
            why: why.chars().take(300).collect(),
            at,
            by: device.id_hex(),
            sig: String::new(),
        };
        r.sig = b64(&crypto::sign(&device.sign, "acl-refusal", &r.bytes()?));
        Ok(r)
    }

    /// The signature, by the device it names.
    pub fn verify(&self) -> Result<()> {
        if self.why.chars().count() > 300 {
            return Err(refused("a refusal reason is at most 300 characters"));
        }
        crypto::verify(
            &unhex::<32>(&self.by)?,
            "acl-refusal",
            &self.bytes()?,
            &unb64(&self.sig)?,
        )
    }
}

fn check_cert(cert: &DeviceCert, certs: &mut HashSet<String>) -> Result<()> {
    if !certs.contains(&cert.sig) {
        cert.verify()?;
        certs.insert(cert.sig.clone());
    }
    Ok(())
}

// ---------------------------------------------------------------------------------------- entries

/// One signed ACL entry, exactly as it travels.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub v: u32,
    /// The link id ("" for genesis).
    pub link: String,
    pub term: u64,
    pub seq: u64,
    /// The hash of the entry before ("" for genesis).
    pub prev: String,
    pub ts: u64,
    /// The certificate of the device that sequences this term and signs the entry.
    pub sequencer: DeviceCert,
    /// The sequencer's own action, if any.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub body: Option<Op>,
    /// Proposals included, applied after `body`, in order.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub proposals: Vec<Proposal>,
    /// For each device this entry removes: the last feed seq still accepted.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub cuts: BTreeMap<String, u64>,
    pub sig: String,
}

impl Entry {
    fn unsigned_bytes(&self) -> Result<Vec<u8>> {
        let mut v = serde_json::to_value(self).map_err(|e| refused(e.to_string()))?;
        if let Some(o) = v.as_object_mut() {
            o.remove("sig");
        }
        codec::jcs(&v)
    }

    /// sha256 of the canonical entry, signature included. The genesis hash is the link id.
    pub fn hash(&self) -> Result<String> {
        Ok(hex(&crypto::sha256(&[&codec::canonical(self)?])))
    }

    pub fn pos(&self) -> Result<AclPos> {
        Ok(AclPos {
            term: self.term,
            seq: self.seq,
            hash: self.hash()?,
        })
    }

    fn takeover(&self) -> Option<&Takeover> {
        match &self.body {
            Some(Op::Takeover(t)) => Some(t),
            _ => None,
        }
    }

    /// The names of the actions it carries, for status and logs.
    pub fn actions(&self) -> Vec<&str> {
        let mut out: Vec<&str> = self.body.iter().map(Op::name).collect();
        out.extend(self.proposals.iter().map(|p| p.kind.as_str()));
        out
    }

    #[allow(clippy::too_many_arguments)]
    fn sign(
        device: &Device,
        link: &str,
        term: u64,
        seq: u64,
        prev: &str,
        ts: u64,
        body: Option<Op>,
        proposals: Vec<Proposal>,
        cuts: BTreeMap<String, u64>,
    ) -> Result<Self> {
        let mut e = Entry {
            v: ENTRY_VERSION,
            link: link.to_owned(),
            term,
            seq,
            prev: prev.to_owned(),
            ts,
            sequencer: device.cert.clone(),
            body,
            proposals,
            cuts,
            sig: String::new(),
        };
        e.sig = b64(&crypto::sign(&device.sign, "acl", &e.unsigned_bytes()?));
        Ok(e)
    }

    /// This entry signed again by `device`, whatever it carries (tests build entries no
    /// sequencer would sign).
    #[cfg(test)]
    pub(crate) fn resigned(mut self, device: &Device) -> Self {
        self.sequencer = device.cert.clone();
        self.sig = String::new();
        self.sig = b64(&crypto::sign(
            &device.sign,
            "acl",
            &self.unsigned_bytes().expect("canonical"),
        ));
        self
    }

    /// The sequencer's certificate and signature (not the proposals': they are checked where
    /// they apply).
    pub fn verify_signature(&self) -> Result<()> {
        self.verify_with(&mut HashSet::new())
    }

    fn verify_with(&self, certs: &mut HashSet<String>) -> Result<()> {
        if self.v != ENTRY_VERSION {
            return Err(refused("unknown ACL entry version"));
        }
        check_cert(&self.sequencer, certs)?;
        crypto::verify(
            &unhex::<32>(&self.sequencer.device)?,
            "acl",
            &self.unsigned_bytes()?,
            &unb64(&self.sig)?,
        )
    }
}

// --------------------------------------------------------------------------------------- invites

/// The invite key both sides derive from the invite secret. Only its public half enters the log.
pub fn invite_key(secret: &[u8; 32]) -> SigningKey {
    crypto::signing_key(&crypto::sha256(&[crypto::CONTEXT, b"invite\0", secret]))
}

/// The bytes an invite key signs in a join (also checked at the join door, `sync::JoinDoor`):
/// the link, the action that issued the invite, the joining root and device, and the
/// proposal's nonce, so a proof is good for exactly one proposal.
pub(crate) fn join_proof_bytes(link: &str, invite: &str, root: &str, device: &str, nonce: &str) -> Result<Vec<u8>> {
    codec::jcs(&json!({"link": link, "invite": invite, "root": root, "device": device, "nonce": nonce}))
}

/// What a joiner holds of an invite: the secret, and the action id that issued it (both travel
/// in the invite code).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InviteTicket {
    pub secret: [u8; 32],
    pub entry: String,
}

impl InviteTicket {
    /// The invite key's public half, as the issuing action names it.
    pub fn key(&self) -> String {
        hex(&crypto::public_of(&invite_key(&self.secret)))
    }
}

/// A join proposal for `device` from an invite ticket, on the chain position `base`, includable
/// until `expires`.
pub fn make_join(
    device: &Device,
    ticket: &InviteTicket,
    link: &str,
    base: Base,
    label: &str,
    expires: u64,
) -> Result<Proposal> {
    let nonce = hex(&crypto::random_bytes(16));
    let proof = crypto::sign(
        &invite_key(&ticket.secret),
        "join",
        &join_proof_bytes(link, &ticket.entry, device.root_hex(), &device.id_hex(), &nonce)?,
    );
    let op = Op::Join(Join {
        invite: ticket.entry.clone(),
        proof: b64(&proof),
        label: label.to_owned(),
    });
    Proposal::sign_with_nonce(device, link, &op, base, expires, &nonce)
}

fn takeover_bytes(link: &str, term: u64, after: &AclPos, sequencer: &str) -> Result<Vec<u8>> {
    codec::jcs(&json!({
        "link": link, "term": term, "sequencer": sequencer,
        "after": {"term": after.term, "seq": after.seq, "hash": after.hash},
    }))
}

// ------------------------------------------------------------------------------------------ state

#[derive(Clone, Debug, Serialize)]
pub struct DeviceState {
    pub cert: DeviceCert,
    pub member: String,
    /// Set once removed: the last seq of this device's feed that is still accepted.
    pub cut: Option<u64>,
}

impl DeviceState {
    pub fn new(cert: DeviceCert, member: String) -> Self {
        Self {
            cert,
            member,
            cut: None,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct MemberState {
    pub root: String,
    pub label: String,
    pub role: Role,
    pub pending: bool,
    pub removed: bool,
    pub devices: BTreeSet<String>,
    /// The action that admitted this member (the join's proposal id; genesis for the owner).
    pub joined: String,
}

/// An invite, by the action id that issued it (`AclState::invites`).
#[derive(Clone, Debug, Serialize)]
pub struct InviteState {
    /// The invite key's public half; a join's proof must verify under it.
    pub key: String,
    pub role: Role,
    pub expires: u64,
    pub single_use: bool,
    pub approval: bool,
    pub used: bool,
    /// The device whose join used it (so that device may fetch the log again at the door).
    pub used_by: Option<String>,
    pub revoked: bool,
    pub by: String,
}

/// Who signed an action, as the state knew them before it.
#[derive(Clone, Debug)]
struct Author {
    device: String,
    root: String,
    role: Role,
    owner: bool,
}

/// What applying one entry needs from the chain before it.
struct Past<'a> {
    /// The entries before it, by seq.
    entries: &'a [Entry],
    /// Proposals included so far, by id.
    included: &'a HashMap<String, u64>,
    /// Verified certificates, by signature.
    certs: &'a mut HashSet<String>,
    /// Entries this process already accepted once: their signatures are not checked again.
    verified: bool,
}

/// The cuts of the entry being applied: `None` in a dry run (the sequencer finding out which
/// devices an action removes), where every new cut is 0 and nothing is checked.
struct Cuts<'a> {
    given: Option<&'a BTreeMap<String, u64>>,
    taken: BTreeSet<String>,
}

impl Cuts<'_> {
    fn cut(&mut self, device: &str) -> u64 {
        self.taken.insert(device.to_owned());
        self.given.and_then(|g| g.get(device).copied()).unwrap_or(0)
    }
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct AclState {
    pub link_id: String,
    pub name: String,
    pub owner: String,
    pub policy: Option<Policy>,
    pub members: OrdMap<String, MemberState>,
    pub devices: OrdMap<String, DeviceState>,
    pub invites: OrdMap<String, InviteState>,
    pub epoch: u64,
    /// The key id of each epoch's key.
    pub key_ids: OrdMap<u64, String>,
    /// Every wrap ever issued, by epoch.
    pub wraps: OrdMap<u64, Vec<Wrap>>,
    /// Epoch k's `prev`: the key of epoch k-1 (or of `prev_from[k]`) sealed under epoch k's.
    pub prev_keys: OrdMap<u64, String>,
    /// For a recovery re-key to epoch k: the earlier epoch whose key its `prev` seals.
    pub prev_from: OrdMap<u64, u64>,
    /// Who filed each wrap (epoch, device): the author of the action that carried it.
    #[serde(skip)]
    pub wrapped_by: OrdMap<(u64, String), String>,
    pub rotation_due: bool,
    /// When the rotation became due: the `ts` of the entry that made it due.
    pub rotation_due_since: u64,
    /// Joins waiting for an `accept`: join proposal id -> member root.
    pub pending_joins: OrdMap<String, String>,
    /// The position of the last entry applied.
    pub term: u64,
    pub seq: u64,
    pub tip: String,
    /// The `ts` of the last entry applied.
    pub frontier_ts: u64,
    /// The device sequencing the current term.
    pub sequencer: String,
    /// A handoff waiting for its target to start the next term.
    pub handoff_to: Option<String>,
    /// The seq of the latest root takeover (0 before any): a proposal on a base before it is
    /// void, since the takeover may have dropped an entry that included it (review finding R6-6).
    pub takeover_at: u64,
    /// Proposals included per member root, by entry `ts` (the sequencer's admission policy).
    #[serde(skip)]
    proposals_by: OrdMap<String, Vec<u64>>,
}

impl AclState {
    pub fn policy(&self) -> Policy {
        self.policy.clone().unwrap_or_default()
    }

    /// The position of the last entry applied.
    pub fn pos(&self) -> AclPos {
        AclPos {
            term: self.term,
            seq: self.seq,
            hash: self.tip.clone(),
        }
    }

    /// The label a member is shown and addressed by (unique among live members).
    pub fn label_of(&self, root: &str) -> String {
        self.members.get(root).map(|m| m.label.clone()).unwrap_or_default()
    }

    /// The member and role behind an active device, if it is one.
    pub fn active_device(&self, device: &str) -> Option<(&MemberState, &DeviceState)> {
        let d = self.devices.get(device)?;
        let m = self.members.get(&d.member)?;
        (d.cut.is_none() && !m.removed && !m.pending).then_some((m, d))
    }

    /// Whether `device` is an active device of an owner or admin member: who may sequence.
    pub fn may_sequence(&self, device: &str) -> bool {
        self.active_device(device).is_some_and(|(m, _)| m.role.admin())
    }

    /// The device that signs the next entry, and that entry's term.
    pub fn next_sequencer(&self) -> (String, u64) {
        match &self.handoff_to {
            Some(to) => (to.clone(), self.term + 1),
            None => (self.sequencer.clone(), self.term),
        }
    }

    /// Devices that must hold the current read key.
    pub fn keyed_devices(&self) -> BTreeSet<String> {
        self.members
            .values()
            .filter(|m| !m.removed && !m.pending && m.role.reads())
            .flat_map(|m| m.devices.iter())
            .filter(|d| self.devices.get(*d).is_some_and(|s| s.cut.is_none()))
            .cloned()
            .collect()
    }

    /// Devices that may sync with us: every active device of every active member, mailboxes too.
    pub fn sync_devices(&self) -> BTreeSet<String> {
        #[cfg(test)]
        SYNC_BUILDS.with(|n| n.set(n.get() + 1));
        self.devices
            .keys()
            .filter(|d| self.active_device(d).is_some())
            .cloned()
            .collect()
    }

    pub fn has_wrap(&self, epoch: u64, device: &str) -> bool {
        self.wraps
            .get(&epoch)
            .is_some_and(|ws| ws.iter().any(|w| w.device == device))
    }

    /// The key id of the epoch in force.
    pub fn key_id(&self) -> &str {
        self.key_ids.get(&self.epoch).map_or("", String::as_str)
    }

    /// HPKE `info` for a wrap. It binds the owner root rather than the link id, because genesis
    /// wraps exist before the link id does, and the key id, so a wrap only opens as the key it
    /// claims to carry. `crypto::wrap` adds the suite.
    fn wrap_info(&self, epoch: u64, device: &str, key_id: &str) -> Vec<u8> {
        [
            self.owner.as_bytes(),
            b"|",
            epoch.to_string().as_bytes(),
            b"|",
            device.as_bytes(),
            b"|",
            key_id.as_bytes(),
        ]
        .concat()
    }

    /// Wrap `key` (the key of `epoch`) to each of `devices`.
    pub fn make_wraps(&self, key: &[u8; 32], epoch: u64, devices: &BTreeSet<String>) -> Result<Vec<Wrap>> {
        let key_id = hex(&crypto::key_id(epoch, key));
        devices
            .iter()
            .map(|d| {
                let cert = &self
                    .devices
                    .get(d)
                    .ok_or_else(|| refused(format!("unknown device {d}")))?
                    .cert;
                let (suite, enc, ct) = crypto::wrap(key, &cert.kem()?, &self.wrap_info(epoch, d, &key_id))?;
                Ok(Wrap {
                    epoch,
                    key_id: key_id.clone(),
                    device: d.clone(),
                    suite,
                    enc: b64(&enc),
                    ct: b64(&ct),
                })
            })
            .collect()
    }

    /// Refuse `key` unless it is the key the log names for `epoch`.
    fn check_key_id(&self, epoch: u64, key: &Secret32) -> Result<()> {
        match self.key_ids.get(&epoch) {
            Some(id) if *id == hex(&crypto::key_id(epoch, &key.0)) => Ok(()),
            _ => Err(refused(format!(
                "the key for epoch {epoch} does not match the key id the log names"
            ))),
        }
    }

    /// This device's key for `epoch`: unwrap directly, or walk back from a later epoch. Every
    /// key on the way is checked against its epoch's key id. A wrap that fails (junk) is passed
    /// over for the next one, and a recovery re-key's `prev` jumps back over the epochs it
    /// recovered from.
    pub fn read_key(&self, epoch: u64, device: &str, kem: &KemSecrets) -> Result<Secret32> {
        let mut last: Option<LinkError> = None;
        for (e, wraps) in self.wraps.range(epoch..) {
            let Some(w) = wraps.iter().find(|w| w.device == device) else {
                continue;
            };
            match self.walk_back(*e, w, epoch, device, kem) {
                Ok(Some(key)) => return Ok(key),
                Ok(None) => {}
                Err(err) => last = Some(err),
            }
        }
        Err(last.unwrap_or_else(|| LinkError::Unavailable(format!("no read key for epoch {epoch}"))))
    }

    /// Open `w` (this device's wrap at `at`) and walk back to `epoch`. `None` when a recovery
    /// jumps past `epoch`.
    fn walk_back(&self, at: u64, w: &Wrap, epoch: u64, device: &str, kem: &KemSecrets) -> Result<Option<Secret32>> {
        let mut key = self.unwrap_own(at, w, device, kem)?;
        let mut at = at;
        while at > epoch {
            let sealed = self
                .prev_keys
                .get(&at)
                .ok_or_else(|| refused(format!("epoch {at} carries no previous key")))?;
            let from = self.prev_from.get(&at).copied().unwrap_or(at - 1);
            if from < epoch {
                return Ok(None);
            }
            let plain = crypto::open(&key.0, &unb64(sealed)?, &self.prev_key_aad(at, from))?;
            key = Secret32(
                plain
                    .as_slice()
                    .try_into()
                    .map_err(|_| refused("previous key has the wrong length"))?,
            );
            at = from;
            self.check_key_id(at, &key)?;
        }
        Ok(Some(key))
    }

    fn unwrap_own(&self, at: u64, w: &Wrap, device: &str, kem: &KemSecrets) -> Result<Secret32> {
        let key = crypto::unwrap(
            w.suite,
            &unb64(&w.enc)?,
            &unb64(&w.ct)?,
            kem,
            &self.wrap_info(at, device, &w.key_id),
        )?;
        self.check_key_id(at, &key)?;
        Ok(key)
    }

    /// When this device holds a wrap at `epoch` that does not open to the key the log names
    /// (junk, wrapped by a rogue key holder): the author of the action that filed it.
    pub fn bad_wrap(&self, epoch: u64, device: &str, kem: &KemSecrets) -> Option<String> {
        let w = self.wraps.get(&epoch)?.iter().find(|w| w.device == device)?;
        self.unwrap_own(epoch, w, device, kem).err()?;
        Some(
            self.wrapped_by
                .get(&(epoch, device.to_owned()))
                .cloned()
                .unwrap_or_default(),
        )
    }

    fn prev_key_aad(&self, epoch: u64, from: u64) -> Vec<u8> {
        let mut aad = [self.link_id.as_bytes(), b"|prev|", epoch.to_string().as_bytes()].concat();
        if from + 1 != epoch {
            aad.extend_from_slice(format!("|from|{from}").as_bytes());
        }
        aad
    }

    fn file_wraps(&mut self, epoch: u64, wraps: &[Wrap], author: &str) {
        for w in wraps {
            self.wrapped_by.insert((epoch, w.device.clone()), author.to_owned());
        }
        self.wraps.entry(epoch).or_default().extend(wraps.iter().cloned());
    }

    /// The device the sequencer takes a due rotation from at once: the sequencer itself when it
    /// holds the key, else the lowest active admin device holding it, else the lowest active
    /// reading device holding it. `gone` is left out (a device being removed in the same action).
    pub fn designated_rotator(&self, gone: Option<&str>) -> Option<String> {
        let holds = |d: &str| Some(d) != gone && self.has_wrap(self.epoch, d);
        if holds(&self.sequencer) && self.may_sequence(&self.sequencer) {
            return Some(self.sequencer.clone());
        }
        let pick = |admin: bool| {
            self.devices
                .keys()
                .filter(|d| {
                    holds(d)
                        && self
                            .active_device(d)
                            .is_some_and(|(m, _)| if admin { m.role.admin() } else { m.role.reads() })
                })
                .min()
                .cloned()
        };
        pick(true).or_else(|| pick(false))
    }

    /// Whether `device`, which is no admin, may rotate a due rotation at `ts`: it reads and holds
    /// the key, and it is the designated device, or `ts` is past `since` plus the grace.
    pub fn may_rotate_due(&self, device: &str, ts: u64, since: u64, gone: Option<&str>) -> bool {
        self.active_device(device).is_some_and(|(m, _)| m.role.reads())
            && self.has_wrap(self.epoch, device)
            && (self.designated_rotator(gone).as_deref() == Some(device)
                || ts >= since.saturating_add(ROTATION_GRACE_S))
    }

    /// Whether `device` may rotate at `ts`: an admin at any time, anyone else only a due
    /// rotation, as `may_rotate_due` says.
    pub fn may_rotate(&self, device: &str, ts: u64) -> bool {
        match self.active_device(device) {
            Some((m, _)) if m.role.admin() => true,
            Some(_) => self.rotation_due && self.may_rotate_due(device, ts, self.rotation_due_since, None),
            None => false,
        }
    }

    /// A complete key change to `epoch + 1` for the devices that may read after it.
    pub fn new_key_change(&self, current: &Secret32, keyed: &BTreeSet<String>) -> Result<(KeyChange, Secret32)> {
        self.check_key_id(self.epoch, current)?;
        let next = Secret32::random();
        let epoch = self.epoch + 1;
        let prev = crypto::seal(&next.0, &current.0, &self.prev_key_aad(epoch, self.epoch));
        Ok((
            KeyChange {
                epoch,
                key_id: hex(&crypto::key_id(epoch, &next.0)),
                wraps: self.make_wraps(&next.0, epoch, keyed)?,
                prev: Some(b64(&prev)),
                prev_id: Some(self.key_id().to_owned()),
                from: None,
            },
            next,
        ))
    }

    /// A recovery re-key to `epoch + 1`: the key in force is junk to this admin, which seals the
    /// key of `from` instead, the last epoch it can read (`old`).
    pub fn recovery_key_change(
        &self,
        from: u64,
        old: &Secret32,
        keyed: &BTreeSet<String>,
    ) -> Result<(KeyChange, Secret32)> {
        if from >= self.epoch {
            return Err(refused("a recovery re-key seals an earlier epoch's key"));
        }
        self.check_key_id(from, old)?;
        let next = Secret32::random();
        let epoch = self.epoch + 1;
        let prev = crypto::seal(&next.0, &old.0, &self.prev_key_aad(epoch, from));
        Ok((
            KeyChange {
                epoch,
                key_id: hex(&crypto::key_id(epoch, &next.0)),
                wraps: self.make_wraps(&next.0, epoch, keyed)?,
                prev: Some(b64(&prev)),
                prev_id: self.key_ids.get(&from).cloned(),
                from: Some(from),
            },
            next,
        ))
    }

    /// Wraps must carry the key `key_id` of `epoch`, cover exactly `expected`, and use the suite
    /// each device's certificate allows.
    fn check_wraps(
        &self,
        epoch: u64,
        key_id: &str,
        wraps: &[Wrap],
        expected: &BTreeSet<String>,
        extra: &[DeviceCert],
    ) -> Result<()> {
        let got: BTreeSet<&str> = wraps.iter().map(|w| w.device.as_str()).collect();
        if got.len() != wraps.len() {
            return Err(refused("a device is wrapped to twice"));
        }
        if !got.iter().copied().eq(expected.iter().map(String::as_str)) {
            return Err(refused("wraps do not cover exactly the devices that may read"));
        }
        for w in wraps {
            if w.epoch != epoch {
                return Err(refused("a wrap names another epoch than the one in force"));
            }
            if w.key_id != key_id {
                return Err(refused("a wrap carries another key than the one in force"));
            }
            let cert = extra
                .iter()
                .find(|c| c.device == w.device)
                .or_else(|| self.devices.get(&w.device).map(|d| &d.cert))
                .ok_or_else(|| refused("wrap names an unknown device"))?;
            let (suite, enc_len, ct_len) = if cert.xwing.is_some() {
                (SUITE_X25519_XWING, 32 + 1120, 32 + 16 + 16)
            } else {
                (SUITE_X25519, 32, 32 + 16)
            };
            if w.suite != suite || unb64(&w.enc)?.len() != enc_len || unb64(&w.ct)?.len() != ct_len {
                return Err(refused("wrap suite or size does not match the device's certificate"));
            }
        }
        Ok(())
    }

    /// Check a key change to the next epoch by `author`, for readers `keyed`.
    fn check_key_change(&self, k: &KeyChange, author: &str, keyed: &BTreeSet<String>) -> Result<()> {
        if k.epoch != self.epoch + 1 {
            return Err(refused("key change does not advance the epoch by one"));
        }
        unhex::<32>(&k.key_id)?;
        match k.from {
            None => {
                if !self.has_wrap(self.epoch, author) {
                    return Err(refused("a key change needs an author that holds the read key"));
                }
                if k.prev_id.as_deref() != Some(self.key_id()) {
                    return Err(refused("key change seals another key than the one in force"));
                }
            }
            // A recovery re-key (the caller checks that its author is an admin).
            Some(from) => {
                if from >= self.epoch || !self.has_wrap(from, author) {
                    return Err(refused(
                        "a recovery re-key seals an earlier epoch's key its author holds a wrap for",
                    ));
                }
                if k.prev_id.as_ref() != self.key_ids.get(&from) {
                    return Err(refused("a recovery re-key seals another key than the one it names"));
                }
            }
        }
        let sealed = unb64(
            k.prev
                .as_deref()
                .ok_or_else(|| refused("key change lacks the previous key"))?,
        )?;
        if sealed.len() != crypto::NONCE_LEN + 32 + crypto::TAG_LEN {
            return Err(refused("sealed previous key has the wrong size"));
        }
        self.check_wraps(k.epoch, &k.key_id, &k.wraps, keyed, &[])
    }

    fn apply_key_change(&mut self, k: &KeyChange, author: &str) {
        self.epoch = k.epoch;
        self.key_ids.insert(k.epoch, k.key_id.clone());
        if let Some(p) = &k.prev {
            self.prev_keys.insert(k.epoch, p.clone());
        }
        if let Some(from) = k.from {
            self.prev_from.insert(k.epoch, from);
        }
        self.file_wraps(k.epoch, &k.wraps, author);
        self.rotation_due = false;
    }

    /// A removal's key change: checked against the readers left, or a rotation left due.
    fn removal_key(
        &mut self,
        rotate: Option<&KeyChange>,
        author: &str,
        keyed: &BTreeSet<String>,
        ts: u64,
    ) -> Result<()> {
        match rotate {
            Some(k) if k.from.is_some() => Err(refused("a recovery re-key travels on its own")),
            Some(k) => {
                self.check_key_change(k, author, keyed)?;
                self.apply_key_change(k, author);
                Ok(())
            }
            None => {
                self.mark_due(ts);
                Ok(())
            }
        }
    }

    fn mark_due(&mut self, ts: u64) {
        if !self.rotation_due {
            self.rotation_due = true;
            self.rotation_due_since = ts;
        }
    }

    /// The readers left once `gone` stop reading.
    fn keyed_without<'a>(&self, gone: impl IntoIterator<Item = &'a String>) -> BTreeSet<String> {
        let mut keyed = self.keyed_devices();
        for d in gone {
            keyed.remove(d);
        }
        keyed
    }

    /// A member's devices that are not cut.
    fn live_devices_of(&self, member: &MemberState) -> BTreeSet<String> {
        member
            .devices
            .iter()
            .filter(|d| self.devices.get(*d).is_some_and(|s| s.cut.is_none()))
            .cloned()
            .collect()
    }

    fn live_members(&self) -> usize {
        self.members.values().filter(|m| !m.removed).count()
    }

    /// How many proposals by `root` the chain included within a day before `ts`.
    pub fn proposals_today(&self, root: &str, ts: u64) -> usize {
        let from = ts.saturating_sub(24 * 3600);
        self.proposals_by
            .get(root)
            .map_or(0, |v| v.iter().filter(|t| **t > from).count())
    }

    /// The state a halted replica acts on (review finding R6-1): this state (the held tip's) with
    /// every device that is not also active in `prefix` (the state where the chain halted) left
    /// out, every member that is not a live member there too counted as pending, and every member
    /// at the lower of its two roles. Removed devices keep their cuts. Keys are the held tip's,
    /// so nothing is ever sealed or checked under a key a removal retired. Positions are the
    /// prefix's: nothing past it is final.
    ///
    /// So a halt never makes a device active, or a role higher, than the held tip says.
    pub fn narrowed(&self, prefix: &AclState) -> AclState {
        let mut v = self.clone();
        for (root, m) in self.members.iter() {
            let vm = v.members.get_mut(root).expect("cloned");
            match prefix.members.get(root) {
                Some(p) if !p.removed && p.joined == m.joined => {
                    vm.role = vm.role.min(p.role);
                    vm.pending |= p.pending;
                }
                _ => vm.pending = true,
            }
        }
        for (d, ds) in self.devices.iter() {
            if ds.cut.is_none() && prefix.active_device(d).is_none() {
                v.devices.remove(d);
                if let Some(m) = v.members.get_mut(&ds.member) {
                    m.devices.remove(d);
                }
            }
        }
        v.term = prefix.term;
        v.seq = prefix.seq;
        v.tip = prefix.tip.clone();
        v.frontier_ts = prefix.frontier_ts;
        v.sequencer = prefix.sequencer.clone();
        v.handoff_to = prefix.handoff_to.clone();
        v
    }

    // -------------------------------------------------------------------------------- applying

    /// The entry `e` (hash `hash`) applied to this state, or why it does not apply. `self` is the
    /// state after the entry before it. Returns the new state and the ids of the proposals it
    /// included.
    /// In a dry run (`dry`), the entry's cuts are not checked: the result names the devices it
    /// removes.
    fn apply_entry(
        &self,
        e: &Entry,
        hash: &str,
        past: &mut Past<'_>,
        dry: bool,
    ) -> Result<(AclState, Vec<String>, BTreeSet<String>)> {
        if !past.verified {
            e.verify_with(past.certs)?;
        } else if e.v != ENTRY_VERSION {
            return Err(refused("unknown ACL entry version"));
        }
        let mut s = self.clone();
        if s.link_id.is_empty() {
            s.apply_genesis(e, hash, past)?;
            return Ok((s, Vec::new(), BTreeSet::new()));
        }
        if e.link != s.link_id {
            return Err(refused("ACL entry belongs to another link"));
        }
        if e.seq != s.seq + 1 || e.prev != s.tip {
            return Err(refused("ACL entry does not follow the chain's last entry"));
        }
        if e.ts < s.frontier_ts {
            return Err(refused("ACL entry is dated before the entry it follows"));
        }
        if e.body.is_none() && e.proposals.is_empty() {
            return Err(refused("an ACL entry carries an action"));
        }
        if matches!(e.body, Some(Op::Genesis(_))) {
            return Err(refused("a link has exactly one genesis"));
        }
        let signer = e.sequencer.device.clone();
        // Who may sign this entry, in which term.
        let starts_term = if let Some(t) = e.takeover() {
            if e.term <= s.term || t.term != e.term {
                return Err(refused("a takeover starts a later term"));
            }
            if t.after != s.pos() {
                return Err(refused("a takeover names another position than the one it follows"));
            }
            if t.sequencer != signer {
                return Err(refused("a takeover is appended by the device it names"));
            }
            crypto::verify(
                &unhex::<32>(&s.owner)?,
                "acl-takeover",
                &takeover_bytes(&s.link_id, t.term, &t.after, &t.sequencer)?,
                &unb64(&t.sig)?,
            )
            .map_err(|_| refused("a takeover must be signed by the owner's fleet root"))?;
            true
        } else {
            match &s.handoff_to {
                Some(to) if e.term == s.term + 1 && *to == signer => true,
                Some(_) => {
                    return Err(refused(
                        "after a handoff, the next entry starts the next term, signed by its target",
                    ));
                }
                None if e.term == s.term && signer == s.sequencer => false,
                None => return Err(refused("ACL entry is not signed by this term's sequencer")),
            }
        };
        if !s.may_sequence(&signer) {
            return Err(refused("the sequencer must be an active owner or admin device"));
        }
        let seq_author = s.author_for(&e.sequencer, e.ts)?;
        if starts_term {
            s.sequencer = signer.clone();
            s.handoff_to = None;
            s.term = e.term;
            if e.takeover().is_some() {
                s.takeover_at = e.seq;
            }
        }
        let mut cuts = Cuts {
            given: (!dry).then_some(&e.cuts),
            taken: BTreeSet::new(),
        };
        let mut ids = Vec::new();
        if let Some(op) = &e.body
            && !matches!(op, Op::Takeover(_))
        {
            s.apply_action(&seq_author, op, hash, e.ts, &mut cuts, past.verified, true)?;
        }
        for p in &e.proposals {
            let id = p.id()?;
            if ids.contains(&id) {
                return Err(refused("a proposal is included once"));
            }
            s.apply_proposal(p, &id, e.ts, past, &mut cuts)?;
            ids.push(id);
        }
        let named: BTreeSet<&String> = e.cuts.keys().collect();
        if !dry && named != cuts.taken.iter().collect() {
            return Err(refused("an entry's cuts must name exactly the devices it removes"));
        }
        s.check_sequencer()?;
        s.seq = e.seq;
        s.tip = hash.to_owned();
        s.frontier_ts = e.ts;
        Ok((s, ids, cuts.taken))
    }

    /// The sequencer (or the handoff's target) must still be an active owner or admin device.
    fn check_sequencer(&self) -> Result<()> {
        let (next, _) = self.next_sequencer();
        if !self.may_sequence(&next) {
            return Err(refused(
                "this would leave the link without its sequencer: hand the sequencer off first",
            ));
        }
        Ok(())
    }

    /// Who `cert` is: an active member device with the same keys, valid at `ts`, whose carried
    /// renewal (if any) is in bounds. The renewal is filed.
    fn author_for(&mut self, cert: &DeviceCert, ts: u64) -> Result<Author> {
        let (m, d) = self
            .active_device(&cert.device)
            .ok_or_else(|| refused("author is not an active member device"))?;
        if !d.cert.same_keys(cert) {
            return Err(refused("author certificate does not match the one in the log"));
        }
        if !cert.valid_at(ts) {
            return Err(refused("author certificate is not valid at the entry's time"));
        }
        if cert.not_after > d.cert.not_after {
            check_renewal(&d.cert, cert, ts)?;
        }
        let author = Author {
            device: cert.device.clone(),
            root: m.root.clone(),
            role: m.role,
            owner: m.root == self.owner,
        };
        if let Some(d) = self.devices.get_mut(&cert.device)
            && cert.not_after > d.cert.not_after
        {
            d.cert = cert.clone();
        }
        Ok(author)
    }

    fn apply_proposal(
        &mut self,
        p: &Proposal,
        id: &str,
        ts: u64,
        past: &mut Past<'_>,
        cuts: &mut Cuts<'_>,
    ) -> Result<()> {
        if !past.verified {
            p.verify_with(past.certs)?;
        }
        if p.link != self.link_id {
            return Err(refused("proposal belongs to another link"));
        }
        if past.included.contains_key(id) {
            return Err(refused("that proposal was already included"));
        }
        // Its base must be on this chain, and not before the latest takeover (which may have
        // dropped an entry that included it); it must not have expired, nor name an expiry
        // further ahead than a proposer may (review finding R6-6).
        let base_ok = past
            .entries
            .get(p.base.seq as usize)
            .is_some_and(|b| b.term == p.base.term);
        if !base_ok || p.base.seq > self.seq {
            return Err(refused("the proposal's base is not on this chain: propose again"));
        }
        if p.base.seq < self.takeover_at {
            return Err(refused(
                "the proposal was signed before the latest takeover, which may have dropped it: propose again",
            ));
        }
        if ts >= p.expires {
            return Err(refused("the proposal expired: propose again"));
        }
        if p.expires > ts.saturating_add(PROPOSAL_TTL_S + MAX_FUTURE_SKEW_S) {
            return Err(refused(
                "the proposal's expiry is further ahead than a proposal may last",
            ));
        }
        let op = p.parsed()?;
        match &op {
            Op::Genesis(_) | Op::Takeover(_) => Err(refused("genesis and takeover are never proposed")),
            Op::Join(j) => self.apply_join(p, j, id, ts, past.verified),
            _ => {
                let author = self.author_for(&p.proposer, ts)?;
                self.apply_action(&author, &op, id, ts, cuts, past.verified, false)?;
                let root = author.root.clone();
                let mut v: Vec<u64> = self.proposals_by.get(&root).cloned().unwrap_or_default();
                v.retain(|t| t.saturating_add(24 * 3600) > ts);
                v.push(ts);
                self.proposals_by.insert(root, v);
                Ok(())
            }
        }
    }

    /// Check and apply one action (`id` is its action id). Every check runs before the first
    /// change; the caller works on a copy, so an error leaves nothing behind.
    #[allow(clippy::too_many_arguments)]
    fn apply_action(
        &mut self,
        a: &Author,
        op: &Op,
        id: &str,
        ts: u64,
        cuts: &mut Cuts<'_>,
        verified: bool,
        by_sequencer: bool,
    ) -> Result<()> {
        let key_id = self.key_id().to_owned();
        match op {
            Op::Genesis(_) | Op::Join(_) | Op::Takeover(_) => {
                return Err(refused("that action cannot be applied here"));
            }
            Op::Invite(i) => {
                if !a.role.admin() {
                    return Err(refused("only an admin may invite"));
                }
                if i.role == Role::Owner || (i.role == Role::Admin && !a.owner) {
                    return Err(refused("that role cannot be granted by invite from this author"));
                }
                unhex::<32>(&i.invite)?;
                if i.expires <= ts || i.expires - ts > MAX_INVITE_TTL_S {
                    return Err(refused("invite expiry is in the past or too far ahead"));
                }
                self.invites.insert(
                    id.to_owned(),
                    InviteState {
                        key: i.invite.clone(),
                        role: i.role,
                        expires: i.expires,
                        single_use: i.single_use,
                        approval: i.approval,
                        used: false,
                        used_by: None,
                        revoked: false,
                        by: a.root.clone(),
                    },
                );
            }
            Op::Accept(acc) => {
                if !a.role.admin() || !self.has_wrap(self.epoch, &a.device) {
                    return Err(refused("only an admin holding the read key may accept"));
                }
                let root = self
                    .pending_joins
                    .get(&acc.join)
                    .cloned()
                    .ok_or_else(|| refused("no such pending join"))?;
                let member = self
                    .members
                    .get(&root)
                    .ok_or_else(|| refused("pending member vanished"))?;
                let expected = if member.role.reads() {
                    self.live_devices_of(member)
                } else {
                    BTreeSet::new()
                };
                self.check_wraps(self.epoch, &key_id, &acc.wraps, &expected, &[])?;
                self.file_wraps(self.epoch, &acc.wraps, &a.device);
                self.pending_joins.remove(&acc.join);
                if let Some(m) = self.members.get_mut(&root) {
                    m.pending = false;
                }
            }
            Op::Decline(d) => {
                if !a.role.admin() {
                    return Err(refused("only an admin may decline"));
                }
                let root = self
                    .pending_joins
                    .get(&d.join)
                    .cloned()
                    .ok_or_else(|| refused("no such pending join"))?;
                let member = self
                    .members
                    .get(&root)
                    .ok_or_else(|| refused("pending member vanished"))?;
                if !member.pending {
                    return Err(refused("that join was already admitted; remove the member instead"));
                }
                let devices = member.devices.clone();
                self.pending_joins.remove(&d.join);
                self.members.get_mut(&root).expect("checked").removed = true;
                for dev in devices {
                    let c = cuts.cut(&dev);
                    if let Some(s) = self.devices.get_mut(&dev) {
                        s.cut = Some(c);
                    }
                }
            }
            Op::AddDevice(add) => {
                if !verified {
                    add.cert.verify()?;
                }
                let member_root = add.cert.root.clone();
                if member_root != a.root && !a.role.admin() {
                    return Err(refused("only the member itself or an admin may add a device"));
                }
                let member = self
                    .members
                    .get(&member_root)
                    .ok_or_else(|| refused("certificate root is not a member"))?;
                if member.removed || member.pending {
                    return Err(refused("that member is not active"));
                }
                let reads = member.role.reads();
                if let Some(existing) = self.devices.get(&add.cert.device) {
                    // A device renewing itself carries the renewal on the action too, so it is
                    // already filed (`author_for`): nothing more to do.
                    if add.cert.device == a.device && existing.cert == add.cert && add.wraps.is_empty() {
                        return Ok(());
                    }
                    // A renewal: same keys, later expiry, no new wraps, in bounds.
                    if !existing.cert.same_keys(&add.cert)
                        || existing.cut.is_some()
                        || add.cert.not_after <= existing.cert.not_after
                    {
                        return Err(refused(
                            "device already listed; only a later renewal of the same keys is allowed",
                        ));
                    }
                    check_renewal(&existing.cert, &add.cert, ts)?;
                    if !add.wraps.is_empty() {
                        return Err(refused("a renewal carries no wraps"));
                    }
                    self.devices.get_mut(&add.cert.device).expect("checked").cert = add.cert.clone();
                } else {
                    if !add.cert.valid_at(ts) {
                        return Err(refused("new device certificate is not valid at the entry's time"));
                    }
                    if member.devices.len() >= MAX_DEVICES_PER_MEMBER {
                        return Err(refused("member already has the maximum number of devices"));
                    }
                    let expected: BTreeSet<String> = if reads {
                        [add.cert.device.clone()].into()
                    } else {
                        BTreeSet::new()
                    };
                    if reads && !self.has_wrap(self.epoch, &a.device) {
                        return Err(refused(
                            "adding a reading device needs an author that holds the read key",
                        ));
                    }
                    self.check_wraps(
                        self.epoch,
                        &key_id,
                        &add.wraps,
                        &expected,
                        std::slice::from_ref(&add.cert),
                    )?;
                    self.devices.insert(
                        add.cert.device.clone(),
                        DeviceState::new(add.cert.clone(), member_root.clone()),
                    );
                    self.members
                        .get_mut(&member_root)
                        .expect("checked")
                        .devices
                        .insert(add.cert.device.clone());
                    self.file_wraps(self.epoch, &add.wraps, &a.device);
                }
            }
            Op::RemoveDevice(r) => {
                let target = self.devices.get(&r.device).ok_or_else(|| refused("no such device"))?;
                if target.cut.is_some() {
                    return Err(refused("device already removed"));
                }
                let target_member = target.member.clone();
                if target_member != a.root && !a.role.admin() {
                    return Err(refused("only the member itself or an admin may remove a device"));
                }
                if target_member == self.owner && !a.owner {
                    return Err(refused("only the owner may remove an owner device"));
                }
                if target_member != a.root && self.members[&target_member].role == Role::Admin && !a.owner {
                    return Err(refused("only the owner may remove an admin's device"));
                }
                if target_member == self.owner && self.live_devices_of(&self.members[&target_member]).len() <= 1 {
                    return Err(refused("the owner's last device cannot be removed"));
                }
                if r.device == a.device && r.rotate.is_some() {
                    return Err(refused("a device that removes itself cannot pick the next key"));
                }
                // A member that is no admin, removing its own other device, picks the next key
                // only when it may rotate the rotation the removal makes due.
                if r.rotate.is_some() && !a.role.admin() {
                    let since = if self.rotation_due { self.rotation_due_since } else { ts };
                    if !self.may_rotate_due(&a.device, ts, since, Some(&r.device)) {
                        return Err(refused(
                            "only the device designated to rotate (or any key holder after the grace) picks the next key",
                        ));
                    }
                }
                let keyed = self.keyed_without([&r.device]);
                let c = cuts.cut(&r.device);
                self.devices.get_mut(&r.device).expect("checked").cut = Some(c);
                self.removal_key(r.rotate.as_ref(), &a.device, &keyed, ts)?;
            }
            Op::SetRole(sr) => {
                let target = self.members.get(&sr.member).ok_or_else(|| refused("no such member"))?;
                if target.removed || target.pending {
                    return Err(refused("that member is not active"));
                }
                if sr.role == Role::Owner || sr.member == self.owner {
                    return Err(refused("the owner role is fixed at genesis"));
                }
                if sr.role == target.role {
                    return Err(refused("that member already has that role"));
                }
                let admin_change = sr.role == Role::Admin || target.role == Role::Admin;
                if !(a.owner || (a.role.admin() && !admin_change)) {
                    return Err(refused("this author may not make that role change"));
                }
                let was_reading = target.role.reads();
                let live = self.live_devices_of(target);
                let granting = sr.role.reads() && !was_reading;
                let losing = was_reading && !sr.role.reads();
                if granting {
                    if !self.has_wrap(self.epoch, &a.device) {
                        return Err(refused("granting read access needs an author that holds the read key"));
                    }
                    self.check_wraps(self.epoch, &key_id, &sr.wraps, &live, &[])?;
                } else if !sr.wraps.is_empty() {
                    return Err(refused("this role change carries no wraps"));
                }
                if !losing && sr.rotate.is_some() {
                    return Err(refused("this role change carries no key change"));
                }
                if losing && sr.rotate.is_none() {
                    return Err(refused("a role change that takes read access away must rotate the key"));
                }
                if granting {
                    self.file_wraps(self.epoch, &sr.wraps, &a.device);
                }
                if losing {
                    let keyed = self.keyed_without(&live);
                    self.removal_key(sr.rotate.as_ref(), &a.device, &keyed, ts)?;
                }
                self.members.get_mut(&sr.member).expect("checked").role = sr.role;
            }
            Op::RemoveMember(r) => {
                let target = self.members.get(&r.member).ok_or_else(|| refused("no such member"))?;
                if target.removed {
                    return Err(refused("member already removed"));
                }
                if r.member == self.owner {
                    return Err(refused("the owner cannot be removed or leave"));
                }
                let leaving = r.member == a.root;
                if !leaving && !(a.role.admin() && (a.owner || target.role < Role::Admin)) {
                    return Err(refused(
                        "only an admin may remove a member, and only the owner may remove an admin",
                    ));
                }
                if leaving && r.rotate.is_some() {
                    return Err(refused("a member that leaves cannot pick the next key"));
                }
                let devices = target.devices.clone();
                let keyed = self.keyed_without(&devices);
                self.members.get_mut(&r.member).expect("checked").removed = true;
                let pending: Vec<String> = self
                    .pending_joins
                    .iter()
                    .filter(|(_, root)| **root == r.member)
                    .map(|(j, _)| j.clone())
                    .collect();
                for j in pending {
                    self.pending_joins.remove(&j);
                }
                for d in devices {
                    if self.devices.get(&d).is_some_and(|s| s.cut.is_none()) {
                        let c = cuts.cut(&d);
                        self.devices.get_mut(&d).expect("checked").cut = Some(c);
                    }
                }
                self.removal_key(r.rotate.as_ref(), &a.device, &keyed, ts)?;
            }
            Op::RotateKey(k) => {
                if k.from.is_some() && !a.role.admin() {
                    return Err(refused("only an admin re-keys to recover"));
                }
                if !self.may_rotate(&a.device, ts) {
                    return Err(refused(
                        "only an admin may rotate, or, while a rotation is due, the device designated to (any key holder after the grace)",
                    ));
                }
                let keyed = self.keyed_devices();
                self.check_key_change(k, &a.device, &keyed)?;
                self.apply_key_change(k, &a.device);
            }
            Op::RevokeInvite(r) => {
                if !a.role.admin() {
                    return Err(refused("only an admin may revoke an invite"));
                }
                let inv = self
                    .invites
                    .get_mut(&r.invite)
                    .ok_or_else(|| refused("no such invite"))?;
                // A reusable invite stays revocable after its first use: that is when it matters.
                if inv.revoked || (inv.single_use && inv.used) {
                    return Err(refused("invite is already used or revoked"));
                }
                inv.revoked = true;
            }
            Op::Handoff(h) => {
                if !(by_sequencer || a.owner) {
                    return Err(refused(
                        "only the sequencer, or an owner device, hands the sequencer off",
                    ));
                }
                if self.handoff_to.is_some() {
                    return Err(refused("a handoff is already waiting for its target"));
                }
                if h.to == self.sequencer {
                    return Err(refused("that device already sequences this link"));
                }
                if !self.may_sequence(&h.to) {
                    return Err(refused("the sequencer is handed to an active owner or admin device"));
                }
                self.handoff_to = Some(h.to.clone());
            }
        }
        Ok(())
    }

    fn apply_genesis(&mut self, e: &Entry, hash: &str, past: &mut Past<'_>) -> Result<()> {
        let Some(Op::Genesis(g)) = &e.body else {
            return Err(refused("the first ACL entry is genesis"));
        };
        if e.seq != 0 || !e.prev.is_empty() || !e.link.is_empty() || e.term != 1 {
            return Err(refused("genesis has seq 0, term 1, no prev and no link"));
        }
        if !e.proposals.is_empty() || !e.cuts.is_empty() {
            return Err(refused("genesis carries nothing but itself"));
        }
        for text in [&g.name, &g.label] {
            if text.is_empty() || text.chars().count() > MAX_LABEL || text.chars().any(char::is_control) {
                return Err(refused(
                    "link or fleet name is empty, too long, or has control characters",
                ));
            }
        }
        if g.policy.kinds.iter().any(|k| !BRIDGE_KINDS.contains(&k.as_str())) || g.policy.kinds.is_empty() {
            return Err(refused("link policy names a kind outside the bridge allowlist"));
        }
        if g.policy.max_members < 2
            || g.policy.max_members > MAX_LINK_MEMBERS
            || g.policy.retention_days == 0
            || g.policy.rate_per_hour == 0
        {
            return Err(refused("link policy limits are out of range"));
        }
        unhex::<32>(&g.owner)?;
        if e.sequencer.root != g.owner || g.sequencer != e.sequencer.device {
            return Err(refused("genesis is signed by the owner's device it names as sequencer"));
        }
        if !e.sequencer.valid_at(e.ts) {
            return Err(refused("the sequencer's certificate is not valid at genesis"));
        }
        if g.devices.is_empty() || g.devices.len() > MAX_DEVICES_PER_MEMBER {
            return Err(refused("genesis lists no devices, or too many"));
        }
        if !g.devices.iter().any(|d| d.same_keys(&e.sequencer)) {
            return Err(refused("genesis lists its sequencer among the owner's devices"));
        }
        let mut devices = BTreeSet::new();
        for c in &g.devices {
            if !past.verified {
                check_cert(c, past.certs)?;
            }
            if c.root != g.owner || !c.valid_at(e.ts) || !devices.insert(c.device.clone()) {
                return Err(refused(
                    "genesis device is not the owner's, not valid now, or listed twice",
                ));
            }
        }
        if g.key.epoch != 0 || g.key.prev.is_some() || g.key.prev_id.is_some() || g.key.from.is_some() {
            return Err(refused("genesis key must be epoch 0 with no previous key"));
        }
        unhex::<32>(&g.key.key_id)?;
        self.owner = g.owner.clone();
        self.check_wraps(0, &g.key.key_id, &g.key.wraps, &devices, &g.devices)?;
        self.link_id = hash.to_owned();
        self.name = g.name.clone();
        self.policy = Some(g.policy.clone());
        for c in &g.devices {
            self.devices
                .insert(c.device.clone(), DeviceState::new(c.clone(), g.owner.clone()));
        }
        self.members.insert(
            g.owner.clone(),
            MemberState {
                root: g.owner.clone(),
                label: g.label.clone(),
                role: Role::Owner,
                pending: false,
                removed: false,
                devices,
                joined: hash.to_owned(),
            },
        );
        self.key_ids.insert(0, g.key.key_id.clone());
        self.file_wraps(0, &g.key.wraps, &e.sequencer.device);
        self.term = 1;
        self.seq = 0;
        self.tip = hash.to_owned();
        self.frontier_ts = e.ts;
        self.sequencer = g.sequencer.clone();
        Ok(())
    }

    fn apply_join(&mut self, p: &Proposal, j: &Join, id: &str, ts: u64, verified: bool) -> Result<()> {
        let inv = self
            .invites
            .get(&j.invite)
            .ok_or_else(|| refused("no such invite"))?
            .clone();
        if inv.revoked {
            return Err(refused("invite was revoked"));
        }
        if inv.single_use && inv.used {
            return Err(refused("invite was already used"));
        }
        if ts >= inv.expires {
            return Err(refused("invite had expired"));
        }
        // An invite is only as good as its inviter: removed or demoted, their invites die.
        if self
            .members
            .get(&inv.by)
            .is_none_or(|m| m.removed || m.pending || !m.role.admin())
        {
            return Err(refused("the inviter is no longer an admin of this link"));
        }
        let cert = &p.proposer;
        let root = cert.root.clone();
        if let Some(m) = self.members.get(&root)
            && !m.removed
        {
            return Err(refused("that fleet is already a member"));
        }
        if self.live_members() as u64 >= self.policy().max_members {
            return Err(refused("the link is full"));
        }
        if j.label.is_empty() || j.label.chars().count() > MAX_LABEL || j.label.chars().any(char::is_control) {
            return Err(refused("fleet label is empty, too long, or has control characters"));
        }
        // Labels name members in commands and in @fleet/seat addresses, so they must be unique
        // and must not look like a root key.
        if j.label.len() == 64 && j.label.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err(refused("a fleet label cannot look like a root key"));
        }
        if self
            .members
            .values()
            .any(|m| !m.removed && m.label.eq_ignore_ascii_case(&j.label))
        {
            return Err(refused("another member already uses that fleet label"));
        }
        if !cert.valid_at(ts) || self.devices.contains_key(&cert.device) {
            return Err(refused("joining device is expired or already known"));
        }
        if !verified {
            let proof = join_proof_bytes(&self.link_id, &j.invite, &root, &cert.device, &p.nonce)?;
            crypto::verify(&unhex::<32>(&inv.key)?, "join", &proof, &unb64(&j.proof)?)
                .map_err(|_| refused("the join's invite proof does not verify"))?;
        }
        // An approval invite waits for a person; any other is admitted at once and waits only for
        // an admin to wrap the read key to it (its `accept`).
        let i = self.invites.get_mut(&j.invite).expect("checked");
        i.used = true;
        i.used_by = Some(cert.device.clone());
        self.devices
            .insert(cert.device.clone(), DeviceState::new(cert.clone(), root.clone()));
        self.members.insert(
            root.clone(),
            MemberState {
                root: root.clone(),
                label: j.label.clone(),
                role: inv.role,
                pending: inv.approval,
                removed: false,
                devices: [cert.device.clone()].into(),
                joined: id.to_owned(),
            },
        );
        if inv.approval || inv.role.reads() {
            self.pending_joins.insert(id.to_owned(), root);
        }
        Ok(())
    }
}

/// A renewed certificate replacing `stored`, at entry time `ts`: it starts at or before the
/// stored one ends, comes inside the renewal window, and comes within one lifetime after the
/// stored one ends.
fn check_renewal(stored: &DeviceCert, renewed: &DeviceCert, ts: u64) -> Result<()> {
    if renewed.not_before > stored.not_after {
        return Err(refused("a renewal must start before the certificate it renews ends"));
    }
    if ts < stored.not_after.saturating_sub(CERT_RENEW_WITHIN_S) {
        return Err(refused(
            "a renewal is only taken within the renewal window before the certificate expires",
        ));
    }
    if ts > stored.not_after.saturating_add(CERT_MAX_LIFETIME_S) {
        return Err(refused(
            "a renewal comes at most one lifetime after the certificate it renews",
        ));
    }
    Ok(())
}

// -------------------------------------------------------------------------------------- the chain

/// Two different entries at one position, each of which applies on its own on the state before
/// it: the chain takes no entry past the one before (`seq - 1`) until a root takeover.
#[derive(Clone, Debug, Serialize)]
pub struct Equivocation {
    pub term: u64,
    pub seq: u64,
    pub ours: Entry,
    pub theirs: Entry,
}

impl Equivocation {
    /// The key of its pair (`Evidence::key`).
    pub fn key(&self) -> EvidenceKey {
        evidence_key(&self.theirs)
    }
}

/// What a stored evidence pair did (review finding R7-1): only the pair of the current halt is
/// checked again when the chain is restored.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvidenceKind {
    /// The pair the chain is halted on now.
    Halt,
    /// Below a later term start here: an alarm only (`AclChain::settled_above`).
    Alarm,
    /// A halt a lower one, or a root takeover, has since replaced.
    Past,
}

impl EvidenceKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Halt => "halt",
            Self::Alarm => "alarm",
            Self::Past => "past",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "halt" => Self::Halt,
            "alarm" => Self::Alarm,
            "past" => Self::Past,
            _ => return None,
        })
    }
}

/// An equivocation pair, for the store and the alarm: two entries at one position, and what they
/// did here (it is an alarm only when this replica's chain started a later term above it; see
/// `AclChain::settled_above`).
#[derive(Clone, Debug)]
pub struct Evidence {
    pub ours: Entry,
    pub theirs: Entry,
    pub kind: EvidenceKind,
}

impl Evidence {
    /// Whether this pair halted the chain when it was found.
    pub fn halts(&self) -> bool {
        self.kind == EvidenceKind::Halt
    }

    /// The position the pair is about, and who signed it: `(signer, term, seq)`. A replica keeps
    /// at most one pair per key, the first (review finding R7-1).
    pub fn key(&self) -> EvidenceKey {
        evidence_key(&self.theirs)
    }
}

/// `(signer, term, seq)`: the signer is the term's sequencer device, or `takeover` for two root
/// takeovers of one term (the owner's root signs both).
pub type EvidenceKey = (String, u64, u64);

fn evidence_key(e: &Entry) -> EvidenceKey {
    let signer = if e.takeover().is_some() {
        "takeover".to_owned()
    } else {
        e.sequencer.device.clone()
    };
    (signer, e.term, e.seq)
}

/// Stored evidence pairs a replica keeps, at most (review finding R7-1). A replica holds at most
/// one pair per position and signer, an alarm-only pair for one signer at most once, and a halt
/// only below the one it has; at the cap a new alarm-only pair is not kept, and a new halt's pair
/// replaces the oldest pair that is not the current halt.
pub const MAX_EVIDENCE_PAIRS: u32 = 256;

/// What a pair of entries at one position proves.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Found {
    /// Not an equivocation (one of them does not apply on its own, or they are not a pair).
    Nothing,
    /// Nothing new: a pair for this position and signer is already held, a halt at or below it
    /// already stands, or it would be one more alarm about a signer already raised. Decided
    /// before any signature is checked or any state folded (review finding R7-1).
    Seen,
    /// An equivocation below a later term start on this replica's chain: an alarm, no halt.
    Alarm,
    /// An equivocation that halts the chain.
    Halt,
}

/// What one `insert` did.
#[derive(Debug, Default)]
pub struct Inserted {
    /// Entries now on the chain that were not.
    pub added: usize,
    /// Ask the peer for entries after this seq (a gap, or a branch that does not link here).
    pub need_from: Option<u64>,
    /// Entries a takeover dropped from this replica's chain (their positions).
    pub dropped: Vec<AclPos>,
    /// An equivocation was found by this insert.
    pub equivocation: bool,
    /// Why the first refused entry was refused.
    pub refused: Option<String>,
    /// The refused entry was the chain's next entry, signed by its sequencer: this replica
    /// cannot follow the chain the sequencer is extending (a divergence, never silent: the
    /// engine raises an alarm).
    pub diverged: Option<String>,
    /// Evidence checks (a signature, a fold and a dry application) this call ran, and any
    /// `note_evidence` before it: what the caller charges to the session that sent them (review
    /// finding R7-1). An insert runs at most one and stops there.
    pub checks: u32,
}

/// The ACL of one link: the chain this replica holds, and the state it folds to.
#[derive(Clone, Default)]
pub struct AclChain {
    entries: Vec<Entry>,
    hashes: Vec<String>,
    /// The epoch in force after each entry.
    epochs: Vec<u64>,
    /// The state after the last held entry. An equivocation never folds it back (review finding
    /// R6-1): a halt narrows what this replica grants, it never widens it.
    state: AclState,
    /// While halted: the state every reader sees (`state()`), the held tip's state narrowed to
    /// what the prefix grants too (`AclState::narrowed`).
    view: Option<AclState>,
    /// The state after entry k, for every k that is a multiple of `CHECKPOINT_EVERY`.
    checkpoints: BTreeMap<u64, AclState>,
    included: HashMap<String, u64>,
    halt: Option<Equivocation>,
    certs: HashSet<String>,
    /// The lowest seq whose stored row changed since `take_dirty`.
    dirty_from: Option<u64>,
    /// Evidence found since `take_evidence`.
    evidence: Vec<Evidence>,
    /// Every position and signer this replica holds a pair for (stored, or found at the store's
    /// cap): a second pair there is not checked (review finding R7-1).
    seen: HashSet<EvidenceKey>,
    /// Signers with an alarm-only pair: one more alarm about them is not checked.
    alarmed: HashSet<String>,
    /// Evidence checks since the last `insert` (`Inserted::checks`).
    checks: u32,
    /// Positions dropped by takeovers since `take_dropped`.
    dropped: Vec<AclPos>,
    /// `settled_above`'s bound per (signer, its root, term), at the held tip it was computed for
    /// (review finding R8-4).
    settled: (String, HashMap<(String, String, u64), usize>),
    /// Scans of the chain by `settled_bound` (tests only).
    #[cfg(test)]
    pub(crate) settled_scans: u32,
    /// The devices that may sync, by `state()` and by `held_state()`, kept until the held tip or
    /// the halt changes (review finding R9-2): every frame of a session asks.
    sync: SyncCache,
}

/// What `SyncCache` keeps its sets for: the held tip's hash, the entries held, the halt's seq
/// and whether a narrowed view is in force.
type SyncKey = (String, usize, Option<u64>, bool);

/// `AclChain::sync_devices` and `AclChain::held_sync_devices`, kept per `SyncKey` (review
/// finding R9-2). Behind a lock so a reader with `&AclChain` can fill it.
#[derive(Default)]
struct SyncCache {
    kept: std::sync::Mutex<Option<(SyncKey, SyncSets)>>,
}

#[cfg(test)]
thread_local! {
    /// Times `AclState::sync_devices` built a set on this thread (tests only).
    static SYNC_BUILDS: std::cell::Cell<u32> = const { std::cell::Cell::new(0) };
}

/// The devices that may sync by `state()`, and by `held_state()`.
type SyncSets = (Arc<BTreeSet<String>>, Arc<BTreeSet<String>>);

impl Clone for SyncCache {
    fn clone(&self) -> Self {
        Self {
            kept: std::sync::Mutex::new(self.kept.lock().unwrap_or_else(|e| e.into_inner()).clone()),
        }
    }
}

enum Step {
    Added,
    Known,
    NeedFrom(u64),
    Stale,
    Replaced(Vec<AclPos>),
    Equivocation,
    /// Evidence that halts nothing, new (an alarm) or not: the rest of the batch is not looked at.
    Evidence,
}

impl AclChain {
    pub fn new() -> Self {
        Self::default()
    }

    /// The state this replica acts on: the held tip's, or, while halted, the held tip's narrowed
    /// to what the prefix grants too (a device active in both, at the lower of its two roles;
    /// positions are the prefix's). Sync, record admission and status all read this.
    pub fn state(&self) -> &AclState {
        self.view.as_ref().unwrap_or(&self.state)
    }

    /// The state after the last held entry, halted or not (self-monitoring reads it: a device
    /// added past the prefix is still listed under its root).
    pub fn held_state(&self) -> &AclState {
        &self.state
    }

    /// The devices that may sync with us by `state()` (narrowed while halted): a lookup, built
    /// once per held tip and halt (review finding R9-2).
    pub fn sync_devices(&self) -> Arc<BTreeSet<String>> {
        self.sync_sets().0
    }

    /// The devices that may sync with us by `held_state()`, kept as `sync_devices` is.
    pub fn held_sync_devices(&self) -> Arc<BTreeSet<String>> {
        self.sync_sets().1
    }

    fn sync_sets(&self) -> SyncSets {
        let halt = self.halt.as_ref().map(|h| h.seq);
        let same = |k: &SyncKey| {
            k.0 == self.state.tip && k.1 == self.entries.len() && k.2 == halt && k.3 == self.view.is_some()
        };
        let mut kept = self.sync.kept.lock().unwrap_or_else(|e| e.into_inner());
        if let Some((k, sets)) = kept.as_ref()
            && same(k)
        {
            return sets.clone();
        }
        let held = Arc::new(self.state.sync_devices());
        let view = self
            .view
            .as_ref()
            .map_or_else(|| held.clone(), |v| Arc::new(v.sync_devices()));
        let key = (self.state.tip.clone(), self.entries.len(), halt, self.view.is_some());
        *kept = Some((key, (view.clone(), held.clone())));
        (view, held)
    }

    /// Times `AclState::sync_devices` built a set on this thread (tests only).
    #[cfg(test)]
    pub(crate) fn sync_builds() -> u32 {
        SYNC_BUILDS.with(|n| n.get())
    }

    /// The position of the last held entry (past the prefix while halted).
    pub fn held_tip(&self) -> AclPos {
        self.state.pos()
    }

    pub fn link_id(&self) -> &str {
        &self.state.link_id
    }

    /// Entries held (past the prefix too, while halted).
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Entries in the prefix: everything, unless an equivocation halted the chain.
    pub fn prefix_len(&self) -> usize {
        self.halt.as_ref().map_or(self.entries.len(), |h| h.seq as usize)
    }

    /// The last position of the prefix.
    pub fn tip(&self) -> AclPos {
        self.state().pos()
    }

    pub fn halt(&self) -> Option<&Equivocation> {
        self.halt.as_ref()
    }

    pub fn entry(&self, seq: u64) -> Option<&Entry> {
        self.entries.get(seq as usize)
    }

    pub fn hash_at(&self, seq: u64) -> Option<&str> {
        self.hashes.get(seq as usize).map(String::as_str)
    }

    /// Whether `pos` is on the prefix of this chain.
    pub fn on_chain(&self, pos: &AclPos) -> bool {
        (pos.seq as usize) < self.prefix_len()
            && self.hashes[pos.seq as usize] == pos.hash
            && self.entries[pos.seq as usize].term == pos.term
    }

    /// The seq of the entry that included proposal `id`, if one did.
    pub fn included(&self, id: &str) -> Option<u64> {
        self.included
            .get(id)
            .copied()
            .filter(|s| (*s as usize) < self.prefix_len())
    }

    /// The epoch in force after entry `seq` of the prefix.
    pub fn epoch_at(&self, seq: u64) -> Option<u64> {
        ((seq as usize) < self.prefix_len()).then(|| self.epochs[seq as usize])
    }

    /// Entries of the prefix with `from < seq <= to`, at most `budget` bytes of them (always at
    /// least one, if any is in range): what a peer that asked for that range is sent.
    pub fn range(&self, from: u64, to: u64, budget: usize) -> Vec<Entry> {
        let end = (to.saturating_add(1) as usize).min(self.prefix_len());
        let start = (from.saturating_add(1) as usize).min(end);
        let mut out = Vec::new();
        let mut used = 0;
        for e in &self.entries[start..end] {
            let n = codec::canonical(e).map_or(MAX_ENTRY_BYTES, |b| b.len());
            if used + n > budget && !out.is_empty() {
                break;
            }
            used += n;
            out.push(e.clone());
        }
        out
    }

    /// Every entry of the prefix, genesis first.
    pub fn all(&self) -> Vec<Entry> {
        self.entries[..self.prefix_len()].to_vec()
    }

    /// The state after entry `seq` of the prefix.
    pub fn state_at(&self, seq: u64) -> Result<AclState> {
        if seq as usize >= self.prefix_len() {
            return Err(refused("that position is not on this chain yet"));
        }
        if seq == self.state.seq {
            return Ok(self.state.clone());
        }
        self.fold_to(seq)
    }

    /// The state after entry `seq` of the held entries, from the nearest checkpoint.
    fn fold_to(&self, seq: u64) -> Result<AclState> {
        let (start, mut s) = match self.checkpoints.range(..=seq).next_back() {
            Some((k, st)) => (*k + 1, st.clone()),
            None => (0, AclState::default()),
        };
        let mut certs = HashSet::new();
        for i in start..=seq {
            // A replay of entries already accepted: their signatures and inclusions were checked.
            let mut past = Past {
                entries: &self.entries[..i as usize],
                included: &EMPTY_INCLUDED,
                certs: &mut certs,
                verified: true,
            };
            s = s
                .apply_entry(&self.entries[i as usize], &self.hashes[i as usize], &mut past, false)?
                .0;
        }
        Ok(s)
    }

    /// Take the dirty marker: the stored rows from this seq on must be rewritten.
    pub fn take_dirty(&mut self) -> Option<u64> {
        self.dirty_from.take()
    }

    pub fn take_evidence(&mut self) -> Vec<Evidence> {
        std::mem::take(&mut self.evidence)
    }

    pub fn take_dropped(&mut self) -> Vec<AclPos> {
        std::mem::take(&mut self.dropped)
    }

    fn mark_dirty(&mut self, seq: u64) {
        self.dirty_from = Some(self.dirty_from.map_or(seq, |d| d.min(seq)));
    }

    /// Apply `e` at the end of the held chain (its state must be `self.state`), and keep it.
    fn push(&mut self, e: Entry, hash: String, verified: bool) -> Result<()> {
        let mut past = Past {
            entries: &self.entries,
            included: &self.included,
            certs: &mut self.certs,
            verified,
        };
        let (state, ids, _) = self.state.apply_entry(&e, &hash, &mut past, false)?;
        let seq = e.seq;
        for id in ids {
            self.included.insert(id, seq);
        }
        self.epochs.push(state.epoch);
        if seq.is_multiple_of(CHECKPOINT_EVERY) {
            self.checkpoints.insert(seq, state.clone());
        }
        self.state = state;
        self.entries.push(e);
        self.hashes.push(hash);
        self.mark_dirty(seq);
        Ok(())
    }

    /// Drop every held entry from `seq` on, and fold the state back to the entry before.
    fn truncate(&mut self, seq: u64) -> Result<Vec<AclPos>> {
        let mut gone = Vec::new();
        for i in (seq as usize)..self.entries.len() {
            gone.push(AclPos {
                term: self.entries[i].term,
                seq: i as u64,
                hash: self.hashes[i].clone(),
            });
        }
        self.entries.truncate(seq as usize);
        self.hashes.truncate(seq as usize);
        self.epochs.truncate(seq as usize);
        self.checkpoints.retain(|k, _| *k < seq);
        self.included.retain(|_, s| *s < seq);
        self.state = if seq == 0 {
            AclState::default()
        } else {
            self.fold_to(seq - 1)?
        };
        self.mark_dirty(seq);
        Ok(gone)
    }

    /// Reload this replica's own stored chain and evidence. Every entry is checked again. Of the
    /// evidence, only the pair of the halt is checked again (review finding R7-1), as an evidence
    /// frame is, so a halt at the next position survives a restart too (R7-4); the other pairs
    /// only mark their position as seen.
    pub fn restore(&mut self, entries: Vec<Entry>, evidence: Vec<Evidence>) -> Result<()> {
        for e in entries {
            let hash = e.hash()?;
            if self.push(e, hash, false).is_err() {
                break;
            }
        }
        let (halts, others): (Vec<Evidence>, Vec<Evidence>) =
            evidence.into_iter().partition(|ev| ev.kind == EvidenceKind::Halt);
        for ev in others {
            if ev.kind == EvidenceKind::Alarm {
                self.alarmed.insert(ev.ours.sequencer.device.clone());
            }
            self.seen.insert(ev.key());
        }
        for ev in halts {
            let _ = self.note_evidence(&ev.ours, &ev.theirs);
        }
        self.dirty_from = None;
        self.evidence.clear();
        self.checks = 0;
        Ok(())
    }

    /// Whether `e` would apply on its own on `before`, the state after entry `s - 1` of the held
    /// chain: a dry run, cuts skipped, every other rule checked (the sequencer's signature and
    /// authority, a takeover's root signature, named device and `after`, certificate validity at
    /// `ts`, and size). Evidence is only ever two entries that pass this (review finding R6-5).
    fn applies_alone(&mut self, before: &AclState, e: &Entry, s: usize) -> bool {
        if !codec::canonical(e).is_ok_and(|b| b.len() <= MAX_ENTRY_BYTES) {
            return false;
        }
        let Ok(hash) = e.hash() else {
            return false;
        };
        let included: HashMap<String, u64> = self
            .included
            .iter()
            .filter(|(_, at)| (**at as usize) < s)
            .map(|(id, at)| (id.clone(), *at))
            .collect();
        let mut past = Past {
            entries: &self.entries[..s],
            included: &included,
            certs: &mut self.certs,
            verified: false,
        };
        before.apply_entry(e, &hash, &mut past, true).is_ok()
    }

    /// Whether this replica's chain, above position `s`, started a term later than `term` in a
    /// way the device that signed the evidence (`signer`, of member `signer_root`) could not have
    /// done alone: a root takeover, or a term sequenced by a device of another member. Honest
    /// replicas that hold that term start have committed to it (fork choice keeps the branch whose
    /// first differing entry has the higher term, and both entries at `s` share one), so a halt
    /// would protect nobody and would hand the old term's key a veto it no longer holds (review
    /// finding R6-1). A term the signer's member started for itself (a handoff to its own fleet's
    /// device) does not count, so a malicious branch cannot buy itself immunity with self-handoffs.
    ///
    /// A self-started later term does count once the signer's device is retired for good (review
    /// finding R7-5): it cannot sequence at the held tip, and an action above `s` that it could not
    /// have authored itself removed or demoted it: one by the owner's fleet, or by another member
    /// than the signer's. An honest owner that hands off to its own other device and then removes
    /// the old one leaves that key no halt switch; a member that hands off to itself and removes
    /// its own old device on its own branch still buys nothing.
    ///
    /// The answer is `s < bound` for one bound per signer and term (every clause asks for an entry
    /// above `s`), computed by one scan of the chain and kept until the chain changes (review
    /// finding R8-4): a flood of frames about an alarmed signer, screened before any charge,
    /// costs a lookup each, not a scan.
    fn settled_above(&mut self, s: usize, term: u64, signer: &str, signer_root: &str) -> bool {
        if self.settled.0 != self.state.tip {
            self.settled = (self.state.tip.clone(), HashMap::new());
        }
        let key = (signer.to_owned(), signer_root.to_owned(), term);
        let bound = match self.settled.1.get(&key) {
            Some(b) => *b,
            None => {
                let b = self.settled_bound(term, signer, signer_root);
                // Keys are signers of evidence that passed the cheap filters: few. Bounded anyway.
                if self.settled.1.len() >= MAX_EVIDENCE_PAIRS as usize {
                    self.settled.1.clear();
                }
                self.settled.1.insert(key, b);
                b
            }
        };
        #[cfg(test)]
        assert_eq!(s < bound, self.settled_above_by_scan(s, term, signer, signer_root));
        s < bound
    }

    /// The round-7 `settled_above`, a scan per call: tests check the bound against it.
    #[cfg(test)]
    fn settled_above_by_scan(&self, s: usize, term: u64, signer: &str, signer_root: &str) -> bool {
        let above = &self.entries[s + 1..];
        let later = |x: &&Entry| x.term > term;
        if above
            .iter()
            .filter(later)
            .any(|x| x.takeover().is_some() || x.sequencer.root != signer_root)
        {
            return true;
        }
        if !above.iter().any(|x| later(&x)) || self.state.may_sequence(signer) {
            return false;
        }
        let owner = self.state.owner.as_str();
        let retires = |op: &Op| match op {
            Op::RemoveDevice(r) => r.device == signer,
            Op::RemoveMember(r) => r.member == signer_root,
            Op::SetRole(r) => r.member == signer_root && !r.role.admin(),
            _ => false,
        };
        let by_other = |root: &str| root != signer_root || root == owner;
        above.iter().any(|x| {
            (by_other(&x.sequencer.root) && x.body.as_ref().is_some_and(retires))
                || x.proposals
                    .iter()
                    .any(|p| by_other(&p.proposer.root) && p.parsed().is_ok_and(|op| retires(&op)))
        })
    }

    /// The bound of `settled_above`: one scan of the chain. Each clause holds for `s` exactly when
    /// an entry with the clause's property sits above `s`, that is when `s` is below the highest
    /// index with it (0 when none does).
    fn settled_bound(&mut self, term: u64, signer: &str, signer_root: &str) -> usize {
        #[cfg(test)]
        {
            self.settled_scans += 1;
        }
        let last = |f: &dyn Fn(&Entry) -> bool| self.entries.iter().rposition(f).unwrap_or(0);
        let later = |x: &Entry| x.term > term;
        let other_term = last(&|x| later(x) && (x.takeover().is_some() || x.sequencer.root != signer_root));
        if self.state.may_sequence(signer) {
            return other_term;
        }
        let owner = self.state.owner.as_str();
        let retires = |op: &Op| match op {
            Op::RemoveDevice(r) => r.device == signer,
            Op::RemoveMember(r) => r.member == signer_root,
            Op::SetRole(r) => r.member == signer_root && !r.role.admin(),
            _ => false,
        };
        let by_other = |root: &str| root != signer_root || root == owner;
        let retired = last(&|x| {
            (by_other(&x.sequencer.root) && x.body.as_ref().is_some_and(retires))
                || x.proposals
                    .iter()
                    .any(|p| by_other(&p.proposer.root) && p.parsed().is_ok_and(|op| retires(&op)))
        });
        other_term.max(last(&later).min(retired))
    }

    /// What is already known about a pair at `e`'s position, signed by the signer of `ours`, before
    /// anything is verified or folded (review finding R7-1): a pair is held for that position
    /// and signer (the first one wins), a halt at or below it already stands, or it would be one
    /// more alarm about a signer already raised. Any of these makes a new pair `Found::Seen`.
    fn screen(&mut self, e: &Entry) -> bool {
        let s = e.seq as usize;
        if self.seen.contains(&evidence_key(e)) || self.halt.as_ref().is_some_and(|h| h.seq as usize <= s) {
            return true;
        }
        let Some(ours) = self.entries.get(s) else {
            return false;
        };
        if ours.takeover().is_some() || !self.alarmed.contains(&ours.sequencer.device) {
            return false;
        }
        let (signer, root) = (ours.sequencer.device.clone(), ours.sequencer.root.clone());
        self.settled_above(s, e.term, &signer, &root)
    }

    /// Keep a new pair: as seen, in `evidence` for the store, and as the halt if it halts.
    fn record(&mut self, ours: Entry, theirs: Entry, kind: EvidenceKind, prefix: Option<AclState>) {
        self.seen.insert(evidence_key(&theirs));
        if kind == EvidenceKind::Alarm {
            self.alarmed.insert(ours.sequencer.device.clone());
        }
        if let Some(prefix) = prefix {
            self.set_halt(
                Equivocation {
                    term: theirs.term,
                    seq: theirs.seq,
                    ours: ours.clone(),
                    theirs: theirs.clone(),
                },
                prefix,
            );
        }
        self.evidence.push(Evidence { ours, theirs, kind });
    }

    /// Whether `e` and the held entry at its seq are an equivocation, and what it does: halts the
    /// chain at the entry before (the held state is kept; `view` narrows it), or, below a later
    /// term start (`settled_above`), raises an alarm only. A pair already known is `Seen`, decided
    /// before any signature is checked.
    fn check_equivocation(&mut self, e: &Entry) -> Result<Found> {
        let s = e.seq as usize;
        let Some(ours) = self.entries.get(s) else {
            return Ok(Found::Nothing);
        };
        let hash = e.hash()?;
        if s == 0 || self.hashes[s] == hash || e.prev != self.hashes[s - 1] || e.term != ours.term {
            return Ok(Found::Nothing);
        }
        // A takeover against an entry of its term: fork choice, not evidence.
        if e.takeover().is_some() != ours.takeover().is_some() {
            return Ok(Found::Nothing);
        }
        // Cheap filters first: an entry of a term is signed by that term's sequencer, and two
        // takeovers of one term name their devices (each is checked in full below).
        if e.takeover().is_none() && e.sequencer.device != ours.sequencer.device {
            return Ok(Found::Nothing);
        }
        if self.screen(e) {
            return Ok(Found::Seen);
        }
        let ours = self.entries[s].clone();
        self.checks += 1;
        if e.verify_with(&mut self.certs).is_err() {
            return Ok(Found::Nothing);
        }
        if let Some(t) = e.takeover() {
            let root_signed = crypto::verify(
                &unhex::<32>(&self.state.owner)?,
                "acl-takeover",
                &takeover_bytes(&self.state.link_id, t.term, &t.after, &t.sequencer)?,
                &unb64(&t.sig).unwrap_or_default(),
            );
            if root_signed.is_err() {
                return Ok(Found::Nothing);
            }
        }
        // Each must apply on its own on the common prefix. Ours did when it was pushed.
        let before = self.fold_to(s as u64 - 1)?;
        if !self.applies_alone(&before, e, s) {
            return Ok(Found::Nothing);
        }
        if self.settled_above(s, e.term, &ours.sequencer.device, &ours.sequencer.root) {
            self.record(ours, e.clone(), EvidenceKind::Alarm, None);
            return Ok(Found::Alarm);
        }
        self.record(ours, e.clone(), EvidenceKind::Halt, Some(before));
        Ok(Found::Halt)
    }

    /// Halt at `h` with `prefix` the state after entry `h.seq - 1`. The held state stays; what
    /// this replica grants is narrowed to the prefix's grants too.
    fn set_halt(&mut self, h: Equivocation, prefix: AclState) {
        self.view = Some(self.state.narrowed(&prefix));
        self.halt = Some(h);
    }

    /// End a halt (a root takeover continued the chain).
    fn clear_halt(&mut self) {
        self.halt = None;
        self.view = None;
    }

    /// An evidence pair from a peer: two entries at one position on one prefix, each of which
    /// applies on its own there. Halts the chain if it proves an equivocation at a position this
    /// replica holds (unless a later term started above it here: then an alarm only), or at the
    /// next one. Returns whether the chain is halted by it. A pair for a position and signer this
    /// replica already holds one for is not checked again (review finding R7-1).
    pub fn note_evidence(&mut self, a: &Entry, b: &Entry) -> Result<bool> {
        let found = [self.check_equivocation(a)?, self.check_equivocation(b)?];
        if found.contains(&Found::Halt) {
            return Ok(true);
        }
        if found.contains(&Found::Alarm) || found.contains(&Found::Seen) {
            return Ok(false);
        }
        let s = a.seq as usize;
        if s == 0 || s != self.entries.len() || b.seq != a.seq || b.term != a.term || b.prev != a.prev {
            return Ok(false);
        }
        if a.prev != self.hashes[s - 1] || a.hash()? == b.hash()? || self.halt.is_some() {
            return Ok(false);
        }
        if a.takeover().is_some() != b.takeover().is_some()
            || (a.takeover().is_none() && a.sequencer.device != b.sequencer.device)
        {
            return Ok(false);
        }
        if self.seen.contains(&evidence_key(a)) || self.seen.contains(&evidence_key(b)) {
            return Ok(false);
        }
        self.checks += 1;
        let before = self.state.clone();
        if !self.applies_alone(&before, a, s) || !self.applies_alone(&before, b, s) {
            return Ok(false);
        }
        self.record(a.clone(), b.clone(), EvidenceKind::Halt, Some(before));
        Ok(true)
    }

    /// Merge entries from a peer (a contiguous run, or any subset; any order). `now` is the
    /// verifier's clock: an entry dated more than `MAX_FUTURE_SKEW_S` ahead of it is refused.
    pub fn insert(&mut self, mut batch: Vec<Entry>, now: Option<u64>) -> Inserted {
        batch.sort_by_key(|e| e.seq);
        batch.dedup_by(|a, b| a == b);
        let mut out = Inserted::default();
        // Entries of a losing branch in this batch: whatever builds on one loses too.
        let mut stale: HashSet<String> = HashSet::new();
        for e in batch {
            // At most one evidence check per batch (review finding R7-1): whatever follows an
            // entry that needed one is on the branch that lost, or more of the same.
            let checks = self.checks;
            if stale.contains(&e.prev) {
                if let Ok(h) = e.hash() {
                    stale.insert(h);
                }
                continue;
            }
            let hash = e.hash().unwrap_or_default();
            // Kept only for the next entry from the sequencer, to tell a divergence on refusal.
            let next = (e.seq as usize == self.entries.len()
                && self.halt.is_none()
                && e.prev == self.state.tip
                && e.sequencer.device == self.state.next_sequencer().0)
                .then(|| e.clone());
            match self.insert_one(e, now) {
                Ok(Step::Added) => out.added += 1,
                Ok(Step::Known) => {}
                Ok(Step::NeedFrom(s)) => {
                    out.need_from = Some(out.need_from.map_or(s, |n: u64| n.min(s)));
                    break;
                }
                Ok(Step::Stale) => {
                    stale.insert(hash);
                }
                Ok(Step::Replaced(gone)) => {
                    out.added += 1;
                    self.dropped.extend(gone.iter().cloned());
                    out.dropped.extend(gone);
                }
                Ok(Step::Equivocation) => {
                    out.equivocation = true;
                    break;
                }
                Ok(Step::Evidence) => break,
                Err(err) => {
                    if let Some(e) = next
                        && out.refused.is_none()
                        && e.verify_with(&mut self.certs).is_ok()
                    {
                        out.diverged = Some(format!("seq {}: {err}", e.seq));
                    }
                    out.refused.get_or_insert(err.to_string());
                    break;
                }
            }
            if self.checks != checks {
                break;
            }
        }
        out.checks = std::mem::take(&mut self.checks);
        out
    }

    fn insert_one(&mut self, e: Entry, now: Option<u64>) -> Result<Step> {
        let bytes = codec::canonical(&e)?;
        if bytes.len() > MAX_ENTRY_BYTES {
            return Err(refused("ACL entry is too large"));
        }
        let hash = hex(&crypto::sha256(&[&bytes]));
        if let Some(n) = now
            && e.ts > n + MAX_FUTURE_SKEW_S
        {
            return Err(refused("ACL entry is dated in the future"));
        }
        let s = e.seq as usize;
        if s < self.entries.len() {
            if self.hashes[s] == hash {
                return Ok(Step::Known);
            }
            if s == 0 {
                return Err(refused("a second genesis for this link"));
            }
            if e.prev != self.hashes[s - 1] {
                // The branch it is on forks below: ask from further back.
                return Ok(Step::NeedFrom((s as u64).saturating_sub(BACKOFF_STEP + 1)));
            }
            match self.check_equivocation(&e)? {
                Found::Halt => return Ok(Step::Equivocation),
                // Evidence below a later term start here (noted), or a pair already known: the
                // entry loses (its term is ours, so ours stays).
                Found::Alarm | Found::Seen => return Ok(Step::Evidence),
                Found::Nothing => {}
            }
            let ours = &self.entries[s];
            let wins =
                e.term > ours.term || (e.term == ours.term && e.takeover().is_some() && ours.takeover().is_none());
            if !wins {
                return Ok(Step::Stale);
            }
            if let Some(h) = &self.halt
                && (e.takeover().is_none() || e.term <= h.term)
            {
                return Err(refused(format!(
                    "this link's sequencer equivocated at term {} seq {}: waiting for a root takeover",
                    h.term, h.seq
                )));
            }
            // A later term (a root takeover, or the next term after a handoff) beats ours from
            // here; it must apply on the state after the entry before, like any entry. Its
            // signatures are checked before anything is folded again.
            self.check_term_start(&e)?;
            let mut probe = self.clone();
            let gone = probe.truncate(e.seq)?;
            probe.clear_halt();
            probe.push(e, hash, false)?;
            let evidence = std::mem::take(&mut self.evidence);
            let dropped = std::mem::take(&mut self.dropped);
            *self = probe;
            self.evidence = evidence;
            self.dropped = dropped;
            return Ok(Step::Replaced(gone));
        }
        if s > self.entries.len() {
            return Ok(Step::NeedFrom(self.entries.len().saturating_sub(1) as u64));
        }
        // The next entry of the held chain.
        if s > 0 && e.prev != self.hashes[s - 1] {
            return Ok(Step::NeedFrom((s as u64).saturating_sub(BACKOFF_STEP + 1)));
        }
        if let Some(h) = &self.halt {
            // Halted: only a root takeover of a later term continues, from any held position.
            if e.takeover().is_none_or(|_| e.term <= h.term) {
                return Err(refused(format!(
                    "this link's sequencer equivocated at term {} seq {}: waiting for a root takeover",
                    h.term, h.seq
                )));
            }
            self.check_term_start(&e)?;
            // The held state is the state after the entry before: never folded back.
            let mut probe = self.clone();
            probe.clear_halt();
            probe.push(e, hash, false)?;
            let evidence = std::mem::take(&mut self.evidence);
            let dropped = std::mem::take(&mut self.dropped);
            *self = probe;
            self.evidence = evidence;
            self.dropped = dropped;
            return Ok(Step::Added);
        }
        self.push(e, hash, false)?;
        Ok(Step::Added)
    }

    /// Before an entry that starts a later term may replace held entries (or end a halt): its
    /// signature, and its authority to start a term: the owner root's takeover signature, or a
    /// handoff to its signer in the entry before. Cheap checks, so a bogus one costs no refold.
    fn check_term_start(&mut self, e: &Entry) -> Result<()> {
        e.verify_with(&mut self.certs)?;
        if let Some(t) = e.takeover() {
            if t.sequencer != e.sequencer.device || t.term != e.term {
                return Err(refused("a takeover is appended by the device it names, in its term"));
            }
            return crypto::verify(
                &unhex::<32>(&self.state.owner)?,
                "acl-takeover",
                &takeover_bytes(&self.state.link_id, t.term, &t.after, &t.sequencer)?,
                &unb64(&t.sig)?,
            )
            .map_err(|_| refused("a takeover must be signed by the owner's fleet root"));
        }
        let to = Some(Op::Handoff(Handoff {
            to: e.sequencer.device.clone(),
        }));
        let before = e.seq.checked_sub(1).and_then(|s| self.entries.get(s as usize));
        let handed = before.is_some_and(|b| {
            b.body == to
                || b.proposals.iter().any(|p| {
                    p.kind == "handoff" && p.args.get("to").and_then(Value::as_str) == Some(e.sequencer.device.as_str())
                })
        });
        if !handed {
            return Err(refused(
                "a later term starts with a root takeover or right after a handoff to its signer",
            ));
        }
        Ok(())
    }

    /// Check a proposal against the current state, as the sequencer would at `ts`.
    pub fn check_proposal(&self, p: &Proposal, ts: u64) -> Result<()> {
        let id = p.id()?;
        let mut s = self.state.clone();
        let mut certs = self.certs.clone();
        let mut past = Past {
            entries: &self.entries[..self.prefix_len()],
            included: &self.included,
            certs: &mut certs,
            verified: false,
        };
        let mut cuts = Cuts {
            given: None,
            taken: BTreeSet::new(),
        };
        s.apply_proposal(p, &id, ts.max(self.state.frontier_ts), &mut past, &mut cuts)?;
        s.check_sequencer()
    }

    /// Append an entry signed by `device`, the next sequencer: its own action `body` and
    /// `proposals`. `cut_of` gives the feed head this replica holds for a device it removes.
    pub fn append(
        &mut self,
        device: &Device,
        body: Option<Op>,
        proposals: Vec<Proposal>,
        ts: u64,
        cut_of: &dyn Fn(&str) -> u64,
    ) -> Result<Entry> {
        if self.state.link_id.is_empty() {
            return Err(refused("this chain has no genesis"));
        }
        let me = device.id_hex();
        let (next, mut term) = self.state.next_sequencer();
        if let Some(Op::Takeover(t)) = &body {
            term = t.term;
        } else {
            if let Some(h) = &self.halt {
                return Err(refused(format!(
                    "this link's sequencer equivocated at term {} seq {}: only a root takeover continues it",
                    h.term, h.seq
                )));
            }
            if next != me {
                return Err(refused("this device does not sequence this link"));
            }
        }
        let ts = ts.max(self.state.frontier_ts);
        let (link, seq, prev) = (self.state.link_id.clone(), self.state.seq + 1, self.state.tip.clone());
        // A dry run finds the devices this entry removes; their cuts are the heads we hold.
        let dry = Entry::sign(
            device,
            &link,
            term,
            seq,
            &prev,
            ts,
            body.clone(),
            proposals.clone(),
            BTreeMap::new(),
        )?;
        let removed = {
            let mut certs = self.certs.clone();
            let mut past = Past {
                entries: &self.entries,
                included: &self.included,
                certs: &mut certs,
                verified: false,
            };
            self.state.apply_entry(&dry, &dry.hash()?, &mut past, true)?.2
        };
        let cuts: BTreeMap<String, u64> = removed.iter().map(|d| (d.clone(), cut_of(d))).collect();
        let e = Entry::sign(device, &link, term, seq, &prev, ts, body, proposals, cuts)?;
        // Every replica refuses a larger entry: never sign one (review finding R6-3).
        if codec::canonical(&e)?.len() > MAX_ENTRY_BYTES {
            return Err(refused(format!(
                "this entry would be larger than {MAX_ENTRY_BYTES} bytes, which no replica takes"
            )));
        }
        let hash = e.hash()?;
        // Not `verified`: the proposals it includes come from other devices.
        self.push(e.clone(), hash, false)?;
        Ok(e)
    }

    /// A proposal for `op` by `device`, on this chain's tip, includable for `PROPOSAL_TTL_S`
    /// after `now` (the proposer's clock).
    pub fn propose_at(&self, device: &Device, op: &Op, now: u64) -> Result<Proposal> {
        let t = self.tip();
        Proposal::sign(
            device,
            self.link_id(),
            op,
            Base {
                term: t.term,
                seq: t.seq,
            },
            now.saturating_add(PROPOSAL_TTL_S),
        )
    }

    /// `propose_at`, timed from the tip's own `ts` (for tools and tests that hold no clock).
    pub fn propose(&self, device: &Device, op: &Op) -> Result<Proposal> {
        self.propose_at(device, op, self.state().frontier_ts)
    }

    /// The owner root's takeover: `device` (an active owner or admin device here) sequences a new
    /// term that continues after entry `after`. The term is one more than any term this replica
    /// holds, evidence included.
    ///
    /// `after` defaults to this replica's held tip: nothing it holds is dropped, and only entries
    /// the lost sequencer gave to others are. While halted below the held tip, `after` must be
    /// given: the common prefix (`halt.seq - 1`, which every replica can take, dropping both
    /// branches of the equivocation) or a position on this replica's branch (which keeps it, but
    /// replicas holding the other branch stay halted until a takeover at or below the common
    /// prefix reaches them).
    pub fn takeover(&mut self, device: &Device, root: &SigningKey, after: Option<u64>, ts: u64) -> Result<Entry> {
        let held_tip = self.entries.len().saturating_sub(1) as u64;
        let seq = match (after, &self.halt) {
            (Some(a), _) => a,
            (None, Some(h)) if h.seq <= held_tip => {
                return Err(refused(format!(
                    "this link halted on an equivocation at seq {}, below this replica's tip (seq {held_tip}): \
                     give `after` explicitly: {} (the common prefix: every replica can take it; this replica \
                     drops seq {} to {held_tip}) or {held_tip} (keeps this replica's branch; replicas holding \
                     the other branch stay halted until a takeover at or below seq {} reaches them)",
                    h.seq,
                    h.seq - 1,
                    h.seq,
                    h.seq - 1
                )));
            }
            (None, _) => held_tip,
        };
        let e = self
            .entries
            .get(seq as usize)
            .ok_or_else(|| refused("no such position on this chain"))?;
        if hex(&crypto::public_of(root)) != self.state.owner {
            return Err(refused("a takeover is signed by the owner's fleet root"));
        }
        let at = AclPos {
            term: e.term,
            seq,
            hash: self.hashes[seq as usize].clone(),
        };
        let top = self
            .entries
            .iter()
            .chain(self.halt.iter().map(|h| &h.theirs))
            .map(|x| x.term)
            .max()
            .unwrap_or(1);
        let term = top + 1;
        let me = device.id_hex();
        let sig = crypto::sign(
            root,
            "acl-takeover",
            &takeover_bytes(&self.state.link_id, term, &at, &me)?,
        );
        let base = self.fold_to(seq)?;
        let t = Takeover {
            term,
            after: at,
            sequencer: me,
            sig: b64(&sig),
        };
        let entry = Entry::sign(
            device,
            &base.link_id,
            term,
            seq + 1,
            &base.tip,
            ts.max(base.frontier_ts),
            Some(Op::Takeover(t)),
            Vec::new(),
            BTreeMap::new(),
        )?;
        let r = self.insert(vec![entry.clone()], None);
        match r.refused {
            Some(why) if r.added == 0 => Err(refused(why)),
            _ if r.added == 0 => Err(refused("the takeover did not apply")),
            _ => Ok(entry),
        }
    }
}

static EMPTY_INCLUDED: std::sync::LazyLock<HashMap<String, u64>> = std::sync::LazyLock::new(HashMap::new);

/// Start a new link: genesis by `device` (term 1's sequencer), with a fresh epoch-0 key wrapped
/// to it.
pub fn genesis(device: &Device, name: &str, label: &str, policy: Policy, ts: u64) -> Result<(AclChain, Entry)> {
    let key = Secret32::random();
    let mut tmp = AclState {
        owner: device.root_hex().to_owned(),
        ..AclState::default()
    };
    tmp.devices.insert(
        device.id_hex(),
        DeviceState::new(device.cert.clone(), device.root_hex().to_owned()),
    );
    let wraps = tmp.make_wraps(&key.0, 0, &[device.id_hex()].into())?;
    let key_id = hex(&crypto::key_id(0, &key.0));
    let op = Op::Genesis(Genesis {
        name: name.to_owned(),
        owner: device.root_hex().to_owned(),
        label: label.to_owned(),
        policy,
        devices: vec![device.cert.clone()],
        sequencer: device.id_hex(),
        key: KeyChange {
            epoch: 0,
            key_id,
            wraps,
            prev: None,
            prev_id: None,
            from: None,
        },
    });
    let entry = Entry::sign(device, "", 1, 0, "", ts, Some(op), Vec::new(), BTreeMap::new())?;
    let mut chain = AclChain::new();
    let hash = entry.hash()?;
    chain.push(entry.clone(), hash, false)?;
    Ok((chain, entry))
}

#[cfg(test)]
mod tests;
