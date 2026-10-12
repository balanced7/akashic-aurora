"""Pins for `link` after the AXI conversion: the read paths (list, status, whoami, inbox) and the
errors, as an agent and a person see them. Runs on the in-process FakeDaemon, no aurora-linkd.

Run: uv run pytest tests/test_axi_link.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.link import cli
from core.link import client as lc
from tests.test_link_python_units import LINK, FakeDaemon, status


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AI_SETUP", str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return _Run(monkeypatch, capsys)


class _Run:
    """`aurora link <action>` against one FakeDaemon: (exit code, stdout + stderr)."""

    def __init__(self, monkeypatch, capsys):
        self.d = FakeDaemon()
        self._capsys = capsys
        monkeypatch.setattr(cli, "connect", lambda **_kw: self.d.client())

    def __call__(self, action: str, *args: str, **opts: Any) -> tuple[int, str]:
        code = cli.main(SimpleNamespace(action=action, args=list(args), **opts))
        cap = self._capsys.readouterr()
        return code, cap.out + cap.err


def test_list_is_a_table_with_a_total(run):
    run.d.handlers["link.list"] = [
        {"name": "ops", "link": LINK, "role": "owner", "members": 2, "epoch": 1, "alarms": 0},
        {"name": "lab", "link": LINK, "role": "reader", "members": 3, "epoch": 0, "alarms": 0},
    ]
    code, text = run("list")
    assert code == 0
    assert "total: 2\nlinks[2]{name,link,role,members,epoch}:" in text  # no alarms column: none have any
    assert "link status <name>" in text


def test_one_link_status_is_flat_and_hints_the_next_move(run):
    run.d.handlers.update({"link.list": [{"link": LINK}], "link.status": status()})
    code, text = run("status")
    assert code == 0
    assert text.startswith("name: ops\n")
    assert "members[2]{fleet,state,verified}:" in text
    assert "link invite ops" in text


def test_errors_are_structured(run, monkeypatch):
    code, text = run("inbox")
    assert code == 2
    assert "code: USAGE" in text

    def missing(**_kw):
        raise lc.LinkdMissing(lc.MISSING)

    monkeypatch.setattr(cli, "connect", missing)
    code, text = run("list")
    assert code == 2
    assert "code: LINKD_MISSING" in text


def test_human_status_keeps_the_prose_layout(run, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    run.d.handlers.update({"link.list": [{"link": LINK}], "link.status": status()})
    _, text = run("status")
    assert "home (us): owner" in text
    assert "our role owner" in text


def test_human_errors_go_to_stderr(run, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    assert cli.main(SimpleNamespace(action="inbox", args=[])) == 2
    cap = capsys.readouterr()
    assert cap.out == ""
    assert "usage: aurora link inbox" in cap.err
