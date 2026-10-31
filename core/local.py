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
"the door script is an entry point" is a value, and it lives in local/wiring.json. Moving a
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

THE TWO PLANES INSIDE `local/` -- PUBLIC DEFAULTS, PRIVATE PROFILE (amendment A1, 2026-10-31):
------------------------------------------------------------------------------------------
The rule the repo split runs on is REPO-VALUE goes public, MACHINE-VALUE goes private. `local/`
is committed, so it can only ever hold the first: the house DEFAULTS a fork inherits (which
scripts mark a gateway, which ports this deployment binds, the panel's allowlist shape) plus
DERIVATIONS (a path written against the instance root, never against somebody's home). The
values that are true only on THIS machine -- a tailnet address, a home-rooted tool path, which
seat this panel reports on -- live in a SEPARATE PRIVATE repo (`akashic-local`, carrying
`profile/*.json`) and are laid OVER the defaults here at read time.

    public  local/<name>.json      committed, house defaults + derivations
    private <profile>/<name>.json  NOT committed, this machine's values, schema `version`

`load()` returns the MERGED view; `public_only()` returns what a clone would see; `overlay()`
returns just the private half. The merge rule is stated once, in `merge()`: objects merge
key-wise, a list whose members all carry an `id` merges BY id (so a profile carries only the
rows it changes), and anything else is replaced outright.

WHERE THE PROFILE IS FOUND, and why absence is announced rather than swallowed:
  * `$AKASHIC_LOCAL` -- the private repo's root (or its `profile/` directory);
  * else a MARKER WALK from this tree: a directory named `akashic-local` that carries the
    marker file `.akashic-local`, tried first as a sibling of each ancestor of the instance
    root and then as a sibling of each of that ancestor's children (which is how `E:/AI-Setup`
    finds `E:/dev/akashic-local` -- one level of bend, no global config file to forget);
  * else the overlay is ABSENT: the work path FAILS OPEN on the public defaults, because a
    diagnostic that dies when a profile is missing would be worse than one that reports more
    UNKNOWN's -- but it says so in ONE loud line per process on stderr. Silent absence is the
    failure this module was written to refuse; a fork that ships only `local/` will see that
    line exactly once and know which values it is deriving or leaving unknown.
The profile is resolved independently of `root`: which machine this is does not change because
a checker is pointed at a shadow worktree.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

LOCAL_DIR_NAME = "local"

# The marker that identifies an instance root: the door script is present in every checkout,
# worktree, zip-export and data-carrying deploy of this repo.
_MARKERS = ("agent_cli.py",)

# --- the private profile (the machine half of the Local layer) ------------------------------
#: The env var naming the private repo's root (or its `profile/` directory directly).
PROFILE_ENV = "AKASHIC_LOCAL"

#: The subdirectory of the private repo that holds one `*.json` per public `local/*.json`.
PROFILE_DIR_NAME = "profile"

#: The marker file that makes an `akashic-local` directory THIS machine's profile rather than a
#: directory that merely shares its name. A directory, not a config file, so a fork that has no
#: profile needs no path to tell us so.
PROFILE_MARKER = ".akashic-local"

#: The overlay schema this loader understands. Bump it when a merge rule or a required key
#: changes; an overlay that declares a HIGHER version is refused rather than guessed at.
SCHEMA_VERSION = 1

_MISSING = object()

#: One loud line per process per kind of absence: the work path fails open, never silently.
_ANNOUNCED = set()

#: `profile_dir()` is called by every loader and by status(); the answer is cached per
#: (env value, instance root) so a re-pointed `$AKASHIC_LOCAL` re-resolves without a reset call.
_profile_cache: Dict[tuple, Optional[Path]] = {}


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


# ------------------------------------------------------------- the private overlay: discovery
def _announce(what: str, message: str) -> None:
    """ONE loud line per process per kind of absence, on stderr.

    Keyed rather than rate-limited: `status()` reads every file, so a per-call line would be a
    wall of identical text and the reader would learn to skip it. One line, naming the remedy,
    is read.
    """
    if what in _ANNOUNCED:
        return
    _ANNOUNCED.add(what)
    try:
        sys.stderr.write(f"[local] {message}\n")
        sys.stderr.flush()
    except Exception:                                      # a closed stderr must not break a read
        pass


def _akashic_local_dirs(parent: Path) -> List[Path]:
    """Every `akashic-local` directory one step under `parent`, sorted for determinism."""
    try:
        return sorted(p for p in parent.iterdir() if p.is_dir() and p.name == "akashic-local")
    except OSError:
        return []


def _one_level_below(parent: Path) -> List[Path]:
    """`<parent>/<child>/akashic-local` for each child of `parent`.

    Used ONLY for the volume root, which is the one place this bend is needed: the private repo
    sits at `E:/dev/akashic-local` while the checkout is at `E:/AI-Setup`, so a pure sibling walk
    never meets it. Applying the bend at every ancestor instead would let an unrelated
    `akashic-local` two directories over capture the read -- which a pin caught it doing
    (`tests/test_local_overlay.py`, 2026-10-31), because 'beside SOME ancestor' is not the same
    claim as 'beside this tree'.
    """
    out = []
    try:
        kids = sorted(p for p in parent.iterdir() if p.is_dir())
    except OSError:
        return out
    for kid in kids:
        try:
            out.extend(_akashic_local_dirs(kid))
        except OSError:
            continue
    return out


def _has_marker(root: Path) -> bool:
    try:
        return (root / PROFILE_MARKER).is_file()
    except OSError:
        return False


def _resolve_profile() -> Optional[Path]:
    """The profile DIRECTORY (`<private repo>/profile`) or None. Cached; announces its refusals."""
    env = os.environ.get(PROFILE_ENV, "").strip()
    if env:
        base = Path(env).expanduser()
        if (base / PROFILE_DIR_NAME).is_dir():
            return base / PROFILE_DIR_NAME
        if _has_marker(base):
            return base / PROFILE_DIR_NAME        # declared but the profile dir is not made yet
        if base.is_dir() and any(base.glob("*.json")):
            return base                           # the env named the profile directory itself
        _announce(
            f"env-bad:{base}",
            f"{PROFILE_ENV}={base} names no usable profile (no '{PROFILE_DIR_NAME}/' inside it, "
            f"no '{PROFILE_MARKER}' marker, no *.json). This is a MISCONFIGURATION, not an absent "
            f"machine -- so the marker walk is NOT used as a silent fallback: fix the variable or "
            f"unset it. Public local/ defaults are in use for this process.")
        return None
    start = instance_root()
    ancestors = [start, *start.parents]
    # PASS 1 -- the strong claim: beside this tree, or beside any ancestor of it, nearest first.
    for parent in ancestors:
        for cand in _akashic_local_dirs(parent):
            if _has_marker(cand):
                return cand / PROFILE_DIR_NAME
    # PASS 2 -- the weak claim, as a fallback only: one level down somewhere on that path. This is
    # what reaches `E:/dev/akashic-local` from `E:/AI-Setup`, and it runs only when no profile sits
    # beside the tree, because "beside SOME ancestor's child" is a lesser claim than "beside us".
    for parent in ancestors:
        for cand in _one_level_below(parent):
            if _has_marker(cand):
                return cand / PROFILE_DIR_NAME
    _announce(
        "absent",
        f"the private overlay is ABSENT -- no ${PROFILE_ENV}, and no '{PROFILE_MARKER}' marker in "
        f"an akashic-local directory beside {start}, beside any of its ancestors, or one level "
        f"under any of them. Reading local/*.json at its PUBLIC defaults: this machine's values "
        f"(tailnet address, home paths, which seat the panel reports on) are UNKNOWN or derived, "
        f"not silently defaulted. Create the private profile (see local/README.md) to silence "
        f"this line.")
    return None


def profile_dir() -> Optional[Path]:
    """This machine's private profile directory, or None when there is none.

    Resolved once per process PER (env value, instance root) -- the cache is keyed by the two
    inputs the answer depends on, rather than by nothing and then needing an invalidation call that
    only tests would ever use. A process that re-points `$AKASHIC_LOCAL` therefore re-resolves on
    its next read, and nothing here has to be reset from the outside.
    """
    key = (os.environ.get(PROFILE_ENV, "").strip(), str(instance_root()))
    if key not in _profile_cache:
        _profile_cache[key] = _resolve_profile()
    return _profile_cache[key]


def overlay_path(name: str, root: Optional[os.PathLike] = None) -> Optional[Path]:
    """The private file that overlays `local/<name>.json`, or None when this machine has none."""
    d = profile_dir()
    if d is None:
        return None
    fname = name if name.endswith(".json") else f"{name}.json"
    path = d / fname
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def overlay(name: str, root: Optional[os.PathLike] = None) -> Optional[Dict[str, Any]]:
    """Read (and version-check) one private overlay file. None when absent; REFUSES when broken.

    Absence is legitimate -- a machine may carry a profile for the panel and not for wiring. A
    file that exists but declares no `version`, or one this loader does not understand, is NOT
    absence: applying a half-known overlay would put values of unknown shape into a live read.
    """
    path = overlay_path(name, root)
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise LocalDataMissing(f"the private overlay {path} could not be read as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LocalDataMissing(
            f"the private overlay {path} must hold a JSON OBJECT (got {type(data).__name__}); it "
            f"is merged into local/<name>.json, and only an object can be merged key-wise.")
    _check_version(data, path)
    return data


def _check_version(data: Dict[str, Any], path: Path) -> int:
    """The overlay's schema version, or a refusal. Unknown is not guessable, so it is not guessed."""
    version = data.get("version")
    if version is None:
        raise LocalDataMissing(
            f"the private overlay {path} carries no 'version'. The version is what lets this "
            f"loader refuse a profile whose shape it does not know instead of merging it and "
            f"producing a plausible-looking wrong answer. Add '\"version\": {SCHEMA_VERSION}'.")
    if isinstance(version, bool) or not isinstance(version, int):
        raise LocalDataMissing(f"the private overlay {path} declares version {version!r}, which "
                               f"is not an integer.")
    if version > SCHEMA_VERSION:
        raise LocalDataMissing(
            f"the private overlay {path} declares schema version {version}; this core/local.py "
            f"understands {SCHEMA_VERSION}. The profile is NEWER than the code reading it -- "
            f"refusing rather than merging values of a shape this loader was not written for.")
    return version


def merge(public: Any, over: Any, where: str = "") -> Any:
    """Lay `over` (private) on `public` (committed). The ONE merge rule, stated once:

      * object + object  -> merged key-wise, recursively (the profile wins on a leaf);
      * list + list, when EVERY member of both is an object carrying a string `id`
                         -> merged BY id: public order is kept, a profile row overrides the
                            public row field-wise, and a row with a new id is appended. This is
                            what lets a profile carry only the two services it changes instead of
                            copying the whole allowlist (a copy is a second source of truth, and
                            it drifts);
      * anything else    -> the profile's value replaces the default outright (a list without
                            ids is a VALUE, not a set of named rows: merging it positionally
                            would invent relationships between unrelated entries).
    """
    if isinstance(public, dict) and isinstance(over, dict):
        out = dict(public)
        for key, value in over.items():
            if key in out:
                out[key] = merge(out[key], value, f"{where}.{key}" if where else str(key))
            else:
                out[key] = value
        return out
    if isinstance(public, list) and isinstance(over, list) and _all_keyed(public) and _all_keyed(over):
        rows = {row["id"]: dict(row) for row in public}
        order = [row["id"] for row in public]
        for row in over:
            rid = row["id"]
            if rid in rows:
                rows[rid] = merge(rows[rid], row, f"{where}[{rid}]")
            else:
                rows[rid] = dict(row)
                order.append(rid)
        return [rows[rid] for rid in order]
    return over


def _all_keyed(rows: Any) -> bool:
    """True when every member is an object carrying a non-empty string `id` (the merge-by-id key)."""
    return bool(rows) and all(
        isinstance(r, dict) and isinstance(r.get("id"), str) and r["id"].strip() for r in rows)


def load(name: str, root: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """The MERGED Local view: the public house defaults, overlaid with this machine's profile.

    This is the one a caller wants: the answer is complete, and whether it came from the
    committed default or from the private profile is provenance, not the caller's business
    (ask `public_only()` or `overlay()` when it IS the question).

    When no private profile exists the public file is returned unchanged and ONE line on stderr
    says the overlay is absent -- fail-open, because every caller of this module is a diagnostic
    that should still run on a fork with no profile, and loud, because a machine value silently
    missing is the class of absence this whole module refuses.
    """
    data = public_only(name, root)
    over, path = overlay(name, root), overlay_path(name, root)
    if over is None:
        return data
    merged = merge(data, over)
    merged["_overlay"] = {
        "path": str(path),
        "version": over.get("version"),
        "_what": "PROVENANCE, added by core.local.load(): the private profile file whose values "
                 "were laid over local/<name>.json. A merged document that does not say which "
                 "profile produced it cannot be audited from its own contents.",
    }
    return merged


def public_only(name: str, root: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """Read one Local data file AS COMMITTED. REFUSES loudly when missing, unparseable, or not an object.

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
    """The MERGED Local view of one file, or None when the committed file is simply absent.

    Use when absence is a legitimate deployment state (a fork that has not adopted this file
    yet). A file that EXISTS but is broken still raises -- 'absent' and 'corrupt' are different
    answers and only one of them is expected. A broken PRIVATE overlay also raises: it overlays
    a file that exists, so its failure is not the deployment's absent-file state.
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
    prof = profile_dir()
    overlays = {fname: str(overlay_path(fname, root)) for fname in present
                if overlay_path(fname, root) is not None}
    # The profile is reported as its OWN block, and its two failure shapes are kept apart from
    # the public files' on purpose: "no private profile on this machine" (a legitimate fork) and
    # "the profile is there and broken" (a deploy that reads as clean while producing nulls) are
    # different answers, and collapsing them is the same mistake status() already refuses above.
    prof_files: List[str] = []
    prof_unreadable = []
    if prof is not None and prof.is_dir():
        prof_files = sorted(p.name for p in prof.glob("*.json"))
        for fname in prof_files:
            try:
                overlay(fname, root)
            except LocalDataMissing as exc:
                prof_unreadable.append({"file": fname, "why": str(exc)})
    return {
        "dir": str(d),
        "exists": d.is_dir(),
        "files": present,
        "missing": [f for f in expected if f not in present],
        "unreadable": unreadable,
        "profile": {
            "_what": "The PRIVATE overlay this machine carries: the values that must never be "
                     "committed to a public repo. Absent is legitimate; broken is not.",
            "env": os.environ.get(PROFILE_ENV) or None,
            "root": str(prof.parent) if prof is not None else None,
            "dir": str(prof) if prof is not None else None,
            "marker": PROFILE_MARKER,
            "present": prof is not None,
            "files": prof_files,
            "unreadable": prof_unreadable,
            "applied": overlays,
        },
    }
