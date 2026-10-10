//! One link, as this device holds it: its ACL log, its store and the rules that join them.
//!
//! Admission of a record is three checks in a fixed order, cheapest first:
//!
//! 1. **Authentic**: shape, ciphertext hash and the author's signature (`Record::verify`).
//! 2. **Authorised**: the author is a device of a member that may write, at the ACL head the
//!    record names and now; a removed device only up to its cut; nobody frozen.
//! 3. **In order**: the author's feed is gapless. The same seq with a different record is
//!    equivocation: the author is frozen and an alarm raised.
//!
//! Only then is the body opened, and only for this fleet's own reading. Whether it reaches an
//! agent is not decided here at all: admitted records become events for Python's quarantine.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use serde_json::{Value, json};

use crate::acl::{self, AclLog, AclState, Entry, Op, Policy, Role};
use crate::codec::{self, hex, unhex};
use crate::crypto::{self, Secret32};
use crate::error::{LinkError, Result, refused};
use crate::identity::{Device, fleet_fingerprint, safety_number};
use crate::record::{ACK_KIND, Body, Record, Seal};
use crate::store::{self, Store};

/// What happened to one received record.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Admit {
    /// Stored, with its status (`admitted`, `own`, `opaque` or `withheld`).
    Stored { id: String, status: String },
    /// Already held: a replay or a second path. A no-op.
    Duplicate,
    /// Not the next record of its author's feed; ask again from `have`.
    Gap { author: String, have: u64 },
    /// Refused. The reason is for the local log only.
    Refused(String),
}

pub struct Link {
    pub store: Store,
    pub acl: AclLog,
    pub path: Option<PathBuf>,
}

pub fn db_path(dir: &Path, link_id: &str) -> PathBuf {
    dir.join(format!("{link_id}.db"))
}

impl Link {
    /// Create a new link owned by this device's fleet.
    pub fn create(
        dir: Option<&Path>,
        device: &Device,
        name: &str,
        label: &str,
        policy: Policy,
        now: u64,
    ) -> Result<Self> {
        let (acl, genesis) = acl::genesis(device, name, label, policy, now)?;
        let mut link = Self::empty(dir, acl.link_id())?;
        link.store.put_acl(&genesis.hash()?, &genesis, now)?;
        link.acl = acl;
        link.store.set_meta("link_id", link.acl.link_id())?;
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
        link.add_acl(entries, now)?;
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
            acl: AclLog::new(),
            path,
        })
    }

    pub fn open(path: &Path) -> Result<Self> {
        let store = Store::open(path)?;
        let mut acl = AclLog::new();
        acl.insert(store.acl_entries()?)?;
        if acl.is_empty() {
            return Err(LinkError::Unavailable(format!("{} holds no link", path.display())));
        }
        Ok(Self {
            store,
            acl,
            path: Some(path.to_owned()),
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

    /// Merge ACL entries from a peer or a bundle. Returns how many were new.
    pub fn add_acl(&mut self, entries: Vec<Entry>, now: u64) -> Result<usize> {
        let fresh: Vec<Entry> = entries
            .into_iter()
            .filter(|e| e.hash().map(|h| !self.acl.contains(&h)).unwrap_or(true))
            .collect();
        let mut trial = self.acl.clone();
        let added = trial.insert(fresh.clone())?;
        if added > 0 {
            for e in &fresh {
                self.store.put_acl(&e.hash()?, e, now)?;
            }
            self.acl = trial;
        }
        Ok(added)
    }

    pub fn append(&mut self, device: &Device, op: Op, now: u64) -> Result<Entry> {
        let mut trial = self.acl.clone();
        let entry = trial.append(device, op, now)?;
        self.store.put_acl(&entry.hash()?, &entry, now)?;
        self.acl = trial;
        Ok(entry)
    }

    pub fn read_key(&self, device: &Device, epoch: u64) -> Result<Secret32> {
        self.state().read_key(epoch, &device.id_hex(), &device.kem)
    }

    pub fn my_role(&self, device: &Device) -> Option<Role> {
        self.state().active_device(&device.id_hex()).map(|(m, _)| m.role)
    }

    // ------------------------------------------------------------------------------ membership

    /// Publish an invite. Returns the secret that goes into the invite code.
    pub fn invite(
        &mut self,
        device: &Device,
        role: Role,
        ttl_s: u64,
        single_use: bool,
        approval: bool,
        now: u64,
    ) -> Result<[u8; 32]> {
        let secret = crypto::random32();
        let op = Op::Invite(acl::Invite {
            invite: hex(&crypto::public_of(&acl::invite_key(&secret))),
            role,
            expires: now + ttl_s.clamp(60, acl::MAX_INVITE_TTL_S),
            single_use,
            approval,
        });
        self.append(device, op, now)?;
        Ok(secret)
    }

    pub fn accept(&mut self, device: &Device, join: &str, now: u64) -> Result<Entry> {
        let s = self.state().clone();
        let root = s
            .pending_joins
            .get(join)
            .ok_or_else(|| refused("no such pending join"))?;
        let m = &s.members[root];
        let devices = if m.role.reads() {
            m.devices.clone()
        } else {
            BTreeSet::new()
        };
        let wraps = s.make_wraps(&self.read_key(device, s.epoch)?.0, s.epoch, &devices)?;
        self.append(
            device,
            Op::Accept(acl::Accept {
                join: join.to_owned(),
                wraps,
            }),
            now,
        )
    }

    pub fn decline(&mut self, device: &Device, join: &str, now: u64) -> Result<Entry> {
        self.append(device, Op::Decline(acl::Decline { join: join.to_owned() }), now)
    }

    /// A new key for everyone who may still read, if this device holds the current one.
    fn rotation(&self, device: &Device, keyed: &BTreeSet<String>) -> Result<Option<acl::KeyChange>> {
        let s = self.state();
        match self.read_key(device, s.epoch) {
            Ok(key) => Ok(Some(s.new_key_change(&key, keyed)?.0)),
            Err(_) => Ok(None),
        }
    }

    pub fn remove_member(&mut self, device: &Device, root: &str, now: u64) -> Result<Entry> {
        let s = self.state().clone();
        let member = s.members.get(root).ok_or_else(|| refused("no such member"))?;
        let cut: BTreeMap<String, u64> = member
            .devices
            .iter()
            .map(|d| Ok((d.clone(), self.store.head(d)?.map(|h| h.0).unwrap_or(0))))
            .collect::<Result<_>>()?;
        let leaving = s.devices.get(&device.id_hex()).is_some_and(|d| d.member == root);
        let mut after = s.clone();
        if let Some(m) = after.members.get_mut(root) {
            m.removed = true;
        }
        for d in &member.devices {
            if let Some(x) = after.devices.get_mut(d) {
                x.cut = Some(0);
            }
        }
        let rotate = if leaving {
            None
        } else {
            self.rotation(device, &after.keyed_devices())?
        };
        self.append(
            device,
            Op::RemoveMember(acl::RemoveMember {
                member: root.to_owned(),
                cut,
                rotate,
            }),
            now,
        )
    }

    pub fn remove_device(&mut self, device: &Device, target: &str, now: u64) -> Result<Entry> {
        let cut = self.store.head(target)?.map(|h| h.0).unwrap_or(0);
        let mut keyed = self.state().keyed_devices();
        keyed.remove(target);
        let rotate = if target == device.id_hex() {
            None
        } else {
            self.rotation(device, &keyed)?
        };
        self.append(
            device,
            Op::RemoveDevice(acl::RemoveDevice {
                device: target.to_owned(),
                cut,
                rotate,
            }),
            now,
        )
    }

    pub fn rotate_key(&mut self, device: &Device, now: u64) -> Result<Entry> {
        let keyed = self.state().keyed_devices();
        let change = self
            .rotation(device, &keyed)?
            .ok_or_else(|| refused("this device does not hold the read key"))?;
        self.append(device, Op::RotateKey(change), now)
    }

    pub fn set_role(&mut self, device: &Device, root: &str, role: Role, now: u64) -> Result<Entry> {
        let s = self.state().clone();
        let m = s.members.get(root).ok_or_else(|| refused("no such member"))?;
        let wraps = if role.reads() && !m.role.reads() {
            let live: BTreeSet<String> = m
                .devices
                .iter()
                .filter(|d| s.devices.get(*d).is_some_and(|x| x.cut.is_none()))
                .cloned()
                .collect();
            s.make_wraps(&self.read_key(device, s.epoch)?.0, s.epoch, &live)?
        } else {
            vec![]
        };
        self.append(
            device,
            Op::SetRole(acl::SetRole {
                member: root.to_owned(),
                role,
                wraps,
            }),
            now,
        )
    }

    pub fn revoke_invite(&mut self, device: &Device, invite: &str, now: u64) -> Result<Entry> {
        self.append(
            device,
            Op::RevokeInvite(acl::RevokeInvite {
                invite: invite.to_owned(),
            }),
            now,
        )
    }

    /// What an admin's daemon does unasked: wrap the key to joins that need no approval, and
    /// append a rotation that a removal left due. Returns the entries it appended.
    pub fn upkeep(&mut self, device: &Device, now: u64) -> Result<Vec<Entry>> {
        let mut out = Vec::new();
        if !self.my_role(device).is_some_and(Role::admin) || self.read_key(device, self.state().epoch).is_err() {
            return Ok(out);
        }
        let auto: Vec<String> = self
            .state()
            .pending_joins
            .iter()
            .filter(|(_, root)| self.state().members.get(*root).is_some_and(|m| !m.pending))
            .map(|(j, _)| j.clone())
            .collect();
        for join in auto {
            out.push(self.accept(device, &join, now)?);
        }
        if self.state().rotation_due {
            out.push(self.rotate_key(device, now)?);
        }
        Ok(out)
    }

    /// Self-monitoring: every device the log lists under our own root must be one we certified.
    /// Returns the unknown ones (and raises an alarm for each).
    ///
    /// A device also vouches for the devices of its own fleet that were already in the log when it
    /// was added (one of them added it), so a fleet's second machine does not raise an alarm
    /// about its first. Anything added under our root later must be one we certified ourselves.
    pub fn self_monitor(&self, me: &str, my_root: &str, certified: &BTreeSet<String>, now: u64) -> Result<Vec<String>> {
        let vouched = self.devices_before(me, my_root);
        let rogue: Vec<String> = self
            .state()
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

    /// Devices under `root` that applied entries introduced up to (and with) the one adding `me`.
    fn devices_before(&self, me: &str, root: &str) -> BTreeSet<String> {
        let applied: BTreeSet<&String> = self.state().applied.iter().collect();
        let mut seen = BTreeSet::new();
        for (hash, e) in self.acl.ordered() {
            if !applied.contains(hash) {
                continue;
            }
            let added: Vec<String> = match e.parsed() {
                Ok(Op::Genesis(g)) => g
                    .devices
                    .iter()
                    .filter(|c| c.root == root)
                    .map(|c| c.device.clone())
                    .collect(),
                Ok(Op::Join(j)) if j.root == root => j.devices.iter().map(|c| c.device.clone()).collect(),
                Ok(Op::AddDevice(a)) if a.cert.root == root => vec![a.cert.device.clone()],
                _ => vec![],
            };
            let found = added.iter().any(|d| d == me);
            seen.extend(added);
            if found {
                return seen;
            }
        }
        BTreeSet::new()
    }

    // -------------------------------------------------------------------------------- records

    /// Write one record to this device's feed.
    pub fn write(&mut self, device: &Device, body: &Body, now: u64) -> Result<(String, Record)> {
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
        let acl_head = s.head.clone();
        let kinds = s.policy().kinds;
        let r = Record::seal(
            device,
            Seal {
                link: &link,
                seq,
                prev: &prev,
                deps,
                acl: &acl_head,
                epoch,
                key: &key.0,
            },
            body,
            &kinds,
        )?;
        let id = r.verify()?;
        let plain = codec::canonical(body)?;
        self.store
            .put_record(&id, &r, store::OWN, Some(&String::from_utf8_lossy(&plain)), None, now)?;
        for b in &body.blobs {
            self.store.put_blob(&b.id, &id, &b.name, b.bytes)?;
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
        if self.store.get(&id)?.is_some() {
            return Ok(Admit::Duplicate);
        }
        if let Err(e) = self.authorised(r) {
            return Ok(Admit::Refused(e.to_string()));
        }
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
        let quota = self.state().policy().rate_per_hour;
        if self.store.count_recent(&r.author, now.saturating_sub(3600))? >= quota {
            return Ok(Admit::Gap {
                author: r.author.clone(),
                have: have_seq,
            });
        }

        // Only now open it, and only to read it here.
        let s = self.state();
        let author_member = s.devices[&r.author].member.clone();
        let my_root = s
            .devices
            .get(&me.id_hex())
            .map(|d| d.member.clone())
            .unwrap_or_default();
        let own_fleet = my_root == author_member;
        let writes = s.members[&author_member].role.writes();
        let kinds = s.policy().kinds;
        let (status, body, reason) = match self.read_key(me, r.epoch) {
            Err(_) => (store::OPAQUE, None, None),
            Ok(key) => match r.open(&key.0, &kinds) {
                Err(e) => {
                    self.store.alarm("withheld", &r.author, &format!("{id}: {e}"), now)?;
                    (store::WITHHELD, None, Some(e.to_string()))
                }
                Ok(b) if b.kind != ACK_KIND && !writes => {
                    let why = "a fleet without write rights sent mail";
                    self.store.alarm("withheld", &r.author, &format!("{id}: {why}"), now)?;
                    (store::WITHHELD, None, Some(why.to_owned()))
                }
                Ok(b) => {
                    let text = String::from_utf8_lossy(&codec::canonical(&b)?).into_owned();
                    let status = if own_fleet || b.kind == ACK_KIND {
                        store::OWN
                    } else {
                        store::ADMITTED
                    };
                    if b.kind == ACK_KIND {
                        self.take_receipts(&my_root, &author_member, &b, now)?;
                    }
                    for blob in &b.blobs {
                        self.store.put_blob(&blob.id, &id, &blob.name, blob.bytes)?;
                    }
                    (status, Some(text), None)
                }
            },
        };
        self.store
            .put_record(&id, r, status, body.as_deref(), reason.as_deref(), now)?;
        for blob in &r.blobs {
            self.store.put_blob(blob, &id, "", 0)?;
        }
        Ok(Admit::Stored {
            id,
            status: status.to_owned(),
        })
    }

    /// The membership half of admission (header only, so a mailbox can apply it too).
    fn authorised(&self, r: &Record) -> Result<()> {
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
        if self.store.frozen(&r.author)? {
            return Err(refused("author is frozen after equivocating"));
        }
        let at = s
            .epoch_at
            .get(&r.acl)
            .ok_or_else(|| refused("record names an ACL head this link does not hold"))?;
        if *at != r.epoch {
            return Err(refused("record epoch does not match its ACL head"));
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
            for r in self.store.range(author, 0, *upto)? {
                self.store.receipt(&r.id()?, fleet, "delivered", now)?;
            }
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

    /// Per author, what the peer lacks given its heads, in seq order.
    pub fn missing_for(&self, theirs: &BTreeMap<String, u64>, limit: usize) -> Result<Vec<Record>> {
        let mut out = Vec::new();
        for (author, (mine, _)) in self.store.heads()? {
            let have = theirs.get(&author).copied().unwrap_or(0);
            if mine > have {
                out.extend(self.store.range(&author, have, mine)?);
                if out.len() >= limit {
                    out.truncate(limit);
                    break;
                }
            }
        }
        Ok(out)
    }

    pub fn heads(&self) -> Result<BTreeMap<String, u64>> {
        Ok(self.store.heads()?.into_iter().map(|(a, (s, _))| (a, s)).collect())
    }

    /// Drop bodies past the link's retention period.
    pub fn retire(&self, now: u64) -> Result<usize> {
        let days = self.state().policy().retention_days;
        self.store.retire_before(now.saturating_sub(days * 24 * 3600))
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
            let fleet = s.members.get(&fleet_root).map(|m| m.label.clone()).unwrap_or_default();
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
                json!({"invite": k, "role": i.role.as_str(), "expires": i.expires, "used": i.used,
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
        Ok(json!({
            "link": s.link_id, "name": s.name, "owner": s.owner, "epoch": s.epoch, "policy": s.policy(),
            "my_device": me, "my_role": self.my_role(device).map(Role::as_str), "rotation_due": s.rotation_due,
            "acl_entries": self.acl.len(), "acl_head": s.head, "members": members, "invites": invites,
            "pending_joins": pending, "alarms": alarms, "quarantine_unpromoted": queued, "sent": sent,
            "dropped_acl_entries": s.dropped.iter().map(|(h, why)| json!({"entry": h, "why": why})).collect::<Vec<_>>(),
            "last_cursor": self.store.last_cursor()?,
        }))
    }
}

#[cfg(test)]
mod tests;
