"""Pins for `fleet` after the AXI conversion: what an agent and a person see. The roster is faked,
so nothing here reads core/fleet/models.json or reaches Ollama.

Run: uv run pytest tests/test_axi_fleet.py -q
"""

import argparse

import pytest

import agent_cli
from core.fleet import model_roster

ROSTER: list[dict] = [
    {"tag": "small:4b", "status": "active", "vram_gb": 4, "context": 32000, "throughput_toks": 40,
     "capabilities": ["extract", "summarize"], "notes": "fast", "disqualifier": None},
    {"tag": "big:30b", "status": "gated", "vram_gb": 19, "context": 64000, "throughput_toks": None,
     "capabilities": ["code"], "notes": "", "disqualifier": "citation laundering"},
]  # fmt: skip


@pytest.fixture
def roster(monkeypatch):
    def models(status=None, capability=None):
        return [
            m
            for m in ROSTER
            if (status is None or m["status"] == status) and (capability is None or capability in m["capabilities"])
        ]

    monkeypatch.setattr(model_roster, "models", models)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _fleet(capsys, action="list", **kw):
    ns = argparse.Namespace(
        action=action, status=None, capability=None, probe=False, json=False, fields=None,
        max_vram=None, min_context=None, model=None, prompt=None, system=None, max_tokens=512,
        temperature=0.2, json_out=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_fleet(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_roster_is_a_table_with_a_total_and_why_gated(roster, capsys):
    code, text = _fleet(capsys)
    assert code == 0
    assert "total: 2\nmodels[2]{tag,status,vram_gb,context,capabilities,why_gated}:" in text
    assert '"small:4b",active,4,32000,extract summarize,null' in text
    assert '"big:30b",gated,19,64000,code,citation laundering' in text
    assert "fleet select --capability <capability>" in text


def test_fields_adds_columns_and_rejects_unknown_ones(roster, capsys):
    _, text = _fleet(capsys, fields="tps")
    assert "{tag,status,vram_gb,context,capabilities,tps,why_gated}" in text
    code, text = _fleet(capsys, fields="bogus")
    assert code == 2
    assert "unknown field(s) bogus" in text


def test_a_filter_matching_nothing_is_an_explicit_zero(roster, capsys):
    code, text = _fleet(capsys, status="retired")
    assert code == 0
    assert "status: retired\ntotal: 0\nmodels: []" in text


def test_select_names_the_pick_and_the_call_to_run(roster, capsys):
    code, text = _fleet(capsys, "select", capability="extract")
    assert code == 0
    assert 'selected: "small:4b"' in text
    assert 'fleet call --model small:4b --prompt "<text>"' in text


def test_nothing_fits_and_a_bad_call_are_structured_errors(roster, capsys):
    code, text = _fleet(capsys, "select", capability="code")  # only a gated model has it
    assert code == 1
    assert "code: NO_FIT" in text
    assert "asked: " in text
    code, text = _fleet(capsys, "call")
    assert code == 2
    assert "code: USAGE" in text


def test_human_roster_colours_status_and_lists_gated_reasons(roster, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _fleet(capsys)
    assert "Fleet roster · 2 models" in text
    assert "4 GB" in text
    assert "32k" in text
    assert "gated big:30b: citation laundering" in text
