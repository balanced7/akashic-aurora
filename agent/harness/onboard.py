"""`agent_cli.py setup` -- the onboarding sequence, and a mini-tutorial of the CLI it drives.

Each step asks one question, does the thing, and prints the command that does the same thing
later (`-> later:`), so a first run teaches the doors you will use to change your mind:
`hooks status|install|uninstall|enable|disable`, `discover`.

Plain input() on purpose (same style as peer_connect.py): it works in git-bash, PowerShell and
harness shells with no TTY tricks. `--yes` answers every question with its default (or the
flag given), so agents and CI can run it non-interactively; `--dry-run` changes nothing.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from agent.harness import install as inst
from agent.harness.registry import HARNESSES

#: installer harness -> registry harness (for its default agent id)
_REGISTRY_NAME = {"claude": "claude-code", "codex": "codex-desktop", "cursor": "cursor"}
#: default hook scope per harness. Claude: user-level fires for every launch cwd (the ledger's
#: routing, C8-3); Codex and Cursor have always been wired per project.
_DEFAULT_SCOPE = {"claude": "user", "codex": "project", "cursor": "project"}
_BINARIES = {"claude": ("claude",), "codex": ("codex",), "cursor": ("cursor", "cursor-agent")}


def say(step: str, msg: str) -> None:
    print(f"[{step}] {msg}")


def later(cmd: str) -> None:
    print(f"        -> later: {cmd}")


def _launcher() -> str:
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py" if os.name == "nt" else "python3"


class Asker:
    def __init__(self, assume_yes: bool):
        self.assume_yes = assume_yes

    def ask(self, question: str, default: str, choices: tuple[str, ...] = ()) -> str:
        hint = f" [{'/'.join(choices)}]" if choices else ""
        if self.assume_yes:
            print(f"        {question}{hint} -> {default}")
            return default
        while True:
            raw = input(f"        {question}{hint} (default: {default}) > ").strip()
            ans = raw or default
            if not choices or ans in choices:
                return ans
            print(f"        please answer one of: {', '.join(choices)}")

    def yes(self, question: str, default: bool) -> bool:
        return self.ask(question, "y" if default else "n", ("y", "n")) == "y"


def detect_harnesses() -> list[str]:
    home = Path(os.path.expanduser("~"))
    found = []
    for h, bins in _BINARIES.items():
        if any(shutil.which(b) for b in bins) or (home / f".{h}").is_dir():
            found.append(h)
    return found


def _print_result(res: inst.Result) -> None:
    if res.added:
        say("hooks", f"{len(res.added)} hook(s) registered in {res.path}")
    for s in res.skipped:
        say("hooks", f"skipped {s} -- one surface per hook, so it is not registered twice")
    for n in res.notes:
        say("hooks", n)
    if not res.added and not res.skipped and not res.notes:
        say("hooks", f"{res.path} already up to date")


def _skills_link_ok(repo: Path) -> bool:
    link = repo / ".claude" / "skills"
    return link.is_symlink() and link.resolve() == (repo / ".agents" / "skills").resolve()


def _mcp_command(repo: Path) -> str | None:
    try:
        spec = importlib.util.spec_from_file_location("_aurora_mcp_register", repo / "scripts" / "mcp_register.py")
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.registration_command(repo)
    except Exception:
        return None


def _ask_enrolment(ask: Asker, here: Path, cli: str, dry: bool) -> None:
    """Installed, the hooks speak up only in enrolled projects (agent/harness/scope.py)."""
    is_home = here == Path(os.path.expanduser("~")).resolve()
    say("2/5", "the hooks recall and record only in projects you enroll; everywhere else they stay silent.")
    choice = ask.ask(
        f"enroll this directory ({here}), every directory, or none for now?",
        "none" if is_home else "here",
        ("here", "everywhere", "none"),
    )
    if choice == "here":
        say("2/5", inst.enroll(here, dry_run=dry))
    elif choice == "everywhere":
        say("2/5", inst.enroll(everywhere=True, dry_run=dry))
    later(f"{cli} hooks enroll --project <dir>      # or --everywhere; `hooks unenroll` undoes it")


def run(args) -> int:
    from core.paths import cli_command, launcher, repo_root

    repo = repo_root().resolve()
    pyl = _launcher()
    ask = Asker(bool(getattr(args, "yes", False)))
    dry = bool(getattr(args, "dry_run", False))
    cli = cli_command()
    # Installed (`aurora`): the code root is a release bundle, so "this project" means the
    # directory you ran setup from, and the checkout-only steps (git hooks) do not apply.
    installed = launcher() is not None
    here = Path.cwd().resolve() if installed else repo

    print("Akashic Aurora setup. Each step shows the command that does the same thing later.")
    if dry:
        print("DRY RUN: nothing will be written.")

    # 1. where are we --------------------------------------------------------------------
    found = detect_harnesses()
    where = f"Aurora {os.getenv('AURORA_CLI_VERSION', '')} installed at {repo}" if installed else f"repo: {repo}"
    say("1/5", f"OS: {'Windows' if os.name == 'nt' else sys.platform}; {where}")
    say("1/5", f"harnesses found: {', '.join(found) or 'none'}")
    if not installed and not _skills_link_ok(repo):
        say(
            "1/5",
            "WARNING: .claude/skills is not a symlink to .agents/skills, so Claude Code sees no skills. "
            "Windows: enable Developer Mode, then `git config core.symlinks true` and "
            "`git checkout -- .claude/skills`.",
        )
    wanted = list(getattr(args, "harness", None) or found)
    if not wanted:
        say("1/5", "no harness detected; pass --harness claude|codex|cursor to set one up anyway.")

    # 2. hooks per harness -----------------------------------------------------------------
    claude_target: Path | None = None
    enrolled_asked = False
    for h in wanted:
        default = getattr(args, "scope", None) or _DEFAULT_SCOPE[h]
        scope = ask.ask(
            f"{h}: register Aurora's hooks for every project (user), one project (project), or skip?",
            default,
            ("user", "project", "skip"),
        )
        say("2/5", f"{h} hooks: {scope}")
        if scope == "skip":
            later(f"{cli} hooks install --harness {h} --scope user")
            continue
        project = None
        flags = f"--harness {h} --scope {scope}"
        if scope == "project":
            project = getattr(args, "project", None) or ask.ask("which project directory?", str(here))
            if Path(project).resolve() != here:
                flags += f' --project "{project}"'
        try:
            res = inst.install(h, scope, project=project, dry_run=dry)
        except Exception as e:
            say("2/5", f"STOPPED for {h}: {type(e).__name__}: {e}")
            continue
        _print_result(res)
        later(f"{cli} hooks install {flags}")
        later(f"{cli} hooks disable {flags}    # off, remembered; `hooks enable {flags}` brings them back")
        if h == "claude":
            claude_target = res.path
        if installed and scope == "user" and not enrolled_asked:
            enrolled_asked = True
            _ask_enrolment(ask, here, cli, dry)

    # 3. identity --------------------------------------------------------------------------
    if claude_target is not None:
        reg = HARNESSES.get(_REGISTRY_NAME["claude"], {})
        default_id = getattr(args, "agent_id", None) or reg.get("default_agent_id") or "claude"
        agent_id = ask.ask("agent id this Claude Code seat writes memory as (AKASHIC_AGENT_ID)?", default_id)
        doc = inst.read_config(claude_target)
        env = doc.setdefault("env", {})
        if env.get("AKASHIC_AGENT_ID") == agent_id:
            say("3/5", f"AKASHIC_AGENT_ID already {agent_id!r} in {claude_target}")
        else:
            env["AKASHIC_AGENT_ID"] = agent_id
            if not dry:
                inst.write_config(claude_target, doc)
            say("3/5", f"AKASHIC_AGENT_ID={agent_id} {'would be ' if dry else ''}set in {claude_target}")
        later(f'edit "env": {{"AKASHIC_AGENT_ID": "..."}} in {claude_target}')
    else:
        say("3/5", "agent id: skipped (no Claude hooks set up); set AKASHIC_AGENT_ID in your harness env")

    # 4. MCP door --------------------------------------------------------------------------
    mcp = _mcp_command(repo)
    if installed:
        say("4/5", "the akashic-aurora MCP server gives Claude Code Aurora's tools (boot, recall, learn, ...).")
    else:
        say("4/5", "this repo's .mcp.json already gives Claude Code the akashic-aurora tools when launched here.")
    if mcp and "claude" in wanted:
        if ask.yes("register them user-wide, so every Claude Code session gets them?", installed):
            if dry:
                say("4/5", f"would run: {mcp}")
            else:
                r = subprocess.run(mcp, shell=True, check=False)
                say("4/5", "registered" if r.returncode == 0 else f"`claude mcp add` exited {r.returncode}")
        later(mcp if installed else f"{pyl} scripts/mcp_register.py   # prints: {mcp}")

    # 5. git hooks -------------------------------------------------------------------------
    if installed:
        say("5/5", "git hooks: skipped -- they guard commits to an Aurora checkout, and this is an install.")
    elif ask.yes("install the repo's git hooks (pre-commit guardrails, commit-msg lint)?", True):
        if dry:
            say("5/5", "would run scripts/githooks/install_git_hooks.py")
        else:
            subprocess.run([sys.executable, str(repo / "scripts" / "githooks" / "install_git_hooks.py")], check=False)
    if not installed:
        later(f"{pyl} scripts/githooks/install_git_hooks.py")

    # summary ------------------------------------------------------------------------------
    print("\nDone. Where things stand:")
    for line in inst.status_lines(here):
        print("  " + line)
    print(
        "\nThe commands you just met:\n"
        f"  {cli} hooks status                       # what is registered where\n"
        f"  {cli} hooks disable --scope user         # switch user-level hooks off (remembered)\n"
        f"  {cli} hooks enable --scope user          # ...and back on\n"
        f"  {cli} discover [word]                    # every verb, one line each\n"
        f'  {cli} discover --semantic "<need>"       # does something already do this?\n'
        f'  {cli} boot <agent_id> --task "..."       # start of every task (AGENTS.md)'
    )
    return 0
