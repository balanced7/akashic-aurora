//! The shared test vectors in aurora-rs/link-vectors/: records, ACL histories with a fork,
//! fingerprints and invite codes. Any second reader of the format (the Python wheel tests, a
//! future port) checks itself against these files, not against a twin implementation.
//!
//! `AURORA_WRITE_VECTORS=1 cargo test -p aurora-link --test vectors` regenerates them; otherwise
//! this test checks that the current code still accepts and refuses exactly what they say.

use std::collections::BTreeMap;
use std::path::PathBuf;

use aurora_link::acl::{self, AclLog, Entry, Op, Policy, Role};
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
        let body = Body { kind: "note".into(), seat: "claude".into(), to: "@peer/codex".into(), content: "vector".into(), sent_at: 1, ..Body::default() };
        let (link, acl_head) = ("11".repeat(32), "22".repeat(32));
        let kinds: Vec<String> = acl::BRIDGE_KINDS.iter().map(|k| (*k).to_owned()).collect();
        let r = Record::seal(&dev, Seal { link: &link, seq: 1, prev: "", deps: vec![], acl: &acl_head, epoch: 0, key: &key }, &body, &kinds).unwrap();
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
        ]);
        save("records.json", &json!({"key_hex": hex(&key), "author": dev.id_hex(), "cases": cases}));
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
        save("fingerprints.json", &json!({
            "phrase": PHRASE,
            "root": hex(&a),
            "fingerprint": identity::fleet_fingerprint(&a),
            "other": hex(&b),
            "safety_number": identity::safety_number(&a, &b),
        }));
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
            v: 1, link: "11".repeat(32), name: "partners".into(), secret: "22".repeat(32), node: "33".repeat(32),
            relay: Some("https://relay.example".into()), addrs: vec!["100.64.0.7:7777".into()], fingerprint: "0".repeat(30),
        };
        save("invites.json", &json!({"cases": [
            {"code": ok.encode().unwrap(), "valid": true, "link": ok.link},
            {"code": "aurora-invite1:@@@", "valid": false},
            {"code": ok.encode().unwrap().replace("aurora-invite1:", "aurora-invite2:"), "valid": false},
            {"code": "aurora-invite1:", "valid": false},
        ]}));
    }
    for case in load("invites.json")["cases"].as_array().unwrap() {
        let got = InviteCode::parse(case["code"].as_str().unwrap());
        assert_eq!(got.is_ok(), case["valid"].as_bool().unwrap(), "{}", case["code"]);
    }
}

/// A log where the owner and an admin append at the same head: every replay order resolves the
/// same, the owner's removal of the admin wins, and the admin's concurrent invite is dropped.
#[test]
fn acl_fork() {
    if write() {
        let owner_root = identity::root_from_phrase(PHRASE).unwrap();
        let o = Device::create(&owner_root, "owner", false, 1_000).unwrap();
        let admin_root = identity::root_from_phrase(&identity::new_phrase()).unwrap();
        let a = Device::create(&admin_root, "admin", false, 1_000).unwrap();
        let (mut log, _) = acl::genesis(&o, "vectors", "owner", Policy::default(), 1_001).unwrap();
        let secret = [9u8; 32];
        let inv = hex(&crypto::public_of(&acl::invite_key(&secret)));
        log.append(&o, Op::Invite(acl::Invite { invite: inv, role: Role::Admin, expires: 2_000, single_use: true, approval: false }), 1_002).unwrap();
        let s = log.state().clone();
        log.insert(vec![acl::make_join(&a, &secret, &s.link_id, &s.head, s.head_seq, "admin", 1_003).unwrap()]).unwrap();
        let s = log.state().clone();
        let join = s.pending_joins.keys().next().unwrap().clone();
        let key = s.read_key(0, &o.id_hex(), &o.kem).unwrap();
        let wraps = s.make_wraps(&key.0, 0, &s.members[a.root_hex()].devices).unwrap();
        log.append(&o, Op::Accept(acl::Accept { join, wraps }), 1_004).unwrap();
        let mut left = log.clone();
        let mut right = log.clone();
        left.append(&o, Op::RemoveMember(acl::RemoveMember { member: a.root_hex().into(), cut: BTreeMap::new(), rotate: None }), 1_010).unwrap();
        right.append(&a, Op::Invite(acl::Invite { invite: "44".repeat(32), role: Role::Writer, expires: 2_000, single_use: true, approval: false }), 1_010).unwrap();
        let mut all: Vec<Entry> = left.missing_for(&Default::default());
        for e in right.missing_for(&left.hashes()) {
            all.push(e);
        }
        save("acl-fork.json", &json!({"entries": all, "removed": a.root_hex(), "dropped": 1}));
    }
    let v = load("acl-fork.json");
    let entries: Vec<Entry> = serde_json::from_value(v["entries"].clone()).unwrap();
    let mut summaries = std::collections::BTreeSet::new();
    for rotate in 0..entries.len() {
        let mut order = entries.clone();
        order.rotate_left(rotate);
        let mut log = AclLog::new();
        // Arrival order varies; a batch is applied whatever order it came in.
        log.insert(order).unwrap();
        let s = log.state();
        assert!(s.members[v["removed"].as_str().unwrap()].removed);
        assert_eq!(s.dropped.len() as u64, v["dropped"].as_u64().unwrap());
        summaries.insert(format!("{:?}{}", s.applied, s.head));
    }
    assert_eq!(summaries.len(), 1, "every arrival order resolves the same way");
}
