"""W33 pins — the capability-gated standing queue (defer verb + boot section).

Consensus: claude opening (Q2: mini-registry, commands-not-chartered-work) + kimi AGREE
with amendments folded: (a) capability-aware render (a read-only seat gets one dim line,
never a shouted work list — the W03/W40 genus in a new organ); (b) --done REQUIRES a
receipt string (a queue where items vanish stampless is a graveyard, not a ledger);
(c) file discipline = git-durable state/defer_queue.json, ATOMIC writes (K0 lesson);
(d) boot section caps at 3 + "+M more" (funnel discipline).
Residual (honest): session-level harness gates (a write-gated kimi seat) are invisible
to the render; ACL caps gate the render, the seat self-selects on its live doors.

  P1  defer files an item (id echoed, needs recorded, file valid JSON)
  P2  --done without --receipt REFUSES; with receipt marks done + stamps seat
  P3  done items leave pending but STAY in the file (receipts are history)
  P4  render: a caps-holding agent sees the list (capped +M more); a read-only
      agent sees one dim line
  P5  atomic write: the file is valid JSON after every operation
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import defer_queue as dq


@pytest.fixture()
def qfile(tmp_path, monkeypatch):
    p = str(tmp_path / "defer_queue.json")
    monkeypatch.setattr(dq, "QUEUE_PATH", p)
    return p


def test_p1_defer_files_item(qfile):
    item = dq.add("kimi", "py -m pytest tests/test_x.py -q", needs="exec")
    assert item["id"] and item["needs"] == "exec" and item["by"] == "kimi"
    stored = json.load(open(qfile, encoding="utf-8"))
    assert len(stored["items"]) == 1 and stored["items"][0]["cmd"].startswith("py -m pytest")


def test_p2_done_requires_receipt(qfile):
    item = dq.add("kimi", "run the thing", needs="exec")
    with pytest.raises(ValueError):
        dq.mark_done(item["id"], seat="claude", receipt="")
    done = dq.mark_done(item["id"], seat="claude", receipt="ran GREEN 6/6, commit abc123")
    assert done["done_by"] == "claude" and "GREEN" in done["receipt"]


def test_p3_done_items_stay_as_history(qfile):
    a = dq.add("kimi", "cmd one", needs="exec")
    b = dq.add("deepseek", "cmd two", needs="write")
    dq.mark_done(a["id"], seat="claude", receipt="done")
    assert [i["id"] for i in dq.pending()] == [b["id"]]
    stored = json.load(open(qfile, encoding="utf-8"))
    assert len(stored["items"]) == 2, "history never deleted"


def test_p4_capability_aware_render(qfile):
    for i in range(5):
        dq.add("kimi", f"cmd {i}", needs="exec")
    full = dq.render_boot_section(agent_caps={"read", "exec", "write"})
    assert "cmd 0" in full and "+2 more" in full, "caps-holder sees the capped list"
    assert full.count("cmd") == 3, "capped at 3 lines (funnel discipline)"
    dim = dq.render_boot_section(agent_caps={"read"})
    assert "cmd 0" not in dim and "not you" in dim and "5" in dim, \
        "a read-only seat gets one dim line, never a shouted work list"
    assert dq.render_boot_section(agent_caps=set()) == dim
    empty = dq.render_boot_section(agent_caps={"exec"})
    # a queue with only-discharged items renders nothing for anyone
    for it in list(dq.pending()):
        dq.mark_done(it["id"], seat="claude", receipt="swept")
    assert dq.render_boot_section(agent_caps={"exec"}) == ""


def test_p5_file_always_valid_json(qfile):
    for i in range(4):
        dq.add("a", f"c{i}", needs="exec")
        json.load(open(qfile, encoding="utf-8"))
    it = dq.pending()[0]
    dq.mark_done(it["id"], seat="s", receipt="r")
    json.load(open(qfile, encoding="utf-8"))
