"""T366 RED: the resuscitation lever must not inherit a credential that dies on a clock.

Measured 2026-08-19, the night Daniil was unreachable for a day. The chain, in full:
his refreshTokenExpiresAt fell on Aug 15 23:40 UTC; after that the CLI could not refresh,
so every !spawn died ~16s in on "Failed to authenticate"; T365 now makes that death
VISIBLE, but visible is not the same as prevented. He logged in at 20:29 and the new
refresh token expires 2026-09-17 -- twenty-eight days out. So this exact outage has a
DUE DATE, and the only question is whether we meet it with a warning or a silence.

Two organs, both decidable, so both live in core with the pins:
  - a refusal: with NO usable credential, refuse INSTANTLY and name the fix, rather than
    burning 16s to arrive at the same conclusion less helpfully.
  - a horizon: how many days until the credential behind the lever dies, so the fleet can
    say so BEFORE the lever is needed. The recovery path is the one whose failure nobody
    is watching, because by definition you only reach for it when things are already bad.

Run:  py -m pytest tests/test_t366_spawn_credential_preflight.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import discord_inbound as DI      # noqa: E402
from core.comm import secret_intake as SI        # noqa: E402

DAY_MS = 86_400_000
NOW = 1_787_100_000_000            # a fixed clock: pins do not ask the wall what time it is


# ------------------------------------------------------------------- the vault slot
def test_the_vault_has_a_home_for_the_spawn_credential():
    """A long-lived token belongs in the vault, not in a 5-day session file."""
    assert "claude_oauth.token" in SI.TARGETS, sorted(SI.TARGETS)
    blurb = SI.TARGETS["claude_oauth.token"].lower()
    assert "setup-token" in blurb, "the slot must name the command that mints it"


# ---------------------------------------------------------------------- the refusal
def test_refuses_instantly_when_there_is_no_credential_at_all():
    """Known-bad: no vault token AND the CLI says logged out. 16s of waiting adds nothing."""
    reason = DI.spawn_credential_refusal("", cli_logged_in=False)
    assert reason, "a spawn with no credential is a spawn we already know will die"
    assert "login" in reason.lower() or "setup-token" in reason.lower(), reason
    assert "\n" not in reason.strip(), "he reads this on a phone"


def test_a_vault_token_is_enough_on_its_own():
    """The whole point: the vault outlives the interactive session's expiry."""
    assert DI.spawn_credential_refusal("sk-ant-oat-XXXX", cli_logged_in=False) is None


def test_a_logged_in_cli_is_enough_on_its_own():
    """No vault token needed while the CLI itself can authenticate -- today's happy path."""
    assert DI.spawn_credential_refusal("", cli_logged_in=True) is None


def test_unknown_cli_state_never_refuses():
    """Fail-OPEN on ignorance. A probe that times out must not become a gate that blocks
    every spawn -- refuse only on a KNOWN bad state. T365 catches what we let through."""
    assert DI.spawn_credential_refusal("", cli_logged_in=None) is None


# ---------------------------------------------------------------------- the horizon
def test_horizon_counts_the_days_behind_the_lever():
    creds = {"claudeAiOauth": {"refreshTokenExpiresAt": NOW + 28 * DAY_MS}}
    assert abs(DI.credential_horizon_days(creds, NOW) - 28.0) < 0.01


def test_horizon_goes_negative_once_the_credential_is_dead():
    """Aug 15's token, read on Aug 19: four days dead, and the number must SAY so."""
    creds = {"claudeAiOauth": {"refreshTokenExpiresAt": NOW - 4 * DAY_MS}}
    assert DI.credential_horizon_days(creds, NOW) < 0


def test_horizon_is_none_when_it_cannot_be_read():
    """Absent, malformed, wrong shape -- unknown is a state, not a zero. A zero here would
    read as 'expires today' and cry wolf on every boot."""
    for bad in ({}, {"claudeAiOauth": {}}, {"claudeAiOauth": {"refreshTokenExpiresAt": "soon"}}):
        assert DI.credential_horizon_days(bad, NOW) is None, bad


def test_warning_stays_quiet_until_the_cliff_is_close():
    assert DI.credential_warning(28.0) is None, "28 days out is not news"
    assert DI.credential_warning(None) is None, "unknown is not a warning either"


def test_warning_names_the_days_and_the_fix_when_close():
    warn = DI.credential_warning(3.0)
    assert warn and "3" in warn, warn
    assert "setup-token" in warn.lower() or "login" in warn.lower(), warn


def test_warning_fires_hardest_when_already_expired():
    warn = DI.credential_warning(-4.0)
    assert warn, "a dead credential is the loudest case, not a silent one"
    assert "expired" in warn.lower(), warn
