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
