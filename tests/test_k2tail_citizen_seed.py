"""K2-tail pins P1-P5 (kimi design 2026-07-19, claude build): the cursor seed keys on SEAT
CITIZENSHIP (the {ns}:seat:born marker), not cursor virginity -- 'virginity is a property of
the cursor; citizenship is a property of the seat.' Real Redis, isolated namespace per test
(house t045 pattern). Deploy note: existing live seats are grandfathered by an explicit
backfill (marker written, no seed) BEFORE any runner reboots on this code."""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus  # noqa: E402


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_k2tail_{uuid.uuid4().hex[:8]}"


def _fill_backlog(c, ns, n=3):
    """A sender floods broadcasts so there is history to skip."""
    boss = Bus("boss", c, namespace=ns, promote=False)
    for i in range(n):
        boss.broadcast("inform", f"ancient news {i}")
    return boss


def test_p1_walk_polluted_seat_seeds_at_tail():
    """Kimi's exact defect: non-virgin cursor (a walk consumed mail pre-citizenship), NO
    born marker -> first citizen boot seeds at tail AND writes the marker."""
    c, ns = _client(), _ns()
    _fill_backlog(c, ns)
    seat = Bus("newborn", c, namespace=ns, promote=False)
    seat.inbox(limit=1, advance=True)            # the 'walk': consumes one, pollutes virginity
    _fill_backlog(c, ns)                         # more history lands after the walk
    assert seat.seed_cursor_at_tail() is True, "walk-polluted no-marker seat must seed (P1)"
    assert c.hget(f"{ns}:seat:born:newborn", "ts"), "birth certificate must be written"
    assert seat.pending() == 0, "post-seed, the ancient backlog is skipped"


def test_p2_returning_citizen_never_rewound():
    c, ns = _client(), _ns()
    _fill_backlog(c, ns)
    seat = Bus("veteran", c, namespace=ns, promote=False)
    assert seat.seed_cursor_at_tail() is True    # first citizen boot: marked
    _fill_backlog(c, ns, n=2)                    # real unread mail arrives
    before = seat.pending()
    assert before > 0
    assert seat.seed_cursor_at_tail() is False, "marked seat must never re-seed (P2)"
    assert seat.pending() == before, "returning citizen's unread mail is untouched"


def test_p3_true_virgin_seeds_as_before():
    """RB-25 F2 regression guard: virgin cursor + no marker seeds exactly as the old law."""
    c, ns = _client(), _ns()
    _fill_backlog(c, ns)
    seat = Bus("fresh", c, namespace=ns, promote=False)
    assert seat.seed_cursor_at_tail() is True, "true virgin must seed (P3)"
    assert seat.pending() == 0


def test_p3b_empty_world_writes_marker_without_seed():
    """Nothing to skip: no seed reported, but the birth certificate still lands so a later
    walk can never masquerade this seat as pollutable."""
    c, ns = _client(), _ns()
    seat = Bus("firstborn", c, namespace=ns, promote=False)
    assert seat.seed_cursor_at_tail() is False, "empty world: nothing seeded"
    assert c.hget(f"{ns}:seat:born:firstborn", "ts"), "marker written even with empty streams"


def test_p5_generation_zero_semantics_preserved():
    """The seed commits with generation=0 (never-fenced seat) -- the guarded Lua accepts it;
    a later fenced advance still works (no generation poisoning)."""
    c, ns = _client(), _ns()
    _fill_backlog(c, ns)
    seat = Bus("genzero", c, namespace=ns, promote=False)
    assert seat.seed_cursor_at_tail() is True
    boss = Bus("boss", c, namespace=ns, promote=False)
    boss.send("genzero", "chat", "fresh mail")
    msgs = seat.inbox(limit=5, advance=True)     # normal advance after the seeded start
    assert any("fresh mail" in str(getattr(m, "content", "")) for m in msgs), \
        "post-seed delivery must work normally (P5)"


def test_backfill_grandfather_marks_without_seed():
    """Deploy step: an existing seat with real progress gets its marker via backfill; the
    next seed call is then a no-op (P2 path), its unread backlog intact."""
    c, ns = _client(), _ns()
    _fill_backlog(c, ns)
    seat = Bus("elder", c, namespace=ns, promote=False)
    seat.inbox(limit=1, advance=True)            # real progress, pre-fix era
    _fill_backlog(c, ns, n=2)                    # unread they must keep
    # the backfill (what deploy runs): mark WITHOUT seeding
    c.hset(f"{ns}:seat:born:elder", mapping={"ts": "backfill", "had_prior_cursor": "1"})
    before = seat.pending()
    assert seat.seed_cursor_at_tail() is False, "backfilled elder must not seed"
    assert seat.pending() == before, "elder's unread backlog intact"
