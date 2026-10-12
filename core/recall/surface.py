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

    if getattr(args, "forge_check", None):
        # Forge F1 (design sec.9): adjudicate ONE bounded edit against the lesson's own
        # durable history. Human-gated apply (trust ladder, decision 5) -- the operator
        # sees the verdict before --apply does anything, and apply is reversible.
        exp = args.forge_check
        if not getattr(args, "draft", None):
            print("ERROR: --forge-check needs --draft FILE (the proposed recommendation text).")
            print(f"Example: {_cli()} recall-curate --forge-check {exp} --draft new_text.md")
            return 2
        try:
            with open(args.draft, encoding="utf-8") as fh:
                draft = fh.read().strip()
        except Exception as e:
            print(f"ERROR reading draft file: {type(e).__name__}: {e}")
            return 2
        from core.recall.forge import apply_edit, gate_edit

        rep = gate_edit(exp, draft)
        if getattr(args, "json", False):
            print(_json.dumps(rep, indent=2, default=str))
        else:
            print(f"[forge-check] {exp}: {rep['verdict']}")
            for k, chk in rep.get("checks", {}).items():
                print(f"  floor {k}: {'ok' if chk.get('ok') else 'FAIL'}  {chk}")
            a1, a2 = rep.get("axis1", {}), rep.get("axis2", {})
            print(
                f"  axis1 must-still-match: {a1.get('kept', 0)}/{a1.get('credited_contexts', 0)} kept"
                + (" (vacuous - never-credited lesson)" if a1.get("vacuous") else "")
                + (f", LOST {len(a1.get('lost', []))}" if a1.get("lost") else "")
            )
            print(
                f"  axis2 noise hits: incumbent {a2.get('incumbent_hits')} -> variant {a2.get('variant_hits')}"
                f" over {a2.get('noise_contexts')} context(s)"
                + (" [improved]" if a2.get("improved") else " [regressed]" if a2.get("regressed") else "")
            )
            for r in rep.get("reasons", []):
                print(f"  - {r}")
        if rep["verdict"] == "PASS" and getattr(args, "apply", False):
            ok = apply_edit(exp, draft, rep)
            if ok:
                print("[forge-apply] APPLIED (provisional -- the curator's Tier-1 watch reads the stamp).")
                print(
                    f'  rollback any time: py -c "from core.learning.learning_store import '
                    f"get_learning_store; print(get_learning_store().rollback_forge_edit('{exp}'))\""
                )
            else:
                print("[forge-apply] FAILED -- record not updated (store down or record missing).")
        elif rep["verdict"] == "PASS":
            print(
                f"  (gate PASS -- apply with: {_cli()} recall-curate --forge-check {exp} --draft {args.draft} --apply)"
            )
        elif rep["verdict"] == "UNMEASURABLE" and getattr(args, "apply", False):
            print(
                "  (the gate ABSTAINS -- it will not apply what it cannot adjudicate. The unaided "
                f"human path is an ordinary re-record: {_cli()} learn <you> --experiment "
                f"{exp} ... which bypasses the Forge and is visible in history.)"
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
            print("[forge-propose] no eligible targets (rehab class empty, or all provisional/pending)")
            return 0
        for r in rows:
            print(
                f"[forge-propose] {r['experiment']} (surfaced {r.get('surfaced')}x): "
                f"{r.get('verdict', '-')} -> {r['outcome']}"
            )
            if r.get("rationale"):
                print(f"    optimizer rationale: {r['rationale']}")
            for reason in r.get("reasons", []):
                print(f"    - {reason}")
        print(f"  review queue: {_cli()} recall-curate --forge-proposals")
        return 0
    if getattr(args, "forge_proposals", False):
        from core.recall.forge_optimizer import pending_proposals

        props = pending_proposals()
        if getattr(args, "json", False):
            print(_json.dumps(props, indent=2, default=str))
            return 0
        if not props:
            print("[forge-proposals] none pending")
            return 0
        for p in props:
            print(f"[forge-proposals] {p['experiment']}  verdict={p['verdict']}  by={p['by']}  at={p['at']}")
            if p["verdict"] == "UNMEASURABLE":
                print(
                    "    !! gate ABSTAINED (no current-regime evidence) -- applying is pure human "
                    "judgment and does NOT count toward trust-ladder alignment"
                )
            if p.get("rationale"):
                print(f"    rationale: {p['rationale']}")
            print(f"    draft: {p['draft'][:220]}")
            print(
                f"    apply: write draft to a file, then {_cli()} recall-curate "
                f"--forge-check {p['experiment']} --draft FILE --apply"
            )
        return 0
    if getattr(args, "forge_audit", False):
        # Forge F0 (design doc sec.9): data-sufficiency audit vs the PRE-REGISTERED
        # criteria. Read-only -- composes with curation because the curator's economics
        # name the Forge's candidates.
        from core.recall.replay import audit

        rep = audit()
        if getattr(args, "json", False):
            print(_json.dumps(rep, indent=2, default=str))
            return 0

        def _pct(x):
            return "n/a" if x is None else f"{100.0 * x:.0f}%"

        print(
            f"[forge-audit] flips {rep['flips']} | targets replayable "
            f"{_pct(rep['flip_targets_replayable_share'])} | credited lessons {rep['credited_lessons']} "
            f"(>=2 ctx: {rep['credited_context_histogram']['>=2']}) | rehab candidates "
            f"{rep['rehab_candidates']} (coverage {_pct(rep['rehab_coverage_share'])}) | "
            f"ledger retention {rep['ledger_retention_days'] and round(rep['ledger_retention_days'], 1)}d"
        )
        f = rep["fidelity"]
        print(f"  fidelity: {f['agreed']}/{f['checked']} ledgered sources re-surface on replay ({_pct(f['rate'])})")
        for m in f.get("mismatches", []):
            print(f"    mismatch: {m['source']}  @  {m['target']}")
        for k, v in rep["verdicts"].items():
            print(f"  {k}: {v}")
        return 0
    from core.recall.curator import apply_curation, curation_report

    rep = curation_report()
    if getattr(args, "json", False):
        print(
            _json.dumps(
                rep if not args.apply else {"report": rep, "applied": apply_curation(rep)}, indent=2, default=str
            )
        )
        return 0
    print(
        f"[recall-curate] corpus {rep['corpus']} | on-surface {rep['surface_active']} | "
        f"bench-candidates {len(rep['bench'])} | unbench {len(rep['unbench'])} | "
        f"ghost counters to prune {rep['ghost_prune_count']} "
        f"(+{len(rep['credited_ghosts'])} credited ghosts kept for adjudication)"
    )
    for row in rep["bench"][:20]:
        print(f"  bench: {row['name']}  (surfaced {row['surfaced']}x, 0 credit, {row['age_days']}d old)")
    for row in rep["unbench"]:
        print(f"  UNBENCH (earned credit): {row['name']}")
    for row in rep.get("forge_rollback", []):
        print(f"  FORGE ROLLBACK: {row['name']}  ({row['why']})")
    for row in rep.get("forge_confirm", []):
        print(
            f"  forge confirm: {row['name']}  ({row['fresh_impressions']} fresh impressions, "
            f"{row['age_days']}d provisional, no regression)"
        )
    for row in rep.get("forge_expire", []):
        print(f"  forge proposal expired unreviewed: {row['name']}")
    if not args.apply:
        if (
            rep["bench"]
            or rep["unbench"]
            or rep["ghost_prune_count"]
            or rep.get("forge_rollback")
            or rep.get("forge_confirm")
            or rep.get("forge_expire")
        ):
            print(f"  (report only -- apply with: {_cli()} recall-curate --apply)")
        return 0
    out = apply_curation(rep)
    print(
        f"[recall-curate] APPLIED: benched {len(out['benched'])}, unbenched {len(out['unbenched'])}, "
        f"ghost counters pruned {out['ghosts_pruned']}"
    )
    return 0


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
    v = rep["verdicts"]
    print("# recall-prevention -- observation only, never a grade")
    print(
        f"  stage rows {rep['stage_rows']} -> {rep['observations']} observation(s) "
        f"over {len(rep['per_lesson'])} lesson(s)"
    )
    print(
        f"  PREVENTION candidates {rep['prevention_candidates']}  |  CONTROL arm "
        f"{rep['control_arm']}  |  rescue flips {rep['rescue_flips']}"
    )
    print(
        f"  verdicts: VIOLATED {v['VIOLATED']} · UNKNOWABLE {v['UNKNOWABLE']} "
        f"· COMPLIED {v['COMPLIED']} (unmintable without the Eye)"
    )
    print(
        f"  settled {rep['settled']} -> coverage {rep['coverage']:.4f}  "
        f"(unattributed repeats: {len(rep.get('unattributed_repeats') or [])})"
    )
    c = rep["contrast"]
    if c["success_rate_when_surfaced"] is not None and c["success_rate_when_not_surfaced"] is not None:
        d = c["success_rate_when_surfaced"] - c["success_rate_when_not_surfaced"]
        print(
            f"  success surfaced {c['success_rate_when_surfaced']:.4f} vs control "
            f"{c['success_rate_when_not_surfaced']:.4f}  (raw delta {d:+.4f} -- NOT an effect size)"
        )
    viol = {k: x for k, x in rep["per_lesson"].items() if x["VIOLATED"]}
    if viol:
        print("  fired-then-violated (1:1 with a filed repeat):")
        for k, x in sorted(viol.items(), key=lambda i: -i[1]["VIOLATED"]):
            print(f"    {x['VIOLATED']}x {k.replace('learn:experiment:', '')}")
    for line in rep["confounds"]:
        print(f"  ! {line}")
    return 0
