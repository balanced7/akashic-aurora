"""CLI handlers for the meta-harness verbs. agent_cli.py registers the parsers (so the door
checkers see them) and calls straight into these; the logic lives with its package.

Every handler prints in one of three ways: `--json` (unchanged, the data function's own
result), or through core.axi.out -- TOON for an agent, a rich layout for a person -- with the
next commands to run. The data functions stay pure; only this module prints."""

from __future__ import annotations

import json
from typing import Any

from core.axi import out


def _print(obj: Any, as_json: bool, text: str) -> None:
    print(json.dumps(obj, indent=1, default=str) if as_json else text)


def _json(obj: Any) -> None:
    """The --json output, byte for byte what it always was."""
    print(json.dumps(obj, indent=1, default=str))


def _cli() -> str:
    """The command prefix for next-step hints (agent_cli._cli, without importing agent_cli)."""
    from core.paths import cli_command

    return cli_command()


def _usage(message: str, *hints: str) -> int:
    return out.fail(message, code="USAGE", hints=list(hints), exit_code=out.EXIT_USAGE)


def _missing(e: KeyError) -> str:
    """A KeyError's message as written (str() of a KeyError wraps it in quotes)."""
    return str(e.args[0]) if e.args else "not found"


#: `corpus list` columns: the default agent schema, and every field --fields can add.
_CORPUS_FIELDS = ("id", "status", "split", "oracle", "title")
_CORPUS_ALL_FIELDS = ("id", "status", "split", "oracle", "title", "priority", "discrimination", "difficulty", "tags")


def corpus_main(args) -> int:
    """`corpus <action>` -- the replayable task corpus (task 03)."""
    from core.metaharness import corpus, transcripts

    a, cli = args.action, _cli()
    if a == "archive":
        r = transcripts.archive(cap_mb=args.cap_mb)
        if args.json:
            _json(r)
            return 0
        doc: dict[str, Any] = {
            "archived": r["archived"],
            "unchanged": r["unchanged"],
            "refused": len(r["refused"]),
            "size_mb": r["bytes"] // 1024 // 1024,
            "cap_mb": r["cap"] // 1024 // 1024,
            "capped": r["capped"],  # the size cap was reached; nothing is ever evicted
        }
        if r["refused"]:
            doc["refused_sessions"] = r["refused"]
        return out.emit(doc, hints=[f"{cli} corpus mine"], title="Transcript archive")
    if a == "mine":
        new = corpus.mine(limit=args.limit)
        if args.json:
            _json(new)
            return 0
        rows = [
            {
                "id": n["id"],
                "oracle": n.get("oracle"),
                "priority": n.get("priority"),
                "split": n.get("split"),
                "refused": n.get("refused"),
            }
            for n in new
        ]
        if not any(r["refused"] for r in rows):
            rows = [{k: v for k, v in r.items() if k != "refused"} for r in rows]
        # A person curates; the miner only proposes -- so the next step is a review.
        ok = [r["id"] for r in rows if not r.get("refused")]
        hints = [f"{cli} corpus show {ok[0]}", f"{cli} corpus accept {ok[0]} --reason <why>"] if ok else []
        return out.emit(
            {"mined": len(rows), "candidates": rows},
            hints=hints or [f"{cli} corpus status"],
            title="Corpus mining",
        )
    if a == "list":
        rows = [corpus.labels(s) for s in corpus.all_ids()]
        if args.status:
            rows = [r for r in rows if r.get("status") == args.status]
        if args.json:
            _json(rows)
            return 0
        try:
            fields = out.fields_arg(getattr(args, "fields", None), _CORPUS_FIELDS, _CORPUS_ALL_FIELDS)
        except ValueError as e:
            return _usage(str(e), f"{cli} corpus list --fields priority,discrimination")
        doc = {"status": args.status} if args.status else {}
        if not rows:  # AXI section 5: the zero is the answer, with how to fill it
            doc.update(total=0, scenarios=[])
            hint = f"{cli} corpus list" if args.status else f"{cli} corpus mine"
            return out.emit(doc, hints=[hint], title="Corpus")
        table = []
        for r in rows:
            full = {
                "id": r.get("id"),
                "status": r.get("status"),
                "split": r.get("split"),
                "oracle": r.get("oracle"),
                "title": out.truncate(r.get("title"), 60)[0] or None,
                "priority": r.get("priority", 0),
                "discrimination": r.get("discrimination", 0),
                "difficulty": r.get("difficulty"),
                "tags": ", ".join(r.get("tags") or []) or None,
            }
            table.append({f: full[f] for f in fields})
        doc.update(total=len(table), scenarios=table)
        return out.emit(doc, hints=[f"{cli} corpus show <id>"], title="Corpus")
    if a == "status":
        st = corpus.status()
        if args.json:
            _json(st)
            return 0
        # An empty breakdown prints as a bare "key:" in TOON, which reads as missing data: leave
        # it out, the zero counts above it already say there is nothing to break down.
        doc = {k: v for k, v in st.items() if v != {}}
        doc["candidates_run"] = st["candidates_run"] or "none yet"
        hint = f"{cli} corpus list --status candidate" if st["total"] else f"{cli} corpus mine"
        return out.emit(doc, hints=[hint], title="Corpus status")
    if a == "retire":
        gone = corpus.retire_saturated()
        if args.json:
            _json(gone)
            return 0
        return out.emit({"retired": len(gone), "ids": gone}, title="Corpus retire")
    if not args.id:
        return _usage(f"`corpus {a}` needs a scenario id", f"{cli} corpus {a} <id>", f"{cli} corpus list")
    try:
        if a == "show":
            lab = corpus.labels(args.id)
            if not lab:
                raise KeyError(args.id)
            path = corpus.scenario_dir(args.id) / "prompt.md"
            prompt = path.read_text(encoding="utf-8")
            if args.json:
                _json(lab)
                return 0
            keep = ("id", "title", "status", "split", "oracle", "difficulty", "priority", "discrimination", "tags")
            doc = {k: lab[k] for k in keep if lab.get(k) not in (None, "", [])}
            text, cut = out.truncate(prompt, 800)
            doc["prompt"] = text
            if cut:
                doc["prompt_file"] = str(path)
            # The labels behind this summary (files, outcomes, history) are one flag away.
            return out.emit(doc, hints=[f"{cli} corpus show {args.id} --json"], title=args.id)
        if a in ("accept", "reject"):
            lab = corpus.set_status(
                args.id, "accepted" if a == "accept" else "rejected", reason=args.reason, by=args.by
            )
            if args.json:
                _json(lab)
                return 0
            return out.emit(
                {"id": args.id, "status": lab["status"], "split": lab["split"]},
                hints=[f"{cli} corpus list --status candidate"],
                title="Corpus curation",
            )
        if a == "validate":
            r = corpus.validate(args.id)
            if args.json:
                _json(r)
            else:
                out.emit(r, title=f"Validate · {args.id}")
            return 0 if r.get("ok") is not False else 1
    except KeyError:
        return out.fail(f"no scenario {args.id!r}", code="NOT_FOUND", hints=[f"{cli} corpus list"])
    return _usage(f"unknown action {a!r}", f"{cli} corpus --help")


def replay_main(args) -> int:
    """`replay <action>` -- run scenarios against candidate harnesses (task 04)."""
    from core.metaharness import replay

    a, cli = args.action, _cli()
    if a == "candidates":
        rows = [replay.candidate(n) for n in (replay.list_candidates() or ["baseline"])]
        if args.json:
            _json(rows)
            return 0
        table = [
            {
                "name": r["name"],
                "harness": r["harness"],
                "model": r["model"] or None,
                "effort": r["effort"] or None,
                "hypothesis": out.truncate(r["hypothesis"], 60)[0] or None,
            }
            for r in rows
        ]
        # A run spends model budget, so the suggested command carries a budget cap.
        first = table[0]["name"]
        return out.emit(
            {"total": len(table), "candidates": table},
            hints=[
                f"{cli} replay run --candidate {first} --scenario <id> --budget-usd 2",
                f"{cli} replay new --candidate <name> --harness codex-cli --model <model>",
            ],
            title="Replay candidates",
        )
    if a == "new":
        if not args.candidate:
            return _usage(
                "`replay new` needs --candidate NAME", f"{cli} replay new --candidate <name> --harness claude-code"
            )
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
        if args.json:
            _json(c)
            return 0
        doc = {k: c[k] or None for k in ("name", "harness", "model", "effort", "parent", "overlay")}
        return out.emit(doc, hints=[f"{cli} replay candidates"], title="Replay candidate created")
    if a == "run":
        if not (args.candidate and args.scenario):
            return _usage(
                "`replay run` needs --candidate C --scenario S",
                f"{cli} replay run --candidate {args.candidate or 'baseline'} --scenario {args.scenario or '<id>'} --budget-usd 2",
                f"{cli} corpus list --status accepted",
            )
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
            return out.fail(_missing(e), code="NOT_FOUND", hints=[f"{cli} replay candidates", f"{cli} corpus list"])
        ok = all(r.get("exit_reason") in ("ok", "error", "timeout", "budget") for r in res)
        if args.json:
            _json(res)
            return 0 if ok else 1
        trials = []
        for r in res:
            row = {
                "trial": r.get("trial"),
                "exit_reason": r.get("exit_reason"),
                "wall_s": r.get("wall_s", 0),
                "cost_usd": round(float(r.get("cost_usd") or 0), 4),
                "tokens_in": r.get("tokens_in", 0),
                "tokens_out": r.get("tokens_out", 0),
                "diff_lines": r.get("diff_lines", 0),
                "infra_failures": r.get("infra_failures") or None,
                "run_dir": r.get("run_dir") or None,
            }
            trials.append(row)
        doc = {
            "candidate": args.candidate,
            "scenario": args.scenario,
            "trials": len(trials),
            "cost_usd": round(sum(float(r.get("cost_usd") or 0) for r in res), 4),
            "results": trials,
        }
        out.emit(
            doc,
            hints=[f"{cli} grade run --candidate {args.candidate} --scenario {args.scenario}"],
            title=f"Replay · {args.candidate} x {args.scenario}",
        )
        return 0 if ok else 1
    return _usage(f"unknown action {a!r}", f"{cli} replay --help")


def _verdict_rows(v: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per criterion of a graders.compare() verdict: A, B, effect and its interval."""
    return [
        {
            "criterion": k,
            "a": r["a"],
            "b": r["b"],
            "effect": r["effect"],
            "ci": f"{r['ci'][0]}..{r['ci'][1]}",
            "verdict": r["verdict"],
        }
        for k, r in v["criteria"].items()
    ]


def grade_main(args) -> int:
    """`grade <action>` -- graders and verdicts (task 05)."""
    from core.metaharness import graders, replay, stats

    a, cli = args.action, _cli()
    judge = graders.default_judge if args.judge else None
    if a == "power":
        mde = stats.min_detectable(args.scenarios_n, args.trials)
        pw = stats.power(args.scenarios_n, args.trials, args.delta) if args.delta else None
        if args.json:
            _json({"min_detectable": mde, "power": pw})
            return 0
        doc: dict[str, Any] = {
            "scenarios": args.scenarios_n,
            "trials": args.trials,
            # The smallest pass-rate change, in points, this design detects at the target power.
            "target_power": 0.8,
            "min_detectable_change_points": round(mde * 100, 1),
        }
        if pw is not None:
            doc.update(change_points=round(args.delta * 100), power_for_change=round(pw, 2))
        return out.emit(doc, title="Grading power")  # a calculation answers itself
    if a == "label":
        if not (args.criterion and args.person and args.judge_call):
            return _usage(
                "`grade label` needs --criterion, --person and --judge-call",
                f"{cli} grade label --criterion quality --person <call> --judge-call <call> --ref <run>",
            )
        graders.add_label(args.criterion, args.person, args.judge_call, ref=args.ref)
        ag = graders.agreement(args.criterion)
        if args.json:
            _json(ag)
            return 0
        return out.emit(
            {**ag, "needs": _calibration_bar(graders)}, hints=[f"{cli} grade agreement"], title="Grader label"
        )
    if a == "agreement":
        rows = [graders.agreement(c) for c in ("quality", "process")]
        if args.json:
            _json(rows)
            return 0
        return out.emit(
            {"graders": rows, "needs": _calibration_bar(graders)},
            hints=[f"{cli} grade label --criterion quality --person <call> --judge-call <call>"],
            title="Model grader calibration",
        )
    scenarios = args.scenario or []
    if a == "run":
        if not (args.candidate and scenarios):
            return _usage(
                "`grade run` needs --candidate and --scenario",
                f"{cli} grade run --candidate {args.candidate or '<name>'} --scenario <id>",
            )
        graded = []
        for s in scenarios:
            for rd in replay.runs_for(args.candidate, s):
                g = graders.grade_run(rd, s, judge=judge)
                graded.append(
                    {
                        "run": str(rd),
                        **{
                            k: (v or {}).get("score") if isinstance(v, dict) else v
                            for k, v in g.items()
                            if k != "non_functional"
                        },
                    }
                )
        if args.json:
            _json(graded)
            return 0
        doc = {"candidate": args.candidate, "scenarios": scenarios, "graded": len(graded), "runs": graded}
        if not graded:  # AXI section 5: nothing to grade is said outright, with how to make runs
            return out.emit(
                doc,
                hints=[f"{cli} replay run --candidate {args.candidate} --scenario {scenarios[0]} --budget-usd 2"],
                title="Grade",
            )
        hint = f"{cli} grade compare --candidate {args.candidate} --against baseline" + "".join(
            f" --scenario {s}" for s in scenarios
        )
        return out.emit(doc, hints=[hint], title="Grade")
    if a in ("compare", "noise"):
        if not (args.candidate and args.against and scenarios):
            return _usage(
                f"`grade {a}` needs --candidate B --against A and --scenario ...",
                f"{cli} grade {a} --candidate <B> --against <A> --scenario <id>",
            )
        if a == "noise":
            r = graders.noise_check(args.against, args.candidate, scenarios)
            if args.json:
                _json(r)
            else:
                # ok: no criterion beats its own rerun; otherwise the criteria that did, spuriously.
                out.emit({"ok": r["ok"], "spurious": r["spurious"]}, title="Noise check")
            return 0 if r["ok"] else 1
        v = graders.compare(args.against, args.candidate, scenarios)
        if args.json:
            _json(v)
            return 0
        doc = {
            "b": v["b"],
            "a": v["a"],
            "scenarios": len(v["scenarios"]),
            "pareto": v["pareto"],
            "wins": v["wins"],
            "losses": v["losses"],
            "criteria": _verdict_rows(v),
        }
        scen = "".join(f" --scenario {s}" for s in scenarios)
        # A verdict over graded runs goes to a person next; with no graded runs there is nothing
        # to review yet, so the next step is grading.
        nxt = (
            f"{cli} review add --candidate {args.candidate} --against {args.against}{scen}"
            if v["scenarios"]
            else f"{cli} grade run --candidate {args.candidate}{scen}"
        )
        return out.emit(doc, hints=[nxt], title=f"Verdict · {v['b']} vs {v['a']}")
    return _usage(f"unknown action {a!r}", f"{cli} grade --help")


def _calibration_bar(graders) -> str:
    """When a model grader's verdicts count (graders.agreement's `calibrated`)."""
    return f"{graders.CALIBRATION_MIN}+ labels at {graders.CALIBRATION_BAR:.0%}+ agreement with a person"


def review_main(args) -> int:
    """`review <action>` -- the human final check-off (task 06)."""
    from core.metaharness import graders, review

    a, cli = args.action, _cli()
    decide_hint = "--reviewer <you> --decision accept|reject|more_runs --reason <why>"
    if a == "list":
        rows = review.pending()
        if args.json:
            _json(rows)
            return 0
        table = [
            {
                "id": r["id"],
                "candidate": r["candidate"],
                "against": r["against"],
                "verdict": r["verdict"].get("pareto"),
                "needs": r["reviewers_needed"],  # reviewers still to accept (2 for high-risk files)
                "expires": r["expires"],
            }
            for r in rows
        ]
        if not table:  # AXI section 5: an empty queue is said outright
            return out.emit({"pending": 0, "items": []}, hints=[f"{cli} review watch"], title="Review queue")
        return out.emit(
            {"pending": len(table), "items": table},
            hints=[f"{cli} review show {table[0]['id']}", f"{cli} review decide {table[0]['id']} {decide_hint}"],
            title="Review queue",
        )
    if a == "watch":
        rows = review.watch()
        if args.json:
            _json(rows)
            return 0
        table = [{"id": r["id"], "status": r["status"], "worse": "; ".join(r["worse"]) or None} for r in rows]
        return out.emit(
            {"watching": len(table), "items": table},
            hints=[] if table else [f"{cli} review list"],
            title="Applied changes under watch",
        )
    if a == "disagreements":
        rows = review.disagreements()
        if args.json:
            _json(rows)
            return 0
        table = [{k: r.get(k) for k in ("item", "criterion", "person", "grader", "reviewer")} for r in rows]
        return out.emit({"total": len(table), "disagreements": table}, title="Person/grader disagreements")
    if a == "add":
        if not (args.candidate and args.against and args.scenario):
            return _usage(
                "`review add` needs --candidate, --against and --scenario ...",
                f"{cli} review add --candidate {args.candidate or '<B>'} --against {args.against or 'baseline'} "
                "--scenario <id>",
            )
        try:
            v = graders.compare(args.against, args.candidate, args.scenario)
            it = review.enqueue(args.candidate, v, predicted=args.predicted)
        except KeyError as e:
            return out.fail(_missing(e), code="NOT_FOUND", hints=[f"{cli} replay candidates"])
        page = review.render(it["id"])
        if args.json:
            _json(it)
            return 0
        return out.emit(
            {"id": it["id"], "verdict": v["pareto"], "needs": it["reviewers_needed"], "page": str(page)},
            hints=[f"{cli} review decide {it['id']} {decide_hint}"],
            title="Queued for review",
        )
    if not args.id:
        return _usage(f"`review {a}` needs an item id", f"{cli} review {a} <id>", f"{cli} review list")
    try:
        if a == "show":
            page = review.render(args.id)
            it = review.item(args.id)
            if args.json:
                _json(it)
                return 0
            v = it.get("verdict") or {}
            doc = {
                "id": it["id"],
                "candidate": it["candidate"],
                "against": it.get("against"),
                "status": it["status"],
                "verdict": v.get("pareto"),
                "wins": v.get("wins") or [],
                "losses": v.get("losses") or [],
                "files": len(it.get("files") or []),
                "high_risk": bool(it.get("high_risk")),
                "needs": it.get("reviewers_needed"),
                "decisions": len(it.get("decisions") or []),
                "expires": it.get("expires"),
                "page": str(page),  # verdict table, config diff and the run diffs side by side
            }
            hints = [f"{cli} review decide {args.id} {decide_hint}"] if it["status"] == "pending" else []
            return out.emit(doc, hints=hints, title=f"Review · {args.id}")
        if a == "decide":
            calls = dict(kv.split("=", 1) for kv in args.calls.replace(",", " ").split() if "=" in kv)
            it = review.decide(args.id, args.reviewer, args.decision, calls, args.reason)
            if args.json:
                _json(it)
                return 0
            hint = f"{cli} review apply {args.id}" if it["status"] == "accepted" else f"{cli} review list"
            return out.emit(
                {
                    "id": args.id,
                    "status": it["status"],
                    "decisions": len(it["decisions"]),
                    "needs": it["reviewers_needed"],
                },
                hints=[hint],
                title="Review decision",
            )
        if a == "apply":
            it = review.apply(args.id)
            if args.json:
                _json(it)
                return 0
            return out.emit(
                {"id": args.id, "status": it["status"], "files": len(it["manifest"]), "watch_until": it["watch_until"]},
                hints=[f"{cli} review watch", f"{cli} review rollback {args.id} --reason <why>"],
                title="Applied",
            )
        if a == "rollback":
            it = review.rollback(args.id, reason=args.reason or "operator rollback")
            if args.json:
                _json(it)
                return 0
            return out.emit({"id": args.id, "status": it["status"]}, title="Rolled back")
    except KeyError as e:
        return out.fail(_missing(e), code="NOT_FOUND", hints=[f"{cli} review list"])
    except PermissionError as e:  # apply without a recorded accept
        return out.fail(str(e), code="REFUSED", hints=[f"{cli} review show {args.id}"])
    except ValueError as e:
        return out.fail(str(e), code="INVALID", hints=[f"{cli} review show {args.id}"])
    return _usage(f"unknown action {a!r}", f"{cli} review --help")


def loop_main(args) -> int:
    """`loop <action>` -- the candidate archive and the proposer loop (task 07)."""
    from core.metaharness import archive, loop, proposer

    a, cli = args.action, _cli()
    # The loop spends real money, so every suggested `loop run` names its daily cap.
    run_hint = f"{cli} loop run --candidate {args.candidate or 'baseline'} --daily-usd 5"
    if a == "status":
        rows = archive.index()
        rep = archive._read_json(proposer._rep_path(), {})
        st = {"candidates": len(rows), "front": archive.front(), "spent_today": loop.spent_today(), "proposers": rep}
        if args.json:
            _json(st)
            return 0
        doc: dict[str, Any] = {
            "candidates": st["candidates"],
            "front": st["front"],  # the Pareto front: candidates no other one beats on every axis
            "spent_today_usd": round(st["spent_today"], 4),
            "proposers": [
                {"proposer": p, "hits": r.get("hits", 0), "checked": r.get("checked", 0)} for p, r in rep.items()
            ],
        }
        hints = [f"{cli} loop archive", run_hint] if rows else [f"{cli} replay new --candidate <name>", run_hint]
        return out.emit(doc, hints=hints, title="Proposer loop")
    if a == "archive":
        rows = archive.index()
        if args.json:
            _json(rows)
            return 0
        table = [
            {
                "name": r["name"],
                "parent": r["parent"] or None,
                "pass_rate": r["scores"].get("pass_rate"),
                "tokens": r["scores"].get("tokens"),
                "hypothesis": out.truncate(r["hypothesis"], 50)[0] or None,
            }
            for r in rows
        ]
        if not table:  # AXI section 5: an empty archive is said outright
            return out.emit({"total": 0, "candidates": []}, hints=[run_hint], title="Candidate archive")
        return out.emit(
            {"total": len(table), "candidates": table},
            hints=[f"{cli} loop lineage --candidate {table[-1]['name']}"],
            title="Candidate archive",
        )
    if a == "lineage":
        if not args.candidate:
            return _usage("`loop lineage` needs --candidate NAME", f"{cli} loop lineage --candidate <name>")
        try:
            chain = archive.lineage(args.candidate)
        except KeyError as e:
            return out.fail(_missing(e), code="NOT_FOUND", hints=[f"{cli} loop archive"])
        if args.json:
            _json(chain)
            return 0
        # Newest first, back to the root: the order the archive's parent links walk.
        return out.emit({"candidate": args.candidate, "depth": len(chain), "lineage": chain}, title="Lineage")
    if a == "run":
        if args.daily_usd is None:
            return _usage(
                "`loop run` needs --daily-usd: the loop spends real money and has no default budget", run_hint
            )
        logs = loop.run(
            args.candidate or "baseline",
            iterations=args.iterations,
            daily_usd=args.daily_usd,
            proposals=args.proposals,
            trials=args.trials,
            mode=args.mode,
            proposer_card={"model": args.proposer_model} if args.proposer_model else None,
        )
        if args.json:
            _json(logs)
            return 0
        doc = {
            "iterations": len(logs),
            "spent_today_usd": round(loop.spent_today(), 4),
            "logs": [out.truncate(json.dumps(x, default=str), 400)[0] for x in logs],
        }
        return out.emit(doc, hints=[f"{cli} loop status", f"{cli} review list"], title="Proposer loop run")
    return _usage(f"unknown action {a!r}", f"{cli} loop --help")


def memreplay_main(args) -> int:
    """`memreplay <action>` -- replay the memory system before and after a lesson (task 08)."""
    from core.metaharness import memreplay

    a, cli = args.action, _cli()
    if a == "snapshot":
        p = memreplay.capture(label=args.label or "manual", exclude=tuple(args.exclude or ()))
        if args.json:
            _json({"snapshot": str(p)})
            return 0
        try:
            meta = json.loads(p.read_text(encoding="utf-8")).get("meta") or {}
        except (OSError, ValueError):
            meta = {}
        doc = {"snapshot": str(p), "lessons": meta.get("lessons"), "excluded": meta.get("excluded") or []}
        return out.emit(doc, title="Memory snapshot")  # a confirmation answers itself
    if a == "queue":
        rows = memreplay.queued()
        if args.json:
            _json(rows)
            return 0
        # Each lesson once, with its first queued record: the true "before" a replay compares.
        table = [{"lesson": r["lesson"], "why": r["why"], "at": r["at"]} for r in rows]
        if not table:  # AXI section 5: an empty queue is said outright
            return out.emit(
                {"queued": 0, "lessons": [], "fills": "when a lesson is recorded, edited, graduated or benched"},
                title="Memory replay queue",
            )
        # Draining replays every queued lesson with real runs, so the hint carries a spend cap.
        return out.emit(
            {"queued": len(table), "lessons": table},
            hints=[
                f"{cli} memreplay run --lesson {table[0]['lesson']} --base baseline --daily-usd 5",
                f"{cli} memreplay drain --base baseline --daily-usd 5",
            ],
            title="Memory replay queue",
        )
    if a == "run":
        if not (args.lesson and args.base):
            return _usage(
                "`memreplay run` needs --lesson and --base (the candidate whose harness the arms share)",
                f"{cli} memreplay run --lesson {args.lesson or '<name>'} --base {args.base or 'baseline'} --daily-usd 5",
            )
        res = memreplay.experiment(
            args.lesson, args.base, scenarios=args.scenario or None, trials=args.trials, daily_usd=args.daily_usd
        )
        if args.json:
            _json(res)
            return 0 if "error" not in res else 1
        if "error" in res:
            return out.fail(str(res["error"]), code="REPLAY_FAILED", hints=[f"{cli} memreplay queue"])
        eff = res.get("proven_effect") or res
        return out.emit({"lesson": args.lesson, "base": args.base, **eff}, title=f"Memory replay · {args.lesson}")
    if a == "drain":
        if args.daily_usd is None or not args.base:
            return _usage(
                "`memreplay drain` needs --base and --daily-usd",
                f"{cli} memreplay drain --base {args.base or 'baseline'} --daily-usd 5",
            )
        res = memreplay.drain(args.base, daily_usd=args.daily_usd, trials=args.trials)
        if args.json:
            _json(res)
            return 0
        table = [
            {"lesson": o.get("lesson"), "verdict": (o.get("proven_effect") or {}).get("verdict", o.get("error"))}
            for o in res
        ]
        return out.emit(
            {"replayed": len(table), "lessons": table}, hints=[f"{cli} memreplay queue"], title="Memory replay drain"
        )
    return _usage(f"unknown action {a!r}", f"{cli} memreplay --help")


def precompile_main(args) -> int:
    """`precompile <action>` -- lessons into harness primitives (task 09)."""
    from pathlib import Path

    from core.learning.learning_store import get_learning_store_instance
    from core.metaharness import precompile

    a, cli = args.action, _cli()
    if a == "check":
        root = Path(args.root) if args.root else precompile.ROOT
        drift = precompile.check_drift(root)
        if args.json:
            _json(drift)
            return 1 if drift else 0
        # Drift is a finding, not a failure of the command: the problems are the output, and
        # the exit code (1) is what a hook or CI step reads.
        out.emit({"root": str(root), "drift": len(drift), "problems": drift}, title="Precompiled drift")
        return 1 if drift else 0
    ls = get_learning_store_instance()
    lessons = ls.load_all_learnings_from_store()
    if args.lesson:
        lessons = [x for x in lessons if x.get("experiment_name") in set(args.lesson)]
    if a == "plan":
        rows = precompile.plan(lessons, store=ls.store)
        if args.json:
            _json(rows)
            return 0
        table = []
        for r in rows:
            g = r["gates"]
            # The gates a lesson still fails, by name: what has to change before it compiles.
            held = [k for k in ("proven", "stable", "premise") if not g[k]]
            table.append(
                {
                    "lesson": r["lesson"],
                    "kind": r["kind"],
                    "status": "pass" if g["pass"] else "held",
                    "failing_gates": ", ".join(held) or None,
                    "harnesses": ", ".join(r["harnesses"]),
                }
            )
        passing = sum(1 for r in rows if r["gates"]["pass"])
        if not table:  # AXI section 5: no lessons is said outright
            return out.emit({"total": 0, "passing": 0, "lessons": []}, title="Precompile plan")
        hint = f"{cli} precompile build" if passing else f"{cli} precompile build --force"
        return out.emit(
            {"total": len(table), "passing": passing, "lessons": table}, hints=[hint], title="Precompile plan"
        )
    if a == "build":
        res = precompile.build(
            lessons,
            base=args.base,
            harnesses=tuple(args.harness or precompile.HARNESSES),
            store=ls.store,
            force=args.force,
        )
        if args.json:
            _json(res)
            return 0 if res.get("built") else 1
        if not res.get("built"):
            return out.fail(
                str(res.get("why") or "nothing was built"),
                code="NOTHING_TO_BUILD",
                hints=[f"{cli} precompile plan", f"{cli} precompile build --force"],
            )
        doc = {
            "candidate": res["candidate"],
            "lessons": res["lessons"],
            "kinds": res["kinds"],
            "files": len(res["files"]),
            "harnesses": res["harnesses"],
        }
        return out.emit(
            doc,
            hints=[f"{cli} review add --candidate {res['candidate']} --against {args.base} --scenario <id>"],
            title="Precompiled candidate",
        )
    return _usage(f"unknown action {a!r}", f"{cli} precompile --help")


def modes_main(args) -> int:
    """`modes <action>` -- interpretive vs precompiled memory (task 10)."""
    from core.learning.learning_store import get_learning_store_instance
    from core.metaharness import modes

    a = args.action
    if a == "show":
        out = {"mode": modes.mode(), "harness": modes._harness_now() or "unknown"}
        _print(out, args.json, f"memory mode: {out['mode']} (AKASHIC_MEMORY_MODE); active harness: {out['harness']}")
        return 0
    if a == "compare":
        if not (args.base and args.compiled and args.scenario):
            print("ERROR: `modes compare` needs --base, --compiled and --scenario ...")
            return 2
        rep = modes.compare(args.base, args.compiled, args.scenario, trials=args.trials, daily_usd=args.daily_usd)
        lines = [f"{rep['harness']} / {rep['model'] or 'default model'}: default mode -> {rep['default_mode']}"]
        lines += [
            f"  {arm:<13} pass={s.get('pass_rate')} tokens={s.get('tokens')} cost={s.get('cost_usd')}"
            for arm, s in rep["scores"].items()
        ]
        _print(rep, args.json, "\n".join(lines))
        return 0
    if a == "placement":
        ls = get_learning_store_instance()
        rows = modes.placement(ls.load_all_learnings_from_store(), store=ls.store)
        _print(
            rows, args.json, "\n".join(f"  {r['lesson']:<40} {r['move']:<10} {r['why']}" for r in rows) or "no lessons"
        )
        return 0
    if a == "stale":
        rows = modes.recompile_queue()
        _print(
            rows,
            args.json,
            "\n".join(f"  {r['lesson']}: {r['why']} at {r['at']}" for r in rows) or "no compiled lesson has changed",
        )
        return 0
    print(f"ERROR: unknown action {a!r}")
    return 2


def compress_main(args) -> int:
    """`compress <action>` -- harness compression (task 11)."""
    from pathlib import Path

    from core.metaharness import compress, replay

    a = args.action
    if a == "pieces":
        root = Path(args.root) if args.root else compress.ROOT_DEFAULT
        rows = compress.pieces(root)
        _print(rows, args.json, "\n".join(f"  {p['id']:<56} group={p['group']}" for p in rows) or "no pieces found")
        return 0
    if a == "telemetry":
        if not (args.candidate and args.scenario):
            print("ERROR: `compress telemetry` needs --candidate and --scenario ...")
            return 2
        root = Path(args.root) if args.root else compress.ROOT_DEFAULT
        items = compress.pieces(root)
        runs = [rd for s in args.scenario for rd in replay.runs_for(args.candidate, s)]
        uses = compress.telemetry(runs, items)
        _print(
            uses,
            args.json,
            "\n".join(f"  {k:<56} {v}" for k, v in sorted(uses.items(), key=lambda kv: kv[1]))
            + f"\n({len(runs)} runs read)",
        )
        return 0
    if a == "run":
        if not (args.candidate and args.scenario and args.max_runs):
            print("ERROR: `compress run` needs --candidate, --scenario ... and --max-runs (real runs cost money)")
            return 2
        res = compress.run_compression(
            args.candidate, args.scenario, repo=compress.ROOT_DEFAULT, max_runs=args.max_runs, trials=args.trials
        )
        _print(res, args.json, json.dumps(res, indent=1))
        return 0 if res.get("built") else 1
    print(f"ERROR: unknown action {a!r}")
    return 2
