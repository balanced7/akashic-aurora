"""G4.P2 latent ADV-033: `season-score --round-file` read the file through an unimported `io`.

Every invocation with --round-file crashed with NameError before scoring anything.
"""

import argparse
import json
import os
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.season import scoring


def test_season_score_reads_the_round_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The round file's claims, verifications, uptime and fixed keys all reach the scorer."""
    claims = [{"player": "p1", "dedupe_key": "k1"}]
    round_file = tmp_path / "round.json"
    round_file.write_text(
        json.dumps({"claims": claims, "verifications": [{"v": 1}], "uptime": {"p1": 1.0}, "fixed_keys": ["k1"]}),
        encoding="utf-8",
    )
    score_round = mock.Mock(return_value={"ok": True})
    monkeypatch.setattr(scoring, "score_round", score_round)
    args = argparse.Namespace(policies=False, round_file=str(round_file), compare=False, json=True, policy="v1_doc")

    assert agent_cli.cmd_season_score(args) == 0

    score_round.assert_called_once_with(claims, [{"v": 1}], policy="v1_doc", uptime={"p1": 1.0}, fixed_keys={"k1"})
    assert json.loads(capsys.readouterr().out) == {"ok": True}
