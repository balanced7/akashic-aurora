"""Repo-scoping policy shared by every harness adapter (Integration Tiers H0).

Hooks are registered user-globally (they fire for sessions launched from ANY cwd --
the read-bootstrap flow depends on that), so every adapter's first duty is deciding
whether an event belongs to THIS repo at all; outside it the adapter must be a
silent no-op, never blocking edits or injecting AI-Setup lessons into unrelated
projects. That decision is POLICY and lives here exactly once -- adapters translate
their runtime's payload shape into these predicates, they never re-implement them
(three drifting copies of _under_root is how this module was earned).
"""
import os

# agent/harness/scope.py -> repo root is three dirs up.
_ROOT_RAW = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.normcase(_ROOT_RAW)


def repo_root() -> str:
    """The repo root as a raw (original-case) absolute path."""
    return _ROOT_RAW


def under_root(p: str) -> bool:
    """True iff `p` is the repo root or inside it (case-normalized, absolute)."""
    if not p:
        return False
    try:
        a = os.path.normcase(os.path.abspath(p))
    except Exception:
        return False
    return a == _ROOT or a.startswith(_ROOT + os.sep)


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


def shell_in_scope(cwd: str, command: str) -> bool:
    """A shell action belongs to this repo iff the session cwd is inside it, or the command
    clearly invokes it (an AI-Setup path / agent_cli.py). In a project-launched session both
    branches are naturally True."""
    if under_root(cwd or ""):
        return True
    cl = (command or "").lower()
    return "ai-setup" in cl or "agent_cli.py" in cl
