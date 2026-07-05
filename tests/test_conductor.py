"""Tests for the conductor (core/coord/conductor) — Slice D.

The pure gate logic lives in task_ledger (tested there). Here we cover the conductor's own behaviour:
next_task() sequencing (deps + one-at-a-time) and that done() emits the RESOLVED marker.
"""
import os

from core.coord import conductor as C


def _kw(tmp_path):
    return dict(client=None, path=os.path.join(str(tmp_path), "t.json"))


def test_next_task_respects_deps_and_one_at_a_time(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "_emit_resolved", lambda *a, **k: None)   # no bus in tests
    k = _kw(tmp_path)
    a = C.propose("a", **k)
    b = C.propose("b", deps=[a["id"]], **k)
    C.approve(a["id"], **k)
    C.approve(b["id"], **k)
    assert C.next_task(**k)["id"] == a["id"]        # b is blocked: dep a not DONE
    C.claim(a["id"], "claude", **k)
    C.start(a["id"], **k)
    assert C.next_task(**k) is None                 # one-at-a-time: a is running
    C.verify(a["id"], **k)
    C.done(a["id"], "c0ffee", "pytest", **k)
    assert C.next_task(**k)["id"] == b["id"]        # a DONE -> b now claimable


def test_done_emits_resolved_marker(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_emit_resolved",
                        lambda tid, title, commit: seen.update(tid=tid, commit=commit))
    k = _kw(tmp_path)
    a = C.propose("x", **k)
    C.approve(a["id"], **k)
    C.claim(a["id"], "claude", **k)
    C.start(a["id"], **k)
    C.verify(a["id"], **k)
    C.done(a["id"], "sha9", "v", **k)
    assert seen == {"tid": a["id"], "commit": "sha9"}
