"""Pins for the CLI's lazy startup: main() builds only the named verb's parser, and that parser
is the same one the whole build makes, verb for verb.

Run: uv run pytest tests/test_cli_lazy_parser.py -q
"""

import argparse
import os
import subprocess
import sys

import pytest

import agent_cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dump(parser: argparse.ArgumentParser) -> dict:
    """Everything about a parser that parsing, help and errors read, recursing into subcommands."""
    actions = []
    for a in parser._actions:
        row = {
            "kind": type(a).__name__,
            "option_strings": a.option_strings,
            "dest": a.dest,
            "nargs": a.nargs,
            "const": repr(a.const),
            "default": repr(a.default),
            "type": getattr(a.type, "__qualname__", repr(a.type)),
            "required": a.required,
            "help": a.help,
            "metavar": a.metavar,
        }
        if isinstance(a, argparse._SubParsersAction):
            row["choices"] = {name: _dump(sp) for name, sp in a.choices.items()}
        else:
            row["choices"] = None if a.choices is None else list(a.choices)
        actions.append(row)
    return {
        "prog": parser.prog,
        "defaults": {k: getattr(v, "__qualname__", repr(v)) for k, v in parser._defaults.items()},
        "help": parser.format_help(),
        "actions": actions,
    }


def _verbs(parser: argparse.ArgumentParser) -> dict:
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return sub.choices


def test_one_verb_build_matches_the_whole_build_for_every_verb_and_alias():
    whole = _verbs(agent_cli.build_parser())
    assert len(whole) > 100  # the door really has its verbs; an empty build proves nothing
    for name, full_parser in whole.items():
        lone = _verbs(agent_cli.build_parser(only=name))
        assert name in lone, name
        assert _dump(lone[name]) == _dump(full_parser), name


def test_one_verb_build_builds_nothing_else():
    lone = _verbs(agent_cli.build_parser(only="find"))
    assert set(lone) == {"find"}


def test_a_word_that_is_no_verb_builds_no_verb():
    assert not _verbs(agent_cli.build_parser(only="no-such-verb"))


@pytest.mark.parametrize(
    ("argv", "expect"),
    [
        (["no-such-verb"], "unknown command"),  # the whole parser judges a word that is no verb
        (["fnd"], "find"),  # ... and still offers its did-you-mean
        (["find", "--no-such-flag"], "--no-such-flag"),  # a known verb names the flag it refuses
    ],
)
def test_usage_errors_read_as_they_did(argv, expect):
    run = subprocess.run(
        [sys.executable, os.path.join(ROOT, "agent_cli.py"), *argv],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "AURORA_OUTPUT": "agent"},
        timeout=60,
    )
    assert run.returncode != 0
    assert expect in run.stdout + run.stderr
