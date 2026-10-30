"""local -- the LOCAL layer's data home, and its ONE loader.

WHY THIS MODULE EXISTS (modular-core detangle, phase 1; Daniel's own frame, 2026-09-17):
    "I want us to have the core architecture be modular and easy to patch with the trickier
    local variables and customizations also being importable and exportable modules. if we
    have good homes and places for things we won't need to detangle critical infrastructure
    on every sync."

The three layers are CODE-side rules, and this module draws the third one:

  * CORE      -- what any fork could take WITHOUT being told who we are. It never names a
                 seat, an absolute home path, a port, or a fork.
  * FEATURES  -- optional capability that still makes sense to a stranger.
  * LOCAL     -- the instance: WHO this deployment is, WHERE it lives, WHICH ports and peers
                 it talks to, and which wiring exceptions it carries. This is DATA, not code,
                 and it belongs in `local/` at the repo root, so a fork edits a JSON file
                 instead of a Python list buried in a checker.

THE ONE RULE THIS MODULE ENFORCES: a checker (or any Core code) that needs an instance value
asks here. It does not hardcode the value and it does not read the environment behind the
caller's back. `check_wiring.py`'s ENTRY_POINTS/EXCEPTIONS were the first mover -- the brief's
own named offender, and the documented blind spot for a seat deployed out of tree.

WHAT IS DELIBERATELY NOT HERE: RULES THAT DERIVE. "Enumerate every scripts/bifrost_runner_*.py"
is a rule, and it is executed in code (check_wiring still globs the runner and hook directories).
"agent_cli.py is an entry point" is a value, and it lives in local/wiring.json. Moving a
derivation into data would freeze it at today's answer -- the exact failure the enumeration
was written to fix.

FAILURE POLICY: MISSING LOCAL DATA IS UNKNOWN, NOT EMPTY. A loader that silently returns {} turns
"the deployment has no local layer" into "the deployment has no entry points", which is the
invisible-absence shape this house has paid for repeatedly. So `load()` raises LocalDataMissing
with the path it wanted and what to do about it, and callers that genuinely can tolerate absence
must say so by calling `optional()` instead. The distinction is the caller's, stated at the call
site, rather than a default that hides.

SECRETS ARE NOT LOCAL DATA THAT SHIPS. `local/` is committed (it carries house defaults), so it
must never hold a token, key, password or webhook URL. Secrets live in the gitignored env/secret
planes (AKASHIC_SECRETS_DIR and friends). tests/test_local_layer.py scans every local/*.json for
secret-shaped keys so the rule is a gate, not a comment.

WHERE THE ROOT COMES FROM: this module's own file, by marker walk -- deliberately NOT
core.paths.repo_root(), and deliberately not AI_SETUP. A checker running against a SHADOW
worktree (check_wiring's T159 canary does exactly this) must read THAT tree's Local data; an
env-driven root would silently hand it the main checkout's, which is the same class of lie the
canary exists to catch.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

LOCAL_DIR_NAME = "local"

# The marker that identifies an instance root. agent_cli.py is the door and it is present in
# every checkout, worktree, zip-export and data-carrying deploy of this repo.
_MARKERS = ("agent_cli.py",)

_MISSING = object()


class LocalDataMissing(RuntimeError):
    """A required piece of Local data is absent or unreadable.

    Raised, not returned: a checker that cannot find its instance values has NOT learned that
    there are none, and every caller that would have reported a clean empty set is a false
    clean. The message names the path and the remedy so the fix is one step.
    """


def instance_root() -> Path:
    """The tree THIS code lives in -- found by walking up from this file.

    No env override and no cache: local data belongs to the deployment whose code is executing,
    and a checker that reports on tree A must not be handed tree B's values.
    """
    here = Path(__file__).resolve()
    for cand in (here.parent, *here.parents):
        try:
            if all((cand / m).exists() for m in _MARKERS):
                return cand
        except OSError:                                    # unreadable dir: keep walking
            continue
    # Fall back to the two-levels-up guess rather than raising on import: the caller's own
    # existence check below will produce the message that names the thing it wanted.
    return here.parents[1]


def local_dir(root: Optional[os.PathLike] = None) -> Path:
    """The Local layer's directory (`<root>/local`). Does not check that it exists."""
    base = Path(root) if root is not None else instance_root()
    return base / LOCAL_DIR_NAME


def local_path(name: str, root: Optional[os.PathLike] = None) -> Path:
    """Resolve one Local data file. `name` may be given with or without the `.json` suffix."""
    fname = name if name.endswith(".json") else f"{name}.json"
    return local_dir(root) / fname


def load(name: str, root: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """Read one Local data file. REFUSES loudly when it is missing, unparseable, or not an object.

    Callers that can honestly proceed without the file must use `optional()`, which makes that
    tolerance a visible decision in their source rather than an accidental default here.
    """
    path = local_path(name, root)
    if not path.exists():
        raise LocalDataMissing(
            f"Local layer data file is missing: {path}. This is UNKNOWN instance data, not an "
            f"empty one -- refusing rather than reporting a clean zero. Restore the file (it is "
            f"committed: see {local_dir(root)}/README.md) or point the caller at the right tree."
        )
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise LocalDataMissing(f"Local data file {path} could not be read as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LocalDataMissing(
            f"Local data file {path} must hold a JSON OBJECT at the top level "
            f"(got {type(data).__name__}); every loader reads it by key."
        )
    return data


def optional(name: str, root: Optional[os.PathLike] = None) -> Optional[Dict[str, Any]]:
    """Read one Local data file, returning None when it is simply absent.

    Use when absence is a legitimate deployment state (a fork that has not adopted this file
    yet). A file that EXISTS but is broken still raises -- 'absent' and 'corrupt' are different
    answers and only one of them is expected.
    """
    if not local_path(name, root).exists():
        return None
    return load(name, root)


def strings(values: Any, *, what: str = "entry") -> list:
    """Normalise a Local list whose members may be a bare string or {path, why}.

    The object form exists so the PROVENANCE of an entry travels with it: check_wiring's
    hand-written list carried paragraphs explaining why each entry point was added (the
    2026-08-01 runner-enumeration incident, the supervisor, the out-of-tree bridge adapter), and
    moving those
    values into data must not silently delete the reasons -- a register without its history is
    how 'the register was accurate and had stopped being about anything'.
    """
    out = []
    for i, v in enumerate(values or []):
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
        elif isinstance(v, dict) and isinstance(v.get("path"), str) and v["path"].strip():
            out.append(v["path"].strip())
        else:
            raise LocalDataMissing(
                f"{what} #{i} must be a string or an object with a non-empty 'path' -- got {v!r}"
            )
    return out


def why_of(values: Any) -> Dict[str, str]:
    """{path: why} for the object-shaped members of a Local list (empty for plain strings)."""
    out = {}
    for v in values or []:
        if isinstance(v, dict) and isinstance(v.get("path"), str):
            note = str(v.get("why") or "").strip()
            if note:
                out[v["path"].strip()] = note
    return out


def status(root: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """A read-only summary for `doctor deploy` -- IS this machine's Local layer present?

    Reports, never judges: the caller decides whether a missing file is fatal. The three answers
    are kept apart on purpose, because collapsing any two of them is how a broken deploy reads as
    a clean one:
      * `files`      -- what is actually on disk
      * `missing`    -- house-default files the tree expects and does not have ("not adopted")
      * `unreadable` -- present but not usable as Local data ("adopted and broken")
    """
    d = local_dir(root)
    present = sorted(p.name for p in d.glob("*.json")) if d.is_dir() else []
    expected = ["wiring.json"]
    unreadable = []
    for fname in present:
        try:
            optional(fname, root)          # absent -> None (a race, not a finding); corrupt -> raises
        except LocalDataMissing as exc:
            unreadable.append({"file": fname, "why": str(exc)})
    return {
        "dir": str(d),
        "exists": d.is_dir(),
        "files": present,
        "missing": [f for f in expected if f not in present],
        "unreadable": unreadable,
    }
