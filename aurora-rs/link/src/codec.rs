//! Strict encodings: canonical base64, fixed-length lowercase hex, and JCS (RFC 8785).
//!
//! Every byte string that is signed is produced here, so sender and verifier agree byte for byte.
//! Parsing is strict on purpose (`bridge_seal.py` learned each of these the hard way): base64
//! must be canonical, hex must be lowercase and exactly the right length, and numbers must be
//! whole and inside the range JavaScript and Python both represent exactly.

use base64::Engine as _;
use base64::engine::general_purpose::STANDARD;
use serde_json::Value;

use crate::error::{Result, refused};

/// The largest integer every JSON reader agrees on (2^53 - 1).
pub const MAX_SAFE_INT: u64 = (1 << 53) - 1;

pub fn b64(raw: &[u8]) -> String {
    STANDARD.encode(raw)
}

/// Canonical base64 only: padding required, no whitespace, no stray trailing bits.
pub fn unb64(text: &str) -> Result<Vec<u8>> {
    let raw = STANDARD
        .decode(text)
        .map_err(|_| refused("field is not canonical base64"))?;
    if STANDARD.encode(&raw) != text {
        return Err(refused("field is not canonical base64"));
    }
    Ok(raw)
}

pub fn hex(raw: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(raw.len() * 2);
    for b in raw {
        out.push(DIGITS[(b >> 4) as usize] as char);
        out.push(DIGITS[(b & 0xf) as usize] as char);
    }
    out
}

/// Lowercase hex of exactly `N` bytes.
pub fn unhex<const N: usize>(text: &str) -> Result<[u8; N]> {
    let bytes = text.as_bytes();
    if bytes.len() != N * 2 {
        return Err(refused(format!(
            "expected {} hex characters, got {}",
            N * 2,
            bytes.len()
        )));
    }
    let nib = |c: u8| match c {
        b'0'..=b'9' => Ok(c - b'0'),
        b'a'..=b'f' => Ok(c - b'a' + 10),
        _ => Err(refused("hex must be lowercase 0-9a-f")),
    };
    let mut out = [0u8; N];
    for (i, pair) in bytes.as_chunks::<2>().0.iter().enumerate() {
        out[i] = (nib(pair[0])? << 4) | nib(pair[1])?;
    }
    Ok(out)
}

/// JCS (RFC 8785) for the subset Aurora signs: null, booleans, safe integers, strings, arrays
/// and objects. Floats are refused rather than canonicalised: nothing we sign has a fraction,
/// and a float is the classic place two implementations disagree.
pub fn jcs(value: &Value) -> Result<Vec<u8>> {
    let mut out = Vec::with_capacity(256);
    write_jcs(value, &mut out)?;
    Ok(out)
}

fn write_jcs(value: &Value, out: &mut Vec<u8>) -> Result<()> {
    match value {
        Value::Null => out.extend_from_slice(b"null"),
        Value::Bool(true) => out.extend_from_slice(b"true"),
        Value::Bool(false) => out.extend_from_slice(b"false"),
        Value::Number(n) => {
            if let Some(u) = n.as_u64() {
                if u > MAX_SAFE_INT {
                    return Err(refused("integer is outside the safe range"));
                }
                out.extend_from_slice(u.to_string().as_bytes());
            } else if let Some(i) = n.as_i64() {
                if i.unsigned_abs() > MAX_SAFE_INT {
                    return Err(refused("integer is outside the safe range"));
                }
                out.extend_from_slice(i.to_string().as_bytes());
            } else {
                return Err(refused("non-integer numbers are not signed"));
            }
        }
        Value::String(s) => write_str(s, out),
        Value::Array(items) => {
            out.push(b'[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                write_jcs(item, out)?;
            }
            out.push(b']');
        }
        Value::Object(map) => {
            // RFC 8785 sorts member names by their UTF-16 code units, not by UTF-8 bytes.
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort_by(|a, b| a.encode_utf16().cmp(b.encode_utf16()));
            out.push(b'{');
            for (i, key) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                write_str(key, out);
                out.push(b':');
                write_jcs(&map[key.as_str()], out)?;
            }
            out.push(b'}');
        }
    }
    Ok(())
}

/// ECMAScript `JSON.stringify` string escaping, which RFC 8785 adopts.
fn write_str(s: &str, out: &mut Vec<u8>) {
    out.push(b'"');
    for c in s.chars() {
        match c {
            '"' => out.extend_from_slice(b"\\\""),
            '\\' => out.extend_from_slice(b"\\\\"),
            '\u{08}' => out.extend_from_slice(b"\\b"),
            '\u{0c}' => out.extend_from_slice(b"\\f"),
            '\n' => out.extend_from_slice(b"\\n"),
            '\r' => out.extend_from_slice(b"\\r"),
            '\t' => out.extend_from_slice(b"\\t"),
            c if (c as u32) < 0x20 => out.extend_from_slice(format!("\\u{:04x}", c as u32).as_bytes()),
            c => {
                let mut buf = [0u8; 4];
                out.extend_from_slice(c.encode_utf8(&mut buf).as_bytes());
            }
        }
    }
    out.push(b'"');
}

/// JCS of any serialisable value.
pub fn canonical<T: serde::Serialize>(value: &T) -> Result<Vec<u8>> {
    let v = serde_json::to_value(value).map_err(|e| refused(format!("not serialisable: {e}")))?;
    jcs(&v)
}

/// Parse JSON strictly into `T` (whose serde derive should deny unknown fields).
pub fn parse<T: serde::de::DeserializeOwned>(raw: &[u8], what: &str) -> Result<T> {
    serde_json::from_slice(raw).map_err(|e| refused(format!("{what} is malformed: {e}")))
}

/// Seconds since the Unix epoch.
pub fn now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn jcs_sorts_by_utf16_and_escapes_like_ecmascript() {
        // RFC 8785 section 3.2.3's sorting example, minus its float members.
        let v = json!({"\u{20ac}": "Euro Sign", "\r": "Carriage Return", "\u{fb33}": "Hebrew Letter Dalet With Dagesh",
            "1": "One", "\u{1f600}": "Emoji: Grinning Face", "\u{0080}": "Control", "\u{00f6}": "Latin Small Letter O With Diaeresis"});
        let got = String::from_utf8(jcs(&v).unwrap()).unwrap();
        let order: Vec<&str> = ["\\r", "1", "\u{0080}", "\u{00f6}", "\u{20ac}", "\u{1f600}", "\u{fb33}"].to_vec();
        let mut last = 0;
        for key in order {
            let at = got.find(&format!("\"{key}\":")).unwrap();
            assert!(at >= last, "{key} out of order in {got}");
            last = at;
        }
        assert_eq!(
            String::from_utf8(jcs(&json!("\u{1}\u{1f}\"\\/")).unwrap()).unwrap(),
            r#""\u0001\u001f\"\\/""#
        );
    }

    #[test]
    fn jcs_refuses_floats_and_unsafe_integers() {
        assert!(jcs(&json!(1.5)).is_err());
        assert!(jcs(&json!(MAX_SAFE_INT + 1)).is_err());
        assert_eq!(jcs(&json!(-7)).unwrap(), b"-7");
    }

    #[test]
    fn base64_and_hex_are_strict() {
        assert_eq!(unb64("aGk=").unwrap(), b"hi");
        for bad in ["aGk", "aG k=", "aGl=", "aGk=\n", "aGk==", ""] {
            if bad.is_empty() {
                assert_eq!(unb64(bad).unwrap(), b"");
                continue;
            }
            assert!(unb64(bad).is_err(), "{bad:?} should be refused");
        }
        assert_eq!(unhex::<2>("0aff").unwrap(), [0x0a, 0xff]);
        assert!(unhex::<2>("0AFF").is_err());
        assert!(unhex::<2>("0af").is_err());
    }
}
