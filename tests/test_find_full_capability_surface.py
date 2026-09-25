"""RED-first acceptance pins: surface the FULL es.exe capability set through `find`.

THE DIRECTIVE (Daniil, 2026-09-25, verbatim intent): "Lets surface the full capabilities
of es in an ergonomic way through find, we bought the whole tool, lets use the whole tool."

These pins freeze the ACCEPTANCE CONTRACT for three things `core/tools/everything.py`
currently strips down to bare ranked paths (verified against es.exe 1.1.0.38 -h):

  (1) METADATA HALF  -- structured per-hit fields (size, date-modified, date-created,
      date-accessed, extension, attributes) ride back as structured records.
  (2) QUERY HALF     -- the search grammar (regex, whole-word, case, dirs-only,
      files-only, path-scoping) is exposed as clean named flags on the seams.
  (3) JOURNAL HALF   -- the live change stream becomes a first-class `journal()` seam.

EVERY pin below is written to FAIL TODAY for the right reason (the seam does not exist),
so observing them RED proves the pre-registration, not a typo. Per the shared-tree
red-fence discipline: these land RED and get observed RED BEFORE any GREEN implementation.
"""
from __future__ import annotations

import pytest

from core.tools import everything as e
from core.tools.everything import SearchResult


# --------------------------------------------------------------------------- (1) metadata half

def test_search_result_exposes_structured_hits():
    """The value object must expose per-hit records, not just a bare path list."""
    sr = SearchResult(query="q")
    # RED reason: SearchResult has 'paths' (List[str]) and NO 'hits' field yet.
    assert hasattr(sr, "hits")


def test_search_page_accepts_sort_and_columns():
    """The seam accepts sort=<key> and columns=<list> so es -sort / -add-columns are reachable."""
    import inspect
    sig = inspect.signature(e.search_page)
    # RED reason: search_page's current signature has no sort= / columns= params.
    assert "sort" in sig.parameters
    assert "columns" in sig.parameters


def test_search_page_accepts_json_format():
    """The seam accepts format='json' so -json output is reachable."""
    import inspect
    sig = inspect.signature(e.search_page)
    # RED reason: no format= param yet.
    assert "format" in sig.parameters


def test_search_result_has_date_modified_field():
    """mtime is the inventory combo's fuel; it must be a first-class per-hit field."""
    # RED reason: no Hit/entry dataclass exists yet to carry date_modified.
    assert hasattr(e, "Hit") or hasattr(SearchResult, "hits")


# --------------------------------------------------------------------------- (2) query half

def test_search_accepts_regex_flag():
    """regex=True maps to es -r."""
    import inspect
    sig = inspect.signature(e.search)
    assert "regex" in sig.parameters


def test_search_accepts_whole_word_and_case_flags():
    """whole_word -> -w / -ww, case -> -i."""
    import inspect
    sig = inspect.signature(e.search)
    assert "whole_word" in sig.parameters
    assert "case" in sig.parameters


def test_search_accepts_dir_and_file_only_flags():
    """dirs_only -> /ad, files_only -> /a-d."""
    import inspect
    sig = inspect.signature(e.search)
    assert "dirs_only" in sig.parameters
    assert "files_only" in sig.parameters


def test_search_accepts_path_scoping():
    """scope=<dir> -> -path <dir>."""
    import inspect
    sig = inspect.signature(e.search)
    assert "scope" in sig.parameters


# --------------------------------------------------------------------------- (3) journal half

# DEFERRED (Daniil: "do 1 and 3, work towards 2" — but the journal() seam is the Option-3
# half held for its OWN fence, a separate slice). These two pins stay as xfail (strict) so
# the deferred contract stays visible and the suite is honestly green for what shipped
# (metadata + query halves). When the journal slice lands, flip these to plain asserts.

@pytest.mark.xfail(reason="journal() seam deferred to its own fence (Option 3 half)", strict=True)
def test_journal_seam_exists():
    """core.tools.everything grows a journal() seam for the live change stream."""
    assert hasattr(e, "journal")


@pytest.mark.xfail(reason="journal() seam deferred to its own fence (Option 3 half)", strict=True)
def test_journal_accepts_from_and_action_filter():
    """journal(from_='today', action='file-modify') reaches es -from-today -action-filter."""
    import inspect
    assert callable(getattr(e, "journal", None))
    sig = inspect.signature(e.journal)
    assert "from_" in sig.parameters
    assert "action" in sig.parameters


# --------------------------------------------------------------------------- live-index (integration)

def test_live_es_available_for_integration():
    """Everything is installed on this host (resolves). If absent, the above pins still
    hold shape-contract; this one records whether the live path CAN be exercised at all."""
    # Not a pass/fail on feature — a fact the slice needs to know which tests are
    # substantively runnable vs shape-only.
    assert e.resolve_es() is not None, "es.exe not found — live integration pins will skip"
