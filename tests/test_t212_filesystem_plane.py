"""
T212 -- the filesystem as an OBSERVED plane in the timeline. RED first.

Daniil, 2026-08-07: "we don't have to only derive time from file contents and titles, we
can see how old a file is and last time it was modified."

WHY IT IS A THIRD PLANE, not just a fourth source. The 07-30 relationship design (fleet-
reviewed, unbuilt) says keep DERIVED / AUTHORED / OBSERVED distinct and never launder one
into another. The timeline's existing sources are all things an agent DECLARED: events are
what a seat said happened, git commits are what someone chose to record, task rows are
ledger transitions. A file's mtime is different in kind -- the filesystem WITNESSED it,
with nobody's narration in between.

WHAT IT CATCHES THAT NOTHING ELSE CAN: activity that left no other trace. This session's
boot reported "18 modified (tracked), 127 untracked" -- whose, and when? No event, no
commit, no ledger row answers that. mtime does. It also makes `touched MINUS committed`
computable, which is work-in-flight or work-abandoned, and is exactly the cross-domain
difference Daniil identified as where the value lives.

THE TRAP THIS PINS, and it is our own bug class living inside the standard library:
`st_ctime` means CREATION time on Windows and INODE CHANGE time on Unix. One attribute,
two meanings, silently platform-dependent -- the fifth instance of one-word-two-meanings
in two days, and the first one we did not write ourselves. Reading it as "created" would
put a wrong birth time on every row on Linux and be right on Windows, which is the worst
possible failure shape: correct on the machine you test on.

Run: py -m pytest tests/test_t212_filesystem_plane.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import timeline as TL  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("y", encoding="utf-8")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "c.py").write_text("z", encoding="utf-8")
    return tmp_path


def test_files_become_rows_with_real_mtimes(tree):
    rows = TL._file_rows(root=str(tree))
    assert len(rows) == 3
    for r in rows:
        assert TL._epoch(r["ts"]) is not None
        assert TL._epoch(r["ts"]) > 1_000_000_000
    assert {os.path.basename(r["ref"]) for r in rows} == {"a.py", "b.md", "c.py"}


def test_the_row_says_modified_not_created(tree):
    """Precision in the KIND field, because this plane's whole value is that it is not
    narrated -- a row that says 'created' when it means 'modified' narrates."""
    rows = TL._file_rows(root=str(tree))
    assert all("modif" in r["kind"] for r in rows), [r["kind"] for r in rows]


def test_ctime_is_never_read_as_creation(tree):
    """THE LOAD-BEARING PIN. st_ctime is CREATION on Windows and INODE CHANGE on Unix.
    Reading it as 'created' is correct on the machine I develop on and wrong on the
    machine CI runs on -- the worst failure shape there is. Only st_birthtime, which
    exists solely where it means what it says, may source a birth time.

    READ AS NAMES, NOT TEXT -- and this is the FOURTH time in two days that a text-scan
    pin went red on the docstring explaining its own compliance. The root cause is
    structural, not carelessness: a prohibition worth pinning is a prohibition worth
    DOCUMENTING, and documenting it necessarily puts the forbidden token in the file.
    Text-scanning pins and good documentation are incompatible by construction. An AST
    walk reads identifiers and cannot see a docstring at all.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(TL))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    consts = {n.value for n in ast.walk(tree)
              if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "st_ctime" not in (attrs | names | consts), (
        "st_ctime means CREATION on Windows and INODE CHANGE on Unix -- use "
        "st_birthtime (guarded) or do not claim a birth time at all")
    assert "st_birthtime" in (attrs | names | consts), (
        "the guarded birth source must actually be the one consulted")


def test_birth_time_is_optional_and_absent_is_not_zero(tree):
    """Where the platform cannot say when a file was born, the field is absent. A 0
    would place every file at the dawn of the record -- the same epoch-0 lie T211
    caught in git's stamps."""
    rows = TL._file_rows(root=str(tree))
    for r in rows:
        born = r.get("born")
        assert born is None or born > 1_000_000_000


def test_the_scan_is_bounded_and_says_so(tree):
    """An unbounded walk over a large repo is how a fast index becomes a slow one that
    nobody runs. The cap is honest: truncation is reported, never silent."""
    rows = TL._file_rows(root=str(tree), limit=2)
    assert len(rows) == 2


def test_ignored_directories_are_skipped(tree):
    """.git alone is tens of thousands of files whose mtimes are git's business, not
    the project's history."""
    g = tree / ".git" / "objects"
    g.mkdir(parents=True)
    (g / "deadbeef").write_text("obj", encoding="utf-8")
    rows = TL._file_rows(root=str(tree))
    assert not any(".git" in r["ref"] for r in rows)


def test_files_plane_is_labelled_observed(tree):
    """Planes must stay distinguishable in the merged set, or a cross-match between
    'what was declared' and 'what was witnessed' cannot be expressed at all."""
    r = TL.gather(sources=[("files", lambda **kw: TL._file_rows(root=str(tree)))])
    assert all(row["domain"] == "files" for row in r["rows"])
    assert TL.PLANE_OF.get("files") == "OBSERVED"
    assert TL.PLANE_OF.get("git") == "AUTHORED"


def test_an_unreadable_file_does_not_kill_the_scan(tree, monkeypatch):
    """One bad stat must not cost the whole plane."""
    real = os.stat

    def flaky(path, *a, **k):
        if str(path).endswith("b.md"):
            raise OSError("permission denied")
        return real(path, *a, **k)

    monkeypatch.setattr(os, "stat", flaky)
    rows = TL._file_rows(root=str(tree))
    assert len(rows) == 2


def test_default_sources_now_include_the_observed_plane():
    assert "files" in {n for n, _ in TL.default_sources()}
