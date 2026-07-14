"""T048 -- recall surface polish (deepseek interview -> deepseek design -> claude build).

Design: research/reviewed/deepseek-t048-design-2026-07-14.md (deepseek, accepted w/ two
grounding corrections: CLI needs --hint-style too because the ToolBox wire shells the CLI;
boot-source truth = the runner's onboarding text, since neither ledger records boot).

Pins:
  H1 render hint_style="tool" names callable TOOLS; default stays CLI-shaped (backward compat).
  H2 legend line renders ONLY when a surfaced lesson carries credibility markers.
  T1 new tools registered (recall_at, knowledge_full; knowledge_recall gains novelty).
  T2 recall_at maps args to the CLI incl. --hint-style tool.
  N1 _boot_sources extracted from onboarding text; novelty tags [boot]/[new], fail-open.
  L1 release_written_locks releases every guarded-write lock and clears the list.

Run: py -m pytest tests/test_t048_recall_surfaces.py -q
"""
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from core.recall.at_action import render
import deepseek_chat as dc


def _result(lessons, total=None):
    return {"lessons": lessons, "total": total if total is not None else len(lessons)}


def _lesson(source="learn:experiment:x", use=None, success="yes"):
    return {"text": "use when testing, do the thing", "source": source,
            "success": success, "agent_id": "claude", "_use": use or {}}


# ---------------------------------------------------------------- H1: hint styles
def test_hint_style_tool_names_callable_tools():
    out = render(_result([_lesson()], total=5), hint_style="tool")
    assert "recall_at(limit=5)" in out
    assert "knowledge_full(source=" in out
    assert "`recall-at --limit" not in out, "tool style must not render CLI verbs"


def test_hint_style_default_stays_cli():
    out = render(_result([_lesson()], total=5))
    assert "`recall-at --limit 5`" in out
    assert "recall_at(limit=" not in out


# ---------------------------------------------------------------- H2: legend gate
def test_legend_renders_on_credibility_markers():
    out = render(_result([_lesson(use={"helped": 2, "useful": 1})]))
    assert "[legend]" in out and "helped=auto credit" in out


def test_legend_silent_on_plain_lessons():
    out = render(_result([_lesson()]))
    assert "[legend]" not in out, "surface discipline: no markers -> no legend"


# ---------------------------------------------------------------- T1: registration
def test_new_tools_registered():
    names = {t["function"]["name"] for t in dc.TOOLS}
    assert {"recall_at", "knowledge_full", "knowledge_recall"} <= names
    kr = next(t for t in dc.TOOLS if t["function"]["name"] == "knowledge_recall")
    assert "novelty" in kr["function"]["parameters"]["properties"]


def _toolbox(boot_text=""):
    return dc.ToolBox(Path("E:/AI-Setup"), allow_exec=False, trust=False, allow_secrets=False,
                      confirm=lambda _p: False, agent_id="testagent", boot_text=boot_text)


# ---------------------------------------------------------------- T2: recall_at mapping
def test_recall_at_tool_maps_args(monkeypatch):
    tb = _toolbox()
    calls = []
    monkeypatch.setattr(tb, "_agent_cli", lambda args, timeout=90: calls.append(args) or "ok")
    tb.recall_at(limit=7, path="core/comm/bus.py")
    args = calls[0]
    assert args[0] == "recall-at" and "--limit" in args and "7" in args
    assert "--hint-style" in args and "tool" in args, "tool-loop pulls must get tool-shaped hints"
    assert "--path" in args


# ---------------------------------------------------------------- N1: novelty tagging
def test_boot_sources_extracted():
    tb = _toolbox(boot_text="lessons: (source: learn:experiment:foo_bar) and learn:experiment:baz-qux too")
    assert tb._boot_sources == {"learn:experiment:foo_bar", "learn:experiment:baz-qux"}


def test_novelty_tags_boot_vs_new(monkeypatch):
    tb = _toolbox(boot_text="learn:experiment:seen_one")
    payload = json.dumps([{"source": "learn:experiment:seen_one"}, {"source": "learn:experiment:fresh"}])
    monkeypatch.setattr(tb, "_agent_cli", lambda args, timeout=90: payload)
    out = json.loads(tb.knowledge_recall("q", novelty=True))
    tags = {e["source"]: e["_novelty"] for e in out}
    assert tags["learn:experiment:seen_one"] == "[boot]"
    assert tags["learn:experiment:fresh"] == "[new]"


def test_novelty_fail_open_on_bad_json(monkeypatch):
    tb = _toolbox()
    monkeypatch.setattr(tb, "_agent_cli", lambda args, timeout=90: "not-json")
    assert tb.knowledge_recall("q", novelty=True) == "not-json"


# ---------------------------------------------------------------- L1: lock release
def test_release_written_locks(monkeypatch):
    tb = _toolbox()
    tb._written_lock_paths = ["E:/AI-Setup/research/reviewed/a.md", "E:/AI-Setup/docs/b.md"]
    calls = []
    monkeypatch.setattr(tb, "_agent_cli", lambda args, timeout=90: calls.append(args) or "released")
    n = tb.release_written_locks()
    assert n == 2 and tb._written_lock_paths == []
    assert all(a[0] == "unlock" and a[1] == "testagent" for a in calls)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
