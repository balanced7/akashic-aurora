"""T340 RED: read_file must slice before it truncates, and confess when a range is empty.

FOUND BY HEIMDALL UNDER LOAD, 2026-08-17. Asked to independently verify T275 -- the first
verification this house could make, because T248 needs a non-owner and claude owns most rows --
he could not read the ledger row he was being asked to judge. He reconstructed it field by
field through grep, delivered the verdict anyway, and then named the gap in his own report:
"a verifier needs a read tool that can return the ledger row it's being asked to judge."

THE MECHANISM, at core/comm/toolbox.py read_file:

    raw = p.read_bytes()
    text = raw[:MAX_FILE_BYTES].decode(...)      # the cap is applied to the INPUT
    if start_line or end_line:
        lines = text.splitlines()                # the slice runs on what SURVIVED

The byte cap eats the file before the line range is ever consulted.

MEASURED, not inferred: MAX_FILE_BYTES is 120,000. state/coord/tasks.json is 646,935 bytes.
T275's row begins at byte offset 510,416 -- 4.25x past the cap. So the decoded text holds
roughly the first 2,000 lines, `lines[10224:10240]` indexes past its end, and the call returns
"" -- which the final `or "(empty file)"` then renders as an EMPTY FILE.

That is the severity: not a refusal, not a truncation notice, but a silent WRONG ANSWER that
names the wrong cause. A reader is told the file is empty. And the tool's own description says
"Prefer start_line/end_line for big files to save tokens" -- it advertises exactly the
capability it cannot deliver, which is the names-that-lie class standing at a door.

This degrades every seat reading any file over 120KB: the ledger, the corpus index, any long
design doc. Heimdall hit it while doing the one job nobody else in this house can do.

Run: py -m pytest tests/test_t340_read_file_slices_before_it_truncates.py -q
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import toolbox as TB  # noqa: E402


@pytest.fixture()
def box(tmp_path):
    return TB.ToolBox(tmp_path, allow_exec=False, trust="member",
                      allow_secrets=False, confirm=None)


# 17,777 rather than a round 20,000 ON PURPOSE. The first draft used 20000 and P3 asserted
# "20000" in the output -- which passed against the UNFIXED code, because the failure message
# reads "[truncated at 120000 bytes]" and 120000 CONTAINS 20000. A pin that goes green on a
# substring coincidence is worse than no pin: it reports coverage it does not have. Three of
# these six passed for that shape of reason before this correction, which is the same
# text-matching blindness this session hit three times already.
_N = 17777


def _big(tmp_path, name="big.txt", lines=_N):
    """A file whose interesting content lives well past MAX_FILE_BYTES, like the ledger."""
    p = tmp_path / name
    p.write_text("\n".join(f"line-{i:05d} " + "x" * 40 for i in range(1, lines + 1)),
                 encoding="utf-8")
    assert p.stat().st_size > TB.MAX_FILE_BYTES * 2, "fixture must exceed the cap"
    return p


def test_p1_a_range_past_the_byte_cap_returns_the_actual_lines(box, tmp_path):
    """THE WHOLE SLICE, and Heimdall's blocker exactly. The requested lines live far beyond the
    byte cap; the tool must reach them."""
    _big(tmp_path)
    out = box.execute("read_file", {"path": "big.txt", "start_line": 15000, "end_line": 15002})
    assert "line-15000" in out, (
        "the byte cap ate the file before the slice ran -- the requested range was never "
        "reachable, which is what forced a verifier to grep a ledger row by hand")
    assert "line-15002" in out and "line-15003" not in out


def test_p2_it_does_not_claim_an_empty_file(box, tmp_path):
    """The worst part of the bug is not that it fails -- it is that it names the wrong cause.
    A reader told '(empty file)' stops looking."""
    _big(tmp_path)
    out = box.execute("read_file", {"path": "big.txt", "start_line": 15000, "end_line": 15002})
    assert "(empty file)" not in out, "a 700KB file must never be reported as empty"
    # POSITIVE assertion: the first draft only checked for the absence of a string, which the
    # unfixed code satisfied by returning a bare truncation notice. Absence-of-a-lie is not
    # presence-of-the-truth.
    assert "line-15001" in out, "the requested content must actually be there"


def test_p3_an_out_of_range_request_confesses_with_the_real_line_count(box, tmp_path):
    """T176's law at a read door: absence must never read as a decision. Asking for a line
    past the end is a real answer -- 'that line does not exist, there are N' -- and it is not
    the same answer as 'the file is empty'."""
    _big(tmp_path)
    out = box.execute("read_file", {"path": "big.txt", "start_line": 99999, "end_line": 99999})
    assert "(empty file)" not in out
    assert str(_N) in out, (
        f"an out-of-range range must name the file's real line count ({_N}) so the caller can "
        f"correct the request rather than conclude the content is gone")


def test_p4_the_whole_file_path_still_truncates_and_confesses(box, tmp_path):
    """The guard against over-correcting. Reading a huge file with NO range must stay bounded
    and must still say it was bounded -- that behaviour is correct and is not what broke."""
    _big(tmp_path)
    out = box.execute("read_file", {"path": "big.txt"})
    assert "truncated" in out.lower(), "the whole-file read must still confess its bound"
    assert len(out) <= TB.MAX_FILE_BYTES + 2000


def test_p5_an_oversized_SLICE_result_is_bounded_and_says_so(box, tmp_path):
    """A range can itself exceed the cap. The bound must move to the RESULT rather than
    disappear -- otherwise fixing the slice would remove the protection entirely."""
    _big(tmp_path)
    out = box.execute("read_file", {"path": "big.txt", "start_line": 1, "end_line": 20000})
    assert len(out) <= TB.MAX_FILE_BYTES + 2000, "a huge slice must still be bounded"
    assert "truncated" in out.lower(), "and must confess that it was"


def test_p6_the_ledger_row_that_started_this_is_reachable():
    """The live case, not a fixture: the exact call Heimdall could not make. Skipped rather
    than failed if the ledger has moved, because this pin asserts a capability, not a line."""
    ledger = Path(ROOT) / "state" / "coord" / "tasks.json"
    if not ledger.exists() or ledger.stat().st_size <= TB.MAX_FILE_BYTES:
        pytest.skip("ledger absent or no longer exceeds the cap")
    box = TB.ToolBox(Path(ROOT), allow_exec=False, trust="member",
                     allow_secrets=False, confirm=None)
    total = sum(1 for _ in open(ledger, encoding="utf-8", errors="replace"))
    mid = total // 2
    out = box.execute("read_file", {"path": "state/coord/tasks.json",
                                    "start_line": mid, "end_line": mid + 2})
    # POSITIVE assertion again: a bare "[truncated at ...]" notice is non-empty and contains no
    # "(empty file)", so the weaker form of this pin passed against the broken code. The ledger
    # is JSON, so real content from its middle must carry a quote or a brace.
    assert ('"' in out or "{" in out or "}" in out), (
        "the middle of the ledger must be READABLE through the door a verifier actually has -- "
        "not merely non-empty")
