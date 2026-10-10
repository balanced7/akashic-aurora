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

#[pymodule]
fn aurora_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(tokens_of, m)?)?;
    m.add_function(wrap_pyfunction!(stem, m)?)?;
    Ok(())
}
