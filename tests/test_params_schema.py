"""The param schema's Python twin (arsenal/params.py) against the shared fixture.

Why: one descriptor describes a knob everywhere it appears -- the GLSL uniform, the slider, the URL, the preset -- and the
browser twin (arsenal/web/lib/params.js, tests/params_schema.test.mjs) reads the same fixture. If the two twins disagree
on a verdict, a preset saved on one side is refused or silently changed on the other. Every expectation lives in
tests/fixtures/params/verdicts.json; this file only runs them, plus the node test when node is installed.
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import params as P  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "params"
D = json.loads((FIX / "descriptors.json").read_text(encoding="utf-8"))
V = json.loads((FIX / "verdicts.json").read_text(encoding="utf-8"))
SETS = D["sets"]
SENTINEL = {"__NaN__": math.nan, "__Inf__": math.inf, "__-Inf__": -math.inf}
NODE = shutil.which("node")


def revive(v):
    """The fixture spells NaN and the infinities as strings; swap them in."""
    if isinstance(v, str) and v in SENTINEL:
        return SENTINEL[v]
    if isinstance(v, list):
        return [revive(x) for x in v]
    if isinstance(v, dict):
        return {k: revive(x) for k, x in v.items()}
    return v


def same(a, b):
    """Strict equality: a bool never equals a number (Python's True == 1 would hide a twin disagreement), -0.0 must have
    been normalised to 0.0 by the twin, NaN equals NaN."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        if a == 0 and b == 0:
            return math.copysign(1.0, a) == math.copysign(1.0, b)
        return a == b
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and sorted(a) == sorted(b) and all(same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def by_id(set_name, pid):
    return next(d for d in SETS[set_name] if d["id"] == pid)


def pairs(problems):
    return [[p["id"], p["code"]] for p in problems]


def ids(cases, key="name"):
    return [str(c.get(key, i)) if isinstance(c, dict) else str(c[:3]) for i, c in enumerate(cases)]


def short(text, n=60):
    """A test id short enough to read (some fixture inputs are a 401-digit integer or 45 emoji)."""
    return text if len(text) <= n else text[:n] + "..."


# ---------------------------------------------------------------------------------------------------- validate --
@pytest.mark.parametrize("case", V["validate"], ids=ids(V["validate"]))
def test_validate_matches_the_fixture(case):
    r = P.validate(SETS[case["set"]], revive(case["values"]))
    want = revive({**V["defaults"][case["set"]], **case["patch"]})
    assert r["ok"] is case["ok"]
    assert same(r["values"], want), (r["values"], want)
    assert pairs(r["problems"]) == case["problems"]
    assert all(isinstance(p["message"], str) and p["message"] for p in r["problems"])


@pytest.mark.parametrize("case", V["messages"], ids=[short(json.dumps(c["values"], ensure_ascii=False)) for c in V["messages"]])
def test_problem_messages_match_the_fixture_word_for_word(case):
    r = P.validate(SETS[case["set"]], revive(case["values"]))
    assert [[p["id"], p["code"], p["message"]] for p in r["problems"]] == case["problems"]


def test_validate_leaves_its_input_alone():
    values = {"intensity": 5, "offset": [3, -3]}
    P.validate(SETS["core"], values)
    assert values == {"intensity": 5, "offset": [3, -3]}


def test_validate_value_snaps_one_value_and_refuses_a_bad_toggle():
    one = P.validate_value(by_id("core", "intensity"), 0.333)
    assert one["value"] == 0.33 and one["problem"] is None
    bad = P.validate_value(by_id("core", "rays"), "yes")
    assert bad["value"] is True and bad["problem"]["code"] == "type"


def test_integer_grids_come_back_as_ints_for_python_callers():
    r = P.validate(SETS["core"], {"layers": 30.2, "angle": 44.6})
    assert type(r["values"]["layers"]) is int and r["values"]["layers"] == 30
    assert type(r["values"]["angle"]) is int and r["values"]["angle"] == 45


# --------------------------------------------------------------------------------------------------- URL codec --
@pytest.mark.parametrize("case", V["encode"], ids=[c["query"] or "(empty)" for c in V["encode"]])
def test_encode_matches_the_fixture(case):
    assert P.encode(SETS[case["set"]], revive(case["values"]), all=case["all"]) == case["query"]


@pytest.mark.parametrize("case", V["decode"], ids=[c["query"] or "(empty)" for c in V["decode"]])
def test_decode_matches_the_fixture(case):
    got = P.decode(SETS[case["set"]], case["query"])
    assert same(got, revive(case["values"])), got
    if "verdict" in case:
        r = P.from_url(SETS[case["set"]], case["query"])
        assert r["ok"] is case["verdict"]["ok"]
        assert pairs(r["problems"]) == case["verdict"]["problems"]


@pytest.mark.parametrize("case", V["roundtrip"], ids=[json.dumps(c["values"], ensure_ascii=False) for c in V["roundtrip"]])
def test_the_url_codec_round_trips_validated_values(case):
    descriptors, values = SETS[case["set"]], revive(case["values"])
    want = P.validate(descriptors, values)["values"]
    assert same(P.from_url(descriptors, P.encode(descriptors, values))["values"], want)
    assert same(P.from_url(descriptors, P.encode(descriptors, values, all=True))["values"], want)


# --------------------------------------------------------------------------------------------------- formatter --
@pytest.mark.parametrize("row", V["format"], ids=[f"{r[1]}={json.dumps(r[2])}" for r in V["format"]])
def test_the_formatter_matches_the_fixture(row):
    set_name, pid, value, text, unit, joined = row
    d = by_id(set_name, pid)
    assert P.format_parts(d, revive(value)) == {"text": text, "unit": unit}
    assert P.format_value(d, revive(value)) == joined


# ----------------------------------------------------------------------------------------------- slider curves --
@pytest.mark.parametrize("row", V["curves"]["to_value"], ids=[f"{r[1]}@{r[2]}" for r in V["curves"]["to_value"]])
def test_position_to_value(row):
    set_name, pid, p, v = row
    got = P.position_to_value(by_id(set_name, pid), p)
    assert abs(got - v) <= V["curves"]["tolerance"] * max(1.0, abs(v)), got


@pytest.mark.parametrize("row", V["curves"]["to_position"], ids=[f"{r[1]}={r[2]}" for r in V["curves"]["to_position"]])
def test_value_to_position(row):
    set_name, pid, v, p = row
    got = P.value_to_position(by_id(set_name, pid), v)
    assert abs(got - p) <= V["curves"]["tolerance"], got


def test_every_curve_round_trips():
    for d in (x for x in SETS["units"] if x["type"] == "range"):
        worst = max(abs(P.value_to_position(d, P.position_to_value(d, i / 20)) - i / 20) for i in range(21))
        assert worst < 1e-9, (d["id"], worst)


# ------------------------------------------------------------------------------------------ descriptor checks --
@pytest.mark.parametrize("case", V["check"], ids=ids(V["check"]))
def test_check_descriptors_matches_the_fixture(case):
    descriptors = SETS[case["set"]] if "set" in case else case["descriptors"]
    assert pairs(P.check_descriptors(descriptors)) == case["problems"]


# Built the same way in tests/params_schema.test.mjs: this twin used to recurse until it crashed on these.
@pytest.mark.parametrize("expr", ["-" * 1200 + "a", "a" + "+a" * 1999], ids=["1200 minus signs", "a 2000-term sum"])
def test_expressions_far_past_the_token_cap_are_a_problem_not_a_crash(expr):
    descriptors = [SETS["deep"][0], {**SETS["deep"][1], "derived": expr}]
    assert pairs(P.validate(descriptors, {})["problems"]) == [["atCap", "derived"]]
    assert pairs(P.check_descriptors(descriptors)) == [["atCap", "derived"]]


# --------------------------------------------------------------------------------------- params from a module --
@pytest.mark.parametrize("case", V["modules"], ids=[f"{c['header']}@{c['instance']}" for c in V["modules"]])
def test_params_from_module_matches_the_fixture(case):
    header = D["headers"][case["header"]]
    got = P.params_from_module(header, case["instance"])
    if "rows" in case:
        assert [[d["id"], d["uniform"], d["type"], d["unit"], d["group"], d["order"], d["cost"]] for d in got] == case["rows"]
    if "full" in case:
        assert same(got, case["full"]), got
    if "derived" in case:
        assert {d["id"]: d["derived"] for d in got if d["derived"]} == case["derived"]
    assert P.check_descriptors(got) == []
    assert same(P.params_from_module(header, case["instance"]), got)
    if "validate" in case:
        r = P.validate(got, case["validate"]["values"])
        assert r["ok"] is case["validate"]["ok"]
        assert same(r["values"], case["validate"]["expect"]), r["values"]


@pytest.mark.parametrize("row", V["module_errors"], ids=[repr(r[1]) for r in V["module_errors"]])
def test_params_from_module_refuses_a_bad_instance_id(row):
    with pytest.raises(ValueError):
        P.params_from_module(D["headers"][row[0]], row[1])


@pytest.mark.parametrize("case", V["module_checks"], ids=ids(V["module_checks"]))
def test_params_from_module_then_the_descriptor_check(case):
    assert pairs(P.check_descriptors(P.params_from_module(case["header"], case["instance"]))) == case["problems"]


@pytest.mark.parametrize("instance", [None, "a"])
@pytest.mark.parametrize("case", V["module_bad_headers"], ids=ids(V["module_bad_headers"]))
def test_params_from_module_refuses_a_param_without_a_name(case, instance):
    with pytest.raises(ValueError):
        P.params_from_module(case["header"], instance)


def test_two_instances_never_share_a_uniform():
    a = {d["uniform"] for d in P.params_from_module(D["headers"]["aurora-sheets"], "a")}
    b = {d["uniform"] for d in P.params_from_module(D["headers"]["aurora-sheets"], "b")}
    assert not a & b


def test_the_refusal_text_is_the_house_text():
    registry = (ROOT / "arsenal" / "web" / "piano" / "looks" / "registry.js").read_text(encoding="utf-8")
    assert f'export const REC_BLOCKED = "{P.REC_REFUSAL_TEXT}";' in registry


# ------------------------------------------------------------------------------------------ the browser twin --
@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_browser_twin_agrees_on_the_same_fixture():
    res = subprocess.run([NODE, str(ROOT / "tests" / "params_schema.test.mjs")], capture_output=True, text=True,
                         encoding="utf-8", cwd=str(ROOT), timeout=120)
    assert res.returncode == 0, (res.stdout + res.stderr)[-4000:]
    assert " 0 failed" in res.stdout
