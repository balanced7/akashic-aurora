"""present.scene.v1 pins: the validator refuses what the family says it refuses, the seven
present.* manifests load through arsenal.registry, and every one of them covers every atom kind
a scene uses (invariant I6). Pure-Python; no Redis, no renderer, no network.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import arsenal.present as present
from arsenal.present import scene as sc
from arsenal.registry import load_registry

_FIXTURE_SCENE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "present" / "mail-and-wake-v2.scene.json"
_OVERRIDE_SCENE = os.environ.get("PRESENT_SCENE")
SCRATCH_SCENE = Path(_OVERRIDE_SCENE) if _OVERRIDE_SCENE and Path(_OVERRIDE_SCENE).exists() else _FIXTURE_SCENE


def _diagram():
    return {
        "kind": "diagram",
        "region": "host",
        "host": {"w": 1664, "h": 700},
        "nodes": [
            {"id": "a", "x": 0, "y": 0, "w": 300, "h": 120, "text": "1  one"},
            {"id": "b", "x": 400, "y": 0, "w": 300, "h": 120, "text": "2  two", "tone": "ghost"},
        ],
        "edges": [{"from": "a", "to": "b", "route": "straight", "head": "end"}],
        "labels": [{"id": "l", "x": 0, "y": 600, "w": 800, "text": "a label", "for": "a"}],
    }


def _scene():
    return {
        "schema": sc.SCHEMA,
        "title": "pin deck",
        "order": ["one", "two"],
        "sections": {"s1": {"description": "one sentence", "start": "one"}},
        "slides": [
            {
                "id": "one",
                "template": "content",
                "background": "light",
                "atoms": [
                    {"kind": "headline", "region": "heading", "text": "A heading", "role": "h2"},
                    {
                        "kind": "group",
                        "region": "body",
                        "arrangement": "row",
                        "items": [
                            {"kind": "number", "value": "47", "caption": "first read", "scale": "hero", "tone": "muted"}
                        ],
                    },
                    {
                        "kind": "statement",
                        "region": "kicker",
                        "role": "kicker",
                        "runs": [{"text": "a kicker", "mark": "plain"}],
                    },
                    {"kind": "receipt", "region": "footer", "text": "file.py:1"},
                    {"kind": "note", "region": "note", "script": "spoken words"},
                ],
            },
            {
                "id": "two",
                "template": "diagram",
                "background": "light",
                "atoms": [
                    {"kind": "headline", "region": "heading", "text": "A diagram", "role": "h2"},
                    _diagram(),
                    {"kind": "receipt", "region": "footer", "text": "file.py:2"},
                    {
                        "kind": "note",
                        "region": "note",
                        "script": "more words",
                        "cues": [{"atom_id": "b", "text": "ghost"}],
                    },
                ],
            },
        ],
    }


def test_schema_is_one_string_everywhere():
    assert present.SCHEMA == sc.SCHEMA == "present.scene.v1"


def test_family_constants_are_enumerable():
    assert len(sc.ATOM_KINDS) == 15 and "note" in sc.ATOM_KINDS
    assert set(sc.TEMPLATES) == {"cover", "section", "statement", "content", "diagram", "comparison", "closing"}
    for tpl in sc.TEMPLATES.values():
        assert any(r["name"] == "note" for r in tpl["regions"]), "every template carries a note region"
    assert "ghost" in sc.TOKEN_ROLES["tone"]


def test_minimal_scene_validates_clean():
    assert sc.validate(_scene()) == []
    assert sc.lint(_scene()) == []


@pytest.mark.parametrize(
    "mutate, code",
    [
        (
            lambda s: s["slides"][0]["atoms"].insert(0, {"kind": "sticker", "region": "body", "text": "x"}),
            "E01 unknown atom kind",
        ),
        (
            lambda s: s["slides"][0]["atoms"].__setitem__(0, {"kind": "diagram", "region": "heading", **_diagram()}),
            "E02",
        ),
        (
            lambda s: s["slides"][0]["atoms"][2]["runs"].__setitem__(0, {"text": "set it to 24px", "mark": "plain"}),
            "E03 target unit",
        ),
        (lambda s: s["slides"][0]["atoms"][0].__setitem__("color", "#fff"), "E03 key 'color'"),
        (
            lambda s: s["slides"][0]["atoms"].__setitem__(
                0, {"kind": "headline", "region": "heading", "payload": '{"text":"x"}'}
            ),
            "E03 payload is a JSON string",
        ),
        (lambda s: s["slides"][1]["atoms"][1].__setitem__("src", "planes.png"), "E04"),
        (lambda s: s["slides"][1]["atoms"][1].update({"nodes": [], "paths": []}), "E04 diagram draws nothing"),
        (lambda s: s["slides"][0]["atoms"].pop(), "E05 no note"),
        (lambda s: s["slides"][0]["atoms"].insert(0, {"kind": "note", "region": "note", "script": "twice"}), "E05"),
        (
            lambda s: (
                s["slides"][0]["atoms"][3].__setitem__("id", "dup")
                or s["slides"][0]["atoms"][2].__setitem__("id", "dup")
            ),
            "E06 duplicate id",
        ),
        (lambda s: s["order"].append("ghost-slide"), "E06 order names an unknown slide"),
        (lambda s: s["order"].pop(), "E06 slide 'two' is not in order"),
        (lambda s: s["sections"]["s1"].__setitem__("start", "nope"), "E06 section"),
        (lambda s: s["slides"][1]["atoms"][1]["edges"][0].__setitem__("to", "zzz"), "E07"),
        (lambda s: s["slides"][1]["atoms"][1]["nodes"][0].__setitem__("x", 1500), "E03 node 'a' box"),
        (
            lambda s: s["slides"][0]["atoms"][1]["items"].append({"kind": "group", "arrangement": "row", "items": []}),
            "E09",
        ),
        (lambda s: s["slides"][0].__setitem__("background", "#F6F7F5"), "E01 background"),
    ],
)
def test_refusals_fire(mutate, code):
    s = _scene()
    mutate(s)
    problems = sc.validate(s)
    assert any(code in p for p in problems), (code, problems)


def test_table_shares_must_sum_to_100():
    s = _scene()
    s["slides"][0]["atoms"].insert(
        1,
        {
            "kind": "table",
            "region": "body",
            "role": "caption",
            "columns": [{"title": "A", "share": 50}, {"title": "B", "share": 40}],
            "rows": [[[{"text": "x"}], [{"text": "y"}]]],
        },
    )
    assert any("E08 column shares sum to 90" in p for p in sc.validate(s))


def test_code_lines_are_exempt_from_the_unit_scan():
    s = _scene()
    s["slides"][0]["atoms"].insert(1, {"kind": "code", "region": "body", "lines": ["width: 1664px;"]})
    assert sc.validate(s) == []


def test_lint_flags_craft_limits_without_refusing():
    s = _scene()
    s["slides"][1]["atoms"][0]["text"] = "x" * 39
    s["slides"][1]["atoms"][1]["nodes"][0]["text"] = "see bifrost_wake.py:404"
    s["slides"][1]["atoms"][3]["cues"].append({"atom_id": "nowhere", "text": "?"})
    s["slides"][1]["duration_s"] = 1
    assert sc.validate(s) == []
    codes = {w.split(": ")[1][:3] for w in sc.lint(s)}
    assert {"W01", "W05", "W06", "W07"} <= codes


def test_present_manifests_load_and_cover_every_kind():
    reg = load_registry()
    ids = [m for m in reg.ids() if m.startswith("present.")]
    assert set(ids) == {
        "present.slides-html",
        "present.pdf",
        "present.sequence",
        "present.video",
        "present.ui-element",
        "present.three-js",
        "present.3d-viz",
    }
    full = _scene()
    for mid in ids:
        m = reg.get(mid)
        assert m.get("status") in ("designed", "building", "exists")
        assert sc.coverage(full, m) == []
        for kind in sc.ATOM_KINDS:  # I6 for the whole family, not just this scene
            row = m["atoms"].get(kind)
            assert row and (row.get("preserves") or row.get("degrades") or row.get("drops")), (mid, kind)
        if m["status"] == "exists":
            assert m["receipts"], f"{mid}: exists needs a receipt (a module without one is presumed broken)"


def test_coverage_refuses_a_target_that_names_neither():
    problems = sc.coverage(_scene(), {"id": "present.nothing", "atoms": {"headline": {"preserves": "full"}}})
    assert problems and all("names neither" in p for p in problems)


@pytest.mark.skipif(
    not SCRATCH_SCENE.exists(), reason="no Mail-and-Wake scene at PRESENT_SCENE or in tests/fixtures/present"
)
def test_mail_and_wake_scene_validates():
    scene = sc.load(SCRATCH_SCENE)
    assert scene["schema"] == sc.SCHEMA and len(scene["slides"]) == 22
    assert sc.validate(scene) == []
    assert sc.lint(scene) == []
    reg = load_registry()
    for mid in reg.ids():
        if mid.startswith("present."):
            assert sc.coverage(scene, reg.get(mid)) == []
