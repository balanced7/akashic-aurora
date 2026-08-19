"""Secret-intake pins — the credential window's laws (RED committed alone, M3).

Daniil, 1:40am 2026-08-19, verbatim: "can we make some kind of pop up window for
credential capture that I can paste into and you can invoke with a verb?" — designed
tired, and correct: both standing credential wounds in this house (the PAT, the
sk-proj key) entered the world as chat pastes. The intake takes the paste OUT OF BAND:
window -> file, never transcript, never corpus.

Laws:
  P1  the target name is an ALLOWLIST lookup, never a path — traversal refused.
  P2  the value lands in the file exactly (stripped, one line), nowhere else.
  P3  the receipt names the byte COUNT, never the bytes — the confirmation itself
      must be safe to print, log, and forward.
  P4  empty paste refuses — a blank credential file is worse than an absent one
      (absent refuses loudly downstream; blank authenticates as garbage).

The tkinter window is a thin unpinned shell; everything decidable lives in
core/comm/secret_intake.py where these pins can reach it.

Run:  py -m pytest tests/test_secret_intake_pins.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _mod():
    try:
        from core.comm import secret_intake
    except ImportError:
        pytest.fail("core.comm.secret_intake missing — the intake is not built (RED)")
    return secret_intake


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    return tmp_path


def test_p1_target_is_an_allowlist_not_a_path(vault):
    m = _mod()
    for evil in ("../../evil", "..\\evil", "x/../../y", "nope.txt", "unknown_target"):
        with pytest.raises(Exception):
            m.save_secret(evil, "value123456")
    assert not list(vault.glob("**/*evil*")), "traversal must write NOTHING"


def test_p2_value_lands_exactly_and_only_in_the_file(vault):
    m = _mod()
    m.save_secret("discord_operator_id", "  123456789012345678\n")
    f = vault / "discord_operator_id"
    assert f.read_text(encoding="utf-8") == "123456789012345678", (
        "stripped, one line, byte-exact — the file IS the delivery")


def test_p3_the_receipt_never_carries_the_bytes(vault):
    m = _mod()
    receipt = m.save_secret("discord_operator_id", "998877665544332211")
    assert "998877665544332211" not in str(receipt), (
        "the receipt must be safe to print into a transcript — count, target, "
        "never content")
    assert "18" in str(receipt.get("bytes", "")) or receipt.get("bytes") == 18


def test_p4_empty_paste_refuses(vault):
    m = _mod()
    with pytest.raises(Exception):
        m.save_secret("discord_operator_id", "   \n ")
    assert not (vault / "discord_operator_id").exists(), (
        "a blank credential file authenticates as garbage downstream — refuse "
        "and leave absence, which at least refuses loudly")
