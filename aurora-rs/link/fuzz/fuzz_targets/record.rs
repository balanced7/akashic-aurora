#![no_main]
//! A record off the wire: strict parse, then verify. Must never panic.
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(r) = aurora_link::codec::parse::<aurora_link::record::Record>(data, "record") {
        let _ = r.verify();
        let _ = r.open(&[0u8; 32], &["note".to_owned()]);
    }
});
