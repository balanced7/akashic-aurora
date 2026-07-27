"""PRE-REGISTERED ACCEPTANCE -- count reverts from git STRUCTURE, not from prose.

MEASURED 2026-07-27, and I caused it. The scorecard counts reverts with
`count(r"\\brevert")` over commit MESSAGE BODIES. Daniel asked that risky changes ship with a
way to undo them, so every commit I have written this arc ends with a "REVERT: ..." line. Live
result: ZERO actual reverts in the last 20 commits, and 20 of 20 messages containing the word.
The card reported a fleet that reverts constantly while nothing had been reverted at all.

This is a NEW SPECIES of the confident-zero family and the most insidious yet: the detector was
not stale and the world did not change. A GOOD PRACTICE was adopted, and the new writing
convention collided with an old regex. Nobody edited the detector; nobody broke anything; the
number silently inverted. Every message-regex detector carries this vulnerability, which is why
M1/M4/M5 now render [self-report] -- and why the revert count, which nothing labels, was the one
that actually misled.

The fix is to read what git KNOWS rather than what we WROTE. `git revert` writes a subject of
the form: Revert "<original subject>". That is structure, and prose in a body cannot forge it.

  P1  a body mentioning revert instructions is NOT counted (the live contamination)
  P2  a real git revert IS counted (subject form)
  P3  case and punctuation of prose never leak in
  P4  the reader fails open on a bad history read

Run: py -m pytest tests/test_revert_count_reads_structure.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p1_revert_instructions_in_a_body_are_not_reverts():
    from scripts import arc_scorecard as sc
    msg = ("A shell hook is a production entry point too\n\n"
           "REVERT: drop the reachable |= shell_invoked_modules() line in analyze().")
    assert not sc.is_revert(msg), (
        "a commit that merely EXPLAINS how to revert was counted as a revert -- 20 of 20 "
        "commits matched while zero reverts had occurred, because a good practice collided "
        "with an old regex")


def test_p2_a_real_git_revert_is_counted():
    from scripts import arc_scorecard as sc
    assert sc.is_revert('Revert "The scorecard now knows the difference between zero and blind"')


def test_p3_prose_cannot_forge_the_structure():
    from scripts import arc_scorecard as sc
    for msg in ("we reverted the thing by hand",
                "reverting is documented below",
                "REVERT: instructions here",
                "this commit is not a revert"):
        assert not sc.is_revert(msg), f"prose leaked into a structural count: {msg!r}"


def test_p4_a_bad_message_never_raises():
    from scripts import arc_scorecard as sc
    for bad in (None, "", "\n\n"):
        assert sc.is_revert(bad) is False
