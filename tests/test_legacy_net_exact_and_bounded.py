"""The legacy straggler net: exact about twins, bounded about paging (2026-09-15).

WHAT HAPPENED, 2026-09-14 around 03:00 on the claude seat. Every bifrost-standby printed
"[work-drain] N legacy-net packet(s) for claude: N LANE WRITE FAILED (absent from the work lane
-- a real transport defect; investigate the sender side)", with N climbing 11 -> 48 -> 285,
nearly all `from sol [blocker]` about 600 s apart. `bifrost-sync --consume` timed out at 90 s.

WHAT WAS TRUE (read-only Redis, 2026-09-15):
  * The packets were sol's daemon re-escalation broadcasts ("runner for 'sol' down N min"),
    one per RE_ESCALATION_S from 09-09 14:03 to 09-11 09:13 while sol's runner was down.
  * Every one was dual-written correctly: legacy 1789004617023-0 has its work-lane twin at
    1789004617022-0, one millisecond earlier. The sender was not at fault.
  * The membership check read only the newest 500 work-lane entries (oldest: 09-11 11:57), so
    every older twin read as absent.
  * The net's shadow cursor sat days behind: legacy broadcast carried 7,927 entries in the
    24 h to 2026-09-15, 99% trace, and the net read `limit` entries per drain.
  * The net then DELIVERED the week-old twins. consume_inbox's stale gate parked each one --
    441 sol blockers sit on claude's bench, 187 "[triage] ... PARKED" notes went to sol in one
    window -- and each park's directed notify costs ~0.33 s. 285 of those is the timeout.

PINS
  P1 (RED at HEAD)  an intact twin older than the newest-500 window is a twin: no LANE WRITE
                    FAILED claim, and the legacy copy is not re-delivered.
  P2 (RED at HEAD)  one drain pages the shadow past legacy junk far beyond `limit`, delivering
                    nothing.
  P3 (guard)        a genuinely legacy-only packet is still delivered and still named LANE WRITE
                    FAILED.
  P4 (guard)        the migrant flip gap still delivers: a packet dual-written before the flip
                    has its twin behind the seeded work cursor, and the net is its only road.
  P5 (guard)        a corrupt lane copy is not a twin: the intact legacy copy flows (R4).

Redis-backed, throwaway namespaces (skip if Redis is down).
Run: py -m pytest tests/test_legacy_net_exact_and_bounded.py -q
"""
import json
import os
import sys
import time
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import bus as _bus_mod  # noqa: E402
from core.comm import packet_spec  # noqa: E402
from core.comm.bus import Bus  # noqa: E402
from core.comm.bifrost_api import BifrostAPI  # noqa: E402

BROADCAST = getattr(_bus_mod, "BROADCAST_TO", "*")


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_lnet_{uuid.uuid4().hex[:8]}"


def _lane_mode(monkeypatch):
    monkeypatch.setenv("BIFROST_CONSUME_LANE", "work")
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")


def _env(frm, to, kind, text, n):
    """A stamped envelope with a unique ts, so every packet has its own (frm, ts, kind)."""
    env = {"frm": frm, "to": to, "kind": kind, "content": json.dumps(text),
           "ts": f"2026-09-10T01:{(n // 60) % 60:02d}:{n % 60:02d}.{n:06d}+00:00",
           "meta": "{}", "parts": "[]"}
    packet_spec.stamp(env)
    return env


def _dual_write(c, envs, *, lane_stream, legacy_stream, lane=True):
    """What a dual-write send does on the wire: lane copy, then legacy copy, same fields."""
    pipe = c.pipeline(transaction=False)
    for env in envs:
        if lane:
            pipe.xadd(lane_stream, env)
        pipe.xadd(legacy_stream, env)
    pipe.execute()


def _tail(c, key):
    last = c.xrevrange(key, count=1)
    return str(last[0][0]) if last else "0-1"


def _establish(c, api, **fields):
    """An established lane consumer (non-virgin hash, so no onboarding seed runs)."""
    cursor = {"inbox": "0-1", "bc": "0-1", "sig_inbox": "0-1", "sig_bc": "0-1",
              "shadow_inbox": "0-1", "shadow_bc": "0-1"}
    cursor.update(fields)
    c.hset(api.bus.lane_cursor_key(), mapping=cursor)


def _texts(msgs):
    return [str(getattr(m, "content", "")) for m in msgs or []]


# ---------------------------------------------------------------------------------------- P1
def test_p1_an_old_intact_twin_is_a_twin_not_a_failed_write(monkeypatch, capsys):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    lane_bc, legacy_bc = f"{ns}:work:broadcast", f"{ns}:broadcast"
    blockers = [_env("sol", BROADCAST, "blocker",
                     f"[blocker] runner for 'sol' down {10 * (i + 1)}min", i) for i in range(3)]
    newer = [_env("kimi", BROADCAST, "inform", f"later traffic {i}", 100 + i) for i in range(520)]
    _dual_write(c, blockers + newer, lane_stream=lane_bc, legacy_stream=legacy_bc)
    api = BifrostAPI("claude", namespace=ns)
    _establish(c, api, bc=_tail(c, lane_bc))        # the work lane already delivered all of it
    capsys.readouterr()

    got = api.work_drain(timeout_ms=1, limit=5)
    err = capsys.readouterr().err

    assert "LANE WRITE FAILED" not in err, (
        "P1: every packet here has an intact work-lane twin; the only thing 'absent' is the "
        "twin's position relative to the newest-500 window. Stderr said:\n" + err[-600:])
    assert got == [], (
        f"P1: the work cursor already delivered these twins, so the legacy copies must not be "
        f"re-delivered (2026-09-14: 285 re-delivered blockers were parked, and the park storm "
        f"timed out bifrost-sync). Re-delivered: {_texts(got)[:5]}")


# ---------------------------------------------------------------------------------------- P2
def test_p2_one_drain_pages_the_shadow_past_junk(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    lane_bc, legacy_bc = f"{ns}:work:broadcast", f"{ns}:broadcast"
    trace = [_env("sol", BROADCAST, "trace", f"telemetry {i}", i) for i in range(800)]
    pipe = c.pipeline(transaction=False)
    for env in trace:                     # trace never rides the work lane (R12)
        pipe.xadd(legacy_bc, env)
    pipe.execute()
    _dual_write(c, [_env("kimi", BROADCAST, "inform", f"old news {i}", 1000 + i)
                    for i in range(200)], lane_stream=lane_bc, legacy_stream=legacy_bc)
    api = BifrostAPI("claude", namespace=ns)
    api.LEGACY_NET_TIME_BUDGET_S = 60.0   # pin the scan budget, not this machine's speed
    _establish(c, api, bc=_tail(c, lane_bc))

    t0 = time.monotonic()
    got = api.work_drain(timeout_ms=1, limit=20)
    elapsed = time.monotonic() - t0

    shadow = c.hget(api.bus.lane_cursor_key(), "shadow_bc")
    assert shadow == _tail(c, legacy_bc), (
        f"P2: 1000 legacy entries, none deliverable, and one drain with limit=20 left the shadow "
        f"at {shadow} instead of the legacy tail {_tail(c, legacy_bc)}. A net that moves "
        f"`limit` entries per drain never catches a trace-flooded broadcast stream.")
    assert got == [], f"P2: nothing here is deliverable, got {_texts(got)[:5]}"
    assert elapsed < 20.0, f"P2: paging 1000 entries took {elapsed:.1f}s"


# ---------------------------------------------------------------------------------------- P3
def test_p3_a_legacy_only_packet_is_still_delivered_and_named(monkeypatch, capsys):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    lane_in, legacy_in = f"{ns}:work:inbox:claude", f"{ns}:inbox:claude"
    _dual_write(c, [_env("deepseek", "claude", "reply", f"delivered {i}", i) for i in range(3)],
                lane_stream=lane_in, legacy_stream=legacy_in)
    api = BifrostAPI("claude", namespace=ns)
    _establish(c, api, inbox=_tail(c, lane_in), shadow_inbox=_tail(c, legacy_in))
    _dual_write(c, [_env("deepseek", "claude", "handoff", "the lane write failed for this", 50)],
                lane_stream=lane_in, legacy_stream=legacy_in, lane=False)
    capsys.readouterr()

    got = api.work_drain(timeout_ms=1, limit=20)
    err = capsys.readouterr().err

    assert _texts(got) == ["the lane write failed for this"], (
        f"P3: a packet that exists only on legacy must be delivered by the net, got {_texts(got)}")
    assert "LANE WRITE FAILED" in err, (
        "P3: the genuine class must keep its alarm -- fixing the false positive must not "
        "silence the true one. Stderr said:\n" + err[-600:])


# ---------------------------------------------------------------------------------------- P4
def test_p4_the_migrant_flip_gap_still_rides_the_net(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    first = sender.send("alice", "handoff", "consumed on the legacy door before the flip")
    migrant = BifrostAPI("alice", namespace=ns)
    assert migrant.bus.advance_to(inbox=str(first)) == "OK", "precondition: legacy progress"
    sender.send("alice", "handoff", "unconsumed backlog at flip time")
    assert c.hgetall(migrant.bus.lane_cursor_key()) == {}, "precondition: virgin lane hash"

    got = BifrostAPI("alice", namespace=ns).work_drain(timeout_ms=1)   # the flip runs inside
    again = BifrostAPI("alice", namespace=ns).work_drain(timeout_ms=1)

    assert _texts(got).count("unconsumed backlog at flip time") == 1, (
        f"P4: the flip seeds the work cursor past this packet's lane twin, so the straggler net "
        f"is its only delivery (lane_flip_if_migrating: 'tail-seeding the work lane loses "
        f"nothing'). got {_texts(got)}")
    assert "unconsumed backlog at flip time" not in _texts(again), (
        f"P4: delivered once, never twice -- got {_texts(again)} on the second drain")


# ---------------------------------------------------------------------------------------- P5
def test_p5_a_corrupt_lane_copy_is_not_a_twin(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    lane_in, legacy_in = f"{ns}:work:inbox:claude", f"{ns}:inbox:claude"
    env = _env("deepseek", "claude", "handoff", "intact on legacy, corrupt on the lane", 7)
    if "sha" not in env or not packet_spec.integrity_enabled():
        pytest.skip("integrity path unarmed in this environment")
    bad = dict(env)
    bad["sha"] = "0" * len(env["sha"])
    api = BifrostAPI("claude", namespace=ns)
    _establish(c, api)
    pipe = c.pipeline(transaction=False)
    pipe.xadd(lane_in, bad)
    pipe.xadd(legacy_in, env)
    pipe.execute()

    got = api.work_drain(timeout_ms=1, limit=20)

    assert _texts(got) == ["intact on legacy, corrupt on the lane"], (
        f"P5: the lane copy fails its integrity check and is dropped, so it delivered nothing; "
        f"the intact legacy copy is the message and must flow. got {_texts(got)}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
