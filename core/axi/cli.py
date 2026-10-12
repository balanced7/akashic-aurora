"""argparse that fails the AXI way: on stdout, structured, with the fix in the same answer.

Plain argparse prints a usage line and an error on stderr and exits 2. An agent reads stdout, so
it sees nothing, guesses again, and pays a second call to learn the valid flags. AxiArgumentParser
keeps exit code 2 and argparse's own checks (unknown flags are already refused, never ignored),
and changes what the error says and where it goes (AXI section 6):

    agent  error: unrecognized arguments: --stat
           code: USAGE
           command: aurora locks
           valid_flags[2]: --json,--help
           help[1]: aurora locks --help

    human  the usage line and a red error on stderr, with the same suggestion.

An unknown verb gets the closest real verbs instead of argparse's list of all 120.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys

from core.axi import out

_INVALID_CHOICE = re.compile(r"invalid choice: '([^']*)'")


def cli_name() -> str:
    """How printed commands name the CLI: `aurora` installed, else `uv run agent_cli.py`."""
    try:
        from core.paths import cli_command

        return cli_command()
    except Exception:
        return "agent_cli.py"


def command_of(prog: str) -> str:
    """'agent_cli.py locks' -> 'aurora locks' (or the checkout form)."""
    parts = prog.split(" ", 1)
    return cli_name() + (f" {parts[1]}" if len(parts) > 1 else "")


def valid_flags(parser: argparse.ArgumentParser) -> list[str]:
    flags = []
    for action in parser._actions:
        long = [o for o in action.option_strings if o.startswith("--")]
        flags.extend(long[:1] or action.option_strings[:1])
    return flags


def subcommands(parser: argparse.ArgumentParser) -> list[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices)
    return []


class AxiArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser whose usage errors are AXI-shaped. Subparsers inherit the class."""

    def error(self, message: str):  # type: ignore[override]  # argparse declares NoReturn
        cmd = command_of(self.prog)
        details: dict = {"command": cmd}
        hints = [f"{cmd} --help"]
        bad = _INVALID_CHOICE.search(message)
        choices = subcommands(self)
        if bad and choices:
            top_level = " " not in self.prog
            near = difflib.get_close_matches(bad.group(1), choices, n=3, cutoff=0.5)
            message = f"unknown command {bad.group(1)!r}" + ("" if top_level else f" for `{cmd}`")
            hints = []
            if near:
                details["did_you_mean"] = near
                hints.append(f"{cmd} {near[0]} --help")
            hints.append(f"{cli_name()} discover" if top_level else f"{cmd} --help")
        else:
            details["valid_flags"] = valid_flags(self)
            if choices and len(choices) <= 20:
                details["subcommands"] = choices
        if not out.is_agent(sys.stdout):
            usage = self.format_usage()
            if usage.count("\n") <= 3:  # a usage line naming 120 verbs helps nobody
                sys.stderr.write(usage)
        out.fail(message, code="USAGE", details=details, hints=hints, exit_code=out.EXIT_USAGE)
        sys.exit(out.EXIT_USAGE)


def _subparsers_action(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def deepest(parser: argparse.ArgumentParser, ns: argparse.Namespace) -> argparse.ArgumentParser:
    """The subcommand parser this invocation reached, following each level's chosen subcommand."""
    current = parser
    while True:
        action = _subparsers_action(current)
        if action is None:
            return current
        chosen = getattr(ns, action.dest, None) if action.dest != argparse.SUPPRESS else None
        nxt = action.choices.get(chosen) if chosen else None
        if nxt is None:
            return current
        current = nxt


def parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace:
    """parse_args, except an unrecognized argument is reported by the subcommand it was given to,
    so the error lists that command's flags rather than the top level's."""
    ns, extras = parser.parse_known_args(argv)
    if extras:
        deepest(parser, ns).error(f"unrecognized arguments: {' '.join(extras)}")
    return ns
