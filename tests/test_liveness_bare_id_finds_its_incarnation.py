"""RED: asking whether a SEAT is alive misses the INCARNATION that is beating.

2026-08-20, measured on the live bus while the session in question was demonstrably running:

    liveness.read("claude")           -> None          ("no record")
    liveness.read("claude#06528775")  -> phase=running, beat 1s, seq=19

Anthropic's servers 529'd overnight and the fleet could not reach this seat. Both peers wrote
their replies "self-contained since Vandor's seat is down" -- a guess, because the house gives no
way to check. I then made the same mistake from the inside: I queried the bare id, got absence,
and reported to the operator that the conductor emits no heartbeat at all. It emits one. It has
been emitting one the whole time, under an id nobody looks up.

This is the defect I fixed in `defer` at 2am the same night -- absence and nonexistence must not
render identically -- committed by me on the liveness plane six hours later.

WHY _id_forms DOES NOT COVER IT, since it is the obvious patch and it is wrong: _id_forms strips a
session suffix, resolving INCARNATION -> BARE ("codex_root_019fab2d" -> "codex_root", T155). The
failing direction is the opposite: given a bare seat name, find the incarnations currently beating
under it. Nothing in the module does that.

NO SILENT CONFLATION. read(bare) must NOT start returning an incarnation's record -- a seat and one
of its incarnations are different subjects, and quietly substituting one for the other trades a
false negative for a false identity. The fix is a separate resolver that NAMES which ids answered.

Run:  py -m pytest tests/test_liveness_bare_id_finds_its_incarnation.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import liveness as L  # noqa: E402


class _FakeClient:
    """Stands in for redis. Pins must never depend on which seats happen to be alive right now --
    the ambient-state trap that put a roster assertion inside one of last night's pins."""

    def __init__(self, keys):
        self._keys = dict(keys)

    def keys(self, pattern):
        import fnmatch
        return [k for k in self._keys if fnmatch.fnmatch(k, pattern)]

    def get(self, key):
        return self._keys.get(key)


@pytest.fixture
def bus(monkeypatch):
    import json
    pre = L._worklive_prefix()
    live = json.dumps({"phase": "running", "beat_ts": 1_787_000_000.0, "seq": 19})
    client = _FakeClient({f"{pre}claude#06528775": live,
                          f"{pre}deepseek": live})
    monkeypatch.setattr(L, "_client", lambda: client)
    return client


def test_bare_seat_name_finds_its_live_incarnations(bus):
    """The whole defect. Asking about the seat must surface the incarnation that is beating."""
    found = L.live_incarnations("claude")
    assert found, "a beating incarnation was invisible to a query about its own seat"
    assert any(str(i).startswith("claude#") for i in found), found


def test_it_names_which_id_answered(bus):
    """No silent conflation: the caller must be able to tell a seat from an incarnation."""
    found = L.live_incarnations("claude")
    assert "claude#06528775" in found, f"the answering id must be named, got {found}"


def test_read_of_the_bare_id_still_means_exactly_what_it_said(bus):
    """Regression guard on the fix itself: read() keeps its narrow contract. Widening it would
    trade a false negative for a false identity, which is the worse trade."""
    assert L.read("claude") is None
    assert L.read("claude#06528775") is not None


def test_a_seat_with_a_direct_record_needs_no_suffix_hunt(bus):
    """deepseek beats under its bare name; the resolver must not require an incarnation."""
    assert L.live_incarnations("deepseek") == ["deepseek"]


def test_a_genuinely_absent_seat_still_reports_absent(bus):
    """The false-alarm floor -- the resolver must not manufacture life from a key scan."""
    assert L.live_incarnations("nobody-home") == []


def test_it_survives_a_dead_bus(bus, monkeypatch):
    """Fail-open, inherited from this module's own contract: observability never wedges the path
    it observes."""
    monkeypatch.setattr(L, "_client", lambda: None)
    assert L.live_incarnations("claude") == []
