"""Sandboxed replay runner: one scenario against one candidate harness (meta-harness task 04).

"Replay" means RE-RUNNING FROM THE SAME STARTING STATE, not replaying the old transcript: once
the harness changes, the path changes. Every comparison later in the programme stands on this
-- candidates (07), memory before and after a lesson (08), modes (10), compression (11).

A CANDIDATE is a folder of harness config plus a card:

    <state>/metaharness/candidates/<name>/
        candidate.json   harness, model, effort, budget, timeout, parent, hypothesis
        overlay/         files laid over the sandbox before launch: CLAUDE.md, AGENTS.md,
                         .claude/settings.json, .claude/skills/, .claude/agents/, hooks ...

`baseline` is the empty overlay: the repo's own config at the scenario's start commit.

ISOLATION, per run:
  * a fresh `git clone --shared` of the repo at start.sha, with its remote REMOVED -- not a
    worktree, because a worktree shares the main repo's remotes and refs;
  * its own AI_SETUP (state under the run folder) and REDIS_DB (15 unless told otherwise),
    plus AKASHIC_WORLD=replay, so nothing reaches the live store or the bus;
  * proxies pointed at a closed port, so an un-fixtured network call fails fast instead of
    reaching the internet. A call with no fixture is recorded as an INFRASTRUCTURE failure of
    the run, never as the agent's failure;
  * the oracle and rubric are NOT in the sandbox. Grading (task 05) applies them afterwards,
    to a copy.

Round one runs in worktree-style clones; a container per run (Harbor, harbor-framework/harbor)
is the upgrade path once agents need system packages or must be kept out of $HOME.

CAPTURE, per run, in runs/<candidate>/<scenario>/<trial>/:
    diff.patch       the final change against start.sha (untracked files included)
    transcript.jsonl the harness's raw event stream (stream-json / --json)
    stderr.log
    metrics.json     exit reason, wall time, tokens, cost, turns, tool calls, infra failures
    provenance.json  the task-01 record of the run's session
    run.json         candidate, scenario, trial, command (with the prompt elided), workdir

The proposer (07) reads these folders directly, raw traces included.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from core.metaharness import home

ROOT = Path(__file__).resolve().parents[2]
CLOSED_PROXY = "http://127.0.0.1:9"
#: The harness's OWN model traffic must get through the closed proxy -- only the agent's tool
#: calls are meant to be cut off. These hosts are exempt (NO_PROXY).
MODEL_API_HOSTS = (
    "api.anthropic.com",
    ".anthropic.com",
    "claude.ai",
    ".claude.ai",
    "api.openai.com",
    "chatgpt.com",
    ".openai.com",
)
DEFAULTS: dict[str, Any] = {
    "harness": "claude-code",
    "model": "",
    "effort": "",
    "budget_usd": 2.0,
    "timeout_s": 1800,
    "parent": "",
    "hypothesis": "",
    "command": [],
    # Extra environment for the sandbox (task 10 switches memory modes through it).
    "env": {},
    # A memory snapshot (memreplay.capture) to load into the run's PRIVATE store. Set, the run
    # gets a file-only store under its own AI_SETUP (Redis pointed at a closed port), so each
    # arm sees exactly one memory state and no arm can see another's.
    "memory": "",
}
CLOSED_REDIS_PORT = "9"
OVERLAY_DELETE = ".aurora/overlay-delete.txt"
_NETWORK_TOOLS = ("WebFetch", "WebSearch")

#: Appended to every scenario prompt, identically for every candidate, so it cannot favour one.
#: A headless run has nobody to answer a question; without this, a model that would normally ask
#: or summarise stops after one turn having changed nothing.
REPLAY_FOOTER = (
    "\n\n---\nYou are running headless in a sandbox clone of this repository. Make the change the "
    "request asks for, in the working tree, and verify it as you normally would. Nobody will answer "
    "questions: decide and proceed. Do not push; there is no remote.\n"
)


# --------------------------------------------------------------------------- candidates
def candidates_dir() -> Path:
    p = home() / "candidates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def runs_dir() -> Path:
    p = home() / "runs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def candidate(name: str) -> dict[str, Any]:
    """The candidate card (defaults filled). `baseline` always exists."""
    d = candidates_dir() / name
    if name == "baseline" and not d.exists():
        create_candidate("baseline", hypothesis="the repo's own config at the scenario's start commit")
    try:
        card = json.loads((d / "candidate.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise KeyError(f"no candidate {name!r}") from e
    return {**DEFAULTS, **card, "name": name, "overlay": str(d / "overlay")}


def create_candidate(name: str, *, overlay_from: str | Path | None = None, **card: Any) -> dict[str, Any]:
    """Create (or replace the card of) a candidate. `overlay_from` copies a folder of config
    files in as the overlay. Unknown card keys are refused, so a typo is never silently ignored."""
    unknown = set(card) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown candidate fields: {sorted(unknown)}")
    d = candidates_dir() / name
    (d / "overlay").mkdir(parents=True, exist_ok=True)
    if overlay_from:
        shutil.copytree(overlay_from, d / "overlay", dirs_exist_ok=True)
    full = {**DEFAULTS, **card}
    (d / "candidate.json").write_text(json.dumps(full, indent=1, sort_keys=True), encoding="utf-8")
    return candidate(name)


def list_candidates() -> list[str]:
    return sorted(p.name for p in candidates_dir().iterdir() if (p / "candidate.json").exists())


# --------------------------------------------------------------------------- sandbox
def _git(*args: str, cwd: Path) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}: {r.stderr.strip()[:300]}")
    return r.stdout


def prepare_sandbox(start_sha: str, workdir: Path, overlay: str | Path | None, *, repo: Path = ROOT) -> None:
    """A clone at start_sha with no remote, the candidate overlay laid on top and committed
    as the sandbox's own base, so the final diff shows the AGENT's change only."""
    _git("clone", "-q", "--shared", "--no-checkout", str(repo), str(workdir), cwd=repo)
    _git("remote", "remove", "origin", cwd=workdir)
    _git("checkout", "-q", "--detach", start_sha, cwd=workdir)
    if overlay and Path(overlay).exists() and any(Path(overlay).iterdir()):
        shutil.copytree(overlay, workdir, dirs_exist_ok=True)
        # An overlay can also REMOVE files (harness compression, task 11): one repo-relative path
        # per line in OVERLAY_DELETE. The list itself never reaches the agent.
        dl = workdir / OVERLAY_DELETE
        if dl.exists():
            for rel in dl.read_text(encoding="utf-8").splitlines():
                rel = rel.strip()
                target = (workdir / rel).resolve()
                if rel and workdir.resolve() in target.parents:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink(missing_ok=True)
            dl.unlink()
        _git("add", "-A", cwd=workdir)
        _git(
            "-c",
            "user.name=replay",
            "-c",
            "user.email=replay@local",
            "commit",
            "-q",
            "--no-verify",
            "-m",
            "candidate overlay",
            cwd=workdir,
        )


def sandbox_env(
    run_dir: Path, *, session_id: str, card: dict[str, Any], fixtures: Path | None, redis_db: int
) -> dict[str, str]:
    keep = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE_CODE_", "CLAUDECODE", "AKASHIC_", "CODEX_", "CURSOR_"))
    }
    env = {
        **keep,
        "AI_SETUP": str(run_dir / "state"),
        "REDIS_DB": str(redis_db),
        "AKASHIC_WORLD": "replay",
        "AKASHIC_SESSION_ID": session_id,
        "AKASHIC_HARNESS": card["harness"],
        "AKASHIC_MODEL": card.get("model") or "",
        "AKASHIC_EFFORT": card.get("effort") or "unknown",
        "AKASHIC_REPLAY": "1",
        "HTTP_PROXY": CLOSED_PROXY,
        "HTTPS_PROXY": CLOSED_PROXY,
        "http_proxy": CLOSED_PROXY,
        "https_proxy": CLOSED_PROXY,
        "NO_PROXY": ",".join(("127.0.0.1", "localhost", *MODEL_API_HOSTS)),
        "no_proxy": ",".join(("127.0.0.1", "localhost", *MODEL_API_HOSTS)),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if fixtures is not None:
        env["AKASHIC_FIXTURES_DIR"] = str(fixtures)
    # Recall's warm cache and scratch state follow this variable; without it every sandbox would
    # share the user's cache -- and with it the LIVE lessons, whatever memory the arm was given.
    env["AKASHIC_RECALL_STATE_DIR"] = str(run_dir / "state" / "recall")
    if card.get("memory"):
        env["REDIS_PORT"] = CLOSED_REDIS_PORT
    env.update({str(k): str(v) for k, v in (card.get("env") or {}).items()})
    (run_dir / "state").mkdir(parents=True, exist_ok=True)
    return env


# --------------------------------------------------------------------------- launchers
def build_command(card: dict[str, Any], workdir: Path, prompt_file: Path, session_id: str) -> list[str]:
    """The headless launch for the candidate's harness. A card's own `command` (a template)
    wins: {prompt_file}, {workdir}, {model}, {effort}, {session_id} are filled in."""
    if card.get("command"):
        fill = {
            "prompt_file": str(prompt_file),
            "workdir": str(workdir),
            "model": card.get("model") or "",
            "effort": card.get("effort") or "",
            "session_id": session_id,
            "python": sys.executable,
        }
        return [str(x).format(**fill) for x in card["command"]]
    prompt = prompt_file.read_text(encoding="utf-8")
    h = card["harness"]
    if h == "claude-code":
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--session-id",
            session_id,
            "--setting-sources",
            "project,local",
            "--permission-mode",
            "bypassPermissions",
            "--max-budget-usd",
            str(card.get("budget_usd") or DEFAULTS["budget_usd"]),
        ]
        if card.get("model"):
            cmd += ["--model", card["model"]]
        if card.get("effort"):
            cmd += ["--effort", card["effort"]]
        return cmd
    if h == "codex-cli":
        cmd = ["codex", "exec", "--json", "-C", str(workdir), "--sandbox", "workspace-write", "--skip-git-repo-check"]
        if card.get("model"):
            cmd += ["-m", card["model"]]
        if card.get("effort"):
            cmd += ["-c", f"model_reasoning_effort={card['effort']}"]
        return [*cmd, prompt]
    raise ValueError(f"no headless launcher for harness {h!r}; give the candidate a `command` template")


# --------------------------------------------------------------------------- capture
def parse_metrics(transcript: str) -> dict[str, Any]:
    """Tokens, cost, turns and tool calls from a stream-json (Claude) or --json (Codex) log."""
    m: dict[str, Any] = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "turns": 0, "tool_calls": 0, "tools": {}}
    for line in transcript.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "result":
            u = ev.get("usage") or {}
            m["tokens_in"] = (
                int(u.get("input_tokens") or 0)
                + int(u.get("cache_read_input_tokens") or 0)
                + int(u.get("cache_creation_input_tokens") or 0)
            )
            m["tokens_out"] = int(u.get("output_tokens") or 0)
            m["cost_usd"] = float(ev.get("total_cost_usd") or ev.get("cost_usd") or 0.0)
            m["turns"] = int(ev.get("num_turns") or 0)
            m["result_subtype"] = ev.get("subtype")
            m["terminal_reason"] = ev.get("terminal_reason")
            if ev.get("terminal_reason") == "api_error" or (ev.get("is_error") and not m["tokens_out"]):
                m["api_error"] = True
            if "budget" in str(ev.get("subtype") or "") or ev.get("terminal_reason") == "budget_exhausted":
                m["budget_exhausted"] = True
        msg = ev.get("message") if ev.get("type") == "assistant" else None
        for block in (msg or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                m["tool_calls"] += 1
                name = str(block.get("name") or "?")
                m["tools"][name] = m["tools"].get(name, 0) + 1
        if ev.get("type") == "turn.completed":  # codex exec --json
            u = ev.get("usage") or {}
            m["tokens_in"] += int(u.get("input_tokens") or 0)
            m["tokens_out"] += int(u.get("output_tokens") or 0)
            m["turns"] += 1
        if ev.get("type") == "item.completed" and (ev.get("item") or {}).get("type") in (
            "command_execution",
            "mcp_tool_call",
        ):
            m["tool_calls"] += 1
    return m


def _final_diff(workdir: Path) -> str:
    _git("add", "-A", "-N", cwd=workdir)  # untracked files appear in the diff, nothing is staged
    return _git("diff", "--binary", "HEAD", cwd=workdir)


def _infra_failures(metrics: dict[str, Any], fixtures: Path | None) -> list[str]:
    has_fixtures = fixtures is not None and fixtures.exists() and any(fixtures.iterdir())
    used = [t for t in _NETWORK_TOOLS if metrics["tools"].get(t)]
    return [f"{t} called with no recorded fixture" for t in used] if used and not has_fixtures else []


# --------------------------------------------------------------------------- run
def run_one(
    cand: str, scenario: str, trial: int, *, repo: Path = ROOT, redis_db: int = 15, keep_sandbox: bool = False
) -> dict[str, Any]:
    """Run one trial. Returns metrics.json's content (plus the run folder path)."""
    from core.metaharness import corpus

    card = candidate(cand)
    sdir = corpus.scenario_dir(scenario)
    if not (sdir / "start.sha").exists():
        raise KeyError(f"no scenario {scenario!r}")
    corpus.seal(scenario)  # graders out of reach: oracle and reference are read-only from here
    run_dir = runs_dir() / cand / scenario / f"t{trial}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    workdir = run_dir / "sandbox"
    session_id = str(uuid.uuid4())
    fixtures = sdir / "fixtures"
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text((sdir / "prompt.md").read_text(encoding="utf-8") + REPLAY_FOOTER, encoding="utf-8")
    t0 = time.monotonic()
    exit_reason, rc = "ok", 0
    out = err = ""
    cmd: list[str] = []
    try:
        prepare_sandbox((sdir / "start.sha").read_text(encoding="utf-8").strip(), workdir, card["overlay"], repo=repo)
        env = sandbox_env(run_dir, session_id=session_id, card=card, fixtures=fixtures, redis_db=redis_db)
        if card.get("memory"):
            from core.metaharness import memreplay

            memreplay.load(Path(card["memory"]), run_dir / "state")
        cmd = build_command(card, workdir, prompt_file, session_id)
        p = subprocess.run(
            cmd,
            cwd=workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=int(card["timeout_s"]),
            check=False,
        )
        rc, out, err = p.returncode, p.stdout, p.stderr
        exit_reason = "ok" if rc == 0 else "error"
    except subprocess.TimeoutExpired as e:
        exit_reason, rc = "timeout", -1
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
    except (RuntimeError, ValueError, OSError) as e:
        exit_reason, rc, err = "infra", -2, str(e)
    wall = round(time.monotonic() - t0, 3)
    (run_dir / "transcript.jsonl").write_text(out, encoding="utf-8")
    (run_dir / "stderr.log").write_text(err, encoding="utf-8")
    diff = ""
    if workdir.exists():
        try:
            diff = _final_diff(workdir)
        except RuntimeError as e:
            err += f"\n[replay] diff capture failed: {e}"
    (run_dir / "diff.patch").write_text(diff, encoding="utf-8")
    metrics = parse_metrics(out)
    infra = _infra_failures(metrics, fixtures)
    if metrics.get("budget_exhausted") and exit_reason == "error":
        exit_reason = "budget"  # stopped by the candidate's spend cap: the diff is a partial result
    if metrics.get("api_error"):  # the harness could not reach its model: not the agent's failure
        infra.append("harness model API error")
        exit_reason = "infra"
    if exit_reason == "infra":
        infra.append(err[:300])
    metrics.update(
        {
            "exit_reason": exit_reason,
            "exit_code": rc,
            "wall_s": wall,
            "infra_failures": infra,
            "diff_lines": diff.count("\n"),
            "candidate": cand,
            "scenario": scenario,
            "trial": trial,
        }
    )
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    prov = {
        "session_id": session_id,
        "harness": card["harness"],
        "model": card.get("model") or "unknown",
        "effort": card.get("effort") or "unknown",
        "candidate": cand,
    }
    (run_dir / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    shown = [("<prompt>" if c == prompt_file.read_text(encoding="utf-8") else c) for c in cmd]
    (run_dir / "run.json").write_text(
        json.dumps(
            {"candidate": cand, "scenario": scenario, "trial": trial, "command": shown, "redis_db": redis_db}, indent=1
        ),
        encoding="utf-8",
    )
    if not keep_sandbox and workdir.exists():
        shutil.rmtree(workdir, ignore_errors=True)
    return {**metrics, "run_dir": str(run_dir)}


def run(
    cand: str,
    scenario: str,
    trials: int = 1,
    *,
    parallel: int = 1,
    budget_usd: float | None = None,
    repo: Path = ROOT,
    redis_db: int = 15,
    keep_sandbox: bool = False,
) -> list[dict[str, Any]]:
    """N isolated trials, up to `parallel` at once. Stops scheduling new trials once the
    batch's spend reaches `budget_usd` (trials already running finish)."""
    results: list[dict[str, Any]] = []
    spent = 0.0
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        pending = []
        for t in range(1, trials + 1):
            if budget_usd is not None and spent >= budget_usd:
                results.append({"candidate": cand, "scenario": scenario, "trial": t, "exit_reason": "skipped_budget"})
                continue
            pending.append(
                pool.submit(run_one, cand, scenario, t, repo=repo, redis_db=redis_db, keep_sandbox=keep_sandbox)
            )
            if len(pending) >= parallel:
                r = pending.pop(0).result()
                spent += float(r.get("cost_usd") or 0.0)
                results.append(r)
        for f in pending:
            r = f.result()
            spent += float(r.get("cost_usd") or 0.0)
            results.append(r)
    return sorted(results, key=lambda r: r.get("trial", 0))


def runs_for(cand: str, scenario: str) -> list[Path]:
    d = runs_dir() / cand / scenario
    return sorted(p for p in d.glob("t*") if (p / "metrics.json").exists()) if d.exists() else []
