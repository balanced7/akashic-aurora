//! The shared test vectors in aurora-rs/link-vectors/: records, an ACL chain with a handoff and a
//! root takeover, an equivocation, fingerprints and invite codes. Any second reader of the format (the Python wheel tests, a
//! future port) checks itself against these files, not against a twin implementation.
//!
//! `AURORA_WRITE_VECTORS=1 cargo test -p aurora-link --test vectors` regenerates them; otherwise
//! this test checks that the current code still accepts and refuses exactly what they say.

use std::path::PathBuf;

use aurora_link::acl::{self, AclChain, AclPos, Entry, Op, Policy, Role};
use aurora_link::codec::hex;
use aurora_link::crypto;
use aurora_link::identity::{self, Device};
use aurora_link::invite::InviteCode;
use aurora_link::record::{Body, Record, Seal};
use serde_json::{Value, json};

fn dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../link-vectors")
}

fn write() -> bool {
    std::env::var("AURORA_WRITE_VECTORS").is_ok_and(|v| v == "1")
}

fn save(name: &str, v: &Value) {
    std::fs::write(dir().join(name), serde_json::to_string_pretty(v).unwrap() + "\n").unwrap();
}

fn load(name: &str) -> Value {
    serde_json::from_str(&std::fs::read_to_string(dir().join(name)).unwrap()).unwrap()
}

// A fixed phrase, so the vectors name stable roots. Never use it for anything real.
const PHRASE: &str = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon \
abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art";

fn tamper(r: &Record, f: impl Fn(&mut Value)) -> Value {
    let mut v = serde_json::to_value(r).unwrap();
    f(&mut v);
    v
}

#[test]
fn records() {
    if write() {
        let root = identity::root_from_phrase(PHRASE).unwrap();
        let dev = Device::create(&root, "vectors", false, 1_000).unwrap();
        let key = [7u8; 32];
        let body = Body {
            kind: "note".into(),
            seat: "claude".into(),
            to: "@peer/codex".into(),
            content: "vector".into(),
            sent_at: 1,
            ..Body::default()
        };
        let link = "11".repeat(32);
        let position = AclPos {
            term: 1,
            seq: 4,
            hash: "22".repeat(32),
        };
        let kinds: Vec<String> = acl::BRIDGE_KINDS.iter().map(|k| (*k).to_owned()).collect();
        let r = Record::seal(
            &dev,
            Seal {
                link: &link,
                seq: 1,
                ts: 1_000,
                prev: "",
                deps: vec![],
                acl: &position,
                epoch: 0,
                key: &key,
            },
            &body,
            &kinds,
        )
        .unwrap();
        let id = r.id().unwrap();
        let cases = json!([
            {"name": "valid", "record": r, "valid": true, "id": id},
            {"name": "retired header still verifies", "record": r.retired(), "valid": true, "id": id},
            {"name": "seq changed", "record": tamper(&r, |v| v["seq"] = json!(2)), "valid": false},
            {"name": "epoch changed", "record": tamper(&r, |v| v["epoch"] = json!(1)), "valid": false},
            {"name": "ciphertext byte flipped", "record": tamper(&r, |v| {
                let mut ct = aurora_link::codec::unb64(v["ct"].as_str().unwrap()).unwrap();
                ct[30] ^= 1;
                v["ct"] = json!(aurora_link::codec::b64(&ct));
            }), "valid": false},
            {"name": "non-canonical base64", "record": tamper(&r, |v| v["sig"] = json!(format!(" {}", v["sig"].as_str().unwrap()))), "valid": false},
            {"name": "unknown field", "record": tamper(&r, |v| v["authority"] = json!("admin")), "valid": false},
            {"name": "seq 2 without prev", "record": tamper(&r, |v| v["seq"] = json!(2)), "valid": false},
            {"name": "ACL position changed", "record": tamper(&r, |v| v["acl"]["seq"] = json!(5)), "valid": false},
            {"name": "ACL position without a hash", "record": tamper(&r, |v| v["acl"] = json!({"term": 1, "seq": 4})), "valid": false},
            {"name": "ACL position in term 0", "record": tamper(&r, |v| v["acl"]["term"] = json!(0)), "valid": false},
            {"name": "ACL heads as a list (the round-4 format)", "record": tamper(&r, |v| v["acl"] = json!(["22".repeat(32)])), "valid": false},
        ]);
        save(
            "records.json",
            &json!({"key_hex": hex(&key), "author": dev.id_hex(), "cases": cases}),
        );
    }
    let v = load("records.json");
    for case in v["cases"].as_array().unwrap() {
        let parsed: Result<Record, _> = aurora_link::codec::parse(case["record"].to_string().as_bytes(), "record");
        let got = parsed.and_then(|r| r.verify());
        assert_eq!(got.is_ok(), case["valid"].as_bool().unwrap(), "{}", case["name"]);
        if let (Ok(id), Some(want)) = (&got, case["id"].as_str()) {
            assert_eq!(id, want, "{}", case["name"]);
        }
    }
}

#[test]
fn fingerprints_and_slip10() {
    if write() {
        let root = identity::root_from_phrase(PHRASE).unwrap();
        let a = crypto::public_of(&root);
        let b = [2u8; 32];
        save(
            "fingerprints.json",
            &json!({
                "phrase": PHRASE,
                "root": hex(&a),
                "fingerprint": identity::fleet_fingerprint(&a),
                "other": hex(&b),
                "safety_number": identity::safety_number(&a, &b),
            }),
        );
    }
    let v = load("fingerprints.json");
    let root = identity::root_from_phrase(v["phrase"].as_str().unwrap()).unwrap();
    let a = crypto::public_of(&root);
    assert_eq!(hex(&a), v["root"]);
    assert_eq!(identity::fleet_fingerprint(&a), v["fingerprint"]);
    let b = aurora_link::codec::unhex::<32>(v["other"].as_str().unwrap()).unwrap();
    assert_eq!(identity::safety_number(&a, &b), v["safety_number"]);
    assert_eq!(identity::safety_number(&b, &a), v["safety_number"]);
}

#[test]
fn invite_codes() {
    if write() {
        let ok = InviteCode {
            v: 1,
            link: "11".repeat(32),
            name: "partners".into(),
            secret: "22".repeat(32),
            invite: "44".repeat(32),
            node: "33".repeat(32),
            relay: Some("https://relay.example".into()),
            addrs: vec!["100.64.0.7:7777".into()],
            fingerprint: "0".repeat(30),
        };
        save(
            "invites.json",
            &json!({"cases": [
                {"code": ok.encode().unwrap(), "valid": true, "link": ok.link},
                {"code": "aurora-invite1:@@@", "valid": false},
                {"code": ok.encode().unwrap().replace("aurora-invite1:", "aurora-invite2:"), "valid": false},
                {"code": "aurora-invite1:", "valid": false},
            ]}),
        );
    }
    for case in load("invites.json")["cases"].as_array().unwrap() {
        let got = InviteCode::parse(case["code"].as_str().unwrap());
        assert_eq!(got.is_ok(), case["valid"].as_bool().unwrap(), "{}", case["code"]);
    }
}

fn zero(_: &str) -> u64 {
    0
}

/// A chain: genesis by the owner's first device, an invite, a join (a proposal by the joining
/// device), its accept, a handoff to the owner's second device and a term-2 entry; then the
/// second device is lost after two more entries, and the owner's root takes over on the first
/// device, after the term-2 entry, as term 3. The lost entries come with it: every replica
/// ignores them, in any arrival order.
#[test]
fn acl_chain() {
    if write() {
        let owner_root = identity::root_from_phrase(PHRASE).unwrap();
        let o = Device::create(&owner_root, "owner", false, 1_000).unwrap();
        let o2 = Device::create(&owner_root, "owner2", false, 1_000).unwrap();
        let admin_root = identity::root_from_phrase(&identity::new_phrase()).unwrap();
        let a = Device::create(&admin_root, "admin", false, 1_000).unwrap();
        let (mut chain, _) = acl::genesis(&o, "vectors", "owner", Policy::default(), 1_001).unwrap();
        let s = chain.state().clone();
        let key = s.read_key(0, &o.id_hex(), &o.kem).unwrap();
        let mut tmp = s.clone();
        tmp.devices.insert(
            o2.id_hex(),
            acl::DeviceState::new(o2.cert.clone(), o2.root_hex().into()),
        );
        let wraps = tmp.make_wraps(&key.0, 0, &[o2.id_hex()].into()).unwrap();
        chain
            .append(
                &o,
                Some(Op::AddDevice(acl::AddDevice {
                    cert: o2.cert.clone(),
                    wraps,
                })),
                vec![],
                1_002,
                &zero,
            )
            .unwrap();
        let secret = [9u8; 32];
        let issued = chain
            .append(
                &o,
                Some(Op::Invite(acl::Invite {
                    invite: hex(&crypto::public_of(&acl::invite_key(&secret))),
                    role: Role::Admin,
                    expires: 2_000,
                    single_use: true,
                    approval: false,
                })),
                vec![],
                1_003,
                &zero,
            )
            .unwrap();
        let ticket = acl::InviteTicket {
            secret,
            entry: issued.hash().unwrap(),
        };
        let t = chain.tip();
        let join = acl::make_join(
            &a,
            &ticket,
            chain.link_id(),
            acl::Base {
                term: t.term,
                seq: t.seq,
            },
            "admin",
            1_004 + acl::PROPOSAL_TTL_S,
        )
        .unwrap();
        chain.append(&o, None, vec![join.clone()], 1_004, &zero).unwrap();
        let s = chain.state().clone();
        let wraps = s.make_wraps(&key.0, 0, &s.members[a.root_hex()].devices).unwrap();
        chain
            .append(
                &o,
                Some(Op::Accept(acl::Accept {
                    join: join.id().unwrap(),
                    wraps,
                })),
                vec![],
                1_005,
                &zero,
            )
            .unwrap();
        chain
            .append(
                &o,
                Some(Op::Handoff(acl::Handoff { to: o2.id_hex() })),
                vec![],
                1_006,
                &zero,
            )
            .unwrap();
        let invite = |n: u8, ts: u64| {
            Op::Invite(acl::Invite {
                invite: hex(&[n; 32]),
                role: Role::Reader,
                expires: ts + 600,
                single_use: true,
                approval: false,
            })
        };
        chain.append(&o2, Some(invite(1, 1_007)), vec![], 1_007, &zero).unwrap();
        let mut lost = chain.clone();
        let dropped: Vec<Entry> = (0..2u8)
            .map(|k| {
                lost.append(&o2, Some(invite(2 + k, 1_008)), vec![], 1_008 + u64::from(k), &zero)
                    .unwrap()
            })
            .collect();
        let takeover = chain.takeover(&o, &owner_root, None, 1_020).unwrap();
        let after = chain.append(&o, Some(invite(5, 1_021)), vec![], 1_021, &zero).unwrap();
        let _ = after;
        let s = chain.state();
        save(
            "acl-chain.json",
            &json!({
                "entries": chain.all(), "dropped": dropped, "tip": chain.tip(), "takeover": takeover.hash().unwrap(),
                "epoch": s.epoch, "sequencer": s.sequencer, "admin": a.root_hex(),
            }),
        );
    }
    let v = load("acl-chain.json");
    let entries: Vec<Entry> = serde_json::from_value(v["entries"].clone()).unwrap();
    let dropped: Vec<Entry> = serde_json::from_value(v["dropped"].clone()).unwrap();
    let tip: AclPos = serde_json::from_value(v["tip"].clone()).unwrap();
    let mut summaries = std::collections::BTreeSet::new();
    let mut all = entries.clone();
    all.extend(dropped.iter().cloned());
    for rotate in 0..all.len() {
        let mut order = all.clone();
        order.rotate_left(rotate);
        let mut chain = AclChain::new();
        // Arrival order varies: a batch is sorted by seq; the lost term-2 entries either never
        // apply, or apply and are dropped when the takeover arrives.
        for _ in 0..3 {
            chain.insert(order.clone(), None);
        }
        assert_eq!(chain.tip(), tip, "rotation {rotate}");
        let s = chain.state();
        assert_eq!(s.epoch, v["epoch"].as_u64().unwrap());
        assert_eq!(s.sequencer, v["sequencer"].as_str().unwrap());
        assert_eq!(s.term, 3);
        assert_eq!(s.members[v["admin"].as_str().unwrap()].role, Role::Admin);
        summaries.insert(format!("{:?}", chain.tip()));
    }
    assert_eq!(summaries.len(), 1);
    // The term-2 entries and the takeover start terms the way the chain says.
    assert_eq!(entries.iter().map(|e| e.term).max(), Some(3));
}

/// Two entries the term's sequencer signed at one position: a replica holding one halts at the
/// common prefix when it sees the other.
#[test]
fn acl_equivocation() {
    if write() {
        let owner_root = identity::root_from_phrase(PHRASE).unwrap();
        let o = Device::create(&owner_root, "owner", false, 1_000).unwrap();
        let (chain, _) = acl::genesis(&o, "vectors", "owner", Policy::default(), 1_001).unwrap();
        let (mut left, mut right) = (chain.clone(), chain.clone());
        let op = |n: u8| {
            Op::Invite(acl::Invite {
                invite: hex(&[n; 32]),
                role: Role::Reader,
                expires: 1_600,
                single_use: true,
                approval: false,
            })
        };
        let a = left.append(&o, Some(op(1)), vec![], 1_002, &zero).unwrap();
        let b = right.append(&o, Some(op(2)), vec![], 1_002, &zero).unwrap();
        save(
            "acl-equivocation.json",
            &json!({"prefix": chain.all(), "a": a, "b": b, "halt_seq": a.seq}),
        );
    }
    let v = load("acl-equivocation.json");
    let prefix: Vec<Entry> = serde_json::from_value(v["prefix"].clone()).unwrap();
    let a: Entry = serde_json::from_value(v["a"].clone()).unwrap();
    let b: Entry = serde_json::from_value(v["b"].clone()).unwrap();
    for (first, second) in [(&a, &b), (&b, &a)] {
        let mut chain = AclChain::new();
        chain.insert(prefix.clone(), None);
        let tip = chain.tip();
        assert_eq!(chain.insert(vec![first.clone()], None).added, 1);
        assert!(chain.insert(vec![second.clone()], None).equivocation);
        assert_eq!(chain.halt().unwrap().seq, v["halt_seq"].as_u64().unwrap());
        assert_eq!(chain.tip(), tip, "back at the common prefix");
    }
}
