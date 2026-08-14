"""W165 pins: a settled answer stops being wake-worthy.

THE RECURRING FAULT, measured across one very long session: the stop hook demanded a wake
re-arm fifteen times, and the watcher seeded over the same undrainable set every time --
7, then 9, growing. Two prior seats hit the identical wall and both correctly stopped
re-arming (lesson: settled_answer_stays_wake_worthy_nonconsuming_poll_pins_the_watcher).

THE CAUSE, which is the same shape as everything else in this arc: TWO COMPONENTS DISAGREEING
ABOUT ONE WORD. `ask --peer` polls its answer NON-CONSUMINGLY by law (T196c, so sibling
sessions do not steal each other's mail). The answer settles the expectation and is never
consumed, so `bifrost-sync --consume` truthfully reports "no NEW mail" from its own advanced
cursor while the wake detector -- which reads the stream, not the cursor -- still sees it.

wake_worthy() ALREADY had a notion of handled: a DECLARED INTENT (act/decline/defer/delegate)
on the mailbox. But nobody declares an intent on an ask answer; the ask settles it. So the
gate knew one way a message could be finished and not the other, and the session that fenced
three rounds manufactured three of its own blockers.

THE FIX IS NOT A NEW MARKER. `bifrost:reply_settled:<sender>:<reply_id>` already exists and is
live (8 in prod), written by the T117-P8 once-only settlement path. The predicate that reads
it was a CLOSURE inside sweep(), so nothing outside could ask the question. It becomes a named
module-level function used by both callers -- one source of truth, no duplicated key shape.

FAIL OPEN, and the direction is not negotiable: an unreadable marker must leave the message
wake-worthy. Trading missed mail for a saved re-arm is the worse bug by a wide margin, and the
existing code says so in its own comment two lines above.
"""
import pytest

from core.comm import expectations as E


class _FakeRedis:
    def __init__(self, keys=()):
        self.keys_ = set(keys)

    def exists(self, k):
        return 1 if k in self.keys_ else 0


class _BoomRedis:
    def exists(self, k):
        raise RuntimeError("redis down")


def test_w1_a_settled_reply_is_recognised():
    c = _FakeRedis({f"{E._ns()}:reply_settled:claude:123-0"})
    assert E.reply_has_settled(c, "claude", "123-0") is True


def test_w2_an_unsettled_reply_is_not():
    assert E.reply_has_settled(_FakeRedis(), "claude", "123-0") is False


def test_w3_a_missing_reply_id_is_not_settled():
    """No id means nothing to look up -- must not read as handled."""
    assert E.reply_has_settled(_FakeRedis(), "claude", "") is False
    assert E.reply_has_settled(_FakeRedis(), "claude", None) is False


def test_w4_the_marker_is_scoped_to_the_SENDER():
    """Expectations are per-sender; a reply settled for kimi has not settled mine."""
    c = _FakeRedis({f"{E._ns()}:reply_settled:kimi:123-0"})
    assert E.reply_has_settled(c, "claude", "123-0") is False


def test_w5_an_unreadable_marker_FAILS_OPEN():
    """The direction matters more than the check. A mailbox outage that silenced a seat
    would trade a bookkeeping fault for missed mail, which is far worse than a re-arm."""
    assert E.reply_has_settled(_BoomRedis(), "claude", "123-0") is False


def test_w6_sweep_uses_the_same_predicate_rather_than_its_own_copy():
    """The key shape lived in a closure. Two spellings of one Redis key is how the
    seat_seen/seatseen fork happened earlier in this same arc."""
    import inspect
    src = inspect.getsource(E)
    assert src.count('reply_settled:{') <= 1, (
        "the reply_settled key shape is written more than once -- one source of truth")


# ------------------------------------------------------------------ the gate

def _msg(kind="reply", frm="deepseek", to="claude", meta=None):
    from types import SimpleNamespace as SN
    return SN(kind=kind, frm=frm, to=to, meta=meta or {}, id="123-0")


def test_g1_a_settled_answer_no_longer_wakes_the_seat(monkeypatch):
    """The headline. Without this, a session that fences three rounds pins its own watcher."""
    import scripts.bifrost_wake as W
    monkeypatch.setattr(W, "_reply_is_settled", lambda m, agent: True, raising=False)
    assert W.wake_worthy(_msg(), agent="claude", incarnation="abcd1234") is False


def test_g2_an_unsettled_answer_still_wakes(monkeypatch):
    import scripts.bifrost_wake as W
    monkeypatch.setattr(W, "_reply_is_settled", lambda m, agent: False, raising=False)
    assert W.wake_worthy(_msg(), agent="claude", incarnation="abcd1234") is True


def test_g3_incarnation_addressed_mail_wakes_even_if_settled(monkeypatch):
    """The sender named THIS session explicitly. Explicit addressing outranks every
    downstream filter -- it is the first check in wake_worthy and must stay first."""
    import scripts.bifrost_wake as W
    monkeypatch.setattr(W, "_reply_is_settled", lambda m, agent: True, raising=False)
    m = _msg(meta={"to_incarnation": "abcd1234"})
    assert W.wake_worthy(m, agent="claude", incarnation="abcd1234") is True


def test_g4_the_operator_still_outranks_a_settled_marker(monkeypatch):
    """2026-07-15 incident: Daniel's broadcast rode a quiet kind and every seat slept
    through the human. That override must never gain a second way to be bypassed."""
    import scripts.bifrost_wake as W
    monkeypatch.setattr(W, "_reply_is_settled", lambda m, agent: True, raising=False)
    monkeypatch.setattr(W, "_operator_ids", lambda: {"user"}, raising=False)
    assert W.wake_worthy(_msg(frm="user", kind="inform"), agent="claude",
                         incarnation="abcd1234") is True
