"""
RB-26 + L1b (T030) -- the guarded cursor commit: commit-after-processing with a fencing
generation validated AT THE RESOURCE (one atomic Lua script; Kleppmann).

Bar: a stale generation is REFUSED (the E1 expired-lease writer cannot corrupt the
cursor); ids only move forward; equal id re-commits are idempotent no-ops; wait() hands
callers the batch-safe next position without consuming (since_out without since), which
the runner's post-batch sweep uses so filtered own-broadcasts don't busy-rescan.

Redis-backed (the Lua script IS the unit under test); skips when the bus is offline.
Run: py -m pytest tests/test_bus_advance_guarded.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus


@pytest.fixture
def bus():
    agent = f"t-adv-{uuid.uuid4().hex[:8]}"
    b = Bus(agent)
    if not b.online:
        pytest.skip("redis not available")
    yield b
    try:   # cursor/generation keys have no TTL -- leave nothing behind
        b._client.delete(b._cursor_key(), f"{b.ns}:generation:{agent}",
                         b._inbox_key(agent))
    except Exception:
        pass


def test_generation_fence_refuses_stale_writer(bus):
    assert bus.advance_to(inbox="5-0", generation=3) == "OK"
    assert bus.advance_to(inbox="7-0", generation=2) == "STALE_GENERATION", \
        "an expired-lease predecessor must be fenced out at the resource"
    assert bus.cursor()["inbox"] == "5-0", "the stale writer changed nothing"
    assert bus.advance_to(inbox="7-0", generation=4) == "OK", "the successor proceeds"


def test_ids_only_move_forward(bus):
    assert bus.advance_to(inbox="10-0", generation=1) == "OK"
    assert bus.advance_to(inbox="9-1", generation=1) == "BACKWARDS"
    assert bus.advance_to(inbox="10-0", generation=1) == "OK_NOOP", \
        "re-committing the same id (redelivery sweep) is idempotent, not an error"
    assert bus.advance_to(inbox="10-1", generation=1) == "OK", "seq-part ordering honored"
    assert bus.cursor()["inbox"] == "10-1"


def test_fields_commit_independently(bus):
    assert bus.advance_to(inbox="3-0", bc="8-0", generation=1) == "OK"
    cur = bus.cursor()
    assert cur["inbox"] == "3-0" and cur["bc"] == "8-0"
    # bc moves while inbox no-ops -- worst status of the pair is reported
    assert bus.advance_to(inbox="3-0", bc="9-0", generation=1) == "OK"


def test_wait_hands_out_batch_next_without_consuming(bus):
    sender = Bus(f"t-snd-{uuid.uuid4().hex[:8]}")
    if not sender.online:
        pytest.skip("redis not available")
    # A fresh agent's bc cursor of "0" would drain the whole SHARED broadcast backlog;
    # park it at the live tail so the pin sees only its own direct traffic.
    bus.advance_to(bc=bus.tail()["bc"], generation=0)   # RB-21: guarded harness park
    m1 = sender.send(bus.agent_id, "chat", "one")
    m2 = sender.send(bus.agent_id, "chat", "two")
    assert m1 and m2
    batch_next: dict = {}
    msgs = bus.wait(timeout_ms=300, advance=False, since_out=batch_next)
    direct = [m.id for m in msgs if m.to == bus.agent_id]
    assert direct == [m1, m2]
    assert batch_next["inbox"] == m2, "the batch-safe next position is handed out"
    assert bus.cursor()["inbox"] == "0", "advance=False consumed NOTHING (RB-26 detect phase)"
    # the runner's commit path: per-message then sweep
    assert bus.advance_to(inbox=m1, generation=1) == "OK"
    assert bus.advance_to(inbox=batch_next["inbox"], generation=1) == "OK"
    assert bus.cursor()["inbox"] == m2
