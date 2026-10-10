"""The candidate archive (meta-harness task 07, step 1): every candidate, never only the winner.

Each diff is one point in a solution space, and later proposals learn from earlier ones -- so
the archive keeps all of them, with their scores and their full traces. A candidate folder
(created by replay.create_candidate) gathers, over its life:

    candidate.json   the card: harness, model, effort, parent, hypothesis
    overlay/         the config it lays over the repo
    contract.json    the proposer's edit contract: the edits and their PREDICTED effects
    parent.diff      the overlay against its parent's overlay (what this candidate changed)
    reviews.jsonl    human review outcomes and reasons (task 06)
    prediction.json  how the predictions turned out once the runs were graded

Runs live in runs/<candidate>/... and verdicts in verdicts/ (tasks 04, 05). This module joins
them into one index, keyed by (harness, model, effort) -- each gets its own Pareto front,
because a harness that is best for one model can be worst for another.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from statistics import fmean
from typing import Any

from core.metaharness import replay, stats

#: Front axes and their direction (higher is better?).
AXES = {"pass_rate": True, "quality": True, "tokens": False, "wall_s": False, "cost_usd": False}
STRUCTURAL = ("skill", "subagent", "hook", "tool", "setting", "guard")
PROSE = ("instruction",)


def cdir(name: str) -> Path:
    return replay.candidates_dir() / name


def _read_json(p: Path, default: Any) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def contract(name: str) -> dict[str, Any]:
    return _read_json(cdir(name) / "contract.json", {})


def reviews(name: str) -> list[dict[str, Any]]:
    p = cdir(name) / "reviews.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def overlay_diff(parent: str, child: str) -> str:
    """Unified diff of child's overlay against parent's (an empty parent overlay = baseline)."""
    po, co = Path(replay.candidate(parent)["overlay"]), Path(replay.candidate(child)["overlay"])
    files = sorted(
        {str(p.relative_to(po)) for p in po.rglob("*") if p.is_file()}
        | {str(p.relative_to(co)) for p in co.rglob("*") if p.is_file()}
    )
    out: list[str] = []
    for rel in files:
        a = (
            (po / rel).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            if (po / rel).exists()
            else []
        )
        b = (
            (co / rel).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            if (co / rel).exists()
            else []
        )
        out.extend(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}"))
    return "".join(out)


def changed_files(parent: str, child: str) -> list[str]:
    lines = overlay_diff(parent, child).splitlines()
    return sorted({ln[6:] for ln in lines if ln.startswith(("+++ b/", "--- a/"))})


def lineage(name: str) -> list[str]:
    """name, its parent, its parent's parent ... back to a root. Cycles stop the walk."""
    chain, seen = [name], {name}
    while True:
        parent = replay.candidate(chain[-1]).get("parent") or ""
        if not parent or parent in seen or not cdir(parent).exists():
            return chain
        chain.append(parent)
        seen.add(parent)


def scores(name: str, scenarios: list[str] | None = None) -> dict[str, Any]:
    """Mean headline grades over the candidate's graded runs (optionally limited to scenarios).
    pass_rate averages per scenario first, as the verdicts do."""
    rd = replay.runs_dir() / name
    per: dict[str, dict[str, list[float]]] = {}
    for gp in sorted(rd.glob("*/t*/grade.json")) if rd.exists() else []:
        sc = gp.parent.parent.name
        if scenarios is not None and sc not in scenarios:
            continue
        g = _read_json(gp, {})
        nf = g.get("non_functional") or {}
        if nf.get("infra_failures"):
            continue
        row = per.setdefault(sc, {k: [] for k in AXES})
        fn = (g.get("functional") or {}).get("score")
        if fn is None:
            fn = (g.get("correctness") or {}).get("score")
        if fn is not None:
            row["pass_rate"].append(float(fn))
        q = (g.get("quality") or {}).get("score")
        if q is not None:
            row["quality"].append(float(q))
        for k in ("tokens", "wall_s", "cost_usd"):
            if nf.get(k) is not None:
                row[k].append(float(nf[k]))
    out: dict[str, Any] = {"scenarios": len(per)}
    for k in AXES:
        vals = [fmean(v[k]) for v in per.values() if v[k]]
        out[k] = round(fmean(vals), 4) if vals else None
    out["per_scenario_pass"] = {s: round(fmean(v["pass_rate"]), 4) for s, v in per.items() if v["pass_rate"]}
    return out


def index() -> list[dict[str, Any]]:
    rows = []
    for name in replay.list_candidates():
        card = replay.candidate(name)
        rows.append(
            {
                "name": name,
                "key": f"{card['harness']}|{card.get('model') or '-'}|{card.get('effort') or '-'}",
                "parent": card.get("parent") or "",
                "hypothesis": card.get("hypothesis") or "",
                "contract": contract(name),
                "reviews": reviews(name),
                "scores": scores(name),
            }
        )
    return rows


def front(key: str | None = None, *, rows: list[dict[str, Any]] | None = None) -> list[str]:
    """Names on the Pareto front for one (harness|model|effort) key, over the axes every
    candidate in the group has a value for. Unscored candidates are not on any front."""
    rows = [
        r for r in (rows or index()) if (key is None or r["key"] == key) and r["scores"].get("pass_rate") is not None
    ]
    if not rows:
        return []
    axes = {k: hib for k, hib in AXES.items() if all(r["scores"].get(k) is not None for r in rows)}
    return stats.pareto({r["name"]: {k: r["scores"][k] for k in axes} for r in rows}, axes)


def edit_kinds(name: str) -> list[str]:
    return [str(e.get("kind") or "") for e in (contract(name).get("edits") or [])]


def is_structural(name: str) -> bool:
    kinds = edit_kinds(name)
    return bool(kinds) and any(k in STRUCTURAL for k in kinds)
