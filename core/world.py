"""world -- which Aurora you are standing in, DERIVED rather than configured.

THE DEFECT THIS REPLACES (measured 2026-08-14, on a clone made minutes earlier):

    E:/AI-Setup-Alpha, cloned clean at HEAD, resolved:
        repo_root  -> E:\\AI-Setup-Alpha     correct; core/paths.py earns this
        REDIS_PORT -> 16379                  PROD, 19,850 live keys
        PORT_UI    -> 8787                   PROD console

    A clone of Aurora is not a second Aurora. It is a second BODY wired to the SAME BRAIN.

    The July 2026 sandbox "solved" this by editing REDIS_PORT on line 20 of config.py -- a
    TRACKED file. That is why it sat frozen at a 2026-07-05 baseline for 40 days: its
    isolation mechanism IS a permanent merge conflict on the most-imported file in the repo.
    Refreshing it means re-fighting the edit that makes it a sandbox at all.

    THE LAW: an environment whose isolation lives in a tracked file cannot be refreshed
    without surrendering its isolation.

WHY THIS SHAPE. core/paths.py solved this exact class one level down and wrote the doctrine
at the top of the file: "CONFIGURATION YOU MUST REMEMBER IS NOT PORTABILITY. It is a hardcoded
path with an extra step." It derived the repo ROOT from where the code stands, and never
generalised to the WORLD. This module applies that module's own doctrine one level up, with
the same escape hatch and the same warning about depending on it.

THE ORDER OF RESOLUTION, and why each rung is where it is:

    1. AKASHIC_WORLD env      -- an operator saying so out loud beats any inference.
    2. .aurora-world marker   -- per-checkout, GITIGNORED. This is the load-bearing rung:
                                 untracked means refreshing from prod can never clobber it,
                                 which is precisely what killed the July sandbox.
    3. directory-name suffix  -- zero-setup convenience so a clone works before anyone
                                 remembers rung 2. Convenience only; never the guarantee.
    4. unresolved -> UNKNOWN  -- NOT prod. A stray checkout that silently answers "prod" is
                                 how a sandbox eats production.

UNKNOWN READS BUT DOES NOT WRITE. Refusing everything is maddening and gets disabled by the
first person it inconveniences; a world that cannot name itself can still boot, orient and
read. Writes are where the damage lives, so writes are what it refuses -- with the remedy in
the message, because a refusal that states the problem and not the fix is a response rather
than an answer (the Dawe Test, adopted 2026-08-13).

ISOLATION IS PHYSICAL; THIS MODULE IS ROUTING. deepseek's fence, 2026-08-14: the firewall is a
separate Redis INSTANCE per world (16379 / 16380 / 16381), not a db index or a key prefix --
those collide on one FLUSHDB or one bad prefix. This module is the belt: it decides which
address the code dials. Both are needed, and routing is the half that actually failed --
physical separation buys nothing when the code dials the right number to the wrong house.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Optional

from core.paths import repo_root

#: The marker filename. Untracked by design -- see .gitignore and test_s3b.
MARKER = ".aurora-world"

#: Lineage aliases: names a human or an old doc may still use for a current world.
#: Recorded rather than silently mapped, so `why` can say the rename happened.
ALIASES = {"sandbox": "beta"}


class WorldRefusal(RuntimeError):
    """A world declined an operation. Always carries the remedy, never just the 'no'."""


@dataclass(frozen=True)
class World:
    name: str
    redis_port: Optional[int]
    ui_port: Optional[int]
    redis_db: int = 0
    container: Optional[str] = None
    #: How this instance was decided: override | marker | derived | unresolved.
    source: str = "derived"
    #: The sentence a human gets when they ask why. Never empty.
    why: str = ""

    # NOTE: there is deliberately no `may_read`. It was written, and check_wiring caught it
    # as a public function no production path calls -- correctly: a property that returns a
    # constant True is decoration, and it made "UNKNOWN reads but does not write" look like
    # an enforced pair when only one half was ever enforced. The read half is not a
    # permission, it is the absence of a refusal.

    @property
    def may_write(self) -> bool:
        return self.name != "unknown"

    # -- guards -----------------------------------------------------------

    def assert_may_write(self) -> None:
        if self.may_write:
            return
        raise WorldRefusal(
            f"refusing to write: this checkout has not declared which world it is "
            f"({self.why}). Reads are fine; writes are not, because an undeclared "
            f"checkout that guesses will guess 'prod'.\n"
            f"  FIX (one line, untracked, survives every refresh):\n"
            f"      echo alpha > {MARKER}\n"
            f"  Legal values: prod | beta | alpha"
        )

    def assert_owns_port(self, port: int) -> None:
        """Refuse a port belonging to another world, and NAME the owner.

        This is what finally makes config.PORT_REGISTRY's `world` field load-bearing.
        Before this, the field was read by exactly four files -- the one that defines
        it, the doc generator, the port checker and its own schema test -- and by
        nothing that made a runtime decision. It described a world without ever
        deciding one: fluent, on the record, operationally inert.
        """
        owner = owner_of_port(port)
        if owner == self.name:
            return
        if owner is None:
            raise WorldRefusal(
                f"port {port} belongs to no declared world, and you are '{self.name}'. "
                f"Register it in config.PORT_REGISTRY with a world and an owner, or "
                f"dial {self.redis_port} (yours)."
            )
        raise WorldRefusal(
            f"refusing cross-world access: port {port} belongs to '{owner}', "
            f"you are '{self.name}'. Yours is {self.redis_port}. "
            f"If you meant to reach '{owner}', do it deliberately from a '{owner}' "
            f"checkout -- crossing worlds by accident is the failure this guard exists for."
        )

    def redis_endpoint(self) -> tuple:
        if self.redis_port is None:
            raise WorldRefusal(
                f"no endpoint: {self.why}. A world that cannot say where it lives must "
                f"not hand out an address.\n  FIX: echo alpha > {MARKER}"
            )
        return ("localhost", self.redis_port, self.redis_db)


#: The declared worlds. Ports mirror config.py; the digits tell you the world.
WORLDS = {
    "prod":  World("prod",  16379, 8787, container="akashic-redis",
                   why="the one live fleet"),
    "beta":  World("beta",  16380, 8790, container="akashic-redis-beta",
                   why="longer-form integration; prod's waiting room"),
    "alpha": World("alpha", 16381, 8800, container="akashic-redis-alpha",
                   why="risky work; discardable by design"),
}

UNKNOWN = World("unknown", None, None, source="unresolved",
                why="no AKASHIC_WORLD, no marker, and the directory name matched no world")


def owner_of_port(port: int) -> Optional[str]:
    """Which world owns `port`, per config.PORT_REGISTRY -- the field, finally consulted."""
    try:
        import config
    except Exception:                                    # pragma: no cover - import guard
        return None
    entry = config.PORT_REGISTRY.get(port)
    if not entry:
        return None
    return ALIASES.get(entry.get("world"), entry.get("world"))


def _from_name(leaf: str) -> Optional[str]:
    """Read a world out of a directory leaf: AI-Setup-Alpha -> alpha, AI-Setup -> prod.

    Case-insensitive and separator-agnostic on purpose: a human who clones to `-alpha`
    or `_Alpha` meant alpha, and a strict match would hand them UNKNOWN for a keystroke.
    """
    norm = leaf.lower().replace("_", "-").rstrip("-")
    if norm in ("ai-setup", "aurora", "akashic-aurora"):
        return "prod"
    for base in ("ai-setup-", "aurora-", "akashic-aurora-"):
        if norm.startswith(base):
            suffix = norm[len(base):]
            suffix = ALIASES.get(suffix, suffix)
            if suffix in WORLDS:
                return suffix
    return None


def _parent_checkout(root: Path) -> Optional[Path]:
    """The checkout this one is a GIT WORKTREE of, or None.

    A linked worktree (any `git worktree add`, including the harness's own worktrees directory)
    has a `.git` FILE containing `gitdir: <parent>/.git/worktrees/<name>` rather than a directory.
    That line is the only proof git gives us that this tree belongs to another one, and it is the
    proof used here: the parent path is reconstructed and required to exist before anything is
    read from it.

    WHY THIS EXISTS (2026-10-30 wish, phase 3 of the modular-core detangle): "(c) worktrees
    inherit `.aurora-world` from their parent checkout instead of printing UNKNOWN checkout ...
    falling back on every commit". Measured on this checkout before the fix: every command in a
    linked worktree of this repo printed

        [world] UNKNOWN checkout -- the checkout is named 'modular-core-p3', which matches no
        world, and no .aurora-world was found in it

    on every single invocation, because marker rung 2 looks only in the tree's own root and rung 3
    (`git worktree` leaf names) matches nothing. The consequence is not cosmetic: UNKNOWN READS
    BUT DOES NOT WRITE, so every worktree agent has to remember `echo alpha > .aurora-world`
    before it can write anything -- and a rule you must remember is not a rule.
    """
    try:
        dot_git = root / ".git"
        if not dot_git.is_file():
            return None
        text = dot_git.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    target = text.split(":", 1)[1].strip()
    try:
        gitdir = Path(target)
        if not gitdir.is_absolute():
            gitdir = (root / gitdir).resolve()
        # <parent>/.git/worktrees/<name>  ->  <parent>
        if gitdir.parent.name != "worktrees" or gitdir.parent.parent.name != ".git":
            return None
        parent = gitdir.parent.parent.parent
        return parent if parent.is_dir() else None
    except (OSError, ValueError):
        return None


def _inherited_marker(root: Path) -> tuple:
    """(world, parent) from the PARENT checkout's marker, or (None, None). Never guesses."""
    parent = _parent_checkout(root)
    if parent is None:
        return None, None
    try:
        raw = (parent / MARKER).read_text(encoding="utf-8", errors="replace").strip().lower()
    except OSError:
        return None, None
    canon = ALIASES.get(raw, raw)
    if canon in WORLDS:
        return canon, parent
    return None, None


def resolve(root: Optional[Path] = None,
            env: Optional[Mapping[str, str]] = None) -> World:
    """Resolve the world. Never raises -- an unresolvable checkout gets UNKNOWN."""
    env = os.environ if env is None else env
    root = Path(root) if root is not None else repo_root()

    # 1. the operator, out loud
    declared = (env.get("AKASHIC_WORLD") or "").strip().lower()
    if declared:
        canon = ALIASES.get(declared, declared)
        if canon in WORLDS:
            note = f" (alias of '{declared}')" if canon != declared else ""
            return replace(WORLDS[canon], source="override",
                           why=f"AKASHIC_WORLD={declared}{note}")
        return replace(UNKNOWN, why=f"AKASHIC_WORLD={declared!r} is not a world "
                                    f"(legal: {', '.join(WORLDS)})")

    # 2. the marker -- untracked, so a refresh from prod can never clobber it
    try:
        raw = (root / MARKER).read_text(encoding="utf-8", errors="replace").strip().lower()
    except OSError:
        raw = ""
    if raw:
        canon = ALIASES.get(raw, raw)
        if canon in WORLDS:
            note = f" (alias of '{raw}')" if canon != raw else ""
            return replace(WORLDS[canon], source="marker", why=f"{MARKER} says {raw}{note}")
        return replace(UNKNOWN, why=f"{MARKER} says {raw!r}, which is not a world "
                                    f"(legal: {', '.join(WORLDS)})")

    # 2b. a GIT WORKTREE inherits its parent checkout's marker (phase 3, 2026-10-30 wish).
    # Placed BELOW this tree's own marker on purpose: a worktree that declares itself beats its
    # parent, so one checkout can still be pulled into another world deliberately. Placed ABOVE
    # the name rung because inheritance is evidence about the same repository, while a directory
    # leaf is a coincidence of how somebody typed `git worktree add`.
    inherited, parent = _inherited_marker(root)
    if inherited:
        return replace(WORLDS[inherited], source="inherited",
                       why=f"this is a git worktree of {parent}, whose {MARKER} says "
                           f"{inherited}")

    # 3. the directory name -- convenience, never the guarantee
    guess = _from_name(root.name)
    if guess:
        return replace(WORLDS[guess], source="derived",
                       why=f"the checkout is named {root.name!r}")

    # 4. UNKNOWN. Deliberately not prod.
    borrowed = ""
    try:
        par = _parent_checkout(root)
        if par is not None:
            borrowed = (f"; it is a git worktree of {par}, which carries no {MARKER} either")
    except Exception:
        pass
    return replace(UNKNOWN, why=f"the checkout is named {root.name!r}, which matches no "
                                f"world, and no {MARKER} was found in it{borrowed}")


_cached: Optional[World] = None


def current() -> World:
    """This process's world. Cached; `resolve()` directly for a fresh read."""
    global _cached
    if _cached is None or os.environ.get("_AISETUP_TEST_ISOLATED"):
        _cached = resolve()
    return _cached


def banner() -> str:
    """One line a boot/status render can carry, per the Dawe Test: it answers.

    Names the world, how it was decided, and where it dials -- so 'which Aurora am I
    talking to' is never something a human has to infer from behaviour.
    """
    w = current()
    if w.redis_port is None:
        return f"world: UNKNOWN -- {w.why} | writes REFUSED (echo alpha > {MARKER})"
    return (f"world: {w.name} [{w.source}: {w.why}] | redis {w.redis_port} "
            f"| ui {w.ui_port} | container {w.container}")
