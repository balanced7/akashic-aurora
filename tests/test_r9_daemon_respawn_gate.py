"""R9 (fences/watcher-controls, build spec 2026-09-29) -- the daemon does not respawn beside a foreign runner.

Heimdall's second assertion for the R9 drill: "a re-arm with the lock still held logs 'cause not cleared' and spawns
nothing". Live receipt 2026-09-30 00:14-00:33: after a push, the kimi runner self-restarted into a successor (a bare
token, pid 83136) that held the runner lock while it worked; the daemon respawned beside it, each spawn failed the
lock and counted as a crash, the breaker tripped and re-armed every ~6.5 min, and each trip paged Discord.
foreign_holder_after_exit() is the gate the daemon's child-poll site now applies: a foreign live holder means idle
(W102's reclaim probe spawns when the lock frees), never a respawn.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bifrost_daemon as bd  # noqa: E402
from core.comm import runner_lock  # noqa: E402


def _holder(monkeypatch, value):
    monkeypatch.setattr(runner_lock, "holder", lambda agent: value)


def test_a_bare_successor_holding_the_lock_is_foreign(monkeypatch):
    _holder(monkeypatch, {"token": "kimi:83136:4e7f3fc4611a", "pid": 83136, "ts": "2026-09-30T04:32:35+00:00"})
    fh = bd.foreign_holder_after_exit("kimi", exited_pid=68972)
    assert fh and fh["pid"] == 83136, "the successor holds the seat: idle, do not respawn"


def test_the_exited_child_s_own_unexpired_key_is_not_foreign(monkeypatch):
    _holder(monkeypatch, {"token": "kimi:68972:f6b5f6028e2f", "pid": 68972})
    assert bd.foreign_holder_after_exit("kimi", exited_pid=68972) is None, "its key just has not expired yet"


def test_a_daemon_token_is_not_foreign(monkeypatch):
    _holder(monkeypatch, {"token": "daemon:kimi:3d239200b364", "pid": 50004})
    assert bd.foreign_holder_after_exit("kimi", exited_pid=1) is None


def test_a_free_lock_is_not_foreign(monkeypatch):
    _holder(monkeypatch, None)
    assert bd.foreign_holder_after_exit("kimi", exited_pid=1) is None


def test_an_unreadable_lock_never_blocks_the_daemon_loop(monkeypatch):
    def boom(agent):
        raise RuntimeError("redis down")
    monkeypatch.setattr(runner_lock, "holder", boom)
    assert bd.foreign_holder_after_exit("kimi", exited_pid=1) is None


def test_a_malformed_pid_is_treated_as_foreign_not_as_a_crash(monkeypatch):
    _holder(monkeypatch, {"token": "kimi:x:abc", "pid": "not-a-pid"})
    assert bd.foreign_holder_after_exit("kimi", exited_pid=1) == {"token": "kimi:x:abc", "pid": "not-a-pid"}
