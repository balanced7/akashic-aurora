"""Pins for `bifrost-skip-to-now` after the AXI conversion: the audit as fields, one row per cursor.

Offline: cursor_admin.skip_to_now is stubbed.
Run: uv run pytest tests/test_axi_bifrost_skip_to_now.py -q
"""

import json
import types

import pytest

import agent_cli

_DONE = {
    "ok": True,
    "agent": "deepseek",
    "before": {"shared": {"inbox": "0", "bc": "5-0"}, "lane": {"inbox": "0"}},
    "after": {
        "shared": {"inbox": "9-0", "bc": "5-0"},
        "lane": {"inbox": "8-0"},
        "advance": {"shared": "OK", "lane": "OK"},
    },
    "refused": "",
}


@pytest.fixture
def admin(monkeypatch):
    from core.comm import cursor_admin

    state = {"res": dict(_DONE)}
    monkeypatch.setattr(cursor_admin, "skip_to_now", lambda agent, by, reason: state["res"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _skip(capsys, json_out=False):
    ns = types.SimpleNamespace(agent_id="deepseek", by="claude", reason="echo storm", json=json_out)
    return agent_cli.cmd_bifrost_skip_to_now(ns), capsys.readouterr().out


def test_a_skip_lists_each_moved_cursor(admin, capsys):
    code, text = _skip(capsys)
    assert code == 0
    assert text.startswith("agent: deepseek\nstatus: skipped to now\nshared: OK\nlane: OK\naudited: true\n")
    assert "moved[2]{cursor,from,to}:" in text
    assert 'shared.inbox,"0",9-0' in text
    assert 'lane.inbox,"0",8-0' in text
    assert "bifrost-resume" in text


def test_a_refusal_says_to_pause_first_and_exits_2(admin, capsys):
    admin["res"] = {"ok": False, "refused": "fleet not paused -- run bifrost-pause first"}
    code, text = _skip(capsys)
    assert code == 2
    assert "code: REFUSED" in text
    assert "skipped: false" in text
    assert "bifrost-pause --reason" in text


def test_json_is_unchanged(admin, capsys):
    _, text = _skip(capsys, json_out=True)
    assert json.loads(text) == _DONE


def test_human_view(admin, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _skip(capsys)
    assert text.startswith("deepseek: skipped to now  shared OK, lane OK")
    assert "shared.inbox" in text
