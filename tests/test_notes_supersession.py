"""
P1 / T021 -- notes supersession: current-only defaults, retire tombstones, archaeology path.

Bar: re-noting a title supersedes the prior (one survivor in default reads); retire_decision
tombstones a one-shot with no successor (reversible flag, record body intact); default
get_decisions hides superseded, include_superseded=True is the --all archaeology path.
The corpus disease this closes: 4 co-active where-we-are notes minted by wrap's dated
default title (T016 F1a; the title default is pinned here too).

Run: py -m pytest tests/test_notes_supersession.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory


def _mem(tmp_path):
    return AgentMemory(store=FileStore(path=str(tmp_path / "store.json")))


def test_renote_same_title_supersedes_and_default_read_shows_one(tmp_path):
    mem = _mem(tmp_path)
    old = mem.decide(title="where-we-are", decision="monday state")
    new = mem.decide(title="where-we-are", decision="tuesday state", supersedes=old)
    active = mem.get_decisions(days=3650)
    assert [d.id for d in active] == [new], "exactly ONE where-we-are survives the default read"
    assert active[0].decision == "tuesday state"


def test_retire_tombstones_without_successor_and_is_reversible_data(tmp_path):
    mem = _mem(tmp_path)
    dec = mem.decide(title="SESSION HANDOFF 2026-07-07", decision="one-shot briefing")
    assert mem.retire_decision(dec) is True
    assert mem.get_decisions(days=3650) == [], "retired note gone from the default read"
    everything = mem.get_decisions(days=3650, include_superseded=True)
    assert [d.id for d in everything] == [dec], "archaeology path still sees it"
    assert everything[0].superseded is True
    assert everything[0].decision == "one-shot briefing", "tombstone keeps the body (reversible)"


def test_retire_unknown_id_returns_false(tmp_path):
    mem = _mem(tmp_path)
    assert mem.retire_decision("ADR_nope_0000") is False


def test_all_view_orders_and_tags_mixed_records(tmp_path):
    mem = _mem(tmp_path)
    a = mem.decide(title="keep-me", decision="load-bearing")
    b = mem.decide(title="old-arc-status", decision="done arc")
    mem.retire_decision(b)
    allv = mem.get_decisions(days=3650, include_superseded=True)
    assert {d.id for d in allv} == {a, b}
    flags = {d.id: d.superseded for d in allv}
    assert flags[a] is False and flags[b] is True


def test_wrap_default_title_is_bare_where_we_are():
    """The one-line root cause of the pileup (agent_cli wrap): a DATED default title
    defeats update-by-title supersession. Pin the bare default at the source."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "agent_cli.py"), encoding="utf-8").read()
    assert 'args.title or "where-we-are"' in src, "wrap default title must be BARE"
    assert 'args.title or f"where-we-are {' not in src, "the dated default must not return"
