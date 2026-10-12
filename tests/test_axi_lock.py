"""Pins for `lock` after the AXI conversion: taken, refreshed, refused, offline.

Run: uv run pytest tests/test_axi_lock.py -q
"""

import argparse
import json
from unittest import mock

import pytest

import agent_cli
from core.comm import locks


def _manager(monkeypatch, *, res, holder=None, online=True):
    mgr = mock.Mock()
    mgr.return_value.acquire.return_value = res
    mgr.return_value.holder.return_value = holder
    mgr.return_value.online = online
    monkeypatch.setattr(locks, "LockManager", mgr)
    return mgr


def _ok(token=7, path="core/a.py"):
    return {"ok": True, "online": True, "mine": True, "token": token, "held_by": "alice", "path": path}


def _lock(capsys, json_=False, ttl=600):
    code = agent_cli.cmd_lock(argparse.Namespace(agent_id="alice", path="core/a.py", ttl=ttl, json=json_))
    return code, capsys.readouterr().out


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def test_fresh_lock_says_acquired_with_ttl_and_release_hint(monkeypatch, capsys):
    _manager(monkeypatch, res=_ok())
    code, text = _lock(capsys)
    assert code == 0
    assert text.startswith("lock: acquired\npath: core/a.py\nagent: alice\nttl_s: 600\ntoken: 7\n")
    assert "unlock alice core/a.py" in text


def test_reclaiming_your_own_lock_says_refreshed(monkeypatch, capsys):
    _manager(monkeypatch, res=_ok(), holder={"agent": "alice", "token": 7})
    code, text = _lock(capsys)
    assert code == 0
    assert text.startswith("lock: refreshed")


def test_a_peers_lock_is_a_structured_refusal_exit_1(monkeypatch, capsys):
    res = {"ok": False, "online": True, "mine": False, "token": 3, "held_by": "bob", "path": "core/a.py"}
    _manager(monkeypatch, res=res, holder={"agent": "bob", "token": 3})
    code, text = _lock(capsys)
    assert code == 1
    assert "error: core/a.py is held by bob" in text
    assert "code: LOCK_HELD" in text
    assert "held_by: bob" in text
    assert "--to bob --kind request" in text


def test_offline_bus_is_an_error(monkeypatch, capsys):
    res = {"ok": False, "online": False, "mine": False, "token": None, "held_by": None, "path": "core/a.py"}
    _manager(monkeypatch, res=res, online=False)
    code, text = _lock(capsys)
    assert code == 1
    assert "code: OFFLINE" in text


def test_json_is_the_raw_acquire_result(monkeypatch, capsys):
    mgr = _manager(monkeypatch, res=_ok())
    code, text = _lock(capsys, json_=True)
    assert code == 0
    assert json.loads(text) == _ok()
    mgr.return_value.holder.assert_not_called()  # --json does exactly what it did before


def test_human_view_says_when_it_expires(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _manager(monkeypatch, res=_ok())
    _, text = _lock(capsys)
    assert "locked core/a.py for alice" in text
    assert "expires in 10m" in text
