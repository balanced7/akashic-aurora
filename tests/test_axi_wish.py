"""Pins for `wish` after the AXI conversion: the filing receipt and the refusals, as an agent
and a person see them. Every case files into a throwaway ledger (AKASHIC_WISHLIST_FILE).

Run: uv run pytest tests/test_axi_wish.py -q
"""

import argparse

import pytest

import agent_cli

LEDGER = """# WISHLIST -- test double

## Open

- [ ] W01 (07-18, claude) — Make recall faster.
- [ ] W02 (07-20, kimi) — Show lock ttl.
- [ ] W02 (07-21, sol) — A duplicate id.

## Folded

## Declined
"""


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "WISHLIST.md"
    p.write_text(LEDGER, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_WISHLIST_FILE", str(p))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr("core.events.event_log.capture_event", lambda *a, **k: None)
    return p


def _wish(capsys, *words, agent="bench", **kw):
    ns = argparse.Namespace(agent_id=agent, text=list(words), text_file=None, trigger="", land="")
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_wish(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_filing_is_a_receipt_with_the_collision_warning(ledger, capsys):
    code, text = _wish(capsys, "make", "status", "faster", trigger="slow")
    assert code == 0
    assert text.startswith("filed: W03\nby: bench\nledger: WISHLIST.md\nwarning:")
    assert "W02 each appear more than once" in text
    assert "wish-curate bench" in text
    assert "- [ ] W03" in ledger.read_text(encoding="utf-8")


def test_an_empty_wish_is_a_usage_error(ledger, capsys):
    code, text = _wish(capsys)
    assert code == 2
    assert "code: USAGE" in text
    assert 'wish bench "<what would have helped>"' in text


def test_a_missing_ledger_is_not_found(ledger, capsys):
    ledger.unlink()
    code, text = _wish(capsys, "x")
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_human_receipt(ledger, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _wish(capsys, "x")
    assert "Wish · filed" in text
    assert "W03" in text
