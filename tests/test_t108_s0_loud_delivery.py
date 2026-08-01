"""T108 slice 0 -- make mail failures LOUD (2026-08-01, Daniil-directed).

His diagnosis, verbatim: "sooner or later we will need to fix our mail so our operating logic
can be simpler. I think we are underestimating its cost."

He is right, and the cost is measurable. One session, 2026-08-01: ~14 wake-watcher arms; three
seats dead without anyone noticing (deepseek 2h11m, kimi timed out twice, opus-engineer ghosted);
TWO briefs delivered to corpses and reported as dispatched; one cross-seat deadlock whose unlock
failure was swallowed; a third redelivery of one ask; 33-55 unread all night.

The count is not the cost. The cost is that EVERY ONE WAS INVISIBLE UNTIL SOMETHING ELSE BROKE,
so the conductor's operating logic grew a compensating branch for each: drain-before-arm, check
the roster before trusting a send, re-verify what a seat claimed. Those branches are the tax.
Deleting them is the goal -- and a branch can only be deleted once the transport reports honestly.

This slice does NOT change transport semantics and needs no fence: durable mail to an OFFLINE
seat stays legal (that is what handoffs are for). It makes the sender's ignorance impossible.

Run: py -m pytest tests/test_t108_s0_loud_delivery.py -q
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def test_send_to_a_dead_seat_warns(monkeypatch, capsys):
    """Delivery is not receipt. A send to a seat with no live heartbeat must SAY SO.

    Live receipt: an `interrupt` -- the highest fidelity below halt -- was sent to deepseek at
    2026-08-01 and reported as dispatched. Its seat had been dead 2h11m. The message landed in a
    mailbox nobody was reading, and nothing anywhere said so; the conductor only discovered it
    when the operator asked why the work had not happened.
    """
    from core.comm import bus as B
    b = B.Bus.__new__(B.Bus)                      # no connect; we only exercise the warn path
    monkeypatch.setattr(b, "_recipient_liveness", lambda to: (False, 7886.0), raising=False)
    warned = b._warn_if_unattended("deepseek")
    assert warned, "a send to a 2h-dead seat produced no warning at all"
    out = (capsys.readouterr().err or "") + (capsys.readouterr().out or "")
    assert "deepseek" in warned and ("dead" in warned.lower() or "unattended" in warned.lower()), warned


def test_send_to_a_live_seat_is_silent(monkeypatch):
    """The warning must fire ONLY on the real condition, or it becomes noise people mute."""
    from core.comm import bus as B
    b = B.Bus.__new__(B.Bus)
    monkeypatch.setattr(b, "_recipient_liveness", lambda to: (True, 12.0), raising=False)
    assert not b._warn_if_unattended("kimi"), "warned about a live seat -- this is how guards get muted"


def test_liveness_probe_failure_does_not_block_the_send(monkeypatch):
    """Fail OPEN on a broken probe. A transport that refuses to send because it cannot check
    liveness is worse than one that sends blind -- durable mail to an offline seat is LEGAL."""
    from core.comm import bus as B
    b = B.Bus.__new__(B.Bus)

    def boom(to):
        raise RuntimeError("redis down")
    monkeypatch.setattr(b, "_recipient_liveness", boom, raising=False)
    assert b._warn_if_unattended("anyone") is None, "a probe crash must not become a send failure"


def test_unlock_failure_is_not_swallowed(monkeypatch):
    """kimi traced this one to source across six bounces while it was blocking deepseek:
    toolbox.release_written_locks swallowed EVERY exception (`except Exception: pass`), so a
    failing unlock left a stale lock that froze a peer and nothing anywhere paged. Its words:
    'a failed unlock should be loud.'"""
    from core.comm import toolbox as T
    tb = T.ToolBox.__new__(T.ToolBox)
    tb.agent_id = "kimi"
    tb._written_lock_paths = ["scripts/bifrost_ui.py"]

    def boom(argv, timeout=15):
        raise RuntimeError("cli exploded")
    monkeypatch.setattr(tb, "_agent_cli", boom, raising=False)
    problems = []
    monkeypatch.setattr(T, "_loud", lambda msg: problems.append(msg), raising=False)

    tb.release_written_locks()
    assert problems, "an unlock that threw was swallowed silently -- the peer-freezing defect"
    assert "bifrost_ui.py" in problems[0], "the report names no path, so nobody can act on it"


def test_the_real_probe_is_wired_not_just_the_monkeypatched_one():
    """THE PIN THAT WOULD HAVE CAUGHT MY OWN NO-OP.

    The four pins above all monkeypatch `_recipient_liveness`, so every one passed while the REAL
    method raised AttributeError on every call (`self.r` -- an attribute Bus does not have; the
    client is `_client`). My own fail-open then swallowed it, so a loudness fix shipped as a
    silent no-op and I reported it as working. Verified live only because a probe send stayed
    quiet against a seat dead 2h+.

    The transferable shape: FAIL-OPEN + MONKEYPATCHED PINS = AN INVISIBLE NO-OP. Whenever a guard
    swallows its own errors by policy, at least one pin must exercise the UNPATCHED path, or the
    guard's absence is indistinguishable from its silence -- which is the exact defect class the
    guard was written to end.
    """
    from core.comm import bus as B
    b = B.Bus("claude")
    try:
        live, age = b._recipient_liveness("claude")     # the real probe, no monkeypatch
    except Exception as e:
        raise AssertionError(
            f"the REAL liveness probe raised {type(e).__name__}: {e} -- with fail-open this "
            "means the warning never fires in production, no matter how green the other pins are"
        )
    assert isinstance(live, bool), f"probe returned a non-bool liveness: {live!r}"
    assert age is None or isinstance(age, (int, float)), f"probe returned a bad age: {age!r}"
