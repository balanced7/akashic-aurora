"""Pins for `review` after the AXI conversion: what an agent and a person see.

Nothing here applies a change to a checkout: apply/rollback are not exercised.

Run: uv run pytest tests/test_axi_review.py -q
"""

import argparse

import pytest

from core.metaharness import cli, replay


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, action, id_="", **kw):
    ns = argparse.Namespace(
        action=action, id=id_, candidate="", against="", scenario=None, predicted="", reviewer="", decision="",
        calls="", reason="", json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.review_main(ns)
    return code, capsys.readouterr().out


def _queue(capsys, name="cand"):
    replay.create_candidate(name, harness="claude-code")
    _, text = _run(capsys, "add", candidate=name, against="baseline", scenario=["T1"])
    return next(ln.split(": ", 1)[1] for ln in text.splitlines() if ln.startswith("id: "))


def test_empty_queue_watch_and_disagreements_say_zero(capsys):
    code, text = _run(capsys, "list")
    assert code == 0
    assert "pending: 0\nitems: []" in text
    _, text = _run(capsys, "watch")
    assert "watching: 0" in text
    _, text = _run(capsys, "disagreements")
    assert "total: 0" in text


def test_add_then_list_gives_rows_and_the_real_next_commands(capsys):
    iid = _queue(capsys)
    _, text = _run(capsys, "list")
    assert "pending: 1" in text
    assert "items[1]{id,candidate,against,verdict,needs,expires}:" in text
    assert f"review show {iid}" in text
    assert f"review decide {iid} --reviewer <you>" in text


def test_show_and_decide(capsys):
    iid = _queue(capsys)
    _, text = _run(capsys, "show", iid)
    assert "status: pending" in text
    assert "page: " in text
    code, text = _run(capsys, "decide", iid, reviewer="ann", decision="reject", reason="no gain")
    assert code == 0
    assert "status: rejected" in text


def test_errors_are_structured(capsys):
    code, text = _run(capsys, "show", "nope")
    assert code == 1
    assert "error: no review item 'nope'\ncode: NOT_FOUND" in text
    code, text = _run(capsys, "decide")
    assert code == 2
    assert "code: USAGE" in text
    iid = _queue(capsys)
    code, text = _run(capsys, "decide", iid, reviewer="ann", decision="maybe", reason="x")
    assert code == 1
    assert "code: INVALID" in text
    code, text = _run(capsys, "apply", iid)
    assert code == 1
    assert "code: REFUSED" in text  # no accept recorded: nothing lands


def test_human_list_is_a_table(capsys, monkeypatch):
    _queue(capsys)
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "list")
    assert "Review queue" in text
    assert "cand" in text
