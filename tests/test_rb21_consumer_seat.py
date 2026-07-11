"""
RB-21 -- session-cursor discipline: pre-registered acceptance (committed BEFORE impl, M3/T031).
Spec: docs/rb21-build-spec-2026-07-11.md.

The invariant under pin: at most ONE cursor-advancer per agent id (runner or session,
same lock). Sessions claim the runner lock sticky (session TTL), every advance rides a
fencing generation, the raw unguarded cursor write is retired, refused consumers degrade
to peek (mail visible, never eaten).

Contract frozen here:
  runner_lock.claim_consumer(agent, holder, ttl=None) -> (bool, int, dict)
      ttl None -> SESSION_CONSUMER_TTL; explicit ttl = raw seconds (tests bypass scaling)
  runner_lock.SESSION_CONSUMER_TTL > runner_lock.LOCK_TTL
  Bus.inbox(..., generation: int = 0); Bus._write_cursor GONE (guarded Lua is the only
      cursor writer)
  consume_inbox() under a foreign live holder -> {"seat_held": True, "holder": ...,
      "peeked": [...]} with the cursor unmoved

Live-Redis pins (skip when the bus is offline), unique agent id per test = namespace
isolation; teardown deletes the touched keys.

Run: py -m pytest tests/test_rb21_consumer_seat.py -q
"""
import ast
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import runner_lock
    from core.comm.bus import Bus
    _BUILT = hasattr(runner_lock, "claim_consumer")
except ImportError:
    runner_lock = Bus = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("rb21-probe").online)
except Exception:
    _ONLINE = False

pytestmark = [
    pytest.mark.skipif(not _BUILT, reason="RB-21 pins pre-registered; impl pending (assertions frozen)"),
    pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline"),
]


@pytest.fixture()
def agent():
    aid = f"rb21test-{uuid.uuid4().hex[:8]}"
    yield aid
    c = runner_lock._client()
    if c is not None:
        try:
            for k in (f"bifrost:runner:{aid}", f"bifrost:generation:{aid}",
                      f"bifrost:cursor:{aid}", f"bifrost:inbox:{aid}",
                      f"bifrost:presence:{aid}"):
                c.delete(k)
        except Exception:
            pass


def _seed(agent, n=1):
    """Send n direct messages to `agent` from a throwaway sender."""
    snd = Bus(f"{agent}-sender")
    for i in range(n):
        assert snd.send(agent, "chat", f"pin-mail-{i}")


def _quiesce(agent):
    """Start the fresh test agent AT the live broadcast tail: a live runner's trace
    backlog (broadcast stream, read by EVERY agent from its own cursor) must not leak
    into pin counts. gen-0 commit is valid here -- the agent is never-fenced yet.
    Harness-only; every frozen assertion is untouched (M3)."""
    b = Bus(agent)
    t = b.tail()
    b.advance_to(inbox=t.get("inbox"), bc=t.get("bc"), generation=0)
    return b


# --- P1: a session claim mints a usable fencing generation ---

def test_session_claim_mints_generation(agent):
    ok, gen, info = runner_lock.claim_consumer(agent, "session:pin-a")
    assert ok and gen > 0
    assert Bus(agent).advance_to(inbox="1-1", generation=gen) == "OK"
    assert runner_lock.SESSION_CONSUMER_TTL > runner_lock.LOCK_TTL, \
        "a turn-based session cannot heartbeat in runner seconds"


# --- P2: second claimant refused while the holder lives, holder named ---

def test_second_claimant_refused_while_holder_alive(agent):
    ok_a, gen_a, _ = runner_lock.claim_consumer(agent, "session:pin-a")
    ok_b, gen_b, info_b = runner_lock.claim_consumer(agent, "session:pin-b")
    assert ok_a and not ok_b
    assert "session:pin-a" in str(info_b), "the refusal names the live holder"


# --- P3: an expired-but-still-writing predecessor is fenced AT THE RESOURCE ---

def test_stale_generation_fenced_at_resource(agent):
    bus = Bus(agent)
    ok_a, g1, _ = runner_lock.claim_consumer(agent, "session:pin-a")
    assert ok_a and bus.advance_to(inbox="1-1", generation=g1) == "OK"
    runner_lock.release(agent, "session:pin-a")          # simulate expiry
    ok_b, g2, _ = runner_lock.claim_consumer(agent, "session:pin-b")
    assert ok_b and g2 > g1
    assert bus.advance_to(inbox="2-1", generation=g2) == "OK"
    assert bus.advance_to(inbox="3-1", generation=g1) == "STALE_GENERATION"
    assert bus.cursor()["inbox"] == "2-1", "the fenced-out write moved NOTHING"


# --- P4: a dead holder's seat frees by TTL alone (no janitor, no SessionStart) ---

def test_ttl_frees_dead_holder_alone(agent):
    ok_a, gen_a, _ = runner_lock.claim_consumer(agent, "session:pin-a", ttl=1)
    assert ok_a
    time.sleep(1.3)                                      # holder vanishes, releases nothing
    ok_b, gen_b, _ = runner_lock.claim_consumer(agent, "session:pin-b")
    assert ok_b and gen_b > gen_a


# --- P5: the raw unguarded cursor write is RETIRED ---

def test_raw_write_cursor_retired():
    assert not hasattr(Bus, "_write_cursor"), \
        "the unguarded HSET path is gone; the guarded Lua is the only cursor writer"


# --- P6: never-fenced agents keep working at generation 0 (strangler back-compat) ---

def test_unfenced_backcompat_gen0_consume(agent):
    bus = _quiesce(agent)
    _seed(agent, 2)
    got = bus.inbox(limit=10, advance=True)              # no claim anywhere, gen 0
    assert len(got) == 2
    assert bus.inbox(limit=10, advance=True) == [], "cursor advanced normally"


# --- P7: peeking touches neither lock nor generation ---

def test_peek_stays_seatless(agent):
    _quiesce(agent)
    _seed(agent, 1)
    got = Bus(agent).inbox(limit=10, advance=False)
    assert len(got) == 1
    c = runner_lock._client()
    assert c.get(f"bifrost:runner:{agent}") is None
    assert c.get(f"bifrost:generation:{agent}") is None


# --- P8: the door degrades to peek under a foreign live holder (mail visible, not eaten) ---

def test_door_degrade_shape_under_foreign_holder(agent):
    from agent.bifrost_pull import consume_inbox
    _quiesce(agent)
    _seed(agent, 2)
    ok, _, _ = runner_lock.claim_consumer(agent, "session:pin-holder")
    assert ok
    bus = Bus(agent)
    before = dict(bus.cursor())
    res = consume_inbox(agent, limit=10)                 # a DIFFERENT session's door call
    assert isinstance(res, dict) and res.get("seat_held") is True
    assert "session:pin-holder" in str(res.get("holder"))
    assert len(res.get("peeked") or []) == 2, "the mail is SHOWN, never eaten"
    assert dict(bus.cursor()) == before, "degraded read moved nothing"


# --- P10 (post-review registration, deepseek N1, added pre-impl at gate GREEN):
#     same-session re-claim is a refresh, never a refusal ---

def test_same_session_reclaim_refreshes_not_refuses(agent):
    ok1, g1, _ = runner_lock.claim_consumer(agent, "session:pin-a")
    ok2, g2, _ = runner_lock.claim_consumer(agent, "session:pin-a")
    assert ok1 and ok2 and g2 == g1, \
        "re-entrant for the own token: refresh TTL, keep the tenure generation"


# --- P11 (post-review registration, deepseek Q3/Option A, added pre-impl at gate GREEN):
#     the door's happy path is the SAME dict shape ---

def test_door_happy_path_dict_shape(agent):
    from agent.bifrost_pull import consume_inbox
    _quiesce(agent)
    _seed(agent, 1)
    res = consume_inbox(agent, limit=10)
    assert isinstance(res, dict) and res.get("seat_held") is False
    assert len(res.get("consumed") or []) == 1, "one consistent type for JSON callers"


# --- P9: the MCP door defaults to PEEK (silent consume-by-default retired) ---

def test_mcp_door_peek_default():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = ast.parse(open(os.path.join(root, "ai_setup_mcp.py"), encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "bifrost_inbox")
    args = fn.args
    named = {a.arg: d for a, d in
             zip(args.args[len(args.args) - len(args.defaults):], args.defaults)}
    named.update({a.arg: d for a, d in zip(args.kwonlyargs, args.kw_defaults) if d})
    assert "consume" in named, "bifrost_inbox grows an explicit consume arg"
    assert getattr(named["consume"], "value", None) is False, "and it defaults to PEEK"
