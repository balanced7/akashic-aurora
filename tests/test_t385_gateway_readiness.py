"""RED pins for process-owned, world-aware Discord gateway readiness."""
from __future__ import annotations

import importlib
import os

from scripts import bifrost_runner_discord as gateway
from scripts import revive


GATEWAY_LINE = (
    "4242\tpython.exe C:/Aurora/scripts/run_aurora_service.py --world prod -- "
    "C:/Aurora/scripts/bifrost_runner_discord.py"
)


def _readiness_module():
    return importlib.import_module("core.comm.gateway_readiness")


def _record(**overrides):
    row = {
        "pid": 4242,
        "generation": "4242-test",
        "ready": True,
        "world": "prod",
        "beat_ts": 100.0,
        "code_sha": "abc123",
        "detail": "discord on_ready",
    }
    row.update(overrides)
    return row


def test_readiness_requires_fresh_matching_pid_world_and_generation():
    readiness = _readiness_module()

    healthy = readiness.assess(
        _record(), live_pids={4242}, expected_world="prod", now=120.0, ttl=45.0
    )
    assert healthy["healthy"] is True

    cases = (
        ({"pid": 9999}, "pid"),
        ({"world": "alpha"}, "world"),
        ({"beat_ts": 1.0}, "stale"),
        ({"ready": False}, "not ready"),
        ({"generation": ""}, "generation"),
    )
    for changes, marker in cases:
        verdict = readiness.assess(
            _record(**changes),
            live_pids={4242},
            expected_world="prod",
            now=120.0,
            ttl=45.0,
        )
        assert verdict["healthy"] is False
        assert marker in verdict["detail"].lower()


def test_revive_gateway_health_refuses_presence_without_owned_readiness():
    no_signal = revive._gateway_health(
        GATEWAY_LINE, None, expected_world="prod", now=120.0
    )
    assert no_signal["healthy"] is False
    assert no_signal["repairable"] is False
    assert "readiness" in no_signal["detail"].lower()

    healthy = revive._gateway_health(
        GATEWAY_LINE, _record(), expected_world="prod", now=120.0
    )
    assert healthy["healthy"] is True
    assert healthy["readiness"] is True
    assert healthy["pid"] == 4242


def test_duplicate_gateway_is_named_but_never_plans_an_additional_spawn():
    row = revive._gateway_health(
        GATEWAY_LINE + "\n" + GATEWAY_LINE.replace("4242", "4243", 1),
        _record(),
        expected_world="prod",
        now=120.0,
    )
    assert row["healthy"] is False
    assert row["repairable"] is False
    assert "duplicate" in row["detail"].lower()
    assert revive.decide({"gateway": row}, target="gateway") == []


def test_verify_rejects_process_only_health_without_readiness(monkeypatch):
    monkeypatch.setattr(
        revive,
        "observe",
        lambda: {"gateway": {"healthy": True, "readiness": False}},
    )
    clock = iter((0.0, 0.0, 2.0))
    monkeypatch.setattr(revive.time, "time", lambda: next(clock))
    monkeypatch.setattr(revive.time, "sleep", lambda _: None)
    assert revive._verify("gateway", deadline_s=1.0) is False


def test_windows_revival_starts_the_owned_task_instead_of_detaching_gateway():
    if os.name != "nt":
        return
    plan = revive.decide(
        {"gateway": {"healthy": False, "repairable": True, "detail": "absent"}},
        target="gateway",
    )
    assert len(plan) == 1
    step = plan[0]
    assert step["kind"] == "scheduled-task-start"
    joined = " ".join(step["cmd"]).lower()
    assert "schtasks" in joined and "/run" in joined
    assert "bifrost_runner_discord.py" not in joined


def test_event_loop_guard_uses_the_existing_readiness_ttl():
    assert gateway._event_loop_is_stale(last_beat=10.0, now=99.9, ttl=45.0) is False
    assert gateway._event_loop_is_stale(last_beat=10.0, now=100.1, ttl=45.0) is True
