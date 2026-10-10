"""The replay runner (meta-harness task 04): one scenario, one candidate, N isolated trials.

Pinned here, with a scripted fake agent standing in for the harness:
  * `replay run` produces N run folders with the diff, the raw transcript, metrics and provenance;
  * a run leaves the main checkout, its refs and its remote untouched, and the sandbox has no
    remote, its own AI_SETUP, Redis db 15 and closed proxies;
  * the candidate overlay is in the sandbox but not in the agent's diff;
  * a network tool call with no fixture is an infrastructure failure, a hang is a timeout, and
    a batch stops scheduling at its budget;
  * the same candidate on the same scenario gives the same result across trials.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metaharness import corpus, replay  # noqa: E402

FAKE_AGENT = textwrap.dedent(
    """
    import json, os, subprocess, sys, time
    mode = sys.argv[1]
    prompt = open(sys.argv[2]).read()
    if mode == "hang":
        time.sleep(30)
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout.split()
    keys = ("AI_SETUP", "REDIS_DB", "AKASHIC_WORLD", "AKASHIC_HARNESS", "AKASHIC_MODEL", "HTTPS_PROXY", "AKASHIC_SESSION_ID")
    seen = {k: os.environ.get(k, "") for k in keys}
    seen["remotes"] = remotes
    seen["overlay_present"] = os.path.exists("CLAUDE.md")
    seen["prompt_head"] = prompt.splitlines()[0]
    open("agent_env.json", "w").write(json.dumps(seen, sort_keys=True))
    src = open("calc.py").read().replace("a - b", "a + b")
    open("calc.py", "w").write(src)
    tool = {"type": "tool_use", "name": "WebFetch" if mode == "net" else "Edit", "input": {}}
    print(json.dumps({"type": "assistant", "message": {"content": [tool]}}))
    print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.25, "num_turns": 3,
                      "usage": {"input_tokens": 100, "cache_read_input_tokens": 20, "output_tokens": 7}}))
    """
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A throwaway repo with a remote, one mined scenario, and the fake agent on disk."""
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "remote", "add", "origin", "https://example.invalid/never.git")
    (r / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "init")
    (r / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (r / "tests").mkdir()
    (r / "tests" / "test_calc.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "fix")
    fix = _git(r, "rev-parse", "HEAD")
    hist = [{"to": "done", "at": "2026-10-01T01:00:00+00:00"}]
    lp = tmp_path / "tasks.json"
    lp.write_text(
        json.dumps(
            {"tasks": [{"id": "T9", "title": "make add add", "status": "done", "commit": fix, "history": hist}]}
        ),
        encoding="utf-8",
    )
    corpus.mine(ledger_path=str(lp), repo=r, events=[])
    agent = tmp_path / "fake_agent.py"
    agent.write_text(FAKE_AGENT, encoding="utf-8")
    return r, f"T9-{fix[:8]}", agent


def _cand(name: str, agent: Path, mode: str = "ok", **card) -> None:
    replay.create_candidate(
        name, harness="claude-code", model="fake-model", command=["{python}", str(agent), mode, "{prompt_file}"], **card
    )


def test_a_run_produces_isolated_folders_with_everything_captured(world):
    repo, sid, agent = world
    _cand("c1", agent)
    before = (_git(repo, "status", "--porcelain"), _git(repo, "show-ref"), _git(repo, "remote", "-v"))
    res = replay.run("c1", sid, trials=2, repo=repo)
    assert [r["trial"] for r in res] == [1, 2]
    for r in res:
        d = Path(r["run_dir"])
        assert {p.name for p in d.iterdir()} >= {
            "diff.patch",
            "transcript.jsonl",
            "stderr.log",
            "metrics.json",
            "provenance.json",
            "run.json",
        }
        assert not (d / "sandbox").exists(), "the sandbox clone is removed after the run"
        m = json.loads((d / "metrics.json").read_text())
        assert m["exit_reason"] == "ok"
        assert (m["tokens_in"], m["tokens_out"], m["cost_usd"], m["turns"], m["tool_calls"]) == (120, 7, 0.25, 3, 1)
        assert m["infra_failures"] == []
        diff = (d / "diff.patch").read_text()
        assert "+    return a + b" in diff
        env = json.loads(next(ln[1:] for ln in diff.splitlines() if ln.startswith('+{"AI_SETUP"')))
        assert env["remotes"] == [], "the sandbox has no remote to push to"
        assert env["REDIS_DB"] == "15"
        assert env["AI_SETUP"] == str(d / "state")
        assert env["AKASHIC_WORLD"] == "replay"
        assert env["HTTPS_PROXY"] == replay.CLOSED_PROXY
        assert env["AKASHIC_HARNESS"] == "claude-code"
        assert env["AKASHIC_MODEL"] == "fake-model"
        assert env["prompt_head"] == "# make add add"
        prov = json.loads((d / "provenance.json").read_text())
        assert prov["session_id"] == env["AKASHIC_SESSION_ID"]
    after = (_git(repo, "status", "--porcelain"), _git(repo, "show-ref"), _git(repo, "remote", "-v"))
    assert before == after, "the main checkout, its refs and its remote are untouched"


def test_the_overlay_is_in_the_sandbox_but_not_in_the_diff(world, tmp_path):
    repo, sid, agent = world
    ov = tmp_path / "ov"
    ov.mkdir()
    (ov / "CLAUDE.md").write_text("candidate instructions\n", encoding="utf-8")
    replay.create_candidate(
        "withov", overlay_from=ov, harness="claude-code", command=["{python}", str(agent), "ok", "{prompt_file}"]
    )
    r = replay.run("withov", sid, trials=1, repo=repo)[0]
    diff = Path(r["run_dir"], "diff.patch").read_text()
    assert '"overlay_present": true' in diff
    assert "candidate instructions" not in diff


def test_same_candidate_same_scenario_same_result(world):
    repo, sid, agent = world
    _cand("det", agent)
    res = replay.run("det", sid, trials=3, repo=repo, parallel=3)
    diffs = {Path(r["run_dir"], "diff.patch").read_text().split("agent_env.json")[0] for r in res}
    assert len(diffs) == 1
    assert {r["exit_reason"] for r in res} == {"ok"}


def test_a_network_call_without_a_fixture_is_an_infra_failure(world):
    repo, sid, agent = world
    _cand("net", agent, mode="net")
    r = replay.run("net", sid, trials=1, repo=repo)[0]
    assert r["infra_failures"] == ["WebFetch called with no recorded fixture"]


def test_a_hang_is_a_timeout(world):
    repo, sid, agent = world
    _cand("slow", agent, mode="hang", timeout_s=2)
    r = replay.run("slow", sid, trials=1, repo=repo)[0]
    assert r["exit_reason"] == "timeout"


def test_the_batch_stops_at_its_budget(world):
    repo, sid, agent = world
    _cand("spend", agent)
    res = replay.run("spend", sid, trials=4, repo=repo, budget_usd=0.5)
    assert [r["exit_reason"] for r in res] == ["ok", "ok", "skipped_budget", "skipped_budget"]


def test_cards_refuse_unknown_fields_and_baseline_always_exists():
    with pytest.raises(ValueError, match="unknown candidate fields"):
        replay.create_candidate("bad", modle="x")
    assert replay.candidate("baseline")["harness"] == "claude-code"


def test_the_real_launchers_build_headless_commands(tmp_path):
    pf = tmp_path / "p.md"
    pf.write_text("do it", encoding="utf-8")
    claude = replay.build_command(
        {**replay.DEFAULTS, "model": "claude-opus-5-5", "effort": "high"}, tmp_path, pf, "sid"
    )
    assert claude[:3] == ["claude", "-p", "do it"]
    assert "--session-id" in claude
    assert claude[claude.index("--model") : claude.index("--model") + 2] == ["--model", "claude-opus-5-5"]
    assert claude[claude.index("--effort") : claude.index("--effort") + 2] == ["--effort", "high"]
    assert "project,local" in claude, "user-level settings stay out of a replay"
    codex = replay.build_command(
        {**replay.DEFAULTS, "harness": "codex-cli", "model": "gpt-5", "effort": "low"}, tmp_path, pf, "sid"
    )
    assert codex[:3] == ["codex", "exec", "--json"]
    assert "model_reasoning_effort=low" in codex
    with pytest.raises(ValueError, match="no headless launcher"):
        replay.build_command({**replay.DEFAULTS, "harness": "cursor"}, tmp_path, pf, "sid")


def test_the_cli_refuses_the_live_db():
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "replay", "run", "--candidate", "x", "--scenario", "y", "--redis-db", "0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 2
    assert "live store" in r.stdout


def test_budget_stops_and_api_errors_are_named():
    budget = json.dumps(
        {
            "type": "result",
            "subtype": "error_max_budget_usd",
            "terminal_reason": "budget_exhausted",
            "is_error": True,
            "usage": {"output_tokens": 50},
        }
    )
    api = json.dumps({"type": "result", "terminal_reason": "api_error", "is_error": True, "usage": {}})
    assert replay.parse_metrics(budget).get("budget_exhausted") is True
    assert replay.parse_metrics(api).get("api_error") is True
    assert "api_error" not in replay.parse_metrics(budget)


def test_the_closed_proxy_still_lets_the_harness_reach_its_model(tmp_path):
    env = replay.sandbox_env(tmp_path, session_id="s", card={**replay.DEFAULTS}, fixtures=None, redis_db=15)
    assert env["HTTPS_PROXY"] == replay.CLOSED_PROXY
    assert "api.anthropic.com" in env["NO_PROXY"].split(",")
    assert "api.openai.com" in env["NO_PROXY"].split(",")
