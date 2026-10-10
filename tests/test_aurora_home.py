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

from core import paths as P
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


# --------------------------------------------------------------------------
# the per-world home
# --------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A prod home under tmp_path, with the world pinned to prod."""
    base = tmp_path / "dot-aurora"
    monkeypatch.setenv("AURORA_HOME", str(base))
    monkeypatch.setattr(W, "current", lambda: W.WORLDS["prod"])
    monkeypatch.delenv("AI_SETUP", raising=False)
    return base


def test_no_home_directory_means_no_home_and_unchanged_roots(home):
    assert P.aurora_home() is None
    assert P.state_root() == P.data_root()
    assert P.shared_state_root() == P.repo_root()


def test_home_is_keyed_by_world(home, monkeypatch):
    (home / "prod").mkdir(parents=True)
    assert P.aurora_home() == home / "prod"
    monkeypatch.setattr(W, "current", lambda: W.WORLDS["alpha"])
    assert P.aurora_home() is None  # alpha has no home yet: never borrow prod's


def test_unknown_world_never_gets_a_home(home, monkeypatch):
    (home / "unknown").mkdir(parents=True)
    monkeypatch.setattr(W, "current", lambda: W.UNKNOWN)
    assert P.aurora_home() is None


def test_existing_home_wins_for_both_roots(home):
    (home / "prod").mkdir(parents=True)
    assert P.state_root() == home / "prod"
    assert P.shared_state_root() == home / "prod"


def test_bare_ai_setup_still_isolates_state_but_not_shared_state(home, tmp_path, monkeypatch):
    (home / "prod").mkdir(parents=True)
    bare = tmp_path / "bare"
    bare.mkdir()
    monkeypatch.setenv("AI_SETUP", str(bare))
    assert P.state_root() == bare  # test isolation keeps working
    assert P.shared_state_root() == home / "prod"  # one embedded server per world, as before


def test_a_repo_ai_setup_does_not_outrank_the_home(home, monkeypatch):
    """The harness hooks set AI_SETUP to the project dir; that names code, not a data dir."""
    (home / "prod").mkdir(parents=True)
    monkeypatch.setenv("AI_SETUP", str(P.repo_root()))
    assert P.state_root() == home / "prod"
