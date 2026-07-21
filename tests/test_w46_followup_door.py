"""W46 door pin — the followup CLI verb (claude's fence-completion of kimi's module).

kimi built + pinned core/toolbelt/followup.py and left the agent_cli wiring "riding the
fence" (shared high-contention file = fence territory). These pins cover the DOOR only;
the module's laws are pinned by tests/test_w46_followup_kimi.py.

  P1  the verb parses and routes to cmd_followup
  P2  cmd_followup writes the question + defer item through the module (live, sandboxed root)
  P3  a missing verdict file refuses loudly (rc 2), nothing filed
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.toolbelt import followup
from core.coord import defer_queue as dq


class Ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, k):
        return None


def test_p1_verb_parses():
    p = agent_cli.build_parser()
    a = p.parse_args(["followup", "kimi", "--on", "research/x.md", "--to", "claude",
                      "--ask", "still open?"])
    assert a.fn is agent_cli.cmd_followup and a.on == "research/x.md" and a.to == "claude"


def test_p2_cmd_files_both_halves(tmp_path, monkeypatch):
    monkeypatch.setattr(followup, "ROOT", str(tmp_path))
    monkeypatch.setattr(dq, "QUEUE_PATH", str(tmp_path / "defer_queue.json"))
    verdict = tmp_path / "verdict.md"
    verdict.write_text("# Verdict\n\nSome analysis.\n", encoding="utf-8")
    rc = agent_cli.cmd_followup(Ns(agent_id="kimi", on="verdict.md", to="claude",
                                   ask="does B1 still hold?", needs="write", json=False))
    assert rc == 0
    body = verdict.read_text(encoding="utf-8")
    assert "## Open Questions" in body and "does B1 still hold?" in body and "OPEN:" in body
    assert any("does B1 still hold?" in i["cmd"] for i in dq.pending())


def test_p3_missing_file_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(followup, "ROOT", str(tmp_path))
    monkeypatch.setattr(dq, "QUEUE_PATH", str(tmp_path / "defer_queue.json"))
    rc = agent_cli.cmd_followup(Ns(agent_id="kimi", on="nope.md", to="claude",
                                   ask="x", needs="write", json=False))
    assert rc == 2 and dq.pending() == []
