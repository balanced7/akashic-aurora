"""PIN: the skills have ONE source, .agents/skills, and .claude/skills is a symlink to it.

The two trees were hand-kept copies and drifted (shader-craft existed only under .claude, and
akashic-memory's text differed between them). A symlink cannot drift. On Windows a checkout
without symlink support writes the link as a small text file, so Claude Code would see no
skills at all -- this pin turns that silent loss into a red test with the fix in its message.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINK = REPO / ".claude" / "skills"
SOURCE = REPO / ".agents" / "skills"

WINDOWS_FIX = (
    "On Windows: enable Developer Mode (or run git as admin), then "
    "`git config core.symlinks true` and `git checkout -- .claude/skills`."
)


def test_claude_skills_is_a_symlink():
    assert LINK.is_symlink(), f".claude/skills is not a symlink. {WINDOWS_FIX}"


def test_claude_skills_resolves_to_agents_skills():
    assert LINK.resolve() == SOURCE.resolve(), f".claude/skills points at {os.readlink(LINK)!r}"


def test_every_skill_has_a_skill_md():
    skills = [d for d in SOURCE.iterdir() if d.is_dir()]
    assert skills, ".agents/skills is empty"
    for d in skills:
        assert (d / "SKILL.md").is_file(), f"{d.name} has no SKILL.md"
