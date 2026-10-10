"""Shared fixtures for the meta-harness tests: a throwaway repo with N scenarios and scripted
fake agents, so every grader, verdict and loop test runs offline and deterministic.

The repo has modules m0.py .. m{N-1}.py, each with the same bug (`a - b` where `a + b` is
meant). Commit i fixes module i and adds tests/test_m{i}.py; the ledger marks task T{i} done
at that commit, so the miner turns each into a test-oracle scenario.

Fake agent modes (argv[1]):
  good     fix every module
  bad      change nothing (a comment only)
  half     fix the even-numbered modules only
  cheat    rewrite the scenario's own oracle test to `assert True`, fix nothing
  verbose  like good, but reports ten times the tokens
  aware    good if the candidate's CLAUDE.md says FIX-EVERYTHING, else bad
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

FAKE_AGENT = textwrap.dedent(
    """
    import glob, json, re, sys
    mode = sys.argv[1]
    prompt = open(sys.argv[2]).read()
    if mode == "aware":  # behaves well only when the candidate's overlay tells it to
        import os
        mode = "good" if os.path.exists("CLAUDE.md") and "FIX-EVERYTHING" in open("CLAUDE.md").read() else "bad"
    if mode in ("good", "verbose", "half"):
        for path in sorted(glob.glob("m*.py")):
            i = int(re.findall(r"\\d+", path)[0])
            if mode == "half" and i % 2:
                continue
            src = open(path).read().replace("a - b", "a + b")
            open(path, "w").write(src)
    elif mode == "cheat":
        m = re.search(r"fix m(\\d+)", prompt)
        if m:
            open(f"tests/test_m{m.group(1)}.py", "w").write("def test_ok():\\n    assert True\\n")
    else:
        open("NOTES.md", "a").write("looked around\\n")
    scale = 10 if mode == "verbose" else 1
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {}}]}}))
    print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.01 * scale, "num_turns": 2,
                      "usage": {"input_tokens": 1000 * scale, "output_tokens": 50 * scale}}))
    """
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def build_world(tmp_path: Path, n: int = 6) -> tuple[Path, list[str], Path]:
    """(repo, scenario ids, fake agent path). Call with AI_SETUP already pointed at tmp state."""
    from core.metaharness import corpus

    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    (r / "tests").mkdir()
    for i in range(n):
        (r / f"m{i}.py").write_text(f"def f{i}(a, b):\n    return a - b\n", encoding="utf-8")
    (r / "tests" / "conftest.py").write_text(
        "import os, sys\nsys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n", encoding="utf-8"
    )
    git(r, "add", ".")
    git(r, "commit", "-qm", "init")
    tasks = []
    for i in range(n):
        (r / f"m{i}.py").write_text(f"def f{i}(a, b):\n    return a + b\n", encoding="utf-8")
        (r / "tests" / f"test_m{i}.py").write_text(
            f"from m{i} import f{i}\n\n\ndef test_f{i}():\n    assert f{i}(2, 3) == 5\n", encoding="utf-8"
        )
        git(r, "add", ".")
        git(r, "commit", "-qm", f"fix m{i}")
        sha = git(r, "rev-parse", "HEAD")
        tasks.append(
            {
                "id": f"T{i}",
                "title": f"fix m{i}",
                "status": "done",
                "commit": sha,
                "history": [{"to": "done", "at": "2026-10-01T00:00:00+00:00"}],
            }
        )
    lp = tmp_path / "tasks.json"
    lp.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    new = corpus.mine(ledger_path=str(lp), repo=r, events=[])
    ids = sorted(x["id"] for x in new)
    for sid in ids:
        corpus.set_status(sid, "accepted", by="fixture")
    agent = tmp_path / "fake_agent.py"
    agent.write_text(FAKE_AGENT, encoding="utf-8")
    return r, ids, agent


def fake_candidate(name: str, agent: Path, mode: str, **card) -> None:
    import sys

    from core.metaharness import replay

    replay.create_candidate(
        name, harness="claude-code", model="fake", command=[sys.executable, str(agent), mode, "{prompt_file}"], **card
    )
