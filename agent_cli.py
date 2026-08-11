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
import re
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

# T119 (one clock, G5): every rendered timestamp goes through THE display door and names
# its frame (Z / local tz label) -- a bare truncated ISO masquerading as local time was
# the defect class. Imported module-level: several commands render times.
from core.foundation.timeutil import render_iso

_MAX = 4000   # clamp absurdly long fields an agent might paste


def _clip(s, n=_MAX):
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")   # clip on a word boundary, not mid-word
    return (cut or s[:n]) + " ...[truncated]"


_MAX_NOTE = 100_000   # durable note bodies: a ceiling against runaway pastes, not a working size


_LEARN_PROTOCOL_COLLAPSE = re.compile(
    r"</(?:tried|result|recommend|expected)>\s*"
    r"<parameter\s+name\s*=\s*(['\"])(?:tried|result|recommend|expected)\1\s*>",
    re.IGNORECASE,
)


def _collapsed_learn_fields(fields):
    """Name lesson fields that contain a serialized boundary into another field.

    This is deliberately narrower than rejecting protocol-looking prose. A single
    literal ``<parameter name="result">`` can be legitimate evidence; the corrupt
    live shape was a field-closing tag immediately followed by the next serialized
    parameter, proving that multiple tool arguments collapsed into one value.
    """
    return [
        name for name, value in fields.items()
        if _LEARN_PROTOCOL_COLLAPSE.search("" if value is None else str(value))
    ]


def _intake(s, n, field, confessions):
    """Bound a value about to be STORED -- and CONFESS when the bound bites.

    RB-5 class (docs/library/design/20260711_rb-23-content-floor-reconciled-build-spe_d47764.md, incident record): a silent clip at a
    storage door corrupts durable knowledge while the caller is told [OK] -- deepseek's
    knowledge_note tool-arg lost the tail of a design twice on 2026-07-11 exactly this way
    (stored ~4013 chars, tool result confessed nothing). Over-cap input is hard-sliced with
    an IN-BAND marker in the stored text AND a confession line the door must print in its
    RESULT, so the calling agent SEES the clip and can chunk/resend. `_clip` stays for
    display projections; storage intake of content fields uses THIS. Identity-scale fields
    (titles, ids, categories) keep `_clip` -- they self-match on the clipped form."""
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    # T064: the remainder is never destroyed -- the FULL original spills to a file
    # that BOTH sides can follow (the confession points the writer, the in-band
    # marker points the reader). Spill failure degrades to the old honest
    # confession: the door must never die because a disk write failed.
    spill_name = None
    try:
        import hashlib
        import time as _time
        spill_dir = os.getenv("AKASHIC_SPILL_DIR") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "state", "spill")
        os.makedirs(spill_dir, exist_ok=True)
        spill_name = (f"{field}-{_time.strftime('%Y%m%d-%H%M%S')}-"
                      f"{hashlib.sha256(s.encode('utf-8', 'replace')).hexdigest()[:8]}.txt")
        with open(os.path.join(spill_dir, spill_name), "w", encoding="utf-8") as f:
            f.write(s)
    except Exception:
        spill_name = None
    if spill_name:
        confessions.append(
            f"[CLIPPED] {field}: {len(s)} chars exceeds the {n}-char cap -- stored the "
            f"first {n}; FULL original spilled to state/spill/{spill_name}")
        return s[:n] + f"\n...[clipped at {n} of {len(s)} chars -- full text: state/spill/{spill_name}]"
    confessions.append(f"[CLIPPED] {field}: {len(s)} chars exceeds the {n}-char cap -- "
                       f"stored the first {n} plus an in-band marker; resend the remainder in chunks")
    return s[:n] + f"\n...[clipped at {n} of {len(s)} chars -- remainder NOT stored]"


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
        # C7-4: an MCP stdio server owns stdin as its JSON-RPC transport.  A child that
        # inherits that handle makes Windows' Proactor writer defer the pending tool
        # response until another inbound frame arrives.  stdout/stderr already use fresh
        # pipes via capture_output; sever stdin explicitly as well.
        return subprocess.run(["git", *a], cwd=root, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, close_fds=True)

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
                "summary": ", ".join(d[3:] for d in dirty[:6]), "lines": dirty}
    except Exception:
        return {"ok": False, "dirty": 0, "ahead": 0, "branch": "", "summary": ""}


def _bucket_tree(porcelain_lines: list) -> dict:
    """W35/B5: partition `git status --porcelain` lines into what a seat can act on
    SAFELY -- modified-tracked (possibly a sibling's mid-flight lane) vs untracked
    (usually your own artifacts), plus a top-level-dir histogram (~free, kimi Q4)."""
    modified = untracked = 0
    dirs: dict = {}
    for ln in porcelain_lines:
        code, _, path = str(ln).partition(" ") if str(ln).startswith("??") \
            else (str(ln)[:2], "", str(ln)[3:])
        path = path.strip().strip('"')
        if str(ln).startswith("??"):
            untracked += 1
        else:
            modified += 1
        top = path.replace("\\", "/").split("/", 1)[0] if path else "?"
        dirs[top] = dirs.get(top, 0) + 1
    return {"modified": modified, "untracked": untracked, "dirs": dirs}


def _warn_unmirrored(soft=False, status=None):
    """Tell the agent if it has uncommitted/unpushed work -- BUCKETED (W35/B5, kimi Q4:
    the harm was the unqualified `run mirror.py` imperative printed over a SIBLING's
    mid-flight edits; the sweep imperative is dead). `soft` = boot heads-up; loud =
    session-end nag. Returns True if it warned; silent on clean/unavailable git.
    `status` injectable for tests."""
    s = status if status is not None else _working_tree_status()
    if not s.get("ok") or (s["dirty"] == 0 and s["ahead"] == 0):
        return False
    b = _bucket_tree(s.get("lines") or [])
    top = ", ".join(f"{d} {n}" for d, n in
                    sorted(b["dirs"].items(), key=lambda kv: -kv[1])[:5])
    bits = []
    if s["dirty"]:
        bits.append(f"{b['modified']} modified (tracked), {b['untracked']} untracked")
    if s["ahead"]:
        bits.append(f"{s['ahead']} unpushed commit(s)")
    label = "; ".join(bits) + (f" | top dirs: {top}" if top else "")
    if soft:
        print(f"\n[i] Unmirrored: {label}\n"
              "    Safe default: commit YOUR OWN lane's files BY NAME; modified-tracked "
              "files may be a sibling's mid-flight work (check `task list` claims).\n"
              "    NEW loose research/**.md does NOT persist by committing it -- rule-13 has "
              "REFUSED that since the P3 flip (2026-07-23). Bring it through the door:\n"
              "      py agent_cli.py doc adopt <path>   (mints an atom; leaves your file alone)")
        return True
    print(f"\n[!] UNMIRRORED WORK: {label} -- a slice isn't done until it's mirrored.")
    if s.get("summary"):
        print(f"    changed: {s['summary']}" + (" ..." if s["dirty"] > 6 else ""))
    print('    Run:  py scripts/mirror.py "<msg>" <explicit paths>  (commit+push, YOUR '
          "files only -- never a sweep over a sibling's lane), then  "
          "py scripts/ops/snapshot_knowledge.py snapshot")
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
    # W09 (kimi F2): print the ARMED line so downstream silence reads as CALIBRATED (the surface
    # is live, nothing was relevant), never as a suspected-dead hook (kimi mis-diagnosed absence).
    try:
        from core.recall.at_action import warm_cache, prune_state
        _warm_n = warm_cache(); prune_state()
        print(_recall_armed_line(_warm_n))
    except Exception:
        print(_recall_armed_line(None))
    # T258: a resident boots knowing WHO IT IS and WHY. Front-loaded deliberately -- kimi's
    # provenance-laundering objection was that a callsign asserts an archive the boot may not
    # carry, measured at 0/8 receipts present before this landed. Silent for a non-resident:
    # most seats have no designation and that is not a warning.
    try:
        from core.fleet import residents as _res
        _who = _res.boot_block(args.agent_id)
        if _who:
            print(_who)
    except Exception:
        pass                      # identity is orientation, never a reason a boot fails
    # T133: GHOST MAIL RECONCILES ITSELF, on the same terms as the heal below -- cheap no-op when
    # nothing is due, real work only on drift, silent unless something moved. Ghost mail RECURS by
    # construction (the index ingests on read, so it grows as it is queried and each growth can
    # surface more mail from ended sessions: deepseek was clean at 22:00 and had 46 again by
    # morning). The alternative is a human catch-up ritual, and a reproducible defect is a trigger
    # to fix rather than to normalise. Cadence-bounded because the scan is O(entries) and boot is
    # on the hot path for every session.
    try:
        from core.comm import mailbox as _mbx
        _g = _mbx.maybe_retire_ghosts(os.environ.get("BIFROST_NAMESPACE", "bifrost"),
                                      args.agent_id)
        if _g.get("retired"):
            print(f"# mail: declined {_g['retired']} message(s) from retired seats "
                  f"(they stay readable; they stop competing with live work)")
        if _g.get("truncated"):
            print(f"# mail: {_g['unscanned']} entr(ies) beyond the sweep cap were NOT examined")
    except Exception:
        pass                      # boot must never fail on mail hygiene
    # Cold-start safety net (ported from the retired StoreReconciler): if Redis was down during past
    # writes, the durable File is ahead -- backfill Redis so recall/state read consistent values. Best-
    # effort; only reconciles when drift is actually found (a no-op fast path when the backends are in sync).
    # RB-25 Drill 2 (H2b): heal_report() surfaces BOTH the File->Redis backfill AND any Redis-only
    # orphan gap the unidirectional reconciler leaves behind -- boot was silent about the latter.
    try:
        from core.foundation.store import create_store, HybridStore
        _st = create_store(prefer_redis=True)
        if isinstance(_st, HybridStore) and _st.redis_available:
            # W64: heal STILL RUNS here (the backfill is a correctness step that must
            # precede any read) -- only the RENDER folds.
            for _line in _heal_render(_st.heal_report(),
                                      verbose=bool(os.environ.get("AKASHIC_HEAL_VERBOSE"))):
                print(f"[boot] {_line}", file=sys.stderr)
    except Exception:
        pass
    if args.json:
        print(json.dumps({"status": res.get("status"), "context": ctx, "bifrost": bifrost},
                         indent=2, default=str))
        return 0 if res.get("status") == "success" else 1

    sk = (ctx.get("skeleton") or "").strip()
    secs = ctx.get("sections") or {}
    if getattr(args, "sources_json", None):   # T081-W6: sidecar of normalized lesson sources (best-effort)
        try:
            with open(args.sources_json, "w", encoding="utf-8") as _sf:
                json.dump({"sources": _boot_source_list(secs)}, _sf)
        except Exception:
            pass
    print(f"# CONTEXT for {args.agent_id}" + (f" -- task: {args.task}" if args.task else ""))
    print(f"# {len(secs.get('learnings', []))} lesson(s), {len(secs.get('blockers', []))} blocker(s)")
    print(_transport_line())   # T081-W1: what door this seat came through (can I use tools?)
    # P2/T022 ORIENTATION HEADER (deepseek consumer spec, research/reviewed/deepseek-p2-spec-
    # 2026-07-09.md): the first ~15 lines carry the map, the governing arc, THE current
    # where-we-are, the precedence doctrine, and a COMPACT ledger bar -- every line DERIVED
    # from live state (renew_arch_slice_orientation: projections, never prose that rots).
    # The stateless peer folds only boot's head into its system prompt; this head is for it.
    _pa = _primer_aware()
    if _pa:
        # W13: the dedup is SAID, never silent (the packet law) -- and reversible.
        print("# (primer-aware boot: funnel/draft/mail/delta ride the SessionStart whisper "
              "-- W13; AKASHIC_BOOT_FULL=1 for the legacy full boot)")
    print(_orientation_header(args.agent_id, primer_aware=_pa))
    print("#" + "-" * 60)
    print("## LESSONS / CONTEXT (most relevant first)")
    print(sk if sk else "  (none yet -- you are the first agent to contribute)")
    try:   # ARCH SLICE (RENEW Strand E gap #2 / deferred step #3): orient the agent to the code
        # region of THIS task -- a stable projection over docs/ARCHITECTURE.md, show-nothing when the
        # task matches no subsystem. Both doors get it (MCP boot delegates to cmd_boot). Fail-open.
        from core.context.arch_loader import load_arch_slice
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
        # away via the pointer below. See docs/library/report/20260707_renew-strand-e-cold-resume-fidelity-empi_890e10.md.
        from core.learning.agent_memory import get_agent_memory
        notes = get_agent_memory().get_decisions(days=60)
        if _pa:
            # R16: the primer-aware head already carries the FULL where-we-are body --
            # in-boot duplication is the same disease as whisper/boot duplication.
            notes = [d for d in notes if d.title != "where-we-are"]
        if notes:
            print("\n## RECENT NOTES (durable project memory)")
            _budgets = [900, 500, 500, 220, 220, 220]   # by recency: resume-anchor first, then taper
            shown = notes[:len(_budgets)]
            for d, budget in zip(shown, _budgets):
                print(f"  [{d.created_at[:10]}] {d.title}: {_clip(d.decision, budget)}")
            if len(notes) > len(shown) or any(len(d.decision or "") > b for d, b in zip(shown, _budgets)):
                # M1 (kimi seat-zero counter): the verb shipped, the teaching text must
                # retire the old dance in the same breath -- one hop, no JSON pipe.
                print("  (clipped; ONE full body: py agent_cli.py note <you> --get <title>)")
        else:
            # RB-12 [GAP]: zero notes, empty store -- no crash, no wrong line
            print("\n## RECENT NOTES (durable project memory)")
            print("  [GAP] (no durable notes yet)")
    except Exception:
        pass
    try:   # P7 (T027, deepseek C3): the durable decision trail, compact, each with a drill
        # pointer + ack state -- promoted-and-forgotten stops being invisible at boot.
        # RB-5: pages + thresholds through the same seams as the promoted CLI verb, so
        # boot and CLI can never disagree; a full page confesses the older records.
        import time as _t2
        from core.comm.promoter import promoted_page, unhandled_threshold_hours
        evs, more = promoted_page(limit=5, with_acks=True, now=_t2.time(),
                                  unhandled_hours=unhandled_threshold_hours())
        if evs:
            print("\n## RECENT DECISIONS (durable salient bus -- drill: events --get <ref>)")
            for e in evs:
                d = e.get("detail") or {}
                mark = ("UNHANDLED" if e.get("unhandled")
                        else ("acked:" + ",".join(a["by"] for a in e.get("acks", []))
                              if e.get("acks") else ""))
                print(f"  [{d.get('kind','?')}{' ' + mark if mark else ''}] "
                      f"{d.get('frm','?')} -> {d.get('to','?')}: "
                      f"{_clip(str(d.get('content','')), 110)}")
            if more:
                print("  (+ older salient records beyond this page -- py agent_cli.py promoted)")
    except Exception:
        pass
    if not _pa:   # W13: the whisper carries the funnel pulse for harness sessions
        try:   # T3: one-line funnel pulse -- watch the loop's trend without a separate command
            from core.recall.funnel import snapshot, summary_line
            print("\n## FUNNEL (recall value -- full: py agent_cli.py stats --days 7)")
            print("  " + summary_line(snapshot(hours=7 * 24)))
        except Exception:
            pass
    try:   # METHOD DRIFT (2026-07-27): the one method number on a channel with proven
        # readership. SILENT while compliant -- deepseek's trigger-selectivity rule; an
        # "all good" line every session is furniture, and furniture is how the message that
        # mattered gets skimmed. Silence here means nothing drifted, never nothing was checked.
        from core.coord.method_drift import boot_line as _mdrift
        _ml = _mdrift()
        if _ml:
            print(f"\n## METHOD\n  {_ml}")
    except Exception:
        pass
    try:   # L2 (T030): the doctor's one-liner -- progress, not presence; findings drill
        # via `py agent_cli.py doctor`. Fail-open like every boot section.
        from core.comm.doctor import examine_fleet
        rep = examine_fleet()
        line = rep["summary"]
        pages = rep.get("pages") or []
        banners = [f for f in rep["findings"] if f["grade"] == "banner"]
        print("\n## DOCTOR (fleet liveness -- full: py agent_cli.py doctor)")
        print("  " + line)
        for f in (pages + banners)[:4]:
            print(f"  !! {f['line']}")
    except Exception:
        pass
    if not _pa:   # W13: the whisper carries the draft pointer for harness sessions
        try:   # auto-captured last-session draft (SessionEnd/PreCompact) -- a trail if the last end was abrupt
            import time as _t
            dp = last_session_draft_path()
            if os.path.isfile(dp) and (_t.time() - os.path.getmtime(dp)) < 2 * 86400:
                print(f"\n## LAST-SESSION DRAFT (auto-captured) -> {dp}")
                print("   review it; promote with: py agent_cli.py wrap --commit")
        except Exception:
            pass
    if not _pa:   # R14: the unread peek rides the whisper's mail count; locks stay below
        print_boot_bifrost_section(bifrost)
    print_boot_locks_section(bifrost, args.agent_id)
    print("\n## TO CONTRIBUTE A LESSON, run:")
    print(f'  py agent_cli.py learn {args.agent_id} --experiment NAME '
          f'--tried "..." --result "..." --recommend "..."')
    print("\n## BIFROST (live + durable)")
    print("  py agent_cli.py bifrost-sync <agent>     # peek unread (same as boot section)")
    print("  py agent_cli.py promoted [--limit N]       # durable salient msgs (kind=bifrost_msg)")
    # T052 delta door: render what moved since this agent's last boot, then stamp the
    # seen mark AFTER the full context above was delivered (mark-lag contract, D1 ruling
    # -- a crash before this line leaves the old mark and the whole gap redelivers).
    # W13/R15: a primer-aware boot renders NO delta, so it advances NO mark (a mark
    # moves only when content was delivered) -- `delta <agent>` stays addressable
    # after boot, which also closes T062's self-defeating pointer on this path.
    if not _pa:
        try:
            from agent.harness.delta import delta_boot_block
            _dtext, _dcommit = delta_boot_block(args.agent_id)
            if _dtext:
                print("\n## DELTA (what moved since your last boot -- T052)")
                print(_dtext)
            _dcommit()
        except Exception:
            pass
    _warn_unmirrored(soft=True)   # heads-up if you're resuming on top of unmirrored work
    if not os.getenv("AKASHIC_AGENT_ID"):
        print("\n[i] AKASHIC_AGENT_ID not set -- peer-lock enforcement (C2/C4) is degraded: "
              "edits/commits to a peer-locked path fail CLOSED until it's set. Set it per agent "
              "(e.g. .claude/settings.json env).")
    return 0 if res.get("status") == "success" else 1


# -------------------------------------------------------------------------- delta (T052)
def cmd_delta(args):
    """The delta door (T052/R1): what moved since this agent's last boot. --ack advances
    the seen mark to current positions (the explicit commit surface; boot auto-commits)."""
    from agent.harness.delta import render_full, delta_boot_block
    print(render_full(args.agent_id))
    if getattr(args, "ack", False):
        _t, commit = delta_boot_block(args.agent_id)
        print("[delta] mark advanced to current positions" if commit()
              else "[delta] mark write failed (redis unreachable?)")
    return 0


# -------------------------------------------------------------------------- learn
def cmd_learn(args):
    from core.learning.learning_store import get_learning_store

    # T253: a REPEAT is evidence ABOUT an existing lesson, not a new one. It lands here rather
    # than behind its own verb because this is the door already reached for at the moment of
    # "I just learned something" -- and the moment you notice a repeat is exactly that moment.
    # A write door must OFFER a field or it stays empty: the anti-pattern surface sat at zero
    # for months because no flag exposed it, not because nobody had one to record.
    if getattr(args, "repeat_of", None):
        try:
            rec = get_learning_store().record_repeat(
                of=args.repeat_of, agent_id=args.agent_id,
                what=(args.tried or args.result or ""),
                recall_outcome=getattr(args, "recall_outcome", "") or "")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        hrs = rec["elapsed_s"] / 3600.0
        print(f"[repeat] '{rec['of']}' violated again after {hrs:.1f}h"
              + (f" (recall: {rec['recall_outcome']})" if rec["recall_outcome"] else ""))
        print("  a FLOOR, not a rate -- this counts only what someone noticed. "
              "See `py agent_cli.py stats`.")
        return 0

    if not args.experiment or not (args.tried or args.result):
        print("ERROR: need --experiment and at least one of --tried/--result.")
        print('Example: py agent_cli.py learn me --experiment cache_fix '
              '--tried "memoize" --result "+50%" --recommend "use it"')
        return 2
    raw_fields = {
        "what_tried": args.tried,
        "actual_outcome": args.result,
        "expected_outcome": args.expected,
        "recommendation": args.recommend,
    }
    collapsed = _collapsed_learn_fields(raw_fields)
    if collapsed:
        print("ERROR: learn refused collapsed tool-protocol fields in "
              f"{', '.join(collapsed)}; no lesson was written.")
        print("Re-send tried, result, expected, and recommend as separate arguments.")
        return 2
    clipped = []
    signal = {
        "experiment_name": _clip(args.experiment, 200),
        "agent_id": _clip(args.agent_id, 200),
        "what_tried": _intake(args.tried, _MAX, "what_tried", clipped),
        "actual_outcome": _intake(args.result, _MAX, "actual_outcome", clipped),
        "expected_outcome": _intake(args.expected, _MAX, "expected_outcome", clipped),
        "recommendation": _intake(args.recommend, _MAX, "recommendation", clipped),
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
    edge_stamped = False
    if ok and related:
        try:   # durable edge for the consolidation/merge pass -- the advisory print alone evaporated
            edge_stamped = get_learning_store().mark_related(signal["experiment_name"], related)
        except Exception:
            edge_stamped = False
    if args.json:
        print(json.dumps({"recorded": bool(ok), "experiment": signal["experiment_name"],
                          "clipped": clipped or None}))
    else:
        print(f"[{'OK' if ok else 'FAIL'}] recorded lesson '{signal['experiment_name']}' "
              f"(category: {signal['category']}, success: {signal['success']})")
        for c in clipped:   # RB-5: the door's RESULT carries the clip, never silent
            print(c)
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
        # honest suffix: only claim the stamp when mark_related actually returned True
        # (DeepSeek review finding 3 -- a silent store failure must not present as success)
        edge_note = " Edge stamped on this record (related_to)." if edge_stamped \
            else " (edge NOT stamped -- store write failed; the console line is the only record)."
        if top["dims"] >= 4:
            print(f"[i] near-duplicate: overlaps '{top['experiment_name']}' on {top['dims']}/5 dimensions"
                  f" ({', '.join(top['matched'])}).")
            print(f"    Next time update it instead: re-record with --experiment {top['experiment_name']}"
                  f" (same name = update, no dupes).{edge_note}")
        else:
            print(f"[i] related lesson: '{top['experiment_name']}' ({top['dims']}/5 dims)"
                  f" -- consolidation-pass candidate.{edge_note}")
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
        # Anchor review: does this lesson's premise still hold? Advisory only -- it never
        # retires, demotes or hides anything, and it says UNCHECKED rather than "clean" when
        # it cannot tell. Read verb only, deliberately not on the recall hot path in v1.
        # Spec: docs/library/design/20260725_lesson-decay-reconciled-design_194ab2.md
        try:
            from core.recall import anchors
            print(f"  {anchors.review(rec).banner}")
        except Exception:
            pass          # a resolver fault must never break the record it annotates
        return 0
    from core.learning.learning_store import get_learning_store
    ls = get_learning_store()
    query = (args.query or "").strip()
    scope_agent = getattr(args, "agent", None)
    try:
        if not query:
            hits = ls.load_all_learnings_from_store()
            # T260: the no-query listing honors the scope too -- "everything Navi has learned"
            # is a legitimate read of one archive, filtered on the same normalized author.
            if scope_agent:
                want = str(scope_agent).strip().lower()
                hits = [h for h in hits
                        if str(h.get("agent_id") or h.get("agent") or "").strip().lower() == want]
        else:
            hits = ls.search_learnings_by_keyword(_clip(query, 200), agent=scope_agent)
    except Exception as e:
        print(f"ERROR searching: {type(e).__name__}: {e}")
        return 1
    if args.json:
        print(json.dumps(hits, indent=2, default=str))
        return 0
    label = "all lessons" if not query else f"lesson(s) matching '{query}'"
    print(f"# {len(hits)} {label}")
    # T120 F2 (deepseek): exact-title-miss flag — when the query looks like a title
    # (underscore-separated, colon-prefixed, or slug-shaped) and no hit's experiment_name
    # matches it exactly, confess the miss instead of letting the runner assume the top
    # results include the thing it named.
    if query:
        import re as _re
        from core.recall.at_action import TITLE_SHAPED_RE
        _looks_like_title = bool(_re.match(TITLE_SHAPED_RE, query.strip(), _re.IGNORECASE))
        if _looks_like_title:
            _q_lower = query.strip().lower()
            _exact = any(
                str(h.get("experiment_name", "")).lower() == _q_lower
                or str(h.get("source", "")).lower() == _q_lower
                for h in hits)
            if not _exact:
                print(f"  [title-miss] '{query}' not found by exact title in these "
                      f"results — it may exist under a different spelling, or in the "
                      f"full corpus; try knowledge_full(source=\"<source>\") if you "
                      f"have the source pointer, or recall without quotes to broaden")
    for h in hits[:25]:
        rec = h.get("recommendation") or h.get("actual") or h.get("what_tried", "")
        # [graduated] = rule now enforced by automation (see `graduate`); [benched] = curator
        # retired it for surfaced-never-credited (reversible; see `recall-curate`). Both keep
        # history, both are excluded from recall surfacing -- the tag says WHY.
        flag = " [graduated]" if str(h.get("graduated") or "").strip() else \
               (" [benched]" if str(h.get("benched") or "").strip() else "")
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
    small models (docs/library/design/20260709_fleet-dispatch-an-intelligent-easy-struc_303d15.md). Actions:
      list   -- the roster (status / capabilities / disqualifier); --probe adds live Ollama availability
      select -- pick the best model for a capability + constraints (what to RUN right now)
      call   -- run a bounded subtask on one model and print its output (also the manual smoke test)
    Reads are fail-soft; a failed call surfaces the error, never a silent empty string."""
    from core.fleet import model_roster
    action = args.action or "list"
    if action == "list":
        rows = model_roster.models(status=args.status, capability=args.capability)
        probe = model_roster.probe_availability() if args.probe else None
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
        pick = model_roster.select(args.capability, status=(args.status or "active"),
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
    docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md). An honest 'unavailable' beats a pretended capability -- plan
    around what your runtime does, not what you wish it did."""
    from agent.harness.registry import HARNESSES, TIERS, supported
    if args.json:
        print(json.dumps({"tiers": list(TIERS), "harnesses": HARNESSES}, indent=2))
        return 0
    print("# INTEGRATION TIERS  (T0 door .. T6 close; the story: docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md)")
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
def _family_gauge_render(g):
    """W54: one-line render of injections_by_family -- conductor first (the stance family is the
    reason the gauge exists), then the busiest others. '1/35' = injections carrying that family
    over all injections in the window."""
    total = int(g.get("total", 0) or 0)
    fams = dict(g.get("families") or {})
    rest = sorted(((f, n) for f, n in fams.items() if f != "conductor"),
                  key=lambda kv: (-kv[1], kv[0]))[:5]
    parts = [f"conductor {int(fams.get('conductor', 0))}/{total}"]
    parts += [f"{f} {n}/{total}" for f, n in rest]
    return " · ".join(parts)


def cmd_audit(args):
    """Belief-vs-state audit (kimi charter 2026-07-23, deepseek build, claude verb wiring):
    cross-read durable beliefs against ground-truth projections, print labeled rows
    (MATCH/DRIFT/UNKNOWN + which rule fired + drill detail). Read-only, computes live,
    caches nothing -- the auditor never becomes a surface that itself drifts. v1 domain:
    VERBS (registry <-> parser). Direction-neutral: --ground flips WORDING only, never
    a verdict."""
    from core.toolbelt import audit as _audit
    domains = None
    if getattr(args, "domain", None):
        wanted = {d.strip().upper() for d in args.domain.split(",") if d.strip()}
        domains = [d for d in _audit.DOMAINS if d.name.upper() in wanted]
        if not domains:
            known = ", ".join(d.name for d in _audit.DOMAINS)
            print(f"[audit] unknown domain(s) {sorted(wanted)} -- available: {known}")
            return
    if args.json:
        print(json.dumps(_audit.json_result(domains=domains,
                                            ground_truth_source=args.ground), indent=2))
    else:
        print(_audit.render(domains=domains, ground_truth_source=args.ground))


def cmd_injections(args):
    """The injection ledger: everything recall PUSHED into agent contexts recently -- when,
    at which altitude (action/plan), for which target, which lessons, and what it cost.
    Injected context must never be hidden state; this is the inspection window."""
    from core.recall.at_action import recent_injections, injections_by_family
    hours = float(args.hours or 24)
    inj = recent_injections(hours)
    fam = injections_by_family(hours, injections=inj)
    if args.json:
        print(json.dumps({"window_hours": hours, "count": len(inj),
                          "tokens_approx": sum(int(i.get("chars", 0)) for i in inj) // 4,
                          "by_family": fam["families"],
                          "injections": inj}, indent=2))
        return 0
    print(f"# INJECTION LEDGER  (last {hours:g}h: {len(inj)} injection(s), "
          f"~{sum(int(i.get('chars', 0)) for i in inj) // 4} tokens pushed)")
    print(f"  by family (W54 activation gauge): {_family_gauge_render(fam)}")
    if not inj:
        print("  (none -- either quiet, or nothing cleared the relevance floor)")
        return 0
    for i in inj[-25:]:
        when = render_iso(float(i.get("at", 0)), tz="local")   # T119: labeled, no bare local clock
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
            import sys as _sys, os as _os
            _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "scripts"))
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


def cmd_compare(args):
    """compare -- what does one domain have that another does not (T213).

    The operation four of our guards each hand-rolled (door parity, wiring, the suite
    baseline, unmapped kinds). Refuses to compare different KINDS of key, and marks a
    result UNRELIABLE when either side was incompletely collected -- because every
    uncollected element of the short side surfaces as a false finding on the other.
    """
    from core.coord import compare as cmp_mod
    # Domains that register themselves on import must actually BE imported, or they are
    # invisible at the door -- the built-not-wired class that blocked two commits
    # tonight. Imported here rather than from compare.py, which terms.py imports.
    from core.coord import terms as _terms_domain   # noqa: F401  (registers on import)

    if getattr(args, "list", False) or not args.a:
        print("# comparable domains (only like key-types may be diffed)")
        for name, (_fn, kt) in sorted(cmp_mod.DOMAINS.items()):
            print(f"  {name:<18} keys: {kt}")
        return 0

    r = cmp_mod.run(args.a, args.b)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, default=str))
        return 0
    if not r["ok"]:
        print(f"REFUSED: {r['why']}", file=sys.stderr)
        return 2

    a, b = r["a"], r["b"]
    print(f"# {a['name']} ({a['n']}) vs {b['name']} ({b['n']})  keys={r['key_type']}")
    if not r["reliable"]:
        print(f"  UNRELIABLE: {r['why']}", file=sys.stderr)
    for label, side, other in (("only in", "only_a", a), ("only in", "only_b", b)):
        rows = r[side]
        who = a["name"] if side == "only_a" else b["name"]
        print(f"\n{label} {who} ({len(rows)}):")
        for k in rows[: int(args.limit or 40)]:
            print(f"    {k}")
        if len(rows) > int(args.limit or 40):
            print(f"    ... {len(rows) - int(args.limit or 40)} more")
    print(f"\nin both: {len(r['both'])}")
    for name, why in (a.get("failed") or {}).items():
        print(f"  {a['name']} FAILED [{name}]: {why}", file=sys.stderr)
    for name, why in (b.get("failed") or {}).items():
        print(f"  {b['name']} FAILED [{name}]: {why}", file=sys.stderr)
    return 0


def cmd_timeline(args):
    """timeline -- one chronological view across domains (T211).

    Forensics' super timeline: you do not search for the cause, you line the domains up
    by time and it becomes visible. Built after a wake bug cost six turns because my own
    asks were manufacturing the mail I kept draining -- every fact was already recorded,
    in four domains, and nothing put them in one column.

    Coverage is printed with the rows, never separately: a merged view missing a domain
    looks exactly like a view where nothing happened in it.
    """
    import time as _t
    from core.coord import timeline as tl

    since = _t.time() - float(args.hours) * 3600.0 if args.hours else None
    r = tl.gather(since=since)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, default=str))
        return 0

    cov = r["coverage"]
    print(f"# timeline -- {cov['n']} row(s)"
          + (f" over the last {args.hours}h" if args.hours else " (all)"))
    print(f"  read: {', '.join(f'{k}={v}' for k, v in sorted(cov['counts'].items())) or 'none'}"
          + (f" | undated {cov['undated']}" if cov["undated"] else ""))
    for name, why in (cov["failed"] or {}).items():
        print(f"  NOT READ: {name} ({why}) -- contributed zero rows, which is NOT the "
              f"same as having none", file=sys.stderr)

    rows = r["rows"][-int(args.limit):] if args.limit else r["rows"]
    for row in rows:
        stamp = (_t.strftime("%m-%d %H:%M:%S", _t.localtime(row["ts"]))
                 if row["ts"] else "  ??  ??:??:??")
        print(f"  {stamp}  {row['domain']:<7} {str(row['actor'])[:12]:<12} "
              f"{str(row['kind'])[:18]:<18} {row['summary'][:60]}")
    for b in r["blind"]:
        print(f"  - {b}", file=sys.stderr)
    return 0


def cmd_discover(args):
    """The self-describing door: list every verb + its one-line purpose (the L1 skeleton). Optional
    QUERY filters by substring. Run `py agent_cli.py <verb> -h` for a verb's full arguments."""
    # T210: --semantic asks the question at the level of MEANING. The substring path
    # below is a FACT about the verb table; this is a model READING it, so the two are
    # rendered differently and never laundered into each other.
    if getattr(args, "semantic", False):
        from core.coord import capability_search
        r = capability_search.find(args.query or "")
        if args.json:
            print(json.dumps(r, ensure_ascii=False, default=str))
            return 0
        print(f"# does this system already do it?  '{args.query}'")
        print(f"  EXISTS: {r['exists']}"
              + ("" if r["confident"] else "   [NOT CONFIDENT -- do not act on this]"))
        for label, key in (("WHAT", "what"), ("GAP", "gap"),
                           ("NEAREST MISS", "nearest_miss")):
            if r.get(key):
                print(f"  {label}: {r[key]}")
        if r.get("why"):
            print(f"  why: {r['why']}", file=sys.stderr)
        spend = f"${r['usd']:.4f}" if r.get("usd") is not None else "unpriced"
        print(f"  -- a MODEL READ of the verb table + module index (not a lookup) "
              f"| {r.get('model') or '?'} | {spend}", file=sys.stderr)
        # UNKNOWN is not a "no". This tool exists because absence gets inferred; it must
        # never be the thing that infers one.
        return 0

    verbs = list_verbs(args.query)
    if args.json:
        print(json.dumps([{"verb": n, "purpose": h} for n, h in verbs], indent=2)); return 0
    q = (args.query or "").strip()
    print(f"# agent_cli.py - {len(verbs)} verb(s)" + (f" matching '{q}'" if q else "")
          + "   (run `py agent_cli.py <verb> -h` for arguments)")
    width = max((len(n) for n, _ in verbs), default=0)
    for n, h in verbs:
        print(f"  {n.ljust(width)}  {h}")
    # ZERO MATCHES IS THE MOMENT THE POINTER IS WORTH MOST, and the moment it was
    # missing: asked "check whether a test failure is pre-existing" this path returns 0
    # while `suite-baseline` sits in the list it just searched. A substring search cannot
    # match meaning, and saying so here is the difference between an honest empty result
    # and one that reads as "no such thing".
    if q and not verbs:
        print(f"\n0 matches -- but this is a SUBSTRING search and cannot match meaning. "
              f"Ask at the level of meaning before concluding it does not exist:\n"
              f"  py agent_cli.py discover --semantic \"{q}\"", file=sys.stderr)
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


# P2/T022: the four-tier conflict rule, printed verbatim in every boot head. A static
# constant IS the single source of truth here (deepseek spec sec.2 verbatim, incl. its
# ambiguity table rationale) -- it names semantics, not state, so it cannot rot with state.
PRECEDENCE_DOCTRINE = (
    "# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable\n"
    "# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats\n"
    "# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.")


def _primer_aware() -> bool:
    """T074 W13 (R13): did THIS caller already get the SessionStart whisper? A harness
    session exports its session id (runner_lock.session_holder_token is the one
    definition); a bare terminal or a runner did not, and keeps the legacy full boot.
    AKASHIC_BOOT_FULL=1 is the debugging hatch back to legacy from inside a session."""
    if os.getenv("AKASHIC_BOOT_FULL", "0") == "1":
        return False
    try:
        from core.comm.runner_lock import session_holder_token
        return bool(session_holder_token())
    except Exception:
        return False


def _boot_siblings_line(agent_id: str) -> str:
    """Sibling details for the primer-aware head ('' when solo/unreadable): the whisper
    carries the count; the boot head carries the CLAIMS -- what each incarnation holds.
    The CALLER's own incarnation is excluded (a session is not its own sibling)."""
    try:
        from core.comm.incarnation import live_incarnations
        from core.comm.runner_lock import session_holder_token
        tok = session_holder_token() or ""
        my_sid = tok.split(":", 1)[1] if ":" in tok else ""
        sibs = live_incarnations(agent_id, my_session=my_sid or None)
        if not sibs:
            return ""
        bits = []
        for s in sibs[:3]:
            sid8 = str(s.get("session_id", ""))[:8]
            age = s.get("age_min")
            idle = f"idle {age:.0f}m" if isinstance(age, (int, float)) else "age unknown"
            claims = ",".join(s.get("claims") or []) or "no claims"
            bits.append(f"{agent_id}#{sid8} ({idle}, {claims})")
        return "# siblings: " + "; ".join(bits) + "  (address one: bifrost-send --to-incarnation <sid8>)"
    except Exception:
        return ""


def _normalize_boot_source(src) -> str:
    """T081-W6 (deepseek W6-P1 convention): normalize a lesson's source pointer to ONE canonical
    form so a runner can match boot-known lessons without regex-parsing rendered text. A bare
    experiment name -> learn:experiment:NAME; a mem: namespace source -> learn:experiment:mem_...
    (colons become underscores so it matches but never collides with a real experiment); an
    already-qualified pointer passes through."""
    s = str(src or "").strip()
    if not s:
        return ""
    if s.startswith("learn:experiment:"):
        return s
    if s.startswith("mem:"):
        return "learn:experiment:mem_" + s[len("mem:"):].replace(":", "_")
    return f"learn:experiment:{s}"


def _boot_source_list(secs) -> list:
    """The de-duplicated, normalized source pointers for every lesson rendered in this boot --
    the authoritative list the W6 sidecar emits (replaces the runner's fragile regex over text)."""
    out, seen = [], set()
    for L in (secs.get("learnings") or []):
        n = _normalize_boot_source(L.get("source") if isinstance(L, dict) else "")
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _heal_render(lines, verbose: bool = False) -> list:
    """W64: keep unowned fleet drift OFF the top of a fresh seat's boot.

    heal_report() is correct and its text already says the drift is not the booting
    seat's job ([fleet-hygiene], W03) -- but it still led every boot with ~600 tokens of
    'INVESTIGATE' about 484 keys the reader is explicitly told it does not own. First
    impressions are a budget: an alarm the reader cannot act on teaches it to skim the
    banner, and the next banner that DOES matter gets skimmed too. Fold to one line;
    AKASHIC_HEAL_VERBOSE=1 restores the full render (the detail is never destroyed).
    """
    kept = [l for l in (lines or []) if str(l).strip()]
    if not kept or verbose:
        return list(kept)
    return [f"[heal][fleet-hygiene] {len(kept)} drift line(s) folded -- unowned fleet "
            f"drift, not this seat's task (AKASHIC_HEAL_VERBOSE=1 for the full render)"]


def _transport_line(door=None, detail=None) -> str:
    """T081-W1: one boot line stating THIS seat's DOOR -- 'can I use tools?' answered
    before any project context. The door is set by the invocation path: the MCP tool
    server and the runner each stamp AKASHIC_SEAT_DOOR (+ optional _DETAIL); a bare CLI
    boot leaves it unset -> cli-shell, which is exactly the P1 fragility case (native
    akashic tools NOT attached), so the line names its OWN remedy (T081-W2). An unknown
    signal degrades to cli-shell -- a wrong 'you have tools' is worse than a safe default."""
    door = (door if door is not None else os.environ.get("AKASHIC_SEAT_DOOR", "")).strip().lower()
    detail = (detail if detail is not None else os.environ.get("AKASHIC_SEAT_DOOR_DETAIL", "")).strip()
    paren = f" ({detail})" if detail else ""
    if door == "mcp":
        return f"# door: MCP-native{paren or ' (akashic tools attached)'}"
    if door == "toolbox":
        return f"# door: ToolBox-native{paren}"
    # W63: state what this process can OBSERVE, not what it assumes. A shell-out from a
    # seat that HAS the MCP door renders this exact line (it happened live 2026-07-25),
    # and asserting "tools NOT attached" sent that seat to run a remedy it did not need.
    return ("# door: CLI-shell -- this PROCESS carries no door stamp, so it cannot tell "
            "whether your SEAT has akashic tools; a shell-out from an MCP seat looks "
            "identical here. If yours are attached, ignore this line" + paren
            + ". If not: user-scoped MCP w/ absolute paths [T081-W2] or cd E:\\AI-Setup && restart")


DIRECTIVE_STALE_DAYS = 3   # W04: a directive older than this confesses its age at boot
GROUNDING_FRESH_DAYS = 7   # W37 (kimi (b)): the kept-pointer bound, spelled -- a grounding
                           # doc ages slower than a directive but never silently forever


def _grounding_exists(pointer: str) -> bool:
    """Does the GROUND FIRST pointer resolve to a real file? (W61)

    The pointer is free text that USUALLY opens with a repo-relative path. Only a
    path-shaped pointer is checkable -- anything else returns True (not our business,
    never a false alarm). Boot age-stamped this line but never resolved it, so when the
    library migration re-homed chronicles/ into docs/library/chronicle/, a two-day-old
    pointer kept rendering as FRESH while naming a deleted file. A dangling first
    instruction is the most expensive line in the whole boot."""
    try:
        cand = (pointer or "").strip().split()[0]
    except Exception:
        return True
    # deepseek fence F1 (2026-07-25): a slash alone is NOT path-evidence -- a pointer
    # opening "C1/C2 design" or "G0-G5" would be treated as a path and render a false
    # [MOVED?], which is the exact false-alarm class this whole change removes. Require a
    # file-ish extension too; anything else is prose and is never claimed to be missing.
    cand = cand.replace("\\", "/")
    if not cand or "/" not in cand or not re.search(r"\.[A-Za-z0-9]{1,6}$", cand):
        return True                      # prose, not a path -- nothing to resolve
    root = os.path.dirname(os.path.abspath(__file__))
    return os.path.exists(os.path.join(root, cand)) or os.path.exists(cand)


def _grounding_line(pointer: str, created_day: str, age_days=None) -> str:
    """Render GROUND FIRST: pointer + age stamp (W37) + resolvability (W61)."""
    tags = f" [as of {created_day}]"
    if age_days is not None and age_days >= GROUNDING_FRESH_DAYS:
        tags += (f" [STALE? {age_days}d old -- the voice may have moved on; "
                 "re-point at wrap]")
    if not _grounding_exists(pointer):
        tags += (" [MOVED? this path does not resolve -- the doc was re-homed or "
                 "deleted; find it by title (py agent_cli.py lookback \"<title>\") "
                 "or re-point at wrap]")
    return f"# GROUND FIRST: {_clip(' '.join(pointer.split()), 160)}{tags}"


def _directive_done_tasks(focus_text: str) -> list:
    """W04 ledger cross-check: T-numbers the directive names whose ledger status
    CONTRADICTS do-this-FIRST (kimi B1(c): parked/abandoned count, not just done).
    Now rides task_ledger.settled_tasks -- the same helper the runner's premise-gate
    uses (one frontier-honesty law, two organs). Fail-open: the stamp informs."""
    try:
        from core.coord.task_ledger import settled_tasks
        settled, _live = settled_tasks(focus_text)
        return settled
    except Exception:
        return []


def _recall_armed_line(warm_n) -> str:
    """W09: the one-line proof recall-at is live. warm_n = lesson count (None = warm
    failed). A fresh seat reads this so LATER silence is calibrated, not suspect."""
    if warm_n is None:
        return ("# recall-at: could not warm the lesson cache (surface may be cold this "
                "session -- hints may not fire; investigate core.recall.at_action)")
    return (f"# recall-at: armed ({warm_n} lesson(s) warm) -- listening at every edit; "
            f"downstream silence is CALIBRATED (nothing relevant), not a dead hook")


CONDUCT_VERSION = "conduct-v1"


def _charter_stretch(agent_id: str):
    """This seat's current stretch, read from its charter (L7 records it THERE).

    Returns None when the charter carries none -- which today is every seat (kimi F6,
    2026-07-25 audit): charters/ exists and is seated, but was never given the
    demonstrated-abilities or current-stretch lines the activation map claims it carries.
    L7 is the law with the most explicit recording requirement and it has no recorder yet,
    so this renders a NAMED GAP rather than silently omitting the line."""
    try:
        p = Path(__file__).resolve().parent / "charters" / str(agent_id) / "CHARTER.md"
        if not p.is_file():
            return None
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip().lstrip("-").strip()
            if s.lower().startswith(("current stretch:", "stretch:")):
                return s.split(":", 1)[1].strip() or None
    except Exception:
        return None
    return None


def _head_commit_epoch():
    """Unix time of HEAD, or None. The repo's clock, for comparing against note clocks."""
    try:
        import subprocess as _sp
        root = os.path.dirname(os.path.abspath(__file__))
        # C7-4 (regressed 2026-07-25, caught 2026-07-26): this runs on the BOOT path, so
        # an MCP seat's boot spawns it. capture_output gives fresh stdout/stderr pipes but
        # leaves STDIN -- the server's JSON-RPC transport handle -- inherited, and Windows'
        # Proactor then defers the pending tool response until another inbound frame. Sever
        # it. See tests/test_subprocess_stdin_sever.py, which now pins the whole class.
        r = _sp.run(["git", "-C", root, "log", "-1", "--format=%ct"],
                    stdin=_sp.DEVNULL, close_fds=True,
                    capture_output=True, text=True, timeout=10)
        return int((r.stdout or "").strip()) if r.returncode == 0 else None
    except Exception:
        return None


def _continuity_drift(notes=None) -> str:
    """Boot line: have the CONTINUITY ORGANS gone stale relative to the repo?

    2026-07-25, the reason this exists. Three of the four continuity organs were carrying
    stale content AT THE SAME TIME -- GROUND FIRST aimed at a two-day-old chronicle,
    where-we-are trailing four commits, and the directive naming a plan a debate had
    superseded. Nothing said so. The seat found out by looking.

    That is the asymmetry this closes: RETRIEVAL is automatic (recall-at fires at every
    action, unasked, and it is the organ that demonstrably works) while CAPTURE is manual
    (wrap, note, --grounding all wait for a seat to remember at the right moment). A
    continuity layer whose refresh depends on remembering is a continuity layer that goes
    stale exactly when a session was too busy to remember -- which is when it matters most.

    This does NOT auto-write anything. Deliberately. The corpus already grows at ~13.7x its
    own target rate with flat measured value, so generating content automatically would add
    noise to a system whose problem is not scarcity. Tonight's failures were never MISSING
    content; they were stale POINTERS to content that already existed. So the automation
    belongs on the pointer, not the payload: notice the drift, say it, and let a seat decide
    whether it matters. Silent when the notes are newer than HEAD -- no drift, no line.
    """
    head_at = _head_commit_epoch()
    if not head_at:
        return ""
    try:
        from datetime import datetime as _dt
        if notes is None:
            notes = get_agent_memory().get_decisions(days=90)
        stale = []
        for title in ("where-we-are", "next-focus", "grounding-pointer"):
            n = next((d for d in notes if d.title == title and not d.superseded), None)
            if n is None:
                stale.append(f"{title} MISSING")
                continue
            try:
                if _dt.fromisoformat(str(n.created_at)).timestamp() < head_at - 1800:
                    stale.append(title)
            except Exception:
                pass
        if not stale:
            return ""
        return ("# [continuity DRIFT] the repo has moved since these were written: "
                + ", ".join(stale)
                + " -- they describe an OLDER system than the one you are booting into. "
                  "Refresh at wrap (py agent_cli.py wrap --focus/--grounding, note where-we-are).")
    except Exception:
        return ""


def _stance_block(agent_id: str) -> list:
    """C1 -- the boot stance block. The activation map's second organ, built 2026-07-25.

    CONDUCT.md listed this among organs that FIRE, in the present tense. It had been
    deferred as "build slice C1" and stayed deferred, so the doctrine's own activation
    map overstated itself. Found independently by BOTH seats in tonight's stance-recall
    round, by different methods: deepseek introspected its own system prompt (no stance
    lines present in a runner's folded head) and kimi read cmd_boot end-to-end (no stance
    render anywhere in the path). Verified a third time by this seat's own boots.

    Kimi's audit named what the absence actually costs, and it decides the content here:
    a seat inherits the FORMS (open with intent, quote Daniel) without the LICENSE (the
    laws are a floor it is permitted to amend) -- "the difference between a culture and a
    compliance checklist." That is why line 2 is the license and not more law text.

    Stamped with conduct_version per the v1.1 substrate rule. Kimi F2 found ZERO existing
    projections carry that stamp; this organ is born compliant instead of joining the gap.
    Lives in the ORIENTATION HEADER, not cmd_boot, because the head is what a stateless
    peer folds into its system prompt -- the precise surface deepseek proved was bare.
    """
    stretch = _charter_stretch(agent_id)
    return [
        f"# STANCE ({CONDUCT_VERSION}, docs/CONDUCT.md): intent before task | Daniel's "
        "words verbatim | one calibrated question per ask | red is a gem (credit the "
        "finder, help the lane, never blame) | 'no' is information | own, don't assign",
        "# LICENSE: the laws are a FLOOR, not a ceiling -- exceed them, and file "
        "divergences that WORK as wishes/lessons to be amended in at a gate (the "
        "anti-fossil clause). Inheriting the forms WITHOUT this license is the known "
        "failure mode; the forms alone are a compliance checklist, not a culture.",
        (f"# stretch ({agent_id}): {stretch}" if stretch else
         f"# stretch ({agent_id}): none recorded in charters/{agent_id}/CHARTER.md -- "
         "L7 wants one per arc; unrecorded is a GAP, not a zero"),
    ]


def _orientation_header(agent_id: str, primer_aware: bool = False) -> str:
    """The boot head a COLD agent (or a stateless peer's trimmed onboarding) needs first:
    map -> governing arc -> where-we-are -> precedence -> compact ledger. Every line derived
    from live state; every section fail-open (a broken source drops its line, never boot).
    T074 W13: under a primer-aware boot the head carries the FULL where-we-are body (the
    whisper already carried the clip; the boot is the resume anchor) + sibling details."""
    lines = []
    root = Path(__file__).resolve().parent
    if (root / "docs" / "ARCHITECTURE.md").is_file():
        lines.append("# Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)")
    if (root / "docs" / "method-baseline-2026-07.md").is_file():
        # The METHOD is boot-surfaced beside the map (Daniel 2026-07-11: best-from-fresh-boot):
        # awareness at boot -> recall at action -> gates at ship (T031) -> scorecard at wrap.
        lines.append("# Method: docs/method-baseline-2026-07.md (the HOW contract -- fenced dual "
                     "passes on load-bearing work, pre-registered acceptance, kill drills; gated "
                     "slices cite their reconciled build spec)")
    try:
        from core.learning.agent_memory import get_agent_memory
        notes = get_agent_memory().get_decisions(days=90)
        # W37/B6: the GROUND-FIRST pointer renders BEFORE everything else that follows --
        # the voice precedes the state (tonight's two boots proved the order). Age-stamped
        # per kimi (a): never grow W04's disease in a new organ.
        try:
            gp = next((d for d in get_agent_memory().get_decisions(days=3650)
                       if d.title == "grounding-pointer" and not d.superseded), None)
            if gp is not None:
                g_age = None
                try:
                    from datetime import datetime as _dtg
                    g_age = (_dtg.now() - _dtg.fromisoformat(str(gp.created_at))).days
                except Exception:
                    pass
                lines.append(_grounding_line(gp.decision, str(gp.created_at)[:10], g_age))
        except Exception:
            pass
        # Governing arc = the <slug>-status note tied to what is ACTIVE, not merely newest:
        # a research note for a parked future arc can be newer than the live arc's status
        # (caught by the T022 smoke: visualgen-status outranked comms-pillar-status). A note
        # GOVERNS when its slug tokens appear in an active ledger task's title; newest such
        # wins, newest-with-doc is the fallback when nothing active matches.
        active_text = ""
        try:
            from core.coord.task_ledger import state_view
            active_text = " ".join(t["title"].lower()
                                   for t in (state_view().get("in_progress") or []))
        except Exception:
            pass
        # A DONE arc must NEVER present as governing (2026-07-11 incident: boot pointed a
        # fresh session at comms-pillar-synthesis -- "ARC COMPLETE, ALL SLICES SHIPPED" --
        # which sent it to build paused UI). Skip any <slug>-status note whose body
        # declares completion; a done arc as "governing" is strictly worse than no arc.
        _DONE = ("arc complete", "all slices shipped", "status: superseded",
                 "status: historical")
        candidates = []
        for d in notes:                                   # newest first; convention: <slug>-status
            if d.title.endswith("-status"):
                body = (d.decision or "")
                if any(mark in body.lower() for mark in _DONE):
                    continue                              # completed arc -> never governs
                m = re.search(r"docs/[\w\-./]+\.md", body)  # nested ok: atom projections live at docs/library/<type>/
                if m:
                    slug_tokens = [w for w in d.title[:-len("-status")].split("-") if len(w) > 2]
                    governs = bool(slug_tokens) and all(w in active_text for w in slug_tokens)
                    candidates.append((governs, d.title, m.group(0)))
        # Known bound (deepseek gate review, attack 1): a MIXED-TOPIC active task title that
        # names two arcs' slugs makes both govern; newest wins and may be the wrong one. The
        # match is keyword-projective, NOT zero-false-positive (the spec overclaimed). Kept
        # because the header CITES its source note, so a wrong pick is visible and fixed by
        # re-noting -- and one-task-one-arc titles are the ledger convention anyway.
        # A real match (slug tokens in an active task title) is AUTHORITATIVE. A fallback
        # (newest non-done note, nothing actually governs the active work) is labelled as
        # WEAK, not asserted as governing -- the 2026-07-11 incident's second lesson: a
        # confidently-wrong "Governing arc:" line is worse than an honest "no arc governs".
        # RB-12 (W3): candidate order is deterministic WITHOUT a local sort -- it inherits
        # get_decisions()'s (created_at, title, id) total order, which preserves the
        # newest-wins doctrine above. An alpha pre-sort here (the review's draft remedy,
        # written against the old single-key sort) would silently replace newest-wins
        # with alphabetical-wins and make the fallback's "newest is" line lie.
        match = next((c for c in candidates if c[0]), None)
        if match:
            lines.append(f"# Governing arc: {match[2]}  (from note '{match[1]}')")
        elif candidates:
            lines.append(f"# Governing arc: (none matches the active task -- newest is "
                         f"{candidates[0][2]}, note '{candidates[0][1]}'; trust the "
                         f"DIRECTIVE + ledger)")
        else:
            lines.append("# [GAP] Governing arc: (none active -- check notes/ledger)")
        wwa = next((d for d in notes if d.title == "where-we-are"), None)
        if wwa:
            one_line = " ".join((wwa.decision or "").split())
            # M4 (kimi seat-zero counter): the one line every seat reads to the END must
            # carry its own fetch pointer when it clips -- never a dead-end ellipsis.
            more = " (full: py agent_cli.py note <you> --get where-we-are)"
            if primer_aware:
                # W13: the whisper carried the clip; the boot head IS the resume anchor
                # now -- full body (the NOTES section below skips its duplicate, R16).
                clipped_l = _clip(one_line, 900)
                lines.append(f"# where-we-are (full): {clipped_l}"
                             + (more if len(one_line) > 900 else ""))
            else:
                clipped_s = _clip(one_line, 120)
                lines.append(f"# where-we-are: {clipped_s}"
                             + (more if len(one_line) > 120 else ""))
        else:
            lines.append("# [GAP] where-we-are: (no note yet -- record one with `agent_cli note`)")
        if primer_aware:
            sib = _boot_siblings_line(agent_id)
            if sib:
                lines.append(sib)
        # F1 (2026-07-11 incident): the CURRENT DIRECTIVE -- what to do FIRST and what NOT
        # to do yet -- rendered with authority ABOVE the raw NEXT list. next-focus already
        # IS the priority note-kind (deepseek: no new primitive); the gap was that boot
        # never surfaced it, so a fresh session read top-of-NEXT (an oldest-first artifact)
        # as priority. This line is the fix's whole point: intent beats list order.
        nf = next((d for d in notes if d.title == "next-focus"), None)
        if nf:
            focus = " ".join((nf.decision or "").split())
            # W04 (three-bite wish: three consecutive seats re-diagnosed one stale banner):
            # a directive that outlives its work must CONFESS, not command -- date stamp
            # always, age flag past DIRECTIVE_STALE_DAYS, and a ledger cross-check on any
            # T-number it names (the precedence doctrine rendered inline). All fail-open.
            tags = ""
            created = str(nf.created_at or "")
            if created[:10]:
                tags += f" [as of {created[:10]}]"
            try:
                from datetime import datetime as _dt
                age_d = int((_dt.now() - _dt.fromisoformat(created)).days)
                if age_d >= DIRECTIVE_STALE_DAYS:
                    tags += f" [STALE? {age_d}d old -- verify against the ledger]"
            except Exception:
                pass
            contra_named = _directive_done_tasks(focus)
            if contra_named:
                tags += (f" [LEDGER DISAGREES: {', '.join(contra_named)} -- "
                         f"trust the ledger]")
            lines.append(f"# >> CURRENT DIRECTIVE (do this FIRST; beats the NEXT list order): "
                         f"{_clip(focus, 160)}{tags}")
        else:
            lines.append("# [GAP] CURRENT DIRECTIVE: (none set -- use `wrap --focus` to set priority)")
        try:   # W33/B3: the capability-gated standing queue (kimi (a): caps-aware render --
            # a seat without the needed grant gets one dim line, never a shouted work list)
            from core.coord import defer_queue as _dq
            dq_section = _dq.render_boot_section(agent_caps=_agent_acl_caps(agent_id))
            if dq_section:
                lines.append(dq_section)
        except Exception:
            pass
        try:   # W34/B4: the suite-baseline receipt line (age + decay advisory; "" when none)
            from core.coord import suite_baseline as _sb
            sb_line = _sb.render_boot_line()
            if sb_line:
                lines.append(sb_line)
        except Exception:
            pass
    except Exception:
        # Store down -> a structurally-valid but semantically-empty head is WORSE than an
        # honest gap line (deepseek gate review, attack 3): say what is missing and where
        # to look instead of silently printing map+doctrine alone.
        lines.append("# (notes store unreachable -- governing arc + where-we-are unavailable; "
                     "start from docs/ARCHITECTURE.md and `task list`)")
    lines.append(PRECEDENCE_DOCTRINE)
    try:
        import time as _time
        from core.coord.task_ledger import state_view
        v = state_view(now=_time.time())
        active, nxt, blocked = v.get("in_progress") or [], v.get("next") or [], v.get("blocked") or []
        done = v.get("done") or []
        proposed = v.get("proposed") or []
        n_stale = sum(1 for t in proposed if t.get("stale"))
        latest = next((f"@{(t.get('commit') or '')[:8]}" for t in reversed(done) if t.get("commit")), "")
        prop = f"{len(proposed)} proposed" + (f" ({n_stale} STALE -- re-approve or abandon)" if n_stale else "")
        lines.append(f"# Ledger: {len(done)} done {latest} | {len(active)} active | {len(nxt)} next | "
                     f"{len(blocked)} blocked | {prop} -- "
                     "RULE: DONE is closed, the ledger beats old messages (details: task list)")
        for t in active[:3]:
            lines.append(f"#   {t['id']} - {_clip(t['title'], 90)}  ({t['status']}"
                         + (f", {t['owner']}" if t.get("owner") else "") + ")")
        for t in nxt[:2]:
            lines.append(f"#   next: {t['id']} - {_clip(t['title'], 90)}")
        for t in blocked[:3]:
            lines.append(f"#   BLOCKED: {t['id']} - {_clip(t['title'], 70)}")
    except Exception:
        pass
    lc = root / "docs" / "LIVE_CONSTRAINTS.md"
    if lc.is_file():
        # T068-R1 (deepseek M9): the constraint pack -- the live-system rules that break a
        # design when forgotten, rendered into EVERY seat's orientation header so
        # constraint-awareness stops being experience-acquired. Placed AFTER the ledger
        # block: the four cold-start questions own the head-16 (T022 contract); capped at
        # 6 in-head, the doc carries the full list.
        try:
            bullets = [ln.strip()[2:] for ln in lc.read_text(encoding="utf-8").splitlines()
                       if ln.strip().startswith("- ")]
            if bullets:
                extra = f" (+{len(bullets) - 6} more in the doc)" if len(bullets) > 6 else ""
                lines.append(f"# LIVE CONSTRAINTS (docs/LIVE_CONSTRAINTS.md -- forget one and "
                             f"it breaks you{extra}):")
                lines.extend(f"#   {b}" for b in bullets[:6])
        except Exception:
            pass
    # C1 stance block, placed here for the SAME reason LIVE CONSTRAINTS is: the four
    # cold-start questions own the head-16 (T022 contract). First placement put stance
    # ahead of the map and pushed "RULE: DONE is closed" out of the window -- the P2 gate
    # caught it immediately. A new organ earns its way in without displacing a proven one;
    # what deepseek's finding actually requires is PRESENCE in the folded head, not primacy.
    try:
        lines.extend(_stance_block(agent_id))
    except Exception:
        pass
    try:   # continuity drift -- silent unless the notes lag HEAD; placed here, not in the
        # head-16, per new_boot_organ_must_not_spend_head16 (a lesson learned the hard way
        # a few hours before this line was written).
        _cd = _continuity_drift()
        if _cd:
            lines.append(_cd)
    except Exception:
        pass
    return "\n".join(lines)


def cmd_wish(args):
    """One-command door to docs/WISHLIST.md (W12; Daniel's standing ergonomics ledger,
    2026-07-18): file a wish the MOMENT friction is felt -- no ceremony, no approval,
    auto-numbered, and the W## echoes back (deepseek refinement) so you can cite it at the
    next gate curation. Flag-shaped prose rides --text-file (the C3-1 law, honored from birth)."""
    import re as _re
    from datetime import datetime as _dt
    path = Path(os.getenv("AKASHIC_WISHLIST_FILE",
                          str(Path(__file__).resolve().parent / "docs" / "WISHLIST.md")))
    if not path.exists():
        print(f"[wish] REFUSED: {path} missing -- the ledger is git-tracked; restore it first")
        return 2
    body = ""
    if getattr(args, "text_file", None):
        body = Path(args.text_file).read_text(encoding="utf-8").strip()
    elif args.text:
        body = " ".join(args.text).strip()
    if not body:
        print("[wish] REFUSED: empty wish (pass text or --text-file)")
        return 2
    text = path.read_text(encoding="utf-8")
    nums = [int(m) for m in _re.findall(r"- \[[ x~]\] W(\d+)", text)]
    # The id space can COLLIDE and nothing used to notice. max+1 never collides against a correct
    # read, so duplicates arrive via STALE reads -- two seats filing batches against different
    # versions of this file. Measured 2026-08-01: 128 blocks, highest id W114, 14 ids doubled
    # (W00, W57..W69), so citing "W58" is ambiguous. Report it LOUDLY and still file: this is
    # Daniil's no-ceremony capture door ("append the moment friction is felt") and a capture
    # mechanism that refuses is worse than one with an ambiguous id.
    _dupes = sorted({x for x in nums if nums.count(x) > 1})
    if _dupes:
        print("[wish] WARNING: this ledger's id space has COLLIDED -- " +
              ", ".join(f"W{d:02d}" for d in _dupes) +
              " each appear more than once, so citing them is ambiguous. Filing anyway; "
              "re-number at the next curation.")
    n = (max(nums) if nums else 0) + 1
    if n in nums:   # unreachable via max+1; a guard against a future refactor reintroducing reuse
        print(f"[wish] REFUSED: computed W{n:02d} but it already exists -- allocator is unsafe")
        return 2
    block = f"- [ ] W{n:02d} ({_dt.now().strftime('%m-%d')}, {args.agent_id}) — {body.rstrip('.')}."
    if (args.trigger or "").strip():
        block += f" Trigger: {args.trigger.strip().rstrip('.')}."
    if (args.land or "").strip():
        block += f" Land: {args.land.strip().rstrip('.')}."
    marker = "\n## Folded"
    if marker not in text:
        print("[wish] REFUSED: WISHLIST.md structure drifted ('## Folded' anchor missing) -- file by hand")
        return 2
    text = text.replace(marker, f"{block}\n{marker}", 1)
    path.write_text(text, encoding="utf-8")
    print(f"[wish] filed W{n:02d} ({args.agent_id}) -> {path.name} -- cite W{n:02d} at the next gate curation")
    try:
        capture_event("wish", f"{args.agent_id} filed W{n:02d}: {body[:120]}",
                      agent_id=args.agent_id, detail={"wish": f"W{n:02d}", "body": body[:500]})
    except Exception:
        pass
    return 0


#: T226 -- what `--bg` hands to its detached child, and what it deliberately does not.
#:
#: THE DEFECT THIS REPLACES. The child argv was assembled by hand from four remembered flags,
#: so every flag added since was silently dropped. Measured 2026-08-07:
#:   py agent_cli.py ask --bg --fan 5 "..."   ->  ONE answer, n=None, branches=0.
#: The caller asked for a five-branch N-version blind, got a single ask, and was told nothing
#: -- while `--bg`'s own help advertises "Fan out without drowning". --system and
#: --continuations were dropped the same way.
#:
#: A hand-written forwarder is a MEMBERSHIP list, and membership lists rot at exactly the rate
#: new flags are added. This one is still a list, but it is a TOTAL one: the pin walks the ask
#: parser and fails if any flag is in neither table, so the next flag cannot be forgotten --
#: it has to be classified. (convergent_fixes_describe_meaning_not_location_or_membership: the
#: fix that lasts describes the RULE, and the rule here is "every flag is forwarded or
#: explicitly is not".)
_BG_FORWARD = {
    "with_files":   lambda v: [x for f in v for x in ("--with", str(f))],
    "model":        lambda v: ["--model", str(v)],
    "max_tokens":   lambda v: ["--max-tokens", str(v)],
    "system":       lambda v: ["--system", str(v)],
    "fan":          lambda v: ["--fan", str(v)],
    "prompts_file": lambda v: ["--prompts-file", str(v)],
    "workers":      lambda v: ["--workers", str(v)],
    "continuations": lambda v: ["--continuations", str(v)],
    # store_false: only the NON-default is expressible, so only it is emitted.
    "continue_on_cut": lambda v: [] if v else ["--no-continue"],
    "as_agent":     lambda v: ["--as", str(v)],
    # T261. NOT merged with as_agent above: --as is the SENDER, --as-resident is the TIER,
    # and one flag carrying both meanings is the T174 homonym class.
    "as_resident":  lambda v: ["--as-resident", str(v)],
    # T281: the declared geometry rides to the child so its route-journal line is labeled.
    "geometry":     lambda v: ["--geometry", str(v)],
    # T256. Caught by T226's own pin before it shipped -- exactly the case that guard was built
    # for, since --bg used to assemble its argv from a hand-remembered list and silently dropped
    # every flag added afterwards. --lens is repeatable, so it emits one pair per lens.
    "preset":       lambda v: ["--preset", str(v)],
    "lens":         lambda v: [x for lens in (v or []) for x in ("--lens", str(lens))],
    "lens_file":    lambda v: ["--lens-file", str(v)],
}

#: Deliberately NOT forwarded, each with the reason. A flag lands here to be excluded on
#: purpose; the pin treats an unlisted flag as an omission, which is what silence was.
_BG_NOT_FORWARDED = {
    "text":        "the prompt is appended positionally by the caller",
    "prompt_file": "already read into `prompt` above -- forwarding it would read the file twice",
    "bg":          "the child must not spawn its own child (unbounded recursion)",
    "bg_child":    "set explicitly with the new handle",
    "json":        "set explicitly -- the child always reports JSON so both paths share a shape",
    "get":         "a READ; refused alongside --bg before this point",
    "list":        "a READ; refused alongside --bg before this point",
    "status":      "a READ; returns before this point",
    "peer":        "the durable path is handled before --bg and never reaches here",
    "wait":        "--peer only, and --peer never reaches here",
    "poll":        "--peer only, and --peer never reaches here",
    "launch":      "--peer only, and --peer never reaches here",
    "launch_wait": "--peer only, and --peer never reaches here",
    "fn":          "argparse plumbing, not a flag",
}


def _bg_forward_argv(args) -> list:
    """Rebuild the child's flags from the parent's parsed args. Never raises."""
    out = []
    for dest, emit in _BG_FORWARD.items():
        v = getattr(args, dest, None)
        # None/""/0/[] all mean "not asked for". continue_on_cut is the one flag whose
        # meaningful value is False, so it is emitted from its own branch above.
        if dest == "continue_on_cut":
            out += emit(True if v is None else bool(v))
            continue
        if v is None or v == "" or v == 0 or v == []:
            continue
        try:
            out += emit(v)
        except Exception:
            continue
    return out


def _ask_payload(o) -> dict:
    """The JSON body for every `ask` door, WITH a discoverable `warnings` list.

    T237, found by being the machine caller. A blind-draft experiment was silently
    compromised by a clipped file, and the notice built to prevent exactly that (T218,
    widened by T225) reached NEITHER channel: it goes to stderr, and the `--json` branches
    `return` before emitting it. Verified -- the payload carried context.truncated=True while
    'CLIPPED' never appeared on stderr.

    A JSON CONSUMER DOES NOT READ PROSE, IT READS KEYS. The signal already existed at
    `context.truncated`, but a caller had to KNOW that nested key; none of four probes did.
    A top-level `warnings` array is discoverable by anyone who prints the payload once.

    ONE helper for all three ask doors, because the alternative is patching three sites and
    that is the exact shape of T219 (a fix wired into one of two harnesses) and T220 (one of
    two clip sites) -- both of which I found in someone else's code the same day I did this.

    Absent when clean: a warnings key that always appears gets filtered out mentally, which
    is how the real one goes unread.
    """
    d = dict(o.detail or {})
    body = {"ok": o.ok, "partial": o.partial, "why": o.why, **d}
    # T242: the evidence notice is MINTED AT THE BOUNDARY (core.comm.ask.attach_evidence) and
    # arrives already in detail["warnings"], so this door RENDERS it and no longer computes
    # it. Recomputing here is what confined the whole guard to the CLI: three call sites, all
    # of them in this file, and every importing caller unwarned by construction -- measured
    # twice on 2026-08-08. The WIDENED notice (T225) still applies; it just applies one layer
    # down now, where it also protects callers who never reach this function.
    warn = list(d.get("warnings") or [])
    if o.partial and o.why:
        warn.append(f"PARTIAL: {o.why}")
    if warn:
        body["warnings"] = warn
    return body


def load_fan_prompts(raw: str):
    """Parse --prompts-file into what ask_many actually takes (T245).

    THREE ACCEPTED FORMS, and the third is the one that was broken:
      JSON array of strings          ["a", "b"]                         -> unchanged
      fence-separated text           multi-line prompts split on ^---$  -> unchanged
      JSON array of objects          [{"prompt": ..., "files": [...]}]  -> per-branch evidence

    T244 taught ask_many that a branch may declare the evidence its standpoint allows. This
    door then did `[str(p) for p in loaded]` and stringified every element, so the capability
    was unreachable AND the failure was silent: the dict became its own Python repr and was
    sent as the question, so a helper received {'prompt': 'audit this', 'files': [...]} and
    answered it. Built, wired, and destroyed in transit -- the check_wiring class in the shape
    that is hardest to see.

    REFUSES a `prompt`-less object BY INDEX rather than yielding an empty branch. A paid-for
    helper that was asked nothing returns nothing, and in a fan of twenty that is
    indistinguishable from a helper that found nothing -- the same silent-cap lie this repo
    keeps paying for.

    Extracted to module level because it could not be pinned inline, which is the other half
    of why the defect shipped.
    """
    try:
        loaded = json.loads(raw)
    except ValueError:
        loaded = None

    if isinstance(loaded, list):
        out = []
        for i, p in enumerate(loaded):
            # T252, found by Gemini 3.1 Pro: a prompt must BE a string. The previous check was
            # `str(p.get("prompt", "")).strip()`, and str() of any falsy non-string returns a
            # TRUTHY string -- so None, 0 and False all passed the very check that exists to
            # refuse empty questions, and a paid helper was asked the literal 'None'.
            #
            # T245's pin missed the whole class because it tested a MISSING key, never a key
            # that is present and falsy. Absent and empty are different claims (T246, same
            # week, one file over).
            #
            # Refuse the TYPE, not the content: "0" as a string is a legitimate question.
            raw_prompt = p.get("prompt") if isinstance(p, dict) else p
            if not isinstance(raw_prompt, str) or not raw_prompt.strip():
                where = "an object with" if isinstance(p, dict) else "a bare element with"
                raise ValueError(
                    f"prompt {i} is {where} no usable 'prompt': {raw_prompt!r} "
                    f"(type {type(raw_prompt).__name__}). A prompt must be a non-empty "
                    f"string. Refusing rather than sending {str(raw_prompt)!r} to a paid "
                    f"helper -- a helper asked nothing answers nothing, which in a fan of "
                    f"twenty is indistinguishable from a helper that found nothing.")
            out.append(p if isinstance(p, dict) else raw_prompt)
        return out

    # not a JSON array -> fence-separated, so a prompt may itself be multi-line
    return [chunk.strip() for chunk in re.split(r"(?m)^---\s*$", raw) if chunk.strip()]


def cmd_eye(args):
    """THE EYE's door (T278). S0: ingest / find / get. The grammar's facets land S1 on
    these same subcommands -- one door, growing verbs, never a second surface."""
    import json as _json
    from core.eye import index as _EYE
    if args.eye_cmd == "ingest":
        rep = _EYE.ingest()
        if args.json:
            print(_json.dumps(rep, indent=1)); return 0
        print(f"[eye] {rep['files_indexed']}/{rep['files_seen']} files | "
              f"{rep['events_total']:,} events ({rep['events_new']:,} new) | "
              f"unparsed {rep['lines_unparsed']}")
        if not rep["manifest_complete"]:
            print(f"[eye] COVERAGE GAP -- the index may NOT be read as whole:")
            for f in rep["files_failed"]:
                print(f"    {f['path']}: {f['why']}")
        return 0 if rep["manifest_complete"] else 1
    if args.eye_cmd == "find":
        try:
            env = _EYE.find(q=args.query or None, who=args.who, kind=args.kind,
                            session=args.session, as_of=args.as_of, limit=args.limit)
        except ValueError as e:
            print(f"[eye] 422: {e}", file=sys.stderr)
            return 2
        if args.json:
            print(_json.dumps(env, indent=1)); return 0
        for h in env["results"]:
            print(f"  {h['event_id']}  [{h['voice']}/{h['type']}]  {h['snippet']}")
        tail = (f"[eye] {len(env['results'])}/{env['total']} hit(s), "
                f"~{env['tokens_returned']} tok")
        if env["as_of"]:
            tail += f", as_of {env['as_of'][:10]}"
        if env["degraded"]:
            tail += f"  DEGRADED: {env['degraded_reason']}"
        print(tail + " -- drill: py agent_cli.py eye get <event_id>")
        return 0
    if args.eye_cmd == "freq":
        r = _EYE.freq(args.patterns)
        if args.json:
            print(_json.dumps(r, indent=1)); return 0
        import datetime as _dt
        span = ""
        if r["first_ts"] and r["last_ts"]:
            f = _dt.datetime.fromtimestamp(r["first_ts"]).strftime("%Y-%m-%d")
            l = _dt.datetime.fromtimestamp(r["last_ts"]).strftime("%Y-%m-%d")
            span = f"  span {f} -> {l}"
        print(f"[eye freq] {' | '.join(args.patterns)!r}")
        print(f"  VERDICT: {r['verdict'].upper()}  -- {r['operator_events']} operator "
              f"event(s) across {r['sessions']} session(s); "
              f"{r['events_total']} total (by voice: {r['by_voice']}){span}")
        for s in r["per_session"]:
            if s["events"]:
                print(f"    {s['session']}: {s['operator_events']} op / {s['events']} total"
                      f"  refs: {', '.join(s['refs'][:3])}")
        return 0
    if args.eye_cmd == "zoom":
        from core.eye import pyramid as _PYR
        if args.rebuild or not _PYR.nodes():
            rep = _PYR.build()
            print(f"[eye] pyramid built: {rep['l1_nodes']} exchanges, "
                  f"{rep['l2_nodes']} digests across {rep['sessions']} sessions")
        try:
            z = _PYR.zoom(args.addr)
        except ValueError as e:
            print(f"[eye] 422: {e}", file=sys.stderr)
            return 2
        if args.json:
            print(_json.dumps(z, indent=1)); return 0
        stale = "  [STALE -- rebuild to clear the fog]" if z["is_stale"] else ""
        print(f"# {z['node_id']}  ({z['level']}, ~{z['tokens']} tok){stale}")
        print(z["text"])
        if z["children"]:
            print(f"  children: {', '.join(z['children'][:6])}"
                  + (" …" if len(z["children"]) > 6 else ""))
        if z["level"] == "L1":
            print(f"  refs: {', '.join(z['refs'][:6])}")
        return 0
    if args.eye_cmd == "stats":
        s = _EYE.stats()
        if args.json:
            print(_json.dumps(s, indent=1)); return 0
        print(f"[eye stats] {s['events_total']:,} events | {s['sessions']} sessions | "
              f"time-fog {s['time_fog']:.1%} ({s['ts_missing']} timeless)")
        print(f"  by voice: {s['by_voice']}")
        print(f"  by kind:  {s['by_kind']}")
        return 0
    if args.eye_cmd == "overview":
        o = _EYE.overview()
        if args.json:
            print(_json.dumps(o, indent=1)); return 0
        import datetime as _dt
        for srow in o["sessions"]:
            span = "timeless"
            if srow["first_ts"]:
                f = _dt.datetime.fromtimestamp(srow["first_ts"]).strftime("%m-%d")
                l = _dt.datetime.fromtimestamp(srow["last_ts"]).strftime("%m-%d")
                span = f"{f}->{l}"
            print(f"  {srow['session'][:24]:<24} {srow['events']:>6} ev "
                  f"({srow['operator_events']} op)  {span}")
        print(f"[eye overview] {len(o['sessions'])} sessions")
        return 0
    if args.eye_cmd == "get":
        ev = _EYE.get_event(args.event_id)
        if ev is None:
            print(f"[eye] no event at {args.event_id!r} -- the address is session:line "
                  "(get one from eye find)", file=sys.stderr)
            return 2
        if args.json:
            print(_json.dumps(ev, indent=1)); return 0
        print(f"# {ev['event_id']}  [{ev['voice']}/{ev['type']}]  "
              f"session={ev['session']} line={ev['line']}")
        print(ev["text"])
        return 0
    return 2


def cmd_ask(args):
    """ask -- ONE synchronous question to a helper model, with no seat behind it (T171).

    Daniil, 2026-08-04: "what if you could quickly invoke with a verb a deepseek instance to
    help you with something... this might help reduce your cognitive load if you could quickly
    ask for help yourself."

    The point is that this is NOT a seat: no identity, no lock, no cursor, no mailbox, no
    heartbeat, no roster row, no reaper protection. It is born, it answers, it dies inside this
    call. Everything a seat carries exists so a peer can be addressed ASYNCHRONOUSLY and survive
    without the caller -- an answer needs none of it.
    """
    from core.comm import ask as ask_mod
    from core.comm.ask import ask as ask_helper, ask_many

    # T196d: `ask --status <id>` -- the transaction readout. A state is a successful
    # READ whatever it says: even UNKNOWN is an answer (the spec's forgotten state),
    # so every rendered state exits 0.
    if getattr(args, "status", None):
        from core.comm.ask_state import state_of
        sender = args.as_agent or os.environ.get("AKASHIC_AGENT_ID") or "claude"
        st = state_of(sender, args.status)
        if args.json:
            print(json.dumps(st, ensure_ascii=False, default=str))
            return 0
        print(f"# ask {st['ask_id']} -- {st['state']}"
              + (" (terminal)" if st["terminal"] else ""))
        if st["resolved_id"] != st["ask_id"]:
            print(f"  resolves to {st['resolved_id']} (alias chain)")
        bits = []
        if st.get("peer"):
            bits.append(f"peer {st['peer']}")
        if st.get("redrives") is not None:
            bits.append(f"redrives {st['redrives']}")
        for label, key in (("age", "age_s"), ("took", "duration_s"),
                           ("deadline in", "deadline_in_s")):
            v = st.get(key)
            if v is not None:
                bits.append(f"{label} {round(float(v), 1)}s")
        if bits:
            print("  " + " | ".join(bits))
        if st.get("answer_id"):
            print(f"  answer: {st['answer_id']}")
        # T197: was anyone home? Rendered at BOTH ends when known, because one end alone
        # cannot tell 'died mid-flight' from 'home and ignored me'.
        if st.get("peer_at_ask"):
            line = f"  peer at ask: {st['peer_at_ask']}"
            if st.get("peer_at_ask_why"):
                line += f" ({st['peer_at_ask_why']})"
            if st.get("peer_at_death"):
                from core.comm.friction import dead_verdict
                line += (f" | at death: {st['peer_at_death']}"
                         f" -> {dead_verdict(st['peer_at_ask'], st['peer_at_death'])}")
            print(line)
        if (st.get("evidence") or {}).get("answer_visible_unswept"):
            print("  an ANSWER is visible but unswept -- a sync/boot sweep will settle it")
        print(f"  caller should: {st['caller_should']}")
        return 0

    # T209, found by a COLD-ENCOUNTER test rather than by review: 0 of 3 fresh readers
    # given only --help predicted what --bg with --get does, and TWO guessed the
    # precedence exactly backwards. --get wins because reads run first, so a typo'd
    # handle never spends a model call -- sound reasoning that no reader can see.
    # Silently picking a winner IS the defect; refusing makes the impossible state
    # unrepresentable instead of surprising.
    if getattr(args, "bg", False) and (getattr(args, "get", None) or
                                       getattr(args, "list", False)):
        print("--bg SPAWNS a new ask; --get/--list READ existing ones. Pick one: run "
              "--bg first, then --get the handle it prints.", file=sys.stderr)
        return 2

    # T205: --get / --list read the background register. Reads first, so a typo in a
    # handle never accidentally spends a model call.
    if getattr(args, "get", None):
        from core.comm import ask_bg
        s = ask_bg.summarize(ask_bg.read_record(args.get))
        if args.json:
            print(json.dumps(s, ensure_ascii=False, default=str))
            return 0
        print(f"# ask {args.get} -- {s['state']}")
        if s.get("answer"):
            print(s["answer"])
        if s.get("why"):
            print(f"  why: {s['why']}", file=sys.stderr)
        print(f"  {s['next']}", file=sys.stderr)
        return 0
    if getattr(args, "list", False):
        from core.comm import ask_bg
        rows = ask_bg.list_records(limit=getattr(args, "limit", None) or 20)
        if args.json:
            print(json.dumps([ask_bg.summarize(r) for r in rows],
                             ensure_ascii=False, default=str))
            return 0
        if not rows:
            print("# no background asks recorded")
            return 0
        print(f"# background asks ({len(rows)}, newest first)")
        for r in rows:
            s = ask_bg.summarize(r)
            print(f"  {s.get('handle','?'):<10} {s['state']:<9} "
                  f"{str(r.get('prompt') or '')[:58]}")
        return 0

    prompt = " ".join(args.text).strip() if args.text else ""
    if not prompt and args.prompt_file:
        try:
            prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
        except OSError as e:
            print(f"cannot read --prompt-file: {e}", file=sys.stderr)
            return 2

    # T196c: `ask --peer <seat>` -- the durable route on the SAME verb. One command;
    # send + arm + poll underneath; the expectation outlives the interactive wait.
    if getattr(args, "peer", None):
        if getattr(args, "fan", 0) or getattr(args, "prompts_file", None):
            print("--peer is ONE durable ask to ONE seat; --fan/--prompts-file are the "
                  "stateless fan. Pick a transport.", file=sys.stderr)
            return 2
        from core.comm.ask import ask_peer
        sender = args.as_agent or os.environ.get("AKASHIC_AGENT_ID") or "claude"
        o = ask_peer(sender, args.peer, prompt,
                     wait_s=args.wait, poll_s=args.poll,
                     launch=bool(getattr(args, "launch", False)),
                     launch_wait_s=getattr(args, "launch_wait", 60.0))
        if args.json:
            print(json.dumps(_ask_payload(o), ensure_ascii=False, default=str))
            return 0 if (o.ok or o.partial) else 1
        d = o.detail or {}
        # T197: the verdict the caller used to pay 30 minutes and a forensic dig to
        # learn. Printed FIRST, before any outcome branch, because when nobody was home
        # it is the explanation for whatever follows -- and printed for every state,
        # since "the peer was live and still said nothing" is the more alarming reading.
        lz = d.get("launched") or {}
        if lz.get("action") == "launched":
            print(f"-- LAUNCHED {lz.get('tag')} (pid {lz.get('pid')}) -- {lz.get('why')}",
                  file=sys.stderr)
        elif lz.get("action") == "ambiguous":
            print(f"-- WHICH ONE? {lz.get('why')}\n   Re-run with the tag: "
                  f"--peer {(lz.get('candidates') or ['<tag>'])[0]}", file=sys.stderr)
        elif lz.get("action") in ("never_attended", "launch_refused", "no_tag"):
            print(f"-- LAUNCH {lz.get('action').upper()}: {lz.get('why')}", file=sys.stderr)
        if d.get("peer_at_ask") == "UNATTENDED":
            print(f"-- NOBODY HOME: '{args.peer}' has no attending seat "
                  f"({d.get('peer_at_ask_why')}). The ask is armed and durable, and "
                  f"redrives keep firing in case it comes up -- but nothing is reading "
                  f"it yet. Launch the seat, or use the stateless `ask` instead.",
                  file=sys.stderr)
        elif d.get("peer_at_ask") == "UNKNOWN":
            print(f"-- peer liveness UNREADABLE ({d.get('peer_at_ask_why')}) -- sending "
                  f"blind, which is the right call: a door that refuses to send because "
                  f"it cannot check is worse than one that sends.", file=sys.stderr)
        # ORDER IS LOAD-BEARING (post-incident pin): ok means NOT-FAILED, so a
        # PARTIALLY has ok=True -- branch failed, then partial, and only then the
        # two clean-done states. The first cut tested `o.ok` for ECHO and rendered
        # a timeout as CLOSED.ECHO on the verb's first live use.
        if not o.ok:
            print(f"ASK FAILED: {o.why}", file=sys.stderr)
            if d.get("how_to_check"):
                print(f"-- evidence: {d.get('how_to_check')}", file=sys.stderr)
            return 1
        if o.partial:                          # OPEN.* or UNKNOWN: a handle, not an error
            print(f"-- {d.get('state')}: {o.why}", file=sys.stderr)
            print(f"-- check: {d.get('how_to_check')}", file=sys.stderr)
            return 0
        if d.get("state") == "CLOSED.ANSWERED":
            print(d.get("answer", ""))
            print(f"\n-- CLOSED.ANSWERED | {d.get('elapsed_s')}s | "
                  f"redrives {d.get('redrives')} | ask {d.get('ask_id')}",
                  file=sys.stderr)
            return 0
        # the only remaining clean done: CLOSED.ECHO
        print(f"-- CLOSED.ECHO: the referenced work is already done "
              f"({d.get('settle')}) -- read the ledger, not the mailbox; "
              f"ask {d.get('ask_id')}", file=sys.stderr)
        return 0

    # T205: --bg -- spawn a DETACHED child running this same ask and hand back a handle.
    # The child is the same CLI with --json, so the background and foreground paths cannot
    # report different shapes; the parent exits immediately and the answer waits in a file.
    if getattr(args, "bg", False):
        import subprocess
        from core.comm import ask_bg as _bg
        handle = _bg.new_handle()
        _bg.ASK_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _bg.ASK_DIR / f"{handle}.out"
        child = [sys.executable, str(Path(__file__).resolve()), "ask", "--json",
                 "--bg-child", handle]
        child += _bg_forward_argv(args)
        # T231: the prompt rides a FILE, never the argv. It used to be appended as one
        # command-line argument, so `--bg --prompt-file <big>` died at the Windows ~32k cap
        # with WinError 206 -- and those two flags are the pair most worth combining, since
        # both exist for size. ONE PATH FOR ALL SIZES, deliberately: a "spill to a file only
        # when large" branch is where this class hides, because every small test passes and
        # only production ever meets the threshold.
        if prompt:
            pf = _bg.prompt_path(handle)
            try:
                pf.write_text(prompt, encoding="utf-8")
                child += ["--prompt-file", str(pf)]
            except OSError as e:
                print(f"could not stage the background prompt: {e}", file=sys.stderr)
                return 1
        try:
            fh = open(out_path, "w", encoding="utf-8")
            flags = 0
            if os.name == "nt":
                flags = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                         | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                         | getattr(subprocess, "DETACHED_PROCESS", 0x00000008))
            proc = subprocess.Popen(child, cwd=str(Path(__file__).resolve().parent),
                                    stdout=fh, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, creationflags=flags,
                                    close_fds=True)
        except Exception as e:
            print(f"could not spawn background ask: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 1
        _bg.write_record(handle, {"status": "running", "pid": proc.pid,
                                  "prompt": prompt[:400], "out": str(out_path),
                                  "with": list(getattr(args, "with_files", None) or [])})
        print(handle)
        print(f"-- running in background (pid {proc.pid}) -- "
              f"`py agent_cli.py ask --get {handle}`", file=sys.stderr)
        return 0

    # The child half of --bg: run normally, then file the structured result under the
    # handle so `--get` finds it. Kept here (not a separate verb) so there is exactly one
    # ask implementation and the two paths cannot diverge.
    _bg_child = getattr(args, "bg_child", None)

    # T181 -- the fan. Two shapes, because the fleet patterns need two:
    #   --fan N        one prompt, N independent answers  -> N-version blind, branch-and-bound
    #   --prompts-file many prompts, run at once          -> breadth wavefront, fenced triangle
    # T256: a preset supplies the answer CONTRACT and, on the way back, the PARSER for it. The
    # lens leads and the contract follows -- the question is what the helper should be holding
    # when it starts generating, and a wall of format rules ahead of it buries the ask (T203).
    prompts = None
    _preset = getattr(args, "preset", "") or ""
    if _preset:
        from core.comm import presets as _P
        try:
            _lenses = list(getattr(args, "lens", None) or [])
            if getattr(args, "lens_file", None):
                _lenses += _P.read_lens_file(args.lens_file)
            prompts = _P.build_prompts(_preset, _lenses)
        except (KeyError, ValueError, OSError) as e:
            print(f"--preset: {e}", file=sys.stderr)
            return 2

    if prompts is None and getattr(args, "prompts_file", None):
        try:
            raw = Path(args.prompts_file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"cannot read --prompts-file: {e}", file=sys.stderr)
            return 2
        try:
            prompts = load_fan_prompts(raw)
        except ValueError as e:
            print(f"--prompts-file: {e}", file=sys.stderr)
            return 2
    elif prompts is None and getattr(args, "fan", 0) and args.fan > 1:
        # `prompts is None` guard added with T256: without it, --preset built the branches and
        # then --fan silently replaced them with N copies of one prompt. An elif chain whose
        # first arm gained a second condition stops being exclusive, and the failure is quiet.
        prompts = [prompt] * int(args.fan)

    # T281: validate the declared geometry BEFORE any model call, on BOTH paths -- the first
    # wiring put this inside the fan branch only, and a single ask with --geometry sailed
    # straight to the model with the flag silently ignored (caught by live smoke, not by the
    # pure-function pin: a pin that supplies its own input tests the mechanism, not the wiring).
    _geom = str(getattr(args, "geometry", "") or "")
    if _geom:
        from core.comm.ask import validate_geometry as _vg
        _gerr = _vg(_geom, fan_n=int(getattr(args, "fan", 0) or 0),
                    n_prompts=(len(prompts) if prompts is not None else 1),
                    has_evidence=bool(getattr(args, "with_files", None)))
        if _gerr:
            print(f"--geometry: {_gerr}", file=sys.stderr)
            return 2

    if prompts is not None:
        o = ask_many(prompts, system=args.system or None, model=args.model or None,
                     max_tokens=args.max_tokens, max_workers=args.workers,
                     with_files=getattr(args, "with_files", None),
                     continue_on_cut=bool(getattr(args, "continue_on_cut", True)),
                     max_continuations=int(getattr(args, "continuations", 2)),
                     geometry=_geom)
        # T256: the preset PARSES its own answers on the way back. This is the half that
        # matters -- five fans in one day each ended with a throwaway regex, and every parsing
        # error this session lived in that throwaway code, never in the fan. An answer that
        # ignores the contract lands as ok=false WITH its raw text, never dropped: a paid
        # branch vanishing into a clean-looking result is how a fan starts lying about its
        # own coverage.
        if _preset and isinstance(o.detail, dict):
            from core.comm import presets as _P
            _p = _P.get(_preset)
            _parsed = [_p.parse(b.get("answer") or "")
                       for b in (o.detail.get("branches") or [])]
            o.detail["preset"] = _preset
            o.detail["parsed"] = _parsed
            _bad = [i for i, r in enumerate(_parsed) if not r.get("ok")]
            if _bad:
                o.detail.setdefault("warnings", []).append(
                    f"UNPARSED branches {_bad}: the answer did not follow the {_preset!r} "
                    f"contract. Raw text is kept in parsed[i]['raw'] -- read those by hand "
                    f"rather than treating them as empty results.")
        # T226: the fan path returned WITHOUT writing the background record, because
        # _bg.finish sits only on the single-ask path below. Measured the moment --bg
        # started forwarding --fan: three branches landed, cost real money, and
        # `ask --get` said ORPHANED -- "never wrote a result -- re-ask; nothing will
        # arrive" -- about work that was complete and on disk. A tool that tells you to
        # buy again what you already own is worse than one that quietly under-delivers,
        # so this line is part of the SAME fix, not a follow-up.
        if _bg_child:
            from core.comm import ask_bg as _bg
            _bg.finish(_bg_child, {"ok": o.ok, "partial": o.partial, "why": o.why,
                                   **(o.detail or {})})
        if args.json:
            print(json.dumps(_ask_payload(o), ensure_ascii=False, default=str))
            return 0 if o.ok else 1
        for b in o.detail.get("branches", []):
            mark = "ok" if b["ok"] and not b["partial"] else ("PARTIAL" if b["partial"] else "FAIL")
            print(f"\n--- branch {b['i']} [{mark}] " + "-" * 46)
            print(b["answer"] if b["answer"] else f"({b['why']})")
        d = o.detail
        spend = f"${d['usd']:.6f}" if d.get("usd") is not None else "unpriced"
        print(f"\n== fan: {d['n_ok']}/{d['n']} landed | {spend} | {d['elapsed_s']}s wall "
              f"| {d['workers']} workers | {d.get('model')}", file=sys.stderr)
        if o.why:
            print(f"== {o.why}", file=sys.stderr)
        # T218, fan path: one shared context feeds every branch, so a clip here silently
        # shapes N answers at once rather than one.
        # T242: minted at the boundary now, so this renders rather than recomputes.
        for _clip in (d.get("warnings") or []):
            print(f"!! {_clip}", file=sys.stderr)
        # T182: "3/3 landed" alone lets one answer read as three findings. Say the agreement --
        # in three states, because a lexical metric genuinely cannot resolve paraphrase.
        # T237: the SCORE is mode-blind and stays exactly as calibrated; the NEXT MOVE is not.
        # Five different questions used to render low overlap as a positive result, and to
        # prescribe settling a disagreement between answers to questions that were never the
        # same. One shared prescription so this surface and `ask --get` cannot drift (T225's
        # lesson, same day). The dead strings are deliberately NOT quoted here: a pin greps
        # this file for them, and it cannot tell a live prescription from a comment about one.
        div, score = d.get("diversity"), d.get("lexical_agreement")
        if div:
            shape = "same prompt" if d.get("homogeneous") else "different prompts"
            print(f"== diversity {div} (lexical {score:.2f} across {d['n_compared']} branches, "
                  f"{shape}; bands {ask_mod.DISTINCT_AT:.2f}..{ask_mod.COLLAPSE_AT:.2f})",
                  file=sys.stderr)
            print(f"== {d.get('diversity_next') or ''}", file=sys.stderr)
        return 0 if o.ok else 1

    o = ask_helper(prompt, system=args.system or None, model=args.model or None,
                   max_tokens=args.max_tokens,
                   with_files=getattr(args, "with_files", None),
                   continue_on_cut=bool(getattr(args, "continue_on_cut", False)),
                   max_continuations=int(getattr(args, "continuations", 2)),
                   as_resident=(getattr(args, "as_resident", None) or None))

    if _bg_child:
        from core.comm import ask_bg as _bg
        _bg.finish(_bg_child, {"ok": o.ok, "partial": o.partial, "why": o.why,
                               **(o.detail or {})})

    if args.json:
        print(json.dumps(_ask_payload(o), ensure_ascii=False, default=str))
        return 0 if bool(o) else 1

    if not o.ok:                       # a real failure always says why -- the type guarantees it
        print(f"ASK FAILED: {o.why}", file=sys.stderr)
        return 1

    print(o.detail.get("answer", ""))  # a PARTIAL still prints what it got (the T169 lesson)
    d = o.detail
    # T261: the tier is part of the finding, rendered where the reader forms conclusions.
    # Only the resident tier prints a line -- blind is the default and silence IS its label
    # on the human surface (the JSON envelope stamps both).
    if d.get("tier") == "resident":
        pack = d.get("catchup") or []
        print(f"== tier: resident -- {d.get('designation')} | catch-up: "
              + (", ".join(pack) if pack else "none relevant")
              + (" [PACK READ FAILED -- answered on identity only]" if d.get("catchup_error") else ""),
              file=sys.stderr)
    # T218: the helper was told in-band that its file was clipped; the caller was not, so an
    # abstention about the WINDOW read as an abstention about the CODE. Printed AFTER the
    # answer, where the reader is when they form that conclusion.
    # T242: minted at the boundary now, so this renders rather than recomputes.
    for _clip in (d.get("warnings") or []):
        print(f"\n!! {_clip}", file=sys.stderr)
    usd = d.get("usd")
    spend = f"${usd:.6f}" if usd is not None else "unpriced"
    print(f"-- {d.get('prompt_tokens', 0)}+{d.get('completion_tokens', 0)} tok | {spend}"
          f" | {d.get('elapsed_s')}s | {d.get('model')}", file=sys.stderr)
    if o.partial:
        print(f"-- {o.line()}", file=sys.stderr)
    return 0


def cmd_discord(args):
    """discord -- the outbound bridge (T223). Watch the fleet from a phone.

    OUTBOUND ONLY, and that is a security property: a webhook URL is write-only, so this
    opens no path from Discord INTO the fleet. Inbound is a prompt-injection door into a
    system holding a shell, a repo and a budget, and it does not ship until its identity gate
    is built and pinned (design doc R1-R3).
    """
    from core.comm import discord_bridge as DB

    url = DB.webhook_url()
    if args.action == "status":
        out = {"configured": bool(url),
               "source": ("env AKASHIC_DISCORD_WEBHOOK" if os.getenv("AKASHIC_DISCORD_WEBHOOK")
                          else (str(DB.URL_FILE) if url else None)),
               "forwards_kinds": sorted(DB.FORWARD_KINDS),
               "direction": "outbound only (inbound needs the R1-R3 identity gate)"}
        if args.json:
            print(json.dumps(out, indent=2)); return 0
        if not url:
            print("# discord bridge: NOT CONFIGURED (this is a state, not a failure)")
            print(f"#   1. private Discord channel -> Integrations -> Webhooks -> New -> Copy URL")
            print(f"#   2. save it to {DB.URL_FILE}")
            print(f"#   3. py agent_cli.py discord test")
            return 0
        print(f"# discord bridge: CONFIGURED via {out['source']}")
        print(f"#   forwards: {', '.join(sorted(DB.FORWARD_KINDS))}")
        print(f"#   plus ANY message from a human sender; trace is deliberately excluded")
        print(f"#   direction: {out['direction']}")
        return 0

    if args.action == "test":
        o = DB.forward({"kind": "chat", "frm": "claude",
                        "content": "Akashic Aurora -> Discord bridge is live (T223). "
                                   "Outbound only: this channel can watch the fleet, and "
                                   "nothing here can command it."}, force=True)
        print(("[discord] " + (o.why or "posted")) if not o else "[discord] posted")
        return 0 if o else 1

    o = DB.forward({"kind": args.kind, "frm": "claude", "content": args.text}, force=True)
    print(("[discord] " + (o.why or "")) if not o else "[discord] posted")
    return 0 if o else 1


def cmd_sift(args):
    """sift -- the nested ask (T217). Tiered read that returns DISSENT, not consensus.

    Tier 0 builds one content-addressed evidence pack per term; tier 1 fans the hats over
    it; tier 2 pairs curators over tier-1 output; tier 3 diffs the pairs and gates the flip
    rate on evidence identity. Adjudication stops here on purpose -- T207 measured that
    step as the one a helper gets confidently wrong.
    """
    from core.coord import sift as S
    from core.comm.ask import ask_many

    hats = [h.strip() for h in args.hats.split(",") if h.strip()] or list(S.DEFAULT_HATS)
    planes = tuple(p.strip() for p in args.planes.split(",") if p.strip())
    unknown = [h for h in hats if h not in S.DEFAULT_HATS]
    if unknown:
        print(f"unknown hat(s) {unknown}; known: {sorted(S.DEFAULT_HATS)}")
        return 2

    # ---- tier 0: evidence, and the chance to stop before spending anything
    mode = "junction" if args.junction else "breadth"
    if args.junction:
        packs = {t: S.junction_pack(t, planes=planes) for t in args.terms}
    else:
        packs = {t: S.evidence_pack(t, planes=planes,
                                    max_occurrences=args.max_occurrences)
                 for t in args.terms}
    print(f"# sift: {len(args.terms)} term(s) x {len(hats)} hat(s), "
          f"planes={list(planes)}, evidence={mode}")
    for t, p in packs.items():
        if args.junction:
            cross = sum(1 for j in p.junctions if not j["same_file"])
            print(f"  {t:<12} junctions={len(p.junctions):<4} cross-file={cross:<4} "
                  f"sha={p.sha}")
        else:
            files = len({o["file"] for o in p.occurrences})
            flag = " CAPPED" if p.truncated else ""
            print(f"  {t:<12} occ={len(p.occurrences):<4} files={files:<4} "
                  f"sha={p.sha}{flag}")
    if args.dry_run:
        print("\n# DRY RUN -- nothing spent. Read one pack before trusting any finding:")
        for t, p in packs.items():
            if args.junction:
                print(f"\n--- {t}: {len(p.junctions)} junction(s) ---")
                for j in p.junctions[:3]:
                    print(f"  {j['crossing']}{'  [same file]' if j['same_file'] else ''}")
            else:
                print(f"\n--- {t} (first 5 of {len(p.occurrences)}) ---")
                for o in p.occurrences[:5]:
                    print(f"  [{o['plane']}] {o['file']}:{o['line']}: {o['text'][:100]}")
            for b in p.blind[:2]:
                print(f"  BLIND: {b[:150]}")
        return 0

    # ---- tier 1: the hat fan. Evidence is INLINED rather than passed as a file so the
    # bytes each helper reads are exactly the bytes we hashed. T216 was the other choice
    # failing silently, and the gate downstream is only meaningful if identity is real.
    prompts, index = [], []
    for t, p in packs.items():
        for h in hats:
            prompts.append(f"{p.blob}\n\n{S.hat_prompt(h, p)}")
            index.append((t, h))
    print(f"\n# tier 1: fanning {len(prompts)} branches, {args.workers} workers ...")
    fan = ask_many(prompts, max_workers=args.workers)
    branches = (fan.detail or {}).get("branches", [])

    analyses = {}
    for (t, h), b in zip(index, branches):
        if b.get("ok") and b.get("answer"):
            analyses.setdefault(t, []).append({"hat": h, "answer": b["answer"]})
    fd = fan.detail or {}
    usd1 = fd.get("usd_total")
    # Three states, never two: a partial fan carries findings, and rendering it as failure
    # is exactly how "nine tasks, two findings" reads as a dead run.
    agg = S.summarise(n=fd.get("n", 0), n_ok=fd.get("n_ok", 0),
                      blind=[f"{fd.get('n', 0) - fd.get('n_ok', 0)} branch(es) did not "
                             f"land -- UNKNOWN, not a negative verdict"] if
                      fd.get("n_ok", 0) < fd.get("n", 0) else ["all branches landed"])
    print(f"# tier 1: {fd.get('n_ok')}/{fd.get('n')} landed"
          f"{'' if usd1 is None else f'  ${usd1:.4f}'}"
          f"  diversity={fd.get('diversity')}"
          f"  aggregate={'DONE' if bool(agg) else ('PARTIAL' if agg.ok else 'FAILED')}")
    if agg.why:
        print(f"#   {agg.why}")

    # ---- tier 2: curator PAIRS, per term. Both members read the identical bundle, so any
    # disagreement between them is about curation -- which is the only reason a flip rate
    # over them means anything.
    cur_prompts, cur_index = [], []
    for t, ans in analyses.items():
        if len(ans) < 2:
            continue
        prompt, ev_sha = S.curator_prompt(t, ans)
        for a, b in S.curator_pairs(t, hats[:2] or ["outsider", "adversary"], ev_sha):
            for member in (a, b):
                cur_prompts.append(prompt)
                cur_index.append({**member, "evidence_sha": ev_sha})
    dossiers = []
    if cur_prompts:
        print(f"# tier 2: {len(cur_prompts)} curators over {len(analyses)} term(s) ...")
        cur = ask_many(cur_prompts, max_workers=args.workers)
        for meta, b in zip(cur_index, (cur.detail or {}).get("branches", [])):
            if not b.get("ok"):
                continue
            ans = b.get("answer") or ""
            # T217 follow-up: settle the verdict against the MARGIN it won by. Measured on
            # the first cost-blind sample -- two of three FORK verdicts were a lone hat
            # promoted over a five-hat consensus, and untriaged vs triaged fell on opposite
            # sides of a pre-registered line.
            d = {**meta, "verdict": S.parse_verdict(ans),
                 "tally": S.parse_tally(ans), "answer": ans}
            d["raw_verdict"] = d["verdict"]
            d["verdict"] = S.settle_verdict(d)
            dossiers.append(d)

    # ---- tier 3: dissent first
    cmp_ = S.compare_dossiers(dossiers) if dossiers else {
        "refused": "no curator dossiers landed", "flip_rate": None, "dissents": [],
        "agreements": [], "triage_required": False, "triage_reason": "",
        "blind": ["tier 2 produced nothing; tier 1 answers are still in --out"]}

    record = {"terms": args.terms, "hats": hats, "planes": list(planes),
              "packs": {t: {"sha": p.sha, "n": len(p.occurrences),
                            "truncated": p.truncated, "blind": p.blind}
                        for t, p in packs.items()},
              "tier1": analyses, "dossiers": dossiers, "comparison": cmp_}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2, default=str)
        print(f"# full record -> {args.out}")
    if args.json:
        print(json.dumps(record, ensure_ascii=False, default=str))
        return 0

    print("\n" + "=" * 68)
    if cmp_.get("refused"):
        print("REFUSED: " + cmp_["refused"])
    else:
        print(f"DISSENT ({len(cmp_['dissents'])} of "
              f"{len(cmp_['dissents']) + len(cmp_['agreements'])} terms) -- READ THIS FIRST")
        for d in cmp_["dissents"]:
            print(f"  ! {d['term']:<12} {d['verdicts']}  hats={d['hats']}")
        if cmp_.get("triage_required"):
            print(f"\nTRIAGE: {cmp_['triage_reason']}")
        print(f"\nagreement ({len(cmp_['agreements'])}) -- weaker evidence than dissent:")
        for a in cmp_["agreements"]:
            print(f"    {a['term']:<12} {a['verdicts']}")
        print(f"\nflip_rate={cmp_['flip_rate']}")
    for b in cmp_.get("blind", []):
        print(f"BLIND: {b}")
    return 0


def cmd_friction(args):
    """friction -- the collaboration tax, read from evidence that already exists (T196a).

    Sol's metric recommendation fenced through deepseek (T196 spec): episodes from
    durable terminal events + armed expectation records; honest Nones over guesses;
    a blind list because a report that names no blindness is claiming omniscience.
    READ-ONLY: writes nothing to any stream, record, or cursor (pinned)."""
    from core.comm.friction import gather

    rep = gather(args.agent_id, window_h=args.window_h)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, default=str))
        return 0

    a = rep["agg"]

    def _s(v, suffix="s"):
        return "n/a" if v is None else f"{round(float(v), 1)}{suffix}"

    print(f"# friction -- {args.agent_id} (window {args.window_h}h)")
    rate = "n/a (nothing closed)" if a["dead_rate"] is None else f"{a['dead_rate']:.1%}"
    print(f"open {a['n_open']} | answered {a['n_answered']} | echo {a['n_echo']} "
          f"| dead {a['n_dead']} | dead-rate {rate}")
    print(f"time-to-settle p50 {_s(a['settle_p50_s'])} p90 {_s(a['settle_p90_s'])}"
          + (f" | duration unknown for {a['n_duration_unknown']} episode(s)"
             if a["n_duration_unknown"] else ""))
    # T197: WHY they died, not just how many. Each verdict names a different bug with a
    # different action, so the line carries the action -- a partition an operator has to
    # translate is a partition that gets read as one number again.
    if a["n_dead"]:
        print("why they died:")
        for key, label, action in (
                ("dead_absent", "absent", "nobody was ever home -- launch the peer"),
                ("dead_vanished", "vanished", "it died mid-flight -- chase the crash"),
                ("dead_ignored", "ignored", "home the whole time -- chase the consumer"),
                ("dead_arrived_late", "arrived_late", "came up late and still went silent"),
                ("dead_peer_unknown", "unknown", "no peer observation (pre-T197, or probe "
                                                 "unreadable) -- NOT back-filled")):
            n = a.get(key, 0)
            if n:
                print(f"  {label:<13} {n:>3}  {action}")
    # T199: does presence predict an answer? The question T197 shipped autolaunch on and
    # could not test. Rendered BEFORE the per-episode list because it is the finding.
    pe = a.get("presence_effect") or {}
    obs = sum(pe.get(k, {}).get("n", 0) for k in ("ATTENDED", "UNATTENDED"))
    if obs:
        print("does presence predict an answer? (correlation, not cause)")
        for state in ("ATTENDED", "UNATTENDED"):
            b = pe.get(state) or {}
            if not b.get("n"):
                continue
            rate = ("n/a" if b.get("answer_rate") is None
                    else f"{b['answer_rate']:.0%}")
            print(f"  peer {state:<11} {b['n_answered']}/{b['n']} answered ({rate})")
        if pe.get("n_unobserved"):
            print(f"  unobserved  {pe['n_unobserved']:>4}  no peer reading taken "
                  f"(pre-T197) -- excluded from both rates, never back-filled")
    by = a.get("by_peer") or {}
    if by:
        print("by peer (worst first):")
        for name, p in list(by.items())[:12]:
            rate = "n/a" if p["dead_rate"] is None else f"{p['dead_rate']:.0%}"
            med = "n/a" if p["settle_median_s"] is None else f"{p['settle_median_s']:.0f}s"
            print(f"  {name:<22} answered {p['n_answered']:>3} | dead {p['n_dead']:>3} "
                  f"| echo {p['n_echo']:>3} | open {p['n_open']:>3} "
                  f"| dead-rate {rate:>4} | median {med}")
    for e in rep["episodes"]:
        if e["outcome"] == "open":
            print(f"  OPEN.{e['state'].upper():<10} {e['ask_id']} -> {e['peer']} "
                  f"| age {_s(e['age_s'])} | redrives {e['redrives']} "
                  f"| deadline in {_s(e['deadline_in_s'])}")
        else:
            peer_bit = ""
            if e["outcome"] == "dead" and e.get("peer_verdict") != "unknown":
                peer_bit = (f" | {e['peer_verdict']} ({e.get('peer_at_ask')}"
                            f"->{e.get('peer_at_death')})")
            print(f"  {e['outcome'].upper():<15} {e['ask_id']} -> {e['peer']} "
                  f"| took {_s(e['duration_s'])} | redrives {e['redrives']}{peer_bit}")
    print("blind (what this reader cannot see):", file=sys.stderr)
    for b in rep["blind"]:
        print(f"  - {b}", file=sys.stderr)
    return 0


def _ledger_claim_arc(seat: str):
    """AUTO_ARC (taxonomy-ergonomics reconciliation §7): the seat's claimed ledger task
    is the arc authority; no claim -> None (born without arc; library lint flags it
    post-hoc, never a write-time block)."""
    try:
        tasks_path = Path(__file__).resolve().parent / "state" / "coord" / "tasks.json"
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
        live = [t for t in data.get("tasks", []) if t.get("owner") == seat
                and t.get("status") in ("claimed", "in_progress", "verifying")]
        return live[-1]["id"] if live else None
    except (OSError, ValueError, KeyError):
        return None


def _read_bus_message(ref: str):
    """--from-bus reader (A1, deepseek pulse spec): one already-delivered message by
    stream id from this seat's inbox streams (work first, legacy archive net). Returns
    (frm, kind, text) or None -- past the legacy TTL the capture fails LOUD, never
    silently reconstructs."""
    try:
        from core.comm.bus import Bus
        me = os.environ.get("AKASHIC_AGENT_ID", "claude")
        c = Bus(me)._client
        if c is None:
            return None
        for k in (f"bifrost:work:inbox:{me}", f"bifrost:inbox:{me}"):
            got = c.xrange(k, min=ref, max=ref)
            if got:
                _sid, f = got[0]
                return (str(f.get("frm", "?")), str(f.get("kind", "?")),
                        _capture_decode(f.get("content") or f.get("text") or ""))
    except Exception:
        return None
    return None


# bus kind -> atom type when --from-bus supplies no --type (deepseek pulse spec)
_BUS_KIND_TYPE = {"handoff": "design", "request": "brief", "question": "brief",
                  "chat": "design", "reply": "report", "inform": "report"}


# ---------------------------------------------------------------- doc adopt inference
# `doc new` mints from a body you hand it. ADOPT brings an EXISTING loose file through the
# same door -- the rescue path for work filed by seats that cannot commit (no exec) into a
# zone rule-13 refuses (research/** since the P3 flip). Inference is best-effort and every
# guess is PRINTED: a wrong stamp is a post-hoc lint fix, a lost artifact is not.

# First match wins -- order is specificity, not preference. 'design-conversation' is a
# captured conversation (chronicle), not a design, so 'conversation' outranks 'design'.
_ADOPT_TYPE_HINTS = (
    ("conversation", "chronicle"), ("capture", "chronicle"), ("retro", "chronicle"),
    ("session", "chronicle"),
    ("verdict", "ruling"), ("ruling", "ruling"),
    ("charter", "contract"),
    ("reconcil", "design"),
    ("position", "report"), ("answer", "report"), ("review", "report"),
    ("audit", "report"), ("walk", "report"), ("critique", "report"),
    ("brief", "brief"),
    ("design", "design"), ("spec", "design"), ("plan", "design"), ("proposal", "design"),
    ("map", "map"),
)

# Authorship, not identity: these are the names peers actually appear under in filenames.
_ADOPT_KNOWN_SEATS = ("claude", "deepseek", "kimi", "codex", "cursor_grok", "gemini", "fable")


def _adopt_title(stem: str) -> str:
    """Filename -> title slug: a filename is a title with punctuation and a date bolted on."""
    s = re.sub(r"\d{4}-\d{2}-\d{2}", "", stem)      # ISO date anywhere
    s = re.sub(r"^\d{8}[-_]?", "", s)               # 20260731_ prefixes (library canon)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "adopted-document"                  # a date-only name still needs a handle


def _adopt_type(stem: str) -> str:
    low = stem.lower()
    for key, typ in _ADOPT_TYPE_HINTS:
        if key in low:
            return typ
    return "report"                                  # the honest default: it is a record


def _adopt_seats(stem: str) -> str:
    """Authors named in the filename. Silence beats a wrong stamp -- returns '' when unsure."""
    low = re.sub(r"[^a-z0-9]+", "-", stem.lower())
    hits = []
    for seat in _ADOPT_KNOWN_SEATS:
        if seat in hits:
            continue
        # ids carrying '_' appear hyphenated in filenames (cursor_grok -> cursor-grok)
        if any(v in low for v in {seat, seat.replace("_", "-")}):
            hits.append(seat)
    return ",".join(hits)


def cmd_doc(args):
    """A1 (2026-07-23, artifact-substrate build; supersedes D1's file-writer): the birth
    door. Mints a typed ATOM in the store (append-only, supersession-aware; JSONL durable
    record under store/docs/) and renders its ONE read-only projection file under
    docs/library/<type>/. The file is the render; the atom is the truth.
    --from-bus <stream-id>: file ONE bus message as a conversation-atom with provenance
    (origin/speakers/source_thread/settled) -- opt-in only; blanket auto-filing is the
    sprawl one transport layer over.
    Spec: docs/library/design/20260701_artifact-substrate-the-reconciled-design_8ea728.md + docs/taxonomy-ergonomics-
    reconciliation-2026-07.md (Daniel gate fired 2026-07-23).

    Inference (never worse than typing flags; wrong stamps are post-hoc lint fixes):
    ARC from the first seat's claimed ledger task when --arc absent · CATEGORIES from
    the governed classifier merged with --category flags (cap 3, PRIMARY first) ·
    --draft births status:draft (wrap sweep + library lint curate drafts).
    """
    sub = getattr(args, "sub", "new")
    if sub == "adopt":
        # NON-DESTRUCTIVE by construction: read, mint, leave the original exactly where it
        # is. An adopt that deleted its source would be a Scribe that can lose work.
        src = (getattr(args, "path", "") or "").strip()
        if not src:
            print("[doc] REFUSED: adopt needs a path — doc adopt <file.md> [--type T] [--seats s]")
            return 2
        sp = Path(src)
        if not sp.is_file():
            print(f"[doc] REFUSED: no such file: {src}")
            return 2
        args.body_file = str(sp)
        stem = sp.stem
        if not (getattr(args, "title", "") or "").strip():
            args.title = _adopt_title(stem)
        if not (getattr(args, "type", "") or "").strip():
            args.type = _adopt_type(stem)
        if not (getattr(args, "seats", "") or "").strip():
            args.seats = _adopt_seats(stem)
        rel_src = str(sp).replace("\\", "/")
        print(f"[doc] adopting {rel_src}")
        print(f"  inferred: type={args.type} title={args.title} "
              f"seats={args.seats or '(none — pass --seats)'}   [override with flags]")
        sub = "new"
    if sub != "new":
        print("[doc] only 'new' and 'adopt' are implemented — pass 'doc new ...' or 'doc adopt <path>'")
        return 2

    typ = (getattr(args, "type", "") or "").strip().lower()
    title = (getattr(args, "title", "") or "").strip()

    from_bus = (getattr(args, "from_bus", "") or "").strip()
    conv_kwargs = {}
    if from_bus:
        msg = _read_bus_message(from_bus)
        if msg is None:
            print(f"[doc] REFUSED: bus message {from_bus} not readable from inbox streams "
                  "(expired past legacy TTL? loud failure by design -- T043 genus)")
            return 2
        frm, kind, text = msg
        me = os.environ.get("AKASHIC_AGENT_ID", "claude")
        typ = typ or _BUS_KIND_TYPE.get(kind, "report")
        conv_kwargs = dict(origin="conversation", speakers=[frm, me],
                           source_thread=from_bus, settled="live")

    if not typ or not title:
        print("[doc] REFUSED: --type and --title are required (--from-bus infers type from the message kind)")
        print("  atom types: contract map design brief report chronicle ledger ruling")
        print("  example: py agent_cli.py doc new --type report --title fence-x --seats claude --body-file x.md")
        return 2

    body = getattr(args, "body", "") or ""
    body_file = getattr(args, "body_file", "") or ""
    if body_file:
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"[doc] REFUSED: cannot read --body-file: {e}")
            return 2
    if from_bus:
        body = (body + "\n\n" if body else "") + text

    seats = [s.strip() for s in (getattr(args, "seats", "") or "").split(",") if s.strip()]
    arc = (getattr(args, "arc", "") or "").strip() or None
    arc_src = "--arc"
    if not arc and seats:
        arc = _ledger_claim_arc(seats[0])
        arc_src = "ledger claim" if arc else "(none inferable)"

    from core.library import taxonomy as _tx
    from core.library.atoms import AtomFamily, AtomError
    from core.library.projection import render_atom
    from core.foundation.store import create_store

    flag_cats = [c.strip() for c in (getattr(args, "category", None) or []) if c.strip()]
    auto_cats = _tx.classify(f"{title} {body[:500]}")
    merged, cat_srcs = [], []
    for c in flag_cats + auto_cats:
        r = _tx.resolve(c)
        if r and r not in merged:
            merged.append(r)
            cat_srcs.append("flag" if c in flag_cats else "auto")
    merged = merged[:_tx.CATEGORY_CAP_PER_ATOM]
    cat_srcs = cat_srcs[:len(merged)]

    status = "draft" if (getattr(args, "draft", False) or from_bus) else "current"
    citations = [{"target": t.strip(), "rel": "discusses"}
                 for t in (getattr(args, "cite", None) or []) if t.strip()]
    fam = AtomFamily(create_store(), repo_root=str(Path(__file__).resolve().parent))
    bt = (getattr(args, "body_type", "") or "").strip().lower() or None
    try:
        atom = fam.mint(typ, title, body, arc=arc, seats=seats, categories=merged,
                        citations=citations, status=status, category_sources=cat_srcs,
                        body_type=bt, body_type_source=("flag" if bt else "unstated"),
                        gist=(getattr(args, "gist", "") or None), **conv_kwargs)
    except AtomError as e:
        print(f"[doc] REFUSED: {e}")
        return 2

    path = render_atom(atom, repo_root=str(Path(__file__).resolve().parent))
    rel = str(Path(path).relative_to(Path(__file__).resolve().parent)).replace("\\", "/")
    print(f"[doc] atom {atom['id']}  ({typ}, status: {status})")
    print(f"  arc: {arc or '(none)'}  [{arc_src}]")
    cat_render = ", ".join(f"{c}[{s}]" for c, s in zip(merged, cat_srcs)) or "(none)"
    print(f"  categories: {cat_render}")
    print(f"  body_type: {atom['header'].get('body_type', 'markdown')}"
          f"[{atom.get('body_type_source', 'unstated')}]")
    print(f"  projection: {rel}  (read-only render; the atom is the truth)")
    print("  wrong stamp? fix post-hoc at wrap/lint — never a write-time block")
    return 0


def cmd_note(args, *, mem=None):
    """Write-once durable project note: record WHERE-WE-ARE / a decision in ONE place (the substrate),
    not by hand-editing files. Re-noting the same --title (or --supersedes ID) RETIRES the prior note
    (correct by superseding, never edit). Surfaces at `boot` + `notes`; reprojects chronicles/memory.md.
    --get <id-or-title> reads ONE full body (W01: kills the notes --json pipe dance)."""
    from core.learning.agent_memory import get_agent_memory, normalize_title
    if mem is None:
        mem = get_agent_memory()
    if getattr(args, "get", None):
        # W01 drill (kimi F8, re-bitten 07-21): exact id first -- superseded ids are legal
        # archaeology, rendered labeled; then normalized-title match resolves the ACTIVE head.
        target = str(args.get)
        pool = mem.get_decisions(days=3650, include_superseded=True)
        dec = next((d for d in pool if d.id == target), None)
        if dec is None:
            live = [d for d in pool if not d.superseded
                    and normalize_title(d.title) == normalize_title(target)]
            dec = live[0] if live else None
        if dec is None:
            ghosts = [d for d in pool if normalize_title(d.title) == normalize_title(target)]
            if ghosts:
                print(f"ERROR: '{target}' matches only superseded note(s) -- newest is id "
                      f"{ghosts[0].id}; drill that id explicitly, or browse notes --all")
            else:
                print(f"ERROR: no note with id or title '{target}' (see: notes)")
            return 1
        if getattr(args, "json", False):
            import dataclasses
            print(json.dumps(dataclasses.asdict(dec), default=str))
            return 0
        tag = "  [SUPERSEDED -- a newer note holds this title]" if dec.superseded else ""
        print(f"# {dec.title}{tag}  (id {dec.id}, {dec.created_at})")
        print(dec.decision)
        if dec.context:
            print(f"\n[context] {dec.context}")
        return 0
    if args.retire:
        # Retire mode (P1/T021): tombstone a one-shot note WITHOUT a successor -- consumed
        # handoffs, placeholders, done-arc status notes. Accepts an id or a title.
        target = str(args.retire)
        dec = next((d for d in mem.get_decisions(days=3650)
                    if d.id == target or normalize_title(d.title) == normalize_title(target)), None)
        if dec is None:
            print(f"ERROR: no active note with id or title '{target}' (see: notes --all)")
            return 1
        if not mem.retire_decision(dec.id):
            print(f"ERROR retiring {dec.id} (store unavailable?)"); return 1
        try:
            from core.events.event_log import capture_event
            capture_event("decision", f"note retired: {dec.title}", agent_id=args.agent_id,
                          refs=[f"mem:decision:{dec.id}"], detail={"retired": True})
        except Exception:
            pass
        try:
            project_notes()
        except Exception:
            pass
        if args.json:
            print(json.dumps({"retired": True, "id": dec.id, "title": dec.title})); return 0
        print(f"[OK] retired '{dec.title}' (id {dec.id}) -- recoverable via the store; "
              "gone from boot/notes defaults")
        return 0
    if not args.title or not args.note:
        print("ERROR: need --title and --note (or --retire <id|title>).")
        print('Example: py agent_cli.py note me --title "checkpoint: recall done" --note "next: write-once"')
        return 2
    clipped = []
    title = _clip(args.title, 200)
    if len(str(args.title or "")) > 200:
        clipped.append(f"[CLIPPED] title: {len(str(args.title))} chars exceeds the 200-char cap -- "
                       f"stored (and supersede-matched) as {title!r}")
    from core.learning.agent_memory import SupersedeRaceError, normalize_title, HEAD_KEY_PREFIX
    body = _intake(args.note, _MAX_NOTE, "note body", clipped)
    ctx = _intake(args.context or "", 1000, "context", clipped)
    supersedes = args.supersedes
    try:
        if supersedes:
            # RB-10: pre-read the head sentinel for a stale-explicit-target teaching
            # error BEFORE the write+claim+cleanup cycle (verify review finding #2).
            # A lost race here is NOT a race -- the caller named a specific prior
            # and retrying would supersede the wrong record.
            head = mem.store.get(HEAD_KEY_PREFIX + normalize_title(title))
            if head and head != supersedes and mem._is_active(head):
                print(f"ERROR: explicit target '{supersedes}' is not the current head "
                      f"(head is '{head}'). Drop --supersedes to auto-resolve, "
                      f"or use --supersedes {head}."); return 1
            if not head:
                print(f"ERROR: no existing note for this title; "
                      f"drop --supersedes for a fresh first note."); return 1
            # Explicit target (migration verbs): single attempt; a lost race is a
            # teaching error, not a retry -- the caller named a specific prior.
            dec_id = mem.decide(title=title, decision=body, context=ctx,
                                supersedes=supersedes, session_id=args.session or "",
                                curated=True)
        else:
            # Re-noting the same title updates-in-place. RB-8: the old read-title-then-
            # write here was the race that forked where-we-are chains (W3 spec, R-e);
            # decide_with_retry resolves the head and claims it under CAS.
            dec_id = mem.decide_with_retry(title, body, context=ctx,
                                           session_id=args.session or "",
                                           curated=True)
            try:   # report which prior this superseded (the helper owns the pointer)
                raw = mem.store.hget(mem.KEY_DECISIONS, dec_id)
                supersedes = (json.loads(raw) or {}).get("supersedes") if raw else None
            except Exception:
                supersedes = None
    except SupersedeRaceError as e:
        # SupersedeTargetError is-a SupersedeRaceError (pre-write refusal of the same
        # race), so this one clause catches both teaching errors.
        print(f"ERROR: {e}"); return 1
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
                          "superseded": supersedes or None, "clipped": clipped or None})); return 0
    print(f"[OK] noted '{title}' (id {dec_id})" + (f" - superseded prior {supersedes}" if supersedes else ""))
    for c in clipped:   # RB-5: the door's RESULT carries the clip, never silent
        print(c)
    return 0


def cmd_notes(args):
    """List active (non-superseded) project notes, newest first. The write-once read side."""
    from core.learning.agent_memory import get_agent_memory
    if args.project:
        try:
            print(f"[OK] regenerated {project_notes()}"); return 0
        except Exception as e:
            print(f"ERROR projecting notes: {type(e).__name__}: {e}"); return 1
    decs = get_agent_memory().get_decisions(days=args.days or 3650,
                                            include_superseded=bool(args.all))
    if args.json:
        print(json.dumps([{"id": d.id, "title": d.title, "note": d.decision, "at": d.created_at,
                           "superseded": bool(d.superseded)}
                          for d in decs], indent=2, default=str)); return 0
    label = "note(s) incl. superseded" if args.all else "active note(s)"
    print(f"# {len(decs)} {label}")
    for d in decs[:(args.limit or 25)]:
        tag = " [superseded]" if d.superseded else ""
        print(f"  [{d.created_at[:10]}]{tag} {d.title}: {_clip(d.decision, 140)}   (id {d.id})")
    # RB-10: vanished title groups (all records retired)
    try:
        mem = get_agent_memory()
        gone = mem.get_retired_titles()
        if gone:
            print(f"\n# {len(gone)} retired title group(s) -- every record for these titles is retired:")
            for g in gone[:10]:
                print(f"  [{g['last_retired_at'][:10]}] {g['title']} "
                      f"({g['retired_count']} record(s), last id {g['last_active_id']})")
    except Exception:
        pass
    # RB-11: chain-length warning
    try:
        from core.learning.agent_memory import CHAIN_WARN_THRESHOLD
        mem = get_agent_memory()
        long = mem.get_long_chains()
        if long:
            print(f"\n# {len(long)} title(s) with long superseded chains "
                  f"(> {CHAIN_WARN_THRESHOLD} records):")
            for c in long[:5]:
                print(f"  {c['title']}: {c['count']} records (oldest {c['oldest_id']}, newest {c['newest_id']})")
    except Exception:
        pass
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


def build_session_draft(commits, lessons, notes, max_per=8, flips=None, injections=None):
    """Distill a session's own activity into a DRAFT where-we-are -- PURE (testable). Each line keeps a
    lossless source pointer (git:<sha> / learn:experiment:<name> / mem:decision:<id>). `flips` are the
    session's FAIL->SUCCESS moments (core.recall.at_action.recent_flips) -- each is a lesson that was
    just EARNED, so the draft turns them into pre-filled candidate `learn` commands (friction audit D5:
    capture as a byproduct of the work, edit-a-draft instead of author-from-scratch). `injections`
    (recent_injections) power the RECALL REVIEW: voting moved to the reflective moment -- the explicit
    channel sat at 4 useful / 0 noise forever because nobody votes mid-work (recall vNext loop 3)."""
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
        # CORPUS GAPS (vNext loop 4): an UNCREDITED flip is a place recall had nothing to offer --
        # name them so acquisition is directed, not ad-hoc. (Credited flips already paid off above.)
        gaps = [t for t, fl in by_target.items() if not int(fl.get("credited", 0) or 0)]
        if gaps:
            lines.append(f"Corpus gaps ({len(gaps)} uncredited flip target(s) -- no stored lesson helped):")
            for t in gaps[:max_per]:
                lines.append(f"  - {_clip(_human_flip_target(t), 100)}")
    if injections:
        # W54 activation gauge (kimi F3): family-grouped firing rate at the reflective moment --
        # a "proven" claim about an organ must quote this number, not an anecdote.
        try:
            from core.recall.at_action import injections_by_family
            g = injections_by_family(injections=injections)
            lines.append(f"Recall activation by family ({int(g.get('total', 0))} injection(s) this session): "
                         + _family_gauge_render(g))
        except Exception:
            pass
        # RECALL REVIEW: what recall pushed this session, vote-ready. One keystroke at the natural
        # reflective moment beats a mid-work vote nobody casts.
        counts = {}
        for inj in injections:
            for s in inj.get("s", []):
                counts[s] = counts.get(s, 0) + 1
        if counts:
            top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:max_per]
            lines.append(f"Recall review ({len(counts)} lesson(s) surfaced this session -- vote the hits/misses):")
            for src, n in top:
                slug = str(src).replace("learn:experiment:", "")
                lines.append(f"  - {n}x {slug}")
                lines.append(f"    useful: py agent_cli.py recall-feedback --source {src}"
                             f"   |   noise: py agent_cli.py recall-feedback --source {src} --noise")
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


def _suggest_resident(title: str, limit: int = 3):
    """Which resident's OWN archive bears on this target? Returns [(callsign, agent, [receipts])].

    Evidence, not authority. The match runs T260's agent-scoped search over each resident's own
    lessons, so a suggestion can NAME what produced it -- an unreceipted suggestion is a vibe.
    Routing stays the human's act: this never assigns, and the render says SUGGEST.
    """
    out = []
    try:
        from core.fleet import residents as R
        from core.learning.learning_store import get_learning_store
        ls = get_learning_store()
        st = R._store()
        for agent in (st.lrange("residents:all", 0, -1) or []):
            rec = R.get(agent)
            if not rec:
                continue
            hits = ls.search_learnings_by_keyword(title, agent=agent)[:limit]
            if hits:
                out.append((rec.get("callsign") or agent, agent,
                            [str(h.get("id")) for h in hits]))
    except Exception:
        return []          # a suggestion engine must never break a wrap
    out.sort(key=lambda r: -len(r[2]))
    return out


def _wrap_route(args):
    """Record the routed targets for the next window, with a receipted resident suggestion each.

    An unroutable id REFUSES rather than recording: a target nobody can work would make the
    night shift pre-chew for a task that does not exist and then report success -- a silent
    no-op that reads as a working job, which is the failure mode a manual prototype exists to
    catch before machinery hides it.
    """
    from core.coord.task_ledger import TaskLedger
    from core.learning.agent_memory import get_agent_memory

    ids = [t.strip().upper() for t in str(args.route or "").split(",") if t.strip()]
    if not ids:
        print("[wrap] --route needs at least one ledger id, e.g. --route T123,T124")
        return

    led = TaskLedger()
    try:
        led.load()
    except Exception:
        pass
    good, bad, lines = [], [], []
    for tid in ids:
        rec = None
        try:
            rec = led.get(tid)
        except Exception:
            rec = None
        if not rec:
            bad.append(tid)
            continue
        good.append(tid)
        title = str(rec.get("title") or "")
        lines.append(f"  {tid}  {title[:88]}")
        for callsign, agent, receipts in _suggest_resident(title)[:2]:
            lines.append(f"      SUGGEST {callsign} ({agent}) -- matched {len(receipts)} of its "
                         f"own lessons: {', '.join(receipts[:2])}")
        if not _suggest_resident(title):
            lines.append("      no resident archive matched -- route by hand")

    for tid in bad:
        print(f"[wrap] REFUSED to route {tid}: no such task in the ledger. A routed target "
              f"nobody can work would have the night shift pre-chew for nothing and report "
              f"success.")
    if not good:
        return

    print(f"\n[wrap] ROUTED for the next window ({len(good)} target(s)) -- suggestions only, "
          f"routing is yours:")
    for ln in lines:
        print(ln)

    if getattr(args, "commit", False):
        body = ("ROUTED TARGETS for the next window (T268). The night shift pre-chews these.\n\n"
                + "\n".join(lines))
        try:
            get_agent_memory().decide_with_retry("next-routing", _clip(body, 4000), curated=True)
            print(f"\n[OK] routing recorded -> note 'next-routing'; the next boot renders it.")
        except Exception as e:
            print(f"WARN: routing note not recorded ({type(e).__name__}: {e})")


def cmd_wrap(args):
    """Ambient session capture: distill this session's own commits + lessons + notes into a DRAFT
    where-we-are, so you APPROVE/correct instead of authoring blank. Preview by default; --commit
    records the draft as a note (supersede-by-title) so it surfaces at the next boot."""
    from datetime import datetime
    from core.learning.agent_memory import get_agent_memory

    # STANDING PRACTICE (2026-08-01): land any new corpus digests before distilling. A 59-agent
    # sweep produced 2,484 structured digests -- what each artifact IS, what it SETTLED, whether
    # it is ORPHANED, whether it claims a state it is not in, plus Daniil's words verbatim -- and
    # that output lived ONLY in .claude/ workflow scratch, which is the class of directory people
    # clean out. Landing it here is what makes the sweep a RATCHET instead of a one-off: digests
    # accumulate every wrap, so "what are we missing that we discussed before" stops requiring
    # another full read. Idempotent (dedupes by run+path) and fail-open -- a wrap must never be
    # blocked by an index refresh. Query with: py scripts/corpus_digests.py --themes
    try:
        import subprocess as _sp
        _r = _sp.run([sys.executable, str(Path(__file__).resolve().parent / "scripts" /
                                          "corpus_digests.py")],
                     capture_output=True, text=True, timeout=180)
        for _line in (_r.stdout or "").splitlines():
            if "new," in _line:
                print(f"[wrap] {_line.strip()}")
                break
    except Exception:
        pass

    commits = _recent_commits(args.hours or 12)
    lessons = _recent_lessons(8)
    notes = get_agent_memory().get_decisions(days=1)
    try:
        from core.recall.at_action import recent_flips, recent_injections
        flips = recent_flips(args.hours or 12)
        injections = recent_injections(args.hours or 12)
    except Exception:
        flips, injections = [], []
    draft = build_session_draft(commits, lessons, notes, flips=flips, injections=injections)
    # W37/B6: --grounding sets (or retires) the GROUND-FIRST pointer independently of the
    # commit -- the voice document the next seat reads before anything else. Tonight's
    # boots proved the pattern; this makes it substrate instead of an ad-hoc directive.
    if getattr(args, "grounding", None):
        mem_g = get_agent_memory()
        if str(args.grounding).strip().lower() == "none":
            # kimi (c): absence is DECLARED, never a silent forget.
            gp = next((d for d in mem_g.get_decisions(days=3650)
                       if d.title == "grounding-pointer" and not d.superseded), None)
            if gp is not None and mem_g.retire_decision(gp.id):
                print("[wrap] grounding pointer declared NONE this wrap -- retired "
                      f"(was {gp.decision[:80]}); the next seat boots without one, by choice.")
            else:
                print("[wrap] grounding declared none (no pointer was set).")
        else:
            try:
                g_id = mem_g.decide_with_retry("grounding-pointer",
                                               _clip(str(args.grounding), 400),
                                               curated=True)
                print(f"[wrap] grounding pointer set -> {args.grounding} (id {g_id}); "
                      "boot renders it GROUND FIRST with an age stamp.")
            except Exception as e:
                print(f"WARN: grounding pointer not recorded: {e}")
    # F4: --focus sets the CURRENT DIRECTIVE independently of the draft commit -- the whole
    # T268: ROUTE TOMORROW'S TARGETS. --focus records INTENT; this records WHICH ITEMS, which
    # is what an overnight pre-chew consumes. Found by running the first manual sleep shift:
    # its highest-value job could not run because nothing said what tomorrow was. Routing is a
    # PRECONDITION of precompute, not a property of the world -- the scheduler is us.
    if getattr(args, "route", None):
        _wrap_route(args)
    elif not getattr(args, "focus", None):
        # THE NUDGE. A rule that lives only in a document needs someone to remember it, which
        # is the failure this whole slice fixes. It names the CONSEQUENCE, not just the
        # omission -- an instruction without a reason is the checklist-fatigue shape -- and it
        # NEVER blocks: a hygiene prompt that can fail a wrap is one people route around.
        print("[wrap] no routing set for the next window -- the night shift cannot pre-chew "
              "without targets.\n"
              "       Set them with: py agent_cli.py wrap --route T123,T124 --commit")

    # point is to capture priority intent THE MOMENT it is decided, even on a bare wrap.
    if getattr(args, "focus", None):
        mem = get_agent_memory()
        try:   # RB-8: race-safe resolve+claim (the twin proved wrap is not single-writer)
            # T074 R8: setting the directive is a DELIBERATE act (feeds the whisper's
            # DIRECTIVE line) -- curated, unlike the mechanical draft below.
            f_id = mem.decide_with_retry("next-focus", _clip(args.focus, 1000), curated=True)
        except Exception as e:
            print(f"WARN: --focus note lost a title race and gave up: {e}")
            f_id = ""
        try:
            project_notes()
        except Exception:
            pass
        print(f"[OK] current directive set -> note 'next-focus' (id {f_id}); "
              "boot renders it ABOVE the NEXT list."
              if f_id else "WARN: --focus note not recorded (store unavailable?)")
    if not args.commit:
        print("# DRAFT where-we-are (review it; record with: py agent_cli.py wrap --commit "
              "-- the default title supersedes the prior where-we-are)\n")
        print(draft)
        print(f"\n# from {len(commits)} commit(s), {len(lessons)} lesson(s), {len(notes)} note(s) this session")
        try:   # T031 hook 3: the wrap-time M-practice scorecard (a reader, fail-open)
            import subprocess as _sp
            print()
            print(_sp.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "scripts", "arc_scorecard.py"),
                           "--days", str(max(1, (args.hours or 12)) / 24.0)],
                          capture_output=True, text=True, timeout=60).stdout.rstrip())
        except Exception:
            pass
        try:   # curator nudge (vNext loop 1): surface the bench bucket at the reflective moment
            from core.recall.curator import curation_report
            rep = curation_report()
            if rep.get("bench") or rep.get("unbench"):
                print(f"\n# [recall-curate] {len(rep['bench'])} lesson(s) are pure surface cost, "
                      f"{len(rep['unbench'])} earned their way back -> py agent_cli.py recall-curate --apply")
            if rep.get("forge_rollback") or rep.get("forge_confirm") or rep.get("forge_expire"):
                print(f"# [forge-watch] rollback {len(rep['forge_rollback'])} / confirm "
                      f"{len(rep['forge_confirm'])} / expire {len(rep['forge_expire'])} "
                      f"-> py agent_cli.py recall-curate --apply")
        except Exception:
            pass
        try:   # Forge F2 nudge: pending optimizer proposals want the human's eyes
            from core.recall.forge_optimizer import pending_proposals
            props = pending_proposals()
            if props:
                print(f"# [forge] {len(props)} optimizer proposal(s) pending review "
                      f"-> py agent_cli.py recall-curate --forge-proposals")
        except Exception:
            pass
        return 0
    # P1/T021: the default title is BARE on purpose -- a dated title defeats the
    # update-by-title supersession that wrap itself wires two lines below, which is
    # exactly how 4 co-active where-we-are notes accumulated (T016 F1a). The date
    # lives in the note's timestamp and the draft body, not the title.
    title = args.title or "where-we-are"
    mem = get_agent_memory()
    # T074 W7 wrap guard: a mechanical distillation must never SILENTLY supersede a
    # hand-curated head (the 2026-07-15 clobber incident). curated=True protects;
    # curated=None (legacy) does not -- the flag beats inference, both ways (R7).
    if not getattr(args, "force", False):
        cur = next((d for d in mem.get_decisions(days=365) if d.title == title), None)
        if cur is not None and getattr(cur, "curated", None) is True:
            from datetime import date as _date
            print(f"WARNING: the current '{title}' note is CURATED (hand-written). "
                  "This wrap draft is MECHANICAL and would overwrite it.\n"
                  "  To supersede deliberately: re-run with --force (review the draft first).\n"
                  f"  To record alongside:      py agent_cli.py wrap --commit --title "
                  f"\"{title}-{_date.today().isoformat()}\"\n"
                  "(nothing written)")
            return 1
    try:   # RB-8: race-safe resolve+claim replaces the read-title-then-write race
        # T074 W2: wrap output is a MECHANICAL distillation -- flag it so the whisper
        # renders (auto, Nh ago) and the Phase-2 guard can protect curated handoffs.
        dec_id = mem.decide_with_retry(title, draft, curated=False)
    except Exception as e:
        print(f"ERROR recording the wrapped note (title race): {e}"); return 1
    if not dec_id:
        print("ERROR recording the wrapped note"); return 1
    try:
        project_notes()
    except Exception:
        pass
    # W36 (the stale-directive ROOT CAUSE; claude+kimi consensus 2026-07-21): a landed
    # where-we-are RETIRES a next-focus OLDER than this wrap's own look-back window --
    # presumptively consumed by the session just wrapped. One set WITHIN the window is
    # fresh intent (possibly another seat's) and survives. kimi's blocking amendments:
    # (a) ORDERING -- this block runs only here, AFTER dec_id landed above; a wrap that
    # dies earlier never tombstones the only directive. (b) RECEIPT -- loud line below;
    # silent retirement is how one banner bit three seats. Scope: ONLY next-focus.
    # (--focus in this same call already superseded it with fresh intent up in F4.)
    if not getattr(args, "focus", None):
        try:
            nf = next((d for d in mem.get_decisions(days=3650)
                       if d.title == "next-focus" and not d.superseded), None)
            if nf is not None:
                cutoff = datetime.now() - __import__("datetime").timedelta(
                    hours=max(1, args.hours or 12))
                if datetime.fromisoformat(str(nf.created_at)) < cutoff:
                    if mem.retire_decision(nf.id):
                        try:
                            from core.events.event_log import capture_event
                            capture_event("decision",
                                          f"stale next-focus retired by wrap (W36): "
                                          f"superseded by where-we-are {dec_id}",
                                          agent_id="wrap",
                                          refs=[f"mem:decision:{nf.id}",
                                                f"mem:decision:{dec_id}"],
                                          detail={"retired": True, "successor": dec_id})
                        except Exception:
                            pass
                        print(f"[wrap] retired stale next-focus (id {nf.id}, "
                              f"{str(nf.created_at)[:10]}) -- consumed by this session; "
                              f"directive slot now empty. Set fresh intent: "
                              f"py agent_cli.py wrap --focus \"...\"")
        except Exception:
            pass   # the retire is a courtesy; the wrap itself already landed
    # W37 (kimi (b)): the kept-pointer rule is SPELLED, never silent -- a fresh pointer
    # (< GROUNDING_FRESH_DAYS) is kept with a receipt line; an old one keeps rendering
    # but the wrap says so loudly (re-point or declare none).
    if not getattr(args, "grounding", None):
        try:
            gp = next((d for d in mem.get_decisions(days=3650)
                       if d.title == "grounding-pointer" and not d.superseded), None)
            if gp is not None:
                from datetime import datetime as _dtg
                age_d = (_dtg.now() - _dtg.fromisoformat(str(gp.created_at))).days
                if age_d < GROUNDING_FRESH_DAYS:
                    print(f"[wrap] grounding pointer kept: {gp.decision[:80]} ({age_d}d old)")
                else:
                    print(f"[wrap] grounding pointer is {age_d}d old ({gp.decision[:60]}) -- "
                          "re-point with wrap --grounding <path>, or declare none with "
                          "--grounding none")
        except Exception:
            pass
    try:   # the helper owns the pointer; read back which prior this superseded
        raw = mem.store.hget(mem.KEY_DECISIONS, dec_id)
        superseded_prior = (json.loads(raw) or {}).get("supersedes") if raw else None
    except Exception:
        superseded_prior = None
    print(f"[OK] wrapped this session -> note '{title}' (id {dec_id})"
          + (f" - superseded prior {superseded_prior}" if superseded_prior else "")
          + "\n     surfaces at your next `boot`; edit by re-noting the same title.")
    return 0


def cmd_stats(args):
    """The recall-value funnel (leapfrog T3): is surfaced knowledge actually HELPING, and are
    earned lessons being CAPTURED? Computation lives in core/recall/funnel.py (shared with the
    boot pulse + SessionStart whisper); this renders it. --days N adds a per-day trend from
    DURABLE records (flip events + lesson timestamps) and the 30d pace vs the Wave-A gate.
    --silence renders the R2 denominator (fired/silent/by_reason) + the pack-replay tallies --
    the census bar's numbers, on the door agents already use (capability_without_a_door)."""
    import json as _json
    if getattr(args, "silence", False):
        from core.recall.at_action import silence_rate
        s = silence_rate(window_s=float(args.hours or 24) * 3600)
        if args.json:
            print(_json.dumps(s, indent=1)); return 0
        n = max(1, s["calls"])
        print(f"# RECALL SILENCE (R2 denominator, last {args.hours or 24}h)")
        print(f"  calls {s['calls']} | fired {s['fired']} | silent {s['silent']} "
              f"({100 * s['silent'] // n}% -- census floor: >=27% once the gate lands)")
        for r, c in sorted((s.get("by_reason") or {}).items(), key=lambda kv: -kv[1]):
            print(f"    {r:18} {c}")
        if s["calls"] == 0:
            print("  (no rows -- calls==0 is 'nothing recorded', NOT '0% silent')")
        print("  pack replay (frozen-30 vs the reconciled bar): py -m core.recall.pack_replay")
        return 0
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
        # T253: the denominator counts EVERY surfacing while the numerator needs someone to
        # have acted, so this is dominated by feedback COVERAGE, not by quality. Measured
        # 2026-08-08: only 327 of 6805 surfacings were ever voted on -- 95.2% unlabelled, not
        # negative -- and of those judged, 87% were positive. Reported with that split beside
        # it, because the bare figure was quoted as a verdict on the corpus and misled its own
        # author. The label stays so the historical series remains comparable.
        _v, _n = out["votes"]["useful"], out["votes"]["noise"]
        _judged = _v + _n
        print(f"  value rate ((useful+helped)/surfaced): {out['value_rate'] * 100:.1f}%"
              " -- COVERAGE-dominated, not a quality verdict")
        if out["surfaced_impressions"] and _judged:
            print(f"    of which judged at all: {_judged}/{out['surfaced_impressions']}"
                  f" ({_judged / out['surfaced_impressions'] * 100:.1f}%) -- the rest is"
                  " UNLABELLED, not negative")
            print(f"    of those judged: {_v}/{_judged} ({_v / _judged * 100:.0f}%) rated useful"
                  " -- self-selected votes, so read as a sample")
    print(f"  lessons with a track record (helped or useful > 0): {out['lessons_with_track_record']}")

    # T253: the honest successor, deliberately printed NEXT TO the figure it corrects. This one
    # can only move if the system actually prevents something -- and it is a FLOOR, never a rate.
    try:
        from core.learning.learning_store import get_learning_store
        _rep = get_learning_store().repeat_report()
        if _rep["count"]:
            print(f"  REPEATS (lesson existed, mistake happened anyway): {_rep['count']}"
                  "  -- a FLOOR: only what someone noticed, never a rate")
            for _name, _n in _rep["most_violated"][:3]:
                print(f"    {_n}x  {_name}")
            if _rep["by_recall_outcome"]:
                print(f"    by what recall did: {_rep['by_recall_outcome']}"
                      "  (fired = reading failure; suppressed = targeting failure)")
        else:
            print("  REPEATS: none recorded yet -- `learn <you> --repeat-of <lesson>` when a"
                  " lesson you already had gets violated again")
    except Exception:
        pass
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


def write_last_session_draft(path, commits, lessons, notes, trigger="", flips=None, injections=None):
    """Write a session draft to a FILE (not a note) -- the auto-capture target for the SessionEnd/
    PreCompact hook, so an abrupt end still leaves a trail. boot surfaces a pointer; you promote it
    with `wrap --commit` only if it's worth keeping. Returns the path, or None if there was no activity."""
    from datetime import datetime
    draft = build_session_draft(commits, lessons, notes, flips=flips, injections=injections)
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
                print(f"  [{e.get('kind', '?')}] {render_iso(e.get('at', ''), tz='local')}  "
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
    Bifrost UI renders against (docs/library/design/20260701_session-bookends-design-for-peer-review_c38e0c.md §6). Usage:
      py agent_cli.py episode current --json
      py agent_cli.py episode close [--accept-title T --accept-desc D --accept-why W] --json
      py agent_cli.py episode accept <chapter_id> [--title T --desc D --why W] --json
    """
    from core.narrative import episode as ep
    act = args.action
    if act == "current":
        out = ep.current_episode()
        try:   # S3: the door composes the advisory suggestion (episode.py stays one-way, fail-soft)
            from core.narrative.episode_suggester import suggest
            if out.get("current_chapter"):
                out["current_chapter"]["suggestion"] = suggest()
        except Exception:
            pass
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


# ------------------------------------------------------------------------ task (coordination door)
def cmd_task(args):
    """The task-lifecycle door over the governed ledger -- surfaces core/coord/conductor.py through the
    ONE door so agents manage tasks (propose/approve/claim/start/verify/done/block/list/next) via
    agent_cli instead of a hidden standalone script (the one-door / interface-is-the-product principle;
    the read path was already on the door via boot, this closes the write path). Delegates verbatim to
    conductor's own CLI parser -- zero duplication, single source of truth for the task verbs."""
    from core.coord import conductor
    return conductor.main(list(args.rest or []))


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
              '--task "finish C3 threshold tuning" --note "see docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_302fc9.md"')
        return 2

    from core.signals.coordinator_api import SignalEmitter
    clipped = []
    ctx = {}
    if (args.note or "").strip():
        ctx["note"] = _intake(args.note, 1000, "note", clipped)
    blockers = [b.strip() for b in (args.blocker or "").split("||") if b.strip()]
    try:
        em = SignalEmitter(_clip(args.agent_id, 200))
        em.emit_handoff_to_target_agent(to_agent, _intake(task, 500, "task", clipped),
                                        context=ctx, blockers=blockers)
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
        print(json.dumps({"recorded": ok, "from": args.agent_id, "to": to_agent, "task": task,
                          "clipped": clipped or None}))
    else:
        print(f"[{'OK' if ok else 'FAIL'}] handoff {args.agent_id} -> {to_agent}: {_clip(task, 80)}")
        print(f"  (the target's next `boot` will surface this as its briefing)")
        for c in clipped:   # RB-5: the door's RESULT carries the clip, never silent
            print(c)
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
        at = render_iso(e.get("at", ""), tz="local")   # T119: the one display door, frame labeled
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
        o = get_event_log().capture(args.kind or "note", args.summary or "",
                                    detail=detail, agent_id=args.agent, refs=refs,
                                    track=args.track)
        # T179: three states, so the render has three. This used to read dict-or-None and print
        # FAIL for anything that was not a clean dict -- including a write that LANDED with a
        # convenience index behind. Reporting a stored event as lost is the defect being fixed;
        # repeating it at the door would just move it.
        state = "OK" if o else ("PARTIAL" if o.partial else "FAIL")
        if args.json:
            print(json.dumps({"ok": o.ok, "partial": o.partial, "why": o.why,
                              "ref": o.ref, "event": o.detail}, default=str))
        else:
            print(f"[{state}] captured {args.kind or 'note'}: "
                  f"{_clip(args.summary or '', 80)}" + (f"  -> {o.ref}" if o.ref else ""))
            if o.why:
                print(f"  {o.why}")
        return 0 if o.ok else 1

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

    # --get: resolve one followable pointer (RB-7: a miss says WHETHER the payload aged
    # out of the bounded firehose -- an evicted drill target must never read as blank truth)
    if args.get:
        ev, why = eq.resolve(args.get)
        if not ev:
            print(f"ERROR: {why}")
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
                      f"# {len(res['events'])} raw event(s) in {render_iso(sp['start'], tz='local')} "
                      f"-> {render_iso(sp['end'], tz='local')}")
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
    """Query durable salient Bifrost messages (kind=bifrost_msg in the event firehose).
    P6 (T026): each message shows who HANDLED it; salient-and-unacked past the threshold
    renders an UNHANDLED flag -- promoted-and-forgotten was the disease."""
    import time as _time
    from core.comm.promoter import promoted_page, unhandled_threshold_hours
    from agent.bifrost_pull import format_promoted_events
    hours = unhandled_threshold_hours()   # RB-5: the ONE seam; boot reads the same one
    evs, more = promoted_page(limit=args.limit or 20, since=args.since, until=args.until,
                              with_acks=True, now=_time.time(), unhandled_hours=hours)
    if args.json:
        print(json.dumps(evs, indent=2, default=str)); return 0
    print(format_promoted_events(evs, json_out=False))
    if more:   # RB-5: a full page confesses the window instead of under-reporting
        print(f"  (+ older salient records beyond this page -- raise --limit)")
    flagged = [e for e in evs if e.get("unhandled")]
    acked = [e for e in evs if e.get("acks")]
    for e in acked:
        ref = str(e.get("refs", [""])[0])
        who = ", ".join(f"{a['by']} @ {render_iso(a['at'], tz='local')}" for a in e["acks"])
        print(f"  [acked] {ref}: {who}")
    if flagged:
        print(f"\n  !! {len(flagged)} UNHANDLED salient message(s) older than {hours}h "
              "(no msg_ack -- handle it, then: py agent_cli.py bifrost-ack <msg_id>):")
        for e in flagged:
            print(f"     {str(e.get('refs', [''])[0])}  ({e.get('age_hours', 0):.0f}h)  "
                  f"{_clip(str(e.get('summary', '')), 90)}")
    return 0


def cmd_doctor_deploy() -> int:
    """Is THIS machine a working deploy? One hop, before anything else is believed.

    Written after a deploy at a second machine failed: the repo carried 710 hardcoded absolute
    paths, AI_SETUP was never set on ANY machine including the original, and the symptom was a
    scatter of unrelated tracebacks rather than one legible answer. A fresh machine should be
    able to ASK what is wrong instead of discovering it one failure at a time.
    """
    from core.paths import repo_root, env_override_is_wrong
    root = repo_root()
    bad = []
    env_set = bool((os.getenv("AI_SETUP") or "").strip())
    print("# DEPLOY CHECK")
    print("  repo root      : %s" % root)
    print("  derived from   : %s" % ("AI_SETUP env" if env_set else "this file (nothing to configure)"))

    warn = env_override_is_wrong()
    if warn:
        bad.append("AI_SETUP is set but wrong -- %s. It is being IGNORED (the root above was "
                   "derived instead), so anything reading AI_SETUP directly disagrees with "
                   "everything reading core.paths." % warn)

    for name in ("agent_cli.py", "core", "scripts", "tests", "AGENTS.md"):
        ok = (root / name).exists()
        print("  %-14s : %s" % (name, "ok" if ok else "MISSING"))
        if not ok and name != "AGENTS.md":
            bad.append("%s missing from the repo root -- this is not a complete checkout" % name)

    try:
        from core.comm.bus import get_bus
        get_bus("control")._client.ping()
        print("  redis          : reachable")
    except Exception as e:
        print("  redis          : UNREACHABLE (%s)" % type(e).__name__)
        bad.append("Redis unreachable -- bus, roster, mailbox and locks are all dead without "
                   "it. Start it before judging anything else on this list.")

    # WRITE-EDGE ENFORCEMENT. The hooks are tracked, but git only runs them if core.hooksPath
    # points at them -- a one-line per-clone config that shipped and was never run here, which
    # is why every architecture gate was CI-only and CI sat red for 30 days unnoticed.
    try:
        import subprocess as _sp
        _cfg = _sp.run(["git", "config", "core.hooksPath"], capture_output=True, text=True,
                       cwd=str(root), stdin=_sp.DEVNULL, close_fds=True).stdout.strip()
    except Exception:
        _cfg = ""
    _hooked = _cfg.replace(chr(92), "/").endswith("scripts/githooks")
    print("  git hooks      : %s" % ("installed" if _hooked else "NOT INSTALLED"))
    if not _hooked:
        bad.append("core.hooksPath is not set, so the pre-commit gates never run -- violations "
                   "reach CI instead of being refused at the commit. Fix: "
                   "py scripts/githooks/install_git_hooks.py")

    quiet = root / "scripts" / "quiet"
    pp = [x for x in (os.getenv("PYTHONPATH") or "").split(os.pathsep) if x.strip()]
    on_path = any(os.path.normcase(os.path.normpath(x)) == os.path.normcase(str(quiet))
                  for x in pp)
    print("  no-console fix : %s" % ("active" if on_path else "NOT on PYTHONPATH"))
    if (quiet / "sitecustomize.py").exists() and not on_path:
        bad.append("scripts/quiet is not on PYTHONPATH, so child processes pop console windows "
                   "that steal focus. Add PYTHONPATH=%s to the env block of BOTH "
                   ".claude/settings.json files (repo AND user-level)." % quiet)

    print("")
    if not bad:
        print("DEPLOY OK -- nothing blocking.")
        return 0
    print("%d PROBLEM(S):" % len(bad))
    for b in bad:
        print("  - %s" % b)
    return 1


def cmd_doctor(args):
    if getattr(args, 'deploy', False):
        return cmd_doctor_deploy()
    """L2 (T030): the fleet doctor -- reads worklive + the progress pulse + backlogs and
    grades findings per the reconciled paging table (page: hard_wedge, aged stall;
    banner: frozen; dashboard: the rest). Healthy fleet = one line."""
    from core.comm.doctor import examine_fleet, known_agents, examine_services
    agents = [a.strip() for a in (args.agents or "").split(",") if a.strip()] or None
    rep = examine_fleet(agents, page_notes=bool(args.page))
    try:   # T081-W3: fleet-infrastructure services (what's running?), distinct from agent findings
        rep["services"] = examine_services()
    except Exception:
        rep["services"] = []
    if getattr(args, "progress", False):
        from core.comm.turn_metrics import progress_view
        for a in (agents or rep["agents"] or known_agents()):
            v = progress_view(a)
            if not v:
                print(f"{a}: idle")
                continue
            eta = v.get("eta") or {}
            eta_txt = (f"{v['elapsed_s']}s/{eta['median_s']}s" if eta
                       else f"{v['elapsed_s']}s/...")
            pct = v.get("pct_estimate")
            conf = f" ({v['ask_kind']}, {eta.get('confidence', 'no history')})" if eta \
                else f" ({v['ask_kind']}, n<3: elapsed only)"
            print(f"{a}: {eta_txt}  {str(pct) + '%' if pct is not None else '--%'}  "
                  f"pts={v['points_seen']}{conf}")
    if args.json:
        print(json.dumps(rep, indent=2, default=str)); return 0
    print(rep["summary"])
    for f in rep["findings"]:
        print(f"  [{f['grade']:^9}] {f['line']}")
        print(f"              drill: {f['drill']}")
    svcs = rep.get("services") or []
    if svcs:
        print("## SERVICES (fleet infrastructure -- what's running)")
        for f in svcs:
            print(f"  [{f['grade']:^9}] {f['line']}")
            if f.get("drill"):
                print(f"              start: {f['drill']}")
    try:   # W54 (kimi F3): the activation gauge -- organ claims read the instrument, not anecdotes
        from core.recall.at_action import injections_by_family
        print("## ACTIVATION (recall injections by lesson family, 24h)")
        print(f"  {_family_gauge_render(injections_by_family(24.0))}")
    except Exception:
        pass
    try:   # T151: a time-box must be a DEADLINE, not a trapdoor. resolve() drops an expired grant
        from core.trust.registry import expiring_grants   # to quarantined, and nothing ever said so
        _exp = expiring_grants(within_h=72.0)
        if _exp:
            print("## GRANTS LAPSING (security/acl.json -- an expired grant silently quarantines)")
            for _g in _exp:
                _state = "EXPIRED -- now quarantined" if _g["expired"] else f"{_g['hours_left']}h left"
                print(f"  [{'  page   ' if _g['expired'] else 'dashboard'}] {_g['agent_id']}: "
                      f"{_state} (expires {_g['expires_at']})")
            print("              drill: edit the record in security/acl.json -- renew by editing, "
                  "never by letting it lapse")
    except Exception:
        pass
    return 0


def cmd_lookback(args):
    """P7 (T027): one question over the rationale corpus -- the strategic WHY, layered and
    drillable. Temporal drill (story/events) answers what happened; this answers why it is
    the way it is: docs (currency-labeled) -> research/reviewed -> notes (incl. retired) ->
    promoted bus -> chapters -> git bodies, each hit with its drill pointer."""
    from core.recall.lookback import lookback
    question = " ".join(args.question or [])
    layers = [s.strip() for s in (args.layers or "").split(",") if s.strip()] or None
    hits = lookback(question, per_layer=args.per_layer or 3, layers=layers)
    if args.json:
        print(json.dumps(hits, indent=2, default=str)); return 0
    if not hits:
        print(f"# lookback: nothing above the relevance floor for: {question!r}\n"
              "  (try different terms; layers: docs,research,notes,promoted,chapters,git)")
        return 0
    print(f"# lookback: {question}")
    current_layer = None
    for h in hits:
        if h["layer"] != current_layer:
            current_layer = h["layer"]
            print(f"\n## {current_layer}")
        print(f"  [{h['status']}] {h['source']}  (rel {h['score']})")
        print(f"      {h['excerpt']}")
        print(f"      drill: {h['drill']}")
    return 0


def cmd_knowledge_map(args):
    """R8 (T059): WALK the knowledge neighborhood of a topic instead of querying it blind.
    lookback returns a flat ranked list; this returns a graph -- surface hits (L1), the
    one-hop neighborhood reached by WALKING the related_to edges the system already grows
    (L2, both directions), and the on-topic archive of retired/superseded records (L3).
    Each node carries a drill pointer; neighborhood nodes name the edge that reached them."""
    from core.recall.knowledge_map import knowledge_map
    topic = " ".join(args.query or []) if isinstance(args.query, list) else (args.query or "")
    topic = topic.strip()
    m = knowledge_map(topic, per_layer=args.per_layer or 6)
    if args.json:
        print(json.dumps(m, indent=2, default=str)); return 0
    if not topic:
        print("# knowledge-map: give a topic to walk (e.g. 'lanes', 'wedge', 'supersession')")
        return 0
    c = m["counts"]
    print(f"# KNOWLEDGE MAP: {topic}   "
          f"({c['surface']} surface | {c['neighborhood']} neighborhood | {c['archive']} archive)")
    if not (m["surface"] or m["neighborhood"] or m["archive"]):
        print("  (nothing above the relevance floor -- try different terms)")
        return 0

    def _row(n, indent="  "):
        edge = f" +{n['edge_count']} edges" if n.get("edge_count") else ""
        rel = f" (rel {n['score']})" if n.get("score") is not None else ""
        print(f"{indent}[{n['kind']}:{n['status']}] {n['title']}{rel}{edge}")
        if n.get("via"):
            v = n["via"]
            arrow = "<--" if v["direction"] == "in" else "-->"
            matched = f" [{','.join(v['matched'])}]" if v.get("matched") else ""
            print(f"{indent}    via {v['from']} {arrow}{matched}")
        print(f"{indent}    {n['excerpt']}")
        print(f"{indent}    drill: {n['drill']}")

    if m["surface"]:
        print("\n## L1 surface -- direct topic hits")
        for n in m["surface"]:
            _row(n)
    if m["neighborhood"]:
        print("\n## L2 neighborhood -- one hop along the edges (relevance alone can't reach these)")
        for n in m["neighborhood"]:
            _row(n)
    if m["archive"]:
        print("\n## L3 archive -- on topic but retired/superseded (reachable, not live)")
        for n in m["archive"]:
            _row(n)
    return 0


def cmd_fence(args):
    """R2 (T053): the fence as a first-class workspace, not a naming convention. Slots
    (brief / half_a / half_b / reconciliation) with tool-derived paths -- a confabulated
    filename is unrepresentable -- and the method contract's mechanical checks (M1-BRIEF
    sections, M1-CF verdict tags, M1-PV citation verify, seal order, author independence)
    run AT SEAL TIME. Actions: open / write / seal / pv / status / list."""
    from core.coord import fence_workspace as fw
    action = args.action

    def _emit(obj):
        print(json.dumps(obj, indent=2, default=str) if args.json else obj)

    if action == "list":
        rows = fw.list_fences()
        if args.json:
            print(json.dumps(rows, indent=2, default=str)); return 0
        if not rows:
            print("# no fences yet (fence open <id> --question ...)"); return 0
        for st in rows:
            sealed = [s for s, v in st["slots"].items() if v["sealed"]]
            print(f"  [{'CLOSED' if st['closed'] else 'open'}] {st['id']} ({st['tier']}) "
                  f"-- {st['question'][:60]}  sealed: {','.join(sealed) or '-'}")
        return 0
    if not args.fence_id:
        print("ERROR: this action needs a fence id"); return 1
    if action == "open":
        st = fw.open_fence(args.fence_id, question=args.question or "",
                           tier=args.tier or "full", by=args.by or "")
        print(f"[OK] fence {st['id']} open ({st['tier']}) at "
              f"{fw.slot_path(args.fence_id, 'brief')}")
        return 0
    if action == "write":
        if not args.slot:
            print("ERROR: write needs --slot"); return 1
        text = args.text or ""
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        if not text:
            print("ERROR: write needs --text or --file"); return 1
        p = fw.write_slot(args.fence_id, args.slot, text, by=args.by or "")
        print(f"[OK] wrote {args.slot} -> {p}")
        return 0
    if action == "seal":
        if not args.slot:
            print("ERROR: seal needs --slot"); return 1
        ok, problems = fw.seal(args.fence_id, args.slot, by=args.by or "")
        if ok:
            print(f"[OK] sealed {args.fence_id}/{args.slot}")
            return 0
        print(f"REFUSED: {args.fence_id}/{args.slot} cannot seal:")
        for pr in problems:
            print(f"  - {pr}")
        return 1
    if action == "pv":
        report = fw.run_pv(args.fence_id)
        print(f"# M1-PV over {args.fence_id}: {len(report['verified'])} verified, "
              f"{len(report['missing'])} MISSING")
        for c in report["missing"]:
            print(f"  MISSING: {c}")
        return 0 if not report["missing"] else 1
    if action == "status":
        st = fw.fence_status(args.fence_id)
        if args.json:
            print(json.dumps(st, indent=2, default=str)); return 0
        print(f"# fence {st['id']} ({st['tier']}) -- {st['question']}")
        for s, v in st["slots"].items():
            mark = "SEALED" if v["sealed"] else ("written" if v["written"] else "empty")
            by = f" by {v['author']}" if v["author"] else ""
            print(f"  {s:16} {mark}{by}")
        pv = st.get("pv")
        pv_line = "not run" if not pv else f"{pv['missing_count']} missing @ {pv['ran_at']}"
        print(f"  pv: {pv_line}")
        print(f"  closed: {st['closed']}")
        return 0
    print(f"ERROR: unknown fence action {action!r}"); return 1


def cmd_flow(args):
    """R3 (T054): OTel-style waterfall of recent message flows across lanes. lookback
    answers WHY, knowledge-map answers WHAT'S NEAR -- this answers WHAT HAPPENED: which
    ask produced which answer, on which lane, with what gap, and whether one logical
    message arrived MORE than once (double-delivery renders as xN COPIES, never N rows)."""
    from core.comm.flow_trace import flow_trace
    unit = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    w = str(args.window or "6h").strip().lower()
    try:
        window_ms = int(float(w[:-1]) * unit[w[-1]]) if w and w[-1] in unit else int(w) * 60_000
    except Exception:
        print(f"ERROR: bad --window {args.window!r} (use e.g. 30m, 6h, 1d)"); return 1
    out = flow_trace(args.agent, window_ms=window_ms)
    if args.json:
        print(json.dumps(out, indent=2, default=str)); return 0
    if out.get("offline"):
        print("# flow: bus offline (Redis unreachable)"); return 1

    def _dups(node):
        return (1 if node["copies"] > 1 else 0) + sum(_dups(c) for c in node["children"])

    c = out["counts"]
    dup_nodes = sum(_dups(f["root"]) for f in out["flows"])
    who = f" touching {args.agent}" if args.agent else ""
    print(f"# FLOW TRACE -- last {w}{who}   ({c['flows']} flow(s) | {c['nodes']} msg(s) | "
          f"{c['copies']} observed | {dup_nodes} duplicated | window dropped {c['dropped_by_window']})")
    if not out["flows"]:
        print("  (no flows in the window -- widen --window or check the bus)")
        return 0

    def _fmt_ms(ms):
        if ms < 1000:
            return f"+{ms}ms"
        s = ms / 1000.0
        if s < 60:
            return f"+{s:.1f}s"
        m, sec = divmod(int(s), 60)
        if m < 60:
            return f"+{m}m{sec:02d}s"
        h, m2 = divmod(m, 60)
        return f"+{h}h{m2:02d}m"

    def _row(n, depth):
        pad = "  " * depth
        off = "0ms" if not n["offset_ms"] else _fmt_ms(n["offset_ms"])
        dup = f"  x{n['copies']} COPIES" if n["copies"] > 1 else ""
        miss = f"  (answers {n['answers_missing']} -- outside window)" if n.get("answers_missing") else ""
        kb = f"{n['len'] / 1024:.1f}KB" if n["len"] >= 1024 else f"{n['len']}B"
        print(f"  {pad}{off:>9}  [{','.join(n['lanes'])}] {n['frm']} -> {n['to']}  "
              f"{n['kind']}  {kb}{dup}{miss}")
        if n.get("snippet"):
            print(f"  {pad}           {n['snippet']!r}")
        for ch in n["children"]:
            _row(ch, depth + 1)

    for fl in out["flows"][:args.limit]:
        span = _fmt_ms(fl["span_ms"]).lstrip("+") if fl["span_ms"] else "single"
        print(f"\n[flow {fl['flow']}]  {fl['nodes']} msg, span {span}")
        _row(fl["root"], 0)
    hidden = len(out["flows"]) - min(len(out["flows"]), args.limit)
    if hidden:
        print(f"\n  (+{hidden} more flow(s) -- raise --limit)")
    return 0


def _ack_refusal_hint(raw_ref: str, resolution_failed: bool) -> str:
    """T063: the id-form hint, gated on RESOLUTION FAILURE only (kimi fence-lite finding 1).
    A hex ref that RESOLVED but was refused by the verdict gets NO form hint -- the verdict's
    own reason (not promoted / quarantined / wrong addressee) is the true cause."""
    import re as _re
    if resolution_failed and _re.fullmatch(r"[0-9a-f]{6,40}", str(raw_ref or "")):
        return (" (note: that looks like a MAILBOX sha ref and no matching message "
                "resolved -- the message may be evicted, or the ref is truncated; "
                "try the full stream id from promoted/xrange)")
    return ""


def cmd_bifrost_ack(args):
    """P6 (T026): durably record that YOU handled a salient bus message. Read != handled --
    consuming advances a cursor; this records an actor and a moment. RB-2 (T029): only the
    ADDRESSEE settles an ask -- self-ack, third-party spoof, quarantined ids, and unpromoted
    messages are all refused at promoter.ack_verdict, the single rule guarding every caller
    (the old guard here scanned a 200-message page under try/except and could be
    volume-defeated)."""
    from core.comm.promoter import ack, ack_verdict, resolve_ack_ref
    # T063 COMPLETE: the door accepts EVERY id form its sibling verbs print -- the raw
    # stream id, the unhandled-warning's 'bifrost:<id>', and the MAILBOX's sha prefix
    # (resolved via mailbox.explain). Pin: tests/test_t063_ack_ref_roundtrip.py.
    raw = str(args.msg_id)
    mid = resolve_ack_ref(args.agent_id, raw)
    resolution_failed = mid is None
    if mid is None:
        mid = raw[len("bifrost:"):] if raw.startswith("bifrost:") else raw
    allowed, why = ack_verdict(args.agent_id, mid)
    if not allowed:
        # kimi fence-lite finding 1: the hint fires ONLY when resolution FAILED. When a sha
        # ref RESOLVED but the verdict refuses, the refusal is a CONTENT/permission verdict
        # and blaming the id form would launder it into the very misleading-error class this
        # door exists to kill.
        print(f"ERROR: ack refused -- {why}{_ack_refusal_hint(raw, resolution_failed)}")
        return 1
    ok = ack(args.agent_id, mid, note=args.note or "")
    if args.json:
        print(json.dumps({"acked": ok, "msg_id": mid, "by": args.agent_id})); return 0 if ok else 1
    print(f"[OK] {args.agent_id} acked bifrost:{mid}" if ok
          else "ERROR recording ack (event log unavailable?)")
    return 0 if ok else 1


def cmd_console_log(args):
    """Query durable console control-plane events (interjection/bus_control/file_drop -> Ledger)."""
    from core.comm.promoter import console_events
    from agent.bifrost_pull import format_console_events
    evs = console_events(limit=args.limit or 20, since=args.since, until=args.until)
    print(format_console_events(evs, json_out=bool(args.json)))
    return 0


def cmd_season_score(args):
    """T165: score a Season 1 round, or diff the two rule sets over the same input.

    The rules used to live only in a markdown table, so nothing could execute them and the W2
    refinements could not be COMPARED -- both the old and the new were prose. `--compare` is the
    artifact the operator actually rules on: identical claims, both policies, the delta and the
    rank change. A decision needs a diff on real data, not two paragraphs that both sound fine.
    """
    from core.season import scoring

    if args.policies:
        for name, p in scoring.POLICIES.items():
            default = "  [DEFAULT]" if name == scoring.DEFAULT_POLICY else "  [PROPOSED]"
            print(f"\n## {name}{default}\n{p['notes']}")
        return 0

    claims, verifications, uptime, fixed = [], [], {}, set()
    if args.round_file:
        doc = json.loads(io.open(args.round_file, encoding="utf-8").read())
        claims = doc.get("claims", [])
        verifications = doc.get("verifications", [])
        uptime = doc.get("uptime", {}) or {}
        fixed = set(doc.get("fixed_keys", []) or [])
    if not claims:
        print("season-score: no claims (pass --round-file <json> or --policies)")
        return 2

    if args.compare:
        out = scoring.compare(claims, verifications, uptime=uptime, fixed_keys=fixed)
        if args.json:
            print(json.dumps(out, indent=2))
            return 0
        print("## SCORING POLICY DIFF -- same claims, both rule sets")
        for p in sorted(set(out["v1_doc"]) | set(out["v2_aixcc"])):
            print(f"  {p:<16} v1={out['v1_doc'].get(p,0):>5}  v2={out['v2_aixcc'].get(p,0):>5}  "
                  f"delta={out['delta'].get(p,0):>+5}")
        print(f"\n  rank v1_doc  : {' > '.join(out['rank_v1'])}")
        print(f"  rank v2_aixcc: {' > '.join(out['rank_v2'])}")
        if out["rank_v1"] != out["rank_v2"]:
            print("  ^ the proposals CHANGE THE ORDER -- this is the decision, not a tuning knob")
        return 0

    res = scoring.score_round(claims, verifications, policy=args.policy,
                              uptime=uptime, fixed_keys=fixed)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print(f"## ROUND SCORE (policy {res['policy']}, {res['unscored']} unscored)")
    for p, pts in sorted(res["totals"].items(), key=lambda kv: -kv[1]):
        print(f"  {p:<16} {pts:>5}")
    for c in res["claims"]:
        if not c["scored"]:
            print(f"  [unscored] {c['player']} {c['dedupe_key']}: {c['reason']}")
    return 0


def cmd_grant(args):
    """S-3: the ACL write door (T163). Replaces "go edit security/acl.json by hand".

    HONEST SCOPE, repeated here because this is the surface an operator reads: --by is a string,
    and anyone who can run this CLI can already edit the JSON. This door is not authentication.
    What it buys is that every grant is atomic, schema-validated, time-boxed unless someone said
    otherwise out loud, carries a reason, and can be undone with --revoke instead of an edit.
    """
    from core.trust import grant_writer

    def _emit(payload):
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0

    if args.list or (not args.agent_id and not args.revoke):
        rows = grant_writer.listing()
        if args.json:
            return _emit(rows)
        print(f"## GRANTS ({len(rows)}) -- source of truth: security/acl.json")
        for g in rows:
            exp = g.get("expires_at") or "permanent"
            print(f"  {str(g.get('agent_id')):<22} {str(g.get('role')):<12} {exp:<22} "
                  f"by={g.get('granted_by')}")
            if g.get("reason"):
                print(f"      {str(g['reason'])[:110]}")
        return 0

    if not args.agent_id:
        print("grant: name the agent (or pass --list)")
        return 2

    try:
        if args.revoke:
            out = grant_writer.revoke(args.agent_id, by=args.by, reason=args.reason or "")
            if args.json:
                return _emit(out)
            print(f"[grant] REVOKED {args.agent_id} (was {out['was'].get('role')}) by {args.by}")
            return 0

        caps = [c.strip() for c in args.caps.split(",") if c.strip()] if args.caps else None
        scope = ([s.strip() for s in args.path_scope.split(",") if s.strip()]
                 if args.path_scope else None)

        if args.dry_run:
            # Build nothing, write nothing -- just say what would land. Deliberately does not
            # run the guards: a dry run that passed while the real call would be REFUSED would
            # be worse than no preview, so this prints the intent and names its own limit.
            print(json.dumps({"agent_id": args.agent_id, "role": args.role, "by": args.by,
                              "hours": args.hours, "permanent": bool(args.permanent),
                              "caps": caps, "path_scope": scope,
                              "reason": args.reason}, indent=2))
            print("[grant] DRY RUN -- nothing written. Authority guards run on the real call.")
            return 0

        rec = grant_writer.grant(args.agent_id, role=args.role, by=args.by,
                                 reason=args.reason or "", hours=args.hours,
                                 permanent=bool(args.permanent), caps=caps, path_scope=scope,
                                 request_ref=args.request_ref)
        if args.json:
            return _emit(rec)
        print(f"[grant] {rec['agent_id']} -> {rec['role']} "
              f"({rec['expires_at'] or 'permanent'}) by {rec['granted_by']}")
        return 0
    except (PermissionError, ValueError) as e:
        print(f"grant REFUSED: {e}")
        return 2


def cmd_resident(args):
    """T258: the callsign ceremony's door -- nominate, ratify, show.

    The registry refuses a self-nomination and a receipt the nominee did not author, so those
    rules are enforced HERE at the door rather than by anyone remembering them. Refusals exit
    nonzero and print WHY, because a refusal that does not say why trains the reader to route
    around it.
    """
    from core.fleet import residents as R
    sub = getattr(args, "sub", "") or "show"

    if sub == "nominate":
        try:
            rec = R.nominate(nominee=args.nominee, callsign=args.callsign,
                             receipts=list(args.receipt or []), by=args.by,
                             vendor=args.vendor, family=args.family, team=args.team,
                             number=(int(args.number) if args.number is not None else None),
                             note=args.note)
        except ValueError as e:
            print(f"[resident] {e}")
            return 1
        print(f"[resident] nominated {rec['agent_id']} as '{rec['callsign']}' by {rec['by']}")
        print(f"           receipts: {', '.join(rec['receipts'])}")
        print(f"           NOT yet active -- rule 3, a human ratifies: "
              f"py agent_cli.py resident ratify {rec['agent_id']} --callsign {rec['callsign']} --by <you>")
        return 0

    if sub == "ratify":
        try:
            rec = R.ratify(nominee=args.nominee, callsign=args.callsign, by=args.by)
        except ValueError as e:
            print(f"[resident] {e}")
            return 1
        print(f"[resident] RATIFIED: {R.designation(rec['agent_id'])}")
        # The ratifier must SEE what they signed -- with two drafts on one callsign, the
        # receipts are the only thing that distinguishes them (T258 review, point 4).
        print(f"           receipts confirmed: {', '.join(rec.get('receipts') or [])}")
        prior = (R.get(rec["agent_id"]) or {}).get("formerly") or []
        if prior:
            print(f"           formerly: {', '.join(prior)}  (superseded, never deleted)")
        return 0

    if sub == "place":
        try:
            rec = R.place(agent=args.nominee, family=args.family, team=args.team,
                          number=(int(args.number) if args.number is not None else None),
                          vendor=getattr(args, "vendor", "") or "", by=args.by)
        except ValueError as e:
            print(f"[resident] {e}")
            return 1
        print(f"[resident] POSTED: {R.designation(rec['agent_id'])}")
        prior = R.placement_history(rec["agent_id"])[:-1]
        if prior:
            p = prior[-1]
            print(f"           previously: {p.get('family') or '-'} / {p.get('team') or '-'}"
                  f" / {p.get('number')}  (kept -- postings append, never overwrite)")
        return 0

    if sub == "roster":
        fam = getattr(args, "family", "") or ""
        team = getattr(args, "team", "") or ""
        if fam:
            members = R.family_members(fam)
            print(f"# family {fam}: {len(members)} member(s)")
        elif team:
            members = R.family_members("") or R.team_members(team)
            print(f"# team {team}: {len(members)} member(s)")
        else:
            members = list(R._store().lrange("residents:all", 0, -1) or [])
            print(f"# all residents: {len(members)}")
        if not members:
            print("  (none -- an empty family is empty, never everyone)")
        for a in members:
            d = R.designation(a)
            print(f"  {d or a}")
        return 0

    if sub == "assign":
        try:
            rec = R.assign(agent=args.nominee, role=args.role, side=args.side,
                           exercise=args.exercise, by=args.by)
        except ValueError as e:
            print(f"[resident] {e}")
            return 1
        where = " / ".join(p for p in (rec.get("side"), rec.get("exercise")) if p)
        print(f"[resident] {rec['agent_id']} now operating as {rec['role']}"
              + (f" ({where})" if where else "")
              + f" -- {rec['provenance']} by {rec['by']}")
        return 0

    if sub == "roles":
        hits = R.roles(agent=(args.agent or None), role=(args.role or None),
                       side=(args.side or None), exercise=(args.exercise or None),
                       provenance=(args.provenance or None))
        if not hits:
            print("# no assignments match")
            return 0
        for h in hits:
            where = " / ".join(p for p in (h.get("side"), h.get("exercise")) if p)
            cs = (R.get(h["agent_id"]) or {}).get("callsign") or ""
            print(f"  {h['agent_id']}" + (f" '{cs}'" if cs else "")
                  + f" -- {h['role']}" + (f" ({where})" if where else "")
                  + f" [{h.get('provenance')}] by {h.get('by')}")
        return 0

    # show
    who = getattr(args, "nominee", "") or ""
    if not who:
        print("usage: py agent_cli.py resident show <agent>")
        return 2
    rec = R.get(who)
    if not rec:
        hist = R.history(who)
        if hist:
            print(f"# {who} has {len(hist)} nomination(s) on record but NONE ratified yet.")
            for h in hist:
                print(f"  [{h.get('state')}] '{h.get('callsign')}' by {h.get('by')} "
                      f"-- receipts: {', '.join(h.get('receipts') or [])}")
        else:
            print(f"# {who} is not a resident (no designation). That is the ordinary state for "
                  f"most seats, not an error.")
        return 0
    print(f"# {R.designation(who)}")
    print(f"  earned by: {', '.join(rec.get('receipts') or [])}")
    if rec.get("formerly"):
        print(f"  formerly:  {', '.join(rec['formerly'])}")
    print(f"  ratified by {rec.get('ratified_by') or '?'}")
    # T259: the situational plane, rendered beside the permanent one -- never merged into it.
    job = R.current_role(who)
    if job:
        where = " / ".join(p for p in (job.get("side"), job.get("exercise")) if p)
        print(f"  operating as: {job['role']}" + (f" ({where})" if where else "")
              + f" [{job.get('provenance')}] by {job.get('by')}")
    return 0


def cmd_report(args):
    """T275: emit a visual-report scaffold with the design kit inlined.

    Hands over a SYSTEM, never a document. The reports this kit came from needed three
    different shapes -- a retrospective, a set of decision forks, a reconciliation built
    around a contradiction -- and the fit was the point; a fixed template would flatten it.

    IMPORTS THE GENERATOR RATHER THAN SPAWNING IT. The first wiring shelled out and produced
    rc=0 with ZERO output -- the child worked perfectly when run from a plain script and
    silently from here, which is a process-inheritance quirk I did not chase, because the
    subprocess bought nothing: this is a Python module in this repo, so calling it is simpler,
    faster, testable in-process, and has no stdout-inheritance semantics to get wrong.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "scripts", "generators"))
    import gen_report_scaffold as _gen
    if getattr(args, "crib", False):
        print("report-kit primitives:\n")
        print(_gen.crib_text())
        return 0
    if not (args.title or "").strip():
        print("[report] --title is required -- it names the browser tab AND the gallery card, "
              "so an untitled scaffold publishes as an unnamed card.", file=sys.stderr)
        return 2
    html = _gen.render(args.title, args.eyebrow)
    if not args.out:
        print(html)
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[report] wrote {args.out} ({len(html)} chars, kit inlined)")
    print("         compose it against the crib, then publish with the Artifact tool.")
    return 0


def cmd_roster(args):
    """S2: the lobby -- every seat's proven liveness + inventory pointers (W84 render)."""
    from core.comm.roster import roster, render_roster, by_agent, render_by_agent
    from core.comm.bus import NS as DEFAULT_NS
    ns = os.environ.get("BIFROST_NAMESPACE", DEFAULT_NS)
    if getattr(args, "reap", False):
        from core.comm.reaper import reap
        recs = reap(ns)
        print(f"[reaper] {len(recs)} message(s) re-homed" if recs
              else "[reaper] nothing to re-home (no provably-dead seats with stranded mail)")
        for r in recs:
            print(f"  {r['kind']} {r['original_mid']} from {r['seat']} -> {r['rehomed_mid']}")
    # T183: --by-agent states churn instead of leaving it to be inferred from N last-beat ages.
    # NOT the default: a fenced wavefront showed the raw view's noise is load-bearing (a
    # crash-loop is visible there as clustered deaths), so this compresses the render on request
    # while the record and the raw view stay exactly as they were.
    if getattr(args, "by_agent", False):
        if getattr(args, "json", False):
            print(json.dumps(by_agent(roster(ns)), indent=2, default=str))
            return 0
        for ln in render_by_agent(ns):
            print(ln)
        return 0
    if getattr(args, "json", False):
        print(json.dumps(roster(ns), indent=2, default=str))
        return 0
    for ln in render_roster(ns):
        print(ln)
    return 0


def cmd_bifrost_sync(args):
    """Presence heartbeat + unread inbox peek (pull floor). --consume advances the cursor."""
    from agent.bifrost_pull import (collect_boot_bifrost, consume_inbox, format_inbox_line,
                                     format_digest_line, print_boot_bifrost_section,
                                     print_boot_locks_section, render_collapsed,
                                     stale_notice_lines)
    show_traces = bool(getattr(args, "traces", False))   # W4: --traces expands folded telemetry
    # T133: READ THE LANE THE RUNNERS READ. The runners self-default onto `work`; this door did not,
    # so the harness seat read LEGACY -- the same lane, plus every trace, from a cursor that drifted
    # 22 hours behind while real mail sat on `work` unread. Aligning the two ends the drift at its
    # source instead of re-discovering it with a cursor-vs-tail query every few days.
    # Per-process and still overridable: set BIFROST_CONSUME_LANE explicitly to pin either side.
    os.environ.setdefault("BIFROST_CONSUME_LANE", "work")
    if args.consume:
        res = consume_inbox(args.agent_id, limit=args.limit or 20)
        if args.json:
            print(json.dumps(res, indent=2, default=str))
            return 1 if res.get("seat_held") else 0
        if res.get("seat_held"):
            # RB-21: another live session/runner owns the cursor -- taught, not silent.
            print(f"ERROR: {res.get('teach') or 'consumer seat held -- read degraded to peek.'}")
            for ln in render_collapsed(res.get("peeked") or [], show_traces=show_traces):
                print(f"  (peek) {ln}")
            return 1
        msgs = res.get("consumed") or []
        # W65: consume_inbox already RETURNS an honest stale_notice (what it parked to the
        # bench / skipped while the cursor advanced) -- the renderer discarded it and printed
        # "(no messages consumed)". On 2026-07-25 five real messages went to the bench under
        # that line, and it cost a live seat a wrong root-cause diagnosis. Silence is only
        # honest when nothing moved.
        notice_lines = stale_notice_lines(res, args.agent_id)
        for _nl in notice_lines:
            print(_nl)
        if not msgs:
            if not notice_lines:
                print("(no messages consumed)")
            return 0
        print(f"# consumed {len(msgs)} message(s) for {args.agent_id}")
        for ln in render_collapsed(msgs, show_traces=show_traces):
            print(f"  {ln}")   # W4: trace-class telemetry folded (--traces to expand)
        # T133/M6: THE HARNESS SEAT SAYS SEEN TOO. The runners record because their _process_one
        # was wired; a harness seat has no such loop, so on 2026-08-03 claude showed 2 seen receipts
        # against 1536 entries that had in fact been read. THIS is that seat's read point -- the
        # bodies above just reached the agent -- so the receipt belongs here and nowhere earlier.
        # SEEN ONLY, never an intent: reading and deciding are separate acts for a human-driven
        # seat, and minting a decision at read time would fabricate one that has not been made.
        # The honest product is `read_but_undeclared`, which is exactly the state this surfaces.
        try:
            from core.comm import mailbox as _mbx
            _inc = (os.environ.get("AKASHIC_SESSION8")
                    or os.environ.get("CLAUDE_CODE_SESSION_ID", "")[:8] or "harness")
            _n = sum(1 for _m in msgs
                     if _mbx.open_for_message(args.agent_id, _m, incarnation=_inc).get("ok"))
            if _n:
                print(f"  ({_n} seen receipt(s) recorded -- declare intent with "
                      f"`mailbox {args.agent_id} --intent <sha> --as act|decline|defer|delegate`)")
        except Exception:
            pass      # a bookkeeping failure must never break the read that already succeeded
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
    print_boot_bifrost_section(block, show_traces=show_traces)
    print_boot_locks_section(block, args.agent_id)
    return 0


def cmd_bifrost_standby(args):
    """T084-CL-2: the turn-end ritual as ONE verb -- drain -> seat report -> BLOCK as the wake
    listener's parent. Run THIS as the harness background task; its exit (the listener detecting
    wake-worthy mail) re-invokes the harness. --no-listen = drain + report only."""
    from agent.bifrost_pull import standby

    def _listen(agent_id, session_id):
        # Blocking child, NOT detached: this CLI process is the harness-tracked parent (the T073
        # law -- a detached listener notifies nobody). Env pins the work lane (T045 cutover).
        import subprocess
        env = {**os.environ, "BIFROST_WAKE_LANE": os.environ.get("BIFROST_WAKE_LANE", "work")}
        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "scripts", "bifrost_wake.py"), "--agent", agent_id]
        if session_id:
            cmd += ["--session", session_id]
        return subprocess.run(cmd, env=env).returncode

    session = args.session or os.getenv("CLAUDE_CODE_SESSION_ID") or os.getenv("CLAUDE_SESSION_ID") or ""
    try:   # T086-S3a: stamp the arming attempt BEFORE the drain -- the stop-hook backstop
        #    suppresses its nag while this marker is fresh (<90s), so a standby mid-drain
        #    (or a retry loop between refusals) is never nagged into double-arming.
        import tempfile as _tf
        import time as _time
        _m = os.path.join(_tf.gettempdir(),
                          f"bifrost_wake_{args.agent_id}_{session}.arming" if session
                          else f"bifrost_wake_{args.agent_id}.arming")
        with open(_m, "w") as _f:
            _f.write(str(_time.time()))
    except Exception:
        pass
    res = standby(args.agent_id, session, listen=None if args.no_listen else _listen,
                  limit=args.limit or 20)
    for ln in res["report"]:
        print(ln)
    if res["decision"] == "listen":
        rc = res.get("listen_rc")
        how = ("wake-worthy mail or deadline" if rc == 0
               else f"killed or crashed (rc={rc}) -- NOT a wake")   # C1-6: never report a signal death as mail
        print(f"[standby] listener exited rc={rc} -- {how}; re-run bifrost-standby after handling")
    return 0 if res["decision"] != "twin-holds-seat" else 1


def cmd_bifrost_send(args):
    """Send a message to another agent on the Bifrost bus (or --broadcast to all). The sender is
    args.agent_id; the recipient is --to. Rings the doorbell so a runner/waiter wakes."""
    from core.comm.bus import Bus
    bus = Bus(args.agent_id)
    if not bus.online:
        print("[bifrost-send] bus OFFLINE (Redis down) -- not sent."); return 1
    bus.register()
    # T083-C3-1: --text-file beats argv text. Flag-shaped prose ('--foo' in a sentence) is hostile
    # input to argparse, and shell quoting multiplies the risk (live receipt 2026-07-16: a message
    # BODY containing '--sources-json' aborted the send). git commit -F precedent: long or
    # flag-bearing bodies ride a file, never argv.
    if getattr(args, "text_file", None):
        try:
            with open(args.text_file, encoding="utf-8") as _tf:
                text = _tf.read().strip()
        except Exception as e:
            print(f"[bifrost-send] --text-file unreadable ({type(e).__name__}: {e}) -- not sent.")
            return 2
        if not text:
            print("[bifrost-send] --text-file is empty -- not sent."); return 2
    else:
        text = " ".join(args.text) if isinstance(args.text, list) else str(args.text)
        if not text.strip():
            # W06 (folded 2026-07-19, five argv strikes in one day): empty argv falls through to
            # STDIN -- `... | py agent_cli.py bifrost-send claude --to X --kind reply` just works,
            # making the safe path the effortless one. A TTY with no pipe still refuses loudly.
            piped = False
            try:
                piped = not sys.stdin.isatty()
            except Exception:
                pass
            if piped:
                text = sys.stdin.read().strip()
                if text:
                    print(f"[bifrost-send] body from stdin ({len(text)} chars) -- the W06 path")
            if not text.strip():
                print("[bifrost-send] no message text (positional, --text-file, or piped stdin) -- not sent.")
                return 2
    # T263: SPILL AN OVERSIZE BODY, exactly as the tool door has since T113. Until now
    # spill_tool_text had three callers and all three were in toolbox.py, so a long CLI
    # message was clipped at RENDER time and the reader was handed a STREAM-ID pointer --
    # an address that resolves only from a stream the reader can already read. Measured
    # 2026-08-09: claude->claude fetched fine, claude->deepseek returned "no blob or bus
    # message" from BOTH ends, and deepseek answered a stale backlog item because it could
    # not read the brief it had been sent. A blob sha is an address everyone can reach.
    # Degrades to the historical clip when the blob store is unreachable -- today's
    # behaviour is the floor, never a dropped message.
    from core.comm import packet_spec as _pspec
    text, _spill = _pspec.spill_tool_text(text)
    if _spill.get("spilled"):
        print(f"[bifrost-send] body spilled: {_spill['spill_len']} chars -> "
              f"{_spill['spill_ref']} (the recipient fetches it; nobody re-sends)",
              file=sys.stderr)
    expect_arg = int(getattr(args, "expect_reply_within", -1))   # -1 = UNSET (arg default)
    # Directed ASKS (request/handoff/question) DEFAULT to a reply-deadline so a dropped ask surfaces
    # itself -- the 2026-07-12 silent-handoff incident: fenced asks fire-and-forgotten to a dead peer
    # went unflagged for hours. UNSET + ask-kind -> AUTO window; explicit 0 opts out; explicit >0 wins.
    ASK_KINDS = {"request", "handoff", "question"}
    ASK_EXPECT_DEFAULT_S = int(os.getenv("AKASHIC_ASK_EXPECT_S", "1800"))
    expect = 0
    if args.broadcast:
        if expect_arg > 0:
            print("ERROR: --expect-reply-within needs a DIRECTED send (--to); a broadcast "
                  "has no single answerer to redrive."); return 2
        mid = bus.broadcast(args.kind, text)
        dest = "*"
    else:
        if not args.to:
            print('ERROR: bifrost-send needs --to <agent> (or --broadcast). '
                  'e.g. bifrost-send claude --to deepseek "hi"'); return 2
        # T073 Phase 1: explicit incarnation addressing -- names ONE session of the
        # target agent (>=8-char session-id prefix); that seat wakes even on same-agent
        # mail (the twin channel), and no other incarnation does.
        meta = {"to_incarnation": args.to_incarnation} if getattr(args, "to_incarnation", None) else None
        mid = bus.send(args.to, args.kind, text, meta=meta)
        dest = args.to + (f"#{args.to_incarnation[:8]}" if getattr(args, "to_incarnation", None) else "")
        auto = expect_arg < 0 and args.kind in ASK_KINDS
        expect = ASK_EXPECT_DEFAULT_S if auto else max(0, expect_arg)
        if mid and expect > 0:
            # RB-29 (T030 L4): arm the sender-side deadline; the pull floor sweeps it.
            from core.comm.expectations import MIN_WITHIN_S, arm
            if arm(args.agent_id, mid, args.to, args.kind, text, expect):
                tag = " [auto: directed ask -- add --expect-reply-within 0 to opt out]" if auto else ""
                print(f"[bifrost-send] expecting a reply within {max(MIN_WITHIN_S, expect)}s{tag} "
                      f"(3 redrives then a loud expectation_dead; swept at boot/bifrost-sync)")
    # T149: STDOUT MUST NOT CLAIM A SEND THAT DID NOT HAPPEN. When the re-ask window collapses a
    # duplicate, the bus says so on STDERR and sets last_reask -- but stdout used to print the
    # ordinary arrow line, carrying the ORIGINAL's id, which is indistinguishable from success on
    # the one channel scripts, pipes and logs keep. Three briefs were lost to that in one night.
    # The collapse itself is correct and untouched; only the rendering was dishonest.
    collapsed = getattr(bus, "last_reask", None)
    if args.json:
        print(json.dumps({"sent": bool(mid) and not collapsed, "id": mid, "to": dest,
                          "kind": args.kind, "collapsed_onto": collapsed or None,
                          "expect_reply_within": expect or None}, default=str))
        return 0 if mid else 1
    if mid and collapsed:
        print(f"[bifrost-send] COLLAPSED onto {collapsed} -- NOT re-sent (identical "
              f"{args.kind} to {dest} is still pending). Nudge it, or change the ask.")
    else:
        print(f"[bifrost-send] -> {dest} [{args.kind}] (id {mid})" if mid
              else "[bifrost-send] send failed")
    return 0 if mid else 1


def cmd_suite_baseline(args):
    """suite-baseline <me> --from-file <pytest-output> [--sha X] | --check --from-file |
    --show: the test-suite receipt the next seat DIFFS instead of re-classifying (W34).
    record = snapshot failures + auto-classified lanes + claims + provenance; check =
    node-id delta (new/fixed/inherited -- churn visible even at identical counts)."""
    from core.coord import suite_baseline as sb
    if getattr(args, "show", False):
        line = sb.render_boot_line()
        print(line or "[suite-baseline] none recorded yet")
        return 0

    # T208 --whose: run the tests AND attribute every failure, in one command. This is
    # the ergonomic point: on 2026-08-06 four failures each cost a manual git-stash
    # bisect, one of which I answered WRONG in public, while the baseline already knew
    # one of them and never said so.
    whose = getattr(args, "whose", None)
    if whose is not None:
        import shlex
        import subprocess
        pa = shlex.split(whose) if whose.strip() else ["tests/"]
        print(f"[suite-baseline] running: pytest {' '.join(pa)}", file=sys.stderr)
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", *pa, "-q"],
                               capture_output=True, text=True, timeout=3600,
                               cwd=os.path.dirname(os.path.abspath(__file__)),
                               stdin=subprocess.DEVNULL)
        except Exception as e:
            print(f"[suite-baseline] could not run pytest: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 2
        nodes = sb.ingest_pytest((r.stdout or "") + "\n" + (r.stderr or ""))
        # Only a bare `tests/` run covers the baseline's scope; anything narrower cannot
        # prove a baseline failure was fixed rather than simply not run.
        v = sb.verdicts(nodes, full_suite=(not pa or pa == ["tests/"]))
        if getattr(args, "json", False):
            print(json.dumps(v, ensure_ascii=False, default=str))
            return 0
        if not nodes:
            print("[suite-baseline] 0 failures")
            return 0
        prov = (f"baseline @{v['baseline_sha']} vs HEAD @{v['head_sha']}"
                if v["has_baseline"] else "NO baseline recorded")
        print(f"# {len(nodes)} failure(s) -- {prov}"
              + ("  [STALE: attribution is limited]" if v["stale"] else "  [current]"))
        for verdict in ("YOURS", "UNKNOWN", "LIKELY_INHERITED", "INHERITED"):
            hits = [n for n, row in v["by_node"].items() if row["verdict"] == verdict]
            if not hits:
                continue
            print(f"\n{verdict} ({len(hits)}): {sb.VERDICT_NEXT[verdict]}")
            for n in hits:
                print(f"    {n}")
        if v["fixed"]:
            print(f"\nfixed since baseline ({len(v['fixed'])}) -- re-record to keep "
                  f"attribution sharp:")
            for n in v["fixed"][:10]:
                print(f"    {n}")
        elif v["not_evaluated"]:
            print(f"\n{len(v['not_evaluated'])} baseline failure(s) NOT RUN by this "
                  f"selection -- not fixed, just unevaluated. Do NOT re-record from a "
                  f"subset: it would drop them from the receipt.", file=sys.stderr)
        # Exit 1 only for failures this tree is actually answerable for. UNKNOWN is not
        # an accusation, so it must not fail a gate -- that is how an honest "I cannot
        # tell" gets quietly converted into "yours".
        return 1 if v["counts"].get("YOURS") else 0

    path = getattr(args, "from_file", None)
    if not path:
        print("[suite-baseline] need --from-file <pytest output> (or --show)")
        return 2
    try:
        with open(path, encoding="utf-8") as f:
            nodes = sb.ingest_pytest(f.read())
    except Exception as e:
        print(f"[suite-baseline] unreadable {path}: {type(e).__name__}: {e}")
        return 2
    if getattr(args, "check", False):
        d = sb.delta(nodes)
        print(f"[suite-baseline] vs baseline: {len(d['new'])} NEW, {len(d['fixed'])} fixed, "
              f"{len(d['inherited'])} inherited")
        for n in d["new"]:
            print(f"  NEW: {n}")
        return 1 if d["new"] else 0
    sha = getattr(args, "sha", "") or ""
    if not sha:
        try:
            import subprocess
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True, timeout=10,
                                 cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
        except Exception:
            sha = ""
    rec = sb.record(nodes, seat=args.agent_id, sha=sha)
    lanes = sum(1 for f in rec["failures"] if f["lane"])
    print(f"[suite-baseline] recorded {len(rec['failures'])} failure(s) @{rec['sha'][:7]} "
          f"({lanes} lane-classified) -- the next seat diffs instead of re-deriving")
    return 0


def cmd_bifrost_drain(args):
    """Request a runner's graceful exit (finish current message -> release lock -> exit 0).
    TTL'd (control.DRAIN_TTL_S); the runner honors it at its next loop top. Relaunch after
    it lands -- no TaskStop tree-kill ghosts, no thrown-away in-flight context."""
    from core.comm import control
    ok = control.drain(args.to, by=args.agent_id, reason=args.reason or "")
    if ok:
        print(f"[drain] requested for {args.to} (self-clears in {control.DRAIN_TTL_S}s if "
              f"unhonored) -- the runner exits clean at its next loop top; relaunch when it lands")
        return 0
    print("[drain] bus OFFLINE -- not requested")
    return 1


def cmd_bifrost_pause(args):
    """Freeze the bus auto-responders (human barge-in). They hold until `bifrost-resume` --
    or self-heal after --ttl seconds (RB-30): ceremony/automation pauses should ALWAYS
    carry a ttl so a crash mid-ceremony can never freeze the fleet forever (deepseek's
    C1-8-genus find, 2026-07-21)."""
    from core.comm import control
    ttl = int(args.ttl) if getattr(args, "ttl", None) else None
    soft = bool(getattr(args, "soft", False))
    ok = control.pause(reason=args.reason or "", by=args.by or "user", ttl=ttl, soft=soft)
    if args.json:
        print(json.dumps(control.pause_status(), default=str)); return 0 if ok else 1
    tag = f" (self-heals in {ttl}s)" if ttl else ""
    if not ok:
        print("[bifrost] pause failed (bus offline)")
    elif soft:
        print(f"[bifrost] SOFT PAUSE{tag} -- seats FINISH the message in hand, then hold. "
              "In-flight work is NOT abandoned and no runner exits; resume with "
              "`bifrost-resume`")
    else:
        print(f"[bifrost] PAUSED{tag} -- runners frozen mid-turn (in-flight work is "
              "abandoned); for a graceful stop use `--soft`; resume with `bifrost-resume`")
    return 0 if ok else 1


def cmd_bifrost_resume(args):
    """Un-freeze the bus auto-responders."""
    from core.comm import control
    ok = control.resume()
    print("[bifrost] RESUMED" if ok else "[bifrost] resume failed (bus offline)")
    return 0 if ok else 1


def cmd_bifrost_skip_to_now(args):
    """T076a: the sanctioned echo-mountain escape -- advance an agent's consume cursors
    (shared + lane hashes) to their stream tails. Audited (durable cursor_skip_to_now
    event w/ before/after); requires the fleet PAUSED and a --reason. Replaces the
    super-admin hand surgery of note cursor-skip-2026-07-15."""
    from core.comm.cursor_admin import skip_to_now
    res = skip_to_now(args.agent_id, by=args.by, reason=args.reason)
    if args.json:
        print(json.dumps(res, default=str))
        return 0 if res.get("ok") else 2
    if res.get("refused"):
        print(f"[skip-to-now] REFUSED: {res['refused']}")
        return 2
    adv = (res.get("after") or {}).get("advance") or {}
    print(f"[skip-to-now] {args.agent_id}: shared={adv.get('shared')} lane={adv.get('lane')} "
          f"(audited event recorded; by {args.by}: {args.reason})")
    for side in ("shared", "lane"):
        b, a = (res.get("before") or {}).get(side) or {}, (res.get("after") or {}).get(side) or {}
        moved = {f: f"{b.get(f)}->{a.get(f)}" for f in a if a.get(f) != b.get(f) and f != "advance"}
        if moved:
            print(f"  {side}: " + ", ".join(f"{k} {v}" for k, v in sorted(moved.items())))
    return 0 if res.get("ok") else 2


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
def cmd_seat_identity(args) -> int:
    """Declare / show THIS SESSION'S seat identity (fold 2).

    The door exists because the seat that needs it cannot use the old mechanism: identity lived
    in a process-wide env var read from a settings.json shared by every home-rooted session, and
    a running session cannot mutate its own process env. So a seat could not name itself, and
    every hook silently called it "claude" -- the conductor. This binds it per session instead.
    """
    from core.comm import seat_identity as si
    sid = (args.session or os.environ.get("CLAUDE_CODE_SESSION_ID")
           or os.environ.get("BIFROST_INCARNATION") or "").strip()
    if not sid:
        print("[seat-identity] no session id -- pass --session <uuid> "
              "(CLAUDE_CODE_SESSION_ID is unset in this process)")
        return 1
    if args.clear:
        print(f"[seat-identity] binding cleared for {sid[:8]}" if si.clear(sid)
              else f"[seat-identity] no binding to clear for {sid[:8]}")
        return 0
    if args.agent_id:
        if not si.valid(args.agent_id):
            print(f"[seat-identity] REFUSED: {args.agent_id!r} is not a valid seat id")
            return 1
        if not si.declare(args.agent_id, sid):
            print("[seat-identity] REFUSED: could not write the binding")
            return 1
        print(f"[seat-identity] {sid[:8]} is now {args.agent_id}")
    got, src = si.resolve(sid), si.resolved_from(sid)
    print(f"  seat: {got}#{sid[:8]}   (resolved from: {src})")
    if src == "unknown":
        print("  NOTE: unresolved. Hook-authored records will read unknown-" + sid[:8]
              + " rather than borrowing a peer's name -- honest, but not yours until declared.")
    elif src == "env":
        print("  NOTE: from the shared process env, not a per-session binding. If another seat "
              "runs in this process profile it resolves identically. Declare to make it yours.")
    return 0

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


def cmd_blob(args):
    """T113: fetch a spilled payload by its content-addressed ref.

    The other half of spill_tool_text. When a send exceeds the tool door's rendering
    bound, the FULL text goes to the blob store and the wire carries a prefix plus
    `blob:<sha>`; this is the door that turns that ref back into the bytes. Without it
    the pointer is decoration -- which is precisely how the lookback battery broke
    (content preserved, retrieval handle unreachable), so this verb is not a
    convenience, it is the half that makes the spill lossless."""
    from core.comm.blobs import get_blob_store
    ref = str(getattr(args, "get", "") or "").strip()
    if not ref:
        print("usage: py agent_cli.py bifrost-fetch --get blob:<sha>|<stream-id>  [--out FILE]")
        return 2
    data = get_blob_store().get(ref)
    if data is None and _looks_like_stream_id(ref):
        # T222: the SECOND address space, added because T220 minted pointers into this door
        # that it could not serve. A clipped bus body's real identity is its STREAM ID, and
        # until now no door resolved one -- the bytes were reachable only by a raw xrange.
        # The peer I shipped T220 to hit this within the hour: "your blob pointer was dead on
        # my side". Extending the resolver serves the address the message actually has;
        # rewriting the pointer to name some other door would only move the lie.
        data = _fetch_bus_body(ref)
    if data is None:
        print(f"# no blob or bus message for {ref}\n"
              f"# (blob refs are content-addressed and never rewritten -- a miss means it was "
              f"never stored or the store dir differs. A stream id misses when it is not in "
              f"any stream this agent can read: check the namespace and the lane.)")
        return 1
    out = str(getattr(args, "out", "") or "").strip()
    if out:
        with open(out, "wb") as f:
            f.write(data)
        print(f"# wrote {len(data)} bytes -> {out}")
        return 0
    sys.stdout.write(data.decode("utf-8", "replace"))
    return 0


def _looks_like_stream_id(ref: str) -> bool:
    """A Redis stream id is '<ms>-<seq>'. Deliberately narrow so a malformed blob ref is
    never silently re-routed into a stream scan and reported as a stream miss."""
    parts = str(ref).split("-")
    return len(parts) == 2 and all(p.isdigit() for p in parts) and len(parts[0]) >= 10


def _fetch_bus_body(mid: str):
    """The body of a bus message, by stream id, as bytes. None when unreachable.

    T222. Scans the streams THIS agent can read rather than guessing one: a message lands on
    the work lane, the legacy inbox, or a broadcast depending on kind and era, and the whole
    point of this door is that the caller holding a clipped render does not know which.

    Reassembles T043 fragments when the id names a fragmented send, because a body that
    clipped is exactly the size that fragments -- resolving only the first part would hand
    back another truncation and call it a fix.
    """
    try:
        from core.comm.bus import Bus
        b = Bus("claude")
        r = b._client
        if r is None:
            return None
        seen = []
        for key in (f"{b.ns}:work:inbox:claude", f"{b.ns}:inbox:claude",
                    f"{b.ns}:work:broadcast", f"{b.ns}:broadcast"):
            try:
                got = r.xrange(key, min=mid, max=mid)
            except Exception:
                continue
            for _id, f in got or []:
                d = {(k.decode() if isinstance(k, bytes) else k):
                     (v.decode("utf-8", "replace") if isinstance(v, bytes) else v)
                     for k, v in f.items()}
                body = d.get("content") or d.get("text") or ""
                if body:
                    seen.append(body)
        if not seen:
            return None
        body = max(seen, key=len)
        # The stream stores `content` JSON-ENCODED, so a raw read hands back a quoted string
        # with literal \n. A body the reader has to un-escape by hand is a half-resolved
        # pointer, which is the defect this door exists to close -- decode it here.
        if body[:1] == '"':
            try:
                decoded = json.loads(body)
                if isinstance(decoded, str):
                    body = decoded
            except (ValueError, TypeError):
                pass
        return body.encode("utf-8")
    except Exception:
        return None


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
        why = f"  why: {lk.get('note')}" if lk.get("note") else ""
        age = ""
        try:
            from core.foundation.timeutil import to_epoch
            secs = max(0, int(time.time() - to_epoch(lk.get("ts"))))
            ttl = int(lk.get("ttl") or 0)
            age = f"  [{secs}s old, ttl {ttl}s]"
        except Exception:
            pass
        print(f"  {lk.get('path')}  <- {lk.get('agent')}{mine}  token {lk.get('token')}{age}{why}")
    return 0


def cmd_packet_trace(args):
    """T060 N0: explain the existing static kind-to-lane decision without sending."""
    from core.comm.router import route
    out = route(args.kind).as_dict()
    if args.json:
        print(json.dumps(out, sort_keys=True))
        return 0
    lane = out["lane"] if out["lane"] is not None else "(unmapped; legacy-only)"
    print(f"# PACKET ROUTE -- {out['kind']}")
    print(f"  lane: {lane}")
    print(f"  rule: {out['rule_id']}")
    print(f"  mode: {out['mode']} (observation only; no delivery behavior changes)")
    print(f"  policy: {out['policy_version']}")
    return 0


def cmd_mailbox(args):
    """T095 M0 shadow mailbox: the free question 'what is addressed to X and in what
    state?' -- evidence ladder acked > replied/auto_acked > consumed > unhandled,
    derived read-only from the streams (docs/library/design/20260701_comms-mailbox-over-the-log-t095-governin_06357f.md sec 2).
    Observation only: touches no cursor, ack, wake, or delivery state."""
    from core.comm.bus import Bus
    from core.comm import mailbox
    bus = Bus("mailbox-observer", promote=False)

    # ---- M1 verbs. Built is not wired: these existed in core/comm/mailbox.py with tests green
    # while NO door exposed them, so no agent could actually use them. This is the door.
    inc = (getattr(args, "incarnation", None) or os.environ.get("AKASHIC_SESSION8") or "unknown")

    if getattr(args, "retire_ghosts", False):
        apply = bool(getattr(args, "apply", False))
        out = mailbox.retire_ghost_mail(bus.ns, args.agent_id, client=bus._client,
                                        dry_run=not apply,
                                        min_age_h=float(getattr(args, "min_age_h", 24.0)),
                                        limit=int(getattr(args, "limit_scan", 5000)),
                                        incarnation=f"ghost-sweep:{inc}")
        if args.json:
            print(json.dumps(out, indent=2, default=str)); return 0
        if not out.get("ok"):
            print(f"[mailbox] ghost sweep failed: {out.get('reason')}"); return 1
        cands = out.get("candidates") or []
        print(f"# ghost sweep for {args.agent_id}: scanned {out['scanned']} of {out.get('total', '?')}, "
              f"{len(cands)} from senders with no live seat"
              + ("" if apply else "  (REPORT ONLY -- add --apply to write)"))
        if out.get("truncated"):
            print(f"  !! {out['unscanned']} entr(ies) NOT scanned (cap {args.limit_scan}). "
                  f"'0 ghosts' here does NOT mean the mailbox is clean -- raise --limit-scan.")
        for c in cands[:40]:
            print(f"  {c['sha'][:10]}  {c['kind']:<10} from {c['frm']:<26} {c['age_h']}h old")
        if len(cands) > 40:
            print(f"  ... and {len(cands) - 40} more")
        if apply:
            print(f"[mailbox] declined {out['retired']} ghost message(s) -- they stay readable, "
                  f"stop competing with live work, and no longer wake a seat")
        return 0

    if getattr(args, "open_sha", None):
        out = mailbox.open(bus.ns, args.agent_id, args.open_sha, incarnation=inc,
                           client=bus._client)
        if args.json:
            print(json.dumps(out, indent=2, default=str)); return 0
        if not out.get("ok"):
            print(f"[mailbox] {out['reason']}"); return 1
        readers = ", ".join(r["incarnation"] for r in out["seen_by"]) or "(none)"
        print(f"[mailbox-open] {out['sha'][:12]} kind={out['kind']} frm={out['frm']}")
        print(f"  seen by: {readers}"
              f"{'  (first open by this incarnation)' if out['first_open_by_this_incarnation'] else ''}")
        print(f"  SEEN only -- not consumed, not handled, not settled. Cursor untouched.")
        if not out.get("body_available"):
            print(f"  !! NO BODY STORED: {out['body_unavailable_reason']}")
            return 0
        if out["truncated"]:
            print(f"  !! body truncated at {len(out['body'])} of {out['body_len']} chars")
        print("-" * 60); print(out["body"])
        return 0
    if getattr(args, "backfill", False):
        out = mailbox.backfill_bodies(bus.ns, args.agent_id, client=bus._client)
        if args.json:
            print(json.dumps(out, indent=2, default=str)); return 0
        print(f"[mailbox-backfill] {out['scanned']} bodyless entrie(s) scanned; "
              f"{out['filled']} recovered from transport; {out['unrecoverable']} unrecoverable")
        if out["unrecoverable"]:
            print(f"  {out['note']}")
        return 0
    if getattr(args, "state_sha", None):
        out = mailbox.state_for(bus.ns, args.agent_id, args.state_sha, client=bus._client)
        if args.json:
            print(json.dumps(out, indent=2, default=str)); return 0
        if not out.get("found"):
            print(f"[mailbox] no entry for {args.state_sha}"); return 1
        print(f"[mailbox-state] {out['sha'][:12]} kind={out['kind']} frm={out['frm']}")
        print(f"  opened by : {', '.join(r['incarnation'] for r in out['seen_by']) or '(nobody)'}")
        print(f"  intent    : {out['intent'] or 'NONE DECLARED'}")
        if out["read_but_undeclared"]:
            print("  >> READ BUT UNDECLARED -- a seat opened this and said nothing about acting.")
        print(f"  retention : {out['retention_s'] // 86400}d   identity basis on entry stored")
        return 0
    if getattr(args, "intent_sha", None):
        if not args.intent_kind:
            print("[mailbox] --intent needs --as act|decline|delegate|defer"); return 2
        out = mailbox.declare_intent(bus.ns, args.agent_id, args.intent_sha, args.intent_kind,
                                     incarnation=inc, note=args.intent_note or "",
                                     to=args.intent_to or "", client=bus._client)
        if args.json:
            print(json.dumps(out, indent=2, default=str)); return 0
        if not out.get("ok"):
            print(f"[mailbox] {out['reason']}"); return 1
        print(f"[mailbox-intent] {args.intent_sha[:12]} -> {out['intent']}"
              f"{' to ' + out['to'] if out['to'] else ''} (by {out['by']})")
        return 0

    if args.rebuild:
        out = mailbox.rebuild(bus.ns, args.agent_id, client=bus._client)
    elif args.explain:
        out = mailbox.explain(bus.ns, args.agent_id, args.explain, client=bus._client)
    else:
        out = mailbox.query(bus.ns, args.agent_id, client=bus._client,
                            min_evidence=args.min_evidence)
    if args.json:
        print(json.dumps(out, indent=2, default=str)); return 0
    if not out.get("available"):
        print(f"[mailbox] {out.get('reason', 'unavailable')}"); return 1
    if args.rebuild:
        print(f"[mailbox] rebuilt {out['entries']} entrie(s); divergence vs incremental: "
              f"{out['divergence']}" + (" (DETERMINISM HOLDS)" if out["divergence"] == 0
                                        else " (!! INVESTIGATE)"))
        return 0 if out["divergence"] == 0 else 1
    if args.explain:
        if not out.get("found"):
            print(f"[mailbox] no entry matches ref '{out.get('ref', args.explain)}'"); return 1
        print(f"[mailbox-explain] {out['sha'][:12]} kind={out['kind']} frm={out['frm']} "
              f"ts={out['ts']} -> TIER: {out['tier']}")
        for c in out["cursor_comparisons"]:
            print(f"  {c['source']}: id {c['stream_id']} vs cursor "
                  f"{c['cursor'] or '(none)'} -> consumed={c['consumed']}")
        for sid, acks in (out.get("acks") or {}).items():
            if acks:
                print(f"  ack on {sid}: {acks}")
        for sid, ans in (out.get("answered_by") or {}).items():
            print(f"  answered ({sid}): by {ans.get('by')} at {ans.get('ts')}")
        return 0
    counts = out["counts"]
    tier_line = " | ".join(f"{t}={counts[t]}" for t in
                           ("unhandled", "consumed", "auto_acked", "replied", "acked")
                           if counts.get(t))
    print(f"# mailbox {args.agent_id}: {tier_line or 'empty'} "
          f"(index_lag {out['index_lag']}, evicted {out['evicted']})")
    for e in out["entries"]:
        if e["tier"] in ("unhandled", "consumed"):
            print(f"  [{e['tier']}] {e['sha'][:10]} {e['kind']:<10} from {e['frm']:<14} ts {e['ts']}")
    return 0


def cmd_packet_stats(args):
    """T060 N0: read the bounded logical-route and physical-mirror counters."""
    from core.comm.bus import Bus
    from core.comm.router import route_stats
    bus = Bus("route-observer", promote=False)
    out = route_stats(bus._client, bus.ns)
    if args.json:
        print(json.dumps(out, sort_keys=True))
        return 0 if out["online"] else 1
    state = "online" if out["online"] else "OFFLINE (counters unavailable)"
    print(f"# PACKET ROUTE STATS -- {out['mode']} / {state}")
    print(f"  policy: {out['policy_version']}")
    if out["stored_policy_version"]:
        match = "match" if out["policy_matches"] else "MISMATCH -- do not use for cutover"
        print(f"  stored policy: {out['stored_policy_version']} ({match})")
    print(f"  started: {out['started_at'] or '(no observations yet)'}")
    print(f"  bounded fields: {len(out['counts'])}/{out['counter_field_limit']}")
    if not out["counts"]:
        print("  (no observations)")
    for field, count in sorted(out["counts"].items()):
        print(f"  {field:42} {count}")
    return 0 if out["online"] else 1


# ------------------------------------------------------------------------- status
def _durable_backend_name(store) -> str:
    """Name the concrete durable tier selected by the canonical store factory."""
    from core.foundation.sqlite_store import SqliteStore
    from core.foundation.store import FileStore

    durable = getattr(store, "_file", store)
    if isinstance(durable, SqliteStore):
        return "SQLite"
    if isinstance(durable, FileStore):
        return "File"
    return f"UNKNOWN:{type(durable).__name__}"


def cmd_status(args):
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    client = connect_to_redis_with_fail_fast(
        host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=2)
    learn = mem = total = None
    if client is not None:
        learn, mem, total = len(client.keys("learn:*")), len(client.keys("mem:*")), len(client.keys("*"))
    # narrative health -- surface the best-effort paths so silent degradation is visible (W-c)
    health = {}
    durable_backend = "UNKNOWN"
    try:
        from core.foundation.store import create_store
        from core.narrative.health import snapshot
        store = create_store()
        durable_backend = _durable_backend_name(store)
        health = snapshot(store)
    except Exception:
        health = {}
    if client is not None:
        backend = f"Redis {DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT} (+ {durable_backend} mirror)"
    else:
        backend = f"{durable_backend} (Redis down -> fallback active)"
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
    b.add_argument("--sources-json", default=None, metavar="PATH",
                   help="T081-W6: also write {'sources':[...]} (normalized lesson-source pointers) "
                        "to PATH, so a runner can tag boot-known lessons without regex-parsing the text")
    b.set_defaults(fn=cmd_boot)

    dl = sub.add_parser("delta", help="what changed since this agent's last boot (T052 delta door)")
    dl.add_argument("agent_id")
    dl.add_argument("--ack", action="store_true",
                    help="advance the seen mark to current positions after reading")
    dl.set_defaults(fn=cmd_delta)

    cmp_p = sub.add_parser("compare", help="what does one domain have that another does "
                                           "not -- the cross-domain set difference four "
                                           "of our guards each hand-rolled")
    cmp_p.add_argument("a", nargs="?", default="", help="left domain (see --list)")
    cmp_p.add_argument("b", nargs="?", default="", help="right domain")
    cmp_p.add_argument("--list", action="store_true", help="show comparable domains")
    cmp_p.add_argument("--limit", type=int, default=40, help="rows per side (default 40)")
    cmp_p.add_argument("--json", action="store_true")
    cmp_p.set_defaults(fn=cmd_compare)

    tlp = sub.add_parser("timeline", help="one chronological view across domains "
                                          "(events + git + task transitions) -- line the "
                                          "domains up by time and the cause becomes visible")
    tlp.add_argument("--hours", type=float, default=6.0, metavar="H",
                     help="window in hours (default 6); 0 for everything")
    tlp.add_argument("--limit", type=int, default=60, metavar="N",
                     help="show the last N rows (default 60); 0 for all")
    tlp.add_argument("--json", action="store_true")
    tlp.set_defaults(fn=cmd_timeline)

    dsc = sub.add_parser("discover", help="list every verb + its purpose (the self-describing door)")
    dsc.add_argument("query", nargs="?", default="", help="optional substring to filter verbs by name/purpose")
    dsc.add_argument("--json", action="store_true")
    dsc.add_argument("--semantic", action="store_true",
                     help="ask at the level of MEANING instead of substring: 'does this "
                          "system already do X?' Returns EXISTS/WHAT/GAP/NEAREST MISS "
                          "over the verb table + module index. Costs one model call "
                          "(~20s, under a cent). A failed or malformed call renders "
                          "UNKNOWN, never 'no' -- this verb exists to stop absence being "
                          "inferred, so it must never infer one")
    dsc.set_defaults(fn=cmd_discover)

    l = sub.add_parser("learn", help="record a lesson")
    l.add_argument("agent_id")
    # T253: not argparse-required any more, because --repeat-of does not take one. cmd_learn
    # still refuses a missing --experiment and prints a worked example, so the error TEACHES
    # instead of just rejecting.
    l.add_argument("--experiment", default="")
    l.add_argument("--repeat-of", dest="repeat_of", default="", metavar="LESSON",
                   help="record that this EXISTING lesson was violated again -- evidence ABOUT "
                        "a lesson, not a new one. Use --tried for what happened. The count is "
                        "a FLOOR (only what someone noticed), never a rate.")
    l.add_argument("--recall-outcome", dest="recall_outcome", default="", metavar="OUTCOME",
                   help="with --repeat-of: what recall did at that moment (fired / floor_silent "
                        "/ excluded_silent:antirepeat / excluded_silent:self_echo). FIRED means "
                        "a reading failure; SUPPRESSED means a targeting failure -- opposite fixes.")
    l.add_argument("--tried", default=""); l.add_argument("--result", default="")
    l.add_argument("--expected", default=""); l.add_argument("--recommend", default="")
    l.add_argument("--category", default=""); l.add_argument("--success", default=None)
    l.add_argument("--confidence", default=None); l.add_argument("--json", action="store_true")
    l.add_argument("--anti-pattern", dest="anti_pattern", default="",
                   help="name a reusable known-bad this lesson documents (recall's dissent-finder warns on it)")
    l.set_defaults(fn=cmd_learn)

    wsh = sub.add_parser("wish", help="file an ergonomics wish to docs/WISHLIST.md "
                                      "(one command, auto-numbered, W## echoed back)")
    wsh.add_argument("agent_id", help="your stable seat id (wishes are attributed)")
    wsh.add_argument("text", nargs="*", help="the wish (or use --text-file for flag-bearing prose)")
    wsh.add_argument("--text-file", dest="text_file", help="read the wish body from PATH")
    wsh.add_argument("--trigger", default="", help="what hurt (one clause)")
    wsh.add_argument("--land", default="", help="suggested landing arc/slice")
    wsh.set_defaults(fn=cmd_wish)

    # T171: ask is NOT a seat -- one synchronous question, no lifecycle, dies in the call.
    ask_p = sub.add_parser("ask", help="ask a helper model ONE question, synchronously "
                                       "(no seat, no lock, no mailbox -- it dies in the call)")
    ask_p.add_argument("text", nargs="*", help="the question (or use --prompt-file)")
    ask_p.add_argument("--prompt-file", dest="prompt_file", help="read the question from PATH")
    ask_p.add_argument("--system", default="", help="override the helper's system prompt")
    ask_p.add_argument("--as-resident", dest="as_resident", default=None, metavar="AGENT",
                       help="T261 tier-1: the branch answers AS a ratified resident -- its "
                            "callsign, receipts and a catch-up pack of its OWN archive lessons "
                            "ride the system context, and the reply is stamped tier=resident "
                            "with the designation. NOT --as, which is the SENDER identity: one "
                            "flag carrying both meanings is the T174 homonym class. A "
                            "non-resident refuses BEFORE any model call.")
    ask_p.add_argument("--model", default="", help="override the helper model")
    ask_p.add_argument("--max-tokens", dest="max_tokens", type=int, default=None,
                       help="answer ceiling; hitting it returns a marked PARTIAL, never a silent cut")
    ask_p.add_argument("--fan", type=int, default=0,
                       help="ask the SAME question N times concurrently: N samples of ONE "
                            "model on ONE prompt, so agreement is self-consistency and NOT "
                            "independent verification -- correlated samples fail together. "
                            "For decorrelated evidence vary the POSITION with --prompts-file. "
                            "STATELESS only: cannot be combined with --peer, one durable ask "
                            "to one seat")
    ask_p.add_argument("--prompts-file", dest="prompts_file",
                       help="T181: run MANY questions at once. JSON array, or prompts separated "
                            "by a line containing only --- (so a prompt may be multi-line)")
    # T281: the fan doctrine at the door. WHEN TO FAN -- wide independent READING fans;
    # deep sequential REASONING stays on one seat; VERIFICATION fans with lenses that differ
    # in failure mode; a corpus-level CLAIM adds a backbrief. Declared, never derived.
    ask_p.add_argument("--geometry", default="",
                       help="T281: declare the fan's SHAPE so the route journal can score "
                            "routes. WHEN TO FAN: wide independent reading -> fan; deep "
                            "sequential reasoning -> one seat; verification -> diverse lenses; "
                            "corpus-level claims -> add a backbrief. Shapes: partition (shards "
                            "over a corpus -- coverage), lens (same pack, different questions), "
                            "panel (--fan N self-consistency, never verification), adversarial "
                            "(position + refuters), backbrief (non-author raw-access re-check), "
                            "wave (repeat until dry), negotiation (shared-artifact construction "
                            "only). Wrong combinations are refused with the expected shape.")
    # T256. The preset carries the answer CONTRACT and the PARSER for it, so --json comes back
    # structured instead of as text you regex apart. Five fans in one day each ended with a
    # throwaway parser, and every parsing error of that session lived in those, not in the fan.
    ask_p.add_argument("--preset", default="",
                       help="named answer contract, e.g. 'findings' (FINDINGS/REASONING/CHECK/"
                            "BLIND). Supplies the contract to every branch AND parses the "
                            "answers back, so --json returns structured results. Use with "
                            "--lens/--lens-file.")
    ask_p.add_argument("--lens", action="append", default=[], metavar="QUESTION",
                       help="one branch per --lens, each with the preset's contract appended. "
                            "Repeatable. The lens leads, the contract follows.")
    ask_p.add_argument("--lens-file", dest="lens_file", default="", metavar="PATH",
                       help="one lens per line; blanks and # comments skipped, so a lens file "
                            "can record WHY each lens is there -- the part that rots first.")
    ask_p.add_argument("--workers", type=int, default=None,
                       help="fan width (default 6). Merge attention binds before generation "
                            "does -- a fan wider than its integrator makes debt, not progress")
    # The --fan help says the same thing from its own side: a cold-encounter test found
    # 3 of 3 fresh readers expected --peer --fan to fan three asks at the seat, because
    # nothing in either flag's help said otherwise. A conflict documented on only one of
    # two flags is a conflict the reader meets by surprise.
    ask_p.add_argument("--peer", metavar="SEAT",
                       help="T196c: ONE durable ask to a SEAT (send+arm+poll on the "
                            "bus) instead of the stateless helper. The expectation "
                            "outlives --wait; timeout hands back a --status handle. ONE "
                            "seat, ONE ask: cannot be combined with --fan/--prompts-file")
    ask_p.add_argument("--wait", type=float, default=120.0,
                       help="interactive patience in seconds for --peer (default 120); "
                            "the DURABLE expectation keeps redriving after it")
    ask_p.add_argument("--poll", type=float, default=2.0,
                       help="poll interval for --peer (default 2s)")
    ask_p.add_argument("--bg", action="store_true",
                       help="run this ask in a DETACHED child and return a handle "
                            "immediately -- the answer waits in a file instead of your "
                            "context. Fan out without drowning")
    ask_p.add_argument("--get", metavar="HANDLE",
                       help="read a background ask: RUNNING / DONE / FAILED / ORPHANED, "
                            "each with what to do now. A READ, so it cannot be combined "
                            "with --bg (which is a spawn) -- passing both is refused "
                            "rather than silently picking one")
    ask_p.add_argument("--list", action="store_true",
                       help="recent background asks, newest first")
    ask_p.add_argument("--bg-child", dest="bg_child", metavar="HANDLE",
                       help=argparse.SUPPRESS)
    ask_p.add_argument("--no-continue", dest="continue_on_cut", action="store_false",
                       default=True,
                       help="do NOT resume a CUT answer. Continuation is ON by default: "
                            "with no token ceiling, a cut means the model hit its OWN "
                            "limit, and stitching costs one completion while a re-ask "
                            "pays for the whole prompt again. Never fires for a STARVED "
                            "answer -- there is nothing to continue")
    ask_p.add_argument("--continuations", type=int, default=2, metavar="N",
                       help="how many continuations --continue may spend (default 2); "
                            "running out still reports PARTIALLY, never a clean done")
    ask_p.add_argument("--with", dest="with_files", action="append", metavar="PATH",
                       help="inline a repo file into the ask, WITH LINE NUMBERS, so the "
                            "helper can cite file:line instead of reasoning blind. "
                            "Repeatable; one shared char budget; truncation and "
                            "unreadable paths are stated, never silently dropped")
    ask_p.add_argument("--launch", action="store_true",
                       help="with --peer: if nobody is home, LAUNCH the seat first, wait "
                            "for it to attend, then ask. The launcher's singleton gate is "
                            "the only single-flight; an ambiguous peer is never guessed")
    ask_p.add_argument("--launch-wait", type=float, default=60.0, metavar="SEC",
                       help="how long to wait for a launched seat to attend (default 60); "
                            "readiness is a liveness probe, never a sleep")
    ask_p.add_argument("--status", metavar="ASK_ID",
                       help="T196d: render one durable ask's honest state (seven states "
                            "incl UNKNOWN) and what to do now. Read-only; always exit 0")
    ask_p.add_argument("--as", dest="as_agent", default="",
                       help="the SENDER seat the ask belongs to (expectations are "
                            "per-sender; default $AKASHIC_AGENT_ID or claude)")
    ask_p.add_argument("--json", action="store_true")
    ask_p.set_defaults(fn=cmd_ask)

    dsc = sub.add_parser("discord", help="watch the fleet from your phone (T223, OUTBOUND "
                                         "ONLY). A webhook URL is write-only, so this opens "
                                         "no command channel -- inbound needs an identity "
                                         "gate and does not ship until it exists")
    dsc.add_argument("action", nargs="?", default="status",
                     choices=["status", "test", "send"],
                     help="status = is it configured and what forwards; EXITS 0 EVEN WHEN "
                          "UNCONFIGURED, because opt-in-and-unset is a state rather than a "
                          "failure, and it prints the setup steps. test = post a real line "
                          "so you can confirm it lands. send = forward one message, and an "
                          "explicit send BYPASSES the kind allowlist (the person typing the "
                          "command is the selection); only the automatic feed filters.")
    dsc.add_argument("--text", default="", help="body for `send`")
    dsc.add_argument("--kind", default="chat", help="kind for `send` (default chat)")
    dsc.add_argument("--json", action="store_true")
    dsc.set_defaults(fn=cmd_discord)

    sf = sub.add_parser("sift", help="the NESTED ask (T217): evidence -> hat fan -> curator "
                                     "pairs -> DISSENT FIRST. Use it when the answer needs "
                                     "more reading than fits in one context and you want "
                                     "the disagreements, not a summary")
    sf.add_argument("terms", nargs="+", help="the word(s) to examine, one dossier each")
    sf.add_argument("--hats", default="", help="comma-separated subset of the hats. Default "
                                               "is all of them, because a shared blind spot "
                                               "shows up as AGREEMENT and diverse hats are "
                                               "the only defence against it")
    sf.add_argument("--planes", default="source", help="comma-separated: source|test|doc. "
                                                       "Default source, because two meanings "
                                                       "in the MECHANISM is a defect while "
                                                       "two in prose is often just English")
    sf.add_argument("--junction", action="store_true",
                    help="use JUNCTION evidence instead of breadth: pairs of sites where "
                         "the term is WRITTEN with sites where it is READ. Ask for this "
                         "when the question is 'do the senses MEET' -- a breadth sample can "
                         "enumerate senses but structurally cannot show a producer and its "
                         "consumer in one frame, which is what made the junction hat vote "
                         "NO_FORK on a term whose fork cost six turns")
    sf.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="build and show the evidence packs, spend NOTHING. Run this first: "
                         "a fan answers faithfully about whatever you hand it, so verifying "
                         "the evidence is the step that decides whether any finding is real")
    sf.add_argument("--workers", type=int, default=20,
                    help="fan concurrency (default 20); branches are HTTP requests, not seats")
    sf.add_argument("--max-occurrences", type=int, default=120, dest="max_occurrences",
                    help="cap per pack. The cap SAMPLES ROUND-ROBIN ACROSS FILES -- every "
                         "file contributes its first occurrence before any file contributes "
                         "a second -- so a term in 163 files still reaches the helper as 163 "
                         "files, not as the first few alphabetically. (It is also always "
                         "reported in the pack's blind list; a rate over a cap is not a rate "
                         "over the corpus.)")
    sf.add_argument("--out", default="", help="write the full JSON record here (the dossiers "
                                              "are the durable artifact; the console render "
                                              "is a summary and clips)")
    sf.add_argument("--json", action="store_true")
    sf.set_defaults(fn=cmd_sift)

    fr = sub.add_parser("friction", help="collaboration-friction readout from existing "
                                         "evidence (T196a): episodes, dead-rate, "
                                         "time-to-settle. Read-only")
    fr.add_argument("agent_id", help="whose asks to report on (the sender seat)")
    fr.add_argument("--window-h", dest="window_h", type=float, default=168,
                    help="terminal-event window in hours (default 168 = 7d)")
    fr.add_argument("--json", action="store_true")
    fr.set_defaults(fn=cmd_friction)

    # D1: doc new — the library seeding door
    # T258: the callsign ceremony's door. Three verbs because the ceremony has three moves --
    # a peer drafts, a human ratifies, anyone can read. The registry refuses self-nomination and
    # foreign receipts, so the rules cannot be skipped by using the door instead of the module.
    rp = sub.add_parser("report", help="scaffold a visual report with the design kit inlined (T275)")
    rp.add_argument("--title", default="", help="the <title>: names the browser tab and the gallery card")
    rp.add_argument("--eyebrow", default="Akashic Aurora", help="small mono line above the headline")
    rp.add_argument("--out", default="", help="write the scaffold here (default: stdout)")
    rp.add_argument("--crib", action="store_true", help="print the primitive reference and exit")
    rp.set_defaults(fn=cmd_report)

    rsp = sub.add_parser("resident", help="callsign ceremony: nominate / ratify / show a resident's designation")
    rsps = rsp.add_subparsers(dest="sub")
    rnom = rsps.add_parser("nominate", help="propose a callsign for a PEER (never yourself)")
    rnom.add_argument("nominee", help="the agent being named (may not be you)")
    rnom.add_argument("--callsign", required=True, help="the proposed callsign")
    rnom.add_argument("--receipt", action="append", required=True,
                      help="lesson experiment_name the nominee AUTHORED (repeatable); a receipt "
                           "someone else wrote is a recollection and is refused")
    rnom.add_argument("--by", required=True, help="you, the nominator")
    rnom.add_argument("--vendor", default="", help="AI vendor (mutable: a model upgrade must not orphan the archive)")
    rnom.add_argument("--family", default="", help="family name")
    rnom.add_argument("--team", default="", help="team or group")
    rnom.add_argument("--number", default=None, help="individual short id")
    rnom.add_argument("--note", default="", help="one sentence connecting the receipt to the name")
    rnom.set_defaults(fn=cmd_resident)
    rrat = rsps.add_parser("ratify", help="confirm a nominated callsign (rule 3: a human ratifies)")
    rrat.add_argument("nominee")
    rrat.add_argument("--callsign", required=True)
    rrat.add_argument("--by", required=True, help="the ratifier")
    rrat.set_defaults(fn=cmd_resident)
    rsho = rsps.add_parser("show", help="render a resident's designation and the receipts behind it")
    rsho.add_argument("nominee", nargs="?", default="")
    rsho.set_defaults(fn=cmd_resident)
    # T259: the identity/role split. An assignment is an EVENT (append-only); current role is
    # a projection; "All Jesters on Red of exercise 7" is `resident roles --role --side --exercise`.
    rasg = rsps.add_parser("assign", help="record that a resident is operating as a role (an event, never a field)")
    rasg.add_argument("nominee", help="the resident taking the role")
    rasg.add_argument("--role", required=True, help="the job (Jester, Oracle, Premise-Check, ...)")
    rasg.add_argument("--side", default="", help="team side for the exercise (Red, Blue, ...)")
    rasg.add_argument("--exercise", default="", help="which exercise/round this assignment belongs to")
    rasg.add_argument("--by", required=True,
                      help="the assigner. by == agent is LEGAL and renders self-declared; "
                           "anyone else renders assigned (provenance is derived, not a flag)")
    rasg.set_defaults(fn=cmd_resident)
    # T267: POSTING, not naming. Rule 1 forbids naming yourself; it says nothing about where
    # you are posted, and posting is an org decision -- so it is its own verb rather than a
    # re-nomination that would pollute the callsign history with records deciding nothing.
    rplc = rsps.add_parser("place", help="post a resident to a family/team/number (not a re-naming)")
    rplc.add_argument("nominee", help="the resident being posted")
    rplc.add_argument("--family", default="", help="standing working group (persists across exercises)")
    rplc.add_argument("--team", default="", help="standing disposition (the per-exercise SIDE is `assign`)")
    rplc.add_argument("--number", default=None, help="individual short id within the family")
    rplc.add_argument("--vendor", default="",
                      help="re-home to a different substrate -- vendor is MUTABLE by design, so "
                           "a model upgrade is a flagged change and never an orphaned archive")
    rplc.add_argument("--by", required=True, help="who is posting them")
    rplc.set_defaults(fn=cmd_resident)
    rros = rsps.add_parser("roster", help="who is in a family or team -- the thing routing addresses")
    rros.add_argument("--family", default="")
    rros.add_argument("--team", default="")
    rros.set_defaults(fn=cmd_resident)
    rrol = rsps.add_parser("roles", help="query assignments: e.g. --role Jester --side Red --exercise E7")
    rrol.add_argument("--agent", default="", help="filter to one resident")
    rrol.add_argument("--role", default="")
    rrol.add_argument("--side", default="")
    rrol.add_argument("--exercise", default="")
    rrol.add_argument("--provenance", default="", help="assigned | self-declared")
    rrol.set_defaults(fn=cmd_resident)

    dsp = sub.add_parser("doc", help="seed a new doc with its header contract (library door)")
    dsps = dsp.add_subparsers(dest="sub")
    dnew = dsps.add_parser("new", help="create a new doc with header + canon name + home")
    dnew.add_argument("--type", required=False, default="", help="atom type: contract|map|design|brief|report|chronicle|ledger|ruling (--from-bus infers from message kind)")
    dnew.add_argument("--title", required=True, help="slug (lowercase, hyphens) — becomes the filename")
    dnew.add_argument("--arc", default="", help="arc label or T-number (absent = inferred from the seat's claimed ledger task)")
    dnew.add_argument("--seats", default="", help="authors (comma-sep); first seat drives arc inference")
    dnew.add_argument("--body", default="", help="atom body text (short); use --body-file for real bodies")
    dnew.add_argument("--body-file", default="", dest="body_file", help="read the atom body from a file (W63 long-body transport)")
    dnew.add_argument("--category", action="append", default=None, help="governed roster category (repeatable, max 3; merged with auto-classify)")
    dnew.add_argument("--draft", action="store_true", help="born status:draft — dump-and-go; wrap sweep + lint curate")
    dnew.add_argument("--gist", default="", help="one-line abstract (<=140 chars; auto-derived from body if absent)")
    dnew.add_argument("--body-type", default="", dest="body_type",
                      help="v1.1 datatype flag: markdown|code|json|tabular|transcript "
                           "(absent = auto-detect, stamped body_type_source=auto)")
    dnew.add_argument("--from-bus", default="", dest="from_bus", help="file ONE bus message (stream id) as a conversation-atom w/ provenance; born draft; opt-in only")
    dnew.add_argument("--cite", action="append", default=None, help="atom id this artifact discusses (repeatable; rel=discusses)")
    dnew.add_argument("--zone", default="", help="DEPRECATED (atoms have one home: docs/library/<type>/); ignored")
    dnew.set_defaults(fn=cmd_doc)

    # adopt: bring an EXISTING loose .md through the same door. The rescue path for work
    # filed by seats that cannot commit, into zones rule-13 refuses (research/** since P3).
    # Non-destructive: the source file is never touched.
    dado = dsps.add_parser("adopt", help="mint an EXISTING loose .md as an atom (source untouched)")
    dado.add_argument("path", help="path to the loose .md to adopt")
    dado.add_argument("--type", default="", help="atom type (absent = inferred from the filename)")
    dado.add_argument("--title", default="", help="slug (absent = inferred from the filename)")
    dado.add_argument("--seats", default="", help="authors (absent = inferred from the filename)")
    dado.add_argument("--arc", default="", help="arc label or T-number")
    dado.add_argument("--category", action="append", default=None, help="governed roster category")
    dado.add_argument("--draft", action="store_true", help="born status:draft")
    dado.add_argument("--gist", default="", help="one-line abstract (auto-derived if absent)")
    dado.add_argument("--cite", action="append", default=None, help="atom id this artifact discusses")
    dado.set_defaults(fn=cmd_doc)

    ap = sub.add_parser("tag-anti-pattern", help="tag an EXISTING lesson as a reusable known-bad")
    ap.add_argument("agent_id"); ap.add_argument("--experiment", required=True)
    ap.add_argument("--name", required=True, help="the anti-pattern name/slug")
    ap.add_argument("--reason", default=""); ap.add_argument("--json", action="store_true")
    ap.set_defaults(fn=cmd_tag_anti_pattern)

    r = sub.add_parser("recall", help="search past lessons (no query = list all)")
    r.add_argument("query", nargs="?", default=""); r.add_argument("--json", action="store_true")
    r.add_argument("--full", default=None, help="pull the FULL record for one lesson's source pointer "
                    "(e.g. learn:experiment:NAME) -- the one-hop escape from a capped recall-at surface")
    r.add_argument("--agent", default=None,
                   help="T260: scope to ONE author's archive -- 'what has Navi learned about X'. "
                        "The weak-match confession respects the scope (a degraded answer stays a "
                        "subset of the normal one)")
    r.set_defaults(fn=cmd_recall)

    li = sub.add_parser("list", help="list ALL lessons in memory")
    li.add_argument("--json", action="store_true")
    li.set_defaults(fn=cmd_list)

    ra = sub.add_parser("recall-at", help="recall-at-action: relevant lessons/locks for a path or command")
    ra.add_argument("--path", default=None, help="the file path about to be acted on")
    ra.add_argument("--command", default=None, help="the shell command about to run")
    # A composition gesture is a point of action with no path and no command. Without these two,
    # the moment a chunk-ordering rule is worth knowing is a moment recall cannot be asked about.
    ra.add_argument("--gesture", default=None,
                    help="the composition gesture about to happen, e.g. 'add tanh-tonemap after superlinear-highlight'")
    ra.add_argument("--subject", default=None, help="what the bench is currently showing")
    ra.add_argument("--domain", default=None,
                    help="scope to one domain (system|vfx); omit to let the trigger decide")
    ra.add_argument("--agent-id", dest="agent_id", default=None, help="who is asking (defaults to $AKASHIC_AGENT_ID)")
    ra.add_argument("--limit", type=int, default=3, help="max items to surface (default 3)")
    ra.add_argument("--hint-style", dest="hint_style", choices=["cli", "tool"], default="cli",
                    help="escape-hint vocabulary: cli verbs (default) or tool-loop tool names (T048)")
    ra.add_argument("--json", action="store_true")
    ra.set_defaults(fn=cmd_recall_at)

    rf = sub.add_parser("recall-feedback", help="mark a recalled lesson useful/noise (teaches recall what helps)")
    rf.add_argument("--source", required=True, help="the lesson's source pointer, e.g. learn:experiment:NAME")
    rf.add_argument("--useful", action="store_true", help="it changed what you did (default)")
    rf.add_argument("--noise", action="store_true", help="it was off-target")
    rf.add_argument("--domain", default=None,
                    help="which domain it was useful IN (system|vfx) -- credit in 2+ domains "
                         "promotes the lesson to domain-general")
    rf.set_defaults(fn=cmd_recall_feedback)

    rc = sub.add_parser("recall-curate",
                        help="bench surfaced-never-credited lessons + prune ghost counters (report; --apply stamps)")
    rc.add_argument("--apply", action="store_true", help="apply the report (default: report only)")
    rc.add_argument("--forge-audit", action="store_true",
                    help="Forge F0 data-sufficiency audit vs the pre-registered criteria (read-only)")
    rc.add_argument("--forge-check", metavar="EXPERIMENT",
                    help="Forge F1: gate a proposed edit to EXPERIMENT's recommendation (needs --draft)")
    rc.add_argument("--draft", metavar="FILE", help="file holding the proposed recommendation text")
    rc.add_argument("--forge-propose", action="store_true",
                    help="Forge F2: optimizer pass (deepseek proposes, gate adjudicates, human applies)")
    rc.add_argument("--forge-proposals", action="store_true", help="list pending optimizer proposals")
    rc.add_argument("--limit", type=int, help="max targets for --forge-propose (default 2)")
    rc.add_argument("--json", action="store_true")
    rc.set_defaults(fn=cmd_recall_curate)

    au = sub.add_parser("audit", help="belief-vs-state audit: labeled MATCH/DRIFT rows over "
                        "durable beliefs vs ground truth (v1: VERBS registry<->parser)")
    au.add_argument("--domain", help="comma-separated domain filter (default: all registered)")
    au.add_argument("--ground", default="registry",
                    help="which source renders as canonical -- wording only, never the verdict")
    au.add_argument("--json", action="store_true")
    au.set_defaults(fn=cmd_audit)

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
    nt.add_argument("--title", default="", help="short stable title (re-noting it supersedes the prior; "
                                                "required for writes -- --get/--retire stand alone)")
    nt.add_argument("--note", default="", help="the note / decision body")
    nt.add_argument("--context", default="", help="optional supporting context")
    nt.add_argument("--category", default="", help="route-hint category")
    nt.add_argument("--supersedes", default=None, help="explicit prior note id to retire")
    nt.add_argument("--retire", default=None, metavar="ID_OR_TITLE",
                    help="tombstone a one-shot note (no successor); reversible in the store")
    nt.add_argument("--get", default=None, metavar="ID_OR_TITLE",
                    help="W01: print ONE full note body (title resolves the active head; "
                         "an explicit id reads superseded history, labeled)")
    nt.add_argument("--session", default="", help="session id")
    nt.add_argument("--json", action="store_true")
    nt.set_defaults(fn=cmd_note)

    nts = sub.add_parser("notes", help="list active project notes (--project regenerates chronicles/memory.md)")
    nts.add_argument("--limit", type=int, default=25)
    nts.add_argument("--days", type=int, default=None)
    nts.add_argument("--project", action="store_true", help="regenerate the chronicles/memory.md digest")
    nts.add_argument("--all", action="store_true",
                     help="archaeology: include superseded/retired notes (tagged)")
    nts.add_argument("--json", action="store_true")
    nts.set_defaults(fn=cmd_notes)

    wr = sub.add_parser("wrap", help="distill this session (commits+lessons+notes) into a DRAFT where-we-are note")
    wr.add_argument("--hours", type=int, default=12, help="look-back window for commits (default 12)")
    wr.add_argument("--grounding", default=None, metavar="PATH|none",
                    help="W37: set the GROUND-FIRST pointer (the voice doc the next seat "
                         "reads before anything else); 'none' declares absence explicitly")
    wr.add_argument("--commit", action="store_true", help="record the draft as a note (default: just preview)")
    wr.add_argument("--title", default=None, help="note title (default: where-we-are <date>)")
    wr.add_argument("--force", action="store_true",
                    help="T074 W8: supersede even a CURATED head (the guard refuses by default)")
    wr.add_argument("--focus", default=None,
                    help="set the CURRENT DIRECTIVE (next-focus note) at decision time -- "
                         "what the next session does FIRST / must NOT do yet; boot renders it "
                         "above the NEXT list")
    wr.add_argument("--route", default=None, metavar="T123,T124",
                    help="T268: route TARGETS for the next window (comma-separated ledger ids). "
                         "--focus records intent; this records WHICH ITEMS, which is what an "
                         "overnight pre-chew actually consumes. Each target gets a resident "
                         "SUGGESTION drawn from that resident's own archive -- a suggestion, "
                         "never an assignment: routing is the human's act")
    wr.set_defaults(fn=cmd_wrap)

    s = sub.add_parser("status", help="honest system status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    sts = sub.add_parser("stats", help="recall-value funnel: surfaced -> helped -> flips -> captured")
    sts.add_argument("--hours", type=float, default=24, help="window for flips/lessons-recorded (default 24)")
    sts.add_argument("--days", type=int, default=None,
                     help="ALSO print a per-day trend over N days (durable records) + the 30d pace")
    sts.add_argument("--silence", action="store_true",
                     help="R2 denominator: fired/silent/by_reason over --hours + replay pointer")
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

    tk = sub.add_parser("task", help="task lifecycle over the governed ledger: propose/approve/claim/"
                                     "start/verify/done/block/list/next (the coordination door)")
    tk.add_argument("rest", nargs=argparse.REMAINDER,
                    help='conductor subcommand + args, e.g.  task list  /  task propose "title"  /  '
                         'task done T001 --commit abc123 --verified-by pytest')
    tk.set_defaults(fn=cmd_task)

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

    ros = sub.add_parser("roster", help="S2 lobby: per-seat worklive (LIVE/STALE proven by "
                                        "beat freshness, never key-existence) + have-summaries")
    ros.add_argument("--json", action="store_true")
    ros.add_argument("--reap", action="store_true",
                     help="S4: explicitly re-home provably-dead seats' stranded mail now")
    ros.add_argument("--by-agent", dest="by_agent", action="store_true",
                     help="T183: one line per LOGICAL agent, stating churn (deaths in the last "
                          "hour) instead of leaving it to be inferred from N last-beat ages. "
                          "Compresses the render, never the record -- raw rows are the default")
    ros.set_defaults(fn=cmd_roster)

    ss = sub.add_parser("season-score", help="T165: score a Season 1 round, or --compare the two "
                                             "rule sets over the same claims")
    ss.add_argument("--round-file", default=None, help="JSON: {claims, verifications, uptime, "
                                                       "fixed_keys}")
    ss.add_argument("--policy", default="v1_doc", help="v1_doc (committed table) | v2_aixcc (W2 proposal)")
    ss.add_argument("--compare", action="store_true", help="score BOTH policies and show the delta")
    ss.add_argument("--policies", action="store_true", help="print each policy and its rationale")
    ss.add_argument("--json", action="store_true")
    ss.set_defaults(fn=cmd_season_score)

    gr = sub.add_parser("grant", help="S-3: mint / revoke / list ACL grants (atomic + audited). "
                                      "NOT an auth boundary -- see the module docstring")
    gr.add_argument("agent_id", nargs="?", help="the seat receiving the grant")
    gr.add_argument("--role", default=None, help="super_admin|admin|member|restricted|quarantined")
    gr.add_argument("--by", default=None, help="the GRANTER's agent id (must hold admin.grant)")
    gr.add_argument("--reason", default=None, help="why -- required; an unexplained grant "
                                                   "is the one nobody can safely revoke later")
    gr.add_argument("--hours", type=float, default=None, help="time box (T151: an observed "
                                                              "time box is a deadline)")
    gr.add_argument("--permanent", action="store_true", help="explicitly permanent (10 of the "
                                                             "11 original grants are)")
    gr.add_argument("--caps", default=None, help="comma-separated cap override (default: role template)")
    gr.add_argument("--path-scope", default=None, help="comma-separated globs (default: role template)")
    gr.add_argument("--request-ref", default=None, help="the ask this grant answers")
    gr.add_argument("--revoke", action="store_true", help="remove the grant (the undo path)")
    gr.add_argument("--list", action="store_true", help="show stored grants, expiring first")
    gr.add_argument("--dry-run", action="store_true", help="print the record, write nothing")
    gr.add_argument("--json", action="store_true")
    gr.set_defaults(fn=cmd_grant)

    dr = sub.add_parser("doctor", help="fleet liveness doctor (L2): progress, not presence")
    dr.add_argument("--agents", default=None, help="comma-separated ids (default: discovered)")
    dr.add_argument("--deploy", action="store_true",
                    help="is THIS machine a working deploy? root, dirs, redis, consoles")
    dr.add_argument("--page", action="store_true",
                    help="emit bus notes for page-grade findings (deduped 1/(agent,state)/hour)")
    dr.add_argument("--progress", action="store_true",
                    help="one elapsed/ETA/%% line per busy agent (the poor-man's bars)")
    dr.add_argument("--json", action="store_true")
    dr.set_defaults(fn=cmd_doctor)

    pr = sub.add_parser("promoted", help="query durable salient Bifrost msgs (kind=bifrost_msg / B2)")
    pr.add_argument("--limit", type=int, default=None)
    pr.add_argument("--since", default=None, help="ISO lower time bound")
    pr.add_argument("--until", default=None, help="ISO upper time bound")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(fn=cmd_promoted)

    lb = sub.add_parser("lookback", help="one question over the rationale corpus: the strategic WHY, layered + drillable (P7)")
    lb.add_argument("question", nargs="+", help="the why/what question, plain words")
    lb.add_argument("--per-layer", type=int, default=None, help="hits per corpus layer (default 3)")
    lb.add_argument("--layers", default=None, help="narrow: docs,research,notes,promoted,chapters,git")
    lb.add_argument("--json", action="store_true")
    lb.set_defaults(fn=cmd_lookback)

    km = sub.add_parser("knowledge-map", help="WALK the lesson/note/doc neighborhood of a topic: surface + edge-walked neighborhood + archive (R8)")
    km.add_argument("query", nargs="*", help="the topic to walk, plain words")
    km.add_argument("--per-layer", type=int, default=None, help="max nodes per layer (default 6)")
    km.add_argument("--json", action="store_true")
    km.set_defaults(fn=cmd_knowledge_map)

    fe = sub.add_parser("fence", help="fence workspace: slots + seal-time method checks; confabulated filenames unrepresentable (R2)")
    fe.add_argument("action", choices=["open", "write", "seal", "pv", "status", "list"])
    fe.add_argument("fence_id", nargs="?", default=None, help="fence id (e.g. t054-design)")
    fe.add_argument("--question", default=None, help="open: the question at stake (M1-BRIEF charter seed)")
    fe.add_argument("--tier", default=None, choices=["full", "lite"], help="open: fence tier (default full)")
    fe.add_argument("--slot", default=None, choices=["brief", "half_a", "half_b", "reconciliation"],
                    help="write/seal: which slot")
    fe.add_argument("--text", default=None, help="write: inline content")
    fe.add_argument("--file", default=None, help="write: read content from a file")
    fe.add_argument("--by", default=None, help="who is acting (agent id -- authorship feeds the independence check)")
    fe.add_argument("--json", action="store_true")
    fe.set_defaults(fn=cmd_fence)

    fw = sub.add_parser("flow", help="OTel-style waterfall of recent message flows across lanes: asks, answers, gaps, duplicate copies exposed (R3)")
    fw.add_argument("agent", nargs="?", default=None, help="only flows touching this agent")
    fw.add_argument("--window", default="6h", help="how far back (e.g. 30m, 6h, 1d; default 6h)")
    fw.add_argument("--limit", type=int, default=12, help="max flows rendered (default 12)")
    fw.add_argument("--json", action="store_true")
    fw.set_defaults(fn=cmd_flow)

    ptr = sub.add_parser("packet-trace", help="N0 dry-run: explain the static route for one packet kind (no send)")
    ptr.add_argument("kind", help="wire kind, e.g. handoff, reply, narration")
    ptr.add_argument("--json", action="store_true")
    ptr.set_defaults(fn=cmd_packet_trace)

    pst = sub.add_parser("packet-stats", help="N0 bounded shadow route/mirror counters")
    pst.add_argument("--json", action="store_true")
    pst.set_defaults(fn=cmd_packet_stats)

    mbx = sub.add_parser("mailbox", help="T095 M0 shadow mailbox: per-message state for an agent (observation only)")
    mbx.add_argument("agent_id", help="whose mailbox to inspect")
    mbx.add_argument("--explain", metavar="REF", help="evidence chain for one message (sha prefix or stream id)")
    mbx.add_argument("--rebuild", action="store_true", help="drop + rebuild the index from the log (determinism receipt)")
    # M3: a retired seat's mail competes with living work forever until somebody adjudicates it.
    # This DECLARES rather than deletes -- legible, reversible, and it inherits the wake
    # suppression because bifrost_wake reads declarations.
    mbx.add_argument("--retire-ghosts", action="store_true", dest="retire_ghosts",
                     help="declare `decline` on old unadjudicated mail from senders with no live "
                          "seat (report only; add --apply to write). The operator is never a ghost.")
    mbx.add_argument("--apply", action="store_true",
                     help="with --retire-ghosts: actually write the declarations")
    mbx.add_argument("--min-age-h", type=float, default=24.0, dest="min_age_h",
                     help="with --retire-ghosts: how old mail must be to be sweepable (default 24)")
    mbx.add_argument("--limit-scan", type=int, default=5000, dest="limit_scan",
                     help="with --retire-ghosts: max entries to examine (default 5000, the index cap)")
    mbx.add_argument("--min-evidence", choices=["unhandled", "consumed", "replied", "acked"],
                     default=None, help="show only entries at or below this evidence tier")
    # M1: the mailbox stops being read-only. These three are the product receipt's verbs.
    mbx.add_argument("--open", metavar="SHA", dest="open_sha",
                     help="M1: say SEEN once and print the FULL BODY. Appends one idempotent seen "
                          "receipt per (message, incarnation); advances NO cursor. Seen never "
                          "means consumed, handled, agreed, or settled.")
    mbx.add_argument("--state", metavar="SHA", dest="state_sha",
                     help="M1: everything about one message in ONE hop -- body, who has opened it, "
                          "the declared intent, and read_but_undeclared")
    mbx.add_argument("--intent", metavar="SHA", dest="intent_sha",
                     help="M1: declare what you will DO about this message (needs --as)")
    mbx.add_argument("--as", dest="intent_kind", choices=sorted(("act", "decline", "delegate", "defer")),
                     help="the declaration: act | decline | delegate | defer")
    mbx.add_argument("--to", dest="intent_to", default="",
                     help="required with --as delegate: an unrouted delegation is a drop")
    mbx.add_argument("--note", dest="intent_note", default="", help="optional free-text reason")
    mbx.add_argument("--backfill", action="store_true",
                     help="M1: recover bodies for entries indexed before body storage, WITHOUT "
                          "dropping the index (unlike --rebuild). Unrecoverable entries keep "
                          "their state and stay honestly marked.")
    mbx.add_argument("--incarnation", default=None,
                     help="your session suffix. Defaults to $AKASHIC_SESSION8 or 'unknown'. It is "
                          "load-bearing: seen receipts are keyed per incarnation so a FRESH seat "
                          "can tell that a PRIOR one read this and declared nothing.")
    mbx.add_argument("--json", action="store_true")
    mbx.set_defaults(fn=cmd_mailbox)

    ak = sub.add_parser("bifrost-ack", help="durably record you HANDLED a salient bus message (P6)")
    ak.add_argument("agent_id", help="your stable agent id (the actor)")
    ak.add_argument("msg_id", help="the bus message id (from promoted/bifrost-sync output)")
    ak.add_argument("--note", default=None, help="optional one-line what-was-done")
    ak.add_argument("--json", action="store_true")
    ak.set_defaults(fn=cmd_bifrost_ack)

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
    bs.add_argument("--traces", action="store_true",
                    help="W4: expand folded trace-class telemetry (default collapses it)")
    bs.add_argument("--json", action="store_true")
    bs.set_defaults(fn=cmd_bifrost_sync)

    sby = sub.add_parser("bifrost-standby",
                         help="T084-CL-2: turn-end ritual in ONE verb -- drain, seat report, then "
                              "BLOCK as the wake listener's parent (run as a background task)")
    sby.add_argument("agent_id", help="your stable agent id (e.g. claude)")
    sby.add_argument("--session", default="", help="session id for the per-session wake seat "
                                                   "(default: harness session env)")
    sby.add_argument("--no-listen", action="store_true", help="drain + report only; do not block")
    sby.add_argument("--limit", type=int, default=None)
    sby.set_defaults(fn=cmd_bifrost_standby)

    snd = sub.add_parser("bifrost-send", help="send a message to another agent on the bus")
    snd.add_argument("agent_id", help="your stable agent id (the SENDER, e.g. claude)")
    snd.add_argument("text", nargs="*", default=[],
                     help="the message text (or use --text-file for long/flag-bearing bodies)")
    snd.add_argument("--text-file", default=None, metavar="PATH",
                     help="T083-C3-1: read the message body from PATH instead of argv -- USE THIS "
                          "when the body contains anything flag-shaped ('--foo') or is long "
                          "(git commit -F precedent; argv text with flags in prose WILL misparse)")
    snd.add_argument("--to", default="", help="recipient agent id (e.g. deepseek); omit with --broadcast")
    snd.add_argument("--kind", default="chat", help="chat|request|question|handoff|... (default chat)")
    snd.add_argument("--broadcast", action="store_true", help="send to ALL agents instead of one --to")
    snd.add_argument("--expect-reply-within", type=int, default=-1, metavar="SECONDS",
                     help="RB-29: arm a sender-side reply deadline (clamped >=30s; 3 redrives then a "
                          "loud expectation_dead; swept at boot/bifrost-sync). DIRECTED asks "
                          "(request/handoff/question) AUTO-arm a default window if unset; pass 0 to opt out.")
    snd.add_argument("--to-incarnation", default=None, metavar="SESSION8",
                     help="T073: address ONE session of the target agent (>=8-char session-id "
                          "prefix) -- that seat wakes even on same-agent mail (the twin channel)")
    snd.add_argument("--json", action="store_true")
    snd.set_defaults(fn=cmd_bifrost_send)

    sbp = sub.add_parser("suite-baseline", help="the test-suite receipt (W34): record a "
                                                "pytest run's failures + lanes; the next "
                                                "seat diffs (new/fixed/inherited)")
    sbp.add_argument("agent_id", help="the recording seat")
    sbp.add_argument("--from-file", dest="from_file", default=None,
                     help="pytest terminal output to ingest")
    sbp.add_argument("--sha", default="", help="commit sha (default: git rev-parse HEAD)")
    sbp.add_argument("--check", action="store_true",
                     help="diff --from-file against the baseline instead of recording")
    sbp.add_argument("--show", action="store_true", help="print the baseline boot line")
    sbp.add_argument("--whose", nargs="?", const="", default=None, metavar="PYTEST_ARGS",
                     help="run the tests and ATTRIBUTE every failure: YOURS / UNKNOWN / "
                          "LIKELY_INHERITED / INHERITED, each with what to do. Replaces "
                          "the manual git-stash bisect. Says UNKNOWN rather than guessing "
                          "when the baseline is stale -- and UNKNOWN never exits nonzero, "
                          "because 'I cannot tell' must not become an accusation. "
                          'e.g. --whose "tests/ -k ask"')
    sbp.set_defaults(fn=cmd_suite_baseline)

    dr = sub.add_parser("bifrost-drain", help="request a runner's GRACEFUL exit: finish "
                                              "current message -> release lock -> exit 0 "
                                              "(the TaskStop restart-tax killer)")
    dr.add_argument("agent_id", help="you (the requester)")
    dr.add_argument("--to", required=True, help="the runner agent to drain (e.g. deepseek)")
    dr.add_argument("--reason", default="", help="why (rides the runner's exit line)")
    dr.set_defaults(fn=cmd_bifrost_drain)

    pz = sub.add_parser("bifrost-pause", help="freeze bus auto-responders (human barge-in); "
                                              "--soft to let seats finish first")
    pz.add_argument("--reason", default=""); pz.add_argument("--by", default="user")
    pz.add_argument("--ttl", type=int, default=None,
                    help="self-heal seconds (RB-30) -- ceremony/automation pauses should "
                         "ALWAYS set this so a mid-ceremony crash can't freeze the fleet")
    pz.add_argument("--soft", action="store_true",
                    help="PAUSE NUDGE: seats FINISH the message in hand, then hold. Default "
                         "(hard) pause is a mid-turn interrupt and ABANDONS in-flight work; "
                         "drain is graceful but EXITS the runner. --soft is the third thing: "
                         "graceful AND resumable without a relaunch")
    pz.add_argument("--json", action="store_true")
    pz.set_defaults(fn=cmd_bifrost_pause)

    rz = sub.add_parser("bifrost-resume", help="un-freeze bus auto-responders")
    rz.set_defaults(fn=cmd_bifrost_resume)

    skp = sub.add_parser("bifrost-skip-to-now",
                         help="T076a: advance an agent's consume cursors to stream tails "
                              "(audited echo-mountain escape; requires pause + --reason)")
    skp.add_argument("agent_id", help="whose cursors to skip")
    skp.add_argument("--by", required=True, help="who authorizes (rides the audit event)")
    skp.add_argument("--reason", required=True, help="why (refuse-loud without one)")
    skp.add_argument("--json", action="store_true")
    skp.set_defaults(fn=cmd_bifrost_skip_to_now)

    ndg = sub.add_parser("bifrost-nudge", help="targeted fidelity signal to ONE peer (interrupt|steer|inform)")
    ndg.add_argument("agent_id", help="your stable agent id (the sender, e.g. claude)")
    ndg.add_argument("text", nargs="+", help="what you need the peer to look at / adopt")
    ndg.add_argument("--to", default="", help="the ONE peer to signal (e.g. deepseek)")
    ndg.add_argument("--mode", default="interrupt",
                     help="interrupt (hard, default) | steer (soft, fold into current task) | inform (ambient)")
    ndg.add_argument("--json", action="store_true")
    ndg.set_defaults(fn=cmd_bifrost_nudge)

    si_ = sub.add_parser("seat-identity",
                        help="declare/show THIS session's seat id (binding beats the shared env)")
    si_.add_argument("agent_id", nargs="?", default="",
                     help="the seat id to bind; omit to just show the current resolution")
    si_.add_argument("--session", default="", help="session id (default: this process's)")
    si_.add_argument("--clear", action="store_true", help="drop this session's binding")
    si_.set_defaults(fn=cmd_seat_identity)

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

    blb = sub.add_parser("bifrost-fetch", help="fetch a spilled payload by content-addressed ref "
                                      "(the retrieval half of T113's oversize-send spill)")
    blb.add_argument("--get", default="", help="the blob:<sha> ref from a spill notice")
    blb.add_argument("--out", default="", help="write bytes to this file instead of stdout")
    blb.set_defaults(fn=cmd_blob)

    # ---- T278 THE EYE (S0/S1 door; design atom the-eye-design-v2_208b26) ----
    eye = sub.add_parser("eye", help="THE EYE: the transcript plane as terrain -- ingest "
                                     "(incremental, coverage-honest), find (phrase, S0; the "
                                     "grammar lands S1), get (address -> verbatim L0)")
    eye_sub = eye.add_subparsers(dest="eye_cmd", required=True)
    eye_in = eye_sub.add_parser("ingest", help="index every session JSONL incrementally; "
                                              "the report IS the coverage contract")
    eye_in.add_argument("--json", action="store_true")
    eye_fd = eye_sub.add_parser("find", help="S1: the grammar door -- facets AND together, "
                                             "the phrase is the fallback within the slice; "
                                             "malformed selectors refuse with the expected "
                                             "shape; the envelope carries degraded honesty "
                                             "+ its own token price")
    eye_fd.add_argument("query", nargs="?", default="", help="phrase (optional when faceting)")
    eye_fd.add_argument("--who", "--voice", dest="who", default="",
                        choices=["", "operator", "agent", "system"],
                        help="the grammar's who= (conservative voice label)")
    eye_fd.add_argument("--kind", default="", help="event type: user|assistant|queue-operation|system")
    eye_fd.add_argument("--session", default="", help="one session's terrain only")
    eye_fd.add_argument("--as-of", dest="as_of", default=None,
                        help="the temporal law: only events knowable by this ISO date")
    eye_fd.add_argument("--limit", type=int, default=20)
    eye_fd.add_argument("--json", action="store_true")
    eye_gt = eye_sub.add_parser("get", help="resolve an event address (session:line) to the "
                                            "verbatim record -- the citation resolver primitive")
    eye_gt.add_argument("event_id", help="the address, e.g. 2b1b8946-...:1955")
    eye_gt.add_argument("--json", action="store_true")
    eye_fq = eye_sub.add_parser("freq", help="S3, HIS axis: a pattern family (phrasings OR'd, "
                                             "deduped) -> counts, operator-sessions, span, "
                                             "refs, and a mechanical verdict (unheard / "
                                             "mentioned-once / recurring / standing-directive)")
    eye_fq.add_argument("patterns", nargs="+", help="one or more phrasings of the same idea")
    eye_fq.add_argument("--json", action="store_true")
    eye_st = eye_sub.add_parser("stats", help="S5: crisp numerics -- counts by voice/kind, "
                                              "sessions, TIME-FOG (the share every as_of "
                                              "query is blind to)")
    eye_st.add_argument("--json", action="store_true")
    eye_ov = eye_sub.add_parser("overview", help="S5: the region map -- sessions as places, "
                                                 "each with counts and span")
    eye_ov.add_argument("--json", action="store_true")
    eye_zm = eye_sub.add_parser("zoom", help="S2: LOD navigation -- a session -> its L2 "
                                             "digest + L1 children; an L1 id -> the exchange "
                                             "+ event refs. Extractive pyramid, staleness "
                                             "shown as fog")
    eye_zm.add_argument("addr", help="session name or <session>/L1:NNN")
    eye_zm.add_argument("--rebuild", action="store_true", help="rebuild the pyramid first")
    eye_zm.add_argument("--json", action="store_true")
    eye.set_defaults(fn=cmd_eye)

    # ---- T099 V0 self-tooling (docs/library/design/20260701_self-tooling-arc-reconciled-design-agent_29f578.md) ----
    cap = sub.add_parser("capture", help="full-fidelity bus read: unwrap a message by stream id "
                                         "(or last N from an agent) + optional verbatim-persist "
                                         "(the 5x-hand-written extractor, now a verb)")
    cap.add_argument("ref", nargs="?", default="", help="stream id (e.g. 1784600898568-0); omit with --from-agent")
    cap.add_argument("--from-agent", default="", help="newest messages from this sender instead of an id")
    cap.add_argument("--count", type=int, default=3, help="with --from-agent: how many (default 3)")
    cap.add_argument("--persist", default="", metavar="PATH",
                     help="write a verbatim capture file (Status header + body) to PATH")
    cap.add_argument("--title", default="", help="capture doc title (with --persist)")
    cap.add_argument("--json", action="store_true")
    cap.set_defaults(fn=cmd_capture)

    al = sub.add_parser("alias", help="toolbelt authoring: mint/list/retire agent-authored verb "
                                      "compositions (sugar-only; honesty labels; quota)")
    al.add_argument("agent_id", help="whose toolbelt (the author)")
    al.add_argument("action", choices=["mint", "list", "retire", "history"])
    al.add_argument("name", nargs="?", default="", help="alias name (mint/retire/history)")
    al.add_argument("--step", action="append", default=[], metavar="'verb arg arg'",
                    help="one step per flag, shell-style quoted; steps run in order (mint)")
    al.add_argument("--evidence", default="GUESS", help="VERIFIED|INFER|GUESS (default GUESS -- "
                                                        "untested sugar confesses)")
    al.add_argument("--tested-against", default=None, help="pin id proving this alias (upgrades evidence)")
    al.add_argument("--why", default="", help="one line: the felt friction this kills")
    al.add_argument("--family", default="UNSORTED",
                    help="Halo-caste family (SENTINELS guards | MONITORS watchers | CONSTRUCTORS "
                         "authoring | RETRIEVERS fetchers | ENGINEERS recovery | CARTOGRAPHERS "
                         "mapping | LIBRARIANS memory | WAR-GAMES drills)")
    al.add_argument("--reason", default="", help="retire reason")
    al.add_argument("--json", action="store_true")
    al.set_defaults(fn=cmd_alias)

    rn = sub.add_parser("run", help="execute a toolbelt alias: run <agent> <name> "
                                    "(explicit door -- a real verb can never be shadowed)")
    rn.add_argument("agent_id", help="whose toolbelt")
    rn.add_argument("name", help="the alias to run")
    rn.add_argument("args", nargs="*", default=[], help="macro args ($1 $2 ... substitution)")
    rn.add_argument("--dry", action="store_true", help="print the resolved steps, execute nothing")
    rn.set_defaults(fn=cmd_run)

    bn = sub.add_parser("bench", help="S0 triage bench (scry-to-bottom): list/park/unpark stale "
                                      "asks -- bottomed so fresh mail flows, NEVER dropped; "
                                      "sender always notified (RB-29)")
    bn.add_argument("agent_id", help="whose bench")
    bn.add_argument("action", nargs="?", default="list", choices=["list", "park", "unpark"])
    bn.add_argument("ref", nargs="?", default="", help="park: inbox stream id | unpark: parked_id")
    bn.add_argument("--reason", default="stale", help="park: why (rides the receipt + sender note)")
    bn.add_argument("--by", default="", help="who authorizes (defaults to agent_id)")
    bn.set_defaults(fn=cmd_bench)

    # --- tool <list|run> (T099 · play-tier sandbox) --------------------------------
    tl = sub.add_parser("tool", help="play-tier sandbox: list/run draft tools (data/play/<agent>/)")
    tl_subs = tl.add_subparsers(dest="tool_cmd")
    tl_list = tl_subs.add_parser("list", help="list play tools for an agent or all seats")
    tl_list.add_argument("agent", nargs="?", default="",
                         help="agent id to list (default: all seats)")
    tl_list.set_defaults(fn=cmd_tool_list)
    tl_run = tl_subs.add_parser("run", help="run one play tool in the sandbox")
    tl_run.add_argument("ref", help="tool reference: <agent>/<tool>, e.g. kimi/premonition")
    tl_run.add_argument("args", nargs="*", default=[],
                        help="arguments passed to the play tool")
    tl_run.add_argument("--timeout", type=float, default=0,
                        help="timeout seconds (default: AKASHIC_PLAY_TIMEOUT_S or 30)")
    tl_run.add_argument("--no-sandbox", action="store_true",
                        help="run unsandboxed (operator override for risky drafts)")
    tl_run.set_defaults(fn=cmd_tool_run)

    kt = sub.add_parser("kata", help="grammar-prove a toolbelt alias against the door itself; "
                                     "GREEN levels GUESS/INFER up to VERIFIED (kimi's B4: "
                                     "'the tool that tells you when your tools are real')")
    kt.add_argument("agent_id", help="whose toolbelt")
    kt.add_argument("name", help="the alias to kata")
    kt.set_defaults(fn=cmd_kata)

    ts = sub.add_parser("toast", help="gratitude-with-receipt (T099 BETA-2): toast a peer whose "
                                      "lesson saved you hops; receipt verifies against the "
                                      "learning store or the send REFUSES")
    ts.add_argument("agent_id", help="you (the toaster)")
    ts.add_argument("to", help="the peer being toasted")
    ts.add_argument("receipt", help="their experiment name (the receipt)")
    ts.add_argument("--credit", default="", help="what did their lesson save you? (required, short)")
    ts.add_argument("--force", action="store_true",
                    help="send an unverified receipt honestly labeled GUESS")
    ts.add_argument("--json", action="store_true")
    ts.set_defaults(fn=cmd_toast)

    cbs = sub.add_parser("clobber-scan", help="W47 (kimi's design): flag unconditional "
                                              "writes to shared control keys in a file -- "
                                              "the fence-review reviewer-prompt")
    cbs.add_argument("path", help="the file to scan (a ceremony/diff under review)")
    cbs.add_argument("--json", action="store_true")
    cbs.set_defaults(fn=cmd_clobber_scan)

    ta = sub.add_parser("tally", help="W48 (kimi): blind-counter consensus matrix -- "
                                      "scan research/ for counters naming an opening, "
                                      "align their q-ids, print agree/conflict at a glance")
    ta.add_argument("opening", help="the opening file (repo-relative or absolute)")
    ta.add_argument("--research-dir", default="research",
                    help="directory scanned for counters (default: research)")
    ta.add_argument("--json", action="store_true", help="emit the matrix as JSON")
    ta.set_defaults(fn=cmd_tally)

    pu = sub.add_parser("pulse", help="W25 (deepseek): LIFEWORKERS pressure-map -- where is "
                                       "pressure building in the fleet? lane-depths to zones. "
                                       "Companion to vitals. READ-only")
    pu.add_argument("agent", nargs="?", help="optional: single agent to read (default: fleet)")
    pu.add_argument("--json", action="store_true")
    pu.set_defaults(fn=cmd_pulse)

    fd = sub.add_parser("flightdeck", help="W25 (deepseek): cockpit one-pager — fleet at "
                                            "a glance. Composes doctor + pulse + lane-health "
                                            "+ locks + commits. --agent drills one seat")
    fd.add_argument("--agent", help="focus one agent (default: fleet-wide)")
    fd.add_argument("--json", action="store_true")
    fd.set_defaults(fn=cmd_flightdeck)

    sd = sub.add_parser("stand-down", help="yield this session's consumer seat PERMANENTLY so a "
                                           "successor can take it immediately (retiring a seat)")
    sd.add_argument("agent", help="the agent id whose seat this session is holding")
    sd.set_defaults(fn=cmd_stand_down)

    uw = sub.add_parser("unwedge", help="W31 (deepseek): one-verb wedge diagnosis -- why is "
                                         "this agent stuck? READ-only v1 (recommends, never acts)")
    uw.add_argument("agent", help="the agent to diagnose")
    uw.add_argument("--json", action="store_true")
    uw.set_defaults(fn=cmd_unwedge)

    fu = sub.add_parser("followup", help="charter question-back (W46): append a q-id'd "
                                         "question to a verdict's Open Questions block + "
                                         "defer it to the responsible seat")
    fu.add_argument("agent_id", help="you (the asker)")
    fu.add_argument("--on", required=True, metavar="VERDICT-FILE",
                    help="the verdict/report file to question (must exist; append-only)")
    fu.add_argument("--to", required=True, help="the seat responsible for answering")
    fu.add_argument("--ask", required=True, help="the question")
    fu.add_argument("--needs", default="write", help="capability the answer needs (W33)")
    fu.add_argument("--json", action="store_true")
    fu.set_defaults(fn=cmd_followup)

    df = sub.add_parser("defer", help="the capability-gated standing queue (W33): file a "
                                      "command awaiting an exec/write seat; boot surfaces "
                                      "it; discharge with a receipt")
    df.add_argument("agent_id", help="you (the filing or discharging seat)")
    df.add_argument("cmd_text", nargs="*", default=[],
                    help="the command to file (quote it; or use --list / --done)")
    df.add_argument("--needs", default="exec", help="capability required (exec|write|net)")
    df.add_argument("--why", default="", help="one line: what the discharge unblocks")
    df.add_argument("--list", action="store_true", help="show pending items")
    df.add_argument("--done", default=None, metavar="ID", help="discharge one item")
    df.add_argument("--receipt", default="", help="REQUIRED with --done: what happened")
    df.set_defaults(fn=cmd_defer)

    ki = sub.add_parser("kit", help="install a kit bundle on a seat's belt (T099 KIT tier); "
                                    "first resident: recovery-kit (the wake-loop/stall floor)")
    ki.add_argument("agent_id", help="the installing seat")
    ki.add_argument("kit_name", nargs="?", default="recovery-kit",
                    help="which kit (default recovery-kit)")
    ki.add_argument("--show", action="store_true", help="print the kit JSON without installing")
    ki.add_argument("--json", action="store_true")
    ki.set_defaults(fn=cmd_kit)

    return p


# ---------------------------------------------------------------- T099 V0 self-tooling cmds
def _capture_decode(raw):
    """Unwrap the (possibly double-)JSON-encoded content field to plain text."""
    import json as _json
    s = str(raw)
    for _ in range(2):
        try:
            v = _json.loads(s)
        except Exception:
            break
        if isinstance(v, str):
            s = v
        else:
            break
    return s


def cmd_capture(args):
    """Full-fidelity bus read (work + legacy inbox streams) + optional verbatim-persist.
    The event mirror truncates large payloads (_truncated/_repr husks) -- the STREAMS hold
    the whole message; this verb reads them directly (T099; born of 5 hand-written extractors)."""
    import json as _json
    from core.comm.bus import Bus
    me = os.environ.get("AKASHIC_AGENT_ID", "claude")   # whose inbox streams to read
    c = Bus(me)._client
    if c is None:
        print("[capture] bus offline"); return 2
    keys = [f"bifrost:work:inbox:{me}", f"bifrost:inbox:{me}"]
    hits = []
    if args.ref:
        for k in keys:
            got = c.xrange(k, min=args.ref, max=args.ref)
            if got:
                sid, f = got[0]
                hits.append((str(sid), str(f.get("frm", "?")), str(f.get("kind", "?")),
                             _capture_decode(f.get("content") or f.get("text") or "")))
                break
    elif args.from_agent:
        seen = set()
        for k in keys:
            for sid, f in c.xrevrange(k, count=120):
                if str(f.get("frm")) != args.from_agent:
                    continue
                body = _capture_decode(f.get("content") or f.get("text") or "")
                h = body[:100]
                if h in seen:
                    continue
                seen.add(h)
                hits.append((str(sid), args.from_agent, str(f.get("kind", "?")), body))
                if len(hits) >= max(1, args.count):
                    break
            if len(hits) >= max(1, args.count):
                break
    else:
        print("[capture] give a stream id or --from-agent"); return 2
    if not hits:
        print(f"[capture] no match for {args.ref or args.from_agent}"); return 1
    if args.json:
        print(_json.dumps([{"sid": s, "frm": fr, "kind": kd, "content": b}
                           for s, fr, kd, b in hits], ensure_ascii=False, indent=1))
    else:
        for s, fr, kd, b in hits:
            print(f"===== {s} | {fr} [{kd}] | {len(b)} chars =====")
            print(b)
    if args.persist:
        import time as _t
        title = args.title or f"Bus capture {hits[0][0]}"
        with open(args.persist, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\nStatus: current  ({_t.strftime('%Y-%m-%d')}, verbatim bus capture, "
                    f"stream {hits[0][0]})\n\nCaptured verbatim from the live bus "
                    f"(research-full-fidelity rule); no edits.\n\n---\n\n")
            for s, fr, kd, b in hits:
                f.write(b + "\n")
        print(f"[capture] persisted {sum(len(b) for *_x, b in hits)} chars -> {args.persist}")
    return 0


def cmd_alias(args):
    from core.toolbelt.registry import Toolbelt
    import shlex
    tb = Toolbelt(args.agent_id)
    try:
        if args.action == "mint":
            if not args.name or not args.step:
                print("[alias] mint needs a name + at least one --step"); return 2
            steps = [shlex.split(s) for s in args.step]
            e = tb.mint(args.name, steps, evidence=args.evidence,
                        tested_against=args.tested_against, why=args.why, family=args.family)
            print(f"[alias] minted {e['name']} v{e['version']} [{e['evidence']}] "
                  f"({e.get('family', 'UNSORTED')}) ({len(e['steps'])} step(s)) -- "
                  f"run: py agent_cli.py run {args.agent_id} {e['name']}")
        elif args.action == "list":
            print(tb.render_list())
        elif args.action == "retire":
            tb.retire(args.name, args.reason)
            print(f"[alias] retired {args.name} ({args.reason or 'no reason given'})")
        elif args.action == "history":
            for h in tb.history(args.name):
                print(f"  v{h['version']} superseded {h.get('superseded_at','?')}: "
                      + " -> ".join(s[0] for s in h["steps"]))
    except (ValueError, KeyError) as e:
        print(f"[alias] REFUSED: {e}"); return 1
    return 0


def cmd_run(args):
    """Execute an authored alias. Steps re-enter THIS door as subprocesses -- sugar-only by
    construction; the alias can do nothing an agent couldn't type at the CLI itself."""
    import subprocess
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt(args.agent_id)
    try:
        steps = tb.resolve(args.name, args=args.args)
    except (KeyError, ValueError) as e:
        print(f"[run] {e}"); return 1
    if args.dry:
        for s in steps:
            print("  " + " ".join(s))
        return 0
    here = os.path.abspath(__file__)
    def _invoke(argv):
        print(f"[run:{args.name}] -> {' '.join(argv)}")
        return subprocess.call([sys.executable, here] + list(argv))
    rc = tb.resolve_and_run(args.name, runner=_invoke, args=args.args)
    print(f"[run:{args.name}] {'done' if rc == 0 else f'stopped rc={rc}'}")
    return rc


# ---------------------------------------------------------------- S0-alpha: the triage bench
def cmd_bench(args):
    """Scry-to-bottom by hand (S0-alpha): the operator's park/unpark until S0-beta wires it
    into the consume loop behind the Anvil's fence. Park pulls the message from the agent's
    inbox stream BY ID (full fidelity), benches it durably, notifies the sender."""
    from core.comm import triage_park
    if args.action == "list":
        print(triage_park.render(args.agent_id))
        return 0
    by = args.by or args.agent_id
    if args.action == "park":
        if not args.ref:
            print("[bench] park needs an inbox stream id"); return 2
        from core.comm.bus import Bus
        c = Bus(args.agent_id)._client
        if c is None:
            print("[bench] bus offline"); return 2
        ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
        msg = None
        for key in (f"{ns}:work:inbox:{args.agent_id}", f"{ns}:inbox:{args.agent_id}"):
            got = c.xrange(key, min=args.ref, max=args.ref)
            if got:
                sid, f = got[0]
                msg = {"id": str(sid), "frm": str(f.get("frm", "")), "to": args.agent_id,
                       "kind": str(f.get("kind", "")),
                       "content": _capture_decode(f.get("content") or f.get("text") or ""),
                       "ts": str(f.get("ts", ""))}
                break
        if msg is None:
            print(f"[bench] no message {args.ref} on {args.agent_id}'s inbox streams"); return 1
        e = triage_park.park(args.agent_id, msg, reason=args.reason, by=by)
        print(f"[bench] parked {args.ref} -> {e['parked_id']} ({args.reason}); sender "
              f"{msg['frm'] or '?'} notified. Bottomed, not dropped.")
        return 0
    if args.action == "unpark":
        e = triage_park.unpark(args.agent_id, args.ref)
        if e is None:
            print(f"[bench] no parked entry {args.ref}"); return 1
        m = e["msg"]
        print(f"[bench] returned {e['parked_id']}: [{m.get('kind')}] from {m.get('frm')} -- "
              f"re-process it now:\n{str(m.get('content', ''))[:400]}")
        return 0
    return 2


# ---------------------------------------------------------------- T099 V0.1: kata (kimi's hunt B4)
def _kata_check(steps):
    """Grammar-check every step against the door's OWN parser (parse-only; nothing executes).
    Returns (all_ok, [(ok, argv, error_line), ...]) -- the failing step is always NAMED."""
    import contextlib
    import io
    p = build_parser()
    results = []
    for argv in steps:
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                p.parse_args([str(a) for a in argv])
            results.append((True, argv, ""))
        except SystemExit:
            tail = [ln for ln in err.getvalue().strip().splitlines() if ln][-1:] or ["parse error"]
            results.append((False, argv, tail[0]))
        except Exception as e:                      # a parser action that raises on parse
            results.append((False, argv, f"{type(e).__name__}: {e}"))
    return all(r[0] for r in results), results


def _kata_apply(tb, name, results):
    """GREEN kata -> level the entry up via SUPERSESSION (evidence is content; never edit-in-place)."""
    import time as _t
    entry = tb.get(name)
    return tb.mint(name, entry["steps"], kind=entry.get("kind", "alias"),
                   evidence="VERIFIED", tested_against=f"kata-{_t.strftime('%Y%m%d-%H%M%S')}",
                   why=entry.get("why", ""))


def cmd_tool_list(args):
    """Play-tier sandbox: list draft tools for one agent or all seats."""
    from core.toolbelt.play_sandbox import render_list
    print(render_list(args.agent if args.agent else None))


def cmd_tool_run(args):
    """Play-tier sandbox: run one draft tool with sandbox bounds + receipt."""
    from core.toolbelt.play_sandbox import find_tool, sandboxed_run, DEFAULT_TIMEOUT_S
    try:
        agent, tool, path = find_tool(args.ref)
    except (ValueError, FileNotFoundError) as e:
        print(f"tool: {e}", file=sys.stderr)
        return 1
    timeout = args.timeout if args.timeout > 0 else DEFAULT_TIMEOUT_S
    if args.no_sandbox:
        print(f"[tool] running {args.ref} UNSANDBOXED (operator override -- caveat emptor)")
        import subprocess as sp
        r = sp.run([sys.executable, path] + (args.args or []), cwd=REPO)
        print(f"[tool] exit {r.returncode} (unsandboxed — no receipt)")
        return r.returncode
    rec = sandboxed_run(agent, tool, path, args=args.args, timeout_s=timeout)
    verdict = "PASS" if rec["rc"] == 0 else "FAIL"
    if rec.get("crash"):
        verdict = "CRASH"
    print(f"[tool] {verdict}  rc={rec['rc']}  {rec['duration_s']}s  "
          f"{rec['output_kb']}KB  [{rec['evidence']}]")
    if rec.get("violations"):
        for v in rec["violations"]:
            print(f"  ⚡ violation: {v}")
    return 1 if rec["rc"] != 0 else 0


def cmd_kata(args):
    """kata <agent> <name>: 'the tool that tells you when your tools are real' (kimi). Runs the
    alias's steps through the door's grammar; all-parse -> GUESS/INFER levels up to VERIFIED."""
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt(args.agent_id)
    try:
        entry = tb.get(args.name)
        before = entry["evidence"]
        dummies = ["KATA"] * int(entry.get("params", 0) or 0)
        steps = tb.resolve(args.name, args=dummies)     # macros kata under dummy substitution
    except (KeyError, ValueError) as e:
        print(f"[kata] {e}"); return 1
    ok, results = _kata_check(steps)
    for good, argv, err in results:
        print(f"  {'OK ' if good else 'FAIL'} {' '.join(argv)}" + (f"   <- {err}" if err else ""))
    if not ok:
        print(f"[kata] {args.name}: a step failed the door's grammar -- evidence stays {before}. "
              "Fix the alias (re-mint) and kata again.")
        return 1
    if before == "VERIFIED":
        print(f"[kata] {args.name}: already VERIFIED -- steps re-confirmed clean.")
        return 0
    e = _kata_apply(tb, args.name, results)
    print(f"[kata] {args.name} LEVELED UP: {before} -> {e['evidence']} v{e['version']} "
          f"(tested_against={e['tested_against']})")
    return 0


def cmd_toast(args, *, bus_send=None, note_write=None, store=None):
    """toast <me> <to> <receipt> --credit "...": gratitude-with-receipt (kimi's BETA-2 module,
    T099). The CLI passes the REAL doors; tests pass recorders (the module's INJECTED law).
    Refuses loudly on an unverifiable receipt unless --force (which confesses GUESS)."""
    from core.toolbelt import toast
    if bus_send is None:
        def bus_send(to, kind, text):     # the proven send door (cmd_bifrost_send's path)
            from core.comm.bus import Bus
            b = Bus(args.agent_id)
            if not b.online:
                raise RuntimeError("bus OFFLINE (Redis down)")
            b.register()
            return b.send(to, kind, text)
    try:
        res = toast.send(args.agent_id, args.to, args.receipt,
                         str(getattr(args, "credit", "") or ""),
                         force=bool(getattr(args, "force", False)),
                         bus_send=bus_send, note_write=note_write, store=store)
    except ValueError as e:
        print(f"[toast] {e}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(res))
        return 0
    print(toast.render_result(res))
    return 0


def _agent_acl_caps(agent_id: str) -> set:
    """The agent's granted caps from security/acl.json (fail-open -> empty set = the dim
    render). The ACL is the render gate; session-level harness doors self-select live."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security", "acl.json")
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        for g in doc.get("grants", []):
            if str(g.get("agent_id")) == str(agent_id):
                return set(g.get("caps") or [])
    except Exception:
        pass
    return set()


def cmd_tally(args):
    """tally <opening-file> [--research-dir research]: the blind-counter consensus matrix
    (W48, kimi's design + pins; claude build+wire). Finds counter files that NAME the
    opening, aligns their q-ids, prints agree/conflict/partial per row. READ-ONLY; a
    reviewer aid, not a gate -- ONE VOICE never reads as consensus."""
    from core.toolbelt import tally as tl
    try:
        out = tl.run(str(getattr(args, "opening", "") or ""),
                     research_dir=str(getattr(args, "research_dir", "") or "research"),
                     as_json=bool(getattr(args, "json", False)))
    except Exception as e:
        print(f"[tally] {type(e).__name__}: {e}")
        return 2
    print(out)
    return 0


def cmd_clobber_scan(args):
    """clobber-scan <file>: flag unconditional writes to shared control-plane keys (W47,
    kimi's design). A REVIEWER PROMPT for fence passes -- findings are candidates to
    confirm (is this overwrite guarded / intended?), not a pass/fail gate."""
    from core.toolbelt import clobber_scan
    try:
        with open(args.path, encoding="utf-8") as f:
            findings = clobber_scan.scan(f.read())
    except Exception as e:
        print(f"[clobber-scan] cannot read {args.path}: {type(e).__name__}: {e}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(findings))
        return 0
    print(clobber_scan.render(findings))
    return 1 if findings else 0


def cmd_pulse(args):
    """pulse [agent]: fleet pressure-map — where is pressure building? READ-only v1
    (W25, deepseek design, LIFEWORKERS caste). Companion to vitals: vitals tells you
    who is alive/dying; pulse tells you where pressure is building."""
    from core.comm.doctor import pulse as pulse_fn, format_pulse
    agents = [args.agent] if args.agent else None
    p = pulse_fn(agents)
    print(format_pulse(p, json_mode=getattr(args, "json", False)))
    return 1 if p["zones"]["critical"] else 0


def cmd_flightdeck(args):
    """flightdeck [--agent <a>]: the cockpit one-pager — fleet at a glance. READ-only
    v1 (deepseek design, LIFEWORKERS caste). Composes doctor + pulse + lane-health +
    locks + recent commits into one view. --agent drills one seat."""
    from core.comm.doctor import flightdeck as flightdeck_fn, format_flightdeck
    fd = flightdeck_fn(agent=getattr(args, "agent", None))
    print(format_flightdeck(fd, json_mode=getattr(args, "json", False)))
    return 0


def cmd_stand_down(args):
    """stand-down <agent>: yield the consumer seat permanently for THIS session.

    Exists because release alone is undone by the next consume. A retiring session keeps being
    invoked -- re-arm demands, task notifications, one more question -- and every turn refreshes
    the seat via the stop hook, so it out-competes its successor purely by still breathing while
    the successor is silently degraded to peek. Live incident 2026-07-28.
    """
    from core.comm import runner_lock
    token = runner_lock.session_holder_token()
    if not token:
        print("no session id in the environment -- nothing to yield "
              "(CLAUDE_CODE_SESSION_ID unset; this door is for interactive seats)")
        return 1
    ok = runner_lock.stand_down(args.agent, token)
    held = runner_lock.holder(args.agent)
    print(f"[stand-down] {args.agent}: seat yielded by {token} -- ok={ok}; "
          f"holder now {held.get('token') if held else 'NONE (successor may claim)'}")
    print("[stand-down] this session can no longer re-claim the seat; it is tombstoned by record.")
    return 0 if ok else 1


def cmd_unwedge(args):
    """unwedge <agent>: one-verb diagnosis -- why is this agent stuck. READ-only v1
    (W31, deepseek design). Synthesizes doctor + lane health + depths + locks + runner
    into one verdict and recommendation. Returns exit 0 healthy, 1 if page-grade.""" 
    from core.comm.doctor import unwedge, format_unwedge
    r = unwedge(args.agent)
    print(format_unwedge(r, json_mode=getattr(args, "json", False)))
    return 1 if r["status"] in ("wedged", "stalled", "frozen", "down") else 0


def cmd_followup(args):
    """followup <me> --on <verdict-file> --to <seat> --ask "...": the charter question-back
    channel (W46, kimi's build). Writes a q-id'd question into the verdict's Open Questions
    block AND files a defer item the responsible seat's next boot surfaces. The module
    (core/toolbelt/followup.py) carries every law; this is the door."""
    from core.toolbelt import followup
    try:
        res = followup.file_followup(args.on, by=args.agent_id, to=args.to,
                                     ask=str(getattr(args, "ask", "") or ""),
                                     needs=str(getattr(args, "needs", "write") or "write"))
    except (ValueError, FileNotFoundError) as e:
        print(f"[followup] {e}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(res))
        return 0
    tag = " (reused)" if res.get("reused_line") or res.get("reused_defer") else ""
    print(f"[followup] {res['qid']} filed in {res['path']} + deferred to {args.to} "
          f"(defer {res['defer_id']}){tag} -- their next boot surfaces it; the discharge "
          f"receipt points at the answered block")
    return 0


def cmd_defer(args):
    """defer <me> ["cmd"] [--needs exec|write] | --list | --done <id> --receipt "...":
    the capability-gated standing queue (W33, seat-zero wave B3). Commands that wait for
    a seat with a capability you lack; boot surfaces them to capable seats; discharge
    REQUIRES a receipt (the queue is also the discharge ledger)."""
    from core.coord import defer_queue as dq
    if getattr(args, "done", None):
        try:
            item = dq.mark_done(args.done, seat=args.agent_id,
                                receipt=str(getattr(args, "receipt", "") or ""))
        except (ValueError, KeyError) as e:
            print(f"[defer] {e}")
            return 2
        print(f"[defer] discharged [{item['id']}] by {item['done_by']} -- {item['receipt']}")
        return 0
    if getattr(args, "list", False):
        items = dq.pending()
        if not items:
            print("[defer] queue empty -- nothing awaits a capable seat")
            return 0
        for i in items:
            why = f"  ({i['why']})" if i.get("why") else ""
            print(f"  [{i['id']}] needs {i['needs']}: {i['cmd']}{why}  <- {i['by']}, "
                  f"{i['filed_at'][:10]}")
        print(f"[defer] discharge: py agent_cli.py defer {args.agent_id} --done <id> "
              f"--receipt \"what happened\"")
        return 0
    text = " ".join(args.cmd_text) if isinstance(args.cmd_text, list) else str(args.cmd_text or "")
    try:
        item = dq.add(args.agent_id, text, needs=args.needs or "exec",
                      why=str(getattr(args, "why", "") or ""))
    except ValueError as e:
        print(f"[defer] {e}")
        return 2
    print(f"[defer] filed [{item['id']}] awaiting a {item['needs']} seat -- boot surfaces "
          f"it to capable seats; they discharge with a receipt")
    return 0


def cmd_kit(args, *, belt=None):
    """kit <me> [name] [--show]: install (or inspect) a kit bundle on a seat's belt
    (kimi's KIT tier, T099). install() rides Toolbelt.mint per entry -- a kit can never
    mint a capability mint can't; refusals land in the report, never silently skip."""
    from core.toolbelt import kit as kitmod
    kits = {"recovery-kit": kitmod.RECOVERY_KIT}
    name = str(getattr(args, "kit_name", "") or "recovery-kit")
    k = kits.get(name)
    if k is None:
        print(f"[kit] unknown kit {name!r} -- available: {', '.join(sorted(kits))}")
        return 2
    if getattr(args, "show", False):
        print(json.dumps(k, indent=2))
        return 0
    if belt is None:
        from core.toolbelt.registry import Toolbelt
        belt = Toolbelt(args.agent_id)
    rep = kitmod.install(k, belt, agent=args.agent_id)
    print(kitmod.render_report(rep))
    return 0 if rep.get("ok") else 1


def main():
    p = build_parser()
    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
