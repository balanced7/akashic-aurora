"""Pins for `packet-trace` after the AXI conversion: what an agent and a person see.

The route table is static policy, so these run the real router.

Run: uv run pytest tests/test_axi_packet_trace.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture(autouse=True)
def agent_mode(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _trace(capsys, kind, json=False):
    code = agent_cli.cmd_packet_trace(argparse.Namespace(kind=kind, json=json))
    return code, capsys.readouterr().out


def test_a_mapped_kind_names_its_lane_and_rule(capsys):
    code, text = _trace(capsys, "handoff")
    assert code == 0
    assert "kind: handoff\nlane: work\n" in text
    assert 'rule: "kind:handoff"' in text
    assert "observation_only: true" in text
    assert "help" not in text  # a lookup answers itself


def test_an_unmapped_kind_is_an_answer_not_an_error(capsys):
    code, text = _trace(capsys, "bogus_kind")
    assert code == 0
    assert "lane: null\nmapped: false\ndelivery: legacy only" in text


def test_json_is_unchanged(capsys):
    _, text = _trace(capsys, "handoff", json=True)
    assert text.startswith('{"kind": "handoff"')


def test_human_view_is_a_key_value_list(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _trace(capsys, "handoff")
    assert "Packet route · handoff" in text
    assert "work" in text
