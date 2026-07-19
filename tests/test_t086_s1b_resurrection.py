"""T086 S1b pin: the tombstone's resurrection edge (SessionStart clears what SessionEnd wrote).

Live receipt 2026-07-19: harness restart/compact cycles fired SessionEnd on a session that
kept living; its own tombstone then blocked every re-arm ("standing down -- session
tombstoned") and the seat went deaf between prompts. The fix is symmetric authority: the
harness writes the ended-fact at SessionEnd and clears it at SessionStart -- a true zombie
never sees a SessionStart, so S1's dead-by-record protection is untouched (its own pins
stand in test_t086_s1_tombstone.py). Namespaced stub client per the drills-never-touch-live
law. Run: py -m pytest tests/test_t086_s1b_resurrection.py -q
"""
from core.comm import wake_seat


class StubRedis:
    """set/get/exists/delete over a dict -- the tombstone legs' whole client surface."""
    def __init__(self):
        self.kv = {}
    def set(self, k, v, ex=None):
        self.kv[k] = v
    def get(self, k):
        return self.kv.get(k)
    def exists(self, k):
        return 1 if k in self.kv else 0
    def delete(self, k):
        return 1 if self.kv.pop(k, None) is not None else 0


def test_resurrection_clears_both_legs_and_is_benign_when_absent(tmp_path):
    r, t, sid = StubRedis(), str(tmp_path), "s1b-drill-session"
    assert wake_seat.write_tombstone(sid, t, c=r)
    assert wake_seat.is_tombstoned(sid, t, c=r)             # dead by record...
    assert wake_seat.clear_tombstone(sid, t, c=r)           # ...until the harness says started
    assert not wake_seat.is_tombstoned(sid, t, c=r)
    assert wake_seat.clear_tombstone(sid, t, c=r) is False  # second clear: benign no-op


def test_clear_without_session_id_is_refused():
    assert wake_seat.clear_tombstone("", None, c=StubRedis()) is False
