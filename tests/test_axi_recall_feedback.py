"""Pins for `recall-feedback` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_recall_feedback.py -q
"""

import argparse
import json

import pytest

import core.recall.at_action as at
from core.recall.surface import cmd_recall_feedback


class _KV:
    def __init__(self):
        self.d = {}

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v):
        self.d[k] = v


@pytest.fixture
def kv(monkeypatch):
    store = _KV()
    monkeypatch.setattr(at, "_store", lambda: store)
    monkeypatch.setattr(at, "canonicalize_source", lambda s, **kw: s)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return store


def _vote(capsys, source="learn:experiment:x", noise=False, domain=None):
    code = cmd_recall_feedback(argparse.Namespace(source=source, useful=not noise, noise=noise, domain=domain))
    return code, capsys.readouterr().out


def test_a_vote_says_what_was_recorded_and_the_running_counts(kv, capsys):
    code, text = _vote(capsys, domain="vfx")
    assert code == 0
    assert text.splitlines()[:5] == [
        "recorded: useful",
        'source: "learn:experiment:x"',
        "domain: vfx",
        "useful_votes: 1",
        "noise_votes: 0",
    ]
    assert "help" not in text  # a confirmation answers itself


def test_credit_in_two_domains_is_announced(kv, capsys):
    _vote(capsys, domain="vfx")
    _, text = _vote(capsys, domain="system")
    assert "useful_votes: 2" in text
    assert "domain_general:" in text


def test_a_noise_vote(kv, capsys):
    _, text = _vote(capsys, noise=True)
    assert "recorded: noise" in text
    assert "noise_votes: 1" in text
    assert json.loads(kv.d["recall:use:learn:experiment:x"])["noise"] == 1


def test_a_vote_that_cannot_be_stored_is_an_error(kv, capsys, monkeypatch):
    monkeypatch.setattr(at, "record_feedback", lambda *a, **k: False)
    code, text = _vote(capsys)
    assert code == 1
    assert "code: NOT_RECORDED" in text


def test_human_view(kv, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _vote(capsys)
    assert "recorded" in text
    assert "useful" in text
    assert "learn:experiment:x" in text
