"""The proposer: a coding agent reads the archive and writes the next candidate (task 07, steps 2-5).

META-HARNESS STYLE (Lee et al. 2026): the proposer is a coding agent (headless Claude Code by
default) that reads the archive's FILES -- including the raw run traces, which beat scores and
summaries by a wide margin in that paper's ablation -- and writes a new candidate. It gets a
context pack:

    brief.md     the goal, the rules below, the current front, scenarios that fail or split
                 candidates, lessons ranked by credit and by repeats, rejected proposals and
                 the reasons people gave
    parents/     the parent candidate's overlay, contract, scores and reviews
    traces/      raw transcripts and diffs of the parent's runs on those scenarios
    out/         where the proposer writes overlay/ (changed files only) and contract.json

RULES, enforced when the proposal is accepted into the archive (not merely asked for):
  * EDIT CONTRACT (AHE): contract.json lists each edit with its kind and path, and the effect it
    PREDICTS -- "S12 passes", "tokens -10%". The loop checks every prediction after the runs, and
    a proposer whose predictions keep failing gets less of the budget.
  * BUNDLE LIMIT (RRSI): at most MAX_EDITS changed overlay files per candidate, so an effect
    stays attributable to its edit.
  * STRUCTURE FIRST (AHE ablation): gains came from tools, middleware and memory structure; a
    system-prompt edit alone hurt. The brief says so, and the loop schedules structural
    candidates first when the budget is short.

PROSE MODE (GEPA): for instruction-file and skill-body edits, the parent is chosen by Pareto
selection PER SCENARIO -- any candidate that is best on at least one scenario -- and the
proposer reflects on that parent's failing traces to rewrite one prose piece.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.metaharness import archive, home, replay

if TYPE_CHECKING:
    from pathlib import Path

MAX_EDITS = 3
EDIT_KINDS = ("instruction", "skill", "subagent", "hook", "tool", "setting", "guard")
DEFAULT_PROPOSER = {
    "harness": "claude-code",
    "model": "claude-opus-5-5",
    "effort": "high",
    "budget_usd": 3.0,
    "timeout_s": 1800,
    "command": [],
}

BRIEF = """# You are the proposer for Aurora's meta-harness

Write ONE new candidate harness for {key} that should beat its parent `{parent}` on our own
replay scenarios. Read the files in this folder before deciding; the raw traces in traces/
show what actually happened -- prefer them over the scores.

## Rules (enforced)
1. Write only CHANGED or NEW files under out/overlay/, at their repo-relative paths
   (CLAUDE.md, AGENTS.md, .claude/settings.json, .claude/skills/<n>/SKILL.md,
   .claude/agents/<n>.md, hook scripts, ...). At most {max_edits} files.
2. Write out/contract.json:
   {{"hypothesis": "...", "edits": [{{"kind": one of {kinds}, "path": "...", "why": "..."}}],
    "predictions": [{{"scenario": "<id>", "metric": "functional", "expect": "pass"}},
                    {{"metric": "tokens", "expect": "-10%"}}]}}
   Every prediction is checked after the runs. Predict only what you expect. pass_rate and
   quality move in absolute points ("+20%" = +0.20); tokens, wall_s and cost_usd move
   relative to the parent ("-10%"). Reaching half the predicted move counts as a hit.
3. Prefer STRUCTURAL edits (tools, hooks, skills, subagents, settings) over prose. Evidence so
   far: structure transfers and helps; a system-prompt edit alone tends to hurt.
4. Never edit tests, graders or anything outside out/.

## Mode: {mode}
{mode_note}

## Current front for {key}
{front}

## Scenarios that fail or split candidates
{scenarios}

## Lessons with the most credit, and the most repeats
{lessons}

## Rejected proposals and why
{rejected}
"""

_MODE_NOTES = {
    "structural": "Change structure: add or adjust a hook, skill, subagent, tool or setting.",
    "prose": "Reflect on the parent's failing traces and rewrite ONE prose piece (an instruction-file section or a skill body). Keep everything else.",
}


def proposals_dir() -> Path:
    p = home() / "proposals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fmt_rows(rows: list[str]) -> str:
    return "\n".join(f"- {r}" for r in rows) or "- (none yet)"


def _lessons_digest(limit: int = 8) -> list[str]:
    """Lessons ranked by recall credit (useful votes) and by recorded repeats. Best-effort."""
    out: list[str] = []
    try:
        from core.learning.learning_store import get_learning_store_instance

        ls = get_learning_store_instance()
        rep: dict[str, int] = {}
        for rid in ls.store.smembers(ls.REPEAT_INDEX):
            of = (ls.store.hgetall(f"learn:repeat:{rid}") or {}).get("of")
            if of:
                rep[of] = rep.get(of, 0) + 1
        for name, n in sorted(rep.items(), key=lambda kv: -kv[1])[:limit]:
            out.append(f"{name}: repeated {n}x")
        from core.recall.at_action import _USE_PREFIX, _load_use

        use = {
            k[len(_USE_PREFIX) :]: _load_use(ls.store, k[len(_USE_PREFIX) :]) for k in ls.store.keys(_USE_PREFIX + "*")
        }
        for src, u in sorted(use.items(), key=lambda kv: -int(kv[1].get("useful", 0) or 0))[:limit]:
            if int(u.get("useful", 0) or 0):
                out.append(f"{src}: useful {u.get('useful')}")
    except Exception:  # noqa: BLE001  # fail-soft: the brief is still useful without lessons
        pass
    return out[: 2 * limit]


def build_pack(parent: str, *, scenarios: list[str], mode: str = "structural", key: str = "") -> Path:
    """Write a context pack for one proposal and return its folder."""
    card = replay.candidate(parent)
    key = key or f"{card['harness']}|{card.get('model') or '-'}|{card.get('effort') or '-'}"
    pid = f"p-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    pack = proposals_dir() / pid
    (pack / "out" / "overlay").mkdir(parents=True)
    shutil.copytree(card["overlay"], pack / "parents" / parent / "overlay", dirs_exist_ok=True)
    (pack / "parents" / parent / "card.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
    (pack / "parents" / parent / "scores.json").write_text(
        json.dumps(archive.scores(parent), indent=1), encoding="utf-8"
    )
    (pack / "parents" / parent / "contract.json").write_text(
        json.dumps(archive.contract(parent), indent=1), encoding="utf-8"
    )
    for s in scenarios:
        for rd in replay.runs_for(parent, s):
            dst = pack / "traces" / s / rd.name
            dst.mkdir(parents=True, exist_ok=True)
            for f in ("transcript.jsonl", "diff.patch", "metrics.json", "grade.json"):
                if (rd / f).exists():
                    shutil.copy2(rd / f, dst / f)
    rows = archive.index()
    front = archive.front(key, rows=rows)
    front_rows = [f"{r['name']}: {r['scores']}" for r in rows if r["name"] in front]
    rejected = [
        f"{r['name']}: {rv['reason']}"
        for r in rows
        for rv in r["reviews"]
        if rv.get("status") in ("rejected", "more_runs", "rolled_back")
    ]
    from core.metaharness import corpus

    sc_rows = [
        f"{s}: discrimination {corpus.labels(s).get('discrimination', 0)}; parent pass {archive.scores(parent).get('per_scenario_pass', {}).get(s)}"
        for s in scenarios
    ]
    brief = BRIEF.format(
        key=key,
        parent=parent,
        max_edits=MAX_EDITS,
        kinds=list(EDIT_KINDS),
        mode=mode,
        mode_note=_MODE_NOTES[mode],
        front=_fmt_rows(front_rows),
        scenarios=_fmt_rows(sc_rows),
        lessons=_fmt_rows(_lessons_digest()),
        rejected=_fmt_rows(rejected),
    )
    (pack / "brief.md").write_text(brief, encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps({"id": pid, "parent": parent, "mode": mode, "key": key, "scenarios": scenarios}, indent=1),
        encoding="utf-8",
    )
    return pack


def run_proposer(pack: Path, proposer: dict[str, Any] | None = None) -> dict[str, Any]:
    """Launch the proposer agent on a pack (cwd = the pack). Returns exit info."""
    import subprocess

    card: dict[str, Any] = {**replay.DEFAULTS, **DEFAULT_PROPOSER, **(proposer or {})}
    cmd = replay.build_command(card, pack, pack / "brief.md", str(uuid.uuid4()))
    try:
        p = subprocess.run(
            cmd,
            cwd=pack,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=int(card["timeout_s"]),
            check=False,
        )
        (pack / "proposer.jsonl").write_text(p.stdout, encoding="utf-8")
        (pack / "proposer.err").write_text(p.stderr, encoding="utf-8")
        metrics = replay.parse_metrics(p.stdout)
        return {
            "exit_code": p.returncode,
            "cost_usd": metrics.get("cost_usd", 0.0),
            "proposer": card.get("model") or card["harness"],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "cost_usd": 0.0, "proposer": card.get("model") or card["harness"], "why": "timeout"}


def validate_contract(c: dict[str, Any], changed: list[str]) -> list[str]:
    """Problems with a proposal's contract against the files it actually changed."""
    errs = []
    edits = c.get("edits") or []
    if not c.get("hypothesis"):
        errs.append("contract has no hypothesis")
    if not edits:
        errs.append("contract lists no edits")
    errs.extend(
        f"edit kind {e.get('kind')!r} is not one of {EDIT_KINDS}" for e in edits if e.get("kind") not in EDIT_KINDS
    )
    if not c.get("predictions"):
        errs.append("contract makes no predictions; an edit with no predicted effect cannot be checked")
    if len(changed) > MAX_EDITS:
        errs.append(f"{len(changed)} files changed; the bundle limit is {MAX_EDITS}")
    if not changed:
        errs.append("the proposal changes no file")
    listed = {str(e.get("path") or "") for e in edits}
    unlisted = [f for f in changed if f not in listed]
    if unlisted:
        errs.append(f"changed files not in the contract: {unlisted}")
    return errs


def accept(pack: Path, *, proposer_id: str = "") -> dict[str, Any]:
    """Turn a pack's out/ into an archive candidate: the parent's overlay plus the proposed
    files. Refused (with reasons) when the contract or the bundle limit is broken."""
    meta = json.loads((pack / "pack.json").read_text(encoding="utf-8"))
    parent = meta["parent"]
    out_overlay = pack / "out" / "overlay"
    changed = sorted(str(p.relative_to(out_overlay)) for p in out_overlay.rglob("*") if p.is_file())
    try:
        c = json.loads((pack / "out" / "contract.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        c = {}
    errs = validate_contract(c, changed)
    if any(".." in f or f.startswith("/") for f in changed):
        errs.append("an overlay path escapes the repo")
    if errs:
        (pack / "refused.json").write_text(json.dumps(errs, indent=1), encoding="utf-8")
        return {"accepted": False, "errors": errs, "pack": str(pack)}
    pcard = replay.candidate(parent)
    name = f"{meta['id']}"
    replay.create_candidate(
        name,
        overlay_from=pcard["overlay"],
        harness=pcard["harness"],
        model=pcard.get("model") or "",
        effort=pcard.get("effort") or "",
        parent=parent,
        hypothesis=str(c.get("hypothesis") or ""),
        command=pcard.get("command") or [],
        budget_usd=pcard.get("budget_usd"),
        timeout_s=pcard.get("timeout_s"),
    )
    shutil.copytree(out_overlay, archive.cdir(name) / "overlay", dirs_exist_ok=True)
    c["proposer"] = proposer_id
    c["mode"] = meta["mode"]
    (archive.cdir(name) / "contract.json").write_text(json.dumps(c, indent=1), encoding="utf-8")
    (archive.cdir(name) / "parent.diff").write_text(archive.overlay_diff(parent, name), encoding="utf-8")
    return {"accepted": True, "candidate": name, "parent": parent, "changed": changed}


# --------------------------------------------------------------------------- predictions
def _rel(change: float, base: float) -> float:
    return (change - base) / base if base else 0.0


def check_predictions(name: str) -> dict[str, Any]:
    """Score the contract's predictions against the graded runs of the candidate and its
    parent. Unverifiable predictions (no runs on that scenario) are counted apart."""
    c = archive.contract(name)
    parent = replay.candidate(name).get("parent") or "baseline"
    mine, theirs = archive.scores(name), archive.scores(parent)
    results = []
    for pr in c.get("predictions") or []:
        metric, expect = str(pr.get("metric") or ""), str(pr.get("expect") or "")
        ok: bool | None = None
        if metric == "functional" and pr.get("scenario"):
            got = mine.get("per_scenario_pass", {}).get(pr["scenario"])
            ok = None if got is None else (got >= 0.5) == (expect == "pass")
        elif metric in ("tokens", "wall_s", "cost_usd", "pass_rate", "quality") and expect.endswith("%"):
            a, b = mine.get(metric), theirs.get(metric)
            if a is not None and b is not None:
                want = float(expect.rstrip("%")) / 100
                # Rates (0..1) move in absolute points: "+20%" is +0.2, which stays defined when
                # the parent scored 0. Costs move relatively: "tokens -10%" is a 10% cut.
                got = (a - b) if metric in ("pass_rate", "quality") else _rel(a, b)
                # Half the predicted move, in the predicted direction, counts as a hit.
                ok = (got <= want / 2) if want < 0 else (got >= want / 2)
        results.append({**pr, "ok": ok})
    checked = [r for r in results if r["ok"] is not None]
    out = {"candidate": name, "results": results, "hits": sum(1 for r in checked if r["ok"]), "checked": len(checked)}
    (archive.cdir(name) / "prediction.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    _update_reputation(str(c.get("proposer") or "unknown"), out["hits"], out["checked"])
    return out


def _rep_path() -> Path:
    return home() / "proposers.json"


def _update_reputation(proposer: str, hits: int, checked: int) -> None:
    rep = archive._read_json(_rep_path(), {})
    r = rep.setdefault(proposer, {"hits": 0, "checked": 0})
    r["hits"] += hits
    r["checked"] += checked
    _rep_path().write_text(json.dumps(rep, indent=1), encoding="utf-8")


def budget_weight(proposer: str) -> float:
    """Share of the proposal budget a proposer earns: Laplace-smoothed prediction accuracy.
    A new proposer starts at 0.5; one whose predictions keep failing falls toward 0."""
    r = archive._read_json(_rep_path(), {}).get(proposer) or {"hits": 0, "checked": 0}
    return (r["hits"] + 1) / (r["checked"] + 2)


def gepa_parents(rows: list[dict[str, Any]]) -> list[str]:
    """GEPA's per-scenario Pareto selection: every candidate that is best (or tied best) on at
    least one scenario. Keeps diverse specialists alive instead of one average winner."""
    best: dict[str, float] = {}
    for r in rows:
        for s, v in (r["scores"].get("per_scenario_pass") or {}).items():
            best[s] = max(best.get(s, 0.0), v)
    return sorted(
        {
            r["name"]
            for r in rows
            for s, v in (r["scores"].get("per_scenario_pass") or {}).items()
            if v >= best[s] and v > 0
        }
    )
