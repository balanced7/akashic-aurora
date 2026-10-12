"""Pins for `capture` after the AXI conversion: what an agent and a person see.

The bus is stubbed with a two-stream fake, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_capture.py -q
"""

import argparse

import pytest

import agent_cli


class _Client:
    def __init__(self, rows):
        self.rows = rows  # [(sid, fields)] on the work inbox

    def xrange(self, key, min=None, max=None):  # noqa: A002  # the redis-py signature
        return [r for r in self.rows if "work" in key and r[0] == min]

    def xrevrange(self, key, count=None):
        return list(reversed(self.rows)) if "work" in key else []


@pytest.fixture
def bus(monkeypatch):
    import core.comm.bus as bus_mod

    state = {"rows": []}

    class _Bus:
        def __init__(self, *a, **k):
            self._client = _Client(state["rows"])

    monkeypatch.setattr(bus_mod, "Bus", _Bus)
    monkeypatch.setenv("AKASHIC_AGENT_ID", "bench")
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _capture(capsys, **kw):
    ns = argparse.Namespace(ref="", from_agent="", count=3, persist="", title="", thread="", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_capture(ns)
    return code, capsys.readouterr().out


def test_bodies_are_whole_and_say_their_size(bus, capsys):
    body = "step one\n" + "x" * 2000
    bus["rows"] = [("1-0", {"frm": "alice", "kind": "handoff", "content": body})]
    code, text = _capture(capsys, from_agent="alice")
    assert code == 0
    assert "count: 1" in text
    assert "messages[1]{id,from,kind,chars,body}:" in text
    assert "1-0,alice,handoff,2009," in text
    assert "x" * 2000 in text  # never cut: full fidelity is the verb's job
    assert "capture --from-agent alice --count 3 --persist <path>" in text


def test_persist_writes_the_file_and_reports_it(bus, capsys, tmp_path):
    bus["rows"] = [("2-0", {"frm": "bob", "kind": "chat", "content": "hello"})]
    dest = tmp_path / "cap.md"
    _, text = _capture(capsys, ref="2-0", persist=str(dest))
    assert "persisted_chars: 5" in text
    assert dest.read_text(encoding="utf-8").endswith("hello\n")


def test_no_match_is_not_found(bus, capsys):
    code, text = _capture(capsys, ref="9-0")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_nothing_asked_is_a_usage_error(bus, capsys):
    code, text = _capture(capsys)
    assert code == 2
    assert "code: USAGE" in text
    assert "--from-agent" in text


def test_human_view_prints_the_body_as_written(bus, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    bus["rows"] = [("3-0", {"frm": "alice", "kind": "note", "content": "line one\nline two"})]
    _, text = _capture(capsys, ref="3-0")
    assert "3-0 · alice [note] · 17 chars" in text
    assert "line one\nline two" in text
