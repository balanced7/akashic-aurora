"""The aurora_rs wheel's fleet-link functions: pure, offline, and the daemon's own code (RFC #70
addendum §2.4). Skipped without a wheel that has them (`maturin develop -m aurora-rs/py/Cargo.toml`)."""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.foundation.accel import rust  # sys.path bootstrap
from core.link.kinds import BRIDGE_KINDS  # sys.path bootstrap


def _wheel(name: str) -> Callable[..., Any]:
    """The wheel's function, or a stand-in that skips the test when the wheel lacks it."""
    f = rust(name)

    def call(*args: Any, **kwargs: Any) -> Any:
        if f is None:
            pytest.skip(f"aurora_rs has no {name}")
        return f(*args, **kwargs)

    return call


verify_record = _wheel("verify_record")
_bridge_kinds = _wheel("bridge_kinds")
_fingerprint = _wheel("fingerprint")
_parse_invite = _wheel("parse_invite")
pytestmark = pytest.mark.skipif(rust("verify_record") is None, reason="aurora_rs without the link functions")


def test_the_wheel_enforces_the_same_allowlist():
    assert set(_bridge_kinds()) == set(BRIDGE_KINDS)


def test_fingerprints_and_safety_numbers():
    fp = _fingerprint
    a, b = "01" * 32, "02" * 32
    assert len(fp(a)) == 30
    assert fp(a).isdigit()
    assert fp(a, b) == fp(b, a)
    assert len(fp(a, b)) == 60
    with pytest.raises(ValueError, match="hex"):
        fp("not hex")


def test_parse_invite_never_returns_the_secret():
    with pytest.raises(ValueError, match="invite"):
        _parse_invite("aurora-invite1:@@@")


def test_verify_record_refuses_junk():
    with pytest.raises(ValueError, match="record"):
        verify_record(json.dumps({"v": 1}))


VECTORS = Path(__file__).resolve().parents[1] / "aurora-rs" / "link-vectors"


def test_the_wheel_agrees_with_the_record_vectors():
    cases = json.loads((VECTORS / "records.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["valid"]:
            assert verify_record(json.dumps(case["record"])) == case["id"], case["name"]
        else:
            with pytest.raises(ValueError, match="refused"):
                verify_record(json.dumps(case["record"]))


def test_the_wheel_agrees_with_the_fingerprint_vectors():
    v = json.loads((VECTORS / "fingerprints.json").read_text(encoding="utf-8"))
    assert _fingerprint(v["root"]) == v["fingerprint"]
    assert _fingerprint(v["root"], v["other"]) == v["safety_number"]
