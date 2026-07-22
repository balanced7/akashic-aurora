"""W09 pins — a boot line proving recall-at is armed (calibrated silence vs missing wiring).

Wish W09 (kimi F2): kimi mis-diagnosed recall-at hook ABSENCE during their walk because
downstream silence is indistinguishable from a dead hook. A boot line saying "recall-at:
armed, N lessons warm" makes later silence CALIBRATED (the surface is live, nothing was
relevant) rather than suspect. Pure render over warm_cache's count.

  P1  armed line names the warm lesson count
  P2  a zero-count corpus still confirms ARMED (empty != broken)
  P3  a warm failure (count None) renders the honest "could not warm" variant
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def test_p1_armed_line_names_count():
    line = agent_cli._recall_armed_line(34)
    assert "recall-at" in line and "armed" in line and "34" in line
    assert "silence" in line.lower(), "the line teaches that later silence is calibrated"


def test_p2_zero_corpus_still_armed():
    line = agent_cli._recall_armed_line(0)
    assert "armed" in line and "0" in line, "an empty corpus is armed, not broken"


def test_p3_warm_failure_is_honest():
    line = agent_cli._recall_armed_line(None)
    assert "could not warm" in line.lower() or "unavailable" in line.lower()
    assert "armed" not in line, "a failed warm must not claim armed"
