"""Regression pins for cross-field tool-protocol text reaching the lesson store.

Three live lessons were written with ``result`` and ``recommend`` serialized inside
``what_tried``.  The write returned success, but the empty sibling fields later made
the lessons fail FAITH.  The public learn door must reject that exact collapsed shape
before any store write while still allowing ordinary prose to mention one protocol
token.
"""
from types import SimpleNamespace

import agent_cli
from core.learning import learning_store


class _Store:
    def __init__(self):
        self.recorded = []

    def _load_experiment(self, _name):
        return {}

    def load_all_learnings_from_store(self):
        return []

    def record_learning(self, signal):
        self.recorded.append(signal)
        return True


def _args(*, tried):
    return SimpleNamespace(
        agent_id="pin",
        experiment="protocol_contamination_pin",
        tried=tried,
        result="",
        expected="",
        recommend="",
        category="testing",
        success="yes",
        confidence="medium",
        anti_pattern="",
        json=False,
    )


def _isolate_success_side_effects(monkeypatch):
    monkeypatch.setattr(
        "core.narrative.beat_log.get_beat_log",
        lambda: SimpleNamespace(emit=lambda *_a, **_k: None),
    )
    monkeypatch.setattr(
        "core.events.event_log.capture_event",
        lambda *_a, **_k: None,
    )


def test_p1_collapsed_tool_fields_are_refused_before_the_store(monkeypatch, capsys):
    store = _Store()
    monkeypatch.setattr(learning_store, "get_learning_store", lambda: store)
    collapsed = (
        "Measured the read path.</tried>\n"
        '<parameter name="result">The measurement succeeded.</parameter>\n'
        '<parameter name="recommend">Use the measured path.</parameter>\n'
        "</invoke>"
    )

    rc = agent_cli.cmd_learn(_args(tried=collapsed))

    assert rc == 2
    assert store.recorded == [], "a collapsed multi-field payload must never reach storage"
    out = capsys.readouterr().out
    assert "tool-protocol" in out and "separate" in out, out


def test_p2_one_literal_protocol_token_in_prose_is_not_a_false_positive(monkeypatch):
    store = _Store()
    monkeypatch.setattr(learning_store, "get_learning_store", lambda: store)
    _isolate_success_side_effects(monkeypatch)
    prose = (
        'The parser documentation names <parameter name="result"> as a literal token; '
        "there is no serialized field-closing boundary here."
    )

    rc = agent_cli.cmd_learn(_args(tried=prose))

    assert rc == 0
    assert len(store.recorded) == 1
    assert store.recorded[0]["what_tried"] == prose
