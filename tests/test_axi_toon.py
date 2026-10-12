"""TOON encoder conformance: the spec's own encode fixtures, run against core.axi.toon.

The fixtures in tests/fixtures/toon/encode are copied unchanged from
https://github.com/toon-format/spec (MIT, see tests/fixtures/toon/LICENSE), spec version 4.4.
A failing fixture means agent-mode output is not valid TOON, which an agent may misread.

Run: uv run pytest tests/test_axi_toon.py -q
"""

import datetime as dt
import json
from pathlib import Path

import pytest

from core.axi.toon import encode

FIXTURES = Path(__file__).parent / "fixtures" / "toon" / "encode"


def _cases():
    for path in sorted(FIXTURES.glob("*.json")):
        for case in json.loads(path.read_text(encoding="utf-8"))["tests"]:
            yield pytest.param(case, id=f"{path.stem}: {case['name']}")


@pytest.mark.parametrize("case", list(_cases()))
def test_spec_fixture(case):
    opts = case.get("options") or {}
    out = encode(case["input"], delimiter=opts.get("delimiter", ","), indent=opts.get("indentSize", 2))
    assert out == case["expected"]


def test_the_fixture_suite_is_present():
    assert len(list(_cases())) >= 160


def test_host_types_are_normalized():
    out = encode({"when": dt.date(2026, 10, 12), "tags": {"b", "a"}, "nan": float("nan"), "path": Path("x/y")})
    assert out == "when: 2026-10-12\ntags[2]: a,b\nnan: null\npath: x/y"


def test_bad_options_are_refused():
    with pytest.raises(ValueError, match="delimiter"):
        encode({}, delimiter=";")
    with pytest.raises(ValueError, match="indent"):
        encode({}, indent=0)
