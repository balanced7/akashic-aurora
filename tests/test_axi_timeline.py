"""Pins for `timeline` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_timeline.py -q
"""

import argparse

import pytest

import agent_cli


def _gathered(rows, failed=None, undated=0):
    counts: dict = {}
    for r in rows:
        counts[r["domain"]] = counts.get(r["domain"], 0) + 1
    return {
        "rows": rows,
        "blind": ["a standing caveat"],
        "coverage": {
            "read": list(counts),
            "failed": failed or {},
            "counts": counts,
            "undated": undated,
            "n": len(rows),
        },
    }


def _row(i, domain="events", kind="deploy", actor="alice"):
    return {"ts": 1_790_000_000 + i, "domain": domain, "actor": actor, "kind": kind, "summary": f"row {i}",
            "ref": f"event:events:raw:{i}-0" if domain == "events" else ""}  # fmt: skip


@pytest.fixture
def gathered(monkeypatch):
    from core.coord import timeline as tl

    holder = {"r": _gathered([])}
    monkeypatch.setattr(tl, "gather", lambda since=None: holder["r"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, hours=6.0, limit=60):
    code = agent_cli.cmd_timeline(argparse.Namespace(hours=hours, limit=limit, json=False))
    return code, capsys.readouterr()


def test_rows_coverage_and_a_drill_hint(gathered, capsys):
    gathered["r"] = _gathered([_row(1), _row(2, domain="git", kind="commit", actor="bob")])
    code, cap = _run(capsys)
    assert code == 0
    assert "window: last 6h\ntotal: 2" in cap.out
    assert "rows[2]{at,domain,actor,kind,summary}:" in cap.out
    assert "events --get event:events:raw:1-0" in cap.out
    assert cap.err == ""  # nothing an agent needs goes to stderr any more


def test_a_cut_list_says_shown_and_how_to_see_all(gathered, capsys):
    gathered["r"] = _gathered([_row(i) for i in range(5)])
    _, cap = _run(capsys, limit=2)
    assert "total: 5\nshown: 2" in cap.out
    assert "timeline --hours 6 --limit 0" in cap.out


def test_an_unread_domain_is_on_stdout(gathered, capsys):
    gathered["r"] = _gathered([], failed={"git": "RuntimeError: not a git repository"})
    _, cap = _run(capsys)
    assert "not_read:" in cap.out
    assert 'git: "RuntimeError: not a git repository"' in cap.out


def test_empty_window_is_total_zero_with_a_wider_window_hint(gathered, capsys):
    code, cap = _run(capsys, hours=1)
    assert code == 0
    assert "total: 0" in cap.out
    assert "timeline --hours 4" in cap.out


def test_human_view(gathered, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    gathered["r"] = _gathered([_row(1)], failed={"tasks": "FileNotFoundError: x"})
    _, cap = _run(capsys)
    assert "1 rows · last 6h" in cap.out
    assert "not read: tasks" in cap.out
    assert "deploy" in cap.out
