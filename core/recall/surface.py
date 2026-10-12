"""The recall cluster's CLI surface -- W169 slice 1 of the agent_cli extraction.

WHY THESE THREE AND NOT THE WHOLE CLUSTER: measured 2026-08-15, these are the only recall
verbs that reference nothing from agent_cli's module scope. The other five (learn, recall,
list, note, notes) reach for _clip/_intake/_MAX/_MAX_NOTE/_collapsed_learn_fields/
project_notes -- the shared intake helpers are the real seam, and migrating a helper is a
different slice with a different blast radius. Move what is free; leave what is coupled.

THE BINDING CONTRACT (why no verb can drop): agent_cli imports these at TOP level, so
build_parser's existing `set_defaults(fn=cmd_...)` resolves to the same objects it always
bound. tests/test_w169_recall_surface_extraction.py pins that by IDENTITY, not presence.

IMPORT DISCIPLINE: agent_cli keeps heavy imports function-local on purpose (7 top-level vs
284 function-local -- startup cost is the door's first impression). This module inherits
that law: top level costs os+json only; everything heavy stays inside the verb that needs it.
"""

import json
import os
from pathlib import Path


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


def _cli() -> str:
    """The CLI as a printed command names it: `aurora` under the installed launcher, else
    `<_pyl()> agent_cli.py` (core.paths.cli_command)."""
    import os as _os

    return "aurora" if (_os.getenv("AURORA_LAUNCHER") or "").strip() else f"{_pyl()} agent_cli.py"


# agent_cli derived the scripts/ dir from its OWN location, which worked because it sits at
# repo root. This file sits two levels down, so the root is named explicitly -- same target,
# honest derivation. (parents[2]: surface.py -> recall -> core -> REPO)
_REPO_ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------- recall-at
#: What recall-at was asked about, as its flags name it.
_TARGETS = ("command", "path", "gesture", "subject")
#: The provenance words recall-at prints, defined in band (the hook's render() keeps its own legend).
_LEGEND = {
    "worked": "the author's own report",
    "unverified": "never confirmed",
    "advice": "a suggestion, not an observation",
    "anti-pattern": "known-bad",
    "probation": "benched, being re-tested",
    "helped": "automatic credit",
    "useful": "votes",
}


def cmd_recall_at(args):
    """Recall-at-action: given a file path and/or command, surface the FEW highest-signal active
    lessons + a lock/peer warning with source pointers. Deterministic, FAITH-gated, fail-soft.
    The same engine the PreToolUse hook calls to inject additionalContext at the moment of action."""
    from core.recall.at_action import recall_at

    res = recall_at(
        path=args.path,
        command=args.command,
        subject=getattr(args, "subject", None),
        gesture=getattr(args, "gesture", None),
        domain=getattr(args, "domain", None),
        agent_id=args.agent_id or os.getenv("AKASHIC_AGENT_ID"),
        limit=args.limit or 3,
    )
    if args.json:
        print(json.dumps(res, default=str))
        return 0
    # The PreToolUse hook does not come through here: it calls recall_at() and render() itself
    # (agent/harness/actions.py recall_block), with anti-repeat and impression counting this verb
    # does not do. render() stays the hook's surface; this is the verb's.
    from core.axi import out
    from core.recall.at_action import _STALE_CUE_DAYS, _provenance_tag

    tool = (getattr(args, "hint_style", "cli") or "cli") == "tool"
    cli = _cli()
    doc: dict = {}
    for key in _TARGETS:
        if getattr(args, key, None):
            doc[key] = getattr(args, key)
    if res.get("error"):
        # A failed recall is not an empty one: say the check did not run. Exit 0 as before --
        # recall is fail-soft, and a caller deciding whether to act reads this, not the code.
        out.fail(
            f"recall unavailable: retrieval failed ({res['error']}); this is NOT 'no relevant lessons' -- "
            "treat the action as unadvised",
            code="RECALL_UNAVAILABLE",
            details=doc,
            hints=[f"{cli} status"],
        )
        return 0
    lessons, locks, verbs = res.get("lessons") or [], res.get("locks") or [], res.get("verbs") or []
    total = int(res.get("total") or 0)
    if not (lessons or locks or verbs):
        # Callers that relay this text test for "nothing relevant" near the top (core/comm/toolbox.py).
        return out.emit(
            {"result": "nothing relevant (silence beats a weak hint)", **doc, "total": 0},
            hints=[f'{cli} recall "<keyword>"'] if not tool else ['knowledge_recall(query="<keyword>")'],
            human=_human_recall_at,
            title="Recall at action",
        )
    doc["total"] = total
    if total > len(lessons):
        doc["shown"] = len(lessons)
    rows = []
    for it in lessons:
        # The provenance tag minus its author: the author gets its own column.
        words = _provenance_tag(it)[1:-1].split()
        author = str(it.get("agent_id") or "").strip()
        if author and author in words:
            words.remove(author)
        rows.append(
            {
                "status": " ".join(words),
                "by": author or None,
                "lesson": out.truncate(it.get("text"), 800)[0],
                "source": it.get("source"),
            }
        )
    if rows:
        doc["lessons"] = rows
    if locks:
        doc["locked_by"] = [lk.get("held_by") for lk in locks]
    counter = res.get("counter") or {}
    if counter.get("text"):
        if counter.get("source") in {r["source"] for r in rows}:
            doc["disputed_by"] = counter.get("source")  # the counter is already listed above
        else:
            doc["counter"] = {"lesson": out.truncate(counter["text"], 800)[0], "source": counter.get("source")}
    if verbs:
        doc["verbs"] = [{"verb": v.get("verb"), "purpose": v.get("purpose", "")} for v in verbs]
    try:  # the staleness cue: an old lesson may name files and flags that have since moved
        import time

        from core.foundation.timeutil import to_epoch

        ages = [(time.time() - to_epoch(it.get("timestamp"))) / 86400.0 for it in lessons if it.get("timestamp")]
        if _STALE_CUE_DAYS > 0 and ages and max(ages) >= _STALE_CUE_DAYS:
            doc["oldest_days"] = int(max(ages))
    except Exception:
        pass
    # Define the provenance words in band, but only the ones on screen, and only when one could be
    # taken for more than it is: "worked" alone is plain enough, "advice" or "unverified" is not.
    on_screen = {w for r in rows for w in str(r["status"]).split()}
    if on_screen - {"worked", "partial"}:
        doc["legend"] = "; ".join(f"{w}={_LEGEND[w]}" for w in _LEGEND if w in on_screen)
    hints = []
    if rows:
        top = rows[0]["source"]
        hints.append(f'knowledge_full(source="{top}")' if tool else f"{cli} recall --full {top}")
    if total > len(lessons):
        if tool:
            hints.append(f"recall_at(limit={total})")
        else:
            import shlex

            target = "".join(f" --{k} {shlex.quote(str(v))}" for k, v in doc.items() if k in _TARGETS)
            hints.append(f"{cli} recall-at{target} --limit {total}")
    elif rows and not tool:
        hints.append(f"{cli} recall-feedback --source {rows[0]['source']} --useful")
    if locks and not tool:
        hints.append(f"{cli} locks")
    return out.emit(doc, hints=hints, human=_human_recall_at, title="Recall at action")


def _human_recall_at(console, doc):
    """Human view of `recall-at`: locks first in red (the most actionable fact), then each lesson
    with its status in colour and the source under it, then any verb the door already has."""
    from core.axi import out

    target = doc.get("command") or doc.get("path") or doc.get("gesture") or doc.get("subject") or ""
    if target:
        console.print(f"[dim]for[/] {out._esc(str(target))}")
    if not doc.get("total") and not doc.get("locked_by") and not doc.get("verbs"):
        console.print("[yellow]Nothing relevant[/] [dim](silence beats a weak hint)[/]")
        return
    for who in doc.get("locked_by", []):
        console.print(f"[bold red]locked[/] by {out._esc(str(who))} -- coordinate before editing")
    if doc.get("lessons"):
        shown = f"{doc['shown']} of " if doc.get("shown") else ""
        console.print(f"[dim]{shown}{doc['total']} relevant lesson{'s' if doc['total'] != 1 else ''}[/]")
    for row in doc.get("lessons", []):
        st = row["status"]
        colour = "red" if "anti-pattern" in st else "green" if st.startswith("worked") else "yellow"
        by = f" [dim]by {out._esc(str(row['by']))}[/]" if row.get("by") else ""
        console.print()
        console.print(f"[{colour}]{out._esc(st)}[/]{by}")
        console.print(f"  {out._esc(row['lesson'])}")
        console.print(f"  [dim]{out._esc(str(row['source']))}[/]")
    if doc.get("counter"):
        console.print()
        console.print(f"[yellow]counter:[/] {out._esc(doc['counter']['lesson'])}")
        console.print(f"  [dim]{out._esc(str(doc['counter']['source']))}[/]")
    if doc.get("disputed_by"):
        console.print(f"[yellow]the top lesson is disputed by {out._esc(doc['disputed_by'])}[/]")
    for v in doc.get("verbs", []):
        console.print(f"[cyan]verb[/] {out._esc(str(v['verb']))} [dim]-- {out._esc(str(v['purpose']))}[/]")
    if doc.get("oldest_days"):
        console.print(
            f"[yellow]oldest lesson is ~{doc['oldest_days']}d old -- check that what it names still exists[/]"
        )
    if doc.get("legend"):
        console.print(f"[dim]{out._esc(doc['legend'])}[/]")


# ------------------------------------------------------------------ recall-feedback
def cmd_recall_feedback(args):
    """Teach recall what's load-bearing: mark a surfaced lesson 'useful' (it changed what you did) or
    'noise' (off-target). Boosts/decays it in future recall ranking. Source = the lesson's pointer,
    e.g. learn:experiment:NAME."""
    from core.axi import out
    from core.recall.at_action import _load_use, _store, canonicalize_source, is_general, record_feedback

    kind = "noise" if args.noise else "useful"
    dom = getattr(args, "domain", None)
    ok = record_feedback(args.source, kind, domain=dom)
    if not ok:
        return out.fail(
            f"could not record the {kind} vote for {args.source} (the store refused or is down)",
            code="NOT_RECORDED",
            hints=[f"{_cli()} status"],
        )
    doc: dict = {"recorded": kind, "source": args.source}
    if dom and kind == "useful":
        doc["domain"] = dom
    # The lesson's counters after this vote: the aggregate a voter would otherwise look up.
    # Best-effort -- the vote is recorded either way.
    try:
        use = _load_use(_store(), canonicalize_source(args.source))
        doc["useful_votes"] = int(use.get("useful", 0) or 0)
        doc["noise_votes"] = int(use.get("noise", 0) or 0)
    except Exception:
        use = None
    # Promotion is EARNED and it is worth saying out loud the moment it happens -- a lesson that has
    # now proved itself in two domains starts surfacing in both, and that is a change in behaviour
    # the operator should hear about rather than discover.
    if kind == "useful" and is_general(args.source, use=use):
        doc["domain_general"] = "yes -- credited in 2+ domains, it now surfaces everywhere"
    return out.emit(doc, title="Recall feedback")  # a confirmation answers itself: no hints


def cmd_recall_curate(args):
    """The funnel's triage made an actor (recall vNext loop 1): BENCH lessons that surfaced 10+
    times without ever earning credit (reversible flag; auto-UNBENCH on any new credit) and prune
    zero-credit ghost counters. Report by default; --apply stamps it."""
    import json as _json

    from core.axi import out

    cli = _cli()
    if getattr(args, "forge_check", None):
        # Forge F1 (design sec.9): adjudicate ONE bounded edit against the lesson's own
        # durable history. Human-gated apply (trust ladder, decision 5) -- the operator
        # sees the verdict before --apply does anything, and apply is reversible.
        exp = args.forge_check
        if not getattr(args, "draft", None):
            return out.fail(
                "--forge-check needs --draft FILE (the proposed recommendation text)",
                code="USAGE",
                hints=[f"{cli} recall-curate --forge-check {exp} --draft new_text.md"],
                exit_code=out.EXIT_USAGE,
            )
        try:
            with open(args.draft, encoding="utf-8") as fh:
                draft = fh.read().strip()
        except Exception as e:
            return out.fail(
                f"cannot read the draft file: {type(e).__name__}: {e}", code="USAGE", exit_code=out.EXIT_USAGE
            )
        from core.recall.forge import apply_edit, gate_edit

        rep = gate_edit(exp, draft)
        if getattr(args, "json", False):
            print(_json.dumps(rep, indent=2, default=str))
        else:
            a1, a2 = rep.get("axis1", {}), rep.get("axis2", {})
            doc: dict = {"experiment": exp, "verdict": rep["verdict"]}
            doc["floors"] = [
                {
                    "floor": k,
                    "ok": bool(chk.get("ok")),
                    "detail": out.truncate(", ".join(f"{dk}={dv}" for dk, dv in chk.items() if dk != "ok"), 200)[0]
                    or None,
                }
                for k, chk in rep.get("checks", {}).items()
            ]
            doc["must_still_match"] = {
                "kept": a1.get("kept", 0),
                "credited_contexts": a1.get("credited_contexts", 0),
                "lost": len(a1.get("lost") or []),
                **({"vacuous": "never-credited lesson"} if a1.get("vacuous") else {}),
            }
            doc["noise_hits"] = {
                "incumbent": a2.get("incumbent_hits"),
                "variant": a2.get("variant_hits"),
                "contexts": a2.get("noise_contexts"),
                "trend": "improved" if a2.get("improved") else "regressed" if a2.get("regressed") else "flat",
            }
            if rep.get("reasons"):
                doc["reasons"] = list(rep["reasons"])
            hints: list[str] = []
            if rep["verdict"] == "PASS" and not getattr(args, "apply", False):
                hints = [f"{cli} recall-curate --forge-check {exp} --draft {args.draft} --apply"]
            elif rep["verdict"] == "UNMEASURABLE" and getattr(args, "apply", False):
                # The gate ABSTAINS: it will not apply what it cannot adjudicate. The unaided human
                # path is an ordinary re-record, which bypasses the Forge and shows in history.
                doc["apply"] = "refused -- the gate abstains on what it cannot measure"
                hints = [f"{cli} learn <agent_id> --experiment {exp} --tried ... --recommend ..."]
            if not (rep["verdict"] == "PASS" and getattr(args, "apply", False)):
                out.emit(doc, hints=hints, title=f"Forge check · {exp}")
        if rep["verdict"] == "PASS" and getattr(args, "apply", False):
            ok = apply_edit(exp, draft, rep)
            rollback = (
                f'py -c "from core.learning.learning_store import '
                f"get_learning_store; print(get_learning_store().rollback_forge_edit('{exp}'))\""
            )
            if getattr(args, "json", False):  # the lines --json always printed after the report
                if ok:
                    print("[forge-apply] APPLIED (provisional -- the curator's Tier-1 watch reads the stamp).")
                    print(f"  rollback any time: {rollback}")
                else:
                    print("[forge-apply] FAILED -- record not updated (store down or record missing).")
            elif ok:
                doc["apply"] = "applied (provisional -- the curator's Tier-1 watch reads the stamp)"
                doc["rollback"] = rollback
                out.emit(doc, title=f"Forge check · {exp}")
            else:
                # Exit status stays what it always was (0 on a PASS verdict); the error says it all.
                out.fail(
                    f"apply failed for {exp}: record not updated (store down or record missing)",
                    code="APPLY_FAILED",
                    details={"verdict": rep["verdict"]},
                )
        return 0 if rep["verdict"] == "PASS" else 1
    if getattr(args, "forge_propose", False):
        # Forge F2: one optimizer pass -- deepseek proposes (blinded payload), the Tier-0
        # gate adjudicates, PASS/UNMEASURABLE queue for the HUMAN (trust ladder). The
        # model call is bridged HERE (root layer); core stays network-free.
        def _deepseek_propose(prompt):
            import sys as _sys

            _sys.path.insert(0, str(_REPO_ROOT / "scripts"))
            from ask_deepseek import DEFAULT_MODEL, load_key
            from deepseek_chat import make_client

            if not load_key():
                raise RuntimeError("no DeepSeek API key (scripts/ask_deepseek.load_key)")
            client = make_client(load_key())
            # v4-pro is a REASONING model: its thinking spends from the same max_tokens
            # budget as the answer, and a tight cap yields finish_reason=length with EMPTY
            # content (live-diagnosed 2026-07-09). Give thinking + answer real room.
            resp = client.chat.completions.create(
                model=DEFAULT_MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content or ""

        from core.recall.forge_optimizer import run_pass

        rows = run_pass(_deepseek_propose, limit=int(getattr(args, "limit", None) or 2))
        if getattr(args, "json", False):
            print(_json.dumps(rows, indent=2, default=str))
            return 0
        if not rows:
            return out.emit(
                {"proposed": 0, "result": "no eligible targets (rehab class empty, or all provisional or pending)"},
                hints=[f"{cli} recall-curate"],
                title="Forge propose",
            )
        props = []
        for r in rows:
            p = {
                "experiment": r["experiment"],
                "surfaced": r.get("surfaced"),
                "verdict": r.get("verdict") or None,
                "outcome": r["outcome"],
            }
            if r.get("rationale"):
                p["rationale"] = out.truncate(r["rationale"], 300)[0]
            if r.get("reasons"):
                p["reasons"] = list(r["reasons"])
            props.append(p)
        return out.emit(
            {"proposed": len(props), "proposals": props},
            hints=[f"{cli} recall-curate --forge-proposals"],
            title="Forge propose",
        )
    if getattr(args, "forge_proposals", False):
        from core.recall.forge_optimizer import pending_proposals

        props = pending_proposals()
        if getattr(args, "json", False):
            print(_json.dumps(props, indent=2, default=str))
            return 0
        if not props:
            return out.emit({"pending": 0}, hints=[f"{cli} recall-curate --forge-propose"], title="Forge proposals")
        rows = []
        for p in props:
            row = {
                "experiment": p["experiment"],
                "verdict": p["verdict"],
                "by": p["by"],
                "at": p["at"],
                "draft": out.truncate(p["draft"], 220)[0],
            }
            if p["verdict"] == "UNMEASURABLE":
                # Applying an abstained proposal is pure human judgment and does NOT count toward
                # trust-ladder alignment -- the reader has to see that before applying.
                row["warning"] = "the gate abstained (no current-regime evidence): applying is pure human judgment"
            if p.get("rationale"):
                row["rationale"] = out.truncate(p["rationale"], 300)[0]
            rows.append(row)
        first = rows[0]["experiment"]
        return out.emit(
            {"pending": len(rows), "proposals": rows},
            hints=[f"{cli} recall-curate --forge-check {first} --draft <file holding the draft> --apply"],
            title="Forge proposals",
        )
    if getattr(args, "forge_audit", False):
        # Forge F0 (design doc sec.9): data-sufficiency audit vs the PRE-REGISTERED
        # criteria. Read-only -- composes with curation because the curator's economics
        # name the Forge's candidates.
        from core.recall.replay import audit

        rep = audit()
        if getattr(args, "json", False):
            print(_json.dumps(rep, indent=2, default=str))
            return 0

        def _share(x):
            return None if x is None else round(float(x), 4)

        f = rep["fidelity"]
        ret = rep["ledger_retention_days"]
        doc = {
            "flips": rep["flips"],
            "flip_targets_replayable": _share(rep["flip_targets_replayable_share"]),
            "credited_lessons": rep["credited_lessons"],
            "credited_in_2_plus_contexts": rep["credited_context_histogram"][">=2"],
            "rehab_candidates": rep["rehab_candidates"],
            "rehab_coverage": _share(rep["rehab_coverage_share"]),
            "ledger_retention_days": round(ret, 1) if ret else None,
            "fidelity": {"agreed": f["agreed"], "checked": f["checked"], "rate": _share(f["rate"])},
            "verdicts": dict(rep["verdicts"]),
        }
        if f.get("mismatches"):
            doc["mismatches"] = [{"source": m["source"], "target": m["target"]} for m in f["mismatches"]]
        return out.emit(doc, title="Forge audit")  # a read-only audit answers itself: no hints
    from core.recall.curator import apply_curation, curation_report

    rep = curation_report()
    if getattr(args, "json", False):
        print(
            _json.dumps(
                rep if not args.apply else {"report": rep, "applied": apply_curation(rep)}, indent=2, default=str
            )
        )
        return 0
    doc = {
        "corpus": rep["corpus"],
        "on_surface": rep["surface_active"],
        "to_bench": len(rep["bench"]),
        "to_unbench": len(rep["unbench"]),
        "ghosts_to_prune": rep["ghost_prune_count"],
        "credited_ghosts_kept": len(rep["credited_ghosts"]),  # earned history: a human folds these
    }
    if rep["bench"]:
        doc["bench"] = [
            {"name": r["name"], "surfaced": r["surfaced"], "credit": 0, "age_days": r["age_days"]}
            for r in rep["bench"][:20]
        ]
        if len(rep["bench"]) > 20:
            doc["bench_shown"] = 20
    if rep["unbench"]:
        doc["unbench"] = [
            {"name": r["name"], "credit": r.get("credit"), "surfaced": r.get("surfaced")} for r in rep["unbench"]
        ]
    if rep.get("forge_rollback"):
        doc["forge_rollback"] = [{"name": r["name"], "why": r["why"]} for r in rep["forge_rollback"]]
    if rep.get("forge_confirm"):
        doc["forge_confirm"] = [
            {"name": r["name"], "fresh_impressions": r["fresh_impressions"], "age_days": r["age_days"]}
            for r in rep["forge_confirm"]
        ]
    if rep.get("forge_expire"):
        doc["forge_expire"] = [r["name"] for r in rep["forge_expire"]]
    pending = bool(
        rep["bench"]
        or rep["unbench"]
        or rep["ghost_prune_count"]
        or rep.get("forge_rollback")
        or rep.get("forge_confirm")
        or rep.get("forge_expire")
    )
    if not args.apply:
        if not pending:
            doc["result"] = "nothing to curate"
            return out.emit(doc, hints=[f"{cli} triage"], human=_human_curate, title="Recall curate")
        doc["mode"] = "report only"
        return out.emit(doc, hints=[f"{cli} recall-curate --apply"], human=_human_curate, title="Recall curate")
    done = apply_curation(rep)
    doc["applied"] = {
        "benched": len(done["benched"]),
        "unbenched": len(done["unbenched"]),
        "ghosts_pruned": done["ghosts_pruned"],
    }
    for key in ("forge_rolled_back", "forge_confirmed", "forge_proposals_expired"):
        if done.get(key):
            doc["applied"][key] = list(done[key])
    return out.emit(doc, human=_human_curate, title="Recall curate · applied")  # a confirmation: no hints


def _human_curate(console, doc):
    """Human view of `recall-curate`: the counts, then each list as a table."""
    from core.axi import out

    scalars = {k: v for k, v in doc.items() if not isinstance(v, (list, dict))}
    out.render_human(console, scalars)
    for key, label in (
        ("bench", "would bench (surfaced, never credited)"),
        ("unbench", "would unbench (earned credit)"),
        ("forge_rollback", "forge rollback"),
        ("forge_confirm", "forge confirm"),
    ):
        if doc.get(key):
            console.print(out.table(doc[key], title=label))
    if doc.get("forge_expire"):
        console.print(f"[yellow]forge proposals expired unreviewed:[/] {out._esc(', '.join(doc['forge_expire']))}")
    if doc.get("applied"):
        console.print("[bold green]applied[/]")
        out.render_human(console, doc["applied"], indent=1)


# ------------------------------------------------------------------ recall-prevention
def cmd_recall_prevention(args):
    """S2: what recall PREVENTED, read from the outcome stage log.

    The credited-flip counter only ever counted RESCUE (a FAIL->SUCCESS flip). Prevention --
    the failure that never happened -- was invisible to it by construction. This reads the
    stage log's contrastive record instead. OBSERVATION ONLY: it never writes credit, never
    benches, never retires; adjudication is operator-only (fence r2 H-C1).
    """
    import json as _json

    from core.recall import prevention

    rep = prevention.report()
    if getattr(args, "json", False):
        print(_json.dumps(rep, default=str, indent=2))
        return 0
    from core.axi import out

    v = rep["verdicts"]
    doc: dict = {
        "authority": "observation only -- never a grade; writes no credit and steers no ranking",
        "stage_rows": rep["stage_rows"],
    }
    doc.update(
        observations=rep["observations"],
        lessons=len(rep["per_lesson"]),
        prevention_candidates=rep["prevention_candidates"],
        control_arm=rep["control_arm"],
        rescue_flips=rep["rescue_flips"],
        # COMPLIED cannot be minted from this join (it needs the Eye), so it reads 0 by construction.
        verdicts={"VIOLATED": v["VIOLATED"], "UNKNOWABLE": v["UNKNOWABLE"], "COMPLIED": v["COMPLIED"]},
        settled=rep["settled"],
        coverage=rep["coverage"],
        unattributed_repeats=len(rep.get("unattributed_repeats") or []),
    )
    c = rep["contrast"]
    if c["success_rate_when_surfaced"] is not None and c["success_rate_when_not_surfaced"] is not None:
        doc["success_rate"] = {
            "surfaced": round(c["success_rate_when_surfaced"], 4),
            "control": round(c["success_rate_when_not_surfaced"], 4),
            "raw_delta": round(c["success_rate_when_surfaced"] - c["success_rate_when_not_surfaced"], 4),
            "note": "NOT an effect size -- read the confounds",
        }
    viol = {k: x for k, x in rep["per_lesson"].items() if x["VIOLATED"]}
    if viol:  # fired-then-violated, 1:1 with a filed repeat
        doc["violated"] = [
            {"lesson": k.replace("learn:experiment:", ""), "times": x["VIOLATED"]}
            for k, x in sorted(viol.items(), key=lambda i: -i[1]["VIOLATED"])
        ]
    if not rep["stage_rows"]:
        # AXI section 5: the zero, and why it can be zero. Only the harness hooks write the stage
        # log, when an action resolves; with nothing logged there is no number for a confound to
        # qualify, so the four of them would be pure cost.
        doc["result"] = "no action outcomes logged yet -- the harness hooks write the stage log"
        return out.emit(doc, hints=[f"{_cli()} hooks status"], human=_human_prevention, title="Recall prevention")
    doc["confounds"] = list(rep["confounds"])  # named beside every number, as the stage log asks
    return out.emit(
        doc, hints=[f"{_cli()} repeat --report", f"{_cli()} triage"], human=_human_prevention, title="Recall prevention"
    )


def _human_prevention(console, doc):
    """Human view of `recall-prevention`: the counts as an aligned list, violated lessons as a
    table, the confounds dimmed under a warning sign."""
    from core.axi import out

    console.print(f"[yellow]{out._esc(doc['authority'])}[/]")
    rest = {k: v for k, v in doc.items() if k not in ("authority", "violated", "confounds")}
    out.render_human(console, rest)
    if doc.get("violated"):
        console.print(out.table(doc["violated"], title="fired, then violated"))
    for line in doc.get("confounds", []):
        console.print(f"[yellow]![/] [dim]{out._esc(line)}[/]")
