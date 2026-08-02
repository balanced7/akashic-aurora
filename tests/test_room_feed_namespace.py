"""PRE-REGISTERED ACCEPTANCE -- namespace-aware room feed (RULING A-2).

Committed RED before implementation (M3 pre-registration).

THE GAP, from the console's own text: the ROOMS panel lists side rooms and says
"listing them here is the only way you can see one exists". You can see a room exists
and cannot read it, enter it, or speak into it -- discovery without access.

THE CAUSE, one literal: scripts/bifrost_ui.py:79 `_inbox_streams` hardcodes
``client.keys("bifrost:inbox:*")`` and appends ``"bifrost:broadcast"``. The stream
prefix IS the namespace, so the feed can only ever render the default room.

This module is the backend half, authored standalone per the ratified UI boundary
(claude authors modules + backend; deepseek owns bifrost_ui.py integration). It is
pure stream discovery -- no HTTP, no rendering, no bus construction.

SECURITY NOTE, and it is the reason pin 4 exists: the namespace arrives from a query
string and lands in a Redis KEYS pattern. An unvalidated ``ns=*`` would match every
stream in the keyspace and leak every room at once. Validation is not decoration here.

Run::

    py -m pytest tests/test_room_feed_namespace.py -q
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _mod():
    import importlib
    return importlib.import_module("core.comm.room_feed")


class _FakeRedis:
    """Minimal double: a keyspace and a spy on the patterns KEYS was asked for."""

    def __init__(self, keys):
        self._keys = list(keys)
        self.patterns = []

    def keys(self, pattern="*"):
        self.patterns.append(str(pattern))
        import fnmatch
        return [k for k in self._keys if fnmatch.fnmatch(k, str(pattern))]


ROOMS_KEYSPACE = [
    "bifrost:inbox:claude", "bifrost:inbox:deepseek", "bifrost:broadcast",
    "test-drill:inbox:claude", "test-drill:broadcast",
    "sandbox:inbox:kimi",
    "bifrost:cursor:lane:claude",          # not a feed stream -- must never be returned
    "bifrost:mailbox:msg:abc",             # ditto
]


# ---------------------------------------------------------------- pin 1
def test_streams_scope_to_the_named_room():
    """THE DEFECT. Asking for a side room must return THAT room's streams, never the
    default's. RED before the module exists."""
    rf = _mod()
    fake = _FakeRedis(ROOMS_KEYSPACE)

    got = set(rf.streams_for(fake, "test-drill"))

    assert got == {"test-drill:inbox:claude", "test-drill:broadcast"}, (
        f"side-room streams wrong: {got}")


# ---------------------------------------------------------------- pin 2
def test_default_room_is_unchanged():
    """NO REGRESSION. The default room must return exactly what the console renders
    today -- every bifrost inbox plus the broadcast, and nothing else."""
    rf = _mod()
    fake = _FakeRedis(ROOMS_KEYSPACE)

    got = set(rf.streams_for(fake, "bifrost"))

    assert got == {"bifrost:inbox:claude", "bifrost:inbox:deepseek", "bifrost:broadcast"}, (
        f"the default room changed shape: {got}")


# ---------------------------------------------------------------- pin 3
def test_non_feed_keys_are_never_returned():
    """Cursors, mailbox rows and lane keys share the namespace prefix. A pattern that
    scooped them would render coordination state as conversation."""
    rf = _mod()
    fake = _FakeRedis(ROOMS_KEYSPACE)

    got = rf.streams_for(fake, "bifrost")

    assert not any("cursor" in k or "mailbox" in k for k in got), (
        f"non-feed keys leaked into the feed: {got}")


# ---------------------------------------------------------------- pin 4
@pytest.mark.parametrize("bad", ["*", "bifrost:*", "*:inbox:*", "", "  ", "a b",
                                 "bifrost:inbox", "../etc", "ns\n*"])
def test_wildcards_and_junk_are_refused(bad):
    """SECURITY. The namespace comes from a query string and lands in a KEYS pattern.
    'ns=*' would match the entire keyspace and leak every room at once. Refuse loudly;
    never sanitize-and-continue, which hides the attempt."""
    rf = _mod()
    fake = _FakeRedis(ROOMS_KEYSPACE)

    with pytest.raises(ValueError):
        rf.streams_for(fake, bad)

    assert fake.patterns == [], (
        f"a rejected namespace still reached Redis as pattern {fake.patterns}")


# ---------------------------------------------------------------- pin 5
def test_unknown_room_is_empty_not_an_error():
    """A well-formed namespace nobody is beating in returns NO streams -- the console's
    existing contract ('an empty room is not a conversation'). Empty is a valid answer;
    only malformed input raises."""
    rf = _mod()
    fake = _FakeRedis(ROOMS_KEYSPACE)

    assert rf.streams_for(fake, "nobody-here") == []


# ---------------------------------------------------------------- pin 6
def test_valid_namespace_accepts_the_shapes_actually_in_use():
    """The live namespaces are 'bifrost', the BIFROST_NAMESPACE env value, and the
    test-* drill convention. Validation must not refuse the shapes the fleet uses."""
    rf = _mod()
    for good in ("bifrost", "test-drill", "test-mbx", "sandbox", "ns_2", "a-b-c"):
        assert rf.valid_namespace(good), f"{good!r} must be accepted"
    for bad in ("*", "a:b", "a b", "", None, "x" * 200):
        assert not rf.valid_namespace(bad), f"{bad!r} must be refused"
