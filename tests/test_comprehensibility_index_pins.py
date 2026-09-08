"""RED pins (M3): the comprehensibility guard asks the INDEX, not the working tree -- and can
ask git about more than one path at a time on Windows.

Defers a3d09c4e5d + af5759c5a2. Three stacked defects, one class ("asks the box, not the repo"):

  1. check_comprehensibility._missing_refs() skipped a reference iff os.path.exists(ROOT/ref).
     "Exists on this box" is not "is in the repository": a present-but-UNTRACKED target passed
     on the workstation and broke for every clone (docs/CODEX_INTEGRATION.md ->
     tests/test_codex_hook_contract.py; docs/MAP.md -> tests/test_t084_intent_shadow.py), and a
     GITIGNORED one (security/acl.json, eleven references) never reached the instance-local
     WARN route locally because here it was never "missing". The guard could not see its own
     blind spot: main tree `--fast` PASS, pristine worktree of the SAME commit 13 drift FAILs.

  2. check_comprehensibility._gitignored() fed `git check-ignore --stdin` through a TEXT-mode
     pipe. CPython rewrites '\\n' as os.linesep on that pipe -- '\\r\\n' on Windows -- so every
     ref except the LAST sorted one reached git as 'path\\r' and matched nothing. The excuse
     path therefore failed closed whenever two or more refs were missing, i.e. in every clean
     checkout on this box (the 11 false acl.json FAILs), while the single-ref pin in
     tests/test_ci_instance_local_refs_pins.py stayed green by accident.

  3. gen_master_map._name_index() built the pin/paper columns from os.listdir, so an untracked
     test on one box was rendered into the COMMITTED map (the second untracked target above).
     The module column had already moved to the index (tests/test_derived_docs_ignore_untracked.py);
     the two name-matched columns had not.

A guard that disagrees with itself across machines is the defect; these pins state the law:
the verdict is a function of the index (tracked + staged), identical on every machine.
Pins 2a/2b are Windows-only RED (the newline translation does not happen on POSIX).

Run: py -m pytest tests/test_comprehensibility_index_pins.py -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "checkers"))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "generators"))

import check_comprehensibility as cm  # noqa: E402
import gen_master_map as mapgen  # noqa: E402
import _tracked  # noqa: E402


# ------------------------------------------------ 2. git can be asked about MANY paths at once
def test_gitignored_recognises_the_acl_when_it_is_not_the_last_ref():
    """Two refs, the ignored one sorting FIRST -- the case the single-ref pin cannot see.
    (2a, Windows-only RED: text-mode stdin turns the separator into CRLF, and the first path
    carries a stray '\\r' into git, which then matches nothing.)"""
    got = cm._gitignored({"security/acl.json", "tests/zz_never_exists.py"})
    assert "security/acl.json" in got, (
        f"a gitignored ref must be recognised regardless of how many refs travel with it; got {got!r}")


def test_gitignored_answers_the_real_clean_checkout_shape():
    """(2b) A clone's actual shape: one ignored path cited from many sources plus a few genuinely
    missing ones -- exactly one answer, the ignored path, never the empty set."""
    refs = {"security/acl.json"} | {f"tests/zz_missing_{i}.py" for i in range(12)}
    assert cm._gitignored(refs) == {"security/acl.json"}


# ------------------------------------------------ 1. the index, not the filesystem
@pytest.fixture()
def throwaway_repo(tmp_path):
    """A real git repo holding ONE committed living doc that cites two paths, plus one tracked
    test. After the commit both cited targets are made to EXIST on disk: one UNTRACKED, one
    GITIGNORED. Both resolve on the filesystem; neither is in the index."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        r = subprocess.run(["git", "-c", "user.name=pin", "-c", "user.email=pin@example.invalid",
                            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
                           cwd=str(repo), capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            pytest.skip(f"git {' '.join(args)} failed here: {(r.stderr or r.stdout)[:200]}")
        return r

    git("init", "-q")
    for d in ("docs", "core", "tests", "security"):
        (repo / d).mkdir()
    (repo / ".gitignore").write_text("security/acl.json\n", encoding="utf-8")
    (repo / "docs" / "PLANTED.md").write_text(
        "Pins: run `tests/planted_probe.py`; grants live in security/acl.json.\n",
        encoding="utf-8")
    (repo / "tests" / "test_tracked_probe.py").write_text("# committed\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "--no-verify", "-m", "pin: one living doc, two references")
    # The condition under which the old guard said PASS: both targets exist on THIS box.
    (repo / "tests" / "planted_probe.py").write_text("# present, never added\n", encoding="utf-8")
    (repo / "security" / "acl.json").write_text("{}\n", encoding="utf-8")
    return str(repo)


def test_untracked_target_is_drift_and_gitignored_target_is_instance_local(throwaway_repo,
                                                                          monkeypatch):
    """(1a) Same repo, two references, two different answers -- neither of them PASS.
    The untracked one is drift (a clone cannot follow it, and nothing declared it absent);
    the gitignored one is absent BY DESIGN: excused from FAIL, still named as a WARN."""
    monkeypatch.setattr(cm, "ROOT", throwaway_repo)
    monkeypatch.setattr(cm, "REF_ALLOWLIST", {})
    fails = cm._stale_refs()
    warns = cm._instance_local_refs()
    assert any("tests/planted_probe.py" in f for f in fails), (
        f"an UNTRACKED target exists on this box and nowhere else -- that is drift; "
        f"got fails={fails}")
    assert not any("security/acl.json" in f for f in fails), (
        f"a GITIGNORED target is absent by design, not drift; got fails={fails}")
    assert any("security/acl.json" in w for w in warns), (
        f"...and it must stay visible as an instance-local WARN; got warns={warns}")


def test_guard_fails_loud_when_the_index_cannot_be_read(tmp_path, monkeypatch):
    """(1b) Outside any repository the ref check must be a broken-check FAIL, never an empty
    'all clear'. A guard that cannot see the index has no verdict to give."""
    norepo = tmp_path / "norepo"
    for d in ("docs", "core"):
        (norepo / d).mkdir(parents=True)
    # git must not discover some repo above tmp_path on this box.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setattr(cm, "ROOT", str(norepo))
    monkeypatch.setattr(cm, "REF_ALLOWLIST", {})
    got, crash = cm._run("F stale-refs", cm._stale_refs)
    assert crash is not None and "CRASHED" in crash, (
        f"no index -> no verdict: expected a loud broken-check FAIL, got got={got} crash={crash}")


# ------------------------------------------------ 3. the map's name-matched columns, same law
def test_map_name_index_reads_the_index_not_the_directory(throwaway_repo, monkeypatch):
    """An untracked tests/*.py on this box must never become the committed map's pin column;
    a tracked one must. (The module column already obeys this via _tracked.tracked_py.)"""
    monkeypatch.setattr(mapgen, "ROOT", throwaway_repo)
    monkeypatch.setattr(_tracked, "ROOT", throwaway_repo)
    _tracked._tracked_paths.cache_clear()
    try:
        got = mapgen._name_index(["tests"], (".py",))
    finally:
        _tracked._tracked_paths.cache_clear()
    assert got == [("tests/test_tracked_probe.py", "test_tracked_probe.py")], (
        f"the pin column must describe the repository, not the box; got {got}")
