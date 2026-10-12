"""Pins for `knowledge-map` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_knowledge_map.py -q
"""

import argparse

import pytest

import agent_cli


def _node(title, kind="lesson", status="current", via=None, edges=0):
    n = {"kind": kind, "id": title, "title": title, "source": title, "status": status, "score": 1.0,
         "excerpt": f"about {title}", "drill": f"recall --full learn:experiment:{title}", "edge_count": edges}  # fmt: skip
    if via:
        n["via"] = via
    return n


@pytest.fixture
def kmap(monkeypatch):
    import core.recall.knowledge_map as km

    holder = {"surface": [], "neighborhood": [], "archive": []}

    def fake(topic, per_layer=6):
        return {**holder, "counts": {k: len(v) for k, v in holder.items()}}

    monkeypatch.setattr(km, "knowledge_map", fake)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, query=("quokkadb",)):
    code = agent_cli.cmd_knowledge_map(argparse.Namespace(query=list(query), per_layer=None, json=False))
    return code, capsys.readouterr().out


def test_layers_are_tables_with_counts_and_a_real_drill_hint(kmap, capsys):
    kmap["surface"] = [_node("wal_mode", edges=2)]
    kmap["neighborhood"] = [_node("backup", via={"from": "wal_mode", "direction": "out", "matched": ["db"]})]
    kmap["archive"] = [_node("old_cache", kind="note", status="retired")]
    code, text = _run(capsys)
    assert code == 0
    assert "surface: 1\n  neighborhood: 1\n  archive: 1" in text
    assert "surface[1]{kind,status,title,score,edges,excerpt,drill}:" in text  # edges: some node has one
    assert "neighborhood[1]{kind,status,title,score,via,excerpt,drill}:" in text
    assert "wal_mode --> [db]" in text
    assert "recall --full learn:experiment:wal_mode" in text.split("help[", 1)[1]


def test_nothing_found_is_explicit(kmap, capsys):
    code, text = _run(capsys, ("zebra",))
    assert code == 0
    assert "surface: 0" in text
    assert "nothing above the relevance floor" in text


def test_no_topic_is_a_usage_error(kmap, capsys):
    code, text = _run(capsys, ())
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(kmap, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    kmap["archive"] = [_node("old_cache", kind="note", status="retired")]
    _, text = _run(capsys)
    assert "0 surface · 0 neighborhood · 1 archive" in text
    assert "L3 archive" in text
    assert "old_cache" in text
