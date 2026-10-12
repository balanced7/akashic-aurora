"""Pins for `harnesses` after the AXI conversion: the tier matrix for an agent and a person.

Run: uv run pytest tests/test_axi_harnesses.py -q
"""

import argparse
import json

import pytest

import agent_cli
from agent.harness import registry

_FAKE = {
    "alpha": {
        "default_agent_id": "a1",
        "adapters": "x",
        "tiers": dict.fromkeys(registry.TIERS, "yes -- wired") | {"T3": "one-beat-late -- next step"},
    },
    "beta": {
        "default_agent_id": None,
        "adapters": "none",
        "tiers": dict.fromkeys(registry.TIERS, "manual -- by hand")
        | {"T0": "yes -- shell", "T5": "unavailable -- no seam", "T2": "pending -- not observed"},
    },
}


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(registry, "HARNESSES", _FAKE)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, **kw):
    code = agent_cli.cmd_harnesses(argparse.Namespace(json=kw.get("json", False)))
    return code, capsys.readouterr().out


def test_agent_matrix_one_row_per_harness_with_status_words(fake, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "tiers: 7" in text
    assert "harnesses[2]{harness,agent_id,automated,T0,T1,T2,T3,T4,T5,T6}:" in text
    assert "alpha,a1,7,yes,yes,yes,one-beat-late,yes,yes,yes" in text
    assert "beta,null,1,yes,manual,pending,manual,manual,unavailable,manual" in text
    assert "harnesses --json" in text


def test_json_keeps_the_registry_shape(fake, capsys):
    _, text = _run(capsys, json=True)
    doc = json.loads(text)
    assert doc["tiers"] == list(registry.TIERS)
    assert doc["harnesses"]["alpha"]["tiers"]["T3"] == "one-beat-late -- next step"


def test_human_view_is_a_marked_matrix_with_a_legend(fake, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys)
    row = next(line for line in text.splitlines() if line.strip().startswith("beta"))
    assert row.split()[1:] == ["—", "1/7", "✓", "m", "?", "m", "m", "✗", "m"]
    alpha = next(line for line in text.splitlines() if line.strip().startswith("alpha"))
    assert "7/7" in alpha
    assert "~" in alpha
    assert "one beat late" in text
