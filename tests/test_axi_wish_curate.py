"""Pins for `wish-curate` after the AXI conversion: the listing, a disposition and a refusal, as
an agent and a person see them. Every case uses a throwaway ledger (AKASHIC_WISHLIST_FILE).

Run: uv run pytest tests/test_axi_wish_curate.py -q
"""

import argparse

import pytest

import agent_cli

LEDGER = """# WISHLIST -- test double

## Open

- [ ] W01 (07-18, claude) — Make recall faster.
- [ ] W02 (07-20, kimi) — Show lock ttl.

## Folded

- [x] W00 (07-01, claude) — The first wish.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
"""


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "WISHLIST.md"
    p.write_text(LEDGER, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_WISHLIST_FILE", str(p))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr("core.events.event_log.capture_event", lambda *a, **k: None)
    return p


def _curate(capsys, **kw):
    ns = argparse.Namespace(agent_id="bench", wish_id=None, as_=None, reason=None, task=None, count=3)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_wish_curate(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_listing_counts_and_the_oldest_open_as_rows(ledger, capsys):
    code, text = _curate(capsys)
    assert code == 0
    assert text.startswith("open: 2\nfolded: 1\ndeclined: 0\nnote:")
    assert "oldest_open[2]{id,filed,by,wish}:\n  W01,07-18,claude,Make recall faster." in text
    assert "wish-curate bench --id W## --as decline --reason" in text


def test_a_decline_is_a_receipt_and_moves_the_wish(ledger, capsys):
    code, text = _curate(capsys, wish_id="W01", as_="decline", reason="not worth it")
    assert code == 0
    assert "curated: W01\nas: decline" in text
    assert "- [~] W01" in ledger.read_text(encoding="utf-8")


def test_a_decline_without_a_reason_is_refused_and_writes_nothing(ledger, capsys):
    before = ledger.read_text(encoding="utf-8")
    code, text = _curate(capsys, wish_id="W01", as_="decline")
    assert code == 2
    assert "code: REFUSED" in text
    assert ledger.read_text(encoding="utf-8") == before


def test_human_listing_is_a_table(ledger, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _curate(capsys)
    assert "Wishlist curation" in text
    assert "W02" in text
