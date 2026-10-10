"""Pins for the per-world home (~/.aurora/<world>) and worktree world inheritance.

THE DEFECT THIS CLOSES (measured 2026-10-10): a git worktree of the prod checkout resolved to
the UNKNOWN world, because its directory name matched no world and the gitignored
.aurora-world marker never reaches a new worktree. UNKNOWN refuses writes, so an agent that
started its work in a fresh worktree could not learn, note or log. And every piece of instance
state (session logs, transcript index, embedded-Redis files) resolved beside the worktree's own
code, cut off from the main checkout and deleted with the worktree.

THE SHAPE: a worktree inherits the world of the checkout it was cut from, and gitignored
instance state lives in one home per world, used only once that directory exists.
"""

import subprocess

import pytest

from core import world as W

# --------------------------------------------------------------------------
# worktree inheritance
# --------------------------------------------------------------------------


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def prod_with_worktree(tmp_path):
    main = tmp_path / "aurora"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init", cwd=main)
    wt = tmp_path / "elsewhere" / "feature-x"
    _git("worktree", "add", "-q", str(wt), cwd=main)
    return main, wt


def test_main_checkout_of_finds_the_main_checkout(prod_with_worktree):
    main, wt = prod_with_worktree
    assert W.main_checkout_of(wt) == main.resolve()


def test_main_checkout_of_is_none_for_a_main_checkout_or_a_plain_dir(prod_with_worktree, tmp_path):
    main, _ = prod_with_worktree
    assert W.main_checkout_of(main) is None
    assert W.main_checkout_of(tmp_path / "not-a-repo") is None


def test_worktree_inherits_the_world_of_its_main_checkout(prod_with_worktree):
    _, wt = prod_with_worktree
    w = W.resolve(root=wt, env={})
    assert w.name == "prod"
    assert w.source == "inherited"
    assert "worktree of 'aurora'" in w.why
    assert w.may_write


def test_worktree_inherits_the_main_checkouts_marker(prod_with_worktree):
    main, wt = prod_with_worktree
    (main / W.MARKER).write_text("alpha\n", encoding="utf-8")
    assert W.resolve(root=wt, env={}).name == "alpha"


def test_a_worktrees_own_marker_and_the_env_still_win(prod_with_worktree):
    _, wt = prod_with_worktree
    assert W.resolve(root=wt, env={"AKASHIC_WORLD": "beta"}).name == "beta"
    (wt / W.MARKER).write_text("alpha\n", encoding="utf-8")
    assert W.resolve(root=wt, env={}).source == "marker"


def test_a_worktree_of_an_unknown_checkout_stays_unknown(tmp_path):
    main = tmp_path / "some-repo"
    main.mkdir()
    _git("init", "-q", cwd=main)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init", cwd=main)
    wt = tmp_path / "wt"
    _git("worktree", "add", "-q", str(wt), cwd=main)
    assert W.resolve(root=wt, env={}).name == "unknown"
