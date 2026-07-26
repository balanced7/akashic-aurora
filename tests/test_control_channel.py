"""The out-of-band control channel must answer when the bus cannot.

Born from the kimi wedge (2026-07-26): an agent up, heartbeating, and UNCOMMANDABLE for 12+
hours because the only path to it was the path that had failed.

The properties under test are the ones that make it out-of-band rather than just another
channel:
  - the port is DERIVED, so there is no registry to go stale
  - it answers while the bus is unreachable
  - a bind conflict is LOUD, never silently swallowed
  - it is loopback-only
  - "nobody listening" is distinguishable from "listener refused"
"""
import os
import socket
import threading
import time

import pytest

from core.comm import control_channel as cc


@pytest.fixture()
def chan():
    # A port well away from the real base so a live runner cannot collide with the test.
    ch = cc.ControlChannel("testagent", port=cc.CONTROL_PORT_BASE + 900)
    assert ch.start(), "test channel failed to bind"
    yield ch
    ch.stop()


def test_port_is_derived_not_registered():
    """No lookup table means nothing to go stale -- the whole reason for a pure function."""
    a, b = cc.port_for("kimi"), cc.port_for("kimi")
    assert a == b, "the same agent must always resolve to the same port"
    assert cc.port_for("kimi") != cc.port_for("deepseek"), "distinct agents must not collide"
    assert cc.CONTROL_PORT_BASE <= a < cc.CONTROL_PORT_BASE + 100


def test_port_is_stable_across_processes():
    """The killer detail: Python's hash() is randomised per process (PYTHONHASHSEED), so a
    hash()-based port would make two processes disagree about where one agent listens. That is
    exactly the stale-mapping failure this design exists to avoid, so it must be pinned."""
    import subprocess, sys
    src = ("import sys; sys.path.insert(0, r'%s'); "
           "from core.comm import control_channel as cc; print(cc.port_for('kimi'))"
           % os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[:300]
    assert int(out.stdout.strip()) == cc.port_for("kimi"), (
        "a separate process computed a DIFFERENT port for the same agent -- the mapping is "
        "not stable and the control channel would be unreachable"
    )


def test_ping_answers(chan):
    reply = cc.send("testagent", "ping", port=chan.port)
    assert reply and reply.startswith("pong"), f"got {reply!r}"
    assert f"pid={os.getpid()}" in reply, "ping must identify the process it reached"


def test_silence_is_distinguishable_from_refusal():
    """None means NOBODY IS LISTENING. An 'ERR ...' string means the listener answered and
    declined. Collapsing those two is the empty-versus-error defect this codebase has spent
    the week removing; a caller must be able to tell 'no channel' from 'no'."""
    assert cc.send("nobody-home", "ping", port=cc.CONTROL_PORT_BASE + 901, timeout=1.0) is None


def test_unknown_verb_is_refused_not_ignored(chan):
    reply = cc.send("testagent", "definitely-not-a-verb", port=chan.port)
    assert reply and reply.startswith("ERR"), f"got {reply!r}"
    assert "help" in reply, "a refusal should teach the caller what IS available"


def test_bind_conflict_is_loud(capsys):
    """Two agents on one port must not silently share it -- a conflict usually means a second
    instance is already running, which is precisely what the caller needs to hear."""
    first = cc.ControlChannel("dup", port=cc.CONTROL_PORT_BASE + 902)
    assert first.start()
    try:
        second = cc.ControlChannel("dup", port=cc.CONTROL_PORT_BASE + 902)
        assert second.start() is False, "the second bind must FAIL, not quietly succeed"
        assert "cannot bind" in capsys.readouterr().out
    finally:
        first.stop()


def test_listener_is_loopback_only(chan):
    """A control plane must never be reachable off-box."""
    conns = [c for c in socket.getaddrinfo("127.0.0.1", chan.port, proto=socket.IPPROTO_TCP)]
    assert conns, "expected a loopback binding"
    s = socket.socket()
    s.settimeout(1.0)
    try:
        # Binding the same port on the wildcard address must fail if we hold it on loopback
        # only when the OS considers them overlapping; the assertion that matters is simply
        # that we never bound 0.0.0.0 ourselves.
        assert chan._sock.getsockname()[0] == "127.0.0.1", (
            f"control channel bound {chan._sock.getsockname()[0]}, not loopback"
        )
    finally:
        s.close()


def test_custom_verb_dispatch(chan):
    seen = {}

    def _handler(arg):
        seen["arg"] = arg
        return f"ok:{arg}"

    chan.register("canary", _handler)
    reply = cc.send("testagent", "canary deploy-v2", port=chan.port)
    assert reply == "ok:deploy-v2", f"got {reply!r}"
    assert seen["arg"] == "deploy-v2", "the argument must reach the handler intact"


def test_answers_while_the_main_thread_is_blocked(chan):
    """THE POINT OF THE WHOLE MODULE.

    Simulates the kimi wedge: the main thread parks in a blocking read that will never return.
    The control channel must still answer, because it lives on its own thread and shares
    nothing with whatever wedged.
    """
    dead = socket.socket()
    dead.bind(("127.0.0.1", 0))
    dead.listen(1)
    blocked = threading.Event()

    def _wedge():
        victim = socket.create_connection(dead.getsockname())
        blocked.set()
        try:
            victim.settimeout(20)
            victim.recv(1)          # nothing will ever be sent -- this is the wedge
        except Exception:
            pass

    t = threading.Thread(target=_wedge, daemon=True)
    t.start()
    assert blocked.wait(5), "setup: the victim thread never reached its blocking read"

    reply = cc.send("testagent", "ping", port=chan.port)
    assert reply and reply.startswith("pong"), (
        "the control channel went silent while another thread was blocked -- it is not "
        "actually out-of-band"
    )
    dead.close()
