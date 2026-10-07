"""RED pins: every user turn pays ~4 seconds to discover there are no locks.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

W132, and the measurement is the whole argument. Taken from the live tree, 2026-10-07:

    agent.harness.context._unread_count("claude")      4.09s, 4.14s, 4.16s   (three runs)

That function is called from agent/harness/hooks/claude_userpromptsubmit.py:68 -- the
UserPromptSubmit hook -- so it runs on EVERY SINGLE USER TURN.

Profiled, the four seconds are not where anyone would guess::

    collect_boot_bifrost          5.245s cumulative
      peek_locks                  3.789s      <- 72%
        locks.list_locks          3.759s
          redis scan              6,503 calls

And then the punchline::

    dbsize                       66,700 keys
    locks matching akashic:lock:*      0
    scan_iter(...)             3.96s  (Redis default COUNT=10)
    scan_iter(..., count=1000) 0.05s  (73x)

**Zero locks. Four seconds. Every turn.** The keyspace is 66,700 keys and SCAN walks it ten keys
per round trip, so the cost is O(keyspace) in NETWORK ROUND TRIPS and completely independent of how
many locks exist. It would cost the same four seconds if the lock feature were deleted.

TWO DEFECTS, and they are worth separating because they have different blast radii.

1. ``LockManager.list_locks`` (core/comm/locks.py:157) calls ``scan_iter`` without ``count``. This
   is the one-line half, and it helps EVERY caller of the lock door, not just this path.

2. ``_unread_count`` asks ``collect_boot_bifrost`` for "presence + unread peek + held locks" and
   then uses only the unread number. It pays for two thirds of a result it discards. Making the
   scan fast hides this but does not fix it: a counter should not be buying locks at all.

WHY A ROUND-TRIP PIN AND NOT A TIMING PIN. Wall-clock assertions are flaky on a loaded box and
tempt everyone to widen the bound until it means nothing. The defect is not "slow", it is "issues a
number of requests proportional to the keyspace", and that is countable and deterministic. These
pins wrap the client and COUNT the commands, so the pin fails for the real reason and cannot be
quieted by a faster machine.

Run::

    py -m pytest tests/test_the_lock_scan_does_not_cost_the_whole_keyspace.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CountingClient:
    """A Redis stand-in that records how many SCAN round trips a caller makes.

    `scan` is implemented honestly: it respects `count`, walks a synthetic keyspace in pages, and
    returns a real cursor. So a caller that passes no count genuinely pays more round trips here,
    exactly as it does against the real server.
    """

    def __init__(self, total_keys: int = 66_700, matching: int = 0):
        self.keys = ["bifrost:other:%d" % i for i in range(total_keys - matching)]
        self.keys += ["bifrost:lock:p%d" % i for i in range(matching)]
        self.scan_calls = 0

    def scan(self, cursor=0, match=None, count=None, **_kw):
        self.scan_calls += 1
        page = int(count or 10)                      # Redis's own default is 10
        start = int(cursor)
        chunk = self.keys[start:start + page]
        nxt = start + page
        if nxt >= len(self.keys):
            nxt = 0
        import fnmatch
        hits = [k for k in chunk if (match is None or fnmatch.fnmatch(k, match))]
        return nxt, hits

    def scan_iter(self, match=None, count=None, **_kw):
        cursor = 0
        while True:
            cursor, data = self.scan(cursor=cursor, match=match, count=count)
            for d in data:
                yield d
            if cursor == 0:
                return

    def get(self, _key):
        return None


# ------------------------------------------------------------------ the defect
def test_listing_locks_does_not_scale_with_the_keyspace():
    """THE PIN, in round trips rather than seconds.

    66,700 keys at Redis's default COUNT=10 is ~6,670 round trips to find zero locks -- measured at
    6,503 against the live server. A bounded scan does it in tens.
    """
    from core.comm.locks import LockManager
    c = CountingClient(total_keys=66_700, matching=0)
    lm = LockManager("probe", client=c)
    try:
        got = lm.list_locks()
    except TypeError:
        pytest.skip("LockManager does not accept an injected client on this checkout")
    assert got == [], "the synthetic keyspace holds no locks; got %r" % (got,)
    assert c.scan_calls <= 200, (
        "list_locks issued %d SCAN round trips over a 66,700-key keyspace holding ZERO locks. "
        "core/comm/locks.py:157 calls scan_iter without `count`, so Redis's default of 10 keys per "
        "round trip makes the cost O(keyspace) and independent of how many locks exist. Measured "
        "live: 6,503 calls, 3.96s -- and 0.05s with count=1000." % c.scan_calls)


def test_the_unread_counter_does_not_buy_locks_it_discards():
    """THE SECOND DEFECT, which a faster scan would hide rather than fix.

    `_unread_count` wants one integer. It calls collect_boot_bifrost, documented as "presence +
    unread peek + held locks", and throws two thirds away -- on every user turn. Asserted on the
    call graph rather than on time, so making SCAN fast cannot silence it.
    """
    import ast
    src = (ROOT / "agent" / "harness" / "context.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "_unread_count"), None)
    assert fn is not None, "no _unread_count to inspect"
    calls = {getattr(c.func, "attr", None) or getattr(c.func, "id", None)
             for c in ast.walk(fn) if isinstance(c, ast.Call)}
    if "collect_boot_bifrost" not in calls:
        return                                        # already routed somewhere cheaper
    kw = set()
    for c in ast.walk(fn):
        if isinstance(c, ast.Call) and (getattr(c.func, "attr", None)
                                        or getattr(c.func, "id", None)) == "collect_boot_bifrost":
            kw |= {k.arg for k in (c.keywords or [])}
    assert kw & {"with_locks", "locks", "want_locks", "cheap", "counts_only"}, (
        "_unread_count calls collect_boot_bifrost with no way to decline the lock peek, so a "
        "once-per-turn counter pays for presence AND a full lock enumeration and uses neither. "
        "Keywords passed: %r" % (sorted(kw),))


# ------------------------------------------------------------------ ratchets
def test_a_real_lock_is_still_found():
    """RATCHET. Speed is worthless if the door stops seeing locks. A bounded scan must return the
    same set a slow one would."""
    import json as _json
    from core.comm.locks import LockManager

    class WithLock(CountingClient):
        def get(self, key):
            if ":lock:" in key:
                return _json.dumps({"path": "core/x.py", "agent": "peer"})
            return None

    c = WithLock(total_keys=5_000, matching=3)
    lm = LockManager("probe", client=c)
    try:
        got = lm.list_locks()
    except TypeError:
        pytest.skip("LockManager does not accept an injected client on this checkout")
    assert len(got) == 3, "expected the 3 seeded locks, got %r" % (got,)
    assert all(g.get("path") == "core/x.py" for g in got)


def test_the_seq_key_is_still_skipped():
    """RATCHET on an existing behaviour that is easy to drop while editing this loop:
    `:_seq` keys are bookkeeping, not locks."""
    import json as _json
    from core.comm.locks import LockManager

    class WithSeq(CountingClient):
        def __init__(self):
            super().__init__(total_keys=100, matching=0)
            self.keys += ["bifrost:lock:a", "bifrost:lock:a:_seq"]

        def get(self, key):
            return _json.dumps({"path": "a"}) if not key.endswith(":_seq") else "7"

    c = WithSeq()
    lm = LockManager("probe", client=c)
    try:
        got = lm.list_locks()
    except TypeError:
        pytest.skip("LockManager does not accept an injected client on this checkout")
    assert len(got) == 1, "the :_seq bookkeeping key leaked into the lock list: %r" % (got,)
