"""G4.P2 latent: `arsenal floors --dir D --json` crashed with UnboundLocalError.

`hard` (the failing receipts that set the exit code) was only computed in the human-readable branch, so the
JSON branch reached `return 0 if not hard else 1` with `hard` unbound.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

from arsenal import __main__ as arsenal_main
from arsenal import floors as fl_mod


def _receipts(verdicts):
    return [{"frame": f"f{i}.png", "pass": v == "pass", "verdict": v, "results": []} for i, v in enumerate(verdicts)]


def _run(monkeypatch, tmp_path, verdicts):
    receipts = _receipts(verdicts)
    monkeypatch.setattr(fl_mod, "sweep", lambda *a, **k: receipts)
    monkeypatch.setattr(fl_mod, "summarise", lambda r: {"frames": len(r)})
    return arsenal_main.main(["floors", "--dir", str(tmp_path), "--json"])


def test_floors_json_exits_zero_when_every_frame_passes(monkeypatch, tmp_path, capsys):
    assert _run(monkeypatch, tmp_path, ["pass", "pass"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"] == {"frames": 2}


def test_floors_json_exits_one_on_a_failing_frame(monkeypatch, tmp_path, capsys):
    assert _run(monkeypatch, tmp_path, ["pass", "fail"]) == 1
    assert len(json.loads(capsys.readouterr().out)["receipts"]) == 2
