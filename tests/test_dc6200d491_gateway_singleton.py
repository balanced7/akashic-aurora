"""dc6200d491 -- the Discord gateway gets a singleton guard.

The gateway was the only supervised organ with no singleton lock: its sole idempotence
was revive counting a process-table string, which is how 4 concurrent gateways existed
at 00:20 on 2026-08-26 (each opening its own websocket, each handling every inbound
message). scripts/bifrost_runner_discord.py now wires DaemonLock the same way
bifrost_daemon.py does for deepseek/kimi/claude, keyed by its own agent id ("discord")
so it never collides with revive.DAEMON_AGENTS.

Two kinds of pin, both offline (no live Redis, no live Discord socket):
  (1) source pins -- main() actually wires acquire/refuse/heartbeat/release the way
      this file claims, so a future edit that quietly drops a piece fails loudly.
  (2) the drill itself -- "start a second copy and prove it refuses", run against the
      real DaemonLock class with a fake redis client standing in for the bus, exactly
      as the defer item (dc6200d491) asked for.

Run:  py -m pytest tests/test_dc6200d491_gateway_singleton.py -v
"""
from __future__ import annotations

import inspect
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.bifrost_child import DaemonLock


class FakeRedis:
    """Same shape as tests/test_t075_m1_delta.py's fixture -- nx-SET + TTL bookkeeping,
    no network. Kept local rather than imported: a shared fixture module is not worth
    the coupling for two small test files."""

    def __init__(self):
        self.kv, self.ex = {}, {}

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k], self.ex[k] = v, ex
        return True

    def get(self, k):
        return self.kv.get(k)

    def delete(self, k):
        self.kv.pop(k, None)
        self.ex.pop(k, None)

    def exists(self, k):
        return k in self.kv


def _gateway_source() -> str:
    return (REPO / "scripts" / "bifrost_runner_discord.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ (1) source pins
def test_main_imports_and_keys_the_lock_by_the_gateways_own_agent_id():
    src = _gateway_source()
    assert "from scripts.bifrost_child import DaemonLock" in src
    assert "DaemonLock(bus._client, bus.ns, GATEWAY_AGENT_ID" in src, (
        "the lock must be keyed by GATEWAY_AGENT_ID ('discord'), not a caller-supplied "
        "agent -- otherwise a twin under a different id would never collide")


def test_failed_acquire_refuses_before_opening_a_socket():
    src = _gateway_source()
    acquire_at = src.index("_dlock.acquire()")
    connect_at = src.index("client.run(")
    assert acquire_at < connect_at, (
        "the guard must run before client.run() -- refusing after the websocket is "
        "already open defeats the point of a singleton")
    # the refusal path itself: loud, and a non-zero exit so a supervisor never mistakes
    # a refused twin for a clean idle exit.
    refuse_block = src[acquire_at:connect_at]
    assert "return 2" in refuse_block
    assert "REFUSED" in refuse_block


def test_pulse_heartbeats_the_lock_not_just_worklive():
    """A guard that is acquired once and never refreshed is a TTL countdown to a false
    twin-refusal on the process's OWN restart path, or worse: a stale lock outliving a
    crashed gateway blocks the real replacement from starting at all."""
    src = _gateway_source()
    pulse_src = src[src.index("def _pulse():"):src.index("threading.Thread(target=_pulse")]
    assert "_dlock.heartbeat()" in pulse_src


def test_lock_release_is_registered_for_normal_exit():
    src = _gateway_source()
    assert "atexit.register(_dlock.release)" in src


# ------------------------------------------------------------------ (2) the drill itself
def test_a_second_gateway_copy_refuses_to_start():
    """The exact acceptance criterion in dc6200d491: start a second copy and prove it
    refuses. Exercised against the real DaemonLock class and the real key shape
    (ns:daemon:discord) so this is the same mechanism main() calls, not a stand-in."""
    c = FakeRedis()
    first = DaemonLock(c, "bifrost", "discord", ttl=30)
    assert first.acquire(), "the first gateway must win an uncontested lock"

    second = DaemonLock(c, "bifrost", "discord", ttl=30)
    assert not second.acquire(), (
        "a twin gateway must refuse while the first is still live -- this is the exact "
        "shape of the 4-concurrent-gateways incident at 00:20 on 2026-08-26")

    # the surviving copy keeps working; heartbeating never lets the loser's later
    # retries suddenly succeed just because time passed.
    assert first.heartbeat()
    assert not second.acquire()

    # clean exit frees the slot for a real successor (restart, not a twin).
    assert first.release()
    third = DaemonLock(c, "bifrost", "discord", ttl=30)
    assert third.acquire(), "after a clean release, a fresh gateway must be able to start"


def test_gateways_own_lock_key_never_collides_with_the_bifrost_daemon_agents():
    """revive.DAEMON_AGENTS = ('deepseek', 'kimi', 'claude') owns a different lock
    namespace (bifrost_daemon.py's per-agent daemon lock). The gateway is not in that
    tuple and must not silently start sharing a key with one of them."""
    from scripts import revive
    assert "discord" not in revive.DAEMON_AGENTS
    c = FakeRedis()
    gw = DaemonLock(c, "bifrost", "discord", ttl=30)
    other = DaemonLock(c, "bifrost", "claude", ttl=30)
    assert gw.acquire()
    assert other.acquire(), "the gateway's lock must not block claude's own daemon lock"
    assert gw._key != other._key
