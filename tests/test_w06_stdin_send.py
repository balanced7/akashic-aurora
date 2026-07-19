"""Pin W06 (2026-07-19, night run): bifrost-send with NO positional text and NO --text-file
reads the body from piped stdin -- the safe path becomes the effortless one (five argv
misparse strikes in one day forced this). TTY-without-pipe still refuses loudly. Offline:
Bus is faked; nothing touches Redis."""
import io
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent_cli  # noqa: E402


class _FakeBus:
    sent = []

    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.online = True

    def register(self, card=None):
        pass

    def send(self, to, kind, text, meta=None):
        _FakeBus.sent.append((self.agent_id, to, kind, text))
        return "fake-mid-1"

    def broadcast(self, kind, text, meta=None):
        _FakeBus.sent.append((self.agent_id, "*", kind, text))
        return "fake-mid-2"


def _args(**over):
    base = dict(agent_id="w06pin", text=[], text_file=None, to="peer", kind="chat",
                broadcast=False, expect_reply_within=-1, to_incarnation=None, json=False)
    base.update(over)
    return types.SimpleNamespace(**base)


def _with_fake_bus(monkeypatch):
    import core.comm.bus as busmod
    monkeypatch.setattr(busmod, "Bus", _FakeBus)
    _FakeBus.sent = []


def test_stdin_body_sends(monkeypatch):
    _with_fake_bus(monkeypatch)
    fake_in = io.StringIO("a body with --flag-shaped prose (parens: yes) that argv would mangle")
    fake_in.isatty = lambda: False
    monkeypatch.setattr(sys, "stdin", fake_in)
    rc = agent_cli.cmd_bifrost_send(_args())
    assert rc in (0, None), f"stdin send must succeed, rc={rc}"
    assert _FakeBus.sent and "--flag-shaped prose" in _FakeBus.sent[0][3]


def test_tty_empty_still_refuses(monkeypatch):
    _with_fake_bus(monkeypatch)
    tty_in = io.StringIO("")
    tty_in.isatty = lambda: True
    monkeypatch.setattr(sys, "stdin", tty_in)
    rc = agent_cli.cmd_bifrost_send(_args())
    assert rc == 2, "no text + no pipe must refuse loudly"
    assert not _FakeBus.sent


def test_positional_text_still_wins(monkeypatch):
    _with_fake_bus(monkeypatch)
    fake_in = io.StringIO("stdin should NOT be read when argv text exists")
    fake_in.isatty = lambda: False
    monkeypatch.setattr(sys, "stdin", fake_in)
    rc = agent_cli.cmd_bifrost_send(_args(text=["short", "safe", "sentence"]))
    assert rc in (0, None)
    assert _FakeBus.sent[0][3] == "short safe sentence"
