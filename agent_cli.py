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
  * ASCII only: safe on the Windows console (cp1252).
  * Robust at the seam: partial / empty / None / huge inputs are sanitized, not fatal.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # make `core`/`agent` importable

_MAX = 4000   # clamp absurdly long fields an agent might paste


def _clip(s, n=_MAX):
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")   # clip on a word boundary, not mid-word
    return (cut or s[:n]) + " ...[truncated]"


# --------------------------------------------------------------------------- boot
def cmd_boot(args):
    from agent.initializer import derive_agent_context_from_startup_sources
    res = derive_agent_context_from_startup_sources(args.agent_id, args.task, verbose=False)
    ctx = res.get("context") or {}
    # Auto-logger (Slice 2): record that this agent booted (raw, full-fidelity). Best-effort.
    try:
        from core.events.event_log import capture_event
        capture_event("boot", f"{args.agent_id} booted" + (f" -- task: {args.task}" if args.task else ""),
                      agent_id=args.agent_id,
                      detail={"task": args.task, "status": res.get("status"),
                              "approx_tokens": ctx.get("approx_tokens")})
    except Exception:
        pass
    if args.json:
        print(json.dumps({"status": res.get("status"), "context": ctx}, indent=2, default=str))
        return 0 if res.get("status") == "success" else 1

    sk = (ctx.get("skeleton") or "").strip()
    secs = ctx.get("sections") or {}
    print(f"# CONTEXT for {args.agent_id}" + (f" -- task: {args.task}" if args.task else ""))
    print(f"# {len(secs.get('learnings', []))} lesson(s), "
          f"{len(secs.get('blockers', []))} blocker(s), "
          f"~{ctx.get('approx_tokens', 0)}/{ctx.get('token_budget', 0)} tokens "
          f"(within budget: {ctx.get('within_budget')})")
    print("#" + "-" * 60)
    print("## LESSONS / CONTEXT (most relevant first)")
    print(sk if sk else "  (none yet -- you are the first agent to contribute)")
    blockers = secs.get("blockers", [])
    if blockers:
        print("\n## ACTIVE BLOCKERS")
        for b in blockers[:5]:
            print(f"  [{b.get('severity', '?')}] {_clip(b.get('description', ''), 120)}")
    print("\n## TO CONTRIBUTE A LESSON, run:")
    print(f'  py agent_cli.py learn {args.agent_id} --experiment NAME '
          f'--tried "..." --result "..." --recommend "..."')
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
    }
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
    return 0 if ok else 1


# ------------------------------------------------------------------------- recall
def cmd_recall(args):
    """Search lessons by keyword; with no query, list ALL lessons."""
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
        print(f"  - [{h.get('category', '?')}] {h.get('experiment_name', '?')}: {_clip(rec, 160)}")
    return 0


# --------------------------------------------------------------------------- list
def cmd_list(args):
    """Alias for recall with no query -- show everything in memory."""
    args.query = ""
    return cmd_recall(args)


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


def main():
    p = argparse.ArgumentParser(prog="agent_cli.py", description="Agent door to the AI-Setup system.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("boot", help="print an agent's startup context")
    b.add_argument("agent_id"); b.add_argument("--task", default=None); b.add_argument("--json", action="store_true")
    b.set_defaults(fn=cmd_boot)

    l = sub.add_parser("learn", help="record a lesson")
    l.add_argument("agent_id"); l.add_argument("--experiment", required=True)
    l.add_argument("--tried", default=""); l.add_argument("--result", default="")
    l.add_argument("--expected", default=""); l.add_argument("--recommend", default="")
    l.add_argument("--category", default=""); l.add_argument("--success", default=None)
    l.add_argument("--confidence", default=None); l.add_argument("--json", action="store_true")
    l.set_defaults(fn=cmd_learn)

    r = sub.add_parser("recall", help="search past lessons (no query = list all)")
    r.add_argument("query", nargs="?", default=""); r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_recall)

    li = sub.add_parser("list", help="list ALL lessons in memory")
    li.add_argument("--json", action="store_true")
    li.set_defaults(fn=cmd_list)

    s = sub.add_parser("status", help="honest system status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    lg = sub.add_parser("log", help="record an arbitrary narrative Beat")
    lg.add_argument("kind", nargs="?", default="note", help="beat kind (session/note/commit/learning/...)")
    lg.add_argument("--summary", default="", help="summary of what happened")
    lg.add_argument("--source", default="", help="source identifier (who:action)")
    lg.add_argument("--category", default="", help="route hint category")
    lg.add_argument("--task", default="", help="route hint task")
    lg.add_argument("--json", action="store_true", help="JSON output")
    lg.set_defaults(fn=cmd_log)

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

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
