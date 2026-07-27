"""PRE-REGISTERED ACCEPTANCE -- wiring evidence includes SHELL invocation, not just imports.

MEASURED 2026-07-27. check_wiring.py reports:

    FAIL: 'core/comm/door_probe.py' exists but is NOT reachable from any production entry
    point (built != wired) -> wire it, delete it, or add to EXCEPTIONS with a reason

door_probe.py IS wired. scripts/githooks/pre-push line 29 runs it as the FIRST blocking step
of the only mandatory door in the repo:

    if ! py -m core.comm.door_probe; then

check_wiring BFSes the IMPORT graph from production entry points, so a `python -m` invocation
from a shell hook is invisible to it. The module is not merely wired -- it is wired to the
strictest gate we own -- and the guard calls it dead.

WHY A FALSE POSITIVE HERE IS EXPENSIVE, and not cosmetic. The remedy the message offers is
"add to EXCEPTIONS with a reason". Every false positive therefore pushes a real, load-bearing
module onto the permanent exemption list, and each entry is a hole the guard will never look
through again. A guard that cries wolf gets fed exceptions until it guards nothing. That is the
same decay as an inherited-failure list that only grows, one layer down.

THIS ALSO EXPLAINS THE ACCUMULATION. check_wiring is correct and blocking (it exits 1 -- an
earlier reading of exit 0 was `tail`'s status through a pipe, not the checker's). It rides
ship.py, and ship.py was impassable until this morning, so the guard has not run in the window
where three unwired modules appeared. Unblocking the ship door is what brought this guard back
to life; its first live run is what produced this finding.

  P1  a module invoked as `py -m pkg.mod` from a tracked shell hook counts as WIRED
  P2  a script invoked by path from a hook or CI counts as WIRED
  P3  a genuinely unreferenced module is still FAIL -- the guard is not weakened
  P4  the shell scan is a fail-open READ: an unreadable hook never crashes the guard

Run: py -m pytest tests/test_wiring_sees_shell_invocations.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts", "checkers"))


def _refs(tmp_path, text, name="pre-push"):
    d = tmp_path / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    import check_wiring
    return check_wiring.shell_invoked_modules([str(d)])


def test_p1_dash_m_invocation_counts_as_wired(tmp_path):
    got = _refs(tmp_path, "#!/bin/sh\nif ! py -m core.comm.door_probe; then\n exit 1\nfi\n")
    assert "core/comm/door_probe.py" in got, (
        "a module run as `py -m` from the repo's only mandatory gate reads as dead -- and the "
        "offered remedy is an EXCEPTIONS entry, which would hole the guard permanently")


def test_p2_script_path_invocation_counts_as_wired(tmp_path):
    got = _refs(tmp_path, "py scripts/repair_learning_index.py --check\n")
    assert "scripts/repair_learning_index.py" in got


def test_p3_the_guard_is_not_weakened(tmp_path):
    """A module nothing references must still FAIL. Fixing a false positive must never
    become a way to stop the guard failing at all."""
    got = _refs(tmp_path, "echo hello\npy -m core.comm.door_probe\n")
    assert "core/foundation/migrate_to_sqlite.py" not in got
    assert len(got) == 1


def test_p4_an_unreadable_hook_never_crashes_the_guard(tmp_path):
    import check_wiring
    assert check_wiring.shell_invoked_modules([str(tmp_path / "nope")]) == set()
