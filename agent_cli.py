#!/usr/bin/env python3
"""
agent_cli.py -- THE single door an external agent (e.g. OpenCode) uses.

OpenCode is a separate process; it cannot import our Python. So it SHELLS OUT here.
Everything an agent needs is two commands:

    py agent_cli.py boot  <agent_id> [--task "..."] [--json]
        Print this agent's startup context: the ranked lessons + project state that
        matter for the task, distilled to a token budget. Read this FIRST.

    py agent_cli.py learn <agent_id> --experiment NAME --tried "..." --result "..."
                       [--expected "..."] [--recommend "..."] [--category C]
                       [--success yes|partial|no] [--confidence low|medium|high]
        Record a lesson back into shared memory so the next agent benefits.

Helpers:
    py agent_cli.py recall "<query>" [--json]   Search past lessons.
    py agent_cli.py status [--json]             Honest system status.

Design notes:
  * Front-loaded: the most useful output is in the FIRST lines (a 50-line reader
    still gets the gist).
  * Fail-soft: Redis down -> File fallback. Never crashes on a missing backend.
  * ASCII-only AUTHORED output; stdout/stderr are forced to UTF-8 (errors=replace) so
    STORED text from peers (em-dashes etc.) survives Windows pipes without mojibake.
  * Robust at the seam: partial / empty / None / huge inputs are sanitized, not fatal.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # make `core`/`agent` importable

# Harness pipes and CI read this output as UTF-8, but a Windows PIPE defaults to cp1252 --
# a peer agent's em-dash rendered as U+FFFD mojibake at every boot (2026-07-02 friction log).
# Authored output stays ASCII (module docstring); this keeps STORED text faithful in transit.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass   # non-reconfigurable stream (exotic wrapper/capture) -> old behavior, still safe

_MAX = 4000   # clamp absurdly long fields an agent might paste


def _clip(s, n=_MAX):
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")   # clip on a word boundary, not mid-word
    return (cut or s[:n]) + " ...[truncated]"


def _working_tree_status():
    """Best-effort git cleanliness for the repo this file lives in.

    Returns {ok, dirty, ahead, branch, summary}. ok=False means git is unavailable
    or this isn't a repo -- callers treat that as 'nothing to warn about'. The whole
    repo (E:\\AI-Setup) is the unit of mirroring, regardless of the agent's cwd.
    Never raises -- a guardrail must not break the door it guards.
    """
    import subprocess
    root = os.path.dirname(os.path.abspath(__file__))
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}   # never hang on a credential prompt

    def _git(*a):
        return subprocess.run(["git", *a], cwd=root, env=env, capture_output=True, text=True)

    try:
        st = _git("status", "--porcelain")
        if st.returncode != 0:
            return {"ok": False, "dirty": 0, "ahead": 0, "branch": "", "summary": ""}
        dirty = [ln for ln in st.stdout.splitlines() if ln.strip()]
        branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        ahead = 0
        rc = _git("rev-list", "--count", f"origin/{branch}..{branch}")
        if rc.returncode == 0 and rc.stdout.strip().isdigit():
            ahead = int(rc.stdout.strip())
        return {"ok": True, "dirty": len(dirty), "ahead": ahead, "branch": branch,
                "summary": ", ".join(d[3:] for d in dirty[:6])}
    except Exception:
        return {"ok": False, "dirty": 0, "ahead": 0, "branch": "", "summary": ""}


def _warn_unmirrored(soft=False):
    """Tell the agent if it has uncommitted/unpushed work -- a slice isn't done until
    it's mirrored. `soft` is a one-line heads-up (boot); otherwise it's the loud
    session-end nag (handoff). Returns True if it warned. Silent when git is
    unavailable or the tree is clean.
    """
    s = _working_tree_status()
    if not s.get("ok") or (s["dirty"] == 0 and s["ahead"] == 0):
        return False
    bits = []
    if s["dirty"]:
        bits.append(f"{s['dirty']} uncommitted file(s)")
    if s["ahead"]:
        bits.append(f"{s['ahead']} unpushed commit(s)")
    label = ", ".join(bits)
    if soft:
        print(f"\n[i] Heads-up: {label} not yet mirrored -- "
              'run `py scripts/mirror.py "msg"` when this slice is done.')
        return True
    print(f"\n[!] UNMIRRORED WORK: {label} -- a slice isn't done until it's mirrored.")
    if s.get("summary"):
        print(f"    changed: {s['summary']}" + (" ..." if s["dirty"] > 6 else ""))
    print('    Run:  py scripts/mirror.py "<msg>"  (commit+push),'
          ' then  py scripts/snapshot_knowledge.py snapshot')
    return True


# --------------------------------------------------------------------------- boot
def cmd_boot(args):
    from agent.initializer import derive_agent_context_from_startup_sources
    from agent.bifrost_pull import collect_boot_bifrost, print_boot_bifrost_section, print_boot_locks_section
    res = derive_agent_context_from_startup_sources(args.agent_id, args.task, verbose=False)
    bifrost = collect_boot_bifrost(args.agent_id, limit=8)
    ctx = res.get("context") or {}
    ctx["bifrost"] = bifrost
    # Auto-logger (Slice 2): record that this agent booted (raw, full-fidelity). Best-effort.
    try:
        from core.events.event_log import capture_event
        capture_event("boot", f"{args.agent_id} booted" + (f" -- task: {args.task}" if args.task else ""),
                      agent_id=args.agent_id,
                      detail={"task": args.task, "status": res.get("status"),
                              "approx_tokens": ctx.get("approx_tokens"),
                              "bifrost_pending": bifrost.get("pending", 0)})
    except Exception:
        pass
    # Pre-warm recall-at-action so the agent's FIRST edit this session gets instant recall (boot is
    # the universal session-start ritual -> covers the read-bootstrap flow). Prune stale state too.
    try:
        from core.recall.at_action import warm_cache, prune_state
        warm_cache(); prune_state()
    except Exception:
        pass
    # Cold-start safety net (ported from the retired StoreReconciler): if Redis was down during past
    # writes, the durable File is ahead -- backfill Redis so recall/state read consistent values. Best-
    # effort; only reconciles when drift is actually found (a no-op fast path when the backends are in sync).
    try:
        from core.foundation.store import create_store, HybridStore
        _st = create_store(prefer_redis=True)
        if isinstance(_st, HybridStore) and _st.redis_available:
            if _st.check_drift().get("missing_in_redis"):
                _rep = _st.reconcile()
                _n = sum((_rep.get("written") or {}).values())
                print(f"[boot] healed Redis divergence: backfilled {_n} key-structures from File "
                      f"(Redis was behind)", file=sys.stderr)
    except Exception:
        pass
    if args.json:
        print(json.dumps({"status": res.get("status"), "context": ctx, "bifrost": bifrost},
                         indent=2, default=str))
        return 0 if res.get("status") == "success" else 1

    sk = (ctx.get("skeleton") or "").strip()
    secs = ctx.get("sections") or {}
    print(f"# CONTEXT for {args.agent_id}" + (f" -- task: {args.task}" if args.task else ""))
    print(f"# {len(secs.get('learnings', []))} lesson(s), "
          f"{len(secs.get('blockers', []))} blocker(s), "
          f"~{ctx.get('approx_tokens', 0)}/{ctx.get('token_budget', 0)} tokens "
          f"(within budget: {ctx.get('within_budget')})")
    print("#" + "-" * 60)
    # Read-state-first (Slice C): the governed task ledger comes BEFORE lessons/notes/messages, so an
    # agent obeys what's DONE/NEXT rather than re-deriving intent from stale backlog. Fail-open.
    try:
        from core.coord.task_ledger import format_state
        print(format_state(agent=args.agent_id))
    except Exception:
        pass
    print("## LESSONS / CONTEXT (most relevant first)")
    print(sk if sk else "  (none yet -- you are the first agent to contribute)")
    try:   # ARCH SLICE (RENEW Strand E gap #2 / deferred step #3): orient the agent to the code
        # region of THIS task -- a stable projection over docs/ARCHITECTURE.md, show-nothing when the
        # task matches no subsystem. Both doors get it (MCP boot delegates to cmd_boot). Fail-open.
        from context.arch_loader import load_arch_slice
        arch = load_arch_slice(args.task or "")
        if arch:
            print("\n## ARCH SLICE (orientation for this task)")
            for a in arch:
                loc = f" -> {a['path']}" if a.get("path") else ""
                print(f"  {a['heading']}{loc}")
    except Exception:
        pass
    blockers = secs.get("blockers", [])
    if blockers:
        print("\n## ACTIVE BLOCKERS")
        for b in blockers[:5]:
            print(f"  [{b.get('severity', '?')}] {_clip(b.get('description', ''), 120)}")
    try:   # durable project notes (write-once) -- the resume ANCHOR (where-we-are / open-docket /
        # handoff). RENEW Strand E (2026-07-07): a flat 110-char clip made the boot payload
        # INSUFFICIENT to resume -- dense multi-item notes (open-docket) collapsed to one line,
        # forcing a second `notes --json` fetch to recover the actual state. Fidelity is now TIERED
        # by recency (freshest note ~full, older ones taper) so the resume anchor survives in the
        # payload itself; worst case ~640 tokens, well within the boot budget. Full bodies one hop
        # away via the pointer below. See research/reviewed/renew-strande-cold-resume-2026-07-07.md.
        from core.learning.agent_memory import get_agent_memory
        notes = get_agent_memory().get_decisions(days=60)
        if notes:
            print("\n## RECENT NOTES (durable project memory)")
            _budgets = [900, 500, 500, 220, 220, 220]   # by recency: resume-anchor first, then taper
            shown = notes[:len(_budgets)]
            for d, budget in zip(shown, _budgets):
                print(f"  [{d.created_at[:10]}] {d.title}: {_clip(d.decision, budget)}")
            if len(notes) > len(shown) or any(len(d.decision or "") > b for d, b in zip(shown, _budgets)):
                print("  (clipped; full note bodies: py agent_cli.py notes --json)")
    except Exception:
        pass
    try:   # T3: one-line funnel pulse -- watch the loop's trend without a separate command
        from core.recall.funnel import snapshot, summary_line
        print("\n## FUNNEL (recall value -- full: py agent_cli.py stats --days 7)")
        print("  " + summary_line(snapshot(hours=7 * 24)))
    except Exception:
        pass
    try:   # auto-captured last-session draft (SessionEnd/PreCompact) -- a trail if the last end was abrupt
        import time as _t
        dp = last_session_draft_path()
        if os.path.isfile(dp) and (_t.time() - os.path.getmtime(dp)) < 2 * 86400:
            print(f"\n## LAST-SESSION DRAFT (auto-captured) -> {dp}")
            print("   review it; promote with: py agent_cli.py wrap --commit")
    except Exception:
        pass
    print_boot_bifrost_section(bifrost)
    print_boot_locks_section(bifrost, args.agent_id)
    print("\n## TO CONTRIBUTE A LESSON, run:")
    print(f'  py agent_cli.py learn {args.agent_id} --experiment NAME '
          f'--tried "..." --result "..." --recommend "..."')
    print("\n## BIFROST (live + durable)")
    print("  py agent_cli.py bifrost-sync <agent>     # peek unread (same as boot section)")
    print("  py agent_cli.py promoted [--limit N]       # durable salient msgs (kind=bifrost_msg)")
    _warn_unmirrored(soft=True)   # heads-up if you're resuming on top of unmirrored work
    if not os.getenv("AKASHIC_AGENT_ID"):
        print("\n[i] AKASHIC_AGENT_ID not set -- peer-lock enforcement (C2/C4) is degraded: "
              "edits/commits to a peer-locked path fail CLOSED until it's set. Set it per agent "
              "(e.g. .claude/settings.json env).")
    return 0 if res.get("status") == "success" else 1


# -------------------------------------------------------------------------- learn
def cmd_learn(args):
    from core.learning.learning_store import get_learning_store
    if not args.experiment or not (args.tried or args.result):
        print("ERROR: need --experiment and at least one of --tried/--result.")
        print('Example: py agent_cli.py learn me --experiment cache_fix '
              '--tried "memoize" --result "+50%" --recommend "use it"')
        return 2
    signal = {
        "experiment_name": _clip(args.experiment, 200),
        "agent_id": _clip(args.agent_id, 200),
        "what_tried": _clip(args.tried),
        "actual_outcome": _clip(args.result),
        "expected_outcome": _clip(args.expected),
        "recommendation": _clip(args.recommend),
        "category": _clip(args.category, 80) or "uncategorized",
        "success": args.success or "yes",
        "confidence": args.confidence or "medium",
        "anti_pattern": _clip(getattr(args, "anti_pattern", ""), 200),
    }
    related = []
    try:   # near-duplicate scan BEFORE recording (advisory only -- writes are never blocked)
        from core.learning.learning_store import find_related
        ls = get_learning_store()
        if not ls._load_experiment(signal["experiment_name"]):   # a re-record IS the update path
            related = find_related(signal, ls.load_all_learnings_from_store(),
                                   exclude_name=signal["experiment_name"])
    except Exception:
        related = []
    try:
        ok = get_learning_store().record_learning(signal)
    except Exception as e:
        print(f"ERROR recording lesson: {type(e).__name__}: {e}")
        return 1
    if ok:
        # narrative spine (Slice 1): a recorded lesson is also a Beat, pointing back
        # to the learning. Best-effort -- a narrative hiccup must not fail `learn`.
        try:
            from core.narrative.beat_log import get_beat_log
            from core.narrative.track_router import RouteHint
            get_beat_log().emit(
                "learning",
                summary=signal.get("recommendation") or signal.get("actual_outcome") or signal["experiment_name"],
                source=f"learn:experiment:{signal['experiment_name']}",
                hint=RouteHint(category=signal.get("category", ""), task=signal.get("experiment_name", "")))
        except Exception:
            pass
        # Auto-logger (Slice 2): the lesson is also a RAW event -- the full experiment
        # payload as drill-down detail beneath the salient learning Beat. Best-effort.
        try:
            from core.events.event_log import capture_event
            capture_event("learning", f"lesson: {signal['experiment_name']}",
                          agent_id=signal.get("agent_id"),
                          refs=[f"learn:experiment:{signal['experiment_name']}"],
                          detail={"tried": signal.get("what_tried"), "result": signal.get("actual_outcome"),
                                  "category": signal.get("category"), "success": signal.get("success")})
        except Exception:
            pass
    if args.json:
        print(json.dumps({"recorded": bool(ok), "experiment": signal["experiment_name"]}))
    else:
        print(f"[{'OK' if ok else 'FAIL'}] recorded lesson '{signal['experiment_name']}' "
              f"(category: {signal['category']}, success: {signal['success']})")
    # Slice 2 capture nudge: a failure with no anti_pattern is where a reusable known-bad hides, and
    # this instant (just recorded, context fresh) is the moment to name it. Auto-draft a candidate NAME
    # (removing the naming cost) and hand back the exact one-line tag command. Silent for successes or
    # when an anti_pattern was already given -- high-signal, no nag.
    if ok and not args.json and str(signal["success"]).lower() in ("no", "false", "partial") \
            and not signal.get("anti_pattern"):
        from core.learning.learning_store import draft_anti_pattern_slug
        slug = draft_anti_pattern_slug(signal.get("what_tried", ""), "", signal.get("recommendation", ""))
        if slug:
            print("[hint] if this failure names a reusable known-bad, tag it so recall can warn others:")
            print(f"       py agent_cli.py tag-anti-pattern {args.agent_id} "
                  f"--experiment {signal['experiment_name']} --name {slug}   (edit the name if a better fits)")
    # Near-duplicate advisory (ce-compound's overlap rule, field-survey C5): 4-5 dims -> this is
    # probably the SAME lesson, update that one next time (same --experiment name = update);
    # 2-3 dims -> related, worth merging in a consolidation pass. Never blocks (append-only).
    if ok and not args.json and related:
        top = related[0]
        if top["dims"] >= 4:
            print(f"[i] near-duplicate: overlaps '{top['experiment_name']}' on {top['dims']}/5 dimensions"
                  f" ({', '.join(top['matched'])}).")
            print(f"    Next time update it instead: re-record with --experiment {top['experiment_name']}"
                  " (same name = update, no dupes).")
        else:
            print(f"[i] related lesson: '{top['experiment_name']}' ({top['dims']}/5 dims)"
                  " -- candidates for a future consolidation pass.")
    return 0 if ok else 1


def cmd_tag_anti_pattern(args):
    """Tag an EXISTING lesson as documenting a reusable known-bad, without clobbering its other fields
    (the safe follow-up the `learn` capture nudge points at). Grows the disconfirmers recall needs."""
    from core.learning.learning_store import get_learning_store
    ok = get_learning_store().tag_anti_pattern(args.experiment, args.name, reason=args.reason)
    if args.json:
        print(json.dumps({"tagged": bool(ok), "experiment": args.experiment, "anti_pattern": args.name}))
    elif ok:
        print(f"[OK] tagged '{args.experiment}' as anti-pattern '{args.name}' -- recall will now warn on it")
    else:
        print(f"[FAIL] no lesson '{args.experiment}' to tag (record it first with `learn`)")
    return 0 if ok else 1


# ------------------------------------------------------------------------- recall
def cmd_recall(args):
    """Search lessons by keyword; with no query, list ALL lessons. --full SOURCE pulls the whole
    faithful record behind one recalled lesson's source pointer (the one-hop escape from a capped
    recall-at surface to the raw evidence, e.g. learn:experiment:NAME)."""
    full = getattr(args, "full", None)
    if full:
        from core.recall.at_action import full_record
        rec = full_record(full)
        if args.json:
            print(json.dumps(rec, default=str)); return 0
        if not rec:
            print(f"# no record found for '{full}'"); return 1
        for k, v in rec.items():
            print(f"  {k}: {v}")
        return 0
    from core.learning.learning_store import get_learning_store
    ls = get_learning_store()
    query = (args.query or "").strip()
    try:
        hits = ls.load_all_learnings_from_store() if not query \
            else ls.search_learnings_by_keyword(_clip(query, 200))
    except Exception as e:
        print(f"ERROR searching: {type(e).__name__}: {e}")
        return 1
    if args.json:
        print(json.dumps(hits, indent=2, default=str))
        return 0
    label = "all lessons" if not query else f"lesson(s) matching '{query}'"
    print(f"# {len(hits)} {label}")
    for h in hits[:25]:
        rec = h.get("recommendation") or h.get("actual") or h.get("what_tried", "")
        # [graduated] = rule now enforced by automation (see `graduate`); kept for history,
        # excluded from recall surfacing -- the tag says WHY it never shows up at action time.
        flag = " [graduated]" if str(h.get("graduated") or "").strip() else ""
        print(f"  - [{h.get('category', '?')}] {h.get('experiment_name', '?')}{flag}: {_clip(rec, 160)}")
    return 0


# --------------------------------------------------------------------------- list
def cmd_list(args):
    """Alias for recall with no query -- show everything in memory."""
    args.query = ""
    return cmd_recall(args)


# ----------------------------------------------------------------------- recall-at
def cmd_recall_at(args):
    """Recall-at-action: given a file path and/or command, surface the FEW highest-signal active
    lessons + a lock/peer warning with source pointers. Deterministic, FAITH-gated, fail-soft.
    The same engine the PreToolUse hook calls to inject additionalContext at the moment of action."""
    from core.recall.at_action import recall_at, render
    res = recall_at(path=args.path, command=args.command,
                    agent_id=args.agent_id or os.getenv("AKASHIC_AGENT_ID"),
                    limit=args.limit or 3)
    if args.json:
        print(json.dumps(res, default=str)); return 0
    out = render(res)
    print(out if out else "# recall-at-action: nothing relevant (silence beats a weak hint)")
    return 0


# --------------------------------------------------------------------- triage
def cmd_triage(args):
    """Sharpening-loop S1: the value-rate triage report -- every tracked lesson ranked by
    measured value so a reviewer can adjudicate merge / graduate / retire. READ-ONLY:
    this verb changes nothing and its output must never be wired into automated pruning
    (F2 Goodhart guard). Actions live elsewhere: `graduate` retires enforced lessons,
    `recall-feedback --noise` downranks, S2 consolidation merges."""
    from core.recall.funnel import triage
    t = triage(min_surfaced=int(args.min_surfaced))
    if args.json:
        print(json.dumps(t, indent=1))
        return 0
    ghosts = t.get("ghosts", [])
    print(f"# TRIAGE (S1)  corpus={t['corpus_lessons']} tracked={t['tracked']} "
          f"(lessons={t.get('tracked_lessons', t['tracked'])}, ghosts={len(ghosts)}) "
          f"dormant={t['dormant_count']} | window push cost ~{t['window_injected_tokens_approx']} tokens")
    print(f"\n## PROTECT ({len(t['protect'])}) -- earned credit; the proven core")
    for r in t["protect"][:15]:
        print(f"  helped={r['helped']} useful={r['useful']} surfaced={r['surfaced']:<4} {r['source']}")
    print(f"\n## COST WITHOUT RETURN ({len(t['cost_no_return'])}) -- surfaced >= {t['min_surfaced']}, "
          f"zero credit; adjudicate: merge / graduate / retire / sharpen trigger")
    for r in t["cost_no_return"][:20]:
        print(f"  surfaced={r['surfaced']:<4} ~{r['window_tokens_approx']:<5} win-tok  {r['source']}")
    print(f"\n## NOISE-VOTED ({len(t['noise_voted'])})")
    for r in t["noise_voted"][:10]:
        print(f"  noise={r['noise']} surfaced={r['surfaced']:<4} {r['source']}")
    print(f"\n## WATCH: {t['watch_count']} lesson(s) surfaced but too early to judge "
          f"(< {t['min_surfaced']} impressions)")
    if ghosts:
        credited = [g for g in ghosts if g["useful"] or g["helped"] or g["noise"]]
        print(f"\n## GHOSTS ({len(ghosts)}) -- counters naming NO live lesson (retired/renamed); "
              f"bookkeeping debt, not knowledge")
        for g in ghosts[:10]:
            tag = "  <-- has credit: adjudicate (fold into successor)" if (
                g["useful"] or g["helped"] or g["noise"]) else ""
            print(f"  surfaced={g['surfaced']:<4} u={g['useful']} h={g['helped']} "
                  f"n={g['noise']}  {g['source']}{tag}")
        zero = len(ghosts) - len(credited)
        print(f"  -> {zero} zero-credit (safe auto-fold), {len(credited)} credited (needs a decision). "
              f"Apply: py agent_cli.py recall-counters --fold")
    print("\n(adjudication is human/frontier judgment -- this report never auto-prunes)")
    return 0


# --------------------------------------------------------------------- recall-counters
def cmd_recall_counters(args):
    """Counter hygiene (sharpening S2a). recall:use:* keys are mutable Store STATE, and two forms
    of debt accumulate: (1) BARE-SLUG counters from votes cast without the learn:experiment: prefix
    (they open a parallel counter that never joins the lesson's totals); (2) GHOSTS -- lesson-shaped
    counters whose lesson was retired or renamed. Report-only by default; --fold applies the fix:
    bare slugs merge into their canonical key, and ZERO-credit ghosts are deleted. A ghost that
    carries credit (useful/helped/noise) is earned history and is KEPT + reported for S2 to fold
    into the superseding lesson -- never auto-dropped (that would silently discard a real signal)."""
    from core.recall.at_action import merge_use_counters, prune_ghost_counters, canonicalize_source, _store, _USE_PREFIX
    from core.learning.learning_store import get_learning_store
    ls = get_learning_store()
    store = _store()
    names = {r.get("experiment_name") for r in ls.load_all_learnings_from_store()}
    # survey (read-only) -- what fold WOULD touch
    bare, ghosts_zero, ghosts_credited = [], [], []
    lesson_prefix = "learn:experiment:"
    try:
        for k in store.keys(_USE_PREFIX + "*"):
            src = k[len(_USE_PREFIX):]
            if ":" not in src:
                if canonicalize_source(src, learning_store=ls) != src:
                    bare.append(src)
            elif src.startswith(lesson_prefix) and names and src[len(lesson_prefix):] not in names:
                use = json.loads(store.get(k) or "{}")
                (ghosts_credited if any(int(use.get(f, 0)) for f in ("useful", "helped", "noise"))
                 else ghosts_zero).append(src)
    except Exception:
        pass
    if not args.fold:
        print(f"# COUNTER HYGIENE (S2a)  -- report only; apply with --fold")
        print(f"  bare-slug counters to merge : {len(bare)}   {bare[:6]}")
        print(f"  zero-credit ghosts to prune : {len(ghosts_zero)}   {ghosts_zero[:6]}")
        print(f"  credited ghosts (KEPT; S2 adjudicates): {len(ghosts_credited)}   {ghosts_credited[:6]}")
        if not (bare or ghosts_zero or ghosts_credited):
            print("  -> counters are clean.")
        return 0
    merged = merge_use_counters(store=store, learning_store=ls)
    res = prune_ghost_counters(store=store, learning_store=ls)
    try:   # counters feed the warm cache's ranking -- rebuild so the fix takes effect now
        from core.recall.at_action import warm_cache
        warm_cache()
    except Exception:
        pass
    from core.events.event_log import capture_event
    capture_event("recall_counters_fold",
                  f"folded {merged} bare-slug, pruned {len(res['pruned'])} ghost counter(s)",
                  agent_id=args.agent_id or os.getenv("AKASHIC_AGENT_ID"),
                  detail={"merged": merged, "pruned": res["pruned"], "kept_credited": res["kept_credited"]})
    print(f"[OK] folded {merged} bare-slug counter(s) into canonical keys.")
    print(f"[OK] pruned {len(res['pruned'])} zero-credit ghost(s): {res['pruned'][:8]}")
    if res["kept_credited"]:
        print(f"[!] KEPT {len(res['kept_credited'])} credited ghost(s) -- these carry earned signal and")
        print(f"    need an S2 decision (fold credit into the successor lesson): {res['kept_credited']}")
    return 0


# --------------------------------------------------------------------- fleet
def cmd_fleet(args):
    """Fleet dispatch: the local-model roster + a direct one-shot caller -- the structure for calling
    small models (docs/fleet-dispatch-design.md). Actions:
      list   -- the roster (status / capabilities / disqualifier); --probe adds live Ollama availability
      select -- pick the best model for a capability + constraints (what to RUN right now)
      call   -- run a bounded subtask on one model and print its output (also the manual smoke test)
    Reads are fail-soft; a failed call surfaces the error, never a silent empty string."""
    from core.fleet import roster
    action = args.action or "list"
    if action == "list":
        rows = roster.models(status=args.status, capability=args.capability)
        probe = roster.probe_availability() if args.probe else None
        present = set(probe["present"]) if probe and probe.get("ok") else None
        if args.json:
            out = {"models": rows}
            if probe is not None:
                out["availability"] = probe
            print(json.dumps(out, indent=1))
            return 0
        hdr = f"# FLEET ROSTER  ({len(rows)} model(s)"
        hdr += f", status={args.status}" if args.status else ""
        hdr += f", capability={args.capability}" if args.capability else ""
        print(hdr + ")")
        if args.probe:
            live = "ollama up" if (probe and probe.get("ok")) else "ollama unreachable"
            print(f"  live: {live}" + (f" -- present: {probe['declared_present']}"
                                       if probe and probe.get("ok") else ""))
        for m in rows:
            up = ""
            if present is not None:
                up = " [up]" if (m["tag"] in present or m["tag"].split(":")[0] in present) else " [--]"
            vram = f"{m['vram_gb']}GB" if m.get("vram_gb") is not None else "?GB"
            tps = f"{m['throughput_toks']}tps" if m.get("throughput_toks") is not None else "?tps"
            print(f"  {m['status']:<9} {m['tag']:<20}{up} {vram:<6} {tps:<7} ctx={m.get('context')}  "
                  f"[{', '.join(m.get('capabilities') or [])}]")
            if m.get("disqualifier"):
                print(f"            GATED: {m['disqualifier']}")
        return 0
    if action == "select":
        pick = roster.select(args.capability, status=(args.status or "active"),
                             max_vram=args.max_vram, min_context=args.min_context)
        if args.json:
            print(json.dumps(pick, indent=1) if pick else "null")
            return 0 if pick else 1
        if not pick:
            print(f"# FLEET SELECT -- nothing fits (capability={args.capability}, "
                  f"max_vram={args.max_vram}, min_context={args.min_context}, status={args.status or 'active'})")
            return 1
        vram = f"{pick['vram_gb']}GB" if pick.get("vram_gb") is not None else "?GB"
        print(f"# FLEET SELECT -> {pick['tag']}  ({pick['status']}, {vram}, ctx={pick.get('context')})")
        print(f"  why: capability={args.capability or 'any'} + constraints; {pick.get('notes', '')}")
        return 0
    if action == "call":
        if not args.model or not args.prompt:
            print("ERROR: fleet call needs --model TAG and --prompt TEXT")
            return 2
        from core.fleet.caller import call, FleetCallError
        try:
            out = call(args.model, args.prompt, system=args.system, max_tokens=args.max_tokens,
                       temperature=args.temperature, fmt=("json" if args.json_out else None))
        except FleetCallError as e:
            print(f"[FAIL] {e}")
            return 1
        print(out)
        return 0
    print(f"ERROR: unknown fleet action '{action}' (list | select | call)")
    return 2


# --------------------------------------------------------------------- harnesses
def cmd_harnesses(args):
    """The integration-tier matrix: what each harness ACTUALLY delivers, T0 door .. T6 close.
    Data = agent/harness/registry.py (the adapters' single source of truth; the prose story is
    docs/integration-tiers.md). An honest 'unavailable' beats a pretended capability -- plan
    around what your runtime does, not what you wish it did."""
    from agent.harness.registry import HARNESSES, TIERS, supported
    if args.json:
        print(json.dumps({"tiers": list(TIERS), "harnesses": HARNESSES}, indent=2))
        return 0
    print("# INTEGRATION TIERS  (T0 door .. T6 close; the story: docs/integration-tiers.md)")
    for name, spec in HARNESSES.items():
        auto = sum(1 for t in TIERS if supported(name, t))
        print(f"\n## {name}  (agent id: {spec.get('default_agent_id') or '<set AKASHIC_AGENT_ID>'}; "
              f"{auto}/{len(TIERS)} tiers automated)")
        print(f"   adapters: {spec.get('adapters')}")
        for t in TIERS:
            mark = "+" if supported(name, t) else "-"
            print(f"   {mark} {t}: {spec['tiers'][t]}")
    return 0


# --------------------------------------------------------------------- injections
def cmd_injections(args):
    """The injection ledger: everything recall PUSHED into agent contexts recently -- when,
    at which altitude (action/plan), for which target, which lessons, and what it cost.
    Injected context must never be hidden state; this is the inspection window."""
    from core.recall.at_action import recent_injections
    hours = float(args.hours or 24)
    inj = recent_injections(hours)
    if args.json:
        print(json.dumps({"window_hours": hours, "count": len(inj),
                          "tokens_approx": sum(int(i.get("chars", 0)) for i in inj) // 4,
                          "injections": inj}, indent=2))
        return 0
    print(f"# INJECTION LEDGER  (last {hours:g}h: {len(inj)} injection(s), "
          f"~{sum(int(i.get('chars', 0)) for i in inj) // 4} tokens pushed)")
    if not inj:
        print("  (none -- either quiet, or nothing cleared the relevance floor)")
        return 0
    import datetime as _dt
    for i in inj[-25:]:
        when = _dt.datetime.fromtimestamp(float(i.get("at", 0))).strftime("%m-%d %H:%M")
        tgt = _human_flip_target(i.get("t", "")) if i.get("t") else "(prompt)"
        print(f"  [{when}] {i.get('alt', 'action'):<6} {_clip(tgt, 60)}  "
              f"{len(i.get('s', []))} lesson(s), {i.get('chars', 0)} chars")
        for s in i.get("s", [])[:3]:
            print(f"           - {s}")
    return 0


# ----------------------------------------------------------------------- graduate
def cmd_graduate(args):
    """A lesson's rule became a FORCING FUNCTION (hook / guardrail / CI check)? Graduate it:
    it keeps its history and full-corpus visibility (`list` shows a [graduated] tag) but stops
    competing for recall surface slots -- the automation does the reminding now. Reversible
    with --undo. (Greptile's 'disable what a deterministic tool covers', on our spectrum:
    forcing-function > just-in-time prompt > documentation > memory.)"""
    from core.learning.learning_store import get_learning_store
    exp = (args.experiment or "").strip()
    enforced = (args.enforced_by or "").strip()
    if not exp or (not args.undo and not enforced):
        print("ERROR: need --experiment NAME and --enforced-by \"<the automation that enforces it>\""
              " (or --undo to reverse a graduation).")
        print('Example: py agent_cli.py graduate claude --experiment git_blanket_staging '
              '--enforced-by "git-guard PreToolUse hook (C0)"')
        return 2
    ls = get_learning_store()
    if not ls.mark_graduated(exp, enforced, undo=bool(args.undo)):
        print(f"ERROR: no lesson named '{exp}' -- check the name with `py agent_cli.py list`.")
        return 1
    try:   # recall must reflect graduation NOW, not at the next cache TTL expiry
        from core.recall.at_action import warm_cache
        warm_cache()
    except Exception:
        pass
    from core.events.event_log import capture_event
    capture_event("graduate",
                  (f"un-graduate: {exp}" if args.undo else f"graduate: {exp} -> enforced by {enforced}"),
                  agent_id=args.agent_id,
                  detail={"experiment": exp, "enforced_by": enforced, "undo": bool(args.undo)})
    if args.json:
        print(json.dumps({"experiment": exp, "graduated": not args.undo,
                          "enforced_by": enforced if not args.undo else ""}))
        return 0
    if args.undo:
        print(f"[OK] un-graduated '{exp}' -- it competes for recall surface slots again.")
    else:
        print(f"[OK] graduated '{exp}' -- enforced by: {enforced}")
        print("     It keeps history (`list` tags it [graduated]) but no longer takes recall slots.")
    return 0


# ------------------------------------------------------------------ recall-feedback
def cmd_recall_feedback(args):
    """Teach recall what's load-bearing: mark a surfaced lesson 'useful' (it changed what you did) or
    'noise' (off-target). Boosts/decays it in future recall ranking. Source = the lesson's pointer,
    e.g. learn:experiment:NAME."""
    from core.recall.at_action import record_feedback
    kind = "noise" if args.noise else "useful"
    ok = record_feedback(args.source, kind)
    print(f"[recall-feedback] {'recorded' if ok else 'failed'}: {kind} <- {args.source}")
    return 0 if ok else 1


# ------------------------------------------------------------------------ discover
def list_verbs(query=""):
    """Introspect the live argparse subparsers -> [(verb, purpose)]. ONE source of truth (the parser
    itself), so the door can never describe a verb that doesn't exist or omit one that does."""
    sa = next((a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction)), None)
    verbs = [(ca.dest, (ca.help or "").strip()) for ca in (sa._choices_actions if sa else [])]
    q = (query or "").strip().lower()
    if q:
        verbs = [(n, h) for n, h in verbs if q in n.lower() or q in h.lower()]
    return verbs


def cmd_discover(args):
    """The self-describing door: list every verb + its one-line purpose (the L1 skeleton). Optional
    QUERY filters by substring. Run `py agent_cli.py <verb> -h` for a verb's full arguments."""
    verbs = list_verbs(args.query)
    if args.json:
        print(json.dumps([{"verb": n, "purpose": h} for n, h in verbs], indent=2)); return 0
    q = (args.query or "").strip()
    print(f"# agent_cli.py - {len(verbs)} verb(s)" + (f" matching '{q}'" if q else "")
          + "   (run `py agent_cli.py <verb> -h` for arguments)")
    width = max((len(n) for n, _ in verbs), default=0)
    for n, h in verbs:
        print(f"  {n.ljust(width)}  {h}")
    return 0


# ----------------------------------------------------------------------------- note
def project_notes(memory=None, chronicle_dir=None):
    """Regenerate chronicles/memory.md from ACTIVE notes -- the file is a DERIVED projection (write-once:
    record one atom, the digest is generated, never hand-edited). Distilled via the shared, faithfulness-
    gated Consolidator. Returns the path. Best-effort caller wraps it."""
    from core.learning.agent_memory import get_agent_memory
    from core.primitives.consolidator import Consolidator
    mem = memory or get_agent_memory()
    decs = mem.get_decisions(days=3650)
    items = [Consolidator.item(text=f"{d.title}: {d.decision}", source=f"mem:decision:{d.id}",
                               importance=4, timestamp=d.created_at) for d in decs]
    dist = Consolidator().consolidate(items, instruction="durable project notes")
    base = Path(chronicle_dir) if chronicle_dir else \
        Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "chronicles"
    base.mkdir(parents=True, exist_ok=True)
    path = base / "memory.md"
    header = ("# Project memory (auto-generated from notes — do not hand-edit)\n\n"
              f"_Distilled from {len(items)} active note(s) · regenerate via `py agent_cli.py note` / `notes --project`_\n\n"
              "Record durable project state once with `note`; correct it by re-noting the same title.\n\n")
    body = dist.skeleton if dist.skeleton else "_(no notes yet)_"
    path.write_text(header + body + "\n", encoding="utf-8")
    return str(path)


def cmd_note(args):
    """Write-once durable project note: record WHERE-WE-ARE / a decision in ONE place (the substrate),
    not by hand-editing files. Re-noting the same --title (or --supersedes ID) RETIRES the prior note
    (correct by superseding, never edit). Surfaces at `boot` + `notes`; reprojects chronicles/memory.md."""
    from core.learning.agent_memory import get_agent_memory
    if not args.title or not args.note:
        print("ERROR: need --title and --note.")
        print('Example: py agent_cli.py note me --title "checkpoint: recall done" --note "next: write-once"')
        return 2
    mem = get_agent_memory()
    title = _clip(args.title, 200)
    supersedes = args.supersedes
    if not supersedes:   # re-noting the same title updates-in-place (write-once correction)
        try:
            for d in mem.get_decisions(days=3650):
                if d.title == title:
                    supersedes = d.id
                    break
        except Exception:
            pass
    dec_id = mem.decide(title=title, decision=_clip(args.note), context=_clip(args.context or "", 1000),
                        supersedes=supersedes or None, session_id=args.session or "")
    if not dec_id:
        print("ERROR recording note (store unavailable?)"); return 1
    try:   # narrative + firehose fanout (best-effort), mirroring cmd_learn
        from core.narrative.beat_log import get_beat_log
        from core.narrative.track_router import RouteHint
        get_beat_log().emit("decision", summary=f"{title}: {_clip(args.note, 160)}",
                            source=f"mem:decision:{dec_id}",
                            hint=RouteHint(category=args.category or "", task=title))
    except Exception:
        pass
    try:
        from core.events.event_log import capture_event
        capture_event("decision", f"note: {title}", agent_id=args.agent_id,
                      refs=[f"mem:decision:{dec_id}"], detail={"note": args.note, "context": args.context})
    except Exception:
        pass
    try:
        project_notes()   # keep the generated digest fresh
    except Exception:
        pass
    if args.json:
        print(json.dumps({"recorded": True, "id": dec_id, "title": title,
                          "superseded": supersedes or None})); return 0
    print(f"[OK] noted '{title}' (id {dec_id})" + (f" - superseded prior {supersedes}" if supersedes else ""))
    return 0


def cmd_notes(args):
    """List active (non-superseded) project notes, newest first. The write-once read side."""
    from core.learning.agent_memory import get_agent_memory
    if args.project:
        try:
            print(f"[OK] regenerated {project_notes()}"); return 0
        except Exception as e:
            print(f"ERROR projecting notes: {type(e).__name__}: {e}"); return 1
    decs = get_agent_memory().get_decisions(days=args.days or 3650)
    if args.json:
        print(json.dumps([{"id": d.id, "title": d.title, "note": d.decision, "at": d.created_at}
                          for d in decs], indent=2, default=str)); return 0
    print(f"# {len(decs)} active note(s)")
    for d in decs[:(args.limit or 25)]:
        print(f"  [{d.created_at[:10]}] {d.title}: {_clip(d.decision, 140)}   (id {d.id})")
    return 0


# ----------------------------------------------------------------------------- wrap
def _human_flip_target(target):
    """normalize_target keys (p:<abs path> / c:<command>) are JOIN keys, not prose -- the draft
    renders what a human recognizes: a repo-relative path or the command line itself."""
    s = str(target)
    if s.startswith("p:"):
        p = s[2:]
        try:
            rel = os.path.relpath(p, os.getenv("AI_SETUP", "E:\\AI-Setup"))
            if not rel.startswith(".."):
                p = rel.replace("\\", "/")
        except Exception:
            pass   # different drive / unparseable -> keep the absolute path
        return "file " + p
    if s.startswith("c:"):
        return "command: " + s[2:]
    return s


def build_session_draft(commits, lessons, notes, max_per=8, flips=None):
    """Distill a session's own activity into a DRAFT where-we-are -- PURE (testable). Each line keeps a
    lossless source pointer (git:<sha> / learn:experiment:<name> / mem:decision:<id>). `flips` are the
    session's FAIL->SUCCESS moments (core.recall.at_action.recent_flips) -- each is a lesson that was
    just EARNED, so the draft turns them into pre-filled candidate `learn` commands (friction audit D5:
    capture as a byproduct of the work, edit-a-draft instead of author-from-scratch)."""
    lines = []
    if commits:
        lines.append("Shipped:")
        for sha, subj in commits[:max_per]:
            lines.append(f"  - {subj}  (git:{sha})")
    if lessons:
        lines.append("Learned:")
        for l in lessons[:max_per]:
            rec = l.get("recommendation") or l.get("actual") or l.get("what_tried") or ""
            lines.append(f"  - {l.get('experiment_name')}: {_clip(rec, 120)}  (learn:experiment:{l.get('experiment_name')})")
    if notes:
        lines.append("Decided / noted:")
        for d in notes[:max_per]:
            lines.append(f"  - {d.title}: {_clip(d.decision, 120)}  (mem:decision:{d.id})")
    if flips:
        from core.recall.at_action import learn_command_for
        # A retry loop flips the same target repeatedly -- one candidate per target (keep the last,
        # its credited count reflects the final state), else the draft is a wall of duplicates.
        by_target = {}
        for fl in flips:
            by_target[str(fl.get("t", ""))] = fl
        lines.append("Candidate lessons (FAIL->SUCCESS flips this session -- record the transferable ones):")
        for t, fl in list(by_target.items())[:max_per]:
            lines.append(f"  - {_clip(_human_flip_target(t), 100)} (credited: {fl.get('credited', 0)})")
            lines.append(f"    {learn_command_for(t)}")
    return "\n".join(lines) if lines else "(no session activity captured)"


def _recent_commits(hours=12, limit=12):
    import subprocess
    try:
        r = subprocess.run(["git", "log", f"--since={hours} hours ago", "--pretty=%h\t%s"],
                           cwd=os.getenv("AI_SETUP", "E:\\AI-Setup"), capture_output=True, text=True, timeout=10)
        out = []
        for line in (r.stdout or "").splitlines()[:limit]:
            if "\t" in line:
                sha, subj = line.split("\t", 1)
                out.append((sha, subj))
        return out
    except Exception:
        return []


def _recent_lessons(limit=8):
    from core.learning.learning_store import get_learning_store
    try:
        recs = get_learning_store().load_all_learnings_from_store()
        recs.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return recs[:limit]
    except Exception:
        return []


def cmd_wrap(args):
    """Ambient session capture: distill this session's own commits + lessons + notes into a DRAFT
    where-we-are, so you APPROVE/correct instead of authoring blank. Preview by default; --commit
    records the draft as a note (supersede-by-title) so it surfaces at the next boot."""
    from datetime import datetime
    from core.learning.agent_memory import get_agent_memory
    commits = _recent_commits(args.hours or 12)
    lessons = _recent_lessons(8)
    notes = get_agent_memory().get_decisions(days=1)
    try:
        from core.recall.at_action import recent_flips
        flips = recent_flips(args.hours or 12)
    except Exception:
        flips = []
    draft = build_session_draft(commits, lessons, notes, flips=flips)
    if not args.commit:
        print("# DRAFT where-we-are (review it; record with: "
              'py agent_cli.py wrap --commit --title "where-we-are ...")\n')
        print(draft)
        print(f"\n# from {len(commits)} commit(s), {len(lessons)} lesson(s), {len(notes)} note(s) this session")
        return 0
    title = args.title or f"where-we-are {datetime.now().date().isoformat()}"
    mem = get_agent_memory()
    supersedes = next((d.id for d in mem.get_decisions(days=3650) if d.title == title), None)
    dec_id = mem.decide(title=title, decision=draft, supersedes=supersedes or None)
    if not dec_id:
        print("ERROR recording the wrapped note"); return 1
    try:
        project_notes()
    except Exception:
        pass
    print(f"[OK] wrapped this session -> note '{title}' (id {dec_id})"
          + (f" - superseded prior {supersedes}" if supersedes else "")
          + "\n     surfaces at your next `boot`; edit by re-noting the same title.")
    return 0


def cmd_stats(args):
    """The recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are
    earned lessons being CAPTURED? Computation lives in core/recall/funnel.py (shared with the
    boot pulse + SessionStart whisper); this renders it. --days N adds a per-day trend from
    DURABLE records (flip events + lesson timestamps) and the 30d pace vs the Wave-A gate."""
    import json as _json
    from core.recall.funnel import snapshot, trend, TARGET_LESSONS_30D
    hours = float(args.hours or 24)
    out = snapshot(hours=hours)
    days = getattr(args, "days", None)
    tr = trend(days=days) if days else None
    if getattr(args, "json", False):
        if tr:
            out = {**out, "trend": tr}
        print(_json.dumps(out, indent=2))
        return 0
    use_n, window = out["tracked_sources"], out["window"]
    print("RECALL-VALUE FUNNEL  (all-time counters + a recent window)")
    print(f"  corpus: {out['corpus_lessons']} lesson(s), {use_n} tracked by recall")
    print(f"  surfaced impressions: {out['surfaced_impressions']} | "
          f"votes: useful={out['votes']['useful']} noise={out['votes']['noise']}")
    print(f"  helped credits (flips that credited a surfaced lesson): {out['helped_credits']}")
    if out.get("value_rate") is not None:
        print(f"  value rate ((useful+helped)/surfaced): {out['value_rate'] * 100:.1f}%"
              " -- the steering number; watch the trend, not the level")
    print(f"  lessons with a track record (helped or useful > 0): {out['lessons_with_track_record']}")
    print(f"  last {hours:g}h: flips={window['flips']} (credited={window['flips_credited']}, "
          f"corpus-gap={window['flips_corpus_gap']}) | lessons recorded={window['lessons_recorded']}"
          f" | lessons-per-flip={window['lessons_per_flip']}")
    if window["flips_corpus_gap"] and not window["lessons_recorded"]:
        print("  hint: flips happened where NO stored lesson helped and nothing was recorded --"
              " `wrap` has pre-filled candidates.")
    if window.get("injections"):
        print(f"  push cost last {hours:g}h: {window['injections']} injection(s), "
              f"~{window['injected_tokens_approx']} tokens -- `injections` for the ledger")
    if tr:
        print(f"\nTREND (last {tr['days']}d, durable records: lesson timestamps + flip events)")
        for b in tr["per_day"]:
            bar = "#" * min(b["lessons"], 40)
            print(f"  {b['date']}  lessons={b['lessons']:<3} flips={b['flips']:<3} "
                  f"credited={b['credited']:<3} {bar}")
        pace = tr["lessons_30d"] / 30.0
        need = TARGET_LESSONS_30D / 30.0
        print(f"  30d pace: {tr['lessons_30d']} recorded vs target {tr['target_30d']} "
              f"({pace:.1f}/day vs {need:.1f}/day needed)")
        if tr["events_capped"]:
            print("  note: event scan hit its cap -- older flips may be missing from the trend.")
    return 0


LAST_SESSION_DRAFT = "last-session-draft.md"   # under chronicles/; auto-captured by the SessionEnd/PreCompact hook


def last_session_draft_path():
    return str(Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "chronicles" / LAST_SESSION_DRAFT)


def write_last_session_draft(path, commits, lessons, notes, trigger="", flips=None):
    """Write a session draft to a FILE (not a note) -- the auto-capture target for the SessionEnd/
    PreCompact hook, so an abrupt end still leaves a trail. boot surfaces a pointer; you promote it
    with `wrap --commit` only if it's worth keeping. Returns the path, or None if there was no activity."""
    from datetime import datetime
    draft = build_session_draft(commits, lessons, notes, flips=flips)
    if not draft or draft == "(no session activity captured)":
        return None
    when = datetime.now().isoformat(timespec="seconds")
    header = (f"# Last-session draft (auto-captured {when}"
              f"{' at ' + trigger if trigger else ''}) — review, then promote with "
              "`py agent_cli.py wrap --commit`\n\n")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(header + draft + "\n", encoding="utf-8")
    return str(p)


# -------------------------------------------------------------------------- story
def cmd_story(args, store=None):
    """Print narrative story views: Atlas, Track, Chapter, Beat, or time-lookup.

    Usage:
      py agent_cli.py story                -> Atlas overview (tracks + chapter counts)
      py agent_cli.py story --chronicle    -> run chronicle_all first, then Atlas
      py agent_cli.py story --track NAME   -> chapters in that track
      py agent_cli.py story --theme NAME   -> chapters with beats in that theme
      py agent_cli.py story --themes       -> list all themes with beat counts
      py agent_cli.py story --at ISO       -> find chapter containing that timestamp
      py agent_cli.py story --chapter ID   -> full chapter detail
      py agent_cli.py story --beat ID      -> full beat detail
      py agent_cli.py story --json         -> any of the above as JSON
    """
    from core.narrative.chronicler import Chronicler
    from core.narrative.schema import Beat, Chapter, Track, Atlas, Edge, beat_key, chapter_key, track_key
    from core.foundation.store import create_store
    from core.narrative.track_router import RouteHint
    import json as _json

    if store is None:
        store = create_store()
    from core.narrative.beat_log import BeatLog
    beat_log = BeatLog(store)
    atlas_raw = store.get("narr:atlas:current")

    # --mark "title": declare an explicit chapter boundary + title (Slice 1/4).
    # A `mark` beat forces a new chapter and names it, then we re-chronicle.
    mark_title = getattr(args, "mark", None)
    if mark_title:
        from datetime import datetime as _dtm
        beat_log.emit("mark", summary=mark_title, source=f"mark:{_dtm.utcnow().isoformat()}",
                      hint=RouteHint(category="meta", task="mark_chapter"))

    # --session-end: close the session (emits session-end beat) then chronicle.
    if getattr(args, "session_end", False):
        from core.narrative.session import end_session
        end_session(store, now=args.at if args.at else None)
        if not args.json:
            print("  (session closed)")
        atlas_raw = store.get("narr:atlas:current")
        if atlas_raw and not args.chronicle:
            atlas = Atlas.from_dict(_json.loads(atlas_raw))
            _print_atlas(atlas, store)
        return 0

    # --chronicle flag (also triggered by --mark): run chronicle_all first
    if args.chronicle or mark_title:
        c = Chronicler(beat_log=beat_log, store=store)
        report = c.chronicle_all(now=args.at if args.at else None)
        atlas_raw = store.get("narr:atlas:current")
        if args.json:
            print(_json.dumps(report, indent=2, default=str))
            return 0
        if atlas_raw:
            atlas = Atlas.from_dict(_json.loads(atlas_raw))
            _print_atlas(atlas, store)
        print(f"  (chronicled {report['chapters']} chapters, "
              f"{report['tracks']} tracks, {report['total_beats']} beats)")
        return 0

    # --beat ID: full beat detail
    if args.beat:
        raw = store.get(beat_key(args.beat))
        if not raw:
            raw = store.get(f"narr:beat:{args.beat}")
        if not raw:
            print(f"ERROR: beat '{args.beat}' not found.")
            return 2
        try:
            beat = Beat.from_dict(_json.loads(raw))
        except _json.JSONDecodeError:
            print(f"ERROR: corrupt data for beat '{args.beat}'.")
            return 2
        if args.json:
            print(_json.dumps(beat.to_dict(), indent=2, default=str))
            return 0
        _print_beat(beat)
        # --raw: drill from this Beat into the un-distilled record beneath it (Slice 4)
        if getattr(args, "raw", False):
            from core.narrative.event_bridge import raw_for_beat
            res = raw_for_beat(args.beat, store=store)
            if res.get("atom"):
                print(f"\nRaw atom (this beat's source):\n  [{res['atom'].get('kind')}] "
                      f"{_clip(res['atom'].get('summary', ''), 90)}")
            evs = res.get("events", [])
            print(f"\n## RAW EVENTS around this beat ({len(evs)})")
            for e in evs[:20]:
                print(f"  [{e.get('kind', '?')}] {str(e.get('at', ''))[:19]}  "
                      f"{_clip(e.get('summary', ''), 80)}")
            if not evs:
                print("  (none captured in this window)")
        return 0

    # --chapter ID: full chapter detail
    if args.chapter:
        raw = store.get(chapter_key(args.chapter))
        if not raw:
            raw = store.get(f"narr:chapter:{args.chapter}")
        if not raw:
            print(f"ERROR: chapter '{args.chapter}' not found.")
            return 2
        try:
            ch = Chapter.from_dict(_json.loads(raw))
        except _json.JSONDecodeError:
            print(f"ERROR: corrupt data for chapter '{args.chapter}'.")
            return 2
        if args.json:
            print(_json.dumps(ch.to_dict(), indent=2, default=str))
            return 0
        _print_chapter(ch, store)
        return 0

    # No atlas -> no story yet
    if not atlas_raw:
        print("ERROR: no story found. Run `py agent_cli.py story --chronicle` first.")
        return 2

    try:
        atlas = Atlas.from_dict(_json.loads(atlas_raw))
    except _json.JSONDecodeError:
        print("ERROR: corrupt atlas data.")
        return 2

    # --at ISO: find which chapter contains this time
    if args.at and not args.chronicle:
        from datetime import datetime as _dt
        try:
            target = _dt.fromisoformat(args.at)
            target_ts = target.timestamp()
        except (ValueError, TypeError):
            print(f"ERROR: invalid timestamp '{args.at}'. Use ISO format like 2026-06-27T10:00:00.")
            return 2

        found = []
        for t in atlas.tracks:
            raw_t = store.get(track_key(t))
            if raw_t:
                tr = Track.from_dict(_json.loads(raw_t))
                for cid in tr.chapters:
                    raw_ch = store.get(chapter_key(cid))
                    if raw_ch:
                        ch = Chapter.from_dict(_json.loads(raw_ch))
                        try:
                            start = _dt.fromisoformat(ch.span_start).timestamp()
                            end = _dt.fromisoformat(ch.span_end).timestamp() if ch.span_end else float("inf")
                            if start <= target_ts <= end:
                                found.append(ch)
                        except (ValueError, TypeError):
                            continue
        if args.json:
            print(_json.dumps([ch.to_dict() for ch in found], indent=2, default=str))
            return 0
        if not found:
            print(f"No chapter contains {args.at}")
            return 1
        print(f"# Chapters containing {args.at}")
        for ch in found:
            _print_chapter(ch, store)
        return 0

    # --themes: list all themes with beat counts
    if args.themes:
        all_chapters = []
        for t in atlas.tracks:
            raw_t = store.get(track_key(t))
            if raw_t:
                tr = Track.from_dict(_json.loads(raw_t))
                for cid in tr.chapters:
                    raw_ch = store.get(chapter_key(cid))
                    if raw_ch:
                        all_chapters.append(Chapter.from_dict(_json.loads(raw_ch)))
        theme_counts = {}
        for ch in all_chapters:
            for bid in ch.beats:
                raw_b = store.get(beat_key(bid))
                if raw_b:
                    b = Beat.from_dict(_json.loads(raw_b))
                    for th in b.themes:
                        theme_counts[th] = theme_counts.get(th, 0) + 1
        if args.json:
            print(_json.dumps(theme_counts, indent=2))
            return 0
        print("# Themes")
        if not theme_counts:
            print("  (no themes found)")
            return 0
        for th, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
            print(f"  {th}: {count} beat(s)")
        return 0

    # --theme NAME: cross-track chapters containing beats with this theme
    if args.theme:
        found = []
        for t in atlas.tracks:
            raw_t = store.get(track_key(t))
            if raw_t:
                tr = Track.from_dict(_json.loads(raw_t))
                for cid in tr.chapters:
                    raw_ch = store.get(chapter_key(cid))
                    if raw_ch:
                        ch = Chapter.from_dict(_json.loads(raw_ch))
                        for bid in ch.beats:
                            raw_b = store.get(beat_key(bid))
                            if raw_b:
                                b = Beat.from_dict(_json.loads(raw_b))
                                if args.theme in b.themes:
                                    found.append(ch)
                                    break
        if args.json:
            print(_json.dumps([ch.to_dict() for ch in found], indent=2, default=str))
            return 0
        if not found:
            print(f"No chapters contain theme '{args.theme}'")
            return 1
        print(f"# Theme: {args.theme} ({len(found)} chapters)")
        for ch in found:
            _print_chapter_summary(ch)
        return 0

    # --track NAME: chapters in that track
    if args.track:
        ch_ids = None
        raw_t = store.get(track_key(args.track))
        if raw_t:
            try:
                tr = Track.from_dict(_json.loads(raw_t))
            except _json.JSONDecodeError:
                print(f"ERROR: corrupt data for track '{args.track}'.")
                return 2
            ch_ids = tr.chapters
        else:
            ch_ids = []
        # Errors that teach (ACI): a track can have Beats but no Chapters yet (not
        # chronicled). Say so, and the exact next step -- don't just say "not found".
        if not ch_ids:
            try:
                nbeats = store.zcard(f"narr:track:{args.track}:beats")
            except Exception:
                nbeats = 0
            if nbeats:
                print(f"Track '{args.track}' has {nbeats} beat(s) but no chapters yet -- "
                      f"run `py agent_cli.py story --chronicle` first, then retry.")
            else:
                print(f"ERROR: track '{args.track}' not found. "
                      f"Available: {', '.join(atlas.tracks) or '(none yet)'}")
            return 2
        chapters = []
        for cid in ch_ids:
            raw_ch = store.get(chapter_key(cid))
            if raw_ch:
                chapters.append(Chapter.from_dict(_json.loads(raw_ch)))
        chapters.sort(key=lambda c: c.span_start)
        if args.json:
            print(_json.dumps([ch.to_dict() for ch in chapters], indent=2, default=str))
            return 0
        print(f"# Track: {args.track} ({len(chapters)} chapters)")
        for ch in chapters:
            _print_chapter_summary(ch)
        return 0

    # Default: Atlas overview
    if args.json:
        print(_json.dumps(atlas.to_dict(), indent=2, default=str))
        return 0

    _print_atlas(atlas, store)
    return 0


def _print_atlas(atlas, store) -> None:
    """Print atlas overview to stdout."""
    from core.narrative.schema import Track, track_key, chapter_key
    import json
    print(f"# Story Atlas")
    print(f"Generated: {atlas.generated_at}")
    print(f"Tracks: {', '.join(atlas.tracks)}")
    for t in atlas.tracks:
        raw = store.get(track_key(t))
        count = 0
        if raw:
            tr = Track.from_dict(json.loads(raw))
            count = len(tr.chapters)
        print(f"  {t}: {count} chapter(s)")
    print(f"\n{atlas.summary}")


def _print_chapter_summary(ch) -> None:
    """Short summary line for a chapter."""
    print(f"  [{ch.track}] {ch.id}: \"{ch.title}\" ({len(ch.beats)} beats, "
          f"{ch.span_start} -> {ch.span_end or 'present'})")


def _print_chapter(ch, store) -> None:
    """Full chapter detail."""
    from core.narrative.schema import chapter_key
    print(f"# Chapter: {ch.id}")
    print(f"Track: {ch.track}")
    print(f"Title: {ch.title}")
    print(f"Span: {ch.span_start} -> {ch.span_end or 'present'}")
    print(f"Beats: {len(ch.beats)}  |  Critic-ok: {ch.critic_ok}")
    print(f"Recorded: {ch.recorded_at}")
    print(f"\n{ch.summary}\n")
    if ch.commits:
        print("Commits:")
        for s in ch.commits[:5]:
            print(f"  {s}")
    if ch.beats:
        print("\nDrill into a beat:")
        print(f'  py agent_cli.py story --beat {ch.beats[0]}')
    if ch.id:
        print(f"\nRaw JSON:")
        print(f'  py agent_cli.py story --chapter {ch.id} --json')


def _print_beat(beat) -> None:
    """Full beat detail."""
    from core.narrative.schema import chapter_key
    print(f"# Beat: {beat.id}")
    print(f"Kind: {beat.kind}  |  Track: {beat.track}  |  Weight: {beat.weight}")
    print(f"At: {beat.at}")
    print(f"Source: {beat.source}")
    print(f"Summary: {beat.summary}")
    if beat.chapter:
        print(f"Chapter: {beat.chapter}")
        print(f'  py agent_cli.py story --chapter {beat.chapter}')
    if beat.relates:
        for e in beat.relates:
            print(f"  relates: ({e.type}) {e.target}")
    if beat.themes:
        print(f"Themes: {', '.join(beat.themes)}")


# --------------------------------------------------------------------------- log
def cmd_log(args):
    """Record an arbitrary narrative Beat (action/task/note) without a learning entry.

    Usage:
      py agent_cli.py log <kind> --summary "what happened" --source "who:action"
                             [--category C] [--task T] [--json]
    """
    from core.narrative.beat_log import get_beat_log
    from core.narrative.track_router import RouteHint
    kind = args.kind or "note"
    summary = args.summary or "no summary"
    source = args.source or "agent_cli:log"
    try:
        beat = get_beat_log().emit(
            kind, summary=summary, source=source,
            hint=RouteHint(category=args.category or "", task=args.task or ""))
        ok = beat is not None
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 1
    # Auto-logger (Slice 2): a logged action is also a RAW event. We stamp the Beat's id
    # into refs so Slice 5 promotion won't create a redundant Beat for it. Best-effort.
    try:
        from core.events.event_log import capture_event
        refs = [r for r in [f"beat:{beat.id}" if beat else None, source] if r]
        capture_event(kind, summary, refs=refs or None,
                      detail={"category": args.category or "", "task": args.task or ""})
    except Exception:
        pass
    if args.json:
        print(json.dumps({"recorded": ok, "kind": kind, "beat_id": beat.id if beat else None}))
    else:
        print(f"[{'OK' if ok else 'FAIL'}] {kind}: {summary[:80]}")
    return 0 if ok else 1


# ------------------------------------------------------------------------ episode (session bookends)
def cmd_episode(args):
    """Session bookends: the live current episode, close+draft, and accept.

    An episode IS a narrative Chapter with an open span + `why` (intent). Emits the JSON contract the
    Bifrost UI renders against (docs/session-bookends-design-2026-07.md §6). Usage:
      py agent_cli.py episode current --json
      py agent_cli.py episode close [--accept-title T --accept-desc D --accept-why W] --json
      py agent_cli.py episode accept <chapter_id> [--title T --desc D --why W] --json
    """
    from core.narrative import episode as ep
    act = args.action
    if act == "current":
        out = ep.current_episode()
    elif act == "close":
        # one-shot finalize when any --accept-* is supplied (the agent/AI path that skips the edit dialog)
        acc = any(x is not None for x in (args.accept_title, args.accept_desc, args.accept_why))
        out = ep.close_episode(title=args.accept_title, description=args.accept_desc,
                               why=args.accept_why, finalize=acc)
    elif act == "accept":
        if not args.chapter_id:
            out = {"error": "accept needs a <chapter_id>"}
        else:
            out = ep.accept_episode(None, args.chapter_id, title=args.title,
                                    description=args.desc, why=args.why)
    else:
        out = {"error": "unknown_action", "action": act}
    if getattr(args, "json", False):
        print(json.dumps(out, indent=2, default=str))
        return 0 if "error" not in out else 1
    # compact human view
    if "error" in out:
        print(f"[episode] {out['error']}")
        return 1
    if act == "current":
        c = out.get("current_chapter")
        if not c:
            print("[episode] no current episode")
        else:
            print(f"[episode] current: {c['title'] or '(untitled, open)'} "
                  f"({c['duration_seconds']}s, {c['beats_count']} beats)")
            if c.get("why"):
                print(f"  why: {c['why']}")
    elif act == "close":
        d = out.get("draft") or {}
        print(f"[episode] closed {d.get('chapter_id')}")
        print(f"  title: {d.get('title')}")
        print(f"  desc : {d.get('description')}")
        print(f"  why  : {d.get('why')}")
        print("  (edit + finalize: py agent_cli.py episode accept "
              f"{d.get('chapter_id')} --title ... --why ...)")
    elif act == "accept":
        c = out.get("chapter") or {}
        print(f"[episode] finalized {c.get('id')}: {c.get('title')}")
    return 0


# ------------------------------------------------------------------------ handoff
def _incoming_handoffs(target_agent, scan=10000):
    """Every handoff signal addressed to `target_agent`, oldest-first."""
    from core.signals.agent_signal_ledger import AgentSignalLedger
    sl = AgentSignalLedger()
    out = []
    for _cid, sig in sl.replay_signals(after_id="0", count=scan):
        if sig.get("signal_type") == "handoff" and sig.get("target_agent") == target_agent:
            out.append(sig)
    return out


def cmd_handoff(args):
    """Hand work to another agent (cross-agent continuity).

    Writing a handoff leaves a briefing that the TARGET agent's next `boot` surfaces
    automatically (Context pillar reads the latest handoff addressed to it). With
    --list, show the handoffs currently addressed to an agent instead of writing one.

    Usage:
      py agent_cli.py handoff <from_agent> --to <agent> --task "..." [--note "..."]
                              [--blocker "a || b"] [--json]
      py agent_cli.py handoff <from_agent> --list [--to <agent>] [--json]
    """
    # --list: read mode -- show handoffs addressed to (--to OR this agent).
    if args.list:
        who = (args.to or args.agent_id or "").strip()
        items = _incoming_handoffs(who)
        if args.json:
            print(json.dumps(items, indent=2, default=str)); return 0
        print(f"# {len(items)} handoff(s) addressed to '{who}' (newest last)")
        for s in items[-25:]:
            note = (s.get("context") or {}).get("note", "")
            print(f"  - from {s.get('agent_id', '?')}: {_clip(s.get('task', ''), 120)}"
                  + (f"  | {_clip(note, 80)}" if note else ""))
        return 0

    to_agent = (args.to or "").strip()
    task = (args.task or "").strip()
    if not to_agent or not task:
        print("ERROR: need --to <agent> and --task \"...\" (or --list to read).")
        print('Example: py agent_cli.py handoff cursor --to claude '
              '--task "finish C3 threshold tuning" --note "see docs/codex-plan.md"')
        return 2

    from core.signals.coordinator_api import SignalEmitter
    ctx = {}
    if (args.note or "").strip():
        ctx["note"] = _clip(args.note, 1000)
    blockers = [b.strip() for b in (args.blocker or "").split("||") if b.strip()]
    try:
        em = SignalEmitter(_clip(args.agent_id, 200))
        em.emit_handoff_to_target_agent(to_agent, _clip(task, 500), context=ctx, blockers=blockers)
        ok = True
    except Exception as e:
        print(f"ERROR recording handoff: {type(e).__name__}: {e}")
        return 1

    # Narrative spine + raw firehose visibility (best-effort): a handoff is a salient
    # Beat AND a raw event, so it shows up in `story` and the cross-agent `events`.
    try:
        from core.narrative.beat_log import get_beat_log
        from core.narrative.track_router import RouteHint
        get_beat_log().emit("handoff",
                            summary=f"{args.agent_id} -> {to_agent}: {task}",
                            source=f"handoff:{args.agent_id}->{to_agent}",
                            hint=RouteHint(category="handoff", task=task))
    except Exception:
        pass
    try:
        from core.events.event_log import capture_event
        capture_event("handoff", f"{args.agent_id} -> {to_agent}: {task}",
                      agent_id=args.agent_id,
                      detail={"target_agent": to_agent, "task": task,
                              "note": ctx.get("note", ""), "blockers": blockers})
    except Exception:
        pass

    if args.json:
        print(json.dumps({"recorded": ok, "from": args.agent_id, "to": to_agent, "task": task}))
    else:
        print(f"[{'OK' if ok else 'FAIL'}] handoff {args.agent_id} -> {to_agent}: {_clip(task, 80)}")
        print(f"  (the target's next `boot` will surface this as its briefing)")
        _warn_unmirrored()   # session-end: don't hand off on top of unmirrored work
    return 0 if ok else 1


# ------------------------------------------------------------------------- events
def _print_events(evs, args, header):
    """Render raw events ASCII-safe, front-loaded, with drill pointers."""
    if args.json:
        print(json.dumps(evs, indent=2, default=str))
        return
    print(header)
    if not evs:
        print("  (none)")
        return
    for e in evs:
        at = str(e.get("at", ""))[:19]
        line = f"  [{e.get('kind', '?')}] {at}  {_clip(e.get('summary', ''), 90)}"
        print(line)
        tail = e.get("_ref", "")
        if e.get("track"):
            tail += f"   track={e['track']}"
        if e.get("agent_id"):
            tail += f"   by={e['agent_id']}"
        print(f"      {tail}")
    print("\nDrill into one:")
    print(f"  py agent_cli.py events --get {evs[0].get('_ref')}")


def cmd_events(args):
    """Search / drill / capture the raw event firehose (the auto-logger's read door).

    Usage:
      py agent_cli.py events                              -> recent raw events
      py agent_cli.py events --search "query" [filters]   -> rank by relevance
      py agent_cli.py events --around <beat|chapter|ISO> [--window 30m]
      py agent_cli.py events --get event:events:raw:<id>  -> one event
      py agent_cli.py events --capture --kind K --summary "..." [--detail-json '{...}']
    Filters: --kind --agent --track --since ISO --until ISO --limit N --json
    """
    from core.events.event_log import get_event_log
    from core.events.event_query import get_event_query
    eq = get_event_query()

    # --capture: external-runtime write door (the agent shells in one raw event)
    if args.capture:
        detail = None
        if args.detail_json:
            try:
                detail = json.loads(args.detail_json)
            except (ValueError, TypeError):
                print("ERROR: --detail-json must be valid JSON.")
                return 2
        refs = [r for r in (args.refs or "").split(",") if r.strip()] or None
        ev = get_event_log().capture(args.kind or "note", args.summary or "",
                                     detail=detail, agent_id=args.agent, refs=refs,
                                     track=args.track)
        if args.json:
            print(json.dumps(ev, default=str))
        else:
            print(f"[{'OK' if ev else 'FAIL'}] captured {args.kind or 'note'}: "
                  f"{_clip(args.summary or '', 80)}" + (f"  -> {ev['_ref']}" if ev else ""))
        return 0 if ev else 1

    # --promote: consolidate salient raw events into Beats (reflection; rate-limited)
    if args.promote:
        from core.narrative.event_promoter import promote_salient
        rep = promote_salient(threshold=args.threshold if args.threshold is not None else 3,
                              max_promote=args.limit or 10)
        if args.json:
            print(json.dumps(rep))
        else:
            print(f"# promotion: {rep['promoted']} promoted / {rep['eligible']} eligible "
                  f"(scanned {rep['scanned']}, skipped {rep['skipped_dup']} dup + "
                  f"{rep['skipped_beat']} already-beat)")
        return 0

    # --get: resolve one followable pointer
    if args.get:
        ev = eq.get(args.get)
        if not ev:
            print(f"ERROR: no event for '{args.get}'.")
            return 2
        print(json.dumps(ev, indent=2, default=str) if args.json
              else f"[{ev.get('kind')}] {ev.get('at')}\n  {ev.get('summary')}\n  detail: {ev.get('detail')}")
        return 0

    # --around: the timeline bridge (chapter/beat/timestamp -> raw events under it)
    if args.around:
        from core.narrative.event_bridge import events_around, parse_window
        res = events_around(args.around, window_seconds=parse_window(args.window),
                            kind=args.kind, agent=args.agent, track=args.track, limit=args.limit)
        if res["span"] is None:
            print(f"ERROR: could not resolve '{args.around}' to a chapter / beat / ISO timestamp.")
            return 2
        sp = res["span"]
        _print_events(res["events"], args,
                      f"# {len(res['events'])} raw event(s) in {sp['start'][:19]} -> {sp['end'][:19]}")
        return 0

    # --search: relevance-ranked; or default: recent
    if args.search is not None:
        evs = eq.search(_clip(args.search, 200), kind=args.kind, agent=args.agent,
                        track=args.track, since=args.since, until=args.until,
                        top_k=args.limit or 10)
        _print_events(evs, args, f"# {len(evs)} event(s) matching '{args.search}'")
    else:
        evs = get_event_log().recent(args.limit or 20, agent=args.agent)
        _print_events(evs, args, f"# {len(evs)} recent raw event(s)"
                      + (f" by {args.agent}" if args.agent else ""))
    return 0


# ---------------------------------------------------------------------- promoted (B2 read side)
def cmd_promoted(args):
    """Query durable salient Bifrost messages (kind=bifrost_msg in the event firehose)."""
    from core.comm.promoter import promoted
    from agent.bifrost_pull import format_promoted_events
    evs = promoted(limit=args.limit or 20, since=args.since, until=args.until)
    print(format_promoted_events(evs, json_out=bool(args.json)))
    return 0


def cmd_console_log(args):
    """Query durable console control-plane events (interjection/bus_control/file_drop -> Ledger)."""
    from core.comm.promoter import console_events
    from agent.bifrost_pull import format_console_events
    evs = console_events(limit=args.limit or 20, since=args.since, until=args.until)
    print(format_console_events(evs, json_out=bool(args.json)))
    return 0


def cmd_bifrost_sync(args):
    """Presence heartbeat + unread inbox peek (pull floor). --consume advances the cursor."""
    from agent.bifrost_pull import (collect_boot_bifrost, consume_inbox, format_inbox_line,
                                     format_digest_line, print_boot_bifrost_section,
                                     print_boot_locks_section)
    if args.consume:
        msgs = consume_inbox(args.agent_id, limit=args.limit or 20)
        if args.json:
            print(json.dumps({"consumed": msgs}, indent=2, default=str))
            return 0
        if not msgs:
            print("(no messages consumed)")
            return 0
        print(f"# consumed {len(msgs)} message(s) for {args.agent_id}")
        for m in msgs:
            print(f"  {format_inbox_line(m)}")
        return 0
    block = collect_boot_bifrost(args.agent_id, limit=args.limit or 10)
    if args.json:
        print(json.dumps(block, indent=2, default=str))
        return 0
    if getattr(args, "digest", False):
        # cheap scan: only-new headlines (cursor-based, no body) -- read the bus without
        # paying to reread the conversation. Drill a headline with `bifrost-sync` (full) or --json.
        msgs = block.get("messages") or []
        print(f"# bifrost digest for {args.agent_id}: {len(msgs)} unread"
              + (" (bus OFFLINE)" if not block.get("bus_online") else ""))
        for m in msgs:
            print(format_digest_line(m))
        print_boot_locks_section(block, args.agent_id)
        return 0
    print(f"# bifrost-sync for {args.agent_id}")
    print_boot_bifrost_section(block)
    print_boot_locks_section(block, args.agent_id)
    return 0


def cmd_bifrost_send(args):
    """Send a message to another agent on the Bifrost bus (or --broadcast to all). The sender is
    args.agent_id; the recipient is --to. Rings the doorbell so a runner/waiter wakes."""
    from core.comm.bus import Bus
    bus = Bus(args.agent_id)
    if not bus.online:
        print("[bifrost-send] bus OFFLINE (Redis down) -- not sent."); return 1
    bus.register()
    text = " ".join(args.text) if isinstance(args.text, list) else str(args.text)
    if args.broadcast:
        mid = bus.broadcast(args.kind, text)
        dest = "*"
    else:
        if not args.to:
            print('ERROR: bifrost-send needs --to <agent> (or --broadcast). '
                  'e.g. bifrost-send claude --to deepseek "hi"'); return 2
        mid = bus.send(args.to, args.kind, text)
        dest = args.to
    if args.json:
        print(json.dumps({"sent": bool(mid), "id": mid, "to": dest, "kind": args.kind}, default=str))
        return 0 if mid else 1
    print(f"[bifrost-send] -> {dest} [{args.kind}] (id {mid})" if mid else "[bifrost-send] send failed")
    return 0 if mid else 1


def cmd_bifrost_pause(args):
    """Freeze the bus auto-responders (human barge-in). They hold until `bifrost-resume`."""
    from core.comm import control
    ok = control.pause(reason=args.reason or "", by=args.by or "user")
    if args.json:
        print(json.dumps(control.pause_status(), default=str)); return 0 if ok else 1
    print("[bifrost] PAUSED -- runners frozen; resume with `bifrost-resume`" if ok
          else "[bifrost] pause failed (bus offline)")
    return 0 if ok else 1


def cmd_bifrost_resume(args):
    """Un-freeze the bus auto-responders."""
    from core.comm import control
    ok = control.resume()
    print("[bifrost] RESUMED" if ok else "[bifrost] resume failed (bus offline)")
    return 0 if ok else 1


def cmd_bifrost_nudge(args):
    """Send a TARGETED, fidelity-graded signal to ONE peer (unlike pause, which freezes the whole bus):
      --mode interrupt (default): HARD barge-in -- set the nudge flag + kind=nudge; the peer drops its
                                   current work at the next round boundary and switches.
      --mode steer:               SOFT -- queue a fact (kind=steer) its runner folds into its CURRENT
                                   task between rounds; it keeps going, adjusted.
      --mode inform:              AMBIENT -- kind=inform; the peer adopts it at its next turn, no disruption."""
    from core.comm.bus import Bus
    from core.comm import nudge
    if not args.to:
        print('ERROR: bifrost-nudge needs --to <agent>. e.g. bifrost-nudge claude --to deepseek "look at X"')
        return 2
    mode = (getattr(args, "mode", None) or "interrupt").lower()
    if mode not in ("interrupt", "steer", "inform"):
        print(f"ERROR: --mode must be interrupt|steer|inform (got {mode!r})"); return 2
    bus = Bus(args.agent_id)
    if not bus.online:
        print("[bifrost-nudge] bus OFFLINE (Redis down) -- not sent."); return 1
    bus.register()
    text = " ".join(args.text) if isinstance(args.text, list) else str(args.text)
    meta = {"via": f"{args.agent_id}-cli", "hops": 0}
    if mode == "interrupt":
        nudge.nudge(args.to, by=args.agent_id, reason=text[:80])
        mid = bus.send(args.to, "nudge", text, meta=meta)
    elif mode == "steer":
        nudge.steer_push(args.to, args.agent_id, text)
        mid = bus.send(args.to, "steer", text, meta={**meta, "display_only": True})
    else:  # inform
        mid = bus.send(args.to, "inform", text, meta=meta)
    if args.json:
        print(json.dumps({"sent": bool(mid), "id": mid, "to": args.to, "mode": mode}, default=str))
        return 0 if mid else 1
    print(f"[bifrost-nudge:{mode}] -> {args.to} (id {mid})" if mid else f"[bifrost-nudge:{mode}] send failed")
    return 0 if mid else 1


# -------------------------------------------------------------------------- locks
def cmd_lock(args):
    """Claim an advisory path-lock so the peer sees you're editing it (C2). Re-claiming
    your own lock refreshes its TTL. Advisory: it coordinates, it does not OS-enforce."""
    from core.comm.locks import LockManager
    res = LockManager(args.agent_id).acquire(args.path, ttl=args.ttl or 900)
    if args.json:
        print(json.dumps(res, default=str)); return 0 if res.get("ok") else 1
    if not res.get("online"):
        print("[lock] bus OFFLINE (Redis down) -- no advisory locking available."); return 1
    if res.get("ok"):
        print(f"[lock] held: {res['path']}  (you={args.agent_id}, token {res['token']})"); return 0
    print(f"[lock] DENIED: {res['path']} is held by {res['held_by']} (token {res['token']}). "
          f"Edit a file you hold, or request a handoff via the bus."); return 1


def cmd_unlock(args):
    from core.comm.locks import LockManager
    ok = LockManager(args.agent_id).release(args.path)
    print(f"[unlock] {'released' if ok else 'not yours / not held'}: {args.path}")
    return 0 if ok else 1


def cmd_locks(args):
    """Awareness: who holds what right now (across both agents)."""
    from core.comm.locks import LockManager
    locks = LockManager(args.agent_id or "viewer").list_locks()
    if args.json:
        print(json.dumps(locks, indent=2, default=str)); return 0
    if not locks:
        print("# no advisory path-locks held"); return 0
    print(f"# {len(locks)} advisory path-lock(s) held")
    for lk in locks:
        mine = " (you)" if lk.get("agent") == args.agent_id else ""
        print(f"  {lk.get('path')}  <- {lk.get('agent')}{mine}  token {lk.get('token')}")
    return 0


# ------------------------------------------------------------------------- status
def cmd_status(args):
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    client = connect_to_redis_with_fail_fast(
        host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=2)
    learn = mem = total = None
    backend = "File (Redis down -> fallback active)"
    if client is not None:
        backend = f"Redis {DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT} (+ File mirror)"
        learn, mem, total = len(client.keys("learn:*")), len(client.keys("mem:*")), len(client.keys("*"))
    # narrative health -- surface the best-effort paths so silent degradation is visible (W-c)
    health = {}
    try:
        from core.foundation.store import create_store
        from core.narrative.health import snapshot
        health = snapshot(create_store())
    except Exception:
        health = {}
    info = {"backend": backend, "learnings": learn, "agent_memory": mem, "total_keys": total,
            "narrative_health": health}
    if args.json:
        print(json.dumps(info, default=str)); return 0
    print(f"# system status")
    print(f"  backend     : {backend}")
    print(f"  learnings   : {learn if learn is not None else 'n/a (see session_logs/)'}")
    print(f"  agent memory: {mem if mem is not None else 'n/a'}")
    if health:
        errors = {k: v for k, v in health.items() if k.endswith(":error")}
        flag = "  [!] errors present" if errors else ""
        print(f"  spine health: {health}{flag}")
    else:
        print(f"  spine health: (no counters yet)")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="agent_cli.py", description="Agent door to the AI-Setup system.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("boot", help="print an agent's startup context")
    b.add_argument("agent_id"); b.add_argument("--task", default=None); b.add_argument("--json", action="store_true")
    b.set_defaults(fn=cmd_boot)

    dsc = sub.add_parser("discover", help="list every verb + its purpose (the self-describing door)")
    dsc.add_argument("query", nargs="?", default="", help="optional substring to filter verbs by name/purpose")
    dsc.add_argument("--json", action="store_true")
    dsc.set_defaults(fn=cmd_discover)

    l = sub.add_parser("learn", help="record a lesson")
    l.add_argument("agent_id"); l.add_argument("--experiment", required=True)
    l.add_argument("--tried", default=""); l.add_argument("--result", default="")
    l.add_argument("--expected", default=""); l.add_argument("--recommend", default="")
    l.add_argument("--category", default=""); l.add_argument("--success", default=None)
    l.add_argument("--confidence", default=None); l.add_argument("--json", action="store_true")
    l.add_argument("--anti-pattern", dest="anti_pattern", default="",
                   help="name a reusable known-bad this lesson documents (recall's dissent-finder warns on it)")
    l.set_defaults(fn=cmd_learn)

    ap = sub.add_parser("tag-anti-pattern", help="tag an EXISTING lesson as a reusable known-bad")
    ap.add_argument("agent_id"); ap.add_argument("--experiment", required=True)
    ap.add_argument("--name", required=True, help="the anti-pattern name/slug")
    ap.add_argument("--reason", default=""); ap.add_argument("--json", action="store_true")
    ap.set_defaults(fn=cmd_tag_anti_pattern)

    r = sub.add_parser("recall", help="search past lessons (no query = list all)")
    r.add_argument("query", nargs="?", default=""); r.add_argument("--json", action="store_true")
    r.add_argument("--full", default=None, help="pull the FULL record for one lesson's source pointer "
                    "(e.g. learn:experiment:NAME) -- the one-hop escape from a capped recall-at surface")
    r.set_defaults(fn=cmd_recall)

    li = sub.add_parser("list", help="list ALL lessons in memory")
    li.add_argument("--json", action="store_true")
    li.set_defaults(fn=cmd_list)

    ra = sub.add_parser("recall-at", help="recall-at-action: relevant lessons/locks for a path or command")
    ra.add_argument("--path", default=None, help="the file path about to be acted on")
    ra.add_argument("--command", default=None, help="the shell command about to run")
    ra.add_argument("--agent-id", dest="agent_id", default=None, help="who is asking (defaults to $AKASHIC_AGENT_ID)")
    ra.add_argument("--limit", type=int, default=3, help="max items to surface (default 3)")
    ra.add_argument("--json", action="store_true")
    ra.set_defaults(fn=cmd_recall_at)

    rf = sub.add_parser("recall-feedback", help="mark a recalled lesson useful/noise (teaches recall what helps)")
    rf.add_argument("--source", required=True, help="the lesson's source pointer, e.g. learn:experiment:NAME")
    rf.add_argument("--useful", action="store_true", help="it changed what you did (default)")
    rf.add_argument("--noise", action="store_true", help="it was off-target")
    rf.set_defaults(fn=cmd_recall_feedback)

    ij = sub.add_parser("injections", help="the injection ledger: what recall pushed into contexts + cost")
    ij.add_argument("--hours", type=float, default=24, help="window (default 24)")
    ij.add_argument("--json", action="store_true")
    ij.set_defaults(fn=cmd_injections)

    hz = sub.add_parser("harnesses",
                        help="integration-tier matrix: what each harness (claude-code/cursor/bare-cli) actually delivers")
    hz.add_argument("--json", action="store_true")
    hz.set_defaults(fn=cmd_harnesses)

    fl = sub.add_parser("fleet",
                        help="local-model dispatch: roster (list) + capability select + direct one-shot call")
    fl.add_argument("action", nargs="?", default="list", choices=["list", "select", "call"],
                    help="list the roster | select a model for a capability | call a model once")
    fl.add_argument("--capability", default=None,
                    help="capability label to filter/route on (generalist, tool-use, extract, summarize, classify, faithful, ...)")
    fl.add_argument("--status", default=None, help="filter by status (active|tested|candidate|gated)")
    fl.add_argument("--probe", action="store_true", help="list: also check live Ollama availability (/api/tags)")
    fl.add_argument("--max-vram", dest="max_vram", type=float, default=None, help="select: max GB VRAM")
    fl.add_argument("--min-context", dest="min_context", type=int, default=None, help="select: min context tokens")
    fl.add_argument("--model", default=None, help="call: the model tag to invoke")
    fl.add_argument("--prompt", default=None, help="call: the prompt text")
    fl.add_argument("--system", default=None, help="call: optional system prompt")
    fl.add_argument("--max-tokens", dest="max_tokens", type=int, default=512, help="call: max output tokens (default 512)")
    fl.add_argument("--temperature", type=float, default=0.2, help="call: sampling temperature (default 0.2)")
    fl.add_argument("--json-out", dest="json_out", action="store_true",
                    help="call: request JSON-formatted MODEL output (Ollama format=json)")
    fl.add_argument("--json", action="store_true", help="print the CLI result as JSON")
    fl.set_defaults(fn=cmd_fleet)

    tr = sub.add_parser("triage",
                        help="sharpening S1: lessons ranked by measured value (protect / cost-no-return / noise) for review")
    tr.add_argument("--min-surfaced", dest="min_surfaced", type=int, default=5,
                    help="impressions before zero-credit counts as cost (default 5)")
    tr.add_argument("--json", action="store_true")
    tr.set_defaults(fn=cmd_triage)

    rc = sub.add_parser("recall-counters",
                        help="sharpening S2a: fold bare-slug + ghost recall:use:* counters (report; --fold applies)")
    rc.add_argument("--fold", action="store_true", help="apply the fix (merge bare slugs, prune zero-credit ghosts)")
    rc.add_argument("--agent-id", dest="agent_id", default=None, help="who ran it (defaults to $AKASHIC_AGENT_ID)")
    rc.set_defaults(fn=cmd_recall_counters)

    gr = sub.add_parser("graduate",
                        help="retire a lesson from recall surfacing -- automation now enforces its rule")
    gr.add_argument("agent_id", help="who is graduating it (you)")
    gr.add_argument("--experiment", default=None, help="the lesson's experiment name")
    gr.add_argument("--enforced-by", dest="enforced_by", default=None,
                    help='the automation that enforces it, e.g. "git-guard PreToolUse hook (C0)"')
    gr.add_argument("--undo", action="store_true", help="reverse a graduation (it surfaces again)")
    gr.add_argument("--json", action="store_true")
    gr.set_defaults(fn=cmd_graduate)

    nt = sub.add_parser("note", help="record a durable project note (write-once; re-note same title to update)")
    nt.add_argument("agent_id")
    nt.add_argument("--title", required=True, help="short stable title (re-noting it supersedes the prior)")
    nt.add_argument("--note", default="", help="the note / decision body")
    nt.add_argument("--context", default="", help="optional supporting context")
    nt.add_argument("--category", default="", help="route-hint category")
    nt.add_argument("--supersedes", default=None, help="explicit prior note id to retire")
    nt.add_argument("--session", default="", help="session id")
    nt.add_argument("--json", action="store_true")
    nt.set_defaults(fn=cmd_note)

    nts = sub.add_parser("notes", help="list active project notes (--project regenerates chronicles/memory.md)")
    nts.add_argument("--limit", type=int, default=25)
    nts.add_argument("--days", type=int, default=None)
    nts.add_argument("--project", action="store_true", help="regenerate the chronicles/memory.md digest")
    nts.add_argument("--json", action="store_true")
    nts.set_defaults(fn=cmd_notes)

    wr = sub.add_parser("wrap", help="distill this session (commits+lessons+notes) into a DRAFT where-we-are note")
    wr.add_argument("--hours", type=int, default=12, help="look-back window for commits (default 12)")
    wr.add_argument("--commit", action="store_true", help="record the draft as a note (default: just preview)")
    wr.add_argument("--title", default=None, help="note title (default: where-we-are <date>)")
    wr.set_defaults(fn=cmd_wrap)

    s = sub.add_parser("status", help="honest system status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    sts = sub.add_parser("stats", help="recall-value funnel: surfaced -> helped -> flips -> captured")
    sts.add_argument("--hours", type=float, default=24, help="window for flips/lessons-recorded (default 24)")
    sts.add_argument("--days", type=int, default=None,
                     help="ALSO print a per-day trend over N days (durable records) + the 30d pace")
    sts.add_argument("--json", action="store_true")
    sts.set_defaults(fn=cmd_stats)

    lg = sub.add_parser("log", help="record an arbitrary narrative Beat")
    lg.add_argument("kind", nargs="?", default="note", help="beat kind (session/note/commit/learning/...)")
    lg.add_argument("--summary", default="", help="summary of what happened")
    lg.add_argument("--source", default="", help="source identifier (who:action)")
    lg.add_argument("--category", default="", help="route hint category")
    lg.add_argument("--task", default="", help="route hint task")
    lg.add_argument("--json", action="store_true", help="JSON output")
    lg.set_defaults(fn=cmd_log)

    epi = sub.add_parser("episode", help="session bookends: current episode, close+draft, accept")
    epi.add_argument("action", choices=["current", "close", "accept"], help="what to do")
    epi.add_argument("chapter_id", nargs="?", default=None, help="(accept) the closed chapter to finalize")
    epi.add_argument("--title", default=None, help="(accept) set the title")
    epi.add_argument("--desc", default=None, help="(accept) set the description")
    epi.add_argument("--why", default=None, help="(accept) set the why/intent")
    epi.add_argument("--accept-title", dest="accept_title", default=None,
                     help="(close, one-shot) finalize immediately with this title")
    epi.add_argument("--accept-desc", dest="accept_desc", default=None,
                     help="(close, one-shot) finalize immediately with this description")
    epi.add_argument("--accept-why", dest="accept_why", default=None,
                     help="(close, one-shot) finalize immediately with this why")
    epi.add_argument("--json", action="store_true")
    epi.set_defaults(fn=cmd_episode)

    st = sub.add_parser("story", help="print narrative story views")
    st.add_argument("--chronicle", action="store_true", help="run chronicle_all first")
    st.add_argument("--mark", default=None, metavar="TITLE",
                    help="declare an explicit chapter boundary titled TITLE, then chronicle")
    st.add_argument("--session-end", action="store_true", help="close the session then chronicle")
    st.add_argument("--track", default=None, help="filter to a named track")
    st.add_argument("--theme", default=None, help="filter chapters by theme")
    st.add_argument("--themes", action="store_true", help="list all themes with beat counts")
    st.add_argument("--at", default=None, help="find chapter containing this ISO timestamp")
    st.add_argument("--chapter", default=None, help="show full chapter detail by ID")
    st.add_argument("--beat", default=None, help="show full beat detail by ID")
    st.add_argument("--raw", action="store_true",
                    help="with --beat: also show the raw events around it (auto-logger drill-down)")
    st.add_argument("--json", action="store_true", help="JSON output")
    st.set_defaults(fn=cmd_story)

    h = sub.add_parser("handoff", help="hand work to another agent (writes a briefing its next boot reads)")
    h.add_argument("agent_id", help="who is handing off (you)")
    h.add_argument("--to", default=None, help="target agent who picks the work up")
    h.add_argument("--task", default=None, help="what the target should do")
    h.add_argument("--note", default=None, help="free-form context note for the target")
    h.add_argument("--blocker", default=None, help="blockers to flag, separated by ' || '")
    h.add_argument("--list", action="store_true", help="list handoffs addressed to --to (or you) instead of writing")
    h.add_argument("--json", action="store_true", help="JSON output")
    h.set_defaults(fn=cmd_handoff)

    ev = sub.add_parser("events", help="search / drill / capture the raw event firehose")
    ev.add_argument("--search", default=None, metavar="QUERY", help="rank raw events by relevance to QUERY")
    ev.add_argument("--around", default=None, metavar="REF",
                    help="raw events around a beat id / chapter id / ISO timestamp")
    ev.add_argument("--window", default=None, help="window around --around target (e.g. 30m, 2h, 1d; default 30m)")
    ev.add_argument("--get", default=None, metavar="REF", help="resolve one event:<stream>:<id> pointer")
    ev.add_argument("--capture", action="store_true", help="append a raw event (external runtimes)")
    ev.add_argument("--promote", action="store_true",
                    help="consolidate salient raw events into narrative Beats (rate-limited)")
    ev.add_argument("--threshold", type=int, default=None, help="promote: min salience 0..5 (default 3)")
    ev.add_argument("--kind", default=None, help="filter, or kind to capture (tool_call/command/...)")
    ev.add_argument("--summary", default=None, help="capture: the event summary")
    ev.add_argument("--detail-json", default=None, dest="detail_json", help="capture: JSON detail payload")
    ev.add_argument("--refs", default=None, help="capture: comma-separated source refs")
    ev.add_argument("--agent", default=None, help="filter / capture agent id")
    ev.add_argument("--track", default=None, help="filter / capture track")
    ev.add_argument("--since", default=None, help="search: ISO lower time bound")
    ev.add_argument("--until", default=None, help="search: ISO upper time bound")
    ev.add_argument("--limit", type=int, default=None, help="max results")
    ev.add_argument("--json", action="store_true", help="JSON output")
    ev.set_defaults(fn=cmd_events)

    pr = sub.add_parser("promoted", help="query durable salient Bifrost msgs (kind=bifrost_msg / B2)")
    pr.add_argument("--limit", type=int, default=None)
    pr.add_argument("--since", default=None, help="ISO lower time bound")
    pr.add_argument("--until", default=None, help="ISO upper time bound")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(fn=cmd_promoted)

    cl = sub.add_parser("console-log", help="durable console events (interjection/bus_control/file_drop)")
    cl.add_argument("--limit", type=int, default=None)
    cl.add_argument("--since", default=None, help="ISO lower time bound")
    cl.add_argument("--until", default=None, help="ISO upper time bound")
    cl.add_argument("--json", action="store_true")
    cl.set_defaults(fn=cmd_console_log)

    bs = sub.add_parser("bifrost-sync", help="Bifrost pull floor: presence + unread inbox peek")
    bs.add_argument("agent_id", help="your stable agent id (e.g. cursor)")
    bs.add_argument("--limit", type=int, default=None)
    bs.add_argument("--consume", action="store_true", help="read inbox and advance cursor (ack)")
    bs.add_argument("--digest", action="store_true", help="cheap one-line-per-unread headlines (no bodies)")
    bs.add_argument("--json", action="store_true")
    bs.set_defaults(fn=cmd_bifrost_sync)

    snd = sub.add_parser("bifrost-send", help="send a message to another agent on the bus")
    snd.add_argument("agent_id", help="your stable agent id (the SENDER, e.g. claude)")
    snd.add_argument("text", nargs="+", help="the message text")
    snd.add_argument("--to", default="", help="recipient agent id (e.g. deepseek); omit with --broadcast")
    snd.add_argument("--kind", default="chat", help="chat|request|question|handoff|... (default chat)")
    snd.add_argument("--broadcast", action="store_true", help="send to ALL agents instead of one --to")
    snd.add_argument("--json", action="store_true")
    snd.set_defaults(fn=cmd_bifrost_send)

    pz = sub.add_parser("bifrost-pause", help="freeze bus auto-responders (human barge-in)")
    pz.add_argument("--reason", default=""); pz.add_argument("--by", default="user")
    pz.add_argument("--json", action="store_true")
    pz.set_defaults(fn=cmd_bifrost_pause)

    rz = sub.add_parser("bifrost-resume", help="un-freeze bus auto-responders")
    rz.set_defaults(fn=cmd_bifrost_resume)

    ndg = sub.add_parser("bifrost-nudge", help="targeted fidelity signal to ONE peer (interrupt|steer|inform)")
    ndg.add_argument("agent_id", help="your stable agent id (the sender, e.g. claude)")
    ndg.add_argument("text", nargs="+", help="what you need the peer to look at / adopt")
    ndg.add_argument("--to", default="", help="the ONE peer to signal (e.g. deepseek)")
    ndg.add_argument("--mode", default="interrupt",
                     help="interrupt (hard, default) | steer (soft, fold into current task) | inform (ambient)")
    ndg.add_argument("--json", action="store_true")
    ndg.set_defaults(fn=cmd_bifrost_nudge)

    lk = sub.add_parser("lock", help="claim an advisory path-lock (C2)")
    lk.add_argument("agent_id"); lk.add_argument("path")
    lk.add_argument("--ttl", type=int, default=None); lk.add_argument("--json", action="store_true")
    lk.set_defaults(fn=cmd_lock)

    ul = sub.add_parser("unlock", help="release your advisory path-lock")
    ul.add_argument("agent_id"); ul.add_argument("path")
    ul.set_defaults(fn=cmd_unlock)

    lks = sub.add_parser("locks", help="show who holds which advisory path-locks")
    lks.add_argument("agent_id", nargs="?", default=""); lks.add_argument("--json", action="store_true")
    lks.set_defaults(fn=cmd_locks)

    return p


def main():
    p = build_parser()
    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
