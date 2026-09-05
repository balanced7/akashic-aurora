"""Launch one long-lived Aurora service in an explicit runtime world.

A checkout world and a deployed service world are different authorities.  Persistent
Discord code lives in an alpha-marked worktree so an ordinary command from that checkout
cannot accidentally mutate production.  The production Scheduled Tasks, however, must
all speak to the production fleet regardless of process start order.  This launcher pins
that decision before importing any Aurora module, verifies the resolved endpoint, and
then executes one allowlisted service entry point in the same process.

No shell is involved, and this is deliberately not a generic Python launcher.
"""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import runpy
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_WORLDS = frozenset({"prod", "beta", "alpha"})
ALLOWED_TARGETS = frozenset(
    {
        "bifrost_runner_discord.py",
        "bifrost_daemon.py",
        "codex_bifrost_wake.py",
    }
)
_ENDPOINT_OVERRIDES = ("REDIS_HOST", "REDIS_PORT", "REDIS_DB")


def pinned_environment(
    world: str,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an inherited environment pinned to exactly one declared world.

    Service launches deliberately discard ambient Redis endpoint overrides.  Keeping one
    of those would let a correctly labelled ``--world prod`` process dial a test or twin
    endpoint, recreating the split-brain class under a truthful-looking command line.
    """
    chosen = str(world or "").strip().lower()
    if chosen not in ALLOWED_WORLDS:
        raise ValueError(
            f"unknown Aurora world {world!r}; choose one of {sorted(ALLOWED_WORLDS)}"
        )
    env = dict(os.environ if base is None else base)
    for name in _ENDPOINT_OVERRIDES:
        env.pop(name, None)
    env["AKASHIC_WORLD"] = chosen
    return env


def resolve_target(raw: str, *, root: Path = ROOT) -> Path:
    """Resolve one allowlisted service script beneath ``root/scripts``."""
    root = Path(root).resolve()
    scripts = (root / "scripts").resolve()
    candidate = Path(str(raw or "").strip())
    if candidate.name not in ALLOWED_TARGETS:
        raise ValueError(
            f"target is outside the Aurora service allowlist: {candidate.name or raw!r}"
        )
    if not candidate.is_absolute():
        candidate = root / candidate if candidate.parts[:1] == ("scripts",) else scripts / candidate
    resolved = candidate.resolve()
    if resolved.parent != scripts:
        raise ValueError(f"service target is outside {scripts}: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"allowlisted service target does not exist: {resolved}")
    return resolved


def verify_world(expected: str) -> dict[str, object]:
    """Activate the pin and prove world resolution agrees with the Redis foundation."""
    env = pinned_environment(expected)
    os.environ.clear()
    os.environ.update(env)

    root_s = str(ROOT)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)

    # This process intentionally imports Aurora only after the environment is pinned.
    # Reloads make the pure function independently exercisable in a test process whose
    # module cache may already contain a differently resolved world.
    from core import world as world_module

    world_module._cached = None
    resolved = world_module.current()
    redis_module = importlib.import_module("core.foundation.redis_connection")
    redis_module = importlib.reload(redis_module)

    observed = {
        "world": resolved.name,
        "world_source": resolved.source,
        "redis_host": redis_module.DEFAULT_REDIS_HOST,
        "redis_port": int(redis_module.DEFAULT_REDIS_PORT),
        "redis_db": int(redis_module.DEFAULT_REDIS_DB),
    }
    if observed["world"] != expected:
        raise RuntimeError(
            f"world pin failed: expected {expected}, resolved {observed['world']}"
        )
    if observed["redis_port"] != resolved.redis_port or observed["redis_db"] != resolved.redis_db:
        raise RuntimeError(
            "world/Redis disagreement: "
            f"world={resolved.name}:{resolved.redis_port}/{resolved.redis_db}, "
            f"foundation={observed['redis_port']}/{observed['redis_db']}"
        )
    return observed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one allowlisted Aurora service in an explicit world"
    )
    parser.add_argument("--world", required=True, choices=sorted(ALLOWED_WORLDS))
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="-- <allowlisted service script> [arguments...]",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise SystemExit("service target required after --")

    target = resolve_target(command[0])
    observed = verify_world(args.world)
    print(
        "[aurora-service] "
        f"world={observed['world']} source={observed['world_source']} "
        f"redis={observed['redis_host']}:{observed['redis_port']}/{observed['redis_db']} "
        f"target={target.name} pid={os.getpid()}",
        flush=True,
    )

    sys.argv = [str(target), *command[1:]]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

