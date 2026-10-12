"""Pins for `events` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_events.py -q
"""

import pytest

import agent_cli


class _Args:
    """argparse stand-in: any unset attribute reads as None."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, _name):
        return None


def _ev(i, kind="note", agent="alice", track=None, summary=None):
    return {
        "kind": kind,
        "at": "2026-10-12T14:00:00+00:00",
        "agent_id": agent,
        "track": track,
        "summary": summary or f"event number {i}",
        "_ref": f"event:events:raw:{i}-0",
    }


class _Log:
    def __init__(self, rows):
        self.rows = rows

    def recent(self, n, agent=None):
        return [r for r in self.rows if agent in (None, r["agent_id"])][:n]


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def search(self, q, top_k=10, **_kw):
        return self.rows[:top_k]

    def resolve(self, ref):
        hit = next((r for r in self.rows if r["_ref"] == ref), None)
        return (hit, None) if hit else (None, "payload aged out")


@pytest.fixture
def events(monkeypatch):
    import core.events.event_log as log_mod
    import core.events.event_query as q_mod

    rows: list = []
    monkeypatch.setattr(log_mod, "get_event_log", lambda: _Log(rows))
    monkeypatch.setattr(q_mod, "get_event_query", lambda: _Query(rows))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return rows


def _run(capsys, **kw):
    code = agent_cli.cmd_events(_Args(**kw))
    return code, capsys.readouterr().out


def test_recent_is_a_table_with_a_drill_hint(events, capsys):
    events += [_ev(2, kind="deploy", track="ops"), _ev(1)]
    code, text = _run(capsys)
    assert code == 0
    assert "count: 2" in text
    assert "events[2]{kind,at,agent,track,summary,ref}:" in text  # track only because one has it
    assert "events --get event:events:raw:2-0" in text


def test_no_track_column_when_no_event_has_one(events, capsys):
    events.append(_ev(1))
    _, text = _run(capsys)
    assert "events[1]{kind,at,agent,summary,ref}:" in text


def test_empty_is_said_outright_with_next_steps(events, capsys):
    code, text = _run(capsys, agent="dave")
    assert code == 0
    assert "agent: dave\ncount: 0\nevents: []" in text
    assert "--capture" in text


def test_a_full_page_says_more_may_exist(events, capsys):
    events += [_ev(i) for i in range(5)]
    _, text = _run(capsys, limit=3)
    assert "count: 3" in text
    assert "more: may exist beyond --limit 3" in text
    assert "events --limit 6" in text


def test_search_says_it_ranks_rather_than_filters(events, capsys):
    events.append(_ev(1))
    _, text = _run(capsys, search="auth")
    assert "query: auth" in text
    assert "ranked, not filtered" in text


def test_long_summary_is_cut_with_its_size(events, capsys):
    events.append(_ev(1, summary="word " * 100))
    _, text = _run(capsys)
    assert "(truncated, 499 chars total)" in text


def test_get_miss_is_a_structured_error(events, capsys):
    code, text = _run(capsys, get="event:events:raw:9-0")
    assert code == 2
    assert "code: NOT_FOUND" in text
    assert "aged out" in text


def test_get_hit_is_a_detail_view(events, capsys):
    events.append(_ev(1, summary="the whole story"))
    code, text = _run(capsys, get="event:events:raw:1-0")
    assert code == 0
    assert "summary: the whole story" in text
    assert "help[" not in text


def test_human_view_lists_each_event(events, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    events.append(_ev(1, kind="deploy", track="ops", summary="deployed api"))
    _, text = _run(capsys)
    assert "1 raw event" in text
    assert "by alice  track ops" in text
    assert "deployed api" in text
