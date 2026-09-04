"""T198 — the wake lane follows the consume lane unless told otherwise.

FOUND BY CHRONOS (Serge's fleet), 2026-09-04, reading our public repo from the outside and
sending the finding over the bridge. Their report named it exactly: the wake watcher routed
to the lane watcher only when BIFROST_WAKE_LANE=work -- a variable set NOWHERE in this house
-- while consumers default to BIFROST_CONSUME_LANE=work. Two cursors, two meanings of
"drained", and a watcher whose own banner told the operator to go drain the OTHER lane.

Measured cost before the fix, on one seat in one day: eight hand re-arms, each preceded by
draining both lanes, while the operator asked "stuck again?".

An outside reviewer cannot see your working tree, which is precisely why they catch this
class -- every probe run from inside was clean.
Run: py -m pytest tests/test_t198_wake_lane_follows_consume.py -q
"""
import pytest

from core.comm import bifrost_api as API


def test_an_explicit_wake_lane_still_wins(monkeypatch):
    # A seat may deliberately split the planes; the fix must not take that away.
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    monkeypatch.setenv("BIFROST_CONSUME_LANE", "legacy")
    assert API.wake_lane() == "work"


def test_the_wake_lane_follows_the_consume_lane_when_unset(monkeypatch):
    # THE DEFECT: this returned "" before, so the watcher fell through to the legacy path
    # while the consumer drained work.
    monkeypatch.delenv("BIFROST_WAKE_LANE", raising=False)
    monkeypatch.setenv("BIFROST_CONSUME_LANE", "work")
    assert API.wake_lane() == "work", (
        "a seat that consumes the work lane must be WOKEN by the work lane, or detection "
        "and draining are about different mail")


def test_neither_set_is_legacy_shaped_not_a_crash(monkeypatch):
    monkeypatch.delenv("BIFROST_WAKE_LANE", raising=False)
    monkeypatch.delenv("BIFROST_CONSUME_LANE", raising=False)
    assert API.wake_lane() == "", "unset stays the historical path -- no surprise cutover"


def test_whitespace_and_case_do_not_silently_disable_the_lane(monkeypatch):
    monkeypatch.delenv("BIFROST_WAKE_LANE", raising=False)
    monkeypatch.setenv("BIFROST_CONSUME_LANE", " work ")
    assert API.wake_lane() == "work", (
        "a stray space in an env var must not silently route the watcher at the wrong lane")
