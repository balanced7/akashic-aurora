"""Pins for `audit` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_audit.py -q
"""

import argparse

import pytest

import agent_cli
from core.toolbelt import audit as _audit
from core.toolbelt.audit import Row


class _Domain:
    def __init__(self, name, rows):
        self.name = name
        self._rows = rows

    def run(self):
        return list(self._rows)


def _row(domain, ref, verdict, rule="", detail="why"):
    return Row(domain, ref, "a", "src_a", "b", "src_b", verdict, detail, rule)


@pytest.fixture
def domains(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    doms = [
        _Domain(
            "VERBS",
            [
                _row("VERBS", "claude:ask-peer", "DRIFT", "stale-receipt"),
                _row("VERBS", "claude:ask-peer", "DRIFT", "argparse-eaten"),
                _row("VERBS", "kimi:fence", "MATCH", detail="VERIFIED receipt kata-1"),
            ],
        ),
        _Domain("SPEND", [_row("SPEND", "kimi:spend", "UNKNOWN", "meter-missing")]),
    ]
    monkeypatch.setattr(_audit, "DOMAINS", doms)
    return doms


def _audit_cli(capsys, **kw):
    ns = argparse.Namespace(domain=None, ground="registry", json=False, fields=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_audit(ns)
    return code, capsys.readouterr().out


def test_counts_aggregates_and_four_column_rows(domains, capsys):
    code, text = _audit_cli(capsys)
    assert code == 0
    assert "total: 4\nmatch: 1\ndrift: 2\nunknown: 1" in text
    assert "domains[2]{domain,rows,match,drift,unknown}:" in text
    assert "VERBS,3,1,2,0" in text
    assert '"stale-receipt": 1' in text
    assert "rows[4]{domain,entry,verdict,rule}:" in text
    assert 'VERBS,"kimi:fence",MATCH,null' in text
    # next steps: the why behind each row, and the history of the first drifted alias
    assert "audit --fields detail" in text
    assert "alias claude history ask-peer" in text


def test_fields_adds_detail_and_rejects_unknown_names(domains, capsys):
    _, text = _audit_cli(capsys, fields="detail")
    assert "{domain,entry,verdict,rule,detail}" in text
    assert "VERIFIED receipt kata-1" in text
    code, text = _audit_cli(capsys, fields="bogus")
    assert code == 2
    assert "unknown field(s) bogus" in text


def test_unknown_domain_is_a_usage_error_naming_the_real_ones(domains, capsys):
    code, text = _audit_cli(capsys, domain="nope")
    assert code == 2
    assert "code: USAGE" in text
    assert "available[2]: VERBS,SPEND" in text


def test_no_rows_is_an_explicit_zero(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(_audit, "DOMAINS", [_Domain("VERBS", [])])
    code, text = _audit_cli(capsys)
    assert code == 0
    assert "total: 0" in text
    assert "rows: []" in text


def test_json_is_the_row_list(domains, capsys):
    import json

    _, text = _audit_cli(capsys, json=True)
    rows = json.loads(text)
    assert [r["verdict"] for r in rows] == ["DRIFT", "DRIFT", "MATCH", "UNKNOWN"]


def test_human_view_puts_counts_first_and_shows_why(domains, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _audit_cli(capsys)
    assert "4 rows: 1 match, 2 drift, 1 unknown" in text
    assert "VERBS · 3 rows, 2 drift" in text
    assert "VERIFIED receipt kata-1" in text  # the detail column is on for people
    assert text.index("stale-receipt") < text.index("kimi:fence")  # drift rows first
