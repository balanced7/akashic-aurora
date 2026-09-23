"""DSH wake-check pins — the non-consuming detect half of the rill-wake organ (T403).

  P1  reports NEW wake-worthy mail NON-CONSUMINGLY (advance=False, since=watermark)
  P2  persists a LOCAL watermark (never the shared Bifrost cursor)
  P3  a non-wake-worthy kind (note/status/trace) is silent-by-default (the ratchet)
  P4  fails open on a bus error (count=0 + error shape, never a traceback)

Run: py -m pytest tests/test_dsh_wake_check.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness.dsh_plugin import bridge


class _Msg:
    def __init__(self, kind, frm):
        self.kind = kind
        self.frm = frm


class _Bus:
    calls = []
    msgs = []

    def __init__(self, agent):
        self.agent = agent

    def cursor(self):
        return {"inbox": "5-5", "bc": "5-5"}

    def wait(self, timeout_ms=0, limit=50, advance=False, since=None,
             since_out=None, streams=None):
        type(self).calls.append({"since": dict(since or {}), "advance": advance})
        if since_out is not None:
            since_out["inbox"] = "6-6"
            since_out["bc"] = "6-6"
        return list(type(self).msgs)


@pytest.fixture()
def patched(monkeypatch, tmp_path):
    _Bus.calls = []
    _Bus.msgs = [_Msg("request", "deepseek"), _Msg("note", "kimi"),
                 _Msg("trace", "claude"), _Msg("reply", "deepseek")]
    monkeypatch.setattr(bridge, "_repo", lambda: str(tmp_path))
    monkeypatch.setattr(bridge, "_wake_watermark_path", lambda: str(tmp_path / "wm.json"))
    monkeypatch.setattr("core.comm.bus.Bus", _Bus)
    monkeypatch.chdir(tmp_path)


def _run(capsys):
    rc = bridge.cmd_wake_check(None)
    return rc, json.loads(capsys.readouterr().out)


def test_p1_reports_wake_worthy_non_consuming(patched, capsys):
    rc, out = _run(capsys)
    assert rc == 0 and out["has_wake_worthy"] is True
    assert out["count"] == 2, "request + reply are wake-worthy; note + trace are not"
    assert set(out["kinds"]) == {"request", "reply"}
    assert out["senders"] == ["deepseek"]
    assert _Bus.calls[0]["advance"] is False, "the shared cursor must never be advanced"
    assert _Bus.calls[0]["since"] == {"inbox": "5-5", "bc": "5-5"}, (
        "first arm seeds from the shared cursor so pre-existing mail never re-wakes")


def test_p2_persists_local_watermark(patched, tmp_path, capsys):
    _run(capsys)
    wm_path = tmp_path / "wm.json"
    assert wm_path.exists(), "the local watermark must persist across subprocess calls"
    assert json.loads(wm_path.read_text()) == {"inbox": "6-6", "bc": "6-6"}


def test_p3_non_wake_worthy_is_silent(patched, monkeypatch, capsys):
    _Bus.msgs = [_Msg("note", "kimi"), _Msg("trace", "claude"), _Msg("status", "claude")]
    rc, out = _run(capsys)
    assert rc == 0 and out["count"] == 0 and out["has_wake_worthy"] is False, (
        "note/status/trace must never wake an idle seat -- silent-by-default ratchet")


def test_p4_fails_open_on_bus_error(patched, monkeypatch, capsys):
    def boom(agent):
        raise RuntimeError("bus down")
    monkeypatch.setattr("core.comm.bus.Bus", boom)
    rc, out = _run(capsys)
    assert rc == 0 and out.get("count") == 0 and "error" in out, (
        "a dead bus is a fail-open shape, never a traceback")


def test_p5_plugin_wake_organ_is_wired():
    """Static seam pins for the JS half (rill-wake T403): the poll timer, the
    non-consuming wake-check call, the inbox next-turn append (pointer, form snapshot),
    the loud seat-down capture, and arm/stop at session/created/disposed."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "agent" / "harness" / "dsh_plugin"
           / "lib" / "index.js").read_text(encoding="utf-8")
    assert "startWakeTimer" in src and "stopWakeTimer" in src
    assert "['wake-check']" in src, "the poll calls the non-consuming detect"
    assert "inbox.append('next-turn', doorbell)" in src, "the poke is the inbox append seam"
    assert "form: 'snapshot'" in src, "the doorbell source form is snapshot (R11)"
    assert "wake-seat-down" in src, "seat down must be LOUD (R6)"
    assert "wake-poke" in src and "wake-poke-failed" in src
    # arm/stop ride the session lifecycle (R2): created arms, disposed stops
    assert "startWakeTimer()" in src and "stopWakeTimer()" in src
