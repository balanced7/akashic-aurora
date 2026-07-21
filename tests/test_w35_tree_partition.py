"""W35/B5 pins — the dirty-tree partition (kill the unqualified mirror imperative).

Consensus (claude opening + kimi Q4): the harm was never a missing bucket taxonomy --
it was boot commanding `run mirror.py "msg"` unqualified over a sibling's mid-flight
edits (63 files at my boot, 72 at kimi's -- the tax compounds nightly). v1: bucketed
counts (modified-tracked vs untracked + top-level-dir histogram, ~free) + a
default-safe action line. Claim-inference is v2.

  P1  bucket math from porcelain lines (modified vs untracked, dir histogram)
  P2  soft render: bucketed + safe-default; the bare sweep imperative is GONE
  P3  loud render: teaches mirror WITH explicit paths (the IR-4 form), never a sweep
  P4  clean tree stays silent
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


PORCELAIN = [
    " M core/comm/toolbox.py",
    " M scripts/bifrost_ui.py",
    "?? research/drafts/thing-a.md",
    "?? research/reviewed/thing-b.md",
    "?? tests/test_probe_one.py",
    "?? tests/test_probe_two.py",
    "?? scratch/x.txt",
]


def test_p1_bucket_math():
    b = agent_cli._bucket_tree(PORCELAIN)
    assert b["modified"] == 2 and b["untracked"] == 5
    assert b["dirs"]["research"] == 2 and b["dirs"]["tests"] == 2
    assert b["dirs"]["core"] == 1 and b["dirs"]["scratch"] == 1


def test_p2_soft_render_safe_default(capsys):
    status = {"ok": True, "dirty": 7, "ahead": 2, "branch": "master",
              "summary": "", "lines": PORCELAIN}
    assert agent_cli._warn_unmirrored(soft=True, status=status)
    out = capsys.readouterr().out
    assert "2 modified" in out and "5 untracked" in out
    assert "research 2" in out and "tests 2" in out
    assert "sibling" in out and "task list" in out, "the safe-default teaches claims"
    assert 'run `py scripts/mirror.py "msg"`' not in out, \
        "the unqualified sweep imperative is DEAD (kimi Q4: the 80% is the verb)"


def test_p3_loud_render_explicit_paths(capsys):
    status = {"ok": True, "dirty": 7, "ahead": 0, "branch": "master",
              "summary": "core/comm/toolbox.py", "lines": PORCELAIN}
    assert agent_cli._warn_unmirrored(soft=False, status=status)
    out = capsys.readouterr().out
    assert "<explicit paths>" in out or "explicit" in out.lower(), \
        "loud form teaches the IR-4 explicit-paths mirror, never a sweep"


def test_p4_clean_tree_silent(capsys):
    status = {"ok": True, "dirty": 0, "ahead": 0, "branch": "master",
              "summary": "", "lines": []}
    assert not agent_cli._warn_unmirrored(soft=True, status=status)
    assert capsys.readouterr().out == ""
