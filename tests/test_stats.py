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
    monkeypatch.setattr(aa, "_INJ_DIR", str(tmp_path / "inj"))   # hermetic: never the real ledger
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
    # utcnow, not now: the stores stamp utcnow().isoformat(), and funnel windows in UTC too
    recs = [{"experiment_name": "new", "timestamp": datetime.utcnow().isoformat(timespec="seconds")},
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
    assert out["value_rate"] == 0.375, "(useful+helped)/surfaced = 3/8 -- the steering ratio"
    w = out["window"]
    assert w["flips"] == 2 and w["flips_credited"] == 1 and w["flips_corpus_gap"] == 1
    assert w["lessons_recorded"] == 1, "only the recent lesson falls in the window"
    assert w["lessons_per_flip"] == 0.5


def test_stats_human_output_ascii(tmp_path, monkeypatch):
    recs, use, flips = _fixture(time.time())
    out = _run_stats(monkeypatch, tmp_path, recs, use, flips)
    assert "RECALL-VALUE FUNNEL" in out and "lessons-per-flip=0.5" in out
    assert "value rate ((useful+helped)/surfaced): 37.5%" in out
    assert out == out.encode("ascii", errors="replace").decode(), "ASCII-only (Windows console)"


def test_stats_no_impressions_no_value_rate(tmp_path, monkeypatch):
    """value_rate must be None (and its line absent), not a divide-by-zero or a fake 0%."""
    out = json.loads(_run_stats(monkeypatch, tmp_path, [], {}, [], as_json=True))
    assert out["value_rate"] is None
    human = _run_stats(monkeypatch, tmp_path, [], {}, [])
    assert "value rate" not in human


def test_stats_empty_everything_is_calm(tmp_path, monkeypatch):
    out = json.loads(_run_stats(monkeypatch, tmp_path, [], {}, [], as_json=True))
    assert out["corpus_lessons"] == 0 and out["window"]["flips"] == 0
    assert out["window"]["lessons_per_flip"] is None


# --- slice 2: the shared funnel module -- trend from durable records + the boot pulse -------------

class _FakeEventLog:
    def __init__(self, events):
        self._events = events

    def scan(self, limit=None):
        return self._events[-limit:] if limit else self._events


def test_trend_buckets_lessons_and_flip_events_by_utc_day():
    from datetime import datetime, timedelta
    from core.recall.funnel import trend
    now = datetime(2026, 7, 2, 12, 0, 0)
    d0, d1 = now.date().isoformat(), (now - timedelta(days=1)).date().isoformat()
    recs = [{"experiment_name": "a", "timestamp": f"{d0}T01:00:00"},
            {"experiment_name": "b", "timestamp": f"{d1}T23:00:00"},
            {"experiment_name": "ancient", "timestamp": "2020-01-01T00:00:00"}]
    events = [{"kind": "flip", "at": f"{d0}T02:00:00", "detail": {"credited": 1}},
              {"kind": "flip", "at": f"{d0}T03:00:00", "detail": {"credited": 0}},
              {"kind": "boot", "at": f"{d0}T04:00:00", "detail": {}}]
    tr = trend(days=3, learning_store=_FakeLearningStore(recs),
               event_log=_FakeEventLog(events), now=now)
    assert [b["date"] for b in tr["per_day"]][-1] == d0, "oldest-first, today last"
    today = tr["per_day"][-1]
    assert today["lessons"] == 1 and today["flips"] == 2 and today["credited"] == 1
    assert tr["per_day"][-2]["lessons"] == 1, "yesterday's lesson bucketed to yesterday"
    assert tr["lessons_30d"] == 2 and tr["target_30d"] == 30
    assert tr["events_capped"] is False


def test_trend_flags_a_capped_event_scan():
    from datetime import datetime
    from core.recall import funnel
    events = [{"kind": "boot", "at": "2026-07-02T00:00:00", "detail": {}}] * funnel.EVENT_SCAN_LIMIT
    tr = funnel.trend(days=1, learning_store=_FakeLearningStore([]),
                      event_log=_FakeEventLog(events), now=datetime(2026, 7, 2, 12, 0, 0))
    assert tr["events_capped"] is True, "a full scan means older flips may be missing -- say so"


def test_summary_line_is_one_ascii_line():
    from core.recall.funnel import snapshot, summary_line
    line = summary_line(snapshot(hours=7 * 24, store=_FakeStore({}),
                                 learning_store=_FakeLearningStore([]), flips=[], injections=[]))
    assert "\n" not in line and "lessons" in line and "last 7d" in line
    assert "value" not in line, "no impressions -> no value segment (silent, not 0%)"
    assert line == line.encode("ascii", errors="replace").decode()


def test_summary_line_carries_value_rate_when_measurable():
    from core.recall.funnel import snapshot, summary_line
    use = {"recall:use:learn:experiment:a": json.dumps({"surfaced": 8, "helped": 2, "useful": 1})}
    line = summary_line(snapshot(hours=24, store=_FakeStore(use),
                                 learning_store=_FakeLearningStore([]), flips=[], injections=[]))
    assert "value 37.5%" in line


def test_snapshot_counts_injection_cost():
    from core.recall.funnel import snapshot
    inj = [{"at": 1.0, "alt": "action", "t": "c:x", "s": ["learn:experiment:a"], "chars": 400},
           {"at": 2.0, "alt": "plan", "t": "", "s": ["learn:experiment:b"], "chars": 200}]
    snap = snapshot(hours=24, store=_FakeStore({}), learning_store=_FakeLearningStore([]),
                    flips=[], injections=inj)
    assert snap["window"]["injections"] == 2
    assert snap["window"]["injected_tokens_approx"] == 150, "(400+200)//4"


def test_stats_days_prints_trend_and_pace(tmp_path, monkeypatch):
    import core.events.event_log as el
    recs, use, flips = _fixture(time.time())
    monkeypatch.setattr(el, "get_event_log",
                        lambda *a, **k: _FakeEventLog([{"kind": "flip",
                                                        "at": recs[0]["timestamp"],
                                                        "detail": {"credited": 1}}]))
    import core.foundation.store as fs
    import core.learning.learning_store as ls
    monkeypatch.setattr(fs, "create_store", lambda *a, **k: _FakeStore(use))
    monkeypatch.setattr(ls, "get_learning_store", lambda *a, **k: _FakeLearningStore(recs))
    monkeypatch.setattr(aa, "_FLIP_DIR", str(tmp_path / "flips"))
    os.makedirs(str(tmp_path / "flips"), exist_ok=True)
    args = types.SimpleNamespace(hours=24, days=7, json=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert agent_cli.cmd_stats(args) == 0
    out = buf.getvalue()
    assert "TREND (last 7d" in out and "30d pace:" in out
    assert "flips=1" in out and "credited=1" in out
    assert out == out.encode("ascii", errors="replace").decode(), "ASCII-only (Windows console)"
