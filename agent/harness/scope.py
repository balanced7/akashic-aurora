"""Repo-scoping policy shared by every harness adapter (Integration Tiers H0).

Hooks are registered user-globally (they fire for sessions launched from ANY cwd --
the read-bootstrap flow depends on that), so every adapter's first duty is deciding
whether an event belongs to THIS repo at all; outside it the adapter must be a
silent no-op, never blocking edits or injecting AI-Setup lessons into unrelated
projects. That decision is POLICY and lives here exactly once -- adapters translate
their runtime's payload shape into these predicates, they never re-implement them
(three drifting copies of _under_root is how this module was earned).

ENROLLED PROJECTS. An installed Aurora (the `aurora` launcher) runs from a release bundle, not
from a checkout anyone works in, so "inside the repo" would match nothing and every hook
would stay silent everywhere. A project is therefore ENROLLED to be treated exactly like the
repo: `hooks install --scope project` enrolls its project, `hooks enroll [--project P]`
enrolls one by hand, `hooks enroll --everywhere` opts every directory in. The list is
instance state (<data_root>/state/harness/scope.json); a checkout with no list behaves as it
always has.
"""

import json
import os

# agent/harness/scope.py -> repo root is three dirs up.
_ROOT_RAW = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.normcase(_ROOT_RAW)


def repo_root() -> str:
    """The repo root as a raw (original-case) absolute path."""
    return _ROOT_RAW


def enrolled_file() -> str:
    """Where the enrolled-project list lives (instance state, so upgrades keep it)."""
    try:
        from core.paths import data_root

        base = str(data_root())
    except Exception:
        base = (os.getenv("AI_SETUP") or "").strip() or _ROOT_RAW
    return os.path.join(base, "state", "harness", "scope.json")


def enrolled() -> dict:
    """{"roots": [abs paths], "everywhere": bool}. Unreadable or absent -> nothing enrolled."""
    try:
        with open(enrolled_file(), encoding="utf-8") as fh:
            doc = json.load(fh)
        roots = [str(r) for r in doc.get("roots") or [] if isinstance(r, str) and r]
        return {"roots": roots, "everywhere": bool(doc.get("everywhere"))}
    except (OSError, ValueError, AttributeError):
        return {"roots": [], "everywhere": False}


def _inside(a: str, root: str) -> bool:
    return a == root or a.startswith(root.rstrip(os.sep) + os.sep)


def _native(p: str) -> str:
    """git-bash spells D:\\x as /d/x; on Windows, read it as the drive path it names."""
    if os.name == "nt" and len(p) >= 3 and p[0] == "/" and p[1].isalpha() and p[2] == "/":
        return f"{p[1].upper()}:{p[2:]}"
    return p


def under_root(p: str) -> bool:
    """True iff `p` is the repo root or inside it, or inside an enrolled project
    (case-normalized, absolute)."""
    if not p:
        return False
    try:
        a = os.path.normcase(os.path.abspath(_native(p)))
    except Exception:
        return False
    if _inside(a, _ROOT):
        return True
    doc = enrolled()
    if doc["everywhere"]:
        return True
    return any(_inside(a, os.path.normcase(os.path.abspath(r))) for r in doc["roots"])


def is_home(p: str) -> bool:
    """The read-bootstrap flow launches from the user home dir EXACTLY. Children of home
    (Desktop/Projects/...) are other projects and must NOT match."""
    try:
        return os.path.normcase(os.path.abspath(p or "")) == os.path.normcase(os.path.expanduser("~"))
    except Exception:
        return False


def session_in_scope(cwd: str) -> bool:
    """Session-level scope: the repo itself, or the home-dir launch pad (read-bootstrap flow).
    Gates whole-session surfaces (auto-boot whisper, plan-time recall)."""
    return under_root(cwd) or is_home(cwd)


def file_in_scope(path: str) -> bool:
    """A file action (edit/write) belongs to this repo iff its TARGET lives under the root --
    the strongest signal; the session cwd is irrelevant."""
    return under_root(path or "")


def _root_spellings() -> tuple:
    """This checkout's path as a command may spell it, lowercased: native, forward-slash, and
    git-bash (/e/AI-Setup) for a Windows drive. Derived, so a clone anywhere is recognised --
    matching the literal 'ai-setup' only ever recognised one machine's folder name."""
    fwd = _ROOT_RAW.replace("\\", "/").rstrip("/").lower()
    out = {fwd, fwd.replace("/", "\\")}
    if len(fwd) > 1 and fwd[1] == ":":
        out.add(f"/{fwd[0]}{fwd[2:]}")
    return tuple(out)


def shell_in_scope(cwd: str, command: str) -> bool:
    """A shell action belongs to this repo iff the session cwd is inside it, or the command
    clearly invokes it (a path to this checkout / agent_cli.py). In a project-launched session
    both branches are naturally True."""
    if under_root(cwd or ""):
        return True
    cl = (command or "").lower()
    if "agent_cli.py" in cl or any(r in cl for r in _root_spellings()):
        return True
    # the installed launcher: `aurora <verb>` invokes Aurora from anywhere
    return cl.startswith("aurora ") or any(f"{sep}aurora " in cl for sep in (" ", ";", "&", "|", "(", "/"))
