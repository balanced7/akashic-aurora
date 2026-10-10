"""accel -- optional Rust implementations of hot paths, with Python as the reference.

The Rust lives in aurora-rs/ (a Cargo workspace, modelled on openai/codex's codex-rs/) and
ships as the akashic-aurora-rs wheel, module `aurora_rs`. Nothing requires it: `uv sync`
never builds Rust, and every caller keeps its pure-Python implementation. A function is
swapped in only when the module imports AND exports it, so an older wheel missing a newer
function degrades to Python for that function alone.

THE CONTRACT for moving a hot path to Rust (aurora-rs/README.md has the steps):
  1. Measure first. A port earns its place by a benchmark, not a hunch.
  2. Port into a pure-Rust crate with its own tests, then bind it in aurora-rs/py.
  3. Keep the Python function as the reference and pin parity in tests/test_accel_parity.py.
  4. Route through `rust(name)` here, so a missing wheel is never an error.

AURORA_NO_RUST=1 forces the Python path (for parity tests, benchmarks and bisecting).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

_mod: Any = None
_tried = False


def module() -> Any:
    """The `aurora_rs` extension module, or None when it is absent or switched off."""
    global _mod, _tried
    if os.environ.get("AURORA_NO_RUST"):
        return None
    if not _tried:
        _tried = True
        try:
            import aurora_rs  # pyright: ignore[reportMissingImports]  # optional wheel (aurora-rs/py)

            _mod = aurora_rs
        except ImportError:
            _mod = None
    return _mod


def rust(name: str) -> Callable[..., Any] | None:
    """The Rust implementation of `name`, or None (use the Python one)."""
    mod = module()
    return getattr(mod, name, None) if mod is not None else None


def status() -> str:
    """One line for `doctor`-style reports: which implementation is live."""
    mod = module()
    if mod is None:
        why = "AURORA_NO_RUST is set" if os.environ.get("AURORA_NO_RUST") else "akashic-aurora-rs not installed"
        return f"rust accel: off ({why}); pure-Python paths in use"
    return f"rust accel: on (aurora_rs {getattr(mod, '__version__', '?')})"
