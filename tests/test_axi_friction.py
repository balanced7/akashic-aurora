"""Pins for `friction` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_friction.py -q
"""

import argparse

import pytest

import agent_cli
from core.comm import friction

NOW = 1_800_000_000.0


def _terminal(kind, ask, to, created, at, **detail):
    from datetime import UTC, datetime

    return {
        "kind": kind,
        "refs": [ask],
        "at": datetime.fromtimestamp(at, UTC).isoformat(),
        "detail": {"to": to, "created": created, **detail},
    }


@pytest.fixture
def report(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    state: dict = {"events": [], "open": {}}

    def fake_gather(agent, window_h=168):
        return friction.fold(state["events"], state["open"], now=NOW)

    monkeypatch.setattr(friction, "gather", fake_gather)
    return state


def _run(capsys, agent="bench", **kw):
    ns = argparse.Namespace(agent_id=agent, window_h=168.0, json=False, limit=20)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_friction(ns)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_counts_peers_and_open_asks_first(report, capsys):
    report["events"] = [
        _terminal("expectation_settled_answered", "a-1", "alice", NOW - 100, NOW - 40),
        _terminal(
            "expectation_dead", "a-2", "carol", NOW - 900, NOW - 10, peer_at_ask="ATTENDED", peer_at_death="ATTENDED"
        ),
    ]
    report["open"] = {"a-3": {"to": "bob", "attempt": 1, "created": NOW - 30, "deadline_ts": NOW + 60}}
    code, text, err = _run(capsys)
    assert code == 0
    assert "open: 1\nanswered: 1\necho: 0\ndead: 1\ndead_rate: 0.5" in text
    assert "dead_by_reason[1]{reason,count,action}:" in text
    assert "ignored,1," in text
    assert "peers[3]{peer,open,answered,dead,dead_rate}:" in text
    assert text.index("carol,0,0,1,1") < text.index("alice,0,1,0,0")  # worst peer first
    assert "asks[3]{ask_id,peer,status,secs,redrives}:" in text
    assert text.index("a-3,bob,open (redriving)") < text.index("a-1,alice,answered")
    assert "dead (ignored)" in text
    assert "bifrost-sync bench" in text
    assert "blind (what this reader cannot see):" in err  # the confession stays on stderr
    assert "blind" not in text


def test_nothing_closed_is_an_explicit_zero_with_a_null_rate(report, capsys):
    code, text, _ = _run(capsys, agent="nobody")
    assert code == 0
    assert "open: 0\nanswered: 0" in text
    assert "dead_rate: null" in text
    assert "episodes: 0\nasks: []" in text
    assert "friction nobody --window-h 672" in text


def test_a_cut_list_gives_the_total_and_how_to_see_the_rest(report, capsys):
    report["open"] = {f"o-{i}": {"to": "bob", "created": NOW - i, "deadline_ts": NOW + 60} for i in range(5)}
    _, text, _ = _run(capsys, limit=2)
    assert "episodes: 5\nshown: 2" in text
    assert "friction bench --limit 5" in text


def test_human_view_leads_with_the_counts(report, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    report["events"] = [_terminal("expectation_settled_answered", "a-1", "alice", NOW - 100, NOW - 40)]
    _, text, _ = _run(capsys)
    assert "0 open  1 answered  0 echo  0 dead   dead rate 0%" in text
    assert "by peer (worst first)" in text
    assert "median 60s" in text
