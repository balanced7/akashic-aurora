"""T066 PRE-REGISTERED ACCEPTANCE -- reply path goes lane-first + reply dedup.

Committed RED before implementation (method-baseline pre-registration). Design half:
research/reviewed/deepseek-t066-design-2026-07-15.md (deepseek traces his OWN reply path);
evidence: event:events:raw:1784082287759-0 + 1784003725351-0 (five wake-loop cycles on
Daniel's seat, 2026-07-14/15).

Pins (deepseek's P1-P7, with ONE build refinement on P4 recorded for his verify pass):
  P1 send_reply writes bifrost:work:inbox:<to> FIRST, then legacy as fallback
  P2 lane write failure -> one retry -> still failing -> LOUD + legacy fallback delivers
  P3 every reply carries meta.reply_id, unique per reply
  P4 receiver-side dedup: a LEGACY-path duplicate of an already-delivered reply_id is
     skipped. REFINEMENT vs the design text: work-lane copies are ALWAYS delivered (only
     marked) -- dropping a redelivered work copy would break RB-26 crash-redelivery
     (work cursor advances only after processing; a crash must redeliver). Only the
     cross-path (legacy twin / straggler re-race) duplicate is dropped.
  P5 non-reply kinds ride the existing legacy-first advisory dual-write, unchanged
  P6 the reply still lands on the legacy inbox (pre-lane consumers keep seeing replies)
  P7 _lane_write failure for non-reply kinds stays silent-advisory

Redis-backed (throwaway namespace per test, the t039a pattern; skip if down).
Run: py -m pytest tests/test_t066_reply_path.py -q
"""
import json
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_t066_{uuid.uuid4().hex[:8]}"


class _Recorder:
    """Client proxy: records xadd stream keys in call order; injects per-key-substring
    failures with a countdown (fail the first N xadds whose key contains the substring)."""

    def __init__(self, real, fail=None):
        self._real = real
        self.xadd_keys = []
        self._fail = dict(fail or {})

    def xadd(self, key, *a, **k):
        self.xadd_keys.append(str(key))
        for sub, n in list(self._fail.items()):
            if sub in str(key) and n > 0:
                self._fail[sub] = n - 1
                raise RuntimeError(f"injected xadd failure ({sub})")
        return self._real.xadd(key, *a, **k)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _bus(agent, ns, fail=None):
    b = Bus(agent, namespace=ns)
    if b._client is None:
        pytest.skip("redis not available")
    b._client = _Recorder(b._client, fail=fail)
    return b


def _entries(client, key):
    out = []
    for eid, fields in client.xrange(key):
        f = dict(fields)
        f["_id"] = eid
        out.append(f)
    return out


def test_p1_reply_is_lane_first():
    ns = _ns()
    b = _bus("deepseek", ns)
    mid = b.send_reply("claude", "the answer", meta={"answers": "1-0"})
    assert mid, "send_reply must return a message id"
    lane_writes = [k for k in b._client.xadd_keys if ":work:inbox:claude" in k]
    legacy_writes = [k for k in b._client.xadd_keys if k.endswith(":inbox:claude") and ":work:" not in k]
    assert lane_writes and legacy_writes, "both streams must be written"
    assert b._client.xadd_keys.index(lane_writes[0]) < b._client.xadd_keys.index(legacy_writes[0]), \
        "the LANE write must come FIRST (it is the load-bearing consume surface)"
    assert len(_entries(b._client, f"{ns}:work:inbox:claude")) == 1
    assert len(_entries(b._client, f"{ns}:inbox:claude")) == 1


def test_p2_lane_failure_retries_then_falls_back_loud(capsys):
    ns = _ns()
    b = _bus("deepseek", ns, fail={":work:inbox:claude": 2})   # initial + retry both fail
    mid = b.send_reply("claude", "the answer")
    assert mid, "legacy fallback must still deliver"
    lane_attempts = [k for k in b._client.xadd_keys if ":work:inbox:claude" in k]
    assert len(lane_attempts) == 2, f"exactly one retry (2 attempts), got {len(lane_attempts)}"
    assert len(_entries(b._client, f"{ns}:work:inbox:claude")) == 0
    assert len(_entries(b._client, f"{ns}:inbox:claude")) == 1, "legacy fallback delivers"
    err = capsys.readouterr().err
    assert "lane write FAILED" in err, "the failure must be LOUD, never silent"


def test_p3_reply_carries_unique_reply_id():
    ns = _ns()
    b = _bus("deepseek", ns)
    b.send_reply("claude", "answer one")
    b.send_reply("claude", "answer two")
    metas = [json.loads(e.get("meta", "{}")) for e in _entries(b._client, f"{ns}:work:inbox:claude")]
    ids = [m.get("reply_id") for m in metas]
    assert all(ids), f"every reply must carry meta.reply_id, got {metas}"
    assert ids[0] != ids[1], "reply_id must be unique per reply"


def test_p4_receiver_drops_legacy_duplicate_keeps_work_copy(monkeypatch):
    """The live bug shape: the work copy delivers; the legacy twin re-surfaces on a later
    drain (straggler re-race / shared-cursor path) and must be SKIPPED. Work copies are
    never dropped (RB-26 crash-redelivery stays intact -- build refinement, see header)."""
    from core.comm.bifrost_api import BifrostAPI
    monkeypatch.setenv("BIFROST_CONSUME_LANE", "work")
    ns = _ns()
    sender = _bus("deepseek", ns)
    api = BifrostAPI("claude", namespace=ns)
    assert api.bus._client is not None or pytest.skip("redis not available")

    sender.send_reply("claude", "the verdict", meta={"answers": "9-0"})
    nxt = {}
    first = api.work_drain(timeout_ms=1, since_out=nxt)
    replies = [m for m in first if str(getattr(m, "kind", "")) == "reply"]
    assert len(replies) == 1, f"first drain delivers the work copy, got {len(replies)}"
    rid = (getattr(replies[0], "meta", {}) or {}).get("reply_id")
    assert rid, "delivered reply carries its reply_id"
    # the consumer contract (pin R3): commit the work cursor AFTER processing
    api.bus.advance_to(inbox=nxt.get("inbox"), bc=nxt.get("bc"),
                       cursor_key=api.bus.lane_cursor_key())

    # the legacy twin re-surfaces later (same envelope, same reply_id, fresh stream id)
    twin = dict(_entries(sender._client, f"{ns}:inbox:claude")[0])
    twin.pop("_id", None)
    sender._client.xadd(f"{ns}:inbox:claude", twin)
    second = api.work_drain(timeout_ms=1)
    dup = [m for m in second if str(getattr(m, "kind", "")) == "reply"
           and (getattr(m, "meta", {}) or {}).get("reply_id") == rid]
    assert dup == [], "the legacy duplicate must be skipped by the reply_id dedup"


def test_p4_unit_is_duplicate_reply_marks_and_ttls():
    ns = _ns()
    b = _bus("deepseek", ns)
    assert b.is_duplicate_reply("rid-1") is False, "first sight marks, reports not-duplicate"
    assert b.is_duplicate_reply("rid-1") is True, "second sight within TTL is a duplicate"
    ttl = b._client.ttl(f"{ns}:reply_seen:rid-1")
    assert ttl and ttl > 0, "the dedup mark must expire (TTL), never accrete forever"
    assert b.is_duplicate_reply("") is False, "empty id never dedupes"


def test_p5_p6_non_reply_kinds_unchanged_and_legacy_compat():
    ns = _ns()
    b = _bus("deepseek", ns)
    b.send("claude", "handoff", "take this")
    lane_first = [k for k in b._client.xadd_keys if ":work:inbox:claude" in k]
    legacy_first = [k for k in b._client.xadd_keys if k.endswith(":inbox:claude") and ":work:" not in k]
    assert legacy_first and lane_first, "handoff still dual-writes"
    assert b._client.xadd_keys.index(legacy_first[0]) < b._client.xadd_keys.index(lane_first[0]), \
        "non-reply kinds stay LEGACY-first (T039a P0 soak untouched)"
    # P6: a reply is visible to a pre-lane legacy consumer
    b.send_reply("claude", "the answer")
    legacy_kinds = [e.get("kind") for e in _entries(b._client, f"{ns}:inbox:claude")]
    assert "reply" in legacy_kinds, "legacy inbox must still carry the reply (backward compat)"


def test_p7_lane_write_failure_stays_silent_for_non_replies(capsys):
    ns = _ns()
    b = _bus("deepseek", ns, fail={":work:inbox:claude": 5})
    mid = b.send("claude", "handoff", "take this")
    assert mid, "legacy delivery unaffected"
    err = capsys.readouterr().err
    assert "lane write FAILED" not in err, "non-reply lane failures stay advisory-silent (P0 contract)"
    assert len(_entries(b._client, f"{ns}:inbox:claude")) == 1


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t066_reply_path.py -q")
