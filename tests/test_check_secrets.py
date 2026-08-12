"""The secret gate: nothing credential-shaped reaches a public repo.

WHY, measured 2026-08-11 before a line was written: this repository is PUBLIC, several
agent seats hold commit access, and `.secrets/API Keys/` sits one gitignore rule away from
the tree. A full scan came back clean -- 2,551 tracked files, and 8,286 blobs across all
2,778 commits of history, zero credential-shaped hits. Nothing has ever leaked. This gate
exists to keep a clean result clean, which is the only time it is cheap to install one.

THE PIN THAT MATTERS MOST IS P2, AND IT IS NOT THE OBVIOUS ONE.

A secret scanner that PRINTS what it found has leaked it a second time -- into the CI log,
into the terminal scrollback, and in this house into the session transcript, which is now
archived to two drives and re-ingested into a queryable index within the hour. The finder
becomes the leak. So every report is MASKED at the source: the scanner never emits more
than a prefix and a suffix, and P2 asserts the full match is absent from its own output.

The allowlist takes a REASON per entry, not a bare path. An unexplained suppression is
indistinguishable from a missed detection six months later, and this repo already has one
legitimate hit -- a deliberate canary string in the wire-journal test that proves prompt
content is NOT recorded. That entry stays visible, with its reason attached.

Run: py -m pytest tests/test_check_secrets.py -q
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.checkers import check_secrets as CS  # noqa: E402

# Synthetic, never-valid credentials. Shaped to match, deliberately not real.
FAKE_OPENAI = "sk-" + "A1b2C3d4E5f6G7h8J9k0L1m2N3o4P5q6R7s8T9u0"
FAKE_AWS = "AKIA" + "IOSFODNN7EXAMPLE"[:16]
FAKE_GH = "ghp_" + "0123456789abcdefghijABCDEFGHIJ0123456789"[:36]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True).stdout


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.t")
    _git(r, "config", "user.name", "t")
    (r / "clean.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "init")
    return r


# ---------------------------------------------------------------- P1: it catches one
def test_p1_a_planted_credential_in_a_tracked_file_is_caught(repo):
    (repo / "leak.py").write_text(f'KEY = "{FAKE_OPENAI}"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "oops")

    rep = CS.scan_tracked(repo)
    assert rep["findings"], "a live-shaped key sat in a tracked file and was not seen"
    assert any("leak.py" in f["file"] for f in rep["findings"])
    assert rep["ok"] is False


# ---------------------------------------------------------------- P2: THE finder is not the leak
def test_p2_the_report_never_contains_the_secret_itself(repo, capsys):
    """A scanner that prints its finding leaks it into the CI log, the scrollback, and --
    here -- the session transcript, which is archived to two drives and indexed within the
    hour. Masking is not cosmetic; it is the difference between a guard and a second leak."""
    (repo / "leak.py").write_text(f'KEY = "{FAKE_OPENAI}"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "oops")

    rep = CS.scan_tracked(repo)
    blob = repr(rep)
    assert FAKE_OPENAI not in blob, "THE FULL SECRET IS IN THE REPORT OBJECT"
    assert FAKE_OPENAI[8:-8] not in blob, "the distinctive middle leaked"

    CS.render(rep)
    printed = capsys.readouterr().out
    assert FAKE_OPENAI not in printed, "THE FULL SECRET WAS PRINTED TO STDOUT"
    assert "sk-" in printed, "...but the operator can still tell WHAT kind of thing it is"


# ---------------------------------------------------------------- P3: clean is clean
def test_p3_a_clean_tree_passes_quietly(repo):
    rep = CS.scan_tracked(repo)
    assert rep["findings"] == [] and rep["ok"] is True
    assert rep["scanned"] >= 1, "it must state how many files it looked at"


# ---------------------------------------------------------------- P4: allowlist needs a why
def test_p4_an_allowlist_entry_carries_its_reason(repo):
    (repo / "canary.py").write_text(f'FAKE = "{FAKE_AWS}"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "canary")

    allow = {"canary.py": "deliberate non-credential fixture proving X is not recorded"}
    rep = CS.scan_tracked(repo, allowlist=allow)
    assert rep["ok"] is True
    assert rep["allowed"] == 1, "a suppression is COUNTED, never silent"
    assert rep["allowlist_reasons"][0], "and it carries the reason forward into the report"

    with pytest.raises(ValueError):
        CS.scan_tracked(repo, allowlist={"canary.py": ""})   # bare path, no reason


# ---------------------------------------------------------------- P5: deletion does not help
def test_p5_history_mode_finds_a_secret_in_a_DELETED_file(repo):
    """The whole reason a working-tree scan is not enough: on a public repo, `git rm`
    removes the file from HEAD and leaves the blob reachable forever."""
    (repo / "oops.py").write_text(f'K = "{FAKE_GH}"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add")
    _git(repo, "rm", "-q", "oops.py")
    _git(repo, "commit", "-qm", "remove it, surely that is fine")

    assert CS.scan_tracked(repo)["ok"] is True, "gone from the working tree..."
    hist = CS.scan_history(repo)
    assert hist["ok"] is False, "...and still in history, which is what the public sees"
    assert hist["findings"], "history mode found nothing in a repo that contains one"
    assert FAKE_GH not in repr(hist), "masked here too"


# ---------------------------------------------------------------- P6: CI sees exit codes
def test_p6_exit_code_is_the_contract(repo):
    assert CS.main(["--root", str(repo)]) == 0
    (repo / "leak.py").write_text(f'K = "{FAKE_OPENAI}"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "x")
    assert CS.main(["--root", str(repo)]) != 0, "a gate that finds and exits 0 is decorative"


# ---------------------------------------------------------------- P7: the live repo
def test_p7_this_repository_is_currently_clean():
    """Not a unit test -- a standing assertion about the real tree. If this ever fails,
    read the masked output and rotate the key BEFORE fixing the test."""
    root = Path(__file__).resolve().parents[1]
    rep = CS.scan_tracked(root, allowlist=CS.DEFAULT_ALLOWLIST)
    assert rep["ok"] is True, f"unallowlisted credential-shaped content: {rep['findings']}"


# ---------------------------------------------------------------- P8: built != wired
def test_p8_the_pre_push_gate_actually_runs_this_scanner():
    """This repo's own history is the argument. repair_learning_index.py shipped a --check
    flag explicitly 'to wire into ship gates' and was wired to nothing; the index sat at 16
    of 464 lessons for two days with 96% of the corpus invisible to recall, and every
    by-name spot-check passed the whole time. A detector no gate runs is decoration.

    Asserts the hook INVOKES the scanner, not merely that both files exist."""
    hook = (Path(__file__).resolve().parents[1] / "scripts" / "githooks" / "pre-push")
    body = hook.read_text(encoding="utf-8", errors="replace")
    assert "check_secrets.py" in body, "the pre-push gate does not run the secret scanner"
    assert "if ! py scripts/checkers/check_secrets.py" in body, (
        "present but not GATING -- it must block the push, not merely be mentioned")
    assert "exit 1" in body.split("check_secrets.py", 1)[1][:600], (
        "the scanner runs but its failure does not stop the push")
