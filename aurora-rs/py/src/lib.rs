//! `aurora_rs`: the Python module maturin builds from this crate.
//!
//! Each function is a thin wrapper over a pure-Rust crate, with the same name and output as the
//! Python function it accelerates. Python decides whether to use it (core/accel.py).

use std::collections::HashSet;

use pyo3::prelude::*;

/// Stemmed word tokens of `text` -- learning_store._tokens_of, in Rust.
#[pyfunction]
fn tokens_of(text: &str) -> HashSet<String> {
    aurora_text::tokens_of(text)
}

/// One lowercase token folded to its stem -- learning_store._stem, in Rust.
#[pyfunction]
fn stem(tok: &str) -> String {
    aurora_text::stem(tok).to_owned()
}

// ---------------------------------------------------------------- fleet links (pure, offline)
//
// These three are the whole PyO3 surface of aurora-link (RFC #70 addendum §2.4): pure functions
// for doctor, tests and the console. No network, no runtime, no keys. They call the same crate the
// daemon runs, so there is still one implementation; Python never re-implements them.

fn refused(e: aurora_link::LinkError) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(e.to_string())
}

/// Check one record's shape, ciphertext hash and author signature; return its record id.
/// Raises ValueError when it does not verify. Membership is the daemon's to judge.
#[pyfunction]
fn verify_record(record_json: &str) -> PyResult<String> {
    let r: aurora_link::record::Record =
        aurora_link::codec::parse(record_json.as_bytes(), "record").map_err(refused)?;
    r.verify().map_err(refused)
}

/// A fleet's 30-digit fingerprint from its root key (hex), or the 60-digit safety number of two.
#[pyfunction]
#[pyo3(signature = (root, other=None))]
fn fingerprint(root: &str, other: Option<&str>) -> PyResult<String> {
    let a = aurora_link::codec::unhex::<32>(root).map_err(refused)?;
    Ok(match other {
        Some(o) => aurora_link::identity::safety_number(&a, &aurora_link::codec::unhex::<32>(o).map_err(refused)?),
        None => aurora_link::identity::fleet_fingerprint(&a),
    })
}

/// Parse an invite code; returns its public fields as JSON (never the secret).
#[pyfunction]
fn parse_invite(code: &str) -> PyResult<String> {
    let c = aurora_link::invite::InviteCode::parse(code).map_err(refused)?;
    Ok(serde_json::json!({
        "link": c.link, "name": c.name, "node": c.node, "relay": c.relay, "addrs": c.addrs,
        "fingerprint": c.fingerprint,
    })
    .to_string())
}

/// The bridge allowlist as the daemon enforces it.
#[pyfunction]
fn bridge_kinds() -> Vec<&'static str> {
    aurora_link::acl::BRIDGE_KINDS.to_vec()
}

#[pymodule]
fn aurora_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(verify_record, m)?)?;
    m.add_function(wrap_pyfunction!(fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(parse_invite, m)?)?;
    m.add_function(wrap_pyfunction!(bridge_kinds, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(tokens_of, m)?)?;
    m.add_function(wrap_pyfunction!(stem, m)?)?;
    Ok(())
}
