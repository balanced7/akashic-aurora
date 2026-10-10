#![no_main]
//! A batch of ACL entries from a peer: parse, then merge into an empty log. Must never panic.
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(entries) = aurora_link::codec::parse::<Vec<aurora_link::acl::Entry>>(data, "acl") {
        let mut log = aurora_link::acl::AclLog::new();
        let _ = log.insert(entries);
        let _ = log.state().keyed_devices();
    }
});
