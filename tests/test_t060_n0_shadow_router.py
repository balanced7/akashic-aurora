"""T060 N0 PRE-REGISTERED ACCEPTANCE -- shadow delivery truth + route explain.

These pins cite the reconciled build spec at
``research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md``.
They are committed RED before implementation.  N0 is observational only: the
new router may explain and count the existing static route, but may not choose a
different lane or change delivery, wake, priority, deadline, cursor, or reply
semantics.

Run::

    py -m pytest tests/test_t060_n0_shadow_router.py -q
"""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm import packet_spec
from core.comm.bus import Bus


def _router():
    # Import inside each pin so pytest still collects and names every RED test
    # before core/comm/router.py exists.
    return importlib.import_module("core.comm.router")


class _FakeRedis:
    """Small transport double: Redis-shaped enough for Bus send-door pins."""

    def __init__(self, *, fail_lane_writes: bool = False,
                 fail_metrics: bool = False) -> None:
        self.fail_lane_writes = fail_lane_writes
        self.fail_metrics = fail_metrics
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.hashes: dict[str, dict[str, int | str]] = {}
        self.values: dict[str, str] = {}
        self.xadd_keys: list[str] = []
        self._ticks: dict[str, int] = {}

    def hgetall(self, key):
        return dict(self.hashes.get(str(key), {}))

    def hset(self, key, field, value):
        self.hashes.setdefault(str(key), {})[str(field)] = value
        return 1

    def hdel(self, key, field):
        return int(self.hashes.get(str(key), {}).pop(str(field), None) is not None)

    def hincrby(self, key, field, amount=1):
        if self.fail_metrics:
            raise RuntimeError("injected metric failure")
        bucket = self.hashes.setdefault(str(key), {})
        bucket[str(field)] = int(bucket.get(str(field), 0)) + int(amount)
        return bucket[str(field)]

    def xadd(self, key, fields, **_kwargs):
        key = str(key)
        self.xadd_keys.append(key)
        if self.fail_lane_writes and any(
                marker in key for marker in (":work:", ":sig:", ":trace")):
            raise RuntimeError("injected lane mirror failure")
        bucket = self.streams.setdefault(key, [])
        mid = f"{len(bucket) + 1}-0"
        bucket.append((mid, dict(fields)))
        return mid

    def set(self, key, value, *, nx=False, **_kwargs):
        key = str(key)
        if nx and key in self.values:
            return False
        self.values[key] = str(value)
        return True

    def publish(self, *_args, **_kwargs):
        return 1

    def incr(self, key):
        key = str(key)
        self._ticks[key] = self._ticks.get(key, 0) + 1
        return self._ticks[key]


def _redis_client():
    from core.foundation.redis_connection import (
        DEFAULT_REDIS_HOST,
        DEFAULT_REDIS_PORT,
        connect_to_redis_with_fail_fast,
    )

    client = connect_to_redis_with_fail_fast(
        host=DEFAULT_REDIS_HOST,
        port=DEFAULT_REDIS_PORT,
        timeout_seconds=3,
        decode_responses=True,
    )
    if client is None:
        pytest.skip("local Redis unavailable")
    return client


def test_route_matches_lane_for_every_live_kind():
    router = _router()
    for kind, lane in packet_spec.KIND_LANE.items():
        decision = router.route(kind)
        assert decision.kind == kind
        assert decision.lane == lane
        assert decision.known is True
        assert decision.rule_id == f"kind:{kind}"
        assert decision.mode == "shadow"
        assert decision.policy_version
        assert decision.as_dict() == {
            "kind": kind,
            "lane": lane,
            "known": True,
            "rule_id": f"kind:{kind}",
            "policy_version": decision.policy_version,
            "mode": "shadow",
        }


def test_unknown_kind_is_shadow_unmapped_not_refused():
    decision = _router().route("brand-new-kind")
    assert decision.kind == "brand-new-kind"
    assert decision.lane is None
    assert decision.known is False
    assert decision.rule_id == "kind:_unknown"
    assert decision.mode == "shadow"


def test_lane_failure_preserves_legacy_delivery_and_counts_failure(monkeypatch):
    router = _router()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    client = _FakeRedis(fail_lane_writes=True)
    namespace = "t060_n0_k0"
    bus = Bus("sol", client, namespace=namespace, promote=False)

    mid = bus.send("fable", "handoff", "K0 mirror-failure probe")

    assert mid
    assert len(client.streams[f"{namespace}:inbox:fable"]) == 1
    assert f"{namespace}:work:inbox:fable" not in client.streams
    stats = router.route_stats(client, namespace)
    assert stats["counts"]["decision:handoff"] == 1
    assert stats["counts"]["mirror:handoff:failure"] == 1


def test_route_and_outcome_cardinality_is_static():
    router = _router()
    client = _FakeRedis()
    namespace = "t060_n0_cardinality"

    for index in range(1_000):
        decision = router.route(f"untrusted-kind-{index}")
        router.record_observation(client, namespace, decision, "unmapped")

    stats = router.route_stats(client, namespace)
    fields = set(stats["counts"])
    schema = set(router.metric_field_schema())
    assert fields <= schema
    assert len(fields) <= len(schema)
    assert stats["counts"] == {
        "decision:_unknown": 1_000,
        "mirror:_unknown:unmapped": 1_000,
    }


def test_reply_lane_first_dedup_and_expectation_semantics_unchanged(monkeypatch):
    router = _router()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    client = _FakeRedis()
    namespace = "t060_n0_reply"
    bus = Bus("deepseek", client, namespace=namespace, promote=False)

    mid = bus.send_reply("sol", "review complete", meta={"answers": "ask-17"})

    assert mid
    lane_key = f"{namespace}:work:inbox:sol"
    legacy_key = f"{namespace}:inbox:sol"
    assert client.xadd_keys.index(lane_key) < client.xadd_keys.index(legacy_key)
    lane_meta = json.loads(client.streams[lane_key][0][1]["meta"])
    legacy_meta = json.loads(client.streams[legacy_key][0][1]["meta"])
    assert lane_meta["reply_id"] == legacy_meta["reply_id"]
    assert lane_meta["answers"] == legacy_meta["answers"] == "ask-17"
    assert bus.is_duplicate_reply(lane_meta["reply_id"]) is False
    assert bus.is_duplicate_reply(lane_meta["reply_id"]) is True
    stats = router.route_stats(client, namespace)
    assert stats["counts"]["decision:reply"] == 1
    assert stats["counts"]["reply:reply:success"] == 1


def test_cli_and_mcp_route_json_are_identical():
    cli = subprocess.run(
        [sys.executable, str(ROOT / "agent_cli.py"),
         "packet-trace", "handoff", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert cli.returncode == 0, cli.stderr or cli.stdout
    cli_value = json.loads(cli.stdout)

    import ai_setup_mcp

    mcp_value = json.loads(ai_setup_mcp.packet_route("handoff"))
    assert cli_value == mcp_value == _router().route("handoff").as_dict()


def test_shadow_metrics_failure_never_fails_send(monkeypatch):
    _router()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    client = _FakeRedis(fail_metrics=True)
    namespace = "t060_n0_metric_failure"
    bus = Bus("sol", client, namespace=namespace, promote=False)

    mid = bus.send("deepseek", "handoff", "metrics are advisory")

    assert mid
    assert len(client.streams[f"{namespace}:inbox:deepseek"]) == 1
    assert len(client.streams[f"{namespace}:work:inbox:deepseek"]) == 1


def test_shadow_observation_adds_under_5ms_p50_on_local_redis():
    router = _router()
    client = _redis_client()
    namespace = f"t060_n0_perf_{uuid.uuid4().hex[:10]}"
    key = router.metric_key(namespace)
    decision = router.route("handoff")
    try:
        # Warm the connection and server command path before taking the distribution.
        for _ in range(5):
            router.record_observation(client, namespace, decision, "success")
        samples_ms = []
        for _ in range(50):
            started = time.perf_counter()
            router.record_observation(client, namespace, decision, "success")
            samples_ms.append((time.perf_counter() - started) * 1_000)
        assert statistics.median(samples_ms) < 5.0, samples_ms
    finally:
        client.delete(key)
