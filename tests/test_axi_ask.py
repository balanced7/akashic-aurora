"""Pins for `ask` after the AXI conversion: what an agent and a person see, with no model call.

The helper is replaced with canned outcomes and the background register points at tmp_path, so
nothing here spends money or reads the real ask journals.

Run: uv run pytest tests/test_axi_ask.py -q
"""

import pytest

import agent_cli
from core.comm import ask as ask_mod
from core.comm import ask_bg
from core.outcome import BoundaryOutcome


def _parse(*argv):
    return agent_cli.build_parser().parse_args(["ask", *argv])


@pytest.fixture(autouse=True)
def _agent(monkeypatch, tmp_path):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(ask_bg, "ASK_DIR", tmp_path / "asks")


def _answered(text="The answer is 42.", partial=False):
    meta = {"model": "deepseek-chat", "prompt_tokens": 120, "completion_tokens": 8, "usd": 0.00002, "elapsed_s": 1.4}
    o = BoundaryOutcome.partially("cut at the token limit") if partial else BoundaryOutcome.done()
    o.detail.update(answer=text, **meta)
    return o


def test_an_answer_carries_its_metadata(monkeypatch, capsys):
    monkeypatch.setattr(ask_mod, "ask", lambda *a, **k: _answered())
    assert agent_cli.cmd_ask(_parse("what is it?")) == 0
    out = capsys.readouterr().out
    for line in ("status: complete", "model: deepseek-chat", "prompt_tokens: 120", "completion_tokens: 8"):
        assert line in out
    assert "answer: The answer is 42." in out
    assert "help[" not in out  # an answer answers itself


def test_a_partial_answer_says_so_and_still_carries_the_text(monkeypatch, capsys):
    monkeypatch.setattr(ask_mod, "ask", lambda *a, **k: _answered(partial=True))
    assert agent_cli.cmd_ask(_parse("what is it?")) == 0
    out = capsys.readouterr().out
    assert "status: partial" in out
    assert "cut at the token limit" in out
    assert "The answer is 42." in out


def test_a_failed_ask_is_a_structured_error(monkeypatch, capsys):
    assert agent_cli.cmd_ask(_parse()) == 1  # no question: refused before any model call
    out = capsys.readouterr().out
    assert out.startswith("error: empty prompt")
    assert "code: ASK_FAILED" in out
    assert 'ask "<question>"' in out


def test_no_background_asks_is_said_outright(capsys):
    assert agent_cli.cmd_ask(_parse("--list")) == 0
    out = capsys.readouterr().out
    assert out.startswith("total: 0")
    assert "ask --bg" in out


def test_listed_asks_are_rows_with_the_newest_handle_in_the_hint(capsys):
    ask_bg.write_record("aaaa1111", {"status": "done", "prompt": "older", "started": 1, "result": {"answer": "x"}})
    ask_bg.write_record("bbbb2222", {"status": "failed", "prompt": "newer", "started": 2, "result": {"why": "no key"}})
    assert agent_cli.cmd_ask(_parse("--list")) == 0
    out = capsys.readouterr().out
    assert "total: 2" in out
    assert "asks[2]{handle,state,prompt}:" in out
    assert out.index("bbbb2222") < out.index("aaaa1111")
    assert "ask --get bbbb2222" in out


def test_get_unknown_handle_points_at_the_list(capsys):
    assert agent_cli.cmd_ask(_parse("--get", "deadbeef")) == 0
    out = capsys.readouterr().out
    assert "state: UNKNOWN" in out
    assert "ask --list" in out


def test_bg_with_get_is_a_usage_error(capsys):
    assert agent_cli.cmd_ask(_parse("--bg", "--get", "x")) == 2
    out = capsys.readouterr().out
    assert "code: USAGE" in out
    assert "--bg SPAWNS a new ask" in out


def test_human_view_prints_the_answer_first(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(ask_mod, "ask", lambda *a, **k: _answered("Line one.\nLine two."))
    assert agent_cli.cmd_ask(_parse("what is it?")) == 0
    out = capsys.readouterr().out
    assert "Line one.\nLine two." in out
    assert out.index("Line two.") < out.index("deepseek-chat")


def test_a_fan_is_one_row_per_branch_with_the_tally(monkeypatch, capsys):
    o = BoundaryOutcome.done()
    o.detail.update(
        n=2,
        n_ok=1,
        model="deepseek-chat",
        usd=None,
        elapsed_s=2.0,
        workers=2,
        branches=[
            {"i": 0, "ok": True, "partial": False, "answer": "Yes.", "why": None},
            {"i": 1, "ok": False, "partial": False, "answer": "", "why": "timeout"},
        ],
    )
    monkeypatch.setattr(ask_mod, "ask_many", lambda *a, **k: o)
    assert agent_cli.cmd_ask(_parse("--fan", "2", "is it?")) == 0
    out = capsys.readouterr().out
    assert "landed: 1" in out
    assert "branches[2]{i,status,answer}:" in out
    assert "1,failed,(timeout)" in out
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    agent_cli.cmd_ask(_parse("--fan", "2", "is it?"))
    human = capsys.readouterr().out
    assert "branch 0" in human
    assert "(timeout)" in human
