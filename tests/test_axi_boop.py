"""Pins for `boop` after the AXI conversion: still tiny, still always answered.

Run: uv run pytest tests/test_axi_boop.py -q
"""

import argparse

import agent_cli
from core.coord.observations import Observation, Snapshot


def _boop(capsys, surface=False, agent_id=""):
    code = agent_cli.cmd_boop(argparse.Namespace(surface=surface, agent_id=agent_id))
    return code, capsys.readouterr().out


def test_a_boop_is_two_fields_and_no_hint(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    code, text = _boop(capsys)
    assert code == 0
    assert text == "boop: received\nadjudicated: useful\n"


def test_surface_nests_the_sweep(capsys, monkeypatch):
    from core.comm import awareness

    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    bus = Observation(
        name="bus",
        subject="s1",
        status="OK",
        summary="2 pending",
        source=("fixture",),
        total=2,
        total_relation="exact",
        drill="bifrost-sync s1 --digest",
    )
    monkeypatch.setattr(
        awareness, "build_snapshot", lambda s: Snapshot(kind="awareness", subject=s, observations=(bus,))
    )
    _, text = _boop(capsys, surface=True, agent_id="s1")
    assert "sweep:\n  subject: s1" in text
    assert "  pending: 2" in text
    assert "bifrost-sync s1 --digest" in text


def test_surface_without_a_subject_is_a_usage_error(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    code, text = _boop(capsys, surface=True)
    assert code == 2
    assert "code: USAGE" in text


def test_human_boop_keeps_its_line(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _boop(capsys)
    assert text.startswith("boop. (received, subject-labeled, adjudicated USEFUL")
