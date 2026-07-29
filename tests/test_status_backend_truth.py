"""T118 status honesty pins for the SQLite durable-tier cutover.

The cutover can be mechanically active while ``agent_cli.py status`` still says
``(+ File mirror)`` because the renderer historically inferred only Redis
reachability.  These pins require the public status surface to name the durable
tier selected by the canonical store factory.
"""

import json
from types import SimpleNamespace

import agent_cli
from core.foundation import redis_connection
from core.foundation import store as store_mod
from core.narrative import health as health_mod


class _RedisProbe:
    def keys(self, _pattern):
        return []


def _run_status(monkeypatch, capsys, tmp_path, *, backend, redis_up):
    if backend is None:
        monkeypatch.delenv("AKASHIC_STORE_BACKEND", raising=False)
    else:
        monkeypatch.setenv("AKASHIC_STORE_BACKEND", backend)

    real_create_store = store_mod.create_store
    json_path = tmp_path / "status-store.json"
    monkeypatch.setattr(
        store_mod,
        "create_store",
        lambda: real_create_store(prefer_redis=False, file_path=str(json_path)),
    )
    monkeypatch.setattr(
        redis_connection,
        "connect_to_redis_with_fail_fast",
        lambda **_kwargs: _RedisProbe() if redis_up else None,
    )
    monkeypatch.setattr(health_mod, "snapshot", lambda _store: {})

    rc = agent_cli.cmd_status(SimpleNamespace(json=True))
    payload = json.loads(capsys.readouterr().out)
    return rc, payload


def test_status_names_sqlite_mirror_when_redis_is_up(monkeypatch, capsys, tmp_path):
    rc, payload = _run_status(
        monkeypatch, capsys, tmp_path, backend="sqlite", redis_up=True
    )

    assert rc == 0
    assert payload["backend"] == "Redis localhost:16379 (+ SQLite mirror)"


def test_status_names_sqlite_fallback_when_redis_is_down(monkeypatch, capsys, tmp_path):
    rc, payload = _run_status(
        monkeypatch, capsys, tmp_path, backend="sqlite", redis_up=False
    )

    assert rc == 0
    assert payload["backend"] == "SQLite (Redis down -> fallback active)"


def test_status_preserves_file_labels_for_default_backend(monkeypatch, capsys, tmp_path):
    rc, payload = _run_status(
        monkeypatch, capsys, tmp_path, backend=None, redis_up=True
    )

    assert rc == 0
    assert payload["backend"] == "Redis localhost:16379 (+ File mirror)"
