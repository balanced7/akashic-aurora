"""Pins for `grant` after the AXI conversion: what an agent and a person see. Every case writes a
throwaway ACL (AKASHIC_ACL_PATH); the real security/acl.json is never read or written.

Run: uv run pytest tests/test_axi_grant.py -q
"""

import argparse
import json

import pytest

import agent_cli

BOSS = {
    "agent_id": "boss", "role": "super_admin", "path_scope": ["*"], "granted_by": "operator",
    "granted_at": "2026-10-01T00:00:00Z", "expires_at": None, "reason": "test super-admin",
    "caps": ["admin.approve", "admin.grant", "bifrost.inbox", "bus.nudge", "bus.send", "bus.steer", "exec",
             "git.read", "kb.learn", "kb.recall", "net", "read", "write"],
}  # fmt: skip


@pytest.fixture
def acl(tmp_path, monkeypatch):
    path = tmp_path / "acl.json"
    path.write_text(json.dumps({"grants": [BOSS]}), encoding="utf-8")
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return path


def _grant(capsys, agent_id=None, **kw):
    ns = argparse.Namespace(
        bootstrap=False, agent_id=agent_id, role=None, by=None, reason=None, hours=None, permanent=False,
        caps=None, path_scope=None, request_ref=None, revoke=False, list=False, dry_run=False, json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_grant(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_listing_is_a_table_with_the_acl_path_and_total(acl, capsys):
    _grant(capsys, "alice", role="member", by="boss", reason="pairing", hours=8)
    code, text = _grant(capsys)
    assert code == 0
    assert f"acl: {acl}\ntotal: 2\ngrants[2]{{agent,role,expires,by,reason}}:" in text
    assert "boss,super_admin,permanent,operator,test super-admin" in text
    assert "--revoke --by <your_id>" in text


def test_a_missing_acl_is_an_explicit_zero_not_a_traceback(acl, capsys):
    acl.unlink()
    code, text = _grant(capsys)
    assert code == 0
    assert "missing: only the code's bootstrap roles apply" in text
    assert "total: 0\ngrants: []" in text


def test_dry_run_writes_nothing_and_hints_the_real_command(acl, capsys):
    before = acl.read_text(encoding="utf-8")
    code, text = _grant(capsys, "dave", role="member", by="boss", reason="trial run", hours=4.0, dry_run=True)
    assert code == 0
    assert "dry_run: true\nwritten: false" in text
    assert "grant dave --role member --by boss --reason 'trial run' --hours 4" in text
    assert acl.read_text(encoding="utf-8") == before


def test_refusal_is_a_structured_error_with_exit_2(acl, capsys):
    code, text = _grant(capsys, "dave", role="member", by="dave", reason="me", hours=1)
    assert code == 2
    assert "code: REFUSED" in text
    code, text = _grant(capsys, "dave", role="member", by="boss", reason="", hours=1)
    assert code == 2
    assert "code: INVALID" in text


def test_mint_and_revoke_confirm_what_happened(acl, capsys):
    code, text = _grant(capsys, "carol", role="member", by="boss", reason="pairing", permanent=True)
    assert code == 0
    assert "granted: carol\nrole: member\nexpires: permanent\nby: boss" in text
    code, text = _grant(capsys, "carol", revoke=True, by="boss", reason="over")
    assert code == 0
    assert "revoked: carol\nwas: member" in text


def test_human_listing_is_a_table(acl, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _grant(capsys)
    assert "Grants · 1" in text
    assert "super_admin" in text
