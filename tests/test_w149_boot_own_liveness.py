"""W149 pins: boot reports the READING session's own wakeability -- before it reports anyone else's.

The wish (docs/WISHLIST.md W149): on 2026-08-12 a seat ran a whole session unreachable and
learned it only from the Stop hook at session END. Boot rendered the sibling's idle minutes
and the fleet doctor, and nothing about the reader's own dead watcher.

Reconciled contract (claude half + deepseek fence half, 2026-08-13):
  probe order is daemon-first, seat-second, NEVER-SPAWN (deepseek D2 -- one code path);
  armed-with-dead-pid and never-armed are DIFFERENT states with different remedies
  (deepseek D1 -- the 08-12 failure was precisely the dead-pid case);
  a probe that cannot tell renders UNKNOWN -- never wakeable, never NOT WAKEABLE
  (claude A4; NB the stop hook's own _pid_alive fails OPEN and is therefore NOT the
  primitive here -- ask_bg's tri-state probe semantics are);
  daemon-live does not prove THIS session is the one it wakes: a live twin holding the
  consumer seat is named, not papered over (deepseek F2, the S3b shape);
  purity is structural: the render path calls no writer (deepseek's static-assert idea,
  done via ast per the L7 lesson -- never getsource+substring).

Pin families:
  P1-P4  core/comm/wake_seat.watcher_state -- the pure probe primitive
  P5     watcher_state purity: no filesystem writes
  P6-P11 agent_cli._boot_you_line -- the render contract (drill matrix, deepseek measure 1)
  P12    render purity, dynamic: empty filesystem diff (deepseek measure 3)
  P13    render purity, static: the function's AST calls no writer names
"""
import ast
import os
import textwrap

import pytest


# ---------------------------------------------------------------- the probe (P1-P5)

def _write_seat(tmp_path, agent, sid, body):
    p = tmp_path / f"bifrost_wake_{agent}_{sid}.pid"
    p.write_text(body, encoding="utf-8")
    return p


def test_p1_armed_live_pid(tmp_path):
    from core.comm.wake_seat import watcher_state
    _write_seat(tmp_path, "claude", "sid1", "4242")
    state, pid = watcher_state("claude", "sid1", tmp=str(tmp_path),
                               pid_probe=lambda p: True)
    assert state == "armed"
    assert pid == 4242


def test_p2_dead_pid_is_its_own_state(tmp_path):
    """D1: a seat file whose pid is dead is 'dead-seat', NOT 'unarmed' -- the remedy
    differs (stale-seat re-arm vs first arm), and the 08-12 failure was THIS state."""
    from core.comm.wake_seat import watcher_state
    _write_seat(tmp_path, "claude", "sid1", "4242")
    state, pid = watcher_state("claude", "sid1", tmp=str(tmp_path),
                               pid_probe=lambda p: False)
    assert state == "dead-seat"
    assert pid == 4242


def test_p3_no_seat_file_is_unarmed(tmp_path):
    from core.comm.wake_seat import watcher_state
    state, pid = watcher_state("claude", "sid1", tmp=str(tmp_path),
                               pid_probe=lambda p: True)
    assert state == "unarmed"
    assert pid is None


def test_p4_cannot_tell_is_unknown(tmp_path):
    """A4 honesty, both shapes: a garbage seat file and a tri-state probe returning
    None (ask_bg semantics: 'the probe failed: cannot tell') are both UNKNOWN --
    never a confident state in either direction."""
    from core.comm.wake_seat import watcher_state
    _write_seat(tmp_path, "claude", "sid1", "not-a-pid")
    state, _ = watcher_state("claude", "sid1", tmp=str(tmp_path),
                             pid_probe=lambda p: True)
    assert state == "unknown"

    _write_seat(tmp_path, "claude", "sid2", "4242")
    state2, _ = watcher_state("claude", "sid2", tmp=str(tmp_path),
                              pid_probe=lambda p: None)
    assert state2 == "unknown"


def test_p5_probe_writes_nothing(tmp_path):
    """A5 purity at the primitive: probing all four states leaves the directory
    byte-identical -- no rearm trigger, no latch, no marker, no seat mutation."""
    from core.comm.wake_seat import watcher_state
    _write_seat(tmp_path, "claude", "sid1", "4242")
    _write_seat(tmp_path, "claude", "sid3", "junk")

    def snapshot():
        return {n: (tmp_path / n).read_bytes() for n in sorted(os.listdir(tmp_path))}

    before = snapshot()
    for sid in ("sid1", "sid2", "sid3"):
        for probe in (lambda p: True, lambda p: False, lambda p: None):
            watcher_state("claude", sid, tmp=str(tmp_path), pid_probe=probe)
    assert snapshot() == before


# ---------------------------------------------------------------- the render (P6-P13)

SID = "d7204ad0-3af9-44c3-bae2-ef8887d59874"


@pytest.fixture
def wired(monkeypatch):
    """Drill-matrix harness (deepseek measure 1): construct the world, render, assert
    the line names the state we constructed. Defaults: in-session, daemon down,
    no consumer-seat holder; each pin overrides what it drills."""
    import agent_cli  # noqa: F401 -- import before patching its collaborators

    monkeypatch.setattr("core.comm.runner_lock.session_holder_token",
                        lambda: f"session:{SID}")
    monkeypatch.setattr("core.comm.runner_lock.holder", lambda agent: None)
    monkeypatch.setattr("core.comm.daemon_state.daemon_is_live",
                        lambda agent, **kw: False)
    monkeypatch.setattr("core.comm.wake_seat.watcher_state",
                        lambda agent, sid, **kw: ("unarmed", None))
    return monkeypatch


def _line():
    import agent_cli
    return agent_cli._boot_you_line("claude")


def test_p6_no_session_no_line(wired):
    """A6: a caller with no session identity gets no YOU line -- nothing
    session-scoped to claim."""
    wired.setattr("core.comm.runner_lock.session_holder_token", lambda: "")
    assert _line() == ""


def test_p7_armed_renders_wakeable_with_pid(wired):
    """A2 amended by F1/F3: claim 'armed' with the pid visible -- armed is the honest
    floor, never 'reachable'."""
    wired.setattr("core.comm.wake_seat.watcher_state",
                  lambda agent, sid, **kw: ("armed", 4242))
    line = _line()
    assert line.startswith("# YOU: wakeable")
    assert "4242" in line
    assert "NOT WAKEABLE" not in line


def test_p8_dead_seat_names_the_death_and_the_remedy(wired):
    """D1: the watcher DIED (stale seat) -- say so, distinctly from never-armed,
    with a copy-runnable re-arm command carrying THIS session id."""
    wired.setattr("core.comm.wake_seat.watcher_state",
                  lambda agent, sid, **kw: ("dead-seat", 4242))
    line = _line()
    assert "NOT WAKEABLE" in line
    assert "DIED" in line.upper()
    assert f"--session {SID}" in line
    assert "bifrost_wake.py" in line


def test_p9_never_armed_renders_arm_command(wired):
    """A3: never armed, daemon down -> NOT WAKEABLE + the arm command with the sid."""
    line = _line()   # wired default: unarmed, daemon down
    assert "NOT WAKEABLE" in line
    assert "DIED" not in line.upper()
    assert f"--session {SID}" in line
    assert "BIFROST_WAKE_LANE=work" in line


def test_p10_unknown_claims_neither_direction(wired):
    """A4: cannot-tell renders UNKNOWN -- the line contains neither the affirmative
    'wakeable (' claim nor 'NOT WAKEABLE'."""
    wired.setattr("core.comm.wake_seat.watcher_state",
                  lambda agent, sid, **kw: ("unknown", None))
    line = _line()
    assert "UNKNOWN" in line
    assert "NOT WAKEABLE" not in line
    assert "wakeable (" not in line

    # and an exploding probe is the same answer, never a broken boot (fail-open render)
    def boom(agent, sid, **kw):
        raise RuntimeError("probe exploded")
    wired.setattr("core.comm.wake_seat.watcher_state", boom)
    line2 = _line()
    assert "UNKNOWN" in line2


def test_p11_daemon_first_and_twin_holder_named(wired):
    """D2 + F2: daemon-live wins without consulting the seat (daemon-first), and a
    LIVE TWIN holding the consumer seat is named -- daemon-live must not render a
    bare self-claim for the non-holder session (the S3b shape)."""
    wired.setattr("core.comm.daemon_state.daemon_is_live", lambda agent, **kw: True)

    def never(agent, sid, **kw):
        raise AssertionError("daemon-first: the seat probe must not run")
    wired.setattr("core.comm.wake_seat.watcher_state", never)

    line = _line()
    assert "wakeable" in line and "daemon" in line

    twin = "05fe0639-aaaa-bbbb-cccc-ddddeeeeffff"
    wired.setattr("core.comm.runner_lock.holder",
                  lambda agent: {"token": f"session:{twin}"})
    line2 = _line()
    assert twin[:8] in line2
    assert "twin" in line2.lower()


def test_p12_render_writes_nothing(wired, tmp_path, monkeypatch):
    """A5 dynamic (deepseek measure 3): render every state with tempdir redirected --
    the filesystem diff is EMPTY. No .rearm, no .daemon_nag, no .alive, no .pid."""
    import tempfile
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    for state in (("armed", 4242), ("dead-seat", 4242), ("unarmed", None),
                  ("unknown", None)):
        wired.setattr("core.comm.wake_seat.watcher_state",
                      lambda agent, sid, _s=state, **kw: _s)
        _line()
    wired.setattr("core.comm.daemon_state.daemon_is_live", lambda agent, **kw: True)
    _line()
    assert os.listdir(tmp_path) == []


def test_p13_render_calls_no_writer_static():
    """A5 structural (deepseek's static assert, via ast per the L7 lesson): the
    render helper's call graph names no writer. Comments/docstrings can say what
    they like; calls cannot."""
    import agent_cli
    import inspect
    src = textwrap.dedent(inspect.getsource(agent_cli._boot_you_line))
    calls = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            f = node.func
            calls.add(f.attr if isinstance(f, ast.Attribute) else
                      getattr(f, "id", ""))
    forbidden = {"write_rearm_trigger", "consume_rearms", "touch_activity",
                 "refresh_consumer", "refresh_card", "Popen", "run", "spawn",
                 "remove", "unlink", "write", "open"}
    assert not (calls & forbidden), f"writer calls in render path: {calls & forbidden}"
