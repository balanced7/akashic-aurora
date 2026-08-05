"""PRE-REGISTERED ACCEPTANCE (T167) -- the wake-listener autopilot has never worked.

THE ROOT CAUSE of the recurring "session silently stops being wakeable", found by dropping a real
trigger during the T166 fire drill instead of reasoning about it:

    scripts/bifrost_daemon.py:140   def _spawn_listener(sid: str) -> bool:     # ONE argument
    scripts/bifrost_daemon.py:386   lambda sid: _spawn_listener(sid, bus.ns)   # TWO arguments

Every rearm trigger raises `TypeError: _spawn_listener() takes 1 positional argument but 2 were
given`, and core/comm/daemon_state.py:consume_rearms swallows it by contract --

    try:    ok = bool(spawn_fn(sid))
    except Exception:    ok = False        # "falsy/raising leaves it for the next tick"

-- so the trigger is left for a next tick that can never succeed. A daemon running
--manage-listener spawns NOTHING, forever, and says nothing.

REPRODUCED 2026-08-04, not inferred: daemon alive at pid 9572 with --manage-listener, a valid
.rearm written for session cdfb9126 via daemon_state.rearm_path, ZERO listeners after 134 seconds,
trigger still on disk. Wild corroboration: bifrost_wake_bob.rearm had been sitting unanswered
since 10:17 the same morning.

THE SECOND DEFECT IS THE ONE THAT MATTERS MORE. A one-line signature typo survived indefinitely
because the only consumer catches every exception and returns False. Fail-open is right here --
a bad spawn must not kill the daemon loop -- but SILENT fail-open turns a crash into a permanent,
invisible no-op. That is the same trap this session hit three times in guards of my own
(fail_open_plus_monkeypatched_pins_equals_invisible_noop). The repair is not "catch less"; it is
"say something when you catch".

  A1  the daemon's spawn callable is signature-compatible with consume_rearms  (the actual bug)
  A2  a successful spawn CLEARS the trigger
  A3  a failing spawn LEAVES the trigger                (fail-open contract preserved)
  A4  a RAISING spawn is reported, not silently swallowed
  A5  the daemon loop survives a raising spawn           (fail-open still fails open)

Run: py -m pytest tests/test_t167_rearm_autopilot_actually_spawns.py -q
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import daemon_state as DS  # noqa: E402

DAEMON = os.path.join(ROOT, "scripts", "bifrost_daemon.py")


def test_a1_the_daemon_spawn_callable_matches_the_definition():
    """THE BUG. Read the real file: the arity the lambda passes must match the def."""
    src = open(DAEMON, encoding="utf-8", errors="replace").read()
    d = re.search(r"def _spawn_listener\(([^)]*)\)", src)
    assert d, "no _spawn_listener definition found"
    params = [p for p in (x.strip() for x in d.group(1).split(",")) if p and p != "self"]
    required = [p for p in params if "=" not in p and not p.startswith("*")]
    call = re.search(r"_spawn_listener\((?!sid: str)([^)]*)\)", src[d.end():])
    assert call, "no _spawn_listener CALL site found"
    passed = [a for a in (x.strip() for x in call.group(1).split(",")) if a]
    assert len(passed) >= len(required) and len(passed) <= len(params), (
        f"the daemon calls _spawn_listener with {len(passed)} arg(s) but it accepts "
        f"{len(required)}..{len(params)} -- every rearm raises TypeError and is swallowed")


def test_a2_a_successful_spawn_clears_the_trigger(tmp_path):
    DS.write_rearm_trigger("claude", "sid12345", tmp=str(tmp_path))
    assert os.path.exists(DS.rearm_path("claude", "sid12345", tmp=str(tmp_path)))
    n = DS.consume_rearms("claude", lambda sid: True, tmp=str(tmp_path))
    assert n == 1
    assert not os.path.exists(DS.rearm_path("claude", "sid12345", tmp=str(tmp_path)))


def test_a3_a_failing_spawn_leaves_the_trigger(tmp_path):
    """The fail-open contract is CORRECT and must survive: a seat that could not be seated this
    tick should be retried next tick."""
    DS.write_rearm_trigger("claude", "sid67890", tmp=str(tmp_path))
    n = DS.consume_rearms("claude", lambda sid: False, tmp=str(tmp_path))
    assert n == 0
    assert os.path.exists(DS.rearm_path("claude", "sid67890", tmp=str(tmp_path)))


def test_a4_a_raising_spawn_is_reported_not_silently_swallowed(capsys, tmp_path):
    """The defect that let a one-line typo live forever. Catching is right; catching SILENTLY is
    how an autopilot spawns nothing for weeks while reporting nothing."""
    DS.write_rearm_trigger("claude", "sidraise0", tmp=str(tmp_path))

    def _boom(sid):
        raise TypeError("_spawn_listener() takes 1 positional argument but 2 were given")

    DS.consume_rearms("claude", _boom, tmp=str(tmp_path))
    said = capsys.readouterr()
    blob = (said.out or "") + (said.err or "")
    assert "TypeError" in blob or "rearm" in blob.lower(), (
        "a raising spawn produced NO output -- this is exactly how the wake autopilot stayed "
        "broken and silent")


def test_a5_the_loop_still_fails_open_on_a_raising_spawn(tmp_path):
    """Loudness must not become fragility: a raising spawn still must not propagate."""
    DS.write_rearm_trigger("claude", "sidraise1", tmp=str(tmp_path))

    def _boom(sid):
        raise RuntimeError("nope")

    n = DS.consume_rearms("claude", _boom, tmp=str(tmp_path))   # must not raise
    assert n == 0
    assert os.path.exists(DS.rearm_path("claude", "sidraise1", tmp=str(tmp_path)))
