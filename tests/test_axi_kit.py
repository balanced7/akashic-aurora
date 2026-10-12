"""Pins for `kit` after the AXI conversion: --show and the install report.

The toolbelt is pointed at a temporary directory, so nothing touches data/verb-registry/.

Run: uv run pytest tests/test_axi_kit.py -q
"""

import argparse
import json

import pytest

import agent_cli


@pytest.fixture
def belt(monkeypatch, tmp_path):
    from core.toolbelt import registry

    monkeypatch.setattr(registry, "default_root", lambda: str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return registry


def _kit(capsys, name="recovery-kit", **kw):
    ns = argparse.Namespace(agent_id="tkit", kit_name=name, show=False, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_kit(ns)
    return code, capsys.readouterr().out


def test_show_is_a_table_of_entries(belt, capsys):
    code, text = _kit(capsys, show=True)
    assert code == 0
    assert "kit: recovery-kit" in text
    assert "total: 4" in text
    assert "entries[4]{name,family,evidence,steps}:" in text
    assert "drain-decide,ENGINEERS,VERIFIED,bifrost-sync -> bifrost-pause" in text
    assert "(truncated, " in text  # the kit's why is long: a preview and its size


def test_show_json_is_the_kit_itself(belt, capsys):
    from core.toolbelt import kit

    _, text = _kit(capsys, show=True, json=True)
    assert json.loads(text) == kit.RECOVERY_KIT


def test_install_reports_one_word_per_entry_and_counts(belt, capsys):
    belt.Toolbelt("tkit").mint("standby-hard", [["doctor"]])
    code, text = _kit(capsys)
    assert code == 1  # the kit names two verbs the CLI no longer has: refusals exit 1, as before
    assert "status: installed with refusals" in text
    assert "standby-hard,superseded to v2,VERIFIED,null" in text
    assert "drain-decide,minted,VERIFIED,null" in text
    assert "vitals,refused,null,\"unknown verb 'bifrost_dashboard'" in text
    _, text = _kit(capsys)
    assert "status: already installed; nothing changed; some refused\nchanged: 0\nunchanged: 2" in text


def test_unknown_kit_is_a_usage_error_naming_the_kits(belt, capsys):
    code, text = _kit(capsys, name="nope")
    assert code == 2
    assert "code: USAGE" in text
    assert "available[1]: recovery-kit" in text


def test_human_view_shows_the_install_table(belt, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "140")
    _, text = _kit(capsys)
    assert "installed with refusals" in text
    assert "standby-hard" in text
    assert "refused" in text
