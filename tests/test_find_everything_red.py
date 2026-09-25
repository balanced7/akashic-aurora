"""RED-first pin for the Search Everything seam (core/tools/everything.py).

The ``find`` verb's search half. These pins test the PURE seam — no Everything
install required. They assert the two properties that matter for a search door
that spans outside the project root:

  1. FAIL-SOFT: when es.exe is missing, search() returns ok=False with a reason,
     never a crash and never a silent empty result (an empty list would read as
     "no such file", which is the exact lie this verb exists to retire).
  2. VALUE/CONTROL SPLIT: format_result() renders a SearchResult; the seam never
     prints.

The live es.exe path (real index lookup) is NOT pinned here — it needs Everything
installed and is an integration concern; the unit contract is the fail-soft and
the render.
"""
from core.tools.everything import SearchResult, format_result, resolve_es, search


def test_empty_query_refuses():
    res = search("   ")
    assert res.ok is False
    assert res.paths == []
    assert "empty query" in (res.error or "")


def test_missing_es_falls_back_to_walk_not_silent(monkeypatch):
    # Force resolve_es to None (simulate "Everything not installed"). Since the engine
    # landed (commit a4fd74a2), a missing CLI no longer REFUSES -- it falls back to a
    # bounded walk and CONFESSES both the engine and the bound. An honest refusal was a
    # door that never opened; the walk answer opens it while still telling the caller it
    # is bounded (so a miss is never read as machine-wide absence).
    monkeypatch.setattr("core.tools.everything.resolve_es", lambda: None)
    monkeypatch.setattr("core.tools.everything._WALK_ROOTS", ())  # no roots -> no dirs walked
    res = search("1552504210585813062-message.txt")
    assert res.engine == "walk"          # the fallback engine answered, not the index
    # A miss with no roots walked is exhaustive (nothing to walk) -- but ok must stay True
    # so the caller can tell "searched, not found" from "failed to search". The BOUNDED
    # confession lives in format_result, not in a refusal crash.
    assert res.ok is True


def test_format_result_distinguishes_error_from_no_match():
    err = SearchResult("q", ok=False, error="es.exe not found")
    assert format_result(err).startswith("ERROR:")
    empty = SearchResult("q", paths=[], ok=True)
    assert "no matches" in format_result(empty)


def test_format_result_lists_paths():
    res = SearchResult("q", paths=[r"C:\a\q.txt", r"C:\b\q.txt"], ok=True)
    out = format_result(res)
    assert "2 match" in out
    assert r"C:\a\q.txt" in out


def test_resolve_es_honors_es_exe_override(monkeypatch, tmp_path):
    fake = tmp_path / "es.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("ES_EXE", str(fake))
    monkeypatch.setattr("core.tools.everything.shutil.which", lambda *a, **k: None)
    assert resolve_es() == str(fake)


# --- PAGING (the 200-cap fix) -------------------------------------------------
# search() asks ES for a fixed over-fetch window and trims, so hits 201+ are
# unreachable. search_page() fetches offset+limit, ranks, then slices -- so a wide
# query (es.ex / lib / .env) stops silently hiding everything past page one.

def _lines_for(n):
    # A fake 200-hit ES answer where the EXACT basename match ("target.exe") is the
    # FIRST line (so ranking keeps it first) and 199 decoys follow.
    return ["C:\\x\\target.exe"] + [f"C:\\x\\decoy{i}.exe" for i in range(n - 1)]


def test_search_page_returns_requested_slice(monkeypatch):
    from core.tools import everything as e

    class _Proc:
        returncode = 0
        stdout = "\n".join(_lines_for(50))
        stderr = ""

    monkeypatch.setattr(e, "resolve_es", lambda: r"C:\es\es.exe")
    monkeypatch.setattr(e.subprocess, "run", lambda *a, **k: _Proc())

    res = e.search_page("target.exe", limit=10, offset=5)
    assert res.ok is True
    assert res.engine == "everything"
    assert len(res.paths) == 10           # limit honoured
    # offset=5 slices INTO the ranked list: target.exe (ranked first) is already
    # skipped, so the returned window starts at decoy4.exe -- page 2 must not
    # re-show page 1's head.
    assert res.paths[0] == "C:\\x\\decoy4.exe"
    assert res.paths[4] == "C:\\x\\decoy8.exe"


def test_search_page_zero_offset_ranks_exact_first(monkeypatch):
    from core.tools import everything as e

    class _Proc:
        returncode = 0
        stdout = "\n".join(_lines_for(50))
        stderr = ""

    monkeypatch.setattr(e, "resolve_es", lambda: r"C:\es\es.exe")
    monkeypatch.setattr(e.subprocess, "run", lambda *a, **k: _Proc())

    res = e.search_page("target.exe", limit=10)   # offset omitted -> 0
    # At offset 0 the EXACT basename match must be ranked FIRST (the whole reason
    # ranking exists -- so target.exe isn't buried under decoys).
    assert res.paths[0] == "C:\\x\\target.exe"


def test_search_page_offset_beyond_result_is_empty(monkeypatch):
    from core.tools import everything as e

    class _Proc:
        returncode = 0
        stdout = "\n".join(_lines_for(10))
        stderr = ""

    monkeypatch.setattr(e, "resolve_es", lambda: r"C:\es\es.exe")
    monkeypatch.setattr(e.subprocess, "run", lambda *a, **k: _Proc())

    res = e.search_page("target.exe", limit=10, offset=100)
    assert res.ok is True
    assert res.paths == []               # offset pushed past everything -> empty, not crash


def test_search_page_fetch_window_covers_offset(monkeypatch):
    from core.tools import everything as e
    captured = {}

    class _Proc:
        returncode = 0
        stdout = "\n".join(_lines_for(500))
        stderr = ""

    def _fake_run(argv, **k):
        captured["argv"] = argv
        return _Proc()

    monkeypatch.setattr(e, "resolve_es", lambda: r"C:\es\es.exe")
    monkeypatch.setattr(e.subprocess, "run", _fake_run)

    e.search_page("x", limit=200, offset=300)
    # -n fetch window must be >= (offset+limit) so the slice EXISTS in what we hold.
    argv = captured["argv"]
    n_idx = argv.index("-n")
    fetch = int(argv[n_idx + 1])
    assert fetch >= 300 + 200
