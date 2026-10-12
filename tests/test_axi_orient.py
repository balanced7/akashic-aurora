"""Pins for `orient` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_orient.py -q
"""

import argparse
import re
import sys

import pytest

import agent_cli


def _row(name, status="OK", summary="fine"):
    return {"name": name, "status": status, "summary": summary}


def _scene(focus=None, blind=()):
    return {
        "subject": "s1",
        "target": {"address": "verb:recall"} if focus else None,
        "aperture": {"density": "compact", "depth": "surface"},
        "focus": focus,
        "nearby": [_row("bus", summary="3 pending")],
        "periphery": [_row("bench"), _row("route", "UNATTENDED", "no beat")],
        "routes": [{"name": "return", "steps": [{"verb": "sweep", "args": {"agent": "s1"}}]}],
        "blind": list(blind),
        "effects": [],
    }


@pytest.fixture
def scene(monkeypatch):
    from core.coord import orient

    holder = {"scene": _scene()}

    def build(subject, target, **kw):
        if target.startswith("bogus"):
            raise ValueError("unsupported orient destination kind 'bogus'")
        return holder["scene"]

    monkeypatch.setattr(orient, "build_orientation", build)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _orient(capsys, target=""):
    ns = argparse.Namespace(agent="s1", target=target, density="compact", depth="surface", per_stream=1000, json=False)
    code = agent_cli.cmd_orient(ns)
    return code, capsys.readouterr().out


def test_ambient_scene_lists_every_landmark_with_its_place(scene, capsys):
    code, text = _orient(capsys)
    assert code == 0
    assert "focus: ambient awareness (no destination supplied)" in text
    assert "landmarks_total: 3" in text
    assert "landmarks[3]{name,place,status,summary}:" in text
    assert "route,contoured,UNATTENDED,no beat" in text
    assert "blind_total: 0" in text
    assert re.search(r"^return: .+ sweep s1$", text, re.MULTILINE)  # the way back, as a command


def test_focus_carries_truth_values_blind_spots_and_its_drill(scene, capsys):
    epi = {"authority": {"value": "mechanical_source"}, "risk": {"value": "ordinary"}}
    scene["scene"] = _scene(
        focus={"summary": "declared=observed", "epistemic": epi, "folded": {"fields": 8}, "drill": "x --report"},
        blind=["no receipt resolver"],
    )
    _, text = _orient(capsys, "verb:recall")
    assert "  authority: mechanical_source" in text
    assert "  currency: unknown" in text
    assert "blind_total: 1" in text
    assert "no receipt resolver" in text
    assert "  x --report" in text


def test_a_bad_destination_is_a_usage_error(scene, capsys):
    code, text = _orient(capsys, "bogus:x")
    assert code == 2
    assert "code: USAGE" in text


def test_stdout_is_restored_when_a_provider_swaps_it(scene, capsys, monkeypatch):
    from core.coord import orient

    def swapping_build(subject, target, **kw):
        sys.stdout = sys.stderr  # what importing the MCP server does to this process
        return _scene()

    monkeypatch.setattr(orient, "build_orientation", swapping_build)
    _, text = _orient(capsys)
    assert "landmarks_total: 3" in text


def test_human_view(scene, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _orient(capsys)
    assert "focus ambient" in text
    assert "UNATTENDED" in text
