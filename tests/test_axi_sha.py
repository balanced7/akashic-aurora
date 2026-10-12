"""Pins for `sha` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_sha.py -q
"""

import argparse
from types import SimpleNamespace
from typing import ClassVar

import pytest

import agent_cli
from core.git.rewrite_map import Resolution


class _Resolver:
    maps: ClassVar[list] = []

    def resolve(self, sha, check_remote=True):
        if sha == "00cf320d":
            return Resolution(
                sha,
                "translated",
                sha="fdccf166e157" + "0" * 28,
                hops=[(sha, "3bc123e32bb3" + "0" * 28, "2026-07-23"), ("3bc123e32bb3", "fdccf166e157", "2026-08-12")],
            )
        return Resolution(sha, "unknown", note="no map covers it")


@pytest.fixture
def resolver(monkeypatch):
    import core.git.rewrite_map as rm

    monkeypatch.setattr(rm, "Resolver", _Resolver)
    monkeypatch.setattr(_Resolver, "maps", [])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return _Resolver


def _sha(capsys, *shas, maps=False, verbose=False):
    ns = argparse.Namespace(sha=list(shas), maps=maps, verbose=verbose, no_remote=True)
    code = agent_cli.cmd_sha(ns)
    return code, capsys.readouterr().out


def test_results_are_counted_and_the_gate_exit_stays(resolver, capsys):
    code, text = _sha(capsys, "00cf320d", "deadbeef1")
    assert code == 1  # any unresolved SHA fails the gate, as before
    assert "total: 2\nresolved: 1\nunresolved: 1" in text
    assert "shas[2]{cited,status,now,maps,note}:" in text
    assert "00cf320d,translated,fdccf166e157,2026-07-23 -> 2026-08-12,null" in text
    assert "deadbeef1,unknown,null,null,no map covers it" in text
    assert "sha --maps" in text


def test_all_resolved_exits_zero_without_a_hint(resolver, capsys):
    code, text = _sha(capsys, "00cf320d")
    assert code == 0
    assert "help[" not in text


def test_verbose_adds_one_row_per_hop(resolver, capsys):
    _, text = _sha(capsys, "00cf320d", verbose=True)
    assert "hops[2]{cited,from,to,map}:" in text


def test_maps_table_and_the_no_maps_error(resolver, capsys, monkeypatch):
    code, text = _sha(capsys, maps=True)
    assert code == 1
    assert "code: NOT_FOUND" in text
    m = SimpleNamespace(label="2026-08-12", rows=[1, 2], dropped=[], method="recorded", durable=False)
    monkeypatch.setattr(_Resolver, "maps", [m])
    code, text = _sha(capsys, maps=True)
    assert code == 0
    assert "2026-08-12,2,0,recorded,no (.git only)" in text


def test_no_sha_is_a_usage_error(resolver, capsys):
    code, text = _sha(capsys)
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(resolver, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _sha(capsys, "00cf320d")
    assert "1 of 1 resolved" in text
    assert "translated" in text
