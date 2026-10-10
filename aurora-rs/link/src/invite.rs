//! Invite codes: one string a person pastes into `aurora link join`.
//!
//! The code carries the invite secret (the log holds only its public key), where to dial the
//! inviter, and the inviter's fleet fingerprint so the joiner can print both halves of the
//! safety number. It is single-use and short-lived by default, so a leaked code is a narrow risk.

use base64::Engine as _;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use serde::{Deserialize, Serialize};

use crate::codec::{self, unhex};
use crate::error::{Result, refused};

pub const PREFIX: &str = "aurora-invite1:";
const MAX_CODE: usize = 4096;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InviteCode {
    pub v: u32,
    pub link: String,
    pub name: String,
    /// The 32-byte invite secret, hex.
    pub secret: String,
    /// The inviter's device id (its iroh node id).
    pub node: String,
    /// Relay URL the inviter is reachable through, if any.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub relay: Option<String>,
    /// Direct address hints (`ip:port`), e.g. a Tailscale address.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub addrs: Vec<String>,
    /// The inviter fleet's 30-digit fingerprint.
    pub fingerprint: String,
}

impl InviteCode {
    pub fn encode(&self) -> Result<String> {
        Ok(format!("{PREFIX}{}", URL_SAFE_NO_PAD.encode(codec::canonical(self)?)))
    }

    pub fn parse(code: &str) -> Result<Self> {
        let code = code.trim();
        if code.len() > MAX_CODE {
            return Err(refused("invite code is too long"));
        }
        let rest = code
            .strip_prefix(PREFIX)
            .ok_or_else(|| refused("not an Aurora invite code"))?;
        let raw = URL_SAFE_NO_PAD
            .decode(rest)
            .map_err(|_| refused("invite code is not valid base64url"))?;
        let c: InviteCode = codec::parse(&raw, "invite code")?;
        if c.v != 1 {
            return Err(refused("unknown invite code version"));
        }
        unhex::<32>(&c.link)?;
        unhex::<32>(&c.secret)?;
        unhex::<32>(&c.node)?;
        if c.fingerprint.len() != 30 || !c.fingerprint.bytes().all(|b| b.is_ascii_digit()) {
            return Err(refused("invite fingerprint must be 30 digits"));
        }
        if c.addrs.len() > 8 || c.addrs.iter().any(|a| a.parse::<std::net::SocketAddr>().is_err()) {
            return Err(refused("invite address hints are malformed"));
        }
        if let Some(r) = &c.relay
            && !(r.starts_with("https://") || r.starts_with("http://"))
        {
            return Err(refused("invite relay must be an http(s) URL"));
        }
        Ok(c)
    }

    pub fn secret_bytes(&self) -> Result<[u8; 32]> {
        unhex::<32>(&self.secret)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn codes_round_trip_and_refuse_junk() {
        let c = InviteCode {
            v: 1,
            link: "11".repeat(32),
            name: "partners".into(),
            secret: "22".repeat(32),
            node: "33".repeat(32),
            relay: Some("https://relay.example".into()),
            addrs: vec!["100.64.0.7:7777".into()],
            fingerprint: "0".repeat(30),
        };
        let s = c.encode().unwrap();
        assert_eq!(InviteCode::parse(&format!("  {s}\n")).unwrap(), c);
        assert!(InviteCode::parse("aurora-invite1:@@@").is_err());
        assert!(InviteCode::parse(&s.replace(PREFIX, "other:")).is_err());
        let mut bad = c.clone();
        bad.addrs = vec!["not an address".into()];
        assert!(InviteCode::parse(&bad.encode().unwrap()).is_err());
    }
}
