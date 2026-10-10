//! The link ACL log: who is in a link, with which role, which devices, and which read key.
//!
//! Every entry is `{v, link, seq, prev, author, cert, op, body, ts, sig}`, signed by a device
//! whose certificate and role are valid when the entry is applied. `link_id` is the hash of the
//! genesis entry.
//!
//! ## Ordering and forks
//!
//! Admins append rarely, so the log is nearly always a line. When two entries share a parent
//! (a fork), every member orders the whole log the same way:
//!
//! 1. by `seq` (an entry's depth), so an entry always applies after everything its author could
//!    have seen at that depth on any branch;
//! 2. at equal `seq`, by branch rank along the path from genesis, where a sibling ranks first if
//!    its author is an **owner** device, then if it is a **removal**, then by **lower hash**.
//!
//! Each entry must hold twice: where its author stood (the state along its own `prev` chain) and
//! against the merged state built so far. One that fails either (it was never valid, or its author
//! was removed on a branch that ranked first, or its invite was revoked) is **dropped** and listed,
//! so the console can show it. A removal therefore always beats a concurrent action by
//! the party it removes, and two admins removing each other resolve the same way everywhere.
//!
//! ## Read keys
//!
//! Epoch 0's key is wrapped to the creator's devices in genesis. Every later change of who may
//! read carries wraps for exactly the devices that may read after it. A removal either rotates
//! in the same entry or marks a rotation due, which any admin's daemon then appends. Each new
//! key carries the previous key sealed under it, so members can still read history.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use ed25519_dalek::SigningKey;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::codec::{self, b64, hex, unb64, unhex};
use crate::crypto::{self, KemSecrets, SUITE_X25519, SUITE_X25519_XWING, Secret32};
use crate::error::{LinkError, Result, refused};
use crate::identity::{Device, DeviceCert, MAX_LABEL};

/// The bridge kinds: the single allowlist, the same set as `core/comm/remote_relay.BRIDGE_KINDS`
/// (tests/test_link_contract.py pins the two together). No control kind crosses, ever.
pub const BRIDGE_KINDS: [&str; 7] = ["blocker", "chat", "completion", "handoff", "note", "question", "reply"];

pub const MAX_DEVICES_PER_MEMBER: usize = 8;
pub const MAX_INVITE_TTL_S: u64 = 30 * 24 * 3600;
pub const DEFAULT_INVITE_TTL_S: u64 = 24 * 3600;
/// How far an entry's own timestamp may run ahead of the verifier's clock.
pub const MAX_FUTURE_SKEW_S: u64 = 600;
/// The largest single ACL entry, canonical bytes. A rotation wrapping to 64 X-Wing devices is
/// about 110 KiB; anything bigger is refused rather than stored and relayed.
pub const MAX_ENTRY_BYTES: usize = 256 * 1024;

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
    /// The epoch whose key this wraps. An entry is refused when it differs from the epoch in
    /// force where the entry applies, so a wrap issued beside a concurrent rotation can never
    /// be filed under the new epoch with the old key inside.
    pub epoch: u64,
    pub device: String,
    pub suite: u8,
    pub enc: String,
    pub ct: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct KeyChange {
    pub epoch: u64,
    pub wraps: Vec<Wrap>,
    /// The previous epoch's key, sealed under this one (absent only for epoch 0).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prev: Option<String>,
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
    pub key: KeyChange,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Invite {
    pub invite: String,
    pub role: Role,
    pub expires: u64,
    pub single_use: bool,
    pub approval: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Join {
    pub invite: String,
    pub proof: String,
    pub root: String,
    pub label: String,
    pub devices: Vec<DeviceCert>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Accept {
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
    /// The removed device's last record the remover accepts; later ones are refused.
    pub cut: u64,
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
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RemoveMember {
    pub member: String,
    pub cut: BTreeMap<String, u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rotate: Option<KeyChange>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RevokeInvite {
    pub invite: String,
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
        }
    }
    fn is_removal(&self) -> bool {
        matches!(self, Op::RemoveDevice(_) | Op::RemoveMember(_))
    }
}

/// One signed ACL entry, exactly as it travels.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub v: u32,
    pub link: String,
    pub seq: u64,
    pub prev: String,
    pub author: String,
    pub cert: DeviceCert,
    pub op: String,
    pub body: Value,
    pub ts: u64,
    pub sig: String,
}

impl Entry {
    fn unsigned_bytes(&self) -> Result<Vec<u8>> {
        codec::jcs(&json!({
            "v": self.v, "link": self.link, "seq": self.seq, "prev": self.prev, "author": self.author,
            "cert": serde_json::to_value(&self.cert).map_err(|e| refused(e.to_string()))?,
            "op": self.op, "body": self.body, "ts": self.ts,
        }))
    }

    /// sha256 of the canonical entry, signature included. The genesis hash is the link id.
    pub fn hash(&self) -> Result<String> {
        Ok(hex(&crypto::sha256(&[&codec::canonical(self)?])))
    }

    pub fn parsed(&self) -> Result<Op> {
        serde_json::from_value(json!({"op": self.op, "body": self.body}))
            .map_err(|e| refused(format!("ACL entry body for {:?} is malformed: {e}", self.op)))
    }

    pub fn sign(device: &Device, link: &str, seq: u64, prev: &str, op: &Op, ts: u64) -> Result<Self> {
        let tagged = serde_json::to_value(op).map_err(|e| refused(e.to_string()))?;
        let mut e = Entry {
            v: 1,
            link: link.to_owned(),
            seq,
            prev: prev.to_owned(),
            author: device.id_hex(),
            cert: device.cert.clone(),
            op: op.name().to_owned(),
            body: tagged["body"].clone(),
            ts,
            sig: String::new(),
        };
        e.sig = b64(&crypto::sign(&device.sign, "acl", &e.unsigned_bytes()?));
        Ok(e)
    }

    /// Structure and signature only; authority is checked when the entry is applied.
    pub fn verify_signature(&self) -> Result<()> {
        if self.v != 1 {
            return Err(refused("unknown ACL entry version"));
        }
        if self.cert.device != self.author {
            return Err(refused("ACL entry author does not match its certificate"));
        }
        self.cert.verify()?;
        crypto::verify(
            &unhex::<32>(&self.author)?,
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

fn join_proof_bytes(link: &str, prev: &str, root: &str, devices: &[DeviceCert]) -> Result<Vec<u8>> {
    let ids: Vec<&str> = devices.iter().map(|d| d.device.as_str()).collect();
    codec::jcs(&json!({"link": link, "prev": prev, "root": root, "devices": ids}))
}

// ------------------------------------------------------------------------------------------ state

#[derive(Clone, Debug, Serialize)]
pub struct DeviceState {
    pub cert: DeviceCert,
    pub member: String,
    /// Set once removed: the last seq of this device's feed that is still accepted.
    pub cut: Option<u64>,
}

#[derive(Clone, Debug, Serialize)]
pub struct MemberState {
    pub root: String,
    pub label: String,
    pub role: Role,
    pub pending: bool,
    pub removed: bool,
    pub devices: BTreeSet<String>,
    /// The join entry that admitted this member (genesis for the owner).
    pub joined: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct InviteState {
    pub role: Role,
    pub expires: u64,
    pub single_use: bool,
    pub approval: bool,
    pub used: bool,
    pub revoked: bool,
    pub by: String,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct AclState {
    pub link_id: String,
    pub name: String,
    pub owner: String,
    pub policy: Option<Policy>,
    pub members: BTreeMap<String, MemberState>,
    pub devices: BTreeMap<String, DeviceState>,
    pub invites: BTreeMap<String, InviteState>,
    pub epoch: u64,
    /// Every wrap ever issued, by epoch.
    pub wraps: BTreeMap<u64, Vec<Wrap>>,
    /// Epoch k's `prev`: the key of epoch k-1 sealed under the key of epoch k.
    pub prev_keys: BTreeMap<u64, String>,
    pub rotation_due: bool,
    /// When the rotation became due (the `ts` of the entry that made it due).
    pub rotation_due_since: u64,
    /// The epoch in force after each entry that was valid where its author stood, applied in
    /// the merged order or not. A record is checked against this, so a head that lost a fork
    /// cannot block its author's feed.
    pub causal_epoch: BTreeMap<String, u64>,
    /// Joins waiting for an `accept`: join entry hash -> member root.
    pub pending_joins: BTreeMap<String, String>,
    /// Epoch in effect after each applied entry, by entry hash.
    pub epoch_at: BTreeMap<String, u64>,
    pub applied: Vec<String>,
    pub dropped: Vec<(String, String)>,
    pub head: String,
    pub head_seq: u64,
}

impl AclState {
    pub fn policy(&self) -> Policy {
        self.policy.clone().unwrap_or_default()
    }

    /// The member and role behind an active device, if it is one.
    pub fn active_device(&self, device: &str) -> Option<(&MemberState, &DeviceState)> {
        let d = self.devices.get(device)?;
        let m = self.members.get(&d.member)?;
        (d.cut.is_none() && !m.removed && !m.pending).then_some((m, d))
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

    /// HPKE `info` for a wrap. It binds the owner root rather than the link id, because genesis
    /// wraps exist before the link id does (the id is the hash of the genesis entry).
    fn wrap_info(&self, epoch: u64, device: &str) -> Vec<u8> {
        [
            self.owner.as_bytes(),
            b"|",
            epoch.to_string().as_bytes(),
            b"|",
            device.as_bytes(),
        ]
        .concat()
    }

    /// Wrap `key` (the key of `epoch`) to each of `devices`.
    pub fn make_wraps(&self, key: &[u8; 32], epoch: u64, devices: &BTreeSet<String>) -> Result<Vec<Wrap>> {
        devices
            .iter()
            .map(|d| {
                let cert = &self
                    .devices
                    .get(d)
                    .ok_or_else(|| refused(format!("unknown device {d}")))?
                    .cert;
                let (suite, enc, ct) = crypto::wrap(key, &cert.kem()?, &self.wrap_info(epoch, d))?;
                Ok(Wrap {
                    epoch,
                    device: d.clone(),
                    suite,
                    enc: b64(&enc),
                    ct: b64(&ct),
                })
            })
            .collect()
    }

    /// This device's key for `epoch`: unwrap directly, or walk back from a later epoch.
    pub fn read_key(&self, epoch: u64, device: &str, kem: &KemSecrets) -> Result<Secret32> {
        let mut found = None;
        for (e, wraps) in self.wraps.range(epoch..) {
            if let Some(w) = wraps.iter().find(|w| w.device == device) {
                found = Some((
                    *e,
                    crypto::unwrap(
                        w.suite,
                        &unb64(&w.enc)?,
                        &unb64(&w.ct)?,
                        kem,
                        &self.wrap_info(*e, device),
                    )?,
                ));
                break;
            }
        }
        let (mut at, mut key) =
            found.ok_or_else(|| LinkError::Unavailable(format!("no read key for epoch {epoch}")))?;
        while at > epoch {
            let sealed = self
                .prev_keys
                .get(&at)
                .ok_or_else(|| refused(format!("epoch {at} carries no previous key")))?;
            let plain = crypto::open(&key.0, &unb64(sealed)?, &self.prev_key_aad(at))?;
            key = Secret32(
                plain
                    .as_slice()
                    .try_into()
                    .map_err(|_| refused("previous key has the wrong length"))?,
            );
            at -= 1;
        }
        Ok(key)
    }

    fn prev_key_aad(&self, epoch: u64) -> Vec<u8> {
        [self.link_id.as_bytes(), b"|prev|", epoch.to_string().as_bytes()].concat()
    }

    /// A complete key change to `epoch + 1` for the devices that may read after it.
    pub fn new_key_change(&self, current: &Secret32, keyed: &BTreeSet<String>) -> Result<(KeyChange, Secret32)> {
        let next = Secret32::random();
        let epoch = self.epoch + 1;
        let prev = crypto::seal(&next.0, &current.0, &self.prev_key_aad(epoch));
        Ok((
            KeyChange {
                epoch,
                wraps: self.make_wraps(&next.0, epoch, keyed)?,
                prev: Some(b64(&prev)),
            },
            next,
        ))
    }

    /// Wraps must cover exactly `expected`, with the suite each device's certificate allows.
    fn check_wraps(&self, epoch: u64, wraps: &[Wrap], expected: &BTreeSet<String>, extra: &[DeviceCert]) -> Result<()> {
        if wraps.iter().any(|w| w.epoch != epoch) {
            return Err(refused("a wrap names another epoch than the one in force"));
        }
        let got: BTreeSet<String> = wraps.iter().map(|w| w.device.clone()).collect();
        if got.len() != wraps.len() {
            return Err(refused("a device is wrapped to twice"));
        }
        if &got != expected {
            return Err(refused("wraps do not cover exactly the devices that may read"));
        }
        for w in wraps {
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

    fn check_key_change(&self, k: &KeyChange, keyed: &BTreeSet<String>) -> Result<()> {
        if k.epoch != self.epoch + 1 {
            return Err(refused("key change does not advance the epoch by one"));
        }
        if unb64(
            k.prev
                .as_deref()
                .ok_or_else(|| refused("key change lacks the previous key"))?,
        )?
        .len()
            != crypto::NONCE_LEN + 32 + crypto::TAG_LEN
        {
            return Err(refused("sealed previous key has the wrong size"));
        }
        self.check_wraps(k.epoch, &k.wraps, keyed, &[])
    }

    fn apply_key_change(&mut self, k: &KeyChange) {
        self.epoch = k.epoch;
        self.wraps.entry(k.epoch).or_default().extend(k.wraps.iter().cloned());
        if let Some(p) = &k.prev {
            self.prev_keys.insert(k.epoch, p.clone());
        }
        self.rotation_due = false;
    }

    fn live_members(&self) -> usize {
        self.members.values().filter(|m| !m.removed).count()
    }

    /// Check `e` against this state and apply it. Atomic: on error nothing changes.
    pub fn apply(&mut self, e: &Entry, hash: &str) -> Result<()> {
        let mut next = self.clone();
        next.apply_inner(e, hash)?;
        if next.rotation_due && !self.rotation_due {
            next.rotation_due_since = e.ts;
        }
        next.applied.push(hash.to_owned());
        next.epoch_at.insert(hash.to_owned(), next.epoch);
        if e.seq >= next.head_seq || next.head.is_empty() {
            next.head = hash.to_owned();
            next.head_seq = e.seq;
        }
        *self = next;
        Ok(())
    }

    fn apply_inner(&mut self, e: &Entry, hash: &str) -> Result<()> {
        let op = e.parsed()?;
        if !e.cert.valid_at(e.ts) {
            return Err(refused("author certificate is not valid at the entry's time"));
        }
        if let Op::Genesis(g) = &op {
            return self.apply_genesis(e, g, hash);
        }
        if e.link != self.link_id {
            return Err(refused("ACL entry belongs to another link"));
        }
        if let Op::Join(j) = &op {
            return self.apply_join(e, j, hash);
        }
        let (author_root, author_role) = {
            let (m, d) = self
                .active_device(&e.author)
                .ok_or_else(|| refused("author is not an active member device"))?;
            if !d.cert.same_keys(&e.cert) {
                return Err(refused("author certificate does not match the one in the log"));
            }
            (m.root.clone(), m.role)
        };
        // A renewed certificate travels with the author's own entries.
        if let Some(d) = self.devices.get_mut(&e.author)
            && e.cert.not_after > d.cert.not_after
        {
            d.cert = e.cert.clone();
        }
        let is_owner = author_root == self.owner;
        match op {
            Op::Genesis(_) | Op::Join(_) => unreachable!("handled above"),
            Op::Invite(i) => {
                if !author_role.admin() {
                    return Err(refused("only an admin may invite"));
                }
                if i.role == Role::Owner || (i.role == Role::Admin && !is_owner) {
                    return Err(refused("that role cannot be granted by invite from this author"));
                }
                unhex::<32>(&i.invite)?;
                if self.invites.contains_key(&i.invite) {
                    return Err(refused("invite key already used in this link"));
                }
                if i.expires <= e.ts || i.expires - e.ts > MAX_INVITE_TTL_S {
                    return Err(refused("invite expiry is in the past or too far ahead"));
                }
                self.invites.insert(
                    i.invite.clone(),
                    InviteState {
                        role: i.role,
                        expires: i.expires,
                        single_use: i.single_use,
                        approval: i.approval,
                        used: false,
                        revoked: false,
                        by: author_root,
                    },
                );
            }
            Op::Accept(a) => {
                if !author_role.admin() || !self.has_wrap(self.epoch, &e.author) {
                    return Err(refused("only an admin holding the read key may accept"));
                }
                let root = self
                    .pending_joins
                    .get(&a.join)
                    .cloned()
                    .ok_or_else(|| refused("no such pending join"))?;
                let member = self
                    .members
                    .get(&root)
                    .ok_or_else(|| refused("pending member vanished"))?;
                // Only live devices get the key: one cut before the accept never does.
                let expected: BTreeSet<String> = if member.role.reads() {
                    member
                        .devices
                        .iter()
                        .filter(|d| self.devices.get(*d).is_some_and(|s| s.cut.is_none()))
                        .cloned()
                        .collect()
                } else {
                    BTreeSet::new()
                };
                self.check_wraps(self.epoch, &a.wraps, &expected, &[])?;
                self.wraps
                    .entry(self.epoch)
                    .or_default()
                    .extend(a.wraps.iter().cloned());
                self.pending_joins.remove(&a.join);
                if let Some(m) = self.members.get_mut(&root) {
                    m.pending = false;
                }
            }
            Op::Decline(d) => {
                if !author_role.admin() {
                    return Err(refused("only an admin may decline"));
                }
                let root = self
                    .pending_joins
                    .remove(&d.join)
                    .ok_or_else(|| refused("no such pending join"))?;
                let member = self
                    .members
                    .get_mut(&root)
                    .ok_or_else(|| refused("pending member vanished"))?;
                if !member.pending {
                    return Err(refused("that join was already admitted; remove the member instead"));
                }
                member.removed = true;
                for dev in member.devices.clone() {
                    if let Some(s) = self.devices.get_mut(&dev) {
                        s.cut = Some(0);
                    }
                }
            }
            Op::AddDevice(a) => {
                a.cert.verify()?;
                let member_root = a.cert.root.clone();
                if member_root != author_root && !author_role.admin() {
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
                if let Some(existing) = self.devices.get(&a.cert.device) {
                    // A renewal: same keys, later expiry, no new wraps.
                    if !existing.cert.same_keys(&a.cert)
                        || existing.cut.is_some()
                        || a.cert.not_after <= existing.cert.not_after
                    {
                        return Err(refused(
                            "device already listed; only a later renewal of the same keys is allowed",
                        ));
                    }
                    if !a.wraps.is_empty() {
                        return Err(refused("a renewal carries no wraps"));
                    }
                    self.devices.get_mut(&a.cert.device).expect("checked").cert = a.cert.clone();
                    return Ok(());
                }
                if !a.cert.valid_at(e.ts) {
                    return Err(refused("new device certificate is not valid now"));
                }
                if member.devices.len() >= MAX_DEVICES_PER_MEMBER {
                    return Err(refused("member already has the maximum number of devices"));
                }
                let expected: BTreeSet<String> = if reads {
                    [a.cert.device.clone()].into()
                } else {
                    BTreeSet::new()
                };
                if reads && !self.has_wrap(self.epoch, &e.author) {
                    return Err(refused(
                        "adding a reading device needs an author that holds the read key",
                    ));
                }
                self.check_wraps(self.epoch, &a.wraps, &expected, std::slice::from_ref(&a.cert))?;
                self.devices.insert(
                    a.cert.device.clone(),
                    DeviceState {
                        cert: a.cert.clone(),
                        member: member_root.clone(),
                        cut: None,
                    },
                );
                self.members
                    .get_mut(&member_root)
                    .expect("checked")
                    .devices
                    .insert(a.cert.device.clone());
                self.wraps
                    .entry(self.epoch)
                    .or_default()
                    .extend(a.wraps.iter().cloned());
            }
            Op::RemoveDevice(r) => {
                let target = self.devices.get(&r.device).ok_or_else(|| refused("no such device"))?;
                if target.cut.is_some() {
                    return Err(refused("device already removed"));
                }
                let target_member = target.member.clone();
                if target_member != author_root && !author_role.admin() {
                    return Err(refused("only the member itself or an admin may remove a device"));
                }
                if target_member == self.owner && author_root != self.owner {
                    return Err(refused("only the owner may remove an owner device"));
                }
                let live_devices = self.members[&target_member]
                    .devices
                    .iter()
                    .filter(|d| self.devices.get(*d).is_some_and(|s| s.cut.is_none()))
                    .count();
                if target_member == self.owner && live_devices <= 1 {
                    return Err(refused("the owner's last device cannot be removed"));
                }
                if r.device == e.author && r.rotate.is_some() {
                    return Err(refused("a device that removes itself cannot pick the next key"));
                }
                self.devices.get_mut(&r.device).expect("checked").cut = Some(r.cut);
                self.removal_rotation(r.rotate.as_ref(), &e.author)?;
            }
            Op::SetRole(s) => {
                let target = self.members.get(&s.member).ok_or_else(|| refused("no such member"))?;
                if target.removed || target.pending {
                    return Err(refused("that member is not active"));
                }
                if s.role == Role::Owner || s.member == self.owner {
                    return Err(refused("the owner role is fixed at genesis"));
                }
                let admin_change = s.role == Role::Admin || target.role == Role::Admin;
                if !(is_owner || (author_role.admin() && !admin_change)) {
                    return Err(refused("this author may not make that role change"));
                }
                let (was_reading, devices) = (target.role.reads(), target.devices.clone());
                let live: BTreeSet<String> = devices
                    .into_iter()
                    .filter(|d| self.devices.get(d).is_some_and(|x| x.cut.is_none()))
                    .collect();
                if s.role.reads() && !was_reading {
                    if !self.has_wrap(self.epoch, &e.author) {
                        return Err(refused("granting read access needs an author that holds the read key"));
                    }
                    self.check_wraps(self.epoch, &s.wraps, &live, &[])?;
                    self.wraps
                        .entry(self.epoch)
                        .or_default()
                        .extend(s.wraps.iter().cloned());
                } else if !s.wraps.is_empty() {
                    return Err(refused("this role change carries no wraps"));
                }
                if was_reading && !s.role.reads() {
                    self.rotation_due = true;
                }
                self.members.get_mut(&s.member).expect("checked").role = s.role;
            }
            Op::RemoveMember(r) => {
                let target = self.members.get(&r.member).ok_or_else(|| refused("no such member"))?;
                if target.removed {
                    return Err(refused("member already removed"));
                }
                let leaving = r.member == author_root;
                if r.member == self.owner {
                    return Err(refused("the owner cannot be removed or leave"));
                }
                if !leaving && !(author_role.admin() && (is_owner || target.role < Role::Admin)) {
                    return Err(refused(
                        "only an admin may remove a member, and only the owner may remove an admin",
                    ));
                }
                if leaving && r.rotate.is_some() {
                    return Err(refused("a member that leaves cannot pick the next key"));
                }
                let target_devices = target.devices.clone();
                if r.cut.keys().any(|d| !target_devices.contains(d)) {
                    return Err(refused("cut names a device of another member"));
                }
                self.members.get_mut(&r.member).expect("checked").removed = true;
                self.pending_joins.retain(|_, root| *root != r.member);
                for d in target_devices {
                    if let Some(s) = self.devices.get_mut(&d)
                        && s.cut.is_none()
                    {
                        s.cut = Some(r.cut.get(&d).copied().unwrap_or(0));
                    }
                }
                self.removal_rotation(r.rotate.as_ref(), &e.author)?;
            }
            Op::RotateKey(k) => {
                if !author_role.admin() || !self.has_wrap(self.epoch, &e.author) {
                    return Err(refused("only an admin holding the read key may rotate"));
                }
                let keyed = self.keyed_devices();
                self.check_key_change(&k, &keyed)?;
                self.apply_key_change(&k);
            }
            Op::RevokeInvite(r) => {
                if !author_role.admin() {
                    return Err(refused("only an admin may revoke an invite"));
                }
                let inv = self
                    .invites
                    .get_mut(&r.invite)
                    .ok_or_else(|| refused("no such invite"))?;
                // A reusable invite stays revocable after its first use: that is when it matters.
                if (inv.single_use && inv.used) || inv.revoked {
                    return Err(refused("invite is already used or revoked"));
                }
                inv.revoked = true;
            }
        }
        Ok(())
    }

    fn removal_rotation(&mut self, rotate: Option<&KeyChange>, author: &str) -> Result<()> {
        match rotate {
            Some(k) => {
                if !self.has_wrap(self.epoch, author) {
                    return Err(refused("rotation needs an author that holds the read key"));
                }
                let keyed = self.keyed_devices();
                self.check_key_change(k, &keyed)?;
                self.apply_key_change(k);
            }
            None => self.rotation_due = true,
        }
        Ok(())
    }

    fn apply_genesis(&mut self, e: &Entry, g: &Genesis, hash: &str) -> Result<()> {
        if !self.link_id.is_empty() {
            return Err(refused("a link has exactly one genesis"));
        }
        if e.seq != 0 || !e.prev.is_empty() || !e.link.is_empty() {
            return Err(refused("genesis must have seq 0, no prev and no link"));
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
        if g.policy.max_members < 2 || g.policy.retention_days == 0 || g.policy.rate_per_hour == 0 {
            return Err(refused("link policy limits are out of range"));
        }
        unhex::<32>(&g.owner)?;
        if e.cert.root != g.owner || !g.devices.iter().any(|d| d.device == e.author) {
            return Err(refused("genesis must be signed by one of the owner's devices"));
        }
        if g.devices.is_empty() || g.devices.len() > MAX_DEVICES_PER_MEMBER {
            return Err(refused("genesis lists no devices, or too many"));
        }
        self.link_id = hash.to_owned();
        self.name = g.name.clone();
        self.owner = g.owner.clone();
        self.policy = Some(g.policy.clone());
        let mut devices = BTreeSet::new();
        for c in &g.devices {
            c.verify()?;
            if c.root != g.owner || !c.valid_at(e.ts) || !devices.insert(c.device.clone()) {
                return Err(refused(
                    "genesis device is not the owner's, not valid now, or listed twice",
                ));
            }
            self.devices.insert(
                c.device.clone(),
                DeviceState {
                    cert: c.clone(),
                    member: g.owner.clone(),
                    cut: None,
                },
            );
        }
        self.members.insert(
            g.owner.clone(),
            MemberState {
                root: g.owner.clone(),
                label: g.label.clone(),
                role: Role::Owner,
                pending: false,
                removed: false,
                devices: devices.clone(),
                joined: hash.to_owned(),
            },
        );
        if g.key.epoch != 0 || g.key.prev.is_some() {
            return Err(refused("genesis key must be epoch 0 with no previous key"));
        }
        self.check_wraps(0, &g.key.wraps, &devices, &[])?;
        self.wraps.insert(0, g.key.wraps.clone());
        Ok(())
    }

    fn apply_join(&mut self, e: &Entry, j: &Join, hash: &str) -> Result<()> {
        let inv = self
            .invites
            .get(&j.invite)
            .ok_or_else(|| refused("no such invite"))?
            .clone();
        if inv.revoked || (inv.single_use && inv.used) || e.ts >= inv.expires {
            return Err(refused("invite is revoked, used, or expired"));
        }
        // An invite is only as good as its inviter: removed or demoted, their invites die.
        if self
            .members
            .get(&inv.by)
            .is_none_or(|m| m.removed || m.pending || !m.role.admin())
        {
            return Err(refused("the inviter is no longer an admin of this link"));
        }
        unhex::<32>(&j.root)?;
        if let Some(m) = self.members.get(&j.root)
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
        // Labels name members in commands and in @fleet/seat addresses, so they must be unique and
        // must not look like a root key.
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
        if j.devices.is_empty() || j.devices.len() > MAX_DEVICES_PER_MEMBER {
            return Err(refused("join lists no devices, or too many"));
        }
        if !j.devices.iter().any(|d| d.device == e.author && d.same_keys(&e.cert)) {
            return Err(refused("join must be signed by one of the joining devices"));
        }
        let mut ids = BTreeSet::new();
        for c in &j.devices {
            c.verify()?;
            if c.root != j.root
                || !c.valid_at(e.ts)
                || self.devices.contains_key(&c.device)
                || !ids.insert(c.device.clone())
            {
                return Err(refused(
                    "joining device is foreign, expired, already known, or listed twice",
                ));
            }
        }
        let proof = join_proof_bytes(&self.link_id, &e.prev, &j.root, &j.devices)?;
        crypto::verify(&unhex::<32>(&j.invite)?, "join", &proof, &unb64(&j.proof)?)?;
        // An approval invite waits for a person; any other is admitted at once and waits only for
        // an admin's daemon to wrap the read key to it (its `accept`).
        self.invites.get_mut(&j.invite).expect("checked").used = true;
        for c in &j.devices {
            self.devices.insert(
                c.device.clone(),
                DeviceState {
                    cert: c.clone(),
                    member: j.root.clone(),
                    cut: None,
                },
            );
        }
        self.members.insert(
            j.root.clone(),
            MemberState {
                root: j.root.clone(),
                label: j.label.clone(),
                role: inv.role,
                pending: inv.approval,
                removed: false,
                devices: ids,
                joined: hash.to_owned(),
            },
        );
        if inv.approval || inv.role.reads() {
            self.pending_joins.insert(hash.to_owned(), j.root.clone());
        }
        Ok(())
    }
}

/// Build a join entry for `device` from an invite secret, against the inviter's current head.
pub fn make_join(
    device: &Device,
    secret: &[u8; 32],
    link: &str,
    head: &str,
    head_seq: u64,
    label: &str,
    ts: u64,
) -> Result<Entry> {
    let key = invite_key(secret);
    let devices = vec![device.cert.clone()];
    let proof = crypto::sign(
        &key,
        "join",
        &join_proof_bytes(link, head, device.root_hex(), &devices)?,
    );
    let op = Op::Join(Join {
        invite: hex(&crypto::public_of(&key)),
        proof: b64(&proof),
        root: device.root_hex().to_owned(),
        label: label.to_owned(),
        devices,
    });
    Entry::sign(device, link, head_seq + 1, head, &op, ts)
}

// -------------------------------------------------------------------------------------- the log

/// All entries known for one link, and the state they resolve to.
#[derive(Clone, Default)]
pub struct AclLog {
    entries: HashMap<String, Entry>,
    state: AclState,
}

impl AclLog {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn state(&self) -> &AclState {
        &self.state
    }

    pub fn link_id(&self) -> &str {
        &self.state.link_id
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn contains(&self, hash: &str) -> bool {
        self.entries.contains_key(hash)
    }

    pub fn get(&self, hash: &str) -> Option<&Entry> {
        self.entries.get(hash)
    }

    pub fn hashes(&self) -> BTreeSet<String> {
        self.entries.keys().cloned().collect()
    }

    /// Entries in application order.
    pub fn ordered(&self) -> Vec<(&String, &Entry)> {
        let ranks = self.ranks();
        let mut all: Vec<(&String, &Entry)> = self.entries.iter().collect();
        all.sort_by(|a, b| (a.1.seq, &ranks[a.0]).cmp(&(b.1.seq, &ranks[b.0])));
        all
    }

    /// Insert verified entries (any order, duplicates ignored) and re-resolve the state.
    /// Returns how many were new. Entries whose parent is unknown are refused.
    pub fn insert(&mut self, batch: Vec<Entry>) -> Result<usize> {
        self.insert_at(batch, None)
    }

    /// Insert entries received at `now` (the verifier's clock). Each entry is checked on its own:
    /// one bad entry does not sink the batch, and entries that build on it are skipped with it.
    /// Entries that were never valid where their author stood are discarded, not stored, so
    /// nobody can grow the log with refused junk. Returns how many entries were kept.
    pub fn insert_at(&mut self, mut batch: Vec<Entry>, now: Option<u64>) -> Result<usize> {
        batch.sort_by_key(|e| e.seq);
        let mut fresh: Vec<String> = Vec::new();
        let mut first_err: Option<LinkError> = None;
        for e in batch {
            match self.check_structure(&e, now) {
                Ok(Some(hash)) => {
                    self.entries.insert(hash.clone(), e);
                    if self.state.link_id.is_empty() {
                        self.resolve();
                        if self.state.link_id != hash {
                            self.entries.remove(&hash);
                            self.resolve();
                            first_err.get_or_insert(refused("genesis does not apply"));
                            continue;
                        }
                    }
                    fresh.push(hash);
                }
                Ok(None) => {}
                Err(err) => {
                    first_err.get_or_insert(err);
                }
            }
        }
        if !fresh.is_empty() {
            self.resolve();
            let never: Vec<String> = self
                .state
                .dropped
                .iter()
                .filter(|(_, why)| why.starts_with("not valid where") || why.starts_with("builds on"))
                .map(|(h, _)| h.clone())
                .collect();
            for h in &never {
                self.entries.remove(h);
            }
            if let Some((_, why)) = self
                .state
                .dropped
                .iter()
                .find(|(h, _)| fresh.contains(h) && never.contains(h))
            {
                first_err.get_or_insert(refused(why.clone()));
            }
            fresh.retain(|h| self.entries.contains_key(h));
        }
        match (fresh.len(), first_err) {
            (0, Some(err)) => Err(err),
            (n, _) => Ok(n),
        }
    }

    /// Signature, size, link, seq, parent and time. `Ok(None)` for an entry already held.
    fn check_structure(&self, e: &Entry, now: Option<u64>) -> Result<Option<String>> {
        let hash = e.hash()?;
        if self.entries.contains_key(&hash) {
            return Ok(None);
        }
        if codec::canonical(e)?.len() > MAX_ENTRY_BYTES {
            return Err(refused("ACL entry is too large"));
        }
        if let Some(n) = now
            && e.ts > n + MAX_FUTURE_SKEW_S
        {
            return Err(refused("ACL entry is dated in the future"));
        }
        e.verify_signature()?;
        if e.seq == 0 {
            if !self.entries.is_empty() {
                return Err(refused("a second genesis for this link"));
            }
        } else {
            let parent = self
                .entries
                .get(&e.prev)
                .ok_or_else(|| refused("ACL entry's parent is unknown"))?;
            if parent.seq + 1 != e.seq || e.link != self.state.link_id {
                return Err(refused("ACL entry seq or link does not follow its parent"));
            }
            if e.ts < parent.ts {
                return Err(refused("ACL entry is dated before its parent"));
            }
        }
        Ok(Some(hash))
    }

    /// The branch rank of every entry: its path of sibling ranks from genesis.
    fn ranks(&self) -> HashMap<String, Vec<(u8, u8, String)>> {
        let owner = self
            .entries
            .values()
            .find(|e| e.seq == 0)
            .map(|g| g.cert.root.clone())
            .unwrap_or_default();
        let mut out: HashMap<String, Vec<(u8, u8, String)>> = HashMap::new();
        let mut by_seq: Vec<(&String, &Entry)> = self.entries.iter().collect();
        by_seq.sort_by_key(|(_, e)| e.seq);
        for (hash, e) in by_seq {
            let removal = e.parsed().map(|op| op.is_removal()).unwrap_or(false);
            let me = (u8::from(e.cert.root != owner), u8::from(!removal), hash.clone());
            let mut path = out.get(&e.prev).cloned().unwrap_or_default();
            path.push(me);
            out.insert(hash.clone(), path);
        }
        out
    }

    /// Apply every entry twice: once where its author stood (the state along its own `prev`
    /// chain, as p2panda-auth does), and once in the merged order. It must hold in both. An
    /// entry that builds on one that was never valid is not valid either.
    fn resolve(&mut self) {
        let mut state = AclState::default();
        let mut causal: HashMap<String, AclState> = HashMap::new();
        let ordered: Vec<(String, Entry)> = self
            .ordered()
            .into_iter()
            .map(|(h, e)| (h.clone(), e.clone()))
            .collect();
        for (hash, e) in ordered {
            let mut own = if e.seq == 0 {
                AclState::default()
            } else if let Some(parent) = causal.get(&e.prev) {
                parent.clone()
            } else {
                state
                    .dropped
                    .push((hash, "builds on an entry that was never valid".into()));
                continue;
            };
            if let Err(err) = own.apply(&e, &hash) {
                state
                    .dropped
                    .push((hash, format!("not valid where its author stood: {err}")));
                continue;
            }
            state.causal_epoch.insert(hash.clone(), own.epoch);
            causal.insert(hash.clone(), own);
            if let Err(err) = state.apply(&e, &hash) {
                state.dropped.push((hash, err.to_string()));
            }
        }
        self.state = state;
    }

    /// Entries the peer lacks, given the hashes it holds, in application order.
    pub fn missing_for(&self, theirs: &BTreeSet<String>) -> Vec<Entry> {
        self.ordered()
            .into_iter()
            .filter(|(h, _)| !theirs.contains(*h))
            .map(|(_, e)| e.clone())
            .collect()
    }

    /// Sign `op` as the next entry after the current head and add it.
    pub fn append(&mut self, device: &Device, op: Op, ts: u64) -> Result<Entry> {
        let (link, seq, prev) = if matches!(op, Op::Genesis(_)) {
            (String::new(), 0, String::new())
        } else {
            (
                self.state.link_id.clone(),
                self.state.head_seq + 1,
                self.state.head.clone(),
            )
        };
        let entry = Entry::sign(device, &link, seq, &prev, &op, ts)?;
        let hash = entry.hash()?;
        // Check first against the resolved state, so a refused op never enters the log.
        self.state.clone().apply(&entry, &hash)?;
        self.insert(vec![entry.clone()])?;
        if let Some((_, why)) = self.state.dropped.iter().find(|(h, _)| *h == hash) {
            return Err(refused(format!("entry was dropped on resolve: {why}")));
        }
        Ok(entry)
    }
}

/// Start a new link: genesis by `device`, with a fresh epoch-0 key wrapped to its devices.
pub fn genesis(device: &Device, name: &str, label: &str, policy: Policy, ts: u64) -> Result<(AclLog, Entry)> {
    let key = Secret32::random();
    let mut tmp = AclState {
        owner: device.root_hex().to_owned(),
        ..AclState::default()
    };
    tmp.devices.insert(
        device.id_hex(),
        DeviceState {
            cert: device.cert.clone(),
            member: device.root_hex().to_owned(),
            cut: None,
        },
    );
    let wraps = tmp.make_wraps(&key.0, 0, &[device.id_hex()].into())?;
    let op = Op::Genesis(Genesis {
        name: name.to_owned(),
        owner: device.root_hex().to_owned(),
        label: label.to_owned(),
        policy,
        devices: vec![device.cert.clone()],
        key: KeyChange {
            epoch: 0,
            wraps,
            prev: None,
        },
    });
    let mut log = AclLog::new();
    let entry = log.append(device, op, ts)?;
    Ok((log, entry))
}

#[cfg(test)]
mod tests;
