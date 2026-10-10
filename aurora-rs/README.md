# aurora-rs

Aurora's Rust workspace. A hot path moves here only after a benchmark shows that Python is too slow for it. Python keeps a reference version of every function and falls back to it, so Rust speeds Aurora up but is never required. The one exception is a feature where two implementations would be a security risk; see [Required crates](#required-crates).

The layout follows openai/codex's `codex-rs/`: one Cargo workspace, small crates that each do one job, and one shared version.

| crate | what it is |
|---|---|
| `text/` (`aurora-text`) | The recall tokenizer: lowercase word runs folded to light stems. It is a port of `_tokens_of` in `core/learning/learning_store.py`. |
| `py/` (`aurora-py`) | PyO3 bindings. maturin builds them into the `akashic-aurora-rs` wheel, which imports as `aurora_rs`. |
| `link/` (`aurora-link`) | Fleet links (RFC #70): identity, the ACL log, signed and sealed records, the per-link store and the sync session. Pure logic, no network. |
| `linkd/` (`aurora-linkd`) | The fleet-link daemon: iroh transport, gossip, blobs, mailbox mode and the JSON-RPC channel. maturin packs the binary into the `akashic-aurora-linkd` wheel. |
| `link-vectors/` | JSON test vectors for the link formats: records, ACL forks, fingerprints and invites. |

## The first port: the recall tokenizer

`recall` tokenizes every stored lesson on every query, so the cost grows with the memory. On 2,000 lesson-sized documents (`bench.py`), the Rust tokenizer is about 17 times faster than the Python one (746 ms against 44 ms on a desktop x86_64), with identical output.

## Build and try it

```bash
cargo build -p aurora-linkd     # the fleet-link daemon; core/link finds it in target/ in a checkout
cd aurora-rs && cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check
uvx --from 'maturin>=1.9,<2' maturin develop --release -m aurora-rs/py/Cargo.toml --uv   # into the repo's .venv
uv run pytest tests/test_accel_parity.py      # Rust output == Python output
uv run python aurora-rs/bench.py              # how much faster
```

`maturin develop` puts the wheel in the repo's `.venv`. The next `uv sync` removes it again, because it is not in `uv.lock`. Run `AURORA_NO_RUST=1` to force the Python path without uninstalling it.

## How a release ships it

`.github/workflows/release.yml` builds one abi3 wheel per platform with maturin. That covers Linux x86_64 and aarch64, macOS x86_64 and arm64, and Windows x64. One wheel serves every Python version from 3.11 up. The wheels are attached to the GitHub release and published to PyPI. When the `aurora` launcher prepares a bundle, it installs the wheel that matches its version, if one exists for the platform. If none does, Aurora runs the Python path and gives the same results.

## Required crates

A crate may be **required by a feature** when two implementations would be a security risk. The feature is then unavailable without the wheel, and the rest of Aurora is unaffected. Such crates ship test vectors, not a Python twin. Today the only such feature is fleet links (`aurora-linkd`).

Without the `akashic-aurora-linkd` wheel, `aurora link …` prints "links need the akashic-aurora-linkd package" and exits. Everything else runs.

The reason is premise P2 of the RFC addendum. For a tokenizer, a Python fallback is a convenience. For a signature scheme, a silent fallback means running the less-tested of two implementations, and any disagreement between them about which bytes are signed is itself the vulnerability. So Python calls `aurora_rs.verify_record`, `fingerprint` and `parse_invite`, which are thin bindings over the same crate, and checks itself against `link-vectors/`.

### Keeping the link crates safe

- **Gate.** `uv run poe rust-gate` (part of `poe gate` when `aurora-rs/` changed) runs fmt, clippy, the tests, `cargo deny check` and a fuzz smoke. CI's `rust` job also runs `cargo audit` and checks the link crates build on iroh's MSRV, 1.91.
- **Fuzzing.** `link/fuzz/` has a cargo-fuzz target for every decoder that sees untrusted bytes, including one that feeds every sync frame variant to a live session: `cd link && cargo +nightly fuzz run frame`.
- **Advisories.** A high-severity RustSec advisory on a network-facing crate (iroh, iroh-gossip, iroh-blobs, rustls, the RustCrypto crates) gets a patch release within 7 days.
- **Churn.** iroh-gossip and iroh-blobs break every few weeks, so they are pinned exactly (`=`), and one upgrade per quarter is budgeted. Dependabot proposes Cargo bumps after a 7-day cooldown.
- **Panics.** The daemon is built with the `linkd` profile (`panic = "abort"`), and `ManagedChild` restarts it. The PyO3 module keeps unwinding, so a panic there becomes a Python exception.

## Porting another hot path

1. **Measure first.** Write the benchmark before the port. A port has to earn its place.
2. **Port into a crate.** Put the logic in a pure-Rust crate here, with its own unit tests. Do not put logic in `py/`.
3. **Bind it.** Expose it from `py/src/lib.rs` under the same name as the Python function.
4. **Keep the reference.** Keep the Python function, renamed `<name>_py`. Pin parity in `tests/test_accel_parity.py`, especially on edge cases.
5. **Route it.** Resolve the function through `core.foundation.accel.rust("<name>")` once, at import, and fall back to Python when it returns `None`.

The version lives in `[workspace.package]` in `Cargo.toml`. `scripts/release/releases.py bump X.Y.Z` keeps it in step with the launcher.
