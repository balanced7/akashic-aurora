"""
Bifrost pull-side helpers (System 5 read lane).

boot() surfaces unread bus mail without consuming the cursor; promoted() reads durable
salient messages from the Ledger (B2). Presence is refreshed on boot.
"""
from __future__ import annotations

import json
import os
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
    """Mark agent online + list who else is ATTENDING. Never raises.

    T155. `Bus.presence()` lists `{ns}:presence:*` REGISTRATION keys -- it answers "who registered
    recently", which is not the question a sender has. Printing that list under the word "online"
    is how, on 2026-08-03, this surface said `codex_root` was online in the same minute the send
    door said it had no heartbeat and queued a directed brief where nothing would read it.

    So registration is now filtered through the one shared verdict (core.comm.liveness.attendance,
    the same probe the send door uses). Registered-but-unattended agents are NOT dropped -- they
    move to their own field, because "registered, but nothing is reading its mail" is precisely the
    state that cost a night, and it deserves a name rather than a silent omission.
    """
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        registered = b.register() if b.online else False
        live = b.presence() if b.online else []
        names = [p.get("agent") for p in live if p.get("agent")]
        attended, unattended = [], []
        for n in names:
            try:
                from core.comm.liveness import attendance
                state = attendance(n).state
            except Exception:
                state = "UNKNOWN"          # a broken probe never promotes to "online"
            (attended if state == "ATTENDED" else unattended).append(n)
        return {
            "online": b.online,
            "registered": registered,
            "pending": b.pending() if b.online else 0,
            "agents_online": attended,
            "agents_registered_unattended": unattended,
        }
    except Exception:
        return {"online": False, "registered": False, "pending": 0,
                "agents_online": [], "agents_registered_unattended": []}


def peek_inbox(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Unread direct+broadcast mail; advance=False so cursor is unchanged.

    FRESHNESS WINDOW (pins: tests/test_sync_peek_freshness.py; kimi's Q4, adopted 3/3):
    the old peek rendered the OLDEST `limit` from the cursor, so a stale backlog showed the
    SAME items on every call and newly-arrived mail was INVISIBLE -- at this session's boot
    that masked three real replies behind ten stale notices. Now the peek OVER-READS
    (detect-only, cursor untouched) and windows: a few oldest for context, the NEWEST for
    truth, and an explicit gap marker plus `pending_at_least` on every row so no renderer
    can present a window as the whole inbox."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        if not b.online:
            return []
        want = max(1, limit)
        cap = max(want * 5, 50)
        raw = b.inbox(limit=cap, advance=False)
        # SOL'S BOUNDARY REGRESSION (blocker, reproduced at 80 msgs; pin
        # test_true_tail_visible_beyond_the_overread_cap): the forward over-read XREADs
        # oldest-first from the cursor, so with backlog > cap the "newest" above is the
        # newest OF THE OLDEST cap -- the true tail is invisible exactly in the storm
        # condition freshness exists for. Fix contract (Sol's): TRUE-TAIL reverse-range
        # merge, not a larger magic cap. We XREVRANGE each stream's genuine tail (unread
        # only: min exclusive of the cursor), apply the same consume-door filters _drain
        # uses (integrity, own-broadcast, other-seat directed mail; frags skipped -- they
        # cannot reassemble backwards, a documented residual), and merge by id.
        tail_msgs = []
        try:
            from core.comm import packet_spec as _ps
            cur = b._read_cursor()
            sid8 = b._my_sid8()
            streams = [(b._inbox_key(str(agent_id)), cur.get("inbox", "0"), False)]
            streams.append((b._bc_key, cur.get("bc", "0"), True))
            if sid8:
                try:
                    seat_cur = str(b._client.hget(b._seat_cursor_key(sid8), "seat") or "0")
                    streams.append((b._seat_inbox_key(str(agent_id), sid8), seat_cur, False))
                except Exception:
                    pass
            seen_tail = set()
            for skey, scur, is_bc in streams:
                lo = "(" + str(scur) if str(scur) not in ("0", "0-0") else "-"
                try:
                    rows = b._client.xrevrange(skey, max="+", min=lo, count=want)
                except Exception:
                    continue
                for sid, fields in rows or []:
                    if str(sid) in seen_tail:
                        continue
                    seen_tail.add(str(sid))
                    ok, _why = _ps.verify_integrity(fields)
                    if not ok or _ps.parse_frag(fields) is not None:
                        continue
                    m = b._to_msg(str(sid), dict(fields))
                    if is_bc and m.frm == str(agent_id):
                        continue
                    inc = str((m.meta or {}).get("to_incarnation") or "")[:8]
                    if inc and sid8 and inc != sid8:
                        continue
                    tail_msgs.append(m)
        except Exception:
            tail_msgs = []
        by_id = {str(m.id): m for m in raw}
        for m in tail_msgs:
            by_id.setdefault(str(m.id), m)
        merged = sorted(by_id.values(), key=lambda m: str(m.id))
        total = len(merged)
        # kimi fence-lite finding 2: when the forward over-read HITS its cap, `total` is a
        # floor, not the depth -- confess it (renderers show "N+") instead of silently capping.
        capped = len(raw) >= cap
        if total > want:
            k_old = max(1, want // 4)
            head, tail = merged[:k_old], merged[-(want - k_old):]
            hidden = total - len(head) - len(tail)
            windowed = True
        else:
            head, tail, hidden, windowed = merged, [], 0, False
        out: List[Dict[str, Any]] = []

        def _row(m):
            d = m.to_dict() if hasattr(m, "to_dict") else {}
            return {
                "id": d.get("id") or getattr(m, "id", ""),
                "frm": d.get("frm") or getattr(m, "frm", ""),
                "to": d.get("to") or getattr(m, "to", ""),
                "kind": d.get("kind") or getattr(m, "kind", ""),
                "content": d.get("content", getattr(m, "content", "")),
                "ts": d.get("ts") or getattr(m, "ts", ""),
                "pending_at_least": total,
                "pending_capped": capped,
            }

        out.extend(_row(m) for m in head)
        if hidden > 0:
            # display_only + kind outside every salient/flaggable/ackable set: the gap row
            # is un-actionable BY CONSTRUCTION (kimi finding 2), not by empty-id accident.
            out.append({"gap": True, "display_only": True, "id": "", "frm": "backlog",
                        "to": str(agent_id), "kind": "gap", "ts": "",
                        "pending_at_least": total, "pending_capped": capped,
                        "content": f"(... {hidden} older unread hidden between oldest and "
                                   f"newest -- the cursor is behind; --consume or drain "
                                   f"to clear)"})
        out.extend(_row(m) for m in tail)
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
        # S3 INVALID SESSION, named (pin P2): a tombstoned self must hear "you ended", never
        # the contention teach that blames a phantom holder. Ends the masquerade.
        try:
            from core.comm import wake_seat as _ws
            _sid = _session_holder_token()
            _sid = _sid[len("session:"):] if _sid.startswith("session:") else _sid
            if _sid and _sid != "anon-cli" and _ws.is_tombstoned(_sid):
                return {"seat_held": True, "invalid_session": True, "consumed": [],
                        "teach": ("INVALID SESSION -- this session ENDED BY RECORD "
                                  "(tombstone, T086 S1). Boot fresh (K2-tail seed); this "
                                  "seat must not consume, arm, or re-arm. The successor "
                                  "owns the seat.")}
        except Exception:
            pass
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
                                stale, now_ms) or 0) / 3600000.0
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


def stale_notice_lines(res: Dict[str, Any], agent_id: str) -> List[str]:
    """W65: the honest tail EVERY consume door must render.

    consume_inbox already reports what it parked to the bench and skipped while the
    cursor advanced; both doors used to drop it and answer "(no messages consumed)" /
    "(no new messages)". The CLI door was fixed first and deepseek's fence immediately
    found the MCP door still lying -- so the render lives HERE, once, and both doors call
    it. A shared renderer is the only version of this fix that cannot drift back apart.
    Returns [] when nothing moved, because silence is honest then."""
    notice = (res.get("stale_notice") or "").strip()
    if not notice:
        return []
    out = [notice]
    if not (res.get("consumed") or []):
        out.append(f"# no NEW mail surfaced for {agent_id} -- but the cursor ADVANCED past "
                   f"the entries above (bench: py agent_cli.py bench {agent_id})")
    return out


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
    # S2: every sync/boot BEATS this seat's per-incarnation worklive -- the roster's (and
    # the future reaper's) sensor. Zero-cost, never raises; claude seats heartbeat for the
    # first time here (deepseek/kimi runners already beat their agent-level keys).
    resume_line = ""
    try:
        from core.comm import roster as _roster
        from core.comm.bus import NS as _DEFAULT_NS
        _ns = os.environ.get("BIFROST_NAMESPACE", _DEFAULT_NS)
        _sid = (os.environ.get("BIFROST_INCARNATION")
                or os.environ.get("CLAUDE_CODE_SESSION_ID") or "")
        if _sid:
            _hb = _roster.heartbeat(_ns, str(agent_id), _sid, phase="sync")
            _gap = (_hb or {}).get("resumed_after_s") if isinstance(_hb, dict) else None
            if _gap:
                # S3, the Discord marker: replay and live are different states; say which.
                resume_line = (f"RESUMED after {int(_gap // 60)}m{int(_gap % 60)}s away -- "
                               f"the unread below accumulated while away; replay ends here, "
                               f"now live")
    except Exception:
        pass
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
        # Honest count: when the peek is WINDOWED, pending_at_least (the true unread depth)
        # beats len(msgs) -- the perpetual "8 unread" whisper all night was this exact lie.
        "pending": (max((int(m.get("pending_at_least", 0)) for m in msgs), default=0)
                    or len(msgs)),
        "messages": msgs,
        "locks": peek_locks(agent_id),
        "pause_line": pause_line,
        "expect_lines": expect_lines,
        "resume_line": resume_line,
    }


def format_inbox_line(msg: Dict[str, Any], max_len: int = 2000) -> str:
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


_ASK_KINDS = frozenset({"request", "question", "handoff", "blocker"})
_TRACE_KINDS = frozenset({"trace", "steer", "nudge", "ledger_update", "resolved"})


def kind_summary(messages) -> Dict[str, int]:
    """W02: bucket unread by what the seat must DO -- asks (need a reply), fyi (read
    only), traces (telemetry/control). Unknown kinds -> fyi (fail toward showing)."""
    out = {"asks": 0, "fyi": 0, "traces": 0}
    for m in (messages or []):
        k = str(_mget(m, "kind", "")).lower()
        if k in _ASK_KINDS:
            out["asks"] += 1
        elif k in _TRACE_KINDS:
            out["traces"] += 1
        else:
            out["fyi"] += 1
    return out


def render_kind_summary(messages) -> str:
    """W02: 'N asks / M fyi / K traces' -- non-zero buckets only, asks first (the thing
    that needs answering leads). '' when empty. Kills the second --traces call just to
    learn whether an ask was buried under trace spam (kimi F9's trigger)."""
    s = kind_summary(messages)
    parts = []
    for key, label in (("asks", "ask"), ("fyi", "fyi"), ("traces", "trace")):
        n = s[key]
        if n:
            plural = label if label == "fyi" else f"{label}s"
            parts.append(f"{n} {plural if n != 1 else label}")
    return " / ".join(parts)


def render_collapsed(messages, *, show_traces: bool = False, max_len: int = 2000):
    """W4 (T081) -- THE shared trace-collapse render (bifrost-sync CLI + the runner's bifrost_inbox
    both go through this, so the two surfaces can never diverge). Algorithm (deepseek's, reconciled
    2026-07-16): work/sig mail shown FIRST and verbatim; trace-class messages grouped into runs of
    consecutive same-(frm, kind), each run showing its first line + 'N more' fold. Prior art:
    rsyslog pmlastmsg ('last message repeated N times' -- consecutive dedup, first always shown);
    Grafana Loki (collapse at render, never at ingest); OTel tail-sampling (decide per snapshot,
    carry no state across peeks). The journald failure mode (silent suppression) is designed out:
    the fold is reversible (show_traces expands, in original order), lossless (nothing dropped),
    and explicit (states the count).
    
    W84 (07-28, deepseek): DUAL-WRITE TWIN DEDUP. T039a/T044 dual-write means every message
    exists on TWO streams. Before rendering, adjacent near-identical messages (same frm+kind+
    content_prefix) collapse to one line with a '[N copies]' marker. The dedup is RENDER-ONLY
    (lossless -- nothing dropped, nothing consumed) and uses content prefix matching so a
    genuine follow-up with different content is never collapsed. Sha/reply_id dedup is stronger
    but requires envelope access; the prefix heuristic catches the dual-write case (identical
    content on two streams) without false positives on real follow-ups.
    
    Accepts dict OR Message-object messages; returns a line list."""
    msgs = list(messages or [])

    def _line(m):
        return (f"[{str(_mget(m, 'kind', '?'))}] from {str(_mget(m, 'frm', '?'))}: "
                f"{_clip(_content_str(_mget(m, 'content')), max_len)}")
    
    def _twin_key(m):
        """W84: logical identity for dual-write twin detection. (frm, kind, first 200 chars
        of content). Two copies of the same message on different streams share these three
        fields. A genuine follow-up from the same sender with different content won't match."""
        content = _content_str(_mget(m, 'content'))
        return (str(_mget(m, 'frm', '?')), str(_mget(m, 'kind', '?')), content[:200])

    if show_traces:
        return [_line(m) for m in msgs]     # full, original order -- the reversible expand

    work_lines, trace_lines = [], []
    seen_twins = {}  # W84: twin_key -> first occurrence index in work_lines
    i = 0
    while i < len(msgs):
        m = msgs[i]
        if not _is_trace_class(m):
            tk = _twin_key(m)
            if tk in seen_twins:
                # W84: twin detected -- bump the count on the first occurrence
                first_idx = seen_twins[tk]
                # Count how many twins we've seen for this key (stored as [line, count])
                if isinstance(work_lines[first_idx], list):
                    work_lines[first_idx][1] += 1
                else:
                    work_lines[first_idx] = [work_lines[first_idx], 2]
                i += 1
                continue
            seen_twins[tk] = len(work_lines)
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

    # W84: expand twin-count lines: "[kind] from X: ..." -> "[kind] from X: ... [2 copies]"
    out = []
    for item in work_lines:
        if isinstance(item, list):
            line, count = item
            out.append(f"{line}  [{count} copies]")
        else:
            out.append(item)
    if trace_lines:
        # T120 G11b: no blank separator -- every emitted line carries structure; a bare
        # "" between mail and folded traces was render noise wearing a line's identity.
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
    if block.get("resume_line"):
        print(f"  {block['resume_line']}")  # S3: the Resumed marker (Discord semantics)
    for ln in block.get("expect_lines") or []:
        print(f"  {ln}")                     # RB-29: redrives + dead expectations, loud
    if not block.get("bus_online"):
        print("  (bus OFFLINE -- Redis unreachable; durable mail still in promoted() / events)")
        return
    online = block.get("agents_online") or []
    if online:
        print(f"  online: {', '.join(online)}")
    # T155: registered, but no beat, pulse, or worklive -- mail addressed here QUEUES and nothing
    # reads it. Named rather than omitted: the silent version of this line cost a directed brief.
    idle = block.get("agents_registered_unattended") or []
    if idle:
        print(f"  registered but UNATTENDED (mail queues, nothing reads it): {', '.join(idle)}")
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
    summary = render_kind_summary(block.get("messages") or [])
    summary_tag = f" [{summary}]" if summary else ""
    # kimi fence-lite finding 2: when the over-read hit its cap, `pending` is a FLOOR --
    # render "N+" so a capped window can never read as the whole depth.
    capped = any(m.get("pending_capped") for m in (block.get("messages") or [])
                 if isinstance(m, dict))
    print(f"  {pending}{'+' if capped else ''} unread ({scope}, peek -- use bifrost_inbox or "
          f"`py agent_cli.py bifrost-sync --consume` to ack):{summary_tag}")
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
