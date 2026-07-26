"""Differential: FileStore vs SqliteStore must agree on hgetall_prefix.

Written AFTER shipping the verb, which is the wrong order and is the reason it exists. The
corpus rule is to write the op-sequence differential FIRST and wire it into the ship gates --
"two store implementations claiming the same semantics" diverge on first contact, and this
verb has two implementations using genuinely different algorithms:

    FileStore   iterates its in-memory hash bucket and calls _evict_if_expired PER KEY,
                which MUTATES state during what the caller believes is a read.
    SqliteStore issues ONE indexed SELECT plus ONE bulk expiry query and filters in Python,
                mutating nothing.

Same contract, different algorithm, different side effects. That is exactly the shape the
differential harness was built to catch.
"""
import tempfile
from pathlib import Path

import pytest

from core.foundation.store import FileStore
from core.foundation.sqlite_store import SqliteStore


@pytest.fixture()
def pair(tmp_path):
    return FileStore(str(tmp_path / "d.json")), SqliteStore(str(tmp_path / "d.db"))


def _apply(store, ops):
    for op, args, kwargs in ops:
        getattr(store, op)(*args, **kwargs)


def _both(pair, ops):
    for s in pair:
        _apply(s, ops)


def test_empty_prefix_agrees(pair):
    a, b = pair
    assert a.hgetall_prefix("learn:") == b.hgetall_prefix("learn:") == {}


def test_basic_population_agrees(pair):
    ops = [
        ("hset", ("learn:experiment:one",), {"mapping": {"tried": "a", "result": "b"}}),
        ("hset", ("learn:experiment:two",), {"mapping": {"tried": "c"}}),
        ("hset", ("other:thing",), {"mapping": {"nope": "x"}}),
    ]
    _both(pair, ops)
    a, b = pair
    ra, rb = a.hgetall_prefix("learn:experiment:"), b.hgetall_prefix("learn:experiment:")
    assert ra == rb, f"divergence: file={ra} sqlite={rb}"
    assert set(ra) == {"learn:experiment:one", "learn:experiment:two"}, (
        "the prefix must not leak neighbouring keyspaces"
    )


def test_prefix_boundary_agrees(pair):
    """A prefix must not match a key that merely starts with a SHORTER prefix.

    SqliteStore implements the prefix as a range scan (key >= p AND key < p + '\\uffff'),
    FileStore as str.startswith. Range scans and startswith are not obviously the same thing
    at the boundary, which is precisely where a hand-rolled range gets it wrong.
    """
    _both(pair, [
        ("hset", ("learn:experiment:x",), {"mapping": {"k": "1"}}),
        ("hset", ("learn:experimentX",), {"mapping": {"k": "2"}}),
        ("hset", ("learn:experiment",), {"mapping": {"k": "3"}}),
    ])
    a, b = pair
    ra, rb = a.hgetall_prefix("learn:experiment:"), b.hgetall_prefix("learn:experiment:")
    assert ra == rb, f"boundary divergence: file={ra} sqlite={rb}"
    assert set(ra) == {"learn:experiment:x"}


def test_unicode_and_high_codepoints_agree(pair):
    """SqliteStore's range scan uses '\\uffff' as its upper bound. A key CONTAINING a high
    codepoint is the case where that sentinel could wrongly exclude a real record."""
    _both(pair, [
        ("hset", ("learn:experiment:emoji_\U0001F600",), {"mapping": {"k": "1"}}),
        ("hset", ("learn:experiment:hi_￮",), {"mapping": {"k": "2"}}),
        ("hset", ("learn:experiment:plain",), {"mapping": {"k": "3"}}),
    ])
    a, b = pair
    ra, rb = a.hgetall_prefix("learn:experiment:"), b.hgetall_prefix("learn:experiment:")
    assert ra == rb, f"unicode divergence: file={ra} sqlite={rb}"
    assert len(ra) == 3, f"a high-codepoint key was dropped by the range bound: {sorted(ra)}"


def test_expired_keys_are_excluded_identically(pair):
    """The algorithms differ MOST here: per-key lazy eviction versus one bulk expiry query."""
    _both(pair, [
        ("hset", ("learn:experiment:keep",), {"mapping": {"k": "1"}}),
        ("hset", ("learn:experiment:gone",), {"mapping": {"k": "2"}}),
        ("expire", ("learn:experiment:gone", -1), {}),
    ])
    a, b = pair
    ra, rb = a.hgetall_prefix("learn:experiment:"), b.hgetall_prefix("learn:experiment:")
    assert ra == rb, f"expiry divergence: file={ra} sqlite={rb}"
    assert "learn:experiment:gone" not in ra, "an expired key was returned"
    assert "learn:experiment:keep" in ra


def test_read_does_not_change_the_answer_on_a_second_call(pair):
    """FileStore's per-key eviction MUTATES during a read. If that mutation changes what a
    second identical read returns, then hgetall_prefix is not idempotent and two consecutive
    recall queries could legitimately disagree."""
    _both(pair, [
        ("hset", ("learn:experiment:a",), {"mapping": {"k": "1"}}),
        ("hset", ("learn:experiment:b",), {"mapping": {"k": "2"}}),
        ("expire", ("learn:experiment:b", -1), {}),
    ])
    for s in pair:
        first = s.hgetall_prefix("learn:experiment:")
        second = s.hgetall_prefix("learn:experiment:")
        assert first == second, (
            f"{type(s).__name__}.hgetall_prefix is not idempotent: {first} then {second}"
        )


def test_agrees_with_the_naive_loop_it_replaced(pair):
    """The whole point is that the fast path returns what the slow path did.

    This reconstructs the ORIGINAL per-key behaviour and asserts the bulk read matches it.
    Without this, the optimisation could be fast and silently wrong -- and every caller would
    inherit the wrongness.
    """
    _both(pair, [
        ("hset", ("learn:experiment:one",), {"mapping": {"tried": "a", "result": "b"}}),
        ("hset", ("learn:experiment:two",), {"mapping": {"tried": "c"}}),
        ("hset", ("learn:experiment:three",), {"mapping": {"x": "y"}}),
    ])
    for s in pair:
        naive = {}
        for k in s.keys("learn:experiment:*"):
            got = s.hgetall(k)
            if got:
                naive[k] = got
        bulk = s.hgetall_prefix("learn:experiment:")
        assert bulk == naive, (
            f"{type(s).__name__}: bulk read disagrees with the per-key loop it replaced.\n"
            f"  bulk : {sorted(bulk)}\n  naive: {sorted(naive)}"
        )
