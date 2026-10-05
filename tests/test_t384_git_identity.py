"""Pins for git identity attribution -- t384's slice, SUPERSEDED IN PLACE by T411.

WHAT t384 PINNED, AND WHY IT IS GONE. The defect t384 closed (measured 2026-08-24) was real:
commit b66e6f67 was authored by a seat per the bus and the ledger, while git recorded the machine
owner, because seats commit through exec using the human's git config. t384's answer was to make
the SEAT the git author and leave the human as committer -- git's own who-wrote-it vs who-applied-it
distinction, on a non-routable `@akashic-aurora.local` address so a seat could never be mistaken
for a real account.

It was half right. git's author field is not only "who wrote this": it is what GitHub DISPLAYS on
every commit and what its contribution graph counts. One field was carrying two jobs, so the
attribution won and the operator's name lost -- 598 commits, 388 of them in his biggest month,
showing an address belonging to no account, and a contribution graph that went dark in the month
he worked hardest.

T411, DANIEL'S RULING 2026-09-26: "I want my name on it", and then, when a first pass left the
seat in the committer field: "How do we make it that my name shows up in the commiter field and
author field for the commits. our tracking for who does what is internal and if someone wants
that they can scrape for it. I want to restore the green boxes."

So BOTH fields are the operator, and attribution moved to an internal plane that is strictly
better at the job: state/authorship/seats.jsonl (scripts/authorship_ledger.py), keyed so it
survives a history rewrite. These pins are rewritten, not deleted, so that a later reader finds a
recorded decision rather than a silent reversal -- and so the t384 half that is STILL TRUE (fail
closed on an unknown id, shell safety, silence outside seat context, fail open on an unreadable
identity) keeps its coverage.

Run: py -m pytest tests/test_t384_git_identity.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OPERATOR = "balanced7"
OPERATOR_EMAIL = "61030820+balanced7@users.noreply.github.com"


# ---------------------------------------------------------------- the derivation


def test_both_identity_fields_are_the_operator():
    """THE T411 RULE. GitHub renders and credits BOTH fields, so a seat in either one costs a
    green box and prints a foreign name on the project page."""
    from core.comm.seat_identity import git_identity_env

    env = git_identity_env("dsh_agent")
    assert env["GIT_AUTHOR_NAME"] == OPERATOR
    assert env["GIT_AUTHOR_EMAIL"] == OPERATOR_EMAIL
    assert env["GIT_COMMITTER_NAME"] == OPERATOR
    assert env["GIT_COMMITTER_EMAIL"] == OPERATOR_EMAIL


def test_the_seat_never_reaches_a_git_identity_field():
    """SUPERSEDES test_identity_derives_from_agent_id and test_address_is_non_routable, which
    asserted the opposite. The seat id must not appear in any identity value for ANY seat --
    including the committer, which was the refused half-measure."""
    from core.comm.seat_identity import git_identity_env

    for agent in ("claude", "deepseek", "kimi", "dsh_agent", "sol"):
        env = git_identity_env(agent)
        assert env, f"{agent} produced no stamp at all"
        for key, value in env.items():
            assert agent not in value, f"{key} still carries the seat id: {value}"
            assert "akashic-aurora.local" not in value, f"{key} still carries a seat address"


def test_the_seat_is_recorded_somewhere_though():
    """Attribution is RELOCATED, not discarded -- the whole premise of the ruling. If the ledger
    plane ever disappears, this rule has quietly become 'erase who did the work'."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    ledger = root / "state" / "authorship" / "seats.jsonl"
    assert ledger.is_file(), "no authorship ledger: the seat record has nowhere to live"
    assert ledger.stat().st_size > 0, "the authorship ledger is empty"
    assert (root / "scripts" / "authorship_ledger.py").is_file(), "no door onto the ledger"


def test_empty_agent_id_yields_no_stamp():
    """STILL TRUE FROM t384. Fail-closed: an unidentified process must NOT get a fabricated
    identity -- it falls through to the human's git config, which is honest about not knowing."""
    from core.comm.seat_identity import git_identity_env

    assert git_identity_env("") == {}
    assert git_identity_env(None) == {}


def test_identity_is_shell_safe():
    """STILL TRUE FROM t384, and now trivially so since the values are constants rather than
    interpolated ids -- which is worth pinning precisely because it would be easy to reintroduce
    an id into a value later and not notice the injection surface came back."""
    from core.comm.seat_identity import git_identity_env

    env = git_identity_env("weird id;rm -rf<>\n")
    if env:
        for value in env.values():
            assert not any(c in value for c in ";<>\n")


# ---------------------------------------------------------------- the guard


def test_guard_passes_when_both_fields_are_the_operator(monkeypatch):
    from scripts.githooks import pre_commit

    monkeypatch.setattr(pre_commit, "_git_committer_ident", lambda: f"{OPERATOR} <{OPERATOR_EMAIL}>")
    ok, msg = pre_commit.check_author_matches_seat("dsh_agent", f"{OPERATOR} <{OPERATOR_EMAIL}>")
    assert ok, msg


def test_guard_refuses_a_seat_author(monkeypatch):
    """The inversion of the old test_guard_refuses_human_author_in_seat_context. What used to be
    the required state is now the refused one."""
    from scripts.githooks import pre_commit

    monkeypatch.setattr(pre_commit, "_git_committer_ident", lambda: f"{OPERATOR} <{OPERATOR_EMAIL}>")
    ok, msg = pre_commit.check_author_matches_seat("dsh_agent", "dsh_agent <dsh_agent@akashic-aurora.local>")
    assert not ok
    assert "dsh_agent" in msg  # names what it actually is
    assert OPERATOR in msg  # names who it should be
    assert "GIT_AUTHOR_NAME" in msg  # names the remedy, not just the drift


def test_guard_refuses_a_drifted_COMMITTER_even_when_the_author_is_right(monkeypatch):
    """The half-measure that was refused. GitHub renders and credits the committer too, so a
    correct author beside a seat committer still prints a foreign name and still costs a box."""
    from scripts.githooks import pre_commit

    monkeypatch.setattr(pre_commit, "_git_committer_ident", lambda: "claude <claude@akashic-aurora.local>")
    ok, msg = pre_commit.check_author_matches_seat("claude", f"{OPERATOR} <{OPERATOR_EMAIL}>")
    assert not ok, "a drifted committer passed"
    assert "COMMITTER" in msg


def test_guard_is_silent_outside_seat_context():
    """STILL TRUE FROM t384. A human committing at their own terminal has no AKASHIC_AGENT_ID;
    the guard must not touch them."""
    from scripts.githooks.pre_commit import check_author_matches_seat

    ok, _ = check_author_matches_seat("", "balanced7 <bal@example.com>")
    assert ok
    ok2, _ = check_author_matches_seat(None, "anyone <a@b.c>")
    assert ok2


def test_guard_fails_open_on_unreadable_author():
    """STILL TRUE FROM t384. A broken guard that blocks all work is worse than the drift it
    watches for."""
    from scripts.githooks.pre_commit import check_author_matches_seat

    ok, _ = check_author_matches_seat("claude", "")
    assert ok


def test_guard_fails_open_on_unreadable_committer(monkeypatch):
    """New surface, same policy: the committer probe is a second shell-out and it can fail on its
    own. An empty answer means 'could not read', which must not refuse a good commit."""
    from scripts.githooks import pre_commit

    monkeypatch.setattr(pre_commit, "_git_committer_ident", lambda: "")
    ok, _ = pre_commit.check_author_matches_seat("claude", f"{OPERATOR} <{OPERATOR_EMAIL}>")
    assert ok


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
