"""RED pins: `find --sort` and every `--preset` are silently inert.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

DANIEL, 2026-10-07, after watching me walk 172,070 files instead of using his own verb:
"Find is supposed to be instant, what hung?" -- and chasing that found this, which is worse
than the slow command that surfaced it.

THE DEFECT. `py agent_cli.py find` documents nine `--sort` keys and eight `--preset` goals.
NONE of them reach the output. The flag IS built correctly and IS passed to es.exe
(`core/tools/everything.py:573-577` validates the key and appends `["-sort", sort]`). Then the
Python layer throws the result away:

    ranked = _rank_exact_first(lines, query)

`_rank_exact_first` sorts by ``(basename != needle, len(path))``, so whatever order es.exe
returned is replaced by exact-match-then-PATH-LENGTH. There are FOUR such sites, because
`search()` and `search_page()` each have a plain-path form and a json/csv form:

    search()       plain  :628      json/csv  :617
    search_page()  plain  :746      json/csv  :737

MEASURED 2026-10-07. Three documented ways to ask for date order, all three byte-identical,
all three wrong::

    find "Transcript" --scope "...\\!Documents" --sort date-modified-descending
    find "Transcript" --scope "...\\!Documents" --sort date-modified-descending --no-sort
    find "Transcript" --scope "...\\!Documents" --preset recently-changed

returned 2013, 2013, 2013, 2020, 2013 ... with three files modified THAT MORNING ranked 7th,
8th and 10th. The actual ordering was ascending path length -- `_rank_exact_first`'s tiebreak
doing the sorting, because its primary key (exact basename) tied across every row.

WHY THE RANKING EXISTS, because the fix must not delete it. The comment at :596 earns it:
es.exe applies `-n` with ITS OWN order, so truncating at max_results can discard the
exact-basename match before Python ever sees it -- measured there, `es.exe` with `-n 4`
returned WhoUses.exe / SetupAsusServices.exe / FindPackages.exe / Cities.exe and the actual
es.exe was not among them. That argues for ranking to protect the OVER-FETCH when es.exe's
order is arbitrary. It does not argue for overriding an order the caller explicitly named --
and when `-sort` IS passed, es.exe's `-n` truncates in the REQUESTED order, so the original
hazard is gone by construction.

THE CLASS, not the instance -- which `_rank_exact_first`'s own docstring already demands:
"The first version of it was inside [walk_search], so the bounded walk was ranked and the
indexed path -- the one people will actually use -- was not. Fixing the instance and leaving
the class open is the recurring defect of this session; a shared helper is the version that
cannot drift apart." The same argument applies now: the decision to rank belongs INSIDE the
shared helper, not at four call sites that can drift.

Run::

    py -m pytest tests/test_find_honors_the_sort_it_was_asked_for.py -q
"""
from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.tools import everything as E  # noqa: E402

CLI = str(ROOT / "agent_cli.py")


def _run(*args, timeout=60):
    return subprocess.run([sys.executable, "-X", "utf8", CLI, *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=str(ROOT), timeout=timeout, stdin=subprocess.DEVNULL)


def _have_everything() -> bool:
    """The real locator is resolve_es(). An earlier version of this guessed at es_path() and
    _find_es(), neither of which exists -- so every end-to-end pin SKIPPED on a host where
    Everything works fine, and a skipped pin reads green. Guessing a precondition is how a
    pin quietly stops testing anything."""
    return bool(E.resolve_es())



#: Rows render as "M/D/YYYY H:MM:SS AM  <path>". Parse the WHOLE timestamp.
#: The first version of these pins compared only the YEAR and passed vacuously, because every
#: hit on this host is from 2026 -- a pin whose comparison cannot discriminate is a green that
#: measures nothing. Calibration before conclusion, every time.
_STAMP = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)")


def _stamps(text):
    from datetime import datetime
    out = []
    for raw in _STAMP.findall(text):
        try:
            out.append(datetime.strptime(" ".join(raw.split()), "%m/%d/%Y %I:%M:%S %p"))
        except ValueError:
            pass
    return out

# ------------------------------------------------------------------ the helper (deterministic)
def test_the_ranker_leaves_an_explicitly_sorted_result_alone():
    """THE PIN. When the caller named a sort, es.exe already answered in that order and the
    ranker must not re-answer. This is the whole defect in one assertion."""
    paths = [
        r"C:\a\zzzz\2026 Return Transcript.pdf",   # newest, longest path -- ranker buries it
        r"C:\a\Transcript.pdf",                    # exact basename, shortest -- ranker promotes it
        r"C:\a\b\old Transcript.pdf",
    ]
    out = E._rank_exact_first(paths, "Transcript", sorted_by="date-modified-descending")
    assert list(out) == paths, (
        "the ranker reordered a result the caller had explicitly sorted. es.exe returned these "
        "in date-modified-descending order and _rank_exact_first replaced that with "
        "(exact-basename, path-length) -- which is why `--sort` and every `--preset` are "
        "silently inert.")


def test_the_ranker_still_promotes_the_exact_match_when_no_sort_was_asked_for():
    """RATCHET. The fix must not delete the ranking -- without an explicit sort, es.exe's order
    is arbitrary and the exact-basename hit genuinely needs rescuing (its docstring measures
    the case: searching es.exe returned Cities.exe and WhoUses.exe ahead of es.exe itself)."""
    paths = [
        r"C:\a\WhoUses.exe",
        r"C:\a\b\c\es.exe",
        r"C:\a\Cities.exe",
    ]
    out = E._rank_exact_first(paths, "es.exe")
    assert os.path.basename(out[0]).lower() == "es.exe", (
        "exact-basename-first ranking was lost: %r" % (out,))


def test_the_ranker_takes_a_key_so_one_helper_serves_paths_and_hits():
    """THE CLASS. There are FOUR re-rank sites because the json/csv forms rank Hit objects and
    the plain forms rank strings, so each grew its own copy of the sort expression. One helper
    with a key extractor is the version that cannot drift apart -- the argument
    _rank_exact_first's own docstring already makes about walk_search."""
    class _Hit:
        def __init__(self, path): self.path = path
    hits = [_Hit(r"C:\a\zz\Transcript.pdf"), _Hit(r"C:\a\Transcript.pdf")]
    out = E._rank_exact_first(hits, "Transcript", key=lambda h: h.path)
    assert [h.path for h in out] == [r"C:\a\Transcript.pdf", r"C:\a\zz\Transcript.pdf"]
    kept = E._rank_exact_first(hits, "Transcript", key=lambda h: h.path, sorted_by="size")
    assert [h.path for h in kept] == [h.path for h in hits], "explicit sort not preserved for Hits"


def test_no_call_site_sorts_after_the_helper():
    """THE DRIFT GUARD. Four sites re-implemented the sort expression inline; if any keeps its
    own copy, `--sort` stays broken on that path only, which is the hardest version to notice."""
    src = inspect.getsource(E)
    body = re.sub(r'"""(?:.|\n)*?"""', "", src)
    offenders = [ln.strip() for ln in body.splitlines()
                 if ".sort(" in ln and "basename" in ln]
    assert not offenders, (
        "a call site still sorts by basename inline instead of going through the shared "
        "helper, so --sort is honored on some paths and not others: %r" % (offenders[:4],))


# ------------------------------------------------------------------ end to end, through the door
@pytest.mark.skipif(not _have_everything(), reason="Everything/es.exe not installed on this host")
def test_sort_date_modified_descending_actually_returns_descending_dates():
    """THE USER-VISIBLE PIN. This is the exact command that failed on 2026-10-07."""
    r = _run("find", "Transcript", "--sort", "date-modified-descending",
             "--columns", "date-modified", "--limit", "8")
    assert r.returncode == 0, r.stderr[:400]
    stamps = _stamps(r.stdout)
    if len(stamps) < 3:
        pytest.skip("fewer than 3 dated rows on this host to compare")
    assert stamps == sorted(stamps, reverse=True), (
        "--sort date-modified-descending returned %r -- not descending. es.exe was asked for "
        "the order and the Python re-rank discarded it."
        % ([d.strftime("%Y-%m-%d") for d in stamps],))


@pytest.mark.skipif(not _have_everything(), reason="Everything/es.exe not installed on this host")
def test_preset_recent_routes_through_sort_and_also_works():
    """A preset is sugar over --sort (`recent` -> date-modified-descending), so it rides the
    same defect. Pinned separately because a preset is what a reader actually reaches for."""
    r = _run("find", "Transcript", "--preset", "recent",
             "--columns", "date-modified", "--limit", "8")
    assert r.returncode == 0, r.stderr[:400]
    stamps = _stamps(r.stdout)
    if len(stamps) < 3:
        pytest.skip("fewer than 3 dated rows on this host to compare")
    assert stamps == sorted(stamps, reverse=True), (
        "--preset recent returned %r -- not newest-first"
        % ([d.strftime("%Y-%m-%d") for d in stamps],))


@pytest.mark.skipif(not _have_everything(), reason="Everything/es.exe not installed on this host")
def test_the_default_search_still_puts_the_exact_match_first():
    """RATCHET end-to-end: with no --sort, the behaviour the ranker exists for must survive."""
    r = _run("find", "agent_cli.py", "--limit", "5", "--bare")
    assert r.returncode == 0, r.stderr[:400]
    lines = [l.strip() for l in r.stdout.splitlines()
             if l.strip().lower().endswith(".py")]
    if not lines:
        pytest.skip("no hits for agent_cli.py on this host")
    assert os.path.basename(lines[0]).lower() == "agent_cli.py", (
        "the exact basename is no longer ranked first with no explicit sort: %r" % (lines[:3],))


# ------------------------------------------------------------------ the SECOND defect, found by play
def test_a_bare_sort_key_is_descending_in_es_so_ascending_presets_must_say_so():
    """RED #2, found by exercising the verb after the first fix landed -- which is the argument
    for playing with a thing rather than declaring it fixed.

    es.exe's help reads ``-sort <name[-ascending|-descending]>``, and the natural reading is
    that a bare name means ascending. IT DOES NOT. Measured directly against es.exe:

        es Transcript -sort date-created            -> 10/7, 10/7, 10/7, 10/6   (DESCENDING)
        es Transcript -sort date-created-ascending  -> 11/1/2025, 11/9/2025 ... (ascending)

    So a bare key is DESCENDING, and the two presets whose whole intent is ascending were
    silently inverted -- they returned exactly the opposite of their names:

        oldest    -> {"sort": "date-created"}  ->  NEWEST first
        smallest  -> {"sort": "size"}          ->  BIGGEST first  (measured: 16.3 MB, 16.3 MB, 2.3 MB)

    This was invisible until the first fix landed, because while the Python re-rank was
    discarding every order, no preset produced its own order anyway.
    """
    assert E.resolve_preset("oldest")["sort"].endswith("-ascending"), (
        "preset 'oldest' is %r -- a bare es.exe key, which sorts DESCENDING, so 'oldest' "
        "returns the newest files" % (E.resolve_preset("oldest")["sort"],))
    assert E.resolve_preset("smallest")["sort"].endswith("-ascending"), (
        "preset 'smallest' is %r -- a bare es.exe key, which sorts DESCENDING, so 'smallest' "
        "returns the biggest files" % (E.resolve_preset("smallest")["sort"],))
    # and the validator must admit the suffix the fix depends on
    assert E.is_valid_sort_key("date-created-ascending")
    assert E.is_valid_sort_key("size-ascending")


@pytest.mark.skipif(not _have_everything(), reason="Everything/es.exe not installed on this host")
def test_preset_smallest_actually_returns_the_smallest():
    """End-to-end on the inverted preset. Sizes render with thousands separators."""
    # --files: the smallest hits are DIRECTORIES, whose size column renders blank, so without
    # this the size regex matches nothing and the pin skips -- green by vacancy again.
    r = _run("find", "Transcript", "--preset", "smallest", "--files",
             "--columns", "size", "--limit", "6")
    assert r.returncode == 0, r.stderr[:300]
    sizes = [int(m.replace(",", "")) for m in re.findall(r"^\s*([\d,]+)\s+[A-Za-z]:", r.stdout, re.M)]
    if len(sizes) < 3:
        pytest.skip("fewer than 3 sized rows to compare on this host")
    assert sizes == sorted(sizes), (
        "--preset smallest returned %r -- that is largest-first, the opposite of its name" % (sizes,))
