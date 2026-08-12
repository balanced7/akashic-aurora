"""Tracked-file discovery for the derived-doc generators.

WHY THIS EXISTS. The generators used to discover modules with os.listdir / Path.glob --
the WORKING TREE. So on a box holding untracked .py files they emitted rows for modules
the repository does not contain. A clean checkout regenerated without those rows, the
comprehensibility guardrail called the committed docs stale, and CI died there with every
later gate skipped behind it. Measured 2026-08-11/12: 15+ consecutive CI failures, across
three break -> fix -> break cycles, because regenerating the docs from a contaminated tree
cannot converge -- the pre-commit hook re-runs the same contaminated generation.

A derived doc is a claim about the REPOSITORY. It must be a function of tracked content
only, or two people at the same commit disagree about what the project contains.

WHY `git ls-files` AND NOT `git ls-tree HEAD`. ls-files is the INDEX: tracked content plus
anything staged for this commit. That is the right denominator for a pre-commit hook -- a
module being added in this very commit SHOULD appear in the docs the commit carries. HEAD
would lag by exactly one commit and reintroduce staleness from the other side.

NO SILENT FALLBACK. If git cannot answer, this raises. Falling back to os.listdir would
restore the original defect quietly, on exactly the machines where it is hardest to see --
which is the failure this module exists to end.
"""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TrackedLookupError(RuntimeError):
    """git could not report tracked files. Loud by design -- see module docstring."""


@lru_cache(maxsize=1)
def _tracked_paths() -> frozenset:
    """Every tracked/staged path, repo-relative with forward slashes. One git call."""
    try:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:      # git absent / unrunnable
        raise TrackedLookupError(
            f"cannot run `git ls-files` in {ROOT}: {e}. Derived docs describe TRACKED "
            f"content; generating from the filesystem instead would silently restore the "
            f"untracked-contamination defect this module exists to prevent.") from e
    if r.returncode != 0:
        raise TrackedLookupError(
            f"`git ls-files` failed in {ROOT} (exit {r.returncode}): {r.stderr.strip()[:300]}")
    return frozenset(line.strip() for line in r.stdout.splitlines() if line.strip())


def tracked_py(rel: str) -> list:
    """Sorted basenames of tracked .py files DIRECTLY in `rel` (no recursion, no __init__).

    Mirrors what the three generators each used to compute with os.listdir, so it is a
    drop-in for their discovery step and nothing downstream changes shape.
    """
    prefix = rel.replace("\\", "/").strip("/")
    prefix = f"{prefix}/" if prefix else ""
    out = []
    for p in _tracked_paths():
        if not p.startswith(prefix):
            continue
        tail = p[len(prefix):]
        if "/" in tail:                      # deeper than this directory
            continue
        if tail.endswith(".py") and tail != "__init__.py":
            out.append(tail)
    return sorted(out)


def tracked_py_count(rel: str) -> int:
    """Count of tracked .py directly in `rel`, excluding __init__.py."""
    return len(tracked_py(rel))


def is_tracked_dir(rel: str) -> bool:
    """True when the repo tracks at least one file at or below `rel`.

    Replaces os.path.isdir/Path.is_dir guards: a directory that exists only on this box
    (an untracked package, a stale build dir) is not part of the repository.
    """
    prefix = rel.replace("\\", "/").strip("/")
    if not prefix:
        return True
    return any(p == prefix or p.startswith(prefix + "/") for p in _tracked_paths())
