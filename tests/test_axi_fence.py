"""Pins for `fence` after the AXI conversion: what an agent and a person see.

Fences live under a temporary AKASHIC_FENCE_ROOT, never the repo's fences/ directory.

Run: uv run pytest tests/test_axi_fence.py -q
"""

import argparse

import pytest

import agent_cli
from core.coord import fence_workspace as fw

_BRIEF = "CHARTER\nx\nINPUTS\nx\nRULES OF ENGAGEMENT\nx\nTHE QUESTION\nx\nOUTPUT CONTRACT\nx\n"


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_FENCE_ROOT", str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return tmp_path


def _run(capsys, action, fence_id=None, **kw):
    ns = argparse.Namespace(
        action=action, fence_id=fence_id, question=None, tier=None, slot=None, text=None, file=None, by=None, json=False
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_fence(ns)
    return code, capsys.readouterr().out


def test_empty_list_says_zero(root, capsys):
    code, text = _run(capsys, "list")
    assert code == 0
    assert "total: 0\nopen: 0\nclosed: 0\nfences: []" in text
    assert "fence open <fence_id>" in text


def test_list_rows(root, capsys):
    fw.open_fence("f1", question="Q?", by="claude")
    fw.write_slot("f1", "brief", _BRIEF, by="claude")
    fw.seal("f1", "brief", by="claude")
    _, text = _run(capsys, "list")
    assert "fences[1]{id,status,tier,sealed,question}:" in text
    assert "f1,open,full,brief,Q?" in text


def test_status_slots_and_next_step(root, capsys):
    fw.open_fence("f1", question="Q?", by="claude")
    fw.write_slot("f1", "brief", _BRIEF, by="claude")
    code, text = _run(capsys, "status", "f1", by="kimi")
    assert code == 0
    assert "slots[4]{slot,state,by}:" in text
    assert "brief,written,claude" in text
    assert "half_a,empty,null" in text
    assert "pv_missing_citations: not run" in text
    assert "fence seal f1 --slot brief --by kimi" in text


def test_refused_seal_lists_the_problems(root, capsys):
    fw.open_fence("f1", question="Q?", by="claude")
    fw.write_slot("f1", "brief", "CHARTER only\n", by="claude")
    code, text = _run(capsys, "seal", "f1", slot="brief")
    assert code == 1
    assert "code: REFUSED" in text
    assert "M1-BRIEF section missing: INPUTS" in text


def test_missing_id_and_unknown_fence_are_structured(root, capsys):
    code, text = _run(capsys, "status")
    assert code == 2
    assert "code: USAGE" in text
    code, text = _run(capsys, "status", "nope")
    assert code == 1
    assert "no such fence" in text


def test_open_and_write_confirm(root, capsys):
    code, text = _run(capsys, "open", "f2", question="Q?")
    assert code == 0
    assert "opened: f2\ntier: full" in text
    code, text = _run(capsys, "write", "f2", slot="brief", text=_BRIEF, by="sol")
    assert code == 0
    assert "wrote: brief" in text
    assert "fence seal f2 --slot brief --by sol" in text


def test_human_status(root, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    fw.open_fence("f1", question="Should it move?", by="claude")
    _, text = _run(capsys, "status", "f1")
    assert "Should it move?" in text
    assert "brief" in text
    assert "not run" in text
