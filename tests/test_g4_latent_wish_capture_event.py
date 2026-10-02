"""G4.P2 latent ADV-033: `wish` and `wish-curate` emitted their event via an unimported name.

`capture_event` was never imported in `cmd_wish` / `cmd_wish_curate`; the call sat inside
`contextlib.suppress(Exception)`, so the NameError vanished and no wish event was ever logged.
"""

import argparse
import os
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.events import event_log

LEDGER = "# Wishlist\n\n## Open\n\n- [ ] W01 (07-18, claude) — an old wish.\n\n## Folded\n\n## Declined\n\n"


def _ledger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, mock.Mock]:
    """Write a throwaway WISHLIST.md and stand a recorder in for capture_event."""
    ledger = tmp_path / "WISHLIST.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_WISHLIST_FILE", str(ledger))
    recorder = mock.Mock()
    monkeypatch.setattr(event_log, "capture_event", recorder)
    return ledger, recorder


def test_wish_filing_captures_an_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Filing a wish logs one 'wish' event naming the new id."""
    ledger, recorder = _ledger(monkeypatch, tmp_path)
    args = argparse.Namespace(agent_id="claude", text_file=None, text=["a", "new", "wish"], trigger=None, land=None)

    assert agent_cli.cmd_wish(args) == 0

    assert "W02" in ledger.read_text(encoding="utf-8")
    recorder.assert_called_once()
    (kind, summary), kw = recorder.call_args
    assert kind == "wish"
    assert "filed W02" in summary
    assert kw["detail"]["wish"] == "W02"


def test_wish_curate_captures_an_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Curating a wish logs one 'wish' event naming the wish and the disposition."""
    ledger, recorder = _ledger(monkeypatch, tmp_path)
    args = argparse.Namespace(agent_id="claude", wish_id="W01", as_="keep", reason="still wanted", task=None)

    assert agent_cli.cmd_wish_curate(args) == 0

    assert "STILL OPEN" in ledger.read_text(encoding="utf-8")
    recorder.assert_called_once()
    (kind, summary), kw = recorder.call_args
    assert kind == "wish"
    assert "curated W01: keep" in summary
    assert kw["detail"]["action"] == "keep"
