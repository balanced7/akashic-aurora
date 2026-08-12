"""T108 slice 2 -- THE LANE CURSOR IS PER-INCARNATION. RED first (M3).

DeepSeek's diff proposal (handoff 1785228076373-0, its named lane; substrate
commits are mine, so this is the gate). Its diagnosis, verified in the code:

    core/comm/bus.py:996
      return f"{self.ns}:cursor:lane:{agent or self.agent_id}"

Agent-keyed. One cursor per AGENT, not per incarnation -- so the three-key
defect (cursor, presence, expectations all agent-keyed) reaches the lane cursor
too. Two live incarnations of one agent advance the SAME hash and eat each
other's mail, which is the misdelivery family T108 slice 1 closed for the seat
streams and left open here.

Pins P1-P4 encode DeepSeek's design: an optional `incarnation` on Bus, a
suffixed key when it is set, and every internal caller inheriting it for free.

P5 IS NOT IN THE PROPOSAL, AND IT IS THE ONE THAT COSTS MONEY.
A per-incarnation cursor starts VIRGIN. read_lane_cursor()'s documented virgin
semantics are '0' = drain-from-start. So the first runner to adopt this would
re-read its ENTIRE lane history as new mail -- the redelivery storm that ran
$97 -> $109 overnight and killed two runners (a13bc0d). The migration must
INHERIT the agent-keyed position on first use. A cursor split is a fork of
progress, and a fork that forgets where it was is not a cursor.

  P1  incarnation set -> the lane cursor key is suffixed with it.
  P2  TWO INCARNATIONS OF ONE AGENT DO NOT SHARE A LANE CURSOR (the defect).
  P3  NO incarnation -> byte-identical legacy key (every existing caller).
  P4  AN EXPLICIT PEER ARGUMENT IS NEVER SUFFIXED: asking where deepseek's
      cursor is must not return a key stamped with MY session.
  P5  A VIRGIN PER-INCARNATION CURSOR INHERITS THE AGENT-KEYED POSITION --
      never '0'. Splitting the key must not replay the backlog.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus

NS = "t108lc"


@pytest.fixture(autouse=True)
def _restore_env():
    """T069: never leak namespace/incarnation env into sibling tests."""
    saved = {k: os.environ.get(k) for k in
             ("BIFROST_NAMESPACE", "BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _bus(agent, incarnation=None):
    # Only pass the kwarg when one is declared, so P3 (the compat pin) exercises the
    # REAL legacy construction path every existing caller uses -- and is green from
    # the start rather than red on a missing-kwarg TypeError. A compat pin that goes
    # red for the wrong reason cannot prove compatibility was kept.
    if incarnation is None:
        return Bus(agent, namespace=NS, promote=False)
    return Bus(agent, namespace=NS, promote=False, incarnation=incarnation)


# --------------------------------------------------------------- P1
def test_p1_incarnation_suffixes_the_lane_cursor_key():
    b = _bus("deepseek", incarnation="a1b2c3d4")
    key = b.lane_cursor_key()
    assert key.endswith("deepseek#a1b2c3d4"), (
        f"lane cursor key must carry the incarnation when one is declared: {key}")


# --------------------------------------------------------------- P2 the defect
def test_p2_two_incarnations_do_not_share_a_lane_cursor():
    """The whole point. Today both resolve to '{ns}:cursor:lane:deepseek' and the
    second incarnation's advance steals the first's mail."""
    one = _bus("deepseek", incarnation="a1b2c3d4")
    two = _bus("deepseek", incarnation="e5f6a7b8")
    assert one.lane_cursor_key() != two.lane_cursor_key(), (
        f"SHARED LANE CURSOR: both incarnations of deepseek advance "
        f"{one.lane_cursor_key()} -- whichever drains first consumes the other's work. "
        f"This is the same misdelivery family T108 slice 1 closed for seat streams.")


# --------------------------------------------------------------- P3 compat
def test_p3_no_incarnation_is_the_unchanged_legacy_key():
    """Every existing caller constructs Bus without an incarnation. Their key must
    not move by a single byte, or the whole fleet's lane progress resets at once."""
    b = _bus("deepseek")
    assert b.lane_cursor_key() == f"{NS}:cursor:lane:deepseek", (
        f"legacy key changed: {b.lane_cursor_key()}")


# --------------------------------------------------------------- P4 peer queries
def test_p4_an_explicit_peer_argument_is_never_suffixed():
    """lane_cursor_key(agent='kimi') asks where KIMI is. Stamping my session onto
    that answer invents a key that holds nothing -- and reads as an empty cursor,
    which is a confident zero about someone else's progress."""
    b = _bus("deepseek", incarnation="a1b2c3d4")
    assert b.lane_cursor_key("kimi") == f"{NS}:cursor:lane:kimi", (
        f"a peer query returned {b.lane_cursor_key('kimi')} -- my incarnation leaked "
        f"onto another agent's cursor key.")


# --------------------------------------------------------------- P5 the storm guard
def test_p5_a_virgin_incarnation_cursor_inherits_the_agent_position():
    """NOT IN THE PROPOSAL. read_lane_cursor()'s virgin semantics are '0' =
    drain-from-start, so an incarnation adopting a fresh key would re-read the
    entire lane as new mail. That is the redelivery storm of a13bc0d, which ran
    $97 -> $109 and killed two runners. Splitting a cursor forks progress; the
    fork must start where the trunk was."""
    shared = _bus("deepseek")
    if not shared.online:
        pytest.skip("bus offline")
    shared._client.delete(f"{NS}:cursor:lane:deepseek",
                          f"{NS}:cursor:lane:deepseek#a1b2c3d4")
    shared._client.hset(f"{NS}:cursor:lane:deepseek",
                        mapping={"inbox": "1785000000000-0", "bc": "1785000000009-0"})
    try:
        fresh = _bus("deepseek", incarnation="a1b2c3d4")
        cur = fresh.read_lane_cursor()
        assert cur["inbox"] == "1785000000000-0", (
            f"REDELIVERY STORM: a new incarnation read inbox={cur['inbox']!r} instead of "
            f"inheriting the agent cursor's 1785000000000-0. '0' means drain-from-start -- "
            f"the entire lane history redelivered as new work, on every seat that adopts "
            f"the split. This exact shape cost $12 and two runners overnight.")
        assert cur["bc"] == "1785000000009-0", "broadcast position must inherit too"
    finally:
        shared._client.delete(f"{NS}:cursor:lane:deepseek",
                              f"{NS}:cursor:lane:deepseek#a1b2c3d4")
