"""Pins for `toast` after the AXI conversion: the confirmation and the refusals.

The bus, the note and the learning store are recorders, so nothing is sent or written.

Run: uv run pytest tests/test_axi_toast.py -q
"""

import argparse

import pytest

import agent_cli


class _Store:
    def _load_experiment(self, rec):
        return {"agent_id": "alice", "experiment_name": rec} if rec == "port_clash" else None

    def load_all_learnings_from_store(self):
        return [{"experiment_name": "port_clash", "agent_id": "alice"}]


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return {"bus": [], "note": []}


def _toast(capsys, sent, to="alice", receipt="port_clash", credit="saved two hours", force=False, json=False):
    ns = argparse.Namespace(agent_id="ttoast", to=to, receipt=receipt, credit=credit, force=force, json=json)
    code = agent_cli.cmd_toast(
        ns,
        bus_send=lambda *a: sent["bus"].append(a),
        note_write=lambda *a: sent["note"].append(a),
        store=_Store(),
    )
    return code, capsys.readouterr().out


def test_a_verified_toast_confirms_both_surfaces(sent, capsys):
    code, text = _toast(capsys, sent)
    assert code == 0
    assert "to: alice\nreceipt: port_clash\ntier: VERIFIED\nverified_by: exact experiment id" in text
    assert "bus: sent\nnote: written" in text
    assert "help" not in text  # a confirmation answers itself


def test_forced_toast_says_guess(sent, capsys):
    code, text = _toast(capsys, sent, receipt="made_up", force=True)
    assert code == 0
    assert "tier: GUESS" in text


def test_unverified_receipt_is_refused_with_the_way_forward(sent, capsys):
    code, text = _toast(capsys, sent, to="carol")
    assert code == 2
    assert "code: REFUSED" in text
    assert "belongs to alice, not carol" in text
    assert "pass --force" in text
    assert "toast ttoast carol port_clash --credit" in text
    assert sent == {"bus": [], "note": []}


def test_missing_credit_names_the_flag(sent, capsys):
    code, text = _toast(capsys, sent, credit="")
    assert code == 2
    assert '--credit "<what their lesson saved you' in text


def test_json_refusal_keeps_its_old_line(sent, capsys):
    code, text = _toast(capsys, sent, to="carol", json=True)
    assert code == 2
    assert text.startswith("[toast] toast REFUSED:")


def test_human_view_lists_the_fields(sent, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _toast(capsys, sent)
    assert "Toast · VERIFIED" in text
    assert "verified by" in text
