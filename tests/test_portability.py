"""PRE-REGISTERED acceptance: this repo runs from ANY path on ANY machine.

Registered before the fix, per M3. RED at registration and that is the point.

WHY (measured 2026-08-01, after a deploy at a second machine failed):
    710 occurrences of the literal E:\\AI-Setup across 238 tracked files
     83 UNCONDITIONAL in executable code -- hard failure anywhere else
      8 guarded by os.getenv("AI_SETUP", r"E:\\AI-Setup")
      0 machines with AI_SETUP actually set, including the original

The escape hatch existed and nobody set it, so every "portable" site silently ran on the
hardcoded fallback. Configuration you must remember is not portability.

SCOPE, deliberately bounded:
  IN   executable code -- .py/.ps1/.bat under core/ scripts/ agent/ tests/ and repo root
  OUT  docs/ prose (misleading to a deployer, breaks nothing -- separate pass)
  OUT  research/ chronicles/ store/ data/ backups/ -- HISTORICAL RECORDS. Rewriting an
       append-only plane to make a grep look clean would falsify the log, which is a worse
       defect than the one being fixed.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import env_override_is_wrong, repo_root  # noqa: E402

ROOT = repo_root()

# Any drive-letter absolute path, not just this machine's -- a fix that swaps E:\AI-Setup for
# someone else's C:\dev\aurora is not a fix.
_ABS = re.compile(r"[A-Za-z]:[\\/](?:AI-Setup|Users)", re.IGNORECASE)

_CODE_DIRS = ("core", "scripts", "agent", "tests")
_SKIP_PARTS = {"backups", "docs", "research", "chronicles", "store", "data",
               "ComfyUI-Zluda", "__pycache__", ".git", "node_modules", "venv"}


def _tracked_code_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(ROOT),
                         encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                         close_fds=True).stdout.splitlines()
    for rel in out:
        parts = rel.split("/")
        if set(parts) & _SKIP_PARTS:
            continue
        if not rel.endswith((".py", ".ps1", ".bat", ".cmd")):
            continue
        if len(parts) > 1 and parts[0] not in _CODE_DIRS:
            continue
        yield rel


def _offending_lines(rel):
    """Lines with an absolute path that are CODE, not prose.

    Comment and docstring lines are excluded on purpose: a comment explaining the rule, or a
    docstring showing an example settings.json command, is documentation rather than a path
    the interpreter will follow. Learned twice today -- a text rule that cannot tell code from
    prose about the rule fires on its own fix's docstring.
    """
    hits = []
    path = os.path.join(str(ROOT), rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            in_doc = False
            for i, line in enumerate(fh, 1):
                s = line.strip()
                fences = s.count('"""') + s.count("'''")
                if in_doc:
                    if fences:
                        in_doc = False
                    continue
                if fences == 1:
                    in_doc = True
                    continue
                if s.startswith(("#", "//", "::", "rem ", "REM ")):
                    continue
                if _ABS.search(line):
                    hits.append(f"{rel}:{i}: {s[:100]}")
    except OSError:
        pass
    return hits


def test_p1_repo_root_derives_with_no_env_var(monkeypatch):
    """The load-bearing property: a fresh clone works with nothing configured."""
    monkeypatch.delenv("AI_SETUP", raising=False)
    got = repo_root(use_env=False)
    assert (got / "agent_cli.py").exists() and (got / "core").is_dir(), (
        f"repo_root() did not find a real repo root without AI_SETUP: {got}")


def test_p2_a_wrong_env_override_is_reported_not_silently_ignored(monkeypatch):
    """A misconfiguration that silently self-heals is how a broken deploy looks healthy."""
    monkeypatch.setenv("AI_SETUP", "Z:/definitely/not/here")
    assert env_override_is_wrong(), "a bogus AI_SETUP produced no diagnosis"
    assert (repo_root() / "agent_cli.py").exists(), "bogus AI_SETUP broke root derivation"


# Files whose absolute paths are INERT FIXTURE DATA -- command strings and arguments fed to a
# parser, never resolved against a filesystem. Listed with a reason rather than silently
# skipped, matching check_boundaries.py's ALLOWLIST convention: known debt stays VISIBLE.
# Verified individually, not assumed -- blind allowlisting is how a real offender hides in a
# crowd of harmless ones.
_FIXTURE_DATA = {
    "tests/test_claude_hook_contract.py":
        "synthetic command strings fed to normalize_target(); asserts on parsing, opens nothing",
    "tests/test_harness_lib.py":
        "'cd E:/AI-Setup && ls' passed to scope.shell_in_scope() as sample input",
    "tests/test_ir4_mirror_family.py":
        "sample argv for the mirror family parser; the path is the thing under test, not a target",
    "tests/test_session_signals.py":
        "normalize_target() fixtures matching a recorded transcript; changing them breaks the match",
    "tests/test_r2_s0_silence_denominator.py":
        "a path STRING handed to recall_at() for relevance scoring; never opened",
    "tests/test_precision_audit.py":
        "recorded query/path pairs from a precision run; historical inputs, not live paths",
}


def test_p3_no_hardcoded_absolute_paths_in_executable_code():
    """THE BIG ONE. Finds every offender so nobody has to hunt 238 files by hand."""
    offenders = []
    for rel in _tracked_code_files():
        if rel.replace("\\", "/") in _FIXTURE_DATA:
            continue
        offenders.extend(_offending_lines(rel))
    assert not offenders, (
        f"{len(offenders)} hardcoded absolute path(s) in executable code -- these hard-fail on "
        f"any machine whose repo lives elsewhere:\n  " + "\n  ".join(offenders[:40])
        + ("\n  ..." if len(offenders) > 40 else ""))


def test_p4_config_py_root_is_derived():
    """config.py calls itself the single source of truth for configuration. It hardcoded the
    root AND nothing in the repo imports it -- so it was neither single, nor a source, nor
    truth. If it stays, its root must at least be real."""
    import importlib
    cfg = importlib.import_module("config")
    base = getattr(cfg, "BASE_DIR", None)
    assert base is not None and (base / "agent_cli.py").exists(), (
        f"config.BASE_DIR does not point at a real repo root: {base}")


def test_p5_doctor_reports_deploy_readiness():
    """A fresh deploy must be able to ASK what is wrong, in one hop, instead of discovering it
    one traceback at a time. This is the ergonomic half of portability."""
    r = subprocess.run([sys.executable, "-X", "utf8", "agent_cli.py", "doctor", "--deploy"],
                       capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL, close_fds=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    assert "repo root" in out.lower(), (
        "doctor --deploy does not report the resolved repo root:\n" + out[:600])
