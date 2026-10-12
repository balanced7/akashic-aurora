"""Pins for `sweep` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_sweep.py -q
"""

import argparse

import pytest

import agent_cli
from core.coord.observations import Observation, Snapshot

SUBJECT = "synthetic-seat-sweep"


def _snapshot(pending=0, attention=0, parked=0):
    rows = (
        Observation(
            name="bus",
            subject=SUBJECT,
            status="OK",
            summary=f"{pending} pending",
            source=("fixture",),
            total=pending,
            total_relation="exact",
            details={"attention_shown": attention},
            drill=f"bifrost-sync {SUBJECT} --digest",
        ),
        Observation(
            name="bench",
            subject=SUBJECT,
            status="OK",
            summary=f"{parked} parked",
            source=("fixture",),
            total=parked,
            total_relation="exact",
            drill=f"bench {SUBJECT}",
        ),
        Observation(name="route", subject=SUBJECT, status="UNATTENDED", summary="no beat", source=("fixture",)),
        Observation(
            name="moved", subject=SUBJECT, status="OK", summary="git=0", source=("fixture",), drill=f"delta {SUBJECT}"
        ),
    )
    return Snapshot(kind="awareness", subject=SUBJECT, observations=rows)


@pytest.fixture
def snap(monkeypatch):
    from core.comm import awareness

    holder = {"snap": _snapshot()}
    monkeypatch.setattr(awareness, "build_snapshot", lambda subject: holder["snap"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _sweep(capsys, agent_id=SUBJECT):
    code = agent_cli.cmd_sweep(argparse.Namespace(agent_id=agent_id, json=False))
    return code, capsys.readouterr().out


def test_counts_first_then_one_row_per_observation(snap, capsys):
    snap["snap"] = _snapshot(pending=3, attention=1)
    code, text = _sweep(capsys)
    assert code == 0
    assert "pending: 3\nneed_attention: 1\nparked: 0" in text
    assert "observations[4]{name,status,summary,drill}:" in text
    assert "route,UNATTENDED,no beat,null" in text
    assert f"bifrost-sync {SUBJECT} --digest" in text  # mail waiting: the drill is the next step


def test_a_quiet_seat_says_zero_and_offers_no_drill(snap, capsys):
    _, text = _sweep(capsys)
    assert "pending: 0" in text
    assert "help[" not in text


def test_missing_subject_is_a_usage_error(snap, capsys, monkeypatch):
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    code, text = _sweep(capsys, agent_id="")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(snap, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    snap["snap"] = _snapshot(pending=2, attention=0, parked=1)
    _, text = _sweep(capsys)
    assert "2 pending  0 need attention  1 parked" in text
    assert "UNATTENDED" in text
