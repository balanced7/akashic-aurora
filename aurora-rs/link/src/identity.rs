//! Identity: a fleet root from a recovery phrase, device keys certified by it, and the safety
//! number two fleets compare once.
//!
//! - **Fleet root (Ed25519).** BIP39 24-word phrase -> seed -> SLIP-10 `m/44'/7743'/0'`. It signs
//!   device certificates and nothing else, so it can stay offline between renewals.
//! - **Device key (Ed25519).** One per install, random. It is the iroh node id, and it signs ACL
//!   entries and records.
//! - **Device KEM keys.** X25519 always, X-Wing optionally; random, never converted from Ed25519.
//! - **Certificate.** `{device, root, label, x25519, xwing?, not_before, not_after}` signed by the
//!   root, valid for at most 90 days, and signed by the device key itself over the same body
//!   (`pop`, purpose `cert-pop`): proof that whoever holds the device key agreed to be certified
//!   under that root with those KEM keys. Without it any root could certify another fleet's device
//!   id and squat it in a link (review finding R4-4).

use std::collections::BTreeMap;

use ed25519_dalek::SigningKey;
use hmac::{Hmac, KeyInit, Mac};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha512};
use unicode_normalization::UnicodeNormalization;
use zeroize::{Zeroize, Zeroizing};

use crate::codec::{self, b64, hex, unb64, unhex};
use crate::crypto::{self, KemPublics, KemSecrets, Secret32};
use crate::error::{LinkError, Result, refused};

/// Aurora's own SLIP-44-style coin number. Not a registered coin; it only keeps our path apart.
pub const AURORA_COIN: u32 = 7743;
pub const CERT_MAX_LIFETIME_S: u64 = 90 * 24 * 3600;
/// Renew when less than this much lifetime is left.
pub const CERT_RENEW_WITHIN_S: u64 = 30 * 24 * 3600;
pub const MAX_LABEL: usize = 64;

// ------------------------------------------------------------------------------------- SLIP-10

const HARDENED: u32 = 0x8000_0000;

/// SLIP-10 for Ed25519 (hardened derivation only, as the spec allows). Owned rather than taken
/// from a crate: it is forty lines, and the spec's test vectors pin it below. Every intermediate
/// (HMAC output, key, chain code) is wiped; the results wipe themselves on drop.
pub fn slip10_ed25519(seed: &[u8], path: &[u32]) -> (Zeroizing<[u8; 32]>, Zeroizing<[u8; 32]>) {
    let mut mac = Hmac::<Sha512>::new_from_slice(b"ed25519 seed").expect("HMAC takes any key length");
    mac.update(seed);
    let mut i = mac.finalize().into_bytes();
    let (mut key, mut chain) = split64(&i);
    i.as_mut_slice().zeroize();
    for index in path {
        let mut mac = Hmac::<Sha512>::new_from_slice(&chain[..]).expect("HMAC takes any key length");
        mac.update(&[0u8]);
        mac.update(&key[..]);
        mac.update(&(index | HARDENED).to_be_bytes());
        let mut i = mac.finalize().into_bytes();
        (key, chain) = split64(&i);
        i.as_mut_slice().zeroize();
    }
    (key, chain)
}

fn split64(i: &[u8]) -> (Zeroizing<[u8; 32]>, Zeroizing<[u8; 32]>) {
    let mut key = Zeroizing::new([0u8; 32]);
    let mut chain = Zeroizing::new([0u8; 32]);
    key.copy_from_slice(&i[..32]);
    chain.copy_from_slice(&i[32..64]);
    (key, chain)
}

/// A fresh 24-word recovery phrase.
pub fn new_phrase() -> String {
    let entropy = crypto::random32();
    bip39::Mnemonic::from_entropy(&entropy)
        .expect("32 bytes is valid BIP39 entropy")
        .to_string()
}

/// The fleet root key a recovery phrase derives. The phrase is checked (words and checksum).
pub fn root_from_phrase(phrase: &str) -> Result<SigningKey> {
    let normalized = Zeroizing::new(phrase.split_whitespace().collect::<Vec<_>>().join(" ").to_lowercase());
    let mnemonic = bip39::Mnemonic::parse_normalized(&normalized)
        .map_err(|e| refused(format!("recovery phrase is not valid BIP39: {e}")))?;
    if mnemonic.word_count() != 24 {
        return Err(refused("the recovery phrase must have 24 words"));
    }
    let seed = Zeroizing::new(mnemonic.to_seed_normalized(""));
    let (key, _chain) = slip10_ed25519(&seed[..], &[44, AURORA_COIN, 0]);
    Ok(crypto::signing_key(&key))
}

// ----------------------------------------------------------------------------------- certificate

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceCert {
    pub v: u32,
    pub device: String,
    pub root: String,
    pub label: String,
    pub x25519: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub xwing: Option<String>,
    pub not_before: u64,
    pub not_after: u64,
    /// The root's signature over the body (purpose `cert`).
    pub sig: String,
    /// The device key's own signature over the same body (purpose `cert-pop`): proof of
    /// possession of the device key.
    pub pop: String,
}

#[derive(Serialize)]
struct CertBody<'a> {
    v: u32,
    device: &'a str,
    root: &'a str,
    label: &'a str,
    x25519: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    xwing: &'a Option<String>,
    not_before: u64,
    not_after: u64,
}

impl DeviceCert {
    fn body_bytes(&self) -> Result<Vec<u8>> {
        codec::canonical(&CertBody {
            v: self.v,
            device: &self.device,
            root: &self.root,
            label: &self.label,
            x25519: &self.x25519,
            xwing: &self.xwing,
            not_before: self.not_before,
            not_after: self.not_after,
        })
    }

    /// Certify `device` (its signing key: the certificate carries its proof of possession) under
    /// `root`.
    pub fn issue(
        root: &SigningKey,
        device: &SigningKey,
        kem: &KemPublics,
        label: &str,
        not_before: u64,
        lifetime_s: u64,
    ) -> Result<Self> {
        if label.chars().count() > MAX_LABEL || label.chars().any(char::is_control) {
            return Err(refused("device label is too long or has control characters"));
        }
        let mut cert = DeviceCert {
            v: 1,
            device: hex(&crypto::public_of(device)),
            root: hex(&crypto::public_of(root)),
            label: label.to_owned(),
            x25519: hex(&kem.x25519),
            xwing: kem.xwing.as_ref().map(|k| b64(k)),
            not_before,
            not_after: not_before + lifetime_s.min(CERT_MAX_LIFETIME_S),
            sig: String::new(),
            pop: String::new(),
        };
        let body = cert.body_bytes()?;
        cert.sig = b64(&crypto::sign(root, "cert", &body));
        cert.pop = b64(&crypto::sign(device, "cert-pop", &body));
        Ok(cert)
    }

    /// Both signatures (the root's, and the device's proof of possession), shape and lifetime.
    /// Not the clock: callers decide which time to check against.
    pub fn verify(&self) -> Result<()> {
        if self.v != 1 {
            return Err(refused("unknown certificate version"));
        }
        let root = unhex::<32>(&self.root)?;
        let device = unhex::<32>(&self.device)?;
        unhex::<32>(&self.x25519)?;
        if let Some(xw) = &self.xwing
            && unb64(xw)?.len() != 1216
        {
            return Err(refused("X-Wing public key has the wrong length"));
        }
        if self.label.chars().count() > MAX_LABEL || self.label.chars().any(char::is_control) {
            return Err(refused("device label is too long or has control characters"));
        }
        if self.not_after <= self.not_before || self.not_after - self.not_before > CERT_MAX_LIFETIME_S {
            return Err(refused("certificate lifetime is empty or longer than 90 days"));
        }
        let body = self.body_bytes()?;
        crypto::verify(&root, "cert", &body, &unb64(&self.sig)?)?;
        crypto::verify(&device, "cert-pop", &body, &unb64(&self.pop)?)
            .map_err(|_| refused("the certificate carries no proof of possession of its device key"))
    }

    pub fn valid_at(&self, t: u64) -> bool {
        self.not_before <= t && t < self.not_after
    }

    pub fn device_bytes(&self) -> Result<[u8; 32]> {
        unhex::<32>(&self.device)
    }

    pub fn kem(&self) -> Result<KemPublics> {
        Ok(KemPublics {
            x25519: unhex::<32>(&self.x25519)?,
            xwing: self.xwing.as_deref().map(unb64).transpose()?,
        })
    }

    /// The same device and keys, possibly a different validity window (a renewal).
    pub fn same_keys(&self, other: &DeviceCert) -> bool {
        self.device == other.device
            && self.root == other.root
            && self.x25519 == other.x25519
            && self.xwing == other.xwing
    }
}

// ------------------------------------------------------------------------------------ the device

/// One install's secrets. Serialised to `<secrets>/link/device.json` (mode 0600) by the daemon.
pub struct Device {
    pub sign: SigningKey,
    pub kem: KemSecrets,
    pub cert: DeviceCert,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct DeviceFile {
    v: u32,
    sign: String,
    x25519: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    xwing: Option<String>,
    cert: DeviceCert,
}

impl Device {
    /// A new device certified by `root`.
    pub fn create(root: &SigningKey, label: &str, with_xwing: bool, now: u64) -> Result<Self> {
        let seed = Secret32::random();
        let sign = crypto::signing_key(&seed.0);
        let kem = KemSecrets::generate(with_xwing);
        let publics = KemPublics {
            x25519: kem.x25519_public(),
            xwing: kem.xwing_public(),
        };
        let cert = DeviceCert::issue(root, &sign, &publics, label, now, CERT_MAX_LIFETIME_S)?;
        Ok(Self { sign, kem, cert })
    }

    pub fn id(&self) -> [u8; 32] {
        crypto::public_of(&self.sign)
    }

    pub fn id_hex(&self) -> String {
        hex(&self.id())
    }

    pub fn root_hex(&self) -> &str {
        &self.cert.root
    }

    /// Re-certify the same keys for another 90 days.
    pub fn renew(&mut self, root: &SigningKey, now: u64) -> Result<()> {
        if hex(&crypto::public_of(root)) != self.cert.root {
            return Err(refused("that root did not certify this device"));
        }
        let publics = self.cert.kem()?;
        self.cert = DeviceCert::issue(root, &self.sign, &publics, &self.cert.label, now, CERT_MAX_LIFETIME_S)?;
        Ok(())
    }

    pub fn needs_renewal(&self, now: u64) -> bool {
        self.cert.not_after.saturating_sub(now) < CERT_RENEW_WITHIN_S
    }

    /// The device file. It holds every secret of this device, so it wipes itself on drop; the
    /// encoded strings it was built from are wiped as soon as it is written.
    pub fn to_json(&self) -> Result<Zeroizing<Vec<u8>>> {
        let sign = Zeroizing::new(self.sign.to_bytes());
        let mut file = DeviceFile {
            v: 1,
            sign: b64(&sign[..]),
            x25519: b64(&self.kem.x25519),
            xwing: self.kem.xwing.as_ref().map(|k| b64(k)),
            cert: self.cert.clone(),
        };
        // Sized up front so the buffer never reallocates (a reallocation leaves a copy behind).
        let mut out = Zeroizing::new(Vec::with_capacity(16 * 1024));
        let written = serde_json::to_writer_pretty(&mut *out, &file);
        file.wipe();
        written.map_err(|e| LinkError::Unavailable(e.to_string()))?;
        Ok(out)
    }

    pub fn from_json(raw: &[u8]) -> Result<Self> {
        let mut file: DeviceFile = codec::parse(raw, "device file")?;
        let keys = Self::keys_of(&file);
        file.wipe();
        let (seed, x25519, xwing) = keys?;
        let device = Self {
            sign: crypto::signing_key(&seed),
            kem: KemSecrets {
                x25519: *x25519,
                xwing: xwing.as_deref().copied(),
            },
            cert: file.cert.clone(),
        };
        device.cert.verify()?;
        if device.cert.device != device.id_hex() {
            return Err(refused("the device file's certificate is for another key"));
        }
        Ok(device)
    }
}

type DeviceKeys = (Zeroizing<[u8; 32]>, Zeroizing<[u8; 32]>, Option<Zeroizing<[u8; 32]>>);

impl Device {
    fn keys_of(file: &DeviceFile) -> Result<DeviceKeys> {
        let key32 = |s: &str, what: &str| -> Result<Zeroizing<[u8; 32]>> {
            let raw = Zeroizing::new(unb64(s)?);
            let mut out = Zeroizing::new([0u8; 32]);
            if raw.len() != 32 {
                return Err(refused(format!("{what} has the wrong length")));
            }
            out.copy_from_slice(&raw);
            Ok(out)
        };
        Ok((
            key32(&file.sign, "device key")?,
            key32(&file.x25519, "X25519 key")?,
            file.xwing.as_deref().map(|s| key32(s, "X-Wing seed")).transpose()?,
        ))
    }
}

impl DeviceFile {
    fn wipe(&mut self) {
        self.sign.zeroize();
        self.x25519.zeroize();
        if let Some(x) = self.xwing.as_mut() {
            x.zeroize();
        }
    }
}

// ------------------------------------------------------------------------------ the stored root

/// The fleet root, sealed under a passphrase (Argon2id, then XChaCha20-Poly1305), for installs
/// that keep it to renew certificates unattended. Without a passphrase the root is not stored:
/// the recovery phrase re-derives it whenever it is needed.
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct SealedRoot {
    v: u32,
    kdf: String,
    m_kib: u32,
    t: u32,
    p: u32,
    salt: String,
    sealed: String,
}

const ROOT_AAD: &[u8] = b"aurora-link/v1/root";
/// The sealed-root format: v2 binds its KDF parameters into the AEAD's associated data.
const ROOT_FORMAT: u32 = 2;
/// Argon2id parameters: what `seal_root` writes, and the window `open_root` accepts. A file
/// asking for less would let whoever planted it make guessing cheap; one asking for much more
/// would make opening it a denial of service.
const ROOT_M_KIB: u32 = 64 * 1024;
const ROOT_M_KIB_MAX: u32 = 256 * 1024;
const ROOT_T: u32 = 3;
const ROOT_T_MAX: u32 = 8;
const ROOT_P_MAX: u32 = 4;

/// The passphrase as Argon2 sees it: NFC, so the same words typed on two systems (composed or
/// decomposed accents) open the same root.
fn nfc(passphrase: &str) -> Zeroizing<String> {
    Zeroizing::new(passphrase.nfc().collect())
}

/// The associated data: the domain, then every format field, so none can be altered unseen.
fn root_aad(f: &SealedRoot) -> Result<Vec<u8>> {
    let fields = codec::jcs(&serde_json::json!({
        "v": f.v, "kdf": f.kdf, "m_kib": f.m_kib, "t": f.t, "p": f.p, "salt": f.salt,
    }))?;
    Ok([ROOT_AAD, b"\0", &fields].concat())
}

fn root_kek(passphrase: &str, salt: &[u8], m_kib: u32, t: u32, p: u32) -> Result<Secret32> {
    let params = argon2::Params::new(m_kib, t, p, Some(32)).map_err(|e| refused(format!("argon2 parameters: {e}")))?;
    let argon = argon2::Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params);
    let mut out = Secret32([0u8; 32]);
    argon
        .hash_password_into(nfc(passphrase).as_bytes(), salt, &mut out.0)
        .map_err(|e| refused(format!("argon2: {e}")))?;
    Ok(out)
}

pub fn seal_root(root: &SigningKey, passphrase: &str) -> Result<Vec<u8>> {
    if nfc(passphrase).chars().count() < 12 {
        return Err(refused("the passphrase must have at least 12 characters"));
    }
    let salt = crypto::random_bytes(16);
    let mut file = SealedRoot {
        v: ROOT_FORMAT,
        kdf: "argon2id".into(),
        m_kib: ROOT_M_KIB,
        t: ROOT_T,
        p: 1,
        salt: b64(&salt),
        sealed: String::new(),
    };
    let kek = root_kek(passphrase, &salt, file.m_kib, file.t, file.p)?;
    let seed = Zeroizing::new(root.to_bytes());
    file.sealed = b64(&crypto::seal(&kek.0, &seed[..], &root_aad(&file)?));
    serde_json::to_vec_pretty(&file).map_err(|e| LinkError::Unavailable(e.to_string()))
}

pub fn open_root(raw: &[u8], passphrase: &str) -> Result<SigningKey> {
    let f: SealedRoot = codec::parse(raw, "sealed root")?;
    if f.v != ROOT_FORMAT || f.kdf != "argon2id" {
        return Err(refused(
            "sealed root has an unknown format (seal it again with `identity.init --force`)",
        ));
    }
    if !(ROOT_M_KIB..=ROOT_M_KIB_MAX).contains(&f.m_kib)
        || !(ROOT_T..=ROOT_T_MAX).contains(&f.t)
        || !(1..=ROOT_P_MAX).contains(&f.p)
    {
        return Err(refused(
            "sealed root asks for Argon2 parameters outside the accepted window",
        ));
    }
    let kek = root_kek(passphrase, &unb64(&f.salt)?, f.m_kib, f.t, f.p)?;
    let seed = Zeroizing::new(
        crypto::open(&kek.0, &unb64(&f.sealed)?, &root_aad(&f)?)
            .map_err(|_| refused("the root did not open with that passphrase"))?,
    );
    let mut arr = Zeroizing::new([0u8; 32]);
    if seed.len() != 32 {
        return Err(refused("sealed root holds a malformed key"));
    }
    arr.copy_from_slice(&seed);
    Ok(crypto::signing_key(&arr))
}

// --------------------------------------------------------------------------------- fingerprints

const FINGERPRINT_ITERATIONS: usize = 5200;

/// One fleet's 30-digit half of a safety number (Signal's construction: 5200 rounds of
/// SHA-512, then six 5-byte chunks each reduced mod 100000).
pub fn fleet_fingerprint(root: &[u8; 32]) -> String {
    let mut digest: Vec<u8> = [&[0u8, 1][..], root, b"aurora-link-fleet"].concat();
    for _ in 0..FINGERPRINT_ITERATIONS {
        let mut h = Sha512::new();
        h.update(&digest);
        h.update(root);
        digest = h.finalize().to_vec();
    }
    let mut out = String::with_capacity(30);
    for chunk in digest[..30].as_chunks::<5>().0 {
        let n = chunk.iter().fold(0u64, |acc, b| (acc << 8) | u64::from(*b));
        out.push_str(&format!("{:05}", n % 100_000));
    }
    out
}

/// The 60-digit safety number of two fleets: both halves, sorted, so both sides print the same.
pub fn safety_number(a: &[u8; 32], b: &[u8; 32]) -> String {
    let mut halves = [fleet_fingerprint(a), fleet_fingerprint(b)];
    halves.sort();
    halves.concat()
}

/// Group a fingerprint as people read it aloud: blocks of five digits.
pub fn grouped(digits: &str) -> String {
    digits
        .as_bytes()
        .chunks(5)
        .map(|c| std::str::from_utf8(c).unwrap_or(""))
        .collect::<Vec<_>>()
        .join(" ")
}

/// Every device under each root, for self-monitoring.
pub fn devices_by_root(certs: &[DeviceCert]) -> BTreeMap<String, Vec<String>> {
    let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for c in certs {
        out.entry(c.root.clone()).or_default().push(c.device.clone());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unhex_vec(s: &str) -> Vec<u8> {
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
            .collect()
    }

    #[test]
    fn slip10_matches_the_spec_vectors() {
        // SLIP-0010, "Test vector 1 for ed25519".
        let seed = unhex_vec("000102030405060708090a0b0c0d0e0f");
        let (k, c) = slip10_ed25519(&seed, &[]);
        assert_eq!(
            hex(&k[..]),
            "2b4be7f19ee27bbf30c667b642d5f4aa69fd169872f8fc3059c08ebae2eb19e7"
        );
        assert_eq!(
            hex(&c[..]),
            "90046a93de5380a72b5e45010748567d5ea02bbf6522f979e05c0d8d8ca9fffb"
        );
        let (k, c) = slip10_ed25519(&seed, &[0]);
        assert_eq!(
            hex(&k[..]),
            "68e0fe46dfb67e368c75379acec591dad19df3cde26e63b93a8e704f1dade7a3"
        );
        assert_eq!(
            hex(&c[..]),
            "8b59aa11380b624e81507a27fedda59fea6d0b779a778918a2fd3590e16e9c69"
        );
        assert_eq!(
            hex(&crypto::public_of(&crypto::signing_key(&k))),
            "8c8a13df77a28f3445213a0f432fde644acaa215fc72dcdf300d5efaa85d350c"
        );
    }

    #[test]
    fn the_phrase_re_derives_the_same_root() {
        let phrase = new_phrase();
        assert_eq!(phrase.split(' ').count(), 24);
        let a = root_from_phrase(&phrase).unwrap();
        let b = root_from_phrase(&format!("  {}  ", phrase.to_uppercase())).unwrap();
        assert_eq!(a.to_bytes(), b.to_bytes());
        assert!(root_from_phrase(&phrase.replacen(phrase.split(' ').next().unwrap(), "zoo", 1)).is_err());
    }

    #[test]
    fn certificates_verify_expire_and_renew() {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let mut device = Device::create(&root, "laptop", true, 1_000).unwrap();
        device.cert.verify().unwrap();
        assert!(device.cert.valid_at(1_000) && !device.cert.valid_at(1_000 + CERT_MAX_LIFETIME_S));
        assert!(device.needs_renewal(1_000 + CERT_MAX_LIFETIME_S - 10));
        let old = device.cert.clone();
        device.renew(&root, 5_000_000).unwrap();
        assert!(device.cert.same_keys(&old) && device.cert.not_after > old.not_after);
        let other_root = root_from_phrase(&new_phrase()).unwrap();
        assert!(device.renew(&other_root, 1).is_err());
        let mut forged = device.cert.clone();
        forged.label = "evil".into();
        assert!(forged.verify().is_err());
        // R4-4: a root certifying a device key it does not hold has no proof of possession.
        let thief = Device::create(&other_root, "thief", false, 1_000).unwrap();
        let mut squat =
            DeviceCert::issue(&other_root, &thief.sign, &device.cert.kem().unwrap(), "x", 1_000, 3600).unwrap();
        squat.device = device.cert.device.clone();
        squat.sig = b64(&crypto::sign(&other_root, "cert", &squat.body_bytes().unwrap()));
        let err = squat.verify().unwrap_err();
        assert!(err.to_string().contains("proof of possession"), "{err}");
        let mut no_pop = device.cert.clone();
        no_pop.pop = device.cert.sig.clone();
        assert!(
            no_pop.verify().is_err(),
            "the root's signature is not a proof of possession"
        );
        let back = Device::from_json(&device.to_json().unwrap()).unwrap();
        assert_eq!(back.id(), device.id());
    }

    #[test]
    fn a_sealed_root_opens_only_with_its_passphrase() {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let sealed = seal_root(&root, "correct horse battery").unwrap();
        assert_eq!(
            open_root(&sealed, "correct horse battery").unwrap().to_bytes(),
            root.to_bytes()
        );
        assert!(open_root(&sealed, "wrong horse battery").is_err());
        assert!(seal_root(&root, "short").is_err());
    }

    #[test]
    fn a_sealed_root_refuses_kdf_parameters_outside_the_window() {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let sealed = seal_root(&root, "correct horse battery").unwrap();
        let v: serde_json::Value = serde_json::from_slice(&sealed).unwrap();
        assert_eq!((v["m_kib"].as_u64(), v["t"].as_u64()), (Some(65536), Some(3)));
        for (field, value) in [
            ("m_kib", 8192u64),
            ("t", 1),
            ("m_kib", 4 * 1024 * 1024),
            ("t", 64),
            ("p", 0),
        ] {
            let mut weak = v.clone();
            weak[field] = value.into();
            let err = open_root(&serde_json::to_vec(&weak).unwrap(), "correct horse battery").unwrap_err();
            assert!(err.to_string().contains("window"), "{field}={value}: {err}");
        }
        let mut old = v.clone();
        old["v"] = 1.into();
        assert!(open_root(&serde_json::to_vec(&old).unwrap(), "correct horse battery").is_err());
    }

    #[test]
    fn the_passphrase_is_nfc_normalised_on_seal_and_open() {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let composed = "caf\u{e9} cr\u{e8}me br\u{fb}l\u{e9}e";
        let decomposed = "cafe\u{301} cre\u{300}me bru\u{302}le\u{301}e";
        assert_ne!(composed, decomposed);
        let sealed = seal_root(&root, composed).unwrap();
        assert_eq!(open_root(&sealed, decomposed).unwrap().to_bytes(), root.to_bytes());
    }

    #[test]
    fn safety_numbers_agree_and_differ() {
        let a = [1u8; 32];
        let b = [2u8; 32];
        assert_eq!(safety_number(&a, &b), safety_number(&b, &a));
        assert_eq!(safety_number(&a, &b).len(), 60);
        assert_ne!(safety_number(&a, &b), safety_number(&a, &[3u8; 32]));
        assert!(safety_number(&a, &b).bytes().all(|c| c.is_ascii_digit()));
    }
}
