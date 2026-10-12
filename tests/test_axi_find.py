"""Pins for `find` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_find.py -q
"""

import argparse

import pytest

import agent_cli
from core.tools.everything import Hit, SearchResult


@pytest.fixture
def result(monkeypatch):
    import core.tools.everything as ev

    holder = {"r": SearchResult(query="x", ok=True, engine="walk", roots=["/a"], scanned_dirs=10)}
    monkeypatch.setattr(ev, "search_page", lambda q, **kw: holder["r"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, query="target.exe", **kw):
    ns = argparse.Namespace(query=query, limit=0, offset=0, format="", bare=False, preset="", **kw)
    code = agent_cli.cmd_find(ns)
    return code, capsys.readouterr().out


def test_matches_mark_the_exact_basename_and_say_the_engine(result, capsys):
    result["r"] = SearchResult(query="target.exe", ok=True, engine="walk", roots=["/a"], scanned_dirs=10,
                               paths=["/a/target.exe", "/a/target.exe.bak"])  # fmt: skip
    code, text = _run(capsys)
    assert code == 0
    assert "engine: walk\nsearched: 10 dirs under 1 roots" in text
    assert "complete: true\ntotal: 2" in text
    assert "/a/target.exe,true" in text
    assert "/a/target.exe.bak,false" in text


def test_everything_hits_carry_mtime_and_size(result, capsys):
    h = Hit(path="C:\\x\\target.exe", size=42, date_modified="2026-10-01 10:00:00")
    result["r"] = SearchResult(query="target.exe", ok=True, engine="everything", paths=[h.path], hits=[h])
    _, text = _run(capsys)
    assert "engine: Everything index" in text
    assert "matches[1]{path,exact,modified,size}:" in text


def test_a_bounded_miss_is_not_absence(result, capsys):
    result["r"] = SearchResult(query="target.exe", ok=True, engine="walk", exhaustive=False)
    code, text = _run(capsys)
    assert code == 0
    assert "complete: false" in text
    assert "not evidence of absence" in text
    assert "total: 0" in text


def test_a_long_list_is_cut_with_the_json_escape_hatch(result, capsys):
    result["r"] = SearchResult(query="t", ok=True, engine="walk", paths=[f"/a/t{i}" for i in range(80)])
    _, text = _run(capsys, query="t")
    assert "total: 80\nshown: 50" in text
    assert "find t --format json" in text


def test_unavailable_engine_is_a_structured_error(result, capsys):
    result["r"] = SearchResult(query="t", ok=False, error="es.exe not found")
    code, text = _run(capsys, query="t")
    assert code == 1
    assert "code: SEARCH_UNAVAILABLE" in text


def test_unknown_preset_is_a_usage_error(result, capsys):
    ns = argparse.Namespace(query="t", limit=0, offset=0, format="", bare=False, preset="nope")
    code = agent_cli.cmd_find(ns)
    text = capsys.readouterr().out
    assert code == 2
    assert "allowed[8]:" in text


def test_human_view(result, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    result["r"] = SearchResult(query="target.exe", ok=True, engine="walk", paths=["/a/target.exe"])
    _, text = _run(capsys)
    assert "1 match" in text
    assert "★ /a/target.exe" in text
