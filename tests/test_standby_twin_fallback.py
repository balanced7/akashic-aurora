"""The twin fallback's pins: a session whose agent id is already consumed must still be reachable.

THE DEFECT THIS FILE PINS (2026-10-30 wish, phase 3 of the modular-core detangle):

    "`bifrost-standby` twin fallback: when a twin holds the consumer seat it exits 1 'NOT
     listening', so this session silently can't be reached. It should arm the per-session
     (incarnation) listener and say who holds the seat."

Two facts make that a real hole rather than a cosmetic one. RB-21 says one session CONSUMES per
agent id -- correctly, so cursors cannot diverge -- and `bifrost-standby` used to read that rule as
"then this session has nothing to do", exiting 1 and leaving a live session nobody could wake.

So the pins below hold three separate promises apart, because a fix that satisfied any one of them
alone would be the wrong fix:

  1. THE SESSION BECOMES REACHABLE. A twin-held seat now arms the per-session listener (decision
     `twin-holds-seat-incarnation-listen`, exit 0) and the report carries the exact
     `bifrost-send ... --to-incarnation <sid8>` command.
  2. THE ONE-CONSUMER RULE STANDS. The armed listener admits ONLY incarnation-addressed mail, so
     agent-wide mail still wakes exactly one seat and cannot double-wake. Pinned at the admission
     rule itself (scripts/bifrost_wake.admits), not at a comment about it.
  3. THE OLD REPORT-ONLY PATH IS STILL THERE and still honest: `--no-listen` says NOT listening
     and how to become reachable, instead of the old silence.

Run: py tests/test_standby_twin_fallback.py   (or via pytest)
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent import bifrost_pull                                               # noqa: E402


def _wake_module():
    """scripts/bifrost_wake.py as a module (it is a script, not a package import)."""
    path = os.path.join(ROOT, "scripts", "bifrost_wake.py")
    spec = importlib.util.spec_from_file_location("bifrost_wake_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Msg:
    def __init__(self, **kw):
        self.id = kw.pop("id", "1-0")
        self.frm = kw.pop("frm", "peer")
        self.to = kw.pop("to", "seat")
        self.kind = kw.pop("kind", "chat")
        self.content = kw.pop("content", "hello")
        self.ts = kw.pop("ts", "2026-10-30T10:00:00")
        self.meta = kw.pop("meta", {})
        self.parts = []


# --------------------------------------------------------------- 1. the session is reachable
def test_a_twin_held_seat_arms_the_incarnation_listener(monkeypatch):
    calls = []

    def _listen(agent_id, session_id, incarnation_only=False):
        calls.append({"agent": agent_id, "session": session_id,
                      "incarnation_only": incarnation_only})
        return 0

    monkeypatch.setattr(bifrost_pull, "consume_inbox",
                        lambda agent_id, limit=20: {"seat_held": True, "holder": "session:twin-xyz",
                                                    "since": "2026-10-30T09:00:00", "ttl": 900,
                                                    "teach": "CONSUMER SEAT HELD (twin)",
                                                    "peeked": [_Msg()]})
    out = bifrost_pull.standby("pin_seat", "sess-abcdefgh", listen=_listen)

    assert out["decision"] == "twin-holds-seat-incarnation-listen", out
    assert out["listened"] is True
    assert out["listen_rc"] == 0
    assert calls == [{"agent": "pin_seat", "session": "sess-abcdefgh", "incarnation_only": True}], calls

    report = "\n".join(out["report"])
    assert "HELD by session:twin-xyz" in report, report
    assert "--to-incarnation" in report, "the report must print HOW to reach this session"
    assert "--to-incarnation" in out["reach"] and out["reach"].startswith("py agent_cli.py bifrost-send")


def test_report_only_still_says_not_listening_and_offers_the_path(monkeypatch):
    monkeypatch.setattr(bifrost_pull, "consume_inbox",
                        lambda agent_id, limit=20: {"seat_held": True, "holder": "session:twin",
                                                    "teach": "CONSUMER SEAT HELD (twin)"})
    out = bifrost_pull.standby("pin_seat", "sess-abcdefgh", listen=None)
    assert out["decision"] == "twin-holds-seat"
    assert out["listened"] is False
    report = "\n".join(out["report"])
    assert "NOT listening (report-only)" in report
    assert "--to-incarnation" in report, "even the report-only path must name a way back in"


def test_the_listener_argv_carries_the_flag_only_when_asked():
    import agent_cli
    plain = agent_cli.standby_listener_argv("pin_seat", "sid-1234", 2)
    twin = agent_cli.standby_listener_argv("pin_seat", "sid-1234", 2, incarnation_only=True)
    assert "--incarnation-only" not in plain, plain
    assert "--incarnation-only" in twin, twin
    # the rest of the command is untouched, so the ordinary arm cannot drift with this change
    assert [a for a in twin if a != "--incarnation-only"] == plain


# --------------------------------------------------- 2. the one-consumer rule still stands
def test_incarnation_addressed_is_explicit_addressing_only():
    W = _wake_module()
    me = "sess-abcdefgh"
    assert W.incarnation_addressed(_Msg(meta={"to_incarnation": "sess-abcdefgh"}), incarnation=me)
    assert W.incarnation_addressed(_Msg(meta={"to_incarnation": "sess-abcd"}), incarnation=me), \
        "an 8-char prefix is the documented addressing form (>=8 chars)"
    assert not W.incarnation_addressed(_Msg(meta={"to_incarnation": "other-1234"}), incarnation=me)
    assert not W.incarnation_addressed(_Msg(meta={"to_incarnation": "shrt"}), incarnation=me), \
        "a prefix shorter than 8 is not an address"
    assert not W.incarnation_addressed(_Msg(meta={}), incarnation=me)
    assert not W.incarnation_addressed(_Msg(meta={"to_incarnation": me}), incarnation="")


def test_the_fallback_arm_narrows_and_never_widens(monkeypatch):
    """The heart of it: an agent-wide operator message must NOT wake an incarnation-only arm,
    while the same message still wakes an ordinary arm (no regression) -- and an addressed
    message wakes BOTH modes."""
    W = _wake_module()
    me = "sess-abcdefgh"
    operator_mail = _Msg(frm="user", to="pin_seat", kind="chat", content="are you there?")
    addressed = _Msg(frm="peer", to="pin_seat", kind="chat", meta={"to_incarnation": me})

    assert W.admits(operator_mail, agent="pin_seat", incarnation=me, incarnation_only=False), \
        "an ordinary arm must still wake on the operator"
    assert not W.admits(operator_mail, agent="pin_seat", incarnation=me, incarnation_only=True), \
        "the twin-fallback arm must NOT wake on agent-wide mail -- that would double-wake beside " \
        "the seat-holder, which is exactly what the one-consumer rule exists to prevent"
    assert W.admits(addressed, agent="pin_seat", incarnation=me, incarnation_only=True)
    assert W.admits(addressed, agent="pin_seat", incarnation=me, incarnation_only=False)


# ------------------------------------------------------------ 3. the exit code tells the truth
def test_the_cli_exit_code_distinguishes_reachable_from_dark(monkeypatch):
    import agent_cli
    args = types.SimpleNamespace(agent_id="pin_seat", session="sess-abcdefgh", no_listen=True,
                                 limit=20, min_tier=None)
    # report-only, twin holds the seat: exit 1 -- NOT reachable, and now it says how to be
    monkeypatch.setattr("agent.bifrost_pull.standby",
                        lambda *a, **kw: {"decision": "twin-holds-seat", "drained": 0,
                                          "report": ["seat: HELD"], "listened": False})
    assert agent_cli.cmd_bifrost_standby(args) == 1

    # the incarnation listener armed: exit 0 -- the session IS reachable now
    monkeypatch.setattr("agent.bifrost_pull.standby",
                        lambda *a, **kw: {"decision": "twin-holds-seat-incarnation-listen",
                                          "drained": 0, "report": ["seat: HELD"],
                                          "listened": True, "listen_rc": 0})
    assert agent_cli.cmd_bifrost_standby(args) == 0


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
