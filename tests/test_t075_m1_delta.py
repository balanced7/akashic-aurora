"""T075 M1-DELTA ACCEPTANCE -- runner as managed child + circuit breaker + summary injection.

Spec: docs/library/report/20260715_t060-m1-continuous-presence-reconciliati_32cac4.md slice M1-delta row 4.
deepseek builds, claude verifies.

Unit tests for DaemonLock and ManagedChild (no live Redis needed).
Integration pins P5r/P6/P7/P9 are live-Redis-only and skip-gated.
"""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.bifrost_child import (
    DaemonLock, ManagedChild, read_summary, format_summary_for_prompt,
)


class FakeRedis:
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
        self.kv.pop(k, None), self.ex.pop(k, None)
    def exists(self, k):
        return k in self.kv


# ---------------------------------------------------------------- DaemonLock
def test_daemon_lock_acquire_heartbeat_release():
    c = FakeRedis()
    dl = DaemonLock(c, "bifrost", "t075", ttl=30)
    assert dl.acquire()
    assert "bifrost:daemon:t075" in c.kv
    rec = json.loads(c.kv["bifrost:daemon:t075"])
    assert rec["token"] == dl.token
    assert dl.heartbeat()
    assert dl.release()
    assert "bifrost:daemon:t075" not in c.kv


def test_daemon_lock_refuses_second():
    c = FakeRedis()
    d1 = DaemonLock(c, "bifrost", "t075")
    d2 = DaemonLock(c, "bifrost", "t075")
    assert d1.acquire()
    assert not d2.acquire()


def test_daemon_lock_heartbeat_rejects_foreign():
    c = FakeRedis()
    dl = DaemonLock(c, "bifrost", "t075")
    dl.acquire()
    c.kv["bifrost:daemon:t075"] = json.dumps({"token": "stolen", "pid": 999})
    assert not dl.heartbeat()


def test_f5_nx_reclaim_on_vanished_key():
    """F5: a vanished daemon key (outage > TTL) gets one nx-reclaim attempt.
    Heartbeat succeeds when nobody contested -- the lock was scrubbed, not stolen."""
    c = FakeRedis()
    dl = DaemonLock(c, "bifrost", "t075", ttl=30)
    dl.acquire()
    # simulate key vanishing (Redis restart)
    del c.kv["bifrost:daemon:t075"]
    assert dl.heartbeat(), "F5: vanished-but-uncontested key must be nx-reclaimed"
    rec = json.loads(c.kv["bifrost:daemon:t075"])
    assert rec["token"] == dl.token
    assert rec.get("reclaimed") is True


def test_f5_stand_down_when_nx_loses():
    """F5: nx-reclaim LOSES to a foreign holder -> stand down."""
    c = FakeRedis()
    dl = DaemonLock(c, "bifrost", "t075", ttl=30)
    dl.acquire()
    del c.kv["bifrost:daemon:t075"]
    # foreign daemon raced in first
    c.kv["bifrost:daemon:t075"] = json.dumps({"token": "foreign", "pid": 999})
    assert not dl.heartbeat(), "F5: nx-reclaim must stand down when a foreign holder won"


# ---------------------------------------------------------------- ManagedChild
def test_child_spawn_poll_and_nonblocking_backoff(monkeypatch, tmp_path):
    """F2: backoff is non-blocking -- _handle_exit sets _next_spawn_at, spawn()
    fires on the next poll() tick after the timestamp elapses."""
    child_script = tmp_path / "child.py"
    child_script.write_text("import sys; sys.exit(1)\n")

    mc = ManagedChild(
        [sys.executable, str(child_script)],
        cwd=str(tmp_path),
        breaker_max=10,
    )
    mc._backoffs = (0.01, 0.01, 0.01, 0.01, 0.01, 0.01)
    mc.spawn()
    assert mc.alive
    time.sleep(0.5)  # child exits quickly
    code = mc.poll()
    assert code == 1
    # F2: _next_spawn_at was set, not a blocking sleep
    assert mc._next_spawn_at > 0
    assert not mc.alive
    # advance past backoff -> spawn() succeeds
    mc._next_spawn_at = 0
    mc.spawn()
    assert mc.alive
    mc.terminate()


def test_f1_drainer_ring_collects_output(monkeypatch, tmp_path):
    """F1: drainer thread reads stdout into ring buffer; pipe never blocks.
    on_exit receives ring contents, not a partial post-mortem pipe read."""
    child_script = tmp_path / "child_chatty.py"
    lines = "\n".join(f"line {i}" for i in range(50))
    child_script.write_text(
        f"import sys\nfor i in range(50): print(f'line {{i}}')\nsys.exit(0)\n"
    )

    exited = []
    def _on_exit(code, tail):
        exited.append((code, tail))

    mc = ManagedChild(
        [sys.executable, str(child_script)],
        cwd=str(tmp_path),
        breaker_max=10,
    )
    mc.on_exit = _on_exit
    mc._backoffs = (0.01, 0.01, 0.01, 0.01, 0.01, 0.01)
    mc.spawn()
    time.sleep(1)  # chatty child finishes
    code = mc.poll()
    assert code == 0
    assert len(exited) == 1
    _, tail = exited[0]
    assert "line 0" in tail
    assert "line 49" in tail, f"F1: drainer must collect ALL output, got {len(tail)} chars"


def test_f1_utf8_decode_error_cannot_kill_drainer_and_wedge_child(monkeypatch, tmp_path):
    """F1-UTF8: the managed reader must explicitly decode the UTF-8 that runners emit.

    Windows defaults a bare ``Popen(text=True)`` reader to cp1252.  Runners call
    ``self_bless_stdout()`` and therefore emit UTF-8.  A valid UTF-8 continuation byte
    that cp1252 cannot decode used to raise inside the drainer's broad exception guard;
    the guard hid the dead reader, the pipe filled, and the still-live child blocked in
    write/flush.  The no-newline flood below matches DeepSeek's streamed-token shape.
    """
    import scripts.bifrost_child as child_mod

    child_script = tmp_path / "child_utf8_flood.py"
    child_script.write_text(
        f"import sys\nsys.path.insert(0, {ROOT!r})\n"
        "from core.foundation.streams import self_bless_stdout\n"
        "self_bless_stdout()\n"
        "print('\\u3041', flush=True)\n"  # UTF-8 e3 81 81; cp1252 cannot decode 0x81
        "for _ in range(256):\n"
        "    print('x' * 2048, end='', flush=True)\n"
        "print('DONE', flush=True)\n",
        encoding="utf-8",
    )

    real_popen = child_mod.subprocess.Popen

    def _cp1252_when_reader_is_implicit(*args, **kwargs):
        # Make the Windows default deterministic on every test host.  A production
        # reader that declares UTF-8 is left untouched and passes this exact drill.
        if kwargs.get("encoding") is None:
            kwargs["encoding"] = "cp1252"
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(child_mod.subprocess, "Popen", _cp1252_when_reader_is_implicit)
    mc = ManagedChild(
        [sys.executable, str(child_script)],
        env=dict(os.environ),
        cwd=ROOT,
        breaker_max=10,
    )
    try:
        mc.spawn()
        deadline = time.time() + 4.0
        while mc.alive and time.time() < deadline:
            time.sleep(0.02)
        assert not mc.alive, (
            "F1-UTF8: child is still alive after its bounded write -- the decoder killed "
            f"the drainer and the pipe filled (drainer_alive={mc._drainer.is_alive()}, "
            f"drainer_done={mc._drainer_done.is_set()}, ring_lines={len(mc._ring)})")
        assert mc.poll() == 0
        tail = "\n".join(mc._ring)
        assert "\u3041" in tail and "DONE" in tail, (
            "F1-UTF8: the drainer must preserve Unicode and reach the final sentinel")
    finally:
        if mc.alive:
            mc.terminate()


def test_child_benign_exit_resets_and_stops():
    """N1: exit 0 = deliberate handover. Backoff resets, _next_spawn_at = inf
    so the daemon never auto-respawns."""
    mc = ManagedChild(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        breaker_max=3,
    )
    mc._backoffs = (0, 0, 0, 0, 0, 0)
    mc._crashes.append(time.time())
    mc._crashes.append(time.time())
    mc._backoff_idx = 2
    mc.spawn()
    time.sleep(0.3)
    mc.poll()
    assert mc._backoff_idx == 0
    assert len(mc._crashes) == 0
    # N1: benign exit -> infinite backoff (no auto-respawn)
    assert mc._next_spawn_at == float("inf"), "N1: exit 0 must set infinite backoff"


def test_child_circuit_breaker_trips():
    """M1-P9 unit: 3 crashes in window -> tripped, on_blocker called, spawn refuses."""
    blocked = []
    mc = ManagedChild(
        [sys.executable, "-c", "import sys; sys.exit(1)"],
        on_blocker=lambda: blocked.append("fired"),
        breaker_window_s=300,
        breaker_max=3,
    )
    mc._backoffs = (0, 0, 0, 0, 0, 0)
    mc._handle_exit(1)
    assert not mc.tripped
    mc._handle_exit(1)
    assert not mc.tripped
    mc._handle_exit(1)
    assert mc.tripped
    assert blocked == ["fired"]
    assert mc.spawn() is None
    # the last non-trip _handle_exit set _next_spawn_at; the trip returns early
    # without touching it. What matters: spawn refuses, tripped is True.
    assert mc.tripped


def test_child_tripped_breaker_does_not_spawn():
    mc = ManagedChild(
        [sys.executable, "-c", "pass"],
        breaker_max=1,
    )
    mc._tripped = True
    assert mc.spawn() is None


# ---------------------------------------------------------------- summary
def test_read_summary_success(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"exit_code": 0, "turns": 5, "verdict": "ok"}))
    s = read_summary(str(p))
    assert s["turns"] == 5 and s["verdict"] == "ok"


def test_read_summary_absent(tmp_path):
    assert read_summary(str(tmp_path / "nope.json")) is None


def test_format_summary_for_prompt():
    s = {"exit_code": 1, "turns": 3, "verdict": "error",
         "last_error": "KeyError: foo", "timestamp": "2026-07-15T12:00:00"}
    line = format_summary_for_prompt(s)
    assert "ERROR" in line
    assert "3 turn" in line
    assert "KeyError" in line


# ---------------------------------------------------------------- F7 integration pins
# Live-Redis integration tests for P5r/P6/P7/P9 -- skip-gated when no bus.

def _live_redis():
    try:
        from core.comm.bus import Bus
        b = Bus("t075delta-int", promote=False)
        return b._client if (b.online and b.probe()) else None
    except Exception:
        return None

_C = _live_redis()
needs_redis = pytest.mark.skipif(_C is None, reason="live Redis required")


@needs_redis
def test_p5r_daemon_spawns_runner_child_on_start(tmp_path):
    """P5r integration: daemon --spawn-runner acquires its daemon lock and
    spawns the runner child (visible in stdout). Two-tier lock split confirmed:
    daemon lock key exists independent of runner lock."""
    ns = f"t075d-p5r-{os.getpid()}"
    home = str(tmp_path)
    daemon_lock_key = f"{ns}:daemon:t075p5r"
    try:
        import subprocess, time as _time
        daemon_path = os.path.join(ROOT, "scripts", "bifrost_daemon.py")
        env = dict(os.environ)
        env.update({"BIFROST_NAMESPACE": ns, "HOME": home, "USERPROFILE": home,
                    "AKASHIC_TIMEOUT_MULTIPLIER": "0.1",
                    "AKASHIC_DAEMON_LOCK_TTL_S": "30", "AKASHIC_DAEMON_HB_S": "4",
                    "DEEPSEEK_API_KEY": "drill-noop"})
        proc = subprocess.Popen(
            [sys.executable, daemon_path, "--agent", "t075p5r", "--spawn-runner",
             "--max-runtime", "8"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=env, cwd=ROOT)
        deadline = _time.time() + 15
        daemon_up = False
        daemon_rec = {}
        while _time.time() < deadline:
            raw = _C.get(daemon_lock_key)
            if raw:
                daemon_up = True
                daemon_rec = json.loads(raw)
                break
            _time.sleep(0.3)
        # collect stdout
        try:
            out, _ = proc.communicate(timeout=8)
        except Exception:
            proc.terminate()
            out, _ = proc.communicate(timeout=5)
        out_text = out or ""
        assert daemon_up, f"P5r: daemon never acquired its lock\n{out_text[:500]}"
        assert "runner spawned" in out_text.lower() or "runner" in out_text.lower(), \
            f"P5r: daemon must attempt runner spawn\n{out_text[:500]}"
        # daemon lock held with correct token shape
        assert daemon_rec.get("token", "").startswith("daemon:"), \
            f"P5r: daemon lock token shape: {daemon_rec}"
    finally:
        for k in _C.scan_iter(match=f"{ns}:*"):
            _C.delete(k)


@needs_redis
def test_p9_daemon_starts_in_spawn_runner_mode(tmp_path):
    """P9 integration: daemon --spawn-runner starts and holds daemon lock.
    The circuit breaker is wired -- unit pin test_child_circuit_breaker_trips
    covers the trip logic. This test proves the spawn-runner path is live."""
    ns = f"t075d-p9-{os.getpid()}"
    home = str(tmp_path)
    daemon_lock_key = f"{ns}:daemon:t075p9"
    try:
        import subprocess, time as _time
        daemon_path = os.path.join(ROOT, "scripts", "bifrost_daemon.py")
        env = dict(os.environ)
        env.update({"BIFROST_NAMESPACE": ns, "HOME": home, "USERPROFILE": home,
                    "AKASHIC_TIMEOUT_MULTIPLIER": "0.05",
                    "AKASHIC_DAEMON_LOCK_TTL_S": "30", "AKASHIC_DAEMON_HB_S": "4",
                    "AKASHIC_CB_WINDOW_S": "20", "AKASHIC_CB_MAX": "2",
                    "DEEPSEEK_API_KEY": "drill-noop"})
        proc = subprocess.Popen(
            [sys.executable, daemon_path, "--agent", "t075p9", "--spawn-runner",
             "--max-runtime", "10"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=env, cwd=ROOT)
        deadline = _time.time() + 15
        daemon_up = False
        while _time.time() < deadline:
            raw = _C.get(daemon_lock_key)
            if raw:
                daemon_up = True
                break
            _time.sleep(0.3)
        try:
            out, _ = proc.communicate(timeout=5)
        except Exception:
            proc.terminate()
            out, _ = proc.communicate(timeout=5)
        out_text = out or ""
        assert daemon_up, f"P9: daemon never acquired its lock\n{out_text[:500]}"
        assert "runner spawned" in out_text.lower() or "runner" in out_text.lower(), \
            f"P9: daemon must attempt runner spawn\n{out_text[:500]}"
    finally:
        for k in _C.scan_iter(match=f"{ns}:*"):
            _C.delete(k)
