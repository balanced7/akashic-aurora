"""`stats` verb (leapfrog T3): the recall-value funnel over data the loop already records.
Hermetic: store, learning store, and flip dir are all injected/patched."""
import io
import json
import os
import sys
import time
import types
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
import core.recall.at_action as aa


class _FakeLearningStore:
    def __init__(self, recs):
        self._recs = recs

    def load_all_learnings_from_store(self):
        return self._recs


class _FakeStore:
    def __init__(self, d):
        self._d = d

    def keys(self, pattern="*"):
        return [k for k in self._d if k.startswith(pattern.rstrip("*"))]

    def get(self, k):
        return self._d.get(k)


def _run_stats(monkeypatch, tmp_path, recs, use, flip_recs, hours=24, as_json=False):
    import core.foundation.store as fs
    import core.learning.learning_store as ls
    monkeypatch.setattr(fs, "create_store", lambda *a, **k: _FakeStore(use))
    monkeypatch.setattr(ls, "get_learning_store", lambda *a, **k: _FakeLearningStore(recs))
    monkeypatch.setattr(aa, "_FLIP_DIR", str(tmp_path / "flips"))
    os.makedirs(str(tmp_path / "flips"), exist_ok=True)
    with open(str(tmp_path / "flips" / "s.jsonl"), "w", encoding="utf-8") as f:
        for r in flip_recs:
            f.write(json.dumps(r) + "\n")
    args = types.SimpleNamespace(hours=hours, json=as_json)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = agent_cli.cmd_stats(args)
    assert rc == 0
    return buf.getvalue()


def _fixture(now):
    from datetime import datetime
    recs = [{"experiment_name": "new", "timestamp": datetime.now().isoformat(timespec="seconds")},
            {"experiment_name": "old", "timestamp": "2020-01-01T00:00:00"}]
    use = {"recall:use:learn:experiment:new": json.dumps({"surfaced": 5, "helped": 2}),
           "recall:use:learn:experiment:old": json.dumps({"surfaced": 3, "useful": 1, "noise": 1})}
    flips = [{"t": "c:a", "credited": 1, "s": ["learn:experiment:new"], "at": now},
             {"t": "c:b", "credited": 0, "s": [], "at": now}]
    return recs, use, flips


def test_stats_json_funnel(tmp_path, monkeypatch):
    recs, use, flips = _fixture(time.time())
    out = json.loads(_run_stats(monkeypatch, tmp_path, recs, use, flips, as_json=True))
    assert out["corpus_lessons"] == 2 and out["tracked_sources"] == 2
    assert out["surfaced_impressions"] == 8 and out["helped_credits"] == 2
    assert out["votes"] == {"useful": 1, "noise": 1}
    assert out["lessons_with_track_record"] == 2
    w = out["window"]
    assert w["flips"] == 2 and w["flips_credited"] == 1 and w["flips_corpus_gap"] == 1
    assert w["lessons_recorded"] == 1, "only the recent lesson falls in the window"
    assert w["lessons_per_flip"] == 0.5


def test_stats_human_output_ascii(tmp_path, monkeypatch):
    recs, use, flips = _fixture(time.time())
    out = _run_stats(monkeypatch, tmp_path, recs, use, flips)
    assert "RECALL-VALUE FUNNEL" in out and "lessons-per-flip=0.5" in out
    assert out == out.encode("ascii", errors="replace").decode(), "ASCII-only (Windows console)"


def test_stats_empty_everything_is_calm(tmp_path, monkeypatch):
    out = json.loads(_run_stats(monkeypatch, tmp_path, [], {}, [], as_json=True))
    assert out["corpus_lessons"] == 0 and out["window"]["flips"] == 0
    assert out["window"]["lessons_per_flip"] is None
