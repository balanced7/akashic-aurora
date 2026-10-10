#![no_main]
//! A device certificate inside an ACL entry. Must never panic.
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(c) = aurora_link::codec::parse::<aurora_link::identity::DeviceCert>(data, "cert") {
        let _ = c.verify();
        let _ = c.kem();
    }
});
