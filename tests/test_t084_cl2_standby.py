"""T084-CL-2 pins: bifrost-standby -- the turn-end ritual as ONE decision function.

Ordering laws under pin (each a tonight's-failure receipt): consume-THEN-arm (C1-2), live-twin
means DON'T listen (plan-wall redundant-watcher law), listener runs only after a clean drain,
and the listener is INJECTED (the CLI blocks as its parent -- never detached, the T073 law).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import bifrost_pull as bp


def _stub_consume(result):
    def f(agent_id, limit=20):
        return result
    return f


def test_live_twin_holds_seat_no_listen(monkeypatch):
    monkeypatch.setattr(bp, "consume_inbox", _stub_consume(
        {"seat_held": True, "holder": "session:twin", "teach": "seat held [holder liveness: marker-fresh (12s)]",
         "peeked": [{"kind": "reply", "frm": "deepseek", "content": "x"}]}))
    called = []
    res = bp.standby("claude", "s1", listen=lambda a, s: called.append(1))
    assert res["decision"] == "twin-holds-seat"
    assert not res["listened"] and not called          # never listen behind a live twin
    assert any("NOT listening" in l for l in res["report"])


def test_clean_drain_then_listen(monkeypatch):
    monkeypatch.setattr(bp, "consume_inbox", _stub_consume(
        {"seat_held": False, "consumed": [{"kind": "reply", "frm": "deepseek", "content": "done"}]}))
    monkeypatch.setattr(bp, "collect_boot_bifrost", lambda a, limit=1: {"expect_lines": []})
    order = []
    res = bp.standby("claude", "s1", listen=lambda a, s: order.append("listen") or 0)
    assert res["drained"] == 1
    assert res["decision"] == "listen" and res["listened"]
    assert res["listen_rc"] == 0
    drain_idx = next(i for i, l in enumerate(res["report"]) if "drained: 1" in l)
    listen_idx = next(i for i, l in enumerate(res["report"]) if "handing off" in l)
    assert drain_idx < listen_idx                      # consume-THEN-arm, structurally


def test_report_only_when_no_listener(monkeypatch):
    monkeypatch.setattr(bp, "consume_inbox", _stub_consume({"seat_held": False, "consumed": []}))
    monkeypatch.setattr(bp, "collect_boot_bifrost", lambda a, limit=1: {"expect_lines": []})
    res = bp.standby("claude", "s1", listen=None)
    assert res["decision"] == "report-only" and not res["listened"]
    assert any("already clean" in l for l in res["report"])


def test_drained_mail_rides_the_report_collapsed(monkeypatch):
    msgs = [{"kind": "reply", "frm": "deepseek", "content": "real"},
            {"kind": "trace", "frm": "deepseek", "content": "t1"},
            {"kind": "trace", "frm": "deepseek", "content": "t2"}]
    monkeypatch.setattr(bp, "consume_inbox", _stub_consume({"seat_held": False, "consumed": msgs}))
    monkeypatch.setattr(bp, "collect_boot_bifrost", lambda a, limit=1: {"expect_lines": []})
    res = bp.standby("claude", "s1", listen=None)
    text = "\n".join(res["report"])
    assert "real" in text
    assert "1 more trace(s)" in text                   # W4 collapse reused in the report


def test_expect_lines_surface(monkeypatch):
    monkeypatch.setattr(bp, "consume_inbox", _stub_consume({"seat_held": False, "consumed": []}))
    monkeypatch.setattr(bp, "collect_boot_bifrost",
                        lambda a, limit=1: {"expect_lines": ["EXPECTATION redrive #2: deepseek"]})
    res = bp.standby("claude", "s1", listen=None)
    assert any("redrive" in l for l in res["report"])  # RB-29 stays visible at turn end
