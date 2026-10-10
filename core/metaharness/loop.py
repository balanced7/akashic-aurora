"""The meta-harness loop: propose, run, grade, select, queue for review (task 07, steps 7-9).

ONE ITERATION
  1. PROPOSE: k proposals from the current front. The proposal budget is split by each
     proposer's prediction accuracy (proposer.budget_weight); parents for prose mode are chosen
     GEPA-style (best on at least one scenario).
  2. SPEND ADAPTIVELY (successive halving): every new candidate runs on a few high-disagreement
     dev scenarios; the top third by pass rate advances to more scenarios; repeat. Structural
     candidates are scheduled before prose ones when the budget runs short (AHE). Concentrating
     budget on what matters is the point -- spreading it evenly froze progress in one study.
  3. SELECT: the Pareto front over pass rate, quality, tokens, time and cost, per
     (harness, model, effort).
  4. FINALISTS run on the HELD-OUT scenarios; one that beats its parent there (verdict
     dominates or trade-off with a functional win) goes to the human review queue (task 06).
     Every prediction in every contract is checked.

SCHEDULE: `loop run` performs iterations until its daily spend cap is reached. It never
touches the live harness -- review.apply after a person's accept is the only path there.
Spend is recorded per day in loop/spend.json, from the cost each run and proposer reports.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.metaharness import archive, corpus, graders, home, proposer, replay, review, stats


def _loop_dir() -> Path:
    p = home() / "loop"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def spent_today() -> float:
    return float(archive._read_json(_loop_dir() / "spend.json", {}).get(_today(), 0.0))


def _spend(usd: float) -> None:
    p = _loop_dir() / "spend.json"
    d = archive._read_json(p, {})
    d[_today()] = round(float(d.get(_today(), 0.0)) + float(usd or 0.0), 6)
    p.write_text(json.dumps(d, indent=1, sort_keys=True), encoding="utf-8")


class BudgetExhausted(Exception):
    pass


def _guard(daily_usd: float) -> None:
    if spent_today() >= daily_usd:
        raise BudgetExhausted(f"daily budget ${daily_usd:.2f} reached (spent ${spent_today():.2f})")


def evaluate(
    cand: str,
    scenarios: list[str],
    *,
    trials: int,
    daily_usd: float,
    repo: Path,
    runner: list[str] | None = None,
    judge=None,
) -> None:
    """Run and grade `cand` on each scenario it has not run yet, within the daily budget."""
    for s in scenarios:
        if len(replay.runs_for(cand, s)) >= trials:
            continue
        _guard(daily_usd)
        for r in replay.run(cand, s, trials=trials, repo=repo):
            _spend(float(r.get("cost_usd") or 0.0))
            if r.get("run_dir"):
                graders.grade_run(Path(r["run_dir"]), s, repo=repo, runner=runner, judge=judge)
                g = json.loads((Path(r["run_dir"]) / "grade.json").read_text(encoding="utf-8"))
                score = (g.get("functional") or {}).get("score")
                if score is not None:
                    corpus.record_outcome(s, cand, score >= 0.5)


def successive_halving(
    cands: list[str],
    ladder: list[int],
    *,
    trials: int,
    daily_usd: float,
    repo: Path,
    keep: float = 1 / 3,
    runner: list[str] | None = None,
    judge=None,
) -> list[str]:
    """Run every candidate on ladder[0] scenarios, keep the top `keep` share by pass rate, run
    the survivors on ladder[1] scenarios, and so on. Returns the final survivors."""
    dev = corpus.select(split="dev")
    alive = sorted(cands, key=lambda c: (not archive.is_structural(c), c))  # structure first
    for rung, n in enumerate(ladder):
        scen = dev[:n]
        done = []
        for c in alive:
            try:
                evaluate(c, scen, trials=trials, daily_usd=daily_usd, repo=repo, runner=runner, judge=judge)
                done.append(c)
            except BudgetExhausted:
                break
        ranked = sorted(done, key=lambda c: -(archive.scores(c, scen).get("pass_rate") or 0.0))
        if rung == len(ladder) - 1:
            return ranked
        alive = ranked[: max(1, round(len(ranked) * keep))]
    return alive


def iterate(
    parent: str,
    *,
    proposals: int = 3,
    ladder: tuple[int, ...] = (3, 8),
    trials: int = 1,
    holdout_n: int = 10,
    daily_usd: float,
    repo: Path = replay.ROOT,
    proposer_card: dict[str, Any] | None = None,
    mode: str = "structural",
    runner: list[str] | None = None,
    judge=None,
) -> dict[str, Any]:
    """One loop iteration from `parent`. Returns what happened, for the log."""
    log: dict[str, Any] = {
        "parent": parent,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "proposed": [],
        "refused": [],
    }
    rows = archive.index()
    parents = proposer.gepa_parents(rows) if mode == "prose" else [parent]
    parents = [p for p in parents if p] or [parent]
    focus = corpus.select(split="dev")[: max(ladder)]
    pid = str((proposer_card or proposer.DEFAULT_PROPOSER).get("model") or "proposer")
    n_props = max(1, round(proposals * proposer.budget_weight(pid) / 0.5)) if proposals else 0
    for i in range(min(n_props, proposals * 2)):
        _guard(daily_usd)
        pack = proposer.build_pack(parents[i % len(parents)], scenarios=focus, mode=mode)
        res = proposer.run_proposer(pack, proposer_card)
        _spend(float(res.get("cost_usd") or 0.0))
        acc = proposer.accept(pack, proposer_id=pid)
        (log["proposed"] if acc["accepted"] else log["refused"]).append(acc.get("candidate") or acc)
    evaluate(
        parent,
        corpus.select(split="dev")[: max(ladder)],
        trials=trials,
        daily_usd=daily_usd,
        repo=repo,
        runner=runner,
        judge=judge,
    )
    survivors = successive_halving(
        log["proposed"], list(ladder), trials=trials, daily_usd=daily_usd, repo=repo, runner=runner, judge=judge
    )
    log["survivors"] = survivors
    hold = corpus.select(split="holdout")[:holdout_n]
    queued = []
    for c in survivors[:2]:
        try:
            evaluate(c, hold, trials=trials, daily_usd=daily_usd, repo=repo, runner=runner, judge=judge)
            evaluate(parent, hold, trials=trials, daily_usd=daily_usd, repo=repo, runner=runner, judge=judge)
        except BudgetExhausted:
            break
        proposer.check_predictions(c)
        v = graders.compare(parent, c, hold)
        fn = (v["criteria"].get("functional") or v["criteria"].get("correctness") or {}).get("verdict")
        if v["pareto"] in ("dominates", "trade-off") and fn == stats.BETTER:
            it = review.enqueue(c, v, predicted=str(archive.contract(c).get("hypothesis") or ""))
            review.render(it["id"])
            queued.append(it["id"])
    for c in log["proposed"]:
        if c not in survivors[:2]:
            proposer.check_predictions(c)
    log["queued_for_review"] = queued
    log["front"] = archive.front()
    log["spent_today"] = spent_today()
    with (_loop_dir() / "iterations.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(log) + "\n")
    return log


def run(parent: str, *, iterations: int, daily_usd: float, **kw: Any) -> list[dict[str, Any]]:
    """Unattended: iterate until `iterations` are done or the day's budget is spent."""
    logs = []
    for _ in range(iterations):
        try:
            logs.append(iterate(parent, daily_usd=daily_usd, **kw))
        except BudgetExhausted as e:
            logs.append({"stopped": str(e)})
            break
    return logs
