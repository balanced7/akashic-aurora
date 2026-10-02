"""G4.P2 latent ADV-033: `season-score --round-file` read the file through an unimported `io`.

Every invocation with --round-file crashed with NameError before scoring anything.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.season import scoring


def test_season_score_reads_the_round_file(monkeypatch, tmp_path, capsys):
    claims = [{"player": "p1", "dedupe_key": "k1"}]
    round_file = tmp_path / "round.json"
    round_file.write_text(
        json.dumps({"claims": claims, "verifications": [{"v": 1}], "uptime": {"p1": 1.0}, "fixed_keys": ["k1"]}),
        encoding="utf-8",
    )
    seen = {}

    def _score_round(c, v, policy=None, uptime=None, fixed_keys=None):
        seen.update(claims=c, verifications=v, policy=policy, uptime=uptime, fixed_keys=fixed_keys)
        return {"ok": True}

    monkeypatch.setattr(scoring, "score_round", _score_round)
    args = argparse.Namespace(policies=False, round_file=str(round_file), compare=False, json=True, policy="v1_doc")

    assert agent_cli.cmd_season_score(args) == 0

    assert seen["claims"] == claims
    assert seen["verifications"] == [{"v": 1}]
    assert seen["uptime"] == {"p1": 1.0}
    assert seen["fixed_keys"] == {"k1"}
    assert json.loads(capsys.readouterr().out) == {"ok": True}
