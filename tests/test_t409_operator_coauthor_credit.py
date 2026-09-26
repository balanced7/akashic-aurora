"""T409 pins -- a seat-authored commit must credit the operator, or his graph goes dark.

MEASURED 2026-09-26. T384 makes the seat the AUTHOR and leaves the operator as COMMITTER.
GitHub builds its contribution graph from the AUTHOR, and `<seat>@akashic-aurora.local`
resolves to no account:

    2026-07   1282 authored by the operator
    2026-08    731 operator + 210 seat
    2026-09      0 operator + 382 seat        <- his biggest month, credited to nobody

GitHub's API on our own commits: `author_login: UNMATCHED, committer_login: balanced7`, and
where the seat is also the committer, both are UNMATCHED.

A Co-authored-by trailer is counted for every co-author GitHub can resolve. It is additive:
t384 is untouched, the seat stays the author. These pins hold the four properties that make
it safe to run on EVERY commit.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.githooks import coauthor  # noqa: E402


def _fake_run(email):
    class _Out:
        stdout = f"seat Name <{email}> 1790000000 -0400"
    return lambda *a, **k: _Out()


def _msg(tmp_path, text):
    p = tmp_path / "COMMIT_EDITMSG"
    p.write_text(text, encoding="utf-8")
    return p


def test_seat_authored_commit_gains_the_trailer(tmp_path):
    """The whole point: a seat-authored message must come out crediting the operator."""
    p = _msg(tmp_path, "find: land the paging pin\n")
    note = coauthor.ensure_operator_coauthor(p, run=_fake_run("claude@akashic-aurora.local"))
    out = p.read_text(encoding="utf-8")
    assert note, "the hook reported no action on a seat-authored message"
    assert f"Co-authored-by: {coauthor.OPERATOR}" in out, out
    assert out.startswith("find: land the paging pin"), "the subject line must be untouched"


def test_it_is_idempotent(tmp_path):
    """Amends and rebases re-run the hook. A message must never grow a trailer per attempt."""
    p = _msg(tmp_path, "roster: one connection per read\n")
    run = _fake_run("deepseek@akashic-aurora.local")
    coauthor.ensure_operator_coauthor(p, run=run)
    coauthor.ensure_operator_coauthor(p, run=run)
    coauthor.ensure_operator_coauthor(p, run=run)
    assert p.read_text(encoding="utf-8").lower().count("co-authored-by:") == 1


def test_operator_authored_commit_is_left_alone(tmp_path):
    """When he IS the author the graph already counts him; a self-credit would be noise."""
    p = _msg(tmp_path, "docs: fix a typo\n")
    before = p.read_text(encoding="utf-8")
    note = coauthor.ensure_operator_coauthor(p, run=_fake_run(coauthor.OPERATOR_EMAIL))
    assert note is None
    assert p.read_text(encoding="utf-8") == before


def test_it_never_raises_and_never_blocks(tmp_path):
    """A credit line must not be able to refuse a good commit.

    Two ways this hook could brick every commit in the repo: the author probe throwing, and
    the message file being unreadable. Both must degrade to None, never to an exception."""
    def boom(*a, **k):
        raise RuntimeError("git is not available")
    p = _msg(tmp_path, "some work\n")
    assert coauthor.ensure_operator_coauthor(p, run=boom) is None
    assert coauthor.ensure_operator_coauthor(tmp_path / "does-not-exist") is None


def test_git_comment_lines_survive(tmp_path):
    """git appends its own '#' guidance to the message file; the trailer must sit ABOVE it,
    or the trailer lands in the part git strips and the credit silently disappears."""
    p = _msg(tmp_path, "a subject\n\n# Please enter the commit message.\n# On branch master\n")
    coauthor.ensure_operator_coauthor(p, run=_fake_run("kimi@akashic-aurora.local"))
    out = p.read_text(encoding="utf-8")
    trailer_at = out.index("Co-authored-by:")
    first_comment = out.index("# Please enter")
    assert trailer_at < first_comment, "the trailer must precede git's comment block\n" + out


def test_the_carve_out_is_documented(tmp_path):
    """The house rule is 'no Co-Authored-By trailers'. This one is the exception BECAUSE it
    credits the operator rather than a vendor. If the module ever stops saying so, a future
    seat reading only the rule will strip it."""
    src = Path(ROOT, "scripts", "githooks", "coauthor.py").read_text(encoding="utf-8")
    assert "CARVE-OUT" in src, "the exception must be stated where the next seat will read it"
    for vendor in ("Claude", "Anthropic"):
        assert f"Co-authored-by: {vendor}" not in src, f"{vendor} must never be credited here"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
