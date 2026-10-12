"""Pins for `mailbox` after the AXI conversion: what an agent and a person see.

The bus and the mailbox index are stubbed, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_mailbox.py -q
"""

import argparse

import pytest

import agent_cli


class _Bus:
    ns, _client = "test-ns", None

    def __init__(self, *a, **k):
        pass


def _entry(sha, tier, frm, kind="chat"):
    return {"sha": sha * 64, "tier": tier, "kind": kind, "frm": frm, "ts": "2026-10-12T10:00:00+00:00"}


@pytest.fixture
def mbx(monkeypatch):
    import core.comm.bus as bus_mod
    import core.comm.mailbox as mb

    state = {"entries": []}

    def query(ns, agent, client=None, min_evidence=None):
        counts = {"unhandled": 0}
        for e in state["entries"]:
            counts[e["tier"]] = counts.get(e["tier"], 0) + 1
        return {"available": True, "entries": state["entries"], "counts": counts, "index_lag": 0, "evicted": 0}

    monkeypatch.setattr(bus_mod, "Bus", _Bus)
    monkeypatch.setattr(mb, "query", query)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _mailbox(capsys, **kw):
    ns = argparse.Namespace(
        agent_id="bench", json=False, rebuild=False, explain=None, min_evidence=None, retire_ghosts=False,
        open_sha=None, backfill=False, state_sha=None, intent_sha=None, intent_kind=None, intent_note=None,
        intent_to=None,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_mailbox(ns)
    return code, capsys.readouterr().out


def test_listing_is_counts_then_the_mail_in_play(mbx, capsys):
    mbx["entries"] = [_entry("a", "consumed", "alice"), _entry("b", "unhandled", "dave", "request"),
                      _entry("c", "acked", "carol")]  # fmt: skip
    code, text = _mailbox(capsys)
    assert code == 0
    assert "total: 3\nunhandled: 1\nconsumed: 1\nacked: 1" in text
    assert "messages[2]{sha,tier,kind,from,at}:" in text
    assert "bbbbbbbbbbbb,unhandled,request,dave" in text  # 12 characters: a width --open accepts
    assert "bifrost-sync bench --consume" in text


def test_one_message_hints_name_its_sha(mbx, capsys):
    mbx["entries"] = [_entry("d", "unhandled", "dave")]
    _, text = _mailbox(capsys)
    assert "mailbox bench --open dddddddddddd" in text
    assert "--intent dddddddddddd --as" in text


def test_empty_mailbox_says_zero(mbx, capsys):
    code, text = _mailbox(capsys)
    assert code == 0
    assert "total: 0\nunhandled: 0\nmessages: []" in text


def test_ambiguous_prefix_is_a_structured_error_with_candidates(mbx, capsys, monkeypatch):
    import core.comm.mailbox as mb

    refusal = {"ok": False, "how": "ambiguous", "reason": "2 entries match", "matched": 2,
               "candidates": ["ab" * 32, "ac" * 32]}  # fmt: skip
    monkeypatch.setattr(mb, "open", lambda *a, **k: refusal)
    code, text = _mailbox(capsys, open_sha="a")
    assert code == 1
    assert "code: AMBIGUOUS" in text
    assert "matched: 2" in text
    assert "--open abababababababab" in text


def test_intent_without_as_is_a_usage_error(mbx, capsys):
    code, text = _mailbox(capsys, intent_sha="abc")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view_counts_and_table(mbx, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    mbx["entries"] = [_entry("b", "unhandled", "dave", "request")]
    _, text = _mailbox(capsys)
    assert "1 addressed to bench: 1 unhandled" in text
    assert "dave" in text
