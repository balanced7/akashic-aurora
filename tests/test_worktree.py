"""Per-agent worktrees (Concurrency design C1).

The whole point: an agent works in its own worktree on its own branch, and green
slices integrate back to master. The integration test below runs the real git flow
in a temp repo: setup -> commit in the worktree -> integrate -> master has the change.

Run: py -m pytest tests/test_worktree.py -q
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.worktree as wt


# ------------------------------------------------------------- pure helpers
def test_branch_name_and_slug():
    assert wt.branch_name("claude") == "agent/claude"
    assert wt.branch_name("Cursor ") == "agent/cursor"
    assert wt.branch_name("a b!c") == "agent/a-b-c"
    assert wt.branch_name("") == "agent/agent"


def test_worktree_path_is_sibling(tmp_path):
    root = tmp_path / "AI-Setup"
    p = wt.worktree_path("claude", root=root)
    assert p == tmp_path / "AI-Setup-claude"
    p2 = wt.worktree_path("claude", root=root, base=tmp_path / "wts")
    assert p2 == tmp_path / "wts" / "AI-Setup-claude"


# ------------------------------------------------------------- integration
def _git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "AI-Setup"
    root.mkdir()
    _git(root, "init")
    _git(root, "branch", "-M", "master")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    (root / "seed.txt").write_text("seed\n")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-m", "seed")
    return root


def test_setup_creates_branch_and_worktree(repo, tmp_path):
    base = tmp_path / "wts"
    p = wt.setup("claude", root=repo, base=base)
    assert p.exists()
    assert (p / ".git").exists()                 # linked-worktree marker (a file, not a dir)
    assert (p / "seed.txt").exists()             # shares history
    branches = subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True).stdout
    assert "agent/claude" in branches


def test_same_branch_cannot_be_checked_out_twice(repo, tmp_path):
    base = tmp_path / "wts"
    wt.setup("claude", root=repo, base=base)
    # second worktree on the SAME branch must fail -- git's built-in collision guard
    r = subprocess.run(["git", "worktree", "add", str(tmp_path / "dup"), "agent/claude"],
                       cwd=repo, capture_output=True, text=True)
    assert r.returncode != 0


def test_integrate_lands_worktree_commit_on_master(repo, tmp_path):
    base = tmp_path / "wts"
    p = wt.setup("claude", root=repo, base=base)
    # work happens in the agent's worktree, on its branch
    (p / "feature.txt").write_text("from claude\n")
    _git(p, "add", "feature.txt")
    _git(p, "commit", "-m", "claude: add feature")
    assert not (repo / "feature.txt").exists()   # isolated: master can't see it yet

    wt.integrate("claude", root=repo)            # repo is on master (no origin -> push skipped)

    assert (repo / "feature.txt").exists()       # now master has it
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True).stdout
    assert "claude: add feature" in log


def test_integrate_refuses_off_master(repo, tmp_path):
    wt.setup("claude", root=repo, base=tmp_path / "wts")
    _git(repo, "checkout", "-b", "somewhere-else")
    with pytest.raises(SystemExit):
        wt.integrate("claude", root=repo)        # guard: integrate only from master
