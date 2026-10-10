//! The primitives, each used one way only.
//!
//! - Signatures: Ed25519, verified with `verify_strict` (no malleable signatures, no small-order
//!   keys). Every signature is over `CONTEXT || purpose || 0x00 || message`, so a signature made
//!   for one purpose (a certificate) can never be replayed as another (an ACL entry).
//! - Content: XChaCha20-Poly1305 with a random 24-byte nonce carried in front of the ciphertext.
//! - Key wrapping: HPKE (RFC 9180) base mode. Suite 1 is X25519 / HKDF-SHA256 / ChaCha20-Poly1305
//!   and every device has it. Suite 2 is for devices that also advertise an X-Wing key: suite 1's
//!   output sealed again to X-Wing (ML-KEM-768 + X25519), so it is additive. Breaking it needs
//!   both X25519 and X-Wing broken, and a bug in the young, unaudited X-Wing code alone cannot
//!   expose a key.
//! - Hashes: SHA-256 for ids that are signed or compared across fleets, BLAKE3 for blob content
//!   (the hash iroh-blobs addresses and verifies by).

use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use hpke::aead::ChaCha20Poly1305 as HpkeChaCha;
use hpke::kdf::HkdfSha256;
use hpke::kem::{X25519HkdfSha256, XWing};
use hpke::{Deserializable, Kem as _, OpModeR, OpModeS, Serializable};
use sha2::{Digest, Sha256};
use zeroize::{Zeroize, ZeroizeOnDrop};

use crate::error::{Result, refused};

/// Domain separation for every signature and HPKE `info` string in the protocol.
pub const CONTEXT: &[u8] = b"aurora-link/v1/";

pub const NONCE_LEN: usize = 24;
pub const TAG_LEN: usize = 16;

/// Padding buckets for record bodies: `bridge_seal`'s, so a body above 256 KiB becomes a blob
/// and no frame ever exceeds the transport limit.
pub const PAD_BUCKETS: [usize; 4] = [4096, 16384, 65536, 262144];

/// A 32-byte secret that is wiped on drop.
#[derive(Clone, Zeroize, ZeroizeOnDrop, PartialEq, Eq)]
pub struct Secret32(pub [u8; 32]);

impl std::fmt::Debug for Secret32 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Secret32(..)")
    }
}

impl Secret32 {
    pub fn random() -> Self {
        Self(random32())
    }
}

pub fn random32() -> [u8; 32] {
    let mut out = [0u8; 32];
    getrandom::fill(&mut out).expect("the OS random source failed");
    out
}

pub fn random_bytes(n: usize) -> Vec<u8> {
    let mut out = vec![0u8; n];
    getrandom::fill(&mut out).expect("the OS random source failed");
    out
}

pub fn sha256(parts: &[&[u8]]) -> [u8; 32] {
    let mut h = Sha256::new();
    for p in parts {
        h.update(p);
    }
    h.finalize().into()
}

pub fn blake3(data: &[u8]) -> [u8; 32] {
    *blake3::hash(data).as_bytes()
}

fn framed(purpose: &str, msg: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(CONTEXT.len() + purpose.len() + 1 + msg.len());
    out.extend_from_slice(CONTEXT);
    out.extend_from_slice(purpose.as_bytes());
    out.push(0);
    out.extend_from_slice(msg);
    out
}

/// The exact bytes a signature for `purpose` covers. Also the preimage of record ids.
pub fn signed_bytes(purpose: &str, msg: &[u8]) -> Vec<u8> {
    framed(purpose, msg)
}

pub fn sign(key: &SigningKey, purpose: &str, msg: &[u8]) -> [u8; 64] {
    key.sign(&framed(purpose, msg)).to_bytes()
}

pub fn verify(public: &[u8; 32], purpose: &str, msg: &[u8], sig: &[u8]) -> Result<()> {
    let key = VerifyingKey::from_bytes(public).map_err(|_| refused("not a valid Ed25519 public key"))?;
    let sig: [u8; 64] = sig.try_into().map_err(|_| refused("signature has the wrong length"))?;
    key.verify_strict(&framed(purpose, msg), &Signature::from_bytes(&sig))
        .map_err(|_| refused(format!("{purpose} signature does not verify")))
}

pub fn signing_key(seed: &[u8; 32]) -> SigningKey {
    SigningKey::from_bytes(seed)
}

pub fn public_of(key: &SigningKey) -> [u8; 32] {
    key.verifying_key().to_bytes()
}

// ------------------------------------------------------------------------------ content (AEAD)

/// XChaCha20-Poly1305 with a fresh random nonce. Output: nonce || ciphertext || tag.
pub fn seal(key: &[u8; 32], plain: &[u8], aad: &[u8]) -> Vec<u8> {
    let cipher = XChaCha20Poly1305::new(key.into());
    let nonce_bytes = random_bytes(NONCE_LEN);
    let nonce = XNonce::try_from(&nonce_bytes[..]).expect("24-byte nonce");
    let ct = cipher
        .encrypt(&nonce, Payload { msg: plain, aad })
        .expect("XChaCha20-Poly1305 cannot fail to seal");
    let mut out = nonce_bytes;
    out.extend_from_slice(&ct);
    out
}

pub fn open(key: &[u8; 32], sealed: &[u8], aad: &[u8]) -> Result<Vec<u8>> {
    if sealed.len() < NONCE_LEN + TAG_LEN {
        return Err(refused("ciphertext is too short"));
    }
    let cipher = XChaCha20Poly1305::new(key.into());
    let nonce = XNonce::try_from(&sealed[..NONCE_LEN]).map_err(|_| refused("bad nonce"))?;
    cipher
        .decrypt(
            &nonce,
            Payload {
                msg: &sealed[NONCE_LEN..],
                aad,
            },
        )
        .map_err(|_| refused("ciphertext does not open"))
}

/// Length-prefix and pad to the smallest bucket that fits.
pub fn pad(plain: &[u8]) -> Result<(Vec<u8>, usize)> {
    let need = plain.len() + 4;
    let bucket = PAD_BUCKETS.iter().copied().find(|b| need <= *b).ok_or_else(|| {
        refused(format!(
            "body of {} bytes exceeds the largest bucket ({}); send it as a blob",
            plain.len(),
            PAD_BUCKETS[PAD_BUCKETS.len() - 1]
        ))
    })?;
    let mut out = Vec::with_capacity(bucket);
    out.extend_from_slice(&(plain.len() as u32).to_be_bytes());
    out.extend_from_slice(plain);
    out.resize(bucket, 0);
    Ok((out, bucket))
}

pub fn unpad(padded: &[u8]) -> Result<Vec<u8>> {
    if padded.len() < 4 {
        return Err(refused("padded body is too short to carry its length"));
    }
    let n = u32::from_be_bytes(padded[..4].try_into().expect("4 bytes")) as usize;
    if n > padded.len() - 4 {
        return Err(refused("padded body declares a length past its own end"));
    }
    if padded[4 + n..].iter().any(|b| *b != 0) {
        return Err(refused("padding is not zero"));
    }
    Ok(padded[4..4 + n].to_vec())
}

// ------------------------------------------------------------------------------ key wrapping

pub const SUITE_X25519: u8 = 1;
pub const SUITE_X25519_XWING: u8 = 2;

/// A device's key-agreement keys. X25519 is mandatory; X-Wing is additive.
#[derive(Clone, Zeroize, ZeroizeOnDrop)]
pub struct KemSecrets {
    pub x25519: [u8; 32],
    pub xwing: Option<[u8; 32]>,
}

impl KemSecrets {
    pub fn generate(with_xwing: bool) -> Self {
        Self {
            x25519: random32(),
            xwing: with_xwing.then(random32),
        }
    }

    pub fn x25519_public(&self) -> [u8; 32] {
        let sk = <X25519HkdfSha256 as hpke::Kem>::PrivateKey::from_bytes(&self.x25519).expect("32-byte X25519 key");
        let pk = X25519HkdfSha256::sk_to_pk(&sk).to_bytes();
        pk.as_slice().try_into().expect("32-byte X25519 public key")
    }

    pub fn xwing_public(&self) -> Option<Vec<u8>> {
        self.xwing.map(|seed| {
            let sk = <XWing as hpke::Kem>::PrivateKey::from_bytes(&seed).expect("32-byte X-Wing seed");
            XWing::sk_to_pk(&sk).to_bytes().to_vec()
        })
    }
}

/// The public half of a device's key-agreement keys, as listed in its certificate.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KemPublics {
    pub x25519: [u8; 32],
    pub xwing: Option<Vec<u8>>,
}

fn wrap_info(info: &[u8]) -> Vec<u8> {
    framed("wrap", info)
}

/// Seal a 32-byte key to one device. Returns (suite, encapsulated key(s), ciphertext).
pub fn wrap(key: &[u8; 32], to: &KemPublics, info: &[u8]) -> Result<(u8, Vec<u8>, Vec<u8>)> {
    let info = wrap_info(info);
    let x_pk = <X25519HkdfSha256 as hpke::Kem>::PublicKey::from_bytes(&to.x25519)
        .map_err(|_| refused("X25519 public key is invalid"))?;
    let (enc1, ct1) =
        hpke::single_shot_seal::<HpkeChaCha, HkdfSha256, X25519HkdfSha256>(&OpModeS::Base, &x_pk, &info, key, b"")
            .map_err(|_| refused("HPKE seal failed"))?;
    let enc1 = enc1.to_bytes().to_vec();
    let Some(xw) = &to.xwing else {
        return Ok((SUITE_X25519, enc1, ct1));
    };
    let xw_pk = <XWing as hpke::Kem>::PublicKey::from_bytes(xw).map_err(|_| refused("X-Wing public key is invalid"))?;
    let (enc2, ct2) =
        hpke::single_shot_seal::<HpkeChaCha, HkdfSha256, XWing>(&OpModeS::Base, &xw_pk, &info, &ct1, &enc1)
            .map_err(|_| refused("HPKE X-Wing seal failed"))?;
    let mut enc = enc1;
    enc.extend_from_slice(&enc2.to_bytes());
    Ok((SUITE_X25519_XWING, enc, ct2))
}

pub fn unwrap(suite: u8, enc: &[u8], ct: &[u8], me: &KemSecrets, info: &[u8]) -> Result<Secret32> {
    let info = wrap_info(info);
    let x_sk = <X25519HkdfSha256 as hpke::Kem>::PrivateKey::from_bytes(&me.x25519)
        .map_err(|_| refused("own X25519 key is unusable"))?;
    let (enc1, inner_ct) = match suite {
        SUITE_X25519 => (enc, ct.to_vec()),
        SUITE_X25519_XWING => {
            let seed = me
                .xwing
                .ok_or_else(|| refused("wrapped with X-Wing, but this device has no X-Wing key"))?;
            if enc.len() != 32 + 1120 {
                return Err(refused("X-Wing wrap has the wrong encapsulation length"));
            }
            let (enc1, enc2) = enc.split_at(32);
            let xw_sk = <XWing as hpke::Kem>::PrivateKey::from_bytes(&seed).map_err(|_| refused("bad X-Wing key"))?;
            let enc2 = <XWing as hpke::Kem>::EncappedKey::from_bytes(enc2).map_err(|_| refused("bad X-Wing enc"))?;
            let inner =
                hpke::single_shot_open::<HpkeChaCha, HkdfSha256, XWing>(&OpModeR::Base, &xw_sk, &enc2, &info, ct, enc1)
                    .map_err(|_| refused("X-Wing wrap does not open"))?;
            (enc1, inner)
        }
        other => return Err(refused(format!("unknown wrap suite {other}"))),
    };
    let enc1 = <X25519HkdfSha256 as hpke::Kem>::EncappedKey::from_bytes(enc1).map_err(|_| refused("bad X25519 enc"))?;
    let mut plain = hpke::single_shot_open::<HpkeChaCha, HkdfSha256, X25519HkdfSha256>(
        &OpModeR::Base,
        &x_sk,
        &enc1,
        &info,
        &inner_ct,
        b"",
    )
    .map_err(|_| refused("wrap does not open"))?;
    let out: [u8; 32] = plain
        .as_slice()
        .try_into()
        .map_err(|_| refused("wrapped key has the wrong length"))?;
    plain.zeroize();
    Ok(Secret32(out))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signatures_are_bound_to_their_purpose() {
        let key = signing_key(&[7u8; 32]);
        let sig = sign(&key, "cert", b"hello");
        assert!(verify(&public_of(&key), "cert", b"hello", &sig).is_ok());
        assert!(verify(&public_of(&key), "acl", b"hello", &sig).is_err());
        assert!(verify(&public_of(&key), "cert", b"hellp", &sig).is_err());
    }

    #[test]
    fn aead_round_trips_and_binds_its_aad() {
        let key = random32();
        let sealed = seal(&key, b"body", b"header");
        assert_eq!(open(&key, &sealed, b"header").unwrap(), b"body");
        assert!(open(&key, &sealed, b"headex").is_err());
        let mut tampered = sealed.clone();
        *tampered.last_mut().unwrap() ^= 1;
        assert!(open(&key, &tampered, b"header").is_err());
    }

    #[test]
    fn padding_hides_length_and_refuses_junk() {
        let (p, bucket) = pad(b"abc").unwrap();
        assert_eq!((p.len(), bucket), (4096, 4096));
        assert_eq!(unpad(&p).unwrap(), b"abc");
        let mut junk = p.clone();
        junk[100] = 1;
        assert!(unpad(&junk).is_err());
        assert!(pad(&vec![0u8; 262144]).is_err());
    }

    #[test]
    fn wrap_round_trips_on_both_suites() {
        for with_xwing in [false, true] {
            let me = KemSecrets::generate(with_xwing);
            let publics = KemPublics {
                x25519: me.x25519_public(),
                xwing: me.xwing_public(),
            };
            let key = random32();
            let (suite, enc, ct) = wrap(&key, &publics, b"link|epoch").unwrap();
            assert_eq!(suite, if with_xwing { SUITE_X25519_XWING } else { SUITE_X25519 });
            assert_eq!(unwrap(suite, &enc, &ct, &me, b"link|epoch").unwrap().0, key);
            assert!(unwrap(suite, &enc, &ct, &me, b"link|epocH").is_err());
            let other = KemSecrets::generate(with_xwing);
            assert!(unwrap(suite, &enc, &ct, &other, b"link|epoch").is_err());
        }
    }
}
