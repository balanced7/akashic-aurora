"""Two execution modes for memory: interpretive and precompiled (meta-harness task 10).

  interpretive  today: lessons are retrieved and shown at the moment of action (boot, recall,
                recall at action). Adapts instantly to a new lesson; costs context every time.
  precompiled   lessons are baked into the harness's primitives (task 09) and recall at action
                pushes nothing. Cheap at run time and preventive; slow to change, can go stale.
  hybrid        the aim -- "most but not all" precompiled: compiled lessons live in the harness,
                and recall at action covers only what is left, as the safety net.

THE SWITCH is one variable, AKASHIC_MEMORY_MODE, set per harness config (an overlay's
.claude/settings.json env, or a candidate card's env). Unset means interpretive: nothing changes
for anyone who has not chosen.

IN HYBRID, recall at action and boot skip any lesson whose `compiled_into` mark (stamped by
review.apply, task 09) names the ACTIVE harness. So no lesson is both compiled into a harness and
pushed at action time in that same harness -- the acceptance this module pins.

THE COMPARISON runs four arms on the same scenarios, model and trials -- bare (no memory),
interpretive, precompiled, hybrid -- and reports each arm's pass rate, tokens, time and cost
with intervals, plus the default it recommends: the best pass rate, then the cheapest among
arms that cannot be told apart from it.

PLACEMENT moves single lessons between modes on evidence: promote a stable, proven lesson that
is still interpretive; demote a compiled one whose pieces are never used or whose lesson keeps
changing. STALENESS: a compiled lesson that is edited, benched or found wrong flags its pieces
and queues a recompile.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MODES = ("interpretive", "precompiled", "hybrid")
DEFAULT = "interpretive"
_HARNESS_FILES = {
    "claude-code": "claude-code",
    "codex-cli": "codex-cli",
    "codex-desktop": "codex-cli",
    "cursor": "cursor",
}


def mode(env: dict[str, str] | None = None) -> str:
    m = ((env if env is not None else os.environ).get("AKASHIC_MEMORY_MODE") or DEFAULT).strip().lower()
    return m if m in MODES else DEFAULT


def _harness_now() -> str:
    try:
        from core.fleet.provenance import detect_harness

        h = detect_harness()
    except Exception:  # noqa: BLE001  # fail-soft: unknown harness compiles nothing away
        return ""
    if h.startswith("runner"):
        return "runner"
    return _HARNESS_FILES.get(h, "")


def compiled_here(item: dict[str, Any], harness: str) -> bool:
    """Is this lesson compiled into `harness` (per its compiled_into mark)?"""
    raw = item.get("compiled_into") or ""
    if not raw or not harness:
        return False
    try:
        where = json.loads(raw) if isinstance(raw, str) else raw
        return harness in (where.get("harnesses") or {})
    except (TypeError, ValueError, AttributeError):
        return False


def filter_for_mode(
    items: list[dict[str, Any]], *, env: dict[str, str] | None = None, harness: str | None = None
) -> list[dict[str, Any]]:
    """What interpretive recall may push in the current mode: everything (interpretive),
    nothing (precompiled), or everything not compiled into the active harness (hybrid)."""
    m = mode(env)
    if m == "interpretive":
        return items
    if m == "precompiled":
        return []
    h = _harness_now() if harness is None else harness
    return [it for it in items if not compiled_here(it, h)]


# --------------------------------------------------------------------------- the four arms
RECALL_HOOK = {
    "matcher": "Bash|PowerShell|Edit|Write|NotebookEdit",
    "hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/agent/harness/hooks/claude_pretooluse.py"'}],
}


def _with_recall_hook(overlay: Path, live_root: Path) -> None:
    """Make an overlay's .claude/settings.json register the recall-at-action hook (opt-in in the
    repo itself), starting from the overlay's own settings or the live ones."""
    p = overlay / ".claude" / "settings.json"
    src = p if p.exists() else live_root / ".claude" / "settings.json"
    try:
        doc = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
    except ValueError:
        doc = {}
    pre = doc.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if not any("claude_pretooluse.py" in json.dumps(e) for e in pre):
        pre.append(RECALL_HOOK)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def arms(
    base: str, compiled: str, *, tag: str = "", live_root: Path | None = None, store: Any = None
) -> dict[str, str]:
    """Create the four arm candidates. `base` carries the harness and model; `compiled` is a
    precompiled candidate (task 09) on top of it. Returns arm -> candidate name."""
    import shutil

    from core.metaharness import memreplay, replay

    live_root = live_root or replay.ROOT
    tag = tag or compiled
    b = replay.candidate(base)
    after = memreplay.capture(store=store, label=f"{tag}-modes")
    spec = {
        "bare": (base, memreplay.empty_snapshot(), "interpretive", False),
        "interpretive": (base, after, "interpretive", True),
        "precompiled": (compiled, after, "precompiled", False),
        "hybrid": (compiled, after, "hybrid", True),
    }
    names = {}
    for arm, (src, snap, m, hook) in spec.items():
        name = f"mode-{tag}-{arm}"
        replay.create_candidate(
            name,
            harness=b["harness"],
            model=b.get("model") or "",
            effort=b.get("effort") or "",
            command=b.get("command") or [],
            env={**(b.get("env") or {}), "AKASHIC_MEMORY_MODE": m, "AKASHIC_RECALL_AT_ACTION": "1" if hook else "0"},
            memory=str(snap),
            parent=src,
            hypothesis=f"memory mode arm '{arm}'",
            budget_usd=b.get("budget_usd"),
            timeout_s=b.get("timeout_s"),
        )
        ov = Path(replay.candidate(name)["overlay"])
        shutil.copytree(replay.candidate(src)["overlay"], ov, dirs_exist_ok=True)
        if hook:
            _with_recall_hook(ov, live_root)
        names[arm] = name
    return names


def compare(
    base: str,
    compiled: str,
    scenarios: list[str],
    *,
    trials: int = 3,
    repo: Path | None = None,
    runner: list[str] | None = None,
    store: Any = None,
    daily_usd: float | None = None,
) -> dict[str, Any]:
    """Run the four arms and report per harness and model, with the default mode chosen."""
    from core.metaharness import archive, graders, replay, stats

    names = arms(base, compiled, live_root=repo, store=store)
    spent = 0.0
    for cand in names.values():
        for s in scenarios:
            if daily_usd is not None and spent >= daily_usd:
                break
            for r in replay.run(cand, s, trials=trials, repo=repo or replay.ROOT):
                spent += float(r.get("cost_usd") or 0.0)
                if r.get("run_dir"):
                    graders.grade_run(Path(r["run_dir"]), s, repo=repo or replay.ROOT, runner=runner)
    rows = {arm: archive.scores(c, scenarios) for arm, c in names.items()}
    vs = {
        arm: graders.compare(names["interpretive"], c, scenarios) for arm, c in names.items() if arm != "interpretive"
    }
    # The default is a MODE, so bare (no memory) is reported but never recommended. Among the
    # modes: the best pass rate, plus every mode that cannot be told apart from it; then the
    # cheapest in tokens; then precompiled before hybrid before interpretive.
    modes_only = [a for a in names if a != "bare"]
    best = max(modes_only, key=lambda a: rows[a].get("pass_rate") or 0.0)
    tied = []
    for a in modes_only:
        if a == best or (rows[a].get("pass_rate") or 0.0) >= (rows[best].get("pass_rate") or 0.0):
            tied.append(a)
            continue
        fn = graders.compare(names[best], names[a], scenarios)["criteria"]
        fn = fn.get("functional") or fn.get("correctness") or {}
        if fn.get("verdict") == stats.CANT_TELL:
            tied.append(a)
    order = {"precompiled": 0, "hybrid": 1, "interpretive": 2}
    chosen = min(tied, key=lambda a: (rows[a].get("tokens") or float("inf"), order[a]))
    card = replay.candidate(base)
    report = {
        "harness": card["harness"],
        "model": card.get("model") or "",
        "effort": card.get("effort") or "",
        "arms": names,
        "scores": rows,
        "vs_interpretive": {
            arm: {k: {"effect": c["effect"], "ci": c["ci"], "verdict": c["verdict"]} for k, c in v["criteria"].items()}
            for arm, v in vs.items()
        },
        "default_mode": chosen,
        "tied_with_best": sorted(tied),
        "spent_usd": round(spent, 4),
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    out = _dir() / f"report-{card['harness']}-{card.get('model') or 'default'}.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def _dir() -> Path:
    from core.metaharness import home

    p = home() / "modes"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- placement and staleness
def stale(lesson: dict[str, Any]) -> str:
    """Why a compiled lesson's pieces may be stale ('' when they are not)."""
    raw = lesson.get("compiled_into") or ""
    if not raw:
        return ""
    try:
        at = str(json.loads(raw).get("at") or "")
    except (TypeError, ValueError, AttributeError):
        return ""
    if str(lesson.get("benched") or "").strip():
        return "benched after it was compiled"
    if str(lesson.get("timestamp") or "")[:19] > at[:19]:
        return "edited after it was compiled"
    try:
        from core.metaharness.memreplay import DAMP, ranker_factor

        if lesson.get("proven_effect") and ranker_factor(lesson["proven_effect"]) == DAMP:
            return "replay found it makes outcomes worse"
    except Exception:  # noqa: BLE001  # no replay module means no replay verdict
        pass
    return ""


def placement(
    lessons: list[dict[str, Any]], *, used: dict[str, int] | None = None, store: Any = None
) -> list[dict[str, Any]]:
    """Per-lesson move: compile, demote, recompile, or keep. `used` is piece path -> uses."""
    from core.metaharness import precompile

    used = used or {}
    rows = []
    for x in lessons:
        name = x.get("experiment_name")
        compiled = bool(x.get("compiled_into"))
        why = stale(x)
        if compiled and why:
            rows.append({"lesson": name, "move": "recompile", "why": why})
            continue
        if compiled:
            try:
                where = json.loads(x["compiled_into"]).get("harnesses") or {}
            except (TypeError, ValueError):
                where = {}
            paths = [p for ps in where.values() for p in ps]
            if paths and not any(used.get(p) for p in paths):
                rows.append({"lesson": name, "move": "demote", "why": "its compiled pieces are never used"})
            else:
                rows.append({"lesson": name, "move": "keep", "why": "compiled and in use"})
            continue
        use = precompile._use_for(store, x) if store is not None else {}
        g = precompile.gates(x, use=use)
        if g["pass"] and precompile.route(x) != "interpretive":
            rows.append({"lesson": name, "move": "compile", "why": f"proven by {g['proven_by']}, stable, premise ok"})
        else:
            rows.append({"lesson": name, "move": "keep", "why": "stays interpretive"})
    return rows


def flag_stale(name: str, why: str, previous: dict[str, Any] | None) -> None:
    """Called on every lesson change (learning_store's trigger): a compiled lesson that changes
    flags its pieces and queues a recompile candidate."""
    if not previous or not previous.get("compiled_into"):
        return
    try:
        with (_dir() / "recompile_queue.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "lesson": name,
                        "why": why,
                        "compiled_into": previous.get("compiled_into"),
                        "at": datetime.now(UTC).isoformat(timespec="seconds"),
                    }
                )
                + "\n"
            )
    except Exception:  # noqa: BLE001  # a flag is bookkeeping; the lesson write is what matters
        pass


def recompile_queue() -> list[dict[str, Any]]:
    p = _dir() / "recompile_queue.jsonl"
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()] if p.exists() else []
