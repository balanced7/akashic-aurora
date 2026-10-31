"""Repo-hygiene pins (phase 3 of the modular-core detangle, 2026-10-30 wish, items 6a-6d).

The wish, verbatim from docs/WISHLIST.md:

    "Repo hygiene: `.gitattributes` line endings (a CRLF warning on every commit; out-of-tree
     diffs read as rewrites); docs/PHYSICS.md as a generated file with a merge driver (it
     conflicted in EVERY merge today); worktrees inherit `.aurora-world` (an "UNKNOWN checkout"
     warning on every worktree commit); consistent `--limit`/`--json` on every listing verb."

Each clause is pinned where it can regress silently:

  6a  the line-ending rules name the extensions MEASURED to be carrying CRLF, and the batch
      exception is still the only CRLF checkout (a later `* text eol=lf` would silently break it).
  6b  docs/PHYSICS.md keeps a merge driver that needs no per-clone git config (the reason this is
      a driver and not "stop tracking it"), and the pre-commit hook still regenerates it.
  6c  a git WORKTREE inherits its parent's `.aurora-world` -- and a worktree that declares its OWN
      marker still wins, because inheritance is evidence, not a verdict.
  6d  every listing verb carries `--json`, and the ones whose output is a list carry `--limit`.

Run: py tests/test_repo_hygiene_p3.py   (or via pytest)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import world as W                                                 # noqa: E402


def _gitattributes() -> str:
    with open(os.path.join(ROOT, ".gitattributes"), encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ------------------------------------------------------------------ 6a: line endings
def test_the_measured_crlf_extensions_are_named():
    text = _gitattributes()
    for pattern in ("*.jsonl", "*.ps1", "*.log", "*.tsv", "*.patch", "*.ini", "*.out",
                    "*.spec", "*.mdc", "*.svg"):
        assert any(line.strip().startswith(pattern) for line in text.splitlines()), \
            f"{pattern} carried CRLF in the working tree when this rule was written and is not named"


def test_the_batch_exception_survives_the_new_rules():
    """A future `* text eol=lf` would silently break cmd.exe's parser. The CRLF checkout stays
    the deliberate exception, and it is pinned as one."""
    lines = [ln.strip() for ln in _gitattributes().splitlines() if ln.strip()]
    assert "*.cmd    text eol=crlf" in lines or any(ln.startswith("*.cmd") and "eol=crlf" in ln
                                                    for ln in lines)
    assert any(ln.startswith("*.bat") and "eol=crlf" in ln for ln in lines)


def test_the_renormalisation_recipe_is_written_down():
    """The wish asked for 'the rule plus a note on how to renormalise later' -- a rule whose
    follow-up is unstated becomes either never applied or applied inside a feature branch."""
    text = _gitattributes()
    assert "git add --renormalize ." in text
    assert "never inside a feature" in text.lower() or "own deliberate commit" in text


# ------------------------------------------------------------------ 6b: the generated sheet
def test_physics_sheet_keeps_a_merge_driver_that_needs_no_clone_config():
    text = _gitattributes()
    line = next((ln for ln in text.splitlines()
                 if ln.strip().startswith("docs/PHYSICS.md")), "")
    assert line, "docs/PHYSICS.md lost its line in .gitattributes"
    assert "merge=union" in line, \
        "the driver must be git's BUILT-IN union: a custom driver needs `git config " \
        "merge.<name>.driver` in every clone, which is a rule you must remember"


def test_the_pre_commit_hook_still_regenerates_it():
    """The driver is only safe because the sheet is regenerated on EVERY commit -- that is what
    turns a union's temporary superset back into the one true sheet."""
    path = os.path.join(ROOT, "scripts", "githooks", "pre_commit.py")
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    assert "gen_physics_sheet" in src
    assert "PHYSICS.md" in src


# ------------------------------------------------------------------ 6c: worktree inheritance
def _fake_worktree(tmp_path, parent_name, marker=None):
    """Build <tmp>/parent/{.git,<marker>} and <tmp>/parent/.git/worktrees/wt + the worktree."""
    parent = tmp_path / parent_name
    (parent / ".git" / "worktrees" / "wt").mkdir(parents=True)
    if marker is not None:
        (parent / ".aurora-world").write_text(marker, encoding="utf-8")
    wt = tmp_path / "modular-core-p3"          # a leaf name that matches NO world
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {parent / '.git' / 'worktrees' / 'wt'}\n",
                             encoding="utf-8")
    return wt, parent


def test_a_worktree_inherits_the_parents_marker(tmp_path, monkeypatch):
    monkeypatch.delenv("AKASHIC_WORLD", raising=False)
    wt, parent = _fake_worktree(tmp_path, "AI-Setup", marker="alpha\n")
    w = W.resolve(wt, env={})
    assert w.name == "alpha", w
    assert w.source == "inherited", w.source
    assert str(parent) in w.why, w.why


def test_a_worktrees_OWN_marker_beats_the_parent(tmp_path):
    """Inheritance is evidence, not a verdict: a worktree may still be pulled into another world."""
    wt, _parent = _fake_worktree(tmp_path, "AI-Setup", marker="alpha\n")
    (wt / ".aurora-world").write_text("beta\n", encoding="utf-8")
    w = W.resolve(wt, env={})
    assert w.name == "beta", w
    assert w.source == "marker", w.source


def test_no_parent_marker_stays_unknown_and_says_why(tmp_path):
    wt, parent = _fake_worktree(tmp_path, "AI-Setup", marker=None)
    w = W.resolve(wt, env={})
    assert w.name == "unknown", w
    assert "worktree of" in w.why and str(parent) in w.why, w.why


def test_an_ordinary_checkout_is_unaffected(tmp_path):
    plain = tmp_path / "AI-Setup"
    (plain / ".git").mkdir(parents=True)          # a DIRECTORY, i.e. a normal checkout
    assert W._parent_checkout(plain) is None
    assert W.resolve(plain, env={}).name == "prod"


# ------------------------------------------------------------------ 6d: listing consistency
def test_the_listing_verbs_carry_the_house_flags():
    """`recall` had no `--limit` while printing 25 rows in silence -- the wish's own example.
    This pin is a TABLE, so a new listing verb has to be added here deliberately."""
    import argparse
    import agent_cli
    parser = agent_cli.build_parser()
    sa = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    need_json = ["recall", "list", "locks", "discover", "injections", "notes", "promoted",
                 "events", "defer", "bus", "reachability"]
    # `reachability` is a SCREEN (one fixed rung per question), not a row list -- it carries
    # --json but a --limit there would be a dial nothing turns. It is named in need_json above so
    # the difference is a stated classification rather than an omission.
    need_limit = ["recall", "list", "locks", "discover", "injections", "notes", "promoted",
                  "events"]
    for name in need_json:
        sub = sa.choices.get(name)
        assert sub is not None, f"{name} vanished from the door"
        opts = {o for a in sub._actions for o in a.option_strings}
        assert "--json" in opts, f"{name} is a listing verb without --json"
    for name in need_limit:
        sub = sa.choices.get(name)
        opts = {o for a in sub._actions for o in a.option_strings}
        assert "--limit" in opts, f"{name} is a listing verb without --limit"


def test_the_window_helper_confesses_a_cut():
    import argparse
    import agent_cli
    ns = argparse.Namespace(limit=2)
    rows, note = agent_cli._window(ns, [1, 2, 3], "lesson", verb="recall")
    assert rows == [1, 2]
    assert "2 of 3" in note and "--limit 0" in note
    # and a window that did NOT cut says nothing at all
    assert agent_cli._window(ns, [1, 2], "lesson") == ([1, 2], "")
    # 0 = no cap, the documented escape hatch
    assert agent_cli._window(argparse.Namespace(limit=0), [1, 2, 3], "lesson") == ([1, 2, 3], "")


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
