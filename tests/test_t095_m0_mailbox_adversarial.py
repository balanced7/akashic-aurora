"""T095 M0 ADVERSARIAL SUITE — runner-seat attack surface (deepseek, 2026-07-18).

Run:  py -m pytest tests/test_t095_m0_mailbox_adversarial.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm.bus import Bus
from tests.test_t095_m0_mailbox_shadow import (
    _FakeRedis, _mk, _advance_cursor, NS,
)
import importlib as _il


def _mailbox():
    return _il.import_module("core.comm.mailbox")


_NO_ACKS = lambda ids: {}


def _q(mbx, ns, agent, client, **kw):
    return mbx.query(ns, agent, client=client, acks_lookup=_NO_ACKS, **kw)


def _rebuild(mbx, ns, agent, client):
    return mbx.rebuild(ns, agent, client=client, acks_lookup=_NO_ACKS)


# A-D1
def test_crash_mid_ingest_leaves_consistent_index():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(20):
        bus.send("deepseek", "handoff", f"crash-{i}")
    mbx.catch_up(NS, "deepseek", client=fake, budget=10)
    after10 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert after10["counts"].get("unhandled", 0) == 10
    mbx.catch_up(NS, "deepseek", client=fake, budget=100)
    assert _q(mbx, NS, "deepseek", fake, catch_up_budget=0)["counts"].get("unhandled", 0) == 20
    assert _rebuild(mbx, NS, "deepseek", fake)["divergence"] == 0


# A-D2
def test_cursor_staleness_does_not_corrupt_tier():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "request", "future")
    sid = fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid)
    r = _q(mbx, NS, "deepseek", fake)
    assert r["counts"].get("unhandled", 0) == 0
    r2 = _q(mbx, NS, "deepseek", fake)
    tiers = {e["kind"]: e["tier"] for e in r2["entries"]}
    assert tiers.get("request") == "consumed", f"got {tiers}"


# A-D3
def test_lane_flip_no_double_count():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "dual")
    mbx.catch_up(NS, "deepseek", client=fake)
    r1 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert r1["counts"].get("unhandled", 0) == 1
    sha = r1["entries"][0]["sha"]
    fake.xadd(f"{NS}:inbox:deepseek", {"frm": "claude", "to": "deepseek", "kind": "handoff",
              "content": "\"dual\"", "ts": "1000000", "meta": "{}", "sha": sha})
    mbx.catch_up(NS, "deepseek", client=fake)
    r2 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert r2["counts"].get("unhandled", 0) == 1
    ids = r2["entries"][0]["ids"]
    sources = list(ids.keys() if isinstance(ids, dict) else json.loads(ids).keys())
    assert "legacy_inbox" in sources and "work_inbox" in sources


# A-D4
def test_legacy_only_straggler_detected_as_consumed():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "chat", "legacy")
    mbx.catch_up(NS, "deepseek", client=fake)
    r = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert {e["kind"]: e["tier"] for e in r["entries"]}.get("chat") == "unhandled"
    sid = fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert {e["kind"]: e["tier"] for e in r2["entries"]}.get("chat") == "consumed"


# A-D5
def test_replied_evidence_ingested_via_sender_inbox():
    mbx = _mailbox()
    fake, bus = _mk()
    mid = bus.send("deepseek", "handoff", "ancestor")
    fake.xadd(f"{NS}:work:inbox:claude", {"frm": "claude", "to": "deepseek", "kind": "reply",
              "content": "\"done\"", "ts": "2000000", "meta": json.dumps({"answers": mid})})
    mbx.catch_up(NS, "deepseek", client=fake)
    mbx.catch_up(NS, "claude", client=fake)
    r = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    tier = list({e["sha"]: e["tier"] for e in r["entries"]}.values())
    assert tier and tier[0] in ("replied", "auto_acked"), f"got {tier}"


# A-D6
def test_cursor_advance_mid_batch_no_double_read():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "before")
    r1 = _q(mbx, NS, "deepseek", fake)
    assert r1["counts"].get("unhandled", 0) == 1
    sid = fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert {e["kind"]: e["tier"] for e in r2["entries"]}.get("handoff") == "consumed"


# A-D7
def test_claim_gated_on_index_position():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "request", "stealth")
    r = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert r["counts"].get("unhandled", 0) == 0
    r2 = _q(mbx, NS, "deepseek", fake)
    assert r2["counts"].get("unhandled", 0) == 1
    sid = fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    pos = fake.hashes.get(f"{NS}:mailbox:pos:deepseek", {}).get("work_inbox", "0-0")
    from core.comm.mailbox import _sid_lte
    assert _sid_lte(sid, pos)


# A-D8
def test_eviction_preserves_unhandled_handoff_over_chat():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(45):
        bus.send("deepseek", "chat", f"n-{i}")
    mid = bus.send("deepseek", "handoff", "important")
    r = _q(mbx, NS, "deepseek", fake, cap=20)
    kinds = [e["kind"] for e in r["entries"]]
    assert "handoff" in kinds
    peer = Bus(agent_id="deepseek", client=fake, namespace=NS)
    peer.send("claude", "reply", "done", meta={"answers": mid})
    mbx.catch_up(NS, "claude", client=fake)
    r2 = _q(mbx, NS, "deepseek", fake, cap=20)
    tier = {e["kind"]: e["tier"] for e in r2["entries"] if e["kind"] == "handoff"}
    assert tier.get("handoff") in ("replied", "auto_acked")


# A-D9
def test_rebuild_after_stream_growth_recovers_all_messages():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(5):
        bus.send("deepseek", "handoff", f"pre-{i}")
    mbx.catch_up(NS, "deepseek", client=fake, budget=100)
    for i in range(5):
        bus.send("deepseek", "request", f"post-{i}")
    assert _rebuild(mbx, NS, "deepseek", fake)["entries"] == 10
    r = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert r["counts"].get("unhandled", 0) == 10
    for i in range(5):
        sid = fake.streams[f"{NS}:work:inbox:deepseek"][i][0]
        _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert r2["counts"].get("consumed", 0) == 5
    assert r2["counts"].get("unhandled", 0) == 5


# A-D10
def test_legacy_stream_retirement_preserves_existing_entries():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "old")
    mbx.catch_up(NS, "deepseek", client=fake)
    r = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert len(r["entries"]) >= 1
    sha = r["entries"][0]["sha"]
    assert r["entries"][0]["tier"] == "unhandled"
    sid = fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = _q(mbx, NS, "deepseek", fake, catch_up_budget=0)
    assert {e["sha"]: e["tier"] for e in r2["entries"]}.get(sha) == "consumed"
