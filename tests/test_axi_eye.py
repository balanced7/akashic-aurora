"""Pins for `eye` after the AXI conversion: what an agent and a person see.

The index is the repo's eye fixtures ingested into a temp database, so nothing here reads or
writes the live state/eye (which in a worktree is a link to the live checkout's).

Run: uv run pytest tests/test_axi_eye.py -q
"""

import json
from pathlib import Path

import pytest

import agent_cli
from core.eye import index as EYE

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eye"


@pytest.fixture
def eye_db(tmp_path, monkeypatch):
    db = tmp_path / "eye.db"
    monkeypatch.setattr(EYE, "_DEFAULT_DB", db)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return db


@pytest.fixture
def indexed(eye_db):
    from core.eye import connectome

    EYE.ingest(paths=sorted(FIX.glob("*.jsonl")), db_path=eye_db)
    connectome.build(db_path=eye_db)
    return eye_db


def _run(capsys, *argv):
    args = agent_cli.build_parser().parse_args(["eye", *argv])
    code = args.fn(args)
    return code, capsys.readouterr().out


def test_find_lists_hits_with_total_and_a_drill_hint(indexed, capsys):
    code, text = _run(capsys, "find", "sword")
    assert code == 0
    assert "total: 5" in text
    assert "hits[5]{event_id,voice,type,snippet}:" in text
    assert "eye get session_alpha:1" in text


def test_a_limited_find_says_how_many_it_shows(indexed, capsys):
    _, text = _run(capsys, "find", "sword", "--limit", "2")
    assert "total: 5\nshown: 2" in text
    assert "eye find sword --limit 5" in text


def test_an_empty_index_is_said_outright(eye_db, capsys):
    code, text = _run(capsys, "find", "sword")
    assert code == 0
    assert "total: 0" in text
    assert "hits: no event matches" in text


def test_a_malformed_selector_is_a_structured_usage_error(indexed, capsys):
    code, text = _run(capsys, "find", "x", "--as-of", "2026-13-01")
    assert code == 2
    assert "code: BAD_SELECTOR" in text


def test_get_resolves_and_names_its_twins(indexed, capsys):
    code, text = _run(capsys, "get", "session_gamma:3")
    assert code == 0
    assert 'event: "session_gamma:3"' in text
    assert "same_utterance_also_at[2]" in text


def test_get_of_a_missing_address_fails_on_stdout(indexed, capsys):
    code, text = _run(capsys, "get", "nope:1")
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_trace_carries_its_fog(indexed, capsys):
    code, text = _run(capsys, "trace", "session_gamma:5")
    assert code == 0
    assert "same_utterance[3]:" in text
    assert "downstream[3]{event_id,evidence,edge,voice,snippet}:" in text
    assert "fog: " in text


def test_trace_on_an_empty_connectome_points_at_ingest(eye_db, capsys):
    code, text = _run(capsys, "trace", "x:1")
    assert code == 2
    assert "code: NO_EDGES" in text
    assert "eye ingest" in text


def test_freq_and_stats(indexed, capsys):
    _, text = _run(capsys, "freq", "sword")
    assert "verdict: standing-directive" in text
    assert "per_session[3]{session,operator,events,refs}:" in text
    _, text = _run(capsys, "stats")
    assert "events_total: 40" in text
    assert "operator: 23" in text


def test_look_without_a_position_refuses(indexed, capsys):
    code, text = _run(capsys, "look", "--seat", "probe#00000000")
    assert code == 2
    assert "code: NO_POSITION" in text
    assert "eye go <session:line>" in text


def test_json_is_unchanged(indexed, capsys):
    _, text = _run(capsys, "find", "sword", "--json")
    env = json.loads(text)
    assert env["total"] == 5
    assert set(env) == {"results", "total", "degraded", "degraded_reason", "tokens_returned", "as_of"}


def test_human_find(indexed, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "find", "sword", "--limit", "2")
    assert "2 of 5 hits" in text
    assert "session_alpha:1" in text
    assert "Next:" in text
