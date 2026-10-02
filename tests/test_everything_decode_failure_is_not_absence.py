"""RED pins: an undecodable byte in Everything's output must never render as "nothing found".

FOUND BY USING THE VERB, two minutes after Daniel asked how I was liking it. I ran
`py agent_cli.py find ".flp"` and it answered:

    (no matches for '.flp' — Everything answered, nothing found)

There are FL Studio projects on this machine. Five were listed a minute later with a plain
directory walk, starting with
`C:\\Program Files\\Image-Line\\FL Studio 2025\\Data\\Demo projects\\NewStuff.flp`.

WHAT ACTUALLY HAPPENED. `search()` calls `subprocess.run(..., text=True)` with no error
handler, so Python decodes es.exe's stdout as UTF-8 strictly. Some filename on these drives is
not valid UTF-8, and the decode raises inside subprocess's own reader THREAD:

    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x89 in position 1762: invalid start byte

A thread's exception does not propagate to the caller. `returncode` is still 0, `stdout` comes
back empty, the parse yields zero paths, `ok` stays True -- and the renderer prints the sentence
reserved for a search that genuinely found nothing. ONE bad byte anywhere in the output discards
EVERY result, and the loss is reported as a confident truth.

WHY THIS IS THE SHARPEST VERSION OF A RULE THIS HOUSE ALREADY HAS. "Zero is not no": an empty
answer must say whether it was asked and answered, or could not be asked. This module already
understands that better than almost anything in the repo -- its own `exhaustive` field carries the
docstring "An empty, NON-exhaustive result means 'not found in what we managed to look at', never
'not on this machine'", and `format_result` has a comment reading "THE LINE THAT MATTERS. A bounded
miss must never read as absence." The doctrine was written here first. The decode path simply never
routes into it, so the one failure mode the module was built to prevent arrives through a door it
did not guard.

And it is worse than a bounded miss, because a bounded miss at least SAYS it was bounded. This
says "Everything answered" -- the most trustworthy-sounding sentence available -- and that half is
even true. Everything did answer. We could not read the answer.

WHAT THE FIX MUST DO, and the choice is not obvious so it is stated. Decoding with
`errors="replace"` keeps every line and mangles only the offending name, which is strictly better
than losing the search: a path with one replacement character is still an answer a human can act
on, and `find` is a locator, not a byte-exact reader. But a replacement is still a LOSS, and a
caller comparing a returned path against a real one needs to know the string may not round-trip.
So the pins require both: keep the results, AND declare that some names were repaired. Silent
repair would trade a loud wrong answer for a quiet one.
"""
import os
import subprocess as _subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools import everything as E  # noqa: E402


# ---------------------------------------------------------------- the fixture
#: Real es.exe output with one undecodable byte in the middle name -- 0x89 is the byte that
#: actually broke this on the live machine.
DIRTY = (b"C:\\Program Files\\Image-Line\\FL Studio 2025\\Data\\Demo projects\\NewStuff.flp\r\n"
         b"C:\\Music\\bad\x89name.flp\r\n"
         b"E:\\AI-Setup\\scratch\\third.flp\r\n")
CLEAN = (b"C:\\one.flp\r\nC:\\two.flp\r\n")


class _Proc:
    def __init__(self, out, rc=0, err=""):
        self.stdout, self.returncode, self.stderr = out, rc, err


@pytest.fixture
def es(monkeypatch, tmp_path):
    """Pretend es.exe exists, and hand `search()` whatever bytes the test wants."""
    fake = tmp_path / "es.exe"
    fake.write_text("")
    monkeypatch.setattr(E, "resolve_es", lambda: str(fake))
    return fake


def _run_returning(monkeypatch, payload: bytes):
    """Emulate subprocess faithfully: under text=True with a strict codec the reader thread dies
    and the caller is handed an EMPTY stdout with returncode 0 -- which is the whole defect."""
    def fake_run(argv, **kw):
        if kw.get("text") or kw.get("universal_newlines") or kw.get("encoding"):
            errs = kw.get("errors")
            enc = kw.get("encoding") or "utf-8"
            if errs in (None, "strict"):
                try:
                    payload.decode(enc)
                except UnicodeDecodeError:
                    return _Proc("", rc=0)        # the thread died; caller sees nothing
            return _Proc(payload.decode(enc, errors=errs or "strict"), rc=0)
        return _Proc(payload, rc=0)               # bytes mode: nothing can fail to decode
    monkeypatch.setattr(E.subprocess, "run", fake_run)


# ---------------------------------------------------------------- P1-P3: it must not read as absence
def test_an_undecodable_byte_does_not_produce_a_confident_empty_result(es, monkeypatch):
    """The core pin. Whatever else happens, the caller must not be told the file is not there."""
    _run_returning(monkeypatch, DIRTY)
    res = E.search(".flp", max_results=10)
    assert not (res.ok and not res.paths), (
        "an undecodable byte produced ok=True with zero paths, which renders as "
        "'Everything answered, nothing found' -- a false negative in the words of a true one")


def test_the_lines_that_decode_are_still_returned(es, monkeypatch):
    """One bad filename must not cost the whole search. Two of the three paths in the fixture are
    plain ASCII and there is no reason the caller should lose them."""
    _run_returning(monkeypatch, DIRTY)
    res = E.search(".flp", max_results=10)
    assert len(res.paths) >= 2, f"one bad byte discarded the other results: {res.paths}"
    assert any("NewStuff.flp" in p for p in res.paths), \
        "the first, perfectly decodable path was lost with the bad one"


def test_the_repaired_name_is_itself_returned_not_quietly_dropped(es, monkeypatch):
    """ADDED AFTER MUTATION TESTING, which found this hole. Three deliberate breakages were run
    against the finished fix and two were caught; the survivor silently FILTERED OUT any line
    containing a replacement character. Every pin stayed green, because the fixture's other two
    paths are clean and the assertions above only required those to survive.

    Dropping the mangled name is the most tempting possible version of this bug: the output looks
    tidy, nothing is obviously wrong, and the file with the strange name becomes permanently
    invisible to the only tool that can find it. That file is precisely the one a human will
    struggle to locate by hand, so it is the one the index is most needed for. The notice says
    'Nothing was dropped' -- this is the pin that makes that sentence true.

    The mutation lived in the SEARCH path, not the renderer, so this pin drives the real one."""
    _run_returning(monkeypatch, DIRTY)
    res = E.search(".flp", max_results=10)
    assert len(res.paths) == 3, f"a path was dropped: {res.paths}"
    assert any("name.flp" in p for p in res.paths), \
        "the repaired name was filtered out of the results; 'Nothing was dropped' is then a lie"
    assert res.undecodable == 1, f"the repair count is wrong: {res.undecodable}"


def test_the_rendered_line_never_claims_nothing_was_found(es, monkeypatch):
    """The renderer is part of the contract: the defect was a SENTENCE, not a field."""
    _run_returning(monkeypatch, DIRTY)
    out = E.format_result(E.search(".flp", max_results=10))
    assert "nothing found" not in out.lower(), \
        f"still claims nothing was found when the answer merely could not be decoded: {out!r}"


# ---------------------------------------------------------------- P4: the loss is DECLARED
def test_a_repaired_name_is_declared_rather_than_repaired_silently():
    """Keeping a mangled path beats losing the search, but a replaced byte means the string no
    longer round-trips to a real file. A caller comparing it against a real path must be able to
    tell. Silent repair swaps a loud wrong answer for a quiet one."""
    res = E.SearchResult(query=".flp", paths=["C:\\Music\\bad\ufffdname.flp"], ok=True,
                         engine="everything")
    assert hasattr(res, "undecodable") or hasattr(res, "repaired_names"), \
        "SearchResult carries no way to say that some returned names were repaired"


def test_the_declaration_survives_into_the_rendered_output(es, monkeypatch):
    _run_returning(monkeypatch, DIRTY)
    out = E.format_result(E.search(".flp", max_results=10))
    assert any(w in out.upper() for w in ("UNDECODABLE", "REPAIRED", "NOT VALID UTF-8")), \
        f"the reader is not told that a name was repaired: {out!r}"


# ---------------------------------------------------------------- P6-P7: RATCHETS, do not regress
def test_a_clean_search_is_completely_unchanged(es, monkeypatch):
    """RATCHET. The fix must be invisible when nothing is wrong."""
    _run_returning(monkeypatch, CLEAN)
    res = E.search(".flp", max_results=10)
    assert res.ok and len(res.paths) == 2
    out = E.format_result(res)
    assert "2 match(es)" in out
    for w in ("UNDECODABLE", "REPAIRED"):
        assert w not in out.upper(), f"a clean search grew a {w} notice"


def test_a_genuinely_empty_result_still_says_nothing_found(es, monkeypatch):
    """RATCHET, and the one that keeps the fix honest. es.exe answering with zero lines is a REAL
    absence and must keep saying so -- otherwise the repair has only moved the lie."""
    _run_returning(monkeypatch, b"")
    res = E.search("zzz-no-such-file-anywhere", max_results=10)
    out = E.format_result(res)
    assert res.ok and not res.paths
    assert "nothing found" in out.lower(), \
        "a true empty result stopped reporting itself as empty; the fix overcorrected"
