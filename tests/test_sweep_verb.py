"""Hermetic CLI pins for the structured awareness snapshot."""
import argparse
import io
import json
from contextlib import redirect_stdout

import pytest

from core.coord.observations import Observation, Snapshot
from agent_cli import build_sweep


SUBJECT = "synthetic-seat-sweep"


def _provider(name, summary="ok"):
    return lambda subject: Observation(
        name=name,
        subject=subject,
        status="OK",
        summary=summary,
        source=(f"fixture:{name}",),
    )


def _providers(**overrides):
    got = {
        "bus": _provider("bus"),
        "bench": _provider("bench", "0 parked"),
        "route": _provider("route", "UNATTENDED"),
        "moved": _provider("moved", "git=0; ledger=0; notes=0; promoted=0"),
    }
    got.update(overrides)
    return got


def test_s1_all_four_sections_render_with_headers():
    out = build_sweep(SUBJECT, providers=_providers())
    for header in ("bus", "bench", "route", "moved"):
        assert f"{header}" in out
    assert f"subject={SUBJECT}" in out


def test_s2_broken_provider_fails_open_not_traceback():
    def _boom(_subject):
        raise RuntimeError("bus down")

    out = build_sweep(SUBJECT, providers=_providers(bus=_boom))
    assert "bus: UNAVAILABLE" in out
    assert "RuntimeError: bus down" in out
    assert "Traceback" not in out


def test_s3_block_is_bounded():
    out = build_sweep(SUBJECT, providers=_providers())
    assert len(out.splitlines()) <= 8


def test_s4_cli_refuses_an_implicit_foreign_identity(monkeypatch):
    import agent_cli

    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = agent_cli.cmd_sweep(argparse.Namespace(agent_id="", json=False))
    assert rc == 2
    assert "subject is required" in buf.getvalue()


def test_s5_toolbox_uses_bound_subject_without_shelling(monkeypatch):
    from core.comm import awareness
    from core.comm.toolbox import ToolBox

    seen = []

    def _snapshot(subject):
        seen.append(subject)
        return Snapshot(
            kind="awareness",
            subject=subject,
            observations=tuple(provider(subject) for provider in _providers().values()),
        )

    monkeypatch.setattr(awareness, "build_snapshot", _snapshot)
    belt = ToolBox.__new__(ToolBox)
    belt.agent_id = SUBJECT

    out = json.loads(belt.sweep())
    assert seen == [SUBJECT]
    assert out["subject"] == SUBJECT


def test_s6_unbound_toolbox_refuses_to_borrow_a_resident_identity():
    from core.comm.toolbox import ToolBox

    belt = ToolBox.__new__(ToolBox)
    belt.agent_id = None
    with pytest.raises(ValueError, match="subject"):
        belt.sweep()
