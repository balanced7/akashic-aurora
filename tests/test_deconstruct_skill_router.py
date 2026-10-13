"""Pins for the deconstruct skill's router and every repo path it names (review defect D1, 2026-10-13).

The deconstruct skill (.claude/skills/deconstruct/) is an umbrella: its router sends work to sibling skills
(reverse-engineering, shader-craft's "Dissecting a shader" section, root-cause-before-fixes, verified-done) and its
text cites repo files as evidence. The review found that the skill's own self-check ("every repo path exists")
passed against the working tree, while three of six outside routes existed only in another workflow's
uncommitted work: a fresh clone would have had dead routes. Existing on this disk is not the same as shipping.

So these pins check what a clone would see:
  1. every repo path named in the skill's Markdown exists in the working tree (FAIL if not: a dead route);
  2. every such path is tracked by git (`git ls-files`). While a target is still untracked the test SKIPS,
     naming the target and what to commit first. A skip is deliberately not a pass: it is the honest state
     while a sibling workflow's files wait to be committed, and it turns green only once git tracks them;
  3. a path-like token that is not a repo path must be on the explicit EXTERNAL list below (another
     repository, a URL scheme, a git ref, or a private plane), so a typo cannot hide as "external";
  4. the private planes the skill names are git-ignored, so they can never become tracked by accident;
  5. the shader-craft section the router names exists, and is committed (skip with the reason otherwise);
  6. the reverse-engineering skill points back to deconstruct (skip with the reason while it does not: that
     file belongs to the reverse-engineering workflow, which owns the fix).

Read-only by construction: the only git commands are `ls-files`, `check-ignore` and `show HEAD:<path>`, run with
--no-optional-locks. Nothing here imports the house (no `core.*`), so the file runs with or without conftest.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".claude" / "skills" / "deconstruct"
SKILL_REL = PurePosixPath(".claude/skills/deconstruct")

# The router's outside routes, as the review listed them. If the extractor stops finding any of these, the
# parser broke (or the router changed): either way the pin must say so instead of passing on an empty set.
ROUTER_ROUTES = (
    ".claude/skills/reverse-engineering/SKILL.md",
    ".claude/skills/reverse-engineering/references/method-legal-cleanroom.md",
    "docs/pillar-analysis-method.md",
    ".claude/skills/root-cause-before-fixes/SKILL.md",
    ".claude/skills/verified-done/SKILL.md",
    ".claude/skills/shader-craft/SKILL.md",
)

SHADER_SKILL = ".claude/skills/shader-craft/SKILL.md"
SHADER_SECTION_RE = re.compile(r"^#+\s*Dissecting a shader\b", re.MULTILINE)
RE_SKILL = ".claude/skills/reverse-engineering/SKILL.md"

# Path-like tokens that are deliberately NOT paths in this repo. Each prefix carries its reason.
EXTERNAL = {
    "akashiclabs-site/": "the website's own repository (a separate checkout), not this repo",
    "http://": "a URL scheme",
    "https://": "a URL scheme",
    "origin/": "a git remote-tracking ref, not a path",
    "private/": "a private plane: named by role only, and it must stay git-ignored (see the ignore pin)",
}
PRIVATE_PLANES = ("private/",)

_TOKEN_RE = re.compile(r"`([^`\n]+)`")
_PATHLIKE_RE = re.compile(r"[A-Za-z0-9_.\-/:,]+")
_LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*$")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _git_ready() -> bool:
    if shutil.which("git") is None:
        return False
    r = _git("rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


if not _git_ready():
    pytest.skip("not a git checkout (or git is missing): tracking cannot be checked here",
                allow_module_level=True)

_TRACKED = [line for line in _git("ls-files").stdout.splitlines() if line]
_TOP_LEVEL = {line.split("/", 1)[0] for line in _TRACKED}


def _skill_markdown() -> list[Path]:
    return sorted(SKILL_DIR.rglob("*.md"))


def _classify(md: Path, token: str):
    """Return ("repo", rel_posix) | ("external", prefix) | ("unknown", token) | None for a backticked token."""
    if not _PATHLIKE_RE.fullmatch(token):
        return None                                   # prose, a command, a key pattern, a Windows path
    for prefix in EXTERNAL:
        if token.startswith(prefix):
            return ("external", prefix)
    path = _LINE_SUFFIX_RE.sub("", token)
    if path.startswith(("references/", "../", "./")):
        base = PurePosixPath(md.parent.relative_to(ROOT).as_posix())
        parts: list[str] = []
        for part in (base / path).parts:
            if part == "..":
                parts.pop()
            elif part != ".":
                parts.append(part)
        rel = "/".join(parts) + ("/" if path.endswith("/") else "")
        return ("repo", rel)
    first = path.split("/", 1)[0]
    if first in _TOP_LEVEL:
        return ("repo", path)
    if "/" in path:
        return ("unknown", token)                     # path-shaped, but neither repo nor declared external
    return None                                       # a bare word such as a flag value or a file name


def _named(kind: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for md in _skill_markdown():
        where = md.relative_to(ROOT).as_posix()
        for token in _TOKEN_RE.findall(md.read_text(encoding="utf-8")):
            c = _classify(md, token)
            if c and c[0] == kind:
                found.setdefault(c[1], []).append(where)
    return found


NAMED_REPO_PATHS = _named("repo")


def _is_tracked(rel: str) -> bool:
    rel = rel.rstrip("/")
    return any(t == rel or t.startswith(rel + "/") for t in _TRACKED)


def test_the_skill_files_exist():
    assert (SKILL_DIR / "SKILL.md").is_file(), "the deconstruct skill is missing"
    assert _skill_markdown(), "no Markdown found under the deconstruct skill"


def test_extractor_finds_every_router_route():
    missing = [r for r in ROUTER_ROUTES if r not in NAMED_REPO_PATHS]
    assert not missing, (f"the router routes {missing} were not found among the paths the skill names; "
                         "either the router changed (update ROUTER_ROUTES) or the extractor broke")


@pytest.mark.parametrize("rel", sorted(NAMED_REPO_PATHS), ids=lambda r: r)
def test_named_path_exists_and_is_tracked(rel):
    where = ", ".join(sorted(set(NAMED_REPO_PATHS[rel])))
    assert (ROOT / rel).exists(), f"{where} names `{rel}`, which does not exist: a dead route or citation"
    if not _is_tracked(rel):
        pytest.skip(f"UNTRACKED, so not a pass: `{rel}` (named in {where}) exists on this disk but git does "
                    "not track it, so a fresh clone would not have it. Commit it together with, or before, "
                    "the deconstruct skill.")


def test_no_undeclared_path_like_tokens():
    unknown = _named("unknown")
    assert not unknown, ("path-shaped tokens that are neither repo paths nor declared EXTERNAL (a typo, or a "
                         f"new outside path that needs a reason in EXTERNAL): {unknown}")


@pytest.mark.parametrize("plane", PRIVATE_PLANES)
def test_private_planes_the_skill_names_are_git_ignored(plane):
    assert plane in _named("external"), f"the skill no longer names `{plane}`; update PRIVATE_PLANES"
    r = _git("check-ignore", "-q", plane)
    assert r.returncode == 0, f"`{plane}` is a private plane but git does not ignore it"


def test_router_shader_section_exists_and_is_committed():
    text = (ROOT / SHADER_SKILL).read_text(encoding="utf-8")
    assert SHADER_SECTION_RE.search(text), f"`{SHADER_SKILL}` has no 'Dissecting a shader' section"
    head = _git("show", f"HEAD:{SHADER_SKILL}")
    if head.returncode != 0 or not SHADER_SECTION_RE.search(head.stdout):
        pytest.skip(f"UNCOMMITTED, so not a pass: the 'Dissecting a shader' section of `{SHADER_SKILL}` exists "
                    "only as a working-tree edit; HEAD does not have it. Commit the shader-craft section "
                    "together with, or before, the deconstruct skill.")


def test_reverse_engineering_skill_links_back_to_deconstruct():
    p = ROOT / RE_SKILL
    if not p.exists():
        pytest.skip(f"`{RE_SKILL}` is absent; the back-link cannot be checked")
    if "deconstruct" not in p.read_text(encoding="utf-8").lower():
        pytest.skip(f"ONE-WAY LINK, so not a pass: `{RE_SKILL}` never mentions the deconstruct umbrella. That "
                    "file belongs to the reverse-engineering workflow; ask it to add a one-line pointer back.")
