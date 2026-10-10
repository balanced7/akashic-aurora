"""A replayable task corpus mined from our own history (meta-harness task 03).

The eval set must be OUR work, not a generic benchmark. The seeds are tasks that reached `done`
on the task ledger with a commit and a check: SWE-bench is built the same way -- the request,
the snapshot before the fix, and tests taken from the fix.

ONE FOLDER PER SCENARIO, under <state>/metaharness/corpus/<id>/:

    prompt.md        the request (task title, description, acceptance -- redacted)
    start.sha        the commit BEFORE the work (the landed commit's parent)
    env.json         where the original ran: owner, landed commit, provenance pointer if known
    oracle/          tests.txt + tests.patch (test files the commit added or changed), and/or
                     rubric.md when the commit carries no tests (docs, design, research)
    fixtures/        recorded external responses (filled by the replay runner, task 04)
    reference/       solution.patch (the non-test part of the landed diff) + diff.stat
    labels.json      status, split, oracle kind, criteria, difficulty, tags, signals, outcomes

LIFECYCLE: the miner writes `candidate`; a person `accept`s or `reject`s (curation is human by
design); every candidate passed by every harness candidate is `retire`d by the discrimination
tracker. About 30% of accepted scenarios are held out for final checks only -- assigned by a
hash of the id, so the split never depends on the order they were accepted in.

DISCRIMINATION (Task-CoEvolve): each run outcome is recorded against its scenario. A scenario on
which candidates disagree is worth evaluating; one every candidate passes teaches nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.metaharness import home
from core.metaharness.redact import find_secrets, redact

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT_SHARE = 0.30
STATUSES = ("candidate", "accepted", "rejected", "retired")
_TEST_HINTS = ("tests/", "test_", ".test.", "_test.")


# --------------------------------------------------------------------------- storage
def corpus_dir() -> Path:
    p = home() / "corpus"
    p.mkdir(parents=True, exist_ok=True)
    return p


def scenario_dir(sid: str) -> Path:
    return corpus_dir() / sid


def labels(sid: str) -> dict[str, Any]:
    try:
        return json.loads((scenario_dir(sid) / "labels.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def save_labels(sid: str, lab: dict[str, Any]) -> None:
    _write(scenario_dir(sid) / "labels.json", json.dumps(lab, indent=1, sort_keys=True))


def all_ids() -> list[str]:
    return sorted(p.name for p in corpus_dir().iterdir() if (p / "labels.json").exists())


def split_for(sid: str) -> str:
    """Deterministic ~30% holdout by a hash of the id."""
    h = int(hashlib.sha256(sid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "holdout" if h < HOLDOUT_SHARE else "dev"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- git
def _git(*args: str, repo: Path = ROOT, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=120, check=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout


_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def _resolves(commit: str, repo: Path) -> str:
    """The full sha of a commit that exists here with exactly one parent, else ''. Only a real
    hex sha counts: the ledger also holds symbolic values like 'HEAD', which resolve to
    whatever is checked out NOW and would mint a scenario about the wrong change."""
    if not _SHA.match(str(commit).strip().lower()):
        return ""
    try:
        full = _git("rev-parse", "--verify", f"{commit}^{{commit}}", repo=repo).strip()
        parents = _git("rev-list", "--parents", "-n", "1", full, repo=repo).split()
        return full if len(parents) == 2 else ""  # a merge commit has no single "before"
    except RuntimeError:
        return ""


def is_test_path(p: str) -> bool:
    return any(h in p for h in _TEST_HINTS)


# --------------------------------------------------------------------------- mining
def _signals(owner: str, start: str, end: str, events: list[dict[str, Any]]) -> dict[str, int]:
    """Fails, flips and learnings by the owner inside the task's working window. These are where
    a lesson should have helped, so the miner ranks such tasks first."""
    out = {"fails": 0, "flips": 0, "lessons": 0}
    for e in events:
        at = str(e.get("at") or "")
        if not (start <= at <= end) or (owner and e.get("agent_id") not in (owner, "unknown")):
            continue
        k = e.get("kind")
        if k == "fail":
            out["fails"] += 1
        elif k == "flip":
            out["flips"] += 1
        elif k == "learning":
            out["lessons"] += 1
    return out


def _window(task: dict[str, Any]) -> tuple[str, str]:
    hist = task.get("history") or []
    start = next((h.get("at") for h in hist if h.get("to") in ("claimed", "in_progress")), task.get("created") or "")
    end = next((h.get("at") for h in reversed(hist) if h.get("to") == "done"), task.get("updated") or "")
    return str(start or ""), str(end or "")


def _difficulty(lines: int) -> str:
    return "small" if lines <= 60 else "medium" if lines <= 400 else "large"


def _tags(files: list[str]) -> list[str]:
    tags = []
    for f in files:
        parts = f.split("/")
        tag = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        if tag not in tags:
            tags.append(tag)
    return tags[:8]


def _prompt(task: dict[str, Any]) -> str:
    body = [f"# {task.get('title') or task.get('id')}"]
    if task.get("desc"):
        body.append(str(task["desc"]))
    if task.get("acceptance"):
        body.append(f"## Acceptance\n{task['acceptance']}")
    return redact("\n\n".join(body)) + "\n"


def _rubric(task: dict[str, Any]) -> str:
    return (
        "# Rubric (no test oracle in the landed commit)\n\n"
        f"Task: {task.get('title')}\n\n"
        "Grade the final diff against the reference solution on:\n"
        "1. It does what the request asks (compare reference/solution.patch).\n"
        "2. It touches the right files and nothing unrelated.\n"
        "3. It follows the house conventions (AGENTS.md, commit format).\n"
        "4. No hacks: no skipped hooks, edited tests or faked output.\n"
        + (f"\nStated acceptance:\n{redact(str(task['acceptance']))}\n" if task.get("acceptance") else "")
    )


def mine(
    *,
    ledger_path: str | None = None,
    repo: Path = ROOT,
    events: list[dict[str, Any]] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Write a candidate scenario for every done task with a resolvable commit that the corpus
    does not hold yet. Ranked by outcome signals (fails/flips/lessons in the work window), so
    `limit` keeps the most informative. Returns one summary per new candidate."""
    from core.coord.task_ledger import LEDGER_PATH, read_ledger

    data = read_ledger(ledger_path or os.environ.get("AKASHIC_TASKS_PATH") or LEDGER_PATH, client=None)
    tasks = [t for t in data.get("tasks", []) if str(t.get("status")).lower() == "done" and t.get("commit")]
    if events is None:
        try:
            from core.events.event_log import get_event_log

            events = get_event_log().scan(limit=20000)
        except Exception:  # noqa: BLE001  # fail-soft: mining without signals still mines
            events = []
    have = {labels(s).get("commit") for s in all_ids()}
    cands: list[tuple[int, dict[str, Any], str, dict[str, int]]] = []
    for t in tasks:
        full = _resolves(str(t["commit"]), repo)
        if not full or full in have:
            continue
        have.add(full)
        start, end = _window(t)
        sig = _signals(str(t.get("owner") or ""), start, end, events)
        cands.append((sig["fails"] + 2 * sig["flips"] + sig["lessons"], t, full, sig))
    cands.sort(key=lambda c: -c[0])
    out = []
    for priority, t, full, sig in cands[: limit or None]:
        out.append(_write_candidate(t, full, sig, priority, repo))
    return out


def _write_candidate(task: dict[str, Any], full: str, sig: dict[str, int], priority: int, repo: Path) -> dict[str, Any]:
    sid = f"{task['id']}-{full[:8]}"
    d = scenario_dir(sid)
    parent = _git("rev-parse", f"{full}^", repo=repo).strip()
    files = [f for f in _git("diff", "--name-only", parent, full, repo=repo).splitlines() if f]
    tests = [f for f in files if is_test_path(f)]
    rest = [f for f in files if f not in tests]
    numstat = _git("diff", "--numstat", parent, full, repo=repo)
    lines = sum(
        int(a) + int(b) for a, b, *_ in (ln.split("\t") for ln in numstat.splitlines()) if a.isdigit() and b.isdigit()
    )
    _write(d / "prompt.md", _prompt(task))
    _write(d / "start.sha", parent + "\n")
    _write(
        d / "env.json",
        json.dumps(
            {
                "owner": task.get("owner"),
                "commit": full,
                "task": task.get("id"),
                "verified_by": task.get("verified_by"),
                "source": "task_ledger",
            },
            indent=1,
        ),
    )
    _write(d / "reference" / "diff.stat", _git("diff", "--stat", parent, full, repo=repo))
    if rest:
        _write(
            d / "reference" / "solution.patch", redact(_git("diff", "--binary", parent, full, "--", *rest, repo=repo))
        )
    oracle_kind = "tests" if tests else "rubric"
    if tests:
        _write(d / "oracle" / "tests.txt", "\n".join(tests) + "\n")
        _write(d / "oracle" / "tests.patch", redact(_git("diff", "--binary", parent, full, "--", *tests, repo=repo)))
    else:
        _write(d / "oracle" / "rubric.md", _rubric(task))
    (d / "fixtures").mkdir(parents=True, exist_ok=True)
    lab = {
        "id": sid,
        "task": task.get("id"),
        "title": task.get("title"),
        "commit": full,
        "status": "candidate",
        "split": split_for(sid),
        "oracle": oracle_kind,
        "criteria": ["functional", "correctness", "non_functional", "quality", "process"]
        if tests
        else ["correctness", "non_functional", "quality", "process"],
        "difficulty": _difficulty(lines),
        "lines_changed": lines,
        "files": files,
        "tags": _tags(files),
        "signals": sig,
        "priority": priority,
        "mined_at": _now(),
        "outcomes": {},
        "validated": None,
    }
    save_labels(sid, lab)
    leaks = [
        str(p.relative_to(d))
        for p in d.rglob("*")
        if p.is_file() and find_secrets(p.read_text(encoding="utf-8", errors="replace"))
    ]
    if leaks:  # the redaction check runs on every write; a hit removes the scenario outright
        shutil.rmtree(d, ignore_errors=True)
        return {"id": sid, "refused": f"secret-shaped text in {leaks}"}
    return {"id": sid, "oracle": oracle_kind, "priority": priority, "split": lab["split"]}


# --------------------------------------------------------------------------- curation
def set_status(sid: str, status: str, *, reason: str = "", by: str = "") -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    lab = labels(sid)
    if not lab:
        raise KeyError(f"no scenario {sid!r}")
    lab["status"] = status
    lab.setdefault("history", []).append({"to": status, "at": _now(), "by": by, "reason": reason})
    save_labels(sid, lab)
    return lab


def record_outcome(sid: str, candidate: str, passed: bool) -> dict[str, Any]:
    """Record one run's pass/fail for a candidate harness, and update the scenario's
    discrimination: the share of candidates that disagree with the majority."""
    lab = labels(sid)
    if not lab:
        raise KeyError(f"no scenario {sid!r}")
    o = lab.setdefault("outcomes", {}).setdefault(candidate, {"pass": 0, "fail": 0})
    o["pass" if passed else "fail"] += 1
    lab["discrimination"] = discrimination(lab["outcomes"])
    save_labels(sid, lab)
    return lab


def discrimination(outcomes: dict[str, dict[str, int]]) -> float:
    """0 when every candidate agrees (all pass or all fail), up to 0.5 when they split evenly.
    Per candidate, its majority verdict; then the minority share across candidates."""
    verdicts = [o.get("pass", 0) > o.get("fail", 0) for o in outcomes.values() if o.get("pass", 0) + o.get("fail", 0)]
    if len(verdicts) < 2:
        return 0.0
    k = sum(verdicts)
    return round(min(k, len(verdicts) - k) / len(verdicts), 3)


def retire_saturated(min_candidates: int = 3) -> list[str]:
    """Retire accepted scenarios every one of >= min_candidates candidates passes."""
    gone = []
    for sid in all_ids():
        lab = labels(sid)
        outs = [o for o in (lab.get("outcomes") or {}).values() if o.get("pass", 0) + o.get("fail", 0)]
        if lab.get("status") == "accepted" and len(outs) >= min_candidates and all(o.get("fail", 0) == 0 for o in outs):
            set_status(sid, "retired", reason=f"all {len(outs)} candidates pass: no discrimination")
            gone.append(sid)
    return gone


def select(*, split: str = "dev", n: int | None = None, status: str = "accepted") -> list[str]:
    """Scenarios to spend eval budget on: highest discrimination first, then priority."""
    ids = [s for s in all_ids() if labels(s).get("status") == status and labels(s).get("split") == split]
    ids.sort(key=lambda s: (-(labels(s).get("discrimination") or 0.0), -(labels(s).get("priority") or 0), s))
    return ids[:n] if n else ids


# --------------------------------------------------------------------------- validation
def validate(sid: str, *, repo: Path = ROOT, timeout: int = 900, runner: list[str] | None = None) -> dict[str, Any]:
    """Check a test-oracle scenario is a real test: its oracle FAILS on the start state with the
    tests applied, and PASSES once the reference solution is applied too. Runs in a throwaway
    worktree with REDIS_DB=15 and a temp AI_SETUP; the main checkout is never touched."""
    d = scenario_dir(sid)
    lab = labels(sid)
    if lab.get("oracle") != "tests":
        return {"id": sid, "ok": None, "why": "rubric-only scenario: graded by model and person (task 05)"}
    start = (d / "start.sha").read_text(encoding="utf-8").strip()
    tests = [t for t in (d / "oracle" / "tests.txt").read_text(encoding="utf-8").split() if t.endswith(".py")]
    if not tests:
        return {"id": sid, "ok": None, "why": "oracle has no python tests to run"}
    wt = Path(tempfile.mkdtemp(prefix="mh_validate_")) / "wt"
    env = {**os.environ, "REDIS_DB": "15", "AI_SETUP": str(wt.parent / "ai"), "_AISETUP_TEST_ISOLATED": ""}
    try:
        _git("worktree", "add", "--detach", "-q", str(wt), start, repo=repo)
        _git("apply", "--whitespace=nowarn", str(d / "oracle" / "tests.patch"), repo=wt)

        def run() -> int:
            r = subprocess.run(
                [*(runner or ["uv", "run", "-q", "pytest"]), "-q", "-x", "-p", "no:cacheprovider", *tests],
                cwd=wt,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return r.returncode

        before = run()
        sol = d / "reference" / "solution.patch"
        if sol.exists():
            _git("apply", "--whitespace=nowarn", str(sol), repo=wt)
        after = run()
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        res = {"id": sid, "ok": False, "why": f"could not run: {e}"}
    else:
        ok = before != 0 and after == 0
        res = {"id": sid, "ok": ok, "fails_on_start": before != 0, "passes_on_reference": after == 0}
    finally:
        _git("worktree", "remove", "--force", str(wt), repo=repo, check=False)
        shutil.rmtree(wt.parent, ignore_errors=True)
    lab["validated"] = {**res, "at": _now()}
    save_labels(sid, lab)
    return res


# --------------------------------------------------------------------------- status
def status() -> dict[str, Any]:
    """Corpus size and coverage, for the status view."""
    labs = [labels(s) for s in all_ids()]
    by_status: dict[str, int] = {}
    by_oracle: dict[str, int] = {}
    areas: dict[str, int] = {}
    harnesses: dict[str, int] = {}
    for lab in labs:
        by_status[lab.get("status", "?")] = by_status.get(lab.get("status", "?"), 0) + 1
        if lab.get("status") != "accepted":
            continue
        by_oracle[lab.get("oracle", "?")] = by_oracle.get(lab.get("oracle", "?"), 0) + 1
        for t in lab.get("tags") or []:
            areas[t] = areas.get(t, 0) + 1
        for c in lab.get("outcomes") or {}:
            harnesses[c] = harnesses.get(c, 0) + 1
    acc = [lab for lab in labs if lab.get("status") == "accepted"]
    return {
        "total": len(labs),
        "by_status": by_status,
        "accepted": len(acc),
        "holdout": sum(1 for lab in acc if lab.get("split") == "holdout"),
        "validated": sum(1 for lab in acc if (lab.get("validated") or {}).get("ok")),
        "by_oracle": by_oracle,
        "areas": dict(sorted(areas.items(), key=lambda kv: -kv[1])[:12]),
        "candidates_run": harnesses,
    }
