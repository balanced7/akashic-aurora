"""T081-W6 (claude sub-part): the boot --sources-json sidecar emits normalized lesson-source
pointers, so the runner ToolBox tags boot-known lessons without regex-parsing rendered text.
"""
import json
import agent_cli


def test_normalize_bare_experiment_name():
    assert agent_cli._normalize_boot_source("gate_exit_codes_never_piped") \
        == "learn:experiment:gate_exit_codes_never_piped"


def test_normalize_mem_namespace():
    # deepseek W6-P1 convention: mem:decision:ADR -> learn:experiment:mem_decision_ADR
    assert agent_cli._normalize_boot_source("mem:decision:ADR_071503") \
        == "learn:experiment:mem_decision_ADR_071503"


def test_normalize_already_qualified_passes_through():
    q = "learn:experiment:foo"
    assert agent_cli._normalize_boot_source(q) == q


def test_normalize_empty_is_empty():
    assert agent_cli._normalize_boot_source("") == ""
    assert agent_cli._normalize_boot_source(None) == ""


def test_source_list_dedups_and_normalizes():
    secs = {"learnings": [
        {"source": "alpha"},
        {"source": "mem:task:T067"},
        {"source": "alpha"},            # dup -> collapsed
        {"source": "learn:experiment:beta"},
        {"nosource": 1},                # missing source -> skipped
    ]}
    got = agent_cli._boot_source_list(secs)
    assert got == ["learn:experiment:alpha",
                   "learn:experiment:mem_task_T067",
                   "learn:experiment:beta"]


def test_sidecar_file_is_written(tmp_path):
    # the emission path itself: a JSON file with a 'sources' list
    p = tmp_path / "sources.json"
    secs = {"learnings": [{"source": "alpha"}, {"source": "mem:x:y"}]}
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"sources": agent_cli._boot_source_list(secs)}, f)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["sources"] == ["learn:experiment:alpha", "learn:experiment:mem_x_y"]
