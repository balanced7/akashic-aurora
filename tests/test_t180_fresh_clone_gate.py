"""T180 pin (committed RED before the implementation, per M3): the fresh-clone gate.

THE WOUND THIS PINS (task T180, found 2026-08-05, drilled 2026-09-02)
---------------------------------------------------------------------
core/comm/room_feed.py sat UNTRACKED while tracked scripts/bifrost_ui.py imported it.
On any fresh clone: 3 collection errors -> pytest INTERRUPTS -> the suite runs ZERO
tests -> a naive pipeline reads the empty failure list as SUCCESS. The failure mode
is a false PASS, and it is invisible from the working tree by construction: the tree
has the file, only the repo doesn't. By 2026-09-02 the named file had healed by
drift (someone tracked it, task untouched), which is exactly why the deliverable is
a GATE, not a fix: the class regenerated three times in one day when first found.

THE MEANING THE GATE MUST ENCODE (not a membership list)
--------------------------------------------------------
1. "The working tree is not the repo": no TRACKED file may import a module whose
   resolved file exists on disk but is untracked -- works-here-breaks-there.
2. "Empty is never success": zero tests collected is a FAILURE no matter what the
   exit code says. Collection errors are failures even when the count looks healthy.

Contract pinned here:
  scripts/check_fresh_clone.py
    scan_static(root) -> list of violations, each naming (importer, module, resolved
        untracked file); [] means clean.
    clone_verdict(returncode, collected, errors, floor) -> {"ok": bool,
        "reasons": [str, ...]} -- a pure judgment, testable without cloning.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.check_fresh_clone import clone_verdict, scan_static  # noqa: E402


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.email=pin@t180", "-c", "user.name=t180-pin", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )


def _make_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    return root


def test_static_scan_flags_tracked_import_of_untracked_module(tmp_path):
    """The T180 shape exactly: tracked app.py imports helper present-but-untracked."""
    root = _make_repo(tmp_path)
    (root / "app.py").write_text("import helper_util\n", encoding="utf-8")
    (root / "helper_util.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "app.py")
    _git(root, "commit", "--quiet", "-m", "track app only")

    violations = scan_static(str(root))

    assert violations, "tracked->untracked import must be flagged, not silent"
    rendered = " ".join(str(v) for v in violations)
    assert "app.py" in rendered and "helper_util" in rendered, (
        "a violation must NAME the importer and the stranded module -- "
        "a loud gate that doesn't say where is only half loud"
    )


def test_static_scan_clean_once_module_is_tracked(tmp_path):
    root = _make_repo(tmp_path)
    (root / "app.py").write_text("import helper_util\n", encoding="utf-8")
    (root / "helper_util.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "app.py", "helper_util.py")
    _git(root, "commit", "--quiet", "-m", "track both")

    assert scan_static(str(root)) == []


def test_static_scan_ignores_third_party_and_stdlib(tmp_path):
    """Only repo-local, present-on-disk, untracked resolutions are violations."""
    root = _make_repo(tmp_path)
    (root / "app.py").write_text("import json\nimport requests\n", encoding="utf-8")
    _git(root, "add", "app.py")
    _git(root, "commit", "--quiet", "-m", "stdlib and 3p only")

    assert scan_static(str(root)) == []


def test_zero_collected_is_failure_even_with_exit_zero():
    """The poison itself: an empty suite must NEVER read as success."""
    v = clone_verdict(returncode=0, collected=0, errors=0, floor=100)
    assert v["ok"] is False
    assert any("zero" in r.lower() or "empty" in r.lower() for r in v["reasons"])


def test_no_tests_exit_code_is_failure():
    """pytest exit 5 (no tests collected) is the same poison wearing a number."""
    v = clone_verdict(returncode=5, collected=0, errors=0, floor=100)
    assert v["ok"] is False


def test_collection_errors_fail_even_when_count_clears_the_floor():
    v = clone_verdict(returncode=2, collected=5000, errors=1, floor=100)
    assert v["ok"] is False


def test_below_floor_is_failure_and_names_the_floor():
    v = clone_verdict(returncode=0, collected=50, errors=0, floor=100)
    assert v["ok"] is False
    assert any("floor" in r.lower() or "100" in r for r in v["reasons"])


def test_healthy_collection_passes():
    v = clone_verdict(returncode=0, collected=4954, errors=0, floor=4900)
    assert v["ok"] is True
    assert v["reasons"] == []
