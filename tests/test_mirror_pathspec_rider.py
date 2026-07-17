"""C2-4 pin: mirror.py named-path mode must NEVER commit another seat's pre-staged work.

The 2026-07-17 incident: claude ran `mirror.py "docs ..." docs/a.md docs/b.md` while the
fable-reconciler twin had two research drafts sitting staged in the SHARED git index; the
commit carried all four files. mirror's docstring promises named-path scoping (the FM1
lesson), but `git add -- <paths>` followed by a bare `git commit` commits the whole index.
Root fix: pathspec-limited `git commit -m msg -- <paths>`, leaving stranger staged entries
staged for their own author's commit.

Offline: runs against a copy of mirror.py inside a temp repo with a local bare origin, so
the push leg exercises for real without a network.
"""
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(cmd, cwd, ok=True):
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True)
    if ok:
        assert r.returncode == 0, f"{cmd} failed:\n{r.stdout}\n{r.stderr}"
    return r


def _committed_files(work):
    r = _run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], work)
    return sorted(r.stdout.split())


def _staged_files(work):
    r = _run(["git", "diff", "--cached", "--name-only"], work)
    return sorted(r.stdout.split())


@pytest.fixture()
def twin_repo(tmp_path):
    """A repo shared by two seats, with a local bare origin so mirror's push succeeds."""
    work = tmp_path / "work"
    work.mkdir()
    _run(["git", "init", "-q"], work)
    _run(["git", "config", "user.email", "pin@test"], work)
    _run(["git", "config", "user.name", "pin"], work)
    bare = tmp_path / "origin.git"
    _run(["git", "init", "-q", "--bare", bare], work)
    _run(["git", "remote", "add", "origin", bare], work)
    (work / "scripts").mkdir()
    shutil.copy(os.path.join(REPO, "scripts", "mirror.py"), work / "scripts" / "mirror.py")
    (work / "seed.txt").write_text("seed\n")
    _run(["git", "add", "-A"], work)
    _run(["git", "commit", "-q", "-m", "seed"], work)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], work).stdout.strip()
    _run(["git", "push", "-q", "-u", "origin", branch], work)
    return work


def _mirror(work, *args):
    return subprocess.run([sys.executable, "scripts/mirror.py", *args],
                          cwd=str(work), capture_output=True, text=True)


def test_named_path_commit_excludes_strangers_staged_files(twin_repo):
    """THE C2-4 PIN: a rider staged by the other seat stays out of my named-path commit."""
    work = twin_repo
    (work / "rider.txt").write_text("the twin's staged draft\n")
    _run(["git", "add", "rider.txt"], work)          # the other seat pre-stages
    (work / "mine.txt").write_text("my doc\n")

    r = _mirror(work, "docs: mine only", "mine.txt")
    assert r.returncode == 0, f"mirror failed:\n{r.stdout}\n{r.stderr}"

    assert _committed_files(work) == ["mine.txt"], (
        f"named-path commit carried a stranger's staged file: {_committed_files(work)}")
    assert "rider.txt" in _staged_files(work), (
        "the twin's staged entry must SURVIVE staged for the twin's own commit")
    # the printed receipt must match what was actually committed
    assert "committed 1 file(s)" in r.stdout, r.stdout


def test_staged_only_mode_still_commits_the_index(twin_repo):
    """Regression: no-path mode keeps its contract (commit exactly what is staged)."""
    work = twin_repo
    (work / "a.txt").write_text("a\n")
    (work / "b.txt").write_text("b\n")
    _run(["git", "add", "a.txt", "b.txt"], work)

    r = _mirror(work, "staged pair")
    assert r.returncode == 0, f"mirror failed:\n{r.stdout}\n{r.stderr}"
    assert _committed_files(work) == ["a.txt", "b.txt"]


def test_all_mode_still_sweeps_the_tree(twin_repo):
    """Regression: --all keeps its explicit opt-in blanket sweep."""
    work = twin_repo
    (work / "x.txt").write_text("x\n")
    (work / "seed.txt").write_text("seed edited\n")

    r = _mirror(work, "sweep", "--all")
    assert r.returncode == 0, f"mirror failed:\n{r.stdout}\n{r.stderr}"
    assert _committed_files(work) == ["seed.txt", "x.txt"]
