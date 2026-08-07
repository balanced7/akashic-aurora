"""T218 RED: `ask --with` tells the HELPER its evidence was clipped, but not the CALLER.

FOUND WHILE USING IT, 2026-08-07. I asked a grounded question about three Redis key
families in core/comm/bus.py. The answer came back full of "not visible in the provided
snippet" and "does not appear anywhere in the 743-line excerpt", and family 3 -- the one at
bus.py:1201 -- was reported as absent from the file it plainly lives in.

The door is HONEST where it counts most: build_context appends
`[TRUNCATED at 40000 chars of 80052; you are seeing a PARTIAL file -- say so if it limits
your answer]`, and the helper obeyed it exactly, flagging its own window. That is good
design and it worked.

THE GAP IS THE OTHER BOUNDARY. The caller's footer prints tokens, spend, elapsed and model
-- and says nothing about the clip. So a truncation-caused abstention is INDISTINGUISHABLE
from a genuine absence at the surface the human reads, and the reader's natural conclusion
is "the code isn't there". That is inferring absence, delivered by the tool, to the one
person in the loop who cannot see the evidence.

`detail["context"]` already carries {"truncated": True, "included": [...]}. Nothing reads it.

The law this pins is W137's, one door over: a clip is only safe if the party who will draw
a conclusion from it is told. Being honest to the model and silent to the human is half a
guarantee.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run(args, **kw):
    return subprocess.run([sys.executable, "agent_cli.py", *args], cwd=REPO,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120, **kw)


def test_build_context_marks_truncation_in_its_meta():
    """Precondition: the data the caller needs already exists and is correct."""
    sys.path.insert(0, str(REPO))
    from core.comm.ask import build_context

    ctx, meta = build_context(["core/comm/bus.py"], root=str(REPO))
    assert meta["truncated"] is True, "bus.py is ~80k chars; it must clip at the 40k budget"
    assert "TRUNCATED" in ctx, "the HELPER's in-band notice is the half that already works"
    inc = meta["included"][0]
    assert inc["truncated"] is True and inc["chars"] < 80000


def test_caller_is_told_when_its_evidence_was_clipped():
    """THE PIN. Ask a question over a file that must clip, and require the caller-facing
    output to say so.

    Uses --help-adjacent plumbing rather than a live model call: the render is what is under
    test, not the helper. A clipped-evidence notice must name the file and both sizes, so
    the reader can decide whether the answer's silence is about the code or about the window.
    """
    sys.path.insert(0, str(REPO))
    from core.comm.ask import build_context, clipped_evidence_notice

    _, meta = build_context(["core/comm/bus.py"], root=str(REPO))
    notice = clipped_evidence_notice(meta)
    assert notice, "evidence was clipped and the caller-facing notice was empty"
    assert "bus.py" in notice, "a clip notice that does not name the file is unactionable"
    assert "40000" in notice and "80052" in notice, \
        "must state how much was shown OF how much, not merely that something was cut"
    low = notice.lower()
    assert "absen" in low or "missing" in low or "not there" in low, (
        "the notice must warn that an abstention may be about the WINDOW rather than about "
        "the code -- that inference is the whole failure being prevented")


def test_no_notice_when_nothing_was_clipped():
    """A warning that fires on clean runs is noise, and noise gets filtered out mentally --
    which is how the real one gets missed."""
    sys.path.insert(0, str(REPO))
    from core.comm.ask import build_context, clipped_evidence_notice

    _, meta = build_context(["core/outcome.py"], root=str(REPO))
    assert meta["truncated"] is False, "precondition: outcome.py fits in the budget"
    assert clipped_evidence_notice(meta) == ""
