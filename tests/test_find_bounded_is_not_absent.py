"""The `find` verb must have an engine, and must never let a bounded miss read as absence.

TWO DEFECTS, FOUND TOGETHER 2026-09-24.

DEFECT ONE: THE VERB HAD NO ENGINE WITHOUT A THIRD-PARTY INSTALL. `find` shelled to Search
Everything's es.exe and, when that was absent, refused:

    ERROR: es.exe not found (Search Everything CLI). ... No search was run -- this is NOT
    'no results'.

That refusal is honest -- it says plainly that nothing ran, which is better than a lying zero.
But it is still a door that never opens. Everything is not installed on this machine, so the
verb did not exist for anybody, and the blind spot it was built to close stayed open.

DEFECT TWO, AND IT WAS MINE. Asked whether ffmpeg was on this machine I answered "absent,
confirmed three ways" and named: shutil.which, `where ffmpeg`, and a recursive glob. The first
two both ask PATH -- one question, asked twice -- and the third I had written with
`recursive=False`, so it walked nothing at all. Three checks, one narrow question, and I
reported the answer to a far wider one. I then told two peers their work was blocked on an
install.

The operator pushed back from memory ("I thought we had ffmpeg for our caption verb") and was
right. With a real engine the verb found it in 25 seconds:

    C:\\Users\\L5\\AppData\\Local\\StemRollerTrio\\ffmpeg\\bin\\ffmpeg.exe

THE LAW THESE PINS ENCODE. An unsearched space is not an empty one. A search that stops on a
budget and finds nothing has learned NOTHING about the world beyond its budget, and if it
reports a bare zero the reader will hear absence -- which is `zero is not no`, arriving on the
filesystem plane after the mailbox, the ingestion plane, the tool surface and the search half
had each produced their own version of it in the same twenty-four hours.

Run::

    py -m pytest tests/test_find_bounded_is_not_absent.py -q
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.tools import everything as ev  # noqa: E402


def test_the_verb_has_an_engine_even_without_search_everything(monkeypatch, tmp_path):
    """THE PIN THE INCIDENT NEEDED. Not "it refuses politely" -- it must SEARCH."""
    (tmp_path / "needle_file.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ev, "resolve_es", lambda: None)          # Everything absent
    monkeypatch.setattr(ev, "_WALK_ROOTS", (str(tmp_path),))

    res = ev.search("needle_file")
    assert res.ok, f"search refused instead of falling back: {res.error!r}"
    assert res.engine == "walk", f"expected the fallback engine, got {res.engine!r}"
    assert any("needle_file.txt" in p for p in res.paths), (
        "the fallback engine reported success but found a file that is demonstrably there"
    )


def test_a_bounded_miss_never_renders_as_absence(monkeypatch, tmp_path):
    """The load-bearing one. Zero results from a BUDGET-STOPPED search must say so, in the
    text a human reads, not merely in a field a caller might inspect."""
    res = ev.SearchResult(query="ffmpeg.exe", paths=[], ok=True, engine="walk",
                          exhaustive=False, scanned_dirs=73513, roots=["C:/Users/L5"],
                          elapsed_s=25.02)
    out = ev.format_result(res)
    low = out.lower()
    assert "bounded" in low, f"a budget-stopped miss did not say it was bounded: {out!r}"
    assert "not evidence" in low or "not 'no results'" in low, (
        "the render does not warn that this is not evidence of absence -- a reader takes a "
        "bare zero as 'the file is not on this machine', which is exactly the error this "
        "module exists to prevent"
    )


def test_a_COMPLETED_walk_that_finds_nothing_says_THAT_instead(tmp_path):
    """The other half, and it must not be collapsed into the first: a walk that genuinely
    finished and found nothing IS evidence, and must read differently from a bounded miss.
    Reporting both as one sentence is the defect, whichever way it is resolved."""
    res = ev.SearchResult(query="nothing_here", paths=[], ok=True, engine="walk",
                          exhaustive=True, scanned_dirs=12, roots=[str(tmp_path)],
                          elapsed_s=0.01)
    out = ev.format_result(res)
    assert "completed" in out.lower(), f"a finished walk did not say so: {out!r}"

    bounded = ev.format_result(ev.SearchResult(query="nothing_here", paths=[], ok=True,
                                               engine="walk", exhaustive=False,
                                               scanned_dirs=12, roots=[str(tmp_path)]))
    assert out != bounded, "a completed miss and a bounded miss render identically"


def test_the_render_always_names_which_engine_answered(tmp_path):
    """An indexed whole-machine answer and a bounded partial walk are different evidence.
    A reader who cannot tell them apart cannot weigh either."""
    walk = ev.format_result(ev.SearchResult(query="q", paths=[r"C:\a\b.exe"], ok=True,
                                            engine="walk", exhaustive=True, scanned_dirs=5,
                                            roots=["C:/a"], elapsed_s=0.1))
    idx = ev.format_result(ev.SearchResult(query="q", paths=[r"C:\a\b.exe"], ok=True,
                                           engine="everything", exhaustive=True))
    assert "walk" in walk.lower()
    assert "everything" in idx.lower()
    assert walk != idx, "the two engines' results are indistinguishable to a reader"


def test_the_walk_does_not_descend_the_same_real_directory_twice(monkeypatch, tmp_path):
    """Windows junctions make USERPROFILE and LOCALAPPDATA overlap heavily. Without the
    realpath guard the walk spends its budget re-walking one tree and reports a bounded miss
    for files it would have reached -- a self-inflicted false absence."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "target.bin").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ev, "resolve_es", lambda: None)
    monkeypatch.setattr(ev, "_WALK_ROOTS", (str(real), str(real)))   # same root twice

    res = ev.search("target.bin")
    assert res.ok and res.paths, "the duplicated root broke the search entirely"
    assert len(res.paths) == 1, (
        f"the same real directory was walked twice and the file reported {len(res.paths)} "
        f"times: {res.paths}"
    )
