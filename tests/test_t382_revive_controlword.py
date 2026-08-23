"""
T382 -- the !revive control word: pins (the R3 amendment made executable).

  P1  a ROOT gets the lever: !revive acts, reviver called with (None, False),
      the 🚑 receipt fires; !revive daemon passes the validated enum member.
  P2  a NON-ROOT operator is REFUSED (root-only, per the ratified amendment)
      and the reviver is never called -- tier is not authority.
  P3  an unknown target is REFUSED with ❓ and never reaches the script:
      message content cannot become argv (zero passthrough by construction).
  P4  !status-deep = observe_only True (the dry lever).
  P5  a lever with no reviver wired RAISES -- refusing beats pretending.

Run: py -m pytest tests/test_t382_revive_controlword.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import discord_inbound

ROOT_ID = "111222333444555666"
PLAIN_OP = "999888777666555444"


def _cfg():
    return {"operator_id": ROOT_ID,
            "roots": {ROOT_ID: {"agent": "daniil"}},
            "people": {ROOT_ID: {"agent": "daniil", "tier": "operator"},
                       PLAIN_OP: {"agent": "guestop", "tier": "operator"}}}


class _Bus:
    def send(self, *a, **k):
        return "m1-0"

    def broadcast(self, *a, **k):
        return "m1-0"


def _call(text, author=ROOT_ID, reviver="unset"):
    calls = []
    reacts = []
    kwargs = {}
    if reviver == "unset":
        kwargs["reviver"] = lambda t, o: calls.append((t, o))
    elif reviver is not None:
        kwargs["reviver"] = reviver
    out = discord_inbound.handle_message(
        _cfg(), author_id=author, author_name="x", channel_id="c1",
        content=text, bus=_Bus(), react=reacts.append, **kwargs)
    return out, calls, reacts


def test_p1_root_pulls_the_lever():
    out, calls, reacts = _call("!revive")
    assert out.get("acted") and out["revive"] == {"target": None,
                                                  "observe_only": False}
    assert calls == [(None, False)]
    assert "🚑" in reacts
    out, calls, _ = _call("!revive daemon")
    assert calls == [("daemon", False)]


def test_p2_non_root_operator_refused():
    out, calls, _ = _call("!revive", author=PLAIN_OP)
    assert not out.get("acted")
    assert "root-only" in str(out.get("reason", ""))
    assert calls == [], "the reviver must never fire for a non-root"


def test_p3_unknown_target_never_reaches_argv():
    out, calls, reacts = _call("!revive teapot; rm -rf /")
    assert not out.get("acted")
    assert calls == [], "unvalidated content must never reach the script"
    assert "❓" in reacts


def test_p4_status_deep_is_the_dry_lever():
    out, calls, _ = _call("!status-deep")
    assert out["revive"]["observe_only"] is True
    assert calls == [(None, True)]


def test_p5_missing_reviver_raises():
    with pytest.raises(RuntimeError):
        discord_inbound.handle_message(
            _cfg(), author_id=ROOT_ID, author_name="x", channel_id="c1",
            content="!revive", bus=_Bus(), react=lambda e: None)
