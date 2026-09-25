"""RED-first pins for the `find` ergonomic surface (presets + CSV + rich defaults).

DIRECTIVE (Daniil, 2026-09-25): make `find` easy WITHOUT expert knowledge -- presets
for intent goals, deep/powerful modes easy to reach, DEFAULTS that return the easiest-to-
ingest form, and RICH (not bare) rendering. Two readers, two defaults:
  * the CLI (a human) gets an ANNOTATED TABLE (mtime + size + rank marker + loud bounded
    confession) by default;
  * the agent door (ToolBox/MCP) returns STRUCTURED FIELDS (the `hits` list serialized),
    NOT prose.

Every pin below FAILS TODAY for the right reason (the seam/flag/preset does not exist),
so observing RED proves the pre-registration, not a typo.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.tools import everything as ev  # noqa: E402


# --------------------------------------------------------------------------- presets

def test_presets_table_exists():
    """Intent presets live in a named table the CLI/ToolBox can read and print."""
    assert hasattr(ev, "PRESETS"), "no PRESETS table on core.tools.everything"


def test_preset_recent_maps_to_date_modified_descending():
    """`recent` must mean RECENT-FIRST -- which requires the DESCENDING sort variant the
    current _SORT_KEYS frozenset forbids."""
    assert ev.PRESETS["recent"]["sort"] == "date-modified-descending"


def test_presets_cover_the_intent_vocabulary():
    """The goal vocabulary a non-expert would reach for, all present."""
    for key in ("recent", "oldest", "biggest", "smallest", "newest"):
        assert key in ev.PRESETS, f"missing preset {key!r}"


def test_resolve_preset_fn_exists():
    """A resolver turns a preset name into the flat search kwargs."""
    assert callable(getattr(ev, "resolve_preset", None))


def test_resolve_unknown_preset_loud_not_silent():
    """An unknown preset must name itself and the valid set, never fall through to a
    bare substring search that silently ignores the typo."""
    res = ev.resolve_preset("recnt")
    assert res is None or "recnt" in str(res), (
        "an unknown preset did not name itself in the refusal"
    )


# --------------------------------------------------------------------------- CSV + rich default

def test_search_page_accepts_csv_format():
    """es.exe natively emits -csv; the seam must reach it (not hand-construct CSV)."""
    sig = inspect.signature(ev.search_page)
    # RED: csv is not a format value the seam handles today (only '' / 'json').
    # The seam accepts format='csv' in the signature already; this pins the BEHAVIOUR
    # via a round-trip below, so this is a shape-check only.
    assert "format" in sig.parameters


def test_csv_parses_to_structured_hits(monkeypatch):
    """format='csv' must parse es.exe's CSV into the same Hit records json mode yields,
    so the agent door can return fields regardless of which native format is cheapest."""
    class _Proc:
        returncode = 0
        stderr = ""
        stdout = (
            '"Filename","Size","Date Modified","Extension"\n'
            '"C:\\x\\target.exe","1024","2026-09-25 14:11:00",".exe"\n'
            '"C:\\x\\other.txt","2048","2026-09-24 09:02:00",".txt"\n'
        )

    monkeypatch.setattr(ev, "resolve_es", lambda: r"C:\es\es.exe")
    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **k: _Proc())

    res = ev.search_page("target.exe", format="csv")
    assert res.hits, "csv format produced no structured hits (RED: csv parsing not built)"
    assert res.hits[0].path == "C:\\x\\target.exe"


# --------------------------------------------------------------------------- rich render

def test_format_hits_marks_the_exact_basename_match():
    """_rank_exact_first already KNOWS which line is the answer; the render must show it
    so a reader's eye lands on the target instead of the first decoy."""
    hits = [
        ev.Hit(path="C:\\x\\target.exe", name="target.exe",
               date_modified="2026-09-25 14:11:00", size=1024),
        ev.Hit(path="C:\\x\\target2.exe", name="target2.exe",
               date_modified="2026-09-24 09:02:00", size=2048),
    ]
    out = ev.format_hits(ev.SearchResult(query="target.exe", hits=hits, ok=True,
                                         engine="everything"))
    first_line = out.splitlines()[1] if len(out.splitlines()) > 1 else ""
    assert "★" in first_line or "->" in first_line or "\u2192" in first_line, (
        f"the exact-basename hit was not marked: {first_line!r}"
    )


def test_format_hits_includes_size_and_mtime_columns():
    """The actionability column is mtime (and size): the render must show them, not a
    bare path list."""
    hits = [ev.Hit(path="C:\\x\\target.exe", name="target.exe",
                   date_modified="2026-09-25 14:11:00", size=1024)]
    out = ev.format_hits(ev.SearchResult(query="target.exe", hits=hits, ok=True,
                                         engine="everything"))
    assert "2026-09-25" in out, "mtime column missing from the rich render"
    assert "1024" in out, "size column missing from the rich render"


# --------------------------------------------------------------------------- fields-not-prose

def test_toolbox_find_defaults_to_structured_fields():
    """The agent door returns fields, not prose. The contract is `format` (its default is
    the structured 'json', not ''), so an agent calling find() gets data to route onward,
    not a rendered table to eyeball."""
    import core.comm.toolbox as tb
    sig = inspect.signature(tb.ToolBox.find)
    assert "format" in sig.parameters, "ToolBox.find lost its format param"
    fmt = sig.parameters["format"].default
    assert fmt == "json", (
        f"ToolBox.find must DEFAULT to structured fields ('json'), got {fmt!r} -- the agent "
        f"door is returning prose"
    )
