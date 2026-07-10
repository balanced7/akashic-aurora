"""
P5 / T025 -- proposed-task decay: stale proposals demand a verdict, abandon records one.

Bar: abandon is a terminal, reasoned transition (conductor emits ledger_update for it);
staleness is computed at RENDER with an injected clock (the ledger stays pure): proposed
tasks untouched past the threshold flag stale, are listed for a verdict, and the counts
line says so -- silent parked intent was the T002-T007 disease.

Run: py -m pytest tests/test_proposed_decay.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import conductor
from core.coord import task_ledger as TL


def test_abandon_is_terminal_and_reasoned(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(conductor, "_broadcast",
                        lambda kind, text, meta: sent.append((kind, meta.get("to"))))
    path = str(tmp_path / "tasks.json")
    t = conductor.propose("lane-era leftover", by="claude", client=None, path=path)
    out = conductor.abandon(t["id"], "lane era ended; re-propose if wanted", by="user",
                            client=None, path=path)
    assert out["status"] == "abandoned"
    assert out["history"][-1]["reason"].startswith("lane era ended")
    assert ("ledger_update", "abandoned") in sent, "P3 uniformity: abandon rings the doorbell"
    with pytest.raises(TL.LedgerError):
        conductor.approve(t["id"], client=None, path=path)   # terminal: no way back


def _seed(tmp_path, created_days_ago):
    path = str(tmp_path / "tasks.json")
    led = TL.TaskLedger(path, client=None)
    old = time.time() - created_days_ago * 86400
    at = __import__("datetime").datetime.fromtimestamp(old).isoformat()
    led.propose("old parked idea", by="claude", at=at)
    return path


def test_stale_flagging_uses_injected_clock(tmp_path):
    path = _seed(tmp_path, created_days_ago=30)
    v = TL.state_view(path, None, now=time.time(), stale_days=7)
    assert v["proposed"][0]["stale"] is True
    assert v["proposed"][0]["age_days"] > 7
    fresh = TL.state_view(path, None, now=time.time(), stale_days=45)
    assert fresh["proposed"][0]["stale"] is False, "threshold is honored"
    plain = TL.state_view(path, None)
    assert "stale" not in plain["proposed"][0], "no clock, no staleness -- ledger stays pure"


def test_format_state_lists_stale_and_counts_them(tmp_path):
    path = _seed(tmp_path, created_days_ago=30)
    text = TL.format_state(path=path, client=None, now=time.time())
    assert "PROPOSED BUT STALE" in text
    assert "re-approve or abandon" in text
    assert "proposed 1 (1 stale)" in text
    fresh = TL.format_state(path=path, client=None)   # no clock -> no annotation
    assert "PROPOSED BUT STALE" not in fresh
