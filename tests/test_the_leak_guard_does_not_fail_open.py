"""RED pin: the private-plane filter silently does nothing in the way it is actually invoked.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

HOW IT WAS FOUND, 2026-10-07, and the finding is embarrassing in a useful way: I wrote the filter
three hours earlier, tested it, watched it work, and it was inert the whole time in the only
invocation anyone uses.

``_drop_private_plane()`` in ``scripts/generators/gen_library.py`` exists because the commit gate
caught the census naming a private-plane record in ``docs/SHELVES.md``. It opens with::

    try:
        from core.trust import private_plane as _pp
        marks = _pp.markers()
    except Exception:
        return list(entries), 0     # guard unavailable -> change nothing

MEASURED, all [CERTAIN] from my own commands:

  * ``py -X utf8 scripts/generators/gen_library.py`` -> ``SHELVES -> ... (25 type(s), 1764
    file(s))`` and **no private-plane line at all**, so ``_plane_dropped == 0``.
  * The marker survived the regeneration: ``docs/SHELVES.md:1729``, ``docs/ARCS.md:1853`` and
    ``research/reviewed/README.md:72`` each name the record, as ``unmarked``.
  * ``py -X utf8 -c "from core.trust import private_plane as p; print(len(p.markers()))"`` ->
    **70 markers**. The guard is healthy. It was never asked.
  * The cause, reproduced directly: with ``sys.path[0]`` set to ``scripts/generators/`` -- which is
    what Python does when you run a script BY PATH -- the import raises
    ``ModuleNotFoundError: No module named 'core'``.
  * ``gen_library.py`` inserts ROOT into ``sys.path`` in **three** places (lines 123, 453, 550),
    every one of them lazily, inside a function that needs ``core``. The default ``walk_docs()``
    path needs none of them, so by line 566 the repo root has never been added and the filter's own
    import is the first to try.

I only ever saw it work because I verified it in-process (``runpy``, after inserting ROOT myself)
and with ``py -c`` (which puts the cwd on ``sys.path``). Both of my checks supplied the one
condition the real invocation does not.

TWO DEFECTS, and the second is the one worth pinning.

1. The path. Fixed by hoisting the insert to module scope, once, instead of three lazy copies.

2. **The guard fails OPEN and says nothing.** ``except Exception: return entries, 0`` makes an
   unimportable guard indistinguishable from a corpus with nothing to hide: both print nothing and
   write every catalog. For a filter whose whole job is keeping private titles out of a public repo,
   the safe direction is the other one -- if the guard cannot run, the catalogs are not written. The
   module it guards says so itself: *"THE LEAK PATH IS REGENERATION, NOT AUTHORING."* A regeneration
   that cannot load the guard IS the leak path with the guard removed.

   The comment on that line reads ``never fail open loudly``, which I wrote, and which describes
   failing open quietly.

THE FIFTH TODAY. ``find --sort`` re-sorted after asking es.exe for an order. A pin of mine compared
only the YEAR when every row was 2026. ``--verify`` hashed nothing. The zone-README write could not
tell its own output from a human's. And now a leak guard that reports a clean sweep because its
import failed. Every one is green-by-not-looking, and every one stayed invisible until someone asked
what the check actually touched.

Run::

    py -m pytest tests/test_the_leak_guard_does_not_fail_open.py -q
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generators" / "gen_library.py"


def _src() -> str:
    return GEN.read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ defect 1: the path
def test_the_guard_actually_loads_in_the_real_invocation():
    """THE PIN. Measure the real thing, not a simulation of it.

    ``--stdout`` runs the full entry path -- walk, filter, census, render -- and writes no files, so
    this exercises exactly the code path that leaked while remaining side-effect free. If the guard
    loaded, the run says so on its own: it prints a counted ``private-plane:`` line. Silence means
    the filter's import failed and every private title went into the census.
    """
    r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), "--stdout"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=300)
    out = r.stdout + r.stderr
    assert "No module named 'core'" not in out, "the generator cannot import core when run by path"
    assert "private-plane:" in out, (
        "the generator ran its whole entry path and never reported the private-plane filter. "
        "Measured 2026-10-07: 1,764 files catalogued, 0 excluded, and the marker present in "
        "SHELVES, ARCS and research/reviewed/README.md -- because `from core.trust import "
        "private_plane` raised ModuleNotFoundError and `except Exception` returned the entries "
        "unfiltered.")


def test_the_root_insert_is_at_module_scope_not_three_lazy_copies():
    """Three lazy inserts (gen_library.py:123, 453, 550) make correctness depend on which code path
    runs first. The filter sits at the entry point and runs before all three."""
    src = _src()
    head = src[:src.index("\ndef ")]
    assert "sys.path" in head, (
        "ROOT is never added to sys.path at module scope, so whichever function runs first decides "
        "whether `core` is importable -- and the private-plane filter runs before all three of the "
        "lazy inserts at lines 123, 453 and 550")


# ------------------------------------------------------------------ defect 2: the direction
def test_the_filter_does_not_fail_open():
    """THE PIN THAT MATTERS. An unimportable leak guard must not read as a clean corpus.

    ``except Exception: return list(entries), 0`` writes every catalog with every private title in
    it and prints nothing. The whole point of this filter is that this is the expensive direction to
    be wrong in.
    """
    src = _src()
    i = src.index("def _drop_private_plane")
    block = src[i:i + 3000]
    assert "return list(entries), 0" not in block, (
        "the filter returns the UNFILTERED entries when its own import fails, so a guard that "
        "cannot load is indistinguishable from a corpus with nothing to hide")


def test_an_unavailable_guard_is_announced_and_blocks_the_write():
    """It must be loud AND it must stop. Printing a warning while still writing the catalogs leaks
    exactly as much as staying quiet; refusing silently leaves a stale census looking protected.

    THIS PIN WAS VACUOUS ON ITS FIRST DRAFT and the correction belongs in the file. It accepted
    ``"unavailable" in block`` -- and the word ``unavailable`` is sitting in the comment on the very
    line being accused (``# guard unavailable -> change nothing``), so the pin passed by matching
    the defect's own prose. That is the third vacuous pin I have written today by the same move:
    choosing a token that the broken code already contains. A pin must assert STRUCTURE, not
    vocabulary. So: the except path must ``raise``. Returning anything at all from a failed leak
    guard is the defect, whatever it prints on the way out.
    """
    src = _src()
    i = src.index("def _drop_private_plane")
    block = src[i:i + 3000]
    body = block[block.index("except"):] if "except" in block else ""
    assert body, "the filter no longer has an except path -- re-read this pin before deleting it"
    first_stmt = body[:400]
    assert "raise" in first_stmt, (
        "the filter's except path does not raise. A leak guard that cannot load must stop the "
        "regeneration, not hand back the unfiltered entries with a warning attached -- the catalogs "
        "get written either way, and written is what leaks.")


# ------------------------------------------------------------------ ratchets
def test_the_markers_themselves_are_healthy():
    """RATCHET, and the number worth watching. 70 markers on 2026-10-07, derived from private/ and
    never declared. If this collapses toward zero the filter becomes a no-op for a DIFFERENT reason
    and every pin above would still pass -- which is the failure mode this whole file is about."""
    sys.path.insert(0, str(ROOT))
    from core.trust import private_plane as pp
    marks = pp.markers()
    assert len(marks) >= 10, (
        "markers() returned %d -- derived markers have collapsed, so the filter matches nothing "
        "even when it does run" % len(marks))


def test_the_known_record_is_absent_from_every_regenerated_catalog():
    """REGRESSION GUARD on the specific leak. The record is UNTRACKED on disk and must never be
    named in a tracked catalog. The needle is split across two fragments so this test file is not
    itself an instance of the thing it guards against."""
    needle = "correspondence-" + "hudgins"
    for rel in ("docs/SHELVES.md", "docs/ARCS.md", "research/reviewed/README.md"):
        p = ROOT / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        assert needle not in text, (
            "%s names a private-plane record. Do NOT hand-edit it out -- the generator puts it "
            "back on the next run. Regenerate with the guard importable." % rel)
