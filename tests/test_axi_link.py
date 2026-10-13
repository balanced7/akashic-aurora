"""Pins for `link` after the AXI conversion: the read paths, the write actions and the errors, as
an agent and a person see them. Runs on the in-process FakeDaemon, no aurora-linkd.

Run: uv run pytest tests/test_axi_link.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.link import cli, quarantine
from core.link import client as lc
from tests.test_link_python_units import LINK, REC, FakeDaemon, event, status


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


def test_a_write_action_is_a_document_with_its_next_step_and_json_is_unchanged(run):
    answer = {"link": LINK, "name": "ops", "fingerprint": "fp"}
    run.d.handlers["link.create"] = answer
    code, text = run("create", "ops")
    assert code == 0
    assert text.startswith(f"name: ops\nlink: {LINK}\nfingerprint: fp\nrole: owner\nhelp[2]:")
    assert "link invite ops" in text
    import json

    assert json.loads(run("create", "ops", json=True)[1]) == answer


def test_show_cuts_long_content_and_says_how_long(run, monkeypatch):
    monkeypatch.setattr(quarantine, "redis_client", lambda: None)
    rec = event(1, rid=REC, content="x" * 2000)
    rec.update(status="admitted", seq=7, promoted=None)
    run.d.handlers.update({"link.status": status(), "events.wait": {"events": [rec]}, "record.get": rec})
    code, text = run("show", "ops", REC[:8])
    assert code == 0
    assert "content_chars: 2000" in text
    assert f"link show ops {REC[:12]} --json" in text
    assert "x" * 2000 not in text


def test_human_init_sets_the_recovery_phrase_apart(run, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    run.d.handlers["identity.init"] = {
        "device": "d" * 64,
        "root": "r" * 64,
        "fingerprint": "fp",
        "root_stored": False,
        "phrase": "alpha beta gamma",
    }
    _, text = run("init")
    assert "RECOVERY PHRASE -- shown once" in text
    assert "alpha beta gamma" in text
    assert "it is the fleet root" in text
    assert text.count("alpha beta gamma") == 1  # printed once, not echoed in the field list too


def test_human_invite_keeps_the_code_whole(run, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "40")
    code = "aurora-invite1:" + "Q" * 120
    run.d.handlers["link.invite"] = {
        "code": code,
        "acl": [],
        "role": "writer",
        "expires": 1_900_000_000,
        "approval": False,
        "fingerprint": "fp",
    }
    _, text = run("invite", "ops")
    assert code in text.splitlines()  # one line, so it copies whole
