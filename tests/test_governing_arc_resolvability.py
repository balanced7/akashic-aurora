"""The governing arc is asserted without the resolvability check built for exactly it.

MEASURED 2026-09-23 across three boots with different tasks: every one printed

    # Governing arc: docs/drill-arc-48cfd5.md  (from note 'drill-arc-status')

and no file matching *drill-arc* exists anywhere in the repository. The line carries no
[MOVED?], no [STALE?], nothing. A seat's first instruction about what governs its work
points at a document that is not there, silently, on every boot.

What makes this worth a pin rather than a one-line patch is WHERE the fix already lived.
agent_cli.py holds two statements of the same law, 250 lines apart:

  _grounding_exists (built 2026-07-25, deepseek fence F1) --
      "A dangling first instruction is the most expensive line in the whole boot."
      It resolves the pointer, tags [MOVED?] when it dangles, and is deliberately safe
      on prose: a pointer must look file-ish (a slash AND an extension) before it is
      ever claimed missing, so "C1/C2 design" and "G0-G5" cannot produce a false alarm.

  the Governing arc render --
      "a confidently-wrong 'Governing arc:' line is worse than an honest
       'no arc governs'."
      Which is the same sentence. It never calls _grounding_exists.

One author built the checker. The other wrote the law in a comment. That gap is the
house's dominant ergonomic defect in miniature, and unlike some neighbours (see
tests/test_watcher_kill_warrant_identity.py, where the adjacent predicate shared the
defect and borrowing it would have been a disaster) THIS neighbour is correct, tested,
and directly applicable.

These pins are written against a small _arc_line() renderer mirroring _grounding_line(),
so the line is testable rather than buried mid-function.

Run:  py -m pytest tests/test_governing_arc_resolvability.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import agent_cli


def _arc_line():
    fn = getattr(agent_cli, "_arc_line", None)
    if fn is None:
        pytest.fail(
            "agent_cli._arc_line(pointer, note_title) does not exist. The Governing arc "
            "line is rendered inline and never resolves its pointer, while "
            "_grounding_line does exactly that 250 lines above it."
        )
    return fn


def test_a_dangling_arc_pointer_is_flagged():
    """The live defect: a path that resolves to nothing must say so."""
    line = _arc_line()("docs/drill-arc-48cfd5.md", "drill-arc-status")
    assert "MOVED?" in line, (
        "a governing-arc pointer naming a nonexistent file rendered as authoritative"
    )


def test_a_resolving_arc_pointer_is_not_flagged():
    """The guard must be silent when the document is actually there."""
    line = _arc_line()("docs/CONDUCT.md", "some-status")
    assert "MOVED?" not in line
    assert "docs/CONDUCT.md" in line


def test_prose_is_never_claimed_missing():
    """deepseek's F1 fence, inherited: a pointer must look file-ish before it can be
    called dangling. 'C1/C2 design' has a slash and is not a path."""
    for prose in ("C1/C2 design", "G0-G5", "the drill arc", "wave 2 / wave 3"):
        assert "MOVED?" not in _arc_line()(prose, "n"), f"false alarm on prose: {prose!r}"


def test_the_note_title_survives_so_the_arc_is_still_findable():
    """A flagged pointer must still say which note claimed it -- the note is how you
    find where the arc actually went."""
    line = _arc_line()("docs/drill-arc-48cfd5.md", "drill-arc-status")
    assert "drill-arc-status" in line


def test_the_boot_render_uses_the_checked_renderer():
    """Source pin, deliberately narrow: the authoritative branch must not hand-format
    the line again and bypass the check."""
    import inspect

    # Look at the CALL SITE, not at any line mentioning the phrase -- _arc_line's own
    # return statement contains it, and this pin's first draft matched that and went red
    # against a correct fix. A source grep must exclude the definition it is testing.
    body = inspect.getsource(agent_cli).split("def _arc_line", 1)
    outside = body[0] + body[1].split("\ndef ", 1)[-1] if len(body) > 1 else body[0]

    assert "lines.append(_arc_line(" in outside, (
        "the authoritative Governing arc branch does not go through _arc_line"
    )
    handrolled = [ln for ln in outside.splitlines()
                  if "lines.append(f\"# Governing arc:" in ln and "from note" in ln]
    assert not handrolled, (
        f"an arc line is still hand-formatted and bypasses the check: {handrolled!r}"
    )
