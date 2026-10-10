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

# Files/dirs that together identify the repo root and nothing else.
_MARKERS = ("agent_cli.py", "core")

_cached: Path | None = None


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


def repo_root(start: str | None = None, *, use_env: bool = True) -> Path:
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


def env_override_is_wrong() -> str | None:
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


def env_paths(name: str) -> list[Path]:
    """Absolute paths from the env var `name`, separated by os.pathsep (';' on Windows, ':'
    elsewhere). For locations that are genuinely MACHINE-SPECIFIC -- a second physical disk,
    a tool installed somewhere odd -- and so cannot be derived the way repo_root() is.

    A relative entry is DROPPED with a warning, never resolved: 'E:\\x' on Linux is a relative
    path, and resolving it against the cwd is how a Windows literal became a stray folder
    inside the repo. Unset or empty -> [] (the caller decides what "not configured" means).
    """
    import sys

    out = []
    for part in (os.environ.get(name) or "").split(os.pathsep):
        part = part.strip().strip('"')
        if not part:
            continue
        p = Path(os.path.expanduser(part))
        if p.is_absolute():
            out.append(p)
        else:
            print(f"[paths] {name}: ignoring {part!r} -- not an absolute path on this OS", file=sys.stderr)
    return out


def python_launcher() -> str:
    """The command prefix that runs Aurora's Python on THIS machine, for commands shown to (or
    run by) an agent: `<launcher> scripts/x.py`, `<launcher> -m pytest`, `<launcher> agent_cli.py`.

    One launcher on every OS: `uv run` when uv and the repo's pyproject are present -- it brings
    Aurora's locked dependencies with it. Without uv, Windows falls back to the `py` launcher
    and everything else to plain `python3` (`py` does not exist there). AKASHIC_PYTHON
    overrides for any other setup. scripts/githooks/pyrun is the same chain for shell scripts.
    """
    override = (os.getenv("AKASHIC_PYTHON") or "").strip()
    if override:
        return override
    import shutil

    if shutil.which("uv") and (repo_root() / "pyproject.toml").exists():
        return "uv run"
    if os.name == "nt":
        return "py"
    return "python3"


def launcher() -> str | None:
    """The installed `aurora` launcher running this process (aurora-cli/), else None.

    Set by the launcher as AURORA_LAUNCHER, an absolute path. Code that writes a command into a
    file that outlives this process -- a harness hook, an MCP registration -- uses it instead of
    a path into the code root, because an installed code root is versioned and moves on upgrade.
    """
    return (os.getenv("AURORA_LAUNCHER") or "").strip() or None


def cli_command() -> str:
    """How to invoke the CLI in commands shown to a person or agent: `aurora` when installed,
    else `<python_launcher()> agent_cli.py` (`uv run agent_cli.py` in a checkout)."""
    return "aurora" if launcher() else f"{python_launcher()} agent_cli.py"
