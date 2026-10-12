"""Pins for `compare` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_compare.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def domains(monkeypatch):
    from core.coord import compare as cmp_mod

    sets = {"left": ({"a", "b", "c"}, "thing"), "right": ({"b", "c", "d"}, "thing"), "other": ({"x"}, "path")}
    monkeypatch.setattr(cmp_mod, "DOMAINS", {k: ((lambda v=v: v[0]), v[1]) for k, v in sets.items()})
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, a="", b="", limit=40, list_=False):
    code = agent_cli.cmd_compare(argparse.Namespace(a=a, b=b, limit=limit, list=list_, json=False))
    return code, capsys.readouterr()


def test_list_names_domains_and_a_real_pair(domains, capsys):
    code, cap = _run(capsys)
    assert code == 0
    assert "total: " in cap.out  # the terms domains register themselves on import, too
    assert "{domain,keys}:" in cap.out
    assert "left,thing" in cap.out
    assert "compare left right" in cap.out


def test_diff_has_counts_reliability_and_both_sides(domains, capsys):
    code, cap = _run(capsys, "left", "right")
    assert code == 0
    assert "reliable: true" in cap.out
    assert "only_a: 1\n  only_b: 1\n  both: 2" in cap.out
    assert "only_a[1]: a" in cap.out
    assert cap.err == ""


def test_a_cut_side_says_how_to_see_all(domains, capsys, monkeypatch):
    from core.coord import compare as cmp_mod

    monkeypatch.setitem(cmp_mod.DOMAINS, "big", (lambda: {"b", "c", "p", "q", "r"}, "thing"))
    _, cap = _run(capsys, "big", "right", limit=1)
    assert "only_a: 3" in cap.out
    assert "only_a[1]: p" in cap.out
    assert "compare big right --limit 3" in cap.out
    _, cap = _run(capsys, "left", "right")  # nothing cut: the output answers itself
    assert "help[" not in cap.out


def test_refusal_is_a_structured_error_on_stdout(domains, capsys):
    code, cap = _run(capsys, "left", "other")
    assert code == 2
    assert "code: REFUSED" in cap.out
    assert "left: thing" in cap.out


def test_unknown_domain_is_a_usage_error_naming_the_real_ones(domains, capsys):
    code, cap = _run(capsys, "nope", "left")
    assert code == 2
    assert "code: USAGE" in cap.out
    assert "unknown domain 'nope'" in cap.out


def test_human_view(domains, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, cap = _run(capsys, "left", "right")
    assert "reliable" in cap.out
    assert "only in left (1)" in cap.out
