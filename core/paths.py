"""paths -- where this repo lives, DERIVED rather than configured.

THE DEFECT THIS REPLACES (measured 2026-08-01, after a deploy at a second machine failed):
    710 occurrences of the literal E:\\AI-Setup across 238 tracked files
     83 of them UNCONDITIONAL in executable code (.py/.ps1/.bat) -- hard failure elsewhere
      8 guarded by os.getenv("AI_SETUP", r"E:\\AI-Setup")
      0 machines with AI_SETUP actually set -- including the original one

That last line is the whole argument. An env var is a thing a human must remember on every
machine, and this repo already ran the experiment: the escape hatch was designed, shipped, and
then never set even on the box it was written on. So every "portable" call site was quietly
running on the hardcoded fallback, and nothing revealed it until the repo was copied somewhere
whose path differed.

CONFIGURATION YOU MUST REMEMBER IS NOT PORTABILITY. It is a hardcoded path with an extra step.

THE FIX: the root is COMPUTABLE. Every module knows its own __file__; walking up to a marker
that only the repo root has gives the answer on any drive, any directory, any machine, with
nothing to set up. AI_SETUP remains as an OVERRIDE for genuinely unusual deployments (a
relocated data dir, a test harness pointing at a fixture tree) -- an override is a fine thing
to have and a terrible thing to depend on.

WHY TWO MARKERS AND NOT `.git`: a deployment can arrive as a zip, an export, or a worktree
whose .git is a FILE rather than a directory. agent_cli.py + core/ identify this repo without
assuming how it got here.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping, Optional

# Files/dirs that together identify the repo root and nothing else.
_MARKERS = ("agent_cli.py", "core")

_cached: Optional[Path] = None


def _cache_enabled() -> bool:
    """T069: a module-level singleton must honour test isolation or it leaks across tests.

    The first isolated test to resolve a root would otherwise pin it for every later test in
    the same process -- including ones that deliberately point at a fixture tree. Caching is
    a production nicety here (one filesystem walk per process), never a correctness
    requirement, so under isolation we simply recompute.
    """
    return not os.environ.get("_AISETUP_TEST_ISOLATED")


def _looks_like_root(p: Path) -> bool:
    try:
        return all((p / m).exists() for m in _MARKERS)
    except OSError:
        return False


def repo_root(start: Optional[str] = None, *, use_env: bool = True) -> Path:
    """The repo root. Order: AI_SETUP override -> derived from this file -> cwd walk.

    Never raises: a path helper that throws during import takes down every door that imports
    it, and the failure then looks like something else entirely.
    """
    global _cached

    if use_env:
        env = (os.getenv("AI_SETUP") or "").strip()
        if env:
            p = Path(env)
            if _looks_like_root(p):
                return p
            # An AI_SETUP that does not point at a repo is a MISCONFIGURATION, not a reason to
            # give up -- fall through to derivation and let `doctor` be the thing that says so.

    if start is None and _cached is not None and _cache_enabled():
        return _cached

    here = Path(start).resolve() if start else Path(__file__).resolve()
    for cand in (here, *here.parents):
        if _looks_like_root(cand):
            if start is None and _cache_enabled():
                _cached = cand
            return cand

    # Last resort: the cwd chain. Covers a script executed from an odd location with this
    # module reached by an installed path rather than an in-tree one.
    cwd = Path.cwd().resolve()
    for cand in (cwd, *cwd.parents):
        if _looks_like_root(cand):
            return cand

    # Nothing identifiable. Return the two-levels-up guess rather than raising, and let the
    # caller's own existence checks fail with a message about the thing they wanted.
    return Path(__file__).resolve().parents[1]


def _git_primary_root(root: Path) -> Optional[Path]:
    """Return the primary checkout behind a linked worktree, if Git can name it."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            close_fds=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        common = Path(result.stdout.strip())
        if not common.is_absolute():
            common = root / common
        common = common.resolve()
        return common.parent if common.name.lower() == ".git" else None
    except (OSError, subprocess.SubprocessError):
        return None


def _family_base(root: Path) -> Path:
    """Strip a conventional world suffix while preserving the caller's actual family name."""
    low = root.name.lower().replace("_", "-")
    for suffix in ("-alpha", "-beta", "-sandbox"):
        if low.endswith(suffix):
            return root.with_name(root.name[:-len(suffix)])
    return root


def world_checkout_root(
    world: str,
    *,
    root: Optional[Path] = None,
    current_world: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Discover a world's code checkout without encoding this host's drive layout.

    Order is explicit ``AKASHIC_<WORLD>_ROOT`` override, the current checkout when it
    represents the requested world, then the Git primary checkout / conventional sibling
    family. Invalid explicit overrides fail visibly as ``None`` instead of silently falling
    back to a different body.
    """
    aliases = {"sandbox": "beta"}
    world = aliases.get(str(world).strip().lower(), str(world).strip().lower())
    if world not in {"prod", "beta", "alpha"}:
        return None

    env = os.environ if env is None else env
    override = (env.get(f"AKASHIC_{world.upper()}_ROOT") or "").strip()
    if override:
        candidate = Path(override).resolve()
        return candidate if _looks_like_root(candidate) else None

    root = Path(root or repo_root()).resolve()
    current_world = aliases.get(str(current_world or "").strip().lower(),
                                str(current_world or "").strip().lower())
    if current_world == world and _looks_like_root(root):
        return root

    bases = []
    primary = _git_primary_root(root)
    if primary is not None:
        bases.append(_family_base(primary))
    bases.append(_family_base(root))

    suffix = {"prod": "", "beta": "-Beta", "alpha": "-Alpha"}[world]
    seen = set()
    for base in bases:
        candidate = base if not suffix else base.with_name(base.name + suffix)
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        if _looks_like_root(candidate):
            return candidate.resolve()
    return None


def root_str() -> str:
    """String form, for the many call sites that build paths with os.path.join."""
    return str(repo_root())


def env_override_is_wrong() -> Optional[str]:
    """AI_SETUP set but not pointing at a repo -> the reason, else None.

    Split out so `doctor` can REPORT it. A silently ignored misconfiguration is how a broken
    deploy looks healthy: the code quietly derives the right root, the operator believes their
    env var is in effect, and the next thing that reads AI_SETUP directly disagrees.
    """
    env = (os.getenv("AI_SETUP") or "").strip()
    if not env:
        return None
    p = Path(env)
    if not p.exists():
        return f"AI_SETUP={env!r} does not exist"
    if not _looks_like_root(p):
        missing = [m for m in _MARKERS if not (p / m).exists()]
        return f"AI_SETUP={env!r} is not a repo root (missing: {', '.join(missing)})"
    return None
