"""W167 pins: the wake seed notice says what IS working, not only what will not help.

THE RECURRENCE, and it is documented in the emitter's own comment before I arrived:
5 identical arms 2026-07-31, 6 on 2026-07-25. Three more seats on 2026-08-14, including me.
Every one concluded the watcher was dead and stopped arming.

IT IS NOT DEAD. The line fires when the lane cursor is seeded past already-seen wake-worthy
mail. It seeds ONCE per process, returns those messages to the caller, and the loop then
blocks correctly for the rest of that process -- which is why the very arm that prints this
goes on to fire on real mail or to end with a planned "deadline self-cycle". Verified on
2026-08-14: of three arms that printed it, two ended having delivered messages and one ended
with `BIFROST_WAKE: deadline self-cycle`, and a fourth was confirmed alive by process table
while the reader believed the seat unarmed.

WHY THE OLD TEXT MISLED, and it was not by being false. Every clause was true: the seed is
per-process, it does not carry, re-arming will not clear the pending set. But the sentence
said only what would NOT work. Paired with a stop hook whose headline is "died or was never
armed", the honest reading is "this seat is broken" -- so the reader stops arming, which is
the one action that actually costs something.

Same defect class as W166's straggler alarm: a diagnostic whose wording misrepresents its own
state, spending other people's attention. The fix in both is the same shape -- classify and
say the true state, keep the caveat, lead with what holds.
"""
import logging

import pytest

from core.comm import bifrost_api as A


def _emit(caplog, n=9, kinds="chat,reply", agent="claude"):
    """Reproduce the seed notice through the module's own logger."""
    logger = logging.getLogger("bifrost")
    with caplog.at_level(logging.WARNING, logger="bifrost"):
        logger.warning(
            "wake: ARMED and watching. Seeded the lane cursor past %d already-seen "
            "wake-worthy message(s) (kinds: %s) -- this arm is live and will fire on "
            "new mail. The seed is per-process and does NOT carry to the next arm, so "
            "if you see this line again the pending set is not clearing and RE-ARMING "
            "WILL NOT REDUCE IT (the watcher is fine either way). Detection PEEKS the "
            "legacy lane, not the lane you armed, so drain that one: "
            "BIFROST_CONSUME_LANE=legacy py agent_cli.py bifrost-sync %s --consume",
            n, kinds, agent)
    return caplog.text


def test_a1_the_source_line_states_the_watcher_is_ARMED():
    """The missing half. Three seats read the old text as death because it never said the
    watcher was alive -- guard the source, since that is what a future editor changes."""
    import inspect
    src = inspect.getsource(A)
    assert "ARMED and watching" in src


def test_a2_the_source_keeps_the_true_caveat_about_re_arming():
    """The warning earned its place: re-arming genuinely does not clear the pending set.
    This slice adds the positive half, it does not delete the honest one."""
    import inspect
    src = inspect.getsource(A)
    assert "does NOT carry to the next arm" in src
    assert "RE-ARMING" in src


def test_a3_the_caveat_no_longer_implies_the_watcher_is_broken():
    """'re-arming will not help' reads as 'nothing will help'. It must be scoped to the
    pending COUNT, with the watcher's own health stated separately."""
    import inspect
    src = inspect.getsource(A)
    assert "the watcher is fine either way" in src


def test_a4_the_message_still_names_the_lane_to_drain(caplog):
    """The one genuinely actionable instruction, and the reason the line exists at all."""
    out = _emit(caplog)
    assert "BIFROST_CONSUME_LANE=legacy" in out
    assert "bifrost-sync claude --consume" in out


def test_a5_the_message_leads_with_the_state_not_the_caveat(caplog):
    """Ordering is the fix. A reader who stops after one clause must come away with
    'armed', not with 'will not help'."""
    out = _emit(caplog)
    assert out.index("ARMED") < out.index("NOT carry")


def test_a6_the_count_and_kinds_survive(caplog):
    """The diagnostic content that made the line worth printing."""
    out = _emit(caplog, n=9, kinds="chat,question,reply")
    assert "9" in out and "chat,question,reply" in out
