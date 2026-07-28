"""T108 S1 acceptance pins -- RED ON PURPOSE (M3: acceptance before implementation).

The role queue: load-balanced role-addressed work with claim semantics. Design settled by the
T108 fence (t108-fence-halves-2026-07-28.md), the build-queue synthesis (as amended by the
codex/Sol outside review), and Daniel's gate 2026-07-28 ~04:00.

The five properties, each a pin:

  P1 EXACTLY-ONCE CLAIM   two consumers in the group, one message -> exactly one receives it.
  P2 STALL RECOVERY       a claim unacked past claim-TTL is reclaimable by another consumer
                          (XAUTOCLAIM handles DEAD claimants; this handles STALLED ones).
  P3 SIDE-EFFECT FENCE    a claimant whose claim was reclaimed CANNOT commit -- the fence
                          token check refuses the stale writer (kimi's fence: verify the
                          claim token before the side effect crosses a hop).
  P4 FRESHNESS            a message past its freshness window is DROPPED-AS-STALE (acked +
                          loud), never handed to a consumer -- games drop the packet that
                          arrived too late; they never replay it.
  P5 PROJECTION           claim state is READABLE from the durable layer alone (stream PEL +
                          fence records) -- a second, fresh handle sees the same claim state.
                          Per the Sol amendment: the mailbox PROJECTS claims; it never owns
                          them. No cache, no side state, rebuildable by construction.

All five are RED today: core/comm/role_queue.py does not exist.
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(autouse=True)
def _restore_incarnation_env():
    """Impersonating seats mutates process env; restore after each test (T069 class)."""
    saved = {k: os.environ.get(k) for k in ("BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


NS = f"t108rq{uuid.uuid4().hex[:6]}"
AGENT = "claude"
SEAT_A = "aaaa1111"
SEAT_B = "bbbb2222"


def _rq():
    from core.comm import role_queue
    return role_queue


def _client():
    from core.comm.bus import get_bus
    return get_bus(AGENT)._client


def test_p1_exactly_once_claim():
    rq = _rq()
    mid = rq.publish(NS, AGENT, "task", f"work-{NS}")
    assert mid
    a = rq.claim_next(NS, AGENT, SEAT_A, block_ms=0)
    b = rq.claim_next(NS, AGENT, SEAT_B, block_ms=0)
    got = [c for c in (a, b) if c is not None]
    assert len(got) == 1, (
        f"EXACTLY-ONCE violated: {len(got)} consumers received the one message "
        f"(a={a and a.msg_id}, b={b and b.msg_id})")
    rq.commit(got[0])


def test_p2_stall_recovery():
    rq = _rq()
    rq.publish(NS + "s", AGENT, "task", f"stall-{NS}")
    a = rq.claim_next(NS + "s", AGENT, SEAT_A, block_ms=0)
    assert a is not None
    # A stalls: never commits. After the claim-TTL, B reclaims.
    time.sleep(1.2)
    reclaimed = rq.reclaim_stalled(NS + "s", AGENT, SEAT_B, min_idle_s=1)
    assert reclaimed, (
        "STALL RECOVERY missing: claim unacked past TTL was not reclaimable by another "
        "consumer -- the lane_stall shape applied to role work (deepseek's fence point)")
    rq.commit(reclaimed[0])


def test_p3_stale_claimant_cannot_commit():
    rq = _rq()
    rq.publish(NS + "f", AGENT, "task", f"fence-{NS}")
    a = rq.claim_next(NS + "f", AGENT, SEAT_A, block_ms=0)
    assert a is not None
    time.sleep(1.2)
    reclaimed = rq.reclaim_stalled(NS + "f", AGENT, SEAT_B, min_idle_s=1)
    assert reclaimed
    # A wakes up believing it still holds the claim and tries to commit its side effect.
    ok_a = rq.commit(a)
    assert not ok_a, (
        "SIDE-EFFECT FENCE missing: a RECLAIMED claimant's commit was accepted -- the stale "
        "writer's side effect crossed the hop (kimi's claim-fence violated)")
    ok_b = rq.commit(reclaimed[0])
    assert ok_b, "the CURRENT claimant's commit must succeed"


def test_p4_stale_message_dropped_never_delivered():
    rq = _rq()
    rq.publish(NS + "t", AGENT, "task", f"fresh-{NS}", freshness_s=1)
    time.sleep(1.3)                    # the message ages out BEFORE any consumer arrives
    c = rq.claim_next(NS + "t", AGENT, SEAT_A, block_ms=0)
    assert c is None or f"fresh-{NS}" not in str(getattr(c, "fields", "")), (
        "FRESHNESS violated: a message past its freshness window was DELIVERED -- the resent "
        "packet that arrived too late must be dropped-as-stale, never re-executed")


def test_p5_claim_state_is_a_projection_of_the_durable_layer():
    rq = _rq()
    mid = rq.publish(NS + "p", AGENT, "task", f"proj-{NS}")
    a = rq.claim_next(NS + "p", AGENT, SEAT_A, block_ms=0)
    assert a is not None
    st = rq.claim_state(NS + "p", AGENT, mid)
    assert st and st.get("claimed_by") == SEAT_A, (
        f"PROJECTION missing: claim state not readable from the durable layer (got {st}) -- "
        f"per the Sol amendment, claims live in stream PEL + fence records and any fresh "
        f"reader must see them; the mailbox projects, never owns")
    rq.commit(a)
    st2 = rq.claim_state(NS + "p", AGENT, mid)
    assert not (st2 and st2.get("claimed_by")), (
        f"PROJECTION stale after commit: {st2} -- a committed claim must read as released")


if __name__ == "__main__":
    test_p1_exactly_once_claim()
    test_p2_stall_recovery()
    test_p3_stale_claimant_cannot_commit()
    test_p4_stale_message_dropped_never_delivered()
    test_p5_claim_state_is_a_projection_of_the_durable_layer()
    print("PASS")
