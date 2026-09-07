"""T329 RED pins: absence is not retirement, and cursor skips inspect cargo.

The original doctor used a missing transient presence signal to call a seat retired,
then recommended ``bifrost-skip-to-now`` over mail it had never inspected.  These pins
stand up the real producer path in an isolated namespace: an absent seat receives one
unsettled handoff.  The diagnostic must call that an UNMANNED SEAT, and the destructive
cursor operation must refuse unless the operator explicitly names every protected item.

Run: py -m pytest tests/test_t329_unmanned_seat_mail_safety.py -q
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from core.comm import control, cursor_admin, doctor, mailbox  # noqa: E402
from core.comm.bus import Bus  # noqa: E402


@pytest.fixture()
def isolated_bus(monkeypatch):
    """A real Bus producer with every key fenced inside one throwaway namespace."""
    namespace = f"t329-{uuid.uuid4().hex[:10]}"
    agent = f"t329-unmanned-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", namespace)
    bus = Bus(agent)
    if not bus.online:
        pytest.skip("live Redis is required for the real-producer acceptance pins")
    try:
        yield namespace, agent, bus
    finally:
        try:
            control.resume()
        except Exception:
            pass
        try:
            keys = list(bus._client.scan_iter(match=f"{namespace}:*"))
            if keys:
                bus._client.delete(*keys)
        except Exception:
            pass


def _quiet_probes(now: float):
    """Fence Doctor's unrelated ambient readers while leaving mail inspection real."""
    return {
        "worklive": lambda _agent: None,
        "progress": lambda _agent: None,
        "backlog": lambda _agent: 1,
        "stalled_since": lambda _agent, _present: None,
        "halted": lambda _agent: None,
        "lane_health": lambda _agent: None,
        "token_cost": lambda _agent: None,
        "wire": lambda _agent: [],
        "feed_failures": lambda _agent: [],
        "stale_code": lambda _agent: None,
        "bench_count": lambda _agent: 0,
        "now": now,
    }


def test_absent_seat_with_unsettled_handoff_is_unmanned_not_retired(isolated_bus):
    _namespace, agent, _bus = isolated_bus
    sent = Bus("t329-sender").send(agent, "handoff", "Please review the live T329 fence.")
    assert sent, "the acceptance pin must exercise the real message producer"

    findings = doctor.examine(agent, probes=_quiet_probes(time.time()))
    assert not [row for row in findings if row["state"] == "offline_backlog"], findings
    unmanned = [row for row in findings if row["state"] == "unmanned_seat"]
    assert len(unmanned) == 1, findings
    rendered = f"{unmanned[0]['line']} {unmanned[0]['drill']}".lower()
    assert "unmanned seat" in rendered
    assert "handoff" in rendered and "unsettled" in rendered
    assert "start" in rendered or "reroute" in rendered
    assert "ghost" not in rendered and "skip-to-now" not in rendered


def test_skip_refuses_unsettled_handoff_until_override_names_it(isolated_bus):
    _namespace, agent, bus = isolated_bus
    sent = Bus("t329-sender").send(agent, "handoff", "This work must survive an admin skip.")
    assert sent
    before = bus.cursor()
    assert control.pause(reason="T329 isolated acceptance", by="sol", ttl=60)

    refused = cursor_admin.skip_to_now(agent, by="sol", reason="T329 acceptance drill")
    assert refused["ok"] is False, refused
    assert "unsettled" in refused["refused"].lower()
    protected = refused.get("unsettled") or []
    assert len(protected) == 1 and protected[0]["kind"] == "handoff", refused
    assert bus.cursor() == before, "a refused inspection must leave every cursor untouched"

    allowed = cursor_admin.skip_to_now(
        agent,
        by="sol",
        reason="T329 explicit named override drill",
        override_unsettled=[protected[0]["sha"]],
    )
    assert allowed["ok"] is True, allowed
    assert allowed.get("override_unsettled") == [protected[0]["sha"]]
    assert bus.cursor().get("inbox", "0") == bus.tail().get("inbox", "0")


def test_ghost_sweep_protects_unsettled_handoff_without_named_override():
    from test_t095_m0_mailbox_shadow import _FakeRedis

    namespace = "t329-mailbox"
    agent = "t329-target"
    client = _FakeRedis()
    fields = {
        "frm": "codex_root_deadbeef",
        "to": agent,
        "kind": "handoff",
        "content": "The sender ended; the requested work did not.",
        "ts": str(time.time() - 48 * 3600),
    }
    sha = mailbox._ingest_one(client, namespace, agent, "work_inbox", "100-0", fields)
    assert sha
    client.hset(
        mailbox._keys(namespace, agent)["msg"] + sha,
        mapping={"ts_s": str(time.time() - 48 * 3600)},
    )

    protected = mailbox.retire_ghost_mail(
        namespace,
        agent,
        client=client,
        dry_run=False,
        is_live=lambda _sender: False,
    )
    assert protected["retired"] == 0, protected
    assert protected.get("protected_unsettled") == 1, protected
    assert mailbox.state_for(namespace, agent, sha, client=client)["intent"] is None

    overridden = mailbox.retire_ghost_mail(
        namespace,
        agent,
        client=client,
        dry_run=False,
        is_live=lambda _sender: False,
        override_unsettled=[sha],
    )
    assert overridden["retired"] == 1, overridden

