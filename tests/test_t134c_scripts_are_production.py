"""PRE-REGISTERED ACCEPTANCE (T134c) -- scripts/ is a production call path.

MEASURED 2026-08-03 by sampling 22 entries from the function backlog the T134 gate had just
produced, to get a false-positive RATE rather than assume one. 21 of 22 held up. One did not:

    core/comm/session_state.py::list_snapshots   reported: no production caller
    scripts/snapshot.py:7   from core.comm.session_state import save, list_snapshots
    scripts/snapshot.py:21  snaps = list_snapshots()

snapshot.py is a real tool -- its docstring is "Snapshot the current Bifrost session for later
resume. Run before shutting down." It carries no `if __name__ == "__main__":` guard because it does
not need one: `py scripts/snapshot.py` runs the module body. So neither the import BFS (nothing
imports it) nor self_invoking_modules (no guard to read) could see it, and a live backup door's
only caller was invisible.

THE GAP WAS 29 OF 47. Counting only scripts reachable by import left these unseen, among others:

    scripts/mirror.py       the commit+push door
    scripts/ship.py         the ship door
    scripts/snapshot.py     the backup door
    scripts/bifrost_daemon.py, scripts/arc_scorecard.py, scripts/run_job.py, ...

A call from ANY of those read as "no caller". Six functions were rescued by fixing it --
build_runtimes, consume_rearms, sweep_stale_markers, list_snapshots, by_status, assignment -- a
false-positive rate of 6/117, about 5%.

WHY THIS PARTICULAR FALSE POSITIVE IS THE WORST KIND. snapshot.py's own source carries this
comment: the sys.path fix was made because "this backup door was dead on every invocation (found
2026-07-31, mid-shutdown, which is precisely when a backup tool fails)". The corpus already holds
`backup_door_never_ran` on the same file. A gate that tells you the backup door's function is dead
code, four days after someone proved the backup door matters, is worse than no gate.

THE RULE: scripts/ is the tools directory. Every file in it is either run by a human or imported by
one that is; the import graph cannot tell which, and guessing wrong costs a false positive on live
code. So the whole directory counts as production for reference-gathering. This can only ever ADD
evidence of wiring -- it never hides a dead function, because a function nothing anywhere names is
still reported.

  G1  a call from a script counts as wiring
  G2  a script with NO __main__ guard still counts        (snapshot.py has none)
  G3  the gate is not weakened -- an unreferenced function is still reported
  G4  every scripts/*.py is in the production set          (no reachability filter survives)

Run: py -m pytest tests/test_t134c_scripts_are_production.py -q
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402


def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return rel.replace(os.sep, "/")


def test_g1_a_call_from_a_script_counts_as_wiring(tmp_path):
    lib = _write(tmp_path, "core/comm/session_state.py",
                 "def save(x):\n    return x\n\ndef list_snapshots():\n    return []\n")
    tool = _write(tmp_path, "scripts/snapshot.py",
                  "from core.comm.session_state import save, list_snapshots\n"
                  "snaps = list_snapshots()\n")
    got = {n for _m, n, _l in
           check_wiring.unwired_functions([lib], [tool, lib], root=str(tmp_path))}
    assert "list_snapshots" not in got, (
        "a live backup door's only caller was invisible to the gate")


def test_g2_a_script_without_a_main_guard_still_counts(tmp_path):
    """snapshot.py has no __main__ guard -- `py scripts/x.py` runs the module body. A rule that
    only recognised guarded scripts would still have missed it."""
    lib = _write(tmp_path, "core/comm/session_state.py", "def list_snapshots():\n    return []\n")
    tool = _write(tmp_path, "scripts/snapshot.py",
                  '"""Run before shutting down."""\n'
                  "from core.comm.session_state import list_snapshots\n"
                  "print(list_snapshots())\n")
    assert "__main__" not in (tmp_path / "scripts/snapshot.py").read_text(encoding="utf-8")
    got = {n for _m, n, _l in
           check_wiring.unwired_functions([lib], [tool, lib], root=str(tmp_path))}
    assert "list_snapshots" not in got


def test_g3_the_gate_is_not_weakened(tmp_path):
    """Widening the production set must not become a way to stop reporting anything. A function
    nothing anywhere names is still dead."""
    lib = _write(tmp_path, "core/comm/session_state.py",
                 "def list_snapshots():\n    return []\n\ndef never_called():\n    return 1\n")
    tool = _write(tmp_path, "scripts/snapshot.py",
                  "from core.comm.session_state import list_snapshots\nlist_snapshots()\n")
    got = {n for _m, n, _l in
           check_wiring.unwired_functions([lib], [tool, lib], root=str(tmp_path))}
    assert "never_called" in got
    assert "list_snapshots" not in got


def test_g4_every_script_is_in_the_production_set():
    """Against the REAL repo: no scripts/*.py may be excluded by reachability. Measured gap when
    this pin was written: 29 of 47 invisible, including mirror.py, ship.py and snapshot.py."""
    universe, reachable, _ = check_wiring.analyze()
    _cand, prod, _orph, _stale = check_wiring.function_level(reachable, universe)
    on_disk = {p.replace(os.sep, "/") for p in glob.glob("scripts/*.py", root_dir=ROOT)}
    missing = sorted(on_disk - set(prod))
    assert not missing, (
        f"{len(missing)} script(s) are not counted as production, so a call from any of them "
        f"reads as no-caller: {missing[:6]}")
