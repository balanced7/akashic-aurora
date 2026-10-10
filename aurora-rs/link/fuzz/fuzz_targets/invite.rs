#![no_main]
//! An invite code pasted by a person. Must never panic.
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let _ = aurora_link::invite::InviteCode::parse(s);
    }
});
