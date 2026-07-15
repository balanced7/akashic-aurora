"""
P2 / T022 -- boot orientation header: derived, compact, doctrine-bearing.

Bar: the first lines of boot answer a cold agent's four questions (where is the map /
what governs / what is current / what must I not redo) from LIVE state -- map pointer,
governing-arc note matched against ACTIVE ledger tasks (not merely newest), one-line
where-we-are, the 3-line precedence doctrine, a one-line ledger bar. Spec:
research/reviewed/deepseek-p2-spec-2026-07-09.md (the stateless consumer wrote it).

Run: py -m pytest tests/test_boot_orientation.py -q
"""
import os
import subprocess
import sys
import uuid
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent_cli


def test_precedence_doctrine_is_exactly_three_lines_with_ordered_tiers():
    lines = agent_cli.PRECEDENCE_DOCTRINE.split("\n")
    assert len(lines) == 3, "spec verification item 7: exactly 3 printed lines"
    text = agent_cli.PRECEDENCE_DOCTRINE
    order = [text.index("TASK LEDGER"), text.index("NOTES"),
             text.index("PROMOTED"), text.index("LIVE BUS")]
    assert order == sorted(order), "four tiers in precedence order"
    assert "[STALE]" in text


def _fake_note(title, body, created="2026-07-09T12:00:00"):
    return SimpleNamespace(title=title, decision=body, created_at=created)


def test_governing_arc_prefers_active_match_over_newest(monkeypatch):
    """A parked future arc's note can be NEWER than the live arc's -- active-task slug
    match must win (caught live: visualgen-status outranked comms-pillar-status)."""
    notes = [
        _fake_note("future-thing-status", "see docs/future-plan.md", "2026-07-09T23:00:00"),
        _fake_note("comms-pillar-status", "GOVERNING: docs/comms-pillar-synthesis-2026-07.md"),
        _fake_note("where-we-are", "shipped a bunch; next P3"),
    ]
    import core.learning.agent_memory as am
    import core.coord.task_ledger as tl
    monkeypatch.setattr(am, "get_agent_memory",
                        lambda: SimpleNamespace(get_decisions=lambda days=90: notes))
    monkeypatch.setattr(tl, "state_view", lambda *a, **k: {
        "in_progress": [{"id": "T022", "title": "P2 comms pillar header", "status": "in_progress",
                         "owner": "claude", "commit": None}],
        "next": [], "blocked": [], "done": [], "proposed": [], "counts": {}})
    head = agent_cli._orientation_header("claude")
    assert "docs/comms-pillar-synthesis-2026-07.md" in head, "active-matched note governs"
    assert "docs/future-plan.md" not in head


def test_governing_arc_falls_back_to_newest_when_nothing_active_matches(monkeypatch):
    notes = [_fake_note("solo-arc-status", "doc: docs/solo-arc.md")]
    import core.learning.agent_memory as am
    import core.coord.task_ledger as tl
    monkeypatch.setattr(am, "get_agent_memory",
                        lambda: SimpleNamespace(get_decisions=lambda days=90: notes))
    monkeypatch.setattr(tl, "state_view", lambda *a, **k: {
        "in_progress": [], "next": [], "blocked": [], "done": [], "proposed": [], "counts": {}})
    assert "docs/solo-arc.md" in agent_cli._orientation_header("claude")


def test_where_we_are_renders_single_clipped_line(monkeypatch):
    """Gate-review attack 4 hardened this pin: the clip path must be EXERCISED (long body)
    and the bound is the spec's 120 content chars exactly, not a loose 150."""
    notes = [_fake_note("where-we-are", "line one\nline two\n" + "x" * 400)]
    import core.learning.agent_memory as am
    monkeypatch.setattr(am, "get_agent_memory",
                        lambda: SimpleNamespace(get_decisions=lambda days=90: notes))
    head = agent_cli._orientation_header("claude")
    wwa = next(l for l in head.split("\n") if l.startswith("# where-we-are:"))
    prefix = "# where-we-are: "
    content = wwa[len(prefix):]
    assert "\n" not in wwa
    assert len(content) <= 120, f"spec item 4: content <=120 chars, got {len(content)}"
    assert "line one line two" in wwa, "newlines collapse to spaces"


def test_store_down_prints_honest_gap_line(monkeypatch):
    """Gate-review attack 3: a broken store must yield an explicit gap line, never a
    semantically-empty head."""
    import core.learning.agent_memory as am
    def _boom():
        raise RuntimeError("store down")
    monkeypatch.setattr(am, "get_agent_memory", _boom)
    head = agent_cli._orientation_header("claude")
    assert "notes store unreachable" in head
    assert "docs/ARCHITECTURE.md" in head


def test_cold_start_drill_answers_the_four_questions(tmp_path):
    """THE P2 gate, executable AND hermetic: seed an isolated knowledge layer with a KNOWN
    arc, boot a fresh agent against it, and the head alone must answer the four questions
    -- including WHICH arc governs (gate-review attack 5: the pin must verify the exact
    seeded doc, not any docs/ substring; and the suite's sandbox made a real-store drill
    empty-corpus flaky, so the drill owns its corpus)."""
    env = {**os.environ,
           "AI_SETUP": str(tmp_path),
           "REDIS_DB": os.environ.get("REDIS_DB", "15"),
           "_AISETUP_TEST_ISOLATED": "1"}
    (tmp_path / "session_logs").mkdir(parents=True, exist_ok=True)

    def cli(*cli_args):
        return subprocess.run([sys.executable, "agent_cli.py", *cli_args], cwd=REPO,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120, env=env)

    seeded_arc = f"docs/drill-arc-{uuid.uuid4().hex[:6]}.md"
    r1 = cli("note", "seeder", "--title", "drill-arc-status",
             "--note", f"governing: {seeded_arc} -- the seeded arc")
    assert "[OK] noted" in (r1.stdout or ""), (r1.stdout or "") + (r1.stderr or "")
    r2 = cli("note", "seeder", "--title", "where-we-are",
             "--note", "drill state: seeded corpus, next P3")
    assert "[OK] noted" in (r2.stdout or "")

    p = cli("boot", f"drill-{uuid.uuid4().hex[:8]}", "--task", "cold start")
    head = "\n".join((p.stdout or "").splitlines()[:16])
    assert "# Map: docs/ARCHITECTURE.md" in head, "where is the map"
    assert "# Method: docs/method-baseline-2026-07.md" in head, \
        "HOW we work here answerable from boot alone (Daniel 2026-07-11: best from fresh " \
        "bootup -- the method rides beside the map in the cold-start head)"
    assert seeded_arc in head, "the SEEDED arc governs (newest-with-doc fallback tier)"
    # T074 W13: under a harness session the head carries the FULL where-we-are body
    # ("# where-we-are (full): ..."); bare terminals keep the one-liner. The gate pins
    # the QUESTION (what is current), not the line shape -- both forms must answer it.
    assert ("# where-we-are: drill state: seeded corpus" in head
            or "# where-we-are (full): drill state: seeded corpus" in head), "what is current"
    assert "Precedence when sources conflict" in head, "who wins on conflict"
    assert "RULE: DONE is closed" in head, "what must I not redo"
    assert "DONE (closed -- do NOT redo):" not in head, "the DONE title dump is gone from boot"
