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

TWO QUESTIONS, TWO RESOLVERS (2026-09-07, defer 951a9944f6). "Where is the CODE" and "where
does INSTANCE STATE live" are different questions with different validation. repo_root() is
marker-validated because a wrong code root means a wrong docs/, scripts/ and store/docs, so
it must never follow AI_SETUP into a directory that is not this repo. data_root() is the
override the paragraph above promised -- a relocated data dir, a fixture tree -- and a data
dir is not a repo, so it carries NO marker check. Merging the two (e30a8517) made every
instance-state default silently ignore the bare temp dir tests/isolate_canonical.py sets:
the FILE half of test isolation was a no-op for two weeks, and live lessons bled into
"empty" test stores while every reader believed the store was isolated.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

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
    """The CODE root. Order: AI_SETUP override (only if it IS a repo) -> derived from this
    file -> cwd walk. For session_logs/, coordinator_logs/ and every other piece of instance
    state use data_root(): a bare data dir is REJECTED here by design.

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


def root_str() -> str:
    """String form, for the many call sites that build paths with os.path.join."""
    return str(repo_root())


def data_root() -> Path:
    """Where INSTANCE STATE lives: session_logs/, coordinator_logs/, chronicle output, the
    default FileStore/FileLedger files, the legacy learnings.jsonl.

    A set AI_SETUP ALWAYS wins here, whether or not it looks like a repo -- that is the whole
    point of the override (a relocated data dir, a test harness's throwaway tree), and a data
    dir has no agent_cli.py or core/ to validate against. Unset, instance state lives beside
    the code, exactly as before. Read per call and never cached: the lookup is cheap, and a
    cached override is the T069 singleton leak all over again.
    """
    env = (os.getenv("AI_SETUP") or "").strip()
    if env:
        return Path(env)
    return repo_root()


def data_root_str() -> str:
    """String form of data_root(), for os.path.join call sites."""
    return str(data_root())


def env_override_is_wrong() -> Optional[str]:
    """AI_SETUP set but not pointing at a repo -> the reason, else None.

    Split out so `doctor` can REPORT it. A silently ignored misconfiguration is how a broken
    deploy looks healthy: the code quietly derives the right root, the operator believes their
    env var is in effect, and the next thing that reads AI_SETUP directly disagrees.

    This diagnoses the CODE root only. Instance state (data_root) follows AI_SETUP regardless
    of markers, so a bare data dir here is a partial override, not an ignored one.
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
