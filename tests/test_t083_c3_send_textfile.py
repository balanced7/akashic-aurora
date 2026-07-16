"""T083-C3-1 pins: bifrost-send --text-file -- flag-bearing/long bodies ride a file, never argv.

Live receipt 2026-07-16: a message body containing '--sources-json' aborted the send after shell
quote-mangling (argparse ate the prose as flags). Prior art: git commit -F. Pins exercise the
real CLI parser + send path with a stubbed bus (no Redis needed).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


class _FakeBus:
    online = True
    sent = None

    def __init__(self, *a, **k):
        pass

    def register(self):
        pass

    def send(self, to, kind, text, meta=None):
        _FakeBus.sent = {"to": to, "kind": kind, "text": text}
        return "1-1"

    def broadcast(self, kind, text):
        _FakeBus.sent = {"to": "*", "kind": kind, "text": text}
        return "1-1"


def _run(argv, monkeypatch):
    import core.comm.bus as bus_mod
    monkeypatch.setattr(bus_mod, "Bus", _FakeBus)
    _FakeBus.sent = None
    parser = agent_cli.build_parser() if hasattr(agent_cli, "build_parser") else None
    if parser is None:                      # fall back to main() with argv
        rc = agent_cli.main(argv)
        return rc
    args = parser.parse_args(argv)
    return args.fn(args)


def test_text_file_body_with_flag_shaped_prose(tmp_path, monkeypatch):
    body = "interop LIVE: pass --sources-json <tmpfile> after the subprocess returns -- 6 pins GREEN"
    p = tmp_path / "body.txt"
    p.write_text(body, encoding="utf-8")
    rc = _run(["bifrost-send", "claude", "--to", "deepseek", "--kind", "inform",
               "--expect-reply-within", "0", "--text-file", str(p)], monkeypatch)
    assert rc == 0
    assert _FakeBus.sent["text"] == body            # the flag-shaped prose arrived intact
    assert _FakeBus.sent["to"] == "deepseek"


def test_positional_text_still_works(monkeypatch):
    rc = _run(["bifrost-send", "claude", "hello", "there", "--to", "deepseek",
               "--expect-reply-within", "0"], monkeypatch)
    assert rc == 0
    assert _FakeBus.sent["text"] == "hello there"


def test_missing_text_file_refuses_loud(tmp_path, monkeypatch):
    rc = _run(["bifrost-send", "claude", "--to", "deepseek",
               "--text-file", str(tmp_path / "nope.txt")], monkeypatch)
    assert rc == 2
    assert _FakeBus.sent is None                     # nothing sent


def test_empty_text_file_refuses(tmp_path, monkeypatch):
    p = tmp_path / "empty.txt"
    p.write_text("   ", encoding="utf-8")
    rc = _run(["bifrost-send", "claude", "--to", "deepseek", "--text-file", str(p)], monkeypatch)
    assert rc == 2


def test_no_text_at_all_refuses(monkeypatch):
    rc = _run(["bifrost-send", "claude", "--to", "deepseek"], monkeypatch)
    assert rc == 2
    assert _FakeBus.sent is None
