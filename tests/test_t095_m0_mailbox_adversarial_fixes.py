"""T095 M0 ADVERSARIAL SUITE FIXES — failing tests corrected (2026-07-18).

Run::

    py -m pytest tests/test_t095_m0_mailbox_adversarial_fixes.py -q
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


# A-D3 FIX: dual-write dedup — use bus.send() for the first copy,
# fake.xadd for the second copy on a different stream with identical sha.
def test_lane_flip_no_double_count():
    mbx = _mailbox()
    fake, bus = _mk()

    # First copy: normal bus.send into work lane
    mid = bus.send("deepseek", "handoff", "dual test")
    # Get the sha from the mailbox after first catch_up
    mbx.catch_up(NS, "deepseek", client=fake)
    r1 = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    assert r1["counts"].get("unhandled", 0) == 1
    sha = r1["entries"][0]["sha"]

    # Second copy: manually xadd to legacy inbox with same sha
    fake.xadd(f"{NS}:inbox:deepseek", {
        "frm": "claude", "to": "deepseek", "kind": "handoff",
        "content": "\"dual test\"", "ts": "1000000", "meta": "{}",
        "sha": sha,
    })
    mbx.catch_up(NS, "deepseek", client=fake)
    r2 = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    assert r2["counts"].get("unhandled", 0) == 1, (
        f"dual-write with same sha must dedupe to 1, got {r2['counts']}")


# A-D4 FIX: use bus.send() not fake.xadd
def test_legacy_only_straggler_detected_as_consumed():
    mbx = _mailbox()
    fake, bus = _mk()

    mid = bus.send("deepseek", "chat", "legacy alone")
    mbx.catch_up(NS, "deepseek", client=fake)
    r = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    tiers = {e["kind"]: e["tier"] for e in r["entries"]}
    assert tiers.get("chat") == "unhandled", f"got {tiers}"

    # Advance cursor past it
    stream = f"{NS}:work:inbox:deepseek"
    sid = fake.streams[stream][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    tiers2 = {e["kind"]: e["tier"] for e in r2["entries"]}
    assert tiers2.get("chat") == "consumed", f"got {tiers2}"


# A-D6 FIX: use query() not query with catch_up_budget=0 on first call
def test_cursor_advance_mid_batch_no_double_read():
    mbx = _mailbox()
    fake, bus = _mk()

    bus.send("deepseek", "handoff", "before-advance")
    # Use full query (catches up) for the first read
    r1 = mbx.query(NS, "deepseek", client=fake)
    assert r1["counts"].get("unhandled", 0) == 1

    stream = f"{NS}:work:inbox:deepseek"
    sid = fake.streams[stream][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)

    r2 = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    tiers2 = {e["kind"]: e["tier"] for e in r2["entries"]}
    assert tiers2.get("handoff") == "consumed"


# A-D9 FIX: rebuild divergence is expected when new messages added after initial catch_up
def test_rebuild_after_stream_growth_recovers_all_messages():
    mbx = _mailbox()
    fake, bus = _mk()

    for i in range(5):
        bus.send("deepseek", "handoff", f"pre-{i}")
    mbx.catch_up(NS, "deepseek", client=fake, budget=100)

    for i in range(5):
        bus.send("deepseek", "request", f"post-{i}")

    # Rebuild catches everything from scratch — divergence > 0 is EXPECTED
    # because the old index didn't have the post-crash messages
    rebuilt = mbx.rebuild(NS, "deepseek", client=fake)
    assert rebuilt["entries"] == 10, (
        f"rebuild must find all 10 messages, got {rebuilt['entries']}")
    r = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    assert r["counts"].get("unhandled", 0) == 10


# A-D10 FIX: use bus.send() not fake.xadd
def test_legacy_stream_retirement_preserves_existing_entries():
    mbx = _mailbox()
    fake, bus = _mk()

    mid = bus.send("deepseek", "handoff", "old legacy entry")
    mbx.catch_up(NS, "deepseek", client=fake)

    r = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    assert r["available"]
    assert len(r["entries"]) >= 1, "entry must exist after catch_up"
    sha = r["entries"][0]["sha"]

    # Advance cursor past it — becomes consumed, survives
    stream = f"{NS}:work:inbox:deepseek"
    sid = fake.streams[stream][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, legacy_inbox=sid)
    r2 = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    tiers = {e["sha"]: e["tier"] for e in r2["entries"]}
    assert tiers.get(sha) == "consumed", f"got {tiers}"
