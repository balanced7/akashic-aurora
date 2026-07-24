"""T055 (R4 pre-flight recall) PRE-REGISTERED ACCEPTANCE -- committed RED before impl.

Cites docs/library/report/20260714_deepseek-r4-pre-flight-recall-design-202_1250bf.md (his design; tier
FENCE-LITE confirmed; claude builds, deepseek live-verifies). These pins cover the
MECHANICAL bars (his P2/P3/P4/P8); P1/P5/P6/P7 are his live-verify lane by design
(loop timing, before-result ordering, post-flight complement, engine-level dedup).

Registered seam: ToolBox._preflight_recall(name, args) -> str ("" = SILENCE, the
byte-identical path; non-empty = a '[recall (pre-flight)]' block <= 300 chars).
"""
import os
import sys

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


def _box(monkeypatch, cli_out):
    """A minimal ToolBox with the subprocess seam stubbed."""
    import deepseek_chat as dc
    box = dc.ToolBox.__new__(dc.ToolBox)
    box.agent_id = "t055-test"
    calls = {"n": 0}

    def fake_cli(call, timeout=15):
        calls["n"] += 1
        return cli_out
    monkeypatch.setattr(box, "_agent_cli", fake_cli, raising=False)
    return box, calls


# ---------------------------------------------------- B1 (his P2): skip-list silence
def test_b1_skip_tools_return_empty_without_subprocess(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_RECALL_AT", "1")
    box, calls = _box(monkeypatch, "should never be fetched")
    for tool in ("knowledge_recall", "memory_note", "bifrost_send", "git_log",
                 "run_command", "web_search", "reload_ui"):
        assert box._preflight_recall(tool, {"query": "x"}) == "", \
            f"B1: {tool} must be pre-flight silent"
    assert calls["n"] == 0, "B1: skipped tools must not even launch the subprocess"


# ---------------------------------------------------- B2 (his P3): empty-result silence
def test_b2_no_relevant_lessons_is_zero_characters(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_RECALL_AT", "1")
    box, _ = _box(monkeypatch, "")
    assert box._preflight_recall("read_file", {"path": "core/comm/bus.py"}) == "", \
        "B2: empty recall injects NOTHING (silence is the signal, never a banner)"


# ---------------------------------------------------- B3 (his P4): 300-char budget
def test_b3_budget_cap_with_pull_pointer(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_RECALL_AT", "1")
    long_out = "\n".join(f"[worked claude] lesson line {i} " + "x" * 90 for i in range(6))
    box, _ = _box(monkeypatch, long_out)
    block = box._preflight_recall("read_file", {"path": "core/comm/bus.py"})
    assert block and len(block) <= 301, "B3: the pre-flight block respects its 300-char budget"
    assert "+more" in block, "B3: truncation is LOUD with a pull pointer"


# ---------------------------------------------------- B4 (his P8): env gate
def test_b4_env_gate_controls_preflight(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_RECALL_AT", raising=False)
    box, calls = _box(monkeypatch, "[worked claude] a very relevant lesson indeed")
    assert box._preflight_recall("read_file", {"path": "core/comm/bus.py"}) == "", \
        "B4: with DEEPSEEK_RECALL_AT unset, pre-flight never fires"
    assert calls["n"] == 0


# ---------------------------------------------------- B5: investigation tools DO fire
def test_b5_investigation_tools_surface_lessons(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_RECALL_AT", "1")
    box, calls = _box(monkeypatch, "[worked claude] guard: STALE_GENERATION refuses backwards")
    block = box._preflight_recall("read_file", {"path": "core/comm/bus.py"})
    assert block.startswith("[recall (pre-flight)]"), "B5: the block carries the pre-flight prefix"
    assert calls["n"] == 1
    block2 = box._preflight_recall("search_files", {"pattern": "cursor", "directory": "core"})
    assert block2.startswith("[recall (pre-flight)]")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
