"""The shared cadence fixtures (tests/fixtures/cadence_cases.json) say what arsenal.practice._cadence says.

Every case is SYNTHETIC (an invented progression). Each is built into practice-style row dicts (one shared area dict per
area id, so area identity is Python `is`, as practice compares it) and judged by practice._cadence itself; the expected
kind and chain bounds are the ones arsenal/web/piano/cadence-live.js must reproduce (tests/piano_cadence_live.test.mjs).
"""
import json
from pathlib import Path

import pytest

from arsenal import practice

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cadence_cases.json"
CASES = json.loads(FIXTURES.read_text(encoding="utf-8"))
NEUTRAL = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _rows(case):
    areas = {a["id"]: {"tonic": a["tonic"], "mode": a["mode"], "key": a["key"]} for a in case["areas"]}
    rows = []
    for i, w in enumerate(case["windows"]):
        area = areas[w["area"]] if w["area"] is not None else None
        name = "-".join(NEUTRAL[p] for p in w["pcs"])
        row = {
            "i": i, "start_ms": w["start_ms"], "end_ms": w["end_ms"], "at": w["at"],
            "seconds": (w["end_ms"] - w["start_ms"]) / 1000,
            "name": name, "label": None, "analysed_as": None, "number": None,
            "third": w["third"], "key": area["key"] if area else None,
            "bass": {"note": f"{NEUTRAL[w['bass_pc']]}2" if w["bass_pc"] is not None else None},
            "_pcs": set(w["pcs"]), "_root_pc": w["root_pc"], "_area": area, "_bass_pc": w["bass_pc"],
            "_low_bass": w["low_bass"],
        }
        if "texture" in w:  # a window without the key exercises w.get("texture", "chord")
            row["texture"] = w["texture"]
        rows.append(row)
    return rows


def test_fixture_count_and_shape():
    assert len(CASES) >= 24
    for case in CASES:
        for w in case["windows"]:
            assert w["mask"] == sum(1 << p for p in w["pcs"]), case["name"]
            assert w["pcs"] == sorted(set(w["pcs"])), case["name"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture_matches_practice_cadence(case):
    rows = _rows(case)
    got = practice._cadence(rows, case["n"])
    expect = case["expect"]
    if expect is None:
        assert got is None, f"practice found {got and got['kind']!r}"
        return
    assert got is not None, f"practice found no cadence, the fixture expects {expect['kind']!r}"
    assert got["kind"] == expect["kind"]
    ws = case["windows"]
    assert got["start_ms"] == ws[expect["first"]]["start_ms"]
    assert got["end_ms"] == ws[expect["last"]]["end_ms"]
    assert got["at"] == ws[expect["first"]]["at"]
    assert len(got["chords"]) in (2, 3)  # the chain is [a, b], [prev, a, b] or [a, b, nxt]: passing moments are left out
