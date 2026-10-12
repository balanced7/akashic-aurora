"""Pins for `packet-stats` after the AXI conversion: what an agent and a person see.

route_stats and the bus are stubbed, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_packet_stats.py -q
"""

import argparse

import pytest

import agent_cli


class _Bus:
    ns, _client = "test-ns", None

    def __init__(self, *a, **k):
        pass


def _stats(counts, online=True, stored="kind-lane:abc", matches=True):
    return {"online": online, "mode": "shadow", "policy_version": "kind-lane:abc", "stored_policy_version": stored,
            "policy_matches": matches, "started_at": "2026-10-12T10:00:00" if counts else "", "counts": counts,
            "counter_field_limit": 148}  # fmt: skip


@pytest.fixture
def stats(monkeypatch):
    import core.comm.bus as bus_mod
    import core.comm.router as router

    state = {"out": _stats({})}
    monkeypatch.setattr(bus_mod, "Bus", _Bus)
    monkeypatch.setattr(router, "route_stats", lambda client, ns: state["out"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _run(capsys):
    code = agent_cli.cmd_packet_stats(argparse.Namespace(json=False))
    return code, capsys.readouterr().out


def test_counters_pivot_to_one_row_per_kind_with_totals(stats, capsys):
    stats["out"] = _stats(
        {
            "decision:chat": 3,
            "mirror:chat:success": 2,
            "mirror:chat:failure": 1,
            "decision:handoff": 1,
            "mirror:handoff:success": 1,
        }
    )
    code, text = _run(capsys)
    assert code == 0
    assert "decisions: 4\nfailures: 1" in text
    assert "kinds[2]{kind,decisions,success,failure}:" in text
    assert "chat,3,2,1" in text
    assert "handoff,1,1,0" in text


def test_a_stored_policy_mismatch_is_named(stats, capsys):
    stats["out"] = _stats({"decision:chat": 1}, stored="kind-lane:old", matches=False)
    _, text = _run(capsys)
    assert "policy_matches: false" in text
    assert 'stored_policy: "kind-lane:old"' in text


def test_no_observations_is_an_explicit_zero(stats, capsys):
    stats["out"] = _stats({}, stored="")
    code, text = _run(capsys)
    assert code == 0
    assert "decisions: 0" in text
    assert "kinds: []" in text


def test_offline_is_a_structured_error(stats, capsys):
    stats["out"] = _stats({}, online=False)
    code, text = _run(capsys)
    assert code == 1
    assert "code: BUS_OFFLINE" in text


def test_human_view_totals_then_table(stats, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    stats["out"] = _stats({"decision:chat": 2, "mirror:chat:success": 2})
    _, text = _run(capsys)
    assert "2 decisions · 0 failures" in text
    assert "chat" in text
