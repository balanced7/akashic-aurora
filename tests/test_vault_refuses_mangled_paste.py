"""The vault refuses a MANGLED paste, not merely a multi-line one.

2026-08-19, measured on a real credential Daniil pasted through the window: 109 bytes,
correct sk-ant-oat prefix, and one ordinary space at position 79 splitting it 79 + 29.
No OAuth token contains a space. The paste had wrapped, and `tk.Entry` is a SINGLE-LINE
widget, so it normalized the newline into a space before save_secret ever saw it.

The existing guard is not wrong -- it refuses "\n" and "\r" with a good message. It simply
sits DOWNSTREAM OF A WIDGET THAT DESTROYS THE EVIDENCE IT LOOKS FOR. So the vault wrote the
file and printed "saved 109 byte(s) -- the value exists in exactly one place": true about
the bytes, false about the credential, which is this house's whole recurring wound.

Closed at the organ rather than the widget: every entry path (window, --stdin, any future
door) passes through save_secret, and no allowlisted target -- key, token, snowflake id or
webhook URL -- legitimately contains internal whitespace.

Run:  py -m pytest tests/test_vault_refuses_mangled_paste.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm.secret_intake import IntakeError, save_secret  # noqa: E402

# the real shape of the defect, reconstructed without the real secret
HEAD, TAIL = "sk-ant-oat01-" + "A" * 66, "B" * 29
MANGLED = f"{HEAD} {TAIL}"
CLEAN = HEAD + TAIL


@pytest.fixture(autouse=True)
def _isolated_vault(tmp_path, monkeypatch):
    """AKASHIC_SECRETS_DIR, always: a credential pin one ambient file away from the real
    vault is how a test once minted a live thread in his server."""
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path / "vault"))


def test_refuses_the_space_a_wrapped_paste_leaves_behind():
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", MANGLED)
    assert "whitespace" in str(e.value).lower(), str(e.value)


def test_the_refusal_names_the_position_so_he_can_see_the_wrap():
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", MANGLED)
    assert "79" in str(e.value), str(e.value)


def test_the_refusal_never_echoes_the_credential():
    """This module's entire premise: values travel window -> file, never a transcript.
    A helpful error message is the most likely place for that promise to break."""
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", MANGLED)
    msg = str(e.value)
    assert HEAD not in msg and TAIL not in msg, "the refusal leaked the value"
    assert "sk-ant-oat" not in msg, "the refusal leaked the prefix"


def test_a_tab_is_the_same_defect_wearing_a_different_character():
    with pytest.raises(IntakeError):
        save_secret("claude_oauth.token", f"{HEAD}\t{TAIL}")


def test_the_original_newline_guard_still_refuses():
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", f"{HEAD}\n{TAIL}")
    assert "line" in str(e.value).lower(), str(e.value)


def test_a_clean_token_still_saves():
    r = save_secret("claude_oauth.token", f"  {CLEAN}  ")
    assert r["bytes"] == len(CLEAN), r
    assert Path(r["path"]).read_text(encoding="utf-8") == CLEAN


def test_a_webhook_url_still_saves_no_false_positive():
    """The floor: punctuation-heavy legitimate values must not trip the new guard."""
    url = "https://discord.com/api/webhooks/1539625/AbC-_123.xyz"
    r = save_secret("discord_webhook.url", url)
    assert Path(r["path"]).read_text(encoding="utf-8") == url


# ------------------------------------------- the BOM, which I added to his vault myself
def test_refuses_a_byte_order_mark_from_a_shell_pipe():
    """Earned the hard way, minutes after the space: piping the joined token through a
    PowerShell 5.1 pipe wrote 111 bytes for a 108-char value -- str.strip() does not treat
    U+FEFF as whitespace, so the BOM sailed straight through the existing guards and the
    receipt cheerfully reported the inflated count."""
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", "﻿" + CLEAN)
    msg = str(e.value).lower()
    assert "byte-order mark" in msg or "bom" in msg, str(e.value)


def test_the_bom_refusal_also_keeps_the_value_out_of_the_message():
    with pytest.raises(IntakeError) as e:
        save_secret("claude_oauth.token", "﻿" + CLEAN)
    assert CLEAN not in str(e.value) and "sk-ant-oat" not in str(e.value)
