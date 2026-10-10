"""The aurora_rs wheel's fleet-link functions: pure, offline, and the daemon's own code (RFC #70
addendum §2.4). Skipped without a wheel that has them (`maturin develop -m aurora-rs/py/Cargo.toml`)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.foundation.accel import rust  # sys.path bootstrap
from core.link.kinds import BRIDGE_KINDS  # sys.path bootstrap

verify_record = rust("verify_record")
_bridge_kinds = rust("bridge_kinds")
_fingerprint = rust("fingerprint")
_parse_invite = rust("parse_invite")
pytestmark = pytest.mark.skipif(verify_record is None, reason="aurora_rs without the link functions")


def test_the_wheel_enforces_the_same_allowlist():
    assert _bridge_kinds is not None
    assert set(_bridge_kinds()) == set(BRIDGE_KINDS)


def test_fingerprints_and_safety_numbers():
    fp = _fingerprint
    assert fp is not None
    a, b = "01" * 32, "02" * 32
    assert len(fp(a)) == 30
    assert fp(a).isdigit()
    assert fp(a, b) == fp(b, a)
    assert len(fp(a, b)) == 60
    with pytest.raises(ValueError, match="hex"):
        fp("not hex")


def test_parse_invite_never_returns_the_secret():
    with pytest.raises(ValueError, match="invite"):
        _parse_invite("aurora-invite1:@@@")  # pyright: ignore[reportOptionalCall]  # skipped when absent


def test_verify_record_refuses_junk():
    with pytest.raises(ValueError, match="record"):
        verify_record(json.dumps({"v": 1}))  # pyright: ignore[reportOptionalCall]  # skipped when absent


VECTORS = Path(__file__).resolve().parents[1] / "aurora-rs" / "link-vectors"


def test_the_wheel_agrees_with_the_record_vectors():
    cases = json.loads((VECTORS / "records.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["valid"]:
            assert verify_record(json.dumps(case["record"])) == case["id"], case["name"]  # pyright: ignore[reportOptionalCall]  # skipped when absent
        else:
            with pytest.raises(ValueError, match="refused"):
                verify_record(json.dumps(case["record"]))  # pyright: ignore[reportOptionalCall]  # skipped when absent


def test_the_wheel_agrees_with_the_fingerprint_vectors():
    v = json.loads((VECTORS / "fingerprints.json").read_text(encoding="utf-8"))
    assert _fingerprint is not None
    assert _fingerprint(v["root"]) == v["fingerprint"]
    assert _fingerprint(v["root"], v["other"]) == v["safety_number"]
