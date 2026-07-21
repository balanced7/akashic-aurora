"""
Bifrost pull-side helpers (System 5 read lane).

boot() surfaces unread bus mail without consuming the cursor; promoted() reads durable
salient messages from the Ledger (B2). Presence is refreshed on boot.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _clip(s: Any, n: int = 220) -> str:
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return (cut or s[:n]) + " ...[truncated]"


def _content_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, default=str)
    except (TypeError, ValueError):
        return str(content)


def register_presence(agent_id: str) -> Dict[str, Any]:
    """Mark agent online + list who else is present. Never raises."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        registered = b.register() if b.online else False
        live = b.presence() if b.online else []
        return {
            "online": b.online,
            "registered": registered,
            "pending": b.pending() if b.online else 0,
            "agents_online": [p.get("agent") for p in live],
        }
    except Exception:
        return {"online": False, "registered": False, "pending": 0, "agents_online": []}


def peek_inbox(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Unread direct+broadcast mail; advance=False so cursor is unchanged."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        if not b.online:
            return []
        msgs = b.inbox(limit=max(1, limit), advance=False)
        out = []
        for m in msgs:
            d = m.to_dict() if hasattr(m, "to_dict") else {}
            out.append({
                "id": d.get("id") or getattr(m, "id", ""),
                "frm": d.get("frm") or getattr(m, "frm", ""),
                "to": d.get("to") or getattr(m, "to", ""),
                "kind": d.get("kind") or getattr(m, "kind", ""),
                "content": d.get("content", getattr(m, "content", "")),
                "ts": d.get("ts") or getattr(m, "ts", ""),
            })
        return out
    except Exception:
        return []


def _session_holder_token() -> str:
    """RB-21: the sticky consumer identity for THIS session (single definition lives in
    runner_lock; this door's fallback = one shared anonymous bucket -- two anonymous
    twins collapse to a single holder, a pre-acknowledged v1 bound; every Claude Code
    session carries the env var, so the twin incident class is covered)."""
    from core.comm import runner_lock
    return runner_lock.session_holder_token() or "session:anon-cli"


def _seat_teach(agent_id: str, info: Dict[str, Any], ttl: int, *, fenced: bool = False) -> str:
    mode = ("fenced MID-DRAIN (a successor claimed the seat during this read)"
            if fenced else "held")
    age = ""
    try:
        import time as _t
        then = _t.mktime(_t.strptime(str(info.get("ts", "")), "%Y-%m-%dT%H:%M:%S"))
        age = f"claimed {int(_t.time() - then)}s ago, "
    except Exception:
        pass
    return (f"CONSUMER SEAT {mode.upper()} for '{agent_id}': holder {info.get('token', '?')} "
            f"({age}ttl {ttl}s) -- read degraded to PEEK (cursor unmoved, nothing consumed). "
            f"One session consumes per agent id; a dead holder frees by TTL alone (<= {ttl}s). "
            f"If this is a live twin, wind it down; durable doors (task ledger, notes, "
            f"promoted) are never blocked.")


def consume_inbox(agent_id: str, limit: int = 20) -> Dict[str, Any]:
    """Read and advance the per-agent cursor -- through the RB-21 consumer seat.

    ONE return shape for every caller (deepseek review Q3, Option A):
      {"seat_held": False, "consumed": [msg, ...]}                       -- we consumed
      {"seat_held": True, "holder": ..., "since": ..., "ttl": ...,
       "peeked": [msg, ...], "teach": "..."}                             -- degraded to peek
    Mail is ALWAYS visible; it is never eaten by a session that lost the seat."""
    try:
        from core.comm.bus import Bus
        from core.comm import runner_lock
        b = Bus(str(agent_id or "unknown"))
        if not b.online:
            return {"seat_held": False, "consumed": []}
        ttl = int(runner_lock.SESSION_CONSUMER_TTL)
        ok, gen, info = runner_lock.claim_consumer(str(agent_id), _session_holder_token())
        if not ok:
            # T083-C1-1: before degrading to peek, check whether the holder is PROVABLY dead
            # (crash-killed session; clean_death only covers graceful ends). Freed -> claim once.
            rescue = {}
            try:
                rescue = runner_lock.free_if_dead(str(agent_id))
            except Exception:
                rescue = {}
            if rescue.get("freed"):
                ok, gen, info = runner_lock.claim_consumer(str(agent_id), _session_holder_token())
        if not ok:
            peek = b.inbox(limit=max(1, limit), advance=False)
            teach = _seat_teach(str(agent_id), info, ttl)
            if rescue.get("reason"):
                teach += f" [holder liveness: {rescue['reason']}]"
            return {"seat_held": True, "holder": info.get("token"), "since": info.get("ts"),
                    "ttl": ttl, "teach": teach,
                    "peeked": [m.to_dict() if hasattr(m, "to_dict") else {} for m in peek]}
        status: Dict[str, str] = {}
        from core.comm.bifrost_api import BifrostAPI
        if BifrostAPI.consume_lane_enabled():
            # T045 stage 2 session-door cutover (fence Q3: same-slice): same RB-21 seat,
            # same generation fence, but reads ride work_drain and advances hit the LANE hash.
            api = BifrostAPI(str(agent_id))
            api.bus.lane_flip_if_migrating()
            nxt: Dict[str, str] = {}
            msgs = api.work_drain(timeout_ms=1, limit=max(1, limit), since_out=nxt,
                                  generation=gen)
            if nxt.get("inbox") or nxt.get("bc"):
                status["status"] = api.bus.advance_to(
                    inbox=nxt.get("inbox"), bc=nxt.get("bc"), generation=gen,
                    cursor_key=api.bus.lane_cursor_key())
        else:
            msgs = b.inbox(limit=max(1, limit), advance=True, generation=gen,
                           commit_status_out=status)
        if status.get("status") == "STALE_GENERATION":
            # A successor fenced us between claim and commit: the cursor did NOT move for
            # us -- show what we read as a PEEK; the successor redelivers (at-least-once).
            info2 = runner_lock.holder(str(agent_id)) or {}
            return {"seat_held": True, "holder": info2.get("token"), "since": info2.get("ts"),
                    "ttl": ttl, "teach": _seat_teach(str(agent_id), info2, ttl, fenced=True),
                    "peeked": [m.to_dict() if hasattr(m, "to_dict") else {} for m in msgs]}
        # S0-gamma-b: stale-gate + auto-park at the CLI consume path (deepseek's build,
        # claude-fenced; mirror of bifrost_runner_deepseek.py's D2 block, S0-beta). The
        # cursor already advanced at drain time, so park is the only backstop: stale asks
        # are bottomed to the durable bench (RB-29-loud, never dropped), stale non-asks
        # skip, fresh mail flows. Parking only on the SEAT-HELD consume -- a peek never
        # parks. Imports are lazy (fence amendment A1: this file's house style; the outer
        # except must never be reachable by an import failure at module load).
        stale_notice_txt = ""
        parked_n = 0
        if msgs:
            try:
                import time as _time
                from core.comm import packet_spec
                now_ms = int(_time.time() * 1000)
                fresh, stale_asks, stale_skips = packet_spec.partition_stale(
                    msgs, now_ms=now_ms, stale_ms=packet_spec.stale_gate_ms())
                if stale_skips:
                    stale_notice_txt += (f"  skipped {len(stale_skips)} stale "
                                         f"inform(s)/trace(s) (no bench pollution)\n")
                if stale_asks:
                    stale_notice_txt += packet_spec.stale_notice(
                        stale_asks, now_ms=now_ms) + "\n"
                    for stale in stale_asks:
                        try:
                            from core.comm import triage_park
                            age_h = (packet_spec.msg_age_ms(
                                getattr(stale, "id", ""), now_ms) or 0) / 3600000.0
                            triage_park.park(
                                str(agent_id),
                                {"id": getattr(stale, "id", ""),
                                 "frm": getattr(stale, "frm", ""),
                                 "to": getattr(stale, "to", ""),
                                 "kind": getattr(stale, "kind", ""),
                                 "content": getattr(stale, "content", ""),
                                 "ts": getattr(stale, "ts", "")},
                                reason=f"stale {age_h:.1f}h (CLI consume auto-triage)",
                                by=f"{agent_id}-cli")
                            parked_n += 1
                        except Exception:
                            pass                     # park is best-effort (G3)
                    stale_notice_txt += (f"  parked {parked_n} stale ask(s) to durable "
                                         f"bench (bottomed, never dropped; "
                                         f"py agent_cli.py bench {agent_id})\n")
                msgs = fresh
            except Exception:
                pass                                 # gate is best-effort; fresh-path intact
        return {"seat_held": False,
                "stale_notice": stale_notice_txt.strip() or None,
                "stale_asks_parked": parked_n,
                "consumed": [m.to_dict() if hasattr(m, "to_dict") else {} for m in msgs]}
    except Exception:
        return {"seat_held": False, "consumed": []}


def peek_locks(agent_id: str) -> List[Dict[str, Any]]:
    """Advisory path-locks currently held (C2 awareness). Never raises."""
    try:
        from core.comm.locks import LockManager
        return LockManager(str(agent_id or "viewer")).list_locks()
    except Exception:
        return []


def collect_boot_bifrost(agent_id: str, limit: int = 8) -> Dict[str, Any]:
    """Presence + unread peek + held locks for boot() / bifrost-sync.
    RB-30: a leftover pause is surfaced LOUDLY here (the pull floor every turn touches)."""
    pres = register_presence(agent_id)
    msgs = peek_inbox(agent_id, limit=limit)
    pause_line = ""
    try:
        from core.comm.control import format_pause_line, pause_status
        pause_line = format_pause_line(pause_status())
    except Exception:
        pass
    expect_lines: List[str] = []
    try:
        # RB-29 (T030 L4): the render-time expectation sweep -- redrive overdue asks,
        # declare the exhausted ones DEAD loudly. No daemon; this pull floor IS the clock.
        from core.comm.expectations import format_sweep_lines, sweep
        expect_lines = format_sweep_lines(sweep(agent_id))
    except Exception:
        pass
    return {
        "bus_online": pres["online"],
        "presence_registered": pres["registered"],
        "agents_online": pres["agents_online"],
        "pending": len(msgs),
        "messages": msgs,
        "locks": peek_locks(agent_id),
        "pause_line": pause_line,
        "expect_lines": expect_lines,
    }


def format_inbox_line(msg: Dict[str, Any], max_len: int = 220) -> str:
    frm = msg.get("frm", "?")
    kind = msg.get("kind", "?")
    body = _clip(_content_str(msg.get("content")), max_len)
    return f"[{kind}] from {frm}: {body}"


def _mget(m, key, default=""):
    """Access a field on a bus message that may be a dict (CLI render) OR a Message object
    (the runner's ToolBox render). Lets ONE collapse helper serve both surfaces."""
    return m.get(key, default) if isinstance(m, dict) else getattr(m, key, default)


def _is_trace_class(msg) -> bool:
    """W4 (T081): display-only telemetry vs work-mail. ONE definition, shared by every render:
    the kind routes to the trace lane (packet_spec.is_trace_kind, the T039 single source) OR meta
    marks it display_only. Fail-open: an unclassifiable message is treated as WORK -- we never
    fold real mail out of sight."""
    try:
        from core.comm.packet_spec import is_trace_kind
        if is_trace_kind(_mget(msg, "kind")):
            return True
    except Exception:
        pass
    meta = _mget(msg, "meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return bool(isinstance(meta, dict) and meta.get("display_only"))


def render_collapsed(messages, *, show_traces: bool = False, max_len: int = 220):
    """W4 (T081) -- THE shared trace-collapse render (bifrost-sync CLI + the runner's bifrost_inbox
    both go through this, so the two surfaces can never diverge). Algorithm (deepseek's, reconciled
    2026-07-16): work/sig mail shown FIRST and verbatim; trace-class messages grouped into runs of
    consecutive same-(frm, kind), each run showing its first line + 'N more' fold. Prior art:
    rsyslog pmlastmsg ('last message repeated N times' -- consecutive dedup, first always shown);
    Grafana Loki (collapse at render, never at ingest); OTel tail-sampling (decide per snapshot,
    carry no state across peeks). The journald failure mode (silent suppression) is designed out:
    the fold is reversible (show_traces expands, in original order), lossless (nothing dropped),
    and explicit (states the count). Accepts dict OR Message-object messages; returns a line list."""
    msgs = list(messages or [])

    def _line(m):
        return (f"[{str(_mget(m, 'kind', '?'))}] from {str(_mget(m, 'frm', '?'))}: "
                f"{_clip(_content_str(_mget(m, 'content')), max_len)}")

    if show_traces:
        return [_line(m) for m in msgs]     # full, original order -- the reversible expand

    work_lines, trace_lines = [], []
    i = 0
    while i < len(msgs):
        m = msgs[i]
        if not _is_trace_class(m):
            work_lines.append(_line(m))     # verbatim; breaks any trace run
            i += 1
            continue
        kind = str(_mget(m, "kind", "?"))
        frm = str(_mget(m, "frm", "?"))
        run_start = i
        while (i < len(msgs) and _is_trace_class(msgs[i])
               and str(_mget(msgs[i], "kind", "?")) == kind
               and str(_mget(msgs[i], "frm", "?")) == frm):
            i += 1
        run_count = i - run_start
        trace_lines.append(_line(msgs[run_start]))
        if run_count > 1:
            trace_lines.append(f"  └─ {run_count - 1} more {kind}(s) from {frm} "
                               f"-- --traces to expand")

    out = list(work_lines)
    if trace_lines:
        if work_lines:
            out.append("")                  # separator between mail and folded traces
        out.extend(trace_lines)
    return out


def format_digest_line(msg: Dict[str, Any]) -> str:
    """Ultra-compact one-liner for a cheap scan: kind, sender, a 64-char teaser.
    The full body is one drill away (`bifrost-sync` without --digest, or --json)."""
    frm = msg.get("frm", "?")
    kind = msg.get("kind", "?")
    ts = (msg.get("ts") or "")[11:16]   # HH:MM
    teaser = _clip(_content_str(msg.get("content")), 64)
    return f"  {ts} [{kind}] {frm}> {teaser}"


def print_boot_bifrost_section(block: Dict[str, Any], show_traces: bool = False) -> None:
    print("\n## UNREAD BIFROST (live bus)")
    if block.get("pause_line"):
        print(f"  {block['pause_line']}")   # RB-30: a frozen fleet announces itself first
    for ln in block.get("expect_lines") or []:
        print(f"  {ln}")                     # RB-29: redrives + dead expectations, loud
    if not block.get("bus_online"):
        print("  (bus OFFLINE -- Redis unreachable; durable mail still in promoted() / events)")
        return
    online = block.get("agents_online") or []
    if online:
        print(f"  online: {', '.join(online)}")
    pending = block.get("pending") or 0
    if pending == 0:
        print("  (no new messages -- peek only; cursor unchanged)")
        return
    # W8 (T081): name the denominator (same scope check as the whisper) so 'N here vs M in the
    # whisper' stops confusing -- the peek reads the legacy cursor (all lanes during dual-write).
    try:
        from core.comm.bifrost_api import BifrostAPI
        scope = "work-lane" if BifrostAPI.consume_lane_enabled() else "all lanes"
    except Exception:
        scope = "legacy peek"
    print(f"  {pending} unread ({scope}, peek -- use bifrost_inbox or "
          f"`py agent_cli.py bifrost-sync --consume` to ack):")
    for ln in render_collapsed(block.get("messages") or [], show_traces=show_traces):
        print(f"  {ln}")   # W4: trace-class telemetry folded (--traces to expand)


def standby(agent_id: str, session_id: str = "", *, listen=None,
            limit: int = 20) -> Dict[str, Any]:
    """T084-CL-2: the turn-end ritual as ONE decision function -- drain (if the seat is ours to
    take), report seat state, then hand off to the LISTENER (injected callable) only when it is
    safe and non-redundant to listen. Encodes tonight's hard-won ordering laws:

      - consume-THEN-arm (arming on an undrained inbox insta-wakes: failure ledger C1-2);
      - a seat held by a provably-dead session gets rescued inside consume_inbox (C1-1);
      - a seat held by a LIVE twin means the TWIN is the wakeable seat-holder -- listening here
        would be a redundant watcher burning cycles (the plan-wall law): report, do NOT listen.

    Returns {"drained": int, "listened": bool, "decision": str, "report": [lines]}. The CLI verb
    wraps this and, when the decision is 'listen', BLOCKS as the wake listener's parent -- so one
    harness-tracked `bifrost-standby` background task = drain + report + armed seat, and the
    listener's exit re-invokes the harness. Never spawns detached (the T073 untracked-process
    root cause)."""
    out: Dict[str, Any] = {"drained": 0, "listened": False, "decision": "", "report": []}
    rep = out["report"]
    res = consume_inbox(agent_id, limit=limit)
    if res.get("seat_held"):
        teach = str(res.get("teach") or "consumer seat held")
        rep.append(f"seat: HELD by {res.get('holder')} -- {teach}")
        rep.append(f"standby: NOT listening (live twin is the wakeable seat-holder; "
                   f"{len(res.get('peeked') or [])} msg(s) visible as peek)")
        out["decision"] = "twin-holds-seat"
        return out
    msgs = res.get("consumed") or []
    out["drained"] = len(msgs)
    rep.append(f"drained: {len(msgs)} message(s)" if msgs else "drained: inbox already clean")
    for ln in render_collapsed(msgs)[:12]:
        rep.append(f"  {ln}")
    try:   # expectations sweep state rides the report (RB-29 visibility)
        blk = collect_boot_bifrost(agent_id, limit=1)
        for ln in blk.get("expect_lines") or []:
            rep.append(f"  {ln}")
    except Exception:
        pass
    if listen is None:
        rep.append("standby: report-only (no listener requested)")
        out["decision"] = "report-only"
        return out
    rep.append("standby: inbox clean -- handing off to the wake listener (blocking)")
    out["decision"] = "listen"
    out["listened"] = True
    out["listen_rc"] = listen(agent_id, session_id)
    return out


def print_boot_locks_section(block: Dict[str, Any], agent_id: str = "") -> None:
    """Awareness: who holds which advisory path-locks (only prints if any are held)."""
    locks = block.get("locks") or []
    if not locks:
        return
    print("\n## ADVISORY PATH-LOCKS (who's editing what -- C2)")
    for lk in locks:
        mine = " (you)" if lk.get("agent") == agent_id else ""
        print(f"  {lk.get('path')}  <- {lk.get('agent')}{mine}  token {lk.get('token')}")


def format_promoted_events(events: List[Dict[str, Any]], *, json_out: bool = False) -> str:
    if json_out:
        return json.dumps(events, indent=2, default=str)
    if not events:
        return "# 0 durable Bifrost message(s) (kind=bifrost_msg)"
    lines = [f"# {len(events)} durable Bifrost message(s) (salient bus -> Ledger)"]
    for ev in events:
        d = ev.get("detail") or {}
        at = (ev.get("at") or d.get("ts") or "")[:19]
        frm, to, kind = d.get("frm", "?"), d.get("to", "?"), d.get("kind", "?")
        body = _clip(_content_str(d.get("content")), 200)
        ref = ev.get("_ref") or ev.get("id") or ""
        lines.append(f"  [{kind}] {frm} -> {to}  {at}")
        lines.append(f"    {body}")
        if ref:
            lines.append(f"    ref: {ref}")
    lines.append("\nDrill: py agent_cli.py events --get <ref>")
    return "\n".join(lines)


def format_console_events(events: List[Dict[str, Any]], *, json_out: bool = False) -> str:
    """Render durable console control-plane events (interjection/bus_control/file_drop) for the CLI."""
    if json_out:
        return json.dumps(events, indent=2, default=str)
    if not events:
        return "# 0 durable console event(s) (interjection / bus_control / file_drop)"
    lines = [f"# {len(events)} durable console event(s) (live cockpit -> Ledger)"]
    for ev in events:
        d = ev.get("detail") or {}
        kind = ev.get("kind", "?")
        at = (ev.get("at") or "")[:19]
        ref = ev.get("_ref") or ev.get("id") or ""
        if kind == "interjection":
            head = f"  [interjection:{d.get('intent','?')}] user -> {d.get('to','?')}  {at}"
            body = _clip(_content_str(d.get("text")), 200)
        elif kind == "bus_control":
            head = f"  [control] {d.get('by','user')} {d.get('action','?')}  {at}"
            body = _clip(_content_str(d.get("reason", "")), 200) or "(no reason)"
        elif kind == "file_drop":
            head = f"  [file_drop] {d.get('by','user')} shared  {at}"
            body = f"{d.get('path','?')} ({d.get('bytes','?')} bytes)"
        else:
            head = f"  [{kind}]  {at}"
            body = _clip(_content_str(ev.get("summary", "")), 200)
        lines.append(head)
        lines.append(f"    {body}")
        if ref:
            lines.append(f"    ref: {ref}")
    lines.append("\nDrill: py agent_cli.py events --get <ref>")
    return "\n".join(lines)
