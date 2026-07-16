"""T084 Tier-1 PRE-REGISTERED ACCEPTANCE — IR-3 write-size gauge + IR-6 research_note.

Committed BEFORE implementation (method-baseline pre-registration; T031 rule practiced).
Cites research/reviewed/ironman-plan-2026-07-16.md Tier 1.

Pins:
  IR3-P1  write_file description includes MTU (~65KB / BUS_MAX_MESSAGE_BYTES)
  IR3-P2  edit_file description includes MTU
  IR3-P3  both mention "never silently clipped"
  IR3-P4  both mention "split into multiple calls"
  IR6-P1  research_note tool is registered in TOOLS
  IR6-P2  research_note delegates to knowledge_learn with research:web: prefix
  IR6-P3  knowledge_learn result shape passes through (experiment name + verdict)

Run: py -m pytest tests/test_t084_tier1_ironman.py -q
"""
import os
import sys

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _tool(name):
    """Find a tool dict by its function name (nested under 'function')."""
    from scripts.deepseek_chat import TOOLS
    for t in TOOLS:
        if t.get("function", {}).get("name") == name:
            return t
    raise KeyError(f"tool {name!r} not found in TOOLS")


def _tool_desc(name):
    return _tool(name)["function"]["description"]


# ------------------------------------------------------------------ IR-3 write-size gauge
def test_ir3_p1_write_file_includes_mtu():
    """write_file description must include the MTU number."""
    desc = _tool_desc("write_file")
    assert "65KB" in desc or "65536" in desc or "BUS_MAX_MESSAGE_BYTES" in desc, \
        f"write_file must declare MTU: {desc}"


def test_ir3_p2_edit_file_includes_mtu():
    """edit_file description must include the MTU number."""
    desc = _tool_desc("edit_file")
    assert "65KB" in desc or "65536" in desc or "BUS_MAX_MESSAGE_BYTES" in desc, \
        f"edit_file must declare MTU: {desc}"


def test_ir3_p3_never_silently_clipped():
    """Both descriptions must state the refuse-loud contract."""
    for name in ("write_file", "edit_file"):
        desc = _tool_desc(name)
        assert "never silently clipped" in desc.lower() or "never silently clip" in desc.lower(), \
            f"{name} must state refuse-loud: {desc}"


def test_ir3_p4_split_into_multiple_calls():
    """Both descriptions must advise splitting large work."""
    for name in ("write_file", "edit_file"):
        desc = _tool_desc(name)
        assert "split" in desc.lower() and "multiple" in desc.lower(), \
            f"{name} must advise splitting: {desc}"


# ------------------------------------------------------------------ IR-6 research_note
def test_ir6_p1_research_note_registered():
    """research_note must be in the TOOLS list."""
    t = _tool("research_note")  # raises if missing
    assert t is not None


def test_ir6_p2_research_note_delegates_to_knowledge_learn():
    """research_note must prefix the experiment with research:web:."""
    from pathlib import Path
    from scripts.deepseek_chat import ToolBox
    tb = ToolBox(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda p: False, agent_id="test", allow_write=False,
                 boot_text="", boot_sources=[])
    seen = {}

    def fake_learn(experiment, tried, result, recommend):
        seen["experiment"] = experiment
        seen["tried"] = tried
        seen["result"] = result
        seen["recommend"] = recommend
        return f"recorded {experiment}"

    tb.knowledge_learn = fake_learn
    out = tb.research_note("k8s_owner_references",
                           "searched k8s GC patterns",
                           "found ownerReferences cascade-delete",
                           "use for our ephemeral roster allowlist")
    assert seen["experiment"] == "research:web:k8s_owner_references", \
        f"must prefix with research:web:: {seen['experiment']}"
    assert "k8s_owner_references" in out or "recorded" in out, \
        f"must return knowledge_learn output: {out}"


def test_ir6_p3_research_note_fields_preserved():
    """All four fields must reach knowledge_learn intact."""
    from pathlib import Path
    from scripts.deepseek_chat import ToolBox
    tb = ToolBox(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda p: False, agent_id="test", allow_write=False,
                 boot_text="", boot_sources=[])
    seen = {}

    def fake_learn(experiment, tried, result, recommend):
        seen.update(experiment=experiment, tried=tried, result=result, recommend=recommend)
        return "ok"

    tb.knowledge_learn = fake_learn
    tb.research_note("test_slug", "searched X", "found Y", "recommend Z")
    assert seen["tried"] == "searched X"
    assert seen["result"] == "found Y"
    assert seen["recommend"] == "recommend Z"
    assert seen["experiment"] == "research:web:test_slug"
