"""T338 RED: a handoff briefing must never arrive clipped mid-thought.

DANIIL, 2026-08-17: "why are things still clipping, how do we get around that, I thought we
fixed this."

NOT A REGRESSION, and that matters for the fix. The cap at agent_cli.py:4663 --
`_intake(args.note, 1000, "note", clipped)` -- is deliberate, and the door behaves perfectly:
it spills the full original to state/spill/, confesses in its result, and leaves an in-band
marker. `_intake` was built for the RB-5 class (a silent clip corrupting durable knowledge
while the caller is told [OK]) and it closes that class properly.

THE DEFECT IS NARROWER AND IT IS REAL, on two counts:

  (a) A HANDOFF IS A BRIEFING. For most capped fields a clip is survivable -- a truncated
      `context` still helps. A briefing that ends mid-sentence is worse than a short one,
      because the reader cannot tell what was lost or judge whether to go looking.

  (b) THE RECOVERY PATH IS INVISIBLE TO THE ONE READER IT EXISTS FOR. The spill lands in
      state/spill/<file>.txt. `boot` never reads state/spill/. So the full text survives on
      disk in a place the next seat -- the entire audience for a handoff -- will not find.

WHY A WRITING DISCIPLINE IS NOT THE FIX, evidenced. The filed lesson
`a_cap_you_know_about_still_needs_the_body_written_to_fit` already records two prior sessions
burned by exactly this, and its own recommendation is "write the body to the cap FIRST." That
lesson fired at me tonight, by accident, on an unrelated call -- AFTER I had already overrun
the cap twice, and I still needed a third attempt to fit. Three overruns in one session by
the author of the lesson is the proof: a rule that must be remembered at compose time will
not be.

THE FIX. On overflow the full body is written to a durable project-scoped NOTE, and the
stored field LEADS with the pointer so it survives any further truncation and is the first
thing the reader sees. Notes are verified project-scoped rather than per-agent
(`note deepseek --get <title>` resolves a note written by claude), so the pointer works for
any target. Falls back to today's file spill if the note write fails -- a door must not die
because a store was unreachable.

Run: py -m pytest tests/test_t338_handoff_briefing_not_clipped.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()


def _briefing_fn():
    """The helper under test, whatever it ends up called -- resolved by contract, not name,
    so the pin does not fail merely because the fix chose a different word."""
    import agent_cli
    for cand in ("_briefing_intake", "_intake_briefing", "_handoff_note_intake"):
        fn = getattr(agent_cli, cand, None)
        if callable(fn):
            return fn
    return None


def test_p1_a_briefing_helper_exists_and_is_distinct_from_intake():
    """_intake stays as-is for context/focus/task, where a clip is survivable. The briefing
    path needs its own behaviour, not a widened cap -- widening only moves the cliff."""
    fn = _briefing_fn()
    assert fn is not None, (
        "no briefing-intake helper found; the handoff note path must not share _intake's "
        "clip-and-spill-to-file behaviour")


def test_p2_an_over_cap_briefing_leads_with_a_resolvable_pointer(tmp_path, monkeypatch):
    """THE WHOLE SLICE. The pointer must be FIRST -- not appended -- so it survives any
    further truncation downstream and is the first thing a tired reader sees."""
    fn = _briefing_fn()
    assert fn is not None
    body = "X" * 9000
    confessions: list = []
    out = fn(body, 1000, "note", confessions, to_agent="claude", by_agent="claude")
    assert len(out) <= 1000, "the stored field must still respect the cap"
    head = out[:200].lower()
    assert "note" in head and "--get" in out[:300], (
        "the stored briefing must OPEN with the retrieval command, not end with it")


def test_p3_the_confession_names_the_note_not_only_a_file():
    """state/spill/ is invisible to boot, which is the reader a handoff exists for. The
    confession must point at something that reader can actually reach."""
    fn = _briefing_fn()
    assert fn is not None
    confessions: list = []
    fn("Y" * 5000, 1000, "note", confessions, to_agent="claude", by_agent="claude")
    joined = " ".join(confessions).lower()
    assert joined, "an overflowing briefing must confess"
    assert "note" in joined, (
        "the confession must name the NOTE that holds the full body -- a state/spill path "
        "alone tells the writer where it went and the reader nothing")


def test_p4_under_cap_briefings_are_untouched():
    """The guard against over-correcting: the common case must not grow a pointer, a note,
    or any ceremony at all."""
    fn = _briefing_fn()
    assert fn is not None
    confessions: list = []
    short = "a complete short briefing"
    assert fn(short, 1000, "note", confessions, to_agent="claude", by_agent="claude") == short
    assert confessions == [], "an under-cap briefing must confess nothing"


def test_p5_a_store_failure_degrades_and_never_raises():
    """A door must not die because a store was unreachable. The fallback is today's
    behaviour -- file spill plus confession -- which is honest, just less reachable."""
    import agent_cli
    fn = _briefing_fn()
    assert fn is not None
    def _boom(*a, **k):
        raise RuntimeError("store down")
    monkey = getattr(agent_cli, "get_agent_memory", None)
    assert monkey is not None, "expected get_agent_memory to be the note seam"
    agent_cli.get_agent_memory = _boom          # type: ignore[assignment]
    try:
        confessions: list = []
        out = fn("Z" * 4000, 1000, "note", confessions, to_agent="claude", by_agent="claude")
        assert isinstance(out, str) and len(out) <= 1100
        assert confessions, "a degraded path must still confess"
    finally:
        agent_cli.get_agent_memory = monkey     # type: ignore[assignment]
