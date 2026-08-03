"""PRE-REGISTERED ACCEPTANCE (T134b) -- `__main__` in a LIBRARY is a stub, not an entry point.

MEASURED 2026-08-03, found while extending this same gate. check_wiring reports:

    WARN: 'core/state/session_recovery.py' is in EXCEPTIONS but is now wired (or gone)
          -> remove the stale entry

It is not wired, and it did not become wired. Traced:

    import BFS reachable      : NO   (no module imports it)
    shell/CI invoked          : NO
    self_invoking(__main__)   : YES  <- the ONLY thing calling it wired

and the whole of that `__main__` block is:

    if __name__ == '__main__':
        recovery = main()

while the module's own docstring gives its usage as `from core.state.session_recovery import
SessionRecovery`, and core/state/__init__.py:21 re-exports it. It is a library with a convenience
runner attached. Its EXCEPTIONS entry, written 2026-07-07, still says "Still unwired (exported by
__init__, no live consumer) -- wire when a session-history consumer lands, or retire then". That
entry is still correct. NOTHING ABOUT THE MODULE CHANGED; the GATE changed on 2026-08-01 and
silently reclassified it.

WHY THIS DIRECTION IS THE DANGEROUS ONE. self_invoking_modules was added to fix false POSITIVES --
migrations and replay harnesses have no caller to find, and reporting them dead pushed live tools
onto a permanent exemption list. That was right. But the heuristic it used ("declares a __main__
guard") also absolves any library carrying a demo stub, and THAT failure is silent: the gate simply
stops asking. A guard that cries wolf gets fed exceptions; a guard that goes quiet gets believed.
Worse, the stale-entry WARN then invites someone to delete a still-accurate exception, which would
hide the module for good.

THE DISCRIMINATOR, checked against the three modules the rule was written for:

    core/foundation/durable_reconcile.py   re-exported: NO    <- genuine self-invoking tool
    core/foundation/migrate_to_sqlite.py   re-exported: NO    <- genuine
    core/recall/pack_replay.py             re-exported: NO    <- genuine
    core/state/session_recovery.py         re-exported: YES   <- library with a stub

A module its own package re-exports is part of an API surface: it is imported BY NAME through the
package, so if it were live the import graph would already show it. 4 of 4.

  S1  a __main__ module its package RE-EXPORTS is NOT self-invoking
  S2  a __main__ module its package does not re-export IS self-invoking   (no regression)
  S3  no __main__ guard is never self-invoking, re-exported or not
  S4  an unreadable/absent __init__.py fails OPEN -- the guard never crashes on a bad read

Run: py -m pytest tests/test_t134_self_invoking_is_not_a_library.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402

MAIN_STUB = "def main():\n    return 1\n\nif __name__ == '__main__':\n    r = main()\n"


def _pkg(tmp_path, pkg, mod, body, init=None):
    d = tmp_path / "core" / pkg
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{mod}.py").write_text(body, encoding="utf-8")
    if init is not None:
        (d / "__init__.py").write_text(init, encoding="utf-8")
    return f"core/{pkg}/{mod}.py"


def test_s1_a_reexported_main_module_is_a_library_not_an_entry_point(tmp_path):
    rel = _pkg(tmp_path, "state", "session_recovery", MAIN_STUB,
               init="from .session_recovery import SessionRecovery\n\n"
                    "__all__ = ['SessionRecovery']\n")
    got = check_wiring.self_invoking_modules({rel}, root=str(tmp_path))
    assert rel not in got, (
        "a library whose package re-exports it was absolved by its own demo stub -- the gate "
        "stopped asking about a module that never became wired")


def test_s2_a_genuine_self_invoking_tool_still_counts(tmp_path):
    """durable_reconcile / migrate_to_sqlite / pack_replay must not regress. Fixing a silent
    false negative must not re-open the loud false positive the rule was built to close."""
    rel = _pkg(tmp_path, "foundation", "durable_reconcile",
               "import argparse\n" + MAIN_STUB, init="# no re-exports\n")
    assert rel in check_wiring.self_invoking_modules({rel}, root=str(tmp_path))


def test_s3_no_main_guard_is_never_self_invoking(tmp_path):
    plain = _pkg(tmp_path, "util", "helpers", "def helper():\n    return 1\n",
                 init="from .helpers import helper\n")
    assert check_wiring.self_invoking_modules({plain}, root=str(tmp_path)) == set()


def test_s4_an_absent_init_fails_open(tmp_path):
    """No __init__.py at all: nothing can be re-exporting it, so the module keeps its
    self-invoking claim. The guard must never crash on a read it cannot make."""
    rel = _pkg(tmp_path, "loose", "tool", MAIN_STUB, init=None)
    assert rel in check_wiring.self_invoking_modules({rel}, root=str(tmp_path))
