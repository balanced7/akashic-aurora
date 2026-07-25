"""Pins: the flip nudge must not claim a corpus gap it never checked for.

THE INCIDENT, 2026-07-25, self-inflicted and caught the same hour.
A Write failed then succeeded. The PostToolUse flip nudge said:

    "No stored lesson helped here -- if the fix generalizes, this is a corpus gap worth
     filling."

I filled it. One call later, recall surfaced `write_tool_needs_read_tool` -- a lesson that
already said exactly what I had just written. The corpus was never short. The lesson simply
had not SURFACED for that target, because relevance is keyed on the file path and a
tool-mechanics lesson matches no path.

So the prompt was wrong, and by being wrong it caused the corpus to grow a duplicate. The
instrument degraded the thing it was measuring (lesson:
corpus_gap_signal_conflates_absent_with_unsurfaced).

THE CONFLATION. `credited == 0` is true in three disjoint cases:
    (a) nothing relevant exists                 -> a real corpus gap
    (b) something relevant exists but did not surface for this target
    (c) something surfaced and simply was not credited
Only (a) is a gap. The old text asserted (a) unconditionally.

THE RULE THESE PINS ENFORCE: never claim a gap without probing for one, and when the probe
cannot run, say NOTHING about gaps rather than guessing. Same discipline as the census
NOTHING-CHECKED line, the FileStore preservation-failure branch, and the anchor resolver's
STARVED state -- report what was checked, never imply what was not.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.recall.at_action import build_learn_nudge  # noqa: E402


def test_credited_flip_is_unchanged():
    out = build_learn_nudge("p:x", 2, ["learn:experiment:a", "learn:experiment:b"])
    assert "earned 'helped' credit" in out
    assert "corpus gap" not in out


def test_no_candidates_may_claim_a_gap():
    """A probe that ran and found nothing is the ONLY licence to say 'gap'."""
    out = build_learn_nudge("p:x", 0, [], probe=lambda _t: [])
    assert "corpus gap" in out


def test_candidates_present_must_not_claim_a_gap():
    """The exact 2026-07-25 case: a lesson existed, did not surface, and a gap was claimed."""
    out = build_learn_nudge("p:x", 0, [], probe=lambda _t: ["write_tool_needs_read_tool"])
    assert "corpus gap" not in out, "claimed a gap while relevant lessons exist"
    assert "write_tool_needs_read_tool" in out, "must name what it found so the agent can check"
    assert "duplicate" in out.lower(), "must warn that writing now risks a duplicate"


def test_no_probe_means_no_gap_claim_at_all():
    """Cannot check => say nothing about gaps. Silence beats a guess."""
    out = build_learn_nudge("p:x", 0, [])
    assert "corpus gap" not in out, "claimed a gap with no probe -- the original defect"


def test_a_broken_probe_is_survivable_and_still_silent_on_gaps():
    """Hot path: a probe fault must never break the nudge, and never license a gap claim."""
    def boom(_t):
        raise RuntimeError("probe exploded")
    out = build_learn_nudge("p:x", 0, [], probe=boom)
    assert out, "the nudge must still render"
    assert "corpus gap" not in out


def test_the_learn_command_survives_every_branch():
    """Whatever it says about gaps, the capture affordance must remain."""
    for probe in (None, (lambda _t: []), (lambda _t: ["x"])):
        out = build_learn_nudge("p:x", 0, [], probe=probe) if probe else \
              build_learn_nudge("p:x", 0, [])
        assert "learn" in out, "the pre-filled capture command must always be offered"
