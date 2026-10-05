"""G4.P2 latent: `sift --junction` crashed building its record after the paid tiers ran.

The record read `p.occurrences` / `p.truncated` from every pack, but junction mode builds
`JunctionPack`s, which have neither, so the run died with AttributeError after the hat fan.
"""

import argparse
import json
import os
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.comm import ask
from core.coord import sift


def test_sift_junction_mode_records_its_packs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A junction run finishes and records each pack's junction count, uncapped."""
    junctions = [
        {"crossing": "a.py:1 -> b.py:2", "same_file": False},
        {"crossing": "a.py:3 -> a.py:4", "same_file": True},
    ]
    pack = sift.JunctionPack(term="drained", junctions=junctions, blob="blob", sha="abc", blind=["b"])
    monkeypatch.setattr(sift, "junction_pack", mock.Mock(return_value=pack))
    fan = mock.Mock(detail={"branches": [], "n": 0, "n_ok": 0})
    monkeypatch.setattr(ask, "ask_many", mock.Mock(return_value=fan))
    args = argparse.Namespace(
        hats="", planes="code", terms=["drained"], junction=True, dry_run=False, workers=1, out=None, json=True
    )

    assert agent_cli.cmd_sift(args) == 0

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["packs"]["drained"] == {"sha": "abc", "n": len(junctions), "truncated": False, "blind": ["b"]}
