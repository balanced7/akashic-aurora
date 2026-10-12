"""Pins for the AXI output layer: who the output is for, how each audience sees it, and how usage
errors read. core/axi/{mode,out,cli}.py; the TOON encoder has its own suite (test_axi_toon.py).

Run: uv run pytest tests/test_axi_output.py -q
"""

import io
import subprocess
import sys
from pathlib import Path

import pytest

from core.axi import mode, out
from core.axi.cli import AxiArgumentParser, parse

ROOT = Path(__file__).resolve().parents[1]


class _Tty(io.StringIO):
    def isatty(self):
        return True


@pytest.fixture
def no_harness(monkeypatch):
    for name in (*mode.AGENT_ENV, mode.ENV):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------- mode


def test_explicit_env_wins(no_harness, monkeypatch):
    monkeypatch.setenv(mode.ENV, "human")
    monkeypatch.setenv("CLAUDECODE", "1")
    assert mode.resolve(io.StringIO()) == "human"


def test_an_agent_harness_means_agent_even_on_a_terminal(no_harness, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert mode.resolve(_Tty()) == "agent"


def test_a_terminal_means_human_and_a_pipe_means_agent(no_harness):
    assert mode.resolve(_Tty()) == "human"
    assert mode.resolve(io.StringIO()) == "agent"


@pytest.mark.parametrize(
    ("argv", "rest", "chosen"),
    [
        (["--output", "human", "locks"], ["locks"], "human"),
        (["locks", "--output=agent"], ["locks"], "agent"),
        (["locks", "--output", "human", "--output", "agent"], ["locks"], "agent"),
        (["run", "x", "--", "--output", "human"], ["run", "x", "--", "--output", "human"], None),
        (["web", "fetch", "--agent", "claude"], ["web", "fetch", "--agent", "claude"], None),
    ],
)
def test_take_flags(argv, rest, chosen):
    assert mode.take_flags(argv) == (rest, chosen)


def test_a_bad_output_value_is_named():
    with pytest.raises(ValueError, match="banana"):
        mode.take_flags(["locks", "--output", "banana"])


# ---------------------------------------------------------------- emit / fail


def test_agent_output_is_toon_then_help_lines(no_harness, monkeypatch):
    monkeypatch.setenv(mode.ENV, "agent")
    buf = io.StringIO()
    out.emit(
        {"count": 2, "items": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}, hints=['x view "<id>"'], stream=buf
    )
    assert buf.getvalue() == 'count: 2\nitems[2]{id,name}:\n  1,a\n  2,b\nhelp[1]:\n  x view "<id>"\n'


def test_human_output_has_a_table_and_next_steps(no_harness, monkeypatch):
    monkeypatch.setenv(mode.ENV, "human")
    monkeypatch.setenv("NO_COLOR", "1")
    buf = io.StringIO()
    out.emit({"status": "ok", "items": [{"id": 1, "state": "live"}]}, hints=["x list"], title="Things", stream=buf)
    text = buf.getvalue()
    assert "Things" in text
    assert "status" in text
    assert "ok" in text
    assert "items (1)" in text
    assert "live" in text
    assert "Next:" in text
    assert "› x list" in text


def test_fail_in_agent_mode_is_structured_on_stdout(no_harness, monkeypatch, capsys):
    monkeypatch.setenv(mode.ENV, "agent")
    code = out.fail("no such lesson", code="NOT_FOUND", hints=["x list"], details={"id": "q1"})
    cap = capsys.readouterr()
    assert code == 1
    assert cap.out == "error: no such lesson\ncode: NOT_FOUND\nid: q1\nhelp[1]:\n  x list\n"
    assert cap.err == ""


def test_fail_in_human_mode_goes_to_stderr(no_harness, monkeypatch, capsys):
    monkeypatch.setenv(mode.ENV, "human")
    monkeypatch.setenv("NO_COLOR", "1")
    out.fail("no such lesson", hints=["x list"])
    cap = capsys.readouterr()
    assert cap.out == ""
    assert "error: no such lesson" in cap.err
    assert "x list" in cap.err


def test_truncate_says_how_much_is_missing():
    text, cut = out.truncate("abcdef" * 300, 100)
    assert cut
    assert text.endswith("(truncated, 1800 chars total)")
    assert out.truncate("short", 100) == ("short", False)


def test_fields_arg():
    assert out.fields_arg(None, ["id"], ["id", "a", "b"]) == ["id"]
    assert out.fields_arg("b", ["id"], ["id", "a", "b"]) == ["id", "b"]
    assert out.fields_arg("all", ["id"], ["id", "a", "b"]) == ["id", "a", "b"]
    with pytest.raises(ValueError, match="nope"):
        out.fields_arg("nope", ["id"], ["id"])


# ---------------------------------------------------------------- parser


def _parser():
    p = AxiArgumentParser(prog="agent_cli.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    locks = sub.add_parser("locks")
    locks.add_argument("--json", action="store_true")
    sub.add_parser("lock")
    return p


def test_unknown_flag_names_the_subcommands_flags(no_harness, monkeypatch, capsys):
    monkeypatch.setenv(mode.ENV, "agent")
    with pytest.raises(SystemExit) as e:
        parse(_parser(), ["locks", "--stat"])
    text = capsys.readouterr().out
    assert e.value.code == 2
    assert 'error: "unrecognized arguments: --stat"' in text
    assert "command:" in text
    assert "locks" in text
    assert 'valid_flags[2]: "--help","--json"' in text


def _lock_parser():
    p = AxiArgumentParser(prog="agent_cli.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    lock = sub.add_parser("lock")
    lock.add_argument("agent_id")
    lock.add_argument("path")
    lock.add_argument("--ttl", type=int)
    lock.add_argument("--json", action="store_true")
    return p


def test_an_unknown_flag_is_named_before_missing_arguments(no_harness, monkeypatch, capsys):
    monkeypatch.setenv(mode.ENV, "agent")
    with pytest.raises(SystemExit) as e:
        parse(_lock_parser(), ["lock", "--stat"])
    text = capsys.readouterr().out
    assert e.value.code == 2
    assert "unrecognized arguments: --stat" in text
    assert '"--ttl"' in text


@pytest.mark.parametrize(
    "argv",
    [
        ["lock", "a", "p", "--ttl", "60"],
        ["lock", "a", "p", "--ttl=60"],
        ["lock", "a", "p", "--tt", "60"],  # an abbreviation argparse accepts
    ],
)
def test_known_flags_and_their_values_pass(no_harness, monkeypatch, argv):
    monkeypatch.setenv(mode.ENV, "agent")
    assert parse(_lock_parser(), argv).cmd == "lock"


def test_the_scan_stops_at_a_bare_double_dash():
    from core.axi.cli import unknown_flags

    assert unknown_flags(_lock_parser(), ["lock", "a", "--", "--stat"]) == []


def test_a_value_that_looks_like_a_flag_is_not_flagged():
    from core.axi.cli import unknown_flags

    p = AxiArgumentParser(prog="agent_cli.py")
    sub = p.add_subparsers(dest="cmd")
    send = sub.add_parser("send")
    send.add_argument("--text")
    assert unknown_flags(p, ["send", "--text", "--looks-like-a-flag"]) == []


def test_unknown_command_suggests_the_nearest(no_harness, monkeypatch, capsys):
    monkeypatch.setenv(mode.ENV, "agent")
    with pytest.raises(SystemExit):
        parse(_parser(), ["lokcs"])
    text = capsys.readouterr().out
    assert "unknown command 'lokcs'" in text
    assert "did_you_mean[2]: locks,lock" in text


# ---------------------------------------------------------------- the real CLI


def _cli(*argv, env_mode="agent"):
    import os

    env = {**os.environ, mode.ENV: env_mode}
    return subprocess.run([sys.executable, str(ROOT / "agent_cli.py"), *argv], capture_output=True, text=True, env=env)


def test_no_verb_shows_the_home_view():
    r = _cli()
    assert r.returncode == 0
    assert r.stdout.startswith("bin: ")
    assert "description:" in r.stdout
    assert "help[4]:" in r.stdout


def test_output_flag_works_after_the_verb():
    r = _cli("locks", "--output", "agent", "--stat", env_mode="human")
    assert r.returncode == 2
    assert "valid_flags" in r.stdout


def test_bad_output_value_is_a_usage_error():
    r = _cli("locks", "--output", "banana")
    assert r.returncode == 2
    assert "--output takes agent or human" in r.stdout
