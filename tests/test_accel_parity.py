"""The Rust accelerators (aurora-rs/, module aurora_rs) must return what Python returns.

core/foundation/accel.py swaps a Rust function in only when the optional akashic-aurora-rs
wheel is installed; Python stays the reference. These pins hold the two to the same output
on the inputs that are easy to get wrong: suffix folding at the 4-character floor, the word
class boundary, and Unicode lowercasing before an ASCII match. Without the wheel the Rust
cases skip and the fallback case still runs.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation import accel
from core.learning import learning_store as ls

CASES = [
    "",
    "Redis-backed CACHE, v2_final!",
    "salience promotion consolidation tracks",
    "statement state states stated stating",
    "uses used ions ation ences",  # stems shorter than 4 characters stay whole
    "\N{KELVIN SIGN}elvin café naïve ÉCOLE straße",
    "path/to/core/learning_store.py::_tokens_of -- line 220",
    "a" * 300 + " " + "b_" * 50,
    "Tab\tnew\nline\r\nmixed   spacing",
]


@pytest.fixture
def rs():
    mod = accel.module()
    if mod is None:
        pytest.skip("akashic-aurora-rs is not installed (optional; see aurora-rs/README.md)")
    return mod


@pytest.mark.parametrize("text", CASES)
def test_tokens_of_matches_python(rs, text):
    assert rs.tokens_of(text) == ls._tokens_of_py(text)


@pytest.mark.parametrize("word", ["tracks", "promotion", "statement", "state", "uses", "ab", "ences", "xxxxing"])
def test_stem_matches_python(rs, word):
    assert rs.stem(word) == ls._stem(word)


def test_tokens_of_always_answers():
    """Whichever implementation is live, the public function gives the reference result."""
    for text in CASES:
        assert ls._tokens_of(text) == ls._tokens_of_py(text)


def test_status_names_the_live_path():
    assert accel.status().startswith("rust accel: ")
