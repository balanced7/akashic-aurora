"""T067-1 PRE-REGISTERED ACCEPTANCE -- ToolBox third-door parity.

Design half: research/reviewed/deepseek-t067-1-design-2026-07-15.md (T058 pattern:
deepseek designs, claude builds, deepseek live-verifies). Three ToolBox additions
(knowledge_map / bifrost_ack / delta), check_door_parity gains the ToolBox as an
ENFORCED third door (ratchet + shared-coverage + toolbox_only class), and the
runner folds this agent's private memory notes into its boot text (Q1 leftover).

Build-half reconciliation notes (for deepseek's gate -- deviations from the sketch):
  * knowledge_map rides the REAL CLI parser: positional query + --per-layer
    (the sketch's --topic/--max-nodes flags do not exist on the verb).
  * delta rides the REAL CLI parser: positional agent, NO --json, NO --ack
    (the mark stays boot-owned; consecutive tool calls keep showing the window).
  * Each new tool also gets a TOOLS schema entry -- methods alone never reach
    the model (the sketch's line estimate missed the schema list).
  * bifrost_ack surfaces a REFUSED verdict (promoter.ack returns False for a
    non-addressee/non-promoted ack) instead of claiming success.
  * Design rule "every shared verb must exist on the ToolBox" is implemented as
    a RATCHET: present by name, covered by a declared alias (recall->knowledge_recall
    class), or explicitly exempted with a rationale -- a NEW shared verb with none
    of the three FAILS. A literal reading would brick the guard on boot/stats/story
    et al., contradicting design non-goal (g) ("the ToolBox is not a CLI mirror").

Pins B1-B3 (tools), D1-D4 (guard), Q1-Q3 (boot fold) per design Part (e).

Run: py -m pytest tests/test_t067_1_toolbox_parity.py -q
"""
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import scripts.deepseek_chat as dc
import scripts.check_door_parity as cdp


def _runner():
    # Lazy, like test_t068_r3_preflight: the runner module wires liveness at import;
    # only the Q pins pay that cost, never bare collection.
    import scripts.bifrost_runner_deepseek as runner
    return runner


def _toolbox(agent_id="testseek"):
    return dc.ToolBox(Path(ROOT), allow_exec=False, trust=False, allow_secrets=False,
                      confirm=lambda _p: False, agent_id=agent_id)


def _schema_names():
    return {t["function"]["name"] for t in dc.TOOLS}


# ------------------------------------------------------------- B1-B3: the three tools
def test_b1_knowledge_map_returns_graph():
    tb = _toolbox()
    seen = {}
    tb._agent_cli = lambda args, timeout=90: seen.setdefault("args", list(args)) and "ok" or "ok"
    out = tb.knowledge_map("lanes")
    assert out == "ok"
    assert seen["args"] == ["knowledge-map", "lanes", "--per-layer", "6", "--json"], \
        f"must ride the REAL knowledge-map parser (positional + --per-layer), got {seen['args']}"
    assert "knowledge_map" in _schema_names(), "the model never sees a tool without a TOOLS schema entry"


def test_b2_ack_marks_handled(monkeypatch):
    calls = {}

    def fake_ack(by, msg_id, note="", **kw):
        calls.update(by=by, msg_id=msg_id, note=note)
        return calls.pop("_refuse", False) is False

    import core.comm.promoter as promoter
    monkeypatch.setattr(promoter, "ack", fake_ack)
    tb = _toolbox()
    out = tb.bifrost_ack("1784082287759-0")
    assert calls["by"] == "testseek" and calls["msg_id"] == "1784082287759-0"
    assert "ToolBox" in calls["note"]
    assert "acked" in out and "1784082287759-0" in out

    calls["_refuse"] = True
    out2 = tb.bifrost_ack("1784082287759-0")
    assert "REFUSED" in out2, "a False verdict from promoter.ack must be surfaced, not claimed as success"
    assert "bifrost_ack" in _schema_names()


def test_b3_delta_returns_changes():
    tb = _toolbox()
    seen = {}
    tb._agent_cli = lambda args, timeout=90: seen.setdefault("args", list(args)) and "ok" or "ok"
    out = tb.delta()
    assert out == "ok"
    assert seen["args"] == ["delta", "testseek"], \
        f"delta rides the REAL parser (positional agent, no --json/--ack), got {seen['args']}"
    seen.clear()
    tb.delta(agent="claude")
    assert seen["args"] == ["delta", "claude"]
    assert "delta" in _schema_names()


# ------------------------------------------------------- D1-D4: the third-door guard
def test_d1_toolbox_enumerated_and_reality_passes():
    tv = set(cdp.toolbox_verbs())
    assert {"read_file", "bifrost_send", "memory_recall", "knowledge_map",
            "bifrost_ack", "delta"} <= tv, f"enumeration missed core tools: {sorted(tv)}"
    assert len(tv) >= 26, f"design floor is 26+ verbs, got {len(tv)}"
    fails, _gaps, _cli, _mcp = cdp.check()
    assert not fails, f"the guard must PASS on current reality (ship/CI gate): {fails}"


def test_d2_shared_missing_from_toolbox_fails(monkeypatch):
    real = set(cdp.toolbox_verbs())
    monkeypatch.setattr(cdp, "toolbox_verbs", lambda: sorted(real - {"knowledge_map"}))
    fails, _g, _c, _m = cdp.check()
    assert any("knowledge_map" in f and "ToolBox" in f and "third-door regression" in f
               for f in fails), f"the knowledge_map class must FAIL loud, got {fails}"


def test_d3_unclassified_toolbox_verb_fails(monkeypatch):
    real = set(cdp.toolbox_verbs())
    monkeypatch.setattr(cdp, "toolbox_verbs", lambda: sorted(real | {"zz_phantom_tool"}))
    fails, _g, _c, _m = cdp.check()
    assert any("zz_phantom_tool" in f and "unclassified" in f for f in fails), \
        f"a new ToolBox verb must hit the ratchet, got {fails}"


def test_d4_report_includes_toolbox():
    p = subprocess.run([sys.executable, os.path.join("scripts", "check_door_parity.py"), "--report"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0, f"--report must exit 0 on reality:\n{p.stdout}\n{p.stderr}"
    assert "ToolBox (" in p.stdout, "the report must print the third door's surface"
    assert "toolbox_only" in p.stdout, "the report must show the toolbox_only stats"


# ------------------------------------------------- Q1-Q3: private notes ride the boot
def _fake_memory(monkeypatch, notes):
    import core.learning.agent_memory as am
    fake = SimpleNamespace(get_decisions=lambda days=365: notes)
    monkeypatch.setattr(am, "get_agent_memory", lambda: fake)


def _note(title, body, superseded=False):
    return SimpleNamespace(title=title, decision=body, superseded=superseded)


def test_q1_private_notes_in_boot(monkeypatch):
    _fake_memory(monkeypatch, [
        _note("scratch:pintest:alpha", "remember the seam"),
        _note("scratch:pintest:old", "gone", superseded=True),
        _note("scratch:otherseat:beta", "not mine"),
    ])
    out = _runner().fold_private_notes("SYSBASE", "pintest")
    assert out.startswith("SYSBASE"), "the fold appends; it never rewrites the system text"
    assert "YOUR PRIVATE NOTES" in out
    assert "alpha" in out and "remember the seam" in out
    assert "gone" not in out, "superseded notes stay dead"
    assert "not mine" not in out, "another seat's notes never leak into this boot"


def test_q2_notes_truncated_with_pointer(monkeypatch):
    _fake_memory(monkeypatch, [_note("scratch:pintest:long", "x" * 500)])
    out = _runner().fold_private_notes("", "pintest")
    assert "x" * 201 not in out, "each note is clipped to 200 chars"
    assert "memory_recall" in out, "the clip must point at the full-fidelity pull (memory_recall)"


def test_q3_no_notes_boot_clean(monkeypatch):
    _fake_memory(monkeypatch, [])
    out = _runner().fold_private_notes("SYSBASE", "pintest")
    assert out == "SYSBASE", "no notes -> no section, byte-identical boot"
