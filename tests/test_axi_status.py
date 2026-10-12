"""Pins for `status` after the AXI conversion: the real lesson count, keys labelled as keys,
the spine verdict, and the hint only when something is wrong.

Run: uv run pytest tests/test_axi_status.py -q
"""

from types import SimpleNamespace

import pytest

import agent_cli


class _Redis:
    def keys(self, pattern):
        # three lessons plus the store's index keys: the old door reported all of these
        return {"learn:*": ["learn:experiment:a", "learn:experiment:b", "learn:experiment:c", "learn:index", "learn:x"],
                "mem:*": ["mem:1"], "*": ["k"] * 9}[pattern]  # fmt: skip


@pytest.fixture
def status(monkeypatch, capsys):
    import core.foundation.redis_connection as rc
    import core.learning.learning_store as ls
    import core.narrative.health as nh

    holder = {"client": _Redis(), "health": {"route:persist": 2}}
    monkeypatch.setattr(rc, "connect_to_redis_with_fail_fast", lambda **k: holder["client"])
    monkeypatch.setattr(nh, "snapshot", lambda store: holder["health"])
    monkeypatch.setattr(
        ls, "get_learning_store", lambda: SimpleNamespace(get_learning_store_stats=lambda: {"total_experiments": 3})
    )
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(client=..., health=None):
        if client is not ...:
            holder["client"] = client
        if health is not None:
            holder["health"] = health
        code = agent_cli.cmd_status(SimpleNamespace(json=False))
        return code, capsys.readouterr().out

    return run


def test_lessons_are_the_store_count_and_keys_are_labelled(status):
    code, text = status()
    assert code == 0
    assert "lessons: 3" in text
    assert "learn: 5" in text
    assert "redis: up" in text
    assert "spine_health: ok" in text
    assert "help[" not in text, "a healthy status answers itself"


def test_spine_errors_point_at_doctor(status):
    _, text = status(health={"route:persist:error": 1})
    assert "spine_health: errors" in text
    assert "doctor" in text


def test_redis_down_says_so(status):
    _, text = status(client=None, health={})
    assert "redis: down" in text
    assert "keys: null" in text
    assert "spine_health: no counters yet" in text
    assert "doctor" in text
