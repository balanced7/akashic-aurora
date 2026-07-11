"""
Progress bars, the data half (co-designed 2026-07-11, deepseek GREEN: median+p90 over
EWFA-rejected, LOW CONFIDENCE n<8, min n=3 to estimate, pct = min(95, points/median*100),
kind-alone bucketing, capped per-(agent,kind) history). The UI bars are deepseek's lane;
this pins the capture + estimator + progress_view the /status payload will read.

Honesty law (M8): an ETA is "the median of N similar turns", never a promise; below
n=3 the view shows elapsed-only; the % bar never claims 100 until the turn closes.

Run: py -m pytest tests/test_turn_metrics.py -q
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import turn_metrics as tm


class FakeStore:
    """Capped-list semantics standing in for the Redis stream."""
    def __init__(self):
        self.rows = {}

    def push(self, key, row, cap):
        self.rows.setdefault(key, []).append(row)
        self.rows[key] = self.rows[key][-cap:]

    def read(self, key):
        return list(self.rows.get(key, []))


def test_record_and_history_are_capped(monkeypatch):
    st = FakeStore()
    monkeypatch.setattr(tm, "_push_row", st.push)
    monkeypatch.setattr(tm, "_read_rows", st.read)
    for i in range(tm.HISTORY_CAP + 20):
        tm.record("deepseek", "handoff", duration_s=10 + (i % 5), progress_points=6,
                  outcome="ok", prompt_len=900)
    rows = st.read(tm._key("deepseek", "handoff"))
    assert len(rows) == tm.HISTORY_CAP, "history stays capped"
    assert rows[-1]["prompt_len_band"] == "medium"


def test_estimator_median_p90_and_confidence_tiers(monkeypatch):
    st = FakeStore()
    monkeypatch.setattr(tm, "_push_row", st.push)
    monkeypatch.setattr(tm, "_read_rows", st.read)
    tm._est_cache.clear()
    # n=2: below min -> no estimate
    for d in (10, 12):
        tm.record("a", "chat", duration_s=d, progress_points=4, outcome="ok", prompt_len=10)
    assert tm.estimate("a", "chat") is None, "n<3 -> elapsed-only, no ETA shown"
    # n=5: estimate with LOW confidence
    for d in (8, 11, 40):
        tm.record("a", "chat", duration_s=d, progress_points=4, outcome="ok", prompt_len=10)
    est = tm.estimate("a", "chat")
    assert est and est["n"] == 5 and est["confidence"] == "low"
    assert est["median_s"] == 11, f"median robust against the 40s outlier: {est}"
    assert est["p90_s"] >= est["median_s"]
    # n=8+: confidence ok
    tm._est_cache.clear()
    for d in (9, 10, 12):
        tm.record("a", "chat", duration_s=d, progress_points=4, outcome="ok", prompt_len=10)
    assert tm.estimate("a", "chat")["confidence"] == "ok"


def test_estimate_is_cached_briefly(monkeypatch):
    st = FakeStore()
    monkeypatch.setattr(tm, "_push_row", st.push)
    monkeypatch.setattr(tm, "_read_rows", st.read)
    tm._est_cache.clear()
    for d in (5, 6, 7):
        tm.record("c", "request", duration_s=d, progress_points=3, outcome="ok", prompt_len=10)
    e1 = tm.estimate("c", "request")
    tm.record("c", "request", duration_s=100, progress_points=3, outcome="ok", prompt_len=10)
    assert tm.estimate("c", "request") == e1, "30s cache: mid-turn reads stay stable"


def test_pct_estimate_honesty():
    est = {"median_points": 10}
    assert tm.pct_estimate(5, est) == 50
    assert tm.pct_estimate(20, est) == 95, "never claims done while running (cap 95)"
    assert tm.pct_estimate(3, None) is None, "no history -> no % claim at all"


def test_prompt_len_bands():
    assert tm.len_band(100) == "small"
    assert tm.len_band(1500) == "medium"
    assert tm.len_band(5000) == "large"


def test_pulse_count_take_resets():
    tm.count_pulse("z"); tm.count_pulse("z"); tm.count_pulse("z")
    assert tm.take_pulse_count("z") == 3
    assert tm.take_pulse_count("z") == 0, "turn-scoped: reading resets"


def test_progress_view_composes_live_turn(monkeypatch):
    st = FakeStore()
    monkeypatch.setattr(tm, "_push_row", st.push)
    monkeypatch.setattr(tm, "_read_rows", st.read)
    tm._est_cache.clear()
    for d in (10, 10, 10, 10):
        tm.record("deepseek", "handoff", duration_s=d, progress_points=8,
                  outcome="ok", prompt_len=900)
    now = time.time()
    monkeypatch.setattr(tm, "_worklive_read", lambda a: {
        "phase": "handling", "detail": "claude:handoff", "since_ts": now - 5})
    tm.count_pulse("deepseek"); tm.count_pulse("deepseek")
    view = tm.progress_view("deepseek", peek=True)
    assert view["ask_kind"] == "handoff" and 4.5 <= view["elapsed_s"] <= 6
    assert view["points_seen"] == 2
    assert view["eta"]["median_s"] == 10
    assert view["pct_estimate"] == 25   # 2/8 * 100
    idle_view = tm.progress_view("deepseek", peek=True,
                                 _wl={"phase": "idle", "since_ts": now})
    assert idle_view is None, "no live turn -> no bars (idle agents get no card)"
