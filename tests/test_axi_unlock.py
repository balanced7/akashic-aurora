"""Pins for `unlock` after the AXI conversion: released, a peer's lock, already free, offline.

Nothing released still exits 1, as before the conversion; the error now says which case it was.

Run: uv run pytest tests/test_axi_unlock.py -q
"""

import argparse
from unittest import mock

import pytest

import agent_cli
from core.comm import locks


def _manager(monkeypatch, *, released, holder=None, online=True):
    mgr = mock.Mock()
    mgr.return_value.release.return_value = released
    mgr.return_value.holder.return_value = holder
    mgr.return_value.online = online
    monkeypatch.setattr(locks, "LockManager", mgr)


def _unlock(capsys, path="core/a.py"):
    code = agent_cli.cmd_unlock(argparse.Namespace(agent_id="alice", path=path))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def test_release_says_released(monkeypatch, capsys):
    _manager(monkeypatch, released=True, holder={"agent": "alice"})
    code, text, _ = _unlock(capsys)
    assert code == 0
    assert text.startswith("unlock: released\npath: core/a.py\nagent: alice\n")
    assert "locks alice" in text


def test_a_peers_lock_names_the_holder(monkeypatch, capsys):
    _manager(monkeypatch, released=False, holder={"agent": "bob"})
    code, text, _ = _unlock(capsys)
    assert code == 1
    assert "error: core/a.py is held by bob" in text
    assert "code: NOT_YOURS" in text


def test_a_free_path_says_not_locked_and_keeps_exit_1(monkeypatch, capsys):
    _manager(monkeypatch, released=False, holder=None)
    code, text, _ = _unlock(capsys)
    assert code == 1
    assert "error: core/a.py is not locked" in text
    assert "code: NOT_HELD" in text


def test_offline_bus_is_its_own_error(monkeypatch, capsys):
    _manager(monkeypatch, released=False, online=False)
    code, text, _ = _unlock(capsys)
    assert code == 1
    assert "code: OFFLINE" in text


def test_human_view(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _manager(monkeypatch, released=True, holder={"agent": "alice"})
    _, text, _ = _unlock(capsys)
    assert "released core/a.py (alice)" in text
    _manager(monkeypatch, released=False, holder={"agent": "bob"})
    code, text, err = _unlock(capsys)
    assert code == 1
    assert "core/a.py is held by bob" in err  # human errors go to stderr
