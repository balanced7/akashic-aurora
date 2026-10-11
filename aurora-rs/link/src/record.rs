//! Records: the signed, sealed, hash-chained unit of a device's feed.
//!
//! The header is readable by anyone who stores the record (a mailbox, a relaying member). It
//! carries no content, but it is not silent: it shows the link, the author device, its seq and
//! signed write time, the ACL chain position and epoch, the deps, the body's padding bucket, and the ids
//! and padded sizes of attached blobs. The body is sealed with the link's read key for `epoch`,
//! using the canonical header as additional data, and padded to a bucket.
//!
//! Blobs are padded too, to a power of two of at least 4 KiB (`blob_ct_len`), so a blob's size
//! on the wire and in the header says only which bucket it fell in. Each `BlobRef` carries
//! `key_hash`, a commitment to its key, so a blob opens to one plaintext only.
//!
//! The signature covers the canonical header, which includes `ct_hash`, the SHA-256 of the
//! ciphertext. That is the RFC's `canonical(header) || ct` with the ciphertext hashed first, and
//! it is deliberate: retention drops `ct` after the link's period, and the header must still
//! verify so the chain still does. (`bridge_seal`'s tombstone signature was the same lesson.)
//!
//! `record_id = sha256(signed bytes)`. Replays are no-ops: a record is stored once, by id.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::acl::{AclPos, BRIDGE_KINDS};
use crate::codec::{self, b64, hex, unb64, unhex};
use crate::crypto::{self, CONTEXT, PAD_BUCKETS};
use crate::error::{Result, refused};
use crate::identity::{Device, MAX_LABEL};

pub const ACK_KIND: &str = "ack";
pub const MAX_DEPS: usize = 16;
/// 2: a record names one ACL chain position (`acl`), not a set of DAG heads.
pub const RECORD_VERSION: u32 = 2;
pub const MAX_BLOBS: usize = 16;
pub const MAX_ADDRESS: usize = 128;

/// Largest attachment, in plaintext bytes. A larger `BlobRef` is refused at write and at read.
pub const MAX_BLOB_BYTES: u64 = 64 << 20;
/// Smallest blob padding bucket: every blob is padded to a power of two of at least this.
pub const MIN_BLOB_BUCKET: u64 = 4096;
/// AEAD overhead on a blob: nonce and tag.
pub const BLOB_OVERHEAD: u64 = (crypto::NONCE_LEN + crypto::TAG_LEN) as u64;
/// Largest blob ciphertext anyone fetches or serves for a record.
pub const MAX_BLOB_CT_BYTES: u64 = blob_ct_len(MAX_BLOB_BYTES);

/// The ciphertext length of a blob of `plain` bytes: padded to its bucket, plus the AEAD overhead.
pub const fn blob_ct_len(plain: u64) -> u64 {
    let b = if plain < MIN_BLOB_BUCKET {
        MIN_BLOB_BUCKET
    } else {
        plain
    };
    b.next_power_of_two() + BLOB_OVERHEAD
}

/// Whether `n` is a ciphertext length `blob_ct_len` can produce, within the cap.
pub fn is_blob_ct_len(n: u64) -> bool {
    n <= MAX_BLOB_CT_BYTES
        && n.checked_sub(BLOB_OVERHEAD)
            .is_some_and(|b| b >= MIN_BLOB_BUCKET && b.is_power_of_two())
}

/// The commitment to a blob key that travels in its `BlobRef`.
pub fn blob_key_hash(key: &[u8]) -> String {
    hex(&crypto::sha256(&[CONTEXT, b"blob-key\0", key]))
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub v: u32,
    pub link: String,
    pub author: String,
    pub seq: u64,
    /// When the author wrote it (its clock, signed). Retention and certificate validity are
    /// judged by this, bounded by our own clock: never more than the allowed skew ahead.
    pub ts: u64,
    pub prev: String,
    pub deps: Vec<String>,
    /// Ids of the blobs the body references: signed and in the clear, so a mailbox that cannot
    /// open the body still knows which blobs travel with the record.
    pub blobs: Vec<String>,
    /// The padded ciphertext length of each blob in `blobs` (`blob_ct_len`), so a mailbox can cap
    /// what it fetches and a fetcher knows the exact size to expect.
    pub blob_sizes: Vec<u64>,
    /// The ACL chain position the writer stood on; `epoch` must be the epoch in force there.
    pub acl: AclPos,
    pub epoch: u64,
    pub size_class: u64,
    pub ct_hash: String,
    /// Absent once retention has dropped the body.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ct: Option<String>,
    pub sig: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BlobRef {
    /// BLAKE3 of the blob's ciphertext: the hash iroh-blobs fetches and verifies by.
    pub id: String,
    pub key: String,
    /// `blob_key_hash(key)`: commits the reference to its key.
    pub key_hash: String,
    pub name: String,
    pub bytes: u64,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Body {
    pub kind: String,
    /// The writing seat: a claim, vouched for by the device signature.
    pub seat: String,
    /// `@fleet/seat`, `@fleet`, or empty for the whole link.
    pub to: String,
    pub content: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reply_to: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub blobs: Vec<BlobRef>,
    /// Advisory; ordering comes from seq and deps.
    pub sent_at: u64,
    /// Receipts (`ack` records only): "I hold everything from author up to seq".
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub acks: BTreeMap<String, u64>,
    /// Receipts (`ack` records only): records a seat has read.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub read: Vec<String>,
}

impl Body {
    /// Shape and kind checks, at write AND at read. `kinds` is the link policy's subset.
    pub fn check(&self, kinds: &[String]) -> Result<()> {
        if self.kind == ACK_KIND {
            if !self.content.is_empty() || !self.blobs.is_empty() || (self.acks.is_empty() && self.read.is_empty()) {
                return Err(refused("an ack carries receipts and nothing else"));
            }
        } else {
            if !BRIDGE_KINDS.contains(&self.kind.as_str()) || !kinds.contains(&self.kind) {
                return Err(refused(format!(
                    "kind {:?} is not on this link's bridge allowlist",
                    self.kind
                )));
            }
            if !self.acks.is_empty() || !self.read.is_empty() {
                return Err(refused("only an ack carries receipts"));
            }
        }
        if self.seat.chars().count() > MAX_LABEL || self.to.chars().count() > MAX_ADDRESS {
            return Err(refused("seat or recipient is too long"));
        }
        if self.seat.chars().chain(self.to.chars()).any(char::is_control) {
            return Err(refused("seat or recipient has control characters"));
        }
        if let Some(r) = &self.reply_to {
            unhex::<32>(r)?;
        }
        if self.blobs.len() > MAX_BLOBS {
            return Err(refused("too many blobs on one record"));
        }
        for b in &self.blobs {
            unhex::<32>(&b.id)?;
            let key = unb64(&b.key)?;
            if key.len() != 32 || b.name.chars().count() > 255 || b.name.chars().any(char::is_control) {
                return Err(refused("blob reference is malformed"));
            }
            if b.key_hash != blob_key_hash(&key) {
                return Err(refused("blob key does not match its commitment"));
            }
            if b.bytes > MAX_BLOB_BYTES {
                return Err(refused(format!("blob is larger than {MAX_BLOB_BYTES} bytes")));
            }
        }
        for author in self.acks.keys() {
            unhex::<32>(author)?;
        }
        for r in &self.read {
            unhex::<32>(r)?;
        }
        Ok(())
    }
}

/// What a writer supplies; the rest of the header is the feed's and the ACL's.
pub struct Seal<'a> {
    pub link: &'a str,
    pub seq: u64,
    /// The write time signed into the header.
    pub ts: u64,
    pub prev: &'a str,
    pub deps: Vec<String>,
    pub acl: &'a AclPos,
    pub epoch: u64,
    pub key: &'a [u8; 32],
}

impl Record {
    fn header_value(&self) -> serde_json::Value {
        json!({
            "v": self.v, "link": self.link, "author": self.author, "seq": self.seq, "ts": self.ts,
            "prev": self.prev, "deps": self.deps, "blobs": self.blobs, "blob_sizes": self.blob_sizes,
            "acl": {"term": self.acl.term, "seq": self.acl.seq, "hash": self.acl.hash}, "epoch": self.epoch, "size_class": self.size_class,
            "ct_hash": self.ct_hash,
        })
    }

    /// Additional data for the body's AEAD: the header without `ct_hash` (which depends on the
    /// ciphertext and so cannot be inside it).
    fn aad(&self) -> Result<Vec<u8>> {
        let mut h = self.header_value();
        h.as_object_mut().expect("object").remove("ct_hash");
        codec::jcs(&h)
    }

    /// The exact bytes the author signed. `record_id` is their SHA-256.
    pub fn signed_bytes(&self) -> Result<Vec<u8>> {
        Ok(crypto::signed_bytes("record", &codec::jcs(&self.header_value())?))
    }

    pub fn id(&self) -> Result<String> {
        Ok(hex(&crypto::sha256(&[&self.signed_bytes()?])))
    }

    /// Write one record: check the body, pad, seal, hash, sign.
    pub fn seal(device: &Device, s: Seal<'_>, body: &Body, kinds: &[String]) -> Result<Self> {
        body.check(kinds)?;
        if s.deps.len() > MAX_DEPS {
            return Err(refused("too many deps"));
        }
        let plain = codec::canonical(body)?;
        let (padded, bucket) = crypto::pad(&plain)?;
        let mut r = Record {
            v: RECORD_VERSION,
            link: s.link.to_owned(),
            author: device.id_hex(),
            seq: s.seq,
            ts: s.ts,
            prev: s.prev.to_owned(),
            deps: s.deps,
            blobs: body.blobs.iter().map(|b| b.id.clone()).collect(),
            blob_sizes: body.blobs.iter().map(|b| blob_ct_len(b.bytes)).collect(),
            acl: s.acl.clone(),
            epoch: s.epoch,
            size_class: bucket as u64,
            ct_hash: String::new(),
            ct: None,
            sig: String::new(),
        };
        let ct = crypto::seal(s.key, &padded, &r.aad()?);
        r.ct_hash = hex(&crypto::sha256(&[&ct]));
        r.ct = Some(b64(&ct));
        let header = codec::jcs(&r.header_value())?;
        r.sig = b64(&crypto::sign(&device.sign, "record", &header));
        Ok(r)
    }

    /// Everything that can be checked without a read key or the ACL: shape, sizes, the hash of
    /// the ciphertext and the author's signature. Returns the record id.
    /// What sending this record costs, in bytes, as the sync budgets count it: its ciphertext and
    /// a fixed allowance for the header.
    pub fn frame_cost(&self) -> usize {
        self.ct.as_ref().map_or(0, String::len) + 1024
    }

    pub fn verify(&self) -> Result<String> {
        if self.v != RECORD_VERSION {
            return Err(refused("unknown record version"));
        }
        unhex::<32>(&self.link)?;
        let author = unhex::<32>(&self.author)?;
        unhex::<32>(&self.acl.hash)?;
        if self.acl.term == 0 || self.acl.term > crate::codec::MAX_SAFE_INT || self.acl.seq > crate::codec::MAX_SAFE_INT
        {
            return Err(refused("a record's ACL position is out of range"));
        }
        unhex::<32>(&self.ct_hash)?;
        if self.seq == 0 || (self.seq == 1) != self.prev.is_empty() {
            return Err(refused("seq starts at 1, and only seq 1 has no prev"));
        }
        if !self.prev.is_empty() {
            unhex::<32>(&self.prev)?;
        }
        if self.deps.len() > MAX_DEPS {
            return Err(refused("too many deps"));
        }
        if self.blobs.len() > MAX_BLOBS {
            return Err(refused("too many blobs"));
        }
        for b in &self.blobs {
            unhex::<32>(b)?;
        }
        if self.blob_sizes.len() != self.blobs.len() || !self.blob_sizes.iter().all(|n| is_blob_ct_len(*n)) {
            return Err(refused("blob sizes do not match the blobs, or are not padding buckets"));
        }
        for d in &self.deps {
            unhex::<32>(d)?;
        }
        if !PAD_BUCKETS.contains(&(self.size_class as usize)) {
            return Err(refused("size class is not a padding bucket"));
        }
        if let Some(ct) = &self.ct {
            let raw = unb64(ct)?;
            if raw.len() != crypto::NONCE_LEN + self.size_class as usize + crypto::TAG_LEN {
                return Err(refused("ciphertext length does not match its size class"));
            }
            if hex(&crypto::sha256(&[&raw])) != self.ct_hash {
                return Err(refused("ciphertext does not match its signed hash"));
            }
        }
        let header = codec::jcs(&self.header_value())?;
        crypto::verify(&author, "record", &header, &unb64(&self.sig)?)?;
        self.id()
    }

    /// Open the body with the read key for this record's epoch. Checks the kind again.
    pub fn open(&self, key: &[u8; 32], kinds: &[String]) -> Result<Body> {
        let ct = unb64(self.ct.as_deref().ok_or_else(|| refused("record body was retired"))?)?;
        let padded = crypto::open(key, &ct, &self.aad()?)?;
        let body: Body = codec::parse(&crypto::unpad(&padded)?, "record body")?;
        body.check(kinds)?;
        if body.blobs.iter().map(|b| &b.id).ne(self.blobs.iter())
            || body
                .blobs
                .iter()
                .map(|b| blob_ct_len(b.bytes))
                .ne(self.blob_sizes.iter().copied())
        {
            return Err(refused("body blobs do not match the signed header"));
        }
        Ok(body)
    }

    /// The same record with its body dropped (retention). The header still verifies.
    pub fn retired(&self) -> Self {
        Self {
            ct: None,
            ..self.clone()
        }
    }
}

// ------------------------------------------------------------------------------------------ blobs

/// Encrypt one attachment under its own random key, zero-padded to its bucket. Returns
/// (reference, ciphertext). An attachment over `MAX_BLOB_BYTES` still seals, but the record that
/// names it is refused at write.
pub fn seal_blob(name: &str, plain: &[u8]) -> (BlobRef, Vec<u8>) {
    let key = crypto::random32();
    let mut padded = plain.to_vec();
    padded.resize((blob_ct_len(plain.len() as u64) - BLOB_OVERHEAD) as usize, 0);
    let ct = crypto::seal(&key, &padded, b"aurora-link/v1/blob");
    let r = BlobRef {
        id: hex(&crypto::blake3(&ct)),
        key: b64(&key),
        key_hash: blob_key_hash(&key),
        name: name.to_owned(),
        bytes: plain.len() as u64,
    };
    (r, ct)
}

/// Verify a blob's ciphertext against its id, size and key commitment, then open and unpad it.
pub fn open_blob(r: &BlobRef, ct: &[u8]) -> Result<Vec<u8>> {
    if hex(&crypto::blake3(ct)) != r.id {
        return Err(refused("blob does not match its content address"));
    }
    if r.bytes > MAX_BLOB_BYTES || ct.len() as u64 != blob_ct_len(r.bytes) {
        return Err(refused("blob length does not match its reference"));
    }
    let key: [u8; 32] = unb64(&r.key)?
        .try_into()
        .map_err(|_| refused("blob key has the wrong length"))?;
    if r.key_hash != blob_key_hash(&key) {
        return Err(refused("blob key does not match its commitment"));
    }
    let mut plain = crypto::open(&key, ct, b"aurora-link/v1/blob")?;
    if plain[r.bytes as usize..].iter().any(|b| *b != 0) {
        return Err(refused("blob padding is not zero"));
    }
    plain.truncate(r.bytes as usize);
    Ok(plain)
}

// ------------------------------------------------------------------------------------ head adverts

/// A signed "my feed has reached seq N" for live sync over gossip. A hint, never an authority:
/// it can make a member sync sooner, never conclude that nothing is new.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HeadAdvert {
    pub v: u32,
    pub link: String,
    pub author: String,
    pub seq: u64,
    pub id: String,
    pub ts: u64,
    pub sig: String,
}

impl HeadAdvert {
    fn body(&self) -> Result<Vec<u8>> {
        codec::jcs(
            &json!({"v": self.v, "link": self.link, "author": self.author, "seq": self.seq, "id": self.id, "ts": self.ts}),
        )
    }

    pub fn sign(device: &Device, link: &str, seq: u64, id: &str, ts: u64) -> Result<Self> {
        let mut a = Self {
            v: 1,
            link: link.into(),
            author: device.id_hex(),
            seq,
            id: id.into(),
            ts,
            sig: String::new(),
        };
        a.sig = b64(&crypto::sign(&device.sign, "head", &a.body()?));
        Ok(a)
    }

    pub fn verify(&self) -> Result<()> {
        if self.v != 1 {
            return Err(refused("unknown advert version"));
        }
        unhex::<32>(&self.link)?;
        unhex::<32>(&self.id)?;
        crypto::verify(&unhex::<32>(&self.author)?, "head", &self.body()?, &unb64(&self.sig)?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::identity::{new_phrase, root_from_phrase};

    fn kinds() -> Vec<String> {
        BRIDGE_KINDS.iter().map(|k| (*k).to_owned()).collect()
    }

    fn device() -> Device {
        Device::create(&root_from_phrase(&new_phrase()).unwrap(), "d", false, 0).unwrap()
    }

    fn body(kind: &str) -> Body {
        Body {
            kind: kind.into(),
            seat: "claude".into(),
            to: "@partner/codex".into(),
            content: "hi".into(),
            sent_at: 5,
            ..Body::default()
        }
    }

    fn write(d: &Device, key: &[u8; 32], b: &Body) -> Result<Record> {
        let link = "11".repeat(32);
        let acl = AclPos {
            term: 1,
            seq: 0,
            hash: "22".repeat(32),
        };
        Record::seal(
            d,
            Seal {
                link: &link,
                seq: 1,
                ts: 5,
                prev: "",
                deps: vec![],
                acl: &acl,
                epoch: 0,
                key,
            },
            b,
            &kinds(),
        )
    }

    #[test]
    fn a_record_round_trips_and_hides_its_length() {
        let d = device();
        let key = crypto::random32();
        let r = write(&d, &key, &body("question")).unwrap();
        let id = r.verify().unwrap();
        assert_eq!(id, r.id().unwrap());
        assert_eq!(r.size_class, 4096);
        assert_eq!(r.open(&key, &kinds()).unwrap(), body("question"));
        let other = crypto::random32();
        assert!(r.open(&other, &kinds()).is_err());
    }

    #[test]
    fn control_kinds_are_refused_at_write_and_at_read() {
        let d = device();
        let key = crypto::random32();
        for kind in ["halt", "nudge", "steer", ""] {
            assert!(write(&d, &key, &body(kind)).is_err(), "{kind} written");
        }
        let r = write(&d, &key, &body("chat")).unwrap();
        let narrow = vec!["note".to_owned()];
        assert!(
            r.open(&key, &narrow).is_err(),
            "a kind outside the link policy is refused at read"
        );
    }

    #[test]
    fn any_tampered_byte_is_refused() {
        let d = device();
        let r = write(&d, &crypto::random32(), &body("chat")).unwrap();
        let mut variants = vec![];
        let mut x = r.clone();
        x.seq = 2;
        variants.push(x);
        let mut x = r.clone();
        x.epoch = 1;
        variants.push(x);
        let mut x = r.clone();
        x.deps.push("33".repeat(32));
        variants.push(x);
        let mut x = r.clone();
        let mut ct = unb64(x.ct.as_ref().unwrap()).unwrap();
        ct[40] ^= 1;
        x.ct = Some(b64(&ct));
        variants.push(x);
        let mut x = r.clone();
        x.ct = Some(format!(" {}", r.ct.as_ref().unwrap()));
        variants.push(x);
        for v in variants {
            assert!(v.verify().is_err(), "{v:?}");
        }
    }

    #[test]
    fn a_retired_record_still_verifies() {
        let d = device();
        let r = write(&d, &crypto::random32(), &body("chat")).unwrap();
        let t = r.retired();
        assert_eq!(t.verify().unwrap(), r.id().unwrap());
        assert!(t.open(&crypto::random32(), &kinds()).is_err());
    }

    #[test]
    fn unknown_fields_are_refused() {
        let d = device();
        let r = write(&d, &crypto::random32(), &body("chat")).unwrap();
        let mut v = serde_json::to_value(&r).unwrap();
        v["extra"] = json!(1);
        assert!(codec::parse::<Record>(v.to_string().as_bytes(), "record").is_err());
    }

    #[test]
    fn acks_carry_receipts_only() {
        let d = device();
        let key = crypto::random32();
        let mut ack = Body {
            kind: ACK_KIND.into(),
            sent_at: 1,
            ..Body::default()
        };
        assert!(write(&d, &key, &ack).is_err());
        ack.acks.insert("44".repeat(32), 3);
        write(&d, &key, &ack).unwrap();
        let mut bad = body("chat");
        bad.read.push("44".repeat(32));
        assert!(write(&d, &key, &bad).is_err());
    }

    #[test]
    fn blobs_are_content_addressed_and_verified() {
        let (r, ct) = seal_blob("playbook.md", b"# steps");
        assert_eq!(open_blob(&r, &ct).unwrap(), b"# steps");
        let mut bad = ct.clone();
        bad[30] ^= 1;
        assert!(open_blob(&r, &bad).is_err());
    }

    #[test]
    fn blobs_are_padded_to_buckets() {
        for (n, want) in [(0, 4096), (5, 4096), (4096, 4096), (4097, 8192), (100_000, 131_072)] {
            let plain = vec![9u8; n];
            let (r, ct) = seal_blob("f", &plain);
            assert_eq!(ct.len() as u64, want + BLOB_OVERHEAD, "{n}");
            assert_eq!(ct.len() as u64, blob_ct_len(n as u64));
            assert!(is_blob_ct_len(ct.len() as u64));
            assert_eq!(open_blob(&r, &ct).unwrap(), plain);
        }
        assert!(!is_blob_ct_len(5000) && !is_blob_ct_len(MAX_BLOB_CT_BYTES * 2 - BLOB_OVERHEAD));
        // A reference that understates its size does not open.
        let (mut r, ct) = seal_blob("f", b"abc");
        r.bytes = 2;
        assert!(open_blob(&r, &ct).is_err());
    }

    #[test]
    fn blob_references_commit_to_their_key() {
        let (r, ct) = seal_blob("f", b"abc");
        assert_eq!(r.key_hash, blob_key_hash(&unb64(&r.key).unwrap()));
        let mut other = r.clone();
        other.key_hash = blob_key_hash(&crypto::random32());
        assert!(open_blob(&other, &ct).is_err());
        let d = device();
        let key = crypto::random32();
        let mut b = body("note");
        b.blobs.push(other);
        assert!(
            write(&d, &key, &b).is_err(),
            "a body naming an uncommitted key is refused"
        );
        b.blobs[0] = r.clone();
        let rec = write(&d, &key, &b).unwrap();
        assert_eq!(rec.blob_sizes, vec![blob_ct_len(3)]);
        assert_eq!(rec.open(&key, &kinds()).unwrap().blobs, vec![r.clone()]);
        // Oversized references are refused at write.
        let mut big = r;
        big.bytes = MAX_BLOB_BYTES + 1;
        b.blobs[0] = big;
        assert!(write(&d, &key, &b).is_err());
    }

    #[test]
    fn blob_sizes_are_signed_and_bucketed() {
        let d = device();
        let key = crypto::random32();
        let (br, _) = seal_blob("f", b"abc");
        let mut b = body("note");
        b.blobs.push(br);
        let r = write(&d, &key, &b).unwrap();
        r.verify().unwrap();
        let mut x = r.clone();
        x.blob_sizes = vec![5000];
        assert!(x.verify().is_err());
        let mut x = r.clone();
        x.blob_sizes = vec![];
        assert!(x.verify().is_err());
        let mut x = r.clone();
        x.ts += 1;
        assert!(x.verify().is_err(), "the write time is signed");
    }

    #[test]
    fn head_adverts_verify() {
        let d = device();
        let a = HeadAdvert::sign(&d, &"11".repeat(32), 4, &"22".repeat(32), 9).unwrap();
        a.verify().unwrap();
        let mut b = a.clone();
        b.seq = 5;
        assert!(b.verify().is_err());
    }
}
