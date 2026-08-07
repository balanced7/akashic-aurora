"""
T201 -- the unread counter must count what its own remediation would surface. RED first.

MEASURED 2026-08-06, three times in one session. The turn-start whisper said "[akashic]
mail: 7 unread bus msg(s) -> py agent_cli.py bifrost-sync claude". Running that command
on BOTH lanes returned "(no messages consumed)" each time. The 7 were ledger_update and
resolved broadcasts -- the conductor's control-plane echoes of THIS agent's own ledger
transitions, emitted by its own task done/approve/claim calls minutes earlier.

THREE SURFACES, ONE QUESTION, TWO ANSWERS:
  * the wake watcher   SKIPS these kinds (SKIP_KINDS_LANE) -- correct, an echo of your
                       own ledger write must never wake a seat
  * the consume door   does not surface them -- correct
  * this counter       counts them RAW -- so it nags every single turn, and the command
                       it prints cannot clear what it is nagging about

WHY THAT IS WORSE THAN A WRONG NUMBER. It is the W131 pathology in a second organ: an
alert that fires constantly and whose stated fix does nothing trains the reader to skip
the line, and that habit transfers unchanged to the turn when the count means real mail.
A counter that cries wolf disarms itself, and this one had been crying on the agent's own
echoes.

THE PREDICATE, stated so it cannot drift: the counter reports what `bifrost-sync` would
SURFACE. It reuses the SAME constant the other two surfaces use (bifrost_api
.PENDING_SKIP_KINDS, already pinned equal to bifrost_wake.SKIP_KINDS_LANE by parity pin
L7) rather than inventing a third filter -- the T198 lesson applied where it is safe.

DIRECTION OF FAILURE IS DELIBERATE AND OPPOSITE TO T198's. There, narrowing risked
DEAFNESS, so the fix was left unbuilt. Here the surface is a nag line, the wake path is
untouched, and boot's fuller surfaces still render mail -- so the safe direction is to
OVER-report. Hence: anything not provably skippable counts, and a truncated peek adds its
unseen remainder back rather than hiding it.

Run: py -m pytest tests/test_t201_unread_counter_honesty.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness import context as ctx  # noqa: E402


def _m(kind, frm="conductor", content="x"):
    return {"kind": kind, "frm": frm, "content": content}


@pytest.fixture
def fake_collect(monkeypatch):
    """Swap the bus read so the counter is tested on constructed evidence, never live."""
    def _install(pending, messages):
        def fake(agent_id, limit=8):
            return {"pending": pending, "messages": messages}
        monkeypatch.setattr("agent.bifrost_pull.collect_boot_bifrost", fake)
    return _install


def test_control_plane_echoes_do_not_count(fake_collect):
    """THE MEASURED CASE. Seven of the agent's own ledger echoes must read as zero --
    silent-at-0 is the existing contract, so the whisper line disappears entirely."""
    msgs = [_m("ledger_update")] * 5 + [_m("resolved")] + [_m("ledger_update")]
    fake_collect(7, msgs)
    assert ctx._unread_count("claude") == 0


def test_real_mail_still_counts(fake_collect):
    fake_collect(3, [_m("request", frm="daniil"), _m("handoff", frm="deepseek"),
                     _m("ledger_update")])
    assert ctx._unread_count("claude") == 2


def test_mixed_counts_only_the_actionable(fake_collect):
    fake_collect(4, [_m("reply", frm="deepseek"), _m("trace"), _m("resolved"),
                     _m("ledger_update")])
    assert ctx._unread_count("claude") == 1


def test_a_truncated_peek_adds_its_remainder_back(fake_collect):
    """The peek is limit=8 but `pending` can exceed it. Unseen messages have unknown
    kinds, and this counter fails toward NAGGING -- hiding mail it never looked at would
    be the same defect pointed the other way."""
    fake_collect(20, [_m("ledger_update")] * 8)
    assert ctx._unread_count("claude") == 12, "0 visible + 12 unseen"


def test_unknown_kinds_count(fake_collect):
    """The skip set is an allowlist of things known to be noise. A kind nobody has
    classified yet is assumed actionable -- new kinds must be LOUD by default, which is
    the same ratchet law the wake allowlist follows from the other side."""
    fake_collect(2, [_m("some_new_kind_2026"), _m("ledger_update")])
    assert ctx._unread_count("claude") == 1


def test_no_third_filter_is_invented():
    """One definition, three surfaces. A local literal set here would drift from the
    watcher and the consume door -- exactly the divergence T198 documents."""
    import inspect
    src = inspect.getsource(ctx._unread_count)
    assert "PENDING_SKIP_KINDS" in src, (
        "reuse the shared constant; a hand-written kind set here becomes the third "
        "meaning of 'unread'")
    for literal in ('"ledger_update"', "'ledger_update'", '"resolved"', "'resolved'"):
        assert literal not in src, "no inline kind literals -- that is a new filter"


def test_counter_never_raises_into_the_hook(fake_collect, monkeypatch):
    """The whisper is fail-soft by contract: an unreachable bus means no line, never a
    broken turn."""
    def boom(agent_id, limit=8):
        raise RuntimeError("bus down")
    monkeypatch.setattr("agent.bifrost_pull.collect_boot_bifrost", boom)
    assert ctx._unread_count("claude") == 0


def test_missing_messages_key_falls_back_to_pending(fake_collect):
    """An older/partial payload without a rendered list must not silently report 0 --
    absence of the list is not evidence of absence of mail."""
    def fake(agent_id, limit=8):
        return {"pending": 5}
    import agent.bifrost_pull as bp
    orig = bp.collect_boot_bifrost
    bp.collect_boot_bifrost = fake
    try:
        assert ctx._unread_count("claude") == 5
    finally:
        bp.collect_boot_bifrost = orig
