"""G4.P2 latent: `arsenal floors --dir D --json` crashed with UnboundLocalError.

`hard` (the failing receipts that set the exit code) was only computed in the human-readable branch, so the
JSON branch reached `return 0 if not hard else 1` with `hard` unbound.
"""

import json
import os
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

from arsenal import __main__ as arsenal_main
from arsenal import floors as fl_mod


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, receipts: list[dict]) -> int:
    """`floors --dir tmp --json` over the given receipts, with the sweep and summary stubbed."""
    monkeypatch.setattr(fl_mod, "sweep", mock.Mock(return_value=receipts))
    monkeypatch.setattr(fl_mod, "summarise", mock.Mock(return_value={"frames": len(receipts)}))
    return arsenal_main.main(["floors", "--dir", str(tmp_path), "--json"])


def _receipt(verdict: str) -> dict:
    """One frame's receipt with the given verdict."""
    return {"frame": "f.png", "pass": verdict == "pass", "verdict": verdict, "results": []}


def test_floors_json_exits_zero_when_every_frame_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every frame passing: exit 0, and the JSON carries the summary."""
    receipts = [_receipt("pass"), _receipt("pass")]
    assert _run(monkeypatch, tmp_path, receipts) == 0
    assert json.loads(capsys.readouterr().out)["summary"] == {"frames": len(receipts)}


def test_floors_json_exits_one_on_a_failing_frame(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One frame failing: exit 1, and the JSON still lists every receipt."""
    receipts = [_receipt("pass"), _receipt("fail")]
    assert _run(monkeypatch, tmp_path, receipts) == 1
    assert len(json.loads(capsys.readouterr().out)["receipts"]) == len(receipts)
