"""RED-first pins for the t384 git-author attribution slice.

The defect these close (measured 2026-08-24): commit b66e6f67 was authored by a seat
(dsh_agent, per the bus and the ledger) but git recorded
`author=balanced7 <61030820+balanced7@users.noreply.github.com>` -- the machine owner --
because seats commit through exec using the human's git config. Git history is the one
plane where, contrary to house doctrine, the costume beat the id.

The sealed design (fences/t384-acl-instance-split/reconciliation.md, RULING 2):
  - the seam is the LAUNCHER, not a commit hook: git resolves authorship when it builds
    the commit object, so a prepare-commit-msg hook (half_a's proposal) cannot change the
    author of the commit already in flight;
  - AUTHOR becomes the seat, COMMITTER stays the human -- that is exactly git's own
    semantics (who wrote it vs who applied it) and it keeps the human's identity where it
    genuinely belongs;
  - the address is NON-ROUTABLE (`@akashic-aurora.local`) so a seat identity can never
    collide with, or be mistaken for, a real GitHub account;
  - a pre-commit guard REFUSES a seat-context commit whose author does not match, so the
    stamp cannot silently stop working (absence would otherwise be invisible -- the same
    class as the stale-plugin-generation lie caught the same night).

Run: py -m pytest tests/test_t384_git_identity.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------- the derivation

def test_identity_derives_from_agent_id():
    from core.comm.seat_identity import git_identity_env
    env = git_identity_env("dsh_agent")
    assert env["GIT_AUTHOR_NAME"] == "dsh_agent"
    assert env["GIT_AUTHOR_EMAIL"] == "dsh_agent@akashic-aurora.local"


def test_committer_is_never_stamped():
    """AUTHOR is the seat; COMMITTER stays whoever's machine applied it. Stamping the
    committer too would erase the human from history entirely -- the opposite error."""
    from core.comm.seat_identity import git_identity_env
    env = git_identity_env("claude")
    assert not any(k.startswith("GIT_COMMITTER") for k in env)


def test_address_is_non_routable():
    """A real address could collide with a GitHub account and mis-attribute to a person."""
    from core.comm.seat_identity import git_identity_env
    for agent in ("claude", "deepseek", "kimi", "dsh_agent"):
        assert git_identity_env(agent)["GIT_AUTHOR_EMAIL"].endswith("@akashic-aurora.local")


def test_empty_agent_id_yields_no_stamp():
    """Fail-closed: an unidentified process must NOT get a fabricated seat identity --
    it falls through to the human's git config, which is honest about not knowing."""
    from core.comm.seat_identity import git_identity_env
    assert git_identity_env("") == {}
    assert git_identity_env(None) == {}


def test_identity_is_shell_safe():
    """The value rides an env dict into a subprocess; a hostile or sloppy id must not be
    able to smuggle shell/format characters into git's author field."""
    from core.comm.seat_identity import git_identity_env
    env = git_identity_env("weird id;rm -rf<>\n")
    if env:  # either refuse, or sanitize -- never pass the raw string through
        assert not any(c in env["GIT_AUTHOR_NAME"] for c in ";<>\n")
        assert not any(c in env["GIT_AUTHOR_EMAIL"] for c in ";<>\n")


# ---------------------------------------------------------------- the guard

def test_guard_passes_when_author_matches_seat():
    from scripts.githooks.pre_commit import check_author_matches_seat
    ok, msg = check_author_matches_seat("dsh_agent", "dsh_agent <dsh_agent@akashic-aurora.local>")
    assert ok, msg


def test_guard_refuses_human_author_in_seat_context():
    """THE MEASURED DEFECT: agent id says a seat, git author says the machine owner."""
    from scripts.githooks.pre_commit import check_author_matches_seat
    ok, msg = check_author_matches_seat(
        "dsh_agent", "balanced7 <61030820+balanced7@users.noreply.github.com>")
    assert not ok
    assert "dsh_agent" in msg          # names who it SHOULD be
    assert "balanced7" in msg          # names who it actually is
    assert "GIT_AUTHOR_NAME" in msg    # names the remedy, not just the drift


def test_guard_is_silent_outside_seat_context():
    """A human committing at their own terminal has no AKASHIC_AGENT_ID; the guard must
    not touch them. Attribution truth is the goal, not universal stamping."""
    from scripts.githooks.pre_commit import check_author_matches_seat
    ok, _ = check_author_matches_seat("", "balanced7 <bal@example.com>")
    assert ok
    ok2, _ = check_author_matches_seat(None, "anyone <a@b.c>")
    assert ok2


def test_guard_fails_open_on_unreadable_author():
    """If git cannot report an author, the guard must not brick every commit -- a broken
    guard that blocks all work is worse than the drift it watches for (the house's own
    fail-open policy for commit-time guards)."""
    from scripts.githooks.pre_commit import check_author_matches_seat
    ok, _ = check_author_matches_seat("claude", "")
    assert ok


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
