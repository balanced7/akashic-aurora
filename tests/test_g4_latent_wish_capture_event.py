"""G4.P2 latent ADV-033: `wish` and `wish-curate` emitted their event via an unimported name.

`capture_event` was never imported in `cmd_wish` / `cmd_wish_curate`; the call sat inside
`contextlib.suppress(Exception)`, so the NameError vanished and no wish event was ever logged.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.events import event_log

LEDGER = "# Wishlist\n\n## Open\n\n- [ ] W01 (07-18, claude) — an old wish.\n\n## Folded\n\n## Declined\n\n"


def _record(monkeypatch):
    calls = []
    monkeypatch.setattr(event_log, "capture_event", lambda kind, summary, **kw: calls.append((kind, summary, kw)))
    return calls


def test_wish_filing_captures_an_event(monkeypatch, tmp_path):
    ledger = tmp_path / "WISHLIST.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_WISHLIST_FILE", str(ledger))
    calls = _record(monkeypatch)
    args = argparse.Namespace(agent_id="claude", text_file=None, text=["a", "new", "wish"], trigger=None, land=None)

    assert agent_cli.cmd_wish(args) == 0

    assert "W02" in ledger.read_text(encoding="utf-8")
    assert len(calls) == 1
    kind, summary, kw = calls[0]
    assert kind == "wish"
    assert "filed W02" in summary
    assert kw["detail"]["wish"] == "W02"


def test_wish_curate_captures_an_event(monkeypatch, tmp_path):
    ledger = tmp_path / "WISHLIST.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_WISHLIST_FILE", str(ledger))
    calls = _record(monkeypatch)
    args = argparse.Namespace(agent_id="claude", wish_id="W01", as_="keep", reason="still wanted", task=None)

    assert agent_cli.cmd_wish_curate(args) == 0

    assert "STILL OPEN" in ledger.read_text(encoding="utf-8")
    assert len(calls) == 1
    kind, summary, kw = calls[0]
    assert kind == "wish"
    assert "curated W01: keep" in summary
    assert kw["detail"]["action"] == "keep"
