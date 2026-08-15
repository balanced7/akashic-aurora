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

# agent_cli derived the scripts/ dir from its OWN location, which worked because it sits at
# repo root. This file sits two levels down, so the root is named explicitly -- same target,
# honest derivation. (parents[2]: surface.py -> recall -> core -> REPO)
_REPO_ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------- recall-at
def cmd_recall_at(args):
    """Recall-at-action: given a file path and/or command, surface the FEW highest-signal active
    lessons + a lock/peer warning with source pointers. Deterministic, FAITH-gated, fail-soft.
    The same engine the PreToolUse hook calls to inject additionalContext at the moment of action."""
    from core.recall.at_action import recall_at, render
    res = recall_at(path=args.path, command=args.command,
                    subject=getattr(args, "subject", None),
                    gesture=getattr(args, "gesture", None),
                    domain=getattr(args, "domain", None),
                    agent_id=args.agent_id or os.getenv("AKASHIC_AGENT_ID"),
                    limit=args.limit or 3)
    if args.json:
        print(json.dumps(res, default=str)); return 0
    out = render(res, hint_style=getattr(args, "hint_style", "cli") or "cli")
    print(out if out else "# recall-at-action: nothing relevant (silence beats a weak hint)")
    return 0


# ------------------------------------------------------------------ recall-feedback
def cmd_recall_feedback(args):
    """Teach recall what's load-bearing: mark a surfaced lesson 'useful' (it changed what you did) or
    'noise' (off-target). Boosts/decays it in future recall ranking. Source = the lesson's pointer,
    e.g. learn:experiment:NAME."""
    from core.recall.at_action import record_feedback, is_general
    kind = "noise" if args.noise else "useful"
    dom = getattr(args, "domain", None)
    ok = record_feedback(args.source, kind, domain=dom)
    print(f"[recall-feedback] {'recorded' if ok else 'failed'}: {kind} <- {args.source}"
          + (f" (domain: {dom})" if dom and kind == "useful" else ""))
    # Promotion is EARNED and it is worth saying out loud the moment it happens -- a lesson that has
    # now proved itself in two domains starts surfacing in both, and that is a change in behaviour
    # the operator should hear about rather than discover.
    if ok and kind == "useful" and is_general(args.source):
        print("[recall-feedback] this lesson has now earned credit in 2+ domains -- "
              "it is DOMAIN-GENERAL and will surface everywhere.")
    return 0 if ok else 1


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
            print(f'Example: py agent_cli.py recall-curate --forge-check {exp} --draft new_text.md')
            return 2
        try:
            with open(args.draft, encoding="utf-8") as fh:
                draft = fh.read().strip()
        except Exception as e:
            print(f"ERROR reading draft file: {type(e).__name__}: {e}")
            return 2
        from core.recall.forge import gate_edit, apply_edit
        rep = gate_edit(exp, draft)
        if getattr(args, "json", False):
            print(_json.dumps(rep, indent=2, default=str))
        else:
            print(f"[forge-check] {exp}: {rep['verdict']}")
            for k, chk in rep.get("checks", {}).items():
                print(f"  floor {k}: {'ok' if chk.get('ok') else 'FAIL'}  {chk}")
            a1, a2 = rep.get("axis1", {}), rep.get("axis2", {})
            print(f"  axis1 must-still-match: {a1.get('kept', 0)}/{a1.get('credited_contexts', 0)} kept"
                  + (" (vacuous - never-credited lesson)" if a1.get("vacuous") else "")
                  + (f", LOST {len(a1.get('lost', []))}" if a1.get("lost") else ""))
            print(f"  axis2 noise hits: incumbent {a2.get('incumbent_hits')} -> variant {a2.get('variant_hits')}"
                  f" over {a2.get('noise_contexts')} context(s)"
                  + (" [improved]" if a2.get("improved") else " [regressed]" if a2.get("regressed") else ""))
            for r in rep.get("reasons", []):
                print(f"  - {r}")
        if rep["verdict"] == "PASS" and getattr(args, "apply", False):
            ok = apply_edit(exp, draft, rep)
            if ok:
                print("[forge-apply] APPLIED (provisional -- the curator's Tier-1 watch reads the stamp).")
                print(f"  rollback any time: py -c \"from core.learning.learning_store import "
                      f"get_learning_store; print(get_learning_store().rollback_forge_edit('{exp}'))\"")
            else:
                print("[forge-apply] FAILED -- record not updated (store down or record missing).")
        elif rep["verdict"] == "PASS":
            print(f"  (gate PASS -- apply with: py agent_cli.py recall-curate --forge-check {exp} "
                  f"--draft {args.draft} --apply)")
        elif rep["verdict"] == "UNMEASURABLE" and getattr(args, "apply", False):
            print("  (the gate ABSTAINS -- it will not apply what it cannot adjudicate. The unaided "
                  "human path is an ordinary re-record: py agent_cli.py learn <you> --experiment "
                  f"{exp} ... which bypasses the Forge and is visible in history.)")
        return 0 if rep["verdict"] == "PASS" else 1
    if getattr(args, "forge_propose", False):
        # Forge F2: one optimizer pass -- deepseek proposes (blinded payload), the Tier-0
        # gate adjudicates, PASS/UNMEASURABLE queue for the HUMAN (trust ladder). The
        # model call is bridged HERE (root layer); core stays network-free.
        def _deepseek_propose(prompt):
            import sys as _sys
            _sys.path.insert(0, str(_REPO_ROOT / "scripts"))
            from ask_deepseek import load_key, DEFAULT_MODEL
            from deepseek_chat import make_client
            if not load_key():
                raise RuntimeError("no DeepSeek API key (scripts/ask_deepseek.load_key)")
            client = make_client(load_key())
            # v4-pro is a REASONING model: its thinking spends from the same max_tokens
            # budget as the answer, and a tight cap yields finish_reason=length with EMPTY
            # content (live-diagnosed 2026-07-09). Give thinking + answer real room.
            resp = client.chat.completions.create(
                model=DEFAULT_MODEL, max_tokens=4000,
                messages=[{"role": "user", "content": prompt}])
            return resp.choices[0].message.content or ""
        from core.recall.forge_optimizer import run_pass
        rows = run_pass(_deepseek_propose, limit=int(getattr(args, "limit", None) or 2))
        if getattr(args, "json", False):
            print(_json.dumps(rows, indent=2, default=str))
            return 0
        if not rows:
            print("[forge-propose] no eligible targets (rehab class empty, or all "
                  "provisional/pending)")
            return 0
        for r in rows:
            print(f"[forge-propose] {r['experiment']} (surfaced {r.get('surfaced')}x): "
                  f"{r.get('verdict', '-')} -> {r['outcome']}")
            if r.get("rationale"):
                print(f"    optimizer rationale: {r['rationale']}")
            for reason in r.get("reasons", []):
                print(f"    - {reason}")
        print("  review queue: py agent_cli.py recall-curate --forge-proposals")
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
                print("    !! gate ABSTAINED (no current-regime evidence) -- applying is pure human "
                      "judgment and does NOT count toward trust-ladder alignment")
            if p.get("rationale"):
                print(f"    rationale: {p['rationale']}")
            print(f"    draft: {p['draft'][:220]}")
            print(f"    apply: write draft to a file, then py agent_cli.py recall-curate "
                  f"--forge-check {p['experiment']} --draft FILE --apply")
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
        print(f"[forge-audit] flips {rep['flips']} | targets replayable "
              f"{_pct(rep['flip_targets_replayable_share'])} | credited lessons {rep['credited_lessons']} "
              f"(>=2 ctx: {rep['credited_context_histogram']['>=2']}) | rehab candidates "
              f"{rep['rehab_candidates']} (coverage {_pct(rep['rehab_coverage_share'])}) | "
              f"ledger retention {rep['ledger_retention_days'] and round(rep['ledger_retention_days'], 1)}d")
        f = rep["fidelity"]
        print(f"  fidelity: {f['agreed']}/{f['checked']} ledgered sources re-surface on replay "
              f"({_pct(f['rate'])})")
        for m in f.get("mismatches", []):
            print(f"    mismatch: {m['source']}  @  {m['target']}")
        for k, v in rep["verdicts"].items():
            print(f"  {k}: {v}")
        return 0
    from core.recall.curator import curation_report, apply_curation
    rep = curation_report()
    if getattr(args, "json", False):
        print(_json.dumps(rep if not args.apply else {"report": rep, "applied": apply_curation(rep)},
                          indent=2, default=str))
        return 0
    print(f"[recall-curate] corpus {rep['corpus']} | on-surface {rep['surface_active']} | "
          f"bench-candidates {len(rep['bench'])} | unbench {len(rep['unbench'])} | "
          f"ghost counters to prune {rep['ghost_prune_count']} "
          f"(+{len(rep['credited_ghosts'])} credited ghosts kept for adjudication)")
    for row in rep["bench"][:20]:
        print(f"  bench: {row['name']}  (surfaced {row['surfaced']}x, 0 credit, {row['age_days']}d old)")
    for row in rep["unbench"]:
        print(f"  UNBENCH (earned credit): {row['name']}")
    for row in rep.get("forge_rollback", []):
        print(f"  FORGE ROLLBACK: {row['name']}  ({row['why']})")
    for row in rep.get("forge_confirm", []):
        print(f"  forge confirm: {row['name']}  ({row['fresh_impressions']} fresh impressions, "
              f"{row['age_days']}d provisional, no regression)")
    for row in rep.get("forge_expire", []):
        print(f"  forge proposal expired unreviewed: {row['name']}")
    if not args.apply:
        if rep["bench"] or rep["unbench"] or rep["ghost_prune_count"] \
                or rep.get("forge_rollback") or rep.get("forge_confirm") or rep.get("forge_expire"):
            print("  (report only -- apply with: py agent_cli.py recall-curate --apply)")
        return 0
    out = apply_curation(rep)
    print(f"[recall-curate] APPLIED: benched {len(out['benched'])}, unbenched {len(out['unbenched'])}, "
          f"ghost counters pruned {out['ghosts_pruned']}")
    return 0
