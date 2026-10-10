"""The `aurora` command: route a call to the right Aurora program and run it.

    aurora <verb> [args]          agent_cli.py <verb>   (boot, learn, recall, hooks, setup, ...)
    aurora mcp                    the MCP server (ai_setup_mcp.py), for `claude mcp add`
    aurora <script.py> [args]     a script from the Aurora tree, e.g. agent/harness/hooks/x.py
    aurora -m <module> [args]     Aurora's Python itself (also -c, -u, ...)
    aurora self <action>          the launcher: version | install | update | prune | uninstall

WHICH PROGRAM. In order: AURORA_REPO (a checkout you name), the checkout this launcher is
installed from (`uv run aurora` inside the repo), else the release bundle matching this
launcher's version under ~/.aurora/versions/. A checkout keeps its state beside its code,
exactly as `uv run agent_cli.py` always has; a bundle keeps it in ~/.aurora/data.

WHY SCRIPTS AND -m ARE ACCEPTED. Aurora prints commands for agents to run (`<launcher>
agent_cli.py recall-at ...`, `<launcher> scripts/bifrost_wake.py ...`) and spawns some itself.
An installed launcher sets AKASHIC_PYTHON=aurora, the override core/paths.python_launcher()
already honours, so every one of those commands resolves through here to the same program.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from aurora_cli import __version__, bundle

_PY_FLAGS = {"-m", "-c", "-u", "-I", "-X", "-W", "-B", "-O", "-E", "-s", "-S", "-q"}
_USAGE_SELF = """usage: aurora self <action>

  version     the launcher, the program it runs, and where state lives
  install     fetch this version's bundle and build its environment now (install scripts run it)
  update      install the newest release (or --version X.Y.Z) of the launcher and its bundle
  prune       delete bundles of versions other than this launcher's
  uninstall   delete the bundles (add --purge to delete ~/.aurora/data, your memory, too)
"""


# --------------------------------------------------------------------------- resolution
def _launcher_path() -> str:
    """The console `aurora` executable, absolute -- what hooks and MCP registrations call."""
    # absolute, NOT resolved: ~/.local/bin/aurora is the stable name; the symlink target inside
    # uv's tool venv is an implementation detail of how it was installed
    return os.path.abspath(shutil.which(sys.argv[0]) or sys.argv[0])


def _source_checkout() -> Path | None:
    """The repo this launcher runs from, when it is installed from a checkout (editable)."""
    here = Path(__file__).resolve()
    return next((p for p in here.parents if bundle.looks_like_repo(p)), None)


def resolve_root() -> tuple[Path, str]:
    """(code root, mode) with mode in repo | checkout | bundle."""
    env = (os.environ.get("AURORA_REPO") or "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        if not bundle.looks_like_repo(root):
            raise SystemExit(f"aurora: AURORA_REPO={env!r} is not an Aurora checkout (no agent_cli.py and core/).")
        return root, "repo"
    src = _source_checkout()
    if src is not None:
        return src, "checkout"
    return bundle.ensure_bundle(__version__), "bundle"


def program_env(root: Path, mode: str) -> dict[str, str]:
    env = dict(os.environ)
    env["AURORA_ROOT"] = str(root)
    env["AURORA_CLI_VERSION"] = __version__
    if mode == "checkout":
        return env  # `uv run aurora` in the repo: the repo's own behaviour, nothing added
    launcher = _launcher_path()
    env["AURORA_LAUNCHER"] = launcher
    on_path = shutil.which("aurora")
    same = bool(on_path) and Path(on_path).resolve() == Path(launcher).resolve()
    env.setdefault("AKASHIC_PYTHON", "aurora" if same else f'"{launcher}"' if " " in launcher else launcher)
    if mode == "bundle":
        data = bundle.data_dir()
        env.setdefault("AI_SETUP", str(data))
        env.setdefault("AKASHIC_EMBEDDED_REDIS_DIR", str(data / "state" / "redis-embedded"))
        env.setdefault("AKASHIC_WORLD", bundle.world())
        env.pop("VIRTUAL_ENV", None)
    return env


def _python(root: Path, mode: str) -> list[str]:
    if mode == "bundle":
        if not bundle.is_synced(root):
            bundle.sync(root, __version__)
        return [str(bundle.venv_python(root))]
    # a checkout: uv keeps its .venv in step with its lock, as `uv run agent_cli.py` does
    return [bundle.uv_bin(), "run", "--quiet", "--project", str(root), "python"]


def _script(arg: str, root: Path) -> str:
    """A relative script resolves against the Aurora tree first: it names Aurora's file."""
    p = Path(arg)
    if not p.is_absolute() and (root / p).exists():
        return str(root / p)
    return arg


def _python_route(argv: list[str]) -> bool:
    return bool(argv) and argv[0] in _PY_FLAGS


def command_for(argv: list[str], root: Path) -> list[str]:
    if argv[:1] == ["mcp"]:
        return [str(root / "ai_setup_mcp.py"), *argv[1:]]
    if argv and (argv[0] in _PY_FLAGS or argv[0].endswith(".py")):
        return [_script(argv[0], root), *argv[1:]] if argv[0].endswith(".py") else list(argv)
    return [str(root / "agent_cli.py"), *argv]


def _run(cmd: list[str], env: dict[str, str]) -> int:
    if os.name != "nt":
        os.execvpe(cmd[0], cmd, env)  # one process: signals and exit codes pass straight through
    return subprocess.call(cmd, env=env)


# --------------------------------------------------------------------------- aurora self
def _self(argv: list[str]) -> int:
    action = argv[0] if argv else "version"
    if action in ("-h", "--help", "help"):
        print(_USAGE_SELF)
        return 0
    if action == "version":
        return _self_version()
    if action == "install":
        root, mode = resolve_root()
        if mode == "bundle" and not bundle.is_synced(root):
            bundle.sync(root, __version__)
        print(f"Aurora {__version__} ready ({mode}: {root})")
        return 0
    if action == "update":
        return _self_update(argv[1:])
    if action == "prune":
        keep = {__version__}
        for v in bundle.installed_versions():
            if v not in keep:
                shutil.rmtree(bundle.bundle_dir(v), ignore_errors=True)
                print(f"removed {bundle.bundle_dir(v)}")
        return 0
    if action == "uninstall":
        return _self_uninstall(argv[1:])
    print(_USAGE_SELF, file=sys.stderr)
    return 2


def _self_version() -> int:
    try:
        root, mode = resolve_root()
    except SystemExit as e:
        root, mode = None, f"unavailable ({e})"
    print(f"aurora {__version__}")
    print(f"  program : {mode}{f' at {root}' if root else ''}")
    if mode == "bundle":
        print(f"  state   : {os.environ.get('AI_SETUP') or bundle.data_dir()}")
        print(f"  world   : {bundle.world()}")
    print(f"  bundles : {', '.join(bundle.installed_versions()) or 'none'} (in {bundle.versions_dir()})")
    print(f"  launcher: {_launcher_path()}")
    return 0


def _installed_by() -> str:
    """How this launcher was installed: uv (tool), pipx, or something else."""
    prefix = Path(sys.prefix).resolve().as_posix().lower()
    if "/uv/tools/" in prefix or "/uv/data/tools/" in prefix:
        return "uv"
    if "/pipx/" in prefix:
        return "pipx"
    return "other"


def _self_update(argv: list[str]) -> int:
    want = argv[argv.index("--version") + 1].lstrip("v") if "--version" in argv[:-1] else bundle.latest_version()
    if want == __version__:
        print(f"aurora {__version__} is the latest release.")
        return 0
    wheel = f"{bundle.release_base(want)}/akashic_aurora_cli-{want}-py3-none-any.whl"
    how = _installed_by()
    if how == "uv":
        cmd = [bundle.uv_bin(), "tool", "install", "--force", "--python", "3.12", wheel]
    elif how == "pipx":
        cmd = ["pipx", "install", "--force", wheel]
    else:
        print(f"aurora {want} is available. Install it the way you installed aurora, e.g.:\n  pip install -U {wheel}")
        return 1
    print(f"updating aurora {__version__} -> {want}")
    rc = subprocess.call(cmd)
    if rc == 0:
        # the NEW launcher fetches its own bundle; this process is still the old one
        rc = subprocess.call([_launcher_path(), "self", "install"])
    return rc


def _self_uninstall(argv: list[str]) -> int:
    purge = "--purge" in argv
    print("Before removing aurora, take out what it registered (each is safe to run twice):")
    print("  aurora hooks uninstall --harness claude --scope user   # and any project scopes you used")
    print("  claude mcp remove --scope user akashic-aurora")
    shutil.rmtree(bundle.versions_dir(), ignore_errors=True)
    print(f"removed {bundle.versions_dir()}")
    if purge:
        shutil.rmtree(bundle.data_dir(), ignore_errors=True)
        print(f"removed {bundle.data_dir()} (your Aurora memory)")
    else:
        print(f"kept {bundle.data_dir()} (your Aurora memory); `aurora self uninstall --purge` removes it")
    how = _installed_by()
    tail = {"uv": "uv tool uninstall akashic-aurora-cli", "pipx": "pipx uninstall akashic-aurora-cli"}
    print(f"finally: {tail.get(how, 'pip uninstall akashic-aurora-cli')}")
    return 0


# --------------------------------------------------------------------------- entry point
def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["self"]:
        sys.exit(_self(argv[1:]))
    if argv[:1] in (["--version"], ["-V"]):
        sys.exit(_self_version())
    root, mode = resolve_root()
    env = program_env(root, mode)
    if _python_route(argv):
        # `aurora -c/-m ...` is Aurora's Python: import `core`, `agent`, ... from any cwd, as
        # `uv run python -c ...` does from the repo root. Only this route: a verb or a script
        # sets up its own path, and a PYTHONPATH would leak into every process it spawns.
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(root), env.get("PYTHONPATH", "")]))
    sys.exit(_run([*_python(root, mode), *command_for(argv, root)], env))
