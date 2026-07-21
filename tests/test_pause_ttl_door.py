"""bifrost-pause --ttl door pins (RB-30 exposure; deepseek's C1-8-genus find 2026-07-21).

control.pause(ttl=) has existed since T030 L5 -- the CLI door never exposed it, so belt
ceremonies (standby-hard, drain-decide) pause WITHOUT self-heal and a mid-ceremony crash
freezes the fleet until human hands. Pins:
  P1  parser accepts --ttl
  P2  cmd passes ttl through to control.pause
  P3  no --ttl -> ttl=None (legacy byte-identical)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.comm import control


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


def test_p1_parser_accepts_ttl():
    p = agent_cli.build_parser()
    a = p.parse_args(["bifrost-pause", "--reason", "kit-standby", "--by", "t", "--ttl", "120"])
    assert a.ttl == 120 and a.fn is agent_cli.cmd_bifrost_pause


def test_p2_ttl_passes_through(monkeypatch):
    seen = {}

    def fake_pause(reason="", by="user", ttl=None):
        seen.update(reason=reason, by=by, ttl=ttl)
        return True

    monkeypatch.setattr(control, "pause", fake_pause)
    rc = agent_cli.cmd_bifrost_pause(Ns(reason="x", by="t", ttl=120, json=False))
    assert rc == 0 and seen["ttl"] == 120


def test_p3_no_ttl_is_legacy(monkeypatch):
    seen = {}

    def fake_pause(reason="", by="user", ttl=None):
        seen.update(ttl=ttl)
        return True

    monkeypatch.setattr(control, "pause", fake_pause)
    rc = agent_cli.cmd_bifrost_pause(Ns(reason="", by="t", ttl=None, json=False))
    assert rc == 0 and seen["ttl"] is None
