#![no_main]
//! A batch of ACL chain entries from a peer: parse, insert into an empty chain (twice, and again
//! in reverse), then ask for the state at each held position, a range of it under a budget, and
//! a proposal check against it; then offer the batch's second half as evidence. Must never panic.
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(entries) = aurora_link::codec::parse::<Vec<aurora_link::acl::Entry>>(data, "acl") {
        let mut chain = aurora_link::acl::AclChain::new();
        let _ = chain.insert(entries.clone(), Some(aurora_link::codec::now()));
        let mut rev = entries.clone();
        rev.reverse();
        let _ = chain.insert(rev, None);
        let _ = chain.state().keyed_devices();
        let _ = chain.state().next_sequencer();
        for seq in 0..chain.len().min(8) as u64 {
            let _ = chain.state_at(seq);
            let _ = chain.epoch_at(seq);
        }
        let _ = chain.range(0, u64::MAX, 64 * 1024);
        let _ = chain.range(u64::MAX - 1, 3, 1);
        for e in entries.iter().take(4) {
            for p in &e.proposals {
                let _ = chain.check_proposal(p, aurora_link::codec::now());
            }
        }
        if let [a, b, ..] = entries.as_slice() {
            let _ = chain.note_evidence(a, b);
        }
        let _ = chain.tip();
        let _ = chain.take_dirty();
    }
});
