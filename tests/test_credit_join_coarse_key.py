"""The CREDIT JOIN is blind to 98% of failures, and the blindness is a key-shape bug.

THE DEFECT, measured on real data (scripts/measure_target_join.py, 2026-10-06):
17,606 of 18,024 distinct `recall:outcome` keys (97.7%) are `c:` COMMAND keys. A command
key is the WHOLE LITERAL command string, lowercased and whitespace-collapsed
(`normalize_target`, core/recall/at_action.py:988). The credit loop then joins on that key
three times -- `_set_outcome`, `_get_outcome`, `_impressions_for` -- all by exact equality.

So consider the only interesting case in the whole system, an agent fixing its own mistake:

    py agent_cli.py boot claude --taks "x"     -> FAIL   (key A)
    py agent_cli.py boot claude --task "x"     -> SUCCESS (key B, A != B)

The FAIL is filed under A and the SUCCESS asks about B. They never meet. No flip, no
credit, and -- worse -- no record that a lesson prevented anything. A FIXED COMMAND CAN
NEVER JOIN ITS OWN EARLIER FAILURE. The 115 failures in the session that motivated this,
113 of them on commands, could not close the loop even in principle.

WHY THE FIX IS A SECOND AXIS AND NOT A COARSER `normalize_target`. The obvious move --
make the primary key coarser -- is wrong, and a pinned contract already says so:
`core/recall/replay.py:128 parse_target` INVERTS `normalize_target` to replay a historical
target through the live matcher, and `tests/test_forge_replay.py:85` pins that inversion.
Coarsening the primary key would feed the replay bench truncated commands while reporting
success. Twenty-odd other call sites share that key shape too.

So `coarse_target` is an ADDITIONAL join axis, and every credit it wins is STAMPED with
the axis that won it (`join`: "exact" | "coarse"). That stamp is the point. Credit here is
already assigned "with no causal check" (core/recall/prevention.py:57); a coarser key
raises recall AND raises false joins, so a sensor that cannot say which axis fired would
trade one blindness for a quieter one. With the stamp, the coarse share is auditable and
the exact path stays byte-for-byte what it was.

  J1  coarse_target drops flags and their values -- the two spellings above agree
  J2  it drops the house `cd <repo> &&` prefix and pipeline tails
  J3  it drops heredoc BODIES (a 40-line heredoc is not an identity)
  J4  it keeps identity: different executable or different file argument NEVER join
  J5  a path key needs no second axis, and neither does an already-minimal command
  J6  THE LOOP CLOSES: fail on one spelling, succeed on another, the lesson is credited
  J7  the credit names the axis that won it, and the exact path still reports "exact"
  J8  consume-on-credit still holds across the axes -- one flip cannot be farmed twice
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import at_action


def _sid():
    return "jointest-" + uuid.uuid4().hex[:10]


def _c(cmd):
    return at_action.normalize_target(command=cmd)


# ---------------------------------------------------------------- the coarsener

def test_j1_flags_and_their_values_are_dropped():
    """The typo case, which is the whole reason this slice exists."""
    bad = at_action.coarse_target(_c('py agent_cli.py boot claude --taks "memory reach"'))
    good = at_action.coarse_target(_c('py agent_cli.py boot claude --task "memory reach"'))
    assert bad and bad == good, "a flag typo must not change the join key"
    assert "--task" not in good and "--taks" not in good
    assert "memory" not in good, "a flag VALUE is not identity either"
    assert good.endswith("boot claude"), f"the action survives coarsening: {good!r}"


def test_j2_cd_prefix_and_pipeline_tail_are_dropped():
    """`cd /e/AI-Setup && real-command | head -40` is the house's own idiom."""
    plain = at_action.coarse_target(_c("py scripts/measure_target_join.py"))
    dressed = at_action.coarse_target(
        _c("cd /e/AI-Setup && py scripts/measure_target_join.py --json | tail -40"))
    assert plain and plain == dressed, f"{plain!r} != {dressed!r}"


def test_j3_heredoc_bodies_are_dropped():
    a = _c("cat > notes.txt <<'EOF'\nfirst body\nEOF")
    b = _c("cat > notes.txt <<'EOF'\na completely different body\nEOF")
    ca, cb = at_action.coarse_target(a), at_action.coarse_target(b)
    assert ca and ca == cb, "the heredoc BODY is payload, not identity"


def test_j4_identity_is_preserved_different_actions_never_join():
    """The false-credit guard. Coarsening that collapses real actions is worse than
    blindness, because a false join credits a lesson for a success it never caused."""
    assert at_action.coarse_target(_c("py scripts/a.py")) \
        != at_action.coarse_target(_c("py scripts/b.py")), "different file args"
    assert at_action.coarse_target(_c("py agent_cli.py boot claude")) \
        != at_action.coarse_target(_c("py agent_cli.py learn claude")), "different subcommand"
    assert at_action.coarse_target(_c("pytest tests/x.py")) \
        != at_action.coarse_target(_c("py tests/x.py")), "different executable"


def test_j5_no_second_axis_when_one_is_not_needed():
    """Empty string means "no coarse axis" -- paths already join exactly, and a command
    with nothing to drop must not be filed twice under two identical keys."""
    assert at_action.coarse_target(at_action.normalize_target(path=__file__)) == ""
    assert at_action.coarse_target(_c("pytest")) == ""
    assert at_action.coarse_target("") == ""
    assert at_action.coarse_target("garbage-with-no-tag") == ""


# ---------------------------------------------------------------- the loop closing

def test_j6_the_credit_loop_closes_across_two_spellings(monkeypatch):
    """THE SLICE. This is the assertion the whole night is for."""
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    failed = _c('py agent_cli.py boot claude --taks "x"')
    fixed = _c('py agent_cli.py boot claude --task "x"')
    assert failed != fixed, "precondition: the exact keys genuinely differ"

    at_action.mark_impression(sid, failed, ["learn:experiment:the_lesson"])
    at_action.resolve_action_outcome(sid, failed, False)        # the typo fails
    res = at_action.resolve_action_outcome(sid, fixed, True)    # the fix succeeds

    assert res["flipped"] is True, "a fixed command must join its own earlier failure"
    assert res["credited"] == 1, "and the lesson surfaced at the failure must be credited"
    assert res["sources"] == ["learn:experiment:the_lesson"]


def test_j7_the_credit_names_the_axis_that_won_it(monkeypatch):
    """Provenance. A coarse credit must be distinguishable from an exact one, forever."""
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)

    sid = _sid()
    at_action.mark_impression(sid, _c("py x.py --a 1"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("py x.py --a 1"), False)
    coarse = at_action.resolve_action_outcome(sid, _c("py x.py --a 2"), True)
    assert coarse["join"] == "coarse", f"won on the new axis: {coarse!r}"

    sid2 = _sid()
    tgt = _c("py y.py")
    at_action.mark_impression(sid2, tgt, ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid2, tgt, False)
    exact = at_action.resolve_action_outcome(sid2, tgt, True)
    assert exact["flipped"] is True and exact["join"] == "exact", \
        "the pre-existing path is unchanged and still says so"

    staged = at_action.session_outcomes(sid)
    assert staged and staged[-1].get("join") == "coarse", \
        "the durable outcome record carries the axis too, or the audit is impossible"


def test_j8_consume_on_credit_holds_across_the_axes(monkeypatch):
    """One flip, one credit. The coarse axis must not become a farm."""
    calls = []
    monkeypatch.setattr(at_action, "record_feedback",
                        lambda src, *a, **k: calls.append(src) or True)
    sid = _sid()
    at_action.mark_impression(sid, _c("py z.py --a 1"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("py z.py --a 1"), False)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 2"), True)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 3"), False)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 4"), True)
    assert calls == ["learn:experiment:l"], f"credited more than once: {calls}"


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
