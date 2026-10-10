"""CLI handlers for the meta-harness verbs. agent_cli.py registers the parsers (so the door
checkers see them) and calls straight into these; the logic lives with its package."""

from __future__ import annotations

import json
from typing import Any


def _print(obj: Any, as_json: bool, text: str) -> None:
    print(json.dumps(obj, indent=1, default=str) if as_json else text)


def corpus_main(args) -> int:
    """`corpus <action>` -- the replayable task corpus (task 03)."""
    from core.metaharness import corpus, transcripts

    a = args.action
    if a == "archive":
        r = transcripts.archive(cap_mb=args.cap_mb)
        _print(
            r,
            args.json,
            f"archived {r['archived']}, unchanged {r['unchanged']}, refused {len(r['refused'])}"
            + (" -- SIZE CAP reached, nothing evicted" if r["capped"] else "")
            + f" ({r['bytes'] // 1024 // 1024} MB of {r['cap'] // 1024 // 1024} MB)"
            + "".join(f"\n  refused: {x}" for x in r["refused"]),
        )
        return 0
    if a == "mine":
        new = corpus.mine(limit=args.limit)
        lines = [f"mined {len(new)} new candidate(s)"]
        lines += [
            f"  {n['id']}: " + (n.get("refused") or f"{n['oracle']} oracle, priority {n['priority']}, {n['split']}")
            for n in new
        ]
        if new:
            lines.append("  accept with: corpus accept <id>   (a person curates; the miner only proposes)")
        _print(new, args.json, "\n".join(lines))
        return 0
    if a == "list":
        rows = [corpus.labels(s) for s in corpus.all_ids()]
        if args.status:
            rows = [r for r in rows if r.get("status") == args.status]
        _print(
            rows,
            args.json,
            "\n".join(
                f"  {r['id']:<22} {r.get('status', '?'):<9} {r.get('split', '?'):<7} {r.get('oracle', '?'):<6} "
                f"p={r.get('priority', 0):<3} d={r.get('discrimination', 0):<5} {str(r.get('title') or '')[:60]}"
                for r in rows
            )
            or "(empty corpus -- run `corpus mine`)",
        )
        return 0
    if a == "status":
        st = corpus.status()
        _print(
            st,
            args.json,
            f"{st['total']} scenario(s): {st['by_status']}\n"
            f"accepted {st['accepted']} (holdout {st['holdout']}, validated {st['validated']}), oracles {st['by_oracle']}\n"
            f"areas: {st['areas']}\ncandidates run: {st['candidates_run'] or 'none yet'}",
        )
        return 0
    if a == "retire":
        gone = corpus.retire_saturated()
        _print(gone, args.json, f"retired {len(gone)}: {', '.join(gone) or '-'}")
        return 0
    if not args.id:
        print(f"ERROR: `corpus {a}` needs a scenario id")
        return 2
    try:
        if a == "show":
            lab = corpus.labels(args.id)
            if not lab:
                raise KeyError(args.id)
            prompt = (corpus.scenario_dir(args.id) / "prompt.md").read_text(encoding="utf-8")
            _print(lab, args.json, prompt + "\n" + json.dumps(lab, indent=1))
            return 0
        if a in ("accept", "reject"):
            lab = corpus.set_status(
                args.id, "accepted" if a == "accept" else "rejected", reason=args.reason, by=args.by
            )
            _print(lab, args.json, f"[OK] {args.id} -> {lab['status']} ({lab['split']})")
            return 0
        if a == "validate":
            r = corpus.validate(args.id)
            _print(r, args.json, json.dumps(r))
            return 0 if r.get("ok") is not False else 1
    except KeyError:
        print(f"ERROR: no scenario {args.id!r}")
        return 1
    print(f"ERROR: unknown action {a!r}")
    return 2


def replay_main(args) -> int:
    """`replay <action>` -- run scenarios against candidate harnesses (task 04)."""
    from core.metaharness import replay

    a = args.action
    if a == "candidates":
        rows = [replay.candidate(n) for n in (replay.list_candidates() or ["baseline"])]
        _print(
            rows,
            args.json,
            "\n".join(
                f"  {r['name']:<20} {r['harness']:<12} model={r['model'] or '-'} effort={r['effort'] or '-'}  {r['hypothesis'][:60]}"
                for r in rows
            ),
        )
        return 0
    if a == "new":
        if not args.candidate:
            print("ERROR: `replay new` needs --candidate NAME")
            return 2
        card = {
            k: v
            for k, v in (
                ("harness", args.harness),
                ("model", args.model),
                ("effort", args.effort),
                ("parent", args.parent),
                ("hypothesis", args.hypothesis),
            )
            if v
        }
        c = replay.create_candidate(args.candidate, overlay_from=args.overlay or None, **card)
        _print(c, args.json, f"[OK] candidate {c['name']} ({c['harness']}); overlay: {c['overlay']}")
        return 0
    if a == "run":
        if not (args.candidate and args.scenario):
            print("ERROR: `replay run` needs --candidate C --scenario S")
            return 2
        try:
            res = replay.run(
                args.candidate,
                args.scenario,
                args.trials,
                parallel=args.parallel,
                budget_usd=args.budget_usd,
                redis_db=args.redis_db,
                keep_sandbox=args.keep_sandbox,
            )
        except KeyError as e:
            print(f"ERROR: {e}")
            return 1
        lines = [
            f"  t{r.get('trial')}: {r.get('exit_reason')} wall={r.get('wall_s', 0)}s cost=${r.get('cost_usd', 0):.4f} "
            f"tokens={r.get('tokens_in', 0)}/{r.get('tokens_out', 0)} diff={r.get('diff_lines', 0)} lines"
            + (f" INFRA: {r['infra_failures']}" if r.get("infra_failures") else "")
            + (f"\n      {r['run_dir']}" if r.get("run_dir") else "")
            for r in res
        ]
        _print(res, args.json, f"{args.candidate} x {args.scenario}, {len(res)} trial(s)\n" + "\n".join(lines))
        return 0 if all(r.get("exit_reason") in ("ok", "error", "timeout", "budget") for r in res) else 1
    print(f"ERROR: unknown action {a!r}")
    return 2


def grade_main(args) -> int:
    """`grade <action>` -- graders and verdicts (task 05)."""
    from core.metaharness import graders, replay, stats

    a = args.action
    judge = graders.default_judge if args.judge else None
    if a == "power":
        mde = stats.min_detectable(args.scenarios_n, args.trials)
        pw = stats.power(args.scenarios_n, args.trials, args.delta) if args.delta else None
        _print(
            {"min_detectable": mde, "power": pw},
            args.json,
            f"{args.scenarios_n} scenarios x {args.trials} trials: detects a pass-rate change of "
            f"{mde * 100:.1f} points at 80% power"
            + (f"; power for {args.delta * 100:.0f} points: {pw:.2f}" if pw is not None else ""),
        )
        return 0
    if a == "label":
        if not (args.criterion and args.person and args.judge_call):
            print("ERROR: `grade label` needs --criterion, --person and --judge-call")
            return 2
        graders.add_label(args.criterion, args.person, args.judge_call, ref=args.ref)
        _print(graders.agreement(args.criterion), args.json, json.dumps(graders.agreement(args.criterion)))
        return 0
    if a == "agreement":
        rows = [graders.agreement(c) for c in ("quality", "process")]
        _print(rows, args.json, "\n".join(json.dumps(r) for r in rows))
        return 0
    scenarios = args.scenario or []
    if a == "run":
        if not (args.candidate and scenarios):
            print("ERROR: `grade run` needs --candidate and --scenario")
            return 2
        out = []
        for s in scenarios:
            for rd in replay.runs_for(args.candidate, s):
                g = graders.grade_run(rd, s, judge=judge)
                out.append(
                    {
                        "run": str(rd),
                        **{
                            k: (v or {}).get("score") if isinstance(v, dict) else v
                            for k, v in g.items()
                            if k != "non_functional"
                        },
                    }
                )
        _print(out, args.json, "\n".join(json.dumps(r) for r in out) or "no runs to grade")
        return 0
    if a in ("compare", "noise"):
        if not (args.candidate and args.against and scenarios):
            print(f"ERROR: `grade {a}` needs --candidate B --against A and --scenario ...")
            return 2
        if a == "noise":
            r = graders.noise_check(args.against, args.candidate, scenarios)
            _print(r, args.json, ("OK: no criterion beats its own rerun" if r["ok"] else f"NOISY: {r['spurious']}"))
            return 0 if r["ok"] else 1
        v = graders.compare(args.against, args.candidate, scenarios)
        lines = [f"{v['b']} vs {v['a']} on {len(v['scenarios'])} scenario(s): {v['pareto']}"]
        lines += [
            f"  {k:<14} {r['a']:>10} -> {r['b']:<10} effect {r['effect']:+.4f} CI {r['ci']}  {r['verdict']}"
            for k, r in v["criteria"].items()
        ]
        _print(v, args.json, "\n".join(lines))
        return 0
    print(f"ERROR: unknown action {a!r}")
    return 2


def review_main(args) -> int:
    """`review <action>` -- the human final check-off (task 06)."""
    from core.metaharness import graders, review

    a = args.action
    if a == "list":
        rows = review.pending()
        _print(
            rows,
            args.json,
            "\n".join(
                f"  {r['id']:<28} {r['candidate']} vs {r['against']}  {r['verdict'].get('pareto')}  needs {r['reviewers_needed']}  expires {r['expires']}"
                for r in rows
            )
            or "queue empty",
        )
        return 0
    if a == "watch":
        out = review.watch()
        _print(
            out,
            args.json,
            "\n".join(f"  {r['id']}: {r['status']}" + (f"  WORSE {r['worse']}" if r["worse"] else "") for r in out)
            or "nothing applied under watch",
        )
        return 0
    if a == "disagreements":
        rows = review.disagreements()
        _print(rows, args.json, "\n".join(json.dumps(r) for r in rows) or "no person/grader disagreements recorded")
        return 0
    if a == "add":
        if not (args.candidate and args.against and args.scenario):
            print("ERROR: `review add` needs --candidate, --against and --scenario ...")
            return 2
        v = graders.compare(args.against, args.candidate, args.scenario)
        it = review.enqueue(args.candidate, v, predicted=args.predicted)
        page = review.render(it["id"])
        _print(it, args.json, f"[OK] queued {it['id']} ({v['pareto']}); review page: {page}")
        return 0
    if not args.id:
        print(f"ERROR: `review {a}` needs an item id")
        return 2
    try:
        if a == "show":
            page = review.render(args.id)
            _print(review.item(args.id), args.json, f"review page: {page}")
            return 0
        if a == "decide":
            calls = dict(kv.split("=", 1) for kv in args.calls.replace(",", " ").split() if "=" in kv)
            it = review.decide(args.id, args.reviewer, args.decision, calls, args.reason)
            _print(
                it,
                args.json,
                f"[OK] {args.id}: {it['status']} ({len(it['decisions'])} decision(s), needs {it['reviewers_needed']})",
            )
            return 0
        if a == "apply":
            it = review.apply(args.id)
            _print(
                it,
                args.json,
                f"[OK] applied {args.id}: {len(it['manifest'])} file(s); watched until {it['watch_until']}",
            )
            return 0
        if a == "rollback":
            it = review.rollback(args.id, reason=args.reason or "operator rollback")
            _print(it, args.json, f"[OK] rolled back {args.id}")
            return 0
    except (KeyError, ValueError, PermissionError) as e:
        print(f"ERROR: {e}")
        return 1
    print(f"ERROR: unknown action {a!r}")
    return 2


def loop_main(args) -> int:
    """`loop <action>` -- the candidate archive and the proposer loop (task 07)."""
    from core.metaharness import archive, loop, proposer

    a = args.action
    if a == "status":
        rows = archive.index()
        rep = archive._read_json(proposer._rep_path(), {})
        out = {"candidates": len(rows), "front": archive.front(), "spent_today": loop.spent_today(), "proposers": rep}
        _print(out, args.json, json.dumps(out, indent=1))
        return 0
    if a == "archive":
        rows = archive.index()
        _print(
            rows,
            args.json,
            "\n".join(
                f"  {r['name']:<30} parent={r['parent'] or '-':<24} pass={r['scores'].get('pass_rate')} tokens={r['scores'].get('tokens')}  {r['hypothesis'][:50]}"
                for r in rows
            ),
        )
        return 0
    if a == "lineage":
        _print(archive.lineage(args.candidate), args.json, " <- ".join(archive.lineage(args.candidate)))
        return 0
    if a == "run":
        if args.daily_usd is None:
            print("ERROR: `loop run` needs --daily-usd: the loop spends real money and has no default budget")
            return 2
        logs = loop.run(
            args.candidate or "baseline",
            iterations=args.iterations,
            daily_usd=args.daily_usd,
            proposals=args.proposals,
            trials=args.trials,
            mode=args.mode,
            proposer_card={"model": args.proposer_model} if args.proposer_model else None,
        )
        _print(logs, args.json, "\n".join(json.dumps(x)[:400] for x in logs))
        return 0
    print(f"ERROR: unknown action {a!r}")
    return 2


def memreplay_main(args) -> int:
    """`memreplay <action>` -- replay the memory system before and after a lesson (task 08)."""
    from core.metaharness import memreplay

    a = args.action
    if a == "snapshot":
        p = memreplay.capture(label=args.label or "manual", exclude=tuple(args.exclude or ()))
        _print({"snapshot": str(p)}, args.json, f"[OK] snapshot {p}")
        return 0
    if a == "queue":
        rows = memreplay.queued()
        _print(rows, args.json, "\n".join(f"  {r['lesson']}: {r['why']} at {r['at']}" for r in rows) or "queue empty")
        return 0
    if a == "run":
        if not (args.lesson and args.base):
            print("ERROR: `memreplay run` needs --lesson and --base (the candidate whose harness the arms share)")
            return 2
        out = memreplay.experiment(
            args.lesson, args.base, scenarios=args.scenario or None, trials=args.trials, daily_usd=args.daily_usd
        )
        _print(out, args.json, json.dumps(out.get("proven_effect") or out, indent=1))
        return 0 if "error" not in out else 1
    if a == "drain":
        if args.daily_usd is None or not args.base:
            print("ERROR: `memreplay drain` needs --base and --daily-usd")
            return 2
        out = memreplay.drain(args.base, daily_usd=args.daily_usd, trials=args.trials)
        _print(
            out,
            args.json,
            "\n".join(f"  {o['lesson']}: {(o.get('proven_effect') or {}).get('verdict', o.get('error'))}" for o in out)
            or "nothing queued",
        )
        return 0
    print(f"ERROR: unknown action {a!r}")
    return 2


def precompile_main(args) -> int:
    """`precompile <action>` -- lessons into harness primitives (task 09)."""
    from pathlib import Path

    from core.learning.learning_store import get_learning_store_instance
    from core.metaharness import precompile

    a = args.action
    if a == "check":
        root = Path(args.root) if args.root else precompile.ROOT
        drift = precompile.check_drift(root)
        _print(drift, args.json, "\n".join(drift) or "no drift: every generated piece matches its source hash")
        return 1 if drift else 0
    ls = get_learning_store_instance()
    lessons = ls.load_all_learnings_from_store()
    if args.lesson:
        lessons = [x for x in lessons if x.get("experiment_name") in set(args.lesson)]
    if a == "plan":
        rows = precompile.plan(lessons, store=ls.store)
        _print(
            rows,
            args.json,
            "\n".join(
                f"  {r['lesson']:<40} {r['kind']:<12} {'PASS' if r['gates']['pass'] else 'hold'} "
                f"proven={r['gates']['proven_by']} stable={r['gates']['stable']} premise={r['gates']['premise']} -> {','.join(r['harnesses'])}"
                for r in rows
            )
            or "no lessons",
        )
        return 0
    if a == "build":
        res = precompile.build(
            lessons,
            base=args.base,
            harnesses=tuple(args.harness or precompile.HARNESSES),
            store=ls.store,
            force=args.force,
        )
        _print(
            res,
            args.json,
            json.dumps({k: v for k, v in res.items() if k != "plan"}, indent=1)
            + ("\n(review it: `review add --candidate ...`)" if res.get("built") else ""),
        )
        return 0 if res.get("built") else 1
    print(f"ERROR: unknown action {a!r}")
    return 2
