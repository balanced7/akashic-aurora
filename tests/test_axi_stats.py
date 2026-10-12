"""Pins for `stats` after the AXI conversion that tests/test_stats.py does not cover: the
--silence zero, the repeat-floor hint, and the human view.

Run: uv run pytest tests/test_axi_stats.py -q
"""

import types

import pytest

import agent_cli

SNAP = {
    "corpus_lessons": 3,
    "tracked_sources": 2,
    "surfaced_impressions": 0,
    "votes": {"useful": 0, "noise": 0},
    "helped_credits": 0,
    "value_rate": None,
    "lessons_with_track_record": 0,
    "window": {
        "flips": 2,
        "flips_credited": 0,
        "flips_corpus_gap": 2,
        "lessons_recorded": 0,
        "lessons_per_flip": 0.0,
    },
}


@pytest.fixture
def stats(monkeypatch, capsys):
    import core.learning.learning_store as ls
    import core.recall.at_action as aa
    import core.recall.funnel as fn

    monkeypatch.setattr(fn, "snapshot", lambda hours: SNAP)
    monkeypatch.setattr(
        ls,
        "get_learning_store",
        lambda: types.SimpleNamespace(repeat_report=lambda: {"count": 0, "most_violated": [], "by_recall_outcome": {}}),
    )
    monkeypatch.setattr(aa, "silence_rate", lambda window_s: {"calls": 0, "fired": 0, "silent": 0, "by_reason": {}})
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "alice")

    def run(**kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        ns = types.SimpleNamespace(**{"hours": 24, "days": None, "silence": False, "json": False, **kw})
        code = agent_cli.cmd_stats(ns)
        return code, capsys.readouterr().out

    return run


def test_funnel_fields_gap_and_hints(stats):
    code, text = stats()
    assert code == 0
    assert "corpus_lessons: 3" in text
    assert "repeats: 0" in text
    assert "capture_gap:" in text
    assert "agent_cli.py wrap" in text or "aurora wrap" in text
    assert "learn alice --repeat-of <lesson>" in text
    assert "stats --days 7" in text


def test_silence_zero_says_what_it_means(stats):
    code, text = stats(silence=True)
    assert code == 0
    assert "calls: 0" in text
    assert "NOT 0% silent" in text
    assert "-m core.recall.pack_replay" in text
    assert "uv run -m" not in text


def test_human_view(stats):
    _, text = stats(env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Recall-value funnel")
    assert "corpus lessons" in text
