"""T076 pins: echo hygiene -- (a) sanctioned skip-to-now, (c) auto-settle asks whose tasks
are terminal. Cites the T076 task text; refines T014 (live asks still redrive; echoes stop).
Live-Redis pattern (rb21/t083/t086 lineage): unique agent ids = namespace isolation."""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import cursor_admin, expectations
from core.comm.bus import Bus

try:
    _ONLINE = bool(Bus("t076-probe").online)
except Exception:
    _ONLINE = False

pytestmark = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")


@pytest.fixture()
def agent():
    aid = f"t076-{uuid.uuid4().hex[:8]}"
    yield aid
    c = Bus(aid)._client
    try:
        for k in (f"bifrost:cursor:{aid}", f"bifrost:cursor:lane:{aid}",
                  f"bifrost:expect:{aid}", f"bifrost:inbox:{aid}"):
            c.delete(k)
    except Exception:
        pass


def _fake_ledger(monkeypatch, tasks):
    from core.coord import task_ledger
    monkeypatch.setattr(task_ledger, "read_ledger",
                        lambda *a, **k: {"tasks": tasks})


# ---------------------------------------------------------------- T076c: auto-settle
def test_done_task_echo_settles_instead_of_redriving(agent, monkeypatch):
    _fake_ledger(monkeypatch, [{"id": "T900", "status": "done"}])
    assert expectations.arm(agent, "111-0", "peer", "handoff",
                            "please build T900 factories", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["settled"] == ["111-0"] and res["redriven"] == []


def test_live_task_ask_still_redrives(agent, monkeypatch):
    _fake_ledger(monkeypatch, [{"id": "T901", "status": "claimed"}])
    assert expectations.arm(agent, "222-0", "peer", "handoff",
                            "T901 blind half please", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["redriven"] == ["222-0"] and res["settled"] == []


def test_mixed_terminal_and_live_ids_redrives(agent, monkeypatch):
    _fake_ledger(monkeypatch, [{"id": "T900", "status": "done"},
                               {"id": "T901", "status": "in_progress"}])
    assert expectations.arm(agent, "333-0", "peer", "request",
                            "T900 shipped; now do T901", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["redriven"] == ["333-0"] and res["settled"] == []


def test_no_task_ids_redrives_as_before(agent):
    assert expectations.arm(agent, "444-0", "peer", "question",
                            "what color should the button be", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["redriven"] == ["444-0"] and res["settled"] == []


def test_settle_kill_switch(agent, monkeypatch):
    _fake_ledger(monkeypatch, [{"id": "T900", "status": "done"}])
    monkeypatch.setenv("AKASHIC_EXPECT_TASK_SETTLE", "0")
    assert expectations.arm(agent, "555-0", "peer", "handoff", "T900 echo", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["redriven"] == ["555-0"] and res["settled"] == []


def test_unknown_task_id_conservative(agent, monkeypatch):
    _fake_ledger(monkeypatch, [{"id": "T900", "status": "done"}])
    assert expectations.arm(agent, "666-0", "peer", "handoff",
                            "T999 does not exist in ledger", within_s=30)
    res = expectations.sweep(agent, now=time.time() + 3600)
    assert res["redriven"] == ["666-0"] and res["settled"] == []


# ---------------------------------------------------------------- T076a: skip-to-now
def test_skip_refused_without_reason(agent):
    r = cursor_admin.skip_to_now(agent, by="tester", reason="  ")
    assert not r["ok"] and "reason required" in r["refused"]


def test_skip_refused_when_not_paused(agent, monkeypatch):
    from core.comm import control
    monkeypatch.setattr(control, "is_paused", lambda: False)
    r = cursor_admin.skip_to_now(agent, by="tester", reason="test")
    assert not r["ok"] and "not paused" in r["refused"]


def test_skip_advances_to_tails(agent, monkeypatch):
    from core.comm import control
    monkeypatch.setattr(control, "is_paused", lambda: True)
    sender = Bus(f"{agent}-peer")
    for i in range(3):
        sender.send(agent, "chat", f"echo {i}")
    b = Bus(agent)
    assert b.cursor().get("inbox", "0") == "0"          # virgin cursor, 3 pending
    r = cursor_admin.skip_to_now(agent, by="tester", reason="drill: clear echo mountain")
    assert r["ok"], r
    tail = b.tail().get("inbox", "0")
    assert tail != "0" and r["after"]["shared"]["inbox"] == tail
    msgs = b.wait(timeout_ms=1)                          # nothing pending after the skip
    assert [m for m in msgs if getattr(m, "kind", "") == "chat"] == []


def test_skip_pause_probe_error_fails_closed(agent, monkeypatch):
    from core.comm import control
    monkeypatch.setattr(control, "is_paused",
                        lambda: (_ for _ in ()).throw(RuntimeError("probe down")))
    r = cursor_admin.skip_to_now(agent, by="tester", reason="test")
    assert not r["ok"] and "unprobeable" in r["refused"]
