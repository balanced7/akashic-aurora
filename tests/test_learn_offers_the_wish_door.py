"""RED pins: W237 -- `learn` must offer the wish door, because filing a lesson is the moment
you have conceded the tool.

THE WISH'S RECEIPT. In the 2026-10-02 01:05-07:25 window: 11 invocations of `agent_cli.py
learn`, 0 of `agent_cli.py wish`. At least five of those lessons name a tool defect in their
own text. Every one is a wish wearing a lesson's clothes. The cost of each miss is not the
unfiled wish, it is the INVERSION: a lesson teaches the next seat to tolerate the defect, so
the defect survives and is paid for again every session.

THE PRECEDENT is in the same function -- cmd_learn already prints a conditional sibling-door
hint for `tag-anti-pattern`. This is the same shape in the same slot.

I DEPARTED FROM THE WISH'S OWN FIX SHAPE, AND THE NUMBERS ARE WHY. W237 (which I wrote) says
to gate on `--category correction` AND the result text naming a tool, door, flag, command or
output format. Measured against all 1,560 corpus lessons before building:

    gate                                  fires     dead seats
    A  category=correction                8%        deepseek, kimi
    B  W237 as written (A AND names-tool)  2%        deepseek, kimi, dsh_agent
    C  names-a-tool AND defect-language    8%        codex
    D  A OR C                             16%        none

W237 as written fires on 28 of 1,560 lessons and on exactly the handful it was reasoned from.
That is the overfit-to-your-own-examples failure in its purest form: it would have passed any
test written from its own description and done nothing in production.

Worse, and this is the part that decided the design: `correction` is a per-seat HABIT, not a
house convention. claude 5%, sol 31%, codex 45%, dsh_agent 6% -- and deepseek 0 of 174, kimi
0 of 106. A category-only gate means the feature does not exist for Heimdall or Navi. Content
alone has the mirror hole: it never fires for codex, whose lessons are terse.

So the gate is the OR. 16% is roughly one hint per six lessons -- not a nag, and the only
option with no dead seat. Both halves are pinned below, because a later simplification that
drops either one silently re-opens a hole for two seats.

WHAT IS NOT PINNED HERE. The anti-pattern hint this is modelled on has no pins of its own --
I found none in the suite. I have not added any; that is someone's lane and a separate slice.

ON THE CONTENT REGEX. A pattern-based guard is a claim about a format, and the house already
has a lesson about those rotting silently. This one claims only our own prose, which we
control, but both sides are still pinned: tests below cover the FALSE-NEGATIVE side (a
tool complaint that must fire) and the FALSE-POSITIVE side (a lesson that merely mentions a
command and must stay silent), because an unpinned widening is unfalsifiable.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from core.learning.learning_store import wish_candidate

REPO = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------ gate A: category
def test_a_correction_lesson_is_wish_shaped():
    """Gate A. 8% of the corpus, and the half that covers sol/codex/codex_root."""
    got = wish_candidate(category="correction", result="the door never told us",
                         experiment="some_lesson")
    assert got, "a correction lesson produced no wish candidate"
    assert got.get("why") == "correction", got


# ------------------------------------------------------------------ gate C: content
def test_a_tool_defect_outside_the_correction_category_still_fires():
    """Gate C, AND THE WHOLE REASON THIS IS NOT W237-AS-WRITTEN. deepseek filed 174 lessons
    and kimi 106 with `category=correction` ZERO times between them. If the only gate is the
    category, this feature does not exist for either of them. This is a real deepseek-shaped
    lesson: uncategorized, and a plain tool complaint."""
    got = wish_candidate(
        category="uncategorized",
        tried="ran py agent_cli.py bifrost-sync --consume to clear the backlog",
        result="it printed (no messages consumed) while its own peek said 60+ unread, so the "
               "remedy silently cleared nothing and neither surface said so",
        experiment="consume_clears_nothing")
    assert got, ("a plain tool complaint produced no candidate -- with a category-only gate "
                 "this feature is dead for deepseek (0/174) and kimi (0/106)")
    assert got.get("why") == "names-a-defect-in-a-tool", got


def test_an_empty_category_does_not_block_the_content_gate():
    """Lessons arrive with no category at all; 826 of 1,560 are 'uncategorized'."""
    got = wish_candidate(category="", result="the verb cannot be reached from a seat and the "
                                             "flag is silently ignored", experiment="x")
    assert got, "the content gate must not require a category to be present"


# ------------------------------------------------------------------ precision
def test_an_ordinary_lesson_stays_silent():
    """A hint that fires on everything is wallpaper, and the precedent's own comment says so:
    'high-signal, no nag'."""
    got = wish_candidate(category="architecture",
                         tried="sharded the index by agent",
                         result="lookups got faster and the shards stayed balanced",
                         experiment="shard_by_agent")
    assert not got, "fired on a lesson with no tool complaint at all: %r" % (got,)


def test_merely_naming_a_command_is_not_a_complaint():
    """THE FALSE-POSITIVE PIN. Nearly every lesson in this corpus names a command somewhere.
    Naming one is not conceding it -- without this the gate degenerates to 'always'."""
    got = wish_candidate(category="method",
                         tried="used py agent_cli.py recall-bench to score the eval set",
                         result="the bench reported 22% recall@1 and the ceiling block worked "
                                "exactly as designed",
                         experiment="bench_scored_fine")
    assert not got, "fired on a lesson that merely USES a tool successfully: %r" % (got,)


# ------------------------------------------------------------------ the draft
def test_the_draft_carries_the_lesson_slug_so_the_wish_is_traceable():
    got = wish_candidate(category="correction", result="the door silently lost the row",
                         experiment="the_door_silently_lost_the_row")
    assert "the_door_silently_lost_the_row" in got.get("body", ""), got.get("body")


def test_the_draft_carries_the_lessons_own_words_not_a_template():
    """Removing the composition cost is the whole point -- the precedent auto-drafts a slug for
    the same reason. A draft that says 'describe the friction' has removed nothing.

    STRENGTHENED AFTER A MUTATION SURVIVED IT. The first version passed a lesson with only a
    `result` and asserted a phrase from it appeared in the body. That phrase ALSO becomes the
    headline, so replacing the RESULT field with a template left the pin green -- it was
    measuring the headline and reporting on the body. Each field now carries a distinct
    sentinel so no one field can stand in for another."""
    got = wish_candidate(
        category="correction",
        tried="RAN-THE-DOOR eight times concurrently",
        result="SIX-OF-FORTY vanished while every process printed filed and exited 0",
        recommendation="LOCK-THE-DOOR before the read",
        root_cause="UNLOCKED-RMW on a shared file",
        experiment="wish_door_loses_wishes")
    body = got.get("body", "")
    for sentinel, field in (("RAN-THE-DOOR", "tried"), ("SIX-OF-FORTY", "result"),
                            ("LOCK-THE-DOOR", "recommendation"), ("UNLOCKED-RMW", "root_cause")):
        assert sentinel in body, "the draft dropped the lesson's %s field:\n%s" % (field, body)
    assert "describe" not in body.lower(), "the draft is asking the seat to write it: " + body


def test_nothing_in_the_draft_needs_shell_escaping():
    """W213: prose through the shell is a standing defect in this house, and the whole reason
    the hint hands back --text-file. A draft that must be pasted inline re-opens it."""
    body = wish_candidate(category="correction",
                          result="backticks ` and $(subshells) and 'quotes' in the prose",
                          experiment="e").get("body", "")
    assert body, "no draft produced"
    # the CONTRACT is that the body goes to a FILE; the hint must never hand back inline prose
    got = wish_candidate(category="correction", result="x", experiment="e")
    assert "--text-file" in got.get("command_hint", ""), got


# ------------------------------------------------------------------ robustness
def test_the_headline_names_the_friction_not_the_advice():
    """FOUND BY DOGFOODING, NOT BY A PIN. The first live draft opened with "Use when building
    or trusting ANY harness..." -- a correct sentence and a useless wish title. House
    recommendations are written in the recall-trigger format and start with "Use when", so
    preferring `recommendation` for the headline reliably produces advice where a wish needs
    friction. Order is root_cause, then result, then tried, then recommendation last."""
    body = wish_candidate(
        category="correction",
        tried="ran the harness",
        result="it reported six of six surviving and every one was wrong",
        recommendation="Use when building any harness that judges a test run",
        root_cause="the detector matched output text instead of reading the exit code",
        experiment="e").get("body", "")
    first = body.splitlines()[0]
    assert not first.lower().startswith("use when"), \
        "the wish opens with trigger-format advice instead of the friction: " + first
    assert "exit code" in first, "the headline should name the cause: " + first


def test_missing_fields_never_throw():
    """This runs inside cmd_learn AFTER the lesson is already recorded. It must never be able
    to turn a successful capture into a traceback."""
    for kwargs in ({}, {"category": None}, {"result": None, "tried": None},
                   {"category": "correction", "experiment": None}):
        wish_candidate(**kwargs)


# ------------------------------------------------------------------ the wiring
def test_cmd_learn_reaches_for_the_helper():
    """Names the intended fix, so a refactor that drops the call fails with WHICH piece is
    missing rather than only that the hint went quiet.

    TIGHTENED AFTER A MUTATION SLIPPED PAST IT. A bare `"wish_candidate" in body` is a
    SUBSTRING test, so it stayed true when the import was mutated to
    `import draft_anti_pattern_slug as wish_candidate_UNUSED` -- a wiring that NameErrors at
    runtime. The end-to-end pin caught that; this one did not, and a pin whose whole job is
    naming the missing piece must not be the loose one. Word-boundary, and both halves."""
    import re as _re
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8")
    start = src.index("def cmd_learn(")
    body = src[start:src.index("\ndef ", start + 1)]
    assert _re.search(r"import\s+wish_candidate\b", body), \
        "cmd_learn does not import wish_candidate by that name"
    assert _re.search(r"\bwish_candidate\s*\(", body), \
        "cmd_learn imports wish_candidate but never calls it"


def test_a_real_learn_prints_the_wish_hint_end_to_end(tmp_path):
    """The pins above measure the decision; this measures the DOOR. Safe to run live because
    conftest's isolate_canonical redirects AI_SETUP and REDIS_DB=15 through os.environ, which
    a subprocess inherits -- so this writes to the test db, never the real corpus."""
    assert os.environ.get("_AISETUP_TEST_ISOLATED") == "1", \
        "refusing to run a live `learn` without conftest isolation -- it would pollute the corpus"
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "learn", "t-seat",
         "--experiment", "pin_w237_end_to_end",
         "--category", "correction",
         "--tried", "called the door",
         "--result", "the door silently dropped the row and exited 0",
         "--success", "yes"],
        capture_output=True, text=True, cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "wish" in out.lower(), "learn recorded but never offered the wish door:\n" + out
    assert "--text-file" in out, "the hint must hand back the SAFE form:\n" + out


def test_the_hint_is_silent_under_json():
    """--json is a machine contract; the precedent hint honours it and so must this."""
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "learn", "t-seat",
         "--experiment", "pin_w237_json", "--category", "correction",
         "--result", "the door silently dropped the row", "--success", "yes", "--json"],
        capture_output=True, text=True, cwd=str(REPO),
        env={**os.environ, "PYTHONUTF8": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    json.loads(r.stdout.strip().splitlines()[-1])    # must still be parseable
    assert "[wish]" not in r.stdout, "the hint leaked into --json output:\n" + r.stdout
